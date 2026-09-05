"""A verdict is stated at the correction the ledger owes **now**, not the one it owed then.

## The defect this module closes

Every record in `data/outputs/` stores the family-wise correction that was
current at the moment its run happened, and every rendered report restated that
stored number as though it were the answer. On 2026-09-05 the lab therefore had
three different corrections in force across its own documents at once:

    data/outputs/cbb_price_backtest.json        looks=30   factor=x1.6041
    data/outputs/holdout/cbb_replication.json   looks=62   factor=x1.7095
    data/outputs/experiment_ledger.json         looks=95   factor=x1.7689

and a reader had no way to tell which of the three a given number carried. Two
published verdicts were stale in the direction that matters — they read
*demonstrated deficit* at a correction narrower than the search that had
actually happened. That is the exact failure the ledger exists to prevent,
arriving through the reports rather than through the ledger.

It was not a one-off. **Every report is out of date the instant anybody
registers another hypothesis**, and this lab registers hypotheses on purpose:
33 of them landed in one commit before the player model existed.

## The choice, and why this one

Two designs were on the table. `docs/decision_log.md` decision 46 records the
call; this is the reasoning it points at.

**(a)** Every rendered report re-reads the ledger at render time and states its
verdicts at the current cumulative count, so a re-render is always current.

**(b)** A report states the factor it was computed at, in its own words, and
also names the current ledger count, so a reader is told plainly that the
verdicts below are stated at a narrower correction than the lab now owes.

This module implements **(a) for the verdicts and (b) for the provenance**, and
draws the line at the record/report seam:

* **A report is a statement a reader acts on, so it must be current.** Every
  report re-reads the ledger when it renders and re-derives every corrected
  interval and every verdict at the ledger's count *at render time*. Nothing is
  re-measured to do it: the point estimate, the standard error, the bet count
  and the cluster count are the measurement, and the correction is arithmetic
  applied on top of them. `RoiInterval.adjusted_low/high` is that arithmetic and
  it is already stored per row, which is why this costs nothing and needs no
  store — the mechanism `--rebuild-report-only` was built on.
* **A record is evidence of what was measured, so it does not move.** Rewriting
  a record's verdicts under a later correction would destroy the only copy of
  what the run actually computed and would make its `generated_at` a lie. So
  the record keeps its own `looks` and `correction_factor`, and the report it
  renders **names both counts** — the one the run was scored at and the one the
  verdicts are stated at.

Pure (b) was rejected for the verdicts. A report that prints *demonstrated
deficit* and adds a footnote saying the correction is out of date is a report
whose headline is wrong and whose correction is in the small print, and the
headline is the part that gets quoted. The correction can only ever widen, so
restating can only ever retract a claim — never manufacture one — which is the
one direction it is safe to move automatically.

Pure (a) was rejected for the record, for the reason above: a lab that
overwrites what it measured with what it now believes has no measurements left.

## What "re-derive" is allowed to touch

Only the correction-dependent fields: `adjusted_low`, `adjusted_high`, `looks`,
and the predicates and words computed off them — `verdict`,
`survives_correction`, `enough_evidence`, `claims`. The point estimate, the raw
95% interval, the standard error, the bet count and the cluster count are the
measurement and are copied through untouched.
`tests/test_no_report_states_a_stale_correction.py` pins that: a restated cell
whose measured fields moved is a re-measurement wearing a re-render's
clothes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from cbb_betting_lab import stats as S
from cbb_betting_lab.experiment_ledger import LEDGER_FILENAME
from cbb_betting_lab.experiment_ledger import load as load_ledger

#: Where a restated record records what its run was scored at. Present only
#: when a restatement actually moved the count, so a re-render against an
#: unchanged ledger is byte-identical to the original report.
RESTATED_FROM = "restated_from"

#: The centre of an interval, and the sample size beside it, in every spelling
#: this repository uses. `price_backtest` writes `roi`/`bets`, `forecast_skill`
#: writes `value`/`rows` for a Brier advantage and `estimate`/`rows` for a
#: fitted coefficient, and `fit_ratings` writes `mean`/`n` for a fitted bias.
#: One table rather than four copies of the same guess.
CELL_SHAPES: tuple[tuple[str, str], ...] = (
    ("roi", "bets"),
    ("value", "rows"),
    ("estimate", "rows"),
    ("mean", "n"),
)

#: Fields a restatement may rewrite. Everything else in a cell is the
#: measurement and is copied through. Listed rather than implied so the test
#: that pins it has something to read.
CORRECTION_DEPENDENT: frozenset[str] = frozenset(
    {
        "looks",
        "adjusted_low",
        "adjusted_high",
        "enough_evidence",
        "survives_correction",
        "verdict",
        "claims",
    }
)


@dataclass(frozen=True)
class Correction:
    """The correction the ledger owes right now, and where it was read from."""

    looks: int
    factor: float
    found: bool
    source: str

    def as_dict(self) -> dict:
        return {
            "looks": int(self.looks),
            "factor": float(self.factor),
            "found": bool(self.found),
            "source": str(self.source),
        }


def current(ledger_path: Path | str | None) -> Correction:
    """The ledger's cumulative count, or a correction of one that says so.

    An absent ledger returns `found=False` and `looks=1`, which applies no
    correction at all. That is the only safe *arithmetic* — inventing a family
    size would be worse — and it is emphatically not safe to print without
    saying so, which is why `found` travels beside it. It is
    `price_backtest.ledger_was_read`'s rule, in the one place the correction is
    now read from.
    """
    if ledger_path is None:
        return Correction(looks=1, factor=1.0, found=False, source="")
    path = Path(ledger_path)
    if not path.is_file():
        return Correction(looks=1, factor=1.0, found=False, source=str(path))
    looks = max(load_ledger(path).count, 1)
    return Correction(
        looks=looks, factor=S.bonferroni_factor(looks), found=True, source=str(path)
    )


def ledger_path(output_dir: Path | str) -> Path:
    return Path(output_dir) / LEDGER_FILENAME


def widened(record_looks: int, correction: Correction) -> int:
    """The family size a report may state: never smaller than it was measured at.

    **A restatement is one-directional.** The correction may only ever get
    stricter, so re-rendering takes the LARGER of the ledger's count and the
    count the run was scored at, and a ledger the renderer cannot find leaves
    the record's own correction in force.

    Without this, a missing ledger would be the most dangerous input in the
    system rather than the loudest: :func:`current` reports one look for an
    absent file, one look applies no correction at all, and a report re-rendered
    beside a ledger that was not there would restate every interval **narrower**
    than the run itself had already published it — turning three demonstrated
    deficits back into an unqualified reading and doing it silently, on the
    cheapest operation in the repository. An absent ledger is an unknown family,
    never an empty one; the widest correction anybody has actually justified for
    these numbers is the one the record carries, so that is the floor.
    """
    return max(int(record_looks or 1), int(correction.looks or 1))


def shape_of(cell: Mapping) -> tuple[str, str] | None:
    """`(centre key, sample-size key)` for a cell, or None if it is not one."""
    for centre, size in CELL_SHAPES:
        if centre in cell:
            return centre, size
    return None


def is_interval_cell(obj: Any) -> bool:
    """Whether a mapping is a stored interval this module knows how to restate.

    It must carry a standard error — without one there is nothing to widen and
    `RoiInterval` returns the raw bounds — plus the raw bounds it was written
    with and a centre. Anything else is left alone.
    """
    if not isinstance(obj, Mapping):
        return False
    if "standard_error" not in obj or "adjusted_low" not in obj:
        return False
    if "low" not in obj or "high" not in obj:
        return False
    return shape_of(obj) is not None


def interval_of(cell: Mapping, *, looks: int) -> S.RoiInterval:
    """The stored cell as a `RoiInterval` under a family size of `looks`."""
    shape = shape_of(cell)
    if shape is None:
        raise ValueError(
            f"{sorted(cell)} is not a stored interval: it carries none of "
            f"{[c for c, _ in CELL_SHAPES]} as its centre, so there is no "
            "estimate for a correction to be applied around."
        )
    centre, size = shape
    return S.RoiInterval(
        roi=float(cell.get(centre, 0.0) or 0.0),
        low=float(cell.get("low", 0.0) or 0.0),
        high=float(cell.get("high", 0.0) or 0.0),
        bets=int(cell.get(size, 0) or 0),
        clusters=int(cell.get("clusters", 0) or 0),
        standard_error=float(cell.get("standard_error", 0.0) or 0.0),
        looks=int(looks),
        cluster_unit=str(cell.get("cluster_unit") or "game"),
    )


def rebuild_cell(cell: Mapping, *, looks: int) -> dict:
    """One stored interval, restated at `looks`. The measurement is copied through.

    Only a field the cell already carries is rewritten: a record that never
    stored a `verdict` does not acquire one here, because a restatement must
    not add a claim to a row that was not making one.
    """
    interval = interval_of(cell, looks=looks)
    out = dict(cell)
    out["looks"] = int(looks)
    out["adjusted_low"] = float(interval.adjusted_low)
    out["adjusted_high"] = float(interval.adjusted_high)
    if "enough_evidence" in cell:
        out["enough_evidence"] = bool(interval.enough_evidence)
    if "survives_correction" in cell:
        out["survives_correction"] = bool(interval.survives_correction)
    if "claims" in cell:
        out["claims"] = bool(interval.survives_correction)
    if "verdict" in cell:
        out["verdict"] = interval.verdict()
    return out


def restate_tree(
    obj: Any,
    *,
    looks: int,
    rebuild: Callable[..., dict] | None = None,
) -> Any:
    """A deep copy of `obj` with every stored interval restated at `looks`.

    Recursive rather than a list of known paths: a report that grows a new
    table would otherwise keep rendering that one table at the old correction,
    and nothing would look wrong. `rebuild` lets a module intercept the cells
    whose derived words are its own — `forecast_skill`'s coefficients, whose
    `verdict` is refused for every term but one.
    """
    build = rebuild or rebuild_cell
    if isinstance(obj, Mapping):
        out = {k: restate_tree(v, looks=looks, rebuild=build) for k, v in obj.items()}
        if is_interval_cell(obj):
            return build(out, looks=looks)
        return out
    if isinstance(obj, list):
        return [restate_tree(v, looks=looks, rebuild=build) for v in obj]
    return obj


def stamp(record: Mapping, *, looks: int, record_name: str = "") -> dict:
    """Set the record's stated correction to `looks` and keep what it was run at.

    This is the (b) half. The stamp is written only when the count actually
    moved, so re-rendering against an unchanged ledger produces the same bytes
    it did before — which is what makes `--rebuild-report-only` safe to run
    reflexively.
    """
    out = dict(record)
    was = int(record.get("looks", 1) or 1)
    out["looks"] = int(looks)
    out["correction_factor"] = float(S.bonferroni_factor(int(looks)))
    if int(looks) != was:
        out[RESTATED_FROM] = {
            "looks": was,
            "factor": float(record.get("correction_factor", S.bonferroni_factor(was))),
            "generated_at": str(record.get("generated_at", "")),
            "record": str(record_name),
        }
    return out


def provenance_paragraph(record: Mapping) -> str:
    """The sentence a restated report prints under its family-correction line.

    Empty when nothing was restated, so an un-moved report gains no paragraph
    it did not have before.
    """
    was = record.get(RESTATED_FROM) or {}
    if not was:
        return ""
    name = str(was.get("record") or "the run record")
    return (
        f"**The verdicts below are stated at the ledger's count as of this "
        f"render, not the one this run was scored at.** The run itself was "
        f"scored at {int(was.get('looks', 1)):,} cumulative hypotheses "
        f"(x{float(was.get('factor', 1.0)):.4f}), and `{name}` still records "
        f"that — it is the measurement and it does not move. Every corrected "
        f"interval and every verdict below is re-derived from that run's own "
        f"point estimates and standard errors at "
        f"{int(record.get('looks', 1)):,} hypotheses "
        f"(x{float(record.get('correction_factor', 1.0)):.4f}), the ledger's "
        f"cumulative count at render time. Nothing was re-measured to do it, "
        f"and a wider correction can only ever retract a claim — never make "
        f"one."
    )


def restated(
    record: Mapping,
    *,
    looks: int,
    record_name: str = "",
    rebuild: Callable[..., dict] | None = None,
) -> dict:
    """The generic restatement: every stored interval, plus the provenance stamp.

    A report whose derived quantities are only its cells needs nothing more
    than this. `replication` and `forecast_skill` wrap it, because a state and
    a bucket comparison are derived from several cells at once and have to be
    re-judged after the cells move.
    """
    moved = restate_tree(record, looks=looks, rebuild=rebuild)
    return stamp(moved, looks=looks, record_name=record_name)
