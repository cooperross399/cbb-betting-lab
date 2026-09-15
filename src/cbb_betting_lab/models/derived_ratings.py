"""Sequential team ratings: Elo, SRS, Pythagorean, Luck, Strength of Schedule.

These differ from `team_features` in one way that matters: they are not averages
of per-game numbers, they are computed ACROSS games. That makes the leakage
question sharper rather than softer — an iterated rating fitted on a whole season
has read every result in it, including the game you are predicting.

So every function here takes a cut-off and uses only games strictly before it.
`elo_series` is the exception and needs none, because Elo is sequential by
construction: a team's rating before game *n* is built from games 1..n-1 and
nothing later can reach it.

**Two numbers in here disagree with the published convention, and the data is
why:**

* `PYTHAGOREAN_K = 8.0`. The sites quote 10.25 (Pomeroy) or 11.5 (Torvik). On
  this lab's 2024 season across 362 teams, k=8 gives RMSE 0.0591 against actual
  win rate where 10.25 gives 0.0656 and 11.5 gives 0.0749. The exponent is a
  fitted convention, not a law, and it must be fitted on PRIOR seasons only —
  fitting it on the season being priced leaks through the exponent itself.
* SRS correlates **0.9995** with the adjusted efficiency margin this lab already
  fits. It is built because it was asked for; it is very close to a tempo-free
  rescaling of a rating the model already has, and `derived_collinearity` says so
  rather than letting it be counted as a new signal.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Fitted on this lab's data, not taken from the publishing sites. See above.
PYTHAGOREAN_K = 8.0

#: Elo's update size. 20 is the common college-basketball choice; the rating is
#: only used as a feature, so its scale matters less than its ordering.
ELO_K = 20.0

#: Points of home advantage in the Elo expectation, in rating units.
ELO_HOME_EDGE = 65.0

#: Every team starts a season here, carrying nothing from the last one. Carrying
#: a prior season's rating forward is defensible and is NOT done, because it
#: would make the first weeks of a season depend on a choice nobody has tested.
ELO_START = 1500.0


def elo_series(team_games: pd.DataFrame, *, k: float = ELO_K) -> pd.DataFrame:
    """Each team's Elo BEFORE each of its games, and the update after.

    Sequential by construction, so the returned `elo_before` is always a
    prediction-time quantity: nothing after the game can reach it. That is worth
    stating because it is the only rating here that needs no cut-off argument,
    and someone will otherwise add one for symmetry and break it.
    """
    frame = team_games[team_games["game_state"] == COUNTABLE].sort_values(
        ["season", "slate_date", "game_id"]
    ).copy()
    ratings: dict[tuple, float] = {}
    before, after = [], []

    for row in frame.itertuples():
        key = (row.season, row.team_id)
        opponent = (row.season, row.opponent_id)
        rating = ratings.setdefault(key, ELO_START)
        opposing = ratings.setdefault(opponent, ELO_START)

        edge = 0.0 if getattr(row, "neutral_site", False) else (
            ELO_HOME_EDGE if str(getattr(row, "home_away", "")).lower() == "home"
            else -ELO_HOME_EDGE
        )
        expected = 1.0 / (1.0 + 10 ** (-(rating + edge - opposing) / 400.0))
        won = 1.0 if row.margin > 0 else 0.0
        updated = rating + k * (won - expected)

        before.append(rating)
        after.append(updated)
        ratings[key] = updated

    frame["elo_before"] = before
    frame["elo_after"] = after
    return frame[["game_id", "team_id", "season", "slate_date", "elo_before", "elo_after"]]


#: The lab's own marker for a game that counts. The alternative value is
#: `non_di_opponent`.
COUNTABLE = "countable"


def _prior_games(team_games: pd.DataFrame, season: int, before) -> pd.DataFrame:
    """Countable games in `season` strictly before `before`.

    **`game_state == "countable"` is not optional and filtering on it is not a
    nicety.** Without it the frame carries 700 "teams" in 2025 where 365 are
    Division I: the rest are non-D1 opponents that appear only through their
    games AGAINST D1 sides, which they mostly lose. Their record in this table
    is an artefact of which games were collected, not of how they played.

    Measured with them in: mean Pythagorean expectation 0.320 where it must be
    0.5 by symmetry, mean Luck -0.034 where it must be 0, mean Strength of
    Schedule +16.9 where it must be 0, and an SRS spread of 26.1 against the
    10.4 this sport produces. Every one of those is a rating computed over a
    population that does not exist.
    """
    if "game_state" not in team_games:
        raise ValueError(
            "the team-game table has no `game_state` column, so countable games "
            "cannot be separated from non-D1 opponents. Every rating below would "
            "be computed over a population that includes teams whose record here "
            "is an artefact of collection."
        )
    return team_games[
        (team_games["season"] == season)
        & (team_games["slate_date"] < before)
        & (team_games["game_state"] == COUNTABLE)
    ]


def pythagorean(team_games: pd.DataFrame, season: int, before, *, k: float = PYTHAGOREAN_K):
    """Expected win rate from points scored and allowed, before `before`.

    Cast to float before exponentiating: season point totals are int64 and
    `total ** 8` overflows silently, producing negative expectations.
    """
    played = _prior_games(team_games, season, before)
    if played.empty:
        return pd.Series(dtype="float64")
    grouped = played.groupby("team_id", observed=True)
    scored = grouped["team_score"].sum().astype("float64")
    allowed = grouped["opponent_score"].sum().astype("float64")
    return (scored**k) / (scored**k + allowed**k)


def luck(team_games: pd.DataFrame, season: int, before, *, k: float = PYTHAGOREAN_K):
    """Actual win rate minus the Pythagorean expectation, before `before`.

    The betting premise is mean reversion, so this is only meaningful measured on
    a strictly earlier window and tested against what happens NEXT. Computed over
    a whole season it embeds the outcomes of the games it would be used to
    predict, twice over.
    """
    played = _prior_games(team_games, season, before)
    if played.empty:
        return pd.Series(dtype="float64")
    actual = played.assign(won=played["margin"] > 0).groupby("team_id", observed=True)["won"].mean()
    return (actual - pythagorean(team_games, season, before, k=k)).dropna()


def simple_rating_system(
    team_games: pd.DataFrame, season: int, before, *, sweeps: int = 200, tolerance: float = 1e-9
):
    """Margin of victory plus strength of schedule, iterated to a fixed point.

    Re-centred to mean zero each sweep, which is what makes the fixed point
    unique — without it the whole vector drifts by a constant and "converged"
    means nothing.
    """
    played = _prior_games(team_games, season, before)
    if played.empty:
        return pd.Series(dtype="float64")
    margin = played.groupby("team_id", observed=True)["margin"].mean()
    rating = margin.copy()
    for _ in range(sweeps):
        opponent_strength = (
            played.assign(value=played["opponent_id"].map(rating))
            .groupby("team_id", observed=True)["value"]
            .mean()
        )
        updated = margin + opponent_strength.reindex(margin.index).fillna(0.0)
        updated = updated - updated.mean()
        if float((updated - rating).abs().max()) < tolerance:
            return updated
        rating = updated
    return rating


def strength_of_schedule(team_games: pd.DataFrame, season: int, before, rating: pd.Series):
    """Mean rating of the opponents a team has already played.

    Takes the rating as an argument rather than computing one, so the caller
    decides which rating and — more to the point — as of when. A SOS built from
    end-of-season ratings is leakage even when the schedule itself is known in
    advance: the games are public, the opponents' strength is not.
    """
    played = _prior_games(team_games, season, before)
    if played.empty:
        return pd.Series(dtype="float64")
    return (
        played.assign(value=played["opponent_id"].map(rating))
        .groupby("team_id", observed=True)["value"]
        .mean()
    )


def derived_collinearity(ratings: pd.DataFrame, reference: pd.Series) -> pd.Series:
    """How much each rating restates `reference`. See the module docstring."""
    return ratings.select_dtypes("number").corrwith(reference).sort_values(key=abs, ascending=False)
