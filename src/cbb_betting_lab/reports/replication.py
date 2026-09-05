"""The held-out season, and the one thing a backtest cannot do for itself.

`price_backtest.py` ends by naming this module and stating its whole
specification in one sentence:

> *It cannot replicate itself. A held-out season is `replication.py`'s job, and
> a window that merely fails to contradict is not confirmation.*

Both halves matter. The first is why the module exists at all: the backtest
chose its rule on the same seasons it scored the rule on, and no amount of
correction inside that window turns a selected result into a validated one. The
second is the bar, and it is the bar because a sibling lab lowered it.

## A window that merely fails to contradict is not confirmation

The NHL lab's `blocked_shots` result is the receipt. A market was selected in
discovery, put to a second window, and reported as having **held** — because
the second window's return had the same sign and its interval, over a sample
far too small to exclude anything, did not contradict the first. An interval
that spans zero is compatible with the discovery result. It is also compatible
with no effect at all, with half the effect, and with the opposite effect. A
test that cannot fail is not a test, and "it did not contradict us" is the
weakest sentence in statistics wearing the clothes of the strongest one.

So the rule here, and :func:`judge_cell` is the only place it is written:

**A cell replicates only when the held-out season's return carries the SAME
SIGN as the discovery result and the held-out season's OWN interval excludes
zero after the family-wise correction.** A held-out interval that includes zero
is reported as ``no demonstrated edge`` in those exact words, and its state is
``did not replicate`` — never "consistent with", never "did not contradict",
never "directionally in line".

There are two failure states rather than one, and the distinction is the point:

* ``did not replicate`` — the held-out interval includes zero. The window said
  nothing. This is the ordinary outcome and it is not evidence against the
  discovery result; it is the absence of evidence for it.
* ``reversed`` — the held-out interval excludes zero on the **other** side.
  The window said something, and it said the opposite. Per the experiment
  ledger, *a reversal is a result, not a failure* — four of the football lab's
  mechanisms reversed outright, and knowing that was worth more than the null.

## This module does not invent a bar. It reads `promotion.py`'s.

`promotion.py` holds the criteria Cooper's build pre-registered on disk at
`data/manual/promotion_criteria.json`, *"written before any challenger was
measured ... a margin picked after seeing the comparison is not a margin, it is
a description of the outcome."* A second bar written here would be a bar chosen
after the first one existed, which is the same defect one level up. So:

* :attr:`Criteria.minimum_bets` — 2,000 settled bets per season — is the floor
  below which this report prints **no number**, only the words *not enough
  evidence*. It is ten times `stats.MINIMUM_BETS`, and the stricter of two
  pre-registered floors is the one that applies to the last gate before a
  human receipt.
* :attr:`Criteria.require_interval_excludes_zero` must be true, and
  :func:`assert_criteria_agree` **raises** when it is not. That flag being
  false would define replication as "the same sign", which is precisely the
  `blocked_shots` mistake; this module refuses to run rather than silently
  picking which of the two documents to believe.
* :attr:`Criteria.must_clear_every_season` — when more than one season is held
  out, a cell replicates only if it replicates in **every** one of them, never
  on their pooled average. The football lab's verdict defect is the receipt:
  *same policy, same script, opposite verdicts*, depending on which season had
  been scored last.
* :attr:`Criteria.roi_margin_points` is deliberately **not** applied, and the
  reason is that it measures something else. It is the margin a *challenger*
  must beat a *champion* by — a comparison of two models on one window. This
  report compares one model across two windows, where the discovery estimate is
  the thing under test rather than the thing to beat. Applying a champion
  margin here would compare a rule to itself and demand it improve.

## Replication is what one does. It is not proof the finding is real.

Written before the first held-out season is scored, because it is the sentence
this report will most want to omit once it has a survivor:

**A constant settlement offset replicates by construction.** The football lab's
single largest false finding returned +11.7% over 3,109 held-out bets and
survived split-half, fragility and a Bonferroni correction across twenty
markets, because a systematic settlement error is present in every window and
therefore reproduces in all of them. This lab has one known settlement
ambiguity of exactly that shape — second-half markets settle including overtime
at most US books and not at all of them, `markets.SECOND_HALF_INCLUDES_OVERTIME`
— so any second-half cell reaching ``replicated`` is flagged in its own row and
named again in the report's own words. **Replication is not evidence against a
settlement artefact; replication is what one does.**

The mirror of that, from `stats.RoiInterval.verdict()`: a replicated **loss**
is a more credible loss, not good news. The sign is read in exactly one place
in this repository and this module does not add a second — every verdict string
here comes from `RoiInterval.verdict()`, and :func:`judge_cell` reads the ROI's
sign only to compare two windows with each other.

## A result found ON the holdout is not a replication

A cell that demonstrated nothing in discovery and demonstrates something on the
held-out season has not replicated anything. It is a **new discovery, made on
the only clean data this lab had left**, and it carries no held-out test of its
own because the holdout has now been spent on it. Those cells get the state
``nothing to replicate`` and a flag, `found_on_the_holdout`, that the report
prints in words. Reading one as a confirmation is how a holdout is quietly
converted into a second discovery window.

## Per market and per conference tier, never a pooled number alone

The lead table is market x tier, the same shape as the backtest's, for the same
reason: high-major, mid-major and low-major are three different distributions
and the thesis of this lab is that the third is priced with less attention. The
pooled rows exist because `docs/when_this_ends.md` applies the stopping rule to
them, and they are printed under `price_backtest.POOLED_CAVEAT` — imported
rather than restated, so the two reports cannot drift — and only ever beside
their tier rows.

**The pooled rows carry no replication state**, deliberately.
`what_we_can_claim.replication_states` treats a row with no tier as a wildcard
that applies to *every* tier of that market, so a pooled state would become a
per-tier claim about a distribution it was never measured on. Only the
``markets`` list — one entry per (market, tier) — is written in the shape that
document reads.

## Re-renderable from the record, like the retention probe

:func:`build_record` writes every count, and :func:`render` is a pure function
of it. A replication run walks a whole season of slate days and re-grades every
wager in it; if improving a sentence cost that, nobody would improve a sentence
— they would edit the generated file by hand, and a hand-edited generated file
survives exactly one re-run.

## Nothing to measure is said in words

No historical price has been bought for this sport, so there is no discovery
record to replicate and no held-out season to replicate it on. Every function
here returns an empty result honestly and :func:`render` prints *"there is
nothing to measure"* rather than an empty table, because an empty table reads
as a null result and a null result is a claim.
"""

from __future__ import annotations

import dataclasses
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pandas as pd

from cbb_betting_lab import experiment_ledger as E
from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.forward_evidence import SETTLEMENT_AMBIGUOUS_MARKETS
from cbb_betting_lab.promotion import Criteria
# Every number below is computed by calling `price_backtest`'s own splitters
# (`by_market_and_tier`, `by_tier`, `pooled`) and its own interval code rather
# than by reimplementing either. That is the same judgement
# `run_price_backtest.py` records about `forward_evidence`'s private settlement
# helpers: a second copy of a formula drifts, and the direction it drifts in is
# never the conservative one — the football lab carries `_bonferroni_factor` in
# four files with a hardcoded 1.96 in the copies. It matters more here than
# anywhere else in the repository, because the whole content of a replication is
# that the held-out season was scored the same way as the discovery season. A
# replication with its own arithmetic is not a test of the rule; it is a
# comparison of two scorers, and it would disagree in exactly the cells where
# the two implementations diverged.
from cbb_betting_lab.reports import price_backtest as PB


#: Bumped whenever the record's shape changes, so a stale record fails loudly at
#: re-render rather than rendering a report with holes in it. Same discipline as
#: `price_backtest.RECORD_VERSION`, and for the same reason.
RECORD_VERSION = 1

#: The stem both outputs share. `competition.output_name` prefixes it, so the
#: record lands at `data/outputs/cbb_replication.json` — which is exactly where
#: `what_we_can_claim.replication_path` looks for it. Restated here rather than
#: imported so this module does not depend on the claims document to name its
#: own file, and pinned equal by `tests/test_replication.py`.
REPORT_STEM = "replication"

#: The seasons the historical purchase covers, labelled by the year each season
#: **ENDS**, matching hoopR and every other season filter in this repository. An
#: earlier version of this lab labelled by the starting year, which would have
#: made every season filter miss on one side of every join.
BOUGHT_SEASONS: tuple[int, ...] = (2021, 2022, 2023, 2024)

#: The split, declared here and not chosen after a number was seen. Discovery is
#: the first three seasons of the bought population and **2024 is held out**.
#:
#: It is the last season rather than a random one because the holdout has to be
#: the window the rule was not fitted on *in time order* as well as in row
#: order: a rule selected on 2022 and validated on 2021 has been validated on
#: data that existed before it, and every regime change in the sport — the
#: transfer portal, the shot-clock and roster-turnover regimes this lab's
#: ratings prior is fitted against — runs the other way.
DECLARED_HELD_OUT_SEASONS: tuple[int, ...] = (2024,)
DECLARED_DISCOVERY_SEASONS: tuple[int, ...] = (2021, 2022, 2023)
#: When the split above was written down. Before any price had been bought, and
#: therefore before any of it could have been chosen with a result in view.
DECLARED_ON = "2026-09-03"

#: The six states a (market, tier) cell can be in. `replicated` is the only one
#: `what_we_can_claim` reads as a replication, and `untestable` is the only one
#: it skips — an unskipped state is printed in the claims table verbatim, so
#: each of these has to read correctly in the sentence *"<state> on the held-out
#: window"*.
REPLICATED = "replicated"
DID_NOT_REPLICATE = "did not replicate"
REVERSED = "reversed"
NOT_ENOUGH_EVIDENCE = "not enough evidence"
NOTHING_TO_REPLICATE = "nothing to replicate"
UNTESTABLE = "untestable"

STATES: tuple[str, ...] = (
    REPLICATED,
    DID_NOT_REPLICATE,
    REVERSED,
    NOT_ENOUGH_EVIDENCE,
    NOTHING_TO_REPLICATE,
    UNTESTABLE,
)

#: Which failure a cell is reported under when several held-out seasons
#: disagree. A reversal is a stronger statement than a null, and both are
#: stronger than "the sample was too small to say", which is stronger than "no
#: test could be run at all". Nothing here can produce `replicated` — that
#: requires **every** season tested to replicate, per
#: `Criteria.must_clear_every_season`.
FAILURE_PRECEDENCE: tuple[str, ...] = (
    REVERSED,
    DID_NOT_REPLICATE,
    NOT_ENOUGH_EVIDENCE,
    UNTESTABLE,
)

#: What the report says when the prices, the discovery record or the held-out
#: season do not exist yet. Imported in spirit from `price_backtest`, restated
#: through it so the two reports say the same words.
NOTHING_TO_MEASURE = PB.NOTHING_TO_MEASURE

#: Printed above every pooled figure, in full, every time. Imported rather than
#: restated so the backtest and the replication cannot drift on the one caveat
#: that stops a Division I headline existing.
POOLED_CAVEAT = PB.POOLED_CAVEAT

#: Printed in full beside any second-half cell that reaches `replicated`. The
#: football lab's largest false finding is the receipt and the sentence is not
#: paraphrased anywhere.
SETTLEMENT_ARTEFACT_CAVEAT = (
    "**A constant settlement offset replicates by construction.** The football "
    "lab's single largest false finding returned +11.7% over 3,109 held-out "
    "bets and survived split-half, fragility and a Bonferroni correction across "
    "twenty markets, because a systematic settlement error is present in every "
    "window and so reproduces in all of them. Second-half markets settle "
    "including overtime at most US books and not at all of them; this lab wires "
    "the majority rule and cannot read a book's rulebook. Replication is not "
    "evidence against a settlement artefact — replication is what one does."
)

#: Tier order for every table here, strongest first. The same order as the
#: backtest report, so a reader moving between the two is not re-orienting.
TIER_ORDER: tuple[str, ...] = PB.TIER_ORDER


class ReplicationError(RuntimeError):
    """A replication could not be run honestly, so it was not run."""


class NotHeldOut(ReplicationError):
    """The season asked for is one the rule was already selected on.

    The single most expensive way this module could fail, and the only one that
    would produce a clean, confident, entirely worthless report: re-scoring a
    rule on a season it was chosen on reproduces the selection, not the effect,
    and it does it with a tighter interval every time the sample grows.
    """


# --------------------------------------------------------------------------
# Which seasons were which, and the refusal that keeps them apart
# --------------------------------------------------------------------------


def seasons_from_label(label: str) -> tuple[int, ...]:
    """The seasons a backtest record was scored on, from its `season_label`.

    `run_price_backtest.season_label` writes either one year (``"2024"``) or an
    inclusive range (``"2021-2024"``), so both are read here. Anything else
    **raises**.

    Raising is the whole value of this function. An unparseable label read as
    "no seasons" would make every held-out season look disjoint from the
    discovery window, and :func:`assert_held_out` would then wave through a
    replication run on the very season the rule was selected on. That failure
    has no symptom: the report would be complete, the intervals would be
    tighter than the discovery window's, and the result would replicate
    beautifully because it is the same measurement twice.
    """
    text = str(label or "").strip()
    if not text:
        raise ReplicationError(
            "The discovery record carries no `season_label`, so which seasons "
            "the rule was selected on cannot be read. This refuses rather than "
            "assuming none: an empty discovery window makes every season look "
            "held out, and re-scoring a rule on the season it was chosen on "
            "reproduces the selection rather than the effect — with a tighter "
            "interval, and nothing in the output looking wrong."
        )
    parts = [p.strip() for p in text.split("-") if p.strip()]
    if not all(p.isdigit() for p in parts) or len(parts) not in (1, 2):
        raise ReplicationError(
            f"Cannot read {label!r} as the seasons a backtest was scored on. "
            "`run_price_backtest.season_label` writes either one year or an "
            "inclusive `first-last` range, both labelled by the year the "
            "season ENDS."
        )
    if len(parts) == 1:
        return (int(parts[0]),)
    first, last = int(parts[0]), int(parts[1])
    if last < first:
        raise ReplicationError(f"{label!r} runs backwards.")
    return tuple(range(first, last + 1))


def assert_held_out(
    *, seasons: Sequence[int], discovery_seasons: Sequence[int]
) -> None:
    """Raise unless every season asked for is one the rule was NOT selected on.

    The one guard this module cannot be written without. `promotion.py` requires
    a challenger to clear its bar *"out of sample, on a holdout the challenger
    was not fitted on and that was declared before discovery closed"*, and a
    replication that re-scores the discovery window satisfies every other
    sentence in this file while testing nothing at all.
    """
    wanted = [int(s) for s in seasons]
    if not wanted:
        raise NotHeldOut(
            "No held-out season was named. A replication with no held-out "
            "season is a re-run of the backtest under a different filename."
        )
    inside = sorted(set(wanted) & {int(s) for s in discovery_seasons})
    if inside:
        raise NotHeldOut(
            f"Season(s) {inside} are inside the discovery window "
            f"{sorted(set(int(s) for s in discovery_seasons))}, so the rule was "
            "selected on them. Re-scoring a rule on the data it was chosen on "
            "reproduces the selection rather than the effect, and it does so "
            "with a tighter interval every time the sample grows. Nothing was "
            "scored and nothing was written."
        )


def assert_criteria_agree(criteria: Criteria) -> None:
    """Refuse to run when the pre-registered criteria do not define replication.

    `Criteria.require_interval_excludes_zero` being false would define a
    replication as "the same sign", which is the NHL lab's `blocked_shots`
    mistake exactly: a window that merely fails to contradict, reported as
    confirmation. This module will not choose between two of Cooper's own
    documents, and it will not quietly apply the stricter one either — a guard
    that silently overrides a criteria file is a guard nobody can audit. It
    raises and names both.
    """
    if not criteria.require_interval_excludes_zero:
        raise ReplicationError(
            "The pre-registered criteria set `require_interval_excludes_zero` "
            "to false, which would make replication mean 'the same sign' and "
            "nothing more. A held-out interval that includes zero is "
            f"'{S.NO_DEMONSTRATED_EDGE}' and is compatible with the discovery "
            "result, with no effect, and with the opposite effect — that is "
            "the NHL lab's blocked_shots mistake, where a window that merely "
            "failed to contradict was reported as confirmation. Nothing was "
            "scored. Fix the criteria file or delete this module; do not have "
            "both."
        )


# --------------------------------------------------------------------------
# The discovery claim, re-read at today's family size
# --------------------------------------------------------------------------


def _sign(value: float) -> int:
    return (value > 0) - (value < 0)


def interval_at(row: Mapping, *, looks: int) -> S.RoiInterval:
    """A stored cell's interval, rebuilt under **today's** family size.

    The `adjusted_low`/`adjusted_high` written into a backtest record were
    computed with whatever the ledger held on the day it ran. Re-deriving them
    from the point estimate and the standard error under the current cumulative
    count is what stops a December correction being quoted in March, and it can
    only ever make the interval wider. `what_we_can_claim` does the same thing
    to the same rows for the same reason.
    """
    return dataclasses.replace(PB.interval_from_row(dict(row)), looks=int(looks))


def discovery_claims(record: Mapping, *, looks: int) -> list[dict]:
    """Every (market, tier) cell the backtest measured, and whether it claimed.

    A cell **claims** when its own interval, corrected for everything this lab
    has ever tested, excludes zero — `RoiInterval.survives_correction`, which is
    gated on the declared sample floor first. Both signs claim: a demonstrated
    deficit is a finding, and a loss that replicates is a *more credible* loss.
    The NHL lab's headline predicate never read the sign; nothing here re-reads
    it either, because the verdict string comes from `RoiInterval.verdict()`.
    """
    claims: list[dict] = []
    for row in record.get("by_market_and_tier") or []:
        if not isinstance(row, Mapping):
            continue
        interval = interval_at(row, looks=looks)
        claims.append(
            {
                "market": str(row.get("market", "")),
                "tier": str(row.get("tier", "")),
                "bets": int(interval.bets),
                "clusters": int(interval.clusters),
                "roi": float(interval.roi),
                "low": float(interval.low),
                "high": float(interval.high),
                "adjusted_low": float(interval.adjusted_low),
                "adjusted_high": float(interval.adjusted_high),
                "standard_error": float(interval.standard_error),
                "cluster_unit": str(interval.cluster_unit),
                "enough_evidence": bool(interval.enough_evidence),
                "verdict": interval.verdict(),
                "claims": bool(interval.survives_correction),
                "sign": _sign(interval.roi),
                "side_biased": bool(row.get("side_biased")),
                "dominant_side": str(row.get("dominant_side", "")),
                "dominant_share": float(row.get("dominant_share", 0.0) or 0.0),
            }
        )
    return claims


# --------------------------------------------------------------------------
# The held-out season, scored the same way
# --------------------------------------------------------------------------


def holdout_cells(bets: pd.DataFrame, *, looks: int) -> dict[tuple[str, str], dict]:
    """`(market, tier) -> the held-out cell`, from `price_backtest`'s own splitter.

    `by_market_and_tier` is called rather than reimplemented so the held-out
    season is cut into exactly the cells the discovery season was cut into, with
    the same two-way clustering and the same side-concentration check. A
    replication whose cells are drawn differently from the discovery run's is
    not a replication of anything; it is a different measurement with a
    reassuring name.
    """
    if bets is None or bets.empty:
        return {}
    return {
        (str(row.get("market", "")), str(row.get("tier", ""))): row
        for row in PB.by_market_and_tier(bets, looks=looks)
    }


def judge_cell(
    claim: Mapping, holdout: Mapping | None, *, criteria: Criteria
) -> tuple[str, str]:
    """One cell's state and the sentence that says why. The only judge here.

    The order is the argument, and every branch before the last one is a way of
    saying *not yet* rather than *no*:

    1. **No held-out rows at all** -> ``untestable``. No test was run. That is
       not a failure to replicate, and `what_we_can_claim` skips this state so
       the cell reads "no held-out test has been run".
    2. **Below `Criteria.minimum_bets`** -> ``not enough evidence``. A phrase,
       never a number. The floor is the pre-registered one in
       `data/manual/promotion_criteria.json`, not a threshold this module chose.
    3. **Nothing claimed in discovery** -> ``nothing to replicate``. A cell that
       demonstrated nothing has no result to reproduce. If the held-out season
       demonstrates something anyway, that is a **new discovery made on the
       holdout** — the clean data is now spent on it — and it is flagged rather
       than promoted.
    4. **The held-out interval includes zero** -> ``did not replicate``, with
       the words ``no demonstrated edge``. THIS IS THE BRANCH THE NHL LAB DID
       NOT HAVE. A window that merely fails to contradict is not confirmation:
       an interval spanning zero is equally compatible with the discovery
       result, with no effect, and with the opposite effect.
    5. **The held-out interval excludes zero on the other side** -> ``reversed``.
       The window said something and it said the opposite. A reversal is a
       result, not a failure.
    6. **Same sign, interval excludes zero** -> ``replicated``. Both conditions,
       never one.
    """
    if not holdout or int(holdout.get("bets", 0)) <= 0:
        return UNTESTABLE, (
            "the held-out season carries no graded bet in this cell, so no test "
            "was run. That is not a failure to replicate — those are different "
            "claims and this lab does not report them the same way."
        )

    bets = int(holdout.get("bets", 0))
    if bets < int(criteria.minimum_bets):
        return NOT_ENOUGH_EVIDENCE, (
            f"{bets:,} held-out bets is below the {criteria.minimum_bets:,} "
            "declared in advance in the promotion criteria, so this cell prints "
            "a phrase and not a number. A +12% return over 40 bets and a coin "
            "flip are the same claim at that sample size."
        )

    interval = interval_at(holdout, looks=int(holdout.get("looks", 1)))
    excludes_zero = interval.survives_correction
    holdout_sign = _sign(interval.roi)

    if not claim.get("claims"):
        if excludes_zero:
            return NOTHING_TO_REPLICATE, (
                f"the discovery window demonstrated nothing here "
                f"({claim.get('verdict', '')}), so there is no result to "
                f"reproduce — and the held-out season's own "
                f"{interval.roi:+.1%} over {bets:,} bets excludes zero. That is "
                "a NEW DISCOVERY MADE ON THE HOLDOUT, not a replication: the "
                "only clean season this lab had is now spent on it, and it has "
                "no held-out test of its own."
            )
        return NOTHING_TO_REPLICATE, (
            f"the discovery window demonstrated nothing here "
            f"({claim.get('verdict', '')}), so there is no result to reproduce. "
            f"The held-out season is {S.NO_DEMONSTRATED_EDGE} as well, over "
            f"{bets:,} bets."
        )

    if not excludes_zero:
        return DID_NOT_REPLICATE, (
            f"the held-out season returned {interval.roi:+.1%} over {bets:,} "
            f"bets across {interval.clusters:,} {interval.cluster_unit}s, "
            f"family-corrected interval {interval.adjusted_low:+.1%} to "
            f"{interval.adjusted_high:+.1%}, which includes zero — "
            f"{S.NO_DEMONSTRATED_EDGE}. It is compatible with the discovery "
            "result, with no effect and with the opposite effect alike, and a "
            "window that merely fails to contradict is not confirmation."
        )

    if holdout_sign != int(claim.get("sign", 0)):
        return REVERSED, (
            f"the held-out season returned {interval.roi:+.1%} over {bets:,} "
            f"bets and its interval excludes zero on the OTHER side of the "
            f"discovery result's {float(claim.get('roi', 0.0)):+.1%}. The "
            "window said something, and it said the opposite. A reversal is a "
            "result, not a failure."
        )

    return REPLICATED, (
        f"the held-out season returned {interval.roi:+.1%} over {bets:,} bets "
        f"across {interval.clusters:,} {interval.cluster_unit}s, "
        f"family-corrected interval {interval.adjusted_low:+.1%} to "
        f"{interval.adjusted_high:+.1%}, which excludes zero on the same side "
        f"as the discovery result's {float(claim.get('roi', 0.0)):+.1%}. Same "
        "sign AND its own interval excludes zero — both, never one."
    )


def combine_seasons(states: Sequence[str]) -> str:
    """One state from several held-out seasons. Every season, never the average.

    `Criteria.must_clear_every_season` is pre-registered and it is not a
    formality: the football lab's verdict defect was a script that scored one
    season and wrote a verdict file, so *the same policy under the same script
    produced opposite verdicts depending on which season had been run last.*
    Pooling the held-out seasons would let one of them carry the others, which
    is the identical failure with a smoother surface.

    So `replicated` requires every season tested to have replicated, and the
    failure reported is the most informative one present — see
    :data:`FAILURE_PRECEDENCE`.
    """
    present = [s for s in states if s]
    if not present:
        return UNTESTABLE
    if all(s == REPLICATED for s in present):
        return REPLICATED
    if any(s == NOTHING_TO_REPLICATE for s in present):
        return NOTHING_TO_REPLICATE
    for state in FAILURE_PRECEDENCE:
        if state in present:
            return state
    return UNTESTABLE


# --------------------------------------------------------------------------
# The record
# --------------------------------------------------------------------------


def _holdout_row(row: Mapping | None) -> dict:
    """A held-out cell as plain data, or an empty one. Never a fabricated zero."""
    if not row:
        return {}
    return {k: v for k, v in dict(row).items()}


def build_record(
    *,
    discovery: Mapping,
    holdout_bets: Mapping[int, pd.DataFrame],
    criteria: Criteria,
    looks: int,
    competition: Competition = CBB,
    model: str = "",
    generated_at: str = "",
    criteria_source: str = "",
    ledger_source: str = "",
    ledger_found: bool = False,
    holdout_looks_recorded: int = 0,
    edge_threshold: float | None = None,
) -> dict:
    """Every count this run made, as plain data. :func:`render` is pure over it.

    `holdout_bets` maps each held-out season to that season's graded bets,
    scored by the same walk-forward machinery on the same store with the same
    edge threshold as the discovery run. They are kept **apart by season** and
    never concatenated before judgement, because
    `Criteria.must_clear_every_season` decides on each one and a pooled frame
    cannot answer a per-season question afterwards.

    `edge_threshold` defaults to the discovery record's. It is an argument only
    so a caller can state it explicitly; a replication run at a different
    threshold is a replication of a different rule, and the record carries both
    values so the two can never be silently conflated.
    """
    assert_criteria_agree(criteria)

    discovery_seasons = seasons_from_label(str(discovery.get("season_label", "")))
    held_out = tuple(sorted(int(s) for s in holdout_bets))
    assert_held_out(seasons=held_out, discovery_seasons=discovery_seasons)

    claims = discovery_claims(discovery, looks=looks)
    per_season_cells = {
        season: holdout_cells(frame, looks=looks)
        for season, frame in holdout_bets.items()
    }
    combined = (
        pd.concat(
            [f for f in holdout_bets.values() if f is not None and not f.empty],
            ignore_index=True,
        )
        if any(f is not None and not f.empty for f in holdout_bets.values())
        else pd.DataFrame()
    )
    combined_cells = holdout_cells(combined, looks=looks)

    markets: list[dict] = []
    for claim in claims:
        key = (claim["market"], claim["tier"])
        seasons_detail: list[dict] = []
        for season in held_out:
            cell = per_season_cells.get(season, {}).get(key)
            state, why = judge_cell(claim, cell, criteria=criteria)
            detail = {"season": int(season), "state": state, "why": why}
            detail.update(_holdout_row(cell))
            seasons_detail.append(detail)
        state = combine_seasons([d["state"] for d in seasons_detail])
        holdout_row = _holdout_row(combined_cells.get(key))
        holdout_interval = (
            interval_at(holdout_row, looks=looks) if holdout_row else None
        )
        # Judged per season and never on the pooled held-out frame, for the same
        # reason the states are: pooling two held-out seasons lets one of them
        # carry the other, and a flag that fires on a pooled figure would name a
        # season that showed nothing.
        found_on_the_holdout = bool(
            not claim["claims"]
            and any(
                int(d.get("bets", 0)) >= int(criteria.minimum_bets)
                and interval_at(d, looks=looks).survives_correction
                for d in seasons_detail
                if d.get("bets")
            )
        )
        markets.append(
            {
                "market": claim["market"],
                "tier": claim["tier"],
                # Read by `what_we_can_claim.replication_states`. One entry per
                # (market, tier); nothing pooled ever carries a state.
                "state": state,
                "why": "; ".join(
                    f"{d['season']}: {d['why']}" for d in seasons_detail
                ),
                "discovery": claim,
                "holdout": holdout_row,
                "holdout_bets": int(holdout_row.get("bets", 0)) if holdout_row else 0,
                "holdout_clusters": (
                    int(holdout_row.get("clusters", 0)) if holdout_row else 0
                ),
                "clears_floor": bool(
                    holdout_row
                    and int(holdout_row.get("bets", 0)) >= int(criteria.minimum_bets)
                ),
                # The same value `run_replication.record_holdout_looks` wrote
                # to the ledger for this cell: the discovery sign where
                # discovery claimed, the two-sided look where it did not. The
                # record and the ledger must not name one look two ways.
                "predicted_direction": (
                    "higher"
                    if claim["claims"] and claim["sign"] > 0
                    else "lower"
                    if claim["claims"] and claim["sign"] < 0
                    else E.TWO_SIDED
                ),
                "realised_direction": (
                    ""
                    if holdout_interval is None
                    else "higher"
                    if _sign(holdout_interval.roi) > 0
                    else "lower"
                    if _sign(holdout_interval.roi) < 0
                    else ""
                ),
                "found_on_the_holdout": found_on_the_holdout,
                "settlement_suspect": claim["market"] in SETTLEMENT_AMBIGUOUS_MARKETS,
                "seasons": seasons_detail,
            }
        )

    counts = {state: 0 for state in STATES}
    for row in markets:
        counts[row["state"]] = counts.get(row["state"], 0) + 1

    return {
        "record_version": RECORD_VERSION,
        "competition": competition.key,
        "title": competition.title,
        "generated_at": generated_at,
        # Read by `what_we_can_claim`, which prints it as the window a cell
        # replicated (or failed to replicate) on.
        "test_label": (
            ", ".join(str(s) for s in held_out) + " (held out)" if held_out else ""
        ),
        "held_out_seasons": [int(s) for s in held_out],
        "discovery_seasons": [int(s) for s in discovery_seasons],
        "discovery_season_label": str(discovery.get("season_label", "")),
        "bought_seasons": list(BOUGHT_SEASONS),
        "declared_held_out_seasons": list(DECLARED_HELD_OUT_SEASONS),
        "declared_discovery_seasons": list(DECLARED_DISCOVERY_SEASONS),
        "declared_on": DECLARED_ON,
        "declared_in_advance": bool(
            set(held_out) == set(DECLARED_HELD_OUT_SEASONS)
        ),
        "model": str(model),
        "snapshot_phase": str(discovery.get("snapshot_phase", "")),
        "edge_threshold": float(
            discovery.get("edge_threshold", PB.BET_EDGE_THRESHOLD)
            if edge_threshold is None
            else edge_threshold
        ),
        "discovery_edge_threshold": float(
            discovery.get("edge_threshold", PB.BET_EDGE_THRESHOLD)
        ),
        "criteria": {
            "minimum_bets": int(criteria.minimum_bets),
            "require_interval_excludes_zero": bool(
                criteria.require_interval_excludes_zero
            ),
            "must_clear_every_season": bool(criteria.must_clear_every_season),
            "roi_margin_points": float(criteria.roi_margin_points),
            "declared_on": str(criteria.declared_on),
            "source": str(criteria_source),
        },
        "looks": int(looks),
        "correction_factor": S.bonferroni_factor(int(looks)),
        "ledger": {
            "source": str(ledger_source),
            "found": bool(ledger_found),
            "cumulative_hypotheses": int(looks),
            "holdout_looks_recorded": int(holdout_looks_recorded),
        },
        "discovery": {
            "generated_at": str(discovery.get("generated_at", "")),
            "bets_graded": int(discovery.get("bets_graded", 0)),
            "wagers_graded": int(discovery.get("wagers_graded", 0)),
            "games": int(discovery.get("games", 0)),
            "days": int(discovery.get("days", 0)),
            "cells": len(claims),
            "claims": sum(1 for c in claims if c["claims"]),
            "looks_when_scored": int(discovery.get("looks", 1)),
        },
        "holdout": {
            "bets_graded": int(len(PB.settled(combined))) if not combined.empty else 0,
            "bets_taken": int(len(combined)),
            "games": int(combined["event_id"].nunique()) if not combined.empty else 0,
            "days": int(combined["slate_date"].nunique()) if not combined.empty else 0,
            "by_season": {
                str(season): {
                    "bets_taken": int(len(frame)) if frame is not None else 0,
                    "bets_graded": (
                        int(len(PB.settled(frame)))
                        if frame is not None and not frame.empty
                        else 0
                    ),
                    "games": (
                        int(frame["event_id"].nunique())
                        if frame is not None and not frame.empty
                        else 0
                    ),
                    "days": (
                        int(frame["slate_date"].nunique())
                        if frame is not None and not frame.empty
                        else 0
                    ),
                }
                for season, frame in holdout_bets.items()
            },
        },
        "markets": markets,
        "by_tier": PB.by_tier(combined, looks=looks),
        "pooled": PB.pooled(combined, looks=looks),
        "counts": counts,
    }


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def roi_cells(row: Mapping, *, criteria_minimum_bets: int) -> tuple[str, str, str]:
    """The return, its interval and the corrected interval — or three dashes.

    **Below the pre-registered floor there is no number.** The floor is
    `Criteria.minimum_bets` from `data/manual/promotion_criteria.json`, ten
    times `stats.MINIMUM_BETS`, and the stricter of two floors declared in
    advance is the one that applies to the last gate before a human receipt.
    `price_backtest.roi_cells` does the formatting once the row has cleared;
    this wrapper only decides whether the row prints at all, so there is one
    formatter and not two.
    """
    if not row or int(row.get("bets", 0)) < int(criteria_minimum_bets):
        return "—", "—", "—"
    return PB.roi_cells(dict(row))


def verdict_text(row: Mapping, *, minimum_bets: int) -> str:
    """The row's verdict, or the phrase that replaces it below the floor.

    A row can clear `stats.MINIMUM_BETS` and miss `Criteria.minimum_bets`, and
    then `RoiInterval.verdict()` has already read the sign into a string like
    `demonstrated edge` while this report is withholding the number. Printing
    both would be a table whose return column says "—" and whose verdict column
    says an edge was demonstrated — the reader would believe the verdict and
    assume the dash was a formatting fault.

    **This reads no sign.** It either passes through the verdict `stats` already
    computed or replaces it with the same *not enough evidence* phrasing `stats`
    uses for its own floor, against the pre-registered floor this report
    applies.
    """
    bets = int(row.get("bets", 0)) if row else 0
    if not row:
        return "—"
    if bets < int(minimum_bets):
        return (
            f"{NOT_ENOUGH_EVIDENCE} ({bets:,} held-out bets, below the "
            f"{int(minimum_bets):,} declared in advance)"
        )
    return str(row.get("verdict", ""))


def _line(row: Mapping, label: str, *, minimum_bets: int) -> str:
    roi, interval, corrected = roi_cells(row, criteria_minimum_bets=minimum_bets)
    return (
        f"| {label} | {int(row.get('bets', 0)):,} | "
        f"{int(row.get('clusters', 0)):,} | {roi} | {interval} | {corrected} | "
        f"{verdict_text(row, minimum_bets=minimum_bets)} |"
    )


def _nothing(what: str) -> list[str]:
    return [
        f"**{NOTHING_TO_MEASURE.capitalize()}.** {what} It is said in words "
        "rather than shown as an empty table, because an empty table reads as a "
        "null result and a null result is a claim.",
        "",
    ]


def render(record: Mapping) -> str:
    """The report, as a pure function of the record. No clock, no network."""
    lines: list[str] = []
    add = lines.append
    minimum_bets = int((record.get("criteria") or {}).get("minimum_bets", S.MINIMUM_BETS))

    add(f"# {record.get('title', CBB.title)} — replication on a held-out season")
    add("")
    if record.get("generated_at"):
        add(f"Generated {record['generated_at']}.")
        add("")

    add(
        "**A window that merely fails to contradict is not confirmation.** A "
        "cell here replicates only when the held-out season's return carries "
        "the **same sign** as the discovery result **and** the held-out "
        "season's **own** interval excludes zero after the family-wise "
        f"correction. A held-out interval that includes zero is "
        f"**{S.NO_DEMONSTRATED_EDGE}** and its state is *{DID_NOT_REPLICATE}* — "
        "never 'consistent with', never 'directionally in line'. The NHL lab "
        "reported a market as having held because a second window with a "
        "sample far too small to exclude anything did not contradict the "
        "first; an interval spanning zero is equally compatible with the "
        "discovery result, with no effect, and with the opposite effect."
    )
    add("")

    held_out = record.get("held_out_seasons") or []
    discovery_seasons = record.get("discovery_seasons") or []
    add(
        f"**Held out: {', '.join(str(s) for s in held_out) or '—'}. Selected "
        f"on: {', '.join(str(s) for s in discovery_seasons) or '—'}.** The "
        "bought population is "
        f"{', '.join(str(s) for s in record.get('bought_seasons') or [])}, "
        "labelled by the year each season ENDS. The rule was not fitted on the "
        "held-out season and was not chosen on it."
    )
    add("")
    if not record.get("declared_in_advance", False):
        add(
            "**This is not the split declared in advance.** "
            f"{record.get('declared_on', '')} declared discovery "
            f"{record.get('declared_discovery_seasons')} and holdout "
            f"{record.get('declared_held_out_seasons')}. A holdout chosen after "
            "the discovery numbers were seen is a second look at the data "
            "rather than a pre-registered test, and every state below should be "
            "read as one."
        )
        add("")

    add(
        f"**The same rule, not a similar one.** The model is "
        f"`{record.get('model') or 'unrecorded'}`, the snapshot window is "
        f"`{record.get('snapshot_phase') or 'unrecorded'}` and the edge "
        f"threshold is {float(record.get('edge_threshold', 0.0)):.0%} — the "
        "discovery run's own threshold, read from its record rather than "
        "re-chosen here. The held-out season is scored by "
        "`price_backtest`'s own walk-forward, one-bet-per-wager and clustering "
        "code, called rather than reimplemented: a replication with its own "
        "scorer is not a test of the rule, it is a comparison of two scorers."
    )
    add("")
    add(
        "**The discovery record does not name the model that priced it.** The "
        "agreement between the two runs on that one point is asserted by the "
        "operator who passed `--model`, not verified by this report, and it is "
        "said here rather than left implicit."
    )
    add("")

    looks = int(record.get("looks", 1))
    ledger = record.get("ledger") or {}
    add(
        f"**Family correction: {looks:,} cumulative hypotheses** in the "
        "experiment ledger, widening every 95% interval by "
        f"x{float(record.get('correction_factor', 1.0)):.2f}. That is the "
        "ledger's **cumulative** count and never the day's — a search that runs "
        "every week is not twelve tests, it is twelve tests a week, forever. "
        f"{int(ledger.get('holdout_looks_recorded', 0)):,} of them are this "
        "run's own holdout looks: putting a discovery finding to the holdout "
        "**is** a second look and is counted as one."
    )
    add("")
    criteria = record.get("criteria") or {}
    add(
        f"**Below {minimum_bets:,} held-out bets there is no number**, only the "
        f"words *{NOT_ENOUGH_EVIDENCE}*. That floor is "
        f"`promotion.Criteria.minimum_bets`, declared "
        f"{criteria.get('declared_on') or 'in advance'} in "
        f"`{criteria.get('source') or 'data/manual/promotion_criteria.json'}`. "
        "This module reads that bar rather than inventing a second one — a "
        "bar written here would be a bar chosen after the first one existed."
    )
    add("")

    counts = record.get("counts") or {}
    holdout = record.get("holdout") or {}
    markets = record.get("markets") or []
    if not markets:
        lines.extend(
            _nothing(
                "The discovery record measured no market-and-tier cell, so "
                "there is nothing to put to a held-out season."
            )
        )
    else:
        add("## The verdict, per market and per conference tier")
        add("")
        add(
            f"{len(markets):,} cell(s) from the discovery record, re-scored on "
            f"{holdout.get('bets_graded', 0):,} graded held-out bets across "
            f"{holdout.get('games', 0):,} games and {holdout.get('days', 0):,} "
            "slate days. **6 high-major conferences / 79 teams, 10 mid-major / "
            "122, 17 low-major / 164** are three different distributions and "
            "are never pooled into one headline."
        )
        add("")
        add(
            f"The **Discovery** column quotes the backtest's own figure at the "
            f"backtest's own floor of {S.MINIMUM_BETS:,} bets; every held-out "
            f"column is withheld below the {minimum_bets:,}-bet floor "
            "`promotion.py` pre-registered per season. Two floors, both "
            "declared in advance, each applied to the report that owns it — "
            "re-judging the backtest's numbers here would be inventing a third."
        )
        add("")
        add(
            "| Tier | Market | Discovery | Held-out bets | Games | Held-out ROI "
            "| 95% interval | Family-corrected | Held-out verdict | State |"
        )
        add("|:---|:---|:---|---:|---:|---:|:---|:---|:---|:---|")
        for row in ordered_cells(markets):
            cell = row.get("holdout") or {}
            roi, interval, corrected = roi_cells(
                cell, criteria_minimum_bets=minimum_bets
            )
            discovery_cell = row.get("discovery") or {}
            # The figure AND whether it was a claim. A discovery return quoted
            # without that marker reads as something the held-out season either
            # confirmed or failed to confirm, when for a cell that demonstrated
            # nothing there was never anything to confirm.
            discovery_figure = (
                (
                    f"{float(discovery_cell.get('roi', 0.0)):+.1%} over "
                    f"{int(discovery_cell.get('bets', 0)):,}"
                    + ("" if discovery_cell.get("claims") else " (no claim)")
                )
                if discovery_cell.get("enough_evidence")
                else "—"
            )
            add(
                f"| {row.get('tier', '')} | {row.get('market', '')} | "
                f"{discovery_figure} | {int(row.get('holdout_bets', 0)):,} | "
                f"{int(row.get('holdout_clusters', 0)):,} | {roi} | {interval} | "
                f"{corrected} | "
                f"{verdict_text(cell, minimum_bets=minimum_bets)} | "
                f"**{row.get('state', '')}** |"
            )
        add("")
        add(
            f"**{counts.get(REPLICATED, 0)} replicated, "
            f"{counts.get(DID_NOT_REPLICATE, 0)} did not replicate, "
            f"{counts.get(REVERSED, 0)} reversed, "
            f"{counts.get(NOT_ENOUGH_EVIDENCE, 0)} not enough evidence, "
            f"{counts.get(NOTHING_TO_REPLICATE, 0)} nothing to replicate, "
            f"{counts.get(UNTESTABLE, 0)} untestable.**"
        )
        add("")
        # Said every run, and not only when nothing replicated. The house rule
        # is that an interval including zero is reported in those exact words —
        # not "promising", not "trending positive", not "did not contradict" —
        # and a summary that only appears on a clean sweep is a summary that is
        # missing on precisely the run somebody quotes.
        spanning = [
            r
            for r in ordered_cells(markets)
            if r.get("clears_floor")
            and (r.get("holdout") or {}).get("verdict") == S.NO_DEMONSTRATED_EDGE
        ]
        if spanning:
            add(
                f"**{len(spanning)} cell(s) have a held-out interval that "
                f"includes zero. Each of those is {S.NO_DEMONSTRATED_EDGE}**, "
                "in those words: "
                + "; ".join(
                    f"{r.get('tier', '')} / {r.get('market', '')} at "
                    f"{float((r.get('holdout') or {}).get('roi', 0.0)):+.1%} over "
                    f"{int(r.get('holdout_bets', 0)):,} bets"
                    for r in spanning
                )
                + "."
            )
            add("")
        if not counts.get(REPLICATED, 0):
            add(
                "**Nothing replicated.** That is the ordinary outcome and it is "
                "not a surprise: clearing a correction in the window a result "
                "was found in, and then failing to hold on a window it was not, "
                "is what most findings do. Every cell whose held-out interval "
                f"includes zero is **{S.NO_DEMONSTRATED_EDGE}**."
            )
            add("")

        lines.extend(_why_section(markets))
        lines.extend(_settlement_section(markets))
        lines.extend(_found_on_the_holdout_section(markets))
        lines.extend(_per_season_section(record, minimum_bets=minimum_bets))

    add("### Per tier, across markets")
    add("")
    add(
        "The held-out season's own return per tier. It carries no replication "
        "state: a state is a claim about a specific (market, tier) cell that "
        "the discovery window made, and a tier roll-up is not one of those."
    )
    add("")
    tiers = record.get("by_tier") or []
    if not tiers:
        lines.extend(_nothing("No tier has a graded held-out bet."))
    else:
        add(S.ROI_TABLE_HEADER.replace("| Market |", "| Tier |"))
        for row in tiers:
            add(_line(row, row.get("name", row.get("tier", "")), minimum_bets=minimum_bets))
        add("")

    add("## Pooled")
    add("")
    add(POOLED_CAVEAT)
    add("")
    add(
        "**No pooled row carries a replication state**, and none is written into "
        "the `markets` list the claims document reads. A row with no tier is "
        "treated there as applying to every tier of that market, so a pooled "
        "state would become a per-tier claim about a distribution it was never "
        "measured on."
    )
    add("")
    pooled_rows = record.get("pooled") or []
    if not pooled_rows:
        lines.extend(_nothing("Nothing to pool."))
    else:
        add(S.ROI_TABLE_HEADER)
        for row in pooled_rows:
            add(_line(row, row.get("name", ""), minimum_bets=minimum_bets))
        add("")

    add("## What this report cannot say")
    add("")
    add(
        "- It cannot say a replicated result is **real**. "
        + SETTLEMENT_ARTEFACT_CAVEAT
    )
    add(
        "- It cannot say a replicated result is **good**. A replicated loss is "
        f"a more credible loss: `{S.DEMONSTRATED_DEFICIT}` is a finding, and "
        "the NHL lab announced one as good news because its headline predicate "
        "tested measured, survives-correction and replicated without ever "
        "reading which side of zero the number sat on."
    )
    add(
        f"- It cannot say a *{DID_NOT_REPLICATE}* cell is **wrong**. An "
        "interval that includes zero is the absence of evidence for the "
        "discovery result, not evidence against it, and this report does not "
        "convert one into the other in either direction."
    )
    add(
        "- It cannot say an edge is **reachable**. That is `reachability.py`'s "
        "question, and an edge living entirely in prices that vanished is "
        "reported there as not reachable regardless of its size or its "
        "significance."
    )
    add(
        "- It cannot say a market is a play. **No market is allowlisted**, and "
        "a replicated result is a candidate for a receipt Cooper signs and "
        "nothing more. Claude may withdraw an allowlist and may never grant one."
    )
    return "\n".join(lines).rstrip() + "\n"


def ordered_cells(markets: Sequence[Mapping]) -> list[dict]:
    """Tier order first, then market, so the lead table reads the same as the backtest's."""
    order = {tier: i for i, tier in enumerate(TIER_ORDER)}
    return sorted(
        (dict(m) for m in markets),
        key=lambda m: (order.get(str(m.get("tier", "")), len(order)), str(m.get("market", ""))),
    )


def _why_section(markets: Sequence[Mapping]) -> list[str]:
    """One line per cell saying, in words, why it landed where it did."""
    lines = ["### Why each cell landed where it did", ""]
    lines.append(
        "Every state below carries its sample size, and every cell whose "
        f"held-out interval includes zero says **{S.NO_DEMONSTRATED_EDGE}** in "
        "those words."
    )
    lines.append("")
    for row in ordered_cells(markets):
        lines.append(
            f"- **{row.get('tier', '')} / {row.get('market', '')} — "
            f"{row.get('state', '')}**: {row.get('why', '')}"
        )
    lines.append("")
    return lines


def _settlement_section(markets: Sequence[Mapping]) -> list[str]:
    suspect = [
        r
        for r in markets
        if r.get("settlement_suspect") and r.get("state") == REPLICATED
    ]
    if not suspect:
        return []
    lines = ["### A replicated second-half cell is a settlement suspect first", ""]
    lines.append(SETTLEMENT_ARTEFACT_CAVEAT)
    lines.append("")
    for row in ordered_cells(suspect):
        lines.append(
            f"- {row.get('tier', '')} / {row.get('market', '')} reached "
            "`replicated` and settles on a rule this lab cannot verify. Treat "
            "it as a settlement artefact first and a finding second."
        )
    lines.append("")
    return lines


def _found_on_the_holdout_section(markets: Sequence[Mapping]) -> list[str]:
    found = [r for r in markets if r.get("found_on_the_holdout")]
    if not found:
        return []
    lines = ["### Found on the holdout, which is not a replication", ""]
    lines.append(
        f"{len(found)} cell(s) demonstrated nothing in the discovery window and "
        "demonstrate something on the held-out season. **That is a new "
        "discovery made on the only clean data this lab had left**, not a "
        "confirmation of anything: the cell has no held-out test of its own, "
        "and the season it would have been tested on has now been spent. It is "
        "counted in the experiment ledger like any other look and it is not a "
        "candidate for a receipt."
    )
    lines.append("")
    for row in ordered_cells(found):
        cell = row.get("holdout") or {}
        lines.append(
            f"- {row.get('tier', '')} / {row.get('market', '')}: "
            f"{float(cell.get('roi', 0.0)):+.1%} over "
            f"{int(cell.get('bets', 0)):,} held-out bets — "
            f"{cell.get('verdict', '')}."
        )
    lines.append("")
    return lines


def _per_season_section(record: Mapping, *, minimum_bets: int) -> list[str]:
    """Each held-out season on its own, when there is more than one.

    Printed because `Criteria.must_clear_every_season` decides on each season
    separately and never on their average. Pooling lets one season carry the
    others, which is the football lab's verdict defect with a smoother surface.
    """
    held_out = record.get("held_out_seasons") or []
    if len(held_out) < 2:
        return []
    lines = ["### Every held-out season on its own", ""]
    lines.append(
        f"`must_clear_every_season` is pre-registered: a cell replicates only "
        f"if it replicates in **all {len(held_out)}** of these, never on their "
        "pooled average. The football lab's verdict for one policy flipped "
        "depending on which season had been scored last — same policy, same "
        "script, opposite verdicts."
    )
    lines.append("")
    lines.append(
        "| Tier | Market | Season | Bets | Games | ROI | 95% interval | "
        "Family-corrected | State |"
    )
    lines.append("|:---|:---|---:|---:|---:|---:|:---|:---|:---|")
    for row in ordered_cells(record.get("markets") or []):
        for detail in row.get("seasons") or []:
            roi, interval, corrected = roi_cells(
                detail, criteria_minimum_bets=minimum_bets
            )
            lines.append(
                f"| {row.get('tier', '')} | {row.get('market', '')} | "
                f"{detail.get('season', '')} | {int(detail.get('bets', 0)):,} | "
                f"{int(detail.get('clusters', 0)):,} | {roi} | {interval} | "
                f"{corrected} | {detail.get('state', '')} |"
            )
    lines.append("")
    return lines


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------


def record_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPORT_STEM, ".json")


def report_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPORT_STEM, ".md")


def write_record(record: Mapping, path: Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dict(record), indent=2, default=str) + "\n", encoding="utf-8"
    )
    return target


def read_record(path: Path) -> dict:
    """The record, or a refusal naming the version mismatch.

    A stale record renders a report with holes in it and nothing looks wrong,
    which is the one failure mode a re-render flag introduces and the reason
    `price_backtest` guards its own the same way.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    version = int(payload.get("record_version", 0))
    if version != RECORD_VERSION:
        raise ReplicationError(
            f"{Path(path).name} is a version {version} record and this module "
            f"writes version {RECORD_VERSION}. Re-run the replication rather "
            "than re-rendering a record whose shape has changed — a stale "
            "record renders a report with holes in it and nothing looks wrong."
        )
    return payload


def write_report(record: Mapping, path: Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(record), encoding="utf-8")
    return target
