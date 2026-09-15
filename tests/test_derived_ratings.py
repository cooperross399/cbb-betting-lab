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
_CUT = "2025-12-31"


@pytest.fixture(scope="module")
def season():
    """A synthetic round-robin league, because a skip is not a test.

    The archive is gitignored, so reading it here skipped on every clean
    checkout -- and this repository refuses a skip: "a gate that passes when it
    should fail". A round robin has the symmetry these ratings must respect, so
    the identities below are forced by construction rather than by the data
    happening to cooperate.
    """
    rows, game = [], 0
    scores = {t: 60 + 4 * t for t in range(12)}
    for home in range(12):
        for away in range(12):
            if home == away:
                continue
            game += 1
            for team, other, at_home in ((home, away, True), (away, home, False)):
                margin = scores[team] - scores[other] + (3 if at_home else -3)
                rows.append({
                    "game_id": game, "season": 2025,
                    "slate_date": f"2025-01-{1 + game % 28:02d}",
                    "team_id": team, "opponent_id": other,
                    "team_score": scores[team], "opponent_score": scores[other],
                    "margin": margin, "game_state": DR.COUNTABLE,
                    "home_away": "home" if at_home else "away", "neutral_site": False,
                })
    # Plus the thing the real archive is full of: non-D1 opponents that appear
    # ONLY through their games against the league, and lose them. Their record
    # here is an artefact of which games were collected. Without these in the
    # fixture, the filter test below has nothing to filter and passes vacuously.
    for guest in range(100, 112):
        game += 1
        rows.append({
            "game_id": game, "season": 2025, "slate_date": "2025-01-15",
            "team_id": guest, "opponent_id": 0, "team_score": 50,
            "opponent_score": 90, "margin": -40, "game_state": "non_di_opponent",
            "home_away": "away", "neutral_site": False,
        })
        rows.append({
            "game_id": game, "season": 2025, "slate_date": "2025-01-15",
            "team_id": 0, "opponent_id": guest, "team_score": 90,
            "opponent_score": 50, "margin": 40, "game_state": "non_di_opponent",
            "home_away": "home", "neutral_site": False,
        })
    return pd.DataFrame(rows)


def test_only_countable_teams_are_rated(season):
    rated = DR.pythagorean(season, 2025, _CUT)
    assert len(rated) == 12, (
        f"{len(rated)} teams rated from a twelve-team league. On the real archive "
        "this was 700 against a Division I of 364, because non-D1 opponents that "
        "appear only through their games AGAINST D1 sides were in the population."
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
    assert 0.0 < srs.std() < 60.0, (
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
    assert len(loose) > len(tight), (
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
