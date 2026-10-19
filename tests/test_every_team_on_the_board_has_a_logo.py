"""Every Division I team has a logo, and the board points only at files that exist.

The shared pages draw a logo in every team circle from `teams[abbr].logo`,
falling back to `./logos/<ABBR>.png` and then to the coloured abbreviation.
`web/fetch_logos.py` fills `web/logos/` once and writes `web/logos/SOURCES.md`;
`web/build_board_json.py` writes the key only for a file that exists when it
runs. A key that names a missing file is a broken image on the public page,
and a team with no file is a circle that silently stops matching its
neighbours.

**Which universe this is pinned against, and why.** The builder holds no
static list of teams: it keys `teams` by whatever abbreviation ESPN's
scoreboard gives it on the night. This repository commits no list of Division
I teams either; its universe is DERIVED, by `population.division_one_team_ids`,
from the tracked hoopR schedules under `tests/fixtures/real_data/`. Those are
not a usable pin for file names: the 2025-26 schedule spells Butler `BUT` and
New Orleans `UNO` where ESPN now writes `BTLR` and `NOLA`, and it still counts
Saint Francis (PA), which has left Division I; the 2026-27 schedule is the
early-season cut and names 319 of the teams. So the list pinned here is
`SOURCES.md`, which is ESPN's conference walk for the season (365 schools,
not the 362 of `/teams?groups=50`), and the committed universe is held to it
BY ESPN TEAM ID — ids do not drift the way abbreviations do — so a school the
lab's own schedule calls Division I and the logo list does not know is a
failure here rather than a dash on the board.

PNG validity is checked with the standard library (signature, IHDR, 500 px,
more than 2 KB, every IDAT inflating to the size the header promises), the
same check the fetch script applies, because CI installs no imaging library.
"""

from __future__ import annotations

import importlib.util
import re
from datetime import date
from pathlib import Path

import pandas as pd

from cbb_betting_lab.population import division_one_team_ids

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WEB = PROJECT_ROOT / "web"
LOGOS = WEB / "logos"
SOURCES = LOGOS / "SOURCES.md"
BUILD = WEB / "build_board_json.py"
FETCH = WEB / "fetch_logos.py"
SCHEDULES = PROJECT_ROOT / "tests" / "fixtures" / "real_data"

ROW = re.compile(r"^\|\s*(?P<file>[^|]+?)\s*\|\s*(?P<team>[^|]+?)\s*\|\s*(?P<id>\d+)\s*\|\s*(?P<source>[^|]+?)\s*\|\s*$")


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _rows() -> list[dict]:
    rows = [m.groupdict() for m in map(ROW.match, SOURCES.read_text(encoding="utf-8").splitlines()) if m]
    assert rows, f"{SOURCES.relative_to(PROJECT_ROOT)} lists no team; run web/fetch_logos.py"
    return rows


def _abbr(row: dict) -> str:
    assert row["file"].endswith(".png"), f"{row['team']} (ESPN id {row['id']}) has no logo file: {row['source']}"
    return row["file"][: -len(".png")]


def test_every_team_on_the_list_has_a_valid_logo_file() -> None:
    fetch = _load(FETCH, "fetch_logos_for_test")
    rows = _rows()
    missing = [f"{r['team']} ({r['id']}): {r['source']}" for r in rows if not r["file"].endswith(".png")]
    assert not missing, f"{len(missing)} of {len(rows)} teams have no logo: {missing}"
    problems = {}
    for row in rows:
        path = LOGOS / row["file"]
        if not path.is_file():
            problems[row["file"]] = "listed in SOURCES.md but not on disk"
            continue
        problem = fetch.png_problem(path.read_bytes())
        if problem:
            problems[row["file"]] = problem
    assert not problems, f"{len(problems)} logo file(s) are not usable: {problems}"


def test_no_two_schools_share_a_file_and_every_file_is_sourced() -> None:
    rows = _rows()
    files = [r["file"] for r in rows]
    ids = [r["id"] for r in rows]
    assert len(set(files)) == len(files), "two schools share an abbreviation, so one logo would stand for both"
    assert len(set(ids)) == len(ids), "an ESPN team id is listed twice"
    for row in rows:
        assert row["source"].startswith("https://"), f"{row['file']} names no source URL: {row['source']!r}"
    on_disk = {p.name for p in LOGOS.glob("*.png")}
    assert on_disk == set(files), (
        f"files without a SOURCES.md row: {sorted(on_disk - set(files))}; "
        f"rows without a file: {sorted(set(files) - on_disk)}"
    )
    text = SOURCES.read_text(encoding="utf-8")
    assert "trademarks of their leagues and clubs, shown for\nidentification only" in text


def test_the_lab_s_own_division_one_universe_is_on_the_logo_list() -> None:
    """By ESPN team id, against the newest season the lab has committed."""
    newest = max(SCHEDULES.glob("mbb_schedule_*.parquet"), key=lambda p: int(p.stem.rsplit("_", 1)[-1]))
    universe = {str(int(i)) for i in division_one_team_ids(pd.read_parquet(newest))}
    assert universe, f"{newest.name} carries no Division I team"
    listed = {r["id"] for r in _rows()}
    unknown = sorted(universe - listed)
    assert not unknown, (
        f"{len(unknown)} of {len(universe)} Division I team ids in {newest.name} have no row in "
        f"SOURCES.md: {unknown}. Re-run web/fetch_logos.py."
    )


def test_the_board_points_every_team_at_its_logo_and_only_at_files_that_exist(tmp_path: Path, monkeypatch) -> None:
    """Through `build()` itself, over a slate that names every listed team.

    The slate is the only thing replaced (it would otherwise ask ESPN), plus
    the model, which would otherwise read ratings this test is not about. One
    side that is not on the list stands in for a non-Division-I opponent: it
    has no file, so it must carry no `logo` key at all.
    """
    board = _load(BUILD, "board_build_for_logos")
    abbrs = [_abbr(r) for r in _rows()]
    stranger = "ZZNOTD1"
    assert not (LOGOS / f"{stranger}.png").exists()
    sides = abbrs + ([stranger] if len(abbrs) % 2 else [stranger, stranger + "X"])

    def side(abbr: str) -> dict:
        return {"name": f"{abbr} Team", "abbr": abbr, "color": "123456", "record": "", "score": None}

    slate = [
        {"id": str(n), "tip": "2026-11-03T00:00Z", "neutral": False, "venue": "", "city": "", "tv": "—",
         "state": "pre", "home": side(sides[2 * n]), "away": side(sides[2 * n + 1])}
        for n in range(len(sides) // 2)
    ]
    monkeypatch.setattr(board, "slate_for", lambda day: slate)
    monkeypatch.setattr(board, "load_model", lambda lab, day, games: None)
    teams = board.build(tmp_path, date(2026, 11, 3))["teams"]

    wrong = {a: teams.get(a, {}).get("logo") for a in abbrs if teams.get(a, {}).get("logo") != f"./logos/{a}.png"}
    assert not wrong, f"{len(wrong)} of {len(abbrs)} teams are not pointed at their own logo: {wrong}"
    dangling = {a: t["logo"] for a, t in teams.items() if "logo" in t and not (WEB / t["logo"]).resolve().is_file()}
    assert not dangling, f"logo keys that name no file: {dangling}"
    assert "logo" not in teams[stranger], "a team with no logo file must carry no logo key"
