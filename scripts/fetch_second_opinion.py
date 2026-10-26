#!/usr/bin/env python3
"""Fetch the card's second opinion: a published ratings table, free.

    PYTHONPATH=src python scripts/fetch_second_opinion.py
    PYTHONPATH=src python scripts/fetch_second_opinion.py --season 2027 --as-of 2026-11-05

Spends no API credit and reads no credential. Writes
`data/raw/cbb/second_opinion/<season>.csv` in the columns
`card_factors.load_second_opinion` reads, with the names it could not place
beside it in `<season>.unresolved.json`.

Exit codes: 0 written and readable by the card; 1 the source could not be
fetched or parsed (nothing written, the previous table stands); 2 written but
under the `SECOND_OPINION_MIN_TEAMS` floor, so the card will not read it.
Every path is soft in the workflows: a card without a second opinion is a
card, and the log says which it was.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from cbb_betting_lab.config import RAW_DIR
from cbb_betting_lab.data import hoopr, second_opinion
from cbb_betting_lab.models import card_factors
from cbb_betting_lab.season import season_for_slate_date


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=None, help="hoopR season (its end year)")
    parser.add_argument("--as-of", default=None, help="the day the table is dated, YYYY-MM-DD")
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument(
        "--payload",
        default=None,
        help="read this file instead of fetching (tests and offline rehearsal)",
    )
    args = parser.parse_args(argv)

    today = datetime.now(ZoneInfo("America/New_York")).date()
    as_of = str(args.as_of or today.isoformat())[:10]
    season = int(args.season or season_for_slate_date(as_of) or 0)
    if not season:
        print(f"::error::No season for {as_of}.", file=sys.stderr)
        return 1
    raw_dir = Path(args.raw_dir)

    if args.payload:
        payload = Path(args.payload).read_bytes()
        url = str(args.payload)
    else:
        try:
            payload, url = second_opinion.fetch(season)
        except second_opinion.SecondOpinionError as exc:
            print(f"::warning::The second opinion could not be fetched: {exc}", file=sys.stderr)
            return 1
    try:
        table = second_opinion.parse(payload)
    except second_opinion.SecondOpinionError as exc:
        print(f"::warning::The second opinion from {url} could not be read: {exc}", file=sys.stderr)
        return 1

    schedule_path = hoopr.FEEDS["schedules"].path(season, raw_dir)
    if not schedule_path.is_file():
        print(
            f"::warning::No cached schedule for {season} at {schedule_path}, so the "
            "table's names cannot be resolved. Run scripts/fetch_cbb_data.py first.",
            file=sys.stderr,
        )
        return 1
    import pandas as pd

    schedule = pd.read_parquet(schedule_path)
    resolved, unresolved = second_opinion.resolve(table, schedule)
    path = second_opinion.write(
        resolved, raw_dir=raw_dir, season=season, as_of=as_of, unresolved=unresolved
    )
    count = int(resolved["team_id"].notna().sum())
    print(
        f"Second opinion: {len(table)} team(s) read from {url}, {count} resolved to "
        f"this lab's ids, {len(unresolved)} not. Wrote {path} dated {as_of}."
    )
    if unresolved:
        print("Unresolved: " + ", ".join(sorted(unresolved)[:40]) + (" …" if len(unresolved) > 40 else ""))
    if count < card_factors.SECOND_OPINION_MIN_TEAMS:
        print(
            f"::warning::{count} resolved teams is under the "
            f"{card_factors.SECOND_OPINION_MIN_TEAMS} the card needs; it will price "
            "without a second opinion.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
