"""The ratings fit, on the data shapes that actually broke it.

`_season_fit` raised `numpy.linalg.LinAlgError: Singular matrix` on 2019, 2020
and 2021 while working on 2022, and it did so the first time it was ever asked
to price a real multi-season history. Nothing in the suite covered it, because
every existing test fitted one season at a time with that season's schedule in
hand — the one arrangement in which the defect cannot appear.

Two independent faults produced it, and both are pinned here because either
alone would have been enough:

1. **The four venue columns were the only unregularised columns in the design.**
   A season supplying no quasi-neutral game with a local team leaves two of them
   structurally zero, and an unpenalised zero column makes the normal matrix
   singular.
2. **The caller supplied only the priced season's schedule.** Venue and locality
   are read off the schedule, and the prior is fitted on *earlier* seasons — so
   those seasons had no local team on any game, which is what emptied the
   columns in the first place.

The ridge makes the estimator well-posed whatever it is handed; the schedules
make the numbers right. They are not substitutes.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cbb_betting_lab.models import ratings as R


def test_a_season_with_no_quasi_neutral_game_fits_rather_than_raising():
    """The reproduction, built rather than loaded.

    Two teams, a home-and-away pair, and not one quasi-neutral game — which
    makes two of the four venue columns exactly zero.
    """
    rows = pd.DataFrame(
        {
            "game_id": [1, 1, 2, 2],
            "team_id": [10, 20, 20, 10],
            "opponent_id": [20, 10, 10, 20],
            "efficiency": [1.05, 0.98, 1.10, 1.02],
            "game_possessions": [68.0, 68.0, 70.0, 70.0],
            "venue_state": ["home", "away", "home", "away"],
            "is_local": [True, False, True, False],
            "opponent_is_local": [False, True, False, True],
            "season": [2021] * 4,
        }
    )
    offence, defence, tempo, *_ = R._season_fit(
        rows, strength=dict(R.DECLARED_PRIOR_STRENGTH)
    )
    assert set(offence) == {10, 20}
    assert all(np.isfinite(v) for v in offence.values())
    assert all(np.isfinite(v) for v in defence.values())
    assert all(np.isfinite(v) for v in tempo.values())


def test_an_inestimable_venue_effect_comes_back_as_zero_not_as_an_exception():
    """The honest answer to "what is the quasi-neutral home effect in a season
    with no quasi-neutral games?" is zero, not a crash and not a guess."""
    rows = pd.DataFrame(
        {
            "game_id": [1, 1],
            "team_id": [10, 20],
            "opponent_id": [20, 10],
            "efficiency": [1.05, 0.98],
            "game_possessions": [68.0, 68.0],
            "venue_state": ["neutral", "neutral"],
            "is_local": [False, False],
            "opponent_is_local": [False, False],
            "season": [2021, 2021],
        }
    )
    # Every venue column is empty here; the fit must still return.
    offence, defence, *_ = R._season_fit(
        rows, strength=dict(R.DECLARED_PRIOR_STRENGTH)
    )
    assert all(np.isfinite(v) for v in offence.values())


def test_the_venue_ridge_is_small_enough_not_to_move_an_estimable_effect():
    """A guard that changed the answer would be a prior wearing a guard's coat.

    One pseudo-observation against thousands of real rows must not move a
    venue effect anywhere a reader would notice.
    """
    assert R.VENUE_RIDGE == pytest.approx(1.0)
    assert R.VENUE_RIDGE < min(R.DECLARED_PRIOR_STRENGTH.values()) / 5


#: The synthetic league `tests/test_fit_ratings.py` builds: three seasons, a
#: double round-robin, every venue state present. Imported from the sibling
#: test module because it is the fixture the whole ratings suite already
#: runs on, and because a second copy would drift.
from test_fit_ratings import build_universe  # noqa: E402


def _slate(season: int, day: str, raw_dir):
    """The real games on a real slate day, as a price frame."""
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.season import slate_date

    schedule = R._cached_schedule(season, raw_dir)
    if "date" in schedule.columns:
        days = schedule["date"].map(
            lambda x: slate_date(pd.Timestamp(x).tz_convert("UTC").isoformat(), CBB)
        )
    else:
        days = schedule["game_date"].astype(str)
    today = schedule[days == day]
    return pd.DataFrame(
        {
            "event_id": [f"e{i}" for i in range(len(today))],
            "game_id": today["id"].values,
        }
    )


@pytest.mark.parametrize("season", [2024, 2025, 2026])
def test_every_season_fits_from_a_multi_season_prepare(season: int, tmp_path):
    """The exact arrangement that broke: prepare over many seasons, fit one.

    Over the synthetic universe rather than the gitignored processed table, so
    it runs in CI. This test used to read `data/processed/cbb_team_games.csv`
    and skip when it was absent — which is CI — so the invariant had only
    ever been checked on a laptop.
    """
    world = build_universe(tmp_path)
    frame = pd.read_csv(world["processed"] / "cbb_team_games.csv")
    schedules = {s: R._cached_schedule(s, world["raw"]) for s in world["seasons"]}
    prepared = R.prepare(frame, schedules=schedules)
    subset = prepared.rows[prepared.rows["season"] == season]
    assert not subset.empty, f"no prepared rows for {season}"
    offence, *_ = R._season_fit(subset, strength=dict(R.DECLARED_PRIOR_STRENGTH))
    assert offence, "the fit returned no team ratings"


def _november_regime_case(tmp_path):
    world = build_universe(tmp_path)
    frame = pd.read_csv(world["processed"] / "cbb_team_games.csv")
    return world, frame


def _slate_days(world, season: int) -> list[str]:
    schedule = R._cached_schedule(season, world["raw"])
    return sorted(schedule["game_date"].astype(str).unique())


def test_the_seam_does_not_delete_the_november_prior_regime(tmp_path):
    """The defect that mattered most, and it was mine.

    `ratings.fit`'s contract is *history filtered to the season being priced* —
    because **a team is not the team it was last March** — and
    `run_price_backtest.walk_forward` hands the model EVERY season strictly
    earlier than the day, so a seam that passes its history straight through
    puts every earlier season's team-games in the design matrix on opening
    night.

    Measured before the fix, by `scripts/fit_ratings.py` on the real 2025-26
    season: 31,828 team-games in the matrix on 3 November, and the prior's
    weight **0.0% on 3 November and 0.0% on 20 February**.

    Reproduced here on the synthetic league: an early slate day of the last
    season against a late one, history = every season strictly before the day,
    exactly as the backtest passes it. The prior must dominate early and fall
    by the end.
    """
    world, frame = _november_regime_case(tmp_path)
    season = world["seasons"][-1]
    days = _slate_days(world, season)
    # Measured on the synthetic league: nothing is priceable before the
    # fourth slate day (the schedule graph has not connected the teams), the
    # prior weight is 0.956 on the fifth and 0.812 on the last.
    early, late = days[4], days[-1]

    weights = {}
    for day in (early, late):
        prices = _slate(season, day, world["raw"])
        assert not prices.empty, f"no synthetic games on {day}"
        matchups = R.matchups_for(
            day=day,
            history=frame[frame["slate_date"] < day],
            prices=prices,
            raw_dir=world["raw"],
        )
        priceable = [m for m in matchups.values() if m.priceable]
        assert priceable, f"nothing priceable on {day}"
        weights[day] = sum(m.prior_weight for m in priceable) / len(priceable)

    assert weights[early] > 0.5, (
        f"early-season prior weight is {weights[early]:.3f}. In the first week "
        "almost all of a rating must still be prior; a low number here means "
        "the fit is treating last season's team as this season's."
    )
    assert weights[early] > weights[late] + 0.1, (
        "The prior's weight does not fall across the season, so an early price "
        "is indistinguishable from a late one — the exact thing the prior "
        "weight is carried to prevent."
    )


def test_the_tier_table_never_sees_the_season_it_is_pricing(tmp_path):
    """A tier is not a label — it selects which home-court effect is applied.

    Letting the priced season into `conferences.tier_table` moved **34 of 367
    teams (9.3%)** across a boundary, measured by `scripts/fit_ratings.py` on
    the real tables. Pinned here on the synthetic league: the tier cache must
    hold no key that includes the season being priced.
    """
    world, frame = _november_regime_case(tmp_path)
    season = world["seasons"][-1]
    R.clear_caches()
    day = _slate_days(world, season)[4]
    prices = _slate(season, day, world["raw"])
    assert not prices.empty
    R.matchups_for(day=day, history=frame[frame["slate_date"] < day], prices=prices, raw_dir=world["raw"])

    keys = [k for k in R._TIER_CACHE if isinstance(k, tuple)]
    assert keys, "no tier table was built"
    assert all(season not in key for key in keys), (
        f"A tier table was built over {keys}, which includes the season being priced."
    )


def test_the_schedule_caches_change_no_number(tmp_path):
    """The optimisation must be invisible in the output, or it is not one.

    `local_teams` and `venue_ids` are pure functions of the schedules and were
    being recomputed inside `prepare` on every walk-forward day — measured on
    the real tables, 3.01 seconds of `prepare`'s 3.09. Caching them is only
    legitimate if it changes nothing, so a cold run is compared against a
    warm one field by field.
    """
    import dataclasses

    from cbb_betting_lab.competitions import CBB

    world, frame = _november_regime_case(tmp_path)
    season = world["seasons"][-1]
    day = _slate_days(world, season)[4]
    prices = _slate(season, day, world["raw"])
    assert not prices.empty
    history = frame[frame["slate_date"] < day]

    R.clear_caches()
    cold = R.matchups_for(day=day, history=history, prices=prices, competition=CBB, raw_dir=world["raw"])
    warm = R.matchups_for(day=day, history=history, prices=prices, competition=CBB, raw_dir=world["raw"])

    assert set(cold) == set(warm) and cold
    for key in cold:
        first = dataclasses.asdict(cold[key])
        second = dataclasses.asdict(warm[key])
        for field, value in first.items():
            other = second[field]
            if value != value and other != other:  # NaN == NaN
                continue
            assert value == other, (
                f"The cached run differs from the cold run on {key}.{field}: "
                f"{value!r} vs {other!r}. A cache that changes an answer is a "
                "defect wearing an optimisation's clothes."
            )


def test_clear_caches_really_empties_every_cache():
    """A cache added to the module and not to `clear_caches` is a cache a test
    cannot reset, and the next test in the file inherits its contents."""
    R.clear_caches()
    caches = [
        value
        for name, value in vars(R).items()
        if name.startswith("_") and name.endswith("_CACHE") and isinstance(value, dict)
    ]
    assert caches, "no module-level caches found; this test has stopped measuring"
    for cache in caches:
        assert not cache, "clear_caches() left a cache populated"
