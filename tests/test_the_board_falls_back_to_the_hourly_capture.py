"""A game the card did not capture takes its line from the hourly capture.

Decision 103. Cooper, 2026-11-14: *"We need to find a way to have lines/odds
for every single game on the website."* The card reads the board twice a day
and ESPN's scoreboard takes a game's line down the moment it tips, so a game
that tipped before the card's read was published with no line at all: on
2026-11-14 that was Maine-Drexel, Bradley-George Mason and the rest of the
early tips. The line-movement store reads every book on every game hourly,
and Publish Board already copies it to `data/processed/`.

So, on fixtures in a temporary lab with the slate and the model replaced:

* a game only the hourly store holds gets its line, from the LAST capture
  taken at or before tip -- the closing line, not a read after tip;
* the open comes from the store's first capture when two captures hold it;
* the card's own capture still wins wherever it has a number;
* a game the provider filed the other way round is restated from the board's
  side (decision 72);
* a game nobody captured stays without a line: nothing is estimated.
"""

from __future__ import annotations

import csv
import importlib.util
import json
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD = PROJECT_ROOT / "web" / "build_board_json.py"

DAY = date(2026, 11, 14)
STORE_COLUMNS = ("captured_at", "slate_date", "event_id", "commence_time", "home_team", "away_team",
                 "market", "segment", "player", "selection", "line", "book", "american_odds")
STAGED_COLUMNS = ("event_id", "commence_time", "slate_date", "home_team", "away_team", "market", "segment",
                  "player", "selection", "line", "american_odds", "book", "provider_key")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _side(name: str, abbr: str) -> dict:
    return {"name": name, "abbr": abbr, "color": "123456", "record": "", "score": None}


TIP = "2026-11-14T17:00:00Z"

SLATE = [
    # Tipped before the card read the board; ESPN has taken its line down.
    {"id": "501", "tip": TIP, "neutral": False, "venue": "", "city": "", "tv": "—", "state": "in", "posted": {},
     "home": _side("Maine Black Bears", "ME"), "away": _side("Drexel Dragons", "DREX")},
    # On the card's capture too: the card's number wins.
    {"id": "502", "tip": "2026-11-15T00:00:00Z", "neutral": False, "venue": "", "city": "", "tv": "—", "state": "pre",
     "posted": {}, "home": _side("Kansas Jayhawks", "KU"), "away": _side("Duke Blue Devils", "DUKE")},
    # The provider files this one the other way round.
    {"id": "503", "tip": TIP, "neutral": True, "venue": "", "city": "", "tv": "—", "state": "in", "posted": {},
     "home": _side("George Mason Patriots", "GMU"), "away": _side("Bradley Braves", "BRAD")},
    # Nobody hangs a line on a Division I side hosting a non-Division I school.
    {"id": "504", "tip": TIP, "neutral": False, "venue": "", "city": "", "tv": "—", "state": "pre", "posted": {},
     "home": _side("Radford Highlanders", "RAD"), "away": _side("Shenandoah Hornets", "SHEN")},
]


def _rows(when: str, tip: str, home: str, away: str, *, ml, spread: float, total: float, book="fixturebook"):
    base = {"captured_at": when, "slate_date": DAY.isoformat(), "event_id": f"{home}-{away}", "commence_time": tip,
            "home_team": home, "away_team": away, "segment": "game", "player": "", "book": book}
    return [
        {**base, "market": "moneyline", "selection": "home", "line": "", "american_odds": ml[0]},
        {**base, "market": "moneyline", "selection": "away", "line": "", "american_odds": ml[1]},
        {**base, "market": "spread", "selection": "home", "line": spread, "american_odds": -110},
        {**base, "market": "spread", "selection": "away", "line": -spread, "american_odds": -110},
        {**base, "market": "total_points", "selection": "over", "line": total, "american_odds": -110},
        {**base, "market": "total_points", "selection": "under", "line": total, "american_odds": -110},
    ]


def _store(lab: Path, rows: list[dict]) -> None:
    folder = lab / "data" / "processed"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "cbb_line_movement.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=STORE_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _stage(lab: Path, rows: list[dict]) -> None:
    folder = lab / "data" / "staging" / "cbb"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f"{DAY.isoformat()}_evening.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=STAGED_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows({**r, "provider_key": ""} for r in rows)


def _build(lab: Path, monkeypatch) -> dict:
    board = _load(BUILD, "board_build_for_hourly_fallback")
    monkeypatch.setattr(board, "slate_for", lambda day: SLATE)
    monkeypatch.setattr(board, "load_model", lambda lab, day, games: None)
    built = board.build(lab, DAY)
    json.dumps(built, allow_nan=False)
    return built


def _game(board: dict, gid: str) -> dict:
    return next(g for g in board["games"] if g["id"] == gid)


def _fixture(lab: Path) -> None:
    _store(lab,
           _rows("2026-11-14T13:00:00+00:00", TIP, "Maine Black Bears", "Drexel Dragons", ml=(120, -140), spread=2.5, total=131.5)
           + _rows("2026-11-14T16:13:00+00:00", TIP, "Maine Black Bears", "Drexel Dragons", ml=(135, -160), spread=3.5, total=130.5)
           # Taken after tip: a live price, never the line the game closed at.
           + _rows("2026-11-14T17:13:00+00:00", TIP, "Maine Black Bears", "Drexel Dragons", ml=(600, -1000), spread=12.5, total=120.5)
           + _rows("2026-11-14T16:13:00+00:00", "2026-11-15T00:00:00Z", "Kansas Jayhawks", "Duke Blue Devils", ml=(-300, 250), spread=-7.5, total=150.5)
           + _rows("2026-11-14T16:13:00+00:00", TIP, "Bradley Braves", "George Mason Patriots", ml=(-150, 130), spread=-3.5, total=140.5))


def test_a_game_only_the_hourly_capture_holds_gets_its_closing_line(tmp_path: Path, monkeypatch) -> None:
    _fixture(tmp_path)
    g = _game(_build(tmp_path, monkeypatch), "501")

    assert g["moneyline"]["current"] == {"home": 135, "away": -160}
    assert g["spread"]["current"] == 3.5 and g["spread"]["homePrice"] == -110 and g["spread"]["awayPrice"] == -110
    assert g["total"]["current"] == 130.5
    assert g["moneyline"]["open"] == {"home": 120, "away": -140}
    assert g["spread"]["open"] == 2.5 and g["total"]["open"] == 131.5


def test_the_cards_own_capture_wins(tmp_path: Path, monkeypatch) -> None:
    _fixture(tmp_path)
    _stage(tmp_path, _rows("", "", "Kansas Jayhawks", "Duke Blue Devils", ml=(-280, 240), spread=-6.5, total=149.5))
    g = _game(_build(tmp_path, monkeypatch), "502")

    assert g["moneyline"]["current"] == {"home": -280, "away": 240}
    assert g["spread"]["current"] == -6.5
    assert g["total"]["current"] == 149.5


def test_a_game_filed_the_other_way_round_is_restated(tmp_path: Path, monkeypatch) -> None:
    _fixture(tmp_path)
    g = _game(_build(tmp_path, monkeypatch), "503")

    # The provider's home is Bradley at -3.5; the board's home is George Mason.
    assert g["moneyline"]["current"] == {"home": 130, "away": -150}
    assert g["spread"]["current"] == 3.5


def test_a_game_nobody_captured_has_no_line(tmp_path: Path, monkeypatch) -> None:
    _fixture(tmp_path)
    g = _game(_build(tmp_path, monkeypatch), "504")

    assert "moneyline" not in g and "spread" not in g and "total" not in g
