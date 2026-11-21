"""Three stricter edge bars on the card, set from its own record (decision 116).

Cooper, 2026-11-20 (*"All 4"*). The card's own record (`reports/card_record.py`)
over its first 391 settled picks, and the closing-line alarm over the forward
ledger, pointed at three places where a 2% edge on the card was not an edge:

1. **The alternate ladders and team totals.** Every full-game alternate spread,
   alternate total, team total and alternate team total cell lost 1-4% to the
   closing line in every tier, against a hold the main markets do not carry,
   and the card's alternate team totals went 3-13. A pick there now needs
   `HIGH_HOLD_EDGE` rather than the card's 2%. Cooper does not want markets
   withdrawn (decision 111), so this is a higher bar, never a closure.
2. **Heavy favourites.** A price at `HEAVY_FAVOURITE_ODDS` or shorter needs
   `HEAVY_FAVOURITE_EDGE`. With the trust table at zero in two tiers the card's
   favourites are price shops, and a 2% shop on a -200 price is half a point of
   probability the de-vig can manufacture on its own; the card went 5-5 there.
3. **The evening card's new games.** The evening card lost 15% on the games
   the morning card had no pick on (51-125), and made money where it added to
   a game the morning had already picked. A game the morning card did not
   pick needs `EVENING_NEW_GAME_EDGE` on the evening card. A side the morning
   card already took is re-listed in the evening only at a price no worse than
   the morning's own bet-down-to number.

Each bar only RAISES the card's threshold, so it can remove a selection and
can never add one, and it never touches the allowlist, the forward ledger (which
still freezes every opinion) or the board's leans. `ON = False` turns all three
off. Registered as `card_bars_2026_11_20`, one per tier, before it was built.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Mapping

ON = True

#: Full-game markets whose closing-line value was a demonstrated deficit.
HIGH_HOLD_MARKETS = frozenset(
    {"alternate_spread", "alternate_total_points", "team_total", "alternate_team_total"}
)
FULL_GAME = ("game", "full_game")
HIGH_HOLD_EDGE = 0.05

#: A price this short or shorter is a heavy favourite.
HEAVY_FAVOURITE_ODDS = -150.0
HEAVY_FAVOURITE_EDGE = 0.04

EVENING_NEW_GAME_EDGE = 0.04
EVENING = "evening"


def _game(home: object, away: object) -> tuple[str, str]:
    return (str(home or "").strip(), str(away or "").strip())


def _line(value: object) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return ""
    return "" if math.isnan(number) else f"{number:g}"


@dataclass
class Morning:
    """What the morning card picked on one slate day."""

    games: set = field(default_factory=set)
    #: (home, away, market, segment, selection, line) -> bet-down-to price
    sides: dict = field(default_factory=dict)

    @classmethod
    def from_rows(cls, rows: Iterable[Mapping], *, day: str) -> "Morning":
        out = cls()
        for row in rows:
            if str(row.get("slate_date", "")) != str(day) or str(row.get("card_slot", "")) != "morning":
                continue
            game = _game(row.get("home_team"), row.get("away_team"))
            out.games.add(game)
            key = game + (
                str(row.get("market", "")), str(row.get("segment", "")),
                str(row.get("selection", "")), _line(row.get("line")),
            )
            try:
                floor = float(row.get("bet_down_to"))
                floor = None if math.isnan(floor) else floor
            except (TypeError, ValueError):
                floor = None
            out.sides[key] = floor
        return out


def _payout(american: float) -> float:
    return american / 100.0 if american > 0 else 100.0 / -american


def worse_than(price: float, floor: float) -> bool:
    """True when `price` pays less per unit than `floor`."""
    return _payout(float(price)) < _payout(float(floor)) - 1e-12


@dataclass(frozen=True)
class Bars:
    """The card's threshold for one quote, given the slot and the morning card."""

    base: float
    card_slot: str = ""
    morning: Morning | None = None
    on: bool = ON

    def wager_threshold(self, wager) -> float:
        """Every bar that depends on the wager alone."""
        threshold = float(self.base)
        if not self.on:
            return threshold
        if str(wager.market) in HIGH_HOLD_MARKETS and str(wager.segment) in FULL_GAME:
            threshold = max(threshold, HIGH_HOLD_EDGE)
        if self.card_slot == EVENING and self.morning is not None:
            if _game(wager.home_team, wager.away_team) not in self.morning.games:
                threshold = max(threshold, EVENING_NEW_GAME_EDGE)
        return threshold

    def morning_floor(self, wager) -> float | None:
        if not self.on or self.card_slot != EVENING or self.morning is None:
            return None
        key = _game(wager.home_team, wager.away_team) + (
            str(wager.market), str(wager.segment), str(wager.selection), _line(wager.line),
        )
        return self.morning.sides.get(key)

    def threshold(self, wager, american_odds: float) -> float:
        """The edge this quote must clear. Infinite where it may not be taken."""
        threshold = self.wager_threshold(wager)
        if not self.on:
            return threshold
        floor = self.morning_floor(wager)
        if floor is not None and worse_than(american_odds, floor):
            return math.inf
        if float(american_odds) <= HEAVY_FAVOURITE_ODDS:
            threshold = max(threshold, HEAVY_FAVOURITE_EDGE)
        return threshold

    def bet_down_to(self, probability: object, wager, *, price_band: tuple[float, float]) -> int | None:
        """The worst price that still clears every bar above for this wager."""
        from cbb_betting_lab.reports.card_pricing import bet_down_to as _bet_down_to

        base = self.wager_threshold(wager)
        number = _bet_down_to(probability, threshold=base, price_band=price_band)
        if number is None or not self.on:
            return number
        if number <= HEAVY_FAVOURITE_ODDS:
            heavy = _bet_down_to(
                probability, threshold=max(base, HEAVY_FAVOURITE_EDGE), price_band=price_band
            )
            number = heavy if heavy is not None and heavy <= HEAVY_FAVOURITE_ODDS else int(HEAVY_FAVOURITE_ODDS) + 1
        floor = self.morning_floor(wager)
        if floor is not None and worse_than(number, floor):
            number = int(floor)
        return number
