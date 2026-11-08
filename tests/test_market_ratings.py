"""Ratings read off the betting lines (decision 84): a candidate layer."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from cbb_betting_lab.models import card_factors as CF
from cbb_betting_lab.models import market_ratings as MR
from cbb_betting_lab.population import division_one_team_ids

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "real_data"


@pytest.fixture(scope="module")
def schedule() -> pd.DataFrame:
    return pd.read_parquet(FIXTURES / "mbb_schedule_2026.parquet")


def _store(schedule: pd.DataFrame, *, strength: dict, home_edge: float, pace: dict, mean_total: float,
           flip_neutral: bool = True) -> pd.DataFrame:
    """A capture store whose closing consensus is exactly what `strength`,
    `home_edge` and `pace` say, the provider naming each game by display name
    and putting the AWAY side first on a neutral floor when `flip_neutral`."""
    rows = []
    for g in schedule.itertuples(index=False):
        h, a = int(g.home_id), int(g.away_id)
        if h not in strength or a not in strength:
            continue
        neutral = bool(g.neutral_site)
        margin = strength[h] - strength[a] + (0.0 if neutral else home_edge)
        total = mean_total + pace[h] + pace[a]
        home_name, away_name = g.home_display_name, g.away_display_name
        if neutral and flip_neutral:
            home_name, away_name, margin = away_name, home_name, -margin
        day = str(g.game_date)[:10]
        common = {"captured_at": f"{day}T12:00:00Z", "slate_date": day, "event_id": f"e{g.id}",
                  "commence_time": f"{day}T23:00:00Z", "home_team": home_name, "away_team": away_name,
                  "segment": "game", "player": "", "book": "b", "american_odds": -110}
        rows.append({**common, "market": "spread", "selection": "home", "line": -margin})
        rows.append({**common, "market": "spread", "selection": "away", "line": margin})
        rows.append({**common, "market": "total_points", "selection": "over", "line": total})
        rows.append({**common, "market": "total_points", "selection": "under", "line": total})
    return pd.DataFrame(rows)


def test_the_fit_recovers_the_lines_it_was_handed(schedule):
    d1 = division_one_team_ids(schedule)
    rng = np.random.default_rng(7)
    teams = sorted(d1)
    strength = {t: float(rng.normal(0, 8)) for t in teams}
    pace = {t: float(rng.normal(0, 4)) for t in teams}
    store = _store(schedule, strength=strength, home_edge=3.0, pace=pace, mean_total=145.0)
    day = "2026-03-01"
    games = MR.lined_games(store, schedule, day=day)
    assert len(games) > MR.MIN_EVENTS
    assert (games["event_id"].map(lambda e: store.loc[store.event_id == e, "slate_date"].iloc[0]) < day).all()
    fitted = MR.fit(games, as_of=day)
    assert fitted.has_margin and fitted.has_total
    assert fitted.home_edge == pytest.approx(3.0, abs=0.5)
    ids = [t for t in fitted.teams]
    truth = np.array([strength[t] for t in ids])
    got = np.array([fitted.teams[t][0] for t in ids])
    assert np.corrcoef(truth, got)[0, 1] > 0.95
    truth_pace = np.array([pace[t] for t in ids])
    got_pace = np.array([fitted.teams[t][1] for t in ids])
    assert np.corrcoef(truth_pace, got_pace)[0, 1] > 0.9


def test_nothing_from_the_day_being_priced_or_after_is_read(schedule):
    d1 = division_one_team_ids(schedule)
    store = _store(schedule, strength={t: 0.0 for t in d1}, home_edge=3.0, pace={t: 0.0 for t in d1},
                   mean_total=140.0)
    first = str(store["slate_date"].min())
    assert MR.lined_games(store, schedule, day=first).empty


def test_too_few_games_is_no_rating_and_the_layer_moves_nothing():
    empty = MR.fit(pd.DataFrame(columns=["event_id", "home_id", "away_id", "neutral", "margin", "total"]),
                   as_of="2026-11-08")
    assert not len(empty) and empty.margin(1, 2, neutral=False) is None and empty.total(1, 2) is None


def test_the_layer_is_a_candidate_and_off_on_the_declared_card():
    assert "market_ratings" in dict(CF.CANDIDATE_LAYERS)
    assert CF.default_switches()["market_ratings"] is False


def test_switched_on_the_layer_moves_the_margin_halfway_to_the_market_view(tmp_path, schedule):
    """Through the one pricing seam: a store on disk under the lab's processed
    directory, an audit that adds the layer, and the price moves
    `MARKET_BLEND_WEIGHT` of the way from where it stood to the market view."""
    import json

    from cbb_betting_lab import line_movement
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.models import ratings
    from cbb_betting_lab.reports import price_backtest as PB

    raw = tmp_path / "data" / "raw"
    schedules = raw / "cbb" / "schedules"
    schedules.mkdir(parents=True)
    for season in (2025, 2026, 2027):
        (schedules / f"mbb_schedule_{season}.parquet").write_bytes(
            (FIXTURES / f"mbb_schedule_{season}.parquet").read_bytes())
    d1 = division_one_team_ids(schedule)
    strength = {t: (t % 17) - 8.0 for t in d1}
    store = _store(schedule, strength=strength, home_edge=3.0, pace={t: 0.0 for t in d1}, mean_total=150.0)
    path = line_movement.store_path(CBB, tmp_path / "data" / "processed")
    path.parent.mkdir(parents=True)
    store.to_csv(path, index=False)
    day = "2026-03-12"
    audit = CF.layer_audit_path(raw)
    audit.parent.mkdir(parents=True, exist_ok=True)
    audit.write_text(json.dumps({"as_of": day, "switches": {"market_ratings": True}}), encoding="utf-8")

    team_games = pd.read_csv(FIXTURES / "cbb_team_games.csv", low_memory=False)
    games = schedule[schedule["game_date"].astype(str) == day]
    prices = pd.DataFrame([{"event_id": f"e{g.id}", "game_id": int(g.id)} for g in games.itertuples()])
    out = ratings.matchups_for(day=day, history=PB.history_before(team_games, day), prices=prices,
                               raw_dir=raw, player_games=None)
    moved = [m for m in out.values() if m.priceable and m.context["market_ratings"]["margin"] is not None]
    assert moved, "no priced game had both teams rated by the lines"
    for game in moved:
        layers = {layer["key"]: layer for layer in game.layers}
        after = layers["market_ratings"]
        before = game.layers[list(layers).index("market_ratings") - 1]
        poss = after["possessions"]
        margin_before = (before["home"] - before["away"]) * poss / 100.0
        margin_after = (after["home"] - after["away"]) * poss / 100.0
        target = game.context["market_ratings"]["margin"]
        assert margin_after == pytest.approx(margin_before + CF.MARKET_BLEND_WEIGHT * (target - margin_before))
