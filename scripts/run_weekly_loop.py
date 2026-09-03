#!/usr/bin/env python3
"""The weekly refit-and-measure loop, and the fence around what it may become.

    PYTHONPATH=src python scripts/run_weekly_loop.py --competition cbb

Cooper's brief asks for a lab that improves itself and then, in the same
paragraph, says exactly what that is not allowed to mean:

> **Self-improving must not mean "search until something looks good."** An
> automated edge-hunter without a cumulative tally does not find edges; it
> manufactures them on a schedule, with clean intervals and good prose.

Everything below is arranged around that sentence. The loop refits, re-measures,
re-renders and checks for demotion — and the one thing it can do that a report
cannot, **spend a degree of freedom**, is rationed by a budget declared on disk
before the season, drawn from a queue this script reads and never writes.

## What one run does, in order

1. **Pre-register the week's search**, before any measurement runs. New
   hypotheses come from `data/manual/weekly_search_queue.json` in the order that
   file declares, capped at the ledger's per-week alpha budget, and are appended
   to the append-only experiment ledger with `outcome="pending"`. **This step is
   first on purpose.** `scripts/record_experiments.py` says why: recording a
   prediction after the number is in hand is not a prediction, and the ledger's
   cumulative count has to already include this week's looks before the backtest
   reads it to compute its correction.
2. **Refit the ratings walk-forward**, by subprocess.
3. **Re-run the price backtest and its replication**, by subprocess.
4. **Re-render the claims report** from the run record, by subprocess.
5. **Check for auto-demotion** of any allowlisted market whose forward evidence
   has fallen through the floor its receipt declared.
6. **Check the stopping rule** that `docs/when_this_ends.md` declared before the
   data existed, weekly rather than in April.

Steps 2, 3 and 4 are subprocesses rather than imports because they are separate
programs with their own argument surfaces and their own failure modes, and
because two of them are being written beside this file. **A missing script
degrades this run and never crashes it** — the loop reports which step did not
happen, finishes the steps that can still run, and exits non-zero so the failure
notice arrives. Silence has to keep meaning "it ran and nothing was wrong".

## Why the budget is a week and not a day

`ExperimentLedger.spent_in()` counts by whatever string a hypothesis records in
`tested_on`, so the budget's unit **is** that string. This loop stamps the ISO
week (`2026-W36`) rather than the date, because a per-day bucket would let two
dispatches in one week buy twelve degrees of freedom out of a budget that says
six. The hypotheses this build pre-registered on 2026-09-01 carry a date, which
is simply a different bucket; the change only ever tightens the budget going
forward and can never loosen it.

The ceiling is checked twice, and the smaller wins: :data:`ALPHA_BUDGET_CEILING`
here and `alpha_budget.per_week` on disk. A ledger file edited to say sixty
cannot make this loop spend sixty. And a budget with no `declared_on` spends
**nothing at all**: a rate limit nobody declared in advance is not a
pre-registration, and the correct response to finding one is to record no new
hypotheses and say so, not to invent a declaration on the way past.

## Why demotion is here and promotion is not

`src/cbb_betting_lab/promotion.py` holds the asymmetry and this file obeys it.
`should_demote()` is called every week and can withdraw a market unattended.
There is no `grant()` in `promotion.py`, none in `staging_provider_policy.py`,
and none here — allowlisting a market is a receipt Cooper signs. An automated
system that can both grant and withdraw its own permissions is a system whose
safety rests on its own judgment being right; one that can only withdraw is safe
by construction.

**A withdrawal made on a runner cannot reach `main`.** This loop's workflow holds
`contents: read` and does not push, which means a demotion that fires in Actions
lands in an artifact and nowhere else. So a fired demotion exits
:data:`EXIT_DEMOTION_PENDING`, loudly, rather than being written to a file the
run then throws away. A card that keeps reading a market this loop decided to
withdraw is the failure mode, and the only thing that prevents it is somebody
noticing.

## The pooled figure, and why one exists here at all

The hard rule is that no pooled headline across the whole of Division I is ever
reported. `forward_evidence.report_payload` honours it structurally: it groups by
market **and** tier and never computes a market's pooled number.

The demotion decision cannot be made that way, because the door it opens is not
tiered — `staging_provider_policy.allows()` takes a market and nothing else, and
`AllowlistEntry.roi_floor` is the floor a human declared against that market. So
this loop computes the pooled per-market interval **for the withdrawal decision
only**, prints every market row with its tier rows underneath it, and says in
words why the pooled number is there.

The asymmetry that leaves is recorded rather than resolved: **a tier that has
fallen through the floor while the market's pooled interval has not is named in
the report and does not withdraw**, because withdrawal removes the market from
every tier and there is no receipt to re-grant it in the tiers where it was
fine. That is a limitation of a per-market allowlist, and the honest place for it
is the report a human reads.

## What this run cannot do

It allowlists nothing, signs nothing, bets nothing, and spends no credit — it
reads the store that was already bought. It cannot lower a bar: the promotion
criteria, the alpha budget and the stopping rule are all read from disk, and the
one place a threshold appears in this file is a ceiling that only tightens the
one on disk.
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from dataclasses import dataclass, field, replace
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from cbb_betting_lab import experiment_ledger as E
from cbb_betting_lab import forward_evidence as fe
from cbb_betting_lab import promotion
from cbb_betting_lab import staging_provider_policy as staging
from cbb_betting_lab import stats as S
from cbb_betting_lab import stores
from cbb_betting_lab.competitions import (
    Competition,
    DEFAULT_COMPETITION_KEY,
    competition_for,
)
from cbb_betting_lab.config import MANUAL_DIR, OUTPUTS_DIR, PROCESSED_DIR
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.reports import what_we_can_claim as WC

#: Bumped whenever the run record's shape changes, so a stale record fails
#: loudly at re-render rather than rendering a report with holes in it. The same
#: rule `price_backtest` and `retention_probe` follow, for the same reason.
RECORD_VERSION = 1

#: The scripts this loop drives, by bare filename. Resolved against
#: `--scripts-dir` at run time rather than imported, and a missing one degrades
#: the run instead of crashing it: two of these are being written beside this
#: file, and a loop that cannot start until every sibling has landed is a loop
#: nobody can test.
#:
#: They are called with this repository's argument convention —
#: `--competition <key>`, plus `--seasons ...` when the loop was given any —
#: which is what `run_gameday_card.py`, `run_forward_evidence.py` and
#: `run_what_we_can_claim.py` already take. A sibling script that does not
#: accept `--competition` will exit non-zero on argparse and be reported as a
#: failed step rather than a missing one, which is the correct distinction: the
#: program exists and did not do its job.
REFIT_SCRIPT = "fit_ratings.py"
BACKTEST_SCRIPT = "run_price_backtest.py"
CLAIMS_SCRIPT = "run_what_we_can_claim.py"

#: The pre-registered search queue. Read, never written — see the module
#: docstring. It lives beside `promotion_criteria.json` in `data/manual/`
#: because it is the same kind of object: a decision recorded before the number
#: it governs was seen.
QUEUE_FILENAME = "weekly_search_queue.json"

#: The most new hypotheses this loop will spend in one week, whatever the ledger
#: file says. The smaller of this and `alpha_budget.per_week` wins, so a ledger
#: edited upward cannot buy degrees of freedom that were never declared.
ALPHA_BUDGET_CEILING = 6

#: From `docs/when_this_ends.md`, which derived both before the data existed:
#: a working pipeline should produce on the order of 23,000 settled opinions
#: across 4,600 games in a season, and the floor below which the test did not
#: run is 10,000 opinions across 2,000 distinct games.
SEASON_OPINION_SUPPLY = 23_000
SAMPLE_FLOOR_OPINIONS = 10_000
SAMPLE_FLOOR_GAMES = 2_000

#: The decision date, declared in `docs/when_this_ends.md` before the season:
#: fourteen days after the 2027 national championship, because fourteen is the
#: settlement patience window.
DECISION_DATE = date(2027, 4, 19)

#: The edge the stopping rule is evaluated at. Not a threshold that decides
#: anything — it is the smallest figure in the detection table in
#: `docs/what_we_can_and_cannot_claim.md`, and therefore the one the correction
#: prices out of reach first.
PLAUSIBLE_EDGE = 0.05

#: Statuses a step can finish in. `SKIPPED` is healthy — a demotion check with
#: no allowlisted market has nothing to do and that is the correct state of this
#: lab. `MISSING` is not: a step that did not happen because its program is not
#: in the repository is a degraded run, however ordinary the reason.
OK = "ok"
SKIPPED = "skipped"
MISSING = "missing"
DEGRADED = "degraded"
FAILED = "failed"

HEALTHY_STATUSES = frozenset({OK, SKIPPED})

EXIT_OK = 0
EXIT_DEGRADED = 1
#: An instrument fault: a record that cannot be read, a ledger that would
#: shrink. Distinguished from a degraded run because there is nothing to read
#: rather than something missing from what was read.
EXIT_FAULT = 2
#: A demotion fired. Non-zero on purpose, and its own code: the withdrawal is in
#: the run's artifact and has to be committed by a human, and a green run would
#: be a run whose decision nobody acted on.
EXIT_DEMOTION_PENDING = 3


class WeeklyLoopError(RuntimeError):
    """An instrument fault. Distinct from a step that merely did not run."""


# --------------------------------------------------------------------------
# The week, and why it is a week
# --------------------------------------------------------------------------


def week_label(day: date) -> str:
    """`2026-W36`. The alpha budget's bucket, and the run record's identity.

    ISO, so the label of a run that fires on Monday and lands on Monday
    afternoon is the same label either way. The workflow's cron is chosen so
    that even at `schedule_contract.OBSERVED_LATENESS_H` the run cannot cross
    into the following ISO week and spend next week's budget on this week's
    search; `tests/test_weekly_loop.py` recomputes that from the constant.
    """
    year, week, _weekday = day.isocalendar()
    return f"{year}-W{week:02d}"


# --------------------------------------------------------------------------
# Steps
# --------------------------------------------------------------------------


@dataclass
class Step:
    """One thing the loop tried, and what came of it."""

    name: str
    status: str
    detail: str
    lines: list[str] = field(default_factory=list)

    @property
    def healthy(self) -> bool:
        return self.status in HEALTHY_STATUSES

    def as_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "lines": list(self.lines),
        }


def run_script(
    filename: str,
    argv: list[str],
    *,
    scripts_dir: Path,
    name: str,
    dry_run: bool,
    timeout_seconds: int,
    python: str = "",
) -> Step:
    """Run a sibling script, and treat its absence as a fact rather than a crash.

    Three outcomes, and they are deliberately not two. A script that is **not in
    the repository** is `MISSING`; a script that ran and **failed** is `FAILED`;
    a script that ran is `OK`. Collapsing the first two would make "nobody has
    written the refit yet" and "the refit crashed on this week's data" produce
    the same line in a report, and those need different responses.
    """
    path = Path(scripts_dir) / filename
    if not path.is_file():
        return Step(
            name=name,
            status=MISSING,
            detail=(
                f"{filename} is not in {scripts_dir}. This step did not run, "
                "and nothing downstream of it was refreshed. The run continues "
                "and finishes red rather than reporting a loop that completed."
            ),
        )
    command = [python or sys.executable, str(path), *argv]
    printable = " ".join([Path(command[0]).name, filename, *argv])
    if dry_run:
        return Step(
            name=name,
            status=SKIPPED,
            detail=f"--dry-run: would have run `{printable}`.",
        )
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return Step(
            name=name,
            status=FAILED,
            detail=(
                f"`{printable}` did not finish inside {timeout_seconds}s and was "
                "killed. Nothing it had half-written is trusted by the steps "
                "below."
            ),
        )
    tail = [line for line in (completed.stdout or "").splitlines() if line.strip()][-12:]
    if completed.returncode != 0:
        stderr_tail = [
            line for line in (completed.stderr or "").splitlines() if line.strip()
        ][-6:]
        return Step(
            name=name,
            status=FAILED,
            detail=f"`{printable}` exited {completed.returncode}.",
            lines=tail + stderr_tail,
        )
    return Step(name=name, status=OK, detail=f"`{printable}` exited 0.", lines=tail)


# --------------------------------------------------------------------------
# Step 1: pre-register the week's search
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class QueuedHypothesis:
    """A pre-registered hypothesis, and the sentence that justified it.

    `why` is not carried on `experiment_ledger.Hypothesis` — that dataclass is
    the ledger's shape and this loop does not change it — so it is kept here and
    printed in the weekly report instead. A queue entry whose reason lives only
    in a commit message is one nobody reads at the moment it is spent.
    """

    hypothesis: E.Hypothesis
    why: str = ""


def load_queue(path: Path, *, week: str) -> tuple[list[QueuedHypothesis], list[str]]:
    """The declared queue, in file order, stamped with this week.

    Returns the entries and the problems. A malformed entry is a **problem
    reported**, never an entry quietly dropped: a queue that silently discards
    the hypothesis somebody meant to pre-register is a queue that under-counts
    the search, which is the one direction the ledger must never err in.

    `tested_on` is stamped here rather than declared in the file, because the
    file says *what* will be tested and the loop decides *when* the budget can
    afford it. It is not part of `Hypothesis.key()`, so an entry spent in one
    week is recognised as already-spent in every later week.
    """
    target = Path(path)
    if not target.is_file():
        return [], []
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return [], [f"{target.name} could not be read: {exc}"]
    if not isinstance(payload, dict):
        return [], [f"{target.name} is not a JSON object."]

    entries: list[QueuedHypothesis] = []
    problems: list[str] = []
    for index, item in enumerate(payload.get("queue", []) or [], start=1):
        if not isinstance(item, dict):
            problems.append(f"entry {index} is not an object and was not spent.")
            continue
        try:
            hypothesis = E.Hypothesis(
                search=str(item.get("search", "")),
                name=str(item.get("name", "")),
                tested_on=week,
                seasons=tuple(int(s) for s in item.get("seasons", []) or []),
                outcome="pending",
                predicted_direction=str(item.get("predicted_direction", "")),
                stage=str(item.get("stage", "discovery")),
            )
        except (E.DirectionRequired, ValueError, TypeError) as exc:
            # The direction guard firing is the guard working. It is reported
            # rather than swallowed so the entry gets fixed instead of silently
            # never being tested.
            problems.append(f"entry {index} ({item.get('name', '?')!r}): {exc}")
            continue
        entries.append(QueuedHypothesis(hypothesis=hypothesis, why=str(item.get("why", ""))))
    return entries, problems


@dataclass
class BudgetSpend:
    """What the alpha budget allowed, and what is still waiting."""

    week: str
    declared_on: str = ""
    per_week: int = 0
    already_spent: int = 0
    remaining_before: int = 0
    spent_now: tuple[QueuedHypothesis, ...] = ()
    waiting: tuple[QueuedHypothesis, ...] = ()
    already_recorded: tuple[QueuedHypothesis, ...] = ()
    problems: tuple[str, ...] = ()
    refused: str = ""

    @property
    def count(self) -> int:
        return len(self.spent_now)


def spend_alpha_budget(
    ledger: E.ExperimentLedger,
    queue: list[QueuedHypothesis],
    *,
    week: str,
    problems: list[str],
    ceiling: int = ALPHA_BUDGET_CEILING,
) -> BudgetSpend:
    """Take at most N new hypotheses from the queue, in the order it declared.

    **The budget is never borrowed against and never lowered.** When it is spent
    the remaining queue waits for next week, which is the whole point: a rate
    limit that can be exceeded on a week the search feels productive is a rate
    limit that has never bound anything.

    The refusals are as important as the arithmetic:

    * **No `declared_on` on the ledger's budget** — nothing is spent. A budget
      nobody declared in advance is not a pre-registration, and inventing a
      declaration date on the way past would be the loop signing its own
      permission slip.
    * **A queue entry already in the ledger** — costs nothing. `Hypothesis.key()`
      excludes the date deliberately, so re-measuring last week's hypothesis on
      another week's data is the same look. Charging for it again would make
      re-running anything expensive, and nobody would re-run anything.
    """
    budget = ledger.budget
    spend = BudgetSpend(
        week=week,
        declared_on=budget.declared_on,
        problems=tuple(problems),
    )
    if not budget.declared_on:
        spend.refused = (
            "the ledger's alpha budget carries no `declared_on`, so it is not a "
            "budget declared in advance. Nothing was spent. Declare it in "
            f"{E.LEDGER_FILENAME} rather than letting this run declare it."
        )
        return spend

    per_week = min(int(budget.per_week), int(ceiling))
    spend.per_week = per_week
    spend.already_spent = ledger.spent_in(week)
    spend.remaining_before = max(per_week - spend.already_spent, 0)

    known = {h.key() for h in ledger.hypotheses}
    fresh: list[QueuedHypothesis] = []
    seen: list[QueuedHypothesis] = []
    for entry in queue:
        (seen if entry.hypothesis.key() in known else fresh).append(entry)
    spend.already_recorded = tuple(seen)

    take = fresh[: spend.remaining_before]
    spend.spent_now = tuple(take)
    spend.waiting = tuple(fresh[spend.remaining_before :])
    if take:
        added = ledger.record(*(entry.hypothesis for entry in take))
        # `record()` skips duplicates, and every entry here was filtered against
        # the ledger a moment ago — so a mismatch means the queue declared the
        # same hypothesis twice, which would have spent one slot and recorded
        # two. Reported rather than tolerated.
        if added != len(take):
            spend.problems = spend.problems + (
                f"the queue declared {len(take)} entries for this week but only "
                f"{added} were new; the duplicate spent a slot and recorded "
                "nothing.",
            )
    return spend


# --------------------------------------------------------------------------
# Step 3b: what the backtest record has to prove about itself
# --------------------------------------------------------------------------


def verify_backtest_record(
    path: Path,
    *,
    looks_expected: int,
    started_at: datetime,
    replication_record: Path,
) -> tuple[Step, dict]:
    """Read the backtest's own record back and check three things about it.

    A subprocess exiting zero says a program finished. It does not say the
    program measured this week, nor that it corrected across the ledger's
    cumulative count. Both have failed silently in a sibling lab, so both are
    checked here against the record that was written:

    1. **Freshness.** A `generated_at` that predates this run means the record on
       disk is last week's and every number downstream of it is stale. A stale
       record is exactly what a green run looks like when the measurement did
       not happen.
    2. **The correction is the ledger's cumulative count.** `record["looks"]`
       must equal `price_backtest.looks_from_ledger`, which is the hard rule
       written down: *"family-wise correction from the experiment ledger's
       CUMULATIVE count, never the day's."* A backtest that corrected across the
       four markets it measured today would report intervals narrower than the
       truth, and they would look clean.
    3. **Replication.** Reported, never asserted. `what_we_can_claim` reads an
       optional replication record and this loop says whether one was written
       this run — because *"replication remains the bar"* and a loop that
       quietly reported nothing about it would let a claim reach the claims
       document with no held-out season behind it.

    A missing replication record does **not** degrade the run. This loop does not
    own the backtest's record schema and must not fail a build over a section
    another module has not written yet; it says the limitation out loud instead.
    """
    summary: dict = {
        "record": str(path),
        "readable": False,
        "fresh": False,
        "looks_expected": int(looks_expected),
        "looks_recorded": None,
        "replication_confirmed": False,
        "replication_record": str(replication_record),
    }
    if not Path(path).is_file():
        return (
            Step(
                name="verify the backtest record",
                status=MISSING,
                detail=(
                    f"No backtest record at {Path(path).name}. Nothing was "
                    "verified, and no number from a backtest may be quoted "
                    "from this run."
                ),
            ),
            summary,
        )
    try:
        record = PB.read_record(Path(path))
    except (PB.BacktestError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        # An unreadable record is an instrument fault rather than a missing
        # step: there IS something on disk and it cannot be trusted, which is
        # worse than there being nothing.
        return (
            Step(
                name="verify the backtest record",
                status=FAILED,
                detail=f"{Path(path).name} could not be read: {exc}",
            ),
            summary,
        )

    summary["readable"] = True
    looks_recorded = int(record.get("looks", 0) or 0)
    summary["looks_recorded"] = looks_recorded
    generated_at = str(record.get("generated_at", "") or "")
    summary["generated_at"] = generated_at

    faults: list[str] = []
    stamped = _parse_timestamp(generated_at)
    if stamped is None:
        faults.append(
            "the record carries no readable `generated_at`, so this run cannot "
            "tell whether the backtest ran this week or last"
        )
    elif stamped < started_at:
        faults.append(
            f"the record was generated at {generated_at}, before this run "
            f"started at {started_at.isoformat(timespec='seconds')} — the "
            "backtest did not re-run and every figure below it is stale"
        )
    else:
        summary["fresh"] = True

    if looks_recorded != int(looks_expected):
        faults.append(
            f"the record corrected across {looks_recorded:,} looks and the "
            f"experiment ledger's cumulative count is {looks_expected:,}. The "
            "correction must come from the ledger's cumulative count and never "
            "the day's, so the intervals in that record are not the intervals "
            "they claim to be"
        )

    if Path(replication_record).is_file():
        replication_stamp = _record_timestamp(Path(replication_record))
        summary["replication_confirmed"] = (
            replication_stamp is not None and replication_stamp >= started_at
        )

    if faults:
        return (
            Step(
                name="verify the backtest record",
                status=DEGRADED,
                detail="; ".join(faults) + ".",
            ),
            summary,
        )
    detail = (
        f"{Path(path).name} is this run's, and its correction is the ledger's "
        f"cumulative {looks_expected:,} looks."
    )
    if not summary["replication_confirmed"]:
        detail += (
            " No replication record was written this run, so nothing here "
            "confirms a held-out season was scored. Replication remains the "
            "bar and this run did not clear it."
        )
    return Step(name="verify the backtest record", status=OK, detail=detail), summary


def _parse_timestamp(value: str) -> datetime | None:
    text = str(value or "").strip().replace("Z", "+00:00")
    if not text:
        return None
    try:
        stamped = datetime.fromisoformat(text)
    except ValueError:
        return None
    return stamped if stamped.tzinfo else stamped.replace(tzinfo=timezone.utc)


def _record_timestamp(path: Path) -> datetime | None:
    """A record's own `generated_at`, or its mtime as a fallback.

    The fallback is deliberate and it is the weaker claim: a file this run wrote
    has a fresh mtime whether or not it stamped itself. It is used only to say
    "something was written this run", never to say a measurement was made.
    """
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        payload = {}
    if isinstance(payload, dict):
        stamped = _parse_timestamp(str(payload.get("generated_at", "")))
        if stamped is not None:
            return stamped
    try:
        return datetime.fromtimestamp(Path(path).stat().st_mtime, tz=timezone.utc)
    except OSError:
        return None


def verify_walk_forward(path: Path | None) -> tuple[Step, dict]:
    """Re-run `price_backtest.assert_walk_forward` over a graded-bet frame.

    `build_record` already asserts it when the record is built, and that is
    where the guard belongs. This is the independent second look, and it exists
    because the football lab's largest silent leak — a distribution loaded once,
    outside the season loop, so the model pricing 2023 had seen 2025 — was
    invisible in every report it produced.

    **The absence of a frame is reported as an absence, never as a pass.** If
    nothing was offered, this step says walk-forward could not be re-verified
    here; it does not say walk-forward held. A leak in a frame that *is* offered
    fails the run outright rather than degrading it: a model priced on games it
    could not have seen is not a degraded measurement, it is a different
    measurement.
    """
    summary = {"frame": str(path) if path else "", "verified": False, "rows": 0}
    if not path or not Path(path).is_file():
        where = f" at {path}" if path else " was offered (--verify-bets)"
        return (
            Step(
                name="re-verify walk-forward",
                status=SKIPPED,
                detail=(
                    f"No graded-bet frame{where}, so walk-forward was not "
                    "re-verified here. `price_backtest.build_record` asserts it "
                    "when the record is built; this run adds no second opinion "
                    "and does not claim one."
                ),
            ),
            summary,
        )
    try:
        frame = pd.read_csv(Path(path))
    except (OSError, UnicodeError, pd.errors.ParserError) as exc:
        return (
            Step(
                name="re-verify walk-forward",
                status=FAILED,
                detail=f"{Path(path).name} could not be read: {exc}",
            ),
            summary,
        )
    summary["rows"] = int(len(frame))
    try:
        PB.assert_walk_forward(frame)
    except PB.WalkForwardLeak as exc:
        return (
            Step(
                name="re-verify walk-forward",
                status=FAILED,
                detail=(
                    f"WALK-FORWARD LEAK in {Path(path).name}: {exc} Nothing "
                    "measured from this frame is out of sample."
                ),
            ),
            summary,
        )
    except (KeyError, PB.BacktestError) as exc:
        return (
            Step(
                name="re-verify walk-forward",
                status=DEGRADED,
                detail=(
                    f"{Path(path).name} could not be checked for a walk-forward "
                    f"leak: {exc} This is not a pass."
                ),
            ),
            summary,
        )
    summary["verified"] = True
    return (
        Step(
            name="re-verify walk-forward",
            status=OK,
            detail=(
                f"{len(frame):,} graded bets, every one priced only on games "
                "strictly earlier than the day it bet on."
            ),
        ),
        summary,
    )


# --------------------------------------------------------------------------
# Step 5: auto-demotion, one direction only
# --------------------------------------------------------------------------


@dataclass
class DemotionFinding:
    """One allowlisted market, its forward record, and what follows."""

    market: str
    receipt_id: str
    roi_floor: float
    minimum_bets: int
    pooled: S.RoiInterval
    tiers: tuple[tuple[str, S.RoiInterval], ...]
    withdraw: bool
    reason: str
    #: Tiers whose whole interval sits below the floor while the market's pooled
    #: interval does not. Named, never acted on. See the module docstring.
    tiers_below_floor: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {
            "market": self.market,
            "receipt_id": self.receipt_id,
            "roi_floor": self.roi_floor,
            "minimum_bets": self.minimum_bets,
            "pooled": _interval_dict(self.pooled),
            "tiers": {tier: _interval_dict(i) for tier, i in self.tiers},
            "withdraw": self.withdraw,
            "reason": self.reason,
            "tiers_below_floor": list(self.tiers_below_floor),
        }


def _interval_dict(interval: S.RoiInterval) -> dict:
    return {
        "roi": interval.roi,
        "low": interval.low,
        "high": interval.high,
        "adjusted_low": interval.adjusted_low,
        "adjusted_high": interval.adjusted_high,
        "bets": interval.bets,
        "clusters": interval.clusters,
        "cluster_unit": interval.cluster_unit,
        "looks": interval.looks,
        "verdict": interval.verdict(),
        "line": interval.line(),
    }


def measurable_bets(ledger_frame: pd.DataFrame, competition: Competition) -> pd.DataFrame:
    """The settled forward opinions a demotion may be decided on.

    Deliberately the **same** helpers `forward_evidence.report_payload` uses,
    called rather than copied. The rules they encode are not incidental — an
    `UNSETTLEABLE` row averaged in as break-even is a fabricated number, a
    `VOID` row folded in at 0.0 drags every interval toward zero while inflating
    every n, and a player prop cannot produce a selection in this sport at all —
    and a second copy of them here would drift from the published report exactly
    the way `docs/decision_log.md` #11 refuses to let the probe's population
    drift from the backtest's. One definition of "measurable", one place.
    """
    measurable = fe._measurable(fe._with_ledger_columns(ledger_frame), competition)
    games, _futures = fe._split_families(measurable)
    return fe._bet_rows(games, fe.BET_EDGE_THRESHOLD)


def check_for_demotion(
    *,
    policy: staging.StagingProviderPolicy,
    criteria: promotion.Criteria,
    bets: pd.DataFrame,
    looks: int,
) -> list[DemotionFinding]:
    """Every allowlisted market, judged against the floor its receipt declared.

    The floor and the evidence bar come from the `AllowlistEntry` rather than
    from the criteria file, because `staging_provider_policy` says so
    explicitly: *"the floor is recorded on the entry at approval time rather
    than looked up later, so the bar a market is held to is the bar its receipt
    named and not the bar that would be convenient in March."*

    The one place the criteria file still wins is the evidence bar, and it wins
    only when it is **stricter**. Withdrawal is irreversible without a new human
    receipt and it stops the forward evidence that would settle the question, so
    the loop demands the larger of the two minimums and never the smaller.
    """
    findings: list[DemotionFinding] = []
    for market in sorted(policy.allowlist):
        entry = policy.allowlist[market]
        market_bets = (
            bets[bets["market"] == market] if not bets.empty else bets
        )
        pooled = fe._interval(market_bets, looks=looks)
        tiers: list[tuple[str, S.RoiInterval]] = []
        if not market_bets.empty:
            for tier, part in market_bets.groupby("tier", sort=True):
                tiers.append((str(tier), fe._interval(part, looks=looks)))

        terms = replace(
            criteria,
            demotion_roi_floor=float(entry.roi_floor),
            demotion_minimum_bets=max(
                int(entry.minimum_bets), int(criteria.demotion_minimum_bets)
            ),
        )
        withdraw, reason = promotion.should_demote(
            roi=pooled.roi,
            low=pooled.low,
            high=pooled.high,
            bets=pooled.bets,
            criteria=terms,
        )
        below = tuple(
            tier
            for tier, interval in tiers
            if interval.bets >= terms.demotion_minimum_bets
            and interval.high < terms.demotion_roi_floor
        )
        findings.append(
            DemotionFinding(
                market=market,
                receipt_id=entry.receipt_id,
                roi_floor=float(entry.roi_floor),
                minimum_bets=int(terms.demotion_minimum_bets),
                pooled=pooled,
                tiers=tuple(tiers),
                withdraw=bool(withdraw),
                reason=reason,
                tiers_below_floor=() if withdraw else below,
            )
        )
    return findings


# --------------------------------------------------------------------------
# Step 6: the stopping rule, checked weekly rather than noticed in April
# --------------------------------------------------------------------------


def stopping_rule(
    ledger: E.ExperimentLedger,
    *,
    today: date,
    edge: float = PLAUSIBLE_EDGE,
    supply: int = SEASON_OPINION_SUPPLY,
) -> dict:
    """Has the search spent so much alpha that nothing could clear?

    The third of the three things that end this project early, from
    `docs/when_this_ends.md`: *"If the correction factor grows large enough that
    a plausible edge could not clear it on a season's sample, the search has
    spent its budget and continuing it is arithmetic theatre. The ledger's own
    `correction_factor()` and `stats.bets_needed_to_detect()` decide that
    together, and it is checked every week rather than noticed in April."*

    Two supplies, both from that document, because they answer different
    questions and only one of them is close enough to watch. The **expected**
    season supply is what a working pipeline produces; the **floor** is the
    minimum below which the verdict is not a number at all. The project stops on
    the generous reading, so `exhausted` is computed against the expected
    supply — but the floor crossing is reported beside it as the early warning,
    and it arrives some ten orders of magnitude sooner.

    The arithmetic assumes independent bets of unit variance, which this sport
    does not supply — one game is several correlated wagers, and every interval
    in this lab is clustered for exactly that reason. So the requirement printed
    here is a **lower bound** on the bets actually needed, which makes this an
    optimistic read of whether the search has spent itself. Stated rather than
    corrected, because a clustering factor invented for this line would be a
    number nobody measured.
    """
    looks = max(ledger.count, 1)
    factor = ledger.correction_factor()
    uncorrected = S.bets_needed_to_detect(edge)
    needed = int(math.ceil(uncorrected * factor**2))
    return {
        "looks": looks,
        "correction_factor": factor,
        "edge": edge,
        "bets_needed_uncorrected": uncorrected,
        "bets_needed_corrected": needed,
        "season_supply": int(supply),
        "sample_floor_opinions": SAMPLE_FLOOR_OPINIONS,
        "sample_floor_games": SAMPLE_FLOOR_GAMES,
        "exhausted": needed > int(supply),
        "looks_at_which_it_bites": looks_at_which_the_budget_is_spent(
            edge=edge, supply=supply
        ),
        "looks_at_which_it_bites_at_the_floor": looks_at_which_the_budget_is_spent(
            edge=edge, supply=SAMPLE_FLOOR_OPINIONS
        ),
        "decision_date": DECISION_DATE.isoformat(),
        "days_to_decision": (DECISION_DATE - today).days,
        "assumption": (
            "independent bets of unit variance, which this sport does not "
            "supply — so this is a lower bound on the bets needed and therefore "
            "an optimistic read of the remaining headroom"
        ),
    }


#: The largest cumulative hypothesis count :func:`looks_at_which_the_budget_is_spent`
#: will search up to before it stops and says "beyond here". Bonferroni's z
#: grows like the square root of the log of the family size, so the crossing
#: point against a full season's supply is astronomically far away and the
#: honest report of it is a bound rather than a number that looks precise.
LOOKS_SEARCH_CEILING = 10**18


def looks_at_which_the_budget_is_spent(
    *, edge: float = PLAUSIBLE_EDGE, supply: int = SEASON_OPINION_SUPPLY
) -> int:
    """The cumulative hypothesis count at which `edge` could no longer clear.

    Reported every week so the number is watched while it is still far away,
    rather than discovered at the moment it binds. Found by search rather than
    by inverting the normal quantile, because the inverse is one more piece of
    arithmetic to get subtly wrong and this runs once a week over integers.

    **What it says is worth knowing and is not encouragement.** Against a full
    season's supply the answer is on the order of a trillion looks, which is the
    honest shape of a Bonferroni correction: its z grows like the square root of
    the log of the family size, so the cumulative count is not what will end
    this project. The decision date and the sample floor are. Against the floor
    the answer is tens of thousands, which is a number a long-running search
    could conceivably reach, and that is the one to watch.
    """
    uncorrected = S.bets_needed_to_detect(edge)
    if uncorrected <= 0:
        return 0
    low, high = 1, 2
    while math.ceil(uncorrected * S.bonferroni_factor(high) ** 2) <= int(supply):
        low, high = high, high * 2
        if high > LOOKS_SEARCH_CEILING:
            return high
    while low + 1 < high:
        middle = (low + high) // 2
        if math.ceil(uncorrected * S.bonferroni_factor(middle) ** 2) <= int(supply):
            low = middle
        else:
            high = middle
    return high


# --------------------------------------------------------------------------
# The run record
# --------------------------------------------------------------------------


def build_record(
    *,
    competition: Competition,
    week: str,
    started_at: datetime,
    steps: list[Step],
    spend: BudgetSpend,
    ledger_before: int,
    ledger_after: int,
    correction_before: float,
    correction_after: float,
    backtest: dict,
    walk_forward: dict,
    findings: list[DemotionFinding],
    stopping: dict,
    forward: dict,
    policy_summary: str,
    dry_run: bool,
) -> dict:
    """Every number this run made, as plain data. `render` is pure over it.

    The retention probe's rule applied again, and for the same reason it was
    written: improving a sentence must never cost a re-run, and a report that
    can only be produced by re-running the measurement is a report nobody
    improves.
    """
    return {
        "record_version": RECORD_VERSION,
        "competition": competition.key,
        "title": competition.title,
        "week": week,
        "generated_at": started_at.isoformat(timespec="seconds"),
        "dry_run": bool(dry_run),
        "steps": [step.as_dict() for step in steps],
        "alpha_budget": {
            "week": spend.week,
            "declared_on": spend.declared_on,
            "per_week": spend.per_week,
            "ceiling": ALPHA_BUDGET_CEILING,
            "already_spent_this_week": spend.already_spent,
            "remaining_before": spend.remaining_before,
            "spent_now": [
                {
                    "search": entry.hypothesis.search,
                    "name": entry.hypothesis.name,
                    "seasons": list(entry.hypothesis.seasons),
                    "predicted_direction": entry.hypothesis.predicted_direction,
                    "stage": entry.hypothesis.stage,
                    "why": entry.why,
                }
                for entry in spend.spent_now
            ],
            "waiting": [
                {
                    "search": entry.hypothesis.search,
                    "name": entry.hypothesis.name,
                    "stage": entry.hypothesis.stage,
                }
                for entry in spend.waiting
            ],
            "already_recorded": len(spend.already_recorded),
            "problems": list(spend.problems),
            "refused": spend.refused,
        },
        "ledger": {
            "hypotheses_before": ledger_before,
            "hypotheses_after": ledger_after,
            "correction_before": correction_before,
            "correction_after": correction_after,
        },
        "backtest": backtest,
        "walk_forward": walk_forward,
        "forward_evidence": forward,
        "policy": {"summary": policy_summary},
        "demotion": [finding.as_dict() for finding in findings],
        "stopping_rule": stopping,
    }


def render(record: dict) -> str:
    """The weekly report, as a pure function of the record."""
    lines: list[str] = []
    add = lines.append
    week = record.get("week", "")
    add(f"# Weekly refit-and-measure — {week}")
    add("")
    add(
        f"**{record.get('title', '')}**, generated "
        f"{record.get('generated_at', '')}."
        + (" **Dry run: nothing was written.**" if record.get("dry_run") else "")
    )
    add("")
    add(
        "This run refitted, re-measured, re-rendered and checked for demotion. "
        "It **allowlisted no market, signed no receipt, placed no bet and spent "
        "no credit** — it reads the store that was already bought. There is no "
        "`grant()` in this repository and this loop does not add one: the "
        "machine may take a market away from itself and may never give itself "
        "one."
    )
    add("")

    add("## What ran")
    add("")
    add("| Step | Status | Detail |")
    add("|:---|:---|:---|")
    for step in record.get("steps", []) or []:
        detail = str(step.get("detail", "")).replace("|", "\\|")
        add(f"| {step.get('name', '')} | **{step.get('status', '')}** | {detail} |")
    add("")

    lines.extend(_alpha_budget_section(record))
    lines.extend(_measurement_section(record))
    lines.extend(_demotion_section(record))
    lines.extend(_stopping_section(record))

    add("## What a reader may not conclude from this page")
    add("")
    add(
        "Nothing here is a claim about whether this lab has an edge. Every "
        f"figure that could be one carries its sample size, and **{S.NO_DEMONSTRATED_EDGE}** "
        "is the only permitted reading of an interval that includes zero. The "
        "claims document is written from the run record by its own script and "
        "is the place those figures are read; this page says what the machinery "
        "did."
    )
    return "\n".join(lines).rstrip() + "\n"


def _alpha_budget_section(record: dict) -> list[str]:
    budget = record.get("alpha_budget", {}) or {}
    ledger = record.get("ledger", {}) or {}
    lines = ["## The alpha budget", ""]
    if budget.get("refused"):
        lines += [
            f"**Nothing was spent:** {budget['refused']}",
            "",
        ]
    else:
        lines += [
            f"**{len(budget.get('spent_now', []) or []):,} of "
            f"{int(budget.get('remaining_before', 0)):,} available slots spent "
            f"this week** ({budget.get('per_week', 0)} a week, declared "
            f"{budget.get('declared_on') or '—'}; the ceiling this script will "
            f"honour is {budget.get('ceiling', ALPHA_BUDGET_CEILING)} whatever "
            "the ledger file says).",
            "",
        ]
    lines += [
        f"The ledger held **{int(ledger.get('hypotheses_before', 0)):,}** distinct "
        f"hypotheses before this run and **{int(ledger.get('hypotheses_after', 0)):,}** "
        f"after. Any new 95% interval must be widened by "
        f"**x{float(ledger.get('correction_after', 1.0)):.2f}** before it means "
        "what it says.",
        "",
    ]
    spent = budget.get("spent_now", []) or []
    if spent:
        lines += [
            "| Search | Hypothesis | Predicted | Stage | Seasons | Why |",
            "|:---|:---|:---|:---|:---|:---|",
        ]
        for entry in spent:
            seasons = ", ".join(str(s) for s in entry.get("seasons", [])) or "—"
            why = str(entry.get("why", "")).replace("|", "\\|")
            lines.append(
                f"| {entry.get('search', '')} | {entry.get('name', '')} | "
                f"{entry.get('predicted_direction', '')} | {entry.get('stage', '')} | "
                f"{seasons} | {why} |"
            )
        lines.append("")
        lines += [
            "**These were recorded before the measurement ran, not after.** A "
            "predicted direction written down once the number is in hand is not "
            "a prediction. The workflow that drives this loop holds "
            "`contents: read` and cannot push, so the grown ledger is in the "
            "run's artifact and has to be committed — until it is, the same "
            "slots are spent again next week and the committed record of what "
            "this lab has tested is smaller than the truth.",
            "",
        ]
    waiting = budget.get("waiting", []) or []
    if waiting:
        lines += [
            f"**{len(waiting):,} pre-registered hypotheses are waiting** for next "
            "week's budget. The search waits; it never lowers the bar and never "
            "borrows against a future week.",
            "",
        ]
    elif not budget.get("refused") and not spent:
        # Only when nothing was spent AND nothing is waiting. Printing "the
        # queue is empty" in the same run that drained it reads as though the
        # loop had found nothing to do.
        lines += [
            "**The pre-registered queue is empty, and that is the steady state.** "
            "Re-measuring a hypothesis already in the ledger on another week's "
            "data is the same look rather than a new one — `Hypothesis.key()` "
            "excludes the date, so re-running costs nothing and cannot inflate "
            "the correction. A new question is declared in "
            f"`data/manual/{QUEUE_FILENAME}` in a pull request, before the "
            "number it predicts has been seen.",
            "",
        ]
    for problem in budget.get("problems", []) or []:
        lines.append(f"- **Queue problem:** {problem}")
    if budget.get("problems"):
        lines.append("")
    return lines


def _measurement_section(record: dict) -> list[str]:
    backtest = record.get("backtest", {}) or {}
    walk = record.get("walk_forward", {}) or {}
    lines = ["## What the measurement proved about itself", ""]
    if not backtest.get("readable"):
        lines += [
            "**No backtest record could be read this run**, so no figure from a "
            "price backtest may be quoted from it. That is an absence, not a "
            "null result.",
            "",
        ]
    else:
        looks_recorded = backtest.get("looks_recorded")
        lines += [
            f"- Correction: the record used **{looks_recorded:,}** looks against "
            f"the experiment ledger's cumulative **{int(backtest.get('looks_expected', 0)):,}**."
            if isinstance(looks_recorded, int)
            else "- Correction: the record does not say how many looks it used.",
            f"- Freshness: the record {'was' if backtest.get('fresh') else '**was not**'} "
            "generated by this run.",
            f"- Replication: {'a replication record was written this run' if backtest.get('replication_confirmed') else '**no replication record was written this run**, so nothing here confirms a held-out season was scored. Replication remains the bar'}.",
            "",
        ]
    if walk.get("verified"):
        lines += [
            f"- Walk-forward: re-verified over **{int(walk.get('rows', 0)):,}** "
            "graded bets, every one priced only on games strictly earlier than "
            "the day it bet on.",
            "",
        ]
    else:
        lines += [
            "- Walk-forward: **not re-verified here.** "
            "`price_backtest.build_record` asserts it when the record is built; "
            "this run adds no second opinion and does not claim one.",
            "",
        ]
    return lines


def _demotion_section(record: dict) -> list[str]:
    findings = record.get("demotion", []) or []
    policy = (record.get("policy", {}) or {}).get("summary", "")
    forward = record.get("forward_evidence", {}) or {}
    lines = ["## Auto-demotion", ""]
    lines += [policy, ""] if policy else []
    lines += [
        f"The forward ledger holds **{int(forward.get('rows', 0)):,}** settled "
        f"rows, of which **{int(forward.get('bets', 0)):,}** clear the "
        f"{float(forward.get('threshold', 0.0)):.0%} edge declared in advance "
        "and could have been selected.",
        "",
    ]
    if not findings:
        lines += [
            "**No market is allowlisted, so there is nothing to withdraw.** That "
            "is the correct state for a lab with no signed receipt, and it is "
            "the state this one expects to stay in unless the measurement says "
            "otherwise and Cooper signs.",
            "",
        ]
        return lines

    lines += [
        "The withdrawal decision is made on each market's **pooled** forward "
        "interval, because the door it opens is not tiered — "
        "`staging_provider_policy.allows()` takes a market and nothing else, "
        "and the floor is the one that market's receipt declared. The pooled "
        "figure is here for that reason and for no other; **it is never a "
        "headline**, and every market row below is followed by its tier rows.",
        "",
        "| Market | Cut | Bets | ROI | 95% interval | Family-corrected | Verdict |",
        "|:---|:---|---:|---:|:---|:---|:---|",
    ]
    for finding in findings:
        pooled = finding.get("pooled", {}) or {}
        lines.append(_interval_row(finding.get("market", ""), "pooled (decision)", pooled))
        for tier, interval in (finding.get("tiers", {}) or {}).items():
            lines.append(_interval_row("", tier, interval))
    lines.append("")
    for finding in findings:
        verb = "**WITHDRAWN**" if finding.get("withdraw") else "kept"
        lines.append(
            f"- `{finding.get('market', '')}` (receipt "
            f"`{finding.get('receipt_id', '') or '—'}`, floor "
            f"{float(finding.get('roi_floor', 0.0)):+.2%}, evidence bar "
            f"{int(finding.get('minimum_bets', 0)):,} bets): {verb} — "
            f"{finding.get('reason', '')}"
        )
        below = finding.get("tiers_below_floor", []) or []
        if below:
            lines.append(
                f"  - **{', '.join(below)} has fallen through the floor while "
                "the market's pooled interval has not.** Named and not acted "
                "on: withdrawal removes the market from every tier and there is "
                "no receipt to re-grant it in the tiers where it was fine. That "
                "is a limitation of a per-market allowlist, and this line is "
                "where it is recorded."
            )
    lines.append("")
    return lines


def _interval_row(market: str, cut: str, interval: dict) -> str:
    if not interval or not int(interval.get("bets", 0)):
        return f"| {market} | {cut} | 0 | — | — | — | not enough evidence — 0 bets |"
    return (
        f"| {market} | {cut} | {int(interval.get('bets', 0)):,} | "
        f"{float(interval.get('roi', 0.0)):+.1%} | "
        f"{float(interval.get('low', 0.0)):+.1%} to {float(interval.get('high', 0.0)):+.1%} | "
        f"{float(interval.get('adjusted_low', 0.0)):+.1%} to "
        f"{float(interval.get('adjusted_high', 0.0)):+.1%} | "
        f"{interval.get('verdict', '')} |"
    )


def _stopping_section(record: dict) -> list[str]:
    rule = record.get("stopping_rule", {}) or {}
    lines = ["## The stopping rule, checked weekly", ""]
    lines += [
        f"`docs/when_this_ends.md` ends this project early if the correction "
        f"grows large enough that a plausible edge could not clear it on a "
        f"season's sample. At **{int(rule.get('looks', 0)):,}** cumulative "
        f"hypotheses the correction is **x{float(rule.get('correction_factor', 1.0)):.2f}**, "
        f"so separating a "
        f"**{float(rule.get('edge', 0.0)):+.0%}** edge from zero needs "
        f"**{int(rule.get('bets_needed_corrected', 0)):,}** bets against "
        f"**{int(rule.get('bets_needed_uncorrected', 0)):,}** uncorrected.",
        "",
    ]
    if rule.get("exhausted"):
        lines += [
            f"**The search has spent its budget.** A season supplies on the "
            f"order of {int(rule.get('season_supply', 0)):,} settled opinions "
            "and the corrected requirement is above that, so continuing is "
            "arithmetic theatre. This is one of the three things "
            "`docs/when_this_ends.md` says ends the project early.",
            "",
        ]
    else:
        lines += [
            f"A season supplies on the order of "
            f"{int(rule.get('season_supply', 0)):,} settled opinions, so there "
            f"is headroom. Against that supply the correction only bites at "
            f"**{int(rule.get('looks_at_which_it_bites', 0)):,}** cumulative "
            "hypotheses — which is the honest shape of a Bonferroni correction "
            "rather than a reassurance: its z grows like the square root of the "
            "log of the family size, so **the cumulative count is not what will "
            "end this project.** The decision date and the sample floor are.",
            "",
            f"Against the {int(rule.get('sample_floor_opinions', 0)):,}-opinion "
            f"floor the correction bites at "
            f"**{int(rule.get('looks_at_which_it_bites_at_the_floor', 0)):,}** "
            "cumulative hypotheses, and that is the number worth watching.",
            "",
        ]
    lines += [
        f"The floor below which the test **did not run** is "
        f"{int(rule.get('sample_floor_opinions', 0)):,} settled opinions across "
        f"{int(rule.get('sample_floor_games', 0)):,} distinct games. Below it "
        "the verdict is not a number.",
        "",
        f"Decision date **{rule.get('decision_date', '')}** — "
        f"{int(rule.get('days_to_decision', 0)):,} days away.",
        "",
        f"This arithmetic assumes {rule.get('assumption', '')}.",
        "",
    ]
    return lines


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------


def record_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name("weekly_loop", ".json")


def report_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name("weekly_loop", ".md")


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--manual-dir", default=str(MANUAL_DIR))
    parser.add_argument(
        "--claims-doc",
        default="",
        help=(
            "The hand-written claims document whose fenced block this loop "
            "re-renders. Empty means the repository's own "
            "docs/what_we_can_and_cannot_claim.md."
        ),
    )
    parser.add_argument(
        "--scripts-dir",
        default=str(Path(__file__).resolve().parent),
        help="Where the sibling scripts this loop drives live.",
    )
    parser.add_argument(
        "--week",
        default="",
        help=(
            "ISO week to spend the alpha budget against, e.g. 2026-W36. "
            "Defaults to today's. The budget's unit is this string."
        ),
    )
    parser.add_argument(
        "--seasons",
        default="",
        help=(
            "Passed through to the refit and the backtest as --seasons. Blank "
            "means each script picks its own default."
        ),
    )
    parser.add_argument(
        "--verify-bets",
        default="",
        help=(
            "A graded-bet CSV to re-run assert_walk_forward over. Absent means "
            "walk-forward is not re-verified here, which is reported as an "
            "absence and never as a pass."
        ),
    )
    parser.add_argument(
        "--timeout-minutes",
        type=int,
        default=120,
        help="Per-subprocess wall clock. A refit that hangs must not hang the loop.",
    )
    parser.add_argument("--python", default="", help="Interpreter for the subprocesses.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Report what the loop would do and write nothing anywhere — no "
            "subprocess, no ledger append, no policy edit, no report. There is "
            "deliberately no flag that turns the demotion check off on its own: "
            "a gate with an off switch is not a gate."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    competition = competition_for(args.competition)
    output_dir = Path(args.output_dir)
    # The hand-written claims document, whose fenced block this loop
    # re-renders. `--claims-doc ''` turns the splice off for a test
    # tree that has no docs/ directory.
    claims_doc = Path(args.claims_doc) if args.claims_doc else (
        Path(__file__).resolve().parents[1] / "docs" / "what_we_can_and_cannot_claim.md"
    )
    processed_dir = Path(args.processed_dir)
    manual_dir = Path(args.manual_dir)
    scripts_dir = Path(args.scripts_dir)
    # Whole seconds, because every record in this repository stamps itself with
    # `timespec="seconds"`. Comparing a second-truncated `generated_at` against
    # a microsecond-precision start time reads a record written 40ms into the
    # run as older than the run — and the freshness check would then report a
    # measurement that had just been made as stale, every single week.
    started_at = datetime.now(timezone.utc).replace(microsecond=0)
    today = started_at.date()
    week = args.week or week_label(today)
    timeout_seconds = max(int(args.timeout_minutes), 1) * 60
    steps: list[Step] = []

    print(f"Weekly refit-and-measure for {competition.title}, week {week}.")
    if args.dry_run:
        print("--dry-run: nothing is written and no subprocess is started.")

    # ---- Step 1: pre-register the week's search, BEFORE anything measures.
    ledger_path = Path(output_dir) / E.LEDGER_FILENAME
    ledger = E.load(ledger_path)
    ledger_before = ledger.count
    correction_before = ledger.correction_factor()
    queue, problems = load_queue(manual_dir / QUEUE_FILENAME, week=week)
    spend = spend_alpha_budget(ledger, queue, week=week, problems=problems)
    if spend.count and not args.dry_run:
        try:
            E.save(ledger, ledger_path)
        except (ValueError, OSError) as exc:
            # `save()` refuses to shrink the ledger. That refusal is the guard
            # working, and it is a fault rather than a degradation: the record
            # of what has been tested is the thing every correction is computed
            # from, so a run that cannot write it must not carry on measuring.
            print(f"::error::{exc}", file=sys.stderr)
            return EXIT_FAULT
        (output_dir / "cbb_experiment_ledger.md").write_text(
            E.render(ledger), encoding="utf-8"
        )
    if spend.refused:
        steps.append(
            Step(
                name="pre-register the week's search",
                status=DEGRADED,
                detail=spend.refused,
            )
        )
    else:
        # A malformed queue entry degrades the run. It is a hypothesis somebody
        # meant to pre-register and this loop did not spend, and the one
        # direction the ledger must never err in is under-counting the search.
        steps.append(
            Step(
                name="pre-register the week's search",
                status=DEGRADED if spend.problems else OK,
                detail=(
                    f"{spend.count} new hypothesis(es) recorded of "
                    f"{spend.remaining_before} available this week; "
                    f"{len(spend.waiting)} waiting."
                    + (
                        " Queue problems: " + "; ".join(spend.problems)
                        if spend.problems
                        else ""
                    )
                ),
            )
        )
    ledger_after = ledger.count
    correction_after = ledger.correction_factor()
    looks = max(ledger_after, 1)

    # ---- Step 2: refit the ratings, walk-forward.
    passthrough = ["--competition", competition.key]
    if args.seasons:
        passthrough += ["--seasons", *args.seasons.split()]
    steps.append(
        run_script(
            REFIT_SCRIPT,
            passthrough,
            scripts_dir=scripts_dir,
            name="refit the ratings walk-forward",
            dry_run=args.dry_run,
            timeout_seconds=timeout_seconds,
            python=args.python,
        )
    )

    # ---- Step 3: the price backtest and its replication.
    #
    # It runs even when the refit did not, on purpose. The backtest over the
    # previously fitted ratings is still a true measurement of those ratings,
    # and the run is already marked degraded so nobody can read it as this
    # week's model. Skipping it as well would turn one missing step into a week
    # with no measurement at all.
    steps.append(
        run_script(
            BACKTEST_SCRIPT,
            passthrough,
            scripts_dir=scripts_dir,
            name="re-run the price backtest and replication",
            dry_run=args.dry_run,
            timeout_seconds=timeout_seconds,
            python=args.python,
        )
    )
    if args.dry_run:
        # Nothing measured, so there is nothing to verify — and reporting a
        # record left over from last week as stale would be a dry run inventing
        # a fault it did not find.
        backtest_summary = {"readable": False, "dry_run": True}
        walk_summary = {"verified": False, "dry_run": True}
        steps.append(
            Step(
                name="verify the backtest record",
                status=SKIPPED,
                detail="--dry-run: no measurement ran, so there is nothing to verify.",
            )
        )
        steps.append(
            Step(
                name="re-verify walk-forward",
                status=SKIPPED,
                detail="--dry-run: no measurement ran, so there is nothing to verify.",
            )
        )
    else:
        verify_step, backtest_summary = verify_backtest_record(
            PB.record_path(competition, output_dir),
            looks_expected=looks,
            started_at=started_at,
            replication_record=WC.replication_path(competition, output_dir),
        )
        steps.append(verify_step)
        walk_step, walk_summary = verify_walk_forward(
            Path(args.verify_bets) if args.verify_bets else None
        )
        steps.append(walk_step)

    # ---- Step 4: re-render the claims report from the run record.
    #
    # `docs/what_we_can_and_cannot_claim.md` is deliberately NOT the file this
    # rewrites. That document was written on 2026-09-01 before the first
    # measurement, and its own first paragraph says the timing is the whole
    # point — a machine that rewrote it every week would destroy the
    # pre-registration it exists to be. The generated claims report is
    # `data/outputs/cbb_what_we_can_claim.md`, which CLAUDE.md pins as the
    # claims output, and that is what is re-rendered from the run record here.
    steps.append(
        run_script(
            CLAIMS_SCRIPT,
            [
                "--competition", competition.key,
                "--output-dir", str(output_dir),
                # DoD 19: the loop re-renders the claims DOC, not only the
                # output report. The doc's framing was written before the first
                # measurement and must stay; only the fenced block moves. A
                # missing fence makes this step fail rather than append, so a
                # document that looks updated and is not cannot be produced.
                "--splice-into", str(claims_doc),
            ],
            scripts_dir=scripts_dir,
            name="re-render the claims report from its run record",
            dry_run=args.dry_run,
            timeout_seconds=timeout_seconds,
            python=args.python,
        )
    )

    # ---- Step 5: auto-demotion.
    policy = staging.load(manual_dir)
    forward_summary = {"rows": 0, "bets": 0, "threshold": fe.BET_EDGE_THRESHOLD}
    findings: list[DemotionFinding] = []
    ledger_csv = processed_dir / fe.LEDGER_FILENAME
    try:
        criteria = promotion.load_criteria(competition, manual_dir=manual_dir)
    except (promotion.PromotionError, KeyError, ValueError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_FAULT
    try:
        # Strict, following `docs/decision_log.md` #19: a damaged ledger read
        # leniently reads back as zero rows, and zero rows means "no market has
        # enough evidence to withdraw" — a gate that fails open because a file
        # was corrupt.
        ledger_frame = stores.read_store(
            ledger_csv, columns=fe.LEDGER_COLUMNS, for_append=True
        )
    except stores.CorruptStoreError as exc:
        steps.append(
            Step(
                name="check for auto-demotion",
                status=FAILED,
                detail=(
                    f"the forward ledger at {ledger_csv.name} could not be read: "
                    f"{exc} No demotion was judged, because a demotion judged on "
                    "an unreadable ledger is judged on nothing."
                ),
            )
        )
    else:
        bets = measurable_bets(ledger_frame, competition)
        forward_summary = {
            "rows": int(len(ledger_frame)),
            "bets": int(len(bets)),
            "threshold": fe.BET_EDGE_THRESHOLD,
        }
        findings = check_for_demotion(
            policy=policy, criteria=criteria, bets=bets, looks=looks
        )
        withdrawing = [f for f in findings if f.withdraw]
        if not findings:
            steps.append(
                Step(
                    name="check for auto-demotion",
                    status=SKIPPED,
                    detail=(
                        "no market is allowlisted, so there is nothing to "
                        "withdraw. That is the correct state for a lab with no "
                        "signed receipt."
                    ),
                )
            )
        elif not withdrawing:
            steps.append(
                Step(
                    name="check for auto-demotion",
                    status=OK,
                    detail=(
                        f"{len(findings)} allowlisted market(s) checked against "
                        "the floor their receipts declared; none has fallen "
                        "through it."
                    ),
                )
            )
        else:
            for finding in withdrawing:
                if not args.dry_run:
                    staging.withdraw(
                        policy,
                        finding.market,
                        reason=finding.reason,
                        at=started_at.isoformat(timespec="seconds"),
                    )
            if not args.dry_run:
                staging.save(policy, manual_dir)
            steps.append(
                Step(
                    name="check for auto-demotion",
                    status=DEGRADED,
                    detail=(
                        f"{len(withdrawing)} market(s) withdrawn: "
                        + ", ".join(f.market for f in withdrawing)
                        + ". This run holds `contents: read` in Actions and "
                        "cannot push, so the edited policy is in this run's "
                        "artifact and has to be committed before the card stops "
                        "reading the market."
                    ),
                )
            )

    # ---- Step 6: the stopping rule.
    stopping = stopping_rule(ledger, today=today)
    steps.append(
        Step(
            name="check the stopping rule",
            status=DEGRADED if stopping["exhausted"] else OK,
            detail=(
                (
                    "the correction has grown past the point where a "
                    f"{stopping['edge']:+.0%} edge could clear on a season's "
                    "sample; `docs/when_this_ends.md` says that ends the "
                    "project"
                )
                if stopping["exhausted"]
                else (
                    f"x{stopping['correction_factor']:.2f} over "
                    f"{stopping['looks']:,} looks; a {stopping['edge']:+.0%} "
                    f"edge needs {stopping['bets_needed_corrected']:,} bets, "
                    f"which is inside a season's supply until "
                    f"{stopping['looks_at_which_it_bites']:,} looks and inside "
                    f"the {stopping['sample_floor_opinions']:,}-opinion floor "
                    f"until "
                    f"{stopping['looks_at_which_it_bites_at_the_floor']:,}"
                )
            ),
        )
    )

    record = build_record(
        competition=competition,
        week=week,
        started_at=started_at,
        steps=steps,
        spend=spend,
        ledger_before=ledger_before,
        ledger_after=ledger_after,
        correction_before=correction_before,
        correction_after=correction_after,
        backtest=backtest_summary,
        walk_forward=walk_summary,
        findings=findings,
        stopping=stopping,
        forward=forward_summary,
        policy_summary=policy.summary_line(competition),
        dry_run=bool(args.dry_run),
    )
    rendered = render(record)
    if not args.dry_run:
        output_dir.mkdir(parents=True, exist_ok=True)
        record_path(competition, output_dir).write_text(
            json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8"
        )
        report_path(competition, output_dir).write_text(rendered, encoding="utf-8")
        print(f"Wrote {report_path(competition, output_dir)} from its run record.")

    print()
    for step in steps:
        print(f"  [{step.status:>8}] {step.name}: {step.detail}")
        for line in step.lines:
            print(f"             {line}")
    print()
    print(
        f"Experiment ledger: {ledger_before:,} distinct hypotheses before, "
        f"{ledger_after:,} after. Correction x{correction_before:.2f} -> "
        f"x{correction_after:.2f}."
    )
    if ledger_after > ledger_before and not args.dry_run:
        # The loop's own measurement in THIS run is correct either way: the
        # ledger is written before the backtest reads it, so the correction the
        # backtest applies is the post-append count. What an uncommitted append
        # costs is next week — the same slots are spent again, and the repository
        # copy of the record of what has been tested lags the truth.
        print(
            f"::warning::The experiment ledger grew by "
            f"{ledger_after - ledger_before}. This loop's workflow holds "
            "`contents: read` and cannot push, so the updated ledger is in the "
            "run artifact. Commit it, or the same slots are spent again next "
            "week and the committed record of what this lab has tested stays "
            "smaller than the truth."
        )
    print(
        "This run allowlisted no market, signed no receipt, placed no bet and "
        "spent no credit."
    )

    # Every reason this run is not clean is printed, and only then is one exit
    # code chosen. A run that both withdrew a market and lost a step has two
    # things wrong with it, and returning early would have reported one.
    withdrawn = [f for f in findings if f.withdraw]
    if withdrawn:
        print(
            "::error::"
            + ", ".join(f.market for f in withdrawn)
            + " was withdrawn from the allowlist. This workflow cannot push, so "
            "the edited policy is in the run artifact and the card keeps reading "
            "the market until somebody commits it."
        )
    unhealthy = [step for step in steps if not step.healthy]
    if unhealthy:
        print(
            "::error::This run was degraded: "
            + ", ".join(f"{s.name} ({s.status})" for s in unhealthy),
            file=sys.stderr,
        )
    if withdrawn:
        return EXIT_DEMOTION_PENDING
    if unhealthy:
        return EXIT_DEGRADED
    print("Clean run.")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
