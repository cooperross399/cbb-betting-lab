"""Team ratings read off the betting lines (decision 84, Cooper 2026-11-08).

The ratings (`models/ratings.py`) are fitted to final scores. The market sees
the same games and more: injuries, lineups, travel and money. Its closing lines
are, game for game, the best public forecast of a margin and a total. This
module fits one number per team for each from the closing consensus of games
already played, so that a team's market view enters the card as a rating and
not as tonight's price.

**The fit.** For every event the line-movement store captured, the last
capture at or before tip gives the consensus home spread and total
(`reports/closing_alarm.closing_consensus`). Oriented to the results source's
home side through the schedule, each game says::

    -spread = net[home] - net[away] + home_edge * (true home floor)
    total   = mean_total + pace[home] + pace[away]

Both are ridge regressions, every team shrunk toward zero at `RIDGE_GAMES`
games' weight, solved in closed form. A team with fewer than `MIN_GAMES` lined
games carries no market rating and the layer leaves its games alone.

**Conditioned on what, known when.** Only events whose slate day is strictly
before the day being priced are read, and only captures at or before each
event's tip, so the fit holds nothing tonight's own line could have told it.
The store begins 2026-10-24, so every day before it has no market rating and
the layer moves nothing there: the price backtest over the bought seasons is
unchanged by it, and it cannot be backtested. It reaches the card only through
the layer audit (`models/layer_audit.py`), which re-prices the last four weeks
walk-forward and switches it on only when it moved the margin and total toward
the final score. Registered as `market_ratings_2026_11_08`, one per tier.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

#: A team's market rating needs this many lined games.
MIN_GAMES = 4
#: Ridge weight, in games: each team is shrunk toward zero as if it had this
#: many games at zero.
RIDGE_GAMES = 2.0
#: The fit needs this many lined games before it says anything.
MIN_EVENTS = 60


@dataclass
class MarketRatings:
    as_of: str
    events: int = 0
    home_edge: float = 0.0
    mean_total: float = 0.0
    has_margin: bool = False
    has_total: bool = False
    #: team_id -> (net margin rating, pace rating in total points, lined games)
    teams: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.teams)

    def margin(self, home_id, away_id, *, neutral: bool) -> float | None:
        h, a = self.teams.get(home_id), self.teams.get(away_id)
        if h is None or a is None or not self.has_margin:
            return None
        return h[0] - a[0] + (0.0 if neutral else self.home_edge)

    def total(self, home_id, away_id) -> float | None:
        h, a = self.teams.get(home_id), self.teams.get(away_id)
        if h is None or a is None or not self.has_total:
            return None
        return self.mean_total + h[1] + a[1]


_STORE_CACHE: dict = {}


def read_store(path: Path | str) -> pd.DataFrame | None:
    """The capture store, read once per process per file version."""
    path = Path(path)
    if not path.is_file():
        return None
    key = (str(path), path.stat().st_mtime_ns)
    if key not in _STORE_CACHE:
        _STORE_CACHE.clear()
        _STORE_CACHE[key] = pd.read_csv(path, low_memory=False)
    return _STORE_CACHE[key]


def lined_games(store: pd.DataFrame, schedule: pd.DataFrame, *, day: str) -> pd.DataFrame:
    """One row per event played before `day`: the results source's home and
    away ids, whether the floor was neutral, the home margin the closing spread
    implied and the closing total."""
    from cbb_betting_lab.providers import team_names
    from cbb_betting_lab.reports.closing_alarm import closing_consensus

    columns = ["event_id", "home_id", "away_id", "neutral", "margin", "total"]
    if store is None or store.empty or schedule is None or schedule.empty:
        return pd.DataFrame(columns=columns)
    before = store[store["slate_date"].astype(str).str[:10] < str(day)[:10]]
    if before.empty:
        return pd.DataFrame(columns=columns)
    close = closing_consensus(before)
    events = before.drop_duplicates("event_id")[["event_id", "slate_date", "home_team", "away_team"]]
    index = team_names.build_index(schedule)
    fixtures: dict = {}
    for row in schedule[["game_date", "home_id", "away_id", "neutral_site"]].itertuples(index=False):
        try:
            pair = frozenset((int(row.home_id), int(row.away_id)))
        except (TypeError, ValueError):
            continue
        fixtures[(str(row.game_date)[:10], pair)] = (int(row.home_id), bool(row.neutral_site))
    out = []
    for e in events.itertuples(index=False):
        spread = close.get((e.event_id, "spread"))
        total = close.get((e.event_id, "total_points"))
        if spread is None and total is None:
            continue
        home = index.resolve(e.home_team)
        away = index.resolve(e.away_team)
        if home is None or away is None or home == away:
            continue
        fixture = fixtures.get((str(e.slate_date)[:10], frozenset((int(home), int(away)))))
        if fixture is None:
            continue
        espn_home, neutral = fixture
        margin = None if spread is None else -float(spread)
        if margin is not None and espn_home != int(home):
            margin = -margin
        h, a = (int(home), int(away)) if espn_home == int(home) else (int(away), int(home))
        out.append({"event_id": e.event_id, "home_id": h, "away_id": a, "neutral": neutral,
                    "margin": margin, "total": None if total is None else float(total)})
    return pd.DataFrame(out, columns=columns)


def fit(games: pd.DataFrame, *, as_of: str) -> MarketRatings:
    """Ridge fits of margin and total; an empty rating when there is too little."""
    ratings = MarketRatings(as_of=str(as_of)[:10])
    if games is None or len(games) < MIN_EVENTS:
        ratings.events = 0 if games is None else int(len(games))
        return ratings
    teams = sorted(set(games["home_id"]) | set(games["away_id"]))
    col = {t: i for i, t in enumerate(teams)}
    n = len(teams)
    counts = pd.concat([games["home_id"], games["away_id"]]).value_counts()

    def solve(rows: pd.DataFrame, y: np.ndarray, *, sign: float, with_home: bool) -> np.ndarray:
        width = n + (1 if with_home else 0)
        X = np.zeros((len(rows), width))
        for k, r in enumerate(rows.itertuples(index=False)):
            X[k, col[r.home_id]] = 1.0
            X[k, col[r.away_id]] = sign
            if with_home and not r.neutral:
                X[k, n] = 1.0
        penalty = np.full(width, RIDGE_GAMES)
        if with_home:
            penalty[n] = 1e-6
        return np.linalg.solve(X.T @ X + np.diag(penalty), X.T @ y)

    margins = games.dropna(subset=["margin"])
    net = np.zeros(n)
    if len(margins) >= MIN_EVENTS:
        beta = solve(margins, margins["margin"].to_numpy(float), sign=-1.0, with_home=True)
        net, ratings.home_edge = beta[:n], float(beta[n])
        ratings.has_margin = True
    totals = games.dropna(subset=["total"])
    pace = np.zeros(n)
    if len(totals) >= MIN_EVENTS:
        ratings.mean_total = float(totals["total"].mean())
        pace = solve(totals, totals["total"].to_numpy(float) - ratings.mean_total, sign=1.0, with_home=False)
        ratings.has_total = True
    ratings.events = int(len(games))
    for team, i in col.items():
        games_played = int(counts.get(team, 0))
        if games_played >= MIN_GAMES:
            ratings.teams[team] = (float(net[i]), float(pace[i]), games_played)
    return ratings
