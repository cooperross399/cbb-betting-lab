#!/usr/bin/env python3
"""Probe which markets the archive retains for this sport, and which are measurable.

    # Costs nothing, makes no request, needs no credential:
    PYTHONPATH=src python scripts/run_retention_probe.py

    # Spends credits:
    PYTHONPATH=src python scripts/run_retention_probe.py --live --credit-cap 50000

**Dry by default.** Without `--live` this script builds the stratified sample,
prints the achieved stratification and the pessimistic bound of the plan, and
stops. It opens no socket, reads no credential and spends nothing — its last
line says so in the exact words CI greps for.

The design, the declared measurability thresholds and every defect this guards
against are documented in `cbb_betting_lab/reports/retention_probe.py`. The two
rules that shape this script came out of the football lab's probe, which cost
7,280 credits:

1. Retention rolls up to the **market**, never the provider key.
2. The report re-renders from the run record, so improving its wording never
   costs credits twice. That is `scripts/rerender_retention_probe.py`, and it
   is why this script writes the record before it writes the report.

The cap is hard and is checked before every request against the **measured**
running total from `x-requests-last`, never against the estimate. And a live run
refuses to start when the cap is below the plan's pessimistic bound, because a
cap below the plan is a cap that starves it — and a starved fetch and an
unquoted market look identical in the reports.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from cbb_betting_lab.competitions import DEFAULT_COMPETITION_KEY, competition_for
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from cbb_betting_lab.providers.env_file import load_provider_env, redact
from cbb_betting_lab.providers.odds_api import (
    DEFAULT_REGIONS,
    OddsApiProvider,
    ProviderError,
    sufficient_quota,
)
from cbb_betting_lab.reports import retention_probe as RP


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    parser.add_argument("--season", type=int, default=RP.DEFAULT_SEASON)
    parser.add_argument(
        "--events-per-stratum", type=int, default=RP.DEFAULT_EVENTS_PER_STRATUM
    )
    parser.add_argument("--seed", type=int, default=RP.DEFAULT_SEED)
    parser.add_argument(
        "--max-events",
        type=int,
        default=0,
        help="Truncate the plan, one pass across every cell before a second.",
    )
    parser.add_argument(
        "--tiers",
        default="1,2,3",
        help="Market tiers to ask for. Futures are never per-event.",
    )
    parser.add_argument("--chunk-size", type=int, default=RP.MARKET_CHUNK_SIZE)
    parser.add_argument(
        "--credit-cap",
        type=int,
        default=RP.DEFAULT_CREDIT_CAP,
        help="Hard. Checked before every request against the measured total.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Actually spend credits. Without this nothing is requested.",
    )
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help=(
            "Start even though the cap is below the plan's pessimistic bound. "
            "The report then says on its own front page that it may have been "
            "truncated."
        ),
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Re-ask for responses already cached. Spends credits again.",
    )
    parser.add_argument("--skip-quota-check", action="store_true")
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument(
        "--preview-report",
        default="",
        help=(
            "Dry run only: render the empty record to this path, so the "
            "report's wording can be reviewed without spending anything."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    competition = competition_for(args.competition)
    tiers = tuple(
        int(t) for t in str(args.tiers).split(",") if str(t).strip().isdigit()
    )
    keys = RP.probe_provider_keys(tiers or (1, 2, 3))

    try:
        team_games, schedule, tier_table, index = RP.load_inputs(
            processed_dir=Path(args.processed_dir),
            raw_dir=Path(args.raw_dir),
            competition=competition,
            season=int(args.season),
        )
        candidates, census = RP.candidate_events(
            team_games,
            schedule,
            tier_table,
            competition=competition,
            season=int(args.season),
        )
    except RP.ProbeError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2

    if not candidates:
        print(
            f"::error::No countable {args.season} game could be placed in a "
            "stratum. Nothing was requested.",
            file=sys.stderr,
        )
        return 2

    plan = RP.stratified_sample(
        candidates,
        events_per_stratum=int(args.events_per_stratum),
        seed=int(args.seed),
        max_events=int(args.max_events),
    )
    regions = len([r for r in DEFAULT_REGIONS.split(",") if r.strip()]) or 1
    bound = RP.pessimistic_bound(plan.events, keys, regions=regions)

    print(f"{competition.title} — historical retention probe")
    print(tier_table.summary_line())
    print(
        f"Population: {census.get('candidates', 0):,} countable {args.season} "
        f"games placed in {len(plan.strata)} non-empty (tier, month, tip "
        "window) cells."
    )
    for reason, count in sorted(census.items()):
        if reason not in {"candidates", "countable_home_rows"}:
            print(f"  excluded — {reason}: {count:,}")
    print(
        f"Plan: {len(plan.events)} event(s), {len(keys)} provider key(s) in "
        f"tier(s) {','.join(str(t) for t in tiers)}, chunked "
        f"{len(RP.market_chunks(keys, size=int(args.chunk_size)))} ways at "
        f"{args.chunk_size} keys."
    )
    if plan.balanced:
        print(
            f"Stratification: balanced — every one of the {len(plan.strata)} "
            f"cells got its target of {args.events_per_stratum}."
        )
    else:
        print(
            f"Stratification: NOT balanced — {len(plan.underfilled)} of "
            f"{len(plan.strata)} cells came up short. They are named in the "
            "report; an unbalanced probe that reports itself as balanced is "
            "worse than no probe."
        )
    print(
        f"Pessimistic bound: {bound:,} credits "
        f"({len(plan.events)} events x {len(keys)} keys x {regions} regions x "
        "10 for history, plus the slate listings). Real spend will come in "
        "under it — an asked-for market nobody quotes costs nothing."
    )
    print(f"Credit cap: {args.credit_cap:,}.")

    if not args.live:
        if bound > int(args.credit_cap):
            print(
                f"A live run would refuse to start: the bound {bound:,} "
                f"exceeds the cap {args.credit_cap:,}. Raise --credit-cap to "
                f"at least {bound:,}, cut the plan with --max-events, or pass "
                "--allow-partial and accept a report that says it may have "
                "been truncated."
            )
        if args.preview_report:
            record = RP.dry_run_record(
                competition=competition,
                plan=plan,
                keys=keys,
                chunk_size=int(args.chunk_size),
                credit_cap=int(args.credit_cap),
                regions=DEFAULT_REGIONS,
                sport_key=competition.provider_sport_key,
                generated_at="",
            )
            target = RP.write_report(record, Path(args.preview_report))
            print(f"Wrote a preview of the report's wording to {target}.")
        # CI greps for this phrase at the end of the last line, which is why
        # there is no full stop after it.
        print(
            "Dry run. Nothing was requested, no credential was read, and "
            f"{RP.NOTHING_WAS_SPENT}"
        )
        return 0

    load_provider_env()
    provider = OddsApiProvider(competition)
    if not args.skip_quota_check:
        try:
            headers = provider.quota()
        except ProviderError as exc:
            print(redact(f"::error::{exc}"), file=sys.stderr)
            return 2
        enough, note = sufficient_quota(headers, int(args.credit_cap))
        print(note)
        if not enough:
            print("::error::Refusing to start. Nothing was fetched.", file=sys.stderr)
            return 1

    try:
        record = RP.probe(
            plan=plan,
            provider=provider,
            index=index,
            provider_keys=keys,
            credit_cap=int(args.credit_cap),
            cache_dir=RP.cache_dir_for(competition, Path(args.raw_dir)),
            competition=competition,
            chunk_size=int(args.chunk_size),
            use_cache=not args.no_cache,
            allow_partial=bool(args.allow_partial),
            generated_at=datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        )
    except RP.ProbeError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    record_target = RP.write_record(record, RP.record_path(competition, output_dir))
    report_target = RP.write_report(record, RP.report_path(competition, output_dir))

    print(f"Wrote {record_target}")
    print(f"Wrote {report_target}")
    counts: dict[str, int] = {}
    for entry in record["markets"]:
        counts[entry["verdict"]] = counts.get(entry["verdict"], 0) + 1
    for verdict in (
        RP.Retention.RETAINED_AND_MEASURABLE,
        RP.Retention.RETAINED_BUT_THIN,
        RP.Retention.NOT_RETAINED,
        RP.Retention.NOT_PROBED,
    ):
        print(f"  {verdict.value}: {counts.get(verdict.value, 0)}")
    print(
        f"{record['credits_spent']:,} credit(s) spent against a cap of "
        f"{record['credit_cap']:,}; the pessimistic bound was "
        f"{record['pessimistic_bound']:,}."
    )
    if not record["completed"]:
        print(
            "::warning::The run did not complete. Every market it never "
            "finished asking about reads NOT_PROBED, never NOT_RETAINED — a "
            "starved fetch and an unquoted market look identical, and this is "
            "the guard that tells them apart."
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
