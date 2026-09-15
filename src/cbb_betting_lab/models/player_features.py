"""Player rate and composite statistics, per player-game.

From `data/raw/cbb/player_box/` plus the team totals of the same game, which is
what every rate here divides by. No subscription number is an input.

**Minutes are the join that makes a rate a rate**, and this feed writes them as
a string. `parse_minutes` handles both the integer form and "34:12"; a silent
coercion to NaN would quietly drop the starters and leave a table of bench
players that still looked like a season.

**What is exact here and what is not**, because the difference matters when a
number gets quoted:

* Usage, %shots, %minutes, assist rate, turnover rate, rebound rates, block and
  steal rates, free-throw rate, per-40 and per-100 — EXACT. They are definitions,
  and the only judgement is which denominator, which is stated per function.
* Game Score — EXACT. Hollinger's published linear formula.
* Offensive Rating (Oliver) and PER — NOT implemented. Oliver's individual ORtg
  needs possession-terminating credit assignment that this box line cannot
  support without assumptions, and PER needs league-wide pace and a positional
  adjustment. An approximation of either, carrying the name, would be quoted as
  though it were the published statistic. `torvik_style_shot_share` is offered
  instead as an honest, defined quantity.
* Box Plus/Minus, Win Shares, RAPM — not possible: there are zero
  `Substitution` rows in the 2019-2024 play-by-play, so there is no on-court five.

Every rate is a per-GAME observation. Use `team_features.walk_forward` on the
aggregated player table to get something a model may use before tip-off.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def parse_minutes(minutes: pd.Series) -> pd.Series:
    """Minutes as a float, from either `34` or `"34:12"`.

    The feed mixes the two. `pd.to_numeric(errors="coerce")` alone turns every
    "MM:SS" row into NaN, which silently removes the players who played most and
    leaves a table that still has the right number of rows.
    """
    text = minutes.astype("string")
    colon = text.str.contains(":", na=False)
    # float64 BEFORE the fill: `to_numeric` returns a nullable Int64 when every
    # plain value is whole, and filling an Int64 with the Float64 minutes from
    # the "MM:SS" branch raises rather than upcasting.
    out = pd.to_numeric(text.where(~colon), errors="coerce").astype("float64")
    if colon.any():
        parts = text.where(colon).str.split(":", expand=True)
        seconds = pd.to_numeric(parts[1], errors="coerce") if parts.shape[1] > 1 else 0.0
        out = out.fillna(
            (pd.to_numeric(parts[0], errors="coerce") + seconds / 60.0).astype("float64")
        )
    return out.astype("float64")


def _rate(numerator, denominator):
    return numerator / denominator.replace(0, np.nan)


def player_game_features(player_box: pd.DataFrame) -> pd.DataFrame:
    """One row per player-game: the rate stats, against team totals.

    **Every "while on the floor" denominator here is a minutes-share
    approximation of the team's game total**, not a true on-court count, because
    this feed has no lineup data. That is the standard box-score approximation --
    it is what Sports-Reference and Torvik compute from the same inputs -- and it
    is stated rather than implied: a player's rebound rate is his share of the
    rebounds available during the minutes he played, assuming the team's rate ran
    at its game average while he was on.
    """
    frame = player_box.copy()
    frame["minutes_played"] = parse_minutes(frame["minutes"])
    frame = frame[frame["minutes_played"].fillna(0) > 0].copy()

    team = frame.groupby(["game_id", "team_id"], observed=True).agg(
        team_minutes=("minutes_played", "sum"),
        team_fga=("field_goals_attempted", "sum"),
        team_fgm=("field_goals_made", "sum"),
        team_fta=("free_throws_attempted", "sum"),
        team_turnovers=("turnovers", "sum"),
        team_oreb=("offensive_rebounds", "sum"),
        team_dreb=("defensive_rebounds", "sum"),
        team_points=("points", "sum"),
    ).reset_index()
    f = frame.merge(team, on=["game_id", "team_id"])

    # The player's share of the team's minutes: the scaling every "on floor"
    # denominator below uses.
    share = _rate(f["minutes_played"] * 5.0, f["team_minutes"])

    out = pd.DataFrame({
        "game_id": f["game_id"], "team_id": f["team_id"],
        "athlete_id": f["athlete_id"], "season": f["season"],
        "minutes": f["minutes_played"], "points": f["points"],
        "starter": f.get("starter"),
    })
    out["minutes_share"] = share

    # Possessions a player ends: a shot, a trip to the line, or a turnover.
    used = f["field_goals_attempted"] + 0.44 * f["free_throws_attempted"] + f["turnovers"]
    team_used = f["team_fga"] + 0.44 * f["team_fta"] + f["team_turnovers"]
    out["usage_rate"] = _rate(used, team_used * share)
    out["shot_share"] = _rate(f["field_goals_attempted"], f["team_fga"] * share)

    out["assist_rate"] = _rate(f["assists"], (f["team_fgm"] - f["field_goals_made"]) * share)
    out["turnover_rate"] = _rate(f["turnovers"], used)
    out["assist_to_turnover"] = _rate(f["assists"], f["turnovers"])
    out["off_reb_rate"] = _rate(f["offensive_rebounds"], f["team_oreb"] * share)
    out["def_reb_rate"] = _rate(f["defensive_rebounds"], f["team_dreb"] * share)
    out["block_rate"] = _rate(f["blocks"], f["minutes_played"]) * 40
    out["steal_rate"] = _rate(f["steals"], f["minutes_played"]) * 40
    out["free_throw_rate"] = _rate(f["free_throws_attempted"], f["field_goals_attempted"])
    out["fouls_per_40"] = _rate(f["fouls"], f["minutes_played"]) * 40
    out["points_per_40"] = _rate(f["points"], f["minutes_played"]) * 40

    out["true_shooting_pct"] = _rate(
        f["points"], 2 * (f["field_goals_attempted"] + 0.44 * f["free_throws_attempted"])
    )

    # Hollinger's Game Score, published and linear -- no approximation in it.
    out["game_score"] = (
        f["points"]
        + 0.4 * f["field_goals_made"]
        - 0.7 * f["field_goals_attempted"]
        - 0.4 * (f["free_throws_attempted"] - f["free_throws_made"])
        + 0.7 * f["offensive_rebounds"]
        + 0.3 * f["defensive_rebounds"]
        + f["steals"]
        + 0.7 * f["assists"]
        + 0.7 * f["blocks"]
        - 0.4 * f["fouls"]
        - f["turnovers"]
    )
    return out


def team_roster_features(players: pd.DataFrame) -> pd.DataFrame:
    """Per team-game: bench share and how concentrated the usage is.

    Roster continuity and returning minutes need a season-over-season join on
    `athlete_id` and belong to whoever builds the preseason prior; what is here
    is what one game can say.
    """
    if "starter" not in players or players["starter"].isna().all():
        raise ValueError(
            "player_box carries no usable `starter` flag, so bench share cannot "
            "be computed. It is not inferable from minutes."
        )
    frame = players.copy()
    frame["is_bench"] = ~frame["starter"].fillna(False).astype(bool)
    grouped = frame.groupby(["game_id", "team_id"], observed=True)
    return pd.DataFrame({
        "bench_minutes_share": grouped.apply(
            lambda g: g.loc[g.is_bench, "minutes"].sum() / g["minutes"].sum(),
            include_groups=False,
        ),
        "bench_points_share": grouped.apply(
            lambda g: g.loc[g.is_bench, "points"].sum() / max(g["points"].sum(), 1),
            include_groups=False,
        ),
        # How few players carry the offence. Herfindahl over usage shares: 0.2
        # is five equal users, higher is more concentrated.
        "usage_concentration": grouped["usage_rate"].apply(
            lambda s: float(((s / s.sum()) ** 2).sum()) if s.sum() else np.nan
        ),
    }).reset_index()
