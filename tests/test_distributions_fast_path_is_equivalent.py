"""The batched variance matcher is the scalar reference, to the bit.

`distributions._match_variance_reference` is the original one-node solver:
a doubling loop, sixty bisection steps, one scalar `realised` per step. The
production path solves every node of a `build` at once through
`_match_variance_batch`. This file is the contract between the two: every
pmf the fast path returns is `np.array_equal` to the reference's, and a
whole `build` computed both ways is the same joint.

The assertion is `np.array_equal` first. Should it ever fail, the message
carries the maximum absolute difference so the failure is read as a number
rather than a boolean, and a fallback tolerance of 1e-12 is what the task
that produced this file allowed; today the measured maximum is zero.
"""

from __future__ import annotations

import numpy as np
import pytest

from cbb_betting_lab.models import distributions as d


def _assert_same_pmf(fast: np.ndarray, reference: np.ndarray, label: str) -> None:
    assert fast.shape == reference.shape, f"{label}: shape {fast.shape} vs {reference.shape}"
    if np.array_equal(fast, reference):
        return
    worst = float(np.max(np.abs(fast - reference)))
    assert np.allclose(fast, reference, rtol=0.0, atol=1e-12), (
        f"{label}: not bit-identical and beyond 1e-12; max abs diff {worst:.3e}"
    )
    pytest.fail(f"{label}: not bit-identical (max abs diff {worst:.3e}); the "
                "close-call recomputation should have made this exact")


def _random_cases(count: int, seed: int = 20260905) -> list[tuple[np.ndarray, np.ndarray, float, str]]:
    rng = np.random.default_rng(seed)
    cases = []
    shapes = ("uniform", "boundaries", "one_point", "spiky", "bell", "binomial")
    targets = ("below", "above", "far_above", "zero", "negative", "current")
    for case in range(count):
        size = int(rng.integers(1, 401))
        if case < 8:
            size = case + 1  # every tiny support, including a single point
        lo = int(rng.integers(-10, 40))
        support = np.arange(lo, lo + size, dtype=float)
        shape = shapes[case % len(shapes)]
        if shape == "uniform":
            pmf = rng.random(size)
        elif shape == "boundaries":
            pmf = np.full(size, 1e-6)
            pmf[0] += 0.5
            pmf[-1] += 0.5
        elif shape == "one_point":
            pmf = np.zeros(size)
            pmf[int(rng.integers(0, size))] = 1.0
        elif shape == "spiky":
            pmf = rng.random(size) ** 8
        elif shape == "bell":
            centre = support[0] + rng.random() * (size - 1)
            pmf = np.exp(-0.5 * ((support - centre) / max(size / 10.0, 0.5)) ** 2)
        else:
            p = float(rng.uniform(0.05, 0.95))
            counts = np.arange(size)
            with np.errstate(divide="ignore"):
                log = counts * np.log(p) + (size - 1 - counts) * np.log1p(-p)
            pmf = np.exp(log - log.max())
        pmf = pmf / pmf.sum()
        mean = float(pmf @ support)
        variance = float(pmf @ (support - mean) ** 2)
        kind = targets[(case // len(shapes)) % len(targets)]
        target = {
            "below": variance * float(rng.uniform(0.1, 0.95)),
            "above": variance * float(rng.uniform(1.05, 3.0)),
            # Far enough that the doubling loop runs several times, and for
            # a large fraction of cases hits the `high < 64` cap.
            "far_above": variance * float(rng.choice([50.0, 400.0, 5000.0, 1e6])) + 1.0,
            "zero": 0.0,
            "negative": -float(rng.uniform(0.1, 10.0)),
            "current": variance,
        }[kind]
        cases.append((pmf, support, target, f"case {case} {shape}/{kind} size {size}"))
    return cases


def test_random_nodes_match_the_reference_one_at_a_time():
    cases = _random_cases(520)
    doubled_to_cap = 0
    for pmf, support, target, label in cases:
        reference = d._match_variance_reference(pmf, support, target)
        fast = d._match_variance(pmf, support, target)
        _assert_same_pmf(fast, reference, label)
        assert abs(float(fast.sum()) - 1.0) <= 1e-12, f"{label}: sums to {fast.sum()!r}"
        mean = float(pmf @ support)
        variance = float(pmf @ (support - mean) ** 2)
        if variance > 0 and target > 64.0**2 * variance:
            doubled_to_cap += 1
    assert doubled_to_cap >= 20, "the fixture should exercise the 64x doubling cap"


def test_random_nodes_match_the_reference_as_one_batch():
    cases = _random_cases(520, seed=7)
    batch = d._match_variance_batch(
        [c[0] for c in cases], [c[1] for c in cases], [c[2] for c in cases]
    )
    assert len(batch) == len(cases)
    for (pmf, support, target, label), fast in zip(cases, batch):
        reference = d._match_variance_reference(pmf, support, target)
        _assert_same_pmf(fast, reference, label)
        assert abs(float(fast.sum()) - 1.0) <= 1e-12, label


def test_untouched_nodes_come_back_exactly_as_given():
    support = np.arange(0.0, 12.0)
    one_point = np.zeros(12)
    one_point[4] = 1.0
    spread = np.full(12, 1 / 12)
    for pmf, target in [(one_point, 3.0), (spread, 0.0), (spread, -2.0)]:
        reference = d._match_variance_reference(pmf, support, target)
        fast = d._match_variance(pmf, support, target)
        assert reference is pmf, "the reference returns the input object untouched"
        assert fast is pmf, "so must the fast path"


def test_edge_cases_are_preserved():
    with pytest.raises(d.DistributionError):
        d._match_variance_reference(np.zeros(5), np.arange(5.0), 1.0)
    with pytest.raises(d.DistributionError):
        d._match_variance(np.zeros(5), np.arange(5.0), 1.0)
    with pytest.raises(d.DistributionError):
        d._match_variance_batch(
            [np.ones(3) / 3, np.zeros(4)], [np.arange(3.0), np.arange(4.0)], [1.0, 1.0]
        )
    for n in (0, -3):
        assert np.array_equal(d._trip_count_pmf(n, 0.5, 2.0), np.array([1.0]))
        assert np.array_equal(d._trip_count_pmf_reference(n, 0.5, 2.0), np.array([1.0]))
    mixed = d._trip_count_pmfs([0, 7, -1, 12], 0.45, [1.0, 1.5, 1.0, 0.0])
    assert np.array_equal(mixed[0], np.array([1.0]))
    assert np.array_equal(mixed[2], np.array([1.0]))
    _assert_same_pmf(mixed[1], d._trip_count_pmf_reference(7, 0.45, 1.5), "n=7")
    _assert_same_pmf(mixed[3], d._trip_count_pmf_reference(12, 0.45, 0.0), "n=12 no target")


def test_trip_counts_match_the_reference_across_probabilities_and_targets():
    rng = np.random.default_rng(3)
    ns, ps, targets = [], [], []
    for _ in range(120):
        n = int(rng.integers(1, 140))
        p = float(rng.uniform(0.2, 0.75))
        binomial = n * p * (1 - p)
        ns.append(n)
        ps.append(p)
        targets.append(binomial * float(rng.choice([0.0, 0.4, 0.66, 0.9, 1.3, 40.0])))
    fast = d._trip_count_pmfs(ns, ps, targets)
    for n, p, target, pmf in zip(ns, ps, targets, fast):
        _assert_same_pmf(pmf, d._trip_count_pmf_reference(n, p, target), f"n={n} p={p:.3f}")


#: Realistic parameter sets: league-average and extreme efficiencies, slow
#: and fast tempos, every segment, resolution on and off.
BUILD_CASES = [
    dict(home_points_per_possession=1.08, away_points_per_possession=1.01, possessions=68.5),
    dict(home_points_per_possession=1.15, away_points_per_possession=0.95, possessions=74.0),
    dict(home_points_per_possession=0.97, away_points_per_possession=1.03, possessions=61.5,
         resolves_ties=False),
    dict(home_points_per_possession=1.02, away_points_per_possession=1.02, possessions=66.0,
         segment=d.FIRST_HALF),
    dict(home_points_per_possession=1.11, away_points_per_possession=0.99, possessions=70.0,
         segment=d.FIRST_HALF, resolves_ties=True),
    dict(home_points_per_possession=0.98, away_points_per_possession=1.04, possessions=62.0,
         segment=d.SECOND_HALF, resolves_ties=False),
    dict(home_points_per_possession=1.20, away_points_per_possession=0.90, possessions=78.0,
         prior_weight=0.4),
]


@pytest.mark.parametrize("case", BUILD_CASES, ids=[str(i) for i in range(len(BUILD_CASES))])
def test_build_is_identical_through_the_reference_path(case, monkeypatch):
    assert d._FORCE_REFERENCE_PATH is False, "the reference switch must be off by default"
    fast = d.build(**case)
    monkeypatch.setattr(d, "_FORCE_REFERENCE_PATH", True)
    reference = d.build(**case)
    monkeypatch.setattr(d, "_FORCE_REFERENCE_PATH", False)

    _assert_same_pmf(fast.joint, reference.joint, "joint")
    for which in ("home", "away"):
        _assert_same_pmf(fast.team_pmf(which), reference.team_pmf(which), f"{which} pmf")
    for name in ("margin_pmf", "total_pmf"):
        fast_support, fast_weights = getattr(fast, name)()
        reference_support, reference_weights = getattr(reference, name)()
        assert np.array_equal(fast_support, reference_support), name
        _assert_same_pmf(fast_weights, reference_weights, name)
    assert fast.segment == reference.segment
    assert fast.resolves_ties == reference.resolves_ties
    assert fast.possessions == reference.possessions
    assert fast.prior_weight == reference.prior_weight
    assert fast.moneyline("home") == reference.moneyline("home")
    assert fast.tie_probability() == reference.tie_probability()
    assert fast.expected_margin == reference.expected_margin
    assert fast.expected_total == reference.expected_total
    assert fast.margin(-3.5, "home") == reference.margin(-3.5, "home")
    assert fast.total(145.5, "over") == reference.total(145.5, "over")
