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

**The same interval came back once through the SELECTION rule rather than
through the estimator**, and the last section of this file is what pins that
shut. `interval_two_way` chose between its two arms on the standard error, and
a degenerate arm reports no standard error at all — so on a one-day population,
which is what the forward ledger is on its first settled night, the unbounded
day arm lost to the finite game arm and the report printed a
cross-game-independence claim about a single slate.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from cbb_betting_lab.stats import (
    DEMONSTRATED_DEFICIT,
    DEMONSTRATED_EDGE,
    MINIMUM_BETS,
    NO_DEMONSTRATED_EDGE,
    RoiInterval,
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

    Every blank subject groups under one key, so `interval_by_cluster` reports
    the unidentified shape and the athlete arm steps aside. The two-way answer
    then stands untouched — which is the property that matters, because the
    danger of a third arm is that it makes an interval NARROWER.

    **The fixture has to leave the two-way answer standing to prove that.** It
    used to be 60 rows on ONE slate date carrying `[+1, −1, +0.5, −0.5, +2, −2]`
    repeated, which is every game returning exactly 0 on a single day — so both
    two-way arms were degenerate too, both sides of every assertion below were
    the same unbounded object, and the test held whatever the third arm did.
    Real between-cluster variation and five slate days, so `two` is a live,
    finite interval and `three` has something it could have narrowed.
    """
    rng = np.random.default_rng(17)
    bets = pd.DataFrame(
        {
            "event_id": [index // 2 for index in range(60)],
            "slate_date": [f"2024-01-{(index % 5) + 2:02d}" for index in range(60)],
            "subject": [""] * 60,
            "profit_units": rng.normal(0.1, 1.0, 60),
        }
    )
    two = interval_two_way(bets)
    three = interval_three_way(bets)
    # The anti-vacuity check: an unbounded `two` would satisfy every assertion
    # below without the third arm ever having been silent about anything.
    assert math.isfinite(two.low) and math.isfinite(two.high)
    assert two.standard_error > 0
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


# ---------------------------------------------------------------------------
# A degenerate arm, which is what the forward ledger's first settled night is
# ---------------------------------------------------------------------------


def _one_night(seed: int = 19, games: int = 40, per_game: int = 6) -> pd.DataFrame:
    """A single slate date, winning, with a real per-game component.

    The shape of `data/processed/cbb_forward_evidence.csv` on 2026-11-02 and
    for as long as a cell holds rows from one slate only: 240 bets over 40
    games, all on one date, above the declared `MINIMUM_BETS` floor. The per-bet
    return is a per-GAME draw plus noise, so the game-clustered arm is finite,
    tight and — the whole point — excludes zero.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for game in range(games):
        shared = float(rng.normal(0.30, 0.5))
        for _ in range(per_game):
            rows.append(
                {
                    "event_id": f"2026-11-02-{game}",
                    "slate_date": "2026-11-02",
                    "profit_units": shared + float(rng.normal(0, 0.05)),
                }
            )
    return pd.DataFrame(rows)


def test_one_slate_date_cannot_be_reported_as_a_game_clustered_interval():
    """The day arm is degenerate on night one, and it must still WIN.

    `interval_two_way` chose between its arms on `standard_error`, and the
    unidentified arm carries the dataclass default 0.0 beside its infinite
    bounds — so the arm with no interval at all lost every comparison it was
    ever in, and the docstring's promise ("computes both and takes the wider")
    inverted exactly where one arm had nothing to say. Days can never outnumber
    games, so the arm that goes degenerate is always the DAY arm, and every cell
    of the forward ledger sits on one slate date from its first settled night
    until it reaches its second.

    Measured on this fixture before the fix: the game arm reported +28.0% over
    240 bets across 40 games, 95% +11.1% to +44.9% — **demonstrated edge**, off
    a standard error that assumed forty independent games on a night when every
    one of them shared whatever daily component there was. The floor does not
    reach this: 240 bets clears the declared 200, so `not enough evidence` never
    fires and the verdict printed is the interval's.
    """
    bets = _one_night()
    by_game = interval_by_cluster(
        bets.groupby("event_id").agg(
            profit=("profit_units", "sum"), bets=("profit_units", "size")
        ),
        cluster_unit="game",
    )
    both = interval_two_way(bets)

    # The fixture has to be able to state the claim, or the test proves nothing
    # about whether the rule prevents it.
    assert by_game.bets >= MINIMUM_BETS
    assert by_game.verdict() == DEMONSTRATED_EDGE

    assert both.cluster_unit == "day" and both.clusters == 1, (
        f"a one-day ledger came back clustered by {both.cluster_unit} over "
        f"{both.clusters:,} clusters: the degenerate arm lost the comparison "
        "again, which is the whole defect"
    )
    assert math.isinf(both.low) and math.isinf(both.high)
    assert both.bets >= MINIMUM_BETS
    assert both.verdict() == NO_DEMONSTRATED_EDGE
    assert math.isnan(both.minimum_detectable_effect), (
        "a cell that could detect nothing at all must print no 'could detect' "
        "figure, and `_detectable` reads NaN to decide that"
    )


def test_clusters_that_all_returned_alike_cannot_manufacture_an_edge():
    """Zero between-cluster variation is no interval, not a perfect one.

    Every cluster returning the same ROI drives the residuals to zero, and the
    interval with them: `roi ± 0` excludes zero for any non-zero return, at any
    sample size, and reads as **demonstrated edge**. Measured before the fix on
    exactly this frame — 240 bets over 120 games all paying +0.9091 — the
    standard error came out at 3.05e-17 rather than 0.0, so every `if not
    standard_error` guard in the module walked straight past it and the cell
    printed *+90.9% to +90.9% — demonstrated edge* with a `could detect` figure
    of ±9.1e-17 beside it.

    **Six slate days on purpose.** The selection rule is not what protects this
    one: both arms are degenerate in the same way here, so whichever wins the
    comparison the answer is the same, and only `interval_by_cluster` refusing
    to report a width can refuse the claim. A real graded column cannot look
    like this — a settlement or grading fault that fills one is what does.
    """
    rows = [
        {
            "event_id": f"g{index // 2}",
            "slate_date": f"2026-11-{2 + (index // 40):02d}",
            "profit_units": 0.9091,
        }
        for index in range(240)
    ]
    flat = interval_two_way(pd.DataFrame(rows), looks=17)

    assert flat.bets >= MINIMUM_BETS, "the floor must not be what saves this"
    assert math.isinf(flat.low) and math.isinf(flat.high), (
        f"a column with no variation in it reported {flat.low:+.6%} to "
        f"{flat.high:+.6%}, which is a width rather than the absence of one"
    )
    assert not flat.survives_correction
    assert flat.verdict() == NO_DEMONSTRATED_EDGE
    assert math.isnan(flat.minimum_detectable_effect)


def test_a_zero_width_interval_read_back_from_a_record_is_not_a_finding():
    """The same shape arriving from a file rather than from the estimator.

    `interval_by_cluster` no longer emits `roi ± 0`, but nothing stops a
    published record from carrying one: `what_we_can_claim._interval_from_
    forward_row` rebuilds a cell out of the payload's own `low` and `high` and
    recovers the standard error as `(high − low) / (2·Z95)`, so a row whose two
    bounds are equal comes back as a zero-width interval with no standard error
    — which excluded zero by arithmetic and was handed the reserved words. The
    verdict must refuse a pair of bounds that is not an interval, on both sides
    of zero, and that is what `survives_correction` now checks first.
    """
    for roi in (+0.9091, -0.9091):
        pinned = RoiInterval(
            roi=roi, low=roi, high=roi, bets=50_000, clusters=12_000, looks=17
        )
        assert not pinned.survives_correction
        assert pinned.verdict() == NO_DEMONSTRATED_EDGE
        assert pinned.verdict() not in {DEMONSTRATED_EDGE, DEMONSTRATED_DEFICIT}


def test_the_athlete_arm_cannot_narrow_an_unbounded_two_way_answer():
    """One night of props: the third arm is live and the two-way arm is not.

    The three-way rule compares the same way the two-way rule does, so the
    hazard it closes is the mirror image: a ladder population on ONE slate date
    gives a degenerate day arm, an unbounded two-way answer — and a perfectly
    healthy athlete arm over forty subjects. Selected on the standard error,
    that finite arm beat the unbounded one and the report printed a per-athlete
    interval for a night whose honest interval is unbounded. It is the same
    inversion as the two-way one and it needs its own test, because the two-way
    fix alone does not reach this line.

    The opposite case — a degenerate ATHLETE arm on a team population — is
    `test_a_frame_with_no_subject_degrades_to_the_two_way_and_never_narrows_it`
    above, and the two must not be traded for each other: there the arm is
    silent because the population has no athletes in it, here the arm is silent
    because the night has no second day in it.
    """
    rng = np.random.default_rng(23)
    rows = []
    for subject in range(40):
        shared = float(rng.normal(0.05, 0.5))
        for rung in range(6):
            rows.append(
                {
                    "event_id": f"2026-11-02-{subject // 2}",
                    "slate_date": "2026-11-02",
                    "subject": f"player {subject}",
                    "profit_units": shared + float(rng.normal(0, 0.05)),
                }
            )
    bets = pd.DataFrame(rows)

    by_subject = interval_by_cluster(
        bets.groupby("subject").agg(
            profit=("profit_units", "sum"), bets=("profit_units", "size")
        ),
        cluster_unit="athlete",
    )
    # The athlete arm is live here; if it were not, the assertion below would
    # hold for a reason that has nothing to do with the rule under test.
    assert by_subject.clusters == 40 and by_subject.standard_error > 0

    three = interval_three_way(bets)
    assert math.isinf(three.low) and math.isinf(three.high), (
        f"the athlete arm ({by_subject.standard_error:.5f}) displaced an "
        f"unbounded two-way answer and printed {three.low:+.1%} to "
        f"{three.high:+.1%} for a single slate date"
    )
    assert three.verdict() == NO_DEMONSTRATED_EDGE
