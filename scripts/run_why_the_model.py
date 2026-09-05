#!/usr/bin/env python3
"""Re-render `docs/why_the_model_does_or_does_not_have_an_edge.md` from records.

    PYTHONPATH=src python scripts/run_why_the_model.py --competition cbb \
        --splice-into docs/why_the_model_does_or_does_not_have_an_edge.md

That is how `scripts/run_weekly_loop.py` invokes it, beside the claims report
and for the same reason. **It touches no network, needs no credential and
cannot spend a credit.**

## The defect it exists to end

`docs/why_the_model_does_or_does_not_have_an_edge.md` said on its third line:

    **Generated from `data/outputs/cbb_price_backtest.json`.** Every figure is
    read from that record rather than typed, so this cannot drift from the
    measurement. Re-render whenever the record changes.

**No generator existed.** Every figure in the document had been typed, and the
sentence promising otherwise is exactly the sentence that stops a reader
checking. The document had already drifted: it quoted a pooled forecast-skill
advantage of `−0.01312 [−0.01468, −0.01156]` and described it as the comparison
*"with the vig left in"* — the value belongs to the de-vigged comparison, and
the bounds are the **uncorrected** ones, so the number was both the wrong
instrument and the un-widened interval, printed under a heading claiming it
could not drift.

## What it does

Reads the price backtest record, the forecast-skill record and the held-out
replication record; writes a **run record** holding every number it found; then
renders the markdown as a pure function of that record. The report is never
written by hand — `--check` fails when the markdown on disk has stopped
matching what its record renders to, because a hand-edited generated file
survives exactly one re-render.

## It refuses rather than inventing

A missing, unreadable or wrongly shaped record exits 2 and writes nothing. A
document that weighs three instruments and silently weighs two still reads like
an answer, and this repository's whole arrangement is against a broken
instrument being reported as a null result.

## `--check` asks two questions

1. **Is the record still about the evidence on disk?** The record writes down
   every file it opened, whether it was there, and what that file stamped
   itself with; `--check` re-asks the disk and fails when any answer changed.
   `what_we_can_claim` learned this the expensive way: on 2026-09-04 its check
   passed while the document it checked named a committed backtest of 118,050
   graded bets as *not found*. Internally consistent, externally false.
2. **Does the markdown still match what the record renders to?** The question a
   hand-edit fails.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cbb_betting_lab.competitions import DEFAULT_COMPETITION_KEY, competition_for
from cbb_betting_lab.config import OUTPUTS_DIR
from cbb_betting_lab.reports import why_the_model as WHY


class WhySpliceError(RuntimeError):
    """The target document cannot receive a generated block."""


def splice(path: Path, rendered: str) -> Path:
    """Replace the fenced block in `path`, leaving every other line alone.

    The same splice `scripts/run_what_we_can_claim.py` performs, and for the
    same reason: the hand-written framing above the fence — what this document
    is, and which document to read first — stays exactly where it is, and only
    the measured block moves.

    A missing fence raises. Appending the block instead would leave a document
    that looks updated and is not, which is the failure mode this whole
    repository is arranged against.
    """
    target = Path(path)
    if not target.is_file():
        raise WhySpliceError(f"{target} does not exist; nothing to splice into.")
    text = target.read_text(encoding="utf-8")
    start = text.find(WHY.BEGIN_MARKER)
    stop = text.find(WHY.END_MARKER)
    if start < 0 or stop < 0 or stop < start:
        raise WhySpliceError(
            f"{target} carries no generated block. It needs the markers\n"
            f"  {WHY.BEGIN_MARKER}\n  {WHY.END_MARKER}\n"
            "in that order. Refusing to append instead: a document that looks "
            "updated and is not is worse than one that is obviously stale."
        )
    body = "\n".join(
        line for line in rendered.splitlines() if not line.startswith("# ")
    ).strip()
    target.write_text(
        text[: start + len(WHY.BEGIN_MARKER)] + "\n\n" + body + "\n\n" + text[stop:],
        encoding="utf-8",
    )
    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument(
        "--record",
        default="",
        help="Run record to write, or to render from with --rerender.",
    )
    parser.add_argument("--report", default="", help="Where to write the markdown.")
    parser.add_argument(
        "--rerender",
        action="store_true",
        help=(
            "Render the existing record without rebuilding it from the "
            "measurement records. Use this to improve a sentence without "
            "re-reading a measurement — the report is a pure function of the "
            "record."
        ),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Do not write. Exit non-zero when the record is older than the "
            "evidence it says it read, or when the report on disk differs from "
            "what that record renders to, which means it was edited by hand."
        ),
    )
    parser.add_argument(
        "--splice-into",
        default="",
        help=(
            "A hand-written document carrying BEGIN/END GENERATED markers. The "
            "rendered report replaces what sits between them and the prose "
            "around them is left alone."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    competition = competition_for(args.competition)
    output_dir = Path(args.output_dir)
    record_target = (
        Path(args.record) if args.record else WHY.record_path(competition, output_dir)
    )
    report_target = (
        Path(args.report) if args.report else WHY.report_path(competition, output_dir)
    )

    # `--rerender` and `--check` read the record; the default run rebuilds it
    # from the evidence. A check that rebuilt first could never detect drift —
    # it would overwrite the thing it was asked to compare against.
    if args.rerender or args.check:
        try:
            record = WHY.read_record(record_target)
        except WHY.WhyError as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 2
    else:
        try:
            record = WHY.build_record(competition=competition, output_dir=output_dir)
        except WHY.WhyError as exc:
            # The refusal. Nothing is written: no record, no report, and no
            # splice into the document, which therefore keeps saying whatever
            # it last truthfully said instead of gaining a hole.
            print(f"::error::{exc}", file=sys.stderr)
            return 2

    # FRESHNESS BEFORE THE RENDER. The re-render comparison describes the
    # record's relationship to itself; only this asks whether the record is
    # still about the evidence on disk.
    if args.check:
        stale = WHY.stale_inputs(record)
        if stale:
            print(
                f"::error::{record_target} is older than the evidence it says "
                "it read, so the document rendered from it is stating things "
                "about files it never opened. Re-run this script without "
                "--check to rebuild the record from the evidence on disk.",
                file=sys.stderr,
            )
            for reason in stale:
                print(f"::error::  {reason}", file=sys.stderr)
            return 1

    try:
        rendered = WHY.render(record)
    except WHY.WhyError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2

    if args.check:
        existing = (
            report_target.read_text(encoding="utf-8") if report_target.is_file() else ""
        )
        if existing != rendered:
            print(
                f"::error::{report_target} does not match what {record_target} "
                "renders to. Re-render it rather than editing it: this report "
                "is a pure function of its record, and an edit here is lost the "
                "next time anybody re-renders.",
                file=sys.stderr,
            )
            return 1
        print(f"{report_target} matches its run record.")
        return 0

    if not args.rerender:
        WHY.write_record(record, record_target)
    try:
        WHY.write_report(record, report_target)
    except WHY.WhyError as exc:
        # The forbidden-vocabulary guard. Refusing to write is the point.
        print(f"::error::{exc}", file=sys.stderr)
        return 2

    if args.splice_into:
        try:
            spliced = splice(Path(args.splice_into), rendered)
        except WhySpliceError as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 2
        print(f"Spliced the generated block into {spliced}.")

    print(f"Wrote {report_target} from {record_target}.")
    print()
    print(WHY.headline(record))
    print()
    correction = record.get("correction", {}) or {}
    if correction.get("applied"):
        print(
            f"Correction: {int(correction.get('hypotheses', 0)):,} cumulative "
            f"hypotheses, intervals widened by "
            f"x{float(correction.get('factor', 1.0)):.2f}."
        )
    else:
        print(
            "Correction: NO experiment ledger could be read, so no family-wise "
            "correction was applied. The report says so rather than quietly "
            "applying none."
        )
    tiers = [t for t in record.get("tiers", []) if t.get("enough_evidence")]
    print(
        f"Tiers measured: {len(tiers):,}. "
        f"Demonstrated edges: {len(WHY.demonstrated_edges(tiers)):,}. "
        f"Demonstrated deficits: {len(WHY.demonstrated_deficits(tiers)):,}."
    )
    print(
        "This run read records, rendered markdown, and touched no network. It "
        "allowlisted no market, signed no receipt and spent no credit."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
