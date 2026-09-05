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

#: Every file that promises the policy gate, and WHAT each one promises.
#:
#: GitHub reports a check under the job's `name:`, so each of these sentences
#: is only true while it spells that name the way the workflow does — but the
#: name alone is not the promise. A file that names `Policy Gate` and calls it
#: advisory, or optional, or a check that runs on some pull requests, passes a
#: bare substring test while saying the opposite of what this repository
#: enforces. So each file's own sentences are pinned: that a market enters the
#: allowlist only behind a green gate, that the gate runs on EVERY pull
#: request, and that it is red while a receipt is missing.
_GATE = CONTRACTS["Policy gate check name"]
_GATE_FILE = CONTRACTS["Policy gate workflow file"]
POLICY_GATE_PROMISES: dict[str, tuple[str, ...]] = {
    "data/manual/README.md": (
        f"in a pull request with a signed receipt beside it and a green **`{_GATE}`** check",
        f"`{_GATE}` is `{_GATE_FILE}`. It runs on every pull request",
        "It is red while any allowlisted market lacks a receipt",
    ),
    "src/cbb_betting_lab/staging_provider_policy.py": (
        f"in a pull request whose **`{_GATE}`** check is green",
        f"`{_GATE}` is `{_GATE_FILE}`",
        "The check now runs on every pull request",
        "It is red until a receipt stands behind every allowlisted market",
    ),
    "docs/what_we_can_and_cannot_claim.md": (
        f"in a pull request whose `{_GATE}` check is green",
        f"`{_GATE_FILE}`, which runs on every pull request",
        "verifies every allowlisted market against a receipt on disk, and is red "
        "while any market lacks one",
    ),
    "data/outputs/cbb_what_we_can_claim.md": (
        f"in a pull request whose `{_GATE}` check is green",
        f"`{_GATE_FILE}`, which runs on every pull request",
        "verifies every allowlisted market against a receipt on disk, and is red "
        "while any market lacks one",
    ),
    ".github/workflows/policy-gate.yml": (
        f"name: {_GATE}",
        "WHAT IT CHECKS, on every pull request",
        "EXIT 2 IS NOT A PASS",
    ),
}

#: Words that turn a promise into a disclaimer. Refused within this many
#: characters of the gate's name — a file may use them about something else,
#: and may not use them about this check.
#:
#: "not a hold on the merge button" is deliberately NOT on this list: that
#: sentence is true (measured, main requires `Tests` and nothing else) and
#: saying a true thing about branch protection is not weakening the gate.
#: What is refused is a file calling the CHECK ITSELF optional.
GATE_SOFTENERS = (
    "advisory",
    "informational",
    "optional",
    "best effort",
    "best-effort",
    "not enforced",
    "for reference only",
    "cosmetic",
    "nice to have",
)
#: How far either side of the gate's name a softener is read as being about it.
SOFTENER_WINDOW = 400


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


def _flowed(text: str) -> str:
    """`text` with every run of whitespace collapsed to one space, so a
    sentence pinned here matches whatever column the file wraps it at."""
    return " ".join(text.split())


@pytest.mark.parametrize("relative", sorted(POLICY_GATE_PROMISES))
def test_every_document_that_promises_the_policy_gate_keeps_its_promise(
    relative: str,
):
    """Each file's PROMISE, not merely the gate's name in it.

    This rule used to be a bare substring: the contract name had to appear
    somewhere in the file. A file saying "`Policy Gate` is advisory only" —
    or that it runs on the pull requests that touch the policy file, which is
    the filter this repository refuses — satisfied that and said the opposite
    of what the gate enforces. So the sentences themselves are pinned: the
    name, that a market enters the allowlist only behind a GREEN gate, that
    the gate runs on EVERY pull request, and that it is RED while a receipt
    is missing. A rewrite that keeps the name and drops the promise fails
    here rather than leaving a document contradicting the check it names.
    """
    path = REPO_ROOT / relative
    assert path.is_file(), f"{relative} is missing; it promised the policy gate"
    text = path.read_text(encoding="utf-8")
    flowed = _flowed(text)

    assert CONTRACTS["Policy gate check name"] in text, (
        f"{relative} does not name {CONTRACTS['Policy gate check name']!r}. "
        "CLAUDE.md's contract table holds that name, and a promise that spells "
        "it differently is a promise about a check that does not report."
    )
    for promise in POLICY_GATE_PROMISES[relative]:
        assert _flowed(promise) in flowed, (
            f"{relative} no longer says {promise!r}. Naming the gate is not "
            "promising anything about it: this file's sentence is what makes "
            "the check's tick mean what the repository says it means."
        )
    lowered = flowed.casefold()
    for match in re.finditer(re.escape(CONTRACTS["Policy gate check name"]), flowed):
        window = lowered[
            max(0, match.start() - SOFTENER_WINDOW) : match.end() + SOFTENER_WINDOW
        ]
        softened = [word for word in GATE_SOFTENERS if word in window]
        assert not softened, (
            f"{relative} calls the gate {softened} within {SOFTENER_WINDOW} "
            f"characters of naming it: …{flowed[max(0, match.start() - 120):match.end() + 120]}… "
            "A check a document calls optional is a check nobody has to keep green."
        )




#: The two files the claims report renders into. Both carry the same bullet
#: about the policy gate, and both are read out of the tree rather than
#: rebuilt: `data/outputs/cbb_what_we_can_claim.json` is `record_version` 1
#: while the renderer emits 2, so neither can be regenerated here.
RENDERED_CLAIMS = (
    "docs/what_we_can_and_cannot_claim.md",
    CONTRACTS["Claims output"],
)


@pytest.mark.parametrize("relative", RENDERED_CLAIMS)
def test_the_rendered_claims_about_the_policy_gate_are_true_of_the_gate(relative: str):
    """Each factual claim the rendered document makes, checked against the tree.

    The rule above pins the document's WORDS. This one asks whether they are
    still TRUE, which is a different question and the one that can go wrong
    silently: these files are generated, they are read by a human deciding
    what this lab may say, and nothing compared their sentences with the
    repository they describe. Four claims, four checks:

      * `grant()` does not exist — assert the module has no such name;
      * `withdraw()` does — assert it is there and callable;
      * the gate runs on EVERY pull request — assert the workflow's
        `pull_request` trigger carries no `paths:`, `branches:` or `types:`
        filter, which is exactly what "every" means here;
      * "No market is allowlisted, and that is the correct state" — assert
        the shipped policy allowlists nothing. The day a market is added,
        this sentence stops being true and this test is what says so.
    """
    import yaml

    path = REPO_ROOT / relative
    assert path.is_file(), f"{relative} is missing"
    flowed = _flowed(path.read_text(encoding="utf-8"))
    gate_bullet = [
        sentence
        for sentence in flowed.split("- **")
        if CONTRACTS["Policy gate check name"] in sentence
    ]
    assert gate_bullet, f"{relative} makes no claim about the policy gate at all"

    assert "`grant()` does not" in flowed, (
        f"{relative} no longer says `grant()` does not exist, which is the whole "
        "shape of this door: the machine may withdraw and may never grant."
    )
    assert not hasattr(policy_module, "grant"), (
        f"{relative} says `grant()` does not exist and "
        "staging_provider_policy.grant does. The document is wrong or the "
        "function is, and either way a human is reading a false sentence."
    )
    assert callable(getattr(policy_module, "withdraw", None)), (
        f"{relative} says `withdraw()` exists and it does not"
    )

    document = yaml.safe_load(
        (REPO_ROOT / CONTRACTS["Policy gate workflow file"]).read_text(encoding="utf-8")
    )
    triggers = document.get(True, document.get("on"))
    assert isinstance(triggers, dict) and "pull_request" in triggers, (
        f"{relative} says the gate runs on every pull request and its triggers "
        f"are {triggers!r}"
    )
    configured = triggers["pull_request"] or {}
    assert not configured, (
        f"{relative} says the gate runs on every pull request, and its "
        f"`pull_request` trigger carries {configured!r}. A filtered check is not "
        "reported on the pull requests it filters out, so 'every' would be false."
    )

    assert "No market is allowlisted, and that is the correct state" in flowed, (
        f"{relative} no longer says no market is allowlisted; if a market has "
        "been added, this document has to say so rather than go quiet."
    )
    shipped = policy_module.load()
    assert shipped.allowlist == {}, (
        f"{relative} says no market is allowlisted and "
        f"{CONTRACTS['Policy gate workflow file']}'s policy file allowlists "
        f"{sorted(shipped.allowlist)}. The rendered claim is now false, and it "
        "is the claim a human reads before deciding what this lab may say."
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
