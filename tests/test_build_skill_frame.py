"""The complement frame: built by the lab's own pairing rule, and honest about what it drops."""

from __future__ import annotations

import json
import runpy
import sys
import types
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


def _namespace() -> dict:
    """The script's own globals — the dict its functions actually close over.

    `runpy.run_path` hands back a **copy**, so assigning into what it returns
    does not reach `main`. A test that has to drive `main` past a census that
    does not reconcile needs the real namespace: the three census terms are
    disjoint and exhaustive over the graded rows, so no pair of input files can
    produce a census that fails to add up, and the refusal branch would
    otherwise be unreachable from the outside and unprotected — which is
    exactly how it survived every test in the suite.
    """
    module = types.ModuleType("build_skill_frame_under_test")
    module.__file__ = str(SCRIPT)
    # Registered before the exec, not for tidiness: `@dataclass` resolves its
    # annotations through `sys.modules[cls.__module__]`, and an unregistered
    # namespace makes the decorator raise while defining `UnpairableCensus`.
    sys.modules[module.__name__] = module
    exec(compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec"), module.__dict__)
    return module.__dict__


def _three() -> pd.DataFrame:
    """One row that pairs, one whose complement is missing, one with no pair key.

    The three census terms in one frame, which is what makes `paired` visibly
    not `supplied - unpairable`.
    """
    return pd.DataFrame({
        "event_id": ["e1", "e2", "e3"],
        "slate_date": ["2024-01-13"] * 3,
        "market": ["total_points"] * 3,
        "segment": ["game"] * 3,
        "selection": ["over", "under", "yes"],
        "line": [140.5, 150.5, 160.5],
        "american_odds": [-110, -105, 120],
        "tier": ["mid_major", "high_major", "low_major"],
        "book": ["fanduel"] * 3,
        "model_probability": [0.55, 0.53, 0.51],
        "outcome": ["won", "lost", "won"],
        FS.SELECTED_COLUMN: [True, False, False],
    })


def _store_for_three() -> pd.DataFrame:
    """e1 has both sides; e2's `over` is absent; e3 is not a wager `pair_key` keys."""
    frame = pd.DataFrame([
        {"event_id": "e1", "market": "total_points", "segment": "game",
         "selection": "over", "line": 140.5, "book": "fanduel", "american_odds": -110},
        {"event_id": "e1", "market": "total_points", "segment": "game",
         "selection": "under", "line": 140.5, "book": "fanduel", "american_odds": -110},
        {"event_id": "e2", "market": "total_points", "segment": "game",
         "selection": "under", "line": 150.5, "book": "fanduel", "american_odds": -105},
    ])
    frame["player"] = ""
    frame["snapshot_phase"] = "card"
    return frame


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
        assert (
            census.paired + census.unpairable + census.no_pair_key
            == census.supplied
            == len(graded)
        )
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
    blame books for a vocabulary gap. Folding it into `paired` — which this
    script did until 2026-09-05 — is the opposite error and just as wrong: a
    row with no pair key did not pair, it never went looking. So it is its own
    term. It stays in the frame, and `forecast_skill.DevigCensus` counts it
    under `unknown_selection`, which is where a reader already looks.
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
    assert census.paired == 1, "a row with no pair key was counted as having paired"
    assert census.supplied == 2 and census.reconciles is True
    assert census.accounted == 2
    assert census.refuses is False
    assert set(frame["event_id"]) == {"e1", "e2"}, "the keyless row was dropped"


def test_a_selection_with_a_named_other_side_but_no_pair_key_is_keyless_too():
    """`pair_key` refuses more rows than an unknown selection, and both are keyless.

    An over/under filed with no line at all is not a wager anyone could grade —
    defaulting it to zero would pair two different numbers — so `FS.pair_key`
    returns `None` for it while its selection `under` sits squarely in
    `FS.COMPLEMENT` and does have a named other side. Drop the `pk is not None`
    guard from `build`'s `wanted` comprehension and the row asks the store for
    `(None, fanduel, over)`, finds nothing, and is counted and excluded as
    though a book had hung one side of it. No book did: no key was ever formed
    and nothing was ever looked for. It belongs in `no_pair_key`, and in the
    frame — the term the refusal threshold is read against must not be inflated
    by this lab's own vocabulary.
    """
    build = _load()
    graded = _graded()
    graded.loc[1, "line"] = float("nan")  # an over/under with no line at all
    assert FS.pair_key(graded.loc[1].to_dict()) is None
    assert graded.loc[1, "selection"] in FS.COMPLEMENT, "the other side is named"
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
    assert census.unpairable == 0, "a row with no key is not a one-sided quote"
    assert census.paired == 1
    assert census.supplied == 2 and census.accounted == 2
    assert census.reconciles is True
    assert census.share == 0.0 and census.refuses is False
    assert census.by_book == {} and census.rows == []
    assert set(frame["event_id"]) == {"e1", "e2"}, "the keyless row was excluded"


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
    assert "Unpairable census — supplied = paired + unpairable + no_pair_key" in captured.out
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

    assert "Unpairable census — supplied = paired + unpairable + no_pair_key" in out
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


def test_every_census_term_is_counted_off_the_frame_and_none_is_a_residual():
    """`paired` is the rows that found a complement, not what is left over.

    Until 2026-09-05 `build` set `paired = len(graded) - len(excluded)`, so
    `supplied = paired + unpairable` held for any two frames whatever and could
    never have detected the loss it exists to detect — the same defect this lab
    had just fixed in `OpinionAccounting.count_from`, arriving here by copying
    the shape of that identity instead of its rule.

    One frame makes the difference visible: three rows, one that pairs, one
    whose complement is missing, one with no pair key. The residual would call
    two of them paired. Only one of them found a complement.
    """
    build = _load()
    graded = _three()
    frame, census = build(graded, _store_for_three())

    assert census.supplied == 3
    assert census.paired == 1
    assert census.unpairable == 1
    assert census.no_pair_key == 1
    assert census.accounted == 3
    assert census.reconciles is True
    # The residual would have said 2, and this is the whole point of the fix.
    assert census.paired != census.supplied - census.unpairable
    # Each term names the row a reader can go and look at.
    assert census.rows[0]["event_id"] == "e2"
    assert census.by_tier == {"high_major": 1}
    # e2 is gone; the keyless row is kept, because a vocabulary gap is not a
    # book hanging one side.
    scorable = frame[frame["outcome"] != ""]
    assert sorted(scorable["event_id"]) == ["e1", "e3"]
    assert len(scorable) == census.paired + census.no_pair_key


class _LosesARowWhenBuildDerivesAColumn(pd.DataFrame):
    """A graded frame that drops its last row the moment `build` assigns `_pk`.

    It stands in for the edit this identity exists to catch and cannot be
    provoked from the outside any other way: a filter, a dedupe or a re-index
    added to `graded` between the frame `build` was handed and the keys it
    buckets. `build`'s own three predicates are exhaustive over whatever
    survives that step, so the loss has to come from the frame itself.
    """

    @property
    def _constructor(self):
        return pd.DataFrame

    def assign(self, **kwargs):
        return pd.DataFrame(self).assign(**kwargs).iloc[:-1]


def test_a_graded_row_lost_before_the_bucketing_breaks_the_identity():
    """`supplied` is read at entry and `paired` is counted, or this is a tautology.

    Both halves are invisible to every other test here, because on a frame
    `build` loses no rows from, the count at entry, the count after the columns
    are derived and the sum of the three buckets are all the same number. This
    frame loses one, and they stop agreeing — which is the only condition under
    which the identity is a comparison rather than a restatement:

    * `paired = supplied - unpairable - no_pair_key` — the residual back in a
      three-term spelling — makes `accounted` equal `supplied` for any frame
      whatever, and calls two rows paired where one found a complement.
    * `supplied` read below the mask computations, or read off the masks
      themselves, counts the frame *after* the loss, so the identity reconciles
      over a population already short a row and says nothing was lost.

    The census must report the three rows it was handed, the one that actually
    paired, and a failure to reconcile.
    """
    build = _load()
    lossy = _LosesARowWhenBuildDerivesAColumn(_three())
    assert len(lossy) == 3, "the fixture must hand `build` all three rows"

    _, census = build(lossy, _store_for_three())

    assert census.supplied == 3, "`supplied` was read after the row went missing"
    assert census.paired == 1, "`paired` must count rows that found a complement"
    assert census.unpairable == 1
    assert census.no_pair_key == 0, "the keyless row is the one that went missing"
    assert census.accounted == 2
    assert census.reconciles is False, "a row that reached no bucket was absorbed"


def test_a_row_that_reached_no_bucket_makes_the_identity_fail_rather_than_absorb():
    """Empty each term by one in turn. The identity must notice all three.

    This is the test the residual arithmetic could not have: with `paired`
    derived, a row lost anywhere moved into `paired` and the sum stayed put.
    Asserted on the census itself, because `build`'s three predicates are
    exhaustive over its own input by construction and cannot produce the
    failure — the class is what carries the identity, and the class is what a
    later caller could set wrongly.
    """
    census_class = _module()["UnpairableCensus"]
    whole = census_class(
        supplied=10, paired=6, unpairable=3, no_pair_key=1, complements=6, paired_wagers=6
    )
    assert whole.accounted == 10
    assert whole.reconciles is True

    for term in ("paired", "unpairable", "no_pair_key"):
        short = census_class(
            supplied=10, paired=6, unpairable=3, no_pair_key=1,
            complements=6, paired_wagers=6,
        )
        setattr(short, term, getattr(short, term) - 1)
        assert short.accounted == 9
        assert short.reconciles is False, f"a row lost from `{term}` was absorbed"
    # And a row counted twice fails just as loudly as a row lost.
    doubled = census_class(
        supplied=10, paired=7, unpairable=3, no_pair_key=1, complements=7, paired_wagers=7
    )
    assert doubled.reconciles is False


def test_a_wager_quoted_two_complements_fails_the_identity_though_the_terms_add_up():
    """The one comparison in `reconciles` that a mis-bucketing cannot hide from.

    `accounted == supplied` is blind to anything that moves a row between
    buckets, because the sum does not move. The second comparison is not a
    rearrangement of the same count: the complement rows the frame actually
    carries, against the distinct wagers the paired rows asked for. A wager
    that contributed two complement rows has had its hold counted twice in the
    de-vig, and the terms above it still add up perfectly.
    """
    census_class = _module()["UnpairableCensus"]
    doubled = census_class(
        supplied=2, paired=2, unpairable=0, no_pair_key=0, complements=3, paired_wagers=2
    )
    assert doubled.accounted == doubled.supplied, "the identity itself is satisfied"
    assert doubled.reconciles is False, "a doubled complement went unnoticed"

    missing = census_class(
        supplied=2, paired=2, unpairable=0, no_pair_key=0, complements=1, paired_wagers=2
    )
    assert missing.accounted == missing.supplied
    assert missing.reconciles is False, "a paired wager with no complement went unnoticed"

    # `-1` is "no frame was built", not "zero complements": the cross-check is
    # not made rather than made and failed.
    unbuilt = census_class(supplied=2, paired=2, unpairable=0, no_pair_key=0)
    assert unbuilt.complements == -1 and unbuilt.paired_wagers == -1
    assert unbuilt.reconciles is True


def test_the_frame_carries_one_complement_per_paired_wager_and_the_census_counts_both():
    """Both sides of the cross-check are read off something real.

    `complements` is the complement block in the returned frame; `paired_wagers`
    is the distinct wagers the paired rows asked for. They are compared to each
    other and never to `paired`, because two graded rows that are the same quote
    filed twice both pair and both want the one complement.
    """
    build = _load()
    graded = _graded()
    frame, census = build(graded, _store_with_complements(graded))
    complement_rows = frame[frame["outcome"] == ""]
    assert census.complements == len(complement_rows) == 2
    assert census.paired_wagers == 2
    assert len(frame) == census.paired + census.no_pair_key + census.complements
    assert census.reconciles is True

    # The same quote filed twice: two paired rows, one wager, one complement —
    # so comparing `complements` to `paired` would fail on a frame that is fine.
    twice = pd.concat([graded.head(1), graded.head(1)], ignore_index=True)
    frame2, census2 = build(twice, _store_with_complements(graded))
    assert census2.paired == 2
    assert census2.paired_wagers == 1
    assert census2.complements == 1
    assert census2.reconciles is True
    assert len(frame2) == census2.paired + census2.no_pair_key + census2.complements

    # And on the three-row frame the complement block is the paired row's alone.
    frame3, census3 = build(_three(), _store_for_three())
    assert census3.complements == census3.paired_wagers == 1
    assert census3.complements == len(frame3[frame3["outcome"] == ""])


def test_moving_one_row_between_buckets_is_what_the_identity_cannot_see():
    """State the blindness rather than imply a coverage the arithmetic lacks.

    The three predicates are disjoint and exhaustive, so a row put in the wrong
    bucket moves a count from one term to another and the sum is unchanged. The
    identity cannot see that, and the class docstring says so. What does move
    is `share` — the number the refusal threshold is read against — so a
    mis-bucketing that inflates `unpairable` is caught by the refusal instead,
    and one that deflates it is caught by nothing here and only by the tests.
    """
    census_class = _module()["UnpairableCensus"]
    true_census = census_class(
        supplied=10_000, paired=9_999, unpairable=1, no_pair_key=0,
        complements=9_999, paired_wagers=9_999,
    )
    mis_bucketed = census_class(
        supplied=10_000, paired=9_998, unpairable=2, no_pair_key=0,
        complements=9_999, paired_wagers=9_999,
    )
    assert true_census.reconciles is True
    assert mis_bucketed.reconciles is True, "the identity is blind here, by construction"
    assert mis_bucketed.accounted == true_census.accounted == 10_000
    assert mis_bucketed.share > true_census.share
    assert mis_bucketed.share == 2 / 10_000


def test_the_refusal_threshold_is_pinned_to_the_number_its_comment_argues_for():
    """Changing this constant must be a deliberate, visible act.

    The suite otherwise constrains it only to a band — one fixture sits below
    it, another above — so it could be moved by a factor of five thousand
    without a single test failing, and the comment arguing for 0.01% would
    quietly stop describing the code. The two claims that comment makes about
    the real 566,377-row export are pinned beside it.
    """
    module = _module()
    threshold = module["MAX_UNPAIRABLE_SHARE"]
    assert threshold == 0.0001, (
        "MAX_UNPAIRABLE_SHARE is pinned. Changing it changes which broken joins "
        "this script writes through; change the comment's argument with it."
    )
    assert module["UNPAIRABLE_ROWS_NAMED"] == 25
    # Above the observed quirk with room: 2 unpairable rows in 566,377.
    assert threshold > 2 / 566_377
    assert threshold / (2 / 566_377) > 28
    # Below the narrowest join-shaped break the export can express — the loss
    # of its smallest single book, 119 rows — which therefore still refuses.
    assert threshold < 119 / 566_377
    assert threshold < 292 / 566_377  # and its smallest single market


def test_the_refusal_fires_a_hair_above_the_threshold_and_not_at_it():
    """The constant is pinned; the comparison that reads it was not.

    `MAX_UNPAIRABLE_SHARE == 0.0001` says nothing about what :attr:`refuses`
    does with it. Widen the comparison to `share > max_share * 2` and every
    test in this suite still passes, because the fixtures sit five thousand
    times above the threshold or at zero and none of them lands in the gap. Two
    censuses one row apart pin the boundary itself: at the declared share this
    is bookkeeping and writes, one row past it this is a broken join and
    refuses.
    """
    module = _module()
    census_class = module["UnpairableCensus"]
    threshold = module["MAX_UNPAIRABLE_SHARE"]

    at = census_class(supplied=100_000, paired=99_990, unpairable=10, no_pair_key=0)
    assert at.share == threshold
    assert at.refuses is False, "exactly at the declared share is not above it"

    over = census_class(supplied=100_000, paired=99_989, unpairable=11, no_pair_key=0)
    assert over.share > threshold
    assert over.refuses is True, "one row past the declared share must refuse"
    # A hair over, not an order of magnitude: a comparison loosened to twice
    # the threshold would write this frame out.
    assert over.share < 2 * threshold


def test_an_unpairable_row_whose_book_is_missing_is_still_counted_in_the_tally():
    """A breakdown that drops rows stops describing the census it sits under.

    `value_counts` drops the missing value, so `_tally` has to put a cell that
    is not there under a key of its own. This was reported as dead code on the
    grounds that `astype(str)` has already spelt NaN `"nan"` — true through
    pandas 2, false on the 3.0.5 this lab runs, where the cast leaves a missing
    value missing. So the test is on the property rather than on either
    mechanism: whatever pandas does with the cast, the tallies total
    `unpairable` and the row is filed under a name a reader can see.
    """
    build = _load()
    graded = _graded()
    graded.loc[1, "book"] = float("nan")  # no book recorded on the second row
    store = pd.DataFrame([
        {"event_id": "e1", "market": "total_points", "segment": "game",
         "selection": "over", "line": 140.5, "book": "fanduel", "american_odds": -110},
        {"event_id": "e1", "market": "total_points", "segment": "game",
         "selection": "under", "line": 140.5, "book": "fanduel", "american_odds": -110},
    ])
    store["player"] = ""
    store["snapshot_phase"] = "card"

    _, census = build(graded, store)
    assert census.unpairable == 1
    assert sum(census.by_book.values()) == census.unpairable, "the row left the tally"
    assert sum(census.by_market.values()) == census.unpairable
    assert sum(census.by_tier.values()) == census.unpairable
    label = _module()["MISSING_LABEL"]
    assert list(census.by_book) == [label]
    assert label.strip(), "a missing book must be named, not left blank"
    assert census.to_json()["by_book"] == {label: 1}


def test_main_refuses_a_census_that_does_not_reconcile_and_writes_nothing(tmp_path, capsys):
    """The refusal branch, exercised — it survived every test in the suite before.

    Nothing a caller can put in the two input files makes the identity fail:
    `build`'s three predicates are disjoint and exhaustive over its own input,
    which is exactly why the branch was unreachable from the outside and
    deleting it whole broke no test. So the census is damaged here instead,
    once for each comparison the script makes of it — the identity, the
    complement block, and the rows `main` itself read from the file — and the
    script must exit non-zero with nothing written every time. The third is the
    one that reaches what the arithmetic inside `build` cannot: a row lost
    before the bucketing leaves three terms that still add up to each other.
    """
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.providers import historical as H

    graded = _graded()
    store = _store_with_complements(graded)
    graded.to_csv(tmp_path / "cbb_graded_bets.csv", index=False)
    store.to_csv(H.store_path(CBB, tmp_path, H.CARD_WINDOW), index=False)

    def _run(damage) -> tuple[int, str, str]:
        ns = _namespace()
        honest = ns["build"]

        def damaged(graded_frame, store_frame):
            frame, census = honest(graded_frame, store_frame)
            damage(census)
            return frame, census

        ns["build"] = damaged
        code = ns["main"](["--processed-dir", str(tmp_path)])
        captured = capsys.readouterr()
        return code, captured.out, captured.err

    def lose_a_row(census) -> None:
        census.paired -= 1  # a graded row that reached no bucket at all

    def double_a_complement(census) -> None:
        census.complements += 1  # one wager's hold counted twice in the de-vig

    def lose_a_row_before_the_census(census) -> None:
        census.supplied -= 1  # a row lost between the CSV and the bucketing
        census.paired -= 1  # so the three terms still add up to each other

    damages = (
        (lose_a_row, "does not reconcile", "1 paired"),
        (double_a_complement, "does not reconcile", "3 complement"),
        (lose_a_row_before_the_census, "were read from", "1 graded rows"),
    )
    for damage, message, expected in damages:
        code, out, err = _run(damage)
        assert code == 1, f"a census that does not reconcile was written anyway: {out}"
        assert not (tmp_path / "cbb_skill_frame.csv").exists(), "a frame was written"
        assert not _module()["census_path"](tmp_path / "cbb_skill_frame.csv").exists()
        assert message in err
        assert expected in err
        # The census is printed before the refusal, so a reader sees the terms.
        assert "Unpairable census — supplied = paired + unpairable + no_pair_key" in out


def test_the_written_frame_and_the_printed_line_agree_with_the_census(tmp_path, capsys):
    """The summary line is read off the census, never as a difference.

    `complements = len(frame) - paired` is a subtraction, and a subtraction is
    how the identity came to reconcile by construction in the first place. The
    line must state the census's own three terms, and the frame on disk must
    hold exactly `paired + no_pair_key + complements` rows.
    """
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.providers import historical as H

    graded = _three()
    store = pd.concat([_store_for_three()] * 1, ignore_index=True)
    # Below the refusal threshold this frame is not, so keep every row pairable
    # except the keyless one, which is not unpairable at all.
    graded = graded[graded["event_id"] != "e2"].reset_index(drop=True)
    graded.to_csv(tmp_path / "cbb_graded_bets.csv", index=False)
    store.to_csv(H.store_path(CBB, tmp_path, H.CARD_WINDOW), index=False)

    ns = _namespace()
    code = ns["main"](["--processed-dir", str(tmp_path)])
    out = capsys.readouterr().out
    assert code == 0, out

    written = pd.read_csv(tmp_path / "cbb_skill_frame.csv")
    record = json.loads(ns["census_path"](tmp_path / "cbb_skill_frame.csv").read_text())
    assert record["supplied"] == 2
    assert record["paired"] == 1
    assert record["no_pair_key"] == 1
    assert record["unpairable"] == 0
    assert record["accounted"] == 2
    assert record["complements"] == record["paired_wagers"] == 1
    assert record["reconciles"] is True
    assert len(written) == record["paired"] + record["no_pair_key"] + record["complements"]
    assert "3 rows = 2 scorable + 1 complement-only" in out
    assert "no_pair_key           1" in out


def test_one_complement_per_paired_wager_even_when_the_store_holds_it_twice():
    """The store keeps a quote once per snapshot phase, and a doubled hold is silent.

    `stores.dedupe_prices` keys on the quote **including** `snapshot_phase`, so
    the same complement legitimately survives it twice. Both rows carry the same
    pair key, the same book and the same selection, and both would land in the
    frame as complements — de-vigging that wager against two copies of one side.
    Nothing in `supplied = paired + unpairable + no_pair_key` moves when that
    happens, which is why the census counts the complement block as well.
    """
    build = _load()
    graded = _graded(1)
    store = _store_with_complements(graded)
    twice = store[store["selection"] == FS.COMPLEMENT[graded.loc[0, "selection"]]].copy()
    twice["snapshot_phase"] = "open"  # the same quote, a second snapshot phase
    store = pd.concat([store, twice], ignore_index=True)
    assert len(store) == 3, "the fixture must offer the complement twice"

    frame, census = build(graded, store)
    assert census.paired == 1
    assert census.paired_wagers == 1
    assert census.complements == 1, "one wager took two complement rows into the frame"
    assert census.reconciles is True
    complement_rows = frame[frame["outcome"] == ""]
    assert len(complement_rows) == 1
    assert len(frame) == census.paired + census.no_pair_key + census.complements
