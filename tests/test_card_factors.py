"""Tonight's context on the card: form, rest, who is missing, the second opinion.

`models/card_factors.py` layers tonight's context onto the season ratings on
the one seam every reader prices through (`ratings.matchups_for`). These tests
pin what each layer reads, what it refuses, and that the layers recorded on a
matchup end at the price the matchup carries.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab.models import card_factors as CF
from cbb_betting_lab.models import ratings
from cbb_betting_lab.reports import price_backtest as PB

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "real_data"
DAY = "2026-03-12"


@pytest.fixture(scope="module")
def lab(tmp_path_factory) -> Path:
    """A lab laid out as the seam expects, from the tracked real-data fixtures."""
    root = tmp_path_factory.mktemp("lab")
    schedules = root / "data" / "raw" / "cbb" / "schedules"
    schedules.mkdir(parents=True)
    for season in (2025, 2026, 2027):
        (schedules / f"mbb_schedule_{season}.parquet").write_bytes(
            (FIXTURES / f"mbb_schedule_{season}.parquet").read_bytes()
        )
    return root


@pytest.fixture(scope="module")
def frames() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    team_games = pd.read_csv(FIXTURES / "cbb_team_games.csv", low_memory=False)
    player_games = pd.read_csv(FIXTURES / "cbb_player_games.csv", low_memory=False)
    schedule = pd.read_parquet(FIXTURES / "mbb_schedule_2026.parquet")
    return team_games, player_games, schedule


def _prices(schedule: pd.DataFrame, day: str) -> pd.DataFrame:
    games = schedule[schedule["game_date"].astype(str) == day]
    return pd.DataFrame(
        [{"event_id": f"e{g.id}", "game_id": int(g.id)} for g in games.itertuples()]
    )


def _priced(lab: Path, frames, day: str = DAY, *, player: bool = True) -> dict:
    team_games, player_games, schedule = frames
    history = PB.history_before(team_games, day)
    player_history = PB.history_before(player_games, day) if player else None
    return ratings.matchups_for(
        day=day,
        history=history,
        prices=_prices(schedule, day),
        raw_dir=lab / "data" / "raw",
        player_games=player_history,
    )


def test_every_priced_matchup_carries_the_layers_in_order_and_ends_at_its_price(lab, frames):
    out = _priced(lab, frames)
    priced = [m for m in out.values() if m.priceable]
    assert priced, "the fixture prices nothing on this day, so the layers are untested"
    for game in priced:
        keys = [layer["key"] for layer in game.layers]
        assert keys == [key for key, _ in CF.LAYERS], keys
        last = game.layers[-1]
        assert last["home"] == pytest.approx(game.home_points_per_possession * 100.0)
        assert last["away"] == pytest.approx(game.away_points_per_possession * 100.0)
        assert last["possessions"] == pytest.approx(game.possessions)
        assert all(layer["label"] for layer in game.layers)
        assert "day_summary" in game.context
        assert game.context["home_court"]["applied_by"] in ("the fit", "the card")


def test_a_refused_matchup_carries_no_layer(lab, frames):
    out = _priced(lab, frames)
    refused = [m for m in out.values() if not m.priceable]
    assert refused, "the thin fixture should refuse at least one pair on connectivity"
    for game in refused:
        assert game.layers == ()
        assert game.context == {}


def test_the_strength_layer_is_the_neutral_floor(lab, frames):
    """Strength minus the venue's two adds is what the fit says of the two
    teams on a neutral floor; home court puts the adds back."""
    out = _priced(lab, frames)
    for game in out.values():
        if not game.priceable:
            continue
        strength = game.layers[0]
        home_court = game.layers[1]
        tier = game.context["home_court"]["tier_margin"]
        departure = game.context["home_court"]["departure"]
        assert (home_court["home"] - home_court["away"]) - (strength["home"] - strength["away"]) == pytest.approx(
            tier + departure
        )
        if game.venue_state == "neutral":
            assert tier == 0.0 and departure == 0.0


def test_the_context_refuses_a_row_from_the_day_being_priced(frames):
    team_games, _, _ = frames
    leaked = team_games[team_games["slate_date"].astype(str) <= DAY]
    assert (leaked["slate_date"].astype(str) == DAY).any(), "the fixture holds the day"

    class _Ratings:
        offence: dict = {}
        defence: dict = {}
        tempo: dict = {}
        season = 2026
        venue_level_home_effect = False

        def tier_of(self, team):
            return "unplaced"

    with pytest.raises(CF.WalkForwardViolation):
        CF.build_context(
            day=DAY,
            ratings=_Ratings(),
            season_rows=leaked,
            history_rows=leaked,
            player_history=None,
            raw_dir=None,
            teams=set(),
        )


def test_form_is_shrunk_and_clamped():
    """Five games keep a quarter of the residual; a huge residual stops at the clamp."""

    class _Ratings:
        offence = {1: 0.0, 2: 0.0}
        defence = {1: 0.0, 2: 0.0}
        season = 2026
        venue_level_home_effect = False

        class venue:  # noqa: N801 - a stand-in for VenueEffects
            quasi_offence = 0.0
            quasi_defence = 0.0

            @staticmethod
            def home_offence(tier):
                return 0.0

            @staticmethod
            def home_defence(tier):
                return 0.0

            @staticmethod
            def departure_for(venue_id):
                return 0.0

        def tier_of(self, team):
            return "unplaced"

    def row(day, team, opp, own, allowed):
        return {
            "game_id": int(day.replace("-", "")), "slate_date": day, "team_id": team,
            "opponent_id": opp, "efficiency": own, "opponent_score": allowed,
            "game_possessions": 100.0, "venue_state": "neutral", "local_team_id": None,
            "venue_id": None, "season": 2026, "home_away": "home",
        }

    days = ["2026-01-%02d" % d for d in range(1, 6)]
    # Team 1 beats expectation by 4 per 100 in every game; team 2 by 400.
    rows = pd.DataFrame(
        [row(d, 1, 2, 104.0, 100.0) for d in days] + [row(d, 2, 1, 500.0, 100.0) for d in days]
    )
    form, games = CF.team_form(rows, _Ratings())
    assert games == {1: 5, 2: 5}
    assert form[1] == pytest.approx(4.0 * 5 / (5 + CF.FORM_SHRINKAGE_GAMES))
    assert form[2] == CF.FORM_CLAMP


def test_rest_buckets_and_days_since_the_last_game():
    assert CF.rest_bucket(None) is None
    assert CF.rest_bucket(0) is None
    assert CF.rest_bucket(1) == "second game in two days"
    assert CF.rest_bucket(2) == "one day off"
    assert CF.rest_bucket(4) == CF.REST_REFERENCE
    assert CF.rest_bucket(30) == "six or more days off"
    rows = pd.DataFrame(
        [{"team_id": 1, "slate_date": "2026-01-10"}, {"team_id": 1, "slate_date": "2026-01-12"},
         {"team_id": 2, "slate_date": "2025-12-01"}]
    )
    assert CF.days_since_last_game(rows, "2026-01-13") == {1: 1, 2: 43}
    assert CF.days_since_last_game(rows, "2026-01-13", teams={2}) == {2: 43}


def test_a_rotation_player_who_sat_the_last_game_is_treated_as_missing():
    team_rows = pd.DataFrame(
        [{"team_id": 7, "game_id": g, "slate_date": f"2026-01-{g:02d}"} for g in range(1, 9)]
    )
    players = []
    for g in range(1, 9):
        for name, minutes, points in (("Star", 30.0, 20.0), ("Glue", 25.0, 8.0), ("Bench", 5.0, 1.0)):
            sat = g == 8 and name == "Star"
            players.append({
                "game_id": g, "team_id": 7, "athlete_display_name": name,
                "did_not_play": sat, "minutes": None if sat else minutes,
                "points": None if sat else points, "season": 2026,
                "slate_date": f"2026-01-{g:02d}",
            })
    missing, factor = CF.missing_rotation(pd.DataFrame(players), team_rows, teams={7})
    assert [m["name"] for m in missing[7]] == ["Star"]
    share = (20.0 * 7) / (20.0 * 7 + 8.0 * 8 + 1.0 * 8)
    assert missing[7][0]["share"] == pytest.approx(share, abs=1e-3)
    assert factor[7] == pytest.approx(max(CF.AVAILABILITY_FLOOR, 1 - CF.AVAILABILITY_SHARE * share))
    # Nobody missing when everybody played the last game.
    for p in players:
        if p["did_not_play"]:
            p.update(did_not_play=False, minutes=30.0, points=20.0)
    missing, factor = CF.missing_rotation(pd.DataFrame(players), team_rows, teams={7})
    assert missing == {} and factor == {}


def _second_opinion(path: Path, *, as_of: str, teams: int, season: int = 2026) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [
        {"as_of": as_of, "season": season, "source": "fixture", "team": f"T{i}", "team_id": i,
         "adj_off": 100.0 + (i % 7), "adj_def": 100.0 - (i % 5), "adj_tempo": 67.0 + (i % 3)}
        for i in range(1, teams + 1)
    ]
    pd.DataFrame(rows).to_csv(path, index=False)


def test_the_second_opinion_is_read_only_when_dated_for_the_day(tmp_path):
    raw = tmp_path / "raw"
    path = CF.second_opinion_path(raw, 2026)
    absent, why = CF.load_second_opinion(raw, season=2026, day="2026-01-10")
    assert absent is None and "no second opinion" in why

    _second_opinion(path, as_of="2026-01-11", teams=320)
    after, why = CF.load_second_opinion(raw, season=2026, day="2026-01-10")
    assert after is None and "after" in why, why

    _second_opinion(path, as_of="2026-01-01", teams=320)
    stale, why = CF.load_second_opinion(raw, season=2026, day="2026-01-10")
    assert stale is None and "more than" in why, why

    _second_opinion(path, as_of="2026-01-09", teams=120)
    thin, why = CF.load_second_opinion(raw, season=2026, day="2026-01-10")
    assert thin is None and "under the" in why, why

    _second_opinion(path, as_of="2026-01-09", teams=320)
    read, why = CF.load_second_opinion(raw, season=2026, day="2026-01-10")
    assert read is not None and why == "" and len(read) == 320
    # Deviations from the table's own mean, so they add to zero.
    assert sum(v[0] for v in read.teams.values()) == pytest.approx(0.0, abs=1e-6)


def test_the_second_opinion_moves_the_price_at_the_blend_weight(lab, frames):
    team_games, _, schedule = frames
    before = _priced(lab, frames, player=False)
    priced = {k: m for k, m in before.items() if m.priceable}
    assert priced
    # A table that puts every team one point better on offence than the
    # ratings' mean, except the home side of the first priced game, which it
    # puts ten points better than that.
    first = next(iter(priced.values()))
    rows = []
    teams = {int(t) for m in before.values() for t in (m.home_team_id, m.away_team_id)}
    for i, team in enumerate(sorted(teams) + list(range(900000, 900000 + 320))):
        rows.append({
            "as_of": DAY, "season": 2026, "source": "fixture", "team": f"T{team}", "team_id": team,
            "adj_off": 110.0 if team == int(first.home_team_id) else 100.0,
            "adj_def": 100.0, "adj_tempo": 67.0,
        })
    path = CF.second_opinion_path(lab / "data" / "raw", 2026)
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False)
    try:
        after = _priced(lab, frames, player=False)
    finally:
        path.unlink()
    changed = after[first.event_id]
    assert changed.context["second_opinion"]["blended"] is True
    assert changed.layers[-1]["home"] != pytest.approx(changed.layers[-2]["home"])
    # Only the last layer moved: everything before the blend is as it was.
    for mine, theirs in zip(before[first.event_id].layers[:-1], changed.layers[:-1]):
        assert mine["home"] == pytest.approx(theirs["home"])
        assert mine["away"] == pytest.approx(theirs["away"])
    # The home side's offence moves BLEND_WEIGHT of the way from the ratings'
    # own deviation to the table's: ten above the table's mean for the home
    # side, and the away side's defence toward the table's zero.
    n = len(rows)
    table_mean = (110.0 + 100.0 * (n - 1)) / n
    # The blend adds weight * (table - own) to each side: the home side's
    # offence deviation (ten above the table's mean) and the away side's
    # defence deviation (zero: every defence in the table is the mean).
    own = changed.context["second_opinion"]["own"]
    moved = changed.layers[-1]["home"] - changed.layers[-2]["home"]
    assert moved == pytest.approx(
        CF.BLEND_WEIGHT * ((110.0 - table_mean) - own["home_offence"])
        + CF.BLEND_WEIGHT * (0.0 - own["away_defence"]),
        abs=1e-6,
    )
    assert after[first.event_id].expected_margin > before[first.event_id].expected_margin


def test_the_context_summary_names_what_it_carried():
    context = CF.DayContext(day="2026-01-10", form={1: 0.5}, rest_days={1: 2, 2: None},
                            missing={1: [{"name": "A"}]}, notes=["no second opinion on disk"])
    line = CF.summary(context)
    assert "form on 1 team(s)" in line and "rest on 1" in line
    assert "1 rotation player(s)" in line and "no second opinion" in line
