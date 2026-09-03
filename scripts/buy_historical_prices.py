#!/usr/bin/env python3
"""Buy historical prices, in the brief's priority order, under a hard cap.

    # Costs nothing, makes no request, needs no credential:
    PYTHONPATH=src python scripts/buy_historical_prices.py --waves core_team

    # Spends credits:
    PYTHONPATH=src python scripts/buy_historical_prices.py \
        --waves core_team --live --credit-cap 1200000

**Dry by default.** Without `--live` this builds the plan, prints what each
wave would cost and which provider keys are refused for falling before their
archive cut-off, and stops. It opens no socket, reads no credential and spends
nothing.

## Why waves, and why this order

The full catalogue costs 35,173,680 credits against a balance of 4,992,714 —
seven times everything the account will ever hold. So the purchase is
prioritised rather than complete, in the order the brief names: **core team
markets across every season first, then ladders, then props, then futures.**
`docs/credit_cost.md` has the arithmetic and the reasoning.

Each wave is bought by its own dispatch. That is deliberate: a wave is a
decision about spending a large fraction of a finite balance, and running four
of them from one invocation would make the third and fourth happen as a
side-effect of the first.

## The cap is checked against what was spent, not what was predicted

The NHL lab capped a run at 200,000 and it spent **289,984** — because the
estimate counted the market keys *asked for* while the provider bills per
market *returned*, and every alternate ladder bills on its own. Both the code
and its test asserted the cap "cannot be breached".

So the cap here is enforced against the **measured** running total read from
the `x-requests-last` response header, before every request. The estimate is
still printed, still pessimistic, and is never the gate.

## A partial buy is a sample, not a prefix

Events are bought in an order whose every prefix is spread across the season
and across conference tiers — `stratified_order()`. A buy that stops halfway
through must leave a *sample* of the season behind it, not its first half. Book
coverage differs by tier and by month, and a prefix-ordered partial buy would
measure the high-major November board and call it college basketball.

## Resuming costs nothing

Every response is cached raw under `data/raw/cbb/historical_<window>/`, keyed
by event and by a fingerprint of the market chunk. A re-run reads the cache and
re-requests only what is missing, so an interrupted purchase resumes rather
than restarts, and `--rebuild` re-derives the price store from the cache
without a single request.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from cbb_betting_lab.providers import historical as H
from cbb_betting_lab.providers.odds_api import OddsApiProvider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--waves",
        default="core_team",
        help="Comma-separated wave names, in order: "
        + ", ".join(w.name for w in H.WAVES),
    )
    parser.add_argument("--credit-cap", type=int, default=1_200_000)
    parser.add_argument("--chunk-size", type=int, default=8)
    parser.add_argument("--max-events-per-segment", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260901)
    parser.add_argument("--window", default="card", choices=sorted(H.WINDOWS))
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Re-derive the price store from the cached responses. No requests.",
    )
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    args = parser.parse_args(argv)

    window = H.WINDOWS[args.window]
    wave_names = tuple(w.strip() for w in args.waves.split(",") if w.strip())
    waves = [H.wave_for(name) for name in wave_names]

    blocked = [w for w in waves if not w.buyable]
    for wave in blocked:
        # Not a pass, an avoid, or a no-value call. A wave that cannot be
        # bought says why, in the report and here.
        print(f"::warning::Wave '{wave.name}' is not buyable: {wave.blocked_reason}")
    waves = [w for w in waves if w.buyable]
    if not waves:
        print("Every requested wave is blocked. Nothing to plan.")
        return 1

    seasons = sorted({s for wave in waves for s in wave.seasons})
    print(
        f"{CBB.title} — historical purchase\n"
        f"Waves: {', '.join(w.name for w in waves)}. Seasons: "
        f"{', '.join(str(s) for s in seasons)}. Window: {window.name} "
        f"(T-{window.minutes_before_tip}m)."
    )

    events_by_season, indexes, _ = H.load_events(
        seasons=seasons,
        processed_dir=Path(args.processed_dir),
        raw_dir=Path(args.raw_dir),
        window=window,
    )
    if not any(events_by_season.values()):
        print("::error::No countable events. Run build_datasets.py first.")
        return 2

    plan = H.build_plan(
        events_by_season,
        waves=[w.name for w in waves],
        window=window,
        seed=args.seed,
        max_events_per_segment=args.max_events_per_segment,
    )
    # Refuses a plan asking for a key before its archive cut-off. Asking for a
    # market that could not exist and recording the silence as absence is how a
    # lab concludes "not retained" about a market the provider never had.
    H.guard_cutoffs(plan)

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cache_dir = H.cache_dir_for(CBB, Path(args.raw_dir), window)

    if args.rebuild:
        # Three values, not two: rows, census, and the events that had at
        # least one cached response. The two-value unpack here had never been
        # exercised, because nothing ran `--rebuild` until the purchase turned
        # out not to write its own store.
        rows, census, reached = H.rebuild_from_cache(
            plan=plan, cache_dir=cache_dir, indexes=indexes,
            chunk_size=args.chunk_size,
        )
        target = H.store_path(CBB, Path(args.processed_dir), window)
        written = H.append_prices(rows, target, window=window)
        print(
            f"Rebuilt {written:,} price rows from {len(reached):,} cached "
            f"events into {target.name}. No request was made and no credit "
            "was spent."
        )
        if census:
            print("\nWhat did not become a row:")
            for reason, count in sorted(census.items(), key=lambda kv: -kv[1]):
                print(f"  {count:>9,}  {reason}")
        if not rows:
            # An empty rebuild is the signature of a cache that did not
            # survive, and it must not read as a purchase with nothing in it.
            print(
                "\n::warning::No cached response staged a single row. Either "
                f"the cache under {cache_dir} is empty, or every response in "
                "it failed to stage. Those are different faults and the census "
                "above tells them apart: an empty census means an empty cache."
            )
        return 0

    if not args.live:
        record = H.dry_run_record(
            competition=CBB, plan=plan, credit_cap=args.credit_cap,
            chunk_size=args.chunk_size, regions=str(plan.segments[0].regions if plan.segments else 2),
            sport_key=CBB.provider_sport_key,
            population_by_season=events_by_season, generated_at=generated_at,
        )
        H.write_record(record, H.record_path(CBB, Path(args.output_dir)))
        print(H.render(record))
        print(
            "\nDry run. Nothing was requested, no credential was read, "
            "and no credit was spent"
        )
        return 0

    if not os.environ.get("CBB_ODDS_API_KEY"):
        print("::error::CBB_ODDS_API_KEY is not set. Nothing was requested.")
        return 3

    provider = OddsApiProvider(CBB)
    record = H.buy(
        plan=plan, provider=provider, indexes=indexes,
        credit_cap=args.credit_cap, cache_dir=cache_dir, competition=CBB,
        chunk_size=args.chunk_size, generated_at=generated_at,
        population_by_season=events_by_season,
    )
    H.write_record(record, H.record_path(CBB, Path(args.output_dir)))
    H.write_report(record, H.report_path(CBB, Path(args.output_dir)))
    print(H.render(record))
    return 0


if __name__ == "__main__":
    sys.exit(main())
