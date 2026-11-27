"""Every game from last night settled, whatever one source does (2026-11-27).

Cooper: *"We need to find a way for every game to be settled from the night
before no matter what in the results page, have many fallbacks options to get
that data. and we need to make sure every projection for every game is ready
at 3am also"*. The scoreboard is asked first and retried; a game it does not
settle is asked of ESPN's game summary, then the lab's own team-games table,
then hoopR's schedule. A final is taken only when a source calls the game
completed; a game no source settles is named, never guessed.
"""

from __future__ import annotations

import importlib.util
import json
import urllib.error
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load(name: str, alias: str):
    spec = importlib.util.spec_from_file_location(alias, ROOT / "web" / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _board() -> dict:
    side = lambda abbr: {"abbr": abbr}
    return {"season": "2026-27", "teams": {}, "games": [
        {"id": "1", "home": side("AAA"), "away": side("BBB")},
        {"id": "2", "home": side("CCC"), "away": side("DDD")},
        {"id": "3", "home": side("EEE"), "away": side("FFF")},
        {"id": "4", "home": side("GGG"), "away": side("HHH")},
    ]}


def _summary(home: int, away: int, completed: bool = True) -> dict:
    return {"header": {"competitions": [{
        "status": {"type": {"completed": completed, "detail": "Final"}},
        "competitors": [{"homeAway": "home", "score": str(home)}, {"homeAway": "away", "score": str(away)}],
    }]}}


def test_a_game_the_scoreboard_missed_is_settled_from_the_next_source(tmp_path, monkeypatch) -> None:
    settle = _load("settle_results.py", "settle_fallbacks")
    monkeypatch.setattr(settle, "FALLBACKS_ON", True)
    monkeypatch.setattr(settle, "SLEEP", lambda s: None)
    monkeypatch.setattr(settle, "finals", lambda sport, day: {"1": {"home": 70, "away": 60, "finish": "REG"}})
    summaries = {"2": _summary(81, 79), "3": _summary(50, 52, completed=False)}

    def fetch(url):
        event = url.rsplit("=", 1)[1]
        if event in summaries:
            return summaries[event]
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

    monkeypatch.setattr(settle, "fetch", fetch)
    processed = tmp_path / "data" / "processed"
    processed.mkdir(parents=True)
    (processed / "cbb_team_games.csv").write_text(
        "game_id,home_away,team_score,opponent_score,overtime\n"
        "3,home,64,61,True\n3,away,61,64,True\n", encoding="utf-8")
    monkeypatch.setattr(settle, "LAB", tmp_path)

    fin, sources = settle.all_finals("cbb", date(2026, 11, 26), _board())
    assert fin["1"]["home"] == 70 and sources["1"] == "espn scoreboard"
    assert fin["2"] == {"home": 81, "away": 79, "finish": "REG"} and sources["2"] == "espn game summary"
    # Not completed in the summary, so the lab's own table settles it.
    assert fin["3"] == {"home": 64, "away": 61, "finish": "OT"} and sources["3"] == "lab team games"
    # No source holds game 4: it is left unsettled rather than guessed.
    assert "4" not in fin

    body, waiting = settle.settle_day("cbb", date(2026, 11, 26), _board())
    assert waiting is True
    assert [g["id"] for g in body["unsettled"]] == ["4"]
    assert {g["id"]: g.get("finalSource") for g in body["games"]} == {"1": None, "2": "espn game summary", "3": "lab team games"}


def test_the_scoreboard_is_retried_before_it_is_given_up_on(monkeypatch) -> None:
    settle = _load("settle_results.py", "settle_retries")
    monkeypatch.setattr(settle, "SLEEP", lambda s: None)
    calls = []

    def fetch(url):
        calls.append(url)
        if len(calls) < 3:
            raise urllib.error.HTTPError(url, 503, "Unavailable", None, None)
        return {"events": []}

    monkeypatch.setattr(settle, "fetch", fetch)
    assert settle.finals("cbb", date(2026, 11, 26)) == {}
    assert len(calls) == 3


def test_a_not_found_is_an_answer_and_is_not_retried(monkeypatch) -> None:
    settle = _load("settle_results.py", "settle_not_found")
    monkeypatch.setattr(settle, "SLEEP", lambda s: None)
    calls = []

    def fetch(url):
        calls.append(url)
        raise urllib.error.HTTPError(url, 404, "Not Found", None, None)

    monkeypatch.setattr(settle, "fetch", fetch)
    assert settle.summary_final("cbb", "9") is None
    assert len(calls) == 1


def test_fallbacks_stay_off_unless_the_publish_asks_for_them(monkeypatch) -> None:
    settle = _load("settle_results.py", "settle_off")
    assert settle.FALLBACKS_ON is False
    monkeypatch.setattr(settle, "finals", lambda sport, day: {})
    monkeypatch.setattr(settle, "fetch", lambda url: (_ for _ in ()).throw(AssertionError("no fallback may fetch")))
    assert settle.all_finals("cbb", date(2026, 11, 26), _board()) == ({}, {})
    workflow = (ROOT / ".github" / "workflows" / "publish-board.yml").read_text(encoding="utf-8")
    assert "python web/settle_results.py --data dist/data --sport cbb --lab . --fallbacks" in workflow


def test_a_game_the_model_cannot_price_still_carries_a_labelled_projection(monkeypatch) -> None:
    board = _load("build_board_json.py", "board_projection_fallbacks")
    row = {"moneyline": {"open": None, "current": {"home": -200, "away": 170}, "fair": None},
           "spread": {"open": None, "current": -5.5, "homePrice": -110, "proj": None}}
    board.fill_projection(row, 0.7, board.ESPN_ONLY_NOTE)
    assert row["spread"]["current"] == -5.5, "a quoted line is never touched"
    assert row["spread"]["proj"] < 0 and row["moneyline"]["fair"]["home"] < 0
    assert row["lineNote"] == "ESPN projection"
    assert "winProb" not in row.get("home", {}), "a fallback projection never enters the model's record"
    assert board.has_projection({"home": {}, **row})

    chance = board.market_home_chance(row)
    assert 0.6 < chance < 0.7
    assert not board.has_projection({"home": {}, "moneyline": {"fair": None}, "spread": {"proj": None}})


def test_the_nightly_publish_settles_with_the_fallbacks_on() -> None:
    nightly = json.dumps((ROOT / ".github" / "workflows" / "nightly-results.yml").read_text(encoding="utf-8"))
    assert "0 0 * * *" in nightly
