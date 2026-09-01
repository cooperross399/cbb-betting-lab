#!/usr/bin/env python3
"""Fetch today's board, freeze the opinions it can still precede, render the card.

    # Costs nothing, makes no request, needs no credential:
    PYTHONPATH=src python scripts/run_gameday_card.py --card-slot morning

    # The same, over a staged board on disk. This is the offline end-to-end path:
    PYTHONPATH=src python scripts/run_gameday_card.py \
        --card-slot morning --staged-board data/staging/cbb/2027-01-12_morning.csv

    # What the workflow runs. Spends credits:
    PYTHONPATH=src python scripts/run_gameday_card.py \
        --live --card-slot morning --credit-cap 40000

    # A rehearsal of one past day. Publishes nothing, settles nothing:
    PYTHONPATH=src python scripts/run_gameday_card.py \
        --live --card-slot evening --credit-cap 40000 \
        --rehearsal --slate-date 2027-01-12

**Dry by default.** Without `--live` nothing is requested, no credential is
read and nothing is spent. `--staged-board` is the offline path that still
exercises the whole chain — staging, pricing, the gates, the freeze and the
render — which is the thing that had to be provable before a single credit was
spent on it. `tests/test_the_dry_run_is_dry.py` blocks the socket layer and
hides the credential, then runs this file.

`.github/workflows/cbb-gameday-refresh.yml` reads `decision=<word>` off the last
line of stdout and puts it on the card feed. Every word this script prints there
is one of `cbb_betting_lab.reports.gameday_card.Decision`.

## The three refusals, and why each one is a refusal rather than a warning

1. **Any run pricing a day that is not today**, without `--rehearsal`. The
   snapshot is named by its day and it is append-only within one, so neither
   direction is recoverable afterwards. Backwards, the file's name says its
   opinions were frozen before games that had already been played. **Forwards
   is worse**: a snapshot frozen now for a future slate is still standing when
   that day arrives, so the real run appends nothing for those wagers and the
   first opinion of the night is one taken before anybody knew who was playing.
   Neither depends on a credential, so the refusal is not gated on `--live`.
2. **Less quota than the cap.** A run that starts short gets partway through the
   slate and stops, freezing the games it happened to reach. In this sport the
   bias has a shape — the fetch works in tip order, so a starved run keeps the
   early games and drops the late ones, which is the West Coast, low-major end
   of the board this lab was built to look at. Refusing loses a night; starting
   writes a biased night into a ledger that cannot be re-made.
3. **An accounting identity that does not reconcile**, and its two neighbours:
   a bar with no bucket in the identity at all, and an already-frozen row this
   run cannot re-key. All three mean the same thing — the run can no longer
   account for every wager it saw — and a wager that reached none of the six
   buckets vanished, which is how a card recommends from a sixth of a slate and
   reports it as the whole one. Errors, not warnings, and the run exits on each.

The credit cap is hard and is checked **inside the provider adapter, before
every request, against the measured running total from `x-requests-last`** —
never against this script's estimate. The NHL lab capped a run at 200,000 and
spent 289,984 by estimating from markets asked rather than markets returned,
while its test asserted the cap could not be breached.

## The one thing this script cannot do on its own

`Selections changed` fires by comparing this run's selection fingerprint against
the previous one, which is kept in `<output-dir>/cbb_card_state.json`. In CI
`data/outputs/` is rebuilt from an empty checkout every run, so that file is
absent and **the card says so** — "nothing is claimed about whether the
selections changed" — rather than firing the marker on every run, which is how a
notification stops being read long before it stops being sent.

Making it operative needs the state file carried on `card-feed` beside the
ledger and the snapshots, restored into `--output-dir` before this script runs.
That is two lines in `.github/workflows/cbb-gameday-refresh.yml` and nothing
here: point `--output-dir` at a directory holding the previous state file and
the comparison works with no change to this file.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from cbb_betting_lab.competitions import DEFAULT_COMPETITION_KEY, competition_for
from cbb_betting_lab.config import OUTPUTS_DIR, RAW_DIR, STAGING_DIR
from cbb_betting_lab.forward_evidence import ARCHIVE_DIR, SnapshotKeyError
from cbb_betting_lab.providers import staging
from cbb_betting_lab.providers.env_file import load_provider_env, redact
from cbb_betting_lab.providers.odds_api import (
    OddsApiProvider,
    ProviderError,
    sufficient_quota,
)
from cbb_betting_lab.reports import gameday_card as GC
from cbb_betting_lab.schedule_contract import SLOT_NAMES, slot_for
from cbb_betting_lab.staging_provider_policy import load as load_policy


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    parser.add_argument(
        "--card-slot",
        default="morning",
        choices=list(SLOT_NAMES),
        help="Which slot this run publishes as. The evening slot freezes the "
        "games the morning slot could not reach and never re-prices one it did.",
    )
    parser.add_argument(
        "--credit-cap",
        type=int,
        default=0,
        help="Hard. Checked before every request against the measured total. "
        "Defaults to the competition registry's own daily cap.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually fetch the board. Without this nothing is requested.",
    )
    parser.add_argument(
        "--rehearsal",
        action="store_true",
        help="Rehearse one day. Writes to its own archive, settles nothing, "
        "labels its output, and never publishes.",
    )
    parser.add_argument(
        "--slate-date",
        default="",
        help="The league date to price (YYYY-MM-DD). Defaults to today in the "
        "competition's own timezone. Any other date requires --rehearsal.",
    )
    parser.add_argument(
        "--staged-board",
        default="",
        help="Read the board from a staged CSV instead of the provider. "
        "Requests nothing, reads no credential, spends nothing.",
    )
    parser.add_argument(
        "--market-tiers",
        default="1,2,3",
        help="Which market tiers to ask for per event. Futures are never on a "
        "gameday card: they settle on a different clock.",
    )
    parser.add_argument("--skip-quota-check", action="store_true")
    parser.add_argument("--archive-dir", default=str(ARCHIVE_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument("--staging-dir", default=str(STAGING_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    return parser


def _today(competition) -> str:
    return datetime.now(competition.timezone).date().isoformat()


def _read_previous_fingerprint(path: Path, *, day: str, card_slot: str) -> str:
    """The previous fingerprint, and only when it describes the same card.

    **The day and the slot are checked, not merely recorded.** `_write_state`
    stores both and this reader ignored them, while the card renders the
    comparison as *"since the last card for this slate day"* — so the moment
    the state file survives a run, which is precisely the change the module
    docstring above proposes, the morning card would be compared against last
    night's evening card and today's against yesterday's. `Selections changed`
    would then fire on a day boundary rather than on a change, which is the one
    failure mode the marker cannot survive: a notification that fires when
    nothing happened stops being read long before it stops being sent.

    A state file for a different day or slot is not an error and not a stale
    file to be repaired. It is simply not a card this run may compare itself
    against, so it reads as "nothing to compare", which the card already knows
    how to say.

    A rehearsal's state is refused for the same reason it is never published: a
    rehearsal is not a card, and a real run must not report a change against
    one.
    """
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return ""
    if not isinstance(payload, dict):
        return ""
    if str(payload.get("slate_date", "")) != str(day):
        return ""
    if str(payload.get("card_slot", "")) != str(card_slot):
        return ""
    if str(payload.get("decision", "")) == GC.Decision.REHEARSAL.value:
        return ""
    return str(payload.get("fingerprint", ""))


def _write_state(path: Path, run: GC.CardRun) -> None:
    """Remember this run's fingerprint so `Selections changed` means something.

    A marker that fires when nothing happened does not become noisy, it becomes
    worthless: the run where the selection genuinely changed looks exactly like
    the four hundred before it. So the comparison is made against the previous
    card **for this slate day and slot pair**, and when there is no previous
    card the card says nothing about change rather than claiming one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "slate_date": run.slate_date,
                "card_slot": run.card_slot,
                "fingerprint": run.fingerprint,
                "decision": run.decision.value,
                "generated_at": run.generated_at,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    competition = competition_for(args.competition)
    slot = slot_for(args.card_slot)
    cap = int(args.credit_cap or competition.daily_credit_cap)
    today = _today(competition)
    day = str(args.slate_date or today).strip() or today
    tiers = tuple(
        int(t) for t in str(args.market_tiers).split(",") if str(t).strip().isdigit()
    ) or (1, 2, 3)

    print(f"{competition.title} — gameday card")
    print(f"Slate day {day} ({competition.timezone.key}); slot `{slot.name}`, which "
          f"freezes {slot.what}.")
    print(f"Credit cap {cap:,}, enforced against the measured running total.")

    # Refusal one. See the module docstring. It is not scoped to `--live`,
    # because the more dangerous direction is the one that spends nothing.
    #
    # Backwards, a run files today's board under a day whose games have already
    # been played, and the snapshot's name then says those opinions were frozen
    # before results that already existed.
    #
    # **Forwards is worse.** `write_snapshot` is append-only by key, so a
    # snapshot frozen now for a future slate is still standing when that day
    # arrives — and the real run finds it, appends nothing for those wagers, and
    # leaves them at prices taken before anybody knew who was playing. The first
    # opinion of opening night would be a rehearsal, and nothing downstream
    # would ever say so. Neither direction depends on a credential, so neither
    # is gated on `--live`.
    if day != today and not args.rehearsal:
        print(
            f"::error::Refusing to card {day}: today is {today}. A snapshot "
            "frozen for another day is append-only and cannot be corrected — "
            "backwards it claims opinions were frozen before results that "
            "already existed, and forwards it is still standing when that day "
            "arrives, so the real run leaves it there and the first opinion of "
            "the night was taken before anybody knew who was playing. Pass "
            "--rehearsal to rehearse that day into its own archive, which "
            "publishes nothing and which no real run reads.",
            file=sys.stderr,
        )
        print(f"decision={GC.Decision.REFUSED.value}")
        return 2

    if args.live and args.staged_board:
        print(
            "::error::--live and --staged-board are mutually exclusive. One "
            "spends credits and one reads a file; a run that did both could not "
            "say which board it carded.",
            file=sys.stderr,
        )
        print(f"decision={GC.Decision.REFUSED.value}")
        return 2

    archive = Path(args.archive_dir)
    if args.rehearsal:
        # Its own archive, which the gameday workflow neither restores nor
        # publishes. A rehearsal's snapshot cannot reach the card feed however
        # this script is invoked.
        archive = archive / GC.REHEARSAL_ARCHIVE_SEGMENT / day
        print(f"REHEARSAL. Frozen opinions go to `{archive}`; nothing is published.")

    policy = load_policy()
    print(policy.summary_line(competition))

    # ---- the board -------------------------------------------------------
    if args.staged_board:
        source = Path(args.staged_board)
        if not source.is_file():
            print(f"::error::No staged board at {source}.", file=sys.stderr)
            print(f"decision={GC.Decision.REFUSED.value}")
            return 2
        board = GC.read_staged_board(source, competition=competition)
        staged_path = source
    elif args.live:
        load_provider_env()
        try:
            provider = OddsApiProvider(competition)
        except ProviderError as exc:
            print(redact(f"::error::{exc}"), file=sys.stderr)
            print(f"decision={GC.Decision.REFUSED.value}")
            return 2
        if not args.skip_quota_check:
            try:
                headers = provider.quota()
            except ProviderError as exc:
                print(redact(f"::error::{exc}"), file=sys.stderr)
                print(f"decision={GC.Decision.REFUSED.value}")
                return 2
            # Refusal two.
            enough, note = sufficient_quota(headers, cap)
            print(note)
            if not enough:
                print(
                    "::error::Refusing to start. Nothing was fetched and "
                    "nothing was frozen.",
                    file=sys.stderr,
                )
                print(f"decision={GC.Decision.REFUSED.value}")
                return 1
        try:
            board = GC.fetch_board(
                provider,
                competition=competition,
                credit_cap=cap,
                day=day,
                market_tiers=tiers,
            )
        except ProviderError as exc:
            print(redact(f"::error::{exc}"), file=sys.stderr)
            print(f"decision={GC.Decision.REFUSED.value}")
            return 2
        # Every quote, every book, to a place the card cannot read. The freeze
        # keeps one row per wager; line shopping and price survival are measured
        # from here.
        staged_path = staging.staging_path(
            competition,
            day=day,
            slot=f"{slot.name}_rehearsal" if args.rehearsal else slot.name,
            staging_dir=Path(args.staging_dir),
        )
        staging.write_staged(board.rows, staged_path, staging_dir=Path(args.staging_dir))
    else:
        print(
            "Dry run. Nothing was requested, no credential was read and no "
            "credit was spent. Pass --staged-board to card a board already on "
            "disk, or --live to fetch one."
        )
        print(f"decision={GC.Decision.DRY_RUN.value}")
        return 0

    print(f"Board: {board.source}. {board.counts.summary_line()}")
    print(board.spend.summary_line())

    # ---- place, price, gate, freeze, render -------------------------------
    placement = GC.place_games(
        board, competition=competition, day=day, raw_dir=Path(args.raw_dir)
    )
    print(placement.summary_line())

    outputs = Path(args.output_dir)
    state = GC.state_path(competition, outputs)
    try:
        run = GC.run_card(
            board,
            competition=competition,
            day=day,
            card_slot=slot.name,
            archive_dir=archive,
            policy=policy,
            placement=placement,
            rehearsal=bool(args.rehearsal),
            previous_fingerprint=_read_previous_fingerprint(
                state, day=day, card_slot=slot.name
            ),
            output_dir=outputs,
        )
    except (ValueError, GC.CardError, SnapshotKeyError) as exc:
        # Refusal three, and its two neighbours. `AccountingIdentity` raises a
        # ValueError when the identity does not reconcile; `gameday_card`
        # raises a `CardError` when a bar has no bucket in the identity at all,
        # which is the same failure one level up; and `write_snapshot` raises a
        # `SnapshotKeyError` when a row already frozen for this day cannot be
        # re-keyed — at which point this run cannot tell an unfrozen game from a
        # re-price, and the first opinion of the day for a game is never
        # replaced. All three are errors rather than warnings, and all three
        # stop the run rather than reaching the reader as a traceback with no
        # `decision=` line behind it.
        print(f"::error::{exc}", file=sys.stderr)
        print(f"decision={GC.Decision.REFUSED.value}")
        return 2
    run.staged_path = staged_path

    print(run.identity.summary_line())
    print(run.opinions.summary_line())
    print(run.tip.summary_line())
    if run.snapshot_path is not None:
        print(
            f"Froze {run.snapshot_rows_offered:,} wager(s) offered into "
            f"{run.snapshot_path}. The first opinion of the day for a game is "
            "never retroactively replaced."
        )
    else:
        print(
            f"Nothing new was frozen from {run.snapshot_rows_offered:,} wager(s) "
            "offered: they were already frozen for this slate day, or none "
            "could be."
        )

    try:
        card, comment = GC.write_outputs(run, outputs)
    except GC.CardWouldEmail as exc:
        print(f"::error::{exc}", file=sys.stderr)
        print(f"decision={GC.Decision.REFUSED.value}")
        return 2
    print(f"Wrote {card}")
    print(f"Wrote {comment}")
    _write_state(state, run)

    if not run.selections:
        # The allowlist half of this sentence is read off the policy, never
        # asserted. A run that printed "no market is allowlisted" while one was
        # would be false on the one day it mattered.
        print(
            "No selection, no lean, no pass and no stake. "
            + (
                "No market is allowlisted, which is the correct state for a "
                "lab with no signed acceptance receipt, and "
                if not policy.allowlist
                else "Markets are allowlisted and none of them produced one, and "
            )
            + "an excluded market is never reported as a pass, an avoid or a "
            "no-value call."
        )
    else:
        print(f"{len(run.selections):,} selection(s); {run.result.exposure.summary_line()}")

    for note in run.degraded:
        print(f"::warning::{note}")
    print(f"degraded={'true' if run.is_degraded else 'false'}")
    print(f"decision={run.decision.value}")
    return 1 if run.is_degraded else 0


if __name__ == "__main__":
    raise SystemExit(main())
