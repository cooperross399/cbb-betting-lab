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


@pytest.mark.parametrize(
    "script", ["buy_historical_prices.py", "capture_line_movement.py", "run_gameday_card.py"]
)
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
