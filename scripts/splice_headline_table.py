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
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cbb_betting_lab import stats as S  # noqa: E402

BEGIN_MARKER = "<!-- BEGIN GENERATED: headline_table -->"
CENSUS_MARKER = "<!-- BEGIN GENERATED: record_census -->"
HISTORY_MARKER = "<!-- BEGIN GENERATED: retraction_history -->"
END_MARKER = "<!-- END GENERATED -->"

#: Every fence these two documents carry, in the order a reader meets them.
#:
#: **The second one exists because the first one's rule was not applied widely
#: enough.** `headline_table` fenced the corrected intervals and the family
#: size, and four rounds of review then found the SAME failure in the figures
#: beside it: on 2026-09-17 both documents still said in the present tense that
#: the forecast-skill record on disk was scored at 30 hypotheses (x1.6041)
#: while the regenerated record stored 133 (x1.8145), that the price backtest
#: covered 920,712 wagers and 191,053 graded bets against a record reading
#: 663,961 and 175,690, and that the replication held out 71,778 bets over
#: 9,776 games against a record reading 71,797 and 9,810. None of those is
#: interval-shaped, so every guard built for the first fence ran green.
#:
#: A count is exactly as generatable as an interval. It is generated here.
#:
#: **The third one exists because a MECHANISM is as generatable as a count.**
#: `docs/retracted_readings.md` is the ledger of what a registration withdrew,
#: and its factual content was hand-written prose asserting WHY each reading
#: left the table -- that one "came back", that another "sharpened", that a
#: third "no longer carries a scored reading at all". Three successive
#: adversarial rounds each found one of those false, every time in the
#: flattering direction, in the one document whose whole purpose is honesty
#: about what was withdrawn. A claim about why a reading departed is a diff of
#: two records across a commit; it is not something a person can hold in their
#: head, and this repository has now measured three times that a person writing
#: it by hand gets it wrong in their own favour.
#:
#: So it is diffed. `render_retraction_history()` reads every reading this
#: file's table has ever named -- from the file's own git history, so the
#: roster is not a roster -- and prints what each one actually did: estimate,
#: standard error, population, verdict and |estimate|/standard-error, at the
#: state before the restatement, at the state after it, and on disk today. A
#: reader sees whether a reading sharpened or blunted without being told.
MARKERS = (BEGIN_MARKER, CENSUS_MARKER, HISTORY_MARKER)

DOCUMENTS = (REPO / "CLAUDE.md", REPO / "docs" / "project_status.md")
RETRACTIONS = REPO / "docs" / "retracted_readings.md"

#: Which fence each function renders, and which documents carry it.
#:
#: **A fence belongs to the documents that carry it, not to every document.**
#: `main()` looped over `DOCUMENTS x FENCES` and would therefore demand a
#: retraction-history block in `CLAUDE.md`; the two headline fences equally do
#: not belong in the retraction ledger. One mapping, read by the splicer and by
#: the test that pins each committed block to a fresh render.
def fences() -> tuple[tuple[str, object, tuple[Path, ...]], ...]:
    return (
        ("headline_table", BEGIN_MARKER, render, DOCUMENTS),
        ("record_census", CENSUS_MARKER, render_census, DOCUMENTS),
        ("retraction_history", HISTORY_MARKER, render_retraction_history, (RETRACTIONS,)),
    )
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


#: Records whose block headings the populations section needs by name.
#:
#: **This is a FLOOR, not the roster.** The roster is derived below from the
#: records on disk; these four are the cuts the populations table has a row
#: for, so their absence is a broken render rather than a shorter table, and it
#: must say so loudly instead of silently dropping a row.
REQUIRED_CUTS = (
    "cbb_price_backtest.json",
    "core_team_only/cbb_price_backtest.json",
    "holdout/cbb_price_backtest.json",
    "holdout/cbb_replication.json",
)


def census_records() -> tuple[str, ...]:
    """Every record on disk that stores a family correction, read from disk.

    **THIS WAS A HAND-LIST OF SEVEN PATHS AND IT WAS ALREADY WRONG.** The
    census fence was added precisely to stop figures being maintained by hand,
    and it was driven by a tuple nothing checked: eight records under
    `data/outputs/` carry both `looks` and `correction_factor`, the tuple named
    seven, and `cbb_reachability.json` — a published record, with its own
    rendered markdown on the roster of documents that state a correction — was
    the one missing. A block headed "What each record on disk was scored under"
    showed seven of eight, and a record could be deleted from the tuple with
    the whole suite green.

    This repository has the lesson written down: a roster only guards what it
    names. So the roster is not written. A record is in the census if and only
    if it stores the two fields the census is about, which is the same
    condition a reader would apply by hand.
    """
    outputs = REPO / "data" / "outputs"
    found = []
    for path in sorted(outputs.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and "looks" in payload and "correction_factor" in payload:
            found.append(path.relative_to(outputs).as_posix())
    missing = [name for name in REQUIRED_CUTS if name not in found]
    if missing:
        raise SystemExit(
            "the record census cannot render: these cuts have a row in the "
            f"populations table and are not on disk with a stored correction: {missing}"
        )
    return tuple(found)


def render_census() -> str:
    """What each record was scored under, the populations, and the tally.

    **This is the second fence, and it exists for the same reason as the
    first.** The prose around it used to state all of this by hand -- which
    correction each record on disk carries, how many wagers and graded bets and
    games each cut covers, how the thirty-two market-and-tier cells fall across
    the verdicts. Every one of those is a figure a regeneration moves, none of
    them is interval-shaped, and on 2026-09-17 a regeneration moved eleven of
    them in one commit with the whole suite green.

    Nothing here is typed. The verdict vocabulary is `stats`' own, so this
    cannot drift from the rule that produced it either.
    """
    import collections

    outputs = REPO / "data" / "outputs"
    # THE LEDGER'S COMPOSITION, COUNTED RATHER THAN SUMMED BY HAND.
    #
    # `CLAUDE.md` used to state this as an exhaustive "A, B, C, D and E" list
    # that summed to barely three quarters of the ledger -- it omitted the
    # residual-regression entries and the weekly-search ones, and it undercounted
    # the replication's appended looks. Understating the registered
    # family understates every correction derived from it, which is the
    # flattering direction, and no guard could see it because a hand-written
    # sum is not interval-shaped and each of its parts is a number some record
    # does hold.
    _ledger = json.loads(
        (outputs / "experiment_ledger.json").read_text(encoding="utf-8")
    )["hypotheses"]
    _by_search = collections.Counter(str(h.get("search")) for h in _ledger)
    scored = {
        relative: json.loads((outputs / relative).read_text(encoding="utf-8"))
        for relative in census_records()
    }

    lines = [
        "**What each record on disk was scored under.** A record keeps the "
        "family correction that was in force when it ran -- that is the "
        "evidence of what was measured -- and every generated report "
        "re-derives its verdicts at the ledger's cumulative count when it "
        "renders (decision 46). Where a row below is narrower than the "
        "ledger's own count, the gap is the search registered since.",
        "",
        "| Record | Scored at | Factor |",
        "|:---|---:|---:|",
    ]
    for relative, payload in scored.items():
        lines.append(
            f"| `{relative}` | {payload['looks']} | "
            f"x{payload['correction_factor']:.4f} |"
        )

    backtest = scored["cbb_price_backtest.json"]
    core = scored["core_team_only/cbb_price_backtest.json"]
    discovery = scored["holdout/cbb_price_backtest.json"]
    replication = scored["holdout/cbb_replication.json"]
    held = replication["holdout"]

    lines += [
        "",
        "**The populations those verdicts are measured on.**",
        "",
        "| Cut | Wagers offered | Graded bets | Games |",
        "|:---|---:|---:|---:|",
        f"| full store, all six seasons | {backtest['wagers_offered']:,} | "
        f"{backtest['bets_graded']:,} | {backtest['games']:,} |",
        f"| core team markets only | {core['wagers_offered']:,} | "
        f"{core['bets_graded']:,} | {core['games']:,} |",
        f"| discovery seasons | {discovery['wagers_offered']:,} | "
        f"{discovery['bets_graded']:,} | {discovery['games']:,} |",
        f"| genuinely held-out seasons | — | {held['bets_graded']:,} "
        f"({held['bets_taken']:,} taken) | {held['games']:,} |",
    ]

    floor = backtest.get("minimum_bets", S.MINIMUM_BETS)
    thin = f"below the {floor:,}-bet floor"
    tally: collections.Counter = collections.Counter()
    for cell in backtest["by_market_and_tier"]:
        verdict = cell["verdict"]
        tally[thin if verdict.startswith("not enough evidence") else verdict] += 1
    order = (S.DEMONSTRATED_EDGE, S.DEMONSTRATED_DEFICIT, S.NO_DEMONSTRATED_EDGE, thin)
    unexpected = sorted(set(tally) - set(order))
    if unexpected:
        raise SystemExit(f"the backtest reads verdicts this block cannot name: {unexpected}")
    spelled = ", ".join(f"{tally.get(name, 0)} {name}" for name in order)
    lines += [
        "",
        f"**The full-store price backtest, cut by market and tier:** "
        f"{len(backtest['by_market_and_tier'])} cells — {spelled}.",
    ]

    lines += _blind_baseline(backtest)
    lines += _distance_to_zero(backtest)

    lines += [
        "",
        f"**What the family of {sum(_by_search.values()):,} is made of.** Counted "
        "from `experiment_ledger.json` at render time, every entry in exactly "
        "one row, so the parts sum to the whole by construction. A composition "
        "stated by hand cannot: the one this replaced summed to 101.",
        "",
        "| Registered under | Entries |",
        "|:---|---:|",
    ]
    for _search, _count in sorted(_by_search.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| `{_search}` | {_count:,} |")
    lines.append(f"| **total** | **{sum(_by_search.values()):,}** |")

    lines += [
        "",
        "*Generated by `scripts/splice_headline_table.py` from the records in "
        "`data/outputs/`. Do not edit between the markers; re-run the script.*",
    ]
    return "\n".join(lines)


def _blind_baseline(backtest: dict) -> list[str]:
    """The blind null baseline, counted rather than described.

    **Every figure here was typed into the prose of both documents, and the
    denominator was wrong by 84% in one of them.** One paragraph of `CLAUDE.md`
    said "the 102 blind sides clearing the 200-bet floor" in one sentence and
    "0 of 188" sixteen lines later, for the same population, and 188 is a
    number no record in this repository holds. It survived four rounds of
    review and two rounds of counting guards because it carries no comma, and
    the comma is what the count guard reads.

    The answer to a figure a guard cannot see is not a wider guard. It is to
    stop typing the figure. Everything below is counted from `null_baseline`
    at render time, so the denominator cannot disagree with itself and cannot
    disagree with the record.
    """
    import collections

    rows = backtest["null_baseline"]
    floor = backtest.get("minimum_bets", S.MINIMUM_BETS)
    clearing = [row for row in rows if row["bets"] >= floor]
    tally = collections.Counter(row["verdict"] for row in clearing)
    by_tier = {row["tier"]: row["roi"] for row in backtest["by_tier"]}
    beat = [row for row in clearing if row["roi"] > by_tier.get(row["tier"], float("inf"))]
    deficits = sum(1 for row in beat if row["verdict"] == S.DEMONSTRATED_DEFICIT)
    markets = sorted({row["market"] for row in rows})
    order = (S.DEMONSTRATED_EDGE, S.DEMONSTRATED_DEFICIT, S.NO_DEMONSTRATED_EDGE)
    unexpected = sorted(set(tally) - set(order))
    if unexpected:
        raise SystemExit(f"the blind baseline reads verdicts this block cannot name: {unexpected}")
    return [
        "",
        "**The blind null baseline — betting one side of one market blindly, "
        f"every time.** {len(rows)} sides, of which {len(clearing)} clear the "
        f"{floor}-bet floor; the rest carry no verdict at all. Across the "
        f"{len(clearing)}: "
        + ", ".join(f"{tally.get(name, 0)} {name}" for name in order)
        + f". {len(beat)} of them return more than their own tier's model, and "
        f"{deficits} of those {len(beat)} are themselves a demonstrated "
        "deficit — beating the model and still losing money is the ordinary "
        f"case here. The baseline covers the {len(markets)} game markets "
        f"({', '.join('`' + name + '`' for name in markets)}) and no prop "
        "market at all.",
    ]


def _distance_to_zero(backtest: dict) -> list[str]:
    """How much more searching each tier's deficit would survive.

    **Both hand-written documents said mid-major "would need 411 hypotheses to
    widen it across".** The record says 35,427, it said 35,427 at HEAD as well,
    and 411 matches no cut of the backtest. It is a derived figure — a search
    over the family size for the first one at which the corrected bound reaches
    zero — so nobody could check it by looking a number up, which is why it sat
    there being quoted as the margin of safety on a demonstrated deficit.

    Per tier and never pooled: a pooled all-of-Division-I headline is banned in
    this repository.
    """
    ceiling = 10_000_000
    lines = [
        "",
        "**How far the search would have to go before each tier's corrected "
        "interval reached zero.** The family correction widens with every "
        "hypothesis registered, so a demonstrated deficit survives only until "
        "the search is large enough to dissolve it. This is that size, "
        "searched at render time from the tier's own return and standard "
        "error. Per tier; there is no pooled row here on purpose.",
        "",
        "| Cut | Verdict today | Hypotheses before the interval reaches zero |",
        "|:---|:---|---:|",
    ]
    for tier in TIERS:
        row = _tier_row(backtest, "by_tier", tier)
        roi, se = row["roi"], row["standard_error"]
        if roi >= 0 or roi + S.bonferroni_z(ceiling) * se < 0:
            reached = None
        else:
            low, high = 1, ceiling
            while low < high:
                mid = (low + high) // 2
                if roi + S.bonferroni_z(mid) * se >= 0:
                    high = mid
                else:
                    low = mid + 1
            reached = low
        if row["verdict"] != S.DEMONSTRATED_DEFICIT:
            answer = "— (not a demonstrated deficit today)"
        elif reached is None:
            answer = f"more than {ceiling:,}"
        else:
            answer = f"{reached:,}"
        lines.append(f"| {tier.replace('_', '-')} | {row['verdict']} | {answer} |")
    return lines


# ---------------------------------------------------------------------------
# The retraction ledger's mechanisms, diffed rather than described
# ---------------------------------------------------------------------------

#: The columns of the retraction table, in the order its header writes them.
#:
#: Read from the HEADER of whichever version of the file is being parsed rather
#: than by position, because the table has not always had the same columns: the
#: `band` column was added on 2026-09-17 and every row written before that has
#: eleven fields, not twelve. A positional parser reads those as a different
#: reading, silently, and the roster this builds would then be missing exactly
#: the rows that are oldest -- the ones nobody remembers.
KEY_COLUMNS = (
    "record", "block", "leaf", "season", "tier", "label", "market", "band", "rule",
)

DASH = "—"

#: The retraction ledger, as git addresses it.
RETRACTIONS_RELATIVE = "docs/retracted_readings.md"


def _git(*arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPO), *arguments],
        capture_output=True,
        text=True,
    )
    if completed.returncode:
        raise SystemExit(
            "the retraction history cannot be rendered because git refused "
            f"`git {' '.join(arguments)}`:\n{completed.stderr.strip()}"
        )
    return completed.stdout


def _text_at(rev: str, relative: str) -> str | None:
    """A tracked file's bytes at a revision, or None if it did not exist."""
    completed = subprocess.run(
        ["git", "-C", str(REPO), "show", f"{rev}:{relative}"],
        capture_output=True,
        text=True,
    )
    return None if completed.returncode else completed.stdout


def _walker():
    """The one definition of "a published reading", imported not copied.

    `tests/test_the_forward_window_is_pre_registered.py` already answers "what
    is a scored reading in a record, and what is its key" -- it is the function
    the cost check walks with, and the retraction table is keyed by its output.
    A second walker here would be a second answer to that question, and the two
    would disagree the first time one of them learned about a new field. This
    repository has that failure written down twice over: `_cells` was blind to
    `estimate` for 33 coefficients and to `mean` for a whole record, and both
    times the thing that hid it was a checker agreeing with a copy of itself.

    The import is lazy so that `render()` and `render_census()` -- which need
    none of this -- do not pay for pandas and pytest.
    """
    global _WALKER
    try:
        return _WALKER
    except NameError:
        pass
    spec = importlib.util.spec_from_file_location(
        "_retraction_walker",
        REPO / "tests" / "test_the_forward_window_is_pre_registered.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _WALKER = module
    return module


def _table_keys(text: str) -> list[tuple]:
    """Every row of the retraction table in one version of the document."""
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("| record | block |"):
            continue
        columns = [cell.strip() for cell in line.strip().strip("|").split("|")]
        keys = []
        for candidate in lines[index + 2 :]:
            if not candidate.startswith("|"):
                break
            fields = [
                field.strip().strip("`")
                for field in candidate.strip().strip("|").split("|")
            ]
            if len(fields) != len(columns):
                continue
            cell = dict(zip(columns, fields))
            keys.append(
                tuple(
                    "" if cell.get(name, DASH) in (DASH, "") else cell[name]
                    for name in KEY_COLUMNS
                )
            )
        return keys
    return []


def readings_this_table_has_named() -> list[tuple]:
    """Every reading this file's table has ever carried, from its own history.

    **This is the roster, and it is not written down anywhere.** The mandate
    that produced this block says "for every reading the file discusses", and
    the honest way to answer that is not a list somebody types -- this
    repository's own lesson is that a roster only guards what it names, and the
    rows that go missing from a hand-typed one are the oldest, which is to say
    the ones nobody would notice. The file's git history IS the list: a reading
    this table ever named is a reading this file discusses, and a reading it
    never named is not.

    Today that resolves to the sixteen rows the narration describes. When a row
    is added the block grows with it; when one is removed the block keeps it,
    which is the point of a retraction ledger.
    """
    named: dict[tuple, None] = {}
    for rev in _git("log", "--format=%H", "--", RETRACTIONS_RELATIVE).split():
        text = _text_at(rev, RETRACTIONS_RELATIVE)
        if text is None:
            continue
        for key in _table_keys(text):
            named.setdefault(key, None)
    for key in _table_keys(RETRACTIONS.read_text(encoding="utf-8")):
        named.setdefault(key, None)
    return sorted(named)


def _cells_by_key(relative: str, payload: dict) -> dict[tuple, dict]:
    walker = _walker()
    return {
        walker._key(relative, cell): cell
        for cell in walker._cells(payload, payload.get("looks"))
    }


def record_states(relative: str) -> list[tuple[str, str, dict]]:
    """(label, what changed it, readings) for a record, oldest first.

    Every committed state of the record, read with `git show`, and the working
    tree last when it differs from the newest commit. The working tree is the
    state a reader is looking at, so a block that stopped at HEAD would narrate
    a record nobody has.
    """
    path = f"data/outputs/{relative}"
    states: list[tuple[str, str, dict]] = []
    newest: str | None = None
    for rev in reversed(_git("log", "--format=%H", "--", path).split()):
        text = _text_at(rev, path)
        if text is None:
            continue
        newest = text
        subject = _git("log", "-1", "--format=%s", rev).strip()
        states.append((rev[:7], subject, _cells_by_key(relative, json.loads(text))))
    # THE TERMINAL STATE IS ALWAYS "ON DISK", NEVER A REVISION.
    #
    # It was appended only when the working tree was dirty, so the block a
    # generator produced depended on git state and not only on the records:
    # rendered dirty it ended `| today | on disk |`, and the moment that render
    # was COMMITTED the same records became the newest revision, the on-disk row
    # stopped being appended, and a fresh render ended `| today | <sha> |`. The
    # block invalidated itself by being committed, and a commit that changes both
    # the records and the block could never be green -- caught by CI on #89 after
    # a local suite that ran before the commit existed and passed.
    #
    # Replacing rather than appending keeps the sequence the same length across
    # that transition: dirty gives N committed states plus one, and once
    # committed it gives N+1 states whose last is relabelled, which is the same
    # rows carrying the same data. Committing the block is now a no-op for it.
    on_disk = (REPO / path).read_text(encoding="utf-8")
    terminal = ("on disk", "the records as they stand",
                _cells_by_key(relative, json.loads(on_disk)))
    if newest is not None and on_disk == newest:
        states[-1] = terminal
    else:
        states.append(terminal)
    if not states:
        raise SystemExit(f"{path} has no committed state and is not on disk")
    return states


def _retracted(cell: dict, looks: int) -> bool:
    """The cost check's own rule, at a FIXED family size.

    `_readings_across_every_record` asks this at the ledger's count today, and
    so does this: holding the family constant is what isolates the record's own
    movement from the search's. A reading that stops being retracted while the
    family is held still stopped for a reason inside the record, which is the
    whole subject of this block.
    """
    if cell is None:
        return False
    return (
        abs(cell["value"]) > S.bonferroni_z(cell["scored"]) * cell["standard_error"]
        and abs(cell["value"]) <= S.bonferroni_z(looks) * cell["standard_error"]
    )


def _reading_label(key: tuple) -> str:
    record, rest = key[0], [part for part in key[1:] if part]
    return f"`{record}` / " + " / ".join(rest) if rest else f"`{record}`"


def _crossed_at(cell: dict) -> str:
    """The family size at which this reading stops excluding zero.

    **The column the prose used to type.** "The core-team sides crossed at 38,
    49, 62 and 76 hypotheses" is four derived figures — a search over the
    family size for the first one whose corrected bound reaches zero — and
    nobody can check a derived figure by looking a number up, which is how one
    of them sat in this file being quoted as a margin of safety. It is the same
    search `_crossing_point` runs in the cost check, imported rather than
    re-implemented.
    """
    walker = _walker()
    try:
        return str(walker._crossing_point(S, cell))
    except AssertionError:
        return "beyond a thousand"


def _row(stage: str, label: str, reading: str, cell: dict | None, looks: int) -> str:
    if cell is None:
        return (
            f"| {stage} | {label} | {reading} | — | — | — | — | — | — | "
            "not in the record | no |"
        )
    ratio = abs(cell["value"]) / cell["standard_error"]
    bets = cell.get("bets")
    population = "—" if bets is None else f"{bets:,}"
    verdict = cell.get("verdict") or "—"
    return (
        f"| {stage} | {label} | {reading} | {cell['value']:+.5f} | "
        f"{cell['standard_error']:.5f} | {population} | {ratio:.2f} | "
        f"{cell['scored']} | {_crossed_at(cell)} | {verdict} | "
        f"{'yes' if _retracted(cell, looks) else 'no'} |"
    )


def _what_the_family_removed(moved: list[str], family: list[tuple]) -> list[str]:
    """Of the verdicts that moved, how many needed the search to grow.

    Generated because the hand-written answer was wrong: for two days this
    document said growth of the family had removed none of these readings, and
    reasoned it from the block above -- which holds the correction FIXED, and
    is therefore the one table that cannot speak to it. Reasoning from a design
    decision to the conclusion that decision excludes is how a false claim
    survives review; the arithmetic is two corrections and a comparison.

    The counterfactual is stated per reading rather than summarised, because
    "three of eight" is exactly the kind of figure that goes stale silently.
    """
    if not moved:
        return ["", "*No reading below changed its verdict between states.*"]
    lines = [
        "",
        f"**Of the {len(moved)} reading(s) whose verdict moved, "
        f"{len(family)} moved because the family grew.** Each row takes the "
        "AFTER measurement and corrects it at the count the reading was scored "
        "under BEFORE: still a deficit there means the measurement did not "
        "remove it and the search did. This block holds the family fixed "
        "everywhere else, so this is the only place it can be read.",
    ]
    if not family:
        lines.append("")
        lines.append("*None of them did.*")
        return lines
    lines += [
        "",
        "| reading | after-measurement | at the family it was scored under before | at the family it was scored under after |",
        "|:---|---:|---:|---:|",
    ]
    for reading, cell, before, after, hi_old, hi_new in family:
        lines.append(
            f"| {reading} | {cell['value']:+.5f} ± {cell['standard_error']:.5f} | "
            f"{before}: high **{hi_old:+.5f}** | {after}: high **{hi_new:+.5f}** |"
        )
    return lines

def render_retraction_history() -> str:
    """What each reading this table has named actually did, diffed.

    **The sentences this replaces were wrong three rounds running, and always
    in the direction that flattered.** "That cell no longer carries a scored
    reading at all -- its sample fell below the bar": the walker finds it, at
    -0.065378. "A team reading that came back ... the reading sharpened": the
    cell is byte-identical at both commits and its |estimate|/error FELL from
    3.54 to 2.62. "Five were team readings that came back ... sharpened out of
    being dissolved": none came back and four of the five blunted.

    None of those is a hard fact to establish -- each is two `git show`s and a
    division. They were wrong because they were typed, and a claim about a
    mechanism is exactly as generatable as a claim about a count. It is
    generated here, and the prose around it no longer asserts a direction.
    """
    looks = len(json.loads(LEDGER.read_text(encoding="utf-8"))["hypotheses"])
    _verdicts_moved: list[str] = []
    _family_did_it: list[tuple] = []
    keys = readings_this_table_has_named()
    states: dict[str, list[tuple[str, str, dict]]] = {}

    lines = [
        "**What each reading this table has ever named actually did.** Every "
        "row below is read from the records with `git show`, at the ledger's "
        f"{looks} cumulative hypotheses held FIXED across every state, so what "
        "moves here is the measurement and never the family. **That is why this "
        "block cannot be read as evidence about what the family did** — it is "
        "built to exclude exactly that, and the `Scored at` column is the only "
        "place the family appears. Three of the readings below moved because "
        "the count they were scored at grew; the prose beneath names them and "
        "shows the arithmetic. The roster is the "
        "table's own history: a reading this file has ever listed as retracted "
        "is a reading this block accounts for. `|est|/se` is the estimate over "
        "its own standard error — a reading that SHARPENED across a "
        "restatement has a larger one after than before, and one that BLUNTED "
        "has a smaller one. Nothing in the prose of this file states a "
        "direction; this is where a direction may be read.",
        "",
        "| Stage | State | Reading | Estimate | Standard error | Bets | "
        "\\|est\\|/se | Scored at | Crossed at | Verdict | "
        "Retracted at today's count |",
        "|:---|:---|:---|---:|---:|---:|---:|---:|---:|:---|:---|",
    ]

    unresolved = []
    for key in keys:
        relative = key[0]
        if relative not in states:
            states[relative] = record_states(relative)
        sequence = states[relative]
        reading = _reading_label(key)

        moved = None
        for index in range(len(sequence) - 1):
            before, after = sequence[index], sequence[index + 1]
            if _retracted(before[2].get(key), looks) and not _retracted(
                after[2].get(key), looks
            ):
                moved = index
        if moved is None:
            unresolved.append(key)
            label, _, cells = sequence[-1]
            lines.append(_row("today", label, reading, cells.get(key), looks))
            continue

        before_label, _, before_cells = sequence[moved]
        after_label, after_subject, after_cells = sequence[moved + 1]
        today_label, _, today_cells = sequence[-1]
        lines.append(_row("before", before_label, reading, before_cells.get(key), looks))
        lines.append(
            _row(
                "after",
                f"{after_label} — {after_subject}",
                reading,
                after_cells.get(key),
                looks,
            )
        )
        if moved + 1 != len(sequence) - 1:
            lines.append(_row("today", today_label, reading, today_cells.get(key), looks))

        # DID THE FAMILY DO IT? Answered here, where both states are in hand.
        #
        # The block above holds the correction fixed, which is what lets a
        # reader see the MEASUREMENT move -- and is exactly why the block
        # cannot answer this question. The prose under it asserted for two days
        # that the family had removed none of these, reasoning from a table
        # built to exclude the family. The honest test is the counterfactual:
        # take the AFTER measurement and correct it at the family the reading
        # was scored under BEFORE. If it is still a deficit there, nothing
        # about the measurement removed it and the search did.
        _b, _a = before_cells.get(key), after_cells.get(key)
        if _b and _a and (_b.get("verdict") != _a.get("verdict")):
            _verdicts_moved.append(reading)
            _hi_old = _a["value"] + S.bonferroni_z(max(int(_b["scored"]), 1)) * _a["standard_error"]
            _hi_new = _a["value"] + S.bonferroni_z(max(int(_a["scored"]), 1)) * _a["standard_error"]
            if int(_b["scored"]) != int(_a["scored"]) and _hi_old < 0 <= _hi_new:
                _family_did_it.append(
                    (reading, _a, int(_b["scored"]), int(_a["scored"]), _hi_old, _hi_new)
                )

    lines += _what_the_family_removed(_verdicts_moved, _family_did_it)
    lines += [
        "",
        f"*{len(keys)} reading(s) this table has named; "
        f"{len(keys) - len(unresolved)} of them stopped being retracted at a "
        f"state this block can name, {len(unresolved)} did not.*",
    ]
    lines += _deficits_each_record_holds()
    lines += [
        "",
        "*Generated by `scripts/splice_headline_table.py` from the records in "
        "`data/outputs/` and from each revision that changed them. Do not edit "
        "between the markers; re-run the script.*",
    ]
    return "\n".join(lines)


def _deficits_each_record_holds() -> list[str]:
    """How many demonstrated deficits each walked record holds, counted.

    **This replaces a sentence that was false and flattering for two days.**
    The prose said *"the record in `data/outputs/holdout/` still shows ZERO
    demonstrated deficits over 110,839 bets, before and after"*, in the present
    tense, with no scope. That record holds demonstrated deficits today — one
    of them arrived in the very commit this file narrates thirty-eight lines
    further down — and the population it quoted is one no record on disk
    states. The fifth round's response was to attach a witness marker to the
    figure rather than correct the sentence, which silences a guard rather than
    a falsity.

    A tally of verdicts is exactly as generatable as a population. The roster
    is the walker's own, so a record added to the cost check appears here
    without anybody remembering to add it.
    """
    import collections

    walker = _walker()
    outputs = REPO / "data" / "outputs"

    def _verdicts(node, block=None):
        if isinstance(node, dict):
            if node.get("verdict") == S.DEMONSTRATED_DEFICIT:
                yield block or "(top level)"
            for key, child in node.items():
                yield from _verdicts(child, block or key)
        elif isinstance(node, list):
            for child in node:
                yield from _verdicts(child, block)

    lines = [
        "",
        "**How many demonstrated deficits each walked record holds today.** A "
        "tier or a cell whose corrected interval lies entirely below zero is a "
        "demonstrated deficit — a different statement from *no demonstrated "
        "edge*, and one this file has published as ZERO about a record that "
        "held dozens. Counted here from the `verdict` each record stores, per "
        "block, so neither the tally nor the population can be typed.",
        "",
        "| Record | Graded bets | Games | Demonstrated deficits, by block |",
        "|:---|---:|---:|:---|",
    ]
    for relative in sorted(walker.SCORED_RECORDS):
        payload = json.loads((outputs / relative).read_text(encoding="utf-8"))
        tally = collections.Counter(_verdicts(payload))
        spelled = (
            ", ".join(f"{name} {count}" for name, count in sorted(tally.items()))
            or "none"
        )
        bets = payload.get("bets_graded")
        games = payload.get("games")
        lines.append(
            f"| `{relative}` | {'—' if bets is None else format(bets, ',')} | "
            f"{'—' if games is None else format(games, ',')} | {spelled} |"
        )
    return lines


def fenced(text: str, begin: str = BEGIN_MARKER) -> str | None:
    """One block's contents.

    **The end marker is found AFTER the opening one, not from the start of the
    file.** Both fences close with the same `<!-- END GENERATED -->`, so a
    `text.find(END_MARKER)` reaches the first close in the document whichever
    block was asked for -- which would have made the second fence read the
    first one's body, and `--check` compare the wrong two strings.
    """
    start = text.find(begin)
    if start == -1:
        return None
    stop = text.find(END_MARKER, start)
    if stop == -1:
        return None
    return text[start + len(begin) : stop].strip("\n")


def outside_every_fence(text: str) -> str:
    """The document's hand-written prose: every generated block removed."""
    for begin in MARKERS:
        start = text.find(begin)
        if start == -1:
            continue
        stop = text.find(END_MARKER, start)
        if stop == -1:
            continue
        text = text[:start] + text[stop + len(END_MARKER) :]
    return text


def splice(path: Path, body: str, begin: str = BEGIN_MARKER) -> bool:
    text = path.read_text(encoding="utf-8")
    start = text.find(begin)
    stop = text.find(END_MARKER, start) if start != -1 else -1
    if start == -1 or stop == -1:
        raise SystemExit(
            f"{path.name} has no {begin} block. Add the markers around it:"
            f"\n  {begin}\n  {END_MARKER}"
        )
    updated = (
        text[: start + len(begin)] + "\n\n" + body + "\n\n" + text[stop:]
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

    stale = []
    for label, begin, build, documents in fences():
        body = build()
        for path in documents:
            if arguments.check:
                if fenced(path.read_text(encoding="utf-8"), begin) != body:
                    stale.append(f"{path.name}:{label}")
                continue
            moved = splice(path, body, begin)
            print(f"{path.name} {label}: {'rewritten' if moved else 'unchanged'}")
    if stale:
        print(f"stale generated block in: {', '.join(stale)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
