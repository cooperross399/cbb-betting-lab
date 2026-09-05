#!/usr/bin/env python3
"""Refuse a diff that removes or rewrites a hypothesis the base already recorded.

    python scripts/check_ledger_append_only.py --base BASE.json --head HEAD.json
    python scripts/check_ledger_append_only.py --base-absent --head HEAD.json

`ExperimentLedger.save()` raises when a ledger would shrink, but it only sees
writes that travel through the code. An earlier version of this docstring said
it "could never fire" and quoted a reproduction — twelve of thirty hypotheses
deleted, the recorder re-run, the correction falling from x1.60 to x1.46. Both
halves were re-measured on 2026-09-04 and both were wrong:

- The old re-read fires. Load the tracked 30-entry ledger, delete twelve in
  memory, save to the same path against `save()` as it stood on 02e75b7:
  `ValueError: The experiment ledger would fall from 30 entries to 18.`
- Running the recorder over a hand-cut 18-entry ledger at 02e75b7 prints *"18
  distinct hypotheses before, 30 after (12 new)"* and *"x1.60"* — `record()`
  puts every hypothesis back. And x1.46 is the factor at **12** hypotheses,
  not at the 18 that deleting twelve of thirty leaves; that is x1.53.

The edit no runtime guard can see is one made **on disk and committed**:
`save()` is never called, so nothing compares anything, and every report from
then on reads the shorter ledger and quotes the smaller correction. That is
what this script is for. It reads the base commit, so a removal has to get
past a comparison rather than past a function that is never invoked.

A count check alone is not that comparison. Drop the hypothesis that failed,
append a fresh one in its place, and the count is unchanged while the
correction now rests on a family that quietly lost its most inconvenient
member. So the merge key is `(search, name, seasons, stage)` — the same key
`Hypothesis.key()` uses, stage included, because putting a discovery finding
to the holdout is a second look and is counted as one — and every surviving
key must still carry the base's `tested_on` and `predicted_direction`
verbatim, and its `outcome` too unless the base recorded `pending`.

`pending` is the one permitted transition, and it is one-way. This lab
pre-registers a hypothesis with `outcome="pending"` BEFORE the backtest runs
and the measurement writes the outcome back; a gate that froze `pending`
would refuse the lab's own design. A measured outcome is frozen: `pending`
may become anything, anything else may not change, and nothing may become
`pending` again. `realised_direction` is written back with the outcome and is
not compared for the same reason.

Nor is a key-by-key comparison enough on its own. Reduce each side to one
record per key and a side that disagrees with ITSELF reads as clean, so
`contradictions()` runs over both sides before the comparison: a ledger may
not hold two records under one key that disagree about what was found.

What that pass does not reach is not described here, because a docstring is
not a check. It is asserted by running this script, in
`test_known_gaps_that_still_get_through` in
`tests/test_check_ledger_append_only.py`.

Standard library only. The workflow step runs this without `PYTHONPATH=src`,
so the correction arithmetic is restated from `experiment_ledger.py` rather
than imported, and `test_the_scripts_arithmetic_matches_the_package` holds the
two copies against each other. There is no `--force`, no allowlist and no
environment waiver. A gate with a waiver is a gate that will be waived.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import NormalDist

#: Same value as `experiment_ledger.ALPHA`; restated, not imported.
ALPHA = 0.05

#: The fields an entry must carry to be a record of anything.
TEXT_FIELDS = ("search", "name", "tested_on", "outcome", "predicted_direction", "stage")

#: What the base and the head must agree on for a hypothesis that appears in
#: both, unconditionally.
FROZEN_FIELDS = ("tested_on", "predicted_direction")

#: The outcome a hypothesis is pre-registered with. The only base outcome a
#: head may change.
PENDING = "pending"

Key = tuple[str, str, tuple[int, ...], str]


class LedgerError(Exception):
    """A ledger that cannot be read or trusted. Always a failure, never a skip."""


def correction_factor(count: int) -> float:
    """Bonferroni on the cumulative count, as `ExperimentLedger` computes it."""
    families = max(count, 1)
    if families == 1:
        return 1.0
    return NormalDist().inv_cdf(1 - (ALPHA / families) / 2) / 1.96


def read_ledger(path: Path, side: str) -> list[dict]:
    """The `hypotheses` list, or a `LedgerError` naming what was wrong."""
    if not path.is_file():
        raise LedgerError(f"the {side} ledger {path} does not exist")
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise LedgerError(f"the {side} ledger {path} could not be read: {exc}") from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise LedgerError(f"the {side} ledger {path} is not parseable JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise LedgerError(
            f"the {side} ledger {path} is a {type(payload).__name__}, not a JSON object with a 'hypotheses' key"
        )
    entries = payload.get("hypotheses")
    if not isinstance(entries, list):
        raise LedgerError(f"the {side} ledger {path} has no 'hypotheses' list (found {type(entries).__name__})")
    for index, entry in enumerate(entries):
        where = f"{side} entry {index}"
        if not isinstance(entry, dict):
            raise LedgerError(f"{where} is a {type(entry).__name__}, not an object")
        for field in TEXT_FIELDS:
            if field not in entry:
                raise LedgerError(f"{where} is missing '{field}'")
            if not isinstance(entry[field], str):
                raise LedgerError(f"{where} has '{field}' as a {type(entry[field]).__name__}, not a string")
        if "seasons" not in entry:
            raise LedgerError(f"{where} is missing 'seasons'")
        seasons = entry["seasons"]
        if not isinstance(seasons, list):
            raise LedgerError(f"{where} has 'seasons' as a {type(seasons).__name__}, not a list")
        for season in seasons:
            # A bool keys IDENTICALLY to the int 1, so `isinstance(x, int)`
            # would admit `true` as a season nobody wrote.
            if not isinstance(season, int) or isinstance(season, bool):
                raise LedgerError(f"{where} has a season that is a {type(season).__name__}, not an int")
    return entries


def key(entry: dict) -> Key:
    """What makes two entries the same test — `Hypothesis.key()` restated."""
    return (entry["search"], entry["name"], tuple(entry["seasons"]), entry["stage"])


def describe(entry_key: Key) -> str:
    search, name, seasons, stage = entry_key
    span = ", ".join(str(s) for s in seasons) or "no seasons"
    return f"{search} / {name} ({span}; {stage})"


def contradictions(entries: list[dict], side: str) -> tuple[list[str], dict[Key, dict]]:
    """Every place one side disagrees with itself, and its first record per key.

    Frozen fields and outcome alike: two records under one key with different
    outcomes is a contradiction even when one of them is `pending`, because a
    ledger records a hypothesis once and the transition happens in place.
    """
    problems: list[str] = []
    first_by_key: dict[Key, dict] = {}
    first_index: dict[Key, int] = {}
    for index, entry in enumerate(entries):
        entry_key = key(entry)
        first = first_by_key.setdefault(entry_key, entry)
        if first is entry:
            first_index[entry_key] = index
            continue
        for field in (*FROZEN_FIELDS, "outcome"):
            if entry[field] != first[field]:
                problems.append(
                    f"the {side} ledger contradicts itself: {describe(entry_key)} — '{field}' is "
                    f"{first[field]!r} in {side} entry {first_index[entry_key]} and {entry[field]!r} "
                    f"in {side} entry {index}. One key, two answers: whichever copy survives the "
                    "next run is a choice nobody recorded."
                )
    return problems, first_by_key


def compare(base: list[dict], head: list[dict]) -> tuple[list[str], int]:
    """Every way the head betrays the base, and how many keys were checked."""
    problems: list[str] = []
    base_problems, base_by_key = contradictions(base, "base")
    head_problems, _ = contradictions(head, "head")
    problems.extend(base_problems)
    problems.extend(head_problems)

    if len(head) < len(base):
        problems.append(
            f"the ledger falls from {len(base)} entries to {len(head)}. It is append-only: the "
            "tests that failed are what make a surviving one unlikely to be chance, and a "
            "ledger that can shrink reports a correction smaller than the truth."
        )

    head_by_key: dict[Key, list[dict]] = {}
    for entry in head:
        head_by_key.setdefault(key(entry), []).append(entry)

    compared = 0
    for entry_key, base_entry in base_by_key.items():
        matches = head_by_key.get(entry_key)
        if not matches:
            problems.append(f"removed from the ledger: {describe(entry_key)}")
            continue
        compared += 1
        for head_entry in matches:
            for field in FROZEN_FIELDS:
                if head_entry[field] != base_entry[field]:
                    problems.append(
                        f"rewritten in the ledger: {describe(entry_key)} — '{field}' was "
                        f"{base_entry[field]!r}, is now {head_entry[field]!r}"
                    )
            if base_entry["outcome"] != PENDING and head_entry["outcome"] != base_entry["outcome"]:
                problems.append(
                    f"rewritten in the ledger: {describe(entry_key)} — 'outcome' was "
                    f"{base_entry['outcome']!r}, is now {head_entry['outcome']!r}. A measured "
                    f"outcome is frozen; only {PENDING!r} may be filled in."
                )
    return problems, compared


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    origin = parser.add_mutually_exclusive_group(required=True)
    origin.add_argument("--base", type=Path, help="the ledger as it stands at the base commit")
    origin.add_argument("--base-absent", action="store_true", help="there was no ledger at the base commit")
    parser.add_argument("--head", type=Path, required=True, help="the ledger as it stands on this branch")
    args = parser.parse_args(argv)

    try:
        head = read_ledger(args.head, "head")
        base = read_ledger(args.base, "base") if args.base is not None else None
    except LedgerError as exc:
        print(f"Ledger check FAILED: {exc}", file=sys.stderr)
        return 1

    # First line, because the workflow takes `head -n 1` of this output. The
    # count is the sample size the factor is derived from.
    distinct = len({key(entry) for entry in head})
    print(
        f"{distinct} distinct hypotheses in the head ledger ({len(head)} entries). "
        f"Any new 95% interval widens by x{correction_factor(distinct):.2f}."
    )

    if base is None:
        problems, _ = contradictions(head, "head")
        compared = 0
    else:
        problems, compared = compare(base, head)
        if not problems and compared == 0:
            problems.append(
                f"base was present but nothing was compared ({len(base)} base entries, {len(head)} head entries)"
            )

    if problems:
        sys.stdout.flush()
        print("Ledger check FAILED. The ledger is append-only.", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        return 1

    if base is None:
        print("No ledger at the base commit: first-commit state, nothing to compare.")
        return 0

    print(
        f"{compared} base hypotheses compared, all present with an identical tested_on and "
        f"predicted_direction and no measured outcome rewritten. {len(head) - len(base)} appended."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
