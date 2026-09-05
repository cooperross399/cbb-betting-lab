"""This lab may not reach into a sibling lab, and nothing was checking.

There are five betting labs in this account — NFL, NCAAF, NHL, EPL and college
basketball — one per sport, and they deliberately share no code. Machinery moves
between them by being **ported**: copied into the repository that uses it, where
it is visible and free to diverge as the sport demands.

That was a promise in a docstring until it was broken. The NCAAF lab's venv was
copied from the NFL lab's to save a few minutes of setup, and that installed
`football_betting_lab` into it as an editable package pointing at the sibling
repository. No line of code had to be written for the two labs to be coupled:
any module could have imported it and it would simply have worked, with no
error and no warning, through a path nobody reads.

Two things are asserted, because either alone is insufficient:

* no module here imports a sibling lab — catches a line someone writes;
* no sibling lab is importable from this environment — catches the environment
  making it possible in the first place.

The second is the one that actually bit. A test that only read source would have
passed all day.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: The other four labs. Named individually rather than derived, so a copied
#: venv from ANY of them fails the same way rather than only the one that
#: happened to cause this.
SIBLING_PACKAGES = ("epl_betting_lab", "football_betting_lab", "ncaaf_betting_lab", "nhl_betting_lab",)


SCAN_ROOTS = (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts", PROJECT_ROOT / "tests")


def _python_files(roots: tuple[Path, ...] = SCAN_ROOTS) -> list[Path]:
    """Every module under `roots`, and never an empty root.

    A root that yields nothing is a moved tree, and a scan over nothing finds
    nothing — the fail-open shape this suite exists to refuse.
    """
    keep: list[Path] = []
    for root in roots:
        here = [
            p for p in root.rglob("*.py")
            if ".venv" not in p.parts and p.name != Path(__file__).name
        ] if root.is_dir() else []
        assert here, f"{root} contributed no Python files to the sibling-import scan"
        keep.extend(here)
    return keep


def _imports_in(path: Path) -> list[str]:
    """Every sibling-lab import in one module, or an AssertionError naming
    the file when it does not parse. This used to `continue` on a
    SyntaxError, so an unparseable module was a module that imported nothing."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        raise AssertionError(f"{path} does not parse, so it cannot be scanned: {exc}") from exc
    offenders: list[str] = []
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names = [a.name for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            names = [node.module]
        for name in names:
            if name.split(".")[0] in SIBLING_PACKAGES:
                offenders.append(f"{path.name}:{node.lineno}: imports {name}")
    return offenders


def test_no_module_imports_a_sibling_lab() -> None:
    offenders: list[str] = []
    for path in _python_files():
        offenders.extend(_imports_in(path))
    assert not offenders, (
        "This lab imports a sibling lab. Machinery is shared by PORTING it "
        "here, visibly, never by coupling two repositories:\n  "
        + "\n  ".join(offenders)
    )


def test_the_scan_reads_a_non_empty_tree(tmp_path: Path) -> None:
    """Absence is never a pass: an empty or missing root is a red build."""
    assert len(_python_files()) > 50
    with pytest.raises(AssertionError, match="contributed no Python files"):
        _python_files(roots=(tmp_path,))
    with pytest.raises(AssertionError, match="contributed no Python files"):
        _python_files(roots=(PROJECT_ROOT / "src", tmp_path / "gone"))


def test_a_planted_sibling_import_is_found(tmp_path: Path) -> None:
    """The guard watched firing, for every spelling of an import."""
    for source in (
        "import nhl_betting_lab\n",
        "from football_betting_lab.stats import interval\n",
        "import epl_betting_lab.config as c\n",
        "from ncaaf_betting_lab import leagues\n",
    ):
        planted = tmp_path / "planted.py"
        planted.write_text(source, encoding="utf-8")
        assert _imports_in(planted), f"{source!r} was not found"
    planted.write_text("from cbb_betting_lab import config\nimport nhl_stats_unrelated\n", encoding="utf-8")
    assert _imports_in(planted) == []


def test_an_unparseable_module_is_a_failure_naming_the_file(tmp_path: Path) -> None:
    broken = tmp_path / "broken.py"
    broken.write_text("import nhl_betting_lab\ndef f(:\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="does not parse"):
        _imports_in(broken)


@pytest.mark.parametrize("package", SIBLING_PACKAGES)
def test_no_sibling_lab_is_even_importable(package: str) -> None:
    """The environment half, and the one that actually bit."""
    assert importlib.util.find_spec(package) is None, (
        f"{package} is importable from this environment. A copied venv or a "
        "stray editable install couples two labs through a path nobody reads. "
        f"Uninstall it: `.venv/bin/python -m pip uninstall "
        f"{package.replace('_', '-')}`."
    )


def test_this_lab_s_own_package_is_importable() -> None:
    """The positive control. A guard that passes because nothing is installed
    is not a guard, it is a broken environment."""
    assert importlib.util.find_spec("cbb_betting_lab") is not None
