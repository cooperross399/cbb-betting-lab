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

from cbb_betting_lab import staging_provider_policy as policy_module
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
    "Policy gate check name": "Policy Gate",
    "Policy gate workflow file": ".github/workflows/policy-gate.yml",
}

#: Every file that promises the policy gate by name. GitHub reports a check
#: under the job's `name:`, so each of these sentences is only true while it
#: spells that name the way the workflow does. They were four bare strings
#: agreeing with each other by hand, which is a rename away from four
#: promises about a check that no longer reports.
POLICY_GATE_PROMISES = (
    "data/manual/README.md",
    "docs/what_we_can_and_cannot_claim.md",
    "data/outputs/cbb_what_we_can_claim.md",
    "src/cbb_betting_lab/staging_provider_policy.py",
    ".github/workflows/policy-gate.yml",
)


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


def test_the_policy_gate_module_constant_matches_the_contract_table():
    """The gate's name lives in one place in the code.

    `staging_provider_policy.POLICY_GATE_CHECK` is what the claims report
    renders and what every rule below compares against, the same way
    `API_KEY_ENV` is what the provider module uses.
    """
    assert policy_module.POLICY_GATE_CHECK == CONTRACTS["Policy gate check name"]
    assert policy_module.POLICY_GATE_WORKFLOW == CONTRACTS["Policy gate workflow file"]


def test_the_policy_gate_workflow_declares_the_contract_check_name():
    """The workflow on disk reports under the pinned name.

    GitHub reports a check under the JOB's `name:`, and the workflow's own
    `name:` is what a human looks for in the Actions tab; both must be the
    contract value, because a rename of either is a rename of the check five
    sentences in this repository promise.
    """
    path = REPO_ROOT / CONTRACTS["Policy gate workflow file"]
    assert path.is_file(), f"{CONTRACTS['Policy gate workflow file']} is missing"
    text = path.read_text(encoding="utf-8")
    name = CONTRACTS["Policy gate check name"]

    declared = re.findall(r"(?m)^name:\s*(.+?)\s*$", text)
    assert declared == [name], (
        f"{CONTRACTS['Policy gate workflow file']} declares workflow name(s) "
        f"{declared}; CLAUDE.md's contract table says {name!r}. Renaming the "
        "workflow renames the check every promise in this repository names."
    )
    jobs = re.findall(r"(?m)^\s{4}name:\s*(.+?)\s*$", text)
    assert jobs == [name], (
        f"{CONTRACTS['Policy gate workflow file']} names its job(s) {jobs}; "
        f"GitHub reports the check under the job name and the contract is {name!r}."
    )


@pytest.mark.parametrize("relative", POLICY_GATE_PROMISES)
def test_every_document_that_promises_the_policy_gate_names_the_contract_check(
    relative: str,
):
    """Each promise names the check that exists.

    These files say a market joins the allowlist in a pull request whose
    policy gate is green. That sentence is true only while the name in it is
    the name the workflow reports under, so the contract value must appear in
    every one of them — and a rename that misses any of these files fails
    here rather than leaving a sentence pointing at nothing.
    """
    path = REPO_ROOT / relative
    assert path.is_file(), f"{relative} is missing; it promised the policy gate"
    text = path.read_text(encoding="utf-8")

    assert CONTRACTS["Policy gate check name"] in text, (
        f"{relative} does not name {CONTRACTS['Policy gate check name']!r}. "
        "CLAUDE.md's contract table holds that name, and a promise that spells "
        "it differently is a promise about a check that does not report."
    )


def test_the_claims_report_renders_the_gate_name_from_the_constant():
    """The claims report may not carry its own spelling of the name.

    `docs/what_we_can_and_cannot_claim.md` and
    `data/outputs/cbb_what_we_can_claim.md` are rendered from this module, so
    a literal here is a fifth copy of the name that a rename can miss. It
    reads `staging_provider_policy.POLICY_GATE_CHECK` instead.
    """
    source = (
        REPO_ROOT / "src" / "cbb_betting_lab" / "reports" / "what_we_can_claim.py"
    ).read_text(encoding="utf-8")

    assert "POLICY_GATE_CHECK" in source, (
        "what_we_can_claim.py does not read the pinned gate name; the rendered "
        "claims file would keep whatever spelling was typed here."
    )
    assert CONTRACTS["Policy gate check name"] not in source, (
        "what_we_can_claim.py spells the policy gate's name literally. It must "
        "render staging_provider_policy.POLICY_GATE_CHECK, so that renaming the "
        "check renames what this report claims about it."
    )
