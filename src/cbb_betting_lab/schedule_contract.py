"""The card's schedule, and the cron lateness it has to survive.

Cooper, 2026-08-31: *"Do not trust the nominal cron time. GitHub has been firing
my repos' crons 4.5-5.3 hours late since 2026-08-27. Check every deadline
against `nominal + OBSERVED_LATENESS_H`."*

This module holds those constants in one place so the workflow, the docs and
the test that proves the schedule works all read the same numbers.

**Since 2026-09-29 the card does not ride the lateness; it absorbs it.** Each
card cron fires :data:`WAIT_LEAD_H` (eight hours) before a fixed SLOT, and the
workflow waits for the slot, so the card lands at the same UTC time every day
whatever GitHub does below eight hours (decision 61 in `docs/decision_log.md`).
:data:`OBSERVED_LATENESS_H` is what the lead has to exceed, and it is still the
constant the weekly refit is sized by.

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
#: **TWO RUNS ARE LATER.** On 2026-08-27 — the first day of the lateness Cooper
#: reported — EPL's two Thursday crons fired **9.61h and 9.85h** late. 7.4 is
#: the worst lateness on every OTHER day since 2026-08-27, rounded up, and the
#: two runs it does not cover are named in the test rather than dropped from the
#: record. They exceed :data:`WAIT_LEAD_H` too, and what a card fired that late
#: does is computed by :meth:`CardSlot.landing_utc_hour` and pinned in the test.
#:
#: Lateness is not flat across the day. Crons due 03:00-10:00 UTC run worst
#: (every run over 6.2h but the two above was due 06:00-10:00 UTC, most of them
#: on a Monday); none due at or after 16:00 UTC has been more than 4.22h late.
#: The morning card's crons (04:00, 05:00 UTC) sit in the worst band, which is
#: why the lead is sized to the account-wide worst and not to an hour's.
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
#: morning backup's slot, is 08:00 EST on 2027-03-13 and 09:00 EDT on
#: 2027-03-14. Later is the unsafe direction, toward the first tip and toward
#: the relay, so EDT is the offset that sets every slot hour: the slots of
#: 2026-09-29 were chosen as the latest whose BACKUP still freezes its block and
#: reaches the relay under EDT. EDT also covers the season's first days in a
#: year whose first Sunday of November falls after the 1st.
#:
#: Under the lateness-driven schedule this offset cost four cells that could not
#: freeze their block, recorded rather than closed. With the wait there are
#: none, and `tests/test_the_card_schedule_survives_cron_lateness.py` pins the
#: sign on the two instants above and the empty set of cells, both ways.
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


#: How far before its SLOT every card cron fires, in hours. Since 2026-09-29
#: (decision 61) a card no longer lands whenever GitHub gets round to it: the
#: cron fires this long before the slot, and the workflow's `wait` and
#: `wait-more` jobs hold the run until the slot (`scripts/wait_for_round.py`,
#: whose `ROUND_LEAD` a test holds equal to this). Lateness up to the lead
#: therefore costs nothing, and the card lands AT its slot every day, in a
#: window of minutes rather than the seven hours it used to wander across.
#:
#: Eight, as in the NHL lab and `line-movement.yml`: above the 7.4h
#: :data:`OBSERVED_LATENESS_H` and the account-wide 7.38h it rounds. The two
#: runs of 2026-08-27 (9.61h and 9.85h) exceed it; a run that late starts after
#: its slot and runs at once, which is what every run did before, and
#: :meth:`CardSlot.landing_utc_hour` says where it lands.
WAIT_LEAD_H = 8


def cron_hour_for(slot_hour_utc: int) -> int:
    """The UTC hour of the cron that serves a slot at `slot_hour_utc`.

    **A slot before 08:00 UTC is refused, not wrapped.** Its cron would fire on
    the previous UTC day, and the season's month field would then fire it on
    30 April for a 1 May slot nobody plays and never on 31 October for the
    1 November slot that opens the season. Every slot here is at or after
    12:00 UTC, so every cron fires on its slot's own UTC date and the month
    field needs no shift. A slot that needs one is a change to
    :func:`cron_expressions` — an extra day-of-month line for the first day —
    and not something to discover on the season's opening morning.
    """
    hour = int(slot_hour_utc) - WAIT_LEAD_H
    if not 0 <= hour < 24:
        raise ValueError(
            f"a slot at {slot_hour_utc:02d}:00 UTC needs its cron at {hour % 24:02d}:00 UTC "
            "on the PREVIOUS day, and the season month field would then miss the "
            "season's first day (1 November) and fire for 1 May. Shift the month and "
            "day fields deliberately in cron_expressions() before using such a slot."
        )
    return hour


@dataclass(frozen=True)
class CardSlot:
    """One publishing slot: when it lands, and what it must precede."""

    name: str
    #: The UTC hours the card LANDS, primary then backup an hour later; the
    #: backup stands down if the primary published cleanly. The crons are
    #: derived: :attr:`cron_hours_utc` is each of these less
    #: :data:`WAIT_LEAD_H`.
    slot_hours_utc: tuple[int, ...]
    #: The ET hour this slot's games start at. The slot must be able to FREEZE
    #: it — see :meth:`worst_case_freeze_bar_et` — not merely land before it.
    must_precede_et_hour: int
    what: str

    @property
    def cron_hours_utc(self) -> tuple[int, ...]:
        """The crons that fire this slot, :data:`WAIT_LEAD_H` before it."""
        return tuple(cron_hour_for(hour) for hour in self.slot_hours_utc)

    def _slot_hour(self, trigger: str) -> int:
        if trigger == "primary":
            return min(self.slot_hours_utc)
        if trigger == "backup":
            return max(self.slot_hours_utc)
        raise KeyError(f"unknown trigger {trigger!r}; a slot has a 'primary' and a 'backup'")

    def landing_utc_hour(self, trigger: str = "primary", lateness_h: float = 0.0) -> float:
        """The UTC hour-of-day `trigger`'s card job starts, its cron
        `lateness_h` late: the slot, unless GitHub started the run after it.

        The wait releases the run at the slot and never before it, so any
        lateness from zero to :data:`WAIT_LEAD_H` lands exactly on the slot.
        Beyond the lead the run starts late and does not wait at all.
        """
        slot = self._slot_hour(trigger)
        return max(float(slot), cron_hour_for(slot) + float(lateness_h))

    def worst_case_landing_et(self, offset_h: float = EST_OFFSET_H) -> float:
        """The latest ET hour the PRIMARY lands at any lateness the wait
        absorbs — which is the slot itself. `offset_h` is the Eastern offset in
        force: EST for the season's bulk, EDT for the tournament, when a fixed
        UTC slot reads an hour later."""
        return (self.landing_utc_hour("primary", WAIT_LEAD_H) + offset_h) % 24

    def backup_worst_case_landing_et(self, offset_h: float = EST_OFFSET_H) -> float:
        return (self.landing_utc_hour("backup", WAIT_LEAD_H) + offset_h) % 24

    def worst_case_freeze_bar_et(self, offset_h: float = EST_OFFSET_H) -> float:
        """The earliest tip the PRIMARY is sure to freeze: its landing, plus
        the whole :data:`CARD_RUN_BUDGET_MINUTES` (the freeze happens somewhere
        inside the run, so take its end), plus the card lead. See
        :func:`freeze_bar_et_hour`."""
        return freeze_bar_et_hour(self.worst_case_landing_et(offset_h) + CARD_RUN_BUDGET_H)

    def backup_worst_case_freeze_bar_et(self, offset_h: float = EST_OFFSET_H) -> float:
        """The earliest tip the BACKUP is sure to freeze."""
        return freeze_bar_et_hour(self.backup_worst_case_landing_et(offset_h) + CARD_RUN_BUDGET_H)

    def primary_holds(self, offset_h: float = EST_OFFSET_H) -> bool:
        """True when the primary can freeze the block's first tip."""
        return self.worst_case_freeze_bar_et(offset_h) < self.must_precede_et_hour

    def holds(self, offset_h: float = EST_OFFSET_H) -> bool:
        """True when even the BACKUP can freeze the block's first tip.

        Under the lateness-driven schedule this failed in four of the eight
        slot/offset/trigger cells, and those gaps were recorded rather than
        closed. With the wait every trigger lands on its slot, so the slots
        were chosen for this to hold in all of them, in EST and in EDT.
        """
        return self.backup_worst_case_freeze_bar_et(offset_h) < self.must_precede_et_hour


#: 11:00 ET is the earliest tip in a full season with any volume (34 games in
#: 2025-26); 12:00 ET is the earliest with meaningful volume. The morning slot
#: is held to 11:00.
#:
#: **12:00 and 13:00 UTC since 2026-09-29** (decision 61), from crons at 07:00
#: and 08:00 UTC that landed wherever GitHub's lateness put them. The latest
#: pair whose BACKUP still freezes the 11:00 ET block under EDT: 13:00 UTC is
#: 09:00 EDT, done by 09:20, freezing everything from 10:20. A 14:00 UTC backup
#: is 10:00 EDT and can freeze nothing before 11:20. In EST the pair is 07:00
#: and 08:00. Both are on `card-feed` well before the relay's 10:52 ET run.
MORNING = CardSlot(
    name="morning",
    slot_hours_utc=(12, 13),
    must_precede_et_hour=11,
    what="every cardable game tipping at least an hour after the run",
)

#: 45.3% of the slate has tipped by 19:00 ET and 84.5% by 21:00. The evening
#: slot exists for the 55% the morning card priced half a day out or not at
#: all, and is held to the 19:00 ET block.
#:
#: **20:00 and 21:00 UTC since 2026-09-29** (decision 61), from crons at 14:00
#: and 15:00 UTC. Two constraints bind together and at the same hour: the
#: backup, at 21:00 UTC, is 17:00 EDT, on `card-feed` by 17:20 — 32 minutes
#: before the relay's 17:52 ET run — and freezes everything from 18:20. A
#: 22:00 UTC backup would be 18:00 EDT: on the feed after the 17:52 relay and
#: the 18:15 read, and unable to freeze the 19:00 block. In EST the pair is
#: 15:00 and 16:00, so the 19:00 block is priced three to four hours out
#: instead of the seven to ten the old crons gave it.
EVENING = CardSlot(
    name="evening",
    slot_hours_utc=(20, 21),
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
#: **It needs no shift for the wait**, and that is by construction rather than
#: luck: :func:`cron_hour_for` refuses any slot whose cron would fire on the
#: previous UTC day, so the cron for the 1 November slot fires on 1 November.
#:
#: It lives here rather than in the workflow alone because
#: `docs/card_cadence.md` claimed the tests pinned the workflow's cron strings
#: to this module and **nothing did**. Only the hours were here, and a month
#: field is half of what a cron says about when a card fires.
SEASON_CRON_MONTHS = "11,12,1,2,3,4"

#: Minute-of-the-hour for every card cron, and so for every slot. On the hour:
#: the slots are whole hours because the constraints that set them — the
#: relay's :52 and the blocks' first tips — leave whole-hour room, and the
#: wait script reads one minute and one hour back out of the cron.
CRON_MINUTE = 0


def cron_expressions() -> tuple[str, ...]:
    """Every cron string the gameday workflow must declare, in slot order.

    Derived from :data:`SLOTS` through :func:`cron_hour_for`, so moving a slot
    is a one-line change here that turns the build red until the workflow — its
    `on.schedule` and the hour `case` in `already-published` — follows.
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

#: The Eastern hours the relay runs. **The live routine runs these and this
#: repository does not change them**: the card slots of 2026-09-29 were chosen
#: to fit this schedule as it stands, so no routine had to move with them.
#:
#: * 10:52 — the morning card. It is on `card-feed` by 07:20 EST / 08:20 EDT
#:   from the primary and 08:20 EST / 09:20 EDT from the backup.
#: * 17:52 — the evening card: 15:20 EST / 16:20 EDT from the primary, 16:20
#:   EST / 17:20 EDT from the backup, 32 minutes clear at the tightest.
#: * 03:52 — carries nothing new since the card crons began waiting for their
#:   slots. It was set for a morning card GitHub fired on time at 07:00 UTC;
#:   no card lands before 07:00 ET now, so this run finds the previous
#:   evening's card, which the relay has already written, and a re-run whose
#:   content is byte-identical changes nothing (`docs/delivery_chain.md`). It
#:   is harmless and left in place, because the routine is Cooper's to edit.
#:
#: Between the two slots there is always a relay run: the morning card is
#: copied at 10:52 before the evening card can exist (15:00 ET at the
#: earliest), and the evening card at 17:52 before the next morning's.
RELAY_ET_HOURS: tuple[int, ...] = (3, 10, 17)

#: How long a card run takes from the moment GitHub starts it to the moment
#: `card-feed` holds the card. **An allowance, not a measurement**: no in-season
#: run of this workflow exists yet. The whole pipeline on an empty off-season
#: board took 1m34s (2026-09-01, dispatch), and a rehearsal against a real slate
#: would spend credits. Twenty minutes is thirteen times the measured run, and
#: the job's own timeout is ninety. Replace it with the first in-season runs'
#: durations. The tightest place it is spent is the evening backup under EDT,
#: which starts at 17:00 and has 52 minutes to reach the 17:52 relay run.
CARD_RUN_BUDGET_MINUTES = 20

#: The same allowance in hours, derived, for the ET hour-of-day arithmetic.
CARD_RUN_BUDGET_H = CARD_RUN_BUDGET_MINUTES / 60.0

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
