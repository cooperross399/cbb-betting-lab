"""Every slot must land before its games, at the worst lateness ever observed.

GitHub has been firing Cooper's crons 4.5-5.3 hours late since 2026-08-27, so a
schedule checked against its nominal time is a schedule checked against a
fiction. This test recomputes the whole table from `OBSERVED_LATENESS_H`, which
means raising that constant when GitHub gets worse is a one-line change that
proves itself rather than a note somebody has to act on.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from conftest import schedule_fixture
from zoneinfo import ZoneInfo

from cbb_betting_lab.config import RAW_DIR
from cbb_betting_lab.schedule_contract import (
    CRON_MINUTE,
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
    landing_et,
    slot_for,
)

#: The same cron instant — 10:00 UTC, the morning backup — on the last day of
#: EST and the first day of EDT. DST begins 2027-03-14 at 02:00 EST (07:00
#: UTC), so 10:00 UTC on the 14th is already an EDT instant.
LAST_EST_MORNING = datetime(2027, 3, 13, 10, 0, tzinfo=timezone.utc)
FIRST_EDT_MORNING = datetime(2027, 3, 14, 10, 0, tzinfo=timezone.utc)


def test_every_slot_lands_before_its_block_even_at_worst_lateness():
    for slot in SLOTS:
        assert slot.holds(), (
            f"Slot {slot.name!r} fires nominally at {slot.cron_hours_utc} UTC. "
            f"At the observed {OBSERVED_LATENESS_H}h lateness its backup lands "
            f"at {slot.backup_worst_case_landing_et():.1f}:00 ET, which is not "
            f"before the {slot.must_precede_et_hour}:00 ET block it exists to "
            "cover. Move the cron earlier — do not lower the lateness constant."
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


def test_the_dst_gap_is_the_one_written_down():
    """Under EDT at the worst observed lateness the morning BACKUP lands
    11:18 ET, after its 11:00 ET block; the morning primary and both evening
    triggers still hold. The crons were not moved for it, and this pins the
    gap as recorded in `docs/card_cadence.md` and the workflow header. If the
    crons move or the lateness constant changes, the record changes with them
    — do not delete this to make the build green."""
    assert MORNING.holds(EST_OFFSET_H) and EVENING.holds(EST_OFFSET_H)
    assert EVENING.holds(EDT_OFFSET_H), (
        f"the evening slot's backup lands {EVENING.backup_worst_case_landing_et(EDT_OFFSET_H):.2f} ET under "
        f"EDT, at or after its {EVENING.must_precede_et_hour}:00 ET block; that is a new gap, not the recorded one"
    )
    primary = MORNING.worst_case_landing_et(EDT_OFFSET_H)
    assert primary < MORNING.must_precede_et_hour, (
        f"the morning PRIMARY lands {primary:.2f} ET under EDT, at or after the first tip; that is a new gap"
    )
    backup = MORNING.backup_worst_case_landing_et(EDT_OFFSET_H)
    assert backup == pytest.approx(max(MORNING.cron_hours_utc) + OBSERVED_LATENESS_H + EDT_OFFSET_H)
    assert backup == pytest.approx(11.3) and not MORNING.holds(EDT_OFFSET_H), (
        f"the recorded gap is the morning backup landing 11:18 ET under EDT; it now lands {backup:.2f} ET. "
        "Update docs/card_cadence.md, the workflow header and this test together."
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


def test_the_uncardable_share_is_tiny_and_named_rather_than_zero():
    """A handful of games a season cannot be carded, and that is stated.

    The morning slot's backup lands at 10:18 ET at worst-case lateness. Three
    games in the whole 2025-26 season tip before that — one at 01:00 ET
    (Hawai'i), one at 08:00 and one at 10:00 — which is **0.05% of the slate**.

    **The 2026-27 season opener is one of them**: Notre Dame v Villanova in
    Rome, 09:30 ET on 2026-11-01. It is a single game and it is the season's
    first, which is exactly the kind of thing that looks like a fault on the
    day and is not.

    Moving the cron earlier to catch it would card the whole day earlier, with
    less information, to buy three games — the football lab reached the same
    conclusion about its six international kickoffs and recorded it rather than
    chasing it. The tip guard quarantines these games correctly and the run
    reports the coverage it achieved. **It is a coverage gap, not a fault.**
    """
    frame = pd.read_parquet(schedule_fixture(2026), columns=["date"])
    assert len(frame) > 6_000
    hours = (
        pd.to_datetime(frame["date"], utc=True)
        .dt.tz_convert(ZoneInfo("America/New_York"))
        .dt.hour
    )
    morning = slot_for("morning")
    landing = morning.backup_worst_case_landing_et()
    uncardable = float((hours < landing).mean())
    assert uncardable < 0.001, (
        f"{uncardable:.2%} of games tip before the morning slot's worst-case "
        f"landing of {landing:.1f}:00 ET. That is no longer a handful, and the "
        "schedule needs revisiting rather than a wider tolerance here."
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
    for slot in SLOTS:
        assert slot.holds(EST_OFFSET_H), (
            f"Slot {slot.name!r} declares crons at {slot.cron_hours_utc} UTC. "
            f"At the {OBSERVED_LATENESS_H}h worst lateness observed its backup "
            f"lands {slot.backup_worst_case_landing_et(EST_OFFSET_H):.2f}:00 "
            f"ET, at or after the {slot.must_precede_et_hour}:00 ET block it "
            "exists to precede. Move the cron earlier — do not lower the "
            "lateness constant."
        )
