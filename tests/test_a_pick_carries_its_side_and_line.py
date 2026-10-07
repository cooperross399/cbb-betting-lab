"""The board's pick carries the side and line the page's live status reads.

`web/lib/live.js::pickStatusFor` judges a CBB pick against the live score
from `pick.side` and, for a spread or total, `pick.line` (a spread's line is
the picked side's handicap: `mine + line`).
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

BUILDER = Path(__file__).resolve().parents[1] / "web" / "build_board_json.py"


def _builder():
    spec = importlib.util.spec_from_file_location("build_board_json_side_line", BUILDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _pick(market: str, selection: str, line: str) -> dict:
    row = {"market": market, "selection": selection, "line": line, "american_odds": "-110", "edge": "0.04"}
    return _builder().pick_from_frozen([row], "DUKE", "UNC")


@pytest.mark.parametrize(("market", "selection", "line", "side", "want_line"), [
    ("h2h", "away", "", "away", None),
    ("spreads", "home", "-3.5", "home", -3.5),
    ("totals", "over", "141.5", "over", 141.5),
])
def test_a_pick_names_its_side_and_line(market, selection, line, side, want_line) -> None:
    pick = _pick(market, selection, line)
    assert (pick["side"], pick["line"]) == (side, want_line), pick


def test_a_spread_with_no_readable_line_carries_no_side() -> None:
    pick = _pick("spreads", "home", "")
    assert pick["side"] is None and pick["line"] is None, pick
