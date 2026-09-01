"""A replicated loss is not good news, and the headline must not say it is.

The NHL lab's `what_we_can_claim` announced *"at least one result survived the
correction and then replicated"* on a market returning **-6.6%**. Its headline
predicate tested measured + survives-correction + replicated and never read the
sign. The one document whose job is to stop a number being misread must not be
the thing misreading it.

This is a day-one regression test in this repository because it was a day-one
defect in two of the three siblings.
"""

from __future__ import annotations

import pytest

from cbb_betting_lab.stats import (
    DEMONSTRATED_DEFICIT,
    DEMONSTRATED_EDGE,
    MINIMUM_BETS,
    NO_DEMONSTRATED_EDGE,
    RoiInterval,
)


def _interval(roi: float, half_width: float, bets: int = 50_000) -> RoiInterval:
    return RoiInterval(
        roi=roi,
        low=roi - half_width,
        high=roi + half_width,
        bets=bets,
        clusters=bets // 4,
        standard_error=half_width / 1.959963984540054,
    )


def test_a_significant_loss_is_a_deficit_and_never_an_edge():
    result = _interval(-0.066, 0.02)
    assert result.survives_correction
    assert result.verdict() == DEMONSTRATED_DEFICIT
    assert result.verdict() != DEMONSTRATED_EDGE


def test_a_significant_gain_is_an_edge():
    assert _interval(+0.066, 0.02).verdict() == DEMONSTRATED_EDGE


def test_an_interval_including_zero_says_no_demonstrated_edge_in_those_words():
    assert _interval(+0.05, 0.09).verdict() == NO_DEMONSTRATED_EDGE
    assert _interval(-0.05, 0.09).verdict() == NO_DEMONSTRATED_EDGE


@pytest.mark.parametrize("roi", [-0.30, -0.01, 0.0, 0.01, 0.30])
def test_below_the_declared_floor_the_verdict_is_never_a_number(roi: float):
    """A market under the pre-declared sample floor gets a phrase, not a figure."""
    thin = _interval(roi, 0.01, bets=MINIMUM_BETS - 1)
    assert "not enough evidence" in thin.verdict()
    assert thin.verdict() not in {DEMONSTRATED_EDGE, DEMONSTRATED_DEFICIT}
    assert not thin.survives_correction


def test_the_family_correction_can_turn_an_edge_into_no_demonstrated_edge():
    """Testing many markets must widen the interval, not be optional."""
    one_look = RoiInterval(
        roi=0.05, low=0.01, high=0.09, bets=50_000, clusters=12_000,
        standard_error=0.0204, looks=1,
    )
    many_looks = RoiInterval(
        roi=0.05, low=0.01, high=0.09, bets=50_000, clusters=12_000,
        standard_error=0.0204, looks=40,
    )
    assert one_look.verdict() == DEMONSTRATED_EDGE
    assert many_looks.verdict() == NO_DEMONSTRATED_EDGE
    assert many_looks.adjusted_low < one_look.adjusted_low
