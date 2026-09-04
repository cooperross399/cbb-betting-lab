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

Three things, each because the football lab recorded a defect that this closes.

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

## Why append-only, and how it is enforced (and how it was not)

The tempting edit is to drop the tests that failed, on the reasoning that they
were exploratory. That reasoning is exactly backwards: the failed tests are
what make the surviving one unlikely to be chance. A ledger that can shrink is
a ledger that will, one honest-seeming commit at a time, and the correction it
reports afterwards is smaller than the truth.

This section used to be titled "Why append-only, enforced", and until
2026-09-04 it was not. `save()` refused to shrink the ledger by re-reading the
file it was about to overwrite, and every caller loads from that file, mutates,
and saves back to it — so the comparison was the same count against itself.
Reproduced on this lab's tracked ledger: twelve of thirty hypotheses deleted by
hand, `scripts/record_experiments.py` re-run, the printed correction fell from
x1.60 to x1.46, and nothing raised. Three things enforce it now: `save()`
takes the count the caller LOADED as a required `floor`;
`scripts/check_ledger_append_only.py` compares the ledger on a PR's head
against its base, keyed on `Hypothesis.key()`, in the `Ledger Guard` workflow;
and `tests/test_check_ledger_append_only.py` holds both to the reproduction.

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

#: Which half of the data a hypothesis was put to. Declared when the hypothesis
#: is written, never after the number is seen.
STAGES: frozenset[str] = frozenset({"discovery", "holdout"})


class DirectionRequired(ValueError):
    """Raised when a hypothesis is recorded without a falsifiable direction."""


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
        if self.predicted_direction not in DIRECTIONS:
            raise DirectionRequired(
                f"Hypothesis {self.name!r} in search {self.search!r} declares "
                f"predicted_direction={self.predicted_direction!r}. It must be "
                f"one of {sorted(DIRECTIONS)}. The football lab spent three of "
                "twelve pre-registered slots on cuts written without a "
                "direction, which could therefore only ever be exploratory; "
                "this raises so that cannot happen again."
            )
        if self.stage not in STAGES:
            raise ValueError(
                f"Hypothesis {self.name!r} declares stage={self.stage!r}; it "
                f"must be one of {sorted(STAGES)}."
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
        return self.realised_direction != self.predicted_direction


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

    @property
    def count(self) -> int:
        """Distinct hypotheses ever tested. The family size for any new claim."""
        return len({h.key() for h in self.hypotheses})

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
        """Add hypotheses. Returns how many were new."""
        seen = {h.key() for h in self.hypotheses}
        added = 0
        for entry in hypotheses:
            if entry.key() in seen:
                continue
            seen.add(entry.key())
            self.hypotheses.append(entry)
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
    )


def save(ledger: ExperimentLedger, path: Path, *, floor: int) -> Path:
    """Write the ledger, refusing to shrink it below `floor`.

    `floor` is the entry count the caller LOADED, before it mutated anything,
    and it is required rather than defaulted because the previous signature
    was a guard that could not fire. It re-read the file it was about to
    overwrite and compared the in-memory count against that — and every
    caller in this repository loads the ledger from `path`, mutates it, and
    saves it back to `path`, so the two counts were the same object's count
    twice. Reproduced on this lab: twelve of thirty tracked hypotheses
    deleted by hand, the recorder re-run, the printed correction fell from
    x1.60 to x1.46, and this function raised nothing. The comparison has to be
    against a number the caller held BEFORE the edit, which only the caller
    can supply.

    The re-read is kept as a second net for the one shape it can see — a
    caller that loaded from one path and saves to another — and
    `scripts/check_ledger_append_only.py` is the third, at the PR diff. The
    tempting edit is to drop the tests that failed because they were
    "exploratory"; the failed tests are precisely what make a surviving one
    unlikely to be chance. This raises rather than warns, because a warning
    in a workflow log is not a guard.
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
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "alpha_budget": {
                    "per_week": ledger.budget.per_week,
                    "declared_on": ledger.budget.declared_on,
                    "rationale": ledger.budget.rationale,
                },
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
        add(f"| {search} | {n} |")
    add("")
    add("| # | Search | Hypothesis | Stage | Predicted | Realised | Seasons | Tested | Outcome |")
    add("|---:|:---|:---|:---|:---|:---|:---|:---|:---|")
    for i, h in enumerate(ledger.hypotheses, start=1):
        seasons = ", ".join(str(s) for s in h.seasons) or "—"
        realised = h.realised_direction or "—"
        if h.reversed_prediction():
            realised = f"**{realised} (reversed)**"
        add(
            f"| {i} | {h.search} | {h.name} | {h.stage} | "
            f"{h.predicted_direction} | {realised} | {seasons} | {h.tested_on} | "
            f"{h.outcome} |"
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
