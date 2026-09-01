#!/usr/bin/env python3
"""Rebuild the retention report from the cached run record. Touches no network.

    PYTHONPATH=src python scripts/rerender_retention_probe.py

This exists because of the football lab, whose probe cost **7,280 credits** and
whose report was written by the same code that spent them. Every improvement to
a sentence, every column somebody wanted differently, every re-ordering of a
table meant either re-running the probe or hand-editing a generated file — and a
hand-edited generated file survives exactly one re-run.

So the probe writes a **run record** holding every count it made, and
`reports.retention_probe.render` is a pure function of that record: no clock, no
network, no randomness. This script reads the record and writes the markdown.
**It makes no request, needs no credential, and cannot spend a credit** — which
is also what makes it safe to run in CI on every push, so a report that has
drifted from its record fails the build.

`tests/test_retention_probe.py::test_the_report_re_renders_byte_identically_from_the_run_record`
holds the two together.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cbb_betting_lab.competitions import DEFAULT_COMPETITION_KEY, competition_for
from cbb_betting_lab.config import OUTPUTS_DIR
from cbb_betting_lab.reports import retention_probe as RP


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument(
        "--record",
        default="",
        help="Run record to render. Defaults to the one beside the report.",
    )
    parser.add_argument(
        "--report",
        default="",
        help="Where to write the markdown. Defaults beside the record.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Do not write. Exit non-zero when the report on disk differs from "
            "what the record renders to — which is a report edited by hand, "
            "and a hand-edited generated file survives exactly one re-run."
        ),
    )
    args = parser.parse_args(argv)

    competition = competition_for(args.competition)
    output_dir = Path(args.output_dir)
    record_target = (
        Path(args.record) if args.record else RP.record_path(competition, output_dir)
    )
    report_target = (
        Path(args.report) if args.report else RP.report_path(competition, output_dir)
    )

    try:
        record = RP.read_record(record_target)
        rendered = RP.render(record)
    except RP.ProbeError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2

    if args.check:
        existing = (
            report_target.read_text(encoding="utf-8")
            if report_target.is_file()
            else ""
        )
        if existing != rendered:
            print(
                f"::error::{report_target} does not match what "
                f"{record_target} renders to. Re-render it rather than editing "
                "it: the report is a pure function of the record, and an edit "
                "here is lost the next time anybody re-renders.",
                file=sys.stderr,
            )
            return 1
        print(f"{report_target} matches its run record.")
    else:
        RP.write_report(record, report_target)
        print(f"Wrote {report_target} from {record_target}.")

    spent = int(record.get("credits_spent", 0))
    print(
        f"The run being rendered spent {spent:,} credit(s) under a cap of "
        f"{int(record.get('credit_cap', 0)):,}; re-rendering it spent none."
    )
    # Same phrase the dry run ends on, and CI greps for it at end of line.
    print(f"No network was touched and {RP.NOTHING_WAS_SPENT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
