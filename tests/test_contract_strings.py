"""CLAUDE.md's contract strings, pinned against the code that uses them.

Cooper's scheduled routines hard-code these. Renaming any of them silently
breaks his automation, and **the breakage looks like the lab going quiet** —
which is the worst possible failure mode, because silence is also what a lab
with nothing to say looks like.

The table in `CLAUDE.md` is the source of truth and this file reads it. A
change to either without the other fails the build.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import REPO_ROOT
from cbb_betting_lab.experiment_ledger import LEDGER_FILENAME
from cbb_betting_lab.providers.odds_api import API_KEY_ENV


CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

#: Every contract string, and what in the code must agree with it.
CONTRACTS = {
    "Workflow name": "CBB Gameday Refresh",
    "Workflow file": ".github/workflows/cbb-gameday-refresh.yml",
    "Card feed branch": "card-feed",
    "Card comment file on the feed": "latest_card_comment.md",
    "Status file on the feed": "latest_status.json",
    "Odds API secret": "CBB_ODDS_API_KEY",
    "CollegeBasketballData secret": "CBBD_API_KEY",
    "Drive file title pattern": "CBB Card <date> <slot>",
    "Accumulating note": (
        "This card is **accumulating evidence, not making recommendations.**"
    ),
    "Claims output": "data/outputs/cbb_what_we_can_claim.md",
    "Forward evidence output": "data/outputs/cbb_forward_evidence.md",
    "Forward evidence ledger": "data/processed/cbb_forward_evidence.csv",
    "Experiment ledger": "data/outputs/experiment_ledger.json",
    "Changed-selections marker": "Selections changed",
}

#: Contract strings pinned here that `CLAUDE.md`'s table does not carry a row
#: for **yet**. A path a program writes to is a contract string in every sense
#: that matters — it is what a reader opens and what the weekly loop splices —
#: and the pin is what stops it moving in silence. The table row is a
#: documentation change, so it is proposed rather than made here; when it
#: lands, move the entry up into `CONTRACTS` and this dict empties again.
#: `test_the_contract_table_has_no_rows_this_test_does_not_pin` accepts the row
#: the day it appears, and the value is checked against the code either way.
PENDING_CONTRACTS = {
    "Edge document": "docs/why_the_model_does_or_does_not_have_an_edge.md",
}


def _table_rows() -> dict[str, str]:
    """Parse the contract table out of CLAUDE.md."""
    text = CLAUDE_MD.read_text(encoding="utf-8")
    section = text.split("## Contract strings", 1)[-1].split("\n## ", 1)[0]
    rows = {}
    for line in section.splitlines():
        match = re.match(r"^\|\s*(.+?)\s*\|\s*`?(.+?)`?\s*\|\s*$", line)
        if not match:
            continue
        name, value = match.group(1), match.group(2)
        if name in {"Thing", ":------"} or set(name) <= {"-", ":", " "}:
            continue
        rows[name] = value
    return rows


@pytest.mark.parametrize("name,value", sorted(CONTRACTS.items()))
def test_claude_md_records_every_contract_string(name: str, value: str):
    rows = _table_rows()

    assert name in rows, f"CLAUDE.md's contract table has no row for {name!r}."
    assert rows[name] == value, (
        f"CLAUDE.md says {name} is {rows[name]!r}; this test says {value!r}. "
        "One of them changed without the other, and Cooper's routines read the "
        "one in CLAUDE.md."
    )


def test_the_contract_table_has_no_rows_this_test_does_not_pin():
    """A new contract string must arrive with its pin, not without one."""
    unpinned = set(_table_rows()) - set(CONTRACTS) - set(PENDING_CONTRACTS)

    assert not unpinned, (
        f"CLAUDE.md declares contract strings this test does not pin: "
        f"{sorted(unpinned)}. An unpinned contract is a rename waiting to happen."
    )


def test_the_credential_name_matches_the_provider_module():
    assert API_KEY_ENV == CONTRACTS["Odds API secret"]


def test_every_output_is_competition_prefixed():
    """An unprefixed output is a file two competitions would both write."""
    for name in ("Claims output", "Forward evidence output", "Forward evidence ledger"):
        stem = Path(CONTRACTS[name]).name

        assert stem.startswith(f"{CBB.key}_"), (
            f"{CONTRACTS[name]} is not competition-prefixed. The second "
            "competition to run would silently become the record."
        )


def test_the_experiment_ledger_filename_matches_the_module():
    assert Path(CONTRACTS["Experiment ledger"]).name == LEDGER_FILENAME


def test_the_workflow_file_named_in_the_contract_is_the_one_on_disk():
    """The workflow exists and carries the name and the branch. This used to
    skip when the file was absent, which would have read as a pass the day the
    workflow was deleted."""
    path = REPO_ROOT / CONTRACTS["Workflow file"]
    assert path.is_file(), f"{CONTRACTS['Workflow file']} is missing"
    text = path.read_text(encoding="utf-8")

    assert f'name: {CONTRACTS["Workflow name"]}' in text
    assert CONTRACTS["Card feed branch"] in text


def test_the_accumulating_note_never_softens():
    """The card says what it is. This phrase is matched literally."""
    note = CONTRACTS["Accumulating note"]

    assert "accumulating evidence" in note
    assert "not making recommendations" in note
    for softener in ("may", "might", "currently", "for now", "at this time"):
        assert softener not in note.casefold(), (
            f"The accumulating note has acquired {softener!r}. It is a "
            "statement of what the card is, not a temporary disclaimer."
        )


def test_the_edge_document_is_the_path_the_generator_writes():
    """The document `run_why_the_model.py` regenerates, pinned by name.

    `why_the_model.DOC_RELATIVE` was a bare module constant that nothing
    checked. Everything downstream — the weekly loop's `--splice-into`, the
    test that compares the committed document against a fresh render, the fence
    guard — resolves the path *from that constant*, so pointing it at
    `docs/scratch.md` moved all of them together and left the suite green with
    the real document unregenerated for ever. A generated document nothing
    regenerates is the exact failure this cluster exists to prevent, arrived at
    from the other end.

    Pinned to the literal string here, the way every other contract string in
    this repository is pinned, so the rename has to be made twice and read once.
    """
    from cbb_betting_lab.reports import why_the_model as WHY

    expected = PENDING_CONTRACTS["Edge document"]

    assert WHY.DOC_RELATIVE == expected, (
        f"why_the_model.DOC_RELATIVE is {WHY.DOC_RELATIVE!r}; this test says "
        f"{expected!r}. Everything that re-renders the edge document resolves "
        "its path from that constant, so moving it silently retires the "
        "document rather than renaming it."
    )
    document = REPO_ROOT / expected
    assert document.is_file(), (
        f"{expected} is not in the repository. The weekly loop splices into it "
        "every week and a missing fence is an error, so an absent file is a "
        "step that will fail every Monday."
    )
    assert WHY.doc_path() == document, (
        "doc_path() does not resolve to the pinned path, so the generator "
        "and this pin are describing different files."
    )


def test_the_edge_document_pin_matches_the_contract_table_if_it_has_the_row():
    """The handoff: the day CLAUDE.md gains the row, its value must agree.

    Until then this asserts nothing about CLAUDE.md, which is the point — the
    row is a documentation change proposed alongside this pin, not made by it.
    """
    rows = _table_rows()
    for name, value in PENDING_CONTRACTS.items():
        if name in rows:
            assert rows[name] == value, (
                f"CLAUDE.md says {name} is {rows[name]!r} and this test says "
                f"{value!r}. Move the entry into CONTRACTS and delete it from "
                "PENDING_CONTRACTS once the row is there."
            )
