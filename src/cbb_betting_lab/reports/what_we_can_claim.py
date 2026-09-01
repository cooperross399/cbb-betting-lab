"""`data/outputs/cbb_what_we_can_claim.md` — the generated half of the honesty doc.

`docs/what_we_can_and_cannot_claim.md` is written by hand, it was written on
2026-09-01 before a single price had been bought, and it states the **rules**.
This module is its machine-generated counterpart: it reads whatever measurement
records exist on disk and writes down what they actually support, in the fixed
vocabulary `stats.py` defines.

It exists so that *"what does the evidence say"* has an answer that cannot drift
from the evidence. A hand-written summary goes stale the moment a measurement is
re-run; this one is re-run with it, and
`scripts/run_what_we_can_claim.py --check` fails the build when the markdown on
disk stops matching the record it claims to be rendered from.

## The defect this file exists to not repeat: **the headline must read the sign**

The NHL lab's version of this module announced *"at least one result survived
the correction and then replicated"* on a market returning **−6.6% over roughly
nine thousand bets**. Its headline predicate tested three things — measured,
survives-correction, replicated — and **never looked at which side of zero the
number sat on**. A market the model reliably loses on satisfies all three
exactly as well as one it wins on. The one document whose job is to stop a
number being misread became the thing misreading it, and it did so in the
confident register of something that had already survived scrutiny.

So the sign is read in exactly one place in this repository —
:meth:`stats.RoiInterval.verdict`, which returns
:data:`stats.DEMONSTRATED_EDGE` or :data:`stats.DEMONSTRATED_DEFICIT` and never
confuses them — and this module *partitions on that string* rather than
re-deriving the test. :func:`demonstrated_edges` and
:func:`demonstrated_deficits` are separate functions returning disjoint lists,
:func:`headline` speaks for the first and **names** the second, and
`tests/test_the_headline_reads_the_sign.py` pins both against a replicated
−6.6% market.

That is defect 3 in `docs/ported_defects.md`.

## Four more rules this module enforces mechanically

1. **Every measured number is printed with its sample size**, and below
   `stats.MINIMUM_BETS` there is no number at all — a phrase instead. *A +12%
   return over 40 bets and a coin flip are the same claim at that sample size*,
   and printing the +12% invites somebody to quote it out of the row that
   qualifies it.
2. **An interval that includes zero is reported with the exact phrase "no
   demonstrated edge"**, never a softer one. That phrase comes from
   `stats.NO_DEMONSTRATED_EDGE` rather than being typed here, because a second
   copy of a phrase drifts and the direction it drifts in is never the
   conservative one.
3. **A market with no price-based measurement is listed under "not measured"**,
   never under "no value", and the section says so in words. An excluded market
   is never reported as a pass, an avoid, or a no-value call — that is Cooper's
   rule, it is absolute, and it covers the deferred provider keys and the
   availability-gated props as well as the merely unmeasured.
4. **Futures never enter a headline computed over game bets.** They tie up stake
   for months and settle on a different clock. They are partitioned out of
   :func:`_headline_claims` structurally rather than by being remembered.

## The correction is the ledger's cumulative count, re-applied here

`experiment_ledger.py` says it: *a search that runs every week is not twelve
tests, it is twelve tests a week, forever.* So the family size this document
corrects by is the ledger's **cumulative** distinct-hypothesis count, read at
render time — not the day's count, and not the count that happened to be in the
ledger when the price backtest was run weeks ago.

That last clause is the reason this module rebuilds every interval rather than
copying the corrected bounds out of the record it read. A backtest run in
December carries December's `looks`; by March the ledger has grown and the same
number means less. `stats.RoiInterval` is reconstructed from the stored point
estimate and standard error with **today's** `looks`, so the correction can only
ever get stricter as the search continues, which is the only direction it is
allowed to move.

**An absent ledger applies no correction and says so**, rather than quietly
applying none — the rule `price_backtest.looks_from_ledger` already follows.

## Nothing to claim yet is a true report, not an empty one

No price has been bought and no opinion has settled. That is the correct state
for a lab whose season opens in November, and it produces a **short and true**
document rather than an empty one: the rules are stated, the policies in force
are listed, the markets that cannot produce a selection are named with their
reasons, and the measured section says :data:`NOTHING_TO_MEASURE` in words.

An empty table reads as a null result, and a null result is a claim.

## Pure over a run record

`build_record` reads disk; `render` reads only the record. The retention probe's
rule, applied here for the same reason: improving a sentence must never cost a
re-run, and a report that can only be produced by re-running the measurement is
a report nobody improves. The workflow re-renders this document every game day,
free, offline, from records other steps wrote.
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cbb_betting_lab import forward_evidence
from cbb_betting_lab import gates
from cbb_betting_lab import markets as markets_registry
from cbb_betting_lab import staging_provider_policy as policy_module
from cbb_betting_lab import stats as S
from cbb_betting_lab import verdicts as verdicts_module
from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, REPO_ROOT
from cbb_betting_lab.conferences import Tier
from cbb_betting_lab.experiment_ledger import LEDGER_FILENAME as EXPERIMENT_LEDGER_FILENAME
from cbb_betting_lab.experiment_ledger import load as load_experiment_ledger
from cbb_betting_lab.reports import price_backtest as backtest


#: Bumped whenever the record's shape changes, so a stale record fails loudly at
#: re-render rather than rendering a report with holes in it. Same discipline as
#: `price_backtest.RECORD_VERSION` and for the same reason.
RECORD_VERSION = 1

#: The stem both outputs share. `competition.output_name` prefixes it, so the
#: markdown lands at `data/outputs/cbb_what_we_can_claim.md` — a contract string
#: in `CLAUDE.md`, pinned by `tests/test_contract_strings.py`.
REPORT_STEM = "what_we_can_claim"

#: An optional record written by a replication run over a held-out season. It
#: does not exist yet and nothing in this repository has replicated anything;
#: when it does exist it is read from here. **Its absence is reported as "no
#: held-out test has been run", never as a market having failed one** — those
#: are different claims and the sibling labs have confused them before.
REPLICATION_STEM = "replication"

#: What the measured section says when there is nothing in it. In words, because
#: an empty table reads as a null result and a null result is a claim.
NOTHING_TO_MEASURE = "there is nothing to measure"

#: Printed under every list of markets this lab has no price-based evidence
#: about — the unmeasured, the deferred and the availability-gated alike.
#: Cooper's rule, verbatim in effect: *an excluded market is never reported as a
#: pass, an avoid, or a no-value call.*
NOT_A_NO_VALUE_CALL = (
    "**A market in this list is not a market judged to have no value.** It is a "
    "market with no price-based evidence either way, and nothing in this "
    "repository will present the two as the same thing. It is not a pass, it is "
    "not an avoid, and it is not a no-value call."
)

#: Phrases this repository does not use about its own results. A generated
#: summary that reaches for one of these has stopped reporting and started
#: selling, so `write_report` raises rather than writing it.
#:
#: Matched on **word boundaries**, never as bare substrings. A substring test
#: for "lock" fails on the word *clock*, which appears legitimately in the
#: futures section — and a guard that fires on honest prose is a guard somebody
#: eventually deletes.
FORBIDDEN_PHRASES: tuple[str, ...] = (
    "guaranteed",
    "sure thing",
    "can't lose",
    "cannot lose",
    "proven edge",
    "beats the market",
    "free money",
    "lock",
    "locks",
)

#: The stopping rule's sample floor, from `docs/when_this_ends.md`, which
#: declared both numbers on 2026-09-01 before any data existed. Restated here so
#: this document can report progress against them, and pinned against the doc by
#: `tests/test_the_headline_reads_the_sign.py` so the two cannot drift — a floor
#: that quietly moved is not a floor.
SAMPLE_FLOOR_OPINIONS = 10_000
SAMPLE_FLOOR_GAMES = 2_000
DECISION_DATE = "2027-04-19"

#: Tier order for every table here, strongest first. Same order as the backtest
#: report so a reader moving between the two is not re-orienting.
TIER_ORDER: tuple[str, ...] = (
    Tier.HIGH_MAJOR.value,
    Tier.MID_MAJOR.value,
    Tier.LOW_MAJOR.value,
    Tier.UNPLACED.value,
)

#: Where a measurement came from. The two are never pooled into one number: a
#: historical backtest bets into prices somebody has already seen resolve, and a
#: frozen forward opinion does not. They are different evidence and they get
#: different rows.
FROM_BACKTEST = "historical price backtest"
FROM_FORWARD = "forward ledger, frozen before tip"


class ClaimsError(RuntimeError):
    """A claims document could not be produced honestly, so it was not."""


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------


def record_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPORT_STEM, ".json")


def report_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPORT_STEM, ".md")


def replication_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPLICATION_STEM, ".json")


def experiment_ledger_path(output_dir: Path) -> Path:
    """The experiment ledger is **not** competition-prefixed, deliberately.

    It counts every hypothesis this lab has ever put to the data, across every
    search. A per-competition ledger in a one-competition repository would be
    the same file with a longer name and a standing invitation to reset the
    count by adding a second one.
    """
    return Path(output_dir) / EXPERIMENT_LEDGER_FILENAME


def forward_ledger_path(processed_dir: Path) -> Path:
    return Path(processed_dir) / forward_evidence.LEDGER_FILENAME


# ---------------------------------------------------------------------------
# Reading, defensively
# ---------------------------------------------------------------------------


def _read_json(path: Path) -> dict:
    """A JSON object, or an empty dict. Never a partial one."""
    target = Path(path)
    if not target.is_file():
        return {}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _as_float(value: object) -> float | None:
    """A float, or None. **A non-finite bound is None, not an infinity.**

    `stats.interval_by_cluster` returns ±inf when a cell has fewer than two
    clusters, because one cluster supplies no between-cluster variation and
    there is genuinely no interval to report. Carrying that through as a float
    would render as `-inf%` and round-trip through JSON as the non-standard
    literal `Infinity`; carrying it through as **0.0** would be far worse,
    because a zero-width interval around a positive return reads as a finding.
    None renders as "unbounded" and cannot be mistaken for either.
    """
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


def _text(value: object) -> str:
    return "" if value is None else str(value).strip()


def _repo_relative(path: Path) -> str:
    """A path as the reader will recognise it, not as this machine spells it.

    The rendered document is published to `card-feed` and read by a human on a
    phone. `/home/runner/work/cbb-betting-lab/cbb-betting-lab/data/outputs/...`
    is the same file as `data/outputs/...` and only one of them is legible — and
    a record whose contents change with the machine that built it makes the
    `--check` re-render comparison depend on where it ran.
    """
    target = Path(path)
    try:
        return str(target.resolve().relative_to(Path(REPO_ROOT).resolve()))
    except ValueError:
        return str(target)


# ---------------------------------------------------------------------------
# The correction
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Correction:
    """The family size this document corrects by, and where it came from."""

    #: Distinct hypotheses ever tested, from the ledger's cumulative count.
    hypotheses: int
    #: `max(hypotheses, 1)`, which is what `stats` wants.
    looks: int
    factor: float
    #: False when no ledger was found. The report then says the correction could
    #: not be applied rather than quietly applying none.
    applied: bool
    budget_per_week: int = 0
    budget_declared_on: str = ""
    discovery: int = 0
    holdout: int = 0
    reversals: int = 0
    source: str = ""

    def as_dict(self) -> dict:
        return {
            "hypotheses": self.hypotheses,
            "looks": self.looks,
            "factor": self.factor,
            "applied": self.applied,
            "budget_per_week": self.budget_per_week,
            "budget_declared_on": self.budget_declared_on,
            "discovery": self.discovery,
            "holdout": self.holdout,
            "reversals": self.reversals,
            "source": self.source,
        }


def correction_from_ledger(path: Path) -> Correction:
    """The cumulative correction, read from the experiment ledger.

    **Cumulative, never the day's count.** Correcting a week's findings across
    "the twelve things I tested today" is a lie if twelve more were tested last
    week and twelve more the week before; over a season that is hundreds of
    looks, and at a nominal 5% threshold roughly one in twenty clears by chance
    alone.

    An absent ledger returns `applied=False` and `looks=1`. The report then
    states that the correction could not be applied, which is a different and
    much more alarming claim than "the correction was applied and nothing
    needed widening".
    """
    target = Path(path)
    if not target.is_file():
        return Correction(
            hypotheses=0,
            looks=1,
            factor=1.0,
            applied=False,
            source=_repo_relative(target),
        )
    ledger = load_experiment_ledger(target)
    stages = ledger.by_stage()
    looks = max(ledger.count, 1)
    return Correction(
        hypotheses=ledger.count,
        looks=looks,
        factor=S.bonferroni_factor(looks),
        applied=True,
        budget_per_week=ledger.budget.per_week,
        budget_declared_on=ledger.budget.declared_on,
        discovery=int(stages.get("discovery", 0)),
        holdout=int(stages.get("holdout", 0)),
        reversals=len(ledger.reversals()),
        source=_repo_relative(target),
    )


# ---------------------------------------------------------------------------
# Replication
# ---------------------------------------------------------------------------


def replication_states(payload: Mapping) -> dict:
    """`(market, tier) -> state`, from an optional replication record.

    A row may name a tier or not; one that does not applies to every tier of
    that market, which is recorded under the wildcard key ``"*"``. Anything this
    function does not find is **not** a failure to replicate: it is a market no
    held-out test has been run on, and the two are reported differently.
    """
    states: dict = {}
    for item in payload.get("markets", []) or []:
        if not isinstance(item, Mapping):
            continue
        market = _text(item.get("market"))
        if not market:
            continue
        state = _text(item.get("state")).casefold()
        if state in {"", "untestable"}:
            continue
        states[(market, _text(item.get("tier")) or "*")] = state
    return states


def _replication_for(states: Mapping, market: str, tier: str) -> str:
    return _text(states.get((market, tier)) or states.get((market, "*")))


# ---------------------------------------------------------------------------
# Claims
# ---------------------------------------------------------------------------


def _family_of(market_key: str) -> str:
    market = markets_registry.MARKETS_BY_KEY.get(market_key)
    return market.family if market else ""


def _claim(
    interval: S.RoiInterval,
    *,
    source: str,
    cut: str,
    market: str,
    tier: str,
    replication: str,
    test_label: str = "",
) -> dict:
    """One measured cell as plain data, with its verdict already read.

    **The sign is read here, once, by `stats.RoiInterval.verdict()`**, and every
    downstream partition — the headline, the tables, the counts — reads the
    resulting string. Nothing else in this module re-derives "is this an edge",
    which is precisely the re-derivation the NHL lab got wrong.
    """
    family = _family_of(market)
    suspect = market in forward_evidence.SETTLEMENT_AMBIGUOUS_MARKETS
    return {
        "source": source,
        "cut": cut,
        "market": market,
        "tier": tier or Tier.UNPLACED.value,
        "family": family,
        "is_futures": family == markets_registry.FUTURES,
        "measured": True,
        "bets": int(interval.bets),
        "clusters": int(interval.clusters),
        "cluster_unit": interval.cluster_unit,
        "roi": _as_float(interval.roi),
        "low": _as_float(interval.low),
        "high": _as_float(interval.high),
        "adjusted_low": _as_float(interval.adjusted_low),
        "adjusted_high": _as_float(interval.adjusted_high),
        "standard_error": _as_float(interval.standard_error) or 0.0,
        "looks": int(interval.looks),
        "enough_evidence": bool(interval.enough_evidence),
        "verdict": interval.verdict(),
        # A second-half market settles including overtime at most US books and
        # not at all of them. That is a book rule this lab cannot read, so its
        # number measures the rule as much as the model — the exact shape of the
        # football lab's largest false finding.
        "settlement_suspect": bool(suspect),
        "replication": replication,
        "replicated": replication == "replicated",
        "replication_label": test_label,
    }


def _interval_from_backtest_row(row: Mapping, *, looks: int) -> S.RoiInterval:
    """Rebuild a backtest cell's interval under **today's** family size.

    The stored `adjusted_low`/`adjusted_high` were computed with whatever the
    ledger held when the backtest ran. Re-deriving them from the point estimate
    and the standard error with the current cumulative count is what stops a
    December correction being quoted in March, and it can only ever make the
    interval wider.
    """
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


def _interval_from_forward_row(row: Mapping, *, looks: int) -> S.RoiInterval:
    """Rebuild a forward-ledger cell's interval under today's family size.

    `forward_evidence.report_payload` does not carry the standard error, so it
    is recovered from the interval it published: the bounds were built as
    ``roi ± Z95 · se`` by `stats.interval_by_cluster`, so ``se = (high − low) /
    (2·Z95)`` inverts that exactly. `tests/test_what_we_can_claim.py` pins the
    recovery against an interval computed directly from the same rows, so a
    change to how the payload is built fails here rather than silently producing
    a correction computed off the wrong width.

    An unbounded row — one cluster, no between-cluster variation — recovers a
    standard error of zero, which leaves the corrected bounds equal to the
    uncorrected ones. That is right: there was no interval to widen.
    """
    low = _as_float(row.get("low"))
    high = _as_float(row.get("high"))
    standard_error = 0.0
    if low is not None and high is not None and high > low:
        standard_error = (high - low) / (2.0 * S.Z95)
    return S.RoiInterval(
        roi=_as_float(row.get("roi")) or 0.0,
        low=low if low is not None else float("-inf"),
        high=high if high is not None else float("inf"),
        bets=_as_int(row.get("bets")),
        clusters=_as_int(row.get("clusters")),
        standard_error=standard_error,
        looks=looks,
        cluster_unit=_text(row.get("cluster_unit")) or "game",
    )


def _pooled_row(row: Mapping, *, looks: int) -> dict:
    """One pooled cell, rebuilt under today's family size.

    Pooled figures are computed because `docs/when_this_ends.md` applies the
    stopping rule to them as well as to each tier — **not so they can be quoted
    on their own.** They live in their own section under
    `price_backtest.POOLED_CAVEAT` and are structurally unreachable from
    :func:`headline`, which reads `record["claims"]` and nothing else.
    """
    interval = _interval_from_backtest_row(row, looks=looks)
    return {
        "name": _text(row.get("name")) or _text(row.get("market")),
        "bets": interval.bets,
        "clusters": interval.clusters,
        "cluster_unit": interval.cluster_unit,
        "roi": _as_float(interval.roi),
        "low": _as_float(interval.low),
        "high": _as_float(interval.high),
        "adjusted_low": _as_float(interval.adjusted_low),
        "adjusted_high": _as_float(interval.adjusted_high),
        "enough_evidence": bool(interval.enough_evidence),
        "verdict": interval.verdict(),
    }


def claims_from_backtest(
    record: Mapping, *, looks: int, states: Mapping, test_label: str = ""
) -> list[dict]:
    """One claim per (market, tier) the price backtest actually staked.

    `by_market_and_tier` is the backtest's lead table and it is **never
    pooled** — high-major, mid-major and low-major are different distributions.
    The record's `pooled` block is deliberately not read here: it is carried
    into its own section of the report under its own caveat, and it never
    reaches the headline.
    """
    rows: list[dict] = []
    for row in record.get("by_market_and_tier", []) or []:
        if not isinstance(row, Mapping):
            continue
        market = _text(row.get("market"))
        tier = _text(row.get("tier"))
        if not market:
            continue
        claim = _claim(
            _interval_from_backtest_row(row, looks=looks),
            source=FROM_BACKTEST,
            cut="bets",
            market=market,
            tier=tier,
            replication=_replication_for(states, market, tier),
            test_label=test_label,
        )
        # A cell whose bets sit overwhelmingly on one side is a bet on that
        # side wearing a model's clothes. The backtest measures it; this
        # document carries the flag rather than re-deriving it.
        claim["dominant_side"] = _text(row.get("dominant_side"))
        claim["side_biased"] = bool(row.get("side_biased"))
        rows.append(claim)
    return rows


def claims_from_forward(
    payload: Mapping, *, looks: int, states: Mapping, test_label: str = ""
) -> list[dict]:
    """One claim per (cut, market, tier) in the forward ledger.

    Both cuts are carried. `docs/when_this_ends.md` names **opinions** as the
    measurement the stopping rule is applied to — the card is dark and places no
    bets, and a frozen opinion scored against the price it was frozen at is the
    same test — while **bets** is the subset that cleared the declared edge
    threshold and could actually have been selected. Reporting only one of them
    would let the choice flatter whichever looked better, which is the move this
    whole repository is arranged against.
    """
    rows: list[dict] = []
    for row in payload.get("rows", []) or []:
        if not isinstance(row, Mapping):
            continue
        market = _text(row.get("market"))
        tier = _text(row.get("tier"))
        if not market:
            continue
        rows.append(
            _claim(
                _interval_from_forward_row(row, looks=looks),
                source=FROM_FORWARD,
                cut=_text(row.get("cut")) or "opinions",
                market=market,
                tier=tier,
                replication=_replication_for(states, market, tier),
                test_label=test_label,
            )
        )
    return rows


# ---------------------------------------------------------------------------
# The headline, and the partition it reads
# ---------------------------------------------------------------------------


def _headline_claims(record: Mapping) -> list[dict]:
    """Every claim the headline is permitted to speak for.

    Two exclusions, both structural rather than remembered:

    * **Futures.** They tie up stake for months and settle on a different clock,
      and Cooper's rule is that no futures return is ever folded into a headline
      ROI computed over game bets. They get their own section with their hold
      time stated.
    * **Unmeasured markets**, which have no number to speak for.
    """
    return [
        claim
        for claim in record.get("claims", []) or []
        if isinstance(claim, Mapping)
        and claim.get("measured")
        and not claim.get("is_futures")
    ]


def demonstrated_edges(record: Mapping) -> list[dict]:
    """Cells whose corrected interval excludes zero **on the winning side**.

    Reads `verdict`, which came from `stats.RoiInterval.verdict()`, which reads
    the sign. This function and :func:`demonstrated_deficits` return disjoint
    lists by construction, and that disjointness is the whole fix for defect 3.
    """
    return [
        claim
        for claim in _headline_claims(record)
        if claim.get("verdict") == S.DEMONSTRATED_EDGE
        and not claim.get("settlement_suspect")
    ]


def demonstrated_deficits(record: Mapping) -> list[dict]:
    """Cells whose corrected interval excludes zero **on the losing side**.

    A demonstrated deficit is a finding, not a null result, and it is never
    reported as an edge, as a near-miss, or as encouragement.
    """
    return [
        claim
        for claim in _headline_claims(record)
        if claim.get("verdict") == S.DEMONSTRATED_DEFICIT
        and not claim.get("settlement_suspect")
    ]


def not_evidence(record: Mapping) -> list[dict]:
    """Cells whose settlement rule this lab cannot verify.

    They are excluded from both lists above rather than assigned to one. A
    number computed on an unverified settlement rule is an artefact at any
    sample size, and the football lab's single largest false finding was exactly
    that — so it is neither an edge nor a deficit, and saying which it "would
    have been" is the mistake.
    """
    return [
        claim
        for claim in _headline_claims(record)
        if claim.get("settlement_suspect") and claim.get("enough_evidence")
    ]


def _figure(claim: Mapping) -> str:
    """A return with its sample size attached. There is no other kind here."""
    roi = _as_float(claim.get("roi"))
    if roi is None:
        return f"{claim.get('bets', 0):,} bets, no readable return"
    return (
        f"{roi:+.1%} over {_as_int(claim.get('bets')):,} bets across "
        f"{_as_int(claim.get('clusters')):,} "
        f"{_text(claim.get('cluster_unit')) or 'game'}s"
    )


def _name(claim: Mapping) -> str:
    return (
        f"`{_text(claim.get('market'))}` / {_text(claim.get('tier'))} "
        f"({_text(claim.get('source'))}, {_text(claim.get('cut'))})"
    )


def _named_figures(claims: Sequence[Mapping]) -> str:
    return "; ".join(f"{_name(c)} at {_figure(c)}" for c in claims)


def headline(record: Mapping) -> str:
    """The one paragraph somebody who reads nothing else will read.

    Six states, checked in an order chosen so that no reading of the document
    can turn a loss into good news:

    1. **Nothing measured.** True today and for the next two months.
    2. **Measured, nothing at the declared sample floor.** A phrase, not a
       number.
    3. **A replicated profitable result.** The only state that may use the word
       *profitable*, and it still names any deficit beside it.
    4. **A surviving profitable result that has not replicated.** A candidate,
       explicitly not a finding.
    5. **A surviving loss and no surviving gain.** Led by the loss, named as a
       `demonstrated deficit`, and **not** opened with `no demonstrated edge` —
       that phrase belongs to an interval that includes zero and a deficit's
       does not.
    6. **Neither.** `no demonstrated edge`, in those exact words.

    States 3 and 4 are reachable only through :func:`demonstrated_edges`, which
    partitions on a verdict string that read the sign. A market returning −6.6%
    that survives correction and replicates lands in state 5 — where the
    replication makes the loss *more* credible and is said so — which is exactly
    what the NHL lab's version of this function did not do.
    """
    claims = _headline_claims(record)
    if not claims:
        return (
            "**Nothing in this repository has a demonstrated edge, because "
            "nothing has been measured against real prices yet.** That is a "
            "statement about the evidence, not about the models, and it is the "
            "correct state for a lab whose first game has not been played. "
            "Forward evidence cannot be back-dated, which is why the "
            "freeze-and-settle organ was built before the models were worth "
            "anything."
        )

    cells = len(claims)
    markets = len({_text(c.get("market")) for c in claims})
    edges = demonstrated_edges(record)
    deficits = demonstrated_deficits(record)
    unverifiable = not_evidence(record)
    replicated_edges = [c for c in edges if c.get("replicated")]

    def _deficit_clause() -> str:
        if not deficits:
            return ""
        return (
            f" Alongside it, {len(deficits)} cell(s) are a "
            f"**{S.DEMONSTRATED_DEFICIT}** — an interval excluding zero on the "
            f"**losing** side: {_named_figures(deficits)}. A "
            f"{S.DEMONSTRATED_DEFICIT} is a finding, not a null result, and it "
            "is never reported as a result that survived and replicated."
        )

    def _unverifiable_clause() -> str:
        if not unverifiable:
            return ""
        return (
            f" A further {len(unverifiable)} cell(s) carry a settlement rule "
            "this lab cannot verify — second-half markets settle including "
            "overtime at most US books and not at all of them — so their "
            "numbers measure the rule as much as the model and are **not "
            "evidence** either way."
        )

    if not any(c.get("enough_evidence") for c in claims):
        largest = max((_as_int(c.get("bets")) for c in claims), default=0)
        return (
            f"**Nothing has reached the sample floor declared in advance.** "
            f"{cells} market-and-tier cell(s) across {markets} market(s) have "
            f"settled rows; the largest carries {largest:,} bets against the "
            f"floor of {S.MINIMUM_BETS:,}. Below that floor this document "
            "prints a phrase and not a number, because a +12% return over 40 "
            "bets and a coin flip are the same claim at that sample size."
            + _unverifiable_clause()
        )

    if replicated_edges:
        return (
            f"{cells} market-and-tier cell(s) across {markets} market(s) are "
            "measured against real prices, and at least one **profitable** "
            "result survived the correction for everything this lab has ever "
            f"tested and then replicated on a window it was not found on: "
            f"{_named_figures(replicated_edges)}. That is a candidate for a "
            "receipt and nothing more — no market reaches the card without a "
            "reviewed human acceptance receipt, whatever the numbers say. Read "
            "the per-cell lines and the sample sizes before doing anything "
            "with it."
            + _deficit_clause()
            + _unverifiable_clause()
        )

    if edges:
        return (
            f"{cells} market-and-tier cell(s) across {markets} market(s) are "
            f"measured against real prices. {len(edges)} of them exclude zero "
            "on the winning side after correcting for everything this lab has "
            f"ever tested — {_named_figures(edges)} — and **none of them has "
            "replicated on a window it was not found on.** That makes them "
            "candidates, not findings, and clearing the correction while "
            "failing to replicate is the ordinary outcome rather than a "
            "surprise."
            + _deficit_clause()
            + _unverifiable_clause()
        )

    if deficits:
        # THE BRANCH THE NHL LAB DID NOT HAVE. A result that is measured,
        # survives the correction and replicates satisfies its headline
        # predicate whichever side of zero it sits on, and so a −6.6% market
        # was announced as good news. Here the deficit leads its own sentence.
        #
        # It deliberately does NOT open with `NO_DEMONSTRATED_EDGE`. That phrase
        # is reserved for an interval that **includes** zero; a deficit's
        # interval excludes it, and reusing the phrase here would blur the one
        # distinction the phrase exists to make.
        replicated_deficits = [c for c in deficits if c.get("replicated")]
        replication_note = (
            " It has also **replicated** on a window it was not found on, "
            "which makes the loss more credible rather than less — replication "
            "is not evidence of an edge, it is evidence that a result is real, "
            "and this result is a loss."
            if replicated_deficits
            else ""
        )
        return (
            f"**The only result that survives is a loss.** {cells} "
            f"market-and-tier cell(s) across {markets} market(s) are measured "
            f"against real prices. None excludes zero on the winning side; "
            f"{len(deficits)} exclude(s) it on the **losing** side after "
            f"correcting for everything this lab has ever tested, which is a "
            f"**{S.DEMONSTRATED_DEFICIT}**: {_named_figures(deficits)}."
            + replication_note
            + " A "
            + S.DEMONSTRATED_DEFICIT
            + " is a finding, not a null result, and it is the finding this "
            "lab has."
            + _unverifiable_clause()
        )

    return (
        f"**{S.NO_DEMONSTRATED_EDGE.capitalize()} in any market.** {cells} "
        f"market-and-tier cell(s) across {markets} market(s) are measured "
        "against real prices, and nothing survives correcting for the number "
        "of hypotheses this lab has tested and then holds on a window it was "
        "not found on."
        + _unverifiable_clause()
    )


# ---------------------------------------------------------------------------
# The markets with no number
# ---------------------------------------------------------------------------


def unmeasured_markets(claims: Sequence[Mapping]) -> list[dict]:
    """Every wired market no claim speaks for, with the reason it has none.

    The reasons are specific rather than a single shrug, because *"the source
    does not have this"* and *"we looked in the wrong place"* have looked
    identical before and the second one cost the NHL lab a market for a season.
    """
    measured = {_text(c.get("market")) for c in claims if c.get("measured")}
    rows: list[dict] = []
    for market in markets_registry.MARKETS:
        if market.key in measured:
            continue
        if market.family == markets_registry.PLAYER:
            reason = (
                "no historical price has been bought for it and no forward "
                "opinion on it has settled. It is also gated: nothing in this "
                "sport reaches `Availability.CONFIRMED`, so it is priced, "
                "frozen and settled and cannot produce a selection"
            )
        elif market.family == markets_registry.FUTURES:
            reason = (
                "a futures market, served under a separate provider sport key, "
                "settling on a clock measured in months. Nothing has been "
                "bought for it and nothing has settled"
            )
        else:
            reason = (
                "no historical price has been bought for it and no forward "
                "opinion on it has settled"
            )
        rows.append(
            {
                "market": market.key,
                "title": market.title,
                "family": market.family,
                "tier": market.tier,
                "segment": market.segment,
                "settles_on": market.settles_on,
                "reason": reason,
            }
        )
    return rows


def deferred_groups() -> list[dict]:
    """`DEFERRED_MARKETS`, grouped by the reason they share.

    Thirty-odd of them are the quarter family and they share one sentence:
    men's college basketball plays two halves, so those markets cannot exist.
    Printing that sentence thirty times would bury the two deferrals that are
    about something else.
    """
    grouped: dict[str, list[str]] = {}
    for key, reason in markets_registry.DEFERRED_MARKETS.items():
        grouped.setdefault(str(reason), []).append(str(key))
    return [
        {"reason": reason, "provider_keys": sorted(keys)}
        for reason, keys in sorted(grouped.items(), key=lambda kv: -len(kv[1]))
    ]


def gated_markets() -> list[dict]:
    """Markets that are modelled, priced, frozen, settled — and cannot be bet.

    The analogue of the NHL lab's "goalie saves needs a confirmed starter".
    Measured on 2026-09-01: ESPN's men's-college-basketball injuries endpoint is
    permanently empty, CollegeBasketballData has no availability endpoint at
    all, and the conference reports that exist cover roughly 115 of 365 teams,
    conference games only. A gate that read a missing feed as "nobody is
    injured" would clear an entire slate.
    """
    note = gates.availability_note(gates.Availability.NO_REPORT)
    return [
        {"market": m.key, "title": m.title, "note": note}
        for m in markets_registry.MARKETS
        if m.family == markets_registry.PLAYER
    ]


# ---------------------------------------------------------------------------
# The record
# ---------------------------------------------------------------------------


def build_record(
    *,
    competition: Competition = CBB,
    output_dir: Path | None = None,
    processed_dir: Path | None = None,
    manual_dir: Path | None = None,
    now: datetime | None = None,
) -> dict:
    """Read every measurement record on disk and state what it supports.

    Reads, in this order and each one optionally:

    * the **experiment ledger**, for the cumulative correction — first, because
      every interval below is rebuilt under it;
    * the **price backtest record**, for the historical measurement;
    * the **forward-evidence ledger**, for the frozen-then-settled measurement,
      through `forward_evidence.report_payload` so the two documents cannot
      disagree about a number they both print;
    * an optional **replication record**, absent today;
    * every recorded **verdict**, and the **staging provider policy**.

    A file that is missing is reported as missing. A file that is present and
    unreadable is reported as unreadable — **never as an absence of evidence**,
    because those are different claims and the second one reads as a null
    result.
    """
    outputs = Path(output_dir) if output_dir else Path(OUTPUTS_DIR)
    processed = Path(processed_dir) if processed_dir else Path(PROCESSED_DIR)
    moment = now or datetime.now(timezone.utc)

    correction = correction_from_ledger(experiment_ledger_path(outputs))
    looks = correction.looks

    replication_file = replication_path(competition, outputs)
    replication_payload = _read_json(replication_file)
    states = replication_states(replication_payload)
    test_label = _text(replication_payload.get("test_label"))

    # --- the historical backtest -------------------------------------------
    backtest_file = backtest.record_path(competition, outputs)
    backtest_block: dict = {
        "path": _repo_relative(backtest_file),
        "found": backtest_file.is_file(),
    }
    backtest_claims: list[dict] = []
    pooled_rows: list[dict] = []
    if backtest_file.is_file():
        try:
            backtest_record = backtest.read_record(backtest_file)
        except (backtest.BacktestError, OSError, UnicodeError, json.JSONDecodeError) as exc:
            backtest_block["error"] = str(exc)
        else:
            backtest_claims = claims_from_backtest(
                backtest_record, looks=looks, states=states, test_label=test_label
            )
            pooled_rows = [
                _pooled_row(row, looks=looks)
                for row in backtest_record.get("pooled", []) or []
                if isinstance(row, Mapping)
            ]
            backtest_block.update(
                {
                    "season_label": _text(backtest_record.get("season_label")),
                    "snapshot_phase": _text(backtest_record.get("snapshot_phase")),
                    "wagers_offered": _as_int(backtest_record.get("wagers_offered")),
                    "wagers_graded": _as_int(backtest_record.get("wagers_graded")),
                    "bets_taken": _as_int(backtest_record.get("bets_taken")),
                    "bets_graded": _as_int(backtest_record.get("bets_graded")),
                    "games": _as_int(backtest_record.get("games")),
                    "days": _as_int(backtest_record.get("days")),
                    "looks_when_run": _as_int(backtest_record.get("looks")),
                    "edge_threshold": _as_float(backtest_record.get("edge_threshold")),
                }
            )

    # --- the forward ledger -------------------------------------------------
    ledger_file = forward_ledger_path(processed)
    forward_block: dict = {
        "path": _repo_relative(ledger_file),
        "found": ledger_file.is_file(),
    }
    forward_claims: list[dict] = []
    try:
        ledger = forward_evidence.read_ledger(ledger_file)
        payload = forward_evidence.report_payload(
            ledger, families=looks, competition=competition
        )
    except Exception as exc:  # noqa: BLE001 - reported, never swallowed
        # An unreadable ledger is NOT an absence of evidence. Reporting it as
        # "nothing measured" would turn a broken instrument into a null result,
        # which is the one substitution this document exists to prevent.
        forward_block["error"] = f"{type(exc).__name__}: {exc}"
    else:
        forward_claims = claims_from_forward(
            payload, looks=looks, states=states, test_label=test_label
        )
        settled_games = 0
        settled_opinions = 0
        for row in payload.get("rows", []) or []:
            if isinstance(row, Mapping) and _text(row.get("cut")) == "opinions":
                settled_opinions += _as_int(row.get("bets"))
                settled_games += _as_int(row.get("clusters"))
        forward_block.update(
            {
                "frozen_opinions": _as_int(payload.get("frozen_opinions")),
                "measurable_rows": _as_int(payload.get("measurable_rows")),
                "settled_opinions": settled_opinions,
                "bet_threshold": _as_float(payload.get("bet_threshold")),
            }
        )

    claims = backtest_claims + forward_claims

    # --- what is in force ---------------------------------------------------
    recorded = [
        verdicts_module.read(policy, competition, output_dir=outputs)
        for policy in sorted(verdicts_module.VERDICT_FILES)
    ]
    policy = policy_module.load(manual_dir)

    record = {
        "record_version": RECORD_VERSION,
        "competition": competition.key,
        "title": competition.title,
        "generated_at": moment.isoformat(timespec="seconds"),
        "minimum_bets": S.MINIMUM_BETS,
        "no_demonstrated_edge_phrase": S.NO_DEMONSTRATED_EDGE,
        "correction": correction.as_dict(),
        "claims": claims,
        "pooled": pooled_rows,
        "unmeasured": unmeasured_markets(claims),
        "deferred": deferred_groups(),
        "gated": gated_markets(),
        "backtest": backtest_block,
        "forward": forward_block,
        "replication": {
            "path": _repo_relative(replication_file),
            "found": replication_file.is_file(),
            "test_label": test_label,
            "states": [
                {"market": market, "tier": tier, "state": state}
                for (market, tier), state in sorted(states.items())
            ],
        },
        "verdicts": [
            {
                "policy": v.policy,
                "ships": v.ships,
                "citation": v.citation(),
            }
            for v in recorded
        ],
        "policy": {
            "provider": policy.provider,
            "mode": policy.mode,
            "manual_only": policy.mode == policy_module.MANUAL_ONLY,
            "allowlisted": sorted(policy.allowlist),
            "summary": policy.summary_line(competition),
            "withdrawn": len(policy.withdrawn),
        },
        "stopping_rule": {
            "decision_date": DECISION_DATE,
            "floor_opinions": SAMPLE_FLOOR_OPINIONS,
            "floor_games": SAMPLE_FLOOR_GAMES,
        },
        "detection": [
            {"edge": edge, "bets": bets} for edge, bets in S.detection_table()
        ],
    }
    record["headline"] = headline(record)
    return record


# ---------------------------------------------------------------------------
# Rendering — a pure function of the record
# ---------------------------------------------------------------------------


def _pct(value: object) -> str:
    number = _as_float(value)
    return "unbounded" if number is None else f"{number:+.1%}"


def _interval_cells(claim: Mapping) -> tuple[str, str, str]:
    """The return, its interval and the corrected interval — or three dashes.

    **Below `stats.MINIMUM_BETS` there is no number.** `stats.roi_table_row`
    prints the figure regardless, which is right for a table of measured markets
    and wrong here for the same reason `price_backtest.roi_cells` has its own
    renderer: printing a +12% over 40 bets invites somebody to quote it out of
    the row that qualifies it.
    """
    if not claim.get("enough_evidence"):
        return "—", "—", "—"
    return (
        _pct(claim.get("roi")),
        f"{_pct(claim.get('low'))} to {_pct(claim.get('high'))}",
        f"{_pct(claim.get('adjusted_low'))} to {_pct(claim.get('adjusted_high'))}",
    )


def _tier_key(claim: Mapping) -> tuple:
    tier = _text(claim.get("tier"))
    order = TIER_ORDER.index(tier) if tier in TIER_ORDER else len(TIER_ORDER)
    return (order, tier, _text(claim.get("market")), _text(claim.get("cut")))


def _claims_table(claims: Sequence[Mapping]) -> list[str]:
    lines = [
        "| Market | Tier | Cut | Bets | Clusters | ROI | 95% interval "
        "| Family-corrected | Replication | Verdict |",
        "|:---|:---|:---|---:|---:|---:|:---|:---|:---|:---|",
    ]
    for claim in sorted(claims, key=_tier_key):
        roi, interval, corrected = _interval_cells(claim)
        if claim.get("replicated"):
            replication = f"**replicated** ({_text(claim.get('replication_label')) or 'held-out window'})"
        elif _text(claim.get("replication")):
            replication = (
                f"{_text(claim.get('replication'))} on the "
                f"{_text(claim.get('replication_label')) or 'held-out'} window"
            )
        else:
            replication = "no held-out test has been run"
        verdict = _text(claim.get("verdict"))
        if claim.get("settlement_suspect"):
            verdict = (
                "**not evidence** — the settlement rule cannot be verified; "
                f"stated in the stats vocabulary it would read *{verdict}*"
            )
        lines.append(
            f"| `{_text(claim.get('market'))}` | {_text(claim.get('tier'))} "
            f"| {_text(claim.get('cut'))} | {_as_int(claim.get('bets')):,} "
            f"| {_as_int(claim.get('clusters')):,} "
            f"{_text(claim.get('cluster_unit')) or 'game'}s "
            f"| {roi} | {interval} | {corrected} | {replication} | {verdict} |"
        )
    return lines


def render(record: Mapping) -> str:
    """The markdown, as a pure function of the record.

    No clock, no disk, no network. That is what makes re-rendering free, which
    is what makes improving a sentence free, which is what stops this document
    being hand-edited — and a hand-edited generated file survives exactly one
    re-render.
    """
    version = _as_int(record.get("record_version"))
    if version != RECORD_VERSION:
        raise ClaimsError(
            f"This is a version {version} claims record and this module renders "
            f"version {RECORD_VERSION}. Rebuild it rather than rendering a "
            "record whose shape has changed — a stale record renders a report "
            "with holes in it and nothing looks wrong."
        )

    correction = record.get("correction", {}) or {}
    claims = [c for c in record.get("claims", []) or [] if isinstance(c, Mapping)]
    game_claims = [c for c in claims if not c.get("is_futures")]
    futures_claims = [c for c in claims if c.get("is_futures")]
    backtest_claims = [c for c in game_claims if _text(c.get("source")) == FROM_BACKTEST]
    forward_claims = [c for c in game_claims if _text(c.get("source")) == FROM_FORWARD]

    lines: list[str] = []
    add = lines.append

    add(f"# What the evidence actually supports — {_text(record.get('title'))}")
    add("")
    add(
        "Generated from the measurement records on disk, so it cannot drift "
        "from them. The hand-written rules — written before the first "
        "measurement, which is the whole point of them — live in "
        "`docs/what_we_can_and_cannot_claim.md`. **This file is re-rendered "
        "from its own run record and is never edited by hand.**"
    )
    add("")
    add(f"- Generated: {_text(record.get('generated_at'))}")
    add(
        f"- Sample floor: **{_as_int(record.get('minimum_bets')):,} bets**, "
        "declared in advance. Below it this document prints a phrase and not a "
        "number."
    )
    add("")
    # RECOMPUTED, never read from `record["headline"]`. The record carries a
    # copy for the run log and for anything that reads the JSON, but the
    # rendered headline is derived from the claims table sitting directly below
    # it — so a headline and the numbers under it cannot disagree, whatever a
    # stale or hand-edited record says.
    add(headline(record))
    add("")

    # --- the correction ----------------------------------------------------
    add("## The correction this document applies")
    add("")
    if not correction.get("applied"):
        add(
            "**No experiment ledger was found, so no family-wise correction "
            "could be applied.** Every interval below is therefore an "
            "*uncorrected* 95% interval, and an uncorrected interval on a lab "
            "that runs a search every week means less than it appears to. That "
            "is a fault in the instrument, not a licence to read the numbers "
            "as they stand."
        )
    else:
        add(
            f"**{_as_int(correction.get('hypotheses')):,} distinct hypotheses "
            "have ever been tested here**, and every interval below is widened "
            f"by **x{float(correction.get('factor', 1.0)):.2f}** before it "
            "means what it says. That is the ledger's **cumulative** count and "
            "never the day's: *a search that runs every week is not twelve "
            "tests, it is twelve tests a week, forever.*"
        )
        add("")
        add(
            f"- Alpha budget: **{_as_int(correction.get('budget_per_week'))} new "
            "hypotheses a week**, declared "
            f"{_text(correction.get('budget_declared_on')) or '—'}. When it is "
            "spent the search waits; it never lowers the bar."
        )
        add(
            f"- {_as_int(correction.get('discovery')):,} discovery, "
            f"{_as_int(correction.get('holdout')):,} holdout. Putting a "
            "discovery finding to the holdout is a second look and is counted "
            "as one."
        )
        if _as_int(correction.get("reversals")):
            add(
                f"- {_as_int(correction.get('reversals')):,} prediction(s) "
                "reversed outright. A reversal is a result, not a failure, and "
                "it is only sayable because a direction was written down before "
                "the number was seen."
            )
    add("")
    add(
        "The correction is re-applied here at render time rather than copied "
        "out of the record it came from. A backtest run in December carries "
        "December's family size; by March the ledger has grown and the same "
        "number means less. This can only ever make an interval wider."
    )
    add("")

    # --- measured ----------------------------------------------------------
    add("## Measured against real prices")
    add("")
    if not game_claims:
        add(
            f"**{NOTHING_TO_MEASURE.capitalize()}.** No historical price has "
            "been bought and no frozen opinion has settled, so there is no "
            "return to report — not a zero, not a null, and not a table with "
            "nothing in it. An empty table reads as a null result, and a null "
            "result is a claim."
        )
        add("")
    else:
        add(
            "**Never pooled across Division I.** High-major, mid-major and "
            "low-major are different distributions, so every row below is one "
            "market in one tier. A policy that wins in low-major games and "
            "loses in high-major ships in low-major only, if it ships at all."
        )
        add("")
        if backtest_claims:
            add(f"### {FROM_BACKTEST.capitalize()}")
            add("")
            add(
                "Prices bought after the games resolved. **A backtest that "
                "beats the opening number is not a bet**, and no figure here is "
                "evidence that a price was reachable at card time."
            )
            add("")
            lines.extend(_claims_table(backtest_claims))
            add("")
        if forward_claims:
            add(f"### {FROM_FORWARD.capitalize()}")
            add("")
            add(
                "Opinions written down before tip and settled against the box "
                "score afterwards, never re-priced. This is the only genuinely "
                "out-of-sample evidence this project will ever have, and it "
                "accumulates one game day at a time. The **opinions** cut is "
                "every frozen view; the **bets** cut is the subset that cleared "
                "the declared edge threshold and could have been selected. Both "
                "are reported, so the choice between them cannot flatter "
                "either."
            )
            add("")
            lines.extend(_claims_table(forward_claims))
            add("")

    # --- futures -----------------------------------------------------------
    if futures_claims:
        add("## Futures, apart from everything above")
        add("")
        add(
            "**No futures return is ever folded into a headline ROI computed "
            "over game bets.** They tie up stake for months, they settle on a "
            "different clock, and their return is not comparable to a "
            "single-game bet. The hold time belongs beside every number here."
        )
        add("")
        lines.extend(_claims_table(futures_claims))
        add("")

    # --- pooled ------------------------------------------------------------
    pooled = [r for r in record.get("pooled", []) or [] if isinstance(r, Mapping)]
    if pooled:
        add("## Pooled across Division I, and never the headline")
        add("")
        add(backtest.POOLED_CAVEAT)
        add("")
        add("| Cell | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |")
        add("|:---|---:|---:|---:|:---|:---|:---|")
        for row in pooled:
            if not row.get("enough_evidence"):
                roi, interval, corrected = "—", "—", "—"
            else:
                roi = _pct(row.get("roi"))
                interval = f"{_pct(row.get('low'))} to {_pct(row.get('high'))}"
                corrected = (
                    f"{_pct(row.get('adjusted_low'))} to "
                    f"{_pct(row.get('adjusted_high'))}"
                )
            add(
                f"| {_text(row.get('name'))} | {_as_int(row.get('bets')):,} "
                f"| {_as_int(row.get('clusters')):,} "
                f"{_text(row.get('cluster_unit')) or 'game'}s | {roi} "
                f"| {interval} | {corrected} | {_text(row.get('verdict'))} |"
            )
        add("")

    # --- what is in force --------------------------------------------------
    add("## What is in force, and what the card may actually use")
    add("")
    policy = record.get("policy", {}) or {}
    add(f"- {_text(policy.get('summary'))}")
    if policy.get("manual_only"):
        add(
            "- **No market is allowlisted, and that is the correct state.** "
            "`withdraw()` exists in `staging_provider_policy.py` and `grant()` "
            "does not: this lab may take a market away from the card and may "
            "never give it one. Adding a market is a receipt Cooper signs, in a "
            "pull request whose policy gate is green."
        )
    if _as_int(policy.get("withdrawn")):
        add(
            f"- {_as_int(policy.get('withdrawn'))} allowlist(s) have been "
            "withdrawn. Withdrawal is automatic and one-directional; a "
            "withdrawn market is not a market judged to have no value."
        )
    add("")
    add(
        "Every modelling policy is a **recorded verdict read from disk**, never "
        "an assertion in code, so what ships is auditable against the "
        "experiment that decided it. A missing verdict file ships nothing — the "
        "conservative reading of *no recorded decision* is *no policy in force*."
    )
    add("")
    for entry in record.get("verdicts", []) or []:
        if isinstance(entry, Mapping):
            add(f"- {_text(entry.get('citation'))}")
    add("")

    # --- not measured ------------------------------------------------------
    add("## Not measured against real prices")
    add("")
    unmeasured = [r for r in record.get("unmeasured", []) or [] if isinstance(r, Mapping)]
    if unmeasured:
        # Grouped by the reason they share. Thirty-five markets each carrying
        # the same sentence is a wall nobody reads, and a wall nobody reads is
        # where a market with a *different* reason goes unnoticed.
        grouped: dict[str, list[Mapping]] = {}
        for row in unmeasured:
            grouped.setdefault(_text(row.get("reason")), []).append(row)
        for reason, rows in sorted(grouped.items(), key=lambda kv: -len(kv[1])):
            add(f"- **{len(rows)} market(s)** — {reason}.")
            add(
                "  - "
                + ", ".join(
                    f"`{_text(r.get('market'))}` (settles on "
                    f"`{_text(r.get('settles_on'))}`)"
                    for r in rows
                )
            )
    else:
        add("- Every market this lab prices has a measurement.")
    add("")
    add(NOT_A_NO_VALUE_CALL)
    add("")

    # --- gated -------------------------------------------------------------
    gated = [r for r in record.get("gated", []) or [] if isinstance(r, Mapping)]
    if gated:
        add("## Priced, frozen and settled — and unable to produce a selection")
        add("")
        add(
            "Division I men's basketball has **no mandated injury report**. "
            "Measured on 2026-09-01: ESPN's men's-college-basketball injuries "
            "endpoint is permanently empty, CollegeBasketballData has no "
            "availability endpoint at all, and the conference reports that "
            "exist cover roughly 115 of 365 teams, conference games only, which "
            "leaves two thirds of the division and the whole of November and "
            "December uncovered. A gate that read a missing feed as *nobody is "
            "injured* would clear an entire slate."
        )
        add("")
        add(
            f"So nothing reaches `Availability.CONFIRMED`, and these "
            f"{len(gated)} market(s) are priced, frozen and settled but "
            "**cannot produce a selection**: "
            + ", ".join(f"`{_text(r.get('market'))}`" for r in gated)
            + "."
        )
        add("")
        add(NOT_A_NO_VALUE_CALL)
        add("")

    # --- deferred ----------------------------------------------------------
    deferred = [r for r in record.get("deferred", []) or [] if isinstance(r, Mapping)]
    if deferred:
        add("## Provider keys this lab does not wire, and why")
        add("")
        add(
            "Nothing is silently dropped. A market nobody quotes and a market "
            "that **cannot exist** look identical in a coverage report and mean "
            "completely different things, so every unwired provider key carries "
            "its reason."
        )
        add("")
        for group in deferred:
            keys = [str(k) for k in group.get("provider_keys", []) or []]
            add(f"- **{len(keys)} key(s)** — {_text(group.get('reason'))}")
            add(f"  - {', '.join(f'`{k}`' for k in keys)}")
        add("")
        add(NOT_A_NO_VALUE_CALL)
        add("")

    # --- reachability ------------------------------------------------------
    add("## Reachability")
    add("")
    add(
        "**A soft number you cannot bet is not an edge.** Edge is measured "
        "against a price actually available at the moment the card is produced, "
        "at a US book Cooper can open, regions `us,us2` — and it is reported "
        "separately for prices that survived to the next capture and prices "
        "that did not. If a measured edge lives entirely in prices that vanish "
        f"within minutes, it is reported as **{forward_evidence.NOT_REACHABLE}**, "
        "in those words, regardless of its size or its significance."
    )
    add("")
    add(
        "The survival split is computed in `data/outputs/"
        f"{forward_evidence.REPORT_MARKDOWN_FILENAME}`. Nothing above has "
        "cleared the bars that would make reachability the deciding question."
        if not demonstrated_edges(record)
        else (
            "The survival split for every result above is in "
            f"`data/outputs/{forward_evidence.REPORT_MARKDOWN_FILENAME}` and it "
            "governs: a result that lives only in prices that did not survive "
            f"is **{forward_evidence.NOT_REACHABLE}**."
        )
    )
    add("")

    # --- how much data ------------------------------------------------------
    add("## How much data would settle it")
    add("")
    add("| If the true edge were | Bets needed to separate it from zero |")
    add("|---:|---:|")
    for row in record.get("detection", []) or []:
        if isinstance(row, Mapping):
            add(f"| {float(row.get('edge', 0.0)):+.0%} | ~{_as_int(row.get('bets')):,} |")
    add("")
    stopping = record.get("stopping_rule", {}) or {}
    forward = record.get("forward", {}) or {}
    add(
        f"`docs/when_this_ends.md` set the decision date at "
        f"**{_text(stopping.get('decision_date'))}** and the sample floor at "
        f"**{_as_int(stopping.get('floor_opinions')):,} settled opinions across "
        f"at least {_as_int(stopping.get('floor_games')):,} distinct games**, "
        "both declared on 2026-09-01 before any data existed. "
        f"The forward ledger currently holds "
        f"**{_as_int(forward.get('settled_opinions')):,} settled opinions**. "
        "Below the floor the correct action is to diagnose the pipeline and "
        "**not to read the number**."
    )
    add("")

    # --- provenance ---------------------------------------------------------
    add("## Where every number above came from")
    add("")
    for label, block in (
        ("Experiment ledger", {"path": _text(correction.get("source")), "found": bool(correction.get("applied"))}),
        ("Price backtest", record.get("backtest", {}) or {}),
        ("Forward-evidence ledger", record.get("forward", {}) or {}),
        ("Replication record", record.get("replication", {}) or {}),
    ):
        path = _text(block.get("path"))
        if block.get("error"):
            state = f"**present and unreadable** — {_text(block.get('error'))}"
        elif block.get("found"):
            state = "read"
        else:
            state = "**not found**, so this document says nothing about it"
        add(f"- {label}: `{path}` — {state}")
    add("")
    add(
        "A file that is missing and a file that is unreadable are reported "
        "differently and deliberately. An unreadable measurement is a broken "
        "instrument, and reporting a broken instrument as *nothing measured* "
        "turns a fault into a null result."
    )
    add("")

    # --- standing notes -----------------------------------------------------
    add("## Standing notes")
    add("")
    for note in (
        f"An interval that includes zero means **{S.NO_DEMONSTRATED_EDGE}**. Not "
        "'promising', not 'trending positive', not 'small but positive'.",
        "An interval that excludes zero **on the losing side** is a "
        f"**{S.DEMONSTRATED_DEFICIT}** and is named as one. It is never "
        "reported as a result that survived and replicated, which is exactly "
        "what a sibling lab's version of this document once did on a market "
        "returning −6.6%.",
        "Calibration can rule a model out. It can never rule one in. A market "
        "with only a calibration number has no price-based evidence, and this "
        "document will not present one as though it did.",
        "A result clears three things before it counts: enough bets, an "
        "interval that survives correcting for everything this lab has ever "
        "tested, and then holding on a window it was not found on. Clearing "
        "the first two and failing the third is the ordinary outcome, not a "
        "surprise.",
        "Every interval is clustered by game **and** by day, and the wider of "
        "the two is reported. One game supplies many correlated bets; a "
        "hundred-game Tuesday is not a thousand independent observations.",
        "**No market reaches the card without a reviewed human acceptance "
        "receipt**, whatever the numbers above say. This lab may withdraw an "
        "allowlist and may never grant one.",
        "The card produced by this repository is **accumulating evidence, not "
        "making recommendations**, and it says so on its face.",
        "Two sibling labs have finished and both measured no edge. That is the "
        "honest prior this document was written under, and a full-build "
        "instruction is an instruction about effort, never about the result.",
    ):
        add(f"- {note}")
    add("")
    return "\n".join(lines).rstrip() + "\n"


# ---------------------------------------------------------------------------
# Record and report IO
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
        raise ClaimsError(
            f"No claims record at {target}. This report is re-rendered from its "
            "record and never written by hand, so without the record there is "
            "nothing to render — run `scripts/run_what_we_can_claim.py` first."
        )
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ClaimsError(
            f"The claims record at {target} could not be read. Refusing to "
            "render a partial report over a good one."
        ) from exc
    if not isinstance(record, dict):
        raise ClaimsError(f"The claims record at {target} is not a JSON object.")
    return record


def write_report(record: Mapping, path: Path) -> Path:
    """Render and write, refusing the vocabulary of a tipster.

    The check is on the rendered text rather than on the source, because the
    phrase that matters is the one a reader sees.
    """
    rendered = render(record)
    lowered = rendered.casefold()
    for phrase in FORBIDDEN_PHRASES:
        if re.search(rf"\b{re.escape(phrase)}\b", lowered):
            raise ClaimsError(
                f"The claims document contains the phrase {phrase!r}, which "
                "this repository does not use about its own results. A "
                "generated summary that reaches for one of these has stopped "
                "reporting and started selling."
            )
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    return target
