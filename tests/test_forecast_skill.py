"""The one number that says whether the model knows anything the price does not.

`reports/forecast_skill.py` fits

    outcome = a + b_market x market_implied
                + b_disagreement x (model_implied - market_implied)

and the coefficient on the disagreement is the whole answer. This file tests
that it **recovers the truth on data whose truth is known**, and that every way
the number could be misread is closed:

* a model that is the truth must produce a disagreement coefficient near 1;
* a model that is the price plus noise must produce one that includes zero, and
  the words must be `stats.NO_DEMONSTRATED_EDGE` exactly;
* an anti-predictive model must produce a negative one **and** a bucket table
  that shows the shape — a coefficient alone can be called noise, a monotone
  column cannot. Two columns are checked, apart, because they are two
  quantities: **overconfidence** (realised minus model-implied, which widens
  with the claimed edge under the winner's curse whatever the model's
  relationship to money) and **anti-predictiveness** (the realised return
  falling as the claimed edge rises, which is what the word means and the only
  one that can carry "raising the threshold makes it worse");
* the standard error must be the clustered one. One game supplies many
  correlated wagers, and the football lab's forward ledger shipped an interval
  10.3x too narrow on exactly that mistake;
* the words *demonstrated edge* must be **impossible** to attach to the market
  coefficient or to the intercept. A market coefficient of 0.97 excludes zero on
  the positive side, and a verdict predicate that never asked what the null was
  would announce a demonstrated edge on a number describing the market. That is
  `test_the_headline_reads_the_sign.py`'s defect arriving through a door that
  file does not watch;
* the Brier advantage must be signed so that a model which is measurably
  **better** than the price is not called a deficit. A Brier score is better
  when it is lower;
* the de-vig must pair the two sides of a wager and only those, must refuse a
  pair with no hold in it, and must count everything it refuses.

The fixture is a synthetic season whose data-generating process is written down
here, because a test of an estimator that cannot say what the estimator should
recover is not a test.
"""

from __future__ import annotations

import json
import math

import numpy as np
import pandas as pd
import pytest

from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.conferences import Tier
from cbb_betting_lab.forward_evidence import profit_units
from cbb_betting_lab.reports import forecast_skill as FS
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.selection import FULL_GAME
from cbb_betting_lab.stores import _decimal_payout as decimal_payout


#: The hold every synthetic book charges. Constant on purpose: a constant
#: overround is the case in which the disagreement coefficient is algebraically
#: invariant to the de-vig, which is a property the report claims and one of
#: these tests checks.
OVERROUND = 1.045

#: Enough games to clear `forecast_skill.MINIMUM_CLUSTERS`, and enough days that
#: the day-clustered fit is not the binding floor in the tests that need a
#: number rather than a refusal.
GAMES = 90
DAYS = 40
WAGERS_PER_GAME = 8


def american_odds_for(probability: float) -> float:
    """The exact American price implying this probability, as a float.

    Exact rather than rounded to the integers a book would hang, so that
    `implied_probability` recovers the input and a de-vig test can assert an
    equality rather than a tolerance. Rounding is a separate concern and it is
    not what these tests are about.
    """
    payout = 1.0 / probability - 1.0
    return 100.0 * payout if payout >= 1.0 else -100.0 / payout


def graded_frame(
    kind: str,
    *,
    games: int = GAMES,
    days: int = DAYS,
    per_game: int = WAGERS_PER_GAME,
    seed: int = 11,
    overround: float = OVERROUND,
    shared_outcome: bool = False,
    carry_profit_units: bool = True,
) -> pd.DataFrame:
    """A synthetic season of graded wagers whose truth is written down.

    Each game hangs `per_game` rungs of an alternate spread ladder, both sides
    of every rung, at a book charging a constant `overround`. The de-vigged
    market probability of the home side is `market_fair`; the model's is
    `market_fair` plus noise, which is what makes the disagreement column vary.

    `kind` selects the data-generating process, and it is the whole point:

    * `truth` — the home side actually wins with probability equal to the
      **model's** number. The model knows exactly what the price does not, so
      `b_market` and `b_disagreement` are both 1.
    * `noise` — it wins with probability equal to the **market's** number. The
      model's disagreement is pure noise, so `b_disagreement` is 0.
    * `anti` — it wins with probability `market - 0.5 x disagreement`. The
      bigger the model's claimed edge, the worse the bet: `b_disagreement` is
      -0.5. This is the NHL lab's shape.

    `shared_outcome=True` makes every wager in a game settle the same way. That
    is the pathological correlation a clustered standard error exists for, and
    it is how the "too narrow" test forces a difference big enough to assert on.

    **`carry_profit_units=False` exists because this fixture hid a defect for a
    fortnight.** Planting `profit_units` on every frame supplies exactly the
    column the producer's export dropped, so the whole realised-return half of
    this report was green on every fixture here and blank on every real tier —
    and the report said so in words that read as a fact about the archive. A
    fixture that always supplies a column can never ask what happens when it is
    missing, and *missing* was the shipped state.
    """
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    for game in range(games):
        day = f"2027-01-{(game % days) + 1:02d}"
        game_draw = float(rng.random())
        for rung in range(per_game):
            line = -9.5 + 2.0 * rung
            market_fair = float(rng.uniform(0.30, 0.70))
            model = float(np.clip(market_fair + rng.normal(0.0, 0.06), 0.02, 0.98))
            realised = {
                "truth": model,
                "noise": market_fair,
                "anti": float(
                    np.clip(market_fair - 0.5 * (model - market_fair), 0.02, 0.98)
                ),
            }[kind]
            draw = game_draw if shared_outcome else float(rng.random())
            home_won = draw < realised
            for selection, side_line, raw, probability, won in (
                ("home", line, market_fair * overround, model, home_won),
                ("away", -line, (1.0 - market_fair) * overround, 1.0 - model, not home_won),
            ):
                rows.append(
                    {
                        "event_id": f"e{game:03d}",
                        "slate_date": day,
                        "market": "alternate_spread",
                        "segment": FULL_GAME,
                        "player": "",
                        "selection": selection,
                        "line": side_line,
                        "american_odds": american_odds_for(raw),
                        "book": "dk",
                        "tier": (
                            Tier.HIGH_MAJOR.value
                            if game % 2
                            else Tier.LOW_MAJOR.value
                        ),
                        "model_probability": probability,
                        "outcome": "won" if won else "lost",
                    }
                )
    frame = pd.DataFrame(rows)
    if carry_profit_units:
        frame["profit_units"] = [
            profit_units(outcome, odds)
            for outcome, odds in zip(frame["outcome"], frame["american_odds"])
        ]
    return frame


def record_for(kind: str, *, looks: int = 1, **kwargs) -> dict:
    return FS.build_record(
        FS.SkillInputs(graded=graded_frame(kind, **kwargs), pair_scope="book"),
        competition=CBB,
        looks=looks,
    )


def pooled_disagreement(record: dict) -> dict:
    return FS.coefficient(FS.pooled_fit_of(record), "disagreement")


@pytest.fixture(scope="module")
def truth() -> dict:
    return record_for("truth")


@pytest.fixture(scope="module")
def noise() -> dict:
    return record_for("noise")


@pytest.fixture(scope="module")
def anti() -> dict:
    return record_for("anti")


# ---------------------------------------------------------------------------
# Does it recover the truth?
# ---------------------------------------------------------------------------


def test_a_model_that_is_the_truth_realises_all_of_its_claimed_edge(truth):
    """`b_disagreement = 1` when the outcome IS the model's probability.

    The estimator has to be able to find a real edge, or a null from it means
    nothing. This is the positive control, and it is the only test in this file
    whose expected verdict is `demonstrated edge`.
    """
    row = pooled_disagreement(truth)
    assert row["enough_evidence"], row
    assert row["estimate"] == pytest.approx(1.0, abs=0.35), (
        "the disagreement coefficient must recover 1 when the model's "
        f"probability is the true one; got {row['estimate']:.3f}"
    )
    assert row["low"] > 0.0, "a model that is the truth must exclude zero"
    assert row["verdict"] == S.DEMONSTRATED_EDGE


def test_a_model_that_is_the_price_plus_noise_knows_nothing_the_price_does_not(noise):
    """`b_disagreement = 0`, and the words are the declared ones, exactly.

    This is the NHL lab's shape — market 0.97, model 0.03 [-0.037, +0.102] — and
    the report's job is to say *no demonstrated edge* about it in those words
    rather than "small but positive" or "trending".
    """
    row = pooled_disagreement(noise)
    assert row["enough_evidence"], row
    assert row["estimate"] == pytest.approx(0.0, abs=0.4), row["estimate"]
    assert row["low"] < 0.0 < row["high"], "a null model's interval must span zero"
    assert row["verdict"] == S.NO_DEMONSTRATED_EDGE
    assert row["verdict"] == "no demonstrated edge"


def test_the_market_coefficient_recovers_one_when_the_price_is_calibrated(noise):
    """`b_market = 1` on a de-vigged, calibrated price. The de-vig's own check."""
    row = FS.coefficient(FS.pooled_fit_of(noise), "market_implied")
    assert row["estimate"] == pytest.approx(1.0, abs=0.3), row["estimate"]
    assert FS.coefficient_from_row(row).contains(1.0), (
        "a calibrated de-vigged price must contain 1.0, or the de-vig is wrong "
        "and every disagreement coefficient measured against it is unreadable"
    )


def test_an_anti_predictive_model_is_negative_and_the_table_shows_the_shape(anti):
    """The coefficient AND the buckets. Either alone is arguable.

    A coefficient is one number and a reader can call it noise. A shape across
    buckets is harder to wave away — but it has to be a shape in the right
    quantity. Two are measured and reported apart:

    * **overconfidence**, realised minus model-implied, which widens with the
      claimed edge under the winner's curse whatever the model's relationship
      to return, because the model's own selection puts its biggest
      over-estimates in its top bucket;
    * **anti-predictiveness**, the realised *return* falling as the claimed
      edge rises, which is the thing the word means and the only one that can
      support "raising the threshold makes it worse".

    Until 2026-09-05 the record carried the first under the key
    `anti_predictive` and the report emitted the threshold sentence from it.
    """
    row = pooled_disagreement(anti)
    assert row["estimate"] < 0.0, row["estimate"]
    assert row["estimate"] == pytest.approx(-0.5, abs=0.45), row["estimate"]

    pooled = anti.get("pooled") or {}
    assert "anti_predictive" not in pooled, (
        "the key that named overconfidence anti-predictiveness must be gone, "
        "not aliased: a reader of the record must not be able to reach the "
        "winner's-curse number by the anti-predictive name"
    )

    curse = pooled.get("overconfidence") or {}
    assert curse["measures"] == FS.OVERCONFIDENCE_LABEL, curse
    assert curse["measurable"], curse
    assert curse["widens_with_claimed_edge"], (
        "an anti-predictive model must show a wider shortfall in its highest "
        f"claimed-edge bucket than in its lowest; got {curse}"
    )
    assert curse["overconfidence_widens_by"] > 0.0

    shape = pooled.get("anti_predictive_return") or {}
    assert shape["measures"] == FS.ANTI_PREDICTIVE_LABEL, shape
    assert shape["measurable"], shape
    assert shape["falls_at_the_top"], (
        "this data-generating process makes the bigger claimed edge the worse "
        f"bet, so the realised return must fall across the buckets; got {shape}"
    )
    for end in ("lowest_bucket", "highest_bucket"):
        bucket = shape[end]
        assert bucket["bets"] >= S.MINIMUM_BETS, (
            f"{end} entered the comparison below the declared floor: {bucket}"
        )
        assert bucket["clusters"] > 0 and bucket["cluster_unit"], bucket

    report = FS.render(anti)
    assert "The model over-estimates more where it claims more." in report
    assert "Realised return by claimed edge — the anti-predictive statistic." in report
    # The threshold sentence rests on the return statistic, and only when the
    # two buckets' clustered intervals are disjoint. On this fixture they are
    # not, and the report must say so rather than borrow the overconfidence
    # shape to make the claim.
    threshold_sentence = "raising the edge threshold the wrong response"
    if shape["demonstrated"]:
        assert threshold_sentence in report
    else:
        assert threshold_sentence not in report
        assert "the fall is not demonstrated" in report


def _measured_with(low_roi, high_roi, *, low_ci, high_ci, looks: int = 1) -> dict:
    """A `measure()`-shaped dict carrying two usable claimed-edge buckets.

    The ROI cell of each bucket is a **real** `stats.RoiInterval` put through
    the module's own `_interval_row`, not a hand-written dict: the standard
    error is recovered from the requested symmetric interval, so the raw
    interval comes back exactly as asked for while `adjusted_low`,
    `adjusted_high` and `verdict` are produced by production code. A fixture
    that spelled the verdict out by hand could print `no demonstrated edge`
    while `RoiInterval.verdict()` had stopped saying it.
    """

    def bucket(low, high, roi, ci):
        standard_error = (ci[1] - ci[0]) / (2.0 * S.Z95)
        interval = S.RoiInterval(
            roi=roi,
            low=roi - S.Z95 * standard_error,
            high=roi + S.Z95 * standard_error,
            bets=400,
            clusters=90,
            standard_error=standard_error,
            looks=looks,
            cluster_unit="day",
        )
        assert interval.low == pytest.approx(ci[0]) and interval.high == pytest.approx(
            ci[1]
        ), "the requested interval must be symmetric about the point estimate"
        return {
            "low": low,
            "high": high,
            "rows": 400,
            "games": 90,
            "enough": True,
            "gap_to_model": 0.0,
            "roi": FS._interval_row(interval, name="realised return"),
        }

    buckets = [
        bucket(0.0, 0.02, low_roi, low_ci),
        bucket(0.20, float("inf"), high_roi, high_ci),
    ]
    return {
        "buckets": buckets,
        "overconfidence": FS.overconfidence_by_bucket(buckets),
        "anti_predictive_return": FS.anti_predictive_return(buckets),
    }


def test_the_threshold_sentence_is_emitted_only_by_disjoint_return_intervals():
    """*"Raising the threshold makes it worse"* is a claim about money.

    So it may be made only from the realised-return statistic, and only when
    the two buckets' clustered intervals do not overlap. Both branches are
    exercised on the same shaped input with only the intervals moved, because
    the defect this closes was a sentence that never looked at them at all.
    """
    disjoint = _measured_with(
        0.06, -0.09, low_ci=(0.02, 0.10), high_ci=(-0.14, -0.04)
    )
    assert disjoint["anti_predictive_return"]["demonstrated"]
    text = "\n".join(FS._anti_predictive_paragraph(disjoint))
    assert "raising the edge threshold the wrong response" in text
    assert "+6.0%" in text and "-9.0%" in text, text
    assert "400 settled wagers across 90 days" in text, (
        "every measured number carries its sample size and the clustering that "
        f"produced it; got {text}"
    )

    overlapping = _measured_with(
        0.06, -0.09, low_ci=(-0.05, 0.17), high_ci=(-0.30, 0.12)
    )
    assert not overlapping["anti_predictive_return"]["demonstrated"]
    text = "\n".join(FS._anti_predictive_paragraph(overlapping))
    assert "the fall is not demonstrated" in text
    assert "raising the edge threshold the wrong response" not in text
    assert "the intervals overlap" in text or "intervals overlap" in text


def test_a_bucket_below_the_declared_floor_gets_no_anti_predictive_comparison():
    """Below `stats.MINIMUM_BETS` settled wagers there is no return figure.

    So there is nothing to compare, and the report says the statistic was not
    measured rather than falling back on the overconfidence column — which is a
    different quantity and was, until 2026-09-05, printed under this one's name.
    """
    thin = [
        {
            "low": 0.0,
            "high": 0.02,
            "rows": 40,
            "games": 20,
            "enough": True,
            "gap_to_model": 0.0,
            "roi": {"value": 0.0, "low": 0.0, "high": 0.0, "rows": 40,
                    "clusters": 20, "cluster_unit": "game",
                    "enough_evidence": False, "verdict": ""},
        }
    ]
    shape = FS.anti_predictive_return(thin)
    assert not shape["measurable"], shape
    text = "\n".join(
        FS._anti_predictive_paragraph({"anti_predictive_return": shape})
    )
    assert "is not measured here" in text
    assert f"{S.MINIMUM_BETS:,} settled wagers" in text
    assert "raising the edge threshold the wrong response" not in text


def _usable_bucket(
    low: float, high: float, roi: float, ci: tuple[float, float], *, looks: int
) -> dict:
    """One usable claimed-edge bucket, its ROI cell built by production code.

    The ROI cell is a real `stats.RoiInterval` through `_interval_row`, for the
    reason `_measured_with` gives: the verdict has to come from production code
    or the test proves only that the fixture and the assertion agree.

    **`looks` is never 1 in a fixture that is about the correction.**
    `RoiInterval.adjusted_low`/`adjusted_high` return `self.low`/`self.high`
    unchanged at `looks <= 1`, so at one look the corrected bounds ARE the raw
    bounds and a test cannot tell which pair the code read. Every rule in this
    module about reading the family-corrected bound and never the raw one is
    invisible to such a fixture: swapping `roi_adjusted_high` for `roi_high`
    passes it.
    """
    standard_error = (ci[1] - ci[0]) / (2.0 * S.Z95)
    interval = S.RoiInterval(
        roi=roi,
        low=roi - S.Z95 * standard_error,
        high=roi + S.Z95 * standard_error,
        bets=400,
        clusters=90,
        standard_error=standard_error,
        looks=looks,
        cluster_unit="day",
    )
    assert interval.low == pytest.approx(ci[0]) and interval.high == pytest.approx(ci[1])
    return {
        "low": low,
        "high": high,
        "rows": 400,
        "games": 90,
        "enough": True,
        "gap_to_model": 0.0,
        "roi": FS._interval_row(interval, name="realised return"),
    }


def _usable_buckets(*specs, looks: int = 24) -> dict:
    """A `measure()`-shaped dict carrying N usable claimed-edge buckets.

    Each spec is `(low, high, roi, ci)`. Two is what the across-bucket
    comparison needs; THREE is the shape that showed the comparison path prints
    only its ends, so a demonstrated deficit in a middle bucket reached neither
    a figure nor a sentence.
    """
    buckets = [_usable_bucket(*spec, looks=looks) for spec in specs]
    return {
        "buckets": buckets,
        "anti_predictive_return": FS.anti_predictive_return(buckets),
    }


def _one_usable_bucket(roi: float, ci: tuple[float, float], *, looks: int = 24) -> dict:
    """A `measure()`-shaped dict carrying exactly ONE usable claimed-edge bucket.

    One is the number the across-bucket comparison cannot use and the sign can.
    Everything else in the cell is empty on purpose: this fixture exists to put
    the report in the state where `measurable` is False and a return figure
    nonetheless exists, and a fixture carrying a second usable bucket would put
    it in the state the comparison already handles.

    `looks` defaults to 24 rather than 1 — see :func:`_usable_bucket`.
    """
    buckets = [_usable_bucket(0.20, float("inf"), roi, ci, looks=looks)]
    return {
        "buckets": buckets,
        "anti_predictive_return": FS.anti_predictive_return(buckets),
    }


def test_a_single_measured_bucket_losing_money_is_reported_as_a_demonstrated_deficit():
    """A sample floor may not pre-empt a measurement that was available.

    `anti_predictive_return` needs two usable buckets to answer *"does the
    return fall as the claimed edge rises"*, and below two it returned four
    keys and threw away everything it had measured. The report then printed a
    sample-size floor — which reads as *we could not see anything* — over a
    bucket carrying 400 settled wagers whose family-corrected interval lies
    entirely below zero. That is `stats.DEMONSTRATED_DEFICIT`: the model did
    worse than no edge, and the one sentence on the page said the sample was
    too small to tell.
    """
    losing = _one_usable_bucket(-0.09, (-0.14, -0.04))
    shape = losing["anti_predictive_return"]
    assert shape["measurable"] is False, (
        "one bucket cannot be compared to another, so the COMPARISON is still "
        f"not measurable; got {shape}"
    )
    assert shape["usable_buckets"] == 1
    assert len(shape["measured_buckets"]) == 1, (
        "the bucket that cleared the floor must survive the early return, or "
        f"no renderer can reach the figure; got {shape}"
    )
    assert shape["demonstrated_deficits"] == 1, shape
    assert shape["worst_bucket"]["verdict"] == S.DEMONSTRATED_DEFICIT, shape

    text = "\n".join(FS._anti_predictive_paragraph(losing))
    assert S.DEMONSTRATED_DEFICIT in text, text
    assert "lost money" in text, text
    # The figure itself, with its sample size and both intervals, not just the
    # word: a verdict with no number under it is the same silence in a louder
    # font.
    assert "-9.0% over 400 settled wagers across 90 days" in text, text
    # Two DIFFERENT pairs, named apart. At `looks=1` they would be the same
    # numbers twice and this pair of assertions would prove nothing about which
    # one the verdict was read off.
    assert "95% interval [-14.0%, -4.0%]" in text, text
    assert "family-corrected [-16.9%, -1.1%] across 24 looks" in text, text
    # And the floor sentence must not be the report's account of why there is
    # no comparison, because a return figure was available and is printed.
    assert "is not measured here" not in text, text
    assert S.NO_DEMONSTRATED_EDGE not in text, (
        "a corrected interval lying entirely below zero is worse than no edge, "
        f"and must never be softened into the phrase for spanning zero; {text}"
    )


def test_a_negative_point_estimate_under_a_wide_interval_says_both_things():
    """Small sample AND a negative point estimate: the report says both.

    The rule this repository states about a sign is that an interval including
    zero is `stats.NO_DEMONSTRATED_EDGE` in those words. That rule is about
    what may be *claimed*; it is not a licence to stop printing the point
    estimate's sign. A bucket returning -9% under an interval from -30% to +12%
    is two facts, and a report that prints only the first invents a loss while
    a report that prints only the second buries one.
    """
    wide = _one_usable_bucket(-0.09, (-0.30, 0.12))
    shape = wide["anti_predictive_return"]
    assert shape["measurable"] is False
    assert shape["negative_point_estimates"] == 1, shape
    assert shape["demonstrated_deficits"] == 0, (
        "the corrected interval spans zero, so nothing is demonstrated; "
        f"got {shape}"
    )
    assert shape["worst_bucket"]["verdict"] == S.NO_DEMONSTRATED_EDGE, shape

    text = "\n".join(FS._anti_predictive_paragraph(wide))
    assert "below zero at the point estimate" in text, text
    assert "-9.0% over 400 settled wagers" in text, text
    assert S.NO_DEMONSTRATED_EDGE in text, text
    assert S.DEMONSTRATED_DEFICIT not in text, (
        "the reserved phrase for an interval excluding zero on the losing side "
        f"must not appear beside one that spans it, even in a negation; {text}"
    )


def test_a_bucket_that_settled_nothing_is_not_reported_as_a_thin_sample():
    """The reason for a silence is counted off the buckets, not asserted.

    This is the shape this lab's own published run is in:
    `data/outputs/cbb_forecast_skill.json` carries eight populated claimed-edge
    buckets holding 293,661 wagers and **no `roi` on any of them** — nothing in
    the frame had been graded to a profit, so no return was ever computed. The
    report printed *"Fewer than two claimed-edge buckets carry 200 settled
    wagers, which is the floor declared in advance"*, ten times, which tells a
    reader the sample was too small to see an answer. The sample was not the
    problem and the floor was never reached or missed.
    """
    buckets = [
        {
            "low": low,
            "high": high,
            "rows": 5_000,
            "games": 900,
            "enough": True,
            "gap_to_model": 0.0,
            # The cause, stamped — this fixture is the WAGERS cause: the frame
            # carried a return column and every row in these buckets is blank
            # in it. Written out because the other cause, a frame with no
            # return column at all, is a different fact and gets a different
            # sentence; see the test below this one.
            "roi_absent_because": FS.ROI_ABSENT_NO_SETTLED_WAGER,
        }
        for low, high in ((0.0, 0.02), (0.02, 0.05), (0.20, float("inf")))
    ]
    shape = FS.anti_predictive_return(buckets)
    assert shape["measurable"] is False
    assert shape["populated_buckets"] == 3
    assert shape["buckets_with_no_settled_wager"] == 3, shape
    assert shape["buckets_with_no_return_column"] == 0, (
        "these buckets sit in a frame that HAS a return column — that is the "
        "fixture — so the shape-reason counter must be empty and the page must "
        f"not print the shape sentence; got {shape}"
    )
    assert shape["buckets_below_the_bet_floor"] == 0, (
        "not one of these buckets carries a settled wager, so not one of them "
        f"is below the settled-wager floor; got {shape}"
    )
    assert shape["measured_buckets"] == [] and shape["worst_bucket"] == {}

    text = "\n".join(FS._anti_predictive_paragraph({"anti_predictive_return": shape}))
    assert "carry no settled wager at all" in text, text
    assert "not a thin sample but an absent one" in text, text
    assert "no realised-return column at all" not in text, (
        "this frame HAS a return column; printing the shape sentence here "
        f"names a cause that is not the cause; got {text}"
    )
    assert f"{S.MINIMUM_BETS:,} settled wagers" not in text, (
        "no bucket here is below the settled-wager floor, so naming that floor "
        f"as the reason states a cause that is not the cause; got {text}"
    )


def test_a_frame_missing_profit_units_still_gets_its_realised_return():
    """**Part two of the fix: the report may not go quiet on a dropped column.**

    `scripts/run_price_backtest.py` projected its graded export onto
    `FS.SKILL_COLUMNS + book + selected` and `profit_units` is in
    `FS.OPTIONAL_SKILL_COLUMNS`, so it was dropped one line before the write —
    on a frame `price_backtest.settled_opinions` had already filtered to rows
    whose `profit_units` is non-null. Every exported row had a realised profit;
    none of them carried it. `edge_buckets` then wrote no `roi` onto any bucket,
    `anti_predictive_return` found nothing usable, and the page said the
    statistic could not be measured.

    The producer now carries the column. This test is the belt: a frame that
    arrives without it, but WITH the two inputs the figure is computed from,
    gets the figure anyway. A statistic that could be computed is computed.
    """
    frame = graded_frame("anti", carry_profit_units=False)
    assert "profit_units" not in frame.columns, "the fixture must not supply it"
    assert {"outcome", "american_odds"} <= set(frame.columns)

    record = FS.build_record(
        FS.SkillInputs(graded=frame, pair_scope="book"), competition=CBB, looks=1
    )
    cells = [record["pooled"], *record["by_tier"]]
    assert cells
    for cell in cells:
        populated = [b for b in cell["buckets"] if int(b.get("rows", 0))]
        assert populated, cell["label"]
        readable = [b for b in populated if b.get("roi")]
        assert readable, (
            f"{cell['label'] or 'pooled'}: every one of its "
            f"{len(populated)} populated buckets came back with no realised "
            "return, on a frame carrying an outcome and a price on every row. "
            "The derivation is not running, and this is exactly the blank "
            "block the finding was about"
        )
        shape = cell["anti_predictive_return"]
        assert shape["buckets_with_no_return_column"] == 0, (
            "a frame this report could derive a return from is not a frame "
            f"with no return column; got {shape}"
        )


def test_a_derived_return_is_the_same_arithmetic_as_a_supplied_one():
    """Equivalence, claimed in the comment and proved here.

    `_with_realised_return` calls `forward_evidence.profit_units` — the
    function `scripts/run_price_backtest.py`'s `grade()` calls — on the row's
    own `outcome` and `american_odds`, then coerces with `pd.to_numeric` as
    `grade()` does. So the derived column is not *close to* the producer's; it
    is the same call on the same two inputs.

    Compared cell for cell **including missingness**, because a won bet at an
    unreadable price is a missing profit and not a zero, and a derivation that
    quietly filled zeroes there would fabricate a number.
    """
    supplied = graded_frame("anti")
    without = supplied.drop(columns=["profit_units"])

    derived, carries = FS._with_realised_return(without)
    assert carries is True
    assert derived["profit_units"].isna().tolist() == (
        supplied["profit_units"].isna().tolist()
    ), "the derived column is missing in different places than the supplied one"
    pd.testing.assert_series_equal(
        pd.to_numeric(derived["profit_units"], errors="coerce"),
        pd.to_numeric(supplied["profit_units"], errors="coerce"),
        check_names=False,
    )
    # And the frame it was given is not mutated: `assign`, never a write-back.
    assert "profit_units" not in without.columns

    # A frame already carrying the column is handed back untouched, so a
    # producer's own value is never silently replaced by a second opinion.
    same, carries = FS._with_realised_return(supplied)
    assert carries is True
    assert same is supplied


def test_a_won_bet_at_an_unreadable_price_derives_a_missing_profit_not_a_zero():
    """**The half of the equivalence claim that nothing could fail on.**

    `_with_realised_return`'s docstring says missingness is part of the claim --
    "a won bet at a price this lab cannot read carries a **missing** profit and
    not a zero, and a derivation that filled zeroes there would fabricate a
    number" -- and the two tests said to pin it compare missingness on frames
    that contain none. The synthetic season yields 1,440 rows with 0 NaN and 0
    unreadable prices; the producer's own export keeps a row only where
    `profit_units` is non-null, and a test one file over asserts exactly that.
    So both pins compared a list of `False` to an identical list of `False`, and
    appending `.fillna(0.0)` to the derivation survived the whole new test set.

    It cannot be reached through the de-vig either -- an unreadable price is
    excluded upstream -- so the only way to test the claim is to call the
    function on the state. That is what this does.

    Mutation: `pd.to_numeric(derived, errors="coerce").fillna(0.0)` in
    `_with_realised_return` -- RED here, and green everywhere else.
    """
    frame = pd.DataFrame(
        {
            "outcome": ["won", "lost", "won", "won", "unsettleable"],
            "american_odds": [-110, -110, "", None, -110],
        }
    )
    derived, carries = FS._with_realised_return(frame)
    assert carries is True
    profits = derived["profit_units"]

    # A won bet at a readable price, and a lost one: both carry a number.
    assert profits.iloc[0] == pytest.approx(10.0 / 11.0)
    assert profits.iloc[1] == pytest.approx(-1.0)

    # A WON bet at a price this lab cannot read. A zero here would say the
    # wager broke even, which is a claim about the money and is false.
    assert pd.isna(profits.iloc[2]), (
        "a won bet at a blank price derived a value; the only honest cell is "
        f"missing, got {profits.iloc[2]!r}"
    )
    assert pd.isna(profits.iloc[3]), profits.iloc[3]
    # And an outcome this lab cannot settle, at a readable price.
    assert pd.isna(profits.iloc[4]), profits.iloc[4]

    assert profits.isna().tolist() == [False, False, True, True, True]
    assert (profits.fillna(-999) != 0.0).all(), (
        "no derived cell may be a zero in this fixture, so a derivation that "
        "filled zeroes for the unreadable rows fails here rather than passing "
        "a comparison of two all-False missingness masks"
    )


def test_a_frame_with_no_return_column_names_the_shape_not_the_wagers():
    """**Part three: the page must print the cause it has, not the cause it assumed.**

    This is the defect, reduced to its smallest true case. A frame with no
    `profit_units` and no `american_odds` to derive one from carries no
    realised return at all — a fact about the frame's SHAPE. The report's
    sentence for that state was *"they carry no settled wager at all — not a
    thin sample but an absent one: nothing in them has been graded to a
    profit"*, which is a fact about the WAGERS, and on the shipped run it was
    false: the frame's 270,504 rows were every one of them settled.

    One counter stood for both causes, so the renderer printed whichever
    sentence it had been written with. The two are counted apart now and this
    test pins WHICH sentence appears — and, just as hard, which does not.
    """
    # Hand-built, because the state has to be *no return column and nothing to
    # derive one from*, and every frame the season fixture makes carries an
    # `american_odds` a return could be computed from. This is the shape the
    # bucket table is handed after the de-vig: a claimed edge, a cluster key,
    # and the three probabilities. No `profit_units`, no `outcome`, no price.
    frame = pd.DataFrame(
        {
            "event_id": [f"e{i % 40:03d}" for i in range(200)],
            "edge": [0.01 if i % 2 else 0.03 for i in range(200)],
            "won": [float(i % 3 == 0) for i in range(200)],
            "model_implied": [0.55] * 200,
            "market_implied": [0.52] * 200,
        }
    )
    assert not {"profit_units", "american_odds", "outcome"} & set(frame.columns)

    buckets = FS.edge_buckets(frame, looks=1)
    populated = [b for b in buckets if int(b.get("rows", 0))]
    assert populated, "the fixture must populate buckets or it tests nothing"
    assert all(
        b.get("roi_absent_because") == FS.ROI_ABSENT_NO_RETURN_COLUMN
        for b in populated
        if b.get("enough")
    ), buckets

    shape = FS.anti_predictive_return(buckets)
    assert shape["measurable"] is False
    assert shape["buckets_with_no_return_column"] == sum(
        1 for b in populated if b.get("enough")
    ), shape
    assert shape["buckets_with_no_settled_wager"] == 0, (
        "nothing here says a single wager went ungraded, and a counter that "
        f"says so is the conflation coming back; got {shape}"
    )

    text = "\n".join(FS._anti_predictive_paragraph({"anti_predictive_return": shape}))
    assert "no realised-return column at all" in text, text
    assert "fact about the shape of the frame handed to this report" in text, text
    assert "not a statement about whether those wagers settled" in text, text
    # The sentences that are FALSE in this state, none of which may appear.
    assert "carry no settled wager at all" not in text, (
        "this frame says nothing whatever about whether its wagers settled; "
        f"got {text}"
    )
    assert "graded to a profit" not in text, text
    assert "not a thin sample but an absent one" not in text, text
    assert f"{S.MINIMUM_BETS:,} settled wagers" not in text, (
        f"no floor was reached or missed here either; got {text}"
    )


def test_the_bucket_table_names_the_shape_too_not_only_the_paragraph():
    """**The other renderer.** The paragraph was fixed; the table was not.

    `_bucket_section` set its verdict cell to the literal `"— (no settled
    wager)"` for any floor-clearing bucket with no `roi`, without consulting
    `roi_absent_because`. So on the frame above -- no return column at all --
    the table would have printed a claim about the WAGERS in every row, sitting
    directly above a paragraph correctly naming the SHAPE. That is the exact
    contradiction the two causes were split to remove, and the split's mutation
    coverage reached only the paragraph, so the table could keep the old false
    wording indefinitely.

    Mutation: put the literal back at the `verdict_cell` assignment in
    `_bucket_section` and this is RED on the first assertion, with the paragraph
    test still green.
    """
    frame = pd.DataFrame(
        {
            "event_id": [f"e{i % 40:03d}" for i in range(200)],
            "edge": [0.01 if i % 2 else 0.03 for i in range(200)],
            "won": [float(i % 3 == 0) for i in range(200)],
            "model_implied": [0.55] * 200,
            "market_implied": [0.52] * 200,
        }
    )
    buckets = FS.edge_buckets(frame, looks=1)
    floor_clearing = [b for b in buckets if b.get("rows") and b.get("enough")]
    assert floor_clearing, "the fixture must clear the row floor or it tests nothing"
    assert all(
        b.get("roi_absent_because") == FS.ROI_ABSENT_NO_RETURN_COLUMN
        for b in floor_clearing
    )

    text = "\n".join(
        FS._bucket_section({"buckets": buckets}, {"minimum_bucket": FS.MINIMUM_BUCKET})
    )
    assert "no return column on this frame" in text, text
    assert "no settled wager" not in text, (
        "the table asserts the wagers cause on a frame that says nothing about "
        f"whether its wagers settled; got:\n{text}"
    )

    # And the other cause still prints its own words, so this is not a rename.
    settled = [dict(b) for b in buckets]
    for b in settled:
        if b.get("roi_absent_because"):
            b["roi_absent_because"] = FS.ROI_ABSENT_NO_SETTLED_WAGER
    other = "\n".join(
        FS._bucket_section({"buckets": settled}, {"minimum_bucket": FS.MINIMUM_BUCKET})
    )
    assert "no settled wager" in other, other
    assert "no return column on this frame" not in other, other

    # A bucket with neither stamp is REFUSED rather than given a default, the
    # same discipline the paragraph applies.
    unstamped = [dict(b) for b in buckets]
    for b in unstamped:
        b.pop("roi_absent_because", None)
    with pytest.raises(FS.ForecastSkillError) as raised:
        FS._bucket_section({"buckets": unstamped}, {"minimum_bucket": FS.MINIMUM_BUCKET})
    assert "roi_absent_because" in str(raised.value)


def test_restating_a_record_keeps_the_reason_each_silent_bucket_gave():
    """The refusal must not fire on this report's own restatement path.

    `restated()` re-derives `anti_predictive_return` from the stored buckets at
    a wider family correction, so those buckets pass through `restate_tree`
    before they are counted again. If a restatement dropped
    `roi_absent_because`, the guard that refuses an unstamped bucket would turn
    every re-render into an exception — a guard whose floor came from the wrong
    place, which is this repository's most-repeated defect and not one to add
    while fixing another.
    """
    frame = graded_frame("anti")
    frame["profit_units"] = float("nan")

    record = FS.build_record(
        FS.SkillInputs(graded=frame, pair_scope="book"), competition=CBB, looks=1
    )
    before = record["pooled"]["anti_predictive_return"]
    assert before["buckets_with_no_settled_wager"] > 0, (
        "the fixture must put at least one bucket in the silent state or this "
        f"test restates nothing; got {before}"
    )

    wider = FS.restated(record, looks=24, record_name="forecast skill")
    after = wider["pooled"]["anti_predictive_return"]
    assert after["buckets_with_no_settled_wager"] == (
        before["buckets_with_no_settled_wager"]
    ), (before, after)
    assert after["buckets_with_no_return_column"] == 0, after
    # And it renders, which is the thing the exception would have stopped.
    assert "not measured here" in FS.render(wider)


def test_a_record_written_before_the_split_is_refused_rather_than_rendered():
    """An old record cannot say which cause it was measured under.

    A version 5 record carries `buckets_with_no_return_figure`, one number for
    two unrelated facts. Rendering it through `.get(..., 0)` would print
    neither sentence — the silence would simply lose its reason — or, worse,
    print whichever the renderer defaulted to. Neither is honest, so the
    renderer refuses and names the keys it does not have.
    """
    stale = {
        "measures": FS.ANTI_PREDICTIVE_LABEL,
        "usable_buckets": 0,
        "populated_buckets": 8,
        "measurable": False,
        "measured_buckets": [],
        "buckets_with_no_return_figure": 8,
        "buckets_below_the_bet_floor": 0,
        "buckets_below_the_row_floor": 0,
    }
    with pytest.raises(FS.ForecastSkillError) as raised:
        FS._anti_predictive_paragraph({"anti_predictive_return": stale})
    message = str(raised.value)
    assert "buckets_with_no_return_column" in message
    assert "buckets_with_no_settled_wager" in message
    assert "Re-run the regression" in message


def test_a_bucket_that_records_no_reason_for_its_silence_is_refused():
    """The cause comes from the code that saw it, or it comes from nowhere.

    `edge_buckets` stamps `roi_absent_because` because it is the only place
    that holds the frame's shape and the bucket's rows at the same time. A
    default in `anti_predictive_return` would let a bucket built anywhere else
    be counted under whichever cause the reader of the count assumed — which is
    the whole mechanism of the defect, one layer further in.
    """
    with pytest.raises(FS.ForecastSkillError) as raised:
        FS.anti_predictive_return(
            [
                {
                    "low": 0.0,
                    "high": 0.02,
                    "rows": 5_000,
                    "games": 900,
                    "enough": True,
                    "gap_to_model": 0.0,
                }
            ]
        )
    assert "roi_absent_because" in str(raised.value)


def test_a_deficit_visible_only_before_the_correction_is_not_called_one():
    """The corrected bound, not the raw one — and a fixture that can tell them apart.

    `RoiInterval.adjusted_low`/`adjusted_high` return the raw bounds unchanged
    at `looks <= 1`, so every fixture written at one look leaves this rule
    untested: `float(b["roi_adjusted_high"]) < 0.0` and
    `float(b["roi_high"]) < 0.0` are the same test on the same number, and
    swapping one for the other passes.

    The bucket below is the case that separates them. Its RAW interval is
    `[-10.0%, -1.0%]` — entirely below zero — and its family-corrected interval
    over 24 looks spans zero. A report that read the raw bound would announce a
    `demonstrated deficit` on a bucket whose corrected interval includes zero,
    which is the reserved phrase used for a claim the correction withdrew.
    """
    borderline = _one_usable_bucket(-0.055, (-0.10, -0.01), looks=24)
    shape = borderline["anti_predictive_return"]
    bucket = shape["measured_buckets"][0]
    assert bucket["roi_high"] < 0.0, (
        "the RAW interval must lie entirely below zero, or this fixture cannot "
        f"tell the two bounds apart; got {bucket}"
    )
    assert bucket["roi_adjusted_high"] > 0.0, (
        "and the CORRECTED interval must span zero, which is the whole of the "
        f"distinction; got {bucket}"
    )
    assert shape["demonstrated_deficits"] == 0, (
        "counted off the corrected high bound; the raw one would say 1 here "
        f"and that is the defect; got {shape}"
    )
    assert shape["deficit_buckets"] == [], shape
    assert shape["negative_point_estimates"] == 1, shape

    text = "\n".join(FS._anti_predictive_paragraph(borderline))
    assert S.NO_DEMONSTRATED_EDGE in text, text
    assert S.DEMONSTRATED_DEFICIT not in text, (
        "a bucket whose corrected interval spans zero may not carry the phrase "
        f"reserved for one that does not; got {text}"
    )
    assert "below zero at the point estimate" in text, text
    assert "lost money" not in text, text


def test_a_demonstrated_deficit_in_a_MIDDLE_bucket_reaches_the_compared_page():
    """Three usable buckets: the comparison prints two cells and there are three.

    `_anti_predictive_paragraph`'s `measurable: True` branch prints
    `lowest_bucket` and `highest_bucket` and nothing else, and it did not call
    :func:`_negative_return_lines` at all — on the written justification that
    *"the sign is on the page there already, in the verdict beside each cell"*.
    That is true of two cells. With three usable buckets and the loss in the
    middle one, the record carried `demonstrated_deficits: 1` and the page
    carried no figure for it, no verdict for it and no sentence about it.

    This is the branch the lab occupies the moment wagers start settling, so it
    is not a corner: it is the ordinary case with one more bucket in it.
    """
    three = _usable_buckets(
        (0.0, 0.02, 0.02, (0.01, 0.03)),
        (0.02, 0.05, -0.15, (-0.20, -0.10)),
        (0.20, float("inf"), 0.01, (0.0, 0.02)),
    )
    shape = three["anti_predictive_return"]
    assert shape["measurable"] is True and shape["usable_buckets"] == 3, shape
    assert shape["falls_at_the_top"] is True and shape["demonstrated"] is False, (
        "the ENDS must overlap, or the paragraph takes a different branch and "
        f"this test is about a different page; got {shape}"
    )
    assert shape["demonstrated_deficits"] == 1, shape
    middle = shape["deficit_buckets"][0]
    assert (middle["low"], middle["high"]) == (0.02, 0.05), (
        f"the deficit is the MIDDLE bucket, which is the point; got {middle}"
    )

    text = "\n".join(FS._anti_predictive_paragraph(three))
    assert "the fall is not demonstrated" in text, text
    assert "+2% to +5%" in text, (
        "the middle bucket's own label has to reach the page, or the sentence "
        f"below names a bucket the reader cannot find; got {text}"
    )
    assert "-15.0% over 400 settled wagers" in text, text
    assert "family-corrected [-22.9%, -7.1%]" in text, text
    assert S.DEMONSTRATED_DEFICIT in text, text
    assert "lost money, and the loss survives the correction" in text, text
    # And the two end cells are each printed exactly once: this paragraph
    # prints them in its head, and the sign lines must not reprint them.
    for label in ("+0% to +2%", "+20% and above"):
        assert text.count(f"The {label} bucket returned") <= 1, text


def test_the_deficit_named_is_the_bucket_that_demonstrated_it_not_the_worst_return():
    """`worst_bucket` and the deficit count are selected by different numbers.

    `worst_bucket` is the lowest POINT ESTIMATE; `demonstrated_deficits` counts
    the corrected HIGH BOUND below zero. They are not the same bucket, and a
    page that printed the first beside a claim justified by the second put a
    figure reading `no demonstrated edge` directly above the sentence *"the
    model's own claimed edge selected wagers that lost money"*.

    Here A returns -20% under a corrected interval spanning zero and B returns
    -5% under one entirely below it.
    """
    two = _usable_buckets(
        (0.0, 0.02, -0.20, (-0.38, -0.02)),
        (0.02, 0.05, -0.05, (-0.075, -0.025)),
    )
    shape = two["anti_predictive_return"]
    worst = shape["worst_bucket"]
    assert (worst["low"], worst["high"]) == (0.0, 0.02), worst
    assert worst["verdict"] == S.NO_DEMONSTRATED_EDGE, (
        "the worst-returning bucket demonstrates nothing, which is what makes "
        f"it the wrong bucket to justify a loss with; got {worst}"
    )
    assert shape["demonstrated_deficits"] == 1, shape
    named = shape["deficit_buckets"][0]
    assert (named["low"], named["high"]) == (0.02, 0.05), named
    assert named["verdict"] == S.DEMONSTRATED_DEFICIT, named

    text = "\n".join(FS._anti_predictive_paragraph(two))
    claim = [line for line in text.splitlines() if "lost money" in line]
    assert len(claim) == 1, text
    assert "+2% to +5%" in claim[0], (
        "the sentence must name the bucket whose corrected interval is below "
        f"zero, not the one with the lowest return; got {claim[0]}"
    )
    assert "+0% to +2%" not in claim[0], claim[0]
    assert "-5.0% over 400 settled wagers" in text, (
        f"and that bucket's own figure has to be on the page; got {text}"
    )


def test_the_unusable_reasons_and_the_usable_count_close_against_populated():
    """The identity, in the form that is true.

    `anti_predictive_return`'s docstring claimed `buckets_below_the_row_floor`,
    `buckets_with_no_return_figure` and `buckets_below_the_bet_floor` were
    *"disjoint and exhaust `populated`"*. They exhaust `populated` minus the
    usable ones, and the difference is not academic: on the single-usable-bucket
    fixture this whole change was written for, all three are zero against a
    populated count of one. A reader who trusted the docstring and wrote
    `below_row + no_return + below_bet == populated_buckets` got a red test on
    the patch's own headline case.

    **The middle term has since become two.** `buckets_with_no_return_figure`
    stood for a frame with no return column AND for a bucket whose wagers are
    all unsettled — two unrelated facts, one counter — and the renderer printed
    the second whichever was true. They are counted apart now, so the identity
    has five terms, and the two new ones must each be exercised or the split is
    untested arithmetic.

    Five shapes, so the check is not satisfied by one arrangement of zeroes.
    """
    shapes = {
        "one usable and nothing else": _one_usable_bucket(-0.09, (-0.14, -0.04))[
            "anti_predictive_return"
        ],
        "three usable": _usable_buckets(
            (0.0, 0.02, 0.02, (0.01, 0.03)),
            (0.02, 0.05, -0.15, (-0.20, -0.10)),
            (0.20, float("inf"), 0.01, (0.0, 0.02)),
        )["anti_predictive_return"],
        "nothing settled anywhere": FS.anti_predictive_return(
            [
                {
                    "low": low,
                    "high": high,
                    "rows": 5_000,
                    "games": 900,
                    "enough": True,
                    "gap_to_model": 0.0,
                    "roi_absent_because": FS.ROI_ABSENT_NO_SETTLED_WAGER,
                }
                for low, high in ((0.0, 0.02), (0.02, 0.05), (0.20, float("inf")))
            ]
        ),
        "no return column anywhere": FS.anti_predictive_return(
            [
                {
                    "low": low,
                    "high": high,
                    "rows": 5_000,
                    "games": 900,
                    "enough": True,
                    "gap_to_model": 0.0,
                    "roi_absent_because": FS.ROI_ABSENT_NO_RETURN_COLUMN,
                }
                for low, high in ((0.0, 0.02), (0.02, 0.05))
            ]
        ),
        "below the row floor": FS.anti_predictive_return(
            [
                {
                    "low": 0.0,
                    "high": 0.02,
                    "rows": 3,
                    "games": 2,
                    "enough": False,
                    "gap_to_model": 0.0,
                }
            ]
        ),
    }
    seen = set()
    for name, shape in shapes.items():
        parts = (
            shape["buckets_below_the_row_floor"],
            shape["buckets_with_no_return_column"],
            shape["buckets_with_no_settled_wager"],
            shape["buckets_below_the_bet_floor"],
            shape["usable_buckets"],
        )
        assert sum(parts) == shape["populated_buckets"], (
            f"{name}: the four unusable reasons plus the usable count must "
            f"close against the populated count; got {shape}"
        )
        seen.add(parts)
    assert len(seen) == len(shapes), (
        "five fixtures that produce the same five numbers test one arrangement "
        f"five times; got {seen}"
    )
    # The two halves of the old conflated counter are each non-zero somewhere,
    # or the split is arithmetic nobody exercised.
    assert shapes["nothing settled anywhere"]["buckets_with_no_settled_wager"] == 3
    assert shapes["nothing settled anywhere"]["buckets_with_no_return_column"] == 0
    assert shapes["no return column anywhere"]["buckets_with_no_return_column"] == 2
    assert shapes["no return column anywhere"]["buckets_with_no_settled_wager"] == 0
    # And the shorter claim the docstring used to make is FALSE on the first
    # fixture, which is why it was corrected rather than kept as a shorthand.
    one = shapes["one usable and nothing else"]
    assert (
        one["buckets_below_the_row_floor"]
        + one["buckets_with_no_return_column"]
        + one["buckets_with_no_settled_wager"]
        + one["buckets_below_the_bet_floor"]
        != one["populated_buckets"]
    ), one


def test_every_printed_return_interval_carries_its_verdict_in_the_mandated_words():
    """An interval printed with no verdict is a verdict the reader supplies.

    The vocabulary is not decoration. An interval that includes zero reads
    `stats.NO_DEMONSTRATED_EDGE` in exactly those words; `demonstrated edge` and
    `demonstrated deficit` are reserved for intervals excluding zero on the
    respective side **after** the family-wise correction. Until 2026-09-05 the
    anti-predictive paragraph computed each bucket's verdict, dropped it, and
    printed the bare interval — so a bucket at `-14.3% [-23.9%, -4.6%]` read as
    a demonstrated deficit to any reader who did the arithmetic, and at 24 looks
    it is not one.
    """
    both_span_zero = _measured_with(
        0.06, -0.09, low_ci=(-0.05, 0.17), high_ci=(-0.30, 0.12)
    )
    text = "\n".join(FS._anti_predictive_paragraph(both_span_zero))
    assert text.count(S.NO_DEMONSTRATED_EDGE) == 2, (
        "both buckets' intervals include zero, so both must read "
        f"{S.NO_DEMONSTRATED_EDGE!r} in exactly those words; got {text}"
    )
    assert S.DEMONSTRATED_EDGE not in text.replace(S.NO_DEMONSTRATED_EDGE, "")
    assert S.DEMONSTRATED_DEFICIT not in text

    # And the reserved words are reachable: a bucket whose corrected interval
    # excludes zero on the losing side is a demonstrated deficit and is allowed
    # to say so. A vocabulary test that only ever proves the negative would pass
    # on a renderer that printed the same phrase unconditionally.
    disjoint = _measured_with(0.06, -0.09, low_ci=(0.02, 0.10), high_ci=(-0.14, -0.04))
    text = "\n".join(FS._anti_predictive_paragraph(disjoint))
    assert S.DEMONSTRATED_EDGE in text, text
    assert S.DEMONSTRATED_DEFICIT in text, text
    assert S.NO_DEMONSTRATED_EDGE not in text, text

    # Every printed interval, both of them, and each beside its own sample size.
    for bucket in ("lowest_bucket", "highest_bucket"):
        cell = disjoint["anti_predictive_return"][bucket]
        assert cell["verdict"], cell
        assert cell["verdict"] in text, cell
    assert text.count("400 settled wagers across 90 days") == 2, text


def test_the_anti_predictive_comparison_is_corrected_for_the_size_of_the_search():
    """The comparison is one more look, and it is corrected like every other.

    Until 2026-09-05 `demonstrated` read the raw 95% intervals while
    `edge_buckets` was being handed the ledger's cumulative `looks` and every
    other interval in the report was corrected by it. So the one comparison the
    threshold sentence rests on was the one made before the search was counted.

    Same point estimates, same raw intervals, only the look count moved: at one
    look the two intervals are disjoint and the sentence is earned; at two
    hundred looks the corrected intervals overlap and it is not.
    """
    at_one_look = _measured_with(
        0.06, -0.09, low_ci=(0.02, 0.10), high_ci=(-0.14, -0.04), looks=1
    )
    at_two_hundred = _measured_with(
        0.06, -0.09, low_ci=(0.02, 0.10), high_ci=(-0.14, -0.04), looks=200
    )

    one = at_one_look["anti_predictive_return"]
    many = at_two_hundred["anti_predictive_return"]
    assert one["looks"] == 1 and many["looks"] == 200
    assert one["demonstrated_before_correction"], one
    assert many["demonstrated_before_correction"], (
        "the raw intervals are identical in both runs, so the uncorrected "
        f"comparison must be unchanged; got {many}"
    )
    assert one["demonstrated"], one
    assert not many["demonstrated"], (
        "two hundred looks must widen the intervals until they overlap; got "
        f"{many}"
    )
    for end in ("lowest_bucket", "highest_bucket"):
        raw = many[end]["roi_high"] - many[end]["roi_low"]
        corrected = many[end]["roi_adjusted_high"] - many[end]["roi_adjusted_low"]
        assert corrected > raw, (
            f"{end}: the correction must widen, never narrow; {many[end]}"
        )

    text = "\n".join(FS._anti_predictive_paragraph(at_two_hundred))
    assert "raising the edge threshold the wrong response" not in text, text
    assert "the fall is not demonstrated" in text
    assert "the correction for the size of the search is what closed the gap" in text
    # Both figures printed and labelled apart, per bucket, in both directions.
    assert "95% interval [+2.0%, +10.0%]" in text, text
    assert "family-corrected [" in text and "across 200 looks" in text, text
    assert text.count(S.NO_DEMONSTRATED_EDGE) == 2, (
        "at two hundred looks neither bucket's corrected interval excludes "
        f"zero; got {text}"
    )

    earned = "\n".join(FS._anti_predictive_paragraph(at_one_look))
    assert "raising the edge threshold the wrong response" in earned
    assert "across 1 look" in earned, earned


def test_the_bucket_table_prints_a_sample_size_beside_every_frequency():
    """Every measured number carries its `n`, and a thin bucket carries no number.

    Checked on the rendered rows rather than on the record, because the record
    computes a frequency for every non-empty bucket and it is `render` that has
    to withhold the thin ones. A point estimate over nine observations invites a
    reader to follow the shape of the line rather than the intervals around it.

    A smaller season than the module fixture, deliberately: it is what leaves
    the extreme claimed-edge bucket below `MINIMUM_BUCKET`, and a test of the
    withholding rule needs a bucket that is actually withheld.
    """
    anti = record_for("anti", games=40)
    buckets = (anti.get("pooled") or {}).get("buckets") or []
    assert buckets
    thin = [b for b in buckets if 0 < b["rows"] < FS.MINIMUM_BUCKET]
    assert thin, "the fixture must produce at least one bucket below the floor"

    table = [
        line
        for line in FS.render(anti).splitlines()
        if line.startswith("| below ") or line.startswith("| +") or line.startswith("| -")
    ]
    assert table
    for line in table:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        label, wagers, games = cells[0], cells[1], cells[2]
        assert wagers and games, line
        count = int(wagers.replace(",", "")) if wagers != "0" else 0
        if 0 < count < FS.MINIMUM_BUCKET:
            assert "%" not in "".join(cells[3:]), (
                f"a bucket of {count} printed a frequency: {line}"
            )
        if count >= FS.MINIMUM_BUCKET:
            assert "%" in cells[3] and "%" in cells[5], line
            assert "pp" in cells[6], label


def test_no_bucket_row_prints_a_return_interval_without_its_verdict():
    """The bucket table's realised-return column, read cell by cell.

    The column printed `-14.3% [-23.9%, -4.6%]` and stopped there. That interval
    excludes zero on the losing side and any reader doing the arithmetic calls
    it a demonstrated deficit — but the family-wise correction over this run's
    looks widens it to `[-29.4%, +0.9%]`, which includes zero, so the only
    permitted reading is `stats.NO_DEMONSTRATED_EDGE`. Raw and corrected are now
    printed apart and the verdict is printed beside them.
    """
    anti = record_for("anti", looks=24)
    report = FS.render(anti)
    header = [
        line for line in report.splitlines() if line.startswith("| Claimed edge |")
    ]
    assert header, report
    columns = [cell.strip() for cell in header[0].strip("|").split("|")]
    assert columns[-4:] == [
        "Realised return",
        "95% interval",
        "Family-corrected",
        "Verdict",
    ], columns

    rows = [
        line
        for line in report.splitlines()
        if line.startswith(("| below ", "| +", "| -"))
    ]
    assert rows
    checked = 0
    saw_correction_change_the_verdict = False
    for line in rows:
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert len(cells) == len(columns), line
        _return, raw, corrected, verdict = cells[-4:]
        if raw == "—":
            # No return figure at all: the verdict says why, or the bucket is
            # empty. Either way no interval is printed without one.
            assert verdict, line
            continue
        assert verdict in {
            S.NO_DEMONSTRATED_EDGE,
            S.DEMONSTRATED_EDGE,
            S.DEMONSTRATED_DEFICIT,
        }, f"a printed interval carries a verdict in the reserved words: {line}"
        assert corrected != "—" and "looks" in corrected, (
            f"the family-corrected interval must be printed beside the raw one "
            f"and labelled: {line}"
        )
        assert "settled" in _return, (
            f"every measured number carries its sample size: {line}"
        )
        if raw.startswith("[-") and raw.endswith("]") and "+" not in raw:
            # A raw interval wholly below zero whose corrected interval spans
            # it: the case the old column let a reader misread.
            if verdict == S.NO_DEMONSTRATED_EDGE:
                saw_correction_change_the_verdict = True
        checked += 1
    assert checked >= 3, f"too few return rows to mean anything: {rows}"
    assert saw_correction_change_the_verdict, (
        "this fixture must contain at least one bucket whose raw interval "
        "excludes zero and whose corrected interval does not, or the test "
        "cannot show that the verdict reads the corrected one"
    )


def test_no_scorable_wager_falls_outside_every_bucket(anti):
    """A bucket table shorter than its population still looks complete."""
    measured = anti["pooled"]
    assert measured["rows_outside_every_bucket"] == 0
    assert sum(b["rows"] for b in measured["buckets"]) == measured["rows"]


# ---------------------------------------------------------------------------
# The standard error is the clustered one
# ---------------------------------------------------------------------------


def _naive_standard_errors(design: np.ndarray, response: np.ndarray) -> np.ndarray:
    """Classical OLS standard errors, computed here as the thing NOT to use.

    The reference the clustered sandwich has to beat. Written in the test rather
    than in the module on purpose: it is the wrong answer, and the module should
    contain no way to ask for it.
    """
    n, k = design.shape
    bread = np.linalg.inv(design.T @ design)
    beta = bread @ (design.T @ response)
    residual = response - design @ beta
    sigma_squared = float(residual @ residual) / (n - k)
    return np.sqrt(np.diag(bread * sigma_squared))


def _design_and_response(frame: pd.DataFrame):
    priced, _ = FS.devig(frame, scope="book")
    population, _ = FS.scorable(priced)
    design = np.column_stack(
        [
            np.ones(len(population)),
            population["market_implied"].to_numpy(dtype=float),
            population["disagreement"].to_numpy(dtype=float),
        ]
    )
    return design, population["won"].to_numpy(dtype=float), population


def _cluster_bootstrap_standard_errors(
    design: np.ndarray, response: np.ndarray, groups, *, draws: int = 500, seed: int = 3
) -> np.ndarray:
    """The ground truth: resample whole games with replacement and refit.

    The same instrument `test_clustered_interval_is_not_too_narrow.py` uses on
    `stats.interval_by_cluster`, applied to a regression coefficient. An
    analytic estimator and a resampling one should not disagree by more than
    noise, and when they do it is the analytic one that is wrong.
    """
    rng = np.random.default_rng(seed)
    positions: dict[str, list[int]] = {}
    for index, key in enumerate(groups):
        positions.setdefault(str(key), []).append(index)
    keys = list(positions)
    estimates = []
    for _ in range(draws):
        drawn = rng.integers(0, len(keys), len(keys))
        rows = np.concatenate([positions[keys[j]] for j in drawn])
        estimates.append(
            np.linalg.lstsq(design[rows], response[rows], rcond=None)[0]
        )
    return np.std(np.asarray(estimates), axis=0, ddof=1)


@pytest.mark.parametrize("shared_outcome", [False, True])
def test_the_clustered_standard_error_agrees_with_a_cluster_bootstrap(shared_outcome):
    """The sandwich against the ground truth, on both correlation structures.

    `shared_outcome=True` is the pathological case — every wager in a game
    settles the same way — and `False` is the ordinary one, where the two sides
    of each wager are still one observation seen twice. The analytic estimator
    has to track the bootstrap in both.
    """
    frame = graded_frame("noise", shared_outcome=shared_outcome, seed=5)
    design, response, population = _design_and_response(frame)
    _, clustered, clusters = FS.cluster_robust(
        design, response, population["event_id"].astype(str)
    )
    truth = _cluster_bootstrap_standard_errors(
        design, response, population["event_id"].astype(str)
    )
    assert clusters == population["event_id"].nunique()
    for index, name in enumerate(("intercept", "market_implied", "disagreement")):
        assert abs(clustered[index] - truth[index]) / truth[index] < 0.15, (
            f"{name}: sandwich {clustered[index]:.5f} against bootstrap "
            f"{truth[index]:.5f}"
        )


def test_a_naive_standard_error_would_be_materially_too_narrow():
    """One game is one observation when a game's wagers settle together.

    The football lab's forward ledger computed a cluster standard error at
    `s/G` where it should have been `s/sqrt(G)` — **10.3x too narrow** on the
    one report that grows all season, and nothing about the output looked wrong.
    A narrow interval is how *no demonstrated edge* quietly becomes a claim, so
    the naive alternative is computed here and shown to be the wrong answer.
    """
    frame = graded_frame("noise", shared_outcome=True, seed=5)
    design, response, population = _design_and_response(frame)
    _, clustered, _ = FS.cluster_robust(
        design, response, population["event_id"].astype(str)
    )
    naive = _naive_standard_errors(design, response)

    assert np.all(naive < clustered), (
        "a naive per-row standard error must be narrower than the clustered "
        f"one on every coefficient; got naive {naive} against {clustered}"
    )
    assert clustered[0] > 1.5 * naive[0], (
        "when every wager in a game settles together, the clustered standard "
        f"error must be much larger than the naive one; got {clustered[0]:.5f} "
        f"against {naive[0]:.5f}"
    )


def test_the_reported_standard_error_is_the_wider_of_game_and_day():
    """`stats.interval_two_way`'s doctrine, applied to a regression coefficient.

    Dependence runs within a game, which makes the game canonical. But a model
    with a shared daily component makes a whole slate correlated, and this
    module cannot know in advance which applies — so it computes both and
    reports the wider. Choosing the narrower after seeing both is the move the
    rest of the repository exists to prevent.
    """
    fitted = FS.fit(
        FS.scorable(FS.devig(graded_frame("noise"), scope="book")[0])[0], looks=1
    )
    assert fitted["fitted"]
    by_game = fitted["standard_errors_by_game"]
    by_day = fitted["standard_errors_by_day"]
    for index, row in enumerate(fitted["coefficients"]):
        assert row["standard_error"] == pytest.approx(
            max(by_game[index], by_day[index])
        ), f"{row['name']} did not report the wider of the two cluster units"
        assert row["cluster_unit"] in ("game", "day")


def test_a_constant_disagreement_is_undefined_rather_than_zero():
    """A model that never disagrees is a wiring fact, not a finding of zero.

    Publishing `0.000` there would publish "the model adds nothing" when what
    happened is that no probability ever differed from the price — the exact
    ambiguity that made the football lab's zero-bets backtest read as a finding
    about the model when its price columns had never been built.
    """
    frame = graded_frame("noise", games=40)
    priced, _ = FS.devig(frame, scope="book")
    population, _ = FS.scorable(priced)
    flattened = population.assign(
        model_implied=population["market_implied"],
        disagreement=0.0,
    )
    fitted = FS.fit(flattened, looks=1)
    assert fitted["fitted"] is False
    assert "rank deficient" in fitted["reason"]
    assert "undefined rather than" in fitted["reason"]
    assert "coefficients" not in fitted


# ---------------------------------------------------------------------------
# The words `demonstrated edge` cannot reach the wrong number
# ---------------------------------------------------------------------------


def _coefficient(**kwargs) -> FS.Coefficient:
    base = dict(
        name="market_implied",
        estimate=0.97,
        standard_error=0.01,
        rows=50_000,
        clusters=5_000,
        cluster_unit="game",
        looks=1,
        null_value=1.0,
        answers_the_question=False,
    )
    base.update(kwargs)
    return FS.Coefficient(**base)


def test_the_market_coefficient_can_never_be_called_a_demonstrated_edge():
    """0.97 excludes zero on the positive side. That is not an edge.

    `stats.RoiInterval.verdict` reads a sign, and a predicate that never asked
    what the null was would announce a demonstrated edge on a number describing
    the **market**. This is the defect `test_the_headline_reads_the_sign.py`
    pins, arriving through a door that file does not watch, and it is closed by
    making the call raise rather than by remembering not to make it.
    """
    market = _coefficient()
    with pytest.raises(ValueError) as raised:
        market.verdict()
    assert "not the coefficient that answers the question" in str(raised.value)
    assert S.DEMONSTRATED_EDGE not in market.null_note()
    assert "1.0" in market.null_note()


def test_the_intercept_can_never_be_called_a_demonstrated_edge_either():
    """A positive intercept excluding zero is a level miscalibration, not an edge."""
    intercept = _coefficient(
        name="intercept", estimate=0.08, null_value=0.0, answers_the_question=False
    )
    with pytest.raises(ValueError):
        intercept.verdict()
    note = intercept.null_note()
    assert S.DEMONSTRATED_EDGE not in note
    assert S.DEMONSTRATED_DEFICIT not in note
    assert "excludes zero" in note


def test_only_the_disagreement_row_carries_a_verdict_in_the_record(noise):
    """One row per fit carries the word, so a reader cannot quote the market's."""
    for measured in list(noise["by_tier"]) + [noise["pooled"]]:
        rows = (measured.get("fit") or {}).get("coefficients") or []
        with_verdict = [r for r in rows if "verdict" in r]
        assert [r["name"] for r in with_verdict] == ["disagreement"], (
            "exactly one coefficient's sign is a claim about the model's skill"
        )
        for row in rows:
            assert "reading" in row, "every row must be describable"


def test_the_rendered_report_never_attaches_an_edge_verdict_to_the_market(truth):
    """End to end: the sentence a human reads, on a run that DOES have an edge.

    The positive-control fixture is used deliberately. On a null run no row says
    `demonstrated edge` at all and the test would pass for the wrong reason; on
    this one the disagreement row does say it, so the assertion that the market
    row does not is actually load-bearing.
    """
    report = FS.render(truth)
    assert S.DEMONSTRATED_EDGE in report, "the positive control must say it somewhere"
    for line in report.splitlines():
        if line.startswith("| market_implied |") or line.startswith("| intercept |"):
            assert S.DEMONSTRATED_EDGE not in line, line
            assert S.DEMONSTRATED_DEFICIT not in line, line


# ---------------------------------------------------------------------------
# Brier
# ---------------------------------------------------------------------------


def test_a_model_that_is_measurably_better_is_not_called_a_deficit(truth):
    """The sign of the Brier advantage is chosen so the verdict reads correctly.

    A Brier score is better when it is **lower**. Handing a lower-is-better
    quantity to a predicate that says "edge" when the number is positive would
    announce a demonstrated edge on a model measurably worse than the price, and
    a demonstrated deficit on one that is better. So the quantity clustered is
    `brier_market - brier_model`, and this pins it on data where the model is
    genuinely better.
    """
    scores = truth["pooled"]["brier"]
    assert scores["model"] < scores["market_devigged"], (
        "the positive-control model must actually score better, or this test "
        "cannot distinguish the sign convention from luck"
    )
    advantage = scores["advantage_over_devigged"]
    assert advantage["value"] > 0.0, "better model must give a positive advantage"
    assert advantage["verdict"] != S.DEMONSTRATED_DEFICIT
    assert scores["skill_vs_devigged"] > 0.0


def test_a_model_that_is_worse_than_the_price_is_not_called_an_edge(anti):
    scores = anti["pooled"]["brier"]
    assert scores["model"] > scores["market_devigged"]
    advantage = scores["advantage_over_devigged"]
    assert advantage["value"] < 0.0
    assert advantage["verdict"] != S.DEMONSTRATED_EDGE


def test_the_raw_market_column_keeps_the_vig_and_is_scored_with_a_handicap(noise):
    """The raw implied probability over-estimates every side, by construction.

    Two sides at -110 imply 52.4% each and sum to 104.8%. Scoring that against
    outcomes handicaps it, which is why it is printed: if the model loses to the
    handicapped market anyway, there is no de-vig argument left to have.
    """
    scores = noise["pooled"]["brier"]
    assert scores["market_raw"] > scores["market_devigged"], (
        "with the hold left in, the market's Brier score must be worse than the "
        "de-vigged one — otherwise the 'handicap' claim in the report is false"
    )
    assert scores["loses_to_the_handicapped_market"] is True
    report = FS.render(noise)
    assert "still has the vig in it" in report
    assert "if the model loses to the handicapped market, that is decisive" in (
        report.lower()
    )
    assert "The model loses to the market even with the vig left in." in report


def test_the_base_rate_reference_is_printed_beside_both_scores(noise):
    """Climatology, so a reader can see how much of either score is the base rate."""
    scores = noise["pooled"]["brier"]
    assert 0.0 < scores["base_rate"] < 1.0
    assert scores["base_rate_reference"] == pytest.approx(
        scores["base_rate"] * (1 - scores["base_rate"]), abs=1e-9
    )
    assert "the base rate" in FS.render(noise)


# ---------------------------------------------------------------------------
# The de-vig
# ---------------------------------------------------------------------------


def _pair(selection: str, line, odds: float, *, book: str = "dk", event: str = "e1") -> dict:
    return {
        "event_id": event,
        "slate_date": "2027-01-05",
        "market": "alternate_spread",
        "segment": FULL_GAME,
        "player": "",
        "selection": selection,
        "line": line,
        "american_odds": odds,
        "book": book,
        "tier": Tier.HIGH_MAJOR.value,
        "model_probability": 0.5,
        "outcome": "won",
    }


def test_the_devig_normalises_the_two_sides_to_one_and_records_the_hold():
    """Multiplicative normalisation, and the hold it removed is measured."""
    frame = pd.DataFrame(
        [
            _pair("home", -3.5, american_odds_for(0.55 * OVERROUND)),
            _pair("away", 3.5, american_odds_for(0.45 * OVERROUND)),
        ]
    )
    priced, census = FS.devig(frame, scope="book")
    assert census.devigged == 2 and census.excluded == 0 and census.reconciles
    assert priced["market_implied"].sum() == pytest.approx(1.0)
    assert priced.loc[0, "market_implied"] == pytest.approx(0.55)
    assert priced.loc[0, "market_implied_raw"] == pytest.approx(0.55 * OVERROUND)
    assert priced["overround"].tolist() == pytest.approx([OVERROUND, OVERROUND])


def test_a_pair_with_no_hold_in_it_is_refused_and_counted():
    """Dividing by a number at or below one INFLATES both sides above the price.

    A cross-book pair of two books' best prices can sum below 1.0. Normalising
    that would hand back a "fair" probability larger than the price implied,
    which is not a fair price — it is an arbitrage or a cross-book artefact
    wearing one. Refused, and counted, rather than quietly used.
    """
    frame = pd.DataFrame(
        [
            _pair("home", -3.5, american_odds_for(0.50), book="dk"),
            _pair("away", 3.5, american_odds_for(0.49), book="dk"),
        ]
    )
    priced, census = FS.devig(frame, scope="book")
    assert census.devigged == 0
    assert census.overround_not_above_one == 2
    assert census.reconciles
    assert priced["market_implied"].isna().all(), (
        "a refused pair must carry a MISSING market-implied probability, never "
        "an imputed one"
    )


def test_a_home_handicap_and_its_mirrored_away_handicap_are_one_wager():
    """-3.5 home and +3.5 away are two sides of one bet, and must pair."""
    home = FS.pair_key(_pair("home", -3.5, -110))
    away = FS.pair_key(_pair("away", 3.5, -110))
    assert home == away


def test_a_ladder_does_not_collapse_four_rungs_into_one_pair():
    """Keying on the absolute line would put home -3.5, home +3.5, away -3.5 and
    away +3.5 in one group of four, and the de-vig would refuse all of them —
    or worse, normalise two rungs of the same ladder against each other."""
    keys = {
        FS.pair_key(_pair("home", -3.5, -110)),
        FS.pair_key(_pair("home", 3.5, -110)),
        FS.pair_key(_pair("away", -3.5, -110)),
        FS.pair_key(_pair("away", 3.5, -110)),
    }
    assert len(keys) == 2, "four ladder rows are two wagers, not one and not four"


def test_home_over_never_pairs_with_away_under():
    """Two teams' totals hung at the same number are two wagers, not one.

    Both selections contain an underscore and both name a total, so anything
    that inferred the pair from the string would normalise one team's total
    against the other's and look entirely plausible doing it.
    """
    home = dict(_pair("home_over", 70.5, -110), market="team_total")
    away = dict(_pair("away_under", 70.5, -110), market="team_total")
    assert FS.pair_key(home) != FS.pair_key(away)
    assert FS.pair_key(home) == FS.pair_key(
        dict(_pair("home_under", 70.5, -110), market="team_total")
    )


def test_a_lone_side_is_counted_as_having_no_complement():
    frame = pd.DataFrame([_pair("home", -3.5, -110)])
    _, census = FS.devig(frame, scope="book")
    assert census.no_complement == 1 and census.devigged == 0 and census.reconciles


def test_a_selection_this_lab_does_not_pair_is_counted_not_guessed():
    frame = pd.DataFrame([_pair("draw", None, 250)])
    _, census = FS.devig(frame, scope="book")
    assert census.unknown_selection == 1
    assert census.reconciles


def test_the_book_scope_refuses_a_frame_with_no_book_column():
    """Every row landing in one nameless book is a cross-book pair in disguise."""
    frame = pd.DataFrame(
        [
            _pair("home", -3.5, american_odds_for(0.55 * OVERROUND)),
            _pair("away", 3.5, american_odds_for(0.45 * OVERROUND)),
        ]
    ).drop(columns=["book"])
    with pytest.raises(FS.ForecastSkillError) as raised:
        FS.devig(frame, scope="book")
    assert "cross-book" in str(raised.value)
    priced, census = FS.devig(frame, scope="wager")
    assert census.devigged == 2 and census.scope == "wager"


def test_implied_probability_is_one_line_over_the_repositorys_only_odds_reader():
    """No second reader of American odds. +150 beats -110 beats -200."""
    for odds in (-110.0, +150.0, -200.0, +100.0):
        assert FS.implied_probability(odds) == pytest.approx(
            1.0 / (1.0 + decimal_payout(odds))
        )
    assert FS.implied_probability(-110) == pytest.approx(110 / 210)
    assert math.isnan(FS.implied_probability("not a price")), (
        "an unreadable price is missing, never a certainty that the bet loses"
    )
    assert math.isnan(FS.implied_probability(None))


# ---------------------------------------------------------------------------
# The population, and the accounting
# ---------------------------------------------------------------------------


def test_a_push_is_not_half_a_win_and_is_excluded_and_counted():
    """A denominator that quietly includes pushes measures a different quantity."""
    frame = graded_frame("noise", games=40)
    frame.loc[frame.index[:20], "outcome"] = "push"
    frame.loc[frame.index[20:40], "outcome"] = "void"
    frame.loc[frame.index[40:50], "outcome"] = "unsettleable"
    priced, _ = FS.devig(frame, scope="book")
    population, census = FS.scorable(priced)

    assert census.push == 20 and census.void == 20 and census.unsettleable == 10
    assert census.reconciles
    assert len(population) == len(frame) - 50
    assert set(population["outcome"]) == {"won", "lost"}


def test_a_missing_model_probability_is_counted_and_is_not_a_probability_of_zero():
    frame = graded_frame("noise", games=40)
    frame.loc[frame.index[:30], "model_probability"] = None
    priced, _ = FS.devig(frame, scope="book")
    population, census = FS.scorable(priced)
    assert census.no_model_probability == 30
    assert census.reconciles
    assert len(population) == len(frame) - 30


def test_both_censuses_reconcile_on_a_real_run(noise):
    assert noise["devig_census"]["reconciles"] is True
    assert noise["population_census"]["reconciles"] is True
    assert (
        noise["devig_census"]["devigged"] + noise["devig_census"]["excluded"]
        == noise["devig_census"]["supplied"]
    )


def test_a_census_that_does_not_reconcile_refuses_to_write_a_record(monkeypatch):
    """A measurement that silently lost a third of its rows still prints an interval.

    Forced rather than waited for: the guard is only worth having if it fires,
    and nothing in a normal run can make it fire.
    """
    real_devig = FS.devig

    def losing_devig(frame, *, scope=FS.PAIR_SCOPES[0]):
        priced, census = real_devig(frame, scope=scope)
        census.devigged -= 7  # rows that reached neither bucket
        return priced, census

    monkeypatch.setattr(FS, "devig", losing_devig)
    with pytest.raises(FS.ForecastSkillError) as raised:
        FS.build_record(
            FS.SkillInputs(graded=graded_frame("noise", games=40), pair_scope="book")
        )
    assert "does not reconcile" in str(raised.value)


def test_a_missing_column_raises_rather_than_reading_as_a_zero():
    """The football lab reported zero bets from a column that had never been built."""
    frame = graded_frame("noise", games=32).drop(columns=["model_probability"])
    with pytest.raises(FS.ForecastSkillError) as raised:
        FS.build_record(FS.SkillInputs(graded=frame, pair_scope="book"))
    assert "model_probability" in str(raised.value)
    assert "Nothing is defaulted" in str(raised.value)


# ---------------------------------------------------------------------------
# Floors, corrections and tiers
# ---------------------------------------------------------------------------


def test_below_the_declared_row_floor_there_is_no_number():
    """A +0.4 disagreement coefficient over 40 wagers and a coin flip are the
    same claim at that sample size, and printing the +0.4 invites a quotation."""
    thin = FS.Coefficient(
        name="disagreement",
        estimate=0.4,
        standard_error=0.05,
        rows=FS.MINIMUM_ROWS - 1,
        clusters=FS.MINIMUM_CLUSTERS + 10,
        cluster_unit="game",
        answers_the_question=True,
    )
    assert not thin.enough_evidence
    assert "not enough evidence" in thin.verdict()
    assert thin.verdict() not in {S.DEMONSTRATED_EDGE, S.DEMONSTRATED_DEFICIT}
    assert FS._coefficient_cells(thin.to_json()) == ("—", "—", "—")


def test_below_the_declared_cluster_floor_there_is_no_number_either():
    """A cluster-robust sandwich is downward biased with few clusters, so its
    interval below the floor is narrow for a reason that has nothing to do with
    the model — and this repository's standing failure mode is a narrow
    interval."""
    few = FS.Coefficient(
        name="disagreement",
        estimate=0.4,
        standard_error=0.05,
        rows=50_000,
        clusters=FS.MINIMUM_CLUSTERS - 1,
        cluster_unit="day",
        answers_the_question=True,
    )
    assert not few.enough_evidence
    assert "not enough evidence" in few.verdict()
    assert f"{FS.MINIMUM_CLUSTERS:,}" in few.verdict()
    assert few.verdict() not in {S.DEMONSTRATED_EDGE, S.DEMONSTRATED_DEFICIT}


def test_the_family_correction_widens_the_interval_and_can_remove_a_verdict():
    """Testing many things must widen the interval, not be optional.

    And the count is the experiment ledger's **cumulative** one — this module
    imports `price_backtest.looks_from_ledger` rather than reimplementing it, so
    there is exactly one place in the repository that answers "how many looks".
    """
    one = record_for("truth", looks=1)
    many = record_for("truth", looks=400)
    single = pooled_disagreement(one)
    corrected = pooled_disagreement(many)
    assert single["estimate"] == pytest.approx(corrected["estimate"])
    assert corrected["adjusted_low"] < single["adjusted_low"]
    assert corrected["adjusted_high"] > single["adjusted_high"]
    assert many["correction_factor"] > one["correction_factor"] == 1.0


def test_the_looks_come_from_the_ledgers_cumulative_count(tmp_path):
    ledger = tmp_path / "experiment_ledger.json"
    ledger.write_text(
        json.dumps(
            {
                "alpha_budget": {"per_week": 6, "declared_on": "2026-09-01"},
                "hypotheses": [
                    {
                        "search": "fixture",
                        "name": f"h{i}",
                        "tested_on": "2026-09-01",
                        "seasons": [2027],
                        "outcome": "",
                        "predicted_direction": "higher",
                        "stage": "discovery",
                    }
                    for i in range(23)
                ],
            }
        ),
        encoding="utf-8",
    )
    assert FS.ledger_path(tmp_path) == ledger
    assert FS.looks_from_ledger(ledger) == 23


def test_every_tier_is_measured_and_the_pooled_row_carries_its_caveat(noise):
    """Never a pooled Division I headline, and a pooled row only beside tiers."""
    labels = [measured["label"] for measured in noise["by_tier"]]
    assert labels == [Tier.HIGH_MAJOR.value, Tier.LOW_MAJOR.value], labels
    for measured in noise["by_tier"]:
        assert measured["rows"] > 0
        assert (measured.get("fit") or {}).get("fitted")

    report = FS.render(noise)
    assert "## Per conference tier" in report
    assert report.index("## Per conference tier") < report.index("## Pooled")
    assert "This is never the headline" in report
    for label in labels:
        assert f"### {label}" in report


def _with_selected(frame: pd.DataFrame, *, threshold: float = PB.BET_EDGE_THRESHOLD) -> pd.DataFrame:
    """Stamp the flag the way the backtest does: `bet_mask` over `add_edge`."""
    edged = PB.add_edge(frame)
    return frame.assign(**{FS.SELECTED_COLUMN: PB.bet_mask(edged, threshold=threshold).to_numpy()})


def test_the_record_carries_both_populations_with_their_counts():
    """Every opinion is the skill measure; the selected bets sit beside it, counted.

    The selection is made by the model's disagreement with the price, and
    fitting outcome on that disagreement over the selected rows alone bakes the
    winner's curse into the coefficient. So the record names two populations,
    the primary `by_tier`/`pooled`/`raw_market_fit` are fitted over EVERY
    scorable opinion, and the selected subset is measured apart with its own
    count — strictly smaller here, because the fixture's disagreement is noise
    around the price and most rows fall below the threshold.
    """
    frame = _with_selected(graded_frame("anti"))
    assert 0 < int(frame[FS.SELECTED_COLUMN].sum()) < len(frame), "the fixture must select a strict subset"
    record = FS.build_record(FS.SkillInputs(graded=frame, pair_scope="book"), competition=CBB)

    populations = record["populations"]
    whole, subset = populations["all_opinions"], populations["selected"]
    assert whole["label"] == FS.ALL_OPINIONS_LABEL
    assert whole["role"] == FS.ALL_OPINIONS_ROLE
    assert subset["label"] == FS.SELECTED_LABEL
    assert subset["role"] == FS.SELECTED_ROLE
    assert "not the skill measure" in subset["role"]
    assert subset["available"] is True

    scored = record["population_census"]["scored"]
    assert whole["rows"] == record["pooled"]["rows"] == scored > 0
    # The subset is the scorable rows the flag marks — no more, no fewer.
    priced, _ = FS.devig(frame, scope="book")
    scorable, _ = FS.scorable(priced)
    expected_selected = int(FS.selected_mask(scorable).sum())
    assert subset["rows"] == record["selected"]["rows"] == record["selected"]["pooled"]["rows"] == expected_selected
    assert 0 < subset["rows"] < whole["rows"]

    # The primary cells are fitted over every opinion, and say so.
    assert record["population_label"] == FS.ALL_OPINIONS_LABEL
    assert record["pooled"]["population"] == FS.ALL_OPINIONS_LABEL
    assert record["by_tier"], "the tier breakdown applies to the all-opinions fit"
    for measured in record["by_tier"]:
        assert measured["population"] == FS.ALL_OPINIONS_LABEL
    assert sum(m["rows"] for m in record["by_tier"]) + record["rows_without_a_tier"] == whole["rows"]
    assert record["raw_market_fit"]["rows"] == whole["rows"]
    # The selected cells say what they are, per tier and pooled, with counts.
    for measured in list(record["selected"]["by_tier"]) + [record["selected"]["pooled"]]:
        assert measured["population"] == FS.SELECTED_LABEL
        assert measured["rows"] >= 0
    assert sum(m["rows"] for m in record["selected"]["by_tier"]) == subset["rows"]
    # A selected bucket table has nothing below the threshold by construction:
    # that is the tautology this split exists to expose, not to hide.
    below = [
        b for b in record["selected"]["pooled"]["buckets"]
        if b["high"] <= PB.BET_EDGE_THRESHOLD and b.get("rows")
    ]
    assert below == [], below
    above = [b for b in record["pooled"]["buckets"] if b["high"] <= 0 and b.get("rows")]
    assert above, "the all-opinions table must keep the wagers the model disliked as its control group"


def test_the_record_and_report_state_the_wagers_excluded_before_the_frame():
    """The frame is a subset of the graded set, and the report has to say so.

    `build_skill_frame.py` excludes every graded wager whose own book hung one
    side only — no hold, no fair price, nothing to de-vig — and writes a census
    of what it dropped. Nothing in the frame records that, so a reader given
    only the two population counts would take the larger for the graded set.
    The count, the share, the reason and where it fell all reach the report.
    """
    frame = _with_selected(graded_frame("anti"))
    census = {
        "supplied": len(frame) + 3,
        "paired": len(frame),
        "unpairable": 3,
        "unpairable_selected": 1,
        "share": 3 / (len(frame) + 3),
        "reconciles": True,
        "reason": "their own book hung only one side of the wager",
        "by_market": {"team_total": 2, "alternate_spread": 1},
        "by_book": {"draftkings": 2, "betmgm": 1},
    }
    record = FS.build_record(
        FS.SkillInputs(graded=frame, pair_scope="book", unpairable=census), competition=CBB
    )
    excluded = record["populations"]["excluded_unpairable"]
    assert excluded["available"] is True
    assert excluded["rows"] == 3
    assert excluded["supplied"] == len(frame) + 3
    assert excluded["paired"] == len(frame)
    assert excluded["selected_rows"] == 1
    assert excluded["reconciles"] is True
    assert excluded["label"] == FS.UNPAIRABLE_LABEL
    assert excluded["by_book"] == {"draftkings": 2, "betmgm": 1}
    # The excluded rows are in neither population, and the record says so.
    whole = record["populations"]["all_opinions"]
    assert whole["rows"] < excluded["supplied"]

    report = FS.render(record)
    assert "## Two populations, and which one is the skill measure" in report
    assert "3 graded wager(s) are in neither population above" in report
    assert f"{len(frame) + 3:,} graded wagers" in report
    assert "their own book hung only one side of the wager" in report
    assert "team_total (2)" in report and "betmgm (1)" in report
    assert f"1 had been marked as {FS.SELECTED_LABEL}" in report
    # The exclusion is stated in the section that states the populations, not
    # somewhere a reader of the counts would never reach.
    section = report.index("## Two populations, and which one is the skill measure")
    assert section < report.index("3 graded wager(s) are in neither population above")


def test_the_unpairable_census_carries_its_third_term_and_the_identity_closes():
    """`supplied = paired + unpairable + no_pair_key` - all three, or none.

    `build_skill_frame.UnpairableCensus` counts three disjoint buckets off the
    graded frame, and `_excluded_unpairable` copied two of them. The third,
    `no_pair_key`, was read back in `_excluded_lines` with a `.get(..., 0)`
    default - so the report printed a hard zero for a term nobody had copied,
    and the three figures a reader was invited to add up contained one that was
    manufactured by a default. The fixture below puts a NON-ZERO count in that
    term, which is the only shape in which the defect is visible at all: at
    zero the dropped term and the default agree.
    """
    frame = _with_selected(graded_frame("anti"))
    paired, unpairable, keyless = len(frame), 3, 7
    census = {
        "supplied": paired + unpairable + keyless,
        "paired": paired,
        "unpairable": unpairable,
        "unpairable_selected": 0,
        "no_pair_key": keyless,
        "share": unpairable / (paired + unpairable + keyless),
        "reconciles": True,
        "reason": "their own book hung only one side of the wager",
    }
    record = FS.build_record(
        FS.SkillInputs(graded=frame, pair_scope="book", unpairable=census), competition=CBB
    )
    excluded = record["populations"]["excluded_unpairable"]
    assert excluded["no_pair_key"] == keyless, (
        "the third term of the census never reached the record, so the report "
        f"prints a default in its place; got {excluded}"
    )
    # `accounted` is this module's own sum over the terms it carries, which is
    # a different statement from `== census["supplied"]`: that one is true by
    # construction of this fixture and would survive `accounted = supplied`.
    # The case that separates them — a census whose terms miss `supplied` — is
    # `test_a_census_whose_three_terms_do_not_add_up_says_so_in_the_arithmetic`.
    assert (
        excluded["accounted"]
        == excluded["paired"] + excluded["rows"] + excluded["no_pair_key"]
    ), f"the sum must be of the three terms the record holds; got {excluded}"
    assert excluded["accounted"] == census["supplied"], (
        "and on this fixture they do add up to the wagers the frame-builder "
        f"was handed; got {excluded}"
    )

    report = FS.render(record)
    assert f"{keyless:,} carried a selection this lab forms no pair key for" in report
    assert (
        f"Census: {paired:,} paired + {unpairable:,} excluded + {keyless:,} "
        f"with no pair key = {census['supplied']:,}, against "
        f"{census['supplied']:,} graded wagers supplied." in report
    ), report
    assert "do not add up to the wagers supplied" not in report


def test_a_census_whose_three_terms_do_not_add_up_says_so_in_the_arithmetic():
    """The identity is independent of the frame-builder's own flag.

    A census stated only when it works is a census whose failure is invisible:
    a reader shown three numbers has to be shown what they sum to as well. But
    that argument is only worth something in the case the flag MISSES — and the
    fixture used to set `reconciles: False` as well, so the report was told
    twice and either guard alone could have produced the page. A fixture that
    satisfies two guards tests neither.

    So `reconciles` is **True** here, which is the only arrangement in which
    this module's arithmetic is the only thing that can fire. The flag being
    False is covered on its own by
    `test_the_report_refuses_to_present_a_census_that_does_not_reconcile`, and
    the two are held apart on purpose.
    """
    frame = _with_selected(graded_frame("anti"))
    paired, unpairable, keyless = len(frame), 3, 7
    census = {
        # Nine wagers the three buckets never account for.
        "supplied": paired + unpairable + keyless + 9,
        "paired": paired,
        "unpairable": unpairable,
        "no_pair_key": keyless,
        "share": 0.0,
        # The frame-builder says its census reconciles. It does not, by this
        # module's own arithmetic over the terms this module carries, and that
        # disagreement is exactly what the printed identity exists to surface.
        "reconciles": True,
        "reason": "their own book hung only one side of the wager",
    }
    record = FS.build_record(
        FS.SkillInputs(graded=frame, pair_scope="book", unpairable=census), competition=CBB
    )
    excluded = record["populations"]["excluded_unpairable"]
    assert excluded["reconciles"] is True, (
        "the flag must say the census is fine, or the page has a second reason "
        f"to print a warning and this test cannot tell which fired; {excluded}"
    )
    assert excluded["accounted"] == paired + unpairable + keyless
    assert excluded["accounted"] != excluded["supplied"]
    report = FS.render(record)
    assert "**The frame-builder's census does not reconcile**" not in report, (
        "the flag's own paragraph must be absent here; its presence would mean "
        f"this test proves nothing about the identity; got {report}"
    )
    assert (
        f"= {paired + unpairable + keyless:,}, against {census['supplied']:,} "
        "graded wagers supplied." in report
    ), report
    assert "**Those three terms do not add up to the wagers supplied**" in report


def test_a_census_missing_its_third_term_is_refused_rather_than_defaulted_to_zero():
    """A record written before the third term was carried cannot be rendered.

    This is the same defect arriving from the other direction. The records in
    `data/outputs/` were written in a shape that holds two of the census's
    three terms, and a `.get(..., 0)` in the renderer would print a hard zero
    for the third — *"0 carried a selection this lab forms no pair key for"* —
    over a run where nobody counted. The sum would balance, because one of its
    addends was invented to make it balance. There is no honest rendering of
    that record, so the report refuses it and names what is missing.
    """
    frame = _with_selected(graded_frame("anti"))
    census = {
        "supplied": len(frame) + 3,
        "paired": len(frame),
        "unpairable": 3,
        "no_pair_key": 0,
        "share": 3 / (len(frame) + 3),
        "reconciles": True,
        "reason": "their own book hung only one side of the wager",
    }
    record = FS.build_record(
        FS.SkillInputs(graded=frame, pair_scope="book", unpairable=census), competition=CBB
    )
    assert FS.render(record), "the current shape must render"

    stale = json.loads(json.dumps(record, default=str))
    stale["populations"]["excluded_unpairable"].pop("no_pair_key")
    with pytest.raises(FS.ForecastSkillError) as raised:
        FS.render(stale)
    assert "`no_pair_key`" in str(raised.value), raised.value
    assert "Re-run the regression" in str(raised.value)


def test_keyless_rows_are_never_reported_as_having_found_a_complement():
    """Excluding nothing is not the same as pairing everything.

    A graded row this lab forms no pair key for never went looking for a
    complement. With `unpairable` at zero the report said *"All N graded wagers
    found a complement at their own book"*, which is a claim about every one of
    them - false of exactly the rows in the third term, and made in the one
    branch where that term is the only thing separating `paired` from
    `supplied`.
    """
    frame = _with_selected(graded_frame("anti"))
    paired, keyless = len(frame), 5
    census = {
        "supplied": paired + keyless,
        "paired": paired,
        "unpairable": 0,
        "no_pair_key": keyless,
        "share": 0.0,
        "reconciles": True,
        "reason": "their own book hung only one side of the wager",
    }
    record = FS.build_record(
        FS.SkillInputs(graded=frame, pair_scope="book", unpairable=census), competition=CBB
    )
    report = FS.render(record)
    assert "**Nothing was excluded before this frame was built.**" in report
    assert f"All {paired + keyless:,} graded wagers found a complement" not in report, (
        "the keyless rows did not find a complement and were not excluded; a "
        "sentence that folds them into `paired` states a pairing nobody made"
    )
    assert f"{keyless:,} carried a selection this lab forms no pair key for" in report
    assert "it is not wholly a paired one" in report


def test_a_frame_with_no_census_says_not_supplied_rather_than_none():
    """Absent is not zero. "Nothing was excluded" is a measurement nobody made.

    The forward ledger carries no census, and defaulting the count to zero
    would print a claim about a quantity that was never counted — the same
    error as deriving an accounting bucket by subtraction and calling the sum
    a reconciliation.
    """
    frame = _with_selected(graded_frame("anti"))
    record = FS.build_record(FS.SkillInputs(graded=frame, pair_scope="book"), competition=CBB)
    excluded = record["populations"]["excluded_unpairable"]
    assert excluded["available"] is False
    assert excluded["rows"] == 0
    report = FS.render(record)
    assert FS.UNPAIRABLE_NOT_SUPPLIED in report
    assert "are in neither population above" not in report


def test_a_census_that_excluded_nothing_says_the_frame_is_the_whole_graded_set():
    frame = _with_selected(graded_frame("anti"))
    census = {
        "supplied": len(frame),
        "paired": len(frame),
        "unpairable": 0,
        "share": 0.0,
        "reconciles": True,
        "reason": "their own book hung only one side of the wager",
    }
    record = FS.build_record(
        FS.SkillInputs(graded=frame, pair_scope="book", unpairable=census), competition=CBB
    )
    excluded = record["populations"]["excluded_unpairable"]
    assert excluded["available"] is True and excluded["rows"] == 0
    report = FS.render(record)
    assert "**Nothing was excluded before this frame was built.**" in report
    assert f"All {len(frame):,} graded wagers found a complement" in report
    assert FS.UNPAIRABLE_NOT_SUPPLIED not in report


def test_a_census_that_does_not_reconcile_is_said_so_before_its_numbers():
    """A census whose own terms do not add up cannot vouch for the frame.

    `supplied = paired + unpairable` is the whole claim the census makes. When
    it fails, the numbers under it are not a smaller truth — they are of
    unknown completeness, and the report says that above them rather than
    printing them as if they were counted.
    """
    frame = _with_selected(graded_frame("anti"))
    census = {
        "supplied": len(frame) + 9,
        "paired": len(frame),
        "unpairable": 3,
        "share": 3 / (len(frame) + 9),
        "reconciles": False,
        "reason": "their own book hung only one side of the wager",
    }
    record = FS.build_record(
        FS.SkillInputs(graded=frame, pair_scope="book", unpairable=census), competition=CBB
    )
    assert record["populations"]["excluded_unpairable"]["reconciles"] is False
    report = FS.render(record)
    warning = "**The frame-builder's census does not reconcile**"
    assert warning in report
    assert report.index(warning) < report.index("3 graded wager(s) are in neither population")


def test_the_report_says_which_population_every_number_belongs_to():
    frame = _with_selected(graded_frame("anti"))
    record = FS.build_record(FS.SkillInputs(graded=frame, pair_scope="book"), competition=CBB)
    report = FS.render(record)

    assert "## Two populations, and which one is the skill measure" in report
    assert f"**{FS.ALL_OPINIONS_LABEL}**" in report
    assert FS.SELECTED_LABEL in report
    assert "the winner's-curse comparison, not the skill measure" in report
    # The skill measure comes first, the comparison after it, labelled.
    tiers = report.index("## Per conference tier")
    pooled = report.index("## Pooled")
    beside = report.index("## The threshold-selected bets, beside it")
    raw = report.index("## The same fit without the de-vig")
    assert tiers < pooled < beside < raw
    # Every fitted cell carries a population line with its own count.
    population_lines = [l for l in report.splitlines() if l.startswith("*Population: **")]
    cells = len(record["by_tier"]) + 1 + len(record["selected"]["by_tier"]) + 1
    assert len(population_lines) == cells, (len(population_lines), cells)
    for line in population_lines:
        assert "scorable wagers" in line
        assert FS.ALL_OPINIONS_LABEL in line or FS.SELECTED_LABEL in line
    whole = record["populations"]["all_opinions"]["rows"]
    subset = record["populations"]["selected"]["rows"]
    assert f"{subset:,} of {whole:,} scorable wagers" in report
    # The threshold section reads the all-opinions fit, in words.
    assert f"pooled disagreement coefficient over **{FS.ALL_OPINIONS_LABEL}**" in report


def test_a_frame_without_the_selected_flag_reports_the_subset_as_not_supplied():
    """The forward ledger carries no flag; the subset is then absent, never inferred."""
    frame = graded_frame("noise")
    assert FS.SELECTED_COLUMN not in frame.columns
    record = FS.build_record(FS.SkillInputs(graded=frame, pair_scope="book"), competition=CBB)
    assert record["populations"]["selected"]["available"] is False
    assert record["populations"]["selected"]["rows"] == 0
    assert record["selected"]["available"] is False
    assert FS.SELECTED_COLUMN in record["selected"]["reason"]
    assert record["selected"]["by_tier"] == []
    assert record["populations"]["all_opinions"]["rows"] == record["pooled"]["rows"] > 0
    report = FS.render(record)
    assert "not supplied" in report
    assert f"Every number in this report belongs to **{FS.ALL_OPINIONS_LABEL}**" in report


def test_an_unreadable_selected_flag_is_not_a_bet():
    frame = pd.DataFrame({FS.SELECTED_COLUMN: [True, False, "True", "false", "1", "0", "", None, "maybe"]})
    assert FS.selected_mask(frame).tolist() == [True, False, True, False, True, False, False, False, False]


def test_nothing_to_measure_is_said_in_words_rather_than_shown_as_an_empty_table():
    """An empty table reads as a null result, and a null result is a claim."""
    record = FS.build_record(FS.SkillInputs(graded=pd.DataFrame(), pair_scope="book"))
    assert record["pooled"]["rows"] == 0
    assert record["by_tier"] == []
    report = FS.render(record)
    assert FS.NOTHING_TO_MEASURE in report.lower()
    assert "an empty table reads as a null result" in report


# ---------------------------------------------------------------------------
# The record, and re-rendering from it
# ---------------------------------------------------------------------------


def test_the_report_re_renders_from_the_record_byte_identically(tmp_path, anti):
    """Improving a sentence must never cost a re-run.

    A report that can only be produced by re-running the measurement is a report
    nobody improves — they edit the generated file by hand, and a hand-edited
    generated file survives exactly one re-run. The retention probe's rule.
    """
    record_path = FS.record_path(CBB, tmp_path)
    report_path = FS.report_path(CBB, tmp_path)
    FS.write_record(anti, record_path)
    FS.write_report(anti, report_path)

    reread = FS.read_record(record_path)
    assert FS.render(reread) == report_path.read_text(encoding="utf-8")
    assert record_path.name == "cbb_forecast_skill.json"
    assert report_path.name == "cbb_forecast_skill.md"


def test_a_record_from_a_different_shape_is_refused_rather_than_rendered(tmp_path, anti):
    """A stale record renders a report with holes in it and nothing looks wrong.

    A **newer** record — written by a checkout ahead of this one — and the
    message names it as such, so a reader can tell it apart from the older
    shape refused below rather than reading one message for two situations.
    """
    path = tmp_path / "stale.json"
    stale = dict(anti)
    stale["record_version"] = FS.RECORD_VERSION + 1
    path.write_text(json.dumps(stale, default=str), encoding="utf-8")
    with pytest.raises(FS.ForecastSkillError) as raised:
        FS.read_record(path)
    message = str(raised.value)
    assert "Re-run" in message
    assert f"version {FS.RECORD_VERSION + 1} record" in message, message
    assert "a newer" in message and "an older" not in message, message


def _version_2_shaped(record: dict) -> dict:
    """The record this module wrote until 2026-09-05, rebuilt from a live one.

    Version 2 carried one key, `anti_predictive`, holding realised minus
    model-implied — overconfidence under the anti-predictive name — and neither
    `overconfidence` nor `anti_predictive_return`.
    """
    stale = json.loads(json.dumps(record, default=str))
    stale["record_version"] = 2
    for cell in list(stale.get("by_tier") or []) + [stale.get("pooled") or {}]:
        curse = cell.pop("overconfidence", None)
        cell.pop("anti_predictive_return", None)
        if curse is not None:
            cell["anti_predictive"] = curse
    return stale


def test_a_record_from_the_previous_shape_is_refused_and_named_as_older(tmp_path, anti):
    """The stale record this repository actually has on disk is the older one.

    `data/outputs/` carries records written by earlier runs, and an older
    record's keys are a **subset** of what `render` reads — so re-rendering one
    drops whole paragraphs and leaves a report that looks finished. The commit
    that split `anti_predictive` into `overconfidence` and
    `anti_predictive_return` left `RECORD_VERSION` at 2, so this guard could not
    fire and a reader could not tell the two shapes apart.
    """
    assert FS.RECORD_VERSION == 6, (
        "the record's shape changed four times and the version moved with it "
        "every time: when `anti_predictive` was split into overconfidence and "
        "anti-predictive return with a corrected interval and a verdict on "
        "every bucket (2 -> 3); when `populations` gained "
        "`excluded_unpairable` — the graded wagers the frame-builder dropped "
        "because their book hung one side only (3 -> 4); when the "
        "unpairable census gained its dropped third term and "
        "`anti_predictive_return` gained the buckets it had measured, the "
        "reason it could not compare them, the sign of them and the buckets "
        "whose corrected interval lies below zero (4 -> 5); and when "
        "`buckets_with_no_return_figure` — one counter standing for a frame "
        "with no return column AND for a bucket whose wagers are all "
        "unsettled — became `buckets_with_no_return_column` and "
        "`buckets_with_no_settled_wager`, with every populated bucket "
        "stamping its own `roi_absent_because` (5 -> 6). The version must "
        "move with the shape or the staleness guard is decoration"
    )
    stale = _version_2_shaped(anti)
    path = tmp_path / "stale.json"
    path.write_text(json.dumps(stale, default=str), encoding="utf-8")

    with pytest.raises(FS.ForecastSkillError) as raised:
        FS.read_record(path)
    message = str(raised.value)
    assert "version 2 record" in message, message
    assert "an older" in message, message
    assert "Re-run" in message

    # And the refusal is load-bearing, not ceremony: rendered anyway, the older
    # shape loses the anti-predictive paragraph outright and nothing looks
    # wrong.
    headline = "Realised return by claimed edge — the anti-predictive statistic."
    assert headline in FS.render(anti)
    assert headline not in FS.render(stale)

    # The version-3 shape is refused for the same reason and it is the same
    # class of harm: its `populations` block carries no `excluded_unpairable`,
    # so re-rendering it prints "no census was supplied" over a run that had
    # one, and the reader is told the frame's provenance is unknown when it was
    # measured and recorded.
    version_3 = json.loads(json.dumps(anti, default=str))
    version_3["record_version"] = 3
    version_3["populations"].pop("excluded_unpairable")
    path_3 = tmp_path / "version_3.json"
    path_3.write_text(json.dumps(version_3, default=str), encoding="utf-8")
    with pytest.raises(FS.ForecastSkillError) as raised_3:
        FS.read_record(path_3)
    assert "version 3 record" in str(raised_3.value)
    assert FS.UNPAIRABLE_NOT_SUPPLIED in FS.render(version_3)

    # And version 4, which is the shape the records in `data/outputs/` were
    # written in. Its `anti_predictive_return` stops at `measurable` on every
    # cell that could not compare two buckets, so re-rendering one prints a
    # sample-size floor as the reason for a silence that had a different cause
    # — which is the defect the fifth version exists to close. Rendered anyway,
    # it loses the counted reason outright.
    version_4 = json.loads(json.dumps(anti, default=str))
    version_4["record_version"] = 4
    for cell in list(version_4.get("by_tier") or []) + [version_4.get("pooled") or {}]:
        shape = cell.get("anti_predictive_return") or {}
        for key in (
            "measured_buckets",
            "buckets_with_no_return_figure",
            "buckets_below_the_bet_floor",
            "buckets_below_the_row_floor",
            "negative_point_estimates",
            "demonstrated_deficits",
            "deficit_buckets",
            "worst_bucket",
        ):
            shape.pop(key, None)
        shape["measurable"] = False
    version_4["populations"]["excluded_unpairable"].pop("no_pair_key")
    version_4["populations"]["excluded_unpairable"].pop("accounted")
    path_4 = tmp_path / "version_4.json"
    path_4.write_text(json.dumps(version_4, default=str), encoding="utf-8")
    with pytest.raises(FS.ForecastSkillError) as raised_4:
        FS.read_record(path_4)
    assert "version 4 record" in str(raised_4.value)
    assert "an older" in str(raised_4.value)
    # Load-bearing in the same way the version 2 check above is: rendered
    # anyway, the version 4 shape loses the comparison paragraph and prints a
    # bare floor sentence in its place, with nothing on the page saying which
    # buckets were measured or why the rest were not.
    stale = FS.render(version_4)
    assert headline not in stale
    assert headline in FS.render(anti)
    assert "Whatever cleared the floor is measured below" not in stale, (
        "a version 4 record carries the COUNT of usable buckets and not the "
        "buckets, so a paragraph keyed on the count would promise a figure "
        "below it and print none"
    )
    assert "carry no settled wager at all" not in stale


def test_the_disagreement_coefficient_survives_the_de_vig_choice(anti):
    """Under a constant overround the two fits must agree exactly.

    The two designs span the same column space — `span{1, m, p}` either way,
    because `k·m` is a scalar multiple of `m` — so only the intercept and the
    market coefficient move. The report claims this; this checks it, and it is
    what makes "the de-vig method cannot manufacture the answer" a measured
    statement rather than a reassuring one.
    """
    devigged = pooled_disagreement(anti)
    raw = FS.coefficient(anti["raw_market_fit"], "disagreement")
    assert raw["estimate"] == pytest.approx(devigged["estimate"], abs=1e-9)
    assert FS.coefficient(anti["raw_market_fit"], "market_implied")[
        "estimate"
    ] != pytest.approx(
        FS.coefficient(FS.pooled_fit_of(anti), "market_implied")["estimate"]
    )


def test_the_threshold_algebra_is_in_the_report_that_promises_it(anti):
    """`price_backtest.bets_from` says this module shows why raising the edge
    threshold cannot help. It has to actually be there."""
    report = FS.render(anti)
    assert "## Why raising the edge threshold cannot help" in report
    assert "b_disagreement" in report
    assert "selects **worse** wagers" in report
    assert f"{FS.BET_EDGE_THRESHOLD:.0%}" in report


def test_the_pooled_population_is_the_tiers_plus_whatever_could_not_be_placed():
    """A pooled figure quietly larger than the sum of its tiers is how a
    Division I headline reappears after being forbidden.

    A row with a missing tier belongs to no tier section, so it has to be
    counted somewhere the reader can see it rather than left as an unexplained
    difference between two tables.
    """
    frame = graded_frame("noise", games=60)
    frame.loc[frame.index[:24], "tier"] = None
    record = FS.build_record(FS.SkillInputs(graded=frame, pair_scope="book"))

    tiered = sum(int(measured["rows"]) for measured in record["by_tier"])
    assert record["rows_without_a_tier"] == 24
    assert tiered + record["rows_without_a_tier"] == record["pooled"]["rows"]

    report = FS.render(record)
    assert "24 scorable wagers carry no conference tier" in report


def test_a_fully_tiered_run_says_nothing_about_orphans(noise):
    assert noise["rows_without_a_tier"] == 0
    assert "carry no conference tier" not in FS.render(noise)
