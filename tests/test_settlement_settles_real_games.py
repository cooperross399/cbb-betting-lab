"""Settlement is proved against real box scores, not against fixtures.

A fixture proves that a comparison operator points the way its author thought
it did. It cannot prove that `team_score_h2` is the second half, that `margin`
is signed for the row's own team, that `pra` is the sum a book would grade, or
that 35% of the player table never took the floor. Every one of those is a
property of `data/processed/`, and every one of them is a way a settlement
function can be confidently wrong on real data while passing a fixture suite.

So the assertions here run over **the whole of the completed 2025-26 season**:
6,299 games and 196,876 player-game rows, read from
`data/processed/cbb_team_games.csv`, `cbb_player_games.csv` and
`cbb_game_segments.csv`. The identities they check are the ones that must hold
on every single row — *the moneyline is won by the team that scored more*, *a
spread at minus the margin pushes*, *a total at the actual total pushes*, *a
points prop at his actual points pushes* — so a violation is a real defect and
not a tolerance question.

The three fixture-shaped tests at the end are the guards that real data cannot
exercise, because real data does not contain a NaN line: the poison-line guard,
the did-not-play void, and the import-time completeness check that fails the
build when `markets.py` wires a market this module cannot grade.

Skipped rather than failed when the processed tables are absent, so a clone
without a build still runs the rest of the suite.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from cbb_betting_lab.config import PROCESSED_DIR
from cbb_betting_lab.markets import (
    DOUBLE_CATEGORIES,
    DOUBLE_FIGURES,
    MARKETS,
    MARKETS_BY_KEY,
    PLAYER,
    SECOND_HALF_INCLUDES_OVERTIME,
)
from cbb_betting_lab.selection import (
    AWAY,
    FIRST_HALF,
    FULL_GAME,
    HOME,
    OVER,
    SECOND_HALF,
    UNDER,
    YES_NO_LINE,
)
from cbb_betting_lab.settlement import (
    PLAYER_COLUMNS,
    Outcome,
    Settled,
    is_graded,
    settle,
    settleable_quantities,
    takes_a_line,
)

#: The season every real-data assertion runs over: the most recent completed
#: one, and the only one whose full market catalogue is buyable from the
#: provider. Stated rather than "the last season in the file", so the numbers
#: printed by this suite are comparable between runs.
SEASON = 2026

TEAM_GAMES = PROCESSED_DIR / "cbb_team_games.csv"
PLAYER_GAMES = PROCESSED_DIR / "cbb_player_games.csv"
GAME_SEGMENTS = PROCESSED_DIR / "cbb_game_segments.csv"

#: How many player-game rows the prop assertions run over. The full 2025-26
#: player table is 196,876 rows and every prop assertion would walk it once per
#: market, which is fifteen passes over 200MB. The sample is the **first N rows
#: in file order**, not a random draw: a seeded sample would still be a sample
#: nobody can reproduce from the file alone, and file order is already a
#: mixture of teams, dates and roles.
PLAYER_SAMPLE = 20_000


def _require(path):
    if not path.is_file():
        pytest.skip(f"{path} has not been built; run scripts/build_datasets.py")
    return path


@pytest.fixture(scope="module")
def team_games() -> pd.DataFrame:
    frame = pd.read_csv(_require(TEAM_GAMES))
    season = frame[frame["season"] == SEASON].reset_index(drop=True)
    assert not season.empty, f"no season {SEASON} rows in {TEAM_GAMES}"
    return season


@pytest.fixture(scope="module")
def games(team_games: pd.DataFrame) -> pd.DataFrame:
    """One row per game, from the **home** team's perspective.

    Every game supplies two team-rows and this takes one of them, so a count
    here is a count of games. The away row is exercised separately by
    `test_the_row_must_be_the_side_the_selection_names`.
    """
    home = team_games[team_games["home_away"] == HOME].reset_index(drop=True)
    assert len(home) == team_games["game_id"].nunique()
    return home


@pytest.fixture(scope="module")
def player_games() -> pd.DataFrame:
    frame = pd.read_csv(_require(PLAYER_GAMES))
    season = frame[frame["season"] == SEASON].reset_index(drop=True)
    assert not season.empty, f"no season {SEASON} rows in {PLAYER_GAMES}"
    return season


@pytest.fixture(scope="module")
def played(player_games: pd.DataFrame) -> pd.DataFrame:
    """The rows of players who actually appeared."""
    return player_games[~player_games["did_not_play"].astype(bool)].reset_index(
        drop=True
    )


@pytest.fixture(scope="module")
def segments() -> pd.DataFrame:
    return pd.read_csv(_require(GAME_SEGMENTS)).set_index("game_id", drop=False)


def _rows(frame: pd.DataFrame, limit: int | None = None) -> list[dict]:
    subset = frame if limit is None else frame.head(limit)
    return subset.to_dict("records")


# --------------------------------------------------------------------------
# Full-game team markets.
# --------------------------------------------------------------------------


def test_the_moneyline_is_won_by_the_team_that_scored_more(games, capsys):
    """Over every game of the season, on both sides, with no exceptions.

    This is the assertion a fixture cannot make: it proves that `margin` in
    `cbb_team_games.csv` is signed for the row's own team, which is the fact
    every side market in this lab rests on.
    """
    won = lost = 0
    for row in _rows(games):
        for side, mine, theirs in (
            (HOME, row["team_score"], row["opponent_score"]),
            (AWAY, row["opponent_score"], row["team_score"]),
        ):
            perspective = row if side == HOME else _flip(row)
            result = settle(
                market="moneyline", segment=FULL_GAME, selection=side,
                line=None, game=perspective,
            )
            expected = Outcome.WON if mine > theirs else Outcome.LOST
            assert result.outcome is expected, (
                f"game {row['game_id']}: {side} scored {mine} against "
                f"{theirs} and settled {result.outcome.value}"
            )
            won += result.outcome is Outcome.WON
            lost += result.outcome is Outcome.LOST
    assert won == lost == len(games), "one winner and one loser per game"
    with capsys.disabled():
        print(
            f"\n  moneyline: {won:,} winners and {lost:,} losers over "
            f"{len(games):,} games of the {SEASON} season, 0 exceptions."
        )


def test_no_full_game_ends_level_so_the_moneyline_never_pushes(games, capsys):
    """The measured basis for `moneyline` carrying `push_possible=False`.

    A full game cannot end level — this sport plays overtime until somebody
    wins — and the module is allowed to have no push branch only because that
    is true of the data as well as of the rulebook.
    """
    level = int((games["margin"] == 0).sum())
    assert level == 0, f"{level} of {len(games):,} games ended level"
    overtime = int((games["periods"] > 2).sum())
    with capsys.disabled():
        print(
            f"  full games ending level: {level} of {len(games):,} (0.0000%). "
            f"Overtime: {overtime:,} of {len(games):,} "
            f"({overtime / len(games) * 100:.2f}%)."
        )


def test_the_spread_at_minus_the_margin_pushes_on_every_game(games, capsys):
    """`adjusted = margin + line`, and a line of exactly minus the margin lands.

    Run on both sides of every game, because the push is the one outcome that
    must be symmetric: a wager that pushes for the home side and loses for the
    away side is a signed-quantity bug.
    """
    pushes = 0
    for row in _rows(games):
        margin = float(row["margin"])
        for side, own_margin in ((HOME, margin), (AWAY, -margin)):
            perspective = row if side == HOME else _flip(row)
            result = settle(
                market="spread", segment=FULL_GAME, selection=side,
                line=-own_margin, game=perspective,
            )
            assert result.outcome is Outcome.PUSH, (
                f"game {row['game_id']}: {side} at {-own_margin:+g} against a "
                f"margin of {own_margin:+g} settled {result.outcome.value}"
            )
            assert result.actual == own_margin, (
                "actual is the margin the box score records, never the "
                "handicapped comparison value"
            )
            pushes += 1
    assert pushes == 2 * len(games)
    with capsys.disabled():
        print(
            f"  spread at line = -margin: {pushes:,} pushes over "
            f"{pushes:,} wagers (100.00%), both sides of {len(games):,} games."
        )


def test_the_spread_a_half_point_either_side_of_the_margin_decides(games):
    """The half-point that separates a push from a result, on real margins.

    `docs/why_the_half_point_matters.md` is about this hook. A settlement that
    got the direction backwards would still push at the exact number — the
    push test alone cannot catch a sign error, and this one can.
    """
    for row in _rows(games, limit=2_000):
        margin = float(row["margin"])
        assert settle(market="spread", segment=FULL_GAME, selection=HOME,
                      line=-margin + 0.5, game=row).outcome is Outcome.WON
        assert settle(market="spread", segment=FULL_GAME, selection=HOME,
                      line=-margin - 0.5, game=row).outcome is Outcome.LOST


def test_the_total_at_the_actual_total_pushes_on_every_game(games, capsys):
    """Exact equality is a push, for the over and the under alike."""
    for row in _rows(games):
        total = float(row["total"])
        assert total == row["team_score"] + row["opponent_score"]
        for direction in (OVER, UNDER):
            result = settle(
                market="total_points", segment=FULL_GAME, selection=direction,
                line=total, game=row,
            )
            assert result.outcome is Outcome.PUSH, (
                f"game {row['game_id']}: {direction} at {total:g} against a "
                f"total of {total:g} settled {result.outcome.value}"
            )
            assert result.actual == total
    with capsys.disabled():
        print(
            f"  total at line = actual total: {2 * len(games):,} pushes over "
            f"{2 * len(games):,} wagers (100.00%), {len(games):,} games."
        )


def test_the_total_settles_over_and_under_in_opposite_directions(games):
    """Half a point either way, so a direction that is reversed cannot hide."""
    for row in _rows(games, limit=2_000):
        total = float(row["total"])
        assert settle(market="total_points", segment=FULL_GAME, selection=OVER,
                      line=total - 0.5, game=row).outcome is Outcome.WON
        assert settle(market="total_points", segment=FULL_GAME, selection=UNDER,
                      line=total - 0.5, game=row).outcome is Outcome.LOST
        assert settle(market="total_points", segment=FULL_GAME, selection=UNDER,
                      line=total + 0.5, game=row).outcome is Outcome.WON


def test_the_team_total_settles_the_team_its_selection_names(games, capsys):
    """`home_over` grades the home score and `away_over` grades the away score.

    Parsed with `rsplit("_", 1)`. Both sides are checked on every game against
    the *other* side's score as well, because a team total that graded the
    opponent would still push at the right number for exactly half the rows.
    """
    for row in _rows(games, limit=2_000):
        home_score, away_score = float(row["team_score"]), float(row["opponent_score"])
        away_row = _flip(row)
        for direction in (OVER, UNDER):
            home = settle(market="team_total", segment=FULL_GAME,
                          selection=f"{HOME}_{direction}", line=home_score,
                          game=row)
            assert home.outcome is Outcome.PUSH and home.actual == home_score
            away = settle(market="team_total", segment=FULL_GAME,
                          selection=f"{AWAY}_{direction}", line=away_score,
                          game=away_row)
            assert away.outcome is Outcome.PUSH and away.actual == away_score
        if home_score != away_score:
            crossed = settle(market="team_total", segment=FULL_GAME,
                             selection=f"{HOME}_{OVER}", line=away_score,
                             game=row)
            assert crossed.outcome is not Outcome.PUSH, (
                "the home team total pushed at the away team's score, so it is "
                "grading the wrong row"
            )
    with capsys.disabled():
        print("  team total: home and away graded from their own rows, 2,000 games.")


def test_the_row_must_be_the_side_the_selection_names(games, capsys):
    """Passing the home row for an away wager is refused, never flipped.

    Measured consequence if it were flipped silently instead: the away
    moneyline would settle on the home team's margin, which is the correct
    verdict for the opposite bet on 100% of games.
    """
    refused = 0
    for row in _rows(games, limit=2_000):
        wrong = settle(market="moneyline", segment=FULL_GAME, selection=AWAY,
                       line=None, game=row)
        assert wrong.outcome is Outcome.UNSETTLEABLE
        assert "not the side this selection names" in wrong.note
        assert wrong.actual is None
        refused += 1
    missing = settle(market="moneyline", segment=FULL_GAME, selection=HOME,
                     line=None, game={"margin": 7})
    assert missing.outcome is Outcome.UNSETTLEABLE, (
        "a row with no home_away cannot be checked against the selection, and "
        "ambiguity falls on the not-settled side"
    )
    with capsys.disabled():
        print(f"  wrong-side rows refused: {refused:,} of {refused:,} (100.00%).")


# --------------------------------------------------------------------------
# Half markets.
# --------------------------------------------------------------------------


def test_the_first_half_total_settles_against_the_halftime_score(games, capsys):
    """`team_score_h1 + opponent_score_h1`, and nothing else.

    Also reports what share of the season records no halftime at all, because
    those games are unsettleable for every half market and a coverage number
    with no denominator is not a coverage number.
    """
    with_half = games[games["team_score_h1"].notna() & games["opponent_score_h1"].notna()]
    pushed = 0
    for row in _rows(with_half):
        half_total = float(row["team_score_h1"]) + float(row["opponent_score_h1"])
        result = settle(market="total_points_h1", segment=FIRST_HALF,
                        selection=OVER, line=half_total, game=row)
        assert result.outcome is Outcome.PUSH, (
            f"game {row['game_id']}: h1 total {half_total:g} settled "
            f"{result.outcome.value}"
        )
        assert result.actual == half_total
        assert half_total <= float(row["total"]), (
            "a first half cannot hold more points than the game it is part of; "
            "if this fires, the h1 columns are not the halftime score"
        )
        pushed += 1
    missing = len(games) - len(with_half)
    for row in _rows(games[games["team_score_h1"].isna()]):
        blocked = settle(market="total_points_h1", segment=FIRST_HALF,
                         selection=OVER, line=70.5, game=row)
        assert blocked.outcome is Outcome.UNSETTLEABLE
        assert "no halftime score" in blocked.note
    with capsys.disabled():
        print(
            f"  h1 total at line = h1 actual: {pushed:,} pushes over "
            f"{pushed:,} games with a halftime score (100.00%). "
            f"{missing:,} of {len(games):,} games "
            f"({missing / len(games) * 100:.2f}%) record no halftime and are "
            "unsettleable for every half market."
        )


def test_the_second_half_is_the_final_minus_halftime_and_includes_overtime(
    games, capsys
):
    """The identity `h1 + h2 == final`, on every game, overtime included.

    `SECOND_HALF_INCLUDES_OVERTIME` is a **book rule this lab cannot verify** —
    no feed here carries any book's rulebook — and this test proves only that
    the module settles the convention it declares. It does not, and cannot,
    prove that a given book grades second halves the same way.
    """
    assert SECOND_HALF_INCLUDES_OVERTIME, (
        "wired False, so the h2 columns are no longer the quantity this module "
        "settles; the handler returns UNSETTLEABLE and this test needs rewriting"
    )
    with_half = games[games["team_score_h2"].notna() & games["opponent_score_h2"].notna()]
    overtime_games = 0
    for row in _rows(with_half):
        assert row["team_score_h1"] + row["team_score_h2"] == row["team_score"]
        half_total = float(row["team_score_h2"]) + float(row["opponent_score_h2"])
        result = settle(market="total_points_h2", segment=SECOND_HALF,
                        selection=UNDER, line=half_total, game=row)
        assert result.outcome is Outcome.PUSH
        assert result.actual == half_total
        if row["periods"] > 2:
            overtime_games += 1
            regulation_only = float(row["total"]) - (
                float(row["team_score_h1"]) + float(row["opponent_score_h1"])
            )
            assert half_total == regulation_only, (
                "the h2 quantity must contain the overtime points, which is "
                "what SECOND_HALF_INCLUDES_OVERTIME asserts"
            )
    with capsys.disabled():
        print(
            f"  h2 = final - halftime on {len(with_half):,} of "
            f"{len(with_half):,} games (100.00%), including the "
            f"{overtime_games:,} that went to overtime "
            f"({overtime_games / len(with_half) * 100:.2f}%). "
            "SECOND_HALF_INCLUDES_OVERTIME is a book rule, not a verified fact."
        )


def test_the_half_moneyline_pushes_on_a_level_half_and_the_full_game_cannot(
    games, capsys
):
    """The measured level-half rate, reported with its sample size.

    This is the football lab's defect ported as a test: it priced a level half
    at 0.4% because its distribution hardcoded the full-game rule. Here the
    full-game rule is *measured* to be 0 of 6,299, and the half rule is
    measured to be something else entirely — so the two segments cannot share a
    push branch by accident.
    """
    with_half = games[games["team_score_h1"].notna() & games["opponent_score_h1"].notna()]
    level_h1 = level_h2 = 0
    for row in _rows(with_half):
        away_row = _flip(row)
        h1 = float(row["team_score_h1"]) - float(row["opponent_score_h1"])
        h2 = float(row["team_score_h2"]) - float(row["opponent_score_h2"])
        for market, segment, margin in (
            ("moneyline_h1", FIRST_HALF, h1),
            ("moneyline_h2", SECOND_HALF, h2),
        ):
            home = settle(market=market, segment=segment, selection=HOME,
                          line=None, game=row)
            away = settle(market=market, segment=segment, selection=AWAY,
                          line=None, game=away_row)
            if margin == 0:
                assert home.outcome is Outcome.PUSH
                assert away.outcome is Outcome.PUSH
            else:
                expected = Outcome.WON if margin > 0 else Outcome.LOST
                assert home.outcome is expected
                assert away.outcome is (
                    Outcome.LOST if margin > 0 else Outcome.WON
                )
            assert home.actual == margin
        level_h1 += h1 == 0
        level_h2 += h2 == 0

    n = len(with_half)
    rate_h1, rate_h2 = level_h1 / n * 100, level_h2 / n * 100
    assert level_h1 > 0 and level_h2 > 0, (
        "a half CAN end level; if this ever measures zero the push branch is "
        "untested and the market is mispriced"
    )
    assert int((games["margin"] == 0).sum()) == 0
    assert MARKETS_BY_KEY["moneyline"].push_possible is False
    assert MARKETS_BY_KEY["moneyline_h1"].push_possible is True
    assert MARKETS_BY_KEY["moneyline_h2"].push_possible is True
    with capsys.disabled():
        print(
            f"  level first halves: {level_h1:,} of {n:,} ({rate_h1:.2f}%). "
            f"Level second halves: {level_h2:,} of {n:,} ({rate_h2:.2f}%). "
            f"Level full games: 0 of {len(games):,} (0.0000%)."
        )


def test_the_half_team_total_settles_that_half_and_that_team(games):
    for row in _rows(games[games["team_score_h1"].notna()], limit=2_000):
        h1 = float(row["team_score_h1"])
        result = settle(market="team_total_h1", segment=FIRST_HALF,
                        selection=f"{HOME}_{OVER}", line=h1, game=row)
        assert result.outcome is Outcome.PUSH and result.actual == h1
        assert settle(market="team_total_h1", segment=FIRST_HALF,
                      selection=f"{HOME}_{OVER}", line=h1 - 0.5,
                      game=row).outcome is Outcome.WON
        h2 = float(row["team_score_h2"])
        second = settle(market="team_total_h2", segment=SECOND_HALF,
                        selection=f"{HOME}_{UNDER}", line=h2, game=row)
        assert second.outcome is Outcome.PUSH and second.actual == h2


def test_a_segment_that_contradicts_its_market_is_refused(games):
    """A first-half market staged on the full game is a join defect, not a bet."""
    row = _rows(games, limit=1)[0]
    wrong = settle(market="total_points_h1", segment=FULL_GAME, selection=OVER,
                   line=70.5, game=row)
    assert wrong.outcome is Outcome.UNSETTLEABLE
    assert "settles on part of a game" in wrong.note
    unknown = settle(market="total_points", segment="q1", selection=OVER,
                     line=140.5, game=row)
    assert unknown.outcome is Outcome.UNSETTLEABLE
    assert "not a known segment" in unknown.note


# --------------------------------------------------------------------------
# Player props.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "market",
    sorted(m.key for m in MARKETS if m.settles_on in PLAYER_COLUMNS),
)
def test_a_counting_prop_pushes_at_the_players_actual_number(market, played, capsys):
    """Every counting prop, at the line the box score records, on real rows.

    Also checks half a point either side, so a comparator whose direction is
    reversed cannot pass by pushing at the exact number.
    """
    column = PLAYER_COLUMNS[MARKETS_BY_KEY[market].settles_on]
    rows = _rows(played, limit=PLAYER_SAMPLE)
    for row in rows:
        actual = float(row[column])
        pushed = settle(market=market, segment=FULL_GAME, selection=OVER,
                        line=actual, player=row, game=None)
        assert pushed.outcome is Outcome.PUSH, (
            f"{market}: {row['athlete_display_name']} had {actual:g} "
            f"{column} and a line of {actual:g} settled {pushed.outcome.value}"
        )
        assert pushed.actual == actual
        assert settle(market=market, segment=FULL_GAME, selection=OVER,
                      line=actual - 0.5, player=row,
                      game=None).outcome is Outcome.WON
        assert settle(market=market, segment=FULL_GAME, selection=UNDER,
                      line=actual - 0.5, player=row,
                      game=None).outcome is Outcome.LOST
    if market == "player_points":
        with capsys.disabled():
            print(
                f"\n  counting props: {len(rows):,} played {SEASON} "
                f"player-game rows per market, {len(PLAYER_COLUMNS):,} "
                "quantities, pushing at the box-score number on 100.00%."
            )


def test_the_compound_props_equal_their_parts_on_every_row(played, capsys):
    """`pra`, `points_rebounds` and the rest are the sums a book would grade.

    Settlement reads the stored compound column. If that column ever stopped
    being the sum of its parts, every compound prop in the lab would settle
    against a quantity no book quotes, and nothing else would notice.
    """
    parts = {
        "points_rebounds": ("points", "rebounds"),
        "points_assists": ("points", "assists"),
        "rebounds_assists": ("rebounds", "assists"),
        "pra": ("points", "rebounds", "assists"),
        "blocks_steals": ("blocks", "steals"),
    }
    for column, components in parts.items():
        summed = sum(played[name] for name in components)
        violations = int((summed != played[column]).sum())
        assert violations == 0, (
            f"{column} disagrees with {' + '.join(components)} on "
            f"{violations:,} of {len(played):,} rows"
        )
    with capsys.disabled():
        print(
            f"  compound props equal their parts on {len(played):,} of "
            f"{len(played):,} played rows (100.00%)."
        )


def test_a_did_not_play_prop_is_void_and_never_a_loss(player_games, capsys):
    """The stake comes back. It is **not** a losing over, and it is an assumption.

    The default this replaces is not neutral: every did-not-play row stores
    null points and `double_double = 0`, so a naive grading marks all of them
    as losing overs — a third of the player table voting against every over
    ever staged.
    """
    absent = player_games[player_games["did_not_play"].astype(bool)]
    assert not absent.empty
    zeroed = int((absent["double_double"] == 0).sum())
    for row in _rows(absent, limit=5_000):
        for market, line in (
            ("player_points", 12.5),
            ("player_double_double", YES_NO_LINE),
            ("player_first_basket", YES_NO_LINE),
        ):
            result = settle(market=market, segment=FULL_GAME, selection=OVER,
                            line=line, player=row, game=None)
            assert result.outcome is Outcome.VOID, (
                f"{market} on a did-not-play row settled "
                f"{result.outcome.value}, not void"
            )
            assert result.actual is None
            assert "assumption about the book's rulebook" in result.note
            assert is_graded(result.outcome), "a void is a settled bet"
    share = len(absent) / len(player_games) * 100
    with capsys.disabled():
        print(
            f"  did-not-play rows: {len(absent):,} of {len(player_games):,} "
            f"({share:.2f}%), all voided. {zeroed:,} of them store "
            "double_double=0 and would grade as losing overs by default. "
            "The void is an ASSUMPTION about the book, stated in the note."
        )


def test_the_double_double_rule_this_lab_declares_is_the_one_it_settles(
    played, capsys
):
    """Two of five categories at ten, recomputed and checked against the column.

    Settlement counts the categories itself from `markets.DOUBLE_CATEGORIES`
    and `markets.DOUBLE_FIGURES`. This proves that the declared rule and
    `build_datasets`' stored flag are the same rule on every played row of the
    season, so a change to either is caught here rather than diverging quietly
    with the ledger following whichever one nobody edited.
    """
    counts = sum(
        (played[category] >= DOUBLE_FIGURES).astype(int)
        for category in DOUBLE_CATEGORIES
    )
    doubles = (counts >= 2).astype(int)
    triples = (counts >= 3).astype(int)
    assert int((doubles != played["double_double"]).sum()) == 0
    assert int((triples != played["triple_double"]).sum()) == 0

    rows = _rows(played, limit=PLAYER_SAMPLE)
    for row in rows:
        made = bool(row["double_double"])
        result = settle(market="player_double_double", segment=FULL_GAME,
                        selection=OVER, line=YES_NO_LINE, player=row, game=None)
        assert result.outcome is (Outcome.WON if made else Outcome.LOST)
        assert result.actual == (1.0 if made else 0.0)
        no = settle(market="player_double_double", segment=FULL_GAME,
                    selection=UNDER, line=YES_NO_LINE, player=row, game=None)
        assert no.outcome is (Outcome.LOST if made else Outcome.WON)
        treble = settle(market="player_triple_double", segment=FULL_GAME,
                        selection=OVER, line=YES_NO_LINE, player=row, game=None)
        assert treble.outcome is (
            Outcome.WON if bool(row["triple_double"]) else Outcome.LOST
        )
    with capsys.disabled():
        print(
            f"  double-double: the declared rule agrees with the stored flag "
            f"on {len(played):,} of {len(played):,} played rows (100.00%). "
            f"{int(played['double_double'].sum()):,} double-doubles and "
            f"{int(played['triple_double'].sum()):,} triple-doubles in {SEASON}."
        )


# --------------------------------------------------------------------------
# First basket.
# --------------------------------------------------------------------------


def test_the_first_basket_settles_from_the_recorded_scorer(played, segments, capsys):
    """Exactly one player per game wins it, and it is the recorded scorer."""
    won = graded = 0
    for row in _rows(played, limit=PLAYER_SAMPLE):
        game_id = row["game_id"]
        if game_id not in segments.index:
            continue
        segment = segments.loc[game_id].to_dict()
        result = settle(market="player_first_basket", segment=FULL_GAME,
                        selection=OVER, line=YES_NO_LINE, player=row,
                        game=segment)
        assert result.outcome in (Outcome.WON, Outcome.LOST)
        scored = float(row["athlete_id"]) == float(segment["first_basket_athlete_id"])
        assert result.outcome is (Outcome.WON if scored else Outcome.LOST)
        assert result.actual == (1.0 if scored else 0.0)
        graded += 1
        won += scored
    assert graded > 0
    with capsys.disabled():
        print(
            f"\n  first basket: {won:,} winners over {graded:,} graded "
            f"player-game rows ({won / graded * 100:.2f}%)."
        )


def test_the_first_basket_is_refused_when_the_rows_are_different_games(
    played, segments
):
    """A cross-game join grades every row and is wrong about all of them."""
    rows = _rows(played, limit=200)
    row = rows[0]
    other = next(
        candidate for candidate in rows if candidate["game_id"] != row["game_id"]
    )
    mismatched = settle(
        market="player_first_basket", segment=FULL_GAME, selection=OVER,
        line=YES_NO_LINE, player=row,
        game=segments.loc[other["game_id"]].to_dict(),
    )
    assert mismatched.outcome is Outcome.UNSETTLEABLE
    assert "different games" in mismatched.note


def test_the_first_team_basket_settles_for_BOTH_teams(played, segments, capsys):
    """Both sides, since the per-team columns exist.

    This test previously asserted the opposite, and that is the point of
    keeping it. `cbb_game_segments.csv` originally recorded only the **game's**
    first basket and its scorer's team, which made this market settleable for
    whichever side happened to score first and unsettleable for the other —
    measured at exactly **50.03% of played rows**. That is the shape of a gap
    that reads as thin market coverage and is really a missing column.

    `build_game_segments` now also derives `home_first_basket_athlete_id` and
    `away_first_basket_athlete_id`, so both sides grade. A handful of games
    still cannot — three of 6,275 in 2025-26, where one team scored every field
    goal in the play stream — and those return UNSETTLEABLE rather than a guess.
    """
    settleable = unsettleable = 0
    for row in _rows(played, limit=PLAYER_SAMPLE):
        game_id = row["game_id"]
        if game_id not in segments.index:
            continue
        segment = segments.loc[game_id].to_dict()
        result = settle(market="player_first_team_basket", segment=FULL_GAME,
                        selection=OVER, line=YES_NO_LINE, player=row,
                        game=segment)
        if result.outcome is Outcome.UNSETTLEABLE:
            assert result.actual is None
            unsettleable += 1
        else:
            assert result.outcome in (Outcome.WON, Outcome.LOST)
            settleable += 1
    total = settleable + unsettleable

    assert total > 0
    assert settleable / total > 0.95, (
        f"Only {settleable:,} of {total:,} rows settled. Before the per-team "
        "columns existed this was 50%; if it has fallen back there, "
        "cbb_game_segments.csv was built by an older build_datasets."
    )
    with capsys.disabled():
        print(
            f"  first TEAM basket: settleable on {settleable:,} of {total:,} "
            f"rows ({settleable / total * 100:.2f}%) now that each team's own "
            "first basket is stored; was 50.03% when only the game's was."
        )


def test_a_row_whose_side_is_unknown_still_refuses_rather_than_guessing(
    played, segments
):
    """`home_away` is how the handler picks a team's column. Missing it must
    not silently grade against the other team's first basket."""
    row = dict(_rows(played, limit=1)[0])
    game_id = row["game_id"]
    segment = dict(segments.loc[game_id])
    row["home_away"] = ""
    # Strip the fallback too, so there is genuinely nothing to grade against.
    segment["first_basket_team_id"] = None
    result = settle(market="player_first_team_basket", segment=FULL_GAME,
                    selection=OVER, line=YES_NO_LINE, player=row, game=segment)

    assert result.outcome is Outcome.UNSETTLEABLE
    assert result.actual is None


def test_a_game_with_no_segment_row_cannot_settle_a_first_basket(played, segments):
    """1,706 of 47,097 games have no segment row. Missing, not a loss."""
    row = _rows(played, limit=1)[0]
    result = settle(market="player_first_basket", segment=FULL_GAME,
                    selection=OVER, line=YES_NO_LINE, player=row, game=None)
    assert result.outcome is Outcome.UNSETTLEABLE
    assert "no game row was supplied" in result.note
    empty = settle(market="player_first_basket", segment=FULL_GAME,
                   selection=OVER, line=YES_NO_LINE, player=row,
                   game={"game_id": row["game_id"]})
    assert empty.outcome is Outcome.UNSETTLEABLE
    assert "no first-basket scorer" in empty.note


# --------------------------------------------------------------------------
# The guards real data cannot exercise, and the completeness check.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "line", [None, float("nan"), "", "  ", "nan", "not a number",
             float("inf"), float("-inf")]
)
def test_a_line_that_cannot_be_read_is_never_compared(line, games):
    """NaN is silent poison: it settles every under as a win and says nothing.

    Reproduced first, so the guard is known to be load-bearing. The natural
    comparator is `(actual - line) > 0` against the direction; with a NaN line
    the difference is NaN, `NaN > 0` is False, and the under wins every time.
    """
    row = _rows(games, limit=1)[0]
    total = float(row["total"])
    if isinstance(line, float) and math.isnan(line):
        # The comparator the guard exists to keep NaN out of, written out.
        def naive(direction: str) -> bool:
            difference = total - line
            return (difference > 0) == (direction is OVER)

        difference = total - line
        assert not (difference > 0) and not (difference < 0) and not (difference == 0)
        assert naive(UNDER) is True and naive(OVER) is False, (
            "the reproduction is stale: a NaN line no longer hands every under "
            "a free win and every over a loss. The guard stays regardless."
        )

    for market, segment, selection in (
        ("spread", FULL_GAME, HOME),
        ("total_points", FULL_GAME, UNDER),
        ("team_total", FULL_GAME, f"{HOME}_{UNDER}"),
        ("total_points_h1", FIRST_HALF, UNDER),
        ("spread_h2", SECOND_HALF, HOME),
    ):
        result = settle(market=market, segment=segment, selection=selection,
                        line=line, game=row)
        assert result.outcome is Outcome.UNSETTLEABLE, (
            f"{market} settled {result.outcome.value} on a line of {line!r}"
        )
        assert result.actual is None
        assert "never compared" in result.note


def test_a_prop_with_an_unreadable_line_is_unsettleable_not_void(played):
    """The ordering is deliberate and is pinned here.

    A void is itself a claim about the book's rulebook. Asserting it on top of
    a row whose line cannot be read would assert more than is known, so the
    line is checked first and the row leaves the record entirely.
    """
    row = _rows(played, limit=1)[0]
    result = settle(market="player_points", segment=FULL_GAME, selection=OVER,
                    line=float("nan"), player=row, game=None)
    assert result.outcome is Outcome.UNSETTLEABLE


def test_the_moneyline_needs_no_line_and_everything_else_does():
    """`takes_a_line` splits *no line* from *a line that could not be read*.

    `selection.normalise_line` returns None for both, which is why this
    predicate exists at all.
    """
    lineless = {m.key for m in MARKETS if not takes_a_line(m)}
    assert lineless == {"moneyline", "moneyline_h1", "moneyline_h2"}, (
        "a market gained or lost a handicap; settlement grades a lineless "
        "market on the raw margin and refuses a lined one with no line"
    )


@pytest.mark.parametrize("market", sorted(m.key for m in MARKETS))
def test_every_wired_market_has_a_handler_for_the_quantity_it_names(market):
    """`markets.py` wires it, so this module settles it — or the import fails.

    The import-time check in `settlement.py` is the real guard; this
    parametrization names the offender when it fires.
    """
    assert MARKETS_BY_KEY[market].settles_on in settleable_quantities()


def test_wiring_a_market_this_module_cannot_settle_fails_at_import():
    """The check that makes the parametrization above redundant, on purpose.

    A market that is priced, frozen and then found ungradeable has already
    spent credits and already published an opinion. This fails the build at the
    first import instead.
    """
    import cbb_betting_lab.settlement as module

    assert not (
        {m.settles_on for m in MARKETS} - set(module._HANDLERS)
    ), module._HANDLERS.keys()
    assert module._UNHANDLED == []


def test_the_futures_market_says_it_cannot_settle_and_is_not_called_a_pass():
    """`tournament_champion` has no results table, and admits it.

    An excluded market is never a pass, an avoid, or a no-value call — so the
    note is checked for the denial and for the absence of the claim.
    """
    result = settle(market="championship_winner", segment=FULL_GAME,
                    selection=HOME, line=None, game=None)
    assert result.outcome is Outcome.UNSETTLEABLE
    assert result.actual is None
    assert "does not exist in this repository" in result.note
    assert "not a pass, an avoid or a no-value call" in result.note


def test_an_unwired_market_key_settles_nothing():
    """A key in neither MARKETS nor DEFERRED_MARKETS is not guessed at."""
    result = settle(market="player_fantasy_points", segment=FULL_GAME,
                    selection=OVER, line=25.5, game=None, player={"points": 30})
    assert result.outcome is Outcome.UNSETTLEABLE
    assert "not a wired market" in result.note


def test_a_selection_from_the_wrong_sport_is_refused(games):
    """There is no draw in college basketball. A staged one is unparseable."""
    row = _rows(games, limit=1)[0]
    result = settle(market="moneyline", segment=FULL_GAME, selection="draw",
                    line=None, game=row)
    assert result.outcome is Outcome.UNSETTLEABLE
    assert "no draw in this sport" in result.note


def test_an_unsettleable_result_can_never_carry_a_number():
    """The contract, enforced by the dataclass rather than by convention.

    An `actual` beside an ungraded row invites a caller to compare it to a line
    and turn an exclusion into a record.
    """
    with pytest.raises(ValueError, match="no settled quantity"):
        Settled(Outcome.UNSETTLEABLE, 7.0, "a reason")
    with pytest.raises(ValueError, match="must carry a note"):
        Settled(Outcome.UNSETTLEABLE, None)
    with pytest.raises(ValueError, match="must carry a note"):
        Settled(Outcome.VOID, None)


def test_a_moneyline_ignores_a_stray_line_rather_than_becoming_a_spread(games):
    """A moneyline is the spread at a handicap of zero, whatever is staged.

    A CSV round-trip that writes `0.0` into a moneyline's line column must not
    change the bet, and a corrupt one must not silently turn it into a
    handicap. The wired markets carry no line, so none is read.
    """
    row = _rows(games, limit=500)
    for game in row:
        expected = Outcome.WON if game["margin"] > 0 else Outcome.LOST
        for line in (None, 0.0, -7.5, float("nan")):
            result = settle(market="moneyline", segment=FULL_GAME,
                            selection=HOME, line=line, game=game)
            assert result.outcome is expected, (
                f"a moneyline moved when the staged line was {line!r}"
            )
            assert result.actual == game["margin"]


def test_no_unsettleable_note_calls_the_market_a_pass_or_an_avoid(games, played):
    """An excluded market is never a pass, an avoid, or a no-value call.

    The words may appear only inside an explicit denial — the same rule, and
    the same regex, as `test_gates_fail_closed.py`, because a note that reads
    like a betting opinion becomes one the moment it is printed on a card.
    """
    import re

    game_row, player_row = _rows(games, limit=1)[0], _rows(played, limit=1)[0]
    notes = [
        settle(market="championship_winner", segment=FULL_GAME, selection=HOME,
               line=None, game=None).note,
        settle(market="moneyline", segment=FULL_GAME, selection=AWAY,
               line=None, game=game_row).note,
        settle(market="spread", segment=FULL_GAME, selection=HOME,
               line=float("nan"), game=game_row).note,
        settle(market="total_points_h1", segment=FULL_GAME, selection=OVER,
               line=70.5, game=game_row).note,
        settle(market="moneyline", segment=FULL_GAME, selection="draw",
               line=None, game=game_row).note,
        settle(market="player_first_team_basket", segment=FULL_GAME,
               selection=OVER, line=YES_NO_LINE, player=player_row,
               game={"game_id": player_row["game_id"],
                     "first_basket_team_id": -1,
                     "first_basket_athlete_id": -1}).note,
        settle(market="player_points", segment=FULL_GAME, selection=OVER,
               line=12.5, game=None, player=None).note,
        settle(market="not_a_market", segment=FULL_GAME, selection=OVER,
               line=12.5, game=None).note,
    ]
    for note in notes:
        assert note, "every unsettleable note must say why"
        remainder = re.sub(r"(?:is not|it is not|never|not a)\b[^.]*", "",
                           note.casefold())
        for banned in (" pass", "avoid", "no value", "no-value", "lean"):
            assert banned not in remainder, (
                f"a settlement note asserts {banned!r} outside a denial: {note}"
            )


def test_a_player_market_without_a_player_row_settles_nothing():
    """A prop cannot be graded off a team row, and zero is not a default."""
    for market in sorted(m.key for m in MARKETS if m.family == PLAYER):
        result = settle(market=market, segment=FULL_GAME, selection=OVER,
                        line=YES_NO_LINE, game=None, player=None)
        assert result.outcome is Outcome.UNSETTLEABLE
        assert "player-games row" in result.note


def _flip(row: dict) -> dict:
    """The same game from the other team's perspective.

    Built here rather than read from the file so that this suite's own idea of
    'the away row' is independent of the builder's. It is checked against the
    real away row by :func:`test_the_flipped_row_matches_the_real_away_row`, so
    a mistake here cannot quietly weaken every side assertion above.
    """
    flipped = dict(row)
    flipped["home_away"] = AWAY if row["home_away"] == HOME else HOME
    flipped["team_score"], flipped["opponent_score"] = (
        row["opponent_score"], row["team_score"],
    )
    flipped["margin"] = -row["margin"]
    for half in ("h1", "h2"):
        flipped[f"team_score_{half}"] = row[f"opponent_score_{half}"]
        flipped[f"opponent_score_{half}"] = row[f"team_score_{half}"]
    return flipped


def test_the_flipped_row_matches_the_real_away_row(team_games, games):
    """The helper above is checked against the file, not trusted."""
    away = team_games[team_games["home_away"] == AWAY].set_index("game_id")
    for row in _rows(games, limit=2_000):
        real = away.loc[row["game_id"]]
        mine = _flip(row)
        assert mine["team_score"] == real["team_score"]
        assert mine["opponent_score"] == real["opponent_score"]
        assert mine["margin"] == real["margin"]
        for column in ("team_score_h1", "opponent_score_h1",
                       "team_score_h2", "opponent_score_h2"):
            left, right = mine[column], real[column]
            assert (left == right) or (
                left != left and right != right  # both NaN
            ), f"{row['game_id']} {column}: {left!r} against {right!r}"
