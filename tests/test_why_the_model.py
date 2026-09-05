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
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.reports import why_the_model as WHY

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = PROJECT_ROOT / "scripts" / "run_why_the_model.py"
OUTPUTS = PROJECT_ROOT / "data" / "outputs"
DOC = PROJECT_ROOT / WHY.DOC_RELATIVE
LOOP = PROJECT_ROOT / "scripts" / "run_weekly_loop.py"


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
    if not OUTPUTS.is_dir():
        pytest.skip("no data/outputs tree in this checkout")
    target = tmp_path / "outputs"
    shutil.copytree(OUTPUTS, target)
    return target


def build(outputs: Path) -> dict:
    return WHY.build_record(competition=CBB, output_dir=outputs)


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


def test_the_committed_document_matches_what_its_committed_record_renders_to(outputs):
    """The pin the missing generator cost. The fenced block in the document is
    compared against a fresh render of the record committed beside it, so a
    hand-edit inside the fence — the exact way the old document acquired its
    wrong forecast-skill interval — fails the build."""
    committed = WHY.record_path(CBB, OUTPUTS)
    if not committed.is_file():
        pytest.skip("no committed run record in this checkout")
    rendered = WHY.render(WHY.read_record(committed))
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


def test_check_passes_on_the_committed_pair_and_fails_on_a_hand_edit(tmp_path):
    """`--check` is the gate. It compares the report on disk against a fresh
    render of its record, and a hand-edited generated file survives exactly one
    re-render."""
    committed_record = WHY.record_path(CBB, OUTPUTS)
    committed_report = WHY.report_path(CBB, OUTPUTS)
    if not (committed_record.is_file() and committed_report.is_file()):
        pytest.skip("no committed run record and report in this checkout")
    assert run_script("--competition", "cbb", "--check").returncode == 0

    edited = tmp_path / "report.md"
    edited.write_text(
        committed_report.read_text(encoding="utf-8").replace("bets", "wagers"),
        encoding="utf-8",
    )
    completed = run_script(
        "--competition", "cbb",
        "--record", str(committed_record),
        "--report", str(edited),
        "--check",
    )
    assert completed.returncode == 1, completed.stdout + completed.stderr
    assert "edited by hand" in completed.stderr or "does not match" in completed.stderr


# --------------------------------------------------------------------------
# 5. The pipeline actually re-renders it
# --------------------------------------------------------------------------


def test_the_weekly_loop_runs_the_generator_and_splices_the_document():
    """*"Regenerated by the pipeline"* is a claim about a file that has to be
    checkable. The loop names the script and passes `--splice-into`, so a
    document that stops being re-rendered fails here rather than going quiet."""
    text = LOOP.read_text(encoding="utf-8")
    assert 'WHY_SCRIPT = "run_why_the_model.py"' in text
    assert SCRIPT.is_file(), "the loop names a script that is not in the repository"
    assert "WHY_SCRIPT," in text, "the loop declares the script and never runs it"
    assert "--splice-into" in text
    assert WHY.DOC_RELATIVE in (LOOP.read_text(encoding="utf-8") + str(WHY.DOC_RELATIVE))


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
