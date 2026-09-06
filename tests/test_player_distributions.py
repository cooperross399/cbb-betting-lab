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
    """
    checks = _distribution().structural_checks()
    assert checks["unconditional_points_vmr_target"] == pytest.approx(
        3.0529074370522156, abs=1e-12
    )
    assert checks["unconditional_points_vmr_ratio"] == pytest.approx(1.0819, abs=1e-3)
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

    # The stop rule fires, and it fires by raising rather than by warning.
    with pytest.raises(PD.StructuralCheckFailed, match="the discrepancy is the finding"):
        PD.assert_structural_checks({**checks, "unconditional_points_vmr_ratio": 1.17})
    PD.assert_structural_checks({**checks, "unconditional_points_vmr_ratio": 1.149})

    # The alternative dispersion is the one that trips it, which is the whole
    # argument for `POINTS_EVENT_DISPERSION_KEY`. Arithmetic on frozen
    # constants: the minutes lift is additive, so the unconditional VMR is the
    # conditional one plus 3.0529074370522156 - 2.328891545818532.
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
                **checks,
                "unconditional_points_vmr": alternative,
                "unconditional_points_vmr_ratio": alternative
                / targets["unconditional_points_vmr_regulars"],
            }
        )
    assert PD.POINTS_EVENT_DISPERSION_KEY == "effective_event_dispersion"


# --------------------------------------------------------------------------
# The limitations, recorded as passing assertions
# --------------------------------------------------------------------------


def test_the_gaps_this_engine_still_has_are_the_ones_written_down() -> None:
    """Five, each of which goes red the day it is closed.

    The repository's form for a limitation: not a docstring claim that quietly
    becomes false, but an assertion that fails on the commit which fixes it and
    forces somebody to say so.

    1. **Nothing here grades anything.** There is no de-vig, no log loss, no
       ROI, no interval and no comparison against a price anywhere in this
       module, and design 10's 261,870-wager reconciliation has not run. The
       engine produces probabilities under its own model and stops.
    2. **The engine is not wired to the card.** `models/slate.py` still answers
       `NO_DISTRIBUTION_ENGINE` for every prop, so no run has priced anything
       through this file. Wiring it is a separate commit and it changes the
       census.
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

    assert "no probability exists for this line yet" in SLATE.NO_DISTRIBUTION_ENGINE, (
        "the seam's sentence has changed. If the engine is now wired in, this "
        "clause has closed: say so, and re-count the prop census in the same "
        "commit."
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
    assert "corr_points_threes_given_minutes" in targets
    assert not any("tolerance" in key for key in targets), (
        "a tolerance is declared for a structural check; say which check can "
        "now stop a run and move it out of the report-only list"
    )
    assert "threes" not in document["constants"]["points_compound_reconciliation"]["value"], (
        "the fit now reconciles the thinned three-point marginal, so the ~5% "
        "narrowness has a number it can fail against. Check it."
    )
