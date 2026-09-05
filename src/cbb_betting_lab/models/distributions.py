"""A joint distribution over (home score, away score). Every market reads it.

The rule this module exists to enforce: **one game, one object.** The spread,
the total, both team totals, the moneyline and every alternate rung are six
questions asked of the same 2-D array, so they cannot disagree. The football
lab priced its featured spread from one model and its alternate ladder from a
normal approximation to that model, and shipped a ladder whose −6.5 was better
value than its −7.5 for a team it made a favourite. Nothing in that output
looked wrong.

## Pushes are exact, because the whole-number lines are where the money is

A −3 spread does not push "about six percent of the time". It pushes with
exactly the probability this joint puts on a 3-point home margin, read off the
diagonal. **Measured on 43,298 Division-I-against-Division-I games, 2018-19
through 2025-26: `|margin| == 3` is the modal absolute margin at 6.13%**, ahead
of 2 (5.75%) and 4 (5.96%), and a signed 3-point home margin is 3.34%. A model
that approximates the push with a normal density at the integer gets the shape
of the margin distribution wrong exactly where the market concentrates its
whole numbers, and every key-number market is mispriced in the same direction
all season.

So the distribution is discrete on the integer lattice from the ground up.
There is no continuity correction anywhere in this file.

## The distributional choice, stated before it was measured

A team's score is a **compound sum**: it plays `N` possessions, some fraction of
them produce points, and the ones that do are worth 1, 2, 3 or (rarely) more.
That is the mechanism, so it is the model. Concretely, per team:

1. the two sides share one possession count `N` — basketball's possessions
   alternate, so the pace of a game is a property of the *game*;
2. `N` possessions produce `T` scoring trips;
3. each trip is worth points drawn from :data:`PER_POSSESSION_POINTS`,
   exponentially tilted to the team's expected points per possession.

The alternative — a bivariate normal on (score, score), or a Poisson pair —
was rejected before fitting. Poisson is wrong by construction: a possession
returns 0, 1, 2 or 3 points, so the variance-to-mean ratio of a team's score is
nothing like one. **Measured: 1.29** (team score mean 71.79, variance 148.4,
86,596 team-games). A normal is wrong in the only place that matters here, the
integers.

### The shape, measured

:data:`PER_POSSESSION_POINTS` is the distribution of points on one possession,
measured from play-by-play across **5,189,520 estimated possessions and
2,364,000 scoring trips, seasons 2018-19 through 2024-25** (2025-26 is held
out). A scoring trip is every scoring play by one team at one displayed clock
time in one period, which correctly groups a made basket with the and-one that
follows it and a two-shot foul with itself; the grouping reproduces the season's
measured points per possession to within 0.2% (1.0829 modelled against 1.0848
observed, 2025-26).

Its **shape is stable and its mean is not**: across the eight seasons the mean
rose from 0.944 to 1.083 points per possession — a 14% drift — while the
variance sat between 1.299 and 1.348. That is what licenses the one-parameter
exponential tilt: tilting the 2018-25 shape to the 2025-26 mean produces a
variance of 1.3713 against 1.3484 measured, a 1.7% error on a quantity the
model was not fitted to.

## Then it was measured, and it was 23% too wide

State-and-then-measure is the house rule, and here the first statement failed.

Sixty-eight independent possessions would give a team-score standard deviation
of 9.60 and a **margin** standard deviation of 13.58. The measured margin
standard deviation, on 5,415 regulation games in 2025-26 with team and venue
effects removed, is **11.03**. An independent-possession model is 23% too wide
on every spread in the sport, which is not a rounding matter: it prices a −10
favourite at 43% to cover instead of 39%.

Three measured constants close that gap, and each is a separate measurable
thing rather than one fudge factor:

* :data:`POSSESSION_SD` — the *effective* spread of the shared possession
  count. Not the raw one. The raw dispersion of `possessions_estimated` is 5.22
  possessions, but a game with one more possession scores only **0.42 points**
  more per team (measured by regressing a team's score residual on its
  **opponent's** possession count, 68,114 team-games, 2018-25), not the 1.03
  that arithmetic suggests, because a high-possession game is a missed-shot
  game. Modelling the raw dispersion would overstate the total's variance
  threefold.
* :data:`SHARED_EFFICIENCY_SD` — a game-level efficiency factor common to both
  teams: the whistle, the rims, the night. It is what is left of the two teams'
  score covariance after pace is accounted for, and it is **three quarters of
  it** (27.17 total covariance, 5.50 from pace).
* :data:`POSSESSION_DEPENDENCE` — the measured ratio of a team's conditional
  score variance to the independent-possession prediction, **0.656**. A team's
  possessions inside one game are not independent draws.

Fitted on 2018-19 through 2024-25 and checked against **held-out 2025-26**:
0.656 → 0.660, 0.0657 → 0.0643, 2.27 → 2.54. The first two agree to about 2%.
The mechanism behind the third is *not* identified — the measurement says a
team's makes are less variable than a coin-flip sequence and does not say why —
so it is applied where it was measured, to the count of scoring trips, and
named as future work rather than dressed up as physics. It is **not** an
artifact of the possession estimator: conditioning on the opponent's possession
count, which shares none of this team's box score, gives 77.95 against 78.24.

## Segments carry `resolves_ties`, because a half can end level

A full game cannot end level. A first half can, and does. The football lab
hardcoded the full-game rule into its half markets and priced a level half at
0.4% against a real rate of 7.4%.

**Measured here: 3.76% of first halves end level** — 1,576 of 41,915 D-I games.
Unlike the full-game margin, the half margin is *smooth* around zero: the
normal-density approximation to it gives 3.84% against 3.76% measured, and the
neighbouring integers (±1 at 3.70% and 3.88%, ±2 at 3.67% and 3.81%) sit right
where a smooth distribution puts them. There is no endgame spike at halftime,
because there is no endgame at halftime.

`resolves_ties=False` is therefore a real constructor argument that changes the
moneyline arithmetic: `moneyline(HOME) + moneyline(AWAY) + tie_probability()`
is 1 in both cases, and the tie term is only zero when the segment resolves.

## Overtime is its own segment, and scaling regulation down does not work

:data:`OVERTIME_TIE_RATE` is the number that settles this. **15.39% of the
2,891 overtime periods in these eight seasons ended level** and went to another
overtime. A normal approximation with overtime's own measured margin spread
(4.81 points) gives 8.30%. A five-minute slice of the regulation distribution
gives about 6%. The measured overtime margin distribution is not smooth at all:

    margin      0      ±1      ±2      ±3
    share    15.4%   ~5.0%   ~6.1%   ~6.9%

**The mass at zero is three times the mass at one point**, because the last
thirty seconds of a tied overtime are not basketball drawn from the same urn as
the first four minutes — they are intentional fouls, a two-for-one, and a three
to tie. No rescaling of a regulation distribution produces that spike.

So overtime is built as its own segment, from its own measured parameters:

* it scores **18.5% faster per minute than the same games' own regulation**
  (20.40 points in five minutes against 17.21 pro-rata from a regulation total
  of 137.71 — and note those games' regulation total is 137.71 against a league
  mean of 142.02, so comparing against the league mean would have understated
  the effect);
* its tie rate is imposed at the measured 15.39% by
  :func:`_concentrate_endgame`, which moves mass onto the diagonal **while
  leaving the distribution of the overtime total exactly unchanged**;
* and a full game is regulation **plus** (overtime | regulation tied), cascaded
  until the residual tie mass is below 1e-12. Measured cascade rates for
  comparison: of 2,392 overtime games, 15.2% needed a second period and 19.2%
  of those needed a third.

**5.81% of games go to overtime** (2,437 of 41,915), against 5.75% of games
level at the end of regulation in the play-by-play — the two agree, which is
the check that the segment is wired to the right event.

## What this module does not do

It takes points per possession and possessions as **given**. It does not know
where they came from, cannot tell a February number from a November one, and
must never be asked to. `ratings.Matchup` carries the prior weight alongside
them, and the card prints it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from cbb_betting_lab.selection import (
    AWAY,
    FIRST_HALF,
    FULL_GAME,
    HOME,
    OVER,
    SECOND_HALF,
    UNDER,
)


# --------------------------------------------------------------------------
# Measured constants. Every one of these carries its sample size in the module
# docstring. None of them is tuned to make a market look better.
# --------------------------------------------------------------------------

#: Points scored on one possession: index k is P(k points). Measured from
#: play-by-play over 5,189,520 estimated possessions and 2,364,000 scoring
#: trips, seasons 2018-19 through 2024-25. Mean 0.9904, variance 1.3236.
#: 2025-26 is deliberately excluded so that the shape is not fitted on the
#: season this lab prices.
PER_POSSESSION_POINTS: tuple[float, ...] = (
    0.544467,
    0.041387,
    0.294694,
    0.118356,
    0.000914,
    0.000182,
)

#: A team's conditional score variance as a fraction of what independent
#: possessions predict. Measured 0.656 on 2018-25, 0.660 on held-out 2025-26.
#: Applied to the count of scoring trips, which is where 88% of a team's score
#: variance lives (80.82 of 92.15 at league-average parameters).
POSSESSION_DEPENDENCE = 0.656

#: Standard deviation of the **shared** possession count, in possessions. This
#: is the *effective* figure — the raw dispersion of `possessions_estimated` is
#: 5.22, but an extra possession is worth 0.42 points rather than 1.03, so
#: modelling the raw figure would treble the pace contribution to the total's
#: variance. Measured 2.27 on 2018-25, 2.54 on held-out 2025-26.
POSSESSION_SD = 2.27

#: A game-level efficiency factor common to both teams, as a fraction of
#: expected points per possession. Three quarters of the two teams' score
#: covariance. Measured 0.0657 on 2018-25, 0.0643 on held-out 2025-26.
SHARED_EFFICIENCY_SD = 0.0657

REGULATION_MINUTES = 40.0
OVERTIME_MINUTES = 5.0

#: A first half is **not** half a game. Measured: first halves are 47.31% of
#: regulation scoring (67.19 of 142.02 points, 41,915 games). The processed
#: tables carry no half-level possession count, so this module cannot say how
#: much of the 2.7-point shortfall is pace and how much is efficiency; it
#: attributes all of it to efficiency and says so. Splitting it correctly is
#: future work and needs a possession count per period.
FIRST_HALF_SCORING_SHARE = 0.4731

#: Overtime scores 18.5% faster per minute than the same games' own regulation
#: (20.40 points in five minutes against 17.21 pro-rata). Measured over 2,891
#: overtime periods in 2,392 games.
OVERTIME_SCORING_MULTIPLIER = 1.174

#: The share of overtime periods that end level. **15.39%**, measured over
#: 2,891 periods — against 8.30% from a normal approximation with overtime's
#: own margin spread, and about 6% from a scaled-down regulation distribution.
#: This is the number that makes overtime a segment rather than a scaling.
OVERTIME_TIE_RATE = 0.1539

#: Measured, for the record and for the tests: 3.76% of 41,915 first halves end
#: level, and 5.81% of games go to overtime (2,437 of 41,915).
MEASURED_FIRST_HALF_TIE_RATE = 0.0376
MEASURED_OVERTIME_RATE = 0.0581
#: Points in a single overtime period, mean over 2,028 single-overtime games.
MEASURED_OVERTIME_POINTS = 20.40

#: The overtime cascade stops when the residual level mass is below this. At
#: the measured 15.4% tie rate that is reached after 17 periods; the longest
#: overtime observed in these eight seasons is four.
TIE_RESIDUAL_TOLERANCE = 1e-12

#: Quadrature nodes for the two shared factors. Enough that the mixture's mean
#: and variance are exact to floating point; `empirical_fit_report` re-measures
#: them rather than trusting this comment.
POSSESSION_NODE_SD_SPAN = 4.0
SHARED_EFFICIENCY_NODES = 7

#: Segments whose level outcomes are played out. Second halves settle
#: **including overtime** — `markets.SECOND_HALF_INCLUDES_OVERTIME`, a book
#: rule this lab records as a settlement ambiguity rather than a fact — so a
#: second half resolves whenever *regulation* was level, not whenever the half
#: was.
_RESOLVES_BY_DEFAULT = {FULL_GAME: True, FIRST_HALF: False, SECOND_HALF: True}

_POINTS = np.arange(len(PER_POSSESSION_POINTS))


class DistributionError(ValueError):
    """A distribution could not be built, or was built inconsistently."""


# --------------------------------------------------------------------------
# The per-possession distribution
# --------------------------------------------------------------------------


def tilt_to_efficiency(
    points_per_possession: float, base: Sequence[float] = PER_POSSESSION_POINTS
) -> np.ndarray:
    """The measured per-possession shape, tilted to a team's efficiency.

    Exponential tilting — `q_k ∝ p_k · e^{θk}` — rather than rescaling or
    re-fitting, for a measured reason. Across eight seasons the *mean* points
    per possession moved 14% (0.944 to 1.083) while the *variance* stayed
    between 1.299 and 1.348. A one-parameter tilt is exactly the operation
    that moves the mean and leaves the shape alone, and tilting the 2018-25
    shape onto the 2025-26 mean reproduces that season's measured variance to
    1.7% — a quantity nothing here was fitted to.

    A two-parameter tilt matching mean *and* variance was tried and rejected:
    to reach the measured variance it drives the three-point mass from 0.118 to
    0.006, and a college basketball distribution without three-pointers is not
    one. The variance shortfall is handled where it was measured instead — see
    :data:`POSSESSION_DEPENDENCE`.
    """
    weights = np.asarray(base, dtype=float)
    if weights.ndim != 1 or weights.size < 2 or np.any(weights < 0):
        raise DistributionError("The per-possession shape must be a pmf.")
    weights = weights / weights.sum()
    target = float(points_per_possession)
    lowest, highest = 0.0, float(_POINTS[-1])
    if not lowest < target < highest:
        raise DistributionError(
            f"Points per possession of {target} is outside the support "
            f"({lowest}, {highest}) of the measured shape. A team cannot score "
            "at a rate no possession can produce, and clipping it silently is "
            "how an absurd rating becomes a plausible price."
        )
    # Newton on the cumulant generating function. Monotone in theta, so this
    # converges from zero for every attainable target.
    theta = 0.0
    for _ in range(64):
        tilted = weights * np.exp(theta * _POINTS)
        tilted /= tilted.sum()
        mean = float(tilted @ _POINTS)
        variance = float(tilted @ (_POINTS**2)) - mean**2
        step = (target - mean) / max(variance, 1e-12)
        theta += step
        if abs(target - mean) < 1e-13:
            break
    tilted = weights * np.exp(theta * _POINTS)
    return tilted / tilted.sum()


def _match_variance_reference(
    pmf: np.ndarray, support: np.ndarray, target_variance: float
) -> np.ndarray:
    """Rescale a lattice distribution to an exact variance, exact mean.

    Maps each support point `s` to `m + c(s - m)` and splits the mass linearly
    between the two neighbouring integers, which preserves the first moment
    exactly by construction. `c` is solved for, rather than set to
    `sqrt(target/current)`, because the linear split adds up to a quarter of a
    unit of variance of its own and the whole point of this function is that
    the answer is exact.

    **This is the reference implementation**: one node, one scalar bisection,
    kept verbatim so that the batched solver :func:`_match_variance_batch` has
    something to be measured against. Production goes through the batch; this
    function is called by the tests and by the
    :data:`_FORCE_REFERENCE_PATH` switch only.
    """
    total = pmf.sum()
    if total <= 0:
        raise DistributionError("Cannot rescale an empty distribution.")
    mean = float(pmf @ support) / total
    variance = float(pmf @ (support - mean) ** 2) / total
    if variance <= 0 or target_variance <= 0:
        return pmf
    lo, hi = support[0], support[-1]

    def realised(c: float) -> tuple[np.ndarray, float]:
        moved = np.clip(mean + c * (support - mean), lo, hi)
        floor = np.floor(moved).astype(np.int64)
        frac = moved - floor
        out = np.zeros(support.size + 1)
        index = floor - int(lo)
        np.add.at(out, index, pmf * (1.0 - frac))
        np.add.at(out, index + 1, pmf * frac)
        out = out[: support.size]
        got = float(out @ (support - mean) ** 2) / max(out.sum(), 1e-300)
        return out, got

    low, high = 0.0, 1.0
    _, at_one = realised(1.0)
    while at_one < target_variance and high < 64.0:
        high *= 2.0
        _, at_one = realised(high)
    for _ in range(60):
        middle = 0.5 * (low + high)
        _, got = realised(middle)
        if got < target_variance:
            low = middle
        else:
            high = middle
    out, _ = realised(0.5 * (low + high))
    return out / out.sum()


#: How far, in units of `width × 2⁻⁵³` relative to the target, a batched node
#: variance may sit from its target before :func:`_match_variance_batch`
#: recomputes it the reference's way. The rounding error of a sum of
#: non-negative terms is below `1 × width × 2⁻⁵³` relative for either
#: computation, so 8 leaves a fourfold margin over the combined bound.
_CLOSE_CALL_ULPS = 8.0

#: Tests only. When true, :func:`_trip_count_pmfs` solves every node through
#: the scalar :func:`_match_variance_reference` instead of the batched solver,
#: so a whole `build` can be computed both ways and compared. Never on by
#: default; nothing in production reads it except that one branch.
_FORCE_REFERENCE_PATH = False


def _match_variance_batch(
    pmfs: Sequence[np.ndarray],
    supports: Sequence[np.ndarray],
    target_variances: Sequence[float],
) -> list[np.ndarray]:
    """:func:`_match_variance_reference` for many nodes at once.

    The same mathematics, node for node — the same doubling rule, the same
    sixty bisection steps, the same midpoint, the same final `realised` and
    normalisation — but every step is one vectorised operation over the whole
    batch instead of a Python call per node. A node that has finished doubling
    keeps its own `high` while the others continue (masks); a node whose
    bisection has decided keeps its own `low`/`high`. Nodes with no variance or
    no positive target are returned untouched, exactly as the reference does.

    Bit-identical to the reference, and here is why that needs saying. The
    scatter, the mean and the normalising sum are the reference's own
    operations in the reference's own order. The one place a batch rounds
    differently is the per-node variance `got` at each step — a row-wise
    reduction is not a 1-D BLAS dot — and a bisection compares `got` with the
    target, so in the last dozen steps, where the two are within rounding of
    each other, a batched `got` could send a node the other way. So every step
    computes `got` batched, then recomputes it **the reference's way, one node
    at a time, for exactly the nodes where the batched value is within the
    rounding bound of the target** (`_CLOSE_CALL_ULPS` × width × 2⁻⁵³,
    relative — the sum of non-negative terms has relative error below
    `width · 2⁻⁵³` in either computation). Far from the target the decision
    cannot depend on rounding; near it the reference's own arithmetic decides.
    The tests check the result is `np.array_equal` to the reference.
    """
    count = len(pmfs)
    if count != len(supports) or count != len(target_variances):
        raise DistributionError("Batched variance matching needs one target per node.")
    results: list[np.ndarray | None] = [None] * count
    active: list[int] = []
    means: list[float] = []
    for i, (pmf, support, target) in enumerate(zip(pmfs, supports, target_variances)):
        total = pmf.sum()
        if total <= 0:
            raise DistributionError("Cannot rescale an empty distribution.")
        mean = float(pmf @ support) / total
        variance = float(pmf @ (support - mean) ** 2) / total
        if variance <= 0 or target <= 0:
            results[i] = pmf
            continue
        active.append(i)
        means.append(mean)
    if not active:
        return results  # type: ignore[return-value]

    rows = len(active)
    sizes = np.array([pmfs[i].size for i in active], dtype=np.int64)
    width = int(sizes.max())
    # Padded rows. A padded support cell carries the row's own `hi` and zero
    # mass, so it lands where the clipped top of the support lands and adds
    # exactly +0.0 there — a no-op in floating point.
    pmf_rows = np.zeros((rows, width))
    support_rows = np.empty((rows, width))
    lo = np.empty(rows)
    hi = np.empty(rows)
    for r, i in enumerate(active):
        size = int(sizes[r])
        pmf_rows[r, :size] = pmfs[i]
        support_rows[r, :size] = supports[i]
        support_rows[r, size:] = supports[i][-1]
        lo[r] = supports[i][0]
        hi[r] = supports[i][-1]
    mean = np.array(means)[:, None]
    target = np.array([target_variances[i] for i in active], dtype=float)
    lo_int = np.array([int(v) for v in lo], dtype=np.int64)[:, None]
    lo = lo[:, None]
    hi = hi[:, None]
    centred = support_rows - mean
    squared = centred**2
    # The reference's `(support - mean) ** 2`, one 1-D array per node, for the
    # close-call recomputation below.
    squared_rows = [
        (supports[i] - means[r]) ** 2 for r, i in enumerate(active)
    ]
    sizes_list = [int(size) for size in sizes]
    close_call = _CLOSE_CALL_ULPS * width * 2.0**-53 * target
    stride = width + 1
    # Row `r` of the scatter target starts at flat cell `r * stride`; the
    # reference's `floor - int(lo)` becomes `floor + shift` with the row offset
    # folded in. Integer arithmetic, so exact.
    shift = (np.arange(rows, dtype=np.int64) * stride)[:, None] - lo_int
    flat_length = rows * stride
    index_pairs = np.empty((2, rows, width), dtype=np.int64)
    weight_pairs = np.empty((2, rows, width))

    def realised(c: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        moved = mean + c[:, None] * centred
        # `np.clip(x, lo, hi)` is `min(max(x, lo), hi)`; every value is finite.
        np.maximum(moved, lo, out=moved)
        np.minimum(moved, hi, out=moved)
        floor = np.floor(moved)
        frac = moved - floor
        np.add(floor.astype(np.int64), shift, out=index_pairs[0])
        np.add(index_pairs[0], 1, out=index_pairs[1])
        np.multiply(pmf_rows, 1.0 - frac, out=weight_pairs[0])
        np.multiply(pmf_rows, frac, out=weight_pairs[1])
        # One sequential accumulation in the reference's order: every
        # `(1 - frac)` share first, then every `frac` share, each in row-major
        # order — which is the order `np.add.at` added them one node at a time.
        out = np.bincount(
            index_pairs.ravel(), weights=weight_pairs.ravel(), minlength=flat_length
        ).reshape(rows, stride)[:, :width]
        got = (out * squared).sum(axis=1) / np.maximum(out.sum(axis=1), 1e-300)
        # Close calls: recompute with the reference's own expression so the
        # comparison against the target is the reference's comparison.
        # (`np.add.reduce` is what `ndarray.sum()` calls, minus the wrapper.)
        for r in np.flatnonzero(np.abs(got - target) <= close_call):
            row = out[r, : sizes_list[r]]
            got[r] = float(row @ squared_rows[r]) / max(np.add.reduce(row), 1e-300)
        return out, got

    low = np.zeros(rows)
    high = np.ones(rows)
    _, at_one = realised(high)
    doubling = (at_one < target) & (high < 64.0)
    while doubling.any():
        high = np.where(doubling, high * 2.0, high)
        _, got = realised(high)
        at_one = np.where(doubling, got, at_one)
        doubling = (at_one < target) & (high < 64.0)
    for _ in range(60):
        middle = 0.5 * (low + high)
        _, got = realised(middle)
        below = got < target
        low = np.where(below, middle, low)
        high = np.where(below, high, middle)
    out, _ = realised(0.5 * (low + high))
    for r, i in enumerate(active):
        row = out[r, : int(sizes[r])]
        results[i] = row / row.sum()
    return results  # type: ignore[return-value]


def _match_variance(
    pmf: np.ndarray, support: np.ndarray, target_variance: float
) -> np.ndarray:
    """One node, through the batched solver. See :func:`_match_variance_batch`."""
    return _match_variance_batch([pmf], [support], [target_variance])[0]


def _trip_count_pmf_reference(
    possessions: int, scoring_probability: float, target_variance: float
) -> np.ndarray:
    """The one-node reference for :func:`_trip_count_pmfs`; tests only."""
    n = int(possessions)
    p = float(scoring_probability)
    if n <= 0:
        return np.array([1.0])
    p = min(max(p, 1e-9), 1 - 1e-9)
    counts = np.arange(n + 1)
    # Binomial via log-gamma: n is at most a few hundred, and the direct
    # product form loses precision in the tails that the ladder reads.
    from scipy.special import gammaln

    log = (
        gammaln(n + 1)
        - gammaln(counts + 1)
        - gammaln(n - counts + 1)
        + counts * np.log(p)
        + (n - counts) * np.log1p(-p)
    )
    pmf = np.exp(log - log.max())
    pmf /= pmf.sum()
    if target_variance <= 0:
        return pmf
    return _match_variance_reference(pmf, counts.astype(float), target_variance)


def _trip_count_pmfs(
    possessions: Sequence[int],
    scoring_probability: float | Sequence[float],
    target_variances: Sequence[float],
) -> list[np.ndarray]:
    """How many of `possessions` possessions score, for a batch of counts.

    Binomial is the independent-possession answer and it is measurably too
    wide — see :data:`POSSESSION_DEPENDENCE`. The count is where the
    correction belongs: at league-average parameters **88% of a team's score
    variance is the number of scoring trips** (80.82 of 92.15) and only 12% is
    what those trips are worth, so a correction applied to the trip values
    would be applied where the variance is not.

    One call for a whole batch of nodes rather than one per possession count:
    the binomials are laid out as padded rows and the variance matching is
    solved for every row at once by :func:`_match_variance_batch`. Each row's
    numbers are the reference's, operation for operation — the log-binomial is
    elementwise, the row maximum is exact, and the normalising sum runs over
    the row's own cells only. `scoring_probability` is one number for the
    batch or one per row.
    """
    ns = [int(n) for n in possessions]
    if np.ndim(scoring_probability) == 0:
        probabilities = [float(scoring_probability)] * len(ns)
    else:
        probabilities = [float(p) for p in scoring_probability]
    if len(probabilities) != len(ns) or len(target_variances) != len(ns):
        raise DistributionError("Batched trip counts need one probability and target per node.")
    if _FORCE_REFERENCE_PATH:
        return [
            _trip_count_pmf_reference(n, p, target)
            for n, p, target in zip(ns, probabilities, target_variances)
        ]
    probabilities = [min(max(p, 1e-9), 1 - 1e-9) for p in probabilities]
    results: list[np.ndarray | None] = [None] * len(ns)
    live = [i for i, n in enumerate(ns) if n > 0]
    for i, n in enumerate(ns):
        if n <= 0:
            results[i] = np.array([1.0])
    if not live:
        return results  # type: ignore[return-value]
    from scipy.special import gammaln

    n_column = np.array([ns[i] for i in live], dtype=np.int64)[:, None]
    p_column = np.array([probabilities[i] for i in live], dtype=float)[:, None]
    width = int(n_column.max()) + 1
    counts = np.arange(width)
    inside = counts[None, :] <= n_column
    remaining = np.where(inside, n_column - counts, 0)
    log = (
        gammaln(n_column + 1)
        - gammaln(counts + 1)
        - gammaln(remaining + 1)
        + counts * np.log(p_column)
        + (n_column - counts) * np.log1p(-p_column)
    )
    log[~inside] = -np.inf
    pmf_rows = np.exp(log - log.max(axis=1, keepdims=True))
    pmfs: list[np.ndarray] = []
    supports: list[np.ndarray] = []
    for r, i in enumerate(live):
        pmf = pmf_rows[r, : ns[i] + 1]
        pmf /= pmf.sum()
        pmfs.append(pmf)
        supports.append(counts[: ns[i] + 1].astype(float))
    matched = _match_variance_batch(
        pmfs, supports, [target_variances[i] for i in live]
    )
    for r, i in enumerate(live):
        results[i] = pmfs[r] if target_variances[i] <= 0 else matched[r]
    return results  # type: ignore[return-value]


def _trip_count_pmf(
    possessions: int, scoring_probability: float, target_variance: float
) -> np.ndarray:
    """One possession count; see :func:`_trip_count_pmfs`."""
    return _trip_count_pmfs([possessions], scoring_probability, [target_variance])[0]


def _trip_value_powers(trip_pmf: np.ndarray, max_trips: int, length: int) -> np.ndarray:
    """`trip_pmf` convolved with itself 0..max_trips times, exactly.

    By FFT. `length` is chosen so that the largest attainable score fits, so
    there is no wraparound and no truncation: the arrays this returns are the
    exact convolution powers, to floating point.
    """
    spectrum = np.fft.rfft(trip_pmf, length)
    powers = spectrum[None, :] ** np.arange(max_trips + 1)[:, None]
    out = np.fft.irfft(powers, length, axis=1)
    np.clip(out, 0.0, None, out=out)
    sums = out.sum(axis=1, keepdims=True)
    return out / np.where(sums > 0, sums, 1.0)


def _lattice_normal(mean: float, sd: float, span: float) -> tuple[np.ndarray, np.ndarray]:
    """An integer-valued approximation to a normal, with the exact mean.

    Used for the shared possession count, which has to be an integer because
    possessions are. Sheppard's correction removes the variance the lattice
    adds; the mean is then fixed exactly by a one-parameter tilt, because a
    possession count that is half a possession off moves every total.
    """
    if sd <= 0:
        value = int(round(mean))
        return np.array([float(value)]), np.array([1.0])
    from scipy.stats import norm

    continuous_sd = float(np.sqrt(max(sd**2 - 1.0 / 12.0, 1e-6)))
    lo = int(np.floor(mean - span * sd))
    hi = int(np.ceil(mean + span * sd))
    lo = max(lo, 1)
    hi = max(hi, lo + 1)
    values = np.arange(lo, hi + 1, dtype=float)
    weights = norm.cdf(values + 0.5, mean, continuous_sd) - norm.cdf(
        values - 0.5, mean, continuous_sd
    )
    weights = np.clip(weights, 1e-300, None)
    weights /= weights.sum()
    theta = 0.0
    for _ in range(64):
        tilted = weights * np.exp(theta * values)
        tilted /= tilted.sum()
        got = float(tilted @ values)
        variance = float(tilted @ values**2) - got**2
        theta += (mean - got) / max(variance, 1e-9)
        if abs(mean - got) < 1e-12:
            break
    tilted = weights * np.exp(theta * values)
    return values, tilted / tilted.sum()


def _gauss_hermite(sd: float, nodes: int) -> tuple[np.ndarray, np.ndarray]:
    """Nodes and weights for a mean-zero normal factor."""
    if sd <= 0 or nodes <= 1:
        return np.array([0.0]), np.array([1.0])
    points, weights = np.polynomial.hermite_e.hermegauss(nodes)
    return points * sd, weights / weights.sum()


# --------------------------------------------------------------------------
# The distribution itself
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class GameDistribution:
    """The joint distribution over (home score, away score) for one segment.

    `joint[h, a]` is the probability the home side scores `h` and the away side
    `a`. Both supports start at zero, so no offset arithmetic is needed
    anywhere and the diagonal is the diagonal.

    Every market method returns `(win, push, loss)` summing to one, so a caller
    can never silently drop the push and re-normalise the other two — which is
    how a −3 comes to be priced as if it were a −3.5.
    """

    joint: np.ndarray
    segment: str
    #: Whether a level segment is played out. False for a first half, which
    #: **can** end level: measured at 3.76% of 41,915 games. When False the two
    #: moneyline sides do not sum to one and `tie_probability` is the rest.
    resolves_ties: bool
    possessions: float
    home_points_per_possession: float
    away_points_per_possession: float
    #: How much of the ratings behind this price is still the preseason prior,
    #: in [0, 1]. Carried, never computed here — this module cannot tell a
    #: November number from a February one and must not pretend to.
    prior_weight: float | None = None

    def __post_init__(self) -> None:
        joint = np.asarray(self.joint, dtype=float)
        if joint.ndim != 2:
            raise DistributionError("A game distribution is a 2-D joint.")
        total = float(joint.sum())
        if not np.isfinite(total) or abs(total - 1.0) > 1e-9:
            raise DistributionError(
                f"This joint sums to {total!r}, not 1. A distribution that "
                "does not sum to one prices every market on the game wrong in "
                "the same direction, and nothing about the output looks broken."
            )
        if self.resolves_ties and self.tie_probability() > 1e-9:
            raise DistributionError(
                "This segment claims to resolve ties and holds "
                f"{self.tie_probability():.3e} of probability on the diagonal. "
                "A full game cannot end level; either the overtime cascade did "
                "not run or it did not converge."
            )

    # -- marginals ---------------------------------------------------------

    def team_pmf(self, which: str) -> np.ndarray:
        """The marginal score distribution for one side."""
        if which == HOME:
            return self.joint.sum(axis=1)
        if which == AWAY:
            return self.joint.sum(axis=0)
        raise DistributionError(f"Unknown side {which!r}; expected {HOME!r} or {AWAY!r}.")

    def margin_pmf(self) -> tuple[np.ndarray, np.ndarray]:
        """`(margins, probabilities)` for home score minus away score."""
        rows, columns = self.joint.shape
        margins = np.arange(-(columns - 1), rows)
        weights = np.array(
            [np.trace(self.joint, offset=-m) for m in margins], dtype=float
        )
        return margins.astype(float), weights

    def total_pmf(self) -> tuple[np.ndarray, np.ndarray]:
        """`(totals, probabilities)` for the sum of the two scores."""
        rows, columns = self.joint.shape
        totals = np.arange(rows + columns - 1)
        weights = np.zeros(totals.size)
        for offset in range(columns):
            weights[offset : offset + rows] += self.joint[:, offset]
        return totals.astype(float), weights

    # -- markets -----------------------------------------------------------

    def margin(self, line: float, side: str) -> tuple[float, float, float]:
        """A spread, in the provider's convention: `line` is the named side's
        handicap.

        Home −3.5 is `margin(-3.5, HOME)`; the same game's away +3.5 is
        `margin(3.5, AWAY)`. The two are complementary by construction because
        they read the same diagonal, which is the property that stops a card
        taking both sides of one game.

        The push is **exact**. It is the mass on one diagonal, not a density.
        """
        margins, weights = self.margin_pmf()
        signed = margins if side == HOME else -margins
        if side not in (HOME, AWAY):
            raise DistributionError(
                f"Unknown side {side!r}; a spread has {HOME!r} and {AWAY!r}."
            )
        adjusted = signed + float(line)
        return (
            float(weights[adjusted > 0].sum()),
            float(weights[adjusted == 0].sum()),
            float(weights[adjusted < 0].sum()),
        )

    def total(self, line: float, side: str) -> tuple[float, float, float]:
        """The game total. `side` is `over` or `under`."""
        if side not in (OVER, UNDER):
            raise DistributionError(
                f"Unknown side {side!r}; a total has {OVER!r} and {UNDER!r}."
            )
        totals, weights = self.total_pmf()
        above = float(weights[totals > float(line)].sum())
        push = float(weights[totals == float(line)].sum())
        below = float(weights[totals < float(line)].sum())
        return (above, push, below) if side == OVER else (below, push, above)

    def team_total(
        self, line: float, side: str, which: str
    ) -> tuple[float, float, float]:
        """One team's own total. `side` is over/under, `which` is home/away."""
        if side not in (OVER, UNDER):
            raise DistributionError(
                f"Unknown side {side!r}; a team total has {OVER!r} and {UNDER!r}."
            )
        pmf = self.team_pmf(which)
        scores = np.arange(pmf.size, dtype=float)
        above = float(pmf[scores > float(line)].sum())
        push = float(pmf[scores == float(line)].sum())
        below = float(pmf[scores < float(line)].sum())
        return (above, push, below) if side == OVER else (below, push, above)

    def moneyline(self, side: str) -> float:
        """The probability this side wins the segment **outright**.

        When `resolves_ties` is False these do not sum to one, and the
        shortfall is `tie_probability()`. That is not a rounding error to be
        normalised away: it is 3.76% of first halves, and a book that voids a
        level half is offering a different bet from one that pushes it.
        """
        if side not in (HOME, AWAY):
            raise DistributionError(
                f"Unknown side {side!r}; a moneyline has {HOME!r} and {AWAY!r}."
            )
        margins, weights = self.margin_pmf()
        return float(weights[margins > 0].sum() if side == HOME else weights[margins < 0].sum())

    def tie_probability(self) -> float:
        """The mass on a level segment. Zero when the segment resolves ties."""
        margins, weights = self.margin_pmf()
        return float(weights[margins == 0].sum())

    # -- ladders -----------------------------------------------------------

    def ladder(
        self,
        lines: Iterable[float],
        *,
        market: str,
        side: str,
        which: str | None = None,
    ) -> list[tuple[float, tuple[float, float, float]]]:
        """Every alternate rung, off this object and no other.

        There is no separate alternate-ladder model in this repository, and
        there must never be one. The football lab had two and shipped a ladder
        whose −6.5 was better value than its −7.5.
        """
        readers = {
            "margin": lambda line: self.margin(line, side),
            "total": lambda line: self.total(line, side),
            "team_total": lambda line: self.team_total(line, side, which or HOME),
        }
        if market not in readers:
            raise DistributionError(
                f"Unknown market {market!r}; expected one of {sorted(readers)}."
            )
        read = readers[market]
        return [(float(line), read(float(line))) for line in lines]

    # -- summary -----------------------------------------------------------

    @property
    def expected_margin(self) -> float:
        margins, weights = self.margin_pmf()
        return float(margins @ weights)

    @property
    def expected_total(self) -> float:
        totals, weights = self.total_pmf()
        return float(totals @ weights)

    def summary_line(self) -> str:
        prior = (
            f", {self.prior_weight:.0%} prior"
            if self.prior_weight is not None
            else ""
        )
        return (
            f"{self.segment}: home {self.moneyline(HOME):.1%} / away "
            f"{self.moneyline(AWAY):.1%}"
            + (
                f" / level {self.tie_probability():.1%}"
                if not self.resolves_ties
                else ""
            )
            + f", margin {self.expected_margin:+.2f}, total "
            f"{self.expected_total:.1f}, {self.possessions:.1f} possessions"
            + prior
        )


# --------------------------------------------------------------------------
# Building one
# --------------------------------------------------------------------------


def _conditional_scores(
    points_per_possession: float,
    possession_values: np.ndarray,
    efficiency_nodes: np.ndarray,
    length: int,
) -> np.ndarray:
    """Score pmfs for every (possessions, shared-efficiency) node.

    Returns an array indexed `[efficiency, possessions, score]`. The
    convolution powers of the trip-value distribution depend only on the
    efficiency node, so they are computed once per node and reused across every
    possession count — which is what keeps a full ladder inside a few
    milliseconds.
    """
    max_possessions = int(possession_values[-1])
    out = np.zeros((efficiency_nodes.size, possession_values.size, length))
    ns = [int(possessions) for possessions in possession_values]
    powers_by_node: list[np.ndarray] = []
    batch_ns: list[int] = []
    batch_scoring: list[float] = []
    batch_variances: list[float] = []
    for shift in efficiency_nodes:
        per_possession = tilt_to_efficiency(points_per_possession * (1.0 + shift))
        scoring = 1.0 - per_possession[0]
        trip_values = per_possession[1:] / scoring
        trip_support = np.arange(1, per_possession.size, dtype=float)
        trip_mean = float(trip_values @ trip_support)
        trip_variance = float(trip_values @ trip_support**2) - trip_mean**2
        per_possession_variance = float(
            per_possession @ (_POINTS**2)
        ) - float(per_possession @ _POINTS) ** 2
        powers_by_node.append(
            _trip_value_powers(
                np.concatenate([[0.0], trip_values]), max_possessions, length
            )
        )
        for n in ns:
            target = POSSESSION_DEPENDENCE * n * per_possession_variance
            # The trips themselves carry n*p*Var(P) of that; the rest has to
            # come from the count, which is where the measurement put it.
            count_variance = (target - n * scoring * trip_variance) / max(
                trip_mean**2, 1e-12
            )
            batch_ns.append(n)
            batch_scoring.append(scoring)
            batch_variances.append(max(count_variance, 0.0))
    # Every (efficiency node, possession count) pair at once: one batched
    # bisection rather than one scalar solve per pair — see `_trip_count_pmfs`.
    counts_by_pair = _trip_count_pmfs(batch_ns, batch_scoring, batch_variances)
    pair = 0
    for e_index, powers in enumerate(powers_by_node):
        for n_index in range(len(ns)):
            counts = counts_by_pair[pair]
            pair += 1
            out[e_index, n_index] = counts @ powers[: counts.size]
    return out


def _concentrate_endgame(joint: np.ndarray, tie_rate: float) -> np.ndarray:
    """Move mass onto the diagonal to hit a **measured** level rate.

    Overtime ends level 15.39% of the time (2,891 periods) and no compound
    model of five minutes of basketball produces that: the same distribution's
    normal approximation gives 8.30%. The last thirty seconds of a tied
    overtime are intentional fouls and a three to tie, and this function is
    where that fact enters — explicitly, at a measured size, rather than by
    quietly widening something until the number came out right.

    It **preserves the distribution of the overtime total exactly**. Only
    even totals can be level, so the reweighting runs within each even total
    and the total's marginal is untouched; what changes is how a given total is
    split between the two teams.
    """
    joint = np.asarray(joint, dtype=float)
    rows, columns = joint.shape
    diagonal = min(rows, columns)
    indices = np.arange(diagonal)
    current = float(joint[indices, indices].sum())
    totals = np.add.outer(np.arange(rows), np.arange(columns))
    even = (totals % 2) == 0
    even_mass = float(joint[even].sum())
    if tie_rate <= current or even_mass <= current:
        return joint
    alpha = (tie_rate - current) / (even_mass - current)
    out = joint.copy()
    out[even] *= 1.0 - alpha
    # Give back exactly what was taken, total by total, onto the diagonal.
    taken = np.zeros(rows + columns - 1)
    np.add.at(taken, totals[even].ravel(), (alpha * joint[even]).ravel())
    for index in indices:
        out[index, index] += taken[2 * index]
    return out


def _resolved_overtime(
    home_points_per_possession: float,
    away_points_per_possession: float,
    possessions_per_40: float,
) -> np.ndarray:
    """The joint of points added in overtime, given the segment reached it.

    Built from overtime's own parameters and cascaded: a level overtime is
    followed by another, until the residual level mass is below
    :data:`TIE_RESIDUAL_TOLERANCE`. It is **not** a scaled regulation
    distribution — see the module docstring for the three measurements that
    rule that out.
    """
    possessions = (
        possessions_per_40 * OVERTIME_MINUTES / REGULATION_MINUTES
    )
    single = _compound_joint(
        home_points_per_possession * OVERTIME_SCORING_MULTIPLIER,
        away_points_per_possession * OVERTIME_SCORING_MULTIPLIER,
        possessions,
    )
    single = _concentrate_endgame(single, OVERTIME_TIE_RATE)

    rows, columns = single.shape
    diagonal = min(rows, columns)
    indices = np.arange(diagonal)
    level = np.zeros_like(single)
    level[indices, indices] = single[indices, indices]
    decided = single - level

    resolved = decided.copy()
    carry = level
    single_spectra: dict[tuple[int, int], np.ndarray] = {}
    for _ in range(64):
        mass = float(carry.sum())
        if mass < TIE_RESIDUAL_TOLERANCE:
            break
        carry = _convolve2d(carry, single, single_spectra)
        rows, columns = carry.shape
        diagonal = min(rows, columns)
        indices = np.arange(diagonal)
        still_level = np.zeros_like(carry)
        still_level[indices, indices] = carry[indices, indices]
        settled = carry - still_level
        resolved = _add_into(resolved, settled)
        carry = still_level
    total = resolved.sum()
    if total <= 0:
        raise DistributionError("The overtime cascade produced no mass.")
    # The truncated remainder is below 1e-12 by construction; it is returned to
    # the distribution proportionally rather than left as a hole.
    return resolved / total


def _convolve2d(
    left: np.ndarray,
    right: np.ndarray,
    right_spectra: dict[tuple[int, int], np.ndarray] | None = None,
) -> np.ndarray:
    """Exact 2-D convolution of two lattice joints, by FFT.

    `right_spectra`, when given, memoises `rfft2(right, shape)` by `shape` for
    a caller convolving the **same** `right` repeatedly — the overtime cascade
    — so the transform of the unchanging side is taken once per padded size
    instead of once per step. The same input at the same size is the same
    transform, so the output is unchanged to the bit.
    """
    rows = left.shape[0] + right.shape[0] - 1
    columns = left.shape[1] + right.shape[1] - 1
    shape = (
        int(2 ** np.ceil(np.log2(max(rows, 2)))),
        int(2 ** np.ceil(np.log2(max(columns, 2)))),
    )
    if right_spectra is None:
        right_spectrum = np.fft.rfft2(right, shape)
    else:
        right_spectrum = right_spectra.get(shape)
        if right_spectrum is None:
            right_spectrum = right_spectra[shape] = np.fft.rfft2(right, shape)
    out = np.fft.irfft2(np.fft.rfft2(left, shape) * right_spectrum, shape)
    out = out[:rows, :columns]
    np.clip(out, 0.0, None, out=out)
    return out


def _add_into(base: np.ndarray, addition: np.ndarray) -> np.ndarray:
    rows = max(base.shape[0], addition.shape[0])
    columns = max(base.shape[1], addition.shape[1])
    out = np.zeros((rows, columns))
    out[: base.shape[0], : base.shape[1]] += base
    out[: addition.shape[0], : addition.shape[1]] += addition
    return out


def _trim(joint: np.ndarray, tolerance: float = 1e-15) -> np.ndarray:
    """Drop the outer rows and columns holding less than `tolerance` in total.

    Storage only. The mass removed is renormalised back in, and it is at most
    2e-15 — five orders of magnitude below the smallest probability any market
    in this repository reports.
    """
    rows = np.where(joint.sum(axis=1).cumsum() >= tolerance)[0]
    columns = np.where(joint.sum(axis=0).cumsum() >= tolerance)[0]
    top = joint.sum(axis=1)[::-1].cumsum()
    left = joint.sum(axis=0)[::-1].cumsum()
    last_row = joint.shape[0] - int(np.argmax(top >= tolerance))
    last_column = joint.shape[1] - int(np.argmax(left >= tolerance))
    first_row = int(rows[0]) if rows.size else 0
    first_column = int(columns[0]) if columns.size else 0
    out = joint[: max(last_row, first_row + 1), : max(last_column, first_column + 1)]
    return out / out.sum()


def _compound_joint(
    home_points_per_possession: float,
    away_points_per_possession: float,
    possessions: float,
) -> np.ndarray:
    """The joint over (home, away) for one uninterrupted stretch of play.

    Possessions are shared — they alternate, so the pace of a game belongs to
    the game — and the two sides are conditionally independent given the shared
    possession count and the shared efficiency factor. Every bit of the two
    scores' correlation therefore comes from a named mechanism rather than from
    a fitted correlation parameter, and `empirical_fit_report` checks how much
    of the measured 0.33 those two mechanisms actually produce.
    """
    if possessions <= 0:
        raise DistributionError("A segment with no possessions has no distribution.")
    possession_sd = POSSESSION_SD * np.sqrt(possessions / 68.5)
    values, possession_weights = _lattice_normal(
        possessions, possession_sd, POSSESSION_NODE_SD_SPAN
    )
    nodes, node_weights = _gauss_hermite(SHARED_EFFICIENCY_SD, SHARED_EFFICIENCY_NODES)
    length = int(2 ** np.ceil(np.log2(_POINTS[-1] * int(values[-1]) + 2)))
    home = _conditional_scores(
        home_points_per_possession, values, nodes, length
    )
    away = _conditional_scores(
        away_points_per_possession, values, nodes, length
    )
    joint = np.zeros((length, length))
    # `joint += weight * np.outer(h, a)`, operation for operation — `outer` is
    # the elementwise product, a scalar multiplies commutatively, and `+=` is
    # `np.add` — but into one reused buffer rather than two fresh half-megabyte
    # arrays per node, which were most of this loop's cost.
    product = np.empty((length, length))
    for e_index, node_weight in enumerate(node_weights):
        for n_index, possession_weight in enumerate(possession_weights):
            weight = node_weight * possession_weight
            if weight < 1e-14:
                continue
            np.multiply.outer(home[e_index, n_index], away[e_index, n_index], out=product)
            np.multiply(product, weight, out=product)
            np.add(joint, product, out=joint)
    return _trim(joint / joint.sum())


def build(
    *,
    home_points_per_possession: float,
    away_points_per_possession: float,
    possessions: float,
    segment: str = FULL_GAME,
    resolves_ties: bool | None = None,
    prior_weight: float | None = None,
) -> GameDistribution:
    """One segment's joint distribution, from three numbers.

    `possessions` is the expected count **per team over forty minutes** —
    tempo, in the vocabulary `ratings` uses — and the segment scales it.

    `resolves_ties` defaults from the segment and is overridable, because it is
    a property of the *bet*, not of the sport: a full game resolves, a first
    half does not, and a second half resolves whenever regulation was level
    rather than whenever the half was, which is
    `markets.SECOND_HALF_INCLUDES_OVERTIME` — a book rule this lab records as a
    settlement ambiguity rather than a fact about basketball.
    """
    if segment not in _RESOLVES_BY_DEFAULT:
        raise DistributionError(
            f"Unknown segment {segment!r}; expected one of "
            f"{sorted(_RESOLVES_BY_DEFAULT)}."
        )
    resolve = _RESOLVES_BY_DEFAULT[segment] if resolves_ties is None else bool(resolves_ties)
    tempo = float(possessions)

    if segment == FULL_GAME:
        joint = _compound_joint(
            home_points_per_possession, away_points_per_possession, tempo
        )
        if resolve:
            joint = _append_overtime(
                joint,
                joint,
                home_points_per_possession,
                away_points_per_possession,
                tempo,
            )
    elif segment == FIRST_HALF:
        efficiency = 2.0 * FIRST_HALF_SCORING_SHARE
        joint = _compound_joint(
            home_points_per_possession * efficiency,
            away_points_per_possession * efficiency,
            tempo / 2.0,
        )
        if resolve:
            joint = _append_overtime(
                joint,
                joint,
                home_points_per_possession,
                away_points_per_possession,
                tempo,
            )
    else:
        efficiency = 2.0 * (1.0 - FIRST_HALF_SCORING_SHARE)
        first = _compound_joint(
            home_points_per_possession * (2.0 * FIRST_HALF_SCORING_SHARE),
            away_points_per_possession * (2.0 * FIRST_HALF_SCORING_SHARE),
            tempo / 2.0,
        )
        joint = _compound_joint(
            home_points_per_possession * efficiency,
            away_points_per_possession * efficiency,
            tempo / 2.0,
        )
        if resolve:
            # A second half settles including overtime, and overtime happens
            # when **regulation** was level — that is, when the first half's
            # margin exactly cancels this half's. Conditioning on the first
            # half's margin is the whole of that dependence, which is why this
            # is exact rather than an approximation that treats the two as
            # independent events.
            joint = _append_overtime(
                joint,
                first,
                home_points_per_possession,
                away_points_per_possession,
                tempo,
            )
    return GameDistribution(
        joint=joint,
        segment=segment,
        resolves_ties=resolve,
        possessions=tempo,
        home_points_per_possession=float(home_points_per_possession),
        away_points_per_possession=float(away_points_per_possession),
        prior_weight=None if prior_weight is None else float(prior_weight),
    )


def _append_overtime(
    joint: np.ndarray,
    deciding: np.ndarray,
    home_points_per_possession: float,
    away_points_per_possession: float,
    tempo: float,
) -> np.ndarray:
    """Add overtime to the part of `joint` that `deciding` says went level.

    For a full game or a half priced on its own, `deciding is joint` and the
    condition is simply that this segment was level. For a second half,
    `deciding` is the **first** half, and the mass that goes to overtime is the
    mass whose first-half margin exactly cancels the second half's — which
    depends on the second half's margin alone, so the reweighting is a function
    of the diagonal offset and nothing more.
    """
    rows, columns = joint.shape
    margins = np.subtract.outer(np.arange(rows), np.arange(columns))
    if deciding is joint:
        goes_to_overtime = (margins == 0).astype(float)
    else:
        other, weights = _margin_pmf_of(deciding)
        lookup = dict(zip(other.astype(int).tolist(), weights.tolist()))
        goes_to_overtime = np.vectorize(lambda m: lookup.get(int(-m), 0.0))(margins)
    to_overtime = joint * goes_to_overtime
    stays = joint - to_overtime
    if to_overtime.sum() <= TIE_RESIDUAL_TOLERANCE:
        return stays / stays.sum()
    overtime = _resolved_overtime(
        home_points_per_possession, away_points_per_possession, tempo
    )
    out = _add_into(stays, _convolve2d(to_overtime, overtime))
    return _trim(out / out.sum())


def _margin_pmf_of(joint: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    rows, columns = joint.shape
    margins = np.arange(-(columns - 1), rows)
    weights = np.array([np.trace(joint, offset=-m) for m in margins], dtype=float)
    return margins.astype(float), weights


# --------------------------------------------------------------------------
# State it, then measure it
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class FitReport:
    """What the fitted distribution's shape is, beside what the sport's is.

    Every row carries its sample size, because a row without one is an opinion.
    """

    games: int
    team_games: int
    season_label: str
    possessions: float
    points_per_possession: float
    measured: dict
    fitted: dict

    def rows(self) -> list[tuple[str, float, float, float]]:
        keys = [k for k in self.measured if k in self.fitted]
        out = []
        for key in keys:
            got, want = float(self.fitted[key]), float(self.measured[key])
            error = (got - want) / want if want else float("nan")
            out.append((key, want, got, error))
        return out

    def table(self) -> str:
        header = (
            "| Quantity | Measured | Fitted | Error |\n|:---|---:|---:|---:|"
        )
        lines = [
            f"| {name} | {want:.4f} | {got:.4f} | {error:+.1%} |"
            for name, want, got, error in self.rows()
        ]
        return "\n".join([header, *lines])

    def summary_line(self) -> str:
        worst = max(
            (abs(e) for _, _, _, e in self.rows() if e == e), default=float("nan")
        )
        return (
            f"{self.season_label}: {self.games:,} games / {self.team_games:,} "
            f"team-games at {self.possessions:.1f} possessions and "
            f"{self.points_per_possession:.4f} points per possession; largest "
            f"discrepancy {worst:.1%}."
        )


def empirical_fit_report(
    team_games: pd.DataFrame, *, season: int | None = None
) -> FitReport:
    """Compare this module's shape against the sport's, and return the numbers.

    The house rule is state-and-then-measure, and this is the measuring. It
    builds one distribution at the frame's own league-average possessions and
    efficiency, and holds it beside the frame's **residual** moments — team
    scores with each team's offence, each opponent's defence and the venue
    removed, which is the quantity the model is trying to be.

    That residual fit is a plain in-sample least squares with no prior and no
    walk-forward guard. **It prices nothing.** It exists to answer "is the
    shape right", it is deliberately not `ratings.fit_ratings`, and using it to
    price anything would be the football lab's pooled-distribution leak with a
    different name.

    Regulation games only: overtime is a separate segment with separate
    measured parameters, and mixing it in here would compare this module's
    regulation distribution against a mixture that is 5.81% something else.
    """
    frame = team_games
    for column in ("game_id", "team_id", "opponent_id", "team_score", "home_away"):
        if column not in frame.columns:
            raise DistributionError(
                f"The team-games frame has no {column!r} column, so the fitted "
                "shape cannot be compared with anything. A report that quietly "
                "skipped the comparison would be worse than none."
            )
    if "game_state" in frame.columns:
        frame = frame[frame["game_state"] == "countable"]
    if season is not None and "season" in frame.columns:
        frame = frame[frame["season"] == season]
    if "periods" in frame.columns:
        frame = frame[frame["periods"] == 2]
    frame = frame.dropna(subset=["team_score", "possessions_estimated"])
    if frame.empty:
        raise DistributionError("No regulation games to measure against.")

    residual, parameters = _residual_scores(frame)
    frame = frame.assign(_residual=residual)
    paired = frame.merge(
        frame[["game_id", "team_id", "_residual"]].rename(
            columns={"team_id": "_other", "_residual": "_residual_other"}
        ),
        on="game_id",
    )
    paired = paired[paired["team_id"] != paired["_other"]]
    home = paired[paired["home_away"] == "home"]
    inflation = len(frame) / max(len(frame) - parameters, 1)

    variance = float(frame["_residual"].var() * inflation)
    covariance = float(
        np.cov(home["_residual"], home["_residual_other"])[0, 1] * inflation
    )
    possessions = float(frame["possessions_estimated"].mean())
    efficiency = float(
        frame["team_score"].sum() / frame["possessions_estimated"].sum()
    )
    measured = {
        "team score sd": float(np.sqrt(variance)),
        "margin sd": float(np.sqrt(max(2.0 * (variance - covariance), 0.0))),
        "total sd": float(np.sqrt(max(2.0 * (variance + covariance), 0.0))),
        "score correlation": covariance / variance if variance else float("nan"),
    }
    if "margin" in frame.columns:
        margins = home["margin"].dropna()
        if len(margins):
            measured["P(|margin| = 3)"] = float((margins.abs() == 3).mean())

    modelled = build(
        home_points_per_possession=efficiency,
        away_points_per_possession=efficiency,
        possessions=possessions,
        segment=FULL_GAME,
        resolves_ties=False,
    )
    home_pmf = modelled.team_pmf(HOME)
    scores = np.arange(home_pmf.size, dtype=float)
    score_mean = float(home_pmf @ scores)
    score_variance = float(home_pmf @ scores**2) - score_mean**2
    margin_values, margin_weights = modelled.margin_pmf()
    margin_mean = float(margin_values @ margin_weights)
    margin_variance = float(margin_weights @ margin_values**2) - margin_mean**2
    total_values, total_weights = modelled.total_pmf()
    total_mean = float(total_values @ total_weights)
    total_variance = float(total_weights @ total_values**2) - total_mean**2
    fitted = {
        "team score sd": float(np.sqrt(score_variance)),
        "margin sd": float(np.sqrt(margin_variance)),
        "total sd": float(np.sqrt(total_variance)),
        "score correlation": float(
            (total_variance - 2.0 * score_variance) / (2.0 * score_variance)
        ),
    }
    if "P(|margin| = 3)" in measured:
        fitted["P(|margin| = 3)"] = float(
            margin_weights[np.abs(margin_values) == 3].sum()
        )
    label = str(season) if season is not None else "all seasons in the frame"
    return FitReport(
        games=int(len(home)),
        team_games=int(len(frame)),
        season_label=label,
        possessions=possessions,
        points_per_possession=efficiency,
        measured=measured,
        fitted=fitted,
    )


def _residual_scores(frame: pd.DataFrame) -> tuple[np.ndarray, int]:
    """Team scores with offence, opposing defence and venue removed.

    In-sample, unregularised, diagnostic. See `empirical_fit_report`: this
    prices nothing and must never be given the chance to.
    """
    teams = sorted(set(frame["team_id"]) | set(frame["opponent_id"]))
    index = {team: position for position, team in enumerate(teams)}
    n = len(teams)
    rows = len(frame)
    design = np.zeros((rows, 2 * n + 3))
    design[np.arange(rows), frame["team_id"].map(index).to_numpy()] = 1.0
    design[np.arange(rows), n + frame["opponent_id"].map(index).to_numpy()] = 1.0
    at_home = (frame["home_away"] == "home").to_numpy()
    venue = (
        frame["venue_state"].to_numpy()
        if "venue_state" in frame.columns
        else np.full(rows, "home")
    )
    for offset, state in enumerate(("home", "neutral", "quasi_neutral")):
        design[:, 2 * n + offset] = np.where(venue == state, 1.0, 0.0) * np.where(
            at_home, 1.0, -1.0
        )
    scores = frame["team_score"].to_numpy(dtype=float)
    ridge = np.eye(2 * n + 3) * 1e-3
    ridge[2 * n :, 2 * n :] *= 1e-6
    beta = np.linalg.solve(design.T @ design + ridge, design.T @ scores)
    return scores - design @ beta, 2 * n + 3
