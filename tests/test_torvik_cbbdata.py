"""T-Rank through the cbbdata API (decision 123): never barttorvik.com itself."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from cbb_betting_lab.data import second_opinion as SO


def _archive():
    rows = []
    for day, shift in (("2026-11-24", 0.0), ("2026-11-25", 1.0)):
        for i in range(5):
            rows.append({"rank": i + 1, "team": f"Team {i}", "adj_o": 110.0 + i + shift,
                         "adj_d": 100.0 - i, "adj_tempo": 68.0, "date": day, "year": 2027})
    return pd.DataFrame(rows)


def test_the_table_is_the_newest_date_on_or_before_the_day():
    table = SO.torvik_on(_archive(), "2026-11-25")
    assert table.attrs["as_of"] == "2026-11-25"
    assert list(table.columns) == ["team", "adj_off", "adj_def", "adj_tempo"]
    assert table.loc[table["team"] == "Team 0", "adj_off"].item() == 111.0
    assert SO.torvik_on(_archive(), "2026-11-24").attrs["as_of"] == "2026-11-24"
    with pytest.raises(SO.SecondOpinionError):
        SO.torvik_on(_archive(), "2026-11-01")


def test_login_registers_once_when_refused_and_never_needs_a_printed_key(monkeypatch):
    calls = []

    def post(url, body, **_):
        calls.append(url)
        if url == SO.CBBDATA_REGISTER_URL:
            return 201, b""
        return (401, b"") if calls.count(SO.CBBDATA_LOGIN_URL) == 1 else (200, json.dumps({"api_key": "k"}).encode())

    monkeypatch.setattr(SO, "_post_json", post)
    key, created = SO.cbbdata_key("u", "p", "e@x")
    assert (key, created) == ("k", True)
    assert calls == [SO.CBBDATA_LOGIN_URL, SO.CBBDATA_REGISTER_URL, SO.CBBDATA_LOGIN_URL]


def test_no_email_means_no_registration(monkeypatch):
    monkeypatch.setattr(SO, "_post_json", lambda url, body, **_: (401, b""))
    with pytest.raises(SO.SecondOpinionError):
        SO.cbbdata_key("u", "p", "")


def test_the_reader_never_asks_barttorvik_com():
    for url in (SO.CBBDATA_LOGIN_URL, SO.CBBDATA_REGISTER_URL, SO.TORVIK_ARCHIVE_URL, SO.TORVIK_CURRENT_URL):
        assert url.startswith("https://www.cbbdata.com/api/")
        assert "barttorvik" not in url


def test_the_current_table_is_read_as_the_day_it_was_read(monkeypatch):
    import io

    current = pd.DataFrame({"team": [f"Team {i}" for i in range(5)], "adj_o": [112.0] * 5,
                            "adj_d": [99.0] * 5, "adj_t": [67.0] * 5, "year": [2027] * 5})
    buffer = io.BytesIO()
    current.to_parquet(buffer)
    seen = []
    monkeypatch.setattr(SO, "_get", lambda url, **_: seen.append(url) or buffer.getvalue())
    table = SO.torvik_on(SO.fetch_torvik_current("k", 2027, "2026-11-27"), "2026-11-27")
    assert seen[0].startswith(SO.TORVIK_CURRENT_URL + "?")
    assert table.attrs["as_of"] == "2026-11-27"
    assert len(table) == 5 and table["adj_tempo"].eq(67.0).all()
    with pytest.raises(SO.SecondOpinionError):
        SO.torvik_on(SO.fetch_torvik_current("k", 2027, "2026-11-27"), "2026-11-26")
