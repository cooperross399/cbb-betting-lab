#!/usr/bin/env python3
"""Fail the build on a skip, an xfail, an empty run, or a missing guard module.

    python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"

`python -m pytest -q` exits 0 on a SKIP and on an XFAIL. Green then means "the
suite did not object" rather than "the suite passed". Measured on this lab on
2026-09-04: a clean clone — which is what CI is — ran the suite as **647
passed, 80 skipped, exit 0**, every skip waiting on a gitignored table, and the
workflow's tick was green. Eighty tests that had never once run on the machine
whose tick the lab reads, and no line anywhere said so. This script is what
closes that.

A zero-collection run is NOT that case: pytest returns 5 and the step's shell
catches it. The empty-evidence checks below earn their place for a different
reason — this gate is invoked under `if: always()`, so it also runs when the
junit.xml is absent, truncated because the run died partway, or stale from an
earlier step. In none of those does an exit code reach this script, and "the
file said nothing" must never read as "nothing was wrong".

There is no allowlist, no environment variable, no flag and no sentinel file
that tolerates a skip, and there will not be one. A temporary skip is a
permanent one, and an exemption list is how the second one gets added without
anybody having to make the case for it. `tests/test_check_test_results.py`
holds this file to that by running it as a subprocess under a sweep of ambient
inputs — the environment emptied and filled, the working directory moved,
sentinel files planted — and demanding the same answer from every arm.

REQUIRED_MODULES is the other half, and it is aimed at a specific failure.
`git rm tests/test_no_secrets_committed.py tests/test_no_sibling_lab_import.py`
drops every test in two files and stays green. Deleting both hard-rule guards
makes the build GREENER, and pytest has no way to say so. Counting what ran is
the only way a deletion reads as red instead of as a smaller green. It is one
of three layers: `tests/test_the_guards_exist.py` asserts each module is
tracked and defines tests, `tests/conftest.py` stops the run at collection when
one contributed nothing, and this script reads the evidence file afterwards —
so a `-k`, a `--deselect`, a `PYTEST_ADDOPTS` or a rename that gets past one
layer has two more to get past.

No integer is quoted for the size of that drop. It is whatever
`pytest --collect-only -q <the two files>` reports today, and an absolute
written here goes stale inside a session.

Standard library only, and nothing from src/: the workflow step invokes this
with no PYTHONPATH, and the gate has to still run and still report when the
package itself is broken.

One thing this file cannot see: a NON-STRICT xpass. pytest writes it into the
XML as an ordinary passing testcase carrying no marker at all. A strict xpass
is written as a <failure> and caught below, and `xfail_strict = true` in
pyproject.toml is the only reason the xpass half of this gate is reachable at
all — remove the setting and every xpass goes invisible; mark one test
`xfail(strict=False)` and that one does. The fix lives in pyproject.toml and in
the markers; this script cannot be it.
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.etree.ElementTree import Element

#: Every module that must show up in the evidence AND must have contributed at
#: least one testcase. Checked against the classnames the XML actually records,
#: so a guard that is deleted, renamed, or edited down to zero collected tests
#: fails here instead of quietly shrinking the pass count. Adding a guard means
#: adding it here too — an unlisted test file is protected by nothing.
#:
#: The same list, in the same order, lives in `tests/test_the_guards_exist.py`
#: and `tests/conftest.py`; `test_the_guards_exist` holds the three copies
#: against each other, because this script may import neither.
REQUIRED_MODULES: tuple[str, ...] = (
    "tests/test_no_secrets_committed.py",
    "tests/test_no_sibling_lab_import.py",
    "tests/test_contract_strings.py",
    "tests/test_competition_registry_is_the_only_place.py",
    "tests/test_workflows.py",
    "tests/test_the_guards_exist.py",
    "tests/test_check_test_results.py",
    "tests/test_check_ledger_append_only.py",
)


def module_key(module: str) -> str:
    """`tests/test_contract_strings.py` -> `tests.test_contract_strings`.

    pytest records classnames dotted, relative to rootdir and without the
    suffix, and appends the class for a test defined inside one.
    """
    return module.removesuffix(".py").replace("/", ".")


def _describe(case: Element, child: Element) -> str:
    ident = f"{case.get('classname', '')}::{case.get('name', '')}".strip(":")
    kind = child.get("type") or child.tag
    message = (child.get("message") or "").strip() or "(no message recorded)"
    return f"{ident or '(unnamed testcase)'} [{kind}] {message}"


def check(path: Path) -> tuple[list[str], str]:
    """Return (reasons this run is not a pass, one-line summary of what ran).

    An empty reason list is the only thing that counts as a pass. Every early
    return here is a case where the evidence itself is missing or unreadable,
    and those return no summary because nothing was verified.
    """
    try:
        root = ET.parse(path).getroot()
    except FileNotFoundError:
        return ([f"{path} does not exist. The suite recorded no evidence, so "
                 "there is nothing to check and this run is not a pass."], "")
    except OSError as exc:
        return ([f"{path} could not be read ({exc}). A gate that cannot open "
                 "its evidence has checked nothing."], "")
    except ET.ParseError as exc:
        return ([f"{path} is not parseable XML ({exc}). A truncated or empty "
                 "evidence file is a run that did not finish."], "")

    suites = [root] if root.tag == "testsuite" else list(root.iter("testsuite"))
    if not suites:
        return ([f"{path} contains no <testsuite> element. It is XML, but it "
                 "is not a junit report, so it proves nothing."], "")

    cases = [case for suite in suites for case in suite.iter("testcase")]

    problems: list[str] = []
    skips: list[str] = []
    xfails: list[str] = []
    failures: list[str] = []
    errors: list[str] = []

    for case in cases:
        for child in case:
            if child.tag == "skipped":
                if child.get("type") == "pytest.xfail":
                    xfails.append(_describe(case, child))
                else:
                    skips.append(_describe(case, child))
            elif child.tag == "failure":
                failures.append(_describe(case, child))
            elif child.tag == "error":
                errors.append(_describe(case, child))

    if skips:
        problems.append(
            f"{len(skips)} skipped test(s). A skip is a gate that passes when "
            "it should fail. Resolve it or delete it; there is no third option "
            "and no exemption list:\n  " + "\n  ".join(skips)
        )
    if xfails:
        problems.append(
            f"{len(xfails)} xfail/xpass test(s). An expected failure is a known "
            "bug the build stopped mentioning:\n  " + "\n  ".join(xfails)
        )
    if failures:
        problems.append(f"{len(failures)} failed test(s):\n  " + "\n  ".join(failures))
    if errors:
        problems.append(
            f"{len(errors)} errored test(s). An error is a failure — a guard "
            "that cannot run has not passed:\n  " + "\n  ".join(errors)
        )

    # Counted from the elements, not trusted from the attributes: a hand-edited
    # or half-written file can claim tests="139" while carrying none.
    recorded = 0
    for suite in suites:
        raw = suite.get("tests")
        if raw is not None and raw.lstrip("-").isdigit():
            recorded += int(raw)
    if not cases:
        problems.append(
            f"0 testcases recorded in {path} (the report claims {recorded}). A "
            "run that collected nothing must never read as a pass — that is the "
            "fail-open case this gate exists for."
        )
    elif recorded == 0:
        problems.append(
            f"{len(cases)} testcase element(s) present but the report totals "
            "tests=0. The evidence contradicts itself and cannot be trusted."
        )

    # A skipped-at-collection or import-broken module is recorded with an empty
    # classname and the module in name=, so it counts as present-and-
    # contributing-nothing rather than as deleted. Different fixes.
    seen: set[str] = set()
    for case in cases:
        classname = case.get("classname") or ""
        seen.add(classname if classname else (case.get("name") or ""))

    per_module: dict[str, int] = {}
    for module in REQUIRED_MODULES:
        key = module_key(module)
        # `key + "."` and not startswith(key) alone: `tests.test_workflows_v2`
        # must not be allowed to stand in for `tests.test_workflows`.
        count = sum(
            1 for case in cases
            if (case.get("classname") or "") == key
            or (case.get("classname") or "").startswith(key + ".")
        )
        per_module[module] = count
        if count:
            continue
        if key in seen:
            problems.append(
                f"{module} is recorded but contributed 0 tests. It was skipped "
                "at collection or failed to import; either way the guard did "
                "not run."
            )
        else:
            problems.append(
                f"{module} contributed 0 tests and appears in no recorded "
                "classname. It was deleted, renamed, or collects nothing — "
                "which would otherwise make this build greener by removing a "
                "guard."
            )

    leanest = min(per_module, key=lambda m: per_module[m]) if per_module else ""
    summary = (
        f"{len(cases)} testcases recorded across {len(seen)} classnames "
        f"({recorded} reported by the run): {len(skips)} skipped, "
        f"{len(xfails)} xfailed, {len(failures)} failed, {len(errors)} errored. "
        f"{len(REQUIRED_MODULES)} required modules checked, thinnest is "
        f"{leanest} at {per_module.get(leanest, 0)} tests."
    )
    return problems, summary


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(f"usage: {argv[0] if argv else 'check_test_results.py'} <junit.xml>", file=sys.stderr)
        return 2

    path = Path(argv[1])
    problems, summary = check(path)

    if problems:
        print(f"FAIL {path}: this run does not count as a pass.", file=sys.stderr)
        for problem in problems:
            print(f"- {problem}", file=sys.stderr)
        if summary:
            print(summary, file=sys.stderr)
        return 1

    print(f"PASS {path}: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
