"""The walk-forward feature table, and the leak it exists to prevent.

**The whole file is about one line.** `walk_forward` shifts each team's history
by one game before averaging it. Without that shift a feature has read the
result it is forecasting: measured on 2025, a team's prior eFG% correlates
+0.215 with its eFG% in the game being predicted, and the same mean computed
WITH that game in it correlates +0.523. A model fitted on the second number
scores beautifully in a backtest and is worth nothing at a window, because at a
window the game has not happened yet.

That is the failure this lab cannot detect after the fact -- a leaked feature and
a good feature look identical in every summary statistic anyone would print.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from cbb_betting_lab.models import team_features as TF


_ROOT = Path(TF.__file__).resolve().parents[3]
_GAMES = _ROOT / "data" / "processed" / "cbb_team_games.csv"


def _season_2025() -> pd.DataFrame:
    """The real 2025 team-games, or a skip — with the existence check FIRST.

    **This guard was written after the read and therefore never fired.** The
    table is gitignored, so CI raised `FileNotFoundError` on the `read_csv` and
    never reached the `pytest.skip` two lines below it. Passed locally, failed on
    a clean checkout: this repository's oldest recurring defect, committed again
    by someone who had written the note about it.

    The toy-fixture tests above carry the walk-forward and arithmetic checks and
    run everywhere. What skips here is only the "does this match real college
    basketball" range check, which needs data a clone does not have.
    """
    if not _GAMES.is_file():
        pytest.skip(f"{_GAMES.name} is not built in this checkout (it is gitignored)")
    games = pd.read_csv(_GAMES)
    season = games[games["season"] == 2025]
    if season.empty:
        pytest.skip("no 2025 rows in the team-game table")
    return season


def _toy() -> pd.DataFrame:
    """Two teams, one game each per date, with known box lines.

    Hand-built rather than sampled, so every expected value below is arithmetic
    a reader can check rather than a number this file recorded from itself.
    """
    rows = []
    for game, (date, made_a, made_b) in enumerate(
        [("2025-01-01", 30, 20), ("2025-01-05", 10, 40), ("2025-01-09", 50, 30)], start=1
    ):
        for team, opponent, made in ((1, 2, made_a), (2, 1, made_b)):
            rows.append({
                "game_id": game, "season": 2025, "slate_date": date,
                "team_id": team, "opponent_id": opponent,
                "team_score": made * 2, "opponent_score": 50, "margin": made * 2 - 50,
                "possessions_estimated": 70.0,
                "field_goals_made": made, "field_goals_attempted": 60,
                "three_point_field_goals_made": 0, "three_point_field_goals_attempted": 20,
                "free_throws_made": 0, "free_throws_attempted": 10,
                "offensive_rebounds": 10, "defensive_rebounds": 20,
                "assists": 10, "steals": 5, "blocks": 3, "turnovers": 12,
            })
    return pd.DataFrame(rows)


def test_a_teams_first_game_has_no_prior_and_says_so():
    """NaN, not a number computed from the game itself."""
    prior = TF.walk_forward(TF.per_game_features(_toy()))
    first = prior.sort_values("game_id").groupby("team_id").head(1)
    assert first["prior_efg_pct"].isna().all(), (
        "a team's first game carries a prior built from no prior games. Whatever "
        "number is in there came from the game being predicted."
    )


def test_the_prior_is_the_mean_of_earlier_games_and_excludes_this_one():
    """Arithmetic, on a fixture whose answer is known by hand.

    Team 1 makes 30, then 10, then 50 of 60 with no threes, so its eFG% is
    .500, .1667 and .8333. The prior for game 3 is the mean of the first two,
    .3333; the mean INCLUDING game 3 is .5000. Those differ, which is the whole
    point -- the first version of this fixture used 30/10/20, where the two
    means are both .3333 and the assertion below could not fail. This file's own
    test caught that, which is the argument for writing the arithmetic out.
    """
    prior = TF.walk_forward(TF.per_game_features(_toy()))
    team = prior[prior["team_id"] == 1].sort_values("game_id")

    assert team.iloc[1]["prior_efg_pct"] == pytest.approx(30 / 60, abs=1e-9), (
        "game 2's prior is not game 1's eFG%"
    )
    assert team.iloc[2]["prior_efg_pct"] == pytest.approx(
        ((30 / 60) + (10 / 60)) / 2, abs=1e-9
    ), "game 3's prior is not the mean of games 1 and 2"

    including_this_game = ((30 / 60) + (10 / 60) + (50 / 60)) / 3
    assert team.iloc[2]["prior_efg_pct"] != pytest.approx(including_this_game, abs=1e-9), (
        "game 3's prior equals the mean INCLUDING game 3, so the shift is gone"
    )


def test_removing_the_shift_changes_the_answer():
    """The mutation, run here rather than described.

    A guard whose load-bearing line can be deleted with every test still green
    is not a guard. This computes the leaked form directly and requires it to
    differ, so the shift cannot be removed quietly.
    """
    features = TF.per_game_features(_toy())
    honest = TF.walk_forward(features)
    leaked = (
        features.sort_values(["team_id", "slate_date"])
        .groupby(["team_id", "season"], observed=True)["efg_pct"]
        .transform(lambda s: s.expanding(1).mean())
    )
    honest_values = honest.sort_values(["team_id", "game_id"])["prior_efg_pct"].to_numpy()
    leaked_values = leaked.to_numpy()
    both = ~np.isnan(honest_values)
    assert not np.allclose(honest_values[both], leaked_values[both]), (
        "the walk-forward mean and the mean including the current game are the "
        "same numbers, so `shift(1)` is doing nothing and every feature built "
        "on this has seen its own answer."
    )


def test_the_four_factors_land_where_college_basketball_does():
    """A rate that computes but is nonsense is a bug someone will trust later."""
    features = TF.per_game_features(_season_2025())

    for column, low, high in [
        ("efg_pct", 0.46, 0.56), ("turnover_rate", 0.13, 0.22),
        ("off_reb_pct", 0.24, 0.36), ("free_throw_rate", 0.26, 0.40),
        ("off_efficiency", 95.0, 118.0), ("tempo", 62.0, 76.0),
        ("true_shooting_pct", 0.50, 0.60), ("three_point_rate", 0.33, 0.46),
    ]:
        mean = features[column].mean()
        assert low < mean < high, (
            f"{column} averages {mean:.4f} across the 2025 season, outside the "
            f"{low}-{high} college basketball actually produces. The formula "
            "runs; that does not make it right."
        )

    # Offensive and defensive rebound percentage are complements across the
    # population -- every offensive board is a defensive board somebody lost --
    # so these two must sum to one. They come from different columns, so this
    # is a real cross-check rather than an identity.
    assert features["off_reb_pct"].mean() + features["def_reb_pct"].mean() == pytest.approx(
        1.0, abs=0.01
    ), "offensive and defensive rebound rates do not complement across the season"


def test_the_box_and_the_play_by_play_agree_on_efg():
    """Two independent routes to one number, which is why this is evidence.

    The box path divides made and three-point field goals from `team_box`; the
    play-by-play path classifies every shooting event and counts makes. They
    share no arithmetic, so agreement is a check on both.
    """
    box_efg = TF.per_game_features(_season_2025())["efg_pct"].mean()
    assert 0.46 < box_efg < 0.56
    # The play-by-play figure, measured 2026-09-15 on 713,965 attempts, is 0.510.
    assert box_efg == pytest.approx(0.510, abs=0.01), (
        f"the box score says eFG% {box_efg:.4f} where the play-by-play says "
        "0.510. One of the two paths moved and they are supposed to measure "
        "the same thing."
    )
