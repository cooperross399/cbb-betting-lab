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
#: and the pin is what stops it moving in silence.
#:
#: **This dict is weaker than `CONTRACTS` and the difference is written down
#: rather than glossed.** A name in `CONTRACTS` must appear in CLAUDE.md's
#: table with a matching value, checked by
#: `test_claude_md_records_every_contract_string`. A name here is exempt from
#: that: it is pinned to the *code* and to nothing in the documentation, so it
#: could sit here for ever with the table never gaining the row. That is a real
#: gap in the table guard, and the two tests below are what stop it widening —
#: `test_the_contract_strings_pending_a_table_row_are_the_ones_written_down`
#: fixes the exact set, so a second string cannot be parked here to dodge the
#: table, and `test_every_pending_contract_string_is_pinned_to_code_by_name`
#: requires each entry to be a literal some other test asserts the code
#: against.
#:
#: It is not in `CONTRACTS` because moving it there means adding a row to
#: `CLAUDE.md`, and this branch does not edit `CLAUDE.md`. When that row lands,
#: move the entry up and this dict empties again — the exact-set test goes red
#: on the day it does, which is the reminder to delete this comment with it.
PENDING_CONTRACTS = {
    "Edge document": "docs/why_the_model_does_or_does_not_have_an_edge.md",
}

#: The names allowed to sit in `PENDING_CONTRACTS`. Written out separately from
#: the dict so that parking a string there is two edits and one of them is here.
CONTRACT_STRINGS_AWAITING_A_TABLE_ROW = {"Edge document"}


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


def test_the_contract_strings_pending_a_table_row_are_the_ones_written_down():
    """The gap in the table guard, asserted at its exact size.

    `test_the_contract_table_has_no_rows_this_test_does_not_pin` subtracts
    `PENDING_CONTRACTS` from what it demands a pin for, and
    `test_claude_md_records_every_contract_string` never runs over it at all.
    So `PENDING_CONTRACTS` is the one place in this file where a contract
    string can live without CLAUDE.md carrying it — a hole exactly as wide as
    this dict and no wider. Fixing the set is what keeps it that wide: a second
    string parked here to avoid writing the table row fails this test rather
    than passing quietly.

    Nothing here is a waiver. The day the row lands in CLAUDE.md, the entry
    moves into `CONTRACTS`, both sets shrink, and this test goes red to be
    re-read — which is the point of writing a gap down as an assertion instead
    of as a sentence.
    """
    assert set(PENDING_CONTRACTS) == CONTRACT_STRINGS_AWAITING_A_TABLE_ROW, (
        f"`PENDING_CONTRACTS` holds {sorted(PENDING_CONTRACTS)} and the names "
        f"written down as awaiting a row are "
        f"{sorted(CONTRACT_STRINGS_AWAITING_A_TABLE_ROW)}. A contract string "
        "belongs in `CONTRACTS` with a row in CLAUDE.md's table; parking it "
        "here exempts it from the table guard, and the exemption is a list "
        "somebody reads, not a category anything can join."
    )
    assert not set(PENDING_CONTRACTS) & set(CONTRACTS), (
        "a name in both dicts is pinned to two values that nothing compares"
    )


def test_every_pending_contract_string_is_pinned_to_code_by_name():
    """A pending entry buys an exemption from the table, not from being pinned.

    Each one must be asserted against the code somewhere in this file by its
    literal value — `Edge document` against `why_the_model.DOC_RELATIVE` in
    `test_the_edge_document_is_the_path_the_generator_writes`. Without that it
    would be a string pinned to nothing at all, which is worse than not being
    listed: it would read as a contract that something checks.
    """
    source = Path(__file__).read_text(encoding="utf-8")
    for name, value in PENDING_CONTRACTS.items():
        assert source.count(f'PENDING_CONTRACTS["{name}"]') >= 1, (
            f"{name!r} is listed in `PENDING_CONTRACTS` and no test in this "
            f"file reads `PENDING_CONTRACTS[{name!r}]` to check the code "
            "against it. It is exempt from the table guard and pinned to "
            "nothing, so it is a rename waiting to happen wearing the word "
            "'pinned'."
        )
        assert value, f"{name!r} is pinned to an empty string"


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
