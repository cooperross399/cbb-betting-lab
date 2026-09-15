"""Shot-zone and tempo features from the play-by-play, per team-game.

**The coordinates in this feed are not usable and this module does not touch
them.** `coordinate_x`/`coordinate_y` are present on only 25.9% of shooting
plays in 2025, and the values that are present run to ±214,748,406 — which is
`INT32_MAX / 10`, a missing-value sentinel rather than a court. Filtering to a
plausible court leaves 27% of attempts, and a rate computed over a quarter of
the shots, selected by whichever feed happened to populate the field, is a
biased estimate wearing the clothes of a measured one.

`type_text` and `score_value` classify every attempt instead: 100% coverage on
the 713,965 field-goal attempts in 2025, and the splits land where college
basketball's do — rim 35.6% at .582, mid 25.1% at .409, three 39.3% at .338.

One documented difference from Hoop-Math, which is the usual publisher of this
split: ESPN's `JumpShot` label includes short jumpers and floaters that
Hoop-Math separates from mid-range, so mid FG% here (~.41) runs above the ~.35
those tables show. The zone boundary is a labelling convention, not a
measurement, and this one is stated rather than matched.

**The play-by-play is not the box score, and this module does not pretend it
is.** Reconciled against `team_box` for 2025 across 12,266 team-games: FGA
matches exactly in 86.6% and the mean pbp count runs 0.29 attempts LOW, 3PA
matches in 98.3%, and eFG% correlates at 0.998 with a mean absolute difference
of 0.0015. 3.2% of team-games differ by more than two attempts.

So the rule this module follows: **the box score owns every total it reports,
and the play-by-play is used only for what the box cannot say** — which zone an
attempt came from, whether it came in transition, how long a possession lasted.
Rates are returned rather than counts, because a rate is the quantity where the
feed's undercount largely cancels, and importing a 0.29-attempt shortfall into a
number the box already measures exactly would be a self-inflicted error.
`efg_pct` is computed here anyway and is NOT for use — it exists as a check on
this path against the box score, and the test suite compares them.

Everything here is a per-GAME observation. Turning these into a prediction for a
future game is the caller's job and must be walk-forward: see
`rolling_before()`, which is the only aggregator this module offers, and which
refuses to include the game it is asked about.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

#: Attempts the feed labels as finishes at the rim.
RIM_TYPES = ("LayUpShot", "DunkShot", "TipShot")

#: The seconds-into-possession cutoff Hoop-Math uses for "transition".
TRANSITION_SECONDS = 10

#: KenPom's free-throw weight. Oliver and Sports-Reference use 0.44; this lab
#: follows the possession formula already used in `cbb_team_games`.
FTA_WEIGHT = 0.475


def classify_zone(type_text: pd.Series, score_value: pd.Series) -> pd.Series:
    """rim / mid / three for every field-goal attempt.

    Three first: a `JumpShot` worth three is a three wherever it was taken, and
    a three is never a rim attempt, so the order removes the ambiguity rather
    than leaving it to the label.
    """
    label = type_text.astype("string").fillna("")
    zone = pd.Series(pd.NA, index=label.index, dtype="string")
    zone[label.isin(RIM_TYPES)] = "rim"
    zone[label.eq("JumpShot")] = "mid"
    zone[score_value.eq(3)] = "three"
    return zone


def field_goal_attempts(pbp: pd.DataFrame) -> pd.DataFrame:
    """Every field-goal attempt, zoned. Free throws are not attempts."""
    shots = pbp[
        pbp["shooting_play"].fillna(False).astype(bool)
        & pbp["score_value"].isin([2, 3])
    ].copy()
    shots["zone"] = classify_zone(shots["type_text"], shots["score_value"])
    shots["made"] = shots["scoring_play"].fillna(False).astype(bool)
    unzoned = shots["zone"].isna().mean()
    if unzoned > 0.01:
        raise ValueError(
            f"{unzoned:.1%} of field-goal attempts carry a shot type this "
            "module does not classify. RIM_TYPES or the feed's vocabulary "
            "moved; a silent 'other' bucket would bias every rate below."
        )
    return shots


def team_game_zones(pbp: pd.DataFrame) -> pd.DataFrame:
    """Per team-game: where a team shot, how it finished, and what it allowed.

    Both sides come from one pass. The defensive row is not a separate
    measurement — it is the opponent's offensive row attributed to the other
    team — so `rim_fg_pct_allowed` and `rim_rate_allowed` cannot drift out of
    step with the offensive numbers they are derived from.
    """
    shots = field_goal_attempts(pbp)
    if shots["team_id"].isna().any():
        raise ValueError("a field-goal attempt carries no team_id; it cannot be attributed")

    grouped = (
        shots.groupby(["game_id", "team_id", "zone"], observed=True)
        .agg(attempts=("made", "size"), makes=("made", "sum"))
        .reset_index()
    )
    wide = grouped.pivot_table(
        index=["game_id", "team_id"], columns="zone",
        values=["attempts", "makes"], fill_value=0,
    )
    wide.columns = [f"{a}_{z}" for a, z in wide.columns]
    wide = wide.reset_index()

    for zone in ("rim", "mid", "three"):
        for stem in ("attempts", "makes"):
            column = f"{stem}_{zone}"
            if column not in wide:
                wide[column] = 0

    wide["fga"] = wide[[f"attempts_{z}" for z in ("rim", "mid", "three")]].sum(axis=1)
    for zone in ("rim", "mid", "three"):
        wide[f"{zone}_rate"] = wide[f"attempts_{zone}"] / wide["fga"].replace(0, np.nan)
        wide[f"{zone}_fg_pct"] = (
            wide[f"makes_{zone}"] / wide[f"attempts_{zone}"].replace(0, np.nan)
        )
    # eFG% from the zones, which is the same quantity the box score reports and
    # so is a check on this whole path rather than a new number.
    wide["efg_pct"] = (
        wide[[f"makes_{z}" for z in ("rim", "mid", "three")]].sum(axis=1)
        + 0.5 * wide["makes_three"]
    ) / wide["fga"].replace(0, np.nan)

    # The opponent's row in the same game, joined back as "allowed".
    pairs = wide[["game_id", "team_id"]].merge(
        wide[["game_id", "team_id"]], on="game_id", suffixes=("", "_opp")
    )
    pairs = pairs[pairs["team_id"] != pairs["team_id_opp"]]
    allowed = wide.add_suffix("_allowed").rename(
        columns={"game_id_allowed": "game_id", "team_id_allowed": "team_id_opp"}
    )
    out = pairs.merge(wide, on=["game_id", "team_id"]).merge(
        allowed, on=["game_id", "team_id_opp"]
    )
    return out.drop(columns=["team_id_opp"])


def rolling_before(
    frame: pd.DataFrame, columns, *, by="team_id", order="slate_date", minimum=1
) -> pd.DataFrame:
    """A team's mean of `columns` over its games STRICTLY BEFORE each game.

    **The only aggregator in this module, because it is the only one that is
    safe.** A season mean used to predict a game inside that season has seen the
    game it is predicting; this lab fits walk-forward and a leaked feature is
    indistinguishable from a good one until it is bet. `shift(1)` before the
    expanding mean is what makes the exclusion, and the test suite mutates it
    away to prove that it is load-bearing.

    `minimum` games of history are required; a team's first game yields NaN
    rather than a number computed from itself.
    """
    frame = frame.sort_values([by, order]).copy()
    grouped = frame.groupby(by, observed=True)[list(columns)]
    prior = grouped.apply(lambda g: g.shift(1).expanding(minimum).mean())
    prior = prior.reset_index(level=0, drop=True) if prior.index.nlevels > 1 else prior
    return prior.add_prefix("prior_")


def possessions(pbp: pd.DataFrame) -> pd.DataFrame:
    """Segment the play-by-play into possessions, using the lab's own rule.

    **The segmentation is `build_datasets.possession_ends`, not a second copy of
    it.** This module first grew its own — ordered by the game clock rather than
    play number, with its own turnover vocabulary and free-throw handling — and
    it was materially worse: correlation 0.649 against the box-score possession
    estimate, where the existing rule gets 0.944 with a 1.9% gap. The rule had
    already been written, validated and paid for; writing a second one produced
    a worse number that would have propagated into every feature below it.

    `possession_validation()` reports the agreement each season, and it is a
    genuine cross-check rather than a formality: the estimate comes from the box
    line (`FGA − OREB + TO + 0.475 × FTA`) and the count comes from the event
    stream, so they share no arithmetic.
    """
    from cbb_betting_lab.data.build_datasets import possession_ends

    frame = pbp.sort_values(
        ["game_id", "game_play_number"], kind="mergesort"
    ).reset_index(drop=True)
    frame["ends"] = possession_ends(frame)
    # The possession a row belongs to is the number of ends strictly before it.
    #
    # **Both operations are grouped.** `groupby(...).cumsum().shift(1)` shifts
    # the UNGROUPED result, so the first row of each game inherits the last
    # possession index of the previous one: 148.1 possessions per game against
    # the 140.7 the rule actually counts, silently, in every feature built on
    # top of it.
    grouped = frame.groupby("game_id", observed=True)["ends"]
    frame["possession"] = grouped.cumsum().sub(frame["ends"].astype(int))
    return frame
