"""The edge bar does not fight the market's move (Cooper, 2026-10-30).

The line-movement capture (`line_movement.py`) records the board four times a
day. This module reads it for one purpose: when the market has moved against a
side since the day's first capture, and the model still leans to that side, the
lean is halved before the edge bar reads it. A move is the market learning
something, usually news or sharp money. A model built on box scores carries
none of that information, and the trusted probability is where the card admits
it.

**The rule.** For each full-game team wager the trusted probability leans
`lean = trusted - market` away from the de-vigged price (`models/trust.py`).
If `lean > 0` and the market has moved at least `MIN_MOVE` against the
selection since the first capture of the event, the trusted probability becomes
`market + FIGHT_SHRINK * lean`. A move WITH the lean changes nothing: the model
is never amplified by a move, only restrained by one.

**What a move is**, from the consensus (the median over books) at the first
capture and at the latest capture no later than the card:

* moneyline: the de-vigged home probability, in probability. `MIN_MOVE` is
  `MIN_MOVE_PROB`.
* spread: the home line, in points. `MIN_MOVE` is `MIN_MOVE_POINTS`.
* total: the total, in points. `MIN_MOVE` is `MIN_MOVE_POINTS`.

The alternate ladders take the move of their main market. Halves, team totals
and player props are untouched, because the capture does not record them.

**Conditioned on what, known when.** Only captures stamped at or before the
card's own time are read, so a card cannot see a move that happened after it
was made. The capture store has no history before 2026-10-24, so this cannot be
backtested and is forward only. It is registered in the experiment ledger
(`line_movement_2026_10_30`, one per tier) and judged there like every other
hypothesis. It reads no price the capture did not already buy, and it touches
neither the allowlist nor the forward ledger, which keeps freezing the model's
own probability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from statistics import median
from typing import Iterable, Mapping

import pandas as pd

#: The share of a lean kept when the market has moved against it.
FIGHT_SHRINK = 0.5
#: The smallest move that counts, by unit.
MIN_MOVE_PROB = 0.02
MIN_MOVE_POINTS = 1.0

#: Each card market, and the captured main market whose move it takes.
MAIN_MARKET = {
    "moneyline": "moneyline",
    "spread": "spread",
    "alternate_spread": "spread",
    "total_points": "total_points",
    "alternate_total_points": "total_points",
}
FULL_GAME = "game"


def _implied(odds) -> float | None:
    try:
        odds = float(odds)
    except (TypeError, ValueError):
        return None
    if odds != odds or odds == 0:
        return None
    return 100.0 / (odds + 100.0) if odds > 0 else -odds / (-odds + 100.0)


def _consensus(capture: pd.DataFrame, market: str) -> float | None:
    """One capture's consensus for one event's main market, home or over side."""
    rows = capture[capture["market"] == market]
    if rows.empty:
        return None
    if market == "moneyline":
        fair = []
        for _book, quotes in rows.groupby("book"):
            sides = {str(s): _implied(o) for s, o in zip(quotes["selection"], quotes["american_odds"])}
            home, away = sides.get("home"), sides.get("away")
            if home is None or away is None or home + away <= 0:
                continue
            fair.append(home / (home + away))
        return float(median(fair)) if fair else None
    side = "home" if market == "spread" else "over"
    lines = pd.to_numeric(rows.loc[rows["selection"].astype(str) == side, "line"], errors="coerce").dropna()
    return float(lines.median()) if len(lines) else None


@dataclass
class Moves:
    """event_id -> main market -> (open, now), and how many events were read."""

    as_of: str
    by_event: dict = field(default_factory=dict)
    reason: str = ""

    def toward(self, wager) -> float | None:
        """How far the market has moved TOWARD this wager's side since the first
        capture, in the market's own unit; negative is against. None when the
        capture holds no move for it."""
        if str(getattr(wager, "player", "") or "").strip():
            return None
        if str(getattr(wager, "segment", "") or "") not in (FULL_GAME, "full_game"):
            return None
        main = MAIN_MARKET.get(str(getattr(wager, "market", "") or ""))
        if main is None:
            return None
        pair = self.by_event.get(str(wager.event_id), {}).get(main)
        if pair is None:
            return None
        opened, now = pair
        delta = now - opened
        selection = str(wager.selection)
        if main == "moneyline":
            return delta if selection == "home" else -delta if selection == "away" else None
        if main == "spread":
            # A home line falling from -3 to -5 is the market moving to home.
            return -delta if selection == "home" else delta if selection == "away" else None
        return delta if selection == "over" else -delta if selection == "under" else None

    @staticmethod
    def threshold(wager) -> float:
        main = MAIN_MARKET.get(str(getattr(wager, "market", "") or ""))
        return MIN_MOVE_PROB if main == "moneyline" else MIN_MOVE_POINTS


def build(captures: pd.DataFrame | None, *, as_of: str) -> Moves:
    """The opening and latest consensus per event, from captures at or before
    `as_of` (an ISO timestamp)."""
    moves = Moves(as_of=str(as_of))
    if captures is None or captures.empty:
        moves.reason = "no line-movement capture was read"
        return moves
    frame = captures.copy()
    frame["captured_at"] = pd.to_datetime(frame["captured_at"], utc=True, errors="coerce")
    cutoff = pd.to_datetime(str(as_of), utc=True, errors="coerce")
    frame = frame.dropna(subset=["captured_at"])
    if cutoff is not None and cutoff == cutoff:
        frame = frame[frame["captured_at"] <= cutoff]
    frame = frame[frame["segment"].astype(str) == FULL_GAME]
    if "player" in frame.columns:
        frame = frame[frame["player"].fillna("").astype(str).str.strip() == ""]
    for event_id, rows in frame.groupby("event_id"):
        stamps = sorted(rows["captured_at"].unique())
        if len(stamps) < 2:
            continue
        first = rows[rows["captured_at"] == stamps[0]]
        last = rows[rows["captured_at"] == stamps[-1]]
        for market in set(MAIN_MARKET.values()):
            opened, now = _consensus(first, market), _consensus(last, market)
            if opened is not None and now is not None:
                moves.by_event.setdefault(str(event_id), {})[market] = (opened, now)
    if not moves.by_event:
        moves.reason = "no event had two captures at or before the card"
    return moves


def read_captures(path: Path | str) -> pd.DataFrame | None:
    """The capture store, or None when it is absent or unreadable."""
    try:
        return pd.read_csv(path, dtype={"event_id": str})
    except (OSError, ValueError):
        return None


@dataclass
class Restraint:
    probabilities: dict
    restrained: list = field(default_factory=list)
    line: str = ""


def apply(trusted: Mapping, market: Mapping, wagers: Iterable, moves: Moves | None) -> Restraint:
    """Halve every lean the market has moved against. Unchanged when there is no
    move table or no market price for a wager."""
    out = dict(trusted or {})
    if moves is None:
        return Restraint(out)
    if not moves.by_event:
        return Restraint(out, line=f"Line movement: not read ({moves.reason}).")
    restrained = []
    for wager in wagers:
        key = wager.key
        if key not in out or key not in (market or {}):
            continue
        lean = float(out[key]) - float(market[key])
        if lean <= 0:
            continue
        toward = moves.toward(wager)
        if toward is None or toward > -Moves.threshold(wager):
            continue
        out[key] = float(market[key]) + FIGHT_SHRINK * lean
        restrained.append(wager)
    line = (
        f"Line movement: {len(moves.by_event):,} event(s) carry a move since their first "
        f"capture; {len(restrained):,} lean(s) the market moved against were "
        f"halved before the edge bar (a move of at least {MIN_MOVE_PROB:.0%} on a "
        f"moneyline or {MIN_MOVE_POINTS:g} point(s) on a spread or total)."
    )
    return Restraint(out, restrained, line)
