#!/usr/bin/env python3
"""Split every staked bet by whether its price survived, and say if it was reachable.

    # Reads the capture store and whatever bets exist. Costs nothing:
    PYTHONPATH=src python scripts/run_reachability.py

    # A specific graded bet frame:
    PYTHONPATH=src python scripts/run_reachability.py --bets data/processed/cbb_forward_evidence.csv

    # Rebuild the report from the run record, touching nothing else:
    PYTHONPATH=src python scripts/run_reachability.py --rerender
    PYTHONPATH=src python scripts/run_reachability.py --check

**This script opens no socket, reads no credential and cannot spend a credit.**
Every input is already on disk: the line-movement store the cron captures four
times a day, and a graded bet frame. That is what makes it safe to run in CI on
every push, which is also how a report that has drifted from its record fails
the build rather than sitting wrong in `data/outputs/`.

## Why it does not fail on a thin store

Today is September. The season opens on 2026-11-01, there is no college
basketball between April and November, and `capture_line_movement.py` writes
nothing when the board comes back empty — because an empty capture would later
read as every price having vanished. So the ordinary state of the store right
now is *absent or nearly so*, and the ordinary output of this script is
**"not enough evidence"** with the census that justifies it.

A crash here would be wrong twice over: it would look like a broken pipeline
when the truth is a calendar, and it would leave `data/outputs/` with no record
of what was actually known on the day. An empty table would be worse still,
because an empty table reads as a null result and a null result is a claim.

## The bet frame, and the two column names it may arrive under

The forward-evidence ledger is the frame that will carry real staked bets in
season, and it spells two things differently from
`reports/price_backtest.BET_COLUMNS`: its slate day is `snapshot_date`, and any
survival it carries is `price_survived`. Both are renamed here, loudly, on the
way in. Nothing else is defaulted — a **missing** column raises and names
itself, because the football lab's backtest read a missing settlement column as
a zero, reported zero bets, and had that read as "the model never disagrees
enough with the market" when it was a wiring fault.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from cbb_betting_lab import reachability as RE
from cbb_betting_lab.competitions import DEFAULT_COMPETITION_KEY, competition_for
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, REPO_ROOT
from cbb_betting_lab.reports import price_backtest as PB

#: The forward ledger's spelling of the columns this report needs, and what it
#: is renamed to. Renamed rather than aliased everywhere downstream: two
#: spellings of one field is how a join quietly matches nothing.
LEDGER_RENAMES: dict[str, str] = {
    "snapshot_date": "slate_date",
    "price_survived": RE.SURVIVED_COLUMN,
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument(
        "--bets",
        default="",
        help=(
            "A graded bet frame. Defaults to the forward-evidence ledger under "
            "--processed-dir. A frame that does not exist is not an error: the "
            "board-level survival census is still written."
        ),
    )
    parser.add_argument(
        "--record",
        default="",
        help="Run record to write or render. Defaults beside the report.",
    )
    parser.add_argument("--report", default="", help="Where to write the markdown.")
    parser.add_argument(
        "--rerender",
        action="store_true",
        help=(
            "Do not measure. Rebuild the report from the existing run record, "
            "so improving a sentence never costs a re-run."
        ),
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
    return parser


def record_path_hint(path: Path) -> str:
    """The store's path as the record should remember it.

    Relative to the repository when it lives inside it. The record is a
    committed artifact under `data/outputs/`, and an absolute path in it churns
    the diff on every machine that runs the script — which makes a real change
    to the census harder to see, not easier.
    """
    try:
        return str(Path(path).relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def default_bets_path(competition, processed_dir: Path) -> Path:
    """The forward-evidence ledger, named through the registry.

    Never a bare literal: an unprefixed output is a file two competitions would
    both write, and the second one to run would silently become the record.
    """
    return Path(processed_dir) / competition.output_name("forward_evidence", ".csv")


def load_bets(path: Path) -> tuple[pd.DataFrame, list[str]]:
    """A graded bet frame, or an empty one, with a note about what happened.

    A **missing file is not an error**: no forward opinion has been settled yet
    and the board-level census is still worth writing. A file that exists and
    is missing a required column **is** an error, and it raises rather than
    defaulting — see the module docstring.
    """
    notes: list[str] = []
    if not path.is_file():
        notes.append(
            f"{path} does not exist, so no staked bet was split. The season "
            "opens in November and no forward opinion has been settled yet; "
            "the board-level survival census below is what is known today."
        )
        return pd.DataFrame(), notes
    frame = pd.read_csv(path, low_memory=False)
    if frame.empty:
        notes.append(
            f"{path} exists and holds no rows. That is a ledger that started "
            "and settled nothing, not a strategy that placed no bets, and no "
            "return is reported over either."
        )
        return pd.DataFrame(), notes
    renames = {a: b for a, b in LEDGER_RENAMES.items() if a in frame.columns and b not in frame.columns}
    if renames:
        frame = frame.rename(columns=renames)
        for source, target in renames.items():
            notes.append(f"Read `{source}` as `{target}`.")
    PB.require_columns(frame, PB.BET_COLUMNS, f"the bet frame at {path}")
    notes.append(f"Read {len(frame):,} graded rows from {path}.")
    return frame, notes


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    competition = competition_for(args.competition)
    output_dir = Path(args.output_dir)
    processed_dir = Path(args.processed_dir)
    record_target = (
        Path(args.record) if args.record else RE.record_path(competition, output_dir)
    )
    report_target = (
        Path(args.report) if args.report else RE.report_path(competition, output_dir)
    )

    if args.rerender or args.check:
        return _rerender(record_target, report_target, check=args.check)

    store_file = RE.store_path(competition, processed_dir)
    store = RE.load_store(competition, processed_dir)
    bets_path = Path(args.bets) if args.bets else default_bets_path(competition, processed_dir)
    try:
        bets, notes = load_bets(bets_path)
    except PB.BacktestError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2
    for note in notes:
        print(note)

    looks = PB.looks_from_ledger(PB.ledger_path(output_dir))
    record = RE.build_record(
        bets,
        store,
        competition=competition,
        looks=looks,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        store_path_hint=record_path_hint(store_file),
    )
    RE.write_record(record, record_target)
    RE.write_report(record, report_target)

    _summarise(record)
    print(f"\nWrote {record_target}")
    print(f"Wrote {report_target}")
    print(
        "Nothing was requested, no credential was read and no credit was spent."
    )
    return 0


def _rerender(record_target: Path, report_target: Path, *, check: bool) -> int:
    try:
        record = RE.read_record(record_target)
        rendered = RE.render(record)
    except FileNotFoundError:
        print(
            f"::error::{record_target} does not exist. Run this script without "
            "--rerender first: the report is a pure function of the record and "
            "there is no record to render.",
            file=sys.stderr,
        )
        return 2
    except RE.ReachabilityError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return 2

    if check:
        existing = (
            report_target.read_text(encoding="utf-8") if report_target.is_file() else ""
        )
        if existing != rendered:
            print(
                f"::error::{report_target} does not match what {record_target} "
                "renders to. Re-render it rather than editing it: the report is "
                "a pure function of the record, and an edit here is lost the "
                "next time anybody re-renders.",
                file=sys.stderr,
            )
            return 1
        print(f"{report_target} matches its run record.")
    else:
        RE.write_report(record, report_target)
        print(f"Wrote {report_target} from {record_target}.")
    print("No network was touched and no credit was spent.")
    return 0


def _summarise(record: dict) -> None:
    """Everything a reader needs on stdout, every number beside its sample size."""
    store = dict(record.get("store") or {})
    print(
        f"\nStore: {store.get('quotes', 0):,} quotes across "
        f"{store.get('captures', 0):,} captures, "
        f"{store.get('judged_quotes', 0):,} judgeable, over "
        f"{store.get('events', 0):,} events and {store.get('books', 0):,} books."
    )
    if not store.get("enough_evidence"):
        print(f"{RE.NOT_ENOUGH_EVIDENCE.capitalize()}: {store.get('reason', '')}")

    provenance = dict(record.get("survival_provenance") or {})
    print(
        f"Bets: {provenance.get('bets', 0):,} staked — "
        f"{provenance.get('survived', 0):,} survived, "
        f"{provenance.get('gone', 0):,} gone, "
        f"{provenance.get('unknown', 0):,} unjudgeable "
        f"(source: {provenance.get('source', 'none')})."
    )
    for verdict in record.get("verdicts") or []:
        print(f"  {verdict['tier']}: {verdict['verdict']}")
    unreachable = [
        v for v in (record.get("verdicts") or []) if v.get("verdict") == RE.NOT_REACHABLE
    ]
    if unreachable:
        tiers = ", ".join(v["tier"] for v in unreachable)
        print(
            f"::warning::{len(unreachable)} tier(s) measured an edge that is "
            f"{RE.NOT_REACHABLE}: {tiers}. It lives entirely in prices that did "
            "not survive to the next capture, regardless of its size or its "
            "significance."
        )


if __name__ == "__main__":
    raise SystemExit(main())
