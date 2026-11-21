"""Measure the card's spread bias against the market for today (decision 117).

    PYTHONPATH=src python scripts/run_spread_bias.py --as-of YYYY-MM-DD

Reads the forward ledger (`data/processed/cbb_forward_evidence.csv`, restored
from `card-feed`) and the carried table of shifts already applied
(`data/raw/cbb/layer_audit/spread_bias.json`), estimates each tier's mean
disagreement with the main-market spread over the fortnight before the day
(`models/spread_bias.py`), and records it under the day. The `spread_bias`
layer of the card reads it.

SOFT in Gameday Refresh: it reads no price from any provider, spends no
credit, and a run that cannot write leaves the newest recorded shift in force
for up to three days and then none at all.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from cbb_betting_lab.config import PROCESSED_DIR, RAW_DIR
from cbb_betting_lab.models import spread_bias as SB


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    args = parser.parse_args(argv)

    ledger_path = Path(args.processed_dir) / "cbb_forward_evidence.csv"
    if not ledger_path.is_file():
        print(f"No forward ledger at {ledger_path}; no spread bias measured.")
        return 2
    ledger = pd.read_csv(ledger_path, low_memory=False)
    payload = SB.update(SB.path(args.raw_dir), ledger, day=args.as_of)
    day = str(args.as_of)[:10]
    shifts = payload["by_day"][day]
    parts = ", ".join(
        f"{tier} {shifts[tier]:+.2f} pts over {payload['games'][tier]} game(s)" for tier in SB.TIERS
    )
    print(f"Spread bias for {day} (home margin, card minus market, taken out): {parts}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
