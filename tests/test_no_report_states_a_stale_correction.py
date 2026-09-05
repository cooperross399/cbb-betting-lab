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
import sys
from pathlib import Path

import pytest

from cbb_betting_lab import restatement as RESTATEMENT
from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.experiment_ledger import load as load_ledger
from cbb_betting_lab.reports import forecast_skill as FS
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.reports import replication as REPL

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
    """
    script = _load_script("run_price_backtest")
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    record = json.loads(
        (OUTPUTS / "cbb_price_backtest.json").read_text(encoding="utf-8")
    )
    PB.write_record(record, PB.record_path(CBB, outputs))
    report = PB.report_path(CBB, outputs)

    small = tmp_path / "small.json"
    small.write_text(
        json.dumps({"hypotheses": [_hypothesis(i) for i in range(40)]}),
        encoding="utf-8",
    )
    big = tmp_path / "big.json"
    big.write_text(
        json.dumps({"hypotheses": [_hypothesis(i) for i in range(400)]}),
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

    assert "40 cumulative hypotheses" in at_forty
    assert "400 cumulative hypotheses" in at_four_hundred
    assert at_forty != at_four_hundred, (
        "the re-render produced the same report against two different ledgers, "
        "so it is replaying the correction stored in the record. That single "
        "line is what let three corrections be in force across this lab at once."
    )


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
)


def _generated_documents() -> list[Path]:
    return sorted(OUTPUTS.rglob("*.md")) + sorted(DOCS.rglob("*.md"))


def test_every_generated_document_states_the_ledgers_current_count():
    looks = ledger_looks()
    checked = 0
    for path in _generated_documents():
        text = path.read_text(encoding="utf-8")
        for match in CORRECTION_SENTENCES.finditer(text):
            stated = next(group for group in match.groups() if group)
            checked += 1
            assert int(stated.replace(",", "")) == looks, (
                f"{path.relative_to(REPO)} states its correction over "
                f"{stated} hypotheses and the experiment ledger holds "
                f"{looks:,}. Re-render it: a verdict stated at a narrower "
                "correction than the search that produced it is the defect "
                "decision 46 closed."
            )
    assert checked >= 8, (
        f"only {checked} correction sentences were found across the generated "
        "documents, so this guard is watching less than it thinks it is"
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
    ],
)
def test_the_committed_report_is_the_record_rendered_at_todays_count(
    record_name, report_name, module
):
    """The gate that fails the day a hypothesis is registered and nothing is
    re-rendered — which is the day the reports used to quietly go stale."""
    renderer = {"price_backtest": PB, "replication": REPL, "forecast_skill": FS}[
        module
    ]
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
    assert len(cells) == 11, sorted(cells)
    return cells


def _spellings(cell: dict, looks: int) -> tuple[str, ...]:
    """A cell's corrected interval in every spelling these two files use.

    Percentages to a tenth for a return, five decimals for a Brier advantage,
    three for a fitted coefficient. A document that grows a fourth spelling has
    to add it here before it can quote a stale number in it.
    """
    rebuilt = RESTATEMENT.rebuild_cell(cell, looks=looks)
    low, high = rebuilt["adjusted_low"], rebuilt["adjusted_high"]
    return (
        f"{low * 100:+.1f}% to {high * 100:+.1f}%",
        f"{low:.5f} to {high:.5f}",
        f"{low:+.3f} to {high:+.3f}",
    )


def _registration_counts() -> list[int]:
    """The cumulative count at every registration boundary this ledger records.

    A **superset** of the corrections that were ever really in force — the
    seven discovery searches all landed on one day and only their total, 30,
    was ever quoted — and deliberately so: checking a boundary nobody published
    at costs nothing, while missing one is how a stale number survives. Read
    from the ledger rather than listed, so the day a 96th hypothesis lands, 95
    joins the set of corrections a document may no longer state a verdict at
    without saying which.
    """
    payload = json.loads(LEDGER.read_text(encoding="utf-8"))
    counts: list[int] = []
    seen: set[tuple] = set()
    for index, entry in enumerate(payload["hypotheses"], start=1):
        key = (entry.get("search"), entry.get("tested_on"))
        if key in seen:
            continue
        seen.add(key)
        if index > 1:
            counts.append(index - 1)
    counts.append(len(payload["hypotheses"]))
    return counts


#: Where one statement ends and the next begins: a sentence's own punctuation,
#: a line break, or a markdown cell wall. Sentence-level rather than
#: paragraph-level on purpose — row 12 of `docs/project_status.md` is a single
#: paragraph the size of a page, and "somewhere in this paragraph a correction
#: is named" would have licensed every stale number in it. A decimal point is
#: not a boundary, because the split needs whitespace after the punctuation.
SENTENCE = re.compile(r"(?<=[.;:!?])\s+|\n|\|")


def _sentences(text: str) -> list[str]:
    return [part for part in SENTENCE.split(text) if part.strip()]


def _names_the_correction(sentence: str, looks: int) -> bool:
    """Whether a sentence says, in its own words, which correction it carries.

    Either the cumulative count or the factor computed from it — the two ways
    this repository writes it. `x1.60` is accepted alongside `x1.6041` because
    the two-decimal form is what the records' own prose uses.
    """
    factor = S.bonferroni_factor(looks)
    tokens = (
        rf"\b{looks}\b",
        rf"[x×]{factor:.4f}".replace(".", r"\."),
        rf"[x×]{factor:.2f}".replace(".", r"\."),
    )
    return any(re.search(token, sentence) for token in tokens)


def test_no_hand_written_document_states_a_headline_verdict_at_a_stale_correction():
    """Row 12's defect, made mechanical.

    For every cell these two files quote, the reading at each **earlier**
    correction this ledger has been through is looked for in the text. Finding
    one is not automatically wrong — this repository narrates the move, and a
    superseded bound quoted beside the factor it was computed at is exactly the
    provenance decision 46 asks for. Finding one in a **sentence** that does
    not say which correction it carries is the defect: a reader meets a verdict
    and has no way to tell it is stated at a narrower family than the lab owes.
    Sentence-level, because row 12 is one paragraph the size of a page and a
    correction named at the far end of it is attached to nothing.
    """
    current = ledger_looks()
    earlier = [count for count in _registration_counts() if count < current]
    assert earlier, "this ledger has only ever had one correction to be stale at"
    cells = _headline_cells()
    checked = 0
    for name in HAND_WRITTEN:
        text = (REPO / name).read_text(encoding="utf-8")
        for label, cell in cells.items():
            live = set(_spellings(cell, current))
            for looks in earlier:
                for stale in _spellings(cell, looks):
                    if stale in live:
                        continue
                    for sentence in _sentences(text):
                        if stale not in sentence:
                            continue
                        checked += 1
                        assert _names_the_correction(sentence, looks), (
                            f"{name} quotes {label} as `{stale}` — the reading "
                            f"at {looks:,} cumulative hypotheses — in a "
                            f"sentence that never says so, while the ledger "
                            f"holds {current:,}. Re-derive it to "
                            f"`{sorted(live)[0]}`, or name the narrower "
                            "correction in the same sentence as the number it "
                            "belongs to. A correction named a paragraph away "
                            "is not attached to anything."
                        )
    assert checked, (
        "no superseded reading was found in either hand-written document, so "
        "this guard checked nothing. That is possible — but check that the "
        "roster still resolves before believing it."
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
        text = (REPO / name).read_text(encoding="utf-8")
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
