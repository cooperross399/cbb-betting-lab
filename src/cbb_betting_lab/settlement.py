"""Grading one staged wager against the box score, and the five ways that goes wrong.

Cooper's rule from `markets.py` is that a market nothing can settle is not
wired. This is the other half of it: **every wired market is settled here, by
name, against a real column in a real processed table**, and a market that
cannot be settled from those tables says so out loud instead of returning a
number.

There are five outcomes rather than three, and the two extra ones are the whole
point of the module:

* :data:`Outcome.VOID` — the book returned the stake. A real verdict with zero
  profit and loss; it belongs in the bet count.
* :data:`Outcome.UNSETTLEABLE` — **this lab cannot grade it.** Not a verdict at
  all. It is never folded into a record, and it is never quietly a loss.

Collapsing either into `LOST` is how a ledger acquires a constant negative
offset that no amount of modelling can explain, and neither collapse looks
wrong in a report.

## 1. Dispatch is on the named quantity, never on the market key

`settle` reads `Market.settles_on` and hands the wager to the handler
registered for that quantity. There is no `if market == "spread"` anywhere in
this file, and there cannot be: :data:`_HANDLERS` is checked against
`markets.MARKETS` **at import**, so wiring a new market without settling it
fails the build at the first import rather than at the first bet.

The two facts that a quantity name does not carry are read off the `Market`
itself — `market.segment` says which half, `market.push_possible` says whether
an exact landing is a push — so the moneyline and the spread share one margin
handler and still obey different rules.

## 2. NaN is silent poison, and this is where it gets in

See :func:`_finite_line`. It is the single most dangerous value in this file.

## 3. A full game cannot end level. A half can, and often does.

Measured over every game in `data/processed/cbb_team_games.csv` — 47,097 games
across seasons 2019 through 2026:

* **full-game margin of exactly zero: 0 of 47,097 (0.0000%).** This sport plays
  overtime until somebody wins. So `moneyline` carries `push_possible=False`
  and has **no path to PUSH** in this module.
* **overtime: 2,450 of 47,097 (5.20%)**; on the completed 2025-26 season, 327
  of 6,299 (5.19%). Full-game markets settle including it.
* **first half level: 1,605 of 45,383 games that record a halftime score
  (3.54%)**; 2025-26 alone, 241 of 6,274 (3.84%). This is the same measurement
  `CLAUDE.md` records as 3.54% over 90,766 halves — that denominator counts the
  two team-rows of each game separately, and the rate is identical.
* **second half level: 1,785 of 45,383 (3.93%)**; 2025-26, 218 of 6,274
  (3.47%).

That gap is the defect `markets.py` records against the football lab, which
priced a level half at 0.4% because its distribution hardcoded the full-game
rule — measured there at 7.4% of halves against 0.35% of games. The college
basketball numbers are different (3.54% and 0.00%) and the shape is identical:
**a half-market push branch that is never reached is a mispriced market, and a
full-game push branch that is reached is a corrupted row.** So `moneyline_h1`
and `moneyline_h2` push on a level half, `moneyline` cannot, and a full game
that somehow arrives level is :data:`Outcome.UNSETTLEABLE` rather than silently
awarded to one side.

## 4. The second half is `final − halftime`, and that is a book's rule

`team_score_h2` is the final score minus the halftime score, so **it contains
overtime**. Verified: `team_score_h1 + team_score_h2 == team_score` on 45,383
of 45,383 games that record a halftime (100.00%), overtime games included.

`SECOND_HALF_INCLUDES_OVERTIME` is wired `True` because that is the majority US
convention — and it is **a book rule this lab cannot verify.** No feed here
carries any book's rulebook. Every second-half number this module produces
carries that ambiguity, it is listed in `docs/cbb_data_sources.md`, and a book
that grades second halves in regulation only would put a constant offset
through 3.9% of second-half moneylines and every second-half total on the 5.20%
of games that go to overtime.

## 5. A did-not-play is a returned stake, not a losing bet

**69,344 of the 196,876 player rows in the 2025-26 file are did-not-play rows**
(35.22%), and every one of them stores `double_double = 0` and null points.
Graded naively, all 69,344 are losing overs. That is not a small bias: it is a
third of the player table voting against every over ever staged.

So `did_not_play` is checked before any comparison and returns
:data:`Outcome.VOID`. **This is an assumption, and a large one.** It assumes
the book voids a prop on a player who does not play. Most US books do for
counting props; some grade a listed player who is a healthy scratch as a loss
on the under; none of that is readable from anything this lab has. It is
recorded here as an assumption rather than presented as a settlement rule, and
`docs/cbb_data_sources.md` carries it beside the second-half ambiguity.

## 6. The row must be the side the selection names

`game` is a **`cbb_team_games.csv` row from the perspective of the side the
selection names** — see :func:`settle` for the exact contract. Every quantity
in that table is already signed for the row's own team, so passing the wrong
row settles the wrong team's bet and nothing errors: the margin is negated, the
team total is the opponent's, and the record looks plausible.

That is the NHL lab's join-vocabulary bug family, and this module refuses to
join for the caller. When the selection names a side and `home_away` disagrees
with it, the answer is :data:`Outcome.UNSETTLEABLE`. **It is deliberately not
flipped**: flipping would settle correctly for a caller that always passes the
home row and would hide the caller that joined the wrong game entirely, and the
second failure is the one that costs a season.

## What cannot be settled from these tables, stated rather than faked

* **`championship_winner` (`tournament_champion`) — never.** Its settlement
  table is `tournament_results`, and there is no such file. Nothing in
  `cbb_team_games.csv` flags an NCAA tournament game, and deriving a champion
  from "the winner of the last game of the season" would invent a settlement
  rule. Always :data:`Outcome.UNSETTLEABLE`.
* **`player_first_team_basket` — about half the time.** `cbb_game_segments.csv`
  records the scorer of the **game's** first basket and that scorer's team, and
  nothing about the other team's first basket. When the player's team scored
  the game's first basket the market settles exactly; otherwise it does not.
  Measured on 2025-26: settleable on **63,527 of 126,968 (50.03%)** played
  player-game rows that have a segment row.
* **Half markets on 1,714 of 47,097 games (3.64%)** that record no halftime
  score at all — 25 of 6,299 in 2025-26 (0.40%), the rest concentrated in the
  older seasons. Missing, not zero.
* **Both first-basket markets on 1,706 of 47,097 games (3.62%)** with no
  `cbb_game_segments.csv` row. Where a row exists, the first-basket scorer is
  present on 45,391 of 45,391 (100.00%).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Callable, Mapping

from cbb_betting_lab.markets import (
    DOUBLE_CATEGORIES,
    DOUBLE_FIGURES,
    MARKETS,
    MARKETS_BY_KEY,
    PLAYER,
    SECOND_HALF_INCLUDES_OVERTIME,
    Market,
)
from cbb_betting_lab.season import clean_text
from cbb_betting_lab.selection import (
    AWAY,
    FIRST_HALF,
    HOME,
    OVER,
    SECOND_HALF,
    SEGMENTS,
    UNDER,
)


class Outcome(str, Enum):
    """What happened to one staked wager.

    Five values, because three would force two different kinds of nothing into
    a loss. `VOID` is the book's verdict and belongs in the bet count with zero
    profit; `UNSETTLEABLE` is this lab's admission and belongs in the exclusion
    count, never in a record.
    """

    WON = "won"
    LOST = "lost"
    #: The quantity landed exactly on the line. Only reachable on a market
    #: whose `push_possible` says it can.
    PUSH = "push"
    #: The book returned the stake. Today this means one thing — a prop on a
    #: player who did not play — and that is an assumption, stated in the
    #: module docstring and in `_player_prop`.
    VOID = "void"
    #: **Not a verdict.** This lab could not grade the wager from the processed
    #: tables. Counted and stated; never a loss, never a pass, never an avoid.
    UNSETTLEABLE = "unsettleable"


#: The outcomes a book actually returns. `UNSETTLEABLE` is deliberately absent:
#: it is the accounting identity's `unparseable`/`ambiguous` bucket, not a bet.
GRADED: frozenset[Outcome] = frozenset(
    {Outcome.WON, Outcome.LOST, Outcome.PUSH, Outcome.VOID}
)


def is_graded(outcome: Outcome) -> bool:
    """True when the outcome is a book's verdict and counts as a settled bet."""
    return outcome in GRADED


@dataclass(frozen=True)
class Settled:
    """One graded wager: the verdict, the quantity it was graded on, and why.

    `actual` is the quantity named by `Market.settles_on`, **not** the
    handicapped comparison value. A spread that lost by a point still reports
    the margin, because the margin is what the box score says and the handicap
    is what the ticket says; a report that stores the adjusted number cannot
    later re-grade the same game at a different rung of the ladder.
    """

    outcome: Outcome
    #: The settled quantity; **None when unsettleable**, enforced below.
    actual: float | None
    #: Why, when the verdict is not obvious from the numbers. Required for
    #: `VOID` and `UNSETTLEABLE`, because both are claims about something the
    #: box score does not say, and an unexplained one is unauditable.
    note: str = ""

    def __post_init__(self) -> None:
        if self.outcome is Outcome.UNSETTLEABLE and self.actual is not None:
            raise ValueError(
                "An unsettleable wager carries no settled quantity. Reporting "
                f"actual={self.actual!r} beside it invites a caller to compare "
                "it to a line and turn an ungraded row into a graded one."
            )
        if self.outcome in (Outcome.UNSETTLEABLE, Outcome.VOID) and not self.note:
            raise ValueError(
                f"Outcome {self.outcome.value!r} must carry a note. It is a "
                "claim about something the box score does not state, and an "
                "unexplained one cannot be audited or overturned."
            )


def _cannot(note: str) -> Settled:
    """The only way an `UNSETTLEABLE` is built, so it always carries a reason."""
    return Settled(Outcome.UNSETTLEABLE, None, note)


# --------------------------------------------------------------------------
# Reading values out of a row, in the two shapes callers actually hold.
# --------------------------------------------------------------------------


def _field(row: object, name: str) -> object:
    """One column, from a Mapping, a pandas Series, or an itertuples row.

    Written once rather than at every call site: `population.classify_venue`
    grew the same three-line accessor inline, and two copies of a row reader
    disagree the first time one of them is asked for a column that is absent.
    """
    if row is None:
        return None
    if hasattr(row, "get"):
        try:
            return row.get(name)  # type: ignore[call-arg]
        except TypeError:
            return None
    return getattr(row, name, None)


def _number(row: object, name: str) -> float | None:
    """A column as a finite float, or None when it is absent or unreadable.

    None, never 0.0. A missing halftime score and a scoreless half are not the
    same fact, and 1,714 of 47,097 games (3.64%) record no halftime at all —
    reading those as 0-0 would settle every first-half under as a winner on
    3.64% of the population, which is a large enough share to carry a headline.
    """
    value = _field(row, name)
    if value is None:
        return None
    if isinstance(value, str):
        text = clean_text(value)
        if not text:
            return None
        value = text
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _is_true(row: object, name: str) -> bool | None:
    """A boolean column as True/False, or None when it cannot be read.

    A CSV round-trip turns `True` into the string `"True"`, and `bool("False")`
    is `True`. That is the shape of the bug this function exists to prevent:
    `did_not_play` read with `bool()` marks the 127,532 players who **did**
    play in 2025-26 as absent and voids the entire prop book.
    """
    value = _field(row, name)
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return bool(value)
    text = clean_text(value).casefold()
    if text in {"true", "t", "yes", "y", "1"}:
        return True
    if text in {"false", "f", "no", "n", "0"}:
        return False
    return None


def _same_id(left: object, right: object) -> bool | None:
    """Whether two identifiers are the same one. None when either is missing.

    Identifiers arrive as `3149059`, `3149059.0` and `"3149059.0"` in the same
    afternoon — the athlete id is a float column in `cbb_player_games.csv` and
    an int in a staged row. Compared as text, those three are three different
    players, which is the join-vocabulary bug family wearing an id instead of a
    team name.
    """
    left_text, right_text = clean_text(left), clean_text(right)
    if not left_text or not right_text:
        return None
    try:
        return float(left_text) == float(right_text)
    except (TypeError, ValueError):
        return left_text.casefold() == right_text.casefold()


# --------------------------------------------------------------------------
# The line, and the reason this function exists at all.
# --------------------------------------------------------------------------


def _finite_line(line: object) -> float | None:
    """The line as a finite float, or None — and **None must never be compared.**

    NaN is silent poison. Every comparison against it is False, in both
    directions, so it does not raise, warn, or produce an obviously wrong
    number. It produces a *plausible* wrong number.

    Concretely, the natural way to write an over/under comparison is

        difference = actual - line
        won = (difference > 0) == (direction is OVER)

    With a NaN line the difference is NaN, `NaN > 0` is False, and so **an
    absent line settles `under` as a win and `over` as a loss** — every single
    time, on every row where the line went missing. A store that lost its lines
    in a CSV round-trip reads back as a profitable under strategy with a
    perfectly clean interval, and nothing anywhere raises.

    So the line is resolved here, once, before any comparator sees it, and a
    line that is None, empty, NaN or infinite makes the wager
    :data:`Outcome.UNSETTLEABLE` instead. A wager whose line cannot be read is
    a wager nobody can describe, and ambiguity falls on the not-settled side.
    """
    if line is None:
        return None
    if isinstance(line, str):
        text = clean_text(line)
        if not text:
            return None
        line = text
    try:
        value = float(line)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return None
    return value if math.isfinite(value) else None


def _is_head_to_head(provider_key: str) -> bool:
    """The provider's head-to-head family: `h2h`, `h2h_h1`, `h2h_h2`.

    A rule rather than a list, matching the provider's own suffix convention,
    so a segment wired later gets the right answer without an edit here. The
    test pins the consequence: exactly `moneyline`, `moneyline_h1` and
    `moneyline_h2` carry no line today, and every other wired market does.
    """
    key = str(provider_key)
    return key == "h2h" or key.startswith("h2h_")


def takes_a_line(market: Market) -> bool:
    """Whether a market's wager carries a handicap or a total to compare against.

    Derived from the provider's own naming convention rather than from a list
    of this lab's market keys, so that a market wired tomorrow gets the right
    answer without anybody remembering to edit this file.

    It matters because `selection.normalise_line` returns None both for *a
    moneyline, which has no line* and for *a line that could not be read*. Those
    are the same value and opposite facts. This predicate is what separates
    them: a moneyline with no line is graded on the raw margin; a spread with no
    line is :data:`Outcome.UNSETTLEABLE`.
    """
    return not all(_is_head_to_head(key) for key in market.provider_keys)


# --------------------------------------------------------------------------
# The selection vocabulary, read rather than guessed at.
# --------------------------------------------------------------------------


def _side_of(selection: str) -> str | None:
    """`home` or `away`, or None when the selection names neither.

    None rather than a default. `draw` lands here from a staged row that came
    from the wrong sport — there is no draw in college basketball and
    `selection.KNOWN_SELECTIONS` deliberately has no entry for one — and a
    default would grade it as an away bet.
    """
    text = clean_text(selection).casefold()
    return text if text in {HOME, AWAY} else None


def _direction_of(selection: str) -> str | None:
    """`over` or `under`, or None. Yes/no markets arrive already staged as these.

    `selection.yes_no_selection` turns Yes into `over` and No into `under`
    upstream, so a double-double and a points prop reach this module in one
    vocabulary and settle through one comparator. That is the NHL lab's
    anytime-scorer defect closed at the settlement end as well as the staging
    end: two spellings of one bet would otherwise settle twice.
    """
    text = clean_text(selection).casefold()
    return text if text in {OVER, UNDER} else None


def _side_and_direction(selection: str) -> tuple[str | None, str | None]:
    """`home_over` -> (`home`, `over`). Split on the **last** underscore.

    `rsplit("_", 1)` and not `split("_")`. The direction is the one component
    that can never contain an underscore; the side is not guaranteed to be.
    A left split reads `home_over` correctly today and would silently
    mis-parse the first side whose name has an underscore in it — and a
    mis-parsed side settles the opponent's team total, which is a plausible
    number and the wrong bet.
    """
    parts = clean_text(selection).casefold().rsplit("_", 1)
    if len(parts) != 2:
        return None, None
    side, direction = parts
    return (side if side in {HOME, AWAY} else None,
            direction if direction in {OVER, UNDER} else None)


def _row_is_the_named_side(game: object, side: str) -> bool | None:
    """Whether the team-games row belongs to the side the selection names.

    None when `home_away` cannot be read, which is treated as a failure like
    any other ambiguity. See the module docstring, section 6: the row is not
    flipped to match, because flipping hides the caller that joined the wrong
    game.
    """
    text = clean_text(_field(game, "home_away")).casefold()
    if text not in {HOME, AWAY}:
        return None
    return text == side


_WRONG_SIDE = (
    "the team-games row is not the side this selection names. `game` must be "
    "the row of the team the wager is on: every quantity in cbb_team_games.csv "
    "is signed for its own team, so settling the other row negates the margin "
    "and swaps the team total, and nothing raises. Not flipped on purpose — "
    "flipping would hide a caller that joined the wrong game."
)


# --------------------------------------------------------------------------
# The two comparators. Everything numeric goes through one of them.
# --------------------------------------------------------------------------


def _grade_against_line(
    actual: float, line: float, direction: str, market: Market
) -> Settled:
    """`over`/`under` against a line, with exact equality first.

    Equality is tested **before** the inequality rather than falling out of an
    `else`, so a push is a decision this function made rather than a case it
    failed to reach — and so a market that says it cannot push (`push_possible`
    False) can refuse the landing instead of quietly awarding it.
    """
    if actual == line:
        if market.push_possible:
            return Settled(Outcome.PUSH, actual, "landed exactly on the line")
        return _cannot(
            f"{market.key} declares push_possible=False and the quantity "
            f"landed exactly on {line:g}. Awarding this to either side would "
            "invent a rule the market says it does not have."
        )
    won = (actual > line) if direction == OVER else (actual < line)
    return Settled(Outcome.WON if won else Outcome.LOST, actual)


def _grade_margin(
    margin: float, handicap: float, market: Market, *, quantity: str
) -> Settled:
    """A side wager: `margin + handicap` against zero.

    The margin is already signed for the side the selection names, so the
    moneyline is exactly the spread at a handicap of zero and there is one
    branch rather than two. What differs is only whether a landing on zero is a
    push, and that comes off the market: `moneyline` says no (0 of 47,097 full
    games ended level), `moneyline_h1` and `moneyline_h2` say yes (1,605 and
    1,785 of 45,383 halves did, 3.54% and 3.93%).

    `actual` is the raw margin, not the adjusted one — see :class:`Settled`.
    """
    adjusted = margin + handicap
    if adjusted == 0:
        if market.push_possible:
            return Settled(Outcome.PUSH, margin, "landed exactly on the line")
        return _cannot(
            f"{market.key} settles on {quantity} and declares "
            f"push_possible=False, but margin {margin:g} against handicap "
            f"{handicap:g} lands exactly level. Measured over 47,097 games, a "
            "full-game margin of zero has never happened — this sport plays "
            "overtime until somebody wins — so this row contradicts the sport "
            "and is not graded."
        )
    return Settled(Outcome.WON if adjusted > 0 else Outcome.LOST, margin)


# --------------------------------------------------------------------------
# The wager, as one object, so every handler has the same signature.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _Ask:
    market: Market
    segment: str
    selection: str
    line: object
    game: object
    player: object


Handler = Callable[[_Ask], Settled]


def _half_columns(segment: str) -> tuple[str, str] | None:
    """The (team, opponent) score columns for a half, or None.

    First half is the halftime score. **Second half is `final − halftime`, so
    it contains overtime** — verified as an identity on 45,383 of 45,383 games
    with a halftime score (100.00%), overtime games included. That is
    `SECOND_HALF_INCLUDES_OVERTIME`, and it is a **book rule this lab cannot
    verify**: no feed here carries any book's rulebook, and a book grading
    second halves in regulation only would be graded wrong on the 5.20% of
    games (2,450 of 47,097) that go to overtime.
    """
    if segment == FIRST_HALF:
        return "team_score_h1", "opponent_score_h1"
    if segment == SECOND_HALF:
        if not SECOND_HALF_INCLUDES_OVERTIME:  # pragma: no cover - wired True
            return None
        return "team_score_h2", "opponent_score_h2"
    return None


_NO_HALFTIME = (
    "this game records no halftime score. 1,714 of 47,097 games (3.64%) do "
    "not, concentrated in the older seasons — 25 of 6,299 in 2025-26 (0.40%). "
    "A missing half is missing, not nil-nil: reading it as 0-0 would settle "
    "every first-half under as a winner across 3.64% of the population."
)


# --------------------------------------------------------------------------
# Team quantities.
# --------------------------------------------------------------------------


def _settle_game_margin(ask: _Ask) -> Settled:
    """`game_margin` — the moneyline, the spread and the spread ladder.

    Settles **including overtime**, which is what `cbb_team_games.margin`
    already is: 2,450 of 47,097 games (5.20%) reach it.
    """
    side = _side_of(ask.selection)
    if side is None:
        return _cannot(
            f"{ask.market.key} is a side market and {ask.selection!r} names "
            "neither side. There is no draw in this sport, so a selection that "
            "is not home or away came from somewhere it should not have."
        )
    if _row_is_the_named_side(ask.game, side) is not True:
        return _cannot(_WRONG_SIDE)
    handicap = _handicap(ask)
    if handicap is None:
        return _cannot(_NO_LINE.format(market=ask.market.key))
    margin = _number(ask.game, "margin")
    if margin is None:
        team = _number(ask.game, "team_score")
        opponent = _number(ask.game, "opponent_score")
        if team is None or opponent is None:
            return _cannot("this game records no final score.")
        margin = team - opponent
    return _grade_margin(margin, handicap, ask.market, quantity="game_margin")


def _settle_half_margin(ask: _Ask) -> Settled:
    """`half_margin` — the half moneylines, half spreads and their ladders.

    **This is the one that pushes.** A half can end level and a full game
    cannot: 1,605 of 45,383 first halves (3.54%) and 1,785 (3.93%) of second
    halves end level, against 0 of 47,097 full games. On 2025-26 alone, 241 of
    6,274 first halves (3.84%) and 218 (3.47%) of second halves.
    """
    columns = _half_columns(ask.segment)
    if columns is None:
        return _cannot(_WRONG_SEGMENT.format(market=ask.market.key, segment=ask.segment))
    side = _side_of(ask.selection)
    if side is None:
        return _cannot(
            f"{ask.market.key} is a side market and {ask.selection!r} names "
            "neither side."
        )
    if _row_is_the_named_side(ask.game, side) is not True:
        return _cannot(_WRONG_SIDE)
    handicap = _handicap(ask)
    if handicap is None:
        return _cannot(_NO_LINE.format(market=ask.market.key))
    team = _number(ask.game, columns[0])
    opponent = _number(ask.game, columns[1])
    if team is None or opponent is None:
        return _cannot(_NO_HALFTIME)
    return _grade_margin(
        team - opponent, handicap, ask.market, quantity="half_margin"
    )


def _settle_game_total(ask: _Ask) -> Settled:
    """`game_total` — the total and the total ladder, **including overtime**.

    Overtime is the whole reason a full-game total is not a first-half total
    doubled: 5.20% of games (2,450 of 47,097) add a period, and every one of
    them adds points to a number an over/under is graded on.
    """
    direction = _direction_of(ask.selection)
    if direction is None:
        return _cannot(_NOT_OVER_UNDER.format(
            market=ask.market.key, selection=ask.selection))
    line = _finite_line(ask.line)
    if line is None:
        return _cannot(_NO_LINE.format(market=ask.market.key))
    total = _number(ask.game, "total")
    if total is None:
        team = _number(ask.game, "team_score")
        opponent = _number(ask.game, "opponent_score")
        if team is None or opponent is None:
            return _cannot("this game records no final score.")
        total = team + opponent
    return _grade_against_line(total, line, direction, ask.market)


def _settle_half_total(ask: _Ask) -> Settled:
    """`half_total` — the half totals and their ladders."""
    columns = _half_columns(ask.segment)
    if columns is None:
        return _cannot(_WRONG_SEGMENT.format(market=ask.market.key, segment=ask.segment))
    direction = _direction_of(ask.selection)
    if direction is None:
        return _cannot(_NOT_OVER_UNDER.format(
            market=ask.market.key, selection=ask.selection))
    line = _finite_line(ask.line)
    if line is None:
        return _cannot(_NO_LINE.format(market=ask.market.key))
    team = _number(ask.game, columns[0])
    opponent = _number(ask.game, columns[1])
    if team is None or opponent is None:
        return _cannot(_NO_HALFTIME)
    return _grade_against_line(team + opponent, line, direction, ask.market)


def _settle_team_score(ask: _Ask) -> Settled:
    """`team_score` — a team total, on the side its selection names.

    The selection is `home_over` … `away_under`: one provider key carries both
    schools, the side in the outcome's description and Over/Under in its name,
    and `selection.team_total_selection` compounds them upstream. Split back
    apart on the **last** underscore.
    """
    side, direction = _side_and_direction(ask.selection)
    if side is None or direction is None:
        return _cannot(
            f"{ask.market.key} is a team total and {ask.selection!r} is not a "
            "side and a direction. Expected one of home_over, home_under, "
            "away_over, away_under."
        )
    if _row_is_the_named_side(ask.game, side) is not True:
        return _cannot(_WRONG_SIDE)
    line = _finite_line(ask.line)
    if line is None:
        return _cannot(_NO_LINE.format(market=ask.market.key))
    score = _number(ask.game, "team_score")
    if score is None:
        return _cannot("this game records no final score.")
    return _grade_against_line(score, line, direction, ask.market)


def _settle_half_team_score(ask: _Ask) -> Settled:
    """`half_team_score` — a half team total, on the side its selection names."""
    columns = _half_columns(ask.segment)
    if columns is None:
        return _cannot(_WRONG_SEGMENT.format(market=ask.market.key, segment=ask.segment))
    side, direction = _side_and_direction(ask.selection)
    if side is None or direction is None:
        return _cannot(
            f"{ask.market.key} is a team total and {ask.selection!r} is not a "
            "side and a direction."
        )
    if _row_is_the_named_side(ask.game, side) is not True:
        return _cannot(_WRONG_SIDE)
    line = _finite_line(ask.line)
    if line is None:
        return _cannot(_NO_LINE.format(market=ask.market.key))
    score = _number(ask.game, columns[0])
    if score is None:
        return _cannot(_NO_HALFTIME)
    return _grade_against_line(score, line, direction, ask.market)


# --------------------------------------------------------------------------
# Player quantities.
# --------------------------------------------------------------------------

#: `settles_on` -> the column in `cbb_player_games.csv` that grades it. One
#: mapping, so a prop cannot be settled against a column its market never
#: named. Every compound is a stored column rather than a sum computed here:
#: verified on 2025-26, `pra`, `points_rebounds`, `points_assists`,
#: `rebounds_assists` and `blocks_steals` equal their parts on 127,532 of
#: 127,532 played rows (100.00%), so the stored column is the same number and
#: recomputing it here would be a second definition free to drift from the one
#: the model is fitted on.
PLAYER_COLUMNS: dict[str, str] = {
    "player_points": "points",
    "player_rebounds": "rebounds",
    "player_assists": "assists",
    "player_threes_made": "three_point_field_goals_made",
    "player_blocks": "blocks",
    "player_steals": "steals",
    "player_turnovers": "turnovers",
    "player_field_goals_made": "field_goals_made",
    "player_free_throws_made": "free_throws_made",
    "player_free_throws_attempted": "free_throws_attempted",
    "player_pra": "pra",
    "player_points_rebounds": "points_rebounds",
    "player_points_assists": "points_assists",
    "player_rebounds_assists": "rebounds_assists",
    "player_blocks_steals": "blocks_steals",
}

_DID_NOT_PLAY = (
    "the player did not play, and this lab settles that as a returned stake "
    "rather than a loss. **That is an assumption about the book's rulebook, "
    "not a fact this lab can read.** Most US books void a counting prop on a "
    "player who does not appear; some grade a healthy scratch as an under. "
    "Nothing in ESPN's feed or in any conference report distinguishes them. "
    "It is assumed rather than left to the default because the default is far "
    "worse: 69,344 of 196,876 player rows in 2025-26 (35.22%) are "
    "did-not-play rows storing null points and double_double=0, so grading "
    "them naively marks a third of the player table as losing overs."
)

_NO_PLAYER_ROW = (
    "no player-games row was supplied. A player prop cannot be settled from a "
    "team row, and guessing zero would grade every prop as a losing over."
)


def _player_guard(ask: _Ask) -> Settled | None:
    """The checks every player prop shares: a row, and whether he played.

    Order matters and is deliberate. The **line** is checked before
    `did_not_play`, because a wager whose line cannot be read is a wager nobody
    can describe, and `VOID` is itself a claim about the book — stacking an
    assumed rulebook on top of an unreadable row asserts more than is known.
    `UNSETTLEABLE` removes the row from the record; `VOID` puts it in with zero
    profit. Ambiguity falls on the not-settled side.
    """
    if ask.player is None:
        return _cannot(_NO_PLAYER_ROW)
    if takes_a_line(ask.market) and _finite_line(ask.line) is None:
        return _cannot(_NO_LINE.format(market=ask.market.key))
    if _is_true(ask.player, "did_not_play") is True:
        return Settled(Outcome.VOID, None, _DID_NOT_PLAY)
    return None


def _settle_player_column(ask: _Ask) -> Settled:
    """Every counting prop: the log column against the line, equality pushes.

    Exact equality is a push because a whole-number line on a counting stat is
    reachable and common — 14 rebounds against a line of 14 is a returned
    stake, not a loss — and `Market.push_possible` is True for all of these.
    """
    guard = _player_guard(ask)
    if guard is not None:
        return guard
    direction = _direction_of(ask.selection)
    if direction is None:
        return _cannot(_NOT_OVER_UNDER.format(
            market=ask.market.key, selection=ask.selection))
    line = _finite_line(ask.line)
    if line is None:  # pragma: no cover - _player_guard already refused
        return _cannot(_NO_LINE.format(market=ask.market.key))
    column = PLAYER_COLUMNS[ask.market.settles_on]
    actual = _number(ask.player, column)
    if actual is None:
        return _cannot(
            f"the player-games row records no {column}, and the player is not "
            "marked did_not_play. A stat that is absent on a player who "
            "appeared is a feed gap, not a zero."
        )
    return _grade_against_line(actual, line, direction, ask.market)


def _double_figure_count(player: object) -> int | None:
    """How many of points, rebounds, assists, steals, blocks reached ten.

    Computed from `markets.DOUBLE_CATEGORIES` and `markets.DOUBLE_FIGURES`
    rather than trusting the stored `double_double` flag, so that the rule this
    lab **declares** is the rule it **settles on**. The stored flag is checked
    against this on every played 2025-26 row by
    `test_settlement_settles_real_games.py`: 127,532 of 127,532 agree
    (100.00%), for both the double-double and the triple-double. If
    `build_datasets` ever changes its definition, that test fails rather than
    the two silently diverging with the ledger following the older one.
    """
    count = 0
    for category in DOUBLE_CATEGORIES:
        value = _number(player, category)
        if value is None:
            return None
        if value >= DOUBLE_FIGURES:
            count += 1
    return count


def _settle_double_figures(ask: _Ask, *, needed: int) -> Settled:
    """A double-double or a triple-double, staged as a count over 0.5.

    Never as yes/no. `selection.yes_no_selection` maps Yes to `over` and No to
    `under` upstream so that one bet has one spelling — the NHL lab staked the
    same anytime-scorer wager twice, once as `yes` and once as `over`, and
    published it as two independent best bets at two different prices.

    The quantity graded is the **indicator**, 1.0 or 0.0, against the staged
    line (0.5). A did-not-play voids: 69,344 of the 196,876 2025-26 player rows
    store `double_double = 0` while never taking the floor, and comparing that
    zero to 0.5 grades a third of the table as losing overs.
    """
    guard = _player_guard(ask)
    if guard is not None:
        return guard
    direction = _direction_of(ask.selection)
    if direction is None:
        return _cannot(_NOT_OVER_UNDER.format(
            market=ask.market.key, selection=ask.selection))
    line = _finite_line(ask.line)
    if line is None:  # pragma: no cover - _player_guard already refused
        return _cannot(_NO_LINE.format(market=ask.market.key))
    count = _double_figure_count(ask.player)
    if count is None:
        return _cannot(
            "the player-games row is missing one of "
            f"{', '.join(DOUBLE_CATEGORIES)}, so the number of double-figure "
            "categories cannot be counted. A missing category is not a "
            "category below ten."
        )
    return _grade_against_line(1.0 if count >= needed else 0.0, line, direction,
                               ask.market)


def _settle_double_double(ask: _Ask) -> Settled:
    """`player_double_double` — two of five categories at ten or more."""
    return _settle_double_figures(ask, needed=2)


def _settle_triple_double(ask: _Ask) -> Settled:
    """`player_triple_double` — three of five. 30 of them in all of 2025-26."""
    return _settle_double_figures(ask, needed=3)


_FIRST_BASKET_COLUMNS = (
    "`game` must be a cbb_game_segments.csv row carrying "
    "first_basket_athlete_id (and first_basket_team_id for the team variant). "
    "1,706 of 47,097 games (3.62%) have no segment row at all; where one "
    "exists the scorer is present on 45,391 of 45,391 (100.00%)."
)


def _first_basket_rows(ask: _Ask) -> tuple[object, object] | Settled:
    """The segment row and the player row, with the join checked rather than assumed.

    When both rows carry a `game_id` and the two disagree, the answer is
    `UNSETTLEABLE`. That check is cheap and it is the one that catches a caller
    that iterated a player frame and a segment frame in different orders —
    which produces a settlement for every row, all of them plausible, and none
    of them about the game they claim.
    """
    guard = _player_guard(ask)
    if guard is not None:
        return guard
    if ask.game is None:
        return _cannot("no game row was supplied. " + _FIRST_BASKET_COLUMNS)
    joined = _same_id(_field(ask.game, "game_id"), _field(ask.player, "game_id"))
    if joined is False:
        return _cannot(
            "the segment row and the player row are for different games. A "
            "first-basket settlement joined across games grades every row and "
            "is wrong on all of them."
        )
    return ask.game, ask.player


def _settle_first_basket(ask: _Ask) -> Settled:
    """`player_first_basket` — did this player score the game's first basket.

    Settled from `cbb_game_segments.first_basket_athlete_id`, which
    `build_datasets` derives from play-by-play as the first row that is a
    scoring play **and** a made field goal. A made free throw is not a basket,
    and the feed spells it `MadeFreeThrow` with no space, so the obvious
    `contains("Free Throw")` filter matches none of the 253,589 free-throw rows
    in a season and this market would settle on whoever made the game's first
    free throw — a plausible name, a real player, and a wrong bet. See
    `tests/test_free_throws_are_not_baskets.py`.

    Measured on 2025-26: 6,268 of 126,968 played player-game rows with a
    segment row (4.94%) are the game's first-basket scorer.
    """
    rows = _first_basket_rows(ask)
    if isinstance(rows, Settled):
        return rows
    game, player = rows
    direction = _direction_of(ask.selection)
    if direction is None:
        return _cannot(_NOT_OVER_UNDER.format(
            market=ask.market.key, selection=ask.selection))
    line = _finite_line(ask.line)
    if line is None:  # pragma: no cover - _player_guard already refused
        return _cannot(_NO_LINE.format(market=ask.market.key))
    scored = _same_id(
        _field(player, "athlete_id"), _field(game, "first_basket_athlete_id")
    )
    if scored is None:
        return _cannot("no first-basket scorer is recorded. " + _FIRST_BASKET_COLUMNS)
    return _grade_against_line(1.0 if scored else 0.0, line, direction, ask.market)


def _settle_first_team_basket(ask: _Ask) -> Settled:
    """`player_first_team_basket` — each team's own first basket.

    This handler was written against a `cbb_game_segments.csv` that recorded
    only the **game's** first basket and its scorer's team. That made the market
    settleable for whichever side happened to score first and unsettleable for
    the other — measured at exactly **50.03% of played rows**, which is the
    shape of a gap that reads as thin coverage and is really a missing column.

    `build_game_segments` now derives `home_first_basket_athlete_id` and
    `away_first_basket_athlete_id` as well, so both sides settle. Present on
    6,275 and 6,272 of 6,275 games in 2025-26; the three missing away rows are
    games where one team scored every field goal in the play stream, and they
    return UNSETTLEABLE rather than a guess.

    The old game-level columns are kept and used as a fallback, because a
    segments file built before this change is still a valid file and settling
    half a market is better than settling none of it.
    """
    rows = _first_basket_rows(ask)
    if isinstance(rows, Settled):
        return rows
    game, player = rows
    direction = _direction_of(ask.selection)
    if direction is None:
        return _cannot(_NOT_OVER_UNDER.format(
            market=ask.market.key, selection=ask.selection))
    line = _finite_line(ask.line)
    if line is None:  # pragma: no cover - _player_guard already refused
        return _cannot(_NO_LINE.format(market=ask.market.key))

    # Which side is this player on? `home_away` is carried on every player row.
    side = str(_field(player, "home_away") or "").strip().lower()
    column = {"home": "home_first_basket_athlete_id",
              "away": "away_first_basket_athlete_id"}.get(side)
    if column is not None and _field(game, column) is not None:
        scored = _same_id(_field(player, "athlete_id"), _field(game, column))
        if scored is not None:
            return _grade_against_line(
                1.0 if scored else 0.0, line, direction, ask.market
            )

    # Fallback for a segments file built before the per-team columns existed.
    same_team = _same_id(
        _field(player, "team_id"), _field(game, "first_basket_team_id")
    )
    if same_team is None:
        return _cannot(
            "the player's team or the first-basket team is missing. "
            + _FIRST_BASKET_COLUMNS
        )
    if not same_team:
        return _cannot(
            "this segments file records only the game's first basket, not each "
            "team's, and the other team scored it. Who scored this team's first "
            "basket is unknown, and unknown is not a loss. Rebuild "
            "cbb_game_segments.csv to settle this market on both sides."
        )
    scored = _same_id(
        _field(player, "athlete_id"), _field(game, "first_basket_athlete_id")
    )
    if scored is None:
        return _cannot("no first-basket scorer is recorded. " + _FIRST_BASKET_COLUMNS)
    return _grade_against_line(1.0 if scored else 0.0, line, direction, ask.market)


# --------------------------------------------------------------------------
# Futures.
# --------------------------------------------------------------------------


def _settle_tournament_champion(ask: _Ask) -> Settled:
    """`tournament_champion` — **this lab cannot settle it, and says so.**

    `championship_winner` names `tournament_results` as its settlement table
    and there is no such file. Nothing in `cbb_team_games.csv` marks a game as
    an NCAA tournament game: there is no round, no bracket, no postseason flag.
    A champion could be *guessed* — the winner of the last game of a season —
    and that guess is exactly the kind of invented settlement rule that
    `markets.py` refuses `player_method_of_first_basket` for.

    Note also that the 2027 tournament is **76 teams and 75 games**, expanded
    from 68 and 67, so even a hand-built results table would need the new
    bracket before it could be trusted.

    A handler exists rather than a gap because the import-time check demands
    one, and because "priced, frozen, and not settleable here" is a fact the
    card must be able to print. It is **not** a pass, an avoid, or a no-value
    call: it is a market this lab prices and cannot grade.
    """
    return _cannot(
        "championship_winner settles on tournament_champion, whose settlement "
        "table (tournament_results) does not exist in this repository. Nothing "
        "in cbb_team_games.csv flags an NCAA tournament game, and deriving a "
        "champion from the last game of a season would invent a settlement "
        "rule. This is not a pass, an avoid or a no-value call: it is a market "
        "the lab prices and cannot grade."
    )


# --------------------------------------------------------------------------
# The registry, and the import-time check that keeps it complete.
# --------------------------------------------------------------------------

_NO_LINE = (
    "{market} needs a line and none could be read. A None, empty, NaN or "
    "infinite line is never compared: NaN comparisons are all False, so a "
    "missing line silently settles every under as a win and every over as a "
    "loss. See _finite_line."
)

_NOT_OVER_UNDER = (
    "{market} is an over/under market and {selection!r} is neither. Yes/no "
    "markets are staged as over/under upstream by "
    "selection.yes_no_selection, so a raw 'yes' reaching here is a staging bug."
)

_WRONG_SEGMENT = (
    "{market} settles on part of a game and the staged segment is {segment!r}. "
    "A first half and a second half are different bets on different numbers, "
    "and a segment that contradicts its own market is a join defect rather "
    "than a settlement question."
)


def _handicap(ask: _Ask) -> float | None:
    """The handicap to add to a margin, or None when the wager cannot be read.

    A moneyline needs none — it is the spread at a handicap of zero — and a
    spread that lost its line is unsettleable. :func:`takes_a_line` is what
    tells those two apart, because `selection.normalise_line` returns None for
    both *a market with no line* and *a line that could not be read*.

    **Zero here is not a fallback.** It is returned only for a market that
    genuinely has no handicap; a spread with an unreadable line returns None
    and is refused, never quietly graded as a pick'em.
    """
    if not takes_a_line(ask.market):
        return 0.0
    return _finite_line(ask.line)


_HANDLERS: dict[str, Handler] = {
    "game_margin": _settle_game_margin,
    "half_margin": _settle_half_margin,
    "game_total": _settle_game_total,
    "half_total": _settle_half_total,
    "team_score": _settle_team_score,
    "half_team_score": _settle_half_team_score,
    "player_double_double": _settle_double_double,
    "player_triple_double": _settle_triple_double,
    "player_first_basket": _settle_first_basket,
    "player_first_team_basket": _settle_first_team_basket,
    "tournament_champion": _settle_tournament_champion,
    **{quantity: _settle_player_column for quantity in PLAYER_COLUMNS},
}


def settleable_quantities() -> frozenset[str]:
    """Every `settles_on` this module has a handler for."""
    return frozenset(_HANDLERS)


_UNHANDLED = sorted({market.settles_on for market in MARKETS} - set(_HANDLERS))
if _UNHANDLED:
    raise RuntimeError(
        "settlement.py has no handler for these settlement quantities, which "
        f"markets.py wires markets against: {_UNHANDLED}. This raises at "
        "import rather than at the first bet, because a market that is priced, "
        "frozen and then found ungradeable has already spent credits and "
        "already published an opinion. Wire a handler, or defer the market in "
        "markets.DEFERRED_MARKETS with a reason."
    )


def settle(
    *,
    market: str,
    segment: str,
    selection: str,
    line: float | None,
    game: Mapping | None,
    player: Mapping | None = None,
) -> Settled:
    """Grade one staged wager against the box score.

    ## What each argument must be

    `market`
        This lab's market key, from `markets.MARKETS_BY_KEY`. It is used to
        *look up* the market and nothing else; the settlement branch is chosen
        by `Market.settles_on`, so a key this file has never heard of settles
        correctly the moment `markets.py` wires it.

    `segment`
        `game`, `h1` or `h2`, from `selection.SEGMENTS`. It must agree with the
        market's own segment — a staged row that disagrees is a join defect, not
        a settlement question, and it is refused rather than resolved in the
        market's favour.

    `selection`
        This lab's vocabulary: `home`/`away` for side markets, `over`/`under`
        for totals and props, `home_over` … `away_under` for team totals. Yes/no
        markets arrive already staged as `over`/`under`.

    `line`
        The handicap or total. `None` is legitimate **only** for a moneyline
        (see :func:`takes_a_line`); everywhere else a line that is None, empty,
        NaN or infinite makes the wager unsettleable rather than compared.

    `game`
        For every team market: **a `cbb_team_games.csv` row from the perspective
        of the side the selection names.** That is one row per team-game, so a
        game supplies two of them; the wager on the away side is settled from
        the away row. Every quantity in that row — `margin`, `team_score`,
        `team_score_h1`, `team_score_h2` — is already signed for that row's own
        team, and `home_away` is checked against the selection so the wrong row
        is refused instead of quietly negating the margin. For an over/under on
        a game total either row will do, because the total is symmetric, and
        `home_away` is not consulted.

        For the two first-basket markets it is instead **a
        `cbb_game_segments.csv` row** — one per game — carrying
        `first_basket_athlete_id` and `first_basket_team_id`. For every other
        player prop it is unused and may be None.

    `player`
        A `cbb_player_games.csv` row, required for every player market.

    ## What comes back

    A :class:`Settled`. `WON`, `LOST` and `PUSH` are the book's verdicts;
    `VOID` is a returned stake and counts as a settled bet with no profit;
    `UNSETTLEABLE` is this lab admitting it cannot grade the row and must never
    be counted as a loss, a pass, or an avoid.
    """
    wired = MARKETS_BY_KEY.get(str(market))
    if wired is None:
        return _cannot(
            f"{market!r} is not a wired market. markets.py names every market "
            "this lab prices and DEFERRED_MARKETS names every one it does not; "
            "a key in neither arrived from somewhere unaccounted for, and "
            "guessing a settlement rule for it is how a lab manufactures "
            "evidence."
        )
    staged_segment = clean_text(segment)
    if staged_segment not in SEGMENTS:
        return _cannot(
            f"{staged_segment!r} is not a known segment. Known: "
            f"{sorted(SEGMENTS)}."
        )
    if staged_segment != wired.segment:
        return _cannot(
            _WRONG_SEGMENT.format(market=wired.key, segment=staged_segment)
        )
    if wired.family == PLAYER and player is None:
        return _cannot(_NO_PLAYER_ROW)
    ask = _Ask(
        market=wired,
        segment=staged_segment,
        selection=clean_text(selection).casefold(),
        line=line,
        game=game,
        player=player,
    )
    return _HANDLERS[wired.settles_on](ask)
