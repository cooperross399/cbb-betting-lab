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


def tracked_test_modules() -> tuple[str, ...]:
    """`tests/conftest.py`'s list, read from the file under test rather than
    reimplemented, so the two cannot drift."""
    spec = importlib.util.spec_from_file_location("cbb_conftest_for_tracking", REPO / "tests" / "conftest.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.tracked_test_modules()


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
    "tests/test_player_shapes_provenance.py",
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


def test_the_hook_reads_the_narrowing_pytest_actually_received(tmp_path: Path) -> None:
    """A `--deselect` of ONE test in a guard, observed rather than spelled.

    Measured on a clone of 133dabd, the commit this branch sits on: with that
    deselect in pyproject.toml's `addopts` the suite ran with EXACTLY ONE test
    deselected, the per-module count hook stayed quiet because the module still
    contributed every other test it declares, and
    `scripts/check_test_results.py` printed PASS.
    Every arm below sets the same narrowing by a different route — the command
    line, the environment, an ini file's `addopts` — and every arm must stop
    the run, because what is read is the option pytest RESOLVED and not the
    text that produced it.
    """
    import sys

    one_guard_test = "tests/test_no_secrets_committed.py::test_no_tracked_file_contains_an_odds_api_key_shape"
    assert "test_no_tracked_file_contains_an_odds_api_key_shape" in functions_named_test_in(
        REPO / "tests/test_no_secrets_committed.py"
    ), "the fixture names a test that no longer exists"

    from_the_command_line = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "--deselect", one_guard_test],
        cwd=REPO, capture_output=True, text=True, timeout=600,
    )
    assert from_the_command_line.returncode == 1, from_the_command_line.stdout[-2000:]
    assert "narrows the suite" in from_the_command_line.stdout + from_the_command_line.stderr

    from_the_environment = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q"],
        cwd=REPO, capture_output=True, text=True, timeout=600,
        env={**os.environ, "PYTEST_ADDOPTS": f"--deselect {one_guard_test}"},
    )
    assert from_the_environment.returncode == 1, "a PYTEST_ADDOPTS deselect of one guard test must stop the run"

    # And from an ini file, which no command line shows at all. A sandbox
    # tree, so the real pyproject.toml is never edited, with a conftest that
    # re-exports THIS repository's hooks — the file under test runs, and the
    # required-guard half of it finds nothing in scope, so the narrowing is
    # the only thing that can stop the run.
    sandbox = tmp_path / "ini"
    (sandbox / "tests").mkdir(parents=True)
    (sandbox / "tests" / "test_two_tests.py").write_text(
        "def test_a() -> None:\n    pass\n\n\ndef test_b() -> None:\n    pass\n", encoding="utf-8"
    )
    (sandbox / "tests" / "conftest.py").write_text(
        "import importlib.util\n"
        f"_spec = importlib.util.spec_from_file_location('lab_conftest', {str(REPO / 'tests' / 'conftest.py')!r})\n"
        "_lab = importlib.util.module_from_spec(_spec)\n"
        "_spec.loader.exec_module(_lab)\n"
        "pytest_collectreport = _lab.pytest_collectreport\n"
        "pytest_collection_modifyitems = _lab.pytest_collection_modifyitems\n",
        encoding="utf-8",
    )
    base = '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n'
    (sandbox / "pyproject.toml").write_text(base, encoding="utf-8")
    clean = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=sandbox, capture_output=True, text=True, timeout=600,
    )
    assert clean.returncode == 0, clean.stdout[-2000:] + clean.stderr[-2000:]

    (sandbox / "pyproject.toml").write_text(
        base + 'addopts = "--deselect tests/test_two_tests.py::test_b"\n', encoding="utf-8"
    )
    from_the_ini = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=sandbox, capture_output=True, text=True, timeout=600,
    )
    assert from_the_ini.returncode == 1, (
        "an addopts in the ini file must stop the run; nothing on the command "
        "line shows it\n" + from_the_ini.stdout[-2000:]
    )
    assert "narrows the suite" in from_the_ini.stdout + from_the_ini.stderr
    assert "addopts in the ini file" in from_the_ini.stdout + from_the_ini.stderr


# --------------------------------------------------------------------------
# Shadow modules: the suite line is not the only way to replace the suite.
# --------------------------------------------------------------------------

#: Basenames that get in FRONT of the installed package when the interpreter
#: starts. `python -m pytest` puts the working directory at the head of
#: sys.path, so a tracked `pytest.py` at the root IS pytest for that run;
#: `sitecustomize`/`usercustomize` are imported by `site` before any of this
#: repository's code runs and can set `PYTEST_ADDOPTS` for it.
FORBIDDEN_TRACKED_BASENAMES = frozenset({"pytest.py", "coverage.py", "sitecustomize.py", "usercustomize.py"})

#: The same capability as a package rather than a module. `_pytest` is on the
#: list because `import pytest` immediately imports `_pytest`; a tracked
#: `_pytest/` at the root that merely re-exported the installed one would sit
#: in front of every internal pytest imports.
FORBIDDEN_DIRECTORY_NAMES = frozenset({"pytest", "coverage", "_pytest"})

TESTS_WORKFLOW = REPO / ".github" / "workflows" / "tests.yml"


def _declared_pythonpath_entries() -> list[str]:
    """Every path `tests.yml` puts on PYTHONPATH, from the parsed tree.

    An `env:` mapping anywhere in the file — workflow, job or step — and the
    value split on `:` the way the interpreter splits it. A directory that is
    on PYTHONPATH is a directory whose contents can shadow a package.
    """
    import yaml

    document = yaml.safe_load(TESTS_WORKFLOW.read_text(encoding="utf-8"))
    entries: list[str] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            environment = node.get("env")
            if isinstance(environment, dict):
                for key, value in environment.items():
                    if str(key).strip().upper() == "PYTHONPATH" and isinstance(value, str):
                        entries.extend(part for part in value.split(":") if part.strip())
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(document)
    return entries


def test_no_tracked_file_shadows_pytest_or_the_interpreter_start() -> None:
    """A tracked root `pytest.py` replaces the suite without touching the workflow.

    Measured on a clone of 133dabd: a `pytest.py` written at the repository
    root, whose `main()` printed a line and returned 0, turned
    `python -m pytest -q -rs --junit-xml=...` into `everything is fine`, exit
    **0**, and no junit file at all. Every rule in `tests/test_workflows.py`
    reads the workflow, and the workflow was untouched. The same measurement
    with `PYTHONSAFEPATH=1` in the environment printed the real pytest's own
    version banner instead, which is why the suite step sets it and
    `check_the_suite_step_disables_the_path_shadows` requires it.
    """
    offenders = sorted(p for p in tracked_files() if Path(p).name in FORBIDDEN_TRACKED_BASENAMES)
    assert not offenders, (
        f"tracked files shadow the tools that run this suite: {offenders}. "
        "`python -m pytest` searches the working directory before site-packages, "
        "and `site` imports sitecustomize before anything here runs."
    )


def test_no_tracked_directory_shadows_pytest_on_a_path_the_workflow_declares() -> None:
    """The package spelling of the same shadow, at the root and on PYTHONPATH."""
    tracked = tracked_files()
    roots = [""] + [entry.strip().strip("/") for entry in _declared_pythonpath_entries()]
    offenders: list[str] = []
    for root in roots:
        prefix = f"{root}/" if root else ""
        for name in sorted(FORBIDDEN_DIRECTORY_NAMES):
            directory = f"{prefix}{name}/"
            if any(path.startswith(directory) for path in tracked):
                offenders.append(directory)
    assert not offenders, (
        f"tracked packages shadow pytest or coverage on an import path this "
        f"repository puts first: {sorted(set(offenders))}"
    )


def test_the_shadow_this_guard_forbids_really_shadows(tmp_path: Path) -> None:
    """The measurement the ban rests on, kept as a test rather than recalled.

    A `pytest.py` in the working directory wins over the installed package
    for `python -m pytest`, and `PYTHONSAFEPATH=1` is what takes it back.
    Both halves are executed here; if either stops being true, the ban and
    the workflow's env are resting on a stale fact and this goes red.
    """
    import sys

    (tmp_path / "pytest.py").write_text(
        "import sys\n\n\ndef main(*a, **k):\n    print('shadowed')\n    return 0\n\n\n"
        "if __name__ == '__main__':\n    sys.exit(main())\n",
        encoding="utf-8",
    )
    environment = {k: v for k, v in os.environ.items() if k != "PYTHONSAFEPATH"}
    shadowed = subprocess.run(
        [sys.executable, "-m", "pytest", "--version"],
        cwd=tmp_path, capture_output=True, text=True, timeout=120, env=environment,
    )
    assert "shadowed" in shadowed.stdout, (
        "a pytest.py in the working directory no longer shadows the installed "
        f"pytest; the ban above may be stale. stdout={shadowed.stdout!r}"
    )
    safe = subprocess.run(
        [sys.executable, "-m", "pytest", "--version"],
        cwd=tmp_path, capture_output=True, text=True, timeout=120,
        env={**environment, "PYTHONSAFEPATH": "1"},
    )
    assert "shadowed" not in safe.stdout + safe.stderr, (
        "PYTHONSAFEPATH=1 no longer removes the working directory from sys.path; "
        "the suite step's env is not the defence this claims"
    )
    assert "pytest" in (safe.stdout + safe.stderr).lower()


def test_a_module_dropped_by_collect_ignore_stops_the_run(tmp_path: Path) -> None:
    """A conftest can drop a whole module before collection, and no option shows it.

    `collect_ignore` is not a command-line narrowing and not a per-item hook's
    business: pytest simply never collects the file. Measured on a clone of
    133dabd with `collect_ignore = ["test_replication.py"]` appended to
    `tests/conftest.py`: the run came back TWENTY-SIX tests short of the clean
    collection, exit 0, and `scripts/check_test_results.py` printed PASS —
    a whole module gone under a green tick, because `test_replication.py` is
    not one of the eight named guards.

    The floor is now every `tests/test_*.py` git tracks. Exercised on a clone
    of this repository so the real `git ls-files` answers, with this
    repository's conftest copied over the clone's so the hook under test is
    the one on disk here.
    """
    import shutil
    import sys

    sandbox = tmp_path / "clone"
    subprocess.run(["git", "clone", "--quiet", str(REPO), str(sandbox)], check=True, timeout=600)
    shutil.copy(REPO / "tests" / "conftest.py", sandbox / "tests" / "conftest.py")

    clean = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=sandbox, capture_output=True, text=True, timeout=600,
    )
    assert clean.returncode == 0, clean.stdout[-3000:] + clean.stderr[-2000:]

    victim = "test_replication.py"
    assert (sandbox / "tests" / victim).is_file(), f"{victim} is not in the clone"
    with (sandbox / "tests" / "conftest.py").open("a", encoding="utf-8") as handle:
        handle.write(f'\n\ncollect_ignore = ["{victim}"]\n')

    dropped = subprocess.run(
        [sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider"],
        cwd=sandbox, capture_output=True, text=True, timeout=600,
    )
    assert dropped.returncode == 1, (
        "a module dropped by collect_ignore did not stop the run\n" + dropped.stdout[-3000:]
    )
    reported = dropped.stdout + dropped.stderr
    assert "tracked test module(s) collected nothing" in reported, reported[-3000:]
    assert f"tests/{victim}" in reported, reported[-3000:]


def test_the_tracked_module_floor_knows_what_git_tracks() -> None:
    """The floor is only as real as the list behind it."""
    modules = tracked_test_modules()
    assert modules, "git ls-files reported no test modules; the floor would pass on anything"
    assert "tests/test_the_guards_exist.py" in modules
    for guard in REQUIRED_GUARDS:
        assert guard in modules, f"{guard} is a required guard that git does not track"
