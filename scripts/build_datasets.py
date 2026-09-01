#!/usr/bin/env python3
"""Build the processed tables from the cached feeds. Spends nothing.

    PYTHONPATH=src python scripts/build_datasets.py --seasons 2019 2020 2021 2022 2023 2024 2025 2026
"""

from __future__ import annotations

import argparse
import json

from cbb_betting_lab.config import OUTPUTS_DIR
from cbb_betting_lab.data.build_datasets import build, possession_validation


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seasons", type=int, nargs="+", required=True)
    parser.add_argument("--allow-shrink", action="store_true")
    parser.add_argument("--validate-possessions", action="store_true")
    args = parser.parse_args(argv)

    written = build(tuple(args.seasons), allow_shrink=args.allow_shrink)
    skipped = written.pop("skipped", {}) if isinstance(written.get("skipped"), dict) else {}
    for name, rows in sorted(written.items()):
        print(f"  {name}: {rows:,} rows")

    # A skipped season is REPORTED, never silent. The 2026-27 season has a
    # schedule and no play-by-play until it is played, and a build that says
    # nothing about that looks identical to one that covered it.
    for table, seasons in sorted(skipped.items()):
        print(
            f"::warning::{table}: no cached feed for season(s) "
            f"{', '.join(str(s) for s in seasons)} — skipped, not failed. A "
            "season with a published schedule and no play-by-play has not been "
            "played yet."
        )
    if not written:
        print("::error::No table could be built for any requested season.")
        return 1

    if args.validate_possessions:
        checks = [possession_validation(s) for s in args.seasons]
        checks = [c for c in checks if c]
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        (OUTPUTS_DIR / "cbb_possession_validation.json").write_text(
            json.dumps(checks, indent=2) + "\n", encoding="utf-8"
        )
        print("\nPossession estimator against play-by-play:")
        for check in checks:
            print(
                f"  {check['season']}: estimator {check['mean_estimated']:.1f} vs "
                f"counted {check['mean_counted']:.1f} — gap "
                f"{check['mean_gap']:+.2f} (sd {check['gap_sd']:.2f}, "
                f"r={check['correlation']:.3f}) over {check['games']:,} games"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
