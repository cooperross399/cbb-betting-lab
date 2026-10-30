"""Whether a book's own ladder contradicts itself.

Borrowed from the NHL lab's `ladder_coherence.py`, and the one item on the
improvement plan that does not depend on the model being any good: it reads
only the book's prices against each other.

Within one book, one game, one market and one side, a line that is better for
the bettor must cost more. Taking +6.5 is better than taking +5.5, so its
implied probability must be at least as high; an over at 140.5 is better than
an over at 141.5. A quote that is beaten on BOTH the line and the price by
another quote on the same book's ladder is **dominated**: nobody should take
it, and a book hanging one is either stale or mispriced.

**What it is not.** It is a diagnostic printed on the card. It changes no
probability, selects nothing, touches no allowlist and states no edge: a
dominated quote is a fact about a book's ladder, never a claim that the better
rung wins money. It measures no outcome, so it is not a hypothesis and is
not on the experiment ledger; the day a dominated quote is used to choose a
bet, that use is a hypothesis and is registered before it is built.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from cbb_betting_lab.selection import (
    AWAY,
    AWAY_OVER,
    AWAY_UNDER,
    HOME,
    HOME_OVER,
    HOME_UNDER,
    OVER,
    UNDER,
)

#: A higher line is better for the bettor on these sides; a lower one on the
#: rest. A selection in neither has no ladder order and is never read.
HIGHER_IS_BETTER = frozenset({HOME, AWAY, UNDER, HOME_UNDER, AWAY_UNDER})
LOWER_IS_BETTER = frozenset({OVER, HOME_OVER, AWAY_OVER})

#: Implied-probability slack before a pair counts as dominated, so a rounding
#: difference in an American price is never reported as a contradiction.
TOLERANCE = 0.002


def implied(american: float) -> float:
    a = float(american)
    return 100.0 / (a + 100.0) if a > 0 else -a / (-a + 100.0)


@dataclass(frozen=True)
class Dominated:
    event: str
    market: str
    segment: str
    selection: str
    book: str
    line: float
    odds: float
    better_line: float
    better_odds: float

    def describe(self) -> str:
        return (
            f"{self.event}: {self.book} {self.market} ({self.segment}) {self.selection} "
            f"{self.line:+g} at {self.odds:+.0f} is beaten by {self.better_line:+g} at "
            f"{self.better_odds:+.0f}"
        )


def dominated_quotes(wagers: Iterable) -> list[Dominated]:
    """Every quote another rung of the same book's ladder beats on line and price."""
    ladders: dict[tuple, list[tuple[float, float, str]]] = {}
    for wager in wagers:
        if getattr(wager, "player", ""):
            continue
        if wager.line is None or wager.selection not in HIGHER_IS_BETTER | LOWER_IS_BETTER:
            continue
        for quote in wager.quotes:
            key = (wager.event_id, wager.market.replace("alternate_", ""), wager.segment,
                   wager.selection, quote.book)
            label = f"{wager.away_team} at {wager.home_team}"
            ladders.setdefault(key, []).append((float(wager.line), float(quote.american_odds), label))
    out: list[Dominated] = []
    for (event, market, segment, selection, book), rungs in sorted(ladders.items()):
        sign = 1.0 if selection in HIGHER_IS_BETTER else -1.0
        for line, odds, label in rungs:
            for other_line, other_odds, _ in rungs:
                better_line = sign * (other_line - line) > 0
                cheaper = implied(other_odds) < implied(odds) - TOLERANCE
                if better_line and cheaper:
                    out.append(Dominated(label, market, segment, selection, book,
                                         line, odds, other_line, other_odds))
                    break
    return out


def summary_lines(found: list[Dominated], *, ladders_read: bool, limit: int = 10) -> list[str]:
    if not ladders_read:
        return ["No line-bearing quote was on this board, so no ladder was checked."]
    if not found:
        return ["No book's ladder contradicted itself: every better line cost more on the same book."]
    lines = [
        f"**{len(found):,} quote(s) are dominated on their own book's ladder**: another "
        "rung on the same side offers a better line at a better price. This is a "
        "fact about the book's prices and is never an edge or a selection."
    ]
    lines += [f"- {d.describe()}" for d in found[:limit]]
    if len(found) > limit:
        lines.append(f"- and {len(found) - limit:,} more.")
    return lines
