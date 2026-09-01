#!/usr/bin/env python3
"""Fetch the free source feeds and cache them, hashed.

    PYTHONPATH=src python scripts/fetch_cbb_data.py --seasons 2023 2024 2025 2026 2027

Spends no API credits — these are public files. A failed feed **degrades rather
than empties**: the run reports what it could not get and leaves the previous
cache in place, because in this sport a partial fetch looks exactly like a
light slate.
"""

from __future__ import annotations

import argparse
import sys

from cbb_betting_lab.data import hoopr


DEFAULT_FEEDS = ("schedules", "team_box", "player_box", "pbp")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", type=int, nargs="+", required=True)
    parser.add_argument("--feeds", nargs="+", default=list(DEFAULT_FEEDS))
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--allow-shrink",
        action="store_true",
        help="Deliberate override for a feed that legitimately got smaller. "
             "Recorded in the manifest when used.",
    )
    args = parser.parse_args(argv)

    failures: list[str] = []
    not_yet: list[str] = []
    restated: list[str] = []
    for feed in args.feeds:
        for season in args.seasons:
            spec = hoopr.FEEDS.get(feed)
            if spec and season < spec.first_season:
                print(f"  {feed} {season}: skipped, no asset before {spec.first_season}")
                continue
            try:
                entry = hoopr.fetch(
                    feed, season, force=args.force, allow_shrink=args.allow_shrink
                )
            except hoopr.NotPublishedYet:
                # Expected before a season's first game. Not a fault, and not
                # counted toward the degraded verdict.
                print(f"  {feed} {season}: not published upstream yet")
                not_yet.append(f"{feed}/{season}")
                continue
            except hoopr.FeedError as exc:
                print(f"  {feed} {season}: FAILED — {exc}", file=sys.stderr)
                failures.append(f"{feed}/{season}")
                continue
            flag = "  RESTATED" if entry.get("restated") else ""
            print(
                f"  {feed} {season}: {entry['rows']:,} rows, "
                f"{entry['columns']} cols, {entry['bytes'] / 1e6:.1f} MB, "
                f"sha {entry['sha256'][:12]}{flag}"
            )
            if entry.get("restated"):
                restated.append(f"{feed}/{season}")

    if restated:
        print(
            f"\n::warning::{len(restated)} cached asset(s) were RESTATED "
            f"upstream: {', '.join(restated)}. Upstream rebuilds the whole "
            "current-season file every night and overwrites in place. A "
            "restatement that moves a row already settled against is how a "
            "walk-forward test quietly stops being one — re-derive anything "
            "fitted on these seasons."
        )
    if not_yet:
        print(
            f"\n{len(not_yet)} asset(s) are not published upstream yet: "
            f"{', '.join(not_yet)}. Expected for a season that has not started."
        )
    if failures:
        print(
            f"\n::warning::{len(failures)} feed(s) failed: "
            f"{', '.join(failures)}. The previous cache is untouched and this "
            "run is DEGRADED. A degraded run is marked, never published as a "
            "thin slate."
        )
        return 1
    print("\nEvery requested feed is cached and hashed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
