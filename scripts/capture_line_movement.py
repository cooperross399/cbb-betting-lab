#!/usr/bin/env python3
"""Capture the board as it stands, and record whether the last one survived.

    # Costs nothing, makes no request:
    PYTHONPATH=src python scripts/capture_line_movement.py

    # Spends credits (6 per capture for the featured board, whole slate):
    PYTHONPATH=src python scripts/capture_line_movement.py --live

**Dry by default.** Without `--live` it reports the existing store and
re-renders the report, opening no socket and reading no credential.

## Why this runs before the season, and why it is cheap

Cooper's brief puts this in the first week of the build rather than late,
because it is the instrument that decides whether any finding is real money.
It also needs history of its own: survival is a statement about a quote at the
*next* capture, so a store with one capture in it can say nothing at all.

It is affordable at any cadence because the featured board comes from the
**bulk** endpoint: 3 keys x 2 regions = **6 credits for the entire slate**,
whatever its size. On a 200-game opening Monday that is 200 games for 6
credits. Per-event ladders are not captured here; they would cost 96 credits a
game a capture, and the reachability question is answerable on the featured
board — which is also the board a card can actually bet.

## An empty board is not a fault, and an empty ACCOUNT is not an empty board

There is no college basketball between April and November. A capture that
returns nothing in September has observed that correctly, and the run says so
rather than failing. **A degraded run and an empty slate must never look the
same**, so a fetch that *errors* is degraded and a fetch that *succeeds with no
events* is empty, and the two are reported differently.

There is a third state, and for the whole of this build this script could not
see it. When the account empties the provider does not fail: it answers, with
a payload that carries no bookmakers. `stage_board` then returns nothing, and
this script used to print *"There is no college basketball between April and
November"* over it and exit 0 — our own wallet published as a fact about the
market, in the one store whose entire purpose is saying which quotes were
reachable. The partly-answered case is worse than the empty one, because it
*writes*: the events the balance ran out on come back unpriced, and at the next
capture every quote in them reads as **gone**, which is movement that did not
happen and a survival rate computed against it.

So this script now does what the other three paid-data paths do. It reads the
free `/v4/sports` balance before the first billed request and refuses to start
a run its cap cannot cover; it re-reads the measured balance on the response in
hand against a floor of `bulk keys x regions` — the widest single request it
makes — and on a stop it writes **nothing** and exits 7; and an empty board is
called an observation about the market only when the balance was measured and
healthy. When the provider reported no balance at all, the run says that rather
than naming the calendar. No number is ever assumed: `remaining_credits()`
returns `None` for "we do not currently know", and `None` is not a pass.

## Exit codes

`0` captured, or observed an empty board with the balance watched. `3` no
credential. `4` the board fetch failed; nothing was written and the previous
captures stand. `5` the free pre-flight could not be read at all. `6` the
pre-flight refused: the account cannot cover this run's cap. `7` the measured
balance fell below the floor on the response in hand; nothing was written.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from cbb_betting_lab import line_movement as LM
from cbb_betting_lab import markets as M
from cbb_betting_lab import stores
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR
from cbb_betting_lab.providers.odds_api import (
    MOVEMENT_STARVATION,
    OddsApiProvider,
    ProviderError,
    Spend,
    sufficient_quota,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--credit-cap",
        type=int,
        default=200,
        help="Generous against a 6-credit bulk call; the cap is a backstop, "
        "not a budget.",
    )
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    args = parser.parse_args(argv)

    path = LM.store_path(CBB, Path(args.processed_dir))
    store = stores.read_store(path, for_append=True)
    captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    if args.live:
        if not os.environ.get("CBB_ODDS_API_KEY"):
            print("::error::CBB_ODDS_API_KEY is not set. Nothing was requested.")
            return 3
        provider = OddsApiProvider(CBB)
        spend = Spend()
        bulk_keys = M.bulk_provider_keys()

        # REFUSAL ONE, and it is free. `/v4/sports` costs nothing and answers
        # the only question that matters before a billed request: can the
        # account pay for this run at all. `why` has no default, so this script
        # states what ITS starvation costs — a reachability store that records
        # prices as withdrawn when it was the wallet that went — rather than
        # inheriting the nightly card's sentence about a biased ledger.
        try:
            headers = provider.quota()
        except ProviderError as error:
            print(f"::error::The free quota reading could not be taken: {error}")
            print("Nothing was requested and nothing was written.")
            return 5
        enough, note = sufficient_quota(
            headers, args.credit_cap, why=MOVEMENT_STARVATION
        )
        print(note)
        if not enough:
            print("::error::Refusing to start. Nothing was fetched or written.")
            return 6

        # The widest single request this script can make. The bulk call is
        # billed `markets x regions` whatever the slate's size, and it is the
        # only billed call here — so a balance at or above this could still
        # have paid for the response in hand in full. A floor below it lets the
        # run be billed for a partial answer, and a partial answer is exactly
        # the board whose silence is unreadable.
        regions = len([r for r in provider.regions.split(",") if r.strip()]) or 1
        floor = len(bulk_keys) * regions

        try:
            payloads = provider.fetch_bulk(
                bulk_keys, spend=spend, credit_cap=args.credit_cap
            )
        except Exception as error:  # noqa: BLE001 - degrade, never empty
            # A failed fetch degrades rather than empties. Writing an empty
            # capture here would record "the board was empty at 19:04", which
            # is a claim about the market rather than about the fetch, and
            # every later survival number would be computed against it.
            print(f"::error::The board fetch failed: {error}")
            print("Nothing was written. The previous captures stand.")
            return 4

        # REFUSAL TWO, read from THIS response and no earlier one. `None` is
        # the third answer — the provider did not say — and it is not a pass:
        # it disqualifies the calendar sentence below rather than the capture.
        remaining = spend.remaining_credits()
        if remaining is not None and remaining < floor:
            print(
                f"::error::STOPPED ON QUOTA. The provider reports "
                f"{remaining:,} credit(s) remaining, below this capture's "
                f"floor of {floor:,} — the cost of the one request it makes. "
                "NOTHING WAS WRITTEN. A board answered on an emptied account "
                "comes back without bookmakers on it, and this store cannot "
                "tell that apart from a board no one hung: written down, the "
                "events it could not pay for would read at the next capture as "
                "prices that vanished. Top the balance up and capture again.",
                file=sys.stderr,
            )
            print(f"Credits spent: {spend.credits_spent:,}")
            return 7

        staged = LM.stage_board(payloads, captured_at=captured_at, competition=CBB)
        if staged.empty:
            if remaining is None:
                # The balance was never reported, so the emptiness cannot be
                # attributed to the market. Saying which of the two it was is
                # not available to this run, and saying the calendar would be
                # stating the one we did not measure.
                print(
                    f"The board returned no wired quotes at {captured_at}, and "
                    "the provider reported no remaining balance on that "
                    "response. This run cannot say whether the board was empty "
                    "or the account was: an emptied account is answered with a "
                    "payload carrying no bookmakers, which is what this looks "
                    "like. Nothing was written, and this absence may not be "
                    "read as a statement about the market."
                )
                print(f"Credits spent: {spend.credits_spent:,}")
                return 0
            print(
                f"The board returned no wired quotes at {captured_at}, with "
                f"{remaining:,} credit(s) measured on the account — so this is "
                "the market and not the wallet. There is no college basketball "
                "between April and November, so this is an observation and not "
                "a fault. Nothing was written: an empty capture would later "
                "read as every price vanishing."
            )
            print(f"Credits spent: {spend.credits_spent:,}")
            return 0

        written = LM.append_capture(staged, path)
        print(
            f"Captured {len(staged):,} quotes at {captured_at} across "
            f"{staged['event_id'].nunique():,} events and "
            f"{staged['book'].nunique()} books. {written:,} new rows."
        )
        if remaining is None:
            # Quotes came back, so this capture is real. What it cannot say is
            # whether it is COMPLETE: the balance on this response was not
            # reported, so an event that came back unpriced could be one no
            # book hung or one the account stopped paying for.
            print(
                "The provider reported no remaining balance on that response, "
                "so the breaker had nothing to watch. An event captured "
                "without quotes here may be an unhung market or an emptied "
                "account; this run cannot tell them apart."
            )
        print(f"Credits spent: {spend.credits_spent:,}")
        store = stores.read_store(path, for_append=True)
    else:
        print(
            f"Dry run. Nothing was requested, no credential was read, "
            f"and no credit was spent"
        )

    # Survival, and the report, from whatever the store holds.
    series = LM.survival_series(store)
    if series:
        print("\nSurvival between consecutive captures:")
        for s in series[-5:]:
            print(f"  {s.line()}")
    elif not store.empty:
        print(
            "\nOnly one capture exists, so nothing can be said about survival "
            "yet. Survival is a statement about a quote at the NEXT capture."
        )

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = out / CBB.output_name("line_movement", ".md")
    report.write_text(LM.render(store, competition=CBB), encoding="utf-8")
    print(f"\nWrote {report}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
