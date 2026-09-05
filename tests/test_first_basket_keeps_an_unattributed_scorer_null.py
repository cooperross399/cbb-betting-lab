"""The first basket's scorer is read by position, never by "first non-null".

Reproduced before it was fixed. `build_game_segments` derived the game's first
basket with `made.groupby("game_id").first()`, and pandas' `GroupBy.first()`
returns **the first non-null value per column**. So when the first made field
goal carries no athlete — an unattributed play in the feed — the scorer column
is quietly filled from the **next** made basket: a real player, a plausible
name, and a wrong `player_first_basket` settlement that nothing flags, because
the row looks exactly like every other row.

Measured on the 2025-26 play-by-play before the fix: 3 of 6,275 games had the
game's first basket attributed to the second scorer this way, and 8 of 12,552
team-games had a team's. Small, and every one of them a graded bet on the wrong
player. The rule this file pins is that a first basket nobody is recorded as
scoring stays **null**, and both first-basket markets on that game are
`UNSETTLEABLE` rather than attributed.
"""

from __future__ import annotations

import pandas as pd

from cbb_betting_lab.data import hoopr
from cbb_betting_lab.data.build_datasets import build_game_segments, is_made_field_goal
from cbb_betting_lab.selection import FULL_GAME, OVER, YES_NO_LINE
from cbb_betting_lab.settlement import Outcome, settle

SEASON = 2026
HOME, AWAY = 10, 20
UNATTRIBUTED_GAME = 7001
ATTRIBUTED_GAME = 7002


def _play(game_id, number, *, type_text, scoring, value, athlete, team, period=1):
    return {
        "game_id": game_id,
        "period_number": period,
        "home_score": 0,
        "away_score": 0,
        "game_play_number": number,
        "scoring_play": scoring,
        "score_value": value,
        "type_text": type_text,
        "athlete_id_1": athlete,
        "team_id": team,
        "home_team_id": HOME,
        "away_team_id": AWAY,
    }


def _plays() -> pd.DataFrame:
    """Two games. One opens with an unattributed basket, the other does not.

    The rows are deliberately written **out of play order**, so a pick that
    followed file order instead of `game_play_number` would also fail here.
    """
    rows = [
        # ---- game 7001: the first BASKET has no athlete ----------------------
        # play 2: a made free throw, attributed. Not a basket, and if the free
        # throw filter ever regressed this would become the "first basket".
        _play(UNATTRIBUTED_GAME, 2, type_text="MadeFreeThrow", scoring=True,
              value=1, athlete=999, team=HOME),
        # play 5: the away team's first basket, attributed. This is the row
        # `first()` steals the scorer from.
        _play(UNATTRIBUTED_GAME, 5, type_text="JumpShot", scoring=True,
              value=3, athlete=200, team=AWAY),
        # play 3: the game's first made field goal. Home team, NO athlete.
        _play(UNATTRIBUTED_GAME, 3, type_text="LayUpShot", scoring=True,
              value=2, athlete=None, team=HOME),
        # play 4: a missed shot; score_value is 2 anyway.
        _play(UNATTRIBUTED_GAME, 4, type_text="JumpShot", scoring=False,
              value=2, athlete=100, team=HOME),
        # play 7: the home team's first ATTRIBUTED basket, which is not its
        # first basket.
        _play(UNATTRIBUTED_GAME, 7, type_text="DunkShot", scoring=True,
              value=2, athlete=100, team=HOME),
        _play(UNATTRIBUTED_GAME, 9, type_text="JumpShot", scoring=True,
              value=2, athlete=100, team=HOME, period=2),
        # ---- game 7002: fully attributed ---------------------------------
        _play(ATTRIBUTED_GAME, 4, type_text="JumpShot", scoring=True,
              value=2, athlete=400, team=AWAY),
        _play(ATTRIBUTED_GAME, 2, type_text="LayUpShot", scoring=True,
              value=2, athlete=300, team=HOME),
        _play(ATTRIBUTED_GAME, 6, type_text="JumpShot", scoring=True,
              value=2, athlete=300, team=HOME, period=2),
    ]
    frame = pd.DataFrame(rows)
    frame["athlete_id_1"] = frame["athlete_id_1"].astype("Float64")
    return frame


def _segments(tmp_path) -> pd.DataFrame:
    path = hoopr.FEEDS["pbp"].path(SEASON, tmp_path)
    path.parent.mkdir(parents=True)
    _plays().to_parquet(path, index=False)
    return build_game_segments(SEASON, raw_dir=tmp_path).set_index("game_id")


def _is_null(value) -> bool:
    return value is None or (isinstance(value, float) and pd.isna(value)) or pd.isna(value)


def test_the_defect_is_real_first_returns_the_first_non_null_not_the_first_row():
    """Reproduce it, so the positional pick below is known to be load-bearing."""
    made = _plays().sort_values(["game_id", "game_play_number"], kind="mergesort")
    made = made[is_made_field_goal(made)]
    stolen = made.groupby("game_id").first().loc[UNATTRIBUTED_GAME, "athlete_id_1"]
    assert stolen == 200, (
        "pandas GroupBy.first() no longer skips nulls; the reproduction is stale "
        "but the positional rule below must still hold."
    )
    kept = made.groupby("game_id").head(1).set_index("game_id").loc[
        UNATTRIBUTED_GAME, "athlete_id_1"
    ]
    assert _is_null(kept)


def test_an_unattributed_first_basket_stays_null_and_is_never_the_second_scorer(tmp_path):
    segments = _segments(tmp_path)
    row = segments.loc[UNATTRIBUTED_GAME]
    assert _is_null(row["first_basket_athlete_id"]), (
        f"the game's first basket was attributed to {row['first_basket_athlete_id']!r}; "
        "nobody is recorded as scoring it"
    )
    # The team IS known — the play carries one — and is kept. Only the scorer
    # is unknown, and only the scorer is null.
    assert row["first_basket_team_id"] == HOME
    # The home team's first basket is that same unattributed play, so its
    # scorer is null too; the away team's is fully attributed and is kept.
    assert _is_null(row["home_first_basket_athlete_id"])
    assert row["away_first_basket_athlete_id"] == 200


def test_a_fully_attributed_first_basket_is_unchanged(tmp_path):
    row = _segments(tmp_path).loc[ATTRIBUTED_GAME]
    assert row["first_basket_athlete_id"] == 300
    assert row["first_basket_team_id"] == HOME
    assert row["home_first_basket_athlete_id"] == 300
    assert row["away_first_basket_athlete_id"] == 400
    assert row["periods"] == 2 and not bool(row["overtime"])


def test_a_made_free_throw_before_the_unattributed_basket_is_still_not_a_basket(tmp_path):
    """`is_made_field_goal` is untouched: the free throw at play 2 never wins."""
    segments = _segments(tmp_path)
    assert (segments["first_basket_athlete_id"] != 999).all()
    assert (segments["home_first_basket_athlete_id"] != 999).all()


def test_both_first_basket_markets_are_unsettleable_on_that_game_not_attributed(tmp_path):
    """End to end: through a CSV round trip, the way the backtest reads it."""
    segments = _segments(tmp_path).reset_index()
    csv = tmp_path / "cbb_game_segments.csv"
    segments.to_csv(csv, index=False)
    game = pd.read_csv(csv).set_index("game_id").loc[UNATTRIBUTED_GAME].to_dict()
    game["game_id"] = UNATTRIBUTED_GAME

    def player(athlete, team, side):
        return {"game_id": UNATTRIBUTED_GAME, "athlete_id": athlete, "team_id": team,
                "home_away": side, "did_not_play": False}

    away_scorer = player(200, AWAY, "away")
    home_scorer = player(100, HOME, "home")

    # The away player scored the SECOND basket. `first()` would have graded
    # this WON; it is unknown.
    for who in (away_scorer, home_scorer):
        result = settle(market="player_first_basket", segment=FULL_GAME,
                        selection=OVER, line=YES_NO_LINE, player=who, game=game)
        assert result.outcome is Outcome.UNSETTLEABLE, result
        assert result.actual is None
        assert "no first-basket scorer is recorded" in result.note

    # The home team's own first basket is the unattributed one: unsettleable.
    home_team = settle(market="player_first_team_basket", segment=FULL_GAME,
                       selection=OVER, line=YES_NO_LINE, player=home_scorer,
                       game=game)
    assert home_team.outcome is Outcome.UNSETTLEABLE, home_team
    # The away team's own first basket IS attributed, and it is this player's.
    away_team = settle(market="player_first_team_basket", segment=FULL_GAME,
                       selection=OVER, line=YES_NO_LINE, player=away_scorer,
                       game=game)
    assert away_team.outcome is Outcome.WON, away_team
