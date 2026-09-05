"""Every hypothesis this lab has ever tested, and the correction that implies.

Ported from `../football-betting-lab/src/football_betting_lab/experiment_ledger.py`,
which says the thing this file exists for better than a paraphrase would:

**A search that runs every week is not twelve tests. It is twelve tests a week,
forever.** Correcting a week's findings across "the twelve things I tested
today" is a lie if twelve more were tested last week and twelve more the week
before. Over a season that is hundreds of looks, and at a nominal 5% threshold
roughly one in twenty of them clears by chance alone. An automated edge-hunter
without a cumulative tally does not find edges; it manufactures them on a
schedule, and it manufactures them with clean intervals and good prose.

So this is an **append-only** record of every hypothesis ever put to the data,
across every search, and the correction factor it hands back grows with the
count. The fiftieth test does not get the first test's benefit of the doubt.

College basketball makes this more urgent, not less. The reason to build a
fourth lab is sample size — roughly 5,600 games a season against the NFL's 272
— and a large sample is exactly what makes a search feel safe. It is not. A
larger n narrows every interval, including the intervals of the hypotheses that
are wrong, so the same 5% of them clear and each one clears with a tighter
interval and a better story. Sample size buys *power*, never *innocence*.

## What this file adds to the football lab's version

Four things. The first three are each because the football lab recorded a
defect that this closes; the fourth is because the player-prop pre-registration
of 2026-09-05 needed to declare seven quantities as descriptive-only and there
was nowhere honest to put them.

1. **A predicted direction is mandatory.** The football lab's pre-registered
   subgroup search wrote three of its twelve hypotheses with no predicted
   direction, "so they could not be falsified by direction and three slots were
   spent on cuts that could only ever be exploratory". A `Hypothesis` here
   cannot be constructed without one. Four of that lab's mechanisms reversed
   outright, and knowing they reversed is worth more than the null result —
   which is only possible because a direction was written down first.

2. **A declared alpha budget.** N new hypotheses per week, declared in advance.
   When the budget is spent, the search waits. It never lowers the bar. The
   budget is a *rate limit on degrees of freedom*, and it is the difference
   between a lab that searches and a lab that fishes.

3. **Discovery and holdout are separated in advance**, on the hypothesis
   itself, so a result found in discovery cannot quietly be reported as though
   it had been validated. The holdout is not looked at until discovery closes.

4. **Descriptive-only is a declaration with a gate behind it.** A run prints
   numbers that are not tests of anything — an over/under split, a refusal
   census, an unapplied diagnostic column — and correcting for those would
   widen every real interval in exchange for no protection at all. So they are
   exempt, and :class:`DescriptiveOnly` records the exemption **in the ledger**
   rather than in a design document nobody diffs. What makes that a trade
   instead of a loophole is that it runs both ways: `record()` raises
   :class:`PromotionRefused` on a hypothesis carrying a declared name, `save()`
   refuses to drop a declaration, and `scripts/check_ledger_append_only.py`
   sees both at the diff. A number that paid no correction may not become a
   finding once it turns out flattering, and that is the only moment anybody
   would ever want it to.

## Why append-only, and how it is enforced (and how it was not)

The tempting edit is to drop the tests that failed, on the reasoning that they
were exploratory. That reasoning is exactly backwards: the failed tests are
what make the surviving one unlikely to be chance. A ledger that can shrink is
a ledger that will, one honest-seeming commit at a time, and the correction it
reports afterwards is smaller than the truth.

This section used to be titled "Why append-only, enforced", and it described a
reproduction that does not happen. **That description was wrong, and correcting
it is the point of this paragraph.** It said `save()`'s re-read of the file
"could never fire" and that deleting twelve of thirty hypotheses and re-running
the recorder dropped the correction from x1.60 to x1.46. Re-measured on
2026-09-04, on the tracked 30-entry ledger, against `save()` exactly as it
stood on 02e75b7:

- The old re-read **does** fire on an in-process shrink. Load 30, delete twelve
  in memory, save back to the same path: `ValueError: The experiment ledger
  would fall from 30 entries to 18.` The file still held 30 at comparison time.
- The recorder **self-heals**. Cut the tracked ledger to 18 entries on disk and
  run `scripts/record_experiments.py` at 02e75b7: it prints *"18 distinct
  hypotheses before, 30 after (12 new)"* and *"x1.60"*, because `record()`
  re-adds every hypothesis in `HYPOTHESES`. The correction never fell.
- The arithmetic did not match the edit either. `correction_factor` is x1.46 at
  **12** hypotheses and x1.53 at 18, and deleting twelve of thirty leaves 18.

What the old code really could not see is a ledger **edited on disk and
committed**: `save()` is never called on that path, so no runtime guard is
reached, and every report then reads the shorter file and quotes the smaller
correction. Three things enforce it now: `save()` takes the count the caller
LOADED as a required `floor`, which the re-read cannot supply when a caller
writes to a path that does not yet exist; `scripts/check_ledger_append_only.py`
compares the ledger on a PR's head against its base, keyed on
`Hypothesis.key()`, in the `Ledger Guard` workflow, which is the layer that
sees a committed edit; and `tests/test_check_ledger_append_only.py` runs the
old comparison itself and pins both what it caught and what it did not.

## What this is not

It is not a substitute for a held-out season. A correction widens an interval;
it cannot tell you whether a result reproduces. Replication remains the bar.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from statistics import NormalDist

#: The file, under `data/outputs/` like every other record the lab keeps.
LEDGER_FILENAME = "experiment_ledger.json"

#: The nominal two-sided level every interval in this lab is quoted at.
ALPHA = 0.05

#: A hypothesis must predict which way it will go. `higher` and `lower` are
#: about the quantity the hypothesis names; `none` is not an option, and that
#: is the point — see the module docstring.
DIRECTIONS: frozenset[str] = frozenset({"higher", "lower"})

#: The one undirected look this ledger admits, and only at the holdout stage.
#:
#: The replication scores EVERY discovery cell on the held-out season — the
#: cells the discovery window claimed nothing in included, because a cell that
#: lights up only on the holdout is *"a NEW DISCOVERY made on the only clean
#: season this lab had"* and the module has to look at it to say so. That look
#: reads an interval, so it spends a degree of freedom, and until 2026-09-05 it
#: was not written down: `run_replication.record_holdout_looks` appended a
#: hypothesis only where discovery had claimed, so a run over 32 cells with 5
#: claims recorded 5 looks and took 32. The family correction was short by
#: exactly the looks nobody wrote down.
#:
#: There is no discovery sign to carry into such a cell, so its hypothesis is
#: two-sided: *the held-out return differs from zero*. That is falsifiable — an
#: interval that includes zero fails it — but it cannot *reverse*, and
#: :meth:`Hypothesis.reversed_prediction` says so. It is NOT `none`: it is
#: refused at the discovery stage, where a cut written without a direction is
#: the football lab's exploratory slot wearing a pre-registration's clothes.
TWO_SIDED = "either"

#: Which half of the data a hypothesis was put to. Declared when the hypothesis
#: is written, never after the number is seen.
STAGES: frozenset[str] = frozenset({"discovery", "holdout"})


class DirectionRequired(ValueError):
    """Raised when a hypothesis is recorded without a falsifiable direction."""


class PromotionRefused(ValueError):
    """Raised when a quantity declared descriptive-only is recorded as a test.

    The whole worth of a descriptive-only declaration is that it costs nothing
    *and* buys nothing. A number that pays no correction may not later be read
    as a finding, because the correction the finding would need was never paid
    — and the moment to notice that is when somebody writes the hypothesis, not
    when the report quotes it.
    """


@dataclass(frozen=True)
class Hypothesis:
    """One thing that was put to the data, once.

    `predicted_direction` is required and validated. A hypothesis without a
    direction cannot be wrong in a way anybody notices, and a search made of
    those is a search that always succeeds.
    """

    search: str
    name: str
    tested_on: str
    seasons: tuple[int, ...]
    outcome: str
    predicted_direction: str = ""
    stage: str = "discovery"
    realised_direction: str = ""

    def __post_init__(self) -> None:
        if self.stage not in STAGES:
            raise ValueError(
                f"Hypothesis {self.name!r} declares stage={self.stage!r}; it "
                f"must be one of {sorted(STAGES)}."
            )
        two_sided_holdout = (
            self.predicted_direction == TWO_SIDED and self.stage == "holdout"
        )
        if self.predicted_direction not in DIRECTIONS and not two_sided_holdout:
            raise DirectionRequired(
                f"Hypothesis {self.name!r} in search {self.search!r} declares "
                f"predicted_direction={self.predicted_direction!r} at stage "
                f"{self.stage!r}. It must be one of {sorted(DIRECTIONS)}, or "
                f"{TWO_SIDED!r} at the holdout stage only — the one undirected "
                "look this ledger admits, for a held-out cell the discovery "
                "window claimed nothing in. The football lab spent three of "
                "twelve pre-registered slots on cuts written without a "
                "direction, which could therefore only ever be exploratory; "
                "this raises so that cannot happen again."
            )

    def key(self) -> tuple[str, str, tuple[int, ...], str]:
        """What makes two entries the same test.

        The same hypothesis re-run on the same seasons at the same stage is one
        degree of freedom, not two — re-running a script must not inflate the
        correction, or nobody will re-run anything. The stage is part of the
        key because putting a discovery finding to the holdout **is** a second
        look, and the whole design collapses if it is not counted as one.
        """
        return (self.search, self.name, self.seasons, self.stage)

    def reversed_prediction(self) -> bool:
        """True when the data went the opposite way from the prediction.

        A reversal is a result, not a failure. Four of the football lab's
        mechanisms reversed outright and the report said so; that is only
        sayable because a direction was written down beforehand.
        """
        if not self.realised_direction:
            return False
        if self.predicted_direction == TWO_SIDED:
            # A two-sided look predicted no sign, so no sign can contradict it.
            # It can fail (an interval including zero) but never reverse.
            return False
        return self.realised_direction != self.predicted_direction


@dataclass(frozen=True)
class DescriptiveOnly:
    """A quantity that will be computed and printed but never read as a finding.

    Some of what a run prints is not a test of anything. The over/under split
    inside a cell is a mandatory disclosure; a refusal census is a description
    of what the model declined to price; an unapplied diagnostic column exists
    so a later session inherits the evidence rather than the temptation. None
    of them is a claim about edge, so none of them spends a degree of freedom,
    and correcting for them would widen every real interval in exchange for
    nothing.

    That exemption is only honest while it holds in both directions, which is
    what this class is for. A declaration recorded here **cannot** be recorded
    as a :class:`Hypothesis`: :meth:`ExperimentLedger.record` raises
    :class:`PromotionRefused` on a matching ``(search, name)``. Reading a
    descriptive number as a finding afterwards is exactly the move the family
    correction exists to stop — it is a look that was never counted, promoted
    once the number turned out to be flattering — and a promise in a design
    document is not a guard.

    It is a declaration, not a measurement, so it carries no direction, no
    stage and no outcome. Those fields would be lies here: there is nothing
    for it to be right or wrong about.
    """

    search: str
    name: str
    declared_on: str
    rationale: str = ""

    def key(self) -> tuple[str, str]:
        """What makes two declarations the same quantity.

        Deliberately NOT the hypothesis key: no seasons and no stage. A
        descriptive number re-printed on another season or against the holdout
        is the same descriptive number, and — more to the point — a hypothesis
        must not be able to slip past the refusal by changing its seasons.
        """
        return (self.search, self.name)


@dataclass(frozen=True)
class AlphaBudget:
    """How many new hypotheses a week the search may spend.

    Declared on disk, beside the ledger. When the budget is spent the search
    waits for the next week; it never lowers the bar, and it never borrows
    against a future week. Both of those are how a rate limit becomes a
    formality.
    """

    per_week: int = 6
    declared_on: str = ""
    rationale: str = ""


@dataclass
class ExperimentLedger:
    hypotheses: list[Hypothesis] = field(default_factory=list)
    budget: AlphaBudget = field(default_factory=AlphaBudget)
    #: Quantities declared descriptive-only. They are NOT in `count` and do not
    #: widen anything; see :class:`DescriptiveOnly` for why that is only honest
    #: because `record()` refuses to promote one.
    descriptive_only: list[DescriptiveOnly] = field(default_factory=list)

    @property
    def count(self) -> int:
        """Distinct hypotheses ever tested. The family size for any new claim.

        Descriptive-only declarations are excluded on purpose: they cannot
        produce a finding, so they cannot produce a false one, so making every
        real interval wider on their account would be a cost with no protection
        bought. `record()` is what keeps that trade honest.
        """
        return len({h.key() for h in self.hypotheses})

    def descriptive_only_keys(self) -> set[tuple[str, str]]:
        return {d.key() for d in self.descriptive_only}

    def correction_factor(self, *, extra: int = 0) -> float:
        """How much wider a 95% interval has to be, given everything ever tested.

        Bonferroni on the cumulative count. Conservative on purpose: the
        alternatives (Holm, Benjamini-Hochberg) need the full set of p-values
        to be in hand at once, and this lab's tests arrive one week at a time
        over a season. A correction that can be computed incrementally and is
        slightly too wide beats one that is exactly right and cannot be
        computed until the season is over.
        """
        families = max(self.count + extra, 1)
        if families == 1:
            return 1.0
        return NormalDist().inv_cdf(1 - (ALPHA / families) / 2) / 1.96

    def record(self, *hypotheses: Hypothesis) -> int:
        """Add hypotheses. Returns how many were new.

        Raises :class:`PromotionRefused` for a hypothesis whose
        ``(search, name)`` was declared descriptive-only. That is the guard
        that makes the descriptive-only exemption a trade rather than a
        loophole: a quantity exempted from the correction on the grounds that
        it can never be a finding cannot afterwards become one.
        """
        exempt = self.descriptive_only_keys()
        for entry in hypotheses:
            if (entry.search, entry.name) in exempt:
                raise PromotionRefused(
                    f"{entry.name!r} in search {entry.search!r} was declared "
                    "descriptive-only, so it paid no family correction and may "
                    "not now be recorded as a hypothesis. Promoting it would "
                    "read a look nobody counted as a finding — which is the "
                    "move the correction exists to stop, and it is always "
                    "tempting for exactly the numbers that came out well. If "
                    "the quantity really is a test, it has to be pre-registered "
                    "as one BEFORE it is measured, under a name that was never "
                    "declared descriptive-only."
                )
        seen = {h.key() for h in self.hypotheses}
        added = 0
        for entry in hypotheses:
            if entry.key() in seen:
                continue
            seen.add(entry.key())
            self.hypotheses.append(entry)
            added += 1
        return added

    def declare(self, *descriptive: DescriptiveOnly) -> int:
        """Declare quantities as descriptive-only. Returns how many were new.

        Refuses a name already recorded as a hypothesis, for the same reason in
        the other direction: a test that has been put to the data cannot be
        reclassified as a description afterwards, which would drop it out of
        the family and narrow every interval already quoted against it.
        """
        recorded = {(h.search, h.name) for h in self.hypotheses}
        seen = self.descriptive_only_keys()
        added = 0
        for entry in descriptive:
            if entry.key() in recorded:
                raise PromotionRefused(
                    f"{entry.name!r} in search {entry.search!r} is already "
                    "recorded as a hypothesis. It cannot be re-declared "
                    "descriptive-only: that would take a counted look back out "
                    "of the family and narrow every interval quoted against it."
                )
            if entry.key() in seen:
                continue
            seen.add(entry.key())
            self.descriptive_only.append(entry)
            added += 1
        return added

    def spent_in(self, week: str) -> int:
        """New hypotheses recorded on a given date string (the budget's unit)."""
        return len({h.key() for h in self.hypotheses if h.tested_on == week})

    def budget_remaining(self, week: str) -> int:
        return max(self.budget.per_week - self.spent_in(week), 0)

    def by_search(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for entry in self.hypotheses:
            counts[entry.search] = counts.get(entry.search, 0) + 1
        return counts

    def reversals(self) -> list[Hypothesis]:
        return [h for h in self.hypotheses if h.reversed_prediction()]

    def by_stage(self) -> dict[str, int]:
        counts: dict[str, int] = {"discovery": 0, "holdout": 0}
        for entry in self.hypotheses:
            counts[entry.stage] = counts.get(entry.stage, 0) + 1
        return counts


def load(path: Path) -> ExperimentLedger:
    """The ledger, or an empty one. An absent file is a lab that has tested
    nothing, which is a true statement about a fresh clone."""
    if not Path(path).is_file():
        return ExperimentLedger()
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    budget_payload = payload.get("alpha_budget", {}) or {}
    return ExperimentLedger(
        hypotheses=[
            Hypothesis(
                search=str(e.get("search", "")),
                name=str(e.get("name", "")),
                tested_on=str(e.get("tested_on", "")),
                seasons=tuple(int(s) for s in e.get("seasons", [])),
                outcome=str(e.get("outcome", "")),
                predicted_direction=str(e.get("predicted_direction", "")),
                stage=str(e.get("stage", "discovery")),
                realised_direction=str(e.get("realised_direction", "")),
            )
            for e in payload.get("hypotheses", [])
        ],
        budget=AlphaBudget(
            per_week=int(budget_payload.get("per_week", 6) or 6),
            declared_on=str(budget_payload.get("declared_on", "")),
            rationale=str(budget_payload.get("rationale", "")),
        ),
        # Absent in a ledger written before the field existed, which is a
        # ledger that declared nothing descriptive-only rather than one whose
        # declarations were lost.
        descriptive_only=[
            DescriptiveOnly(
                search=str(d.get("search", "")),
                name=str(d.get("name", "")),
                declared_on=str(d.get("declared_on", "")),
                rationale=str(d.get("rationale", "")),
            )
            for d in payload.get("descriptive_only", []) or []
        ],
    )


def save(ledger: ExperimentLedger, path: Path, *, floor: int) -> Path:
    """Write the ledger, refusing to shrink it below `floor`.

    `floor` is the entry count the caller LOADED, before it mutated anything.

    This docstring used to say the previous signature "could not fire", and
    that was false. Measured 2026-09-04 against `save()` as it stood on
    02e75b7: load the tracked 30-entry ledger, delete twelve in memory, save
    back to the same path, and the re-read raised — the file still held 30
    when it was compared. What the re-read cannot see is a save to a path
    that does not yet hold the ledger, where there is nothing to re-read; and
    it is never reached at all by a ledger edited on disk and committed,
    which is the layer `scripts/check_ledger_append_only.py` covers at the PR
    diff. `floor` is required rather than defaulted so the caller cannot
    quietly stop supplying the one number the re-read cannot reconstruct.

    Both comparisons are kept: the floor first, then the re-read, because
    they fail on different edits. The tempting edit is to drop the tests that
    failed because they were "exploratory"; the failed tests are precisely
    what make a surviving one unlikely to be chance. This raises rather than
    warns, because a warning in a workflow log is not a guard.
    """
    target = Path(path)
    if floor < 0:
        raise ValueError(f"floor must be the count the caller loaded, not {floor}")
    if len(ledger.hypotheses) < floor:
        raise ValueError(
            f"The experiment ledger would fall from {floor} entries (the count "
            f"loaded) to {len(ledger.hypotheses)}. It is append-only: the tests "
            "that failed are what make a surviving one unlikely to be chance, "
            "and a ledger that can shrink reports a correction smaller than the "
            "truth."
        )
    if target.is_file():
        existing = load(target)
        if len(ledger.hypotheses) < len(existing.hypotheses):
            raise ValueError(
                f"The experiment ledger would fall from "
                f"{len(existing.hypotheses)} entries on disk to "
                f"{len(ledger.hypotheses)}. It is append-only."
            )
        # A descriptive-only declaration is append-only for the same reason a
        # hypothesis is, and for one more: it is the ONLY thing stopping the
        # quantity it names from being recorded as a test after the number is
        # seen. Delete the declaration and the refusal in `record()` has
        # nothing to refuse.
        if len(ledger.descriptive_only) < len(existing.descriptive_only):
            raise ValueError(
                f"The descriptive-only declarations would fall from "
                f"{len(existing.descriptive_only)} on disk to "
                f"{len(ledger.descriptive_only)}. They are append-only: each "
                "one is what stops the quantity it names from being promoted "
                "to a finding it never paid a correction for."
            )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "alpha_budget": {
                    "per_week": ledger.budget.per_week,
                    "declared_on": ledger.budget.declared_on,
                    "rationale": ledger.budget.rationale,
                },
                "descriptive_only": [
                    {
                        "search": d.search,
                        "name": d.name,
                        "declared_on": d.declared_on,
                        "rationale": d.rationale,
                    }
                    for d in ledger.descriptive_only
                ],
                "hypotheses": [
                    {
                        "search": h.search,
                        "name": h.name,
                        "tested_on": h.tested_on,
                        "seasons": list(h.seasons),
                        "outcome": h.outcome,
                        "predicted_direction": h.predicted_direction,
                        "stage": h.stage,
                        "realised_direction": h.realised_direction,
                    }
                    for h in ledger.hypotheses
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return target


def _md(text: str) -> str:
    """One markdown table cell.

    A pipe inside a cell ends the cell. `calibration by |z| bucket` is a real
    declared quantity — |z| is the edge statistic and naming it any other way
    would be a euphemism — and unescaped it silently split its row into extra
    columns, so the rendered table showed a different rationale beside a
    different name.
    """
    return str(text).replace("|", "\\|")


def render(ledger: ExperimentLedger) -> str:
    lines: list[str] = []
    add = lines.append
    add("# Everything this lab has ever tested")
    add("")
    add(
        "**A search that runs every week is not twelve tests. It is twelve "
        "tests a week, forever.** Correcting today's findings across today's "
        "twelve is a lie if twelve more were tested last week. At a nominal 5% "
        "threshold roughly one look in twenty clears by chance, so an "
        "automated edge-hunter without a cumulative tally does not find edges "
        "— it manufactures them on a schedule, with clean intervals and good "
        "prose."
    )
    add("")
    add(
        "College basketball's large sample makes this **more** urgent, not "
        "less. A bigger n narrows every interval, including the intervals of "
        "the hypotheses that are wrong. Sample size buys power, never "
        "innocence."
    )
    add("")
    if not ledger.hypotheses:
        add(
            "**Nothing has been recorded yet.** That is a true statement about "
            "a fresh clone and a false one about a lab that has measured "
            "anything; if you are seeing it beside a measurement, the ledger "
            "did not load."
        )
        return "\n".join(lines) + "\n"

    factor = ledger.correction_factor()
    stages = ledger.by_stage()
    add(
        f"**{ledger.count} distinct hypotheses tested.** Any new 95% interval "
        f"must be widened by **x{factor:.2f}** before it means what it says."
    )
    add("")
    add(
        f"**Alpha budget: {ledger.budget.per_week} new hypotheses a week**, "
        f"declared {ledger.budget.declared_on or '—'}. "
        f"{ledger.budget.rationale}".rstrip()
    )
    add("")
    add(
        f"**{stages.get('discovery', 0)} discovery, "
        f"{stages.get('holdout', 0)} holdout.** Putting a discovery finding to "
        "the holdout is a second look and is counted as one."
    )
    add("")
    reversals = ledger.reversals()
    if reversals:
        add(
            f"**{len(reversals)} predictions reversed outright.** A reversal is "
            "a result, not a failure — and it is only sayable because a "
            "direction was written down before the number was seen."
        )
        add("")
    add("| Search | Hypotheses |")
    add("|:---|---:|")
    for search, n in sorted(ledger.by_search().items(), key=lambda kv: -kv[1]):
        add(f"| {_md(search)} | {n} |")
    add("")
    add("| # | Search | Hypothesis | Stage | Predicted | Realised | Seasons | Tested | Outcome |")
    add("|---:|:---|:---|:---|:---|:---|:---|:---|:---|")
    for i, h in enumerate(ledger.hypotheses, start=1):
        seasons = ", ".join(str(s) for s in h.seasons) or "—"
        realised = h.realised_direction or "—"
        if h.reversed_prediction():
            realised = f"**{realised} (reversed)**"
        add(
            f"| {i} | {_md(h.search)} | {_md(h.name)} | {_md(h.stage)} | "
            f"{_md(h.predicted_direction)} | {realised} | {seasons} | "
            f"{_md(h.tested_on)} | {_md(h.outcome)} |"
        )
    add("")
    if ledger.descriptive_only:
        add(
            f"## {len(ledger.descriptive_only)} quantities declared "
            "descriptive-only"
        )
        add("")
        add(
            "**These cost no hypotheses and may never be reported as a "
            "finding.** They are computed and printed because a run that hides "
            "its own diagnostics is worse than one that shows them, and they "
            "pay no family correction because none of them is a claim about "
            "edge. That exemption is enforced rather than promised: "
            "`ExperimentLedger.record()` raises `PromotionRefused` on a "
            "hypothesis carrying one of these names, and `save()` refuses to "
            "drop a declaration — because deleting the declaration is how the "
            "refusal would be got around. Promoting one after the fact would "
            "read a look nobody counted as a result, and the temptation to do "
            "it arrives with exactly the numbers that came out well."
        )
        add("")
        add("| Search | Quantity | Declared | Why it can never be a finding |")
        add("|:---|:---|:---|:---|")
        for d in ledger.descriptive_only:
            add(
                f"| {_md(d.search)} | {_md(d.name)} | "
                f"{_md(d.declared_on) or '—'} | {_md(d.rationale)} |"
            )
        add("")
    add(
        "The correction is Bonferroni on the cumulative count — conservative on "
        "purpose. Holm and Benjamini-Hochberg need every p-value in hand at "
        "once, and this lab's tests arrive one week at a time over a season. A "
        "correction that can be computed incrementally and is slightly too wide "
        "beats one that is exactly right and cannot be computed until the "
        "season is over."
    )
    add("")
    add(
        "**This is not a substitute for a held-out season.** A correction "
        "widens an interval; it cannot tell you whether a result reproduces. "
        "Replication remains the bar."
    )
    return "\n".join(lines) + "\n"
