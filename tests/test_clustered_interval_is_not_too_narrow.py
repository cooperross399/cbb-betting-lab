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

from cbb_betting_lab.stats import (
    interval_by_cluster,
    interval_three_way,
    interval_two_way,
)


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


# ---------------------------------------------------------------------------
# The third arm: the athlete, which design section 10 says is not optional
# ---------------------------------------------------------------------------


def _synthetic_ladder(subjects: int = 60, rungs: int = 8, seed: int = 5) -> pd.DataFrame:
    """One athlete's whole ladder moves together; his rungs sit on other nights.

    The shape the player-prop population actually has, and the one the game and
    the day arms cannot see: `player_points` carries a mean 7.19 lines per
    subject on the 2024 store, so 78,984 wagers are about 8,803
    subject-opinions. Here each subject carries a shared component and each of
    his rungs is on a different game and a different day, so the game and day
    arms see independent observations and only the athlete arm sees the
    dependence.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for subject in range(subjects):
        shared = float(rng.normal(0, 1))
        for rung in range(rungs):
            rows.append(
                {
                    "event_id": subject * rungs + rung,
                    "slate_date": f"2024-01-{(rung % 28) + 1:02d}",
                    "subject": f"player {subject}",
                    "profit_units": shared + float(rng.normal(0, 0.05)),
                }
            )
    return pd.DataFrame(rows)


def _subject_bootstrap_se(bets: pd.DataFrame, draws: int = 3000, seed: int = 13) -> float:
    """The ground truth for the third arm: resample whole ATHLETES."""
    rng = np.random.default_rng(seed)
    groups = [g["profit_units"].to_numpy() for _, g in bets.groupby("subject")]
    n = len(groups)
    estimates = []
    for _ in range(draws):
        idx = rng.integers(0, n, n)
        profit = sum(groups[i].sum() for i in idx)
        count = sum(len(groups[i]) for i in idx)
        estimates.append(profit / count)
    return float(np.std(estimates, ddof=1))


def test_the_athlete_arm_agrees_with_a_bootstrap_over_athletes():
    """A new estimator gets the same treatment the first one got.

    `interval_three_way` is `interval_two_way` plus one more `interval_by_
    cluster` call, so the arithmetic is already pinned above — but the arm is
    new and the population it exists for is new, and this repository's rule is
    that an analytic standard error is checked against a resampling one before
    anything is published on it.
    """
    bets = _synthetic_ladder()
    ours = interval_three_way(bets)
    truth = _subject_bootstrap_se(bets)
    assert ours.cluster_unit == "athlete", (
        "the athlete arm did not win on a population built so that it must"
    )
    assert abs(ours.standard_error - truth) / truth < 0.10, (
        f"athlete-clustered SE {ours.standard_error:.5f} against a bootstrap "
        f"over athletes {truth:.5f}"
    )


def test_the_game_and_the_day_cannot_see_what_the_athlete_arm_sees():
    """The reason the third arm is not optional, measured rather than argued.

    On a ladder population the game and day arms are several times too narrow —
    each athlete's rungs are spread across games and days, so both arms read
    them as independent. Reporting the widest of three is what stops that being
    published as an interval.
    """
    bets = _synthetic_ladder()
    two = interval_two_way(bets)
    three = interval_three_way(bets)
    assert three.standard_error > 2 * two.standard_error, (
        f"the two-way interval ({two.standard_error:.5f}, clustered by "
        f"{two.cluster_unit}) is not materially narrower than the three-way "
        f"({three.standard_error:.5f}). Either this fixture stopped having a "
        "per-athlete component, or the third arm stopped being needed — check "
        "which before relaxing the bound."
    )


def test_a_frame_with_no_subject_degrades_to_the_two_way_and_never_narrows_it():
    """A team market has no athlete, and the arm must be silent rather than wrong.

    Every blank subject groups under one key, and `interval_by_cluster` with a
    single cluster reports a standard error of 0.0 and infinite bounds. Zero
    never wins the widest-of-three comparison, so the two-way answer stands
    untouched — which is the property that matters, because the danger of a
    third arm is that it makes an interval NARROWER.
    """
    bets = pd.DataFrame(
        {
            "event_id": [index // 2 for index in range(60)],
            "slate_date": ["2024-01-02"] * 60,
            "subject": [""] * 60,
            "profit_units": [1.0, -1.0, 0.5, -0.5, 2.0, -2.0] * 10,
        }
    )
    two = interval_two_way(bets)
    three = interval_three_way(bets)
    assert three.cluster_unit == two.cluster_unit
    assert three.standard_error == two.standard_error
    assert (three.low, three.high) == (two.low, two.high)


def test_the_third_arm_can_never_narrow_the_two_way_answer():
    """Whatever the subjects look like, the widest of the three is taken.

    The check that matters most, because a third arm is a new way for an
    interval to come out too narrow and this repository has paid for one of
    those already.
    """
    for seed in range(8):
        rng = np.random.default_rng(seed)
        bets = pd.DataFrame(
            {
                "event_id": rng.integers(0, 40, 400),
                "slate_date": rng.integers(0, 30, 400),
                "subject": rng.integers(0, 50, 400),
                "profit_units": rng.normal(0, 1, 400),
            }
        )
        two = interval_two_way(bets)
        three = interval_three_way(bets)
        assert three.standard_error >= two.standard_error, (
            f"seed {seed}: the third arm narrowed the interval from "
            f"{two.standard_error:.6f} to {three.standard_error:.6f}"
        )
