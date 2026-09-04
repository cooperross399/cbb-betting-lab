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


def full_run(extra: list[str] | None = None, drop: str | None = None) -> list[str]:
    """Two testcases for every required module, so a fixture can remove one
    testcase without emptying a module and firing the manifest check instead
    of the check under test."""
    cases: list[str] = []
    for module in gate.REQUIRED_MODULES:
        if module == drop:
            continue
        key = gate.module_key(module)
        cases.append(case(key, "test_one"))
        cases.append(case(f"{key}.TestGroup", "test_two"))
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
    assert f"{2 * len(gate.REQUIRED_MODULES)} testcases recorded" in summary
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
    xml = suite(full_run()).replace(f'tests="{2 * len(gate.REQUIRED_MODULES)}"', 'tests="0"')
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
    no business with `os`, `subprocess`, `socket` or `json`. The sweep above
    is what enforces the behaviour; this names the module if one appears."""
    import ast

    tree = ast.parse(_SCRIPT.read_text(encoding="utf-8"))
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert imported <= {"__future__", "sys", "xml", "pathlib"}, sorted(imported)


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
