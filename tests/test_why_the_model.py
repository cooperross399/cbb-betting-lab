"""`docs/why_the_model_does_or_does_not_have_an_edge.md` said it was generated.

Its third line read, verbatim:

    **Generated from `data/outputs/cbb_price_backtest.json`.** Every figure is
    read from that record rather than typed, so this cannot drift from the
    measurement. Re-render whenever the record changes.

**No generator existed.** Every figure in that document had been typed by hand,
and the sentence promising otherwise is exactly the sentence that stops a reader
checking one. It had already drifted: the document quoted a pooled
forecast-skill advantage of `−0.01312 [−0.01468, −0.01156]` and called it the
comparison *"with the vig left in"*, when `−0.01312` is the **de-vigged**
comparison and `[−0.01468, −0.01156]` are its **uncorrected** bounds — the wrong
instrument and the un-widened interval, printed under a heading claiming neither
could happen.

These tests pin the generator that sentence claimed, and they pin the committed
document against it, so the claim cannot become false again without a red build.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.reports import forecast_skill as FS
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.reports import why_the_model as WHY

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "run_why_the_model.py"
OUTPUTS = PROJECT_ROOT / "data" / "outputs"
DOC = PROJECT_ROOT / WHY.DOC_RELATIVE
LOOP = PROJECT_ROOT / "scripts" / "run_weekly_loop.py"
STATUS = PROJECT_ROOT / "docs" / "project_status.md"


# --------------------------------------------------------------------------
# Fixtures: a real output tree, copied so a test can break one record
# --------------------------------------------------------------------------


@pytest.fixture
def outputs(tmp_path: Path) -> Path:
    """A copy of the committed output tree, writable.

    Copied rather than synthesised: a generator tested only against records
    this file invented is a generator tested against this file's idea of the
    record shape, which is the shape it will still agree with after the real
    one changes.
    """
    assert OUTPUTS.is_dir(), (
        f"{OUTPUTS} is missing. Every record this fixture copies is tracked by "
        "git, so its absence is a broken checkout and not a reason to pass. "
        "This fixture never skips: a guard that skips itself out of existence "
        "when its data is absent is not a guard, and this repository fails its "
        "own build on a skip for exactly that reason."
    )
    target = tmp_path / "outputs"
    shutil.copytree(OUTPUTS, target)
    return target


def build(outputs: Path) -> dict:
    return WHY.build_record(competition=CBB, output_dir=outputs)


def committed_record() -> dict:
    """The committed run record, or one BUILT from the committed evidence.

    Never skips. The record is an intermediate — the three measurement records
    beside it are the source of truth — so a checkout without it is a checkout
    that has not run the generator yet, and the test can run it. Building the
    record here rather than skipping is also the only version of these tests
    that still fires on the day somebody deletes the record to make them quiet.
    """
    path = WHY.record_path(CBB, OUTPUTS)
    if path.is_file():
        return WHY.read_record(path)
    return build(OUTPUTS)


def run_script(*args: str) -> subprocess.CompletedProcess:
    env = {
        "PATH": "/usr/bin:/bin",
        "PYTHONPATH": str(PROJECT_ROOT / "src"),
        "HOME": str(PROJECT_ROOT),
    }
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        cwd=str(PROJECT_ROOT),
        env=env,
        timeout=300,
    )


# --------------------------------------------------------------------------
# 1. It refuses rather than inventing
# --------------------------------------------------------------------------


@pytest.mark.parametrize("label", ["price backtest", "forecast skill", "held-out replication"])
def test_the_generator_refuses_when_one_of_its_three_records_is_absent(outputs, label):
    """A document that weighs two instruments and reads like an answer is worse
    than no document. Each of the three is required, and the refusal names the
    file rather than the class of file."""
    path = WHY.evidence_paths(CBB, outputs)[label]
    path.unlink()
    with pytest.raises(WHY.WhyError) as caught:
        build(outputs)
    assert path.name in str(caught.value), (
        f"the refusal for a missing {label} record must name the file"
    )


@pytest.mark.parametrize("label", ["price backtest", "forecast skill", "held-out replication"])
def test_an_unreadable_record_is_refused_and_never_read_as_an_empty_one(outputs, label):
    """A broken instrument is never reported as a null result. Truncated JSON
    parses as nothing; nothing renders as a document with no findings in it,
    which is a claim."""
    path = WHY.evidence_paths(CBB, outputs)[label]
    path.write_text("{ this is not json", encoding="utf-8")
    with pytest.raises(WHY.WhyError):
        build(outputs)


def test_a_record_missing_a_section_is_refused_rather_than_rendered_empty(outputs):
    """An absent `by_tier` is not three tiers with nothing in them."""
    path = WHY.evidence_paths(CBB, outputs)["price backtest"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload.pop("by_tier")
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(WHY.WhyError) as caught:
        build(outputs)
    assert "by_tier" in str(caught.value)


def test_the_script_exits_two_and_writes_nothing_when_a_record_is_missing(tmp_path):
    """The refusal reaches the process boundary. Nothing is written: no record,
    no report, and no splice, so the document keeps saying what it last
    truthfully said instead of gaining a hole."""
    empty = tmp_path / "outputs"
    empty.mkdir()
    report = tmp_path / "report.md"
    record = tmp_path / "record.json"
    completed = run_script(
        "--competition", "cbb",
        "--output-dir", str(empty),
        "--record", str(record),
        "--report", str(report),
    )
    assert completed.returncode == 2, completed.stderr
    assert not report.exists() and not record.exists()
    assert "cbb_price_backtest.json" in completed.stderr


# --------------------------------------------------------------------------
# 2. The vocabulary
# --------------------------------------------------------------------------


def _tier(**over) -> dict:
    row = {
        "name": "mid_major",
        "market": "",
        "tier": "mid_major",
        "roi": -0.04,
        "low": -0.09,
        "high": 0.01,
        "bets": 50_000,
        "clusters": 500,
        "standard_error": 0.025,
        "cluster_unit": "day",
    }
    row.update(over)
    return row


def test_an_interval_that_spans_zero_reads_the_exact_phrase(outputs):
    """`stats.NO_DEMONSTRATED_EDGE` and nothing softer. The phrase is imported,
    never retyped: a second copy drifts, and never conservatively."""
    record = build(outputs)
    spanning = [
        row
        for row in record["tiers"] + record["cells"]
        if row["enough_evidence"]
        and (row["adjusted_low"] or 0.0) < 0.0 < (row["adjusted_high"] or 0.0)
    ]
    assert spanning, "this fixture has no interval spanning zero to check"
    for row in spanning:
        assert row["verdict"] == S.NO_DEMONSTRATED_EDGE, row


def test_only_an_interval_excluding_zero_after_the_correction_is_ever_demonstrated(outputs):
    """A demonstrated edge or deficit is read off the CORRECTED bounds. The
    uncorrected ones are narrower by construction, so a verdict read off them
    would call findings demonstrated that the family-wise correction rejects."""
    record = build(outputs)
    for row in record["tiers"] + record["cells"] + record["pooled"]:
        if row["verdict"] in (S.DEMONSTRATED_EDGE, S.DEMONSTRATED_DEFICIT):
            low, high = row["adjusted_low"], row["adjusted_high"]
            assert low is not None and high is not None
            assert low > 0.0 or high < 0.0, (
                f"{row['name']} is called {row['verdict']!r} on a corrected "
                f"interval [{low}, {high}] that contains zero"
            )
            assert (row["verdict"] == S.DEMONSTRATED_EDGE) == (low > 0.0)


def test_a_cell_below_the_declared_floor_prints_a_phrase_and_no_number(outputs):
    """A +12% return over 40 bets and a coin flip are the same claim at that
    sample size, and printing the +12% invites somebody to quote it out of the
    row that qualifies it."""
    record = build(outputs)
    thin = [row for row in record["tiers"] if not row["enough_evidence"]]
    assert thin, "this fixture has no below-floor tier to check"
    for row in thin:
        figure = WHY._figure(row)
        assert "%" not in figure, figure
        assert str(S.MINIMUM_BETS) in figure, figure


def test_every_measured_tier_prints_its_sample_size_beside_its_return(outputs):
    """No bare percentage anywhere in the tier table."""
    record = build(outputs)
    for row in record["tiers"]:
        figure = WHY._figure(row)
        if "%" in figure:
            assert "bets," in figure or "bet," in figure, figure


def test_the_forbidden_vocabulary_is_refused_at_the_write(outputs, tmp_path):
    """A generated summary that reaches for a tipster's phrase has stopped
    reporting and started selling, so the write raises rather than producing
    the file. The list is `what_we_can_claim`'s, not a second copy of it."""
    record = build(outputs)
    record["backtest"]["season_label"] = "a guaranteed season"
    with pytest.raises(WHY.WhyError) as caught:
        WHY.write_report(record, tmp_path / "out.md")
    assert "guaranteed" in str(caught.value)
    assert not (tmp_path / "out.md").exists()


# --------------------------------------------------------------------------
# 3. Per tier, never a pooled headline
# --------------------------------------------------------------------------


def test_the_headline_is_per_tier_and_cannot_reach_the_pooled_figure(outputs):
    """The document this replaced put the pooled Division I row in the same
    table as the three tiers, three lines below a sentence saying it never
    would. `headline` reads `record["tiers"]` and nothing else."""
    record = build(outputs)
    pooled = record["every_market"]
    assert pooled, "this fixture has no pooled row to check the headline against"
    line = WHY.headline(record)
    assert f"{pooled['bets']:,}" not in line, (
        "the headline names the pooled sample size, which makes it a pooled "
        f"headline: {line!r}"
    )
    for tier in record["tiers"]:
        if tier["enough_evidence"]:
            assert f"{tier['bets']:,}" in line


def test_the_pooled_figure_appears_only_under_the_caveat(outputs):
    """It is computed because `docs/when_this_ends.md` applies the stopping
    rule to it, not so it can be quoted on its own."""
    record = build(outputs)
    rendered = WHY.render(record)
    assert PB.POOLED_CAVEAT in rendered
    pooled_figure = WHY._figure(record["every_market"])
    caveat_at = rendered.index(PB.POOLED_CAVEAT)
    assert rendered.index(pooled_figure) > caveat_at, (
        "the pooled figure is printed before the caveat that qualifies it"
    )


def test_the_title_reads_the_sign_rather_than_stating_a_conclusion(outputs):
    """A file named *does or does not* whose heading is typed says whichever of
    the two somebody last believed. Flip one tier to a demonstrated edge and
    the heading has to follow."""
    record = build(outputs)
    assert "does not have a demonstrated edge" in WHY.title(record)
    winner = WHY.cell(
        _tier(roi=0.30, low=0.25, high=0.35, standard_error=0.02), looks=1
    )
    assert winner["verdict"] == S.DEMONSTRATED_EDGE, winner
    record["tiers"] = [winner]
    assert "does have a demonstrated edge" in WHY.title(record)
    assert "demonstrated edge" in WHY.headline(record)


def test_a_verdict_typed_into_the_record_never_reaches_the_document(outputs):
    """**The headline reads the sign.**

    Setting a row's `verdict` to a demonstrated edge in the record on disk once
    made the rendered document say so, over an interval that spans zero: the
    renderer printed `row["verdict"]` and trusted it. The render now derives
    every verdict from the interval it is about to print and refuses a record
    whose stored string disagrees — refuses rather than silently printing the
    derived one, because a disagreement between a measurement and the file
    claiming to hold it is something a human has to see.
    """
    record = build(outputs)
    spanning = next(
        row
        for row in record["tiers"]
        if row["enough_evidence"]
        and (row["adjusted_low"] or 0.0) < 0.0 < (row["adjusted_high"] or 0.0)
    )
    spanning["verdict"] = S.DEMONSTRATED_EDGE

    with pytest.raises(WHY.WhyError) as caught:
        WHY.render(record)
    assert S.DEMONSTRATED_EDGE in str(caught.value)
    assert S.NO_DEMONSTRATED_EDGE in str(caught.value)

    # And every reader of a verdict reads the interval, not the string, so the
    # planted word cannot reach a headline, a table cell or an edge count even
    # if the refusal above were removed.
    assert WHY.verdict_of(spanning) == S.NO_DEMONSTRATED_EDGE
    assert WHY.demonstrated_edges([spanning]) == []
    assert WHY._figure(spanning).endswith(S.NO_DEMONSTRATED_EDGE), WHY._figure(spanning)
    assert "shows a demonstrated edge" not in WHY.headline({"tiers": [spanning]})
    assert "does have a demonstrated edge" not in WHY.title({"tiers": [spanning]})


def test_a_verdict_typed_into_the_forecast_table_never_reaches_the_document(outputs):
    """The same rule in the other table on the page. Its Reading column used to
    print the verdict string stored beside the Brier advantage."""
    record = build(outputs)
    advantage = record["forecast"]["tiers"][0]["advantage_over_raw"]
    assert advantage["verdict"] == S.DEMONSTRATED_DEFICIT
    advantage["verdict"] = S.DEMONSTRATED_EDGE
    with pytest.raises(WHY.WhyError) as caught:
        WHY.render(record)
    assert "advantage_over_raw" in str(caught.value)
    assert WHY.verdict_of(advantage) == S.DEMONSTRATED_DEFICIT


@pytest.mark.parametrize(
    "roi,adjusted_low,adjusted_high,expected",
    [
        # Entirely below zero, with a winning return typed beside it. This is
        # the pair that used to read "a demonstrated edge".
        (+0.05, -0.09, -0.02, S.DEMONSTRATED_DEFICIT),
        # Entirely above zero, with a losing return typed beside it.
        (-0.05, +0.02, +0.09, S.DEMONSTRATED_EDGE),
        # Spanning zero. Neither word is available at any return.
        (+0.05, -0.09, +0.02, S.NO_DEMONSTRATED_EDGE),
    ],
)
def test_the_verdict_is_read_off_the_two_bounds_that_are_printed(
    roi: float, adjusted_low: float, adjusted_high: float, expected: str
):
    """**A verdict is a statement about the interval printed beside it.**

    `printed_interval` hands the corrected bounds in as the interval's own, so
    the reading is of the pair a reader sees — but the reading itself used to
    come from the row's `roi`, which is a *different number in the record*. A
    row carrying `+5.0%` over corrected bounds of −9.0% to −2.0% therefore
    cleared the correction (zero is outside those bounds) and was then called a
    demonstrated **edge**, because the sign consulted was the typed return's
    and not the losing interval's.

    Each case types a return whose sign disagrees with its bounds, so a
    verdict derived from `roi` gets two of these three wrong.
    """
    row = {
        "name": "mid_major",
        "tier": "mid_major",
        "roi": roi,
        "adjusted_low": adjusted_low,
        "adjusted_high": adjusted_high,
        "bets": 50_000,
        "clusters": 500,
    }

    assert WHY.verdict_of(row) == expected
    assert (WHY.demonstrated_edges([row]) == [row]) == (expected == S.DEMONSTRATED_EDGE)
    assert (WHY.demonstrated_deficits([row]) == [row]) == (
        expected == S.DEMONSTRATED_DEFICIT
    )
    assert WHY._figure(row).endswith(expected), WHY._figure(row)


def test_a_return_outside_its_own_corrected_interval_is_refused_not_printed(outputs):
    """The other half of *"the two must never be printed in disagreement"*.

    Deriving the verdict from the bounds stops the losing interval being called
    an edge. It does not stop the line reading **+5.0%, corrected −9.0% to
    −2.0% — demonstrated deficit**, which is a return no estimator could have
    produced those bounds around: the interval is built around the estimate, so
    a return outside it is two measurements spliced into one row. There is no
    honest way to print that line, and no way to choose which of the two
    numbers to believe, so the render refuses it.

    The stored verdict here is set to what the bounds read, so the only thing
    this test can be failed by is the new check.
    """
    record = build(outputs)
    row = next(r for r in record["tiers"] if r["enough_evidence"])
    row["roi"] = +0.05
    row["adjusted_low"], row["adjusted_high"] = -0.09, -0.02
    row["verdict"] = S.DEMONSTRATED_DEFICIT

    with pytest.raises(WHY.WhyError) as caught:
        WHY.render(record)
    message = str(caught.value)
    assert "does not lie between" in message, message
    assert S.DEMONSTRATED_DEFICIT in message

    # The word never attaches to the losing pair even where the refusal is not
    # reached, and the same row with a coherent return renders and reads as the
    # deficit it is.
    assert S.DEMONSTRATED_EDGE not in WHY._figure(row)
    row["roi"] = -0.055
    rendered = WHY.render(record)
    assert "**-5.5%**, corrected -9.0% to -2.0% — demonstrated deficit" in rendered


def test_half_an_interval_cannot_fabricate_an_edge_by_being_half_an_interval(outputs):
    """**The check used to be opt-in, and the opt-out was one deleted key.**

    `verdict_disagreements` ran over the rows carrying *both* `adjusted_low`
    and `adjusted_high`, so carrying the keys was the condition for being
    checked and not carrying them was the way past. Deleting `adjusted_high`
    from one row of the committed record — and nothing else — published this
    in the headline of the document whose entire subject is whether the
    sentence may be said:

        high-major 24,691 bets, **+99.0%**, corrected +2.0% to unbounded —
        demonstrated edge

    A missing bound reads as `0.0`, so `[+0.02, missing]` excludes zero
    *above*; the return beside it was compared to nothing at all, because the
    row had opted itself out of the only comparison. The verdict check did not
    catch it either: the stored string and the fabricated interval agreed.

    Rows are now taken whole and classified by what they carry, so this row is
    refused twice over — for the maimed pair, and for the return sitting
    outside the `low`/`high` pair it still carries.
    """
    record = build(outputs)
    row = next(r for r in record["tiers"] if r["enough_evidence"])
    row["roi"] = +0.99
    row["adjusted_low"] = +0.02
    del row["adjusted_high"]
    row["verdict"] = S.DEMONSTRATED_EDGE
    assert WHY.verdict_of(row) == S.DEMONSTRATED_EDGE, (
        "the fabricated interval must still read as an edge, or this test is "
        "passing because the row stopped being dangerous rather than because "
        "the record is refused"
    )

    with pytest.raises(WHY.WhyError) as caught:
        WHY.render(record)
    message = str(caught.value)
    assert "adjusted_high" in message, message
    assert "Half an interval is not an interval" in message, message
    # Refused twice: the maimed corrected pair, and the return sitting outside
    # the uncorrected pair the row still carries. The second is what stops a
    # row keeping `adjusted_low`/`adjusted_high` coherent while `low`/`high`
    # hold numbers from another measurement, so it is asserted here rather
    # than left as a side effect.
    assert "`low`/`high`" in message, message
    assert "+99.0% does not lie between" in message, message

    # And with the bound restored to a pair no measurement disagrees with, the
    # same record renders — so the refusal is about the missing key and not
    # about this row being unrenderable for some other reason.
    row["roi"], row["adjusted_low"], row["adjusted_high"] = -0.055, -0.09, -0.02
    row["verdict"] = S.DEMONSTRATED_DEFICIT
    assert "+99.0%" not in WHY.render(record)


def test_stale_numbers_cannot_hide_under_the_uncorrected_bounds(outputs):
    """Both pairs a row carries are checked, not just the pair on the page.

    `_figure` prints `adjusted_low`/`adjusted_high`, so a coherence check that
    reads only those leaves `low`/`high` free to hold numbers from a different
    measurement — and they are the pair the corrected bounds are *recomputed
    from* on the next re-render, at which point the incoherence moves onto the
    page and nothing about the record changed to announce it.

    Here the printed pair agrees with the return and the uncorrected pair does
    not, so this row is refused by the `low`/`high` reading alone. A
    `printed_interval` that ignored the bounds it was handed and always read
    the corrected pair would pass it.
    """
    record = build(outputs)
    row = next(r for r in record["tiers"] if r["enough_evidence"])
    row["roi"] = -0.055
    row["adjusted_low"], row["adjusted_high"] = -0.09, -0.02
    row["low"], row["high"] = +0.30, +0.40
    row["verdict"] = S.DEMONSTRATED_DEFICIT

    printed = WHY.printed_interval(row)
    assert printed.return_sits_inside_its_own_interval, (
        "the pair on the page must agree with the return, or this test is "
        "passing on the check it is not about"
    )

    reasons = WHY.verdict_disagreements(record)
    mine = [r for r in reasons if r.startswith("tiers[")]
    assert len(mine) == 1, mine
    assert "`low`/`high`" in mine[0], mine[0]
    assert "-5.5% does not lie between" in mine[0], mine[0]
    with pytest.raises(WHY.WhyError):
        WHY.render(record)


def test_a_figure_with_no_interval_beside_it_is_refused_rather_than_printed(outputs):
    """A return and a verdict, and nothing qualifying either.

    Stripping all four bound keys leaves a row that prints `**+99.0%**,
    corrected unbounded to unbounded`, and the stored verdict agrees with the
    empty interval's reading, so every other check on the record passes it.
    That is the typed-figure defect this whole document exists to prevent,
    arrived at by deletion instead of by typing. A row carrying a claim must
    carry an interval to justify it.
    """
    record = build(outputs)
    row = next(r for r in record["tiers"] if r["enough_evidence"])
    row["roi"] = +0.99
    for key in ("low", "high", "adjusted_low", "adjusted_high"):
        del row[key]
    row["verdict"] = WHY.verdict_of(row)
    assert row["verdict"] == S.NO_DEMONSTRATED_EDGE, (
        "the stored verdict is set to what the empty interval reads on "
        "purpose, so the only check that can refuse this row is the new one"
    )

    reasons = WHY.verdict_disagreements(record)
    mine = [r for r in reasons if r.startswith("tiers[")]
    assert len(mine) == 1, mine
    assert "no interval of any kind" in mine[0], mine[0]
    assert "`roi`" in mine[0] and "`verdict`" in mine[0], mine[0]
    with pytest.raises(WHY.WhyError):
        WHY.render(record)


def test_deleting_both_printed_bounds_is_not_a_way_past_the_check(outputs):
    """**Keeping the other pair used to answer for the pair on the page.**

    The refusal above tested *"carries a claim and no pair at all"*, so a row
    that dropped `adjusted_low` and `adjusted_high` and kept `low` and `high`
    was carrying an interval as far as the check was concerned. It is not the
    interval anybody sees. `_figure` prints the **corrected** pair and
    `verdict_of` reads the sign off it, so the row publishes

        24,691 bets, **+99.0%**, corrected unbounded to unbounded

    with the uncorrected bounds it kept qualifying nothing on the page. The
    condition now names `PRINTED_BOUNDS`, so some other pair does not answer
    for it.
    """
    record = build(outputs)
    row = next(r for r in record["tiers"] if r["enough_evidence"])
    row["roi"] = +0.99
    del row["adjusted_low"]
    del row["adjusted_high"]
    row["low"], row["high"] = +0.80, +1.18
    row["verdict"] = WHY.verdict_of(row)

    whole, half, absent = WHY._bound_pairs_carried(row)
    assert whole == [("low", "high")] and not half, (
        "the row must still carry one whole pair, or this test is passing on "
        "the half-interval refusal instead of the one it is about"
    )
    assert WHY.PRINTED_BOUNDS in absent
    # What would be published, spelled out rather than described.
    printed = WHY._figure(row)
    assert "**+99.0%**" in printed and "corrected unbounded to unbounded" in printed

    reasons = WHY.verdict_disagreements(record)
    mine = [r for r in reasons if r.startswith("tiers[")]
    assert len(mine) == 1, mine
    assert "`adjusted_low`/`adjusted_high`" in mine[0], mine[0]
    assert "neither of" in mine[0], mine[0]
    assert "`low`/`high`" in mine[0], mine[0]
    with pytest.raises(WHY.WhyError):
        WHY.render(record)

    # Restored, the same record renders — so the refusal is about the two
    # missing keys and not about this row being unrenderable some other way.
    row["adjusted_low"], row["adjusted_high"] = +0.80, +1.18
    row["verdict"] = WHY.verdict_of(row)
    assert "**+99.0%**, corrected +80.0% to +118.0%" in WHY.render(record)


def test_the_three_lists_partition_the_bound_vocabulary(outputs):
    """Every pair is in exactly one of `whole`, `half`, `absent`.

    The defeat above existed because a pair could be in neither list, so
    *"does this row carry an interval"* was the only question a caller could
    ask. A fourth state — or a pair silently dropped from the classification —
    puts that question back.
    """
    record = build(outputs)
    rows = [row for _, row in WHY._rows_of_the_record(record)]
    rows += [
        {},
        {"low": 0.0},
        {"adjusted_high": 0.0},
        {"low": 0.0, "high": 0.0},
        {"adjusted_low": 0.0, "adjusted_high": 0.0, "low": 0.0, "high": 0.0},
    ]
    for row in rows:
        whole, half, absent = WHY._bound_pairs_carried(row)
        together = whole + half + absent
        assert sorted(together) == sorted(WHY.INTERVAL_BOUND_KEYS), together
        assert len(together) == len(set(together)) == len(WHY.INTERVAL_BOUND_KEYS)

    assert WHY._bound_pairs_carried({}) == ([], [], list(WHY.INTERVAL_BOUND_KEYS))


def test_a_blind_baseline_below_the_floor_prints_no_number_and_decides_nothing(outputs):
    """**The one number on the page nothing had checked.**

    `_blind_lines` printed a bolded return for every row the record carried,
    with no floor test of its own — while refusal 3 of
    `verdict_disagreements` skips below-floor rows on the stated grounds that
    below the floor there is no number on the page. The two together published
    an unchecked figure.

    Worse, `worst_blind` was the maximum over every row, and the sentence it
    decides is this document's *the model carries information* verdict. One
    40-bet baseline carrying a large return turns *"All 3 measured tiers
    return more than every one of them"* into *"**No measured tier returns
    more than all of them**, which is a worse result than the model being
    merely unprofitable"* — the strongest negative statement in the file,
    reached by a row that clears nothing.
    """
    record = build(outputs)
    before = WHY.render(record)
    flipped = "No measured tier returns more than all of them"
    assert "return more than every one of them" in before
    assert flipped not in before

    thin = {
        "name": "always the favourite",
        "market": "moneyline",
        "tier": "high_major",
        "bets": 40,
        "clusters": 9,
        "cluster_unit": "game",
        "roi": +0.99,
        "low": +0.80,
        "high": +1.18,
        "adjusted_low": +0.80,
        "adjusted_high": +1.18,
        "looks": 1,
    }
    thin["enough_evidence"] = WHY.enough_evidence_of(thin)
    thin["verdict"] = WHY.verdict_of(thin)
    assert thin["enough_evidence"] is False
    record["blind"].append(thin)

    # The row really would have decided the sentence: it is the largest return
    # in the section by a distance, and the only one above zero.
    assert max(b["roi"] for b in record["blind"]) == pytest.approx(+0.99)
    assert max(b["roi"] for b in record["blind"] if WHY.enough_evidence_of(b)) < 0

    assert WHY.verdict_disagreements(record) == [], (
        "the planted row must leave the record self-consistent, or this test "
        "passes on a refusal rather than on the floor rule"
    )
    after = WHY.render(record)
    assert "+99.0%" not in after
    assert flipped not in after, (
        "a 40-bet baseline decided this document's strongest negative "
        "sentence"
    )
    assert "return more than every one of them" in after
    # Named, with the phrase — not dropped, which would be a document that
    # does not admit what its own record holds.
    assert (
        "- `high_major / moneyline / always the favourite`: not enough "
        "evidence (40 bets, below the 200 declared in advance)"
    ) in after


def test_no_row_below_the_floor_prints_a_number_in_any_of_the_three_places(outputs):
    """The module docstring's rule 1, over all three printers it names.

    `_figure` obeyed it. `_blind_lines` and the forecast advantage column did
    not, and both are places a reader meets a figure read off a row. A thin
    row is planted in each with a return no other line in the document
    carries, and the rendered text is read back for it.
    """
    record = build(outputs)

    tier = next(t for t in record["tiers"] if t["enough_evidence"])
    tier["bets"] = 40
    tier["roi"] = +0.777
    tier["low"] = tier["adjusted_low"] = +0.60
    tier["high"] = tier["adjusted_high"] = +0.95
    tier["enough_evidence"] = WHY.enough_evidence_of(tier)
    tier["verdict"] = WHY.verdict_of(tier)

    blind = dict(record["blind"][0])
    blind["bets"] = 40
    blind["roi"] = +0.888
    blind["low"] = blind["adjusted_low"] = +0.70
    blind["high"] = blind["adjusted_high"] = +0.99
    blind["enough_evidence"] = WHY.enough_evidence_of(blind)
    blind["verdict"] = WHY.verdict_of(blind)
    record["blind"].append(blind)

    forecast_tier = next(
        t
        for t in record["forecast"]["tiers"]
        if t["rows"] >= S.MINIMUM_BETS and t.get("advantage_over_raw")
    )
    advantage = forecast_tier["advantage_over_raw"]
    advantage["rows"] = 40
    advantage["value"] = +0.09999
    advantage["low"] = advantage["adjusted_low"] = +0.08
    advantage["high"] = advantage["adjusted_high"] = +0.11
    advantage["enough_evidence"] = WHY.enough_evidence_of(advantage)
    advantage["verdict"] = WHY.verdict_of(advantage)
    assert forecast_tier["rows"] >= S.MINIMUM_BETS, (
        "the tier must still be in the forecast table, or its advantage cell "
        "is never rendered and this leg tests nothing"
    )

    assert WHY.verdict_disagreements(record) == [], (
        "every planted row must leave the record self-consistent, or this "
        "test passes on a refusal rather than on the floor rule"
    )
    rendered = WHY.render(record)
    for number in ("+77.7%", "+88.8%", "+0.09999"):
        assert number not in rendered, (
            f"{number} is printed for a 40-bet row, below the "
            f"{S.MINIMUM_BETS:,} declared in advance"
        )
    phrase = (
        f"not enough evidence (40 bets, below the {S.MINIMUM_BETS:,} "
        "declared in advance)"
    )
    assert rendered.count(phrase) >= 3, rendered.count(phrase)
    assert "no number below the floor declared in advance" in rendered


def test_the_gaps_this_guard_still_has_are_the_ones_written_down(outputs):
    """What `verdict_disagreements` still lets through, asserted **open**.

    A limitation recorded as a passing assertion goes red the day it is closed
    and has to be re-read; a limitation recorded only in a docstring quietly
    becomes a false claim — which is how the sentence *"Every row of the
    record is examined. There is no opt-in."* came to stand over a function
    with two ways past it. None of these is a waiver.

    1. Refusal 3 does not run below the floor, so a thin row may carry a
       return outside its own bounds. It is not free to close: the committed
       record itself holds such rows, because `stats.roi_interval` returns
       `±inf` for a single-cluster cell, JSON cannot carry an infinity, and
       `interval_from_row` reads the stored null back as `0.0`. Nothing below
       the floor is printed as a number, which is what makes it survivable.
    2. The population is the sections `_rows_of_the_record` names. A section
       that exists only in a record edited on disk is examined by nothing here
       — and printed by nothing either, because `render` reads by name.
    3. Only bounds, returns and verdicts are compared. Every other number the
       document prints is checked against nothing by this function.
    """
    doc = WHY.verdict_disagreements.__doc__ or ""
    ledger = doc.split("## What still gets through", 1)
    assert len(ledger) == 2, "the guard's docstring no longer writes its gaps down"
    assert re.findall(r"^ {4}(\d+)\. ", ledger[1], re.M) == ["1", "2", "3"], (
        "the written-down list changed; every gap below is asserted open, so "
        "one of them has been closed or a new one added without a case here"
    )

    # Gap 1, and the measurement behind leaving it open.
    committed = build(outputs)
    incoherent = [
        label
        for label, row in WHY._rows_of_the_record(committed)
        for pair in WHY._bound_pairs_carried(row)[0]
        if not WHY.printed_interval(row, bounds=pair).enough_evidence
        and not WHY.printed_interval(
            row, bounds=pair
        ).return_sits_inside_its_own_interval
    ]
    assert incoherent, (
        "no thin row of the committed record has a return outside its stored "
        "bounds any more, so gap 1 may be closeable — re-measure before "
        "deleting the skip"
    )

    record = build(outputs)
    row = next(r for r in record["tiers"] if r["enough_evidence"])
    row["bets"] = 40
    row["roi"] = +0.99
    row["low"] = row["adjusted_low"] = -0.09
    row["high"] = row["adjusted_high"] = -0.02
    row["enough_evidence"] = WHY.enough_evidence_of(row)
    row["verdict"] = WHY.verdict_of(row)
    assert [r for r in WHY.verdict_disagreements(record) if r.startswith("tiers[")] == []
    assert "+99.0%" not in WHY.render(record)

    # Gap 2: a section the generator never writes.
    record = build(outputs)
    record["invented"] = [
        {
            "name": "planted",
            "market": "moneyline",
            "tier": "high_major",
            "bets": 24691,
            "clusters": 900,
            "roi": +0.99,
            "low": -0.09,
            "high": -0.02,
            "adjusted_low": -0.09,
            "adjusted_high": -0.02,
            "enough_evidence": True,
            "verdict": S.DEMONSTRATED_EDGE,
        }
    ]
    assert WHY.verdict_disagreements(record) == []
    assert "+99.0%" not in WHY.render(record)

    # Gap 3: a number that is neither a bound, a return, nor a verdict.
    record = build(outputs)
    record["backtest"]["calibration"]["overall"]["points"] = 9.0
    assert WHY.verdict_disagreements(record) == []
    assert "**900.0 pp overconfident**" in WHY.render(record)


def test_the_bound_keys_this_guard_knows_about_are_the_ones_the_record_writes(outputs):
    """`INTERVAL_BOUND_KEYS` is the whole vocabulary, and it is derived, not
    trusted.

    The rows examined are now every row of the record, so the one remaining
    place a check could be narrowed by a one-line edit is this tuple: drop
    `("low", "high")` and every row carrying only that pair stops being
    compared to its own return. The expectation here is read off the record the
    generator actually wrote — every key in it that names a bound — so the
    narrowing is red rather than silent.
    """
    record = build(outputs)
    written = {
        key
        for _, row in WHY._rows_of_the_record(record)
        for key in row
        if key.endswith("low") or key.endswith("high")
    }
    known = {key for pair in WHY.INTERVAL_BOUND_KEYS for key in pair}

    assert written, "no row of the record names a bound at all"
    assert known == written, (
        f"`INTERVAL_BOUND_KEYS` knows about {sorted(known)} and the record "
        f"writes {sorted(written)}. A bound key the record writes and this "
        "tuple does not name is a pair no coherence check ever reads; a key "
        "this tuple names and the record does not write is a check that has "
        "quietly stopped applying to anything."
    )
    for low_key, high_key in WHY.INTERVAL_BOUND_KEYS:
        assert low_key.endswith("low") and high_key.endswith("high"), (
            f"({low_key}, {high_key}) is not a (low, high) pair, and "
            "`_bound_pairs_carried` reads it in that order"
        )


def test_every_row_of_the_record_that_carries_a_figure_is_walked(outputs):
    """The population the coherence check runs over is derived from the record.

    `_rows_of_the_record` names its sections — `tiers`, `cells`, `pooled`,
    `blind`, `every_market`, the forecast's advantage blocks. A name dropped
    from that list, or a section added to the record and not added to it, is a
    corner of the document nothing checks, and it looks like nothing at all.
    So the record is descended in full here and every mapping in it that
    carries a bound or a claim must come back from the walk — matched by
    identity, so a walk that rebuilds rows instead of yielding them fails too.

    **A claim, not just a verdict.** This used to look for a bound key or the
    word `verdict`, which left a mapping carrying only `roi` or `value`
    outside the population it derives — and a return with nothing beside it is
    precisely the row refusal 2 exists for, so a section of them was neither
    walked nor missed. The definition is now the bound keys plus
    `CLAIM_KEYS`, the same vocabulary `verdict_disagreements` reads.
    """
    record = build(outputs)
    bound_keys = {key for pair in WHY.INTERVAL_BOUND_KEYS for key in pair}
    claim_keys = set(WHY.CLAIM_KEYS)
    walked = {id(row) for _, row in WHY._rows_of_the_record(record)}
    carrying: list[str] = []
    carrying_ids: set[int] = set()
    missed: list[str] = []

    def descend(node: object, path: str) -> None:
        if isinstance(node, Mapping):
            if (bound_keys | claim_keys) & set(node):
                carrying.append(path)
                carrying_ids.add(id(node))
                if id(node) not in walked:
                    missed.append(path)
            for key, value in node.items():
                descend(value, f"{path}.{key}" if path else str(key))
        elif isinstance(node, Sequence) and not isinstance(node, (str, bytes)):
            for index, value in enumerate(node):
                descend(value, f"{path}[{index}]")

    descend(record, "")

    assert carrying, "the record carries no figures at all, so nothing was checked"
    assert not missed, (
        f"{len(missed)} of {len(carrying)} rows carrying a bound or a claim "
        f"are never reached by `_rows_of_the_record`: {sorted(missed)[:8]}. "
        "Every check in `verdict_disagreements` runs over that walk, so a row "
        "it does not reach can hold any pair of numbers it likes."
    )
    # The record reaches `every_market` by two paths — its own key and the last
    # entry of `pooled` — so the two are compared as sets of rows, not as
    # counts of paths. Equality in the other direction matters too: a walk
    # yielding a row that carries no figure at all is a walk that has started
    # examining something the document does not print.
    assert walked == carrying_ids, (
        f"the walk yields {len(walked)} distinct rows and {len(carrying_ids)} "
        "in the record carry a figure; a row yielded that carries none means "
        "the two are no longer the same population"
    )


def test_a_sample_size_typed_over_the_floor_never_promotes_a_cell(outputs):
    """`enough_evidence` is derived from the count too. A row hand-flagged as
    having cleared the floor it does not clear would otherwise walk into the
    headline's population carrying a number it is not allowed to print."""
    record = build(outputs)
    thin = next(row for row in record["tiers"] if not row["enough_evidence"])
    assert thin["bets"] < S.MINIMUM_BETS
    thin["enough_evidence"] = True
    with pytest.raises(WHY.WhyError) as caught:
        WHY.render(record)
    assert "enough_evidence" in str(caught.value)
    assert WHY.enough_evidence_of(thin) is False
    assert "%" not in WHY._figure(thin)


def test_a_demonstrated_deficit_is_named_and_never_folded_into_the_edges(outputs):
    """`demonstrated_edges` and `demonstrated_deficits` return disjoint lists.
    The NHL lab's headline announced a result had *survived and replicated* on a
    market returning −6.6%, because its predicate never read the sign."""
    loser = WHY.cell(
        _tier(roi=-0.30, low=-0.35, high=-0.25, standard_error=0.02), looks=1
    )
    assert loser["verdict"] == S.DEMONSTRATED_DEFICIT
    assert WHY.demonstrated_edges([loser]) == []
    assert WHY.demonstrated_deficits([loser]) == [loser]
    line = WHY.headline({"tiers": [loser]})
    assert "demonstrated deficit" in line
    assert "shows a demonstrated edge" not in line


# --------------------------------------------------------------------------
# 4. Purity, freshness, and the committed document
# --------------------------------------------------------------------------


def test_the_report_is_a_pure_function_of_its_record(outputs):
    """Rendering reads no disk, so improving a sentence never costs a re-run of
    the measurement — and a report that can only be produced by re-running the
    measurement is a report nobody improves."""
    record = build(outputs)
    first = WHY.render(record)
    for path in WHY.evidence_paths(CBB, outputs).values():
        path.unlink()
    assert WHY.render(record) == first


def test_a_record_that_has_fallen_behind_the_evidence_says_so(outputs):
    """Purity buys one guarantee and was once read as buying a second.
    `what_we_can_claim`'s `--check` passed while the document it checked named
    a committed backtest of 118,050 graded bets as *not found*: the comparison
    was against the record, and the record predated the measurement."""
    record = build(outputs)
    assert WHY.stale_inputs(record) == []
    path = WHY.evidence_paths(CBB, outputs)["price backtest"]
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["generated_at"] = "2099-01-01T00:00:00Z"
    path.write_text(json.dumps(payload), encoding="utf-8")
    reasons = WHY.stale_inputs(record)
    assert reasons and "cbb_price_backtest.json" in reasons[0]


def test_a_record_that_cannot_answer_the_freshness_question_is_stale(outputs):
    """*"Could not check"* is reported as a failure, never as a pass. A check
    that treats an unanswerable question as an answer of "fine" is the shape of
    the defect, not the fix for it."""
    record = build(outputs)
    record.pop("evidence_inputs")
    assert WHY.stale_inputs(record)


def test_a_vanished_record_is_reported_as_vanished(outputs):
    record = build(outputs)
    WHY.evidence_paths(CBB, outputs)["forecast skill"].unlink()
    reasons = WHY.stale_inputs(record)
    assert reasons and "no longer exists" in reasons[0]


def test_a_record_of_another_version_is_refused_rather_than_rendered(outputs):
    record = build(outputs)
    record["record_version"] = WHY.RECORD_VERSION + 1
    with pytest.raises(WHY.WhyError):
        WHY.render(record)


def test_the_committed_document_carries_the_fence(outputs):
    """Without the markers the splice raises rather than appending, which is
    what stops the weekly loop producing a document that looks updated and is
    not. A document that lost its fence would silently stop being re-rendered."""
    text = DOC.read_text(encoding="utf-8")
    start = text.find(WHY.BEGIN_MARKER)
    stop = text.find(WHY.END_MARKER)
    assert 0 <= start < stop, (
        f"{DOC.name} carries no generated block, so nothing re-renders it and "
        "its figures are typed again."
    )


#: What the fence guard treats as a figure: **any digit at all**, anywhere
#: outside the generated block. Not a percent sign — that was the guard's
#: whole reach, and it is a guard against one spelling rather than against the
#: thing. `-4.3%` was caught; `-4.3 points`, `86,351 bets`, `0.043`, a
#: corrected interval written `[-0.100, +0.014]` and a bare `1.60` correction
#: factor were not, and every one of them is a number about this model that
#: nothing re-renders.
#:
#: A digit is a coarse net, and deliberately: this page's prose is about where
#: the numbers live, not what they are, so it carries none today and the cost
#: of the rule is that a future sentence wanting one must put it inside the
#: fence or argue here for an exception.
TYPED_FIGURE = re.compile(r"\d")


def outside_the_fence(text: str) -> str:
    """Everything in `text` the generator does not write."""
    return (
        text[: text.index(WHY.BEGIN_MARKER)]
        + text[text.index(WHY.END_MARKER) + len(WHY.END_MARKER) :]
    )


def typed_figures(text: str) -> list[str]:
    """Lines outside the fence that carry a figure nothing re-renders.

    **What this does not reach**, stated plainly rather than left to be
    discovered:

    * a figure **spelled in words** — *"the low-major tier lost four and a
      half percent"* carries no digit and passes here;
    * a **stale claim with no number in it** — *"the model beats the market in
      one tier"* is exactly as unre-rendered and exactly as invisible to a
      regex;
    * anything **inside** the fence. A figure typed between the markers is a
      different failure, and a different test catches it:
      `test_the_committed_document_matches_what_its_committed_record_renders_to`
      re-renders the record and compares, so the fence's contents are pinned to
      the record rather than to a spelling.

    So this is a net under one specific and repeated mistake — dropping a
    number into the prose around a generated block — and not a proof that the
    prose is true.
    """
    return [
        line
        for line in outside_the_fence(text).splitlines()
        if TYPED_FIGURE.search(line)
    ]


def test_no_figure_is_typed_outside_the_generated_fence(outputs):
    """The drift this cluster exists to prevent, in its last hiding place.

    Below the fence sat a note headed *"the figures in this section are
    historical"* which then hand-typed the tier's **current** return and
    corrected interval — `-4.3%, corrected -10.0% to +1.4%` — so a
    re-measurement moved the generated table above it and left the paragraph
    below saying what the tier used to read, under a heading promising it could
    not. A number outside the fence is a figure nothing re-renders.
    """
    typed = typed_figures(DOC.read_text(encoding="utf-8"))

    assert not typed, (
        f"{DOC.name} carries a figure outside its generated block: {typed!r}. "
        "Nothing re-renders those lines, so they are typed figures under a "
        "heading saying there are none. Put the figure inside the fence, where "
        "the generator writes it from the record."
    )


def test_the_fence_guard_catches_a_figure_written_without_a_percent_sign():
    """The guard's own regression test.

    It was `assert "%" not in outside`, which is a test for a **character**
    rather than for a figure: the same stale sentence rewritten as *"the
    low-major tier returned -0.043 over 34,720 bets"* sat outside the fence
    unnoticed, and so did the correction factor, the bet counts and every
    interval written in decimals. Each line below is the drift the guard was
    written for, in a spelling the old guard let through.
    """
    framing = "# A page\n\nProse with no figures in it.\n\n"
    fenced = f"{WHY.BEGIN_MARKER}\n\nlow-major -4.3%\n\n{WHY.END_MARKER}\n"

    assert typed_figures(framing + fenced) == []

    for stale in (
        "The low-major tier returned -0.043 over 34,720 bets.",
        "Corrected interval: [-0.100, +0.014].",
        "The family correction is x1.60.",
        "Measured over 86,351 bets.",
        "Historically the tier lost 4.3 points of return.",
    ):
        assert typed_figures(f"{framing}{fenced}{stale}\n") == [stale], stale

    # And the spelling the old guard did catch is still caught.
    assert typed_figures(f"{framing}{fenced}The tier reads -4.3%.\n") == [
        "The tier reads -4.3%."
    ]


def test_the_retraction_reads_its_current_figure_from_the_record(outputs):
    """The retracted claim is kept — the reason a claim was withdrawn is
    evidence about the claim — but only its WORDING and its date are carried in
    the source. Whether it still holds, and what the tier reads today, are read
    off the record, so the retraction cannot become the stale paragraph that
    the hand-written version of it was.

    On 2026-09-04's expanded store the retraction read *"It no longer holds"*,
    and this test pinned that sentence. On the full store measured 2026-09-05
    low-major is a demonstrated deficit again — 59,475 bets, -4.0%, corrected
    -8.0% to -0.1% — so the generator emits *"It still holds"* and the pinned
    sentence moved with the record rather than the record being made to match
    the pin. That is the whole design: the branch below is chosen by
    `verdict_of(current)` and nothing else, and both branches are still
    exercised against rows this test builds, so neither can be hard-coded.

    What the generator compares is the tier's VERDICT against the verdict the
    retracted sentence claimed. The retracted wording also said *"the only
    tier"*, and on the full store mid-major excludes zero as well, so the
    sentence's exclusivity does not survive even though its sign does. The
    generator does not read exclusivity and this test does not assert it.
    """
    record = build(outputs)
    tier_key = WHY.SUPERSEDED_CLAIM["tier"]
    current = next(row for row in record["tiers"] if row["tier"] == tier_key)
    assert WHY.verdict_of(current) == WHY.SUPERSEDED_CLAIM["verdict_claimed"], (
        "the committed record no longer reads the verdict the retracted claim "
        "made; re-derive this test's branch from the record rather than "
        "re-pinning the sentence"
    )
    rendered = WHY.render(record)
    heading = f"### A claim this document has retracted, recorded {WHY.SUPERSEDED_CLAIM['recorded_on']}"
    assert heading in rendered
    section = rendered[rendered.index(heading) :]
    assert WHY.SUPERSEDED_CLAIM["wording"] in section
    assert WHY._figure(current) in section, (
        "the retraction does not print what the record says the tier reads "
        "today, so it is a hand-typed figure again"
    )
    assert "**It still holds.**" in section
    assert "**It no longer holds.**" not in section

    # A DIFFERENT row that does NOT hold. Asserting only that the
    # committed tier's figure appears is not enough: that string is also what a
    # hard-coded sentence would print today, which is exactly the drift this
    # test exists to catch — measured, by hard-coding it and watching this pass.
    moved = WHY.cell(
        _tier(
            name=tier_key, tier=tier_key, bets=30_000,
            roi=-0.10, low=-0.16, high=-0.04, standard_error=0.05,
        ),
        looks=30,
    )
    assert moved["verdict"] == S.NO_DEMONSTRATED_EDGE, moved
    assert WHY._figure(moved) != WHY._figure(current)
    record["tiers"] = [moved]
    moved_section = WHY.render(record)
    moved_section = moved_section[moved_section.index(heading) :]
    assert "**It no longer holds.**" in moved_section
    assert WHY._figure(moved) in moved_section, (
        "the retraction prints a figure that does not move when the record "
        "does, so it is hard-coded"
    )
    assert WHY._figure(current) not in moved_section

    # Flip the same tier to the reading the retracted claim made, and the
    # retraction has to follow it rather than stay retracted.
    record = build(outputs)
    restored = WHY.cell(
        _tier(
            name=tier_key, tier=tier_key,
            roi=-0.30, low=-0.35, high=-0.25, standard_error=0.02,
        ),
        looks=1,
    )
    assert restored["verdict"] == WHY.SUPERSEDED_CLAIM["verdict_claimed"]
    assert WHY._figure(restored) != WHY._figure(current)
    record["tiers"] = [restored]
    section = WHY.render(record)
    section = section[section.index(heading) :]
    assert "**It still holds.**" in section
    assert "**It no longer holds.**" not in section
    assert WHY._figure(restored) in section, (
        "the retraction prints a figure that does not move when the record "
        "does, so it is hard-coded"
    )
    assert WHY._figure(current) not in section


def test_no_document_quotes_the_devigged_advantage_as_the_raw_one():
    """`docs/project_status.md` row 13 carried the figure this whole cluster is
    about: **-0.01312 [-0.01468, -0.01156]**, described as the comparison *"with
    the vig left in"*. `-0.01312` is the DE-VIGGED pooled advantage and those
    bounds are its UNCORRECTED ones — the wrong instrument and the un-widened
    interval, and a pooled all-of-Division-I figure besides. The strings are
    computed from the record here, so this stays a check on the measurement
    rather than a pin on a typo.
    """
    payload = json.loads(
        FS.record_path(CBB, OUTPUTS).read_text(encoding="utf-8")
    )
    devigged = payload["pooled"]["brier"]["advantage_over_devigged"]
    value = f"{devigged['value']:.5f}"
    uncorrected = f"[{devigged['low']:.5f}, {devigged['high']:.5f}]"
    documents = sorted((PROJECT_ROOT / "docs").rglob("*.md"))
    assert documents, "no documents to check"
    for path in documents:
        text = path.read_text(encoding="utf-8")
        assert value not in text, (
            f"{path.name} prints {value}, the pooled DE-VIGGED Brier advantage. "
            "This repository reports that comparison per tier and against the "
            "raw market, and never pools Division I into one headline figure."
        )
        assert uncorrected not in text, (
            f"{path.name} prints {uncorrected}, the UNCORRECTED bounds of the "
            "pooled de-vigged advantage. Every interval quoted in this "
            "repository is the family-corrected one."
        )


def test_the_status_row_for_the_regression_carries_the_measured_per_tier_figures():
    """The other half of the same row: having removed the wrong figure, the
    right ones have to be there and have to match the record. Read from
    `cbb_forecast_skill.json`, so the day the regression is re-run and this row
    is not rewritten, this fails."""
    payload = json.loads(
        FS.record_path(CBB, OUTPUTS).read_text(encoding="utf-8")
    )
    text = STATUS.read_text(encoding="utf-8")
    measured = [
        tier for tier in payload["by_tier"]
        if int(tier.get("rows") or 0) >= S.MINIMUM_BETS
    ]
    assert len(measured) == 3, [t["label"] for t in measured]
    for tier in measured:
        raw = tier["brier"]["advantage_over_raw"]
        printed = (
            f"{raw['value']:.5f}, corrected "
            f"{raw['adjusted_low']:.5f} to {raw['adjusted_high']:.5f}"
        )
        assert printed in text, (
            f"docs/project_status.md does not carry {tier['label']}'s measured "
            f"advantage as `{printed}`, so the row says something the record "
            "does not."
        )
        assert f"{int(raw['rows']):,} rows" in text, (
            f"{tier['label']}'s figure in docs/project_status.md carries no "
            "sample size beside it"
        )


def test_the_committed_document_matches_what_its_committed_record_renders_to(outputs):
    """The pin the missing generator cost. The fenced block in the document is
    compared against a fresh render of the record committed beside it, so a
    hand-edit inside the fence — the exact way the old document acquired its
    wrong forecast-skill interval — fails the build."""
    rendered = WHY.render(committed_record())
    body = "\n".join(
        line for line in rendered.splitlines() if not line.startswith("# ")
    ).strip()
    text = DOC.read_text(encoding="utf-8")
    block = text[
        text.index(WHY.BEGIN_MARKER) + len(WHY.BEGIN_MARKER) : text.index(WHY.END_MARKER)
    ].strip()
    assert block == body, (
        f"{DOC.name}'s generated block is not what its run record renders to. "
        "Re-render it with scripts/run_why_the_model.py --splice-into rather "
        "than editing it: an edit here is lost at the next re-render, and "
        "until then it is a hand-typed number under a line saying there are "
        "none."
    )


def _pair_to_check(tmp_path: Path) -> tuple[Path, Path]:
    """A record/report pair on disk for `--check` to read — the committed one
    when it is committed, and one BUILT from the committed evidence otherwise.

    Never skips. When the pair is absent the generator is run to produce it, so
    a checkout that has not been generated is generated rather than excused,
    and deleting the committed pair cannot turn this gate off.
    """
    record = WHY.record_path(CBB, OUTPUTS)
    report = WHY.report_path(CBB, OUTPUTS)
    if record.is_file() and report.is_file():
        return record, report
    record, report = tmp_path / "record.json", tmp_path / "report.md"
    built = run_script(
        "--competition", "cbb", "--record", str(record), "--report", str(report)
    )
    assert built.returncode == 0, built.stdout + built.stderr
    return record, report


def test_check_passes_on_the_committed_pair_and_fails_on_a_hand_edit(tmp_path):
    """`--check` is the gate. It compares the report on disk against a fresh
    render of its record, and a hand-edited generated file survives exactly one
    re-render."""
    record, report = _pair_to_check(tmp_path)
    passing = run_script(
        "--competition", "cbb", "--record", str(record), "--report", str(report),
        "--check",
    )
    assert passing.returncode == 0, passing.stdout + passing.stderr

    edited = tmp_path / "edited.md"
    edited.write_text(
        report.read_text(encoding="utf-8").replace("bets", "wagers"),
        encoding="utf-8",
    )
    completed = run_script(
        "--competition", "cbb",
        "--record", str(record),
        "--report", str(edited),
        "--check",
    )
    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert "edited by hand" in completed.stderr or "does not match" in completed.stderr


def test_a_figure_planted_in_the_record_is_refused_rather_than_published(tmp_path):
    """**The record is not the source of truth.**

    Nothing used to re-derive `data/outputs/cbb_why_the_model.json` from the
    three measurement records, and the document is a pure function of it — so a
    figure typed into the record reached the published document and `--check`
    passed, because the document matched the record and the record matched
    itself. Here a tier's return is doubled in a copy of the record and every
    other number is left consistent with it; the check has to re-ask the
    measurement to notice.
    """
    record, report = _pair_to_check(tmp_path)
    payload = json.loads(record.read_text(encoding="utf-8"))
    planted = tmp_path / "planted.json"
    tier = payload["tiers"][0]
    tier["roi"] = (tier["roi"] or 0.0) * 2 - 0.001
    planted.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    completed = run_script(
        "--competition", "cbb",
        "--record", str(planted),
        "--report", str(report),
        "--check",
    )
    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert "not what the measurement records on disk produce" in completed.stderr
    assert "tiers" in completed.stderr


def test_a_planted_figure_is_refused_on_rerender_too_and_writes_nothing(tmp_path):
    """`--rerender` is the other door into the document, and it renders from
    the record without rebuilding it. It re-derives and compares as well, and
    it writes no report when the comparison fails: a refusal that has already
    overwritten the good document is not a refusal."""
    record, _ = _pair_to_check(tmp_path)
    payload = json.loads(record.read_text(encoding="utf-8"))
    payload["backtest"]["bets_graded"] = int(payload["backtest"]["bets_graded"]) + 1
    planted = tmp_path / "planted.json"
    planted.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    out = tmp_path / "out.md"

    completed = run_script(
        "--competition", "cbb",
        "--record", str(planted),
        "--report", str(out),
        "--rerender",
    )
    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert "backtest" in completed.stderr
    assert not out.exists(), "the refusal wrote the report anyway"


def test_the_committed_record_is_what_the_committed_evidence_produces(outputs):
    """The same question asked of the pair in the repository, in-process.

    `rederivation_differences` raises rather than returning an empty list when
    a measurement record cannot be read, so an unreadable instrument is never
    reported here as agreement.
    """
    assert WHY.rederivation_differences(
        committed_record(), competition=CBB, output_dir=OUTPUTS
    ) == []


# --------------------------------------------------------------------------
# 5. The pipeline actually re-renders it
# --------------------------------------------------------------------------


@pytest.fixture
def lab(tmp_path: Path) -> dict:
    """A complete, empty lab, built by the weekly loop's own test helpers.

    Imported rather than re-implemented: a second copy of the harness is a
    copy that drifts from what the loop actually needs, and then this test
    passes because it stopped exercising the loop rather than because the loop
    is right. `tests/` is on `sys.path` under pytest, and
    `test_ratings_fit_is_well_posed.py` imports `test_fit_ratings` the same way.
    """
    import test_weekly_loop as WL

    tree = {
        name: tmp_path / name
        for name in ("outputs", "processed", "manual", "scripts")
    }
    for directory in tree.values():
        directory.mkdir(parents=True, exist_ok=True)
    WL.write_ledger(tree["outputs"] / WL.E.LEDGER_FILENAME)
    (tree["manual"] / WL.promotion.CRITERIA_FILENAME).write_text(
        (PROJECT_ROOT / "data" / "manual" / WL.promotion.CRITERIA_FILENAME).read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    WL.staging.save(WL.staging.StagingProviderPolicy(), tree["manual"])
    return tree


def _loop_invocation_of_the_generator(
    lab: dict, sentinel: Path, *extra: str
) -> list[str]:
    """Run the whole weekly loop with every sibling stubbed, and return the
    argument list the generator was actually invoked with.

    The generator's stub records `sys.argv[1:]` and nothing else, so the
    sentinel exists **only** if the loop reached a subprocess for it.

    **The stub is installed under this file's own name for the generator, not
    under whatever `run_weekly_loop.WHY_SCRIPT` happens to say.** It used to be
    the constant, which made every test below a test that *something* ran:
    repoint `WHY_SCRIPT` at `run_price_backtest.py` and the stub follows it
    there, the sentinel is written by the wrong program, the argument
    assertions pass, and the edge document stops being regenerated with the
    suite green. `SCRIPT` is the path the rest of this file executes for real —
    it is the program that writes the record and splices the document — so
    stubbing *it* is what makes the sentinel evidence about identity and not
    just about activity.
    """
    import test_weekly_loop as WL

    assert WL.LOOP.WHY_SCRIPT == SCRIPT.name, (
        f"the weekly loop runs `{WL.LOOP.WHY_SCRIPT}` for the edge document "
        f"and the generator this file pins is `{SCRIPT.name}`. The loop is "
        "re-rendering something else, so `docs/"
        f"{Path(WHY.DOC_RELATIVE).name}` is regenerated by nothing."
    )
    WL.with_siblings(lab)
    WL.stub_script(
        lab,
        SCRIPT.name,
        body=(
            "import json, pathlib\n"
            f"pathlib.Path({str(sentinel)!r}).write_text("
            "json.dumps(sys.argv[1:]), encoding='utf-8')\n"
        ),
    )
    exit_code = WL.run(lab, *extra)
    assert exit_code in (0, 1), f"the loop crashed rather than reporting: {exit_code}"
    assert sentinel.is_file(), (
        f"the weekly loop finished without ever running `{SCRIPT.name}`. "
        f"`docs/{Path(WHY.DOC_RELATIVE).name}` says it is regenerated every "
        "week; nothing regenerated it, so every figure in it is as old as the "
        "last time somebody ran the script by hand."
    )
    return json.loads(sentinel.read_text(encoding="utf-8"))


def test_the_weekly_loop_runs_the_generator(lab, tmp_path):
    """*"Regenerated by the pipeline"* is a claim about a file, so it is
    checked by **running the pipeline**.

    This test used to be four `assert <string> in LOOP.read_text()` greps over
    the loop's source. Every one of them is satisfied by a comment: delete the
    `run_script(WHY_SCRIPT, ...)` call, leave the constant and the words
    `--splice-into` and `WHY.DOC_RELATIVE` behind in prose, and the document
    silently stops being re-rendered with the suite green — the pipeline step
    withdrawn behind a dead reference, which is the same shape as the defect
    this whole cluster exists to close (a document that said it was generated
    while nothing generated it).

    So: the real `main()`, every sibling stubbed the way `test_weekly_loop.py`
    stubs them, and an assertion that the generator was **invoked** and told
    which document to splice into.
    """
    import test_weekly_loop as WL

    sentinel = tmp_path / "the-generator-ran.json"
    argv = _loop_invocation_of_the_generator(lab, sentinel)

    assert SCRIPT.is_file(), "the loop names a script that is not in the repository"

    # The identity check, made structural rather than by name: the script the
    # loop names must be one that can actually splice this document. A constant
    # repointed at a program with no `splice` — or at one splicing a different
    # document — is caught here even if it happened to be named plausibly.
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    try:
        generator = __import__(Path(WL.LOOP.WHY_SCRIPT).stem)
    finally:
        sys.path.pop(0)
    assert hasattr(generator, "splice"), (
        f"`{WL.LOOP.WHY_SCRIPT}` has no `splice`, so whatever the loop is "
        "running every week, it is not the program that rewrites the fenced "
        "body of the edge document"
    )
    assert generator.WHY.DOC_RELATIVE == WHY.DOC_RELATIVE, (
        "the script the loop runs resolves the edge document from a different "
        "module than this test does"
    )
    assert "--splice-into" in argv, (
        "the loop runs the generator but never asks it to splice, so the "
        "record is refreshed and the document a human reads is not"
    )
    spliced_into = Path(argv[argv.index("--splice-into") + 1])
    assert spliced_into == PROJECT_ROOT / WHY.DOC_RELATIVE, (
        f"the loop splices into {spliced_into}, which is not the document "
        f"`why_the_model.DOC_RELATIVE` names ({WHY.DOC_RELATIVE}). The two "
        "having drifted apart means the loop re-renders a page nothing else "
        "is looking at."
    )
    assert "--output-dir" in argv and argv[argv.index("--output-dir") + 1] == str(
        lab["outputs"]
    ), "the generator was pointed at a different output tree from the run's"
    assert "--competition" in argv and argv[argv.index("--competition") + 1] == CBB.key


def test_the_loop_records_the_generator_step_as_a_step_that_ran(lab, tmp_path):
    """And it appears in the run record, so a week it did not run is visible.

    A step that silently no-ops is worse than one that fails: the record is
    what a Monday morning reader checks, and a re-render missing from it is how
    a stale document goes unnoticed for a season.
    """
    import test_weekly_loop as WL

    sentinel = tmp_path / "the-generator-ran.json"
    _loop_invocation_of_the_generator(lab, sentinel)
    steps = WL.steps_from(lab)

    named = [name for name in steps if "edge document" in name]
    assert named, (
        f"no step in the run record re-renders the edge document: {sorted(steps)}"
    )
    for name in named:
        assert steps[name] == WL.LOOP.OK, f"{name} finished {steps[name]}"


def test_the_loop_can_be_pointed_at_another_document_and_says_which(lab, tmp_path):
    """`--why-doc` exists so a test tree with no `docs/` can run the loop.

    It is asserted here because it is the argument that makes the assertion
    above meaningful: the default is not a hardcoded string that happens to
    match, it is a resolved path that a flag can move.
    """
    elsewhere = tmp_path / "somewhere_else.md"
    sentinel = tmp_path / "the-generator-ran.json"
    argv = _loop_invocation_of_the_generator(
        lab, sentinel, "--why-doc", str(elsewhere)
    )

    assert Path(argv[argv.index("--splice-into") + 1]) == elsewhere


def test_the_splice_refuses_a_document_with_no_fence(tmp_path):
    """Appending would leave a document that looks updated and is not."""
    sys.path.insert(0, str(PROJECT_ROOT / "scripts"))
    try:
        import run_why_the_model as program
    finally:
        sys.path.pop(0)
    doc = tmp_path / "doc.md"
    doc.write_text("# A document with no markers\n", encoding="utf-8")
    with pytest.raises(program.WhySpliceError):
        program.splice(doc, "# Title\n\nbody\n")
    assert doc.read_text(encoding="utf-8") == "# A document with no markers\n"
