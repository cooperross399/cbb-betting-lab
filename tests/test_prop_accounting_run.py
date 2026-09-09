"""The accounting run: the second receipt design section 10's gate demands.

`models.player_census.guard_graded_frame` asks for two receipts.
`assert_reconciles` fills the first — the store counted twice under two folds
of one column and reconciled against the frozen artifact. The second is filled
only by `assert_every_offered_prop_is_accounted`, and until this commit
**nothing in this repository called it**: `tests/test_player_census_reconciles.
py`'s clause 5 held that open, in those words, on the ground that "Grading
belongs in its own commit, gated on this one."

`scripts/run_prop_accounting.py` is the caller. This file is what pins it.

**Nothing here is graded and nothing here states a result.** No probability is
compared against a price, no return is computed, no interval is built and no
verdict is printed. Every number below is a count of rows or of wagers.

## What each test is for

The identity itself — every prop the store offers lands in exactly one bucket,
two independently derived sides, residual exactly 0 — is already driven at the
call site by `tests/test_player_seam.py::test_s12_every_prop_the_store_offers_
lands_in_exactly_one_bucket`, over a real board through the shipped
`gameday_card.opinions_for`. This file does **not** repeat that. It pins the
four things the SCRIPT adds and the call site cannot:

1. the receipt is filed through the real function, so a later
   `guard_graded_frame` sees it;
2. the run reads the store itself, fingerprints what it read, and is refused
   when the census counted different bytes;
3. the run is walk-forward, and a run that priced only part of the store is
   refused rather than reported as an accounting of it;
4. the script assigns no bucket of its own — every filing is made by
   `opinions_for`, the one function in the tree that decides — and it reaches
   nothing in `price_backtest` that scores.

The receipt is process-global. Every test here drops both halves before and
after it runs: a receipt that leaked out of this file would make the gate look
shut in a file that never ran it, which is the failure this whole gate exists
against.
"""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from conftest import REAL_DATA, census_expected_record  # noqa: E402

from cbb_betting_lab.competitions import CBB  # noqa: E402
from cbb_betting_lab.models import player_census as PC  # noqa: E402
from cbb_betting_lab.models import player_rates as PR  # noqa: E402

SCRIPT_PATH = REPO / "scripts" / "run_prop_accounting.py"


def _script():
    """`scripts/run_prop_accounting.py` as an importable module.

    Loaded by path because `scripts/` is not a package. The module is what the
    shell runs, byte for byte, so a test that drives `main()` drives the script
    rather than a re-implementation of it.
    """
    spec = importlib.util.spec_from_file_location("run_prop_accounting", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_prop_accounting"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# The model this file prices with, and why it is a stub
# --------------------------------------------------------------------------


def no_player_half(*, day, history, prices, competition, raw_dir):
    """A model with a team half and no player half. Returns a bare mapping.

    **Deliberately not the real seam.** What this file measures is the
    ACCOUNTING — that every wager the store offers is filed exactly once and
    that the two sides agree — and the accounting has to hold whatever the
    model says. A stub that answers nothing puts every priceable prop in
    `never_asked` and every refused-by-name prop in `refused_by_name`, which is
    the decline path through `_player_decline` with no dependence on a roster,
    a schedule or a fitted constant. The priced path over a real board is
    `tests/test_player_seam.py`'s subject and is not restated here.

    `{}` and not a `SlateModel`: it is what `ratings.matchups_for` and every
    test double return, and `opinions_for` coerces it. A stub that returned the
    richer object would be testing a shape no shipped model produces.
    """
    return {}


# --------------------------------------------------------------------------
# A store small enough to count by hand
# --------------------------------------------------------------------------

#: Every column the census reads plus every column the run reads. Assembled
#: from the two declarations rather than typed, so a column added to either
#: side appears here without anyone remembering to.
STORE_COLUMNS: tuple[str, ...] = tuple(
    dict.fromkeys(
        (
            *PC.STORE_COLUMNS_THE_CENSUS_READS,
            "commence_time",
            "home_team",
            "away_team",
            "home_name",
            "away_name",
            "tier",
        )
    )
)


def quote(**overrides) -> dict:
    """One row of the price store. Two books on one selection is one wager."""
    row = {
        "event_id": "E1",
        "market": "player_points",
        "segment": "game",
        "player": "Al Jones",
        "selection": "over",
        "line": "10.5",
        "snapshot_phase": "card",
        "book": "draftkings",
        "season": "2026",
        "slate_date": "2026-01-02",
        "game_id": "901",
        "american_odds": "-110",
        "commence_time": "2026-01-03T00:30Z",
        "home_team": "11",
        "away_team": "22",
        "home_name": "Home School",
        "away_name": "Away School",
        "tier": "high_major",
    }
    row.update(overrides)
    return row


def a_board() -> list[dict]:
    """Six quotes: five wagers, two days, three tiers, one refused market.

    Small enough that every count below can be checked by reading it:

        E1 2026-01-02 high_major player_points  Al Jones over 10.5   x2 books
        E1 2026-01-02 high_major player_points  Al Jones under 10.5
        E2 2026-01-02 low_major  player_rebounds Bo Smith over 6.5
        E3 2026-01-09 mid_major  player_points  Cy Ray   over 14.5
        E3 2026-01-09 mid_major  <refused>      Cy Ray   over 0.5

    Two books on the first selection is one wager, which is the collapse
    `stores.best_price_per_wager` makes and the census counts.
    """
    refused = sorted(PR.MARKETS_REFUSED_BY_NAME)[0]
    return [
        quote(),
        quote(book="fanduel", american_odds="-105"),
        quote(selection="under", american_odds="-110"),
        quote(
            event_id="E2", game_id="902", market="player_rebounds",
            player="Bo Smith", line="6.5", tier="low_major",
            home_team="33", away_team="44",
            home_name="Third School", away_name="Fourth School",
        ),
        quote(
            event_id="E3", game_id="903", slate_date="2026-01-09",
            commence_time="2026-01-10T00:30Z", player="Cy Ray", line="14.5",
            tier="mid_major", home_team="55", away_team="66",
            home_name="Fifth School", away_name="Sixth School",
        ),
        quote(
            event_id="E3", game_id="903", slate_date="2026-01-09",
            commence_time="2026-01-10T00:30Z", market=refused,
            player="Cy Ray", line="0.5", tier="mid_major",
            home_team="55", away_team="66",
            home_name="Fifth School", away_name="Sixth School",
        ),
    ]


def a_processed_dir(root: Path, rows) -> Path:
    """A `data/processed`-shaped directory: the store, the tables, the artifact.

    The team and player tables are the tracked sample corpus, copied rather
    than symlinked so nothing in the test can write through to it. The frozen
    census artifact is built FROM the census of the store written here — what
    this file needs is a reconciled receipt, and every way the two sides can
    disagree is `tests/test_player_census_reconciles.py`'s subject.
    """
    processed = root / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    store = processed / CBB.output_name("historical_prices__card", ".csv")
    pd.DataFrame(list(rows), columns=list(STORE_COLUMNS)).to_csv(store, index=False)
    for stem in ("team_games", "player_games"):
        name = CBB.output_name(stem, ".csv")
        shutil.copy(REAL_DATA / name, processed / name)
    taken = PC.census(store, roster=processed / CBB.output_name("player_games", ".csv"))
    (processed / CBB.output_name("player_census", ".json")).write_text(
        json.dumps(census_expected_record(taken), indent=1), encoding="utf-8"
    )
    return processed


def run_script(module, processed: Path, root: Path, *extra: str) -> int:
    return module.main(
        [
            "--processed-dir", str(processed),
            "--output-dir", str(root / "outputs"),
            "--raw-dir", str(root / "raw"),
            "--model", f"{__name__}:no_player_half",
            *extra,
        ]
    )


@pytest.fixture(autouse=True)
def _no_receipt_leaves_this_file():
    """Both receipts dropped either side of every test in this file.

    Both, and never only one: `guard_graded_frame` asks for two and a test that
    dropped the census half would leave the accounting half standing, so a file
    that never ran the gate would find half of it already open.
    """
    PC.forget_reconciliations()
    yield
    PC.forget_reconciliations()


# --------------------------------------------------------------------------
# 1. The receipt is filed, through the real function
# --------------------------------------------------------------------------


def test_the_run_files_the_receipt_the_gate_demands(tmp_path, capsys):
    """Exit 0, residual exactly 0, and `accounted()` no longer empty.

    The identity is `offered = refused by name + no opinion + priced +
    unreadable`, and the two sides are two passes over one file: the store's
    own count taken by `player_census.census` with `usecols=` and `chunksize=`,
    and the run's own count filed one wager at a time by
    `gameday_card.opinions_for` as it decides. Neither is a remainder of the
    other and no term below is subtracted from another.

    Mutation: delete the `assert_every_offered_prop_is_accounted` call from
    `main` — RED, because `accounted()` stays empty and a later
    `guard_graded_frame` would still refuse.
    """
    module = _script()
    processed = a_processed_dir(tmp_path, a_board())
    assert PC.accounted() == (), "a receipt survived into this test"

    assert run_script(module, processed, tmp_path) == module.EXIT_OK

    # The receipt exists, and it is the one the grading gate reads.
    assert len(PC.accounted()) == 1
    accounted = PC.accounted()[0]
    assert accounted.residual == 0
    assert accounted.offered == accounted.accounted == 5, (
        "six quotes are five wagers: two books on one selection is one bet"
    )

    # And the guard that gates grading is now satisfied on both halves, which
    # is the whole purpose of the run. Asserted on the guard rather than on the
    # receipt, because the guard is what a grading entry point actually asks.
    frame = pd.DataFrame({"market": ["player_points"], "tier": ["high_major"]})
    assert PC.guard_graded_frame(frame, what="a test") == ("player_points",)

    record = json.loads(
        (tmp_path / "outputs" / CBB.output_name("prop_accounting", ".json"))
        .read_text(encoding="utf-8")
    )
    assert record["residual"] == 0
    assert record["offered"] == record["accounted"] == 5
    assert sum(record["buckets"].values()) == record["offered"], (
        "the buckets do not sum to the offered count, so one of them is a "
        "relabelling of another rather than a count of wagers"
    )
    # Four priceable wagers with no player half is four `never_asked`; the
    # refused market is asked FIRST, before anything about the athlete, and is
    # the fifth.
    assert record["buckets"][PC.BUCKET_NEVER_ASKED] == 4
    assert record["buckets"][PC.BUCKET_REFUSED_BY_NAME] == 1
    assert record["buckets"][PC.BUCKET_PRICED] == 0
    assert record["no_opinion"] == 4

    # Per tier, and never as one Division I number: the three tiers are carried
    # apart, and a wager whose event has no tier is `(untiered)` rather than
    # assigned to one.
    assert set(record["by_tier"]) == {"high_major", "mid_major", "low_major"}
    assert record["by_tier"]["high_major"] == {PC.BUCKET_NEVER_ASKED: 2}
    assert record["by_tier"]["low_major"] == {PC.BUCKET_NEVER_ASKED: 1}
    assert record["by_tier"]["mid_major"] == {
        PC.BUCKET_NEVER_ASKED: 1,
        PC.BUCKET_REFUSED_BY_NAME: 1,
    }

    printed = capsys.readouterr().out
    assert "residual 0" in printed
    assert "no opinion" in printed


#: What a grading number is MADE of, copied from
#: `tests/test_player_census_reconciles.py::GRADING_TOKENS` rather than
#: narrowed: a document that names one of these is stating a result, and this
#: run measures none.
GRADING_TOKENS = re.compile(
    r"\b(interval_two_way|interval_by_cluster|RoiInterval|row_verdict"
    r"|reachability_verdict|log_loss|logloss|brier|de_?vig|fair_price"
    r"|scorable|settled_opinions|roi_interval)\b|\.verdict\s*\(",
    re.IGNORECASE,
)


def test_the_report_states_counts_and_never_a_result(tmp_path):
    """The rendered document carries a count per bucket and no measurement.

    A census that printed a return or an interval beside its counts would be a
    grading wearing a census's name, and design section 10 gates grading on
    this run rather than the other way round.
    """
    module = _script()
    processed = a_processed_dir(tmp_path, a_board())
    assert run_script(module, processed, tmp_path) == module.EXIT_OK

    report = (
        tmp_path / "outputs" / CBB.output_name("prop_accounting", ".md")
    ).read_text(encoding="utf-8")
    assert "census and not a grading" in report
    assert "| priced | 0 |" in report
    assert "Per tier" in report
    assert GRADING_TOKENS.search(report) is None, (
        "the accounting report names something a grader is made of. It counts "
        "wagers, and a result on the same page is a result nobody measured."
    )
    assert GRADING_TOKENS.search(SCRIPT_PATH.read_text(encoding="utf-8")) is None, (
        "the accounting run names something a grader is made of. If it has "
        "started grading it belongs on the pinned list in "
        "`tests/test_player_census_reconciles.py` and must carry the guard."
    )
    # Every number in the tables is a count of wagers. A rate anywhere in them
    # would be a result this run did not measure. The prose outside the tables
    # is not held to this — the refusal sentences below the tables are the
    # model's own words and are reprinted, never rewritten.
    tables = [line for line in report.splitlines() if line.startswith("|")]
    assert tables, "the report rendered no table at all"
    assert not [line for line in tables if "%" in line], (
        "a table in the accounting report carries a percentage. Every number "
        "in one is a count of wagers, and a rate is a result this run did not "
        "measure."
    )

    # The reasons are grouped and bounded, and the bound never hides the count.
    # A bucket's own total and how many sentences were NOT kept are both
    # written, so a truncated list cannot be mistaken for the whole of it.
    record = json.loads(
        (tmp_path / "outputs" / CBB.output_name("prop_accounting", ".json"))
        .read_text(encoding="utf-8")
    )
    for bucket, held in record["reasons"].items():
        assert len(held["commonest"]) <= module.REASONS_KEPT
        assert held["wagers"] == record["buckets"][bucket]
        assert held["distinct_sentences"] >= len(held["commonest"])
        assert sum(held["commonest"].values()) <= held["wagers"]


# --------------------------------------------------------------------------
# 2. The run reads the store itself and fingerprints what it read
# --------------------------------------------------------------------------


def test_the_run_fingerprints_the_bytes_it_read(tmp_path):
    """`store_digest` is the run's own statement about which file it priced.

    `data/processed/` is a tree of symlinks into a shared store. A run that
    took its digest from the census would be handing the check to the thing it
    is meant to check, so the digest is computed here, over the bytes this
    script opened, and `assert_every_offered_prop_is_accounted` looks the
    census up by it.
    """
    module = _script()
    processed = a_processed_dir(tmp_path, a_board())
    store = processed / CBB.output_name("historical_prices__card", ".csv")

    digest, size = module.store_digest(store)
    assert digest == hashlib.sha256(store.read_bytes()).hexdigest()
    assert size == store.stat().st_size

    assert run_script(module, processed, tmp_path) == module.EXIT_OK
    record = json.loads(
        (tmp_path / "outputs" / CBB.output_name("prop_accounting", ".json"))
        .read_text(encoding="utf-8")
    )
    assert record["store"]["sha256"] == digest
    assert record["store"]["bytes"] == size


def test_a_store_that_moved_under_the_frozen_artifact_is_refused(tmp_path):
    """The census counted one file; the run opened another. Nothing is filed.

    Written as the thing that actually happens — a store rewritten while the
    artifact beside it still describes the old one — rather than as a forged
    digest, because that is the shape a symlinked tree produces.
    """
    module = _script()
    processed = a_processed_dir(tmp_path, a_board())
    store = processed / CBB.output_name("historical_prices__card", ".csv")
    pd.DataFrame(
        a_board() + [quote(event_id="E4", game_id="904", player="Di Fox")],
        columns=list(STORE_COLUMNS),
    ).to_csv(store, index=False)

    assert run_script(module, processed, tmp_path) == module.EXIT_DOES_NOT_RECONCILE
    assert PC.accounted() == (), "a receipt was filed against a store that moved"
    assert PC.reconciled() == ()


# --------------------------------------------------------------------------
# 3. A run that priced part of the store accounts for part of the store
# --------------------------------------------------------------------------


def test_a_partial_run_is_refused_and_not_reported_as_an_accounting(tmp_path, capsys):
    """`--days 1` prices one of two slate days, so the residual is not 0.

    The flag exists to exercise the wiring and it can never pass: the store's
    side of the identity is the whole store, and a run that saw half of it has
    accounted for half of it. That is the gate failing CLOSED on exactly the
    thing it is for — a wager the store offered that the run never disposed of
    — and a partial run must never write a record that reads like an
    accounting of the store.
    """
    module = _script()
    processed = a_processed_dir(tmp_path, a_board())

    assert (
        run_script(module, processed, tmp_path, "--days", "1")
        == module.EXIT_DOES_NOT_RECONCILE
    )
    assert PC.accounted() == ()
    assert not (tmp_path / "outputs").exists(), (
        "a refused run wrote a record. A record on disk outlives the exit code "
        "that refused it, and the next reader takes the number."
    )
    printed = capsys.readouterr()
    assert "This is NOT an accounting of the store." in printed.out
    assert "residual must be EXACTLY 0" in printed.err


# --------------------------------------------------------------------------
# 4. The script decides nothing, and reaches nothing that scores
# --------------------------------------------------------------------------


def _script_tree() -> ast.AST:
    return ast.parse(SCRIPT_PATH.read_text(encoding="utf-8"))


def test_the_script_assigns_no_bucket_of_its_own():
    """Every filing is made by `opinions_for`, which is the decider.

    `reports.gameday_card.opinions_for` is the only function in the tree that
    decides what becomes of a prop, so it is the only one that can say which
    bucket the wager landed in. A bucket assigned out in the script would be a
    second opinion about a decision the card already made, and an identity
    whose two sides are two opinions of one thing is not an identity.

    Mutation: add a `run.file(...)` to `make_price_day` — RED.
    """
    tree = _script_tree()
    called = {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "file" not in called, (
        "the accounting run files a disposition itself. The bucket is the "
        "card's decision and must be filed where it is made."
    )
    assert "opinions_for" in called, (
        "the run no longer drives the function that decides, so whatever it is "
        "counting is not what a card would do with these wagers."
    )
    assert "assert_every_offered_prop_is_accounted" in called
    assert "assert_reconciles" in called, (
        "the run must take the census receipt first: 'the store I priced was "
        "never counted' and 'the store I priced does not reconcile' are "
        "different faults and only one is fixed by running the census."
    )


def test_the_run_reaches_nothing_in_the_backtest_that_scores():
    """Pinned by name, because `price_backtest` is a module that grades.

    The script imports it for the walk-forward harness — the day cut, the
    stamp, the model resolution — and for nothing else. `settled_opinions`,
    `bets_from`, `null_baseline`, `by_market_and_tier` and everything like them
    turn wagers into numbers, and a census that reached one of them would be
    stating a result while calling itself a count.

    A new name here is not a failure to fix by adding it: it is a question
    about whether this run has started grading.
    """
    tree = _script_tree()
    used = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "PB"
    }
    allowed = {
        "walk_forward",
        "assert_walk_forward",
        "call_model",
        "resolve_model",
        "latest_day",
        "ModelNotWired",
    }
    assert used <= allowed, (
        f"the accounting run reaches {sorted(used - allowed)} in "
        "`reports/price_backtest.py`. Say whether this run has started "
        "grading; it may not."
    )


def test_the_run_is_walk_forward_and_says_so_on_the_row():
    """The stamp is checked, not the code path.

    `walk_forward` cuts both tables to rows strictly earlier than each slate
    day and stamps what the pricer was allowed to see; `assert_walk_forward`
    reads that stamp back off every row. The buckets are an output of the
    model, and a model that had seen the night it was pricing refuses
    differently from one that had not — so a census taken with the season in
    hand would be a census of a model this lab will never run.

    Mutation: drop the `PB.assert_walk_forward(priced)` call — RED.
    """
    tree = _script_tree()
    main = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    rendered = ast.dump(main)
    assert "assert_walk_forward" in rendered
    assert "walk_forward" in rendered
    price_day = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "price_day"
    )
    declared = [argument.arg for argument in price_day.args.kwonlyargs]
    assert declared == ["day", "history", "prices", "player_history"], (
        f"the pricer declares {declared}. Every frame it reads has to be named "
        "here, because a frame it reached any other way is uncut and unstamped."
    )
    assert not price_day.args.kw_defaults or not any(price_day.args.kw_defaults), (
        "a frame parameter carries a default. `player_history=None` is not a "
        "pricer that works without player games; it is a pricer left to find "
        "them some other way, and every other way is uncut."
    )
