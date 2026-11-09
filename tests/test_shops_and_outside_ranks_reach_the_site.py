"""Decision 93: each game page lists its price shops, and the ratings page
carries WAB and the NCAA's and ESPN's own ranks beside the lab's."""

from __future__ import annotations

import importlib.util
import json
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

WEB = Path(__file__).resolve().parents[1] / "web"


def _load(name: str, alias: str):
    spec = importlib.util.spec_from_file_location(alias, WEB / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _record(tmp_path: Path, stamp: str) -> Path:
    out = tmp_path / "data" / "outputs"
    out.mkdir(parents=True)
    record = {"latest_capture": stamp, "current": [
        {"event_id": "e1", "home_team": "Home U", "away_team": "Away U", "market": "spread",
         "selection": "home", "line": -3.5, "book": "slow", "american": 105, "fair_american": -102,
         "edge": 0.031, "books": 7},
        {"event_id": "e1", "home_team": "Home U", "away_team": "Away U", "market": "moneyline",
         "selection": "away", "line": None, "book": "slow", "american": 160, "fair_american": 150,
         "edge": 0.022, "books": 7},
    ]}
    (out / "cbb_price_shop.json").write_text(json.dumps(record), encoding="utf-8")
    return tmp_path


def test_a_games_shops_are_restated_from_the_boards_side(tmp_path):
    board = _load("build_board_json.py", "board_for_shops")
    now = datetime(2026, 11, 9, 19, 0, tzinfo=timezone.utc)
    groups = board.load_shops(_record(tmp_path, "2026-11-09T18:13:00+00:00"), now, lambda name: name)
    straight = board.shops_for(groups, ("Home U", "Away U"), "HOME", "AWAY")
    assert [s["label"] for s in straight] == ["HOME −3.5", "AWAY ML"]
    assert straight[0]["edgePct"] == 3.1 and straight[0]["book"] == "slow"
    # The provider filed the game the other way round: home and away swap.
    flipped = board.shops_for(groups, ("Away U", "Home U"), "AWAY", "HOME")
    assert [s["label"] for s in flipped] == ["HOME −3.5", "AWAY ML"]


def test_a_stale_shop_is_not_shown(tmp_path):
    board = _load("build_board_json.py", "board_for_stale_shops")
    now = datetime(2026, 11, 9, 23, 0, tzinfo=timezone.utc)
    assert board.load_shops(_record(tmp_path, "2026-11-09T18:13:00+00:00"), now, lambda n: n) == {}


def test_no_record_is_no_shop(tmp_path):
    board = _load("build_board_json.py", "board_for_no_shops")
    assert board.load_shops(tmp_path, datetime.now(timezone.utc), lambda n: n) == {}


def test_the_game_page_has_a_best_prices_section():
    text = (WEB / "Game.dc.html").read_text(encoding="utf-8")
    assert "Best prices right now" in text and "hasShops" in text


def _table(path: Path, as_of: str, rows: list[tuple[int, float]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([{"as_of": as_of, "season": 2027, "source": "s", "team": str(t), "team_id": t,
                   "adj_off": 100 + n / 2, "adj_def": 100 - n / 2, "adj_tempo": None} for t, n in rows]).to_csv(path, index=False)


def test_outside_ranks_are_read_by_their_own_net_and_refused_when_stale(tmp_path):
    from cbb_betting_lab.models import card_factors

    site = _load("site_pages.py", "site_for_outside")
    raw = tmp_path / "data" / "raw"
    _table(card_factors.second_opinion_path(raw, 2027, source="ncaa_net"), "2026-11-08", [(1, 5.0), (2, 9.0), (3, -2.0)])
    _table(card_factors.second_opinion_path(raw, 2027), "2026-10-01", [(1, 5.0), (2, 9.0)])
    ranks = site.outside_ranks(tmp_path, 2027, date(2026, 11, 9))
    assert ranks == {"netRank": {2: 1, 1: 2, 3: 3}}, "the BPI table is a month old and is not shown"


def test_the_ratings_page_shows_wab_net_and_bpi_and_no_subscription_table():
    text = (WEB / "Season.dc.html").read_text(encoding="utf-8")
    for column in ('"WAB"', '"NET"', '"BPI"'):
        assert column in text
