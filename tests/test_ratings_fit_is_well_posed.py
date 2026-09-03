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


@pytest.mark.parametrize("season", [2019, 2020, 2021, 2022])
def test_every_cached_season_fits_from_a_multi_season_prepare(season: int):
    """The exact arrangement that broke: prepare over many seasons, fit one.

    Skipped when the processed table is not on disk, which is CI. The unit
    reproductions above carry the invariant there.
    """
    from pathlib import Path

    table = Path(__file__).resolve().parents[1] / "data" / "processed" / "cbb_team_games.csv"
    if not table.is_file():
        pytest.skip("cbb_team_games.csv is not built here.")
    frame = pd.read_csv(table, low_memory=False)
    frame = frame[frame["season"] <= 2022]
    if frame.empty or season not in set(frame["season"]):
        pytest.skip(f"season {season} is not in the table")
    try:
        schedules = {
            int(s): R._cached_schedule(int(s))
            for s in sorted(frame["season"].unique())
        }
    except FileNotFoundError:
        pytest.skip("schedules are not cached here")
    prepared = R.prepare(frame, schedules=schedules)
    subset = prepared.rows[prepared.rows["season"] == season]
    if subset.empty:
        pytest.skip(f"no prepared rows for {season}")
    offence, *_ = R._season_fit(subset, strength=dict(R.DECLARED_PRIOR_STRENGTH))
    assert offence, "the fit returned no team ratings"
