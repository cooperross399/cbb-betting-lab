"""The card's schedule, and the cron lateness it has to survive.

Cooper, 2026-08-31: *"Do not trust the nominal cron time. GitHub has been firing
my repos' crons 4.5-5.3 hours late since 2026-08-27. Check every deadline
against `nominal + OBSERVED_LATENESS_H`."*

This module holds those constants in one place so the workflow, the docs and
the test that proves the schedule works all read the same numbers. Raising
:data:`OBSERVED_LATENESS_H` when GitHub gets worse is a one-line change that
proves itself, because the test recomputes the whole table from it.

The reasoning is in `docs/card_cadence.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

#: Worst lateness observed on Cooper's repositories since 2026-08-27, in hours.
#: Measured, not documented behaviour. Every deadline is checked against
#: `nominal + this`, never against nominal.
OBSERVED_LATENESS_H = 5.3

#: Eastern standard time offset, UTC-5. The college basketball season runs
#: almost entirely in EST, and every figure in `docs/card_cadence.md`'s table
#: is an EST figure.
EST_OFFSET_H = -5

#: Eastern daylight time offset, UTC-4, from 2027-03-14 (02:00 EST, 07:00 UTC)
#: to the end of the season. THE SIGN MATTERS AND THIS FILE HAD IT BACKWARDS:
#: it used to say DST moves every landing an hour *earlier* in ET, "the safe
#: direction". A cron is fixed in UTC, so when the offset shrinks from -5 to -4
#: the same instant reads an hour LATER on an Eastern clock — 10:00 UTC is
#: 05:00 EST on 2027-03-13 and 06:00 EDT on 2027-03-14. Later is the unsafe
#: direction, toward the first tip, and at the worst observed lateness it moves
#: the morning backup from 10:18 ET to 11:18 ET, past its 11:00 ET block. The
#: morning primary (10:18 ET) and both evening triggers still hold. That gap is
#: recorded rather than chased — the crons were not moved for it — and
#: `tests/test_the_card_schedule_survives_cron_lateness.py` pins the sign on
#: those two instants and the gap as written.
EDT_OFFSET_H = -4

EASTERN = ZoneInfo("America/New_York")


def eastern_offset_h(instant: datetime) -> float:
    """The Eastern UTC offset in hours at `instant`, read from the tz database
    rather than from a constant, so the DST direction is measured here and
    never asserted. `instant` must be timezone-aware."""
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("eastern_offset_h needs an aware datetime; a naive one has no instant")
    offset = instant.astimezone(EASTERN).utcoffset()
    assert offset is not None
    return offset.total_seconds() / 3600


def landing_et(cron_hour_utc: float, day: date, lateness_h: float = 0.0) -> float:
    """The Eastern wall-clock hour at which a cron fixed at `cron_hour_utc`
    lands on `day`, `lateness_h` hours late. The offset is the one in force at
    the landing instant, so a run fired after the 07:00 UTC switch on
    2027-03-14 is already an EDT landing."""
    fired = datetime(day.year, day.month, day.day, tzinfo=timezone.utc) + timedelta(
        hours=cron_hour_utc + lateness_h
    )
    return (cron_hour_utc + lateness_h + eastern_offset_h(fired)) % 24

#: A game tipping inside this many minutes of a run is not carded by it.
#: This is the lead the historical store was bought at (T-60,
#: `providers.historical.CARD_WINDOW`) and so the lead every measured number
#: rests on. `gates.IMMINENT_MINUTES` **is** this constant — it imports it —
#: so the per-game tip guard and the schedule read one number. They used to be
#: two (15 and 60), and a game tipping in 16-59 minutes could be selected at a
#: price no measurement ever covered. This module imports nothing from `gates`,
#: which is what keeps that import acyclic.
CARD_LEAD_MINUTES = 60


@dataclass(frozen=True)
class CardSlot:
    """One publishing slot: when it nominally fires and what it must precede."""

    name: str
    #: Nominal cron hours in UTC. Two of them: a primary and a backup an hour
    #: later, where the backup stands down if the primary published cleanly.
    cron_hours_utc: tuple[int, ...]
    #: The ET hour this slot's games start at. The slot must land before it even
    #: at worst-case lateness.
    must_precede_et_hour: int
    what: str

    def worst_case_landing_et(self, offset_h: float = EST_OFFSET_H) -> float:
        """The latest ET hour this slot can land, at observed worst lateness.
        `offset_h` is the Eastern offset in force: EST for the season's bulk,
        `EDT_OFFSET_H` from 2027-03-14, which lands an hour later."""
        primary = min(self.cron_hours_utc)
        return (primary + OBSERVED_LATENESS_H + offset_h) % 24

    def backup_worst_case_landing_et(self, offset_h: float = EST_OFFSET_H) -> float:
        backup = max(self.cron_hours_utc)
        return (backup + OBSERVED_LATENESS_H + offset_h) % 24

    def holds(self, offset_h: float = EST_OFFSET_H) -> bool:
        """True when even the backup trigger lands before its block starts."""
        return self.backup_worst_case_landing_et(offset_h) < self.must_precede_et_hour


#: 11:00 ET is the earliest tip in a full season (3 games); 12:00 ET is the
#: earliest with meaningful volume. The morning slot is held to 11:00.
MORNING = CardSlot(
    name="morning",
    cron_hours_utc=(9, 10),
    must_precede_et_hour=11,
    what="every cardable game tipping at least an hour after the run",
)

#: 45.3% of the slate has tipped by 19:00 ET and 84.5% by 21:00. The evening
#: slot exists for the 55% the morning card priced fourteen hours out or not at
#: all, and is held to the 19:00 ET block.
EVENING = CardSlot(
    name="evening",
    cron_hours_utc=(16, 17),
    must_precede_et_hour=19,
    what="every cardable game not already frozen today, tipping at least an "
         "hour after the run",
)

SLOTS: tuple[CardSlot, ...] = (MORNING, EVENING)
SLOT_NAMES: tuple[str, ...] = tuple(s.name for s in SLOTS)

#: The cron MONTH field every card trigger carries. November to April is the
#: Division I season: the 2026-27 opener is 2026-11-01 and the championship is
#: in early April. A card run outside it would fetch an empty board, and an
#: empty board between April and November is an observation rather than a
#: fault — but it is an observation the line-movement capture is already
#: making, four times a day, for six credits.
#:
#: It lives here rather than in the workflow alone because
#: `docs/card_cadence.md` claimed the tests pinned the workflow's cron strings
#: to this module and **nothing did**. Only the hours were here, and a month
#: field is half of what a cron says about when a card fires.
SEASON_CRON_MONTHS = "11,12,1,2,3,4"

#: Minute-of-the-hour for every card trigger. On the hour, and the lateness
#: arithmetic is done in whole hours because GitHub's own lateness is measured
#: in hours: a cron at :30 would buy thirty minutes against a delay of five
#: hours and read as precision this schedule does not have.
CRON_MINUTE = 0


def cron_expressions() -> tuple[str, ...]:
    """Every cron string the gameday workflow must declare, in slot order.

    Derived from :data:`SLOTS`, so moving a trigger is a one-line change here
    that turns the build red until the workflow follows.
    `tests/test_the_card_schedule_survives_cron_lateness.py` compares this
    against the `on.schedule` of `.github/workflows/cbb-gameday-refresh.yml`
    and fails on any difference in either direction — a cron the contract does
    not declare, and a cron the contract declares that the workflow has
    dropped. The second is the quieter failure: a workflow missing its backup
    trigger looks exactly like a healthy one until the primary is skipped.
    """
    return tuple(
        f"{CRON_MINUTE} {hour} * {SEASON_CRON_MONTHS} *"
        for slot in SLOTS
        for hour in sorted(slot.cron_hours_utc)
    )


def slot_for(name: str) -> CardSlot:
    for slot in SLOTS:
        if slot.name == str(name):
            return slot
    raise KeyError(f"Unknown card slot {name!r}. Known: {SLOT_NAMES}")
