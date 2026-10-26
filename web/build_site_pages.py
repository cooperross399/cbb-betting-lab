#!/usr/bin/env python3
"""Write record.json and tracker.json from the frozen boards and their finals.

    python web/build_site_pages.py --data dist/data

Runs after `settle_results.py` in Publish Board, over the same `history/`
folder. Reads finals from the settled days when they were kept, else from
the finals cache, else from the scoreboard (cached once a day is complete).
Fetches no price, spends no credit, places no bet. A day whose finals cannot
be read is left out of this build and asked for again next time; nothing
here fails the publish.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default="dist/data")
    ap.add_argument("--date", default="", help="Today (default: today in New York).")
    ap.add_argument("--no-fetch", action="store_true", help="Read only what is on disk; ask no scoreboard.")
    args = ap.parse_args(argv)
    today = date.fromisoformat(args.date) if args.date else datetime.now(ET).date()
    spec = importlib.util.spec_from_file_location("site_pages", Path(__file__).with_name("site_pages.py"))
    site_pages = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(site_pages)
    summary = site_pages.write_record_pages(Path(args.data), today, fetch=not args.no_fetch)
    print(
        f"record pages through {today}: {summary['games']} graded games over {summary['nights']} nights, "
        f"{summary['bets']} bets and {summary['opinions']} opinions. No odds were fetched, no credit was spent, "
        "and no bet was placed."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
