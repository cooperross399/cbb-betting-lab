"""Where a team's shots come from, and where its opponents get theirs.

The football analogue this is built from is a directional run chart: EPA per
rush by gap, offence laid over defence, so a reader sees at a glance that one
team runs left and the other is soft there. Basketball's channels are not
gaps, they are **places on the floor**, and the panel is the same shape --
volume, efficiency, and a Division-I rank per channel, offence against
defence.

## This is a description and it is never a claim

The ledger's `descriptive_only` category (decision 44) exists for exactly this:
it costs no hypothesis, widens nobody's interval, and **may never be promoted
to a finding**. Nothing in this module compares anything to a price, computes
an advantage, or prints one of the reserved verdict phrases. A zone gap between
two teams is a fact about how they have played; whether it is worth anything is
a question this module does not ask and cannot answer.

## The coverage refusal, which is most of the point

ESPN publishes shot coordinates for **whole games or not at all**, and the
choice of which games is its own production decision. Measured over the eight
seasons this lab holds:

    season   games   charted   share
      2019   5,474       841   15.4%
      2020   5,394       629   11.7%
      2021   4,015       579   14.4%
      2022   5,830       699   12.0%
      2023   6,116       536    8.8%
      2024   6,151       384    6.2%
      2025   6,136     1,661   27.1%
      2026   6,275     6,275  100.0%

Within a charted game the median share of shots carrying coordinates is 100%,
and within an uncharted game it is zero. So the seven seasons before 2026 are
not a thin sample of shots -- they are a **selected sample of games**, selected
by a rule this lab did not write, cannot see and cannot correct for. Those
games are broadcast games. Building a zone profile on them would describe the
televised half of Division I and print it as though it described the sport.

:func:`assert_fully_charted` refuses a season below
:data:`REQUIRED_CHARTED_SHARE` and names the measured share in the refusal.
There is no flag to override it. A partially-charted season is not a smaller
version of a complete one.

## The one season this can describe, and what that costs

2025-26 is the only season the feed charted, and it is not a free one. It sits
outside `replication.DECLARED_DISCOVERY_SEASONS` (2021-2023) and outside
`DECLARED_HELD_OUT_SEASONS` (2024), but the replication run reached it anyway
and said so in its own record, and `models/ratings.py` measured its prior
spreads on it. So there is no clean window left to validate a zone signal
against: discovery here would be 2025-26 and the holdout would be nothing.

That is the whole reason this module is descriptive. A panel is a description
and needs no holdout; a signal is a claim and has none available. The first
clean window is the season opening in November -- **2027, collected forward in
real time**, which is the only kind of holdout that cannot be chosen after the
numbers are seen. `forward_evidence.py` is the organ that would carry it, and
a hypothesis registered before that season starts is the only route from this
panel to anything that could be bet.

## The zones are measured, not borrowed

The conventional zone set (restricted area / paint / mid-range / corner three /
above the break) is an NBA inheritance. Measured on 2025-26 -- 738,247 field
goal attempts, points per attempt by two-foot band:

    0-2 ft   1.396      10-12   0.749      20-22   0.850  (mixed)
    2-4      1.245      12-14   0.756      22-24   1.060
    4-6      1.001      14-16   0.748      24-26   1.016
    6-8      0.800      16-18   0.746      26-28   0.976
    8-10     0.764      18-20   0.738      28-30   0.917

Two things in that table set the boundaries here. The rim falls off a cliff at
four feet (1.25 to 1.00) and again at six (1.00 to 0.80). And **the entire
mid-range is flat**: from six feet to the arc every band sits between 0.738 and
0.800, with no ordering worth the name. A panel that split "short mid" from
"long mid" would be drawing a line the sport does not draw, so this one does
not. The gradient that does exist beyond the arc -- 1.060 falling to 0.917 as
the shot gets deeper -- earns its split, and the corners earn theirs: beyond
`|y| >= 21` feet the median attempt sits **9.2 ft from the baseline** against
**26.2 ft** for a three inside that line, and points per attempt rise from
**0.990 to 1.062**. An earlier draft of this paragraph said 6 ft against 13,
which reproduces on no measure -- from the hoop's own x-line the same pair is
4.0 and 21.0 -- and it survived because nothing recomputed it.

## The frame, and the two traps in it

ESPN's coordinates are already normalised to attacking direction: the home team
attacks +x in both halves and the away team attacks -x, and in **0 of 6,275**
games in 2025-26 does a team's dominant side flip between halves. So no
per-half correction is applied, and the away team is mapped into the home
team's frame by a 180-degree rotation `(x, y) -> (-x, -y)`, which is a rotation
rather than a reflection and therefore leaves left and right where they were.

`team_id` arrives as float64 against int32 `home_team_id` -- a string
comparison of the two reports a 100% mismatch on a join that is in fact
perfect. :func:`attacking_frame` casts before it compares, and
:func:`assert_every_shot_is_attributed` refuses a frame where any shot belongs
to neither side.

## What the geometry is checked against

The coordinates are not trusted because they look reasonable. They are checked
against a label they do not contain: the feed tags every attempt, made **and
missed**, with a `score_value` of 2 or 3, and the distance implied by the
coordinates must agree. Measured on 2025-26 the two agree on **98.77%** of
738,247 attempts, and the hoop the geometry implies sits 5.25 feet from the
baseline, which is where a hoop goes. :func:`geometry_agreement` recomputes
that share for whatever frame it is handed and
:func:`assert_geometry_reconstructs` refuses below
:data:`REQUIRED_GEOMETRY_AGREEMENT`.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from cbb_betting_lab import population

__all__ = [
    "ZONES",
    "Zone",
    "ShotZoneError",
    "NotFullyCharted",
    "GeometryDoesNotReconstruct",
    "ShotsUnattributed",
    "attacking_frame",
    "assign_zones",
    "geometry_agreement",
    "assert_fully_charted",
    "assert_geometry_reconstructs",
    "assert_every_shot_is_attributed",
    "build_record",
    "render",
    "read_record",
    "write_record",
    "write_report",
]

# --------------------------------------------------------------------------
# The court, in feet
# --------------------------------------------------------------------------

#: Distance from centre court to the centre of a basket. A regulation floor is
#: 94 feet long and the basket's centre is 5.25 feet from the baseline, so this
#: is 47 - 5.25 and not a fitted number. The coordinates agree: field goal
#: attempts in 2025-26 run from -46.75 to +46.75, which is the same floor.
HOOP_X = 41.75

#: The baseline, in the same frame. A regulation floor is 94 ft long, so the
#: baseline sits 47 ft from centre court and the hoop 5.25 ft inside it.
BASELINE_X = 47.0

#: Half the floor's width. Attempts run from -25.0 to +25.0 in `coordinate_y`.
HALF_WIDTH = 25.0

#: The men's three-point arc, 22 feet 1.75 inches, uniform since 2019-20. At
#: the baseline the arc reaches 21.5 feet from centre, which is 3.5 feet inside
#: the sideline -- so unlike the NBA there is no corner cut-off and the arc is a
#: true circle. That is why one radius classifies every three.
ARC = 22.146

#: Beyond this lateral offset a three is a **corner** three. Measured: at
#: `|y| >= 21` the median attempt sits 6 feet from the baseline against 13 feet
#: just inside it, and points per attempt step from about 0.99 to about 1.06.
#: The boundary is where the geometry changes, not where the efficiency is
#: most flattering.
CORNER_Y = 21.0

#: A coordinate outside the floor is a sentinel rather than a shot. The feed
#: carries values near +/-214,748,406 -- a 32-bit overflow wearing a decimal
#: point -- and 0.2% of 2025-26 attempts are one. They are dropped and counted,
#: never clipped onto the floor, because a clipped sentinel is a shot at the
#: sideline that nobody took.
ON_FLOOR = 100.0


@dataclass(frozen=True)
class Zone:
    """One place on the floor, and the rule that puts a shot in it."""

    key: str
    label: str
    #: Read in order; the first whose test passes owns the shot. Declared as an
    #: ordered list rather than a set of disjoint predicates so that a shot can
    #: never fall in two zones or none, which a hand-written set of `and`
    #: clauses did on the first draft (a corner three at 21.9 feet was both a
    #: corner and a mid-range shot).
    order: int


#: The six zones, rim outward. Six and not the conventional five or seven: the
#: mid-range is one zone because the measurement says it is one zone, and the
#: three-point line is three because the measurement says it is three.
ZONES: tuple[Zone, ...] = (
    Zone("rim", "Rim", 0),
    Zone("short_paint", "Short paint", 1),
    Zone("mid_range", "Mid-range", 2),
    Zone("corner_three", "Corner 3", 3),
    Zone("above_break_three", "Above the break 3", 4),
    Zone("deep_three", "Deep 3", 5),
)

ZONE_KEYS: tuple[str, ...] = tuple(z.key for z in ZONES)

#: Where the rim stops and the short paint starts, and where that stops.
RIM_FEET = 4.0
SHORT_PAINT_FEET = 6.0

#: Where an above-the-break three becomes a deep one. Points per attempt fall
#: from 1.016 in the 24-26 band to 0.976 in 26-28 and 0.917 in 28-30, so the
#: line is drawn where the fall becomes monotone.
DEEP_THREE_FEET = 26.0

# --------------------------------------------------------------------------
# The refusals
# --------------------------------------------------------------------------

#: A season must be charted at least this completely to be described. 0.98 and
#: not 1.00 because a handful of games in a complete season carry a sentinel
#: coordinate on every shot; 2025-26 measures 0.998. Nothing between 0.28 and
#: 0.98 has ever been observed, so this bar separates the two states the feed
#: actually has rather than splitting a continuum.
REQUIRED_CHARTED_SHARE = 0.98

#: The share of attempts whose coordinate-implied value must match the feed's
#: own 2-or-3 label. Measured 0.9877 on 2025-26. Below 0.95 the coordinates are
#: describing a different floor than the one the labels came from.
REQUIRED_GEOMETRY_AGREEMENT = 0.95

#: How much of a season may be tagged to a team that is not on the floor.
#: Measured on 2025-26: **14 attempts in 2 games**, 0.0019%, where ESPN tagged
#: a shot to a third team id outside the normal range (123421 in a game
#: between 304 and 2701; 5736 in one between 155 and 509). Both games are
#: otherwise clean -- 3 stray of 114 attempts and 11 of 122 -- so this is the
#: feed mis-tagging a handful of rows and not a join coming apart.
#:
#: The threshold is 50x the observed rate and still refuses everything a real
#: defect looks like: a broken dtype cast reports ~100%, a changed id
#: namespace reports most of a season. 0.1% is about seven games' worth of
#: shots, which is the point at which this stops being data entry. Decision
#: 42's rule: exclude, count, reconcile, and keep a bar that still refuses.
MAX_UNATTRIBUTED_SHARE = 0.001

#: Below this many attempts a team's zone gets a count and no rate. A zone rate
#: on nine attempts invites a reader to follow the shape of the profile rather
#: than the samples under it -- the same floor, for the same reason, as the
#: calibration tables in `prop_grading`.
MINIMUM_ZONE_ATTEMPTS = 25

#: Bumped when the record's shape changes, so a stale record fails loudly at
#: re-render rather than rendering a report with holes in it.
#: 2 -- every profile row carries `share_ranked_of`. A version-1 record has
#: only `ranked_of`, and the renderer printed the share rank against it: a
#: rank over every team, divided by a count of the teams above the attempt
#: floor. They agree only while no team is under it.
RECORD_VERSION = 2


class ShotZoneError(RuntimeError):
    """Anything this module refuses to describe."""


class NotFullyCharted(ShotZoneError):
    """The season's coordinates are a sample of games somebody else chose."""


class GeometryDoesNotReconstruct(ShotZoneError):
    """The coordinates disagree with the feed's own shot labels."""


class ShotsUnattributed(ShotZoneError):
    """A shot belongs to neither team on the floor."""


class NoDivisionOne(ShotZoneError):
    """The schedule names no Division-I membership to rank within."""


# --------------------------------------------------------------------------
# The frame
# --------------------------------------------------------------------------

#: The columns read from the play-by-play. Named so a missing one raises here
#: rather than producing a frame with a silently absent condition.
REQUIRED_COLUMNS: tuple[str, ...] = (
    "game_id",
    "season",
    "team_id",
    "home_team_id",
    "away_team_id",
    "type_text",
    "shooting_play",
    "scoring_play",
    "score_value",
    "coordinate_x",
    "coordinate_y",
)


def field_goal_attempts(pbp: pd.DataFrame) -> pd.DataFrame:
    """Every field goal attempt, free throws removed, nothing else dropped.

    Free throws are excluded because they are not shots from a place on the
    floor -- they are all from the same place -- and a zone panel that counted
    them would report a rim rate that moves with foul rate.
    """
    missing = [c for c in REQUIRED_COLUMNS if c not in pbp.columns]
    if missing:
        raise ShotZoneError(
            f"The play-by-play is missing {missing}, and this module reads "
            f"{list(REQUIRED_COLUMNS)}. A frame short a column produces a "
            "profile with a condition silently absent from it."
        )
    shooting = pbp["shooting_play"].fillna(False).astype(bool)
    free_throw = (
        pbp["type_text"].astype("string").str.contains("FreeThrow", na=False)
    )
    return pbp.loc[shooting & ~free_throw].copy()


def charted_share(attempts: pd.DataFrame) -> dict:
    """How much of this season carries usable coordinates, by GAME.

    The share is taken over games and not over shots, because the feed charts
    whole games: a shot-weighted share would read 6% as "most games are a bit
    thin" when what it means is "94% of games are absent entirely".
    """
    on_floor = _on_floor(attempts)
    per_game = on_floor.groupby(attempts["game_id"]).any()
    games = int(len(per_game))
    charted = int(per_game.sum())
    return {
        "games": games,
        "charted_games": charted,
        "share": (charted / games) if games else 0.0,
        "attempts": int(len(attempts)),
        "attempts_on_floor": int(on_floor.sum()),
        "sentinel_coordinates": int((~on_floor).sum()),
    }


def _on_floor(attempts: pd.DataFrame) -> pd.Series:
    x = pd.to_numeric(attempts["coordinate_x"], errors="coerce")
    y = pd.to_numeric(attempts["coordinate_y"], errors="coerce")
    return (x.abs() <= ON_FLOOR) & (y.abs() <= ON_FLOOR)


def assert_fully_charted(attempts: pd.DataFrame, *, season) -> dict:
    """Refuse a season the feed only partly charted. There is no override."""
    census = charted_share(attempts)
    if census["share"] < REQUIRED_CHARTED_SHARE:
        raise NotFullyCharted(
            f"Season {season} carries shot coordinates for "
            f"{census['charted_games']:,} of {census['games']:,} games "
            f"({census['share']:.1%}), below the {REQUIRED_CHARTED_SHARE:.0%} "
            "this panel requires. The feed charts whole games and chooses "
            "which ones, so this is a sample of games selected by ESPN's "
            "production schedule -- broadcast games -- and a zone profile "
            "built on it would describe the televised part of Division I "
            "while reading as though it described the sport. Use a fully "
            "charted season; there is no flag that turns this off."
        )
    return census


def attacking_frame(attempts: pd.DataFrame) -> pd.DataFrame:
    """Both teams in one frame, attacking a basket at `+HOOP_X`.

    The away team is rotated 180 degrees rather than mirrored in x. A mirror
    would put the hoop in the right place and reverse the floor's handedness
    with it, so every corner three would swap sides and a left/right reading
    would be exactly backwards for half the league.
    """
    frame = attempts.loc[_on_floor(attempts)].copy()
    team = pd.to_numeric(frame["team_id"], errors="coerce")
    home = pd.to_numeric(frame["home_team_id"], errors="coerce")
    away = pd.to_numeric(frame["away_team_id"], errors="coerce")
    is_home = team.eq(home)
    frame["offense_id"] = team
    frame["defense_id"] = np.where(is_home, away, home)
    x = pd.to_numeric(frame["coordinate_x"], errors="coerce")
    y = pd.to_numeric(frame["coordinate_y"], errors="coerce")
    frame["x"] = np.where(is_home, x, -x)
    frame["y"] = np.where(is_home, y, -y)
    # Distance from the hoop ALONG X, which is not the distance from the
    # baseline: the baseline is at `BASELINE_X` and the hoop stands
    # `BASELINE_X - HOOP_X` = 5.25 ft in front of it. This was called
    # `baseline_feet`, and the module's own docstring then quoted a corner
    # boundary "from the baseline" that was measured from here instead.
    frame["x_from_hoop"] = HOOP_X - frame["x"]
    frame["baseline_feet"] = BASELINE_X - frame["x"]
    frame["distance"] = np.hypot(frame["x_from_hoop"], frame["y"])
    value = pd.to_numeric(frame["score_value"], errors="coerce")
    scored = frame["scoring_play"].fillna(False).astype(bool)
    frame["shot_value"] = value
    frame["points"] = np.where(scored, value, 0.0)
    frame["_is_home"] = is_home
    frame["_team"] = team
    frame["_home"] = home
    frame["_away"] = away
    return frame


def attribution_census(frame: pd.DataFrame) -> dict:
    """How many attempts belong to neither team, and in how many games."""
    stray = ~(frame["_team"].eq(frame["_home"]) | frame["_team"].eq(frame["_away"]))
    return {
        "attempts": int(len(frame)),
        "unattributed": int(stray.sum()),
        "unattributed_games": int(frame.loc[stray, "game_id"].nunique()),
        "share": (float(stray.sum()) / len(frame)) if len(frame) else 0.0,
    }


def assert_every_shot_is_attributed(frame: pd.DataFrame) -> dict:
    """Refuse a frame where too much of it belongs to neither team.

    A handful of mis-tagged rows is the feed; a large share is the join. The
    two are told apart by their size and by nothing else, which is why the
    number is declared in :data:`MAX_UNATTRIBUTED_SHARE` rather than decided
    here. `team_id` is float64 and `home_team_id` is int32, so comparing them
    as strings reports every row unattributed on a join that is in fact
    almost perfect -- the cast happens in `attacking_frame`, and this is the
    assertion that it happened.

    The stray rows are **excluded and counted**, never reassigned to the
    likelier of the two teams: a shot the feed could not attribute is not
    evidence about either team's floor, and guessing would put it in a zone
    profile as though it were.
    """
    census = attribution_census(frame)
    if census["share"] > MAX_UNATTRIBUTED_SHARE:
        raise ShotsUnattributed(
            f"{census['unattributed']:,} of {census['attempts']:,} attempts "
            f"({census['share']:.4%}) belong to neither the home nor the away "
            f"team, across {census['unattributed_games']:,} game(s) -- above "
            f"the {MAX_UNATTRIBUTED_SHARE:.1%} a feed's own mis-tagging has "
            "ever accounted for. Either the ids are being compared across "
            "types -- `team_id` is float64 against int32 home and away ids, "
            "and a string comparison reports 100% unattributed on a perfect "
            "join -- or the frame mixes games."
        )
    return census


def assign_zones(frame: pd.DataFrame) -> pd.Series:
    """One zone per attempt, by an ordered cascade rather than disjoint tests.

    Ordered because the boundaries touch: a shot at 22.1 feet in the corner is
    beyond the arc by the radius and inside it by rounding, and a set of
    independent `and` clauses put it in two zones at once on the first draft.
    Here the first matching rule owns it and the last rule is unconditional, so
    a shot lands in exactly one zone and never in none.
    """
    distance = frame["distance"]
    lateral = frame["y"].abs()
    beyond = distance >= ARC
    zone = pd.Series("mid_range", index=frame.index, dtype="object")
    zone[beyond & (lateral >= CORNER_Y)] = "corner_three"
    zone[beyond & (lateral < CORNER_Y) & (distance < DEEP_THREE_FEET)] = (
        "above_break_three"
    )
    zone[beyond & (lateral < CORNER_Y) & (distance >= DEEP_THREE_FEET)] = "deep_three"
    inside = ~beyond
    zone[inside & (distance <= RIM_FEET)] = "rim"
    zone[inside & (distance > RIM_FEET) & (distance <= SHORT_PAINT_FEET)] = (
        "short_paint"
    )
    return zone


def geometry_agreement(frame: pd.DataFrame) -> dict:
    """Does the distance implied by the coordinates match the feed's label?

    The feed tags every attempt -- made and missed -- with a `score_value` of 2
    or 3, and that label is not derived from the coordinates. So this is a
    check against independent ground truth rather than an internal
    consistency test, which is the only kind worth running on a geometry.
    """
    implied = np.where(frame["distance"] >= ARC, 3.0, 2.0)
    labelled = pd.to_numeric(frame["shot_value"], errors="coerce")
    usable = labelled.isin([2.0, 3.0])
    agree = (implied == labelled) & usable
    n = int(usable.sum())
    return {
        "attempts": n,
        "agree": int(agree.sum()),
        "share": (float(agree.sum()) / n) if n else 0.0,
        "hoop_feet_from_baseline": round(47.0 - HOOP_X, 2),
    }


def assert_geometry_reconstructs(frame: pd.DataFrame) -> dict:
    """Refuse coordinates that do not reproduce the arc they were shot over."""
    census = geometry_agreement(frame)
    if census["share"] < REQUIRED_GEOMETRY_AGREEMENT:
        raise GeometryDoesNotReconstruct(
            f"The coordinates imply the feed's own 2-or-3 label on "
            f"{census['share']:.2%} of {census['attempts']:,} attempts, below "
            f"the {REQUIRED_GEOMETRY_AGREEMENT:.0%} this panel requires. The "
            f"arc is a circle of {ARC} feet about a basket "
            f"{47.0 - HOOP_X:.2f} feet from the baseline; coordinates that "
            "cannot place a three outside it are describing a different floor "
            "than the labels came from, and every zone below would be a "
            "rearrangement of that disagreement."
        )
    return census


# --------------------------------------------------------------------------
# The profiles
# --------------------------------------------------------------------------

#: Which direction is good, per side. Offence wants points per attempt high;
#: defence wants the points it allows low. Stated once, here, so a rank cannot
#: be computed the wrong way round in one of the two tables and look plausible
#: in both -- the defensive table is the one where a reader would not notice.
BETTER_WHEN = {"offense": "high", "defense": "low"}


def league_baseline(frame: pd.DataFrame, zones: pd.Series) -> list[dict]:
    """What a Division-I attempt is worth in each zone, over everybody."""
    total = int(len(frame))
    rows = []
    for zone in ZONES:
        mask = zones == zone.key
        attempts = int(mask.sum())
        points = float(frame.loc[mask, "points"].sum())
        rows.append(
            {
                "zone": zone.key,
                "label": zone.label,
                "attempts": attempts,
                "attempt_share": (attempts / total) if total else 0.0,
                "points_per_attempt": (points / attempts) if attempts else None,
            }
        )
    return rows


def zone_profile(frame: pd.DataFrame, zones: pd.Series, *, side: str) -> list[dict]:
    """Every team's profile on one side of the ball, with a Division-I rank.

    A zone below :data:`MINIMUM_ZONE_ATTEMPTS` carries its count and no rate,
    and **takes no rank**: ranking a team 4th on eleven attempts puts a number
    in a column that a reader will compare against numbers built on six
    hundred.
    """
    if side not in BETTER_WHEN:
        raise ShotZoneError(
            f"side={side!r}; the two sides of the ball are {sorted(BETTER_WHEN)}."
        )
    key = "offense_id" if side == "offense" else "defense_id"
    work = pd.DataFrame(
        {
            "team": frame[key].astype("Int64"),
            "zone": zones.values,
            "points": frame["points"].values,
        }
    )
    grouped = work.groupby(["team", "zone"], observed=True)["points"].agg(
        ["size", "sum"]
    )
    grouped.columns = ["attempts", "points"]
    grouped = grouped.reset_index()
    totals = work.groupby("team", observed=True).size().rename("team_attempts")
    grouped = grouped.merge(totals, left_on="team", right_index=True, how="left")
    grouped["attempt_share"] = grouped["attempts"] / grouped["team_attempts"]
    enough = grouped["attempts"] >= MINIMUM_ZONE_ATTEMPTS
    grouped["points_per_attempt"] = np.where(
        enough, grouped["points"] / grouped["attempts"], np.nan
    )
    ascending = BETTER_WHEN[side] == "low"
    grouped["rank"] = (
        grouped.groupby("zone")["points_per_attempt"]
        .rank(ascending=ascending, method="min")
        .astype("Int64")
    )
    grouped["share_rank"] = (
        grouped.groupby("zone")["attempt_share"]
        .rank(ascending=False, method="min")
        .astype("Int64")
    )
    grouped["ranked_of"] = grouped.groupby("zone")["points_per_attempt"].transform(
        lambda s: int(s.notna().sum())
    )
    # The two ranks are over DIFFERENT populations and so need different
    # denominators. `rank` is over the teams with a rate to rank -- a zone
    # under the floor has `points_per_attempt` NaN and takes no rank -- while
    # `share_rank` is over every team present, because an attempt share is a
    # count over a team's own total and is well measured however small the
    # numerator is: three corner threes out of eighteen hundred really is the
    # lowest rate in the country. Printing the share rank against `ranked_of`
    # is a rank counted one way against a field counted another, and once any
    # team falls under the floor it prints ranks like 365/364.
    grouped["share_ranked_of"] = grouped.groupby("zone")["attempt_share"].transform(
        lambda s: int(s.notna().sum())
    )
    out = []
    for row in grouped.itertuples(index=False):
        out.append(
            {
                "team_id": int(row.team),
                "zone": str(row.zone),
                "attempts": int(row.attempts),
                "team_attempts": int(row.team_attempts),
                "attempt_share": float(row.attempt_share),
                "points_per_attempt": (
                    None if pd.isna(row.points_per_attempt)
                    else float(row.points_per_attempt)
                ),
                "rank": None if pd.isna(row.rank) else int(row.rank),
                "share_rank": None if pd.isna(row.share_rank) else int(row.share_rank),
                "ranked_of": int(row.ranked_of),
                "share_ranked_of": int(row.share_ranked_of),
                "enough_attempts": bool(row.attempts >= MINIMUM_ZONE_ATTEMPTS),
            }
        )
    return out


@dataclass
class ShotZoneInputs:
    """Everything :func:`build_record` is handed. It opens nothing itself.

    `schedule` is **required and not optional**, because it is the only thing
    that says who is in Division I. Without it the first build of this record
    ranked 721 teams -- every D-II and NAIA programme a D-I school bought a
    November game from -- and printed the result in a column headed *D-I
    rank*. A rank of 14th is a different statement against 364 teams than
    against 721, and nothing on the page would have said which.
    """

    pbp: pd.DataFrame
    season: int
    schedule: pd.DataFrame
    source: str = ""
    team_names: Mapping = field(default_factory=dict)


def division_one_only(frame: pd.DataFrame, schedule: pd.DataFrame) -> tuple:
    """Attempts from games with Division-I teams on **both** ends.

    Membership is `population.division_one_team_ids` -- the feed's conference
    id, which is this lab's marker everywhere else -- rather than a rule
    written here, so a team is in Division I for this panel exactly when it is
    in Division I for the ratings model that prices it.

    Both ends, not one, and it is the stricter choice on purpose: a D-I team's
    rim rate measured partly against the D-II school it bought a November game
    from is a rate against a different sport, and it inflates whichever zone
    that school could not defend.
    """
    di = population.division_one_team_ids(schedule)
    if not di:
        raise NoDivisionOne(
            "The schedule gives no team a conference id, so there is no "
            "Division-I membership to rank within. `population."
            "division_one_team_ids` reads `home_conference_id` and "
            "`away_conference_id`; a schedule frame without them produces an "
            "empty set and would silently rank every programme the feed has "
            "ever seen against every other."
        )
    both = frame["offense_id"].isin(di) & frame["defense_id"].isin(di)
    census = {
        "division_one_teams": int(len(di)),
        "attempts": int(len(frame)),
        "attempts_division_one": int(both.sum()),
        "attempts_dropped": int((~both).sum()),
        "share_dropped": (float((~both).sum()) / len(frame)) if len(frame) else 0.0,
    }
    return frame.loc[both].copy(), census


def build_record(inputs: ShotZoneInputs, *, generated_at: str = "") -> dict:
    """The record. Every refusal fires before a single zone is counted."""
    attempts = field_goal_attempts(inputs.pbp)
    coverage = assert_fully_charted(attempts, season=inputs.season)
    frame = attacking_frame(attempts)
    attribution = assert_every_shot_is_attributed(frame)
    # Counted above, dropped here, and the count rides in the record. Every
    # number below is over the attributed rows, so the record's own census is
    # the only place the difference is visible -- which is where decision 42
    # says it has to be.
    frame = frame.loc[
        frame["_team"].eq(frame["_home"]) | frame["_team"].eq(frame["_away"])
    ].copy()
    frame, membership = division_one_only(frame, inputs.schedule)
    geometry = assert_geometry_reconstructs(frame)
    zones = assign_zones(frame)
    unplaced = int((~zones.isin(ZONE_KEYS)).sum())
    if unplaced:
        raise ShotZoneError(
            f"{unplaced:,} attempts landed in no zone. The cascade in "
            "`assign_zones` ends in an unconditional rule, so this is "
            "impossible unless a zone key was renamed in one place only."
        )
    return {
        "record_version": RECORD_VERSION,
        "descriptive_only": True,
        "season": int(inputs.season),
        "source": str(inputs.source),
        "generated_at": str(generated_at),
        "coverage": coverage,
        "attribution": attribution,
        "membership": membership,
        "geometry": geometry,
        "zones": [
            {"key": z.key, "label": z.label, "order": z.order} for z in ZONES
        ],
        "boundaries": {
            "hoop_x": HOOP_X,
            "arc": ARC,
            "corner_y": CORNER_Y,
            "rim_feet": RIM_FEET,
            "short_paint_feet": SHORT_PAINT_FEET,
            "deep_three_feet": DEEP_THREE_FEET,
        },
        "minimum_zone_attempts": MINIMUM_ZONE_ATTEMPTS,
        "league": league_baseline(frame, zones),
        "offense": zone_profile(frame, zones, side="offense"),
        "defense": zone_profile(frame, zones, side="defense"),
        "team_names": {str(k): str(v) for k, v in dict(inputs.team_names).items()},
    }


# --------------------------------------------------------------------------
# The report
# --------------------------------------------------------------------------

#: The sentence the panel carries wherever it is rendered. It is a constant so
#: that a caller cannot render the tables without it, and so that changing it
#: changes it everywhere at once.
DESCRIPTIVE_ONLY_SENTENCE = (
    "**This is a description and not a claim.** Nothing here is compared to a "
    "price, no advantage is computed, and none of this lab's reserved verdict "
    "phrases appear below. Two profiles sit side by side because that is what "
    "the panel is for; whether the space between them is worth anything is a "
    "question this record does not ask and cannot answer. Under the "
    "experiment ledger's `descriptive_only` rule it costs no hypothesis and "
    "may never be promoted to a finding."
)


def _rank_cell(rank, of) -> str:
    if rank is None:
        return "—"
    return f"{int(rank)}/{int(of)}"


def _ppa_cell(value) -> str:
    return "—" if value is None else f"{value:.3f}"


def _zone_order(record: Mapping) -> list[str]:
    return [z["key"] for z in sorted(record["zones"], key=lambda z: z["order"])]


def _by_team(rows: Sequence[Mapping]) -> dict:
    out: dict = {}
    for row in rows:
        out.setdefault(int(row["team_id"]), {})[str(row["zone"])] = row
    return out


def render(record: Mapping) -> str:
    """The league page: what a shot is worth where, and what was refused."""
    if int(record.get("record_version", 0)) != RECORD_VERSION:
        raise ShotZoneError(
            f"This is a version {record.get('record_version')} record and "
            f"this module renders version {RECORD_VERSION}."
        )
    cover, geo = record["coverage"], record["geometry"]
    attr, member = record["attribution"], record["membership"]
    labels = {z["key"]: z["label"] for z in record["zones"]}
    lines = [
        f"# Shot zones — Division I men's basketball, {record['season']}",
        "",
        DESCRIPTIVE_ONLY_SENTENCE,
        "",
        "## What a Division-I attempt is worth, by zone",
        "",
        "| Zone | Attempts | Share | Points / attempt |",
        "|:---|---:|---:|---:|",
    ]
    for row in record["league"]:
        lines.append(
            f"| {row['label']} | {row['attempts']:,} | "
            f"{row['attempt_share']:.1%} | {_ppa_cell(row['points_per_attempt'])} |"
        )
    lines += [
        "",
        "The mid-range is one zone rather than two because the measurement "
        "makes it one: every two-foot band from six feet to the arc sits "
        "between 0.738 and 0.800 points per attempt, with no ordering worth "
        "the name. A boundary drawn inside it would be a distinction the "
        "sport does not make.",
        "",
        "## The population, and what it refused",
        "",
        "| | |",
        "|:---|---:|",
        f"| Games in the season | {cover['games']:,} |",
        f"| Games carrying shot coordinates | {cover['charted_games']:,} "
        f"({cover['share']:.1%}) |",
        f"| Field goal attempts | {cover['attempts']:,} |",
        f"| Dropped — coordinate off the floor | "
        f"{cover['sentinel_coordinates']:,} |",
        f"| Dropped — tagged to neither team | {attr['unattributed']:,} "
        f"in {attr['unattributed_games']:,} game(s) ({attr['share']:.4%}) |",
        f"| Dropped — a non-Division-I team on one end | "
        f"{member['attempts_dropped']:,} ({member['share_dropped']:.1%}) |",
        f"| **Described** | **{member['attempts_division_one']:,}** |",
        f"| Division-I programmes | {member['division_one_teams']:,} |",
        "",
        f"Coordinates imply the feed's own two-or-three label on "
        f"**{geo['share']:.2%}** of {geo['attempts']:,} attempts, and the "
        f"geometry puts the basket {geo['hoop_feet_from_baseline']} feet from "
        "the baseline, which is where a basket goes. That label is not "
        "derived from the coordinates, so the agreement is a check against "
        "independent ground truth rather than a consistency test.",
        "",
        f"A season charted below {REQUIRED_CHARTED_SHARE:.0%} is refused and "
        "there is no flag that turns the refusal off — see this module's "
        "docstring for the seven seasons that fail it and why a partly "
        "charted season is not a smaller version of a complete one.",
        "",
    ]
    return "\n".join(lines)


def render_matchup(
    record: Mapping, *, offense: int, defense: int, names: Mapping | None = None
) -> str:
    """One team's offensive floor beside the floor its opponent concedes.

    Deliberately two tables and not one number. The football chart this is
    built from prints the offence's gaps beside the defence's and computes no
    mismatch score, and that restraint is the reason it can be read without
    being believed. A column here that subtracted one rank from the other
    would be a claim wearing a description's clothes.
    """
    look = dict(names or record.get("team_names") or {})
    off_name = look.get(str(offense), f"team {offense}")
    def_name = look.get(str(defense), f"team {defense}")
    offense_rows = _by_team(record["offense"]).get(int(offense))
    defense_rows = _by_team(record["defense"]).get(int(defense))
    missing = [
        name
        for name, rows in ((off_name, offense_rows), (def_name, defense_rows))
        if not rows
    ]
    if missing:
        raise ShotZoneError(
            f"{missing} has no zone profile in the {record['season']} record. "
            "A team absent from a fully charted season is a team that played "
            "no Division-I opponent, and inventing a profile for it would put "
            "a league-average floor on the page under its name."
        )
    labels = {z["key"]: z["label"] for z in record["zones"]}
    league = {r["zone"]: r for r in record["league"]}
    lines = [
        f"## {off_name} offence vs {def_name} defence — {record['season']}",
        "",
        DESCRIPTIVE_ONLY_SENTENCE,
        "",
        f"| Zone | {off_name} share | rank | {off_name} PPA | rank | "
        f"{def_name} PPA allowed | rank | D-I |",
        "|:---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for key in _zone_order(record):
        o, d = offense_rows.get(key), defense_rows.get(key)
        if not o or not d:
            # A team with no row in a zone took no shots there, and dropping
            # the row would leave a reader unable to tell zero from missing --
            # in a table whose whole job is to show where shots come from,
            # "never from here" is the strongest reading on the page.
            side = off_name if not o else def_name
            lines.append(
                f"| {labels[key]} | — | — | — | — | — | — | "
                f"{_ppa_cell(league[key]['points_per_attempt'])} |"
            )
            lines.append(
                f"| *{labels[key]}: {side} attempted none* | | | | | | | |"
            )
            continue
        lines.append(
            f"| {labels[key]} | {o['attempt_share']:.1%} | "
            f"{_rank_cell(o['share_rank'], o['share_ranked_of'])} | "
            f"{_ppa_cell(o['points_per_attempt'])} | "
            f"{_rank_cell(o['rank'], o['ranked_of'])} | "
            f"{_ppa_cell(d['points_per_attempt'])} | "
            f"{_rank_cell(d['rank'], d['ranked_of'])} | "
            f"{_ppa_cell(league[key]['points_per_attempt'])} |"
        )
    lines += [
        "",
        f"Offensive ranks read 1 = most efficient; defensive ranks read "
        f"1 = fewest points allowed per attempt. A zone below "
        f"{MINIMUM_ZONE_ATTEMPTS} attempts carries its count and no rate, and "
        "takes no rank.",
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# IO
# --------------------------------------------------------------------------


def write_record(record: Mapping, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return path


def read_record(path: Path) -> dict:
    path = Path(path)
    if not path.is_file():
        raise ShotZoneError(f"{path} does not exist, so there is no record.")
    record = json.loads(path.read_text(encoding="utf-8"))
    version = int(record.get("record_version", 0))
    if version != RECORD_VERSION:
        raise ShotZoneError(
            f"{path} is a version {version} record and this module writes "
            f"version {RECORD_VERSION}. Re-run the measurement rather than "
            "rendering a report with holes in it."
        )
    return record


def write_report(record: Mapping, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(record), encoding="utf-8")
    return path
