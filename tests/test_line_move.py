"""The edge bar halves a lean the market has moved against (`models/line_move.py`)."""

from __future__ import annotations

import pandas as pd
import pytest

from cbb_betting_lab.models import line_move as LM
from cbb_betting_lab.reports.card_pricing import Quote, Wager


def _capture(at: str, *, home_odds=-110, away_odds=-110, home_line=-3.5, total=140.5):
    base = dict(captured_at=at, slate_date="2026-11-10", event_id="e1",
                commence_time="2026-11-10T23:00:00Z", home_team="H", away_team="A",
                segment="game", player="", book="b")
    return [
        {**base, "market": "moneyline", "selection": "home", "line": None, "american_odds": home_odds},
        {**base, "market": "moneyline", "selection": "away", "line": None, "american_odds": away_odds},
        {**base, "market": "spread", "selection": "home", "line": home_line, "american_odds": -110},
        {**base, "market": "spread", "selection": "away", "line": -home_line, "american_odds": -110},
        {**base, "market": "total_points", "selection": "over", "line": total, "american_odds": -110},
        {**base, "market": "total_points", "selection": "under", "line": total, "american_odds": -110},
    ]


def _wager(market: str, selection: str, line=None) -> Wager:
    return Wager(
        key=("e1", market, selection, line), event_id="e1", slate_date="2026-11-10",
        commence_time="2026-11-10T23:00:00Z", home_team="H", away_team="A", market=market,
        segment="game", player="", selection=selection, line=line, tier="mid_major",
        quotes=(Quote("b", -110),),
    )


def _moves(**later):
    rows = _capture("2026-11-10T10:00:00Z") + _capture("2026-11-10T15:00:00Z", **later)
    return LM.build(pd.DataFrame(rows), as_of="2026-11-10T16:00:00Z")


def test_the_move_is_signed_toward_each_side():
    moves = _moves(home_line=-5.5, total=143.5, home_odds=-150, away_odds=+130)
    assert moves.toward(_wager("spread", "home", -3.5)) == pytest.approx(2.0)
    assert moves.toward(_wager("spread", "away", 3.5)) == pytest.approx(-2.0)
    assert moves.toward(_wager("alternate_total_points", "over", 141.5)) == pytest.approx(3.0)
    assert moves.toward(_wager("total_points", "under", 140.5)) == pytest.approx(-3.0)
    assert moves.toward(_wager("moneyline", "home")) > LM.MIN_MOVE_PROB
    assert moves.toward(_wager("team_total", "over", 70.5)) is None


def test_a_capture_after_the_card_is_not_read():
    rows = _capture("2026-11-10T10:00:00Z") + _capture("2026-11-10T18:00:00Z", home_line=-9.5)
    moves = LM.build(pd.DataFrame(rows), as_of="2026-11-10T16:00:00Z")
    assert moves.by_event == {}
    assert "two captures" in moves.reason


def test_only_a_lean_the_market_moved_against_is_halved():
    moves = _moves(home_line=-5.5)
    home, away = _wager("spread", "home", -3.5), _wager("spread", "away", 3.5)
    market = {home.key: 0.5, away.key: 0.5}
    # The model leans away; the market moved two points toward home.
    out = LM.apply({home.key: 0.4, away.key: 0.6}, market, [home, away], moves)
    assert out.probabilities[away.key] == pytest.approx(0.5 + LM.FIGHT_SHRINK * 0.1)
    assert out.probabilities[home.key] == pytest.approx(0.4), "a side with no lean is untouched"
    assert out.restrained == [away]
    # Leaning with the move changes nothing.
    out = LM.apply({home.key: 0.6, away.key: 0.4}, market, [home, away], moves)
    assert out.probabilities[home.key] == pytest.approx(0.6) and not out.restrained


def test_a_small_move_and_an_absent_table_change_nothing():
    moves = _moves(home_line=-4.0)
    home = _wager("spread", "home", -3.5)
    away = _wager("spread", "away", 3.5)
    trusted = {home.key: 0.4, away.key: 0.6}
    assert LM.apply(trusted, {home.key: 0.5, away.key: 0.5}, [home, away], moves).probabilities == trusted
    assert LM.apply(trusted, {}, [home, away], None).probabilities == trusted
    empty = LM.apply(trusted, {}, [home, away], LM.build(None, as_of="2026-11-10"))
    assert empty.probabilities == trusted and "not read" in empty.line
