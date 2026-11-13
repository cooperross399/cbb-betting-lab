"""A side's price for a settled call, read from the hourly line captures.

Cooper, 2026-11-13: *"find a spread for both teams in every game"*. A frozen
board before decision 101 carried the home spread price only, and some boards
carry no price for one side of a market at all, so a straight-up, spread or
totals call on that side was graded and counted `unpriced`. The line-movement
capture store (`cbb_line_movement.csv`, the `line-movement` branch) holds
every book's price on both sides of every game, hourly, since 2026-10-24.

This reads the price the board itself could have shown: the best price
across books, for that team, at that line, in the last capture taken at or
before the board was frozen. Nothing is estimated. A side the store did not
capture at that line by then stays unpriced.

Sides are matched by TEAM, never by the provider's home/away label: on a
neutral floor the provider and ESPN can file a game the other way round
(decision 72), and a side read by label would price a team as its opponent.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

#: The store's market names, by the board's.
MARKETS = {"spread": "spread", "moneyline": "moneyline", "total": "total_points"}


def _when(text) -> datetime | None:
    if not text:
        return None
    try:
        t = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except ValueError:
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def _num(text) -> float | None:
    try:
        v = float(text)
    except (TypeError, ValueError):
        return None
    return v if v == v else None


class CapturePrices:
    """Every full-game team row of the store, indexed by slate date and the
    resolved pair of teams. `resolve` maps a team name (either feed's
    spelling) to one key; with no resolver every name is its own key."""

    def __init__(self, rows, resolve=None):
        self._resolve = resolve or (lambda name: name)
        self._seen: dict[str, str] = {}
        self._games: dict[tuple[str, frozenset], list[dict]] = defaultdict(list)
        wanted = set(MARKETS.values())
        for r in rows:
            if r.get("market") not in wanted or (r.get("segment") or "game") != "game" or r.get("player"):
                continue
            home, away = self.key(r.get("home_team")), self.key(r.get("away_team"))
            when, odds = _when(r.get("captured_at")), _num(r.get("american_odds"))
            if not home or not away or when is None or odds is None:
                continue
            self._games[(r.get("slate_date") or "", frozenset((home, away)))].append(
                {"when": when, "market": r["market"], "home": home, "away": away,
                 "selection": (r.get("selection") or "").lower(), "line": _num(r.get("line")), "odds": odds})

    @classmethod
    def load(cls, path: Path, resolve=None) -> "CapturePrices | None":
        try:
            with open(path, newline="", encoding="utf-8") as fh:
                return cls(csv.DictReader(fh), resolve)
        except (OSError, UnicodeError, csv.Error):
            return None

    def key(self, name) -> str:
        if not name:
            return ""
        if name not in self._seen:
            try:
                self._seen[name] = self._resolve(name) or name
            except Exception:
                self._seen[name] = name
        return self._seen[name]

    def price(self, day: str, market: str, team: str, opponent: str, selection: str,
              line: float | None, before) -> int | None:
        """The best American price for `team`'s side (or, for a total, the
        `selection` "over"/"under") at `line`, in the last capture at or
        before `before`. `line` is the side's own handicap for a spread."""
        cutoff = _when(before)
        store = MARKETS.get(market)
        t, o = self.key(team), self.key(opponent)
        rows = self._games.get((day or "", frozenset((t, o))))
        if not rows or cutoff is None or store is None or t == o:
            return None
        picked = []
        for r in rows:
            if r["market"] != store or r["when"] > cutoff:
                continue
            if store == "total_points":
                if r["selection"] != selection:
                    continue
            else:
                side = "home" if r["home"] == t else "away" if r["away"] == t else None
                if side is None or r["selection"] != side:
                    continue
            if line is not None and (r["line"] is None or abs(r["line"] - line) > 1e-6):
                continue
            picked.append(r)
        if not picked:
            return None
        last = max(r["when"] for r in picked)
        return int(max(r["odds"] for r in picked if r["when"] == last))
