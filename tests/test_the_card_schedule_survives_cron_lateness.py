"""Every slot must land before its games, at the worst lateness ever observed.

GitHub has been firing Cooper's crons 4.5-5.3 hours late since 2026-08-27, so a
schedule checked against its nominal time is a schedule checked against a
fiction. This test recomputes the whole table from `OBSERVED_LATENESS_H`, which
means raising that constant when GitHub gets worse is a one-line change that
proves itself rather than a note somebody has to act on.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from conftest import schedule_fixture
from zoneinfo import ZoneInfo

from cbb_betting_lab.config import RAW_DIR
from cbb_betting_lab.schedule_contract import (
    OBSERVED_LATENESS_H,
    SLOTS,
    CardSlot,
    slot_for,
)


def test_every_slot_lands_before_its_block_even_at_worst_lateness():
    for slot in SLOTS:
        assert slot.holds(), (
            f"Slot {slot.name!r} fires nominally at {slot.cron_hours_utc} UTC. "
            f"At the observed {OBSERVED_LATENESS_H}h lateness its backup lands "
            f"at {slot.backup_worst_case_landing_et():.1f}:00 ET, which is not "
            f"before the {slot.must_precede_et_hour}:00 ET block it exists to "
            "cover. Move the cron earlier — do not lower the lateness constant."
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
