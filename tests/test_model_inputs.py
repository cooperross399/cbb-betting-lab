"""Decision 92: the consensus second opinion, KenPom, the NET, the hand-drop
folder, the four-factor mismatch, WAB and close-game luck."""

from __future__ import annotations

import json
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from cbb_betting_lab.data import second_opinion as SO
from cbb_betting_lab.models import card_factors as CF
from cbb_betting_lab.models import four_factors as FF


def _table(path, *, as_of, source, off_shift=0.0, teams=320, tempo=True):
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [{"as_of": as_of, "season": 2027, "source": source, "team": f"T{i}", "team_id": i,
             "adj_off": 100.0 + (i % 7) + (off_shift if i == 1 else 0.0), "adj_def": 100.0 - (i % 5),
             "adj_tempo": (67.0 + (i % 3)) if tempo else np.nan}
            for i in range(1, teams + 1)]
    pd.DataFrame(rows).to_csv(path, index=False)


def test_one_table_reads_as_it_always_did(tmp_path):
    _table(CF.second_opinion_path(tmp_path, 2027), as_of="2026-11-09", source="espn_bpi")
    read, why = CF.load_second_opinion(tmp_path, season=2027, day="2026-11-09")
    assert why == "" and read.source == "espn_bpi" and len(read) == 320


def test_several_tables_blend_into_their_consensus(tmp_path):
    _table(CF.second_opinion_path(tmp_path, 2027), as_of="2026-11-09", source="espn_bpi", tempo=False)
    _table(CF.second_opinion_path(tmp_path, 2027, source="kenpom"), as_of="2026-11-09",
           source="kenpom", off_shift=6.0)
    alone, _ = CF._load_one_opinion(CF.second_opinion_path(tmp_path, 2027), day="2026-11-09")
    read, why = CF.load_second_opinion(tmp_path, season=2027, day="2026-11-09")
    assert why == "" and read.source == "espn_bpi+kenpom"
    # Team 1's offence is +6 in one table: the consensus moves it about half that.
    assert read.teams[1][0] - alone.teams[1][0] == pytest.approx(3.0, abs=0.1)
    # Tempo comes from the table that has one.
    assert np.isfinite(read.teams[1][2])


def test_a_stale_extra_table_is_left_out_not_averaged_in(tmp_path):
    _table(CF.second_opinion_path(tmp_path, 2027), as_of="2026-11-09", source="espn_bpi")
    _table(CF.second_opinion_path(tmp_path, 2027, source="trank"), as_of="2026-11-01",
           source="trank", off_shift=50.0)
    read, _ = CF.load_second_opinion(tmp_path, season=2027, day="2026-11-09")
    assert read.source == "espn_bpi"


def test_kenpom_is_read_by_field_name_and_the_key_is_never_in_an_error(monkeypatch):
    payload = json.dumps([{"TeamName": "Duke", "AdjOE": 125.1, "AdjDE": 90.2, "AdjTempo": 70.1},
                          {"TeamName": "Bad", "AdjOE": 5.0, "AdjDE": 90.0, "AdjTempo": 70.0}]).encode()
    frame = SO.parse_kenpom(payload)
    assert list(frame["team"]) == ["Duke"] and frame.iloc[0]["adj_tempo"] == pytest.approx(70.1)
    seen = {}

    def fake_get(url, *, headers=None, timeout=60.0):
        seen["headers"] = headers
        raise SO.SecondOpinionError(f"{url.split('?')[0]}: HTTP 401")

    monkeypatch.setattr(SO, "_get", fake_get)
    with pytest.raises(SO.SecondOpinionError) as caught:
        SO.fetch_kenpom("sekrit-value", 2027)
    assert "sekrit-value" not in str(caught.value)
    assert seen["headers"]["Authorization"].endswith("sekrit-value")
    with pytest.raises(SO.SecondOpinionError):
        SO.fetch_kenpom("", 2027)


def test_the_net_is_read_off_its_table_and_placed_by_rank():
    rows = "".join(f"<tr><td>{i}</td><td>School {i}</td><td>10-1</td></tr>" for i in range(1, 331))
    net = SO.parse_net(f"<table><tr><th>Rank</th><th>School</th></tr>{rows}</table>".encode())
    assert len(net) == 330 and net.iloc[0]["team"] == "School 1"
    placed = SO.net_to_ratings(net)
    spread = placed["adj_off"] - placed["adj_def"]
    assert spread.is_monotonic_decreasing and spread.iloc[0] > 0 > spread.iloc[-1]
    assert placed["adj_tempo"].isna().all()


def test_a_page_without_enough_ranked_schools_is_refused():
    with pytest.raises(SO.SecondOpinionError):
        SO.parse_net(b"<table><tr><td>1</td><td>Duke</td></tr></table>")


def test_robots_that_cannot_be_read_is_not_permission(monkeypatch):
    def boom(*a, **k):
        raise OSError("no network")

    monkeypatch.setattr(SO.urllib.request, "urlopen", boom)
    allowed, why = SO.allowed_by_robots("https://example.org/x")
    assert not allowed and "not fetched" in why


def test_robots_closed_to_this_agent_is_a_no(monkeypatch):
    class Answer:
        def __init__(self, body):
            self.body = body

        def read(self):
            return self.body

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(SO.urllib.request, "urlopen",
                        lambda *a, **k: Answer(b"User-agent: ClaudeBot\nDisallow: /\n"))
    allowed, why = SO.allowed_by_robots("https://example.org/x")
    assert not allowed and "ClaudeBot" in why
    monkeypatch.setattr(SO.urllib.request, "urlopen", lambda *a, **k: Answer(b"User-agent: *\nAllow: /\n"))
    assert SO.allowed_by_robots("https://example.org/x")[0]


def test_the_newest_drop_on_or_before_the_day_is_read(tmp_path):
    drop = tmp_path / SO.DROP_DIR
    drop.mkdir(parents=True)
    for name in ("trank_2026-11-07.csv", "trank_2026-11-08.csv", "trank_2026-11-10.csv", "notes.txt"):
        (drop / name).write_text("x")
    found = SO.drops("2026-11-09", root=tmp_path)
    assert list(found) == ["trank"] and found["trank"].name == "trank_2026-11-08.csv"


def _games(n_teams=12, games_each=8, seed=3):
    rng = np.random.default_rng(seed)
    rows = []
    gid = 0
    for _ in range(games_each):
        order = rng.permutation(n_teams)
        for a, b in zip(order[::2], order[1::2]):
            gid += 1
            for team, opp in ((a, b), (b, a)):
                fga = 60
                rows.append({"game_id": gid, "team_id": int(team), "opponent_id": int(opp),
                             "field_goals_made": int(20 + team), "field_goals_attempted": fga,
                             "three_point_field_goals_made": 7, "free_throws_made": int(10 + team % 4),
                             "turnovers": int(12 - team % 3), "offensive_rebounds": int(6 + team),
                             "defensive_rebounds": 24, "team_score": int(65 + 2 * team + rng.integers(0, 6)),
                             "opponent_score": int(65 + 2 * opp + rng.integers(0, 6)),
                             "game_possessions": 68.0, "home_away": "home" if team == a else "away"})
    return pd.DataFrame(rows)


def test_two_average_teams_have_no_mismatch_and_extremes_do():
    table = FF.FactorTable(FF.game_factors(_games()))
    assert len(table) == 12 and set(table.weights) == set(FF.FACTORS)
    # Shrunk toward the league, each side's style is a fraction of its raw one.
    moves = [abs(table.mismatch(a, b) or 0.0) for a in range(12) for b in range(12) if a != b]
    assert max(moves) <= FF.CLAMP
    assert max(moves) > 0.0


def test_too_few_games_is_no_mismatch():
    table = FF.FactorTable(FF.game_factors(_games(games_each=3)))
    assert table.mismatch(0, 1) is None


def test_wab_and_luck_read_the_days_ratings():
    rows = _games(n_teams=60, games_each=8)
    nets = {t: 0.5 * (t - 30) for t in range(60)}
    ratings = SimpleNamespace(offence={t: v / 2 for t, v in nets.items()},
                              defence={t: -v / 2 for t, v in nets.items()},
                              expected_tempo=lambda a, b: 68.0)
    wab, luck = FF.resume(rows, ratings)
    assert len(wab) == 60
    # The strongest teams beat a bubble team's expectation; the weakest do not.
    assert wab[59] > wab[0]
    assert all(abs(v) <= FF.LUCK_CLAMP for v in luck.values())


def test_the_new_layers_are_candidates_off_by_default():
    switches = CF.default_switches()
    assert switches["four_factors"] is False and switches["close_game_luck"] is False
