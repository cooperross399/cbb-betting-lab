"""KenPom's projected scores (decision 96): read, resolved, and a candidate layer."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab.data import kenpom
from cbb_betting_lab.models import card_factors as CF

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "real_data"
DAY = "2026-03-12"


@pytest.fixture(scope="module")
def schedule() -> pd.DataFrame:
    return pd.read_parquet(FIXTURES / "mbb_schedule_2026.parquet")


def _payload(games: pd.DataFrame, *, flip: bool = False) -> bytes:
    rows = []
    for g in games.itertuples(index=False):
        home, away = g.home_location, g.away_location
        if flip:
            home, away = away, home
        rows.append({"Season": 2026, "GameID": int(g.id), "DateOfGame": DAY, "Home": home,
                     "Visitor": away, "HomePred": 75.0, "VisitorPred": 68.0, "HomeWP": 74,
                     "PredTempo": 68.5, "ThrillScore": 50.1})
    return json.dumps(rows).encode()


def test_fanmatch_is_read_by_field_name_and_bad_rows_are_dropped():
    payload = json.dumps({"data": [
        {"home": "Duke", "visitor": "UNC", "homepred": "80.1", "visitorpred": "71.0", "HomeWP": 81, "PredTempo": 70},
        {"Home": "A", "Visitor": "B", "HomePred": 900, "VisitorPred": 60},
        {"Home": "", "Visitor": "B", "HomePred": 70, "VisitorPred": 60},
    ]}).encode()
    frame = kenpom.parse_fanmatch(payload, day=DAY)
    assert list(frame["home"]) == ["Duke"]
    assert frame.loc[0, "home_wp"] == pytest.approx(0.81)
    assert "HomeWP" in kenpom.field_names(payload) and "80.1" not in kenpom.field_names(payload)


def test_an_off_day_is_an_empty_table_not_an_error():
    assert kenpom.parse_fanmatch(b"[]", day=DAY).empty


def test_the_layer_is_a_candidate_and_off_on_the_declared_card():
    assert "kenpom" in dict(CF.CANDIDATE_LAYERS)
    assert CF.default_switches()["kenpom"] is False


def test_only_the_day_being_priced_is_read(tmp_path, schedule):
    games = schedule[schedule["game_date"].astype(str) == DAY]
    table, _ = kenpom.resolve(kenpom.parse_fanmatch(_payload(games), day=DAY), schedule)
    kenpom.write_fanmatch(table, raw_dir=tmp_path, day=DAY)
    assert CF.load_kenpom(tmp_path, day=DAY)[0]
    earlier = (pd.Timestamp(DAY) - pd.Timedelta(days=1)).date().isoformat()
    projected, reason = CF.load_kenpom(tmp_path, day=earlier)
    assert projected == {} and "no KenPom projection" in reason


def test_a_game_filed_the_other_way_round_is_turned_over(tmp_path, schedule):
    games = schedule[schedule["game_date"].astype(str) == DAY]
    table, _ = kenpom.resolve(kenpom.parse_fanmatch(_payload(games, flip=True), day=DAY), schedule)
    assert table["home_id"].notna().sum() > 0
    kenpom.write_fanmatch(table, raw_dir=tmp_path, day=DAY)
    context = CF.DayContext(day=DAY)
    context.kenpom, _ = CF.load_kenpom(tmp_path, day=DAY)
    turned = [CF.kenpom_for(context, g.home_id, g.away_id) for g in games.itertuples(index=False)]
    turned = [t for t in turned if t is not None]
    assert turned
    for got in turned:
        assert got[0] == 68.0 and got[1] == 75.0 and got[2] == pytest.approx(0.26)


def test_switched_on_the_layer_moves_the_margin_and_total_halfway_to_kenpom(tmp_path, schedule):
    from cbb_betting_lab.models import ratings
    from cbb_betting_lab.reports import price_backtest as PB

    raw = tmp_path / "data" / "raw"
    schedules = raw / "cbb" / "schedules"
    schedules.mkdir(parents=True)
    for season in (2025, 2026, 2027):
        (schedules / f"mbb_schedule_{season}.parquet").write_bytes(
            (FIXTURES / f"mbb_schedule_{season}.parquet").read_bytes())
    games = schedule[schedule["game_date"].astype(str) == DAY]
    table, _ = kenpom.resolve(kenpom.parse_fanmatch(_payload(games), day=DAY), schedule)
    kenpom.write_fanmatch(table, raw_dir=raw, day=DAY)
    audit = CF.layer_audit_path(raw)
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(json.dumps({"as_of": DAY, "switches": {"kenpom": True}}), encoding="utf-8")

    team_games = pd.read_csv(FIXTURES / "cbb_team_games.csv", low_memory=False)
    prices = pd.DataFrame([{"event_id": f"e{g.id}", "game_id": int(g.id)} for g in games.itertuples()])
    out = ratings.matchups_for(day=DAY, history=PB.history_before(team_games, DAY), prices=prices,
                               raw_dir=raw, player_games=None)
    moved = [m for m in out.values() if m.priceable and m.context["kenpom"]["margin"] is not None]
    assert moved, "no priced game carried KenPom's projection"
    for game in moved:
        keys = [layer["key"] for layer in game.layers]
        after = game.layers[keys.index("kenpom")]
        before = game.layers[keys.index("kenpom") - 1]
        poss = after["possessions"]
        margin_before = (before["home"] - before["away"]) * poss / 100.0
        margin_after = (after["home"] - after["away"]) * poss / 100.0
        total_before = (before["home"] + before["away"]) * poss / 100.0
        total_after = (after["home"] + after["away"]) * poss / 100.0
        assert margin_after == pytest.approx(margin_before + CF.KENPOM_BLEND_WEIGHT * (7.0 - margin_before))
        assert total_after == pytest.approx(total_before + CF.KENPOM_BLEND_WEIGHT * (143.0 - total_before))


def test_every_known_spelling_names_the_school_espn_files_under_that_id():
    from cbb_betting_lab.data import second_opinion

    sched = pd.read_parquet(FIXTURES / "mbb_schedule_2027.parquet")
    names = {}
    for side in ("home", "away"):
        for tid, loc in zip(sched[f"{side}_id"], sched[f"{side}_location"]):
            names[int(tid)] = str(loc)
    expected = {
        "Albany": "UAlbany", "Appalachian St.": "App State", "Boston College": "Boston College",
        "Boston University": "Boston University", "Cal Baptist": "California Baptist",
        "Cornell": "Cornell", "Grambling St.": "Grambling", "Hawaii": "Hawai'i",
        "Illinois Chicago": "UIC", "Louisiana Monroe": "UL Monroe", "Sam Houston St.": "Sam Houston",
        "Seattle": "Seattle U", "Southeast Missouri": "Southeast Missouri State",
        "Southeastern Louisiana": "SE Louisiana", "Tennessee Martin": "UT Martin",
        "Texas A&M Corpus Chris": "Texas A&M-Corpus Christi", "USC Upstate": "South Carolina Upstate",
    }
    assert set(expected) == set(second_opinion.KNOWN_IDS)
    for spelling, tid in second_opinion.KNOWN_IDS.items():
        assert names.get(tid) == expected[spelling], (spelling, tid, names.get(tid))


def test_a_day_recorded_empty_is_read_as_no_projection_not_an_error(tmp_path):
    kenpom.write_fanmatch(kenpom.parse_fanmatch(b"[]", day=DAY), raw_dir=tmp_path, day=DAY)
    assert kenpom.fanmatch_path(tmp_path, DAY).is_file()
    projected, reason = CF.load_kenpom(tmp_path, day=DAY)
    assert projected == {} and "resolves no game" in reason
