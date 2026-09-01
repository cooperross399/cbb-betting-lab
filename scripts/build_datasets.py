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
    for name, rows in sorted(written.items()):
        print(f"  {name}: {rows:,} rows")

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
