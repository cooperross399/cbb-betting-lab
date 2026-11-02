"""Every game a book has hung a line on shows that line on the board.

On 2026-11-02 the public board carried no market line on any of 182 games.
Two causes, both pinned here:

1. Publish Board restored only *successful* gameday runs. Every gameday run
   that morning froze and published its card and then went red on the settle
   pass (which exits 1 on any night props go ungraded), so the board skipped
   them and built from a day-old artifact that held no capture for the day.
2. The board's only price source was the card's own capture, taken twice a
   day for the games the card can stake. A game added after the card, or a
   board built before the first card, had nothing.

The fix for (2) is `posted_lines`: the main line ESPN's free scoreboard posts
beside each game fills any market the capture does not hold. The capture wins
wherever it has a number, because it is every book's best price, not one's.
Runs on fixtures; no network.
"""

from __future__ import annotations

import csv
import importlib.util
import json
from datetime import date
from pathlib import Path

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD = PROJECT_ROOT / "web" / "build_board_json.py"
DAY = date(2026, 11, 2)
COLUMNS = ("event_id", "commence_time", "slate_date", "home_team", "away_team", "market", "segment",
           "player", "selection", "line", "american_odds", "book", "provider_key")


def _load():
    spec = importlib.util.spec_from_file_location("board_build_for_posted_lines", BUILD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


#: ESPN's scoreboard `competitions[0].odds` for an away favourite, trimmed to
#: the keys read. Murray State at Tennessee State, 2026-11-02.
ESPN_ODDS = [{
    "provider": {"id": "100", "name": "DraftKings", "displayName": "DraftKings"},
    "details": "MUR -10.5", "overUnder": 165.5, "spread": 10.5,
    "moneyline": {"home": {"close": {"odds": "+400"}, "open": {"odds": "+260"}},
                  "away": {"close": {"odds": "-535"}, "open": {"odds": "-325"}}},
    "pointSpread": {"home": {"close": {"line": "+10.5", "odds": "-112"}, "open": {"line": "+8.5", "odds": "-112"}},
                    "away": {"close": {"line": "-10.5", "odds": "-108"}, "open": {"line": "-8.5", "odds": "-108"}}},
    "total": {"over": {"close": {"line": "o165.5", "odds": "-108"}, "open": {"line": "o161.5", "odds": "-110"}},
              "under": {"close": {"line": "u165.5", "odds": "-112"}, "open": {"line": "u161.5", "odds": "-110"}}},
}]


def _side(name: str, abbr: str) -> dict:
    return {"name": name, "abbr": abbr, "color": "123456", "record": "", "score": None}


def _slate(board) -> list[dict]:
    posted = board.posted_lines({"odds": ESPN_ODDS}, "Tennessee State Tigers", "Murray State Racers")
    return [
        {"id": "501", "tip": "2026-11-03T00:00Z", "neutral": False, "venue": "", "city": "", "tv": "—", "state": "pre",
         "home": _side("Tennessee State Tigers", "TNST"), "away": _side("Murray State Racers", "MUR"), "posted": posted},
        # A Division I side hosting a non-Division I school: no book posts a line.
        {"id": "502", "tip": "2026-11-03T00:00Z", "neutral": False, "venue": "", "city": "", "tv": "—", "state": "pre",
         "home": _side("Harvard Crimson", "HARV"), "away": _side("MIT Engineers", "MIT"),
         "posted": board.posted_lines({}, "Harvard Crimson", "MIT Engineers")},
    ]


def _build(lab: Path, monkeypatch) -> dict:
    board = _load()
    slate = _slate(board)
    monkeypatch.setattr(board, "slate_for", lambda day: slate)
    monkeypatch.setattr(board, "load_model", lambda lab, day, games: None)
    built = board.build(lab, DAY)
    json.dumps(built, allow_nan=False)
    return built


def _game(board: dict, gid: str) -> dict:
    return next(g for g in board["games"] if g["id"] == gid)


def test_the_posted_line_is_read_from_the_home_side() -> None:
    posted = _load().posted_lines({"odds": ESPN_ODDS}, "Tennessee State Tigers", "Murray State Racers")
    by = {(r["market"], r["selection"]): r for r in posted["rows"]}
    assert by[("moneyline", "home")]["american_odds"] == 400
    assert by[("moneyline", "away")]["american_odds"] == -535
    assert by[("spread", "home")]["line"] == 10.5 and by[("spread", "away")]["line"] == -10.5
    assert by[("total_points", "over")]["line"] == 165.5
    assert {r["book"] for r in posted["rows"]} == {"DraftKings"}
    assert posted["open"] == {"moneyline": {"home": 260, "away": -325}, "spread": 8.5, "total": 161.5}


def test_a_board_with_no_capture_shows_the_posted_line(tmp_path: Path, monkeypatch) -> None:
    g = _game(_build(tmp_path, monkeypatch), "501")
    assert g["moneyline"]["current"] == {"home": 400, "away": -535}
    assert g["spread"]["current"] == 10.5 and g["spread"]["homePrice"] == -112
    assert g["total"]["current"] == 165.5 and g["total"]["overPrice"] == -108
    assert g["moneyline"]["open"] == {"home": 260, "away": -325}
    assert g["spread"]["open"] == 8.5 and g["total"]["open"] == 161.5


def test_a_game_no_book_quotes_carries_no_invented_line(tmp_path: Path, monkeypatch) -> None:
    g = _game(_build(tmp_path, monkeypatch), "502")
    assert "moneyline" not in g and "spread" not in g and "total" not in g


def test_the_capture_wins_where_it_holds_a_market(tmp_path: Path, monkeypatch) -> None:
    """The capture holds only the spread; the moneyline and total come from the
    posted line, and the spread is the capture's, not the scoreboard's."""
    folder = tmp_path / "data" / "staging" / "cbb"
    folder.mkdir(parents=True)
    base = {"event_id": "e", "commence_time": "", "slate_date": DAY.isoformat(), "home_team": "Tennessee State Tigers",
            "away_team": "Murray State Racers", "segment": "game", "player": "", "book": "fixturebook", "provider_key": ""}
    with (folder / f"{DAY.isoformat()}_morning.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerow({**base, "market": "spread", "selection": "home", "line": 11.5, "american_odds": -105})
        writer.writerow({**base, "market": "spread", "selection": "away", "line": -11.5, "american_odds": -115})

    g = _game(_build(tmp_path, monkeypatch), "501")
    assert g["spread"]["current"] == 11.5 and g["spread"]["homePrice"] == -105
    assert g["spread"]["open"] is None, "one capture is a price, not an open; the scoreboard's open is another book's"
    assert g["moneyline"]["current"] == {"home": 400, "away": -535}
    assert g["total"]["current"] == 165.5


def test_publish_board_restores_a_red_gameday_run_that_holds_a_card() -> None:
    workflow = yaml.safe_load((PROJECT_ROOT / ".github" / "workflows" / "publish-board.yml").read_text(encoding="utf-8"))
    steps = next(iter(workflow["jobs"].values()))["steps"]
    restore = next(s for s in steps if s.get("name", "").startswith("Restore the lab's latest run"))["run"]
    assert "--workflow cbb-gameday-refresh.yml --status success" not in restore
    assert 'select(.conclusion == "success" or .conclusion == "failure")' in restore
