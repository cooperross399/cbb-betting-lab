"""Dean Oliver's four factors, Wins Above Bubble and close-game luck (decision 92).

Cooper, 2026-11-09: *"every stat that goes into the model. Add more stats if
needed"*, naming the four factors, WAB and the NET among them.

**What the ratings already hold.** The fitted offence and defence are points
per 100 possessions adjusted for the opponent and the venue: they ARE the
four factors summed with their weights. So an additive four-factor model
reprices nothing. What a sum misses is the *mismatch*: an attack that lives on
offensive rebounds against a defence that gives them up gains more than the
two deviations added in points, because a rate cannot exceed one and the
effect compounds near the ends. So `mismatch` combines each factor on the
log-odds scale -- the attack's departure from the league plus the defence's
-- and prices only the difference from the straight sum, through each
factor's own points-per-100 weight, fitted by least squares on the season's
games each day. That difference is zero for two average teams and largest
for two extreme styles, which is what "a stylistic mismatch" means.

**Wins Above Bubble** is the NCAA committee's résumé number: a team's wins
minus the wins a bubble team (here the `BUBBLE_RANK`-th best net rating in
the day's ratings) would expect against the same schedule at the same sites.
It is a fact about the season so far, not a forecast, and sportsbooks do not
price it, so it is computed and shown and moves no price on its own.

**Close-game luck** is the part of WAB that is a forecast. A team whose wins
run ahead of what its own ratings expected of the same games has won its
close ones, and close-game records do not repeat. `luck` is that excess per
game; the candidate layer takes `LUCK_SHARE` of it back, in points per 100.

Both layers are candidates in `card_factors`, computed on every game and on
the card only when the layer audit adds them (registered as
`model_inputs_2026_11_09`). Every constant is this lab's choice, made before
any price was read.
"""

from __future__ import annotations

import math
from statistics import NormalDist

import numpy as np
import pandas as pd

#: Games a side needs before its factors are read, and the shrinkage toward
#: the league that keeps a six-game sample from carrying a full style.
MIN_GAMES = 5
SHRINKAGE_GAMES = 10.0
#: The most the mismatch may move one side's attack, per 100 possessions.
CLAMP = 2.0

#: The bubble: roughly the last at-large team, by net rating.
BUBBLE_RANK = 45
#: A game's margin spread around its expectation, in points, for WAB and luck.
MARGIN_SD = 11.0
#: Share of each extra win per game taken back, as points per 100 (one win a
#: game above expectation is enormous; ten per 100 is a full-strength swing).
LUCK_SHARE = 0.5
LUCK_POINTS_PER_WIN = 10.0
LUCK_CLAMP = 2.0
LUCK_MIN_GAMES = 5

FACTORS = ("efg", "tov", "orb", "ftr")

_NORMAL = NormalDist()


def _num(frame: pd.DataFrame, column: str) -> pd.Series:
    return pd.to_numeric(frame.get(column), errors="coerce")


def game_factors(rows: pd.DataFrame) -> pd.DataFrame:
    """One row per team-game with the team's own four factors and its
    opponent's, and points per 100 of its possessions."""
    need = {"game_id", "team_id", "opponent_id", "field_goals_made", "field_goals_attempted",
            "three_point_field_goals_made", "free_throws_made", "turnovers",
            "offensive_rebounds", "defensive_rebounds", "team_score", "game_possessions"}
    if rows is None or len(rows) == 0 or not need <= set(rows.columns):
        return pd.DataFrame()
    frame = rows[list(need)].copy()
    for column in need - {"game_id", "team_id", "opponent_id"}:
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    opp = frame[["game_id", "team_id", "defensive_rebounds", "offensive_rebounds"]].rename(
        columns={"team_id": "opponent_id", "defensive_rebounds": "opp_drb", "offensive_rebounds": "opp_orb"})
    frame = frame.merge(opp, on=["game_id", "opponent_id"], how="inner")
    fga = frame["field_goals_attempted"]
    poss = frame["game_possessions"]
    out = pd.DataFrame({
        "game_id": frame["game_id"], "team_id": frame["team_id"], "opponent_id": frame["opponent_id"],
        "fgm3": frame["field_goals_made"] + 0.5 * frame["three_point_field_goals_made"],
        "fga": fga, "tov_n": frame["turnovers"], "poss": poss,
        "orb_n": frame["offensive_rebounds"], "orb_d": frame["offensive_rebounds"] + frame["opp_drb"],
        "ftm": frame["free_throws_made"],
        "ppp": 100.0 * frame["team_score"] / poss,
    })
    out = out.replace([np.inf, -np.inf], np.nan).dropna()
    return out[(out["fga"] > 0) & (out["poss"] > 0) & (out["orb_d"] > 0)]


def _rates(frame: pd.DataFrame) -> dict:
    return {
        "efg": float(frame["fgm3"].sum() / frame["fga"].sum()),
        "tov": float(frame["tov_n"].sum() / frame["poss"].sum()),
        "orb": float(frame["orb_n"].sum() / frame["orb_d"].sum()),
        "ftr": float(frame["ftm"].sum() / frame["fga"].sum()),
    }


class FactorTable:
    """The season's four factors, attack and defence per team, the league's,
    and each factor's points-per-100 weight."""

    def __init__(self, games: pd.DataFrame):
        self.league: dict = {}
        self.weights: dict = {}
        self.attack: dict = {}
        self.defence: dict = {}
        self.games: dict = {}
        if games is None or games.empty:
            return
        self.league = _rates(games)
        per_game = pd.DataFrame({
            "efg": games["fgm3"] / games["fga"], "tov": games["tov_n"] / games["poss"],
            "orb": games["orb_n"] / games["orb_d"], "ftr": games["ftm"] / games["fga"],
        })
        if len(per_game) >= 50:
            design = np.column_stack([np.ones(len(per_game))] + [per_game[f].to_numpy() for f in FACTORS])
            coef, *_ = np.linalg.lstsq(design, games["ppp"].to_numpy(), rcond=None)
            self.weights = dict(zip(FACTORS, (float(c) for c in coef[1:])))
        for team, group in games.groupby("team_id"):
            self.attack[team] = _rates(group)
            self.games[team] = len(group)
        for team, group in games.groupby("opponent_id"):
            self.defence[team] = _rates(group)

    def __len__(self) -> int:
        return len(self.attack)

    def _shrunk(self, table: dict, team) -> dict | None:
        if team not in table or self.games.get(team, 0) < MIN_GAMES:
            return None
        n = float(self.games[team])
        keep = n / (n + SHRINKAGE_GAMES)
        return {f: self.league[f] + keep * (table[team][f] - self.league[f]) for f in FACTORS}

    def mismatch(self, attack_team, defence_team) -> float | None:
        """Points per 100 the attack gains from the style pairing beyond the
        straight sum of the two sides' factors, or None without enough games
        or without the season's weights."""
        if not self.weights:
            return None
        attack = self._shrunk(self.attack, attack_team)
        defence = self._shrunk(self.defence, defence_team)
        if attack is None or defence is None:
            return None
        move = 0.0
        for factor in FACTORS:
            league = self.league[factor]
            if not 0.0 < league < 1.0:
                continue
            a = min(max(attack[factor], 1e-4), 1 - 1e-4)
            d = min(max(defence[factor], 1e-4), 1 - 1e-4)
            logit = _logit(league) + (_logit(a) - _logit(league)) + (_logit(d) - _logit(league))
            combined = 1.0 / (1.0 + math.exp(-logit))
            straight = league + (a - league) + (d - league)
            move += self.weights[factor] * (combined - straight)
        return float(np.clip(move, -CLAMP, CLAMP))


def _logit(p: float) -> float:
    return math.log(p / (1.0 - p))


def _home_sign(row: dict, team) -> float:
    state = str(row.get("venue_state") or row.get("home_away") or "")
    home_away = str(row.get("home_away") or "")
    if state in ("neutral", "quasi_neutral") or str(row.get("neutral_site")).lower() in ("true", "1"):
        return 0.0
    return 1.0 if home_away == "home" else -1.0 if home_away == "away" else 0.0


def _win_probability(net_per_100: float, possessions: float) -> float:
    return _NORMAL.cdf(net_per_100 * possessions / 100.0 / MARGIN_SD)


def resume(rows: pd.DataFrame, ratings, *, teams=None, home_points: float = 3.0) -> tuple[dict, dict]:
    """(WAB per team, close-game luck per team in points per 100).

    WAB: wins minus a bubble team's expected wins against the same opponents
    at the same sites. Luck: wins minus the team's OWN expected wins from the
    day's ratings, per game, shrunk and clamped, as points per 100."""
    if rows is None or len(rows) == 0 or ratings is None:
        return {}, {}
    nets = {t: float(ratings.offence.get(t, 0.0)) - float(ratings.defence.get(t, 0.0))
            for t in set(ratings.offence) | set(ratings.defence)}
    if len(nets) < BUBBLE_RANK:
        return {}, {}
    bubble = sorted(nets.values(), reverse=True)[BUBBLE_RANK - 1]
    frame = rows.copy()
    frame["won"] = pd.to_numeric(frame.get("team_score"), errors="coerce") > pd.to_numeric(
        frame.get("opponent_score"), errors="coerce")
    wanted = None if teams is None else {t for t in teams}
    wab: dict = {}
    luck: dict = {}
    for team, group in frame.groupby("team_id"):
        if wanted is not None and team not in wanted:
            continue
        bubble_wins = own_wins = actual = 0.0
        n = 0
        for row in group.to_dict("records"):
            opponent = row.get("opponent_id")
            if opponent not in nets:
                continue
            possessions = ratings.expected_tempo(team, opponent)
            site = _home_sign(row, team) * home_points * 100.0 / max(possessions, 1.0)
            bubble_wins += _win_probability(bubble - nets[opponent] + site, possessions)
            own_wins += _win_probability(nets.get(team, 0.0) - nets[opponent] + site, possessions)
            actual += 1.0 if row["won"] else 0.0
            n += 1
        if n == 0:
            continue
        wab[team] = round(actual - bubble_wins, 2)
        if n >= LUCK_MIN_GAMES:
            per_game = (actual - own_wins) / n
            shrunk = per_game * n / (n + SHRINKAGE_GAMES)
            luck[team] = float(np.clip(LUCK_SHARE * LUCK_POINTS_PER_WIN * shrunk, -LUCK_CLAMP, LUCK_CLAMP))
    return wab, luck
