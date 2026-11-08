"""The card does not bet where the model loses to the closing line (decision 82)."""

from __future__ import annotations

import json
from pathlib import Path

from cbb_betting_lab.models import closing_gate
from cbb_betting_lab.reports.card_pricing import Quote, Wager


def _wager(market: str, tier: str = "high_major", segment: str = "full_game", key: str = "") -> Wager:
    return Wager(
        key=("e1", market, segment, tier, key),
        event_id="e1", slate_date="2026-11-10", commence_time="2026-11-10T23:00:00Z",
        home_team="Home", away_team="Away", market=market, segment=segment,
        player="", selection="home", line=-3.5, tier=tier, quotes=(Quote("a", -110),),
    )


def _record(tmp_path: Path, as_of: str, alarms: list[str]) -> Path:
    path = tmp_path / closing_gate.RECORD_NAME
    path.write_text(json.dumps({"as_of": as_of, "alarms": alarms}), encoding="utf-8")
    return path


def test_an_alarmed_cell_and_its_ladder_are_closed_and_nothing_else(tmp_path):
    gate = closing_gate.load(_record(tmp_path, "2026-11-09", ["high_major / spread"]), "2026-11-10")
    closed = [_wager("spread"), _wager("alternate_spread")]
    kept = [_wager("moneyline"), _wager("spread", tier="mid_major"), _wager("spread_h1", segment="h1"),
            _wager("total_points")]
    probabilities = {w.key: 0.6 for w in closed + kept}
    out, removed = closing_gate.apply(probabilities, closed + kept, gate)
    assert removed == 2
    assert set(out) == {w.key for w in kept}


def test_a_stale_or_future_alarm_closes_nothing(tmp_path):
    stale = closing_gate.load(_record(tmp_path, "2026-11-01", ["high_major / spread"]), "2026-11-10")
    future = closing_gate.load(_record(tmp_path, "2026-11-11", ["high_major / spread"]), "2026-11-10")
    assert not stale.closed and not future.closed
    assert "older" in stale.reason and "after" in future.reason


def test_no_record_is_no_gate_never_no_card(tmp_path):
    gate = closing_gate.load(tmp_path / "missing.json", "2026-11-10")
    assert not gate.closed
    w = _wager("spread")
    assert closing_gate.apply({w.key: 0.6}, [w], gate) == ({w.key: 0.6}, 0)


def test_the_gate_never_adds_a_wager(tmp_path):
    gate = closing_gate.load(_record(tmp_path, "2026-11-10", ["high_major / spread"]), "2026-11-10")
    w = _wager("spread")
    out, removed = closing_gate.apply({}, [w], gate)
    assert out == {} and removed == 0


def test_the_card_reads_the_gate_after_trust_and_before_select():
    source = (Path(__file__).resolve().parents[1] / "src/cbb_betting_lab/reports/gameday_card.py").read_text()
    gate_at = source.index("closing_gate.apply(trusted, wagers, gate)")
    assert source.index("line_move.apply(trusted") < gate_at < source.index("result = select(")
