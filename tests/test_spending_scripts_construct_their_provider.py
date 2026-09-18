"""The credit-spending scripts can actually build the thing that spends.

Every one of these scripts is dry by default, which is right, and has a side
effect nobody wanted: **the code path that only runs under `--live` is the code
path no test and no dry run ever executes.** `scripts/buy_historical_prices.py`
was dispatched twice against the real API before anyone discovered that its
very first live statement — `OddsApiProvider()` — was missing a required
argument. The dry run passed, CI passed, and the failure arrived after a
GitHub Actions job had spent eleven minutes fetching and building 423MB of
play-by-play.

So this file executes the live branch far enough to construct the provider,
with a fake credential and no network. It does not request anything; it proves
the wiring exists.

The general shape of the defect is worth naming: **a flag that guards a code
path also hides it.** Anywhere `--live` gates something, the thing it gates
needs a test that does not depend on `--live`.
"""

from __future__ import annotations

import ast
import socket
from pathlib import Path

import pytest

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.providers.odds_api import OddsApiProvider

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"


@pytest.fixture()
def no_network(monkeypatch):
    def refuse(*a, **k):
        raise AssertionError("Constructing a provider must open no socket.")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


def test_the_provider_constructs_the_way_the_scripts_construct_it(no_network):
    """The exact call the live branch makes."""
    provider = OddsApiProvider(CBB, environment={"CBB_ODDS_API_KEY": "x" * 32})
    assert provider is not None


def test_no_script_constructs_the_provider_without_a_competition():
    """Read the source rather than run it: the live branch cannot be executed
    here, so the check is that the CALL is well-formed.

    This is a static check on purpose. Constructing the provider for real needs
    a credential; parsing the call needs nothing, and it is exactly the defect
    that got through — a zero-argument call to a one-argument constructor.
    """
    offenders: list[str] = []
    scripts = sorted(SCRIPTS.glob("*.py"))
    assert len(scripts) > 5, f"{len(scripts)} scripts under {SCRIPTS}; a moved directory is not a pass"
    for path in scripts:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name != "OddsApiProvider":
                continue
            if not node.args and not any(
                kw.arg == "competition" for kw in node.keywords
            ):
                offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, (
        "OddsApiProvider is constructed without a competition in: "
        f"{offenders}. It takes one positionally, and the call only runs under "
        "--live — so nothing but this test sees it."
    )


#: Every script that runs the free pre-flight before spending, and the module
#: constant each one passes as its reason. PINNED, because a sentence about
#: this set was written into `docs/ported_defects.md` row AD and into a test
#: docstring — "`sufficient_quota` existed and only `run_gameday_card.py`
#: called it" — and it was false: the probe called it too, behind
#: `--skip-quota-check`. That one row was the one that would have pointed at
#: the probe as a paid-data path, and instead it pointed away from it, in the
#: round whose whole finding was that the probe had been left out.
#:
#: IT WAS PINNED AT THREE AND THE SET WAS FOUR. `capture_line_movement.py` buys
#: the featured board on a schedule and ran no pre-flight and no in-run
#: breaker, and this constant recorded that as a deliberate boundary rather
#: than as the gap it was — so the audit that reads this dict was told the set
#: was complete. A capture on an emptied account is answered with a board
#: carrying no bookmakers, which the reachability store cannot tell apart from
#: a board no one hung; written down, it is movement that did not happen. It
#: now runs the same pre-flight with its own reason and the set is four.
PREFLIGHT_CALLERS = {
    "buy_historical_prices.py": "PURCHASE_STARVATION",
    "capture_line_movement.py": "MOVEMENT_STARVATION",
    "run_gameday_card.py": "CARD_STARVATION",
    "run_retention_probe.py": "PROBE_STARVATION",
}


# Parametrised off PREFLIGHT_CALLERS rather than a literal list. The literal
# said three while `PREFLIGHT_CALLERS` fourteen lines below said four, inside
# the very change that corrected three to four everywhere else — a roster that
# only guards what it names, in the file whose job is naming the roster.
@pytest.mark.parametrize("script", sorted(PREFLIGHT_CALLERS))
def test_every_spending_script_imports_cleanly(script):
    """A NameError in the live branch is invisible until money is being spent."""
    path = SCRIPTS / script
    assert path.is_file(), f"{script} does not exist; a spending script that vanished is not a pass"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    assigned = {
        target.id
        for node in ast.walk(tree)
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Name)
    }
    imported = {
        (alias.asname or alias.name).split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    # Every name the script constructs a provider or competition with must be
    # imported or assigned somewhere in the file.
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = getattr(node.func, "id", None)
            if name in {"OddsApiProvider"}:
                assert name in imported, f"{script} calls {name} without importing it."
                for arg in node.args:
                    if isinstance(arg, ast.Name):
                        assert arg.id in imported or arg.id in assigned, (
                            f"{script}:{node.lineno} passes undefined {arg.id!r}."
                        )




def _preflight_calls() -> dict[str, list[str]]:
    """Per script, the `why=` constant of every `sufficient_quota` call in it."""
    found: dict[str, list[str]] = {}
    for path in sorted(SCRIPTS.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
            if name != "sufficient_quota":
                continue
            why = next(
                (kw.value for kw in node.keywords if kw.arg == "why"), None
            )
            found.setdefault(path.name, []).append(
                getattr(why, "id", None) or getattr(why, "attr", None) or "<none>"
            )
    return found


def test_the_preflight_callers_are_exactly_the_ones_the_defect_record_names():
    """A claim in a permanent record, checked against the record AND the source.

    Row AD of `docs/ported_defects.md` said for one round that only
    `run_gameday_card.py` ran the free pre-flight. That was false — the probe
    ran it too — and the row was the one place a future audit would have
    looked to find the untouched sibling. It pointed away from it instead.

    So this checks BOTH halves. The earlier version of this test asserted only
    that the source agrees with `PREFLIGHT_CALLERS`, while its docstring and
    its failure message both said it was checking the record; it passed
    identically on the corrected and the uncorrected row. A prose correction
    that no test reads goes stale again the same way it went stale the first
    time, which is the whole reason this row exists.
    """
    assert set(_preflight_calls()) == set(PREFLIGHT_CALLERS), (
        "the set of scripts running the free quota pre-flight has changed, and "
        "docs/ported_defects.md row AD names it. Either a spending script "
        "stopped asking what the balance is before it spends, or a new one "
        "started and the record does not say so."
    )
    record = (Path(__file__).resolve().parents[1] / "docs" / "ported_defects.md").read_text(encoding="utf-8")
    row = next((line for line in record.splitlines() if line.lstrip().startswith("| AD ")), "")
    assert row, "docs/ported_defects.md has no row AD; the record this test names is gone"
    unnamed = sorted(name for name in PREFLIGHT_CALLERS if name not in row)
    assert not unnamed, (
        f"row AD of docs/ported_defects.md does not name {unnamed}. Every "
        "script that runs the pre-flight has to appear in the row, because the "
        "row is what the next audit reads to decide which spending paths are "
        "already covered — and a row that undercounts them points the audit "
        "away from the uncovered one."
    )


def test_each_preflight_caller_states_its_own_starvation_reason():
    """`why` has no default, so a caller cannot inherit the card's sentence
    about frozen early tips and a biased night written into the ledger. Four
    callers, four distinct constants, none of them `<none>`."""
    calls = _preflight_calls()
    reasons = []
    for script, expected in PREFLIGHT_CALLERS.items():
        assert calls[script] == [expected], (
            f"{script} passes {calls[script]} as its refusal reason rather than "
            f"{expected!r}. A caller printing another caller's reason tells the "
            "operator what a different script would have lost."
        )
        reasons.append(expected)
    assert len(set(reasons)) == len(reasons), "two callers share one reason"
