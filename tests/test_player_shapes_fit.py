"""What `scripts/fit_player_model.py` computes, held against something else.

The fitter reads the whole settlement table and writes numbers a later model
will price on. Nobody re-derives those numbers by hand, so each estimator here
is checked against a quantity it must equal for a reason independent of its own
implementation:

* the vectorised trailing columns against the obvious per-group pandas lambdas
  they replaced (the speed is bought with a test, not with trust);
* the pooled variance-to-mean against synthetic data whose dispersion is known
  by construction, in both directions -- Poisson at 1, an over-dispersed mixture
  above it, a binomial below it, because the whole point of the Panjer family is
  that it must be allowed to come out below 1;
* the credibility fit against synthetic data generated from a known `k`;
* the value pmf against the box score's own points identity;
* and the window guard against every season this lab must never read.

The window guard is the one that matters most and it is tested first, because
every other number in this file is worthless if it was made on 2024.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
FROZEN = REPO / "data" / "processed" / "cbb_player_shapes.json"


def _load_fitter():
    """Import the fitter by path; it lives in `scripts/`, which is not a package."""
    path = REPO / "scripts" / "fit_player_model.py"
    spec = importlib.util.spec_from_file_location("fit_player_model", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Registered before execution: `@dataclass` resolves annotations through
    # `sys.modules[cls.__module__]`, and a module that is not there yet raises.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


F = _load_fitter()


def _frame(rows: int = 600, seed: int = 0) -> pd.DataFrame:
    """A synthetic player table with the columns `prepare` reads."""
    rng = np.random.default_rng(seed)
    field_goals = rng.integers(0, 12, rows).astype(float)
    return pd.DataFrame(
        {
            "game_id": np.arange(rows) + 500_000,
            "season": rng.integers(2019, 2023, rows),
            "slate_date": (
                pd.to_datetime("2018-11-06") + pd.to_timedelta(rng.integers(0, 120, rows), "D")
            ).astype(str),
            "athlete_id": rng.integers(1, 40, rows).astype(float),
            "athlete_display_name": "A Player",
            "team_id": 1,
            "opponent_id": 2,
            "home_away": "home",
            "did_not_play": rng.random(rows) < 0.2,
            "starter": True,
            "minutes": rng.integers(1, 41, rows).astype(float),
            "points": 0.0,
            "rebounds": rng.integers(0, 15, rows).astype(float),
            "assists": rng.integers(0, 10, rows).astype(float),
            "steals": rng.integers(0, 5, rows).astype(float),
            "turnovers": rng.integers(0, 6, rows).astype(float),
            "field_goals_made": field_goals,
            "three_point_field_goals_made": np.minimum(field_goals, rng.integers(0, 6, rows)),
            "free_throws_made": rng.integers(0, 8, rows).astype(float),
        }
    ).assign(
        points=lambda d: d["free_throws_made"]
        + 2 * d["field_goals_made"]
        + d["three_point_field_goals_made"]
    )


# --------------------------------------------------------------------------
# The window
# --------------------------------------------------------------------------


@pytest.mark.parametrize("season", [2024, 2025, 2026, 2030])
def test_the_fitter_refuses_the_priced_season_and_everything_after_it(season: int) -> None:
    """The guard fires before a row is read, on the season list itself."""
    with pytest.raises(F.FitError) as raised:
        F._check_window([2021, season], what="a test")
    assert str(season) in str(raised.value)


@pytest.mark.parametrize("seasons", [(2019, 2020), (2021, 2022), (2019, 2020, 2021, 2022, 2023)])
def test_the_fitter_permits_every_season_earlier_than_the_priced_one(seasons) -> None:
    F._check_window(list(seasons), what="a test")


def test_a_holdout_inside_the_fit_is_refused() -> None:
    with pytest.raises(F.FitError) as raised:
        F.fit(Path("/does/not/matter.csv"), [2021, 2022], 2022)
    assert "not a holdout" in str(raised.value)


def test_the_price_season_floor_is_the_season_this_lab_actually_prices() -> None:
    """Pinned, because everything else here is downstream of this one integer."""
    assert F.PRICE_SEASON == 2024
    assert max(F.FIT_SEASONS) < F.PRICE_SEASON
    assert F.VALIDATION_SEASON < F.PRICE_SEASON
    assert F.VALIDATION_SEASON not in F.FIT_SEASONS


# --------------------------------------------------------------------------
# Reading the table
# --------------------------------------------------------------------------


def test_did_not_play_is_read_as_a_boolean_and_not_as_a_non_empty_string() -> None:
    """`bool("False")` is True, and this lab has already been bitten by it.

    A CSV round-trip turns the column into the strings `"True"` and `"False"`.
    Read with `bool()`, every player who did play is marked absent.
    """
    frame = _frame(rows=200)
    frame["did_not_play"] = frame["did_not_play"].astype(str)
    prepared = F.prepare(frame)
    assert prepared["appeared"].sum() == (frame["did_not_play"] == "False").sum()
    assert prepared["appeared"].sum() > 0
    assert (~prepared["appeared"]).sum() > 0


def test_did_not_play_rows_survive_prepare_and_carry_a_projection() -> None:
    """The projection has to exist on the night a player sat.

    A frame built only from appearances cannot say what was expected of a
    did-not-play, and that expectation is the whole content of the stored
    `dnp_probability` diagnostic. This is the bug this test was written against:
    the diagnostic came out 0.0 in every bucket because no did-not-play row had
    a bucket at all.
    """
    trailing = F.with_trailing(F.prepare(_frame(rows=2000, seed=3)), F.MINUTES_HALF_LIFE)
    absent = trailing[~trailing["appeared"]]
    assert len(absent) > 0
    assert absent["projected_minutes"].notna().any()
    rates, counts, _ = F.dnp_base_rates(trailing)
    assert sum(counts) > 0
    assert any(rate > 0 for rate in rates if rate == rate)


def test_a_projection_never_reads_the_game_it_is_projecting() -> None:
    """Every trailing column is strictly prior; the first game of a season has none."""
    trailing = F.with_trailing(F.prepare(_frame(rows=1200, seed=7)), F.MINUTES_HALF_LIFE)
    first = trailing.groupby(["season", "athlete_id"], sort=False).head(1)
    assert first["projected_minutes"].isna().all()
    assert (first["prior_games"] == 0).all()
    assert (first["prior_minutes"] == 0).all()
    assert (first["bank_points"] == 0).all()


def test_trailing_columns_match_the_obvious_groupby() -> None:
    """The vectorised columns against the per-group lambdas they replaced.

    `with_trailing` computes every column as a whole-array cumulative operation
    reset at group boundaries, which is roughly a hundred times faster than a
    per-group lambda over thirty thousand athletes. That is only worth doing if
    it computes the same numbers.
    """
    prepared = F.prepare(_frame(rows=1500, seed=11))
    got = F.with_trailing(prepared, 4.0)
    played = prepared[prepared["played"]]
    group = played.groupby(["season", "athlete_id"], sort=False)

    expected_projection = group["minutes"].transform(
        lambda s: s.ewm(halflife=4.0).mean().shift(1)
    )
    expected_games = group.cumcount()
    expected_minutes = group["minutes"].transform(lambda s: s.cumsum().shift(1)).fillna(0.0)
    expected_bank = group["rebounds"].transform(lambda s: s.cumsum().shift(1)).fillna(0.0)

    on_played = got.loc[played.index]
    assert np.allclose(
        on_played["projected_minutes"].fillna(-1.0), expected_projection.fillna(-1.0)
    )
    assert (on_played["prior_games"].to_numpy() == expected_games.to_numpy()).all()
    assert np.allclose(on_played["prior_minutes"], expected_minutes)
    assert np.allclose(on_played["bank_rebounds"], expected_bank)


def test_the_row_hash_does_not_depend_on_row_order_or_id_spelling() -> None:
    """A provenance record nobody can reproduce is not a provenance record."""
    frame = _frame(rows=300, seed=13)
    shuffled = frame.sample(frac=1.0, random_state=5)
    restyled = frame.copy()
    restyled["athlete_id"] = restyled["athlete_id"].map(lambda v: f"{v:.1f}")
    assert F.rows_sha256(frame) == F.rows_sha256(shuffled)
    assert F.rows_sha256(frame) == F.rows_sha256(restyled)
    assert F.rows_sha256(frame) != F.rows_sha256(frame.iloc[:-1])


# --------------------------------------------------------------------------
# The estimators, against things they must equal
# --------------------------------------------------------------------------


def test_pooled_vmr_recovers_a_poisson_at_one() -> None:
    rng = np.random.default_rng(19)
    cells = np.repeat(np.arange(4000), 6)
    frame = pd.DataFrame({"cell": cells, "x": rng.poisson(3.0, size=cells.size).astype(float)})
    vmr, rows, count = F.pooled_vmr(frame, "x", ["cell"])
    assert rows == cells.size
    assert count == 4000
    assert vmr == pytest.approx(1.0, abs=0.03)


def test_pooled_vmr_reports_overdispersion_when_it_is_there() -> None:
    """A negative binomial with a known variance-to-mean, recovered."""
    rng = np.random.default_rng(23)
    cells = np.repeat(np.arange(4000), 6)
    mean, phi = 3.0, 2.0
    lam = rng.gamma(shape=mean / (phi - 1.0), scale=(phi - 1.0), size=cells.size)
    frame = pd.DataFrame({"cell": cells, "x": rng.poisson(lam).astype(float)})
    vmr, _, _ = F.pooled_vmr(frame, "x", ["cell"])
    assert vmr == pytest.approx(phi, rel=0.06)


def test_pooled_vmr_is_allowed_to_come_out_below_one() -> None:
    """Underdispersion is the case the Panjer family's binomial member exists for.

    `turnovers` measures below 1 on this data, and a estimator that could not
    report it -- or a family that could not represent it -- would silently widen
    the market this lab quotes ten thousand times.
    """
    rng = np.random.default_rng(29)
    cells = np.repeat(np.arange(4000), 6)
    frame = pd.DataFrame(
        {"cell": cells, "x": rng.binomial(10, 0.4, size=cells.size).astype(float)}
    )
    vmr, _, _ = F.pooled_vmr(frame, "x", ["cell"])
    assert vmr == pytest.approx(0.6, rel=0.06)
    assert vmr < 1.0


def test_pooled_vmr_ignores_cells_of_one_rather_than_charging_them_a_variance() -> None:
    """A cell with one observation has a mean and no variance.

    Counted as if it had one, it contributes a squared residual of zero against
    its own mean and eats a degree of freedom, which drags every dispersion
    downward -- and hardest on exactly the players with the fewest repeated
    minute counts, who are the bench players a book quotes at the shortest lines.
    Built here so the singletons are wildly off the pooled mean: if they were
    being counted at all, the answer would move.
    """
    rng = np.random.default_rng(53)
    paired = np.repeat(np.arange(3000), 4)
    singletons = np.arange(3000, 3000 + 20_000)
    frame = pd.DataFrame(
        {
            "cell": np.concatenate([paired, singletons]),
            "x": np.concatenate(
                [
                    rng.poisson(3.0, size=paired.size).astype(float),
                    np.full(singletons.size, 300.0),
                ]
            ),
        }
    )
    vmr, rows, cells = F.pooled_vmr(frame, "x", ["cell"])
    assert rows == paired.size, "the singleton cells were counted as observations"
    assert cells == 3000
    assert vmr == pytest.approx(1.0, abs=0.05)


def test_the_role_prior_is_minutes_weighted_and_not_an_average_of_rates() -> None:
    """A four-minute night must not weigh what a thirty-four-minute night says.

    The two differ whenever minutes and rate are correlated, which is the whole
    reason the table is indexed by minutes in the first place. Built so they
    differ by a factor of three: one long efficient night against nine short
    barren ones.
    """
    rows = 10
    frame = pd.DataFrame(
        {
            "bucket": np.zeros(rows, dtype=int),
            "minutes": np.array([36.0] + [4.0] * 9),
            "points": np.array([36.0] + [0.0] * 9),
        }
    )
    for market in F.RATE_MARKETS:
        frame[market] = frame["points"]
    tables, counts, _ = F.role_priors(frame)
    minutes_weighted = 36.0 / (36.0 + 9 * 4.0)
    average_of_rates = (1.0 + 9 * 0.0) / 10.0
    assert minutes_weighted == pytest.approx(0.5)
    assert average_of_rates == pytest.approx(0.1)
    assert tables["points"][0] == pytest.approx(minutes_weighted)
    assert counts[0] == rows


def test_non_finite_values_are_written_as_null_and_never_as_a_nan_token() -> None:
    """`json.dumps` writes a bare `NaN`, which is not JSON.

    A bucket with no rows is an absence, and it has to survive the round trip as
    one. A `NaN` token parses in Python and is rejected by a strict reader in any
    other language, so the file would be readable exactly where nobody was
    checking it.
    """
    cleaned = F.jsonable(
        {"a": float("nan"), "b": [float("inf"), 1.0], "c": {"d": float("-inf")}, "e": np.float64(2.5)}
    )
    assert cleaned == {"a": None, "b": [None, 1.0], "c": {"d": None}, "e": 2.5}
    assert json.loads(json.dumps(cleaned, allow_nan=False)) == cleaned


def test_the_credibility_fit_recovers_a_known_k() -> None:
    """Synthetic players with a known process and prior variance.

    `k = s^2 / tau^2`: process variance per minute over the spread of true rates.
    Generated at 60, the fit has to find it from the forecast loss alone.
    """
    rng = np.random.default_rng(31)
    # Large on purpose: the estimator is unbiased but the argmin of an empirical
    # loss is noisy, and at six thousand players it lands near 73 as often as 60.
    # A tolerance wide enough to pass at that size would not have caught a
    # genuinely wrong k, which is the only thing this test is for.
    players = 200_000
    process, spread = 0.6, 0.1
    truth = 0.4 + rng.normal(0.0, spread, players)
    prior_minutes = rng.uniform(60.0, 900.0, players)
    minutes = rng.uniform(10.0, 40.0, players)
    bank = truth + rng.normal(0.0, np.sqrt(process / prior_minutes))
    outcome = truth + rng.normal(0.0, np.sqrt(process / minutes))
    prior = np.full(players, 0.4)
    k, _ = F._fit_k(bank, prior, prior_minutes, outcome, minutes)
    assert k == pytest.approx(process / spread**2, rel=0.05)


def test_the_value_pmf_reconciles_against_the_box_scores_own_point_total() -> None:
    """One made free throw, one made two, one made three, and nothing else.

    If the event decomposition were wrong the implied point total would not
    reconcile, and the pmf would be a plausible-looking table of the wrong thing.
    """
    prepared = F.prepare(_frame(rows=2000, seed=37))
    played = prepared[prepared["played"]]
    pmf, evidence = F.value_pmf(played)
    assert sum(pmf) == pytest.approx(1.0)
    assert evidence["implied_point_total"] == pytest.approx(evidence["actual_point_total"], rel=1e-9)
    assert evidence["expected_value"] == pytest.approx(
        pmf[0] + 2 * pmf[1] + 3 * pmf[2]
    )


def test_the_minutes_lattice_carries_exactly_zero_mass_at_zero() -> None:
    """The book voids a did-not-play, so the priced quantity is conditional on appearing.

    Support starts at 1. If it ever started at 0 the model could multiply a
    did-not-play probability into a price, which is a wager the book does not
    settle.
    """
    assert F.MINUTES_SUPPORT_LOW == 1
    document = json.loads(FROZEN.read_text(encoding="utf-8"))
    payload = document["constants"]["minutes_pmf"]
    assert payload["value"]["support_low"] == 1
    assert payload["evidence"]["fit"]["mass_at_zero_minutes"] == 0.0
    for pmf in payload["value"]["pmf"]:
        if pmf is None:
            continue
        assert len(pmf) == F.MINUTES_SUPPORT_HIGH - F.MINUTES_SUPPORT_LOW + 1
        assert sum(pmf) == pytest.approx(1.0)


def test_the_compound_identity_is_arithmetic_and_not_a_fit() -> None:
    """`VMR(points) = (Var[V] + phi_N E[V]^2) / E[V]`, both ways round.

    The reconciliation constant is derived from two measured quantities and
    nothing new is fitted, so the effective dispersion must invert the implied
    VMR exactly. This is what makes the 22% gap a statement about the data
    rather than about an estimator.
    """
    value = {"expected_value": 1.864, "variance_of_value": 0.5063, "second_moment_over_first": 2.1356}
    dispersion = {"points_events": 1.38, "points": 2.33}
    got, _ = F.compound_reconciliation(dispersion, value)
    ev, var = value["expected_value"], value["variance_of_value"]
    assert got["compound_implied_points_vmr"] == pytest.approx(
        (var + dispersion["points_events"] * ev**2) / ev
    )
    round_trip = (var + got["effective_event_dispersion"] * ev**2) / ev
    assert round_trip == pytest.approx(dispersion["points"])
    assert got["compound_overstatement"] > 1.0


def test_the_role_prior_is_allowed_to_run_downward() -> None:
    """Rebounds per minute falls with minutes, and the table records it.

    A quadratic or any monotone form would be wrong about this forever: big men
    foul out, so the highest-minute bucket is not the most rebound-dense one.
    """
    document = json.loads(FROZEN.read_text(encoding="utf-8"))
    payload = document["constants"]["role_prior"]
    rebounds = payload["value"]["rebounds"]
    assert rebounds[-1] < rebounds[1]
    assert payload["evidence"]["fit"]["shape_over_buckets"]["rebounds"] != (
        "rises with minutes throughout"
    )
    points = payload["value"]["points"]
    assert points[-1] > points[1]


def test_the_fit_populations_are_never_screened_on_the_game_being_fitted() -> None:
    """The design's L9, asserted on the code rather than described in a docstring.

    A `minutes >= 15` screen truncates exactly the left tail a standing wager is
    exposed to. Every screen in the priced population reads the bank, so
    removing every realised column from a row must not change whether it is in.
    """
    trailing = F.with_trailing(F.prepare(_frame(rows=3000, seed=41)), F.MINUTES_HALF_LIFE)
    priced = F.priced_population(trailing)
    corrupted = trailing.copy()
    for column in ("points", "rebounds", "assists", "steals", "turnovers", "threes", "twos", "ones",
                   "points_events", "minutes"):
        corrupted[column] = 999.0
    corrupted_priced = F.priced_population(corrupted)
    assert set(priced.index) == set(corrupted_priced.index)


# --------------------------------------------------------------------------
# The frozen file, against the fitter that wrote it
# --------------------------------------------------------------------------


def test_the_frozen_file_records_the_window_the_fitter_declares() -> None:
    document = json.loads(FROZEN.read_text(encoding="utf-8"))
    assert document["fit_seasons"] == list(F.FIT_SEASONS)
    assert document["validation_season"] == F.VALIDATION_SEASON
    assert document["price_season_floor"] == F.PRICE_SEASON
    assert document["never_runs_at_price_time"] is True


def test_the_frozen_file_counts_the_window_rather_than_quoting_it() -> None:
    """The census in the file is the census in the table.

    2019-2023 holds 890,514 player-games in the table, over 34,165 athletes, and
    569,025 of those rows are appearances. Three of those numbers are not the
    same as "rows the fit used", and the file has to say which is which:

    * **one** row carries no readable athlete id and is dropped, leaving 890,513;
    * **5,029** rows say the player appeared and carry no minutes -- a logged
      appearance with a blank or zero minute count. A per-minute rate cannot be
      formed from them, so 563,996 rows are usable, not 569,025. Folding them
      into either bucket without saying so would misstate the sample by 0.9%.
    """
    document = json.loads(FROZEN.read_text(encoding="utf-8"))
    permitted = document["input"]["permitted_window_census"]
    fit = document["input"]["fit_census"]
    held = document["input"]["held_out_census"]
    assert permitted["rows_in_the_table"] == 890_514
    assert permitted["rows_with_no_readable_athlete_id"] == 1
    assert permitted["rows"] == 890_513
    assert permitted["appeared_rows"] == 569_025
    assert permitted["appeared_but_no_minutes_rows"] == 5_029
    assert permitted["played_rows"] == 563_996
    assert permitted["played_rows"] + permitted["appeared_but_no_minutes_rows"] == (
        permitted["appeared_rows"]
    )
    assert permitted["appeared_rows"] + permitted["did_not_play_rows"] == permitted["rows"]
    assert permitted["athletes"] == 34_165
    assert fit["rows_in_the_table"] + held["rows_in_the_table"] == permitted["rows_in_the_table"]
    assert fit["played_rows"] + held["played_rows"] == permitted["played_rows"]
    assert fit["seasons"] == [2019, 2020, 2021, 2022]
    assert held["seasons"] == [2023]
    assert document["input"]["fit_slice_sha256"] != document["input"]["held_out_slice_sha256"]


def test_the_dispersion_constants_choose_a_panjer_member_on_each_side_of_one() -> None:
    """Not every market is overdispersed, and the file must be able to say so."""
    document = json.loads(FROZEN.read_text(encoding="utf-8"))
    value = document["constants"]["conditional_dispersion"]["value"]
    assert value["turnovers"] < 1.0, "turnovers is underdispersed conditional on minutes"
    assert value["rebounds"] > 1.0
    assert value["points_events"] > 1.0
    evidence = document["constants"]["conditional_dispersion"]["evidence"]["fit"]
    assert evidence["turnovers"]["panjer_family"] == "binomial"
    assert evidence["rebounds"]["panjer_family"] == "negative binomial"


def test_the_credibility_gate_reports_the_range_it_could_actually_run_on() -> None:
    """The design declared 10-900 prior minutes; R2 empties the bottom bank.

    The file has to say which gate ran. Narrowing a declared check and reporting
    it as the declared check is the failure this asserts against.
    """
    document = json.loads(FROZEN.read_text(encoding="utf-8"))
    evidence = document["constants"]["rate_shrinkage_k"]["evidence"]
    assert "10 to 900" in evidence["gate_as_declared"]
    assert "60 to 900" in evidence["gate_as_run"]
    for market, entry in evidence["fit"].items():
        bank = entry["k_by_evidence_bank_prior_minutes"]["10-60"]
        assert bank["k"] is None and bank["rows"] == 0, market
        assert entry["banks_actually_checked"] == 3, market
        assert entry["spread_across_checked_banks"] <= F.K_STABILITY_MAX_SPREAD, market
    # Pinned, because every "passes the gate" above is only as strong as the
    # gate. The design declared 2x in advance; widening it after seeing the
    # spreads is how a market that failed becomes a market that passed.
    assert F.K_STABILITY_MAX_SPREAD == 2.0
    assert F.K_STABILITY_BANDS[0] == (10.0, 60.0)


def test_a_market_whose_k_is_unstable_is_recorded_unfittable_rather_than_averaged() -> None:
    """The refusal path, exercised on data built to fail the gate.

    Nothing in the frozen file fails it today, and a refusal path that has never
    run is not a path. The bank rate here carries a different amount of signal at
    small and large evidence banks, which is exactly the condition the design's
    2x gate is aimed at.
    """
    rng = np.random.default_rng(47)
    rows = 40_000
    prior_minutes = np.exp(rng.uniform(np.log(60.0), np.log(900.0), rows))
    minutes = rng.uniform(10.0, 40.0, rows)
    truth = 0.4 + rng.normal(0.0, 0.1, rows)
    # A bank whose noise does NOT fall as 1/M: at large banks it stays as noisy
    # as at small ones, so the optimal k rises steeply with the bank size.
    bank = truth + rng.normal(0.0, 0.05 + 0.0004 * prior_minutes, rows)
    frame = pd.DataFrame(
        {
            "bucket": np.zeros(rows, dtype=int),
            "prior_minutes": prior_minutes,
            "minutes": minutes,
            "bank_points": bank * prior_minutes,
            "points": (truth + rng.normal(0.0, np.sqrt(0.6 / minutes))) * minutes,
        }
    )
    for market in F.RATE_MARKETS:
        if market == "points":
            continue
        frame[market] = frame["points"]
        frame[f"bank_{market}"] = frame["bank_points"]
    priors = {market: [0.4] * len(F.BUCKET_LABELS) for market in F.RATE_MARKETS}
    _, report, unfittable = F.credibility(frame, frame.iloc[:0], priors)
    assert "points" in unfittable
    assert "not stable across evidence banks" in unfittable["points"]
    assert report["points"]["spread_across_checked_banks"] > F.K_STABILITY_MAX_SPREAD


def test_the_design_is_re_measured_on_its_own_window_rather_than_quoted() -> None:
    """Every design number that could be checked was recomputed on 2021-2022.

    The value pmf reproduces to four decimals, which is what makes the
    disagreements elsewhere in the file credible rather than a difference in how
    a scoring event was counted.
    """
    document = json.loads(FROZEN.read_text(encoding="utf-8"))
    reproduction = document["design_reproduction"]
    assert reproduction["seasons"] == [2021, 2022]
    measured = reproduction["value_pmf"]["measured"]
    published = reproduction["value_pmf"]["design_published"]
    assert max(abs(a - b) for a, b in zip(measured, published)) <= 0.005
    disagreements = {entry["quantity"]: entry for entry in document["design_disagreements"]}
    assert disagreements["conditional_dispersion.points_events"]["agrees"] is False
    assert (
        disagreements["points_compound_reconciliation.effective_event_dispersion"]["agrees"] is True
    )
    assert disagreements["residual_correlation.points|assists"]["agrees"] is False
