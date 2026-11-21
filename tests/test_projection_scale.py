"""Decision 109: KenPom's weight, the margin stretch, the home-bonus fade, and
the layer audit reading the betting-line store it fits `market_ratings` from."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest
import yaml

from cbb_betting_lab.models import card_factors as CF

REPO = Path(__file__).resolve().parents[1]
FIXTURES = REPO / "tests" / "fixtures" / "real_data"
DAY = "2026-03-12"


def test_kenpom_carries_the_weight_the_audit_measured():
    # The 2026-11-19 audit: best at 0.77 times a 0.85 blend, so 0.65 (decision 112).
    assert CF.KENPOM_BLEND_WEIGHT == pytest.approx(0.65)
    assert CF.KENPOM_BLEND_WEIGHT == pytest.approx(0.85 * 0.77, abs=0.01)


def test_the_second_opinion_carries_the_weight_the_audit_measured():
    # 2026-11-19: best at 1.96 times a 0.5 blend (0.98), so 0.9 (decision 112).
    # 2026-11-20: best at 1.10 times a 0.9 blend (0.99), so 1.0 (decision 116).
    assert CF.BLEND_WEIGHT == pytest.approx(1.0)
    assert CF.BLEND_WEIGHT == pytest.approx(0.9 * 1.10, abs=0.02)


def test_the_margin_stretch_is_a_candidate_and_off_on_the_declared_card():
    assert "margin_stretch" in dict(CF.CANDIDATE_LAYERS)
    assert CF.default_switches()["margin_stretch"] is False
    # Applied last, so it stretches the margin every other layer left.
    assert CF.CANDIDATE_LAYERS[-1][0] == "margin_stretch"
    assert CF.MARGIN_STRETCH > 1.0


def test_the_home_bonus_is_spent_in_three_weeks():
    assert CF.EARLY_HOME_BONUS_DAYS == 21
    assert CF.early_home_bonus(0) == pytest.approx(CF.EARLY_HOME_BONUS_POINTS)
    assert CF.early_home_bonus(21) == 0.0
    assert CF.early_home_bonus(30) == 0.0


def test_the_layer_audit_runs_after_the_line_movement_store_is_read():
    workflow = yaml.safe_load((REPO / ".github" / "workflows" / "cbb-gameday-refresh.yml").read_text())
    for job in workflow["jobs"].values():
        ids = [step.get("id") for step in job.get("steps", [])]
        if "layer_audit" in ids:
            assert "line_moves" in ids, "the job that audits must also read the store"
            assert ids.index("line_moves") < ids.index("layer_audit"), (
                "the audit ran before the line-movement store existed, so it measured "
                "`market_ratings` as moving no game at all (decision 109)"
            )
            return
    pytest.fail("no job runs the layer audit")


def test_switched_on_the_stretch_multiplies_the_margin_and_holds_the_total(tmp_path):
    from cbb_betting_lab.models import ratings
    from cbb_betting_lab.reports import price_backtest as PB

    raw = tmp_path / "data" / "raw"
    schedules = raw / "cbb" / "schedules"
    schedules.mkdir(parents=True)
    for season in (2025, 2026, 2027):
        (schedules / f"mbb_schedule_{season}.parquet").write_bytes(
            (FIXTURES / f"mbb_schedule_{season}.parquet").read_bytes())
    schedule = pd.read_parquet(FIXTURES / "mbb_schedule_2026.parquet")
    games = schedule[schedule["game_date"].astype(str) == DAY]
    audit = CF.layer_audit_path(raw)
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(json.dumps({"as_of": DAY, "switches": {"margin_stretch": True}}), encoding="utf-8")

    team_games = pd.read_csv(FIXTURES / "cbb_team_games.csv", low_memory=False)
    prices = pd.DataFrame([{"event_id": f"e{g.id}", "game_id": int(g.id)} for g in games.itertuples()])
    out = ratings.matchups_for(day=DAY, history=PB.history_before(team_games, DAY), prices=prices,
                               raw_dir=raw, player_games=None)
    priced = [m for m in out.values() if m.priceable]
    assert priced
    for game in priced:
        keys = [layer["key"] for layer in game.layers]
        assert keys[-1] == "margin_stretch"
        after, before = game.layers[-1], game.layers[-2]
        assert after["possessions"] == pytest.approx(before["possessions"])
        assert after["home"] - after["away"] == pytest.approx(
            CF.MARGIN_STRETCH * (before["home"] - before["away"]))
        assert after["home"] + after["away"] == pytest.approx(before["home"] + before["away"])
