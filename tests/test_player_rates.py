"""What `models/player_rates.py` must be true about before it may price anything.

The estimator turns a cut player frame into a projection. Nothing here measures
an edge, a loss or a verdict — `models/player_distributions.py` is not written,
so no probability exists — and every number below is either read off a fixture
or off the frozen constants.

The properties, and the specific defect each is arranged against:

* **the cut** is `slate_date < day`, played rows only, `did_not_play` read
  through `settlement`'s own truth reader. `bool("False")` is `True`, and
  reading that column with `bool()` marks every player who did play as absent;
* **the minutes object** is an empirical pmf over 1..45 with **exactly zero**
  mass at zero, because the book voids a did-not-play and the priced quantity
  is conditional on him appearing;
* **`dnp_probability` is a diagnostic** and is never multiplied into anything —
  asserted by pricing the same athlete against two shapes files that differ
  only there and demanding the lattice and the rates be bit-identical;
* **the rate is minutes-weighted**, never per-game-averaged;
* **the shrink target is the role prior by projected-minutes bucket**, and it
  is allowed to run DOWNWARD with minutes, which rebounds does.

The two that hold this file to the rest of the tree: the estimator reproduces
`scripts/fit_player_model.with_trailing` column for column, because it may not
import it and a second copy of an estimator is how two windows come to
disagree; and `tilt_to_mean` reproduces `distributions.tilt_to_efficiency` to
1e-12, because it could not import that either and a second tilt would be a
second operation.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from cbb_betting_lab import settlement
from cbb_betting_lab.conferences import Tier, TierTable
from cbb_betting_lab.models import distributions as D
from cbb_betting_lab.models import player_rates as PR
from cbb_betting_lab.models.player_shapes import (
    ShapesFileError,
    load_player_shapes,
)
from cbb_betting_lab.providers import player_names
from cbb_betting_lab.reports import price_backtest as PB

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "src" / "cbb_betting_lab" / "models" / "player_rates.py"
SHAPES = REPO / "data" / "processed" / "cbb_player_shapes.json"

#: The season every prop quote in the store belongs to, and the only season the
#: 33 pre-registered hypotheses name.
PRICED_SEASON = 2024
DAY = "2024-01-15"


# --------------------------------------------------------------------------
# Fixtures
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


def _row(
    day: str,
    *,
    game_id: int,
    athlete_id: float = 4001.0,
    name: str = "Sean Bairstow",
    team_id: int = 55,
    minutes: float | None = 28.0,
    did_not_play: object = "False",
    season: int = PRICED_SEASON,
    points: float = 14.0,
    rebounds: float = 6.0,
    assists: float = 3.0,
    steals: float = 1.0,
    turnovers: float = 2.0,
    fgm: float = 5.0,
    threes: float = 2.0,
    ftm: float = 2.0,
) -> dict:
    return {
        "slate_date": day,
        "season": season,
        "game_id": game_id,
        "athlete_id": athlete_id,
        "athlete_display_name": name,
        "team_id": team_id,
        "opponent_id": 66,
        "home_away": "home",
        "did_not_play": did_not_play,
        "starter": True,
        "minutes": minutes,
        "points": points,
        "rebounds": rebounds,
        "assists": assists,
        "steals": steals,
        "turnovers": turnovers,
        "field_goals_made": fgm,
        "three_point_field_goals_made": threes,
        "free_throws_made": ftm,
    }


def _history(**overrides) -> pd.DataFrame:
    """Eight prior appearances for one athlete: enough to clear R2 and R3."""
    return pd.DataFrame(
        [_row(f"2024-01-{day:02d}", game_id=100 + day, **overrides) for day in range(1, 9)]
    )


def _prices(*subjects, event_id: str = "e1", market: str = "player_points") -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_id": event_id,
                "market": market,
                "player": subject,
                "selection": "over",
                "line": 14.5,
                "book": "dk",
                "game_id": 999,
                "season": PRICED_SEASON,
                "slate_date": DAY,
                "home_team": 55,
                "away_team": 66,
            }
            for subject in subjects
        ]
    )


def _one(slate: PR.PlayerSlate) -> PR.PlayerProjection:
    return next(iter(next(iter(slate.projections.values())).values()))


def _fitter():
    """`scripts/fit_player_model.py`, loaded as a SPECIFICATION, never imported.

    `tests/test_player_shapes_provenance.py::test_the_fit_script_is_not_
    importable_from_the_model_package` fails any module under `src/` that names
    it, because it reads the whole settlement table. A test is not under `src/`
    and is the one place the two estimators can be held against each other.
    """
    spec = importlib.util.spec_from_file_location(
        "fit_player_model", REPO / "scripts" / "fit_player_model.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# The cut, and how a boolean is read
# --------------------------------------------------------------------------


def test_did_not_play_is_read_the_way_settlement_reads_it() -> None:
    """One reading, not two, and `bool("False")` is the bug it exists against.

    `settlement`'s own docstring records the size of it: reading this column
    with `bool()` marks the 127,532 players who **did** play in 2025-26 as
    absent and voids the entire prop book. This module does not carry a second
    copy of the rule — it hands the column's distinct values to
    `settlement._is_true` itself — and this asserts the two agree value by
    value, including on the values a CSV round-trip actually produces.
    """
    battery = [
        True, False, "True", "False", "true", "false", "TRUE", "FALSE",
        "t", "f", "yes", "no", "y", "n", "1", "0", "", None, float("nan"),
        1, 0, 1.0, 0.0, np.True_, np.False_, "  True  ", "nan",
    ]
    column = pd.Series(battery, dtype=object)
    ours = PR._did_not_play(column)
    theirs = [
        settlement._is_true({"did_not_play": value}, "did_not_play") is True
        for value in battery
    ]
    assert list(ours) == theirs, dict(zip(map(repr, battery), zip(ours, theirs)))

    # The negative control, so the assertion above cannot be satisfied by a
    # reader that says True to everything.
    assert bool("False") is True, "this is the bug; if it stops being true, say so"
    assert PR._did_not_play(pd.Series(["False"] * 3)).tolist() == [False] * 3
    assert PR._did_not_play(pd.Series([True, False])).tolist() == [True, False]


def test_every_cut_this_module_makes_is_strictly_before_the_day() -> None:
    """`prior_roster` narrows and never widens, and the estimator refuses a leak."""
    frame = pd.concat(
        [_history(), pd.DataFrame([_row(DAY, game_id=999), _row("2024-02-01", game_id=1000)])],
        ignore_index=True,
    )
    roster = PR.prior_roster(frame, day=DAY, season=PRICED_SEASON, team_ids=(55, 66))
    assert set(roster["slate_date"]) == {f"2024-01-{d:02d}" for d in range(1, 9)}
    assert (roster["slate_date"] < DAY).all()

    with pytest.raises(PR.PlayerRatesError) as raised:
        PR.player_projections_for(
            day=DAY,
            player_history=frame,
            prices=_prices("Sean Bairstow"),
            shapes=_shapes(),
        )
    message = str(raised.value)
    assert "2 row(s)" in message and DAY in message, message


def test_only_played_rows_enter_the_bank() -> None:
    """A did-not-play, a sub-minute cameo and a blank minutes cell are all out.

    `played` is `appeared AND minutes is a number AND minutes >= 1.0`, which is
    the fitter's rule. A row logged as having appeared and carrying no minutes
    cannot produce a per-minute rate and is counted in neither bucket rather
    than folded into one.
    """
    frame = pd.DataFrame(
        [
            _row("2024-01-01", game_id=1, minutes=20.0),
            _row("2024-01-02", game_id=2, minutes=None, did_not_play="True"),
            _row("2024-01-03", game_id=3, minutes=0.5),
            _row("2024-01-04", game_id=4, minutes=None),
            _row("2024-01-05", game_id=5, minutes=30.0),
        ]
    )
    evidence = PR.trailing_evidence(frame, half_life=4.0)
    row = evidence.iloc[0]
    assert int(row["prior_games"]) == 2, "only the 20- and 30-minute rows played"
    assert float(row["prior_minutes"]) == pytest.approx(50.0)
    assert float(row["bank_points"]) == pytest.approx(28.0), "two rows of 14 points"


def test_the_trailing_bank_never_contains_the_game_it_projects() -> None:
    """The fitter's own leak test, one level down and at price time.

    Corrupt every row dated on or after the day being priced and the evidence
    does not move, because the cut removed them before this function saw them.
    """
    history = _history()
    tonight = pd.DataFrame([_row(DAY, game_id=999, minutes=45.0, points=99.0)])
    before = PR.trailing_evidence(history, half_life=4.0)
    after = PR.trailing_evidence(
        PR.prior_roster(
            pd.concat([history, tonight], ignore_index=True),
            day=DAY,
            season=PRICED_SEASON,
            team_ids=(55,),
        ),
        half_life=4.0,
    )
    pd.testing.assert_frame_equal(before, after)


def test_the_bank_resets_at_every_season_boundary() -> None:
    """No cross-season carry-over, and it is the November census's largest driver.

    The fitter says outright that admitting carry-over "would need a decay
    constant nobody has fitted". Combined with R2 this refuses every player,
    returning starters included, for the first four appearances of every
    season. That has to be read before the census is.
    """
    frame = pd.concat(
        [
            pd.DataFrame([_row(f"2023-01-{d:02d}", game_id=d, season=2023) for d in range(1, 9)]),
            pd.DataFrame([_row("2023-11-10", game_id=50)]),
        ],
        ignore_index=True,
    )
    evidence = PR.trailing_evidence(frame, half_life=4.0)
    this_season = evidence.loc[(float(PRICED_SEASON), 4001)]
    assert int(this_season["prior_games"]) == 1, "last season's eight games do not carry"
    assert float(this_season["bank_points"]) == pytest.approx(14.0)

    slate = PR.player_projections_for(
        day="2023-11-12",
        player_history=frame,
        prices=_prices("Sean Bairstow"),
        shapes=_shapes(),
    )
    projection = _one(slate)
    assert projection.priceable is False
    assert projection.unpriceable_reason == PR.R2_TOO_THIN


def test_the_estimator_reproduces_the_fitters_trailing_columns() -> None:
    """Column for column against `fit_player_model.with_trailing`, on real rows.

    This module may not import the fitter, so the only thing holding the two
    estimators together is this test. It runs the fitter's row-level trailing
    columns over the tracked fixture corpus and asserts that, for each row, the
    bank this module builds from the rows *strictly earlier than that row's
    day* is the same numbers.

    **Where they differ, they differ in one direction and it is the safe one.**
    The fitter orders within a day by `game_id`, so a player's second game of a
    calendar day carries the first in its bank. This module cuts on
    `slate_date < day` and cannot: at sixty minutes to tip the earlier game is
    a row dated today, and today is exactly what the leak rule forbids. Those
    rows are asserted separately to have a bank that is smaller or equal, never
    larger.
    """
    fitter = _fitter()
    raw = pd.read_csv(
        REPO / "tests" / "fixtures" / "real_data" / "cbb_player_games.csv",
        low_memory=False,
    )
    busiest = raw.groupby("athlete_id").size().sort_values(ascending=False)
    sample = raw[raw["athlete_id"].isin(list(busiest.index[:40]))].copy()
    assert len(sample) >= 100, f"only {len(sample)} fixture rows; too few to hold anything"

    trailing = fitter.with_trailing(fitter.prepare(sample), fitter.MINUTES_HALF_LIFE)
    compared = 0
    same_day = 0
    for _, expected in trailing.iterrows():
        day = str(expected["slate_date"])
        season = int(expected["season"])
        prior = sample[sample["slate_date"].astype(str) < day]
        prior = prior[pd.to_numeric(prior["season"], errors="coerce") == season]
        evidence = PR.trailing_evidence(prior, half_life=fitter.MINUTES_HALF_LIFE)
        key = (float(season), PR._athlete_key(expected["athlete_id"]))
        if key not in evidence.index:
            assert float(expected["prior_games"]) == 0.0
            continue
        got = evidence.loc[key]
        if float(got["prior_games"]) != float(expected["prior_games"]):
            assert float(got["prior_games"]) < float(expected["prior_games"]), (
                "the price-time bank is larger than the settlement-time bank, "
                "which means it read something the fitter did not"
            )
            same_day += 1
            continue
        compared += 1
        for column in (
            "prior_minutes",
            "bank_points",
            "bank_points_events",
            "bank_rebounds",
            "bank_assists",
            "bank_threes",
            "bank_steals",
            "bank_turnovers",
            "bank_ones",
            "bank_twos",
        ):
            assert float(got[column]) == pytest.approx(
                float(expected[column]), abs=1e-9
            ), f"{column} at {day} for {expected['athlete_id']}"
        ours, theirs = float(got["projected_minutes"]), float(expected["projected_minutes"])
        assert (math.isnan(ours) and math.isnan(theirs)) or ours == pytest.approx(
            theirs, abs=1e-9
        )
    print(
        f"{compared:,} fixture rows agreed column for column; {same_day:,} "
        "carried an earlier game on the same calendar day, which this module "
        "may not read"
    )
    assert compared >= 100


# --------------------------------------------------------------------------
# The minutes object
# --------------------------------------------------------------------------


def test_the_minutes_lattice_is_forty_six_long_and_carries_exactly_zero_at_zero() -> None:
    """Design 3's D4 shape, asserted here as well as in the distributions file.

    Exactly zero, compared with `is`-strength equality rather than a tolerance,
    because the whole content of the claim is that `dnp_probability` cannot be
    discounted into a price. The book voids a did-not-play; the priced quantity
    is `P(stat > line | he appears)`, and a lattice carrying `P(0 minutes)`
    would discount every projection by the chance of a void that pays nothing
    back.
    """
    shapes = _shapes()
    for projected, bucket in ((9.0, 1), (18.0, 4), (27.4, 6), (38.0, 8)):
        lattice = PR.minutes_lattice(
            projected_minutes=projected, bucket=bucket, shapes=shapes
        )
        assert len(lattice) == 46, "index is the number of minutes; 0..45 is 46 long"
        assert lattice[0] == 0.0
        assert sum(lattice) == pytest.approx(1.0, abs=1e-12)
        assert all(value >= 0.0 for value in lattice)


def test_tilt_to_mean_reproduces_tilt_to_efficiency_on_the_six_point_lattice() -> None:
    """To 1e-12, so the new tilt is provably the same operation and not a second one.

    Design 3 says to import `tilt_to_efficiency`. It cannot be:
    `distributions._POINTS` is a module-level `arange(6)` and the support check
    refuses any target above 5.0, so handing it a 46-long minutes base raises.
    That is asserted here too, because a disagreement with the design has to be
    demonstrated rather than described.
    """
    support = np.arange(len(D.PER_POSSESSION_POINTS), dtype=float)
    for target in (0.5, 0.944, 1.0, 1.083, 2.0, 3.5, 4.9):
        theirs = D.tilt_to_efficiency(target)
        ours = PR.tilt_to_mean(
            D.PER_POSSESSION_POINTS, support=support, target=target
        )
        assert np.max(np.abs(theirs - ours)) < 1e-12, target

    with pytest.raises(D.DistributionError) as raised:
        D.tilt_to_efficiency(24.0, base=[1.0 / 46] * 46)
    assert "outside the support" in str(raised.value)


def test_the_tilted_lattice_has_the_projected_mean() -> None:
    """To 1e-9, and it refuses rather than clips at the ceiling of the support.

    The frozen file declares `minutes_support` [1, 45] and no per-market count
    ceiling of any kind, so the refusal above 45 is the support's own — a
    projection at or beyond it has no tilt that reaches it, and there is no
    fitted constant to appeal to.
    """
    shapes = _shapes()
    for projected in (8.0, 12.5, 20.0, 27.4, 33.9, 40.0, 44.999):
        bucket = PR.role_prior_bucket(projected, bucket_edges=PR.BUCKET_EDGES)
        lattice = PR.minutes_lattice(
            projected_minutes=projected, bucket=bucket, shapes=shapes
        )
        mean = float(np.asarray(lattice) @ np.arange(len(lattice)))
        assert mean == pytest.approx(projected, abs=1e-9), projected

    for impossible in (45.0, 46.0, 1.0, 0.0):
        with pytest.raises(PR.PlayerRatesError) as raised:
            PR.minutes_lattice(projected_minutes=impossible, bucket=8, shapes=shapes)
        assert "outside the support" in str(raised.value), impossible


def test_the_did_not_play_diagnostic_never_reaches_the_lattice(tmp_path: Path) -> None:
    """`dnp_probability` is stored and is never multiplied into a price.

    Priced twice against two shapes files that differ **only** in
    `dnp_base_rate`, with the second one absurd. The stored diagnostic moves
    and the minutes lattice, the rates, the value mix and the credibility
    weights are bit-identical — not approximately, identically. That is the
    assertion; a docstring saying the same thing would go on being true after
    somebody multiplied it in.
    """
    history = _history()
    prices = _prices("Sean Bairstow")

    def _absurd(document: dict) -> None:
        document["constants"]["dnp_base_rate"]["value"] = [0.99] * 9

    plain = _one(
        PR.player_projections_for(
            day=DAY, player_history=history, prices=prices, shapes=_shapes()
        )
    )
    moved = _one(
        PR.player_projections_for(
            day=DAY,
            player_history=history,
            prices=prices,
            shapes=_shapes_with(tmp_path, _absurd),
        )
    )

    assert plain.dnp_probability != moved.dnp_probability
    assert moved.dnp_probability == 0.99
    assert plain.minutes_pmf == moved.minutes_pmf
    assert plain.rates == moved.rates
    assert plain.prior_weight == moved.prior_weight
    assert plain.value_pmf == moved.value_pmf
    assert plain.priceable == moved.priceable is True

    # And it is not reachable: the function that builds the lattice does not
    # take it and cannot read it.
    assert set(inspect.signature(PR.minutes_lattice).parameters) == {
        "projected_minutes",
        "bucket",
        "shapes",
    }


# --------------------------------------------------------------------------
# The rate
# --------------------------------------------------------------------------


def test_the_rate_is_minutes_weighted_and_never_per_game_averaged() -> None:
    """A four-minute night must not weigh what a thirty-four-minute night says.

    Two athletes with the same per-game average and different minute
    distributions must get different rates; if the estimator averaged per game
    they would be identical.
    """
    lopsided = pd.DataFrame(
        [
            _row(
                f"2024-01-{day:02d}",
                game_id=day,
                minutes=4.0 if day % 2 else 36.0,
                points=4.0 if day % 2 else 9.0,
            )
            for day in range(1, 9)
        ]
    )
    evidence = PR.trailing_evidence(lopsided, half_life=4.0).iloc[0]
    assert float(evidence["prior_minutes"]) == pytest.approx(160.0)
    assert float(evidence["bank_points"]) == pytest.approx(52.0)

    rate, weight = PR.shrink_rate(
        bank_stat=float(evidence["bank_points"]),
        prior_minutes=float(evidence["prior_minutes"]),
        prior_rate=0.3,
        k=0.0,
    )
    assert weight == 1.0
    minutes_weighted = 52.0 / 160.0
    per_game_averaged = (1.00 + 0.25) / 2.0
    assert minutes_weighted == pytest.approx(0.325)
    assert per_game_averaged == pytest.approx(0.625)
    assert rate == pytest.approx(minutes_weighted), (
        "the rate is the bank over the bank's minutes"
    )
    assert rate != pytest.approx(per_game_averaged, abs=1e-6), (
        "the rate is the mean of the per-game ratios, so a four-minute night "
        "weighs what a thirty-six-minute night says about it -- which is "
        "nearly twice the number, on the same eight games"
    )


def test_the_shrink_weight_is_prior_minutes_over_prior_minutes_plus_k() -> None:
    """`w = m / (m + k)`, with `k` read from the file and never written here.

    The measured reason R2 refuses at sixty prior minutes is in this formula:
    `60 / (60 + 102.834) = 0.3685` for points, so below it the majority of the
    projection is an average player in this role published under a named
    player's name.
    """
    ks = _shapes().value("rate_shrinkage_k")
    assert set(ks) == set(PR.STAT_KEYS)
    for stat, k in ks.items():
        for minutes in (60.0, 200.0, 900.0):
            rate, weight = PR.shrink_rate(
                bank_stat=minutes * 0.5, prior_minutes=minutes, prior_rate=0.1, k=k
            )
            assert weight == pytest.approx(minutes / (minutes + k))
            assert rate == pytest.approx(weight * 0.5 + (1.0 - weight) * 0.1)
    assert 60.0 / (60.0 + ks["points"]) == pytest.approx(0.3685, abs=5e-5)

    # No evidence at all is the prior itself, at weight zero -- never a
    # division by zero and never a rate of nothing.
    assert PR.shrink_rate(bank_stat=0.0, prior_minutes=0.0, prior_rate=0.25, k=1.0) == (
        0.25,
        0.0,
    )


def test_the_role_prior_is_allowed_to_run_downward() -> None:
    """Rebounds falls with minutes and nothing here imposes monotonicity.

    A quadratic, a log-link or any monotone functional form would be wrong
    about this forever: big men foul out, so the per-minute rebound rate runs
    from 0.16823 in the 8-12 bucket down to 0.13048 in the 36+ bucket. The
    estimator reads the table by index and applies no shape at all, which this
    asserts by reading the priced rate straight out of the table at w = 0.
    """
    table = _shapes().value("role_prior")
    rebounds = table["rebounds"]
    assert rebounds[1] == pytest.approx(0.16823, abs=5e-6)
    assert rebounds[8] == pytest.approx(0.13048, abs=5e-6)
    assert rebounds[8] < rebounds[1], "the table runs downward and must be allowed to"
    assert not all(b >= a for a, b in zip(rebounds, rebounds[1:])), "not monotone"

    for bucket, value in enumerate(rebounds):
        rate, weight = PR.shrink_rate(
            bank_stat=0.0, prior_minutes=0.0, prior_rate=value, k=52.0
        )
        assert weight == 0.0 and rate == value, (
            "at zero evidence the priced rate IS the table's own entry, so "
            "nothing between the file and the price reshapes it"
        )


def test_the_coincident_window_identity_holds_at_w_equal_one() -> None:
    """D5, composed from the public helpers rather than from a `shrinkage=False`.

    With the rate window and the minutes window set equal — the projection
    being the bank's own mean minutes — and the credibility weight forced to
    1.0, the decomposition `rate * minutes` must equal the direct per-game
    trailing mean to floating point. There is deliberately no `shrinkage: bool`
    flag on the estimator: this repository treats a mode flag as the
    `strict=False` a guard cannot have, so the identity is built from
    :func:`shrink_rate` with `k = 0`.
    """
    evidence = PR.trailing_evidence(_history(), half_life=4.0).iloc[0]
    prior_minutes = float(evidence["prior_minutes"])
    prior_games = int(evidence["prior_games"])
    coincident = prior_minutes / prior_games
    for stat in PR.STAT_KEYS:
        rate, weight = PR.shrink_rate(
            bank_stat=float(evidence[f"bank_{stat}"]),
            prior_minutes=prior_minutes,
            prior_rate=0.0,
            k=0.0,
        )
        assert weight == 1.0
        direct = float(evidence[f"bank_{stat}"]) / prior_games
        assert rate * coincident == pytest.approx(direct, abs=1e-12), stat


def test_the_combination_markets_agree_with_their_components() -> None:
    """D3 coherence, to 1e-9: a points line and a pra line cannot disagree.

    They are built from components over the **shared** minutes draw, never from
    their own history, which is the structural reason rather than a measured
    one. Both rival measurements agreed own-history buys nothing on the mean
    (MAE 5.097 against 5.099 — the design's numbers, quoted, not re-measured).
    """
    projection = _one(
        PR.player_projections_for(
            day=DAY,
            player_history=_history(),
            prices=_prices("Sean Bairstow"),
            shapes=_shapes(),
        )
    )
    assert projection.priceable is True
    for market, components in PR.MARKET_COMPONENTS.items():
        combined = PR.mean_for_market(projection, market)
        parts = sum(
            projection.rates[stat] * projection.projected_minutes for stat in components
        )
        assert combined == pytest.approx(parts, abs=1e-9), market
    assert PR.mean_for_market(projection, "player_pra") == pytest.approx(
        sum(
            PR.mean_for_market(projection, m)
            for m in ("player_points", "player_rebounds", "player_assists")
        ),
        abs=1e-9,
    )


def test_the_value_mix_is_the_players_own_and_shrinks_toward_the_league() -> None:
    """A centre and a shooting guard differ, and both differ from the league.

    The bank is in prior scoring events and `k` is fitted in the same unit, so
    a player with ten prior scoring events already carries weight
    `10 / (10 + 9.2201) = 0.5203` — much faster than the rate shrinks, which is
    what lets `player_threes` fall out of the points object.
    """
    shapes = _shapes()
    league = shapes.value("value_pmf")
    k = float(shapes.value("value_mix_shrinkage_events"))
    assert 10.0 / (10.0 + k) == pytest.approx(0.5203, abs=5e-5)

    centre, events, weight = PR.shrink_value_mix(
        bank_ones=40.0, bank_twos=120.0, bank_threes=0.0, league=league, k_events=k
    )
    guard, _, _ = PR.shrink_value_mix(
        bank_ones=40.0, bank_twos=40.0, bank_threes=80.0, league=league, k_events=k
    )
    assert events == 160.0 and weight == pytest.approx(160.0 / (160.0 + k))
    assert centre != guard
    assert centre[2] < league[2] < guard[2]
    assert sum(centre) == pytest.approx(1.0) and sum(guard) == pytest.approx(1.0)

    # No events at all is the league shape at weight zero, never a mix of
    # nothing and never a division by zero.
    assert PR.shrink_value_mix(
        bank_ones=0.0, bank_twos=0.0, bank_threes=0.0, league=league, k_events=k
    ) == (tuple(league), 0.0, 0.0)


# --------------------------------------------------------------------------
# The name, and the roster it is read against
# --------------------------------------------------------------------------


def test_a_name_reaching_two_athletes_refuses_and_never_picks() -> None:
    """R1: ambiguity resolves to nothing, never to a coin flip.

    `team_names`' comment holds here word for word, and it is what lets the
    readings be generous: a generous reading that reaches two people costs a
    refusal, not a settlement against the wrong athlete. Design C's
    `difflib >= 0.88` terminal step is deleted and stays deleted — combined
    with R1a it has no correct answer available for a debutant and will
    confidently match the nearest teammate.
    """
    frame = pd.concat(
        [
            _history(athlete_id=4001.0, name="Jaylen Smith"),
            _history(athlete_id=4002.0, name="Jordan Smith"),
        ],
        ignore_index=True,
    )
    slate = PR.player_projections_for(
        day=DAY,
        player_history=frame,
        prices=_prices("J. Smith"),
        shapes=_shapes(),
    )
    assert slate.projections == {}, "nothing was projected for an unreadable name"
    assert slate.name_refusals == {("e1", "J. Smith"): PR.R1_UNRESOLVED}
    assert slate.resolution_census["refused_name"] == 1
    assert set(slate.resolved) == set()

    resolution = PR.resolve_subject("J. Smith", roster=frame)
    assert resolution.candidates == 2 and resolution.athlete_id is None
    imported: set[str] = set()
    for node in ast.walk(ast.parse(MODULE.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert "difflib" not in imported, (
        "a fuzzy terminal step is back; it was deleted for a measured reason"
    )


def test_a_name_that_resolves_only_in_tonights_box_score_is_refused_as_R1a_and_counted() -> None:
    """The positive evidence that the model is not reading tonight's roster.

    The debutant plays tonight and has never played before. He is in the
    settlement table and he is not in the cut frame, so the model cannot reach
    him — and the refusal is a separate census bucket from R1, because a player
    this lab has not seen is a different fact from a name it cannot read.
    """
    settled = pd.concat(
        [
            _history(athlete_id=4001.0, name="Sean Bairstow"),
            pd.DataFrame([_row(DAY, game_id=999, athlete_id=4099.0, name="Brand New")]),
        ],
        ignore_index=True,
    )
    cut = PR.prior_roster(settled, day=DAY, season=PRICED_SEASON, team_ids=(55,))
    assert 4099.0 not in set(cut["athlete_id"]), "tonight's box score is not in the cut"

    slate = PR.player_projections_for(
        day=DAY,
        player_history=cut,
        prices=_prices("Brand New", "Sean Bairstow"),
        shapes=_shapes(),
    )
    assert slate.name_refusals == {("e1", "Brand New"): PR.R1A_TONIGHT_ONLY}
    assert slate.resolution_census["refused_debutant"] == 1
    assert "refused_name" not in slate.resolution_census, (
        "R1 and R1a are counted separately; a player this lab has not seen is "
        "not a name it cannot read"
    )
    assert set(slate.resolved) == {("e1", "Sean Bairstow")}
    assert set(slate.name_refusals) & set(slate.resolved) == set()


def test_the_roster_searched_is_never_keyed_on_the_game_being_priced(monkeypatch) -> None:
    """`build_index` is not called, and a prior-roster index is built instead.

    `providers.player_names.build_index` keys `(game_id, alias)` off the box
    score **of the game itself**. Resolving tonight's spelling against it is
    exactly the R1a leak — not a risk of one, the thing itself — so this
    asserts both that the module never names it and that calling it would be
    noticed if it did.
    """
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    named = {
        node.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Attribute) and node.attr == "build_index"
    }
    assert not named, "the estimator names `build_index`, which keys on tonight's game"

    def _explode(*args, **kwargs):  # pragma: no cover - it must not run
        raise AssertionError("build_index was called at price time")

    monkeypatch.setattr(player_names, "build_index", _explode)
    slate = PR.player_projections_for(
        day=DAY,
        player_history=_history(),
        prices=_prices("Sean Bairstow"),
        shapes=_shapes(),
    )
    assert set(slate.resolved) == {("e1", "Sean Bairstow")}

    # And the index it does build is keyed by the EVENT, not by tonight's game.
    index = PR._prior_index(_history(), event_id="e1")
    assert all(key[0] == "e1" for key in index.aliases)


def test_a_game_with_no_prior_roster_is_its_own_refusal() -> None:
    """Neither team has played: the lab has seen nobody, and it says which.

    Folding this into R1a would attribute to the athlete what belongs to the
    lab — every name on the board would come back as "a player this lab has
    not seen" on the opening night of a season, which is true of the roster and
    false as a statement about any one player.
    """
    elsewhere = pd.DataFrame(
        [_row(f"2023-11-{day:02d}", game_id=day, team_id=77) for day in range(1, 9)]
    )
    slate = PR.player_projections_for(
        day=DAY,
        player_history=elsewhere,
        prices=_prices("Sean Bairstow"),
        shapes=_shapes(),
    )
    assert slate.name_refusals == {("e1", "Sean Bairstow"): PR.R1B_NO_PRIOR_ROSTER}
    assert slate.resolution_census["refused_no_prior_roster"] == 1
    assert "refused_debutant" not in slate.resolution_census


def test_a_subject_is_counted_once_however_many_rungs_it_carries() -> None:
    """The census counts subjects and rungs apart, and never sums them.

    `player_points` carries a measured mean of 7.19 distinct lines per subject
    across a mean 4.6 books (design 10, quoted). A census over price ROWS would
    report a resolution rate of ladder rungs and call it a rate of players.
    """
    prices = pd.concat(
        [_prices("Sean Bairstow") for _ in range(9)], ignore_index=True
    )
    slate = PR.player_projections_for(
        day=DAY, player_history=_history(), prices=prices, shapes=_shapes()
    )
    assert len(slate.resolved) == 1
    assert slate.resolution_census["exact"] == 1
    assert slate.resolution_census["quotes:exact"] == 9


def test_the_per_tier_resolution_rate_is_reported_every_run() -> None:
    """Design 13, failure mode 5, and the gate that goes with it.

    Reported over resolved subjects only, because design 9 tiers a player by
    his OWN team and an unresolved name has none. The refused names are
    reported beside it with their count rather than distributed across the
    tiers, and the 2pp check is stated as being over the resolved.
    """
    frame = pd.concat(
        [
            _history(athlete_id=4001.0, name="High Major", team_id=55),
            pd.DataFrame(
                [
                    _row(
                        f"2024-01-{day:02d}",
                        game_id=200 + day,
                        athlete_id=4002.0,
                        name="Low Major",
                        team_id=66,
                        minutes=7.0,
                    )
                    for day in range(1, 12)
                ]
            ),
        ],
        ignore_index=True,
    )
    tiers = TierTable(
        team_tier={55: Tier.HIGH_MAJOR, 66: Tier.LOW_MAJOR},
        conference_tier={},
        team_margin={},
        conference_margin={},
        seasons=(2023,),
    )
    slate = PR.player_projections_for(
        day=DAY,
        player_history=frame,
        prices=_prices("High Major", "Low Major", "Nobody At All"),
        shapes=_shapes(),
        tiers=tiers,
    )
    census = PR.resolution_census(slate.projections, tiers=tiers)
    assert set(census) == {Tier.HIGH_MAJOR.value, Tier.LOW_MAJOR.value}
    assert census[Tier.HIGH_MAJOR.value]["priceable"] == 1
    assert census[Tier.LOW_MAJOR.value]["priceable"] == 0
    assert PR.untiered_name_refusals(slate) == 1

    with pytest.raises(PR.PlayerRatesError) as raised:
        PR.assert_tier_resolution_holds(census)
    assert "percentage points across tiers" in str(raised.value)
    assert "20.5%" in str(raised.value), "the gate cites the defect it exists for"

    flat = {
        Tier.HIGH_MAJOR.value: {"subjects": 100, "priceable": 90},
        Tier.LOW_MAJOR.value: {"subjects": 100, "priceable": 91},
    }
    PR.assert_tier_resolution_holds(flat)


# --------------------------------------------------------------------------
# Refusals, and what they are not
# --------------------------------------------------------------------------


def test_a_missing_entry_is_no_opinion_and_a_refusal_is_an_entry() -> None:
    """The two are counted separately, always, and this is the difference.

    A thin player is an entry with `priceable=False` and a full sentence; an
    athlete nobody quoted is not in the container at all. Summing them would
    report a model that declined as a model that was never asked, and the
    parallel rule already holds for `ratings.matchups_for`.
    """
    frame = pd.concat(
        [
            _history(athlete_id=4001.0, name="Sean Bairstow"),
            pd.DataFrame([_row("2024-01-01", game_id=1, athlete_id=4002.0, name="Thin Man")]),
            _history(athlete_id=4003.0, name="Never Quoted"),
        ],
        ignore_index=True,
    )
    slate = PR.player_projections_for(
        day=DAY,
        player_history=frame,
        prices=_prices("Sean Bairstow", "Thin Man"),
        shapes=_shapes(),
    )
    projections = slate.projections["e1"]
    assert set(projections) == {4001, 4002}, "4003 was never quoted; he has no entry"
    assert projections[4001].priceable is True
    assert projections[4002].priceable is False
    assert projections[4002].unpriceable_reason == PR.R2_TOO_THIN

    census = PR.refusal_census(slate.projections)
    assert census["priceable"] == 1
    assert sum(count for key, count in census.items() if key != "priceable") == 1


def test_the_refusal_thresholds_this_module_enforces_equal_the_declared_block() -> None:
    """Four games, sixty minutes, eight projected minutes -- one copy, held.

    The frozen file keeps these in a `declared` block that `PlayerShapes`
    exposes no accessor for and `_check_constant` never inspects, so unlike the
    twelve fitted constants they carry no fit window. Design L4 says to assert
    that no constant lacks one. This is that assertion in the form the contract
    asked for: declared here, held against the file, red the day the two drift.
    """
    declared = json.loads(SHAPES.read_text(encoding="utf-8"))["declared"]
    assert declared["refusal_thresholds"] == {
        "min_prior_games": PR.MIN_PRIOR_GAMES,
        "min_prior_minutes": PR.MIN_PRIOR_MINUTES,
        "min_projected_minutes": PR.MIN_PROJECTED_MINUTES,
    }
    assert tuple(declared["bucket_edges"]) == PR.BUCKET_EDGES
    assert tuple(declared["bucket_labels"]) == PR.BUCKET_LABELS
    assert tuple(declared["minutes_support"]) == PR.MINUTES_SUPPORT
    assert declared["prior_season_min_games"] == PR.PRIOR_SEASON_MIN_GAMES
    assert (PR.MIN_PRIOR_GAMES, PR.MIN_PRIOR_MINUTES, PR.MIN_PROJECTED_MINUTES) == (
        4,
        60.0,
        8.0,
    ), "the design's declared thresholds, in the design's units"

    # `declared` carries no fit window and the guard does not look at it, which
    # is why this equality is checked at price time as well as here.
    with pytest.raises(ShapesFileError):
        _shapes().value("refusal_thresholds")


def test_a_declared_block_that_drifts_refuses_rather_than_prices(tmp_path: Path) -> None:
    """Two copies of a threshold is how a fit and a price refuse two populations."""

    def _drift(document: dict) -> None:
        document["declared"]["refusal_thresholds"]["min_prior_minutes"] = 30.0

    with pytest.raises(PR.PlayerRatesError) as raised:
        PR.player_projections_for(
            day=DAY,
            player_history=_history(),
            prices=_prices("Sean Bairstow"),
            shapes=_shapes_with(tmp_path, _drift),
        )
    assert "refusal_thresholds" in str(raised.value)


def test_the_thresholds_bite_where_the_design_says_they_do() -> None:
    """R2 on both of its arms, and R3 on both of its."""
    shapes = _shapes()
    prices = _prices("Sean Bairstow")

    thin_games = pd.DataFrame(
        [_row(f"2024-01-{d:02d}", game_id=d, minutes=40.0) for d in range(1, 4)]
    )
    thin_minutes = pd.DataFrame(
        [_row(f"2024-01-{d:02d}", game_id=d, minutes=10.0) for d in range(1, 6)]
    )
    short = pd.DataFrame(
        [_row(f"2024-01-{d:02d}", game_id=d, minutes=7.0) for d in range(1, 12)]
    )
    for frame, reason, why in (
        (thin_games, PR.R2_TOO_THIN, "three prior appearances is fewer than four"),
        (thin_minutes, PR.R2_TOO_THIN, "fifty prior minutes is fewer than sixty"),
        (short, PR.R3_NO_MINUTES, "seven projected minutes is below eight"),
    ):
        projection = _one(
            PR.player_projections_for(
                day=DAY, player_history=frame, prices=prices, shapes=shapes
            )
        )
        assert projection.priceable is False, why
        assert projection.unpriceable_reason == reason, why
        assert projection.athlete_id is not None, (
            "a refusal on the athlete still knows which athlete it refused; "
            "that is what makes it different from a name refusal"
        )


def test_an_unfittable_constant_refuses_the_market_rather_than_substituting_a_value(
    tmp_path: Path,
) -> None:
    """R5, driven through a synthetic file: the shipped `unfittable` block is empty.

    Two levels, because the block's keys are either a constant name or
    `constant.market`. A per-stat refusal drops that stat and leaves the rest
    standing; refusing something every market needs makes the projection itself
    unpriceable. Neither substitutes a value, and `PlayerShapes.value` raises
    rather than returning one, which is what stops a silent fallback.
    """
    history, prices = _history(), _prices("Sean Bairstow")
    sentence = "measured and found unstable across evidence banks."

    def _stat(document: dict) -> None:
        document["unfittable"] = {
            "rate_shrinkage_k.threes": {"reason": sentence, "cost": "threes is refused."}
        }

    def _structural(document: dict) -> None:
        document["unfittable"] = {
            "minutes_pmf": {"reason": sentence, "cost": "no market prices."}
        }

    per_stat = _one(
        PR.player_projections_for(
            day=DAY, player_history=history, prices=prices,
            shapes=_shapes_with(tmp_path, _stat, name="stat.json"),
        )
    )
    assert "threes" not in per_stat.rates, "a refused constant may not be substituted"
    assert set(per_stat.refused_stats) == {"threes"}
    assert sentence in per_stat.refused_stats["threes"]
    assert per_stat.priceable is True, "the other six markets still have constants"
    assert math.isnan(PR.mean_for_market(per_stat, "player_threes"))

    whole = _one(
        PR.player_projections_for(
            day=DAY, player_history=history, prices=prices,
            shapes=_shapes_with(tmp_path, _structural, name="whole.json"),
        )
    )
    assert whole.priceable is False
    assert whole.unpriceable_reason.startswith(PR.R5_NO_WALK_FORWARD_FIT)
    assert sentence in whole.unpriceable_reason


def test_the_two_markets_refused_by_name_never_become_an_eleventh() -> None:
    """`player_first_basket` and `player_double_double`, refused before the run.

    Both are absent from the 33 pre-registered hypotheses, because a refused
    market costs no degree of freedom. Asking this module for a mean on either
    raises with the census wording rather than returning one.
    """
    assert len(PR.PRICED_MARKETS) == 10
    assert set(PR.MARKETS_REFUSED_BY_NAME) == {
        "player_first_basket",
        "player_double_double",
    }
    assert not set(PR.MARKETS_REFUSED_BY_NAME) & set(PR.PRICED_MARKETS)

    projection = _one(
        PR.player_projections_for(
            day=DAY, player_history=_history(), prices=_prices("Sean Bairstow"),
            shapes=_shapes(),
        )
    )
    for market in PR.MARKETS_REFUSED_BY_NAME:
        with pytest.raises(PR.PlayerRatesError) as raised:
            PR.mean_for_market(projection, market)
        assert "refused" in str(raised.value)
    assert "sample of one" in PR.MARKETS_REFUSED_BY_NAME["player_double_double"]
    assert "first field goal" in PR.MARKETS_REFUSED_BY_NAME["player_first_basket"]


def test_a_frame_with_no_box_score_columns_is_refused_not_defaulted() -> None:
    """R6, which the design does not have and the wiring made real.

    `reports/card_matchups.load_player_games` reads only the eight columns
    `slate.REQUIRED_PLAYER_COLUMNS` declares. Those eight can project minutes
    and cannot form a per-minute rate, so a rate built from them would be the
    role table wearing a player's name. The refusal names the missing columns
    rather than defaulting them, which is `require_columns`' rule: a missing
    column read as a zero is how the football lab's props backtest reported
    zero bets and had that read as a finding about the model.
    """
    from cbb_betting_lab.models import slate as SLATE

    eight = _history()[list(SLATE.REQUIRED_PLAYER_COLUMNS)]
    projection = _one(
        PR.player_projections_for(
            day=DAY, player_history=eight, prices=_prices("Sean Bairstow"),
            shapes=_shapes(),
        )
    )
    assert projection.priceable is False
    assert projection.unpriceable_reason.startswith(PR.R6_NO_BOX_SCORE_COLUMNS)
    for column in ("points", "rebounds", "field_goals_made"):
        assert column in projection.unpriceable_reason
    assert projection.rates == {}
    # It still knows what it DID have: minutes are projectable from the eight.
    assert projection.projected_minutes == pytest.approx(28.0)
    assert len(projection.minutes_pmf) == 46 and projection.minutes_pmf[0] == 0.0


def test_the_matchup_is_not_read_and_cannot_be() -> None:
    """The player price reads NOTHING from `ratings.Matchup`, by construction.

    Not a convention: the estimator's signature has nowhere to put one, and it
    imports neither `models.ratings` nor anything from `reports/`. Inheriting
    `matchup()`'s refusals would delete about 1.8% of quotes, concentrated
    before 20 November, with a 2.3x tier skew and zero low-major (the design's
    measurement, quoted), for adjustments worth 0.13-0.29% of RMSE against an
    oracle ceiling of 0.7-0.9%.
    """
    parameters = set(inspect.signature(PR.player_projections_for).parameters)
    assert parameters == {
        "day", "player_history", "prices", "shapes", "competition", "tiers"
    }
    source = MODULE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
    assert not any("ratings" in name for name in imported), sorted(imported)
    assert not any(name.startswith("cbb_betting_lab.reports") for name in imported)


# --------------------------------------------------------------------------
# The seam this module sits behind
# --------------------------------------------------------------------------


def test_another_competition_is_refused_rather_than_priced_with_these_shapes() -> None:
    """A constant used where nobody measured it is the season leak wearing a sport.

    The frozen role prior says 0.4395 points per minute in the 36+ bucket. That
    is a fact about college basketball box scores and about nothing else, and
    there is no shapes file for a second competition, so the estimator refuses
    rather than reusing these. `competition` is therefore load-bearing rather
    than a parameter carried to satisfy a signature.
    """
    import dataclasses

    from cbb_betting_lab.competitions import CBB

    other = dataclasses.replace(CBB, key="nhl", title="NHL")
    with pytest.raises(PR.PlayerRatesError) as raised:
        PR.player_projections_for(
            day=DAY,
            player_history=_history(),
            prices=_prices("Sean Bairstow"),
            shapes=_shapes(),
            competition=other,
        )
    assert "nhl" in str(raised.value) and "cbb" in str(raised.value)
    assert _shapes().value("role_prior")["points"][8] == pytest.approx(
        0.4395, abs=5e-5
    ), "the number the refusal's docstring quotes"


def test_the_signature_is_keyword_only_and_declares_its_frames_without_defaults() -> None:
    """`_refuse_undeclared_frames` cannot be walked past from here.

    It refuses a pricer whose frame parameter carries a default and refuses
    `**kwargs` on sight, and this module sits behind that seam. A default on
    `player_history` would let a caller forget `frames=` and get `None`, which
    is the silence the whole `frames=` mechanism exists to end.
    """
    signature = inspect.signature(PR.player_projections_for)
    for name, parameter in signature.parameters.items():
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, name
    for name in ("day", "player_history", "prices", "shapes"):
        assert signature.parameters[name].default is inspect.Parameter.empty, name
    assert signature.parameters["competition"].default is not inspect.Parameter.empty
    assert signature.parameters["tiers"].default is None
    assert PB.unsupplied_arguments(
        PR.player_projections_for, {"day", "player_history", "prices", "shapes"}
    ) == []
    assert PB.unsupplied_arguments(PR.player_projections_for, {"day"}) == [
        "player_history",
        "prices",
        "shapes",
    ], "the check is reading this signature and not returning empty for everything"


def test_the_latest_day_this_module_reads_is_the_harnesss_definition() -> None:
    """The stamp is read the same way on both sides of the seam.

    A maximum written twice is still two places the literal string `"nan"` can
    sort above every real date.
    """
    frames = [
        pd.DataFrame(columns=["slate_date"]),
        pd.DataFrame({"slate_date": []}),
        pd.DataFrame({"slate_date": ["2024-01-02", "2024-01-09"]}),
        pd.DataFrame({"slate_date": ["2024-01-02", None, "nan", ""]}),
        pd.DataFrame({"minutes": [1.0, 2.0]}),
    ]
    for frame in frames:
        assert PR._latest_day(frame) == PB.latest_day(frame), frame.to_dict()


def test_the_seam_receives_the_record_and_reads_all_five_of_its_fields() -> None:
    """`models/slate.py` unpacks a `PlayerSlate`, and every field it reads is here.

    The record is a DECLARED DEVIATION from design 2's `tuple[dict, str]`: that
    return cannot carry an R1/R1a refusal, because a name that does not resolve
    has no athlete id and a container keyed only by athlete id makes design 7's
    own rule unrepresentable for the two refusals design 11 says must be
    printed every run.
    """
    from cbb_betting_lab.models import slate as SLATE

    slate = PR.player_projections_for(
        day=DAY, player_history=_history(), prices=_prices("Sean Bairstow"),
        shapes=_shapes(),
    )
    unpacked = SLATE._unpack(slate, player_history=_history())
    projections, resolved, refusals, stamp, census, absence = unpacked
    assert projections == slate.projections
    assert resolved == slate.resolved
    assert refusals == slate.name_refusals
    assert stamp == slate.priced_through == "2024-01-08"
    assert census == slate.resolution_census
    assert absence == "", "a populated player half names no absence"


def test_projection_for_raises_on_a_name_rather_than_inventing_an_athlete() -> None:
    """R1 and R1a have no athlete id, and a projection carrying one invented it.

    That is the join-vocabulary bug family in its purest form, and this lab has
    it written down five times. The single-subject entry point refuses and says
    where the refusal belongs instead.
    """
    with pytest.raises(PR.PlayerRatesError) as raised:
        PR.projection_for(
            day=DAY,
            event_id="e1",
            game_id=999,
            home_team_id=55,
            away_team_id=66,
            provider_name="Nobody At All",
            roster=_history(),
            shapes=_shapes(),
            priced_through="2024-01-08",
        )
    assert "player_projections_for" in str(raised.value)

    projection = PR.projection_for(
        day=DAY,
        event_id="e1",
        game_id=999,
        home_team_id=55,
        away_team_id=66,
        provider_name="S. Bairstow",
        roster=_history(),
        shapes=_shapes(),
        priced_through="2024-01-08",
    )
    assert projection.priceable is True
    assert projection.resolution_route == PR.ROUTE_INITIAL
    assert projection.priced_through == "2024-01-08"


# --------------------------------------------------------------------------
# The limitations, recorded as passing assertions
# --------------------------------------------------------------------------


def test_the_gaps_this_estimator_still_has_are_the_ones_written_down() -> None:
    """Six, each of which goes red the day it is closed.

    The repository's form for a limitation: not a docstring claim that quietly
    becomes false, but an assertion that fails on the commit which fixes it and
    forces somebody to say so.

    1. **No distribution engine.** `models/player_distributions.py` is not
       written, so a priceable projection is a mean and a lattice and never a
       probability. Nothing here can select a bet.
    2. **No cross-season carry-over.** The bank resets at every season
       boundary, because admitting one needs a decay constant nobody has
       fitted. With R2 that refuses every player for his first four
       appearances of every season, which is the largest single driver of the
       November refusal census.
    3. **No availability source.** `dnp_probability` is the bucket base rate,
       unshrunk, because the frozen file carries no credibility constant for
       it. There is no injury feed, no lineup feed and no rotation note in any
       table here.
    4. **No opponent, pace, venue or rest term.** Each is declined with a
       declared admission bar of 2% of held-out RMSE; the measured values are
       0.13-0.29% (the design's numbers, quoted).
    5. **No count-lattice ceiling.** R4 refuses a mean "above the lattice
       ceiling" and the frozen file declares `minutes_support` and no per-market
       count ceiling at all, so the upper half of R4 is enforced on minutes and
       not on counts. It belongs in `player_distributions.py`.
    6. **The card cannot form a rate.** `slate.REQUIRED_PLAYER_COLUMNS` is
       eight columns and a per-minute rate needs the box score, so every
       subject on the card path is refused under R6. It is one list away, and
       widening it changes a measured docstring in `card_matchups.py`.
    """
    models = REPO / "src" / "cbb_betting_lab" / "models"
    assert not (models / "player_distributions.py").exists(), (
        "the distribution engine now exists, so a projection can carry a "
        "probability. Delete this clause, and with it every sentence in this "
        "file that says no probability exists."
    )

    evidence = PR.trailing_evidence(
        pd.concat(
            [
                pd.DataFrame([_row(f"2023-01-{d:02d}", game_id=d, season=2023) for d in range(1, 9)]),
                pd.DataFrame([_row("2023-11-10", game_id=50)]),
            ],
            ignore_index=True,
        ),
        half_life=4.0,
    )
    assert int(evidence.loc[(float(PRICED_SEASON), 4001)]["prior_games"]) == 1

    document = json.loads(SHAPES.read_text(encoding="utf-8"))
    assert "dnp_shrinkage" not in document["constants"], (
        "a credibility constant for the did-not-play rate now exists, so it "
        "can be shrunk toward the bucket base rate rather than being it"
    )
    assert not any(
        "ceiling" in name for name in document["constants"]
    ), "a count-lattice ceiling now exists; R4's upper half can be enforced"
    assert set(document["declared"]) == {
        "bucket_edges",
        "bucket_labels",
        "refusal_thresholds",
        "minutes_support",
        "prior_season_min_games",
        "overtime_is_included",
    }, "the declared block grew or shrank; say which of these clauses changed"

    from cbb_betting_lab.models import slate as SLATE

    assert not set(PR.REQUIRED_STAT_COLUMNS) <= set(SLATE.REQUIRED_PLAYER_COLUMNS), (
        "the seam now declares the box-score columns, so the card path can "
        "form a rate and R6 no longer fires there. Delete clause 6, and "
        "re-measure the read cost `card_matchups.load_player_games` quotes."
    )
    for term in ("opponent", "pace", "venue", "rest"):
        assert term not in {
            parameter for parameter in inspect.signature(PR.projection_for).parameters
        }, f"a {term} term reached the estimator; the admission bar is 2% of RMSE"
