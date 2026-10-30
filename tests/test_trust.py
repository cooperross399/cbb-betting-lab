"""The trust table: how far the edge bar believes the model against the price."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from cbb_betting_lab.models import trust
from cbb_betting_lab.reports.card_pricing import Quote, Wager


def _wager(selection: str, quotes: dict[str, float], *, line=-3.5, tier="mid_major", market="spread") -> Wager:
    return Wager(
        key=("e1", market, selection, line),
        event_id="e1", slate_date="2026-11-10", commence_time="2026-11-10T23:00:00Z",
        home_team="Home", away_team="Away", market=market, segment="full_game",
        player="", selection=selection, line=line if selection == "home" else (None if line is None else -line),
        tier=tier, quotes=tuple(Quote(b, o) for b, o in quotes.items()),
    )


def _seed(tmp_path, estimates: dict[str, float]):
    by_tier = [
        {"label": tier, "rows": 1000, "fit": {"fitted": True, "coefficients": [
            {"name": "disagreement", "estimate": w, "enough_evidence": True}]}}
        for tier, w in estimates.items()
    ]
    (tmp_path / trust.SEED_RECORD).write_text(json.dumps({"by_tier": by_tier}), encoding="utf-8")


def test_the_seed_is_read_per_tier_and_clamped(tmp_path):
    _seed(tmp_path, {"high_major": 0.05, "mid_major": -0.2, "low_major": 1.7})
    seeds = trust.seed_from_record(tmp_path / trust.SEED_RECORD)
    assert seeds == {"high_major": (0.05, 1000), "mid_major": (0.0, 1000), "low_major": (1.0, 1000)}


def test_nothing_is_applied_before_the_seed_is_known(tmp_path):
    _seed(tmp_path, {"mid_major": 0.5})
    table = trust.build("2026-10-31", outputs_dir=tmp_path, ledger=None)
    assert not table.active
    home, away = _wager("home", {"a": -110}), _wager("away", {"a": -110})
    probabilities = {home.key: 0.7, away.key: 0.3}
    assert trust.apply(probabilities, [home, away], table) == probabilities


def test_an_absent_table_changes_nothing():
    home = _wager("home", {"a": -110})
    assert trust.apply({home.key: 0.7}, [home], None) == {home.key: 0.7}


def test_the_market_is_each_books_own_pair_devigged_and_the_median_taken():
    home = _wager("home", {"a": -110, "b": -120, "solo": +500})
    away = _wager("away", {"a": -110, "b": +100})
    market = trust.market_probabilities([home, away])
    pa = 0.5
    rb = (120 / 220) / (120 / 220 + 0.5)
    assert market[home.key] == pytest.approx((pa + rb) / 2)
    assert market[away.key] == pytest.approx(1 - market[home.key])


def test_the_probability_is_pulled_toward_the_market_by_the_tier_weight(tmp_path):
    _seed(tmp_path, {"mid_major": 0.25})
    table = trust.build("2026-11-10", outputs_dir=tmp_path, ledger=None)
    home, away = _wager("home", {"a": -110}), _wager("away", {"a": -110})
    out = trust.apply({home.key: 0.70, away.key: 0.30}, [home, away], table)
    assert out[home.key] == pytest.approx(0.5 + 0.25 * 0.2)
    assert out[away.key] == pytest.approx(0.5 - 0.25 * 0.2)


def test_a_one_sided_wager_carries_no_trusted_opinion(tmp_path):
    _seed(tmp_path, {"mid_major": 0.25})
    table = trust.build("2026-11-10", outputs_dir=tmp_path, ledger=None)
    home = _wager("home", {"a": -110})
    assert trust.apply({home.key: 0.7}, [home], table) == {}


def test_an_unseeded_tier_trusts_the_market(tmp_path):
    _seed(tmp_path, {"mid_major": 0.25})
    table = trust.build("2026-11-10", outputs_dir=tmp_path, ledger=None)
    home = _wager("home", {"a": -110}, tier="unplaced")
    away = _wager("away", {"a": -110}, tier="unplaced")
    out = trust.apply({home.key: 0.9, away.key: 0.1}, [home, away], table)
    assert out[home.key] == pytest.approx(0.5)


def _ledger(rows):
    columns = ["snapshot_date", "event_id", "market", "segment", "player", "selection",
               "line", "american_odds", "book", "model_probability", "tier", "outcome"]
    return pd.DataFrame(rows, columns=columns)


def test_the_ledger_moves_the_weight_and_only_rows_before_the_day_count(tmp_path):
    _seed(tmp_path, {"mid_major": 0.0})
    rows = []
    # The model leans home at 0.7 against an even price and home always wins:
    # its disagreement is realised, so the weight rises from the seed.
    for i in range(400):
        event = f"g{i}"
        rows.append(["2026-11-05", event, "spread", "full_game", "", "home", -3.5, -110, "a", 0.7, "mid_major", "won"])
        rows.append(["2026-11-05", event, "spread", "full_game", "", "away", 3.5, -110, "a", 0.3, "mid_major", "lost"])
    later = [["2026-11-20", "z", "spread", "full_game", "", "home", -3.5, -110, "a", 0.7, "mid_major", "lost"]]
    table = trust.build("2026-11-10", outputs_dir=tmp_path, ledger=_ledger(rows + later))
    tier = table.by_tier["mid_major"]
    assert tier.ledger_rows == 800
    assert 0.0 < tier.weight <= 1.0
    assert table.weight("mid_major") == tier.weight
    # The same ledger read on a day before any of it settled is the seed.
    early = trust.build("2026-11-05", outputs_dir=tmp_path, ledger=_ledger(rows))
    assert early.by_tier["mid_major"].weight == 0.0


def test_the_card_line_says_what_was_applied(tmp_path):
    _seed(tmp_path, {"high_major": 0.05})
    line = trust.build("2026-11-10", outputs_dir=tmp_path, ledger=None).line()
    assert "high-major 0.050" in line and "market + trust x (model - market)" in line
    assert "not applied" in trust.build("2026-10-01", outputs_dir=tmp_path, ledger=None).line()
