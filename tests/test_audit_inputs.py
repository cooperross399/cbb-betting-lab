"""Decision 110: dated second-opinion copies, pace form's size, per-tier bias history."""

from __future__ import annotations

import pandas as pd
import pytest

from cbb_betting_lab.models import card_factors as CF
from cbb_betting_lab.reports import nightly_learning as NL

DAY = "2026-11-18"


def _table(path, *, as_of, source, teams=CF.SECOND_OPINION_MIN_TEAMS + 5, shift=0.0):
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame([
        {"as_of": as_of, "season": 2027, "source": source, "team": f"T{i}", "team_id": i,
         "adj_off": 100.0 + (i % 7) + shift, "adj_def": 100.0 - (i % 5), "adj_tempo": 67.0 + (i % 3)}
        for i in range(1, teams + 1)
    ]).to_csv(path, index=False)


def test_a_past_day_reads_the_dated_copy_from_the_day_before(tmp_path):
    _table(CF.second_opinion_path(tmp_path, 2027), as_of="2026-11-19", source="espn_bpi")
    assert CF.load_second_opinion(tmp_path, season=2027, day=DAY)[0] is None
    _table(CF.second_opinion_history_path(tmp_path, "2026-11-17", "kenpom"), as_of="2026-11-17", source="kenpom")
    opinion, _ = CF.load_second_opinion(tmp_path, season=2027, day=DAY)
    assert opinion is not None and opinion.source == "kenpom" and opinion.as_of == "2026-11-17"


def test_a_copy_dated_the_day_itself_or_too_old_is_never_read(tmp_path):
    _table(CF.second_opinion_history_path(tmp_path, DAY, "kenpom"), as_of=DAY, source="kenpom")
    _table(CF.second_opinion_history_path(tmp_path, "2026-11-10", "kenpom"), as_of="2026-11-10", source="kenpom")
    assert CF.history_paths(tmp_path, day=DAY) == []
    assert CF.load_second_opinion(tmp_path, season=2027, day=DAY)[0] is None


def test_a_source_with_a_current_table_is_not_counted_twice(tmp_path):
    _table(CF.second_opinion_path(tmp_path, 2027, source="kenpom"), as_of=DAY, source="kenpom")
    _table(CF.second_opinion_history_path(tmp_path, "2026-11-17", "kenpom"), as_of="2026-11-17",
           source="kenpom", shift=5.0)
    opinion, _ = CF.load_second_opinion(tmp_path, season=2027, day=DAY)
    assert opinion is not None and opinion.as_of == DAY and opinion.source == "kenpom"


def test_pace_form_carries_the_audits_measured_weight():
    # A full last five keeps 5 / (5 + shrinkage): twice the old 5 / 20.
    assert 5 / (5 + CF.PACE_FORM_SHRINKAGE_GAMES) == pytest.approx(2 * 5 / (5 + 15))
    assert CF.default_switches()["pace_form"] is False


def test_the_nightly_history_carries_each_tier():
    for tier in NL.TIERS:
        assert f"{tier}_total_bias" in NL.HISTORY_COLUMNS
    record = {"day": DAY, "as_of": "2026-11-19", "accuracy": {"games": 3, "total_bias": 1.0},
              "by_tier": {"mid_major": {"games": 3, "margin_bias": -2.5, "total_bias": 7.04}},
              "ratings": {}}
    row = NL.history_row(record)
    assert row["mid_major_total_bias"] == "7.04" and row["mid_major_games"] == "3"
    assert row["high_major_games"] == "0" and row["high_major_total_bias"] == ""
