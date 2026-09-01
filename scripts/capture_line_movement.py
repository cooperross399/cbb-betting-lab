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

## An empty board is not a fault

There is no college basketball between April and November. A capture that
returns nothing in September has observed that correctly, and the run says so
rather than failing. **A degraded run and an empty slate must never look the
same**, so a fetch that *errors* is degraded and a fetch that *succeeds with no
events* is empty, and the two are reported differently.
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
from cbb_betting_lab.providers.odds_api import OddsApiProvider, Spend


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
        try:
            payloads = provider.fetch_bulk(
                M.bulk_provider_keys(), spend=spend, credit_cap=args.credit_cap
            )
        except Exception as error:  # noqa: BLE001 - degrade, never empty
            # A failed fetch degrades rather than empties. Writing an empty
            # capture here would record "the board was empty at 19:04", which
            # is a claim about the market rather than about the fetch, and
            # every later survival number would be computed against it.
            print(f"::error::The board fetch failed: {error}")
            print("Nothing was written. The previous captures stand.")
            return 4

        staged = LM.stage_board(payloads, captured_at=captured_at, competition=CBB)
        if staged.empty:
            print(
                f"The board returned no wired quotes at {captured_at}. "
                "There is no college basketball between April and November, so "
                "this is an observation and not a fault. Nothing was written: "
                "an empty capture would later read as every price vanishing."
            )
            print(f"Credits spent: {spend.credits_spent:,}")
            return 0

        written = LM.append_capture(staged, path)
        print(
            f"Captured {len(staged):,} quotes at {captured_at} across "
            f"{staged['event_id'].nunique():,} events and "
            f"{staged['book'].nunique()} books. {written:,} new rows."
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
