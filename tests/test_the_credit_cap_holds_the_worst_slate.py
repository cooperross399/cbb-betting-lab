"""The cap must be able to hold the largest night this sport produces.

The NHL lab capped a purchase at 200,000 and spent **289,984**, because it
estimated from the markets it *asked* for while the provider bills per market
*returned* and every alternate ladder bills on its own. Its code and its test
both asserted the cap "cannot be breached".

Two separate guards came out of that, and this file is the first:

1. The **cap** must exceed the pessimistic bound for the worst slate, so a real
   night can never be truncated. A truncated night freezes the early tips and
   drops the late ones — the West Coast, low-major end of the board this lab
   exists to look at — and forward evidence cannot be re-made.
2. The **spend** is enforced against the measured running total, not the
   estimate. That is `tests/test_retention_probe.py` —
   `test_the_cap_refuses_a_request_that_would_breach_it` and
   `test_the_measured_total_and_not_the_estimate_is_what_was_reported` (this
   docstring used to name a `test_the_spend_guard_uses_the_measured_total.py`
   that never existed).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbb_betting_lab import markets as M
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import OUTPUTS_DIR
from cbb_betting_lab.providers.odds_api import DEFAULT_REGIONS

REGIONS = len([r for r in DEFAULT_REGIONS.split(",") if r.strip()])

#: The largest single-day slate across every cached season, measured by
#: `scripts/estimate_credit_cost.py`. Opening Monday of 2022-23.
WORST_SLATE_GAMES = 200


def test_one_snapshot_of_the_worst_slate_fits_inside_the_cap():
    per_event = len(M.per_event_provider_keys()) * REGIONS
    bulk = len(M.bulk_provider_keys()) * REGIONS
    worst = bulk + WORST_SLATE_GAMES * per_event
    assert CBB.daily_credit_cap >= worst, (
        f"The cap is {CBB.daily_credit_cap:,} and the worst slate bounds at "
        f"{worst:,} ({WORST_SLATE_GAMES} games x {per_event} credits). A cap "
        "below the worst slate starves it, and a starved fetch and an unquoted "
        "market look identical in the reports. Either raise the cap or move "
        "markets out of the per-event list — do not leave this red."
    )


def test_the_regions_are_the_ones_cooper_can_actually_open():
    """A price at a book he cannot open is not reachable."""
    assert DEFAULT_REGIONS == "us,us2"


def test_the_generated_arithmetic_agrees_with_the_registry():
    """CI regenerates the cost file; this checks the two have not drifted."""
    path = Path(OUTPUTS_DIR) / CBB.output_name("credit_cost", ".json")
    assert path.is_file(), f"{path.name} is tracked under data/outputs; its absence is a broken checkout, not a pass"
    record = json.loads(path.read_text(encoding="utf-8"))
    assert record["per_event_cost_pessimistic"] == (
        len(M.per_event_provider_keys()) * REGIONS
    )
    assert record["peak_games_in_a_day"] <= WORST_SLATE_GAMES, (
        "A season with a larger peak slate has been cached. Re-derive the cap "
        "and update WORST_SLATE_GAMES."
    )
