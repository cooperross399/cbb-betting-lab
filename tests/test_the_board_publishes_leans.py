"""The board publishes leans the way the NHL and EPL boards do (decision 74).

A lean is the model's own opinion clearing the card's edge bar before the
trust table pulls it toward the market. It is graded into its own record,
stakes nothing, is shown only on an allowlisted main market inside the card's
price band, and is never a bet.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from cbb_betting_lab.reports import card_pricing

BUILDER = Path(__file__).resolve().parents[1] / "web" / "build_board_json.py"
ALLOW = {"moneyline", "spread", "total_points"}


def _builder():
    spec = importlib.util.spec_from_file_location("build_board_json_leans", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _frozen(edge: str, odds: str = "-110", market: str = "spreads") -> list[dict]:
    return [{"market": market, "selection": "home", "line": "-3.5", "american_odds": odds, "book": "b",
             "model_probability": "0.56", "edge": edge}]


def test_the_lean_bar_is_the_cards_own_bar_and_band() -> None:
    builder = _builder()
    assert builder.LEAN_EDGE == card_pricing.EDGE_THRESHOLD
    assert tuple(builder.LEAN_PRICE_BAND) == tuple(card_pricing.PRICE_BAND)


def test_a_frozen_opinion_over_the_bar_on_an_allowlisted_market_is_a_lean() -> None:
    pick = _builder().pick_from_frozen(_frozen("0.04"), "DUKE", "UNC", [], ALLOW)
    assert pick["kind"] == "lean" and pick["units"] is None and pick["edgePct"] == 4.0


def test_no_lean_without_an_allowlist_below_the_bar_or_outside_the_band() -> None:
    builder = _builder()
    assert builder.pick_from_frozen(_frozen("0.04"), "DUKE", "UNC", [], set())["kind"] == "pass"
    assert builder.pick_from_frozen(_frozen("0.01"), "DUKE", "UNC", [], ALLOW)["kind"] == "pass"
    assert builder.pick_from_frozen(_frozen("0.30", "-900"), "DUKE", "UNC", [], ALLOW)["kind"] == "pass"


def test_a_card_selection_is_still_a_bet_and_never_a_lean() -> None:
    rows = _frozen("0.04")
    assert _builder().pick_from_frozen(rows, "DUKE", "UNC", rows, ALLOW)["kind"] == "bet"


def _model(home_win: float, cover: float, over: float) -> dict:
    return {"home_win": home_win,
            "margin_triple": lambda line: (cover, 0.0, 1 - cover),
            "total_triple": lambda line: (over, 0.0, 1 - over)}


def _board_rows() -> list[dict]:
    q = lambda m, s, line, odds, book="b": {"market": m, "selection": s, "line": line, "american_odds": odds, "book": book}
    return [q("h2h", "home", "", "-200"), q("h2h", "away", "", "+170"),
            q("spreads", "home", "-4.5", "-110"), q("spreads", "away", "4.5", "-105", "best"),
            q("totals", "over", "140.5", "-110"), q("totals", "under", "140.5", "-110")]


def test_the_model_lean_is_its_best_side_against_the_best_price() -> None:
    builder = _builder()
    pick = builder.pick_from_model(_board_rows(), _model(0.66, 0.42, 0.5), "DUKE", "UNC", -4.5, 140.5, ALLOW)
    # Away +4.5 at -105 covers 58%: 0.58 * 100/105 - 0.42 = +13.2%.
    assert pick["kind"] == "lean" and pick["basis"] == "model"
    assert (pick["market"], pick["side"], pick["line"], pick["price"], pick["book"]) == ("Spread", "away", 4.5, -105, "best")
    assert pick["edgePct"] == 13.2 and pick["units"] is None


def test_a_model_opinion_under_the_bar_is_a_pass() -> None:
    pick = _builder().pick_from_model(_board_rows(), _model(0.66, 0.5, 0.5), "DUKE", "UNC", -4.5, 140.5, ALLOW)
    assert pick["kind"] == "pass"


def test_the_freeze_wins_over_the_model_when_it_holds_an_opinion() -> None:
    builder = _builder()
    assert builder.frozen_has_opinion(_frozen("0.01"))
    assert not builder.frozen_has_opinion([{**_frozen("0.01")[0], "edge": ""}])
    source = BUILDER.read_text(encoding="utf-8")
    assert 'not row["started"]' in source and "not frozen_has_opinion(my_frozen)" in source
