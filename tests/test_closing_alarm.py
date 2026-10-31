"""The early alarm: the model's settled leans against the closing line."""

from __future__ import annotations

import pandas as pd
import pytest

from cbb_betting_lab.reports import closing_alarm as CA


def _store(event: str, *, home_line: float, total: float, at: str, tip: str = "2026-11-10T23:00:00Z"):
    base = dict(captured_at=at, slate_date="2026-11-10", event_id=event, commence_time=tip,
                home_team="H", away_team="A", segment="game", player="", book="b")
    return [
        {**base, "market": "spread", "selection": "home", "line": home_line, "american_odds": -110},
        {**base, "market": "spread", "selection": "away", "line": -home_line, "american_odds": -110},
        {**base, "market": "total_points", "selection": "over", "line": total, "american_odds": -110},
        {**base, "market": "total_points", "selection": "under", "line": total, "american_odds": -110},
        {**base, "market": "moneyline", "selection": "home", "line": None, "american_odds": -150},
        {**base, "market": "moneyline", "selection": "away", "line": None, "american_odds": +130},
    ]


def _lean(event: str, market: str, selection: str, line, *, edge=0.05, odds=-110, tier="mid_major"):
    return {"snapshot_date": "2026-11-10", "commence_time": "2026-11-10T23:00:00Z",
            "event_id": event, "home_team": "H", "away_team": "A", "market": market,
            "segment": "game", "player": "", "selection": selection, "line": line,
            "american_odds": odds, "book": "b", "model_probability": 0.55, "edge": edge,
            "tier": tier, "outcome": "won"}


def test_closing_value_is_from_the_bettors_side():
    close = {("e", "spread"): -5.5, ("e", "total_points"): 143.5, ("e", "moneyline"): 0.6}
    assert CA.closing_value(_lean("e", "spread", "home", -3.5), close) == pytest.approx(2.0)
    assert CA.closing_value(_lean("e", "spread", "away", 3.5), close) == pytest.approx(-2.0)
    assert CA.closing_value(_lean("e", "total_points", "over", 141.5), close) == pytest.approx(2.0)
    assert CA.closing_value(_lean("e", "total_points", "under", 141.5), close) == pytest.approx(-2.0)
    # The vig counts against a moneyline lean: an even price implies 52.4%.
    assert CA.closing_value(_lean("e", "moneyline", "home", None), close) == pytest.approx(0.6 - 110 / 210)
    assert CA.closing_value(_lean("x", "spread", "home", -3.5), close) is None


def test_the_close_is_the_last_capture_before_tip():
    rows = (_store("e", home_line=-3.5, total=140.5, at="2026-11-10T14:00:00Z")
            + _store("e", home_line=-5.5, total=141.5, at="2026-11-10T22:00:00Z")
            + _store("e", home_line=-9.5, total=150.5, at="2026-11-11T03:00:00Z"))
    close = CA.closing_consensus(pd.DataFrame(rows))
    assert close[("e", "spread")] == pytest.approx(-5.5)
    assert close[("e", "total_points")] == pytest.approx(141.5)


def test_only_settled_full_game_team_leans_above_the_bar_count():
    rows = [
        _lean("e", "spread", "home", -3.5),
        _lean("e", "spread", "away", 3.5, edge=0.01),
        {**_lean("e", "total_points", "over", 140.5), "outcome": ""},
        {**_lean("e", "spread", "home", -3.5), "segment": "h1"},
        {**_lean("e", "spread", "home", -3.5), "player": "Someone"},
        _lean("e", "alternate_spread", "home", -7.5),
    ]
    assert len(CA.leans(pd.DataFrame(rows))) == 1


def test_the_alarm_trips_only_with_enough_leans_all_losing_to_the_close():
    store, ledger = [], []
    for game in range(40):
        event = f"g{game}"
        store += _store(event, home_line=-3.5, total=140.5, at="2026-11-10T14:00:00Z")
        store += _store(event, home_line=-1.5 - (game % 3) * 0.5, total=140.5, at="2026-11-10T22:00:00Z")
        for _ in range(3):
            ledger.append(_lean(event, "spread", "home", -3.5))
    record = CA.build_record(pd.DataFrame(ledger), pd.DataFrame(store), looks=150, as_of="2026-12-01")
    cell = next(c for c in record["cells"] if c["tier"] == "mid_major" and c["market"] == "spread")
    assert cell["graded"] == 120 and cell["games"] == 40
    assert cell["mean"] < 0 and cell["high"] < 0
    assert cell["alarm"] and record["alarms"] == ["mid_major / spread"]
    assert "candidate for withdrawal" in CA.render(record)
    # The same leans over too few games say nothing.
    few = CA.build_record(pd.DataFrame(ledger[:30]), pd.DataFrame(store), looks=150, as_of="2026-12-01")
    assert few["alarms"] == []


def test_an_empty_ledger_says_it_is_empty():
    record = CA.build_record(pd.DataFrame(), pd.DataFrame(), looks=150, as_of="2026-11-01")
    assert record["leans"] == 0 and not record["alarms"]
    assert "silent because it is empty" in CA.render(record)
