"""The generated honesty document, and the four ways it could quietly lie.

`tests/test_the_headline_reads_the_sign.py` pins the headline, which is the
defect this report was built around. This file pins everything else the document
has to get right for the headline to be worth reading:

* it is a **pure function of a run record**, so improving a sentence never costs
  a re-run and a hand-edit is caught rather than lost;
* it corrects by the experiment ledger's **cumulative** count, re-applied at
  render time, so a December correction cannot be quoted in March;
* a **broken instrument is never reported as an absence of evidence** — an
  unreadable ledger is a fault, not a null result;
* an excluded market is **never a pass, an avoid or a no-value call**, which is
  one of Cooper's absolute rules and covers the deferred keys and the
  availability-gated props as well as the merely unmeasured.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab import forward_evidence
from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import REPO_ROOT
from cbb_betting_lab.experiment_ledger import (
    AlphaBudget,
    ExperimentLedger,
    Hypothesis,
    save as save_ledger,
)
from cbb_betting_lab.reports import price_backtest
from cbb_betting_lab.reports import replication
from cbb_betting_lab.reports import what_we_can_claim as WC


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _cell(
    *,
    market: str = "spread",
    tier: str = "low_major",
    roi: float = 0.05,
    half_width: float = 0.02,
    bets: int = 9_000,
    clusters: int = 2_200,
) -> dict:
    return {
        "market": market,
        "tier": tier,
        "roi": roi,
        "low": roi - half_width,
        "high": roi + half_width,
        "adjusted_low": roi - half_width,
        "adjusted_high": roi + half_width,
        "bets": bets,
        "clusters": clusters,
        "cluster_unit": "game",
        "looks": 1,
        "standard_error": half_width / S.Z95,
        "enough_evidence": bets >= S.MINIMUM_BETS,
        "verdict": "",
    }


def _write_backtest(
    outputs: Path, cells: list[dict], *, generated_at: str = ""
) -> Path:
    """The price-backtest record on disk.

    `generated_at` is optional and defaults to the empty stamp every existing
    caller was already writing. It is settable because the freshness check
    below reads exactly that field: a backtest that has been re-run carries a
    later stamp, and that is the whole signal.
    """
    outputs.mkdir(parents=True, exist_ok=True)
    target = price_backtest.record_path(CBB, outputs)
    target.write_text(
        json.dumps(
            {
                "record_version": price_backtest.RECORD_VERSION,
                "competition": CBB.key,
                "generated_at": generated_at,
                "by_market_and_tier": cells,
                "pooled": [],
            }
        ),
        encoding="utf-8",
    )
    return target


def _build(tmp_path: Path) -> dict:
    return WC.build_record(
        competition=CBB,
        output_dir=tmp_path / "outputs",
        processed_dir=tmp_path / "processed",
        manual_dir=tmp_path / "manual",
    )


# ---------------------------------------------------------------------------
# A fresh lab
# ---------------------------------------------------------------------------


def test_a_lab_that_has_measured_nothing_produces_a_true_report_not_an_empty_one(
    tmp_path: Path,
):
    """The state this repository is actually in on 2026-09-01.

    The season opens in November. Nothing is bought, nothing has settled, and
    the correct document says so — in words, because an empty table reads as a
    null result and a null result is a claim.
    """
    record = _build(tmp_path)
    rendered = WC.render(record)

    assert record["claims"] == []
    assert WC.NOTHING_TO_MEASURE.capitalize() in rendered
    assert "nothing has been measured against real prices yet" in rendered
    # Short, but never empty: the rules, the policies, the gates and the
    # deferrals are all true statements a fresh lab can make.
    assert len(rendered.splitlines()) > 40
    assert "manual-only" in rendered
    assert "No market is allowlisted, and that is the correct state." in rendered


def test_every_recorded_verdict_is_read_and_stated(tmp_path: Path):
    """A policy absent from the report is a policy nobody can audit."""
    from cbb_betting_lab import verdicts

    rendered = WC.render(_build(tmp_path))

    for policy in verdicts.VERDICT_FILES:
        assert f"`{policy}`" in rendered, (
            f"{policy} has a verdict door and the claims report never mentions "
            "it. What ships must be auditable against the experiment that "
            "decided it."
        )
    assert "No verdict is recorded." in rendered


def test_a_recorded_verdict_that_ships_is_reported_as_in_force(tmp_path: Path):
    from cbb_betting_lab import verdicts

    outputs = tmp_path / "outputs"
    outputs.mkdir(parents=True)
    verdicts.record(
        "venue_home_effect",
        CBB,
        ships_it=True,
        measured_on="2027-01-15",
        variants_tested=3,
        summary="Beat a single league constant on the price backtest.",
        seasons_cleared=(2025, 2026),
        seasons_tested=(2025, 2026),
        output_dir=outputs,
    )
    record = _build(tmp_path)
    rendered = WC.render(record)

    assert any(v["policy"] == "venue_home_effect" and v["ships"] for v in record["verdicts"])
    assert "`venue_home_effect` is **in force**" in rendered
    # A variant count is a degree of freedom spent, and the citation says so.
    assert "3 variants" in rendered


# ---------------------------------------------------------------------------
# Purity: the report is a function of the record
# ---------------------------------------------------------------------------


def test_the_report_re_renders_byte_identically_from_the_run_record(tmp_path: Path):
    """Improving a sentence must never cost a re-run of the measurement."""
    _write_backtest(tmp_path / "outputs", [_cell()])
    record = _build(tmp_path)

    first = WC.render(record)
    round_tripped = json.loads(json.dumps(record, default=str))

    assert WC.render(round_tripped) == first


def test_a_record_of_the_wrong_version_refuses_to_render(tmp_path: Path):
    """A stale record renders a report with holes in it and nothing looks wrong."""
    record = _build(tmp_path)
    record["record_version"] = WC.RECORD_VERSION + 1

    with pytest.raises(WC.ClaimsError, match="Rebuild it"):
        WC.render(record)


def test_the_check_mode_catches_a_hand_edited_report(tmp_path: Path):
    """A hand-edited generated file survives exactly one re-render."""
    outputs = tmp_path / "outputs"
    record = _build(tmp_path)
    WC.write_record(record, WC.record_path(CBB, outputs))
    report = WC.report_path(CBB, outputs)
    WC.write_report(record, report)

    assert _run_script("--check", cwd=tmp_path).returncode == 0

    report.write_text(
        report.read_text(encoding="utf-8").replace(
            "no demonstrated edge", "promising"
        ),
        encoding="utf-8",
    )

    assert _run_script("--check", cwd=tmp_path).returncode == 1


def test_the_vocabulary_of_a_tipster_is_refused(tmp_path: Path):
    """A generated summary that reaches for one of these has started selling."""
    record = _build(tmp_path)
    record["claims"] = []
    record["deferred"] = [
        {"reason": "this is a guaranteed winner", "provider_keys": ["h2h_q1"]}
    ]

    with pytest.raises(WC.ClaimsError, match="guaranteed"):
        WC.write_report(record, tmp_path / "out.md")


def test_the_forbidden_words_are_matched_on_word_boundaries(tmp_path: Path):
    """`clock` contains `lock`, and the futures section says *clock*.

    A guard that fires on honest prose is a guard somebody eventually deletes,
    which is how the guard stops protecting the thing it was written for.
    """
    record = _build(tmp_path)
    record["deferred"] = [
        {"reason": "it settles on a different clock", "provider_keys": ["h2h_q1"]}
    ]

    WC.write_report(record, tmp_path / "out.md")  # does not raise


# ---------------------------------------------------------------------------
# The correction
# ---------------------------------------------------------------------------


def _ledger_with(n: int) -> ExperimentLedger:
    return ExperimentLedger(
        hypotheses=[
            Hypothesis(
                search="tier_search",
                name=f"hypothesis_{i}",
                tested_on="2027-01-15",
                seasons=(2026,),
                outcome="null",
                predicted_direction="higher",
            )
            for i in range(n)
        ],
        budget=AlphaBudget(per_week=6, declared_on="2026-09-01", rationale="Declared."),
    )


def test_the_correction_is_the_ledgers_cumulative_count_and_not_the_days(
    tmp_path: Path,
):
    """*A search that runs every week is not twelve tests. It is twelve tests a
    week, forever.*"""
    outputs = tmp_path / "outputs"
    outputs.mkdir(parents=True)
    save_ledger(_ledger_with(40), WC.experiment_ledger_path(outputs), floor=0)

    correction = WC.correction_from_ledger(WC.experiment_ledger_path(outputs))

    assert correction.applied
    assert correction.hypotheses == 40
    assert correction.looks == 40
    assert correction.factor == pytest.approx(S.bonferroni_factor(40))


def test_an_absent_ledger_applies_no_correction_and_says_so(tmp_path: Path):
    """Quietly applying none is the failure; saying none was applied is not."""
    correction = WC.correction_from_ledger(tmp_path / "nothing.json")
    rendered = WC.render(_build(tmp_path))

    assert not correction.applied
    assert correction.looks == 1
    assert "no family-wise correction could be applied" in rendered
    assert "a fault in the instrument" in rendered


def test_a_grown_ledger_can_turn_a_recorded_edge_into_no_demonstrated_edge(
    tmp_path: Path,
):
    """The reason every interval is rebuilt rather than copied.

    The backtest cell below was recorded with one look and excludes zero. By the
    time this document renders, the ledger has recorded forty hypotheses, and
    the same number no longer clears. The correction may only ever get stricter
    as the search continues.
    """
    outputs = tmp_path / "outputs"
    _write_backtest(outputs, [_cell(roi=0.05, half_width=0.04)])

    before = _build(tmp_path)
    assert [c["verdict"] for c in before["claims"]] == [S.DEMONSTRATED_EDGE]

    save_ledger(_ledger_with(40), WC.experiment_ledger_path(outputs), floor=0)
    after = _build(tmp_path)

    assert [c["verdict"] for c in after["claims"]] == [S.NO_DEMONSTRATED_EDGE]
    assert WC.demonstrated_edges(after) == []
    assert after["claims"][0]["adjusted_low"] < before["claims"][0]["adjusted_low"]


# ---------------------------------------------------------------------------
# The forward ledger
# ---------------------------------------------------------------------------


def _forward_ledger(rows: int = 400) -> pd.DataFrame:
    """A settled forward ledger, alternating won and lost at −110."""
    records = []
    for i in range(rows):
        won = i % 2 == 0
        records.append(
            {
                "snapshot_date": "2027-01-15",
                "commence_time": f"2027-01-{15 + i % 10:02d}T23:00:00+00:00",
                "event_id": f"g{i // 4}",
                "home_team": "A",
                "away_team": "B",
                "market": "spread",
                "segment": "full_game",
                "player": "",
                "selection": "home",
                "line": -1.5,
                "american_odds": -110,
                "book": "book",
                "model_probability": 0.56,
                "edge": 0.05,
                "calibrated_probability": "",
                "calibrated_edge": "",
                "prior_weight": 0.0,
                "tier": "low_major",
                "verdicts_in_force": "",
                "settled_at": "2027-01-16",
                "outcome": "won" if won else "lost",
                "actual": 3.0,
                "profit_units": 0.909091 if won else -1.0,
            }
        )
    return pd.DataFrame(records)


def test_the_forward_standard_error_recovered_here_matches_a_direct_computation(
    tmp_path: Path,
):
    """**The one reconstruction in this module, pinned.**

    `forward_evidence.report_payload` publishes an interval but not the standard
    error behind it. This module recovers it as `(high − low) / (2·Z95)`, which
    inverts exactly how `stats.interval_by_cluster` built the bounds. If that
    construction ever changes, the correction here would be computed off the
    wrong width and nothing would look wrong — so it is checked against an
    interval computed directly from the same rows.
    """
    ledger = _forward_ledger()
    payload = forward_evidence.report_payload(ledger, families=17, competition=CBB)
    rows = [r for r in payload["rows"] if r["cut"] == "opinions"]
    assert rows, "the fixture should produce a measurable opinions row"

    measurable = ledger.assign(
        profit_units=ledger["profit_units"].astype(float),
        slate_date=[c[:10] for c in ledger["commence_time"]],
    )
    direct = S.interval_two_way(measurable, looks=17)
    recovered = WC._interval_from_forward_row(rows[0], looks=17)

    assert recovered.standard_error == pytest.approx(direct.standard_error, rel=1e-9)
    assert recovered.adjusted_low == pytest.approx(direct.adjusted_low, rel=1e-9)


def test_forward_claims_carry_both_cuts_and_their_sample_sizes(tmp_path: Path):
    """Reporting only one cut would let the choice flatter whichever looked
    better, which is the move this repository is arranged against."""
    processed = tmp_path / "processed"
    processed.mkdir(parents=True)
    _forward_ledger().to_csv(processed / forward_evidence.LEDGER_FILENAME, index=False)
    record = _build(tmp_path)
    rendered = WC.render(record)

    cuts = {c["cut"] for c in record["claims"]}
    assert cuts == {"opinions", "bets"}
    for claim in record["claims"]:
        assert claim["bets"] > 0
        assert claim["source"] == WC.FROM_FORWARD
    # Every measured row prints its n, and the corrected interval beside it.
    assert "| Bets | Clusters | ROI | 95% interval | Family-corrected |" in rendered


def test_an_unreadable_ledger_is_a_fault_and_never_an_absence_of_evidence(
    tmp_path: Path,
):
    """Reporting a broken instrument as *nothing measured* turns a fault into a
    null result, which is the one substitution this document exists to prevent."""
    processed = tmp_path / "processed"
    processed.mkdir(parents=True)
    ledger = processed / forward_evidence.LEDGER_FILENAME
    ledger.write_text("event_id,market\nthis,is\nnot,a,ledger\n", encoding="utf-8")

    record = _build(tmp_path)
    rendered = WC.render(record)
    block = record["forward"]

    # Either it parsed to nothing measurable, or it raised. Both are reported
    # as what they are; neither is reported as "no historical price exists".
    assert block["found"] is True
    if block.get("error"):
        assert "present and unreadable" in rendered
    assert record["claims"] == []


# ---------------------------------------------------------------------------
# Cooper's absolute rule about excluded markets
# ---------------------------------------------------------------------------


def test_no_excluded_market_is_ever_a_pass_an_avoid_or_a_no_value_call(
    tmp_path: Path,
):
    rendered = WC.render(_build(tmp_path))

    assert rendered.count(WC.NOT_A_NO_VALUE_CALL) >= 3, (
        "The sentence must sit under every list of markets with no evidence — "
        "the unmeasured, the availability-gated and the deferred provider keys."
    )
    # The only place the words appear is the sentence denying them.
    for phrase in ("no value", "no-value"):
        for line in rendered.splitlines():
            if phrase in line.casefold():
                assert "not a market judged to have no value" in line

    assert "cannot produce a selection" in rendered
    assert "no mandated injury report" in rendered


def test_every_wired_market_appears_somewhere(tmp_path: Path):
    """Nothing is silently dropped: a market with no measurement is listed with
    the reason it has none."""
    from cbb_betting_lab import markets as registry

    record = _build(tmp_path)
    listed = {r["market"] for r in record["unmeasured"]} | {
        c["market"] for c in record["claims"]
    }

    assert listed == {m.key for m in registry.MARKETS}


def test_every_deferred_provider_key_is_listed_with_its_reason(tmp_path: Path):
    from cbb_betting_lab import markets as registry

    rendered = WC.render(_build(tmp_path))
    listed = {
        key
        for group in WC.deferred_groups()
        for key in group["provider_keys"]
    }

    assert listed == set(registry.DEFERRED_MARKETS)
    assert "plays two twenty-minute halves" in rendered


# ---------------------------------------------------------------------------
# The script
# ---------------------------------------------------------------------------


def _run_script(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    root = Path(REPO_ROOT)
    target = cwd if isinstance(cwd, Path) else None
    argv = [
        sys.executable,
        str(root / "scripts" / "run_what_we_can_claim.py"),
        "--competition",
        CBB.key,
    ]
    if target is not None:
        argv += [
            "--output-dir",
            str(target / "outputs"),
            "--processed-dir",
            str(target / "processed"),
            "--manual-dir",
            str(target / "manual"),
        ]
    argv += [a for a in args]
    return subprocess.run(
        argv,
        cwd=str(root),
        env={"PYTHONPATH": str(root / "src"), "PATH": "/usr/bin:/bin"},
        capture_output=True,
        text=True,
    )


def test_the_script_the_workflow_runs_exits_zero_with_nothing_to_say(tmp_path: Path):
    """`run_what_we_can_claim.py --competition cbb`, which is the workflow's
    invocation. A lab that has measured nothing is not a failed run."""
    result = _run_script(cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    report = WC.report_path(CBB, tmp_path / "outputs")
    record = WC.record_path(CBB, tmp_path / "outputs")
    assert report.is_file() and record.is_file()
    assert "nothing has been measured against real prices yet" in result.stdout
    assert "spent no credit" in result.stdout


def test_the_script_writes_the_contract_path(tmp_path: Path):
    """`CLAUDE.md` pins `data/outputs/cbb_what_we_can_claim.md`, and Cooper's
    relay reads it off the card-feed branch under that name."""
    contract = "data/outputs/cbb_what_we_can_claim.md"
    produced = Path("data/outputs") / WC.report_path(CBB, Path("data/outputs")).name

    assert produced.as_posix() == contract


def test_rerender_does_not_consult_the_evidence(tmp_path: Path):
    """The retention probe's rule: re-rendering must never re-read a
    measurement, or improving a sentence costs a re-run."""
    outputs = tmp_path / "outputs"
    _write_backtest(outputs, [_cell(roi=-0.066, half_width=0.02)])
    assert _run_script(cwd=tmp_path).returncode == 0

    # Remove the evidence entirely; the record still renders the same report.
    before = WC.report_path(CBB, outputs).read_text(encoding="utf-8")
    price_backtest.record_path(CBB, outputs).unlink()
    result = _run_script("--rerender", cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert WC.report_path(CBB, outputs).read_text(encoding="utf-8") == before
    assert "The only result that survives is a loss." in before


# ---------------------------------------------------------------------------
# Two regressions found by adversarial review on 2026-09-01
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("label", "payload"),
    [
        ("malformed json", "{ this is not json"),
        # `experiment_ledger.Hypothesis.__post_init__` raises `DirectionRequired`
        # on a hypothesis with no predicted direction. That is the right thing
        # for the ledger to do and the wrong thing for this report to die of.
        (
            "a hypothesis with no declared direction",
            json.dumps(
                {
                    "alpha_budget": {"per_week": 6, "declared_on": "", "rationale": ""},
                    "hypotheses": [
                        {
                            "search": "core_team_markets",
                            "name": "moneyline",
                            "tested_on": "2026-09-01",
                            "seasons": [2026],
                            "outcome": "pending",
                            "predicted_direction": "",
                            "stage": "discovery",
                            "realised_direction": "",
                        }
                    ],
                }
            ),
        ),
        ("a JSON array where an object belongs", "[]"),
    ],
)
def test_an_unreadable_experiment_ledger_is_reported_and_never_takes_the_document_down(
    tmp_path: Path, label: str, payload: str
):
    """The experiment ledger was the one input whose failure escaped.

    `build_record` already catches a broken backtest record and a broken forward
    ledger and reports each as *present and unreadable*, because reporting a
    broken instrument as *nothing measured* turns a fault into a null result.
    `correction_from_ledger` did not: the exception escaped `build_record`, the
    script died with a traceback, and **no document was written at all**.

    That is not fail-closed. The workflow step that re-renders this report is
    `continue-on-error: true` and the health step does not consult it, so the run
    is not marked degraded — and the publish step then carries the *previous*
    `data/outputs/cbb_what_we_can_claim.md` from the checkout onto `card-feed`
    as `latest_what_we_can_claim.md`. The reader gets a coherent, confident
    document with nothing in it to say that today's render never happened, which
    is the stale-claim-for-broken-instrument substitution this whole file exists
    to prevent.

    So: the correction is not applied, the report says the ledger is present and
    could not be read, it names the reason, and every other section still
    renders — none of them depends on the family size.
    """
    outputs = tmp_path / "outputs"
    outputs.mkdir(parents=True)
    WC.experiment_ledger_path(outputs).write_text(payload, encoding="utf-8")
    _write_backtest(outputs, [_cell(roi=0.05, half_width=0.02)])

    correction = WC.correction_from_ledger(WC.experiment_ledger_path(outputs))
    assert not correction.applied, label
    assert correction.error, f"{label}: an unreadable ledger must name its fault"
    assert correction.looks == 1

    record = _build(tmp_path)
    rendered = WC.render(record)

    # Present and unreadable, never "not found" — they are different claims.
    assert "present and could not be read" in rendered, label
    assert "No experiment ledger was found" not in rendered, label
    assert "broken instrument" in rendered
    assert "narrower than the evidence supports" in rendered
    assert "**present and unreadable**" in rendered
    # And the rest of the document is still there.
    assert "## Measured against real prices" in rendered
    assert WC.NOT_A_NO_VALUE_CALL in rendered

    # End to end, through the entry point the workflow actually runs.
    result = _run_script(cwd=tmp_path)
    assert result.returncode == 0, result.stderr
    assert WC.report_path(CBB, outputs).is_file()


def test_a_suspect_settlement_row_never_prints_the_verdict_it_would_have_had(
    tmp_path: Path,
):
    """`not_evidence` says it in words: *saying which it "would have been" is
    the mistake.*

    The verdict cell for a second-half market used to read "**not evidence** —
    the settlement rule cannot be verified; stated in the stats vocabulary it
    would read *demonstrated edge*". That is the sentence the docstring forbids,
    printed in the one column a reader skims for the answer, on exactly the
    market family that produced the football lab's largest false finding. The
    ROI, the interval and the corrected interval are all still printed with the
    sample size beside them, so no number is hidden — only the verdict word the
    lab is not entitled to.
    """
    outputs = tmp_path / "outputs"
    _write_backtest(outputs, [_cell(market="total_points_h2", roi=0.099, half_width=0.02)])

    record = _build(tmp_path)
    rendered = WC.render(record)

    assert len(WC.not_evidence(record)) == 1
    assert WC.demonstrated_edges(record) == []
    assert WC.demonstrated_deficits(record) == []

    assert "not evidence" in rendered
    assert "neither an edge nor a deficit" in rendered
    assert "would read" not in rendered

    # The verdict word must not appear in the cell's own row. Checked on the
    # row rather than on the whole document, because the headline's
    # `no demonstrated edge` legitimately contains `demonstrated edge` as a
    # substring — the distinction the phrase exists to make lives in the word
    # in front of it, which is why nothing in this repository tests for the
    # sign by substring.
    row = next(l for l in rendered.splitlines() if l.startswith("| `total_points_h2`"))
    assert S.DEMONSTRATED_EDGE not in row
    assert S.DEMONSTRATED_DEFICIT not in row
    # The numbers themselves are still in that row, with their sample size.
    assert "+9.9%" in row
    assert "9,000" in row


# ---------------------------------------------------------------------------
# A record that can tell it is stale
#
# The defect, verbatim from the committed document on 2026-09-04: line 8 said
# "**Nothing in this repository has a demonstrated edge, because nothing has
# been measured against real prices yet.**" and the provenance list said
# "Price backtest: `data/outputs/cbb_price_backtest.json` — **not found**",
# while that record sat committed beside it with `generated_at` 2026-09-04,
# 118,050 graded bets and one demonstrated deficit in it. The run record had
# `backtest: {"found": false}` and had been written the day before the backtest
# ran, so the markdown was a faithful rendering of it and `--check` — which
# compared the markdown against nothing else — exited zero.
#
# Every test here starts from a green `--check` and then moves the evidence.
# ---------------------------------------------------------------------------


PAST = "2020-01-01T00:00:00Z"
LATER = "2031-01-01T00:00:00Z"


def _publish(tmp_path: Path) -> tuple[Path, Path, Path]:
    """Build, write the record, write the report. A green `--check` starts here."""
    outputs = tmp_path / "outputs"
    record = _build(tmp_path)
    record_target = WC.write_record(record, WC.record_path(CBB, outputs))
    report_target = WC.write_report(record, WC.report_path(CBB, outputs))
    return outputs, record_target, report_target


def _still_matches_its_own_record(record_target: Path, report_target: Path) -> bool:
    """What the OLD `--check` asked, and the only thing it asked.

    Asserted true in the tests below at the moment they expect a failure, so
    each of them proves the new question is doing the work rather than riding
    on the old one.
    """
    return WC.render(WC.read_record(record_target)) == report_target.read_text(
        encoding="utf-8"
    )


def test_a_record_newer_than_every_input_it_read_passes_the_check(tmp_path: Path):
    """The honest case, and it must stay quiet or nobody keeps the check."""
    _write_backtest(tmp_path / "outputs", [_cell()], generated_at=PAST)
    _publish(tmp_path)

    result = _run_script("--check", cwd=tmp_path)

    assert result.returncode == 0, result.stderr


def test_a_record_that_says_absent_fails_when_the_evidence_is_now_on_disk(
    tmp_path: Path,
):
    """**The committed defect.** `backtest: {"found": false}`, backtest on disk."""
    outputs, record_target, report_target = _publish(tmp_path)
    assert _run_script("--check", cwd=tmp_path).returncode == 0
    backtest_file = _write_backtest(outputs, [_cell()], generated_at=LATER)

    result = _run_script("--check", cwd=tmp_path)

    assert result.returncode == 1, result.stdout
    # The old question still answers "fine", which is exactly how this shipped.
    assert _still_matches_its_own_record(record_target, report_target)
    # The message names the file and both timestamps.
    written_at = json.loads(record_target.read_text(encoding="utf-8"))["generated_at"]
    assert str(backtest_file) in result.stderr
    assert LATER in result.stderr
    assert written_at in result.stderr


def test_a_record_fails_when_evidence_it_read_has_since_vanished(tmp_path: Path):
    """A document quoting a measurement that is no longer on disk."""
    outputs, record_target, report_target = _publish(tmp_path)
    _write_backtest(outputs, [_cell()], generated_at=PAST)
    _publish(tmp_path)
    assert _run_script("--check", cwd=tmp_path).returncode == 0
    price_backtest.record_path(CBB, outputs).unlink()

    result = _run_script("--check", cwd=tmp_path)

    assert result.returncode == 1, result.stdout
    assert _still_matches_its_own_record(record_target, report_target)
    assert "is not on disk now" in result.stderr


def test_a_record_fails_when_an_input_it_read_has_been_regenerated(tmp_path: Path):
    """Same cells, later stamp. The numbers are identical and the record is not
    the one that read them, which is what a re-measured season looks like the
    moment before it changes a number."""
    outputs = tmp_path / "outputs"
    _write_backtest(outputs, [_cell()], generated_at=PAST)
    _, record_target, report_target = _publish(tmp_path)
    assert _run_script("--check", cwd=tmp_path).returncode == 0

    _write_backtest(outputs, [_cell()], generated_at=LATER)

    result = _run_script("--check", cwd=tmp_path)

    assert result.returncode == 1, result.stdout
    assert _still_matches_its_own_record(record_target, report_target)
    assert PAST in result.stderr and LATER in result.stderr


def test_a_record_that_never_wrote_down_what_it_read_cannot_pass_the_check(
    tmp_path: Path,
):
    """The shape of the record committed on 2026-09-04.

    It cannot answer "are you older than the evidence", and *"could not check"*
    is reported as a failure rather than as a pass. A check that reads an
    unanswerable question as an answer of "fine" is the defect, not the fix.
    """
    outputs = tmp_path / "outputs"
    _write_backtest(outputs, [_cell()], generated_at=PAST)
    _, record_target, _ = _publish(tmp_path)
    record = json.loads(record_target.read_text(encoding="utf-8"))
    record.pop("evidence_inputs")
    record_target.write_text(json.dumps(record, indent=2), encoding="utf-8")

    assert WC.stale_inputs(record)
    assert _run_script("--check", cwd=tmp_path).returncode == 1


def test_the_record_writes_down_every_evidence_file_it_opened(tmp_path: Path):
    """Path, presence and stamp, for each one. That triple is what makes the
    check possible; a record carrying two thirds of it is a record that can
    still be silently out of date about the third."""
    outputs = tmp_path / "outputs"
    _write_backtest(outputs, [_cell()], generated_at=PAST)
    record = _build(tmp_path)

    inputs = {(i["label"], i["path"]): i for i in record["evidence_inputs"]}
    assert {label for label, _ in inputs} == {
        "Experiment ledger",
        "Price backtest",
        "Forward-evidence ledger",
        "Replication record",
    }
    for item in inputs.values():
        assert set(item) == {"label", "path", "found", "generated_at"}
    backtest_entry = inputs[
        ("Price backtest", str(price_backtest.record_path(CBB, outputs)))
    ]
    assert backtest_entry["found"] is True
    assert backtest_entry["generated_at"] == PAST
    assert WC.stale_inputs(record) == []


# ---------------------------------------------------------------------------
# The replication record, read from where the script actually writes it
#
# `replication_path` built its own path under `--output-dir`, and
# `scripts/run_replication.py` writes under ITS `--output-dir`, which a holdout
# run points at `data/outputs/holdout/`. So a real replication over the
# held-out 2024 season sat committed at
# `data/outputs/holdout/cbb_replication.json` while this document reported that
# no held-out test had been run — a test that ran, reported as a test that did
# not.
# ---------------------------------------------------------------------------


def _replication_record(target: Path, *, state: str = "replicated") -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "test_label": "2024 (held out)",
                "markets": [
                    {"market": "spread", "tier": "low_major", "state": state}
                ],
            }
        ),
        encoding="utf-8",
    )
    return target


def test_the_paths_searched_are_the_ones_the_replication_script_writes():
    """Derived from `replication.record_path` — the function
    `scripts/run_replication.py` itself calls — rather than re-spelled here. A
    second literal is how the reader and the writer drifted apart."""
    outputs = Path("/tmp/x")

    assert WC.replication_paths(CBB, outputs) == [
        replication.record_path(CBB, outputs),
        replication.record_path(CBB, outputs / WC.HOLDOUT_DIRNAME),
    ]
    assert [p.name for p in WC.replication_paths(CBB, outputs)] == [
        "cbb_replication.json",
        "cbb_replication.json",
    ]
    assert WC.replication_paths(CBB, outputs)[1].parent.name == "holdout"


def test_a_replication_record_where_the_holdout_run_writes_it_is_read(
    tmp_path: Path,
):
    """`--output-dir data/outputs/holdout/`, which is the invocation both
    `run_replication.py` and `run_price_backtest.py` document in comments."""
    outputs = tmp_path / "outputs"
    _write_backtest(outputs, [_cell(roi=0.06)])
    target = _replication_record(
        replication.record_path(CBB, outputs / WC.HOLDOUT_DIRNAME)
    )

    record = _build(tmp_path)
    rendered = WC.render(record)

    assert record["replication"]["found"] is True
    assert record["replication"]["path"] == str(target)
    assert record["replication"]["test_label"] == "2024 (held out)"
    assert record["replication"]["states"] == [
        {"market": "spread", "tier": "low_major", "state": "replicated"}
    ]
    claim = record["claims"][0]
    assert claim["replication"] == "replicated"
    assert claim["replicated"] is True
    assert f"- Replication record: `{target}` — read" in rendered


def test_a_replication_record_at_the_default_output_dir_is_still_read(
    tmp_path: Path,
):
    """`run_replication.py --output-dir` defaults to `data/outputs`, so that
    path is not dropped in favour of the holdout one."""
    outputs = tmp_path / "outputs"
    _write_backtest(outputs, [_cell(roi=0.06)])
    target = _replication_record(replication.record_path(CBB, outputs))

    record = _build(tmp_path)

    assert record["replication"]["path"] == str(target)
    assert record["claims"][0]["replicated"] is True


def test_an_absent_replication_record_is_reported_absent_and_never_as_a_failure(
    tmp_path: Path,
):
    """The absence must keep saying *no held-out test has been run*. It is not
    a market that failed to replicate, and the sibling labs have printed the
    second while meaning the first."""
    outputs = tmp_path / "outputs"
    _write_backtest(outputs, [_cell(roi=0.06)])

    record = _build(tmp_path)
    rendered = WC.render(record)

    assert record["replication"]["found"] is False
    assert record["replication"]["states"] == []
    assert record["replication"]["test_label"] == ""
    claim = record["claims"][0]
    assert claim["replication"] == ""
    assert claim["replicated"] is False
    assert (
        f"- Replication record: `{replication.record_path(CBB, outputs)}` — "
        "**not found**, so this document says nothing about it" in rendered
    )
    lowered = rendered.casefold()
    assert "failed to replicate" not in lowered
    assert "did not replicate" not in lowered


def test_a_replication_record_that_appears_later_fails_the_check(tmp_path: Path):
    """Both candidate paths are watched, not only the one this run resolved to.
    A holdout run writing the other one is precisely the appearance that left
    the committed document saying no held-out test had been run."""
    outputs = tmp_path / "outputs"
    _write_backtest(outputs, [_cell(roi=0.06)], generated_at=PAST)
    _publish(tmp_path)
    assert _run_script("--check", cwd=tmp_path).returncode == 0

    _replication_record(
        replication.record_path(CBB, outputs / WC.HOLDOUT_DIRNAME)
    )

    result = _run_script("--check", cwd=tmp_path)

    assert result.returncode == 1, result.stdout
    assert "holdout" in result.stderr
