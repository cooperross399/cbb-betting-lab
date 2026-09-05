"""The complement frame, built by the lab's own pairing rule and refusing to be partial."""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pandas as pd

from cbb_betting_lab.reports import forecast_skill as FS

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_skill_frame.py"


def _load():
    sys.argv = [str(SCRIPT), "--help"]
    ns = runpy.run_path(str(SCRIPT))
    return ns["build"]


def _graded(n: int = 2) -> pd.DataFrame:
    return pd.DataFrame({
        "event_id": ["e1", "e2"][:n], "slate_date": ["2024-01-13"] * n, "market": ["total_points"] * n,
        "segment": ["game"] * n, "selection": ["over", "under"][:n], "line": [140.5, 150.5][:n],
        "american_odds": [-110, -105][:n], "tier": ["mid_major"] * n, "book": ["fanduel"] * n,
        "model_probability": [0.55, 0.53][:n], "outcome": ["won", "lost"][:n],
    })


def _store_with_complements(graded: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for r in graded.to_dict("records"):
        rows.append({k: r[k] for k in ("event_id", "market", "segment", "selection", "line", "book", "american_odds")})
        rows.append({**{k: r[k] for k in ("event_id", "market", "segment", "line", "book")},
                     "selection": FS.COMPLEMENT[r["selection"]], "american_odds": -110})
    frame = pd.DataFrame(rows)
    frame["player"] = ""
    frame["snapshot_phase"] = "card"
    return frame


def test_every_graded_bet_gets_exactly_one_complement_with_no_opinion():
    build = _load()
    graded = _graded()
    frame, missing = build(graded, _store_with_complements(graded))
    assert missing == 0
    assert len(frame) == 2 * len(graded)
    comp = frame[frame["outcome"] == ""]
    assert len(comp) == len(graded)
    assert comp["model_probability"].isna().all(), "a complement must carry no opinion"
    # The complements pair with the graded rows under the module's own rule.
    keys = [FS.pair_key(r) for r in frame.to_dict("records")]
    assert all(k is not None for k in keys)
    assert len(set(keys)) == len(graded), "each graded bet and its complement must share one pair key"


def test_a_missing_complement_is_counted_not_dropped():
    build = _load()
    graded = _graded()
    store = _store_with_complements(graded)
    store = store[~((store["event_id"] == "e2") & (store["selection"] == "over"))]  # e2's complement gone
    _, missing = build(graded, store)
    assert missing == 1


def test_the_script_refuses_to_write_a_partial_frame(tmp_path):
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.providers import historical as H

    graded = _graded()
    store = _store_with_complements(graded)
    store = store[~((store["event_id"] == "e2") & (store["selection"] == "over"))]
    graded.to_csv(tmp_path / "cbb_graded_bets.csv", index=False)
    store.to_csv(H.store_path(CBB, tmp_path, H.CARD_WINDOW), index=False)

    sys.argv = [str(SCRIPT), "--processed-dir", str(tmp_path)]
    try:
        runpy.run_path(str(SCRIPT), run_name="__main__")
        code = 0
    except SystemExit as exc:
        code = int(exc.code or 0)
    assert code == 1
    assert not (tmp_path / "cbb_skill_frame.csv").exists(), "a partial frame was written"
