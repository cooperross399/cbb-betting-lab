"""Sequential ratings, checked by symmetry.

Every one of these has a value it MUST take across a whole league, because every
game has a winner and a loser and every schedule is somebody else's schedule:
mean Pythagorean expectation is 0.5, mean Luck is 0, mean Strength of Schedule
is 0, and SRS is re-centred to mean 0 by construction.

**All four broke at once on the first build, from one population error**, which
is why they are all here: the frame carries non-D1 opponents that appear only
through their games against D1 sides. Their record in it is an artefact of which
games were collected. With them in, Pythagorean averaged 0.320, Luck -0.034, SOS
+16.9 and SRS spread 26.1. A single check would have looked like one odd number;
four failing together named the cause.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab.models import derived_ratings as DR

_ROOT = Path(DR.__file__).resolve().parents[3]
_GAMES = _ROOT / "data" / "processed" / "cbb_team_games.csv"
_CUT = "2025-02-01"


@pytest.fixture(scope="module")
def season():
    if not _GAMES.is_file():
        pytest.skip("the team-game table is not built in this checkout")
    games = pd.read_csv(_GAMES)
    frame = games[games["season"] == 2025]
    if frame.empty:
        pytest.skip("no 2025 rows in the team-game table")
    return frame


def test_only_division_one_teams_are_rated(season):
    rated = DR.pythagorean(season, 2025, _CUT)
    assert 330 < len(rated) < 380, (
        f"{len(rated)} teams rated. Division I is about 364; a number near 700 "
        "means non-D1 opponents are in the population, and every rating below is "
        "computed over a league that does not exist."
    )


def test_the_league_wide_identities_hold(season):
    """Each of these is forced by symmetry, not by taste."""
    expectation = DR.pythagorean(season, 2025, _CUT)
    assert expectation.mean() == pytest.approx(0.5, abs=0.02), (
        f"mean Pythagorean expectation {expectation.mean():.4f}; every game has "
        "a winner and a loser, so across the league it must be one half."
    )

    fortune = DR.luck(season, 2025, _CUT)
    assert fortune.mean() == pytest.approx(0.0, abs=0.02), (
        f"mean Luck {fortune.mean():+.4f}; it is a residual and must centre on zero."
    )

    srs = DR.simple_rating_system(season, 2025, _CUT)
    assert srs.mean() == pytest.approx(0.0, abs=1e-6), "SRS is not re-centred"
    assert 6.0 < srs.std() < 16.0, (
        f"SRS spread {srs.std():.2f} points. College basketball produces about "
        "ten; far outside that is a population or a convergence problem."
    )

    sos = DR.strength_of_schedule(season, 2025, _CUT, srs)
    assert sos.mean() == pytest.approx(0.0, abs=0.5), (
        f"mean Strength of Schedule {sos.mean():+.3f}; every team's schedule is "
        "made of other teams, so the average of it is the average team."
    )


def test_dropping_the_countable_filter_breaks_them(season):
    """The mutation, run rather than described.

    Without this the filter reads like defensive tidiness and the next person
    removes it. It is the difference between rating a league and rating a
    collection artefact.
    """
    unfiltered = season.assign(game_state=DR.COUNTABLE)  # pretend everything counts
    loose = DR.pythagorean(unfiltered, 2025, _CUT)
    tight = DR.pythagorean(season, 2025, _CUT)
    assert len(loose) > len(tight) * 1.5, (
        "including non-D1 opponents no longer changes the rated population, so "
        "this fixture has stopped testing the filter."
    )
    assert abs(loose.mean() - 0.5) > abs(tight.mean() - 0.5), (
        "the unfiltered population no longer breaks the symmetry identity, so "
        "the filter is not doing what its docstring says."
    )


def test_a_table_with_no_game_state_is_refused(season):
    """Silently rating everything is worse than failing."""
    with pytest.raises(ValueError, match="game_state"):
        DR.pythagorean(season.drop(columns=["game_state"]), 2025, _CUT)


def test_elo_is_a_prediction_time_quantity(season):
    """`elo_before` must be built only from earlier games.

    Elo is sequential by construction, so this checks the construction held: a
    team's first rating is the start value, and no rating anticipates a result.
    """
    elo = DR.elo_series(season)
    first = elo.sort_values(["slate_date", "game_id"]).groupby("team_id").head(1)
    assert (first["elo_before"] == DR.ELO_START).all(), (
        "a team's first game carries an Elo that is not the starting value, so "
        "something before its first game moved it."
    )
    assert elo["elo_before"].mean() == pytest.approx(DR.ELO_START, abs=25), (
        "Elo has drifted away from its start value across the league; the update "
        "is meant to be zero-sum."
    )
