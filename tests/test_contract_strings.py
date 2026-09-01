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
    unpinned = set(_table_rows()) - set(CONTRACTS)

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
    """Skipped until the workflow exists; failing once it does is the point."""
    path = REPO_ROOT / CONTRACTS["Workflow file"]
    if not path.is_file():
        pytest.skip("the gameday workflow is not written yet")
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
