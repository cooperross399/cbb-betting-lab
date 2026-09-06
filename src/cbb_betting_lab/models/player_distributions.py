"""One athlete, one object, and the ten prop markets read off it.

This is the distribution half of the player model. It takes a
:class:`~cbb_betting_lab.models.player_rates.PlayerProjection` — a minutes
lattice, seven per-minute rates and the athlete's own 1/2/3 scoring mix — and
turns it into count pmfs and, per line, `(win, push, loss)`.

It states **no result**. There is no de-vig here, no log loss, no ROI, no
comparison against a price and no interval. Those belong to the grading commit,
which is gated on design 10's wager reconciliation and has not run. Every
number this module produces is a probability under its own model or a
structural check against a frozen target, and the two are never mixed.

## The defect this file is arranged against

`models/distributions._match_variance` is refused for player counts, and the
refusal is structural rather than stylistic. It is a linear dilation of a
Poisson lattice with a linear split between neighbouring integers. At team-score
scale the dilation factor sits near 1 and it is harmless; a player points count
needs c ~ 1.8, and the split aliases source integers into a comb — adjacent-
integer swings of ~5x at identical mean and identical variance, mean
|dP(over)| ~ 2.5pp against a smooth family with the same two moments (the
design's measurement, quoted, not re-measured here). A 2% ROI edge at -110 is
~1.0pp, so that is a deterministic, line-dependent error 2.5x the effect under
test on the four largest markets.

`tests/test_player_distributions.py::test_no_player_count_is_built_by_match_
variance` parses this file's AST and fails if either name is imported, so the
refusal is a checked fact rather than a paragraph.

What replaces it is one mechanism with three closed forms — the (a,b,0) Panjer
family — compounded for the points family and mixed over the minutes lattice.
Every member is smooth, every member is exactly convolvable, and the recursion
is the same three lines for all of them.

## The five things this file gets right on purpose

*The Panjer member is chosen by the conditional dispersion, and the binomial arm
is real.* `turnovers` measures phi = 0.98286 on the fit window and 0.99787 held
out. A negative binomial cannot represent phi < 1 at all — its variance is
`mu * (1 + beta)` with `beta > 0` — so a "just use NB everywhere" engine is not
a simplification of this one, it is a different and wrong answer on one of the
ten markets. :func:`panjer_family` reads the frozen dispersion and
`tests/test_player_distributions.py::test_the_panjer_member_matches_the_frozen_
files_own_recorded_family` asserts the branch equals the string the fit
recorded, for all seven stats, on both windows. That is the file checking the
code rather than the code checking itself.

*Points is a compound sum, not a count.* `S = sum_{i=1..N} V_i` with `N` the
scoring-event count and `V` in {1,2,3} drawn from the athlete's own shrunk mix.
The phi handed to `N` is `points_compound_reconciliation.effective_event_
dispersion` = 1.1059306970490195 and **not** `conditional_dispersion.
points_events` = 1.3799506487253412; see :data:`POINTS_EVENT_DISPERSION_KEY`
for the arithmetic that decides it. The compound recursion runs over a severity
pmf with `f[0] = 0`, which is exact and O(3K) and cannot ring the way an FFT
does — a tiny negative tail mass from ringing would trip D1 for a numerical
reason rather than a structural one.

*`player_threes` is thinned out of the same object.* Design 4 is explicit that
threes "falls out as the three-point component of the same object rather than as
a separate count", so the three-point count is the scoring-event count thinned
at `p3 = value_pmf[2]`. Thinning preserves the (a,b,0) family exactly
(:func:`thin`), so `rates["threes"]` and `conditional_dispersion["threes"]`
become CHECK quantities for threes exactly as `rates["points"]` and
`conditional_dispersion["points"]` are for points. Taking the standalone route
instead would make design 4's second structural check — the produced
`corr(points, threes)` given minutes — a comparison of a constant with itself,
because the number that would be imposed through the copula and the number
being checked against are the same frozen 0.6021705535430947.

*The minutes channel is applied exactly once, and the order is asserted.*
`minutes lattice -> conditional Panjer/compound -> residual copula -> component
sum -> mix over m`, in that order, with the copula strictly inside the minutes
node because `residual_correlation`'s own provenance is "residuals within
(season, athlete, realised minute)". Applying it after the mixture re-imposes a
coupling the mixture already produced. :meth:`PlayerDistribution.node_market_
pmf` exposes the per-node objects so the ordering is a checked number rather
than a comment: `test_the_minutes_channel_is_applied_exactly_once` asserts the
law-of-total-variance identity against the node pmfs and shows that mixing
twice is materially wider.

*Mass at zero minutes is zero, and `dnp_probability` never reaches a price.*
The book **voids** a did-not-play, so the priced quantity is
`P(stat > line | the wager stands)`. `minutes_pmf[0] == 0.0` is re-asserted here
on every build — the estimator guarantees it, and a guarantee whose consumer
does not check it is a comment — and `dnp_probability` is carried through to the
stored `void_probability` column as a diagnostic that is multiplied into
nothing.

## What is declared here rather than fitted, and why it had to be

Three constants this engine needs have no counterpart in
`data/processed/cbb_player_shapes.json`. None is invented as a fitted number;
all three are declared as structural, with the reason written down and a test
that goes red if any is quietly turned into a fit:

* :data:`POISSON_BAND` — design 4 says "VMR = 1 -> Poisson", which never happens
  in floating point. It MUST NOT be set to
  `conditional_dispersion.material_absolute` = 0.02, because the frozen
  turnovers phi is 0.9828561088984643, i.e. 0.0171 from 1, and a 0.02 band would
  swallow the binomial branch entirely and delete the only case design 4 says
  the binomial exists for. That 0.02 now has a reader of its own — it is the
  floor :func:`panjer_parameters` checks the binomial's integer rounding
  against, threaded down from :func:`build` through
  :func:`_materiality_floor` — and the two questions are different at the same
  scale: "did the rounding move the dispersion materially" is what the fit's
  agreement floor is the right size for, and "is this dispersion equal to one"
  is not.
* :data:`COUNT_LATTICE_HARD_CAP` — R4 refuses a mean "above the lattice
  ceiling" and the frozen file declares `minutes_support` and no count ceiling
  for any of the seven stats, so R4's upper half was unenforced. It is enforced
  here, from a declared tail tolerance and a structural cap.
* :data:`STRUCTURAL_CHECK_POPULATION_FLOOR` — design 4's check (a) is a POOLED
  quantity over regulars, so it needs a population, and the file says who is a
  regular (`regular_min_projected_minutes` = 15.0, read through
  :meth:`PlayerShapes.evidence`) but not how many of them make a population.
  Eight, and the measurement that chose it is on the constant.

Three, and it says three because a fourth was found and deleted. This module
also carried `_MINUTES_LATTICE_LENGTH = 46`, which is not a constant without a
counterpart at all: it is `declared.minutes_support` = [1, 45] retyped a third
time, after the frozen file and after `player_rates.MINUTES_SUPPORT` — and
`player_rates` holds ITS copy against the file at price time while this one was
held against nothing. It is now derived, in :func:`_minutes_lattice_length`,
which is where the drift it would have caused is written down.

## What this module does not do

It grades nothing, it selects nothing, and it opens no file: `shapes` arrives
as an argument, exactly as it does in `player_rates`, and every constant is
read through :class:`~cbb_betting_lab.models.player_shapes.PlayerShapes` so the
walk-forward guard has already run on it. It never calls `shapes.held_out_value`
on a pricing path — the holdout is a check, and a model that reaches for it has
spent it — and the one place a held-out number appears is
:func:`held_out_panjer_families`, which prices nothing.

`player_first_basket` and `player_double_double` are refused BY NAME, through
`player_rates.MARKETS_REFUSED_BY_NAME` read verbatim. They are not missing
engines, they are not a pass, they are not an avoid, and they are not a
no-value call.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

import numpy as np
from scipy.special import ndtr, ndtri

from cbb_betting_lab.models.player_rates import (
    MARKET_COMPONENTS,
    MARKETS_REFUSED_BY_NAME,
    PlayerProjection,
)
from cbb_betting_lab.models.player_shapes import PlayerShapes
from cbb_betting_lab.selection import OVER, UNDER

__all__ = [
    "PlayerDistributionError",
    "MarketRefused",
    "StructuralCheckFailed",
    "PanjerParameters",
    "PlayerDistribution",
    "build",
    "panjer_family",
    "panjer_parameters",
    "thin",
    "compound_pmf",
    "coupled_sum_pmf",
    "price_line",
    "count_lattice_ceiling",
    "assert_structural_checks",
    "population_structural_checks",
    "held_out_panjer_families",
    "points_threes_correlation",
    "CONSTRUCTION_ORDER",
    "POISSON_BAND",
    "COUNT_LATTICE_TAIL_TOLERANCE",
    "COUNT_LATTICE_HARD_CAP",
    "COPULA_NODES_PER_CELL",
    "COPULA_LATENT_LIMIT",
    "OUTER_CELL_PIECES",
    "OUTER_CELL_RATIO",
    "MARGINAL_SWEEPS",
    "UNCONDITIONAL_POINTS_VMR_STOP",
    "STRUCTURAL_CHECK_POPULATION_FLOOR",
    "POINTS_EVENT_DISPERSION_KEY",
    "PANJER_STATS",
    "COMPOUND_STATS",
]


class PlayerDistributionError(ValueError):
    """The engine was asked for a price it cannot honestly produce.

    Caller-side mistakes only: an unpriceable projection handed here anyway, a
    minutes lattice that carries mass at zero minutes, a market key outside the
    ten, a line above the count lattice's ceiling. Never raised because a
    subject has no opinion — that is an absence upstream and it never reaches
    this module.
    """


class MarketRefused(PlayerDistributionError):
    """This market is refused, in the refusal's own words.

    Deliberately a subclass rather than a return value: design 7 says a refusal
    is an entry with `priceable=False` and a full sentence, and a caller that
    could drop a boolean would turn a refusal into a missing engine. The two
    are different census buckets and this repository has the inversion written
    down.
    """


class StructuralCheckFailed(PlayerDistributionError):
    """Design 4's stop rule fired: the run stops and the discrepancy is the finding.

    Raised only by :func:`assert_structural_checks`, only for the unconditional
    within-player points VMR **pooled over the run's regular athletes**, and only
    outside +/-15%. Nothing else in design 4 or in `structural_check_targets`
    declares a tolerance, so nothing else here can stop a run — the rest are
    reported.

    It reaches a run through `reports/gameday_card.opinions_for`, which is the
    only function in this repository that turns wagers into modelled
    probabilities. It escapes rather than being folded into `OpinionCensus`: a
    declined wager is a wager the model had no opinion about, and this is the
    model saying its own assembled mixture does not reproduce a number nothing
    in it can influence. Those are different facts and a card that printed the
    second as the first would have turned a stop into a footnote.
    """


# --------------------------------------------------------------------------
# Declared constants. Neither of the first two is in the frozen file, and the
# reason each is declared HERE rather than fitted is the whole content of it.
# --------------------------------------------------------------------------

#: How close the conditional dispersion has to be to 1 before the count is
#: called Poisson. **A numerical-degeneracy epsilon, declared, not fitted.**
#:
#: Design 4 writes the rule as "VMR = 1 -> Poisson", which is not a branch any
#: floating-point number takes. Below this band the two neighbouring
#: parameterisations diverge — the binomial's `n = mu/(1-phi)` and the negative
#: binomial's `r = mu/(phi-1)` both go to infinity — so the band exists to keep
#: the arithmetic finite and for no other reason.
#:
#: It MUST NOT be `conditional_dispersion.material_absolute` (0.02). That
#: number is the fit's materiality floor for *agreement between two windows*,
#: and using it here would swallow the frozen turnovers phi of
#: 0.9828561088984643 — 0.0171 from 1 — deleting the binomial branch that design
#: 4 spends a paragraph justifying, on the one market that needs it.
#: `test_the_poisson_band_does_not_swallow_the_binomial_arm` asserts both the
#: fit and the held-out turnovers phi still select "binomial".
POISSON_BAND: float = 1e-12

#: The truncated tail a count lattice is allowed to drop, at the largest
#: minutes node. Declared, not fitted: it is a numerical accuracy target, and
#: 1e-12 is four orders of magnitude below the smallest probability any of the
#: ten markets is ever read at.
COUNT_LATTICE_TAIL_TOLERANCE: float = 1e-12

#: The hard ceiling on a single component's count lattice. **Structural, not
#: fitted, and it is the missing half of R4.**
#:
#: R4 refuses a mean "above the lattice ceiling"; the frozen file declares
#: `minutes_support` = [1, 45] and no count ceiling for any of the seven stats,
#: so until this module existed the upper half of R4 was enforced on minutes and
#: not on counts — `tests/test_player_rates.py` says so in clause 5 of its
#: limitations. It is declared rather than fitted because a count of 200 in one
#: of these seven stats has never happened in a Division I game (the single-game
#: scoring record is 100, and points is by far the largest of the seven), so a
#: distribution that needed more rungs than this would be describing a mean the
#: model should have refused, not a tail it should have kept.
COUNT_LATTICE_HARD_CAP: int = 200

#: Gauss-Legendre nodes per latent cell in the copula quadrature. Declared for
#: accuracy, and checked rather than asserted: the independence case is exact to
#: floating point at any value of this (see :func:`coupled_sum_pmf`), and
#: `test_the_copula_is_deterministic_and_reduces_to_a_convolution` pins both.
COPULA_NODES_PER_CELL: int = 5

#: How many geometric slivers the first and last latent cell are cut into, and
#: by what factor. Declared for accuracy; :func:`_split_outer_cells` carries the
#: whole measurement, including what it does NOT settle — the sum pmf's error
#: against an 800-node reference is 1.289e-09 at six pieces and 9.181e-10 at
#: seven, so the measurement bounds the choice rather than picking six out of
#: it. Four is the bottom of a U in the ratio, jointly with five.
OUTER_CELL_PIECES: int = 6
OUTER_CELL_RATIO: float = 4.0

#: Iterative-proportional-fitting sweeps that put the joint's marginals back on
#: the count pmfs, so the copula provably does not move a mean. Eight, measured
#: on the fixture's points-by-rebounds joint at its modal node: the worst
#: marginal error is 3.8e-11 at zero sweeps, 1.7e-14 at two and 2.8e-17 at four,
#: and does not improve after that. Eight is twice what the measurement needs,
#: which costs a few array multiplies on an object that has already had a
#: quadrature run over it.
MARGINAL_SWEEPS: int = 8

#: Where the latent normal is truncated when a cut point is infinite.
#: `Phi(-8.5) = 9.5e-18`, and the per-cell renormalisation in
#: :func:`coupled_sum_pmf` restores the truncated mass exactly, so this is a
#: node-placement bound and not a probability.
COPULA_LATENT_LIMIT: float = 8.5

#: Design 4's only stop rule: "If (a) is off by more than 15%, the run stops
#: and the discrepancy is the finding." Quoted from the design, not chosen here.
UNCONDITIONAL_POINTS_VMR_STOP: float = 0.15

#: How many REGULAR athletes a run must have priced before the stop above is
#: allowed to stop it. **A floor on the population the check is computed over,
#: not a tolerance**, and it is declared here because the frozen file has no
#: number for it.
#:
#: The defect it exists against: `structural_check_targets.
#: unconditional_points_vmr_regulars` = 3.0529074370522156 is a POOLED
#: within-player VMR over 242,634 rows of regulars, whose own
#: `regular_min_projected_minutes` is 15.0. Dividing ONE athlete's mixture VMR
#: by it compares two different objects, and the answer then moves with the
#: athlete's minutes rather than with the model. Measured on frozen constants
#: only — the file's own nine role priors, its own nine minutes shapes, tilted
#: to its own recorded bucket means 6.73 ... 36.22, at the league value mix —
#: the per-athlete ratio runs
#:
#:     1.1123  1.1203  1.0893  1.0497  1.0043  0.9626  0.9203  0.8790  0.8482
#:
#: while the CONDITIONAL half reads 2.328891545818532 at all nine, to floating
#: point, which is the frozen `points_vmr_given_minutes` exactly. So the entire
#: spread is the minutes channel, and the average 36.22-minute starter — inside
#: the population the target is measured on, not a tail case — is 15.2% low and
#: would stop the run on its own.
#:
#: Pooled the way the target is pooled — a ratio of two sums — those same nine
#: restricted to regulars reproduce 2.8113 against 3.0529074370522156, a ratio
#: of **0.9209**, 7.9% low and inside the stop. That is the number design 4's
#: sentence is about, and it is what :func:`population_structural_checks`
#: returns for them, because a slate carries each athlete once and the function
#: therefore weights them equally. Weighting the same six by the frozen file's
#: own `minutes_pmf` evidence `rows_per_bucket` instead — the occupancy the
#: TARGET's population actually has — gives 2.8803 and **0.9435**. Both are
#: inside; the pair is quoted so the composition sensitivity is on the page
#: rather than discovered later.
#:
#: Eight is where the floor sits, and it is measured rather than picked.
#: Drawing regular athletes iid from that same `rows_per_bucket` mix, 40,000
#: populations at each size: at ONE athlete the stop fires on 2.72% of them on
#: composition alone; at two, 0.08%; at three and above, none of 40,000. At
#: eight the worst of 40,000 draws is 0.8745 — 12.6% off, still inside — so the
#: floor sits well past where the check stopped being a coin toss about which
#: athletes the book quoted. Below it the check does not stop and does not
#: silently pass either: it reports that it could not run, and
#: `test_the_population_floor_is_a_gap_that_is_held_open` is the passing
#: assertion that goes red the day a run-level population makes it closable.
STRUCTURAL_CHECK_POPULATION_FLOOR: int = 8

#: Which frozen number is handed to the scoring-event count's Panjer family.
#:
#: The frozen file freezes both candidates under
#: `points_compound_reconciliation` and says in terms that "the choice belongs
#: to the model, not to the fit". This engine takes
#: `effective_event_dispersion` = 1.1059306970490195 and prints
#: `measured_event_dispersion` = 1.3799506487253412 beside it on every run.
#:
#: The reason is an identity, not a preference. For a mixture with a mean linear
#: in minutes and a constant conditional VMR, `VMR_unconditional = VMR_conditional
#: + r * Var(M)/E(M)`, so the minutes lift is additive and equals, from
#: `structural_check_targets`, 3.0529074370522156 - 2.328891545818532 =
#: 0.7240159. **That arithmetic is a statement about the frozen constants and
#: not about anything this module produces**, and the distinction is written out
#: here because it was once blurred: carrying the target's own POPULATION lift,
#: `measured_event_dispersion` implies 2.8377415929483303 + 0.7240159 =
#: 3.5617575, a ratio of 1.1667, and `effective_event_dispersion` implies
#: 2.328891545818532 + 0.7240159 = the target itself, a ratio of 1.0000. Neither
#: 1.0000 nor 1.1667 is a number :func:`population_structural_checks` returns or
#: ever could: the produced lift is each athlete's OWN `r * Var(M)/E(M)` over
#: his own minutes lattice, not the population's.
#:
#: What the engine does produce, through
#: :func:`population_structural_checks` over the frozen file's nine role-prior
#: athletes restricted to regulars: **0.9209** on this key, and **1.0875** on
#: `measured_event_dispersion`. So the choice moves the produced ratio by 0.167
#: — the whole width of design 4's stop budget, which is why it is a choice
#: worth naming — but **both land inside the 15% stop, and the stop rule
#: therefore does not decide it**. The identity above does, and the file's
#: stated mechanism for the gap is that free throws arrive in pairs, so two made
#: free throws are one trip charged as two independent severity draws:
#: exchangeability fails, in the direction observed. `test_the_dispersion_
#: choice_is_not_decided_by_the_stop_rule` holds both produced numbers.
#:
#: The price of the choice is reported and not tuned away: the thinned
#: three-point marginal's produced VMR is then 1.0206 against a measured
#: `conditional_dispersion["threes"]` of 1.0846864899201918, about 6% narrow.
#: **That is at the LEAGUE `value_pmf`**, whose three-point share is
#: 0.19423721541072833; re-measured, `1 + p3*(phi - 1)` is 1.020575683621319
#: there and the narrowness 5.9105%. It runs through the athlete's own shrunk
#: mix, so it is a different number for every athlete — the test fixture's
#: 0.2727822483104362 gives 1.0288960137061232 and 5.14% — and
#: :meth:`PlayerDistribution.phi_conditional` reports the athlete's, not this
#: one. Design 4 declares a tolerance for (a) and for nothing else, so that one
#: is report-only. Both numbers appear in
#: :meth:`PlayerDistribution.structural_checks`.
#:
#: **The sentence in the frozen file that reads as a prohibition on this line,
#: quoted and answered.** `points_compound_reconciliation`'s note ends:
#:
#:     "The design's published 1.11 is the SECOND of these: it reproduces as
#:     `effective_event_dispersion` = 1.106 here and 1.079 on the design's own
#:     two seasons, inside its own +/-0.05 gate. It is not the event count's
#:     dispersion and must not be handed to a Panjer family as one."
#:
#: Read with "It" bound to `effective_event_dispersion`, that forbids exactly
#: what :func:`build` does, and an auditor comparing this module against the
#: file finds a contradiction with nothing to read. It is answered here rather
#: than left standing, and the answer is an antecedent, not a preference.
#:
#: *The subject of that sentence is the design's published 1.11, not this
#: constant.* The fitter's own `compound_reconciliation` — the function that
#: wrote both the value and the note, `scripts/fit_player_model.py` — says of
#: the design's number: "The design's own published 1.11 is neither: it is
#: `VMR(points|m) / (E[V^2]/E[V])`, a multiplier on the compound-*Poisson*
#: points VMR, which is reproduced here to about a hundredth. Read as an event
#: count's dispersion -- which is how a Panjer family would consume it -- it is
#: out by about 0.24, and that is the reading a distribution engine is most
#: likely to take." The note's "is the SECOND of these" and the fitter's "is
#: neither" cannot both be true; the file's own evidence block sides with the
#: fitter — "the design's 1.11 reproduces as `points_vmr_over_compound_poisson`,
#: not as an event-count dispersion" — and that quantity is
#: 1.0922583243981805, which this module reads nowhere.
#:
#: *The arithmetic that settles it.* `effective_event_dispersion` is not
#: measured; it is DEFINED by inverting the compound identity, `phi =
#: (VMR_points * E[V] - Var[V]) / E[V]^2`, and handing it back to a Panjer
#: family is the only thing it can be for. Measured on the file's own evidence
#: — `E[V]` = 1.856981741719531, `Var[V]` = 0.5110384669003465 — the compound
#: identity `(Var[V] + phi*E[V]^2)/E[V]` returns **2.328891545818532 exactly**,
#: bit-for-bit the frozen `measured_points_vmr_given_minutes`, at
#: `effective_event_dispersion`; and **2.8377415929483303 exactly**, bit-for-bit
#: the frozen `compound_implied_points_vmr`, at `measured_event_dispersion`. A
#: constant computed by inverting the identity cannot coherently be barred from
#: the family it was inverted out of, and the same note says in the sentence
#: before that "the choice between them belongs to the model, not to the fit".
#:
#: *What the other reading would cost, so the choice is not hidden behind the
#: antecedent.* Obeying it literally means handing over
#: `measured_event_dispersion`, and the produced conditional points VMR becomes
#: 2.8377415929483303 against the file's own measured 2.328891545818532 — 21.8%
#: wide, the 22% overstatement the note itself names — while the population
#: ratio moves from 0.9209 to 1.0875. Both are inside design 4's 15% stop, so
#: the stop rule does not decide this either way, and the engine prints
#: `measured_event_dispersion` beside `effective_event_dispersion` on every run.
#: `test_the_file_says_this_number_must_not_be_handed_to_a_panjer_family` reads
#: the sentence out of the frozen file, re-measures both sides of the identity,
#: and goes red the day a refit rewrites the note — at which point this answer
#: has to be rewritten with it.
POINTS_EVENT_DISPERSION_KEY: str = "effective_event_dispersion"

#: The order design 5 fixes, recorded so a reader and a test see the same list.
#: The numeric assertion that it holds is
#: `test_the_minutes_channel_is_applied_exactly_once`; this tuple is the label
#: on it, not the evidence for it.
CONSTRUCTION_ORDER: tuple[str, ...] = (
    "minutes_lattice",
    "conditional_panjer_or_compound",
    "residual_copula",
    "component_sum",
    "mix_over_minutes",
)

#: The stats whose count is a plain Panjer draw at their own frozen conditional
#: dispersion.
PANJER_STATS: tuple[str, ...] = ("rebounds", "assists", "steals", "turnovers")

#: The stats that come out of the shared scoring-event object instead: `points`
#: as the compound sum over the value mix, `threes` as the same count thinned at
#: `value_pmf[2]`.
COMPOUND_STATS: tuple[str, ...] = ("points", "threes")

#: Constants this module reads and must therefore check for a fit-level refusal
#: before it prices anything. `player_rates._unfittable` reads only `role_prior`
#: and `rate_shrinkage_k`, so these six are unchecked anywhere else and a
#: market that needs one of them would otherwise be priced on a number the fit
#: refused to stand behind.
#:
#: The other half of R5 does NOT come through here and must not be looked for
#: here: `role_prior.<stat>` and `rate_shrinkage_k.<stat>` are the two the
#: estimator itself reads, and it hands them on as `projection.refused_stats`,
#: which :func:`build` folds into the same market refusals. That is the split
#: that hid the `points_events` crash — this tuple can only ever refuse a market
#: whose CONSTANT was refused, and `points_events` is refused by STAT.
#:
#: The shipped `unfittable` block is empty, so both halves ship exercised only
#: against a synthetic file, which is what
#: `test_a_constant_the_fit_refused_to_invent_refuses_the_market` and
#: `test_an_r5_refusal_of_the_scoring_event_count_refuses_instead_of_crashing`
#: build. (The name this comment carried before was
#: `..._refuses_the_market_that_needs_it`, which is not a test that exists in
#: this repository.)
_CONSTANTS_READ_HERE: tuple[str, ...] = (
    "conditional_dispersion",
    "value_pmf",
    "value_mix_shrinkage_events",
    "points_compound_reconciliation",
    "residual_correlation",
    "structural_check_targets",
)

#: A scoring event is worth one, two or three points. Structural, not fitted:
#: there is no fourth value for a basketball possession to be worth, and the
#: frozen `value_pmf` is a pmf OVER these three and does not name them.
_SEVERITY_SUPPORT = (1, 2, 3)


# --------------------------------------------------------------------------
# The (a,b,0) family
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class PanjerParameters:
    """One (a,b,0) member, in the form the recursion consumes.

    `phi_requested` is what the frozen file said; `phi_used` is what the family
    actually carries once the binomial's `n` has been rounded to an integer.
    They are equal for the Poisson and the negative binomial and differ by a
    rounding for the binomial, and it is `phi_used` that is stored in design 9's
    `phi_conditional` column, because that is the dispersion the price was
    actually made at.

    `materiality` is the floor the gap between those two was CHECKED against —
    `conditional_dispersion.material_absolute`, read out of the frozen file by
    :func:`build` and never defaulted here. It is carried on the member rather
    than on the module so :func:`thin` can hand the same floor to the thinned
    family: a derived count that quietly acquired a laxer floor than the count
    it came from would be the guard defeating itself one construction at a time.
    """

    family: str
    mu: float
    phi_requested: float
    phi_used: float
    a: float
    b: float
    g0: float
    materiality: float
    trials: float = float("nan")
    shape_r: float = float("nan")
    scale_beta: float = float("nan")

    def variance(self) -> float:
        """`mu * phi_used`, which is the whole content of the parameterisation."""
        return self.mu * self.phi_used


def panjer_family(phi: float) -> str:
    """Which (a,b,0) member a conditional dispersion selects.

    Design 4's rule, with :data:`POISSON_BAND` supplying the equality that
    floating point cannot. Below 1 a binomial, at 1 a Poisson, above 1 a
    negative binomial — and the first branch is not decoration: `turnovers`
    measures 0.9828561088984643 on the fit window and 0.9978708188334368 held
    out, and a negative binomial has variance `mu * (1 + beta)` with `beta > 0`,
    so it cannot reach a variance below its mean at any parameter value at all.

    The frozen file records the branch itself, per stat, at
    `conditional_dispersion.evidence.<window>.<stat>.panjer_family`, and
    `test_the_panjer_member_matches_the_frozen_files_own_recorded_family`
    asserts this function agrees with those strings for all seven stats on both
    windows rather than asserting it agrees with itself.
    """
    value = float(phi)
    if not math.isfinite(value) or value <= 0.0:
        raise PlayerDistributionError(
            f"A conditional dispersion of {phi!r} is not a variance-to-mean "
            "ratio. Every (a,b,0) member needs a strictly positive one, and a "
            "count with no dispersion is a market to refuse, not a family to "
            "guess at."
        )
    if abs(value - 1.0) <= POISSON_BAND:
        return "poisson"
    return "binomial" if value < 1.0 else "negative_binomial"


def panjer_parameters(
    *, mu: float, phi: float, materiality: float
) -> PanjerParameters:
    """`(a, b, g0)` for the member :func:`panjer_family` selects at this `phi`.

    The three parameterisations, each matched on `(mu, phi * mu)` so that the
    mean is the projection's and the variance is the frozen dispersion's:

    * binomial, `p = 1 - phi`, `n = mu / (1 - phi)`:
      `a = -(1-phi)/phi`, `b = (n+1)(1-phi)/phi`, `g0 = phi**n`;
    * Poisson, `lambda = mu`: `a = 0`, `b = mu`, `g0 = exp(-mu)`;
    * negative binomial, `r = mu/(phi-1)`, `beta = phi-1`:
      `a = (phi-1)/phi`, `b = (r-1)(phi-1)/phi`, `g0 = phi**(-r)`.

    **The binomial's `n` is not an integer at any (mu, phi) this store carries,
    and the (a,b,0) recursion needs one.** Arithmetic on the frozen turnovers
    phi: `1 - phi = 0.0171439`, so `n` is 58.33 at mu = 1.0, 99.16 at mu = 1.7
    and 174.99 at mu = 3.0. Left alone the recursion runs past `-b/a = n+1` and
    emits negative mass. The declared convention is `n = round(mu/(1-phi))`
    followed by a re-solve of `p = mu/n`, so the **mean is preserved exactly**
    — D3 and D5 are first-moment identities and must not pay for a rounding —
    and the dispersion moves by `O(1/n)`.

    **The realised `phi_used = 1 - p` is then checked against `materiality`, and
    the check is performed rather than described.** Until this commit the
    paragraph above ended with a sentence saying this function "refuses if the
    rounding moved it further than `conditional_dispersion.material_absolute` =
    0.02" and no such comparison existed anywhere: `material_absolute` was read
    by nothing in `src/`, `phi_requested` was stored on
    :class:`PanjerParameters` and never read back, and the `max(1, ...)` floor
    on the trial count silently substituted a different dispersion. Measured on
    the code as it stood, with nothing raised: `(mu=0.3, phi=0.5)` returned
    `trials=1`, `phi_used=0.70` — moved 0.20, ten times the floor the docstring
    named; `(mu=0.05, phi=0.8)` moved 0.15; `(mu=0.04, phi=0.9)` moved 0.06;
    `(mu=0.02, phi=0.95)` moved 0.03. All four now refuse, in words.

    The floor is a REQUIRED argument and is never defaulted here, because a
    floor this module chose would be a number about the file that did not come
    from it: :func:`build` reads
    `conditional_dispersion.material_absolute` = 0.02 out of the frozen file and
    hands it down, and :func:`thin` carries the same floor onto the thinned
    family. A non-finite or non-positive floor is refused before a family is
    chosen — `abs(gap) > nan` is False, so a NaN floor would be a guard that
    silently passed everything.

    **What the shipped file can and cannot reach.** The mechanism the guard is
    against is line `trials = max(1, int(round(mean / (1.0 - dispersion))))`:
    when `mu/(1-phi)` rounds to zero the floor forces a one-trial binomial and
    the realised dispersion becomes `1 - mu` whatever the fit said. `turnovers`
    is the one frozen dispersion below 1, at 0.9828561088984643, so the largest
    move it can produce is `1 - phi = 0.01714389110153569` as `mu -> 0` —
    inside the frozen 0.02, and measured over mu in [0.001, 6.0] at a step of
    0.001 the worst is 1.614e-02, also inside. So this refusal cannot fire on
    the file as shipped and it ships latent, exactly like R5: it fires on a
    refit that moves a sub-1 dispersion further from 1, or on a second stat
    entering the binomial arm. Over the narrower grid the older measurement
    quotes — mu in [0.2, 6.0] at a step of 0.01 — the mean error is exactly zero
    and the largest |phi_used - phi| is 5.484e-04, 2.74% of the floor.
    `test_the_binomial_rounding_preserves_the_mean_and_reports_its_own_error`
    re-measures both, and
    `test_the_binomial_rounding_refuses_a_material_move_and_reads_its_floor_from_the_file`
    holds the refusal and the provenance of the floor.
    """
    mean = float(mu)
    dispersion = float(phi)
    floor = float(materiality)
    if not math.isfinite(floor) or floor <= 0.0:
        raise PlayerDistributionError(
            f"A materiality floor of {materiality!r} is not a floor. The "
            "binomial rounding is checked against "
            "`conditional_dispersion.material_absolute` from the frozen file, "
            "and every comparison against a NaN is False — a floor that cannot "
            "be compared is a guard that passes everything."
        )
    if not math.isfinite(mean) or mean <= 0.0:
        raise PlayerDistributionError(
            f"A count mean of {mu!r} is outside the support this engine can "
            "price. R4 refuses a non-finite or non-positive mean before a "
            "family is chosen; a zero-mean count is a refusal, not a "
            "degenerate distribution."
        )
    family = panjer_family(dispersion)
    if family == "poisson":
        return PanjerParameters(
            family=family,
            mu=mean,
            phi_requested=dispersion,
            phi_used=1.0,
            a=0.0,
            b=mean,
            g0=math.exp(-mean),
            materiality=floor,
        )
    if family == "negative_binomial":
        beta = dispersion - 1.0
        shape = mean / beta
        return PanjerParameters(
            family=family,
            mu=mean,
            phi_requested=dispersion,
            phi_used=dispersion,
            a=beta / dispersion,
            b=(shape - 1.0) * beta / dispersion,
            g0=dispersion ** (-shape),
            materiality=floor,
            shape_r=shape,
            scale_beta=beta,
        )

    trials = max(1, int(round(mean / (1.0 - dispersion))))
    probability = mean / trials
    if not 0.0 < probability < 1.0:
        raise PlayerDistributionError(
            f"A binomial matched on (mu={mean}, phi={dispersion}) needs "
            f"{trials} trials at success probability {probability}, which is "
            "not a probability. The dispersion and the mean disagree about "
            "what this count is."
        )
    used = 1.0 - probability
    if abs(used - dispersion) > floor:
        raise PlayerDistributionError(
            f"A binomial matched on (mu={mean}, phi={dispersion}) needs "
            f"{trials} trial(s) once `n = mu/(1 - phi)` is rounded to an "
            f"integer, and the re-solved dispersion is {used}. That is "
            f"{abs(used - dispersion)} from what the fit recorded, past the "
            f"fit's own materiality floor of {floor}. The mean is preserved and "
            "the rounding is charged to the dispersion, so a move this large "
            "would price the count at a width nobody fitted — most often "
            "because `mu/(1 - phi)` rounded below one and the trial floor "
            "substituted a one-trial binomial whose dispersion is `1 - mu`."
        )
    return PanjerParameters(
        family=family,
        mu=mean,
        phi_requested=dispersion,
        phi_used=used,
        a=-probability / used,
        b=(trials + 1) * probability / used,
        g0=used**trials,
        materiality=floor,
        trials=float(trials),
    )


def thin(parameters: PanjerParameters, retention: float) -> PanjerParameters:
    """The same count with each event kept independently with probability `q`.

    Thinning preserves the (a,b,0) family exactly — Poisson to Poisson,
    binomial to binomial with `p*q`, negative binomial to negative binomial with
    `beta*q` — which is why design 4 can say `player_threes` "falls out as the
    three-point component of the same object rather than as a separate count"
    and have it mean something arithmetic. The produced dispersion is
    `1 + q*(phi - 1)` for every member, so the thinned marginal's width is a
    consequence of the shared event count rather than a second fitted number,
    and `conditional_dispersion["threes"]` is what it is checked against.

    **No new rounding happens here, and the materiality floor is carried
    through anyway.** The binomial arm keeps the trial count it was given and
    scales `p` by `q` exactly, so there is nothing for
    :func:`panjer_parameters`' rounding check to re-check; the floor is copied
    onto the thinned member so that a family derived from this one — through
    the Poisson arm, which does re-enter `panjer_parameters` — is checked
    against the floor the frozen file gave the count it came from rather than
    against one this module chose.
    """
    keep = float(retention)
    if not 0.0 < keep <= 1.0:
        raise PlayerDistributionError(
            f"A thinning probability of {retention!r} is not a probability. "
            "The three-point share of a scoring event comes from the athlete's "
            "own shrunk value mix and is strictly inside (0, 1]."
        )
    if parameters.family == "poisson":
        return panjer_parameters(
            mu=parameters.mu * keep, phi=1.0, materiality=parameters.materiality
        )
    if parameters.family == "negative_binomial":
        beta = parameters.scale_beta * keep
        shape = parameters.shape_r
        dispersion = 1.0 + beta
        return PanjerParameters(
            family="negative_binomial",
            mu=shape * beta,
            phi_requested=dispersion,
            phi_used=dispersion,
            a=beta / dispersion,
            b=(shape - 1.0) * beta / dispersion,
            g0=dispersion ** (-shape),
            materiality=parameters.materiality,
            shape_r=shape,
            scale_beta=beta,
        )
    trials = int(round(parameters.trials))
    probability = (1.0 - parameters.phi_used) * keep
    used = 1.0 - probability
    return PanjerParameters(
        family="binomial",
        mu=trials * probability,
        phi_requested=used,
        phi_used=used,
        a=-probability / used,
        b=(trials + 1) * probability / used,
        g0=used**trials,
        materiality=parameters.materiality,
        trials=float(trials),
    )


def compound_pmf(
    parameters: PanjerParameters, *, severity: Sequence[float], size: int
) -> np.ndarray:
    """`P(S = k)` for `k = 0..size`, `S = sum_{i=1..N} V_i`, by Panjer recursion.

        g[0] = g0
        g[k] = sum_{j=1..min(k,J)} (a + b*j/k) * f[j] * g[k-j]

    with `f[0] = 0`, which is what removes the `1/(1 - a*f[0])` factor and makes
    the recursion three lines. `severity` is the value pmf indexed by the value
    itself, so `severity[0]` is zero and `severity[1:4]` is the athlete's own
    1/2/3 mix; a plain count passes `(0.0, 1.0)` and the recursion collapses to
    `g[k] = (a + b/k) g[k-1]`, the textbook (a,b,0) form.

    Exact and O(J*size), and deliberately not an FFT: FFT convolution puts tiny
    negative masses in the tail, and D1's adjacent-integer smoothness check
    would then be failing for a numerical reason rather than the structural one
    it exists to catch.
    """
    weights = np.asarray(severity, dtype=float)
    if weights.ndim != 1 or weights.size < 2 or weights[0] != 0.0:
        raise PlayerDistributionError(
            "A compound severity is indexed by the value it pays and cannot put "
            "mass on zero: an event worth nothing is not an event. Got "
            f"{list(weights)}."
        )
    if size < 0:
        raise PlayerDistributionError(f"A count lattice cannot be {size} long.")
    highest = weights.size - 1
    pmf = np.zeros(size + 1, dtype=float)
    pmf[0] = parameters.g0
    indices = np.arange(1, highest + 1, dtype=float)
    for step in range(1, size + 1):
        top = min(step, highest)
        factors = parameters.a + parameters.b * indices[:top] / step
        # g[k-1], g[k-2], ... g[k-top]
        earlier = pmf[step - top : step][::-1]
        pmf[step] = float(np.dot(factors * weights[1 : top + 1], earlier))
    return pmf


def _trim(pmf: np.ndarray, tolerance: float = COUNT_LATTICE_TAIL_TOLERANCE) -> np.ndarray:
    """The shortest prefix holding all but `tolerance`, renormalised to sum to one.

    Every minutes node gets its own length: at 8 projected minutes a points
    lattice that runs as far as the 45-minute node's would be tens of rungs of
    1e-40, and the copula quadrature below costs a latent cell for each of them.
    Trimming happens in ONE place — :meth:`PlayerDistribution.node_component_pmf`
    — so the single markets and the combination markets read the identical
    arrays and D3's coherence stays exact by construction rather than by
    tolerance.
    """
    remaining = 1.0 - np.cumsum(pmf)
    within = np.flatnonzero(remaining <= float(tolerance))
    end = int(within[0]) if within.size else pmf.size - 1
    trimmed = pmf[: end + 1]
    return trimmed / trimmed.sum()


def count_lattice_ceiling(
    parameters: PanjerParameters,
    *,
    severity: Sequence[float],
    tolerance: float = COUNT_LATTICE_TAIL_TOLERANCE,
    cap: int = COUNT_LATTICE_HARD_CAP,
) -> int:
    """The smallest `K` holding all but `tolerance` of the mass, or R4 refuses.

    **This is the upper half of R4, and it did not exist before this file.**
    `tests/test_player_rates.py` records it as clause 5 of that module's
    limitations: R4 refuses a mean "above the lattice ceiling" and the frozen
    file declares `minutes_support` and no per-market count ceiling, so nothing
    enforced it. The ceiling is derived from the assembled distribution and a
    declared tail tolerance rather than fitted, and a distribution that has not
    spent its tail by :data:`COUNT_LATTICE_HARD_CAP` refuses instead of
    silently truncating — a truncated lattice reports `P(over) = 0` on a far
    rung, which is a confident wrong answer rather than a missing one.
    """
    pmf = compound_pmf(parameters, severity=severity, size=cap)
    remaining = 1.0 - np.cumsum(pmf)
    within = np.flatnonzero(remaining <= float(tolerance))
    if within.size == 0:
        raise MarketRefused(
            "refused: R4, mean outside support. This count has a mean of "
            f"{parameters.mu:.4f} at dispersion {parameters.phi_used:.6f} and "
            f"still carries {float(remaining[-1]):.3e} of its mass above "
            f"{cap}, which is the declared count-lattice ceiling. A lattice "
            "that has not spent its tail there is describing a mean this model "
            "should have refused, not a tail it should have kept."
        )
    return int(within[0])


# --------------------------------------------------------------------------
# The residual copula, inside the minutes node
# --------------------------------------------------------------------------


def _latent_cells(
    pmf: np.ndarray,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """`(values, u_edges, z_edges)` -- the latent interval each count owns.

    A discrete Gaussian copula maps `X = F^{-1}(Phi(Z))`, so the count `k`
    occupies `Z` in `(Phi^{-1}(F(k-1)), Phi^{-1}(F(k))]` and, equivalently,
    `U = Phi(Z)` in `(F(k-1), F(k)]`. Both edge arrays are returned because the
    quadrature runs in `U` and the conditioning runs in `Z`.

    Counts with no mass own an interval of zero width and are dropped; because a
    zero-mass cell does not move the cumulative, the surviving cells still tile
    the line without a gap, which is what lets the edges be one contiguous
    array. The infinite ends are placed at :data:`COPULA_LATENT_LIMIT`; that
    costs nothing, because the weights are taken in `U`, where the ends are
    exactly 0 and 1.
    """
    weights = pmf / float(pmf.sum())
    cumulative = np.cumsum(weights)
    cumulative[-1] = 1.0
    live = np.flatnonzero(weights > 0.0)
    u_edges = np.concatenate(([0.0], cumulative[live]))
    u_edges[-1] = 1.0
    z_edges = np.clip(
        ndtri(np.clip(u_edges, 1e-17, 1.0 - 1e-17)),
        -COPULA_LATENT_LIMIT,
        COPULA_LATENT_LIMIT,
    )
    return live, u_edges, z_edges


def _outer_fractions(pieces: int, ratio: float) -> np.ndarray:
    fractions = np.array(
        [0.0] + [float(ratio) ** -power for power in range(int(pieces) - 1, -1, -1)]
    )
    return fractions / fractions[-1]


def _split_outer_cells(edges: np.ndarray) -> np.ndarray:
    """Cut the first and last cell into geometric slivers against their outer edge.

    **The one place a five-node rule was measurably not enough, and why.** In
    probability space the integrand is `P(X_next = j | Z = Phi^{-1}(u))`, whose
    derivative in `u` is `-rho/s * [phi((c_j - rho*z)/s) - phi((c_{j-1} -
    rho*z)/s)] / phi(z)`. The `1/phi(z)` is the whole story: only the OUTER
    cells reach :data:`COPULA_LATENT_LIMIT`, where `phi(z)` is 8.0e-17, so only
    they hold a stretch over which a bounded integrand moves between two
    plateaux faster than any fixed-order rule can see. Every interior cell is
    smooth and five nodes are ample there.

    **Measured per cell rather than argued.** On the test fixture's
    points-by-rebounds joint at the 20-minute node, integrating each of the 29
    axis-0 cells with the shipped five-node rule and again with a 400-node one:
    the FIRST cell is out by 8.788e-07 at its worst count, the worst of the 27
    interior cells by 1.126e-09, and the median interior cell by 3.14e-14. That
    one cell in twenty-nine therefore carries 8.788e-07 of the 8.800e-07 the
    whole second marginal is out by, which is why the split is aimed at it. The
    LAST cell is out by 2.0e-17 undivided: it reaches the truncation too, but on
    the side where the lattice has already spent its mass, so it is narrow in
    `u` and the integrand across it is flat. Cut into
    :data:`OUTER_CELL_PIECES` = 6 pieces against :data:`OUTER_CELL_RATIO` = 4,
    the first cell's error falls to 6.654e-10.

    **What that is worth on the assembled object.** Same node, five nodes per
    cell, with the marginal fitting switched off (`MARGINAL_SWEEPS = 0`) so the
    quadrature stands alone. Undivided — `OUTER_CELL_PIECES = 1`, which
    :func:`_outer_fractions` makes an exact identity — the second marginal is
    wrong by 8.800e-07 at its worst rung and the sum's mean by 5.113e-05; at 6
    pieces and ratio 4, by 1.886e-09 and 1.109e-07. The SECOND marginal is the
    one that carries the error, and which component that is is not a choice:
    :func:`coupled_sum_pmf` sorts by support, so at this node axis 0 is
    rebounds and axis 1 is points, and axis 0's cell weights sum to its own
    cell probabilities exactly — that marginal is out by 5.5e-17 in every
    configuration below.

    **This function is NOT what makes D3's mean identity hold; the sweeps
    are.** With the shipped eight sweeps the identity holds with the split and
    without it alike: `|mu(sum) - sum(mu)|` is 0.0 on `player_points_rebounds`
    and 1.421e-14 on `player_pra`, undivided and split, the same two numbers.
    So :func:`_fit_marginals`' neighbouring measurement — 5.1e-05 with neither
    and 1.2e-07 with this alone — must not be read as making this function
    load-bearing for D3. What the sweeps cannot restore is the DEPENDENCE, and
    that is what this is for: against an 800-node reference (converged — 400
    and 800 nodes agree to 9.97e-14) the coupled sum pmf at that node is out by
    7.256e-07 at its worst rung undivided and 1.289e-09 split, and the realised
    `points|rebounds` correlation reads 0.10207704656857115 undivided against
    the reference's 0.10209676623064948 — a miss of 1.97e-05, where the split
    misses by 3.6e-08.

    **Why six, and why four — and what the measurement does not settle.**
    Pieces, at ratio 4, against that reference: 7.256e-07, 1.793e-07,
    4.460e-08, 1.115e-08, 2.974e-09, 1.289e-09, 9.181e-10, 8.386e-10,
    8.200e-10, 8.156e-10 for 1 through 10. The error falls by a factor of four
    per piece through the fifth, by 2.3 for the sixth and by 1.40 for the
    seventh, and then stops: 8.16e-10 is the floor the interior cells' own
    five-node rule leaves, and no number of outer pieces can go below it. Six
    is within 1.58x of that floor, seven within 1.13x, ten within 1.00x. **The
    measurement does not single out six over seven** and this docstring does
    not pretend it does; what it settles is that anything at or above five is
    within 3.6x of the floor and that below five the constant matters — one
    piece is 890x the floor. Ratio, at 6 pieces: 9.411e-08, 2.221e-08,
    3.022e-09, 1.289e-09, 1.174e-09, 1.545e-09, 3.403e-09, 2.291e-08 at 1.5, 2,
    3, 4, 5, 6, 8 and 16. That is a U — too small and the innermost sliver
    never reaches the truncation, too large and the sub-cells are spent where
    there is no mass — and 4 and 5 are its bottom, within 10% of each other.

    **And what it is worth at price time, so the exponents are not read as a
    result.** Mixed over the whole minutes lattice, undivided against shipped,
    the priced pmf moves by at most 1.291e-06 on `player_points_rebounds` and
    7.550e-07 on `player_pra`, and the `over 19.5` win leg on the first moves
    from 0.44609676189196446 to 0.4460971685625639. This is an accuracy
    constant; nothing here is a measurement of an edge.

    **The four figures this docstring used to quote did not reproduce, which is
    why the test exists.** It said the undivided second marginal was wrong by
    7.2e-07 and the sum's mean by 8.9e-06, becoming 6.5e-10 and 7.4e-09 split.
    Re-measured they are 8.800e-07 / 5.113e-05 and 1.886e-09 / 1.109e-07, and
    they never reproduced: run against this module AS IT STOOD at commit
    0985942 — the commit that wrote the four figures — the fixture's component
    means come back 9.41767029946209 and 4.0588963589730103 and all four
    errors come back identical to today's, so nothing repaired on this branch
    moved them. And no node of the 45 reproduces the quoted pair:
    node 21's undivided marginal reads 6.939e-07 but its mean error 4.281e-05,
    and node 30's mean error reads 8.377e-06 but its marginal 8.545e-08. The
    constants were right and the measurement was wrong. Nothing re-measured
    them, so they could not go red;
    `test_the_outer_cell_split_re_measures_the_numbers_that_fix_its_constants`
    now measures every figure above and asserts this docstring still quotes it.
    """
    if edges.shape[-1] < 3:
        # One cell owns the whole line, so there is no outer cell to separate
        # from an interior one. Splitting it would emit `2*pieces` sub-cells
        # against `2*pieces` counts and one edge too few, which is an
        # off-by-one nobody would ever see: it needs a component whose entire
        # mass sits on a single count.
        return edges
    fractions = _outer_fractions(OUTER_CELL_PIECES, OUTER_CELL_RATIO)
    first = edges[..., :1] + (edges[..., 1:2] - edges[..., :1]) * fractions
    last = edges[..., -1:] - (edges[..., -1:] - edges[..., -2:-1]) * fractions[::-1]
    return np.concatenate([first[..., :-1], edges[..., 1:-1], last[..., 1:]], axis=-1)


def _split_values(values: np.ndarray) -> np.ndarray:
    """The count each expanded cell still stands for; the outer counts repeat."""
    if values.size < 2:
        return values
    return np.concatenate(
        [
            np.repeat(values[:1], OUTER_CELL_PIECES),
            values[1:-1],
            np.repeat(values[-1:], OUTER_CELL_PIECES),
        ]
    )


def _cell_nodes(
    lower: np.ndarray, upper: np.ndarray, nodes_per_cell: int
) -> tuple[np.ndarray, np.ndarray]:
    """Gauss-Legendre abscissae and weights inside every cell, in PROBABILITY space.

    **The substitution is the whole accuracy argument.** Integrating
    `phi(z) f(z)` over a latent cell in `z` is quadrature against a bell curve,
    and the cells that carry the mass are wide -- the zero-count cell of a points
    lattice at eight minutes runs from -8.5 to +1.3 and straddles the peak -- so
    a five-node rule there is badly wrong. Substituting `u = Phi(z)` makes the
    measure uniform: the weights become the plain Gauss-Legendre weights, they
    sum over a cell to exactly that count's own probability with no
    renormalisation at all, and the integrand becomes a bounded conditional
    probability.

    Deterministic: `leggauss` is a fixed polynomial root set, there is no RNG
    anywhere in this module, and L1's bit-identity requirement is a real one.
    """
    abscissa, weight = np.polynomial.legendre.leggauss(int(nodes_per_cell))
    half = 0.5 * (upper - lower)[..., None]
    middle = 0.5 * (upper + lower)[..., None]
    return middle + half * abscissa, half * weight


def _latent(u: np.ndarray) -> np.ndarray:
    return np.clip(
        ndtri(np.clip(u, 1e-17, 1.0 - 1e-17)),
        -COPULA_LATENT_LIMIT,
        COPULA_LATENT_LIMIT,
    )


def _collapse(joint: np.ndarray, axis: int, values: np.ndarray, size: int) -> np.ndarray:
    """Sum the expanded outer slivers back onto the counts they stand for."""
    moved = np.moveaxis(joint, axis, 0)
    gathered = np.zeros((size,) + moved.shape[1:], dtype=float)
    np.add.at(gathered, values, moved)
    return np.moveaxis(gathered, 0, axis)


def _fit_marginals(joint: np.ndarray, marginals: Sequence[np.ndarray]) -> np.ndarray:
    """Scale the joint until every marginal is the count pmf it must be.

    Iterative proportional fitting, :data:`MARGINAL_SWEEPS` sweeps. It is the
    minimum-relative-entropy adjustment that reproduces given marginals, so it
    moves the dependence as little as any correction can, and it is here for one
    reason: **D3 is an identity and must hold as one.** The copula may not move
    a mean, so `mu(pra)` must equal `mu(points) + mu(rebounds) + mu(assists)`
    exactly rather than to whatever the quadrature happened to achieve. Measured
    on the test fixture: with neither this nor the outer-cell split the pra mean
    misses the sum of its components by 5.1e-05; with the split alone it misses
    by 1.2e-07, which still fails D3's 1e-9; with both it misses by 1.4e-14.

    A pmf entry that the quadrature sent to exactly zero cannot be scaled back
    up, so the sweep leaves it alone rather than dividing by zero; that only
    happens where the target is zero too, because a live count cell always has
    weight from its own quadrature nodes.
    """
    fitted = joint
    for _ in range(MARGINAL_SWEEPS):
        for axis, target in enumerate(marginals):
            others = tuple(index for index in range(fitted.ndim) if index != axis)
            current = fitted.sum(axis=others)
            scale = np.where(current > 0.0, target / np.where(current > 0.0, current, 1.0), 1.0)
            shape = [1] * fitted.ndim
            shape[axis] = -1
            fitted = fitted * scale.reshape(shape)
    return fitted


def coupled_sum_pmf(
    pmfs: Sequence[np.ndarray], correlation: np.ndarray
) -> np.ndarray:
    """The pmf of `X1 + ... + Xd` under a discrete Gaussian copula.

    Only the **sum's marginal** is wanted (design 5: "this is a per-minutes-node
    1-D convolution, not a joint"), so the joint is formed, summed out and
    discarded inside the node. The transient object is two- or three-
    dimensional and nothing five-dimensional is ever built -- which is half the
    reason `player_double_double` is refused rather than priced off the joint.

    Method: the latent normals are integrated in sequence -- `Z1`, then
    `Z2 | Z1`, then `X3 | Z1, Z2` in closed form -- by tensor-product
    Gauss-Legendre inside each latent cell, taken in probability space
    (:func:`_cell_nodes`), with the outer cells split geometrically
    (:func:`_split_outer_cells`) and the marginals fitted back onto the count
    pmfs (:func:`_fit_marginals`). Deterministic, with no RNG and no randomised
    QMC: L1 requires a re-price to be bit-identical, and scipy's
    `multivariate_normal.cdf` is randomised for `d >= 3`.

    Two properties this construction has by design, both asserted by
    `test_the_copula_is_deterministic_and_reduces_to_a_convolution` and by D3:

    * **at zero correlation it is exactly a convolution**, to floating point,
      because every cell's quadrature weights then sum to that count's own
      probability and the conditional count probabilities are the unconditional
      ones;
    * **it does not move the means**, because it does not move the marginals.

    The copula parameter is set equal to the measured Pearson correlation OF THE
    COUNTS, which is not the same object as a Gaussian copula's latent
    correlation. The realised correlation of the coupled discrete marginals is
    therefore reported beside the target and never solved back onto it: tuning
    the latent parameter until the discrete correlation hit
    0.10523131793586692 would be fitting a constant at price time.
    """
    lattices = [np.asarray(pmf, dtype=float) for pmf in pmfs]
    if not lattices:
        raise PlayerDistributionError("A market with no components has no sum.")
    if len(lattices) == 1:
        return lattices[0].copy()
    matrix = np.asarray(correlation, dtype=float)
    if matrix.shape != (len(lattices), len(lattices)):
        raise PlayerDistributionError(
            f"A {len(lattices)}-component market needs a "
            f"{len(lattices)}x{len(lattices)} correlation matrix; got "
            f"{matrix.shape}."
        )
    try:
        np.linalg.cholesky(matrix)
    except np.linalg.LinAlgError as error:
        raise PlayerDistributionError(
            "The residual correlation matrix for this market is not positive "
            "definite, so there is no Gaussian copula with these off-diagonals "
            f"and no joint to build:\n{matrix}"
        ) from error
    if len(lattices) > 3:
        raise PlayerDistributionError(
            "This engine couples at most three components. The four priced "
            "combination markets are pra and three pairs; a fourth dimension "
            "is `player_double_double`, which is refused by name."
        )

    # Largest support last: the final level is evaluated in closed form over the
    # whole count axis and costs no quadrature nodes, so putting the widest
    # lattice there is the cheapest arrangement. The sum is invariant to it.
    order = sorted(range(len(lattices)), key=lambda index: lattices[index].size)
    lattices = [lattices[index] for index in order]
    matrix = matrix[np.ix_(order, order)]

    cells = [_latent_cells(pmf) for pmf in lattices]
    values = [entry[0] for entry in cells]
    targets = [lattice[value] for lattice, value in zip(lattices, values)]

    split0 = _split_outer_cells(cells[0][1])
    map0 = _split_values(np.arange(values[0].size))
    u0, weight0 = _cell_nodes(split0[:-1], split0[1:], COPULA_NODES_PER_CELL)
    z0 = _latent(u0)

    if len(lattices) == 2:
        rho = float(matrix[0, 1])
        spread = math.sqrt(max(1.0 - rho * rho, 1e-300))
        conditional = np.diff(
            ndtr((cells[1][2] - rho * z0[..., None]) / spread), axis=-1
        )
        joint = _collapse(
            np.einsum("cq,cqv->cv", weight0, conditional), 0, map0, values[0].size
        )
        joint = _fit_marginals(joint, targets)
        return _accumulate(joint, values)

    rho01 = float(matrix[0, 1])
    spread1 = math.sqrt(max(1.0 - rho01 * rho01, 1e-300))
    flat0 = z0.reshape(-1)
    flat_w0 = weight0.reshape(-1)

    # Z1 | Z0 is normal with mean rho01*Z0 and sd spread1. Its cells are the
    # same z-intervals; taking the quadrature in ITS OWN probability space makes
    # each cell's weights sum to the exact conditional cell probability.
    bounds = _split_outer_cells(
        ndtr((cells[1][2] - rho01 * flat0[:, None]) / spread1)
    )
    map1 = _split_values(np.arange(values[1].size))
    v1, weight1 = _cell_nodes(bounds[..., :-1], bounds[..., 1:], COPULA_NODES_PER_CELL)
    z1 = rho01 * flat0[:, None, None] + spread1 * _latent(v1)

    # Z2 | Z0, Z1 in closed form.
    solved = np.linalg.solve(matrix[:2, :2], matrix[:2, 2])
    residual = float(matrix[2, 2] - matrix[:2, 2] @ solved)
    spread2 = math.sqrt(max(residual, 1e-300))
    flat1 = z1.reshape(flat0.size, -1)
    centre = solved[0] * flat0[:, None] + solved[1] * flat1
    cell2 = np.diff(ndtr((cells[2][2] - centre[..., None]) / spread2), axis=-1)

    combined = flat_w0[:, None] * weight1.reshape(flat0.size, -1)
    grouped = (combined[..., None] * cell2).reshape(
        map0.size,
        COPULA_NODES_PER_CELL,
        map1.size,
        COPULA_NODES_PER_CELL,
        values[2].size,
    ).sum(axis=(1, 3))
    joint = _collapse(_collapse(grouped, 0, map0, values[0].size), 1, map1, values[1].size)
    joint = _fit_marginals(joint, targets)
    return _accumulate(joint, values)


def _accumulate(joint: np.ndarray, values: Sequence[np.ndarray]) -> np.ndarray:
    """Sum the joint out onto the one axis that is wanted: the component total."""
    total = np.zeros(int(sum(value.max() for value in values)) + 1, dtype=float)
    if joint.ndim == 2:
        for row, first in enumerate(values[0]):
            np.add.at(total, values[1] + first, joint[row])
        return total
    for row, first in enumerate(values[0]):
        for column, second in enumerate(values[1]):
            np.add.at(total, values[2] + first + second, joint[row, column])
    return total


# --------------------------------------------------------------------------
# The market reader
# --------------------------------------------------------------------------


def price_line(
    pmf: np.ndarray, line: float, side: str
) -> tuple[float, float, float]:
    """`(win, push, loss)` for one rung, in this repository's one push convention.

    Mirrors `distributions.GameDistribution.total` exactly, transposed onto a
    count lattice, and for the same stated reason: *every market method returns
    (win, push, loss) summing to one, so a caller can never silently drop the
    push and re-normalise the other two*. All ten player markets carry
    `push_possible=True` and `settlement._settle_player_column` settles them as
    "the log column against the line, equality pushes" — 14 rebounds against a
    line of 14 is a returned stake, not a loss.

    The push is **exact lattice mass** at the integer, never a density and never
    an interpolation between rungs. A half-point line returns a push of exactly
    0.0 and still returns the field, because the design records 6 quotes on 3
    integer lines in the store — a branch that is live and rare, which is the
    profile of a branch that ships broken.

    The three legs are unconditional. Forming `win / (1 - push)` is a grading
    decision about what a de-vigged two-sided fair price implies, and it belongs
    to the grading commit; a reader that renormalised here would be offering a
    different bet from the one `settlement._grade_against_line` settles, which
    tests equality BEFORE the inequality precisely so a push is a decision.

    A DECLARED DEVIATION from one of the two contracts, which orders the tuple
    `(over, under, push)`. There is one push convention in this repository and
    this is it; two orderings of one triple is how a caller comes to read the
    loss leg as the push.
    """
    if side not in (OVER, UNDER):
        raise PlayerDistributionError(
            f"Unknown side {side!r}; a player prop has {OVER!r} and {UNDER!r}."
        )
    weights = np.asarray(pmf, dtype=float)
    counts = np.arange(weights.size, dtype=float)
    threshold = float(line)
    if not math.isfinite(threshold):
        raise PlayerDistributionError(f"A line of {line!r} is not a number.")
    if threshold >= weights.size - 1:
        raise MarketRefused(
            "refused: R4, line above the count lattice ceiling. This lattice "
            f"runs to {weights.size - 1} and the line is {threshold}. Returning "
            "(0, 0, 1) there would report a confident zero that is an artefact "
            "of where the lattice was truncated."
        )
    above = float(weights[counts > threshold].sum())
    push = float(weights[counts == threshold].sum())
    below = float(weights[counts < threshold].sum())
    return (above, push, below) if side == OVER else (below, push, above)


# --------------------------------------------------------------------------
# Structural checks -- report, do not tune
# --------------------------------------------------------------------------


def points_threes_correlation(
    *, mu_events: float, phi_events: float, value_pmf: Sequence[float]
) -> float:
    """`corr(points, threes)` given minutes, produced by the shared event count.

    Design 4's second free structural check. Under the thinning route both
    quantities are functions of one scoring-event count `N` and one severity
    sequence, so the correlation is an identity rather than a parameter:

        Cov         = mu_N * (3*p3      + (phi-1) * E[V] * p3)
        Var(points) = mu_N * (E[V^2]    + (phi-1) * E[V]^2)
        Var(threes) = mu_N * (p3        + (phi-1) * p3^2)

    each of them `E[N]*Var(.) + Var(N)*E[.]^2` collected with `E[N] = mu_N` and
    `Var(N) = phi*mu_N`. The middle line is the same identity the frozen file's
    `points_compound_reconciliation` is built on: divide it by
    `E[S] = mu_N*E[V]` and it is `E[V^2]/E[V] + (phi-1)*E[V]`. It is checked against the
    frozen `structural_check_targets.corr_points_threes_given_minutes` =
    0.6021705535430947, which no path here can influence — that is the point of
    the thinning route. `test_the_points_threes_correlation_identity_matches_a_
    brute_force_joint` verifies these three lines against an enumerated joint
    rather than against themselves.
    """
    mix = np.asarray(value_pmf, dtype=float)
    values = np.asarray(_SEVERITY_SUPPORT, dtype=float)
    first = float(mix @ values)
    second = float(mix @ (values * values))
    share = float(mix[2])
    excess = float(phi_events) - 1.0
    mean = float(mu_events)
    covariance = mean * (3.0 * share + excess * first * share)
    points_variance = mean * (second + excess * first * first)
    threes_variance = mean * (share + excess * share * share)
    return covariance / math.sqrt(points_variance * threes_variance)


def _moments(pmf: np.ndarray) -> tuple[float, float]:
    counts = np.arange(pmf.size, dtype=float)
    mean = float(pmf @ counts)
    variance = float(pmf @ (counts * counts)) - mean * mean
    return mean, variance


def population_structural_checks(
    population: Iterable[PlayerDistribution], *, shapes: PlayerShapes
) -> Mapping[str, float]:
    """Design 4's check (a), pooled over the POPULATION the target is defined on.

    Design 4: "the mixture must reproduce (a) the unconditional within-player
    points VMR **among regulars**, measured 2.991 (fit) / 3.024 (2023). Report
    the ratio. If (a) is off by more than 15%, the run stops and the discrepancy
    is the finding." The subject of that sentence is a population, and this is
    the function that supplies one. :meth:`PlayerDistribution.structural_checks`
    reports the same quantity for a single athlete, under a key that says so,
    and cannot be handed to :func:`assert_structural_checks` at all.

    **The defect this is arranged against**, and it is why the two are separate
    functions. `structural_check_targets.unconditional_points_vmr_regulars` is
    `pooled_vmr` over 242,634 rows of regulars: within-player sums of squares
    over `sum(n_i - 1)`, divided by the mean of every row used. One athlete's
    mixture VMR divided by that is a per-athlete number over a population
    constant, and the answer moves with the athlete's minutes rather than with
    the model — 1.1123 at the 6.73-minute bucket down to 0.8482 at the
    36.22-minute one, on the frozen file's own role priors, with the conditional
    half pinned at 2.328891545818532 throughout. See
    :data:`STRUCTURAL_CHECK_POPULATION_FLOOR` for the whole measurement.

    **What is pooled, and the one place it differs from the fitter.** The target
    weights an athlete-season by its games; a slate carries each athlete once, so
    there is no `n_i` to weight by and every athlete counts once. The shape is
    otherwise the fitter's: `mean of the produced variances / mean of the
    produced means`, a ratio of two sums and NOT the mean of the per-athlete
    ratios. The two differ — 0.9209 against 0.9440 on the regulars among the
    nine role-prior athletes — and the first is the one that matches how the
    target was built. `test_design_4s_stop_rule_is_a_population_quantity` holds
    both, so the day someone simplifies this to a mean of ratios it goes red.

    **Who is a regular is read off the frozen file, never assumed here.**
    `regular_min_projected_minutes` is 15.0 and it lives in the target's own
    evidence block, so it arrives through :meth:`PlayerShapes.evidence`. An
    athlete below it was not in the population the target was measured over and
    is counted apart rather than pooled: `population_below_regular_floor` is a
    reported census bucket, not a silent drop.

    **A regular whose points market is REFUSED is a third bucket, not a
    crash.** `player_points` is refused for a subject whenever the fit would not
    stand behind a constant the compound sum needs — `conditional_dispersion.
    points`, `conditional_dispersion.points_events`, `role_prior.points_events`
    — and asking that subject for `count_pmf("player_points")` raises
    :class:`MarketRefused`. This function pools the athletes it was handed, is
    called by `gameday_card._run_the_structural_check` outside every `except`
    the card owns, and would therefore have turned one refused prop into a dead
    card. A refused subject produced no points mixture, so he has no VMR to
    pool and pooling an absence is the one thing that must not happen: he is
    counted in `population_points_refused` and left out of both sums.

    Returns every number the caller needs to print the ratio design 4 asks to be
    reported, and the census that says whether it may stop anything. Nothing
    here raises on population size: with no regulars at all the ratio is NaN and
    `population_athletes` is 0, and :func:`assert_structural_checks` reads the
    census before it reads the ratio.
    """
    target = float(
        shapes.value("structural_check_targets")["unconditional_points_vmr_regulars"]
    )
    evidence = shapes.evidence("structural_check_targets")
    try:
        regular_floor = float(evidence["fit"]["regular_min_projected_minutes"])
    except (KeyError, TypeError) as error:
        raise PlayerDistributionError(
            f"{shapes.path}: `structural_check_targets` records no "
            "`fit.regular_min_projected_minutes`, so the population its value "
            "was measured over is not stated and nothing can be compared to it. "
            "Design 4's check (a) is about regulars; a floor invented here "
            "would be a number about the file that did not come from it."
        ) from error

    means: list[float] = []
    variances: list[float] = []
    offered = 0
    below = 0
    refused = 0
    # `population`, never `distributions`: `test_no_player_count_is_built_by_
    # match_variance` scans this module's AST for the name of the TEAM
    # distribution module and refuses it, because design 4's refusal of
    # `_match_variance` for player counts is easiest to defeat one attribute at
    # a time. A parameter that shadowed the module name would have blunted it.
    for subject in population:
        offered += 1
        if float(subject.projection.projected_minutes) < regular_floor:
            below += 1
            continue
        if "player_points" in subject.refusals:
            refused += 1
            continue
        mean, variance = _moments(subject.count_pmf("player_points"))
        means.append(mean)
        variances.append(variance)

    if means:
        pooled_mean = float(np.mean(means))
        pooled_variance = float(np.mean(variances))
        produced = pooled_variance / pooled_mean if pooled_mean > 0.0 else float("nan")
    else:
        produced = float("nan")

    return {
        "unconditional_points_vmr": produced,
        "unconditional_points_vmr_target": target,
        "unconditional_points_vmr_ratio": produced / target,
        "population_athletes": float(len(means)),
        "population_athletes_offered": float(offered),
        "population_below_regular_floor": float(below),
        "population_points_refused": float(refused),
        "regular_min_projected_minutes": regular_floor,
        "population_floor": float(STRUCTURAL_CHECK_POPULATION_FLOOR),
    }


def assert_structural_checks(checks: Mapping[str, float]) -> None:
    """Design 4's stop rule, and it is the only one there is.

    "If (a) is off by more than 15%, the run stops and the discrepancy is the
    finding." Nothing is tuned when this fires: no constant here is refitted, no
    tolerance is widened and no market is dropped. The other four targets in
    `structural_check_targets` carry no declared tolerance anywhere in the design
    or the frozen file, so they are reported and cannot stop anything —
    including the narrowness of the thinned three-point marginal, which is the
    known price of :data:`POINTS_EVENT_DISPERSION_KEY` — 5.9105% at the league
    `value_pmf` and 5.14% at the fixture athlete's own mix, because it runs
    through his three-point share and not through anything the model chose.

    **It takes a population and refuses to take anything else.** The census keys
    below exist only on a mapping :func:`population_structural_checks` built, so
    a single athlete's :meth:`PlayerDistribution.structural_checks` cannot reach
    the tolerance by accident — it does not carry a key called
    `unconditional_points_vmr_ratio` at all. That is the whole repair: the
    tolerance is unchanged and the quantity it is applied to is now the one
    design 4's sentence names.

    **Below the floor it does not stop, and it does not pass either.** Fewer
    than :data:`STRUCTURAL_CHECK_POPULATION_FLOOR` regulars is the per-athlete
    comparison wearing a population's name, which is the defect, so the check
    reports instead of stopping and the caller says so — `gameday_card`'s
    `OpinionCensus.structural_check_line`. Widening the tolerance to make a
    small population pass would be the one move this function exists to prevent.
    """
    for required in (
        "unconditional_points_vmr_ratio",
        "population_athletes",
        "population_floor",
    ):
        if required not in checks:
            raise PlayerDistributionError(
                "Design 4's check (a) is a POPULATION quantity — the pooled "
                "within-player points VMR among regulars — and this mapping "
                f"carries no {required!r}, so it is not one. Build it with "
                "`population_structural_checks(population, shapes=shapes)`. "
                "A single athlete's `structural_checks()` reports "
                "`unconditional_points_vmr_ratio_this_athlete`, which moves "
                "with his minutes rather than with the model and is not the "
                "thing design 4 stops on."
            )
    athletes = int(checks["population_athletes"])
    floor = int(checks["population_floor"])
    if athletes < floor:
        return
    ratio = float(checks["unconditional_points_vmr_ratio"])
    if not math.isfinite(ratio) or abs(ratio - 1.0) > UNCONDITIONAL_POINTS_VMR_STOP:
        raise StructuralCheckFailed(
            "The assembled mixture reproduces an unconditional points "
            f"variance-to-mean of {checks['unconditional_points_vmr']:.6f} "
            f"against the frozen target "
            f"{checks['unconditional_points_vmr_target']:.6f}, a ratio of "
            f"{ratio:.4f}. Design 4 stops the run outside "
            f"{UNCONDITIONAL_POINTS_VMR_STOP:.0%} and the discrepancy is the "
            "finding. Nothing is tuned to close it. Pooled over the "
            f"{athletes:,} regular athlete(s) this run priced, at or above "
            f"{checks['regular_min_projected_minutes']:.1f} projected minutes."
        )


def held_out_panjer_families(shapes: PlayerShapes) -> Mapping[str, str]:
    """Which member the HELD-OUT dispersions select, for printing beside the fit.

    The one function in this module that touches `held_out_value`, and it prices
    nothing: `player_shapes` records that the holdout is a check and a model that
    reaches for it has spent it. It exists so the binomial arm can be shown to be
    the arm on both windows — turnovers reads 0.9828561088984643 on the fit and
    0.9978708188334368 held out, and both are binomial.
    """
    held = shapes.held_out_value("conditional_dispersion")
    return {stat: panjer_family(float(value)) for stat, value in held.items()}


# --------------------------------------------------------------------------
# The object
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class PlayerDistribution:
    """One cached object per (event, athlete); the ten markets are ten questions.

    Design 2's rule made structural: "one cached `PlayerDistribution` per
    (event_id, athlete_id) so a player's points, threes, pra and points_rebounds
    rungs are six questions asked of one object". The single markets and the
    combination markets take their component pmfs from the same per-node arrays,
    and that — not an assertion — is what makes "a points line and a pra line on
    one player cannot disagree" true.

    `projection` is the estimator's output, unchanged. Nothing here re-shrinks a
    rate, re-tilts a mix or re-reads a file.
    """

    projection: PlayerProjection
    minutes: np.ndarray
    minutes_weight: np.ndarray
    event_parameters: Mapping[int, PanjerParameters]
    stat_parameters: Mapping[str, Mapping[int, PanjerParameters]]
    severity: np.ndarray
    ceilings: Mapping[str, int]
    correlations: Mapping[str, float]
    dispersions: Mapping[str, float]
    targets: Mapping[str, float]
    reconciliation: Mapping[str, float]
    refusals: Mapping[str, str]
    construction_order: tuple[str, ...] = CONSTRUCTION_ORDER
    _cache: dict = field(default_factory=dict, repr=False, compare=False)

    # -- components --------------------------------------------------------

    def _threes_parameters(self, node: int) -> PanjerParameters:
        """The thinned family the three-point count at `node` is actually built from.

        `thin(event_parameters[node], p3)`, and it is a method rather than an
        expression written twice because two readers need the SAME object:
        :meth:`node_component_pmf` builds the count from it and
        :meth:`phi_conditional` reports its width in design 9's column. Those
        two were separate expressions until this commit and they disagreed —
        the column carried the un-thinned event dispersion for a count nothing
        had built at that width. One construction is what makes the column and
        the lattice the same claim rather than two claims that happen to be
        maintained together.

        `p3` is `severity[3]`, the athlete's own shrunk three-point share, and
        the thinned dispersion `1 + p3*(phi_events - 1)` therefore moves with
        the athlete and not with the node: it is 1.0288960137061232 at this
        fixture's 0.2727822483104362 on all 45 nodes, because `thin` scales
        `beta` and `beta` is `phi - 1` at every node.
        """
        return thin(self.event_parameters[node], float(self.severity[3]))

    def node_component_pmf(self, stat: str, node: int) -> np.ndarray:
        """`P(stat = k | m)` at one minutes node — stage 2 of the order.

        Exposed because design 5's ordering rule is only worth having if it can
        be checked: a test that cannot see the per-node objects can only read the
        order off a comment.
        """
        key = ("component", stat, int(node))
        if key not in self._cache:
            size = self.ceilings[stat]
            if stat == "points":
                pmf = compound_pmf(
                    self.event_parameters[node], severity=self.severity, size=size
                )
            elif stat == "threes":
                pmf = compound_pmf(
                    self._threes_parameters(node), severity=(0.0, 1.0), size=size
                )
            else:
                pmf = compound_pmf(
                    self.stat_parameters[stat][node], severity=(0.0, 1.0), size=size
                )
            self._cache[key] = _trim(pmf)
        return self._cache[key]

    def node_market_pmf(self, market_key: str, node: int) -> np.ndarray:
        """`P(market = k | m)` — stages 2, 3 and 4, still inside the node.

        The copula lives here and nowhere else. `residual_correlation`'s
        provenance in the frozen file is "residuals within (season, athlete,
        realised minute)", so it is a coupling measured GIVEN the realised
        minute; applying it after the mixture would re-impose a dependence the
        mixture has already produced, which is the failure design 5 quantifies
        as "pra ~15% too wide".
        """
        components = self._components(market_key)
        key = ("market", market_key, int(node))
        if key not in self._cache:
            pmfs = [self.node_component_pmf(stat, node) for stat in components]
            self._cache[key] = coupled_sum_pmf(
                pmfs, self._correlation_matrix(components)
            )
        return self._cache[key]

    def count_pmf(self, market_key: str) -> np.ndarray:
        """`P(market = k)` — stage 5, the mixture over the minutes lattice.

            P(X = k) = sum_{m=1..45} P(M = m) * P(X = k | m)

        The marginal overdispersion and the cross-stat correlation are
        **produced** by this line, not fitted: no combination market has a rate,
        a role prior, a credibility constant or a dispersion anywhere in the
        frozen file, and design 8 says combination dispersions are "derived from
        the joint, never fitted". A fitted pra dispersion appearing later is a
        defect, not an improvement.
        """
        key = ("mixed", market_key)
        if key not in self._cache:
            self._cache[key] = self._mix(
                [self.node_market_pmf(market_key, node) for node in range(self.minutes.size)]
            )
        return self._cache[key]

    def component_pmf(self, stat: str) -> np.ndarray:
        """One component's own marginal, mixed over minutes.

        Not used to build any combination market — that would be the minutes
        channel applied twice — and exposed so the test which proves it can
        construct the wrong order from public parts rather than from a private
        copy of the right one.
        """
        key = ("mixed_component", stat)
        if key not in self._cache:
            self._cache[key] = self._mix(
                [
                    self.node_component_pmf(stat, node)
                    for node in range(self.minutes.size)
                ]
            )
        return self._cache[key]

    # -- market reading ----------------------------------------------------

    def mean(self, market_key: str) -> float:
        """The PRICE mean: the first moment of the pmf this engine actually made.

        For points and threes this is **not** `player_rates.mean_for_market`.
        The estimator's route is `rates["points"] * minutes`; the price is
        `rates["points_events"] * minutes * E[V_player]`, and `player_rates`'
        own comment says which is which ("the compound is the price and
        `rates['points']` is the check"). The gap between them is stored by
        :meth:`diagnostics` as a descriptive column and is never asserted to
        zero and never used to tune: asserting it would force one route to be
        fitted to the other, and both are frozen.
        """
        return _moments(self.count_pmf(market_key))[0]

    def market(
        self, market_key: str, line: float, side: str
    ) -> tuple[float, float, float]:
        """`(win, push, loss)` for one rung of one market off this object."""
        return price_line(self.count_pmf(market_key), line, side)

    def ladder(
        self, lines: Iterable[float], *, market_key: str, side: str
    ) -> list[tuple[float, tuple[float, float, float]]]:
        """Every rung, off this object and no other.

        `distributions.GameDistribution.ladder`'s rule, quoted: there is no
        separate alternate-ladder model in this repository and there must never
        be one. The football lab had two and shipped a ladder whose -6.5 was
        better value than its -7.5.
        """
        pmf = self.count_pmf(market_key)
        return [(float(line), price_line(pmf, line, side)) for line in lines]

    def phi_conditional(self, market_key: str) -> float:
        """The dispersion the family that made THIS count was carrying.

        Design 9's column, and there are three cases because the engine has
        three constructions.

        * **The four plain Panjer stats** carry the frozen conditional
          dispersion with the binomial's integer-`n` rounding already in it:
          `player_turnovers` reads 0.9828493167608962 against a frozen
          0.9828561088984643, and the three negative-binomial stats read the
          frozen constant exactly.
        * **`player_points`** carries the shared scoring-event count's
          dispersion, 1.1059306970490195 out of
          `points_compound_reconciliation[POINTS_EVENT_DISPERSION_KEY]`,
          because a compound sum is handed no dispersion of its own — the phi
          goes to the event count and the sum's width is PRODUCED
          (2.4750752387725523 at this fixture's price node, against a frozen
          `conditional_dispersion["points"]` of 2.328891545818532).
          :meth:`structural_checks` is where the produced width is reported.
        * **`player_threes` carries the THINNED dispersion**,
          `1 + p3*(phi_events - 1)`, read off the same
          :meth:`_threes_parameters` call :meth:`node_component_pmf` builds the
          count from. On this fixture that is 1.0288960137061232 at a
          three-point share of 0.2727822483104362, and it is what the lattice
          is: the produced `threes_vmr_given_minutes` reads
          1.0288960135790235, 1.27e-10 below it, and the whole gap is
          count-lattice truncation.

        **The defect the third case is arranged against.** Until this commit
        `player_threes` returned the UN-THINNED 1.1059306970490195 — the same
        cell as `player_points`, for a count nothing ever built at that width.
        The thinning is the reason threes falls out of the points object at
        all, so a column that ignores it names a distribution this engine did
        not price, and names it in the wrong DIRECTION: a reader reconciling
        that cell against `conditional_dispersion["threes"]` =
        1.0846864899201918 read the three-point marginal as 1.96% wide when
        the marginal actually priced is 5.14% narrow. That 5.14% is this
        athlete's and moves with his own three-point share — at the league
        `value_pmf`'s 0.19423721541072833 it is the 5.91% recorded at
        :data:`POINTS_EVENT_DISPERSION_KEY`. The old behaviour was DISCLOSED,
        in the body of this docstring, and that is exactly what made it worth
        repairing rather than re-declaring: the summary line said "the
        dispersion actually handed to the family that made this count", which
        was true of nine markets and false of the tenth, and a convention that
        contradicts its own summary line is not a decision anybody took.

        **NaN for the four combination markets, deliberately.** No phi is handed
        to a sum: its width is produced by the components, the copula and the
        mixture, and writing a number in this column for pra would be inventing
        a parameter that does not exist.
        """
        components = self._components(market_key)
        if len(components) > 1:
            return float("nan")
        stat = components[0]
        if stat == "threes":
            return float(self._threes_parameters(self.price_node()).phi_used)
        if stat in COMPOUND_STATS:
            return float(self.dispersions["points_event_dispersion_used"])
        return float(self.stat_parameters[stat][self.price_node()].phi_used)

    def void_probability(self) -> float:
        """Design 9's stored column: `dnp_probability`, carried and not used.

        The bucket base rate, unshrunk, exactly as the estimator produced it.
        It is a diagnostic and it is multiplied into nothing: the minutes lattice
        carries exactly zero mass at zero minutes, so the priced quantity is
        already conditional on the wager standing, and discounting it again by
        the chance of a void that pays nothing back would be wrong twice.

        The two contracts disagree about this column — one says it is
        `dnp_probability` verbatim, the other proposes
        `push_mass + (1-push_mass)*dnp_probability`. This implements the first,
        because the second composes a number out of a quantity that may never go
        near a price and one that already is one, and reports the disagreement
        rather than deciding it silently.
        """
        return float(self.projection.dnp_probability)

    # -- checks and diagnostics -------------------------------------------

    def structural_checks(self) -> Mapping[str, float]:
        """What THIS athlete's assembled mixture reproduces, against what was frozen.

        Report, never tune. Design 4 gives two free checks and a tolerance for
        exactly one of them; `structural_check_targets`' own note says these are
        "not parameters ... what the assembled mixture has to reproduce with
        nothing tuned to them".

        **Nothing here can stop a run, including the unconditional points VMR.**
        The key that carries it is `unconditional_points_vmr_ratio_this_athlete`
        and the suffix is load-bearing: the frozen target is pooled over 242,634
        rows of regulars, so one athlete's ratio to it is two different objects
        divided, and it moves with his minutes rather than with the model —
        1.1123 at the 6.73-minute role prior down to 0.8482 at the 36.22-minute
        one, with the conditional half pinned at 2.328891545818532 throughout.
        Design 4's stop is :func:`assert_structural_checks` over
        :func:`population_structural_checks`, and it cannot be handed this
        mapping because this mapping has no `unconditional_points_vmr_ratio`.
        The per-athlete number is still worth printing — it is the design's
        "report the ratio" for one subject — which is why it is here at all.
        """
        points = self.count_pmf("player_points")
        mean, variance = _moments(points)
        target = float(self.targets["unconditional_points_vmr_regulars"])
        produced = variance / mean

        node = self.price_node()
        conditional_mean, conditional_variance = _moments(
            self.node_component_pmf("points", node)
        )
        threes_mean, threes_variance = _moments(
            self.node_component_pmf("threes", node)
        )
        correlation = points_threes_correlation(
            mu_events=self.event_parameters[node].mu,
            phi_events=self.event_parameters[node].phi_used,
            value_pmf=self.severity[1:4],
        )
        return {
            "unconditional_points_vmr": produced,
            "unconditional_points_vmr_target": target,
            # NOT `unconditional_points_vmr_ratio`. See the docstring: the
            # target is a population and this is one athlete, so the name says
            # so and `assert_structural_checks` cannot read it.
            "unconditional_points_vmr_ratio_this_athlete": produced / target,
            "points_vmr_given_minutes": conditional_variance / conditional_mean,
            "points_vmr_given_minutes_target": float(
                self.targets["points_vmr_given_minutes"]
            ),
            "threes_vmr_given_minutes": threes_variance / threes_mean,
            "threes_vmr_given_minutes_target": float(self.dispersions["threes"]),
            "corr_points_threes_given_minutes": correlation,
            "corr_points_threes_given_minutes_target": float(
                self.targets["corr_points_threes_given_minutes"]
            ),
            "checked_at_minutes": float(self.minutes[node]),
            "measured_event_dispersion": float(
                self.reconciliation["measured_event_dispersion"]
            ),
            "effective_event_dispersion": float(
                self.reconciliation["effective_event_dispersion"]
            ),
            "compound_overstatement": float(
                self.reconciliation["compound_overstatement"]
            ),
        }

    def realised_correlations(self, node: int | None = None) -> Mapping[str, tuple[float, float]]:
        """`{pair: (target, realised)}` for the copula, at one minutes node.

        **Report, never tune.** The copula parameter is set equal to the
        measured Pearson correlation OF THE COUNTS, and a Gaussian copula's
        latent correlation is not that object: discretising the latent normals
        onto integer counts always loses a little of it. Measured on the test
        fixture at its modal node, `points|rebounds` is asked for
        0.10523131793586692 and realises 0.10333 — 1.8% low. Solving the latent
        parameter back onto the target would be fitting a constant at price
        time, and it is not done.

        The realised number is read off the coupled PAIR sum through
        `Cov = (Var(X+Y) - Var(X) - Var(Y)) / 2`, so it is the coupling the
        engine actually applied and not a second calculation of what it
        intended to apply.
        """
        index = self.price_node() if node is None else int(node)
        out: dict[str, tuple[float, float]] = {}
        for market, components in MARKET_COMPONENTS.items():
            if len(components) != 2 or market in self.refusals:
                continue
            first, second = components
            pmfs = [self.node_component_pmf(stat, index) for stat in components]
            variances = [_moments(pmf)[1] for pmf in pmfs]
            matrix = self._correlation_matrix(components)
            joined = coupled_sum_pmf(pmfs, matrix)
            covariance = (_moments(joined)[1] - variances[0] - variances[1]) / 2.0
            out[f"{first}|{second}"] = (
                float(matrix[0, 1]),
                covariance / math.sqrt(variances[0] * variances[1]),
            )
        return out

    def diagnostics(self) -> Mapping[str, float]:
        """Descriptive columns that may never become a finding.

        The two mean-route gaps live here. `player_rates.mean_for_market`
        returns `rates["points"] * minutes` and this engine prices
        `rates["points_events"] * minutes * E[V_player]`; the same split exists
        for threes. Both routes are frozen, neither is tuned to the other, and
        design 12 registers them descriptive-only. They are stored so a later
        session inherits the evidence rather than the temptation.
        """
        minutes = float(self.projection.projected_minutes)
        rates = self.projection.rates
        gaps: dict[str, float] = {}
        for stat, market in (("points", "player_points"), ("threes", "player_threes")):
            check = float(rates[stat]) * minutes
            price = self.mean(market)
            gaps[f"{stat}_mean_check"] = check
            gaps[f"{stat}_mean_price"] = price
            gaps[f"{stat}_mean_relative_gap"] = (price - check) / check
        gaps["void_probability"] = self.void_probability()
        return gaps

    # -- internals ---------------------------------------------------------

    def price_node(self) -> int:
        """The minutes node design 9's per-row columns are quoted at.

        The modal node of the minutes lattice. A row of `cbb_player_lines.csv`
        has one `phi_conditional` cell and the conditional dispersion of a
        binomial moves with the mean through the integer-`n` rounding, so the
        column has to name a node; the mode is the one the lattice puts the most
        weight on. The pmf itself is the mixture over every node and does not
        depend on this choice.
        """
        return int(np.argmax(self.minutes_weight))

    def _components(self, market_key: str) -> tuple[str, ...]:
        if market_key in MARKETS_REFUSED_BY_NAME:
            raise MarketRefused(MARKETS_REFUSED_BY_NAME[market_key])
        if market_key in self.refusals:
            raise MarketRefused(self.refusals[market_key])
        components = MARKET_COMPONENTS.get(market_key)
        if components is None:
            raise PlayerDistributionError(
                f"{market_key!r} is not one of the ten markets this model is "
                f"registered against: {', '.join(MARKET_COMPONENTS)}. It is not "
                "refused by name either, so it is a key nothing here has an "
                "opinion about."
            )
        return components

    def _correlation_matrix(self, components: Sequence[str]) -> np.ndarray:
        size = len(components)
        matrix = np.eye(size)
        for i in range(size):
            for j in range(i + 1, size):
                first, second = components[i], components[j]
                # The frozen file spells each pair once. Reading it under one
                # spelling only would make the matrix depend on the order
                # `MARKET_COMPONENTS` happens to list a market's components in.
                if f"{first}|{second}" in self.correlations:
                    rho = self.correlations[f"{first}|{second}"]
                elif f"{second}|{first}" in self.correlations:
                    rho = self.correlations[f"{second}|{first}"]
                else:
                    raise PlayerDistributionError(
                        f"The frozen residual correlation carries no entry for "
                        f"{first!r} with {second!r}, under either spelling. A "
                        "combination market cannot be coupled on a number that "
                        "is not there, and substituting zero would assert "
                        "conditional independence the fit never measured."
                    )
                matrix[i, j] = matrix[j, i] = float(rho)
        return matrix

    def _mix(self, per_node: Sequence[np.ndarray]) -> np.ndarray:
        length = max(pmf.size for pmf in per_node)
        mixed = np.zeros(length, dtype=float)
        for weight, pmf in zip(self.minutes_weight, per_node):
            mixed[: pmf.size] += weight * pmf
        return mixed


# --------------------------------------------------------------------------
# Construction
# --------------------------------------------------------------------------


def _refused_constants(shapes: PlayerShapes) -> dict[str, str]:
    """Market-level refusals owed to a constant the fit would not invent.

    `player_rates._unfittable` reads `role_prior` and `rate_shrinkage_k` only.
    The five constants this module reads are unchecked anywhere else, so a fit
    that recorded one of them unfittable would otherwise reach a price through
    here. The refusal is the file's own sentence, from `shapes.refusal_for`, not
    a sentence written in this module.
    """
    shared = [
        reason
        for reason in (shapes.refusal_for(name) for name in _CONSTANTS_READ_HERE)
        if reason
    ]
    refusals: dict[str, str] = {}
    for market, components in MARKET_COMPONENTS.items():
        reasons = list(shared)
        for stat in components:
            names = [f"conditional_dispersion.{stat}"]
            if stat in COMPOUND_STATS:
                names += [
                    "conditional_dispersion.points_events",
                    "points_compound_reconciliation",
                ]
            for name in names:
                reason = shapes.refusal_for(name)
                if reason and reason not in reasons:
                    reasons.append(reason)
        if reasons:
            refusals[market] = " ".join(reasons)
    return refusals


def _materiality_floor(shapes: PlayerShapes) -> float:
    """`conditional_dispersion.material_absolute`, and it comes from the file.

    The floor :func:`panjer_parameters` checks the binomial rounding against.
    It is read here, from the constant whose dispersions do the rounding, and
    handed down as an argument, because a floor written into this module would
    be a number about the file that did not come from it — the same rule
    :func:`population_structural_checks` follows for
    `regular_min_projected_minutes`, and the reason both are arguments rather
    than constants.

    It is deliberately NOT the same object as :data:`POISSON_BAND`, which the
    module docstring spends a paragraph refusing to set to this number: 0.02 is
    the fit's floor for **agreement between two windows**, which is the right
    scale for "did the rounding move the dispersion materially" and the wrong
    scale entirely for "is this dispersion equal to one", where it would swallow
    the frozen turnovers phi and delete the binomial arm.

    `material_absolute` sits beside `value` on the constant rather than inside
    it, so it is read off the constant block; the refusal is asked for first,
    because a floor taken from a constant the fit would not stand behind is not
    a floor either.
    """
    refusal = shapes.refusal_for("conditional_dispersion")
    if refusal:
        raise MarketRefused(refusal)
    try:
        floor = float(shapes.constants["conditional_dispersion"]["material_absolute"])
    except (KeyError, TypeError, ValueError) as error:
        raise PlayerDistributionError(
            f"{shapes.path}: `conditional_dispersion` records no readable "
            "`material_absolute`, so the fit's own materiality floor is not "
            "stated and the binomial rounding has nothing to be checked "
            "against. A floor invented here would be a number about the file "
            "that did not come from it."
        ) from error
    return floor


def _minutes_lattice_length(shapes: PlayerShapes) -> int:
    """How long a minutes pmf must be, read off `declared.minutes_support`.

    `high + 1`, because the lattice is indexed BY minutes with a 0.0 prepended:
    a support of [1, 45] is a 46-long array whose index 45 is the 45-minute
    rung. The arithmetic is the only thing declared here; the number is not.

    **The defect this is arranged against is a third copy.** This was
    `_MINUTES_LATTICE_LENGTH = 46`, a literal, and 46 is a restatement of the
    frozen file's `declared.minutes_support` = [1, 45] that was neither derived
    from it nor asserted against it. `player_rates` declares the same support as
    `MINUTES_SUPPORT` and holds it against the file in `_assert_declared_agrees`
    at price time, so those two provably cannot drift; this module's copy could,
    and silently. A refit widening the support to [1, 48] — the obvious response
    to the file's own `declared.overtime_is_included` caveat, which says
    multi-overtime nights are folded onto 45 rather than dropped — would update
    the file and `player_rates` together, pass `_assert_declared_agrees`, and
    hand this function 49-long lattices; :func:`build` would then refuse every
    athlete with a message naming neither the frozen file nor the constant that
    moved, and every prop on every card would decline. It failed closed, which
    is why nothing caught it, and it defeated the single-source rule the
    `declared` block exists for.

    The AST scan in
    `test_every_constant_comes_from_the_frozen_file_through_the_loader` could
    not have caught it either, twice over: it only collects numbers under
    `document["constants"]` and the support lives under `document["declared"]`,
    and it drops whole numbers on purpose because a frozen 4 is not a
    fingerprint of anything.

    Raises rather than defaulting. A file with no readable support is a file
    this engine cannot index a lattice against, and a default of 46 here would
    be exactly the copy this function exists to delete.
    """
    declared = shapes.document.get("declared") or {}
    support = declared.get("minutes_support")
    try:
        low, high = int(support[0]), int(support[1])  # type: ignore[index]
    except (TypeError, ValueError, KeyError, IndexError) as error:
        raise PlayerDistributionError(
            f"{shapes.path}: the `declared` block states no readable "
            f"`minutes_support` (it reads {support!r}), so the length a minutes "
            "lattice must have is not declared anywhere this engine can see. "
            "A length written into this module would be a number about the "
            "file that did not come from it."
        ) from error
    if low != 1 or high < low:
        raise PlayerDistributionError(
            f"{shapes.path}: `declared.minutes_support` is [{low}, {high}]. The "
            "lattice index IS the number of minutes and index 0 is the void "
            "rung the book pays back, so the support must start at 1 and run "
            "upward; a support starting elsewhere renumbers every rung."
        )
    return high + 1


def _refused_stats(shapes: PlayerShapes, projection: PlayerProjection) -> set[str]:
    """Which of the seven stats no family may be built for.

    R5 at engine level. `player_rates` already carries the two constants IT
    reads as `projection.refused_stats`; this adds the per-stat entries under
    the dispersion constant, which nothing upstream looks at.
    """
    refused = set(projection.refused_stats)
    for stat in (*PANJER_STATS, *COMPOUND_STATS, "points_events"):
        if shapes.refusal_for(f"conditional_dispersion.{stat}"):
            refused.add(stat)
    return refused


def build(projection: PlayerProjection, *, shapes: PlayerShapes) -> PlayerDistribution:
    """The cached object for one (event, athlete), in design 5's fixed order.

    Every constant arrives through `shapes`, which means the walk-forward guard
    in `player_shapes.load_player_shapes` has already refused any of them whose
    fit window reaches the priced season. This function opens no file, holds no
    module-level frame and never sees a settled outcome; it reads exactly the
    fields of `projection` that design 9 says it may, and never
    `dnp_probability` into anything but a stored column.

    What it refuses, before it builds anything:

    * a projection that is not `priceable` — its `unpriceable_reason` stands and
      this engine does not get a second opinion about it;
    * a minutes lattice that is not 46 long, does not sum to one, or carries any
      mass at all at zero minutes (D4). The estimator guarantees the last of
      these; a guarantee whose consumer does not check it is a comment, and this
      is the one property that makes the priced quantity `P(· | the wager
      stands)`;
    * a market whose stat the fit recorded unfittable (R5), in the fit's own
      words — **including `points_events`, which is a stat no market names.**
      `points` and `threes` are both read off the scoring-event count, so an R5
      refusal of `role_prior.points_events` or `rate_shrinkage_k.points_events`
      refuses the five markets that need it. Until this commit it did not: the
      refusal loop only asked about a market's own components, `points_events`
      is a component of none of the ten, and `player_rates._rates` drops a
      refused stat from `projection.rates` — so `rates["points_events"]` was
      read unconditionally two statements later and the fit's deliberate
      refusal came out as `KeyError('points_events')`. `KeyError` is not a
      `ValueError`, so neither `except` clause in
      `reports/gameday_card.opinions_for` caught it and one refused prop killed
      the whole card, every spread and total on the slate with it. Reproduced
      through the real loader on both keys before the repair, and
      `test_an_r5_refusal_of_the_scoring_event_count_refuses_instead_of_crashing`
      holds it from both ends.
    """
    if not projection.priceable:
        raise PlayerDistributionError(
            "This projection is not priceable and its own sentence stands: "
            f"{projection.unpriceable_reason or 'no reason was recorded'}. A "
            "distribution engine is not a second opinion about a refusal."
        )
    lattice = np.asarray(projection.minutes_pmf, dtype=float)
    required = _minutes_lattice_length(shapes)
    if lattice.size != required:
        raise PlayerDistributionError(
            f"The minutes lattice is {lattice.size} long and the index is the "
            f"number of minutes, so it must be {required} — "
            f"{shapes.path} declares `minutes_support` "
            f"{list(shapes.document.get('declared', {}).get('minutes_support', []))}. "
            "A support that moved would silently renumber every rung."
        )
    if lattice[0] != 0.0:
        raise PlayerDistributionError(
            f"The minutes lattice carries {lattice[0]!r} at zero minutes. The "
            "book VOIDS a did-not-play, so the priced quantity is "
            "`P(stat > line | the wager stands)`; mass at zero minutes would "
            "discount every price by the chance of a void that pays nothing "
            "back. Exactly zero, not nearly."
        )
    if not math.isclose(float(lattice.sum()), 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise PlayerDistributionError(
            f"The minutes lattice sums to {float(lattice.sum())!r}, which is "
            "not a pmf."
        )

    # R5 first, and before any `shapes.value` call: `value` RAISES on a constant
    # the fit recorded unfittable, and a raise is not a refusal. The caller has
    # to be handed the fit's own sentence, so the refusals are collected while
    # asking `refusal_for` and only then are the surviving constants read.
    refusals = _refused_constants(shapes)
    refused_stats = _refused_stats(shapes, projection)
    for market, components in MARKET_COMPONENTS.items():
        # The scoring-event count is an INPUT of every compound market without
        # being a component of any: `points` is the compound sum over it and
        # `threes` is the same count thinned. `player_rates._unfittable` reads
        # `role_prior.<stat>` and `rate_shrinkage_k.<stat>` for all seven stats,
        # `points_events` among them, so `projection.refused_stats` can carry a
        # refusal that no market's component list mentions. Asking only about
        # components left those five markets unrefused and then priced them off
        # a rate that had been dropped from `projection.rates`.
        needed = list(components)
        if any(stat in COMPOUND_STATS for stat in components):
            needed.append("points_events")
        reasons: list[str] = []
        for stat in needed:
            reason = projection.refused_stats.get(stat)
            if reason and reason not in reasons:
                reasons.append(reason)
        if reasons:
            refusals[market] = " ".join(
                [refusals[market]] + reasons if market in refusals else reasons
            )
    if len(refusals) == len(MARKET_COMPONENTS):
        raise MarketRefused(
            "refused: every one of the ten markets. "
            + " ".join(sorted(set(refusals.values())))
        )

    dispersions = dict(shapes.value("conditional_dispersion"))
    materiality = _materiality_floor(shapes)
    reconciliation = dict(shapes.value("points_compound_reconciliation"))
    correlations = dict(shapes.value("residual_correlation"))
    targets = dict(shapes.value("structural_check_targets"))
    league_mix = shapes.value("value_pmf")
    # Read so a refusal on it is seen here even though the shrinkage itself
    # happened upstream: `player_rates.shrink_value_mix` consumed it, and a
    # constant the fit refused must not reach a price through either module.
    shapes.value("value_mix_shrinkage_events")
    if len(league_mix) != 3:
        raise PlayerDistributionError(
            f"{shapes.path}: the league value pmf is {league_mix}, which is not "
            "a three-point pmf. A scoring event is worth one, two or three "
            "points and nothing else."
        )

    event_dispersion = float(reconciliation[POINTS_EVENT_DISPERSION_KEY])
    dispersions["points_event_dispersion_used"] = event_dispersion

    severity = np.zeros(4, dtype=float)
    severity[1:] = np.asarray(projection.value_pmf, dtype=float)
    if not math.isclose(float(severity.sum()), 1.0, rel_tol=0.0, abs_tol=1e-9):
        raise PlayerDistributionError(
            f"The athlete's value mix {projection.value_pmf} is not a pmf."
        )

    nodes = np.flatnonzero(lattice > 0.0)
    minutes = nodes.astype(float)
    weights = lattice[nodes]
    rates = projection.rates

    # Stage 1 of CONSTRUCTION_ORDER is the lattice above; stage 2 is every
    # family below, one per minutes node, at the CONDITIONAL dispersion.
    #
    # `points_events` is read only after the refusal set has been consulted. A
    # stat the fit refused has no entry in `projection.rates` at all, so the
    # guard is what makes the refusal a refusal rather than a `KeyError`; the
    # five markets that need the count are already in `refusals` above, and the
    # other five are priced from their own rates as usual.
    event_parameters = (
        {}
        if "points_events" in refused_stats
        else {
            index: panjer_parameters(
                mu=float(rates["points_events"]) * float(node),
                phi=event_dispersion,
                materiality=materiality,
            )
            for index, node in enumerate(minutes)
        }
    )
    stat_parameters = {
        stat: {
            index: panjer_parameters(
                mu=float(rates[stat]) * float(node),
                phi=float(dispersions[stat]),
                materiality=materiality,
            )
            for index, node in enumerate(minutes)
        }
        for stat in PANJER_STATS
        if stat not in refused_stats
    }

    highest = int(np.argmax(minutes))
    ceilings: dict[str, int] = {}
    if "points" not in refused_stats and "points_events" not in refused_stats:
        ceilings["points"] = count_lattice_ceiling(
            event_parameters[highest], severity=severity
        )
    if "threes" not in refused_stats and "points_events" not in refused_stats:
        ceilings["threes"] = count_lattice_ceiling(
            thin(event_parameters[highest], float(severity[3])), severity=(0.0, 1.0)
        )
    for stat, table in stat_parameters.items():
        ceilings[stat] = count_lattice_ceiling(table[highest], severity=(0.0, 1.0))

    return PlayerDistribution(
        projection=projection,
        minutes=minutes,
        minutes_weight=weights,
        event_parameters=event_parameters,
        stat_parameters=stat_parameters,
        severity=severity,
        ceilings=ceilings,
        correlations=correlations,
        dispersions=dispersions,
        targets=targets,
        reconciliation=reconciliation,
        refusals=refusals,
    )
