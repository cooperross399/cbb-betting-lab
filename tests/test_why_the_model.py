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

import copy
import difflib
import json
import re
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from cbb_betting_lab import forward_evidence as FE
from cbb_betting_lab import restatement as RESTATEMENT
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


def read_back(record: Mapping, tmp_path: Path) -> dict:
    """`record`, through the file the production path actually writes it to.

    `WHY.write_record` then `WHY.read_record`, not `copy.deepcopy` and not a
    hand-rolled `json.dumps` beside them: the difference this exists to expose
    is precisely the difference between the dict `build_record` returns and the
    dict that comes back off disk, and only the production pair is guaranteed
    to *be* that difference. A copy of the dumping options spelled out here
    would drift from `write_record` and start round-tripping something no run
    ever wrote.
    """
    return WHY.read_record(WHY.write_record(record, tmp_path / "round_trip.json"))


def rendered_both_ways(record: Mapping, tmp_path: Path) -> str:
    """`render(record)` — asserted to be the SAME document read back off disk.

    **Every other test in this file builds the record in memory and renders
    that**, so until this existed no test in the file could see a renderer that
    reads anything but the record's values. One did: `_forecast_lines` labelled
    the worst claimed-edge bucket with `row is worst`, an object-identity test
    against `block["worst_bucket"]`, and `json.loads` gives that key an object
    of its own. In memory three lines read `worst-returning bucket`; off disk
    none of them did.

    That is not a cosmetic difference. `scripts/run_why_the_model.py` writes
    the record with `write_record` and the document from the record **in
    memory**; the next `--check` run reads the record back and renders it, so
    the two disagree and the script exits 1 with *"does not match what ...
    renders to. Re-render it rather than editing it"* — accusing a hand edit
    nobody made, on a document no re-render can fix.

    So the assertion is equality of the two documents, which is the assertion
    that makes `render`'s docstring — *"The document, as a pure function of the
    record"* — true rather than nearly true. Anything the renderer reads that
    survives `json.dumps`/`json.loads` unchanged passes it; anything it reads
    off the object graph does not.
    """
    in_memory = WHY.render(record)
    through_disk = WHY.render(read_back(record, tmp_path))
    if in_memory != through_disk:
        diff = "\n".join(
            difflib.unified_diff(
                in_memory.splitlines(),
                through_disk.splitlines(),
                fromfile="rendered from the record in memory",
                tofile="rendered from the same record read back off disk",
                lineterm="",
                n=1,
            )
        )
        raise AssertionError(
            "`render` is not a pure function of the record: the same record "
            "renders two different documents before and after it is written "
            "and read back. Something in the renderer is reading the object "
            "graph — an `is` against another key of the record, a cached "
            "object — rather than the values. This is what makes "
            "`run_why_the_model.py --check` fail on a document nobody "
            f"touched.\n{diff[:4000]}"
        )
    return in_memory


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
    # THE TRIPWIRE, AND WHY IT NO LONGER NAMES A VERDICT.
    #
    # This asserted `verdict_of(row) == DEMONSTRATED_EDGE`, so that a green test
    # could not mean "the row stopped being dangerous" instead of "the record
    # is refused". It fired on 2026-09-15, doing exactly its job: a second door
    # closed underneath it. `RoiInterval.survives_correction` now refuses any
    # pair that is not an interval, and a missing bound reads 0.0, so the
    # fabricated pair `[+0.02, 0.0]` is INVERTED rather than merely zero-width
    # and no longer reads as an edge anywhere. The old expectation had itself
    # been produced by the defect that fix closed: `0.02 <= 0` is False, so the
    # single `not (low <= 0 <= high)` clause called that pair an edge.
    #
    # So the tripwire now asserts the DANGER rather than the verdict that used
    # to follow from it. What made the deleted key dangerous is that the pair
    # the row publishes excludes zero by arithmetic while being compared to
    # nothing — and that is still exactly true. A row that stopped satisfying
    # this would still make the test below vacuous, which is the whole point of
    # asserting anything here.
    assert "adjusted_high" not in row
    published = WHY.printed_interval(row)
    assert published.low > 0.0 >= published.high, (
        "the pair this row would PUBLISH no longer excludes zero from above "
        f"({published.low} to {published.high}), so this is not the dangerous "
        "row the test is named for and the refusal below proves nothing"
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


#: The claimed-edge buckets the round-trip fixtures plant, by what they make
#: separately observable. Two rows whose worst-by-return and
#: whose-interval-is-below-zero are DIFFERENT rows, because a fixture in which
#: the two coincide cannot tell the two labels apart — and the label is the
#: thing the round trip broke.
ROUND_TRIP_BUCKETS: dict = {
    "one measured bucket": [(0.20, float("inf"), -0.09, (-0.10, -0.08))],
    "worst is not the deficit": [
        (0.0, 0.02, -0.20, (-0.45, 0.05)),
        (0.02, 0.05, -0.05, (-0.065, -0.035)),
    ],
}


def _plant_round_trip_buckets(outputs: Path, shape: str) -> None:
    """Give every forecast cell the buckets `shape` names, in every tier."""
    cells = [_bucket_cell(*args) for args in ROUND_TRIP_BUCKETS[shape]]
    _plant_per_tier(
        outputs,
        {
            label: cells
            for label in ("high_major", "mid_major", "low_major", "every tier pooled")
        },
    )


@pytest.mark.parametrize("shape", sorted(ROUND_TRIP_BUCKETS))
def test_the_page_is_the_same_document_after_the_record_is_written_and_read_back(
    outputs, tmp_path, shape
):
    """**The record is written and read back, and the page must not move.**

    The defect: `_forecast_lines` found the worst claimed-edge bucket with
    `row is worst`, an identity test against `block["worst_bucket"]`. That key
    holds the very object `measured_buckets` holds while the record is the dict
    `build_record` returned, and a different object with the same value once
    the record has been through JSON — which is every path that renders a
    record this repository has written: `--check`, `--rerender`, and
    `test_the_committed_document_matches_what_its_committed_record_renders_to`,
    all of which go through `read_record`.

    Both fixtures below make the two labels separately observable. *worst is
    not the deficit* plants a bucket returning -20% under an interval spanning
    zero and one returning -5% entirely below it, so the worst-returning row
    and the row that demonstrates the deficit are different rows and a renderer
    that labelled either of them by accident would print the wrong one. The
    assertion is not that the label is present — `test_the_page_names_the_
    bucket_whose_own_interval_is_below_zero` holds that — but that the two
    documents are IDENTICAL, which is the whole of what `render`'s docstring
    promises and the only form of the claim a value/identity confusion cannot
    satisfy by accident.
    """
    _plant_round_trip_buckets(outputs, shape)
    record = build(outputs)
    assert record["forecast"]["pooled"]["anti_predictive"]["measured_buckets"], (
        "the planted buckets must reach the record, or this test round-trips a "
        "document with no claimed-edge bucket in it and proves nothing"
    )

    page = rendered_both_ways(record, tmp_path)

    # The section this is about really is on the page, once per tier that
    # reaches it, with the label the identity test used to produce. A
    # round-trip equality that held because neither document said anything
    # would be the vacuous fixture this file refuses elsewhere — and the
    # expected count is read off the record rather than typed, so a fixture
    # that stops reaching a tier is a red test and not a quieter one.
    printing = [
        tier
        for tier in record["forecast"]["tiers"]
        if WHY._as_int(tier.get("rows")) >= S.MINIMUM_BETS
        and tier["anti_predictive"].get("measured_buckets")
    ]
    assert printing, "no tier reached the anti-predictiveness section"
    assert page.count("worst-returning bucket") == len(printing), page[:2000]
    assert page.count("claimed-edge bucket (") == len(printing) * (
        len(ROUND_TRIP_BUCKETS[shape]) - 1
    ), page[:2000]


def test_the_committed_evidence_renders_the_same_document_off_disk(tmp_path):
    """The same equality on the evidence this repository actually publishes.

    The fixtures above plant buckets the committed forecast record does not
    carry. This one asserts the property on the record built from `data/
    outputs/` — the pair `--check` reads every week — so the guarantee is not
    one that only holds on planted evidence.

    Built from the evidence rather than read from `data/outputs/cbb_why_the_
    model.json`: that committed record is a version behind this module and
    `render` refuses it by design, which is a different failure and one this
    test is not about.
    """
    rendered_both_ways(build(OUTPUTS), tmp_path)


@pytest.mark.parametrize(
    ("planted", "round_trip"),
    [(False, False), (True, False), (True, True)],
    ids=["as committed", "with buckets", "with buckets, read back off disk"],
)
def test_every_row_of_the_record_that_carries_a_figure_is_walked(
    outputs, tmp_path, planted, round_trip
):
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

    **And it runs over the record READ BACK OFF DISK**, which is the arm that
    matters. Both in-memory arms passed over a walk that reached
    `anti_predictive.measured_buckets` and nothing else, because in that one
    shape `worst_bucket` and `deficit_buckets[i]` are the *same objects* as
    entries of that list — the walk's own comment said so and used it as the
    justification for one append. `json.loads` gives each of them an object of
    its own, and every path this repository renders from goes through
    `read_record`: ten rows on a two-bucket record, the ones a hand-edit of the
    file would touch, were examined by nothing. An identity-matched coverage
    test over a record whose identities coincide asserts full coverage over the
    one shape in which coverage is free.
    """
    if planted:
        # **Run once over a record that HOLDS the rows this walk gained.** The
        # committed forecast record is version 4, so `anti_predictive` comes
        # back `{"readable": False}` and carries no bucket at all — this test
        # would pass over the new section by never meeting it, which is the
        # vacuous-fixture shape it exists to refuse elsewhere.
        #
        # Two buckets, and NOT two of the same shape: -20% under an interval
        # spanning zero and -5% under one entirely below it, so `worst_bucket`
        # (lowest return) and `deficit_buckets` (corrected high bound below
        # zero) are different rows. A fixture where the two coincide leaves one
        # of the two appends untested.
        _plant_round_trip_buckets(outputs, "worst is not the deficit")
    record = build(outputs)
    if planted:
        assert record["forecast"]["pooled"]["anti_predictive"]["measured_buckets"], (
            "the planted buckets must be in the record, or this arm is the "
            "unplanted one under a different name"
        )
    if round_trip:
        block = record["forecast"]["pooled"]["anti_predictive"]
        assert any(block["worst_bucket"] is row for row in block["measured_buckets"]), (
            "this arm is about the identity the in-memory record HAS and the "
            "one off disk does not; if the built record no longer aliases "
            "them, the arm is no longer the contrast it was written as"
        )
        record = read_back(record, tmp_path)
        block = record["forecast"]["pooled"]["anti_predictive"]
        assert not any(
            block["worst_bucket"] is row for row in block["measured_buckets"]
        ), (
            "the round trip did not separate the objects, so this arm is the "
            "in-memory one under a different name"
        )
        assert block["worst_bucket"] in block["measured_buckets"], (
            "and it must still be the same row BY VALUE, or the fixture has "
            "stopped being the pair the defect is about"
        )
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


def _plant_one_measured_bucket(
    outputs: Path, roi: float, ci: tuple[float, float], *, looks: int = 1
) -> None:
    """Give every forecast cell in `outputs` exactly ONE usable claimed-edge bucket.

    Written into the **copy** of the output tree the `outputs` fixture makes,
    never into `data/outputs/`. One bucket is the shape the across-bucket
    comparison cannot use: `measurable` comes back False, and the only thing
    left to report is the sign of the money in that bucket. That is the shape
    this document used to render as nothing at all.

    The bucket's return cell is a real `stats.RoiInterval` through
    `forecast_skill._interval_row`, so the bounds, the correction and the
    verdict are production code's and not this file's arithmetic.

    **`record_version` is stamped forward with the shape.** The committed
    forecast record is version 4 and carries none of the keys written here; a
    fixture that plants version 5 content under a version 4 stamp is a record
    no run could produce, and — before `_forecast_section` checked the version
    — it was the only reason these tests passed at all. What the stamp does not
    claim: `populations` is left exactly as the committed run wrote it, because
    this document reads no key from it. A test of the census belongs in
    `test_forecast_skill.py`, where the renderer that reads it lives.

    `looks` is the family size the FORECAST RUN recorded the bucket under, and
    it is deliberately separate from the ledger count this document re-states
    at. The two being different is the whole of
    `test_a_deficit_that_does_not_survive_todays_correction_is_not_called_one`.
    """
    path = outputs / "cbb_forecast_skill.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["record_version"] = FS.RECORD_VERSION
    standard_error = (ci[1] - ci[0]) / (2.0 * S.Z95)
    interval = S.RoiInterval(
        roi=roi,
        low=roi - S.Z95 * standard_error,
        high=roi + S.Z95 * standard_error,
        bets=400,
        clusters=90,
        standard_error=standard_error,
        looks=looks,
        cluster_unit="day",
    )
    assert interval.low == pytest.approx(ci[0]) and interval.high == pytest.approx(ci[1])
    for cell in [payload["pooled"], *payload["by_tier"]]:
        bucket = {
            "low": 0.20,
            "high": float("inf"),
            "rows": 400,
            "games": 90,
            "enough": True,
            "gap_to_model": 0.0,
            "roi": FS._interval_row(interval, name="realised return"),
        }
        cell["buckets"] = [bucket]
        cell["anti_predictive_return"] = FS.anti_predictive_return([bucket])
    path.write_text(json.dumps(payload, default=str), encoding="utf-8")


def test_a_demonstrated_deficit_in_one_claimed_edge_bucket_reaches_this_page(outputs):
    """The dead key, and the silence behind it.

    `_forecast_tier` read `anti_predictive` — a key `forecast_skill` stopped
    writing on 2026-09-05, when the quantity it held was split into
    `overconfidence` and `anti_predictive_return` because the two are not the
    same thing. It was a `.get`, so nothing raised and nothing went red: the
    block came back `measurable: False` on every run, the per-tier paragraph
    was filtered out of the document, and this page said nothing about
    anti-predictiveness at all.

    So the test is not that a key was renamed. It is that a **measured loss**
    now reaches the rendered page: a claimed-edge bucket of 400 settled wagers
    returning -9% with a family-corrected interval entirely below zero.
    """
    _plant_one_measured_bucket(outputs, -0.09, (-0.10, -0.08))
    record = build(outputs)
    block = record["forecast"]["pooled"]["anti_predictive"]
    assert block["measurable"] is False, (
        "one bucket is not two, so the across-bucket comparison is still not "
        f"measurable — and that must no longer be the end of it; got {block}"
    )
    assert len(block["deficit_buckets"]) == 1, block
    worst = block["worst_bucket"]
    assert worst, "the losing bucket never reached this record"
    assert worst["verdict"] == S.DEMONSTRATED_DEFICIT, worst
    assert WHY.verdict_of(worst) == S.DEMONSTRATED_DEFICIT, (
        "the verdict on the page is derived from the two bounds printed beside "
        f"the return, and it must agree with the stored one; got {worst}"
    )

    page = WHY.render(record)
    assert "Anti-predictiveness, per tier" in page, page[:400]
    assert "worst-returning bucket" in page
    assert "+20% and above" in page
    assert "**-9.0%**" in page, (
        "the return itself has to reach the page; naming a verdict with no "
        "number under it is the same silence in a louder font"
    )
    assert "400 bets" in page
    assert S.DEMONSTRATED_DEFICIT in page
    assert "lost money on the evidence of this run" in page
    # And the threshold sentence is NOT earned here: it rests on two buckets'
    # corrected intervals being disjoint, and there is only one bucket.
    assert "raising the edge threshold is the wrong response" not in page


def test_a_losing_point_estimate_under_a_wide_interval_is_not_called_a_deficit(outputs):
    """The same wiring, the other sign, and the vocabulary held apart.

    A bucket returning -9% under an interval from -30% to +12% has lost nothing
    that has been shown. The page prints the figure and the phrase reserved for
    an interval spanning zero, and never the phrase reserved for one that does
    not — the distinction rule 7 of this lab's standing instructions is about.
    """
    _plant_one_measured_bucket(outputs, -0.09, (-0.30, 0.12))
    record = build(outputs)
    block = record["forecast"]["pooled"]["anti_predictive"]
    assert block["negative_point_estimates"] == 1, block
    assert block["deficit_buckets"] == [], block

    page = WHY.render(record)
    assert "worst-returning bucket" in page
    assert "**-9.0%**" in page
    assert S.NO_DEMONSTRATED_EDGE in page
    assert "lost money on the evidence of this run" not in page, (
        "an interval that spans zero is not a loss that has been shown"
    )


def test_a_deficit_that_does_not_survive_todays_correction_is_not_called_one(outputs):
    """The sentence and the figure beside it are read at ONE family size.

    `_restated_return_bucket` re-states every bucket at the ledger's look count
    on purpose — a bucket whose deficit survived the forecast run's family has
    not necessarily survived today's. The deficit COUNT was then copied
    un-restated out of the forecast record, so the two disagreed: the figure
    printed the re-stated interval and read `no demonstrated edge`, and three
    lines below it the page said the model's claimed edge *"selected wagers
    that lost money on the evidence of this run"*.

    The bucket below is exactly that shape. At the forecast run's one look the
    corrected interval IS the raw one, `[-10.0%, -1.0%]`, entirely below zero —
    so the forecast record records a demonstrated deficit and stores that
    verdict. At the ledger's count the same standard error gives a corrected
    interval that spans zero, and no claim of a loss is available.
    """
    _plant_one_measured_bucket(outputs, -0.055, (-0.10, -0.01), looks=1)
    planted = json.loads(
        (outputs / "cbb_forecast_skill.json").read_text(encoding="utf-8")
    )
    stored = planted["pooled"]["anti_predictive_return"]
    assert stored["demonstrated_deficits"] == 1, (
        "the forecast run must record a deficit, or this test is not about a "
        f"restatement withdrawing one; got {stored}"
    )
    assert stored["worst_bucket"]["verdict"] == S.DEMONSTRATED_DEFICIT, stored

    record = build(outputs)
    block = record["forecast"]["pooled"]["anti_predictive"]
    worst = block["worst_bucket"]
    assert WHY.verdict_of(worst) == S.NO_DEMONSTRATED_EDGE, (
        "at the ledger's look count this interval spans zero; the verdict on "
        f"the page is read off the bounds on the page; got {worst}"
    )
    assert block["deficit_buckets"] == [], (
        "a deficit the correction withdrew is not a deficit this document may "
        f"count; got {block}"
    )

    page = WHY.render(record)
    assert "lost money on the evidence of this run" not in page, (
        "a demonstrated-loss claim printed beside a figure labelled no "
        "demonstrated edge is the page contradicting itself in three lines"
    )
    # The figure itself, on its own line. `demonstrated deficit` is a true
    # reading of other cells elsewhere on this page — the backtest's tiers are
    # genuinely below zero — so the assertion is scoped to the line this test
    # is about rather than to the document.
    printed = [line for line in page.splitlines() if "worst-returning bucket" in line]
    assert printed, "the figure the sentence would have contradicted must be on the page"
    for line in printed:
        assert S.NO_DEMONSTRATED_EDGE in line, line
        assert not line.endswith(S.DEMONSTRATED_DEFICIT), line


def test_a_forecast_record_older_than_this_document_reads_says_so_on_the_page(outputs):
    """A silence a reader cannot tell from a null result is the defect.

    Every key the anti-predictiveness paragraph depends on arrived with
    `forecast_skill.RECORD_VERSION` 5. `read_evidence` checks that the record
    exists, parses and is an object — not that it is the shape this document
    reads — so an older record was read through `_as_int`/`_as_float` and came
    back `measurable: False, demonstrated_deficits: 0, worst_bucket: {}`. The
    section filter then dropped every tier and the whole paragraph left the
    page, green.

    **The committed record used to BE that older shape and no longer is**, so
    the older version is planted here rather than relied on. The regression was
    re-run on 2026-09-17 and the record caught up — which is exactly the case
    the assertion below used to warn about, and its instruction was to plant an
    older version rather than delete the test. The planted version is
    `RECORD_VERSION - 1`, read off the producer's own constant so that this
    stays one version behind through every future bump instead of pinning a
    number that will drift into being the current one again.

    Planting it on the copy is safe: the `outputs` fixture is a writable copy of
    the committed tree, so nothing under `data/outputs/` is touched.
    """
    path = outputs / "cbb_forecast_skill.json"
    committed = json.loads(path.read_text(encoding="utf-8"))
    assert committed["record_version"] == FS.RECORD_VERSION, (
        "the committed record is expected to be current; if it is not, the "
        "regression needs re-running rather than this test needing an edit"
    )
    committed["record_version"] = FS.RECORD_VERSION - 1
    path.write_text(json.dumps(committed, default=str), encoding="utf-8")

    record = build(outputs)
    section = record["forecast"]
    assert section["anti_predictive_readable"] is False, section["record_version"]
    block = record["forecast"]["pooled"]["anti_predictive"]
    assert block == {"readable": False}, (
        "an older record carries none of these keys, and `_as_int` of an "
        f"absent key is a zero nobody counted; got {block}"
    )

    page = WHY.render(record)
    assert "Anti-predictiveness, per tier — not read from this record." in page, (
        "the section may not simply vanish: a reader cannot tell a section "
        "that was dropped from a section that found nothing"
    )
    assert f"is version {committed['record_version']}" in page
    assert "re-run the forecast regression" in page
    assert "Nothing below should be read as the model having been cleared" in page
    # And no measurement vocabulary, in either direction, over a record that
    # was never asked.
    assert "worst-returning bucket" not in page
    assert "lost money on the evidence of this run" not in page
    assert "raising the edge threshold is the wrong response" not in page


BRIER_SILENCE = "No tier above carries a Brier comparison at all"


def test_a_brier_column_with_no_comparison_anywhere_says_so_on_the_page(outputs):
    """**The hole `FORECAST_RECORD_VERSION` deliberately does not cover.**

    The version gate is on the anti-predictive block alone, and on purpose: a
    version 4 forecast record carries `brier.advantage_over_raw` and this
    module reads it correctly, so gating the Brier table on the version would
    refuse figures the record holds. What the version cannot catch there is a
    **rename** — the same event that killed `anti_predictive` on 2026-09-05 —
    and its symptom is a table of `no comparison recorded` in every row with
    `not scored` in every verdict cell, under `anti_predictive_readable: True`
    and a green suite.

    So the whole-column silence is named. This test moves the key exactly as a
    rename would, asserts the sentence, and asserts it is **absent** from the
    committed shape — a guard that fired on every record would be a guard that
    says nothing.
    """
    page_before = WHY.render(build(outputs))
    assert BRIER_SILENCE not in page_before, (
        "the committed record carries the comparison, so the refusal must not "
        "be on the page; a sentence printed unconditionally measures nothing"
    )
    assert "no comparison recorded" not in page_before, (
        "the table has to be carrying real comparisons before the key is "
        "moved, or the contrast this test draws is between two silences"
    )

    path = outputs / "cbb_forecast_skill.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    moved = 0
    for cell in [payload["pooled"], *payload["by_tier"]]:
        brier = cell.get("brier") or {}
        if "advantage_over_raw" in brier:
            brier["advantage_over_raw_v2"] = brier.pop("advantage_over_raw")
            moved += 1
    assert moved, "no cell carried the key, so the rename planted nothing"
    path.write_text(json.dumps(payload, default=str), encoding="utf-8")

    record = build(outputs)
    assert all(
        tier["advantage_over_raw"] == {} for tier in record["forecast"]["tiers"]
    ), "the rename must empty the block, or this test is not about a rename"

    page = WHY.render(record)
    assert page.count("no comparison recorded") >= 3, page[:1500]
    assert BRIER_SILENCE in page, (
        "every cell of the Brier table reads `no comparison recorded` and "
        "every verdict reads `not scored`, which is indistinguishable from a "
        "comparison that came out flat. The page has to say which it is"
    )
    assert "re-run the forecast regression" in page
    assert (
        "Nothing in this table should be read as the model having been cleared"
        in page
    )


def test_the_brier_silence_is_not_claimed_when_one_tier_still_carries_a_comparison(
    outputs,
):
    """*"No tier above carries a Brier comparison at all"* is a census, and a
    census printed over a table that holds one is a false sentence.

    This is the boundary the guard above is written at: `not any(...)`, not
    `not all(...)`. A record in which one tier lost the key and the others kept
    it prints the surviving figures and one `no comparison recorded` cell — a
    partial silence this document does **not** distinguish from a comparison
    the run did not make, disclosed as an open gap beside
    `FORECAST_RECORD_VERSION` rather than claimed closed. What it may not do is
    say *no tier* while a tier is right there in the table.
    """
    path = outputs / "cbb_forecast_skill.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    scored = [
        cell
        for cell in payload["by_tier"]
        if "advantage_over_raw" in (cell.get("brier") or {})
    ]
    assert len(scored) >= 2, (
        "this test needs one tier to lose the key and at least one to keep it; "
        f"only {len(scored)} tiers carry it"
    )
    brier = scored[0]["brier"]
    brier["advantage_over_raw_v2"] = brier.pop("advantage_over_raw")
    path.write_text(json.dumps(payload, default=str), encoding="utf-8")

    page = WHY.render(build(outputs))
    assert "no comparison recorded" in page, (
        "the tier that lost the key must show the empty cell, or nothing was "
        "planted"
    )
    assert BRIER_SILENCE not in page, (
        "the page claimed no tier carries a comparison while "
        f"{len(scored) - 1} of them still do"
    )


@pytest.mark.parametrize(
    ("roi", "would_read"),
    [(0.05, S.DEMONSTRATED_EDGE), (-0.05, S.DEMONSTRATED_DEFICIT)],
)
def test_a_second_half_cell_is_not_evidence_and_never_becomes_the_title(
    outputs, roi, would_read
):
    """**The two published documents disagreed about one row, and this one won.**

    A second-half market settles including overtime at most US books and not at
    all of them, so its return measures a book's rulebook as much as the model.
    `what_we_can_claim` has excluded those cells from both verdict lists since
    it was written; this module never mentioned settlement at all, and its
    `cells` come straight off `by_market_and_tier` with no filter. The h2 prices
    are already bought and unscored, so the first routine backtest that scores
    them puts such a cell in that table — and a positive one retitles this whole
    document *"Where the model does have a demonstrated edge"* while the sibling
    document prints the same row as **not evidence** on the same day.

    Planted in the price backtest and rebuilt, rather than constructed as a
    record row, because the reachability is half the claim: the defect needs no
    edit to a record and no new data, only a measurement that has not run yet.
    """
    backtest_path = WHY.evidence_paths(CBB, outputs)["price backtest"]
    payload = json.loads(backtest_path.read_text(encoding="utf-8"))
    before = build(outputs)

    market = sorted(FE.SETTLEMENT_AMBIGUOUS_MARKETS)[0]
    assert market not in {c["market"] for c in before["cells"]}, (
        "this fixture plants the first second-half cell; the record already "
        "holds one, so the counts below no longer isolate it"
    )
    template = max(payload["by_market_and_tier"], key=lambda r: r.get("bets") or 0)
    planted_row = dict(template)
    planted_row.update(
        {
            "market": market,
            "name": market,
            "tier": "high_major",
            "roi": roi,
            "low": roi - 0.01,
            "high": roi + 0.01,
            "bets": 4_000,
            "clusters": 900,
            "standard_error": 0.005,
        }
    )
    payload["by_market_and_tier"] = list(payload["by_market_and_tier"]) + [planted_row]
    backtest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    record = build(outputs)
    planted = next(c for c in record["cells"] if c["market"] == market)
    # It clears the floor and its corrected interval excludes zero: on the
    # merits of the arithmetic alone this row IS a finding, which is what makes
    # excluding it a rule about settlement rather than about sample size.
    assert planted["enough_evidence"] is True
    assert planted["verdict"] == would_read
    assert WHY.settlement_suspect(planted) is True

    measured = WHY._measured(record, "cells")
    assert planted not in WHY.demonstrated_edges(measured)
    assert planted not in WHY.demonstrated_deficits(measured)
    assert planted in WHY.not_evidence(measured)

    # Neither count moves, and the title cannot follow a verdict nothing holds.
    was = WHY._measured(before, "cells")
    assert len(WHY.demonstrated_edges(measured)) == len(WHY.demonstrated_edges(was))
    assert len(WHY.demonstrated_deficits(measured)) == len(
        WHY.demonstrated_deficits(was)
    )
    assert WHY.title(record) == WHY.title(before)
    assert "does not have a demonstrated edge" in WHY.title(record)

    # Named on the page, carrying its figure and no verdict word. Dropping it
    # silently would be a record this document does not admit to; printing the
    # verdict it "would have had" is the thing `not_evidence` says is the
    # mistake.
    text = WHY.render(record)
    named = [line for line in text.splitlines() if market in line]
    assert named, f"the {market} cell reached the record and not the document"
    for line in named:
        assert "demonstrated" not in line, line
    assert "not evidence" in text
    assert f"{roi:+.1%}" in "\n".join(named)


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

    The sentence has moved three times, and every time the record moved first:

    - 2026-09-04, expanded store: *"It no longer holds"*;
    - 2026-09-05, full store: *"It still holds"* — low-major a demonstrated
      deficit again at 59,475 bets, -4.0%, corrected -8.0% to -0.1% over the
      62 hypotheses the ledger then held;
    - 2026-09-05, after the player-prop pre-registration: *"It no longer
      holds"*. The ledger went from 62 hypotheses to 95, the correction from
      x1.7095 to x1.7689, and low-major's corrected upper bound crossed zero to
      +0.0% on a record whose population, model and store did not change at
      all.

    That third move is the one worth pinning, because nothing about the
    measurement produced it. The branch below is chosen by
    `verdict_of(current)` and nothing else, and both branches are exercised
    against rows this test builds, so neither can be hard-coded.

    What the generator compares is the tier's VERDICT against the verdict the
    retracted sentence claimed. The retracted wording also said *"the only
    tier"*; the generator does not read exclusivity and this test does not
    assert it.
    """
    record = build(outputs)
    tier_key = WHY.SUPERSEDED_CLAIM["tier"]
    current = next(row for row in record["tiers"] if row["tier"] == tier_key)

    # DERIVED, NOT PINNED. This half used to assert the committed record reads
    # "no longer holds", and on 2026-09-17 it stopped being true: refusing the
    # neutral-court side wagers the store cannot orient removed NOISE from
    # low-major rather than signal — a misgraded row is a sign flip, which
    # biases a return toward zero and inflates its variance — and the tier
    # became a demonstrated deficit again. The retraction was itself retracted.
    #
    # Pinning either sentence makes this test a record of the day it was
    # written. The generator chooses its branch from `verdict_of(current)` and
    # nothing else, so this reads the same function and checks the branch it
    # implies. Both branches are still exercised below, against rows this test
    # builds, so neither can be hard-coded into the generator.
    holds = WHY.verdict_of(current) == WHY.SUPERSEDED_CLAIM["verdict_claimed"]
    rendered = WHY.render(record)
    heading = f"### A claim this document has retracted, recorded {WHY.SUPERSEDED_CLAIM['recorded_on']}"
    assert heading in rendered
    section = rendered[rendered.index(heading) :]
    assert WHY.SUPERSEDED_CLAIM["wording"] in section
    assert WHY._figure(current) in section, (
        "the retraction does not print what the record says the tier reads "
        "today, so it is a hand-typed figure again"
    )
    said, not_said = (
        ("**It still holds.**", "**It no longer holds.**")
        if holds
        else ("**It no longer holds.**", "**It still holds.**")
    )
    assert said in section, f"the record reads holds={holds} and the section does not say so"
    assert not_said not in section

    # When it does NOT hold, it must also say WHICH of the two things moved,
    # read off the row: an uncorrected interval that still excludes zero means
    # the correction widened it across, and the paragraph has to say so rather
    # than blame a population that did not change.
    if not holds:
        raw = WHY.printed_interval(current, bounds=("low", "high"))
        if not (raw.low <= 0.0 <= raw.high):
            assert "**The measurement did not move; the search did.**" in section
            assert f"x{S.bonferroni_factor(current['looks']):.4f}" in section

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

    # The other branch of the explanation: a row whose UNCORRECTED interval
    # already spans zero. Nothing about the family can have produced that, so
    # the paragraph must not claim the search did it — the fixed sentence this
    # branch replaced would have blamed the population either way.
    upstream = WHY.cell(
        _tier(
            name=tier_key, tier=tier_key, bets=30_000,
            roi=-0.01, low=-0.09, high=+0.07, standard_error=0.04,
        ),
        looks=95,
    )
    assert upstream["verdict"] == S.NO_DEMONSTRATED_EDGE, upstream
    record["tiers"] = [upstream]
    upstream_section = WHY.render(record)
    upstream_section = upstream_section[upstream_section.index(heading) :]
    assert "**It no longer holds.**" in upstream_section
    assert "**The measurement itself moved.**" in upstream_section
    assert "**The measurement did not move; the search did.**" not in upstream_section

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
    assert "**The measurement did not move; the search did.**" not in section
    assert "**The measurement itself moved.**" not in section
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
    is not rewritten, this fails.

    **Compared at the experiment ledger's count, not at the record's.** This
    test used to read `adjusted_low`/`adjusted_high` straight off the record,
    which pinned row 13 to the correction the fit happened to be scored under —
    x1.6041 over 30 hypotheses — and so required the row to stay stale as the
    ledger grew past it. That is the defect decision 46 closes, in the guard
    that was supposed to catch it. The bounds are re-derived here the way every
    report now re-derives them: same point estimate, same standard error, the
    ledger's cumulative count at read time.
    """
    payload = json.loads(
        FS.record_path(CBB, OUTPUTS).read_text(encoding="utf-8")
    )
    looks = RESTATEMENT.widened(
        int(payload.get("looks", 1) or 1),
        RESTATEMENT.current(RESTATEMENT.ledger_path(OUTPUTS)),
    )
    payload = FS.restated(payload, looks=looks, record_name="cbb_forecast_skill.json")
    text = STATUS.read_text(encoding="utf-8")
    measured = [
        tier for tier in payload["by_tier"]
        if int(tier.get("rows") or 0) >= S.MINIMUM_BETS
    ]
    assert len(measured) == 3, [t["label"] for t in measured]
    for tier in measured:
        raw = tier["brier"]["advantage_over_raw"]
        assert int(raw["looks"]) == looks, (
            "the restatement did not reach this cell, so the comparison below "
            "is against the record's own correction after all"
        )
        # **The figures moved into the generated block, and this reads them
        # there.** It used to require them TYPED in the row, in one exact
        # prose spelling — which was the right guard while the document was
        # hand-written and the wrong one once it was not: it would have forced
        # a second, hand-maintained copy of three intervals to sit outside the
        # fence that exists to stop exactly that. What it is really asserting
        # is unchanged: this document states each measured tier's advantage,
        # and the figure matches the record at the LEDGER's count rather than
        # the one the fit was scored under. Only the location moved.
        printed = (
            f"{raw['adjusted_low']:+.5f} to {raw['adjusted_high']:+.5f}"
        )
        assert printed in text, (
            f"docs/project_status.md does not carry {tier['label']}'s measured "
            f"advantage as `{printed}`, so the document says something the "
            "record does not. It is rendered into the generated block by "
            "`scripts/splice_headline_table.py`; re-run it."
        )
        assert f"{raw['value']:+.5f}" in text, (
            f"{tier['label']}'s interval is in docs/project_status.md without "
            "the point estimate it was derived from."
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


def test_check_refuses_a_record_older_than_the_evidence_it_says_it_read(tmp_path):
    """The freshness gate, driven through the script rather than called directly.

    `stale_inputs` has four unit tests above. The `--check` wiring that consumes
    it had none: replacing `stale = WHY.stale_inputs(record)` in
    `scripts/run_why_the_model.py` with `stale = []` left
    `tests/test_why_the_model.py` and `tests/test_contract_strings.py` -- the
    only two files that name that script -- at 99 passed, so the refusal could
    have been deleted outright with the suite green. A guard nothing executes
    is a guard that is not there, and this is the same shape as the defect in
    `replication.stale_discovery` that these two commits were written for.

    The record is aged rather than the evidence, because `generated_at` is the
    one field `rederivation_differences` treats as volatile: the re-derivation
    still agrees, so this reaches the freshness check instead of stopping at
    the gate above it. That is also the real shape -- `what_we_can_claim`'s
    `--check` passed while the document it checked called a committed backtest
    of 118,050 graded bets *not found*, because the record predated the
    measurement.

    Mutation: `stale = []` at that line. Measured over
    `tests/test_why_the_model.py tests/test_contract_strings.py`: 1 failed, 99
    passed -- this test alone. The run exits 0 with *"matches its run record"*,
    because `render` does not print `generated_at` and the report comparison
    below therefore still passes, so nothing else in either file can see it.
    """
    record, report = _pair_to_check(tmp_path)
    aged = tmp_path / "aged.json"
    payload = json.loads(record.read_text(encoding="utf-8"))
    assert payload.get("evidence_inputs"), (
        "the record names no evidence, so ageing it tests the cannot-answer "
        "branch rather than the older-than-the-evidence one"
    )
    payload["generated_at"] = "2000-01-01T00:00:00Z"
    aged.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    completed = run_script(
        "--competition", "cbb",
        "--record", str(aged),
        "--report", str(report),
        "--check",
    )

    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert "older than the evidence it says it read" in completed.stderr, (
        "the run exited non-zero for some other reason, so this would pass "
        "with the freshness check deleted"
    )
    reasons = [
        line for line in completed.stderr.splitlines() if line.startswith("::error::  ")
    ]
    assert len(reasons) == len(payload["evidence_inputs"]), (
        f"{len(reasons)} reasons for {len(payload['evidence_inputs'])} evidence "
        "files: every input this record names is newer than the record now, so "
        "a run that reported only some of them is reporting a subset as the whole"
    )
    for line in reasons:
        assert "cannot have read evidence that did not exist yet" in line, line
    assert "2000-01-01T00:00:00Z" in completed.stderr, (
        "the refusal names the evidence's stamp and not the record's, so a "
        "reader cannot see which of the two is the stale one"
    )


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


# ---------------------------------------------------------------------------
# The re-derivation guard compares measurements, not the last bits of a double
# ---------------------------------------------------------------------------


def _nudge_every_float(value, steps: int = 5):
    """`value` with every float moved `steps` units in the last place.

    Stands in for the platform difference measured between this repository's
    records and CI: `_statistics._normal_dist_inv_cdf` compiled by two
    compilers returns doubles a unit apart, and `adjusted_low`/`adjusted_high`
    amplify that to about five.
    """
    import math as _math

    if isinstance(value, dict):
        return {k: _nudge_every_float(v, steps) for k, v in value.items()}
    if isinstance(value, list):
        return [_nudge_every_float(v, steps) for v in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        for _ in range(steps):
            value = _math.nextafter(value, _math.inf)
        return value
    return value


def test_a_platforms_worth_of_last_bit_difference_is_not_a_fabrication():
    """The failure that found this: CI called an honest re-render a fabrication.

    Bit-identity across machines is not a property this arithmetic has, and two
    attempts to give it one were measured and rejected — rounding the
    correction to a fixed number of digits only moves the boundary (3,247 of
    4,999 family sizes change under a four-unit nudge at 15 digits), and
    computing `inv_cdf` in pure Python still calls `math.log`, which no
    platform must round correctly. So the guard compares measurements.
    """
    record = json.loads(
        (OUTPUTS / "cbb_why_the_model.json").read_text(encoding="utf-8")
    )
    assert not WHY._differs(record, _nudge_every_float(record)), (
        "five units in the last place reads as a different measurement, so "
        "this guard still fails on any machine whose libm differs from the one "
        "that wrote the record."
    )


@pytest.mark.parametrize(
    "label,mutate",
    [
        (
            "a bound moved by one part in a million",
            lambda r: r["tiers"][0].__setitem__(
                "adjusted_low", r["tiers"][0]["adjusted_low"] * (1 + 1e-6)
            ),
        ),
        (
            "a bound moved by one part in a hundred million",
            lambda r: r["tiers"][0].__setitem__(
                "adjusted_low", r["tiers"][0]["adjusted_low"] * (1 + 1e-8)
            ),
        ),
        (
            "a verdict word",
            lambda r: r["tiers"][0].__setitem__("verdict", "demonstrated edge"),
        ),
        (
            "one bet",
            lambda r: r["tiers"][0].__setitem__("bets", r["tiers"][0]["bets"] + 1),
        ),
        (
            "the correction's applied flag",
            lambda r: r["correction"].__setitem__("applied", False),
        ),
        (
            "a bound of exactly zero nudged above the floor",
            lambda r: r["cells"][20].__setitem__("adjusted_high", 1e-11),
        ),
    ],
)
def test_the_tolerance_still_catches_everything_a_hand_could_type(label, mutate):
    """The gate's purpose, unchanged: a figure no instrument produced.

    Every one of these is orders of magnitude larger than the platform noise
    above, and every one is smaller than anything a reader could see. If one of
    them ever passes, the tolerance has stopped being a tolerance.
    """
    record = json.loads(
        (OUTPUTS / "cbb_why_the_model.json").read_text(encoding="utf-8")
    )
    edited = copy.deepcopy(record)
    mutate(edited)
    assert WHY._differs(record, edited), f"{label} was not caught."


def _bucket_cell(
    low: float, high: float, roi: float, ci: tuple[float, float], *, looks: int = 1
) -> dict:
    """One claimed-edge bucket, its ROI cell built by `forecast_skill`."""
    standard_error = (ci[1] - ci[0]) / (2.0 * S.Z95)
    interval = S.RoiInterval(
        roi=roi,
        low=roi - S.Z95 * standard_error,
        high=roi + S.Z95 * standard_error,
        bets=400,
        clusters=90,
        standard_error=standard_error,
        looks=looks,
        cluster_unit="day",
    )
    assert interval.low == pytest.approx(ci[0]) and interval.high == pytest.approx(ci[1])
    return {
        "low": low,
        "high": high,
        "rows": 400,
        "games": 90,
        "enough": True,
        "gap_to_model": 0.0,
        "roi": FS._interval_row(interval, name="realised return"),
    }


def _plant_per_tier(outputs: Path, by_label: Mapping) -> dict:
    """Plant a DIFFERENT set of claimed-edge buckets into each named cell.

    `_plant_one_measured_bucket` gives every cell the same shape, which cannot
    build the record a per-tier quantifier is about: tiers that differ. Keyed by
    the cell's own `label`, and a label the record does not carry is a failure
    rather than a silent no-op — a fixture that plants nothing and asserts a
    silence is a test of nothing.
    """
    path = outputs / "cbb_forecast_skill.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["record_version"] = FS.RECORD_VERSION
    cells = {c.get("label"): c for c in [payload["pooled"], *payload["by_tier"]]}
    unknown = set(by_label) - set(cells)
    assert not unknown, f"no cell in this record is labelled {unknown}; has {set(cells)}"
    for label, buckets in by_label.items():
        cells[label]["buckets"] = list(buckets)
        cells[label]["anti_predictive_return"] = FS.anti_predictive_return(list(buckets))
    path.write_text(json.dumps(payload, default=str), encoding="utf-8")
    return payload


def test_a_return_bucket_carrying_one_bound_is_refused_not_dropped(outputs):
    """A malformed record is refused; it is not reported as an empty page.

    `_restated_return_bucket` used to `return {}` when either uncorrected bound
    was missing. The tier then had no measured bucket, failed the section
    filter, and left the document — taking its deficit with it. A missing bound
    was reported as *there was nothing here*, which is the same shape as the
    silence this whole section exists to break, and it is the opposite of what
    `verdict_disagreements` does with a half-carried bound pair: that refuses
    outright, because `[x, 0.0]` has a side of zero and therefore a verdict.
    """
    _plant_one_measured_bucket(outputs, -0.09, (-0.14, -0.04))
    path = outputs / "cbb_forecast_skill.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    for cell in [payload["pooled"], *payload["by_tier"]]:
        shape = cell["anti_predictive_return"]
        for bucket in shape["measured_buckets"]:
            bucket.pop("roi_low")
    path.write_text(json.dumps(payload, default=str), encoding="utf-8")

    with pytest.raises(WHY.WhyError) as raised:
        build(outputs)
    assert "one bound" in str(raised.value), raised.value
    assert "Re-run the forecast regression" in str(raised.value)


def test_the_threshold_sentence_quantifies_over_the_tiers_that_could_be_measured(
    outputs,
):
    """"in every tier that can be measured" — so the gate counts those tiers.

    The gate was `shown and len(shown) == len(anti)`, and `anti` now admits a
    tier on a single measured bucket, for which no comparison exists and
    `demonstrated` is necessarily False. So one tier with too few buckets to
    compare suppressed the sentence over every tier that DID compare and did
    come out disjoint — a guard that no longer meant what its own words said.

    Below: high-major and mid-major each compare two buckets whose corrected
    intervals are disjoint; low-major carries one bucket and no comparison.
    """
    compared = [
        _bucket_cell(0.0, 0.02, 0.06, (0.04, 0.08)),
        _bucket_cell(0.20, float("inf"), -0.09, (-0.11, -0.07)),
    ]
    _plant_per_tier(
        outputs,
        {
            "high_major": compared,
            "mid_major": compared,
            "low_major": [_bucket_cell(0.20, float("inf"), -0.09, (-0.11, -0.07))],
            "every tier pooled": compared,
        },
    )
    record = build(outputs)
    blocks = {
        str(t.get("label") or ""): t["anti_predictive"]
        for t in record["forecast"]["tiers"]
    }
    assert blocks["high_major"]["demonstrated"] is True, blocks["high_major"]
    assert blocks["mid_major"]["demonstrated"] is True, blocks["mid_major"]
    assert blocks["low_major"]["measurable"] is False, blocks["low_major"]
    assert blocks["low_major"]["measured_buckets"], (
        "low-major must still reach the page on its single bucket, or this "
        "test is not about the population the quantifier ranges over"
    )

    page = WHY.render(record)
    assert "raising the edge threshold is the wrong response" in page, (
        "both tiers that could be measured came out disjoint, which is exactly "
        "what the sentence claims; a third tier that could not be compared is "
        "not a counterexample to it"
    )
    assert "low_major" in page or "low-major" in page, page


def test_the_threshold_sentence_is_withheld_when_a_compared_tier_overlaps(outputs):
    """The other side of the same gate, so it is not simply always printed.

    One comparable tier's corrected intervals overlap, so the fall is not
    demonstrated there and the sentence may not be printed for any of them.
    """
    disjoint = [
        _bucket_cell(0.0, 0.02, 0.06, (0.04, 0.08)),
        _bucket_cell(0.20, float("inf"), -0.09, (-0.11, -0.07)),
    ]
    overlapping = [
        _bucket_cell(0.0, 0.02, 0.06, (-0.20, 0.32)),
        _bucket_cell(0.20, float("inf"), -0.09, (-0.35, 0.17)),
    ]
    _plant_per_tier(
        outputs,
        {
            "high_major": disjoint,
            "mid_major": overlapping,
            "low_major": disjoint,
            "every tier pooled": disjoint,
        },
    )
    record = build(outputs)
    blocks = {
        str(t.get("label") or ""): t["anti_predictive"]
        for t in record["forecast"]["tiers"]
    }
    assert blocks["mid_major"]["measurable"] is True, blocks["mid_major"]
    assert blocks["mid_major"]["demonstrated"] is False, blocks["mid_major"]
    page = WHY.render(record)
    assert "raising the edge threshold is the wrong response" not in page, page


def test_this_document_states_which_forecast_shape_it_reads():
    """The consumer's floor is pinned to the producer's version, not aliased.

    `FORECAST_RECORD_VERSION` is a literal. Written as `FS.RECORD_VERSION` it
    would be satisfied by every future forecast shape by definition — a gate
    that cannot fire, which is the failure mode one layer up from the one it
    was added to close. Pinned here instead, so the day `forecast_skill`
    changes shape this test is what says the anti-predictiveness paragraph has
    not been read against the new one yet.
    """
    assert WHY.FORECAST_RECORD_VERSION == FS.RECORD_VERSION, (
        "`forecast_skill.RECORD_VERSION` has moved and this document has not "
        "been re-read against the new shape. Check what the anti-predictive "
        "block gained or lost, update `_anti_predictive_block`, then move this "
        "constant — in that order. Moving the constant first turns the gate "
        "off without reading anything"
    )


def test_a_fall_that_does_not_survive_todays_correction_does_not_earn_the_sentence(
    outputs,
):
    """`demonstrated` is derived at today's count, not copied from the run.

    The threshold sentence is a claim about money and rests on the two
    family-corrected intervals being disjoint. That answer was read out of the
    forecast record, where it was taken under that run's family — while the
    intervals this document prints beside it are re-stated at the ledger's. A
    gap that survived one look has not necessarily survived 133.

    The two buckets below are disjoint at the forecast run's single look
    (`[+4.0%, +6.0%]` against `[+1.0%, +3.0%]`) and overlap once re-stated. The
    forecast record therefore stores `demonstrated: True`, and the sentence may
    not be printed.
    """
    compared = [
        _bucket_cell(0.0, 0.02, 0.05, (0.04, 0.06)),
        _bucket_cell(0.20, float("inf"), 0.02, (0.01, 0.03)),
    ]
    payload = _plant_per_tier(
        outputs,
        {
            "high_major": compared,
            "mid_major": compared,
            "low_major": compared,
            "every tier pooled": compared,
        },
    )
    stored = payload["pooled"]["anti_predictive_return"]
    assert stored["falls_at_the_top"] is True, stored
    assert stored["demonstrated"] is True, (
        "the forecast run must record the fall as demonstrated, or this test "
        f"is not about a restatement withdrawing one; got {stored}"
    )

    record = build(outputs)
    block = record["forecast"]["pooled"]["anti_predictive"]
    assert block["measurable"] is True, block
    assert block["demonstrated"] is False, (
        "re-stated at the ledger's count the two corrected intervals overlap, "
        f"so the fall is not demonstrated today; got {block}"
    )
    page = WHY.render(record)
    assert "overlap, so the fall is not demonstrated" in page, page
    assert "raising the edge threshold is the wrong response" not in page, (
        "a sentence about money resting on a gap the correction closed is the "
        "document publishing the forecast run's answer under its own bounds"
    )


def test_the_page_names_the_bucket_whose_own_interval_is_below_zero(outputs):
    """Not the worst return: the bucket the printed bounds convict.

    `worst_bucket` in the forecast record is the lowest POINT ESTIMATE and the
    deficit count is taken off the corrected HIGH BOUND, so they are routinely
    different buckets. This page printed the first and justified it with the
    second: a figure reading `no demonstrated edge` with *"selected wagers that
    lost money"* three lines under it, and the bucket that actually lost the
    money nowhere on the page.

    A returns -20% under an interval spanning zero; B returns -5% under one
    entirely below zero after this document's own correction.
    """
    a = _bucket_cell(0.0, 0.02, -0.20, (-0.45, 0.05))
    b = _bucket_cell(0.02, 0.05, -0.05, (-0.065, -0.035))
    _plant_per_tier(
        outputs,
        {
            "high_major": [a, b],
            "mid_major": [a, b],
            "low_major": [a, b],
            "every tier pooled": [a, b],
        },
    )
    record = build(outputs)
    block = record["forecast"]["pooled"]["anti_predictive"]
    worst = block["worst_bucket"]
    assert worst["name"] == "+0% to +2%", worst
    assert WHY.verdict_of(worst) == S.NO_DEMONSTRATED_EDGE, (
        f"the worst-returning bucket demonstrates nothing; got {worst}"
    )
    named = block["deficit_buckets"]
    assert [row["name"] for row in named] == ["+2% to +5%"], block
    assert WHY.verdict_of(named[0]) == S.DEMONSTRATED_DEFICIT, named[0]

    page = WHY.render(record)
    claim = [line for line in page.splitlines() if "lost money on the evidence" in line]
    assert len(claim) == 1, page
    assert "+2% to +5%" in claim[0], (
        f"the sentence must name the bucket its bounds convict; got {claim[0]}"
    )
    # And that bucket's own figure is on the page, with its verdict beside it.
    figures = [line for line in page.splitlines() if "+2% to +5%" in line and "bets" in line]
    assert figures, page
    for line in figures:
        assert S.DEMONSTRATED_DEFICIT in line, line
    # The worst-returning bucket is printed too, and reads what it is.
    worst_lines = [line for line in page.splitlines() if "worst-returning bucket" in line]
    assert worst_lines, page
    for line in worst_lines:
        assert "+0% to +2%" in line and S.NO_DEMONSTRATED_EDGE in line, line
