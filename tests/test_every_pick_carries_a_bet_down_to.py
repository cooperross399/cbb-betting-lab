"""Every pick carries a "bet down to" number (Cooper, 2026-11-01).

The number is the worst whole American price at which the pick still clears
the card's edge bar, on the probability the bar read. It restates a bar that
has already been read and decides nothing, so these tests pin three things:
the price it prints really clears, one cent worse does not, and the card, the
board and the tracker all carry it.
"""

from __future__ import annotations

import importlib.util
import random
from pathlib import Path

from cbb_betting_lab.forward_evidence import expected_value
from cbb_betting_lab.reports import card_pricing
from cbb_betting_lab.reports.card_pricing import (
    EDGE_THRESHOLD,
    PRICE_BAND,
    bet_down_to,
    bet_down_to_from_edge,
)

WEB = Path(__file__).resolve().parents[1] / "web"
ALLOW = {"moneyline", "spread", "total_points"}


def _builder():
    spec = importlib.util.spec_from_file_location("build_board_json_down_to", WEB / "build_board_json.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _one_worse(american: int) -> int:
    return -101 if american == 100 else american - 1


def test_the_printed_price_clears_and_one_cent_worse_does_not() -> None:
    rng = random.Random(20261101)
    checked = 0
    for _ in range(20_000):
        p = rng.uniform(0.15, 0.85)
        price = bet_down_to(p)
        if price is None:
            assert expected_value(p, PRICE_BAND[1]) < EDGE_THRESHOLD
            continue
        assert PRICE_BAND[0] <= price <= PRICE_BAND[1]
        assert expected_value(p, price) >= EDGE_THRESHOLD
        if price > PRICE_BAND[0]:
            assert expected_value(p, _one_worse(price)) < EDGE_THRESHOLD
        checked += 1
    assert checked > 10_000


def test_the_floor_is_the_band_and_nothing_clears_is_none() -> None:
    assert bet_down_to(0.95) == int(PRICE_BAND[0])
    assert bet_down_to(0.05) is None
    assert bet_down_to(None) is None and bet_down_to(0.0) is None and bet_down_to(1.0) is None


def test_the_number_is_recovered_from_an_edge_and_a_price() -> None:
    # The 2026-11-01 evening card: +225 at a 3.95% edge clears down to +219.
    assert bet_down_to_from_edge(0.0395, 225) == 219
    assert bet_down_to_from_edge(None, 225) is None
    assert bet_down_to_from_edge(0.03, "not a price") is None


def test_select_records_it_on_every_selection() -> None:
    import pandas as pd

    from cbb_betting_lab.competitions import COMPETITIONS

    competition = next(iter(COMPETITIONS.values()))
    rows = pd.DataFrame(
        [
            {"event_id": "e1", "commence_time": "2026-11-02T23:00:00Z", "slate_date": "2026-11-02",
             "home_team": "Duke Blue Devils", "away_team": "North Carolina Tar Heels", "market": "moneyline",
             "segment": "game", "player": "", "selection": "home", "line": None, "book": "b",
             "american_odds": 150.0},
        ]
    )
    wagers, _, _ = card_pricing.build_wagers(rows, competition=competition, key_for=card_pricing.default_key_for(competition))
    assert wagers
    result = card_pricing.select(
        wagers,
        {wagers[0].key: 0.45},
        approved=lambda _m: True,
        tip_state_for=lambda _w: card_pricing.TipState.UPCOMING,
    )
    assert len(result.selections) == 1
    row = result.selections[0]
    assert row["bet_down_to"] == bet_down_to(0.45)
    assert row["bet_down_to"] <= row["american_odds"]


def test_the_board_carries_it_on_bets_and_leans() -> None:
    builder = _builder()
    rows = [{"market": "spreads", "selection": "home", "line": "-3.5", "american_odds": "-110", "book": "b",
             "model_probability": "0.56", "edge": "0.04"}]
    lean = builder.pick_from_frozen(rows, "DUKE", "UNC", [], ALLOW)
    bet = builder.pick_from_frozen(rows, "DUKE", "UNC", rows, ALLOW)
    for pick in (lean, bet):
        assert pick["betDownTo"] == bet_down_to_from_edge(0.04, -110)
        assert "bet down to" in pick["sub"]
    recorded = [dict(rows[0], bet_down_to=-118)]
    assert builder.pick_from_frozen(recorded, "DUKE", "UNC", recorded, ALLOW)["betDownTo"] == -118


def test_the_board_cut_is_the_cards_cut() -> None:
    builder = _builder()
    # Away from an exact tie, where the two float paths may differ by a cent.
    for p in (0.31, 0.45, 0.503, 0.55, 0.613, 0.8, 0.9):
        assert builder.bet_down_to(p) == bet_down_to(p), p


def test_the_tracker_and_game_pages_show_it() -> None:
    assert "r.betDownTo" in (WEB / "Tracker.dc.html").read_text(encoding="utf-8")
    assert "p.betDownTo" in (WEB / "Game.dc.html").read_text(encoding="utf-8")
    assert '"betDownTo"' in (WEB / "site_pages.py").read_text(encoding="utf-8")
