"""The wager census gate: what it counts, what it refuses, and what it may not skip.

Design section 10: *"Gate before grading: reconcile 261,870 wagers (measured, by
event/market/player/selection/line) against the brief's 257,474. A 1.7%
unexplained denominator is a wrong-denominator error of the same family. The run
stops until it reconciles."*

**Nothing in this file grades anything and nothing here states a result.** There
is no probability, no de-vig, no log loss, no ROI, no interval and no verdict in
it. Every number below is a count of rows in a table, and each says how it was
counted.

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
    """
    record = {
        "schema_version": 1,
        "declared_subject": None,
        "source": {
            "path": taken.source_path,
            "sha256": taken.source_sha256,
            "bytes": taken.source_bytes,
        },
        "quotes": {m.market: m.quotes for m in taken.by_market},
        "wagers_raw": {m.market: m.wagers_raw for m in taken.by_market},
        "totals": {
            "total_raw": taken.total_raw,
            "total_folded": taken.total_folded,
            "priced_raw": taken.priced_raw,
            "priced_folded": taken.priced_folded,
            "refused_raw": taken.refused_raw,
            "refused_folded": taken.refused_folded,
        },
        "subjects": {
            "raw": taken.subjects_raw,
            "folded": taken.subjects_folded,
            "player_points_raw": taken.points_subjects_raw,
            "player_points_folded": taken.points_subjects_folded,
        },
        "invariants": {
            "rows_scanned": taken.rows_scanned,
            "player_quotes": taken.player_quotes,
            "events": taken.events,
            "game_ids": taken.game_ids,
            "slate_dates": taken.slate_dates,
            "events_with_two_game_ids": taken.events_with_two_game_ids,
            "books": len(taken.books),
            "collision_groups": len(taken.collisions),
            "ambiguous_subjects": len(taken.ambiguous_subjects),
            "seasons": list(taken.seasons),
            "segments": list(taken.segments),
            "snapshot_phases": list(taken.snapshot_phases),
        },
        "sources": {},
        "notes": {},
    }
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


def test_no_player_wager_can_be_graded_until_this_gate_has_run(tmp_path):
    """The two grading entry points refuse a player frame with no receipt.

    `forecast_skill.build_record` is design section 10's own metric — it de-vigs,
    scores log loss and Brier and builds the clustered intervals — and it
    already carries `player` as an optional column, casefolded in the de-vig
    pair scope. A frame of player props handed to it needs NO new code to be
    graded. `price_backtest.settled_opinions` is the ROI half. Both call
    `guard_graded_frame` before they read a probability, and it fails closed.

    Mutation: delete the `player_census.guard_graded_frame(...)` line from
    `forecast_skill.build_record` — RED. Same for `settled_opinions` — RED.
    """
    from cbb_betting_lab.reports import forecast_skill as FS
    from cbb_betting_lab.reports import price_backtest as PB

    team = pd.DataFrame(
        {"market": ["spreads"], "model_probability": [0.5], "outcome": ["won"]}
    )
    props = pd.DataFrame(
        {"market": ["player_points"], "model_probability": [0.5], "outcome": ["won"]}
    )

    assert PC.reconciled() == ()
    # A team frame passes with no receipt at all: the guard costs one prefix
    # test and refuses nothing this lab has ever measured. (Whether the row
    # survives `settled` is a different question and not this gate's.)
    assert PC.player_markets_in(team) == ()
    assert isinstance(PB.settled_opinions(team), pd.DataFrame)
    assert isinstance(FS.build_record(FS.SkillInputs(graded=team.iloc[0:0])), dict)
    with pytest.raises(PC.WagerCountMismatch, match="no wager census has reconciled"):
        PB.settled_opinions(props)
    with pytest.raises(PC.WagerCountMismatch, match="no wager census has reconciled"):
        FS.build_record(FS.SkillInputs(graded=props))

    # And with the gate run, the same call is allowed through.
    store = write_store(tmp_path / "p.csv", [quote()])
    roster = write_roster(tmp_path / "r.csv", (("G1", "1", "Al Jones"),))
    taken = PC.census(store, roster=roster)
    PC.assert_reconciles(
        store=store, roster=roster, expected=write_expected(tmp_path / "e.json", taken)
    )
    assert len(PC.reconciled()) == 1
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


def test_the_two_declared_entry_points_are_the_whole_of_the_grading_surface():
    """Every module in the tree that names a grading verb, pinned with a reason.

    Nine modules, measured 2026-09-06 by the regexp below over `src/` and
    `scripts/`. Two of them GRADE and carry the guard; the rest read a record
    that has already been built, or call the two that do. The day a tenth
    appears this goes red and its author has to say which kind it is — which is
    how "whatever entry point a later commit adds" stays covered without this
    file guessing a filename.

    Mutation: add a new module under src/ naming `log_loss` — RED.
    """
    pattern = re.compile(
        r"\b(log_loss|logloss|brier|de_?vig|fair_price|scorable|settled_opinions"
        r"|roi_interval)\b",
        re.IGNORECASE,
    )
    found = sorted(
        path.relative_to(REPO).as_posix()
        for base in ("src", "scripts")
        for path in (REPO / base).rglob("*.py")
        if pattern.search(path.read_text(encoding="utf-8"))
    )
    grades_and_is_guarded = {
        "src/cbb_betting_lab/reports/forecast_skill.py":
            "design section 10's metric; guarded in build_record",
        "src/cbb_betting_lab/reports/price_backtest.py":
            "the ROI half; guarded in settled_opinions",
    }
    reads_an_already_built_record_or_calls_one_that_grades = {
        "src/cbb_betting_lab/models/player_census.py": "this gate, naming the verbs",
        "src/cbb_betting_lab/reports/what_we_can_claim.py": "reads the written records",
        "src/cbb_betting_lab/reports/why_the_model.py": "reads cbb_forecast_skill.json",
        "src/cbb_betting_lab/restatement.py": "the vocabulary of derived words",
        "scripts/build_skill_frame.py": "builds the frame; grades nothing",
        "scripts/run_forecast_skill.py": "calls forecast_skill.build_record",
        "scripts/run_price_backtest.py": "calls price_backtest.settled_opinions",
    }
    known = set(grades_and_is_guarded) | set(
        reads_an_already_built_record_or_calls_one_that_grades
    )
    assert set(found) == known, (
        f"The grading surface moved. New: {sorted(set(found) - known)}. Gone: "
        f"{sorted(known - set(found))}. Each new one is either a grader, and "
        "must call player_census.guard_graded_frame before it reads a "
        "probability, or a reader of an already-built record, and must be named "
        "here with that reason."
    )
    for module in grades_and_is_guarded:
        source = (REPO / module).read_text(encoding="utf-8")
        assert "guard_graded_frame" in source, module


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
    assert attribution.pinned_checks == 29
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
    """Four things this gate cannot do. Assertions, so they cannot rot into prose.

    1. **The denominator it certifies is a STRING count, not an athlete count.**
       The price store carries no `athlete_id` column. The graded denominator is
       only knowable after design section 7's R1 cascade runs and its refusals
       are removed; an approximation of R1's pre-match fold counts 251,949, at
       least 5,525 below the design's number. The gate must run a second time,
       on resolved athletes, against a third declared number.
    2. **No subject normalizer is declared.** Five reasonable folds give five
       denominators and the design names none of them.
    3. **Design section 10 is written as an equality that can never hold.**
       Implemented as an attribution, and the disagreement is reported.
    4. **Nothing has been graded.** No de-vig, no log loss, no interval and no
       verdict exists anywhere in this tree for a player prop.

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
        "CLAUSE 2 HAS CLOSED: the lab has declared a subject normalizer. Make "
        "reconcile compare against that one by name and say what the other is "
        "for; do not delete this."
    )
    assert set(PC.SUBJECT_NORMALIZERS) == {"raw", "casefold"}

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
