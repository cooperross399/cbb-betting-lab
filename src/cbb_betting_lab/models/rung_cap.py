"""The card does not reach far down an alternate ladder (decision 86).

Cooper, 2026-11-08 (*"DO all 7"*, item 3). Each rung further from the main
line carries more of the book's hold, and the first week of the forward ledger
measured it on every frozen alternate spread at its best price, both sides,
blind: a return of -5.4% within 1.5 points of the main line, -6.1% to 3.5,
-7.1% to 5.5, -7.6% to 8, then -13.1% from 8 to 12 and -17.7% beyond 12
(16,260 settled rows over the week's games). The drop past 8 points is where
the rung stops being a different number and starts being the book's margin.

**The rule.** An alternate spread or alternate total whose line sits more than
`MAX_RUNG_DISTANCE` points from its game's main line is taken off the
probability map the edge bar reads. The main line is the one the most books
quote on the main market for that event on tonight's board; an event with no
main market on the board keeps its ladder, because there is nothing to measure
the distance from. Totals take the same distance by analogy: the forward ledger
graded no total until decision 85, so their ladder could not be measured.

Withdrawal only. It never adds a wager, never touches the allowlist, and never
touches the forward ledger, which still freezes every rung. Registered as
`rung_cap_2026_11_08`, one per tier. `MAX_RUNG_DISTANCE = None` turns it off.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable, Mapping

MAX_RUNG_DISTANCE: float | None = 8.0

#: ladder market -> its main market
LADDERS = {"alternate_spread": "spread", "alternate_total_points": "total_points"}
FULL_GAME = ("game", "full_game")


def _home_line(wager) -> float | None:
    try:
        line = float(wager.line)
    except (TypeError, ValueError):
        return None
    if line != line:
        return None
    selection = str(wager.selection)
    if selection == "home":
        return line
    if selection == "away":
        return -line
    if selection in ("over", "under"):
        return line
    return None


def main_lines(wagers: Iterable) -> dict:
    """(event_id, main market) -> the line the most books quote on tonight's board."""
    counts: dict = {}
    for wager in wagers:
        market = str(wager.market)
        if market not in LADDERS.values() or str(wager.segment) not in FULL_GAME:
            continue
        line = _home_line(wager)
        if line is None:
            continue
        counts.setdefault((str(wager.event_id), market), Counter())[line] += len(wager.quotes)
    return {key: c.most_common(1)[0][0] for key, c in counts.items() if c}


def distance(wager, mains: Mapping) -> float | None:
    """How far a ladder rung sits from its game's main line, or None."""
    main = LADDERS.get(str(wager.market))
    if main is None or str(wager.segment) not in FULL_GAME:
        return None
    centre = mains.get((str(wager.event_id), main))
    line = _home_line(wager)
    if centre is None or line is None:
        return None
    return abs(line - centre)


def apply(probabilities: Mapping, wagers: Iterable) -> tuple[dict, int]:
    """The probability map without the rungs past the cap, and how many went."""
    out = dict(probabilities or {})
    if MAX_RUNG_DISTANCE is None:
        return out, 0
    wagers = list(wagers)
    mains = main_lines(wagers)
    removed = 0
    for wager in wagers:
        if wager.key not in out:
            continue
        far = distance(wager, mains)
        if far is not None and far > MAX_RUNG_DISTANCE:
            del out[wager.key]
            removed += 1
    return out, removed
