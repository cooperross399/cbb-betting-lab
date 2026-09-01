"""Ambiguity falls on the not-a-play side, always.

Every assertion here is a defect a sibling lab actually shipped: the EPL lab
carried a fixture that had already kicked off, and the football lab's first
availability gate would have read a missing injury file as a healthy slate.
"""

from __future__ import annotations

import re

from datetime import datetime, timedelta, timezone

import pytest

from cbb_betting_lab.gates import (
    AccountingIdentity,
    Availability,
    TipState,
    availability_note,
    can_be_played,
    can_produce_a_selection,
    tip_state,
)

NOW = datetime(2027, 1, 12, 18, 0, tzinfo=timezone.utc)


def _at(minutes: float) -> str:
    return (NOW + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def test_a_game_that_has_started_cannot_be_played():
    assert tip_state(_at(-1), now=NOW) is TipState.STARTED
    assert not can_be_played(TipState.STARTED)


def test_a_game_tipping_within_the_margin_cannot_be_played():
    assert tip_state(_at(5), now=NOW) is TipState.IMMINENT
    assert not can_be_played(TipState.IMMINENT)


def test_an_upcoming_game_can_be_played():
    assert tip_state(_at(180), now=NOW) is TipState.UPCOMING
    assert can_be_played(TipState.UPCOMING)


@pytest.mark.parametrize(
    "value", ["", None, "not a date", "2027-01-12", "2027-01-12T18:00:00", float("nan")]
)
def test_an_unconfirmable_tip_quarantines_rather_than_passing(value):
    """Including a naive timestamp: guessing a zone moves a game by hours."""
    assert tip_state(value, now=NOW) is TipState.UNCONFIRMED
    assert not can_be_played(TipState.UNCONFIRMED)


def test_the_guard_judges_each_game_by_its_own_tip():
    """This sport tips every fifteen minutes for twelve hours."""
    morning, evening = _at(-360), _at(300)
    assert tip_state(morning, now=NOW) is TipState.STARTED
    assert tip_state(evening, now=NOW) is TipState.UPCOMING


def test_nothing_reaches_confirmed_so_no_prop_can_be_selected():
    for state in Availability:
        if state is Availability.CONFIRMED:
            continue
        assert not can_produce_a_selection(state)
        assert "cannot produce a selection" in availability_note(state)


def test_no_report_and_undesignated_are_different_states_with_different_words():
    """Collapsing them is how a missing feed becomes a clean slate."""
    assert Availability.NO_REPORT is not Availability.UNDESIGNATED
    no_report = availability_note(Availability.NO_REPORT)
    undesignated = availability_note(Availability.UNDESIGNATED)
    assert no_report != undesignated
    assert "no availability report exists" in no_report
    assert "a report exists" in undesignated


def test_a_blocked_market_is_never_described_as_a_pass_or_an_avoid():
    """The words may appear only inside an explicit denial.

    The first version of this test banned the substrings outright and failed on
    the note that says *"This is not a pass, an avoid or a no-value call"* —
    which is the required phrasing, not a violation. The rule is about the
    **assertion**, so the check has to be about the assertion too: a note may
    deny being a pass and may never claim to be one.
    """
    for state in Availability:
        note = availability_note(state).casefold()
        if not note:
            continue
        assert "cannot produce a selection" in note
        # Drop every explicitly negated clause, then look for what is left.
        remainder = re.sub(
            r"(?:is not|it is not|never)\b[^.]*", "", note
        )
        for banned in (" pass", "avoid", "no value", "no-value", "lean"):
            assert banned not in remainder, (
                f"{state.value} asserts {banned!r} outside a denial. An "
                "excluded market is never a pass, an avoid, or a no-value call."
            )


def test_the_accounting_identity_reconciles_or_raises():
    good = AccountingIdentity(
        priced=100, no_opinion=40, below_threshold=20, unparseable=5,
        ambiguous=5, gated=30, bets=0,
    )
    assert good.reconciles()
    good.raise_if_unreconciled()

    bad = AccountingIdentity(priced=100, no_opinion=40, bets=0)
    assert not bad.reconciles()
    with pytest.raises(ValueError, match="does not reconcile"):
        bad.raise_if_unreconciled()
    assert "off by" in bad.summary_line()
