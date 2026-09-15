"""Render the per-tier headline table into the hand-written documents.

**These two documents had no generator, and that is what every guard in
`tests/test_no_report_states_a_stale_correction.py` was built to compensate for.**
Four rounds of those guards were defeated in turn -- by a row count that looked
like a family size, by an ordinal, by a sentence terminator hidden behind a bold
marker, by a figure written in a spelling the guard did not enumerate. Each fix
made the inference cleverer; none of them made it right, because "which number
in this English sentence is a corrected interval, and which correction is it
stated at" is not a question a parser gets to answer.

A figure that is GENERATED cannot go stale, and needs no parsing at all. This
splices the table a reader actually acts on -- ROI and corrected interval per
tier, at the ledger's count as of this render -- between markers, exactly as
`run_why_the_model.py --splice-into` does for its own document.

The prose around it still argues, narrates and quotes superseded readings on
purpose; that is what these documents are for. Those figures carry an explicit
`[@N]`, and `test_every_interval_in_the_document_is_accounted_for` refuses any
interval it cannot account for, in any spelling. Between the two, nothing
stale is silent: the live numbers re-render, and the historical ones say so.

Usage:
    PYTHONPATH=src python scripts/splice_headline_table.py [--check]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cbb_betting_lab import stats as S  # noqa: E402

BEGIN_MARKER = "<!-- BEGIN GENERATED: headline_table -->"
END_MARKER = "<!-- END GENERATED -->"

DOCUMENTS = (REPO / "CLAUDE.md", REPO / "docs" / "project_status.md")
LEDGER = REPO / "data" / "outputs" / "experiment_ledger.json"
BACKTEST = REPO / "data" / "outputs" / "cbb_price_backtest.json"

TIERS = ("high_major", "mid_major", "low_major")

PROPS = REPO / "data" / "outputs" / "cbb_prop_grading.json"
SKILL = REPO / "data" / "outputs" / "cbb_forecast_skill.json"
REPLICATION = REPO / "data" / "outputs" / "holdout" / "cbb_replication.json"


def _at(payload, *path):
    node = payload
    for step in path:
        node = node[step]
    return node


def _tier_row(payload, key, tier):
    for row in payload[key]:
        if tier in (row.get("tier"), row.get("label")):
            return row
    raise SystemExit(f"no {tier!r} row in {key}")


def roster() -> dict[str, dict]:
    """Every cell these two documents publish, from the records.

    **Defined here rather than in the test that checks it.** The guard used to
    carry its own copy of this list, so the thing being generated and the thing
    being policed were two hand-maintained rosters that could disagree -- and
    for a while they did, at eleven cells against eighteen, which is how four
    published prop intervals went stale with every test green. One definition;
    the test imports it.
    """
    backtest = json.loads(BACKTEST.read_text(encoding="utf-8"))
    props = json.loads(PROPS.read_text(encoding="utf-8"))
    skill = json.loads(SKILL.read_text(encoding="utf-8"))
    replication = json.loads(REPLICATION.read_text(encoding="utf-8"))

    cells: dict[str, dict] = {}
    for tier in TIERS:
        cells[f"price backtest / {tier} ROI"] = _tier_row(backtest, "by_tier", tier)

        skill_row = _tier_row(skill, "by_tier", tier)
        cells[f"forecast skill / {tier} Brier vs raw"] = _at(
            skill_row, "brier", "advantage_over_raw"
        )
        coefficients = skill_row["fit"]["coefficients"]
        cells[f"forecast skill / {tier} disagreement"] = next(
            c for c in coefficients if c["name"] == "disagreement"
        )

        prop_row = _tier_row(props, "by_tier", tier)
        cells[f"prop grading / {tier} de-vig headline"] = _at(
            prop_row, "advantages", "devig_power__conditional"
        )
        cells[f"prop grading / {tier} role-prior control"] = _at(
            prop_row, "advantages", "control__conditional"
        )

    cells["forecast skill / selected-bets disagreement"] = next(
        c
        for c in skill["selected"]["by_tier"][0]["fit"]["coefficients"]
        if c["name"] == "disagreement"
    )
    pra = next(
        row
        for row in props["by_market_and_tier"]
        if (row.get("market"), row.get("tier")) == ("player_pra", "high_major")
    )
    cells["prop grading / player_pra high-major"] = _at(
        pra, "advantages", "devig_power__conditional"
    )
    market = next(
        row
        for row in replication["markets"]
        if (row.get("market"), row.get("tier")) == ("total_points", "mid_major")
    )
    cells["replication / total_points mid-major held out"] = market["holdout"]

    if len(cells) != 18:
        raise SystemExit(f"the roster resolved {len(cells)} cells, expected 18")
    return cells


def _interval(cell, looks):
    value = cell.get("roi", cell.get("value", cell.get("estimate")))
    return S.RoiInterval(
        roi=value,
        low=cell["low"],
        high=cell["high"],
        bets=cell.get("bets", cell.get("rows", 0)),
        clusters=cell.get("clusters", 0),
        standard_error=cell["standard_error"],
        looks=looks,
        cluster_unit=cell.get("cluster_unit", "game"),
    )


def render() -> str:
    """Every ledger-dependent figure these documents state, from the records.

    **The prose around this block states verdicts and states no numbers.** Sixty
    eight ledger-dependent figures were typed into it by hand -- twenty eight
    corrected intervals, twenty five correction factors, fifteen hypothesis
    counts -- and every one went stale the moment a hypothesis was registered.
    Seven rounds of adversarial review were spent building a guard that could
    find a stale one in English prose; each round found a spelling the last had
    missed, because "two numbers that together are an interval" has no closed
    form in a natural language. A generated figure does not need to be found.
    """
    looks = len(json.loads(LEDGER.read_text(encoding="utf-8"))["hypotheses"])
    factor = S.bonferroni_factor(looks)
    cells = roster()

    lines = [
        f"**Family correction: {looks} cumulative hypotheses, x{factor:.4f}.** "
        "Every interval below is widened by it. The count is the experiment "
        "ledger's cumulative total, not the day's.",
        "",
        "| Cut | Bets | ROI | Corrected | Verdict |",
        "|:---|---:|---:|:---|:---|",
    ]
    for tier in TIERS:
        interval = _interval(cells[f"price backtest / {tier} ROI"], looks)
        lines.append(
            f"| {tier.replace('_', '-')} | {interval.bets:,} | "
            f"{interval.roi:+.1%} | {interval.adjusted_low * 100:+.1f}% to "
            f"{interval.adjusted_high * 100:+.1f}% | {interval.verdict()} |"
        )

    lines += [
        "",
        "| Measure | Cut | Estimate | Corrected | Verdict |",
        "|:---|:---|---:|:---|:---|",
    ]
    for label in sorted(cells):
        if label.startswith("price backtest /"):
            continue
        measure, _, cut = label.partition(" / ")
        interval = _interval(cells[label], looks)
        lines.append(
            f"| {measure} | {cut} | {interval.roi:+.5f} | "
            f"{interval.adjusted_low:+.5f} to {interval.adjusted_high:+.5f} | "
            f"{interval.verdict()} |"
        )

    lines += [
        "",
        f"*Generated by `scripts/splice_headline_table.py` from the records in "
        f"`data/outputs/` at the ledger's {looks} hypotheses. Do not edit "
        "between the markers; re-run the script.*",
    ]
    return "\n".join(lines)


def fenced(text: str) -> str | None:
    start, stop = text.find(BEGIN_MARKER), text.find(END_MARKER)
    if start == -1 or stop == -1:
        return None
    return text[start + len(BEGIN_MARKER) : stop].strip("\n")


def splice(path: Path, body: str) -> bool:
    text = path.read_text(encoding="utf-8")
    start, stop = text.find(BEGIN_MARKER), text.find(END_MARKER)
    if start == -1 or stop == -1:
        raise SystemExit(
            f"{path.name} has no generated block. Add the markers around the "
            f"headline table:\n  {BEGIN_MARKER}\n  {END_MARKER}"
        )
    updated = (
        text[: start + len(BEGIN_MARKER)] + "\n\n" + body + "\n\n" + text[stop:]
    )
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if a document's block is not what render() produces",
    )
    arguments = parser.parse_args()

    body = render()
    stale = []
    for path in DOCUMENTS:
        if arguments.check:
            if fenced(path.read_text(encoding="utf-8")) != body:
                stale.append(path.name)
            continue
        print(f"{path.name}: {'rewritten' if splice(path, body) else 'unchanged'}")
    if stale:
        print(f"stale generated block in: {', '.join(stale)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
