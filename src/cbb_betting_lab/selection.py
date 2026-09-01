"""The one function that builds every join key, and the vocabulary it uses.

The NHL lab's join-vocabulary bug family reached **five members** and cost
weeks. Every one of them was two hand-built copies of a key disagreeing:

1. provider team names against league abbreviations;
2. UTC dates against league game dates — 69% of every bought price silently
   discarded, and the survivors were systematically the afternoon games;
3. `home -1.5` against `home_minus`;
4. three-way outcomes staged in the provider's vocabulary instead of the lab's,
   so every downstream join missed;
5. a CSV round-trip turning an empty player into the string `"nan"` on one side
   of a hand-built key.

So there is one `selection_key`, both sides of every join call it, and the
fixtures call it too. A key that is absent means **no modelled opinion**, which
is different from a probability of zero, and every caller treats it as
different.

## The vocabulary, fixed here so two spellings can never mean one bet

**There is no draw in college basketball**, so there is no three-way to price
and `DRAW` does not exist in this vocabulary. That is a deliberate omission
rather than an oversight: a `draw` selection reaching a key here would be a
staged row from the wrong sport, and it is refused rather than carried.

Yes/no markets are the trap. The provider prices `player_double_double` and
`player_first_basket` as yes/no; this lab prices them as the underlying count
**over 0.5**, in the same vocabulary as every other prop, because it is the
same bet and it settles identically. This is the NHL lab's anytime-scorer bug
ported as a rule: both spellings price identically and settle identically, but
`selection_key` carries the selection string, so two spellings are two keys —
and the card staked one wager twice, published it as two independent best bets
at two different prices, and froze it into the ledger twice.
"""

from __future__ import annotations

from cbb_betting_lab.competitions import Competition
from cbb_betting_lab.season import clean_text, row_slate_date


# Team-market selections.
HOME = "home"
AWAY = "away"
OVER = "over"
UNDER = "under"
HOME_OVER = "home_over"
HOME_UNDER = "home_under"
AWAY_OVER = "away_over"
AWAY_UNDER = "away_under"

#: A yes/no market is the underlying count over this line. One name for one
#: thing, so the two cannot disagree on the same card.
YES_NO_LINE = 0.5

#: Every selection string this lab recognises. A staged row carrying anything
#: else is unparseable and is counted as such — never guessed at. `draw` is
#: deliberately absent: this sport does not have one, and a row claiming
#: otherwise came from somewhere it should not have.
KNOWN_SELECTIONS: frozenset[str] = frozenset(
    {HOME, AWAY, OVER, UNDER, HOME_OVER, HOME_UNDER, AWAY_OVER, AWAY_UNDER}
)

#: Which segment of the game a market settles on. Full-game markets settle
#: **including overtime**; half markets do not. Keeping the segment in the key
#: is what stops a first-half total joining a full-game total's price, and it
#: is why `resolves_ties` differs between them — a half can end level and a
#: full game cannot.
FULL_GAME = "game"
FIRST_HALF = "h1"
SECOND_HALF = "h2"
SEGMENTS: frozenset[str] = frozenset({FULL_GAME, FIRST_HALF, SECOND_HALF})


def selection_key(
    row: object,
    *,
    market: str,
    selection: str,
    line: float | None,
    competition: Competition,
    segment: str = FULL_GAME,
) -> tuple:
    """The one key both sides of the price/probability join build.

    `player` goes through `clean_text` before anything else, because a CSV
    round-trip turns an empty field into NaN — which is truthy, so
    `str(x or "")` yields the literal string `"nan"` and quietly matches
    nothing forever.

    The **slate date** is a component because a staged file spans days: the
    bulk endpoint returns every upcoming game, and two meetings between the
    same schools are two different bets whose tips the guard must judge
    separately. It is the slate date, not the UTC one — a 22:30 Pacific tip is
    tomorrow in Eastern and the day after tomorrow in UTC, and joining on
    either discards it.
    """
    if str(segment) not in SEGMENTS:
        raise ValueError(
            f"Unknown segment {segment!r}. Known: {sorted(SEGMENTS)}. A market "
            "that settles on part of a game must say which part, because a "
            "first half can end level and a full game cannot."
        )
    return (
        str(market),
        str(segment),
        clean_text(getattr(row, "player", "")).casefold(),
        str(getattr(row, "home_team", "")),
        str(getattr(row, "away_team", "")),
        str(selection),
        None if line is None else float(line),
        row_slate_date(row, competition),
    )


def normalise_line(value: object) -> float | None:
    """A line as a float, or None when there is not one.

    None rather than 0.0. A moneyline has no line, and a line of zero is a
    pick'em — two different things that a falsy check would merge.
    """
    if value is None:
        return None
    text = clean_text(value)
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def team_selection(outcome_name: str, home_team: str, away_team: str) -> str | None:
    """`home`, `away`, or None when the outcome names neither school.

    None rather than a guess. The provider names the sides after the schools,
    and a row staged under a school's name misses every downstream join — the
    member of the bug family that was hardest to see because nothing errored.

    A `draw` outcome returns None rather than a selection. There is no draw in
    this sport; a row carrying one is unparseable, and unparseable is a counted
    outcome in the accounting identity rather than a silent drop.
    """
    name = clean_text(outcome_name)
    if not name:
        return None
    if name == clean_text(home_team):
        return HOME
    if name == clean_text(away_team):
        return AWAY
    return None


def over_under_selection(outcome_name: str) -> str | None:
    name = clean_text(outcome_name).casefold()
    if name in {"over", "o"}:
        return OVER
    if name in {"under", "u"}:
        return UNDER
    return None


def team_total_selection(
    outcome_name: str, description: str, home_team: str, away_team: str
) -> str | None:
    """`home_over` … `away_under`.

    Both schools arrive under one provider key, the side in the outcome's
    description and Over/Under in its name. Staged in this lab's vocabulary,
    for the same reason everything else is.
    """
    side = over_under_selection(outcome_name)
    if side is None:
        return None
    school = clean_text(description)
    if school == clean_text(home_team):
        return f"home_{side}"
    if school == clean_text(away_team):
        return f"away_{side}"
    return None


def yes_no_selection(outcome_name: str) -> str | None:
    """`over` for Yes, `under` for No — never `yes`, never `no`.

    This is the NHL lab's anytime-scorer bug, ported as a rule rather than
    rediscovered. `player_double_double`, `player_triple_double` and
    `player_first_basket` all arrive as yes/no and are all the underlying count
    over 0.5.
    """
    name = clean_text(outcome_name).casefold()
    if name == "yes":
        return OVER
    if name == "no":
        return UNDER
    return None
