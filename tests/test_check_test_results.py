"""The junit gate, exercised on XML instead of on a merged workflow.

The one place `scripts/check_test_results.py` runs for real is the
`.github/workflows/tests.yml` step whose command is
`python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"`. A workflow
can only be tested by merging it, so the logic lives in a script and the
script's cases live here.

The case that matters most is not the clean pass. It is the pair at the
bottom: a required module that vanished, and one that is still listed but ran
nothing. Both are what `git rm tests/test_no_secrets_committed.py` looks like
from inside the evidence file, and both make the build GREENER without this
gate. No integer is quoted for the size of that drop; it is whatever
`pytest --collect-only -q` reports today.

The waiver section is not a text match on the script. A guard that greps for
spellings proves only that those spellings are absent. What is asserted is
that the script's ANSWER does not move when its ambient input does: the same
one-skip junit is handed to a subprocess under an empty environment, a full
one, plausible waiver variables, a moved working directory and planted
sentinel files, and every arm must return the same exit code and the same
report. A waiver keyed on a literal token no arm draws is the residue, and it
is written down rather than claimed away.

Every fixture is built in tmp_path. This test reads no junit.xml from disk.
"""

from __future__ import annotations

import ast
import importlib.util
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_test_results.py"
_spec = importlib.util.spec_from_file_location("check_test_results", _SCRIPT)
assert _spec is not None and _spec.loader is not None
gate = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gate)


def case(classname: str, name: str, body: str = "") -> str:
    inner = f">{body}</testcase>" if body else " />"
    return f'<testcase classname="{classname}" name="{name}" time="0.001"{inner}'


def suite(cases: list[str], *, skipped: int = 0, failures: int = 0, errors: int = 0) -> str:
    return (
        '<?xml version="1.0" encoding="utf-8"?><testsuites name="pytest tests">'
        f'<testsuite name="pytest" errors="{errors}" failures="{failures}" '
        f'skipped="{skipped}" tests="{len(cases)}" time="0.9">'
        + "".join(cases)
        + "</testsuite></testsuites>"
    )


REPO = Path(__file__).resolve().parents[1]


def full_run(extra: list[str] | None = None, drop: str | None = None) -> list[str]:
    """One testcase for every test function every required module DECLARES.

    Read from the tree rather than fabricated, because the gate now floors
    per TEST: a fixture that invents two names per module would look, to the
    per-test check, exactly like a run that dropped everything else. A
    fixture can still remove ONE case without emptying a module, which is
    what separates the manifest check from the check under test.
    """
    cases: list[str] = []
    for module in gate.REQUIRED_MODULES:
        if module == drop:
            continue
        key = gate.module_key(module)
        declared = gate.test_functions_declared_in(REPO / module)
        assert declared, f"{module} declares no test functions; the fixture would prove nothing"
        for index, name in enumerate(declared):
            # Half of them under a class, so the classname-prefix branch of
            # the module match is exercised as well as the exact one.
            cases.append(case(key if index % 2 else f"{key}.TestGroup", name))
    return cases + (extra or [])


def write(tmp_path: Path, xml: str, name: str = "junit.xml") -> Path:
    path = tmp_path / name
    path.write_text(xml, encoding="utf-8")
    return path


SKIP = case(
    "tests.test_contract_strings", "test_x",
    '<skipped type="pytest.skip" message="the table is not built">tests/test_contract_strings.py:40: not built</skipped>',
)


def test_a_clean_run_passes(tmp_path: Path) -> None:
    problems, summary = gate.check(write(tmp_path, suite(full_run())))
    assert problems == []
    assert f"{len(full_run())} testcases recorded" in summary
    assert "0 skipped, 0 xfailed, 0 failed, 0 errored" in summary
    assert gate.main(["check_test_results.py", str(write(tmp_path, suite(full_run())))]) == 0


def test_one_skip_fails_the_run(tmp_path: Path) -> None:
    """The case the whole gate exists for: pytest exits 0 on this."""
    problems, _ = gate.check(write(tmp_path, suite(full_run([SKIP]), skipped=1)))
    assert len(problems) == 1
    assert "1 skipped test(s)" in problems[0]
    assert "tests.test_contract_strings::test_x" in problems[0]
    assert "no exemption list" in problems[0]


def test_an_xfail_fails_the_run(tmp_path: Path) -> None:
    xfail = case("tests.test_x", "test_y", '<skipped type="pytest.xfail" message="known bug">x</skipped>')
    problems, _ = gate.check(write(tmp_path, suite(full_run([xfail]), skipped=1)))
    assert len(problems) == 1 and "xfail/xpass" in problems[0]


def test_a_skipped_element_with_no_type_still_fails(tmp_path: Path) -> None:
    untyped = case("tests.test_x", "test_y", "<skipped>no type at all</skipped>")
    problems, _ = gate.check(write(tmp_path, suite(full_run([untyped]))))
    assert len(problems) == 1 and "skipped" in problems[0]


def test_failures_and_errors_fail(tmp_path: Path) -> None:
    failed = case("tests.test_x", "test_y", '<failure message="assert 1 == 2">boom</failure>')
    errored = case("tests.test_x", "test_z", '<error message="fixture broke">boom</error>')
    problems, _ = gate.check(write(tmp_path, suite(full_run([failed, errored]), failures=1, errors=1)))
    assert len(problems) == 2
    assert "1 failed test(s)" in problems[0] and "1 errored test(s)" in problems[1]


def test_an_empty_run_fails(tmp_path: Path) -> None:
    problems, _ = gate.check(write(tmp_path, suite([])))
    assert any("0 testcases recorded" in p for p in problems)


def test_a_report_that_contradicts_its_own_count_fails(tmp_path: Path) -> None:
    xml = suite(full_run()).replace(f'tests="{len(full_run())}"', 'tests="0"')
    problems, _ = gate.check(write(tmp_path, xml))
    assert any("contradicts itself" in p for p in problems)


def test_a_missing_file_fails(tmp_path: Path) -> None:
    problems, summary = gate.check(tmp_path / "nowhere.xml")
    assert len(problems) == 1 and "does not exist" in problems[0] and summary == ""


def test_a_malformed_or_empty_file_fails(tmp_path: Path) -> None:
    for text in ("<testsuites><testsuite", "", "<html/>"):
        problems, summary = gate.check(write(tmp_path, text))
        assert len(problems) == 1 and summary == ""


def test_a_deleted_required_module_fails(tmp_path: Path) -> None:
    """`git rm` of a guard, as seen from the evidence: its classname appears
    nowhere. Without this the build is GREENER for the deletion."""
    problems, _ = gate.check(write(tmp_path, suite(full_run(drop="tests/test_no_secrets_committed.py"))))
    assert len(problems) == 1
    assert "tests/test_no_secrets_committed.py contributed 0 tests and appears in no recorded classname" in problems[0]


def test_a_renamed_required_module_fails(tmp_path: Path) -> None:
    """`tests.test_workflows_v2` must not stand in for `tests.test_workflows`."""
    renamed = [case("tests.test_workflows_v2", "test_one"), case("tests.test_workflows_v2", "test_two")]
    problems, _ = gate.check(write(tmp_path, suite(full_run(renamed, drop="tests/test_workflows.py"))))
    assert len(problems) == 1 and "tests/test_workflows.py contributed 0 tests" in problems[0]


def test_a_required_module_that_ran_nothing_fails(tmp_path: Path) -> None:
    """Skipped at collection or failed to import: pytest records the module
    with an empty classname and the path in name=."""
    dropped = "tests/test_workflows.py"
    collected_nothing = case("", gate.module_key(dropped), '<error message="collection failure">x</error>')
    problems, _ = gate.check(write(tmp_path, suite(full_run([collected_nothing], drop=dropped), errors=1)))
    assert any(f"{dropped} is recorded but contributed 0 tests" in p for p in problems)
    assert not any("appears in no recorded classname" in p for p in problems)
    assert any("errored test(s)" in p for p in problems)


def test_every_problem_is_reported_at_once(tmp_path: Path) -> None:
    failed = case("tests.test_x", "test_y", '<failure message="x">boom</failure>')
    problems, _ = gate.check(write(tmp_path, suite(full_run([SKIP, failed], drop="tests/test_workflows.py"), skipped=1, failures=1)))
    assert len(problems) == 3, problems


def test_module_key_maps_paths_to_the_dotted_form() -> None:
    assert gate.module_key("tests/test_contract_strings.py") == "tests.test_contract_strings"


def test_the_manifest_names_every_hard_rule_guard() -> None:
    required = set(gate.REQUIRED_MODULES)
    for guard in (
        "tests/test_no_secrets_committed.py", "tests/test_no_sibling_lab_import.py",
        "tests/test_contract_strings.py", "tests/test_competition_registry_is_the_only_place.py",
        "tests/test_workflows.py", "tests/test_the_guards_exist.py",
        "tests/test_check_test_results.py", "tests/test_check_ledger_append_only.py",
    ):
        assert guard in required, f"{guard} is not in REQUIRED_MODULES; an unlisted guard is protected by nothing"
    for module in required:
        assert (Path(__file__).resolve().parents[1] / module).is_file(), f"{module} is required and does not exist"


def test_wrong_invocation_is_not_a_pass() -> None:
    assert gate.main(["check_test_results.py"]) == 2
    assert gate.main(["check_test_results.py", "a", "b"]) == 2


def _normalise(text: str, path: Path) -> str:
    return text.replace(str(path), "<junit>").replace(str(path.parent), "<dir>")


def _arms(tmp_path: Path, junit: Path) -> list[dict]:
    """Ambient inputs a waiver would plausibly key on. Every arm hands the
    script the same one-skip junit."""
    clean = {"PATH": os.environ.get("PATH", ""), "SYSTEMROOT": os.environ.get("SYSTEMROOT", "")}
    arms: list[dict] = [
        {"label": "empty-env", "env": clean, "cwd": tmp_path},
        {"label": "full-env", "env": dict(os.environ), "cwd": tmp_path},
        {"label": "repo-cwd", "env": clean, "cwd": _SCRIPT.parents[1]},
    ]
    for name in ("SKIP_OK", "ALLOW_SKIPS", "CI", "GITHUB_ACTIONS", "FORCE", "LEDGER_GUARD", "PYTEST_SKIPS_OK", "WAIVE", "TOLERATE_SKIPS"):
        arms.append({"label": f"env:{name}", "env": {**clean, name: "1"}, "cwd": tmp_path})
    for seed in ("0", "1", "42", "12345"):
        arms.append({"label": f"hashseed:{seed}", "env": {**clean, "PYTHONHASHSEED": seed}, "cwd": tmp_path})
    for flag in ("PYTHONDONTWRITEBYTECODE", "PYTHONOPTIMIZE", "PYTHONUTF8"):
        arms.append({"label": f"env:{flag}", "env": {**clean, flag: "1"}, "cwd": tmp_path})
    sentinel_dir = tmp_path / "sentinels"
    sentinel_dir.mkdir(exist_ok=True)
    for sentinel in (".skip-ok", ".allow-skips", "waiver", "ALLOW_SKIPS", ".ci-waiver", "skips.txt"):
        (sentinel_dir / sentinel).write_text("1\n", encoding="utf-8")
    arms.append({"label": "sentinels-in-cwd", "env": clean, "cwd": sentinel_dir})
    return arms


def test_the_gate_answers_the_same_however_it_was_started(tmp_path: Path) -> None:
    """The differential sweep. A waiver reads SOMETHING ambient; vary the
    ambient and demand the answer does not move. Blind to spelling by
    construction: `os.environ`, `os.getenv`, a from-import alias, a sentinel
    stat, a hash of a token — all show up the same way, as an arm that
    disagrees."""
    junit = write(tmp_path, suite(full_run([SKIP]), skipped=1))
    results = []
    for arm in _arms(tmp_path, junit):
        completed = subprocess.run(
            [sys.executable, str(_SCRIPT), str(junit)],
            cwd=arm["cwd"], env=arm["env"], capture_output=True, text=True, timeout=60,
        )
        results.append((arm["label"], completed.returncode, _normalise(completed.stdout + completed.stderr, junit)))
    first = results[0]
    assert first[1] == 1, f"the one-skip fixture no longer fails in the baseline arm: {first}"
    disagreeing = [r[0] for r in results if (r[1], r[2]) != (first[1], first[2])]
    assert not disagreeing, (
        f"{len(disagreeing)} of {len(results)} arms answered differently from the baseline: "
        f"{disagreeing}. The gate's verdict moved with its environment, which is what a waiver looks like."
    )


def test_the_sweep_fires_on_a_waiver_keyed_on_each_ambient_it_varies(tmp_path: Path) -> None:
    """The sweep proved to fire: a copy of the script with a waiver spliced
    in, for each dimension the arms vary, must produce a disagreeing arm."""
    junit = write(tmp_path, suite(full_run([SKIP]), skipped=1))
    source = _SCRIPT.read_text(encoding="utf-8")
    anchor = "    if skips:\n"
    assert anchor in source
    hatches = {
        "environment": "    import os as _o\n    if _o.environ.get('SKIP_OK'): skips = []\n",
        "sentinel": "    if (Path.cwd() / '.skip-ok').exists(): skips = []\n",
        "hash-seed": "    if hash('waive') % 2 == 0: skips = []\n",
        "cwd": "    if Path.cwd().name == 'sentinels': skips = []\n",
    }
    for label, hatch in hatches.items():
        spliced = tmp_path / f"gate_{label}.py"
        spliced.write_text(source.replace(anchor, hatch + anchor, 1), encoding="utf-8")
        answers = set()
        for arm in _arms(tmp_path, junit):
            completed = subprocess.run([sys.executable, str(spliced), str(junit)], cwd=arm["cwd"], env=arm["env"], capture_output=True, text=True, timeout=60)
            answers.add((completed.returncode, _normalise(completed.stdout + completed.stderr, junit)))
        assert len(answers) > 1, f"the sweep did not notice a waiver keyed on {label}"


def test_the_script_imports_only_what_it_needs() -> None:
    """A capability check, labelled as the narrow thing it is: the script has
    no business with `os`, `subprocess`, `socket` or `json`. `ast` is on the
    list because the per-test floor reads each guard's declarations, and
    reading them with `ast` rather than importing the module is what keeps a
    guard with a broken import countable. The sweep above is what enforces
    the behaviour; this names the module if a new one appears."""
    import ast

    tree = ast.parse(_SCRIPT.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= {"__future__", "ast", "sys", "xml", "pathlib"}, sorted(imported)


def test_the_known_gaps_of_the_sweep_are_written_down(tmp_path: Path) -> None:
    """A waiver keyed on a token no arm draws, or on the evidence's own shape,
    is invisible to the sweep. Asserted open: measured green through every
    arm, so review still has to read `check()`."""
    junit = write(tmp_path, suite(full_run([SKIP]), skipped=1))
    source = _SCRIPT.read_text(encoding="utf-8")
    anchor = "    if skips:\n"
    for label, hatch in {
        "literal-token": "    skips = [s for s in skips if 'zq7v' not in s]\n",
        "evidence-shape": "    if len(cases) > 5: skips = []\n",
    }.items():
        spliced = tmp_path / f"gap_{label}.py"
        spliced.write_text(source.replace(anchor, hatch + anchor, 1), encoding="utf-8")
        answers = set()
        for arm in _arms(tmp_path, junit):
            completed = subprocess.run([sys.executable, str(spliced), str(junit)], cwd=arm["cwd"], env=arm["env"], capture_output=True, text=True, timeout=60)
            answers.add(completed.returncode)
        assert len(answers) == 1, f"the sweep now sees the {label} waiver; move it out of this ledger"
    assert re.search(r"zq7v", source) is None


# --------------------------------------------------------------------------
# Collection-phase skips: run a real tree, read the real exit code.
# --------------------------------------------------------------------------

#: The two shapes that never become a test item. Both are how a test waiting
#: on a gitignored table hides from a per-item hook.
COLLECTION_SKIP_MODULES: dict[str, str] = {
    "test_module_level_skip.py": (
        "import pytest\n"
        'pytest.skip("the processed table is gitignored", allow_module_level=True)\n'
        "\n\ndef test_never_runs() -> None:\n    raise AssertionError\n"
    ),
    "test_module_level_importorskip.py": (
        "import pytest\n"
        'pytest.importorskip("a_module_this_lab_does_not_have")\n'
        "\n\ndef test_also_never_runs() -> None:\n    raise AssertionError\n"
    ),
}

_SYNTHETIC_CONFTEST = '''\
import importlib.util

_spec = importlib.util.spec_from_file_location("lab_conftest", {lab!r})
_lab = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_lab)

pytest_collectreport = _lab.pytest_collectreport
pytest_collection_modifyitems = _lab.pytest_collection_modifyitems
'''


def _synthetic_tree(root: Path, *, with_the_hooks: bool) -> Path:
    """A three-module tree: one honest module and both collection-skip shapes.

    `pytest.ini` pins the rootdir so the run cannot wander up into this
    repository's own configuration.
    """
    tests = root / "tests"
    tests.mkdir(parents=True, exist_ok=True)
    (root / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n", encoding="utf-8")
    (tests / "test_two_honest_tests.py").write_text(
        "def test_one() -> None:\n    pass\n\n\ndef test_two() -> None:\n    pass\n",
        encoding="utf-8",
    )
    for name, body in COLLECTION_SKIP_MODULES.items():
        (tests / name).write_text(body, encoding="utf-8")
    conftest = _SYNTHETIC_CONFTEST.format(lab=str(Path(__file__).resolve().parent / "conftest.py"))
    (tests / "conftest.py").write_text(conftest if with_the_hooks else "", encoding="utf-8")
    return root


def _run_pytest(root: Path, junit: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-rs", "-p", "no:cacheprovider", f"--junit-xml={junit}"],
        cwd=root, capture_output=True, text=True, timeout=300,
    )


def test_a_collection_phase_skip_is_not_a_pass(tmp_path: Path) -> None:
    """Both module-level shapes, executed, with the exit code read.

    Measured 2026-09-04 on the control arm — the same three modules with no
    hooks installed — `python -m pytest -q` reported `2 passed, 2 skipped`
    and exited **0**. That is the whole defect: a skip that arrives before
    collection finishes costs the run nothing. With the conftest hooks the
    same tree exits 1, and the junit the control arm wrote is refused by the
    gate as well, so the two nets are independent.
    """
    control = _synthetic_tree(tmp_path / "control", with_the_hooks=False)
    control_junit = tmp_path / "control.xml"
    without = _run_pytest(control, control_junit)
    assert without.returncode == 0, (
        "the control arm no longer exits 0 over a collection-phase skip; this "
        "test's premise has changed and the docstrings that rest on it are stale\n"
        + without.stdout[-2000:]
    )
    assert "2 passed" in without.stdout and "2 skipped" in without.stdout, without.stdout[-2000:]

    guarded = _synthetic_tree(tmp_path / "guarded", with_the_hooks=True)
    guarded_junit = tmp_path / "guarded.xml"
    with_hooks = _run_pytest(guarded, guarded_junit)
    assert with_hooks.returncode == 1, (
        "a module that skipped itself at collection did not stop the run\n"
        + with_hooks.stdout[-3000:] + with_hooks.stderr[-2000:]
    )
    reported = with_hooks.stdout + with_hooks.stderr
    assert "skipped at COLLECTION" in reported, reported[-3000:]
    for name in COLLECTION_SKIP_MODULES:
        assert name in reported, f"{name} is not named in the refusal:\n{reported[-3000:]}"

    # And the second net: the junit the UNGUARDED run wrote records both as
    # skipped testcases, and the gate refuses it.
    problems, _ = gate.check(control_junit)
    assert any("skipped test(s)" in problem for problem in problems), problems
    assert gate.main(["check_test_results.py", str(control_junit)]) == 1


def test_the_collection_skip_hook_is_installed_in_this_suites_conftest() -> None:
    """The hook itself, named. A synthetic tree proves the hook works; this
    proves the suite is the thing that has it."""
    conftest = Path(__file__).resolve().parent / "conftest.py"
    spec = importlib.util.spec_from_file_location("cbb_conftest_for_collectreport", conftest)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert callable(getattr(module, "pytest_collectreport", None)), (
        "tests/conftest.py defines no pytest_collectreport, so a module-level "
        "skip is invisible to every hook in the run"
    )


# --------------------------------------------------------------------------
# The floor per TEST, not per module.
# --------------------------------------------------------------------------


def test_one_deselected_test_inside_a_guard_fails_the_run(tmp_path: Path) -> None:
    """The measured attack: `--deselect` of exactly one guard test.

    On a clone of 133dabd, with that one line in pyproject.toml's `addopts`,
    the suite ran with EXACTLY ONE test deselected and this gate printed PASS.
    The module still contributed every other test it declares, so every
    per-MODULE floor was clear.
    """
    victim = "tests/test_no_secrets_committed.py"
    dropped = "test_no_tracked_file_contains_an_odds_api_key_shape"
    assert dropped in (gate.test_functions_declared_in(REPO / victim) or []), (
        f"{dropped} is no longer declared in {victim}; pick another name for this fixture"
    )
    thinned = [c for c in full_run() if f'name="{dropped}"' not in c]
    assert len(thinned) == len(full_run()) - 1

    problems, _ = gate.check(write(tmp_path, suite(thinned)))
    assert len(problems) == 1, problems
    assert "1 declared test(s) never ran" in problems[0]
    assert dropped in problems[0]
    assert gate.main(["check_test_results.py", str(write(tmp_path, suite(thinned)))]) == 1


def test_a_parametrised_test_satisfies_the_floor_under_its_own_name(tmp_path: Path) -> None:
    """pytest writes `test_x[id]`, and that must count as `test_x` having
    run — while `test_x_and_y` must never count as `test_x`."""
    assert gate._ran("test_x", {"test_x[1-a]"})
    assert gate._ran("test_x", {"test_x"})
    assert not gate._ran("test_x", {"test_x_and_y"})
    assert not gate._ran("test_x", set())


def test_the_floor_reads_the_source_tree_it_is_given(tmp_path: Path) -> None:
    """`source_root` is a parameter so the check is over a tree rather than
    over whatever happens to be beside the script. A required module that
    cannot be read there is a problem, never a pass."""
    empty_tree = tmp_path / "no-guards-here"
    (empty_tree / "tests").mkdir(parents=True)
    problems, _ = gate.check(write(tmp_path, suite(full_run())), source_root=empty_tree)
    assert len(problems) == len(gate.REQUIRED_MODULES), problems
    assert all("could not be read or parsed" in p for p in problems)


def test_a_guard_that_stopped_parsing_is_not_excused(tmp_path: Path) -> None:
    """`ast` is used and not an import, so a guard whose IMPORTS are broken
    is still counted — but one that no longer PARSES is reported, because a
    declaration count of zero would otherwise read as nothing missing."""
    broken = tmp_path / "broken-tree"
    for module in gate.REQUIRED_MODULES:
        target = broken / module
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((REPO / module).read_text(encoding="utf-8"), encoding="utf-8")
    victim = broken / gate.REQUIRED_MODULES[0]
    victim.write_text("def test_one(:\n", encoding="utf-8")
    assert gate.test_functions_declared_in(victim) is None
    problems, _ = gate.check(write(tmp_path, suite(full_run())), source_root=broken)
    assert len(problems) == 1 and "could not be read or parsed" in problems[0], problems

    # And the claim the other way: a guard whose IMPORTS are broken still has
    # its declarations counted, because `ast` reads the file and never runs it.
    victim.write_text(
        "import a_module_that_does_not_exist\n\n\ndef test_one() -> None:\n    pass\n",
        encoding="utf-8",
    )
    assert gate.test_functions_declared_in(victim) == ["test_one"]


# --------------------------------------------------------------------------
# Freshness: evidence that predates the run is not this run's evidence.
# --------------------------------------------------------------------------


def _touch(path: Path, when: float) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_text("", encoding="utf-8")
    os.utime(path, (when, when))
    return path


def test_evidence_older_than_the_marker_is_refused(tmp_path: Path) -> None:
    """`pytest --version` exits 0 and writes no junit, so whatever is at the
    gated path is what the gate would read. The marker the suite step writes
    immediately before pytest is what makes 'older than this run' visible."""
    junit = write(tmp_path, suite(full_run()))
    marker = tmp_path / "suite_started_at"

    _touch(junit, 1_000_000.0)
    _touch(marker, 2_000_000.0)
    problems, summary = gate.check(junit, newer_than=marker)
    assert len(problems) == 1 and "predates the run" in problems[0]
    assert summary == "", "nothing was verified, so nothing is summarised"
    assert gate.main(["check_test_results.py", str(junit), "--newer-than", str(marker)]) == 1

    # Written after the marker: this run's evidence, and it passes.
    _touch(junit, 2_000_001.0)
    assert gate.check(junit, newer_than=marker)[0] == []
    assert gate.main(["check_test_results.py", str(junit), "--newer-than", str(marker)]) == 0


def test_an_absent_marker_is_refused(tmp_path: Path) -> None:
    """The suite step writes the marker before it runs pytest, so no marker
    means the step died before that. `if: always()` is what brings the gate
    here at all, and 'the file said nothing' must never read as a pass."""
    junit = write(tmp_path, suite(full_run()))
    problems, summary = gate.check(junit, newer_than=tmp_path / "never_written")
    assert len(problems) == 1 and "never reached pytest" in problems[0]
    assert summary == ""


def test_the_marker_argument_is_spelled_exactly_one_way() -> None:
    """The gate's command line is pinned in tests.yml as a whole command, so
    the only shapes that must work are the two that appear there."""
    assert gate.main(["check_test_results.py"]) == 2
    assert gate.main(["check_test_results.py", "a", "b"]) == 2
    assert gate.main(["check_test_results.py", "a", "--older-than", "b"]) == 2
    assert gate.main(["check_test_results.py", "a", "--newer-than", "b", "c"]) == 2

def _without_its_last_test(source: str) -> str:
    """`source` with its last top-level test removed, decorator included.

    This used to cut at `source.rindex("def test_")`, which assumed the last
    test in tests/test_contract_strings.py carries no decorator — a property of
    somebody else's file that nothing stated and nothing enforced. A sibling
    session appended a parametrized test there, the cut landed BELOW its
    `@pytest.mark.parametrize`, the truncated file stopped parsing,
    `test_functions_declared_in` returned None and CI went red on
    `assert kept is not None`. It was green locally for both of us, because
    only CI runs the whole suite.

    Cutting from the decorator makes the fixture independent of what anyone
    appends to that file, which is the property it needed all along.
    """
    tree = ast.parse(source)
    tests = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]
    assert len(tests) > 1, "the victim file must define more than one test"
    last = tests[-1]
    first_line = min([last.lineno] + [d.lineno for d in last.decorator_list])
    return "\n".join(source.splitlines()[: first_line - 1]) + "\n"



def test_the_gaps_the_per_test_floor_still_has_are_written_down(tmp_path: Path) -> None:
    """What the floor per test does NOT reach, asserted open and measured.

    1. A test DELETED outright. The floor compares the declarations against
       the evidence, and deleting the `def` removes it from both sides.
       Measured by deleting the last test function of
       `tests/test_contract_strings.py`: the suite collected and passed
       EXACTLY ONE test fewer, and this gate printed PASS. `MINIMUM_TESTS = 5`
       in `tests/test_the_guards_exist.py` is the only floor left there, so a
       guard may shrink all the way down to that number and stay green.
    2. The floor covers the eight REQUIRED modules and no others. A test
       deselected inside `tests/test_replication.py` is caught by the
       conftest's narrowing read, not by this file — and if it were dropped
       by something the conftest cannot see, this gate would not object.
       Widening it needs `git ls-files`, and this script may not spawn a
       subprocess: `test_the_script_imports_only_what_it_needs` is that rule.
    3. A test RENAMED on both sides passes, because both sides move together.

    Each is exercised below, so a gap that closes turns this red and the
    sentence gets rewritten rather than outliving the fix.
    """
    victim = "tests/test_contract_strings.py"
    declared = gate.test_functions_declared_in(REPO / victim)
    assert declared and len(declared) > 1

    # 1. Deleted from the source AND from the evidence: nothing to compare.
    source = (REPO / victim).read_text(encoding="utf-8")
    shorter = tmp_path / "shorter-tree"
    for module in gate.REQUIRED_MODULES:
        target = shorter / module
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((REPO / module).read_text(encoding="utf-8"), encoding="utf-8")
    (shorter / victim).write_text(_without_its_last_test(source), encoding="utf-8")
    kept = gate.test_functions_declared_in(shorter / victim)
    assert kept is not None and len(kept) == len(declared) - 1
    thinned = [c for c in full_run() if f'name="{declared[-1]}"' not in c]
    assert gate.check(write(tmp_path, suite(thinned)), source_root=shorter)[0] == [], (
        "a deleted test is now visible to the floor; move this out of the ledger"
    )

    # 2. A module that is not required is not floored here at all.
    assert "tests/test_replication.py" not in gate.REQUIRED_MODULES

    # 3. Renamed on both sides.
    renamed_source = source.replace(declared[0], declared[0] + "_v2")
    renamed_tree = tmp_path / "renamed-tree"
    for module in gate.REQUIRED_MODULES:
        target = renamed_tree / module
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text((REPO / module).read_text(encoding="utf-8"), encoding="utf-8")
    (renamed_tree / victim).write_text(renamed_source, encoding="utf-8")
    renamed_cases = [
        c.replace(f'name="{declared[0]}"', f'name="{declared[0]}_v2"') for c in full_run()
    ]
    assert gate.check(write(tmp_path, suite(renamed_cases)), source_root=renamed_tree)[0] == []
