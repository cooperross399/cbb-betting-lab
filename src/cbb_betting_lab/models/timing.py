"""When to take a selection's price (decision 89).

Cooper, 2026-11-08 (*"build the rest"*, the early-line idea of *"DO all 7"*).
Decision 88 measured betting the model's leans earlier and declined it as a
rule: over the archive, a lean placed 14-30 hours before tip closed about a
third of a point worse on spreads than one placed inside ten hours, so on
average the price the card sees improves toward tip rather than leaving. That
is an average. When the market has **already** moved toward the selection since
the event's first capture, the price is leaving, and waiting is what costs.

So the card carries a **When** column, read from the same line-movement
capture `models/line_move.py` reads:

* **Now**: the market has moved at least `line_move`'s minimum toward the
  selection since its first capture, at or before the card. The price the
  card shows is leaving.
* **Near tip**: anything else, including a game the capture holds no move for,
  because the measured average says the price improves toward tip.

Advice only. It changes no probability, no selection, no size and no record,
and it reads only captures stamped at or before the card. Registered as
`bet_timing_2026_11_08`, one per tier, and judged forward: the forward ledger
already keeps each selection's card price and its closing price, which is the
whole of what grading this column needs.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Mapping

from cbb_betting_lab.models import line_move

NOW = "Now"
NEAR_TIP = "Near tip"

EXPLANATION = (
    f"**When** is *{NOW}* where the market has already moved toward the "
    f"selection since its first capture today (at least "
    f"{line_move.MIN_MOVE_PROB:.0%} on a moneyline or "
    f"{line_move.MIN_MOVE_POINTS:g} point(s) on a spread or total), so the price "
    f"is leaving; otherwise *{NEAR_TIP}*, because over the archive the model's "
    "prices improved toward tip on average. Advice only: it moves no "
    "probability, no pick and no size."
)


def advise(row: Mapping, moves: "line_move.Moves | None") -> str:
    """`NOW` or `NEAR_TIP` for one selection row."""
    if moves is None or not moves.by_event:
        return NEAR_TIP
    wager = SimpleNamespace(
        event_id=str(row.get("event_id") or ""),
        market=str(row.get("market") or ""),
        selection=str(row.get("selection") or ""),
        segment=str(row.get("segment") or line_move.FULL_GAME),
        player=str(row.get("player") or ""),
    )
    toward = moves.toward(wager)
    if toward is not None and toward >= line_move.Moves.threshold(wager):
        return NOW
    return NEAR_TIP
