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

**Decision 120 (Cooper, 2026-11-26, *"all 4"*)** read the card's record over
its first 479 graded picks and changed four things, registered first as
`card_bars_2026_11_26`, one per tier:

1. **The heavy-favourite bar is off** (`HEAVY_FAVOURITE_ON`). The card's
   favourites at -150 or shorter beat the close 77% of the time; the bar was
   set on ten picks and was costing the card its best-priced side.
2. **Moneylines lead.** The card's moneylines returned +23% and beat the close
   67% of the time, against an alternate spread that lost 1% to it. When a game
   has more than one side clearing its bar, a moneyline ranks
   `MONEYLINE_RANK_BONUS` ahead of the rest for the one slot a game gets.
3. **A claimed edge above `EDGE_SHRINK_FROM` is distrusted.** Above 8% the
   card's picks beat the close 32% of the time; between 5% and 8%, 59%. For
   ranking, an edge above 8% keeps only `EDGE_SHRINK` of its excess, so a
   believable 6% side wins the game's slot over a 14% claim. No bar is lowered.
4. **Long alternate spreads need more.** A full-game alternate spread priced
   `LONG_ALT_ODDS` or longer needs `LONG_ALT_EDGE` (the +200 to +399 rungs beat
   the close 38% of the time, the +400 rungs went 0-13).

And the evening card's picks on games the morning card did not pick are
sized at `EVENING_NEW_GAME_SIZE` of the card's size (`size_scale`).
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
#: Decision 120: the heavy-favourite bar is off.
HEAVY_FAVOURITE_ON = False

#: Decision 120: full-game alternate spreads at +200 or longer.
LONG_ALT_MARKET = "alternate_spread"
LONG_ALT_ODDS = 200.0
LONG_ALT_EDGE = 0.07

#: Decision 120: ranking only, never a bar.
EDGE_SHRINK_FROM = 0.08
EDGE_SHRINK = 0.25
MONEYLINE_RANK_BONUS = 0.02

#: Decision 120: the evening card's new games are bet at half size.
EVENING_NEW_GAME_SIZE = 0.5

#: Every rule this module can apply, by name. `Bars.rules` names the ones in
#: force; the what-if replay (`reports/card_whatif.py`) switches them one at a
#: time to see what each did to the card's record.
RULES = (
    "high_hold",          # decision 116: 5% on full-game ladders and team totals
    "heavy_favourite",    # decision 116: 4% at -150 or shorter (off since 120)
    "evening_new_game",   # decision 116: 4% on the evening card's new games
    "morning_floor",      # decision 116: no evening re-list below the morning's number
    "long_alt",           # decision 120: 7% on full-game alt spreads at +200 or longer
    "rank",               # decision 120: big edges shrunk, moneylines first, for the slot
    "evening_size",       # decision 120: evening new games at half size
)


def default_rules() -> frozenset:
    """The rules the card applies today."""
    return frozenset(r for r in RULES if r != "heavy_favourite" or HEAVY_FAVOURITE_ON)

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
    rules: frozenset = field(default_factory=default_rules)

    def _has(self, rule: str) -> bool:
        return self.on and rule in self.rules

    def wager_threshold(self, wager) -> float:
        """Every bar that depends on the wager alone."""
        threshold = float(self.base)
        if not self.on:
            return threshold
        if self._has("high_hold") and str(wager.market) in HIGH_HOLD_MARKETS and str(wager.segment) in FULL_GAME:
            threshold = max(threshold, HIGH_HOLD_EDGE)
        if self._has("evening_new_game") and self.card_slot == EVENING and self.morning is not None:
            if _game(wager.home_team, wager.away_team) not in self.morning.games:
                threshold = max(threshold, EVENING_NEW_GAME_EDGE)
        return threshold

    def _long_alt(self, wager) -> bool:
        return str(wager.market) == LONG_ALT_MARKET and str(wager.segment) in FULL_GAME

    def rank_edge(self, wager, edge: float) -> float:
        """The edge the card ranks a game's candidates by (decision 120).

        Never a bar: the threshold is read on the claimed edge. Above
        `EDGE_SHRINK_FROM` only `EDGE_SHRINK` of the excess counts, and a
        moneyline gets `MONEYLINE_RANK_BONUS`.
        """
        edge = float(edge)
        if not self._has("rank"):
            return edge
        if edge > EDGE_SHRINK_FROM:
            edge = EDGE_SHRINK_FROM + EDGE_SHRINK * (edge - EDGE_SHRINK_FROM)
        if str(wager.market) == "moneyline":
            edge += MONEYLINE_RANK_BONUS
        return edge

    def size_scale(self, row) -> float:
        """The share of the card's size this pick is bet at (decision 120)."""
        if not self._has("evening_size") or self.card_slot != EVENING or self.morning is None:
            return 1.0
        if _game(row.get("home_team"), row.get("away_team")) in self.morning.games:
            return 1.0
        return EVENING_NEW_GAME_SIZE

    def morning_floor(self, wager) -> float | None:
        if not self._has("morning_floor") or self.card_slot != EVENING or self.morning is None:
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
        if self._has("heavy_favourite") and float(american_odds) <= HEAVY_FAVOURITE_ODDS:
            threshold = max(threshold, HEAVY_FAVOURITE_EDGE)
        if self._has("long_alt") and self._long_alt(wager) and float(american_odds) >= LONG_ALT_ODDS:
            threshold = max(threshold, LONG_ALT_EDGE)
        return threshold

    def bet_down_to(self, probability: object, wager, *, price_band: tuple[float, float]) -> int | None:
        """The worst price that still clears every bar above for this wager."""
        from cbb_betting_lab.reports.card_pricing import bet_down_to as _bet_down_to

        base = self.wager_threshold(wager)
        number = _bet_down_to(probability, threshold=base, price_band=price_band)
        if number is None or not self.on:
            return number
        if self._has("long_alt") and self._long_alt(wager) and number >= LONG_ALT_ODDS:
            longer = _bet_down_to(
                probability, threshold=max(base, LONG_ALT_EDGE), price_band=price_band
            )
            number = longer if longer is not None else number
            if number is not None and number < LONG_ALT_ODDS:
                number = int(LONG_ALT_ODDS)
        if self._has("heavy_favourite") and number is not None and number <= HEAVY_FAVOURITE_ODDS:
            heavy = _bet_down_to(
                probability, threshold=max(base, HEAVY_FAVOURITE_EDGE), price_band=price_band
            )
            number = heavy if heavy is not None and heavy <= HEAVY_FAVOURITE_ODDS else int(HEAVY_FAVOURITE_ODDS) + 1
        floor = self.morning_floor(wager)
        if floor is not None and worse_than(number, floor):
            number = int(floor)
        return number
