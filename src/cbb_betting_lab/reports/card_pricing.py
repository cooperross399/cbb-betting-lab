"""Pricing, and only pricing. Every gate is next door in `gameday_card.py`.

The split is the whole design. A gate that can be reached by two paths is a gate
with a bypass, and **the bypass is always the pricing path** — because pricing is
where the interesting code is, where the optimisation happens, and where a
convenience shortcut looks harmless. So this module can compute an edge, rank a
price and cap an exposure, and it cannot decide that a market is approved, that
a player is available, or that a game has not tipped. Those arrive as arguments,
from `gates.py` and `staging_provider_policy.py`, and :func:`select` refuses
anything it was not handed an affirmative answer for.

## The bars, in this order, with the best price taken last

`approved → the model has an opinion at all → edge ≥ threshold → price band →
availability → tip guard →` **then** the best price among whatever survived.

The order is load-bearing at both ends.

**Approved is first** because an unapproved market must never be priced, ranked
or edged — a number computed for it is a number somebody will eventually read as
an opinion, and this lab's one human decision is which markets may produce one.

**Best price is last** because a bar cleared by a price the card would not have
used is not cleared. Collapse to the best price first and the edge threshold is
judged at a quote that may be outside the price band, may be at a book that
returned a stale row, and is by construction the most flattering number in the
book. Bar the quotes first and the survivors are prices that each cleared every
bar on their own; the best of *those* is the price the card would actually take.
`stores.best_price_per_wager` does the same collapse for the backtest, and it
carries the NHL lab's receipt: counting every book's quote as an independent bet
put 2.83 quotes on every selection and made every interval √2.83 too narrow —
per quote its store called all three team markets demonstrated losses, per wager
all three spanned zero.

## No opinion is not an opinion of zero

`probabilities.get(key)` returning None means the model was never asked, or
could not answer. It is **not** a probability of zero, and the difference is the
difference between "the model declines" and "the model is certain the bet
loses". Every caller here keeps them apart, and `NO_OPINION` is its own counted
bar.

## Correlation is an accounting problem, and this sport makes it a large one

A game's spread, its moneyline, both team totals, the game total and a starter's
points are **one event seen six ways**. Their edges are not additive and their
outcomes are not independent, so exposure is counted per game and per slate,
never per selection, and the caps below are declared in advance:

* :data:`MAX_POSITIONS_PER_GAME` = 1. One game is one event. When more than one
  wager on a game clears every bar, the highest-edge one is kept and the rest
  are **counted** as correlated with a position already taken, never silently
  dropped and never added up.
* :data:`MAX_POSITIONS_PER_SLATE` = 20. Even at one position per game, the
  200-game peak slate measured in `docs/card_cadence.md` would allow two hundred
  positions on a night that `stats.interval_two_way` may well have to cluster as
  a **single** observation, because a model with a shared daily component makes
  a whole slate correlated. Twenty is a ceiling declared before any market was
  measured. It is not a target: the expected number of positions on this card is
  zero, because no market is allowlisted.

Neither cap binds today and both are tested, which is the correct order — a cap
first written on the night it first binds is a cap chosen to fit the night.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from enum import Enum

import pandas as pd

from cbb_betting_lab.competitions import Competition
from cbb_betting_lab.gates import Availability, TipState, can_be_played, can_produce_a_selection
from cbb_betting_lab.markets import MARKETS_BY_KEY, PLAYER
from cbb_betting_lab.season import clean_text
from cbb_betting_lab.selection import (
    FULL_GAME,
    KNOWN_SELECTIONS,
    SEGMENTS,
    normalise_line,
    selection_key,
)

# The one definition of "edge" in this repository, imported rather than copied.
# A second implementation is the football lab's `_bonferroni_factor` defect in
# miniature — four copies, one carrying a rounded constant, and the direction
# two copies drift in is never the conservative one. A rename upstream breaks
# this import loudly at import time; a duplicate would drift silently, and a
# report that disagrees with the ledger about what "edge" means is a report
# whose every number has to be re-derived before it can be read.
from cbb_betting_lab.forward_evidence import expected_value


#: The edge a wager must clear to be a selection rather than an opinion.
#: Declared in advance and equal to `forward_evidence.BET_EDGE_THRESHOLD`, so
#: the card's "bet" and the ledger's "bet" are the same cut. Moving it after
#: seeing a number is the defect this whole repository is arranged against.
EDGE_THRESHOLD = 0.02

#: The band of American prices this card will take, declared in advance.
#:
#: Outside it the arithmetic stops being about the model and starts being about
#: its tails. At −400 a wager stakes four units to win one, so the edge estimate
#: is dominated by exactly the part of the distribution eight seasons of box
#: scores constrain worst; November's high-major-against-low-major games quote
#: past −3000 routinely, and a one-point error in a thirty-point mismatch moves
#: the fair price by more than any measured edge. Above +600 the same holds in
#: reverse. And the practical reason, which matters more: **the largest apparent
#: edges in any price store are the rows that are wrong** — a stale quote, a
#: mis-keyed line, a book's error left hanging — and they all live out here.
PRICE_BAND: tuple[float, float] = (-400.0, 600.0)

#: One game is one event. See the module docstring.
MAX_POSITIONS_PER_GAME = 1
#: And one night may be one observation. See the module docstring.
MAX_POSITIONS_PER_SLATE = 20


class Bar(str, Enum):
    """Why a priced wager did not become a selection. Evaluated in this order.

    An excluded market is **never** a pass, an avoid, or a no-value call, so
    every value here says what the lab could not do rather than what it thinks
    of the bet.
    """

    NOT_APPROVED = "the market is not allowlisted by a reviewed policy"
    NO_OPINION = "the model has no opinion on this selection"
    BELOW_THRESHOLD = "no price on it clears the declared edge threshold"
    OUTSIDE_PRICE_BAND = "every clearing price is outside the declared band"
    AVAILABILITY = "availability cannot be confirmed"
    TIP_GUARD = "the game has tipped, is imminent, or has no readable tip time"
    CORRELATED_GAME = "a position is already taken on this game"
    SLATE_CAP = "the slate's declared position cap is already full"


#: The order the bars are applied in. Written down as data so the test that
#: pins the order reads the same list the code does, rather than asserting
#: against a copy of it.
BAR_ORDER: tuple[Bar, ...] = (
    Bar.NOT_APPROVED,
    Bar.NO_OPINION,
    Bar.BELOW_THRESHOLD,
    Bar.OUTSIDE_PRICE_BAND,
    Bar.AVAILABILITY,
    Bar.TIP_GUARD,
    Bar.CORRELATED_GAME,
    Bar.SLATE_CAP,
)


@dataclass(frozen=True)
class Quote:
    """One book's price on one wager. The book is part of a quote's identity."""

    book: str
    american_odds: float


@dataclass(frozen=True)
class Wager:
    """One bet, and every price on it.

    A wager is the quote identity **minus the book**: the same selection at the
    same line on the same event is one bet however many books hang it. Twenty-one
    books quoting one game is not twenty-one bets.
    """

    key: tuple
    event_id: str
    slate_date: str
    commence_time: str
    home_team: str
    away_team: str
    market: str
    segment: str
    player: str
    selection: str
    line: float | None
    tier: str
    quotes: tuple[Quote, ...]

    @property
    def is_player_market(self) -> bool:
        market = MARKETS_BY_KEY.get(self.market)
        return bool(market and market.family == PLAYER)

    def label(self) -> str:
        """How this wager is named on the card. No handle, ever — see below."""
        line = "" if self.line is None else f" {self.line:+g}"
        who = f" — {self.player}" if self.player else ""
        return (
            f"{self.away_team} at {self.home_team}: {self.market} "
            f"({self.segment}) {self.selection}{line}{who}"
        )


@dataclass
class Exposure:
    """Positions per game and per slate, against the caps declared in advance.

    Reported rather than summed. Cooper's rule: *never stake correlated
    selections as independent, and never sum their edges.*
    """

    per_game: dict[str, int] = field(default_factory=dict)
    per_slate: int = 0
    per_game_cap: int = MAX_POSITIONS_PER_GAME
    per_slate_cap: int = MAX_POSITIONS_PER_SLATE
    games_with_a_position: int = 0
    capped: list[str] = field(default_factory=list)

    def summary_line(self) -> str:
        return (
            f"{self.per_slate:,} position(s) across "
            f"{self.games_with_a_position:,} game(s); the cap is "
            f"{self.per_game_cap} per game and {self.per_slate_cap} per slate. "
            f"{len(self.capped):,} wager(s) cleared every bar and were held "
            "back by a cap. Spread, moneyline, team total, game total and a "
            "player's points are one event seen five ways: these are counted "
            "per game and per slate, and their edges are never summed."
        )


@dataclass
class SelectionResult:
    """What `select` decided, and why everything else did not make it."""

    selections: list[dict] = field(default_factory=list)
    #: Bar value -> the wagers it stopped, grouped. **Grouped by reason, not
    #: listed per market**: with 35 markets over a 200-game slate, one line per
    #: exclusion is seventeen thousand lines of one identical sentence, and
    #: noise on a card is how the line that matters gets skipped.
    barred: dict[str, list[str]] = field(default_factory=dict)
    bar_counts: dict[str, int] = field(default_factory=dict)
    exposure: Exposure = field(default_factory=Exposure)
    priced_wagers: int = 0

    def bar(self, reason: Bar, wager: "Wager") -> None:
        self.barred.setdefault(reason.value, []).append(wager.label())
        self.bar_counts[reason.value] = self.bar_counts.get(reason.value, 0) + 1


def _as_float(value: object) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def default_key_for(competition: Competition) -> Callable[[object], tuple]:
    """The `selection_key` builder both sides of every join must use.

    Injected as a callable rather than imported at each call site so the card,
    the freeze and the probability map agree on the key **by construction**. Two
    hand-built copies of a join key is the NHL lab's five-member bug family, and
    every member of it failed silently.
    """

    def key_for(row: object) -> tuple:
        return selection_key(
            row,
            market=getattr(row, "market", ""),
            selection=getattr(row, "selection", ""),
            line=normalise_line(getattr(row, "line", None)),
            competition=competition,
            segment=clean_text(getattr(row, "segment", "")) or FULL_GAME,
        )

    return key_for


def build_wagers(
    prices: pd.DataFrame | Iterable[Mapping],
    *,
    competition: Competition,
    key_for: Callable[[object], tuple] | None = None,
    tiers: Mapping | None = None,
) -> tuple[list[Wager], int, dict[str, int]]:
    """Group price rows into wagers. Returns `(wagers, unparseable, reasons)`.

    Unparseable rows are **counted and returned**, never dropped: a market key
    this lab does not carry, a selection outside `KNOWN_SELECTIONS`, a segment
    that is not one of the three, or a price that will not read as a number. A
    row that reaches none of those and is not staged has vanished, and a silent
    drop is how a card recommends from a sixth of a slate and reports it as the
    whole one.
    """
    keyer = key_for or default_key_for(competition)
    records = (
        prices.to_dict("records")
        if isinstance(prices, pd.DataFrame)
        else [dict(row) for row in prices]
    )
    grouped: dict[tuple, list] = {}
    order: list[tuple] = []
    unparseable = 0
    reasons: dict[str, int] = {}

    def refuse(reason: str) -> None:
        nonlocal unparseable
        unparseable += 1
        reasons[reason] = reasons.get(reason, 0) + 1

    for record in records:
        row = _row(record)
        if row.market not in MARKETS_BY_KEY:
            refuse("the market is not one this lab wires")
            continue
        if row.segment not in SEGMENTS:
            refuse("the segment is not one of game, h1 or h2")
            continue
        if row.selection not in KNOWN_SELECTIONS:
            refuse("the selection is outside this lab's vocabulary")
            continue
        odds = _as_float(record.get("american_odds"))
        if odds is None or odds == 0.0:
            refuse("the price is missing or unreadable")
            continue
        if not row.event_id or not row.home_team or not row.away_team:
            refuse("the row names no event or no schools")
            continue
        try:
            key = keyer(row)
        except (TypeError, ValueError):
            refuse("the row could not be keyed")
            continue
        if key not in grouped:
            grouped[key] = []
            order.append(key)
            tier = ""
            if tiers:
                found = tiers.get(key, tiers.get(row.event_id))
                tier = clean_text(getattr(found, "value", found))
            grouped[key] = [
                Wager(
                    key=key,
                    event_id=row.event_id,
                    slate_date=row.slate_date,
                    commence_time=row.commence_time,
                    home_team=row.home_team,
                    away_team=row.away_team,
                    market=row.market,
                    segment=row.segment,
                    player=row.player,
                    selection=row.selection,
                    line=row.line,
                    tier=tier or "unplaced",
                    quotes=(),
                ),
                [],
            ]
        grouped[key][1].append(Quote(book=row.book, american_odds=odds))

    wagers = [
        Wager(**{**grouped[k][0].__dict__, "quotes": tuple(grouped[k][1])}) for k in order
    ]
    return wagers, unparseable, reasons


class _Row:
    """A price row with attribute access, normalised once.

    `clean_text` on every text field and `normalise_line` on the line, because a
    CSV round trip turns an empty player into the literal string `"nan"` — NaN
    is truthy, so `str(x or "")` does not catch it — and an empty line into a
    float NaN, which `is not None`. Both make a key that matches nothing
    forever.
    """

    __slots__ = (
        "event_id",
        "commence_time",
        "slate_date",
        "home_team",
        "away_team",
        "market",
        "segment",
        "player",
        "selection",
        "line",
        "book",
    )

    def __init__(self, record: Mapping) -> None:
        self.event_id = clean_text(record.get("event_id"))
        self.commence_time = clean_text(record.get("commence_time"))
        self.slate_date = clean_text(record.get("slate_date"))
        self.home_team = clean_text(record.get("home_team"))
        self.away_team = clean_text(record.get("away_team"))
        self.market = clean_text(record.get("market"))
        self.segment = clean_text(record.get("segment")) or FULL_GAME
        self.player = clean_text(record.get("player"))
        self.selection = clean_text(record.get("selection"))
        self.line = normalise_line(record.get("line"))
        self.book = clean_text(record.get("book"))


def _row(record: Mapping) -> _Row:
    return _Row(record)


def in_price_band(odds: float, band: tuple[float, float] = PRICE_BAND) -> bool:
    """Whether a price is one this card would take. See :data:`PRICE_BAND`."""
    low, high = band
    return low <= float(odds) <= high


def select(
    wagers: Iterable[Wager],
    probabilities: Mapping | None,
    *,
    approved: Callable[[str], bool] | Iterable[str],
    availability_for: Callable[[Wager], Availability] | None = None,
    tip_state_for: Callable[[Wager], TipState] | None = None,
    threshold: float = EDGE_THRESHOLD,
    price_band: tuple[float, float] = PRICE_BAND,
    per_game_cap: int = MAX_POSITIONS_PER_GAME,
    per_slate_cap: int = MAX_POSITIONS_PER_SLATE,
) -> SelectionResult:
    """Turn priced wagers into selections, or into counted reasons why not.

    Every bar is applied in :data:`BAR_ORDER`, and the best price is taken last
    — see the module docstring for why both halves of that sentence are
    load-bearing.

    `approved`, `availability_for` and `tip_state_for` are **arguments**. This
    module cannot compute any of them: an approval comes from a reviewed policy
    with a human acceptance receipt behind it, and availability and tip state
    come from `gates.py`, which fails closed. A missing `availability_for` is
    treated as `NO_REPORT` and a missing `tip_state_for` as `UNCONFIRMED`,
    because ambiguity falls on the not-a-play side, always — a default of "fine"
    here would let a caller clear both gates by forgetting them.
    """
    result = SelectionResult()
    allows = approved if callable(approved) else (lambda m, s=set(approved): m in s)
    probabilities = probabilities if probabilities is not None else {}

    cleared: list[dict] = []
    for wager in wagers:
        result.priced_wagers += 1

        if not allows(wager.market):
            result.bar(Bar.NOT_APPROVED, wager)
            continue

        # An absent key is no modelled opinion. It is not a probability of zero,
        # and treating it as one would turn every unpriced selection into a
        # confident bet against itself.
        probability = _as_float(probabilities.get(wager.key))
        if probability is None:
            result.bar(Bar.NO_OPINION, wager)
            continue

        priced = [
            (quote, expected_value(probability, quote.american_odds))
            for quote in wager.quotes
        ]
        clearing = [(q, e) for q, e in priced if e is not None and e >= threshold]
        if not clearing:
            result.bar(Bar.BELOW_THRESHOLD, wager)
            continue

        in_band = [(q, e) for q, e in clearing if in_price_band(q.american_odds, price_band)]
        if not in_band:
            result.bar(Bar.OUTSIDE_PRICE_BAND, wager)
            continue

        availability = (
            availability_for(wager) if availability_for else Availability.NO_REPORT
        )
        if wager.is_player_market and not can_produce_a_selection(availability):
            result.bar(Bar.AVAILABILITY, wager)
            continue

        state = tip_state_for(wager) if tip_state_for else TipState.UNCONFIRMED
        if not can_be_played(state):
            result.bar(Bar.TIP_GUARD, wager)
            continue

        # Best price last, and only among quotes that cleared every bar on their
        # own. `max` on the edge rather than on the American number: +150 beats
        # −110 beats −200, and a naive numeric sort puts −200 on top.
        best_quote, best_edge = max(in_band, key=lambda pair: pair[1])
        cleared.append(
            {
                "wager": wager,
                "edge": float(best_edge),
                "probability": float(probability),
                "american_odds": float(best_quote.american_odds),
                "book": best_quote.book,
                "quotes": len(wager.quotes),
            }
        )

    result.selections, result.exposure = _apply_exposure_caps(
        cleared, result, per_game_cap=per_game_cap, per_slate_cap=per_slate_cap
    )
    return result


def _apply_exposure_caps(
    cleared: list[dict],
    result: SelectionResult,
    *,
    per_game_cap: int,
    per_slate_cap: int,
) -> tuple[list[dict], Exposure]:
    """Keep the highest-edge position per game, then hold the slate to its cap.

    Ordered by edge descending so the position kept on a game is the one the
    card would have led with. A stable secondary sort on the wager label keeps
    the output identical between two runs over the same input, which is what
    makes `selection_fingerprint` mean anything.
    """
    exposure = Exposure(per_game_cap=per_game_cap, per_slate_cap=per_slate_cap)
    ranked = sorted(cleared, key=lambda c: (-c["edge"], c["wager"].label()))
    kept: list[dict] = []
    for candidate in ranked:
        wager: Wager = candidate["wager"]
        taken = exposure.per_game.get(wager.event_id, 0)
        if taken >= per_game_cap:
            result.bar(Bar.CORRELATED_GAME, wager)
            exposure.capped.append(wager.label())
            continue
        if len(kept) >= per_slate_cap:
            result.bar(Bar.SLATE_CAP, wager)
            exposure.capped.append(wager.label())
            continue
        exposure.per_game[wager.event_id] = taken + 1
        kept.append(
            {
                "event_id": wager.event_id,
                "slate_date": wager.slate_date,
                "commence_time": wager.commence_time,
                "home_team": wager.home_team,
                "away_team": wager.away_team,
                "market": wager.market,
                "segment": wager.segment,
                "player": wager.player,
                "selection": wager.selection,
                "line": wager.line,
                "tier": wager.tier,
                "american_odds": candidate["american_odds"],
                "book": candidate["book"],
                "model_probability": candidate["probability"],
                "edge": candidate["edge"],
                "quotes_seen": candidate["quotes"],
                "label": wager.label(),
            }
        )
    exposure.per_slate = len(kept)
    exposure.games_with_a_position = len(exposure.per_game)
    return kept, exposure


#: What identifies a selection. **Prices and probabilities are not on this
#: list**, and neither is the book.
FINGERPRINT_FIELDS: tuple[str, ...] = (
    "slate_date",
    "event_id",
    "market",
    "segment",
    "player",
    "selection",
    "line",
)


def selection_fingerprint(selections: Iterable[Mapping]) -> str:
    """A digest of *what the card says to do*, excluding what it costs.

    Prices, probabilities, edges and the book are all excluded, on purpose. A
    half-cent move from −110 to −109 is not a changed selection, and a
    fingerprint that treated it as one would fire the `Selections changed`
    marker on essentially every run — which does not make the notification
    noisy, it makes it worthless, because the run where the selection genuinely
    changed looks exactly like the four hundred before it. The EPL lab's
    `@mention` defect is the same shape: a notification that fires when nothing
    happened stops being read long before it stops being sent.

    The **handicap** is in the fingerprint, because a bet at −3.5 and a bet at
    −4.5 settle differently on a four-point win. That is a different bet, not a
    different price.
    """
    rows = sorted(
        "|".join(
            "" if row.get(field_name) is None else str(row.get(field_name, ""))
            for field_name in FINGERPRINT_FIELDS
        )
        for row in selections
    )
    digest = hashlib.sha256()
    for row in rows:
        digest.update(row.encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:16]
