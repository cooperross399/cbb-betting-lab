"""An unplayed fixture is stored as 0-0, and the tier table read it as a result.

`tier_table` dropped rows with a missing score. The 2027 schedule arrives
with all 1,629 games `STATUS_SCHEDULED` and both scores stored as integer
zeros, which are not missing, so every fixture entered the margins as a game
decided by nothing. Measured on the real schedules on 2026-09-24: no tier
moves in any window a published output uses (2019-2026), and the first window
to include 2027 moves 34 teams and 4 conferences for (2026, 2027) and 29 teams
for (2025, 2026, 2027), while 2027 alone tiers 297 teams off fixtures where
the correct answer is nobody.

Also here: a season whose play-by-play is empty was left out of the segments
table with no `_skip` record, though `build`'s docstring promises every
skipped season is reported.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab.conferences import Tier, played_games, tier_table

A_TEAMS = (1, 2, 3, 4)
B_TEAMS = (5, 6, 7, 8)


def _game(home, away, home_score, away_score, *, completed=True, name="STATUS_FINAL"):
    return {
        "home_id": home, "away_id": away,
        "home_conference_id": 10 if home in A_TEAMS else 20,
        "away_conference_id": 10 if away in A_TEAMS else 20,
        "home_score": home_score, "away_score": away_score,
        "status_type_completed": completed, "status_type_name": name,
    }


def _played(repeat: int = 2) -> list[dict]:
    """Conference A beats conference B by ten, every time."""
    return [_game(a, b, 80, 70) for a in A_TEAMS for b in B_TEAMS for _ in range(repeat)]


def _fixtures(repeat: int = 2) -> list[dict]:
    """The same pairings, scheduled and not yet played, as the feed stores them."""
    return [
        _game(a, b, 0, 0, completed=False, name="STATUS_SCHEDULED")
        for a in A_TEAMS for b in B_TEAMS for _ in range(repeat)
    ]


def test_an_unplayed_fixture_is_not_a_game_decided_by_nothing():
    played_only = tier_table({2025: pd.DataFrame(_played())}, (2025,))
    with_fixtures = tier_table({2025: pd.DataFrame(_played() + _fixtures())}, (2025,))

    assert with_fixtures.team_margin == played_only.team_margin
    assert with_fixtures.team_tier == played_only.team_tier
    # And the planted league is what it should be: +10 is high-major. Averaged
    # with eight 0-0 fixtures it would have read +5, a mid-major.
    assert {with_fixtures.team_tier[t] for t in A_TEAMS} == {Tier.HIGH_MAJOR}


def test_a_season_of_nothing_but_fixtures_places_nobody():
    table = tier_table({2027: pd.DataFrame(_fixtures(repeat=4))}, (2027,))
    assert table.team_tier == {}
    assert table.conference_tier == {}


def test_the_status_name_decides_when_the_flag_is_absent():
    """The synthetic league in test_fit_ratings carries only the name."""
    frame = pd.DataFrame(
        _played()
        + [_game(1, 5, 0, 0, name="STATUS_POSTPONED")]
        + [_game(2, 6, 2, 0, name="STATUS_FORFEIT")]
    ).drop(columns=["status_type_completed"])

    kept = played_games(frame)
    assert "STATUS_POSTPONED" not in set(kept["status_type_name"])
    assert "STATUS_FORFEIT" in set(kept["status_type_name"]), (
        "a forfeit counts today and has a completed flag of True in the feed"
    )


def test_a_schedule_that_cannot_say_which_games_were_played_is_refused():
    frame = pd.DataFrame(_played()).drop(columns=["status_type_completed", "status_type_name"])
    with pytest.raises(ValueError, match="cannot be told"):
        tier_table({2025: frame}, (2025,))


def test_each_season_is_filtered_before_the_concat():
    """Filtering after it would read NaN for a season lacking the flag and drop
    that season whole. Four games a season is below MINIMUM_GAMES; the teams
    are placed only if both seasons count."""
    with_flag = pd.DataFrame(_played(repeat=1))
    name_only = pd.DataFrame(_played(repeat=1)).drop(columns=["status_type_completed"])

    table = tier_table({2025: with_flag, 2026: name_only}, (2025, 2026))

    assert {table.team_tier[t] for t in A_TEAMS} == {Tier.HIGH_MAJOR}


def test_the_real_2027_schedule_is_all_fixtures_stored_as_zero():
    path = Path(__file__).parent / "fixtures" / "real_data" / "mbb_schedule_2027.parquet"
    schedule = pd.read_parquet(path)

    assert len(schedule) > 0
    assert (schedule["home_score"] == 0).all() and schedule["home_score"].notna().all(), (
        "the shape this file is about: unplayed, and not missing"
    )
    assert played_games(schedule).empty


def test_an_empty_play_by_play_season_is_reported_as_skipped(tmp_path, monkeypatch):
    from cbb_betting_lab.data import build_datasets as B
    from cbb_betting_lab.data import hoopr

    def no_feed(season, raw_dir=None):
        raise hoopr.FeedError("not cached in this test")

    def segments(season, raw_dir=None):
        if season == 2026:
            return pd.DataFrame(columns=["game_id", "season"])
        return pd.DataFrame([{"game_id": 1, "season": season}])

    monkeypatch.setattr(B, "build_team_games", no_feed)
    monkeypatch.setattr(B, "build_player_games", no_feed)
    monkeypatch.setattr(B, "build_game_segments", segments)

    written = B.build((2025, 2026), raw_dir=tmp_path, processed_dir=tmp_path)

    assert 2026 in written["skipped"]["game_segments"]
    assert written["game_segments"] == 1
