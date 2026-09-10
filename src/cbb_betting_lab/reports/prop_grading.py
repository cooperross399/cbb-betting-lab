"""Design section 10's scoring of the player-prop model, per tier and never pooled.

    # The whole store, walk-forward, scored once:
    PYTHONPATH=src python scripts/run_prop_grading.py

    # Re-render the report from the committed record, at today's ledger count:
    PYTHONPATH=src python scripts/run_prop_grading.py --rebuild-report-only

This module is the metric. `scripts/run_prop_grading.py` is the run that feeds
it: it reconciles the store's wager census, prices every prop walk-forward with
the model AND with the identity-blind role-prior control, settles what it
priced, and hands the frame here. Nothing below opens a file, prices a wager or
settles one; :func:`render` is a pure function of :func:`build_record`'s output,
so the report re-renders at the ledger's current count for free.

## What is compared against what

**The benchmark is a DE-VIGGED two-sided fair price, joined on the same event,
market, athlete, line AND book.** Not the vigged implied probability: two sides
of a two-way market at -110 imply 52.4% each and sum to 104.8%, so scoring
against the raw number gives the model a handicap worth the whole hold and
turns a losing model into one that appears to win. The vigged comparison is
computed here and is printed once, in a section that says in its own heading
that it is a diagnostic and never a headline — for the one reason
`forecast_skill.VIG_HANDICAP` gives: if the model loses to the handicapped
market, there is no de-vig methodology argument left to have.

**Both de-vigs are reported and the LEAST FAVOURABLE TO THE MODEL is the
headline.** :data:`DEVIG_METHODS` is proportional (each side's raw implied
probability divided by their sum) and power (the exponent `k` solving
`p_over^k + p_under^k = 1`, which is the log-odds family's two-way member). The
two disagree by construction on favourites and longshots, and the direction is
MEASURED here rather than asserted: at -400 / +300 (overround 1.0500) the
favourite's fair probability is 0.7619 proportional against 0.7824 power, and at
+150 / -180 the longshot's is 0.3836 against 0.3760 — so power shades a
favourite UP and a longshot DOWN relative to proportional. At -110 / -110 they
are equal to fourteen decimal places, because a symmetric pair has no
favourite-longshot asymmetry for either method to disagree about. Choosing
between them after seeing which flatters the model is the move this repository
exists to prevent. Both pairs are formed ONCE, by one call, so the two methods can never
disagree about which rows are a pair.

**Two probability conventions, for the same reason.** All ten player markets
carry `push_possible=True`, so `P(win) + P(loss) + P(push) = 1` while a
two-sided de-vig normalises two sides to 1 and knows nothing about a push. The
scored population excludes pushes (they are counted, never scored — a push is
not half a win), so the like-for-like model number is the CONDITIONAL
`P(win) / (P(win) + P(loss))`. The card's own convention is the unconditional
`P(win)`, which counts the push against the bet. Both are scored, and the
headline is the least favourable of the four combinations of de-vig and
convention. The measured push mass is printed beside them so a reader can see
how much the choice could have been worth.

## The two baselines, printed BEFORE the model

1. **The de-vigged fair price.** Its own mean log loss and Brier over the same
   rows. This is the thing the thirty pre-registered hypotheses name.
2. **The identity-blind role-prior control.** The same engine, the same minutes
   lattice, the same lines — with every per-minute rate replaced by the role
   prior at the athlete's projected-minutes bucket and the scoring mix replaced
   by the league's. It is `player_rates.shrink_rate` with the credibility weight
   at zero: the athlete's ROLE, with his identity removed. It is ledger entries
   H31 to H33, one per tier, and `tests/test_player_model_leakage.py` has
   carried it as an open leak test (L6) since before the engine existed.

They are printed first because a model that beats neither has nothing to
explain, and a table that leads with the model invites a reader to read its
number before the two that qualify it.

## Metric

Mean **log loss** per scored wager, plus **Brier**, plus **calibration by
decile**. The advantage a cell reports is

    advantage = (baseline mean log loss) - (model mean log loss)

so a POSITIVE advantage is the model doing better, which is the direction the
thirty hypotheses predict ("the model's mean log loss is below the de-vigged
two-sided fair price's"). An interval that includes zero is
:data:`stats.NO_DEMONSTRATED_EDGE` in exactly those words; one that excludes
zero on the losing side is a :data:`stats.DEMONSTRATED_DEFICIT`, which is a
finding and not a null result.

A probability of exactly 0 or 1 has infinite log loss, so every probability is
clipped into :data:`PROBABILITY_FLOOR`. The number of rows clipped is counted
per source and printed: a clip is a number this module changed, and a changed
number that nobody counted is the shape of defect this lab keeps finding.

## Intervals cluster THREE ways and the widest wins

Game, day and **athlete** — `stats.interval_three_way`. The athlete is not
optional here and is not a refinement of the game: `player_points` carries a
mean 7.19 lines per subject on this store, so 78,984 wagers are about 8,803
subject-opinions under the declared casefold, and a game holds two whole
rosters. The subject is `stores.normalise_subject`, the lab's declared fold,
and never the book's raw spelling — under the raw spelling one athlete under
two capitalisations is two clusters.

## Coverage, beside every verdict

A rung with no opposite side at the same book gets **no fair price at all**, so
the scored population is the two-sided part of the ladder and nothing else.
Coverage is reported per cell, and the ladder is cut at
:data:`BENCHMARKED_RUNGS` rungs from the money — the line closest to the middle
of that athlete's quoted ladder for that market. Beyond it, two-sided coverage
collapses, so whatever survives out there is a small and selected slice of a
much larger offer: it is reported as :data:`UNBENCHMARKED` and never as an edge,
however its interval falls.

## Per tier, never pooled

`high_major`, `mid_major` and `low_major` are three distributions and a pooled
all-of-Division-I headline is banned in this repository. There is no pooled row
in this record and no function here computes one. The thirty market hypotheses
are (market x tier); the three control hypotheses are per tier, pooled across
the ten priceable markets, which is what the ledger registered and is not a
pooling across tiers.

## The two markets refused by name

`player_first_basket` and `player_double_double` are refused BY NAME. They are
filtered out before the gate, are never scored, never given a verdict, and are
not a pass, an avoid or a no-value call. `player_census.without_markets_refused_
by_name` is the filter and it is called here rather than restated.

## The family correction

Applied at the experiment ledger's CURRENT count through
`restatement`, never at whatever a record was scored under. The record keeps
what its run was scored at; :func:`restated` re-derives every corrected interval
and every verdict from the run's own point estimates and standard errors at
render time, and can therefore only ever retract a claim.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
import dataclasses
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from cbb_betting_lab import restatement as RESTATEMENT
from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.models import player_census
from cbb_betting_lab.models import player_rates as PR
from cbb_betting_lab.reports.forecast_skill import (
    MINIMUM_OVERROUND,
    VIG_HANDICAP,
    implied_probability,
    pair_key,
)
from cbb_betting_lab.reports.price_backtest import (
    NOTHING_TO_MEASURE,
    SCORABLE_OUTCOMES,
    TIER_ORDER,
    ledger_path,
    looks_from_ledger,
)
from cbb_betting_lab.season import clean_text
from cbb_betting_lab.stores import normalise_subject

__all__ = [
    "PropGradingError",
    "PropGradingInputs",
    "build_record",
    "render",
    "restated",
    "record_path",
    "report_path",
    "write_record",
    "read_record",
    "write_report",
    "ledger_path",
    "looks_from_ledger",
]


class PropGradingError(RuntimeError):
    """A precondition of the metric is absent, so nothing was scored."""


#: The stem every output of this measurement carries, so the record, the report
#: and the sentence a restated report points a reader back at cannot disagree.
REPORT_STEM = "prop_grading"


#: Bumped when the record's shape changes, so a stale record fails loudly at
#: re-render rather than rendering a report with holes in it.
#:
#: 2 -- every calibration bin carries `wagers` beside `rows` and its floor is
#: taken on the wagers. A version-1 record has only the quote count, and the
#: renderer that filled a *Wagers* column from it is the reason this bumped:
#: re-rendering one would print the same overstated sample the bump exists to
#: retire, so a version-1 record is refused and the measurement is re-run.
RECORD_VERSION = 2

#: What a scored row must carry. A **missing column raises**: the football lab's
#: backtest read a missing settlement column as a zero through
#: `getattr(..., None)`, reported zero bets, and that read as "the model never
#: disagrees enough" when the price columns had never been built.
GRADED_COLUMNS: tuple[str, ...] = (
    "event_id",
    "slate_date",
    "market",
    "segment",
    "player",
    "selection",
    "line",
    "book",
    "american_odds",
    "tier",
    "outcome",
    "model_probability",
    "model_push_mass",
    "control_probability",
    "control_push_mass",
)

#: The two de-vigs, both reported, the least favourable to the model headlined.
DEVIG_PROPORTIONAL = "proportional"
DEVIG_POWER = "power"
DEVIG_METHODS: tuple[str, ...] = (DEVIG_PROPORTIONAL, DEVIG_POWER)

#: The two probability conventions. `conditional` renormalises the model over
#: the two outcomes a scored row can have, which is what a two-way de-vigged
#: fair price is; `unconditional` is the card's own `P(win)`, which counts the
#: push against the bet. Both are scored and the least favourable is headlined.
CONVENTION_CONDITIONAL = "conditional"
CONVENTION_UNCONDITIONAL = "unconditional"
CONVENTIONS: tuple[str, ...] = (CONVENTION_CONDITIONAL, CONVENTION_UNCONDITIONAL)

#: How a probability is kept out of an infinite log loss, and it is DECLARED
#: rather than chosen per run. Every clip is counted and printed per source.
PROBABILITY_FLOOR = 1e-6

#: How far from the money the ladder is benchmarked. Design section 10: two-
#: sided coverage is ~99% at the money and ~1% beyond three rungs out, so what
#: survives past this is a selected slice of a much larger offer.
BENCHMARKED_RUNGS = 3

#: The word for a cell that lives past that, whatever its interval says.
UNBENCHMARKED = "unbenchmarked"

#: The reserved phrase for a cell with no measurable rung distance. A subject
#: quoted at one line has no ladder to be far along, so it is AT the money by
#: construction, and this exists only so a reader can see that it was decided
#: rather than defaulted.
SINGLE_RUNG = 0

#: Rows below this get a phrase and never a number.
#: `stats.MINIMUM_BETS`, restated so a reader of this module sees which floor
#: binds and imported so there is one value.
MINIMUM_ROWS = S.MINIMUM_BETS

#: Below this many clusters there is no interval either, whatever the row
#: count: a cluster-robust ratio estimator is downward biased with few
#: clusters, and this repository's standing anxiety is intervals that are too
#: narrow. `forecast_skill.MINIMUM_CLUSTERS`, restated for the same reason.
MINIMUM_CLUSTERS = 30

#: Below this many rows a calibration bin prints its count and no frequency.
MINIMUM_BUCKET = 30

#: The ten markets the model is registered against, in the order the ledger
#: registered them. Read off the estimator rather than typed: the hypotheses
#: are (market x tier) and a market list that drifted from the model's would
#: silently answer a hypothesis nobody registered.
PRICED_MARKETS: tuple[str, ...] = tuple(PR.PRICED_MARKETS)

#: The three tiers the thirty-three hypotheses were registered over, and the
#: only three this report has a section for. `price_backtest.TIER_ORDER` carries
#: a fourth, `unplaced`, which is what design 9's tier table calls a team it
#: could not place from measured non-conference margin. A wager on an unplaced
#: event is COUNTED -- `PopulationCensus.no_tier` -- and is scored nowhere: it
#: belongs to no registered hypothesis, and giving it a section would be a
#: fourth cell nobody pre-registered sitting in a table of thirty that were.
GRADED_TIERS: tuple[str, ...] = tuple(
    tier for tier in TIER_ORDER if tier != "unplaced"
)

#: The subject fold, named in the record every time. `stores.normalise_subject`
#: is the lab's declaration and is imported rather than re-implemented: the
#: athlete-clustered interval is a function of this fold and a second copy of it
#: would move every one of them without anything saying so.
DECLARED_SUBJECT_FOLD = "stores.normalise_subject (casefold)"

#: The two ledger searches the 33 pre-registered hypotheses live under. Read
#: off the tracked ledger by the run and passed in, never re-typed here: a
#: second copy of a hypothesis name would let this report answer a question the
#: ledger did not ask, under a name that looked like one it did.
SEARCH_VS_DEVIG = "player_props_vs_devig"
SEARCH_VS_CONTROL = "player_props_vs_role_prior"

#: The sentence printed above every de-vigged number.
DEVIG_SENTENCE = (
    "Market-implied probabilities are de-vigged **two ways and the least "
    "favourable to the model is the headline**. *Proportional*: the two sides' "
    "raw implied probabilities are divided by their sum. *Power*: the exponent "
    "`k` solving `p_over^k + p_under^k = 1`, the two-way member of the "
    "log-odds family. They disagree by construction on favourites and "
    "longshots, this lab has not measured which is right for a college "
    "basketball prop, and picking one after seeing which flatters the model is "
    "the move the rest of this repository exists to prevent. Both are formed "
    "from ONE pairing pass, so they cannot disagree about which rows are a pair."
)

#: The sentence printed above every un-de-vigged number.
VIGGED_IS_NEVER_A_HEADLINE = (
    "**This section is a diagnostic and is never a headline.** Comparing a "
    "model against the VIGGED implied probability hands it the whole hold and "
    "turns a losing model into one that appears to win. `forecast_skill` "
    "already states why it is printed at all, and its sentence is quoted here "
    "rather than reworded so the two reports cannot drift:\n\n> " + VIG_HANDICAP
)

#: The sentence that separates the two comparisons, printed wherever both
#: appear. It is the single likeliest misreading of this report: the control is
#: a NEGATIVE control, and beating it says the model's per-athlete evidence is
#: worth something over knowing his role. It says nothing whatever about the
#: market, and the tier's own verdict is the market comparison and only that.
CONTROL_IS_NOT_THE_MARKET = (
    "**Beating the control is not beating the market, and the verdict above is "
    "the market comparison only.** The identity-blind role-prior control is a "
    "NEGATIVE control: it is the same engine told the athlete's role and not "
    "his identity, and a model that beats it has shown that its per-athlete "
    "evidence is worth something over a role table. A model can beat that "
    "control decisively and still lose to a de-vigged fair price, which is the "
    "only comparison that bears on whether anything here could be bet — and "
    "nothing here can be bet in any case."
)

#: What a cell says when the ladder it lives on was never benchmarked.
UNBENCHMARKED_SENTENCE = (
    "**Unbenchmarked.** These rows sit more than "
    f"{BENCHMARKED_RUNGS} rungs from the money, where two-sided coverage "
    "collapses: whatever has a fair price out here is a small and selected "
    "slice of a much larger offer, and the selection is the book's rather than "
    "this lab's. Whatever the interval below says, it is NOT an edge and is "
    "not reported as one."
)

#: The advantage keys a cell carries, in the order they are read. Every one of
#: them is `(baseline mean log loss) - (model mean log loss)`, so positive is
#: the model doing better.
ADVANTAGE_KEYS: tuple[str, ...] = tuple(
    f"{baseline}__{convention}"
    for baseline in (
        f"devig_{DEVIG_PROPORTIONAL}",
        f"devig_{DEVIG_POWER}",
        "control",
    )
    for convention in CONVENTIONS
)

#: Which of those the headline is chosen from. The control is a different
#: hypothesis (H31-H33) and is never allowed to stand in for the de-vig
#: comparison, so the headline over the market is picked from the four de-vig
#: cells alone.
HEADLINE_KEYS: tuple[str, ...] = tuple(
    key for key in ADVANTAGE_KEYS if key.startswith("devig_")
)

#: The control's own headline, chosen the same way over its two conventions.
CONTROL_KEYS: tuple[str, ...] = tuple(
    key for key in ADVANTAGE_KEYS if key.startswith("control__")
)

#: The two comparisons a cell can be read against, each as
#: `(which headline the cell stores, which family must agree)`. They are named
#: here rather than chosen at each call site so that a reader asking for the
#: control cannot be answered with the market's verdict, which is what happened
#: while the answered-hypotheses table picked its own headline by hand.
COMPARISONS: dict[str, tuple[str, tuple[str, ...]]] = {
    "market": ("headline", HEADLINE_KEYS),
    "control": ("control_headline", CONTROL_KEYS),
}


# --------------------------------------------------------------------------
# The de-vig: one pairing pass, two methods
# --------------------------------------------------------------------------


def power_exponent(first: float, second: float) -> float:
    """`k` with `first**k + second**k == 1`, by bisection. NaN when there is none.

    The two-way member of the log-odds family. Both probabilities are strictly
    inside (0, 1) and their sum is strictly above one for a real pair, so
    `f(k) = first**k + second**k - 1` is continuous, strictly decreasing, and
    positive at `k = 1`; the root is unique and above one. Bisection rather than
    Newton because there is no derivative to get wrong and no starting point to
    tune, and because a solver that fails silently on a pathological pair would
    put a fabricated fair price into a measurement.

    A pair this cannot solve returns NaN and the caller counts it. It is never
    defaulted to the proportional answer: the whole point of reporting two
    de-vigs is that they are two, and a power column that quietly held
    proportional numbers on the hard rows would be one method wearing two names.
    """
    low, high = 1.0, 1.0
    if not (0.0 < first < 1.0 and 0.0 < second < 1.0):
        return float("nan")
    if not (first + second) > MINIMUM_OVERROUND:
        return float("nan")
    # Walk the upper bracket out rather than assuming one: a pair at 1.0001
    # overround needs a k barely above 1, and a 1.20 overround on a heavy
    # favourite can need a large one.
    for _ in range(200):
        high *= 2.0
        if first**high + second**high < 1.0:
            break
    else:  # pragma: no cover - unreachable for probabilities inside (0, 1)
        return float("nan")
    for _ in range(200):
        middle = 0.5 * (low + high)
        value = first**middle + second**middle - 1.0
        if value > 0:
            low = middle
        else:
            high = middle
        if high - low < 1e-13:
            break
    return 0.5 * (low + high)


@dataclass
class DevigCensus:
    """Why a supplied row carries no fair price. Counted, never imputed.

    `supplied = devigged + excluded` reconciles and :func:`build_record` refuses
    a record when it does not: a measurement that silently loses a third of its
    rows still prints an interval, and the interval looks fine.
    """

    supplied: int = 0
    devigged: int = 0
    unknown_selection: int = 0
    unreadable_price: int = 0
    no_complement: int = 0
    not_two_sided: int = 0
    overround_not_above_one: int = 0
    power_unsolved: int = 0
    scope: str = "book"

    @property
    def excluded(self) -> int:
        return (
            self.unknown_selection
            + self.unreadable_price
            + self.no_complement
            + self.not_two_sided
            + self.overround_not_above_one
            + self.power_unsolved
        )

    @property
    def reconciles(self) -> bool:
        return self.devigged + self.excluded == self.supplied

    def to_json(self) -> dict:
        return {
            "scope": self.scope,
            "supplied": self.supplied,
            "devigged": self.devigged,
            "excluded": self.excluded,
            "reconciles": self.reconciles,
            "unknown_selection": self.unknown_selection,
            "unreadable_price": self.unreadable_price,
            "no_complement": self.no_complement,
            "not_two_sided": self.not_two_sided,
            "overround_not_above_one": self.overround_not_above_one,
            "power_unsolved": self.power_unsolved,
        }


def devig(frame: pd.DataFrame) -> tuple[pd.DataFrame, DevigCensus]:
    """Add `fair_proportional`, `fair_power`, `market_implied_raw`, `overround`.

    **The pair is the same event, market, athlete, line AND book**, which is
    design section 10's join and is the only pair that has a hold in it at all.
    Pairing across books understates the hold — two books' best prices can sum
    below one — and the row that comes out of that is not a fair price, it is an
    arbitrage wearing one.

    One pass forms the pairs and both methods are applied to it, so the two
    de-vigs are two readings of one population rather than two populations.
    A row whose pair cannot be formed keeps a **missing** fair price and the
    reason is counted: a missing price stays missing is this lab's first hard
    rule, and a de-vig is a price.

    The athlete in the pair key is `pair_key`'s casefold of the `player`
    column, which is the same fold `stores.normalise_subject` declares — so the
    pair, the cluster and the census all agree about who one athlete is.
    """
    census = DevigCensus(supplied=int(len(frame)))
    if frame.empty:
        empty = pd.Series(dtype="float64")
        return (
            frame.assign(
                fair_proportional=empty,
                fair_power=empty,
                market_implied_raw=empty,
                overround=empty,
                devig_exponent=empty,
            ),
            census,
        )

    records = frame.to_dict("records")
    raw = [implied_probability(r.get("american_odds")) for r in records]
    keys: list[tuple | None] = []
    for position, record in enumerate(records):
        key = pair_key(record)
        if key is None:
            census.unknown_selection += 1
            keys.append(None)
            continue
        if not (raw[position] == raw[position]):  # NaN
            census.unreadable_price += 1
            keys.append(None)
            continue
        keys.append(key + (clean_text(record.get("book")),))

    groups: dict[tuple, list[int]] = {}
    for position, key in enumerate(keys):
        if key is not None:
            groups.setdefault(key, []).append(position)

    size = len(records)
    proportional = [float("nan")] * size
    power = [float("nan")] * size
    overrounds = [float("nan")] * size
    exponents = [float("nan")] * size
    for _key, positions in groups.items():
        sides = {clean_text(records[p].get("selection")) for p in positions}
        if len(positions) == 1:
            census.no_complement += 1
            continue
        if len(positions) != 2 or len(sides) != 2:
            census.not_two_sided += len(positions)
            continue
        first, second = positions
        total = raw[first] + raw[second]
        if not (total > MINIMUM_OVERROUND):
            census.overround_not_above_one += 2
            continue
        exponent = power_exponent(raw[first], raw[second])
        if not (exponent == exponent):  # NaN
            # Counted rather than filled from the other method. See
            # :func:`power_exponent`.
            census.power_unsolved += 2
            continue
        for position in positions:
            proportional[position] = raw[position] / total
            power[position] = raw[position] ** exponent
            overrounds[position] = total
            exponents[position] = exponent
        census.devigged += 2

    index = frame.index
    return (
        frame.assign(
            fair_proportional=pd.Series(proportional, index=index, dtype="float64"),
            fair_power=pd.Series(power, index=index, dtype="float64"),
            market_implied_raw=pd.Series(raw, index=index, dtype="float64"),
            overround=pd.Series(overrounds, index=index, dtype="float64"),
            devig_exponent=pd.Series(exponents, index=index, dtype="float64"),
        ),
        census,
    )


def overround_summary(frame: pd.DataFrame) -> dict:
    """The hold this de-vig actually removed, measured, with its `n`.

    Printed because the de-vig is otherwise invisible: a population whose median
    overround is 1.02 and one whose median is 1.12 are different instruments,
    and the second is where the two methods have the most room to disagree.
    """
    blank = {"pairs": 0, "rows": 0, "median": None, "mean": None,
             "minimum": None, "maximum": None, "median_exponent": None}
    if frame.empty or "overround" not in frame.columns:
        return blank
    values = pd.to_numeric(frame["overround"], errors="coerce").dropna()
    if values.empty:
        return blank
    exponents = pd.to_numeric(
        frame.get("devig_exponent", pd.Series(dtype="float64")), errors="coerce"
    ).dropna()
    return {
        # Two rows share one pair's overround, so the pair count is half the rows.
        "pairs": int(len(values) // 2),
        "rows": int(len(values)),
        "median": float(values.median()),
        "mean": float(values.mean()),
        "minimum": float(values.min()),
        "maximum": float(values.max()),
        "median_exponent": float(exponents.median()) if not exponents.empty else None,
    }


# --------------------------------------------------------------------------
# The ladder: how far from the money a rung sits
# --------------------------------------------------------------------------


def rungs_from_the_money(frame: pd.DataFrame) -> pd.Series:
    """How many rungs out along its own ladder each row's line sits.

    The ladder is one athlete's distinct quoted lines on one market on one
    event, over every book, sorted. **Distance is counted in RUNGS and never in
    points**, because the ladders in this store are not evenly spaced: measured
    on the 2024 card store, the gap between adjacent quoted lines is 1.0 on
    1,444 steps and 2.0 on 858, and a points ladder can run
    `9.5, 11.5, 12.5, 14.5` — so a fixed half-point unit would call one rung out
    on an assists ladder two rungs and one rung out on a points ladder four.

    **The money is the rung the market prices closest to a coin flip**, which is
    a fact about the offer and takes nothing at all from the model: using the
    model's own central estimate here would make the coverage table a statement
    about the model rather than about what could be benchmarked. The raw implied
    probability is enough for this and no de-vig is needed — the hold shifts
    both sides of every rung on a ladder by about the same amount, so it moves
    which rung is nearest to even hardly at all, and a rung with only one side
    quoted has no de-vigged price to be picked by.

    A subject quoted at exactly one line is at rung :data:`SINGLE_RUNG` by
    construction: there is no ladder for it to be far along. A ladder whose
    prices cannot be read falls back to its middle rung by rank, and that is a
    fallback rather than a measurement — it is the honest centre of a ladder
    nobody could price.
    """
    if frame.empty:
        return pd.Series(dtype="float64")
    lines = pd.to_numeric(frame["line"], errors="coerce")
    over = frame["selection"].astype(str).str.strip().str.lower().eq("over")
    raw = pd.Series(
        [implied_probability(value) for value in frame["american_odds"]],
        index=frame.index,
        dtype="float64",
    )
    # One number per (rung, side): the over's own implied probability, or one
    # minus the under's where only the under is quoted. Median across books,
    # because two books' prices on one rung are two readings of one rung.
    grouped = pd.DataFrame(
        {
            "event_id": frame["event_id"].astype(str),
            "market": frame["market"].astype(str),
            "subject": frame["player"].map(normalise_subject),
            "line": lines,
            "over_implied": raw.where(over, 1.0 - raw),
        }
    )
    per_rung = (
        grouped.groupby(["event_id", "market", "subject", "line"], dropna=True)[
            "over_implied"
        ]
        .median()
        .reset_index()
    )
    distance: dict[tuple, float] = {}
    for keys, rungs in per_rung.groupby(["event_id", "market", "subject"], sort=False):
        ordered = rungs.sort_values("line").reset_index(drop=True)
        prices = ordered["over_implied"]
        if prices.notna().any():
            money = int((prices - 0.5).abs().idxmin())
        else:
            money = (len(ordered) - 1) // 2
        for position, line in enumerate(ordered["line"]):
            distance[(keys[0], keys[1], keys[2], float(line))] = float(
                abs(position - money)
            )
    key = list(
        zip(
            grouped["event_id"],
            grouped["market"],
            grouped["subject"],
            grouped["line"],
        )
    )
    return pd.Series(
        [distance.get(k, float("nan")) for k in key], index=frame.index, dtype="float64"
    )


# --------------------------------------------------------------------------
# The scorable population
# --------------------------------------------------------------------------


@dataclass
class PopulationCensus:
    """Why a de-vigged row is still not in the metric's denominator."""

    devigged: int = 0
    scored: int = 0
    no_model_probability: int = 0
    no_control_probability: int = 0
    push: int = 0
    void: int = 0
    unsettleable: int = 0
    other_outcome: int = 0
    no_tier: int = 0
    unbenchmarked: int = 0

    @property
    def excluded(self) -> int:
        return (
            self.no_model_probability
            + self.no_control_probability
            + self.push
            + self.void
            + self.unsettleable
            + self.other_outcome
            + self.no_tier
            + self.unbenchmarked
        )

    @property
    def reconciles(self) -> bool:
        return self.scored + self.excluded == self.devigged

    def to_json(self) -> dict:
        return {
            "devigged": self.devigged,
            "scored": self.scored,
            "excluded": self.excluded,
            "reconciles": self.reconciles,
            "no_model_probability": self.no_model_probability,
            "no_control_probability": self.no_control_probability,
            "push": self.push,
            "void": self.void,
            "unsettleable": self.unsettleable,
            "other_outcome": self.other_outcome,
            "no_tier": self.no_tier,
            "unbenchmarked": self.unbenchmarked,
        }


def scorable(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, PopulationCensus]:
    """`(benchmarked, unbenchmarked, census)`. Everything else is excluded and counted.

    A row reaches the metric when it has a fair price under BOTH de-vigs, a
    model probability, a control probability, a won-or-lost outcome and a tier.
    A push is not half a win and is scored nowhere; a void is a returned stake;
    an `unsettleable` row is this lab admitting it cannot grade it and is never
    counted as a loss.

    The far ladder is separated rather than dropped: it is returned as its own
    frame so the record can report it under :data:`UNBENCHMARKED` and never as
    an edge. The census counts it as an exclusion from the benchmarked
    population, which is what it is.
    """
    census = PopulationCensus()
    if frame.empty or "fair_proportional" not in frame.columns:
        return frame.iloc[0:0], frame.iloc[0:0], census
    paired = frame[
        pd.to_numeric(frame["fair_proportional"], errors="coerce").notna()
        & pd.to_numeric(frame["fair_power"], errors="coerce").notna()
    ]
    census.devigged = int(len(paired))
    if paired.empty:
        return paired, paired, census

    model = pd.to_numeric(paired["model_probability"], errors="coerce")
    control = pd.to_numeric(paired["control_probability"], errors="coerce")
    outcome = paired["outcome"].astype(str).str.strip().str.lower()
    tier = paired["tier"].astype(str).str.strip()

    census.no_model_probability = int(model.isna().sum())
    have_model = model.notna()
    census.no_control_probability = int((have_model & control.isna()).sum())
    have_both = have_model & control.notna()
    census.push = int((have_both & (outcome == "push")).sum())
    census.void = int((have_both & (outcome == "void")).sum())
    census.unsettleable = int((have_both & (outcome == "unsettleable")).sum())
    settled = have_both & outcome.isin(sorted(SCORABLE_OUTCOMES))
    census.other_outcome = int(
        (have_both & ~settled & ~outcome.isin(["push", "void", "unsettleable"])).sum()
    )
    tiered = settled & tier.isin(GRADED_TIERS)
    census.no_tier = int((settled & ~tiered).sum())

    rungs = pd.to_numeric(paired["rungs_from_the_money"], errors="coerce")
    near = tiered & (rungs <= BENCHMARKED_RUNGS)
    far = tiered & ~(rungs <= BENCHMARKED_RUNGS)
    census.unbenchmarked = int(far.sum())
    census.scored = int(near.sum())
    return paired[near], paired[far], census


# --------------------------------------------------------------------------
# The metric
# --------------------------------------------------------------------------


def _clip(values: pd.Series) -> tuple[pd.Series, int]:
    """Probabilities inside `[floor, 1 - floor]`, and how many moved."""
    numbers = pd.to_numeric(values, errors="coerce")
    clipped = numbers.clip(lower=PROBABILITY_FLOOR, upper=1.0 - PROBABILITY_FLOOR)
    moved = int((numbers != clipped).sum())
    return clipped, moved


def log_loss(probability: pd.Series, won: pd.Series) -> pd.Series:
    """`-[y log p + (1-y) log(1-p)]`, per row. Lower is better."""
    p = np.asarray(probability, dtype=float)
    y = np.asarray(won, dtype=float)
    return pd.Series(
        -(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)),
        index=getattr(probability, "index", None),
        dtype="float64",
    )


def brier(probability: pd.Series, won: pd.Series) -> pd.Series:
    """`(p - y)^2`, per row. Lower is better."""
    p = np.asarray(probability, dtype=float)
    y = np.asarray(won, dtype=float)
    return pd.Series(
        (p - y) ** 2, index=getattr(probability, "index", None), dtype="float64"
    )


def prepared(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Every per-row number the metric reads, added once. Returns `(frame, clips)`.

    The model's two conventions are built here and nowhere else, so a caller
    cannot end up with one of them: `unconditional` is `P(win)` as the card
    computes it, with the push counted against the bet; `conditional` is
    `P(win) / (P(win) + P(loss))`, which is what a two-sided de-vigged fair
    price is and is therefore the like-for-like comparison on a population that
    excludes pushes. A row whose two outcomes carry no mass at all keeps a
    missing conditional probability rather than a defaulted one.
    """
    if frame.empty:
        return frame, {}
    won = frame["outcome"].astype(str).str.strip().str.lower().eq("won").astype(float)
    out = frame.assign(won=won)
    clips: dict[str, int] = {}

    model_unconditional = pd.to_numeric(out["model_probability"], errors="coerce")
    model_push = pd.to_numeric(out["model_push_mass"], errors="coerce").fillna(0.0)
    control_unconditional = pd.to_numeric(out["control_probability"], errors="coerce")
    control_push = pd.to_numeric(out["control_push_mass"], errors="coerce").fillna(0.0)

    def conditional(win: pd.Series, push: pd.Series) -> pd.Series:
        denominator = 1.0 - push
        return win.where(denominator > 0) / denominator.where(denominator > 0)

    sources = {
        f"model__{CONVENTION_UNCONDITIONAL}": model_unconditional,
        f"model__{CONVENTION_CONDITIONAL}": conditional(model_unconditional, model_push),
        f"control__{CONVENTION_UNCONDITIONAL}": control_unconditional,
        f"control__{CONVENTION_CONDITIONAL}": conditional(
            control_unconditional, control_push
        ),
        f"devig_{DEVIG_PROPORTIONAL}": pd.to_numeric(
            out["fair_proportional"], errors="coerce"
        ),
        f"devig_{DEVIG_POWER}": pd.to_numeric(out["fair_power"], errors="coerce"),
        "vigged_market": pd.to_numeric(out["market_implied_raw"], errors="coerce"),
    }
    # A de-vigged fair price knows nothing about a push, so it is the same
    # number under both conventions and is stored under both names rather than
    # special-cased at every read.
    for method in DEVIG_METHODS:
        for convention in CONVENTIONS:
            sources[f"devig_{method}__{convention}"] = sources[f"devig_{method}"]
    for convention in CONVENTIONS:
        sources[f"vigged_market__{convention}"] = sources["vigged_market"]

    for name, series in sources.items():
        values, moved = _clip(series)
        out[f"p__{name}"] = values
        out[f"logloss__{name}"] = log_loss(values, out["won"])
        out[f"brier__{name}"] = brier(values, out["won"])
        if moved:
            clips[name] = moved
    for key in ADVANTAGE_KEYS:
        baseline, convention = key.split("__")
        out[f"advantage__{key}"] = (
            out[f"logloss__{baseline}__{convention}"]
            - out[f"logloss__model__{convention}"]
        )
    for convention in CONVENTIONS:
        out[f"advantage__vigged_market__{convention}"] = (
            out[f"logloss__vigged_market__{convention}"]
            - out[f"logloss__model__{convention}"]
        )
    out["subject"] = out["player"].map(normalise_subject)
    return out, clips


def _interval_row(interval: S.RoiInterval, *, label: str, scored_rows: int) -> dict:
    """One stored interval, in the shape `restatement` restates.

    `rows` is the WAGER count and `scored_rows` is the row count, and they are
    different numbers on purpose: the estimator runs over one row per (wager,
    book) because the de-vig joins on the book, and the declared 200-unit floor
    is a floor on BETS. Storing the row count as `rows` would let a wager
    quoted at five books clear a floor on its own, and `restatement.rebuild_cell`
    -- which recomputes `enough_evidence` from this field on every re-render --
    would keep doing it for the life of the record.
    """
    return {
        "label": label,
        "value": float(interval.roi),
        "rows": int(interval.bets),
        "scored_rows": int(scored_rows),
        "clusters": int(interval.clusters),
        "cluster_unit": str(interval.cluster_unit),
        "low": float(interval.low),
        "high": float(interval.high),
        "standard_error": float(interval.standard_error),
        "looks": int(interval.looks),
        "adjusted_low": float(interval.adjusted_low),
        "adjusted_high": float(interval.adjusted_high),
        "enough_evidence": bool(interval.enough_evidence),
        "survives_correction": bool(interval.survives_correction),
        "verdict": interval.verdict(),
    }


def advantage_interval(frame: pd.DataFrame, *, key: str, looks: int) -> dict:
    """One advantage, clustered three ways, the widest reported.

    The ratio estimator over one row per scored quote with a weight of one,
    which is the mean of the per-row advantage — the same arithmetic
    `stats.interval_by_cluster` uses for a return, handed a per-row quantity
    that is not money.

    The floor is then applied in WAGERS rather than rows. See
    :func:`_interval_row`.
    """
    column = f"advantage__{key}"
    usable = frame.assign(
        _value=pd.to_numeric(frame[column], errors="coerce")
    ).dropna(subset=["_value"])
    interval = S.interval_three_way(
        usable,
        game_column="event_id",
        day_column="slate_date",
        subject_column="subject",
        profit_column="_value",
        looks=looks,
    )
    interval = dataclasses.replace(interval, bets=wagers_in(usable))
    row = _interval_row(interval, label=key, scored_rows=int(len(usable)))
    if interval.clusters < MINIMUM_CLUSTERS:
        # Not a narrower interval and not a wider one: no interval. A
        # cluster-robust sandwich with nine clusters prints a number that is an
        # artefact of the estimator rather than a fact about the model.
        row["enough_evidence"] = False
        row["survives_correction"] = False
        row["verdict"] = (
            f"not enough evidence ({interval.clusters:,} "
            f"{interval.cluster_unit} cluster(s), below the "
            f"{MINIMUM_CLUSTERS:,} declared in advance)"
        )
        row["below_the_cluster_floor"] = True
    else:
        row["below_the_cluster_floor"] = False
    return row


def _means(frame: pd.DataFrame, name: str) -> dict:
    """The mean log loss and Brier of one probability source over these rows."""
    return {
        "log_loss": float(pd.to_numeric(frame[f"logloss__{name}"], errors="coerce").mean()),
        "brier": float(pd.to_numeric(frame[f"brier__{name}"], errors="coerce").mean()),
    }


def calibration_by_decile(frame: pd.DataFrame, *, name: str) -> list[dict]:
    """Ten fixed bins of predicted probability, with what actually happened.

    The bins are DECLARED at the tenths and never computed as quantiles of the
    sample: quantiles move with the data, so the same model measured twice
    produces two incomparable tables. A bin below :data:`MINIMUM_BUCKET`
    **wagers** carries its counts and no frequency — the point estimate of nine
    observations invites a reader to follow the shape of the line rather than
    the sample sizes under it.

    **Each bin carries both counts and the floor is taken on the wagers.** A
    row here is one quote, so a wager hung at five books lands in the same bin
    five times: the mean is over quotes, but the independent unit under it is
    the wager, and a floor applied to quotes lets a bin of 30 rows clear it on
    11 bets. Measured on this store a high-major tier's scored population is
    130,988 quotes over 46,370 wagers -- 2.82 quotes per bet, and 4.38 in the
    worst cell -- so a table that headed the quote count *Wagers*, which the
    first version of this one did, overstated its own sample by that much.
    """
    if frame.empty:
        return []
    probability = pd.to_numeric(frame[f"p__{name}"], errors="coerce")
    won = pd.to_numeric(frame["won"], errors="coerce")
    rows: list[dict] = []
    for index in range(10):
        low, high = index / 10.0, (index + 1) / 10.0
        inside = (probability >= low) & (
            (probability < high) if index < 9 else (probability <= high)
        )
        count = int(inside.sum())
        wagers = wagers_in(frame.loc[inside])
        row = {
            "bin": f"{low:.0%}-{high:.0%}",
            "low": low,
            "high": high,
            "rows": count,
            "wagers": wagers,
            "enough_wagers": wagers >= MINIMUM_BUCKET,
            "predicted": None,
            "realised": None,
            "gap_points": None,
        }
        if wagers >= MINIMUM_BUCKET:
            predicted = float(probability[inside].mean())
            realised = float(won[inside].mean())
            row["predicted"] = predicted
            row["realised"] = realised
            row["gap_points"] = 100.0 * (predicted - realised)
        rows.append(row)
    return rows


#: What makes two rows the same WAGER. The quote identity minus the book, which
#: is `card_pricing.Wager`'s own definition: the same selection at the same line
#: on the same event is one bet however many books hang it. The athlete enters
#: under the DECLARED FOLD and never under the book's raw spelling — see
#: :func:`wagers_in`.
WAGER_IDENTITY: tuple[str, ...] = (
    "event_id",
    "market",
    "subject",
    "selection",
    "line",
)


def wagers_in(frame: pd.DataFrame) -> int:
    """How many distinct wagers these rows are. Rows are quotes, not wagers.

    The scored population is one row per (wager, book), because design section
    10's de-vig joins on the book and a rung's fair price is the book's own. The
    OFFERED count the accounting identity produces is one per wager. Comparing
    the two without collapsing is how a coverage figure comes out above 100%,
    which it did on the first run of this report.

    **The athlete is folded by `stores.normalise_subject` before the count is
    taken.** That is the lab's declared subject and it is the fold the store's
    own census counts under: 261,870 wagers under the book's raw spelling and
    257,474 under the fold, a difference of 4,396 wagers carrying two rows
    apiece. Counting here under the raw spelling would put one athlete's wager
    in this denominator twice, inflate every coverage share against a census
    that folded, and let a cell clear the declared 200-BET floor on wagers that
    are one bet.
    """
    if frame.empty:
        return 0
    keys = frame.assign(subject=frame["player"].map(normalise_subject))
    return int(len(keys.drop_duplicates(subset=list(WAGER_IDENTITY))))


def coverage_of(offered: Mapping, scored: pd.DataFrame, far: pd.DataFrame) -> dict:
    """How much of what the store offered reached a fair price, and how far out.

    `offered` is the run's own count of wagers in this cell, taken from the
    accounting identity rather than from the frame — a frame that has already
    been filtered cannot say what it was filtered from. **Every count here is
    in WAGERS**, on both sides, because the scored frame is one row per quote
    and the offered count is one per wager.
    """
    near_wagers = wagers_in(scored)
    far_wagers = wagers_in(far)
    settled = int(offered.get("settled", 0))
    return {
        "offered": int(offered.get("offered", 0)),
        "priced": int(offered.get("priced", 0)),
        "settled": settled,
        "two_sided": near_wagers + far_wagers,
        "benchmarked": near_wagers,
        "unbenchmarked": far_wagers,
        "scored_rows": int(len(scored)),
        "unbenchmarked_rows": int(len(far)),
        "two_sided_share_of_settled": (
            (near_wagers + far_wagers) / settled if settled else None
        ),
    }


def coverage_by_rung(offered: pd.DataFrame) -> list[dict]:
    """Two-sided coverage against rung distance, over the whole priced offer.

    This is the table design section 10's coverage sentence is about: ~99% at
    the money, ~1% beyond three rungs out.

    **The denominator is every priced-and-settled row, paired or not.** That is
    the only denominator this question has: a rung with no opposite side at the
    same book is exactly what the table is counting, so building it over the
    rows that DID pair would report 100% at every distance and say nothing.
    """
    if offered.empty:
        return []
    rungs = pd.to_numeric(offered["rungs_from_the_money"], errors="coerce")
    paired = pd.to_numeric(offered["fair_proportional"], errors="coerce").notna()
    rows: list[dict] = []
    for rung in sorted(int(r) for r in rungs.dropna().unique()):
        inside = rungs == rung
        count = int(inside.sum())
        with_pair = int((inside & paired).sum())
        rows.append(
            {
                "rungs": rung,
                "rows": count,
                "two_sided": with_pair,
                "share": (with_pair / count) if count else None,
                "benchmarked": rung <= BENCHMARKED_RUNGS,
            }
        )
    return rows


def measure(
    frame: pd.DataFrame,
    *,
    looks: int,
    label: str,
    tier: str,
    market: str = "",
    benchmarked: bool = True,
) -> dict:
    """One cell: both baselines, then the model, then every advantage.

    The order of the keys is the order the renderer prints them, and it is the
    order design section 10 asks for: the de-vigged fair price and the
    identity-blind control BEFORE the model.
    """
    cell = {
        "label": label,
        "tier": tier,
        "market": market,
        "benchmarked": bool(benchmarked),
        "rows": wagers_in(frame),
        "scored_rows": int(len(frame)),
        "games": int(frame["event_id"].nunique()) if not frame.empty else 0,
        "days": int(frame["slate_date"].nunique()) if not frame.empty else 0,
        "athletes": int(frame["subject"].nunique()) if not frame.empty else 0,
        "books": int(frame["book"].nunique()) if not frame.empty else 0,
        "won": int(pd.to_numeric(frame["won"], errors="coerce").sum())
        if not frame.empty
        else 0,
        "enough_evidence": bool(wagers_in(frame) >= MINIMUM_ROWS),
    }
    if frame.empty:
        cell["baselines"] = {}
        cell["model"] = {}
        cell["advantages"] = {}
        cell["headline"] = None
        cell["control_headline"] = None
        cell["verdict"] = (
            f"not enough evidence (0 wagers, below the {MINIMUM_ROWS:,} "
            "declared in advance)"
        )
        return cell

    cell["baselines"] = {
        f"devig_{method}": _means(frame, f"devig_{method}") for method in DEVIG_METHODS
    } | {
        f"control__{convention}": _means(frame, f"control__{convention}")
        for convention in CONVENTIONS
    }
    cell["model"] = {
        convention: _means(frame, f"model__{convention}") for convention in CONVENTIONS
    }
    cell["vigged_market_diagnostic"] = _means(frame, "vigged_market")
    cell["push_mass"] = {
        "model_mean": float(
            pd.to_numeric(frame["model_push_mass"], errors="coerce").mean()
        ),
        "control_mean": float(
            pd.to_numeric(frame["control_push_mass"], errors="coerce").mean()
        ),
    }
    cell["advantages"] = {
        key: advantage_interval(frame, key=key, looks=looks) for key in ADVANTAGE_KEYS
    }
    cell["vigged_market_advantage"] = {
        convention: advantage_interval(
            frame, key=f"vigged_market__{convention}", looks=looks
        )
        for convention in CONVENTIONS
    }
    cell["headline"] = _least_favourable(cell["advantages"], HEADLINE_KEYS)
    cell["control_headline"] = _least_favourable(cell["advantages"], CONTROL_KEYS)
    cell["verdict"] = verdict_of(cell)
    return cell


def _least_favourable(advantages: Mapping, keys: Sequence[str]) -> str:
    """Which of these advantage cells is least favourable to the model.

    The point estimate, and the point estimate alone. A rule that picked the
    weakest LOWER BOUND would sometimes headline the cell whose interval is
    widest rather than the comparison the model does worst under, and the two
    come apart exactly where the sample sizes differ. Ties go to the first key
    in :data:`ADVANTAGE_KEYS`, which is a declared order and not the data's.
    """
    present = [key for key in keys if key in advantages]
    if not present:
        return ""
    return min(present, key=lambda key: float(advantages[key]["value"]))


def verdict_of(cell: Mapping, *, against: str = "market") -> str:
    """The one sentence this cell is permitted to be described by.

    `against` picks WHICH comparison is being read: `"market"` for the
    de-vigged fair price, which is the only one that bears on whether anything
    could be bet, or `"control"` for the identity-blind role prior. The four
    rules below are the same either way; what changes is the headline they read
    and the family they check for agreement. The parameter exists because the
    answered-hypotheses table used to skip this function entirely for the three
    control hypotheses and print the headline row's raw verdict, which applied
    neither rule 2 nor rule 4 to them.

    Four rules, in this order:

    1. Below the declared row floor, or below the cluster floor, it is *not
       enough evidence* and there is no number.
    2. Past :data:`BENCHMARKED_RUNGS`, it is :data:`UNBENCHMARKED` whatever the
       interval says. An "edge" living on the far ladder is a statement about
       which rungs a book chose to hang two sides on.
    3. Otherwise the headline advantage's own verdict — which reads the sign off
       the CORRECTED bounds, so an interval excluding zero on the losing side is
       a demonstrated deficit and never a null result.
    4. And a demonstrated edge requires EVERY de-vig and EVERY convention to
       show one, not just the headline: the headline is the least favourable
       point estimate, and a cell whose weakest comparison excludes zero on the
       winning side while another does not has not shown the same thing twice.
    """
    if against not in COMPARISONS:
        raise PropGradingError(
            f"verdict_of was asked to read {against!r}, and the only "
            f"comparisons this record carries are {sorted(COMPARISONS)}."
        )
    headline_key, family = COMPARISONS[against]
    if not cell.get("advantages"):
        return (
            f"not enough evidence ({int(cell.get('rows', 0)):,} wagers, below "
            f"the {MINIMUM_ROWS:,} declared in advance)"
        )
    headline = cell.get(headline_key) or ""
    row = cell["advantages"].get(headline) or {}
    if not cell.get("enough_evidence"):
        return (
            f"not enough evidence ({int(cell.get('rows', 0)):,} wagers, below "
            f"the {MINIMUM_ROWS:,} declared in advance)"
        )
    if not row.get("enough_evidence"):
        return str(row.get("verdict") or S.NO_DEMONSTRATED_EDGE)
    if not cell.get("benchmarked", True):
        return UNBENCHMARKED
    verdict = str(row.get("verdict") or S.NO_DEMONSTRATED_EDGE)
    if verdict == S.DEMONSTRATED_EDGE:
        every = [
            cell["advantages"][key].get("verdict") for key in family
            if key in cell["advantages"]
        ]
        if any(one != S.DEMONSTRATED_EDGE for one in every):
            return S.NO_DEMONSTRATED_EDGE
    return verdict


def reading_of(cell: Mapping, row: Mapping) -> str:
    """What ONE comparison inside `cell` is permitted to be read as.

    :func:`verdict_of` decides the cell. This decides a single row of its
    advantage table, and it exists because a row's own `verdict` reads nothing
    but the sign of its corrected bounds and knows nothing about where the row
    lives. Printed unfiltered under the far-ladder heading, a row reading
    *demonstrated edge* contradicts :data:`UNBENCHMARKED_SENTENCE` three lines
    above it -- which promises, in those words, that whatever the interval
    below says it is NOT an edge and is not reported as one. The heading was
    right and the column was wrong.

    A deficit is suppressed for the same reason an edge is, and not because it
    is unflattering: past :data:`BENCHMARKED_RUNGS` the sign of the difference
    is a statement about which rungs a book chose to hang two sides on, and
    that is true whichever way it points. It is exactly rule 2 of
    :func:`verdict_of`, applied one row lower down.
    """
    verdict = str(row.get("verdict") or "")
    if cell.get("benchmarked", True):
        return verdict
    if verdict in (S.DEMONSTRATED_EDGE, S.DEMONSTRATED_DEFICIT):
        return UNBENCHMARKED
    return verdict


# --------------------------------------------------------------------------
# The record
# --------------------------------------------------------------------------


@dataclass
class PropGradingInputs:
    """Everything :func:`build_record` is handed. It opens nothing itself."""

    graded: pd.DataFrame
    source: str = ""
    season_label: str = ""
    snapshot_phase: str = ""
    model: str = ""
    control: str = ""
    store: Mapping = field(default_factory=dict)
    #: The run's own accounting of every prop the store offered, per
    #: (market, tier). Coverage is reported against THIS and never against the
    #: frame, because a frame that has already been filtered cannot say what it
    #: was filtered from.
    offered: Mapping = field(default_factory=dict)
    #: The accounting identity's buckets, carried through so the report can say
    #: what became of every prop the store offered without re-deriving it.
    accounting: Mapping = field(default_factory=dict)
    #: The pre-registered hypotheses, as the tracked experiment ledger holds
    #: them: `{"search": ..., "name": ..., "predicted_direction": ...}`. Passed
    #: in rather than read here, because `render` is a pure function of the
    #: record and a module that opened the ledger could not be. Every one of
    #: them must find a cell or :func:`build_record` refuses — see
    #: :func:`answered_hypotheses`.
    hypotheses: Sequence[Mapping] = field(default_factory=tuple)


def require_columns(frame: pd.DataFrame, columns: Sequence[str], what: str) -> None:
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise PropGradingError(
            f"{what} is missing {missing}. Nothing is defaulted: a missing "
            "column read as a zero is how a wiring fault becomes a finding."
        )


def build_record(
    inputs: PropGradingInputs,
    *,
    competition: Competition = CBB,
    looks: int = 1,
    generated_at: str = "",
) -> dict:
    """Every number this run made, as plain data. `render` is pure over it.

    **The census gate runs first, before anything is read off the frame.** A
    gate after the de-vig is a gate on the report and not on the run, which is
    the property `tests/test_player_census_reconciles.py::test_the_guard_is_the_
    first_thing_each_entry_point_does` holds over every name in
    `player_census.GRADING_ENTRY_POINTS`, and this function is one of them.
    Both receipts are required and both fail closed: the store's own wager count
    reconciled against the frozen artifact, and the run's own accounting that
    every prop the store offered landed in exactly one bucket.

    The refusal filter runs immediately after, so a receipt never lets a market
    refused BY NAME be scored: `player_first_basket` and `player_double_double`
    are dropped here, are never given a verdict, and are not a pass, an avoid or
    a no-value call.
    """
    player_census.guard_graded_frame(inputs.graded, what="prop_grading.build_record")
    # Bound first and then filtered back onto the SAME name, so every line
    # below sees the filtered frame and there is no second variable still
    # holding the unfiltered one. `tests/test_forward_evidence.py::
    # _assert_gate_precedes_filter` reads exactly this shape off the syntax
    # tree, and it reads it that way because three earlier versions of the
    # check passed against a filter whose result was discarded.
    graded = inputs.graded
    graded = PR.without_markets_refused_by_name(graded)
    if not graded.empty:
        require_columns(graded, GRADED_COLUMNS, "the graded prop frame")

    priced, devig_census = devig(graded)
    if not devig_census.reconciles:
        raise PropGradingError(
            f"The de-vig census does not reconcile: {devig_census.devigged:,} "
            f"de-vigged plus {devig_census.excluded:,} excluded is not the "
            f"{devig_census.supplied:,} supplied. A row that reached neither "
            "bucket has vanished from the measurement, and the metric would "
            "still print an interval. Nothing was recorded."
        )
    if not priced.empty:
        priced = priced.assign(rungs_from_the_money=rungs_from_the_money(priced))
    else:
        priced = priced.assign(rungs_from_the_money=pd.Series(dtype="float64"))

    near, far, population_census = scorable(priced)
    if not population_census.reconciles:
        raise PropGradingError(
            f"The population census does not reconcile: "
            f"{population_census.scored:,} scored plus "
            f"{population_census.excluded:,} excluded is not the "
            f"{population_census.devigged:,} de-vigged. Nothing was recorded."
        )
    near, clips = prepared(near)
    far, far_clips = prepared(far)

    settled_offer = priced
    if not settled_offer.empty:
        settled_offer = settled_offer[
            settled_offer["outcome"].astype(str).str.strip().str.lower().isin(
                sorted(SCORABLE_OUTCOMES)
            )
        ]

    by_tier: list[dict] = []
    by_market_and_tier: list[dict] = []
    for tier in GRADED_TIERS:
        tier_rows = near[near["tier"].astype(str).str.strip() == tier] if not near.empty else near
        far_rows = far[far["tier"].astype(str).str.strip() == tier] if not far.empty else far
        cell = measure(
            tier_rows,
            looks=looks,
            label=f"{tier}: the ten priceable markets pooled",
            tier=tier,
        )
        cell["coverage"] = coverage_of(
            _offered_for(inputs.offered, tier=tier), tier_rows, far_rows
        )
        cell["unbenchmarked_cell"] = measure(
            far_rows,
            looks=looks,
            label=f"{tier}: past {BENCHMARKED_RUNGS} rungs",
            tier=tier,
            benchmarked=False,
        )
        cell["calibration"] = {
            f"model__{CONVENTION_CONDITIONAL}": calibration_by_decile(
                tier_rows, name=f"model__{CONVENTION_CONDITIONAL}"
            ),
            f"devig_{DEVIG_PROPORTIONAL}": calibration_by_decile(
                tier_rows, name=f"devig_{DEVIG_PROPORTIONAL}"
            ),
        }
        by_tier.append(cell)
        for market in PRICED_MARKETS:
            market_rows = (
                tier_rows[tier_rows["market"].astype(str).str.strip() == market]
                if not tier_rows.empty
                else tier_rows
            )
            far_market = (
                far_rows[far_rows["market"].astype(str).str.strip() == market]
                if not far_rows.empty
                else far_rows
            )
            market_cell = measure(
                market_rows,
                looks=looks,
                label=f"{market} / {tier}",
                tier=tier,
                market=market,
            )
            market_cell["coverage"] = coverage_of(
                _offered_for(inputs.offered, tier=tier, market=market),
                market_rows,
                far_market,
            )
            by_market_and_tier.append(market_cell)

    return {
        "record_version": RECORD_VERSION,
        "competition": competition.key,
        "title": competition.title,
        "generated_at": generated_at,
        "source": inputs.source,
        "season_label": inputs.season_label,
        "snapshot_phase": inputs.snapshot_phase,
        "model": inputs.model,
        "control": inputs.control,
        "store": dict(inputs.store),
        "declared_subject_fold": DECLARED_SUBJECT_FOLD,
        "devig_methods": list(DEVIG_METHODS),
        "conventions": list(CONVENTIONS),
        "probability_floor": PROBABILITY_FLOOR,
        "benchmarked_rungs": BENCHMARKED_RUNGS,
        "minimum_rows": MINIMUM_ROWS,
        "minimum_clusters": MINIMUM_CLUSTERS,
        "minimum_bucket": MINIMUM_BUCKET,
        "priced_markets": list(PRICED_MARKETS),
        "markets_refused_by_name": list(PR.MARKETS_REFUSED_BY_NAME),
        "looks": int(looks),
        "correction_factor": S.bonferroni_factor(int(looks)),
        "devig_census": devig_census.to_json(),
        "population_census": population_census.to_json(),
        "accounting": dict(inputs.accounting),
        "overround": overround_summary(priced),
        "probability_clips": dict(sorted(clips.items())),
        "probability_clips_unbenchmarked": dict(sorted(far_clips.items())),
        "coverage_by_rung": coverage_by_rung(settled_offer),
        "by_tier": by_tier,
        "by_market_and_tier": by_market_and_tier,
        "hypotheses": answered_hypotheses(
            inputs.hypotheses,
            by_tier=by_tier,
            by_market_and_tier=by_market_and_tier,
        ),
    }


def _cell_for_hypothesis(name: str) -> tuple[str, str]:
    """`(tier, market)` for a pre-registered name; `market` is `""` for a control.

    The names are the ledger's, and their shape is fixed by the registration:

        `player_points / high_major: the model's mean log loss is below ...`
        `high_major: the full model's mean log loss is below ...`

    Parsed rather than re-typed. A parse can go wrong, so
    :func:`answered_hypotheses` refuses a record in which any of the registered
    names failed to find a cell — the alternative, a second copy of 33 strings,
    goes wrong silently and stays wrong.
    """
    head = str(name).split(":", 1)[0].strip()
    if "/" in head:
        market, tier = (part.strip() for part in head.split("/", 1))
        return tier, market
    return head, ""


def answered_hypotheses(
    hypotheses: Sequence[Mapping],
    *,
    by_tier: Sequence[Mapping],
    by_market_and_tier: Sequence[Mapping],
) -> list[dict]:
    """Every registered hypothesis beside the cell that answers it.

    **This is the loop the pre-registration closes.** Thirty cells are
    (market x tier) against the de-vigged fair price and three are per tier
    against the identity-blind control, and each carries a direction fixed
    before the model existed. Reporting the cells without saying which
    registered question each one answers would leave a reader to match them by
    eye, which is how a cell nobody registered ends up in a table of cells that
    were.

    A registered name that finds no cell raises: the parse is the only thing
    joining the ledger to this record, and a silent miss would drop a
    hypothesis out of the answered set while every count above still looked
    right.
    """
    market_cells = {
        (str(cell["tier"]), str(cell["market"])): cell for cell in by_market_and_tier
    }
    tier_cells = {str(cell["tier"]): cell for cell in by_tier}
    answered: list[dict] = []
    for entry in hypotheses:
        search = str(entry.get("search", ""))
        name = str(entry.get("name", ""))
        tier, market = _cell_for_hypothesis(name)
        cell = market_cells.get((tier, market)) if market else tier_cells.get(tier)
        if cell is None:
            raise PropGradingError(
                f"The pre-registered hypothesis {name!r} names cell "
                f"(tier={tier!r}, market={market!r}) and this record has no "
                "such cell. The 33 were registered before the model existed "
                "and may not be added to, dropped or reworded; if a market or "
                "a tier was renamed, the rename is the thing to undo."
            )
        # WHICH comparison this hypothesis registered, taken from the
        # ledger's own `search` and never inferred from whether the cell
        # happens to name a market. The two agree on this record -- all 30
        # de-vig hypotheses are (market x tier) and all 3 control hypotheses
        # are per tier -- and the day they stop agreeing, the ledger is the
        # side that is right.
        against = "control" if search == SEARCH_VS_CONTROL else "market"
        headline_key, _family = COMPARISONS[against]
        headline = cell.get(headline_key)
        row = (cell.get("advantages") or {}).get(headline or "")
        answered.append(
            {
                "search": search,
                "name": name,
                "predicted_direction": str(entry.get("predicted_direction", "")),
                "tier": tier,
                "market": market,
                "comparison": headline or "",
                "rows": int(cell.get("rows", 0)),
                "estimate": float(row["value"]) if row else None,
                "adjusted_low": float(row["adjusted_low"]) if row else None,
                "adjusted_high": float(row["adjusted_high"]) if row else None,
                "enough_evidence": bool(row.get("enough_evidence")) if row else False,
                # The reading is `verdict_of`, which is the one function that
                # decides what a cell may be described by, asked about the
                # comparison this hypothesis registered. It used to be the
                # headline ROW's own verdict plus a refusal sentence written
                # out again here, and that had three consequences: the far
                # ladder's refusal (rule 2) and the every-comparison
                # requirement (rule 4) were skipped for every hypothesis, the
                # two copies of the refusal sentence drifted -- this one said
                # "bets" where `verdict_of` said "wagers" -- and a cell refused
                # for too few clusters was reported here as refused for too few
                # bets. Neither reason was false; they were two answers to one
                # question, which is how a table gets quoted against itself.
                "reading": verdict_of(cell, against=against),
            }
        )
    return answered


def _offered_for(offered: Mapping, *, tier: str, market: str = "") -> dict:
    """The run's own count of what the store offered in one cell.

    Keyed `tier` or `tier/market`, and an absent key is an empty count rather
    than a zero-filled one — the coverage line then says the run supplied no
    count for that cell instead of claiming it offered nothing.
    """
    key = f"{tier}/{market}" if market else tier
    found = offered.get(key)
    return dict(found) if isinstance(found, Mapping) else {}


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def _pct(value: float | None) -> str:
    return "—" if value is None else f"{value:.1%}"


def _detectable_cell(row: Mapping | None) -> str:
    """The smallest advantage this comparison could have demonstrated.

    In log-loss units, not percent: this table's estimate is
    `(baseline mean log loss) - (model mean log loss)`, so its detectable
    effect is on the same scale and printing a percentage here would invite a
    reader to compare it against the ROI column of a different report.

    Same construction as `price_backtest.mde_cell` and the same reason. Twenty
    of this record's thirty cells read *no demonstrated edge*, and those three
    words cover both a comparison that looked hard and found nothing and one
    that could not have seen an advantage twice the size of anything this lab
    has ever measured. Derived from the row's own `looks`, never stored, so it
    moves when the correction does.
    """
    if not row or not row.get("enough_evidence"):
        return "—"
    error = float(row.get("standard_error", 0.0) or 0.0)
    if not error:
        return "—"
    return f"±{S.bonferroni_z(int(row.get('looks', 1) or 1)) * error:.4f}"


def _advantage_cells(row: Mapping | None) -> tuple[str, str, str]:
    """The estimate, its interval and the corrected interval — or three dashes.

    **Below the declared floors there is no number.** A +0.03 advantage over
    forty wagers and a coin flip are the same claim at that sample size, and
    printing the +0.03 invites somebody to quote it out of the row that
    qualifies it.
    """
    if not row or not row.get("enough_evidence"):
        return "—", "—", "—"
    return (
        f"{row['value']:+.4f}",
        f"{row['low']:+.4f} to {row['high']:+.4f}",
        f"{row['adjusted_low']:+.4f} to {row['adjusted_high']:+.4f}",
    )


def _cluster_cell(row: Mapping | None) -> str:
    if not row:
        return "—"
    return f"{int(row.get('clusters', 0)):,} {row.get('cluster_unit', 'unknown')}s"


def _coverage_line(coverage: Mapping) -> str:
    if not coverage or not coverage.get("offered"):
        return (
            "*Coverage: the run supplied no offered count for this cell, so "
            "this report cannot say what share of the offer reached a fair "
            "price. That is a missing number and not a full one.*"
        )
    return (
        f"*Coverage, in wagers: {int(coverage['offered']):,} offered, "
        f"{int(coverage['priced']):,} priced, {int(coverage['settled']):,} "
        f"settled, {int(coverage['two_sided']):,} with a two-sided fair price "
        f"({_pct(coverage.get('two_sided_share_of_settled'))} of settled), of "
        f"which {int(coverage['benchmarked']):,} are within "
        f"{BENCHMARKED_RUNGS} rungs of the money and "
        f"{int(coverage['unbenchmarked']):,} are past it and unbenchmarked. "
        f"Those {int(coverage['benchmarked']):,} wagers are "
        f"{int(coverage.get('scored_rows', 0)):,} scored rows, one per book "
        "quoting them.*"
    )


def _baseline_table(cell: Mapping) -> list[str]:
    """The two baselines and then the model. In that order, always."""
    lines = [
        "| Source | Role | Mean log loss | Brier |",
        "|:---|:---|---:|---:|",
    ]
    baselines = cell.get("baselines") or {}
    for method in DEVIG_METHODS:
        found = baselines.get(f"devig_{method}") or {}
        if not found:
            continue
        lines.append(
            f"| de-vigged fair price ({method}) | baseline, printed first | "
            f"{found['log_loss']:.5f} | {found['brier']:.5f} |"
        )
    for convention in CONVENTIONS:
        found = baselines.get(f"control__{convention}") or {}
        if not found:
            continue
        lines.append(
            f"| identity-blind role-prior control ({convention}) | baseline, "
            f"printed first | {found['log_loss']:.5f} | {found['brier']:.5f} |"
        )
    for convention in CONVENTIONS:
        found = (cell.get("model") or {}).get(convention) or {}
        if not found:
            continue
        lines.append(
            f"| **the model ({convention})** | what is being tested | "
            f"{found['log_loss']:.5f} | {found['brier']:.5f} |"
        )
    lines.append("")
    return lines


def _advantage_table(cell: Mapping) -> list[str]:
    lines = [
        "| Comparison | Advantage (baseline − model log loss) | 95% interval | "
        "Family-corrected | Wagers | Clusters | Could detect | Reading |",
        "|:---|---:|:---|:---|---:|---:|---:|:---|",
    ]
    advantages = cell.get("advantages") or {}
    headline = cell.get("headline")
    for key in ADVANTAGE_KEYS:
        row = advantages.get(key)
        if not row:
            continue
        estimate, interval, corrected = _advantage_cells(row)
        name = key.replace("__", " / ").replace("devig_", "de-vig ")
        if key == headline:
            name = f"**{name} — HEADLINE, least favourable to the model**"
        lines.append(
            f"| {name} | {estimate} | {interval} | {corrected} | "
            f"{int(row.get('rows', 0)):,} | {_cluster_cell(row)} | "
            f"{_detectable_cell(row)} | {reading_of(cell, row)} |"
        )
    lines.append("")
    return lines


def _calibration_table(rows: Sequence[Mapping], *, what: str) -> list[str]:
    if not rows:
        return []
    lines = [
        f"**Calibration by decile — {what}.**",
        "",
        "| Predicted band | Wagers | Quotes | Mean predicted | Realised | "
        "Gap (pp) |",
        "|:---|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        # `wagers` is read without a default on purpose. `read_record` refuses
        # a record written before this column existed, so the only way to
        # arrive here without it is a schema drift, and a renderer that filled
        # it with the quote count is the defect this column was added to fix.
        counts = f"{int(row['wagers']):,} | {int(row['rows']):,}"
        if not row.get("enough_wagers"):
            lines.append(
                f"| {row['bin']} | {counts} | — | — | "
                f"below the {MINIMUM_BUCKET}-wager floor, so no frequency |"
            )
            continue
        lines.append(
            f"| {row['bin']} | {counts} | {row['predicted']:.1%} | "
            f"{row['realised']:.1%} | {row['gap_points']:+.1f} |"
        )
    lines.append("")
    return lines


def _tier_section(cell: Mapping) -> list[str]:
    lines = [
        f"### {cell['tier']}",
        "",
        f"{int(cell['rows']):,} scored wager(s) — "
        f"{int(cell.get('scored_rows', 0)):,} rows, one per book quoting one — "
        f"on {int(cell['games']):,} game(s) over {int(cell['days']):,} slate "
        f"day(s), {int(cell['athletes']):,} athlete(s) across "
        f"{int(cell['books']):,} book(s). {int(cell['won']):,} of the rows won.",
        "",
        _coverage_line(cell.get("coverage") or {}),
        "",
    ]
    if not cell.get("advantages"):
        lines += [
            f"**{NOTHING_TO_MEASURE.capitalize()}.** This tier carries no scored "
            "wager, so there is no baseline, no model number and no verdict. It "
            "is said in words rather than shown as an empty table, because an "
            "empty table reads as a null result and a null result is a claim.",
            "",
        ]
        return lines
    lines += _baseline_table(cell)
    lines += _advantage_table(cell)
    lines += [
        f"**{cell['tier']}: {cell['verdict']}.**",
        "",
        CONTROL_IS_NOT_THE_MARKET,
        "",
        f"Mean push mass on the scored rows: model "
        f"{cell['push_mass']['model_mean']:.4f}, control "
        f"{cell['push_mass']['control_mean']:.4f}. That is how much the choice "
        "between the two probability conventions could have been worth, and it "
        "is why both are scored rather than one being chosen.",
        "",
    ]
    for name, what in (
        (f"model__{CONVENTION_CONDITIONAL}", "the model"),
        (f"devig_{DEVIG_PROPORTIONAL}", "the de-vigged fair price (proportional)"),
    ):
        lines += _calibration_table(
            (cell.get("calibration") or {}).get(name) or [], what=what
        )
    far = cell.get("unbenchmarked_cell") or {}
    if int(far.get("rows", 0)):
        lines += [
            f"#### {cell['tier']} — the far ladder, {UNBENCHMARKED}",
            "",
            UNBENCHMARKED_SENTENCE,
            "",
            f"{int(far['rows']):,} scored wager(s) past {BENCHMARKED_RUNGS} rungs. "
            f"Reading: **{far.get('verdict', UNBENCHMARKED)}**.",
            "",
        ]
        lines += _advantage_table(far)
    return lines


def _market_table(record: Mapping) -> list[str]:
    lines = [
        "| Market / tier | Wagers | Headline comparison | Advantage | "
        "Family-corrected | Clusters | Coverage (two-sided of settled) | Verdict |",
        "|:---|---:|:---|---:|:---|---:|---:|:---|",
    ]
    for cell in record.get("by_market_and_tier", []):
        headline = cell.get("headline") or ""
        row = (cell.get("advantages") or {}).get(headline)
        estimate, _interval, corrected = _advantage_cells(row)
        coverage = cell.get("coverage") or {}
        lines.append(
            f"| {cell['label']} | {int(cell['rows']):,} | "
            f"{headline.replace('__', ' / ').replace('devig_', 'de-vig ') or '—'} | "
            f"{estimate} | {corrected} | {_cluster_cell(row)} | "
            f"{_pct(coverage.get('two_sided_share_of_settled'))} | "
            f"{cell['verdict']} |"
        )
    lines.append("")
    return lines


def _hypothesis_section(record: Mapping) -> list[str]:
    """The 33 pre-registered hypotheses, each beside the cell that answers it.

    Printed so nobody has to match a table of cells against a ledger by eye.
    The direction is the one registered before the model existed; the reading
    is the cell's own verdict and is never re-derived here.
    """
    answered = record.get("hypotheses") or []
    if not answered:
        return [
            "## The pre-registered hypotheses",
            "",
            "**Not supplied.** This run was handed no ledger entries, so this "
            "report cannot say which registered question each cell answers. "
            "That is a missing statement and not an empty one: the 33 exist "
            "whether or not this record carries them.",
            "",
        ]
    lines = [
        "## The pre-registered hypotheses, answered",
        "",
        f"{len(answered):,} hypotheses, registered on 2026-09-05 **before the "
        "model that answers them existed**, each with a direction fixed then "
        "and unchangeable now: the ledger is append-only under its own CI job. "
        "Thirty are (market x tier) against the de-vigged two-sided fair "
        "price; three are per tier against the identity-blind role-prior "
        "control, pooled across the ten priceable markets.",
        "",
        "The reading below is the cell's own verdict, not a second judgment of "
        "the same interval. A direction that was predicted and not observed is "
        "the pre-registration working.",
        "",
        "| Search | Hypothesis | Predicted | Wagers | Advantage | "
        "Family-corrected | Reading |",
        "|:---|:---|:---|---:|---:|:---|:---|",
    ]
    for row in answered:
        estimate = (
            f"{row['estimate']:+.4f}"
            if row.get("enough_evidence") and row.get("estimate") is not None
            else "—"
        )
        corrected = (
            f"{row['adjusted_low']:+.4f} to {row['adjusted_high']:+.4f}"
            if row.get("enough_evidence") and row.get("adjusted_low") is not None
            else "—"
        )
        label = f"{row['market']} / {row['tier']}" if row["market"] else row["tier"]
        lines.append(
            f"| {row['search']} | {label} | {row['predicted_direction']} | "
            f"{int(row['rows']):,} | {estimate} | {corrected} | "
            f"{row['reading']} |"
        )
    lines.append("")
    return lines


def _vigged_section(record: Mapping) -> list[str]:
    lines = [
        "## The vigged comparison, which is a diagnostic and never a headline",
        "",
        VIGGED_IS_NEVER_A_HEADLINE,
        "",
        "| Tier | Convention | Advantage over the VIGGED market | "
        "Family-corrected | Reading |",
        "|:---|:---|---:|:---|:---|",
    ]
    for cell in record.get("by_tier", []):
        for convention in CONVENTIONS:
            row = (cell.get("vigged_market_advantage") or {}).get(convention)
            if not row:
                continue
            estimate, _interval, corrected = _advantage_cells(row)
            lines.append(
                f"| {cell['tier']} | {convention} | {estimate} | {corrected} | "
                f"{row.get('verdict', '')} |"
            )
    lines.append("")
    return lines


def _coverage_section(record: Mapping) -> list[str]:
    rows = record.get("coverage_by_rung") or []
    if not rows:
        return []
    lines = [
        "## Two-sided coverage against distance from the money",
        "",
        "The ladder, measured. A rung with no opposite side at the same book "
        "gets no fair price at all, so this table is what the benchmark could "
        "reach rather than what the store offered.",
        "",
        "| Rungs from the money | Settled rows | With a two-sided fair price | "
        "Coverage | Benchmarked |",
        "|---:|---:|---:|---:|:---|",
    ]
    for row in rows:
        lines.append(
            f"| {int(row['rungs'])} | {int(row['rows']):,} | "
            f"{int(row['two_sided']):,} | {_pct(row.get('share'))} | "
            f"{'yes' if row['benchmarked'] else f'no — {UNBENCHMARKED}'} |"
        )
    lines.append("")
    return lines


def render(record: Mapping) -> str:
    """The report. A pure function of the record: no clock, no frame, no ledger.

    The retention probe's rule, and it binds here for the same reason — a report
    that can only be produced by re-running a four-hour measurement is a report
    nobody improves, and a hand-edited generated file survives exactly one
    re-run.
    """
    looks = int(record.get("looks", 1) or 1)
    store = record.get("store") or {}
    # The title comes off the record and is never defaulted to a sport name:
    # `tests/test_competition_registry_is_the_only_place.py` bans a sport
    # literal outside the registry, and a heading that named the wrong sport
    # for a record written by another competition would be worse than a blank.
    title = str(record.get("title") or record.get("competition") or "")
    lines = [
        f"# {title} — the player-prop model, scored".lstrip(" —"),
        "",
        "**Every number below is per tier. There is no pooled "
        "all-of-Division-I row in this report and no function that computes "
        "one: high-major, mid-major and low-major are three distributions and "
        "a pooled headline is banned in this repository.**",
        "",
        f"- Model: `{record.get('model', '')}`",
        f"- Control: `{record.get('control', '')}`",
        f"- Store: `{store.get('path', '')}`"
        + (
            f", {int(store['bytes']):,} bytes, sha256 `{store['sha256']}`"
            if store.get("sha256")
            else ""
        ),
        f"- Season: {record.get('season_label', '')}; snapshot window "
        f"`{record.get('snapshot_phase', '')}`",
        f"- Subject fold for the athlete clustering: `"
        f"{record.get('declared_subject_fold', '')}`",
        f"- Family correction: {looks:,} cumulative hypotheses "
        f"(x{float(record.get('correction_factor', 1.0)):.4f}), read from the "
        "experiment ledger at render time",
        "",
    ]
    provenance = RESTATEMENT.provenance_paragraph(record)
    if provenance:
        lines += [provenance, ""]
    lines += [
        "## What is compared against what",
        "",
        DEVIG_SENTENCE,
        "",
        "The two baselines are printed BEFORE the model in every section "
        "below: the de-vigged two-sided fair price, and the identity-blind "
        "role-prior control — the same engine and the same minutes lattice "
        "with every per-minute rate replaced by the role prior at the "
        "athlete's projected-minutes bucket, which is the credibility weight "
        "set to zero. A model that beats neither has nothing to explain.",
        "",
        "**An interval that includes zero is "
        f"*{S.NO_DEMONSTRATED_EDGE}*, in exactly those words. One that "
        f"excludes zero on the losing side is a *{S.DEMONSTRATED_DEFICIT}*, "
        "which is a finding and not a null result.** Advantage is "
        "`(baseline mean log loss) − (model mean log loss)`, so positive is "
        "the model doing better, which is the direction the thirty registered "
        "hypotheses predict.",
        "",
        f"Intervals cluster **three** ways — by game, by day and by athlete — "
        "and the widest wins. The athlete is not optional: one subject "
        "supplies a whole ladder across ten markets, and neither the game nor "
        "the day absorbs that.",
        "",
        f"Below {MINIMUM_ROWS:,} wagers, or below {MINIMUM_CLUSTERS:,} "
        "clusters, a cell carries the words *not enough evidence* and no "
        "number at all.",
        "",
        f"`{'`, `'.join(record.get('markets_refused_by_name') or [])}` are "
        "**refused by name**. They are not scored anywhere below, are never "
        "given a verdict, and are not a pass, an avoid or a no-value call.",
        "",
    ]
    lines += [
        "## What one scored row is, and what it is not",
        "",
        "A scored row is **one side of one wager at one book**. That is the "
        "unit design section 10's de-vig joins on — the same event, market, "
        "athlete, line AND book — and it is why the row counts below are "
        "larger than the wager counts beside them.",
        "",
        "Two consequences are stated rather than left to be found:",
        "",
        "1. **Both sides of a pair are scored.** The store's own census counts "
        "an over and an under as two wagers, and both are here. Their errors "
        "are exactly opposite by construction, which is why the calibration "
        "tables below are close to symmetric about 50% — that symmetry is a "
        "property of the population and not a finding about the model. The "
        "clustering absorbs the dependence: two sides of one pair share a "
        "game, a day and an athlete, so they are never two independent "
        "observations in any of the three arms.",
        "2. **The declared floor is a floor on WAGERS, not on rows.** A wager "
        f"quoted at five books is five rows and one bet, and the {MINIMUM_ROWS:,}"
        " declared in advance is a number of bets. Every cell below is "
        "qualified by its wager count.",
        "",
    ]
    lines += _census_section(record)
    lines += ["## Per tier", ""]
    for cell in record.get("by_tier", []):
        lines += _tier_section(cell)
    lines += ["## Per market and tier", "", ]
    lines += _market_table(record)
    lines += _hypothesis_section(record)
    lines += _coverage_section(record)
    lines += _vigged_section(record)
    lines += [
        "## What this is not",
        "",
        "- It is not a recommendation and not a selection. No market in this "
        "lab is allowlisted and no player prop can reach "
        "`Availability.CONFIRMED`, so nothing here can become a bet.",
        "- It is not a return. Nothing above is a stake, a profit or an ROI; "
        "every number is a log loss, a Brier score or a difference between "
        "two of them.",
        "- It is not a claim about a market whose cell says *not enough "
        "evidence*, and a cell that says so is not a pass, an avoid or a "
        "no-value call.",
        "",
    ]
    return "\n".join(lines) + "\n"


def _census_section(record: Mapping) -> list[str]:
    devig_census = record.get("devig_census") or {}
    population = record.get("population_census") or {}
    overround = record.get("overround") or {}
    clips = record.get("probability_clips") or {}
    lines = [
        "## What was scored, and what was not",
        "",
        "Both censuses reconcile, and `build_record` refuses to write a record "
        "when either does not: a measurement that silently loses rows still "
        "prints an interval, and the interval looks fine.",
        "",
        "| Step | Rows |",
        "|:---|---:|",
        f"| supplied to the de-vig | {int(devig_census.get('supplied', 0)):,} |",
        f"| de-vigged (two-sided, same book) | "
        f"{int(devig_census.get('devigged', 0)):,} |",
        f"| no complement at the same book | "
        f"{int(devig_census.get('no_complement', 0)):,} |",
        f"| not two-sided | {int(devig_census.get('not_two_sided', 0)):,} |",
        f"| overround not above one | "
        f"{int(devig_census.get('overround_not_above_one', 0)):,} |",
        f"| power exponent unsolved | "
        f"{int(devig_census.get('power_unsolved', 0)):,} |",
        f"| unreadable price | {int(devig_census.get('unreadable_price', 0)):,} |",
        f"| unknown selection | {int(devig_census.get('unknown_selection', 0)):,} |",
        "",
        "| Step | Rows |",
        "|:---|---:|",
        f"| de-vigged | {int(population.get('devigged', 0)):,} |",
        f"| **scored** | {int(population.get('scored', 0)):,} |",
        f"| push (never half a win) | {int(population.get('push', 0)):,} |",
        f"| void (a returned stake) | {int(population.get('void', 0)):,} |",
        f"| unsettleable (never a loss) | "
        f"{int(population.get('unsettleable', 0)):,} |",
        f"| no model probability | "
        f"{int(population.get('no_model_probability', 0)):,} |",
        f"| no control probability | "
        f"{int(population.get('no_control_probability', 0)):,} |",
        f"| no tier | {int(population.get('no_tier', 0)):,} |",
        f"| past {BENCHMARKED_RUNGS} rungs — {UNBENCHMARKED}, reported apart | "
        f"{int(population.get('unbenchmarked', 0)):,} |",
        "",
    ]
    if overround.get("pairs"):
        lines += [
            f"The hold this de-vig removed: **{overround['pairs']:,} pair(s)**, "
            f"median overround {overround['median']:.4f}, mean "
            f"{overround['mean']:.4f}, range {overround['minimum']:.4f} to "
            f"{overround['maximum']:.4f}"
            + (
                f"; median power exponent {overround['median_exponent']:.4f}."
                if overround.get("median_exponent") is not None
                else "."
            ),
            "",
        ]
    lines += [
        f"Probabilities are clipped into "
        f"[{PROBABILITY_FLOOR:g}, {1 - PROBABILITY_FLOOR:g}] before any log is "
        "taken, because a probability of exactly zero or one has an infinite "
        "log loss. Every clip is a number this report changed, so every clip "
        "is counted: "
        + (
            ", ".join(f"`{name}` {count:,} row(s)" for name, count in clips.items())
            if clips
            else "**no row was clipped**"
        )
        + ".",
        "",
    ]
    return lines


# --------------------------------------------------------------------------
# Paths, IO and the restatement
# --------------------------------------------------------------------------


def record_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPORT_STEM, ".json")


def report_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPORT_STEM, ".md")


def write_record(record: Mapping, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=False) + "\n", encoding="utf-8")
    return path


def read_record(path: Path) -> dict:
    record = json.loads(Path(path).read_text(encoding="utf-8"))
    version = int(record.get("record_version", 0))
    if version != RECORD_VERSION:
        raise PropGradingError(
            f"{path} is a version {version} record and this module writes "
            f"version {RECORD_VERSION}. Re-run the measurement rather than "
            "rendering a report with holes in it."
        )
    return record


def rebuild_cell(cell: Mapping, *, looks: int) -> dict:
    """One stored interval restated, with THIS module's second floor kept.

    `restatement.rebuild_cell` re-derives `enough_evidence` and `verdict` from
    the stored estimate and the stored `rows`, which is the declared 200-wager
    floor and nothing else. This module declares a second floor — 30 clusters,
    because a cluster-robust ratio estimator is downward biased with few of
    them — and a cell refused by it carries `below_the_cluster_floor`.

    Without this, a re-render turned every such cell from *not enough evidence*
    into a verdict about an interval the run itself had refused to state.
    Measured on the first record this module wrote: a 682-wager, 7-cluster
    high-major cell re-rendered as *no demonstrated edge*. That is a
    restatement inventing a reading, which is the one thing a restatement may
    never do.
    """
    out = RESTATEMENT.rebuild_cell(cell, looks=looks)
    if cell.get("below_the_cluster_floor"):
        out["enough_evidence"] = False
        out["survives_correction"] = False
        out["verdict"] = str(cell.get("verdict", ""))
    return out


def restated(record: Mapping, *, looks: int, record_name: str = "") -> dict:
    """The record restated at `looks`, with every derived word re-derived.

    `restatement.restated` moves every stored interval; the cell-level headline
    and verdict are derived from several intervals at once, so they are
    recomputed here afterwards. A restatement may only ever widen — see
    `restatement.widened` — so it can retract a claim and can never make one.
    """
    moved = RESTATEMENT.restated(
        record, looks=looks, record_name=record_name, rebuild=rebuild_cell
    )
    for cell in moved.get("by_tier", []):
        _rejudge(cell)
        far = cell.get("unbenchmarked_cell")
        if far:
            _rejudge(far)
    for cell in moved.get("by_market_and_tier", []):
        _rejudge(cell)
    if moved.get("hypotheses"):
        # The answered table is derived from the cells, so it moves with them.
        # Leaving it alone would print a stale reading beside a fresh interval
        # on one page, which is decision 46's defect in a new table.
        moved["hypotheses"] = answered_hypotheses(
            moved["hypotheses"],
            by_tier=moved.get("by_tier", []),
            by_market_and_tier=moved.get("by_market_and_tier", []),
        )
    return moved


def _rejudge(cell: dict) -> None:
    if not cell.get("advantages"):
        return
    cell["headline"] = _least_favourable(cell["advantages"], HEADLINE_KEYS)
    cell["control_headline"] = _least_favourable(cell["advantages"], CONTROL_KEYS)
    cell["verdict"] = verdict_of(cell)


def record_file_name(record: Mapping) -> str:
    """The record file a restated report points a reader back at."""
    key = str(record.get("competition", CBB.key)) or CBB.key
    return f"{key}_{REPORT_STEM}.json"


def write_report(record: Mapping, path: Path, *, looks: int | None = None) -> Path:
    """Render at the ledger's current count, never at the record's own.

    `looks=None` means the caller has already restated; anything else restates
    here first. Either way the record on disk keeps what it was measured at.
    """
    payload = record if looks is None else restated(
        record, looks=looks, record_name=record_file_name(record)
    )
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(payload), encoding="utf-8")
    return path
