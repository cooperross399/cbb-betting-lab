"""A rating for every school on a Division I schedule, not only the D-I ones.

Cooper, 2026-11-27: *"Still need full projections for every game and figure
out how to learn every team so you can do that. Need total projections and
spreads"*, and the same morning *"We need to know every single ... division"*.

**Why the fit cannot do this on its own.** `ratings.fit` is fitted on D-I
against D-I (`population.fittable`), because a non-D-I school is connected to
the D-I graph by one or two games a season and its rating would be the prior
talking. So a D-I side hosting an NAIA, D-II or D-III school had no number at
all and the board fell back to ESPN's predictor -- six to ten games a day in
November and December.

**What this does instead.** It does not widen the lab: nothing here fits a
non-D-I school's games against other non-D-I schools, and no non-D-I game is
ever fitted on, carded or graded. It reads the games those schools have
already played *against D-I opposition* -- the rows `build_datasets` has
always carried and the fit has always excluded -- and measures each side of
each game against what the D-I opponent's own fitted rating says it should
have been:

* the non-D-I offence is its efficiency less the league level, the D-I
  defence and the venue;
* its defence is the D-I offence's efficiency less the same;
* its tempo is the game's possessions less the league tempo and the D-I
  tempo.

Each school's rating is then the **class mean** (every non-D-I school's
residuals this season, so a school never seen before still gets the measured
level of a typical visiting non-D-I side) plus its own shrunk departure from
that mean, read off its own games: this season's at full weight, last
season's at half and the season before at a quarter, shrunk at
`SHRINK_GAMES` games. A school with three games against D-I this season
keeps about three sevenths of its own departure.

The residual for an earlier season is read against the D-I opponent's
CURRENT rating, which is an approximation -- a team is not the team it was
last March -- and it is why earlier seasons carry less weight and move only
a school's departure, never the class mean (unless this season has fewer
than `MIN_CLASS_GAMES` such games, which is true only in the first week).

Everything read is strictly before the day being priced: the caller's
`history` is already cut by `price_backtest.history_before`, and this module
re-cuts on `slate_date` anyway so a mis-cut frame cannot leak a score.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Iterable

import numpy as np
import pandas as pd

#: The switch. Off, a non-D-I school has no rating and its game is refused
#: as before (the board then falls back to ESPN's predictor).
RATE_NON_DIVISION_ONE = True

#: A school's own departure from the class mean is shrunk at this many
#: (weighted) games: three games keep 3 / (3 + 4) of it.
SHRINK_GAMES = 4.0

#: Weight on a game by how many seasons before the priced one it was played.
SEASON_WEIGHTS = {0: 1.0, 1: 0.5, 2: 0.25}

#: Below this many non-D-I games this season the class mean is read off every
#: season in `SEASON_WEIGHTS` instead of this one alone.
MIN_CLASS_GAMES = 30

#: The game state `population.classify_game` gives a D-I side's game against
#: a school the feed gives no conference.
NON_DI_STATE = "non_di_opponent"

#: The label a matchup carries when one side's rating came from here.
IDENTIFIED_BY = "non_di_baseline"

#: A clamp on any one residual, in points per 100 possessions (efficiency) or
#: possessions (tempo), so one blowout box score with a broken possession
#: count cannot drag a school's rating by itself.
RESIDUAL_CLAMP = 40.0

MINIMUM_GAME_POSSESSIONS = 40.0
POSSESSION_SCALE = 100.0


@dataclass(frozen=True)
class ClassLevel:
    """The typical non-D-I side, and how many games it is measured on."""

    offence: float
    defence: float
    tempo: float
    games: int
    seasons: tuple[int, ...] = ()


@dataclass(frozen=True)
class BaselineRatings:
    """What `extend` added: per school, its three numbers and its evidence."""

    level: ClassLevel | None
    offence: dict = field(default_factory=dict)
    defence: dict = field(default_factory=dict)
    tempo: dict = field(default_factory=dict)
    #: (component, team) -> share of the rating that is the class mean.
    prior_weight: dict = field(default_factory=dict)
    #: team -> weighted games of its own behind its departure.
    games: dict = field(default_factory=dict)

    @property
    def teams(self) -> frozenset:
        return frozenset(self.offence)

    def summary_line(self) -> str:
        if self.level is None:
            return "Non-D-I schools: no games against D-I opposition to measure, none rated."
        return (
            f"Non-D-I schools: class level measured on {self.level.games} game(s) "
            f"against D-I opposition (seasons {list(self.level.seasons)}): offence "
            f"{self.level.offence:+.1f}, defence {self.level.defence:+.1f} per 100 "
            f"against the D-I league, tempo {self.level.tempo:+.1f}. "
            f"{len(self.offence)} school(s) rated for this slate, "
            f"{sum(1 for g in self.games.values() if g > 0)} with games of their own."
        )


def _residuals(ratings, history: pd.DataFrame, *, season: int, day: str) -> pd.DataFrame:
    """One row per non-D-I side per game, with its three residuals."""
    needed = {"game_id", "season", "slate_date", "team_id", "opponent_id", "home_away",
              "team_score", "opponent_score", "possessions_estimated", "game_state"}
    if history is None or history.empty or not needed <= set(history.columns):
        return pd.DataFrame()
    frame = history[history["game_state"].astype(str) == NON_DI_STATE]
    frame = frame[frame["slate_date"].astype(str) < str(day)]
    seasons = pd.to_numeric(frame["season"], errors="coerce")
    back = int(season) - seasons
    frame = frame.assign(back=back)
    frame = frame[frame["back"].isin(list(SEASON_WEIGHTS))]
    if frame.empty:
        return pd.DataFrame()
    if "periods" in frame.columns:
        # Regulation only, as the fit: `distributions.build` adds overtime back.
        periods = pd.to_numeric(frame["periods"], errors="coerce")
        frame = frame[(periods == 2) | periods.isna()]
    poss = pd.to_numeric(frame["possessions_estimated"], errors="coerce")
    frame = frame.assign(possessions_estimated=poss)
    frame = frame.assign(game_possessions=frame.groupby("game_id")["possessions_estimated"].transform("mean"))
    frame = frame[frame["game_possessions"] >= MINIMUM_GAME_POSSESSIONS]

    rated = set(ratings.offence)
    # The non-D-I side's own row: its team is not rated, its opponent is.
    mine = frame[~frame["team_id"].isin(rated) & frame["opponent_id"].isin(rated)]
    if mine.empty:
        return pd.DataFrame()
    league, pace = float(ratings.league_efficiency), float(ratings.league_tempo)
    venue = ratings.venue
    neutral = mine["neutral_site"].astype(str).str.lower().isin({"true", "1"}) if "neutral_site" in mine.columns \
        else pd.Series(False, index=mine.index)
    home = mine["home_away"].astype(str).str.lower() == "home"
    rows = []
    for record, is_neutral, is_home in zip(mine.to_dict("records"), neutral, home):
        opponent = record["opponent_id"]
        tier = ratings.tier_of(opponent)
        own_add = opp_add = 0.0
        if not is_neutral:
            if is_home:  # the non-D-I school at home: rare, measured the same way
                own_add, opp_add = venue.home_offence(tier), venue.home_defence(tier)
            else:
                own_add, opp_add = venue.home_defence(tier), venue.home_offence(tier)
        p = float(record["game_possessions"])
        own_eff = POSSESSION_SCALE * float(record["team_score"]) / p
        opp_eff = POSSESSION_SCALE * float(record["opponent_score"]) / p
        r_off = own_eff - league - float(ratings.defence.get(opponent, 0.0)) - own_add
        r_def = opp_eff - league - float(ratings.offence.get(opponent, 0.0)) - opp_add
        r_tmp = p - pace - float(ratings.tempo.get(opponent, 0.0))
        clamp = lambda v: float(np.clip(v, -RESIDUAL_CLAMP, RESIDUAL_CLAMP))  # noqa: E731
        rows.append({"team_id": record["team_id"], "back": int(record["back"]),
                     "season": int(record["season"]),
                     "offence": clamp(r_off), "defence": clamp(r_def), "tempo": clamp(r_tmp)})
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out[np.isfinite(out[["offence", "defence", "tempo"]]).all(axis=1)]
    return out


def class_level(residuals: pd.DataFrame) -> ClassLevel | None:
    if residuals is None or residuals.empty:
        return None
    current = residuals[residuals["back"] == 0]
    pool = current if len(current) >= MIN_CLASS_GAMES else residuals
    return ClassLevel(
        offence=float(pool["offence"].mean()),
        defence=float(pool["defence"].mean()),
        tempo=float(pool["tempo"].mean()),
        games=int(len(pool)),
        seasons=tuple(sorted(int(s) for s in pool["season"].unique())),
    )


def rate(ratings, history: pd.DataFrame, *, season: int, day: str,
         teams: Iterable) -> BaselineRatings:
    """Ratings for each of `teams` the D-I fit does not hold."""
    wanted = [t for t in dict.fromkeys(teams) if t is not None and t not in ratings.offence]
    if not wanted:
        return BaselineRatings(level=None)
    residuals = _residuals(ratings, history, season=season, day=day)
    level = class_level(residuals)
    if level is None:
        return BaselineRatings(level=None)
    out = BaselineRatings(level=level)
    means = {"offence": level.offence, "defence": level.defence, "tempo": level.tempo}
    weights = residuals["back"].map(SEASON_WEIGHTS).astype(float) if not residuals.empty else None
    for team in wanted:
        own = residuals[residuals["team_id"] == team] if not residuals.empty else residuals
        w = weights.loc[own.index].to_numpy() if len(own) else np.zeros(0)
        n = float(w.sum())
        share = SHRINK_GAMES / (n + SHRINK_GAMES)
        for component in ("offence", "defence", "tempo"):
            departure = 0.0
            if n > 0:
                departure = float(np.sum(w * (own[component].to_numpy() - means[component]))) / (n + SHRINK_GAMES)
            getattr(out, component)[team] = means[component] + departure
            out.prior_weight[(component, team)] = share
        out.games[team] = n
    return out


def extend(ratings, history: pd.DataFrame, *, season: int, day: str, teams: Iterable):
    """`ratings` with every non-D-I school in `teams` rated, and what was added.

    Returns `(ratings, baseline)`. The D-I ratings are untouched; a school the
    fit already holds is never overwritten.
    """
    if not RATE_NON_DIVISION_ONE:
        return ratings, BaselineRatings(level=None)
    baseline = rate(ratings, history, season=season, day=day, teams=teams)
    if not baseline.offence:
        return ratings, baseline
    prior_weight = {**ratings.prior_weight, **baseline.prior_weight}
    extended = replace(
        ratings,
        offence={**ratings.offence, **baseline.offence},
        defence={**ratings.defence, **baseline.defence},
        tempo={**ratings.tempo, **baseline.tempo},
        prior_weight=prior_weight,
        baseline_teams=frozenset(ratings.baseline_teams) | baseline.teams,
    )
    return extended, baseline
