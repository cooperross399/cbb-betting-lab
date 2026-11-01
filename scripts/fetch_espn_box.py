"""Fill the current season's results from ESPN where hoopR has not published.

    PYTHONPATH=src python scripts/fetch_espn_box.py
    PYTHONPATH=src python scripts/fetch_espn_box.py --season 2027 --through 2026-11-03

Run after `scripts/fetch_cbb_data.py` and before `scripts/build_datasets.py`.
Reads hoopR's cached schedule and team box for the season, then fetches from
ESPN every completed game since hoopR's last published date (or since the
season's first scheduled game when hoopR has published nothing) that hoopR
does not hold. Writes `data/raw/cbb/espn_box/` (`data/espn_box.py`). Free,
keyless, no credit.

Exit codes: 0 done (including "nothing to fetch"); 1 no schedule for the
season, so the window is unknown. A failed game is reported and retried on the
next run; it does not fail the step.
"""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from cbb_betting_lab.config import RAW_DIR
from cbb_betting_lab.data import espn_box, hoopr
from cbb_betting_lab.season import season_for_slate_date

#: Days re-read before hoopR's last published date, for games it filed late.
OVERLAP_DAYS = 3


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=None)
    parser.add_argument("--through", default=None, help="last Eastern date to read, YYYY-MM-DD")
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    args = parser.parse_args(argv)

    today = datetime.now(ZoneInfo("America/New_York")).date()
    through = str(args.through or today.isoformat())[:10]
    season = int(args.season or season_for_slate_date(through) or 0)
    raw_dir = Path(args.raw_dir)
    try:
        schedule = hoopr.load("schedules", season, raw_dir=raw_dir, columns=["game_date"])
    except hoopr.FeedError as exc:
        print(f"::warning::No schedule for {season}: {exc}", file=sys.stderr)
        return 1
    dates = sorted(str(d)[:10] for d in schedule["game_date"].dropna())
    if not dates:
        print(f"::warning::The {season} schedule carries no dates.", file=sys.stderr)
        return 1
    first = dates[0]

    published: set[int] = set()
    try:
        box = hoopr.load("team_box", season, raw_dir=raw_dir, columns=["game_id", "game_date"])
        published = set(box["game_id"].astype(int))
        if len(box):
            last = date.fromisoformat(str(box["game_date"].max())[:10])
            first = max(first, (last - timedelta(days=OVERLAP_DAYS)).isoformat())
    except hoopr.FeedError:
        pass

    if first > through:
        print(f"ESPN supplement: the {season} season has no game on or before {through}.")
        return 0
    report = espn_box.supplement(
        season, first_day=first, last_day=through, published_ids=published, raw_dir=raw_dir
    )
    print(report.line())
    if report.failed:
        print(f"::warning::{len(report.failed)} ESPN request(s) failed; retried next run.", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
