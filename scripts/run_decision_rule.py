"""Apply the April rule to the forward ledger as it stands.

    PYTHONPATH=src python scripts/run_decision_rule.py

Writes `data/outputs/cbb_decision_rule.{json,md}` (`reports/decision_rule.py`).
Before 2027-04-19 it is a dry run and says so on the page; on and after that
date it is the decision `docs/when_this_ends.md` declared. Spends no credit and
reads no new price.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from cbb_betting_lab import forward_evidence, reachability
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR
from cbb_betting_lab.reports import decision_rule
from cbb_betting_lab.reports.price_backtest import looks_from_ledger


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    args = parser.parse_args(argv)

    processed = Path(args.processed_dir)
    ledger = forward_evidence.read_ledger(processed / forward_evidence.LEDGER_FILENAME)
    store = reachability.load_store(CBB, processed)
    looks = looks_from_ledger(Path(args.output_dir) / "experiment_ledger.json")
    record = decision_rule.build_record(
        ledger, looks=looks, as_of=datetime.now(timezone.utc).date().isoformat(), store=store
    )
    json_path, md_path = decision_rule.write(record, args.output_dir)
    outcomes = ", ".join(f"{r['cut']}: {r['outcome']}" for r in record["tiers"])
    print(f"Decision rule ({'final' if record['final'] else 'dry run'}): {outcomes}. Wrote {json_path} and {md_path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
