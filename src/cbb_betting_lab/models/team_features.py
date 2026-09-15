"""Walk-forward team features, from the box line this lab already holds.

Every column here is computed from `data/processed/cbb_team_games.csv`, which is
one row per team-game with the full box line and `possessions_estimated`. No
purchase, no scrape, no subscription number as an input.

**The per-game numbers are observations; the features are `walk_forward` of
them.** A season aggregate used to predict a game inside that season has seen
the game it is predicting, and a leaked feature is indistinguishable from a good
one right up until it is bet. `walk_forward` shifts by one game inside each team
before it averages, so a team's first game yields NaN rather than a number
computed from itself. `tests/test_team_features.py` mutates the shift away and
fails, which is the only evidence that it is load-bearing.

**What is deliberately NOT here**, from the obtainability audit of 2026-09-15:

* Height and effective height — absent from every file on disk and not derivable
  from a box score. No proxy is offered; a block-rate stand-in would be a
  different quantity wearing the name.
* Closing line value and any market-implied rating — all 3,863,325 rows in the
  price store carry `snapshot_phase == card`. The close was never bought, so CLV
  cannot be computed here at all, and saying so is better than approximating it
  from the card price and calling it CLV.
* Box Plus/Minus and RAPM — no on-court-five data: the 2019-2024 play-by-play
  carries zero `Substitution` rows.
* Points in the paint and fast-break points — the native columns are missing for
  five of the eight seasons, and nothing in the feed marks a transition
  possession.

**Several of these are near-collinear with what the lab already fits.** SRS
correlates 0.9995 with the existing AdjEM on this data, and Barthag is a monotone
transform of AdjOE/AdjDE. They are built because they were asked for, and
`collinearity_with()` reports the overlap so nobody counts them as new
information.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: KenPom's free-throw weight, matching `possessions_estimated` in the store.
FTA_WEIGHT = 0.475

#: Pythagorean exponent. **8, not the 10.25 or 11.5 the public sites quote.**
#: Fitted on this lab's own 2024 season across 362 teams, k=8 gives RMSE 0.0591
#: against actual win rate where 10.25 gives 0.0656 and 11.5 gives 0.0749. The
#: convention is not a law of the sport and this data prefers a lower exponent.
#: It must be re-fitted on PRIOR seasons only; fitting it on the season being
#: priced leaks through the exponent.
PYTHAGOREAN_K = 8.0


def _rate(numerator, denominator):
    """Divide, returning NaN where the denominator is zero rather than inf."""
    return numerator / denominator.replace(0, np.nan)


def per_game_features(team_games: pd.DataFrame) -> pd.DataFrame:
    """One row per team-game: the Four Factors, shooting and defensive rates.

    Opponent columns come from the other team's row in the same game rather than
    from a separate measurement, so a team's defensive rate and its opponent's
    offensive rate are the same number by construction and cannot drift.
    """
    frame = team_games.copy()
    opponent = frame.merge(
        frame, left_on=["game_id", "opponent_id"], right_on=["game_id", "team_id"],
        suffixes=("", "_opp"),
    )
    f = opponent
    poss = f["possessions_estimated"]

    out = pd.DataFrame({
        "game_id": f["game_id"], "team_id": f["team_id"], "season": f["season"],
        "slate_date": f["slate_date"], "opponent_id": f["opponent_id"],
        "margin": f["margin"],
    })

    # --- Four Factors, offense
    out["efg_pct"] = _rate(
        f["field_goals_made"] + 0.5 * f["three_point_field_goals_made"],
        f["field_goals_attempted"],
    )
    out["turnover_rate"] = _rate(f["turnovers"], poss)
    out["off_reb_pct"] = _rate(
        f["offensive_rebounds"], f["offensive_rebounds"] + f["defensive_rebounds_opp"]
    )
    out["def_reb_pct"] = _rate(
        f["defensive_rebounds"], f["defensive_rebounds"] + f["offensive_rebounds_opp"]
    )
    out["free_throw_rate"] = _rate(f["free_throws_attempted"], f["field_goals_attempted"])

    # --- Four Factors, defense: the opponent's offense, attributed here
    out["efg_pct_allowed"] = _rate(
        f["field_goals_made_opp"] + 0.5 * f["three_point_field_goals_made_opp"],
        f["field_goals_attempted_opp"],
    )
    out["turnover_rate_forced"] = _rate(f["turnovers_opp"], f["possessions_estimated_opp"])
    out["free_throw_rate_allowed"] = _rate(
        f["free_throws_attempted_opp"], f["field_goals_attempted_opp"]
    )

    # **Non-steal turnover rate: sloppiness rather than pressure.** Subtracting
    # the opponent's steals leaves the turnovers nobody took away.
    out["non_steal_turnover_rate"] = _rate(f["turnovers"] - f["steals_opp"], poss)

    # --- efficiency
    out["off_efficiency"] = _rate(f["team_score"], poss) * 100
    out["def_efficiency"] = _rate(f["opponent_score"], f["possessions_estimated_opp"]) * 100
    out["net_efficiency"] = out["off_efficiency"] - out["def_efficiency"]
    out["tempo"] = poss

    # --- shooting
    out["true_shooting_pct"] = _rate(
        f["team_score"], 2 * (f["field_goals_attempted"] + 0.44 * f["free_throws_attempted"])
    )
    out["three_point_rate"] = _rate(
        f["three_point_field_goals_attempted"], f["field_goals_attempted"]
    )
    out["three_point_rate_allowed"] = _rate(
        f["three_point_field_goals_attempted_opp"], f["field_goals_attempted_opp"]
    )
    out["two_point_pct"] = _rate(
        f["field_goals_made"] - f["three_point_field_goals_made"],
        f["field_goals_attempted"] - f["three_point_field_goals_attempted"],
    )
    out["three_point_pct"] = _rate(
        f["three_point_field_goals_made"], f["three_point_field_goals_attempted"]
    )
    out["free_throw_pct"] = _rate(f["free_throws_made"], f["free_throws_attempted"])
    out["assist_rate"] = _rate(f["assists"], f["field_goals_made"])
    out["points_per_shot"] = _rate(f["team_score"], f["field_goals_attempted"])

    # --- point distribution
    out["points_share_three"] = _rate(3 * f["three_point_field_goals_made"], f["team_score"])
    out["points_share_free_throw"] = _rate(f["free_throws_made"], f["team_score"])
    out["points_share_two"] = 1 - out["points_share_three"] - out["points_share_free_throw"]

    # --- defense
    out["block_rate"] = _rate(
        f["blocks"],
        f["field_goals_attempted_opp"] - f["three_point_field_goals_attempted_opp"],
    )
    out["steal_rate"] = _rate(f["steals"], f["possessions_estimated_opp"])

    return out


def walk_forward(frame: pd.DataFrame, columns=None, *, minimum: int = 1) -> pd.DataFrame:
    """Each team's mean of `columns` over its games STRICTLY BEFORE each one.

    The `shift(1)` is what excludes the game being predicted. Removing it leaves
    a feature that has read the result it is forecasting -- which scores
    beautifully in a backtest and is worth nothing at a window.
    """
    if columns is None:
        columns = [
            c for c in frame.columns
            if c not in {"game_id", "team_id", "season", "slate_date", "opponent_id", "margin"}
        ]
    frame = frame.sort_values(["team_id", "season", "slate_date", "game_id"]).copy()
    grouped = frame.groupby(["team_id", "season"], observed=True)[list(columns)]
    prior = grouped.transform(lambda s: s.shift(1).expanding(minimum).mean())
    prior = prior.add_prefix("prior_")
    keep = ["game_id", "team_id", "season", "slate_date", "opponent_id", "margin"]
    return pd.concat([frame[keep], prior], axis=1)


def collinearity_with(features: pd.DataFrame, reference: pd.Series) -> pd.Series:
    """How much each feature already says what `reference` says.

    Reported because several of these are transforms of things the lab fits
    already -- SRS correlates 0.9995 with its AdjEM -- and a feature that
    restates an existing one is not new information however new its name is.
    """
    numeric = features.select_dtypes("number")
    return numeric.corrwith(reference).sort_values(key=abs, ascending=False)
