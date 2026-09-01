"""A made free throw is not a basket, and the obvious filter does not know that.

Reproduced before it was fixed. The feed's play type is `MadeFreeThrow` —
**one word, no space** — so the natural screen, `str.contains("Free Throw")`,
matches **none** of the 253,589 free-throw rows in a single season. Every one
of them then counts as a made field goal.

Two things break when it does, and only one of them is visible:

* the possession count inflates by about 15 a game, which shows up as an
  obviously wrong number in a validation report;
* **`player_first_basket` settles on whoever made the game's first free
  throw**, which shows up as nothing at all. It is a plausible name, a real
  player, and a wrong bet.

The second is why this test exists.
"""

from __future__ import annotations

import pandas as pd
import pytest

from cbb_betting_lab.data.build_datasets import (
    FREE_THROW_TYPE_KEYS,
    KNOWN_FIELD_GOAL_TYPES,
    _type_key,
    is_free_throw,
    is_made_field_goal,
)


def _plays():
    """A game that opens with two free throws before anyone makes a field goal."""
    return pd.DataFrame(
        [
            # play 1: a made free throw. Scoring, worth 1, NOT a basket.
            {"type_text": "MadeFreeThrow", "scoring_play": True, "score_value": 1},
            # play 2: a MISSED jump shot. score_value is 2 anyway — the trap.
            {"type_text": "JumpShot", "scoring_play": False, "score_value": 2},
            # play 3: the actual first basket.
            {"type_text": "LayUpShot", "scoring_play": True, "score_value": 2},
        ]
    )


def test_the_naive_space_separated_filter_matches_nothing():
    """Reproduce the defect, so the fix is known to be load-bearing."""
    types = _plays()["type_text"]
    assert not types.str.contains("Free Throw", case=False).any(), (
        "If this ever matches, ESPN has changed its vocabulary and the "
        "reproduction is stale — but the fix must still be the key-based one."
    )
    assert is_free_throw(types).any(), "The key-based filter must match it."


def test_a_made_free_throw_is_not_a_made_field_goal():
    plays = _plays()
    made = is_made_field_goal(plays)
    assert not bool(made.iloc[0]), "A made free throw is not a basket."
    assert not bool(made.iloc[1]), (
        "A missed shot carries a positive score_value; 478,588 rows in one "
        "season do. score_value alone is not enough."
    )
    assert bool(made.iloc[2])


def test_the_first_basket_is_the_layup_and_not_the_free_throw():
    plays = _plays()
    first = plays[is_made_field_goal(plays)].iloc[0]
    assert first["type_text"] == "LayUpShot"


@pytest.mark.parametrize(
    "spelling", ["MadeFreeThrow", "Made Free Throw", "made free throw", "MADEFREETHROW"]
)
def test_spacing_and_case_cannot_hide_a_free_throw(spelling: str):
    assert _type_key(spelling) in FREE_THROW_TYPE_KEYS


def test_the_filter_is_negative_so_a_new_shot_type_stays_a_basket():
    """A shot type ESPN has not used before must still settle as a basket.

    An allowlist would be safer for possessions and wrong for first basket: an
    unrecognised shot type would be skipped and the first basket attributed to
    a later one. The filter is negative on purpose.
    """
    novel = pd.DataFrame(
        [{"type_text": "AlleyOopShot", "scoring_play": True, "score_value": 2}]
    )
    assert _type_key("AlleyOopShot") not in KNOWN_FIELD_GOAL_TYPES
    assert bool(is_made_field_goal(novel).iloc[0])
