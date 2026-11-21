"""Decision 117: the card's spread bias against the market, taken out per tier."""

from __future__ import annotations

import json
from statistics import NormalDist

import pandas as pd
import pytest

from cbb_betting_lab.models import card_factors as CF
from cbb_betting_lab.models import spread_bias as SB


def _ledger(day: str, tier: str, disagreement: float, games: int) -> pd.DataFrame:
    p = NormalDist().cdf(disagreement / SB.SIGMA)
    rows = []
    for i in range(games):
        for book, line in (("a", -3.5), ("b", -4.0)):
            rows.append({
                "snapshot_date": day, "event_id": f"{day}-{tier}-{i}", "market": "spread",
                "segment": "game", "selection": "home", "line": line, "book": book,
                "model_probability": p, "tier": tier,
            })
        rows.append({
            "snapshot_date": day, "event_id": f"{day}-{tier}-{i}", "market": "spread",
            "segment": "game", "selection": "away", "line": 3.5, "book": "a",
            "model_probability": 1 - p, "tier": tier,
        })
    return pd.DataFrame(rows)


def test_a_tier_runs_two_points_away_and_the_shift_says_so():
    ledger = pd.concat([_ledger("2026-11-10", "high_major", -2.0, 25), _ledger("2026-11-10", "mid_major", 1.0, 5)])
    out = SB.estimate(ledger, day="2026-11-12")
    assert out["shifts"]["high_major"] == pytest.approx(-2.0, abs=1e-3)
    assert out["games"]["high_major"] == 25
    # Under the game floor, no shift.
    assert out["shifts"]["mid_major"] == 0.0


def test_only_days_before_the_window_end_are_read():
    ledger = pd.concat([_ledger("2026-11-12", "high_major", -3.0, 30), _ledger("2026-10-20", "high_major", 3.0, 30)])
    # The day itself and anything older than the window are not read.
    assert SB.estimate(ledger, day="2026-11-12")["shifts"]["high_major"] == 0.0
    assert SB.estimate(ledger, day="2026-11-13")["shifts"]["high_major"] == pytest.approx(-3.0, abs=1e-3)


def test_the_applied_shift_is_added_back_so_the_correction_does_not_undo_itself():
    # The card was corrected by -2 that day, so its frozen residual reads 0.
    ledger = _ledger("2026-11-10", "high_major", 0.0, 30)
    applied = {"2026-11-10": {"high_major": -2.0}}
    assert SB.estimate(ledger, day="2026-11-11", by_day=applied)["shifts"]["high_major"] == pytest.approx(-2.0, abs=1e-3)


def test_the_shift_is_clamped():
    ledger = _ledger("2026-11-10", "low_major", -9.0, 30)
    assert SB.estimate(ledger, day="2026-11-11")["shifts"]["low_major"] == -SB.CLAMP


def test_update_records_the_day_and_readers_never_look_ahead(tmp_path):
    ledger = _ledger("2026-11-10", "high_major", -2.0, 30)
    SB.update(SB.path(tmp_path), ledger, day="2026-11-11")
    payload = json.loads(SB.path(tmp_path).read_text())
    assert payload["by_day"]["2026-11-11"]["high_major"] == pytest.approx(-2.0, abs=1e-3)
    shifts, reason = SB.shifts_for(tmp_path, day="2026-11-12")
    assert shifts["high_major"] == pytest.approx(-2.0, abs=1e-3) and not reason
    shifts, reason = SB.shifts_for(tmp_path, day="2026-11-10")
    assert shifts == {} and reason
    shifts, reason = SB.shifts_for(tmp_path, day="2026-11-20")
    assert shifts == {} and "more than" in reason


def test_the_card_places_a_game_in_the_higher_tier():
    assert SB.higher_tier("low_major", "high_major") == "high_major"
    assert SB.higher_tier("unplaced", "mid_major") == "mid_major"
    assert SB.higher_tier(None, "") == "unplaced"


def test_it_is_a_declared_layer_on_by_default():
    assert "spread_bias" in dict(CF.CORRECTIONS) and "spread_bias" in CF.SWITCHABLE
    assert CF.default_switches()["spread_bias"] is True
