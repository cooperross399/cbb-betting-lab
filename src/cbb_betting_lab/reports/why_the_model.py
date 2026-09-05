"""`data/outputs/cbb_why_the_model.md` — the edge question, rendered from records.

`docs/why_the_model_does_or_does_not_have_an_edge.md` said on its own third
line, *"Generated from `data/outputs/cbb_price_backtest.json`. Every figure is
read from that record rather than typed, so this cannot drift from the
measurement."* **No generator existed.** Every figure in it had been typed by
hand, and the sentence promising otherwise is exactly the sentence that stops a
reader checking. This module is the generator that sentence claimed.

## What it reads, and what it refuses

Three records, all three required:

* `data/outputs/cbb_price_backtest.json` — the returns, per market-and-tier
  cell, and the blind baselines they are compared against;
* `data/outputs/cbb_forecast_skill.json` — Brier against the market and the
  claimed-edge buckets;
* the replication record a held-out run writes, resolved through
  :func:`what_we_can_claim.replication_path` so the `data/outputs/holdout/`
  copy is found rather than reported missing.

**A missing record raises :class:`WhyError` rather than rendering the document
without it.** That is the whole point of the file: a document about whether a
model has an edge, rendered with one of its three instruments silently absent,
reads as a complete answer and is not one. `what_we_can_claim` may report *"no
held-out test has been run"* because reporting the state of the evidence is its
job; this document's job is to weigh the evidence, and it cannot weigh what it
does not have.

## The vocabulary is not restated here, it is imported

Every verdict string comes from :meth:`stats.RoiInterval.verdict` — the one
place in this repository that reads the sign — so an interval spanning zero
reads :data:`stats.NO_DEMONSTRATED_EDGE` and nothing softer, and only an
interval excluding zero **after the family-wise correction** is ever called a
demonstrated edge or a demonstrated deficit. A second copy of a phrase drifts,
and the direction it drifts in is never the conservative one.

Three more rules this module enforces mechanically:

1. **Every measured number carries its sample size**, and a cell below
   `stats.MINIMUM_BETS` prints the phrase and no number at all.
2. **The headline is per tier and never pooled.** High-major, mid-major and
   low-major are three distributions. :func:`headline` reads
   ``record["tiers"]`` and cannot reach the pooled figure, which lives in its
   own section under `price_backtest.POOLED_CAVEAT`. The document this replaced
   put the pooled row in the same table as the three tiers, one line below a
   sentence saying it never would.
3. **The title reads the sign.** The file is named *does or does not*; the
   heading is derived from how many tiers show a demonstrated edge, so a
   document titled *"does not have an edge"* cannot survive a measurement that
   found one.

## Corrected with today's family size, not the backtest's

The stored `adjusted_low`/`adjusted_high` were computed with whatever the
experiment ledger held when the backtest ran. Every interval here is rebuilt
from the stored point estimate and standard error with the **current**
cumulative hypothesis count, the same rule `what_we_can_claim` follows, so a
December correction can never be quoted in March. It can only ever get wider.

An absent ledger applies no correction **and says so**, which is a different and
much more alarming claim than a correction that was applied and changed nothing.

## Pure over a run record

:func:`build_record` reads disk; :func:`render` reads only the record. Improving
a sentence must never cost a re-run of the measurement, and a report that can
only be produced by re-running the measurement is a report nobody improves.
:func:`stale_inputs` re-asks the disk the three questions the record wrote down
about every file it opened — which path, was it there, what did it stamp itself
with — so a record that has fallen behind the evidence says so instead of
rendering confident prose about files it never read.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import Competition
from cbb_betting_lab.config import REPO_ROOT
from cbb_betting_lab.conferences import Tier
from cbb_betting_lab.reports import forecast_skill as FS
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.reports import what_we_can_claim as WC

#: Bumped whenever the record's shape changes, so a stale record fails loudly at
#: re-render rather than rendering a report with holes in it. Same discipline as
#: `price_backtest.RECORD_VERSION`, and for the same reason.
RECORD_VERSION = 1

#: `data/outputs/cbb_why_the_model.{json,md}`.
REPORT_STEM = "why_the_model"

#: The hand-written document whose fenced block this report is spliced into.
#: Named here so the script, the weekly loop and the test all resolve one path.
DOC_RELATIVE = "docs/why_the_model_does_or_does_not_have_an_edge.md"

#: The markers that fence the generated block inside that document.
BEGIN_MARKER = "<!-- BEGIN GENERATED: why_the_model -->"
END_MARKER = "<!-- END GENERATED -->"

#: How many blind baselines the document names. They are the worst by return,
#: among those clearing `stats.MINIMUM_BETS`; a blind side below the floor is
#: not printed with a number, for the same reason a model cell is not.
BLIND_BASELINES_SHOWN = 5

#: A claim an earlier, hand-typed version of this document made, kept so the
#: retraction survives beside the correction: the reason a claim was withdrawn
#: is evidence about the claim, and deleting the retraction leaves only the
#: correction.
#:
#: **It carries no figure.** The note that used to sit below the generated
#: fence hand-typed the tier's CURRENT return and interval into a paragraph
#: headed *historical*, which is the exact drift this whole cluster exists to
#: prevent — and it carried the superseded run's return with no sample size
#: beside it, from a record that no longer exists on disk to be re-read. What
#: is kept here is the retracted WORDING and the day it was recorded, both
#: historical by construction; every number in the rendered retraction is read
#: from today's record by :func:`_retraction_lines`, including whether the
#: claim still stands.
SUPERSEDED_CLAIM: dict[str, str] = {
    "recorded_on": "2026-09-04",
    "tier": Tier.LOW_MAJOR.value,
    "wording": (
        "the only tier whose interval excludes zero, and it excludes zero on "
        "the losing side"
    ),
    "verdict_claimed": S.DEMONSTRATED_DEFICIT,
    "population": (
        "the core team markets alone, before the alternate ladders and the "
        "halves entered the population"
    ),
}

#: Tier order, strongest first — the same order as the backtest report and
#: `what_we_can_claim`, so a reader moving between the three is not re-orienting.
TIER_ORDER: tuple[str, ...] = (
    Tier.HIGH_MAJOR.value,
    Tier.MID_MAJOR.value,
    Tier.LOW_MAJOR.value,
    Tier.UNPLACED.value,
)


class WhyError(RuntimeError):
    """A record this document needs is absent, unreadable, or the wrong shape.

    Raised rather than rendering around the hole. A document that weighs three
    instruments and silently weighs two still reads like an answer.
    """


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def record_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPORT_STEM, ".json")


def report_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPORT_STEM, ".md")


def doc_path() -> Path:
    """The hand-written document, resolved from the repository root."""
    return Path(REPO_ROOT) / DOC_RELATIVE


def evidence_paths(competition: Competition, output_dir: Path) -> dict[str, Path]:
    """The three records this document is a function of, by label.

    Each is built by calling the module that writes it, never by re-spelling a
    filename here: a second literal is how a reader and a writer drift apart,
    and `what_we_can_claim` has the scar — it looked in `data/outputs/` alone
    and reported a committed holdout replication as *"no held-out test has been
    run"* for as long as that record existed.
    """
    outputs = Path(output_dir)
    return {
        "price backtest": PB.record_path(competition, outputs),
        "forecast skill": FS.record_path(competition, outputs),
        "held-out replication": WC.replication_path(competition, outputs),
    }


# ---------------------------------------------------------------------------
# Reading, defensively
# ---------------------------------------------------------------------------


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _as_float(value: object) -> float | None:
    """A float, or None. A non-finite bound is None, never an infinity and
    never a zero: a zero-width interval around a positive return reads as a
    finding, and `-inf%` renders as nonsense."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _as_int(value: object) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _repo_relative(path: Path) -> str:
    target = Path(path)
    try:
        return str(target.resolve().relative_to(Path(REPO_ROOT).resolve()))
    except ValueError:
        return str(target)


def _absolute(stored: str) -> Path:
    target = Path(stored)
    return target if target.is_absolute() else Path(REPO_ROOT) / target


def _moment(stamp: str) -> datetime | None:
    text = _text(stamp)
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def read_evidence(label: str, path: Path) -> dict:
    """One required record, or :class:`WhyError` naming what is missing.

    The three failures are reported apart — absent, unreadable, not an object —
    because *"the instrument is not there"*, *"the instrument is broken"* and
    *"that file is not the instrument"* call for three different responses and
    a single message invites the wrong one.
    """
    target = Path(path)
    if not target.is_file():
        raise WhyError(
            f"The {label} record is not on disk at `{_repo_relative(target)}`. "
            "This document weighs three measurements and refuses to render "
            "with one of them missing: a page that weighs two and reads like "
            "an answer is worse than no page. Run the measurement that writes "
            "it, then re-render."
        )
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WhyError(
            f"The {label} record at `{_repo_relative(target)}` could not be "
            f"read ({type(exc).__name__}). Refusing to render a partial "
            "document over a good one."
        ) from exc
    if not isinstance(payload, dict):
        raise WhyError(
            f"The {label} record at `{_repo_relative(target)}` is not a JSON "
            "object, so it is not the record this document names."
        )
    return payload


def _require(payload: Mapping, key: str, *, label: str, path: Path) -> object:
    if key not in payload:
        raise WhyError(
            f"The {label} record at `{_repo_relative(path)}` carries no "
            f"`{key}`, so this document cannot say what it was written to say "
            "about it. Refusing to render the section empty: an empty section "
            "reads as a null result, and a null result is a claim."
        )
    return payload[key]


def _evidence_input(label: str, path: Path) -> dict:
    """One evidence file as this run found it: which path, present, stamped when.

    `generated_at` is read from the file's own contents, never from its
    modification time: a fresh `git clone` stamps every file with the moment of
    the clone, and a freshness check that calls every record in CI stale is a
    check somebody eventually silences.
    """
    target = Path(path)
    stamp = ""
    if target.is_file():
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            payload = {}
        if isinstance(payload, dict):
            stamp = _text(payload.get("generated_at"))
    return {
        "label": label,
        "path": _repo_relative(target),
        "found": target.is_file(),
        "generated_at": stamp,
    }


def stale_inputs(record: Mapping) -> list[str]:
    """Every reason this record is no longer about the evidence it names.

    Empty means the record is still true of the disk. Purity buys one guarantee
    — the markdown always matches its record — and it was once read as buying a
    second one it does not: `what_we_can_claim`'s `--check` passed while the
    document it checked named a committed backtest of 118,050 graded bets as
    *not found*, because the comparison was against the record and the record
    was a day older than the measurement. Internally consistent, externally
    false. So this asks the disk.
    """
    written_at = _text(record.get("generated_at")) or "an unrecorded time"
    written = _moment(record.get("generated_at"))
    inputs = record.get("evidence_inputs")
    if not isinstance(inputs, Sequence) or isinstance(inputs, (str, bytes)) or not inputs:
        return [
            "This record does not write down which evidence files it read, so "
            "nothing can tell whether it is older than they are. It was "
            f"written at {written_at}. Re-render it with "
            "`scripts/run_why_the_model.py`."
        ]
    reasons: list[str] = []
    for item in inputs:
        if not isinstance(item, Mapping):
            continue
        stored = _text(item.get("path"))
        if not stored:
            continue
        label = _text(item.get("label")) or stored
        target = _absolute(stored)
        found_then = bool(item.get("found"))
        found_now = target.is_file()
        stamped_then = _text(item.get("generated_at")) or "an unrecorded time"
        stamped_now = _evidence_input(label, target)["generated_at"]

        if found_now and not found_then:
            reasons.append(
                f"{label}: `{stored}` was ABSENT when this record was written "
                f"at {written_at} and is on disk now, generated at "
                f"{stamped_now or 'an unrecorded time'}."
            )
            continue
        if found_then and not found_now:
            reasons.append(
                f"{label}: `{stored}` was read when this record was written at "
                f"{written_at}, stamped {stamped_then}, and is not on disk now. "
                "This document is quoting a measurement that no longer exists."
            )
            continue
        if not found_now:
            continue
        if stamped_now and stamped_now != stamped_then:
            reasons.append(
                f"{label}: `{stored}` was generated at {stamped_now}; this "
                f"record read the version generated at {stamped_then} and was "
                f"itself written at {written_at}."
            )
            continue
        moment = _moment(stamped_now)
        if moment is not None and written is not None and moment > written:
            reasons.append(
                f"{label}: `{stored}` was generated at {stamped_now}, which is "
                f"after this record was written at {written_at}. A document "
                "cannot have read evidence that did not exist yet."
            )
    return reasons


# ---------------------------------------------------------------------------
# Cells
# ---------------------------------------------------------------------------


def interval_from_row(row: Mapping, *, looks: int) -> S.RoiInterval:
    """Rebuild a stored cell's interval under **today's** family size."""
    return S.RoiInterval(
        roi=_as_float(row.get("roi")) or 0.0,
        low=_as_float(row.get("low")) or 0.0,
        high=_as_float(row.get("high")) or 0.0,
        bets=_as_int(row.get("bets")),
        clusters=_as_int(row.get("clusters")),
        standard_error=_as_float(row.get("standard_error")) or 0.0,
        looks=looks,
        cluster_unit=_text(row.get("cluster_unit")) or "game",
    )


#: The bound-key pairs a row of this record can carry, as ``(low, high)``.
#:
#: **This is the record's whole bound vocabulary, not a filter over it.**
#: :func:`cell` and :func:`_advantage` are the only two constructors that
#: produce a row this document prints, and both write all four of these keys;
#: nothing else in the record names a bound.
#: ``test_the_bound_keys_this_guard_knows_about_are_the_ones_the_record_writes``
#: derives the expected set from what those constructors actually emit, so
#: dropping a pair from this tuple — the one-line way to narrow the check in
#: :func:`verdict_disagreements` — turns that test red instead of quietly
#: exempting every row that carries only the dropped pair.
INTERVAL_BOUND_KEYS: tuple[tuple[str, str], ...] = (
    ("adjusted_low", "adjusted_high"),
    ("low", "high"),
)

#: The bounds :func:`printed_interval` reads when it is not told otherwise:
#: the corrected pair, which is the pair `_figure` prints.
PRINTED_BOUNDS: tuple[str, str] = INTERVAL_BOUND_KEYS[0]


def printed_interval(
    row: Mapping, *, bounds: tuple[str, str] = PRINTED_BOUNDS
) -> S.RoiInterval:
    """The interval this document is about to PRINT, as a `RoiInterval`.

    The corrected bounds are handed in as the interval's own bounds and the
    correction is then switched off (``looks=1``), so
    :meth:`stats.RoiInterval.verdict` reads exactly the two numbers a reader
    sees beside the return — not a wider or narrower pair recomputed from a
    standard error the reader is never shown. `verdict()` reads the sign off
    that pair, so a bound pair below zero is a demonstrated **deficit** whatever
    return the record carries beside it; and
    :func:`verdict_disagreements` refuses a row whose return does not lie
    between them at all, so the sentence and the figure can never be published
    contradicting each other.

    Constructed rather than re-implemented. A second copy of *"which side of
    zero is this on"* is a copy that drifts, and the direction it drifts in is
    never the conservative one; `stats` owns that question for the whole
    repository and this asks it there.

    A row from the forecast section names its return `value` and its sample
    `rows`; a backtest cell names them `roi` and `bets`. Both are accepted so
    that one derivation covers every verdict this document prints.

    `bounds` names which of :data:`INTERVAL_BOUND_KEYS` to read. It defaults to
    the corrected pair — the pair on the page — and is moved only by
    :func:`verdict_disagreements`, which checks the uncorrected pair too so
    that a row cannot escape the coherence check by carrying its stale numbers
    under the other two names.

    **A bound the row does not carry reads 0.0, and that is a lie the caller
    must not be allowed to publish**: a row with `adjusted_low=+0.02` and no
    `adjusted_high` becomes the interval `[+0.02, 0.0]`, which excludes zero
    above and reads *demonstrated edge* over an arbitrary return. That is why
    :func:`verdict_disagreements` refuses a half-carried pair outright rather
    than reasoning about the interval it fabricates.
    """
    low_key, high_key = bounds
    roi = _as_float(row.get("roi"))
    if roi is None:
        roi = _as_float(row.get("value"))
    bets = _as_int(row.get("bets")) or _as_int(row.get("rows"))
    return S.RoiInterval(
        roi=roi or 0.0,
        low=_as_float(row.get(low_key)) or 0.0,
        high=_as_float(row.get(high_key)) or 0.0,
        bets=bets,
        clusters=_as_int(row.get("clusters")),
        standard_error=0.0,
        looks=1,
        cluster_unit=_text(row.get("cluster_unit")) or "game",
    )


def verdict_of(row: Mapping) -> str:
    """The verdict of the interval in `row`, **derived, never read**.

    The renderer calls this everywhere it used to read ``row["verdict"]``.
    Setting a row's stored verdict to `"a demonstrated edge"` in the record on
    disk once made the published document say so; a document whose whole job is
    to stop a number being misread must not take the reading on trust from the
    file it is reading.
    """
    return printed_interval(row).verdict()


def enough_evidence_of(row: Mapping) -> bool:
    """Whether `row`'s own sample size clears the floor declared in advance.

    Derived from the count, not from the stored flag, for the same reason: a
    hand-set ``enough_evidence: true`` on a 40-bet row would otherwise promote
    it into the headline's population.
    """
    return printed_interval(row).enough_evidence


def _rows_of_the_record(record: Mapping) -> list[tuple[str, Mapping]]:
    """Every row in the record that carries a figure, as `(label, row)` pairs.

    Used only to REFUSE a record that disagrees with itself — the rendering
    itself never reads a stored verdict.

    **This walk is the population :func:`verdict_disagreements` checks, and it
    is checked in turn.**
    ``test_every_row_of_the_record_that_carries_a_figure_is_walked`` descends
    the whole record looking for any mapping that carries a bound key or a
    verdict, and asserts that every one of them comes back from here — by
    identity, so a section this walk does not reach is a red test rather than a
    silently unchecked corner. Deleting `"blind"` from the tuple below, or
    adding a section to the record and not adding it here, fails that test.
    """
    found: list[tuple[str, Mapping]] = []
    for key in ("tiers", "cells", "pooled", "blind"):
        for index, row in enumerate(record.get(key, []) or []):
            if isinstance(row, Mapping):
                found.append((f"{key}[{index}] {_text(row.get('name'))}".strip(), row))
    every_market = record.get("every_market")
    if isinstance(every_market, Mapping):
        found.append(("every_market", every_market))
    forecast = record.get("forecast")
    if isinstance(forecast, Mapping):
        blocks: list[tuple[str, object]] = [("forecast.pooled", forecast.get("pooled"))]
        for index, tier in enumerate(forecast.get("tiers", []) or []):
            blocks.append((f"forecast.tiers[{index}]", tier))
        for label, block in blocks:
            if not isinstance(block, Mapping):
                continue
            advantage = block.get("advantage_over_raw")
            if isinstance(advantage, Mapping):
                found.append((f"{label}.advantage_over_raw", advantage))
    return found


#: The keys by which a row announces it is making a claim a reader will act
#: on: a return that gets printed, or a verdict beside it. A row carrying one
#: of these and no interval at all is refused rather than examined — see
#: :func:`verdict_disagreements`.
CLAIM_KEYS: tuple[str, ...] = ("roi", "value", "verdict")


def _bound_pairs_carried(
    row: Mapping,
) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """`(whole, half)` — the bound pairs this row carries, and the maimed ones.

    A pair is *half* carried when one of its two keys is present and the other
    is not. That is not a lesser version of an interval; it is a row that will
    be read as an interval with a fabricated 0.0 on the missing side.
    """
    whole: list[tuple[str, str]] = []
    half: list[tuple[str, str]] = []
    for pair in INTERVAL_BOUND_KEYS:
        present = [key for key in pair if key in row]
        if len(present) == 2:
            whole.append(pair)
        elif present:
            half.append(pair)
    return whole, half


def verdict_disagreements(record: Mapping) -> list[str]:
    """Every row that disagrees with itself, in any of the four ways.

    **Every row of the record is examined. There is no opt-in.** This check
    used to run over `_rows_carrying_an_interval(record)` — the rows carrying
    *both* of `adjusted_low` and `adjusted_high` — which made carrying the keys
    the condition for being checked, so the way past the check was to not carry
    them. Deleting one key from one row of the committed record published

        high-major 24,691 bets, **+99.0%**, corrected +2.0% to unbounded —
        demonstrated edge

    in the headline of a document whose entire subject is whether that
    sentence may be said: `[+0.02, missing]` is read as `[+0.02, 0.0]`, which
    excludes zero above, and the return beside it was never compared to
    anything. Rows are now taken from :func:`_rows_of_the_record` whole and
    each is classified by the bound keys it actually carries.

    The four refusals:

    1. **A half-carried bound pair.** `adjusted_low` without `adjusted_high`
       (or the reverse) is the defeat above. There is no interval to read, and
       the one that gets fabricated in its place is the flattering one.
    2. **A claim with no interval at all.** A row carrying a return or a
       verdict and no bound of either pair prints `**+99.0%**, corrected
       unbounded to unbounded` — a figure with nothing qualifying it, which is
       the typed-figure defect this whole document exists to prevent. Refused
       rather than passed through.
    3. **The return is not inside its own interval.** No estimator produces
       that row — the interval is built around the estimate — so it is a return
       typed over one measurement beside bounds left from another. `_figure`
       prints both on one line, so a `+5.0%` beside corrected bounds of −9% to
       −2% would put the words *demonstrated deficit* next to a positive
       number. Checked against **both** pairs the row carries, so stale numbers
       cannot hide under `low`/`high` while `adjusted_low`/`adjusted_high` are
       kept coherent.
    4. **The stored verdict, or `enough_evidence`, is not the reading of its
       own interval**, which is a record edited by hand between the
       measurement and the document.

    Empty means the record agrees with itself. :func:`render` refuses a
    non-empty list rather than printing either reading: printing the stored one
    publishes the edit, and printing the derived one silently overwrites a
    disagreement a human should see.
    """
    reasons: list[str] = []
    for label, row in _rows_of_the_record(record):
        whole, half = _bound_pairs_carried(row)
        claims = [key for key in CLAIM_KEYS if key in row]

        for low_key, high_key in half:
            carried, missing = (
                (low_key, high_key) if low_key in row else (high_key, low_key)
            )
            reasons.append(
                f"{label}: carries `{carried}` and no `{missing}`. Half an "
                "interval is not an interval — the missing bound is read as "
                "0.0, which is a bound no measurement produced and the one "
                "that most easily excludes zero."
            )

        if claims and not whole and not half:
            reasons.append(
                f"{label}: carries {', '.join(f'`{key}`' for key in claims)} "
                "and no interval of any kind. A return printed with no bounds "
                "beside it, or a verdict with no interval to be a statement "
                "about, is a figure with nothing qualifying it."
            )

        for pair in whole:
            interval = printed_interval(row, bounds=pair)
            if not interval.enough_evidence:
                # Below the floor `_figure` prints the phrase and no number at
                # all, so there is no pair on the page to disagree.
                continue
            if not interval.return_sits_inside_its_own_interval:
                reasons.append(
                    f"{label}: the return {_pct(interval.roi)} does not lie "
                    f"between the bounds "
                    f"[{_as_float(row.get(pair[0]))}, "
                    f"{_as_float(row.get(pair[1]))}] it carries under "
                    f"`{pair[0]}`/`{pair[1]}`, so the two numbers on that line "
                    "did not come from one measurement — and those bounds read "
                    f"{interval.verdict()!r}."
                )

        if "verdict" in row:
            stored = _text(row.get("verdict"))
            derived = verdict_of(row)
            if stored != derived:
                reasons.append(
                    f"{label}: the record stores the verdict {stored!r}, and "
                    f"the corrected interval it is printed beside "
                    f"[{_as_float(row.get('adjusted_low'))}, "
                    f"{_as_float(row.get('adjusted_high'))}] over "
                    f"{printed_interval(row).bets:,} reads {derived!r}."
                )
        if "enough_evidence" in row:
            stored_enough = bool(row.get("enough_evidence"))
            derived_enough = enough_evidence_of(row)
            if stored_enough != derived_enough:
                reasons.append(
                    f"{label}: the record stores enough_evidence="
                    f"{stored_enough} and its sample of "
                    f"{printed_interval(row).bets:,} against the "
                    f"{S.MINIMUM_BETS:,} declared in advance says "
                    f"{derived_enough}."
                )
    return reasons


def cell(row: Mapping, *, looks: int, name: str = "") -> dict:
    """One measured cell as plain data, with its verdict already read.

    **The sign is read here, once, by `stats.RoiInterval.verdict()`.** Nothing
    downstream re-derives *"is this an edge"* — that re-derivation is the NHL
    lab's defect 3, where a headline tested measured-survives-correction-and-
    replicated and never looked at which side of zero the number sat on.
    """
    interval = interval_from_row(row, looks=looks)
    return {
        "name": name or _text(row.get("name")) or _text(row.get("market")),
        "market": _text(row.get("market")),
        "tier": _text(row.get("tier")),
        "bets": interval.bets,
        "clusters": interval.clusters,
        "cluster_unit": interval.cluster_unit,
        "roi": _as_float(interval.roi),
        "low": _as_float(interval.low),
        "high": _as_float(interval.high),
        "adjusted_low": _as_float(interval.adjusted_low),
        "adjusted_high": _as_float(interval.adjusted_high),
        "looks": int(interval.looks),
        "enough_evidence": bool(interval.enough_evidence),
        "verdict": interval.verdict(),
    }


def _rows(payload: Mapping, key: str, *, label: str, path: Path) -> list[dict]:
    value = _require(payload, key, label=label, path=path)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise WhyError(
            f"The {label} record at `{_repo_relative(path)}` carries a `{key}` "
            "that is not a list of cells."
        )
    return [dict(row) for row in value if isinstance(row, Mapping)]


def demonstrated_edges(cells: Sequence[Mapping]) -> list[dict]:
    """Cells whose corrected interval excludes zero **above** it.

    The predicate is :func:`verdict_of`, which reads the interval, and never
    the stored ``verdict`` string: a record edited to say `"a demonstrated
    edge"` must not be able to put a cell in this list.
    """
    return [c for c in cells if verdict_of(c) == S.DEMONSTRATED_EDGE]


def demonstrated_deficits(cells: Sequence[Mapping]) -> list[dict]:
    """Cells whose corrected interval excludes zero **below** it.

    A separate function returning a disjoint list, never a flag on the first
    one: the two are different findings and the sibling lab merged them.
    """
    return [c for c in cells if verdict_of(c) == S.DEMONSTRATED_DEFICIT]


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------


def build_record(
    *,
    competition: Competition,
    output_dir: Path,
) -> dict:
    """Read the three records and write down every number this document uses.

    Reads disk. :func:`render` does not.
    """
    outputs = Path(output_dir)
    paths = evidence_paths(competition, outputs)
    backtest = read_evidence("price backtest", paths["price backtest"])
    forecast = read_evidence("forecast skill", paths["forecast skill"])
    replication = read_evidence("held-out replication", paths["held-out replication"])

    correction = WC.correction_from_ledger(WC.experiment_ledger_path(outputs))
    looks = correction.looks

    backtest_path = paths["price backtest"]
    tier_rows = _rows(backtest, "by_tier", label="price backtest", path=backtest_path)
    cell_rows = _rows(
        backtest, "by_market_and_tier", label="price backtest", path=backtest_path
    )
    pooled_rows = _rows(backtest, "pooled", label="price backtest", path=backtest_path)
    blind_rows = _rows(
        backtest, "null_baseline", label="price backtest", path=backtest_path
    )

    tiers = [cell(row, looks=looks) for row in tier_rows]
    tiers.sort(key=lambda c: _tier_rank(_text(c.get("tier"))))
    cells = [cell(row, looks=looks) for row in cell_rows]
    pooled = [cell(row, looks=looks) for row in pooled_rows]
    every_market = next(
        (p for p in pooled if not _text(p.get("market"))),
        None,
    )

    blind = [
        cell(row, looks=looks)
        for row in blind_rows
        if _as_int(row.get("bets")) >= S.MINIMUM_BETS
    ]
    blind.sort(key=lambda c: (c.get("roi") if c.get("roi") is not None else 0.0))

    record = {
        "record_version": RECORD_VERSION,
        "competition": competition.key,
        "title": competition.title,
        "generated_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat(),
        "evidence_inputs": [
            _evidence_input(label, path) for label, path in paths.items()
        ],
        "correction": correction.as_dict(),
        "backtest": {
            "generated_at": _text(backtest.get("generated_at")),
            "record_version": _as_int(backtest.get("record_version")),
            "season_label": _text(backtest.get("season_label")),
            "snapshot_phase": _text(backtest.get("snapshot_phase")),
            "edge_threshold": _as_float(backtest.get("edge_threshold")),
            "minimum_bets": _as_int(backtest.get("minimum_bets")) or S.MINIMUM_BETS,
            "bets_graded": _as_int(backtest.get("bets_graded")),
            "games": _as_int(backtest.get("games")),
            "days": _as_int(backtest.get("days")),
            "cells": len(cells),
            "half_point": _half_point(backtest),
            "calibration": _calibration(backtest),
        },
        "tiers": tiers,
        "cells": cells,
        "pooled": pooled,
        "every_market": every_market,
        "blind": blind[:BLIND_BASELINES_SHOWN],
        "forecast": _forecast_section(forecast, paths["forecast skill"], looks=looks),
        "replication": _replication_section(
            replication, paths["held-out replication"]
        ),
    }
    return record


#: The one field of the record that is allowed to differ between two builds of
#: the same evidence: the moment the build happened. Everything else is a
#: function of the three measurement records and the experiment ledger, so a
#: difference anywhere else is a difference somebody made by hand.
VOLATILE_RECORD_FIELDS: tuple[str, ...] = ("generated_at",)


def rederivation_differences(
    record: Mapping,
    *,
    competition: Competition,
    output_dir: Path,
) -> list[str]:
    """Every field of `record` that a fresh build from the evidence disagrees with.

    **The intermediate record must not be the only source of truth.** The
    document is a pure function of this record, and `--check` compared the two
    of them — so a fabricated figure hand-typed into
    `data/outputs/cbb_why_the_model.json` produced a published document saying
    it, with a green suite: the record and the document agreed with each other,
    and nothing re-asked the measurement.

    This re-derives the record from the three measurement records and the
    experiment ledger and returns what differs. Empty means the record really
    is what those files say. It raises the same :class:`WhyError` as
    :func:`build_record` when one of them cannot be read — a comparison that
    cannot be made is never reported as a comparison that passed.
    """
    fresh = build_record(competition=competition, output_dir=output_dir)
    stored = {k: v for k, v in dict(record).items() if k not in VOLATILE_RECORD_FIELDS}
    derived = {k: v for k, v in fresh.items() if k not in VOLATILE_RECORD_FIELDS}
    reasons: list[str] = []
    for key in sorted(set(stored) | set(derived)):
        if key not in stored:
            reasons.append(
                f"`{key}`: the evidence on disk produces this section and the "
                "record does not carry it at all."
            )
            continue
        if key not in derived:
            reasons.append(
                f"`{key}`: the record carries this section and a fresh build "
                "from the evidence on disk produces no such section."
            )
            continue
        if stored[key] != derived[key]:
            reasons.append(
                f"`{key}`: the record says {_short(stored[key])} and the "
                f"evidence on disk says {_short(derived[key])}."
            )
    return reasons


def _short(value: object, limit: int = 240) -> str:
    """A value as one line, cut, so a diff message names a field and not a book."""
    text = json.dumps(value, sort_keys=True, default=str)
    return text if len(text) <= limit else text[:limit] + "…"


def _tier_rank(tier: str) -> tuple[int, str]:
    try:
        return (TIER_ORDER.index(tier), tier)
    except ValueError:
        return (len(TIER_ORDER), tier)


def _half_point(backtest: Mapping) -> dict:
    payload = backtest.get("half_point")
    payload = payload if isinstance(payload, Mapping) else {}
    convention = payload.get("convention")
    convention = convention if isinstance(convention, Mapping) else {}
    return {
        "verified": bool(payload.get("verified")),
        "checked": _as_int(convention.get("checked")),
        "agreed": _as_int(convention.get("agreed")),
        "rate": _as_float(convention.get("rate")),
    }


def _calibration(backtest: Mapping) -> dict:
    payload = backtest.get("calibration")
    payload = payload if isinstance(payload, Mapping) else {}

    def side(key: str) -> dict:
        block = payload.get(key)
        block = block if isinstance(block, Mapping) else {}
        return {
            "points": _as_float(block.get("points")),
            "rows": _as_int(block.get("n")),
            "buckets": _as_int(block.get("buckets")),
        }

    return {
        "overall": side("overall_overconfidence"),
        "selected": side("selected_overconfidence"),
    }


def _advantage(block: Mapping, *, looks: int) -> dict:
    """A Brier advantage over the market, re-corrected under today's looks.

    `forecast_skill` stores the value, the uncorrected bounds and the standard
    error; `stats.RoiInterval` is the one type that reads a sign, so the
    advantage is carried through it and its verdict string is the one the
    document prints. It is not a return, and the document says so where it
    prints it — but *"does this interval exclude zero after the correction"* is
    the same question and gets the same answer from the same code.
    """
    interval = S.RoiInterval(
        roi=_as_float(block.get("value")) or 0.0,
        low=_as_float(block.get("low")) or 0.0,
        high=_as_float(block.get("high")) or 0.0,
        bets=_as_int(block.get("rows")),
        clusters=_as_int(block.get("clusters")),
        standard_error=_as_float(block.get("standard_error")) or 0.0,
        looks=looks,
        cluster_unit=_text(block.get("cluster_unit")) or "day",
    )
    return {
        "name": _text(block.get("name")),
        "value": _as_float(interval.roi),
        "low": _as_float(interval.low),
        "high": _as_float(interval.high),
        "adjusted_low": _as_float(interval.adjusted_low),
        "adjusted_high": _as_float(interval.adjusted_high),
        "rows": interval.bets,
        "enough_evidence": bool(interval.enough_evidence),
        "verdict": interval.verdict(),
    }


def _forecast_tier(block: Mapping, *, looks: int) -> dict:
    brier = block.get("brier")
    brier = brier if isinstance(brier, Mapping) else {}
    anti = block.get("anti_predictive")
    anti = anti if isinstance(anti, Mapping) else {}
    lowest = anti.get("lowest_bucket")
    lowest = lowest if isinstance(lowest, Mapping) else {}
    highest = anti.get("highest_bucket")
    highest = highest if isinstance(highest, Mapping) else {}
    raw = brier.get("advantage_over_raw")
    raw = raw if isinstance(raw, Mapping) else {}
    return {
        "label": _text(block.get("label")),
        "rows": _as_int(block.get("rows")),
        "games": _as_int(block.get("games")),
        "model_brier": _as_float(brier.get("model")),
        "base_rate_brier": _as_float(brier.get("base_rate_reference")),
        "worse_than_the_base_rate": (
            (_as_float(brier.get("model")) or 0.0)
            > (_as_float(brier.get("base_rate_reference")) or 0.0)
        ),
        "loses_to_the_handicapped_market": bool(
            brier.get("loses_to_the_handicapped_market")
        ),
        "advantage_over_raw": _advantage(raw, looks=looks) if raw else {},
        "anti_predictive": {
            "measurable": bool(anti.get("measurable")),
            "usable_buckets": _as_int(anti.get("usable_buckets")),
            "widens_by": _as_float(anti.get("shortfall_widens_by")),
            "lowest_rows": _as_int(lowest.get("rows")),
            "highest_rows": _as_int(highest.get("rows")),
        },
    }


def _forecast_section(payload: Mapping, path: Path, *, looks: int) -> dict:
    pooled = _require(payload, "pooled", label="forecast skill", path=path)
    if not isinstance(pooled, Mapping):
        raise WhyError(
            f"The forecast skill record at `{_repo_relative(path)}` carries a "
            "`pooled` that is not an object."
        )
    tiers = _require(payload, "by_tier", label="forecast skill", path=path)
    if not isinstance(tiers, Sequence) or isinstance(tiers, (str, bytes)):
        raise WhyError(
            f"The forecast skill record at `{_repo_relative(path)}` carries a "
            "`by_tier` that is not a list."
        )
    rendered = [
        _forecast_tier(block, looks=looks) for block in tiers if isinstance(block, Mapping)
    ]
    rendered.sort(key=lambda t: _tier_rank(t["label"]))
    return {
        "generated_at": _text(payload.get("generated_at")),
        "record_version": _as_int(payload.get("record_version")),
        "source": _text(payload.get("source")),
        "season_label": _text(payload.get("season_label")),
        "devig_method": _text(payload.get("devig_method")),
        "pooled": _forecast_tier(pooled, looks=looks),
        "tiers": rendered,
    }


def _replication_section(payload: Mapping, path: Path) -> dict:
    counts = _require(payload, "counts", label="held-out replication", path=path)
    if not isinstance(counts, Mapping):
        raise WhyError(
            f"The held-out replication record at `{_repo_relative(path)}` "
            "carries a `counts` that is not an object."
        )
    markets = payload.get("markets")
    markets = markets if isinstance(markets, Sequence) and not isinstance(markets, (str, bytes)) else []
    holdout = payload.get("holdout")
    holdout = holdout if isinstance(holdout, Mapping) else {}
    discovery = payload.get("discovery")
    discovery = discovery if isinstance(discovery, Mapping) else {}
    return {
        "generated_at": _text(payload.get("generated_at")),
        "record_version": _as_int(payload.get("record_version")),
        "test_label": _text(payload.get("test_label")),
        "discovery_season_label": _text(payload.get("discovery_season_label")),
        "declared_in_advance": bool(payload.get("declared_in_advance")),
        "declared_on": _text(payload.get("declared_on")),
        "cells": len(markets),
        "counts": {str(k): _as_int(v) for k, v in counts.items()},
        "holdout_bets": _as_int(holdout.get("bets_graded")),
        "holdout_games": _as_int(holdout.get("games")),
        "discovery_bets": _as_int(discovery.get("bets_graded")),
    }


# ---------------------------------------------------------------------------
# Rendering — a pure function of the record
# ---------------------------------------------------------------------------


def _measured(record: Mapping, key: str) -> list[dict]:
    """The rows of `record[key]` that clear the floor declared in advance.

    A row below it has a phrase and no number, so it can be neither an edge nor
    a deficit and must not be counted as an absence of one either.
    """
    return [
        dict(row)
        for row in record.get(key, [])
        if isinstance(row, Mapping) and enough_evidence_of(row)
    ]


def _pct(value: object) -> str:
    number = _as_float(value)
    return "unbounded" if number is None else f"{number * 100:+.1f}%"


def _tier_label(tier: str) -> str:
    return (tier or Tier.UNPLACED.value).replace("_", "-")


def _bets(count: int) -> str:
    """`bet` or `bets`. A sample size of one is still a sample size."""
    return "bet" if count == 1 else "bets"


def _figure(claim: Mapping) -> str:
    """One cell as a sentence, **always with its sample size**.

    Below the floor there is no number at all, only the phrase the verdict
    already carries. A +12% return over 40 bets and a coin flip are the same
    claim at that sample size, and printing the +12% invites somebody to quote
    it out of the row that qualifies it.

    **The verdict is derived from the two bounds printed on this line**, by
    :func:`verdict_of`, and never read from the record. The renderer once
    printed ``claim["verdict"]``, so setting that string in the record on disk
    made the published document announce a demonstrated edge over an interval
    that spanned zero — the number and the sentence beside it disagreeing, with
    nothing in the pipeline to notice.
    """
    interval = printed_interval(claim)
    bets = interval.bets
    if not interval.enough_evidence:
        # No number at all. `RoiInterval.verdict()` already names the sample and
        # the floor it is below, so printing a count beside it would say the
        # same thing twice and printing the return would say it once too often.
        return interval.verdict()
    return (
        f"{bets:,} {_bets(bets)}, **{_pct(claim.get('roi', claim.get('value')))}**, "
        f"corrected {_pct(claim.get('adjusted_low'))} to "
        f"{_pct(claim.get('adjusted_high'))} — {interval.verdict()}"
    )


def headline(record: Mapping) -> str:
    """The answer, per tier, over the tiers and never over the pool.

    Reads ``record["tiers"]`` and cannot reach ``record["every_market"]``. The
    document this replaced printed the pooled Division I row in the same table
    as the three tiers, one line above a sentence saying it never would.
    """
    measured = _measured(record, "tiers")
    edges = demonstrated_edges(measured)
    deficits = demonstrated_deficits(measured)
    if not measured:
        return (
            "**No tier clears the sample floor declared in advance**, so there "
            "is no number to report in any of them."
        )
    spread = ", ".join(
        f"{_tier_label(_text(t.get('tier')))} {_as_int(t.get('bets')):,} "
        f"{_bets(_as_int(t.get('bets')))}"
        for t in measured
    )
    if edges:
        named = "; ".join(
            f"{_tier_label(_text(t.get('tier')))} {_figure(t)}" for t in edges
        )
        lead = (
            f"**{len(edges)} of {len(measured)} measured tiers shows a "
            f"demonstrated edge**: {named}."
        )
    else:
        lead = (
            f"**No demonstrated edge in any of the {len(measured)} measured "
            f"tiers** ({spread})."
        )
    if deficits:
        named = "; ".join(
            f"{_tier_label(_text(t.get('tier')))} {_figure(t)}" for t in deficits
        )
        lead += f" {len(deficits)} shows a demonstrated deficit: {named}."
    else:
        lead += " None shows a demonstrated deficit."
    return lead


def title(record: Mapping) -> str:
    """The heading, derived from the sign rather than typed above the numbers.

    A file named *does or does not* whose heading is hand-written says whichever
    of the two somebody last believed. This one cannot outlive the measurement.
    """
    measured = _measured(record, "tiers") + _measured(record, "cells")
    if demonstrated_edges(measured):
        return "# Where the model does have a demonstrated edge, and where it does not"
    return "# Why the model does not have a demonstrated edge"


def _tier_table(record: Mapping) -> list[str]:
    lines = ["| Tier | Result |", "|:---|:---|"]
    for claim in record.get("tiers", []):
        if not isinstance(claim, Mapping):
            continue
        lines.append(f"| {_tier_label(_text(claim.get('tier')))} | {_figure(claim)} |")
    return lines


def _cell_lines(record: Mapping) -> list[str]:
    """The finer cut, named rather than counted away.

    A tier is a pool of markets, and a finding inside one of them does not
    survive being averaged with the rest. Both counts are printed even when
    they are zero, because *"0 of 32 cells shows a demonstrated edge"* is the
    answer and an omitted line reads as an oversight.
    """
    backtest = record.get("backtest")
    backtest = backtest if isinstance(backtest, Mapping) else {}
    total = _as_int(backtest.get("cells"))
    measured = _measured(record, "cells")
    edges = demonstrated_edges(measured)
    deficits = demonstrated_deficits(measured)
    lines = [
        f"Cut finer, by market **and** tier: **{len(edges)} of {total:,} cells "
        f"shows a demonstrated edge** and **{len(deficits)} shows a "
        f"demonstrated deficit**, over the "
        f"{len(measured):,} that clear the floor declared in advance.",
        "",
    ]
    for row in edges + deficits:
        lines.append(
            f"- `{_text(row.get('market'))} / {_text(row.get('tier'))}`: "
            f"{_figure(row)}"
        )
    if edges or deficits:
        lines.append("")
    return lines


def _retraction_lines(record: Mapping) -> list[str]:
    """The retracted claim, and what the same tier reads **in today's record**.

    Generated, because the hand-written version of this note drifted exactly
    the way the document above it did: it was headed *"the figures in this
    section are historical"* and then hand-typed the tier's current return and
    corrected interval underneath, so a re-measurement moved the table and left
    the paragraph. Nothing here is typed but the retracted sentence and the day
    it was recorded, and whether the claim still stands is read off the sign
    rather than asserted.
    """
    tier_key = SUPERSEDED_CLAIM["tier"]
    label = _tier_label(tier_key)
    lines = [
        f"### A claim this document has retracted, recorded "
        f"{SUPERSEDED_CLAIM['recorded_on']}",
        "",
        f"Before this block was generated, this document said of **{label}** "
        f"that it was *“{SUPERSEDED_CLAIM['wording']}”* — a "
        f"{SUPERSEDED_CLAIM['verdict_claimed']}. That was measured on "
        f"{SUPERSEDED_CLAIM['population']}.",
        "",
    ]
    current = next(
        (
            row
            for row in record.get("tiers", [])
            if isinstance(row, Mapping) and _text(row.get("tier")) == tier_key
        ),
        None,
    )
    if current is None:
        lines.append(
            f"**Today's record carries no {label} row at all**, so this "
            "document cannot say whether that claim still holds. It is left "
            "standing as withdrawn rather than quietly re-asserted."
        )
        return lines
    now = verdict_of(current)
    if now == SUPERSEDED_CLAIM["verdict_claimed"]:
        lines.append(
            f"**It still holds.** On today's record {label} reads "
            f"{_figure(current)}."
        )
    else:
        lines.append(
            f"**It no longer holds.** On today's record {label} reads "
            f"{_figure(current)}."
        )
        lines += [
            "",
            "Nothing about the model changed. The population did: the markets "
            "added since are one season deep and thin, which widens every "
            "interval they enter. A finding that survives on the narrower "
            "population and dissolves when the wider one is measured was "
            "fragile to the population all along, and the earlier wording did "
            "not say so because at the time there was nothing to say it "
            "against.",
        ]
    return lines


def _worst_tier(record: Mapping) -> Mapping | None:
    measured = _measured(record, "tiers")
    if not measured:
        return None
    return min(measured, key=lambda t: _as_float(t.get("roi")) or 0.0)


def _provenance(record: Mapping) -> list[str]:
    lines = [
        "Every figure below is read from a record on disk by "
        "`scripts/run_why_the_model.py`, never typed. The records, and the "
        "moment each stamped itself with:",
        "",
    ]
    for item in record.get("evidence_inputs", []):
        if not isinstance(item, Mapping):
            continue
        stamp = _text(item.get("generated_at")) or "no `generated_at` of its own"
        lines.append(
            f"- **{_text(item.get('label'))}** — `{_text(item.get('path'))}`, "
            f"generated {stamp}"
        )
    return lines


def _correction_lines(record: Mapping) -> list[str]:
    correction = record.get("correction")
    correction = correction if isinstance(correction, Mapping) else {}
    if not correction.get("applied"):
        why = _text(correction.get("error"))
        detail = (
            f" It is on disk and could not be read: {why}"
            if why
            else " No experiment ledger was found."
        )
        return [
            "**No family-wise correction could be applied.**" + detail + " Every "
            "interval below is therefore uncorrected, and an uncorrected "
            "interval on a search that has run many times is wider than it "
            "looks. This document says so rather than quietly applying none.",
        ]
    return [
        f"Every interval is corrected for "
        f"{_as_int(correction.get('hypotheses')):,} cumulative distinct "
        f"hypotheses — the experiment ledger's count at render time, not the "
        f"count when the backtest ran — which widens each one by "
        f"x{_as_float(correction.get('factor')) or 1.0:.2f}. The correction can "
        "only ever get stricter as the search continues, which is the only "
        "direction it is allowed to move.",
    ]


def _blind_lines(record: Mapping) -> list[str]:
    blind = [b for b in record.get("blind", []) if isinstance(b, Mapping)]
    if not blind:
        return [
            "No blind side clears the "
            f"{S.MINIMUM_BETS:,}-bet floor declared in advance, so there is "
            "nothing to compare against and this section reports that rather "
            "than an empty table."
        ]
    lines = [
        f"The worst blind sides that clear the {S.MINIMUM_BETS:,}-bet floor "
        "declared in advance:",
        "",
    ]
    for row in blind:
        lines.append(
            f"- `{_text(row.get('tier'))} / {_text(row.get('market'))} / "
            f"{_text(row.get('name'))}`: {_as_int(row.get('bets')):,} "
            f"{_bets(_as_int(row.get('bets')))}, **{_pct(row.get('roi'))}**"
        )
    lines.append("")
    worst_blind = max(
        (_as_float(b.get("roi")) or 0.0 for b in blind), default=0.0
    )
    tiers = _measured(record, "tiers")
    beaten = [t for t in tiers if (_as_float(t.get("roi")) or 0.0) > worst_blind]
    if tiers and len(beaten) == len(tiers):
        verdict = (
            f"All {len(tiers)} measured tiers return more than every one of "
            "them"
        )
    elif beaten:
        verdict = (
            f"{len(beaten)} of {len(tiers)} measured tiers return more than "
            "every one of them, and the rest do not"
        )
    else:
        verdict = (
            "**No measured tier returns more than all of them**, which is a "
            "worse result than the model being merely unprofitable"
        )
    lines.append(
        f"Each is a rule that needs no model at all. {verdict}. That is what "
        "*the model carries information* means here, and it is a different "
        "statement from *the model beats the price* — which is the one the "
        "next section tests."
    )
    return lines


def _forecast_lines(record: Mapping) -> list[str]:
    forecast = record.get("forecast")
    forecast = forecast if isinstance(forecast, Mapping) else {}
    lines: list[str] = []
    tiers = [t for t in forecast.get("tiers", []) if isinstance(t, Mapping)]
    measured = [t for t in tiers if _as_int(t.get("rows")) >= S.MINIMUM_BETS]
    if not measured:
        lines.append(
            "No tier carries enough scored rows to report a Brier comparison, "
            "so none is reported."
        )
        return lines
    lines.append("**Brier against the market, per tier, with the vig left in.**")
    lines.append("")
    lines.append("| Tier | Rows | Model minus raw market | Reading |")
    lines.append("|:---|---:|:---|:---|")
    for tier in measured:
        advantage = tier.get("advantage_over_raw")
        advantage = advantage if isinstance(advantage, Mapping) else {}
        value = _as_float(advantage.get("value"))
        cells = (
            "no comparison recorded"
            if value is None
            else (
                f"{value:+.5f}, corrected "
                f"{_as_float(advantage.get('adjusted_low')) or 0.0:+.5f} to "
                f"{_as_float(advantage.get('adjusted_high')) or 0.0:+.5f}"
            )
        )
        # The reading, derived from the corrected bounds printed in the cell to
        # its left rather than read from the record — the same rule the return
        # table follows, and for the same reason.
        reading = verdict_of(advantage) if advantage else "not scored"
        lines.append(
            f"| {_tier_label(_text(tier.get('label')))} "
            f"| {_as_int(tier.get('rows')):,} | {cells} "
            f"| {reading} |"
        )
    lines.append("")
    lines.append(
        "A **negative** advantage is the model scoring worse than the price it "
        "is betting into. The verdict column reads the sign the same way every "
        "other interval in this repository does; it is a Brier difference and "
        "not a return, and it is never added to one."
    )
    worse = [t for t in measured if t.get("worse_than_the_base_rate")]
    if worse:
        named = ", ".join(
            f"{_tier_label(_text(t.get('label')))} "
            f"({_as_float(t.get('model_brier')) or 0.0:.5f} against "
            f"{_as_float(t.get('base_rate_brier')) or 0.0:.5f}, "
            f"{_as_int(t.get('rows')):,} rows)"
            for t in worse
        )
        lines.append("")
        lines.append(
            f"In {named} the model's Brier is worse than the base rate: beaten "
            "by always predicting the league average."
        )
    anti = [
        t
        for t in measured
        if isinstance(t.get("anti_predictive"), Mapping)
        and t["anti_predictive"].get("measurable")
    ]
    if anti:
        lines.append("")
        lines.append(
            "**Anti-predictiveness, per tier.** By claimed edge, the shortfall "
            "against the model's own probability widens from the smallest "
            "bucket to the largest by:"
        )
        lines.append("")
        for tier in anti:
            block = tier["anti_predictive"]
            widens = _as_float(block.get("widens_by"))
            lines.append(
                f"- {_tier_label(_text(tier.get('label')))}: "
                f"**{(widens or 0.0) * 100:.1f} pp** across "
                f"{_as_int(block.get('usable_buckets'))} usable buckets "
                f"({_as_int(block.get('lowest_rows')):,} rows in the smallest, "
                f"{_as_int(block.get('highest_rows')):,} in the largest)"
            )
        lines.append("")
        lines.append(
            "The biggest claimed edges do worst in every tier that can be "
            "measured, so raising the edge threshold is the wrong response — "
            "and it is the one move a disappointing backtest invites."
        )
    return lines


def _calibration_lines(record: Mapping) -> list[str]:
    backtest = record.get("backtest")
    backtest = backtest if isinstance(backtest, Mapping) else {}
    calibration = backtest.get("calibration")
    calibration = calibration if isinstance(calibration, Mapping) else {}
    overall = calibration.get("overall") or {}
    selected = calibration.get("selected") or {}
    overall_points = _as_float(overall.get("points"))
    selected_points = _as_float(selected.get("points"))
    if overall_points is None or selected_points is None:
        return [
            "The backtest record carries no calibration summary, so none is "
            "reported here."
        ]

    def word(points: float) -> str:
        return "overconfident" if points > 0 else "underconfident"

    return [
        "**Calibration, over the whole population and over the bets the model "
        "selected.** These are counts of rows across Division I rather than a "
        "return, and they are reported together because only the second one is "
        "evidence about the bets this lab would place:",
        "",
        f"- overall: **{abs(overall_points) * 100:.1f} pp "
        f"{word(overall_points)}** over {_as_int(overall.get('rows')):,} rows",
        f"- on the bets it **selected**: **{abs(selected_points) * 100:.1f} pp "
        f"{word(selected_points)}** over {_as_int(selected.get('rows')):,} rows",
        "",
        "The overall figure is not evidence about a betting policy. Nothing "
        "stakes money on the overall population.",
    ]


def _replication_lines(record: Mapping) -> list[str]:
    block = record.get("replication")
    block = block if isinstance(block, Mapping) else {}
    counts = block.get("counts")
    counts = counts if isinstance(counts, Mapping) else {}
    declared = (
        f"declared in advance on {_text(block.get('declared_on'))}"
        if block.get("declared_in_advance")
        else "**not declared in advance**, which is what a held-out test is for"
    )
    lines = [
        f"The held-out test is {_text(block.get('test_label')) or 'unlabelled'}, "
        f"discovered on {_text(block.get('discovery_season_label')) or 'unrecorded seasons'} "
        f"and {declared}. It graded "
        f"{_as_int(block.get('holdout_bets')):,} held-out bets over "
        f"{_as_int(block.get('holdout_games')):,} games against "
        f"{_as_int(block.get('discovery_bets')):,} on the discovery seasons, "
        f"across {_as_int(block.get('cells')):,} cells:",
        "",
    ]
    for state in sorted(counts):
        lines.append(f"- {state}: **{_as_int(counts[state]):,}** of {_as_int(block.get('cells')):,}")
    lines.append("")
    lines.append(
        "*Not enough evidence* and *nothing to replicate* are not failures to "
        "replicate. A cell with no discovery claim had nothing to carry "
        "forward, and a cell below the floor the criteria declared in advance "
        "prints a phrase and not a number. Neither is a pass, an avoid, or a "
        "no-value call."
    )
    return lines


def _open_questions(record: Mapping) -> list[str]:
    backtest = record.get("backtest")
    backtest = backtest if isinstance(backtest, Mapping) else {}
    half = backtest.get("half_point")
    half = half if isinstance(half, Mapping) else {}
    lines: list[str] = []
    phase = _text(backtest.get("snapshot_phase"))
    if phase:
        lines.append(
            f"- **One price window.** Every number above is measured at the "
            f"`{phase}` snapshot and says nothing about any other."
        )
    if not half.get("verified"):
        rate = _as_float(half.get("rate"))
        lines.append(
            "- **The half-point decomposition was refused, not computed.** The "
            "ticket-margin reconstruction agreed with the recorded outcome on "
            f"{_as_int(half.get('agreed')):,} of {_as_int(half.get('checked')):,} "
            f"settled bets ({(rate or 0.0) * 100:.1f}%), below the bar this "
            "repository set for using it, so how much of any spread or total "
            "figure is half a point at a key number is still open."
        )
    thin = [
        c
        for c in record.get("cells", [])
        if isinstance(c, Mapping) and not c.get("enough_evidence")
    ]
    if thin:
        named = ", ".join(
            f"`{_text(c.get('market'))} / {_text(c.get('tier'))}` "
            f"({_as_int(c.get('bets')):,} {_bets(_as_int(c.get('bets')))})"
            for c in sorted(thin, key=lambda c: -_as_int(c.get("bets")))
        )
        lines.append(
            f"- **{len(thin)} of {_as_int(backtest.get('cells')):,} cells are "
            f"below the {_as_int(backtest.get('minimum_bets')):,}-bet floor "
            f"declared in advance** and carry a phrase rather than a number: "
            f"{named}. A market in that list is not a market judged to have no "
            "value; it is a market with no price-based evidence either way."
        )
    lines.append(
        "- **Nothing here is a forward result.** Every number above is a "
        "historical backtest, bet into prices somebody has already seen "
        "resolve. The forward ledger is untouched by all of it and is the only "
        "evidence that can still grow."
    )
    return lines


def render(record: Mapping) -> str:
    """The document, as a pure function of the record. Reads no disk."""
    version = _as_int(record.get("record_version"))
    if version != RECORD_VERSION:
        raise WhyError(
            f"This record is version {version}; this module renders version "
            f"{RECORD_VERSION}. A record whose shape has changed is refused "
            "rather than rendered with holes in it."
        )
    # THE HEADLINE READS THE SIGN, and so does every other verdict on the page.
    # Refusing here rather than printing either string: printing the stored one
    # publishes a hand-edit, and quietly printing the derived one hides a
    # disagreement between a measurement and the file that claims to hold it.
    disagreements = verdict_disagreements(record)
    if disagreements:
        raise WhyError(
            "This record does not agree with itself — a return outside its "
            "own interval, a bound missing from the pair it belongs to, a "
            "figure with no interval beside it at all, or a stored verdict "
            "that is not what those bounds read. Every one of them is "
            "something edited between the measurement and the document. "
            "Refusing to render either reading:\n  "
            + "\n  ".join(disagreements)
        )
    backtest = record.get("backtest")
    backtest = backtest if isinstance(backtest, Mapping) else {}
    every_market = record.get("every_market")
    every_market = every_market if isinstance(every_market, Mapping) else {}

    lines: list[str] = [title(record), ""]
    lines += _provenance(record)
    lines += [
        "",
        "Read `docs/what_we_can_and_cannot_claim.md` first. This says what the "
        "evidence *is*; that says how to read it.",
        "",
        "## The answer",
        "",
        headline(record),
        "",
        f"Measured on {_as_int(backtest.get('bets_graded')):,} graded bets over "
        f"{_as_int(backtest.get('games')):,} games and "
        f"{_as_int(backtest.get('days')):,} days of the "
        f"{_text(backtest.get('season_label')) or 'unrecorded'} seasons, across "
        f"{_as_int(backtest.get('cells')):,} market-and-tier cells.",
        "",
    ]
    lines += _correction_lines(record)
    lines += ["", *_tier_table(record), ""]
    lines += _cell_lines(record)

    worst = _worst_tier(record)
    if worst is not None:
        lines += [
            "### The tier this lab was built expecting to be the best",
            "",
            "The reason for a fourth lab was market heterogeneity — 360 teams "
            "on a Tuesday night in January being priced with less attention "
            "than a 32-team league, so softness should appear at the low-major "
            "end. By point estimate the **worst** measured tier is "
            f"**{_tier_label(_text(worst.get('tier')))}**: {_figure(worst)}. "
            "Whatever is different about that board, this model is not better "
            "there.",
            "",
        ]

    if every_market:
        lines += [
            "### The pooled figure, which is not the answer",
            "",
            PB.POOLED_CAVEAT,
            "",
            f"Pooled across every market and tier: {_figure(every_market)}.",
            "",
        ]

    lines += _retraction_lines(record)
    lines += [""]

    lines += ["## The model is not worthless — it is beaten by the vig", ""]
    lines += _blind_lines(record)
    lines += ["", "## Three instruments, and none of them is the return", ""]
    lines += _forecast_lines(record)
    lines += ["", *_calibration_lines(record)]
    lines += ["", "## The held-out test", ""]
    lines += _replication_lines(record)
    lines += ["", "## What this does not settle", ""]
    lines += _open_questions(record)
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------


def write_record(record: Mapping, path: Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(record, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return target


def read_record(path: Path) -> dict:
    target = Path(path)
    if not target.is_file():
        raise WhyError(
            f"No run record at `{_repo_relative(target)}`. This report is "
            "re-rendered from its record and never written by hand, so without "
            "the record there is nothing to render — run "
            "`scripts/run_why_the_model.py` first."
        )
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise WhyError(
            f"The run record at `{_repo_relative(target)}` could not be read. "
            "Refusing to render a partial report over a good one."
        ) from exc
    if not isinstance(record, dict):
        raise WhyError(f"The run record at `{_repo_relative(target)}` is not a JSON object.")
    return record


def write_report(record: Mapping, path: Path) -> Path:
    """Render and write, refusing the vocabulary of a tipster.

    The forbidden list is `what_we_can_claim.FORBIDDEN_PHRASES` rather than a
    second copy of it: two lists drift, and the direction they drift in is
    never the conservative one. The check is on the rendered text, because the
    phrase that matters is the one a reader sees.
    """
    rendered = render(record)
    lowered = rendered.casefold()
    for phrase in WC.FORBIDDEN_PHRASES:
        if re.search(rf"\b{re.escape(phrase)}\b", lowered):
            raise WhyError(
                f"This document contains the phrase {phrase!r}, which this "
                "repository does not use about its own results. A generated "
                "summary that reaches for one of these has stopped reporting "
                "and started selling."
            )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    return target
