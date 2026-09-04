"""The guard manifest: every hard-rule guard is tracked, defines tests, and is listed everywhere it must be.

`git rm tests/test_no_secrets_committed.py tests/test_no_sibling_lab_import.py`
used to leave this suite green with BETTER metrics — fewer tests, all
passing. Nothing counted the guards, so a deleted guard was a smaller green.
Three layers now do, and this file is the one that runs inside the suite:

1. every module in `REQUIRED_GUARDS` is tracked by git (`git ls-files`), not
   merely present on disk — an untracked copy is a copy the next clone does
   not have;
2. every one parses and defines at least `MINIMUM_TESTS` test functions
   (`ast.parse`, counting `def test_*` at module level and inside classes),
   so a guard edited down to a stub is a red build;
3. the three copies of the manifest — this list, `tests/conftest.py`'s
   `REQUIRED_GUARD_MODULES` and `scripts/check_test_results.py`'s
   `REQUIRED_MODULES` — agree exactly. The script may import neither, so
   the agreement is asserted here by reading it.

`tests/conftest.py` catches what this file cannot: a run that never collected
this file. A `-k`, a `--deselect`, an `--ignore` or a `PYTEST_ADDOPTS` drops
a guard from the run without touching the file, and a test inside the run
cannot see that it was not collected — the collection hook can, and it stops
the run with exit code 1. `scripts/check_test_results.py` catches it a third
time from the junit, after the fact, in CI.

This file lists itself. A manifest that does not name itself can be deleted
with the guards it names.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]

#: The hard-rule guards. Adding a guard means adding it to all three lists.
REQUIRED_GUARDS: tuple[str, ...] = (
    "tests/test_no_secrets_committed.py",
    "tests/test_no_sibling_lab_import.py",
    "tests/test_contract_strings.py",
    "tests/test_competition_registry_is_the_only_place.py",
    "tests/test_workflows.py",
    "tests/test_the_guards_exist.py",
    "tests/test_check_test_results.py",
    "tests/test_check_ledger_append_only.py",
)

#: A guard with fewer test functions than this has been hollowed out.
MINIMUM_TESTS = 5


def tracked_files() -> set[str]:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=REPO, capture_output=True, check=True)
    return {item for item in result.stdout.decode("utf-8").split("\0") if item}


def functions_named_test_in(path: Path) -> list[str]:
    """Every `def test_*` in the module, at module level or inside a class.

    A SyntaxError is a failure naming the file, never a zero: an unparseable
    guard is a guard that enforces nothing.
    """
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        raise AssertionError(f"{path} does not parse: {exc}") from exc
    found: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
            found.append(node.name)
    return found


def test_the_manifest_names_this_file() -> None:
    assert "tests/test_the_guards_exist.py" in REQUIRED_GUARDS


@pytest.mark.parametrize("module", REQUIRED_GUARDS)
def test_every_required_guard_is_tracked_by_git(module: str) -> None:
    assert module in tracked_files(), (
        f"{module} is not tracked by git. Present on disk is not enough: a guard the "
        "next clone does not have is a guard that does not exist."
    )


@pytest.mark.parametrize("module", REQUIRED_GUARDS)
def test_every_required_guard_defines_enough_tests(module: str) -> None:
    path = REPO / module
    assert path.is_file(), f"{module} is missing"
    found = functions_named_test_in(path)
    assert len(found) >= MINIMUM_TESTS, (
        f"{module} defines {len(found)} test function(s); at least {MINIMUM_TESTS} are "
        f"required. A guard edited down to a stub is a guard that has been removed."
    )


def test_the_three_copies_of_the_manifest_agree() -> None:
    """conftest.py, this file and the junit gate script name the same guards
    in the same order. The script is loaded by path because it may not be
    imported from the package."""
    conftest_path = REPO / "tests" / "conftest.py"
    script_path = REPO / "scripts" / "check_test_results.py"
    assert conftest_path.is_file() and script_path.is_file()

    def constant_tuple(path: Path, name: str) -> tuple[str, ...]:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            targets = []
            if isinstance(node, ast.Assign):
                targets = node.targets
            elif isinstance(node, ast.AnnAssign):
                targets = [node.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id == name:
                    value = ast.literal_eval(node.value)
                    return tuple(value)
        raise AssertionError(f"{path.name} defines no {name}")

    assert constant_tuple(conftest_path, "REQUIRED_GUARD_MODULES") == REQUIRED_GUARDS
    assert constant_tuple(script_path, "REQUIRED_MODULES") == REQUIRED_GUARDS


def test_the_collection_hook_is_installed() -> None:
    """The hook is what catches a deselected guard; a conftest without it is
    a conftest with a docstring."""
    spec = importlib.util.spec_from_file_location("cbb_conftest", REPO / "tests" / "conftest.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(getattr(module, "pytest_collection_modifyitems", None))


def test_the_collection_hook_stops_a_run_that_dropped_a_guard(tmp_path: Path) -> None:
    """Executed, not reasoned about: a real pytest subprocess over this
    repository with one required guard deselected must exit 1 before any
    test runs, and a run over everything must collect."""
    import sys

    deselected = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "--ignore=tests/test_no_secrets_committed.py"],
        cwd=REPO, capture_output=True, text=True, timeout=600,
    )
    assert deselected.returncode == 1, deselected.stdout[-2000:] + deselected.stderr[-2000:]
    assert "contributed zero collected tests" in deselected.stdout + deselected.stderr

    narrowed = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-k", "not secrets"],
        cwd=REPO, capture_output=True, text=True, timeout=600,
    )
    assert narrowed.returncode == 1, "a -k that filters a guard out must stop the run"

    deselected_one = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/test_the_guards_exist.py", "-k", "nothing_matches_this"],
        cwd=REPO, capture_output=True, text=True, timeout=600,
    )
    assert deselected_one.returncode == 1, "a guard named on the command line and then filtered to nothing must stop the run"

    addopts = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=REPO, capture_output=True, text=True, timeout=600,
        env={**os.environ, "PYTEST_ADDOPTS": "--ignore=tests/test_workflows.py"},
    )
    assert addopts.returncode == 1, "PYTEST_ADDOPTS that drops a guard must stop the run"

    # A developer running ONE file is not a narrowing: the other guards are
    # out of scope, this one is in scope and collects, and the run proceeds.
    # In CI the workflow linter is what refuses a positional on the required
    # check; this hook is for the drops no command line shows.
    positional = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "tests/test_the_guards_exist.py"],
        cwd=REPO, capture_output=True, text=True, timeout=600,
    )
    assert positional.returncode == 0, positional.stdout[-2000:] + positional.stderr[-2000:]

    everything = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=REPO, capture_output=True, text=True, timeout=600,
    )
    assert everything.returncode == 0, everything.stdout[-2000:] + everything.stderr[-2000:]


def test_a_stub_module_is_counted_as_hollow(tmp_path: Path) -> None:
    stub = tmp_path / "test_stub.py"
    stub.write_text("def test_one():\n    pass\n", encoding="utf-8")
    assert functions_named_test_in(stub) == ["test_one"]
    broken = tmp_path / "test_broken.py"
    broken.write_text("def test_one(:\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="does not parse"):
        functions_named_test_in(broken)
