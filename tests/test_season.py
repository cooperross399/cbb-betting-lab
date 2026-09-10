"""The rule regimes inside this lab's window, and the seasons they separate.

A season is not just a label here: the three-point arc moved for 2019-20, so
2019 and 2020 are different games and pooling them models one as the other.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from conftest import processed_table  # noqa: E402


def test_the_arc_change_is_declared_where_a_pooling_decision_can_see_it():
    """2019 is a different game, and the boundary is measured not asserted."""
    from cbb_betting_lab import season as S

    assert S.THREE_POINT_ARC_MOVED_IN == 2020
    assert 2019 not in S.ARC_CONSISTENT_SEASONS
    assert S.crosses_the_arc_change([2019, 2020]) is True
    assert S.crosses_the_arc_change([2021, 2026]) is False
    assert S.crosses_the_arc_change(S.ARC_CONSISTENT_SEASONS) is False
    # A single season on either side crosses nothing.
    assert S.crosses_the_arc_change([2019]) is False


def test_the_declared_boundary_is_the_one_the_data_shows():
    """The step in 3P% is at the declared season, on whichever corpus is here.

    **The tracked sample holds one season (2026), so it cannot span the arc
    boundary.** That is stated rather than worked around: on the sample this
    verifies the constants and records that the data check did not run, and on
    a built `data/processed` it measures the step. Writing it to require the
    full table would make it a test that passes on the author's laptop and
    fails in CI, which this repository did once today already.
    """
    import pandas as pd
    from cbb_betting_lab import season as S

    path, corpus = processed_table("cbb_team_games.csv")
    frame = pd.read_csv(
        path,
        usecols=[
            "season",
            "game_state",
            "three_point_field_goals_made",
            "three_point_field_goals_attempted",
        ],
    )
    frame = frame[frame["game_state"] == "countable"]
    seasons = sorted(frame["season"].unique())
    spans = min(seasons) < S.THREE_POINT_ARC_MOVED_IN <= max(seasons)
    assert S.crosses_the_arc_change(seasons) == spans

    if not spans:
        # The honest branch. It asserts the reason, so a corpus that QUIETLY
        # stopped spanning the boundary cannot look like a passing check.
        assert corpus == "sample", (
            f"the {corpus} corpus holds seasons {seasons} and does not span the "
            f"declared arc change at {S.THREE_POINT_ARC_MOVED_IN}. A full table "
            "that stops spanning it means the boundary or the build moved."
        )
        return

    rate = frame.groupby("season").apply(
        lambda d: d["three_point_field_goals_made"].sum()
        / max(1, d["three_point_field_goals_attempted"].sum()),
        include_groups=False,
    )
    before = rate.loc[rate.index < S.THREE_POINT_ARC_MOVED_IN].mean()
    after = rate.loc[rate.index >= S.THREE_POINT_ARC_MOVED_IN].mean()
    assert before - after > 0.004, (
        f"3P% is {before:.4f} before the declared arc change and {after:.4f} "
        "after, a step too small to be the rule change. Either the boundary is "
        "in the wrong season or the table changed."
    )
