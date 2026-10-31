"""The April rule, held to the table `docs/when_this_ends.md` declared."""

from __future__ import annotations

import random
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from cbb_betting_lab.reports import decision_rule as DR

ROOT = Path(__file__).resolve().parents[1]


def _interval(low: float, high: float):
    return SimpleNamespace(adjusted_low=low, adjusted_high=high)


def test_the_outcome_is_the_declared_table():
    above = dict(opinions_n=DR.FLOOR_OPINIONS, games_n=DR.FLOOR_GAMES)
    assert DR.outcome(_interval(0.01, 0.05), opinions_n=DR.FLOOR_OPINIONS - 1,
                      games_n=DR.FLOOR_GAMES) == DR.DID_NOT_RUN
    assert DR.outcome(_interval(0.01, 0.05), opinions_n=DR.FLOOR_OPINIONS,
                      games_n=DR.FLOOR_GAMES - 1) == DR.DID_NOT_RUN
    assert DR.outcome(_interval(-0.02, 0.03), **above) == DR.STOP_NO_EDGE
    assert DR.outcome(_interval(-0.06, -0.01), **above) == DR.STOP_LOSER
    assert DR.outcome(_interval(0.01, 0.05), **above) == DR.CANDIDATE
    assert DR.outcome(_interval(0.01, 0.05), survived_roi=-0.01, **above) == DR.NOT_REACHABLE
    # Unlabelled survival leaves the clause unread, never failed or passed silently.
    assert DR.outcome(_interval(0.01, 0.05), survived_roi=None, **above) == DR.CANDIDATE


def test_the_floors_and_date_are_the_ones_the_document_declared():
    text = (ROOT / "docs" / "when_this_ends.md").read_text(encoding="utf-8")
    assert f"**Decision date: {DR.DECISION_DATE}.**" in text
    assert f"{DR.FLOOR_OPINIONS:,} settled opinions across at least {DR.FLOOR_GAMES:,} distinct games" in text


def test_an_empty_ledger_did_not_run_and_is_a_dry_run():
    record = DR.build_record(pd.DataFrame(), looks=152, as_of="2026-11-02")
    assert not record["final"]
    assert all(r["outcome"] == DR.DID_NOT_RUN for r in record["tiers"])
    assert record["pooled"]["outcome"] == DR.DID_NOT_RUN
    text = DR.render(record)
    assert "dry run" in text and "never the headline" in text


def _row(i: int, *, tier: str, won: bool, market="spread", player=""):
    day = f"2026-11-{1 + i % 28:02d}"
    return {"snapshot_date": day, "commence_time": f"{day}T23:00:00Z", "event_id": f"g{i // 2}",
            "home_team": "H", "away_team": "A", "market": market, "segment": "game",
            "player": player, "selection": "home", "line": -3.5, "american_odds": -110,
            "book": "b", "model_probability": 0.55, "edge": 0.05, "tier": tier,
            "outcome": "won" if won else "lost", "profit_units": 100 / 110 if won else -1.0}


def test_a_season_that_loses_is_read_as_a_loser_and_props_are_left_out():
    rng = random.Random(7)
    rows = [_row(i, tier="mid_major", won=rng.random() < 0.40) for i in range(12_000)]
    rows += [_row(i, tier="mid_major", won=True, market="player_points", player="P") for i in range(500)]
    record = DR.build_record(pd.DataFrame(rows), looks=152, as_of="2027-04-19")
    assert record["final"]
    mid = next(r for r in record["tiers"] if r["cut"] == "mid_major")
    assert mid["opinions"] == 12_000
    assert mid["outcome"] == DR.STOP_LOSER
    assert next(r for r in record["tiers"] if r["cut"] == "high_major")["outcome"] == DR.DID_NOT_RUN
