"""The fastest honest read on whether the model knows anything the price does not.

`price_backtest.py` says whether a policy would have **made money**. This module
says whether there is anything there to make money *from*, and it answers in one
number: the coefficient on the model's disagreement with the de-vigged price.

Cooper, in the brief, item 3 of measurement discipline:

    *"Regress outcome on market-implied vs model-implied probability, every
    week, and print it. The NHL lab's coefficients were market 0.97, model 0.03
    [-0.037, +0.102] — the model added nothing and its claimed edge was
    anti-predictive, bigger claimed edge being worse. This single test is the
    fastest honest read on whether anything here is real."*

It is the fastest read because it does not wait for a return to separate itself
from noise. A return is a bet-weighted, payout-weighted, heavy-tailed function
of the thing we actually want to know, which is whether the model's opinion
carries information. This regression asks that question directly, on every
graded wager rather than on the small adversely-selected slice a threshold lets
through, and it answers it in units anybody can read: **how much of a claimed
edge is realised?**

## The specification, and why it is parameterised this way

Over every graded wager, with the outcome as 1 for a win and 0 for a loss:

    outcome = a + b_market x market_implied + b_disagreement x (model_implied - market_implied)

The equivalent unparameterised regression is
``outcome ~ market_implied + model_implied``, and the two are the same fit: with
``d = model - market``,

    a + c_m x market + c_p x model  ==  a + (c_m + c_p) x market + c_p x d

so **the coefficient on the disagreement here is numerically identical to the
coefficient on model-implied there**. That identity is why the NHL lab's *model
0.03 [-0.037, +0.102]* is directly comparable to the disagreement figure this
module prints, and it is the reason for the reparameterisation: it puts the one
number that answers the question in its own column instead of leaving a reader
to subtract two correlated coefficients in their head.

How to read it:

* **b_disagreement = 1** — every point of claimed edge is realised. The model
  knows exactly what the price does not.
* **b_disagreement = 0** — none of it is realised. The model knows **nothing the
  price does not**, whatever its calibration plot looks like and whatever its
  backtest return happens to be at this sample size.
* **b_disagreement < 0** — **anti-predictive**. The bigger the claimed edge, the
  worse the bet. This is the NHL lab's finding and it is the single most
  important shape this module exists to make visible, because it inverts the
  natural response to a disappointing backtest. See "the threshold cannot help"
  below.

`b_market` is reported too, and it is a *diagnostic on the de-vig*, not a
headline. Its null is **1.0**, not zero. A de-vigged price that is calibrated
gives b_market near 1 with an intercept near 0; b_market far from 1 says the
de-vig or the population is doing something the reader has to understand before
the disagreement coefficient means anything.

**It is deliberately impossible to attach the words "demonstrated edge" to
b_market.** :meth:`Coefficient.verdict` raises when the coefficient's null is
not zero, because `stats.RoiInterval.verdict` reads a *sign* — and a market
coefficient of 0.97 excludes zero on the positive side, so a verdict predicate
that never asked what the null was would announce a demonstrated edge on a
number describing the **market**. That is precisely the class of defect
`tests/test_the_headline_reads_the_sign.py` exists for, arriving through a door
that test does not watch.

## Clustered by game, and by day, and the wider one wins

One game supplies a moneyline, a spread, a total, two team totals and a dozen
props, and they are one evening seen fifteen ways. An ordinary regression
standard error over them assumes they are independent observations, and in this
sport that is wrong by roughly the square root of the cluster size rather than
by a rounding.

So the covariance is the cluster-robust sandwich

    V = (X'X)^-1 [ sum over clusters of (X_g' u_g)(X_g' u_g)' ] (X'X)^-1 x c

with the usual finite-cluster correction ``c = G/(G-1) x (N-1)/(N-K)``, computed
**twice** — clustering by game and clustering by day — and the wider standard
error is the one reported, per coefficient. That is `stats.interval_two_way`'s
doctrine applied to a regression: dependence runs within a game, but a model
with a shared daily component (a pace prior refit nightly, a calibration map
fitted to yesterday) makes a whole slate correlated, and choosing the narrower
unit after seeing both is the move this repository is arranged to prevent.

**Both sides of a wager are in this population, and they are one observation
seen twice.** A home ticket and its away complement win and lose together by
construction, and their regressors are mirror images. That is not a defect —
both sides were genuinely offered and both genuinely settled — and the interval
is unaffected, because the two rows sit in the same game cluster and the
sandwich is built from per-cluster sums. But it does mean **the row count is not
a count of independent observations**, which is why the interval rather than the
`n` is the thing to read here, and why the cluster count is printed beside every
coefficient.

**This is not a second copy of `stats.interval_by_cluster`.** That function is a
ratio estimator for a mean return and this is a sandwich for a regression
coefficient; they are different estimators of different quantities and neither
can be written in terms of the other. Everything that *can* be shared is:
:data:`stats.Z95`, the Bonferroni z, the cumulative-looks correction, the
"not enough evidence" floor, and the one function in this repository that turns
a sign into a word. The one place a mean *is* what is wanted — the Brier
advantage below — goes through `stats.interval_two_way` rather than through
anything written here.

## Brier, side by side, with the vig left in on purpose

:func:`brier` scores the model and the market on the same rows, and prints three
market numbers rather than one:

* **de-vigged** — the fair price, and the honest comparison;
* **raw** — the price with the hold still in it. Two sides of a two-way market
  quoted at -110 imply 52.4% each and sum to 104.8%: the raw implied probability
  is an **over-estimate of every side by construction**, so scoring it against
  outcomes handicaps it. It is printed for one reason: **if the model loses to
  the handicapped market, that is decisive.** There is no argument left about
  de-vig methodology to have.
* **the base rate** — the climatology reference, so a reader can see how much of
  either score is just the population's win rate.

The paired difference goes through `stats.interval_two_way`, and its **sign is
chosen so that the shared verdict function reads it correctly**: the quantity
clustered is ``brier_market - brier_model``, so positive means the model is more
accurate. A Brier score is better when it is *lower*, and handing a
lower-is-better quantity to a predicate that says "edge" when the number is
positive would announce a demonstrated edge on a model that is measurably worse
than the price. That is the same defect as the market-coefficient one above, and
it is closed the same way: by making the arithmetic agree with the words rather
than by remembering which way round it goes.

## Anti-predictiveness as a table, not only as a coefficient

A coefficient is one number and a reader can wave it away as noise. The bucket
table cannot be waved away: it shows, per bucket of **claimed** edge, what the
model said would happen and what did. If the largest claimed edges have the
largest shortfall, the reader sees a monotone column rather than a minus sign.

The buckets are declared here, fixed, and they **include the negative ones**.
Cutting at the bet threshold and showing only what a card would have staked
hides exactly the comparison that makes the shape legible: the wagers the model
disliked are the control group.

## Why raising the edge threshold cannot help, algebraically

`price_backtest.bets_from` promises this module shows it, so here it is.

A card takes a wager when the claimed edge clears a threshold, and the claimed
edge is monotone in the disagreement ``d`` at a fixed price. Under the fit, a
wager with disagreement ``d`` realises

    outcome = a + b_market x market + b_disagreement x d

so the **realised excess over the de-vigged price** is

    (a + (b_market - 1) x market) + b_disagreement x d

whose derivative in ``d`` is exactly ``b_disagreement``. Raising the threshold
is a monotone filter that admits only larger ``d``. So:

* ``b_disagreement > 0`` — a higher threshold selects better bets, and how much
  better is that coefficient.
* ``b_disagreement = 0`` — a higher threshold selects **the same** bets on
  average, at a smaller sample, with a wider interval. It buys nothing and costs
  power.
* ``b_disagreement < 0`` — a higher threshold selects **worse** bets. The
  natural response to a disappointing backtest is the one that makes it worse,
  and nothing in a return figure says so.

The algebra states it; the bucket table measures it. They are printed together
because either alone is arguable.

## De-vig: multiplicative, stated, and refused rather than guessed

Every market-implied probability is de-vigged before it is used, by
**multiplicative normalisation**: the raw implied probabilities of the two sides
of a wager are divided by their sum. Declared in :data:`DEVIG_METHOD` and stated
in the rendered report every time.

Multiplicative because it needs no solver, no free parameter and no assumption
this lab has not measured. Shin's method and the power method both fit a
parameter for insider trading or for favourite-longshot curvature, and fitting
one on this population would be a hypothesis that belongs in the experiment
ledger rather than a preprocessing step nobody counts. Its known bias is
favourite-longshot: against Shin it shades the fair probability of a heavy
favourite up and a longshot down. That bias enters through the *level* of
``market_implied``, which is what ``b_market`` is there to expose — and
:func:`build_record` fits the whole regression a second time on the **raw**
probabilities so the reader can see how much the de-vig choice moved anything.

A pair is de-vigged only when it is genuinely a pair:

* exactly two rows, one on each side of the same wager, at the scope declared
  (the same book by default — see :data:`PAIR_SCOPES`);
* both prices readable;
* **an overround strictly above 1.0**. A "de-vig" that divides by a number below
  one *inflates* both sides above their raw implied probabilities, which is not
  a fair price — it is a cross-book artefact or an arbitrage wearing a fair
  price's clothes. Refused and counted.

Anything else is **excluded and counted**, never imputed. The exclusion census
reconciles: ``supplied = scored + excluded``, and :func:`build_record` refuses to
produce a record when it does not, because a measurement that silently loses a
third of its rows still prints an interval.

There is no second reader of American odds here. :func:`implied_probability` is
one line over `stores._decimal_payout`, which is the only function in this
repository that knows +150 beats -110 beats -200 — the same reason
`price_backtest` imports it rather than converting odds itself.

## Nothing to measure is said in words

No historical price has been bought for this sport and no forward opinion has
been settled. Every function here returns an empty result honestly and
:func:`render` prints *"there is nothing to measure"* rather than an empty
table, because an empty table reads as a null result and a null result is a
claim.

## Re-renderable from the record

`render` is a pure function of the run record: no clock, no network, no frame.
The retention probe's rule, and it binds here for the same reason — a report
that can only be produced by re-running the measurement is a report nobody
improves, and a hand-edited generated file survives exactly one re-run.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import CBB, Competition

# Imported rather than restated, and re-exported so the script has one door.
# `POOLED_CAVEAT`, `TIER_ORDER` and `NOTHING_TO_MEASURE` are wordings and
# orderings this package has already committed to, and two copies of a caveat
# drift — the direction they drift in is never the conservative one.
# `add_edge`, `ledger_path` and `looks_from_ledger` are arithmetic and paths: a
# second copy of any of them would be free to disagree with the backtest about
# what "edge" means, about where the ledger lives, and about how many looks the
# family holds. `looks_from_ledger` in particular is the hard rule — the
# family-wise correction is ALWAYS the ledger's cumulative count — and it is
# imported so there is exactly one implementation of it in the repository.
from cbb_betting_lab.reports.price_backtest import (
    BET_EDGE_THRESHOLD,
    NOTHING_TO_MEASURE,
    POOLED_CAVEAT,
    TIER_ORDER,
    add_edge,
    ledger_path,
    looks_from_ledger,
)
from cbb_betting_lab.selection import (
    AWAY,
    AWAY_OVER,
    AWAY_UNDER,
    HOME,
    HOME_OVER,
    HOME_UNDER,
    OVER,
    UNDER,
)
from cbb_betting_lab.stores import _decimal_payout as decimal_payout


#: Bumped whenever the record's shape changes, so a stale record fails loudly at
#: re-render rather than rendering a report with holes in it.
RECORD_VERSION = 1

#: The output stem. Competition-prefixed by `Competition.output_name`, so this
#: lab's record could never be overwritten by another's.
REPORT_STEM = "forecast_skill"

#: What a graded wager must carry. A **missing column raises** — the football
#: lab's backtest read a missing settlement column as a zero through
#: `getattr(..., None)`, reported zero bets, and had that read as "the model
#: never disagrees enough with the market" when its price columns had never been
#: built. Nothing here is defaulted.
SKILL_COLUMNS: tuple[str, ...] = (
    "event_id",
    "slate_date",
    "market",
    "segment",
    "selection",
    "line",
    "american_odds",
    "tier",
    "model_probability",
    "outcome",
)

#: Optional, and each one turns something on rather than being faked when
#: absent. `book` narrows the de-vig scope to a single book's own two-sided
#: quote; `profit_units` adds the realised return to the bucket table;
#: `player` separates two athletes' props on one event; `edge` is used as
#: supplied rather than recomputed, so this report and the card cannot disagree
#: about what the card claimed.
OPTIONAL_SKILL_COLUMNS: tuple[str, ...] = ("book", "player", "edge", "profit_units")

#: The de-vig. One method, declared, and stated in the report every time.
DEVIG_METHOD = "multiplicative"

#: How the de-vig is scoped. `book` pairs a quote only with the **same book's**
#: quote on the other side, which is the only pair that has a hold in it at all.
#: `wager` pairs across books, which understates the hold — two books' best
#: prices can sum below 1.0 — and exists for a store that has already been
#: collapsed to one row per wager at the best price. The scope used is recorded
#: and printed, because the two measure different things.
PAIR_SCOPES: tuple[str, ...] = ("book", "wager")

#: Which selection completes a two-sided wager. Read off `selection.py`'s
#: declared vocabulary rather than inferred from the string, because inferring
#: it is how `home_over` ends up paired with `away_under`: both contain an
#: underscore, both name a total, and the resulting "de-vig" would normalise two
#: different teams' totals against each other and look entirely plausible.
COMPLEMENT: dict[str, str] = {
    HOME: AWAY,
    AWAY: HOME,
    OVER: UNDER,
    UNDER: OVER,
    HOME_OVER: HOME_UNDER,
    HOME_UNDER: HOME_OVER,
    AWAY_OVER: AWAY_UNDER,
    AWAY_UNDER: AWAY_OVER,
}

#: The two selections whose lines are equal and opposite. A home side at -3.5
#: and an away side at +3.5 are the two halves of one wager, and a pair key that
#: used the line as filed would put them in different groups and de-vig neither
#: — while a ladder that quotes home at both -3.5 and +3.5 would put four rows
#: in one group if the key used only the absolute value.
HANDICAP_SIDES: frozenset[str] = frozenset({HOME, AWAY})

#: Below this the overround is not a hold. See the module docstring: dividing by
#: a number at or below one inflates both sides above their raw implied
#: probabilities, and a market-implied probability larger than the price implies
#: is not a fair price.
MINIMUM_OVERROUND = 1.0

#: Buckets of **claimed** edge, declared in advance and fixed rather than
#: computed as quantiles of the sample. Quantiles move with the data, so the
#: same model measured twice produces two incomparable tables. The negative
#: buckets are here on purpose: the wagers the model disliked are the control
#: group, and a table cut at the bet threshold hides the comparison that makes
#: anti-predictiveness legible.
EDGE_BUCKETS: tuple[tuple[float, float], ...] = (
    (float("-inf"), -0.10),
    (-0.10, -0.05),
    (-0.05, 0.0),
    (0.0, 0.02),
    (0.02, 0.05),
    (0.05, 0.10),
    (0.10, 0.20),
    (0.20, float("inf")),
)

#: Below this many rows a bucket prints its count and no frequency. The point
#: estimate of nine observations invites a reader to follow the shape of the
#: line rather than the intervals around it — `calibration_on_selected` declares
#: the same floor for the same reason, and the two are deliberately equal.
MINIMUM_BUCKET = 30

#: Below this many graded rows there is no coefficient, only the words *not
#: enough evidence*. `stats.MINIMUM_BETS`, restated as the row floor so a reader
#: of this module sees which floor binds.
MINIMUM_ROWS = S.MINIMUM_BETS

#: Below this many clusters there is no coefficient either, whatever the row
#: count. A cluster-robust sandwich is **downward biased with few clusters** —
#: the meat is a sum of G outer products and estimates its own target badly when
#: G is small — so a thousand bets over nine games would print a narrow interval
#: that is an artefact of the estimator rather than a fact about the model. The
#: repository's standing anxiety is intervals that are too narrow, and this is
#: the way this particular estimator produces one.
MINIMUM_CLUSTERS = 30

#: What the disagreement coefficient is, in one sentence, printed every time.
THE_WHOLE_ANSWER = (
    "**The coefficient on the disagreement is the whole answer.** If it is "
    "indistinguishable from zero, the model knows nothing the price does not — "
    "whatever its calibration plot looks like and whatever its backtest return "
    "happens to be at this sample size."
)

#: The prior, named, because a null here is the expected result rather than a
#: surprise. Two finished sibling labs, two routes, one answer.
NHL_PRIOR = (
    "The honest prior is the NHL lab, which ran this same regression and got "
    "**market 0.97, model 0.03 [-0.037, +0.102]** — the model added nothing, "
    "and its claimed edge was *anti-predictive*, bigger claimed edge being "
    "worse. Because the reparameterisation is an algebraic identity, that 0.03 "
    "is directly comparable to the disagreement coefficient below."
)

#: The vig sentence, in full, wherever a Brier table appears.
VIG_HANDICAP = (
    "**The raw market column still has the vig in it.** Two sides of a two-way "
    "market at -110 imply 52.4% each and sum to 104.8%, so the raw implied "
    "probability over-estimates every side by construction and is being scored "
    "with a handicap. It is printed for exactly one reason: **if the model "
    "loses to the handicapped market, that is decisive** — there is no argument "
    "about de-vig methodology left to have."
)

#: What the de-vig did, in words, every time a market-implied number is printed.
DEVIG_SENTENCE = (
    "Market-implied probabilities are de-vigged by **multiplicative "
    "normalisation**: the two sides' raw implied probabilities are divided by "
    "their sum. Chosen because it needs no solver, no free parameter and no "
    "assumption this lab has not measured; Shin's method and the power method "
    "each fit a parameter, and fitting one here would be a hypothesis that "
    "belongs in the experiment ledger rather than a preprocessing step nobody "
    "counts. Its known bias is favourite-longshot, and it enters through the "
    "*level* of the market-implied probability — which is what the market "
    "coefficient is there to expose. The same fit on the **raw** probabilities "
    "is reported beside it so the reader can see how much the choice moved."
)


class ForecastSkillError(RuntimeError):
    """The regression could not be run honestly, so it was not run."""


class NotIdentified(ForecastSkillError):
    """A coefficient has no value to estimate, so none is reported.

    Raised — and caught into a stated refusal — when the design matrix is rank
    deficient. The commonest cause is a model whose probability never differs
    from the de-vigged price, which makes the disagreement column constant: its
    coefficient is then not "zero", it is *undefined*, and the difference
    matters because zero is a finding about the model and undefined is a fact
    about the wiring.
    """


# --------------------------------------------------------------------------
# Frame hygiene
# --------------------------------------------------------------------------


def require_columns(frame: pd.DataFrame, columns: Sequence[str], what: str) -> None:
    """Raise on a missing column. Never default it, never `getattr(..., None)`.

    The same guard `price_backtest.require_columns` makes, restated here rather
    than imported so that this module's error message names *this* module's
    contract. A missing column read as a zero is how the football lab's backtest
    reported zero bets and had that read as a finding about the model.
    """
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise ForecastSkillError(
            f"{what} is missing {missing}. Nothing is defaulted: a missing "
            "column read as a zero is how a wiring fault becomes a finding, and "
            "this regression would happily fit one and print an interval."
        )


def implied_probability(american: object) -> float:
    """The probability a price implies, before the vig is taken out of it.

    One line over `stores._decimal_payout`, which is the only function in this
    repository that reads American odds — +150 beats -110 beats -200, and a
    naive numeric sort puts -200 on top. A second odds reader here would be free
    to disagree with the store, the card and the backtest about what a price
    means, and it would disagree quietly.

    `nan` for a price that cannot be read, never `0.0`. An unreadable price is
    not a certainty that the bet loses.
    """
    payout = decimal_payout(american)
    if payout == float("-inf") or payout <= -1.0:
        return float("nan")
    return 1.0 / (1.0 + payout)


def _text(value: object) -> str:
    """One spelling for a cell that has been through a CSV round-trip.

    A CSV round-trip turns an empty player into NaN, which is truthy, so
    `str(x or "")` yields the literal string `"nan"` — the fifth member of the
    NHL lab's join-key bug family, and the one that matched nothing forever.
    """
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    text = str(value).strip()
    return "" if text.lower() in {"nan", "none", "<na>"} else text


def _line(value: object) -> float | None:
    text = _text(value)
    if not text:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def pair_key(record: Mapping) -> tuple | None:
    """What makes two rows the two sides of one wager, or `None`.

    The handicap markets are the trap and they are handled explicitly. A home
    side at -3.5 and an away side at +3.5 are one wager; keyed on the line as
    filed they land in different groups and neither is ever de-vigged, and keyed
    on the line's absolute value a ladder that quotes home at both -3.5 and +3.5
    puts **four** rows in one group. So the handicap key is the line in the
    home's frame of reference: negated for the away row, and both sides then
    agree.

    A missing line becomes 0.0 for a handicap market, which is what pairs the
    two sides of a moneyline — a market that has no line at all rather than a
    line of zero.

    Over/under markets key on the line as filed, plus the team the total belongs
    to, so `home_over` cannot pair with `away_under` on a night when the two
    teams happen to be hung at the same number.
    """
    selection = _text(record.get("selection"))
    if selection not in COMPLEMENT:
        return None
    line = _line(record.get("line"))
    if selection in HANDICAP_SIDES:
        oriented = 0.0 if line is None else float(line)
        if selection == AWAY:
            oriented = -oriented
        side = ""
    else:
        if line is None:
            # An over/under with no line is not a wager anyone could grade, and
            # defaulting it to zero would pair two different numbers.
            return None
        oriented = float(line)
        side = selection.split("_", 1)[0] if "_" in selection else ""
    return (
        _text(record.get("event_id")),
        _text(record.get("market")),
        _text(record.get("segment")),
        _text(record.get("player")).casefold(),
        "handicap" if selection in HANDICAP_SIDES else "total",
        side,
        round(float(oriented), 6),
    )


# --------------------------------------------------------------------------
# The de-vig
# --------------------------------------------------------------------------


@dataclass
class DevigCensus:
    """Why a supplied row carries no de-vigged market-implied probability.

    Counted and printed rather than dropped. `supplied = scored + excluded`
    reconciles, and :func:`build_record` refuses to produce a record when it
    does not — a measurement that silently loses a third of its rows still
    prints an interval, and the interval looks fine.
    """

    supplied: int = 0
    devigged: int = 0
    unknown_selection: int = 0
    unreadable_price: int = 0
    no_complement: int = 0
    not_two_sided: int = 0
    overround_not_above_one: int = 0
    scope: str = PAIR_SCOPES[0]

    @property
    def excluded(self) -> int:
        return (
            self.unknown_selection
            + self.unreadable_price
            + self.no_complement
            + self.not_two_sided
            + self.overround_not_above_one
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
        }


def devig(
    frame: pd.DataFrame, *, scope: str = PAIR_SCOPES[0]
) -> tuple[pd.DataFrame, DevigCensus]:
    """Add `market_implied`, `market_implied_raw` and `overround`.

    Multiplicative normalisation within a two-sided pair — see
    :data:`DEVIG_SENTENCE`, which is the sentence the report prints. A row whose
    pair cannot be formed keeps a **missing** market-implied probability rather
    than a guessed one, and the reason is counted: a missing price stays missing
    is this lab's first hard rule, and a de-vig is a price.

    `scope="book"` pairs a quote only with the same book's quote on the other
    side. That is the only pair that actually contains a hold. `scope="wager"`
    pairs across books and is for a store already collapsed to one row per wager
    at the best price; it understates the hold, sometimes to nothing, which is
    why the overround guard below is not optional in either scope.
    """
    if scope not in PAIR_SCOPES:
        raise ForecastSkillError(
            f"Unknown de-vig scope {scope!r}; it must be one of "
            f"{list(PAIR_SCOPES)}. The two measure different things — a "
            "cross-book pair understates the hold — so this is refused rather "
            "than defaulted."
        )
    if scope == "book" and not frame.empty and "book" not in frame.columns:
        raise ForecastSkillError(
            "The de-vig scope is 'book' and the frame carries no `book` "
            "column. Every row would land in one nameless book and the pairs "
            "would silently become cross-book pairs, which understate the hold "
            "— sometimes to nothing. Pass scope='wager' deliberately if that is "
            "what is wanted; it is recorded and printed, because the two "
            "measure different things."
        )
    census = DevigCensus(supplied=int(len(frame)), scope=scope)
    if frame.empty:
        return (
            frame.assign(
                market_implied=pd.Series(dtype="float64"),
                market_implied_raw=pd.Series(dtype="float64"),
                overround=pd.Series(dtype="float64"),
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
        if scope == "book":
            key = key + (_text(record.get("book")),)
        keys.append(key)

    groups: dict[tuple, list[int]] = {}
    for position, key in enumerate(keys):
        if key is not None:
            groups.setdefault(key, []).append(position)

    fair: list[float] = [float("nan")] * len(records)
    overrounds: list[float] = [float("nan")] * len(records)
    for key, positions in groups.items():
        sides = {_text(records[p].get("selection")) for p in positions}
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
        for position in positions:
            fair[position] = raw[position] / total
            overrounds[position] = total
        census.devigged += 2

    return (
        frame.assign(
            market_implied=pd.Series(fair, index=frame.index, dtype="float64"),
            market_implied_raw=pd.Series(raw, index=frame.index, dtype="float64"),
            overround=pd.Series(overrounds, index=frame.index, dtype="float64"),
        ),
        census,
    )


def overround_summary(frame: pd.DataFrame) -> dict:
    """The hold this de-vig actually removed, measured, with its `n`.

    Printed because the de-vig is otherwise invisible. A population whose median
    overround is 1.02 and one whose median is 1.09 are different instruments,
    and the second is where the market coefficient has the most room to drift.
    """
    if frame.empty or "overround" not in frame.columns:
        return {"pairs": 0, "median": None, "mean": None, "minimum": None, "maximum": None}
    values = pd.to_numeric(frame["overround"], errors="coerce").dropna()
    if values.empty:
        return {"pairs": 0, "median": None, "mean": None, "minimum": None, "maximum": None}
    # Two rows share one pair's overround, so the pair count is half the rows.
    return {
        "pairs": int(len(values) // 2),
        "rows": int(len(values)),
        "median": float(values.median()),
        "mean": float(values.mean()),
        "minimum": float(values.min()),
        "maximum": float(values.max()),
    }


# --------------------------------------------------------------------------
# The scorable population
# --------------------------------------------------------------------------


#: The two outcomes a probability can be scored against. A push is **not half a
#: win**: folding it in as 0.5 measures a different quantity from the one the
#: figure names, and the difference grows with exactly the markets where
#: whole-number lines are common. Excluded and counted.
SCORABLE_OUTCOMES: frozenset[str] = frozenset({"won", "lost"})


@dataclass
class PopulationCensus:
    """Why a de-vigged row is still not in the regression's denominator."""

    devigged: int = 0
    scored: int = 0
    no_model_probability: int = 0
    push: int = 0
    void: int = 0
    unsettleable: int = 0
    other_outcome: int = 0

    @property
    def excluded(self) -> int:
        return (
            self.no_model_probability
            + self.push
            + self.void
            + self.unsettleable
            + self.other_outcome
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
            "push": self.push,
            "void": self.void,
            "unsettleable": self.unsettleable,
            "other_outcome": self.other_outcome,
        }


def scorable(frame: pd.DataFrame) -> tuple[pd.DataFrame, PopulationCensus]:
    """The rows the regression and the Brier scores run over, and why the rest are not.

    A row needs a de-vigged market-implied probability, a model probability, and
    a won-or-lost outcome. Everything else is excluded **and counted** — see
    :class:`PopulationCensus`, and the push rule in its docstring.
    """
    census = PopulationCensus()
    if frame.empty or "market_implied" not in frame.columns:
        return frame.iloc[0:0], census
    devigged = frame[pd.to_numeric(frame["market_implied"], errors="coerce").notna()]
    census.devigged = int(len(devigged))
    if devigged.empty:
        return devigged, census

    probability = pd.to_numeric(devigged["model_probability"], errors="coerce")
    outcome = devigged["outcome"].astype(str).str.strip().str.lower()
    census.no_model_probability = int(probability.isna().sum())
    with_probability = probability.notna()
    census.push = int((with_probability & (outcome == "push")).sum())
    census.void = int((with_probability & (outcome == "void")).sum())
    census.unsettleable = int((with_probability & (outcome == "unsettleable")).sum())
    keep = with_probability & outcome.isin(SCORABLE_OUTCOMES)
    census.other_outcome = int(
        (
            with_probability
            & ~outcome.isin(SCORABLE_OUTCOMES | {"push", "void", "unsettleable"})
        ).sum()
    )
    kept = devigged[keep].copy()
    kept["won"] = (outcome[keep] == "won").astype(float)
    kept["model_implied"] = probability[keep].astype(float)
    kept["disagreement"] = kept["model_implied"] - pd.to_numeric(
        kept["market_implied"], errors="coerce"
    )
    census.scored = int(len(kept))
    return kept.reset_index(drop=True), census


# --------------------------------------------------------------------------
# The regression
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Coefficient:
    """One fitted coefficient, its clustered interval, and what it took.

    `null_value` is the value the coefficient takes when the thing it measures
    is absent: **zero** for the disagreement and for the intercept, and **one**
    for the market, because a calibrated de-vigged price realises all of its
    own probability.

    `answers_the_question` is the important field, and it is True for exactly
    one coefficient in this regression. `stats.RoiInterval.verdict` is the only
    place in this repository a sign becomes a word, and the words it produces
    are *demonstrated edge* and *demonstrated deficit* — claims about a model
    having skill. Three of the four things this module could hand it are not
    that:

    * the **market** coefficient of 0.97 excludes zero on the positive side, so
      a predicate that never asked what the null was would announce a
      demonstrated edge on a number describing the **market**;
    * the **intercept**, positive and excluding zero, is a level miscalibration
      of the de-vigged price, not an edge;
    * the same is true of the raw-market fit's terms.

    So :meth:`verdict` **raises** for every coefficient but the disagreement,
    and the rest are described by :meth:`null_note`, which states plainly
    whether the corrected interval contains the null and never uses the
    vocabulary of a claim. This is the defect
    `tests/test_the_headline_reads_the_sign.py` pins, arriving through a door
    that test does not watch, and it is closed by making it impossible rather
    than by remembering.
    """

    name: str
    estimate: float
    standard_error: float
    rows: int
    clusters: int
    cluster_unit: str
    looks: int = 1
    null_value: float = 0.0
    #: True for the disagreement coefficient and nothing else. See the class
    #: docstring: it is what gates `verdict()`.
    answers_the_question: bool = False

    def as_interval(self) -> S.RoiInterval:
        """The shared interval object, so the arithmetic lives in one module.

        A coefficient is not a return and this does not pretend otherwise; what
        is shared is the 95% multiplier, the Bonferroni widening from the
        ledger's cumulative count, the declared row floor, and the one function
        in this repository that turns a sign into a word.
        """
        return S.RoiInterval(
            roi=self.estimate,
            low=self.estimate - S.Z95 * self.standard_error,
            high=self.estimate + S.Z95 * self.standard_error,
            bets=self.rows,
            clusters=self.clusters,
            standard_error=self.standard_error,
            looks=self.looks,
            cluster_unit=self.cluster_unit,
        )

    @property
    def low(self) -> float:
        return self.as_interval().low

    @property
    def high(self) -> float:
        return self.as_interval().high

    @property
    def adjusted_low(self) -> float:
        return self.as_interval().adjusted_low

    @property
    def adjusted_high(self) -> float:
        return self.as_interval().adjusted_high

    @property
    def enough_evidence(self) -> bool:
        return self.rows >= MINIMUM_ROWS and self.clusters >= MINIMUM_CLUSTERS

    def contains(self, value: float) -> bool:
        """Whether the family-corrected interval contains a value.

        Corrected rather than raw, everywhere it is consulted. The correction is
        the ledger's cumulative count, and a predicate that reads the raw
        interval is a predicate that has not counted the search.
        """
        return self.adjusted_low <= value <= self.adjusted_high

    def verdict(self) -> str:
        """The one sentence this coefficient may be described by.

        Delegates to `stats.RoiInterval.verdict`, which is the only place in
        this repository a sign becomes a word. The cluster floor is the one
        branch handled here, and it deliberately returns a *not enough
        evidence* phrase without ever consulting the sign: a cluster-robust
        sandwich is downward biased with few clusters, so its interval below the
        floor is narrow for a reason that has nothing to do with the model.

        **Raises for every coefficient but the disagreement.** See the class
        docstring — the words this returns are claims about a model having
        skill, and the market coefficient and the intercept are not that.
        """
        if not self.answers_the_question:
            raise ValueError(
                f"{self.name!r} is not the coefficient that answers the "
                "question, so `stats.RoiInterval.verdict` must not describe it: "
                "that function reads a sign and produces 'demonstrated edge', "
                "and a market coefficient of 0.97 excludes zero on the positive "
                "side while an intercept excluding zero is a level "
                "miscalibration. Either would be announced as an edge by a "
                "predicate that never asked what the null was. Use "
                "`null_note()` instead."
            )
        if not self.enough_evidence:
            return self.floor_note()
        return self.as_interval().verdict()

    def floor_note(self) -> str:
        """Which declared floor binds, named, and never reading the sign.

        The row floor's exact wording is `stats.RoiInterval.verdict`'s, so both
        reports say it the same way; that branch of that function never
        consults the sign either. The cluster floor is this module's own,
        because a cluster-robust sandwich is downward biased with few clusters
        and no other report in this repository fits one.
        """
        if self.rows < MINIMUM_ROWS:
            return self.as_interval().verdict()
        return (
            f"not enough evidence ({self.clusters:,} {self.cluster_unit}s, "
            f"below the {MINIMUM_CLUSTERS:,} declared in advance, over "
            f"{self.rows:,} rows)"
        )

    def null_note(self) -> str:
        """A plain statement for a coefficient whose sign is not a claim.

        Says whether the family-corrected interval contains the value the
        coefficient would take if the thing it measures were absent, and says
        it without ever using the vocabulary of an edge or a deficit.
        """
        if not self.enough_evidence:
            return self.floor_note()
        if self.null_value == 1.0:
            return self.calibration_note()
        if self.contains(self.null_value):
            return "contains zero"
        direction = "above" if self.estimate > self.null_value else "below"
        return (
            f"excludes zero, {direction} it — a level the de-vigged price does "
            "not account for, which is a fact about the fit rather than a claim "
            "about the model"
        )

    def describe(self) -> str:
        """The verdict where one is permitted, and a plain null note otherwise."""
        return self.verdict() if self.answers_the_question else self.null_note()

    def gloss(self) -> str:
        """What the verdict means for this model, in the reader's language."""
        if not self.answers_the_question:
            return self.null_note()
        if not self.enough_evidence:
            return (
                "There is no number here yet, and that is not a null result — "
                "it is a sample below the floor declared in advance."
            )
        verdict = self.verdict()
        if verdict == S.NO_DEMONSTRATED_EDGE:
            return (
                "**The model knows nothing the price does not.** The interval "
                "on the disagreement includes zero, so none of the claimed edge "
                "is demonstrably realised."
            )
        if verdict == S.DEMONSTRATED_DEFICIT:
            return (
                "**Anti-predictive: the bigger the claimed edge, the worse the "
                "bet.** The disagreement coefficient excludes zero on the "
                "losing side, which means raising the edge threshold selects "
                "worse wagers, not better ones."
            )
        return (
            f"**{self.estimate:.0%} of each point of claimed edge is realised.** "
            "The interval excludes zero on the winning side. That is a "
            "necessary condition for a real edge and not a sufficient one: "
            "`price_backtest.py` decides whether a policy would have made "
            "money, and `reachability` decides whether the price could have "
            "been taken."
        )

    def calibration_note(self) -> str:
        """For a coefficient whose null is one: is the de-vigged price calibrated?"""
        if not self.enough_evidence:
            return (
                f"not enough evidence to say whether the de-vigged price is "
                f"calibrated ({self.rows:,} rows across {self.clusters:,} "
                f"{self.cluster_unit}s)"
            )
        if self.contains(1.0):
            return (
                "contains 1.0 — the de-vigged price is calibrated at this "
                "sample size, which is what makes the disagreement coefficient "
                "readable"
            )
        direction = "over" if self.estimate > 1.0 else "under"
        return (
            f"excludes 1.0 ({direction}-responsive) — the de-vigged price is "
            "not calibrated on this population, so read the disagreement "
            "coefficient only after understanding why"
        )

    def to_json(self) -> dict:
        payload = {
            "name": self.name,
            "estimate": self.estimate,
            "standard_error": self.standard_error,
            "low": self.low,
            "high": self.high,
            "adjusted_low": self.adjusted_low,
            "adjusted_high": self.adjusted_high,
            "rows": self.rows,
            "clusters": self.clusters,
            "cluster_unit": self.cluster_unit,
            "looks": self.looks,
            "null_value": self.null_value,
            "answers_the_question": self.answers_the_question,
            "enough_evidence": self.enough_evidence,
            "contains_null": self.contains(self.null_value),
            # `reading` is what every row carries and what `render` prints.
            # `verdict` is present on the ONE coefficient whose sign is a claim
            # about skill, so a grep for the word finds one row per fit rather
            # than three, and a reader who quotes it cannot quote the market's.
            "reading": self.describe(),
            "gloss": self.gloss(),
        }
        if self.answers_the_question:
            payload["verdict"] = self.verdict()
        return payload


def coefficient_from_row(row: Mapping) -> Coefficient:
    """Rebuild a coefficient from a record row, so `render` needs no frame."""
    return Coefficient(
        name=str(row.get("name", "")),
        estimate=float(row.get("estimate", 0.0)),
        standard_error=float(row.get("standard_error", 0.0)),
        rows=int(row.get("rows", 0)),
        clusters=int(row.get("clusters", 0)),
        cluster_unit=str(row.get("cluster_unit", "game")),
        looks=int(row.get("looks", 1)),
        null_value=float(row.get("null_value", 0.0)),
        answers_the_question=bool(row.get("answers_the_question", False)),
    )


def cluster_robust(
    design: np.ndarray, response: np.ndarray, groups: Sequence
) -> tuple[np.ndarray, np.ndarray, int]:
    """Least squares with a cluster-robust sandwich, and the cluster count.

    ``V = (X'X)^-1 [ sum_g (X_g'u_g)(X_g'u_g)' ] (X'X)^-1 x G/(G-1) x (N-1)/(N-K)``

    The finite-cluster correction is the standard one, applied rather than
    omitted: it only ever widens, and this repository's standing failure mode is
    an interval that is too narrow. The football lab's forward ledger shipped
    one that was 10.3x too narrow on the one report that grows all season.

    Raises :class:`NotIdentified` when the design is rank deficient, rather than
    returning a pseudo-inverse's plausible-looking answer. The commonest cause
    is a disagreement column that never varies, and its coefficient is then
    undefined rather than zero — a fact about the wiring, not about the model.
    """
    X = np.asarray(design, dtype=float)
    y = np.asarray(response, dtype=float)
    if X.ndim != 2 or len(X) != len(y):
        raise ForecastSkillError("The design and the response are different lengths.")
    n, k = X.shape
    if n <= k:
        raise NotIdentified(
            f"{n:,} row(s) cannot identify {k} coefficient(s). Nothing was fitted."
        )
    xtx = X.T @ X
    if int(np.linalg.matrix_rank(xtx)) < k:
        constant = [
            index
            for index in range(k)
            if float(np.ptp(X[:, index])) == 0.0 and index != 0
        ]
        raise NotIdentified(
            "The design matrix is rank deficient"
            + (
                f" — column(s) {constant} never vary"
                if constant
                else ""
            )
            + ". A coefficient with no variation to explain is undefined rather "
            "than zero, and the difference matters: zero is a finding about the "
            "model and undefined is a fact about the wiring. Nothing was fitted."
        )
    bread = np.linalg.inv(xtx)
    beta = bread @ (X.T @ y)
    residual = y - X @ beta
    codes, uniques = pd.factorize(pd.Series(list(groups)), sort=False)
    clusters = int(len(uniques))
    if clusters < 2:
        raise NotIdentified(
            f"{clusters} cluster(s) cannot support a clustered standard error. "
            "One game is not a sample of games."
        )
    scores = X * residual[:, None]
    summed = np.zeros((clusters, k), dtype=float)
    np.add.at(summed, codes, scores)
    meat = summed.T @ summed
    correction = (clusters / (clusters - 1)) * ((n - 1) / (n - k))
    covariance = bread @ meat @ bread * correction
    standard_errors = np.sqrt(np.clip(np.diag(covariance), 0.0, None))
    return beta, standard_errors, clusters


def fit(frame: pd.DataFrame, *, looks: int = 1) -> dict:
    """Fit `outcome ~ market_implied + (model_implied - market_implied)`.

    Clustered by game **and** by day, with the wider standard error reported per
    coefficient. Dependence runs within a game, which makes the game canonical;
    a model with a shared daily component makes a whole slate correlated, and
    this module cannot know in advance which applies. Choosing the narrower
    after seeing both is the move the rest of this repository exists to prevent.

    Returns a plain-data record. A refusal is returned rather than raised, with
    its reason, so a report can print *why* there is no number instead of
    stopping — a report that stops leaves the reader with the previous run's
    number and no indication it is stale.
    """
    if frame.empty:
        return {"fitted": False, "reason": NOTHING_TO_MEASURE, "rows": 0}
    market = pd.to_numeric(frame["market_implied"], errors="coerce").to_numpy(dtype=float)
    disagreement = pd.to_numeric(frame["disagreement"], errors="coerce").to_numpy(
        dtype=float
    )
    won = pd.to_numeric(frame["won"], errors="coerce").to_numpy(dtype=float)
    design = np.column_stack([np.ones(len(frame)), market, disagreement])
    try:
        by_game = cluster_robust(design, won, frame["event_id"].astype(str))
        by_day = cluster_robust(design, won, frame["slate_date"].astype(str))
    except NotIdentified as exc:
        return {"fitted": False, "reason": str(exc), "rows": int(len(frame))}

    beta, game_errors, game_clusters = by_game
    _, day_errors, day_clusters = by_day
    #: Order matters: it is the design matrix's column order, and the third
    #: column is the one the whole report is about.
    names = ("intercept", "market_implied", "disagreement")
    nulls = (0.0, 1.0, 0.0)
    coefficients: list[dict] = []
    for index, (name, null) in enumerate(zip(names, nulls)):
        wider_is_day = float(day_errors[index]) > float(game_errors[index])
        coefficients.append(
            Coefficient(
                name=name,
                estimate=float(beta[index]),
                standard_error=float(
                    day_errors[index] if wider_is_day else game_errors[index]
                ),
                rows=int(len(frame)),
                clusters=int(day_clusters if wider_is_day else game_clusters),
                cluster_unit="day" if wider_is_day else "game",
                looks=int(looks),
                null_value=float(null),
                answers_the_question=(name == "disagreement"),
            ).to_json()
        )
    return {
        "fitted": True,
        "reason": "",
        "rows": int(len(frame)),
        "games": int(game_clusters),
        "days": int(day_clusters),
        "coefficients": coefficients,
        # Kept so a reader can see that the reported error is the wider of two
        # and by how much, rather than taking "the wider wins" on trust.
        "standard_errors_by_game": [float(v) for v in game_errors],
        "standard_errors_by_day": [float(v) for v in day_errors],
    }


def pooled_fit_of(record: Mapping) -> dict:
    """The pooled fit out of a record, for the one comparison `render` makes."""
    return (record.get("pooled") or {}).get("fit") or {}


def coefficient(fitted: Mapping, name: str) -> dict:
    """One named coefficient out of a fit record, or an empty dict."""
    for row in (fitted or {}).get("coefficients", []) or []:
        if row.get("name") == name:
            return dict(row)
    return {}


# --------------------------------------------------------------------------
# Brier
# --------------------------------------------------------------------------


def brier(frame: pd.DataFrame, *, looks: int = 1) -> dict:
    """The model and the market scored on the same rows, side by side.

    Three market numbers, not one: de-vigged (the fair price, the honest
    comparison), raw (the price with the hold still in it, which over-estimates
    every side by construction and is therefore being scored with a handicap),
    and the population's own base rate as the climatology reference.

    The paired difference is clustered through `stats.interval_two_way` rather
    than through anything written in this module, because a clustered mean is
    exactly what that function computes and a second copy of a formula drifts.

    **The sign is chosen so the shared verdict function reads it correctly.**
    The quantity clustered is `brier_market - brier_model`, so positive means
    the model is more accurate. A Brier score is better when it is lower, and
    handing a lower-is-better quantity to a predicate that says "edge" when the
    number is positive would announce a demonstrated edge on a model measurably
    worse than the price — the same defect as a market coefficient wearing an
    edge verdict, closed the same way.
    """
    if frame.empty:
        return {"rows": 0, "scored": False}
    won = pd.to_numeric(frame["won"], errors="coerce")
    model = pd.to_numeric(frame["model_implied"], errors="coerce")
    fair = pd.to_numeric(frame["market_implied"], errors="coerce")
    raw = pd.to_numeric(frame["market_implied_raw"], errors="coerce")
    base = float(won.mean())

    model_loss = (model - won) ** 2
    fair_loss = (fair - won) ** 2
    raw_loss = (raw - won) ** 2
    base_loss = (base - won) ** 2

    advantage_fair = S.interval_two_way(
        frame.assign(profit_units=(fair_loss - model_loss)), looks=looks
    )
    advantage_raw = S.interval_two_way(
        frame.assign(profit_units=(raw_loss - model_loss)), looks=looks
    )
    return {
        "rows": int(len(frame)),
        "scored": True,
        "base_rate": base,
        "model": float(model_loss.mean()),
        "market_devigged": float(fair_loss.mean()),
        "market_raw": float(raw_loss.mean()),
        "base_rate_reference": float(base_loss.mean()),
        # 1 - model/market. Positive means the model beats that market column.
        "skill_vs_devigged": (
            float(1.0 - model_loss.mean() / fair_loss.mean())
            if float(fair_loss.mean())
            else None
        ),
        "skill_vs_raw": (
            float(1.0 - model_loss.mean() / raw_loss.mean())
            if float(raw_loss.mean())
            else None
        ),
        "advantage_over_devigged": _interval_row(
            advantage_fair, name="model minus de-vigged market"
        ),
        "advantage_over_raw": _interval_row(
            advantage_raw, name="model minus raw market"
        ),
        "loses_to_the_handicapped_market": bool(
            float(model_loss.mean()) > float(raw_loss.mean())
        ),
    }


def _interval_row(interval: S.RoiInterval, *, name: str = "") -> dict:
    """One `RoiInterval` as plain data, so `render` needs no objects."""
    return {
        "name": name,
        "value": interval.roi,
        "low": interval.low,
        "high": interval.high,
        "adjusted_low": interval.adjusted_low,
        "adjusted_high": interval.adjusted_high,
        "rows": interval.bets,
        "clusters": interval.clusters,
        "cluster_unit": interval.cluster_unit,
        "looks": interval.looks,
        "standard_error": interval.standard_error,
        "enough_evidence": interval.enough_evidence,
        "verdict": interval.verdict(),
    }


# --------------------------------------------------------------------------
# Claimed edge, bucketed
# --------------------------------------------------------------------------


def edge_buckets(frame: pd.DataFrame, *, looks: int = 1) -> list[dict]:
    """Realised outcome against model-implied, per bucket of **claimed** edge.

    This is the table that makes anti-predictiveness impossible to wave away. A
    coefficient is one number and a reader can call it noise; a column that gets
    steadily more negative as the claimed edge grows is a shape.

    Each bucket prints its `n`, what the model said would happen, what the
    de-vigged price said, and what did happen with a Wilson interval — Wilson
    rather than the normal approximation because the extreme buckets are exactly
    where small counts and proportions near zero or one live. Below
    :data:`MINIMUM_BUCKET` rows a bucket prints its count and no frequency.
    """
    if frame.empty or "edge" not in frame.columns:
        return []
    edge = pd.to_numeric(frame["edge"], errors="coerce")
    rows: list[dict] = []
    for low, high in EDGE_BUCKETS:
        last = high == EDGE_BUCKETS[-1][1]
        in_bucket = (edge >= low) & ((edge <= high) if last else (edge < high))
        chunk = frame[in_bucket.fillna(False)]
        n = int(len(chunk))
        row: dict = {
            "low": low,
            "high": high,
            "rows": n,
            "games": int(chunk["event_id"].nunique()) if n else 0,
            "enough": n >= MINIMUM_BUCKET,
        }
        if not n:
            rows.append(row)
            continue
        wins = int(pd.to_numeric(chunk["won"], errors="coerce").sum())
        realised = wins / n
        wilson_low, wilson_high = S.wilson_interval(wins, n)
        row.update(
            {
                "claimed_edge": float(pd.to_numeric(chunk["edge"], errors="coerce").mean()),
                "model_implied": float(
                    pd.to_numeric(chunk["model_implied"], errors="coerce").mean()
                ),
                "market_implied": float(
                    pd.to_numeric(chunk["market_implied"], errors="coerce").mean()
                ),
                "realised": float(realised),
                "wilson_low": float(wilson_low),
                "wilson_high": float(wilson_high),
                # The whole point of the table: what the model claimed minus
                # what happened. Negative means the model was optimistic here.
                "gap_to_model": float(realised)
                - float(pd.to_numeric(chunk["model_implied"], errors="coerce").mean()),
                "gap_to_market": float(realised)
                - float(pd.to_numeric(chunk["market_implied"], errors="coerce").mean()),
            }
        )
        if "profit_units" in chunk.columns:
            settled = chunk[
                pd.to_numeric(chunk["profit_units"], errors="coerce").notna()
            ]
            if not settled.empty:
                row["roi"] = _interval_row(
                    S.interval_two_way(
                        settled.assign(
                            profit_units=pd.to_numeric(
                                settled["profit_units"], errors="coerce"
                            )
                        ),
                        looks=looks,
                    ),
                    name="realised return",
                )
        rows.append(row)
    return rows


def anti_predictive(buckets: Sequence[Mapping]) -> dict:
    """Do the biggest claimed edges do worst? Measured, over usable buckets.

    Compares the shortfall — realised minus model-implied — in the highest
    claimed-edge bucket that clears :data:`MINIMUM_BUCKET` against the lowest.
    `worse_at_the_top` is the anti-predictive shape; it is reported as a fact
    about two buckets with both their `n`s beside it, never as a significance
    claim. The disagreement coefficient is the test; this is the picture.
    """
    usable = [b for b in buckets if b.get("enough") and "gap_to_model" in b]
    if len(usable) < 2:
        return {"usable_buckets": len(usable), "measurable": False}
    lowest, highest = usable[0], usable[-1]
    return {
        "usable_buckets": len(usable),
        "measurable": True,
        "lowest_bucket": {
            "low": lowest["low"],
            "high": lowest["high"],
            "rows": lowest["rows"],
            "gap_to_model": lowest["gap_to_model"],
        },
        "highest_bucket": {
            "low": highest["low"],
            "high": highest["high"],
            "rows": highest["rows"],
            "gap_to_model": highest["gap_to_model"],
        },
        "worse_at_the_top": bool(
            highest["gap_to_model"] < lowest["gap_to_model"]
        ),
        "shortfall_widens_by": float(
            lowest["gap_to_model"] - highest["gap_to_model"]
        ),
    }


# --------------------------------------------------------------------------
# Cells: per tier, and pooled under its caveat
# --------------------------------------------------------------------------


def _tiers_in(frame: pd.DataFrame) -> list[str]:
    """Tiers present, strongest first, then anything unrecognised.

    The same ordering `price_backtest` uses, from the same `TIER_ORDER`, so two
    reports of the same run cannot list the tiers differently and read as two
    populations.
    """
    present = {str(t) for t in frame["tier"].dropna().unique()}
    ordered = [t for t in TIER_ORDER if t in present]
    return ordered + sorted(present - set(ordered))


def measure(frame: pd.DataFrame, *, looks: int = 1, label: str = "") -> dict:
    """Everything this report says about one population, as plain data."""
    buckets = edge_buckets(frame, looks=looks)
    return {
        "label": label,
        "rows": int(len(frame)),
        "games": int(frame["event_id"].nunique()) if not frame.empty else 0,
        "days": int(frame["slate_date"].nunique()) if not frame.empty else 0,
        "fit": fit(frame, looks=looks),
        "brier": brier(frame, looks=looks),
        "buckets": buckets,
        # Every scorable row lands in exactly one bucket unless its claimed edge
        # is unreadable, and a bucket table quietly shorter than its population
        # is the same defect as a pooled figure quietly larger than its tiers.
        "rows_outside_every_bucket": int(len(frame))
        - sum(int(b.get("rows", 0)) for b in buckets),
        "anti_predictive": anti_predictive(buckets),
    }


# --------------------------------------------------------------------------
# The record
# --------------------------------------------------------------------------


@dataclass
class SkillInputs:
    """Every graded wager the run measures. Assembled by the script.

    One frame, not two. This regression runs over **every graded wager**, not
    over the bets a threshold let through: the threshold's own effect is the
    bucket table's subject, and fitting only above it would condition the
    regression on the variable whose usefulness is the question.
    """

    graded: pd.DataFrame = field(default_factory=pd.DataFrame)
    source: str = ""
    season_label: str = ""
    snapshot_phase: str = ""
    pair_scope: str = PAIR_SCOPES[0]
    edge_threshold: float = BET_EDGE_THRESHOLD


def build_record(
    inputs: SkillInputs,
    *,
    competition: Competition = CBB,
    looks: int = 1,
    generated_at: str = "",
) -> dict:
    """Every number this run made, as plain data. `render` is pure over it.

    The de-vig, the population census and both accounting identities happen
    here, and a record is **refused** when either identity fails to reconcile. A
    wager that reached none of the buckets has vanished from a measurement, and
    a measurement that silently lost rows still prints an interval that looks
    exactly like one that did not.
    """
    graded = inputs.graded
    if not graded.empty:
        require_columns(graded, SKILL_COLUMNS, "the graded wager frame")
        if "edge" not in graded.columns:
            # `price_backtest.add_edge`, not a second definition of the word.
            graded = add_edge(graded)

    priced, devig_census = devig(graded, scope=inputs.pair_scope)
    if not devig_census.reconciles:
        raise ForecastSkillError(
            f"The de-vig census does not reconcile: {devig_census.devigged:,} "
            f"de-vigged plus {devig_census.excluded:,} excluded is not the "
            f"{devig_census.supplied:,} supplied. A row that reached neither "
            "bucket has vanished from the measurement, and the regression would "
            "still print an interval. Nothing was recorded."
        )
    population, population_census = scorable(priced)
    if not population_census.reconciles:
        raise ForecastSkillError(
            f"The population census does not reconcile: "
            f"{population_census.scored:,} scored plus "
            f"{population_census.excluded:,} excluded is not the "
            f"{population_census.devigged:,} de-vigged. Nothing was recorded."
        )

    tiers = (
        [
            measure(
                population[population["tier"].astype(str) == tier],
                looks=looks,
                label=tier,
            )
            for tier in _tiers_in(population)
        ]
        if not population.empty
        else []
    )
    # The pooled figure must equal the tiers plus whatever could not be placed
    # in one. A row whose tier is missing belongs to no tier section, and a
    # pooled number quietly larger than the sum of its tiers is how a Division I
    # headline reappears after being forbidden. Counted and printed.
    tiered_rows = sum(int(t["rows"]) for t in tiers)
    return {
        "record_version": RECORD_VERSION,
        "competition": competition.key,
        "title": competition.title,
        "generated_at": generated_at,
        "source": inputs.source,
        "season_label": inputs.season_label,
        "snapshot_phase": inputs.snapshot_phase,
        "edge_threshold": float(inputs.edge_threshold),
        "devig_method": DEVIG_METHOD,
        "pair_scope": inputs.pair_scope,
        "minimum_rows": MINIMUM_ROWS,
        "minimum_clusters": MINIMUM_CLUSTERS,
        "minimum_bucket": MINIMUM_BUCKET,
        "edge_buckets": [list(b) for b in EDGE_BUCKETS],
        "looks": int(looks),
        "correction_factor": S.bonferroni_factor(int(looks)),
        "devig_census": devig_census.to_json(),
        "population_census": population_census.to_json(),
        "overround": overround_summary(priced),
        "by_tier": tiers,
        "rows_without_a_tier": int(len(population)) - tiered_rows,
        "pooled": measure(population, looks=looks, label="every tier pooled"),
        # The same fit on the un-de-vigged probabilities. The de-vig method is a
        # choice, and a choice nobody can see the effect of is an assumption.
        "raw_market_fit": (
            fit(
                population.assign(
                    market_implied=pd.to_numeric(
                        population["market_implied_raw"], errors="coerce"
                    ),
                    disagreement=pd.to_numeric(
                        population["model_implied"], errors="coerce"
                    )
                    - pd.to_numeric(population["market_implied_raw"], errors="coerce"),
                ),
                looks=looks,
            )
            if not population.empty
            else {"fitted": False, "reason": NOTHING_TO_MEASURE, "rows": 0}
        ),
    }


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def _coefficient_cells(row: Mapping) -> tuple[str, str, str]:
    """The estimate, its interval and the corrected interval — or three dashes.

    **Below the declared floors there is no number.** A +0.4 disagreement
    coefficient over 40 bets and a coin flip are the same claim at that sample
    size, and printing the +0.4 invites somebody to quote it out of the row that
    qualifies it.
    """
    if not row or not row.get("enough_evidence"):
        return "—", "—", "—"
    return (
        f"{row['estimate']:+.3f}",
        f"{row['low']:+.3f} to {row['high']:+.3f}",
        f"{row['adjusted_low']:+.3f} to {row['adjusted_high']:+.3f}",
    )


def _nothing(what: str) -> list[str]:
    return [
        f"**{NOTHING_TO_MEASURE.capitalize()}.** {what} It is said in words "
        "rather than shown as an empty table, because an empty table reads as a "
        "null result and a null result is a claim.",
        "",
    ]


def bucket_label(low: float, high: float) -> str:
    """A claimed-edge bucket's name, with no `inf` in it.

    Public because the entry point prints the same buckets to a console and a
    second formatter would be free to label them differently — and a bucket
    called `-inf% to -10%` on stdout and `below -10%` in the report is two names
    for one row, which is how a reader ends up comparing two tables that are not
    the same table.
    """
    if low == float("-inf"):
        return f"below {high:+.0%}"
    if high == float("inf"):
        return f"{low:+.0%} and above"
    return f"{low:+.0%} to {high:+.0%}"


def _fit_section(measured: Mapping) -> list[str]:
    """One population's regression, as table rows plus the sentence that reads it."""
    lines: list[str] = []
    add = lines.append
    fitted = measured.get("fit") or {}
    if not fitted.get("fitted"):
        add(
            f"**Not fitted.** {fitted.get('reason') or NOTHING_TO_MEASURE} "
            f"({int(fitted.get('rows', 0)):,} row(s) supplied.)"
        )
        add("")
        return lines
    add(
        f"{int(measured.get('rows', 0)):,} graded wagers across "
        f"{int(measured.get('games', 0)):,} games and "
        f"{int(measured.get('days', 0)):,} slate days."
    )
    add("")
    add(
        "| Term | Null | Coefficient | 95% interval | Family-corrected | "
        "Rows | Clusters | Reading |"
    )
    add("|:---|---:|---:|:---|:---|---:|---:|:---|")
    for row in fitted.get("coefficients", []):
        estimate, interval, corrected = _coefficient_cells(row)
        add(
            f"| {row['name']} | {row['null_value']:.0f} | {estimate} | "
            f"{interval} | {corrected} | {row['rows']:,} | "
            f"{row['clusters']:,} {row['cluster_unit']}s | {row['reading']} |"
        )
    add("")
    disagreement = coefficient(fitted, "disagreement")
    if disagreement:
        add(coefficient_from_row(disagreement).gloss())
        add("")
    market = coefficient(fitted, "market_implied")
    if market:
        add(
            "The market coefficient is a diagnostic, not a headline. Its null "
            f"is 1.0 rather than zero, and its reading is: "
            f"*{market['reading']}*. The intercept is read the same way. "
            "Neither is ever described as an edge, because the words "
            "*demonstrated edge* are a claim about a **model**, and a "
            "coefficient of 0.97 on the **market** excludes zero on the "
            "positive side."
        )
        add("")
    return lines


def _brier_section(measured: Mapping) -> list[str]:
    lines: list[str] = []
    add = lines.append
    scores = measured.get("brier") or {}
    if not scores.get("scored"):
        lines.extend(_nothing("No row carries both a probability and an outcome."))
        return lines
    n = int(scores.get("rows", 0))
    add("| Forecaster | Brier score | Rows |")
    add("|:---|---:|---:|")
    add(f"| the model | {scores['model']:.5f} | {n:,} |")
    add(f"| the market, de-vigged | {scores['market_devigged']:.5f} | {n:,} |")
    add(f"| the market, **raw** (vig left in) | {scores['market_raw']:.5f} | {n:,} |")
    add(
        f"| the base rate ({scores['base_rate']:.1%} of these wagers won) | "
        f"{scores['base_rate_reference']:.5f} | {n:,} |"
    )
    add("")
    for key, label in (
        ("advantage_over_devigged", "against the de-vigged market"),
        ("advantage_over_raw", "against the raw, handicapped market"),
    ):
        row = scores.get(key) or {}
        if not row:
            continue
        add(
            f"- **{label}:** the model's Brier advantage is "
            f"{row['value']:+.5f} over {row['rows']:,} wagers across "
            f"{row['clusters']:,} {row['cluster_unit']}s, 95% interval "
            f"{row['low']:+.5f} to {row['high']:+.5f}, family-corrected "
            f"{row['adjusted_low']:+.5f} to {row['adjusted_high']:+.5f} — "
            f"{row['verdict']}."
        )
    add("")
    add(
        "Positive is the model being **more** accurate. A Brier score is better "
        "when it is lower, so the quantity clustered is `brier_market − "
        "brier_model` — the sign is chosen that way so the shared verdict "
        "function reads it correctly rather than announcing an edge on a model "
        "that is measurably worse than the price."
    )
    add("")
    if scores.get("loses_to_the_handicapped_market"):
        add(
            "**The model loses to the market even with the vig left in.** That "
            "is decisive: the raw implied probability over-estimates every side "
            "by construction, so it was being scored with a handicap, and it "
            "still won. No de-vig argument recovers this."
        )
        add("")
    return lines


def _bucket_section(measured: Mapping, record: Mapping) -> list[str]:
    lines: list[str] = []
    add = lines.append
    buckets = measured.get("buckets") or []
    if not any(b.get("rows") for b in buckets):
        lines.extend(_nothing("No wager carries a claimed edge."))
        return lines
    minimum = int(record.get("minimum_bucket", MINIMUM_BUCKET))
    add(
        "| Claimed edge | Wagers | Games | Model said | De-vigged price said | "
        "Actually won | Realised − model | Realised return |"
    )
    add("|:---|---:|---:|---:|---:|:---|---:|:---|")
    for bucket in buckets:
        label = bucket_label(bucket["low"], bucket["high"])
        n = int(bucket.get("rows", 0))
        if not n:
            add(f"| {label} | 0 | 0 | — | — | — | — | — |")
            continue
        if not bucket.get("enough"):
            add(f"| {label} | {n:,} | {bucket['games']:,} | — | — | — | — | — |")
            continue
        roi = bucket.get("roi") or {}
        return_cell = "—"
        if roi and roi.get("enough_evidence"):
            return_cell = (
                f"{roi['value']:+.1%} [{roi['low']:+.1%}, {roi['high']:+.1%}]"
            )
        elif roi:
            return_cell = f"— ({roi['rows']:,} settled)"
        add(
            f"| {label} | {n:,} | {bucket['games']:,} | "
            f"{bucket['model_implied']:.1%} | {bucket['market_implied']:.1%} | "
            f"{bucket['realised']:.1%} [{bucket['wilson_low']:.1%}, "
            f"{bucket['wilson_high']:.1%}] | "
            f"{bucket['gap_to_model'] * 100:+.1f} pp | {return_cell} |"
        )
    add("")
    add(
        f"A bucket below {minimum:,} wagers prints its count and no frequency — "
        "the point estimate of nine observations invites a reader to follow the "
        "shape of the line rather than the intervals around it."
    )
    add("")
    outside = int(measured.get("rows_outside_every_bucket", 0))
    if outside:
        add(
            f"**{outside:,} scorable wagers carry no readable claimed edge** and "
            "are in none of these buckets. Counted rather than left as the "
            "difference between the bucket total and the population, because "
            "that difference is invisible and a table shorter than its own "
            "population still looks complete."
        )
        add("")
    shape = measured.get("anti_predictive") or {}
    if shape.get("measurable"):
        low = shape["lowest_bucket"]
        high = shape["highest_bucket"]
        if shape.get("worse_at_the_top"):
            add(
                "**The biggest claimed edges do worst.** The shortfall against "
                f"model-implied is {low['gap_to_model'] * 100:+.1f} pp in the "
                f"{bucket_label(low['low'], low['high'])} bucket "
                f"({low['rows']:,} wagers) and "
                f"{high['gap_to_model'] * 100:+.1f} pp in the "
                f"{bucket_label(high['low'], high['high'])} bucket "
                f"({high['rows']:,} wagers) — it widens by "
                f"{shape['shortfall_widens_by'] * 100:.1f} pp across the range. "
                "That is anti-predictiveness as a table rather than as a minus "
                "sign, and it is the shape that makes raising the edge "
                "threshold the wrong response."
            )
        else:
            add(
                "The shortfall against model-implied does **not** widen with "
                f"the claimed edge: {low['gap_to_model'] * 100:+.1f} pp in the "
                f"{bucket_label(low['low'], low['high'])} bucket "
                f"({low['rows']:,} wagers) against "
                f"{high['gap_to_model'] * 100:+.1f} pp in the "
                f"{bucket_label(high['low'], high['high'])} bucket "
                f"({high['rows']:,} wagers). That is not evidence of skill; the "
                "disagreement coefficient is the test and this is the picture."
            )
        add("")
    return lines


def _threshold_section(record: Mapping) -> list[str]:
    """Why raising the edge threshold cannot help, from this run's own fit."""
    lines: list[str] = []
    add = lines.append
    add("## Why raising the edge threshold cannot help")
    add("")
    add(
        "A card takes a wager when the claimed edge clears a threshold, and at a "
        "fixed price the claimed edge is monotone in the disagreement `d`. Under "
        "the fit above, the realised excess of a wager over the de-vigged price "
        "is `(a + (b_market − 1)·market) + b_disagreement·d`, whose derivative "
        "in `d` is exactly **b_disagreement**. Raising the threshold is a "
        "monotone filter that admits only larger `d`, so:"
    )
    add("")
    add(
        "- `b_disagreement > 0` — a higher threshold selects better wagers, and "
        "that coefficient says how much better."
    )
    add(
        "- `b_disagreement = 0` — a higher threshold selects **the same** wagers "
        "on average, at a smaller sample and a wider interval. It buys nothing "
        "and costs power."
    )
    add(
        "- `b_disagreement < 0` — a higher threshold selects **worse** wagers. "
        "The natural response to a disappointing backtest is the one that makes "
        "it worse, and nothing in a return figure says so."
    )
    add("")
    disagreement = coefficient(pooled_fit_of(record), "disagreement")
    if disagreement and disagreement.get("enough_evidence"):
        add(
            f"This run's pooled disagreement coefficient is "
            f"{disagreement['estimate']:+.3f} "
            f"[{disagreement['low']:+.3f}, {disagreement['high']:+.3f}] over "
            f"{disagreement['rows']:,} wagers across "
            f"{disagreement['clusters']:,} {disagreement['cluster_unit']}s — "
            f"{disagreement['verdict']}. The claimed-edge buckets above are the "
            "measurement of the same thing; the algebra and the table are "
            "printed together because either alone is arguable."
        )
        add("")
    add(
        f"The threshold `price_backtest.BET_EDGE_THRESHOLD` declares in advance "
        f"is {float(record.get('edge_threshold', BET_EDGE_THRESHOLD)):.0%}, and "
        "moving it after seeing a number is the defect this repository is "
        "arranged against. This section exists so that moving it is not even "
        "tempting."
    )
    add("")
    return lines



def _pooling_artefact_warning(record: Mapping) -> list[str]:
    """Say so when the pooled cell claims something no tier claims.

    Three tiers whose intervals each span zero, pooled, can produce an interval
    that does not — the sample triples while the estimate barely moves. That is
    arithmetic, not a discovery, and it is exactly why the brief forbids a
    pooled headline across the whole of Division I: *"High-major, mid-major and
    low-major are different distributions. Never report a single pooled
    headline."*

    This run is the case in point. Every tier's disagreement coefficient reads
    **no demonstrated edge**; pooled reads **demonstrated edge**, in the same
    words this repository reserves for a profitable return. A reader skimming
    for the strongest phrase on the page finds it in the one cell the brief
    says is never the headline.

    So the contradiction is printed where it happens, rather than left for a
    reader to notice by comparing two tables.
    """
    def disagreement_verdict(cell: Mapping) -> str:
        for coefficient in ((cell.get("fit") or {}).get("coefficients") or []):
            if str(coefficient.get("name")) == "disagreement":
                return str(coefficient.get("verdict") or "")
        return ""

    pooled_verdict = disagreement_verdict(record.get("pooled") or {})
    if not pooled_verdict or "not enough evidence" in pooled_verdict:
        return []

    tier_verdicts = [
        verdict
        for cell in (record.get("by_tier") or [])
        if (verdict := disagreement_verdict(cell))
        and "not enough evidence" not in verdict
    ]
    if not tier_verdicts or pooled_verdict in tier_verdicts:
        return []

    return [
        f"> **The pooled verdict is `{pooled_verdict}` and no tier says that.** "
        f"Every tier that cleared its floor reads "
        f"*{', '.join(sorted(set(tier_verdicts)))}*. Three intervals that each "
        "span zero can pool into one that does not, because the sample triples "
        "while the estimate barely moves — that is arithmetic and not a "
        "discovery. It is the reason this lab does not headline a pooled "
        "Division I number, and the reason this line is printed here rather "
        "than left for a reader to find by comparing two tables.",
        "",
    ]


def render(record: Mapping) -> str:
    """The report, as a pure function of the record. No clock, no network."""
    lines: list[str] = []
    add = lines.append
    add(f"# {record.get('title', CBB.title)} — forecast skill")
    add("")
    if record.get("generated_at"):
        add(f"Generated {record['generated_at']}.")
        add("")
    add(
        "**Does the model know anything the price does not?** This report "
        "regresses the outcome of every graded wager on the de-vigged "
        "market-implied probability and on the model's disagreement with it:"
    )
    add("")
    add("```")
    add("outcome = a + b_market · market_implied")
    add("            + b_disagreement · (model_implied − market_implied)")
    add("```")
    add("")
    add(THE_WHOLE_ANSWER)
    add("")
    add(
        "The equivalent unparameterised fit is `outcome ~ market_implied + "
        "model_implied`, and the two are the same regression: the coefficient "
        "on the disagreement here **is** the coefficient on model-implied "
        "there. The reparameterisation puts the answer in its own column "
        "instead of leaving a reader to subtract two correlated coefficients."
    )
    add("")
    add(NHL_PRIOR)
    add("")
    add(DEVIG_SENTENCE)
    add("")
    add(VIG_HANDICAP)
    add("")
    add(
        "**Both sides of a wager are in this population, and they are one "
        "observation seen twice.** A home ticket and its away complement win "
        "and lose together by construction. The intervals are unaffected — the "
        "two rows share a game cluster and the sandwich is built from "
        "per-cluster sums — but the row count is **not** a count of independent "
        "observations, which is why the cluster count is printed beside every "
        "coefficient and why the interval rather than the `n` is the thing to "
        "read."
    )
    add("")

    census = record.get("devig_census") or {}
    population = record.get("population_census") or {}
    if census:
        add("## What was measured, and what could not be")
        add("")
        add(
            f"**{int(census.get('supplied', 0)):,} graded wagers supplied.** "
            f"{int(census.get('devigged', 0)):,} could be de-vigged at the "
            f"`{census.get('scope', '')}` pair scope; "
            f"{int(census.get('excluded', 0)):,} could not and are counted "
            "rather than imputed. A missing price stays missing, and a de-vig "
            "is a price."
        )
        add("")
        add("| Why a wager carries no de-vigged price | Wagers |")
        add("|:---|---:|")
        for key, label in (
            ("unknown_selection", "the selection is not one this lab pairs"),
            ("unreadable_price", "the price could not be read"),
            ("no_complement", "the other side of the wager is not in the frame"),
            ("not_two_sided", "the pair does not hold exactly two opposite sides"),
            (
                "overround_not_above_one",
                "the two sides sum to 1.0 or less, so there is no hold to remove",
            ),
        ):
            add(f"| {label} | {int(census.get(key, 0)):,} |")
        add("")
        add(
            f"The identity `supplied = de-vigged + excluded` "
            f"{'reconciles' if census.get('reconciles') else '**does not reconcile**'}. "
            "A run that does not reconcile writes no record: a measurement that "
            "silently loses a third of its rows still prints an interval, and "
            "the interval looks exactly like one that did not."
        )
        add("")
    if population:
        add(
            f"Of the de-vigged wagers, **{int(population.get('scored', 0)):,} "
            f"are scorable** and {int(population.get('excluded', 0)):,} are not: "
            f"{int(population.get('no_model_probability', 0)):,} carry no model "
            f"probability, {int(population.get('push', 0)):,} pushed, "
            f"{int(population.get('void', 0)):,} were void and "
            f"{int(population.get('unsettleable', 0)):,} were unsettleable. "
            "**A push is not half a win** and is never folded in as one — a "
            "score computed over a denominator that quietly includes pushes "
            "measures a different quantity from the one it names."
        )
        add("")
    hold = record.get("overround") or {}
    if hold.get("pairs"):
        add(
            f"The hold this de-vig removed, measured over {hold['pairs']:,} "
            f"two-sided pairs: median **{hold['median']:.4f}**, mean "
            f"{hold['mean']:.4f}, range {hold['minimum']:.4f} to "
            f"{hold['maximum']:.4f}. Printed because a de-vig is otherwise "
            "invisible, and a population held at 1.02 and one held at 1.09 are "
            "different instruments."
        )
        add("")

    tiers = record.get("by_tier") or []
    add("## Per conference tier")
    add("")
    add(
        "**6 high-major conferences / 79 teams, 10 mid-major / 122, 17 "
        "low-major / 164** are three different distributions, and this lab "
        "exists because the third is plausibly priced with less attention. No "
        "pooled Division I headline is ever reported; the pooled section below "
        "exists only because it is printed beside these."
    )
    add("")
    if not tiers:
        lines.extend(_nothing("No tier has a scorable wager."))
    orphans = int(record.get("rows_without_a_tier", 0))
    if orphans:
        add(
            f"**{orphans:,} scorable wagers carry no conference tier** and "
            "therefore appear in the pooled section below and in no tier "
            "section above it. They are counted here rather than left as the "
            "difference between a pooled figure and the sum of its tiers, "
            "because that difference is how a Division I headline reappears "
            "after being forbidden."
        )
        add("")
    for measured in tiers:
        add(f"### {measured.get('label', '')}")
        add("")
        lines.extend(_fit_section(measured))
        add(f"#### Brier — {measured.get('label', '')}")
        add("")
        lines.extend(_brier_section(measured))
        add(f"#### Claimed edge against what happened — {measured.get('label', '')}")
        add("")
        lines.extend(_bucket_section(measured, record))

    add("## Pooled")
    add("")
    add(POOLED_CAVEAT)
    add("")
    lines.extend(_pooling_artefact_warning(record))
    pooled = record.get("pooled") or {}
    if not pooled or not int(pooled.get("rows", 0)):
        lines.extend(_nothing("Nothing to pool."))
    else:
        lines.extend(_fit_section(pooled))
        add("### Brier — pooled")
        add("")
        lines.extend(_brier_section(pooled))
        add("### Claimed edge against what happened — pooled")
        add("")
        lines.extend(_bucket_section(pooled, record))

    raw_fit = record.get("raw_market_fit") or {}
    add("## The same fit without the de-vig")
    add("")
    add(
        "The de-vig is a choice, and a choice whose effect nobody can see is an "
        "assumption. This is the identical regression run on the **raw** "
        "implied probabilities, with the hold still in them."
    )
    add("")
    add(
        "**Under a constant overround the disagreement coefficient is "
        "algebraically invariant to a multiplicative de-vig, and this table is "
        "how that is checked rather than asserted.** The two designs span the "
        "same column space — `span{1, m, p}` either way, because `k·m` is a "
        "scalar multiple of `m` — so the fitted values are identical and only "
        "the intercept and the market coefficient move. A disagreement "
        "coefficient that *does* move between the two tables is therefore a "
        "fact about the overround **varying** across the population, not about "
        "the de-vig method being wrong, and it is worth understanding before "
        "either number is quoted."
    )
    add("")
    if not raw_fit.get("fitted"):
        add(f"**Not fitted.** {raw_fit.get('reason') or NOTHING_TO_MEASURE}")
        add("")
    else:
        add("| Term | Coefficient | 95% interval | Rows | Clusters |")
        add("|:---|---:|:---|---:|---:|")
        for row in raw_fit.get("coefficients", []):
            estimate, interval, _ = _coefficient_cells(row)
            add(
                f"| {row['name']} | {estimate} | {interval} | {row['rows']:,} | "
                f"{row['clusters']:,} {row['cluster_unit']}s |"
            )
        add("")
        raw_disagreement = coefficient(raw_fit, "disagreement")
        devigged_disagreement = coefficient(pooled_fit_of(record), "disagreement")
        if raw_disagreement and devigged_disagreement:
            moved = abs(
                float(raw_disagreement["estimate"])
                - float(devigged_disagreement["estimate"])
            )
            add(
                f"The disagreement coefficient moved by **{moved:.4f}** between "
                "the de-vigged fit and this one. A move of zero is the "
                "constant-overround case; anything larger is the overround "
                "varying across the population, and the hold summary above says "
                "by how much it varies."
            )
            add("")

    lines.extend(_threshold_section(record))

    looks = int(record.get("looks", 1))
    add("## How this report is corrected, and what it cannot say")
    add("")
    add(
        f"**Family correction: {looks:,} cumulative hypotheses** in the "
        f"experiment ledger, widening every 95% interval by "
        f"x{float(record.get('correction_factor', 1.0)):.2f}. That is the "
        "ledger's cumulative count and never the day's — correcting today's "
        "findings across today's tests is a lie if more were tested last week."
    )
    add("")
    add(
        f"**Below {int(record.get('minimum_rows', MINIMUM_ROWS)):,} scored "
        f"wagers or {int(record.get('minimum_clusters', MINIMUM_CLUSTERS)):,} "
        "clusters there is no number**, only the words *not enough evidence*. "
        "Both floors were declared in advance. The cluster floor is there "
        "because a cluster-robust sandwich is downward biased with few "
        "clusters, and this repository's standing failure mode is an interval "
        "that is too narrow."
    )
    add("")
    add(
        "- It cannot say a model **would have made money**. That is "
        "`price_backtest.py`'s question, and a disagreement coefficient above "
        "zero is a necessary condition for an edge and not a sufficient one."
    )
    add(
        "- It cannot say an edge is **reachable**. An edge living entirely in "
        "prices that vanished is reported as not reachable regardless of its "
        "size or its significance."
    )
    add(
        "- It cannot rule a model **in**. It is a calibration-family instrument "
        "and shares the family's asymmetry: it can kill, and where a priced "
        "test exists the priced test decides."
    )
    add(
        "- It cannot say a market is a play. **No market is allowlisted**, and "
        "an excluded market is never a pass, an avoid, or a no-value call."
    )
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------


def record_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPORT_STEM, ".json")


def report_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPORT_STEM, ".md")


# `ledger_path` and `looks_from_ledger` are imported at the top of this module
# rather than redefined here, and are reachable as `forecast_skill.ledger_path`
# and `forecast_skill.looks_from_ledger` so the script has one door. The
# experiment ledger is deliberately **not** competition-prefixed: it counts every
# hypothesis this lab has ever put to the data across every search, and a
# per-competition ledger in a one-competition repository would be the same file
# with a longer name and a standing invitation to reset the count by adding a
# second one.


def write_record(record: Mapping, path: Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dict(record), indent=2, default=str) + "\n", encoding="utf-8"
    )
    return target


def read_record(path: Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    version = int(payload.get("record_version", 0))
    if version != RECORD_VERSION:
        raise ForecastSkillError(
            f"{Path(path).name} is a version {version} record and this module "
            f"writes version {RECORD_VERSION}. Re-run the regression rather "
            "than re-rendering a record whose shape has changed — a stale "
            "record renders a report with holes in it and nothing looks wrong."
        )
    return payload


def write_report(record: Mapping, path: Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(record), encoding="utf-8")
    return target
