"""Which games count, which teams are Division I, and where a game was played.

Three exclusions, each of which fails closed. Cooper's rule for all of them:
**excluded is counted and stated, never silently dropped**, and an excluded
game is never reported as a pass, an avoid, or a no-value call.

## 1. Non-Division-I opponents

Measured on the completed 2025-26 season: **551 of 6,318 games have a side that
is not D-I**, and **541 of those 551 (98%) are in November and December**. These
are the buy-games — a low-major hosting a D-II or NAIA school for a guaranteed
win — and they are exactly what Cooper predicted. They have no comparable data
on the other side: no ratings, no schedule, no opponents in common.

They are never fitted on, never carded, and never in the ledger. They are
counted and stated.

The membership test is `home_conference_id` and `away_conference_id` both being
present in the schedule feed. Measured: 365 team ids carry one across 31
conferences, and 363 do not. **The one false negative this test can produce is
a genuine D-I independent**, which would also read as conference-less — so the
D-I universe is cross-checked against ESPN's conference walk, and a team
missing from both is excluded rather than guessed at.

**Do not use ESPN's `/teams?groups=50` endpoint as the universe.** It returns
362 and silently omits three genuine D-I programmes — Queens, Lindenwood and
Southern Indiana, all recent D-II reclassifications, each of which reports
`isActive: true` under group 50 when asked individually. The conference walk
returns 365 and is the one that agrees with the NCAA's own count.

## 2. Venue state, which has three values and not two

A game mislabelled neutral is a multi-point error applied to every market on
it, so "neutral" is not a boolean here.

Measured on 2025-26: of **709 games flagged `neutral_site`, 39 (5.5%) are in a
participant's own home city** and **7 are in a participant's own arena** —
Vanderbilt hosting the SEC tournament in Nashville, Yale and Cornell in Ithaca,
Houston in Houston for a Sweet 16. Those are not neutral and they are not
ordinary home games either. They get their own state, :data:`QUASI_NEUTRAL`,
and the model fits an effect for it rather than assuming one.

An unknown or contradictory venue status **quarantines the game** rather than
defaulting to neutral. Defaulting is the failure that looks like nothing.

## 3. Exhibitions and closed scrimmages

The feed does not carry these at all: a preseason exhibition against a D-II
school is either absent or arrives as a non-D-I game and is caught by the first
exclusion. The guard is still explicit, because "the feed happens not to carry
them" is a fact that can change and "we excluded them" is a claim this lab
makes.

## What abstaining costs, and why it is still right

Cooper: *"Abstain rather than nuke a real slate."* A guard that quarantines a
whole night because one venue string was unfamiliar has done more damage than
the error it prevented. So each guard is per game, the counts are printed every
run, and the accounting identity reconciles them — a game that vanishes without
appearing in a count is a defect, not a decision.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import pandas as pd


class GameState(str, Enum):
    """Why a game is or is not in the population."""

    #: Division I against Division I, played, countable.
    COUNTABLE = "countable"
    #: One side is not Division I. The November buy-game.
    NON_DI_OPPONENT = "non_di_opponent"
    #: An exhibition or closed scrimmage.
    EXHIBITION = "exhibition"
    #: Called off. More common in this sport than in the NHL or NFL.
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    #: Scheduled but not yet played. Cardable, not fittable.
    SCHEDULED = "scheduled"
    #: Something the classifier could not read. Quarantined, never guessed.
    UNKNOWN = "unknown"


class VenueState(str, Enum):
    """Where a game was played, in three states rather than two."""

    HOME = "home"
    NEUTRAL = "neutral"
    #: Flagged neutral, played in a participant's own city or arena. A
    #: conference tournament at home, or a multi-team event forty miles from
    #: campus. Measured at 5.5% of flagged-neutral games.
    QUASI_NEUTRAL = "quasi_neutral"
    #: Contradictory or missing. Quarantined rather than defaulted.
    UNKNOWN = "unknown"


#: ESPN status strings, mapped. Anything not here is UNKNOWN, deliberately.
_STATUS_STATES = {
    "STATUS_FINAL": GameState.COUNTABLE,
    "STATUS_SCHEDULED": GameState.SCHEDULED,
    "STATUS_POSTPONED": GameState.POSTPONED,
    "STATUS_CANCELED": GameState.CANCELLED,
    "STATUS_CANCELLED": GameState.CANCELLED,
}

#: Headline fragments that mark a game as not countable. The feed does not
#: currently carry exhibitions, so this is a guard against a change upstream
#: rather than a filter that fires today — and it is asserted by a test that
#: fails if it ever starts matching a large share of the season.
_EXHIBITION_MARKERS = ("exhibition", "scrimmage", "charity exhibition")


@dataclass(frozen=True)
class PopulationCounts:
    """The accounting identity for a season's games. Printed every run."""

    total: int = 0
    by_state: dict[str, int] = field(default_factory=dict)
    by_venue: dict[str, int] = field(default_factory=dict)

    def reconciles(self) -> bool:
        return sum(self.by_state.values()) == self.total

    def summary_line(self) -> str:
        parts = ", ".join(
            f"{state}={count:,}" for state, count in sorted(self.by_state.items())
        )
        venues = ", ".join(
            f"{state}={count:,}" for state, count in sorted(self.by_venue.items())
        )
        ok = "reconciles" if self.reconciles() else "DOES NOT RECONCILE"
        return f"{self.total:,} games: {parts} ({ok}). Venue: {venues}."


def division_one_team_ids(schedule: pd.DataFrame) -> set:
    """Every team id the feed gives a conference to, on either side.

    The conference id is the membership marker: measured on 2025-26, 365 team
    ids carry one and 363 do not, against an NCAA count of 365 D-I programmes.
    """
    ids: set = set()
    for side in ("home", "away"):
        column, conference = f"{side}_id", f"{side}_conference_id"
        if column not in schedule or conference not in schedule:
            continue
        present = schedule.loc[schedule[conference].notna(), column]
        ids.update(present.dropna().tolist())
    return ids


def home_venues(schedule: pd.DataFrame) -> pd.DataFrame:
    """Each team's usual home venue, from its own non-neutral home games.

    Derived rather than looked up, because no free feed publishes a
    team-to-arena table and a derived one is checkable against the games it was
    derived from.
    """
    columns = ["home_id", "venue_id", "venue_address_city", "venue_address_state"]
    if not set(columns) <= set(schedule.columns):
        return pd.DataFrame(columns=columns).set_index("home_id")
    at_home = schedule.loc[~schedule["neutral_site"].astype(bool), columns]
    if at_home.empty:
        return pd.DataFrame(columns=columns).set_index("home_id")

    def _mode(series: pd.Series):
        modes = series.dropna().mode()
        return modes.iloc[0] if len(modes) else None

    return at_home.groupby("home_id").agg(_mode)


def classify_venue(row, venues: pd.DataFrame) -> VenueState:
    """`home`, `neutral`, `quasi_neutral`, or `unknown`.

    `unknown` quarantines. A game whose venue status is missing or
    contradictory is not assumed neutral, because assuming neutral is a
    multi-point error applied to every market on the game and it looks like
    nothing when it happens.
    """
    flag = row.get("neutral_site") if hasattr(row, "get") else getattr(row, "neutral_site", None)
    if flag is None or (isinstance(flag, float) and flag != flag):
        return VenueState.UNKNOWN
    if not bool(flag):
        return VenueState.HOME

    def _field(name):
        return row.get(name) if hasattr(row, "get") else getattr(row, name, None)

    venue_id = _field("venue_id")
    city = _field("venue_address_city")
    state = _field("venue_address_state")
    if venue_id is None and city is None:
        # Flagged neutral with no venue at all: it may be genuinely neutral or
        # it may be a feed gap, and the two are not distinguishable here.
        return VenueState.UNKNOWN

    for side in ("home_id", "away_id"):
        team = _field(side)
        if team is None or team not in venues.index:
            continue
        usual = venues.loc[team]
        if venue_id is not None and usual.get("venue_id") == venue_id:
            return VenueState.QUASI_NEUTRAL
        if (
            city is not None
            and usual.get("venue_address_city") == city
            and usual.get("venue_address_state") == state
        ):
            return VenueState.QUASI_NEUTRAL
    return VenueState.NEUTRAL


def classify_game(row, di_ids: set) -> GameState:
    """Why this game is or is not in the population."""

    def _field(name):
        return row.get(name) if hasattr(row, "get") else getattr(row, name, None)

    headline = str(_field("notes_headline") or "").casefold()
    if any(marker in headline for marker in _EXHIBITION_MARKERS):
        return GameState.EXHIBITION

    home, away = _field("home_id"), _field("away_id")
    if home is None or away is None:
        return GameState.UNKNOWN
    if home not in di_ids or away not in di_ids:
        return GameState.NON_DI_OPPONENT

    status = str(_field("status_type_name") or "")
    return _STATUS_STATES.get(status, GameState.UNKNOWN)


def classify(schedule: pd.DataFrame) -> pd.DataFrame:
    """Add `game_state` and `venue_state` to a schedule frame."""
    di_ids = division_one_team_ids(schedule)
    venues = home_venues(schedule)
    out = schedule.copy()
    out["game_state"] = [
        classify_game(row, di_ids).value for row in out.to_dict("records")
    ]
    out["venue_state"] = [
        classify_venue(row, venues).value for row in out.to_dict("records")
    ]
    return out


def count(classified: pd.DataFrame) -> PopulationCounts:
    return PopulationCounts(
        total=int(len(classified)),
        by_state=classified["game_state"].value_counts().to_dict(),
        by_venue=classified["venue_state"].value_counts().to_dict(),
    )


def fittable(classified: pd.DataFrame) -> pd.DataFrame:
    """The games a model may be fitted on: D-I against D-I, played, venue known.

    Deliberately stricter than `cardable`. A game this lab cannot place in a
    venue state is a game whose home effect is unknown, and fitting on it puts
    that unknown into every price the model makes afterwards.
    """
    return classified[
        (classified["game_state"] == GameState.COUNTABLE.value)
        & (classified["venue_state"] != VenueState.UNKNOWN.value)
    ]


def cardable(classified: pd.DataFrame) -> pd.DataFrame:
    """The games the card may price: D-I against D-I, scheduled or played.

    A venue state of `unknown` is excluded here too — a game the lab cannot
    place is a game it cannot price honestly — but the exclusion is per game
    and is counted, so an unfamiliar venue string quarantines one game rather
    than nuking a slate.
    """
    return classified[
        classified["game_state"].isin(
            {GameState.COUNTABLE.value, GameState.SCHEDULED.value}
        )
        & (classified["venue_state"] != VenueState.UNKNOWN.value)
    ]
