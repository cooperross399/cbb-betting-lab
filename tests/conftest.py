"""Suite-wide hooks and the shared real-data corpus.

Four things live here, and all four exist because absence used to read as a
pass.

**The guard manifest at collection.** `pytest_collection_modifyitems` runs
after collection and before any test, and it stops the run with exit code 1
if any module in `REQUIRED_GUARD_MODULES` contributed zero collected items.
That is what catches the ways a guard vanishes that no test can see from
inside the run: a rename, a `--deselect`, a `-k` that filters it out, a
`--ignore`, a `PYTEST_ADDOPTS` nobody reads, or a `git rm`. Deleting the two
hard-rule guards drops every test in two files and, without this hook, the
suite gets GREENER. `tests/test_the_guards_exist.py` is the same manifest
asserted from inside the run (tracked by git, defines at least five tests),
and `scripts/check_test_results.py` is it asserted from the junit afterwards;
the three copies are held against each other by `test_the_guards_exist`.

**What pytest actually received, not what a command line spells.** Counting
items is a floor per MODULE, and a `--deselect` of exactly ONE test in a guard
walks straight past it. Measured on a clone of 133dabd, the commit this branch
sits on: with
`addopts = "--deselect tests/test_no_secrets_committed.py::test_no_tracked_\
file_contains_an_odds_api_key_shape"` added to pyproject.toml, the suite ran
with EXACTLY ONE test deselected, this hook stayed quiet, and
`scripts/check_test_results.py` printed PASS. So the hook now also reads the
narrowing options out of the config pytest BUILT — `--deselect`, `-k`,
`--ignore`, `--ignore-glob`, the ini file's `addopts`, and `PYTEST_ADDOPTS`
from the environment — and stops the run when any is set. Reading the resolved
option is what makes a `PYTEST_ADD""OPTS` assembled from pieces, or an
`addopts` buried in a config file, visible: whatever assembled it, pytest
received it.

**Collection-phase skips.** `pytest.skip(..., allow_module_level=True)` and a
module-level `pytest.importorskip` never become items, so the count above sees
a shorter list and nothing else — that is the gitignored-table skip moved one
phase earlier. They arrive as CollectReports, `pytest_collectreport` records
them, and the run stops with exit code 1 before any test runs. Measured
2026-09-04 over a three-module synthetic tree carrying one of each shape:
`python -m pytest -q` alone reported `2 passed, 2 skipped` and exit **0**.
`tests/test_check_test_results.py::test_a_collection_phase_skip_is_not_a_pass`
is the observation, run as a subprocess over both shapes.

**The real-data corpus.** `data/processed/*.csv` and `data/raw/cbb/schedules/`
are gitignored, and every test that read them used to skip when they were
absent — 80 tests in CI, waiting on data CI can never have.
`scripts/build_test_fixtures.py` cuts a tracked sample under
`tests/fixtures/real_data/`, and the helpers below hand a test the full table
when it is on disk and the sample when it is not, saying which. Nothing
skips: both branches run every assertion, and the printed sample size says
which corpus the number is over.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REAL_DATA = REPO / "tests" / "fixtures" / "real_data"

#: The guard modules that must contribute at least one collected item to
#: every run. Kept in the same order as `scripts/check_test_results.py`'s
#: REQUIRED_MODULES and `tests/test_the_guards_exist.py`'s REQUIRED_GUARDS.
REQUIRED_GUARD_MODULES: tuple[str, ...] = (
    "tests/test_no_secrets_committed.py",
    "tests/test_no_sibling_lab_import.py",
    "tests/test_contract_strings.py",
    "tests/test_competition_registry_is_the_only_place.py",
    "tests/test_workflows.py",
    "tests/test_the_guards_exist.py",
    "tests/test_check_test_results.py",
    "tests/test_check_ledger_append_only.py",
)


def _in_scope(module: str, config) -> bool:
    """Whether this invocation would have collected `module` at all.

    With no positional argument pytest collects `testpaths`, which is the
    whole suite, so every guard is in scope. A positional that names the
    module, or a directory above it, puts it in scope too. A developer's
    `pytest tests/test_workflows.py` names one file and leaves the others OUT
    of scope — that is a person running one file, not a narrowing, and in CI
    the workflow linter refuses a positional on the required check anyway.
    What no invocation can do is collect a guard and then drop it: a `-k`, a
    `--deselect`, an `--ignore` or a `PYTEST_ADDOPTS` on a run that covers the
    module all leave it in scope with zero items, which is what fires below.
    """
    # `config.args` is what pytest resolved to collect: the positionals when
    # some were given, `testpaths` otherwise. Reading the raw invocation
    # instead mistook option VALUES (`-k "not secrets"`, `-p no:cacheprovider`)
    # for positional paths and put every guard out of scope — measured, and
    # the reason this reads the resolved list.
    positionals = [Path(str(argument).split("::", 1)[0]) for argument in config.args]
    if not positionals:
        return True
    target = (REPO / module).resolve()
    for positional in positionals:
        candidate = positional if positional.is_absolute() else Path(config.invocation_params.dir) / positional
        try:
            candidate = candidate.resolve()
        except OSError:
            continue
        if candidate == target or candidate in target.parents:
            return True
    return False


#: The options that decide WHAT RUNS, read from the config pytest built rather
#: than from the text of a command line. `deselect` and `keyword` drop tests
#: that were collected; `ignore` and `ignore_glob` stop them being collected at
#: all. A blocklist of spellings is beaten by a different spelling; a read of
#: the resolved option is not.
SELECTION_OPTIONS: tuple[str, ...] = ("deselect", "keyword", "ignore", "ignore_glob")

#: Filled by `pytest_collectreport`, read by `pytest_collection_modifyitems`.
_COLLECTION_SKIPS: list[str] = []


def selection_narrowings(config) -> list[str]:
    """Every narrowing this invocation actually carries, however it was spelled.

    Four option values as pytest resolved them, the `addopts` pytest read out
    of the ini file, and `PYTEST_ADDOPTS` from the environment. The first four
    are what pytest RECEIVED, whatever assembled them; the last two are read
    separately so the message can name the place the narrowing was written,
    which is what makes it fixable.
    """
    found: list[str] = []
    for option in SELECTION_OPTIONS:
        try:
            value = config.getoption(option)
        except (ValueError, AttributeError):  # pragma: no cover - option removed
            continue
        if value:
            found.append(f"--{option.replace('_', '-')}={value!r}")
    try:
        ini_addopts = config.getini("addopts")
    except (ValueError, KeyError):  # pragma: no cover - no such ini key
        ini_addopts = []
    if ini_addopts:
        found.append(f"addopts in the ini file = {list(ini_addopts)!r}")
    environment_addopts = os.environ.get("PYTEST_ADDOPTS", "")
    if environment_addopts:
        found.append(f"PYTEST_ADDOPTS={environment_addopts!r}")
    return found


def tracked_test_modules() -> tuple[str, ...]:
    """Every `tests/test_*.py` git tracks, or `()` when git cannot answer.

    The named manifest is the hard-rule guards; this is every test module the
    next clone will have. It closes a route the named list does not see: a
    `collect_ignore` in a conftest drops a whole module before collection, and
    for a module that is not on the manifest nothing noticed. Measured on a
    clone of 133dabd: `collect_ignore = ["test_replication.py"]` in this file
    ran TWENTY-SIX tests short of the clean collection, exit 0, and
    `scripts/check_test_results.py` printed PASS — a whole module gone under a
    green tick.

    When git cannot answer — an export rather than a checkout — this returns
    empty and the check degrades to the named manifest above, which is
    checked from the tracked list in `test_the_guards_exist` as well.
    """
    if not (REPO / ".git").exists():
        return ()
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "tests/test_*.py"],
            cwd=REPO, capture_output=True, timeout=60,
        )
    except (OSError, subprocess.SubprocessError):  # pragma: no cover - no git
        return ()
    if result.returncode != 0:  # pragma: no cover - not a repository
        return ()
    return tuple(sorted(item for item in result.stdout.decode("utf-8").split("\0") if item))


def pytest_collectreport(report) -> None:
    """Record a module that skipped itself before producing a single item.

    `pytest.skip(..., allow_module_level=True)` and a module-level
    `pytest.importorskip` never reach `pytest_collection_modifyitems` as
    items and pytest exits 0 over them. They arrive here as a CollectReport
    whose outcome is `skipped`. The run is stopped in
    `pytest_collection_modifyitems` once the whole tree has been walked, so
    the message names every one of them rather than only the first.
    """
    if report.skipped:
        _COLLECTION_SKIPS.append(f"{report.nodeid or '(unnamed module)'}: {report.longrepr}")


def _is(item, module: str) -> bool:
    """Whether a collected item came from `module`, as a repo-relative path."""
    try:
        return Path(str(item.fspath)).resolve().relative_to(REPO).as_posix() == module
    except ValueError:
        return False


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items) -> None:
    """Stop the run if a required guard in scope contributed nothing to it.

    `trylast`, because pytest's own `-k` and `--deselect` handling is itself
    a `pytest_collection_modifyitems` hook and a conftest hook runs BEFORE
    the built-in ones by default — measured: without this marker the hook
    saw every `-k`-deselected item still present and let the run through.
    Counted from the items left AFTER deselection, so a `-k`, a
    `--deselect`, an `--ignore` or a `PYTEST_ADDOPTS` that EMPTIES a module is
    visible here as a module in scope that contributed zero items.
    `pytest.exit` with `returncode=1` rather than a failing test, because a
    failing test is one more thing a `-k` can deselect.

    That count is a floor per MODULE, and deselecting one test in a guard
    leaves it intact, so this hook also reads the narrowings themselves and
    the collection-phase skips `pytest_collectreport` recorded. All three
    reasons are gathered before exiting, so a run carrying more than one is
    told about all of them.
    """
    reasons: list[str] = []

    contributed: dict[str, int] = {module: 0 for module in REQUIRED_GUARD_MODULES}
    for item in items:
        try:
            relative = Path(str(item.fspath)).resolve().relative_to(REPO).as_posix()
        except ValueError:
            continue
        if relative in contributed:
            contributed[relative] += 1
    empty = sorted(
        module for module, count in contributed.items()
        if count == 0 and _in_scope(module, config)
    )
    if empty:
        reasons.append(
            "Required guard modules contributed zero collected tests: "
            f"{empty}. A guard that collects nothing enforces nothing, and a run "
            "that drops one — by rename, -k, --deselect, --ignore, a positional "
            "path or PYTEST_ADDOPTS — is not a run of this suite."
        )

    tracked = [m for m in tracked_test_modules() if m not in contributed]
    silent = sorted(
        module for module in tracked
        if _in_scope(module, config)
        and not any(
            _is(item, module) for item in items
        )
    )
    if silent:
        reasons.append(
            f"{len(silent)} tracked test module(s) collected nothing: {silent}. "
            "A module git tracks and this run did not collect was dropped before "
            "collection — a conftest `collect_ignore`, an `--ignore`, or a "
            "module that stopped defining tests. The named manifest above only "
            "covers the hard-rule guards; this covers every module the next "
            "clone will have."
        )

    narrowings = selection_narrowings(config)
    if narrowings:
        reasons.append(
            "This invocation narrows the suite: " + "; ".join(narrowings) + ". "
            "Read from the config pytest built rather than from the spelling of "
            "a command line. A run that picks which tests to run is not a run of "
            "this suite, and deselecting one test inside a guard leaves every "
            "per-module count untouched."
        )

    if _COLLECTION_SKIPS:
        reasons.append(
            f"{len(_COLLECTION_SKIPS)} module(s) skipped at COLLECTION, before "
            "contributing a single test. pytest exits 0 over these and no "
            "per-item hook ever sees them:\n  " + "\n  ".join(_COLLECTION_SKIPS)
        )

    if reasons:
        pytest.exit("\n".join(reasons), returncode=1)


def processed_table(name: str) -> tuple[Path, str]:
    """`data/processed/<name>` when it is built, else the tracked sample.

    Returns the path and a label — `"full"` or `"sample"` — for the sample
    size a test prints beside its numbers. Never skips: the sample is tracked,
    and its absence is a broken checkout rather than a reason to pass.
    """
    from cbb_betting_lab.config import PROCESSED_DIR

    full = Path(PROCESSED_DIR) / name
    if full.is_file():
        return full, "full"
    sample = REAL_DATA / name
    assert sample.is_file(), (
        f"{sample} is missing. It is a tracked fixture cut by "
        "scripts/build_test_fixtures.py; a checkout without it is broken, and a "
        "test that cannot find its corpus fails rather than skips."
    )
    return sample, "sample"


def schedule_fixture(season: int) -> Path:
    """The tracked, column-trimmed hoopR schedule for one season.

    Every row of the season, so a test over "every cached game" is over every
    game whether or not the full parquet is cached. Used everywhere a
    schedule is read, locally too: the same corpus in both places is what
    makes the printed numbers comparable between a laptop and CI.
    """
    path = REAL_DATA / f"mbb_schedule_{season}.parquet"
    assert path.is_file(), f"{path} is missing; run scripts/build_test_fixtures.py"
    return path


@pytest.fixture(scope="session")
def fixture_raw_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A `data/raw`-shaped tree holding the tracked schedules, for code that
    takes a `raw_dir` and globs `cbb/schedules/mbb_schedule_*.parquet`."""
    root = tmp_path_factory.mktemp("raw")
    target = root / "cbb" / "schedules"
    target.mkdir(parents=True)
    seasons = sorted(int(p.stem.rsplit("_", 1)[-1]) for p in REAL_DATA.glob("mbb_schedule_*.parquet"))
    assert seasons, f"no schedule fixture under {REAL_DATA}"
    for season in seasons:
        shutil.copy(schedule_fixture(season), target / f"mbb_schedule_{season}.parquet")
    return root


@pytest.fixture(scope="session")
def fixture_processed_dir() -> Path:
    """The directory holding the processed tables a test should read: the
    real one when built, else the tracked sample."""
    path, _ = processed_table("cbb_team_games.csv")
    return path.parent
