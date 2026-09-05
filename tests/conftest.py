"""Suite-wide hooks and the shared real-data corpus.

Two things live here, and both exist because absence used to read as a pass.

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


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(session, config, items) -> None:
    """Stop the run if a required guard in scope contributed nothing to it.

    `trylast`, because pytest's own `-k` and `--deselect` handling is itself
    a `pytest_collection_modifyitems` hook and a conftest hook runs BEFORE
    the built-in ones by default — measured: without this marker the hook
    saw every `-k`-deselected item still present and let the run through.
    Counted from the items left AFTER deselection, so a `-k`, a
    `--deselect`, an `--ignore` and a `PYTEST_ADDOPTS` are all visible here
    as a module that was in scope and contributed zero items. `pytest.exit`
    with `returncode=1` rather than a failing test, because a failing test
    is one more thing a `-k` can deselect.
    """
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
        pytest.exit(
            "Required guard modules contributed zero collected tests: "
            f"{empty}. A guard that collects nothing enforces nothing, and a run "
            "that drops one — by rename, -k, --deselect, --ignore, a positional "
            "path or PYTEST_ADDOPTS — is not a run of this suite.",
            returncode=1,
        )


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
