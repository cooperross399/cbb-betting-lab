"""The model learns from each night of basketball (decision 78).

Two halves. The defect: a finished game whose play-by-play hoopR had not
published yet had no `periods`, and `ratings.prepare` drops such a row, so on
2026-11-03 the ratings refitted on 3 of a 182-game opening Monday. The
schedule's own line scores now fill the gap. And the receipt: the nightly
learning report grades a night's projections and keeps one row per night.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.data import build_datasets as BD
from cbb_betting_lab.reports import nightly_learning as NL


LINES_HOME = "[{'value': 47.0, 'displayValue': '47', 'period': 1.0}\n {'value': 27.0, 'displayValue': '27', 'period': 2.0}]"
LINES_AWAY = "[{'value': 39.0, 'displayValue': '39', 'period': 1.0}\n {'value': 34.0, 'displayValue': '34', 'period': 2.0}]"
LINES_OT = "[{'value': 30.0}\n {'value': 35.0}\n {'value': 9.0}]"


def test_line_scores_parse_from_hoopr_text_and_from_a_list():
    assert BD._linescore_values(LINES_HOME) == [47.0, 27.0]
    assert BD._linescore_values([{"value": 1.0}, {"value": 2.0}]) == [1.0, 2.0]
    assert BD._linescore_values(None) == []
    assert BD._linescore_values(float("nan")) == []


def test_a_finished_game_without_play_by_play_still_gets_its_periods(monkeypatch):
    schedule = pd.DataFrame([
        {"game_id": 1, "home_linescores": LINES_HOME, "away_linescores": LINES_AWAY, "status_type_completed": True},
        {"game_id": 2, "home_linescores": LINES_OT, "away_linescores": LINES_OT, "status_type_completed": True},
        {"game_id": 3, "home_linescores": "[]", "away_linescores": "[]", "status_type_completed": False},
        {"game_id": 4, "home_linescores": LINES_HOME, "away_linescores": LINES_AWAY, "status_type_completed": True},
    ])
    pbp_segments = pd.DataFrame([{"game_id": 4, "periods": 2, "overtime": False,
                                  "home_score_h1": 47.0, "away_score_h1": 39.0}])

    def load(kind, season, raw_dir=None, columns=None):
        assert kind == "schedules"
        return schedule

    monkeypatch.setattr(BD.hoopr, "load", load)
    monkeypatch.setattr(BD, "build_game_segments", lambda season, raw_dir=None: pbp_segments)
    monkeypatch.setattr(BD.espn_box, "load", lambda kind, season, raw_dir=None: pd.DataFrame())

    out = BD.game_segments_with_supplement(2027).set_index("game_id")
    assert sorted(out.index) == [1, 2, 4], "an unfinished game is not a segment, and play-by-play wins where it exists"
    assert out.loc[1, "periods"] == 2 and not out.loc[1, "overtime"]
    assert (out.loc[1, "home_score_h1"], out.loc[1, "away_score_h1"]) == (47.0, 39.0)
    assert out.loc[2, "periods"] == 3 and out.loc[2, "overtime"]


@dataclass
class _Game:
    home_team_id: int
    away_team_id: int
    expected_margin: float
    expected_total: float
    home_tier: str = "mid_major"
    away_tier: str = "mid_major"
    priceable: bool = True
    identified_by: str = ""


@dataclass
class _Fit:
    offence: dict
    defence: dict
    priced_through: str = ""
    games: int = 0

    def tier_of(self, team):
        return "mid_major"

    def prior_weight_distribution(self, q):
        return {"offence": {0.5: 0.9}, "defence": {0.5: 0.8}, "tempo": {0.5: 0.7}}


def test_a_night_is_graded_per_tier_and_the_ratings_moves_are_reported(tmp_path):
    matchups = {
        "10": _Game(1, 2, expected_margin=5.0, expected_total=140.0),
        "11": _Game(3, 4, expected_margin=-2.0, expected_total=150.0, home_tier="low_major"),
        "12": _Game(5, 6, expected_margin=1.0, expected_total=130.0, priceable=False),
        "13": _Game(7, 8, expected_margin=1.0, expected_total=130.0),  # no final yet
    }
    results = {10: {1: 80.0, 2: 70.0}, 11: {3: 70.0, 4: 80.0}, 12: {5: 1.0, 6: 2.0}}
    graded = NL.grade(matchups, results, {1: "Home A"})
    assert [g.game_id for g in graded] == [10, 11]
    assert graded[0].home == "Home A" and graded[0].margin_error == 5.0
    assert graded[1].tier == "low_major", "a cross-tier game is the lower tier's"

    before = _Fit({1: 1.0, 2: 0.0}, {1: 0.0, 2: 0.0}, "2026-11-01", 2)
    after = _Fit({1: 3.0, 2: -1.0}, {1: 0.0, 2: 0.0}, "2026-11-02", 4)
    moves = NL.rating_moves(before, after, {}, played={1, 2})
    assert [(m["team_id"], m["change"]) for m in moves] == [(2, -1.0), (1, 2.0)]

    record = NL.build_record(day="2026-11-02", as_of="2026-11-03", graded=graded, moves=moves,
                             before=before, after=after)
    assert record["accuracy"]["games"] == 2
    assert record["accuracy"]["winner_pct"] == 1.0
    assert set(record["by_tier"]) == {"mid_major", "low_major"}, "per tier, never only a pooled row"

    history = tmp_path / "history.csv"
    NL.update_history(history, record)
    rows = NL.update_history(history, record)
    assert len(rows) == 1, "a re-run of the same night replaces its row"
    text = NL.render(record, rows)
    assert "What the model learned from 2026-11-02" in text
    assert "not whether any bet had an edge" in text
    json_path, md_path = NL.save(record, text, tmp_path, CBB)
    assert json_path.name == "cbb_nightly_learning.json" and md_path.read_text() == text


def test_an_empty_night_says_so_and_writes_no_history_row(tmp_path):
    record = NL.build_record(day="2026-11-02", as_of="2026-11-03", graded=[], moves=[],
                             before=None, after=None, notes=["nothing finished"])
    assert NL.update_history(tmp_path / "h.csv", record) == []
    assert "could be graded" in NL.render(record)
