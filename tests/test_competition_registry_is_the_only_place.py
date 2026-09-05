"""No sport literal may appear outside the competition registry.

CLAUDE.md, `competitions.py` and `providers/odds_api.py` all cited this file
by name as the thing that "fails the build when a sport literal appears
anywhere else", and until 2026-09-04 it did not exist. Written, and run, it
found four: the data-directory segment `"cbb"` hardcoded in `data/hoopr.py`
(twice) and `scripts/estimate_credit_cost.py`, and the provider sport key
written into two report strings. All four now read the registry. A citation
that points at a file that is not there is a rule that is not enforced, and
the honest thing to say about this one is that it was not, for the whole of
the build so far.

What is banned, precisely, in every non-docstring `str` or `bytes` constant
under `src/` and `scripts/` other than `competitions.py`:

* a provider sport key — the men's key, its futures key, and the women's
  key `basketball_wncaab` that is deliberately absent from the registry —
  anywhere in the constant. Not the bare prefix `basketball_`: hoopR names
  its release assets `espn_mens_college_basketball_*`, and those are the
  data source's vocabulary, not the provider's;
* the competition key `cbb` as a VALUE: a whole string, a whole path
  segment (`data/cbb/raw`, `cbb/schedules`), or a piece of a non-prose
  segment split on every character that is not `[a-z0-9_-]` (`cbb.csv`,
  `h2h:cbb`, `?sport=cbb`). A segment that carries whitespace is prose and
  is skipped; whitespace and bracketing are stripped off the edges first.

What is deliberately NOT banned, and said plainly rather than implied:

* the letters cbb in prose — a docstring or a message explaining the lab;
* the `cbb_` OUTPUT PREFIX on a filename (`cbb_team_games.csv`,
  `cbb_experiment_ledger.md`), which `Competition.output_name` exists to
  supply and which this repository nonetheless writes as literals in more
  than twenty places. Banning those would fail the processed-table names the
  whole lab is built on, and a rule that rejects correct code gets deleted.
  The contract outputs are held to the prefix by
  `tests/test_contract_strings.py::test_every_output_is_competition_prefixed`;
  the rest of the convention is UNENFORCED, and this docstring is where that
  is written down;
* `-` as a join. `cbb-betting-lab` is the repository's own name in one URL,
  and `cbb-x.csv` therefore passes too. The gap is asserted open in
  `test_the_shapes_this_guard_still_lets_through`.

`tests/` is outside the scan: this module holds the banned literals as data.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from cbb_betting_lab.competitions import CBB, COMPETITIONS, competition_keys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
REGISTRY = PROJECT_ROOT / "src" / "cbb_betting_lab" / "competitions.py"

BANNED_COMPETITION_KEYS = frozenset(competition_keys())
#: The men's sport key and its futures keys, from the registry, plus the
#: women's key the registry will never hold — so a session that widens the
#: lab by literal is caught even though no entry names the key.
WOMENS_SPORT_KEY = "basketball_wncaab"
BANNED_SPORT_KEYS = frozenset({CBB.provider_sport_key, *CBB.futures_sport_keys, WOMENS_SPORT_KEY})
BANNED_SPORT_KEY_PREFIX = "basketball_ncaab"
SCAN_ROOTS = (PROJECT_ROOT / "src", PROJECT_ROOT / "scripts")

PATH_SEPARATORS = re.compile(r"[\\/]")
SEGMENT_IS_PROSE = re.compile(r"\s")
#: The complement of a name's characters, minus `_` (handled as a prefix by
#: the output convention, which is not enforced here) and minus `-` (see the
#: module docstring). A complement and not a list: under a list, a character
#: nobody thought of hides a key.
NAME_JOINS = re.compile(r"[^a-z0-9_-]")
EDGE_NOISE = re.compile(r"^[\s\"'`()\[\]{}<>]+|[\s\"'`()\[\]{}<>]+$")


def python_files(roots: tuple[Path, ...] = SCAN_ROOTS) -> list[Path]:
    """Every module under `roots`, and never an empty list: a moved tree is a
    red build, not a guard that read nothing."""
    found: list[Path] = []
    for root in roots:
        here = [p for p in root.rglob("*.py") if "__pycache__" not in p.parts and p != REGISTRY]
        if not here:
            raise AssertionError(f"{root} contributed no Python files to the sport-literal scan")
        found.extend(here)
    return sorted(found)


def docstring_nodes(tree: ast.AST) -> set[int]:
    found: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = getattr(node, "body", [])
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) and isinstance(body[0].value.value, str):
                found.add(id(body[0].value))
    return found


def strip_edges(text: str) -> str:
    return EDGE_NOISE.sub("", text)


def names_competition_key(text: str, key: str) -> bool:
    lowered = text.lower()
    for segment in PATH_SEPARATORS.split(lowered):
        if strip_edges(segment) == key:
            return True
        if SEGMENT_IS_PROSE.search(segment):
            continue
        for piece in NAME_JOINS.split(strip_edges(segment)):
            if piece == key:
                return True
    return False


def constant_text(node: ast.Constant) -> str | None:
    if isinstance(node.value, str):
        return node.value
    if isinstance(node.value, bytes):
        return node.value.decode("utf-8", errors="replace")
    return None


def offending_strings(path: Path) -> list[tuple[int, str]]:
    """A SyntaxError is a failure naming the file, never a `continue`."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        raise AssertionError(f"{path} does not parse: {exc}") from exc
    exempt = docstring_nodes(tree)
    problems: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        text = constant_text(node)
        if text is None or id(node) in exempt:
            continue
        if any(key in text.lower() for key in BANNED_SPORT_KEYS):
            problems.append((node.lineno, text))
            continue
        if any(names_competition_key(text, key) for key in BANNED_COMPETITION_KEYS):
            problems.append((node.lineno, text))
    return problems


@pytest.mark.parametrize("path", python_files(), ids=lambda p: str(p.relative_to(PROJECT_ROOT)))
def test_no_module_outside_the_registry_writes_a_sport_literal(path: Path) -> None:
    problems = offending_strings(path)
    assert not problems, (
        f"{path.relative_to(PROJECT_ROOT)} writes a sport literal that belongs in "
        f"competitions.py: {problems}. Take it from the Competition — "
        "`CBB.provider_sport_key`, `CBB.data_dir_segment`, `CBB.futures_sport_keys`."
    )


def test_a_root_that_contributes_no_files_fails_rather_than_scanning_nothing(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="contributed no Python files"):
        python_files(roots=(tmp_path,))
    with pytest.raises(AssertionError, match="contributed no Python files"):
        python_files(roots=(PROJECT_ROOT / "src", tmp_path))
    assert python_files(roots=(PROJECT_ROOT / "src",))
    assert python_files(roots=(PROJECT_ROOT / "scripts",))


def test_the_registry_holds_exactly_the_competition_that_is_built() -> None:
    """Men's D-I and nothing else. Women's basketball and the lower divisions
    are separate repositories if they ever happen."""
    assert competition_keys() == ("cbb",)
    assert set(COMPETITIONS) == {"cbb"}
    assert CBB.provider_sport_key == BANNED_SPORT_KEY_PREFIX
    assert WOMENS_SPORT_KEY not in BANNED_SPORT_KEY_PREFIX
    assert all(key.startswith(BANNED_SPORT_KEY_PREFIX) for key in CBB.futures_sport_keys)
    assert CBB.data_adapter and CBB.market_registry and CBB.daily_credit_cap > 0


def test_outputs_are_competition_prefixed() -> None:
    assert CBB.output_name("forward_evidence", ".md") == "cbb_forward_evidence.md"
    assert CBB.policy_key().endswith(":cbb")


MUST_FLAG = (
    "cbb", "CBB", "data/cbb/raw", "data/raw/cbb", "cbb/schedules", "/cbb", "cbb/", "./cbb",
    "cbb.csv", "data\\raw\\cbb", "(cbb)", "'cbb'", "cbb\n", " cbb ", "h2h:cbb",
    "?sport=cbb&mkt=h2h", "data.cbb", "data/{cbb}/raw", "$cbb/raw", "glob/cbb*/x",
    "data/[cbb]/raw", "data/ cbb/raw",
)
MUST_PASS = (
    "the cbb season", "CBB card — ", "no cbb games were returned", "cbb_team_games.csv",
    "cbb_experiment_ledger.md", "cbb-betting-lab", "https://github.com/cooperross399/cbb-betting-lab",
    "cbb_betting_lab.models.ratings:matchups_for", "CBB_ODDS_API_KEY", "{competition}_summary.md",
    "ncaab", "xcbb", "cbbd", "espn_mens_college_basketball_schedules",
)
ATTACK_SHAPES = (
    "data/{cbb}/raw", "raw/cbb{}", "data/${cbb}/raw", "data/cbb%2Fraw", "%cbb%/out", "$cbb/raw",
    "raw/#cbb", "reports/cbb!/x", "cache/cbb;raw", "s3://bucket@cbb/raw", "raw/@cbb", "glob/cbb*/x",
    "data/[cbb]/raw", "data/(cbb)/raw", "~cbb/raw", "data/ cbb", "data/cbb /raw", "out/\tcbb/x",
    "data/\vcbb/raw", "data/ cbb/raw", "( cbb )/raw",
)


def test_names_competition_key_flags_the_shapes_this_docstring_claims() -> None:
    for text in MUST_FLAG:
        assert names_competition_key(text, "cbb"), f"{text!r} names the competition key"
    for text in MUST_PASS:
        assert not names_competition_key(text, "cbb"), f"{text!r} is not a sport literal and flagging it would fail correct code"


def test_a_key_hidden_by_a_non_name_character_is_still_found() -> None:
    missed = [text for text in ATTACK_SHAPES if not names_competition_key(text, "cbb")]
    assert not missed, f"{len(missed)} of {len(ATTACK_SHAPES)} attack shapes hide the key: {missed}"


def test_the_guard_still_flags_the_literals_this_module_holds() -> None:
    """The reason `tests/` is outside SCAN_ROOTS, checked rather than trusted."""
    flagged = {text for _, text in offending_strings(Path(__file__).resolve())}
    assert WOMENS_SPORT_KEY in flagged
    assert "cbb" in flagged
    assert set(ATTACK_SHAPES) <= flagged


def test_the_guard_reads_a_key_that_is_a_constant(tmp_path: Path) -> None:
    caught = {
        "plain literal": 'KEY = "cbb"\n',
        "implicit concatenation": 'KEY = "cb" "b"\n',
        "f-string literal part": 'P = f"data/{root}/cbb/raw"\n',
        "provider sport key": 'S = "basketball_ncaab"\n',
        "futures sport key": 'S = "basketball_ncaab_championship_winner"\n',
        "the women's key, which no registry entry will ever hold": 'S = "basketball_wncaab"\n',
        "a sport key inside a URL": 'U = "https://x/v4/sports/basketball_ncaab/odds"\n',
        "policy key": 'K = "h2h:cbb"\n',
        "bytes literal": 'KEY = b"cbb"\n',
        "bytes decoded into a Path": 'from pathlib import Path\nP = Path(b"data/cbb/raw".decode())\n',
        "the four real findings, shape 1": 'P = root / "cbb" / self.directory\n',
        "the four real findings, shape 2": 'MSG = f"for `basketball_ncaab`."\n',
    }
    for label, source in caught.items():
        module = tmp_path / "caught.py"
        module.write_text(source, encoding="utf-8")
        assert offending_strings(module), f"{label} writes a sport literal"
    broken = tmp_path / "broken.py"
    broken.write_text("def f(:\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="does not parse"):
        offending_strings(broken)


def test_the_shapes_this_guard_still_lets_through(tmp_path: Path) -> None:
    """The known-gaps ledger, asserted open so it cannot go stale.

    1. The `cbb_` output prefix and a `-` join: `cbb_prices.csv`, `cbb-x.csv`.
       Deliberate — see the module docstring — and the prefix convention is
       unenforced here.
    2. A segment with whitespace inside it, read as prose.
    3. Anything that is not a constant: a name assembled at run time.
    4. A key in a file that is not `.py`: YAML, JSON, CSV are never opened.
    """
    for text in ("cbb_prices.csv", "data/cbb_raw/x", "cbb-x.csv", "data/cbb raw/x", "out/the cbb files"):
        assert not names_competition_key(text, "cbb"), f"{text!r} is now flagged; move it out of this ledger"
    for source in ('KEY = "cb" + "b"\n', 'KEY = "".join(["c", "b", "b"])\n', 'KEY = "{}b".format("cb")\n'):
        module = tmp_path / "invisible.py"
        module.write_text(source, encoding="utf-8")
        assert offending_strings(module) == [], f"{source!r} is now reported; move it out of this ledger"
    not_python = tmp_path / "not_python"
    not_python.mkdir()
    (not_python / "config.yaml").write_text("root: data/cbb/raw\n", encoding="utf-8")
    (not_python / "module.py").write_text("x = 1\n", encoding="utf-8")
    assert [p.name for p in python_files(roots=(not_python,))] == ["module.py"]
