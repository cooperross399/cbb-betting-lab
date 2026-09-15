"""No document in this repository states a verdict at a stale correction.

The defect this file exists for, recorded 2026-09-05: every record stored the
family-wise correction that was current when its run happened, every rendered
report restated that stored number as the answer, and `--rebuild-report-only`
— the cheapest and most-run operation here — replayed it rather than re-reading
the ledger. The lab therefore held **three** corrections in force at once,
across its own documents, with nothing on the page to say which was which:

    data/outputs/cbb_price_backtest.json        looks=30   x1.6041
    data/outputs/holdout/cbb_replication.json   looks=62   x1.7095
    data/outputs/experiment_ledger.json         looks=95   x1.7689

and two published verdicts read *demonstrated deficit* at a correction narrower
than the search that had actually been run. Decision 46 is the fix: the report
restates at render time, the record keeps what it measured.

Three properties are pinned here, and the third is the one that would have
caught the original.

1. **A restatement moves only the correction.** The point estimate, the raw
   interval, the standard error, the bet count and the cluster count are the
   measurement and must come through untouched. A restatement that moved them
   is a re-measurement wearing a re-render's clothes.
2. **A restatement is one-directional.** It may only widen, so it can retract a
   claim and never create one — and an experiment ledger the renderer cannot
   find leaves the record's own correction in force rather than collapsing it
   to the raw interval, which would make a missing file the strongest claim in
   the repository.
3. **Every committed report is what its committed record renders to at the
   ledger's CURRENT count.** This is the repository-level gate: it fails the
   day a hypothesis is registered and a report is not re-rendered, which is the
   day the old defect used to reappear.
"""

from __future__ import annotations

import copy
import dataclasses
import importlib.util
import json
import re
import shutil
import sys
from pathlib import Path

import pytest

from cbb_betting_lab import restatement as RESTATEMENT
from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.experiment_ledger import load as load_ledger
from cbb_betting_lab.reports import forecast_skill as FS
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.models import player_rates as PR  # noqa: E402
from cbb_betting_lab.reports import prop_grading as PG
from cbb_betting_lab.reports import replication as REPL
from cbb_betting_lab.reports import what_we_can_claim as WC
from cbb_betting_lab.reports import why_the_model as WTM

REPO = Path(__file__).resolve().parents[1]
OUTPUTS = REPO / "data" / "outputs"
DOCS = REPO / "docs"
LEDGER = OUTPUTS / "experiment_ledger.json"


def _load_script(name: str):
    """Import a script by path. `scripts/` is not a package and never will be."""
    path = REPO / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_stale_{name}", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def ledger_looks() -> int:
    return max(load_ledger(LEDGER).count, 1)


# ---------------------------------------------------------------------------
# 1. A restatement moves only the correction
# ---------------------------------------------------------------------------

#: What a cell is allowed to differ by after a restatement. Anything else in it
#: is the measurement. Kept here as a second, independently written copy of
#: `restatement.CORRECTION_DEPENDENT` — a constant that checks itself against a
#: constant it imports is not a check.
MAY_MOVE = {
    "looks",
    "adjusted_low",
    "adjusted_high",
    "enough_evidence",
    "survives_correction",
    "verdict",
    "claims",
    # `forecast_skill.Coefficient` writes these three off the corrected
    # interval, so they move with it and never on their own.
    "contains_null",
    "reading",
    "gloss",
}


def _cells(node, path=""):
    if isinstance(node, dict):
        if RESTATEMENT.is_interval_cell(node):
            yield path, node
        for key, value in node.items():
            yield from _cells(value, f"{path}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _cells(value, f"{path}[{index}]")


def test_the_permitted_fields_are_the_ones_the_module_declares():
    assert set(RESTATEMENT.CORRECTION_DEPENDENT) <= MAY_MOVE, (
        "restatement.py declares a correction-dependent field this test does "
        "not know about. Either the field is really part of the measurement, "
        "or this list is out of date — decide which before the suite goes green."
    )


def test_a_restatement_moves_only_the_correction():
    record = json.loads(
        (OUTPUTS / "cbb_price_backtest.json").read_text(encoding="utf-8")
    )
    moved = PB.restated(record, looks=ledger_looks() + 500, record_name="x")

    before = dict(_cells(record))
    after = dict(_cells(moved))
    assert before, "no interval cells found, so this test checks nothing"
    assert set(before) == set(after)
    for path, cell in before.items():
        for key, value in cell.items():
            if key in MAY_MOVE:
                continue
            assert after[path][key] == value, (
                f"{path}.{key} moved during a re-render. That field is the "
                "measurement, and a re-render does not re-measure."
            )


def test_a_restatement_can_retract_a_verdict_and_never_creates_one():
    """The correction only widens, so it can only ever take a claim away."""
    record = json.loads(
        (OUTPUTS / "cbb_price_backtest.json").read_text(encoding="utf-8")
    )
    narrow = PB.restated(record, looks=1, record_name="x")
    wide = PB.restated(record, looks=100_000, record_name="x")
    for path, cell in _cells(narrow):
        if "verdict" not in cell:
            continue
        widened = dict(_cells(wide))[path]
        claimed = cell["verdict"] in {S.DEMONSTRATED_EDGE, S.DEMONSTRATED_DEFICIT}
        still = widened["verdict"] in {S.DEMONSTRATED_EDGE, S.DEMONSTRATED_DEFICIT}
        assert claimed or not still, (
            f"{path} makes a claim at 100,000 hypotheses that it did not make "
            "at one. A wider correction manufactured a finding, which is the "
            "opposite of what a correction is for."
        )
        assert widened["adjusted_low"] <= cell["adjusted_low"]
        assert widened["adjusted_high"] >= cell["adjusted_high"]


# ---------------------------------------------------------------------------
# 2. One-directional, and an absent ledger does not narrow anything
# ---------------------------------------------------------------------------


def test_an_absent_ledger_leaves_the_records_own_correction_in_force(tmp_path):
    absent = RESTATEMENT.current(tmp_path / "nothing.json")
    assert absent.found is False
    assert absent.looks == 1
    assert RESTATEMENT.widened(30, absent) == 30, (
        "a ledger the renderer could not find narrowed a published verdict "
        "back towards its raw interval. An absent ledger is an unknown family, "
        "never an empty one."
    )


@pytest.mark.parametrize(
    "how",
    ["absent", "unreadable"],
    ids=["a ledger that is not there", "a ledger that will not parse"],
)
@pytest.mark.parametrize(
    "build",
    [
        pytest.param(lambda out: WC.build_record(output_dir=out), id="what_we_can_claim"),
        pytest.param(
            lambda out: WTM.build_record(competition=CBB, output_dir=out),
            id="why_the_model",
        ),
    ],
)
def test_a_ledger_the_renderer_cannot_read_never_manufactures_a_replication(
    tmp_path, build, how
):
    """The one direction a restatement may not move, at the two call sites that could.

    `correction_from_ledger` returns `looks=1` for a ledger that is absent and
    for one that is present and will not parse — deliberately, so a broken file
    does not take the whole document down. One look applies no correction at
    all, so passing it straight to `replication.restated` does not merely fail
    to widen: it runs `judge_cell` again on the RAW 95% bounds and hands back
    states nobody measured. On the committed record that turns
    `team_total / mid_major` from *nothing to replicate* into **replicated** and
    `total_points / low_major` into *did not replicate* — a claim manufactured
    by deleting a file.

    The floor is `restatement.widened`, which takes the larger of the ledger's
    count and the record's own, so the worst an unreadable ledger can do is
    leave the correction exactly where the run published it.
    """
    outputs = tmp_path / "outputs"
    shutil.copytree(OUTPUTS, outputs)
    ledger = outputs / "experiment_ledger.json"
    assert ledger.is_file(), "the fixture copy must start with a readable ledger"

    with_ledger = build(outputs)

    if how == "absent":
        ledger.unlink()
    else:
        ledger.write_text("{ this is not json", encoding="utf-8")

    without_ledger = build(outputs)

    for label, record in (("with", with_ledger), ("without", without_ledger)):
        states = _replication_states(record)
        assert states.get("replicated", 0) == 0, (
            f"{label} a readable ledger, the report states "
            f"{states.get('replicated')} replicated cell(s). The committed "
            "record replicates nothing at its own correction or at the "
            "ledger's; a replication that appears when a file is removed was "
            "manufactured by the removal."
        )
        assert states.get("did not replicate", 0) == 0

    assert _replication_states(with_ledger) == _replication_states(without_ledger), (
        "an unreadable ledger changed the replication states. The floor exists "
        "so that it cannot: the record's own correction stays in force."
    )


def _replication_states(record) -> dict:
    """The replication state counts a built record carries, in either spelling.

    `why_the_model` stores them already counted under
    `replication.counts`; `what_we_can_claim` carries them as a `replicated`
    flag on each claim plus its own `replication` block. Both are read here so
    one test can hold both call sites, and the helper asserts it found
    something rather than returning an empty dict that would make every
    assertion below it vacuous.
    """
    payload = record.get("replication")
    if isinstance(payload, dict) and isinstance(payload.get("counts"), dict):
        counts = {str(k): int(v) for k, v in payload["counts"].items()}
    else:
        counts = {}
        for market in (payload or {}).get("markets", []) or []:
            for cell in market.get("cells", [market]):
                state = cell.get("state")
                if state:
                    counts[state] = counts.get(state, 0) + 1
        for claim in record.get("claims", []) or []:
            if claim.get("replicated"):
                counts["replicated"] = counts.get("replicated", 0) + 1
        counts.setdefault("replicated", 0)
        counts.setdefault("did not replicate", 0)
    assert counts, (
        "no replication states were found in the built record. This helper is "
        "the only thing the assertions below read, so an empty result would "
        "make the whole test pass on nothing."
    )
    return counts


def test_a_shorter_ledger_never_narrows_a_report(tmp_path):
    shorter = RESTATEMENT.Correction(looks=12, factor=1.0, found=True, source="x")
    assert RESTATEMENT.widened(95, shorter) == 95


def test_the_rebuild_flag_reads_the_ledger_rather_than_replaying_the_record(
    tmp_path,
):
    """The defect, in one line: the re-render used to replay `record["looks"]`.

    Reproduced by giving the same record two different ledgers and requiring
    two different reports. Before decision 46 both renders were identical, and
    the identical one was the stale one.

    **Both ledgers are sized from the record's own `looks`.** They used to be
    40 and 400 against a record scored at 30, and the small one silently
    stopped being a restatement the day that record was re-run at 95: the
    restatement may only ever widen, so a ledger below the record's own count
    correctly leaves it alone, and the report then names 95 where the test
    demanded 40. The property under test is that the RENDER reads the ledger;
    the two counts only have to differ from each other and sit above the
    record.
    """
    script = _load_script("run_price_backtest")
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    record = json.loads(
        (OUTPUTS / "cbb_price_backtest.json").read_text(encoding="utf-8")
    )
    PB.write_record(record, PB.record_path(CBB, outputs))
    report = PB.report_path(CBB, outputs)

    scored_at = int(record.get("looks", 1) or 1)
    fewer, more = scored_at + 10, scored_at + 310
    small = tmp_path / "small.json"
    small.write_text(
        json.dumps({"hypotheses": [_hypothesis(i) for i in range(fewer)]}),
        encoding="utf-8",
    )
    big = tmp_path / "big.json"
    big.write_text(
        json.dumps({"hypotheses": [_hypothesis(i) for i in range(more)]}),
        encoding="utf-8",
    )

    assert script.main(
        ["--output-dir", str(outputs), "--ledger", str(small), "--rebuild-report-only"]
    ) == 0
    at_forty = report.read_text(encoding="utf-8")
    assert script.main(
        ["--output-dir", str(outputs), "--ledger", str(big), "--rebuild-report-only"]
    ) == 0
    at_four_hundred = report.read_text(encoding="utf-8")

    assert f"{fewer:,} cumulative hypotheses" in at_forty
    assert f"{more:,} cumulative hypotheses" in at_four_hundred
    assert at_forty != at_four_hundred, (
        "the re-render produced the same report against two different ledgers, "
        "so it is replaying the correction stored in the record. That single "
        "line is what let three corrections be in force across this lab at once."
    )


def test_a_restated_report_does_not_announce_that_no_correction_was_applied():
    """The two sentences that used to contradict each other on one page.

    `ledger_read` records whether the RUN found a ledger, and a restatement
    deliberately leaves it alone — it is provenance, not arithmetic. But a
    re-render corrects from the ledger it finds at render time, so a record
    written with no ledger and re-rendered beside a 95-hypothesis one had every
    interval widened by x1.77 under a bold paragraph reading *"NO FAMILY
    CORRECTION WAS APPLIED ... Every interval below is the raw one ... Read
    nothing here as corrected"*. The alarming sentence was the wrong one, which
    is the worst way round for it to be wrong.

    The paragraph is now keyed on the correction in force on the page. The
    warning still fires when there genuinely is none, and when a run that saw
    no ledger is corrected at render time the page says both things.
    """
    record = json.loads(
        (OUTPUTS / "cbb_price_backtest.json").read_text(encoding="utf-8")
    )
    correction = RESTATEMENT.current(LEDGER)
    looks = RESTATEMENT.widened(_as_int_or_one(record.get("looks")), correction)
    assert looks > 1, "this test needs a ledger with a real cumulative count"

    corrected_but_blind = RESTATEMENT.restate_tree(copy.deepcopy(record), looks=looks)
    corrected_but_blind["looks"] = looks
    corrected_but_blind["correction_factor"] = S.bonferroni_factor(looks)
    corrected_but_blind["ledger_read"] = False
    page = PB.render(corrected_but_blind)

    assert "NO FAMILY CORRECTION WAS APPLIED" not in page, (
        "the page announces that no correction was applied, over intervals it "
        f"widened by x{S.bonferroni_factor(looks):.2f}."
    )
    assert f"Family correction: {looks:,} cumulative hypotheses" in page
    assert "found no ledger; this correction was read at render time" in page, (
        "the page corrects at render time and does not say that the run itself "
        "never saw a ledger, which is the provenance the flag exists to carry."
    )

    # And the warning still fires when there is genuinely no correction.
    uncorrected = copy.deepcopy(record)
    uncorrected["looks"] = 1
    uncorrected["correction_factor"] = 1.0
    uncorrected["ledger_read"] = False
    assert "NO FAMILY CORRECTION WAS APPLIED" in PB.render(uncorrected)


def _as_int_or_one(value) -> int:
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return 1


def _hypothesis(index: int) -> dict:
    return {
        "search": "synthetic",
        "name": f"h{index}",
        "tested_on": "2026-09-05",
        "seasons": [2024],
        "outcome": "pending",
        "predicted_direction": "lower",
        "stage": "discovery",
    }


# ---------------------------------------------------------------------------
# 3. Every committed report is current
# ---------------------------------------------------------------------------

#: Every sentence a generated document uses to state the family size it applies.
#: One pattern per generator, so a generator that grows a fourth phrasing has to
#: be added here before its report can go stale unnoticed.
CORRECTION_SENTENCES = re.compile(
    r"Family correction: ([\d,]+) cumulative hypotheses"
    r"|corrected across \*\*([\d,]+) hypotheses ever tested"
    r"|\*\*([\d,]+) distinct hypotheses have ever been tested here\*\*"
    r"|corrected for ([\d,]+) cumulative distinct hypotheses"
    r"|\*\*([\d,]+) distinct hypotheses tested\.\*\*"
    # Added 2026-09-10 with the detection table's power preamble. It grew a
    # sixth phrasing and was not added here, so the page could print "at the
    # ledger's 1 cumulative hypotheses" while this regex collected only the
    # OTHER count on the same page and compared that to the ledger. The
    # constant's comment above already demanded this; it was simply not done.
    r"|at the ledger's ([\d,]+) cumulative hypotheses"
    # CLAUDE.md's own phrasing. It was unmatched by every pattern above, so the
    # file could — and did — state the family size as 95 for a whole day after
    # the ledger reached 98 with nothing checking it.
    r"|[Tt]he ledger holds \*\*([\d,]+) distinct\s+hypotheses"
)


def _generated_documents() -> list[Path]:
    return sorted(OUTPUTS.rglob("*.md")) + sorted(DOCS.rglob("*.md"))


#: Every document that MUST state the family size it corrects by, by name.
#:
#: **A roster, not a count.** This guard used to end at `assert checked >= 8`
#: over the whole tree, and the tree yields 13 — so five documents could stop
#: stating a correction at all and the floor still passed. That is not a
#: hypothetical: `what_we_can_claim.render` emits its sentence only when a
#: ledger was applied, so one render beside a missing ledger drops two of these
#: files to zero matches, and seven of the thirteen have no other freshness
#: check on them — they are not in the byte-equality parametrisation below and
#: not in `HAND_WRITTEN`. A floor that is a sum cannot name what went missing;
#: a roster can, and it goes red on the file rather than on the total.
#:
#: A document that legitimately stops carrying a correction is removed from
#: here in the same commit, which is a line in a diff somebody has to justify.
DOCUMENTS_THAT_STATE_A_CORRECTION: tuple[str, ...] = (
    "data/outputs/cbb_experiment_ledger.md",
    "data/outputs/cbb_forecast_skill.md",
    "data/outputs/cbb_forward_evidence.md",
    "data/outputs/cbb_price_backtest.md",
    "data/outputs/cbb_prop_grading.md",
    "data/outputs/cbb_ratings_fit.md",
    "data/outputs/cbb_reachability.md",
    "data/outputs/cbb_what_we_can_claim.md",
    "data/outputs/cbb_why_the_model.md",
    "data/outputs/core_team_only/cbb_price_backtest.md",
    "data/outputs/holdout/cbb_price_backtest.md",
    "data/outputs/holdout/cbb_replication.md",
    "docs/what_we_can_and_cannot_claim.md",
    "docs/why_the_model_does_or_does_not_have_an_edge.md",
    # Hand-written, and on the roster for exactly that reason. Registering the
    # forward window moved the ledger 95 -> 98 and left NINE sentences across
    # this file and CLAUDE.md stating the old count — the roster did not name
    # it, and `HAND_WRITTEN` only checks whether a QUOTED INTERVAL is stale,
    # never whether the document states the wrong family size outright. So the
    # whole registration shipped green with the count wrong in both.
    "docs/project_status.md",
)


@pytest.mark.parametrize("relative", DOCUMENTS_THAT_STATE_A_CORRECTION)
def test_each_document_on_the_roster_states_the_ledgers_current_count(relative):
    """Named, so a document that stops stating a correction fails as itself."""
    looks = ledger_looks()
    path = REPO / relative
    assert path.is_file(), (
        f"{relative} is on the roster of documents that must state their family "
        "correction and is not on disk. Either re-render it or take it off the "
        "roster in this commit."
    )
    text = path.read_text(encoding="utf-8")
    stated = [
        next(group for group in match.groups() if group)
        for match in CORRECTION_SENTENCES.finditer(text)
    ]
    assert stated, (
        f"{relative} states no family correction at all. Every interval it "
        "prints is then uncorrected with nothing on the page saying so — which "
        "is what `what_we_can_claim.render` does when it is rendered beside a "
        "ledger it cannot read. Re-render it beside the ledger, or add the new "
        "phrasing to CORRECTION_SENTENCES if the wording changed."
    )
    for value in stated:
        assert int(value.replace(",", "")) == looks, (
            f"{relative} states its correction over {value} hypotheses and the "
            f"experiment ledger holds {looks:,}. Re-render it: a verdict stated "
            "at a narrower correction than the search that produced it is the "
            "defect decision 46 closed."
        )


def test_the_roster_names_every_document_that_states_a_correction():
    """The roster cannot silently fall behind the tree.

    The failure the roster replaces was a document dropping off a count. The
    failure a roster introduces is a NEW document nobody added to it, so that
    one is closed here: any generated document that states a correction and is
    not on the roster fails, by name.
    """
    on_disk = {
        path.relative_to(REPO).as_posix()
        for path in _generated_documents()
        if CORRECTION_SENTENCES.search(path.read_text(encoding="utf-8"))
    }
    roster = set(DOCUMENTS_THAT_STATE_A_CORRECTION)
    assert on_disk - roster == set(), (
        f"{sorted(on_disk - roster)} state a family correction and are not on "
        "DOCUMENTS_THAT_STATE_A_CORRECTION, so nothing checks that theirs is "
        "current. Add them."
    )
    assert roster - on_disk == set(), (
        f"{sorted(roster - on_disk)} are on the roster and state no correction. "
        "That is the exact hole the roster exists to catch."
    )


@pytest.mark.parametrize(
    "record_name,report_name,module",
    [
        ("cbb_price_backtest.json", "cbb_price_backtest.md", "price_backtest"),
        (
            "core_team_only/cbb_price_backtest.json",
            "core_team_only/cbb_price_backtest.md",
            "price_backtest",
        ),
        (
            "holdout/cbb_price_backtest.json",
            "holdout/cbb_price_backtest.md",
            "price_backtest",
        ),
        (
            "holdout/cbb_replication.json",
            "holdout/cbb_replication.md",
            "replication",
        ),
        ("cbb_forecast_skill.json", "cbb_forecast_skill.md", "forecast_skill"),
        # Added 2026-09-07 with the grading commit. Its record carries a second
        # derived layer the others do not — the headline comparison and the
        # answered-hypothesis table are functions of several cells at once — so
        # a re-render that moved only the stored intervals would leave both
        # stale on the page beside fresh bounds. `prop_grading.restated`
        # re-derives them, and this is the gate that says so.
        ("cbb_prop_grading.json", "cbb_prop_grading.md", "prop_grading"),
    ],
)
def test_the_committed_report_is_the_record_rendered_at_todays_count(
    record_name, report_name, module
):
    """The gate that fails the day a hypothesis is registered and nothing is
    re-rendered — which is the day the reports used to quietly go stale."""
    renderer = {
        "price_backtest": PB,
        "replication": REPL,
        "forecast_skill": FS,
        "prop_grading": PG,
    }[module]
    record = json.loads((OUTPUTS / record_name).read_text(encoding="utf-8"))
    looks = RESTATEMENT.widened(
        int(record.get("looks", 1) or 1),
        RESTATEMENT.Correction(
            looks=ledger_looks(),
            factor=S.bonferroni_factor(ledger_looks()),
            found=True,
            source=str(LEDGER),
        ),
    )
    expected = renderer.render(
        renderer.restated(
            record,
            looks=looks,
            record_name=Path(record_name).name,
        )
    )
    assert (OUTPUTS / report_name).read_text(encoding="utf-8") == expected, (
        f"data/outputs/{report_name} is not what data/outputs/{record_name} "
        f"renders to at the ledger's {ledger_looks():,} hypotheses. Re-render "
        "it with --rebuild-report-only; it costs no store and no credit."
    )


def test_the_ratings_fit_report_is_current_too():
    """`scripts/fit_ratings.py` owns its own renderer, so it is loaded by path
    rather than imported — and it is checked, because a report left out of a
    guard is a report the guard was written for."""
    fit = _load_script("fit_ratings")
    record = json.loads(
        (OUTPUTS / "cbb_ratings_fit.json").read_text(encoding="utf-8")
    )
    looks = max(int(record.get("looks", 1) or 1), ledger_looks())
    expected = fit.render(
        fit.restated(record, looks=looks, record_name="cbb_ratings_fit.json")
    )
    assert (OUTPUTS / "cbb_ratings_fit.md").read_text(encoding="utf-8") == expected


def test_the_records_keep_what_they_measured():
    """The other half of decision 46: a re-render does not rewrite the record.

    The record is the evidence of what was computed and when. Overwriting its
    verdicts under a later correction would destroy the only copy of the
    measurement and make its `generated_at` a lie — so every record still
    carries its own `looks`, and at least one of them is deliberately behind
    the ledger.
    """
    stored = {}
    for name in (
        "cbb_price_backtest.json",
        "cbb_forecast_skill.json",
        "cbb_ratings_fit.json",
        "holdout/cbb_replication.json",
    ):
        payload = json.loads((OUTPUTS / name).read_text(encoding="utf-8"))
        stored[name] = int(payload.get("looks", 0) or 0)
        assert stored[name] >= 1, f"{name} records no family size at all"
        assert payload.get("correction_factor"), f"{name} records no factor"
    assert any(value < ledger_looks() for value in stored.values()), (
        "every record now matches the ledger, which is fine — but this test "
        "was written while some did not, and it exists to state that a record "
        "behind the ledger is a correct record and not a broken one. If the "
        "records were rewritten to match, decision 46 was reversed."
    )


def test_restating_is_idempotent():
    record = json.loads(
        (OUTPUTS / "cbb_price_backtest.json").read_text(encoding="utf-8")
    )
    once = PB.restated(record, looks=95, record_name="r.json")
    twice = PB.restated(copy.deepcopy(once), looks=95, record_name="r.json")
    assert twice["looks"] == 95
    assert PB.render(once) == PB.render(twice)


def test_a_coefficient_is_restated_through_its_own_class():
    """`Coefficient.verdict` raises for every term but the disagreement, so a
    generic rebuild would either crash or invent a verdict for the market
    coefficient — the one that excludes zero on the positive side and would be
    announced as a demonstrated edge by a predicate that never asked what the
    null was."""
    record = json.loads(
        (OUTPUTS / "cbb_forecast_skill.json").read_text(encoding="utf-8")
    )
    moved = FS.restated(record, looks=400, record_name="x")
    seen = 0
    for _, cell in _cells(moved):
        if "answers_the_question" not in cell:
            continue
        seen += 1
        if cell["answers_the_question"]:
            continue
        assert "verdict" not in cell, (
            f"{cell['name']!r} acquired a verdict during a re-render. Only the "
            "disagreement coefficient's sign is a claim about skill."
        )
    assert seen >= 3, "no coefficients were checked"


def test_the_shared_shape_table_covers_every_committed_cell():
    """Every stored interval in the repository is restateable.

    A cell this module cannot recognise is a cell that keeps its old
    correction for ever while everything around it moves, and nothing on the
    page would say so.
    """
    unknown: list[str] = []
    for path in sorted(OUTPUTS.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))

        def walk(node, where=""):
            if isinstance(node, dict):
                if "standard_error" in node and "adjusted_low" in node:
                    if RESTATEMENT.shape_of(node) is None:
                        unknown.append(f"{path.name}{where}")
                for key, value in node.items():
                    walk(value, f"{where}/{key}")
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, f"{where}[{index}]")

        walk(payload)
    assert not unknown, (
        "these stored intervals carry a standard error and corrected bounds "
        f"under a centre `restatement.CELL_SHAPES` does not name: {unknown[:5]}"
    )


def test_a_restated_report_names_both_counts():
    """(b), the provenance half. A reader is told what the run was scored at
    and what the verdicts are stated at, so no number on the page is anonymous.
    """
    record = json.loads(
        (OUTPUTS / "cbb_price_backtest.json").read_text(encoding="utf-8")
    )
    text = PB.render(PB.restated(record, looks=400, record_name="cbb_x.json"))
    assert "400 hypotheses" in text
    assert f"{int(record['looks']):,} cumulative hypotheses" in text
    assert "cbb_x.json" in text
    assert "does not move" in text

    same = PB.render(PB.restated(record, looks=int(record["looks"]), record_name="x"))
    assert "stated at the ledger's count as of this render" not in same, (
        "a report that was not restated gained a paragraph saying it was"
    )


# ---------------------------------------------------------------------------
# 4. The two hand-written documents
# ---------------------------------------------------------------------------
#
# `CLAUDE.md` and `docs/project_status.md` have no generator, so nothing
# re-renders them and the section above cannot see them. They are where the
# blocking defect actually sat: row 12 of the status file printed low-major as
# a demonstrated deficit at the bounds the record was scored with, months of
# hypotheses after the ledger had widened past it. A hand-written document is
# still a document, so the same rule holds — it may quote a headline cell only
# at the correction the ledger owes now, unless it says in its own words which
# narrower correction the number carries.

HAND_WRITTEN = ("CLAUDE.md", "docs/project_status.md")


def test_every_hand_written_document_states_the_ledgers_current_count():
    """The hole that let nine sentences go stale in one commit.

    `HAND_WRITTEN` was already checked — but only for whether a QUOTED
    INTERVAL was stale, never for whether the document states the wrong FAMILY
    SIZE outright. Registering the forward window moved the ledger 95 -> 98 and
    left nine sentences across these two files saying 95 and x1.7689, and the
    whole registration shipped green.

    A hand-written file may still describe history — "took the family from 62
    to 95" is a true sentence about 2026-09-05 — so this checks only the counts
    stated in the present tense, which is what `CORRECTION_SENTENCES` matches.
    """
    looks = ledger_looks()
    for name in HAND_WRITTEN:
        text = (REPO / name).read_text(encoding="utf-8")
        stated = {
            int(group.replace(",", ""))
            for found in CORRECTION_SENTENCES.finditer(text)
            for group in found.groups()
            if group
        }
        assert stated, (
            f"{name} states no family size in any phrasing this guard knows. "
            "Either it stopped naming the correction its figures carry, or it "
            "grew a phrasing that must be added to CORRECTION_SENTENCES — "
            "which is exactly how the last one went unnoticed."
        )
        assert stated == {looks}, (
            f"{name} states the family correction at {sorted(stated)} and the "
            f"experiment ledger holds {looks}. Re-derive its figures at the "
            "current count, or mark the stale number as history in the same "
            "sentence."
        )


def _at(payload, *path):
    """One cell out of a record by an explicit path, or a failure that says so."""
    node = payload
    for step in path:
        try:
            node = node[step]
        except (KeyError, IndexError, TypeError):  # pragma: no cover - guard
            raise AssertionError(
                f"no cell at {list(path)} in this record; the roster below "
                "names a cell the record no longer has, so it is checking "
                "nothing. Fix the path rather than dropping the entry."
            )
    assert RESTATEMENT.is_interval_cell(node), (
        f"{list(path)} is not a stored interval, so a correction cannot be "
        "re-derived for it"
    )
    return node


def _tier(payload, key, tier):
    """The index of a tier's row. The price backtest keys it `tier`, the
    forecast-skill record keys it `label`; both are read rather than guessed."""
    for index, row in enumerate(payload[key]):
        if tier in (row.get("tier"), row.get("label")):
            return index
    raise AssertionError(f"no {tier!r} row in {key}")


def _headline_cells() -> dict[str, dict]:
    """Every cell whose verdict the two hand-written documents state.

    Named individually rather than swept up, because the sweep is what the
    generated documents get: these two are quoted by hand, so the roster is the
    list of numbers a human has to retype when the ledger moves.
    """
    backtest = json.loads(
        (OUTPUTS / "cbb_price_backtest.json").read_text(encoding="utf-8")
    )
    skill = json.loads(
        (OUTPUTS / "cbb_forecast_skill.json").read_text(encoding="utf-8")
    )
    replication = json.loads(
        (OUTPUTS / "holdout" / "cbb_replication.json").read_text(encoding="utf-8")
    )
    props = json.loads(
        (OUTPUTS / "cbb_prop_grading.json").read_text(encoding="utf-8")
    )
    cells: dict[str, dict] = {}
    for tier in ("high_major", "mid_major", "low_major"):
        index = _tier(backtest, "by_tier", tier)
        cells[f"price backtest / {tier} ROI"] = _at(backtest, "by_tier", index)
        skill_index = _tier(skill, "by_tier", tier)
        cells[f"forecast skill / {tier} Brier vs raw"] = _at(
            skill, "by_tier", skill_index, "brier", "advantage_over_raw"
        )
        coefficients = skill["by_tier"][skill_index]["fit"]["coefficients"]
        position = next(
            i for i, c in enumerate(coefficients) if c["name"] == "disagreement"
        )
        cells[f"forecast skill / {tier} disagreement"] = _at(
            skill, "by_tier", skill_index, "fit", "coefficients", position
        )
    selected = skill["selected"]["by_tier"][0]["fit"]["coefficients"]
    position = next(
        i for i, c in enumerate(selected) if c["name"] == "disagreement"
    )
    cells["forecast skill / selected-bets disagreement"] = _at(
        skill, "selected", "by_tier", 0, "fit", "coefficients", position
    )
    market = next(
        i
        for i, row in enumerate(replication["markets"])
        if (row.get("market"), row.get("tier")) == ("total_points", "mid_major")
    )
    cells["replication / total_points mid-major held out"] = _at(
        replication, "markets", market, "holdout"
    )

    # The player-prop cells. **These were missing, and published intervals went
    # stale behind the gap.** The roster was built from three records and pinned
    # at eleven, so every prop figure the two hand-written documents quote was
    # outside the guard's reach.
    #
    # **The first repair added four of six and pinned the count at four**, which
    # made the roster assert as fact that the documents quote four -- so an
    # author completing it was met by a red test telling them they were wrong.
    # The no-pooled rule guarantees a headline advantage PER TIER, so there are
    # three of those, not one. The two that were still uncovered were also both
    # wrong: the documents carried a point estimate and bounds that match no
    # correction of this cell at any count.
    #
    # `devig_power__conditional` and `control__conditional` are named outright
    # rather than reached through an "unconditional if present" fallback. The
    # record carries both variants of each; for high-major they differ in the
    # seventh decimal, which is invisible at the four the documents print and
    # would stop being invisible without warning. The report labels the
    # conditional one HEADLINE, so that is the one a reader meets.
    for tier in ("high_major", "mid_major", "low_major"):
        index = _tier(props, "by_tier", tier)
        cells[f"prop grading / {tier} de-vig headline"] = _at(
            props, "by_tier", index, "advantages", "devig_power__conditional"
        )
        cells[f"prop grading / {tier} role-prior control"] = _at(
            props, "by_tier", index, "advantages", "control__conditional"
        )
    pra = next(
        i
        for i, row in enumerate(props["by_market_and_tier"])
        if (row.get("market"), row.get("tier")) == ("player_pra", "high_major")
    )
    cells["prop grading / player_pra high-major"] = _at(
        props, "by_market_and_tier", pra, "advantages", "devig_power__conditional"
    )

    assert len(cells) == 18, sorted(cells)
    return cells


def _spellings(cell: dict, looks: int) -> tuple[str, ...]:
    """A cell's corrected interval in every spelling these two files use.

    Percentages to a tenth for a return, five decimals for a Brier advantage,
    three for a fitted coefficient. A document that grows a fourth spelling has
    to add it here before it can quote a stale number in it.

    **It grew one and this was not updated.** Re-deriving CLAUDE.md's
    disagreement coefficients at 98 hypotheses wrote them SIGNED to five
    decimals -- `-0.04527 to +0.22045` -- while this produced only the unsigned
    `-0.04527 to 0.22045`. Four of the eleven headline cells were therefore
    quoted in a spelling no pattern here could match, so the guard that exists
    to catch a stale figure could not have seen those four go stale. The
    docstring above said exactly what to do; it simply was not done.

    **And it grew a fifth.** The player-prop figures are written to FOUR
    decimals (`-0.0387 to +0.0257`), which no pattern here matched either --
    so even once those cells reached the roster the guard would have kept
    quiet about them. Two spellings added late, for the same reason both
    times: a document was written first and the guard was updated never.
    """
    rebuilt = RESTATEMENT.rebuild_cell(cell, looks=looks)
    low, high = rebuilt["adjusted_low"], rebuilt["adjusted_high"]
    return (
        f"{low * 100:+.1f}% to {high * 100:+.1f}%",
        f"{low:.5f} to {high:.5f}",
        f"{low:+.5f} to {high:+.5f}",
        f"{low:+.3f} to {high:+.3f}",
        f"{low:+.4f} to {high:+.4f}",
    )


def _and_list(counts) -> str:
    """`92`, `92 or 95`, `85, 92 or 95` — the counts a reading could be stated at."""
    spelled = [f"{count:,}" for count in counts]
    if len(spelled) == 1:
        return spelled[0]
    return f"{', '.join(spelled[:-1])} or {spelled[-1]}"


def _stale_spellings(cell, earlier, live) -> dict[str, list[int]]:
    """Every superseded spelling of a cell, mapped to the counts that produce it.

    **One spelling is usually the reading at several counts.** A tier ROI shown
    to a tenth of a percent moves by less than 0.05pp across a whole
    registration, so `-8.1% to +0.0%` is what this lab owed at 85, at 92, at 95
    and at 98 alike. Asking a sentence to name *all four* is asking for
    something no sentence can say, and the earlier form of this guard did
    exactly that: it demanded the sentence name 92 while the sentence named 95,
    for a figure identical at both, and the only way to satisfy it was to stop
    narrating the history. Naming **one** count at which the quoted figure is
    the reading is complete provenance, which is what decision 46 asks for.

    Nothing is given up by this. A sentence that names no count at all still
    fails, and so does one that names a count whose reading is a different
    figure — the spelling at 62 is `-8.0% to -0.1%`, and a sentence quoting it
    while saying "at 101" names a count that is not in this map's list for it.
    """
    by_spelling: dict[str, list[int]] = {}
    for looks in earlier:
        for spelling in _spellings(cell, looks):
            if spelling in live:
                continue
            counts = by_spelling.setdefault(spelling, [])
            # De-duplicated, because several spellings of one cell collide: a
            # cell whose bounds are both negative renders identically under the
            # unsigned and the signed five-decimal forms, so one count was
            # appended twice and `_and_list` read back "85 or 85".
            if looks not in counts:
                counts.append(looks)
    return by_spelling


def _registration_counts() -> list[int]:
    """Every cumulative count this ledger has passed through.

    A **superset** of the corrections that were ever really in force, and
    deliberately so: checking a count nobody published at costs one comparison,
    while missing one is how a stale number survives.

    **It used to be derived from registration BOUNDARIES and was not a superset
    at all.** A boundary was recorded only at the first entry of each new
    `(search, tested_on)` pair -- but the ledger's uniqueness rule is
    `(search, name, seasons, stage)`, so appending a hypothesis to an EXISTING
    search on that search's own date is legal and moves the cumulative count
    without recording anything. The count the documents were written at then
    drops out of the set, every published figure becomes a reading at a count
    this function does not enumerate, no spelling is generated for any of them,
    and the guard passes having checked nothing. Demonstrated end to end: one
    appended entry reusing `(rebound_differential_vs_spread, 2026-09-10)` takes
    the ledger to 102 and leaves 101 unlisted, after which a figure left behind
    at 101 sits unmarked in CLAUDE.md with every guard green.

    So the range is every prefix from TWO. There is no cleverness left in it to
    be wrong.

    Two rather than one because `bonferroni_factor(1)` is 1: at a family of one
    the "corrected" interval IS the uncorrected one, which both documents publish
    on purpose -- `-6.3% to -1.7%`, in the sentence arguing that what moved is
    the search and not the measurement. Treating that as a stale reading at a
    family of 1 is a false red, and the uncorrected interval has its own guard:
    `_uncorrected_spellings` with a pinned occurrence count.
    """
    payload = json.loads(LEDGER.read_text(encoding="utf-8"))
    return list(range(2, len(payload["hypotheses"]) + 1))


#: Where one statement ends and the next begins: a sentence's own punctuation,
#: a line break, or a markdown cell wall. Sentence-level rather than
#: paragraph-level on purpose — row 12 of `docs/project_status.md` is a single
#: paragraph the size of a page, and "somewhere in this paragraph a correction
#: is named" would have licensed every stale number in it. A decimal point is
#: not a boundary, because the split needs whitespace after the punctuation.
SENTENCE = re.compile(r"(?<=[.;:!?])\s+|\n|\|")


#: A line that OPENS a block rather than continuing the previous one.
#:
#: **There is no numbered-list branch, and the omission is deliberate.** A
#: `\d+[.)]\s` alternative was here and did one thing to these documents: it cut
#: `...the family: 62 hypotheses became` / `95. The uncorrected interval...` in
#: half, because the continuation of a hard-wrapped sentence happened to begin
#: with a number and a full stop. Zero right splits, one wrong one -- and the
#: wrong one is exactly the shape this guard reads, a count separated from the
#: figure it belongs to. A real numbered list item is preceded either by a blank
#: line or by a line ending in a sentence terminator, and both of those already
#: refuse the join, so the branch bought nothing it was not already getting.
BLOCK_OPENER = re.compile(
    r"^(?:\||[-*+]\s|#{1,6}\s|>|```|-{3,}$|\*{3,}$|_{3,}$|$)"
)

#: Closing delimiters that can sit AFTER a sentence's full stop.
#:
#: `line.rstrip().endswith(...)` tests the last character, and this repository's
#: house style ends a lede sentence `**like this.**` -- so the terminator was
#: masked by the bold marker and `_unwrapped` joined straight through it, on ten
#: committed lines. `SENTENCE` could not recover either: it needs the terminator
#: immediately before the whitespace, and after the join the character there is
#: `*`. Two blocks became one chunk and a count in the first vouched for every
#: figure in the second.
CLOSING_DELIMITERS = "*_`\"')]}"


def _unwrapped(text: str) -> str:
    """The file's prose with SOFT WRAPS joined -- and nothing else.

    **A figure straddling a line break was invisible to this guard.** These two
    documents are hard-wrapped, so `-0.02199 to -0.01127` is written across two
    lines as often as not, and a literal substring search does not find it.
    Both tests below then skipped the cell in silence: one because it looks for
    superseded spellings and found none, the other because it only fires on a
    cell the file is seen to quote. Five of CLAUDE.md's eleven headline cells
    were in that state -- unguarded, and indistinguishable from a file that
    simply does not mention them. Re-wrapping a paragraph is not supposed to
    decide whether a number is checked.

    **The first fix for that flattened every run of whitespace, and that was
    too much.** `SENTENCE` splits on `\n` as well as on `.;:!?` and `|`, so
    erasing every newline erased a boundary the splitter depends on: measured on
    these two files it halved the chunk count (905 -> 457) and nearly doubled
    the longest chunk (273 -> 525 characters). The guard's whole premise is
    sentence-level scope -- "a correction named at the far end of it is attached
    to nothing" -- so doubling what counts as one sentence lets a correction
    named in one block vouch for a figure in the next. No committed document
    exploited it, which is exactly why it needed catching by construction rather
    than by inspection.

    So join only a newline that is a SOFT WRAP: the previous line does not end a
    sentence or a table row, and the next line continues prose rather than
    opening a block. Every other newline survives as the boundary it was.
    """
    out: list[str] = []
    lines = text.split("\n")
    joined = False
    for index, line in enumerate(lines):
        # A continuation carries the paragraph's indent; joining has to drop it
        # or the figure reads `-0.02199   to -0.01127` and still does not match.
        out.append(line.lstrip() if joined else line)
        if index + 1 >= len(lines):
            break
        soft = bool(
            line.strip()
            and not line.rstrip().rstrip(CLOSING_DELIMITERS).endswith(
                ("|", ".", ";", ":", "!", "?")
            )
            and not BLOCK_OPENER.match(lines[index + 1].lstrip())
        )
        out.append(" " if soft else "\n")
        joined = soft
    return "".join(out)


def _sentences(text: str) -> list[str]:
    return [part for part in SENTENCE.split(_unwrapped(text)) if part.strip()]


#: An explicit attribution: the figure before it is stated at THAT family size.
#:
#: **This replaces four rounds of trying to infer the same thing from prose.**
#: The guard used to read a sentence and decide which integer in it was a family
#: size. `\b62\b` matched inside `62,163 rows`; anchoring it left `85th`
#: vouching for 8 and `decision 46` for 4; gating on the sentence mentioning
#: "corrected" did nothing, because every sentence quoting an interval says
#: "corrected"; narrowing that left `corrected at 95 percent confidence` and, on
#: the committed file, `-- 30 discovery entries`. Each round the heuristic got
#: cleverer and ordinary English beat it again, because "which number here is a
#: family size" is not a question a regex can answer about English.
#:
#: So the document says it outright. `-8.0% to -0.1% [@62]` is unambiguous to a
#: parser and to a reader, and it cannot be satisfied by a row count, an ordinal,
#: a decision number or a percentage that happens to sit nearby.
ATTRIBUTION = re.compile(r"\s*(?:\*{1,2}|_{1,2}|`)*\s*\[@(\d+)\]")


def _attributed_to(text: str, position: int) -> int | None:
    """The count a figure ending at `position` is explicitly stated at."""
    match = ATTRIBUTION.match(text, position)
    return int(match.group(1)) if match else None


#: Roster cells the two hand-written documents quote. Their LIVE reading has to
#: be findable in one of them.
#:
#: **The stale-figure guards cannot see a figure that is simply WRONG.** They
#: work by finding a superseded spelling; a number matching no correction of the
#: cell at any count matches nothing, so the cell is skipped in silence. Two
#: published de-vig headlines sat in both documents in exactly that state --
#: `-0.0139 to +0.0024` and `-0.0102 to +0.0011`, which no count produces -- with
#: point estimates that were wrong too, and every guard green. Requiring the
#: live spelling to be PRESENT is the complement: stale figures are caught by
#: what they say, wrong ones by what they fail to say.
QUOTED_CELLS = frozenset(
    {
        f"forecast skill / {tier} {measure}"
        for tier in ("high_major", "mid_major", "low_major")
        for measure in ("Brier vs raw", "disagreement")
    }
    | {f"price backtest / {tier} ROI" for tier in ("high_major", "mid_major", "low_major")}
    | {f"prop grading / {tier} de-vig headline" for tier in ("high_major", "mid_major", "low_major")}
    | {f"prop grading / {tier} role-prior control" for tier in ("high_major", "mid_major")}
    | {
        "forecast skill / selected-bets disagreement",
        "prop grading / player_pra high-major",
        "replication / total_points mid-major held out",
    }
)


def _uncorrected_spellings(cell: dict) -> tuple[str, ...]:
    """A cell's UNCORRECTED interval, in the forms these documents write.

    `_spellings` renders only `adjusted_low`/`adjusted_high`, so the record's own
    `low`/`high` were unreachable by every test in this file -- while both
    documents publish `-6.3% to -1.7%` in the sentence carrying the argument
    "what moved is the search and not the measurement". An interval nothing can
    check is an interval anyone can retype.
    """
    low, high = cell["low"], cell["high"]
    return (
        f"{low * 100:+.1f}% to {high * 100:+.1f}%",
        f"{low:+.4f} to {high:+.4f}",
        f"{low:+.5f} to {high:+.5f}",
    )


#: How many times each document quotes each cell, corrected and uncorrected.
#:
#: **Pinned as counts, because presence is not enough.** The check was
#: `any(spelling in document)` -- satisfied by ONE surviving correct occurrence.
#: `price backtest / low_major ROI` is written three times in CLAUDE.md, so two
#: of the three could be replaced with fabricated numbers and every guard stayed
#: green: a stale figure is caught by what it says, a fabricated one only by
#: something noticing it is no longer there.
#:
#: Editing prose that adds or removes a mention fails here until this is updated.
#: That is the intended cost; the number of times a lab states a finding is not
#: something that should drift silently either.
QUOTED_OCCURRENCES = {
    ("CLAUDE.md", "price backtest / low_major ROI"): (1, 1),
    ("docs/project_status.md", "price backtest / low_major ROI"): (1, 1),
}


@pytest.mark.parametrize("document", HAND_WRITTEN)
def test_each_cell_is_quoted_exactly_as_often_as_it_should_be(document):
    """Every occurrence carries the live reading, not just one of them."""
    text = _unwrapped((REPO / document).read_text(encoding="utf-8"))
    cells = _headline_cells()
    for name in sorted(QUOTED_CELLS):
        corrected, uncorrected = QUOTED_OCCURRENCES.get((document, name), (1, 0))
        seen = sum(
            text.count(spelling)
            for spelling in set(_spellings(cells[name], ledger_looks()))
        )
        assert seen == corrected, (
            f"{document} states the current reading of {name!r} {seen} time(s); "
            f"{corrected} expected. If an occurrence was replaced by a figure no "
            "correction of this cell produces, the stale-figure guards cannot see "
            "it -- a wrong number matches no spelling. If the prose legitimately "
            "gained or lost a mention, move the count in QUOTED_OCCURRENCES."
        )
        seen_raw = sum(
            text.count(spelling) for spelling in set(_uncorrected_spellings(cells[name]))
        )
        assert seen_raw == uncorrected, (
            f"{document} states the UNCORRECTED interval of {name!r} {seen_raw} "
            f"time(s); {uncorrected} expected. These are published beside the "
            "corrected ones and nothing else in this file reaches them."
        )


@pytest.mark.parametrize("document", HAND_WRITTEN)
def test_every_cell_the_documents_quote_carries_its_live_reading(document):
    """Per document, not over the two concatenated.

    Both files quote all seventeen of these cells, so a wrong figure in one of
    them is not excused by the other being right -- and over the concatenation it
    was: changing a de-vig headline in CLAUDE.md to a value no correction
    produces left the test green on the copy in docs/project_status.md.
    """
    quoted = _unwrapped((REPO / document).read_text(encoding="utf-8"))
    cells = _headline_cells()
    missing = set(QUOTED_CELLS) - set(cells)
    assert not missing, f"QUOTED_CELLS names cells the roster does not: {sorted(missing)}"
    for name in sorted(QUOTED_CELLS):
        spellings = _spellings(cells[name], ledger_looks())
        assert any(spelling in quoted for spelling in spellings), (
            f"{document} does not carry the current reading of "
            f"{name!r}. Expected one of {list(spellings)}. Either the figure was "
            "changed to something no correction of this cell produces -- which "
            "the stale-figure guards cannot see, because a wrong number matches "
            "no spelling -- or this document stopped quoting the cell, in which "
            "case take it out of QUOTED_CELLS in this commit."
        )


#: Every boundary `_unwrapped` must not join across, one fixture per condition.
#:
#: **An earlier version had five fixtures and killed two of thirteen
#: conditions.** Each tripped several at once, so most branches could be deleted
#: with the test still green. Every case below is built so that exactly one
#: condition stands between the figure and the foreign count.
BOUNDARY_CASES = {
    "table row": "| tier | -8.1% to +0.0% |\n| the family holds 101 hypotheses |",
    "table row after prose": "low-major reads -8.1% to +0.0%\n| the family holds 101 hypotheses |",
    "bullet": "- low-major reads -8.1% to +0.0%\n- the family holds 101 hypotheses",
    "star bullet": "* low-major reads -8.1% to +0.0%\n* the family holds 101 hypotheses",
    "plus bullet": "+ low-major reads -8.1% to +0.0%\n+ the family holds 101 hypotheses",
    "heading": "low-major reads -8.1% to +0.0%\n### the family holds 101 hypotheses",
    "blockquote": "low-major reads -8.1% to +0.0%\n> the family holds 101 hypotheses",
    "fence": "low-major reads -8.1% to +0.0%\n```\nthe family holds 101 hypotheses",
    "blank line": "low-major reads -8.1% to +0.0%\n\nthe family holds 101 hypotheses",
    "thematic break": "low-major reads -8.1% to +0.0%\n---\nthe family holds 101 hypotheses",
}

#: A line ending in one of these ends a sentence, so the next line is new.
#:
#: **Written out, not generated from the implementation's own tuple.** They were
#: a comprehension over the same six characters the predicate checks, so the
#: fixtures could only confirm the clause that existed -- and the whole class of
#: terminator-plus-closing-delimiter (`.**`, `.)`, `."`), which this repository
#: writes constantly, was invisible to them.
TERMINATOR_CASES = {
    ending: f"low-major reads -8.1% to +0.0%{ending}\nthe family holds 101 hypotheses"
    for ending in (
        ".", ";", ":", "!", "?", "|",
        ".**", ".)", '."', ".'", ".`", ".]", ".}", ".*", ".__",
        "!**", "?)", ";**", ":**",
    )
}


@pytest.mark.parametrize("label", sorted(BOUNDARY_CASES))
def test_unwrapping_keeps_each_block_boundary(label):
    """One boundary per case, and nothing else keeping the two apart."""
    chunks = [c for c in SENTENCE.split(_unwrapped(BOUNDARY_CASES[label])) if c.strip()]
    holding = [c for c in chunks if "-8.1% to +0.0%" in c]
    assert holding, f"{label}: the figure vanished from every chunk: {chunks!r}"
    assert not any("101" in c for c in holding), (
        f"{label}: the figure shares a chunk with a correction count that does "
        f"not belong to it, so that count vouches for it. Chunks: {chunks!r}"
    )


@pytest.mark.parametrize("terminator", sorted(TERMINATOR_CASES))
def test_unwrapping_does_not_join_across_a_sentence_terminator(terminator):
    chunks = [c for c in SENTENCE.split(_unwrapped(TERMINATOR_CASES[terminator])) if c.strip()]
    holding = [c for c in chunks if "-8.1% to +0.0%" in c]
    assert holding and not any("101" in c for c in holding), (
        f"a line ending in {terminator!r} was joined to the next, so a count in "
        f"the following sentence vouches for this one. Chunks: {chunks!r}"
    )


def test_unwrapping_joins_a_soft_wrap_and_preserves_every_character():
    """The other half: a wrap INSIDE a sentence must close up, losing nothing."""
    joined = _unwrapped("corrected -0.02199\n  to -0.01127 over 62,163 rows.")
    assert "-0.02199 to -0.01127" in joined, (
        f"a soft wrap inside a sentence is no longer joined: {joined!r}"
    )
    # A continuation that merely looks like a list item is still a continuation.
    numbered = _unwrapped("the family: 62 hypotheses became\n95. The interval held.")
    assert "became 95." in numbered, (
        f"a wrapped sentence whose continuation starts with a number was split: "
        f"{numbered!r}"
    )
    for name in HAND_WRITTEN:
        text = (REPO / name).read_text(encoding="utf-8")
        assert re.sub(r"\s+", "", _unwrapped(text)) == re.sub(r"\s+", "", text), (
            f"{name}: _unwrapped changed the document's non-whitespace content. "
            "It may only ever move whitespace."
        )


#: Anything shaped like an interval, in any spelling.
#:
#: **This is the half that was never total.** Everything before it worked by
#: enumerating a cell's renderings and searching for them, so a figure written in
#: a spelling `_spellings` does not emit was not caught -- it was not even
#: looked at. The same stale reading as `-0.0791 to 0.0144` (unsigned), as
#: `-7.91% to +1.44%` (two decimals), or with a U+2212 minus instead of a hyphen
#: passed every guard in this file. Adding those four spellings moves the
#: boundary; it does not close it, because the list of ways to write a number is
#: not finite.
#:
#: So detection stops enumerating and matches the SHAPE, and the default flips
#: from ignore-what-I-do-not-recognise to REFUSE-what-I-do-not-recognise. An
#: interval this file cannot account for is a failure, not a silence.
#: The separator was a literal `\s+to\s+`, which made this an enumeration
#: again -- of the word joining the bounds rather than of the bounds themselves.
#: `-12.4% – +3.1%` (en dash) and `-19.0% *to* -4.2%` ("to" emphasised, this
#: repository's own house style) were not interval-shaped to it, so they were
#: never looked at. An en dash is already in these documents' vocabulary:
#: `2021–2026`. Any dash, and any emphasis around the word, now counts.
#: WHAT THIS DOES NOT REACH. Stated here rather than left to be discovered.
#:
#: Seven rounds of adversarial review went into this function, and each one
#: found a spelling the previous one could not see. These are the ones known to
#: be outside it TODAY, each verified by running `INTERVAL.search` on it:
#:
#:     (-8.0%, -0.1%)          [-8.0%, -0.1%]        -8.0%, -0.1%
#:     between -8.0% and -0.1% -8.0% .. -0.1%        -8.0%/-0.1%
#:     -8.0% − -0.1%           -8.0% - -0.1%         -8.0% TO -0.1%
#:     -4.0% ± 4.1pp           -4.0% ± 4.1%
#:
#: The last pair matters most: `±` is this lab's own convention for the
#: minimum detectable effect, printed beside every null it reports.
#:
#: **The list is not the point; the fact that there is one is.** "Two numbers
#: that together are an interval" has no closed form in English, so a detector
#: over prose is a list of shapes someone thought of, and the next reader thinks
#: of another. Widening it is what the last four rounds did, and each widening
#: was defeated by ordinary writing.
#:
#: The convergent fix is not here. It is for the two hand-written documents to
#: stop carrying figures outside a generated block at all -- at which point the
#: question becomes "is there a digit here", which needs no judgement -- and
#: `scripts/splice_headline_table.py` is the first step of it: the per-tier
#: headline is already generated and already single-source. Everything below is
#: a net under the prose that remains, and a net has holes by construction.
INTERVAL = re.compile(
    r"[-−+]?\d+(?:\.\d+)?\s*%?"
    r"\s*(?:[*_`]*\s*(?:to|through)\s*[*_`]*|[–—])\s*"
    r"[-−+]?\d+(?:\.\d+)?\s*%?"
)

#: Interval-shaped strings in these documents that are not corrected intervals.
#:
#: Count ranges, a bound crossing zero, a season label. Each is checked against
#: every roster cell at every count this ledger has passed through, and an entry
#: that collides with a real reading is refused -- so this list cannot be used to
#: launder a figure, only to name something that was never one.
NOT_A_READING = frozenset(
    {
        "31 to 32",
        "188 to 71",
        "187 to 62",
        "48 to 27",
        "62 to 95",
        "-19 to 2025",
        # Season ranges. Broadening the separator to catch an en dash and an
        # emphasised "to" also catches these, which is the cost of a shape wide
        # enough not to be an enumeration -- and the right cost, because a false
        # red is answered by one line here after the collision check clears it.
        "-19 through 2025",
        "2021–2026",
    }
)


def _readings_by_spelling() -> dict[str, list]:
    """Every spelling of every roster cell, mapped to (cell, count)."""
    index: dict[str, list] = {}
    for label, cell in _headline_cells().items():
        for looks in [*_registration_counts(), ledger_looks()]:
            for spelling in _spellings(cell, looks):
                index.setdefault(spelling, []).append((label, looks))
        for spelling in _uncorrected_spellings(cell):
            index.setdefault(spelling, []).append((label, "uncorrected"))
    return index


def test_no_exemption_collides_with_a_real_reading():
    """`NOT_A_READING` may only name things that are not readings.

    **Checked against every scored reading in every published record**, not just
    the eighteen on this file's roster. Scoped to the roster, any
    correction-dependent figure from an off-roster cell passed the collision
    check and was then exempt forever -- and the failure message of
    `test_every_interval_in_the_document_is_accounted_for` actively invites an
    author to add one. Two committed entries were exactly that: a blind side's
    corrected bound crossing zero, and a coefficient's bound at two superseded
    counts. Both would have stayed exempt, and wrong, as the ledger moved.
    """
    from test_the_forward_window_is_pre_registered import SCORED_RECORDS, _cells

    index = _readings_by_spelling()
    every: dict[str, str] = {}
    for relative in SCORED_RECORDS:
        payload = json.loads(
            (OUTPUTS / relative).read_text(encoding="utf-8")
        )
        for cell in _cells(payload, payload.get("looks")):
            for looks in (*_registration_counts(), ledger_looks()):
                half = S.bonferroni_z(looks) * cell["standard_error"]
                low, high = cell["value"] - half, cell["value"] + half
                for spelling in (
                    f"{low * 100:+.1f}% to {high * 100:+.1f}%",
                    f"{low:+.4f} to {high:+.4f}",
                    f"{low:+.5f} to {high:+.5f}",
                    f"{low:+.6f} to {high:+.6f}",
                    f"{low:+.3f} to {high:+.3f}",
                ):
                    every.setdefault(
                        spelling,
                        f"{relative} {cell.get('tier') or ''}/"
                        f"{cell.get('market') or ''}/{cell.get('name') or ''} "
                        f"at {looks}",
                    )

    for exempt in sorted(NOT_A_READING):
        assert exempt not in index, (
            f"NOT_A_READING lists {exempt!r}, which IS {index[exempt][0][0]}'s "
            f"reading at {index[exempt][0][1]} hypotheses. An exemption that "
            "names a real figure is a hole with a comment over it."
        )
        assert exempt not in every, (
            f"NOT_A_READING lists {exempt!r}, which is a corrected reading of "
            f"{every[exempt]}. It is not on this file's roster, which is why the "
            "narrower check accepted it -- and it will stop being true the next "
            "time the ledger moves, with nothing to notice."
        )


@pytest.mark.parametrize("document", HAND_WRITTEN)
def test_every_interval_in_the_document_is_accounted_for(document):
    """Nothing interval-shaped goes unexamined, whatever spelling it is in.

    Four rounds of this guard worked by looking for figures it already knew how
    to spell, which meant an unrecognised figure was indistinguishable from no
    figure at all. Here an interval is found by its shape and then has to be one
    of four things: today's reading, an attributed historical one, a cell's
    uncorrected interval, or an entry on a short exemption list that is itself
    checked for collisions. There is no fifth option and no silent skip.
    """
    text = _unwrapped((REPO / document).read_text(encoding="utf-8"))
    index = _readings_by_spelling()
    current = ledger_looks()

    for match in INTERVAL.finditer(text):
        spelling = match.group(0).strip()
        if spelling in NOT_A_READING:
            continue
        found = index.get(spelling)
        assert found, (
            f"{document} carries {spelling!r}, which is shaped like a corrected "
            "interval and is not the reading of any cell on the roster at any "
            "count this ledger has held, in any spelling this file renders.\n"
            f"  …{text[max(0, match.start() - 90):match.end() + 40]}…\n"
            "Either it is a stale or fabricated figure -- which is what this "
            "refusal is for -- or it is a real number that is not a corrected "
            "interval, in which case add it to NOT_A_READING, where it will be "
            "checked against every real reading before it is accepted."
        )
        looks = {count for _, count in found}
        if current in looks or "uncorrected" in looks:
            continue
        marked = _attributed_to(text, match.end())
        assert marked is not None, (
            f"{document} carries {spelling!r} -- {found[0][0]} at "
            f"{_and_list(sorted(c for c in looks if isinstance(c, int)))} "
            f"hypotheses, not at today's {current:,} -- with no attribution.\n"
            f"  …{text[max(0, match.start() - 90):match.end() + 40]}…"
        )
        assert marked in looks, (
            f"{document} attributes {spelling!r} to {marked} hypotheses; that is "
            f"not a count any roster cell reads {spelling!r} at."
        )


@pytest.mark.parametrize("document", HAND_WRITTEN)
def test_every_superseded_figure_is_explicitly_attributed(document):
    """A figure stated at anything but today's count says so, in `[@N]`.

    This repository narrates the history of its own verdicts on purpose, so a
    superseded reading in the prose is not a defect -- an UNMARKED one is. The
    rule has no judgement in it: find a figure that is some roster cell's reading
    at some earlier count and is not its reading today, and require the marker
    immediately after it to name a count that produces it.

    What this removes is the inference. There is no sentence to parse, no window
    to size, no vocabulary of family words to maintain, and no way for a bet
    count or an ordinal to vouch for anything.
    """
    text = _unwrapped((REPO / document).read_text(encoding="utf-8"))
    current = ledger_looks()
    earlier = [count for count in _registration_counts() if count < current]
    assert earlier, "this ledger has only ever had one correction to be stale at"

    checked = 0
    for label, cell in _headline_cells().items():
        live = set(_spellings(cell, current))
        for stale, counts in _stale_spellings(cell, earlier, live).items():
            for match in re.finditer(re.escape(stale), text):
                checked += 1
                marked = _attributed_to(text, match.end())
                assert marked is not None, (
                    f"{document} states {label} as `{stale}` -- its reading at "
                    f"{_and_list(counts)} cumulative hypotheses -- with no "
                    f"attribution, while the ledger holds {current:,}. Write "
                    f"`{stale} [@{counts[0]}]` if the history is the point, or "
                    f"re-derive it to `{sorted(live)[0]}` if it is not."
                )
                assert marked in counts, (
                    f"{document} attributes `{stale}` to {marked} hypotheses. "
                    f"That is not a count this cell reads `{stale}` at; the "
                    f"counts that produce it are {_and_list(counts)}."
                )
    assert checked, (
        "no superseded reading was found in either hand-written document, so "
        "this guard checked nothing. That is possible -- but check that the "
        "roster still resolves before believing it."
    )


@pytest.mark.parametrize("document", HAND_WRITTEN)
def test_no_attribution_marks_a_figure_that_is_current(document):
    """The other direction: a marker on a live reading is a false history.

    Without this, `[@62]` could be sprinkled onto correct figures to buy silence
    -- the same shape as pre-filling the retraction table, which the cost check
    refuses for the same reason.
    """
    text = _unwrapped((REPO / document).read_text(encoding="utf-8"))
    current = ledger_looks()
    for label, cell in _headline_cells().items():
        for live in set(_spellings(cell, current)):
            for match in re.finditer(re.escape(live), text):
                marked = _attributed_to(text, match.end())
                assert marked is None or marked == current, (
                    f"{document} attributes `{live}` to {marked} hypotheses, but "
                    f"that is {label}'s reading at today's {current:,}. A marker "
                    "on a current figure tells a reader it is history when it is "
                    "not."
                )


def test_every_attribution_in_the_documents_belongs_to_a_figure(document=None):
    """No marker may float free of a figure this roster knows.

    A `[@N]` that attributes nothing is worse than no marker: it reads as
    provenance and carries none.
    """
    current = ledger_looks()
    counts = set(_registration_counts()) | {current}
    for name in HAND_WRITTEN:
        text = _unwrapped((REPO / name).read_text(encoding="utf-8"))
        attached = set()
        for label, cell in _headline_cells().items():
            for looks in counts:
                for spelling in _spellings(cell, looks):
                    for match in re.finditer(re.escape(spelling), text):
                        if ATTRIBUTION.match(text, match.end()):
                            attached.add(ATTRIBUTION.match(text, match.end()).end())
        for match in re.finditer(r"\[@(\d+)\]", text):
            assert match.end() in attached, (
                f"{name} carries `{match.group(0)}` that does not follow any "
                "figure on the roster: "
                f"…{text[max(0, match.start() - 70):match.end() + 10]}…"
            )
            assert int(match.group(1)) in counts, (
                f"{name} attributes a figure to {match.group(1)} hypotheses, "
                f"which this ledger has never held. Its registration boundaries "
                f"are {sorted(counts)}."
            )


def test_the_hand_written_documents_quote_the_headline_cells_at_todays_count():
    """The other half: having found no stale number, the current one has to be
    there. A document that quotes a cell at all quotes it at the ledger's count.
    """
    current = ledger_looks()
    earlier = [count for count in _registration_counts() if count < current]
    cells = _headline_cells()
    quoted = 0
    for name in HAND_WRITTEN:
        # Flattened, because a figure hard-wrapped across two lines is still a
        # figure the file quotes -- see `_unwrapped`.
        text = _unwrapped((REPO / name).read_text(encoding="utf-8"))
        for label, cell in cells.items():
            live = _spellings(cell, current)
            mentioned = [
                spelling
                for looks in [*earlier, current]
                for spelling in _spellings(cell, looks)
                if spelling in text
            ]
            if not mentioned:
                continue
            quoted += 1
            assert any(spelling in text for spelling in live), (
                f"{name} quotes {label} only at a superseded correction "
                f"({mentioned[0]}). Whatever else the file says about the "
                f"history, it has to state the cell at the ledger's "
                f"{current:,} hypotheses too — that is the reading a person "
                "acts on."
            )
    assert quoted >= 8, (
        f"only {quoted} of the roster's cells were found in the hand-written "
        "documents, so this guard is watching less than it thinks it is"
    )


# ---------------------------------------------------------------------------
# 5. Restating at the count a run was scored under changes nothing
# ---------------------------------------------------------------------------

RENDERERS = [
    ("cbb_price_backtest.json", "price_backtest"),
    ("core_team_only/cbb_price_backtest.json", "price_backtest"),
    ("holdout/cbb_price_backtest.json", "price_backtest"),
    ("holdout/cbb_replication.json", "replication"),
    ("cbb_forecast_skill.json", "forecast_skill"),
    ("cbb_ratings_fit.json", "fit_ratings"),
]


def _renderer(module):
    if module == "fit_ratings":
        return _load_script("fit_ratings")
    return {"price_backtest": PB, "replication": REPL, "forecast_skill": FS}[module]


@pytest.mark.parametrize("record_name,module", RENDERERS)
def test_restating_at_the_run_s_own_count_is_the_old_render_exactly(
    record_name, module
):
    """The equivalence the whole change rests on.

    Restating is meant to move the correction and nothing else, so restating a
    record at the count it was already scored under must reproduce the report
    that was there before any of this existed — byte for byte, through the
    renderer, not just field by field. Run against every committed record, so a
    module whose restatement quietly drops a field, reorders a table or
    re-judges a state differently from `build_record` fails here rather than in
    a document nobody diffs.

    `replication` is the one that earns this test: its restatement does not
    re-derive bounds, it runs `judge_cell` again over the stored measurements.
    That is a second implementation of a judgement `build_record` already made,
    and two implementations of one judgement is exactly the shape that drifts.
    """
    renderer = _renderer(module)
    record = json.loads((OUTPUTS / record_name).read_text(encoding="utf-8"))
    unmoved = renderer.restated(
        record, looks=int(record["looks"]), record_name=Path(record_name).name
    )
    assert renderer.render(unmoved) == renderer.render(record), (
        f"restating {record_name} at the {int(record['looks'])} hypotheses it "
        "was already scored under changed its report. A restatement moves the "
        "correction and nothing else; this one moved something else."
    )
    assert RESTATEMENT.RESTATED_FROM not in unmoved, (
        "a record that did not move was stamped as restated"
    )


def test_the_status_row_counts_the_decision_log_rather_than_quoting_it():
    """Row 21 said 47 while the log held 48, one commit after decision 46 landed.

    A hand-maintained tally of a file that grows is stale by construction; this
    one drifted in the same commit that recorded the decision about numbers
    going stale. Counted here rather than re-typed, so the next decision fails
    the suite instead of quietly widening the gap.
    """
    rows = re.findall(
        r"^\| *(\d+) *\|", (DOCS / "decision_log.md").read_text(encoding="utf-8"), re.M
    )
    assert rows, "no numbered rows found in docs/decision_log.md"
    status = (DOCS / "project_status.md").read_text(encoding="utf-8")
    stated = re.search(r"\| \*\*done\*\* \| ([\d,]+) decisions", status)
    assert stated, (
        "docs/project_status.md row 21 no longer states a decision count in the "
        "shape this guard reads. Re-point the guard in the same commit."
    )
    assert int(stated.group(1).replace(",", "")) == len(rows), (
        f"docs/project_status.md states {stated.group(1)} decisions and "
        f"docs/decision_log.md holds {len(rows)} rows."
    )

    classes = re.findall(
        r"^\| *([A-Z]{1,2}) *\|", (DOCS / "ported_defects.md").read_text(encoding="utf-8"), re.M
    )
    stated_classes = re.search(r"\*\*(\d+) defect classes\*\*", status)
    assert stated_classes, "row 21 no longer states a defect-class count"
    assert int(stated_classes.group(1)) == len(classes), (
        f"docs/project_status.md states {stated_classes.group(1)} defect "
        f"classes and docs/ported_defects.md holds {len(classes)}."
    )


# --------------------------------------------------------------------------
# A committed record may not carry a market the code now refuses by name
#
# `test_the_committed_report_is_the_record_rendered_at_todays_count` proves
# report == render(record). Nothing proves record == what today's code would
# produce, and that second gap is not cheap to close in general: a record is a
# function of the code AND a 978 MB store, and re-deriving it costs an hour.
#
# This closes the sliver of it that costs nothing. `MARKETS_REFUSED_BY_NAME` is
# a filter applied on every verdict-producing path, so a market it names can
# never appear in a record today's code wrote. If one appears, the record
# predates the filter -- which is exactly what happened: the price backtest's
# record was generated 2026-09-05, the filter landed 2026-09-07 in #45, and the
# stale record kept publishing `player_first_basket` blind-rule rows carrying
# `demonstrated deficit` for two months.
# --------------------------------------------------------------------------


def _every_committed_record():
    for path in sorted(OUTPUTS.rglob("*.json")):
        if path.name == "experiment_ledger.json":
            continue
        try:
            yield path, json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:  # pragma: no cover - a corrupt record
            continue


#: The verdicts that are a claim about what a market is WORTH.
RESERVED_VERDICTS = frozenset(
    {S.DEMONSTRATED_EDGE, S.DEMONSTRATED_DEFICIT, S.NO_DEMONSTRATED_EDGE}
)

#: The sample-floor refusal. It belongs with the three above and not with
#: `RETAINED_BUT_THIN`: for a market refused BY NAME it says the market was
#: taken to the measurement and came back short of a floor, when the truth is
#: it was never priced -- the wrong reason, and the more flattering one, since
#: it implies a bigger store would produce a number.
NOT_ENOUGH_EVIDENCE = "not enough evidence"


def _betting_claims_about(payload, refused: set) -> list:
    """Rows that give a refused market a claim about its BETTING value.

    The line is not "names the market". Two committed records must name these
    markets and are right to: `cbb_prop_accounting.json` counts 721 wagers into
    a `refused_by_name` bucket, and `cbb_what_we_can_claim.json` says in words
    that they are never priced. A census that could not name what it refuses
    would not be a census.

    Nor is the line "carries a verdict". `cbb_retention_probe.json` calls
    `player_first_basket` RETAINED_BUT_THIN, and that is a fact about the
    ARCHIVE -- the store really does hold those quotes -- not a call on the
    bet. Suppressing it would hide something true about the data.

    The line is a claim about what the market is WORTH: an ROI, or a VERDICT
    of any kind. That is the thing this lab may not say about a market it
    refuses to price.

    **Including "not enough evidence (...)".** The predicate first listed only
    the three reserved phrases, which let a refused market carry
    `"not enough evidence (0 wagers, below the 200 declared in advance)"` into
    a committed record with the gate green. That sentence is not harmless
    here: it says the market WAS taken to the measurement and came back short
    of a sample floor, when the truth is that it was refused by name and never
    priced at all. Wrong reason, and the more flattering of the two -- it
    implies a bigger store would produce a number.

    But NOT any verdict at all. `cbb_retention_probe.json` calls
    `player_double_double` **RETAINED_BUT_THIN**, and that is a fact about the
    ARCHIVE -- the store really does hold those quotes -- not a call on the
    bet. Widening this to every non-empty verdict flagged it, which would
    force a census to hide something true and be worse than the defect. The
    line is a verdict about what the market is WORTH: the three reserved
    phrases, or the sample-floor refusal that implies it was measured.
    """
    def _is_a_betting_verdict(text: str) -> bool:
        word = str(text or "").strip()
        return word in RESERVED_VERDICTS or word.startswith(NOT_ENOUGH_EVIDENCE)

    found, stack = [], [payload]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            if node.get("market") in refused and (
                "roi" in node or _is_a_betting_verdict(node.get("verdict"))
            ):
                found.append(node)
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return found


def test_no_committed_record_prices_a_market_refused_by_name():
    """A priced refusal in a committed record is a record older than the filter.

    `player_first_basket` and `player_double_double` are refused because this
    lab has no defensible way to price them, so an ROI on one -- even a blind
    rule's -- is a number about a market it says it never prices.
    `without_markets_refused_by_name` is applied on every verdict-producing
    path, so today's code cannot produce these rows.

    They are here because the price backtest's record was generated
    2026-09-05 and the filter landed 2026-09-07 in #45. The report is a pure
    function of the record and that is gated; the RECORD is a function of the
    code and the store, and nothing gated that. This is the sliver of the
    second gap that costs nothing to check.
    """
    refused = set(PR.MARKETS_REFUSED_BY_NAME)
    assert refused, "the refusal list is empty, so this test proves nothing"
    offenders = {}
    for path, payload in _every_committed_record():
        rows = _betting_claims_about(payload, refused)
        if rows:
            offenders[path.relative_to(OUTPUTS).as_posix()] = len(rows)
    assert not offenders, (
        f"committed records put a price on a market this lab refuses: "
        f"{offenders}. Today's code cannot produce these rows — the records "
        "predate the filter and have to be RE-RUN, never hand-edited."
    )


def test_the_refusal_gate_catches_a_sample_floor_verdict_too():
    """The narrowest thing the gate must still catch, and the widest it must not.

    Both sides pinned here, because the predicate is wrong in two directions
    and only a pair of cases holds it in the middle:

    * a refused market carrying `"not enough evidence (0 wagers, below the 200
      declared in advance)"` MUST be caught. The gate first listed only the
      three reserved phrases and let this through — and for a market refused
      BY NAME that sentence is not a harmless refusal, it says the market was
      measured and came up short of a floor when it was never priced at all;
    * a refused market carrying `RETAINED_BUT_THIN` must NOT be caught. That is
      a fact about the archive, and a gate that forced a census to hide it
      would be worse than the defect.
    """
    refused = frozenset({"player_first_basket", "player_double_double"})

    floor = {
        "market": "player_first_basket",
        "tier": "high_major",
        "rows": 0,
        "verdict": "not enough evidence (0 wagers, below the 200 declared in advance)",
    }
    assert _betting_claims_about({"cells": [floor]}, refused), (
        "a market refused by name carried a sample-floor verdict into a record "
        "and the gate did not notice"
    )

    archive = {"market": "player_double_double", "verdict": "RETAINED_BUT_THIN"}
    assert not _betting_claims_about({"probe": [archive]}, refused), (
        "the gate flagged an archive-retention verdict, which is a true "
        "statement about the store and not a price"
    )

    # And a bare count stays legal, which is the census's whole job.
    census = {"market": "player_first_basket", "wagers": 721, "bucket": "refused_by_name"}
    assert not _betting_claims_about({"accounting": [census]}, refused)


def test_the_refusal_gate_still_lets_a_census_name_what_it_refuses():
    """The gate above must not be so broad that it forbids counting.

    A census that names a refused market, and a probe that says the archive
    retains it, are both correct and neither is a price. If this test ever goes
    red the gate has been widened into one that would force the accounting
    identity to hide a bucket it is required to publish.
    """
    refused = set(PR.MARKETS_REFUSED_BY_NAME)
    market = sorted(refused)[0]
    census = {"market": market, "bucket": "refused_by_name", "wagers": 721}
    archive = {"market": market, "verdict": "RETAINED_BUT_THIN"}
    priced = {"market": market, "bets": 292, "roi": -0.27, "verdict": S.DEMONSTRATED_DEFICIT}
    assert _betting_claims_about(census, refused) == []
    assert _betting_claims_about(archive, refused) == []
    assert _betting_claims_about(priced, refused) == [priced]
