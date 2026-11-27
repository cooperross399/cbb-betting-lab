"""Every school on a D-I slate gets a projection from the model (2026-11-27).

Cooper: *"Still need full projections for every game and figure out how to
learn every team so you can do that. Need total projections and spreads"*.
On 2026-11-27, 16 of 55 games fell back to ESPN's predictor: six were D-I
sides hosting a non-D-I school the ratings had no number for, and ten were
tournament pairings set after hoopR's nightly schedule build. These pin the
three repairs: a non-D-I school is rated from its games against D-I; the
board finds a fixture by its ESPN event id when the names do not resolve; and
a fixture missing from the cached schedule is added from ESPN's slate.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab.models import non_division_one, ratings
from cbb_betting_lab.reports import card_matchups


def _ratings() -> ratings.Ratings:
    return ratings.Ratings(
        season=2027, as_of="2026-11-27", priced_through="2026-11-26", games=1, team_games=2,
        league_efficiency=100.0, league_tempo=68.0,
        offence={1: 5.0, 2: 0.0}, defence={1: -5.0, 2: 0.0}, tempo={1: 0.0, 2: 1.0},
    )


def _game(game_id, home, away, home_pts, away_pts, poss, day="2026-11-20", season=2027):
    base = {"game_id": game_id, "season": season, "slate_date": day, "game_state": "non_di_opponent",
            "neutral_site": False, "periods": 2, "possessions_estimated": poss}
    return [
        {**base, "team_id": home, "opponent_id": away, "home_away": "home",
         "team_score": home_pts, "opponent_score": away_pts},
        {**base, "team_id": away, "opponent_id": home, "home_away": "away",
         "team_score": away_pts, "opponent_score": home_pts},
    ]


def _history() -> pd.DataFrame:
    rows = (_game(10, 1, 900, 90, 60, 70.0) + _game(11, 2, 900, 80, 62, 70.0)
            + _game(12, 1, 901, 100, 50, 72.0)
            # On the day being priced: never read.
            + _game(13, 2, 901, 50, 120, 70.0, day="2026-11-27"))
    return pd.DataFrame(rows)


def test_a_non_division_one_school_is_rated_from_its_games_against_division_one():
    base = _ratings()
    extended, baseline = non_division_one.extend(
        base, _history(), season=2027, day="2026-11-27", teams=[1, 900, 901, 902])
    # The D-I fit is untouched, and every school asked about is rated --
    # including 902, never seen, which takes the measured class level.
    assert extended.offence[1] == base.offence[1]
    assert {900, 901, 902} <= set(extended.offence) and extended.baseline_teams == {900, 901, 902}
    level = baseline.level
    assert level.games == 3
    assert extended.offence[902] == pytest.approx(level.offence)
    assert extended.prior_weight[("offence", 902)] == 1.0
    # 900's offence: 60/70 and 62/70 per 100 against defences of -5 and 0.
    r900 = [100 * 60 / 70 - 100 + 5, 100 * 62 / 70 - 100]
    r901 = [100 * 50 / 72 - 100 + 5]
    mean = (sum(r900) + sum(r901)) / 3
    assert level.offence == pytest.approx(mean)
    assert extended.offence[900] == pytest.approx(mean + sum(r - mean for r in r900) / (2 + non_division_one.SHRINK_GAMES))
    # The game on the priced day (901 scoring 120) moved nothing.
    assert extended.offence[901] < level.offence


def test_the_matchup_prices_and_says_how_the_visitor_was_rated():
    extended, _ = non_division_one.extend(
        _ratings(), _history(), season=2027, day="2026-11-27", teams=[1, 900])
    game = ratings.matchup(extended, home_team_id=1, away_team_id=900, venue_state="home")
    assert game.priceable
    assert game.identified_by == "non_di_baseline"
    dist = ratings.to_distribution(game)
    assert dist.expected_margin > 10 and 100 < dist.expected_total < 200


def test_switched_off_the_school_is_refused_as_before(monkeypatch):
    monkeypatch.setattr(non_division_one, "RATE_NON_DIVISION_ONE", False)
    extended, _ = non_division_one.extend(
        _ratings(), _history(), season=2027, day="2026-11-27", teams=[1, 900])
    assert ratings.matchup(extended, home_team_id=1, away_team_id=900, venue_state="home").priceable is False


def _schedule() -> pd.DataFrame:
    row = {"id": 401000001, "game_id": 401000001, "game_date": date(2026, 11, 27),
           "home_id": 1, "away_id": 900, "home_display_name": "Alpha Ants", "home_location": "Alpha",
           "home_name": "Ants", "away_display_name": "Small College Owls", "away_location": "Small College",
           "away_name": "Owls", "home_conference_id": 5.0, "away_conference_id": None,
           "neutral_site": False, "status_type_name": "STATUS_SCHEDULED"}
    return pd.DataFrame([row])


def test_an_espn_event_id_finds_its_fixture_when_the_names_do_not():
    rows = pd.DataFrame([
        {"event_id": "401000001", "home_team": "Alpha Ants", "away_team": "Small College Owls"},
        # A provider's hex id never matches a schedule id.
        {"event_id": "abc123", "home_team": "Nobody", "away_team": "Small College Owls"},
        # The right id on the wrong day is not a match.
    ])
    joined, _unresolved, _ = card_matchups.attach_game_ids(rows, day="2026-11-27", schedule=_schedule())
    got = dict(zip(joined["event_id"], joined["game_id"]))
    assert got["401000001"] == 401000001
    assert pd.isna(got["abc123"])
    joined, _, _ = card_matchups.attach_game_ids(rows.iloc[:1], day="2026-11-28", schedule=_schedule())
    assert pd.isna(joined["game_id"].iloc[0])


def test_a_fixture_the_cached_schedule_lacks_is_added_from_the_slate(monkeypatch):
    raw = Path("/nonexistent-raw")
    key = (2027, str(raw))
    base = _schedule()
    monkeypatch.setitem(ratings._SCHEDULE_CACHE, key, base)
    extra = pd.concat([base, base.assign(id=401000002, game_id=401000002, home_id="2", away_id=1)])
    assert ratings.supplement_schedule(2027, extra, raw) == 1
    merged = ratings._SCHEDULE_CACHE[key]
    assert sorted(merged["id"].tolist()) == [401000001, 401000002]
    assert merged.loc[merged["id"] == 401000002, "home_id"].iloc[0] == 2
    # A game already held is never replaced, so a second pass adds nothing.
    assert ratings.supplement_schedule(2027, extra, raw) == 0
