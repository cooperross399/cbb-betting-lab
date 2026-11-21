"""Decision 119: the site's spread call, its best number, and its strong flag."""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path

import pytest

WEB = Path(__file__).resolve().parents[1] / "web"


def _load(name: str, alias: str):
    spec = importlib.util.spec_from_file_location(alias, WEB / name)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


BOARD = _load("build_board_json.py", "board_ats_rule")
SETTLE = _load("settle_results.py", "settle_ats_rule")


@pytest.mark.parametrize("proj, current", [(-4.0, -3.5), (-8.0, -3.5), (1.0, -3.5), (-2.0, 2.5), (5.0, 2.5), (0.0, 0.0), (-3.0, -3.0)])
def test_the_ats_call_is_one_rule(proj, current):
    assert BOARD.ats_call_home(proj, current) == SETTLE.ats_call_home(proj, current)
    assert BOARD.DOG_TIEBREAK == SETTLE.DOG_TIEBREAK


def test_a_call_within_a_point_takes_the_underdog():
    # Home -3.5, projection -4.0: half a point of opinion, so the away dog.
    assert SETTLE.ats_call_home(-4.0, -3.5) is False
    # Home +2.5 underdog, projection +2.0: the home dog.
    assert SETTLE.ats_call_home(2.0, 2.5) is True
    # A real opinion stands: home -3.5, projection -8.
    assert SETTLE.ats_call_home(-8.0, -3.5) is True


def test_the_best_number_is_the_largest_handicap_and_its_best_price():
    rows = [
        {"market": "spread", "selection": "away", "line": 3.5, "american_odds": -110},
        {"market": "spread", "selection": "away", "line": 4.0, "american_odds": -115},
        {"market": "spread", "selection": "away", "line": 4.0, "american_odds": -112},
        {"market": "spread", "selection": "home", "line": -3.5, "american_odds": -108},
    ]
    assert BOARD.best_number(rows, "away") == {"line": 4.0, "price": -112}
    assert BOARD.best_number(rows, "home") == {"line": -3.5, "price": -108}
    assert BOARD.best_number([], "home") is None


def test_a_strong_spread_agrees_and_has_moved_or_shopped():
    # Call away at home -3.5; the outside projection has home by 1 (line -1): agrees.
    assert BOARD.strong_spread(False, -3.5, 1.0, -5.0, None) is True          # moved from -5 to -3.5, toward away
    assert BOARD.strong_spread(False, -3.5, 1.0, -2.0, None) is False         # moved against
    assert BOARD.strong_spread(False, -3.5, 1.0, None, {"line": 4.5}) is True  # a book a point better
    assert BOARD.strong_spread(False, -3.5, 1.0, None, {"line": 4.0}) is False
    # Disagrees: the projection has home by 6.
    assert BOARD.strong_spread(False, -3.5, 6.0, -5.0, {"line": 5.0}) is False
    assert BOARD.strong_spread(False, -3.5, None, -5.0, {"line": 5.0}) is False


def test_the_call_is_graded_at_the_best_number_and_both_tallies_are_kept(monkeypatch):
    board = {"teams": {}, "games": [
        # Home -3.5, projection -8: home call. Home wins by 3: loses at -3.5, wins at -2.5.
        {"id": "1", "home": {"abbr": "A"}, "away": {"abbr": "B"},
         "spread": {"current": -3.5, "proj": -8.0, "homePrice": -110, "strong": True,
                    "best": {"home": {"line": -2.5, "price": -120}, "away": {"line": 4.0, "price": -110}}}},
        # No best on an older board and no captures: graded at the consensus number.
        {"id": "2", "home": {"abbr": "C"}, "away": {"abbr": "D"},
         "spread": {"current": -3.5, "proj": -8.0, "homePrice": -110}},
    ]}
    monkeypatch.setattr(SETTLE, "finals", lambda sport, day: {"1": {"home": 70, "away": 67, "finish": "REG"},
                                                             "2": {"home": 70, "away": 67, "finish": "REG"}})
    monkeypatch.setattr(SETTLE, "CAPTURES", None)
    body, _ = SETTLE.settle_day("cbb", date(2026, 11, 21), board)
    s = body["summary"]
    assert (s["ats"]["w"], s["ats"]["l"]) == (1, 1)
    assert (s["atsMarket"]["w"], s["atsMarket"]["l"]) == (0, 2)
    assert (s["atsStrong"]["w"], s["atsStrong"]["l"]) == (1, 0)
    first = body["games"][0]["markets"]["spread"]["call"]
    assert first == {"side": "home", "line": -2.5, "price": -120, "strong": True, "result": "win"}


def test_the_capture_store_gives_the_best_number_before_the_board_froze():
    cap = _load("capture_prices.py", "capture_best_line").CapturePrices([
        {"market": "spread", "segment": "game", "home_team": "A", "away_team": "B", "selection": "away",
         "line": "3.5", "american_odds": "-110", "captured_at": "2026-11-21T15:00:00Z", "slate_date": "2026-11-21"},
        {"market": "spread", "segment": "game", "home_team": "A", "away_team": "B", "selection": "away",
         "line": "4.5", "american_odds": "-118", "captured_at": "2026-11-21T15:00:00Z", "slate_date": "2026-11-21"},
        {"market": "spread", "segment": "game", "home_team": "A", "away_team": "B", "selection": "away",
         "line": "6.5", "american_odds": "-110", "captured_at": "2026-11-21T20:00:00Z", "slate_date": "2026-11-21"},
    ])
    assert cap.best_line("2026-11-21", "B", "A", "2026-11-21T16:00:00Z") == (4.5, -118)
    assert cap.best_line("2026-11-21", "B", "A", "2026-11-21T14:00:00Z") is None
