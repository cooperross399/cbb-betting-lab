"""The complement frame: built by the lab's own pairing rule, and honest about what it drops."""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab.reports import forecast_skill as FS

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "build_skill_frame.py"


def _module():
    sys.argv = [str(SCRIPT), "--help"]
    return runpy.run_path(str(SCRIPT))


def _load():
    return _module()["build"]


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


def _many(n: int) -> pd.DataFrame:
    """`n` settled opinions on `n` distinct wagers, a third of them bets.

    Large enough that one unpairable row is a *share* below the refusal
    threshold, which is the shape the real 566,377-row export has and the one
    a two-row fixture cannot express.
    """
    return pd.DataFrame({
        "event_id": [f"e{i}" for i in range(n)],
        "slate_date": ["2024-01-13"] * n,
        "market": ["total_points"] * n,
        "segment": ["game"] * n,
        "selection": [("over", "under")[i % 2] for i in range(n)],
        "line": [140.5 + (i % 9) for i in range(n)],
        "american_odds": [(-110, -105)[i % 2] for i in range(n)],
        "tier": [("mid_major", "high_major", "low_major")[i % 3] for i in range(n)],
        "book": ["fanduel"] * n,
        "model_probability": [0.50 + (i % 11) / 100 for i in range(n)],
        "outcome": [("won", "lost")[i % 2] for i in range(n)],
        FS.SELECTED_COLUMN: [i % 3 == 0 for i in range(n)],
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
    frame, census = build(graded, _store_with_complements(graded))
    assert census.unpairable == 0 and census.reconciles
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
    frame, census = build(graded, _store_with_complements(graded))
    assert census.unpairable == 0 and census.reconciles
    assert FS.SELECTED_COLUMN in frame.columns
    scorable = frame[frame["outcome"] != ""]
    comp = frame[frame["outcome"] == ""]
    assert scorable[FS.SELECTED_COLUMN].tolist() == graded[FS.SELECTED_COLUMN].tolist()
    assert comp[FS.SELECTED_COLUMN].notna().all()
    assert not comp[FS.SELECTED_COLUMN].astype(bool).any(), "a complement row was flagged as a bet"
    assert int(FS.selected_mask(frame).sum()) == int(graded[FS.SELECTED_COLUMN].sum()) == 1


def test_a_frame_where_every_row_pairs_excludes_nothing_and_the_census_is_zero():
    """The ordinary case, and the one the census must not make noisy.

    Every graded row finds its complement at its own book, so nothing is
    excluded, the census's unpairable term is zero, and the frame holds every
    row that was supplied.
    """
    build = _load()
    graded = _graded()
    frame, census = build(graded, _store_with_complements(graded))
    assert census.supplied == len(graded)
    assert census.paired == len(graded)
    assert census.unpairable == 0
    assert census.unpairable_selected == 0
    assert census.by_market == {} and census.by_book == {} and census.by_tier == {}
    assert census.rows == []
    assert census.share == 0.0
    assert census.reconciles is True
    assert census.refuses is False
    scorable = frame[frame["outcome"] != ""]
    assert len(scorable) == len(graded)
    assert sorted(scorable["event_id"]) == sorted(graded["event_id"])


def test_an_unpairable_row_is_excluded_counted_and_named_and_the_census_reconciles():
    """A book that hung one side only: excluded, but never silently.

    The row genuinely cannot be de-vigged — a one-sided quote holds no vig —
    so it leaves the frame. What the old script did instead was refuse the
    whole frame; what it must never do is drop the row without saying so. The
    census names the market, the book and the tier it fell on, carries the row
    itself, and `supplied = paired + unpairable` reconciles.
    """
    build = _load()
    graded = _graded()
    store = _store_with_complements(graded)
    store = store[~((store["event_id"] == "e2") & (store["selection"] == "over"))]  # e2's complement gone
    frame, census = build(graded, store)

    assert census.supplied == 2
    assert census.paired == 1
    assert census.unpairable == 1
    assert census.reconciles is True
    assert census.share == 0.5
    # e2 was the row with no complement, and it is gone from the frame.
    assert "e2" not in set(frame["event_id"]), "an unpairable row was kept anyway"
    assert set(frame["event_id"]) == {"e1"}
    # Named, not merely counted: market, book, tier, and the row itself.
    assert census.by_market == {"total_points": 1}
    assert census.by_book == {"fanduel": 1}
    assert census.by_tier == {"mid_major": 1}
    assert len(census.rows) == 1
    named = census.rows[0]
    assert named["event_id"] == "e2"
    assert named["selection"] == "under"
    assert named["book"] == "fanduel"
    assert named["line"] == 150.5
    # e2 was not a threshold-selected bet in the fixture, and the count says so.
    assert census.unpairable_selected == 0
    # Drop e1's complement instead — e1 IS a bet — and the count moves. A
    # dropped bet is a dropped stake and the winner's-curse comparison shrinks
    # with it, so it is counted apart rather than folded into the total.
    other = _store_with_complements(graded)
    other = other[~((other["event_id"] == "e1") & (other["selection"] == "under"))]
    _, bet_census = build(graded, other)
    assert bet_census.unpairable == 1
    assert bet_census.unpairable_selected == 1
    assert bet_census.rows[0]["event_id"] == "e1"
    assert bet_census.rows[0][FS.SELECTED_COLUMN] is True
    payload = census.to_json()
    assert payload["unpairable"] == 1 and payload["reconciles"] is True
    assert "one side" in payload["reason"] or "no hold" in payload["reason"]


def test_the_census_numbers_add_up_to_the_rows_supplied():
    """The identity is a real comparison, not an arithmetic tautology.

    `paired` and `unpairable` are each counted off the graded frame, so their
    sum being `supplied` is a claim that can fail — and it is the claim that
    catches a row reaching neither bucket. Checked here on both shapes: a
    frame where everything pairs and one where a row does not.
    """
    build = _load()
    graded = _graded()
    whole = _store_with_complements(graded)
    partial = whole[~((whole["event_id"] == "e2") & (whole["selection"] == "over"))]
    for store, expected in ((whole, 0), (partial, 1)):
        frame, census = build(graded, store)
        assert census.unpairable == expected
        assert census.paired + census.unpairable == census.supplied == len(graded)
        assert census.accounted == census.supplied
        assert census.reconciles is True
        # The frame's scorable rows are exactly the paired ones, so the census
        # describes the frame rather than something beside it.
        assert len(frame[frame["outcome"] != ""]) == census.paired
        assert sum(census.by_market.values()) == census.unpairable
        assert sum(census.by_book.values()) == census.unpairable
        assert sum(census.by_tier.values()) == census.unpairable


def test_a_selection_with_no_complement_at_all_is_kept_and_counted_apart():
    """A wager `pair_key` cannot key is a different fact, and belongs elsewhere.

    A selection outside `FS.COMPLEMENT` has no other side to look for, so it is
    not evidence that a book hung one side only. Folding it into the unpairable
    count would inflate the number the refusal threshold is read against and
    blame books for a vocabulary gap. It stays in the frame and
    `forecast_skill.DevigCensus` counts it under `unknown_selection`, which is
    where a reader already looks; this census records it apart and keeps the
    identity over the two buckets that are its own.
    """
    build = _load()
    graded = _graded()
    graded.loc[1, "selection"] = "yes"  # no complement in the lab's vocabulary
    store = pd.DataFrame([
        {"event_id": "e1", "market": "total_points", "segment": "game",
         "selection": "over", "line": 140.5, "book": "fanduel", "american_odds": -110},
        {"event_id": "e1", "market": "total_points", "segment": "game",
         "selection": "under", "line": 140.5, "book": "fanduel", "american_odds": -110},
    ])
    store["player"] = ""
    store["snapshot_phase"] = "card"

    frame, census = build(graded, store)
    assert census.no_pair_key == 1
    assert census.unpairable == 0, "a keyless selection is not a one-sided quote"
    assert census.paired == 2 and census.supplied == 2 and census.reconciles is True
    assert census.refuses is False
    assert set(frame["event_id"]) == {"e1", "e2"}, "the keyless row was dropped"


def test_an_unpairable_share_above_the_threshold_still_refuses(tmp_path, capsys):
    """Excluding a large share is a broken join wearing the costume of a quirk.

    One row in two is 50%, five thousand times the declared threshold. At that
    share the honest reading is not "some books hung one side"; it is that the
    pair key stopped matching — a renamed column, a flipped line convention, a
    book spelt two ways — and excluding half a measurement to make the script
    finish is the failure the old blanket refusal existed to prevent. So it
    still refuses, exits non-zero, writes nothing, and the message carries both
    the share it saw and the threshold it was measured against.
    """
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.providers import historical as H

    module = _module()
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
    captured = capsys.readouterr()
    assert code == 1
    assert code != 0
    assert not (tmp_path / "cbb_skill_frame.csv").exists(), "a partial frame was written"
    assert not module["census_path"](tmp_path / "cbb_skill_frame.csv").exists()
    # The message says the share it saw AND the threshold it failed.
    assert f"{0.5:.6%}" in captured.err
    assert f"{module['MAX_UNPAIRABLE_SHARE']:.6%}" in captured.err
    assert "broken join" in captured.err
    # And the census was printed before the refusal, so a reader can see where.
    assert "Unpairable census — supplied = paired + unpairable" in captured.out
    assert "total_points" in captured.out and "fanduel" in captured.out


def test_a_handful_of_unpairable_rows_is_excluded_counted_and_the_frame_is_written(tmp_path, capsys):
    """Below the threshold the frame is written, and the census goes with it.

    This is the case that stopped the lab: 2 rows in 566,377. The frame is
    written without them, the JSON record beside it states how many were
    excluded and why, and the reconciling identity is on stdout in the same
    shape the price backtest prints its own.
    """
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.providers import historical as H

    module = _module()
    graded = _many(12_000)
    store = _store_with_complements(graded)
    # One book hangs one side only, on one wager, out of twelve thousand.
    orphan = graded.iloc[7]
    store = store[
        ~(
            (store["event_id"] == orphan["event_id"])
            & (store["selection"] == FS.COMPLEMENT[orphan["selection"]])
        )
    ]
    share = 1 / len(graded)
    assert share < module["MAX_UNPAIRABLE_SHARE"], "the fixture must sit below the threshold"

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
    scorable = written[written["outcome"].notna() & (written["outcome"].astype(str) != "")]
    assert len(scorable) == len(graded) - 1, "the unpairable row is still in the frame"
    assert orphan["event_id"] not in set(scorable["event_id"])

    record = json.loads(module["census_path"](tmp_path / "cbb_skill_frame.csv").read_text())
    assert record["supplied"] == len(graded)
    assert record["unpairable"] == 1
    assert record["paired"] == len(graded) - 1
    assert record["paired"] + record["unpairable"] == record["supplied"]
    assert record["reconciles"] is True
    assert record["share"] == pytest.approx(share)
    assert record["max_share"] == module["MAX_UNPAIRABLE_SHARE"]
    assert record["by_book"] == {"fanduel": 1}
    assert sum(record["by_market"].values()) == 1
    assert record["rows"] and record["rows"][0]["event_id"] == orphan["event_id"]
    assert record["reason"]

    assert "Unpairable census — supplied = paired + unpairable" in out
    assert f"graded rows supplied  {len(graded):,}" in out
    assert f"unpairable            {1:,}" in out
    assert "reconciles            yes" in out
    assert f"{len(graded) - 1:,} scorable" in out


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
