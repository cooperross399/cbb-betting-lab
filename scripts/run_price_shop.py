"""List the books whose price beats the market's fair price, and grade the
earlier ones against the close (decision 91).

    PYTHONPATH=src python scripts/run_price_shop.py

Reads the line-movement captures (`data/processed/cbb_line_movement.csv`),
the allowlist, and, when present, the forward ledger for each game's tier.
Writes `data/outputs/cbb_price_shop.{json,md}` (`reports/price_shop.py`).
Runs after every capture in Line Movement and after settlement in Gameday
Refresh, SOFT in both. Spends no credit, reads no new price, picks nothing
and withdraws nothing.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from cbb_betting_lab import forward_evidence, reachability, staging_provider_policy
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR
from cbb_betting_lab.reports import price_shop
from cbb_betting_lab.reports.price_backtest import looks_from_ledger


def _tiers(processed: Path) -> dict[str, str]:
    path = processed / forward_evidence.LEDGER_FILENAME
    if not path.is_file():
        return {}
    ledger = forward_evidence.read_ledger(path)
    if ledger.empty or "tier" not in ledger.columns:
        return {}
    pairs = ledger[["event_id", "tier"]].dropna().astype(str).drop_duplicates("event_id")
    return dict(zip(pairs["event_id"], pairs["tier"]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    args = parser.parse_args(argv)

    processed = Path(args.processed_dir)
    store = reachability.load_store(CBB, processed)
    policy = staging_provider_policy.load()
    allowed = [m for m in price_shop.MARKETS if policy.allows(m)]
    looks = looks_from_ledger(Path(args.output_dir) / "experiment_ledger.json")
    record = price_shop.build_record(
        store, tiers=_tiers(processed), looks=looks, allowlisted=allowed,
        as_of=datetime.now(timezone.utc).isoformat(timespec="minutes"),
    )
    json_path, md_path = price_shop.write(record, args.output_dir)
    print(
        f"Price shop: {len(record['current']):,} side(s) clear the bar in the latest capture "
        f"({record['latest_capture'] or 'none'}); {record['captures']:,} capture(s) read; "
        f"markets {', '.join(allowed) or 'none allowlisted'}. Wrote {json_path} and {md_path}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
