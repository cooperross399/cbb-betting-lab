"""Every slot must FREEZE its block and REACH Cooper, whatever GitHub's lateness.

GitHub fires Cooper's crons hours late — 7.38 hours at worst on every day since
2026-08-27 but the first, `data/outputs/cbb_cron_lateness.json`. Until
2026-09-29 the card rode that lateness: its crons were set early enough that a
landing anywhere from nominal to nominal + 7.4h still froze its block and
reached the relay, and this file checked every trigger at the worst of it.

**Since 2026-09-29 the card absorbs the lateness instead** (decision 61). Each
cron fires `WAIT_LEAD_H` (eight hours) before a fixed slot, and the workflow's
`wait` and `wait-more` jobs hold the run until the slot, exactly as
`line-movement.yml` does. So this file now pins three things:

* **the arithmetic** — every cron is its slot less the lead, the wait script
  releases every cron's run at that slot for any lateness up to the lead, and
  the season's first day has its cron inside the season's month field;
* **the slots** — in EST and in EDT, both triggers of each slot are on
  `card-feed` before the relay run that carries them, with margin, and can
  freeze their block's first tip; and no later whole hour could say the same;
* **the wiring** — the waits sit in front of the guard, no condition upstream
  of the card can silently skip it, and the concurrency group is on the card
  job, because a workflow-level group cancels runs that now spend hours pending.

**And landing is not freezing.** A run cannot freeze a game tipping inside
`CARD_LEAD_MINUTES` of it, because `gates.tip_state` calls it `IMMINENT`,
`can_be_played` refuses it and `reports/gameday_card.py._rows_to_freeze` drops
it before it reaches the append-only store. Every bar here is the landing plus
the whole `CARD_RUN_BUDGET_MINUTES` plus that lead, and
`test_a_slots_verdict_is_the_tip_guards_verdict_on_the_blocks_first_tip` asks
`gates` itself rather than agreeing with this module's own arithmetic.
"""

from __future__ import annotations

import importlib.util
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest
import yaml

from conftest import schedule_fixture
from zoneinfo import ZoneInfo

from cbb_betting_lab.gates import can_be_played, tip_state
from cbb_betting_lab.schedule_contract import (
    CARD_LEAD_H,
    CARD_LEAD_MINUTES,
    CARD_RUN_BUDGET_H,
    CARD_RUN_BUDGET_MINUTES,
    CRON_MINUTE,
    EASTERN,
    EDT_OFFSET_H,
    EST_OFFSET_H,
    EVENING,
    MORNING,
    OBSERVED_LATENESS_H,
    READER_ET_HOUR,
    RELAY_BUDGET_MINUTES,
    RELAY_MINUTE,
    RELAY_TIMEZONE,
    SEASON_CRON_MONTHS,
    SLOT_NAMES,
    SLOTS,
    WAIT_LEAD_H,
    CardSlot,
    cron_expressions,
    cron_hour_for,
    eastern_offset_h,
    freeze_bar_et_hour,
    landing_et,
    relay_cron_expression,
    slot_for,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WAIT_SCRIPT = PROJECT_ROOT / "scripts" / "wait_for_round.py"


def _load_wait_script():
    spec = importlib.util.spec_from_file_location("_cbb_card_wait_for_round", WAIT_SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


wfr = _load_wait_script()

#: The slots, typed out by hand, so the arithmetic below has something to
#: disagree with. (slot, trigger) -> UTC hour the card lands.
SLOT_HOURS_UTC = {
    ("morning", "primary"): 12,
    ("morning", "backup"): 13,
    ("evening", "primary"): 20,
    ("evening", "backup"): 21,
}

#: The slot name each cron's run publishes as, and the slot name the cron it
#: REPLACED published as on 2026-09-28. Hand-written in both columns: moving
#: a cron must not move the card it publishes from one slot to the other.
CRON_TO_SLOT_NAME = {
    "0 4 * 11,12,1,2,3,4 *": "morning",   # was "0 7 ..."
    "0 5 * 11,12,1,2,3,4 *": "morning",   # was "0 8 ..."
    "0 12 * 11,12,1,2,3,4 *": "evening",  # was "0 14 ..."
    "0 13 * 11,12,1,2,3,4 *": "evening",  # was "0 15 ..."
}
RETIRED_CRON_HOURS_UTC = (7, 8, 14, 15)

#: The same instant — 13:00 UTC, the morning backup's slot — on the last day of
#: EST and the first day of EDT. DST begins 2027-03-14 at 02:00 EST (07:00
#: UTC), so 13:00 UTC on the 14th is already an EDT instant.
LAST_EST_MORNING = datetime(2027, 3, 13, 13, 0, tzinfo=timezone.utc)
FIRST_EDT_MORNING = datetime(2027, 3, 14, 13, 0, tzinfo=timezone.utc)

#: Two ordinary slate days, one either side of the 2027-03-14 switch, used to
#: put a landing and a tip on the same real Eastern clock. Neither contains a
#: transition, so adding hours to midnight is honest wall-clock arithmetic, and
#: each is checked against the tz database before it is used.
AN_EST_SLATE_DAY = date(2026, 12, 2)
AN_EDT_SLATE_DAY = date(2027, 3, 17)
OFFSETS = (
    ("EST", EST_OFFSET_H, AN_EST_SLATE_DAY),
    ("EDT", EDT_OFFSET_H, AN_EDT_SLATE_DAY),
)
TRIGGERS = ("primary", "backup")

#: Every lateness the wait absorbs, sampled: on time, a minute late, the
#: capture's median, its worst, the account's worst, and a minute short of
#: the lead. At each of these every card lands on its slot.
ABSORBED_LATENESS_H = (0.0, 1 / 60, 3.1, 6.6, OBSERVED_LATENESS_H, WAIT_LEAD_H - 1 / 60, WAIT_LEAD_H)

#: How much room each card must leave before the relay run that carries it.
#: The tightest cell, the evening backup under EDT, leaves 32 minutes.
RELAY_MARGIN_MINUTES = 30


def eastern_instant(day: date, et_hour: float) -> datetime:
    """`et_hour` on `day`, as a real Eastern instant."""
    return datetime(day.year, day.month, day.day, tzinfo=EASTERN) + timedelta(hours=et_hour)


def utc_instant(day: date, utc_hour: float) -> datetime:
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc) + timedelta(hours=utc_hour)


# --------------------------------------------------------------------------
# The arithmetic: cron + lead = slot, and the wait releases every run there
# --------------------------------------------------------------------------


def test_the_slots_are_the_ones_written_down():
    measured = {
        (slot.name, trigger): slot._slot_hour(trigger) for slot in SLOTS for trigger in TRIGGERS
    }
    assert measured == SLOT_HOURS_UTC
    assert SLOT_NAMES == ("morning", "evening")


def test_the_contracts_lead_is_the_wait_scripts_lead():
    """Two spellings of one number, held together. The contract reasons with
    `WAIT_LEAD_H`; the run is held by `wait_for_round.ROUND_LEAD`."""
    assert wfr.ROUND_LEAD == timedelta(hours=WAIT_LEAD_H)
    assert WAIT_LEAD_H >= OBSERVED_LATENESS_H, (
        "the wait lead must cover the lateness this repository is sized for"
    )


def test_every_slot_is_its_cron_plus_the_lead():
    """For every cron the WORKFLOW declares — parsed, not the contract's own
    list — cron + lead is one of the slots, and every slot has its cron."""
    landed = {}
    for cron in workflow_crons():
        minute, hour = cron.split()[:2]
        assert minute == str(CRON_MINUTE)
        landed[cron] = int(hour) + WAIT_LEAD_H
    assert sorted(landed.values()) == sorted(SLOT_HOURS_UTC.values())
    for slot in SLOTS:
        for slot_hour, cron_hour in zip(slot.slot_hours_utc, slot.cron_hours_utc):
            assert cron_hour + WAIT_LEAD_H == slot_hour
    assert len(set(workflow_crons())) == len(SLOT_HOURS_UTC), "two crons for one slot"


@pytest.mark.parametrize("late_h", ABSORBED_LATENESS_H)
@pytest.mark.parametrize("day", [AN_EST_SLATE_DAY, AN_EDT_SLATE_DAY, date(2026, 11, 1), date(2027, 4, 30)])
def test_the_wait_releases_every_cron_at_its_slot(day, late_h):
    """The wait script, run on each declared cron fired `late_h` late,
    targets the slot on the slot's own day and never a moment before the run
    started. That is the whole claim the schedule rests on."""
    for (name, trigger), slot_hour in SLOT_HOURS_UTC.items():
        slot = slot_for(name)
        cron_hour = cron_hour_for(slot_hour)
        cron = f"{CRON_MINUTE} {cron_hour} * {SEASON_CRON_MONTHS} *"
        assert cron in workflow_crons()
        started = utc_instant(day, cron_hour + late_h)
        target = wfr.round_for(cron, started)
        assert target == utc_instant(day, slot_hour), (name, trigger, late_h)
        assert target >= started
        assert slot.landing_utc_hour(trigger, late_h) == slot_hour


def test_the_seasons_first_day_has_its_cron_inside_the_season():
    """A slot before 08:00 UTC would need its cron on the PREVIOUS UTC day, so
    the cron for 1 November would fire on 31 October — a month the field does
    not name — and the season would open without its first card, while 30
    April's cron fired for a 1 May nobody plays. Every slot here is at or after
    12:00 UTC, so every cron fires on its slot's own date; that is checked on
    the real first and last days, in both offsets the first day can fall in
    (1 November 2026 is the day DST ends; 1 November 2027 is still EDT)."""
    months = {int(m) for m in SEASON_CRON_MONTHS.split(",")}
    for first_day, label in ((date(2026, 11, 1), "EST"), (date(2027, 11, 1), "EDT")):
        for (name, trigger), slot_hour in SLOT_HOURS_UTC.items():
            landing = utc_instant(first_day, slot_hour)
            fired = landing - timedelta(hours=WAIT_LEAD_H)
            assert fired.date() == first_day, (name, trigger)
            assert fired.month in months
            assert landing.astimezone(EASTERN).date() == first_day, (
                f"the {name} {trigger} slot on {first_day} is on a different "
                "league date, so the run would stamp the wrong slate"
            )
            assert landing.astimezone(EASTERN).tzname() == label
    for (name, trigger), slot_hour in SLOT_HOURS_UTC.items():
        last = utc_instant(date(2027, 4, 30), slot_hour)
        assert (last - timedelta(hours=WAIT_LEAD_H)).month in months
        assert last.astimezone(EASTERN).date() == date(2027, 4, 30)


@pytest.mark.parametrize("slot_hour", range(0, 8))
def test_a_slot_whose_cron_would_cross_midnight_is_refused(slot_hour):
    with pytest.raises(ValueError, match="PREVIOUS day"):
        cron_hour_for(slot_hour)
    with pytest.raises(ValueError):
        CardSlot(name="x", slot_hours_utc=(slot_hour, 9), must_precede_et_hour=11, what="x").cron_hours_utc


def test_the_2026_27_opener_in_rome_is_frozen_by_both_morning_triggers():
    """Notre Dame v Villanova, 09:30 ET on 2026-11-01, the season's first game.
    Under the old crons the worst-late morning card could not freeze it; the
    morning slot now lands 07:00 EST that day (DST ended at 06:00 UTC), and
    even the backup, done by 08:20, precedes the tip by more than the lead."""
    tip = datetime(2026, 11, 1, 9, 30, tzinfo=EASTERN)
    assert tip.tzname() == "EST"
    for trigger in TRIGGERS:
        done = utc_instant(date(2026, 11, 1), MORNING.landing_utc_hour(trigger)) + timedelta(
            minutes=CARD_RUN_BUDGET_MINUTES
        )
        assert can_be_played(tip_state(tip.isoformat(), now=done)), trigger


# --------------------------------------------------------------------------
# The slots: both triggers freeze their block and reach the relay, EST and EDT
# --------------------------------------------------------------------------


#: Every `(slot, offset, trigger)` that cannot freeze the first tip of its own
#: block. Under the lateness-driven crons this held four cells — the morning
#: backup in EST, both morning triggers and the evening backup in EDT — and
#: they were recorded rather than closed. With the wait every trigger lands on
#: its slot, and the slots were chosen so that this set is empty. It is kept as
#: a set, compared both ways, so a gap that reopens is named rather than
#: swept into a boolean.
CELLS_THAT_CANNOT_FREEZE_THEIR_BLOCK: set[tuple[str, str, str]] = set()


def test_the_cells_that_cannot_freeze_their_block_are_the_ones_written_down():
    measured = {
        (slot.name, label, trigger)
        for slot in SLOTS
        for label, offset_h, _day in OFFSETS
        for trigger, held in (("primary", slot.primary_holds(offset_h)), ("backup", slot.holds(offset_h)))
        if not held
    }
    assert measured == CELLS_THAT_CANNOT_FREEZE_THEIR_BLOCK, (
        f"measured {sorted(measured)}, recorded {sorted(CELLS_THAT_CANNOT_FREEZE_THEIR_BLOCK)}. "
        "Update docs/card_cadence.md, the workflow header and this set together."
    )
    # The figures docs/card_cadence.md prints, from the contract.
    assert MORNING.backup_worst_case_freeze_bar_et(EDT_OFFSET_H) == pytest.approx(9 + 1 / 3 + 1)
    assert EVENING.backup_worst_case_freeze_bar_et(EDT_OFFSET_H) == pytest.approx(17 + 1 / 3 + 1)
    assert MORNING.worst_case_landing_et(EST_OFFSET_H) == 7.0
    assert EVENING.worst_case_landing_et(EST_OFFSET_H) == 15.0


def test_dst_moves_a_fixed_utc_slot_later_on_an_eastern_clock():
    """Measured on two concrete instants from the tz database, not asserted:
    13:00 UTC is 08:00 on 2027-03-13 and 09:00 on 2027-03-14. Later, by one
    hour, toward the first tip and toward the relay — which is why EDT is the
    offset that set every slot hour."""
    assert LAST_EST_MORNING.hour == FIRST_EDT_MORNING.hour == max(MORNING.slot_hours_utc)
    assert LAST_EST_MORNING.astimezone(EASTERN).strftime("%H:%M %Z") == "08:00 EST"
    assert FIRST_EDT_MORNING.astimezone(EASTERN).strftime("%H:%M %Z") == "09:00 EDT"
    assert eastern_offset_h(LAST_EST_MORNING) == EST_OFFSET_H == -5
    assert eastern_offset_h(FIRST_EDT_MORNING) == EDT_OFFSET_H == -4
    before = landing_et(13, date(2027, 3, 13))
    after = landing_et(13, date(2027, 3, 14))
    assert (before, after) == (8.0, 9.0)

    for slot in SLOTS:
        for offset_h, day in ((EST_OFFSET_H, date(2027, 3, 13)), (EDT_OFFSET_H, date(2027, 3, 14))):
            assert slot.backup_worst_case_landing_et(offset_h) == pytest.approx(
                landing_et(max(slot.slot_hours_utc), day)
            )
            assert slot.worst_case_landing_et(offset_h) == pytest.approx(
                landing_et(min(slot.slot_hours_utc), day)
            )

    with pytest.raises(ValueError):
        eastern_offset_h(datetime(2027, 3, 14, 10, 0))


def test_a_freeze_bar_near_midnight_does_not_wrap_into_the_next_morning():
    """`freeze_bar_et_hour` deliberately does not take its sum modulo 24: a bar
    of 24.3 is the honest answer for a run landing 23:18 ET, and wrapping it
    to 00:18 would let it claim tomorrow's 11:00 block. No slot can land that
    late any more — `cron_hour_for` refuses every slot that could — which is
    exactly why the behaviour needs a test rather than a comment."""
    assert freeze_bar_et_hour(23.3) == pytest.approx(23.3 + CARD_LEAD_H)
    assert freeze_bar_et_hour(23.3) > 24


def test_a_slots_verdict_is_the_tip_guards_verdict_on_the_blocks_first_tip():
    """The schedule times the guard. For every slot, trigger and offset, the
    run's end — landing plus the run budget — and the block's first tip are
    put on one real Eastern clock and `gates.tip_state` is asked, and the
    contract's own verdict must agree with `can_be_played`."""
    for slot in SLOTS:
        for label, offset_h, day in OFFSETS:
            first_tip = eastern_instant(day, slot.must_precede_et_hour)
            assert eastern_offset_h(first_tip) == offset_h, f"{day} is not a {label} day"
            for trigger, verdict in (("primary", slot.primary_holds(offset_h)), ("backup", slot.holds(offset_h))):
                done = utc_instant(day, slot.landing_utc_hour(trigger)) + timedelta(
                    minutes=CARD_RUN_BUDGET_MINUTES
                )
                state = tip_state(first_tip.isoformat(), now=done)
                assert verdict == can_be_played(state), (
                    f"{slot.name}/{label}/{trigger}: the contract says "
                    f"{'it covers' if verdict else 'it misses'} the {slot.must_precede_et_hour}:00 ET "
                    f"block and the tip guard reads it {state.value!r} for a run done at "
                    f"{done.astimezone(EASTERN):%H:%M %Z}."
                )
                assert verdict, f"{slot.name}/{label}/{trigger} cannot freeze its block"


def relay_runs_on(day: date) -> list[datetime]:
    """The relay's runs on `day`, read back out of its cron string rather than
    out of the constants that built it, so a hand-edited string is checked too."""
    prefix, minute, hours, day_of_month, months, day_of_week = relay_cron_expression().split()
    assert prefix == f"CRON_TZ={RELAY_TIMEZONE}" and RELAY_TIMEZONE == "America/New_York"
    assert (day_of_month, day_of_week, months) == ("*", "*", SEASON_CRON_MONTHS)
    return [eastern_instant(day, int(hour) + int(minute) / 60) for hour in hours.split(",")]


def card_ready(slot: CardSlot, day: date, trigger: str, lateness_h: float) -> datetime:
    """When `card-feed` holds this trigger's card: its landing plus the time
    the run itself takes."""
    return utc_instant(day, slot.landing_utc_hour(trigger, lateness_h)) + timedelta(
        minutes=CARD_RUN_BUDGET_MINUTES
    )


#: The relay run (Eastern hour, at :52) that carries each slot's card. The
#: relay's schedule is Cooper's and unchanged; these are the runs of it the
#: slots were fitted to.
CARRIER_RELAY_ET_HOUR = {"morning": 10, "evening": 17}


@pytest.mark.parametrize("late_h", ABSORBED_LATENESS_H)
def test_every_card_is_on_the_feed_before_its_relay_run_with_margin_in_both_offsets(late_h):
    """The goal the schedule exists for, stated end to end, for BOTH triggers:
    the card is on `card-feed` at least `RELAY_MARGIN_MINUTES` before the relay
    run that carries it, and that run finishes before the slot's reader. At any
    lateness the wait absorbs, in EST and in EDT."""
    assert set(READER_ET_HOUR) == set(SLOT_NAMES) == set(CARRIER_RELAY_ET_HOUR)
    for slot in SLOTS:
        for label, offset_h, day in OFFSETS:
            reader = eastern_instant(day, READER_ET_HOUR[slot.name])
            assert eastern_offset_h(reader) == offset_h
            (carrier,) = [r for r in relay_runs_on(day) if r.hour == CARRIER_RELAY_ET_HOUR[slot.name]]
            assert carrier.minute == RELAY_MINUTE
            assert carrier + timedelta(minutes=RELAY_BUDGET_MINUTES) <= reader
            for trigger in TRIGGERS:
                ready = card_ready(slot, day, trigger, late_h)
                margin = carrier - ready
                assert margin >= timedelta(minutes=RELAY_MARGIN_MINUTES), (
                    f"{slot.name}/{label}/{trigger} at {late_h}h late: on card-feed at "
                    f"{ready.astimezone(EASTERN):%H:%M %Z}, {margin} before the "
                    f"{carrier:%H:%M} relay run. Move the slot earlier; the relay is Cooper's."
                )


def test_the_tightest_relay_margin_is_the_evening_backup_under_edt():
    margins = {
        (slot.name, label, trigger): (
            [r for r in relay_runs_on(day) if r.hour == CARRIER_RELAY_ET_HOUR[slot.name]][0]
            - card_ready(slot, day, trigger, 0.0)
        )
        for slot in SLOTS
        for label, _offset, day in OFFSETS
        for trigger in TRIGGERS
    }
    tightest = min(margins, key=margins.get)
    assert tightest == ("evening", "EDT", "backup")
    assert margins[tightest] == timedelta(minutes=32)


def test_no_later_whole_hour_would_hold():
    """"As close to tip as the constraints allow", checked rather than claimed:
    moving either slot's pair one hour later breaks the freeze or the relay for
    its backup under EDT."""
    for slot in SLOTS:
        later = CardSlot(
            name=slot.name,
            slot_hours_utc=tuple(h + 1 for h in slot.slot_hours_utc),
            must_precede_et_hour=slot.must_precede_et_hour,
            what=slot.what,
        )
        carrier = eastern_instant(AN_EDT_SLATE_DAY, CARRIER_RELAY_ET_HOUR[slot.name] + RELAY_MINUTE / 60)
        late_ready = card_ready(later, AN_EDT_SLATE_DAY, "backup", 0.0)
        assert (not later.holds(EDT_OFFSET_H)) or (
            carrier - late_ready < timedelta(minutes=RELAY_MARGIN_MINUTES)
        ), f"{slot.name} could land an hour later and still hold; the slot is not the latest"


def test_an_earlier_slot_is_relayed_before_the_next_slot_can_replace_it():
    """The relay copies whatever is newest on `card-feed`, so a card is lost to
    Drive if the next slot publishes before a relay run has copied it. The
    next slot can publish no earlier than its primary's slot, because the wait
    never releases a run early."""
    for label, _offset, day in OFFSETS:
        for index, slot in enumerate(SLOTS):
            following = SLOTS[(index + 1) % len(SLOTS)]
            next_day = day if index + 1 < len(SLOTS) else day + timedelta(days=1)
            relays = relay_runs_on(day) + relay_runs_on(next_day)
            replaced_from = utc_instant(next_day, following.landing_utc_hour("primary"))
            for trigger in TRIGGERS:
                ready = card_ready(slot, day, trigger, 0.0)
                assert any(
                    ready <= run and run + timedelta(minutes=RELAY_BUDGET_MINUTES) <= replaced_from
                    for run in relays
                ), f"{slot.name}/{label}/{trigger}: no relay run between its card and the {following.name} card"


#: How late a PRIMARY's cron can fire, in hours, before it misses its block
#: or its relay run under EDT — the slack beyond the eight-hour wait. Computed
#: by scanning minutes, pinned here so a moved slot says what it cost.
PRIMARY_TOLERANCE_H_EDT = {"morning": 9 + 39 / 60, "evening": 9 + 32 / 60}


def _tolerance_h(slot: CardSlot, day: date) -> float:
    carrier = [r for r in relay_runs_on(day) if r.hour == CARRIER_RELAY_ET_HOUR[slot.name]][0]
    first_tip = eastern_instant(day, slot.must_precede_et_hour)
    minutes = 0
    while True:
        late_h = (minutes + 1) / 60
        done = card_ready(slot, day, "primary", late_h)
        if done > carrier or not can_be_played(tip_state(first_tip.isoformat(), now=done)):
            return minutes / 60
        minutes += 1


def test_what_a_run_later_than_the_lead_does_is_computed_and_named():
    """Beyond the lead the run does not wait: it lands at cron + lateness. The
    slack between the slot and the constraints means each primary still holds
    past eight hours — up to about nine and a half under EDT — but not the
    9.85h run of 2026-08-27, which would put the evening card on the feed after
    the 17:52 relay under EDT. Recorded, not chased: sizing for one day's
    lateness would price the whole season an hour or more earlier."""
    for slot in SLOTS:
        tolerance = _tolerance_h(slot, AN_EDT_SLATE_DAY)
        assert tolerance == pytest.approx(PRIMARY_TOLERANCE_H_EDT[slot.name], abs=1 / 120), slot.name
        assert tolerance > WAIT_LEAD_H > OBSERVED_LATENESS_H
        assert _tolerance_h(slot, AN_EST_SLATE_DAY) > tolerance
    assert MORNING.landing_utc_hour("primary", 9.85) == pytest.approx(13.85)
    assert card_ready(EVENING, AN_EDT_SLATE_DAY, "primary", 9.85) > eastern_instant(AN_EDT_SLATE_DAY, 17 + 52 / 60)


def test_each_slot_has_a_trigger_pair():
    for slot in SLOTS:
        assert len(slot.slot_hours_utc) == 2 and slot.slot_hours_utc[1] == slot.slot_hours_utc[0] + 1, slot.name


def test_the_lateness_constant_is_not_quietly_optimistic():
    assert OBSERVED_LATENESS_H >= 7.4, (
        "7.4 hours is the worst lateness measured on every day but one since "
        "2026-08-27 (data/outputs/cbb_cron_lateness.json). Lowering this "
        "constant makes every deadline in this repository pass on paper "
        "without changing anything about when a card lands."
    )


LATENESS_RECORD = Path(__file__).resolve().parents[1] / "data" / "outputs" / "cbb_cron_lateness.json"

#: Every run in the lateness record that fired later than `OBSERVED_LATENESS_H`,
#: as (repository, workflow, nominal instant). Both are EPL's Thursday crons on
#: 2026-08-27, the first day of the lateness Cooper reported, at 9.61h and
#: 9.85h. They exceed the eight-hour wait lead as well; what a card fired that
#: late does is pinned in
#: `test_what_a_run_later_than_the_lead_does_is_computed_and_named` below.
RUNS_LATER_THAN_THE_CONSTANT = {
    ("epl-betting-lab", "matchday-refresh.yml", "2026-08-27T11:30:00+00:00"),
    ("epl-betting-lab", "matchday-refresh.yml", "2026-08-27T13:00:00+00:00"),
}


def test_the_lateness_constant_covers_every_measured_run_but_the_named_ones():
    """The floor above is a number somebody typed. This one is an observation.

    `OBSERVED_LATENESS_H` was 5.3 for four weeks under a docstring that said
    "measured", while the same account's crons had run 7.38 hours late. Nothing
    held the constant to a measurement because there was none on disk; now
    `scripts/measure_cron_lateness.py` writes one, and this fails the day a
    re-measurement finds a run later than the constant that is not named in
    `RUNS_LATER_THAN_THE_CONSTANT` — in either direction, so a named run that
    disappears from the record is a change somebody has to look at too.
    """
    import json

    record = json.loads(LATENESS_RECORD.read_text(encoding="utf-8"))
    runs = record["worst_runs"]
    assert record["matched_runs"] >= 500 and len(runs) >= 10, (
        "the lateness record is too thin to hold a constant to"
    )
    assert record["worst_h"] == max(run["lateness_h"] for run in runs)
    # The record keeps only the worst runs. If even the last of them is later
    # than the constant, runs the constant does not cover may have been cut.
    assert min(run["lateness_h"] for run in runs) <= OBSERVED_LATENESS_H, (
        "every run the record kept is later than the constant, so it may have "
        "truncated some that are too; raise TOP_N in the script and re-measure"
    )
    later = {
        (run["repository"], run["workflow"], run["nominal_utc"])
        for run in runs
        if run["lateness_h"] > OBSERVED_LATENESS_H
    }
    assert later == RUNS_LATER_THAN_THE_CONSTANT, (
        f"runs later than {OBSERVED_LATENESS_H}h have changed.\n"
        f"  in the record: {sorted(later)}\n"
        f"  named here:    {sorted(RUNS_LATER_THAN_THE_CONSTANT)}\n"
        "Raise OBSERVED_LATENESS_H and let the tests below say which crons "
        "move, or name the run here and tell Cooper the schedule does not "
        "survive it. Do not edit the record."
    )


def test_an_unknown_slot_raises_rather_than_defaulting():
    with pytest.raises(KeyError):
        slot_for("afternoon")



def test_the_uncardable_share_is_the_measured_one_and_named_rather_than_zero():
    """Two games of the 2025-26 slate tip before even the morning BACKUP can
    freeze them, in either offset, and the number was 37 under the old crons.

    **What this test measured before, and why.** The worst-late morning backup
    landed 10:24 EST / 11:24 EDT and could freeze nothing tipping at or before
    11:24 ET: 37 games, 0.59% of the slate, 34 of them the 11:00 ET block
    itself, and one of them the 2026-27 opener in Rome. It was a recorded
    coverage gap. The backup now lands 08:00 EST / 09:00 EDT, done by the end
    of its run budget, and the bar is 09:20 EST / 10:20 EDT.

    **The two that remain**, to the minute on the completed season: a 08:00 ET
    neutral-site game on 2025-11-03, and the Honolulu game at 01:00 ET on
    2025-11-10 — counted here because a time-of-day bar counts it, although it
    belongs to the previous night's slate and the evening card prices it.
    VCU v Virginia Tech at 10:30 ET on 2025-11-28, which the old record once
    miscounted, clears both bars. `<=`, because `tip_state` quarantines
    `delta <= IMMINENT_MINUTES`. Do not widen the tolerance; if the constants or
    the fixture move, update `docs/card_cadence.md` and this number together.
    """
    frame = pd.read_parquet(schedule_fixture(2026), columns=["date"])
    assert len(frame) == 6_318
    tips = pd.to_datetime(frame["date"], utc=True).dt.tz_convert(ZoneInfo("America/New_York"))
    tip_hours = tips.dt.hour + tips.dt.minute / 60
    morning = slot_for("morning")
    for offset_h, expected_bar in ((EST_OFFSET_H, 8 + CARD_RUN_BUDGET_H + CARD_LEAD_H), (EDT_OFFSET_H, 9 + CARD_RUN_BUDGET_H + CARD_LEAD_H)):
        bar = morning.backup_worst_case_freeze_bar_et(offset_h)
        assert bar == pytest.approx(expected_bar)
        uncardable = tip_hours <= bar
        assert int(uncardable.sum()) == 2, (
            f"{int(uncardable.sum())} games of the 2025-26 slate tip at or before the "
            f"morning backup's freeze bar of {bar:.2f} ET; the recorded figure is 2."
        )
        assert sorted(tips[uncardable].dt.strftime("%Y-%m-%d %H:%M")) == [
            "2025-11-03 08:00",
            "2025-11-10 01:00",
        ]
    # What the move bought: the bar the lateness-driven backup had.
    assert int((tip_hours <= 11.4).sum()) == 37


def test_the_evening_slot_still_earns_its_cron():
    frame = pd.read_parquet(schedule_fixture(2026), columns=["date"])
    assert len(frame) > 6_000
    hours = (
        pd.to_datetime(frame["date"], utc=True)
        .dt.tz_convert(ZoneInfo("America/New_York"))
        .dt.hour
    )
    evening: CardSlot = slot_for("evening")
    share_after = float((hours >= evening.must_precede_et_hour).mean())
    assert share_after > 0.4, (
        f"Only {share_after:.1%} of games tip at or after "
        f"{evening.must_precede_et_hour}:00 ET. If that has fallen this far, "
        "the evening slot is no longer earning its cron."
    )


# --------------------------------------------------------------------------
# The crons in the workflow, pinned to the contract that reasons about them
#
# `docs/card_cadence.md` said, of the schedule table it prints: *"The test pins
# the sign on those two instants and the gap as written, so the day the crons
# move or the lateness changes, the record changes with them or the build goes
# red."* Half of that was true. The lateness constant was pinned and the DST
# instants were pinned; **the cron strings in the workflow were pinned to
# nothing.** Every test in this file above computed its table from
# `schedule_contract` and none of them had ever read
# `.github/workflows/cbb-gameday-refresh.yml`, so a cron moved in the workflow
# left the module, the document and this file all agreeing with each other
# about a schedule the repository no longer ran.
#
# That is the worst shape a schedule check can have: the arithmetic stays
# correct, the prose stays confident, and the thing being described has moved.
# --------------------------------------------------------------------------

GAMEDAY_WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "cbb-gameday-refresh.yml"
)


def workflow_crons() -> list[str]:
    """`on.schedule` from the gameday workflow, parsed rather than grepped.

    `on` is the YAML 1.1 boolean `True` once loaded, which is why it is looked
    up under both spellings: a regex over the text would also match the four
    cron strings quoted in this file's own comments and in the workflow's
    header prose, and would then pass while the real `on.schedule` said
    something else.
    """
    import yaml

    document = yaml.safe_load(GAMEDAY_WORKFLOW.read_text(encoding="utf-8"))
    triggers = document.get("on", document.get(True))
    assert isinstance(triggers, dict), (
        f"{GAMEDAY_WORKFLOW.name} declares no `on:` mapping, so it has no "
        "schedule to pin."
    )
    schedule = triggers.get("schedule")
    assert isinstance(schedule, list) and schedule, (
        f"{GAMEDAY_WORKFLOW.name} declares no `on.schedule`. The card is a "
        "scheduled job; a workflow that only runs on dispatch freezes no "
        "opinion on a day nobody is watching."
    )
    return [str(entry["cron"]) for entry in schedule]


def test_the_gameday_workflow_crons_are_exactly_the_ones_the_contract_declares():
    """The pin `docs/card_cadence.md` said existed.

    Equality in both directions. A cron the contract does not declare is a card
    fired at a time nothing in this file has checked against the lateness; a
    cron the contract declares and the workflow has dropped is the quieter
    failure, because a workflow missing its backup trigger looks exactly like a
    healthy one until the primary is skipped.
    """
    assert workflow_crons() == list(cron_expressions()), (
        f"{GAMEDAY_WORKFLOW.name}'s `on.schedule` is not what "
        "`schedule_contract.cron_expressions()` declares.\n"
        f"  workflow: {workflow_crons()}\n"
        f"  contract: {list(cron_expressions())}\n"
        "Move the trigger in `schedule_contract` and let the workflow follow, "
        "so the arithmetic in this file is about the schedule that actually "
        "runs. Do not edit one of the two to match the other."
    )



def test_every_declared_cron_has_the_shape_the_wait_reads():
    """One minute and one hour, every day of every season month — the wait
    reads the minute and hour back to find its slot, and a list or a step
    would raise there and run the card at once."""
    for expression in cron_expressions():
        minute, hour, day_of_month, months, day_of_week = expression.split()
        assert (minute, day_of_month, day_of_week) == (str(CRON_MINUTE), "*", "*"), expression
        assert hour.isdigit(), expression
        assert months == SEASON_CRON_MONTHS, expression
        wfr.round_for(expression, datetime(2026, 12, 2, 23, 0, tzinfo=timezone.utc))


# --------------------------------------------------------------------------
# The slot a run publishes as, decided by a shell `case` nothing pinned
#
# The workflow names its slot from the hour of the cron that fired it, in a
# `case` inside the `already-published` job, and an hour it did not list fell
# through to `morning`. The pin above held `on.schedule` to the contract and
# nothing held the `case` to either: moving the crons as this file demands
# would have published every evening card as the morning's, and then stood
# the evening down on any day the morning card was clean. This runs that step.
# --------------------------------------------------------------------------


def _run_the_slot_guard(tmp_path: Path, *, event: str, schedule: str, dispatch_slot: str = ""):
    """The `already-published` job's `check` step, as written, under real bash
    and awk, with a `git` that cannot fetch — the step's own "no card-feed
    branch yet" path, so it decides the slot exactly as a runner would and
    then stops without touching a network."""
    import shutil
    import subprocess

    import yaml

    document = yaml.safe_load(GAMEDAY_WORKFLOW.read_text(encoding="utf-8"))
    steps = document["jobs"]["already-published"]["steps"]
    (step,) = [s for s in steps if s.get("id") == "check"]
    script = step["run"]
    script = script.replace("${{ github.event_name }}", event)
    script = script.replace("${{ github.repository }}", "owner/repository")
    assert "${{" not in script, "the check step reads an expression this harness does not supply"

    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_git = bin_dir / "git"
    fake_git.write_text(
        "#!/bin/sh\n"
        'if [ "$1" = init ]; then for last; do :; done; /bin/mkdir -p "$last"; exit 0; fi\n'
        "exit 1\n",
        encoding="utf-8",
    )
    fake_git.chmod(0o755)
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    (tmp_path / "step.sh").write_text(script, encoding="utf-8")
    bash = shutil.which("bash")
    assert bash, "no bash on PATH: the slot guard cannot be run"
    completed = subprocess.run(
        [bash, "-e", str(tmp_path / "step.sh")],
        cwd=tmp_path,
        env={
            "PATH": f"{bin_dir}:/usr/bin:/bin",
            "HOME": str(tmp_path),
            "GITHUB_OUTPUT": str(output),
            "GH_TOKEN": "not-a-token",
            "SCHEDULE": schedule,
            "DISPATCH_SLOT": dispatch_slot,
        },
        capture_output=True,
        text=True,
        timeout=60,
    )
    outputs = dict(
        line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines() if "=" in line
    )
    return completed, outputs




def test_every_declared_cron_names_its_own_slot_when_the_guard_runs(tmp_path: Path):
    """Each cron publishes as the slot the contract says — and as the slot the
    cron it replaced published as, from the hand-written table at the top of
    this file. A cron moved without its `case` line is a red build rather than
    an evening card published as the morning's."""
    derived = {
        f"{CRON_MINUTE} {hour} * {SEASON_CRON_MONTHS} *": slot.name
        for slot in SLOTS
        for hour in slot.cron_hours_utc
    }
    assert derived == CRON_TO_SLOT_NAME
    assert set(CRON_TO_SLOT_NAME) == set(cron_expressions()) == set(workflow_crons())
    for expression, slot_name in CRON_TO_SLOT_NAME.items():
        case = tmp_path / expression.split()[1]
        case.mkdir()
        completed, outputs = _run_the_slot_guard(case, event="schedule", schedule=expression)
        assert completed.returncode == 0, (
            f"the slot guard failed for the contract cron {expression!r}:\n{completed.stdout}{completed.stderr}"
        )
        assert outputs.get("card_slot") == slot_name, (
            f"a run fired by {expression!r} publishes as {outputs.get('card_slot')!r}, "
            f"and the contract says it is the {slot_name!r} slot. The hours in the "
            "`case` of the `already-published` job must follow `schedule_contract`."
        )
        assert outputs.get("run") == "yes"


def test_a_cron_hour_the_guard_does_not_know_is_refused_rather_than_called_morning(tmp_path: Path):
    """The fall-through was the defect. An hour no slot owns must stop the run
    loudly — a failed run is noticed; a mislabelled card is not. The retired
    hours are refused too, so a `case` left naming them is not dead weight
    that would one day claim a cron somebody adds for another reason."""
    declared = {hour for slot in SLOTS for hour in slot.cron_hours_utc}
    stray = next(hour for hour in range(24) if hour not in declared)
    for hour in (stray, *RETIRED_CRON_HOURS_UTC):
        assert hour not in declared
        case = tmp_path / f"h{hour}"
        case.mkdir()
        completed, outputs = _run_the_slot_guard(
            case, event="schedule", schedule=f"0 {hour} * {SEASON_CRON_MONTHS} *"
        )
        assert completed.returncode != 0, hour
        assert "card_slot" not in outputs and "run" not in outputs
        assert "belongs to no card slot" in completed.stdout


def test_a_dispatch_publishes_as_the_slot_it_asked_for(tmp_path: Path):
    for slot in SLOTS:
        case = tmp_path / slot.name
        case.mkdir()
        completed, outputs = _run_the_slot_guard(
            case, event="workflow_dispatch", schedule="", dispatch_slot=slot.name
        )
        assert completed.returncode == 0, completed.stderr
        assert outputs == {"card_slot": slot.name, "run": "yes"}


# --------------------------------------------------------------------------
# The wiring: the waits sit in front of the guard, and nothing skips the card
#
# A correct wait the card does not wait for fixes nothing, and a wait whose
# failure skips the card is worse than no wait. These read the parsed workflow.
# --------------------------------------------------------------------------


def _jobs() -> dict:
    document = yaml.safe_load(GAMEDAY_WORKFLOW.read_text(encoding="utf-8"))
    return document["jobs"]


def _wait_step(job: dict) -> dict:
    (step,) = [s for s in job["steps"] if "wait_for_round.py" in str(s.get("run", ""))]
    return step


def test_the_card_waits_behind_both_waits_and_the_guard():
    jobs = _jobs()
    assert set(jobs) == {"wait", "wait-more", "already-published", "card"}
    assert "needs" not in jobs["wait"]
    assert jobs["wait-more"]["needs"] == "wait"
    assert jobs["already-published"]["needs"] == "wait-more"
    assert jobs["card"]["needs"] == "already-published"


def test_no_condition_upstream_of_the_card_can_silently_skip_it():
    """Spelled out on every job downstream of a wait. A job with no `if`, or a
    bare one, carries an implicit success() over EVERY job upstream — the waits
    included — so a wait that failed would skip the card. `always()` would be
    wrong the other way: it keeps running a run somebody cancelled."""
    jobs = _jobs()
    for name in ("wait-more", "already-published", "card"):
        condition = str(jobs[name].get("if", ""))
        assert condition.startswith("${{") and condition.endswith("}}"), (name, condition)
        assert "!cancelled()" in condition, name
        assert "always()" not in condition, name
    card = str(jobs["card"]["if"])
    assert "needs.already-published.result == 'success'" in card, (
        "a guard that refused an unknown cron hour has named no slot; the card must not run"
    )
    assert "needs.already-published.outputs.run == 'yes'" in card


def test_both_waits_read_the_cron_that_fired_the_run_and_cover_the_lead():
    jobs = _jobs()
    budgets = []
    for name in ("wait", "wait-more"):
        step = _wait_step(jobs[name])
        assert step["env"]["SCHEDULE"] == "${{ github.event.schedule }}", name
        assert '--schedule "$SCHEDULE"' in step["run"], name
        budget = float(step["run"].split("--budget-minutes")[1].split()[0])
        assert budget < int(jobs[name]["timeout-minutes"]) <= 360, name
        assert "secrets." not in str(jobs[name]), name
        budgets.append(budget)
    assert timedelta(minutes=sum(budgets)) >= timedelta(hours=WAIT_LEAD_H)


def test_concurrency_is_on_the_card_job_not_the_workflow():
    """A workflow-level group keeps one run pending and cancels the one before
    it, and every run now spends hours pending behind its wait: the morning
    backup's run would be cancelled by the evening primary's cron."""
    document = yaml.safe_load(GAMEDAY_WORKFLOW.read_text(encoding="utf-8"))
    assert "concurrency" not in document
    assert document["jobs"]["card"]["concurrency"] == {
        "group": "cbb-gameday-refresh",
        "cancel-in-progress": False,
    }
    for name in ("wait", "wait-more", "already-published"):
        assert "concurrency" not in document["jobs"][name], name


# --------------------------------------------------------------------------
# The documents Cooper and the relay were given
# --------------------------------------------------------------------------


def test_the_relay_script_builds_the_contract_cron():
    import importlib.util

    path = Path(__file__).resolve().parents[1] / "scripts" / "create_card_relay_routine.py"
    spec = importlib.util.spec_from_file_location("create_card_relay_routine", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.body()["cron_expression"] == relay_cron_expression()
    # The two figures the relay prompt carried that the repository contradicts.
    assert "private repository" not in module.PROMPT
    assert "45% of games have not tipped" not in module.PROMPT


DOCS = Path(__file__).resolve().parents[1] / "docs"


def test_the_readers_cooper_was_told_to_set_are_the_ones_the_contract_checks():
    """`docs/chat_task_prompt.md` is where Cooper was given his read times. If
    that page and `READER_ET_HOUR` disagree, the chain above is checked against
    reads that do not happen."""
    import re

    text = (DOCS / "chat_task_prompt.md").read_text(encoding="utf-8")
    rows = dict(re.findall(r"\|\s*`CBB CARD — (\w+)`\s*\|\s*\*\*(\d{1,2}:\d{2})\*\*", text))
    assert rows, "chat_task_prompt.md's table of read times did not parse"
    as_hours = {name: int(t[:-3]) + int(t[-2:]) / 60 for name, t in rows.items()}
    assert as_hours == READER_ET_HOUR


def test_the_delivery_chain_page_names_the_relay_cron_the_contract_builds():
    text = (DOCS / "delivery_chain.md").read_text(encoding="utf-8")
    assert f"`{relay_cron_expression()}`" in text, (
        "docs/delivery_chain.md does not name the relay cron the contract builds"
    )
