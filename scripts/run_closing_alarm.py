"""Read the model's settled leans against the closing line, per tier and market.

    PYTHONPATH=src python scripts/run_closing_alarm.py

Reads the forward ledger and the line-movement captures from the processed
directory and writes `data/outputs/cbb_closing_alarm.{json,md}`
(`reports/closing_alarm.py`). SOFT in Gameday Refresh: a run that cannot read
either input writes an empty report and the card is untouched. Spends no
credit, reads no new price, and withdraws nothing: a tripped alarm names a
candidate for withdrawal and stops there.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from cbb_betting_lab import forward_evidence, reachability
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR
from cbb_betting_lab.reports import closing_alarm
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
    record = closing_alarm.build_record(
        ledger, store, looks=looks, as_of=datetime.now(timezone.utc).date().isoformat()
    )
    json_path, md_path = closing_alarm.write(record, args.output_dir)
    print(
        f"Closing-line alarm: {record['leans']:,} settled lean(s), "
        f"{record['captures']:,} capture(s); "
        + ("ALARM on " + ", ".join(record["alarms"]) if record["alarms"] else "no alarm")
        + f". Wrote {json_path} and {md_path}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
