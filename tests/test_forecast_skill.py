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
  whose shortfall widens with the claimed edge — a coefficient alone can be
  called noise, a monotone column cannot;
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

    A coefficient is one number and a reader can call it noise. A shortfall
    column that widens as the claimed edge grows is a shape, and it is what
    makes "raise the threshold" visibly the wrong response rather than the
    obvious one.
    """
    row = pooled_disagreement(anti)
    assert row["estimate"] < 0.0, row["estimate"]
    assert row["estimate"] == pytest.approx(-0.5, abs=0.45), row["estimate"]

    shape = (anti.get("pooled") or {}).get("anti_predictive") or {}
    assert shape["measurable"], shape
    assert shape["worse_at_the_top"], (
        "an anti-predictive model must show a wider shortfall in its highest "
        f"claimed-edge bucket than in its lowest; got {shape}"
    )
    assert shape["shortfall_widens_by"] > 0.0

    report = FS.render(anti)
    assert "The biggest claimed edges do worst." in report
    assert "raising the edge threshold the wrong response" in report


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
    """A stale record renders a report with holes in it and nothing looks wrong."""
    path = tmp_path / "stale.json"
    stale = dict(anti)
    stale["record_version"] = FS.RECORD_VERSION + 1
    path.write_text(json.dumps(stale, default=str), encoding="utf-8")
    with pytest.raises(FS.ForecastSkillError) as raised:
        FS.read_record(path)
    assert "Re-run" in str(raised.value)


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
