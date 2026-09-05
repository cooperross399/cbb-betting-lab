"""Suite-wide hooks and the shared real-data corpus.

Three things live here, and all three exist because absence used to read as a
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

**What pytest actually received, not what the command line spells.** Counting
the items a module contributed is a floor per MODULE, and a `--deselect` of
exactly one test in a guard leaves that floor intact: measured on
2026-09-04, `addopts = "--deselect tests/test_no_secrets_committed.py::
test_no_tracked_file_contains_an_odds_api_key_shape"` in pyproject.toml ran
as **1235 passed, 1 deselected** out of 1236 collected, the hook below stayed
quiet, and `scripts/check_test_results.py` printed PASS. So the hook now also
reads the SELECTION options out of `config` — `--deselect`, `-k`,
`--ignore`, `--ignore-glob`, the `addopts` pytest resolved from the ini file,
and `PYTEST_ADDOPTS` in the environment — and stops the run when any of them
is set. Reading the option values is what makes a `PYTEST_ADD""OPTS` spelled
from pieces, or an `addopts` buried in a config file, visible: whatever
assembled it, pytest received it.

**Collection-phase skips.** A `pytest.skip(..., allow_module_level=True)` or
a module-level `pytest.importorskip` never produces a test item, so
`pytest_collection_modifyitems` sees a shorter list and nothing else — that
is defect 7 (a permanent skip on a gitignored table) with the skip moved one
phase earlier. `pytest_collectreport` is where those arrive, and it records
them; the run then stops with exit code 1 before any test runs. Measured
2026-09-04 over a three-module synthetic tree: `python -m pytest -q` alone
reported `2 passed, 2 skipped` and exit **0**. `tests/test_check_test_results
.py::test_a_module_level_skip_is_not_a_pass_in_the_run_or_in_the_junit` is
the observation, run as a subprocess over both shapes.

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
#: all. A blocklist of spellings is defeated by a different spelling; a read of
#: the resolved option is not.
SELECTION_OPTIONS: tuple[str, ...] = ("deselect", "keyword", "ignore", "ignore_glob")


def _selection_narrowings(config) -> list[str]:
    """Every narrowing this invocation actually carries, however it was spelled.

    Four option values, the `addopts` pytest resolved out of the ini file, and
    `PYTEST_ADDOPTS` from the environment. The first four are what pytest
    received; the last two are read because they are the two places a
    narrowing can be set without appearing on any command line, and naming
    them in the message is what makes the failure fixable.
    """
    found: list[str] = []
    for option in SELECTION_OPTIONS:
        try:
            value = config.getoption(option)
        except (ValueError, AttributeError):  # pragma: no cover - option gone
            continue
        if value:
            found.append(f"--{option.replace('_', '-')}={value!r}")
    inifile_addopts = ""
    try:
        inifile_addopts = config.inicfg.get("addopts", "") or ""
    except AttributeError:  # pragma: no cover - no ini in this invocation
        inifile_addopts = ""
    if inifile_addopts:
        found.append(f"addopts in the ini file = {inifile_addopts!r}")
    environment_addopts = os.environ.get("PYTEST_ADDOPTS", "")
    if environment_addopts:
        found.append(f"PYTEST_ADDOPTS={environment_addopts!r}")
    return found


def pytest_collectreport(report) -> None:
    """Record a module that skipped itself before it produced a single item.

    `pytest.skip(..., allow_module_level=True)` and a module-level
    `pytest.importorskip` never reach `pytest_collection_modifyitems` as
    items, and pytest exits 0 over them. They arrive here, as a CollectReport
    whose outcome is `skipped`, and the run is stopped in
    `pytest_collection_modifyitems` once the whole tree has been walked, so
    the message names every one of them rather than only the first.
    """
    if report.skipped:
        _COLLECTION_SKIPS.append(f"{report.nodeid or '(unnamed module)'}: {report.longrepr}")


#: Filled by `pytest_collectreport`, drained by `pytest_collection_modifyitems`.
_COLLECTION_SKIPS: list[str] = []


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items) -> None:
    """Stop the run if a required guard in scope contributed nothing to it.

    `trylast`, because pytest's own `-k` and `--deselect` handling is itself
    a `pytest_collection_modifyitems` hook and a conftest hook runs BEFORE
    the built-in ones by default — measured: without this marker the hook
    saw every `-k`-deselected item still present and let the run through.
    Counted from the items left AFTER deselection, so a `-k`, a
    `--deselect`, an `--ignore` and a `PYTEST_ADDOPTS` that empty a module
    are all visible here as a module that was in scope and contributed zero
    items. `pytest.exit` with `returncode=1` rather than a failing test,
    because a failing test is one more thing a `-k` can deselect.

    The count is a floor per MODULE, which a `--deselect` of one test in a
    guard walks straight past, so this hook also reads the narrowing options
    themselves and the collection-phase skips recorded above. All three
    reasons are gathered before exiting, so a run that carries more than one
    is told about all of them.
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

    narrowings = _selection_narrowings(config)
    if narrowings:
        reasons.append(
            "This invocation narrows the suite: " + "; ".join(narrowings) + ". "
            "Read from the config pytest built, not from the spelling of a "
            "command line. A run that chooses which tests to run is not a run "
            "of this suite, and deselecting one test in a guard leaves every "
            "per-module count intact."
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
