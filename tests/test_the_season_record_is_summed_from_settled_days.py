"""The Board strip's four season records, summed from the days already settled.

The shared page reads `record` in the NHL lab's shape -- `picks`, `straightUp`,
`totals`, `leans`, each a W-L(-P), and `season {nights, firstDate, lastDate,
missingNights}` -- and prints a dash with "Not tallied yet" for any key that is
absent. `web/settle_results.py::season_record` sums every frozen board up to
the day it settles, keeps each settled day under `history/settled/`, and
`write_season` puts the season onto board.json and into results.json as
`seasonRecord`.

What is pinned here is what would be silently wrong on the page:

* before a day has settled there is NO season record -- not 0-0, which is a
  tally nobody made;
* a lean is graded the same way as a best bet and is never counted in `picks`;
* a day the settler could not settle is counted in `missingNights`, not
  folded in as a day that went 0-0;
* the keys board.json already published (`markets`, `opinionsSoFar`) stay.

Everything runs against fixture boards; the scoreboard is replaced, so no
network is asked anything.
"""

from __future__ import annotations

import importlib.util
import json
import urllib.error
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SETTLE = PROJECT_ROOT / "web" / "settle_results.py"

#: The sport this repository settles; `main` validates it against its table.
SPORT = "cbb"

TEAMS = {
    "ND": {"name": "Notre Dame", "short": "Notre Dame"},
    "NOVA": {"name": "Villanova", "short": "Villanova"},
    "KU": {"name": "Kansas", "short": "Kansas"},
    "DUKE": {"name": "Duke", "short": "Duke"},
}


def _module():
    spec = importlib.util.spec_from_file_location("settle_results_season", SETTLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _game(gid: str, home: str, away: str, *, pick: dict | None = None) -> dict:
    """A frozen board's game with a model view: home favoured, spread and total."""
    return {
        "id": gid,
        "home": {"abbr": home, "projPts": 75.0, "winProb": 0.7},
        "away": {"abbr": away, "projPts": 68.0, "winProb": 0.3},
        "spread": {"current": -5.5, "proj": -7.0},
        "total": {"current": 140.5, "proj": 143.0},
        "pick": pick,
    }


def _board(*games: dict) -> dict:
    return {"season": "2026–27", "teams": TEAMS, "games": list(games)}


def _freeze(data: Path, day: str, board: dict, slot: str = "morning") -> None:
    hist = data / "history"
    hist.mkdir(parents=True, exist_ok=True)
    (hist / f"{day}_{slot}.json").write_text(json.dumps(board), encoding="utf-8")


def _live_board(data: Path) -> None:
    """Today's board.json as build_board_json writes its record today."""
    data.mkdir(parents=True, exist_ok=True)
    (data / "board.json").write_text(
        json.dumps({"record": {"markets": [], "marketsByTier": [], "opinionsSoFar": 0, "opinionsNeeded": 10000}, "games": []}),
        encoding="utf-8",
    )


def _finals(by_day: dict[str, dict | Exception]):
    """A scoreboard stand-in: finals per day, or the exception that day raises."""
    asked: list[str] = []

    def finals(sport: str, day: date) -> dict:
        asked.append(day.isoformat())
        answer = by_day.get(day.isoformat(), {})
        if isinstance(answer, Exception):
            raise answer
        return answer

    finals.asked = asked  # type: ignore[attr-defined]
    return finals


def _final(home: int, away: int) -> dict:
    return {"home": home, "away": away, "finish": "REG"}


def _run(module, data: Path, day: str) -> tuple[dict, dict]:
    assert module.main(["--data", str(data), "--sport", SPORT, "--date", day]) == 0
    results = json.loads((data / "results.json").read_text(encoding="utf-8"))
    board = json.loads((data / "board.json").read_text(encoding="utf-8"))
    return results, board


def test_no_season_record_until_a_day_has_settled(tmp_path: Path, monkeypatch) -> None:
    """A board was frozen and no game on it has a final: nothing is tallied.

    The record must stay ABSENT -- no `picks {w:0, l:0, p:0}`, no
    `seasonRecord` -- because the page renders an absent key as "Not tallied
    yet" and a 0-0 as a season that happened.
    """
    module = _module()
    _live_board(tmp_path)
    _freeze(tmp_path, "2026-11-03", _board(_game("1", "ND", "NOVA")))
    monkeypatch.setattr(module, "finals", _finals({}))

    results, board = _run(module, tmp_path, "2026-11-03")

    assert "seasonRecord" not in results
    for key in ("picks", "straightUp", "totals", "leans", "season"):
        assert key not in board["record"], f"record.{key} was published before any day settled"
    assert board["record"]["markets"] == [] and board["record"]["opinionsSoFar"] == 0


def test_no_season_record_before_any_board_exists(tmp_path: Path, monkeypatch) -> None:
    """Before opening night there is no board at all; still nothing tallied."""
    module = _module()
    _live_board(tmp_path)
    monkeypatch.setattr(module, "finals", _finals({}))

    results, board = _run(module, tmp_path, "2026-10-31")

    assert "seasonRecord" not in results
    assert set(board["record"]) == {"markets", "marketsByTier", "opinionsSoFar", "opinionsNeeded"}


def test_one_settled_day_publishes_the_four_records_and_keeps_the_old_keys(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    _live_board(tmp_path)
    _freeze(tmp_path, "2026-11-03", _board(_game("1", "ND", "NOVA"), _game("2", "KU", "DUKE")))
    # ND wins by 10 (model side, covers -5.5, 150 over 140.5); DUKE upsets KU
    # (miss, no cover, 130 under 140.5 against a model over).
    monkeypatch.setattr(module, "finals", _finals({"2026-11-03": {"1": _final(80, 70), "2": _final(60, 70)}}))

    results, board = _run(module, tmp_path, "2026-11-03")

    season = results["seasonRecord"]
    assert season["nights"] == 1 and season["missingNights"] == 0
    assert season["firstDate"] == season["lastDate"] == "2026-11-03"
    assert season["straightUp"] == {"w": 1, "l": 1}
    assert season["totals"] == {"w": 1, "l": 1, "p": 0}
    assert season["picks"] == {"w": 0, "l": 0, "p": 0}
    assert season["leans"] == {"w": 0, "l": 0, "p": 0}
    record = board["record"]
    for key in ("picks", "straightUp", "totals", "leans"):
        assert record[key] == season[key]
    assert {k: record["season"][k] for k in ("nights", "firstDate", "lastDate", "missingNights")} == {
        "nights": 1, "firstDate": "2026-11-03", "lastDate": "2026-11-03", "missingNights": 0}
    # The keys this board published before stay, whatever the page reads.
    assert "markets" in record and "opinionsSoFar" in record
    # results.json's own day keys stay too.
    assert {"picks", "straightUp", "ats", "totals"} <= set(results["summary"])


def test_a_lean_is_never_counted_in_picks(tmp_path: Path, monkeypatch) -> None:
    """Graded the same way, tallied apart: on the day and across the season."""
    module = _module()
    _live_board(tmp_path)
    bet = {"kind": "bet", "market": "Moneyline", "label": "Notre Dame ML", "price": -150}
    lean = {"kind": "lean", "market": "Total", "label": "Over 140.5", "line": 140.5, "price": -110}
    lean_lost = {"kind": "lean", "market": "Moneyline", "label": "Kansas ML", "price": -120}
    _freeze(tmp_path, "2026-11-03", _board(_game("1", "ND", "NOVA", pick=bet), _game("2", "KU", "DUKE", pick=lean_lost)))
    _freeze(tmp_path, "2026-11-04", _board(_game("3", "ND", "NOVA", pick=lean)))
    monkeypatch.setattr(module, "finals", _finals({
        "2026-11-03": {"1": _final(80, 70), "2": _final(60, 70)},
        "2026-11-04": {"3": _final(80, 70)},
    }))

    results, board = _run(module, tmp_path, "2026-11-04")

    assert results["summary"]["picks"] == {"w": 0, "l": 0, "p": 0}
    assert results["summary"]["leans"] == {"w": 1, "l": 0, "p": 0}
    season = results["seasonRecord"]
    assert season["picks"] == {"w": 1, "l": 0, "p": 0}, "a lean reached the best bets' record"
    assert season["leans"] == {"w": 1, "l": 1, "p": 0}
    assert board["record"]["picks"] == {"w": 1, "l": 0, "p": 0}


def test_a_frozen_opinion_is_graded_into_neither(tmp_path: Path, monkeypatch) -> None:
    """Every CBB pick today is `kind: "pass"` -- an opinion, not a bet or a lean."""
    module = _module()
    _live_board(tmp_path)
    opinion = {"kind": "pass", "market": "Moneyline", "label": "Notre Dame ML", "price": -150}
    _freeze(tmp_path, "2026-11-03", _board(_game("1", "ND", "NOVA", pick=opinion)))
    monkeypatch.setattr(module, "finals", _finals({"2026-11-03": {"1": _final(80, 70)}}))

    results, _ = _run(module, tmp_path, "2026-11-03")

    assert results["seasonRecord"]["picks"] == {"w": 0, "l": 0, "p": 0}
    assert results["seasonRecord"]["leans"] == {"w": 0, "l": 0, "p": 0}


def test_a_day_the_settler_skipped_is_in_missing_nights(tmp_path: Path, monkeypatch) -> None:
    """A day with a frozen board whose scoreboard cannot be read now.

    It is left out of every tally and counted, and it is not kept, so the
    next run tries it again.
    """
    module = _module()
    _live_board(tmp_path)
    _freeze(tmp_path, "2026-11-03", _board(_game("1", "ND", "NOVA")))
    _freeze(tmp_path, "2026-11-04", _board(_game("2", "KU", "DUKE")))
    down = urllib.error.HTTPError("https://example.invalid", 403, "Forbidden", None, None)
    monkeypatch.setattr(module, "finals", _finals({"2026-11-03": down, "2026-11-04": {"2": _final(80, 70)}}))

    results, board = _run(module, tmp_path, "2026-11-04")

    season = results["seasonRecord"]
    assert season["nights"] == 1
    assert season["missingNights"] == 1
    assert season["firstDate"] == season["lastDate"] == "2026-11-04"
    assert board["record"]["season"]["missingNights"] == 1
    assert not (tmp_path / "history" / "settled" / "2026-11-03.json").exists()


def test_a_day_with_no_final_yet_is_missing_not_zero(tmp_path: Path, monkeypatch) -> None:
    """The scoreboard answered, and nothing on the board is final yet."""
    module = _module()
    _live_board(tmp_path)
    _freeze(tmp_path, "2026-11-03", _board(_game("1", "ND", "NOVA")))
    _freeze(tmp_path, "2026-11-04", _board(_game("2", "KU", "DUKE")))
    monkeypatch.setattr(module, "finals", _finals({"2026-11-03": {}, "2026-11-04": {"2": _final(80, 70)}}))

    results, _ = _run(module, tmp_path, "2026-11-04")

    assert results["seasonRecord"]["nights"] == 1
    assert results["seasonRecord"]["missingNights"] == 1


def test_yesterdays_outage_is_a_missing_night(tmp_path: Path, monkeypatch) -> None:
    """The day this run settles could not be read: the season says so."""
    module = _module()
    _live_board(tmp_path)
    _freeze(tmp_path, "2026-11-03", _board(_game("1", "ND", "NOVA")))
    _freeze(tmp_path, "2026-11-04", _board(_game("2", "KU", "DUKE")))
    down = urllib.error.URLError("timed out")
    monkeypatch.setattr(module, "finals", _finals({"2026-11-03": {"1": _final(80, 70)}, "2026-11-04": down}))

    results, _ = _run(module, tmp_path, "2026-11-04")

    assert "could not be settled" in results["notice"]
    assert results["seasonRecord"]["nights"] == 1
    assert results["seasonRecord"]["missingNights"] == 1


def test_a_settled_day_is_kept_and_read_back_without_the_scoreboard(tmp_path: Path, monkeypatch) -> None:
    module = _module()
    _live_board(tmp_path)
    bet = {"kind": "bet", "market": "Moneyline", "label": "Notre Dame ML", "price": -150}
    _freeze(tmp_path, "2026-11-03", _board(_game("1", "ND", "NOVA", pick=bet)))
    _freeze(tmp_path, "2026-11-04", _board(_game("2", "KU", "DUKE")))
    _freeze(tmp_path, "2026-11-05", _board(_game("3", "KU", "DUKE")))
    first = _finals({"2026-11-03": {"1": _final(80, 70)}, "2026-11-04": {"2": _final(80, 70)}})
    monkeypatch.setattr(module, "finals", first)
    _run(module, tmp_path, "2026-11-04")
    assert (tmp_path / "history" / "settled" / "2026-11-03.json").is_file()

    # The next morning the scoreboard is down for every earlier day: the kept
    # day still counts, read from the cache rather than asked again.
    down = urllib.error.URLError("down")
    second = _finals({"2026-11-03": down, "2026-11-04": {"2": _final(80, 70)}, "2026-11-05": {"3": _final(80, 70)}})
    monkeypatch.setattr(module, "finals", second)
    results, _ = _run(module, tmp_path, "2026-11-05")

    assert "2026-11-03" not in second.asked  # type: ignore[attr-defined]
    season = results["seasonRecord"]
    assert season["nights"] == 3 and season["missingNights"] == 0
    assert season["picks"] == {"w": 1, "l": 0, "p": 0}
    assert season["firstDate"] == "2026-11-03" and season["lastDate"] == "2026-11-05"


def test_the_season_object_is_absent_tallies_when_nothing_settled(tmp_path: Path) -> None:
    """`season_record` itself: the span alone, every tally left out."""
    module = _module()
    season = module.season_record(SPORT, date(2026, 11, 3), tmp_path / "history", None, False)
    assert season == {"nights": 0, "firstDate": None, "lastDate": None, "missingNights": 0}
