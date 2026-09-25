"""The card's schedule, and the cron lateness it has to survive.

Cooper, 2026-08-31: *"Do not trust the nominal cron time. GitHub has been firing
my repos' crons 4.5-5.3 hours late since 2026-08-27. Check every deadline
against `nominal + OBSERVED_LATENESS_H`."*

This module holds those constants in one place so the workflow, the docs and
the test that proves the schedule works all read the same numbers. Raising
:data:`OBSERVED_LATENESS_H` when GitHub gets worse is a one-line change that
proves itself, because the test recomputes the whole table from it.

**A landing is not a deadline.** Every deadline here is a landing plus
:data:`CARD_LEAD_MINUTES`, because the tip guard the card actually runs
quarantines any game tipping inside that lead and never writes it to the
append-only store. This module declared that constant and then compared
landings to tip hours as though it were zero, for its whole life — see
:func:`freeze_bar_et_hour`, which is where the sixty minutes now live.

**And a frozen card is not a delivered one.** Cooper reads the card through a
cloud relay that copies it into Google Drive and a chat task that reads Drive
at fixed Eastern times. That chain had its own cron, pinned in a script and
reasoned about in prose, and nothing multiplied it by the lateness: fixed in
UTC, its late runs would have landed after both reads for the whole of the
tournament. The relay's schedule and the readers' times now live here too, see
:func:`relay_cron_expression`.

The reasoning is in `docs/card_cadence.md` and `docs/delivery_chain.md`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

#: The lateness every deadline here is checked against, in hours. Measured, not
#: documented behaviour: every deadline is `nominal + this`, never nominal.
#:
#: **HELD TO A RECORD NOW, BECAUSE IT WAS A SENTENCE.** This read 5.3, from
#: Cooper's *"4.5-5.3 hours late since 2026-08-27"*, until 2026-09-25 — when
#: `scripts/measure_cron_lateness.py` read every scheduled run on his six
#: repositories since that date (565 matched) and found the same account's crons
#: **7.38h** late on 2026-08-31 (football, `0 6 * * *`), **6.83h** on 2026-09-14
#: and 09-21 (EPL, `0 9 * * 1`), and this repository's own weekly refit 5.84h
#: late. The record is `data/outputs/cbb_cron_lateness.json`, every figure in it
#: a lower bound, and `tests/test_the_card_schedule_survives_cron_lateness.py`
#: fails when a run in it is later than this constant and not named there.
#:
#: **TWO RUNS ARE LATER, AND THIS SCHEDULE DOES NOT SURVIVE THEM.** On
#: 2026-08-27 — the first day of the lateness Cooper reported — EPL's two
#: Thursday crons fired **9.61h and 9.85h** late. Sizing every deadline for 9.85
#: would move the morning card to 04:00 UTC and the evening card to 11:00 UTC,
#: pricing every day of the season hours earlier against a repeat of one day.
#: That is Cooper's trade to make and not a constant's, so 7.4 is the worst
#: lateness on every OTHER day since 2026-08-27, rounded up, and the two runs it
#: does not cover are named in the test rather than dropped from the record.
#:
#: Lateness is not flat across the day, and one constant ignores that on
#: purpose. Crons due 03:00-10:00 UTC run worst (every run over 6.2h but the
#: two above was due 06:00-10:00 UTC, most of them on a Monday); none due at or
#: after 16:00 UTC has been more than 4.22h late. Applying the morning's worst to
#: the evening is pessimistic by about two hours, and it is the pessimism that
#: moved the evening card — see :data:`EVENING`.
OBSERVED_LATENESS_H = 7.4

#: Eastern standard time offset, UTC-5. The college basketball season runs
#: almost entirely in EST, and every figure in `docs/card_cadence.md`'s table
#: is an EST figure.
EST_OFFSET_H = -5

#: Eastern daylight time offset, UTC-4, from 2027-03-14 (02:00 EST, 07:00 UTC)
#: to the end of the season. THE SIGN MATTERS AND THIS FILE HAD IT BACKWARDS:
#: it used to say DST moves every landing an hour *earlier* in ET, "the safe
#: direction". A cron is fixed in UTC, so when the offset shrinks from -5 to -4
#: the same instant reads an hour LATER on an Eastern clock — 08:00 UTC, the
#: morning backup, is 03:00 EST on 2027-03-13 and 04:00 EDT on 2027-03-14. Later
#: is the unsafe direction, toward the first tip, and at the worst observed
#: lateness it moves the morning backup from 10:24 ET to 11:24 ET, past its
#: 11:00 ET block.
#:
#: This comment used to end "the morning primary (10:18 ET) and both evening
#: triggers still hold", and that sentence was the same sixty-minute omission
#: :func:`freeze_bar_et_hour` exists to close. A run landing at 10:24 cannot
#: freeze an 11:00 tip: the tip guard quarantines it. Under EDT the morning
#: primary therefore misses the 11:00 block too, and the evening backup lands
#: 18:24 and cannot reach the 19:00 block it exists for. Those gaps are
#: recorded rather than chased — the crons moved on 2026-09-25 for the lateness
#: and for the relay, not to close them — and
#: `tests/test_the_card_schedule_survives_cron_lateness.py` pins the sign on
#: those two instants and the whole set of cells that cannot freeze their block
#: as written.
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

#: The same lead in hours, because every landing in this module is an ET
#: hour-of-day as a float. Derived from the minutes rather than typed again:
#: two spellings of one number is how `gates` and this module came to hold 15
#: and 60 in the first place.
CARD_LEAD_H = CARD_LEAD_MINUTES / 60.0


def freeze_bar_et_hour(landing_hour_et: float) -> float:
    """The ET tip hour a run landing at `landing_hour_et` must beat to freeze.

    **A landing is not a deadline, and this module treated it as one.** A game
    is carded only if the tip guard calls it `UPCOMING`, and
    `gates.IMMINENT_MINUTES` **is** :data:`CARD_LEAD_MINUTES`: `gates.tip_state`
    returns `IMMINENT` for `delta <= IMMINENT_MINUTES`, `gates.can_be_played`
    is true only for `UPCOMING`, and `reports/gameday_card.py._rows_to_freeze`
    drops everything that is not playable *before* the rows reach
    `forward_evidence.write_snapshot`. So a game inside the lead is not merely
    unstaked — it is never written to the append-only store at all, and the
    night it would have contributed cannot be rebuilt.

    The earliest tip a run can freeze is therefore its landing plus the lead.
    :meth:`CardSlot.holds` compared the bare landing to the block's tip hour
    for this module's whole life, which made every slot sixty minutes more
    comfortable than it is: the morning backup's recorded margin was "42 min",
    which is *inside* the lab's own guard, and `holds()` went red at 6.0h
    lateness when the real bar was already violated at 5.0h — below the 5.3h
    being observed the day this was found.

    Two deliberate choices:

    * The caller compares with a strict `<`. A tip exactly on the bar is
      `delta == IMMINENT_MINUTES`, which `tip_state` quarantines, so the bar is
      a hour a tip must fall strictly after and not merely reach.
    * The sum is **not** taken modulo 24, unlike the landings that feed it. A
      landing at 23:30 should read 24.5 here and fail every `<` against a tip
      hour; wrapping it to 00:30 would let a slot that lands tonight claim to
      cover tomorrow morning. Fail closed on the one case nobody has a test for.
    """
    return landing_hour_et + CARD_LEAD_H


@dataclass(frozen=True)
class CardSlot:
    """One publishing slot: when it nominally fires and what it must precede."""

    name: str
    #: Nominal cron hours in UTC. Two of them: a primary and a backup an hour
    #: later, where the backup stands down if the primary published cleanly.
    cron_hours_utc: tuple[int, ...]
    #: The ET hour this slot's games start at. The slot must land a full
    #: :data:`CARD_LEAD_MINUTES` before it even at worst-case lateness — not
    #: merely before it, see :func:`freeze_bar_et_hour`.
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

    def worst_case_freeze_bar_et(self, offset_h: float = EST_OFFSET_H) -> float:
        """The earliest tip the PRIMARY can still freeze, at worst lateness:
        its landing plus the card lead. See :func:`freeze_bar_et_hour`."""
        return freeze_bar_et_hour(self.worst_case_landing_et(offset_h))

    def backup_worst_case_freeze_bar_et(self, offset_h: float = EST_OFFSET_H) -> float:
        """The earliest tip the BACKUP can still freeze, at worst lateness."""
        return freeze_bar_et_hour(self.backup_worst_case_landing_et(offset_h))

    def primary_holds(self, offset_h: float = EST_OFFSET_H) -> bool:
        """True when the primary trigger can still freeze the block's first tip.

        The weaker of the two promises, and the only one the morning slot keeps
        under EST. It is stated separately because the backup exists precisely
        for the day the primary was dropped, so "the primary holds" is not a
        substitute for "the slot holds" — it is the smaller thing that is true.
        """
        return self.worst_case_freeze_bar_et(offset_h) < self.must_precede_et_hour

    def holds(self, offset_h: float = EST_OFFSET_H) -> bool:
        """True when even the backup trigger can still FREEZE the block's first
        tip — landing plus :data:`CARD_LEAD_MINUTES`, not the bare landing.

        This method asked `backup_worst_case_landing_et(offset_h) <
        must_precede_et_hour` until 2026-09-15, with no lead term, twenty-seven
        lines below the constant that defines the lead. Three of the four
        slot/offset cells it passed cannot in fact freeze the block they name,
        and the uncardable share the repository had recorded off the same
        omission (0.05%) understated the real one (0.59%) by eighteen times.
        """
        return self.backup_worst_case_freeze_bar_et(offset_h) < self.must_precede_et_hour


#: 11:00 ET is the earliest tip in a full season (3 games); 12:00 ET is the
#: earliest with meaningful volume. The morning slot is held to 11:00.
#:
#: 07:00/08:00 UTC since 2026-09-25, from 09:00/10:00, and two constraints set
#: it. At 7.4h late a 09:00 UTC primary lands 11:24 EST and can freeze nothing
#: before 12:24, so it no longer covered its own block at all; 08:00 would. But
#: the card also has to REACH Cooper, and from 2027-03-14 an 08:00 UTC primary
#: lands 11:24 EDT at worst — after the 11:15 ET reader. 07:00 UTC lands 10:24
#: EDT, is ready by 10:44 on :data:`CARD_RUN_BUDGET_MINUTES`, and the relay's
#: 10:52 ET run carries it. The tests hold both constraints, so the next change
#: to the lateness says which of them moves this pair.
MORNING = CardSlot(
    name="morning",
    cron_hours_utc=(7, 8),
    must_precede_et_hour=11,
    what="every cardable game tipping at least an hour after the run",
)

#: 45.3% of the slate has tipped by 19:00 ET and 84.5% by 21:00. The evening
#: slot exists for the 55% the morning card priced half a day out or not at
#: all, and is held to the 19:00 ET block.
#:
#: 14:00/15:00 UTC since 2026-09-25, from 16:00/17:00, and the reason is the
#: reader rather than the block. At 7.4h late a 16:00 UTC primary lands 18:24
#: EST and freezes nothing before 19:24. 15:00 UTC would freeze the block in
#: EST, but under EDT it lands 18:24 — after the 18:15 ET reader, for the whole
#: tournament. 14:00 UTC lands 16:24 EST / 17:24 EDT and the relay's 17:52 ET
#: run carries it either way. **On the evidence this is pessimism, not need**:
#: no cron due at or after 16:00 UTC has run more than 4.22h late, and the 7.4h
#: this slot is sized for was a 06:00 UTC cron on a Monday. A lateness that
#: varied by hour would keep the evening card later; one constant is the
#: design, and what it costs this slot is written here rather than hidden in it.
EVENING = CardSlot(
    name="evening",
    cron_hours_utc=(14, 15),
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


# --------------------------------------------------------------------------
# The rest of the chain: the relay, and the two reads it exists for
#
# A card on `card-feed` is frozen evidence; a card Cooper sees is one the
# `CBB CARD RELAY` cloud routine copied into Google Drive before his chat task
# read Drive. Everything above is about the first. This is about the second,
# and until 2026-09-25 none of it was here: the relay cron was a string in
# `scripts/create_card_relay_routine.py`, fixed in UTC, and its "worst-case"
# runs at 15:37 and 22:37 UTC were reasoned about in EST only. From 2027-03-14
# those are 11:37 and 18:37 EDT — after both reads, for the tournament.
# --------------------------------------------------------------------------

#: When Cooper's chat-side tasks read the newest card in Drive, as Eastern
#: wall-clock hours. They are his, set in the regular Claude app, and they
#: follow the Eastern clock through DST; `docs/chat_task_prompt.md` is where he
#: was told them, and a test holds that page to this mapping.
READER_ET_HOUR: dict[str, float] = {"morning": 11.25, "evening": 18.25}

#: The relay runs on the READERS' clock, not GitHub's. A cloud routine accepts
#: a `CRON_TZ=` prefix and three of Cooper's routines already use it, with
#: `next_run_at` correct across DST. Pinned to UTC, the gap from relay to
#: reader moved by an hour on 2027-03-14; pinned to Eastern it never moves, and
#: the gap from card to relay — which does move, because the card crons are UTC —
#: is what the tests check in both offsets.
RELAY_TIMEZONE = "America/New_York"

#: Minute of every relay run. :52 leaves :data:`RELAY_BUDGET_MINUTES` before
#: a :15 read, with three minutes spare.
RELAY_MINUTE = 52

#: The Eastern hours the relay runs, each for a stated reason:
#:
#: * 03:52 — the morning card when GitHub is ON TIME (07:00 UTC is 02:00 EST,
#:   03:00 EDT). Without it an on-time morning card could be replaced on
#:   `card-feed` by an on-time evening card before any relay copied it.
#: * 10:52 — the morning card at worst lateness (ready 09:44 EST, 10:44 EDT),
#:   and the evening card when GitHub is on time (ready 09:20 EST, 10:20 EDT).
#: * 17:52 — the evening card at worst lateness (ready 16:44 EST, 17:44 EDT).
#:
#: Three runs where the UTC schedule had four: an on-time evening card no
#: longer needs a run of its own, because the morning's late run is already
#: after it.
RELAY_ET_HOURS: tuple[int, ...] = (3, 10, 17)

#: How long a card run takes from the moment GitHub starts it to the moment
#: `card-feed` holds the card. **An allowance, not a measurement**: no in-season
#: run of this workflow exists yet. The whole pipeline on an empty off-season
#: board took 1m34s (2026-09-01, dispatch), and a rehearsal against a real slate
#: would spend credits. Twenty minutes is thirteen times the measured run, and
#: the job's own timeout is ninety. Replace it with the first in-season runs'
#: durations: at 7.4h late the morning and evening cards have eight minutes to
#: spare against it under EDT.
CARD_RUN_BUDGET_MINUTES = 20

#: How long after its cron a relay run can still be writing to Drive. Measured
#: 2026-09-25 from Cooper's live routines: they fire up to 15m11s after their
#: cron (NFL LAB BRIEF, due 15:00, fired 15:15:11) and a relay run takes 9s to
#: 2m48s (NHL, SOCCER). Twenty minutes covers both.
RELAY_BUDGET_MINUTES = 20


def relay_cron_expression() -> str:
    """The `CBB CARD RELAY` routine's cron, derived from the constants above.

    `scripts/create_card_relay_routine.py` builds the routine from this, and
    the tests hold the relay to both ends of the chain: every slot's card, on
    time and at :data:`OBSERVED_LATENESS_H`, in EST and in EDT, must be ready
    before some relay run that finishes before that slot's reader. **The live
    routine is not in this repository** — changing this string changes what
    the script would create, and the running routine only when somebody
    updates it.
    """
    hours = ",".join(str(hour) for hour in RELAY_ET_HOURS)
    return f"CRON_TZ={RELAY_TIMEZONE} {RELAY_MINUTE} {hours} * {SEASON_CRON_MONTHS} *"


def slot_for(name: str) -> CardSlot:
    for slot in SLOTS:
        if slot.name == str(name):
            return slot
    raise KeyError(f"Unknown card slot {name!r}. Known: {SLOT_NAMES}")
