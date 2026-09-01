"""What slate day a game belongs to, and how CSV-borne text is read.

The provider timestamps a game by tip-off, in UTC. The sport timestamps it by
the Eastern calendar date, and a 20:00 tip in Honolulu is 01:00 Eastern the
following morning and 06:00 UTC the morning after that. Three calendars, one
game — and the sport's own answer, verified against ESPN's filed date over
6,318 games, is the middle one.

The NHL lab measured what happens when two of them meet in a join: **69% of
every price it bought was silently discarded**, and the survivors were
systematically the afternoon games. This module exists so the rule lives in one
place, ported before a single price is fetched rather than after a season of
them is lost.

The timezone and the day boundary come from the competition registry, never
from a literal here.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from cbb_betting_lab.competitions import DAY_BOUNDARY_HOUR, Competition


def slate_date(commence_time: object, competition: Competition) -> str:
    """The slate day a tip-off belongs to, as `YYYY-MM-DD`.

    Eastern, shifted back by the day boundary, so a game tipping after
    midnight Eastern lands on the night it was actually played.

    An unparseable value falls back to its leading ten characters. That is the
    best available guess and it is never silently better than the input — a
    caller that needs to know uses `slate_date_is_derived`.
    """
    text = str(commence_time or "").strip()
    if not text:
        return ""
    candidate = text.replace("Z", "+00:00")
    try:
        moment = datetime.fromisoformat(candidate)
    except ValueError:
        return text[:10]
    if moment.tzinfo is None:
        # No timezone means no conversion is possible, and inventing one would
        # move every late game by a day in whichever direction the guess went.
        return text[:10]
    local = moment.astimezone(competition.timezone)
    return (local - timedelta(hours=DAY_BOUNDARY_HOUR)).date().isoformat()


def slate_date_is_derived(commence_time: object) -> bool:
    """True when `slate_date` genuinely converted rather than truncated.

    A caller joining two sides needs to know which it got: a truncated value is
    a UTC date wearing a slate date's name, and that is the whole bug.
    """
    text = str(commence_time or "").strip()
    if not text:
        return False
    try:
        moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return False
    return moment.tzinfo is not None


def clean_text(value: object) -> str:
    """A CSV-safe string: NaN, None and whitespace all read as empty.

    `str(x or "")` looks like it does this and does not — float NaN is truthy,
    so an empty CSV cell round-trips to the literal string `"nan"`, which then
    matches nothing, resolves nothing, and renders as a player called nan.
    Three copies of that pattern shipped in the NHL lab before its equivalent
    of this function existed, and it was the fifth member of that repository's
    join-vocabulary bug family.
    """
    if value is None:
        return ""
    if isinstance(value, float) and value != value:  # NaN without numpy
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def row_slate_date(row: object, competition: Competition) -> str:
    """The slate day for a price row: commence time, else its recorded date.

    The fallback exists for hand-built frames; real staged rows always carry a
    commence time. `or` cannot express this, because a NaN commence time is
    truthy and `slate_date(nan)` is the string "nan" — which would make two
    meetings between the same clubs on different nights share one key.
    """
    commence = clean_text(getattr(row, "commence_time", ""))
    if commence:
        return slate_date(commence, competition)
    return slate_date(clean_text(getattr(row, "date", "")), competition)


def season_for_slate_date(day: str) -> int:
    """The season a slate day belongs to, labelled by its **ending** year.

    A college basketball season spans two calendar years, so the label is a
    choice — and it is not a free one. **hoopR labels a season by the year it
    ends**: `mbb_schedule_2026.parquet` holds 2025-11-03 to 2026-04-07, and
    `mbb_schedule_2027.parquet` holds the 2026-27 season. Verified by reading
    both files rather than assumed.

    This lab uses the same convention, so a season integer never has to be
    translated at a join. An earlier version of this function labelled by the
    *starting* year, which would have made every `season == 2027` filter on our
    side miss every `season == 2027` row on theirs — the join-vocabulary bug
    family in its purest form, caught before a single row was joined.

    The cut is 1 July: everything from July onward belongs to the season ending
    the following year. Nothing countable is played in June or July, so the
    exact day is arbitrary and only its stability matters.
    """
    text = str(day or "").strip()[:10]
    if len(text) != 10:
        return 0
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return 0
    return moment.year + 1 if moment.month >= 7 else moment.year
