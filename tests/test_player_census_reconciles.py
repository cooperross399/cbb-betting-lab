"""The wager census gate: what it counts, what it refuses, and what it may not skip.

Design section 10: *"Gate before grading: reconcile 261,870 wagers (measured, by
event/market/player/selection/line) against the brief's 257,474. A 1.7%
unexplained denominator is a wrong-denominator error of the same family. The run
stops until it reconciles."*

**Nothing in this file grades anything and nothing here states a result.** It
de-vigs nothing, scores no log loss, builds no interval and prints no verdict.
Every number below is a count of rows in a table, and each says how it was
counted. The one probability in the file is the `model_probability` column of
:data:`TEAM_WAGER`, a fixture value that exists because
`price_backtest.require_columns` refuses a frame missing it, and every entry
point it is handed either refuses before reading it or is asserted about
without being run.

**The declared grading surface was wrong until 2026-09-06 and this file is
where it was wrong.** `player_census.GRADING_ENTRY_POINTS` named two functions
and `test_..._are_the_whole_of_the_grading_surface` claimed to prove no third
existed. There were five. `forward_evidence.render_ledger`,
`forward_evidence.report_payload` and `reachability.build_record` each build a
clustered `stats.RoiInterval` over settled wagers and print a family-corrected
Verdict per market, none of them was declared, none called the guard, and the
scan could not see them because it matched one spelling of one verb list. The
replacement scan looks for what a grader DOES, the pinned list says which kind
each module is, and the completeness claim is gone: a lexical scan is a floor,
and `test_a_lexical_scan_cannot_be_exhaustive_and_this_is_the_module_it_misses`
holds that gap open with a module that grades and is not seen.

The numbers over the real store, measured 2026-09-06 with `usecols=` and
`chunksize=500_000` and never on the whole 977,613,435-byte file:

    3,863,325 rows scanned, 504,394 of them player quotes
    261,870 wagers under the book's own spelling of the athlete (1,357 names)
    257,474 wagers under strip().casefold()             (1,293 names)
      4,396 collapses = 1.679% of 261,870 -- design section 10's "1.7%"
      4,396 attributed to 64 collision groups, residual EXACTLY 0
          0 of them same-book; 3,959 of them carry two different american_odds
    261,147 / 256,751 once the two markets refused BY NAME are removed

Most of this file runs on fixtures small enough to read: nine rows, two books,
one deliberate collision. Two tests run against the real store when it is on
disk, and assert the frozen artifact's own arithmetic when it is not, so nothing
skips and both branches carry assertions.
"""

from __future__ import annotations

import ast
import importlib
import json
import re
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from conftest import census_expected_record  # noqa: E402  (tests/ is on sys.path under pytest)

from cbb_betting_lab import stores  # noqa: E402
from cbb_betting_lab.models import player_census as PC  # noqa: E402
from cbb_betting_lab.models import player_rates  # noqa: E402

MODULE_PATH = REPO / "src" / "cbb_betting_lab" / "models" / "player_census.py"
ARTIFACT_PATH = REPO / "data" / "processed" / "cbb_player_census.json"

STORE_COLUMNS = (
    "event_id",
    "market",
    "segment",
    "player",
    "selection",
    "line",
    "snapshot_phase",
    "book",
    "season",
    "slate_date",
    "game_id",
    "american_odds",
)


# --------------------------------------------------------------------------
# Fixtures small enough to count by hand
# --------------------------------------------------------------------------


def quote(**overrides) -> dict:
    """One row of the price store. Defaults chosen so a test overrides one field."""
    row = {
        "event_id": "E1",
        "market": "player_points",
        "segment": "game",
        "player": "Al Jones",
        "selection": "over",
        "line": "10.5",
        "snapshot_phase": "card",
        "book": "draftkings",
        "season": "2024",
        "slate_date": "2024-01-02",
        "game_id": "G1",
        "american_odds": "-110",
    }
    row.update(overrides)
    return row


def write_store(path: Path, rows) -> Path:
    pd.DataFrame(list(rows), columns=list(STORE_COLUMNS)).to_csv(path, index=False)
    return path


def write_roster(path: Path, rows) -> Path:
    """`cbb_player_games.csv`'s three columns the census reads, and no others."""
    pd.DataFrame(
        list(rows), columns=["game_id", "athlete_id", "athlete_display_name"]
    ).to_csv(path, index=False)
    return path


def write_expected(path: Path, taken: PC.Census, **overrides) -> Path:
    """A frozen artifact matching a census, so a test can move exactly one number.

    Built from the census rather than typed out, because what these tests
    exercise is the COMPARISON: every one of them moves one side and watches
    `reconcile` raise.

    The shape comes from `conftest.census_expected_record`, which is the one
    copy of it in this repository. `conftest.reconcile_a_fixture_census` needs
    the same shape to hand a report test a receipt, and two spellings of an
    artifact whose missing section reads as a reconciled clause is exactly the
    drift `reconcile`'s "counted as checked and never compared" complaint
    exists to catch.
    """
    record = census_expected_record(taken)
    for key, value in overrides.items():
        section, _, field = key.partition(".")
        if field:
            record[section][field] = value
        else:
            record[section] = value
    path.write_text(json.dumps(record, indent=1), encoding="utf-8")
    return path


def take(tmp_path: Path, rows, roster_rows=(("G1", "1", "Al Jones"),)):
    """Census a fixture store, with a roster unless a test asks for none."""
    store = write_store(tmp_path / "prices.csv", rows)
    roster = write_roster(tmp_path / "roster.csv", roster_rows)
    return PC.census(store, roster=roster), store, roster


@pytest.fixture(autouse=True)
def _no_receipt_leaks_between_tests():
    """The guard's receipt is process-global; a leak would make it look shut."""
    PC.forget_reconciliations()
    yield
    PC.forget_reconciliations()


# --------------------------------------------------------------------------
# The key
# --------------------------------------------------------------------------


def test_the_wager_key_is_derived_from_price_identity_and_never_retyped():
    """One wager is the lab's quote identity minus the book — read, not restated.

    A literal here drifts from `stores.best_price_per_wager`, which is the code
    that actually collapses quotes, and that drift is the whole finding this gate
    exists to surface: the shipped collapse keys on these seven columns and
    `stores._dedupe_value` strips but does not casefold, so on 4,396 wagers it
    returns two rows for one athlete-line-side.

    Mutation: `WAGER_KEY = ("event_id", "market", "segment", "player",
    "selection", "line", "snapshot_phase")` typed as a literal — RED here.
    """
    assert PC.WAGER_KEY == tuple(c for c in stores.PRICE_IDENTITY if c != "book")
    assert "book" not in PC.WAGER_KEY
    assert PC.SUBJECT_COLUMN in PC.WAGER_KEY

    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    literals = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Tuple)
        and len(node.elts) >= 5
        and all(isinstance(e, ast.Constant) and isinstance(e.value, str) for e in node.elts)
    ]
    spelled = [tuple(e.value for e in node.elts) for node in literals]
    assert not any(set(PC.WAGER_KEY) <= set(s) for s in spelled), (
        "A tuple literal in player_census.py spells the wager key. It must be "
        f"derived from stores.PRICE_IDENTITY, which is {stores.PRICE_IDENTITY}; "
        f"the literals found were {spelled}."
    )


# --------------------------------------------------------------------------
# How it reads the store
# --------------------------------------------------------------------------


def test_the_store_is_read_in_chunks_and_never_whole(tmp_path, monkeypatch):
    """978 MB, 3,863,325 rows. A whole-file read is minutes and gigabytes.

    The guard is not a habit a later edit can forget: every call is intercepted
    and must carry both `usecols` and `chunksize`.

    Mutation: drop `chunksize=chunksize` from `_player_chunks` — RED (and the
    census then also returns a `TypeError`, which is the point: the code cannot
    be written the slow way and still work).
    """
    calls: list[dict] = []
    real = pd.read_csv

    def spy(*args, **kwargs):
        calls.append(dict(kwargs))
        return real(*args, **kwargs)

    monkeypatch.setattr(PC.pd, "read_csv", spy)
    take(tmp_path, [quote()])

    assert calls, "the census read nothing"
    for kwargs in calls:
        assert kwargs.get("chunksize"), (
            f"a read of the price store carried no chunksize: {kwargs}. The "
            "store is 977,613,435 bytes."
        )
        assert kwargs.get("usecols"), (
            f"a read of the price store carried no usecols: {kwargs}. It has 23 "
            "columns and this census reads twelve of them."
        )


def test_a_quote_is_not_a_wager_and_the_count_carries_both(tmp_path):
    """Two books on one selection is one bet. `stores.py` rule 2, counted here.

    Measured on the real store: 504,394 quotes are 261,870 wagers, i.e. 1.93
    books per wager on average. This fixture is the same arithmetic at n=2.

    Mutation: `raw_keys[market].add(row)` -> `raw_keys[market] = ...` counting
    rows — RED, because wagers_raw would equal quotes.
    """
    taken, _, _ = take(
        tmp_path,
        [quote(book="draftkings", american_odds="-110"), quote(book="fanduel", american_odds="-105")],
    )
    points = taken.market("player_points")
    assert points.quotes == 2
    assert points.wagers_raw == 1, (
        "two books quoting one athlete at one line on one event is one wager. "
        f"This census made it {points.wagers_raw}."
    )
    assert taken.player_quotes == 2
    assert taken.total_raw == 1


def test_the_two_markets_refused_by_name_are_counted_and_never_priced(tmp_path):
    """A refusal that is counted is evidence it held; a dropped one is invisible.

    On the real store these are `player_first_basket` 1,823 quotes / 721 wagers
    and `player_double_double` 2 quotes / 2 wagers — design section 6's figures,
    reproduced exactly. Both headline numbers, 261,870 and 257,474, INCLUDE
    those 723, and neither is therefore a grading denominator.

    Mutation: `priced=market not in refused` -> `priced=True` — RED here and in
    `reconcile`, which cross-checks every `priced` flag against
    `player_rates.MARKETS_REFUSED_BY_NAME`.
    """
    rows = [
        quote(),
        quote(market="player_first_basket", line="0.5"),
        quote(market="player_double_double", line="0.5"),
    ]
    taken, _, _ = take(tmp_path, rows)
    for name in player_rates.MARKETS_REFUSED_BY_NAME:
        count = taken.market(name)
        assert count is not None, f"{name} was not counted at all"
        assert count.priced is False
    assert taken.refused_raw == 2
    assert taken.priced_raw == 1
    assert taken.total_raw == taken.priced_raw + taken.refused_raw

    expected = write_expected(tmp_path / "e.json", taken)
    PC.reconcile(taken, PC.load_expected(expected))

    priced_refusal = PC.Census(
        **{
            **taken.__dict__,
            "by_market": tuple(
                PC.MarketCount(m.market, m.quotes, m.wagers_raw, m.wagers_folded, True)
                for m in taken.by_market
            ),
        }
    )
    with pytest.raises(PC.WagerCountMismatch, match="refused by name"):
        PC.reconcile(priced_refusal, PC.load_expected(expected))


# --------------------------------------------------------------------------
# The attribution — the clause that matters
# --------------------------------------------------------------------------


def test_the_gap_is_named_wager_by_wager_and_the_residual_must_be_zero(tmp_path):
    """The gate is not "the two numbers are equal". They are not, and both are right.

    On the real store 261,870 and 257,474 are correct counts of the same rows
    under two spellings of the subject, so an equality gate could never open.
    What is gated is that every wager of the difference is NAMED: 4,396 counted,
    4,396 attributed to 64 collision groups, residual exactly 0.

    Mutation: `if len(per_spelling) < 2: continue` -> `continue` unconditionally
    in `_collisions` (nothing attributed) — RED with residual 1.
    """
    rows = [
        quote(player="AJ Storr", book="draftkings"),
        quote(player="Aj Storr", book="bovada", american_odds="-120"),
    ]
    taken, _, _ = take(tmp_path, rows, roster_rows=(("G1", "1", "AJ Storr"),))

    assert taken.total_raw == 2 and taken.total_folded == 1
    assert taken.difference == 1
    assert taken.attributed == 1
    assert taken.residual == 0
    (collision,) = taken.collisions
    assert collision.folded == "aj storr"
    assert collision.spellings == ("AJ Storr", "Aj Storr")
    assert collision.wagers_collapsed == 1
    assert collision.same_book is False
    assert collision.odds_disagreements == 1, (
        "the two spellings carry two different american_odds, which is the "
        "shape that makes best_price_per_wager return two rows for one bet. "
        "Measured on the real store: 3,959 of 4,396."
    )

    expected = write_expected(tmp_path / "e.json", taken)
    PC.reconcile(taken, PC.load_expected(expected))

    unattributed = PC.Census(**{**taken.__dict__, "collisions": ()})
    with pytest.raises(PC.WagerCountMismatch, match="not fully attributed"):
        PC.reconcile(unattributed, PC.load_expected(expected))


def test_a_same_book_collision_is_a_duplicated_quote_and_is_never_folded_away(tmp_path):
    """One book, one wager key, two spellings. That is `dedupe_prices`'s defect.

    Measured on the real store: 0 of the 4,396 collapsing keys carry a book that
    quoted both spellings, so every one is cross-book. The day one does, folding
    it silently would hide a duplicated quote — ROI unchanged, interval narrowed
    by root two, and nothing about the output looking wrong.

    Mutation: `if set.intersection(*booksets): same_book.add(folded)` deleted —
    RED.
    """
    rows = [
        quote(player="AJ Storr", book="bovada"),
        quote(player="Aj Storr", book="bovada", american_odds="-120"),
    ]
    taken, _, _ = take(tmp_path, rows, roster_rows=(("G1", "1", "AJ Storr"),))
    (collision,) = taken.collisions
    assert collision.same_book is True
    expected = write_expected(tmp_path / "e.json", taken)
    with pytest.raises(PC.WagerCountMismatch, match="one book quoting two"):
        PC.reconcile(taken, PC.load_expected(expected))


def test_a_fold_that_merges_two_athletes_inside_one_game_refuses(tmp_path):
    """Normalising a spelling is not the same act as destroying a subject.

    Measured on the real store: 0 of the 64 collision groups merge two
    `athlete_id`s. Separately, exactly one of 9,098 quoted (game, folded-name)
    pairs is ambiguous before any fold — 'Justin Moore', game 401604303,
    Villanova against Drexel — and section 7's R1 refuses more than one
    candidate rather than picking.

    Mutation: `if len(roster_ids.get(...)) > 1: ambiguous.add(folded)` deleted —
    RED.
    """
    rows = [
        quote(player="AJ Storr", book="draftkings"),
        quote(player="Aj Storr", book="bovada", american_odds="-120"),
    ]
    taken, _, _ = take(
        tmp_path,
        rows,
        roster_rows=(("G1", "111", "AJ Storr"), ("G1", "222", "Aj Storr")),
    )
    (collision,) = taken.collisions
    assert collision.roster_ambiguous is True
    assert taken.ambiguous_subjects == (("G1", "aj storr", ("111", "222")),)
    expected = write_expected(tmp_path / "e.json", taken)
    with pytest.raises(PC.WagerCountMismatch, match="fold two athlete_ids"):
        PC.reconcile(taken, PC.load_expected(expected))


def test_a_census_that_skipped_the_roster_cannot_pass(tmp_path):
    """Two of the seven clauses read a roster. A gate that skipped them is not one.

    `census` takes `roster` as a keyword with no default, so the caller has to
    decide, and `None` is recorded rather than assumed. This is the demotion
    gate's failure — a corrupt ledger read as "no allowlisted market has fallen
    through its floor" — refused in advance.

    Mutation: `roster_checked=True` hardcoded in `census` — RED.
    """
    store = write_store(tmp_path / "p.csv", [quote()])
    taken = PC.census(store, roster=None)
    assert taken.roster_checked is False
    expected = write_expected(tmp_path / "e.json", taken)
    with pytest.raises(PC.WagerCountMismatch, match="without a roster"):
        PC.reconcile(taken, PC.load_expected(expected))


# --------------------------------------------------------------------------
# What stops a run
# --------------------------------------------------------------------------


def test_a_mismatch_stops_the_run_and_the_message_carries_both_numbers(tmp_path):
    """It raises. It never warns, never returns a bool, never picks a side.

    A bool is droppable: `if not gate(): ...` is one keystroke from `gate()` on
    its own line. The only two outcomes are an `Attribution` and an exception.

    Mutation: `raise WagerCountMismatch(...)` -> `return None` at the end of
    `reconcile` — RED.
    """
    taken, _, _ = take(tmp_path, [quote(), quote(book="fanduel")])
    good = write_expected(tmp_path / "good.json", taken)
    attribution = PC.reconcile(taken, PC.load_expected(good))
    assert isinstance(attribution, PC.Attribution)
    assert not isinstance(attribution, bool)

    moved = write_expected(
        tmp_path / "moved.json", taken, **{"wagers_raw.player_points": 99}
    )
    with pytest.raises(PC.WagerCountMismatch) as raised:
        PC.reconcile(taken, PC.load_expected(moved))
    message = str(raised.value)
    assert "1 wagers under `raw`, expected 99" in message
    assert "-98" in message, "the difference itself must be in the message"
    assert "The run stops until it reconciles" in message
    assert "player_points" in message


def test_each_subject_count_is_compared_and_a_moved_one_stops_the_run(tmp_path):
    """All four `subjects[...]` clauses, moved one at a time, must refuse.

    The clause counted itself as compared and could not fail. `carried` and
    `note` put all four into `Attribution.compared_checks`, and
    `test_the_gate_reconciles_the_store_it_is_pinned_to` asserts the total
    including "four subject counts" -- but the only mismatch any test moved was
    `wagers_raw.player_points`, so the four `complaints.append` at
    `player_census.py`'s `subjects[...]` block ran in no test at all.

    Measured on the module as it stood: `if False and want is not None and
    value != want:` on that comparison left this file, `test_gameday_card.py`
    and `test_player_seam.py` fully green -- 114 tests -- including the run
    against the real store. So the gate could ship comparing the four athlete
    cluster counts against nothing while still reporting 46 comparisons, and
    certify a store whose clusters had moved. They are the denominator every
    athlete-clustered interval is widened to, which is why the clause's own
    message says "a change here moves every athlete-clustered interval".

    Held here one clause at a time rather than all four at once: a single moved
    number that raised would leave the other three as vacuous as they were.
    """
    taken, _, _ = take(tmp_path, [quote(), quote(book="fanduel")])
    truth = {
        "raw": taken.subjects_raw,
        "folded": taken.subjects_folded,
        "player_points_raw": taken.points_subjects_raw,
        "player_points_folded": taken.points_subjects_folded,
    }
    # The artifact as written reconciles, so every raise below is the moved
    # number and not the fixture.
    PC.reconcile(taken, PC.load_expected(write_expected(tmp_path / "ok.json", taken)))

    for clause, value in truth.items():
        moved = write_expected(
            tmp_path / f"moved_{clause}.json",
            taken,
            **{f"subjects.{clause}": int(value) + 7},
        )
        with pytest.raises(PC.WagerCountMismatch) as raised:
            PC.reconcile(taken, PC.load_expected(moved))
        message = str(raised.value)
        assert f"subjects[{clause}]: {value:,}, expected {int(value) + 7:,}" in message, (
            f"the {clause} mismatch did not name the clause and both numbers: "
            f"{message}"
        )
        assert "athlete-clustered interval" in message, (
            "the message no longer says what a moved cluster count moves"
        )
        # And only this clause complained: a mismatch that dragged the other
        # three in with it would let any one of them stay uncompared.
        others = [
            other for other in truth if other != clause and f"subjects[{other}]:" in message
        ]
        assert not others, (
            f"moving subjects[{clause}] also complained about {others}, so a "
            "single vacuous clause would be hidden behind its neighbours"
        )


def test_a_clause_whose_expectation_is_absent_is_refused_not_counted_as_checked(
    tmp_path,
):
    """A comparison that did not run must not be reported as a comparison.

    Every value clause in `reconcile` is guarded by `if want is not None`, and
    until this commit an expectation the artifact did not carry was silently not
    compared while `note()` still appended the clause to `Attribution.checked`
    and counted it into `declared_checks` or `pinned_checks`. Those two counts
    are what `test_the_gate_reconciles_the_store_it_is_pinned_to` asserts as
    "53 clauses ran", and both come off the `sources` block rather than off the
    value sections — so a record with every value deleted reproduced them in
    full.

    Re-measured here against the module with the repair removed, and reproduced
    below as the last case: an expectations record written from this fixture's
    census and then emptied to `quotes: {}`, `totals: {}`, `subjects: {}`,
    `invariants: {}` reconciled that same census and RETURNED NORMALLY, with
    `len(checked) == 30`, `pinned_checks == 30`, `declared_checks == 0` and
    `"quotes[player_points]" in checked` True -- while exactly ONE of the thirty
    clauses had compared anything, because `wagers_raw` is a fifth section the
    probe leaves alone. Thirty was the clause count on the day that was
    measured; the declared-subject clause has since made it thirty-one, which
    is what the assertions below read. The realistic version is not
    the emptied record: it is a regenerated `data/processed/
    cbb_player_census.json` that drops one `quotes[...]`, `totals.priced_raw` or
    `subjects.folded` while keeping its `sources` row, which left both that test
    and `test_the_frozen_artifact_says_where_every_number_came_from` — which
    counts `sources` keys — green while the gate certified a store it had not
    compared on those clauses.

    Held now: an absent expectation is a complaint naming the clause, and
    `Attribution.compared_checks` says how many comparisons actually ran beside
    the `len(checked)` that says how many were attempted. On this fixture the
    two are 24 and 31 — one market gives two clauses, plus six totals, twelve
    invariants and four subject counts, and the seven that need no expectation
    (the digest, the declared subject normalizer, the residual, the two
    collision clauses, the roster and the null key fields) are attempted and
    compared against nothing by design.
    """
    taken, _, _ = take(tmp_path, [quote(), quote(book="fanduel", american_odds="-105")])
    good = write_expected(tmp_path / "good.json", taken)
    attribution = PC.reconcile(taken, PC.load_expected(good))
    assert attribution.compared_checks == 24, (
        f"{attribution.compared_checks} value comparisons ran on a "
        "single-market fixture; two per market, six totals, twelve invariants "
        "and four subject counts is 24"
    )
    assert len(attribution.checked) == 31
    assert (
        attribution.declared_checks + attribution.pinned_checks
        == len(attribution.checked)
    ), "the source split must partition the clauses attempted, not a subset"
    assert attribution.pinned_checks == 31 and attribution.declared_checks == 0, (
        "this fixture's artifact carries an empty `sources` block, so all 31 "
        "clauses are PINNED -- which is the pair of numbers the probe in the "
        "docstring reproduced with every value section emptied"
    )
    assert "quotes[player_points]" in attribution.checked

    def without(name: str, *keys: str):
        """The same artifact with one expectation DELETED, not moved."""
        record = json.loads(good.read_text(encoding="utf-8"))
        section = record
        for key in keys[:-1]:
            section = section[key]
        del section[keys[-1]]
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(record, indent=1), encoding="utf-8")
        return PC.load_expected(path)

    for name, keys, clause in (
        ("no_quotes", ("quotes", "player_points"), "quotes[player_points]"),
        ("no_total", ("totals", "priced_raw"), "priced_raw"),
        ("no_subject", ("subjects", "folded"), "subjects[folded]"),
        ("no_invariant", ("invariants", "player_quotes"), "player_quotes"),
    ):
        with pytest.raises(PC.WagerCountMismatch) as raised:
            PC.reconcile(taken, without(name, *keys))
        message = str(raised.value)
        assert clause in message, message
        assert "counted as checked and never compared" in message
        assert "The run stops until it reconciles" in message

    # And the emptied record, which is the probe that found this, run against
    # the census it WAS written from so that nothing else can be the reason it
    # stops. The digest matches, the one per-market wager count matches, and
    # every other clause has nothing to compare against.
    record = json.loads(good.read_text(encoding="utf-8"))
    for section in ("quotes", "totals", "subjects", "invariants"):
        record[section] = {}
    emptied = tmp_path / "emptied.json"
    emptied.write_text(json.dumps(record, indent=1), encoding="utf-8")

    with pytest.raises(PC.WagerCountMismatch) as raised:
        PC.reconcile(taken, PC.load_expected(emptied))
    message = str(raised.value)
    # 23 and not 24: `wagers_raw` is a fifth section and the probe left it
    # alone, so exactly one comparison -- the per-market wager count -- ran.
    assert "23 clause(s) were counted as checked and never compared" in message, message
    assert "only 1 of the value comparisons ran" in message
    assert "quotes[player_points]" in message
    assert "The price store is not the one this census" not in message, (
        "the digest matched, so this refusal has exactly one cause and it is "
        "the one this test is about"
    )


def test_a_market_that_appeared_or_vanished_stops_the_run(tmp_path):
    """The market SETS are compared, not only the counts inside them.

    A market that appeared is a market nobody registered a hypothesis for; a
    market that vanished is a denominator that moved without anyone saying so.
    Neither shows up in a total: a market with zero wagers changes no sum, so
    the totals clause is blind to exactly the case this one is for.

    **It was executed by no test until this one.** Every fixture in this file
    builds its expectations artifact FROM the census it will be compared
    against, so the two market sets agree by construction and nothing
    constructed the disagreement. Measured before this test was written:
    `if False and (absent or surplus):` left the whole file GREEN at 20 passed,
    with the real 978 MB store on disk.

    Both directions are driven, and the vanished half is driven on its own so
    that the "counted as checked and never compared" complaint it also raises
    cannot be the thing that makes the assertion pass.

    Mutation: `if False and (absent or surplus):` — RED on the first case here.
    """
    taken, _, _ = take(tmp_path, [quote()])
    assert [m.market for m in taken.by_market] == ["player_points"]

    # DECLARED AND ABSENT. The artifact says the store carries a market it does
    # not. Every other clause passes, so this refusal has exactly one cause.
    declared = write_expected(
        tmp_path / "appeared.json",
        taken,
        **{"wagers_raw": {"player_points": 1, "player_assists": 0}},
    )
    with pytest.raises(PC.WagerCountMismatch) as raised:
        PC.reconcile(taken, PC.load_expected(declared))
    message = str(raised.value)
    assert "The store's markets are not the census's" in message, message
    assert "player_assists" in message
    assert "a denominator that moved without anyone saying so" in message
    assert "counted as checked and never compared" not in message, (
        "this refusal has a second cause, so it does not hold the clause it "
        "is about"
    )

    # PRESENT AND UNDECLARED, the other direction: the store carries a market
    # the artifact never registered.
    surplus = write_expected(
        tmp_path / "vanished.json", taken, **{"wagers_raw": {}}
    )
    with pytest.raises(PC.WagerCountMismatch) as raised:
        PC.reconcile(taken, PC.load_expected(surplus))
    assert "Present and undeclared: ['player_points']" in str(raised.value)


def test_the_store_is_pinned_by_its_digest(tmp_path):
    """The store is a symlink into a shared tree and nothing else pins it.

    Measured 2026-09-06: `data/processed/cbb_historical_prices__card.csv` is a
    symlink whose own mtime is newer than its target's, sha256
    143d7d307d9bc3b21989d7857aac6a52f8abd010da2c1e0ea2df8c0f0b82b78b over
    977,613,435 bytes. Unpinned, this gate would certify whichever file the link
    pointed at.

    Mutation: drop the `taken.source_sha256 != expected.source_sha256` clause —
    RED.
    """
    taken, store, roster = take(tmp_path, [quote()])
    expected = write_expected(tmp_path / "e.json", taken)
    PC.reconcile(taken, PC.load_expected(expected))

    write_store(store, [quote(), quote(book="fanduel", line="9.5")])
    again = PC.census(store, roster=roster)
    assert again.source_sha256 != taken.source_sha256
    with pytest.raises(PC.WagerCountMismatch, match="not the one this census"):
        PC.reconcile(again, PC.load_expected(expected))


def test_the_invariants_refuse_a_second_season_or_a_second_snapshot_window(tmp_path):
    """Every player row is season 2024, segment game, snapshot phase card.

    Measured: 504,394 of 504,394 on all three. A second window in one
    measurement takes the better of a card-time price and a closing price for
    one wager, which is `stores.assert_single_window`'s reason; a second season
    is a denominator that grew without anyone saying so.

    Mutation: drop `seasons`/`segments`/`snapshot_phases` from the invariant
    loop in `reconcile` — RED.
    """
    taken, _, _ = take(tmp_path, [quote()])
    expected = write_expected(tmp_path / "e.json", taken)
    PC.reconcile(taken, PC.load_expected(expected))

    for column, value, label in (
        ("season", "2025", "seasons"),
        ("snapshot_phase", "closing", "snapshot_phases"),
        ("segment", "1h", "segments"),
    ):
        store = write_store(
            tmp_path / f"{label}.csv", [quote(), quote(**{column: value}, book="fanduel")]
        )
        moved = PC.census(store, roster=tmp_path / "roster.csv")
        with pytest.raises(PC.WagerCountMismatch, match=label):
            PC.reconcile(
                moved,
                PC.load_expected(
                    write_expected(
                        tmp_path / f"{label}.json",
                        moved,
                        **{f"invariants.{label}": list(getattr(taken, label))},
                    )
                ),
            )


def test_a_null_in_the_wager_key_stops_the_run(tmp_path):
    """A null in the key makes two different wagers compare equal.

    Measured on the real store: 0 nulls in any of the seven key columns. The
    count that would come back with one is smaller for a reason nobody wrote
    down, which is the same shape as the collapse this gate names.

    Mutation: drop the `null_key_fields` clause from `reconcile` — RED.
    """
    taken, _, _ = take(tmp_path, [quote(), quote(line="", book="fanduel")])
    assert taken.null_key_fields["line"] == 1
    with pytest.raises(PC.WagerCountMismatch, match="carries nulls"):
        PC.reconcile(taken, PC.load_expected(write_expected(tmp_path / "e.json", taken)))


def test_the_expectations_are_not_editable_from_the_call_site():
    """No expected count is written in the module that does the comparing.

    Otherwise a run is made to pass by editing the comparer, which is the
    edit-to-green this lab has written down repeatedly. Every count comes out of
    `data/processed/cbb_player_census.json` through `load_expected`, and
    `load_expected` RAISES when the artifact is missing rather than defaulting
    to an empty record that would pass every store.

    Mutation: add `_LEAKED_TOTAL = 261870` anywhere in player_census.py — RED.
    """
    expected = PC.load_expected(ARTIFACT_PATH)
    frozen = (
        set(expected.quotes.values())
        | set(expected.wagers_raw.values())
        | set(expected.totals.values())
        | set(expected.subjects.values())
        | {
            value
            for value in expected.invariants.values()
            if isinstance(value, int) and not isinstance(value, bool)
        }
    )
    # A floor, declared with its reason: an expected count below 100 is
    # indistinguishable from an ordinary index or a small constant. Five are --
    # `events_with_two_game_ids` 0, `ambiguous_subjects` 1, `player_double_
    # double` 2 quotes and 2 wagers, `books` 10 and `collision_groups` 64 -- and
    # they are covered instead by `test_a_mismatch_stops_the_run...`, which
    # moves a count in the artifact and watches `reconcile` raise: proof that
    # the comparison reads the file rather than the module. Every count at or
    # above the floor is distinctive enough that its appearance here is a leak.
    DISTINCTIVE = 100
    below = sorted(v for v in frozen if v < DISTINCTIVE)
    assert below == [0, 1, 2, 10, 64], (
        "the set of expectations too small to check this way moved: "
        f"{below}. Re-read the floor's reason before changing it."
    )
    frozen = {value for value in frozen if value >= DISTINCTIVE}
    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    literals = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, int)
        and not isinstance(node.value, bool)
    }
    leaked = sorted(literals & frozen)
    assert not leaked, (
        f"player_census.py carries the integer literal(s) {leaked}, which are "
        "expected counts. An expectation typed into the module that compares "
        "against it is one edit from green."
    )

    with pytest.raises(PC.WagerCountMismatch, match="carries every expected count"):
        PC.load_expected(Path("/nonexistent/cbb_player_census.json"))


def test_the_frozen_artifact_says_where_every_number_came_from():
    """23 counts are the design's own; 29 are pins measured here.

    A pin is not evidence of anything today — it was measured and then compared
    with itself — and can only ever refuse later. The refusal message says which
    each one is, so nobody reads a pin as a reproduction.

    Mutation: `expected.source_of` -> `return "design section 6"` always — RED,
    because the declared/pinned split then reads 52/0.
    """
    taken_like = PC.load_expected(ARTIFACT_PATH)
    assert taken_like.schema_version == 1
    assert taken_like.declared_subject is None, (
        "the lab has declared no subject normalizer; the denominator is "
        "261,870 / 257,474 / 257,378 / 255,553 / 251,949 over five reasonable "
        "folds and picking one is a declaration for the design to make"
    )
    designed = [k for k, v in taken_like.sources.items() if v.startswith("design")]
    pinned = [k for k, v in taken_like.sources.items() if not v.startswith("design")]
    assert len(designed) == 23, sorted(designed)
    assert len(pinned) == 29, sorted(pinned)
    for market, count in taken_like.wagers_raw.items():
        assert taken_like.sources[f"wagers_raw[{market}]"].startswith("design section 6")
        assert count > 0
    assert taken_like.totals["total_raw"] == 261870
    assert taken_like.totals["total_folded"] == 257474
    assert taken_like.sources["total_raw"].startswith("design section 10")


# --------------------------------------------------------------------------
# The gate on the run, not on the merge
# --------------------------------------------------------------------------


#: One settled team wager with every column `reachability.build_record` and
#: `price_backtest` require, so the "a team frame is waved through" half of the
#: gate test is driven through the real entry points and not around them.
TEAM_WAGER = {
    "event_id": "e1",
    "slate_date": "2026-01-02",
    "market": "spreads",
    "segment": "game",
    "selection": "home",
    "line": "-3.5",
    "american_odds": "-110",
    "tier": "high_major",
    "model_probability": 0.55,
    "outcome": "won",
    "profit_units": 1.0,
}


def test_no_player_wager_can_be_graded_until_this_gate_has_run(tmp_path):
    """All six grading entry points refuse a player frame with no receipt.

    `forecast_skill.build_record` is design section 10's own metric — it de-vigs,
    scores log loss and Brier and builds the clustered intervals — and it
    already carries `player` as an optional column, casefolded in the de-vig
    pair scope. A frame of player props handed to it needs NO new code to be
    graded. `price_backtest.settled_opinions` is the ROI half.

    The other three were added 2026-09-06 and are the repair to a completeness
    claim that was wrong. `forward_evidence.render_ledger` and
    `forward_evidence.report_payload` print ROI, a 95% interval, a
    family-corrected interval and a Verdict per market and per tier over every
    settled row — `_bet_rows` excludes player props from the BETS table and
    from that table only — and `reachability.build_record` splits the same
    forward ledger by market and turns each cell into an interval and a verdict
    sentence. None of the three was declared, none called a guard, and the scan
    that claimed to see "the whole of the grading surface" matched none of
    them.

    Every one of the five is driven HERE, at its own call site, because a test
    that asserts a helper works passes with the call deleted.

    The sixth arrived 2026-09-07 with the grading commit:
    `reports.prop_grading.build_record` is design section 10's scoring — two
    de-vigs, log loss, Brier, calibration by decile, three-way clustered
    intervals and a verdict per market and per tier — over a population that is
    nothing BUT player props.

    Mutation: delete the `player_census.guard_graded_frame(...)` line from
    `forecast_skill.build_record` — RED. Same for `settled_opinions`,
    `render_ledger`, `report_payload`, `reachability.build_record` and
    `prop_grading.build_record` — RED, one at a time.

    **Two receipts, and the second one is the gate with two independently
    derived numbers.** The census is the store counted twice under two folds of
    one column -- 261,870 and 257,474 are one file, not two stores, and since
    `stores.normalise_subject` declared the fold they are not even two live
    spellings of a question. So each door is driven three times here: with no
    receipt at all, with the census reconciled and nothing accounted, and with
    both. The middle state is the one that used to open every door.

    Mutation: delete `if not _ACCOUNTED:` from `guard_graded_frame` — RED on the
    middle loop below, six times over.
    """
    from cbb_betting_lab import forward_evidence as FE
    from cbb_betting_lab import reachability as RE
    from cbb_betting_lab.reports import forecast_skill as FS
    from cbb_betting_lab.reports import price_backtest as PB
    from cbb_betting_lab.reports import prop_grading as PG

    team = pd.DataFrame([TEAM_WAGER])
    props = pd.DataFrame([dict(TEAM_WAGER, market="player_points")])

    assert PC.reconciled() == ()
    # A team frame passes with no receipt at all: the guard costs one prefix
    # test and refuses nothing this lab has ever measured. (Whether the row
    # survives `settled` is a different question and not this gate's.)
    assert PC.player_markets_in(team) == ()
    assert isinstance(PB.settled_opinions(team), pd.DataFrame)
    assert isinstance(FS.build_record(FS.SkillInputs(graded=team.iloc[0:0])), dict)
    # The other three are NOT driven over a team frame here, deliberately:
    # `render_ledger`, `report_payload` and `reachability.build_record` all go
    # on to build an interval and print a verdict once the guard lets them
    # through, and this file computes neither. That half is already proved
    # where those reports are tested: counted by walking the AST 2026-09-06,
    # 16 tests in `tests/test_forward_evidence.py` call `render_ledger`,
    # `report_payload` or `write_report` and 14 in
    # `tests/test_reachability.py` call `build_record`, all 30 over team
    # ledgers with `reconciled() == ()`, and all 30 pass. That is the guard
    # costing nothing on a team run. Two further tests in the first file take
    # a receipt, because their ledgers hold a prop.

    refusals = {
        "price_backtest.settled_opinions": lambda: PB.settled_opinions(props),
        "forecast_skill.build_record": lambda: FS.build_record(
            FS.SkillInputs(graded=props)
        ),
        "forward_evidence.render_ledger": lambda: FE.render_ledger(props),
        "forward_evidence.report_payload": lambda: FE.report_payload(props),
        "reachability.build_record": lambda: RE.build_record(props, None),
        # Added 2026-09-07 with the grading commit. It is the door design
        # section 10 was written for, and it is the only one of the six whose
        # every row is a player wager: the guard is not a cheap prefix test
        # that finds nothing here, it either lets the whole run through or
        # stops it.
        "prop_grading.build_record": lambda: PG.build_record(
            PG.PropGradingInputs(graded=props)
        ),
    }
    assert set(refusals) == {
        dotted.split(".", 2)[-1] if dotted.startswith("cbb_betting_lab.reports.")
        else dotted[len("cbb_betting_lab."):]
        for dotted in PC.GRADING_ENTRY_POINTS
    }, (
        "a declared entry point is not driven here. Every name in "
        "GRADING_ENTRY_POINTS has to be called at its own call site, or the "
        "gate is asserted about and not run."
    )
    for name, call in refusals.items():
        with pytest.raises(
            PC.WagerCountMismatch, match="no wager census has reconciled"
        ) as raised:
            call()
        assert name in str(raised.value), (
            f"{name} refused, but named {str(raised.value)[:80]!r} as the caller "
            "— the `what=` label is what tells an operator which door shut."
        )

    # The census on its own is NOT enough, and this is the half of the gate
    # design section 10's own wording could not carry. Reconciling 261,870
    # against 257,474 is one file counted twice under two folds of one column,
    # so with the census run and nothing else every one of the five doors
    # would have opened on a run that had accounted for nothing.
    store = write_store(tmp_path / "p.csv", [quote()])
    roster = write_roster(tmp_path / "r.csv", (("G1", "1", "Al Jones"),))
    taken = PC.census(store, roster=roster)
    PC.assert_reconciles(
        store=store, roster=roster, expected=write_expected(tmp_path / "e.json", taken)
    )
    assert len(PC.reconciled()) == 1
    assert PC.accounted() == ()
    for name, call in refusals.items():
        with pytest.raises(
            PC.WagerCountMismatch, match="no run has accounted for the props"
        ) as raised:
            call()
        assert "residual of EXACTLY 0" in str(raised.value), (
            f"{name} refused for the second receipt without saying what the "
            "identity is. The operator has to be told what to produce."
        )

    # And with BOTH halves run, the same call is allowed through. The store
    # offers one wager -- two books on one athlete at one line is one bet --
    # and the run files one, priced.
    run = PC.RunDisposition(
        what="a test", store_sha256=taken.source_sha256
    )
    run.file(("E1", "player_points", "over", "10.5"), market="player_points",
             bucket=PC.BUCKET_PRICED)
    accounted = PC.assert_every_offered_prop_is_accounted(run)
    assert accounted.offered == 1 and accounted.accounted == 1
    assert accounted.residual == 0
    assert len(PC.accounted()) == 1
    assert PC.guard_graded_frame(props, what="a test") == ("player_points",)


def test_the_guard_is_the_first_thing_each_entry_point_does(tmp_path):
    """Before it reads a probability, not after it has scored one.

    Read off the source: the first statement of each declared entry point, after
    its docstring, is the call to `guard_graded_frame`.

    Mutation: move the guard below `priced, devig_census = devig(...)` in
    `forecast_skill.build_record` — RED.
    """
    for dotted in PC.GRADING_ENTRY_POINTS:
        module_name, _, function_name = dotted.rpartition(".")
        module = importlib.import_module(module_name)
        assert hasattr(module, function_name), (
            f"{dotted} is declared as a grading entry point and does not exist. "
            "Either it was renamed, in which case this list is stale, or the "
            "gate is now watching a door nobody uses."
        )
        source = Path(module.__file__).read_text(encoding="utf-8")
        tree = ast.parse(source)
        target = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == function_name
        )
        body = [
            statement
            for statement in target.body
            if not (
                isinstance(statement, ast.Expr)
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            )
        ]
        first = body[0]
        rendered = ast.dump(first)
        assert "guard_graded_frame" in rendered, (
            f"{dotted}'s first statement is not the census guard. It is "
            f"{ast.unparse(first)[:120]!r}. A gate that runs after the de-vig "
            "is a gate on the report, not on the run."
        )


#: What a grading number is MADE of, rather than one spelling of one verb.
#: A grader either builds a clustered interval (`stats.interval_two_way`,
#: `stats.interval_by_cluster`, a `RoiInterval` constructed or read back),
#: scores a probability (`log_loss`, `brier`, a de-vig, a fair price), or turns
#: one into a sentence (`row_verdict`, `reachability_verdict`, `.verdict()`).
#:
#: The first version of this list was the verb half alone --
#: `log_loss|logloss|brier|de_?vig|fair_price|scorable|settled_opinions|roi_interval`
#: -- and it matched NINE modules while `forward_evidence.py` and
#: `reachability.py` both built clustered `stats.RoiInterval`s over settled
#: wagers and printed a family-corrected Verdict per market. Measured over
#: `git show 1fd4843:<file>`, the source as it stood before this commit: the
#: old pattern matched NEITHER file, because both spell the type
#: `stats.RoiInterval` in camel case and neither de-vigs or scores a log loss.
#: A scan for a spelling finds the modules that share a vocabulary, not the
#: modules that grade.
GRADING_TOKENS = re.compile(
    r"\b(interval_two_way|interval_by_cluster|RoiInterval|row_verdict"
    r"|reachability_verdict|log_loss|logloss|brier|de_?vig|fair_price"
    r"|scorable|settled_opinions|roi_interval)\b|\.verdict\s*\(",
    re.IGNORECASE,
)


def _modules_naming_a_grading_token() -> list[str]:
    """Every `.py` under `src/` and `scripts/` that names one. Repo-relative."""
    return sorted(
        path.relative_to(REPO).as_posix()
        for base in ("src", "scripts")
        for path in (REPO / base).rglob("*.py")
        if GRADING_TOKENS.search(path.read_text(encoding="utf-8"))
    )


#: Grades a frame of wagers, and therefore carries `guard_graded_frame`. These
#: four hold the five names in `player_census.GRADING_ENTRY_POINTS`.
GRADES_A_WAGER_FRAME_AND_IS_GUARDED = {
    "src/cbb_betting_lab/forward_evidence.py":
        "the Opinions table: ROI, a 95% interval, a family-corrected interval "
        "and a Verdict per market and per tier, over every settled row "
        "including player props; guarded in render_ledger and report_payload",
    "src/cbb_betting_lab/reachability.py":
        "the same forward ledger split by market, tier and price survival, "
        "each cell an interval and each tier a verdict sentence; guarded in "
        "build_record",
    "src/cbb_betting_lab/reports/forecast_skill.py":
        "design section 10's metric; guarded in build_record",
    "src/cbb_betting_lab/reports/price_backtest.py":
        "the ROI half; guarded in settled_opinions",
    "src/cbb_betting_lab/reports/prop_grading.py":
        "design section 10's scoring of the player-prop model -- two de-vigs, "
        "log loss, Brier, calibration by decile, three-way clustered intervals "
        "and a verdict per market and per tier; guarded in build_record",
}

#: Builds an interval over something that is not a wager, so no player wager
#: can reach a number through it and the guard would refuse nothing.
BUILDS_AN_INTERVAL_OVER_SOMETHING_THAT_IS_NOT_A_WAGER = {
    "src/cbb_betting_lab/stats.py":
        "the arithmetic itself. It is handed a frame and a profit column and "
        "has no idea what a market is; gating here would gate the ratings fit",
    "scripts/fit_ratings.py":
        "mean_interval and mean_by_cluster over margin_error, total_error and "
        "points per 100 -- model error on scored GAMES, no market, no stake, "
        "no profit_units of its own",
}

#: Reads a record somebody else already graded, or calls one of the four above.
READS_A_BUILT_RECORD_OR_CALLS_ONE_THAT_GRADES = {
    "src/cbb_betting_lab/models/player_census.py": "this gate, naming the verbs",
    "src/cbb_betting_lab/reports/card_pricing.py":
        "one docstring line about how a night clusters; grades nothing",
    "src/cbb_betting_lab/reports/replication.py":
        "rebuilds a RoiInterval from a stored backtest row to restate it",
    "src/cbb_betting_lab/reports/retention_probe.py":
        "its own RetentionVerdict enum, which is a credit-cost word and not an "
        "interval",
    "src/cbb_betting_lab/reports/what_we_can_claim.py": "reads the written records",
    "src/cbb_betting_lab/reports/why_the_model.py": "reads cbb_forecast_skill.json",
    "src/cbb_betting_lab/restatement.py": "the vocabulary of derived words",
    "scripts/build_skill_frame.py": "builds the frame; grades nothing",
    "scripts/run_forecast_skill.py": "calls forecast_skill.build_record",
    "scripts/run_price_backtest.py": "calls price_backtest.settled_opinions",
    "scripts/run_prop_grading.py":
        "the wiring for the module above: it prices, files its dispositions "
        "and settles, and every number it prints comes back from "
        "prop_grading.build_record",
    "scripts/run_weekly_loop.py":
        "calls forward_evidence's own helpers for the demotion check, over "
        "`measurable_bets` -- which is `fe._bet_rows`, and that excludes every "
        "player prop before an interval is built",
}


def test_no_module_outside_this_pinned_list_builds_an_interval_or_scores_one():
    """Every module naming a grading token, pinned with what kind it is.

    Nineteen modules, measured 2026-09-07 by :data:`GRADING_TOKENS` over
    `src/` and `scripts/`. FIVE grade a frame of wagers and carry the guard;
    two build an interval over something that is not a wager; twelve read a
    record somebody else graded or call one of the five. The day a twentieth
    appears this goes red and its author has to say which of the three it is.

    The fifth grader and the twelfth reader arrived together on 2026-09-07:
    `reports/prop_grading.py` is design section 10's metric and
    `scripts/run_prop_grading.py` is its wiring.

    **This replaces a check that called itself "the whole of the grading
    surface" and was not.** It scanned for one verb list, matched nine modules,
    and `forward_evidence.py` and `reachability.py` — both of which build a
    clustered `stats.RoiInterval` over settled wagers and print a
    family-corrected Verdict per market — contained none of those tokens at
    `1fd4843`, the commit before this one. Measured with the guard lines
    deleted and nothing else changed: a 240-row `player_points` fixture ledger
    rendered ONE table row through `render_ledger` carrying 240 bets, 3
    day-clusters, a ROI, a 95% interval, a family-corrected interval and a
    verdict string, plus the matching `roi`/`adjusted_low`/`verdict` entry from
    `report_payload`, with `player_census.reconciled() == ()` and nothing
    raised. The fixture's own return is a property of the fixture and is not
    restated here; this file computes no interval and prints no verdict.

    It is a floor and not a proof, and the name says so:
    `test_a_lexical_scan_cannot_be_exhaustive_and_this_is_the_module_it_misses`
    below holds that gap open with a module that grades and is not seen.

    Mutation: add a module under `src/` naming `interval_two_way` -- RED.
    """
    found = _modules_naming_a_grading_token()
    known = (
        set(GRADES_A_WAGER_FRAME_AND_IS_GUARDED)
        | set(BUILDS_AN_INTERVAL_OVER_SOMETHING_THAT_IS_NOT_A_WAGER)
        | set(READS_A_BUILT_RECORD_OR_CALLS_ONE_THAT_GRADES)
    )
    assert set(found) == known, (
        f"The grading surface moved. New: {sorted(set(found) - known)}. Gone: "
        f"{sorted(known - set(found))}. Each new one is a grader of wagers, and "
        "must call player_census.guard_graded_frame as its first statement and "
        "be named in player_census.GRADING_ENTRY_POINTS; or it builds an "
        "interval over something that is not a wager; or it reads a record "
        "somebody else graded. Say which, here, with the reason."
    )
    for module in GRADES_A_WAGER_FRAME_AND_IS_GUARDED:
        source = (REPO / module).read_text(encoding="utf-8")
        assert "guard_graded_frame" in source, module

    # And the declared entry points live in exactly those four modules, so the
    # two lists cannot drift apart without one of them going red.
    declared_modules = {
        "src/" + dotted.rsplit(".", 1)[0].replace(".", "/") + ".py"
        for dotted in PC.GRADING_ENTRY_POINTS
    }
    assert declared_modules == set(GRADES_A_WAGER_FRAME_AND_IS_GUARDED), (
        f"GRADING_ENTRY_POINTS names {sorted(declared_modules)} and the scan "
        f"calls {sorted(GRADES_A_WAGER_FRAME_AND_IS_GUARDED)} the graders."
    )


def test_a_lexical_scan_cannot_be_exhaustive_and_this_is_the_module_it_misses(tmp_path):
    """The limitation, written down as a passing assertion rather than a claim.

    The scan above reads source text. It finds a grader that SPELLS one of
    :data:`GRADING_TOKENS`, and it cannot find one that reaches the same
    arithmetic without spelling it — through `getattr`, through a re-export,
    through a name assembled at runtime. That is not hypothetical: it is the
    shape of the defect this whole section repairs. The old scan matched
    `roi_interval` and `forward_evidence.py` spells the type `stats.RoiInterval`
    in camel case, so a module that graded every settled wager on the board and
    printed a family-corrected Verdict per market was invisible to a check
    whose own name said "the whole of the grading surface".

    So this test WRITES the module the scan cannot see and asserts two things:
    that `GRADING_TOKENS` finds nothing in its source, and that the callable it
    resolves at run time **is** `stats.interval_two_way` — identity, the lab's
    one implementation of a clustered interval. It is not a straw man and it is
    not run over data: nothing in this file computes an interval or prints a
    verdict, which is a promise the module docstring makes and this test keeps.

    **This is a limitation clause and it is meant to go RED.** The day the
    check is strengthened — an AST walk of the call graph, an import-graph
    scan, a registry a grader has to register with — this test fails, and
    whoever strengthened it must delete it and rewrite the completeness
    sentence in `player_census.GRADING_ENTRY_POINTS`' docstring. Until then the
    pinned list is a FLOOR, the guard on the four graders is the gate, and "the
    whole of the grading surface" is a sentence this file does not say.
    """
    hidden = tmp_path / "a_grader_the_scan_cannot_see.py"
    hidden.write_text(
        "from cbb_betting_lab import stats\n"
        "\n"
        "def clustered():\n"
        "    return getattr(stats, 'interval_' + 'two_way')\n"
        "\n"
        "def grade(frame):\n"
        "    return getattr(clustered()(frame, looks=1), 'ver' + 'dict')()\n",
        encoding="utf-8",
    )

    assert GRADING_TOKENS.search(hidden.read_text(encoding="utf-8")) is None, (
        "the scan now sees a grader that names none of its tokens. If that is "
        "because the check became structural, delete this test and re-read the "
        "completeness claim in player_census.GRADING_ENTRY_POINTS."
    )
    assert "guard_graded_frame" not in hidden.read_text(encoding="utf-8")

    sys.path.insert(0, str(tmp_path))
    try:
        module = importlib.import_module(hidden.stem)
        reached = module.clustered()
    finally:
        sys.path.remove(str(tmp_path))
        sys.modules.pop(hidden.stem, None)

    from cbb_betting_lab import stats

    assert reached is stats.interval_two_way, (
        "the module the scan misses no longer reaches the lab's clustered "
        "interval, so it has stopped demonstrating anything and this "
        "limitation clause needs rewriting rather than keeping."
    )
    assert callable(getattr(module, "grade")), (
        "the grading path is gone from the fixture module"
    )


# --------------------------------------------------------------------------
# The real store
# --------------------------------------------------------------------------


def test_the_gate_reconciles_the_store_it_is_pinned_to():
    """The count, over the real store when it is on disk and over the artifact when not.

    Full corpus, measured 2026-09-06: 3,863,325 rows scanned, 504,394 player
    quotes, 261,870 wagers raw against 257,474 folded, 4,396 attributed to 64
    groups with residual 0, 1,180 events over 140 days from 10 books, all season
    2024 / segment game / snapshot phase card. Every one of design section 6's
    ten per-market wager counts and both of section 10's totals reproduced
    exactly. 12 seconds.

    Mutation: `residual != 0` -> `residual > 10` in `reconcile` — RED against
    the real store only if the store moves, so the fixture tests above carry
    that proof and this one carries the count.
    """
    expected = PC.load_expected(ARTIFACT_PATH)
    if not PC.DEFAULT_STORE_PATH.is_file():
        # No store on disk. The artifact's own arithmetic still has to close,
        # and it is the thing a run would be checked against.
        assert sum(expected.wagers_raw.values()) == expected.totals["total_raw"]
        assert (
            expected.totals["priced_raw"] + expected.totals["refused_raw"]
            == expected.totals["total_raw"]
        )
        assert expected.totals["total_raw"] - expected.totals["total_folded"] == 4396
        assert expected.invariants["collision_groups"] == 64
        return

    attribution = PC.assert_reconciles()
    taken = attribution.census
    assert taken.total_raw == 261870
    assert taken.total_folded == 257474
    assert taken.difference == 4396
    assert taken.residual == 0
    assert len(taken.collisions) == 64
    assert taken.priced_raw == 261147
    assert taken.refused_raw == 723
    assert taken.player_quotes == 504394
    assert taken.rows_scanned == 3863325
    assert taken.seasons == ("2024",)
    assert taken.segments == ("game",)
    assert taken.snapshot_phases == ("card",)
    assert attribution.declared_checks == 23
    assert attribution.pinned_checks == 30
    # And the 52 are 52 clauses that COMPARED something. `declared_checks` and
    # `pinned_checks` partition the clauses attempted, by where the expectation
    # came from, and both are read off the artifact's `sources` block; an
    # expectation deleted from a value section left them unmoved while the
    # comparison silently did not run. See
    # `test_a_clause_whose_expectation_is_absent_is_refused_not_counted_as_
    # checked` for the measurement.
    assert len(attribution.checked) == 53
    assert attribution.compared_checks == 46, (
        f"{attribution.compared_checks} of the 53 clauses compared a value "
        "against the artifact. Twelve markets give 24, plus six totals, twelve "
        "invariants and four subject counts; the remaining seven -- the digest, "
        "the declared subject normalizer, the residual, the two collision "
        "clauses, the roster and the null key fields -- need no expectation and "
        "are checked unconditionally."
    )
    assert sum(c.odds_disagreements for c in taken.collisions) == 3959, (
        "the collapsing keys that carry two different american_odds are the "
        "ones where the shipped best_price_per_wager returns two rows for one "
        "athlete-line-side"
    )
    assert not any(c.same_book for c in taken.collisions)
    assert not any(c.roster_ambiguous for c in taken.collisions)
    assert taken.ambiguous_subjects == (
        ("401604303", "justin moore", ("4592491.0", "5105780.0")),
    ), (
        "exactly one quoted (game, folded-name) pair of 9,098 covers two "
        "athlete_ids, and section 7's R1 refuses rather than picking"
    )


# --------------------------------------------------------------------------
# Limitations: each of these is red the day it closes
# --------------------------------------------------------------------------


def test_the_limitations_this_gate_ships_with():
    """Five things this gate cannot do. Assertions, so they cannot rot into prose.

    1. **The denominator it certifies is a STRING count, not an athlete count.**
       The price store carries no `athlete_id` column. The graded denominator is
       only knowable after design section 7's R1 cascade runs and its refusals
       are removed; an approximation of R1's pre-match fold counts 251,949, at
       least 5,525 below the design's number. The gate must run a second time,
       on resolved athletes, against a third declared number.
    2. **The DESIGN declares no subject normalizer; the code now does.** Five
       reasonable folds give five denominators and the design names none of
       them. `stores.normalise_subject` declared `casefold` on 2026-09-06,
       `DECLARED_SUBJECT` recovers which menu entry that is by running it, and
       `reconcile` refuses a declaration outside the menu -- so the half of
       this clause that said "make reconcile compare against that one by name"
       has been done. What is still open is the artifact: `declared_subject` is
       null in `data/processed/cbb_player_census.json`, so the gate's frozen
       record of what was declared does not carry the declaration, and the raw
       count is still counted beside the folded one because neither headline is
       a grading denominator.
    3. **Design section 10 is written as an equality that can never hold.**
       Implemented as an attribution, and the disagreement is reported.
    4. **Nothing has been graded.** No de-vig, no log loss, no interval and no
       verdict exists anywhere in this tree for a player prop.
    5. **A grading run files its own dispositions now, and the SHIPPED card
       and backtest still do not.** This clause has been re-pointed twice. It
       began as "no shipped script files a disposition, so no run can pass the
       second half of this gate"; on 2026-09-07 `scripts/run_prop_accounting.
       py` closed that and it was re-pointed at "the runs that turn wagers into
       numbers file nothing"; and `scripts/run_prop_grading.py` closed THAT on
       the same day — it walks the store forward, hands
       `reports.gameday_card.opinions_for` a `RunDisposition`, calls
       `assert_every_offered_prop_is_accounted`, and only then scores anything.

       It is re-pointed again rather than deleted, at the half that is still
       open: **the two shipped runs that price props every night file
       nothing.** `scripts/run_price_backtest.py` and
       `scripts/run_gameday_card.py` both call `opinions_for` with
       `dispositions=None`, so neither can produce the second receipt in its
       own process, and a receipt from the grading run does not outlive it.
       `price_backtest.build_record` therefore still scores player markets with
       no census — `test_the_grading_commit_still_owes_this_gate` holds that
       open — and the card still prices props it has filed no disposition for.
       The day either of them files one, check that it also calls
       `assert_every_offered_prop_is_accounted` before it scores, and re-point
       this clause again.

    Each clause goes red the day it closes, and the instruction is to re-point
    it at the next limitation, never to delete it.
    """
    columns = pd.read_csv(
        PC.DEFAULT_STORE_PATH, nrows=0
    ).columns.tolist() if PC.DEFAULT_STORE_PATH.is_file() else list(STORE_COLUMNS)
    assert "athlete_id" not in columns, (
        "CLAUSE 1 HAS CLOSED: the price store now carries athlete_id, so an "
        "athlete-level denominator is measurable. Run this gate a second time "
        "on resolved athletes and declare that third number; do not delete this."
    )

    expected = PC.load_expected(ARTIFACT_PATH)
    assert expected.declared_subject is None, (
        "CLAUSE 2 HAS CLOSED FURTHER: the frozen artifact now records a "
        "declared subject. Re-point this at whatever is still undeclared -- the "
        "athlete-level fold is the obvious next one -- and do not delete it."
    )
    assert set(PC.SUBJECT_NORMALIZERS) == {"raw", "casefold"}
    # The half that HAS closed, asserted positively so it cannot rot back into
    # prose: the code's declaration is read, not retyped, and the store side of
    # the pre-grading identity counts under it.
    assert PC.DECLARED_SUBJECT == "casefold"
    assert PC.SUBJECT_NORMALIZERS[PC.DECLARED_SUBJECT]("A.J. HOGGARD") == (
        stores.normalise_subject("A.J. HOGGARD")
    ), (
        "`DECLARED_SUBJECT` names a fold `stores.normalise_subject` does not "
        "implement, so the offered side of the identity counts a denominator "
        "the lab has not declared"
    )

    assert expected.totals["total_raw"] != expected.totals["total_folded"], (
        "CLAUSE 3 HAS CLOSED: the two counts are now equal, so section 10's "
        "gate could be an equality after all. Say what changed in the store."
    )

    tree = ast.parse(MODULE_PATH.read_text(encoding="utf-8"))
    named = {
        node.id if isinstance(node, ast.Name) else node.attr
        for node in ast.walk(tree)
        if isinstance(node, (ast.Name, ast.Attribute))
    }
    forbidden = {
        "log_loss",
        "logloss",
        "brier",
        "devig",
        "de_vig",
        "fair_price",
        "roi",
        "edge",
    }
    assert not (named & forbidden), (
        "CLAUSE 4 HAS CLOSED: player_census.py names "
        f"{sorted(named & forbidden)}. This module counts rows and refuses; it "
        "states no result. Grading belongs in its own commit, gated on this one."
    )

    scripts = sorted((REPO / "scripts").glob("*.py"))
    assert scripts, "the scripts directory is empty, so this scan proves nothing"
    sources = {path.name: path.read_text(encoding="utf-8") for path in scripts}
    filing = sorted(
        name for name, text in sources.items() if "RunDisposition(" in text
    )
    assert filing == ["run_prop_accounting.py", "run_prop_grading.py"], (
        f"{filing} file a disposition. A script that files one must also call "
        "`assert_every_offered_prop_is_accounted` on what it filed, or it has "
        "produced half an identity and nothing checks the other half; add it "
        "here in the same commit."
    )
    for name in filing:
        assert "assert_every_offered_prop_is_accounted" in sources[name], (
            f"{name} files dispositions and never reconciles them. Counting "
            "what a run did with every prop and then not comparing it against "
            "what the store offered is the accounting that reconciles by "
            "construction, one lab over."
        )

    # The half that is still open, asserted so it goes red the day it closes:
    # the runs that produce numbers over these wagers file nothing, so neither
    # can pass the second half of the gate. `dispositions=` is the only way in
    # and both leave it at its default.
    for name in ("run_price_backtest.py", "run_gameday_card.py"):
        assert "dispositions" not in sources[name], (
            f"CLAUSE 5 HAS MOVED: {name} now passes a disposition to "
            "`opinions_for`. Check that it calls "
            "`assert_every_offered_prop_is_accounted` before it scores "
            "anything, add its entry point back to GRADING_ENTRY_POINTS if it "
            "gained one, and re-point this clause; do not delete it."
        )

    assert PC.accounted() == (), (
        "a disposition receipt survived into this test, so the gate would look "
        "open in a file that never ran it"
    )


def test_every_grading_entry_point_filters_before_it_gates():
    """Both halves, at all six doors, because fixing one door moved the bug.

    Commit 6549cd7 made `player_markets_in` subtract the markets refused by
    name, so `guard_graded_frame` returned `()` on a frame whose only player
    market was refused. The justification was that such a market "is filtered
    out of every verdict table and every JSON payload" — true of THREE entry
    points. `GRADING_ENTRY_POINTS` names five, and `forecast_skill` and
    `price_backtest` never called the filter, so for those two the gate was the
    only thing keeping a refused market out.

    Measured at the shipped entry point with no receipt: a 16-row
    `player_double_double` frame through `forecast_skill.build_record` returned
    a Brier score, a de-vigged advantage and a verdict.

    So the filter runs BEFORE the gate at each door, and both halves are
    asserted at each: a refused market is silently dropped rather than scored,
    and a market that CAN be graded is refused without a receipt.
    """
    from cbb_betting_lab.models.player_rates import MARKETS_REFUSED_BY_NAME

    assert PC.reconciled() == (), (
        "this test needs a process with no receipt; something reconciled first"
    )
    refused = sorted(MARKETS_REFUSED_BY_NAME)[0]

    def _frame(market: str, n: int = 16) -> pd.DataFrame:
        return pd.DataFrame(
            {
                "market": [market] * n,
                "tier": ["high_major"] * n,
                "selection": ["over", "under"] * (n // 2),
                "american_odds": [-110] * n,
                "outcome": ["won", "lost"] * (n // 2),
                "book": ["dk"] * n,
                "event_id": [f"e{i}" for i in range(n)],
                "player": ["A Player"] * n,
                "line": [10.5] * n,
                "profit_units": [1.0, -1.0] * (n // 2),
                "model_probability": [0.5] * n,
                "slate_date": ["2024-01-05"] * n,
            }
        )

    # The gate itself sees a refused market again — the subtraction is gone.
    assert PC.player_markets_in(_frame(refused)) == (refused,), (
        "the gate no longer counts a market refused by name, which is what let "
        "two entry points score one"
    )

    # Half one: a market that CAN be graded is refused without a receipt.
    from cbb_betting_lab.reports import forecast_skill as FS
    from cbb_betting_lab.reports import price_backtest as PBT
    from cbb_betting_lab.reports import prop_grading as PG

    with pytest.raises(PC.WagerCountMismatch):
        FS.build_record(FS.SkillInputs(graded=_frame("player_points")))
    with pytest.raises(PC.WagerCountMismatch):
        PBT.settled_opinions(_frame("player_points"))
    with pytest.raises(PC.WagerCountMismatch):
        PG.build_record(PG.PropGradingInputs(graded=_frame("player_points")))

    # Half two: a refused market is refused too, and that is FAIL-CLOSED
    # rather than a nuisance. The gate is required by its own test to be the
    # first statement in each entry point — "a gate that runs after the de-vig
    # is a gate on the report, not on the run" — so it sees the frame before
    # anything is filtered. With no receipt it refuses everything player-shaped,
    # including markets that could never be graded anyway.
    with pytest.raises(PC.WagerCountMismatch):
        FS.build_record(FS.SkillInputs(graded=_frame(refused)))
    with pytest.raises(PC.WagerCountMismatch):
        PBT.settled_opinions(_frame(refused))
    with pytest.raises(PC.WagerCountMismatch):
        PG.build_record(PG.PropGradingInputs(graded=_frame(refused)))

    # And the filter still runs, immediately after the gate, so a receipt does
    # not let a refused market be scored. Asserted on the source rather than by
    # driving it, because driving it needs a reconciled census over the real
    # store and this test has none: the ORDER is what matters and the order is
    # what is read.
    import inspect

    for function in (FS.build_record, PBT.settled_opinions, PG.build_record):
        body = inspect.getsource(function)
        gate_at = body.index("guard_graded_frame")
        filter_at = body.index("without_markets_refused_by_name")
        assert gate_at < filter_at, (
            f"{function.__qualname__} filters before it gates; the gate must be "
            "the first statement and the filter must follow it"
        )


def test_the_grading_commit_still_owes_this_gate():
    """`price_backtest.build_record` scores player markets with NO census.

    **Written down because it cannot be closed here.** `guard_graded_frame`
    demands two receipts. The second is set only by
    `assert_every_offered_prop_is_accounted`, and as of 2026-09-07 it has a
    caller — `scripts/run_prop_accounting.py`, which is clause 5 above closing
    and being re-pointed. That producer is a **separate invocation**: its
    receipt lives for the length of its own process and is gone before the
    backtest starts, so `build_record` is no closer to carrying one than it was
    when nothing filed the second receipt at all. What has changed is that the
    receipt is now producible, so the remaining work is wiring rather than a
    missing gate.

    `build_record` is not a not-yet path. It is the shipped backtest's ROI
    half, it runs on every invocation, and the committed
    `data/outputs/cbb_price_backtest.json` holds 127 null-baseline rows over
    twelve player markets that it produced. Gating it was attempted three times
    and each attempt only changed which refusal the run died on; the last paid
    a full pass over the 978 MB store first.

    So the hole is real and stated: this function scores player markets without
    a census receipt. The filter still runs, so a market refused BY NAME never
    reaches a verdict — that needs no receipt. Closing the rest belongs in the
    grading commit the census was built for, and it is a commit that now has
    the receipt it was waiting on: `scripts/run_prop_accounting.py` files one,
    over the whole store, and prints what became of every prop.
    """
    # **Read the CALLS, not the prose.** The first version of this asserted
    # `"guard_graded_frame" not in source` and failed on the COMMENT above the
    # code explaining why the gate is absent — a test matching text instead of
    # behaviour, inside the test written about that very habit.
    import ast
    import inspect
    import textwrap

    from cbb_betting_lab.reports import price_backtest as PBT

    tree = ast.parse(textwrap.dedent(inspect.getsource(PBT.build_record)))
    called = {
        getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    }
    assert "guard_graded_frame" not in called, (
        "`build_record` now CALLS the census gate. If the second receipt has a "
        "producer, add the name back to GRADING_ENTRY_POINTS, drive it in the "
        "five-door test, and delete this. If it does not, the shipped backtest "
        "cannot run: measured three times, each attempt only changing which "
        "refusal it died on."
    )
    assert "without_markets_refused_by_name" in called, (
        "the refusal filter came off with the gate. It needs no receipt and a "
        "market refused by name must never carry a verdict."
    )
    assert PC.accounted() == (), (
        "something filed the accounting receipt, so the not-yet gate is "
        "satisfiable now and this gap can be closed properly"
    )
