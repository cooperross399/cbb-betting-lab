#!/usr/bin/env python3
"""Re-render `data/outputs/cbb_what_we_can_claim.md` from the evidence on disk.

    PYTHONPATH=src python scripts/run_what_we_can_claim.py --competition cbb

That is exactly how `.github/workflows/cbb-gameday-refresh.yml` invokes it,
under `if: always()` and `continue-on-error: true`, after the card has been
frozen and the ledger settled. **It touches no network, needs no credential and
cannot spend a credit**, which is what makes it safe to run on every game day
and in CI on every push.

## What it does

Reads the experiment ledger, the price backtest record, the forward-evidence
ledger, any replication record, every recorded verdict and the staging provider
policy; writes a **run record** holding every number it found; then renders the
markdown as a pure function of that record. The report is never written by hand
— `--check` fails when the markdown on disk has stopped matching what its record
renders to, because a hand-edited generated file survives exactly one re-render.

## `--check` asks two questions, and it used to ask only the cheaper one

1. **Is the record still about the evidence on disk?** The record writes down
   every file it opened, whether it was there, and what that file stamped
   itself with; `--check` re-asks the disk and fails when any of the three
   answers has changed.
2. **Does the markdown still match what the record renders to?** The original
   question, and the one a hand-edit fails.

Only the second existed, and on 2026-09-04 it passed while the document said
*"nothing has been measured against real prices yet"* and named
`data/outputs/cbb_price_backtest.json` as **not found** — with that record
committed beside it holding 118,050 graded bets and one demonstrated deficit.
The markdown was a faithful rendering of a run record written the day before the
backtest ran, and a check that compares a document only against its own record
can confirm that it is internally consistent and never that it is true.

## Why it exits zero with nothing to say

Today there is nothing to claim: no price has been bought and no opinion has
settled. That produces a short, true document rather than an empty one or a
failure. A run that exits non-zero here would mark the whole game-day run
degraded, and *"the lab has measured nothing yet"* is not a fault — it is the
correct state for a lab whose season opens in November.

It exits non-zero for exactly two things: `--check` finding drift — a stale
record or a hand-edited report — and a record it was asked to render that cannot
be read. Both are faults in the instrument.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cbb_betting_lab.competitions import DEFAULT_COMPETITION_KEY, competition_for
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR
from cbb_betting_lab.reports import what_we_can_claim as WC



#: The markers that fence the generated block inside a hand-written document.
BEGIN = "<!-- BEGIN GENERATED: what_we_can_claim -->"
END = "<!-- END GENERATED -->"


class ClaimsSpliceError(RuntimeError):
    """The target document cannot receive a generated block."""


def splice(path: Path, rendered: str) -> Path:
    """Replace the fenced block in `path`, leaving every other line alone.

    **Why a splice rather than a write.** Cooper's brief asks for two things
    that pull against each other: `docs/what_we_can_and_cannot_claim.md` is
    written *before the first measurement* — that timing is the whole point of
    the file, because a document explaining how to read a number, written after
    the number arrives, is a justification rather than a rule — and the weekly
    loop must *re-render it from the run record rather than by hand*.

    Overwriting the file would satisfy the second and destroy the first. So the
    hand-written framing stays exactly where it is and only the fenced block
    moves, which is what makes the sentence "generated weekly, framing written
    first" true of one file rather than of two that can drift apart.

    A missing fence raises. Appending the block instead would leave a document
    that looks updated and is not, which is the failure mode this whole
    repository is arranged against.
    """
    target = Path(path)
    if not target.is_file():
        raise ClaimsSpliceError(f"{target} does not exist; nothing to splice into.")
    text = target.read_text(encoding="utf-8")
    start = text.find(BEGIN)
    stop = text.find(END)
    if start < 0 or stop < 0 or stop < start:
        raise ClaimsSpliceError(
            f"{target} carries no generated block. It needs the markers\n"
            f"  {BEGIN}\n  {END}\n"
            "in that order. Refusing to append instead: a document that looks "
            "updated and is not is worse than one that is obviously stale."
        )
    body = "\n".join(
        line for line in rendered.splitlines() if not line.startswith("# ")
    ).strip()
    return _write(
        target,
        text[: start + len(BEGIN)] + "\n\n" + body + "\n\n" + text[stop:],
    )


def _write(target: Path, text: str) -> Path:
    target.write_text(text, encoding="utf-8")
    return target


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument(
        "--processed-dir",
        default=str(PROCESSED_DIR),
        help="Where the forward-evidence ledger lives.",
    )
    parser.add_argument(
        "--manual-dir",
        default="",
        help="Where the staging provider policy lives. Read, never written.",
    )
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
            "evidence. Use this to improve a sentence without re-reading a "
            "measurement — the report is a pure function of the record."
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
    args = parser.parse_args(argv)

    competition = competition_for(args.competition)
    output_dir = Path(args.output_dir)
    record_target = (
        Path(args.record) if args.record else WC.record_path(competition, output_dir)
    )
    report_target = (
        Path(args.report) if args.report else WC.report_path(competition, output_dir)
    )

    # `--rerender` and `--check` read the record; the default run rebuilds it
    # from the evidence. The distinction matters because rebuilding is the only
    # step that consults the measurement records, and a check that rebuilt
    # first could never detect drift — it would overwrite the thing it was
    # asked to compare against.
    if args.rerender or args.check:
        try:
            record = WC.read_record(record_target)
        except WC.ClaimsError as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 2
    else:
        record = WC.build_record(
            competition=competition,
            output_dir=output_dir,
            processed_dir=Path(args.processed_dir),
            manual_dir=Path(args.manual_dir) if args.manual_dir else None,
        )

    # FRESHNESS BEFORE THE RENDER, and before the re-render comparison. Both
    # of those describe the record's relationship to itself; only this one asks
    # whether the record is still about the evidence on disk, and until it
    # existed nothing did. On 2026-09-04 the markdown matched its record byte
    # for byte — the record had been written the day before the price backtest
    # ran, so both said `data/outputs/cbb_price_backtest.json` was **not found**
    # while 118,050 graded bets sat committed in it. `--check` compared the
    # document only against its own record, agreed with itself, and exited zero.
    #
    # It runs before `render` so that a record too old to carry
    # `evidence_inputs` reports *why* it is out of date rather than the version
    # mismatch it would also fail on. Both are faults; only one names the file
    # whose evidence went unread.
    if args.check:
        stale = WC.stale_inputs(record)
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
        rendered = WC.render(record)
    except WC.ClaimsError as exc:
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
        WC.write_record(record, record_target)
    try:
        WC.write_report(record, report_target)
    except WC.ClaimsError as exc:
        # The forbidden-vocabulary guard. Refusing to write is the point: a
        # document that has started selling must not reach the card feed.
        print(f"::error::{exc}", file=sys.stderr)
        return 2

    if args.splice_into:
        try:
            spliced = splice(Path(args.splice_into), rendered)
        except ClaimsSpliceError as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return 2
        print(f"Spliced the generated block into {spliced}.")

    print(f"Wrote {report_target} from {record_target}.")
    print()
    print(WC.headline(record))
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
            "Correction: NO experiment ledger was found, so no family-wise "
            "correction could be applied. The report says so rather than "
            "quietly applying none."
        )

    claims = record.get("claims", []) or []
    print(
        f"Cells measured: {len(claims):,}. "
        f"Demonstrated edges: {len(WC.demonstrated_edges(record)):,}. "
        f"Demonstrated deficits: {len(WC.demonstrated_deficits(record)):,}."
    )
    policy = record.get("policy", {}) or {}
    print(f"Policy: {policy.get('summary', '')}")
    print(
        "This run read records, rendered markdown, and touched no network. It "
        "allowlisted no market, signed no receipt and spent no credit."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
