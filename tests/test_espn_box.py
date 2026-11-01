"""The ESPN results supplement and the power-index second opinion.

Fixtures are real ESPN payloads trimmed to one game (Purdue 82, Evansville 51,
2025-11-04) and three teams, so the column mapping is held against what ESPN
actually sends, and checked against the numbers hoopR published for the same
game.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from cbb_betting_lab.data import build_datasets as B
from cbb_betting_lab.data import espn_box as E
from cbb_betting_lab.data import second_opinion as SO

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "espn"


def _fake_fetch(url: str) -> dict:
    if "scoreboard" in url:
        if "20251104" in url:
            return json.loads((FIXTURES / "scoreboard_20251104.json").read_text())
        return {"events": []}
    if "summary" in url and "401828553" in url:
        return json.loads((FIXTURES / "summary_401828553.json").read_text())
    raise E.EspnError(f"unexpected {url}")


def test_a_finished_game_lands_in_hoopr_columns_with_hoopr_numbers(tmp_path):
    report = E.supplement(2026, first_day="2025-11-03", last_day="2025-11-04",
                          published_ids=set(), raw_dir=tmp_path, fetch=_fake_fetch, pause_s=0)
    assert report.fetched == 1 and not report.failed
    teams = E.load("team_box", 2026, tmp_path).set_index("team_id")
    purdue, evansville = teams.loc[2509], teams.loc[339]
    # hoopR's published row for this game, read 2026-11-01.
    assert (purdue.team_score, purdue.field_goals_made, purdue.field_goals_attempted) == (82, 28, 59)
    assert (purdue.three_point_field_goals_made, purdue.free_throws_attempted) == (13, 16)
    assert (evansville.offensive_rebounds, evansville.turnovers, evansville.team_home_away) == (20, 10, "away")
    segments = E.load("segments", 2026, tmp_path).iloc[0]
    assert (segments.periods, segments.home_score_h1, segments.away_score_h1) == (2, 41, 22)
    players = E.load("player_box", 2026, tmp_path)
    hughes = players[players.athlete_id == 5177734].iloc[0]
    assert (hughes.minutes, hughes.points, hughes.rebounds, hughes.three_point_field_goals_made) == (30, 15, 11, 3)


def test_a_game_hoopr_published_is_never_fetched_and_a_cached_one_not_twice(tmp_path):
    report = E.supplement(2026, first_day="2025-11-04", last_day="2025-11-04",
                          published_ids={401828553}, raw_dir=tmp_path, fetch=_fake_fetch, pause_s=0)
    assert report.fetched == 0 and report.already_published == 1
    assert E.load("team_box", 2026, tmp_path).empty
    E.supplement(2026, first_day="2025-11-04", last_day="2025-11-04",
                 published_ids=set(), raw_dir=tmp_path, fetch=_fake_fetch, pause_s=0)
    again = E.supplement(2026, first_day="2025-11-04", last_day="2025-11-04",
                         published_ids=set(), raw_dir=tmp_path, fetch=_fake_fetch, pause_s=0)
    assert again.fetched == 0 and again.already_cached == 1
    # Once hoopR publishes it, the supplement drops its copy.
    E.supplement(2026, first_day="2025-11-05", last_day="2025-11-05",
                 published_ids={401828553}, raw_dir=tmp_path, fetch=_fake_fetch, pause_s=0)
    assert E.load("team_box", 2026, tmp_path).empty


def test_the_tables_build_from_the_supplement_when_hoopr_has_no_box(tmp_path):
    E.supplement(2026, first_day="2025-11-04", last_day="2025-11-04",
                 published_ids=set(), raw_dir=tmp_path, fetch=_fake_fetch, pause_s=0)
    schedule = pd.DataFrame({
        "id": [401828553], "game_id": [401828553], "neutral_site": [False],
        "home_id": [2509], "away_id": [339], "venue_id": [1],
        "home_venue_id": [1], "away_venue_id": [2],
        "venue_address_city": ["West Lafayette"], "status_type_name": ["STATUS_FINAL"],
        "season_type": [2], "date": ["2025-11-04T23:30Z"],
    })
    target = tmp_path / "cbb" / "schedules"
    target.mkdir(parents=True)
    schedule.to_parquet(target / "mbb_schedule_2026.parquet", index=False)
    try:
        games = B.build_team_games(2026, raw_dir=tmp_path)
    except Exception as exc:  # classify may need columns a real schedule carries
        raise AssertionError(f"the supplement could not build: {exc}") from exc
    row = games.set_index("team_id").loc[2509]
    assert (row.margin, row.periods, row.team_score_h1, row.slate_date) == (31, 2, 41, "2025-11-04")


def test_the_power_index_is_read_by_team_id_on_this_labs_scale():
    frame = SO.parse_bpi((FIXTURES / "powerindex.json").read_bytes(), season=2027)
    assert len(frame) == 3 and frame["team_id"].notna().all()
    assert frame["adj_tempo"].isna().all()
    # Defence positive when good in BPI, positive when bad here.
    assert (frame["adj_def"] < 100).all() and (frame["adj_off"] > 100).all()
