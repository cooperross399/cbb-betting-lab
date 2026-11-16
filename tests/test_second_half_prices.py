"""A second half is priced, and it can end level (decision 105).

Until 2026-11-16 `distributions.build` defaulted a second half to
`resolves_ties=True`, appended overtime to the regulation-level mass, and then
refused its own joint because the half still held level mass: a second half
settled including overtime is level whenever regulation was NOT (home +5 at
the break, a 30-30 second half). Every second-half wager on every card carried
no opinion. These pin the corrected contract.
"""

from __future__ import annotations

import pytest

from cbb_betting_lab.models import distributions as d

CASE = dict(home_points_per_possession=1.05, away_points_per_possession=1.00, possessions=68.0)


def test_a_second_half_builds_by_default():
    half = d.build(segment=d.SECOND_HALF, **CASE)
    assert half.segment == d.SECOND_HALF
    assert half.resolves_ties is False


def test_a_second_half_can_push_and_its_three_outcomes_sum_to_one():
    half = d.build(segment=d.SECOND_HALF, **CASE)
    tie = half.tie_probability()
    # A smooth half margin puts a few percent on zero, like the first half's
    # measured 3.76%; it is neither zero nor a full game's overtime rate.
    assert 0.02 < tie < 0.08
    total = half.moneyline(d.HOME) + half.moneyline(d.AWAY) + tie
    assert total == pytest.approx(1.0, abs=1e-9)


def test_overtime_is_still_played_onto_the_second_half():
    with_overtime = d.build(segment=d.SECOND_HALF, **CASE)
    without = d.build(segment=d.SECOND_HALF, resolves_ties=False, **CASE)
    # Overtime adds points in the ~6% of games that reach it, so the half's
    # expected total is higher when it is played out, and by less than a point
    # and a half (6% of about twenty points).
    gained = with_overtime.expected_total - without.expected_total
    assert 0.3 < gained < 1.5


def test_a_full_game_still_cannot_end_level():
    game = d.build(segment=d.FULL_GAME, **CASE)
    assert game.resolves_ties is True
    assert game.tie_probability() < 1e-9
