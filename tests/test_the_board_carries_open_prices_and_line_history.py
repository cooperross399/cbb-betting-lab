"""Open prices and line movement on the board, read from the staged captures.

`providers.staging.staging_path` writes one file per slate day and slot,
`data/staging/cbb/<day>_<slot>.csv`, and each is one read of the board. The
page shows Open / Current / Fair per market and draws a sparkline from
`lineHistory[gameId]` when it exists. So:

* `moneyline.open`, `spread.open` and `total.open` come from the FIRST capture
  of the slate day -- the morning file when the current is the evening's --
  and are null when only one capture holds the game: one read is a price,
  never an open that happens to equal it;
* the current price is the LATEST capture holding the game, not every
  capture pooled (which let the morning's best price stand as tonight's);
* `lineHistory[gameId]` has one point per capture, and is absent with one.

The captures are ordered by the card's slot order, never by name: "evening"
sorts before "morning", and an alphabetical open would be the evening price.

Everything runs on fixture files in a temporary lab; the slate and the model
are replaced, so no network and no ratings are asked anything.
"""

from __future__ import annotations

import csv
import importlib.util
import json
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD = PROJECT_ROOT / "web" / "build_board_json.py"
HISTORY = PROJECT_ROOT / "web" / "site_history.py"

DAY = date(2026, 11, 3)
COLUMNS = ("event_id", "commence_time", "slate_date", "home_team", "away_team", "market", "segment",
           "player", "selection", "line", "american_odds", "book", "provider_key")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _side(name: str, abbr: str) -> dict:
    return {"name": name, "abbr": abbr, "color": "123456", "record": "", "score": None}


#: Two games: the first is on both captures, the second tipped before the
#: evening read and is on the morning's only.
SLATE = [
    {"id": "401", "tip": "2026-11-04T00:00Z", "neutral": False, "venue": "", "city": "", "tv": "—", "state": "pre",
     "home": _side("Notre Dame Fighting Irish", "ND"), "away": _side("Villanova Wildcats", "NOVA")},
    {"id": "402", "tip": "2026-11-03T17:00Z", "neutral": False, "venue": "", "city": "", "tv": "—", "state": "pre",
     "home": _side("Kansas Jayhawks", "KU"), "away": _side("Duke Blue Devils", "DUKE")},
]


def _rows(home: str, away: str, *, ml: tuple[int | None, int | None], spread: float, total: float) -> list[dict]:
    base = {"event_id": "e", "commence_time": "", "slate_date": DAY.isoformat(), "home_team": home,
            "away_team": away, "segment": "game", "player": "", "book": "fixturebook", "provider_key": ""}
    out = []
    for selection, price in zip(("home", "away"), ml):
        if price is not None:
            out.append({**base, "market": "moneyline", "selection": selection, "line": "", "american_odds": price})
    out.append({**base, "market": "spread", "selection": "home", "line": spread, "american_odds": -110})
    out.append({**base, "market": "spread", "selection": "away", "line": -spread, "american_odds": -110})
    out.append({**base, "market": "total_points", "selection": "over", "line": total, "american_odds": -110})
    out.append({**base, "market": "total_points", "selection": "under", "line": total, "american_odds": -110})
    return out


def _stage(lab: Path, slot: str, rows: list[dict]) -> None:
    folder = lab / "data" / "staging" / "cbb"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / f"{DAY.isoformat()}_{slot}.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def _build(lab: Path, monkeypatch) -> dict:
    board = _load(BUILD, "board_build_for_open_prices")
    monkeypatch.setattr(board, "slate_for", lambda day: SLATE)
    monkeypatch.setattr(board, "load_model", lambda lab, day, games: None)
    built = board.build(lab, DAY)
    # It must survive the writer's own serialisation, which refuses NaN.
    json.dumps(built, allow_nan=False)
    return built


def _game(board: dict, gid: str) -> dict:
    return next(g for g in board["games"] if g["id"] == gid)


def _morning() -> list[dict]:
    return (_rows("Notre Dame Fighting Irish", "Villanova Wildcats", ml=(-150, 130), spread=-3.5, total=141.5)
            + _rows("Kansas Jayhawks", "Duke Blue Devils", ml=(-200, 170), spread=-5.5, total=150.5))


def _evening() -> list[dict]:
    return _rows("Notre Dame Fighting Irish", "Villanova Wildcats", ml=(-180, 155), spread=-4.5, total=139.5)


def test_open_is_null_with_one_capture(tmp_path: Path, monkeypatch) -> None:
    _stage(tmp_path, "morning", _morning())

    board = _build(tmp_path, monkeypatch)

    for gid in ("401", "402"):
        g = _game(board, gid)
        assert g["moneyline"]["open"] is None
        assert g["spread"]["open"] is None
        assert g["total"]["open"] is None
        assert g["moneyline"]["current"] is not None, "the one capture is still the current price"
    assert "lineHistory" not in board, "one capture is a price, not a movement"


def test_open_is_the_morning_capture_when_the_current_is_the_evening(tmp_path: Path, monkeypatch) -> None:
    _stage(tmp_path, "morning", _morning())
    _stage(tmp_path, "evening", _evening())

    g = _game(_build(tmp_path, monkeypatch), "401")

    assert g["moneyline"]["open"] == {"home": -150, "away": 130}
    assert g["moneyline"]["current"] == {"home": -180, "away": 155}
    assert g["spread"]["open"] == -3.5 and g["spread"]["current"] == -4.5
    assert g["total"]["open"] == 141.5 and g["total"]["current"] == 139.5


def test_captures_are_not_pooled_into_the_current_price(tmp_path: Path, monkeypatch) -> None:
    """The morning's home -150 is a better price than the evening's -180, and
    with the two files pooled it was published as tonight's best home price."""
    _stage(tmp_path, "morning", _morning())
    _stage(tmp_path, "evening", _evening())

    g = _game(_build(tmp_path, monkeypatch), "401")

    assert g["moneyline"]["current"]["home"] == -180


def test_a_game_only_the_morning_held_keeps_its_last_price_and_has_no_open(tmp_path: Path, monkeypatch) -> None:
    _stage(tmp_path, "morning", _morning())
    _stage(tmp_path, "evening", _evening())

    board = _build(tmp_path, monkeypatch)
    g = _game(board, "402")

    assert g["moneyline"]["current"] == {"home": -200, "away": 170}
    assert g["moneyline"]["open"] is None and g["spread"]["open"] is None and g["total"]["open"] is None
    assert "402" not in board["lineHistory"]


def test_line_history_has_one_point_per_capture_in_slot_order(tmp_path: Path, monkeypatch) -> None:
    _stage(tmp_path, "evening", _evening())
    _stage(tmp_path, "morning", _morning())

    history = _build(tmp_path, monkeypatch)["lineHistory"]

    assert set(history) == {"401"}
    series = history["401"]
    assert set(series) == {"ml_home", "spread", "total"}
    assert [p["v"] for p in series["ml_home"]] == [-150, -180]
    assert [p["v"] for p in series["spread"]] == [-3.5, -4.5]
    assert [p["v"] for p in series["total"]] == [141.5, 139.5]
    assert [p["slot"] for p in series["total"]] == ["morning", "evening"]
    assert all(p["t"] and p["t"].startswith(DAY.isoformat()) for p in series["total"])
    assert series["total"][0]["t"] < series["total"][1]["t"]


def test_a_one_sided_open_moneyline_opens_nothing(tmp_path: Path, monkeypatch) -> None:
    """The page names the favourite from the pair; half a pair is not an open."""
    _stage(tmp_path, "morning", _rows("Notre Dame Fighting Irish", "Villanova Wildcats", ml=(-150, None), spread=-3.5, total=141.5))
    _stage(tmp_path, "evening", _evening())

    g = _game(_build(tmp_path, monkeypatch), "401")

    assert g["moneyline"]["open"] is None
    assert g["spread"]["open"] == -3.5


def test_no_staged_capture_leaves_every_price_absent(tmp_path: Path, monkeypatch) -> None:
    board = _build(tmp_path, monkeypatch)

    assert all("moneyline" not in g for g in board["games"])
    assert "lineHistory" not in board


def test_site_history_keeps_the_builders_capture_series(tmp_path: Path, monkeypatch) -> None:
    """site_history.py records one point per build and used to overwrite
    `lineHistory` with that; a series the builder drew from the captures is
    the better record and is kept."""
    _stage(tmp_path / "lab", "morning", _morning())
    _stage(tmp_path / "lab", "evening", _evening())
    board = _build(tmp_path / "lab", monkeypatch)
    data = tmp_path / "data"
    data.mkdir()
    (data / "board.json").write_text(json.dumps(board), encoding="utf-8")

    assert _load(HISTORY, "site_history_for_open_prices").main(["--data", str(data)]) == 0

    written = json.loads((data / "board.json").read_text(encoding="utf-8"))
    assert written["lineHistory"]["401"] == board["lineHistory"]["401"]
