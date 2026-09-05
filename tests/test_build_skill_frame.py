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
    """Two settled opinions, one of which cleared the threshold and was a bet.

    The export is every settled opinion with the bets flagged `selected`; a
    frame of bets alone with no flag is what it used to be, and the script
    refuses that (see `test_a_graded_frame_without_the_selected_flag_is_refused`).
    """
    return pd.DataFrame({
        "event_id": ["e1", "e2"][:n], "slate_date": ["2024-01-13"] * n, "market": ["total_points"] * n,
        "segment": ["game"] * n, "selection": ["over", "under"][:n], "line": [140.5, 150.5][:n],
        "american_odds": [-110, -105][:n], "tier": ["mid_major"] * n, "book": ["fanduel"] * n,
        "model_probability": [0.55, 0.53][:n], "outcome": ["won", "lost"][:n],
        FS.SELECTED_COLUMN: [True, False][:n],
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


def test_the_selected_flag_survives_and_a_complement_is_never_selected():
    """The flag is what tells the bets from the rest; the frame must carry it through.

    Graded rows keep exactly the flag the backtest stamped; complement rows are
    the other side of the price — not opinions, not bets — and carry False
    rather than a blank, because a blank would read as "unknown" in a column
    whose whole job is to be known.
    """
    build = _load()
    graded = _graded()
    frame, missing = build(graded, _store_with_complements(graded))
    assert missing == 0
    assert FS.SELECTED_COLUMN in frame.columns
    scorable = frame[frame["outcome"] != ""]
    comp = frame[frame["outcome"] == ""]
    assert scorable[FS.SELECTED_COLUMN].tolist() == graded[FS.SELECTED_COLUMN].tolist()
    assert comp[FS.SELECTED_COLUMN].notna().all()
    assert not comp[FS.SELECTED_COLUMN].astype(bool).any(), "a complement row was flagged as a bet"
    assert int(FS.selected_mask(frame).sum()) == int(graded[FS.SELECTED_COLUMN].sum()) == 1


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


def test_a_graded_frame_without_the_selected_flag_is_refused(tmp_path):
    """A frame with no `selected` column is indistinguishable from the old export.

    Before 2026-09-05 `--write-graded` wrote the threshold-selected bets and
    nothing else. A graded file left over from that backtest, passed through
    here and on to `forecast_skill`, would be fitted as every opinion and read
    as the skill measure — the winner's-curse slice with no mark on it. The
    script refuses (exit 2, nothing written) and names the re-run.
    """
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.providers import historical as H

    graded = _graded().drop(columns=[FS.SELECTED_COLUMN])
    store = _store_with_complements(graded)  # every complement present
    graded.to_csv(tmp_path / "cbb_graded_bets.csv", index=False)
    store.to_csv(H.store_path(CBB, tmp_path, H.CARD_WINDOW), index=False)

    sys.argv = [str(SCRIPT), "--processed-dir", str(tmp_path)]
    try:
        runpy.run_path(str(SCRIPT), run_name="__main__")
        code = 0
    except SystemExit as exc:
        code = int(exc.code or 0)
    assert code == 2
    assert not (tmp_path / "cbb_skill_frame.csv").exists(), "an unflagged frame was written through"


def test_a_complete_flagged_frame_is_written_with_both_populations_counted(tmp_path, capsys):
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.providers import historical as H

    graded = _graded()
    store = _store_with_complements(graded)
    graded.to_csv(tmp_path / "cbb_graded_bets.csv", index=False)
    store.to_csv(H.store_path(CBB, tmp_path, H.CARD_WINDOW), index=False)

    sys.argv = [str(SCRIPT), "--processed-dir", str(tmp_path)]
    try:
        runpy.run_path(str(SCRIPT), run_name="__main__")
        code = 0
    except SystemExit as exc:
        code = int(exc.code or 0)
    out = capsys.readouterr().out
    assert code == 0, out
    written = pd.read_csv(tmp_path / "cbb_skill_frame.csv")
    assert len(written) == 2 * len(graded)
    assert int(FS.selected_mask(written).sum()) == 1
    assert "2 settled opinion(s), of which 1 are the threshold-selected bets" in out
