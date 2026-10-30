"""The layer audit: the card switches its own layers on and off by results.

`models/layer_audit.py` judges each layer in `card_factors` on whether it
moved the predicted margin and total toward the final score, and
`card_factors.load_layer_audit` reads its verdict for the next card. These
tests pin the rule, the walk-forward refusal, and that a layer switched off
still appears on the page, unmoved, with its move kept in the shadow.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from cbb_betting_lab.models import card_factors as CF
from cbb_betting_lab.models import layer_audit as LA
from cbb_betting_lab.models import ratings
from cbb_betting_lab.reports import price_backtest as PB

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "real_data"
DAY = "2026-03-12"


@pytest.fixture()
def lab(tmp_path) -> Path:
    schedules = tmp_path / "data" / "raw" / "cbb" / "schedules"
    schedules.mkdir(parents=True)
    for season in (2025, 2026, 2027):
        (schedules / f"mbb_schedule_{season}.parquet").write_bytes(
            (FIXTURES / f"mbb_schedule_{season}.parquet").read_bytes()
        )
    return tmp_path


@pytest.fixture(scope="module")
def frames():
    team_games = pd.read_csv(FIXTURES / "cbb_team_games.csv", low_memory=False)
    player_games = pd.read_csv(FIXTURES / "cbb_player_games.csv", low_memory=False)
    schedule = pd.read_parquet(FIXTURES / "mbb_schedule_2026.parquet")
    return team_games, player_games, schedule


def _priced(lab: Path, frames, day: str = DAY) -> dict:
    team_games, player_games, schedule = frames
    games = schedule[schedule["game_date"].astype(str) == day]
    prices = pd.DataFrame([{"event_id": f"e{g.id}", "game_id": int(g.id)} for g in games.itertuples()])
    ratings.clear_caches()
    return ratings.matchups_for(
        day=day, history=PB.history_before(team_games, day), prices=prices,
        raw_dir=lab / "data" / "raw", player_games=PB.history_before(player_games, day),
    )


def _write_audit(lab: Path, as_of: str, switches: dict) -> None:
    path = CF.layer_audit_path(lab / "data" / "raw")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"as_of": as_of, "switches": switches}))


def test_the_declared_card_is_the_six_layers_on_and_the_candidates_off():
    switches = CF.default_switches()
    assert set(switches) == set(CF.SWITCHABLE)
    assert "strength" not in switches, "team strength is the model and is never switched"
    for key, _ in CF.LAYERS[1:]:
        assert switches[key] is True
    for key, _ in CF.CANDIDATE_LAYERS:
        assert switches[key] is False


def test_with_no_audit_the_card_prices_as_declared_and_keeps_the_candidates_in_the_shadow(lab, frames):
    priced = [m for m in _priced(lab, frames).values() if m.priceable]
    assert priced
    for game in priced:
        assert [layer["key"] for layer in game.layers] == [key for key, _ in CF.LAYERS]
        shadow = game.context["shadow"]
        assert set(shadow) == {key for key, _ in CF.CANDIDATE_LAYERS}
        assert game.context["switches"] == CF.default_switches()
        assert game.context["audit_as_of"] is None


def test_a_layer_switched_off_stays_on_the_page_unmoved_and_its_move_goes_to_the_shadow(lab, frames):
    before = {k: m for k, m in _priced(lab, frames).items() if m.priceable}
    _write_audit(lab, DAY, {"form": False, "pace_form": True})
    after = {k: m for k, m in _priced(lab, frames).items() if m.priceable}
    assert set(before) == set(after)
    moved = 0
    for key, game in after.items():
        keys = [layer["key"] for layer in game.layers]
        assert keys == [k for k, _ in CF.LAYERS] + ["pace_form"], keys
        form_at = keys.index("form")
        assert game.layers[form_at]["home"] == game.layers[form_at - 1]["home"]
        assert game.layers[form_at]["note"] == "switched off by the layer audit"
        assert "form" in game.context["shadow"] and "pace_form" not in game.context["shadow"]
        assert game.context["audit_as_of"] == DAY
        old = before[key].layers[form_at]
        shadow = game.context["shadow"]["form"]
        assert shadow["home"] == pytest.approx(old["home"] - before[key].layers[form_at - 1]["home"])
        moved += abs(shadow["home"]) > 0
        assert game.possessions == pytest.approx(game.layers[-1]["possessions"])
    assert moved, "no game carried any form, so the switch is untested"


@pytest.mark.parametrize("as_of, read", [(DAY, True), ("2026-03-10", True), ("2026-03-13", False), ("2026-03-01", False)])
def test_an_audit_dated_after_the_day_or_too_old_is_not_read(tmp_path, as_of, read):
    _write_audit(tmp_path, as_of, {"form": False})
    switches, _, reason = CF.load_layer_audit(tmp_path / "data" / "raw", day=DAY)
    assert (switches is not None) is read, reason
    if read:
        assert switches["form"] is False and switches["rest"] is True


def test_an_audit_cannot_switch_a_layer_it_does_not_know_or_switch_strength(tmp_path):
    _write_audit(tmp_path, DAY, {"strength": False, "astrology": True, "rest": "no"})
    switches, _, _ = CF.load_layer_audit(tmp_path / "data" / "raw", day=DAY)
    assert switches == CF.default_switches()


def _synthetic(key: str, *, on: bool, helps: bool, games: int, days: int, seed: int = 7) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(games):
        actual_m, actual_t = rng.normal(0, 11), rng.normal(140, 17)
        truth = rng.normal(0, 3)  # what the layer should move by
        move = truth if helps else -truth
        base_m = actual_m - truth + rng.normal(0, 9)
        pred_m = base_m + move if on else base_m
        rows.append({
            "day": f"2026-02-{1 + i % days:02d}", "game_id": i,
            "actual_margin": actual_m, "actual_total": actual_t,
            "pred_margin": pred_m, "pred_total": actual_t + rng.normal(0, 15),
            f"{key}:margin": move, f"{key}:total": 0.0, f"{key}:on": on,
        })
    return pd.DataFrame(rows)


def _verdict(frame: pd.DataFrame, key: str) -> LA.LayerVerdict:
    return {v.key: v for v in LA.judge(frame)}[key]


def test_a_layer_that_makes_predictions_worse_is_switched_off():
    verdict = _verdict(_synthetic("rest", on=True, helps=False, games=600, days=20), "rest")
    assert verdict.on is False and verdict.z <= LA.DROP_Z, verdict


def test_a_layer_that_helps_stays_on_and_a_candidate_that_helps_is_added():
    assert _verdict(_synthetic("rest", on=True, helps=True, games=600, days=20), "rest").on is True
    verdict = _verdict(_synthetic("pace_form", on=False, helps=True, games=600, days=20), "pace_form")
    assert verdict.on is True and verdict.z >= LA.ADD_Z, verdict


def test_a_thin_window_changes_nothing_however_strong_the_signal():
    verdict = _verdict(_synthetic("rest", on=True, helps=False, games=LA.MIN_GAMES - 1, days=20), "rest")
    assert verdict.on is True and "kept as declared" in verdict.reason
    verdict = _verdict(_synthetic("rest", on=True, helps=False, games=600, days=LA.MIN_DAYS - 1), "rest")
    assert verdict.on is True


def test_the_standard_error_is_clustered_by_day():
    values = pd.Series([1.0, 1.0, -1.0, -1.0])
    _, by_day = LA.clustered_mean(values, pd.Series(["a", "a", "b", "b"]))
    _, by_game = LA.clustered_mean(values, pd.Series(["a", "b", "c", "d"]))
    assert by_day > by_game, "two games on one day are not two independent observations"


def test_the_script_writes_an_audit_the_card_reads(lab, frames, monkeypatch):
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "run_layer_audit", Path(__file__).resolve().parents[1] / "scripts" / "run_layer_audit.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    processed = lab / "data" / "processed"
    processed.mkdir(parents=True)
    for name in ("cbb_team_games.csv", "cbb_player_games.csv"):
        (processed / name).write_bytes((FIXTURES / name).read_bytes())
    ratings.clear_caches()
    code = module.main(["--as-of", "2026-03-14", "--days", "5", "--processed-dir", str(processed),
                        "--raw-dir", str(lab / "data" / "raw")])
    assert code == 0
    record = json.loads(CF.layer_audit_path(lab / "data" / "raw").read_text())
    assert set(record["switches"]) == set(CF.SWITCHABLE)
    assert record["as_of"] == "2026-03-14"
    assert all(day < "2026-03-14" for day in record["window"]["days"])
    switches, _, _ = CF.load_layer_audit(lab / "data" / "raw", day="2026-03-14")
    assert switches == record["switches"]
