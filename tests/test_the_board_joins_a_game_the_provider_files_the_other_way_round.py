"""A game the odds provider files the other way round from ESPN still gets its odds.

Measured on opening day, 2026-11-01: ESPN filed Notre Dame at Villanova (Rome)
and Liberty at High Point; the provider filed both with the sides reversed. The
board joins its captures on the `(home, away)` pair in ESPN's orientation, so
both games showed a model spread and no market line beside it (decision 72).

The fix restates the reversed rows from the board's side: names swap, a side
selection names the other word, and every line stays with the team it already
belonged to.
"""

from __future__ import annotations

import csv
import importlib.util
import json
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD = PROJECT_ROOT / "web" / "build_board_json.py"

DAY = date(2026, 11, 1)
COLUMNS = ("event_id", "commence_time", "slate_date", "home_team", "away_team", "market", "segment",
           "player", "selection", "line", "american_odds", "book", "provider_key")


def _load():
    spec = importlib.util.spec_from_file_location("board_build_for_flipped_sides", BUILD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _side(name: str, abbr: str) -> dict:
    return {"name": name, "abbr": abbr, "color": "123456", "record": "", "score": None}


#: ESPN's orientation: Villanova the home side.
SLATE = [
    {"id": "401920982", "tip": "2026-11-01T14:30Z", "neutral": True, "venue": "", "city": "", "tv": "—",
     "state": "pre", "home": _side("Villanova Wildcats", "VILL"), "away": _side("Notre Dame Fighting Irish", "ND")},
]


def _provider_rows() -> list[dict]:
    """The provider's orientation: Notre Dame home, a 7-point underdog."""
    base = {"event_id": "e", "commence_time": "", "slate_date": DAY.isoformat(),
            "home_team": "Notre Dame Fighting Irish", "away_team": "Villanova Wildcats",
            "segment": "game", "player": "", "book": "fixturebook", "provider_key": ""}
    return [
        {**base, "market": "moneyline", "selection": "home", "line": "", "american_odds": 270},
        {**base, "market": "moneyline", "selection": "away", "line": "", "american_odds": -315},
        {**base, "market": "spread", "selection": "home", "line": 7.0, "american_odds": -110},
        {**base, "market": "spread", "selection": "away", "line": -7.0, "american_odds": -110},
        {**base, "market": "total_points", "selection": "over", "line": 147.0, "american_odds": -110},
        {**base, "market": "total_points", "selection": "under", "line": 147.0, "american_odds": -110},
    ]


def _stage(lab: Path, rows: list[dict]) -> None:
    folder = lab / "data" / "staging" / "cbb"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f"{DAY.isoformat()}_morning.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def test_a_reversed_game_carries_the_market_from_the_boards_side(tmp_path: Path, monkeypatch) -> None:
    board = _load()
    monkeypatch.setattr(board, "slate_for", lambda day: SLATE)
    monkeypatch.setattr(board, "load_model", lambda lab, day, games: None)
    _stage(tmp_path, _provider_rows())

    built = board.build(tmp_path, DAY)
    json.dumps(built, allow_nan=False)
    game = built["games"][0]

    assert game["spread"]["current"] == -7.0, "Villanova, the board's home side, is the 7-point favourite"
    assert game["moneyline"]["current"] == {"home": -315, "away": 270}
    assert game["total"]["current"] == 147.0


def test_flip_row_restates_a_ticket_without_changing_it() -> None:
    board = _load()
    row = {"home_team": "A", "away_team": "B", "market": "spread", "selection": "home", "line": "7.5"}
    assert board.flip_row(row) == {"home_team": "B", "away_team": "A", "market": "spread",
                                   "selection": "away", "line": "7.5"}
    total = {"home_team": "A", "away_team": "B", "market": "team_total", "selection": "home_over", "line": "70.5"}
    assert board.flip_row(total)["selection"] == "away_over" and board.flip_row(total)["line"] == "70.5"
    over = {"home_team": "A", "away_team": "B", "market": "total_points", "selection": "over", "line": "147"}
    assert board.flip_row(over)["selection"] == "over" and board.flip_row(over)["line"] == "147"


def test_orient_never_overwrites_a_pair_the_board_already_holds() -> None:
    board = _load()
    groups = {("A", "B"): [{"x": 1}], ("B", "A"): [{"home_team": "B", "away_team": "A", "selection": "home"}]}
    board.orient(groups, ("A", "B"))
    assert groups[("A", "B")] == [{"x": 1}]
