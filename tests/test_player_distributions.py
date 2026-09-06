"""What `models/player_distributions.py` must be true about before it may price.

The engine turns a projection into count pmfs and, per line, `(win, push, loss)`.
Nothing here measures an edge, a loss, a de-vigged price or a verdict: every
number below is either read off a fixture, read off the frozen constants, or is
a **structural check** — what the assembled mixture reproduces against a target
nothing in the engine can influence — and each one says which it is.

The properties, and the specific defect each is arranged against:

* **the Panjer member is chosen by the conditional dispersion, and the binomial
  arm is real.** `turnovers` measures 0.9829 on the fit window and 0.9979 held
  out, and a negative binomial cannot reach a variance below its mean at any
  parameter. The branch is asserted against the string the FROZEN FILE recorded
  for each of the seven stats on both windows, so the file checks the code
  rather than the code checking itself;
* **points is a compound sum, not a count** — `S = sum V_i` over the athlete's
  own shrunk 1/2/3 mix, so `P(exactly 1 point)` is below `P(0)` because one
  point is one made free throw and nothing else, and the engine's points mean is
  `rates["points_events"] * minutes * E[V]` rather than `rates["points"] *
  minutes`;
* **`player_threes` is the same object thinned**, not a second count, so
  design 4's `corr(points, threes)` check is produced rather than imposed;
* **the minutes channel is applied exactly once**, asserted as the law of total
  variance against the per-node objects and not as a comment;
* **the lattice carries exactly zero mass at zero minutes**, because the book
  voids a did-not-play — asserted by pricing one athlete against two shapes
  files differing only in `dnp_base_rate` and demanding bit-identical pmfs;
* **every constant comes from the frozen file through `player_shapes`**, checked
  three ways: the loader is the only reader, no float literal in the module
  equals a frozen constant, and changing a constant changes the price.

D1 is the one that catches `distributions._match_variance`, and it is run
against the comb itself inside the test rather than described in a docstring.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from cbb_betting_lab.models import distributions as D
from cbb_betting_lab.models import player_distributions as PD
from cbb_betting_lab.models import player_rates as PR
from cbb_betting_lab.models.player_shapes import load_player_shapes

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "src" / "cbb_betting_lab" / "models" / "player_distributions.py"
SHAPES = REPO / "data" / "processed" / "cbb_player_shapes.json"

#: The season every prop quote in the store belongs to, and the only season the
#: 33 pre-registered hypotheses name.
PRICED_SEASON = 2024
DAY = "2024-01-15"

#: The interior of a count pmf, for D1: every rung carrying at least this much
#: of the modal mass. DECLARED HERE, and the reason is a disagreement with the
#: design that is reported rather than patched — see
#: :func:`test_d1_no_priced_pmf_carries_the_match_variance_comb`.
D1_INTERIOR_FLOOR = 0.15


# --------------------------------------------------------------------------
# Fixtures. Every projection is built by the real estimator from a cut frame,
# never assembled by hand, so what is priced here is what would be priced.
# --------------------------------------------------------------------------


def _shapes(priced_season: int = PRICED_SEASON):
    return load_player_shapes(SHAPES, priced_season=priced_season)


def _shapes_with(tmp_path: Path, mutate, *, name: str = "shapes.json"):
    """The frozen file with one thing changed, loaded through the real guard.

    Through :func:`load_player_shapes`, never `json.load`: an instance existing
    IS the evidence the provenance guard ran, and a test that built a
    `PlayerShapes` by hand would be testing a path no price can take.
    """
    document = json.loads(SHAPES.read_text(encoding="utf-8"))
    mutate(document)
    path = tmp_path / name
    path.write_text(json.dumps(document), encoding="utf-8")
    return load_player_shapes(path, priced_season=PRICED_SEASON)


def _rates_fixture():
    """`tests/test_player_rates.py`, loaded for its row builders and nothing else.

    Imported by path rather than copied. The alternative is a second fixture
    frame that drifts from the estimator's own, and this repository has the
    two-copies-of-one-thing family written down five times.
    """
    spec = importlib.util.spec_from_file_location(
        "player_rates_fixtures", REPO / "tests" / "test_player_rates.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _projection(shapes=None, **overrides) -> PR.PlayerProjection:
    fixtures = _rates_fixture()
    slate = PR.player_projections_for(
        day=DAY,
        player_history=fixtures._history(**overrides),
        prices=fixtures._prices("Sean Bairstow"),
        shapes=shapes or _shapes(),
    )
    projection = fixtures._one(slate)
    assert projection.priceable is True, projection.unpriceable_reason
    return projection


def _distribution(shapes=None, **overrides) -> PD.PlayerDistribution:
    resolved = shapes or _shapes()
    return PD.build(_projection(resolved, **overrides), shapes=resolved)


def _moments(pmf: np.ndarray) -> tuple[float, float]:
    counts = np.arange(len(pmf), dtype=float)
    mean = float(np.asarray(pmf) @ counts)
    return mean, float(np.asarray(pmf) @ (counts * counts)) - mean * mean


def _interior_ratios(pmf: np.ndarray, floor: float = D1_INTERIOR_FLOOR) -> np.ndarray:
    live = np.flatnonzero(pmf >= floor * pmf.max())
    low, high = int(live[0]), int(live[-1])
    return pmf[low + 1 : high + 1] / pmf[low:high]


def _the_comb(mean: float = 9.0, dispersion: float = 2.3289) -> np.ndarray:
    """A player points count built the refused way, at the same two moments.

    `distributions._match_variance` applied to a Poisson lattice and asked for
    the frozen conditional points VMR. This is the object design 4 refuses, and
    D1 runs against it so the band is shown to still catch what it exists for.
    """
    counts = np.arange(80, dtype=float)
    base = np.array(
        [math.exp(-mean) * mean**k / math.factorial(k) for k in range(80)]
    )
    return D._match_variance(base / base.sum(), counts, mean * dispersion)


# --------------------------------------------------------------------------
# The Panjer member, and the arm that is the whole reason for the family
# --------------------------------------------------------------------------


def test_the_panjer_member_is_selected_by_the_conditional_dispersion() -> None:
    """Design 4's rule, and the binomial arm exercised rather than described.

    Below one a binomial, at one a Poisson, above one a negative binomial. The
    first branch is not decoration: a negative binomial has variance
    `mu * (1 + beta)` with `beta > 0`, so it cannot represent a variance below
    its mean at ANY parameter value, and `turnovers` is genuinely below —
    0.9828561088984643 on the fit window. "Just use a negative binomial" is not
    a simplification of this engine, it is a different and wrong answer on one
    of the ten markets, and this test prices the binomial arm to prove it runs.
    """
    frozen = _shapes().value("conditional_dispersion")
    assert PD.panjer_family(frozen["turnovers"]) == "binomial"
    assert PD.panjer_family(frozen["rebounds"]) == "negative_binomial"
    assert PD.panjer_family(1.0) == "poisson"

    # The arm actually produces a distribution, and it is underdispersed.
    parameters = PD.panjer_parameters(mu=1.9, phi=frozen["turnovers"])
    assert parameters.family == "binomial"
    pmf = PD.compound_pmf(parameters, severity=(0.0, 1.0), size=40)
    mean, variance = _moments(pmf)
    assert mean == pytest.approx(1.9, abs=1e-12)
    assert variance < mean, (
        "the binomial arm produced a count whose variance is not below its "
        "mean, which is the only property it exists for"
    )
    assert variance / mean == pytest.approx(parameters.phi_used, abs=1e-9)
    assert pmf.min() >= 0.0, "the (a,b,0) recursion emitted negative mass"

    # And it is a real market read off a real object, not a bare family.
    turnovers = _distribution().count_pmf("player_turnovers")
    turnover_mean, turnover_variance = _moments(turnovers)
    assert turnover_variance > turnover_mean, (
        "the UNCONDITIONAL turnovers count is overdispersed even though the "
        "conditional one is not, because the minutes mixture adds "
        "`r * Var(M)/E(M)`. That is the whole reason the dispersion constants "
        "are conditional, and a family chosen on the unconditional number "
        "would never select the binomial at all."
    )


def test_the_panjer_member_matches_the_frozen_files_own_recorded_family() -> None:
    """The FILE checks the CODE, on both windows and all seven stats.

    `conditional_dispersion.evidence.<window>.<stat>.panjer_family` is a string
    the fitter wrote down. Asserting the engine's branch against it is a
    different claim from asserting the engine agrees with itself: if a later
    refit moved a dispersion across one, this goes red on the constant rather
    than on the code.
    """
    shapes = _shapes()
    evidence = shapes.document["constants"]["conditional_dispersion"]["evidence"]
    spelling = {"negative binomial": "negative_binomial", "binomial": "binomial"}
    for window, values in (
        ("fit", shapes.value("conditional_dispersion")),
        ("held_out", shapes.held_out_value("conditional_dispersion")),
    ):
        for stat, dispersion in values.items():
            recorded = spelling[evidence[window][stat]["panjer_family"]]
            assert PD.panjer_family(dispersion) == recorded, (
                f"{window}/{stat}: the frozen file recorded "
                f"{recorded!r} and this engine selects "
                f"{PD.panjer_family(dispersion)!r} at phi={dispersion}"
            )
    assert dict(PD.held_out_panjer_families(shapes))["turnovers"] == "binomial", (
        "the binomial arm must be the arm on the HELD-OUT window too, or it is "
        "one window's rounding rather than an underdispersed market"
    )


def test_the_poisson_band_does_not_swallow_the_binomial_arm() -> None:
    """`POISSON_BAND` is a degeneracy epsilon and must not be a materiality floor.

    The frozen turnovers dispersion sits 0.0171 below one, and
    `conditional_dispersion.material_absolute` is 0.02. A band set to the
    materiality floor — the obvious-looking choice, and the one the contract
    warned about — would call turnovers Poisson on BOTH windows and delete the
    branch design 4 spends a paragraph justifying.
    """
    shapes = _shapes()
    fit = shapes.value("conditional_dispersion")["turnovers"]
    held_out = shapes.held_out_value("conditional_dispersion")["turnovers"]
    material = shapes.document["constants"]["conditional_dispersion"][
        "material_absolute"
    ]

    assert PD.POISSON_BAND < abs(1.0 - fit)
    assert PD.POISSON_BAND < abs(1.0 - held_out)
    assert PD.panjer_family(fit) == PD.panjer_family(held_out) == "binomial"

    assert abs(1.0 - fit) < material, (
        "the frozen turnovers dispersion is no longer inside the fit's own "
        "materiality floor, so the trap this test guards has moved; re-measure "
        "the sentence below rather than deleting it"
    )
    assert PD.POISSON_BAND != material, (
        "POISSON_BAND has been set to the dispersion constant's materiality "
        "floor. That is a band of 0.02 around one, the frozen turnovers phi is "
        f"{abs(1.0 - fit):.4f} from one, and the binomial branch disappears."
    )


def test_the_binomial_rounding_preserves_the_mean_and_reports_its_own_error() -> None:
    """`n` is not an integer at any (mu, phi) the store carries, and must be one.

    Arithmetic on the frozen turnovers dispersion: `1 - phi = 0.0171439`, so
    `n = mu/(1-phi)` is 58.33 at mu = 1.0, 99.16 at 1.7 and 174.99 at 3.0. The
    (a,b,0) recursion runs past `-b/a = n+1` on a non-integer `n` and emits
    negative mass, so the convention is `n = round(...)` followed by a re-solve
    of `p = mu/n`.

    Measured here across mu in [0.2, 6.0] at 0.01: the mean is preserved to
    **exactly zero** error, and the largest |phi_used - phi| is **5.484e-04**,
    which is 2.74% of the fit's own materiality floor of 0.02. The rounding is
    charged to the dispersion, the row says how much, and D3 and D5 — both
    first-moment identities — pay nothing for it.
    """
    dispersion = _shapes().value("conditional_dispersion")["turnovers"]
    worst = 0.0
    for mu in np.arange(0.2, 6.001, 0.01):
        parameters = PD.panjer_parameters(mu=float(mu), phi=dispersion)
        assert parameters.mu == float(mu), "the rounding moved the mean"
        assert float(parameters.trials).is_integer()
        worst = max(worst, abs(parameters.phi_used - dispersion))
    assert worst == pytest.approx(5.484e-04, abs=1e-6), (
        f"the binomial rounding error is now {worst:.3e}; the docstring above "
        "quotes 5.484e-04 and must be re-measured"
    )
    assert worst < 0.02, "the rounding moved the dispersion materially"


# --------------------------------------------------------------------------
# The points object, and the two markets that fall out of it
# --------------------------------------------------------------------------


def test_points_is_a_compound_sum_over_the_value_pmf_and_not_a_count() -> None:
    """`S = sum_{i=1..N} V_i`, with three consequences a count cannot have.

    1. **The mean is the compound one.** `rates["points_events"] * minutes *
       E[V_player]`, not `rates["points"] * minutes`. `player_rates`' own
       comment says which is which: "the compound is the price and
       `rates['points']` is the check". On this fixture the two differ by
       **1.639%**, which is stored as a diagnostic and asserted against nothing.
    2. **`P(1 point)` sits BELOW `P(0 points)`.** One point is one made free
       throw and nothing else, and the athlete's shrunk mix puts 0.293 on a
       one-pointer, so the pmf dips at one. No count family can do that at a
       positive mean, and it is not a comb: the dip is the severity's, and it
       appears at exactly one rung.
    3. **The dispersion handed to the family is the EVENT count's**, and the
       points marginal's own dispersion is produced from it through the
       compound identity `VMR = E[V^2]/E[V] + (phi-1)*E[V]`.
    """
    shapes = _shapes()
    distribution = _distribution(shapes)
    projection = distribution.projection
    mix = np.asarray(projection.value_pmf)
    values = np.array([1.0, 2.0, 3.0])
    first = float(mix @ values)

    minutes = float(projection.projected_minutes)
    compound = float(projection.rates["points_events"]) * minutes * first
    assert distribution.mean("player_points") == pytest.approx(compound, rel=1e-9)
    assert PR.mean_for_market(projection, "player_points") == pytest.approx(
        float(projection.rates["points"]) * minutes, rel=1e-12
    )
    gap = distribution.diagnostics()["points_mean_relative_gap"]
    assert gap == pytest.approx(0.016386, abs=1e-5), (
        f"the two mean routes now differ by {gap:.6f}; the docstring quotes "
        "1.639% and design 12 registers it descriptive-only"
    )

    pmf = distribution.count_pmf("player_points")
    assert pmf[1] < pmf[0] < pmf[2], (
        "a compound sum over {1,2,3} dips at one point, because one point is "
        "one made free throw. A Panjer count cannot produce that shape and its "
        "absence is how a compound engine silently becomes a count engine."
    )

    node = distribution.price_node()
    handed = distribution.event_parameters[node]
    assert handed.phi_used == pytest.approx(
        shapes.value("points_compound_reconciliation")["effective_event_dispersion"],
        abs=1e-15,
    )
    conditional_mean, conditional_variance = _moments(
        distribution.node_component_pmf("points", node)
    )
    second = float(mix @ (values * values))
    predicted = second / first + (handed.phi_used - 1.0) * first
    assert conditional_variance / conditional_mean == pytest.approx(
        predicted, rel=1e-9
    ), "the produced points VMR is not the compound identity's"


def test_threes_is_the_same_object_thinned_and_not_a_second_count() -> None:
    """Design 4: threes "falls out as the three-point component of the same object".

    Thinning an (a,b,0) member at `q` keeps the family and produces
    `VMR = 1 + q*(phi - 1)` for every member, so the three-point marginal's
    width is a consequence of the shared scoring-event count rather than a
    second fitted number. `rates["threes"]` and
    `conditional_dispersion["threes"]` are therefore CHECK quantities, and both
    are computed and reported here and neither is used to form the price.
    """
    shapes = _shapes()
    distribution = _distribution(shapes)
    projection = distribution.projection
    share = float(projection.value_pmf[2])
    node = distribution.price_node()
    events = distribution.event_parameters[node]

    thinned = PD.thin(events, share)
    assert thinned.family == events.family, "thinning changed the family"
    assert thinned.mu == pytest.approx(events.mu * share, rel=1e-12)
    assert thinned.phi_used == pytest.approx(
        1.0 + share * (events.phi_used - 1.0), rel=1e-12
    )

    mean, variance = _moments(distribution.node_component_pmf("threes", node))
    assert variance / mean == pytest.approx(thinned.phi_used, rel=1e-9)

    # The check quantities, reported. The thinned marginal is measurably
    # NARROWER than the standalone constant, and design 4 declares a tolerance
    # for the unconditional points VMR and for nothing else, so this is
    # report-only and may not be tuned.
    checks = distribution.structural_checks()
    assert checks["threes_vmr_given_minutes"] < checks["threes_vmr_given_minutes_target"]
    assert checks["threes_vmr_given_minutes"] == pytest.approx(1.028896, abs=1e-5)
    assert checks["threes_vmr_given_minutes_target"] == pytest.approx(
        1.0846864899201918, abs=1e-12
    )

    for name in ("threes", "points"):
        assert name in projection.rates, (
            "the standalone rate must still exist, because it is the check; "
            "deleting it would make the disagreement invisible instead of "
            "reported"
        )
    assert distribution.diagnostics()["threes_mean_relative_gap"] == pytest.approx(
        0.006817, abs=1e-5
    )


def test_the_points_threes_correlation_identity_matches_a_brute_force_joint() -> None:
    """Design 4's second free check, verified against an enumerated joint.

    `points_threes_correlation` is three lines of algebra, and three lines of
    algebra asserted against themselves prove nothing. Here the same quantity is
    built by enumerating the scoring-event count and the multinomial over
    {1,2,3} inside it, which shares no code with the identity. They agree to
    2e-16.

    The produced number is then reported beside the frozen target, and it does
    NOT reproduce it: at the league value mix the thinning produces 0.6706
    against a frozen 0.6021705535430947, and at this fixture's own three-heavy
    mix it produces 0.7466. No tolerance is declared for this check anywhere in
    the design or the frozen file, so it is reported and stops nothing — and
    nothing is tuned to close it.
    """
    shapes = _shapes()
    mix = _distribution(shapes).projection.value_pmf
    dispersion = shapes.value("points_compound_reconciliation")[
        "effective_event_dispersion"
    ]

    for mu, cap in ((0.9, 25), (3.0, 32)):
        counts = PD.compound_pmf(
            PD.panjer_parameters(mu=mu, phi=dispersion), severity=(0.0, 1.0), size=cap
        )
        joint = np.zeros((cap * 3 + 1, cap + 1))
        for events in range(cap + 1):
            if counts[events] < 1e-20:
                continue
            for threes in range(events + 1):
                for twos in range(events - threes + 1):
                    ones = events - threes - twos
                    weight = (
                        math.factorial(events)
                        / (math.factorial(ones) * math.factorial(twos) * math.factorial(threes))
                        * mix[0] ** ones
                        * mix[1] ** twos
                        * mix[2] ** threes
                    )
                    joint[ones + 2 * twos + 3 * threes, threes] += counts[events] * weight
        points = np.arange(joint.shape[0])[:, None]
        threes_axis = np.arange(joint.shape[1])[None, :]
        mean_points = float((joint * points).sum())
        mean_threes = float((joint * threes_axis).sum())
        brute = (float((joint * points * threes_axis).sum()) - mean_points * mean_threes) / math.sqrt(
            (float((joint * points * points).sum()) - mean_points**2)
            * (float((joint * threes_axis * threes_axis).sum()) - mean_threes**2)
        )
        assert PD.points_threes_correlation(
            mu_events=mu, phi_events=dispersion, value_pmf=mix
        ) == pytest.approx(brute, abs=1e-12)

    league = PD.points_threes_correlation(
        mu_events=5.0, phi_events=dispersion, value_pmf=shapes.value("value_pmf")
    )
    target = shapes.value("structural_check_targets")["corr_points_threes_given_minutes"]
    assert league == pytest.approx(0.6706, abs=5e-4)
    assert target == pytest.approx(0.6021705535430947, abs=1e-12)
    assert league > target, (
        "the thinning now produces a correlation at or below the frozen "
        "target; the docstring above reports it as 11.4% high and must be "
        "re-measured"
    )


# --------------------------------------------------------------------------
# D1 -- the comb
# --------------------------------------------------------------------------


def test_d1_no_priced_pmf_carries_the_match_variance_comb() -> None:
    """Design 4's smoothness band, with the object it exists to catch run beside it.

    The band is `[0.4, 2.5]` on adjacent-integer ratios across the interior
    support. Measured on this fixture, over the ten priced markets, the worst
    ratios are **0.489** and **2.042**; the same measurement on
    `_match_variance` at the same two moments gives **0.392** and **2.751**, so
    the band still catches the comb on both edges. The comb's largest adjacent
    swing — the ratio of one ratio to the next — is **5.07**, which is the
    design's "adjacent-integer swings of ~5x", against **2.89** for the
    engine's worst market.

    **A DISAGREEMENT WITH THE DESIGN, reported rather than patched.** "Interior
    support" has to be defined and the design does not define it. Over the whole
    live support the band is FALSE for a smooth family: a near-Poisson count
    with a mean of 0.96 has ratio `lambda/k = 0.32` at its third rung and
    `player_steals` measures 0.359 there, so a band asserted over every rung
    would fail on a distribution with nothing wrong with it and would then have
    to be weakened, which is worse than declaring the region now.
    :data:`D1_INTERIOR_FLOOR` is therefore declared at 0.15 of the modal mass —
    the rungs within a factor of about seven of the mode — and the comb is
    measured under exactly the same rule.
    """
    distribution = _distribution()
    lowest, highest, swing = 1.0, 1.0, 1.0
    for market in PR.MARKET_COMPONENTS:
        ratios = _interior_ratios(distribution.count_pmf(market))
        assert ratios.size >= 2, market
        assert ratios.min() >= 0.4, f"{market} dips to {ratios.min():.4f}"
        assert ratios.max() <= 2.5, f"{market} spikes to {ratios.max():.4f}"
        lowest = min(lowest, float(ratios.min()))
        highest = max(highest, float(ratios.max()))
        steps = ratios[1:] / ratios[:-1]
        swing = max(swing, float(np.max(np.maximum(steps, 1.0 / steps))))
    assert lowest == pytest.approx(0.489, abs=5e-3)
    assert highest == pytest.approx(2.042, abs=5e-3)
    assert swing == pytest.approx(2.89, abs=0.02)

    comb = _interior_ratios(_the_comb())
    assert comb.min() < 0.4 and comb.max() > 2.5, (
        "the refused `_match_variance` object now passes D1 under the interior "
        "rule declared here, so the band has stopped catching what it exists "
        "for. Do not widen the band; find out what changed."
    )
    comb_steps = comb[1:] / comb[:-1]
    comb_swing = float(np.max(np.maximum(comb_steps, 1.0 / comb_steps)))
    assert comb_swing == pytest.approx(5.07, abs=0.02)
    assert comb_swing > swing * 1.5


def test_no_player_count_is_built_by_match_variance() -> None:
    """The refusal as a checked fact, read off the AST rather than off a comment.

    Design 4 refuses `_match_variance` for player counts and this module must
    not reach it by any route: not an import, not an attribute access on the
    `distributions` module, not a re-implementation under another name. The
    scan reads every name the module touches, so `from ... import
    _match_variance as _smooth` is caught too.
    """
    tree = ast.parse(MODULE.read_text(encoding="utf-8"), filename=str(MODULE))
    touched: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            touched.add(node.attr)
        elif isinstance(node, ast.Name):
            touched.add(node.id)
        elif isinstance(node, ast.ImportFrom):
            touched.update(alias.name for alias in node.names)
            touched.update(alias.asname or "" for alias in node.names)
        elif isinstance(node, ast.Import):
            touched.update(alias.name for alias in node.names)
    for refused in (
        "_match_variance",
        "_match_variance_batch",
        "_match_variance_reference",
        "_trip_count_pmfs",
    ):
        assert refused not in touched, (
            f"{refused} is reachable from the player engine. It is refused for "
            "player counts: at c ~ 1.8 the linear split aliases source integers "
            "into a comb with ~5x adjacent swings at identical mean and "
            "variance."
        )
    assert "distributions" not in touched, (
        "the player engine now names the team distribution module. Nothing in "
        "it is refused wholesale, but the two are separate objects and the "
        "refusal above is easiest to defeat one attribute at a time."
    )


# --------------------------------------------------------------------------
# D2 to D5
# --------------------------------------------------------------------------


def test_d2_the_ladder_is_monotone_off_one_cached_object() -> None:
    """P(over) strictly decreasing in the line, on every rung of one object.

    Off ONE object, which is the content of it: the football lab shipped a
    ladder whose -6.5 was better value than its -7.5 because it had two models
    for one quantity. There is no alternate-ladder path here and there must
    never be one.
    """
    distribution = _distribution()
    for market, lines in (
        ("player_points", np.arange(4.5, 24.0, 1.0)),
        ("player_rebounds", np.arange(1.5, 11.0, 1.0)),
        ("player_threes", np.arange(0.5, 5.0, 1.0)),
        ("player_pra", np.arange(12.5, 32.0, 1.0)),
    ):
        rungs = distribution.ladder(lines, market_key=market, side="over")
        overs = [triple[0] for _, triple in rungs]
        assert all(a > b for a, b in zip(overs, overs[1:])), market
        unders = [
            triple[0]
            for _, triple in distribution.ladder(lines, market_key=market, side="under")
        ]
        assert all(a < b for a, b in zip(unders, unders[1:])), market
        for (line, triple), under in zip(rungs, unders):
            assert triple[0] + triple[1] + under == pytest.approx(1.0, abs=1e-12)


def test_d3_the_combination_markets_agree_with_their_components() -> None:
    """A points line and a pra line on one player cannot disagree, to 1e-9.

    Asserted on the ENGINE's price means, which for points and threes are the
    compound ones and not `player_rates.mean_for_market`'s. It holds because the
    copula does not move a marginal — :func:`player_distributions._fit_marginals`
    is what makes that an identity rather than a quadrature accident — and
    because every market reads the same per-node component arrays.

    Measured here: pra misses the sum of its three components by 1.4e-14.
    """
    distribution = _distribution()
    for market, components in PR.MARKET_COMPONENTS.items():
        parts = sum(
            distribution.mean(f"player_{stat}") for stat in components
        )
        assert distribution.mean(market) == pytest.approx(parts, abs=1e-9), market

    assert distribution.mean("player_pra") == pytest.approx(
        sum(
            distribution.mean(market)
            for market in ("player_points", "player_rebounds", "player_assists")
        ),
        abs=1e-9,
    )

    # The rate route's own identity still holds where the two routes agree: the
    # four plain Panjer stats are `rate * E[M]` on both sides, because the
    # minutes lattice is tilted to `projected_minutes`.
    projection = distribution.projection
    for stat in ("rebounds", "assists", "steals", "turnovers"):
        assert distribution.mean(f"player_{stat}") == pytest.approx(
            float(projection.rates[stat]) * float(projection.projected_minutes),
            rel=1e-9,
        ), stat


def test_d4_the_lattice_carries_no_mass_at_zero_minutes(tmp_path: Path) -> None:
    """The book VOIDS a did-not-play, so `dnp_probability` may not reach a price.

    Two assertions, and the second is the one that cannot be argued with: the
    same athlete is priced against two shapes files differing ONLY in
    `dnp_base_rate`, and every pmf must come back bit-identical. A discount
    applied anywhere on the path would move them.

    The engine also re-checks `minutes_pmf[0] == 0.0` itself rather than
    trusting the estimator's guarantee, with `is`-strength equality and not a
    tolerance, because the whole content of the claim is that the priced
    quantity is `P(stat > line | the wager stands)`.
    """
    distribution = _distribution()
    assert distribution.projection.minutes_pmf[0] == 0.0
    assert distribution.minutes.min() >= 1.0

    def _raise_dnp(document: dict) -> None:
        base = document["constants"]["dnp_base_rate"]["value"]
        document["constants"]["dnp_base_rate"]["value"] = [
            min(0.99, float(value) * 3.0 + 0.2) for value in base
        ]

    other = _shapes_with(tmp_path, _raise_dnp)
    moved = PD.build(_projection(other), shapes=other)
    assert moved.void_probability() != distribution.void_probability(), (
        "the fixture did not actually move `dnp_probability`, so the identity "
        "below is vacuous"
    )
    for market in PR.MARKET_COMPONENTS:
        assert np.array_equal(
            moved.count_pmf(market), distribution.count_pmf(market)
        ), f"{market} moved when only `dnp_base_rate` changed"

    # And a lattice that DID carry mass at zero is refused rather than priced.
    projection = distribution.projection
    leaking = list(projection.minutes_pmf)
    leaking[0] = 0.05
    leaking[20] -= 0.05
    with pytest.raises(PD.PlayerDistributionError, match="zero minutes"):
        PD.build(
            PR.PlayerProjection(
                **{
                    **{
                        field.name: getattr(projection, field.name)
                        for field in __import__("dataclasses").fields(projection)
                    },
                    "minutes_pmf": tuple(leaking),
                }
            ),
            shapes=_shapes(),
        )


def test_d5_the_coincident_window_identity_holds_at_the_engine_level() -> None:
    """Rate window == minutes window, shrinkage off: the price mean IS the trailing mean.

    `player_rates` asserts this on the rate; the same identity has to survive
    the lattice and the Panjer family, or the engine has quietly introduced a
    second opinion about the first moment. Composed from `shrink_rate` with
    `k = 0` exactly as the estimator's own D5 does — there is deliberately no
    `shrinkage=False` flag anywhere, because this repository treats a mode flag
    as the `strict=False` a guard cannot have.
    """
    fixtures = _rates_fixture()
    shapes = _shapes()
    evidence = PR.trailing_evidence(fixtures._history(), half_life=4.0).iloc[0]
    prior_minutes = float(evidence["prior_minutes"])
    prior_games = int(evidence["prior_games"])
    coincident = prior_minutes / prior_games

    rates: dict[str, float] = {}
    for stat in PR.STAT_KEYS:
        rate, weight = PR.shrink_rate(
            bank_stat=float(evidence[f"bank_{stat}"]),
            prior_minutes=prior_minutes,
            prior_rate=0.0,
            k=0.0,
        )
        assert weight == 1.0
        rates[stat] = rate

    bucket = PR.role_prior_bucket(
        coincident, bucket_edges=shapes.document["declared"]["bucket_edges"]
    )
    lattice = PR.minutes_lattice(
        projected_minutes=coincident, bucket=bucket, shapes=shapes
    )
    unshrunk = PR.PlayerProjection(
        event_id="e1",
        athlete_id=4001.0,
        projected_minutes=coincident,
        minutes_bucket=bucket,
        minutes_pmf=lattice,
        rates=rates,
        value_pmf=(1 / 3, 1 / 3, 1 / 3),
        dnp_probability=0.0,
        priceable=True,
    )
    distribution = PD.build(unshrunk, shapes=shapes)
    for stat in ("rebounds", "assists", "steals", "turnovers"):
        direct = float(evidence[f"bank_{stat}"]) / prior_games
        assert distribution.mean(f"player_{stat}") == pytest.approx(direct, abs=1e-9), (
            f"{stat}: the engine's price mean is not the direct trailing mean "
            "at a coincident window with the shrinkage off"
        )


# --------------------------------------------------------------------------
# The order of operations
# --------------------------------------------------------------------------


def test_the_minutes_channel_is_applied_exactly_once_and_the_order_is_fixed() -> None:
    """Design 5's ordering rule, as three numbers rather than as a comment.

    1. **Exactly once.** The market's variance equals the law of total variance
       taken over the per-node objects — `E_m[Var(X|m)] + Var_m[E(X|m)]` — to
       2.8e-14 on pra. That is the assertion that the mixture entered once, and
       entered where the order says.
    2. **The copula is inside the node.** Coupling the already-mixed components
       instead leaves the mean alone (to 1e-9) and changes the width by a
       measured amount, so the order is a checked fact.
    3. **The direction, measured, and it is not the one the contract predicted.**
       At the frozen RESIDUAL correlations, mix-then-couple comes out **10.6%
       NARROWER** in standard deviation, not wider — algebraically, because
       coupling after the mixture drops the shared-minutes covariance
       `2*sum_{i<j} r_i*r_j*Var(M)` and replaces it with
       `2*sum rho*sd_i*sd_j` at rho ~ 0.1. Design 5's "pra ~15% too wide" is
       about the OTHER version of the same mistake, and clause 3 below
       reproduces it: at the trailing-minutes scale the frozen note describes
       ("on trailing minutes these run around 0.4"), mix-then-couple is 6.4%
       wider. 0.4 is prose in the file's own note and not a frozen constant, so
       it is written here as a fixture and never read by the engine.
    """
    distribution = _distribution()
    pra = distribution.count_pmf("player_pra")
    mean, variance = _moments(pra)

    nodes = [
        distribution.node_market_pmf("player_pra", index)
        for index in range(distribution.minutes.size)
    ]
    weights = distribution.minutes_weight
    within = float(sum(w * _moments(node)[1] for w, node in zip(weights, nodes)))
    node_means = np.array([_moments(node)[0] for node in nodes])
    between = float(weights @ (node_means**2) - (weights @ node_means) ** 2)
    assert variance == pytest.approx(within + between, abs=1e-9), (
        "the assembled pra variance is not the law of total variance over the "
        "per-node objects, so the minutes channel did not enter exactly once"
    )
    assert mean == pytest.approx(float(weights @ node_means), abs=1e-9)

    components = ("points", "rebounds", "assists")
    mixed = [distribution.component_pmf(stat) for stat in components]
    residual = distribution._correlation_matrix(components)

    wrong_order = PD.coupled_sum_pmf(mixed, residual)
    wrong_mean, wrong_variance = _moments(wrong_order)
    assert wrong_mean == pytest.approx(mean, abs=1e-9), (
        "the two orders must agree on the mean; if they do not, the copula is "
        "moving a marginal and D3 is next"
    )
    ratio = math.sqrt(wrong_variance / variance)
    assert ratio == pytest.approx(0.894, abs=5e-3), (
        f"mix-then-couple now gives a width ratio of {ratio:.4f}; the "
        "docstring quotes 10.6% narrower and must be re-measured"
    )

    trailing = np.full((3, 3), 0.4)
    np.fill_diagonal(trailing, 1.0)
    double_counted = PD.coupled_sum_pmf(mixed, trailing)
    wide = math.sqrt(_moments(double_counted)[1] / variance)
    assert wide > 1.0, (
        "applying a trailing-scale correlation after the mixture is design 5's "
        "double count and must come out wider than the declared order"
    )
    assert wide == pytest.approx(1.064, abs=5e-3)

    assert distribution.construction_order == (
        "minutes_lattice",
        "conditional_panjer_or_compound",
        "residual_copula",
        "component_sum",
        "mix_over_minutes",
    )


def test_the_copula_is_deterministic_and_reduces_to_a_convolution() -> None:
    """Two properties L1 and D3 both need, asserted at floating-point strength.

    **Independence.** With every off-diagonal exactly zero the coupled sum must
    be `np.convolve`, not approximately: the quadrature weights in probability
    space sum over each cell to that count's own mass, so the joint factorises
    exactly. Measured here at 1e-16, which is the arithmetic and not a
    tolerance.

    **Determinism.** Re-pricing the same object twice must be bit-identical.
    There is no RNG in the engine and there must never be one — scipy's
    `multivariate_normal.cdf` is randomised for three or more dimensions, which
    is exactly the case pra needs, and L1's re-price check would fail on it
    intermittently rather than always.
    """
    distribution = _distribution()
    node = distribution.price_node()
    rebounds = distribution.node_component_pmf("rebounds", node)
    assists = distribution.node_component_pmf("assists", node)
    points = distribution.node_component_pmf("points", node)

    pair = PD.coupled_sum_pmf([rebounds, assists], np.eye(2))
    assert np.abs(pair - np.convolve(rebounds, assists)).max() < 1e-15

    triple = PD.coupled_sum_pmf([rebounds, assists, points], np.eye(3))
    assert np.abs(
        triple - np.convolve(np.convolve(rebounds, assists), points)
    ).max() < 1e-15

    # A non-zero correlation must actually change the answer, or the test above
    # is asserting that a no-op is a no-op.
    coupled = PD.coupled_sum_pmf(
        [rebounds, assists, points],
        distribution._correlation_matrix(("rebounds", "assists", "points")),
    )
    assert np.abs(coupled - triple).max() > 1e-6

    again = _distribution()
    for market in PR.MARKET_COMPONENTS:
        assert np.array_equal(
            again.count_pmf(market), distribution.count_pmf(market)
        ), f"{market} is not bit-identical on a re-price"

    with pytest.raises(PD.PlayerDistributionError, match="positive definite"):
        PD.coupled_sum_pmf([rebounds, assists], np.array([[1.0, 1.4], [1.4, 1.0]]))

    # A component that is a point mass owns the whole latent line as ONE cell,
    # which is the case the outer-cell split has to decline to split. It cannot
    # arise from a Panjer family at a positive mean, so it is exercised here
    # rather than waited for.
    certain = np.array([0.0, 0.0, 1.0])
    for rho in (0.0, 0.10523131793586692):
        matrix = np.array([[1.0, rho], [rho, 1.0]])
        shifted = PD.coupled_sum_pmf([certain, rebounds], matrix)
        assert np.abs(shifted - np.convolve(certain, rebounds)).max() < 1e-15, (
            "a point-mass component must shift the other one and change "
            "nothing else, at any correlation"
        )


def test_the_realised_correlation_is_reported_and_the_two_copula_routes_agree() -> None:
    """What the copula actually applied, beside what it was asked for.

    Two claims, and the second is a cross-check between two independent code
    paths rather than a check of one path against itself.

    1. **Reported, not solved.** The off-diagonals are the measured Pearson
       correlations OF THE COUNTS, and discretising a latent normal onto integer
       counts loses a little of any correlation. Measured on this fixture at its
       modal node: `points|rebounds` asked 0.10523131793586692 and realises
       0.10333, `rebounds|assists` asked 0.05817638552684023 and realises
       0.05601, `points|assists` asked -0.016618706383100403 and realises
       -0.01605. All three are within 4% relative, all three are low in absolute
       value, and none is solved back onto its target.
    2. **The three-component path and the two-component path agree.** pra runs
       through the trivariate branch and the pairs run through the bivariate
       one, so `Var(P+R+A)` from the first must equal
       `sum Var + 2 sum Cov` with each covariance taken from the second.
       Measured agreement: 1.7e-09 relative. Nothing else in this file compares
       the two branches, and without it the conditioning inside the trivariate
       branch could be wrong by a whole term with every other test still green.
    """
    distribution = _distribution()
    node = distribution.price_node()
    realised = distribution.realised_correlations()
    assert set(realised) == {"points|rebounds", "points|assists", "rebounds|assists"}
    for pair, (target, produced) in realised.items():
        assert produced == pytest.approx(target, rel=0.04), pair
        assert abs(produced) <= abs(target), (
            f"{pair}: the discretised copula realises MORE correlation than it "
            "was asked for, which is the direction a solved-back parameter "
            "would produce"
        )

    components = ("points", "rebounds", "assists")
    pmfs = [distribution.node_component_pmf(stat, node) for stat in components]
    variances = [_moments(pmf)[1] for pmf in pmfs]
    matrix = distribution._correlation_matrix(components)
    predicted = sum(variances)
    for i in range(3):
        for j in range(i + 1, 3):
            pair = PD.coupled_sum_pmf(
                [pmfs[i], pmfs[j]],
                np.array([[1.0, matrix[i, j]], [matrix[i, j], 1.0]]),
            )
            predicted += _moments(pair)[1] - variances[i] - variances[j]
    trivariate = _moments(distribution.node_market_pmf("player_pra", node))[1]
    assert trivariate == pytest.approx(predicted, rel=1e-6), (
        "the trivariate copula branch and the bivariate one disagree about the "
        "pairwise covariances, so one of them is conditioning wrongly"
    )


# --------------------------------------------------------------------------
# Where the constants come from, and what the engine refuses
# --------------------------------------------------------------------------


def test_every_constant_comes_from_the_frozen_file_through_the_loader(
    tmp_path: Path,
) -> None:
    """Three checks, because "it reads the file" is the easiest claim to break.

    1. The module names `PlayerShapes` and opens no path: `player_rates`' rule —
       *nothing in this module opens a file* — extends here, and a `read_csv` or
       a `Path(...)` below this line would reach the settlement table.
    2. No float literal anywhere in the module equals a frozen constant. A
       copied number is a constant with no provenance and no window, which is
       precisely what the loader exists to prevent.
    3. Changing a constant changes the price. That is the one that cannot be
       satisfied by a module which reads the file and then ignores it.
    """
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODULE))

    for banned in ("read_csv", "open(", "Path(", "DEFAULT_SHAPES_PATH"):
        assert banned not in source, (
            f"the engine names {banned!r}; `shapes` arrives as an argument and "
            "this module opens nothing"
        )

    frozen: set[float] = set()

    def _collect(value) -> None:
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            frozen.add(round(float(value), 10))
        elif isinstance(value, dict):
            for item in value.values():
                _collect(item)
        elif isinstance(value, list):
            for item in value:
                _collect(item)

    document = json.loads(SHAPES.read_text(encoding="utf-8"))
    for payload in document["constants"].values():
        _collect(payload.get("value"))
        _collect(payload.get("held_out_value"))
    # A frozen value that happens to be a whole number is not a fingerprint:
    # `minutes_half_life` is 4 and so is `OUTER_CELL_RATIO`, and one is not a
    # copy of the other. Only the fitted decimals identify a constant.
    frozen = {value for value in frozen if value != round(value)}

    literals = {
        round(float(node.value), 10)
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    }
    assert not (literals & frozen), (
        f"these frozen constants are typed as literals in the engine: "
        f"{sorted(literals & frozen)}. A copied constant carries no fit window "
        "and the provenance guard cannot see it."
    )

    baseline = _distribution()

    def _widen(payload: dict) -> None:
        payload["constants"]["conditional_dispersion"]["value"]["rebounds"] = 1.9

    widened = _shapes_with(tmp_path, _widen)
    moved = PD.build(_projection(widened), shapes=widened)
    assert moved.phi_conditional("player_rebounds") == pytest.approx(1.9, abs=1e-12)
    assert _moments(moved.count_pmf("player_rebounds"))[1] > _moments(
        baseline.count_pmf("player_rebounds")
    )[1], "widening the frozen rebounds dispersion did not widen the price"
    assert moved.mean("player_rebounds") == pytest.approx(
        baseline.mean("player_rebounds"), rel=1e-9
    ), "the dispersion moved the mean, which is a parameterisation error"


def test_the_markets_refused_by_name_are_refused_by_name() -> None:
    """Not a missing engine, not a pass, not an avoid, not a no-value call.

    Read verbatim from `player_rates.MARKETS_REFUSED_BY_NAME`, which is the one
    copy of these sentences. A refusal that reaches no output is not a refusal,
    and until this engine existed the only reader of that mapping was an
    exception message.
    """
    distribution = _distribution()
    for market, sentence in PR.MARKETS_REFUSED_BY_NAME.items():
        with pytest.raises(PD.MarketRefused) as raised:
            distribution.count_pmf(market)
        assert str(raised.value) == sentence
        assert "refused" in sentence
    assert "first_basket" in " ".join(PR.MARKETS_REFUSED_BY_NAME)
    assert set(PR.MARKETS_REFUSED_BY_NAME) & set(PR.MARKET_COMPONENTS) == set(), (
        "a market refused by name is also in the priced mapping, so one of the "
        "two is wrong about what this model prices"
    )
    with pytest.raises(PD.PlayerDistributionError, match="not one of the ten"):
        distribution.count_pmf("player_blocks")


def test_a_constant_the_fit_refused_to_invent_refuses_the_market(
    tmp_path: Path,
) -> None:
    """R5 at engine level, in the fit's own sentence.

    `player_rates._unfittable` reads `role_prior` and `rate_shrinkage_k` only,
    so the five constants this engine reads are unchecked anywhere else. The
    shipped `unfittable` block is empty — which is why this path can only ship
    exercised against a synthetic file, and why it is exercised here rather than
    asserted to be unreachable.
    """
    assert _shapes().unfittable() == (), (
        "the frozen file now refuses a constant, so this test is no longer "
        "synthetic: say which market it refuses and count it in the census"
    )

    def _refuse_rebounds(document: dict) -> None:
        document["unfittable"] = {
            "conditional_dispersion.rebounds": {
                "reason": "refused: the rebounds dispersion did not stabilise.",
                "cost": "Every market with a rebounds component is unpriced.",
            }
        }

    partial = _shapes_with(tmp_path, _refuse_rebounds, name="partial.json")
    distribution = PD.build(_projection(partial), shapes=partial)
    for market in (
        "player_rebounds",
        "player_pra",
        "player_points_rebounds",
        "player_rebounds_assists",
    ):
        with pytest.raises(PD.MarketRefused, match="did not stabilise"):
            distribution.count_pmf(market)
    assert distribution.mean("player_points") > 0.0, (
        "one refused component must not refuse the markets that do not use it"
    )

    def _refuse_everything(document: dict) -> None:
        document["unfittable"] = {
            "residual_correlation": {
                "reason": "refused: the residual copula did not stabilise.",
                "cost": "No market can be priced.",
            }
        }

    nothing = _shapes_with(tmp_path, _refuse_everything, name="nothing.json")
    with pytest.raises(PD.MarketRefused, match="every one of the ten markets"):
        PD.build(_projection(), shapes=nothing)


def test_an_unpriceable_projection_is_not_given_a_second_opinion() -> None:
    """R2 through R6 stand; this engine does not re-adjudicate a refusal."""
    fixtures = _rates_fixture()
    thin = PR.player_projections_for(
        day=DAY,
        player_history=pd.DataFrame([fixtures._row("2024-01-02", game_id=101)]),
        prices=fixtures._prices("Sean Bairstow"),
        shapes=_shapes(),
    )
    projection = fixtures._one(thin)
    assert projection.priceable is False
    with pytest.raises(PD.PlayerDistributionError) as raised:
        PD.build(projection, shapes=_shapes())
    assert projection.unpriceable_reason in str(raised.value)


def test_the_push_is_exact_lattice_mass_and_is_never_renormalised_away() -> None:
    """All ten markets push on an integer line, and the reader says so.

    `settlement._settle_player_column` settles these as "the log column against
    the line, equality pushes": 14 rebounds against a line of 14 is a returned
    stake, not a loss. The push is exact mass at the integer, a half-point line
    returns exactly 0.0 and still returns the field, and the two sides are never
    renormalised — forming `win/(1-push)` is a grading decision and belongs to
    the grading commit, not to the reader.
    """
    distribution = _distribution()
    pmf = distribution.count_pmf("player_points")

    over = distribution.market("player_points", 13.0, "over")
    under = distribution.market("player_points", 13.0, "under")
    assert sum(over) == pytest.approx(1.0, abs=1e-12)
    assert over[1] == under[1] == pytest.approx(float(pmf[13]), abs=1e-15)
    assert over[1] > 0.0, "the fixture chose a line with no push mass"
    assert over[0] == under[2] and over[2] == under[0]

    half = distribution.market("player_points", 13.5, "over")
    assert half[1] == 0.0, "a half-point line must push exactly nothing"
    assert sum(half) == pytest.approx(1.0, abs=1e-12)
    assert half[0] == pytest.approx(over[0], abs=1e-15), (
        "moving the line from 13 to 13.5 must move only the push and the under"
    )

    with pytest.raises(PD.PlayerDistributionError, match="Unknown side"):
        distribution.market("player_points", 13.5, "home")


def test_r4s_upper_half_is_enforced_on_counts_here() -> None:
    """The ceiling `player_rates` records as clause 5 of its limitations.

    R4 refuses a mean "above the lattice ceiling" and the frozen file declares
    `minutes_support` and no per-market count ceiling at all, so until this
    module existed the upper half of R4 was enforced on minutes and not on
    counts. It is derived from the assembled distribution and a declared tail
    tolerance rather than fitted, and a line beyond it REFUSES rather than
    returning `(0, 0, 1)` — a confident zero that is an artefact of where the
    lattice was cut is worse than a missing answer.
    """
    distribution = _distribution()
    ceiling = distribution.ceilings["points"]
    assert distribution.count_pmf("player_points").size == ceiling + 1
    assert float(distribution.count_pmf("player_points").sum()) == pytest.approx(
        1.0, abs=1e-12
    )

    with pytest.raises(PD.MarketRefused, match="ceiling"):
        distribution.market("player_points", float(ceiling), "over")
    assert distribution.market("player_points", float(ceiling) - 1.0, "over")[0] >= 0.0

    # And a mean that cannot spend its tail inside the declared cap refuses
    # rather than truncating.
    with pytest.raises(PD.MarketRefused, match="R4"):
        PD.count_lattice_ceiling(
            PD.panjer_parameters(mu=180.0, phi=1.1), severity=(0.0, 1.0)
        )
    assert PD.COUNT_LATTICE_HARD_CAP == 200
    assert PD.COUNT_LATTICE_TAIL_TOLERANCE == 1e-12


def test_the_structural_checks_are_reported_and_only_one_can_stop_the_run() -> None:
    """Design 4's two free checks, with the one declared tolerance there is.

    **A STRUCTURAL CHECK, NOT A RESULT.** These are what the assembled mixture
    reproduces against targets nothing in the engine can influence, measured on
    one synthetic fixture athlete. They are not a census, not an edge and not a
    verdict, and no store row was read to produce any of them.

    Measured on this fixture: the unconditional points VMR comes out 3.3030
    against the frozen 3.0529074370522156, a ratio of **1.0819**, inside design
    4's 15% stop. The conditional points VMR is 2.4751 against 2.3289 — the
    fixture athlete's shrunk mix has `E[V] = 1.980` against the league's 1.857,
    and the compound identity `VMR = E[V^2]/E[V] + (phi-1)*E[V]` is increasing
    in `E[V]`, so a three-heavy athlete gets a wider points marginal at the same
    dispersion. That extrapolation is declared, not discovered.

    The stop rule is the only tolerance declared anywhere: neither the design
    nor `structural_check_targets` gives one for the conditional VMRs, the
    threes marginal or the points/threes correlation, so those are reported and
    stop nothing. Nothing here is tuned to any of them.

    **The per-athlete unconditional ratio is reported under a key that says so
    and cannot stop anything**, which is the repair this file's
    `test_design_4s_stop_rule_is_a_population_quantity` measures. The fixture's
    1.0819 is one athlete's; design 4's stop is pooled over regulars.
    """
    checks = _distribution().structural_checks()
    assert checks["unconditional_points_vmr_target"] == pytest.approx(
        3.0529074370522156, abs=1e-12
    )
    assert checks["unconditional_points_vmr_ratio_this_athlete"] == pytest.approx(
        1.0819, abs=1e-3
    )
    assert "unconditional_points_vmr_ratio" not in checks, (
        "a single athlete's checks must not carry the key the population stop "
        "reads, or the two objects can be divided by accident again"
    )
    with pytest.raises(PD.PlayerDistributionError, match="POPULATION quantity"):
        PD.assert_structural_checks(checks)

    assert checks["measured_event_dispersion"] == pytest.approx(
        1.3799506487253412, abs=1e-12
    )
    assert checks["effective_event_dispersion"] == pytest.approx(
        1.1059306970490195, abs=1e-12
    )
    assert checks["compound_overstatement"] == pytest.approx(
        1.2184945228743802, abs=1e-12
    )

    # The stop rule fires, and it fires by raising rather than by warning. The
    # census keys are what make the mapping a population's; the tolerance
    # applied to the ratio is unchanged.
    population = {
        "unconditional_points_vmr": 3.0529074370522156,
        "unconditional_points_vmr_target": 3.0529074370522156,
        "unconditional_points_vmr_ratio": 1.0,
        "population_athletes": float(PD.STRUCTURAL_CHECK_POPULATION_FLOOR),
        "population_floor": float(PD.STRUCTURAL_CHECK_POPULATION_FLOOR),
        "regular_min_projected_minutes": 15.0,
    }
    PD.assert_structural_checks(population)
    with pytest.raises(PD.StructuralCheckFailed, match="the discrepancy is the finding"):
        PD.assert_structural_checks(
            {**population, "unconditional_points_vmr_ratio": 1.17}
        )
    PD.assert_structural_checks({**population, "unconditional_points_vmr_ratio": 1.149})
    with pytest.raises(PD.StructuralCheckFailed):
        PD.assert_structural_checks(
            {**population, "unconditional_points_vmr_ratio": float("nan")}
        )

    # The alternative dispersion is the one that trips the IDENTITY, which is
    # the argument for `POINTS_EVENT_DISPERSION_KEY`. Arithmetic on frozen
    # constants: the minutes lift is additive, so the unconditional VMR is the
    # conditional one plus 3.0529074370522156 - 2.328891545818532. What the
    # engine PRODUCES under each key is a different pair of numbers and
    # `test_the_dispersion_choice_is_not_decided_by_the_stop_rule` holds those.
    shapes = _shapes()
    targets = shapes.value("structural_check_targets")
    lift = (
        targets["unconditional_points_vmr_regulars"]
        - targets["points_vmr_given_minutes"]
    )
    alternative = targets["compound_implied_points_vmr_given_minutes"] + lift
    assert alternative / targets["unconditional_points_vmr_regulars"] == pytest.approx(
        1.1667, abs=1e-3
    )
    with pytest.raises(PD.StructuralCheckFailed):
        PD.assert_structural_checks(
            {
                **population,
                "unconditional_points_vmr": alternative,
                "unconditional_points_vmr_ratio": alternative
                / targets["unconditional_points_vmr_regulars"],
            }
        )
    assert PD.POINTS_EVENT_DISPERSION_KEY == "effective_event_dispersion"


# --------------------------------------------------------------------------
# Design 4's stop rule: what it is computed OVER, and where it runs
# --------------------------------------------------------------------------


def _role_prior_athlete(shapes, bucket: int, *, minutes: float | None = None):
    """One athlete built from the frozen file's OWN role prior for a bucket.

    Not a fixture and not a store row: `role_prior[stat][bucket]` for the rates,
    `minutes_lattice` tilted to the bucket's own recorded mean for the lattice,
    and the league `value_pmf` for the severity mix. It is the file describing
    the average athlete of a minutes bucket, so a check computed over the nine
    of them is a check over the file's own population rather than over whoever
    the test fixture happens to be.
    """
    priors = shapes.value("role_prior")
    table = shapes.value("minutes_pmf")
    support = np.arange(
        int(table["support_low"]), int(table["support_high"]) + 1, dtype=float
    )
    mean = float(np.asarray(table["pmf"][bucket], dtype=float) @ support)
    projected = mean if minutes is None else float(minutes)
    projection = PR.PlayerProjection(
        event_id="E",
        game_id="G",
        athlete_id=f"role-prior-{bucket}",
        display_name=f"bucket {bucket}",
        provider_name=f"bucket {bucket}",
        team_id="T",
        opponent_id="O",
        player_tier="high",
        projected_minutes=projected,
        minutes_bucket=bucket,
        minutes_pmf=PR.minutes_lattice(
            projected_minutes=projected, bucket=bucket, shapes=shapes
        ),
        rates={stat: float(priors[stat][bucket]) for stat in priors},
        prior_weight={stat: 1.0 for stat in priors},
        prior_minutes=400.0,
        prior_games=20,
        value_pmf=tuple(float(v) for v in shapes.value("value_pmf")),
        value_prior_events=100.0,
        value_mix_weight=1.0,
        dnp_probability=0.01,
        resolution_route="exact",
        priceable=True,
        unpriceable_reason=None,
        priced_through="2024-01-14",
        refused_stats={},
    )
    return PD.build(projection, shapes=shapes)


def test_design_4s_stop_rule_is_a_population_quantity() -> None:
    """The check is pooled over regulars, and one athlete is not a population.

    **A STRUCTURAL CHECK, NOT A RESULT.** Every number here is produced from the
    frozen file's own nine role priors and nine minutes shapes. No store row is
    read, nothing is graded, and none of it is an edge.

    The defect. `structural_check_targets.unconditional_points_vmr_regulars` is
    `pooled_vmr` over 242,634 rows whose own `regular_min_projected_minutes` is
    15.0 — a POPULATION number. Dividing ONE athlete's mixture VMR by it divides
    two different objects, and the quotient then moves with the athlete's
    minutes rather than with the model. Measured below: the nine role-prior
    athletes read 1.1123, 1.1203, 1.0893, 1.0497, 1.0043, 0.9626, 0.9203, 0.8790
    and 0.8482 from the 6.73-minute bucket to the 36.22-minute one, a spread of
    0.272, while the CONDITIONAL half reads 2.328891545818532 at all nine to
    floating point — exactly the frozen `points_vmr_given_minutes`. So the whole
    spread is the minutes channel and none of it is the model missing anything.

    The consequence, and it is the reason this is a bug rather than a nuance:
    the 36.22-minute athlete is 15.2% low, so the per-athlete route stops the
    run on the average high-minutes starter — squarely inside the population the
    target is measured over, not a tail case.

    Pooled the way the target is pooled — a ratio of two sums, not a mean of
    ratios — the regulars among those nine reproduce 2.8113 against
    3.0529074370522156, a ratio of 0.9209, inside design 4's 15% stop.
    """
    shapes = _shapes()
    athletes = [_role_prior_athlete(shapes, bucket) for bucket in range(9)]

    per_athlete = [
        a.structural_checks()["unconditional_points_vmr_ratio_this_athlete"]
        for a in athletes
    ]
    assert per_athlete == pytest.approx(
        [1.1123, 1.1203, 1.0893, 1.0497, 1.0043, 0.9626, 0.9203, 0.8790, 0.8482],
        abs=5e-4,
    )
    conditional = [
        a.structural_checks()["points_vmr_given_minutes"] for a in athletes
    ]
    assert conditional == pytest.approx([2.328891545818532] * 9, abs=1e-8), (
        "the conditional half is exact by construction at the league value mix, "
        "so every bit of the spread above is the minutes channel"
    )
    # 1e-8 rather than 1e-12, and the residual is a lattice truncation rather
    # than a model difference. Every one of the nine sits BELOW the constant,
    # which is the signature of dropped tail mass and not of noise: the
    # deviations run -1.25e-09, -3.74e-10, -3.43e-10, -2.37e-10, -3.20e-10,
    # -2.27e-10, -2.10e-10, -1.69e-10, -2.17e-10, worst at the 6.73-minute
    # bucket where `count_lattice_ceiling` truncates the smallest count. All
    # nine are one-sided and all nine are inside 1.3e-09.
    assert max(conditional) < 2.328891545818532, (
        "all nine sit below the frozen constant. A two-sided spread would be a "
        "different fact and would not be truncation"
    )
    assert min(conditional) > 2.328891545818532 - 1.3e-9
    assert max(per_athlete) - min(per_athlete) == pytest.approx(0.2721, abs=1e-3)
    assert abs(per_athlete[8] - 1.0) > PD.UNCONDITIONAL_POINTS_VMR_STOP, (
        "the average 36.22-minute starter is outside the stop on the per-athlete "
        "route. He is a regular by the target's own definition, so a rule that "
        "stopped on him would stop most of the book"
    )

    # The population route, on the same nine objects.
    checks = PD.population_structural_checks(athletes, shapes=shapes)
    assert checks["regular_min_projected_minutes"] == 15.0
    assert checks["population_athletes_offered"] == 9.0
    assert checks["population_athletes"] == 6.0
    assert checks["population_below_regular_floor"] == 3.0, (
        "the three sub-15-minute buckets were not in the population the target "
        "was measured over, so they are counted apart rather than pooled"
    )
    assert checks["unconditional_points_vmr"] == pytest.approx(2.8113, abs=1e-3)
    assert checks["unconditional_points_vmr_ratio"] == pytest.approx(0.9209, abs=1e-3)
    assert abs(checks["unconditional_points_vmr_ratio"] - 1.0) < (
        PD.UNCONDITIONAL_POINTS_VMR_STOP
    )

    # A ratio of two sums, NOT the mean of the ratios. The two differ, and the
    # first is the one `pooled_vmr` builds the target with.
    regulars = per_athlete[3:]
    assert float(np.mean(regulars)) == pytest.approx(0.9440, abs=1e-3)
    assert checks["unconditional_points_vmr_ratio"] != pytest.approx(
        float(np.mean(regulars)), abs=1e-4
    )

    # And the two mappings cannot be confused: neither carries the other's key.
    assert "unconditional_points_vmr_ratio_this_athlete" not in checks
    with pytest.raises(PD.PlayerDistributionError, match="POPULATION quantity"):
        PD.assert_structural_checks(athletes[8].structural_checks())


def test_the_population_floor_is_a_gap_that_is_held_open() -> None:
    """Below the floor the stop cannot run, and that is stated rather than passed.

    **A LIMITATION, ASSERTED.** This test goes red the day a run-level
    population reaches the floor by itself, which is the only honest way to
    carry the gap: the check is wired and it evaluates, but on a population
    smaller than :data:`PD.STRUCTURAL_CHECK_POPULATION_FLOOR` it may not stop
    anything, because pooling over that few IS the per-athlete comparison the
    floor exists against.

    What decided eight, measured on frozen constants: regular athletes drawn iid
    from the frozen file's own `minutes_pmf` evidence `rows_per_bucket`, 40,000
    populations at each size, tripped the 15% stop on COMPOSITION ALONE 2.72% of
    the time at one athlete, 0.08% at two, and never at three or more; the worst
    of 40,000 at eight was 0.8745, which is 12.6% off and inside. Eight is
    therefore well past where the check stopped being a coin toss about which
    athletes the book happened to quote.

    The gap is real and it is not closed here: a single-athlete card evaluates
    the check, reports the ratio and stops nothing.
    """
    shapes = _shapes()
    assert PD.STRUCTURAL_CHECK_POPULATION_FLOOR == 8

    # The 36.22-minute starter is outside the stop on his own, and one athlete
    # does not stop the run.
    alone = PD.population_structural_checks(
        [_role_prior_athlete(shapes, 8)], shapes=shapes
    )
    assert alone["population_athletes"] == 1.0
    assert alone["unconditional_points_vmr_ratio"] == pytest.approx(0.8482, abs=1e-3)
    assert abs(alone["unconditional_points_vmr_ratio"] - 1.0) > (
        PD.UNCONDITIONAL_POINTS_VMR_STOP
    )
    PD.assert_structural_checks(alone)  # does not raise: below the floor

    # At the floor the same discrepancy does stop the run. This is the pair that
    # makes the floor a floor rather than an exemption: the tolerance never
    # moved, only the size of the population it is allowed to speak about.
    crowd = PD.population_structural_checks(
        [_role_prior_athlete(shapes, 8) for _ in range(8)], shapes=shapes
    )
    assert crowd["population_athletes"] == 8.0
    assert crowd["unconditional_points_vmr_ratio"] == pytest.approx(
        alone["unconditional_points_vmr_ratio"], rel=1e-12
    )
    with pytest.raises(PD.StructuralCheckFailed, match="the discrepancy is the finding"):
        PD.assert_structural_checks(crowd)

    # No regulars at all is not a pass either: it is NaN and no population.
    empty = PD.population_structural_checks(
        [_role_prior_athlete(shapes, 0)], shapes=shapes
    )
    assert empty["population_athletes"] == 0.0
    assert empty["population_below_regular_floor"] == 1.0
    assert math.isnan(empty["unconditional_points_vmr_ratio"])
    PD.assert_structural_checks(empty)


def test_the_regulars_floor_comes_from_the_frozen_file_not_from_this_module(
    tmp_path: Path,
) -> None:
    """Who counts as a regular is a fact about the target, read off the target.

    `regular_min_projected_minutes` = 15.0 defines the population
    `unconditional_points_vmr_regulars` was pooled over, and it lives in that
    constant's own evidence block. A floor hard-coded in the engine would go on
    reading 15.0 after a refit moved it, and the check would then be pooling a
    population the target was never measured on. Asserted by moving it in a copy
    of the file and watching the census follow.
    """
    shapes = _shapes()
    assert shapes.evidence("structural_check_targets")["fit"][
        "regular_min_projected_minutes"
    ] == 15.0

    athletes = [_role_prior_athlete(shapes, bucket) for bucket in range(9)]
    assert PD.population_structural_checks(athletes, shapes=shapes)[
        "population_athletes"
    ] == 6.0

    def _move_the_floor(document):
        document["constants"]["structural_check_targets"]["evidence"]["fit"][
            "regular_min_projected_minutes"
        ] = 25.0

    moved = _shapes_with(tmp_path, _move_the_floor, name="moved-floor.json")
    followed = PD.population_structural_checks(athletes, shapes=moved)
    assert followed["regular_min_projected_minutes"] == 25.0
    assert followed["population_athletes"] == 4.0, (
        "at a 25-minute floor the 18.32 and 22.44 buckets leave the population, "
        "which is the engine following the file rather than its own literal"
    )

    def _delete_the_floor(document):
        del document["constants"]["structural_check_targets"]["evidence"]["fit"][
            "regular_min_projected_minutes"
        ]

    without = _shapes_with(tmp_path, _delete_the_floor, name="no-floor.json")
    with pytest.raises(PD.PlayerDistributionError, match="regular_min_projected_minutes"):
        PD.population_structural_checks(athletes, shapes=without)


def test_the_dispersion_choice_is_not_decided_by_the_stop_rule() -> None:
    """What each candidate PRODUCES, against what the identity arithmetic says.

    **A STRUCTURAL CHECK, NOT A RESULT.** `POINTS_EVENT_DISPERSION_KEY`'s
    docstring used to argue for `effective_event_dispersion` by quoting "a ratio
    of 1.0000" against "1.1667 — over design 4's own 15% stop". Both numbers are
    frozen-constant arithmetic — the target's own conditional VMR plus the
    target's own POPULATION minutes lift of 3.0529074370522156 −
    2.328891545818532 — and neither is a number the engine emits, because the
    produced lift is each athlete's own `r·Var(M)/E(M)`.

    Measured here over the file's nine role-prior athletes restricted to
    regulars: `effective_event_dispersion` produces 0.9209 and
    `measured_event_dispersion` produces 1.0875. The choice moves the produced
    ratio by 0.167 — the whole width of the stop budget — but **both land
    inside the stop**, so the stop rule does not decide it and the docstring may
    not say it does. The identity does, and the file's stated mechanism is that
    free throws arrive in pairs.
    """
    shapes = _shapes()
    produced = {}
    original = PD.POINTS_EVENT_DISPERSION_KEY
    try:
        for key in ("effective_event_dispersion", "measured_event_dispersion"):
            PD.POINTS_EVENT_DISPERSION_KEY = key
            athletes = [_role_prior_athlete(shapes, bucket) for bucket in range(9)]
            produced[key] = PD.population_structural_checks(athletes, shapes=shapes)[
                "unconditional_points_vmr_ratio"
            ]
    finally:
        PD.POINTS_EVENT_DISPERSION_KEY = original
    assert PD.POINTS_EVENT_DISPERSION_KEY == "effective_event_dispersion"

    assert produced["effective_event_dispersion"] == pytest.approx(0.9209, abs=1e-3)
    assert produced["measured_event_dispersion"] == pytest.approx(1.0875, abs=1e-3)
    assert produced["measured_event_dispersion"] - produced[
        "effective_event_dispersion"
    ] == pytest.approx(0.1666, abs=1e-3)
    for key, ratio in produced.items():
        assert abs(ratio - 1.0) < PD.UNCONDITIONAL_POINTS_VMR_STOP, (
            f"{key} produces {ratio:.4f}, and the docstring may not claim the "
            "stop rule picks between the two while both are inside it"
        )


# --------------------------------------------------------------------------
# The ten readers, and the two routes to a mean
# --------------------------------------------------------------------------


def test_the_ten_readers_are_ten_questions_asked_of_one_object() -> None:
    """Every priced market reads a rung off the SAME cached object.

    Design 6 registers ten markets and design 5 says the four combinations come
    "from components over the shared minutes draw, never from their own
    history". Both halves are checked here rather than asserted:

    * the ten are exactly `MARKET_COMPONENTS`, and the two refused by name are
      disjoint from them;
    * every reader returns `(win, push, loss)` summing to one with each leg in
      [0, 1], on a half-point rung and on an integer rung;
    * `over` and `under` at one line are the same three numbers with the outer
      two swapped, so a caller cannot get a different bet by asking the other
      way round;
    * an integer rung's push is EXACTLY the lattice mass at that count -- never
      a density at an integer and never an interpolation between rungs;
    * no combination market has a rate, a role prior, a credibility constant or
      a dispersion anywhere in the frozen file. Design 8: derived from the
      joint, never fitted. A fitted pra constant appearing later is a defect,
      not an improvement.
    """
    distribution = _distribution()
    assert set(PR.MARKET_COMPONENTS) == set(PR.PRICED_MARKETS)
    assert len(PR.PRICED_MARKETS) == 10
    assert set(PR.PRICED_MARKETS) & set(PR.MARKETS_REFUSED_BY_NAME) == set()

    for market in PR.PRICED_MARKETS:
        pmf = distribution.count_pmf(market)
        rung = math.floor(distribution.mean(market)) + 0.5
        over = distribution.market(market, rung, "over")
        under = distribution.market(market, rung, "under")
        assert sum(over) == pytest.approx(1.0, abs=1e-12), market
        assert all(0.0 <= leg <= 1.0 for leg in over), market
        assert over == (under[2], under[1], under[0]), (
            f"{market}: the two sides of one line are not one bet read twice"
        )
        assert over[1] == 0.0, f"{market}: a half-point rung cannot push"

        integer = float(math.floor(rung))
        win, push, loss = distribution.market(market, integer, "over")
        assert push == float(pmf[int(integer)]), market
        assert win + push + loss == pytest.approx(1.0, abs=1e-12), market
        assert push > 0.0, f"{market}: an integer rung must carry lattice mass"

    document = json.loads(SHAPES.read_text(encoding="utf-8"))
    combinations = {"pra", "points_rebounds", "points_assists", "rebounds_assists"}
    for name in ("role_prior", "rate_shrinkage_k", "conditional_dispersion"):
        assert not set(document["constants"][name]["value"]) & combinations, (
            f"{name} now carries a combination-market constant. Design 8 says "
            "combination dispersions are derived from the joint and never "
            "fitted, so this is a defect rather than an improvement."
        )


def test_the_two_mean_routes_agree_where_they_are_one_route_and_are_measured_where_they_are_two() -> None:
    """The points/threes ruling, and the size of what it costs, measured.

    `player_rates` carries TWO routes to a mean for two of the seven stats, and
    the markets contract settles which one is the price:

        the compound is the price and `rates["points"]` is the check

    -- `player_rates.py`'s own comment, quoting the fitter's. `player_threes`
    goes the same way, because design 4 says it "falls out as the three-point
    component of the same object rather than as a separate count", and because
    the standalone route would make design 4's own `corr(points, threes)` check
    a comparison of the frozen 0.6021705535430947 with itself.

    **WHERE THE TWO ROUTES ARE ONE ROUTE THEY AGREE, AND THE TOLERANCE IS
    STATED: 1e-9 RELATIVE.** For `rebounds`, `assists`, `steals`, `turnovers`
    and `player_rebounds_assists` the engine's price mean and
    `player_rates.mean_for_market` are the same arithmetic -- `rate * E[M]`,
    with the minutes lattice tilted to `projected_minutes` so `E[M]` reproduces
    it to 7.1e-15. Measured worst case on this fixture: 6.6e-12 relative, three
    orders inside the stated tolerance, and the residual is the count lattice's
    own 1e-12 tail truncation.

    **WHERE THEY ARE TWO ROUTES THEY DO NOT AGREE, AND THE DISAGREEMENT IS
    REPORTED RATHER THAN TUNED.** Measured on this fixture athlete:

        player_points            +1.6386%   (13.184738 against 12.972176)
        player_threes            +0.6817%   ( 1.816646 against  1.804346)
        player_pra               +0.9929%   (the points leg, unchanged)
        player_points_rebounds   +1.1395%
        player_points_assists    +1.3517%

    There is no tolerance at which those agree -- a 2% ROI edge at -110 is about
    1.0pp of probability -- so this test asserts the DECOMPOSITION instead,
    which is exact and names both halves:

        gap = mu_events * (E[V_shrunk] - E[V_observed]) * minutes     (the mix)
            + (mu_events * E[V_observed] - rate_points) * minutes     (the weights)

    On this athlete, in points: +0.212563 = -0.134648 + 0.347211. Both terms are
    structural and both are frozen. The first is the value mix being shrunk
    toward the league shape at `value_mix_shrinkage_events` = 9.220113 EVENTS
    while the points rate is shrunk toward the role prior at
    `rate_shrinkage_k["points"]` = 102.833900 prior MINUTES -- two targets, two
    speeds, two units. The second is that the two rates carry different
    credibility weights on identical evidence: 0.685363 for `points` against
    0.721897 for `points_events` and 0.765818 for `threes`.

    The identity underneath is the box score's own: a player's points are
    `1*FT + 2*FG2 + 3*FG3` and his scoring events are `FT + FG2 + FG3`, so
    `observed_points == observed_events * E[V_observed]` exactly. The two routes
    are therefore ONE route with the shrinkage off -- this fixture's observed
    E[V] is exactly 2.000000 -- and every part of the gap is shrinkage.

    **At the role prior, where an athlete has no evidence at all, the two routes
    are much further apart on threes than on points.** Measurement on frozen
    constants, no store row read: the ratio of `role_prior["threes"]` to
    `role_prior["points_events"] * p3_league`, by minutes bucket, is

        0-8 0.892 | 8-12 0.927 | 12-16 0.921 | 16-20 0.914 | 20-24 0.936
        24-28 0.959 | 28-32 1.038 | 32-36 1.092 | 36+ 1.091

    -- -10.8% to +9.2%, **changing sign between the 24-28 and 28-32 buckets**.
    The same ratio for points runs 0.994 to 1.007, flat. So the standalone
    threes rate takes a different position on shot diet by minutes bucket, in
    both directions, and a model that used it for threes and the compound for
    points would be giving two answers to one question inside one object.

    Nothing is tuned to close any of this. `mean_for_market` is untouched and
    still returns the rate route; the engine still returns the compound one;
    both are printed.
    """
    distribution = _distribution()
    projection = distribution.projection
    minutes = float(projection.projected_minutes)
    shapes = _shapes()

    # -- one route, and the tolerance is stated -----------------------------
    for market in (
        "player_rebounds",
        "player_assists",
        "player_steals",
        "player_turnovers",
        "player_rebounds_assists",
    ):
        assert distribution.mean(market) == pytest.approx(
            PR.mean_for_market(projection, market), rel=1e-9
        ), market
    assert projection.mean_minutes() == pytest.approx(minutes, abs=1e-12)

    # -- two routes, and the price is the compound one ----------------------
    severity = np.asarray(projection.value_pmf, dtype=float)
    expected_value = float(severity @ np.array([1.0, 2.0, 3.0]))
    events = float(projection.rates["points_events"]) * minutes
    assert distribution.mean("player_points") == pytest.approx(
        events * expected_value, abs=1e-9
    ), "the priced points mean is not the compound one"
    assert distribution.mean("player_threes") == pytest.approx(
        events * float(severity[2]), abs=1e-9
    ), "the priced threes mean is not the thinned one"

    measured = {
        market: distribution.mean(market) / PR.mean_for_market(projection, market) - 1.0
        for market in (
            "player_points",
            "player_threes",
            "player_pra",
            "player_points_rebounds",
            "player_points_assists",
        )
    }
    assert measured["player_points"] == pytest.approx(0.016386, abs=1e-5)
    assert measured["player_threes"] == pytest.approx(0.006817, abs=1e-5)
    assert measured["player_pra"] == pytest.approx(0.009929, abs=1e-5)
    assert measured["player_points_rebounds"] == pytest.approx(0.011395, abs=1e-5)
    assert measured["player_points_assists"] == pytest.approx(0.013517, abs=1e-5)
    assert all(gap > 0.0 for gap in measured.values()), (
        "the compound route no longer runs above the rate route on this "
        "fixture, and the direction is part of what is reported"
    )

    # -- the decomposition, which makes the gap a fact rather than a smell --
    role = shapes.value("role_prior")
    bucket = int(projection.minutes_bucket)
    observed = {}
    for stat in ("points", "points_events", "threes"):
        weight = float(projection.prior_weight[stat])
        observed[stat] = (
            float(projection.rates[stat]) - (1.0 - weight) * float(role[stat][bucket])
        ) / weight
    assert observed["points"] / observed["points_events"] == pytest.approx(2.0, abs=1e-9), (
        "the box-score identity points == events * E[V] does not hold on the "
        "observed bank, so the gap is not purely shrinkage and this "
        "decomposition is not the whole of it"
    )

    for stat, share in (("points", expected_value), ("threes", float(severity[2]))):
        observed_share = observed[stat] / observed["points_events"]
        rate_events = float(projection.rates["points_events"])
        gap = (rate_events * share - float(projection.rates[stat])) * minutes
        mix = rate_events * (share - observed_share) * minutes
        weights = (rate_events * observed_share - float(projection.rates[stat])) * minutes
        assert mix + weights == pytest.approx(gap, abs=1e-12), stat
        assert distribution.mean(f"player_{stat}") - PR.mean_for_market(
            projection, f"player_{stat}"
        ) == pytest.approx(gap, abs=1e-9), stat
        assert mix < 0.0 < weights, stat
    assert float(projection.prior_weight["points"]) == pytest.approx(0.685363, abs=1e-6)
    assert float(projection.prior_weight["points_events"]) == pytest.approx(
        0.721897, abs=1e-6
    )
    assert float(projection.prior_weight["threes"]) == pytest.approx(0.765818, abs=1e-6)
    assert shapes.value("rate_shrinkage_k")["points"] == pytest.approx(
        102.83390031937007, abs=1e-9
    )
    assert shapes.value("value_mix_shrinkage_events") == pytest.approx(
        9.220113199777744, abs=1e-9
    )

    # -- and at the prior, where the athlete has no evidence at all ---------
    league = shapes.value("value_pmf")
    league_value = sum((index + 1) * share for index, share in enumerate(league))
    points_ratio = [
        role["points"][index] / (role["points_events"][index] * league_value)
        for index in range(len(role["points"]))
    ]
    threes_ratio = [
        role["threes"][index] / (role["points_events"][index] * league[2])
        for index in range(len(role["threes"]))
    ]
    assert len(threes_ratio) == 9
    assert min(points_ratio) == pytest.approx(0.9942, abs=1e-3)
    assert max(points_ratio) == pytest.approx(1.0072, abs=1e-3)
    assert min(threes_ratio) == pytest.approx(0.8922, abs=1e-3)
    assert max(threes_ratio) == pytest.approx(1.0917, abs=1e-3)
    assert threes_ratio[5] < 1.0 < threes_ratio[6], (
        "the standalone-versus-thinned threes disagreement no longer changes "
        "sign between the 24-28 and 28-32 buckets, which is the measurement "
        "saying it is a role effect and not a level offset"
    )

    # Nothing was tuned to close any of it: the check route is still the rate
    # route, unchanged, for every one of the ten.
    for market, components in PR.MARKET_COMPONENTS.items():
        assert PR.mean_for_market(projection, market) == pytest.approx(
            sum(float(projection.rates[stat]) * minutes for stat in components),
            abs=1e-12,
        ), market


# --------------------------------------------------------------------------
# The wiring: a priceable projection carries a probability
# --------------------------------------------------------------------------


def _wager(market: str, *, line: float, event_id: str = "e1", player: str = "Sean Bairstow"):
    """One prop, keyed the way `reports/card_pricing.py` keys it."""
    from cbb_betting_lab.reports import card_pricing

    return card_pricing.Wager(
        key=(event_id, market, "over", line, player),
        event_id=event_id,
        slate_date=DAY,
        commence_time=f"{DAY}T23:00:00Z",
        home_team="Home State",
        away_team="Away Tech",
        market=market,
        segment="game",
        player=player,
        selection="over",
        line=line,
        tier="high_major",
        quotes=(card_pricing.Quote(book="dk", american_odds=-110.0),),
    )


def _slate_model(shapes=None, *, carry_shapes: bool = True):
    """A real `SlateModel`: the real estimator's projections, the real constants.

    Not a hand-assembled double. What the card is handed here is what
    `slate.slate_model` hands it, so the wiring under test is the shipped one.
    """
    from cbb_betting_lab.models import slate as SLATE

    resolved = shapes or _shapes()
    fixtures = _rates_fixture()
    result = PR.player_projections_for(
        day=DAY,
        player_history=fixtures._history(),
        prices=fixtures._prices("Sean Bairstow"),
        shapes=resolved,
    )
    model = SLATE.SlateModel(
        day=DAY,
        matchups={},
        players=dict(result.projections),
        resolved=dict(result.resolved),
        name_refusals=dict(result.name_refusals),
        player_priced_through=str(result.priced_through),
        shapes=resolved if carry_shapes else None,
    )
    return model, resolved


def test_a_priceable_projection_now_carries_a_probability_through_the_card() -> None:
    """The wiring, end to end, and what it does and does not change.

    Until this commit `reports/gameday_card.opinions_for` gave the whole player
    family a census bucket and no probability: a priceable projection's last
    word was `slate.NO_DISTRIBUTION_ENGINE`, which said the engine was not
    written. It is written, and it is now built from the projection and the
    slate's OWN provenance-checked constants -- one `PlayerDistribution` per
    (event, athlete), cached on the call, so ten markets on one athlete are ten
    questions asked of one object.

    Asserted here, on a fourteen-wager fixture card:

    * sixteen wagers in, eleven priced and five declined into five distinct
      buckets;
    * the ten priced markets carry a probability, and it is BIT-IDENTICAL to
      the number the engine gives for the same rung when built separately. The
      engine holds no RNG and reads no clock, so equality is exact and a drift
      would mean the card is pricing off something the engine is not;
    * the push is stored beside it and never folded in. `p = win` understates
      the edge by exactly the push mass, which is the conservative direction;
      `win/(1-push)` would overstate it on precisely the whole-number lines;
    * `player_first_basket` and `player_double_double` still print their own
      refusals, word for word, and are never priced;
    * a player market outside the ten (`player_blocks`) reads its own sentence
      rather than a refusal or a missing engine;
    * an event the model was never asked about still reads `no opinion`;
    * a line above the count lattice ceiling REFUSES rather than returning
      `(0, 0, 1)`, so R4's upper half is enforced where the card can see it;
    * a points ladder read through the card is strictly decreasing, because the
      rungs come off one object and there is no second ladder model.

    **What this does not do.** Nothing is graded and no result is stated. Every
    prop is still stopped before it can become a selection:
    `gates.can_produce_a_selection` is CONFIRMED-only, no availability report
    exists for Division I men's basketball, and no market is allowlisted.
    """
    from cbb_betting_lab.models import slate as SLATE
    from cbb_betting_lab.reports import gameday_card as GC

    model, shapes = _slate_model()
    projection = model.players["e1"][next(iter(model.players["e1"]))]
    reference = PD.build(projection, shapes=shapes)

    rungs = {
        market: math.floor(reference.mean(market)) + 0.5 for market in PR.PRICED_MARKETS
    }
    wagers = [_wager(market, line=line) for market, line in rungs.items()]
    wagers += [
        _wager("player_first_basket", line=0.5),
        _wager("player_double_double", line=0.5),
        _wager("player_blocks", line=1.5),
        _wager("player_points", line=14.5, event_id="e9"),
        _wager("player_points", line=400.5),
        # An INTEGER rung. The design measures 6 such quotes on 3 lines in the
        # store, all `player_points`, all williamhill_us: live and rare, which
        # is the profile of a branch that ships broken. It is the only rung on
        # this card where the push convention is visible at all.
        _wager("player_points", line=13.0),
    ]
    probabilities, census = GC.opinions_for(wagers, model, day=DAY)

    assert census.wagers == 16
    assert census.priced == 11, census.declined
    for market, line in rungs.items():
        key = ("e1", market, "over", line, "Sean Bairstow")
        win, push, _loss = reference.market(market, line, "over")
        assert probabilities[key] == win, (
            f"{market}: the card's number is not the engine's. There is one "
            "model for this athlete and the card must be reading it"
        )
        assert census.push_mass[key] == push
        assert 0.0 < probabilities[key] < 1.0, market

    declined = census.declined
    for market, sentence in PR.MARKETS_REFUSED_BY_NAME.items():
        assert sentence in declined, market
        assert not any(
            ("e1", market, "over", 0.5, "Sean Bairstow") == key for key in probabilities
        ), f"{market} was priced, and it is refused by name"
    assert any("registered against ten markets" in reason for reason in declined), (
        "`player_blocks` is not one of the ten and is not refused by name "
        f"either; it must say so. It read: {sorted(declined)}"
    )
    # The size of that bucket, measured rather than described: 19 player
    # markets on the board, 10 priced, 2 refused by name, 7 the model was
    # never asked about. `player_first_team_basket` is one of the seven and is
    # NOT `player_first_basket`, so the design's refusal does not reach it.
    from cbb_betting_lab.markets import PLAYER_MARKETS

    outside = [
        market.key
        for market in PLAYER_MARKETS
        if market.key not in PR.MARKET_COMPONENTS
        and market.key not in PR.MARKETS_REFUSED_BY_NAME
    ]
    assert len(PLAYER_MARKETS) == 19 and len(outside) == 7, outside
    assert "player_first_team_basket" in outside
    assert any("never asked about this event's athletes" in r for r in declined)
    # R4's upper half, through the card. A line past the count lattice must
    # REFUSE and print why; returning (0, 0, 1) would report a confident zero
    # that is an artefact of where the lattice was truncated, and it would be
    # the most attractive-looking number on the card.
    assert any("above the count lattice ceiling" in r for r in declined), sorted(declined)
    assert ("e1", "player_points", "over", 400.5, "Sean Bairstow") not in probabilities
    assert SLATE.NO_DISTRIBUTION_ENGINE not in declined
    assert SLATE.NO_ENGINE_CONSTANTS not in declined
    assert not any("no probability exists for this line yet" in r for r in declined), (
        "the sentence that said the engine was not written has survived the "
        "commit that wrote it"
    )

    # The push, on the one rung that has one. `p = win` UNCONDITIONAL: the edge
    # definition `p*(1+payout) - 1` has no push term, so `win/(1-push)` would
    # overstate the edge by the push mass in the flattering direction, on
    # precisely the whole-number lines where the market concentrates.
    integer = ("e1", "player_points", "over", 13.0, "Sean Bairstow")
    win, push, loss = reference.market("player_points", 13.0, "over")
    assert push > 0.01, "the integer rung carries no push and proves nothing"
    assert probabilities[integer] == win
    assert census.push_mass[integer] == push
    assert probabilities[integer] != pytest.approx(win / (1.0 - push), abs=1e-9)
    assert win + push + loss == pytest.approx(1.0, abs=1e-12)

    # D2 through the card: one object, one ladder, strictly decreasing.
    ladder = [_wager("player_points", line=line) for line in (10.5, 12.5, 14.5, 16.5, 18.5)]
    priced, rung_census = GC.opinions_for(ladder, model, day=DAY)
    assert rung_census.priced == 5
    steps = [priced[wager.key] for wager in ladder]
    assert steps == sorted(steps, reverse=True) and len(set(steps)) == 5, steps


def test_two_spellings_of_one_athlete_build_one_object(monkeypatch) -> None:
    """Design 2's cache rule, asserted by counting builds rather than by comment.

    "One cached `PlayerDistribution` per (event_id, athlete_id)" is a claim
    about the KEY, and the key is the thing the store makes non-obvious: the
    census gate over `cbb_historical_prices__card.csv` found 64 folded names
    each carrying exactly two raw spellings — `'A.J. HOGGARD'` and
    `'A.J. Hoggard'`, `'Tucker DeVries'` and `'Tucker Devries'` — 128 raw
    spellings collapsing 4,396 wager keys, every one of them a book's
    title-caser rather than one book quoting twice. Both spellings resolve to
    one athlete id here, exactly as they would there.

    Keyed on the spelling, that athlete would get TWO distribution objects on
    one game. They would agree today, because the engine is deterministic and
    holds no RNG — which is precisely why nothing else in this file could catch
    the mistake, and why this counts builds instead of comparing numbers.
    """
    from cbb_betting_lab.reports import gameday_card as GC

    model, shapes = _slate_model()
    athlete = next(iter(model.players["e1"]))
    resolved = dict(model.resolved)
    resolved[("e1", "sean bairstow")] = athlete
    resolved[("e1", "SEAN BAIRSTOW")] = athlete
    model = replace(model, resolved=resolved)

    builds: list[object] = []
    real = PD.build

    def counting(projection, *, shapes):
        builds.append(projection.athlete_id)
        return real(projection, shapes=shapes)

    monkeypatch.setattr(PD, "build", counting)
    _, census = GC.opinions_for(
        [
            _wager("player_points", line=14.5, player="Sean Bairstow"),
            _wager("player_rebounds", line=5.5, player="sean bairstow"),
            _wager("player_assists", line=2.5, player="SEAN BAIRSTOW"),
        ],
        model,
        day=DAY,
    )
    assert census.priced == 3, census.declined
    assert builds == [athlete], (
        "three rungs on one athlete under three spellings built "
        f"{len(builds)} distribution(s). One player, one object."
    )


def test_the_card_says_which_absence_it_is_when_it_cannot_reach_the_engine(
    monkeypatch,
) -> None:
    """Two absences that look identical from the outside, and one is a fault.

    A slate carrying a priceable projection can fail to reach a probability in
    exactly two ways that are not about the athlete, and the card must not print
    one sentence for both:

    * the engine cannot be IMPORTED -- a lab with no model. Simulated the only
      honest way, by removing it from `sys.modules` and from the package, so the
      real `from ... import` inside `_player_distributions_module` is what fails
      rather than a patched-out branch;
    * the slate carries no CONSTANTS -- every bare mapping through
      `SlateModel.coerce` is in this state, and so is any model assembled by
      hand. The card does not load its own: that would be a second load site
      with a season argument it would have to derive, and the seam records what
      an unchecked season argument already cost once.

    Neither is a refusal, neither is a pass, an avoid or a no-value call, and
    neither may be reported as the model having no opinion.
    """
    from cbb_betting_lab.models import slate as SLATE
    from cbb_betting_lab.reports import gameday_card as GC

    model, _ = _slate_model(carry_shapes=False)
    _, census = GC.opinions_for([_wager("player_points", line=14.5)], model, day=DAY)
    assert list(census.declined) == [SLATE.NO_ENGINE_CONSTANTS]
    assert census.priced == 0

    model, _ = _slate_model()
    import cbb_betting_lab.models as MODELS

    monkeypatch.setitem(sys.modules, "cbb_betting_lab.models.player_distributions", None)
    monkeypatch.delattr(MODELS, "player_distributions", raising=False)
    assert GC._player_distributions_module() is None, (
        "the engine still imports, so this test is asserting nothing"
    )
    _, census = GC.opinions_for([_wager("player_points", line=14.5)], model, day=DAY)
    assert list(census.declined) == [SLATE.NO_DISTRIBUTION_ENGINE]
    assert "player_distributions.py" in SLATE.NO_DISTRIBUTION_ENGINE
    assert "not a pass, an avoid or a no-value call" in SLATE.NO_DISTRIBUTION_ENGINE


def _card_of(events: int, *, shapes=None):
    """One fixture athlete on `events` distinct events, and a wager on each.

    The card keys its distribution cache on `(event_id, athlete_id)`, so the
    same athlete on N events is N subjects and therefore a population of N. The
    projection is still the real estimator's — nothing is assembled by hand —
    and the athlete is a regular at 28.0 projected minutes, above the frozen
    file's own `regular_min_projected_minutes` of 15.0.
    """
    from cbb_betting_lab.models import slate as SLATE

    model, resolved = _slate_model(shapes=shapes)
    athletes = dict(model.players["e1"])
    players = {f"e{index}": dict(athletes) for index in range(1, events + 1)}
    lookup = {
        (f"e{index}", name): athlete_id
        for (_, name), athlete_id in model.resolved.items()
        for index in range(1, events + 1)
    }
    wide = SLATE.SlateModel(
        day=DAY,
        matchups={},
        players=players,
        resolved=lookup,
        name_refusals={},
        player_priced_through=model.player_priced_through,
        shapes=model.shapes,
    )
    wagers = [
        _wager("player_points", line=14.5, event_id=f"e{index}")
        for index in range(1, events + 1)
    ]
    return wide, wagers, resolved


def test_design_4s_stop_rule_has_a_caller_on_the_pricing_path(
    tmp_path: Path,
) -> None:
    """It runs on a card, it reports, and it stops the run when it fires.

    **The defect.** `assert_structural_checks` had no caller anywhere outside
    this file: `build()` did not call it, `opinions_for` built one
    `PlayerDistribution` per subject and read every rung off it without ever
    asking for the checks, and a grep over `src/` and `scripts/` found the name
    only in its own definition and docstrings. Design 4's single automatic
    refusal on the engine's own output therefore could not fire on any run, and
    the ratio design 4 also asks to be REPORTED was never printed either. The
    engine commit could reasonably leave it unwired because it priced nothing;
    the wiring commit made the card price and did not wire it.

    **Nothing here is graded and no result is stated.** The probabilities are a
    fixture's, the target is frozen, and the only number asserted is a
    structural ratio.
    """
    from cbb_betting_lab.reports import gameday_card as GC

    # It runs, over the population the card actually built, and it reports.
    model, wagers, _ = _card_of(PD.STRUCTURAL_CHECK_POPULATION_FLOOR)
    probabilities, census = GC.opinions_for(wagers, model, day=DAY)
    assert census.priced == PD.STRUCTURAL_CHECK_POPULATION_FLOOR
    assert len(probabilities) == PD.STRUCTURAL_CHECK_POPULATION_FLOOR
    checks = census.structural_check
    assert checks, "the card priced eight subjects and reported no structural check"
    assert checks["population_athletes"] == float(
        PD.STRUCTURAL_CHECK_POPULATION_FLOOR
    )
    assert checks["population_below_regular_floor"] == 0.0
    assert checks["unconditional_points_vmr_ratio"] == pytest.approx(1.0819, abs=1e-3)
    assert "a ratio of 1.0819" in census.structural_check_line()
    assert "inside design 4's 15% stop" in census.structural_check_line()

    # And it STOPS. The mutation is on the frozen TARGET, which is the one thing
    # in this comparison no path in the engine can influence and which feeds no
    # price: `targets` is read by `structural_checks` and by nothing else, so a
    # moved target changes the check and leaves every probability alone.
    def _move_the_target(document):
        document["constants"]["structural_check_targets"]["value"][
            "unconditional_points_vmr_regulars"
        ] = 2.5

    moved = _shapes_with(tmp_path, _move_the_target, name="moved.json")
    model, wagers, _ = _card_of(PD.STRUCTURAL_CHECK_POPULATION_FLOOR, shapes=moved)
    with pytest.raises(PD.StructuralCheckFailed, match="the discrepancy is the finding"):
        GC.opinions_for(wagers, model, day=DAY)

    # The gap, on the same moved target: below the floor the card prices, reports
    # the very same out-of-band ratio, and does NOT stop. This is the limitation
    # `test_the_population_floor_is_a_gap_that_is_held_open` records, seen from
    # the card, and it goes red the day the floor is reachable by a single
    # subject.
    model, wagers, _ = _card_of(PD.STRUCTURAL_CHECK_POPULATION_FLOOR - 1, shapes=moved)
    _, census = GC.opinions_for(wagers, model, day=DAY)
    assert census.priced == PD.STRUCTURAL_CHECK_POPULATION_FLOOR - 1
    assert abs(
        census.structural_check["unconditional_points_vmr_ratio"] - 1.0
    ) > PD.UNCONDITIONAL_POINTS_VMR_STOP
    assert "STOPS NOTHING" in census.structural_check_line()

    # A card that built no player distribution is not a structural failure and
    # must not read as one.
    _, census = GC.opinions_for([], {}, day=DAY)
    assert census.structural_check == {}
    assert "was not asked" in census.structural_check_line()


# --------------------------------------------------------------------------
# The limitations, recorded as passing assertions
# --------------------------------------------------------------------------


def test_the_gaps_this_engine_still_has_are_the_ones_written_down() -> None:
    """Six, each of which goes red the day it is closed.

    The repository's form for a limitation: not a docstring claim that quietly
    becomes false, but an assertion that fails on the commit which fixes it and
    forces somebody to say so.

    1. **Nothing here grades anything.** There is no de-vig, no log loss, no
       ROI, no interval and no comparison against a price anywhere in this
       module, and design 10's 261,870-wager reconciliation has not run. The
       engine produces probabilities under its own model and stops.
    2. **CLOSED, and replaced by its successor.** The engine was not wired: the
       card answered `NO_DISTRIBUTION_ENGINE` for every prop and no run had
       priced anything through this file. It is wired now —
       `reports/gameday_card.opinions_for` builds one `PlayerDistribution` per
       (event, athlete) from the slate's own provenance-checked constants — and
       the clause's own instruction was to re-count the prop census in the same
       commit. Re-counted, on the fixture card in
       `test_a_priceable_projection_now_carries_a_probability_through_the_card`:
       **16 wagers, 11 priced, 5 declined in 5 distinct buckets** (the two
       markets refused by name, one player market outside the ten, one event the
       model was never asked about, one line above the count lattice ceiling).
       That is a count off a fixture and not a census of the store: design
       10's 261,870-wager reconciliation has not run, and nothing may be graded
       until it does.

       The successor is that **nothing stores what is now priced.** Design 9's
       `data/processed/cbb_player_lines.csv` — one row per (game_id,
       athlete_id, market) carrying `mu`, `phi_conditional`,
       `model_probability`, `push_mass`, `void_probability` and the rest — does
       not exist, so the probabilities this engine produces live only inside a
       call and no run leaves a record of what it thought. The assertion below
       goes red the day that file appears, and whoever writes it owes the
       per-tier report this lab requires rather than a pooled headline.
    3. **No frozen combination target.** Design 8 says combination dispersions
       are "derived from the joint, never fitted -- checked against measured
       pra/pair VMR", and `structural_check_targets` carries no pra, pair or
       points_rebounds VMR at all. The derivation happens; the check design 8
       asks for cannot be run against the file as shipped and needs a refit.
    4. **No tolerance for the second structural check.** `corr(points, threes)`
       is frozen at 0.6021705535430947 and no acceptance band is declared
       anywhere, so it is report-only and cannot stop a run — while the
       thinning produces 0.6706 at the league mix.
    5. **No frozen counterpart for the thinned three-point marginal.** The file
       reconciles the compound POINTS marginal (`points_compound_reconciliation`)
       and nothing reconciles the thinned THREES one, so the measured narrowness
       is reported against no number that could fail.
    6. **Design 4's stop rule cannot run on one athlete.** Its target is pooled
       within-player over 242,634 rows of regulars, so the engine's counterpart
       has to be pooled too, and a card that priced fewer than
       `STRUCTURAL_CHECK_POPULATION_FLOOR` regulars reports the ratio and stops
       nothing — see `test_the_population_floor_is_a_gap_that_is_held_open`.
       What would close it is a frozen target the comparison could be made
       against ONE athlete: a per-bucket or minutes-conditional unconditional
       points VMR. The file carries exactly one and it is the pooled one, which
       is what the assertion below holds.
    """
    # Names the CODE binds or touches, not words in the prose: the prose has to
    # be able to say "no ROI, no log loss" without turning its own check red.
    tree = ast.parse(MODULE.read_text(encoding="utf-8"), filename=str(MODULE))
    named: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            named.add(node.id.lower())
        elif isinstance(node, ast.Attribute):
            named.add(node.attr.lower())
        elif isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            named.add(node.name.lower())
        elif isinstance(node, ast.arg):
            named.add(node.arg.lower())
    # "edge" is deliberately not on this list: the copula's latent cell EDGES
    # are named all over the module and a substring rule cannot tell the two
    # apart. The six below have no innocent spelling in a distribution engine.
    for word in ("log_loss", "devig", "de_vig", "fair_price", "roi", "brier"):
        assert not any(word in name for name in named), (
            f"the engine now names {word!r}. It produces probabilities and "
            "grades nothing; the grading commit is gated on design 10's "
            "reconciliation."
        )

    from cbb_betting_lab.models import slate as SLATE

    assert "could not be imported" in SLATE.NO_DISTRIBUTION_ENGINE, (
        "the seam's sentence has changed again. It says which of two absences "
        "the lab is in — a tree that lost the engine, or a night with no "
        "evidence — and the two look identical from the outside."
    )
    assert "is not written" not in SLATE.NO_DISTRIBUTION_ENGINE
    assert SLATE.NO_ENGINE_CONSTANTS, "the constants-absent bucket has gone"
    assert not (REPO / "data" / "processed" / "cbb_player_lines.csv").exists(), (
        "design 9's store now exists, so the probabilities this engine produces "
        "outlive the call that made them. Say what is in it, report it per tier "
        "rather than pooled, and state that design 10's wager reconciliation "
        "still gates any grading of it."
    )

    document = json.loads(SHAPES.read_text(encoding="utf-8"))
    targets = document["constants"]["structural_check_targets"]["value"]
    assert not any(
        key.startswith(("pra", "points_rebounds", "points_assists", "rebounds_assists"))
        for key in targets
    ), (
        "a combination-market VMR target now exists, so design 8's check on the "
        "derived joint can be run. Write it, and say whether the derivation "
        "reproduces it."
    )
    unconditional = sorted(k for k in targets if "unconditional_points_vmr" in k)
    assert unconditional == ["unconditional_points_vmr_regulars"], (
        "the fit now carries more than one unconditional points VMR. If one of "
        "them is per-bucket or minutes-conditional, design 4's check (a) can be "
        "made against a single athlete and `STRUCTURAL_CHECK_POPULATION_FLOOR` "
        "is no longer needed — say so and delete the floor rather than leaving "
        "a population apparatus around a target that no longer needs one."
    )
    assert "corr_points_threes_given_minutes" in targets
    assert not any("tolerance" in key for key in targets), (
        "a tolerance is declared for a structural check; say which check can "
        "now stop a run and move it out of the report-only list"
    )
    assert "threes" not in document["constants"]["points_compound_reconciliation"]["value"], (
        "the fit now reconciles the thinned three-point marginal, so the ~5% "
        "narrowness has a number it can fail against. Check it."
    )
