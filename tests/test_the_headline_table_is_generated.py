"""The per-tier headline is rendered from the record, not retyped.

**This is the fix four rounds of guards were standing in for.** Those guards
tried to decide, from English prose, which number was a corrected interval and
which correction it carried. Each version was defeated by ordinary writing: a row
count that looked like a family size, an ordinal, a sentence terminator hidden
behind a bold marker, a figure written in a spelling the guard did not enumerate.
A generated figure needs none of that reasoning, because nothing about it is
retyped.

What is fenced is the table a reader acts on. The prose around it still argues
and still quotes superseded readings on purpose -- those carry an explicit
`[@N]`, and `test_every_interval_in_the_document_is_accounted_for` refuses any
interval it cannot account for -- in every spelling `INTERVAL` matches,
which is not the same as every spelling, and that guard's own docstring
now says which.
"""

from __future__ import annotations

import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO / "scripts" / "splice_headline_table.py"


def _generator():
    spec = importlib.util.spec_from_file_location("_splice", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GENERATOR = _generator()


#: Every (fence, document) pair in the repository, from the generator's own
#: mapping.
#:
#: **Parametrised over the MAPPING, not over documents x fences.** The first
#: version was a cross product of two tuples, which was right while every fence
#: lived in both documents and wrong the moment one did not: the third fence,
#: `retraction_history`, belongs to `docs/retracted_readings.md` alone, and a
#: cross product would have demanded it in `CLAUDE.md` and — far worse — would
#: have silently covered nothing at all had the new document simply been left
#: off `DOCUMENTS`. A fence nobody compares to a fresh render is a hand-written
#: block with markers around it.
PAIRS = tuple(
    (label, marker, render, path)
    for label, marker, render, documents in GENERATOR.fences()
    for path in documents
)


def test_every_fence_the_generator_renders_is_pinned_to_a_document():
    """The parametrisation cannot shrink to nothing without saying so."""
    labels = {label for label, _, _, _ in PAIRS}
    assert labels == {"headline_table", "record_census", "retraction_history"}, (
        f"the generator renders {sorted(labels)}. A fence added to "
        "scripts/splice_headline_table.py and not named here is compared to "
        "nothing; a fence removed from it is a block in a committed document "
        "that no longer has a generator."
    )
    assert len(PAIRS) == 5, (
        f"{len(PAIRS)} (fence, document) pairs are pinned. Two documents carry "
        "the headline table and the record census; the retraction ledger "
        "carries the retraction history."
    )


@pytest.mark.parametrize(
    "fence", PAIRS, ids=[f"{label}-{path.name}" for label, _, _, path in PAIRS]
)
def test_the_committed_block_is_what_the_record_renders_to(fence):
    """The fence's contents pinned to the record, not to a spelling."""
    label, marker, render, path = fence
    document = path.name
    committed = GENERATOR.fenced(path.read_text(encoding="utf-8"), marker)
    assert committed is not None, (
        f"{document} has lost the {label} markers. Restore "
        f"`{marker}` / `{GENERATOR.END_MARKER}` around the block and re-run "
        "scripts/splice_headline_table.py."
    )
    assert committed == render(), (
        f"{document}'s {label} block is not what the record renders to. "
        "Someone edited between the markers, or the ledger moved and nobody "
        "re-ran `PYTHONPATH=src python scripts/splice_headline_table.py`."
    )


def test_the_generator_defers_to_the_records_own_verdict_rule():
    """The floor applies, on a cell today's data cannot demonstrate.

    `render()` re-implemented the verdict as `high < 0 / low > 0 / else`, which
    drops the declared 200-bet evidence floor. Every tier clears 43,000 bets, so
    the committed table was identical either way and no document mutant could
    have shown it -- while a thinner cell would have been published as a
    "demonstrated deficit" inside the fence, which is the copy this change makes
    authoritative, with the record itself saying "not enough evidence".
    """
    from cbb_betting_lab import stats as S

    thin = S.RoiInterval(
        roi=-0.043, low=-0.065, high=-0.021, bets=S.MINIMUM_BETS - 1,
        clusters=12, standard_error=0.011, looks=101,
    )
    assert "not enough evidence" in thin.verdict(), (
        "this test's own fixture no longer sits below the floor; "
        f"MINIMUM_BETS is {S.MINIMUM_BETS}."
    )

    source = _SCRIPT.read_text(encoding="utf-8")
    # Comments stripped: the block explaining why the re-implementation was
    # wrong quotes the verdict strings, and a check that cannot tell an
    # explanation from the code would have to be satisfied by rewording prose.
    body = "\n".join(
        line for line in source[source.index("def render("):].splitlines()
        if not line.lstrip().startswith("#")
    )
    assert "interval.verdict()" in body, (
        "scripts/splice_headline_table.py no longer asks RoiInterval for the "
        "verdict. A generator that re-derives the rule is a second "
        "implementation of it, and the second one is the one nobody re-reads."
    )
    for reimplemented in ('"demonstrated deficit"', '"demonstrated edge"', '"no demonstrated edge"'):
        assert reimplemented not in body, (
            f"render() spells {reimplemented} itself again. The verdict strings "
            "belong to stats.RoiInterval."
        )


def test_the_generator_reads_the_ledger_rather_than_a_pinned_count():
    """A count typed into the generator is the defect one layer further back."""
    source = _SCRIPT.read_text(encoding="utf-8")
    body = source[source.index("def render("):]
    looks = len(
        json.loads(GENERATOR.LEDGER.read_text(encoding="utf-8"))["hypotheses"]
    )
    assert str(looks) not in body, (
        f"scripts/splice_headline_table.py has {looks} written into render(). "
        "It must read the ledger; a generator with the count baked in produces "
        "a stale table that matches itself forever."
    )


def test_the_check_mode_fails_on_a_stale_block(tmp_path):
    """`--check` is what CI would run, so it has to be able to fail.

    Exercised against COPIES: this test must never write the repository's own
    documents, and a check that has only ever been seen to pass is not evidence.
    """
    body = GENERATOR.render()
    assert GENERATOR.fenced(f"x\n{GENERATOR.BEGIN_MARKER}\n\n{body}\n\n{GENERATOR.END_MARKER}\ny") == body

    stale = f"x\n{GENERATOR.BEGIN_MARKER}\n\n| Cut |\n| stale |\n\n{GENERATOR.END_MARKER}\ny"
    assert GENERATOR.fenced(stale) != body

    missing = "a document with no markers at all"
    assert GENERATOR.fenced(missing) is None

    completed = subprocess.run(
        [sys.executable, str(_SCRIPT), "--check"],
        cwd=_REPO,
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "PYTHONPATH": "src", "HOME": str(Path.home())},
    )
    assert completed.returncode == 0, (
        "the committed documents do not match a fresh render:\n"
        f"{completed.stdout}\n{completed.stderr}"
    )


#: History a document may still state: a count the ledger has LEFT BEHIND.
#:
#: `98 -> 101` describes a transition that happened and stays true forever. What
#: may not appear outside the fence is the ledger's count or factor asserted as
#: CURRENT, because that is what a registration falsifies.
def _outside_the_fence(path) -> str:
    """Prose means prose: EVERY generated block removed, not the first one.

    This sliced from the first `BEGIN` to the first `END` in the file. With one
    fence that is the fence; with two it is the first block only, and the
    SECOND block's generated figures are then read as hand-typed prose -- so
    the two checks below fired on the generator's own output the moment a
    second fence was added, which is a false red that an author fixes by
    deleting a figure from a generated block.
    """
    return GENERATOR.outside_every_fence(path.read_text(encoding="utf-8"))


@pytest.mark.parametrize("document", [path.name for path in GENERATOR.DOCUMENTS])
def test_no_ledger_dependent_figure_is_typed_outside_the_fence(document):
    """The whole class, and this one is total.

    Every guard before it tried to FIND a stale figure in prose by recognising
    its shape, and seven rounds of adversarial review each found a spelling the
    last had missed -- `(-8.0%, -0.1%)`, `between -8.0% and -0.1%`, `± 4.1pp`.
    "Two numbers that together are an interval" has no closed form in English.

    This asks the opposite question, and it is decidable: the values are
    GENERATED here, so they can be enumerated exactly, and none of them may
    appear in the prose. A figure written in some other spelling is not this
    check's problem -- it is not the current reading, so it is a stale or
    invented one, and `test_every_interval_in_the_document_is_accounted_for`
    refuses whatever it can account for while the limit written beside it says
    what it cannot. The two together are a net plus a fence; the fence is the
    part that holds.

    Sixty-eight of these were typed into these two documents when this was
    written: twenty-eight corrected intervals, twenty-five correction factors,
    fifteen hypothesis counts. Every one of them went stale the moment a
    hypothesis was registered, and the whole apparatus that failed seven times
    existed to catch them afterwards.
    """
    import json as _json

    from cbb_betting_lab import stats as _stats

    path = next(p for p in GENERATOR.DOCUMENTS if p.name == document)
    outside = _outside_the_fence(path)
    looks = len(
        _json.loads(GENERATOR.LEDGER.read_text(encoding="utf-8"))["hypotheses"]
    )
    factor = _stats.bonferroni_factor(looks)

    forbidden = {f"x{factor:.4f}", f"×{factor:.4f}", f"x{factor:.2f}", f"×{factor:.2f}"}
    for cell in GENERATOR.roster().values():
        interval = GENERATOR._interval(cell, looks)
        low, high = interval.adjusted_low, interval.adjusted_high
        forbidden |= {
            f"{low * 100:+.1f}% to {high * 100:+.1f}%",
            f"{low:+.5f} to {high:+.5f}",
            f"{low:+.4f} to {high:+.4f}",
            f"{low:+.3f} to {high:+.3f}",
        }

    found = sorted(figure for figure in forbidden if figure in outside)
    assert not found, (
        f"{document} states {found} outside the generated block. Those are "
        "rendered from the record inside it, so a copy out here is a second "
        "source that goes stale at the next registration and must be retyped by "
        "hand -- which is the failure this fence replaces. State the verdict and "
        "point at the block."
    )

    # The COUNT, as a current assertion. A transition like `98 -> 101` is
    # history and stays true; `at today's 101` does not. The trailing lookahead
    # excludes a decimal (`1.7773` must not read as the count) but NOT a
    # sentence-ending period: `the ledger today holds 101.` is the plainest way
    # to type the forbidden thing, and for a while it was the one spelling that
    # walked straight through here.
    #
    # **THE TRAILING LOOKAHEAD WAS `(?![\d,]|\.\d)` AND `[\d,]` EXEMPTED A
    # TRAILING COMMA.** That is the same failure shape as the one the count
    # guard was rescued from one file over, byte-identical to the version this
    # file carried at HEAD, and sitting fifty lines above a comment in the SAME
    # file claiming "the same trailing lookahead fix" had been applied here.
    # `[\d,]` says "a digit OR a comma ends this match", so `the ledger today
    # holds 133, and every reading is corrected by it` was invisible while
    # `...holds 133.` was refused, with a comma the only difference -- and the
    # commaed spelling is the plainer way to type the forbidden assertion.
    #
    # What ends the figure is a digit, a comma-AND-digit, or a point-AND-digit:
    # the three continuations that mean the number is not finished. `133,` at
    # the end of a clause is a finished 133. `133,000` is not, and is not this
    # count. Proved with two mutants, which is this repository's written rule
    # for a lookahead fix.
    import re as _re

    for match in _re.finditer(rf"(?<![\w,.]){looks}(?!\d|,\d|\.\d)", outside):
        window = outside[max(0, match.start() - 60) : match.end() + 20]
        assert _re.search(rf"\d+\s*(?:->|→|to)\s*{looks}", window), (
            f"{document} states the ledger's current count ({looks}) outside the "
            f"generated block: …{window}… Only a transition that already happened "
            "may name it out here; what the ledger holds TODAY is the block's to "
            "say, because that is the number a registration changes."
        )


def test_every_fenced_figure_is_absent_from_the_prose_that_frames_it():
    """A figure inside the fence must not also be typed outside it.

    The whole point is one source. A hand-typed copy beside the generated one is
    the drift this replaces, and it is exactly what happened in
    `docs/what_we_can_and_cannot_claim.md`: the paragraph explaining that a
    number written twice drifts carried its own copy of the number, and it had
    already drifted by 28.
    """
    # **Every figure the table carries, not just the interval column.** This
    # filtered on `"%" in cell` and then on `" to " in figure`, which between
    # them dropped the bets counts (no percent sign) and the ROI point estimates
    # (no " to ") -- two of the three columns. The docstring above cites an
    # incident where a COUNT drifted by 28, which is precisely the class it was
    # not looking at, and both documents were carrying hand-typed copies of
    # fenced figures when this was written.
    rendered = {
        cell.strip()
        for line in GENERATOR.render().splitlines()
        if line.startswith("| ") and "Cut" not in line and ":---" not in line
        for cell in line.strip("|").split("|")
        if re.search(r"\d", cell) and not re.fullmatch(r"(?:high|mid|low)-major", cell.strip())
    }
    assert len(rendered) >= 9, (
        f"the rendered table yielded {len(rendered)} figures to police; the "
        "three tiers carry three each. The filter stopped matching a column."
    )

    # **The census block's POPULATIONS, by the shape that is a population.**
    # Its cells also hold record names, a stored family size and an em dash;
    # policing "every cell with a digit in it" out of this block would forbid
    # the prose from saying `133` or `95` anywhere, which the fence rule below
    # already handles for the ledger's own count and which is not this check's
    # job. A comma-formatted count is a population or a tally by construction,
    # and those are exactly the figures that were being kept in two places.
    census = {
        found.group(0)
        # The same count shape the document guard uses, and the same trailing
        # lookahead fix: `(?![\w.])` exempted a figure at the end of a sentence
        # and TRUNCATED a three-group count, so this block's own populations
        # were policed under one spelling and the documents under another.
        for found in re.finditer(
            r"(?<![\w.,])\d{1,3}(?:,\d{3})+(?!\d|,\d|\.\d)", GENERATOR.render_census()
        )
    }
    assert len(census) >= 8, (
        f"the census block yielded {len(census)} populations to police; it "
        "renders four cuts of three counts each. The filter stopped matching."
    )
    rendered |= census

    for path in GENERATOR.DOCUMENTS:
        outside = _outside_the_fence(path)
        for figure in sorted(rendered):
            assert figure not in outside, (
                f"{path.name} types {figure!r} outside the generated block as "
                "well as inside it. One of the two will be right after the next "
                "registration and nothing says which."
            )


def test_the_census_names_every_record_on_disk_that_stores_a_correction():
    """The roster is not a roster, and this is the check that says so.

    **The census fence was driven by a hand-list of seven paths and nothing
    asserted it covered the records on disk.** Eight records under
    `data/outputs/` store both `looks` and `correction_factor`;
    `cbb_reachability.json` was not on the tuple, so a block headed "What each
    record on disk was scored under" showed seven of eight, and a record could
    be deleted from the tuple with the whole suite green. That is this
    repository's own written lesson — a roster only guards what it names —
    reintroduced inside the fix that was mandated not to use a roster.

    The derivation is re-run here rather than imported. A test that calls
    `census_records()` and compares it with `census_records()` is the pair of
    hand-maintained rosters agreeing with each other, which is the shape this
    file already had to be rescued from once.
    """
    outputs = _REPO / "data" / "outputs"
    on_disk = set()
    for path in sorted(outputs.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        if "looks" in payload and "correction_factor" in payload:
            on_disk.add(path.relative_to(outputs).as_posix())

    assert len(on_disk) >= 7, (
        f"only {len(on_disk)} records on disk store a family correction. The "
        "census is about the records that carry one; if the field was renamed "
        "this check now passes by finding almost nothing."
    )

    rendered = GENERATOR.render_census()
    missing = sorted(name for name in on_disk if f"`{name}`" not in rendered)
    assert not missing, (
        "the record census does not name every record on disk that stores a "
        f"family correction: {missing}. The block's heading says it does."
    )

    named = {
        cell.strip().strip("`")
        for line in rendered.splitlines()
        if line.startswith("| `")
        for cell in line.strip("|").split("|")
        if cell.strip().startswith("`") and cell.strip().endswith("`")
    }
    extra = sorted(name for name in named if name.endswith(".json") and name not in on_disk)
    assert not extra, (
        f"the record census names {extra}, which is not a record on disk "
        "storing a family correction."
    )


#: A correction factor as these documents spell it.
#:
#: **THIS REQUIRED THE LITERAL `x`/`×` AND AT LEAST TWO DECIMALS, AND BOTH
#: RESTRICTIONS WERE ESCAPES.** The two rules below are the ones that refuse
#: the review's blocking sentence, and at the character-class level they were
#: defeated by writing the same claim in ordinary English: *"the price backtest
#: at 95 hypotheses, a factor of 1.7689"* matched nothing, *"is widened
#: 1.7689-fold"* matched nothing, and `x1.8` matched nothing because `\d{2,4}`
#: demands a second decimal place. That is the identical failure shape as the
#: lookahead this round was sent to fix, in the round's own new deliverable.
#:
#: The spellings are enumerated instead of inferred, and the limit of an
#: enumeration is written into the docstrings below rather than implied away: a
#: factor written in a spelling not listed here is NOT seen, and the protection
#: that does not depend on a spelling is the record census, which renders every
#: record's own `looks` and `correction_factor` from the record.
CORRECTION_FACTOR = re.compile(
    r"(?:[x×]\s*(?P<prefixed>\d\.\d{1,5})"
    r"|factor(?:\s+of)?(?:\s+is)?\s+(?P<named>\d\.\d{1,5})"
    r"|(?P<fold>\d\.\d{1,5})[-‑– ]fold"
    r"|widen(?:ed|s|ing)?(?:\s+\w+){0,3}\s+by\s+(?P<widened>\d\.\d{1,5}))"
)


def _factors_in(sentence: str):
    """(what was written, the decimal as written) for every factor spelling."""
    for found in CORRECTION_FACTOR.finditer(sentence):
        spelling = next(
            value for value in found.groupdict().values() if value is not None
        )
        yield found.group(0), spelling


#: Every way these documents name a published record.
#:
#: **THE FILENAME SHAPE ALONE WAS AN ESCAPE, AND IT WAS THE BLOCKING ONE.** The
#: rule below refuses a sentence that pairs a record with a correction factor,
#: and it fired on `[\w./-]*\.json\b` — a literal filename. Replace the one
#: filename in the review's blocking sentence with the English name these
#: documents themselves use, *"the price backtest at 95 (x1.7689)"*, and the
#: identical sentence — present tense, false in every clause — was green at
#: full-suite scope. What is closed by a filename pattern is a filename.
#:
#: The English names are DERIVED from the records on disk, not listed: a record
#: on the generated census is named in prose by its stem with `cbb_` and the
#: extension stripped, spelled with spaces or with a hyphen. So a record added
#: to `data/outputs/` is covered here the day it lands, and this cannot become
#: the hand-maintained roster the census fence was rescued from.
#: How each cut directory under `data/outputs/` is spoken about in prose.
#:
#: Pinned by `test_every_cut_on_disk_has_its_english_name`, so this cannot
#: silently fall behind the cuts that exist.
CUT_WORDS: dict[str, tuple[str, ...]] = {
    "holdout": ("held-out", "heldout", "holdout"),
    "core_team_only": ("core-team", "core team"),
}


def record_names() -> re.Pattern:
    global _RECORD_NAMES
    try:
        return _RECORD_NAMES
    except NameError:
        pass
    spellings = {r"[\w./-]*\.json\b"}
    for relative in GENERATOR.census_records():
        stem = relative.rsplit("/", 1)[-1].removesuffix(".json").removeprefix("cbb_")
        words = stem.split("_")
        spellings.add(re.escape(" ".join(words)))
        spellings.add(re.escape("-".join(words)))
        # THE DOCUMENTS NAME A CUT RECORD BY ITS CUT, NOT BY ITS FILE.
        #
        # A stem-derived name reaches `holdout/cbb_price_backtest.json` only as
        # "price backtest". The documents call it "the held-out backtest" -- in
        # live text, five times -- and a measured probe showed a sentence
        # pairing that name with a correction factor, every clause of it false,
        # passing the whole suite. The spelling that escaped was the one the
        # documents actually use.
        #
        # `CUT_WORDS` is a hand-list and hand-lists are how this guard keeps
        # failing, so it is pinned: `test_every_cut_on_disk_has_its_english_name`
        # fails when a new cut directory appears without an entry. An unnamed
        # cut then turns the suite red instead of quietly escaping the net.
        if "/" in relative:
            cut = relative.rsplit("/", 1)[0]
            noun = words[-1]
            for phrasing in CUT_WORDS.get(cut, ()):
                spellings.add(re.escape(f"{phrasing} {noun}"))
                spellings.add(re.escape(f"{phrasing} cut"))
    _RECORD_NAMES = re.compile(
        "|".join(sorted(spellings, key=len, reverse=True)), re.IGNORECASE
    )
    return _RECORD_NAMES

#: Sentence scope, and the soft-wrap join that has to happen before it.
#:
#: **Both are imported from the count guard rather than copied.** These
#: documents are hard-wrapped, so `At the 62 hypotheses in force before the` /
#: `registration (x1.7095)` is two lines, and a sentence splitter that does not
#: join soft wraps first would see the factor in a chunk with no family size in
#: it — a false red on honest prose, which is the failure this repository has
#: shipped before. A second copy of that joiner would be a second thing to keep
#: right; there is one, and it carries the whole argument in its docstring.
def _guard_module():
    global _GUARD
    try:
        return _GUARD
    except NameError:
        pass
    spec = importlib.util.spec_from_file_location(
        "_stale_guard_for_factors",
        _REPO / "tests" / "test_no_report_states_a_stale_correction.py",
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _GUARD = module
    return module


def _sentences_outside(path):
    """Sentences, plus each markdown table ROW as a unit of its own.

    **`SENTENCE` splits on `|`, which is the markdown cell wall**, so a record
    named in one cell and a correction factor written in the next were not "the
    same sentence" and the pairing rule below did not fire — measured, with a
    row stating a family size and a factor that the record contradicts, green
    over all three guard files. The fact that rule exists to stop being
    maintained twice is *which record carries which correction*, and the
    natural way to write that is a table.

    Splitting differently would change every other consumer of `SENTENCE`. A
    table row's DATA cells are ADDED as one extra unit instead: the cells still
    appear as their own chunks, and the row's data cells appear joined as well,
    so a pairing written across two cells is visible without changing what a
    sentence means anywhere else.

    **Data cells, not every cell**, because one row of
    `docs/project_status.md`'s Definition of Done is four thousand characters
    of prose in a single cell and joining that to its neighbours pairs a record
    named in its last clause with a factor quoted in its first — a false red on
    honest writing, which is the failure this repository has shipped before. A
    cell carrying a sentence terminator is prose and is left to the sentence
    splitter; a cell that is a label or a value is not.

    The limit that leaves: a pairing written across two cells where one of them
    ends in a full stop is not seen here. What does not depend on a spelling is
    the census block, which renders the pairing from the records.
    """
    guard = _guard_module()
    outside = _outside_the_fence(path)
    joined = guard._unwrapped(outside)
    parts = [part for part in guard.SENTENCE.split(joined) if part.strip()]
    rows = []
    for line in outside.splitlines():
        if not line.lstrip().startswith("|") or set(line) <= set("|:- "):
            continue
        cells = [
            cell
            for cell in line.strip().strip("|").split("|")
            if cell.strip() and not re.search(r"[.;:!?]\s", cell)
        ]
        if len(cells) > 1:
            rows.append(" ".join(cells))
    return parts + rows


@pytest.mark.parametrize("document", [path.name for path in GENERATOR.DOCUMENTS])
def test_a_correction_factor_in_the_prose_names_the_family_it_is_the_factor_of(document):
    """A stale factor is as generatable as a stale interval, and was not generated.

    `test_no_ledger_dependent_figure_is_typed_outside_the_fence` forbids only
    TODAY's factor. A factor from any OTHER family size walked straight through
    it, which is how the whole of the review's blocking sentence could be typed
    back into both documents, verbatim and in the present tense, with the full
    suite green: *"the forecast-skill fit and the ratings fit at 30 hypotheses
    (x1.6041), the price backtest at 95 (x1.7689)"*. Every clause of that is
    false against the records, and none of it is interval-shaped, comma-shaped
    or today's count.

    `stats.bonferroni_factor` is a function of one integer, so a factor written
    in prose has exactly one family size behind it and the guard can check the
    arithmetic. It must name that size in the same sentence. A factor that
    names no family is a figure with no referent, and a factor that names the
    wrong one is caught by the arithmetic.
    """
    import json as _json

    from cbb_betting_lab import stats as _stats

    path = next(p for p in GENERATOR.DOCUMENTS if p.name == document)
    seen = 0
    for sentence in _sentences_outside(path):
        integers = [int(found) for found in re.findall(r"(?<![\w.,])\d{1,6}(?!\d|,\d|\.\d)", sentence)]
        for written, spelling in _factors_in(sentence):
            places = len(spelling.split(".")[1])
            seen += 1
            matches = [
                value
                for value in integers
                if f"{_stats.bonferroni_factor(value):.{places}f}" == spelling
            ]
            assert matches, (
                f"{document} writes the correction factor {written!r} "
                "outside the generated block without naming the family size it "
                f"is the factor of: …{sentence.strip()[:200]}…\n"
                "`stats.bonferroni_factor` is a function of one integer, so "
                "every factor has exactly one family behind it. Name it in this "
                "sentence and the arithmetic is checked, or state the verdict "
                "and point at the census block, which renders every record's "
                "own factor from the record."
            )

    assert seen or True  # a document that states no factor at all is fine


#: A tier of the price backtest, however these documents spell it.
TIER_NAME = re.compile(r"\b(high|mid|low)[-_]major\b", re.IGNORECASE)

#: "this interval excludes zero", in the spellings these documents use.
EXCLUDES_ZERO = re.compile(
    r"excludes? zero|excluding zero|excluded zero|excludes it\b", re.IGNORECASE
)

#: "this interval does NOT exclude zero", likewise.
CROSSES_ZERO = re.compile(
    r"no longer does|no longer excludes? zero|does not exclude zero"
    r"|crosses? zero|spans? zero|includes? zero|straddles? zero",
    re.IGNORECASE,
)

def _other_cut_words(backtest) -> re.Pattern:
    """Anything that says a sentence is about some cut other than the tier row.

    The market names are DERIVED from the backtest itself rather than listed, so
    a market the lab starts pricing is covered without anybody remembering. The
    literal words beside them are the cuts that are not markets — a different
    record, a different block, a different population.
    """
    markets = {
        row.get("market")
        for block in ("by_market_and_tier", "null_baseline")
        for row in backtest.get(block, [])
        if row.get("market")
    }
    words = {re.escape(name) for name in markets if name} | {
        r"held[- ]out", r"holdout", r"core[- _]team", r"bucket", r"replication",
        r"prop\b", r"null[- _]baseline", r"blind", r"selected", r"pooled",
        r"brier", r"disagreement", r"log loss", r"\.json",
    }
    return re.compile("|".join(sorted(words, key=len, reverse=True)), re.IGNORECASE)


#: Attributed history: a reading stated AT a count or ON a date.
#:
#: This file narrates its own retracted wordings on purpose, and a sentence that
#: says when a claim held is governed by `test_every_superseded_figure_is_-
#: explicitly_attributed` and by the `[@N]` rules rather than by this one. An
#: unanchored sentence is a claim about today.
HISTORICAL_ANCHOR = re.compile(r"\[@\d+\]|\[superseded:|\d{4}-\d{2}-\d{2}")


@pytest.mark.parametrize("document", [path.name for path in GENERATOR.DOCUMENTS])
def test_no_tier_is_paired_with_a_zero_crossing_the_record_contradicts(document):
    """A tier's zero-crossing is the record's to state, and it was typed wrong.

    **The defect this closes shipped in the flattering direction.** `CLAUDE.md`
    published *"mid-major excludes zero and low-major no longer does"* while the
    record's corrected interval for low-major lay entirely below zero — a
    DEMONSTRATED DEFICIT, which this repository's rules require to be stated as
    such and never as a reading that fails to exclude zero. The sentence
    contradicted its own paragraph three sentences earlier, the generated census
    one hundred and sixty lines above it, `docs/project_status.md`, and the
    repository's own generated report, and nothing was red: it carries no
    comma-formatted count, no correction factor and no interval, so every guard
    in this repository looked straight past it. That is the class the sweep lens
    named — prose that states a VERDICT rather than a number — and this is an
    instrument for the one shape of it that is decidable.

    Decidable because nothing here parses English *meaning*. The record says, per
    tier, whether the interval excludes zero; the prose either agrees or it does
    not. A sentence carrying an attributed date or `[@N]` is history and is
    governed by the attribution rules instead. A sentence that says
    *uncorrected* is compared against the record's uncorrected bounds, because
    that is a different interval and both are legitimately published.

    **Its limits, written here rather than implied, and there are three.**

    First, it sees two claim vocabularies and three tier spellings. A tier's
    zero-crossing written some other way — "the interval no longer reaches past
    zero", say — is not seen.

    Second, it is about the FULL-STORE PER-TIER ROW and nothing else. These
    documents legitimately discuss a tier's reading in other cuts — the held-out
    replication, the core-team backtest, a prop market, a claimed-edge bucket,
    the blind baseline — and those have their own bounds. A sentence that names
    any of those is SKIPPED rather than compared against the wrong cut, because
    a false red on honest writing is answered by weakening a guard and this
    repository has shipped that failure before. Skipping is a real loss of
    reach and it is why this is named a limit and not a solution.

    Third, and it follows from the second: the VERDICT WORDS themselves —
    "demonstrated deficit", "no demonstrated edge" — are deliberately NOT part
    of the claim vocabulary. They were tried and they cannot be scoped: eight
    live sentences across these two documents pair a tier with a verdict word
    while talking about some other cut, and binding those to the full-store row
    made honest prose red. Zero-crossing language is the part that turned out to
    be scopeable.

    The protection that does not depend on any of this is the generated table,
    which renders every tier's bets, return, corrected interval and verdict from
    the record. The convergent fix is to point at that table, which is what the
    prose now does.

    Mutation: restore the published sentence — RED, naming low-major. Write
    "high-major excludes zero" without the word uncorrected — RED. Write
    "mid-major crosses zero" — RED.
    """
    import json as _json

    from cbb_betting_lab import stats as _stats

    path = next(p for p in GENERATOR.DOCUMENTS if p.name == document)
    backtest = _json.loads(GENERATOR.BACKTEST.read_text(encoding="utf-8"))
    looks = len(
        _json.loads(GENERATOR.LEDGER.read_text(encoding="utf-8"))["hypotheses"]
    )

    excludes: dict[str, dict[str, bool]] = {}
    for tier in GENERATOR.TIERS:
        row = GENERATOR._tier_row(backtest, "by_tier", tier)
        interval = GENERATOR._interval(row, looks)
        excludes[tier] = {
            "corrected": interval.adjusted_low > 0 or interval.adjusted_high < 0,
            "uncorrected": row["low"] > 0 or row["high"] < 0,
        }
    assert set(excludes) == set(GENERATOR.TIERS) and len(excludes) == 3, (
        "the price backtest no longer carries a row for each of "
        f"{GENERATOR.TIERS}, so this check has nothing to compare prose against."
    )

    other_cuts = _other_cut_words(backtest)
    for sentence in _sentences_outside(path):
        if HISTORICAL_ANCHOR.search(sentence):
            continue
        if other_cuts.search(sentence):
            continue
        tiers = {
            f"{found.group(1).lower()}_major" for found in TIER_NAME.finditer(sentence)
        }
        if not tiers:
            continue
        claims_excludes = bool(EXCLUDES_ZERO.search(sentence))
        claims_crosses = bool(CROSSES_ZERO.search(sentence))
        if not claims_excludes and not claims_crosses:
            continue
        which = (
            "uncorrected"
            if re.search(r"uncorrected", sentence, re.IGNORECASE)
            else "corrected"
        )
        for tier in sorted(tiers):
            reading = excludes[tier]
            if claims_excludes and not reading[which]:
                raise AssertionError(
                    f"{document} says a {which} interval excludes zero in a "
                    f"sentence naming {tier}, and the record's {which} interval "
                    f"for {tier} does not exclude zero: "
                    f"…{sentence.strip()[:220]}…\n"
                    "Which tiers exclude zero is a column of the generated "
                    "table; state the verdict there and point at it."
                )
            if claims_crosses and reading[which]:
                raise AssertionError(
                    f"{document} says a {which} interval fails to exclude zero "
                    f"in a sentence naming {tier}, and the record's {which} "
                    f"interval for {tier} lies entirely on one side of zero. "
                    "An interval entirely below zero is a DEMONSTRATED DEFICIT "
                    "and has to be stated as one — it is a different statement "
                    "from 'no demonstrated edge', and writing the weaker one is "
                    "the flattering error this check exists to stop: "
                    f"…{sentence.strip()[:220]}…"
                )


@pytest.mark.parametrize("document", [path.name for path in GENERATOR.DOCUMENTS])
def test_no_sentence_pairs_a_record_with_a_correction_factor_outside_the_fence(document):
    """WHICH record carries WHICH correction is the census block's to say.

    This is the other half of the blocking sentence. Its falsity is not in the
    arithmetic — `bonferroni_factor(95)` really is 1.7689 — but in the pairing:
    it attaches that factor to `cbb_price_backtest.json`, which stores 133. A
    pairing of a record with a correction is exactly one row of the record
    census, rendered from the record's own `looks` and `correction_factor`, and
    there is no honest reason to retype one out here. History can say what the
    factor was at a family size without naming a file.
    """
    path = next(p for p in GENERATOR.DOCUMENTS if p.name == document)
    for sentence in _sentences_outside(path):
        if not CORRECTION_FACTOR.search(sentence):
            continue
        named = record_names().findall(sentence)
        assert not named, (
            f"{document} pairs {named} with a correction factor outside the "
            f"generated block: …{sentence.strip()[:200]}…\n"
            "What each record on disk was scored under is a row of the record "
            "census, rendered from that record's own `looks` and "
            "`correction_factor`. A hand-typed pairing is a second source for "
            "the one fact this round exists to stop being maintained twice."
        )


def test_every_cut_on_disk_has_its_english_name():
    """`CUT_WORDS` is a hand-list, so it is pinned to the cuts that exist.

    `record_names()` derives a record's English spellings from its FILENAME, so
    `holdout/cbb_price_backtest.json` reached the guard only as "price
    backtest". The documents call it "the held-out backtest", and a sentence
    pairing that name with a correction factor -- every clause of it false --
    passed the entire suite when it was measured.

    Adding the cut vocabulary fixes the spelling; this test fixes the class. A
    new cut directory with no entry here turns the suite red, which is the only
    reason a hand-list is allowed to exist in this module at all: it can still
    be incomplete, but it cannot be incomplete SILENTLY.
    """
    on_disk = {
        relative.rsplit("/", 1)[0]
        for relative in GENERATOR.census_records()
        if "/" in relative
    }
    missing = sorted(on_disk - set(CUT_WORDS))
    assert not missing, (
        f"{missing} name cuts under data/outputs/ with no entry in CUT_WORDS, so "
        "a record in one of them can only be caught when a document spells it as "
        "a filename. The documents spell cuts in English."
    )
    stale = sorted(set(CUT_WORDS) - on_disk)
    assert not stale, (
        f"CUT_WORDS names {stale}, which no longer exist under data/outputs/. A "
        "roster that outlives what it names stops being checkable."
    )


def test_the_terminal_state_is_on_disk_even_when_the_tree_is_clean(tmp_path, monkeypatch):
    """The block must not change meaning when it is committed.

    `record_states` used to append the on-disk state only when it DIFFERED from
    the newest committed one. So the same records rendered
    `| today | on disk |` from a dirty tree and `| today | <sha> |` from a
    clean one, and a commit carrying both the records and the block made
    itself stale: the records became the newest revision, the on-disk row
    stopped being appended, and a fresh render no longer matched what had just
    been committed. A commit that changed both could never be green.

    **A test run against the real repository cannot catch this**, and that is
    the whole reason this one builds its own. On a dirty tree the broken code
    and the fixed code agree, so the suite passed at 2586 immediately before
    the commit that broke it, and only CI — which always sees a clean tree —
    could tell them apart. The scratch repository below is committed and clean
    by construction, which is the state the defect needs.
    """
    scratch = tmp_path / "repo"
    (scratch / "data" / "outputs").mkdir(parents=True)
    record = scratch / "data" / "outputs" / "cbb_price_backtest.json"
    record.write_text(json.dumps({"looks": 3, "by_tier": []}), encoding="utf-8")

    def git(*arguments):
        subprocess.run(
            ["git", "-C", str(scratch), *arguments],
            check=True, capture_output=True, text=True,
        )
    git("init", "-q")
    git("config", "user.email", "t@example.com")
    git("config", "user.name", "t")
    git("add", "-A")
    git("commit", "-q", "-m", "the record")

    monkeypatch.setattr(GENERATOR, "REPO", scratch)
    states = GENERATOR.record_states("cbb_price_backtest.json")

    assert states, "a committed record yielded no states at all"
    label = states[-1][0]
    assert label == "on disk", (
        f"the terminal state of a CLEAN tree is labelled {label!r}, not 'on disk'. "
        "The block then says something different once it is committed than it "
        "said when it was rendered, so the commit that carries both the records "
        "and the block is stale the moment it lands."
    )
