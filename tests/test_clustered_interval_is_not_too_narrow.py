"""The football lab's forward-ledger interval is 10x too narrow. This pins the fix.

Reproduced before it was fixed, as the operating model requires. The football
lab's `forward_evidence.interval_by_game` computes

    variance = Σ(wᵢ² · s² / G) · G ;  standard_error = √(variance / G)

which lands at `s/G` where a cluster standard error is `s/√G`. That is on the
one report that grows all season and whose own docstring says *"a narrow
interval is how 'no demonstrated edge' quietly becomes a claim."*

The sibling lab is not touched — see `docs/ported_defects.md`. This test proves
that **this** lab's version agrees with a cluster bootstrap, which is the
ground truth, and that the defective formula does not.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from cbb_betting_lab.stats import interval_by_cluster, interval_two_way


def _synthetic_bets(seed: int = 7, games: int = 200):
    rng = np.random.default_rng(seed)
    rows = []
    for game in range(games):
        for _ in range(int(rng.integers(1, 6))):
            rows.append({"event_id": game, "profit_units": float(rng.normal(0, 1))})
    return pd.DataFrame(rows)


def _cluster_bootstrap_se(bets: pd.DataFrame, draws: int = 3000, seed: int = 11) -> float:
    """The ground truth: resample whole games with replacement."""
    rng = np.random.default_rng(seed)
    groups = [g["profit_units"].to_numpy() for _, g in bets.groupby("event_id")]
    n = len(groups)
    estimates = []
    for _ in range(draws):
        idx = rng.integers(0, n, n)
        profit = sum(groups[i].sum() for i in idx)
        count = sum(len(groups[i]) for i in idx)
        estimates.append(profit / count)
    return float(np.std(estimates, ddof=1))


def _defective_se(per_cluster: pd.DataFrame) -> float:
    """The football lab's formula, reproduced verbatim so it can be shown wrong."""
    total_bets = int(per_cluster["bets"].sum())
    games = len(per_cluster)
    ratios = per_cluster["profit"] / per_cluster["bets"]
    weights = per_cluster["bets"] / total_bets
    variance = float((weights**2 * ratios.var(ddof=1) / games).sum() * games)
    return math.sqrt(max(variance, 0.0) / games)


def test_the_ratio_estimator_agrees_with_a_cluster_bootstrap():
    bets = _synthetic_bets()
    per_cluster = bets.groupby("event_id").agg(
        profit=("profit_units", "sum"), bets=("profit_units", "size")
    )
    ours = interval_by_cluster(per_cluster)
    truth = _cluster_bootstrap_se(bets)
    # Within 10% of the bootstrap. Two estimators of the same quantity, one
    # analytic and one by resampling, should not disagree by more than noise.
    assert abs(ours.standard_error - truth) / truth < 0.10, (
        f"ratio estimator {ours.standard_error:.5f} against bootstrap {truth:.5f}"
    )


def test_the_defective_formula_is_reproduced_and_is_an_order_of_magnitude_narrow():
    """The defect itself, so nobody re-introduces it thinking it looked fine."""
    bets = _synthetic_bets()
    per_cluster = bets.groupby("event_id").agg(
        profit=("profit_units", "sum"), bets=("profit_units", "size")
    )
    truth = _cluster_bootstrap_se(bets)
    assert _defective_se(per_cluster) < truth / 5, (
        "The football lab's formula is supposed to be many times too narrow. "
        "If this assertion fails the reproduction is wrong, not the fix."
    )


def test_clustering_widens_against_a_naive_per_bet_interval():
    """With genuinely correlated bets, the cluster interval must be wider."""
    rng = np.random.default_rng(3)
    rows = []
    for game in range(150):
        shared = float(rng.normal(0, 1))  # a whole game moves together
        for _ in range(6):
            rows.append(
                {"event_id": game, "profit_units": shared + float(rng.normal(0, 0.1))}
            )
    bets = pd.DataFrame(rows)
    per_cluster = bets.groupby("event_id").agg(
        profit=("profit_units", "sum"), bets=("profit_units", "size")
    )
    clustered = interval_by_cluster(per_cluster)
    naive = float(bets["profit_units"].std(ddof=1)) / math.sqrt(len(bets))
    assert clustered.standard_error > naive * 2, (
        f"clustered {clustered.standard_error:.4f} vs naive {naive:.4f}: with "
        "six perfectly correlated bets per game the clustered interval must be "
        "about sqrt(6) wider, and it is not."
    )


def test_two_way_clustering_takes_the_wider_interval():
    """A shared daily component must widen the interval, not be averaged away."""
    rng = np.random.default_rng(5)
    rows = []
    for day in range(40):
        daily = float(rng.normal(0, 1))  # the whole slate moves together
        for game in range(10):
            for _ in range(3):
                rows.append(
                    {
                        "event_id": f"{day}-{game}",
                        "slate_date": f"2027-01-{day + 1:02d}",
                        "profit_units": daily + float(rng.normal(0, 0.05)),
                    }
                )
    bets = pd.DataFrame(rows)
    both = interval_two_way(bets)
    by_game = interval_by_cluster(
        bets.groupby("event_id").agg(
            profit=("profit_units", "sum"), bets=("profit_units", "size")
        )
    )
    assert both.cluster_unit == "day", (
        "When every game on a day moves together, the day is the honest "
        "cluster and interval_two_way must pick it."
    )
    assert both.standard_error > by_game.standard_error
