#!/usr/bin/env python3
"""What became of every prop wager the store offers. A census, and not a grading.

    # The whole store, walk-forward, one disposition per wager:
    PYTHONPATH=src python scripts/run_prop_accounting.py

    # A shorter run over the first N slate days, for wiring only:
    PYTHONPATH=src python scripts/run_prop_accounting.py --days 3

**Nothing here is scored.** This run states no return, no advantage, no
interval and no verdict; it computes no fair price, no log loss and no
probability comparison of any kind. It counts wagers into buckets and it
refuses. Design section 10's gate is two receipts and this script files the
second one, through `models.player_census.assert_every_offered_prop_is_
accounted`, which had no caller anywhere in this repository until this commit.

## The identity, and why both sides are real counts

    every prop wager the store offers
        = refused by name
        + no opinion   (unregistered market + name unresolved
                        + athlete refused + never asked, counted apart)
        + priced
        + unreadable

with a residual of **exactly 0**, market by market and in total.

The two sides are produced by two different passes over the same file and
neither is a remainder of the other:

* the **store's** side is `models.player_census.census`, taken with `usecols=`
  and `chunksize=` over the 977,613,435-byte price store and reconciled against
  the frozen artifact by `assert_reconciles` before this script prices
  anything;
* the **run's** side is one `RunDisposition.file()` call per wager, made by
  `reports.gameday_card.opinions_for` at the moment it decides — the only
  function in the tree that decides what becomes of a prop, and therefore the
  only one that can say which bucket a wager landed in. `file()` raises on a
  second filing of the same wager, so "exactly one bucket" is enforced at the
  call rather than assumed at the sum.

That is the property `scripts/run_price_backtest.py`'s `OpinionAccounting`
docstring records the absence of: an identity whose terms are computed by
subtraction reconciles by construction and cannot detect the loss it exists to
detect. Nothing below subtracts.

**The run fingerprints the file it read.** `store_digest` is computed here, in
this script, over the bytes this script opened, and `assert_every_offered_prop_
is_accounted` looks the census up by that digest and refuses when no census has
reconciled against it. `data/processed/` is a tree of symlinks; a run that
priced one file and reconciled against another would otherwise account for a
denominator nobody counted.

## Why it is walk-forward, on a run that measures nothing

Because the buckets are an output of the model, and a model that has seen the
night it is pricing refuses differently from one that has not. `price_backtest.
walk_forward` cuts the team table and the player table to rows strictly earlier
than each slate day, hands the pricer only those, and stamps what it was
allowed to see; `assert_walk_forward` then reads the stamp back off every row.
A census taken with the whole season in hand would be a census of a model this
lab will never run.

## The record it writes is a report and never a receipt

`data/outputs/cbb_prop_accounting.{json,md}` is what this run found, written so
somebody can read it. **Nothing reads it back.** The receipt itself is
`player_census._ACCOUNTED`, a dict that lives for the length of one process,
and it is deliberately not a file: the module's own comment says a file on disk
would be a grant, it would survive the store changing under it, and a later run
would grade on somebody else's tick. A grading run has to call this gate for
itself, in its own process, and finding this record on disk buys it nothing.

## What it does not do, and where that is written down

It files no acceptance receipt, writes nothing under `data/manual/`, and takes
no position on whether any of these wagers is worth anything. The 33
pre-registered player-prop hypotheses in `data/outputs/experiment_ledger.json`
are untouched by it: not one of them is answered by a count of buckets, and
this script would be the wrong place to answer one.

The two markets refused BY NAME — `player_first_basket` and
`player_double_double` — are counted and are never priced, never given a
verdict, and are not a pass, an avoid or a no-value call.
`reconcile_offered`'s clause 5 refuses this run outright if a wager on either
one reaches any bucket but `refused_by_name`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from cbb_betting_lab.competitions import (
    Competition,
    DEFAULT_COMPETITION_KEY,
    competition_for,
)
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from cbb_betting_lab.models import player_census as PC
from cbb_betting_lab.models import slate
from cbb_betting_lab.providers import historical as H
from cbb_betting_lab.reports import card_matchups, card_pricing, gameday_card
from cbb_betting_lab.reports import price_backtest as PB

#: The model that answers for both halves of a slate. **Not
#: `price_backtest.DEFAULT_MODEL`**, which resolves the team seam alone and
#: declares no `player_history`: under it every prop on every night lands in
#: `never_asked`, the identity still closes at residual 0, and the run would
#: report a census of a model that was never asked a single question. Named
#: here so the refusal is a wiring fault an operator can read rather than a
#: table of zeros.
PLAYER_MODEL = "cbb_betting_lab.models.slate:slate_model"

#: Every column of the price store this run opens. The census reads its own
#: list (`player_census.STORE_COLUMNS_THE_CENSUS_READS`) and this one is
#: deliberately separate: the two sides of the identity are two passes over one
#: file, and a shared column list would be one pass wearing two names. What is
#: here is what `card_pricing.build_wagers` keys a wager on and what
#: `models.slate` forms a subject from.
STORE_COLUMNS_THE_RUN_READS: tuple[str, ...] = (
    "event_id",
    "market",
    "segment",
    "player",
    "selection",
    "line",
    "book",
    "snapshot_phase",
    "american_odds",
    "game_id",
    "season",
    "slate_date",
    "commence_time",
    "home_team",
    "away_team",
    "home_name",
    "away_name",
    "tier",
)

#: 500,000 rows at a time, read from the census rather than restated. The store
#: is 3,863,325 rows and a whole-file read of it is minutes of wall clock and
#: gigabytes resident.
CHUNK_ROWS = PC.CHUNK_ROWS

#: How many distinct sentences the record keeps per bucket. The engine's
#: refusals carry the line or the constant they refused on — "line 41.5 is
#: above the lattice ceiling" is one sentence per line — so a bucket can hold
#: hundreds of spellings of one fact and a record that wrote every one would be
#: a log rather than a record. The commonest are kept, the number NOT kept is
#: written beside them, and the bucket's own count is written beside both, so
#: nothing is summed away and no reader can mistake a truncated list for the
#: whole of it. It is the rule `gameday_card.OpinionCensus` already applies on
#: the card, for the same reason.
REASONS_KEPT = 25

EXIT_OK = 0
EXIT_NOTHING_TO_ACCOUNT = 2
EXIT_DOES_NOT_RECONCILE = 3
EXIT_NO_MODEL = 4
EXIT_INPUTS_ABSENT = 5


class NothingToAccount(RuntimeError):
    """The store holds no prop wager, so there is nothing to account for."""


# --------------------------------------------------------------------------
# The store, fingerprinted and read by the run itself
# --------------------------------------------------------------------------


def store_digest(path: Path) -> tuple[str, int]:
    """sha256 and byte length of the file THIS run opened, read in blocks.

    Computed here rather than taken off the census, because the whole use of it
    is to be a second, independent statement about which bytes were priced.
    A digest handed over by the thing it is meant to check is not a check.
    """
    hasher = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1 << 22)
            if not block:
                break
            size += len(block)
            hasher.update(block)
    return hasher.hexdigest(), size


def load_offered_props(
    path: Path, *, chunksize: int = CHUNK_ROWS
) -> pd.DataFrame:
    """Every player-prop quote in the store, and no other row.

    `usecols=` and `chunksize=` on the one `read_csv` this module makes of the
    price store, for the reason `player_census` gives: the file is 978 MB and
    the player rows are an eighth of it.

    A market key beginning `player_` is a prop, which is
    `player_census.PLAYER_MARKET_PREFIX` and is read from there rather than
    typed: the two sides of the identity have to agree about which rows are in
    it before they can disagree about anything else.
    """
    header = pd.read_csv(path, nrows=0)
    missing = [c for c in STORE_COLUMNS_THE_RUN_READS if c not in header.columns]
    if missing:
        raise NothingToAccount(
            f"{path} is missing {missing}. Nothing is defaulted: a missing "
            "column read as a zero is how a wiring fault becomes a finding, "
            "and a wager this run could not key would be a wager the store "
            "offered and nobody disposed of."
        )
    kept: list[pd.DataFrame] = []
    for chunk in pd.read_csv(
        path,
        usecols=list(STORE_COLUMNS_THE_RUN_READS),
        chunksize=chunksize,
        low_memory=False,
    ):
        props = chunk[
            chunk["market"]
            .astype(str)
            .str.startswith(PC.PLAYER_MARKET_PREFIX, na=False)
        ]
        if not props.empty:
            kept.append(props)
    if not kept:
        raise NothingToAccount(
            f"{path} holds no row whose market begins "
            f"`{PC.PLAYER_MARKET_PREFIX}`. A store with no prop in it and a "
            "store this run failed to read look identical from here, and an "
            "empty accounting must never be printed as a reconciled one."
        )
    return pd.concat(kept, ignore_index=True)


# --------------------------------------------------------------------------
# The run's own side of the identity
# --------------------------------------------------------------------------


def make_price_day(
    model,
    *,
    competition: Competition,
    run: PC.RunDisposition,
    raw_dir: Path,
    tier_of_key: dict,
    refusals: Counter,
    rows_refused: list,
    progress=None,
):
    """The `price_day` callable `walk_forward` drives, one slate day at a time.

    Every frame parameter is named for the key the caller cut it under and none
    carries a default: `price_backtest._refuse_undeclared_frames` refuses a
    pricer whose frame parameter has one, on the ground that a default is a
    pricer left to find the table some other way and every other way is uncut
    and unstamped.

    **The dispositions are filed by `opinions_for` and not here.** This function
    hands it a `RunDisposition` and it makes one `file()` call per prop as it
    decides, in exactly one bucket, before the loop moves on. A bucket assigned
    out here would be this script's second opinion about a decision the card
    already made — the shape of defect that gives an identity two counts of the
    same thing and calls them two sides.

    `tier_of_key` is filled beside the filing so the buckets can be reported per
    tier afterwards. The tier is the store's own column on the wager's event; it
    is never re-derived, because design 9 tiers a team in one place and a second
    tiering here could disagree with the one the estimator used.
    """

    def price_day(
        *,
        day: str,
        history: pd.DataFrame,
        prices: pd.DataFrame,
        player_history: pd.DataFrame,
    ):
        frame = prices.copy()
        model_slate = slate.SlateModel.coerce(
            PB.call_model(
                model,
                "the prop accounting run's per-day pricer (make_price_day)",
                day=day,
                history=history,
                prices=frame,
                competition=competition,
                raw_dir=raw_dir,
                player_history=player_history,
            ),
            day=day,
            team_priced_through=PB.latest_day(history),
            player_priced_through="",
        )

        row_reasons: list[str] = []
        wagers, unparseable, reasons = card_pricing.build_wagers(
            frame,
            competition=competition,
            key_for=card_pricing.default_key_for(competition),
            row_reasons=row_reasons,
        )
        if unparseable:
            # NOT filed into a bucket, and not silently dropped either. A row
            # that never became a wager has no wager key to file under, so the
            # honest thing is to count it, name it, and let the residual carry
            # it: the identity then refuses, which is what a run that cannot
            # say what became of a prop the store offered is supposed to do.
            for reason, count in reasons.items():
                refusals[reason] += int(count)
            rows_refused.append((str(day), int(unparseable)))

        tier_by_event = {
            str(event): str(tier)
            for event, tier in zip(frame["event_id"], frame["tier"])
        }
        for wager in wagers:
            tier_of_key[wager.key] = tier_by_event.get(str(wager.event_id), "")

        before = run.total
        gameday_card.opinions_for(wagers, model_slate, day=day, dispositions=run)
        if progress is not None:
            progress(
                f"  {day}: {len(frame):,} quote(s) -> {len(wagers):,} wager(s), "
                f"{run.total - before:,} filed, {run.total:,} filed so far"
            )

        team_through = PB.latest_day(history)
        player_through = str(model_slate.player_priced_through)
        frame["player_priced_through"] = player_through
        frame["priced_through"] = max(team_through, player_through)
        return frame

    return price_day


# --------------------------------------------------------------------------
# The report. Counts, and nothing derived from them
# --------------------------------------------------------------------------


def bucket_lines(run: PC.RunDisposition) -> list[str]:
    """One line per bucket, in the order the identity sums them.

    `no opinion` is printed as a SUM over four states and never as a bucket of
    its own: a spelling that resolved to nobody, a market the model is not
    registered against, an athlete the projection refused and an event the
    model was never asked about are four different facts about the lab, and the
    wiring faults this seam has had each hid in exactly one of them.
    """
    lines = [
        f"  {run.bucket(PC.BUCKET_PRICED):>9,d}  priced",
        f"  {run.bucket(PC.BUCKET_REFUSED_BY_NAME):>9,d}  refused by name "
        f"({', '.join(PC.MARKETS_REFUSED_BY_NAME)})",
        f"  {run.no_opinion:>9,d}  no opinion, which is these four and is "
        "never one number:",
    ]
    for bucket in PC.NO_OPINION_BUCKETS:
        lines.append(f"  {run.bucket(bucket):>9,d}      {bucket}")
    lines.append(f"  {run.bucket(PC.BUCKET_UNREADABLE):>9,d}  unreadable")
    return lines


#: A wager whose event carries no tier. Counted under its own name rather than
#: assigned to one: design 9 tiers a team in one place, and guessing here would
#: be a second tiering that could disagree with the estimator's own.
UNTIERED = "(untiered)"


def buckets_by_tier(
    run: PC.RunDisposition, tier_of_key: dict
) -> dict[str, Counter]:
    """Tier -> bucket -> wagers, read off what the run FILED.

    One function, called by both the printed table and the written record, so
    the two cannot be two counts of the same thing. Two hand-built copies of
    one number is the shape of defect this repository has paid for repeatedly.

    The bucket comes from `run.filed`, which is the card's own decision at the
    moment it made it; the tier comes from the store's column on the wager's
    event. Neither is re-derived here.
    """
    per_tier: dict[str, Counter] = {}
    for key, (_market, bucket) in run.filed.items():
        tier = tier_of_key.get(key) or UNTIERED
        per_tier.setdefault(tier, Counter())[bucket] += 1
    return per_tier


def tier_lines(run: PC.RunDisposition, tier_of_key: dict) -> list[str]:
    """The same buckets, per tier, because a pooled count hides a skew.

    Design 13's fifth failure mode is name resolution drifting by tier, and it
    is invisible in a Division I total: a fold that refuses low-major spellings
    twice as often as high-major ones reads as one number here and as a biased
    population three steps downstream. The tiers are printed side by side and
    are never summed into a headline.
    """
    per_tier = buckets_by_tier(run, tier_of_key)
    if not per_tier:
        return []
    buckets = [b for b in PC.OFFERED_BUCKETS if any(c[b] for c in per_tier.values())]
    head = f"{'tier':14s} {'wagers':>9s}  " + "  ".join(
        f"{name:>18s}" for name in buckets
    )
    lines = [head]
    for tier in sorted(per_tier):
        counts = per_tier[tier]
        lines.append(
            f"{tier:14s} {sum(counts.values()):9,d}  "
            + "  ".join(f"{counts[name]:18,d}" for name in buckets)
        )
    return lines


def reason_lines(run: PC.RunDisposition, *, most: int = 5) -> list[str]:
    """Why the model said nothing, grouped by bucket and never one line a wager.

    The model's own sentences, printed as it wrote them. A classifier over them
    would go wrong the first time one was reworded, which is why `_player_
    decline` returns the bucket beside the sentence instead of deriving it.
    """
    lines: list[str] = []
    for bucket in PC.OFFERED_BUCKETS:
        reasons = run.reasons.get(bucket)
        if not reasons:
            continue
        lines.append(f"  {bucket}:")
        ordered = sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))
        for reason, count in ordered[:most]:
            lines.append(f"    {count:>9,d} x {reason}")
        if len(ordered) > most:
            lines.append(f"    and {len(ordered) - most:,} further sentence(s)")
    return lines


def record_of(
    accounted: PC.OfferedAttribution,
    *,
    tier_of_key: dict,
    model_spec: str,
    days: int,
    unparseable_rows: int,
    refusals: Counter,
) -> dict:
    """The run record. Counts only, and every one of them a count of rows."""
    census = accounted.census
    run = accounted.run
    per_tier = buckets_by_tier(run, tier_of_key)
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "what": run.what,
        "model": model_spec,
        "store": {
            "path": census.source_path,
            "sha256": census.source_sha256,
            "bytes": census.source_bytes,
            "rows_scanned": census.rows_scanned,
            "player_quotes": census.player_quotes,
            "events": census.events,
            "slate_dates": census.slate_dates,
        },
        "declared_subject": PC.DECLARED_SUBJECT,
        "slate_days_priced": days,
        "offered": accounted.offered,
        "accounted": accounted.accounted,
        "residual": accounted.residual,
        "buckets": {name: run.bucket(name) for name in PC.OFFERED_BUCKETS},
        "no_opinion": run.no_opinion,
        "by_market": [
            {
                "market": market,
                "offered": offered,
                "accounted": counted,
                "buckets": {
                    name: int(run.by_market.get(market, Counter())[name])
                    for name in PC.OFFERED_BUCKETS
                    if run.by_market.get(market, Counter())[name]
                },
            }
            for market, offered, counted in accounted.by_market
        ],
        "by_tier": {
            tier: {name: int(counts[name]) for name in PC.OFFERED_BUCKETS if counts[name]}
            for tier, counts in sorted(per_tier.items())
        },
        "reasons": {
            bucket: {
                "wagers": run.bucket(bucket),
                "distinct_sentences": len(counts),
                "commonest": dict(
                    sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[
                        :REASONS_KEPT
                    ]
                ),
            }
            for bucket, counts in sorted(run.reasons.items())
        },
        "rows_that_became_no_wager": unparseable_rows,
        "row_refusal_reasons": dict(sorted(refusals.items())),
    }


def render(record: dict) -> str:
    """The report. It states no result, and says so on its own first line."""
    store = record["store"]
    lines = [
        "# Prop accounting — what became of every prop wager the store offers",
        "",
        "**This is a census and not a grading.** Every number below is a count "
        "of wagers. Nothing here compares a probability against a price, and "
        "no result of any kind is stated or implied.",
        "",
        f"- Store: `{store['path']}`, {store['bytes']:,} bytes, sha256 "
        f"`{store['sha256']}`",
        f"- {store['rows_scanned']:,} rows scanned, {store['player_quotes']:,} "
        f"of them prop quotes, over {store['events']:,} event(s) and "
        f"{store['slate_dates']:,} slate day(s)",
        f"- Subject: the declared fold is `{record['declared_subject']}`, and "
        "the offered count below is under that one and no other",
        f"- Model: `{record['model']}`, walk-forward over "
        f"{record['slate_days_priced']:,} slate day(s)",
        "",
        f"**{record['offered']:,} wager(s) offered, {record['accounted']:,} "
        f"accounted for, residual {record['residual']}.**",
        "",
        "| Bucket | Wagers |",
        "|:---|---:|",
        f"| priced | {record['buckets'][PC.BUCKET_PRICED]:,} |",
        f"| refused by name | {record['buckets'][PC.BUCKET_REFUSED_BY_NAME]:,} |",
        f"| no opinion (the four below, never summed into a finding) | "
        f"{record['no_opinion']:,} |",
    ]
    for bucket in PC.NO_OPINION_BUCKETS:
        lines.append(f"| &nbsp;&nbsp;{bucket} | {record['buckets'][bucket]:,} |")
    lines += [
        f"| unreadable | {record['buckets'][PC.BUCKET_UNREADABLE]:,} |",
        "",
        "## Per market",
        "",
        "| Market | Offered | Accounted | Residual | Buckets |",
        "|:---|---:|---:|---:|:---|",
    ]
    for row in record["by_market"]:
        spelled = ", ".join(f"{k}={v:,}" for k, v in row["buckets"].items())
        lines.append(
            f"| {row['market']} | {row['offered']:,} | {row['accounted']:,} | "
            f"{row['offered'] - row['accounted']} | {spelled or '-'} |"
        )
    lines += [
        "",
        "## Per tier",
        "",
        "Printed side by side and never pooled into one Division I line: a "
        "fold that refuses one tier's spellings more often than another's "
        "reads as a single number in a total and as a biased population three "
        "steps downstream.",
        "",
        "| Tier | Wagers | Buckets |",
        "|:---|---:|:---|",
    ]
    for tier, counts in record["by_tier"].items():
        spelled = ", ".join(f"{k}={v:,}" for k, v in counts.items())
        lines.append(f"| {tier} | {sum(counts.values()):,} | {spelled} |")
    lines += [
        "",
        "## Why the model said nothing",
        "",
        "The model's own sentences, grouped. Not one of them is a pass, an "
        "avoid or a no-value call, and an absent opinion is never a "
        "probability of zero.",
        "",
    ]
    for bucket, held in record["reasons"].items():
        lines.append(
            f"**{bucket}** — {held['wagers']:,} wager(s) in "
            f"{held['distinct_sentences']:,} distinct sentence(s)"
        )
        lines.append("")
        shown = list(held["commonest"].items())[:6]
        for reason, count in shown:
            lines.append(f"- {count:,} x {reason}")
        unshown = held["distinct_sentences"] - len(shown)
        if unshown > 0:
            lines.append(f"- and {unshown:,} further sentence(s), not shown")
        lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# The run
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument(
        "--window",
        default=H.CARD_WINDOW.name,
        choices=sorted(H.WINDOWS),
        help=(
            "Which snapshot store to account for. `card` is the only window "
            "this lab's own card could have taken. The census gate is frozen "
            "against that store and refuses any other."
        ),
    )
    parser.add_argument(
        "--model",
        default=PLAYER_MODEL,
        help=(
            "`module:attribute` for the slate model. The default answers both "
            "halves; a team-only model puts every prop in `never_asked` and "
            "reports a census of a model nobody asked anything."
        ),
    )
    parser.add_argument(
        "--days",
        type=int,
        default=0,
        help=(
            "Price only the first N slate days. FOR WIRING ONLY, and it can "
            "never pass: the store's side of the identity is the whole store "
            "and a run that priced part of it accounts for part of it, so the "
            "gate refuses with the residual it found. That is the point of the "
            "flag — it exercises the pricer and shows the refusal. 0, the "
            "default, prices the whole store."
        ),
    )
    parser.add_argument("--chunksize", type=int, default=CHUNK_ROWS)
    parser.add_argument(
        "--progress",
        action="store_true",
        help=(
            "Print one line per slate day as it is priced. The whole store is "
            "140 slate days and over an hour of wall clock, and a run with no "
            "output is indistinguishable from a run that has hung."
        ),
    )
    parser.add_argument(
        "--no-write",
        action="store_true",
        help="Print the accounting and write no record.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    competition = competition_for(args.competition)
    processed = Path(args.processed_dir)
    store = H.store_path(competition, processed, H.WINDOWS[args.window])
    outputs = Path(args.output_dir)

    print(f"{competition.title} — prop accounting (a census, not a grading)")

    # ---- the run fingerprints the file it is about to read -----------------
    if not store.is_file():
        print(f"::error::{store} does not exist. Nothing was accounted for.",
              file=sys.stderr)
        return EXIT_INPUTS_ABSENT
    digest, size = store_digest(store)
    print(f"Store: {store} — {size:,} bytes, sha256 {digest}")

    # ---- receipt one: the store's own count, reconciled --------------------
    try:
        attribution = PC.assert_reconciles(
            store=store,
            roster=processed / competition.output_name("player_games", ".csv"),
            expected=processed / competition.output_name("player_census", ".json"),
            chunksize=int(args.chunksize),
        )
    except PC.WagerCountMismatch as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_DOES_NOT_RECONCILE
    print(attribution.report())
    if attribution.census.source_sha256 != digest:
        # Belt and braces: `assert_every_offered_prop_is_accounted` refuses on
        # this too, and it is said here as well because the two reads happen
        # eleven seconds apart over a symlink into a shared tree.
        print(
            "::error::the census counted a different file from the one this "
            f"run fingerprinted ({attribution.census.source_sha256} against "
            f"{digest}). Nothing was accounted for.",
            file=sys.stderr,
        )
        return EXIT_DOES_NOT_RECONCILE

    # ---- the props, and the tables the model reads -------------------------
    try:
        props = load_offered_props(store, chunksize=int(args.chunksize))
        team_games = card_matchups.load_team_games(competition, processed)
        player_games = card_matchups.load_player_games(competition, processed)
    except NothingToAccount as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_ACCOUNT
    except card_matchups.InputsAbsent as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_INPUTS_ABSENT

    days = sorted(str(d) for d in props["slate_date"].dropna().unique())
    if args.days:
        whole = len(days)
        days = days[: int(args.days)]
        props = props[props["slate_date"].astype(str).isin(set(days))]
        print(
            f"!! --days {args.days}: this run prices {len(days)} of the store's "
            f"{whole} slate day(s). The store's side of the identity is still "
            "the WHOLE store, so the gate refuses with the residual it finds "
            "and no record is written. This is NOT an accounting of the store."
        )
    print(
        f"{len(props):,} prop quote(s) over {len(days):,} slate day(s), "
        f"{props['event_id'].nunique():,} event(s)."
    )

    # ---- receipt two: what the run did with every one of them --------------
    try:
        model = PB.resolve_model(args.model)
    except PB.ModelNotWired as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NO_MODEL

    run = PC.RunDisposition(
        what=f"scripts/run_prop_accounting.py ({args.model})",
        store_sha256=digest,
    )
    tier_of_key: dict = {}
    refusals: Counter = Counter()
    rows_refused: list = []
    try:
        priced = PB.walk_forward(
            props,
            team_games,
            price_day=make_price_day(
                model,
                competition=competition,
                run=run,
                raw_dir=Path(args.raw_dir),
                tier_of_key=tier_of_key,
                refusals=refusals,
                rows_refused=rows_refused,
                progress=print if args.progress else None,
            ),
            frames={"player_history": player_games},
        )
    except PB.ModelNotWired as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NO_MODEL
    PB.assert_walk_forward(priced)
    print(
        f"Walk-forward: {len(priced):,} row(s) came back stamped, every one "
        "priced by a model cut to rows strictly earlier than its own night."
    )

    unparseable_rows = sum(count for _day, count in rows_refused)
    if unparseable_rows:
        print(
            f"!! {unparseable_rows:,} store row(s) on "
            f"{len(rows_refused):,} day(s) never became a wager, so this run "
            "cannot say what became of them. They are counted here and are "
            "filed in NO bucket; the identity below will refuse."
        )
        for reason, count in sorted(refusals.items(), key=lambda kv: -kv[1]):
            print(f"     {count:,} x {reason}")

    try:
        accounted = PC.assert_every_offered_prop_is_accounted(run)
    except PC.WagerCountMismatch as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_DOES_NOT_RECONCILE

    # ---- the counts --------------------------------------------------------
    print()
    print(accounted.report())
    print()
    print("Buckets, which are counts of wagers and nothing else:")
    for line in bucket_lines(run):
        print(line)
    print()
    print("Per tier, never pooled:")
    for line in tier_lines(run, tier_of_key):
        print(line)
    print()
    print("Why the model said nothing:")
    for line in reason_lines(run):
        print(line)

    record = record_of(
        accounted,
        tier_of_key=tier_of_key,
        model_spec=str(args.model),
        days=len(days),
        unparseable_rows=unparseable_rows,
        refusals=refusals,
    )
    if not args.no_write:
        outputs.mkdir(parents=True, exist_ok=True)
        record_path = outputs / competition.output_name("prop_accounting", ".json")
        report_path = outputs / competition.output_name("prop_accounting", ".md")
        record_path.write_text(
            json.dumps(record, indent=2, sort_keys=False) + "\n", encoding="utf-8"
        )
        report_path.write_text(render(record), encoding="utf-8")
        print()
        print(f"Wrote {record_path} and {report_path}.")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
