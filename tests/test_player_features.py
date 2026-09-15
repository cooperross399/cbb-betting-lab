"""Player rates, checked by the identities they must satisfy.

A rate that computes is not a rate that is right. These are checked the only way
box-score rates can be: the players on a team must account for exactly the
team's whole game. Five players are on the floor at all times, so minutes shares
sum to five; every possession is ended by somebody, so usage weighted by minutes
share sums to one; every rebound is grabbed by somebody, so rebound rates do the
same. A formula that is off by a constant, or that divides by the wrong
denominator, breaks these and nothing else would have shown it.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab.models import player_features as PF

_ROOT = Path(PF.__file__).resolve().parents[3]
_BOX = _ROOT / "data" / "raw" / "cbb" / "player_box" / "player_box_2025.parquet"


def test_minutes_parse_from_both_forms_the_feed_uses():
    """`"34:12"` and `34` both appear; coercing blindly drops the starters."""
    parsed = PF.parse_minutes(pd.Series(["34:12", "28", None, "0:30"], dtype="string"))
    assert parsed.iloc[0] == pytest.approx(34.2, abs=1e-6)
    assert parsed.iloc[1] == pytest.approx(28.0)
    assert pd.isna(parsed.iloc[2])
    assert parsed.iloc[3] == pytest.approx(0.5, abs=1e-6)


def test_a_naive_numeric_coercion_would_have_lost_the_minutes():
    """The mistake this parser exists to avoid, shown failing.

    Without this the parser looks like an unnecessary wrapper around
    `to_numeric`, and the next person simplifies it.
    """
    naive = pd.to_numeric(pd.Series(["34:12", "28"], dtype="string"), errors="coerce")
    assert pd.isna(naive.iloc[0]), "the feed's MM:SS form no longer breaks to_numeric"
    assert PF.parse_minutes(pd.Series(["34:12"], dtype="string")).notna().all()


@pytest.fixture(scope="module")
def features():
    if not _BOX.is_file():
        pytest.skip("the 2025 player box is not present in this checkout")
    return PF.player_game_features(pd.read_parquet(_BOX))


def test_five_players_are_on_the_floor_at_all_times(features):
    """Minutes shares must sum to exactly five per team-game."""
    total = features.groupby(["game_id", "team_id"], observed=True)["minutes_share"].sum()
    assert total.mean() == pytest.approx(5.0, abs=0.01)
    assert (total.sub(5.0).abs() < 0.1).mean() > 0.99, (
        "a team's minutes shares do not sum to five, so the denominator every "
        "rate below divides by is wrong."
    )


def test_every_possession_is_ended_by_somebody(features):
    """Usage weighted by minutes share sums to one: the team's own possessions.

    This is what catches a usage formula with the wrong denominator — the most
    common way to get usage subtly wrong, and invisible in the mean.
    """
    frame = features.assign(weighted=features["usage_rate"] * features["minutes_share"])
    total = frame.groupby(["game_id", "team_id"], observed=True)["weighted"].sum()
    assert total.mean() == pytest.approx(1.0, abs=0.01)
    assert (total.sub(1.0).abs() < 0.05).mean() > 0.99


def test_every_rebound_is_grabbed_by_somebody(features):
    for column in ("off_reb_rate", "def_reb_rate"):
        frame = features.assign(w=features[column] * features["minutes_share"])
        total = frame.groupby(["game_id", "team_id"], observed=True)["w"].sum()
        assert total.mean() == pytest.approx(1.0, abs=0.02), (
            f"{column} weighted by minutes share sums to {total.mean():.3f} per "
            "team-game, not one. The rate is not a share of what was available."
        )


def test_the_rates_land_where_college_basketball_does(features):
    for column, low, high in [
        ("usage_rate", 0.15, 0.25), ("true_shooting_pct", 0.47, 0.58),
        ("turnover_rate", 0.12, 0.22), ("game_score", 3.0, 8.0),
        ("minutes", 15.0, 25.0),
    ]:
        mean = features[column].mean()
        assert low < mean < high, (
            f"{column} averages {mean:.4f}, outside the {low}-{high} this sport "
            "produces. The formula runs; that does not make it right."
        )
