"""Conference tiers, derived from measured strength rather than a list of names.

Cooper's requirement: *"Conference tiers are different distributions. Fit and
measure per tier at minimum (high-major / mid-major / low-major, defined
explicitly and recorded). Never report a single pooled headline across the
whole of D-I."*

## Why this is measured and not a hardcoded list

**Twenty-nine schools change conference for 2026-27** — the Pac-12 resumes with
nine members drawn from the Mountain West, Sun Belt and WCC; the WAC is renamed
the UAC; the MAAC is renamed the Metro Conference. A hardcoded conference-name
list would be wrong on the day it was written, and a hardcoded *membership* list
would be wrong every summer.

So a **team's** tier comes from its own strength, and a conference's tier is the
median of its members'. That follows the teams through realignment for free, and
it means a conference that loses its four best programmes is re-tiered by the
data rather than by somebody remembering to edit a file.

## The measurement, and why it is this one

Mean scoring margin in **non-conference games against other D-I opponents**.
Non-conference because a conference game measures a team against its own tier
and tells you nothing about where that tier sits; D-I-only because the November
buy-games are excluded from everything.

Measured on 2025-26 it produces a clean, continuous gradient across the 31
conferences — from **+13.9** (Big Ten) to **−20.8** — with no ties and no
inversions, which is what makes cut points defensible rather than arbitrary.

## The cut points are declared in advance

:data:`HIGH_MAJOR_MARGIN` and :data:`MID_MAJOR_MARGIN`, chosen from the shape of
that gradient and **fixed before any market was measured per tier**. They are
not re-tuned to make a tier's ROI look better; that is the whole point of
writing them down here.

## Walk-forward, like everything else

`tier_table` takes the seasons it may look at, and a caller pricing a game in
season N passes seasons strictly before N. A team's tier in November 2026 is
what its 2025-26 non-conference record said, not what its 2026-27 record will
say. `docs/why_the_model_does_or_does_not_have_an_edge.md` will state the
consequence: a team that improves enormously is mis-tiered for a season, and
that is a cost paid to avoid a leak.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd

from cbb_betting_lab.population import division_one_team_ids


class Tier(str, Enum):
    HIGH_MAJOR = "high_major"
    MID_MAJOR = "mid_major"
    LOW_MAJOR = "low_major"
    #: A team with too little prior non-conference evidence to place — a first
    #: D-I season, or a conference the feed has not seen before. Priced with the
    #: mid-major prior and **reported separately**, never folded into a tier's
    #: number.
    UNPLACED = "unplaced"


#: Declared in advance, from the 2025-26 gradient. Above this a conference is
#: high-major; the five that clear it are the ones anybody would name.
HIGH_MAJOR_MARGIN = 8.0
#: Above this a conference is mid-major, below it low-major.
MID_MAJOR_MARGIN = -3.0

#: Below this many non-conference D-I games in the window, a team is UNPLACED.
#: A tier assigned off four games is a coin flip wearing a label.
MINIMUM_GAMES = 8


@dataclass(frozen=True)
class TierTable:
    """Which tier each team and conference is in, and on what evidence."""

    team_tier: dict
    conference_tier: dict
    team_margin: dict
    conference_margin: dict
    seasons: tuple[int, ...]

    def tier_for(self, team_id) -> Tier:
        return self.team_tier.get(team_id, Tier.UNPLACED)

    def summary_line(self) -> str:
        counts: dict[str, int] = {}
        for tier in self.team_tier.values():
            counts[tier.value] = counts.get(tier.value, 0) + 1
        parts = ", ".join(f"{k}={v}" for k, v in sorted(counts.items()))
        return (
            f"Tiers from seasons {list(self.seasons)}: {parts} "
            f"({len(self.conference_tier)} conferences)."
        )


def _long_form(schedule: pd.DataFrame) -> pd.DataFrame:
    """One row per team-game, with the opponent's conference beside it."""
    frames = []
    for side, other in (("home", "away"), ("away", "home")):
        columns = {
            f"{side}_id": "team_id",
            f"{side}_conference_id": "conference_id",
            f"{side}_score": "points_for",
            f"{other}_score": "points_against",
            f"{other}_conference_id": "opponent_conference_id",
            f"{other}_id": "opponent_id",
        }
        if not set(columns) <= set(schedule.columns):
            continue
        frames.append(schedule[list(columns)].rename(columns=columns))
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


#: Statuses of a game that was played to a result, for a schedule that does
#: not carry ESPN's own `status_type_completed` flag. On every real season
#: from 2019 to 2027 these two names are exactly the rows the flag marks True.
COMPLETED_STATUSES = ("STATUS_FINAL", "STATUS_FORFEIT")


def played_games(schedule: pd.DataFrame) -> pd.DataFrame:
    """The rows of one season's schedule that were played to a result.

    **An unplayed fixture carries a score of 0-0, not a missing one.** The
    2027 schedule arrives with all 1,629 games `STATUS_SCHEDULED` and both
    scores stored as integer zeros, and `dropna` on the scores let every one of
    them into the tier margins as a game decided by nothing: 27 of 365 teams
    would change tier on the first refit to include 2027. Postponed and
    cancelled fixtures in earlier seasons (64 of them, 2023-2026) got in the
    same way, and moved no tier. A schedule that says neither way is refused
    rather than assumed played.

    Call it per season, BEFORE any concat: a season missing the flag would
    otherwise read NaN for it and leave the table without a word.
    """
    if "status_type_completed" in schedule.columns:
        flag = schedule["status_type_completed"].map(
            lambda value: value is True or str(value).strip().lower() == "true"
        )
        return schedule[flag.astype(bool)]
    if "status_type_name" in schedule.columns:
        return schedule[schedule["status_type_name"].isin(COMPLETED_STATUSES)]
    raise ValueError(
        "This schedule carries neither `status_type_completed` nor "
        "`status_type_name`, so a played game cannot be told from an unplayed "
        "fixture stored as 0-0. Refusing to compute tiers from it."
    )


def tier_table(schedules: dict[int, pd.DataFrame], seasons: tuple[int, ...]) -> TierTable:
    """Tiers from the named seasons only. Pass seasons strictly before the
    one being priced."""
    usable = [played_games(schedules[s]) for s in seasons if s in schedules]
    if not usable:
        return TierTable({}, {}, {}, {}, seasons)
    schedule = pd.concat(usable, ignore_index=True)
    di = division_one_team_ids(schedule)

    long = _long_form(schedule)
    if long.empty:
        return TierTable({}, {}, {}, {}, seasons)
    long = long.dropna(subset=["conference_id", "opponent_conference_id", "points_for", "points_against"])
    # Non-conference, D-I against D-I only.
    long = long[
        (long["conference_id"] != long["opponent_conference_id"])
        & long["team_id"].isin(di)
        & long["opponent_id"].isin(di)
    ]
    long = long.assign(margin=long["points_for"] - long["points_against"])

    per_team = long.groupby("team_id").agg(
        games=("margin", "size"), margin=("margin", "mean")
    )
    team_margin = per_team["margin"].to_dict()

    def _tier(margin: float) -> Tier:
        if margin >= HIGH_MAJOR_MARGIN:
            return Tier.HIGH_MAJOR
        if margin >= MID_MAJOR_MARGIN:
            return Tier.MID_MAJOR
        return Tier.LOW_MAJOR

    # A conference's tier is the median of its members' margins, so it follows
    # the teams through realignment rather than following a name.
    membership = (
        long[["team_id", "conference_id"]]
        .drop_duplicates()
        .groupby("conference_id")["team_id"]
        .apply(list)
        .to_dict()
    )
    conference_margin = {
        conference: float(
            pd.Series([team_margin[t] for t in teams if t in team_margin]).median()
        )
        for conference, teams in membership.items()
        if any(t in team_margin for t in teams)
    }
    conference_tier = {c: _tier(m) for c, m in conference_margin.items()}

    # The team takes its conference's tier — the unit Cooper wants reported —
    # unless it has too little evidence to be placed at all.
    team_conference = (
        long[["team_id", "conference_id"]].drop_duplicates().set_index("team_id")["conference_id"].to_dict()
    )
    team_tier = {}
    for team, row in per_team.iterrows():
        if int(row["games"]) < MINIMUM_GAMES:
            team_tier[team] = Tier.UNPLACED
            continue
        conference = team_conference.get(team)
        team_tier[team] = conference_tier.get(conference, _tier(float(row["margin"])))

    return TierTable(
        team_tier=team_tier,
        conference_tier=conference_tier,
        team_margin=team_margin,
        conference_margin=conference_margin,
        seasons=tuple(seasons),
    )
