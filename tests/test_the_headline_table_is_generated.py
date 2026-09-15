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
interval it cannot account for, in any spelling at all.
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


@pytest.mark.parametrize("document", [path.name for path in GENERATOR.DOCUMENTS])
def test_the_committed_block_is_what_the_record_renders_to(document):
    """The fence's contents pinned to the record, not to a spelling."""
    path = next(p for p in GENERATOR.DOCUMENTS if p.name == document)
    committed = GENERATOR.fenced(path.read_text(encoding="utf-8"))
    assert committed is not None, (
        f"{document} has lost its generated markers. Restore "
        f"`{GENERATOR.BEGIN_MARKER}` / `{GENERATOR.END_MARKER}` around the "
        "headline table and re-run scripts/splice_headline_table.py."
    )
    assert committed == GENERATOR.render(), (
        f"{document}'s generated block is not what the record renders to. "
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
    for path in GENERATOR.DOCUMENTS:
        text = path.read_text(encoding="utf-8")
        start = text.find(GENERATOR.BEGIN_MARKER)
        stop = text.find(GENERATOR.END_MARKER) + len(GENERATOR.END_MARKER)
        outside = text[:start] + text[stop:]
        for figure in sorted(rendered):
            assert figure not in outside, (
                f"{path.name} types {figure!r} outside the generated block as "
                "well as inside it. One of the two will be right after the next "
                "registration and nothing says which."
            )
