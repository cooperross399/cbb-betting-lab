"""The card's When column (`models/timing.py`, decision 89)."""

from __future__ import annotations

from cbb_betting_lab.models import line_move, timing


def _moves(opened: float, now: float, market: str = "spread") -> line_move.Moves:
    moves = line_move.Moves(as_of="2026-11-08T16:00:00Z")
    moves.by_event = {"ev1": {market: (opened, now)}}
    return moves


def _row(selection: str, market: str = "spread") -> dict:
    return {"event_id": "ev1", "market": market, "selection": selection, "segment": "game"}


def test_a_price_the_market_is_taking_away_reads_now():
    # Home line -3 -> -5: the market moved to home by two points.
    moves = _moves(-3.0, -5.0)
    assert timing.advise(_row("home"), moves) == timing.NOW
    assert timing.advise(_row("away"), moves) == timing.NEAR_TIP


def test_a_small_move_or_no_capture_reads_near_tip():
    assert timing.advise(_row("home"), _moves(-3.0, -3.5)) == timing.NEAR_TIP
    assert timing.advise(_row("home"), None) == timing.NEAR_TIP
    assert timing.advise({"event_id": "other", "market": "spread", "selection": "home"}, _moves(-3.0, -6.0)) == timing.NEAR_TIP


def test_alternate_ladders_and_totals_take_their_main_markets_move():
    moves = _moves(140.0, 142.0, market="total_points")
    assert timing.advise(_row("over", "alternate_total_points"), moves) == timing.NOW
    assert timing.advise(_row("under", "total_points"), moves) == timing.NEAR_TIP


def test_a_player_prop_or_a_half_is_never_told_now():
    moves = _moves(-3.0, -6.0)
    assert timing.advise({**_row("home"), "segment": "h1"}, moves) == timing.NEAR_TIP
    assert timing.advise({**_row("home"), "player": "Someone"}, moves) == timing.NEAR_TIP
