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

Two constants this engine needs have no counterpart in
`data/processed/cbb_player_shapes.json`. Neither is invented as a fitted number;
both are declared as structural, with the reason written down and a test that
goes red if either is quietly turned into a fit:

* :data:`POISSON_BAND` — design 4 says "VMR = 1 -> Poisson", which never happens
  in floating point. It MUST NOT be set to
  `conditional_dispersion.material_absolute` = 0.02, because the frozen
  turnovers phi is 0.9828561088984643, i.e. 0.0171 from 1, and a 0.02 band would
  swallow the binomial branch entirely and delete the only case design 4 says
  the binomial exists for.
* :data:`COUNT_LATTICE_HARD_CAP` — R4 refuses a mean "above the lattice
  ceiling" and the frozen file declares `minutes_support` and no count ceiling
  for any of the seven stats, so R4's upper half was unenforced. It is enforced
  here, from a declared tail tolerance and a structural cap.

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
    within-player points VMR, and only outside +/-15%. Nothing else in design 4
    or in `structural_check_targets` declares a tolerance, so nothing else here
    can stop a run — the rest are reported.
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
#: measurement that fixes them.
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
#: 0.7240159. Feeding `measured_event_dispersion` produces a conditional points
#: VMR of 2.8377415929483303 and therefore an unconditional 3.5617575, a ratio
#: of 1.1667 against the frozen target — over design 4's own 15% stop. Feeding
#: `effective_event_dispersion` produces 2.328891545818532 and a ratio of
#: 1.0000. The file's stated mechanism for the gap is that free throws arrive in
#: pairs, so two made free throws are one trip charged as two independent
#: severity draws: exchangeability fails, in the direction observed.
#:
#: The price of the choice is reported and not tuned away: the thinned
#: three-point marginal's produced VMR is then 1.0206 against a measured
#: `conditional_dispersion["threes"]` of 1.0846864899201918, about 6% narrow.
#: Design 4 declares a tolerance for (a) and for nothing else, so that one is
#: report-only. Both numbers appear in :meth:`PlayerDistribution.structural_checks`.
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
#: and `rate_shrinkage_k`, so these five are unchecked anywhere else and a
#: market that needs one of them would otherwise be priced on a number the fit
#: refused to stand behind. The shipped `unfittable` block is empty, so this
#: path ships exercised only against a synthetic file — which is what
#: `test_a_constant_the_fit_refused_to_invent_refuses_the_market_that_needs_it`
#: builds.
_CONSTANTS_READ_HERE: tuple[str, ...] = (
    "conditional_dispersion",
    "value_pmf",
    "value_mix_shrinkage_events",
    "points_compound_reconciliation",
    "residual_correlation",
    "structural_check_targets",
)

_MINUTES_LATTICE_LENGTH = 46
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
    """

    family: str
    mu: float
    phi_requested: float
    phi_used: float
    a: float
    b: float
    g0: float
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


def panjer_parameters(*, mu: float, phi: float) -> PanjerParameters:
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
    and the dispersion moves by `O(1/n)`. The realised `phi_used = 1 - p` is
    stored, and this function refuses if the rounding moved it further than
    `conditional_dispersion.material_absolute` = 0.02, the fit's own materiality
    floor. Measured on the frozen turnovers phi across mu in [0.2, 6.0] at a
    step of 0.01: the mean error is exactly zero and the largest
    |phi_used - phi| is 5.484e-04, which is 2.74% of that floor.
    `test_the_binomial_rounding_preserves_the_mean_and_reports_its_own_error`
    re-measures both rather than taking them on trust.
    """
    mean = float(mu)
    dispersion = float(phi)
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
    return PanjerParameters(
        family=family,
        mu=mean,
        phi_requested=dispersion,
        phi_used=used,
        a=-probability / used,
        b=(trials + 1) * probability / used,
        g0=used**trials,
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
    """
    keep = float(retention)
    if not 0.0 < keep <= 1.0:
        raise PlayerDistributionError(
            f"A thinning probability of {retention!r} is not a probability. "
            "The three-point share of a scoring event comes from the athlete's "
            "own shrunk value mix and is strictly inside (0, 1]."
        )
    if parameters.family == "poisson":
        return panjer_parameters(mu=parameters.mu * keep, phi=1.0)
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
    derivative is `-rho/s * phi((c - rho*z)/s) / phi(z)`. That ratio is 2.3e5 at
    `z = -5` and 2.8e15 at the truncation, so inside the OUTER cells -- and only
    those, because only they reach the truncation -- the integrand goes from one
    plateau to another over a stretch that is invisible to any fixed-order rule.
    Every interior cell is smooth and five nodes are ample there.

    Measured on the test fixture's points-by-rebounds joint at the 20-minute
    node, against a 400-node reference: undivided, the second marginal is wrong
    by 7.2e-07 and the sum's mean by 8.9e-06; at
    :data:`OUTER_CELL_PIECES` = 6 and :data:`OUTER_CELL_RATIO` = 4 those become
    6.5e-10 and 7.4e-09. :func:`_fit_marginals` then closes the rest.
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


def assert_structural_checks(checks: Mapping[str, float]) -> None:
    """Design 4's stop rule, and it is the only one there is.

    "If (a) is off by more than 15%, the run stops and the discrepancy is the
    finding." Nothing is tuned when this fires: no constant here is refitted, no
    tolerance is widened and no market is dropped. The other four targets in
    `structural_check_targets` carry no declared tolerance anywhere in the design
    or the frozen file, so they are reported and cannot stop anything —
    including the ~6% narrowness of the thinned three-point marginal, which is
    the known price of :data:`POINTS_EVENT_DISPERSION_KEY`.
    """
    ratio = float(checks["unconditional_points_vmr_ratio"])
    if not math.isfinite(ratio) or abs(ratio - 1.0) > UNCONDITIONAL_POINTS_VMR_STOP:
        raise StructuralCheckFailed(
            "The assembled mixture reproduces an unconditional points "
            f"variance-to-mean of {checks['unconditional_points_vmr']:.6f} "
            f"against the frozen target "
            f"{checks['unconditional_points_vmr_target']:.6f}, a ratio of "
            f"{ratio:.4f}. Design 4 stops the run outside "
            f"{UNCONDITIONAL_POINTS_VMR_STOP:.0%} and the discrepancy is the "
            "finding. Nothing is tuned to close it."
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
                    thin(self.event_parameters[node], float(self.severity[3])),
                    severity=(0.0, 1.0),
                    size=size,
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
        """The dispersion actually handed to the family that made this count.

        Design 9's column. For the four plain Panjer stats it is the frozen
        conditional dispersion with the binomial's integer-`n` rounding already
        in it. For `player_points` and `player_threes` it is the dispersion of
        the shared scoring-event count, because that is the family a phi was
        handed to; the produced dispersion of the points and threes marginals is
        a different quantity and :meth:`structural_checks` reports it.

        **NaN for the four combination markets, deliberately.** No phi is handed
        to a sum: its width is produced by the components, the copula and the
        mixture, and writing a number in this column for pra would be inventing
        a parameter that does not exist.
        """
        components = self._components(market_key)
        if len(components) > 1:
            return float("nan")
        stat = components[0]
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
        """What the assembled mixture reproduces, against what was frozen.

        Report, never tune. Design 4 gives two free checks and a tolerance for
        exactly one of them; `structural_check_targets`' own note says these are
        "not parameters ... what the assembled mixture has to reproduce with
        nothing tuned to them".
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
            "unconditional_points_vmr_ratio": produced / target,
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
      words.
    """
    if not projection.priceable:
        raise PlayerDistributionError(
            "This projection is not priceable and its own sentence stands: "
            f"{projection.unpriceable_reason or 'no reason was recorded'}. A "
            "distribution engine is not a second opinion about a refusal."
        )
    lattice = np.asarray(projection.minutes_pmf, dtype=float)
    if lattice.size != _MINUTES_LATTICE_LENGTH:
        raise PlayerDistributionError(
            f"The minutes lattice is {lattice.size} long and the index is the "
            f"number of minutes, so it must be {_MINUTES_LATTICE_LENGTH}. A "
            "support that moved would silently renumber every rung."
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
        reasons = [
            projection.refused_stats[stat]
            for stat in components
            if stat in projection.refused_stats
        ]
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
    event_parameters = {
        index: panjer_parameters(
            mu=float(rates["points_events"]) * float(node), phi=event_dispersion
        )
        for index, node in enumerate(minutes)
    }
    stat_parameters = {
        stat: {
            index: panjer_parameters(
                mu=float(rates[stat]) * float(node), phi=float(dispersions[stat])
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
