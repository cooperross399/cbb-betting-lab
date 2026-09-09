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


def _materiality(shapes=None) -> float:
    """The fit's own materiality floor, off the constant whose rounding it bounds.

    `conditional_dispersion.material_absolute` = 0.02, read through the loaded
    `PlayerShapes` and never typed here. The engine takes the same number from
    the same place; a test that hard-coded it would agree with the engine about
    a floor neither of them got from the fit.
    """
    resolved = shapes or _shapes()
    return float(resolved.constants["conditional_dispersion"]["material_absolute"])


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


#: The mean D1's comb is built at. DECLARED, and it is **not** the fixture
#: athlete's points mean — see :func:`_the_comb`, which measures what happens
#: at his (13.184738) and why the comb is not moved there.
COMB_MEAN = 9.0


def _the_comb(mean: float = COMB_MEAN, shapes=None) -> np.ndarray:
    """A player points count built the refused way, at a declared mean and the file's VMR.

    `distributions._match_variance` applied to a Poisson lattice and asked to
    hit a variance of `mean * conditional_dispersion["points"]`. This is the
    object design 4 refuses, and D1 runs against it so the band is shown to
    still catch what it exists for.

    **The dispersion is read through the loader, never typed.** It was the
    literal `2.3289`, a four-decimal rounding of
    `conditional_dispersion["points"]` = 2.328891545818532, while this
    docstring said the comb is asked for the frozen conditional points VMR.
    The engine module is scanned for retyped frozen constants
    (`test_every_constant_comes_from_the_frozen_file_through_the_loader`) and
    this file is not — and that scan could not have caught this one anyway,
    because it compares against exact frozen values and 2.3289 is a rounding.
    A refit moving that constant would have moved every priced pmf and left the
    comb at the old second moment, while D1's docstring went on saying both
    were at the same two moments. Reading it costs nothing measurable today:
    the comb's interior ratios move from 0.392104/2.751335 to 0.392103/2.751405
    and its worst adjacent swing from 5.073401 to 5.073336, all inside the
    tolerances D1 asserts.

    **The mean is declared, and it is not the fixture's.** 9.0 is not read off
    any projection and must not be quietly replaced by one: the fixture
    athlete's points mean is 13.184738, and at THAT mean the comb's interior
    ratios run 0.350047 to 2.073995 — it still breaks D1's lower edge of 0.4
    and it no longer breaks the upper edge of 2.5. So "tie the mean to the
    projection" would leave `comb.max() > 2.5` false and invite somebody to
    weaken the conjunction to a disjunction. D1 holds both means instead: the
    declared one where the comb fails on both edges, and the fixture's own
    where it fails on one.
    """
    resolved = shapes or _shapes()
    dispersion = float(resolved.value("conditional_dispersion")["points"])
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
    parameters = PD.panjer_parameters(
        mu=1.9, phi=frozen["turnovers"], materiality=_materiality()
    )
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

    Measured here across mu in [0.2, 6.0] at 0.01, off the pmf the recursion
    actually emits: the largest absolute mean error is **1.06e-13** (at
    mu = 5.62, 1.9e-14 relative — floating-point summation and nothing else),
    and the largest |phi_used - phi| is **5.484e-04**, which is 2.74% of the
    fit's own materiality floor of 0.02. The rounding is charged to the
    dispersion, the row says how much, and D3 and D5 — both first-moment
    identities — pay nothing for it.

    **The mean is checked on the PRODUCED COUNT, not on the field that echoes
    the request.** `assert parameters.mu == float(mu), "the rounding moved the
    mean"` was the whole of this claim until this commit, and
    `panjer_parameters` sets `mu=mean` verbatim from its own argument and never
    derives it from the family it built — so the assertion was true by
    construction, as was `float(parameters.trials).is_integer()` on a
    `float(int(round(...)))`. Stubbing the binomial arm's `b` to
    `(trials + 1.02) * probability / used` moves the emitted count's mean
    (player_turnovers came back 1.8900775816106816 against 1.890862827111199)
    while leaving `mu` and `phi_used` untouched, and this test stayed GREEN: the
    four that went red were D3, D5, the two-mean-routes test and the Panjer
    member test, none of which sweep mu. Both fields are still asserted — they
    record what was ASKED for, and `phi_used` is the stored column — and the
    Panjer recursion is now run at every step so the mean and the variance are
    read off the distribution that was made.
    """
    shapes = _shapes()
    dispersion = shapes.value("conditional_dispersion")["turnovers"]
    floor = _materiality(shapes)
    worst = 0.0
    worst_mean = 0.0
    for mu in np.arange(0.2, 6.001, 0.01):
        parameters = PD.panjer_parameters(
            mu=float(mu), phi=dispersion, materiality=floor
        )
        assert parameters.mu == float(mu), (
            "the member no longer records the mean it was asked for. This is "
            "the request, not the produced first moment: `worst_mean` below is "
            "what the recursion actually emitted."
        )
        assert float(parameters.trials).is_integer()
        trials = int(parameters.trials)
        # The binomial's whole support, so the mass is 1 by arithmetic and the
        # moments below are the family's own rather than a truncation's.
        made = PD.compound_pmf(parameters, severity=(0.0, 1.0), size=trials)
        assert float(made.sum()) == pytest.approx(1.0, abs=1e-12)
        counts = np.arange(trials + 1, dtype=float)
        produced_mean = float(made @ counts)
        produced_variance = float(made @ (counts * counts)) - produced_mean**2
        worst_mean = max(worst_mean, abs(produced_mean - float(mu)))
        assert produced_variance / produced_mean == pytest.approx(
            parameters.phi_used, rel=1e-9
        ), (
            f"at mu={float(mu)} the emitted count has a variance-to-mean ratio "
            f"of {produced_variance / produced_mean} and the member says it "
            f"carries {parameters.phi_used}. `phi_used` is design 9's stored "
            "`phi_conditional` column, so a member that does not describe its "
            "own pmf would be written into the store as though it did."
        )
        worst = max(worst, abs(parameters.phi_used - dispersion))
    assert 0.0 < worst_mean < 1e-11, (
        f"the produced count's mean is now {worst_mean:.3e} away from the mean "
        "it was matched on. The docstring above quotes 1.06e-13, which is "
        "floating-point summation over up to 350 trials; anything at 1e-11 or "
        "worse is the parameterisation, and D3 and D5 are first-moment "
        "identities that must not pay for the integer-n rounding."
    )
    assert worst == pytest.approx(5.484e-04, abs=1e-6), (
        f"the binomial rounding error is now {worst:.3e}; the docstring above "
        "quotes 5.484e-04 and must be re-measured"
    )
    assert worst < 0.02, "the rounding moved the dispersion materially"
    assert worst < floor and floor == 0.02, (
        "the same bound, against the floor read off the frozen file rather than "
        "typed here. `panjer_parameters` now REFUSES past it — see "
        "`test_the_binomial_rounding_refuses_a_material_move_and_reads_its_floor"
        "_from_the_file` — so this loop passing is the measurement that says the "
        "refusal cannot fire on the file as shipped"
    )


def test_the_binomial_rounding_refuses_a_material_move_and_reads_its_floor_from_the_file(
    tmp_path: Path,
) -> None:
    """The refusal `panjer_parameters` promised in prose, performed, with a floor from the file.

    **The defect.** Its docstring said "this function refuses if the rounding
    moved it further than `conditional_dispersion.material_absolute` = 0.02, the
    fit's own materiality floor", and no such comparison existed anywhere in
    `src/`: `material_absolute` was read by nothing, `phi_requested` was stored
    on `PanjerParameters` and never read back, and the mean-preserving convention
    `n = max(1, round(mu/(1-phi)))`, `p = mu/n` silently substituted a different
    dispersion whenever `mu/(1-phi)` rounded below one. Measured on the code as
    it stood, nothing raised: `(mu=0.3, phi=0.5)` produced `phi_used = 0.70`,
    moved 0.20 — ten times the floor the docstring named — and `(0.05, 0.8)`,
    `(0.04, 0.9)` and `(0.02, 0.95)` moved 0.15, 0.06 and 0.03. The house rule
    is that a docstring must not describe a check the code does not do, and the
    repair is the check rather than the deletion, because the substitution is
    real: the count would be priced at a width nobody fitted.

    **The floor is an argument, never a module constant.** It is
    `conditional_dispersion.material_absolute`, read out of the frozen file by
    `build` and threaded down — the same rule
    `population_structural_checks` follows for `regular_min_projected_minutes`.
    Held here by tightening the file's own number and watching the same athlete
    refuse.

    **And it ships latent, which is stated rather than hidden.** `turnovers` is
    the one frozen dispersion below 1, so the largest move the shipped constants
    can produce is `1 - 0.9828561088984643 = 0.01714`, inside the 0.02 floor;
    over mu in [0.001, 6.0] at a step of 0.001 the worst is 1.614e-02, also
    inside. This refusal cannot fire on the file as shipped. It fires on a refit
    that moves a sub-1 dispersion further from 1, or on a second stat entering
    the binomial arm.
    """
    shapes = _shapes()
    floor = _materiality(shapes)
    assert floor == 0.02, "the fit's materiality floor moved; re-measure below"

    # The four the finding measured. Every one was silent; every one refuses.
    for mu, phi, moved in (
        (0.3, 0.5, 0.20),
        (0.05, 0.8, 0.15),
        (0.04, 0.9, 0.06),
        (0.02, 0.95, 0.03),
    ):
        with pytest.raises(PD.PlayerDistributionError, match="materiality floor") as raised:
            PD.panjer_parameters(mu=mu, phi=phi, materiality=floor)
        assert f"{floor}" in str(raised.value), (
            "the refusal must quote the floor it was given, so a reader can see "
            "which number refused and where it came from"
        )
        # The same arithmetic against a floor wide enough to admit it still
        # prices, so what refuses is the SIZE of the move rather than the
        # rounding itself, and the trial floor is the mechanism.
        admitted = PD.panjer_parameters(mu=mu, phi=phi, materiality=moved + 0.01)
        assert admitted.trials == 1.0
        assert admitted.mu == mu, "the rounding must never move the mean"
        assert abs(admitted.phi_used - admitted.phi_requested) == pytest.approx(
            moved, abs=5e-3
        )

    # A floor that cannot be compared is a guard that passes everything:
    # `abs(gap) > nan` is False. Refused before a family is chosen.
    turnovers = shapes.value("conditional_dispersion")["turnovers"]
    for bad in (float("nan"), 0.0, -0.02, float("inf")):
        with pytest.raises(PD.PlayerDistributionError, match="is not a floor"):
            PD.panjer_parameters(mu=1.9, phi=turnovers, materiality=bad)

    # The shipped file cannot reach the floor, measured rather than asserted.
    assert PD.panjer_family(turnovers) == "binomial"
    assert 1.0 - turnovers == pytest.approx(0.01714389110153569, abs=1e-15)
    assert 1.0 - turnovers < floor, (
        "the frozen turnovers dispersion is now further from 1 than the fit's "
        "materiality floor, so the trial floor can substitute a dispersion the "
        "fit never stood behind. This refusal is no longer latent: say so."
    )
    worst = max(
        abs(
            PD.panjer_parameters(
                mu=float(mu), phi=turnovers, materiality=floor
            ).phi_used
            - turnovers
        )
        for mu in np.arange(0.001, 6.0, 0.001)
    )
    assert worst == pytest.approx(1.614e-02, abs=1e-5) and worst < floor

    # The floor comes from the FILE. Tighten the file's own number and the same
    # athlete refuses: his worst turnovers rounding across the 45 minutes nodes
    # is 2.612e-04, inside 0.02 and far outside 1e-06.
    def _tighten(document: dict) -> None:
        document["constants"]["conditional_dispersion"]["material_absolute"] = 1e-06

    tight = _shapes_with(tmp_path, _tighten, name="tight.json")
    assert _materiality(tight) == 1e-06
    with pytest.raises(PD.PlayerDistributionError, match="materiality floor of 1e-06"):
        _distribution(tight)

    # And it is carried, not re-chosen: every family the engine built holds the
    # file's floor, and a thinned family holds the floor of the count it came
    # from rather than one this module picked.
    built = _distribution(shapes)
    moves = [
        abs(parameters.phi_used - parameters.phi_requested)
        for parameters in built.stat_parameters["turnovers"].values()
    ]
    assert max(moves) == pytest.approx(2.6119e-04, abs=1e-7)
    assert all(
        parameters.materiality == floor
        for table in built.stat_parameters.values()
        for parameters in table.values()
    )
    events = built.event_parameters[built.price_node()]
    assert events.materiality == floor
    assert PD.thin(events, 0.35).materiality == floor
    poisson = PD.panjer_parameters(mu=2.0, phi=1.0, materiality=floor)
    assert PD.thin(poisson, 0.5).materiality == floor


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
    `VMR = 1 + q*(phi - 1)`. This exercises the ONE member the shipped
    `effective_event_dispersion` of 1.1059306970490195 selects — the negative
    binomial — on the real fixture, and says so rather than saying "every
    member": the claim held for all three is the next test's, and until
    2026-09-07 this docstring made it while `thin`'s binomial arm ran in no
    test on this branch. `rates["threes"]` and
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


def test_thinning_keeps_the_family_and_the_dispersion_identity_on_all_three_arms(
) -> None:
    """`VMR = 1 + q*(phi - 1)`, held for every (a,b,0) member and not for one.

    The binomial arm of `thin` -- the four statements building the thinned
    `PanjerParameters` -- was executed by no test on this branch, because the
    shipped `effective_event_dispersion` of 1.1059306970490195 selects the
    negative binomial and every existing thinning test goes through the real
    fixture. Design 4's claim that `player_threes` "falls out as the
    three-point component of the same object" rests on those statements as much
    as on the two that were covered, and a `b=(trials + 1) * probability / used`
    that lost its `+ 1` would emit a wrong pmf for every three-point price the
    day a refit moved the dispersion below `1 - POISSON_BAND`.

    Each arm is checked twice: the identity, and the produced pmf against the
    distribution the thinned member is supposed to BE, computed here from
    `math.comb`/`math.exp`/`math.lgamma` rather than from the recursion under
    test. Measured, worst absolute pmf error across the three: binomial
    1.67e-16, Poisson 3.47e-18, negative binomial 5.55e-17.
    """
    floor = 1e-6
    size = 24
    cases = {
        # phi < 1 - POISSON_BAND: binomial. n = round(3.0/0.3) = 10, p = 0.3.
        "binomial": PD.panjer_parameters(mu=3.0, phi=0.7, materiality=floor),
        "poisson": PD.panjer_parameters(mu=3.0, phi=1.0, materiality=floor),
        "negative_binomial": PD.panjer_parameters(mu=3.0, phi=1.6, materiality=floor),
    }
    keep = 0.5
    worst: dict[str, float] = {}
    for family, parameters in cases.items():
        assert parameters.family == family, (
            f"the fixture for the {family} arm selected {parameters.family}; "
            "the arm this test exists for is not the one being run"
        )
        thinned = PD.thin(parameters, keep)
        assert thinned.family == family, "thinning changed the family"
        assert thinned.mu == pytest.approx(parameters.mu * keep, rel=1e-12)
        assert thinned.phi_used == pytest.approx(
            1.0 + keep * (parameters.phi_used - 1.0), rel=1e-12
        ), (
            f"the {family} arm does not produce `1 + q*(phi - 1)`, which is the "
            "identity design 4's 'same object' claim is made of"
        )

        produced = PD.compound_pmf(thinned, severity=(0.0, 1.0), size=size)
        mean, variance = _moments(produced)
        assert variance / mean == pytest.approx(thinned.phi_used, rel=1e-6), (
            f"the {family} arm's produced pmf does not carry the dispersion its "
            "parameters declare"
        )

        if family == "binomial":
            trials, probability = int(thinned.trials), 1.0 - thinned.phi_used
            assert (trials, probability) == (10, pytest.approx(0.15, abs=1e-12)), (
                "the thinned binomial is not n=10 at p=0.15, so the arithmetic "
                "below is being compared against a different distribution"
            )
            exact = [
                math.comb(trials, k)
                * probability**k
                * (1.0 - probability) ** (trials - k)
                if k <= trials
                else 0.0
                for k in range(size + 1)
            ]
        elif family == "poisson":
            mu = thinned.mu
            exact = [
                math.exp(-mu + k * math.log(mu) - math.lgamma(k + 1.0))
                for k in range(size + 1)
            ]
        else:
            shape, beta = thinned.shape_r, thinned.scale_beta
            odds = beta / (1.0 + beta)
            exact = [
                math.exp(
                    math.lgamma(shape + k)
                    - math.lgamma(shape)
                    - math.lgamma(k + 1.0)
                    + shape * math.log(1.0 - odds)
                    + k * math.log(odds)
                )
                for k in range(size + 1)
            ]
        worst[family] = float(np.max(np.abs(np.asarray(exact) - produced)))
        assert worst[family] < 1e-12, (
            f"the thinned {family} is not the {family} it claims to be: worst "
            f"absolute pmf error {worst[family]:.3e}"
        )
    print(f"worst absolute pmf error by arm: {worst}")


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
            PD.panjer_parameters(mu=mu, phi=dispersion, materiality=_materiality(shapes)),
            severity=(0.0, 1.0),
            size=cap,
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


def test_the_stored_phi_column_is_nan_for_a_sum_and_the_event_phi_for_a_compound() -> None:
    """Design 9's `phi_conditional`, on all ten markets rather than on one.

    `PlayerDistribution.phi_conditional` was asserted exactly once in this file
    — `player_rebounds` at 1.9 — while its docstring makes two further
    behavioural claims that nothing checked. Stubbing the method to return
    `0.0` for the combination markets and `1.0` for the compound stats left the
    file green at 40 passed, and a `cbb_player_lines.csv` written by the first
    consumer would then carry `phi_conditional = 0.0` on a pra row (which reads
    as a measured dispersion of zero rather than "no phi was handed to this
    sum") and 1.0 — Poisson — on a points row.

    The three cases, measured:

    * **NaN for the four combination markets.** No phi is handed to a sum: its
      width is produced by the components, the copula and the mixture. NaN is
      asserted as NaN and separately as *not zero*, because zero is the value a
      well-meaning fill would put there and every comparison against NaN is
      False, so `phi == 0.0` would not have caught it either.
    * **The SHARED SCORING-EVENT dispersion for `player_points`**, which is
      `points_compound_reconciliation[POINTS_EVENT_DISPERSION_KEY]` =
      1.1059306970490195 and is not what a reader would expect on that row:
      the frozen `conditional_dispersion` says 2.328891545818532 for points,
      which is the produced marginal's width and is where
      :meth:`structural_checks` reports it. **`player_threes` no longer carries
      the same number**, and the assertion here is now that it must not: the
      threes count is built from `thin(event, p3)` and its column is that
      family's own dispersion. See
      `test_the_threes_phi_column_is_the_thinned_width_the_count_was_built_at`,
      which owns that case; this test keeps the tripwire that stops it being
      folded back into the points branch.
    * **The rounding is in the column, for the one market that has one.**
      `player_turnovers` is the binomial arm: the frozen conditional dispersion
      is 0.9828561088984643 and the column reads 0.9828493167608962, a move of
      6.79e-06 charged to the dispersion by the integer-`n` re-solve, three
      orders inside the fit's own materiality floor of 0.02. The other three
      Panjer stats are negative binomial, where no rounding happens and the
      column is the frozen constant exactly.

    And a market refused by name has no column at all rather than a filled one.
    """
    distribution = _distribution()
    shapes = _shapes()
    frozen = shapes.value("conditional_dispersion")
    event_phi = float(
        shapes.value("points_compound_reconciliation")[PD.POINTS_EVENT_DISPERSION_KEY]
    )

    for market in ("player_pra", "player_points_rebounds", "player_points_assists",
                   "player_rebounds_assists"):
        phi = distribution.phi_conditional(market)
        assert math.isnan(phi), (
            f"{market} carries phi_conditional={phi!r}. No dispersion is handed "
            "to a sum — its width is produced by the components, the copula and "
            "the mixture — and a number in this column is a parameter that does "
            "not exist."
        )
        assert phi != 0.0, f"{market}: NaN, not a zero fill"

    assert distribution.phi_conditional("player_points") == event_phi, (
        "player_points: the column must carry the dispersion of the shared "
        "scoring-event count, because a compound sum is handed no phi of its "
        f"own. Frozen: {event_phi}."
    )
    assert distribution.phi_conditional("player_threes") != event_phi, (
        "player_threes carries the UN-THINNED event dispersion again. The "
        "count at the price node is built from `thin(event, p3)`, whose "
        "phi_used is a different number, so this cell would be naming a width "
        "nothing was priced at — and naming it in the wrong direction, as "
        "1.96% wide against the frozen threes dispersion where the priced "
        "marginal is 5.14% narrow."
    )
    assert event_phi == pytest.approx(1.1059306970490195, abs=1e-12)
    assert distribution.phi_conditional("player_points") != 1.0, (
        "a points row reading 1.0 is a Poisson event count, which is not the "
        "family this engine built"
    )
    assert distribution.phi_conditional("player_points") != frozen["points"], (
        "the column is the EVENT count's dispersion, not the produced points "
        "marginal's 2.3289; the marginal's width is a structural check and is "
        "reported there"
    )
    assert distribution.phi_conditional("player_threes") != frozen["threes"]

    for stat in ("rebounds", "assists", "steals"):
        assert distribution.phi_conditional(f"player_{stat}") == float(frozen[stat]), (
            f"{stat} is on the negative binomial arm, where nothing is rounded "
            "and the column is the frozen constant exactly"
        )
    assert distribution.phi_conditional("player_rebounds") == pytest.approx(
        1.1029646164554165, abs=1e-12
    )

    rounded = distribution.phi_conditional("player_turnovers")
    assert rounded != float(frozen["turnovers"]), (
        "turnovers is the binomial arm and its integer-`n` re-solve moves the "
        "dispersion. A column reading the frozen constant exactly means the "
        "rounding is being reported as if it had not happened."
    )
    assert rounded == pytest.approx(0.9828493167608962, abs=1e-12)
    move = abs(rounded - float(frozen["turnovers"]))
    assert move == pytest.approx(6.79e-06, abs=1e-8), (
        f"the turnovers rounding is now {move:.3e}; the docstring quotes "
        "6.79e-06 and must be re-measured"
    )
    assert move < _materiality(shapes)

    for refused in PR.MARKETS_REFUSED_BY_NAME:
        with pytest.raises(PD.MarketRefused):
            distribution.phi_conditional(refused)


def test_the_threes_phi_column_is_the_thinned_width_the_count_was_built_at() -> None:
    """Design 9's `phi_conditional` for `player_threes`, off the count's own family.

    **The defect.** The method returned
    `dispersions["points_event_dispersion_used"]` = 1.1059306970490195 for
    `player_threes`, which is the SHARED SCORING-EVENT count's dispersion. The
    threes count is not that count: `node_component_pmf` builds it from
    `thin(event_parameters[node], severity[3])`, whose `phi_used` is
    `1 + p3*(phi_events - 1)` = 1.0288960137061232 at this athlete's
    three-point share of 0.2727822483104362. So the column named a width no
    lattice in the engine was ever built at, and named it in the wrong
    direction: against the frozen `conditional_dispersion["threes"]` of
    1.0846864899201918, the old cell reads 1.96% WIDE and the marginal that is
    actually priced is 5.14% NARROW. The old cell was also bit-identical to the
    `player_points` cell, so two different distributions shared one number.

    **The premise was checked before it was repaired**, because the old
    behaviour was disclosed rather than hidden — the body of the method's
    docstring declared the convention while its summary line ("the dispersion
    actually handed to the family that made this count") contradicted it. What
    settles it is that for `player_threes` there IS a family and it DOES carry
    a phi: `thin` returns a `PanjerParameters` whose `phi_requested` and
    `phi_used` are both the thinned dispersion, and `compound_pmf` is handed
    that object. `player_points` is the case where no such family exists — a
    compound sum is handed no dispersion of its own — and its cell is
    unchanged at 1.1059306970490195, which this test also asserts, because the
    repair must not migrate.

    **The column and the lattice are now one construction, not two.**
    `PlayerDistribution._threes_parameters` is called by
    `node_component_pmf` and by `phi_conditional`, so the number reported and
    the number priced cannot drift; the assertion below reads the produced
    `threes_vmr_given_minutes` back off the mixture-free node pmf and finds
    1.0288960135790235, 1.27e-10 under the column, all of it count-lattice
    truncation.

    **What is NOT asserted here.** Nothing about whether 5.14% narrow is
    acceptable. Design 4 declares a tolerance for the unconditional points VMR
    and for nothing else, `structural_check_targets` carries none for this, and
    a test that turned the narrowness into a threshold would be inventing a
    stop rule the design does not have. The narrowness is measured, reported,
    and shown to move with the athlete's own three-point share rather than with
    anything the model chose.
    """
    shapes = _shapes()
    distribution = _distribution(shapes)
    node = distribution.price_node()
    share = float(distribution.severity[3])
    event = distribution.event_parameters[node]
    event_phi = float(
        shapes.value("points_compound_reconciliation")[PD.POINTS_EVENT_DISPERSION_KEY]
    )
    frozen_threes = float(shapes.value("conditional_dispersion")["threes"])

    column = distribution.phi_conditional("player_threes")
    thinned = PD.thin(event, share)

    assert column == thinned.phi_used, (
        f"the threes column reads {column!r} and the family the count was "
        f"built from carries {thinned.phi_used!r}. The column has to be the "
        "family's own number, bit for bit, or it is a second calculation of "
        "what the engine intended rather than a reading of what it did."
    )
    assert column == pytest.approx(1.0288960137061232, abs=1e-15)
    assert column == pytest.approx(1.0 + share * (event.phi_used - 1.0), rel=1e-15)
    assert share == pytest.approx(0.2727822483104362, abs=1e-15)

    assert column != event_phi, (
        "the threes column is the un-thinned event dispersion again, which is "
        "the defect: the thinning is what makes threes fall out of the points "
        "object, and a dispersion that ignores it describes a different "
        "distribution from the one being priced"
    )
    assert distribution.phi_conditional("player_points") == event_phi, (
        "the repair migrated onto player_points. A compound sum is handed no "
        "phi of its own; the event count is the only family in that "
        "construction and 1.1059306970490195 is its dispersion."
    )
    assert distribution.phi_conditional("player_points") != column

    # The column is the width the lattice actually has.
    mean, variance = _moments(distribution.node_component_pmf("threes", node))
    produced = variance / mean
    assert produced == pytest.approx(1.0288960135790235, abs=1e-12)
    assert 0.0 < column - produced < 1e-09, (
        f"the column is {column!r} and the produced lattice VMR is "
        f"{produced!r}. The gap is count-lattice truncation and is one-sided "
        "and tiny; a two-sided or larger gap means the column and the lattice "
        "are no longer the same family."
    )

    # The direction of the disclosure, measured rather than asserted as a bound.
    narrow = 1.0 - column / frozen_threes
    assert narrow == pytest.approx(0.051435, abs=1e-6), (
        f"the priced three-point marginal is now {narrow * 100:.4f}% narrow "
        "against the frozen threes dispersion; the docstrings quote 5.14% and "
        "must be re-measured"
    )
    stale = event_phi / frozen_threes - 1.0
    assert stale == pytest.approx(0.0195856, abs=1e-7), (
        "the number the OLD column reported reads as 1.96% wide against the "
        "same frozen constant, which is why the two are not interchangeable: "
        "they disagree about the sign"
    )

    # It moves with the athlete's own mix, not with the node and not with the
    # model. The league `value_pmf`'s share is what the 5.91% recorded at
    # `POINTS_EVENT_DISPERSION_KEY` is measured at.
    for other in (0, node, distribution.minutes.size - 1):
        assert PD.thin(
            distribution.event_parameters[other], share
        ).phi_used == pytest.approx(column, abs=1e-15), (
            "the thinned dispersion moved with the minutes node. `thin` scales "
            "`beta`, and `beta` is `phi - 1` at every node, so it cannot."
        )
    league = float(shapes.value("value_pmf")[2])
    assert league == pytest.approx(0.19423721541072833, abs=1e-15)
    league_phi = 1.0 + league * (event_phi - 1.0)
    assert league_phi == pytest.approx(1.020575683621319, abs=1e-15)
    assert 1.0 - league_phi / frozen_threes == pytest.approx(0.059105, abs=1e-6), (
        "`POINTS_EVENT_DISPERSION_KEY` records the price of the dispersion "
        "choice as `1.0206 ... about 6% narrow`, and that is the LEAGUE mix, "
        "not this athlete's. The two numbers are both right and are not the "
        "same number, which is why each now says which mix it is at."
    )
    module = " ".join(MODULE.read_text(encoding="utf-8").split())
    assert (
        "there and the narrowness 5.9105%" in module
        and "0.2727822483104362 gives 1.0288960137061232 and 5.14%" in module
    ), (
        "`POINTS_EVENT_DISPERSION_KEY`'s note quoted `about 6% narrow` with no "
        "mix named, and `assert_structural_checks` quoted `~6%`. Both "
        "reproduce — at the LEAGUE mix — and neither said so, which is how a "
        "reader ends up comparing them to the column this athlete's row "
        "carries. The mix is named in both places now and this holds it."
    )

    # One construction, and it is the one the count is built from.
    assert distribution._threes_parameters(node) == thinned
    doc = " ".join((PD.PlayerDistribution.phi_conditional.__doc__ or "").split())
    assert "carries the THINNED dispersion" in doc
    assert "1.0288960137061232" in doc and "0.2727822483104362" in doc
    assert "1.96% wide when the marginal actually priced is 5.14% narrow" in doc


# --------------------------------------------------------------------------
# D1 -- the comb
# --------------------------------------------------------------------------


def test_d1_no_priced_pmf_carries_the_match_variance_comb(tmp_path: Path) -> None:
    """Design 4's smoothness band, with the object it exists to catch run beside it.

    The band is `[0.4, 2.5]` on adjacent-integer ratios across the interior
    support. Measured on this fixture, over the ten priced markets, the worst
    ratios are **0.489** and **2.042**; the same measurement on
    `_match_variance` at a mean of 9.0 and the frozen conditional points VMR
    gives **0.392** and **2.751**, so the band still catches the comb on both
    edges. The comb's largest adjacent swing — the ratio of one ratio to the
    next — is **5.07**, which is the design's "adjacent-integer swings of ~5x",
    against **2.89** for the engine's worst market.

    **The comb's two moments, and what each is.** The VMR is read from the
    frozen file through the loader, so a refit moves the comb with the priced
    pmfs; the check that it does is a copy of the file with that constant moved
    to 4.0, whose comb must differ. The MEAN is declared at
    :data:`COMB_MEAN` = 9.0 and is not any projection's. Both are held here
    because the comb is weaker at the fixture athlete's own points mean of
    13.184738: its ratios there run 0.350047 to 2.073995, which trips the lower
    edge and NOT the upper one. That is the trap in "tie the fixture to the
    projection" — it would make `comb.max() > 2.5` false and the obvious next
    move is to weaken the conjunction. Both means are asserted instead, and the
    weaker one is asserted as the single-edge catch it actually is.

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

    # The comb's dispersion comes from the FILE. Move that constant in a copy
    # and the comb has to move with it; a retyped literal would not.
    def _move_points_vmr(payload: dict) -> None:
        payload["constants"]["conditional_dispersion"]["value"]["points"] = 4.0

    moved = _shapes_with(tmp_path, _move_points_vmr, name="comb.json")
    assert not np.allclose(_the_comb(shapes=moved), _the_comb()), (
        "the frozen conditional points VMR moved and D1's comb did not, so the "
        "comb is built on a number typed here rather than read from the file. "
        "A refit would then leave the engine's pmfs at the new second moment "
        "and this comb at the old one, while D1 went on claiming both are at "
        "the same two moments."
    )

    # And what the comb looks like at the fixture athlete's OWN points mean:
    # weaker, one edge instead of two, which is why COMB_MEAN is declared.
    at_his_mean = _interior_ratios(_the_comb(mean=distribution.mean("player_points")))
    assert distribution.mean("player_points") == pytest.approx(13.184738, abs=5e-6)
    assert at_his_mean.min() == pytest.approx(0.350, abs=5e-3)
    assert at_his_mean.max() == pytest.approx(2.074, abs=5e-3)
    assert at_his_mean.min() < 0.4, (
        "the comb at the fixture athlete's own points mean now passes D1 on "
        "BOTH edges, so at his mean the band catches nothing. Do not widen the "
        "band and do not move COMB_MEAN; find out what changed."
    )
    assert at_his_mean.max() <= 2.5, (
        "the comb at the fixture's own mean now trips the upper edge too, so "
        "the reason COMB_MEAN is declared rather than read off the projection "
        "has gone. Re-measure and say so before moving it."
    )


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
    """P(over) strictly decreasing in the line, on EVERY rung that was asked for.

    Off ONE object, which is the content of it: the football lab shipped a
    ladder whose -6.5 was better value than its -7.5 because it had two models
    for one quantity. There is no alternate-ladder path here and there must
    never be one.

    **The rung count is asserted before the monotonicity, because a rung that is
    not there cannot be non-monotone.** As written until this commit the whole
    of D2 was `all(a > b for a, b in zip(overs, overs[1:]))` and three `zip`s
    over the same list — every one of which is vacuously true on an empty list
    and silently short on a truncated one — and nothing asserted
    `len(rungs) == len(lines)`. `PlayerDistribution.ladder` has exactly one
    caller in this tree (this test), so a ladder returning fewer rungs than it
    was asked for was constrained nowhere: stubbed to `return []`, the file
    stayed green at 40 passed.

    The realistic version is not the empty return. It is a rung FILTER —
    wrapping `price_line` in `try/except MarketRefused: continue` so the rungs
    above the count lattice's ceiling are dropped rather than refused — which
    ships a ladder silently missing its top and leaves D2 green on whatever came
    back. Both halves are held below: one rung per requested line in the
    requested order on both sides, and a line past the ceiling REFUSING out of
    `ladder` rather than vanishing from it. Measured on this fixture, the four
    lattices run to 94 counts (points), 41 (rebounds), 22 (threes) and 165
    (pra), so a 23.5 threes rung is above the ceiling and a 4.5 one is not.
    """
    distribution = _distribution()
    for market, lines in (
        ("player_points", np.arange(4.5, 24.0, 1.0)),
        ("player_rebounds", np.arange(1.5, 11.0, 1.0)),
        ("player_threes", np.arange(0.5, 5.0, 1.0)),
        ("player_pra", np.arange(12.5, 32.0, 1.0)),
    ):
        rungs = distribution.ladder(lines, market_key=market, side="over")
        assert len(rungs) == len(lines), (
            f"{market}: {len(lines)} lines went in and {len(rungs)} rungs came "
            "back. A ladder that drops a rung it was asked for reports nothing "
            "about that line, and every monotonicity check below is over "
            "whatever survived rather than over what was priced."
        )
        assert [line for line, _ in rungs] == [float(line) for line in lines], (
            f"{market}: the rungs are not the lines that were asked for, in "
            "order. The caller reads the ladder positionally."
        )
        overs = [triple[0] for _, triple in rungs]
        assert all(a > b for a, b in zip(overs, overs[1:])), market
        under_rungs = distribution.ladder(lines, market_key=market, side="under")
        assert len(under_rungs) == len(lines), (
            f"{market}: the under side returned {len(under_rungs)} rungs for "
            f"{len(lines)} lines"
        )
        unders = [triple[0] for _, triple in under_rungs]
        assert all(a < b for a, b in zip(unders, unders[1:])), market
        assert len(rungs) == len(unders)
        for (line, triple), under in zip(rungs, unders):
            assert triple[0] + triple[1] + under == pytest.approx(1.0, abs=1e-12)

    # And the rung that cannot be priced is REFUSED, never dropped. This is the
    # assertion the count above exists for: with it, a `try/except
    # MarketRefused: continue` inside `ladder` fails here, and without it the
    # same filter would silently shorten every ladder that reaches its ceiling.
    ceiling = distribution.count_pmf("player_threes").size - 1
    assert ceiling == 22, (
        f"the threes lattice now runs to {ceiling}; the line below has to stay "
        "above the ceiling for this to be the refusal case"
    )
    with pytest.raises(PD.MarketRefused, match="above the count lattice ceiling"):
        distribution.ladder(
            [0.5, 1.5, float(ceiling) + 1.5], market_key="player_threes", side="over"
        )


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

    **Why the two assertions this test shipped with could not fail on the
    defect they name.** `produced == approx(target, rel=0.04)` and
    `abs(produced) <= abs(target)` are BOTH satisfied when `produced IS target`,
    so the one outcome the docstring calls "fitting a constant at price time"
    passed them: stubbing `realised_correlations` to return
    `(matrix[0, 1], matrix[0, 1])` left the file green at 40 passed, and the
    three measured numbers the paragraph above quotes were asserted nowhere in
    the tree. Two things are held now instead of described.

    * **The shortfall is a measured band, not a one-sided inequality.** Each
      pair realises strictly LESS than it was asked for, by 1.81% (points|
      rebounds), 3.45% (points|assists) and 3.73% (rebounds|assists) of the
      target's absolute value. A solve-back drives that to zero, which is
      outside the band from below; a discretisation that started losing a
      quarter of the coupling is outside it from above and has to be
      re-measured rather than absorbed.
    * **The number reported as the TARGET is the frozen constant**, read out of
      `residual_correlation` through the loader. Without that, a latent
      parameter tuned until the realised correlation hit the frozen one would
      report the tuned latent as its own target and land back inside any band
      written on the pair alone.
    """
    distribution = _distribution()
    node = distribution.price_node()
    frozen = _shapes().value("residual_correlation")
    realised = distribution.realised_correlations()
    assert set(realised) == {"points|rebounds", "points|assists", "rebounds|assists"}
    measured = {
        "points|rebounds": 0.10333029585215918,
        "points|assists": -0.016045437179660036,
        "rebounds|assists": 0.05600887929455022,
    }
    for pair, (target, produced) in realised.items():
        assert target == float(frozen[pair]), (
            f"{pair}: the copula reports a target of {target} and the frozen "
            f"`residual_correlation` says {frozen[pair]}. The reported target "
            "is what every check below is relative to; a latent solved back "
            "onto the constant would report the solved value here and look "
            "faithful."
        )
        assert produced == pytest.approx(target, rel=0.04), pair
        assert abs(produced) <= abs(target), (
            f"{pair}: the discretised copula realises MORE correlation than it "
            "was asked for, which is the direction a solved-back parameter "
            "would produce"
        )
        assert produced == pytest.approx(measured[pair], abs=1e-6), (
            f"{pair}: realises {produced!r}; the docstring above quotes "
            f"{measured[pair]:.5f} and must be re-measured"
        )
        shortfall = 1.0 - abs(produced) / abs(target)
        assert 0.005 < shortfall < 0.06, (
            f"{pair}: the copula realises {shortfall * 100:.3f}% less "
            "correlation than it was asked for. At zero the latent parameter "
            "has been solved back onto the frozen constant, which is fitting a "
            "constant at price time and is the one thing this method exists to "
            "make visible; far above the band the discretisation loss has "
            "moved and the three numbers in the docstring are stale."
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


#: How close the D3 mean identity has to come before it counts as closed.
#: `mean(points + rebounds)` equals `mean(points) + mean(rebounds)` exactly in
#: exact arithmetic, so what is left is rounding on means of order ten, where
#: one ULP is about 1.8e-15.
#:
#: This was `pytest.approx(0.0, abs=1e-16)`, against a pinned `1.421e-14` for
#: the three-component market -- the only 1e-16 in a file whose other 45
#: tolerance assertions are 1e-12 or 1e-15. At that width it did not test that
#: the identity closes. It tested that the same floating-point operations
#: happened in the same order, and they do not: adding one unrelated test
#: module to the suite moved the two-component gap from 0.0 to 3.553e-15 on
#: x86-64 CI while arm64 stayed at 0.0, because an extra import changes
#: allocation and a numpy reduction reassociates. Both results are exact to
#: within two ULPs of their operands.
#:
#: The bound is 1e-12 because that is six orders BELOW the magnitude this same
#: test measures for a split that genuinely does not close -- the quoted
#: 1.291e-06 and 7.550e-07 below. `test_the_closing_bound_cannot_hide_a_real_
#: failure` pins that gap, so this number cannot be widened later into one
#: that admits the thing it exists to catch.
MEAN_IDENTITY_CLOSES = 1e-12

#: The smallest gap this test elsewhere records for an identity that does NOT
#: close. The bound above has to stay far under it.
MEAN_IDENTITY_FAILS_AT = 7.550e-07


def test_the_closing_bound_cannot_hide_a_real_failure() -> None:
    """A tolerance is only honest while it still refuses something.

    `MEAN_IDENTITY_CLOSES` was widened once, from a bit-exact 1e-16 that no
    two machines agreed on. This is the assertion that stops it being widened
    again into a number that would accept a split which does not close.
    """
    assert MEAN_IDENTITY_CLOSES < MEAN_IDENTITY_FAILS_AT / 1000, (
        f"the closing bound {MEAN_IDENTITY_CLOSES:.1e} is within three orders "
        f"of {MEAN_IDENTITY_FAILS_AT:.3e}, the smallest gap this test records "
        "for an identity that does not close. At that width it would accept "
        "the failure it exists to catch."
    )
    # And it stays above the rounding it must tolerate: means of order ten,
    # one ULP about 1.8e-15, and a reassociated sum measured at 3.553e-15.
    assert MEAN_IDENTITY_CLOSES > 1e-14


def test_the_identity_check_reads_the_declared_bound() -> None:
    """That the bound is right is worth nothing unless it is the one used.

    `test_the_closing_bound_cannot_hide_a_real_failure` proves the NUMBER is
    defensible. It cannot prove the identity assertion reads it: replacing
    `gap <= MEAN_IDENTITY_CLOSES` with `gap <= 1.0` leaves both of these tests
    passing, because nothing in this suite makes the identity fail and an
    inert assertion is invisible. A mutant demonstrated exactly that, so the
    call site is pinned here.
    """
    import ast

    tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    target = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name
        == "test_the_outer_cell_split_re_measures_the_numbers_that_fix_its_constants"
    )
    compared = [
        ast.unparse(compare.comparators[0])
        for node in ast.walk(target)
        if isinstance(node, ast.Assert)
        for compare in [node.test]
        if isinstance(compare, ast.Compare)
        and ast.unparse(compare.left) == "gap"
    ]
    assert compared == ["MEAN_IDENTITY_CLOSES"], (
        "the D3 mean identity is compared against "
        f"{compared} rather than the declared bound. A literal there is a "
        "bound nobody reviewed, and a wide one is an assertion that cannot "
        "fail."
    )


def test_the_outer_cell_split_re_measures_the_numbers_that_fix_its_constants(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`OUTER_CELL_PIECES` = 6 and `OUTER_CELL_RATIO` = 4, against a reference.

    **The defect this is arranged against.** `_split_outer_cells`' docstring
    was the only evidence for both constants and its four figures did not
    reproduce. It said that, on this fixture's points-by-rebounds joint at the
    20-minute node against a 400-node reference, the undivided second marginal
    is wrong by 7.2e-07 and the sum's mean by 8.9e-06, and that six pieces at
    ratio four make those 6.5e-10 and 7.4e-09. Re-measured they are 8.800e-07 /
    5.113e-05 and 1.886e-09 / 1.109e-07, and the figures never reproduced: the
    module AS IT STOOD at commit 0985942, the one that wrote them, was copied
    over the shipped file and driven through this same fixture — the component
    means came back 9.41767029946209 and 4.0588963589730103 and all four errors
    came back identical to today's, so no repair on this branch moved them.
    (`data/processed/cbb_player_shapes.json` is byte-identical across the
    branch and `models/player_rates.py` is identical once docstrings are
    stripped, so the fixture is the same fixture.) No node of the 45
    reproduces the quoted pair: node 21's
    undivided marginal is 6.939e-07 with a mean error of 4.281e-05, node 30's
    mean error is 8.377e-06 with a marginal of 8.545e-08. `grep` found the four
    strings only in that docstring, so nothing could go red on them. **The
    constants were right and the measurement was wrong**, which this test
    settles by measuring the curve both constants sit on rather than one point
    of it.

    Everything asserted here is a QUADRATURE ACCURACY measurement on a fixture
    joint. No probability below is a price, an edge or a result, and the last
    section exists to bound what the whole question is worth at price time:
    4.1e-07 on a win leg.

    Six claims, each of which the docstring now states and this test measures:

    1. **The error is one cell in twenty-nine.** Integrating each axis-0 cell
       with the shipped five-node rule and again with a 400-node one, the first
       cell — the only one that reaches `COPULA_LATENT_LIMIT` on the side where
       the lattice still has mass — is out by 8.788e-07, the worst of the 27
       interior cells by 1.126e-09 and the median interior cell by 3.14e-14.
       The last cell is out by 2.0e-17 even undivided. Split six ways at ratio
       four the first cell falls to 6.654e-10.
    2. **On the assembled joint, with the marginal fitting switched off**, the
       second marginal (points — `coupled_sum_pmf` sorts by support, so axis 0
       is rebounds and its weights sum to its own cell probabilities exactly,
       leaving it out by 5.5e-17 in every configuration) is out by 8.800e-07
       undivided and 1.886e-09 split, and the sum's mean by 5.113e-05 and
       1.109e-07.
    3. **The split is not what makes D3 hold.** With the shipped eight sweeps
       `|mu(sum) - sum(mu)|` is 0.0 on `player_points_rebounds` and 1.421e-14
       on `player_pra` WITH the split and WITHOUT it — the same two numbers. A
       reader of `_fit_marginals`' 5.1e-05 / 1.2e-07 / 1.4e-14 would infer the
       opposite, so it is asserted here.
    4. **What the split is for is the dependence**, which the sweeps cannot
       restore: against an 800-node reference the coupled sum pmf is out by
       7.256e-07 undivided and 1.289e-09 split, and the realised
       `points|rebounds` correlation misses the reference by 1.97e-05 undivided
       against 3.6e-08 split.
    5. **Both constants sit on a measured curve.** Pieces 1..10 at ratio 4 run
       7.256e-07 down to 8.156e-10, falling four-fold per piece to the fifth
       and flattening onto the floor the interior cells' own five-node rule
       leaves. The assertions are the SHAPE — six beats five, ten does not beat
       six by as much as a factor of two, one is hundreds of times the floor —
       and NOT that six is uniquely best, because it is not: seven reads
       9.181e-10. Ratio at six pieces is a U with 4 and 5 at the bottom
       (1.289e-09 and 1.174e-09) and 3 and 8 up at 3.022e-09 and 3.403e-09.
    6. **The docstring still quotes every figure measured here.** A negative
       tripwire was refused: banning the superseded strings would go red on the
       paragraph that records them as superseded, which is exactly the
       confusion this repair exists to prevent. The check is positive — each
       measured figure must appear in `_split_outer_cells.__doc__` — so
       re-measuring without editing the prose, or editing the prose without
       re-measuring, both go red.
    """
    engine = _distribution()
    node = int(np.flatnonzero(engine.minutes == 20.0)[0])
    assert float(engine.minutes[node]) == 20.0

    points = engine.node_component_pmf("points", node)
    rebounds = engine.node_component_pmf("rebounds", node)
    matrix = engine._correlation_matrix(("points", "rebounds"))
    exact_mean = _moments(points)[0] + _moments(rebounds)[0]
    assert rebounds.size < points.size, (
        "the docstring names axis 0 as rebounds and axis 1 as points because "
        "`coupled_sum_pmf` sorts by support; if that ordering changes, every "
        "figure below is about the other marginal"
    )

    fit_marginals = PD._fit_marginals
    seen: dict = {}

    def _capture(joint, marginals):
        seen["joint"] = np.array(joint, copy=True)
        seen["targets"] = [np.array(target, copy=True) for target in marginals]
        return fit_marginals(joint, marginals)

    monkeypatch.setattr(PD, "_fit_marginals", _capture)

    def _couple(pieces, *, ratio=4.0, sweeps=8, nodes=5, pair=None):
        monkeypatch.setattr(PD, "OUTER_CELL_PIECES", int(pieces))
        monkeypatch.setattr(PD, "OUTER_CELL_RATIO", float(ratio))
        monkeypatch.setattr(PD, "MARGINAL_SWEEPS", int(sweeps))
        monkeypatch.setattr(PD, "COPULA_NODES_PER_CELL", int(nodes))
        lattices = pair or [points, rebounds]
        return PD.coupled_sum_pmf(lattices, matrix)

    def _marginal_errors():
        joint, targets = seen["joint"], seen["targets"]
        out = []
        for axis in range(joint.ndim):
            others = tuple(index for index in range(joint.ndim) if index != axis)
            out.append(float(np.abs(joint.sum(axis=others) - targets[axis]).max()))
        return out

    # -- claim 1: the error lives in one cell ------------------------------
    cells = PD._latent_cells(rebounds)
    cuts = PD._latent_cells(points)[2]
    rho = float(matrix[0, 1])
    spread = math.sqrt(1.0 - rho * rho)

    def _cell(lower: float, upper: float, nodes: int) -> np.ndarray:
        grid, weight = PD._cell_nodes(
            np.array([lower]), np.array([upper]), nodes
        )
        latent = PD._latent(grid)
        conditional = np.diff(
            PD.ndtr((cuts - rho * latent[..., None]) / spread), axis=-1
        )
        return np.einsum("cq,cqv->cv", weight, conditional)[0]

    edges = cells[1]
    per_cell = np.array(
        [
            float(np.abs(_cell(edges[k], edges[k + 1], 5)
                         - _cell(edges[k], edges[k + 1], 400)).max())
            for k in range(edges.size - 1)
        ]
    )
    assert per_cell.size == 29
    assert per_cell[0] == pytest.approx(8.788e-07, rel=1e-3), (
        f"the first axis-0 cell's five-node error is now {per_cell[0]:.4e}; the "
        "docstring quotes 8.788e-07 and must be re-measured"
    )
    interior = per_cell[1:-1]
    assert interior.max() == pytest.approx(1.126e-09, rel=1e-3)
    assert float(np.median(interior)) == pytest.approx(3.14e-14, rel=1e-2)
    assert per_cell[-1] == pytest.approx(2.0e-17, rel=0.05), (
        "the LAST outer cell reaches the truncation too and is nonetheless "
        "harmless, because the lattice has spent its mass there. If this grew, "
        "the docstring's account of WHY the split is aimed at the first cell "
        "is wrong even though the split itself still works."
    )
    assert per_cell[0] > 700 * interior.max(), (
        "the whole argument for splitting only the outer cells is that they "
        "carry the error; at this ratio they no longer do"
    )
    fractions = PD._outer_fractions(6, 4.0)
    sliver = edges[0] + (edges[1] - edges[0]) * fractions
    split_first = sum(
        _cell(sliver[k], sliver[k + 1], 5) for k in range(6)
    )
    assert float(np.abs(split_first - _cell(edges[0], edges[1], 400)).max()) == (
        pytest.approx(6.654e-10, rel=1e-3)
    )

    # -- claim 2: the assembled joint, quadrature standing alone -----------
    _couple(1, sweeps=0)
    undivided = _marginal_errors()
    undivided_mean = abs(_moments(_couple(1, sweeps=0))[0] - exact_mean)
    _couple(6, sweeps=0)
    split = _marginal_errors()
    split_mean = abs(_moments(_couple(6, sweeps=0))[0] - exact_mean)

    assert PD._outer_fractions(1, 4.0).tolist() == [0.0, 1.0], (
        "`OUTER_CELL_PIECES = 1` is the undivided control only because "
        "`_outer_fractions` makes it an exact identity"
    )
    assert undivided[1] == pytest.approx(8.800e-07, rel=1e-3)
    assert undivided_mean == pytest.approx(5.113e-05, rel=1e-3)
    assert split[1] == pytest.approx(1.886e-09, rel=1e-3)
    assert split_mean == pytest.approx(1.109e-07, rel=1e-3)
    for errors in (undivided, split):
        assert errors[0] == pytest.approx(5.5e-17, rel=0.02), (
            "axis 0's marginal is exact by construction — its cell weights sum "
            "to its own cell probabilities — so a moved number here means the "
            "quadrature is no longer taken in probability space"
        )

    # -- claim 4: the dependence, against a converged reference ------------
    reference = _couple(6, nodes=800)
    assert float(np.abs(_couple(6, nodes=400) - reference).max()) == pytest.approx(
        9.97e-14, rel=0.05
    ), "the 800-node reference is only a reference if it has converged"

    def _against_reference(pieces, *, ratio=4.0):
        produced = _couple(pieces, ratio=ratio)
        return float(np.abs(produced - reference).max())

    assert _against_reference(1) == pytest.approx(7.256e-07, rel=1e-3)
    assert _against_reference(6) == pytest.approx(1.289e-09, rel=1e-3)

    def _realised(pieces, *, nodes=5):
        produced = _couple(pieces, nodes=nodes)
        variances = [_moments(points)[1], _moments(rebounds)[1]]
        covariance = (_moments(produced)[1] - variances[0] - variances[1]) / 2.0
        return covariance / math.sqrt(variances[0] * variances[1])

    # **`abs=1e-15` on a value of 0.102 is BIT precision, and this arithmetic
    # is not bit-identical across machines.** These three literals were
    # measured on arm64/Clang; CI runs x86-64/GCC and produced
    # 0.10209676623064635 against the first, off by 3.1e-15 — a quadrature over
    # 800 nodes accumulating rounding in a different order, which is the same
    # platform difference that made `why_the_model.rederivation_differences`
    # call an honest re-render a fabrication earlier today.
    #
    # The tolerance is 1e-12: three orders looser than the disagreement
    # measured, and still eight orders tighter than the 1.97e-05 and 3.6e-08
    # SHAPE claims below, which are what this test is actually about — that six
    # pieces beat one, and by how much. A correlation this far out has no
    # effect on any price; the copula's own realised-versus-asked check runs at
    # 4% relative.
    reference_correlation = _realised(6, nodes=800)
    assert reference_correlation == pytest.approx(0.10209676623064948, abs=1e-12)
    assert _realised(1) == pytest.approx(0.10207704656857115, abs=1e-12)
    assert _realised(6) == pytest.approx(0.10209673007926263, abs=1e-12)
    assert abs(_realised(1) - reference_correlation) == pytest.approx(1.97e-05, rel=1e-2)
    assert abs(_realised(6) - reference_correlation) == pytest.approx(3.6e-08, rel=2e-2)

    # -- claim 5: the curve both constants sit on --------------------------
    quoted_pieces = [
        7.256e-07, 1.793e-07, 4.460e-08, 1.115e-08, 2.974e-09,
        1.289e-09, 9.181e-10, 8.386e-10, 8.200e-10, 8.156e-10,
    ]
    curve = [_against_reference(pieces) for pieces in range(1, 11)]
    for pieces, (produced, quoted) in enumerate(zip(curve, quoted_pieces), start=1):
        assert produced == pytest.approx(quoted, rel=1e-3), (
            f"pieces={pieces}: {produced:.4e} against the docstring's {quoted:.4e}"
        )
    floor = curve[-1]
    assert curve[5] < curve[4], "six must beat five or the constant is not a choice"
    assert curve[5] < 2.0 * floor, (
        "six is supposed to be within a small multiple of the floor more outer "
        "pieces cannot go below"
    )
    assert curve[0] > 500.0 * floor, (
        "undivided is supposed to be hundreds of times the floor; if it is not, "
        "this function is buying nothing and the constants are decoration"
    )
    assert curve[6] < curve[5], (
        "seven is measurably better than six. The docstring says so rather than "
        "claiming six is optimal, and this assertion is what stops the claim "
        "from being made later."
    )

    quoted_ratios = {
        1.5: 9.411e-08, 2.0: 2.221e-08, 3.0: 3.022e-09, 4.0: 1.289e-09,
        5.0: 1.174e-09, 6.0: 1.545e-09, 8.0: 3.403e-09, 16.0: 2.291e-08,
    }
    for ratio, quoted in quoted_ratios.items():
        produced = _against_reference(6, ratio=ratio)
        assert produced == pytest.approx(quoted, rel=1e-3), (
            f"ratio={ratio}: {produced:.4e} against the docstring's {quoted:.4e}"
        )
    assert quoted_ratios[4.0] < quoted_ratios[3.0]
    assert quoted_ratios[4.0] < quoted_ratios[8.0]

    # -- claim 3, and what the whole question is worth at price time -------
    monkeypatch.setattr(PD, "_fit_marginals", fit_marginals)
    priced = {}
    for label, pieces in (("undivided", 1), ("shipped", 6)):
        monkeypatch.setattr(PD, "OUTER_CELL_PIECES", pieces)
        monkeypatch.setattr(PD, "OUTER_CELL_RATIO", 4.0)
        monkeypatch.setattr(PD, "MARGINAL_SWEEPS", 8)
        monkeypatch.setattr(PD, "COPULA_NODES_PER_CELL", 5)
        engine._cache.clear()
        priced[label] = {
            market: engine.count_pmf(market)
            for market in ("player_points_rebounds", "player_pra")
        }
        for market, components in (
            ("player_points_rebounds", ("points", "rebounds")),
            ("player_pra", ("points", "rebounds", "assists")),
        ):
            parts = sum(engine.mean(f"player_{stat}") for stat in components)
            gap = abs(engine.mean(market) - parts)
            assert gap <= MEAN_IDENTITY_CLOSES, (
                f"{label}/{market}: the D3 mean identity is out by {gap:.4e}, "
                f"above the {MEAN_IDENTITY_CLOSES:.1e} that counts as closed. "
                "The docstring's claim is that `_fit_marginals` closes it with "
                "the split and without it alike."
            )
    engine._cache.clear()

    for market, quoted in (
        ("player_points_rebounds", 1.291e-06),
        ("player_pra", 7.550e-07),
    ):
        first, second = priced["undivided"][market], priced["shipped"][market]
        assert first.size == second.size
        assert float(np.abs(first - second).max()) == pytest.approx(quoted, rel=1e-3)

    legs = {
        label: PD.price_line(priced[label]["player_points_rebounds"], 19.5, PD.OVER)
        for label in ("undivided", "shipped")
    }
    assert legs["undivided"][0] == pytest.approx(0.44609676189196446, abs=1e-15)
    assert legs["shipped"][0] == pytest.approx(0.4460971685625639, abs=1e-15)
    assert abs(legs["undivided"][0] - legs["shipped"][0]) < 1e-06, (
        "the accuracy question this function settles is worth well under a "
        "millionth of a win leg; a number here that had grown would mean the "
        "docstring's last paragraph is stale and the constant is doing "
        "something else"
    )

    # -- claim 6: the prose and the measurement cannot drift apart ---------
    # PHRASES, not bare figures, and whitespace-normalised so the wrapping is
    # not part of the contract. A bare-figure scan was tried first and a
    # mutation walked through it: putting `7.2e-07` back as the live
    # measurement left the test green, because `8.800e-07` was still present a
    # paragraph later in the sentence that records it as the correction. Every
    # figure below is pinned inside the sentence that asserts it.
    doc = " ".join((PD._split_outer_cells.__doc__ or "").split())
    for phrase in (
        "the FIRST cell is out by 8.788e-07 at its worst count, the worst of "
        "the 27 interior cells by 1.126e-09, and the median interior cell by "
        "3.14e-14",
        "The LAST cell is out by 2.0e-17 undivided",
        "the first cell's error falls to 6.654e-10",
        "the second marginal is wrong by 8.800e-07 at its worst rung and the "
        "sum's mean by 5.113e-05; at 6 pieces and ratio 4, by 1.886e-09 and "
        "1.109e-07",
        "that marginal is out by 5.5e-17 in every configuration below",
        "is 0.0 on `player_points_rebounds` and 1.421e-14 on `player_pra`",
        "400 and 800 nodes agree to 9.97e-14",
        "out by 7.256e-07 at its worst rung undivided and 1.289e-09 split",
        "reads 0.10207704656857115 undivided against the reference's "
        "0.10209676623064948",
        "a miss of 1.97e-05, where the split misses by 3.6e-08",
        "7.256e-07, 1.793e-07, 4.460e-08, 1.115e-08, 2.974e-09, 1.289e-09, "
        "9.181e-10, 8.386e-10, 8.200e-10, 8.156e-10 for 1 through 10",
        "9.411e-08, 2.221e-08, 3.022e-09, 1.289e-09, 1.174e-09, 1.545e-09, "
        "3.403e-09, 2.291e-08 at 1.5, 2, 3, 4, 5, 6, 8 and 16",
        "at most 1.291e-06 on `player_points_rebounds` and 7.550e-07 on "
        "`player_pra`",
        "moves from 0.44609676189196446 to 0.4460971685625639",
        "node 21's undivided marginal reads 6.939e-07 but its mean error "
        "4.281e-05, and node 30's mean error reads 8.377e-06 but its marginal "
        "8.545e-08",
        "The measurement does not single out six over seven",
    ):
        assert phrase in doc, (
            "`_split_outer_cells`' docstring no longer says "
            f"{phrase!r}, which this test measures. That docstring is the only "
            "place the two constants are justified and it has been wrong once "
            "already."
        )

    # The two nodes that show the superseded pair belongs to no node at all.
    # The capture wrapper was handed back before the priced section above, so
    # it goes on again here; without it `_marginal_errors` silently reports the
    # last joint anything captured, which is a green test reading a stale array.
    monkeypatch.setattr(PD, "_fit_marginals", _capture)
    for other, marginal, mean_error in (
        (20, 6.939e-07, 4.281e-05),
        (29, 8.545e-08, 8.377e-06),
    ):
        pair = [
            engine.node_component_pmf("points", other),
            engine.node_component_pmf("rebounds", other),
        ]
        total = _couple(1, sweeps=0, pair=pair)
        assert _marginal_errors()[1] == pytest.approx(marginal, rel=1e-3)
        produced = abs(
            _moments(total)[0]
            - sum(_moments(lattice)[0] for lattice in pair)
        )
        assert produced == pytest.approx(mean_error, rel=1e-3), (
            f"minutes node {other + 1}: the docstring cites this node to show "
            "the superseded pair reproduces at NO node, and the citation is "
            "now stale"
        )


def _declared_comment(name: str) -> str:
    """The `#:` block immediately above a module-level constant, as one line.

    A `#:` block is a comment, not a docstring, so nothing can read it at run
    time: the figures that justify `MARGINAL_SWEEPS` are invisible to
    `__doc__`, which is half of why they sat unreproduced. This lifts them out
    of the source so a test can assert the constant's OWN paragraph still
    quotes what was measured, rather than that the number appears somewhere in
    a 4,000-line module.
    """
    lines = MODULE.read_text(encoding="utf-8").splitlines()
    index = next(i for i, line in enumerate(lines) if line.startswith(f"{name}:"))
    block: list[str] = []
    while index > 0 and lines[index - 1].lstrip().startswith("#:"):
        index -= 1
        block.append(lines[index].lstrip()[2:])
    assert block, f"{name} carries no `#:` block at all"
    return " ".join(" ".join(reversed(block)).split())


#: Below this, `_worst` is the last bits of a quadrature rather than a
#: residual: this test asserts the modal curve reaches 1e-16 by sweep
#: five, and a ratio taken across that floor differs by platform --
#: measured 83.67 on CI (x86-64/GCC) against 88.65 here (arm64/Clang), a
#: 5.6% gap on quantities the test itself calls exhausted. Ten times the
#: floor, so a ratio is quoted only while both of its terms are real.
_CONTRACTION_FLOOR = 1e-15


def test_the_marginal_sweep_count_re_measures_the_curve_it_sits_on(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`MARGINAL_SWEEPS` = 8, against the curve rather than one point of it.

    **The defect this is arranged against.** The `#:` block on the constant was
    its only evidence and its three figures did not reproduce. It said that on
    this fixture's points-by-rebounds joint at its modal node the worst
    marginal error is "3.8e-11 at zero sweeps, 1.7e-14 at two and 2.8e-17 at
    four, and does not improve after that. Eight is twice what the measurement
    needs." Re-measured on exactly that object, in the shipped configuration,
    it is 8.3624e-10, 1.9158e-12 and 2.3592e-16 -- out by 22x, 113x and 8.4x --
    and it DOES improve after four, by a further 8.5x to the floor at five.
    Nothing on this branch moved them: the whole tree at commit 0985942, the
    commit that wrote the three figures, was exported with `git archive` and
    driven through its own copy of this fixture, and returns that column bit
    for bit (`data/processed/cbb_player_shapes.json` is byte-identical between
    that commit and this one, so it is the same fixture). No node of the 45
    carries the quoted triple in any reading -- split, undivided, relative, or
    on the `pra` joint -- and `grep` found the three strings only in that one
    comment, so nothing could go red on them. **The constant was right and the
    measurement was wrong**, which this test settles by measuring the curve the
    constant sits on instead of one point of it.

    Everything below is a QUADRATURE ACCURACY measurement on fixture joints and
    on the frozen file's own role priors. No probability here is a price, an
    edge or a result, and the one price-time reading exists to bound what the
    whole question is worth: nothing any rung can see.

    Eight claims, each of which the constant's comment now states and this
    test measures:

    1. **The object the old comment named**, re-measured. The fixture's
       points-by-rebounds joint at its modal node (index 31, 32.0 minutes),
       worst absolute marginal error over both axes of the FITTED joint, runs
       8.3624e-10, 1.7447e-10, 1.9158e-12, 2.0914e-14, 2.3592e-16 and then the
       double-precision floor at five sweeps -- 2.7756e-17 measured here, which
       is asserted as a bound rather than a value because it is a multiple of
       machine epsilon and not a residual. Past the floor it random-walks in
       the last bits rather than falling -- 5 through 24 sweeps all sit there
       -- so the constant is bounded above as well as below.
    2. **The shortcut clause 4 needs is exact.** The joint handed to
       `_fit_marginals` is the quadrature's output and does not depend on
       `MARGINAL_SWEEPS`, so a captured joint refitted at `s` sweeps and a
       whole `coupled_sum_pmf` re-run at `s` sweeps are the same array. That is
       asserted, not assumed: without it clause 4 measures 1,748 joints it
       never checked belong to the engine.
    3. **The rate is a frozen constant, not a property of the fixture.**
       Iterative proportional fitting on a two-way table contracts by the
       square of the correlation per sweep. Measured at the modal node against
       `1/rho^2` off the engine's own matrix: `points|rebounds` 91.07, 91.60
       and 88.65 against 90.30; `rebounds|assists` 310.84 and 313.00 against
       295.47; `points|assists` 3752.52 against 3620.81.
    4. **The curve the constant actually sits on.** Worst over the fixture
       athlete and the frozen file's own nine role-prior athletes, every
       minutes node each of them carries (437 of them) and all four couplings
       the engine builds -- 1,748 joints -- the column is 4.2419e-06,
       4.5909e-08, 4.6486e-10, 2.4287e-12, 4.1189e-14 and then the floor.
       Five is where it lands; four is 34x above it; eight is 1.6x five and
       NOT "twice what the measurement needs". The starting error is the only
       thing that varies with the athlete and it varies 37x -- 1.1443e-07 on
       the fixture's own worst node against 4.2419e-06 on the 6.73-minute role
       prior -- which is the quantity the reserve is sized against.
    5. **What the measurement does not settle, and the reserve it buys.**
       Eight is enough because the frozen correlations are small: with the
       matrix replaced by a synthetic one, eight sweeps leave the worst
       marginal at 2.083e-13 at `rho` = 0.5, 4.090e-11 at 0.7 and 1.970e-09 at
       0.9 -- the last of which alone would miss D3's 1e-9. The largest
       correlation this engine couples is `points|rebounds` =
       0.10523131793586692, and that is asserted, so a refit that raises it
       goes red here.
    6. **Three spare sweeps move no priced number.** Between five sweeps and
       eight, no rung of any of the four coupled markets moves by more than
       2.776e-17, mixed over the whole minutes lattice. So the reserve is free
       in output as well as nearly free in time.
    7. **The constant IS the sweep count**, read off the AST. This is the one
       claim no output can carry: five sweeps and eight produce identical
       rungs, so a `_fit_marginals` that capped its loop would satisfy every
       measurement above while spending the reserve the comment argues for.
    8. **The constant's own comment still quotes every figure measured here.**
       A negative tripwire was refused for the same reason the outer-cell test
       refuses one: banning the superseded strings would go red on the
       paragraph that records them as superseded. The check is positive, and
       it reads the `#:` block above the constant rather than the module, so a
       figure that migrated elsewhere does not satisfy it.
    """
    # Read BEFORE anything is monkeypatched. Claim 6 sets `MARGINAL_SWEEPS`
    # itself, so an assertion at the end of this test reads the patched value
    # and passes on any shipped constant at all -- which is the shape of
    # green-test defect this file has written down twice.
    shipped = PD.MARGINAL_SWEEPS
    engine = _distribution()
    node = engine.price_node()
    assert node == 31 and float(engine.minutes[node]) == 32.0, (
        "the comment names the modal node of this fixture's minutes lattice; "
        f"it is now {node} at {float(engine.minutes[node])} minutes and every "
        "figure below is about a different object"
    )

    fit_marginals = PD._fit_marginals
    seen: dict = {}

    def _capture(joint, marginals):
        seen["joint"] = np.array(joint, copy=True)
        seen["targets"] = [np.array(target, copy=True) for target in marginals]
        return fit_marginals(joint, marginals)

    def _worst(joint: np.ndarray, targets) -> float:
        """The worst absolute marginal error of one joint, over every axis."""
        return max(
            float(
                np.abs(
                    joint.sum(axis=tuple(i for i in range(joint.ndim) if i != axis))
                    - targets[axis]
                ).max()
            )
            for axis in range(joint.ndim)
        )

    def _quadrature(distribution, components, index, correlation=None):
        """The joint and its targets, straight out of `coupled_sum_pmf`.

        Captured at zero sweeps only to skip work the capture discards; the
        joint `_fit_marginals` is HANDED is the quadrature's output either way,
        which is claim 2.
        """
        monkeypatch.setattr(PD, "MARGINAL_SWEEPS", 0)
        monkeypatch.setattr(PD, "_fit_marginals", _capture)
        matrix = (
            distribution._correlation_matrix(components)
            if correlation is None
            else correlation
        )
        PD.coupled_sum_pmf(
            [distribution.node_component_pmf(stat, index) for stat in components],
            matrix,
        )
        monkeypatch.setattr(PD, "_fit_marginals", fit_marginals)
        return seen["joint"], seen["targets"]

    def _curve(joint, targets, sweeps) -> list[float]:
        out = []
        for count in sweeps:
            monkeypatch.setattr(PD, "MARGINAL_SWEEPS", int(count))
            out.append(_worst(fit_marginals(joint, targets), targets))
        return out

    # -- claim 1: the object the old comment named -------------------------
    pair = ("points", "rebounds")
    joint, targets = _quadrature(engine, pair, node)
    modal = _curve(joint, targets, range(0, 6))
    for sweeps, expected in enumerate(
        (8.3624e-10, 1.7447e-10, 1.9158e-12, 2.0914e-14, 2.3592e-16)
    ):
        assert modal[sweeps] == pytest.approx(expected, rel=1e-3), (
            f"at {sweeps} sweeps the fixture's points-by-rebounds joint at its "
            f"modal node is out by {modal[sweeps]:.4e}; the constant's comment "
            f"quotes {expected:.4e} and must be re-measured"
        )
    assert modal[5] <= 1e-16, (
        f"five sweeps now leave {modal[5]:.4e}; the comment says five reaches "
        "the double-precision floor (2.7756e-17 when measured) and the whole "
        "argument for eight is that it is 1.6x that"
    )
    assert modal[4] / modal[5] >= 4.0, (
        "the superseded comment said the error 'does not improve after' four "
        f"sweeps. It falls a further {modal[4] / modal[5]:.1f}x (8.5x when "
        "measured), which is the sentence this test exists to keep false"
    )
    # And it is bounded above: past the floor the last bits random-walk rather
    # than fall, which is why the comment says raising the constant buys
    # nothing either.
    tail = _curve(joint, targets, range(5, 25))
    assert max(tail) <= 1e-16, (
        f"sweeps 5 through 24 now reach {max(tail):.4e}; the comment says they "
        "sit on the floor (2.776e-17 with occasional 4.163e-17 and 5.551e-17) "
        "and that more sweeps therefore buy nothing"
    )

    # -- claim 2: the captured joint is the joint --------------------------
    for sweeps in (3, 8):
        monkeypatch.setattr(PD, "MARGINAL_SWEEPS", int(sweeps))
        monkeypatch.setattr(PD, "_fit_marginals", _capture)
        PD.coupled_sum_pmf(
            [engine.node_component_pmf(stat, node) for stat in pair],
            engine._correlation_matrix(pair),
        )
        monkeypatch.setattr(PD, "_fit_marginals", fit_marginals)
        assert np.array_equal(seen["joint"], joint), (
            "the joint handed to `_fit_marginals` moved with `MARGINAL_SWEEPS`, "
            "so the captured-once measurement below is measuring joints the "
            "engine would not have built"
        )

    # -- claim 3: the contraction is one over the squared correlation ------
    for components, quoted in (
        (("points", "rebounds"), (91.07, 91.60, 88.65)),
        (("rebounds", "assists"), (310.84, 313.00)),
        (("points", "assists"), (3752.52,)),
    ):
        matrix = engine._correlation_matrix(components)
        rho = float(matrix[0, 1])
        row = _curve(*_quadrature(engine, components, node), range(0, 5))
        # The first sweep fits one axis only, so the geometric rate starts at
        # the second; that is why the comment quotes ratios and not a rate.
        measured = [row[i + 1] / row[i + 2] for i in range(len(quoted))]
        for i, (got, expect) in enumerate(zip(measured, quoted)):
            # **A ratio whose denominator has reached the noise floor is not a
            # contraction rate.** `_worst` is the residual marginal error, and
            # this test asserts a few lines above that it is <= 1e-16 by the
            # fifth sweep. Dividing by a number at 1e-16 measures the last bits
            # of a quadrature, not the geometry — and those bits differ by
            # platform. Measured: CI (x86-64/GCC) reports 83.67 for the
            # points|rebounds third ratio where this machine (arm64/Clang)
            # reports 88.65, a 5.6% gap on quantities the test itself calls
            # exhausted.
            #
            # So the quoted value is asserted only while the denominator is
            # above the floor, and the floor is asserted where it is not. Both
            # branches assert; neither is a skip.
            if row[i + 2] > _CONTRACTION_FLOOR:
                assert got == pytest.approx(expect, rel=5e-3), (
                    f"{'|'.join(components)} now contracts {got:.2f} per sweep; "
                    f"the comment quotes {expect:.2f}"
                )
            else:
                assert row[i + 2] <= _CONTRACTION_FLOOR, (
                    f"{'|'.join(components)} sweep {i + 2} sits at "
                    f"{row[i + 2]:.3e}, which is neither above the floor nor at "
                    "it, so this branch is asserting nothing"
                )
            assert got == pytest.approx(1.0 / (rho * rho), rel=0.1), (
                f"{'|'.join(components)} contracts {got:.2f} per sweep against "
                f"1/rho^2 = {1.0 / (rho * rho):.2f}. The comment's whole reason "
                "for a reserve is that the RATE is frozen and only the starting "
                "error varies with the athlete"
            )

    # -- claim 4: the curve, over the file's own population ----------------
    shapes = _shapes()
    population = [engine] + [
        _role_prior_athlete(shapes, bucket) for bucket in range(9)
    ]
    couplings = [
        ("points", "rebounds", "assists"),
        ("points", "rebounds"),
        ("points", "assists"),
        ("rebounds", "assists"),
    ]
    assert sum(athlete.minutes.size for athlete in population) == 437, (
        "the comment counts 437 minutes nodes across these ten athletes; the "
        "population has changed and the joint count with it"
    )
    joints = []
    fixtures_own = 0
    for athlete in population:
        for components in couplings:
            for index in range(athlete.minutes.size):
                joints.append(_quadrature(athlete, components, index))
                fixtures_own += int(athlete is engine)
    assert len(joints) == 1748, (
        f"the comment quotes 1,748 joints and this population builds "
        f"{len(joints)}"
    )
    worst_at = []
    for sweeps in range(0, 9):
        monkeypatch.setattr(PD, "MARGINAL_SWEEPS", int(sweeps))
        worst_at.append(
            max(_worst(fit_marginals(one, target), target) for one, target in joints)
        )
    # The starting error is the ONE quantity that varies with the athlete, and
    # the comment's argument for a reserve is built on how much it varies.
    monkeypatch.setattr(PD, "MARGINAL_SWEEPS", 0)
    fixture_start = max(
        _worst(fit_marginals(one, target), target)
        for one, target in joints[:fixtures_own]
    )
    assert fixture_start == pytest.approx(1.1443e-07, rel=1e-3), (
        f"the fixture athlete's own worst starting error is now "
        f"{fixture_start:.4e}; the comment quotes 1.1443e-07 as the bottom of "
        "the 37x spread the reserve is sized against"
    )
    assert worst_at[0] / fixture_start == pytest.approx(37.0, abs=1.0), (
        "the starting error's spread across the ten athletes has moved off the "
        f"37x the comment quotes: it is now "
        f"{worst_at[0] / fixture_start:.1f}x"
    )
    for sweeps, expected in enumerate(
        (4.2419e-06, 4.5909e-08, 4.6486e-10, 2.4287e-12, 4.1189e-14)
    ):
        assert worst_at[sweeps] == pytest.approx(expected, rel=1e-3), (
            f"the worst of the 1,748 joints at {sweeps} sweeps is now "
            f"{worst_at[sweeps]:.4e}; the comment quotes {expected:.4e}"
        )
    assert worst_at[4] >= 1e-14, (
        "four sweeps now reach the floor on every one of the 1,748 joints, so "
        "the comment's 'four is not enough' has stopped being true"
    )
    for sweeps in (5, 6, 7, 8):
        assert worst_at[sweeps] <= 5e-15, (
            f"{sweeps} sweeps leave {worst_at[sweeps]:.4e}, above the "
            "double-precision floor the comment says five reaches"
        )
    assert worst_at[4] / worst_at[5] >= 10.0

    # -- claim 5: what the reserve is for ---------------------------------
    largest = max(
        abs(float(engine._correlation_matrix(components)[i, j]))
        for components in couplings
        if len(components) == 2
        for i in range(2)
        for j in range(i + 1, 2)
    )
    assert largest == float(
        shapes.value("residual_correlation")["points|rebounds"]
    ) == 0.10523131793586692, (
        "the largest correlation this engine couples has moved. Eight sweeps "
        "are enough BECAUSE it is small -- the contraction is 1/rho^2 -- so "
        "`MARGINAL_SWEEPS` has to be re-measured against the new one"
    )
    # A synthetic matrix, never a fitted one: this is a numerical probe of what
    # the sweep count would cost at a correlation nothing in the tree produces,
    # and no price is taken from it.
    at_three_tenths = _curve(
        *_quadrature(
            engine, pair, node, np.array([[1.0, 0.3], [0.3, 1.0]])
        ),
        [8],
    )[0]
    assert at_three_tenths <= 1e-15, (
        f"eight sweeps at rho = 0.3 now leave {at_three_tenths:.4e}; the "
        "comment quotes 8.327e-17, which is the floor, and the point of the "
        "row is that 0.3 is still covered and 0.5 is not"
    )
    for rho, expected in ((0.5, 2.083e-13), (0.7, 4.090e-11), (0.9, 1.970e-09)):
        synthetic = np.array([[1.0, rho], [rho, 1.0]])
        eight = _curve(*_quadrature(engine, pair, node, synthetic), [8])[0]
        assert eight == pytest.approx(expected, rel=1e-2), (
            f"at a correlation of {rho} eight sweeps now leave {eight:.4e}; the "
            f"comment quotes {expected:.4e} as what the constant does NOT cover"
        )
    assert eight > 1e-9, (
        "the comment says eight sweeps at rho = 0.9 alone would miss D3's 1e-9, "
        f"and it now leaves {eight:.4e}"
    )

    # -- claim 6: the reserve moves no priced number -----------------------
    coupled = (
        "player_points_rebounds",
        "player_points_assists",
        "player_rebounds_assists",
        "player_pra",
    )
    priced = {}
    for sweeps in (5, 8):
        monkeypatch.setattr(PD, "MARGINAL_SWEEPS", int(sweeps))
        built = _distribution()
        priced[sweeps] = {
            market: np.array(built.count_pmf(market)) for market in coupled
        }
    monkeypatch.setattr(PD, "MARGINAL_SWEEPS", shipped)
    for market in coupled:
        five, eight_rungs = priced[5][market], priced[8][market]
        assert five.shape == eight_rungs.shape
        moved = float(np.abs(five - eight_rungs).max())
        assert moved <= 1e-16, (
            f"{market} moves by {moved:.4e} between five sweeps and eight; the "
            "comment says the three spare sweeps move no rung by more than "
            "2.776e-17, which is why the reserve is free"
        )

    # -- claim 7: the constant IS the sweep count -------------------------
    # Structural, and it is the one claim above that no output can carry:
    # five sweeps and eight produce identical rungs, so a `_fit_marginals`
    # that quietly capped the loop would satisfy every measurement here while
    # spending the reserve the comment argues for. The loop's own bound is
    # read off the AST instead.
    tree = ast.parse(MODULE.read_text(encoding="utf-8"), filename=str(MODULE))
    fitter = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_fit_marginals"
    )
    bounds = [
        node.iter
        for node in ast.walk(fitter)
        if isinstance(node, ast.For)
        and isinstance(node.iter, ast.Call)
        and isinstance(node.iter.func, ast.Name)
        and node.iter.func.id == "range"
    ]
    assert len(bounds) == 1, (
        f"`_fit_marginals` now has {len(bounds)} counted loops; the sweep "
        "count is supposed to be the only one"
    )
    assert [ast.dump(argument) for argument in bounds[0].args] == [
        ast.dump(ast.Name(id="MARGINAL_SWEEPS", ctx=ast.Load()))
    ], (
        "the sweep loop no longer runs exactly `MARGINAL_SWEEPS` times: it is "
        f"bounded by `{ast.unparse(bounds[0])}`. Five sweeps and eight produce "
        "identical rungs, so a cap here is invisible to every other assertion "
        "in this test and would silently spend the reserve"
    )

    # -- claim 8: the comment still quotes every figure --------------------
    comment = _declared_comment("MARGINAL_SWEEPS")
    for figure in (
        "4.2419e-06",
        "4.5909e-08",
        "4.6486e-10",
        "2.4287e-12",
        "4.1189e-14",
        "9.9920e-16",
        "1.2212e-15",
        "8.3624e-10",
        "1.9158e-12",
        "2.3592e-16",
        "2.7756e-17",
        "91.07",
        "88.65",
        "310.84",
        "3752.52",
        "0.10523131793586692",
        "2.083e-13",
        "1.970e-09",
        "1.1443e-07",
        "437",
        "37x",
        "1,748",
    ):
        assert figure in comment, (
            f"{figure} is measured by this test and no longer appears in "
            "`MARGINAL_SWEEPS`' own comment. Re-measuring without editing the "
            "prose is how the last three figures came to be wrong"
        )
    assert shipped == 8, (
        f"`MARGINAL_SWEEPS` is now {shipped}. Every figure above is "
        "measured on the curve and not on the shipped value, so the curve does "
        "not move when the constant does -- what has to move with it is the "
        "comment's argument: five is the measured floor, eight is the reserve "
        "it keeps, and a new value needs its own sentence about which of those "
        "it is"
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


def test_the_minutes_lattice_length_is_derived_from_the_declared_block(
    tmp_path: Path,
) -> None:
    """The length the engine demands moves with the file, not with a literal.

    The engine carried `_MINUTES_LATTICE_LENGTH = 46`, a third copy of
    `declared.minutes_support` = [1, 45] — after the frozen file itself and
    after `player_rates.MINUTES_SUPPORT`, which is the only one of the three
    that was held against the file (`player_rates._assert_declared_agrees`, at
    price time). The scan above could not see it: it collects numbers under
    `document["constants"]` and the support lives under `document["declared"]`,
    and it drops whole numbers deliberately because a frozen 4 fingerprints
    nothing.

    Three things, each measured against a file rather than described:

    1. On the SHIPPED file the derived length is 46, so the repair changed no
       behaviour on any path that prices anything today.
    2. On a copy declaring [1, 48] it is 49, and `build` then refuses the
       shipped 46-long lattice **naming the file and the support it read** —
       which is the half the old message did not have. A refit that widened the
       support would have produced 49-long lattices, passed
       `_assert_declared_agrees`, and made every prop on every card decline with
       a message naming neither the file nor the constant that moved.
    3. A file whose `declared` block states no readable support REFUSES rather
       than falling back to 46. A default here would be the copy this deletes.
    """
    shipped = _shapes()
    assert PD._minutes_lattice_length(shipped) == 46
    assert len(_projection(shipped).minutes_pmf) == 46

    def _widen(payload: dict) -> None:
        payload["declared"]["minutes_support"] = [1, 48]

    widened = _shapes_with(tmp_path, _widen, name="wide.json")
    assert PD._minutes_lattice_length(widened) == 49
    with pytest.raises(PD.PlayerDistributionError) as raised:
        PD.build(_projection(shipped), shapes=widened)
    message = str(raised.value)
    assert "46 long" in message and "must be 49" in message, message
    assert "wide.json" in message and "[1, 48]" in message, (
        "the refusal names neither the frozen file nor the support it read, so "
        "a reader hitting it on every prop on every card cannot tell which of "
        "the three copies moved. That is the whole reason this length is "
        f"derived rather than typed. It read: {message}"
    )

    for index, broken in enumerate(([], [1], "1-45", None, [2, 45])):

        def _break(payload: dict, value=broken) -> None:
            payload["declared"]["minutes_support"] = value

        bad = _shapes_with(tmp_path, _break, name=f"broken{index}.json")
        with pytest.raises(PD.PlayerDistributionError):
            PD._minutes_lattice_length(bad)


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




#: The five markets that read the scoring-event count. `points` is the compound
#: sum over it and `threes` is the same count thinned, so every market carrying
#: either component needs it — and `points_events` is a component of none of
#: them, which is the whole reason its refusal went unnoticed.
COMPOUND_MARKETS = (
    "player_points",
    "player_threes",
    "player_pra",
    "player_points_rebounds",
    "player_points_assists",
)


def test_an_r5_refusal_of_the_scoring_event_count_refuses_instead_of_crashing(
    tmp_path: Path,
) -> None:
    """R5 on `points_events`, which is a stat no market names.

    **The defect, reproduced before it was repaired.** `player_rates._unfittable`
    reads `role_prior.<stat>` and `rate_shrinkage_k.<stat>` for all seven stats,
    `points_events` among them, and `_rates` DROPS a refused stat from
    `projection.rates`. The projection stays `priceable=True` — six rates are
    still there and six markets still have everything they need — so `build()`
    ran, and its market-refusal loop asked only about each market's own
    components. `points_events` is a component of none of the ten. So no market
    was refused, and two statements later `rates["points_events"]` was read
    unconditionally: `KeyError('points_events')`, on both keys, measured through
    the real loader.

    That is worse than a wrong price. `KeyError` is not a `ValueError`, so
    neither `except engine.PlayerDistributionError` nor `except (TypeError,
    ValueError)` in `reports/gameday_card.opinions_for` caught it: a refusal the
    fit made deliberately took down the whole card — every spread, total and
    moneyline on the slate, and a `player_rebounds` prop that has nothing to do
    with points. The contrast is `conditional_dispersion.points_events`, which
    took the constant route through `_refused_constants` and refused the same
    five markets correctly all along.

    Asserted here on all three keys: the two the estimator reads and the one it
    does not.
    """
    from cbb_betting_lab.reports import gameday_card as GC

    sentence = "refused: the scoring-event count did not stabilise."
    cost = "Every market that reads the scoring-event count is unpriced."
    priced_anyway = tuple(
        market for market in PR.MARKET_COMPONENTS if market not in COMPOUND_MARKETS
    )
    assert len(COMPOUND_MARKETS) == 5 and len(priced_anyway) == 5

    for key in (
        "role_prior.points_events",
        "rate_shrinkage_k.points_events",
        "conditional_dispersion.points_events",
    ):
        def _refuse(document: dict, key: str = key) -> None:
            document["unfittable"] = {key: {"reason": sentence, "cost": cost}}

        shapes = _shapes_with(tmp_path, _refuse, name=key.replace(".", "_") + ".json")
        projection = _projection(shapes)

        # The estimator's own shape, asserted rather than assumed: this is why
        # the read raised instead of returning a number.
        estimator_route = key.split(".")[0] in ("role_prior", "rate_shrinkage_k")
        assert ("points_events" in projection.refused_stats) is estimator_route
        assert ("points_events" not in projection.rates) is estimator_route
        assert projection.priceable is True, (
            "a refusal of one stat leaves the other six priceable, which is "
            "exactly why this reached the engine at all"
        )

        distribution = PD.build(projection, shapes=shapes)
        assert sorted(distribution.refusals) == sorted(COMPOUND_MARKETS), (
            f"{key}: the five markets that read the scoring-event count are "
            f"not the five refused. Refused: {sorted(distribution.refusals)}"
        )
        for market in COMPOUND_MARKETS:
            with pytest.raises(PD.MarketRefused, match="did not stabilise"):
                distribution.count_pmf(market)
            assert cost in distribution.refusals[market], (
                "the refusal must be the FILE's sentence, not a paraphrase "
                "written in the engine"
            )
        for market in priced_anyway:
            assert distribution.mean(market) > 0.0, (
                f"{market} needs no scoring-event count and must still price"
            )
        assert not distribution.event_parameters, (
            "no scoring-event family may be built at all when the count it "
            "would be built from was refused"
        )

        # And through the card, which is where the KeyError actually landed.
        model, _ = _slate_model(shapes=shapes)
        wagers = [
            _wager("player_points", line=14.5),
            _wager("player_rebounds", line=5.5),
        ]
        probabilities, census = GC.opinions_for(wagers, model, day=DAY)
        assert census.wagers == 2 and census.priced == 1, census.declined
        assert ("e1", "player_rebounds", "over", 5.5, "Sean Bairstow") in probabilities
        assert ("e1", "player_points", "over", 14.5, "Sean Bairstow") not in probabilities
        assert any(sentence in reason for reason in census.declined), sorted(
            census.declined
        )


def test_a_regular_whose_points_is_refused_is_counted_apart_not_pooled(
    tmp_path: Path,
) -> None:
    """The stop rule's population survives a refused subject, and says how many.

    `population_structural_checks` asks every regular for
    `count_pmf("player_points")`, and that raises `MarketRefused` for a subject
    whose points constant the fit would not stand behind. It is called by
    `gameday_card._run_the_structural_check` OUTSIDE every `except` the card
    owns — the call has to be outside, because the check is about the pooled
    population rather than about one wager — so before this commit one refused
    prop killed the card there instead of in `build()`. The bucket is reported
    rather than silently dropped: a population that shrank because a constant
    was refused reads exactly like a population that was small, and the second
    is a limitation while the first is a finding.
    """
    def _refuse_points(document: dict) -> None:
        document["unfittable"] = {
            "conditional_dispersion.points": {
                "reason": "refused: the points dispersion did not stabilise.",
                "cost": "Every market with a points component is unpriced.",
            }
        }

    shapes = _shapes()
    refused_shapes = _shapes_with(tmp_path, _refuse_points, name="no_points.json")
    # Eight regulars off the file's own role priors, at the floor exactly, and
    # a ninth who is a 36.22-minute starter — a regular by the target's own
    # `regular_min_projected_minutes` of 15.0, so he cannot be excused as
    # sub-floor and the only thing separating him from the eight is the
    # refusal. The eight pool to 0.9214, inside design 4's stop, so the run
    # this test describes is one that continues.
    healthy = [_role_prior_athlete(shapes, bucket) for bucket in (3, 4, 5, 6, 7, 8, 4, 7)]
    refused = _role_prior_athlete(refused_shapes, 8)
    assert "player_points" in refused.refusals
    assert float(refused.projection.projected_minutes) > 15.0

    checks = PD.population_structural_checks([*healthy, refused], shapes=shapes)
    assert checks["population_athletes_offered"] == 9.0
    assert checks["population_athletes"] == 8.0
    assert checks["population_points_refused"] == 1.0
    assert checks["population_below_regular_floor"] == 0.0
    assert (
        checks["population_athletes"]
        + checks["population_points_refused"]
        + checks["population_below_regular_floor"]
        == checks["population_athletes_offered"]
    ), "the three buckets must partition what was offered, or one is a silent drop"

    # The pooled number is the eight it could read, unchanged by the ninth.
    alone = PD.population_structural_checks(healthy, shapes=shapes)
    assert checks["unconditional_points_vmr_ratio"] == pytest.approx(
        alone["unconditional_points_vmr_ratio"], rel=1e-12
    )
    assert checks["unconditional_points_vmr_ratio"] == pytest.approx(0.9214, abs=1e-3)
    PD.assert_structural_checks(checks)  # at the floor, inside the stop, no raise
    # And the card prints the bucket rather than leaving the population short
    # with no explanation.
    from cbb_betting_lab.reports.gameday_card import OpinionCensus

    census = OpinionCensus(wagers=0)
    census.structural_check = dict(checks)
    assert "1 regular(s) whose `player_points` the fit refused" in (
        census.structural_check_line()
    )



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
            PD.panjer_parameters(mu=180.0, phi=1.1, materiality=_materiality()),
            severity=(0.0, 1.0),
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

    **Design 4's check (b) is asserted here, and so are the ARGUMENTS the
    engine hands it.** `structural_checks()` returns fourteen keys and five of
    them — `corr_points_threes_given_minutes`, its target,
    `points_vmr_given_minutes`, its target and `checked_at_minutes` — were read
    by no assertion in the suite, including the 2.4751-against-2.3289 sentence
    this docstring quotes. Stubbing the engine's one call to
    `points_threes_correlation` to pass `value_pmf=self.severity[0:3]` instead
    of `self.severity[1:4]` -- the severity array is `[0, p1, p2, p3]`, so the
    share becomes p2 and both moments are wrong: the correlation goes to
    0.8825 -- left the file green at 40 passed, measured against the file as it
    stood at the parent commit. (The other half of the same stub, hard-coding
    `points_vmr_given_minutes` to 0.0, is NOT green there: two tests written
    since this finding was raised, `test_design_4s_stop_rule_is_a_population_
    quantity` and `test_the_file_says_this_number_must_not_be_handed_to_a_
    panjer_family`, reach that key by another route and go red on it. The
    correlation half was caught by nothing at all.)
    `points_threes_correlation` itself is checked against an
    enumerated joint elsewhere; what is held below is which distribution the
    engine asks it about, rebuilt from parts that do not pass through
    `structural_checks` at all — the scoring-event mean as
    `rates["points_events"] * minutes[node]` = 7.611078, the dispersion out of
    the frozen file under `POINTS_EVENT_DISPERSION_KEY`, and the athlete's own
    1/2/3 mix off `projection.value_pmf`. The conditional VMR gets the same
    treatment against the compound identity `E[V^2]/E[V] + (phi-1)*E[V]`, which
    reproduces the engine's 2.4750752387725523 to 2.8e-10 without touching a
    pmf.
    """
    distribution = _distribution()
    checks = distribution.structural_checks()
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

    # -- check (b), and the distribution the engine asks it about -----------
    projection = distribution.projection
    node = distribution.price_node()
    assert checks["checked_at_minutes"] == float(distribution.minutes[node]), (
        "the reported node is not the node the columns were quoted at"
    )
    assert checks["checked_at_minutes"] == pytest.approx(32.0, abs=1e-12), (
        f"the modal minutes node moved to {checks['checked_at_minutes']}; every "
        "conditional number in this test is quoted at 32 minutes"
    )

    dispersion = float(
        shapes.value("points_compound_reconciliation")[PD.POINTS_EVENT_DISPERSION_KEY]
    )
    events = float(projection.rates["points_events"]) * checks["checked_at_minutes"]
    assert events == pytest.approx(7.611078044398606, abs=1e-9)
    assert PD.points_threes_correlation(
        mu_events=events, phi_events=dispersion, value_pmf=projection.value_pmf
    ) == pytest.approx(checks["corr_points_threes_given_minutes"], abs=1e-12), (
        "the engine's own call to `points_threes_correlation` does not "
        "reproduce from the athlete's scoring-event mean, the frozen event "
        "dispersion and his own value mix, so it is being asked about some "
        "other distribution than the one it prices"
    )
    assert checks["corr_points_threes_given_minutes"] == pytest.approx(
        0.746598, abs=1e-6
    ), (
        f"check (b) now produces {checks['corr_points_threes_given_minutes']}; "
        "this fixture's three-heavy mix measured 0.7466 and the docstring of "
        "`test_the_points_threes_correlation_identity_matches_a_brute_force_"
        "joint` quotes it"
    )
    assert checks["corr_points_threes_given_minutes_target"] == pytest.approx(
        0.6021705535430947, abs=1e-12
    )
    assert (
        checks["corr_points_threes_given_minutes"]
        > checks["corr_points_threes_given_minutes_target"]
    ), (
        "the thinning now produces a correlation at or below the frozen target. "
        "No tolerance is declared for this check anywhere, so it stops nothing "
        "and nothing may be tuned to close it — but the direction is part of "
        "what is reported and has moved."
    )

    mix = np.asarray(projection.value_pmf, dtype=float)
    values = np.array([1.0, 2.0, 3.0])
    expected_value = float(mix @ values)
    identity = float(mix @ (values * values)) / expected_value + (
        dispersion - 1.0
    ) * expected_value
    assert checks["points_vmr_given_minutes"] == pytest.approx(identity, abs=1e-8), (
        "the conditional points VMR the engine reports is not the compound "
        f"identity at this athlete's own mix ({identity}), so the number in the "
        "report is not the one the docstring's extrapolation argument is about"
    )
    assert checks["points_vmr_given_minutes"] == pytest.approx(2.475075, abs=1e-6)
    assert checks["points_vmr_given_minutes_target"] == pytest.approx(
        2.328891545818532, abs=1e-12
    )
    assert (
        checks["points_vmr_given_minutes"] > checks["points_vmr_given_minutes_target"]
    ), (
        "the fixture athlete's shrunk mix has E[V] = 1.980 against the league's "
        "1.857 and the compound identity is increasing in E[V], so his points "
        "marginal is wider at the same dispersion. That extrapolation is "
        "declared; if the direction has flipped, say why."
    )


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


def test_the_file_says_this_number_must_not_be_handed_to_a_panjer_family() -> None:
    """The frozen file's own prohibition, quoted, and the antecedent that answers it.

    `points_compound_reconciliation`'s note ends "It is not the event count's
    dispersion and must not be handed to a Panjer family as one", and
    `build` hands `effective_event_dispersion` to `panjer_parameters` as the
    scoring-event count's phi. Read with "It" bound to that constant, the file
    forbids what the engine does — and until this commit no docstring in the
    module quoted the sentence or answered it, so an auditor comparing the two
    found a flat contradiction with nothing to read.

    **The answer is an antecedent, not a preference, and it is measured here.**

    1. The subject is the design's published 1.11. The fitter that wrote both
       the value and the note says of it "The design's own published 1.11 is
       neither" — neither of the two frozen candidates — and the file's own
       evidence block says it "reproduces as `points_vmr_over_compound_poisson`,
       not as an event-count dispersion". That quantity is 1.0922583243981805
       and this engine reads it nowhere.
    2. `effective_event_dispersion` is not a measurement of anything; it is
       DEFINED by inverting the compound identity. Handing it back to a Panjer
       family reproduces the frozen `measured_points_vmr_given_minutes` of
       2.328891545818532 **bit-for-bit**, and handing over
       `measured_event_dispersion` reproduces the frozen
       `compound_implied_points_vmr` of 2.8377415929483303 bit-for-bit. A
       constant computed by inverting the identity cannot coherently be barred
       from the family it was inverted out of.
    3. The cost of the other reading is reported rather than hidden: obeying it
       literally produces a conditional points VMR of 2.8377 against the file's
       own measured 2.3289, and moves the population ratio from 0.9209 to
       1.0875 — see `test_the_dispersion_choice_is_not_decided_by_the_stop_rule`,
       which holds that both land inside design 4's stop, so nothing here is
       decided by a tolerance.

    **This test goes red the day the note is rewritten**, which is the only
    honest way to hold an answer to a sentence in a file this module does not
    own: the answer above would then be about a sentence that no longer exists
    and has to be re-read, not silently kept.
    """
    document = json.loads(SHAPES.read_text(encoding="utf-8"))
    constant = document["constants"]["points_compound_reconciliation"]
    note = constant["note"]
    values = constant["value"]
    evidence = constant["evidence"]["fit"]

    prohibition = (
        "It is not the event count's dispersion and must not be handed to a "
        "Panjer family as one."
    )
    reproduces = (
        "the design's 1.11 reproduces as `points_vmr_over_compound_poisson`, "
        "not as an event-count dispersion"
    )
    neither = "The design's own published 1.11 is neither"

    assert prohibition in note, (
        "the frozen file's note no longer carries the sentence "
        "`POINTS_EVENT_DISPERSION_KEY`'s docstring quotes and answers. Re-read "
        "the note and rewrite the answer with it."
    )
    assert reproduces in evidence["how_the_design_number_reads"]
    fitter = " ".join((REPO / "scripts" / "fit_player_model.py").read_text(
        encoding="utf-8"
    ).split())
    assert neither in fitter, (
        "the fitter's own reading of the design's 1.11 has changed, and it is "
        "the antecedent the module's answer rests on"
    )

    # The module quotes all three rather than paraphrasing them.
    module = " ".join(MODULE.read_text(encoding="utf-8").replace("#:", " ").split())
    for quoted in (prohibition, reproduces, neither):
        assert " ".join(quoted.split()) in module, (
            f"the module does not quote {quoted!r}. The file's sentence has to "
            "be on the page it contradicts, not summarised somewhere else."
        )

    # The arithmetic that settles the antecedent, from the file's own evidence.
    expected = float(evidence["expected_value_of_a_scoring_event"])
    variance = float(evidence["variance_of_a_scoring_event"])

    def compound_vmr(phi: float) -> float:
        return (variance + phi * expected**2) / expected

    assert compound_vmr(values["effective_event_dispersion"]) == (
        values["measured_points_vmr_given_minutes"]
    ), "the inversion no longer reproduces the measured points VMR exactly"
    assert compound_vmr(values["measured_event_dispersion"]) == (
        values["compound_implied_points_vmr"]
    )
    assert compound_vmr(values["points_vmr_over_compound_poisson"]) == pytest.approx(
        2.30350, abs=1e-5
    ), (
        "the design's published number read as an event phi produces neither "
        "frozen points VMR, which is the whole content of `is neither`"
    )
    assert values["compound_implied_points_vmr"] / values[
        "measured_points_vmr_given_minutes"
    ] == pytest.approx(1.2185, abs=1e-4), "the 22% the note names"

    # And what the engine actually hands over is the inverted constant.
    assert PD.POINTS_EVENT_DISPERSION_KEY == "effective_event_dispersion"
    built = _distribution()
    requested = {
        parameters.phi_requested for parameters in built.event_parameters.values()
    }
    assert requested == {values["effective_event_dispersion"]}
    assert values["points_vmr_over_compound_poisson"] not in requested
    # And it reproduces, THROUGH THE ENGINE, at the mix the constant was
    # measured at: the file's own role-prior athlete carries the league
    # `value_pmf`, and his produced conditional points VMR is the frozen
    # 2.328891545818532. That is the inversion coming back out of the assembled
    # object rather than out of the arithmetic above.
    assert _role_prior_athlete(_shapes(), 8).structural_checks()[
        "points_vmr_given_minutes"
    ] == pytest.approx(values["measured_points_vmr_given_minutes"], abs=1e-8), (
        "the produced conditional points VMR is the frozen measured one, which "
        "is what the inversion is for and the reason the choice is defensible"
    )
    # At an athlete's OWN shrunk mix it is a different number and must not be
    # the frozen one — `Var[V]/E[V] + phi*E[V]` moves with the mix — and the
    # fixture's three-heavy mix produces 2.4751. A test that demanded the
    # constant here would be asking the engine to ignore the athlete.
    assert built.structural_checks()["points_vmr_given_minutes"] == pytest.approx(
        2.4751, abs=1e-3
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

    **`mix + weights == gap` is an algebraic rearrangement and cannot fail, so
    the two halves are asserted individually.** `observed_share` cancels
    identically between the two lines: re-evaluated here with `observed_share`
    drawn uniformly from [-100, 100] -- values no shrinkage could produce --
    `mix + weights - gap` came back within 4.6e-14 of zero on every draw of six
    (-1.18e-14, +4.51e-14, +1.67e-14, -1.18e-14, -1.18e-14, -1.18e-14), which
    is the float noise of the products and not a comparison. Until this
    commit that identity was the whole of the decomposition's evidence.

    Which half of it that mattered for is measurable rather than arguable.
    Reading `role_prior` at bucket 5 or 7 instead of this athlete's 6 moves the
    POINTS mix to -0.182397 and -0.106957 against -0.134648, and all three
    satisfy the identity -- but the neighbouring box-score assertion catches
    that one anyway, because `observed E[V]` goes to 2.007170 and 1.995842
    against an exact 2.0. Doing the same to the THREES prior alone was caught by
    NOTHING: `observed[threes]/observed[points_events]` moved from 2/7 to
    0.292775 and the threes mix from -0.086123 to -0.133148 with this test
    green, because no box-score identity pins a three-point share. So three
    things are held now: each half of both decompositions against its own
    measured value, that observed three-point share against 2/7, and the points
    mix against the SAME quantity taken by a second route -- the box score fixes
    `E[V_observed]` at exactly 2.000000 without inverting any shrinkage, so
    `mix == rate_events * (E[V_shrunk] - 2.0) * minutes` compares the inverted
    bank against the box score rather than against itself.

    On this athlete, in points: +0.212563 = -0.134648 + 0.347211; in threes:
    +0.012300 = -0.086123 + 0.098423. Both terms are
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

    assert observed["threes"] / observed["points_events"] == pytest.approx(
        2.0 / 7.0, abs=1e-9
    ), (
        "the observed three-point share of this fixture's scoring events is no "
        "longer 2/7. It is inverted out of the shrinkage the same way "
        "E[V_observed] is, and unlike E[V_observed] no box-score identity pins "
        "it, so it is pinned here instead: a wrong `role_prior` bucket or a "
        "wrong `prior_weight` moves it and nothing else in this test would."
    )

    #: Each half of the decomposition, measured. `mix + weights == gap` holds
    #: for ANY `observed_share`, so these are what carry the claim.
    halves = {
        "points": (-0.13464815840554356, 0.34721069422860906),
        "threes": (-0.08612340270955803, 0.09842311620643912),
    }
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
        want_mix, want_weights = halves[stat]
        assert mix == pytest.approx(want_mix, abs=1e-6), (
            f"{stat}: the shrunk-mix half of the gap is now {mix:.6f} against "
            f"the measured {want_mix:.6f}. The identity above holds whatever "
            "`observed` is; this is the assertion that says `observed` is the "
            "athlete's own unshrunk bank."
        )
        assert weights == pytest.approx(want_weights, abs=1e-6), (
            f"{stat}: the credibility-weights half is now {weights:.6f} against "
            f"the measured {want_weights:.6f}"
        )
    # The points mix, by the second route: the box score says a player's points
    # are 1*FT + 2*FG2 + 3*FG3 and his scoring events are FT + FG2 + FG3, so
    # E[V_observed] is 2.000000 here by identity and not by inversion.
    assert float(projection.rates["points_events"]) * (
        expected_value - 2.0
    ) * minutes == pytest.approx(halves["points"][0], abs=1e-9), (
        "the inverted bank and the box-score identity disagree about "
        "E[V_observed], so one of `role_prior[bucket]` and `prior_weight` is "
        "not the pair this projection was shrunk with"
    )
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


def test_a_priced_prop_reaches_the_freeze_and_the_selection_gate_is_not_what_stops_it(
    tmp_path: Path,
) -> None:
    """What pricing a prop actually changes, driven through the shipped functions.

    `gameday_card.opinions_for`'s docstring said the wiring changes "one number
    — `census.priced` — and nothing else", and gave the selection gate as the
    reason. Both halves were wrong, and the same docstring conceded it four
    lines later by saying "prices, freezes and settles" is now literally true of
    the player family.

    Three outputs move, and this asserts all three off one call: `census.priced`,
    a player key in the returned `probabilities` map, and `census.push_mass`
    beside it.

    The freeze is not behind the selection gate. `_rows_to_freeze` takes the
    WAGERS — its three filters are tip state, complete strata and best price —
    and never reads `result.selections`, so a prop that can never become a
    selection is frozen anyway. `forward_evidence.write_snapshot` is handed the
    whole probability map and writes `model_probability` and `edge` per row into
    an append-only-within-the-day CSV, so the first such row can never be
    re-priced or withdrawn.

    Driven with the shipped key builder (`card_pricing.default_key_for(CBB)`),
    the shipped `_rows_to_freeze` and the shipped `write_snapshot`, into
    `tmp_path`. **Nothing here is graded and no result is stated**: the two
    numbers asserted are that the snapshot's player row carries a finite
    probability strictly between 0 and 1 and a finite edge — a structural check
    that the columns are populated rather than blank, not a claim about the
    model's accuracy or its value against the price.

    This test is where the docstring's claim is held. It goes red if the freeze
    is ever put behind `result.selections`, at which point that paragraph is
    wrong in the other direction and has to be rewritten again.
    """
    from dataclasses import replace as _replace
    from datetime import datetime, timezone

    from cbb_betting_lab import forward_evidence
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.reports import card_pricing, gameday_card as GC

    key_for = card_pricing.default_key_for(CBB)
    model, _shapes_used = _slate_model()

    # The real key, built by the same callable the card and the freeze share,
    # rather than the hand-built tuple `_wager` carries for the other tests.
    # Two hand-built copies of a join key is the NHL lab's five-member bug
    # family, and a test that built its own would prove the join, not use it.
    prop = _wager("player_points", line=14.5)
    prop = _replace(prop, key=key_for(prop))

    probabilities, census = GC.opinions_for([prop], model, day=DAY)
    assert census.priced == 1
    assert prop.key in probabilities, sorted(probabilities)
    assert 0.0 < probabilities[prop.key] < 1.0
    assert prop.key in census.push_mass, (
        "the call filled no push mass for a player rung. All ten player markets "
        "are push_possible and the freeze reads this map."
    )

    guard = GC.TipGuard(now=lambda: datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc))
    freezable = GC._rows_to_freeze(
        [prop], guard=guard, per_event_complete=True
    )
    assert len(freezable) == 1, (
        "the prop did not reach the freeze at all, so this test proves nothing "
        f"about what the freeze writes. Rows: {freezable.to_dict('records')}"
    )

    path = forward_evidence.write_snapshot(
        freezable,
        probabilities,
        key_for=key_for,
        verdicts_in_force=(),
        snapshot_date=DAY,
        archive_dir=tmp_path / "archive",
    )
    assert path is not None and path.is_file()
    frozen = forward_evidence.read_snapshot(path)
    rows = frozen.loc[frozen["market"] == "player_points"]
    assert len(rows) == 1, frozen.to_dict("records")
    row = rows.iloc[0]

    written = float(row["model_probability"])
    assert written == pytest.approx(probabilities[prop.key], abs=1e-12), (
        "the frozen probability is not the one the card produced"
    )
    assert 0.0 < written < 1.0
    assert math.isfinite(float(row["edge"])), (
        "`write_snapshot` computes `edge = expected_value(probability, "
        "american_odds)` and wrote a blank for a row that carries both. The "
        "docstring's claim that pricing changes `census.priced` and nothing "
        "else rested on this column staying empty."
    )

    # The selection gate is a different question and does not reach here. It
    # stops a BET, and it is asserted where it belongs; what this shows is that
    # `_rows_to_freeze` never asked it anything.
    import inspect as _inspect

    source = _inspect.getsource(GC._rows_to_freeze)
    assert "selections" not in source, (
        "`_rows_to_freeze` now reads the selections, so the freeze IS behind "
        "the selection gate and `opinions_for`'s docstring — which says it is "
        "not — has to be rewritten. Say which way round the tree is."
    )

    # And the docstring, held POSITIVELY. A ban on the false form of words
    # cannot be written here: the corrected paragraph quotes the sentence it is
    # correcting, and a substring test cannot tell a quotation of a repaired
    # defect from a fresh claim of it — the same reason
    # `tests/test_player_rates.py` will not ban "no probability exists". So the
    # docstring is required to NAME each of the three outputs that move and the
    # writer they reach, which a paragraph claiming only `census.priced` moves
    # could not do.
    doc = GC.opinions_for.__doc__ or ""
    for named in ("push_mass", "_rows_to_freeze", "write_snapshot", "edge"):
        assert named in doc, (
            f"`opinions_for`'s docstring no longer names {named!r}. It said for "
            "three commits that pricing the player half changes `census.priced` "
            "and nothing else, while it also fills the push mass and the "
            "probability map — and both reach an append-only frozen snapshot "
            "carrying a model probability and an edge per player wager."
        )


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


def test_an_engine_that_refuses_the_whole_subject_declines_and_does_not_kill_the_card(
    tmp_path: Path,
) -> None:
    """`opinions_for`'s two engine-build handlers, driven — they held no test.

    The build call in `reports/gameday_card.opinions_for` is wrapped in two
    `except` clauses that turn a whole-OBJECT refusal into a census bucket
    instead of a traceback, and neither was executed anywhere on this branch: a
    line tracer over this file, `test_gameday_card.py`, `test_player_seam.py`,
    `test_player_rates.py` and `test_player_census_reconciles.py` recorded them
    as never run, because every card test built successfully and refused
    per-MARKET inside `_read_player_market` instead. Measured here, by running
    those five files with the whole `try` replaced by a bare
    `cached = engine.build(projection, shapes=model.shapes)`: 216 of 217 tests
    stayed green and the single red one was this test. A handler with no test is
    a handler nobody has seen work, and this one is the difference between one
    refused prop and a card with no spread, total or moneyline on it — the
    outcome `models/player_distributions.build`'s own docstring records a
    `KeyError` producing once already.

    Both clauses, and they catch different things:

    * **`PlayerDistributionError` and its subclasses.** Driven through the real
      loader on a frozen file recording `residual_correlation` unfittable —
      `player_rates._unfittable` does not read that constant, so the projection
      stays `priceable=True` and reaches the engine, which refuses every one of
      the ten markets at once and raises `MarketRefused`. The card must decline
      in the FIT'S own sentence, never a paraphrase.
    * **a bare `TypeError` or `ValueError`.** `PlayerDistributionError` is a
      `ValueError` subclass, so this clause catches only what the engine did not
      raise deliberately: a projection whose fields are not the numbers the
      engine reads. Driven by taking the real estimator's projection and
      replacing its minutes lattice with strings — the shape a slate assembled
      by hand, or an estimator whose return changed under the card, actually
      has. `_player_decline` lets such a slate through by design (it checks
      `priceable` and `shapes`, not field dtypes), so this is the net under it.

    Neither is a pass, an avoid or a no-value call, and neither may be reported
    as the model having no opinion: both land in `census.declined`, `priced` is
    zero, and every other wager on the card is still priced.
    """
    from cbb_betting_lab.reports import gameday_card as GC

    def _refuse_a_constant_the_estimator_never_reads(document: dict) -> None:
        document["unfittable"] = {
            "residual_correlation": {
                "reason": "refused: the residual copula did not stabilise.",
                "cost": "No market can be priced.",
            }
        }

    nothing = _shapes_with(
        tmp_path, _refuse_a_constant_the_estimator_never_reads, name="card-refused.json"
    )
    model, _ = _slate_model(shapes=nothing)
    projection = next(iter(next(iter(model.players.values())).values()))
    assert projection.priceable, (
        "the estimator now refuses this constant too, so the engine is never "
        "reached and this test drives the projection's refusal instead of the "
        "engine's; pick a constant only `player_distributions` reads"
    )

    from cbb_betting_lab.models import player_census as PC

    run = PC.RunDisposition(what="a card", store_sha256="not a store")
    probabilities, census = GC.opinions_for(
        [_wager("player_points", line=14.5), _wager("player_rebounds", line=5.5)],
        model,
        day=DAY,
        dispositions=run,
    )
    assert probabilities == {} and census.priced == 0
    # And the bucket it lands in for design section 10's pre-grading identity:
    # the ENGINE refused the subject, so both wagers are the athlete's refusal
    # and neither is an unreadable row. The two are different facts and the
    # gate sums them apart.
    assert run.bucket(PC.BUCKET_ATHLETE_REFUSED) == 2
    assert run.bucket(PC.BUCKET_UNREADABLE) == 0 and run.bucket(PC.BUCKET_PRICED) == 0
    assert list(census.declined) == [
        "refused: every one of the ten markets. refused: the residual copula "
        "did not stabilise. No market can be priced."
    ], (
        "the card did not print the engine's own sentence for a whole-object "
        f"refusal: {census.declined}"
    )
    assert census.declined[next(iter(census.declined))] == 2, (
        "one object refused, two wagers declined against it — the cache is per "
        "(event, athlete) and the refusal is cached with it"
    )

    # The second clause. The same real projection, with the one field the
    # engine reads first replaced by something that is not numbers.
    good, shapes = _slate_model()
    athlete, real = next(iter(good.players["e1"].items()))
    corrupt = replace(real, minutes_pmf=tuple("a" for _ in real.minutes_pmf))
    from cbb_betting_lab.models import slate as SLATE

    hand_assembled = SLATE.SlateModel(
        day=DAY,
        matchups={},
        players={"e1": {athlete: corrupt}},
        resolved=dict(good.resolved),
        name_refusals={},
        player_priced_through=good.player_priced_through,
        shapes=shapes,
    )
    with pytest.raises(ValueError):
        PD.build(corrupt, shapes=shapes)
    probabilities, census = GC.opinions_for(
        [_wager("player_points", line=14.5)], hand_assembled, day=DAY
    )
    assert probabilities == {} and census.priced == 0
    reason = next(iter(census.declined))
    assert reason.startswith("the player distribution could not be built"), (
        f"a bare ValueError out of the engine reached no reader: {census.declined}"
    )
    assert "could not convert string to float" in reason, (
        "the sentence must carry the exception's own words; a bucket that says "
        "only 'could not be built' cannot be acted on"
    )


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
    """It runs on a card and it reports. It does NOT stop — see the body.

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


def _rendered_card(model, *, tmp_path: Path, events: int, name: str) -> str:
    """A whole card, rendered, over `events` prop wagers on the fixture athlete.

    Through `board_from_payloads` and `run_card` rather than by calling the
    renderer's private section builder, because what is under test is whether a
    reader of the published card can tell the three states apart. A test that
    called `OpinionCensus.structural_check_line` itself would pass on a card
    that never printed it -- which is precisely the state this test was written
    against, and which four tests in this file already had.
    """
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.reports import gameday_card as GC
    from cbb_betting_lab.staging_provider_policy import StagingProviderPolicy

    payloads = [
        {
            "id": f"e{index}",
            "commence_time": f"{DAY}T23:00:00Z",
            # A DISTINCT pair of schools per event. `default_key_for` keys a
            # wager by market, segment, player, the two schools, selection and
            # line -- not by event id -- so eight events sharing two school
            # names are one wager, and the card would price one distribution
            # while the census counted eight.
            "home_team": f"Home State {index}",
            "away_team": f"Away Tech {index}",
            "bookmakers": [
                {
                    "key": "draftkings",
                    "title": "DraftKings",
                    "markets": [
                        {
                            "key": "player_points",
                            "outcomes": [
                                {
                                    "name": "Over",
                                    "description": "Sean Bairstow",
                                    "price": -110,
                                    "point": 14.5,
                                }
                            ],
                        }
                    ],
                }
            ],
        }
        for index in range(1, events + 1)
    ]
    board = GC.board_from_payloads(payloads, competition=CBB)
    assert len(board.rows) == events, "the stager refused the fixture board"
    run = GC.run_card(
        board,
        competition=CBB,
        day=DAY,
        card_slot="morning",
        archive_dir=tmp_path / name,
        # An empty policy rather than the one on disk: this test asserts what
        # the card SAYS, and `data/manual/` is never read for that.
        policy=StagingProviderPolicy(),
        matchups=model,
    )
    assert run.opinions.wagers == events, "the card priced a different board"
    return GC.render_card(run)


def _model_section_of(card: str) -> str:
    """The "What the model said" section of a rendered card, and only it."""
    head = "## What the model said"
    assert head in card, "the card no longer carries the model's section"
    body = card.split(head, 1)[1]
    return head + body.split("\n## ", 1)[0]


def test_the_card_prints_design_4s_ratio_and_not_only_stops_on_it(
    tmp_path: Path,
) -> None:
    """Design 4's report half, read off the rendered card.

    **The defect.** The commit that gave design 4's stop rule a caller wired
    only the stop. `_run_the_structural_check` filled `census.structural_check`
    and called `assert_structural_checks`, and
    `OpinionCensus.structural_check_line` -- the only thing that says which of
    the three states a run was in -- was called nowhere in `src/` or
    `scripts/`: `grep -rn structural_check_line src/ scripts/` returned the
    definition and three docstrings claiming it was printed. `_model_section`
    emitted `summary_line()` and `table()` and nothing else, so a card whose
    check ran over a full population and passed, a card whose population was
    below the floor and stopped nothing, and a card that built no player
    distribution at all published a byte-identical section. That is the exact
    ambiguity `structural_check_line`'s own docstring exists against.

    Three states, three cards, three different sentences, and the difference is
    asserted rather than each sentence alone -- a renderer that printed the
    same line in every state would satisfy any one of the three.

    Nothing here is graded. The ratio is a structural quantity over a fixture
    population, the target is frozen, and no ROI, edge or verdict is stated.
    """
    passing, wagers, _ = _card_of(PD.STRUCTURAL_CHECK_POPULATION_FLOOR)
    card = _rendered_card(
        passing,
        tmp_path=tmp_path,
        events=PD.STRUCTURAL_CHECK_POPULATION_FLOOR,
        name="passed",
    )
    section = _model_section_of(card)
    assert "a ratio of 1.0819" in section, section
    assert "inside design 4's 15% stop" in section
    assert f"{PD.STRUCTURAL_CHECK_POPULATION_FLOOR} of " in section

    # Below the floor, on a target moved out of band: the card prints the ratio
    # and says in terms that it stops nothing. Same fixture athlete, same
    # renderer, and the only thing that changed is the size of the population.
    def _move_the_target(document):
        document["constants"]["structural_check_targets"]["value"][
            "unconditional_points_vmr_regulars"
        ] = 2.5

    moved = _shapes_with(tmp_path, _move_the_target, name="moved-for-the-card.json")
    small, _, _ = _card_of(PD.STRUCTURAL_CHECK_POPULATION_FLOOR - 1, shapes=moved)
    below = _model_section_of(
        _rendered_card(
            small,
            tmp_path=tmp_path,
            events=PD.STRUCTURAL_CHECK_POPULATION_FLOOR - 1,
            name="below",
        )
    )
    assert "STOPS NOTHING" in below
    assert "Fewer than the declared floor of " in below

    # And a card that built no player distribution says that, rather than
    # saying nothing and reading like either of the two above.
    never = _model_section_of(
        _rendered_card({}, tmp_path=tmp_path, events=2, name="never")
    )
    assert "structural check was not asked" in never
    assert "built no player distribution" in never

    assert len({section, below, never}) == 3, (
        "two of the three states publish the same section, which is the "
        "ambiguity this line exists to remove"
    )


def test_the_card_prints_both_event_dispersions_and_says_which_one_priced_the_card(
    tmp_path: Path,
) -> None:
    """`POINTS_EVENT_DISPERSION_KEY`'s disclosure, read off a rendered card.

    **The defect.** The constant justifies its choice twice by promising the
    disclosure -- "This engine takes `effective_event_dispersion` =
    1.1059306970490195 and prints `measured_event_dispersion` =
    1.3799506487253412 beside it on every run", and again at the end of the
    paragraph that answers the frozen file's apparent prohibition -- and
    nothing printed either number. The only mapping carrying the two keys was
    `PlayerDistribution.structural_checks`, which has no caller in `src/` or
    `scripts/`. The mapping a run does print came from
    `population_structural_checks`, which returned nine keys and neither
    dispersion. Rendered, the eight-prop card built below carried neither
    figure and not the word "dispersion" anywhere in it.

    It is load-bearing rather than decorative: the same paragraph concedes the
    choice moves design 4's produced ratio by 0.167, "the whole width of design
    4's stop budget", and offers the printed-beside disclosure as the thing
    that keeps the choice honest given the stop rule cannot decide it.

    Four claims:

    1. **Both frozen numbers reach a published card**, at full precision, in
       its model section, with the name of the key that priced it. Read
       through `run_card` and `render_card`, never by calling the reporter: a
       test that called `OpinionCensus.event_dispersion_line` itself would pass
       on a card that printed nothing, which is exactly the state this repair
       is against and which the ratio line was in until last commit.
    2. **The sentence follows the engine rather than repeating a literal.**
       Moving `POINTS_EVENT_DISPERSION_KEY` moves the number the card says it
       priced at, the name it gives that number, and which candidate is named
       as unused. That is asserted on a card BELOW the population floor,
       because the swap is not cosmetic: on this fixture population -- eight
       copies of one athlete, which is not the frozen file's nine role priors
       the constant's 0.9209/1.0875 pair is measured over -- it moves the
       pooled ratio from 1.0819 to 1.2596 and design 4's stop fires. Both of
       those are structural checks over a fixture, not results.
    3. **A card that built no player distribution says so**, so the two states
       do not publish the same sentence; that is the ambiguity
       `structural_check_line` exists against, one level down.
    4. **Nothing stops on the disclosure.** It is three frozen constants, and
       `assert_structural_checks` still refuses a mapping that carries them
       without a population.

    Nothing here is graded. Every number is a frozen constant read out of
    `data/processed/cbb_player_shapes.json` and reprinted, or a structural
    check over a fixture card that says so. No ROI, edge or verdict is stated,
    and no market refused by name is priced.
    """
    from cbb_betting_lab.reports import gameday_card as GC

    shapes = _shapes()
    reconciliation = shapes.value("points_compound_reconciliation")
    effective = float(reconciliation["effective_event_dispersion"])
    measured = float(reconciliation["measured_event_dispersion"])
    assert PD.POINTS_EVENT_DISPERSION_KEY == "effective_event_dispersion"

    # -- claim 1: both numbers, on a published card -----------------------
    passing, _, _ = _card_of(PD.STRUCTURAL_CHECK_POPULATION_FLOOR)
    section = _model_section_of(
        _rendered_card(
            passing,
            tmp_path=tmp_path,
            events=PD.STRUCTURAL_CHECK_POPULATION_FLOOR,
            name="dispersion",
        )
    )
    assert repr(effective) in section, section
    assert repr(measured) in section, section
    assert "priced the compound points sum at `effective_event_dispersion`" in section
    assert "other candidate `measured_event_dispersion`" in section
    assert "was not used" in section

    # -- claim 2: it follows the constant ---------------------------------
    below = PD.STRUCTURAL_CHECK_POPULATION_FLOOR - 1
    original = PD.POINTS_EVENT_DISPERSION_KEY
    try:
        PD.POINTS_EVENT_DISPERSION_KEY = "measured_event_dispersion"
        swapped_model, swapped_wagers, _ = _card_of(below)
        swapped = _model_section_of(
            _rendered_card(
                swapped_model, tmp_path=tmp_path, events=below, name="swapped"
            )
        )
        _, swapped_census = GC.opinions_for(swapped_wagers, swapped_model, day=DAY)
        stopped = swapped_census.structural_check["unconditional_points_vmr_ratio"]
        # The card at the floor, with the constant swapped: design 4's stop
        # fires on this fixture population. Built here rather than asserted
        # from the ratio alone, because the point of claim 2 is that the swap
        # reaches the priced object and not only the printed sentence.
        at_floor, floor_wagers, _ = _card_of(PD.STRUCTURAL_CHECK_POPULATION_FLOOR)
        with pytest.raises(PD.StructuralCheckFailed, match="a ratio of 1.2596"):
            GC.opinions_for(floor_wagers, at_floor, day=DAY)
    finally:
        PD.POINTS_EVENT_DISPERSION_KEY = original
    assert PD.POINTS_EVENT_DISPERSION_KEY == "effective_event_dispersion"

    assert "priced the compound points sum at `measured_event_dispersion`" in swapped
    assert "other candidate `effective_event_dispersion`" in swapped
    assert repr(measured) in swapped and repr(effective) in swapped
    assert stopped == pytest.approx(1.2596, abs=1e-3), (
        "the swap no longer moves the fixture card's pooled ratio, so claim 2 "
        "is asserting a printed sentence over an unchanged object"
    )

    # -- claim 3: the state where no dispersion was chosen ----------------
    never = _model_section_of(
        _rendered_card({}, tmp_path=tmp_path, events=2, name="no-dispersion")
    )
    assert "No scoring-event dispersion was chosen on this card" in never
    assert repr(effective) not in never and repr(measured) not in never
    assert "priced the compound points sum at" not in never

    # -- claim 4: it is a disclosure and nothing stops on it --------------
    with pytest.raises(PD.PlayerDistributionError, match="POPULATION quantity"):
        PD.assert_structural_checks(
            {
                "measured_event_dispersion": measured,
                "effective_event_dispersion": effective,
                "points_event_dispersion_used": effective,
            }
        )


# --------------------------------------------------------------------------
# The limitations, recorded as passing assertions
# --------------------------------------------------------------------------


def _player_rows_in_archive(archive_dir) -> dict[str, list[str]]:
    """`{snapshot filename: [player markets frozen in it]}`, through the shipped reader.

    The detector behind clause 2's successor. It reads the frozen opinions the
    way the settle pass does — `forward_evidence.snapshot_files` then
    `read_snapshot`, never a hand-built glob or a hand-built column list — and
    reports the rows whose market is in the PLAYER family of the registry.

    Which market keys count is read off `markets.MARKETS` rather than typed,
    because a player market added to the registry later must be watched by this
    clause without anybody remembering to add it here.
    """
    from cbb_betting_lab import forward_evidence
    from cbb_betting_lab import markets as markets_registry

    player_keys = {
        market.key
        for market in markets_registry.MARKETS
        if market.family == markets_registry.PLAYER
    }
    assert "player_points" in player_keys
    found: dict[str, list[str]] = {}
    for snapshot in forward_evidence.snapshot_files(archive_dir):
        frozen = forward_evidence.read_snapshot(snapshot)
        if "market" not in frozen.columns:
            continue
        hits = sorted(set(frozen["market"].dropna().astype(str)) & player_keys)
        if hits:
            found[snapshot.name] = hits
    return found


def test_the_gaps_this_engine_still_has_are_the_ones_written_down(
    tmp_path: Path,
) -> None:
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

       The successor is that **no run has stored what is now priced — and the
       writer that would store it is already wired, so the clause is guarded on
       the archive and not only on design 9's file.** As it stood this clause
       said "the probabilities this engine produces live only inside a call and
       no run leaves a record of what it thought", and the only assertion under
       it was that `data/processed/cbb_player_lines.csv` does not exist —
       design 9's proposed store, which nothing in this branch writes or reads.
       The path that actually records a player probability is
       `gameday_card.run_card` -> `forward_evidence.write_snapshot`, wired in
       this same branch and driven end to end by
       `test_a_priced_prop_reaches_the_freeze_and_the_selection_gate_is_not_
       what_stops_it`, which watches a player_points row reach a snapshot CSV
       carrying `model_probability` and `edge`. The day
       `price_backtest.DEFAULT_MODEL` is pointed at
       `cbb_betting_lab.models.slate:slate_model`, the nightly card writes
       exactly those rows into `data/archive/priced_snapshots/<day>.csv` — and
       the clause as written would have stayed green while the branch went on
       saying no run leaves a record.

       So both are held. Design 9's per-row store still does not exist, and
       `_player_rows_in_archive` finds no player-family row in any frozen
       snapshot in this tree — measured today over 0 snapshot files, because
       `data/archive/` has never been written here. The detector is exercised
       on a fixture archive in the same assertion rather than trusted: a
       snapshot written by the shipped `write_snapshot` with one player_points
       row is found by it, so "no rows" is a fact about the archive and not
       about the scan. `forward_evidence`'s own sentence — "no player prop has
       ever been priced here" — is the same claim one module up, and it is
       required to still be there so the two go red together.
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

    # Clause 2's other half: the writer that is already wired. Prove the
    # detector first, on an archive built by the shipped `write_snapshot`, so
    # the empty result below is a fact about this tree and not about the scan.
    from cbb_betting_lab import forward_evidence
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.reports import card_pricing

    fixture_archive = tmp_path / "archive"
    forward_evidence.write_snapshot(
        [
            {
                "event_id": "E1",
                "commence_time": "2024-01-15T23:00:00Z",
                "home_team": "Home",
                "away_team": "Away",
                "market": "player_points",
                "segment": "game",
                "player": "Sean Bairstow",
                "selection": "over",
                "line": 14.5,
                "american_odds": -110,
                "book": "draftkings",
            }
        ],
        {},
        key_for=card_pricing.default_key_for(CBB),
        verdicts_in_force=(),
        snapshot_date=DAY,
        archive_dir=fixture_archive,
    )
    assert _player_rows_in_archive(fixture_archive) == {
        f"{DAY}.csv": ["player_points"]
    }, (
        "the detector below cannot see a player prop in a snapshot written by "
        "the shipped writer, so the assertion after it certifies nothing"
    )

    frozen_player_rows = _player_rows_in_archive(forward_evidence.ARCHIVE_DIR)
    assert not frozen_player_rows, (
        "a run has frozen player-prop opinions into "
        f"{forward_evidence.snapshot_dir(forward_evidence.ARCHIVE_DIR)}: "
        f"{frozen_player_rows}. `write_snapshot` writes `model_probability` and "
        "`edge` per row and is append-only within the day, so those "
        "probabilities now outlive the call that made them and cannot be "
        "withdrawn. Say what was recorded and on which model spec, and note "
        "that design 10's 261,870-wager reconciliation still gates grading any "
        "of it; do not delete this clause."
    )
    # **Re-pointed on 2026-09-07, exactly as this assertion's own message
    # said to.** The sentence used to be "no player prop has ever been priced
    # here", and it stopped being true twice: `gameday_card.opinions_for` has
    # priced props since 2026-09-06 and `reports/prop_grading.py` has scored
    # them since 2026-09-07. The claim that survives is narrower and is the one
    # the archive scan above is the floor for — nothing has been FROZEN into
    # this ledger — so the two now say the same thing.
    assert "no player prop has ever been frozen into" in (
        forward_evidence.__doc__ or ""
    ), (
        "`forward_evidence`'s module docstring no longer carries the sentence "
        "the assertion above is the floor for. It is the same claim one module "
        "up — inside the module that would do the recording. If a prop has now "
        "been frozen there, rewrite both together; if the sentence was merely "
        "reworded, re-point this assertion at the new words."
    )
    # The wider claim may be QUOTED — the correction has to be able to say what
    # it corrected — and may not be asserted. Same rule, same reason, as
    # `tests/test_what_we_can_claim.py::test_nothing_in_this_repository_calls_
    # a_player_prop_priced`.
    asserting = [
        line
        for line in (forward_evidence.__doc__ or "").splitlines()
        if "no player prop has ever been priced" in line
        and '*"no player prop has ever been priced here"*' not in line
    ]
    assert not asserting, (
        "the wider claim came back, unquoted: "
        f"{asserting}. Props are priced by `gameday_card.opinions_for` and "
        "scored by `reports/prop_grading.py`; a module docstring saying "
        "otherwise is a false sentence in the tree."
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


# --------------------------------------------------------------------------
# The two guards between a malformed prop and the engine
# --------------------------------------------------------------------------


def test_a_prop_with_no_side_or_no_line_is_a_bucket_and_not_a_dead_card() -> None:
    """The two guards between a malformed prop and the engine, driven at the card.

    `_read_player_market` refuses a selection that names no side of the line and
    a prop with no line at all, and **both returns were executed by no test on
    this branch**: every player wager any test built carried `over`/`under` and
    a numeric line, so the two census buckets they produce were asserted
    nowhere. `_read_player_market` is called with no `try` around it and
    `_player_decline` checks the market, the event, the name and the projection
    and never the selection or the line — so with the guards removed or
    reordered, `float(line)` on `None` is a `TypeError` raised inside
    `opinions_for`'s player branch, which no handler there covers, and the whole
    card dies rather than filing one bucket.

    Both wagers here reach the guards: the subject is priceable, the engine is
    importable and the slate carries its constants, so nothing upstream declines
    them first. They are filed in the row-level bucket of design section 10's
    pre-grading identity, because the athlete has a distribution and it is the
    rung that cannot be read off it.

    Mutation: delete `if wager.selection not in (OVER, UNDER)` — RED, with the
    selection reaching `distribution.market` and the card raising. Delete
    `if line is None` — RED with a `TypeError` out of `opinions_for`.
    """
    from cbb_betting_lab.models import player_census as PC
    from cbb_betting_lab.reports import gameday_card as GC

    model, _ = _slate_model()
    sideless = replace(
        _wager("player_points", line=14.5),
        selection="yes",
        key=("e1", "player_points", "yes", 14.5, "Sean Bairstow"),
    )
    lineless = replace(
        _wager("player_points", line=14.5),
        line=None,
        key=("e1", "player_points", "over", None, "Sean Bairstow"),
    )
    run = PC.RunDisposition(what="a card", store_sha256="not a store")
    probabilities, census = GC.opinions_for(
        [sideless, lineless], model, day=DAY, dispositions=run
    )

    assert probabilities == {} and census.priced == 0 and census.wagers == 2
    assert "the selection does not name a side of this player line" in census.declined
    assert any(
        "there is no rung to price" in reason for reason in census.declined
    ), sorted(census.declined)
    assert len(census.declined) == 2, (
        "the two malformed rows collapsed into one bucket, so one of the two "
        f"guards is not the one that answered: {sorted(census.declined)}"
    )
    assert run.bucket(PC.BUCKET_UNREADABLE) == 2, (
        f"a row that cannot be read is not a statement about the athlete: "
        f"{run.by_market}"
    )
    assert run.bucket(PC.BUCKET_ATHLETE_REFUSED) == 0

    # And a well-formed wager on the same subject still prices, so neither
    # guard is refusing the athlete.
    priced, good_census = GC.opinions_for(
        [_wager("player_points", line=14.5)], model, day=DAY
    )
    assert good_census.priced == 1 and priced


def _two_tier_model(tiers: "tuple[tuple[str, bool], ...]"):
    """A slate whose athletes carry the tiers and priceability given, per event.

    Built from the real estimator's projection and then re-tiered, one event
    each, because `player_rates.resolution_census` reads
    `projection.player_tier` and `projection.priceable` and nothing else about
    a subject. Nothing here is a price: the projections are the fixture's own
    and the only fields moved are the two the join census counts.
    """
    from cbb_betting_lab.models import slate as SLATE

    model, resolved = _slate_model()
    athlete, real = next(iter(model.players["e1"].items()))
    players: dict = {}
    lookup: dict = {}
    for index, (tier, priceable) in enumerate(tiers, start=1):
        projection = replace(
            real,
            player_tier=tier,
            team_id=None,
            priceable=priceable,
            unpriceable_reason=(
                "" if priceable else "refused: this fixture subject is refused."
            ),
        )
        players[f"e{index}"] = {athlete: projection}
        lookup[(f"e{index}", "Sean Bairstow")] = athlete
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
        for index in range(1, len(tiers) + 1)
    ]
    return wide, wagers, resolved


def test_design_13s_per_tier_resolution_gate_has_a_caller_on_the_pricing_path(
    tmp_path: Path,
) -> None:
    """It runs on a card and it reports. It does NOT stop — see the body.

    **The defect, and it is design 4's defect wearing a different design
    clause.** Design 13's failure mode 5 asks for two things: print the per-tier
    resolution rate every run, and stop the run when the priceable rate moves
    more than 2pp across tiers. `player_rates.resolution_census` is the first
    and `player_rates.assert_tier_resolution_holds` is the second, and
    `grep -rn` over `src/` and `scripts/` found BOTH only in their own
    definitions and in `tests/test_player_rates.py` — so the rate was printed on
    no run and the stop could not fire on a card, on a backtest, or on anything
    else. The measurement the rule exists against is in the module's own words:
    the team-name version of this join failed on 20.5% of provider names with
    46.7% of the misses at the low-major end, and a join that fails on half the
    low-major board is a biased sample rather than a smaller one.

    Driven at the card's own entry point, both halves:

    * a board whose two tiers resolve at 100% and 50% raises out of
      `opinions_for` — the run stops, and the message carries both rates;
    * a board inside the tolerance renders, and the card SAYS the rate rather
      than only not stopping.

    Nothing here is graded. Every number is a count of subjects, and no ROI,
    edge, interval or verdict is stated.

    Mutation: delete `player_rates.report_tier_priceable_rates(...)` from
    `_run_the_resolution_check` — RED on the first half. Delete
    `_run_the_resolution_check(model, census)` from `opinions_for` — RED on
    both. Delete `run.opinions.tier_resolution_line()` from `_model_section` —
    RED on the rendered half.
    """
    from cbb_betting_lab.reports import gameday_card as GC

    # Half one: **it reports and does not stop** — Cooper's declaration of
    # 2026-09-07. 100% against 50% is fifty percentage points, twenty-five
    # times the threshold, and the run continues.
    #
    # It stopped before, and stopping was wrong: the quantity is the PRICEABLE
    # rate and design 13's 2pp is declared for the RESOLUTION rate. Measured on
    # a real eight-game board the spread is 7.50pp, so the card stopped every
    # night — read as "the model refuses tonight" when the truth was "the
    # threshold is measuring the wrong thing". The resolution rate cannot be
    # gated in its place: an unresolved name carries no athlete, so no team and
    # no tier, and `resolution_census` files it in no tier at all.
    wide, wagers, _ = _two_tier_model(
        (("high_major", True), ("high_major", True), ("low_major", True), ("low_major", False))
    )
    _probabilities, census = GC.opinions_for(wagers, wide, day=DAY)
    reported = census.tier_priceable
    assert reported is not None, (
        "the per-tier priceable rate reached no census, so design 13's "
        "first half — print it every run — is unmet again"
    )
    assert reported.gated is False
    assert reported.spread_points > reported.tolerance_points, (
        "this fixture is built to exceed the threshold; a report rather than a "
        "raise is the whole claim"
    )
    assert reported.tolerance_points == PR.TIER_RESOLUTION_TOLERANCE_POINTS, (
        "the threshold design 13 declared is carried on the report, so the day "
        "the census can tier a refusal the gate has its number already"
    )
    assert "reports and does not stop" in reported.line()

    # Half two: the report, off a rendered card. Two tiers, both resolving in
    # full, so the check runs and passes and the card has to say so.
    holding, wagers, _ = _two_tier_model(
        (("high_major", True), ("high_major", True), ("low_major", True), ("low_major", True))
    )
    _, census = GC.opinions_for(wagers, holding, day=DAY)
    assert set(census.tier_resolution) == {"high_major", "low_major"}
    section = _model_section_of(
        _rendered_card(holding, tmp_path=tmp_path, events=4, name="tiers")
    )
    assert "Design 13's per-tier resolution rate" in section, section
    assert "moves 0.00 percentage points across tiers" in section
    assert "high_major 100.0% of 2" in section and "low_major 100.0% of 2" in section

    # And the third state, which must not read like the second: one tier
    # carries every subject, so the check has nothing to compare.
    lone, wagers, _ = _two_tier_model((("high_major", True), ("high_major", False)))
    _, census = GC.opinions_for(wagers, lone, day=DAY)
    assert census.tier_resolution_line().endswith(
        "Fewer than two tiers carry a subject, so the 2pp check has nothing to "
        "compare and STOPS NOTHING on this card."
    ), census.tier_resolution_line()

    # And a card with no player projection at all says which absence that is,
    # rather than printing a rate over nothing.
    empty = GC.OpinionCensus()
    assert empty.tier_resolution_line() == (
        "Design 13's per-tier resolution rate was not asked: this card holds "
        "no player projection to tier."
    )
