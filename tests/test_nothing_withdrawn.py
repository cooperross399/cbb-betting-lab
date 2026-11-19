"""Decision 111. Cooper, 2026-11-19: *"dont withdraw anything"*.

The card's own withdrawals are off: the closing-line gate (decision 82) and the
alternate-ladder cap (decision 86). Both modules stay, and their own tests
switch them on to keep the mechanism honest; the declared card runs without
them. The closing-line alarm still reports, and withdraws nothing.
"""

from __future__ import annotations

from cbb_betting_lab.models import closing_gate, rung_cap


def test_the_closing_line_gate_is_off_on_the_declared_card(tmp_path):
    assert closing_gate.GATE_ON is False
    gate = closing_gate.load(tmp_path / "missing.json", "2026-11-19")
    assert not gate.closed and gate.reason == "the gate is off"


def test_the_ladder_cap_is_off_on_the_declared_card():
    assert rung_cap.MAX_RUNG_DISTANCE is None
    assert rung_cap.apply({"k": 0.5}, []) == ({"k": 0.5}, 0)
