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

## Anti-predictiveness and overconfidence are two different things

The claimed-edge bucket table reports both, apart, under their own names.
**Overconfidence** is realised minus model-implied: how far the model's own
number was above what happened. It widens with the claimed edge under the
winner's curse almost by construction — the top bucket is where the model's
largest over-estimates land — so a widening gap says the model is optimistic
where it is loud, and says nothing on its own about return.
**Anti-predictiveness** is the realised *return* falling as the claimed edge
rises: a statement about money, and the only one of the two that supports
"raising the threshold makes it worse". Until 2026-09-05 this module computed
the first, recorded it under the key `anti_predictive`, and emitted the
threshold sentence from it. Both are now measured and both are printed, and the
threshold sentence is emitted only when the two return intervals are disjoint.

Each bucket's return prints **both** intervals — the raw 95% one and the one
widened by the family-wise correction over the experiment ledger's cumulative
look count — labelled apart, and the disjointness the threshold sentence rests
on is read off the corrected pair, because this comparison is one more look at
the same data as every other interval in this report. Every printed interval
carries `stats.RoiInterval.verdict()` beside it: a bucket whose corrected
interval spans zero reads **no demonstrated edge** in exactly those words, and
*demonstrated edge* and *demonstrated deficit* stay reserved for intervals that
exclude zero after the correction.

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

import dataclasses
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from cbb_betting_lab import restatement as RESTATEMENT
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
    SCORABLE_OUTCOMES,
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
from cbb_betting_lab.models import player_census
from cbb_betting_lab.models import player_rates as _PR
from cbb_betting_lab.stores import _decimal_payout as decimal_payout

# The ONE implementation of "what did a unit staked at this price return". The
# price backtest's `grade()` settles with it, the forward ledger settles with
# it, and this report derives with it when the producer's column did not
# arrive — so a derived return and a carried one are the same arithmetic on the
# same two inputs rather than two functions free to disagree.
from cbb_betting_lab.forward_evidence import profit_units as realised_profit_units


#: Bumped whenever the record's shape changes, so a stale record fails loudly at
#: re-render rather than rendering a report with holes in it. Version 2 carries
#: two populations — every opinion and the threshold-selected subset — where
#: version 1 carried one and could not say which it was. Version 3 splits the
#: single key `anti_predictive` — which held realised-minus-model-implied and
#: was therefore overconfidence printed under the anti-predictive name — into
#: `overconfidence` and `anti_predictive_return`, and the latter carries each
#: bucket's family-corrected interval and its verdict beside the raw one. A
#: version 2 record has none of those keys and every one of them is read by
#: `render`, so re-rendering one would print a bucket section with the
#: anti-predictive paragraph missing entirely and nothing would look wrong.
#: That is exactly what :func:`read_record` refuses. Version 4 adds
#: `populations.excluded_unpairable`, the graded wagers the frame-builder
#: dropped because their book hung one side only.
#:
#: Version 5 makes two shapes larger, and a version 4 record carries neither.
#: `populations.excluded_unpairable` gains `no_pair_key` and `accounted` — the
#: third term of the frame-builder's census and the sum of all three, so the
#: identity the report prints is closed by counts this module holds rather than
#: by a `.get` default standing in for a term nobody copied. And
#: `anti_predictive_return` gains `measured_buckets`, the three disjoint
#: reasons a populated bucket is not usable, and the sign of what was measured
#: — `negative_point_estimates`, `demonstrated_deficits`, `deficit_buckets` and
#: `worst_bucket` — which is what a run with fewer than two usable buckets had
#: no way of reporting at all. `deficit_buckets` is carried beside the count
#: because `worst_bucket` is selected by the lowest point estimate and the
#: count is taken off the corrected high bound: they are not the same bucket,
#: and a renderer given only the count and the worst bucket will print one
#: beside a claim justified by the other. Re-render a version 4 record and the census prints a
#: manufactured zero while the anti-predictive paragraph gives a sample floor
#: as the reason for a silence it did not cause.
#:
#: **Version 6** splits `buckets_with_no_return_figure` into
#: `buckets_with_no_return_column` and `buckets_with_no_settled_wager`, and
#: stamps `roi_absent_because` on every populated bucket that carries no `roi`.
#: The one counter stood for two unrelated facts — a frame with no return
#: column, and a bucket whose wagers are all unsettled — and the renderer
#: printed the second whichever was true, so a version 5 record cannot say
#: which cause it was measured under. It is refused rather than re-rendered.
RECORD_VERSION = 6

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

#: The boolean column the price backtest's `--write-graded` export stamps on
#: every settled opinion: True exactly where `price_backtest.bets_from` would
#: have kept the row, i.e. the wager cleared the edge threshold and was a bet.
#:
#: It exists because of what the export used to be. Until 2026-09-05 the graded
#: frame WAS the bets, so this regression — whose whole point is to run over
#: every opinion rather than *"the small adversely-selected slice a threshold
#: lets through"* — ran over exactly that slice. The selection is made by the
#: model's disagreement with the price, and outcome was then regressed on that
#: same disagreement: the winner's curse was in the coefficient, and every
#: claimed-edge bucket below the threshold was empty by construction.
#:
#: The frame now carries every settled opinion and this column marks the bets,
#: so the report can fit the whole population and show the selected subset
#: BESIDE it — labelled as the winner's-curse comparison, never as the skill
#: measure.
SELECTED_COLUMN = "selected"

#: Optional, and each one turns something on rather than being faked when
#: absent. `book` narrows the de-vig scope to a single book's own two-sided
#: quote; `profit_units` adds the realised return to the bucket table;
#: `player` separates two athletes' props on one event; `edge` is used as
#: supplied rather than recomputed, so this report and the card cannot disagree
#: about what the card claimed; `selected` turns on the selected-subset
#: comparison, and a frame without it reports that subset as not supplied.
OPTIONAL_SKILL_COLUMNS: tuple[str, ...] = (
    "book",
    "player",
    "edge",
    "profit_units",
    SELECTED_COLUMN,
)

#: The two populations, named in words wherever a number from either appears.
#: The first is the skill measure. The second is NOT — it is the model's own
#: choice of rows, and its numbers show how much the winner's curse costs.
ALL_OPINIONS_LABEL = "every settled wager the model had an opinion on"
SELECTED_LABEL = "the threshold-selected bets only"
ALL_OPINIONS_ROLE = "the skill measure"
SELECTED_ROLE = "the winner's-curse comparison, not the skill measure"

#: The graded rows that never reached either population, because the frame
#: handed to this module had already excluded them. `build_skill_frame.py`
#: pairs every graded wager with the SAME book's quote on the other side, and a
#: book that hung one side only supplies no hold — the wager cannot be
#: de-vigged and excluding it is the only honest arithmetic available. That
#: exclusion happens **upstream of this module**, so nothing in this file can
#: see it in the frame: the row is simply not there, and the frame's length is
#: therefore not a count of the graded set.
#:
#: So the builder writes a census beside the frame and this report states it
#: wherever it states a population. Without it a reader would take the frame's
#: length on trust, which is exactly the habit the two-populations section
#: exists to break.
UNPAIRABLE_LABEL = "graded wagers excluded before the frame was built"
UNPAIRABLE_ROLE = (
    "in neither population — no complement at their own book, so no hold and "
    "no fair price"
)
UNPAIRABLE_NOT_SUPPLIED = (
    "No census of excluded wagers was supplied with this frame, so this report "
    "cannot say whether the frame is the whole graded set or a subset of it. "
    "`scripts/build_skill_frame.py` writes that census beside the frame it "
    "builds; a frame from anywhere else carries none."
)

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


# `SCORABLE_OUTCOMES` — won or lost — is imported from `price_backtest`, which
# uses it to cut the graded export, so the export and this regression cannot
# disagree about what "settled" means. A push is not half a win; it is counted
# in the census below and scored nowhere.


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


#: Why a populated claimed-edge bucket carries no `roi`. **These two are
#: disjoint and they are facts about different things**, which is the whole
#: reason they are two constants and not one.
#:
#: * :data:`ROI_ABSENT_NO_RETURN_COLUMN` is a fact about the frame's SHAPE —
#:   the frame handed to this report carries no realised return and none can be
#:   derived from it. It says nothing whatever about whether the wagers in the
#:   bucket settled.
#: * :data:`ROI_ABSENT_NO_SETTLED_WAGER` is a fact about the WAGERS — the
#:   column is there and every row in this bucket is blank in it.
#:
#: Collapsing them is how this report came to print the second as a fact about
#: the archive on a run where the first was true: a frame of 270,504 rows, all
#: of them settled, described on the page as holding nothing *"graded to a
#: profit"*. The counter that produced that sentence could not tell the two
#: apart, so the renderer printed whichever cause the wording assumed.
#:
#: **`ROI_ABSENT_NO_RETURN_COLUMN` cannot be reached through `build_record`, and
#: that is a property worth stating rather than a claim to make quietly.** Both
#: `american_odds` and `outcome` are in :data:`SKILL_COLUMNS`, and
#: `build_record` calls `require_columns(graded, SKILL_COLUMNS)` -- measured:
#: dropping either from a real frame raises `ForecastSkillError` before
#: `edge_buckets` runs. So `_with_realised_return` returns `carries=True` on
#: every frame that reaches the bucket table through the production path, and
#: `buckets_with_no_return_column` is structurally 0 in every published record.
#: It is reachable by calling `edge_buckets` directly, which is what the tests
#: do, and it is kept because the alternative is a renderer whose only branch is
#: the one that was wrong: a cause that is impossible today becomes possible the
#: day a required column becomes optional, and the report that has no words for
#: it prints the other cause's.
ROI_ABSENT_NO_RETURN_COLUMN = "no_return_column"
ROI_ABSENT_NO_SETTLED_WAGER = "no_settled_wager"

#: The two together, so a reader of a bucket can check the key is one of them.
ROI_ABSENT_REASONS: frozenset[str] = frozenset(
    {ROI_ABSENT_NO_RETURN_COLUMN, ROI_ABSENT_NO_SETTLED_WAGER}
)

#: What the bucket table's verdict cell says when a bucket cleared the row floor
#: and carries no `roi`, **per cause**.
#:
#: The cell was the literal `"— (no settled wager)"` for both causes, chosen
#: once and never consulted again — so the table would have asserted the wagers
#: cause directly above a paragraph correctly naming the shape cause. That is
#: the same contradiction the two constants above were split to remove, left
#: standing in the other renderer, and the mutation coverage for the split
#: reached only the paragraph.
ROI_ABSENT_CELLS: dict[str, str] = {
    ROI_ABSENT_NO_RETURN_COLUMN: "— (no return column on this frame)",
    ROI_ABSENT_NO_SETTLED_WAGER: "— (no settled wager)",
}


def _roi_absent_cell(bucket: Mapping) -> str:
    """The verdict cell for a floor-clearing bucket with no `roi`, by cause.

    **Refused, not guessed**, for the reason `_anti_predictive_paragraph` gives
    at greater length: a default here is a sentence about an archive written by
    whichever cause the wording happened to assume.
    """
    reason = bucket.get("roi_absent_because")
    if reason in ROI_ABSENT_CELLS:
        return ROI_ABSENT_CELLS[reason]
    raise ForecastSkillError(
        "A populated claimed-edge bucket "
        f"{bucket_label(bucket.get('low'), bucket.get('high'))} carries no "
        "`roi` and no `roi_absent_because`, so the table cannot say why it "
        "carries no return figure. The two causes — a frame with no return "
        "column at all, and a bucket whose every wager is unsettled — are "
        "different facts about different things. `edge_buckets` stamps the "
        f"reason; a bucket built by hand has to stamp one of "
        f"{sorted(ROI_ABSENT_REASONS)!r} too."
    )


def _with_realised_return(frame: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    """The frame carrying `profit_units`, derived when the producer dropped it.

    **A report may not go quiet because a producer dropped a column it could
    have computed.** That is exactly what happened here: `settled_opinions`
    keeps a row only where `profit_units` is non-null, so every row of the
    graded export had a realised profit in memory — and the export's column
    projection listed the required columns and not this optional one, dropping
    it one line before the write. The consequence was not an error anywhere. It
    was `roi` never being written onto a single bucket, `usable == 0` on every
    real tier, and a report that told its readers anti-predictiveness could not
    be measured because nothing had been graded to a profit.

    **Is the derived value equivalent to the producer's own?** Yes, and not by
    resemblance: this calls `forward_evidence.profit_units`, which is the
    function `scripts/run_price_backtest.py`'s `grade()` calls, on the same two
    inputs it passes — the row's `outcome` and its `american_odds`. The
    producer then runs the result through `pd.to_numeric(..., errors="coerce")`
    and so does this, so a `None` becomes `NaN` on both sides. The claim is
    pinned twice, and one of the two is on a real producer run:
    `test_run_price_backtest.test_the_skill_report_derives_the_same_return_the_
    backtest_graded` takes the file the backtest's `--write-graded` actually
    wrote, drops the column, derives it back and compares it at pandas'
    default tolerance; `test_forecast_skill.test_a_derived_return_is_
    the_same_arithmetic_as_a_supplied_one` does the same on the synthetic
    season and also checks that a frame already carrying the column is handed
    back untouched. Deriving is a belt to the producer's braces and never a
    second opinion.

    **Not bit-equal on the producer's file, and the reason is the file.** Of
    that export's 526,735 rows, 149,868 differ between the stored column and the
    re-derivation, by at most 1.11e-16: `read_csv` cannot recover the last ULP
    `to_csv` wrote. The arithmetic is the same call on the same two inputs; the
    serialisation is what moves. Saying "cell for cell" without that sentence
    claimed something `(a == b).all()` refutes.

    Missingness is part of the claim, not a detail: a won bet at a price this
    lab cannot read carries a **missing** profit and not a zero, and a
    derivation that filled zeroes there would fabricate a number. **Neither pin
    above can fail on it** -- both frames are all-settled, so both compare an
    all-`False` mask to an identical one -- so the claim is tested directly on
    the state, in `test_forecast_skill.test_a_won_bet_at_an_unreadable_price_
    derives_a_missing_profit_not_a_zero`.

    Returns the frame — assigned, never mutated — and whether a return column is
    on it at all. False is a fact about the frame's shape and is reported as
    one.
    """
    if "profit_units" in frame.columns:
        return frame, True
    if "outcome" not in frame.columns or "american_odds" not in frame.columns:
        return frame, False
    derived = pd.Series(
        [
            realised_profit_units(outcome, odds)
            for outcome, odds in zip(frame["outcome"], frame["american_odds"])
        ],
        index=frame.index,
        dtype="object",
    )
    return frame.assign(
        profit_units=pd.to_numeric(derived, errors="coerce")
    ), True


def edge_buckets(frame: pd.DataFrame, *, looks: int = 1) -> list[dict]:
    """Realised outcome against model-implied, per bucket of **claimed** edge.

    This is the table that makes a shape visible where a coefficient is one
    number a reader can call noise. It carries **two** columns that are easy to
    confuse and are not the same quantity:

    * `gap_to_model` — realised minus model-implied, the model's **over-estimate**
      in that bucket. Read across buckets it is :func:`overconfidence_by_bucket`,
      and a widening gap is the winner's curse: the model's own selection puts
      its biggest over-estimates in its top bucket, whatever relationship it has
      to money.
    * `roi` — the realised **return** over the settled wagers in that bucket, a
      two-way clustered interval with its bet count and cluster unit. Read
      across buckets it is :func:`anti_predictive_return`, and *that* is what
      the word anti-predictive names.

    Each bucket prints its `n`, what the model said would happen, what the
    de-vigged price said, and what did happen with a Wilson interval — Wilson
    rather than the normal approximation because the extreme buckets are exactly
    where small counts and proportions near zero or one live. Below
    :data:`MINIMUM_BUCKET` rows a bucket prints its count and no frequency, and
    below `stats.MINIMUM_BETS` settled wagers it carries no return figure.
    """
    if frame.empty or "edge" not in frame.columns:
        return []
    # Derived here, once, rather than per bucket — and BEFORE the loop, so
    # every bucket in this table answers the same question about the same
    # column. `carries_return` is the frame's shape and travels onto each
    # bucket that ends up with no figure, so no renderer has to guess why.
    frame, carries_return = _with_realised_return(frame)
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
        # **Why there is no figure, recorded by the only code that knows.**
        # A bucket with no `roi` used to say nothing about which of two
        # unrelated causes produced the silence, and the renderer then printed
        # the one its sentence assumed. The cause is written here, where the
        # frame's shape and the bucket's rows are both in hand, and counted
        # downstream rather than inferred.
        if not carries_return:
            row["roi_absent_because"] = ROI_ABSENT_NO_RETURN_COLUMN
        else:
            settled = chunk[
                pd.to_numeric(chunk["profit_units"], errors="coerce").notna()
            ]
            if settled.empty:
                row["roi_absent_because"] = ROI_ABSENT_NO_SETTLED_WAGER
            else:
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


#: What the overconfidence block measures, in the words the report must use for
#: it. Realised minus model-implied is the model's **over-estimate**, and an
#: over-estimate that grows with the claimed edge is the winner's curse: the
#: biggest claimed edges are the biggest over-estimates by construction,
#: whatever relationship the model has to realised return. Until 2026-09-05
#: this quantity was recorded under the key `anti_predictive` and described in
#: the report as anti-predictiveness, which is a different claim about a
#: different quantity.
OVERCONFIDENCE_LABEL = "overconfidence (realised minus model-implied)"

#: What anti-predictiveness actually is: a negative relationship between the
#: model's claimed edge and what the wagers **returned**. It is measured from
#: the realised return per claimed-edge bucket, which is a fact about money and
#: not about the model's own arithmetic.
ANTI_PREDICTIVE_LABEL = "realised return by claimed-edge bucket"


def overconfidence_by_bucket(buckets: Sequence[Mapping]) -> dict:
    """Does the model **over-estimate** more as its claimed edge grows?

    Compares the shortfall — realised minus model-implied — in the highest
    claimed-edge bucket that clears :data:`MINIMUM_BUCKET` against the lowest.
    Reported as a fact about two buckets with both their `n`s beside it, never
    as a significance claim.

    **This is overconfidence, not anti-predictiveness.** A shortfall that widens
    with the claimed edge is the winner's curse and is very nearly guaranteed:
    the model's own selection puts its largest over-estimates in its top bucket.
    Anti-predictiveness is a statement about realised return, and it is measured
    separately by :func:`anti_predictive_return`. Both are reported; neither is
    printed under the other's name.
    """
    usable = [b for b in buckets if b.get("enough") and "gap_to_model" in b]
    if len(usable) < 2:
        return {
            "measures": OVERCONFIDENCE_LABEL,
            "usable_buckets": len(usable),
            "measurable": False,
        }
    lowest, highest = usable[0], usable[-1]
    return {
        "measures": OVERCONFIDENCE_LABEL,
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
        "widens_with_claimed_edge": bool(
            highest["gap_to_model"] < lowest["gap_to_model"]
        ),
        "overconfidence_widens_by": float(
            lowest["gap_to_model"] - highest["gap_to_model"]
        ),
    }


def _return_bucket(bucket: Mapping) -> dict:
    """One bucket's realised return, with everything needed to read it.

    Both intervals travel, never one: the raw 95% interval **and** the interval
    widened by the family-wise correction over `looks` — the experiment
    ledger's cumulative count, which is what `build_record` hands `edge_buckets`
    and what every other interval in this report is corrected by. A bucket that
    carried only the raw interval would be the one place in the report where a
    comparison was made before the search was counted.

    `verdict` is `stats.RoiInterval.verdict()`, which reads the **corrected**
    interval and the sign: `no demonstrated edge` when it spans zero,
    `demonstrated edge` or `demonstrated deficit` when it does not, and `not
    enough evidence` below the declared bet floor. It is carried here so no
    renderer has to re-derive the words, and every printed interval prints it.
    """
    roi = bucket.get("roi") or {}
    raw_low = float(roi.get("low", 0.0))
    raw_high = float(roi.get("high", 0.0))
    return {
        "low": bucket["low"],
        "high": bucket["high"],
        "rows": int(bucket.get("rows", 0)),
        "roi": float(roi.get("value", 0.0)),
        "roi_low": raw_low,
        "roi_high": raw_high,
        # The family-wise correction, from the same `looks` every other
        # interval in this record is corrected by. Absent keys fall back to the
        # raw interval, which is what `RoiInterval.adjusted_low/high` return at
        # one look — never something narrower than what was measured.
        "roi_adjusted_low": float(roi.get("adjusted_low", raw_low)),
        "roi_adjusted_high": float(roi.get("adjusted_high", raw_high)),
        "looks": int(roi.get("looks", 1) or 1),
        "bets": int(roi.get("rows", 0)),
        "clusters": int(roi.get("clusters", 0)),
        "cluster_unit": str(roi.get("cluster_unit") or "game"),
        "verdict": str(roi.get("verdict", "")),
    }


def _negative_return_finding(measured: Sequence[Mapping]) -> dict:
    """What the buckets that cleared the floor say about the SIGN of the return.

    Separate from the across-bucket comparison on purpose. That comparison needs
    two buckets and answers *"does the return fall as the claimed edge rises"*.
    This one needs one bucket and answers a question the comparison never asks:
    *"did the wagers in it lose money, and is that loss demonstrated"*. Until
    2026-09-17 nothing asked the second question, so a run with a single
    measurable bucket returning a demonstrated deficit reported nothing at all
    and gave the sample floor as the reason.

    Three counts and one bucket, all read off the **family-corrected** bounds
    and never off `roi` alone:

    * `negative_point_estimates` — buckets whose return point estimate is below
      zero. On its own this is not a claim: an interval spanning zero around a
      negative point estimate is `stats.NO_DEMONSTRATED_EDGE`, in those words,
      and this count exists so the report can say *"the point estimate is
      negative and the interval spans zero"* rather than picking one of the two.
    * `demonstrated_deficits` — buckets whose corrected interval lies **entirely
      below zero**. That is `stats.DEMONSTRATED_DEFICIT` and it is a different
      statement from no demonstrated edge: worse than nothing, not merely
      indistinguishable from it.
    * `worst_bucket` — the measured bucket with the lowest return, so a reader
      is given the figure and not only the count. Empty when nothing cleared
      the floor, which is the one case where there is genuinely no number.

    **`worst_bucket` is not the bucket `demonstrated_deficits` counts, and a
    renderer may not treat it as one.** The two are selected by different
    quantities — the lowest **point estimate** against the corrected **high
    bound** — so with buckets A (`roi -20%`, corrected `[-45%, +5%]`) and B
    (`roi -5%`, corrected `[-8%, -2%]`), `worst_bucket` is A and the one
    demonstrated deficit is B. Printing A beside a sentence justified by B puts
    a loss on the page with its evidence missing and a figure on the page
    reading `no demonstrated edge`. `deficit_buckets` is therefore carried as
    well: the buckets the count counts, as rows, so the claim and the figures
    under it are the same buckets.
    """
    ordered = sorted(measured, key=lambda b: float(b["roi"]))
    # The corrected high bound, not the raw one and not the point estimate: a
    # deficit that is visible only before the size of the search is counted has
    # not been demonstrated, and the report may not say it has.
    deficits = [dict(b) for b in measured if float(b["roi_adjusted_high"]) < 0.0]
    return {
        "negative_point_estimates": sum(1 for b in measured if float(b["roi"]) < 0.0),
        "demonstrated_deficits": len(deficits),
        "deficit_buckets": deficits,
        "worst_bucket": dict(ordered[0]) if ordered else {},
    }


def anti_predictive_return(buckets: Sequence[Mapping]) -> dict:
    """Does the realised **return** fall as the claimed edge rises?

    This is the anti-predictive statistic. The model's claimed edge is a
    prediction about money, and anti-predictiveness is that prediction running
    backwards: the buckets the model liked most returning less than the buckets
    it liked least. It is read off the realised return `edge_buckets` already
    measures per bucket — a two-way clustered interval over the settled wagers
    in that bucket, with its bet count and the clustering that produced it.

    A bucket enters the COMPARISON only if its return clears
    `stats.MINIMUM_BETS`, because below that floor there is no number.
    `falls_at_the_top` is the direction; `demonstrated` is whether the two
    intervals are **disjoint**, and it is the only key any sentence about the
    shape may lean on. Two overlapping intervals are two buckets that have not
    been shown to differ, and saying so is not the same as saying they are
    equal.

    **`measurable: False` is a statement about the comparison, not about the
    evidence.** Below two usable buckets this function returned four keys and
    dropped everything it had measured, and the report then printed a
    sample-size floor as the reason there was no result — a claim about WHY
    with nothing enforcing that it was the real why. Two things are wrong with
    that and both are now closed:

    * The reason is counted rather than asserted, and **the two unrelated
      reasons a bucket carries no return figure are counted apart**.
      `buckets_below_the_row_floor`, `buckets_with_no_return_column`,
      `buckets_with_no_settled_wager` and `buckets_below_the_bet_floor` are
      disjoint, and they are the reasons a populated bucket is **not** usable —
      so the identity is

      ``below_the_row_floor + no_return_column + no_settled_wager +
      below_the_bet_floor + usable_buckets == populated_buckets``

      and **not** that the four alone exhaust `populated`. They sum to zero on
      the single-usable-bucket fixture this whole change was written for, where
      `populated` is 1. `test_the_unusable_reasons_and_the_usable_count_
      close_against_populated` pins the identity in the form above; a
      reconciliation written from the shorter claim is red on the patch's own
      headline case.

      The split is the second half of that lesson and it cost a second
      defect to learn. `no_return_column` is a fact about the frame's SHAPE —
      no realised return arrived and none could be derived. `no_settled_wager`
      is a fact about the WAGERS — the column is there and this bucket's rows
      are blank in it. One counter carried both, the renderer printed the
      wagers-reason because that is what its sentence said, and the page
      asserted that nothing in those buckets had been graded to a profit on a
      frame where every row had been. Each bucket now stamps its own cause in
      `roi_absent_because` and a bucket that stamps neither is refused.
    * A measurement that WAS available is no longer pre-empted by a floor.
      `measured_buckets` carries every bucket that cleared the floor even when
      there is only one — a comparison needs two, a **sign** needs one — and
      `negative_point_estimates`, `demonstrated_deficits` and `worst_bucket`
      read that sign off the family-corrected bounds. A single bucket whose
      corrected interval lies entirely below zero is a demonstrated deficit,
      which is a stronger statement than *no demonstrated edge* and used to
      have no way of reaching the page at all.

    **`demonstrated` reads the family-corrected intervals**, not the raw ones.
    This comparison is one more look at the same data as every other interval
    in this report, and a difference that survives only before the search is
    counted has not survived. The raw disjointness is kept beside it as
    `demonstrated_before_correction` — labelled, never printed as the answer —
    so a reader can see what the correction cost, and `looks` records how many
    results the correction was taken over.
    """
    usable = [
        b
        for b in buckets
        if b.get("enough") and (b.get("roi") or {}).get("enough_evidence")
    ]
    populated = [b for b in buckets if int(b.get("rows", 0))]
    # **Why each populated bucket is not usable, counted rather than asserted,
    # and the two return-figure reasons counted apart.**
    #
    # The report first gave one reason for the absence of this statistic — that
    # fewer than `stats.MINIMUM_BETS` settled wagers were carried — with
    # nothing checking it was the real one. Counting the reasons fixed that
    # half. It did not fix the other half, because one counter still stood for
    # two unrelated facts: a frame carrying no return column AT ALL, and a
    # bucket whose own wagers are all unsettled. The renderer printed the
    # second, because that is what its sentence said, and the page then told
    # readers that nothing in those buckets had been graded to a profit — on a
    # frame every row of which had been graded, and whose return column had
    # been dropped by a column projection one line before the write. That is a
    # stronger and more foreclosing claim than the floor sentence it replaced,
    # and the page printed nothing a reader could have checked it against.
    #
    # So the cause is stamped by `edge_buckets`, which is the only code that
    # sees the frame's shape and the bucket's rows together, and a bucket that
    # stamps neither is refused rather than defaulted. These four counts are
    # disjoint and are the reasons a populated bucket is NOT usable, so
    # `below_the_row_floor + no_return_column + no_settled_wager +
    # below_the_bet_floor + len(usable) == len(populated)` — they do not
    # exhaust `populated` on their own, and on a run with one usable bucket and
    # nothing else populated all four are zero.
    below_the_row_floor = sum(1 for b in populated if not b.get("enough"))
    no_return_column = 0
    no_settled_wager = 0
    for b in populated:
        if not b.get("enough") or b.get("roi"):
            continue
        reason = b.get("roi_absent_because")
        if reason == ROI_ABSENT_NO_RETURN_COLUMN:
            no_return_column += 1
        elif reason == ROI_ABSENT_NO_SETTLED_WAGER:
            no_settled_wager += 1
        else:
            # **Refused, not guessed.** The cause has to come from the code
            # that built the bucket, which is the only code that saw both the
            # frame's shape and the bucket's rows. A default here would put
            # this report straight back where it was: printing whichever of
            # two unrelated causes the sentence happened to assume.
            raise ForecastSkillError(
                "A populated claimed-edge bucket "
                f"{bucket_label(b.get('low'), b.get('high'))} carries no "
                "`roi` and no `roi_absent_because`, so why it carries no "
                "return figure is not recorded anywhere. The two causes — a "
                "frame with no return column at all, and a bucket whose every "
                "wager is unsettled — are different facts about different "
                "things, and this report has already once printed the second "
                "as a statement about an archive where the first was true. "
                "`edge_buckets` stamps the reason; a bucket built by hand has "
                f"to stamp one of {sorted(ROI_ABSENT_REASONS)!r} too."
            )
    below_the_bet_floor = sum(
        1
        for b in populated
        if b.get("enough")
        and b.get("roi")
        and not (b["roi"] or {}).get("enough_evidence")
    )
    # Every bucket that cleared the floor, measured — whether or not there are
    # two of them. A comparison needs two; a SIGN needs one, and the sign was
    # what the early return threw away.
    measured = [_return_bucket(b) for b in usable]
    negative = _negative_return_finding(measured)
    if len(usable) < 2:
        return {
            "measures": ANTI_PREDICTIVE_LABEL,
            "usable_buckets": len(usable),
            "populated_buckets": len(populated),
            # The ACROSS-BUCKET comparison is what is not measurable. That is
            # not the same as "there is no number": `measured_buckets` may hold
            # one, and a single bucket whose corrected interval lies entirely
            # below zero is a demonstrated deficit that has to be said.
            "measurable": False,
            "measured_buckets": measured,
            "buckets_with_no_return_column": no_return_column,
            "buckets_with_no_settled_wager": no_settled_wager,
            "buckets_below_the_bet_floor": below_the_bet_floor,
            "buckets_below_the_row_floor": below_the_row_floor,
            **negative,
        }
    lowest, highest = _return_bucket(usable[0]), _return_bucket(usable[-1])
    return {
        "measures": ANTI_PREDICTIVE_LABEL,
        "usable_buckets": len(usable),
        "populated_buckets": len(populated),
        "measured_buckets": measured,
        "buckets_with_no_return_column": no_return_column,
        "buckets_with_no_settled_wager": no_settled_wager,
        "buckets_below_the_bet_floor": below_the_bet_floor,
        "buckets_below_the_row_floor": below_the_row_floor,
        **negative,
        # Whether the comparison reaches the top of the claimed-edge range. It
        # usually does not: the top buckets are the thinnest, and a bucket below
        # `stats.MINIMUM_BETS` settled wagers has no return figure at all. A
        # comparison that stops two buckets short is a different comparison, and
        # the report says which buckets it made.
        "spans_the_range": bool(
            populated and usable[-1] is populated[-1] and usable[0] is populated[0]
        ),
        "measurable": True,
        "lowest_bucket": lowest,
        "highest_bucket": highest,
        "falls_at_the_top": bool(highest["roi"] < lowest["roi"]),
        "return_falls_by": float(lowest["roi"] - highest["roi"]),
        # How many results the family-wise correction is taken over. The
        # ledger's cumulative count, threaded down from `build_record` through
        # `edge_buckets`, so this comparison is corrected by the same divisor as
        # the disagreement coefficient it is printed beside.
        "looks": max(lowest["looks"], highest["looks"]),
        # Disjoint intervals, both clustered, both carrying their bet count and
        # both **family-corrected**. A difference whose corrected intervals
        # overlap has not been demonstrated, and a sentence that says "raising
        # the threshold makes it worse" has to rest on this and not on the
        # point estimates and not on the uncorrected interval.
        "demonstrated": bool(
            highest["roi_adjusted_high"] < lowest["roi_adjusted_low"]
        ),
        # The same test before the correction, kept so the report can print
        # what the correction cost. It is never the basis of a claim: a
        # difference visible only at one look is a difference found by looking
        # many times.
        "demonstrated_before_correction": bool(
            highest["roi_high"] < lowest["roi_low"]
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


def measure(
    frame: pd.DataFrame,
    *,
    looks: int = 1,
    label: str = "",
    population: str = ALL_OPINIONS_LABEL,
) -> dict:
    """Everything this report says about one population, as plain data.

    `population` names, in words, which of the two populations the numbers
    belong to — every opinion, or the threshold-selected subset — and travels
    with every cell so no renderer can print a number without its population.
    """
    buckets = edge_buckets(frame, looks=looks)
    return {
        "label": label,
        "population": population,
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
        # Two different quantities under two different names. The first is the
        # winner's curse; the second is the one the word "anti-predictive"
        # means.
        "overconfidence": overconfidence_by_bucket(buckets),
        "anti_predictive_return": anti_predictive_return(buckets),
    }


def _by_tier(frame: pd.DataFrame, *, looks: int, population: str) -> list[dict]:
    if frame.empty:
        return []
    return [
        measure(
            frame[frame["tier"].astype(str) == tier],
            looks=looks,
            label=tier,
            population=population,
        )
        for tier in _tiers_in(frame)
    ]


def selected_mask(frame: pd.DataFrame) -> pd.Series:
    """The rows :data:`SELECTED_COLUMN` marks, read strictly.

    A CSV round-trip hands the column back as `bool`, as the strings `True` /
    `False`, or as `1` / `0`, and any of those must read the same way. Anything
    else — a blank, a `NaN`, a word — is **not** selected: an unreadable flag is
    not a bet, for the same reason a missing probability is not a probability of
    zero.
    """
    if frame.empty or SELECTED_COLUMN not in frame.columns:
        return pd.Series(False, index=frame.index, dtype=bool)
    raw = frame[SELECTED_COLUMN]
    if raw.dtype == bool:
        return raw.astype(bool)
    return raw.astype(str).str.strip().str.lower().isin({"true", "1", "1.0"})


def _selected_section(population: pd.DataFrame, graded: pd.DataFrame, *, looks: int) -> dict:
    """The threshold-selected subset, measured apart and named as what it is.

    Measured over the SAME scorable population the primary fit uses, cut by the
    `selected` flag the backtest stamped, so the two populations differ by
    exactly that flag and nothing else. Absent the column, the subset is
    reported as not supplied — never inferred from the edge, because the whole
    point of carrying the flag is that the backtest's predicate and this
    module's must be one predicate.
    """
    available = bool(not graded.empty and SELECTED_COLUMN in graded.columns)
    if not available:
        return {
            "available": False,
            "label": SELECTED_LABEL,
            "role": SELECTED_ROLE,
            "column": SELECTED_COLUMN,
            "rows": 0,
            "games": 0,
            "days": 0,
            "reason": (
                f"the frame carries no `{SELECTED_COLUMN}` column, so which "
                "rows were bets is not recorded and the subset is not measured"
            ),
            "by_tier": [],
            "pooled": measure(
                population.iloc[0:0], looks=looks, label="every tier pooled",
                population=SELECTED_LABEL,
            ),
        }
    subset = population[selected_mask(population)] if not population.empty else population
    return {
        "available": True,
        "label": SELECTED_LABEL,
        "role": SELECTED_ROLE,
        "column": SELECTED_COLUMN,
        "rows": int(len(subset)),
        "games": int(subset["event_id"].nunique()) if not subset.empty else 0,
        "days": int(subset["slate_date"].nunique()) if not subset.empty else 0,
        "reason": "",
        "by_tier": _by_tier(subset, looks=looks, population=SELECTED_LABEL),
        "pooled": measure(
            subset, looks=looks, label="every tier pooled", population=SELECTED_LABEL
        ),
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
    regression on the variable whose usefulness is the question. When the frame
    carries :data:`SELECTED_COLUMN`, the rows it marks are ALSO measured, apart,
    as the winner's-curse comparison — beside the whole and never instead of it.
    """

    graded: pd.DataFrame = field(default_factory=pd.DataFrame)
    source: str = ""
    season_label: str = ""
    snapshot_phase: str = ""
    pair_scope: str = PAIR_SCOPES[0]
    edge_threshold: float = BET_EDGE_THRESHOLD
    #: The frame-builder's unpairable census, as written beside the frame, or
    #: `None` when the frame came from somewhere that writes no census. It is
    #: the ONLY way this module can know that rows were excluded upstream, and
    #: the report says "not supplied" rather than "none" when it is absent —
    #: the two are different claims and only one of them is a measurement.
    unpairable: Mapping | None = None


def _excluded_unpairable(census: Mapping | None) -> dict:
    """The frame-builder's census, as the record carries it.

    `available` is False when no census was supplied, and the report then says
    so in words. It is never defaulted to zero: "no rows were excluded" and
    "nobody counted" are different claims, and printing the first when the
    second is true is the whole class of error this file argues against.

    **All THREE terms are carried, and `accounted` is their sum.**
    `build_skill_frame.UnpairableCensus` states one identity — `supplied =
    paired + unpairable + no_pair_key` — and until 2026-09-17 this function
    copied two of its terms and dropped `no_pair_key` on the floor. The
    consequence was not a missing column: `_excluded_lines` already printed a
    `no_pair_key` figure, read it off this dict with a `0` default, and so
    printed a hard zero for a term nobody had copied. A reader was shown three
    numbers that added up, one of which was invented by a default — which is
    the same defect as deriving an accounting bucket by subtraction, wearing
    the shape of a census that balances. `accounted` is carried beside them so
    the sum a reader is asked to check is the one this module computed from the
    terms it holds, not one the reader has to do in their head.
    """
    if not census:
        return {
            "label": UNPAIRABLE_LABEL,
            "role": UNPAIRABLE_ROLE,
            "available": False,
            "rows": 0,
            "supplied": 0,
            "paired": 0,
            "no_pair_key": 0,
            "accounted": 0,
            "share": 0.0,
            "selected_rows": 0,
            "reason": "",
            "by_market": {},
            "by_book": {},
            "reconciles": False,
        }
    supplied = int(census.get("supplied", 0))
    rows = int(census.get("unpairable", 0))
    paired = int(census.get("paired", 0))
    no_pair_key = int(census.get("no_pair_key", 0))
    return {
        "label": UNPAIRABLE_LABEL,
        "role": UNPAIRABLE_ROLE,
        "available": True,
        "rows": rows,
        "supplied": supplied,
        "paired": paired,
        # The third term. A graded row whose selection this lab forms no pair
        # key for did not pair and was not excluded — it is its own bucket,
        # and it stays in the frame.
        "no_pair_key": no_pair_key,
        # The sum of the three, so the identity the reader is shown is closed
        # by arithmetic this module did rather than by arithmetic it assumes.
        "accounted": paired + rows + no_pair_key,
        "share": float(census.get("share", 0.0)),
        "selected_rows": int(census.get("unpairable_selected", 0)),
        "reason": str(census.get("reason", "")),
        "by_market": dict(census.get("by_market") or {}),
        "by_book": dict(census.get("by_book") or {}),
        "reconciles": bool(census.get("reconciles", False)),
    }


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

    **A player wager may not be graded here until the store's wager census has
    reconciled.** This function is design section 10's own metric — the de-vig,
    the log loss, the Brier and the clustered intervals — and `player` is
    already an OPTIONAL column of the frame it grades, casefolded in the de-vig
    pair scope, so a frame of player props handed to it needs no new code to be
    scored. Section 10 gates that on reconciling the store's wager count
    (261,870 wagers under the book's own spelling of the athlete against 257,474
    under a casefold, a 4,396 difference that has to be named wager by wager)
    and says "the run stops until it reconciles". The guard is one vectorised
    prefix test on a frame already in memory, it finds nothing on every
    team-market run this lab has ever made, and it fails CLOSED: no receipt
    means refused.
    """
    # The gate runs first (its own test requires it to be the first
    # statement: a gate after the de-vig is a gate on the report, not on the
    # run). The refusal filter runs immediately after, so a receipt never lets
    # a refused market be scored. See `player_census.player_markets_in`. This module
    # never called the refusal filter, so when the gate stopped counting
    # refused markets a `player_double_double` frame was scored here — Brier,
    # de-vigged advantage and a verdict — for a market this lab refuses to
    # price at all. Measured on a 16-row frame with no receipt.
    player_census.guard_graded_frame(inputs.graded, what="forecast_skill.build_record")
    graded = _PR.without_markets_refused_by_name(inputs.graded)
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

    tiers = _by_tier(population, looks=looks, population=ALL_OPINIONS_LABEL)
    # The pooled figure must equal the tiers plus whatever could not be placed
    # in one. A row whose tier is missing belongs to no tier section, and a
    # pooled number quietly larger than the sum of its tiers is how a Division I
    # headline reappears after being forbidden. Counted and printed.
    tiered_rows = sum(int(t["rows"]) for t in tiers)
    selected = _selected_section(population, graded, looks=looks)
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
        # The two populations, side by side, each with its count. `by_tier`,
        # `pooled` and `raw_market_fit` are the FIRST — every opinion, the skill
        # measure. `selected` is the second and is labelled as what it is.
        "population_label": ALL_OPINIONS_LABEL,
        "population_role": ALL_OPINIONS_ROLE,
        "populations": {
            "all_opinions": {
                "label": ALL_OPINIONS_LABEL,
                "role": ALL_OPINIONS_ROLE,
                "rows": int(len(population)),
                "games": int(population["event_id"].nunique()) if not population.empty else 0,
                "days": int(population["slate_date"].nunique()) if not population.empty else 0,
            },
            "selected": {
                "label": SELECTED_LABEL,
                "role": SELECTED_ROLE,
                "available": bool(selected["available"]),
                "rows": int(selected["rows"]),
                "games": int(selected["games"]),
                "days": int(selected["days"]),
            },
            # Neither population, and that is the point: these rows were
            # dropped before this module saw the frame, so the frame's length
            # is not the graded set and only this census can say so.
            "excluded_unpairable": _excluded_unpairable(inputs.unpairable),
        },
        "by_tier": tiers,
        "rows_without_a_tier": int(len(population)) - tiered_rows,
        "pooled": measure(
            population, looks=looks, label="every tier pooled", population=ALL_OPINIONS_LABEL
        ),
        "selected": selected,
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


def _population_line(measured: Mapping) -> str:
    """Which population a cell's numbers belong to, in words, with its size."""
    population = str(measured.get("population") or ALL_OPINIONS_LABEL)
    role = SELECTED_ROLE if population == SELECTED_LABEL else ALL_OPINIONS_ROLE
    return (
        f"*Population: **{population}** — {role}; "
        f"{int(measured.get('rows', 0)):,} scorable wagers in "
        f"{int(measured.get('games', 0)):,} games over "
        f"{int(measured.get('days', 0)):,} days.*"
    )


def _fit_section(measured: Mapping) -> list[str]:
    """One population's regression, as table rows plus the sentence that reads it."""
    lines: list[str] = []
    add = lines.append
    add(_population_line(measured))
    add("")
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
    # The realised-return column is four cells, not one. A return, its sample
    # size and clustering, the raw interval, the interval widened by the
    # family-wise correction, and the verdict those words are reserved for —
    # the same shape `price_backtest`'s ROI tables use, for the same reason. An
    # interval printed with no verdict beside it is a verdict the reader
    # supplies, and until 2026-09-05 this column printed `-14.3% [-23.9%,
    # -4.6%]` and let the reader call it a demonstrated deficit, which at this
    # run's look count it is not.
    add(
        "| Claimed edge | Wagers | Games | Model said | De-vigged price said | "
        "Actually won | Realised − model | Realised return | 95% interval | "
        "Family-corrected | Verdict |"
    )
    add("|:---|---:|---:|---:|---:|:---|---:|---:|:---|:---|:---|")
    for bucket in buckets:
        label = bucket_label(bucket["low"], bucket["high"])
        n = int(bucket.get("rows", 0))
        if not n:
            add(f"| {label} | 0 | 0 | — | — | — | — | — | — | — | — |")
            continue
        if not bucket.get("enough"):
            add(
                f"| {label} | {n:,} | {bucket['games']:,} | — | — | — | — | — "
                "| — | — | — |"
            )
            continue
        roi = bucket.get("roi") or {}
        return_cell, interval_cell, corrected_cell = "—", "—", "—"
        verdict_cell = "—" if roi else _roi_absent_cell(bucket)
        if roi and roi.get("enough_evidence"):
            looks = int(roi.get("looks", 1) or 1)
            return_cell = (
                f"{roi['value']:+.1%} over {roi['rows']:,} settled, "
                f"{roi['clusters']:,} {roi.get('cluster_unit') or 'game'}s"
            )
            interval_cell = f"[{roi['low']:+.1%}, {roi['high']:+.1%}]"
            corrected_cell = (
                f"[{roi['adjusted_low']:+.1%}, {roi['adjusted_high']:+.1%}] "
                f"across {looks:,} look{'' if looks == 1 else 's'}"
            )
            verdict_cell = str(roi.get("verdict") or "")
        elif roi:
            # Below the declared bet floor there is no return figure, and the
            # verdict says so in the words `RoiInterval.verdict()` uses rather
            # than leaving the cell blank for a reader to fill in.
            return_cell = f"— ({roi['rows']:,} settled)"
            verdict_cell = str(roi.get("verdict") or "")
        add(
            f"| {label} | {n:,} | {bucket['games']:,} | "
            f"{bucket['model_implied']:.1%} | {bucket['market_implied']:.1%} | "
            f"{bucket['realised']:.1%} [{bucket['wilson_low']:.1%}, "
            f"{bucket['wilson_high']:.1%}] | "
            f"{bucket['gap_to_model'] * 100:+.1f} pp | {return_cell} | "
            f"{interval_cell} | {corrected_cell} | {verdict_cell} |"
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
    lines.extend(_overconfidence_paragraph(measured))
    lines.extend(_anti_predictive_paragraph(measured))
    return lines


def _overconfidence_paragraph(measured: Mapping) -> list[str]:
    """Overconfidence by claimed-edge bucket, under its own name.

    The section this paragraph closes measures **realised minus model-implied**
    across buckets of claimed edge. That is the model's over-estimate, and an
    over-estimate that widens with the claimed edge is the winner's curse — the
    model's own selection puts its largest over-estimates in its top bucket.
    Until 2026-09-05 this paragraph called that anti-predictiveness and used it
    to say raising the threshold is the wrong response. Anti-predictiveness is a
    statement about realised return; it now has its own paragraph below, and
    that is where the threshold sentence lives.
    """
    lines: list[str] = []
    add = lines.append
    shape = measured.get("overconfidence") or {}
    if not shape.get("measurable"):
        return lines
    low = shape["lowest_bucket"]
    high = shape["highest_bucket"]
    if shape.get("widens_with_claimed_edge"):
        add(
            "**The model over-estimates more where it claims more.** The "
            "shortfall against model-implied is "
            f"{low['gap_to_model'] * 100:+.1f} pp in the "
            f"{bucket_label(low['low'], low['high'])} bucket "
            f"({low['rows']:,} wagers) and "
            f"{high['gap_to_model'] * 100:+.1f} pp in the "
            f"{bucket_label(high['low'], high['high'])} bucket "
            f"({high['rows']:,} wagers) — it widens by "
            f"{shape['overconfidence_widens_by'] * 100:.1f} pp across the "
            "range. That is **overconfidence**, which is what this column "
            "measures, and it is the winner's curse: the biggest claimed edges "
            "are the biggest over-estimates by construction. It is not by "
            "itself anti-predictiveness — that is a claim about realised "
            "return, and it is measured in its own right below."
        )
    else:
        add(
            "The shortfall against model-implied does **not** widen with the "
            f"claimed edge: {low['gap_to_model'] * 100:+.1f} pp in the "
            f"{bucket_label(low['low'], low['high'])} bucket "
            f"({low['rows']:,} wagers) against "
            f"{high['gap_to_model'] * 100:+.1f} pp in the "
            f"{bucket_label(high['low'], high['high'])} bucket "
            f"({high['rows']:,} wagers). That is an absence of overconfidence "
            "and not evidence of skill; the disagreement coefficient is the "
            "test."
        )
    add("")
    return lines


def _return_cell(bucket: Mapping) -> str:
    """One bucket's return: both intervals, labelled, and the verdict.

    Raw and family-corrected are printed side by side and named apart, because
    the corrected one is what any claim rests on and the raw one is what the
    correction was applied to. The verdict is `stats.RoiInterval.verdict()`
    read off the corrected interval, so a bucket whose corrected interval spans
    zero reads `stats.NO_DEMONSTRATED_EDGE` in exactly those words — a printed
    interval with no verdict beside it is the thing a reader supplies a verdict
    for.

    Module-level rather than nested inside the paragraph that used to own it,
    because the same cell is now printed from two places: the across-bucket
    comparison, and the single-bucket sign statement that the comparison's
    early return used to suppress. Two copies of this formatting would be two
    ways of printing one figure.
    """
    return (
        f"{bucket['roi']:+.1%} over {bucket['bets']:,} settled wagers "
        f"across {bucket['clusters']:,} {bucket['cluster_unit']}s, 95% "
        f"interval [{bucket['roi_low']:+.1%}, {bucket['roi_high']:+.1%}], "
        f"family-corrected [{bucket['roi_adjusted_low']:+.1%}, "
        f"{bucket['roi_adjusted_high']:+.1%}] across "
        f"{bucket['looks']:,} look{'' if bucket['looks'] == 1 else 's'} — "
        f"{bucket['verdict']}"
    )


def _negative_return_lines(
    shape: Mapping, *, printed: Sequence[Mapping] = ()
) -> list[str]:
    """The SIGN of what was measured, said in plain words, or nothing.

    **A negative result is a result.** The across-bucket comparison answers
    *"does the return fall as the claimed edge rises"* and needs two buckets;
    it returned early below two and the report then printed a sample-size
    floor, which reads as *we could not see anything*. It is a different
    sentence from *we saw the model lose money*, and until 2026-09-17 the
    second one had no way of being printed at all: `anti_predictive_return`
    dropped every measured bucket on the floor-return path, so no renderer
    could reach the figure even when the figure existed.

    Three outcomes, and the vocabulary is not interchangeable between them:

    * corrected interval entirely below zero -> `stats.DEMONSTRATED_DEFICIT`.
      Worse than no edge, and it is never softened into no-demonstrated-edge.
    * point estimate below zero, corrected interval spanning it ->
      `stats.NO_DEMONSTRATED_EDGE` **in those words**, with the negative point
      estimate stated beside it rather than instead of it. Both are true; the
      report says both.
    * neither -> nothing. There is no negative finding to report and inventing
      one would be the same defect in the other direction.

    **It reads every measured bucket, and it is called on BOTH paths.** It used
    to read `worst_bucket` alone — the bucket with the lowest point estimate —
    and `worst_bucket` is not the bucket a deficit is counted off: that is
    selected by the corrected high bound. On buckets A (`-20%`, corrected
    `[-45%, +5%]`) and B (`-5%`, corrected `[-8%, -2%]`) the old reading named
    A, whose interval spans zero, and printed nothing about B. And it was not
    called at all on the compared path, on the justification that *"the sign is
    on the page there already, in the verdict beside each cell"* — true of two
    cells, and that path prints exactly two however many buckets were measured.
    Three usable buckets with a demonstrated deficit in the middle one reached
    no sentence and no figure on this page at all.

    `printed` is the buckets the caller has already put on the page. A bucket
    this function needs and the caller has not printed gets its cell here, so
    the sentence never refers to *"the interval printed above"* when there is
    none — and a bucket already on the page is not printed twice, because an
    interval printed twice is two chances for a reader to quote the one without
    its qualifier.
    """
    measured = [b for b in (shape.get("measured_buckets") or []) if b]
    if not measured:
        return []
    already = {(b["low"], b["high"]) for b in printed}

    def cells(buckets: Sequence[Mapping]) -> list[str]:
        return [
            f"The {bucket_label(b['low'], b['high'])} bucket returned "
            f"{_return_cell(b)}."
            for b in buckets
            if (b["low"], b["high"]) not in already
        ]

    deficits = [b for b in measured if float(b["roi_adjusted_high"]) < 0.0]
    if deficits:
        named = ", ".join(bucket_label(b["low"], b["high"]) for b in deficits)
        plural = len(deficits) != 1
        return cells(deficits) + [
            f"**The wagers in the {named} claimed-edge "
            + ("buckets" if plural else "bucket")
            + " lost money, and the loss survives the correction.** The "
            "family-corrected "
            + ("intervals" if plural else "interval")
            + " printed above "
            + ("lie" if plural else "lies")
            + " entirely below zero, so "
            + ("each of those buckets is" if plural else "that bucket is")
            + f" a **{S.DEMONSTRATED_DEFICIT}**: the model did worse than no "
            "edge in "
            + ("them" if plural else "it")
            + ", which is a stronger statement than failing to demonstrate "
            "one, and it is a statement about the money rather than about the "
            "size of the sample."
        ]
    negative = [b for b in measured if float(b["roi"]) < 0.0]
    if negative:
        worst = min(negative, key=lambda b: float(b["roi"]))
        label = bucket_label(worst["low"], worst["high"])
        return cells([worst]) + [
            f"**The {label} claimed-edge bucket's return is below zero at the "
            "point estimate.** Both things are true and both are said: the "
            "point estimate sits on the losing side, and the family-corrected "
            "interval printed above includes zero, so the verdict beside it "
            "is the one that stands. A negative number under an interval that "
            "spans zero is not evidence of a loss; it is also not evidence of "
            "anything else."
        ]
    return []


def _unmeasured_anti_predictive_lines(shape: Mapping) -> list[str]:
    """Why the across-bucket comparison was not made, counted off the buckets.

    **This paragraph has now been the site of two findings and the second was
    worse than the first.**

    It began as one sentence: *"Fewer than two claimed-edge buckets carry 200
    settled wagers, which is the floor declared in advance, and below it there
    is no return figure to compare."* That is a claim about WHY there is no
    result with nothing enforcing that it was the real why — and it was
    checkable, because the bucket sizes were printed a few lines above it.
    A reader checked it, and it was wrong.

    Counting the reasons replaced it with a sentence that was not checkable:
    *"no claimed-edge bucket ... carries a readable return ... they carry no
    settled wager at all — not a thin sample but an absent one: nothing in them
    has been graded to a profit."* That is an assertion about what the ARCHIVE
    holds, and it was false. The frame held 270,504 rows and every one of them
    was settled — 263,367 won and 263,367 lost across the full graded export,
    with a price on every row. What was missing was the return COLUMN, dropped
    by the export's column projection one line before the write. The page
    forecloses the question, and the only thing contradicting it is something
    the page never prints.

    So the two causes are now counted apart and this paragraph prints the one
    it actually has. `buckets_with_no_return_column` is a fact about the shape
    of the frame handed to this report and says nothing about any wager;
    `buckets_with_no_settled_wager` is a fact about the wagers in a bucket.
    With `buckets_below_the_row_floor`, `buckets_below_the_bet_floor` and the
    usable count they are disjoint and close against `populated` — they do
    **not** exhaust it on their own, and this paragraph prints the usable ones
    itself, which is the fifth term. So the sentence cannot say something the
    counts do not, and it can no longer say the wrong one of two things.

    And when a bucket DID clear the floor — one is not two, so no comparison
    is possible — its return is printed with its verdict, and
    :func:`_negative_return_lines` says what its sign means. A floor may not
    pre-empt a measurement that was available.
    """
    populated = int(shape.get("populated_buckets", 0))
    measured = shape.get("measured_buckets") or []
    # **Counted off the buckets this paragraph is about to print, not off
    # `usable_buckets`.** The two agree in any record this module wrote, and
    # they do not in a record written before version 5: that shape carries the
    # count and not the buckets, and keying the sentence on the count would
    # promise a figure below that nothing can print. A sentence whose subject
    # is a number rather than the thing the number counts is the same defect
    # as the floor sentence this paragraph exists to replace.
    usable = len(measured)
    lines: list[str] = []
    add = lines.append

    def carry(count: int) -> str:
        """Verb agreement. These counts are routinely one, and *"1 carry"*
        reads like a typo in a document whose whole argument is care."""
        return "carries" if count == 1 else "carry"

    if usable:
        add(
            "**Anti-predictiveness — the realised return falling as the "
            "claimed edge rises — is not compared across buckets here.** A "
            f"comparison needs two, and {usable:,} of {populated:,} populated "
            f"claimed-edge buckets {carry(usable)} a readable return. "
            "Whatever cleared the floor is measured below rather than left "
            "under the floor sentence."
        )
    else:
        add(
            "**Anti-predictiveness — the realised return falling as the "
            "claimed edge rises — is not measured here.** No claimed-edge "
            f"bucket of the {populated:,} with any wager in them carries a "
            "readable return, so there is nothing to compare and nothing to "
            "read a sign off."
        )
    # **Refused, not defaulted.** A `.get(..., 0)` here is how this paragraph
    # came to print one cause while the other was the true one: a record
    # written before the split carries a single conflated counter, and a zero
    # for the two that replaced it would silently drop the reason entirely.
    # There is no honest rendering of a silence whose cause this record does
    # not hold.
    # Scoped to a shape that IS an anti-predictiveness block. An empty mapping
    # is a record carrying no block at all — a different and older failure, the
    # one `record_version` and `why_the_model.FORECAST_RECORD_VERSION` already
    # stand over — and refusing it here would turn every pre-split record into
    # an exception instead of the named silence those guards produce.
    missing = [
        key
        for key in ("buckets_with_no_return_column", "buckets_with_no_settled_wager")
        if key not in shape
    ] if shape else []
    if missing:
        raise ForecastSkillError(
            "This anti-predictiveness shape carries no "
            + " and no ".join(f"`{key}`" for key in missing)
            + f". `read_record` writes version {RECORD_VERSION}, in which the "
            "two reasons a bucket carries no return figure — a frame with no "
            "return column, and a bucket whose wagers are all unsettled — are "
            "counted apart. An older record carries one counter standing for "
            "both, and printing either sentence from it would state a cause "
            "nobody separated. Re-run the regression rather than "
            "re-rendering."
        )
    # The `0` is reachable only for an empty shape — a record with no block at
    # all, whose populated count is zero too, so no sentence is printed from
    # it. Every real block is guaranteed both keys by the refusal above.
    no_return_column = int(shape.get("buckets_with_no_return_column", 0))
    no_settled_wager = int(shape.get("buckets_with_no_settled_wager", 0))
    below_the_bet_floor = int(shape.get("buckets_below_the_bet_floor", 0))
    below_the_row_floor = int(shape.get("buckets_below_the_row_floor", 0))
    if no_return_column:
        add(
            f"Of those, {no_return_column:,} sit in a frame that carries no "
            "realised-return column at all and none that could be derived "
            "from it — no `profit_units`, and not both of `outcome` and "
            "`american_odds` to compute one from. **That is a fact about the "
            "shape of the frame handed to this report, and it is not a "
            "statement about whether those wagers settled.** Nothing here says "
            "they did not. The frame's producer is "
            "`scripts/run_price_backtest.py --write-graded`, and a frame in "
            "this shape means the export is to be re-run, not that the archive "
            "holds nothing."
        )
    if no_settled_wager:
        add(
            f"Of those, {no_settled_wager:,} {carry(no_settled_wager)} no "
            "settled wager at all — not a thin sample but an absent one: "
            "the frame carries a realised-return column and every row in these "
            "buckets is blank in it, so no return was computed and no floor "
            "was reached or missed. That is a fact about what the frame holds "
            "and it is **not** a statement that the model was measured and "
            "found wanting, nor that it was measured and found harmless."
        )
    if below_the_bet_floor:
        add(
            f"{below_the_bet_floor:,} {carry(below_the_bet_floor)} a settled "
            f"wager but fewer than the {S.MINIMUM_BETS:,} settled wagers "
            "declared in advance as the floor, which is below the point where "
            "a return figure is printed at all."
        )
    if below_the_row_floor:
        add(
            f"{below_the_row_floor:,} hold fewer than {MINIMUM_BUCKET:,} "
            "wagers in total, which is the row floor this table prints no "
            "frequency below."
        )
    for bucket in measured:
        add(
            f"The {bucket_label(bucket['low'], bucket['high'])} bucket "
            f"returned {_return_cell(bucket)}."
        )
    lines.extend(_negative_return_lines(shape, printed=measured))
    add(
        "The overconfidence column above is a different quantity and cannot "
        "stand in for this one."
    )
    return lines


def _anti_predictive_paragraph(measured: Mapping) -> list[str]:
    """The statistic the word *anti-predictive* actually names: realised return.

    Realised return in the highest claimed-edge bucket against the lowest, each
    with its settled bet count, the clustering that produced its interval, the
    raw 95% interval, the **family-corrected** interval beside it, and the
    verdict those words are reserved for — a bucket whose corrected interval
    spans zero reads `stats.NO_DEMONSTRATED_EDGE`. The sentence *"raising the
    threshold makes it worse"* is emitted only when the two **corrected**
    intervals are disjoint, because that sentence is a claim about money, the
    point estimates alone do not carry it, and an interval read before the size
    of the search is counted is not the interval the claim rests on.

    **When there are not two buckets to compare, this delegates rather than
    stopping.** :func:`_unmeasured_anti_predictive_lines` states the reason the
    buckets themselves give, prints whatever single bucket cleared the floor,
    and says what its sign means. That path used to be one sentence naming a
    sample floor, which is a claim about why there is no result with nothing
    enforcing that it is the real reason.
    """
    lines: list[str] = []
    add = lines.append
    shape = measured.get("anti_predictive_return") or {}
    if not shape.get("measurable"):
        lines.extend(_unmeasured_anti_predictive_lines(shape))
        add("")
        return lines
    low = shape["lowest_bucket"]
    high = shape["highest_bucket"]
    cell = _return_cell

    head = (
        "**Realised return by claimed edge — the anti-predictive statistic.** "
        f"The {bucket_label(low['low'], low['high'])} bucket returned "
        f"{cell(low)}; the {bucket_label(high['low'], high['high'])} bucket "
        f"returned {cell(high)}."
    )
    if not shape.get("spans_the_range"):
        head += (
            f" Those are the lowest and highest of {shape['usable_buckets']:,} "
            f"claimed-edge buckets (of {shape['populated_buckets']:,} with any "
            f"wager in them) carrying {S.MINIMUM_BETS:,} settled wagers or "
            "more, so this comparison does **not** reach the ends of the "
            "claimed-edge range."
        )
    if shape.get("falls_at_the_top") and shape.get("demonstrated"):
        add(
            head
            + " The two **family-corrected** intervals do not overlap across "
            f"{shape['looks']:,} look"
            + ("" if shape["looks"] == 1 else "s")
            + ", so the return **falls** by "
            f"{shape['return_falls_by'] * 100:.1f} pp across the range on the "
            "evidence of this run. That is anti-predictiveness measured on "
            "money, and it is what makes raising the edge threshold the wrong "
            "response: a higher threshold admits only the buckets that "
            "returned less."
        )
    elif shape.get("falls_at_the_top"):
        add(
            head
            + " The point estimate falls by "
            f"{shape['return_falls_by'] * 100:.1f} pp across the range, but "
            "the two family-corrected intervals overlap across "
            f"{shape['looks']:,} look"
            + ("" if shape["looks"] == 1 else "s")
            + ", so **the fall is not demonstrated**"
            + (
                " — the raw intervals were disjoint and the correction for the "
                "size of the search is what closed the gap"
                if shape.get("demonstrated_before_correction")
                else " and the raw intervals overlap too"
            )
            + ". No sentence here says raising the threshold makes it worse; "
            "the disagreement coefficient is the test that can say so, and the "
            "overconfidence column above measures a different quantity."
        )
    else:
        add(
            head
            + " The return does not fall across the range, so this run shows "
            "no anti-predictiveness in realised return. That is not evidence "
            "of skill — the disagreement coefficient is the test — and it does "
            "not contradict the overconfidence column above, which measures a "
            "different quantity."
        )
    # **The sign, on this path too.** The paragraph above prints the lowest and
    # the highest bucket and no others, so with three or more usable buckets a
    # demonstrated deficit in a middle one reached neither a figure nor a
    # sentence. `printed` is the two cells the head already carries, so nothing
    # is printed twice and anything the claim needs and the head does not carry
    # is printed here.
    lines.extend(_negative_return_lines(shape, printed=(low, high)))
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
            f"This run's pooled disagreement coefficient over "
            f"**{ALL_OPINIONS_LABEL}** is "
            f"{disagreement['estimate']:+.3f} "
            f"[{disagreement['low']:+.3f}, {disagreement['high']:+.3f}] over "
            f"{disagreement['rows']:,} wagers across "
            f"{disagreement['clusters']:,} {disagreement['cluster_unit']}s — "
            f"{disagreement['verdict']}. The **realised return** column of the "
            "claimed-edge buckets above measures the same thing bucket by "
            "bucket; the algebra and the table are printed together because "
            "either alone is arguable. The realised-minus-model column beside "
            "it is overconfidence, which is a different quantity and does not "
            "support this section's conclusion on its own."
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


def _excluded_lines(excluded: Mapping) -> list[str]:
    """What the frame does not contain, stated where the populations are stated.

    A reader who is told two population counts and nothing else will take the
    larger of them for the graded set. It is not: `build_skill_frame.py`
    excludes every graded wager whose own book hung one side only, because a
    one-sided quote holds no vig and no fair price can be taken from it. The
    count is small and the exclusion is correct; **saying nothing about it** is
    the part that would not be.

    The census this reads has THREE terms — `supplied = paired + unpairable +
    no_pair_key` — and this paragraph names all three and then prints the sum
    beside the number it is supposed to equal. It named two until 2026-09-05,
    which made `supplied - paired` read as the exclusion when a third term was
    sitting between them; and from then until 2026-09-17 it *printed* three
    while `_excluded_unpairable` copied two, so the third figure on the page
    was the `0` of a `.get` default rather than a count. A zero that arrives by
    default is indistinguishable on the page from a zero that was measured,
    which is why the term is now read off a key that is always written and the
    identity is closed in front of the reader rather than left for them to do.
    """
    if not excluded.get("available"):
        return [UNPAIRABLE_NOT_SUPPLIED, ""]
    rows = int(excluded.get("rows", 0))
    supplied = int(excluded.get("supplied", 0))
    paired = int(excluded.get("paired", 0))
    missing = [key for key in ("no_pair_key", "accounted") if key not in excluded]
    if missing:
        # **Refused, not defaulted.** This is the defect itself, arriving from
        # the other direction: a record written before version 5 carries two of
        # the census's three terms, and a `.get(..., 0)` here would print a
        # hard zero for the third and a total that balances because one of its
        # addends was invented. There is no honest rendering of a census whose
        # terms this record does not hold, so the report says so and stops
        # rather than publishing arithmetic nobody did.
        raise ForecastSkillError(
            "The unpairable census in this record carries no "
            + " and no ".join(f"`{key}`" for key in missing)
            + f". `read_record` writes version {RECORD_VERSION}, in which the "
            "census carries all three of its terms and their sum; an older "
            "record carries two, and printing a zero for the third would say "
            "that no graded wager lacked a pair key when nobody counted. "
            "Re-run the regression rather than re-rendering."
        )
    no_pair_key = int(excluded["no_pair_key"])
    accounted = int(excluded["accounted"])
    reason = str(excluded.get("reason") or UNPAIRABLE_ROLE)
    paragraphs: list[str] = []
    if not excluded.get("reconciles"):
        paragraphs.append(
            "**The frame-builder's census does not reconcile** — its own "
            "terms do not add up to the wagers it was handed, so nothing in "
            "this subsection can be read as complete."
        )
    if not rows and not no_pair_key:
        paragraphs.append(
            f"**Nothing was excluded before this frame was built.** All "
            f"{supplied:,} graded wagers found a complement at their own book, "
            "so the frame is the whole graded set."
        )
    elif not rows:
        # Nothing excluded, but the third term is not zero. "All of them found
        # a complement" would be false of exactly these rows: they never went
        # looking for one, because this lab forms no pair key for what they
        # selected. They are in the frame and they are not paired, and a
        # sentence that folds them into `paired` is the same error the
        # frame-builder's own census docstring was written to close.
        paragraphs.append(
            f"**Nothing was excluded before this frame was built.** Of the "
            f"{supplied:,} graded wagers the frame was built from, {paired:,} "
            f"paired with the other side of their own book's quote and "
            f"{no_pair_key:,} carried a selection this lab forms no pair key "
            "for and were kept unpaired. None was dropped, so the frame is the "
            "whole graded set — but it is not wholly a paired one."
        )
    else:
        paragraphs.append(
            f"**{rows:,} graded wager(s) are in neither population above.** "
            f"The frame was built from {supplied:,} graded wagers: {paired:,} "
            f"paired with the other side of their own book's quote, "
            f"{no_pair_key:,} carried a selection this "
            f"lab forms no pair key for and were kept unpaired, and {rows:,} "
            f"({float(excluded.get('share', 0.0)):.6%}) were excluded because "
            f"{reason}. Excluding them is the only honest arithmetic available "
            "— there is no hold in a one-sided quote to de-vig — but every "
            "count above is therefore a count of a **subset** of the graded "
            "set, not of the graded set itself."
        )
        where = []
        for what, key in (("market", "by_market"), ("book", "by_book")):
            tally = excluded.get(key) or {}
            if tally:
                named = ", ".join(
                    f"{name} ({int(count):,})"
                    for name, count in sorted(
                        tally.items(), key=lambda kv: (-kv[1], kv[0])
                    )
                )
                where.append(f"by {what}: {named}")
        if where:
            paragraphs.append("They fell " + "; ".join(where) + ".")
        selected_rows = int(excluded.get("selected_rows", 0))
        if selected_rows:
            paragraphs.append(
                f"Of the {rows:,} excluded, {selected_rows:,} had been marked "
                f"as {SELECTED_LABEL}, so that comparison is short by the same "
                "number."
            )
    # The identity, closed on the page. Every bucket is named above; this is
    # the one line that adds them up, and it is printed whether or not it
    # balances — a census stated only when it works is a census whose failure
    # is invisible.
    identity = (
        f"Census: {paired:,} paired + {rows:,} excluded + {no_pair_key:,} with "
        f"no pair key = {accounted:,}, against {supplied:,} graded wagers "
        "supplied."
    )
    if accounted != supplied:
        identity += (
            " **Those three terms do not add up to the wagers supplied**, so a "
            "graded wager reached none of the three buckets and the counts "
            "above are of unknown completeness."
        )
    paragraphs.append(identity)
    out: list[str] = []
    for paragraph in paragraphs:
        out.append(paragraph)
        out.append("")
    return out


def _populations_section(record: Mapping) -> list[str]:
    """The two populations, named and counted, before any number from either."""
    populations = record.get("populations") or {}
    whole = populations.get("all_opinions") or {}
    subset = populations.get("selected") or {}
    excluded = populations.get("excluded_unpairable") or {}
    lines: list[str] = []
    add = lines.append
    add("## Two populations, and which one is the skill measure")
    add("")
    add(
        "A card takes a wager when the model's disagreement with the price "
        "clears a threshold, and the bets are therefore the tail of the model's "
        "own error distribution — the winner's curse. Regressing outcome on "
        "that same disagreement **over the bets alone** builds the curse into "
        "the coefficient, and a claimed-edge table over them is tautological: "
        "every row is above the threshold by construction. Until 2026-09-05 the "
        "graded export was exactly the bets, so this report's regression ran "
        "over the slice it exists to avoid. Two populations are now measured, "
        "and every number below says which it belongs to."
    )
    add("")
    add("| Population | What it is | Scorable wagers | Games | Days |")
    add("|:---|:---|---:|---:|---:|")
    add(
        f"| **{whole.get('label', ALL_OPINIONS_LABEL)}** | "
        f"**{whole.get('role', ALL_OPINIONS_ROLE)}** | "
        f"{int(whole.get('rows', 0)):,} | {int(whole.get('games', 0)):,} | "
        f"{int(whole.get('days', 0)):,} |"
    )
    if subset.get("available"):
        add(
            f"| {subset.get('label', SELECTED_LABEL)} | "
            f"{subset.get('role', SELECTED_ROLE)} | "
            f"{int(subset.get('rows', 0)):,} | {int(subset.get('games', 0)):,} | "
            f"{int(subset.get('days', 0)):,} |"
        )
    else:
        add(
            f"| {subset.get('label', SELECTED_LABEL)} | "
            f"{subset.get('role', SELECTED_ROLE)} | not supplied | — | — |"
        )
    if excluded.get("available"):
        add(
            f"| {excluded.get('label', UNPAIRABLE_LABEL)} | "
            f"{excluded.get('role', UNPAIRABLE_ROLE)} | "
            f"{int(excluded.get('rows', 0)):,} | — | — |"
        )
    else:
        add(
            f"| {UNPAIRABLE_LABEL} | {UNPAIRABLE_ROLE} | not supplied | "
            "— | — |"
        )
    add("")
    lines.extend(_excluded_lines(excluded))
    if subset.get("available"):
        add(
            f"The selected subset is {int(subset.get('rows', 0)):,} of "
            f"{int(whole.get('rows', 0)):,} scorable wagers, cut by the "
            f"`{SELECTED_COLUMN}` flag the price backtest stamped with the same "
            "predicate it used to count its bets. It is reported **beside** the "
            "whole, in its own section, and nothing in it is the skill measure."
        )
    else:
        add(
            f"The frame carried no `{SELECTED_COLUMN}` column, so the selected "
            "subset is not reported. Every number in this report belongs to "
            f"**{ALL_OPINIONS_LABEL}**."
        )
    add("")
    return lines


def _selected_report_section(record: Mapping) -> list[str]:
    """The threshold-selected bets, beside the whole and never instead of it."""
    selected = record.get("selected") or {}
    lines: list[str] = []
    add = lines.append
    add("## The threshold-selected bets, beside it — the winner's-curse comparison")
    add("")
    add(
        f"**Population: {SELECTED_LABEL} — {SELECTED_ROLE}.** These are the "
        "rows the model's own disagreement with the price selected. A "
        "disagreement coefficient here is fitted on the tail of the model's "
        "error distribution and says how much the selection cost, not whether "
        "the model knows anything; a bucket table here has nothing below the "
        "threshold by construction. Read the section above for the skill "
        "measure and this one for the size of the curse."
    )
    add("")
    if not selected.get("available"):
        add(
            f"**Not supplied.** {selected.get('reason') or ''} The forward "
            "evidence ledger does not carry the flag; the price backtest's "
            "`--write-graded` export does."
        )
        add("")
        return lines
    if not int(selected.get("rows", 0)):
        lines.extend(_nothing("No scorable wager was selected."))
        return lines
    for measured in selected.get("by_tier") or []:
        label = measured.get("label", "")
        add(f"### {label} — {SELECTED_LABEL}")
        add("")
        lines.extend(_fit_section(measured))
        add(f"#### Brier — {label} — {SELECTED_LABEL}")
        add("")
        lines.extend(_brier_section(measured))
        add(f"#### Claimed edge against what happened — {label} — {SELECTED_LABEL}")
        add("")
        lines.extend(_bucket_section(measured, record))
    pooled = selected.get("pooled") or {}
    add(f"### Pooled — {SELECTED_LABEL}")
    add("")
    add(POOLED_CAVEAT)
    add("")
    if not int(pooled.get("rows", 0)):
        lines.extend(_nothing("Nothing to pool."))
    else:
        lines.extend(_fit_section(pooled))
        add(f"#### Brier — pooled — {SELECTED_LABEL}")
        add("")
        lines.extend(_brier_section(pooled))
        add(f"#### Claimed edge against what happened — pooled — {SELECTED_LABEL}")
        add("")
        lines.extend(_bucket_section(pooled, record))
    return lines


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
    lines.extend(_populations_section(record))

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
        f"**Population: {ALL_OPINIONS_LABEL} — {ALL_OPINIONS_ROLE}.** Every "
        "number in this section and in the pooled section below it is fitted "
        "over that population. The threshold-selected bets are measured apart, "
        "in their own section further down, and are labelled as what they are."
    )
    add("")
    add(
        "**The three tiers are measured from non-conference margin, never "
        "assigned by a conference name list** — so the count in each moves "
        "with the data. They are three different distributions, and this lab "
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
    add(f"**Population: {ALL_OPINIONS_LABEL} — {ALL_OPINIONS_ROLE}.**")
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

    lines.extend(_selected_report_section(record))

    raw_fit = record.get("raw_market_fit") or {}
    add("## The same fit without the de-vig")
    add("")
    add(
        "The de-vig is a choice, and a choice whose effect nobody can see is an "
        "assumption. This is the identical regression run on the **raw** "
        "implied probabilities, with the hold still in them."
    )
    add("")
    add(f"**Population: {ALL_OPINIONS_LABEL} — {ALL_OPINIONS_ROLE}.**")
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
    provenance = RESTATEMENT.provenance_paragraph(record)
    if provenance:
        add(provenance)
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
    """Read a record, refusing any shape but this module's.

    Both directions are refused and both are named. An **older** record is the
    one this repository actually produces — `data/outputs/` carries records
    written by earlier runs — and it is the dangerous one: its keys are a
    subset of what `render` reads, so re-rendering it drops whole paragraphs
    and leaves a report that looks finished. A **newer** record was written by
    a checkout ahead of this one and cannot be read at all. Neither is
    salvaged: the fix is to re-run the regression, not to re-render.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    version = int(payload.get("record_version", 0))
    if version != RECORD_VERSION:
        older = version < RECORD_VERSION
        raise ForecastSkillError(
            f"{Path(path).name} is a version {version} record and this module "
            f"writes version {RECORD_VERSION}, so it is "
            + ("an older" if older else "a newer")
            + " shape. Re-run the regression rather than re-rendering a record "
            "whose shape has changed — a stale record renders a report with "
            "holes in it and nothing looks wrong."
        )
    return payload


def _restate_cell(cell: Mapping, *, looks: int) -> dict:
    """One stored cell at `looks` — a coefficient through its own class.

    A Brier advantage is a `RoiInterval` and the shared rebuild handles it. A
    fitted coefficient is not: :meth:`Coefficient.verdict` **raises** for every
    term but the disagreement, because a market coefficient of 0.97 excludes
    zero on the positive side and a predicate that never asked what the null
    was would announce it as a demonstrated edge. So a coefficient is restated
    by rebuilding the object and asking it again, which routes `reading`,
    `gloss` and `contains_null` through the same door they were written by.
    """
    if "answers_the_question" in cell:
        coefficient = dataclasses.replace(
            coefficient_from_row(dict(cell)), looks=int(looks)
        )
        out = dict(cell)
        out.update(coefficient.to_json())
        return out
    return RESTATEMENT.rebuild_cell(cell, looks=looks)


def restated(record: Mapping, *, looks: int, record_name: str = "") -> dict:
    """The record with every interval, verdict and reading re-derived at `looks`.

    The claimed-edge comparison is re-derived too: `anti_predictive_return`
    asks whether two buckets' **family-corrected** intervals are disjoint, and
    that question has a different answer under a wider correction. Leaving it
    at the stored answer would put one sentence of this report at a narrower
    correction than the table above it.
    """
    moved = RESTATEMENT.restate_tree(record, looks=looks, rebuild=_restate_cell)
    for cell in _cells_with_buckets(moved):
        cell["anti_predictive_return"] = anti_predictive_return(
            cell.get("buckets") or []
        )
    return RESTATEMENT.stamp(moved, looks=looks, record_name=record_name)


def _cells_with_buckets(record: Mapping) -> list[dict]:
    """Every cell carrying a bucket table: each tier, the pooled fit, and both
    of those again inside the selected-bets population."""
    found: list[dict] = []

    def walk(node: object) -> None:
        if isinstance(node, dict):
            if "anti_predictive_return" in node and "buckets" in node:
                found.append(node)
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(record)
    return found


def record_file_name(record: Mapping) -> str:
    """The record file a restated report points a reader back at."""
    key = str(record.get("competition", CBB.key)) or CBB.key
    return f"{key}_{REPORT_STEM}.json"


def write_report(record: Mapping, path: Path, *, looks: int | None = None) -> Path:
    """Render the report. With `looks`, state its readings at that family size.

    `looks` is the experiment ledger's count **at render time**. Passing the
    record's own count is a no-op, so an unchanged ledger re-renders to the
    same bytes.
    """
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = (
        record
        if looks is None
        else restated(record, looks=looks, record_name=record_file_name(record))
    )
    target.write_text(render(payload), encoding="utf-8")
    return target
