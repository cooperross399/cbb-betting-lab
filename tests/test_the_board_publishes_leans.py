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


# --------------------------------------------------------------------------
# Decision 79: a lean reads the probability the card's edge bar reads.
# --------------------------------------------------------------------------


class _Table:
    active = True

    def __init__(self, weights: dict) -> None:
        self.weights = weights

    def weight(self, tier) -> float:
        return self.weights.get(tier, 0.0)


def _two_sided(model_home: str, home_odds: str = "+120", away_odds: str = "-140") -> list[dict]:
    """A spread both sides of which two books quote, the model loving the dog."""
    row = lambda sel, line, odds, book, p: {"market": "spreads", "selection": sel, "line": line, "american_odds": odds,
                                            "book": book, "model_probability": p, "edge": "0.30", "tier": "mid_major"}
    p_home = float(model_home)
    return [row("home", "7.5", home_odds, "a", model_home), row("away", "-7.5", away_odds, "a", f"{1 - p_home}"),
            row("home", "7.5", "-110", "b", model_home), row("away", "-7.5", "-110", "b", f"{1 - p_home}")]


def test_a_tier_the_card_no_longer_trusts_publishes_no_lean_on_the_models_word() -> None:
    builder = _builder()
    rows = _two_sided("0.70", home_odds="-105", away_odds="-115")
    assert builder.pick_from_frozen(rows, "DUKE", "UNC", [], ALLOW)["kind"] == "lean"
    trust = builder.LeanTrust(_Table({"mid_major": 0.0}))
    assert builder.pick_from_frozen(rows, "DUKE", "UNC", [], ALLOW, trust)["kind"] == "pass"


def test_a_trusted_tier_still_leans_and_shows_the_trusted_edge() -> None:
    builder = _builder()
    rows = _two_sided("0.70", home_odds="-105", away_odds="-115")
    pick = builder.pick_from_frozen(rows, "DUKE", "UNC", [], ALLOW, builder.LeanTrust(_Table({"mid_major": 1.0})))
    assert pick["kind"] == "lean" and pick["side"] == "home"
    half = builder.pick_from_frozen(rows, "DUKE", "UNC", [], ALLOW, builder.LeanTrust(_Table({"mid_major": 0.5})))
    assert half["trustedProb"] < pick["trustedProb"] and half["edgePct"] < pick["edgePct"]


def test_with_no_trust_table_a_lean_needs_a_book_beating_the_fair_price() -> None:
    builder = _builder()
    # Fair is the median of book a's and book b's own pairs; +120 at book a
    # beats it by more than the bar even with the model ignored.
    pick = builder.pick_from_frozen(_two_sided("0.70"), "DUKE", "UNC", [], ALLOW, builder.LeanTrust(None))
    assert pick["kind"] == "lean" and pick["price"] == 120


def test_a_one_sided_price_carries_no_trusted_lean() -> None:
    builder = _builder()
    assert builder.pick_from_frozen(_frozen("0.30"), "DUKE", "UNC", [], ALLOW, builder.LeanTrust(_Table({}))) ["kind"] == "pass"


def test_the_model_lean_reads_the_trust_too() -> None:
    builder = _builder()
    rows = _board_rows() + [{"market": "spreads", "selection": "away", "line": "4.5", "american_odds": "-110", "book": "b"}]
    untrusted = builder.pick_from_model(rows, _model(0.66, 0.42, 0.5), "DUKE", "UNC", -4.5, 140.5, ALLOW,
                                        builder.LeanTrust(_Table({"high_major": 0.0})), "high_major")
    assert untrusted is None or untrusted["kind"] == "pass"


def test_the_board_build_passes_the_trust_table_to_both_lean_paths() -> None:
    source = BUILDER.read_text(encoding="utf-8")
    assert "lean_trust = load_lean_trust(lab, day)" in source
    assert "lean_markets, lean_trust)" in source and "lean_markets, lean_trust, tier)" in source
