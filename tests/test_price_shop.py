"""The price shop (decision 91): a book beating the market's own fair price."""

from __future__ import annotations

import pandas as pd

from cbb_betting_lab.reports import price_shop as PS


def _quote(cap, book, sel, odds, *, market="moneyline", line=None, event="e1",
           tip="2026-11-10T00:00:00Z"):
    return {"captured_at": cap, "slate_date": "2026-11-09", "event_id": event,
            "commence_time": tip, "home_team": "Home U", "away_team": "Away U",
            "market": market, "segment": "game", "player": "", "selection": sel,
            "line": line, "book": book, "american_odds": odds}


def _pair(cap, book, home, away, **kw):
    return [_quote(cap, book, "home", home, **kw), _quote(cap, book, "away", away, **kw)]


def _store(slow_book_away=+150, close_away=+120):
    rows = []
    early, late = "2026-11-09T17:13:00+00:00", "2026-11-09T23:13:00+00:00"
    for book in ("a", "b", "c"):
        rows += _pair(early, book, -140, +120)
        rows += _pair(late, book, -150, close_away)
    rows += _pair(early, "slow", -170, slow_book_away)
    return pd.DataFrame(rows)


def test_a_slow_book_is_a_shop_and_a_fair_price_is_not():
    board = PS.fair_board(_store())
    found = PS.shops(board)
    early = found[found["captured_at"] == found["captured_at"].min()]
    assert list(early["selection"]) == ["away"]
    assert early.iloc[0]["best_book"] == "slow"
    assert early.iloc[0]["shop_edge"] > PS.SHOP_EDGE


def test_fewer_than_three_books_is_no_fair_price():
    store = pd.DataFrame(_pair("2026-11-09T17:13:00+00:00", "a", -110, -110)
                         + _pair("2026-11-09T17:13:00+00:00", "b", -110, +200))
    assert PS.fair_board(store).empty


def test_a_quote_after_tip_is_no_price():
    store = _store()
    store["commence_time"] = "2026-11-09T12:00:00Z"
    assert PS.fair_board(store).empty


def test_the_shop_is_graded_against_the_close_at_the_same_line():
    board = PS.fair_board(_store())
    grades = PS.graded(board, PS.shops(board), now="2026-11-11T00:00:00Z")
    first = grades[grades["selection"] == "away"].iloc[0]
    assert first["close_fair"] == first["close_fair"]
    assert first["clv"] > 0


def test_an_untipped_game_is_not_graded():
    board = PS.fair_board(_store())
    assert PS.graded(board, PS.shops(board), now="2026-11-09T18:00:00Z").empty


def test_a_line_the_close_no_longer_quotes_is_ungraded_not_guessed():
    rows = []
    early, late = "2026-11-09T17:13:00+00:00", "2026-11-09T23:13:00+00:00"
    for book in ("a", "b", "c"):
        rows += [_quote(early, book, "home", -110, market="spread", line=-3.0),
                 _quote(early, book, "away", -110, market="spread", line=3.0),
                 _quote(late, book, "home", -110, market="spread", line=-5.0),
                 _quote(late, book, "away", -110, market="spread", line=5.0)]
    rows += [_quote(early, "slow", "home", +115, market="spread", line=-3.0),
             _quote(early, "slow", "away", -140, market="spread", line=3.0)]
    board = PS.fair_board(pd.DataFrame(rows))
    grades = PS.graded(board, PS.shops(board), now="2026-11-11T00:00:00Z")
    assert len(grades) == 1 and grades["clv"].isna().all()


def test_a_market_off_the_allowlist_is_not_listed():
    board = PS.fair_board(_store())
    assert PS.shops(board, allowlisted=["spread"]).empty


def test_the_record_is_per_tier_and_never_pooled():
    record = PS.build_record(_store(), tiers={"e1": "low_major"}, looks=182,
                             as_of="2026-11-11", now="2026-11-11T00:00:00Z")
    assert [c["tier"] for c in record["cells"]] == list(PS.TIERS) + [PS.UNPLACED]
    low = next(c for c in record["cells"] if c["tier"] == "low_major")
    assert low["shops"] >= 1 and low["low"] is None  # under the floor: no interval
    text = PS.render(record)
    assert "pooled" not in text.lower() and "all tiers" not in text.lower()
    assert "Closing-line value is not a return" in text


def test_an_empty_store_says_so():
    record = PS.build_record(None, tiers=None, looks=182, as_of="2026-11-09")
    assert record["latest_capture"] is None
    assert "No capture holds an untipped game" in PS.render(record)


def _with_slow_book_at(*stamps, away=+150):
    rows = []
    for stamp in stamps:
        for book in ("a", "b", "c"):
            rows += _pair(stamp, book, -140, +120)
        rows += _pair(stamp, "slow", -170, away)
    return pd.DataFrame(rows)


def test_a_new_alert_sized_shop_is_an_alert():
    record = PS.build_record(_with_slow_book_at("2026-11-09T17:13:00+00:00"), tiers={}, looks=200,
                             as_of="x", now="2026-11-09T18:00:00Z")
    assert [a["book"] for a in record["alerts"]] == ["slow"]
    assert record["alerts"][0]["edge"] >= PS.ALERT_EDGE
    text = PS.alert_text(record)
    assert "Away U moneyline" in text and "+150 at slow" in text and "ET" in text
    assert "not a model pick" in text


def test_a_shop_already_alerted_an_hour_ago_is_not_posted_again():
    store = _with_slow_book_at("2026-11-09T17:13:00+00:00", "2026-11-09T18:13:00+00:00")
    record = PS.build_record(store, tiers={}, looks=200, as_of="x", now="2026-11-09T19:00:00Z")
    assert record["current"] and record["alerts"] == []
    assert PS.alert_text(record) == ""


def test_a_shop_under_the_alert_bar_is_listed_but_not_posted():
    # +134 against a fair price of about 43.8% clears 2% but not 3%.
    store = _with_slow_book_at("2026-11-09T17:13:00+00:00", away=+134)
    record = PS.build_record(store, tiers={}, looks=200, as_of="x", now="2026-11-09T18:00:00Z")
    assert record["current"] and all(r["edge"] < PS.ALERT_EDGE for r in record["current"])
    assert record["alerts"] == []


def test_the_alert_is_written_beside_the_record(tmp_path):
    record = PS.build_record(_with_slow_book_at("2026-11-09T17:13:00+00:00"), tiers={}, looks=200,
                             as_of="x", now="2026-11-09T18:00:00Z")
    PS.write(record, tmp_path)
    assert (tmp_path / PS.ALERT_NAME).read_text(encoding="utf-8").startswith("**CBB price shop")
