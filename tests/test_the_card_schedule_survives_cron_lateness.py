"""Every slot must be able to FREEZE its games, at the worst lateness observed.

GitHub has been firing Cooper's crons 4.5-5.3 hours late since 2026-08-27, so a
schedule checked against its nominal time is a schedule checked against a
fiction. This test recomputes the whole table from `OBSERVED_LATENESS_H`, which
means raising that constant when GitHub gets worse is a one-line change that
proves itself rather than a note somebody has to act on.

**And landing is not freezing.** Every check in this file used to compare a
landing to a tip hour, which is the arithmetic `schedule_contract.holds()` did
— and the card cannot freeze a game tipping inside `CARD_LEAD_MINUTES` of the
run, because `gates.tip_state` calls it `IMMINENT`, `can_be_played` refuses it
and `reports/gameday_card.py._rows_to_freeze` drops it before it ever reaches
the append-only store. Sixty minutes were missing from every bar here, so this
file was green while the morning backup already failed to cover its block. The
cross-check that would have caught it is
`test_a_slots_verdict_is_the_tip_guards_verdict_on_the_blocks_first_tip`: it
puts a landing and a tip on one real clock and asks `gates` itself, instead of
recomputing the schedule's own arithmetic a second time and agreeing with it.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from conftest import schedule_fixture
from zoneinfo import ZoneInfo

from cbb_betting_lab.config import RAW_DIR
from cbb_betting_lab.gates import can_be_played, tip_state
from cbb_betting_lab.schedule_contract import (
    CARD_LEAD_H,
    CARD_LEAD_MINUTES,
    CRON_MINUTE,
    EASTERN,
    EDT_OFFSET_H,
    EST_OFFSET_H,
    EVENING,
    MORNING,
    OBSERVED_LATENESS_H,
    SEASON_CRON_MONTHS,
    SLOTS,
    CardSlot,
    cron_expressions,
    eastern_offset_h,
    freeze_bar_et_hour,
    landing_et,
    slot_for,
)

#: The same cron instant — 10:00 UTC, the morning backup — on the last day of
#: EST and the first day of EDT. DST begins 2027-03-14 at 02:00 EST (07:00
#: UTC), so 10:00 UTC on the 14th is already an EDT instant.
LAST_EST_MORNING = datetime(2027, 3, 13, 10, 0, tzinfo=timezone.utc)
FIRST_EDT_MORNING = datetime(2027, 3, 14, 10, 0, tzinfo=timezone.utc)


def test_every_slot_can_freeze_its_block_from_its_primary_even_at_worst_lateness():
    """The strongest statement that is true of EVERY slot, and it is not the
    one this test used to make.

    It asserted `slot.holds()` — the BACKUP landing before the block — and
    `holds()` compared a bare landing to a tip hour with no card lead, sixty
    minutes below the bar `gates` actually enforces. Under that reading all
    four slot/offset cells passed; under the real one, three of them cannot
    freeze the block they name, and the morning backup has not covered its
    11:00 ET block at any point since the lateness reached 5.0h. It is 5.3h.

    So the promise left that every slot keeps is the PRIMARY's: at the worst
    lateness observed, each slot's first trigger still lands a full
    `CARD_LEAD_MINUTES` before its block in EST, the offset the season runs in.
    That is a weaker promise than the one this file used to print, and it is
    the true one. The cells that fail are not swept up here — they are named,
    one by one, in
    `test_the_cells_that_cannot_freeze_their_block_are_the_ones_written_down`,
    which fails if that set ever grows. Do NOT restore the blanket assertion by
    dropping the lead; the lead is the whole finding.
    """
    for slot in SLOTS:
        assert slot.primary_holds(), (
            f"Slot {slot.name!r} fires nominally at {slot.cron_hours_utc} UTC. "
            f"At the observed {OBSERVED_LATENESS_H}h lateness its PRIMARY lands "
            f"at {slot.worst_case_landing_et():.2f} ET and so can freeze nothing "
            f"tipping before {slot.worst_case_freeze_bar_et():.2f} ET — the "
            f"landing plus the {CARD_LEAD_MINUTES}-minute card lead the tip "
            f"guard enforces — which does not reach the "
            f"{slot.must_precede_et_hour}:00 ET block it exists to cover. Move "
            "the cron earlier — do not lower the lateness constant, and do not "
            "drop the lead."
        )


def test_dst_moves_a_fixed_utc_cron_later_on_an_eastern_clock():
    """`schedule_contract.py` used to say DST moves every landing an hour
    *earlier* in ET, "the safe direction". Measured on two concrete instants
    from the tz database, not asserted: 10:00 UTC is 05:00 on 2027-03-13 and
    06:00 on 2027-03-14. Later, by exactly one hour, toward the first tip."""
    eastern = ZoneInfo("America/New_York")
    assert LAST_EST_MORNING.astimezone(eastern).strftime("%H:%M %Z") == "05:00 EST"
    assert FIRST_EDT_MORNING.astimezone(eastern).strftime("%H:%M %Z") == "06:00 EDT"

    assert eastern_offset_h(LAST_EST_MORNING) == EST_OFFSET_H == -5
    assert eastern_offset_h(FIRST_EDT_MORNING) == EDT_OFFSET_H == -4

    before = landing_et(10, date(2027, 3, 13))
    after = landing_et(10, date(2027, 3, 14))
    assert (before, after) == (5.0, 6.0)
    assert after - before == 1.0, "a fixed UTC cron lands LATER in Eastern wall-clock time under DST, not earlier"

    # The slot arithmetic agrees with the tz database on both sides of the switch.
    for slot in SLOTS:
        for offset_h, day in ((EST_OFFSET_H, date(2027, 3, 13)), (EDT_OFFSET_H, date(2027, 3, 14))):
            assert slot.backup_worst_case_landing_et(offset_h) == pytest.approx(
                landing_et(max(slot.cron_hours_utc), day, OBSERVED_LATENESS_H)
            )
            assert slot.worst_case_landing_et(offset_h) == pytest.approx(
                landing_et(min(slot.cron_hours_utc), day, OBSERVED_LATENESS_H)
            )

    with pytest.raises(ValueError):
        eastern_offset_h(datetime(2027, 3, 14, 10, 0))


#: Every `(slot, offset, trigger)` that CANNOT freeze the first tip of its own
#: block at `OBSERVED_LATENESS_H`, once the card lead is applied. Written out by
#: hand so that the arithmetic below has a record to disagree with, and so the
#: cost of this schedule is a list somebody can read rather than a boolean.
#:
#: **One of these four was recorded before and three were not.** This file used
#: to pin a single DST gap — the morning backup landing 11:18 ET from
#: 2027-03-14 — because `holds()` compared a bare landing to a tip hour. With
#: the `CARD_LEAD_MINUTES` the tip guard actually enforces, the morning backup
#: misses its 11:00 ET block in EST too, which is the whole season and not the
#: last three weeks of it; the morning primary joins it under EDT; and the
#: evening backup lands 18:18 EDT and so reaches nothing before 19:18.
CELLS_THAT_CANNOT_FREEZE_THEIR_BLOCK = {
    ("morning", "EST", "backup"),
    ("morning", "EDT", "primary"),
    ("morning", "EDT", "backup"),
    ("evening", "EDT", "backup"),
}


def test_the_cells_that_cannot_freeze_their_block_are_the_ones_written_down():
    """The gaps, named one at a time, in both directions.

    A gap that appears fails this test, and so does a gap that disappears —
    because the day a cron moves or the lateness constant changes, the record
    in `docs/card_cadence.md` and the workflow header has to move with it or it
    is describing a schedule this repository no longer runs. Do not delete a
    line from the set above to make the build green; that is the gap being
    hidden rather than closed.

    These gaps are recorded rather than chased, on the same reasoning the lab
    applied when it was one gap instead of four: moving the morning pair to
    08:00/09:00 UTC would close the EST half of it, and would card every day of
    the season an hour earlier with an hour less information, to buy a handful
    of 11:00 ET tips on the days the primary was also dropped. **It is a
    coverage gap, not a fault** — but it is four cells and 0.59% of the slate,
    not one cell and 0.05%, and the number a reader acts on has to be the real
    one.
    """
    measured = {
        (slot.name, label, trigger)
        for slot in SLOTS
        for label, offset_h in (("EST", EST_OFFSET_H), ("EDT", EDT_OFFSET_H))
        for trigger, held in (
            ("primary", slot.primary_holds(offset_h)),
            ("backup", slot.holds(offset_h)),
        )
        if not held
    }
    assert measured == CELLS_THAT_CANNOT_FREEZE_THEIR_BLOCK, (
        "the set of slot/offset/trigger cells that cannot freeze their block "
        f"has moved.\n  measured: {sorted(measured)}\n  recorded: "
        f"{sorted(CELLS_THAT_CANNOT_FREEZE_THEIR_BLOCK)}\n"
        "Update docs/card_cadence.md, the workflow header and this set "
        "together, in whichever direction it moved."
    )

    # The DST instant this file has always pinned, kept explicit: the morning
    # backup's landing under EDT, and the tip bar an hour past it.
    backup = MORNING.backup_worst_case_landing_et(EDT_OFFSET_H)
    assert backup == pytest.approx(max(MORNING.cron_hours_utc) + OBSERVED_LATENESS_H + EDT_OFFSET_H)
    assert backup == pytest.approx(11.3), (
        f"the recorded gap is the morning backup landing 11:18 ET under EDT; it now lands {backup:.2f} ET. "
        "Update docs/card_cadence.md, the workflow header and this test together."
    )
    assert MORNING.backup_worst_case_freeze_bar_et(EDT_OFFSET_H) == pytest.approx(
        11.3 + CARD_LEAD_H
    )

    # And the EST cell the old bar hid: the backup lands 42 minutes before the
    # first tip, which is INSIDE the lab's own 60-minute guard. That 42 is the
    # figure `docs/card_cadence.md` and the workflow header both printed as the
    # slot's safety margin.
    margin_h = MORNING.must_precede_et_hour - MORNING.backup_worst_case_landing_et(EST_OFFSET_H)
    assert margin_h == pytest.approx(0.7)
    assert margin_h * 60 < CARD_LEAD_MINUTES, (
        f"the morning backup's EST margin is {margin_h * 60:.0f} minutes against a "
        f"{CARD_LEAD_MINUTES}-minute card lead. If this has become a real margin the "
        "crons moved, and the record above is out of date."
    )


def test_a_landing_near_midnight_does_not_wrap_into_the_next_morning():
    """`freeze_bar_et_hour` deliberately does not take its sum modulo 24, and
    this is the case that decides it.

    The landings it is given already wrap, so a slot whose backup lands 23:18
    ET reads 23.3 — and a bar of 24.3 is the honest answer, because that run
    can freeze nothing else today. Wrapping the bar to 00:18 would let it claim
    to cover an 11:00 ET block on a morning it has not reached, which is the
    same shape of optimism as omitting the lead in the first place. No declared
    slot fires this late, which is exactly why the behaviour needs a test
    rather than a comment.
    """
    assert freeze_bar_et_hour(23.3) == pytest.approx(23.3 + CARD_LEAD_H)
    assert freeze_bar_et_hour(23.3) > 24, "the bar wrapped, and a wrapped bar covers tomorrow"

    midnight = CardSlot(
        name="midnight",
        cron_hours_utc=(22, 23),
        must_precede_et_hour=11,
        what="a slot this lab does not run, here only to pin the wrap",
    )
    assert midnight.backup_worst_case_landing_et() == pytest.approx(23.3)
    assert not midnight.holds(), "a slot landing 23:18 ET covers no 11:00 ET block"
    assert not midnight.primary_holds()


#: Two ordinary slate days, one either side of the 2027-03-14 switch, used to
#: put a landing and a tip on the same real Eastern clock. Neither contains a
#: transition, so adding hours to midnight is honest wall-clock arithmetic, and
#: each is checked against the tz database before it is used.
AN_EST_SLATE_DAY = date(2026, 12, 2)
AN_EDT_SLATE_DAY = date(2027, 3, 17)


def eastern_instant(day: date, et_hour: float) -> datetime:
    """`et_hour` on `day`, as a real Eastern instant."""
    return datetime(day.year, day.month, day.day, tzinfo=EASTERN) + timedelta(hours=et_hour)


def test_a_slots_verdict_is_the_tip_guards_verdict_on_the_blocks_first_tip():
    """The check nothing in this repository made: the schedule times the guard.

    `tests/test_gates_fail_closed.py` pins `gates.IMMINENT_MINUTES` to
    `schedule_contract.CARD_LEAD_MINUTES`, and every test in this file computed
    its bar from a slot landing. Neither ever put the two in one sentence, so a
    contract that said a slot covered its block and a guard that quarantined
    every game in it could both be green at once — and were, for the morning
    slot, at the lateness being observed the day it was found.

    This asks `gates` rather than recomputing the schedule's own arithmetic: it
    builds the worst-case landing and the block's first tip as real Eastern
    instants on a real slate day, runs `tip_state` on the pair exactly as the
    card does, and requires the slot's own verdict to agree with
    `can_be_played`. An independent implementation, on the module that actually
    decides what gets written to the append-only store.
    """
    for slot in SLOTS:
        for label, offset_h, day in (
            ("EST", EST_OFFSET_H, AN_EST_SLATE_DAY),
            ("EDT", EDT_OFFSET_H, AN_EDT_SLATE_DAY),
        ):
            first_tip = eastern_instant(day, slot.must_precede_et_hour)
            assert eastern_offset_h(first_tip) == offset_h, (
                f"{day} is not a {label} day in the tz database, so this case is "
                "checking an offset the season does not run in"
            )
            for trigger, landing, verdict in (
                ("primary", slot.worst_case_landing_et(offset_h), slot.primary_holds(offset_h)),
                ("backup", slot.backup_worst_case_landing_et(offset_h), slot.holds(offset_h)),
            ):
                fired = eastern_instant(day, landing)
                state = tip_state(first_tip.isoformat(), now=fired)
                assert verdict == can_be_played(state), (
                    f"{slot.name}/{label}/{trigger}: the schedule contract says "
                    f"{'it covers' if verdict else 'it misses'} the "
                    f"{slot.must_precede_et_hour}:00 ET block, and the tip guard reads "
                    f"that game as {state.value!r} for a run landing {fired:%H:%M} ET. "
                    "The contract and the guard have to agree: the guard is what "
                    "decides whether the row is ever written to the append-only "
                    "store, and `holds()` is only a promise about it."
                )


def test_each_slot_has_a_trigger_pair():
    """One trigger cannot hold both a relay deadline and a freshness bar."""
    for slot in SLOTS:
        assert len(slot.cron_hours_utc) >= 2, (
            f"Slot {slot.name!r} has one trigger. The brief requires early "
            "trigger pairs where one trigger cannot hold both."
        )


def test_the_lateness_constant_is_not_quietly_optimistic():
    assert OBSERVED_LATENESS_H >= 5.3, (
        "5.3 hours is the worst lateness actually observed. Lowering this "
        "constant makes every deadline in this repository pass on paper "
        "without changing anything about when a card lands."
    )


def test_an_unknown_slot_raises_rather_than_defaulting():
    with pytest.raises(KeyError):
        slot_for("afternoon")


def test_the_uncardable_share_is_the_measured_one_and_named_rather_than_zero():
    """Some games a season cannot be carded, and the number is 37, not 3.

    **What this test used to measure, and why it was wrong twice.** It read
    `hours = .dt.hour` and asserted `(hours < 10.3).mean() < 0.001` — an
    integer-hour tip against a fractional bar, which asks "does this game tip
    before 11:00?" while the failure message said "before 10:18". It answered
    3 games, 0.05%, the figure `docs/card_cadence.md` and the workflow header
    both recorded. Two errors were cancelling. The truncation over-counted: the
    third of those three games is VCU–Virginia Tech at **10:30 ET** on
    2025-11-28, filed by the old record as "one at 10:00", and it tips *after*
    a 10:18 landing. And the missing card lead under-counted, by far more.

    **The bar is not the landing.** `gates.IMMINENT_MINUTES` **is**
    `CARD_LEAD_MINUTES`, so a run landing at 10:18 ET freezes nothing tipping
    at or before 11:18 ET — the tip guard calls those games `IMMINENT`,
    `_rows_to_freeze` drops them, and they never reach the append-only store.
    Measured on the same completed 2025-26 fixture, to the minute rather than
    the hour: **37 games, 0.59% of the slate, over 27 dates from 2025-11-03 to
    2026-03-14**, one to three on a date. Eighteen times the 0.05% that was
    written down, and 34 of the 37 are the 11:00 ET block itself — the block
    the morning slot exists to precede.

    **The 2026-27 season opener is still one of them**: Notre Dame v Villanova
    in Rome, 09:30 ET on 2026-11-01. It is a single game and it is the season's
    first, which is exactly the kind of thing that looks like a fault on the
    day and is not.

    It remains a coverage gap rather than a fault — it bites only when the
    primary was dropped as well, the tip guard quarantines these games
    correctly and the run reports the coverage it achieved. But the share is
    0.59%, and the record has to carry the real number. **The bound here was
    `< 0.001` and it is not loosened to accommodate the truth**; it is replaced
    by the measured value, which is stricter in both directions and goes red
    the day the schedule constants or the fixture move. If that happens, update
    `docs/card_cadence.md` and this number together rather than widening the
    tolerance — a guard that rounds off its own cost is how 0.05% stood for
    0.59% for a season.
    """
    frame = pd.read_parquet(schedule_fixture(2026), columns=["date"])
    assert len(frame) > 6_000
    tips = (
        pd.to_datetime(frame["date"], utc=True)
        .dt.tz_convert(ZoneInfo("America/New_York"))
    )
    # To the minute. The hour alone moves a 10:30 tip to 10:00, and a guard
    # cannot be more precise than the thing it counts.
    tip_hours = tips.dt.hour + tips.dt.minute / 60
    morning = slot_for("morning")
    landing = morning.backup_worst_case_landing_et()
    bar = morning.backup_worst_case_freeze_bar_et()
    assert bar == pytest.approx(landing + CARD_LEAD_H) and bar == pytest.approx(11.3)

    # `<=`, because `tip_state` quarantines `delta <= IMMINENT_MINUTES`: a game
    # tipping exactly on the bar is uncardable too. No game in this fixture sits
    # exactly on it — the two spellings agree here — and the strictness is
    # written the fail-closed way so it stays right the day one does.
    uncardable = float((tip_hours <= bar).mean())
    assert uncardable == pytest.approx(0.0059, abs=0.0002), (
        f"{uncardable:.2%} of the 2025-26 slate tips at or before the morning "
        f"backup's worst-case freeze bar of {bar:.2f} ET. The recorded figure is "
        "0.59% over 6,318 games. The schedule constants or the fixture have "
        "moved; update docs/card_cadence.md and this number together. Do not "
        "widen the tolerance."
    )

    # What the missing lead was worth, asserted rather than asserted-about: the
    # bare landing counts a twentieth of the real set.
    no_lead = float((tip_hours <= landing).mean())
    assert no_lead == pytest.approx(0.0003, abs=0.0002)
    assert uncardable > 10 * no_lead, (
        f"the lead-corrected uncardable share ({uncardable:.2%}) is no longer "
        f"much larger than the bare-landing one ({no_lead:.2%}). Either the crons "
        "moved or the card lead has been dropped from the bar; the second is the "
        "defect this test exists for."
    )


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


def test_every_declared_cron_is_a_trigger_of_a_slot_that_survives_the_lateness():
    """Each cron string is decomposed back to its hour and put through the same
    lateness arithmetic the rest of this file uses, so the pin above cannot be
    satisfied by a contract that declares a time no slot could survive."""
    hours_by_slot = {
        slot.name: sorted(slot.cron_hours_utc) for slot in SLOTS
    }
    declared = []
    for expression in cron_expressions():
        minute, hour, day_of_month, months, day_of_week = expression.split()
        assert (minute, day_of_month, day_of_week) == (str(CRON_MINUTE), "*", "*"), (
            f"{expression!r} is not the shape this schedule reasons about: "
            "every day of every declared month, on the hour."
        )
        assert months == SEASON_CRON_MONTHS, (
            f"{expression!r} runs in months {months}, not the season "
            f"{SEASON_CRON_MONTHS}."
        )
        declared.append(int(hour))

    assert sorted(declared) == sorted(
        hour for hours in hours_by_slot.values() for hour in hours
    )
    # The primary's bar, for the reason given in
    # `test_every_slot_can_freeze_its_block_from_its_primary_even_at_worst_lateness`:
    # the backup's bar is not met by the morning slot in any offset once the
    # card lead is applied, and those cells are named in
    # `CELLS_THAT_CANNOT_FREEZE_THEIR_BLOCK` rather than swept into a `holds()`
    # that was sixty minutes optimistic.
    for slot in SLOTS:
        assert slot.primary_holds(EST_OFFSET_H), (
            f"Slot {slot.name!r} declares crons at {slot.cron_hours_utc} UTC. "
            f"At the {OBSERVED_LATENESS_H}h worst lateness observed its primary "
            f"lands {slot.worst_case_landing_et(EST_OFFSET_H):.2f} ET and can "
            f"freeze nothing tipping before "
            f"{slot.worst_case_freeze_bar_et(EST_OFFSET_H):.2f} ET, which does "
            f"not reach the {slot.must_precede_et_hour}:00 ET block it exists to "
            "precede. Move the cron earlier — do not lower the lateness "
            "constant, and do not drop the lead."
        )
