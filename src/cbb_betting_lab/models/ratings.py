"""Adjusted efficiency, tempo and the venue effect — fitted, walk-forward.

`distributions.build` takes three numbers and knows nothing about teams, dates
or seasons. **This module is where those three numbers come from**, and it is
also where every reason not to produce them lives. It answers four questions,
and the last two matter more than the first two:

1. how good are these two teams per possession, and how many possessions will
   the game have;
2. what does this venue add, given that "neutral" in this sport has three
   values and not two;
3. **how much of that answer is still the preseason prior**, carried as a field
   on every rating and every matchup so a November number can never be printed
   as if it were a February one;
4. **whether the schedule graph has connected these two teams by anything but
   that prior at all** — and if it has not, this module refuses to price the
   game. An unpriced game is an honest output; a confidently priced one built
   on no connecting evidence is not.

## Possessions, not points, and the estimator rather than the count

Every quantity here is per 100 possessions or in possessions per forty minutes.
The possession count is `possessions_estimated` from `data/build_datasets.py`
— `FGA - OREB + TOV + 0.475·FTA` — and **never** the play-by-play transition
count, deliberately.

`data/outputs/cbb_possession_validation.json` is the reason. Across seven
seasons the estimator sits 1.7 to 2.7 possessions under the counted number, and
in 2026 the gap jumps to **6.5**, coinciding exactly with ESPN quadrupling its
substitution reporting. Seven stable seasons and one discontinuity is a feed
artifact, not a change in basketball, and a model fitted on the count would
carry a step change in tempo into every total it priced from 2026 onward. The
estimator is stable, so the estimator is what is fitted.

A game's possessions are the **mean of the two teams' estimates**, because
basketball's possessions alternate: pace is a property of the game and the two
per-team figures differ only by estimator noise. `distributions.build` takes one
shared count for exactly the same reason.

## Overtime is not fitted on, because the distribution adds it back

`distributions.build` produces regulation and then cascades overtime onto the
level mass itself. Feeding it a points-per-possession fitted on final scores
would count overtime twice — 5.8% of games times about 20 points is over a
point on every total in the sport, in one direction, all season.

So **the fit uses games that ended in regulation**: 78,944 of 86,596 fittable
team-games (91.2%). 4,856 went to overtime and 2,766 have no play-by-play and
therefore no period count, and a missing period count is not evidence of a
regulation finish. Both groups are excluded and counted, never silently
dropped.

That exclusion conditions on the outcome, which is worth saying out loud: it
removes exactly the games that were level after forty minutes. It biases the
*margin* distribution, which this module does not produce, and leaves an
additive team effect essentially untouched. `fit_report()` prints the league
efficiency and tempo with and without the excluded games so the size of the
conditioning is visible rather than argued about.

## The November prior, and the weight it is carried with

Cooper's rule: *"A rating built only on this season's games is uninformative
until roughly December… report the prior's weight in every price so the card
can never present a November number as if it were a February one."*

The prior is a real forecast, fitted from three things and honest about the
fourth:

* **last season's adjusted rating**, carried forward by a **measured**
  coefficient. Pooled over 2,124 team-season pairs, offence carries at 0.637
  and defence at 0.601 — so roughly forty per cent of a team is new every
  November before anybody counts a roster;
* **returning minutes.** Measured rather than quoted: the share of a team's
  previous-season minutes played by athletes back on its roster has fallen from
  **40.7% (2019-20) to 25.3% (2025-26)**, and the share of minutes played by
  athletes who were at another school last season has risen from **3.7% to
  20.0%** over the same window. The transfer portal is not a modifier here, it
  is the main term;
* **incoming transfers' production at their prior school, adjusted for level.**
  Minutes brought in are worth more when they come from a stronger programme,
  and the level gap is measured against the prior school's own fitted rating
  rather than a name;
* **recruiting is not in it, and cannot be.** No free source in
  `docs/cbb_data_sources.md` publishes a recruiting ranking this lab may use,
  and a rating that quietly depended on a scraped one would be someone else's
  number with our name on it. It is a named absence, not an omission.

Fitted on 2020-2025 season pairs with **2026 held out**, the roster terms cut
the season-ahead prediction error from 3.243 to 3.083 points per 100 on offence
and from 2.959 to 2.829 on defence — on a season nothing here was fitted to.
On **tempo they do nothing at all**: 1.4684 against 1.4680, a 0.03% change, so
they are not applied to tempo and this module says so rather than applying them
everywhere and calling it a model. Tempo is a coaching property; the personnel
term was tested, measured at nothing, and left out.

### The weight is exact, not a rule of thumb

The fit is a ridge whose penalty centre is the prior — which is precisely a
normal prior updated by the games played so far. So the prior's share of a
rating is not estimated, it is read off the solution:

    posterior = A⁻¹X'y + A⁻¹Λp,        A = X'X + Λ

and the second term is the prior's contribution. `prior_weight` is the row sum
of `A⁻¹Λ`: the fraction of the rating that would move if the whole prior moved
by one. It is 1.0 for a team that has not played, and it falls as that team's
own games arrive. Λ is not chosen either — it is `σ²_observation / σ²_prior`,
both measured, which is the ridge that a Bayesian posterior actually implies.

A matchup carries the **largest** prior weight among the six parameters that
enter its price, not the average. A price is only as data-driven as its
worst-identified input, and averaging is how a brand-new team hides behind a
well-known opponent.

## Connectivity, and the refusal

Cooper: *"Graph connectivity is an identifiability problem, not a nuisance."*

The diagnostic is the **effective resistance** between the two teams on the
graph of games played so far, because that is not a metaphor for
identifiability, it *is* it: under a paired-comparison model with no prior, the
variance of the estimated rating **difference** between two teams is
proportional to the effective resistance between them. It is infinite when they
are in different components, large when one thin chain of results connects them,
and small once the schedule has genuinely tied them together.

The cut point is declared in advance and has an arithmetic reading rather than
a taste: :data:`MAX_EFFECTIVE_RESISTANCE` = 1.0 is exactly the connecting
evidence of **one head-to-head meeting**, and also exactly that of **two
independent common opponents** (two paths of length two in parallel). Below it
the matchup is priced; at or above it, it is refused.

Measured over the 2025-26 season, the refusal bites hard and then stops:

    day       games   components   median resistance   share priced
    Nov 5       128          128            1.000            0.2%
    Nov 10      311           47            7.000            0.3%
    Nov 15      509            1            1.746            1.8%
    Nov 20      731            1            0.767           86.5%
    Nov 25      967            1            0.502           99.9%
    Dec 1     1,245            1            0.358          100.0%

The middle row is the whole argument for this measure over a component count.
**On 15 November the graph is already a single connected component** — a naive
"are they connected" test passes every pair — and the median resistance is still
1.75, which is to say most pairs are joined by about half a common opponent's
worth of evidence. Components stop refusing five days before the evidence
arrives.

Connectivity and prior weight are different instruments and both are needed. On
25 November every pair clears the resistance bar and the typical rating is still
three quarters prior. Connectivity says *whether the difference is identified at
all*; prior weight says *how much of it is last season's news*. Neither
substitutes for the other, and the card prints both.

## Home advantage is fitted, and it is not one number

Fitted, never assumed, and the measurement is not a detail. Per 100 possessions
of margin, from a fit with team effects on either side, by the **tier of the
home team**:

    season   league   high-major   mid-major   low-major
    2022      +6.21      +10.52       +6.55       +3.51
    2023      +7.27      +11.41       +7.12       +5.10
    2024      +8.08      +12.63       +7.43       +3.27
    2025      +7.50      +13.32       +6.90       +3.90
    2026      +7.48      +12.91       +7.58       +3.87

A high-major home court is worth **three to four times** a low-major one — about
8.8 points a game against 2.6 at 68 possessions. One league-wide constant is
roughly three and a half points wrong in each direction, on every market on the
game, all season. That is the measurement that makes `HIGH_MAJOR` / `MID_MAJOR`
/ `LOW_MAJOR` a modelling distinction rather than a reporting one.

**2021 is the cross-check, and it was not designed as one.** The season played
in empty arenas measures the smallest home advantage in the window (+4.99
league, +8.69 high-major) and the gradient compresses with it. A tier effect
that shrinks when the crowds are removed is behaving like a crowd effect.

Underneath the tier, each venue gets its own shrunk departure. Across 418
venues and 34,816 home-state games the between-venue standard deviation is
**2.05 points per 100 per side — 4.10 in margin, about 2.8 points a game** —
against a within-venue variance of 70.1, so the shrinkage constant is
`κ = 16.7` home games and a venue with fifty of them keeps three quarters of its
own departure.

**What that number cannot separate is stated rather than glossed:** a venue in
this sport hosts one team, so "this arena is worth more than the tier says" and
"this team is better at home than its rating says" are the same column. The
effect is fitted and reported as a *team-venue* effect for that reason, and
whether it ships is decided by the price backtest through the
`venue_home_effect` verdict — which is pre-registered in the experiment ledger
as *"fitted venue-level home effect: ROI exceeds one league-wide constant"*.
With no verdict recorded, the tier effect is what prices and the venue
departures are computed, reported and not applied. A missing verdict ships
nothing.

### `quasi_neutral` is a third state and it is nearly neutral

Of 197 quasi-neutral games in eight seasons the local participant is the
**nominal away team in 64 of them (32.5%)** — the ESPN home flag is on the wrong
team a third of the time, so the local side is derived from
`population.home_venues` rather than taken from the designation.

Fitted with the local side correct, the quasi-neutral margin effect pools to
**−0.90 per 100 possessions, 95% interval −3.32 to +1.52 over 348 team-games** —
an interval that includes zero, which this lab reports as **no demonstrated
edge**. The finding is not that quasi-neutral is worth something; it is that it
is worth nothing like a home game. Treating those games as home would apply
+7.5 per 100 — five points — that the data does not support, on every market on
the game. That is CLAUDE.md's *"multi-point error applied to every market on
it"*, measured.

## Walk-forward, structurally

`fit()` takes `as_of` and **raises** if a single history row is dated on or
after it. `price_backtest.walk_forward` supplies history strictly earlier than
the day it is pricing; this module refuses to be handed anything else, so the
guard holds whoever calls it. Every `Ratings` carries `priced_through`, which is
the stamp `price_backtest.assert_walk_forward` reads.

The seam has three levels and each looks at a different window, all of them in
the past:

* **team ratings** — the current season's games, strictly before `as_of`. A
  team is not the team it was last March;
* **the prior and the structural coefficients** — completed seasons strictly
  before the priced one, prepared once by `prepare_prior`. The home effect is a
  slow league property and re-deriving it nightly from a part-season adds noise
  and no information;
* **conference tiers** — `conferences.tier_table` on seasons strictly before,
  which is that module's own rule.

`tests/test_fit_ratings.py::test_corrupting_every_game_after_a_cut_leaves_the_
earlier_fits_identical` corrupts every game after a cut date and asserts the
fit is unchanged to the last bit, which is the test `docs/ported_defects.md`
names against the football lab's defect 13. (This used to cite a
`tests/test_ratings_are_walk_forward.py` that never existed.)

## What this module does not do

It does not decide anything. The card reads `priceable`, `prior_weight` and the
three numbers; the price backtest decides whether any of it is worth money.
Calibration can rule a model out and never in, and nothing here is evidence of
an edge.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

from cbb_betting_lab import config, verdicts
from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.conferences import Tier, TierTable, tier_table
from cbb_betting_lab.data.build_datasets import REGULATION_PERIODS
from cbb_betting_lab.models import distributions
from cbb_betting_lab.population import GameState, VenueState, classify, home_venues
from cbb_betting_lab.season import clean_text, season_for_slate_date


# --------------------------------------------------------------------------
# Declared before anything was fitted. Every number carries its sample size in
# the module docstring; none of them is tuned to make a market look better.
# --------------------------------------------------------------------------

#: A game whose two teams' estimated possession counts average below this did
#: not happen the way the box score says. Sixteen such team-games exist in
#: eight seasons and every one of them is a truncated box score.
MINIMUM_GAME_POSSESSIONS = 40.0

#: Efficiency is per this many possessions, everywhere in this module.
POSSESSION_SCALE = 100.0

#: **The refusal.** Effective resistance on the games-played graph, above which
#: the two teams are not connected by enough to identify their difference and
#: the matchup is not priced.
#:
#: 1.0 is not a taste. A single head-to-head meeting is exactly 1.0; two
#: independent common opponents (two length-2 paths in parallel) are also
#: exactly 1.0. So the bar reads: *these two teams must be joined by at least
#: as much evidence as one meeting between them.* Measured on 2025-26 it
#: refuses essentially the whole board before 20 November and essentially
#: nothing after 25 November — see the module docstring's table.
MAX_EFFECTIVE_RESISTANCE = 1.0

#: Eigenvalues of a graph Laplacian below this times the largest are the null
#: space — one dimension per connected component — and are dropped when the
#: pseudo-inverse is formed.
LAPLACIAN_TOLERANCE = 1e-10

#: Shrinkage for a single venue's departure from its tier's home effect, in
#: home games. Measured: within-venue variance 70.1 against a between-venue
#: variance of 4.20 over 418 venues and 34,816 home-state games, so
#: κ = 70.1 / 4.20 = 16.7 and a venue with fifty home games in the window keeps
#: 50/(50+16.7) = 75% of its own departure. Re-measured by `prepare_prior`
#: whenever the window supports it; this is the fallback and the record.
DECLARED_VENUE_SHRINKAGE = 16.7

#: Ridge on a tier's departure from the league home effect, in team-games. The
#: tier gradient is large and well-measured (see the docstring's table), so this
#: is deliberately light — it exists to stop `UNPLACED`, which is a handful of
#: teams a season, from acquiring a home effect of its own on forty games.
TIER_HOME_EFFECT_SHRINKAGE = 50.0

#: Fallback prior strengths, in games, used only when there is no earlier
#: season to measure them from. `σ²_observation / σ²_prior`, both measured:
#: offence 13.08² / 3.083², defence 13.08² / 2.829², tempo 4.118² / 1.468²,
#: with the prior spreads taken from the **held-out** 2026 season rather than
#: from the seasons the carryover was fitted on. An in-sample prior spread
#: would overstate λ and hand the prior more weight than it has earned, which
#: One pseudo-observation of "no effect" on each venue column, so the design is
#: well-posed even when a season supplies no game of some venue kind. See the
#: block comment in `_season_fit`; this is a numerical guard, not a prior with
#: an opinion, and at 1.0 against thousands of rows it moves an estimable
#: effect in the fourth decimal place.
VENUE_RIDGE = 1.0

#: is the one direction this number must not be wrong in.
DECLARED_PRIOR_STRENGTH: dict[str, float] = {
    "offence": 18.0,
    "defence": 21.4,
    "tempo": 7.9,
}

#: Fallback season-to-season carryover, per component, when there is no earlier
#: pair of seasons to fit it on. Measured over 2,124 team-season pairs.
DECLARED_CARRYOVER: dict[str, float] = {
    "offence": 0.637,
    "defence": 0.601,
    "tempo": 0.605,
}

#: The components a rating has. Named once so a loop cannot disagree with a
#: dataclass field.
OFFENCE, DEFENCE, TEMPO = "offence", "defence", "tempo"
COMPONENTS: tuple[str, ...] = (OFFENCE, DEFENCE, TEMPO)

#: A tier with no previous-season evidence is priced with the **mid-major**
#: prior and reported separately — `conferences.Tier.UNPLACED`'s own docstring
#: says so, and this is where that sentence is honoured rather than repeated.
UNPLACED_PRIOR_TIER = Tier.MID_MAJOR

#: The roster terms are applied to efficiency and **not** to tempo. Measured on
#: held-out 2026: they cut offence's season-ahead error by 4.9% and defence's by
#: 4.4%, and tempo's by 0.03% — which is nothing. A term applied where it was
#: measured at nothing is decoration.
ROSTER_TERMS_APPLY_TO: frozenset[str] = frozenset({OFFENCE, DEFENCE})

#: How many earlier seasons the prior and the structural coefficients may read.
#: Three: enough that a venue has forty-odd home games in the window, few enough
#: that a programme five years ago is not evidence about this one.
PRIOR_WINDOW_SEASONS = 3


class RatingsError(RuntimeError):
    """A rating could not be produced, or was asked for dishonestly."""


class WalkForwardViolation(RatingsError):
    """History reaching the day being priced, or past it.

    Raised rather than filtered. Silently dropping the offending rows would
    make a leak look like a clean fit, and the football lab's defect 13 was
    invisible for exactly that reason — the code path looked right.
    """


# --------------------------------------------------------------------------
# Preparing the fittable frame
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class PreparedGames:
    """Team-game rows a rating may be fitted on, and what was dropped to get them.

    The counts are the accounting identity for the fit, in the same spirit as
    `population.PopulationCounts`: a row that vanished without appearing in a
    count is a defect, not a decision.
    """

    rows: pd.DataFrame
    #: Rows in, rows out, and every reason in between.
    supplied: int = 0
    not_countable: int = 0
    venue_unknown: int = 0
    overtime: int = 0
    periods_unknown: int = 0
    too_few_possessions: int = 0
    #: Quasi-neutral rows whose local participant could not be identified
    #: because no schedule was supplied. They are fitted as neutral, which the
    #: measurement says is close to right, and they are counted here so that
    #: "close to right" is a number rather than a claim.
    quasi_local_side_unknown: int = 0
    has_venue_ids: bool = False

    def reconciles(self) -> bool:
        return self.supplied == (
            len(self.rows)
            + self.not_countable
            + self.venue_unknown
            + self.overtime
            + self.periods_unknown
            + self.too_few_possessions
        )

    def summary_line(self) -> str:
        ok = "reconciles" if self.reconciles() else "DOES NOT RECONCILE"
        return (
            f"{len(self.rows):,} fittable team-games of {self.supplied:,} "
            f"supplied ({ok}): not countable {self.not_countable:,}, venue "
            f"unknown {self.venue_unknown:,}, overtime {self.overtime:,}, "
            f"period count missing {self.periods_unknown:,}, possessions below "
            f"{MINIMUM_GAME_POSSESSIONS:.0f} {self.too_few_possessions:,}."
        )



#: `local_teams` and `venue_ids` are pure functions of the schedules and are
#: called once per slate day by `prepare`. Measured on the real tables:
#: `local_teams` is **3.01 seconds** of `prepare`'s 3.09, and across ~600
#: walk-forward days that is **an hour of identical work**. A backtest that
#: takes two hours instead of ten minutes is not merely slow — the weekly loop
#: runs it unattended, so the cost is paid every week for ever.
#:
#: Keyed on the seasons rather than on the frames, because within a process the
#: schedule frame for a season is the same cached object every time and a key
#: built from frame contents would cost more than the call it saves.
_LOCAL_TEAMS_CACHE: dict[tuple, dict] = {}
_VENUE_IDS_CACHE: dict[tuple, dict] = {}


def _schedule_key(schedules: Mapping[int, "pd.DataFrame"]) -> tuple:
    """A key that identifies the FRAMES, not merely the seasons they cover.

    **The first version of this keyed on season numbers alone and was wrong.**
    A caller supplying a synthetic 2026 schedule — which every card test does —
    got back the cached answer for the *real* 2026 schedule, so quasi-neutral
    games resolved to the wrong local side, venues misclassified, and the card
    froze zero opinions. It failed in isolation, not through cross-test
    pollution, which is the tell that the key itself was the defect rather than
    the ordering.

    `id()` is safe here only because the cache value keeps a reference to the
    frames it was built from, so the ids cannot be recycled underneath it. The
    row count is carried as a cheap second opinion.
    """
    return tuple(
        (int(season), id(frame), len(frame))
        for season, frame in sorted(schedules.items())
    )


def _local_teams_uncached(schedules: Mapping[int, pd.DataFrame]) -> dict:
    """`game_id -> the participant playing in its own city or arena`, or None.

    For an ordinary home game that is the home team by definition. For a
    quasi-neutral one it is **derived**, using the same `home_venues` table
    `population.classify_venue` classifies with, because the designation cannot
    be trusted: of 197 quasi-neutral games in eight seasons the local side is
    the nominal **away** team in 64 (32.5%), and nine have both participants
    local — a city with two D-I programmes in it — where the effect cancels and
    the answer is correctly None.
    """
    out: dict = {}
    for schedule in schedules.values():
        if schedule is None or schedule.empty:
            continue
        classified = classify(schedule)
        venues = home_venues(schedule)
        for row in classified.to_dict("records"):
            state = row.get("venue_state")
            if state == VenueState.HOME.value:
                out[row.get("id")] = row.get("home_id")
                continue
            if state != VenueState.QUASI_NEUTRAL.value:
                continue
            local = [
                row.get(side)
                for side in ("home_id", "away_id")
                if _is_local(row, row.get(side), venues)
            ]
            out[row.get("id")] = local[0] if len(local) == 1 else None
    return out


def _is_local(row: Mapping, team, venues: pd.DataFrame) -> bool:
    """Is this participant playing in its own arena, or at least its own city?"""
    if team is None or team not in venues.index:
        return False
    usual = venues.loc[team]
    if row.get("venue_id") is not None and usual.get("venue_id") == row.get("venue_id"):
        return True
    return bool(
        usual.get("venue_address_city") == row.get("venue_address_city")
        and usual.get("venue_address_state") == row.get("venue_address_state")
    )


def _venue_ids_uncached(schedules: Mapping[int, pd.DataFrame]) -> dict:
    """`game_id -> venue_id`. The team-game table does not carry it."""
    out: dict = {}
    for schedule in schedules.values():
        if schedule is None or schedule.empty:
            continue
        if "id" in schedule.columns and "venue_id" in schedule.columns:
            out.update(dict(zip(schedule["id"], schedule["venue_id"])))
    return out


def prepare(
    team_games: pd.DataFrame,
    *,
    schedules: Mapping[int, pd.DataFrame] | None = None,
) -> PreparedGames:
    """The team-game rows a rating may be fitted on, with everything derived.

    Adds `game_possessions` (the mean of the two sides' estimates, because pace
    is a property of the game), `efficiency` in points per 100, and the local
    side. Drops nothing silently: every exclusion is a field on the result.

    `schedules` is optional and buys two things — the venue id, without which
    there is no venue-level effect, and the derived local side for quasi-neutral
    games, without which a third of them would put the effect on the wrong team.
    """
    supplied = int(len(team_games))
    if supplied == 0:
        return PreparedGames(rows=team_games.copy(), supplied=0)

    frame = team_games.copy()
    countable = frame["game_state"].astype(str) == GameState.COUNTABLE.value
    not_countable = int((~countable).sum())
    frame = frame[countable]

    known_venue = frame["venue_state"].astype(str) != VenueState.UNKNOWN.value
    venue_unknown = int((~known_venue).sum())
    frame = frame[known_venue]

    # Overtime is excluded because `distributions.build` appends it itself, and
    # a missing period count is not evidence of a regulation finish.
    periods = pd.to_numeric(frame.get("periods"), errors="coerce")
    periods_unknown = int(periods.isna().sum())
    overtime = int((periods > REGULATION_PERIODS).sum())
    frame = frame[periods == REGULATION_PERIODS]

    possessions = pd.to_numeric(frame["possessions_estimated"], errors="coerce")
    frame = frame.assign(possessions_estimated=possessions)
    game_possessions = frame.groupby("game_id")["possessions_estimated"].transform("mean")
    frame = frame.assign(game_possessions=game_possessions)
    enough = frame["game_possessions"] >= MINIMUM_GAME_POSSESSIONS
    too_few = int((~enough).sum())
    frame = frame[enough]

    frame = frame.assign(
        efficiency=POSSESSION_SCALE
        * pd.to_numeric(frame["team_score"], errors="coerce")
        / frame["game_possessions"],
        slate_date=frame["slate_date"].astype(str),
    )

    is_home_side = frame["home_away"].astype(str).str.lower() == "home"
    at_home_venue = frame["venue_state"].astype(str) == VenueState.HOME.value
    local = pd.Series(pd.NA, index=frame.index, dtype="object")
    local[at_home_venue & is_home_side] = frame.loc[at_home_venue & is_home_side, "team_id"]
    local[at_home_venue & ~is_home_side] = frame.loc[
        at_home_venue & ~is_home_side, "opponent_id"
    ]

    quasi = frame["venue_state"].astype(str) == VenueState.QUASI_NEUTRAL.value
    quasi_unknown = int(quasi.sum())
    has_venues = False
    if schedules:
        derived = local_teams(schedules)
        mapped = frame.loc[quasi, "game_id"].map(derived)
        local[quasi] = mapped
        quasi_unknown = int(mapped.isna().sum())
        ids = venue_ids(schedules)
        if ids:
            frame = frame.assign(venue_id=frame["game_id"].map(ids))
            has_venues = True
    if "venue_id" not in frame.columns:
        frame = frame.assign(venue_id=pd.NA)

    frame = frame.assign(
        local_team_id=local,
        is_local=local.notna() & (local == frame["team_id"]),
        opponent_is_local=local.notna() & (local == frame["opponent_id"]),
    )

    return PreparedGames(
        rows=frame,
        supplied=supplied,
        not_countable=not_countable,
        venue_unknown=venue_unknown,
        overtime=overtime,
        periods_unknown=periods_unknown,
        too_few_possessions=too_few,
        quasi_local_side_unknown=quasi_unknown,
        has_venue_ids=has_venues,
    )


# --------------------------------------------------------------------------
# Connectivity: the identifiability diagnostic that refuses
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Connectivity:
    """The games-played graph, and how well any two teams are joined on it.

    `resistance` is the effective resistance matrix — the variance of the
    estimated rating **difference** up to a constant, under a paired-comparison
    model with no prior. `numpy.inf` between components, because two teams with
    no chain of results between them have no identified difference at all and a
    large finite number would understate that.
    """

    index: dict
    component_of: dict
    component_sizes: dict
    resistance: np.ndarray
    games: int
    #: Algebraic connectivity of the largest component. Zero when the graph is
    #: disconnected; larger as the schedule ties the board together.
    fiedler_value: float = 0.0

    @property
    def teams(self) -> int:
        return len(self.index)

    @property
    def components(self) -> int:
        return len(self.component_sizes)

    def resistance_between(self, a, b) -> float:
        """`inf` for an unknown team, an unplayed team, or a different component."""
        if a == b:
            return 0.0
        i, j = self.index.get(a), self.index.get(b)
        if i is None or j is None:
            return float("inf")
        if self.component_of.get(a) != self.component_of.get(b):
            return float("inf")
        return float(self.resistance[i, j])

    def connects(self, a, b) -> tuple[bool, str]:
        """Whether these two teams are joined by enough to identify a price.

        Returns the answer **and the sentence the card prints when it is no**,
        together, so that a refusal can never reach a reader without its reason.
        """
        if a == b:
            return False, "a team cannot play itself"
        for team in (a, b):
            if team not in self.index:
                return (
                    False,
                    f"team {team} has played no countable game this season, so "
                    "its rating is the preseason prior and nothing else",
                )
        if self.component_of.get(a) != self.component_of.get(b):
            return (
                False,
                "the two teams are in different components of the games-played "
                f"graph ({self.components} components over {self.teams} teams, "
                f"{self.games:,} games) — no chain of results connects them and "
                "any difference between their ratings is the prior's opinion",
            )
        resistance = self.resistance_between(a, b)
        if not np.isfinite(resistance) or resistance >= MAX_EFFECTIVE_RESISTANCE:
            return (
                False,
                f"the effective resistance between them is {resistance:.2f} "
                f"against a bar of {MAX_EFFECTIVE_RESISTANCE:.2f} — less "
                "connecting evidence than a single head-to-head meeting, or "
                "than two common opponents",
            )
        return True, ""

    def summary_line(self) -> str:
        largest = max(self.component_sizes.values()) if self.component_sizes else 0
        return (
            f"{self.games:,} games over {self.teams} teams: {self.components} "
            f"component(s), largest {largest}, algebraic connectivity "
            f"{self.fiedler_value:.4f}."
        )

    def resistance_quantiles(
        self, quantiles: Sequence[float] = (0.1, 0.5, 0.9)
    ) -> dict[float, float]:
        """Resistance across same-component pairs. `inf` pairs are not in it —
        they are counted by `priceable_share` instead."""
        if self.teams < 2:
            return {q: float("inf") for q in quantiles}
        upper = np.triu_indices(self.teams, 1)
        labels = np.array([self.component_of[t] for t in self.index])
        same = (labels[:, None] == labels[None, :])[upper]
        values = self.resistance[upper][same]
        if values.size == 0:
            return {q: float("inf") for q in quantiles}
        return {q: float(np.quantile(values, q)) for q in quantiles}

    def priceable_share(self) -> float:
        """The share of **all** team pairs this graph would let a card price."""
        if self.teams < 2:
            return 0.0
        upper = np.triu_indices(self.teams, 1)
        labels = np.array([self.component_of[t] for t in self.index])
        same = (labels[:, None] == labels[None, :])[upper]
        values = self.resistance[upper]
        return float(np.mean(same & (values < MAX_EFFECTIVE_RESISTANCE)))


def connectivity(history: pd.DataFrame) -> Connectivity:
    """The games-played graph and its effective resistances.

    One symmetric eigendecomposition of the Laplacian, which is cheap at this
    size (365 teams) and gives the algebraic connectivity for free. The
    pseudo-inverse of a block-diagonal Laplacian is the block diagonal of the
    blocks' pseudo-inverses, so within-component resistances read correctly off
    the whole-graph decomposition; across components they are set to infinity
    explicitly rather than left as the finite nonsense the arithmetic produces.
    """
    if history is None or history.empty:
        return Connectivity({}, {}, {}, np.zeros((0, 0)), 0)
    pairs = (
        history[["game_id", "team_id", "opponent_id"]]
        .drop_duplicates("game_id")
        .dropna()
    )
    teams = sorted(set(pairs["team_id"]) | set(pairs["opponent_id"]), key=repr)
    index = {team: i for i, team in enumerate(teams)}
    size = len(teams)
    laplacian = np.zeros((size, size))
    for a, b in zip(pairs["team_id"], pairs["opponent_id"]):
        i, j = index[a], index[b]
        if i == j:
            continue
        laplacian[i, j] -= 1.0
        laplacian[j, i] -= 1.0
        laplacian[i, i] += 1.0
        laplacian[j, j] += 1.0

    # Components by union-find rather than by reading them off the spectrum: a
    # near-zero eigenvalue and a zero one are the same thing to floating point,
    # and the difference between them is exactly the refusal this class makes.
    parent = list(range(size))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in zip(pairs["team_id"], pairs["opponent_id"]):
        ra, rb = find(index[a]), find(index[b])
        if ra != rb:
            parent[ra] = rb
    component_of = {team: find(i) for team, i in index.items()}
    sizes: dict = {}
    for label in component_of.values():
        sizes[label] = sizes.get(label, 0) + 1

    values, vectors = np.linalg.eigh(laplacian)
    cutoff = LAPLACIAN_TOLERANCE * max(float(values.max()), 1.0)
    keep = values > cutoff
    inverse = np.zeros_like(values)
    inverse[keep] = 1.0 / values[keep]
    pseudo = (vectors * inverse) @ vectors.T
    diagonal = np.diag(pseudo)
    resistance = diagonal[:, None] + diagonal[None, :] - 2.0 * pseudo
    np.fill_diagonal(resistance, 0.0)
    resistance = np.maximum(resistance, 0.0)

    fiedler = float(values[keep].min()) if keep.any() else 0.0
    return Connectivity(
        index=index,
        component_of=component_of,
        component_sizes=sizes,
        resistance=resistance,
        games=int(len(pairs)),
        fiedler_value=fiedler,
    )


# --------------------------------------------------------------------------
# The preseason prior
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class RosterEvidence:
    """Who is on a team this season, known only from games already played.

    The brief asks for a prior built from returning minutes, incoming
    transfers' production at their prior school adjusted for level, and
    recruiting. The first two are here; recruiting is not obtainable from any
    source this lab may use and is a **named absence** in the module docstring
    rather than a silent one.

    The walk-forward rule bites hardest here. A roster is public in October and
    this lab can only see it through games, so `share_as_of` reads only players
    who have already appeared. Before a team's first game it knows nothing, the
    roster terms contribute exactly zero, and the prior falls back to last
    season's rating carried forward — which is the honest answer, not a
    degraded one.
    """

    #: One row per (team_id, athlete_id) seen this season: `first_slate_date`,
    #: `previous_minutes`, `previous_team_id`, `previous_team_rating`.
    appearances: pd.DataFrame
    #: Previous-season minutes by team, the denominator for both shares.
    previous_minutes_by_team: dict
    #: Previous-season net rating by team, for the level adjustment.
    previous_net_rating: dict
    season: int = 0

    def share_as_of(self, day: str) -> pd.DataFrame:
        """Returning-minutes share, incoming-minutes share and the level gap.

        One row per team that has played, indexed by `team_id`. A team absent
        from the result has not played and gets no roster terms at all.
        """
        empty = pd.DataFrame(
            columns=["returning", "incoming", "incoming_level"]
        ).rename_axis("team_id")
        if self.appearances.empty:
            return empty
        seen = self.appearances[
            self.appearances["first_slate_date"].astype(str) < str(day)
        ]
        if seen.empty:
            return empty
        rows = []
        for team, group in seen.groupby("team_id"):
            total = float(self.previous_minutes_by_team.get(team, 0.0))
            if total <= 0:
                continue
            returning = group[group["previous_team_id"] == team]["previous_minutes"].sum()
            incoming = group[
                group["previous_team_id"].notna() & (group["previous_team_id"] != team)
            ]
            incoming_minutes = float(incoming["previous_minutes"].sum())
            own = float(self.previous_net_rating.get(team, np.nan))
            level = 0.0
            if incoming_minutes > 0 and np.isfinite(own):
                rated = incoming[incoming["previous_team_rating"].notna()]
                if not rated.empty and rated["previous_minutes"].sum() > 0:
                    level = (
                        float(
                            np.average(
                                rated["previous_team_rating"].to_numpy(dtype=float),
                                weights=np.maximum(
                                    rated["previous_minutes"].to_numpy(dtype=float), 1e-9
                                ),
                            )
                        )
                        - own
                    )
            rows.append(
                {
                    "team_id": team,
                    "returning": float(returning) / total,
                    "incoming": incoming_minutes / total,
                    "incoming_level": level,
                }
            )
        if not rows:
            return empty
        return pd.DataFrame(rows).set_index("team_id")


@dataclass(frozen=True)
class CarryoverFit:
    """One component's season-to-season forecast, and how wrong it is.

    `residual_sd` is measured **out of sample** wherever there is more than one
    pair of seasons to do it with — the coefficients are fitted leaving the most
    recent pair out and scored on it. An in-sample residual understates the
    prior's error, which overstates λ, which hands the prior more weight than it
    has earned. That is the one direction this number must not be wrong in.
    """

    component: str
    carryover: float
    returning: float = 0.0
    incoming: float = 0.0
    incoming_level: float = 0.0
    residual_sd: float = 0.0
    observation_sd: float = 0.0
    pairs: int = 0
    uses_roster: bool = False
    out_of_sample: bool = False

    @property
    def strength(self) -> float:
        """λ, in games: `σ²_observation / σ²_prior`. Not chosen — implied."""
        if self.residual_sd <= 0 or self.observation_sd <= 0:
            return float(DECLARED_PRIOR_STRENGTH[self.component])
        return float(self.observation_sd**2 / self.residual_sd**2)

    def summary_line(self) -> str:
        how = "out-of-sample" if self.out_of_sample else "in-sample"
        roster = "with roster terms" if self.uses_roster else "carryover only"
        return (
            f"{self.component}: carryover {self.carryover:.3f}, {roster}, "
            f"prior sd {self.residual_sd:.3f} ({how}), observation sd "
            f"{self.observation_sd:.3f} -> lambda {self.strength:.1f} games, "
            f"{self.pairs:,} team-season pairs."
        )


@dataclass(frozen=True)
class TeamPrior:
    """One team's preseason rating, in departures from the league mean."""

    team_id: object
    offence: float
    defence: float
    tempo: float
    tier: str
    source: str


@dataclass(frozen=True)
class VenueEffects:
    """The fitted venue structure: league, tier, and each venue's own departure.

    Every effect is in points per 100 possessions **on one side's efficiency**.
    A home team's offence gets `+home_offence` and the visitor's gets
    `home_defence` (which is measured negative), so the margin effect is the
    difference of the two — which is why they are stored apart rather than as
    one number. Whether home advantage is scored or prevented is a measurable
    question and this lab does not assume the answer.
    """

    league_home_offence: float = 0.0
    league_home_defence: float = 0.0
    tier_home_offence: dict[str, float] = field(default_factory=dict)
    tier_home_defence: dict[str, float] = field(default_factory=dict)
    quasi_offence: float = 0.0
    quasi_defence: float = 0.0
    venue_departure: dict = field(default_factory=dict)
    venue_games: dict = field(default_factory=dict)
    shrinkage: float = DECLARED_VENUE_SHRINKAGE
    between_sd: float = 0.0
    within_sd: float = 0.0
    seasons: tuple[int, ...] = ()
    team_games: int = 0
    source: str = "declared"

    def home_margin(self, tier: str) -> float:
        """This tier's home advantage in points per 100 possessions of margin."""
        return self.home_offence(tier) - self.home_defence(tier)

    def home_offence(self, tier: str) -> float:
        return self.league_home_offence + self.tier_home_offence.get(str(tier), 0.0)

    def home_defence(self, tier: str) -> float:
        return self.league_home_defence + self.tier_home_defence.get(str(tier), 0.0)

    def departure_for(self, venue_id) -> float:
        """This venue's own shrunk departure, per side. Zero when unknown."""
        if venue_id is None or (isinstance(venue_id, float) and venue_id != venue_id):
            return 0.0
        return float(self.venue_departure.get(venue_id, 0.0))

    def summary_line(self) -> str:
        tiers = ", ".join(
            f"{tier}={self.home_margin(tier):+.2f}"
            for tier in sorted(set(self.tier_home_offence) | set(self.tier_home_defence))
        )
        return (
            f"Home advantage per 100 possessions of margin: league "
            f"{self.home_margin('__none__'):+.2f}"
            + (f" ({tiers})" if tiers else "")
            + f". Quasi-neutral {self.quasi_offence - self.quasi_defence:+.2f}. "
            f"{len(self.venue_departure)} venues, between-venue sd "
            f"{self.between_sd:.2f} per side, shrinkage {self.shrinkage:.1f} "
            f"home games. Fitted on {self.team_games:,} team-games from seasons "
            f"{list(self.seasons)}."
        )


@dataclass(frozen=True)
class Prior:
    """Everything a season's fit inherits from the seasons before it.

    Prepared once per season, never inside the daily loop, and built from
    seasons **strictly earlier** than the one being priced. The only part that
    moves during the season is the roster evidence, and it moves because roster
    information genuinely arrives — a player who has appeared has appeared.
    """

    season: int
    league_efficiency: float
    league_tempo: float
    league_efficiency_strength: float
    league_tempo_strength: float
    team: dict = field(default_factory=dict)
    fits: dict = field(default_factory=dict)
    venue: VenueEffects = field(default_factory=VenueEffects)
    tiers: TierTable | None = None
    roster: RosterEvidence | None = None
    seasons_used: tuple[int, ...] = ()
    #: Departures by tier, so a team with no previous season inherits its
    #: tier's mean rather than the league's.
    tier_offence: dict = field(default_factory=dict)
    tier_defence: dict = field(default_factory=dict)
    tier_tempo: dict = field(default_factory=dict)

    def strength(self, component: str) -> float:
        fit = self.fits.get(component)
        return fit.strength if fit is not None else DECLARED_PRIOR_STRENGTH[component]

    def tier_of(self, team_id) -> str:
        if self.tiers is None:
            return Tier.UNPLACED.value
        return self.tiers.tier_for(team_id).value

    def summary_line(self) -> str:
        return (
            f"Prior for season {self.season} from seasons "
            f"{list(self.seasons_used)}: {len(self.team)} teams, league "
            f"{self.league_efficiency:.2f} per 100 at {self.league_tempo:.2f} "
            "possessions. "
            + " ".join(
                self.fits[c].summary_line() for c in COMPONENTS if c in self.fits
            )
        )


# --------------------------------------------------------------------------
# Fitting one season's structure from the seasons before it
# --------------------------------------------------------------------------


def _season_fit(
    rows: pd.DataFrame, *, strength: dict[str, float]
) -> tuple[dict, dict, dict, float, float, float]:
    """A single completed season's ratings, shrunk toward the league mean.

    Deliberately simple and prior-free: this is what the *next* season's prior
    is built from, and a prior built from a prior is a chain nobody can audit.
    Venue effects are carried as free parameters so that a team playing more
    home games than away does not bank the difference as skill.
    """
    teams = sorted(set(rows["team_id"]) | set(rows["opponent_id"]), key=repr)
    index = {team: i for i, team in enumerate(teams)}
    size = len(teams)
    count = len(rows)
    if size == 0 or count == 0:
        return {}, {}, {}, 0.0, 0.0, 0.0

    league_efficiency = float(rows["efficiency"].mean())
    columns = 2 * size + 4
    design = np.zeros((count, columns))
    order = np.arange(count)
    design[order, rows["team_id"].map(index).to_numpy()] = 1.0
    design[order, rows["opponent_id"].map(index).to_numpy() + size] = 1.0
    at_home = (rows["venue_state"].astype(str) == VenueState.HOME.value).to_numpy()
    quasi = (rows["venue_state"].astype(str) == VenueState.QUASI_NEUTRAL.value).to_numpy()
    local = rows["is_local"].to_numpy(dtype=bool)
    opponent_local = rows["opponent_is_local"].to_numpy(dtype=bool)
    design[:, 2 * size + 0] = at_home & local
    design[:, 2 * size + 1] = at_home & opponent_local
    design[:, 2 * size + 2] = quasi & local
    design[:, 2 * size + 3] = quasi & opponent_local

    penalty = np.zeros(columns)
    penalty[:size] = strength[OFFENCE]
    penalty[size : 2 * size] = strength[DEFENCE]
    # THE FOUR VENUE COLUMNS ARE PENALISED TOO, AND THE REASON IS NOT TASTE.
    # Left at zero they are the only unregularised columns in the design, so a
    # season in which one of them is structurally empty — no quasi-neutral game
    # carrying a local team, say — makes the normal matrix singular and
    # `np.linalg.solve` raise. That is not a hypothetical: it happened on
    # 2019, 2020 and 2021 simultaneously, and the fit worked on 2022 only
    # because those seasons had 18 such rows and the others had none.
    #
    # A ridge of one pseudo-observation is negligible against the ~4,400 real
    # rows that populate a venue column when the effect is estimable, and it
    # makes an inestimable effect come back as exactly **zero** — which is the
    # honest answer to "what is the quasi-neutral home effect in a season with
    # no quasi-neutral games?" — rather than as an exception.
    penalty[2 * size :] = VENUE_RIDGE
    response = rows["efficiency"].to_numpy(dtype=float) - league_efficiency
    normal = design.T @ design + np.diag(penalty)
    coefficients = np.linalg.solve(normal, design.T @ response)
    residual = response - design @ coefficients
    observation_sd = float(np.std(residual, ddof=1)) if count > 1 else 0.0

    offence = {team: float(coefficients[i]) for team, i in index.items()}
    defence = {team: float(coefficients[i + size]) for team, i in index.items()}

    games = rows.drop_duplicates("game_id")
    league_tempo = float(games["game_possessions"].mean())
    tempo_design = np.zeros((len(games), size))
    tempo_order = np.arange(len(games))
    np.add.at(tempo_design, (tempo_order, games["team_id"].map(index).to_numpy()), 1.0)
    np.add.at(
        tempo_design, (tempo_order, games["opponent_id"].map(index).to_numpy()), 1.0
    )
    tempo_response = games["game_possessions"].to_numpy(dtype=float) - league_tempo
    tempo_normal = tempo_design.T @ tempo_design + np.eye(size) * strength[TEMPO]
    tempo_coefficients = np.linalg.solve(tempo_normal, tempo_design.T @ tempo_response)
    tempo = {team: float(tempo_coefficients[i]) for team, i in index.items()}
    tempo_residual = tempo_response - tempo_design @ tempo_coefficients
    tempo_sd = float(np.std(tempo_residual, ddof=1)) if len(games) > 1 else 0.0

    return offence, defence, tempo, league_efficiency, league_tempo, observation_sd, tempo_sd  # type: ignore[return-value]


def _carryover(
    pairs: pd.DataFrame,
    component: str,
    *,
    observation_sd: float,
    use_roster: bool,
) -> CarryoverFit:
    """Fit `this season ~ last season (+ roster evidence)` for one component.

    Held out by season wherever there is more than one to hold out, because the
    number this produces is the prior's standard deviation and an optimistic one
    is the difference between a November price that says it is mostly prior and
    one that says it is mostly evidence.
    """
    usable = pairs.dropna(subset=["previous", "current"])
    if len(usable) < 8:
        return CarryoverFit(
            component=component,
            carryover=DECLARED_CARRYOVER[component],
            observation_sd=observation_sd,
            pairs=int(len(usable)),
        )

    roster_columns = ["returning", "incoming", "incoming_level_product"]
    has_roster = use_roster and set(roster_columns) <= set(usable.columns)

    def design_for(frame: pd.DataFrame, returning_mean: float) -> np.ndarray:
        block = [frame["previous"].to_numpy(dtype=float)]
        if has_roster:
            block.append(frame["returning"].to_numpy(dtype=float) - returning_mean)
            block.append(frame["incoming"].to_numpy(dtype=float))
            block.append(frame["incoming_level_product"].to_numpy(dtype=float))
        return np.column_stack(block)

    seasons = sorted(usable["season"].unique())
    returning_mean = (
        float(usable["returning"].mean()) if has_roster else 0.0
    )
    out_of_sample = False
    residual_sd = 0.0
    if len(seasons) >= 2:
        latest = seasons[-1]
        train = usable[usable["season"] != latest]
        test = usable[usable["season"] == latest]
        if len(train) >= 8 and len(test) >= 8:
            fitted, *_ = np.linalg.lstsq(
                design_for(train, returning_mean),
                train["current"].to_numpy(dtype=float),
                rcond=None,
            )
            held = test["current"].to_numpy(dtype=float) - design_for(
                test, returning_mean
            ) @ fitted
            residual_sd = float(np.std(held, ddof=1))
            out_of_sample = True

    coefficients, *_ = np.linalg.lstsq(
        design_for(usable, returning_mean),
        usable["current"].to_numpy(dtype=float),
        rcond=None,
    )
    if not out_of_sample:
        residual = usable["current"].to_numpy(dtype=float) - design_for(
            usable, returning_mean
        ) @ coefficients
        residual_sd = float(np.std(residual, ddof=1))

    return CarryoverFit(
        component=component,
        carryover=float(coefficients[0]),
        returning=float(coefficients[1]) if has_roster else 0.0,
        incoming=float(coefficients[2]) if has_roster else 0.0,
        incoming_level=float(coefficients[3]) if has_roster else 0.0,
        residual_sd=residual_sd,
        observation_sd=observation_sd,
        pairs=int(len(usable)),
        uses_roster=has_roster,
        out_of_sample=out_of_sample,
    )


def _venue_effects(
    rows: pd.DataFrame,
    season_ratings: Mapping[int, dict],
    tiers: TierTable | None,
    *,
    seasons: tuple[int, ...],
) -> VenueEffects:
    """Home and quasi-neutral effects: league, per tier, and per venue.

    Fitted on completed seasons and held fixed through the season being priced.
    A home-court effect is a slow league property; re-deriving it every night
    from a part-season adds noise and no information, and in November it would
    be fitted on a few hundred games and would swamp the ratings it corrects.

    The per-venue departures are computed from the residuals of the tier fit and
    shrunk by `n/(n+κ)` with κ measured from the variance decomposition rather
    than chosen. When the decomposition finds no between-venue variance at all,
    κ is infinite, every venue takes its tier's effect, and that is a result
    rather than a failure.
    """
    if rows.empty:
        return VenueEffects(seasons=seasons)

    tier_values = tuple(t.value for t in Tier)
    frames = []
    residuals = []
    for season, group in rows.groupby("season"):
        ratings = season_ratings.get(int(season))
        if not ratings:
            continue
        offence, defence, _tempo, league, *_ = ratings
        predicted = (
            group["team_id"].map(offence).fillna(0.0).to_numpy(dtype=float)
            + group["opponent_id"].map(defence).fillna(0.0).to_numpy(dtype=float)
        )
        frames.append(group)
        residuals.append(
            group["efficiency"].to_numpy(dtype=float) - league - predicted
        )
    if not frames:
        return VenueEffects(seasons=seasons)
    frame = pd.concat(frames)
    response = np.concatenate(residuals)

    at_home = (frame["venue_state"].astype(str) == VenueState.HOME.value).to_numpy()
    quasi = (
        frame["venue_state"].astype(str) == VenueState.QUASI_NEUTRAL.value
    ).to_numpy()
    local = frame["is_local"].to_numpy(dtype=bool)
    opponent_local = frame["opponent_is_local"].to_numpy(dtype=bool)
    home_offence = (at_home & local).astype(float)
    home_defence = (at_home & opponent_local).astype(float)

    def tier_of(team) -> str:
        if tiers is None or team is None or (isinstance(team, float) and team != team):
            return Tier.UNPLACED.value
        return tiers.tier_for(team).value

    local_tier = frame["local_team_id"].map(tier_of).to_numpy()
    blocks = [home_offence, home_defence]
    for tier in tier_values:
        blocks.append(home_offence * (local_tier == tier))
    for tier in tier_values:
        blocks.append(home_defence * (local_tier == tier))
    blocks.append((quasi & local).astype(float))
    blocks.append((quasi & opponent_local).astype(float))
    design = np.column_stack(blocks)

    penalty = np.zeros(design.shape[1])
    penalty[2 : 2 + 2 * len(tier_values)] = TIER_HOME_EFFECT_SHRINKAGE
    normal = design.T @ design + np.diag(penalty)
    coefficients = np.linalg.solve(normal, design.T @ response)
    remainder = response - design @ coefficients

    tier_offence = {
        tier: float(coefficients[2 + i]) for i, tier in enumerate(tier_values)
    }
    tier_defence = {
        tier: float(coefficients[2 + len(tier_values) + i])
        for i, tier in enumerate(tier_values)
    }

    # Per-venue departures, from the margin left over at each venue. Halved,
    # because a departure of `d` in margin is `+d/2` to the home side and
    # `-d/2` to the visitor.
    departures: dict = {}
    games: dict = {}
    within = between = 0.0
    shrinkage = DECLARED_VENUE_SHRINKAGE
    if "venue_id" in frame.columns:
        left = pd.DataFrame(
            {
                "game_id": frame["game_id"].to_numpy(),
                "venue_id": frame["venue_id"].to_numpy(),
                "is_local": local,
                "at_home": at_home,
                "remainder": remainder,
            }
        )
        left = left[left["at_home"] & left["venue_id"].notna()]
        if not left.empty:
            pivot = left.pivot_table(
                index=["game_id", "venue_id"], columns="is_local", values="remainder"
            ).dropna()
            if not pivot.empty and True in pivot.columns and False in pivot.columns:
                margin = (pivot[True] - pivot[False]) / 2.0
                by_venue = margin.groupby(level="venue_id")
                counts = by_venue.size()
                means = by_venue.mean()
                variances = by_venue.var(ddof=1)
                usable = counts[counts >= 5].index
                if len(usable) >= 2:
                    weights = counts.loc[usable].to_numpy(dtype=float)
                    within_values = variances.loc[usable].fillna(0.0).to_numpy(float)
                    within = float(np.average(within_values, weights=weights))
                    harmonic = float(len(usable) / np.sum(1.0 / weights))
                    observed = float(np.var(means.loc[usable].to_numpy(float), ddof=1))
                    between = max(observed - within / harmonic, 0.0)
                    shrinkage = (
                        within / between if between > 0 else float("inf")
                    )
                    for venue, count in counts.items():
                        weight = (
                            0.0
                            if not np.isfinite(shrinkage)
                            else count / (count + shrinkage)
                        )
                        departures[venue] = float(weight * means.loc[venue] / 1.0)
                        games[venue] = int(count)

    return VenueEffects(
        league_home_offence=float(coefficients[0]),
        league_home_defence=float(coefficients[1]),
        tier_home_offence=tier_offence,
        tier_home_defence=tier_defence,
        quasi_offence=float(coefficients[-2]),
        quasi_defence=float(coefficients[-1]),
        venue_departure=departures,
        venue_games=games,
        shrinkage=shrinkage,
        between_sd=float(np.sqrt(between)),
        within_sd=float(np.sqrt(within)),
        seasons=seasons,
        team_games=int(len(frame)),
        source="fitted",
    )


def build_roster_evidence(
    player_games: pd.DataFrame,
    *,
    season: int,
    previous_net_rating: Mapping,
) -> RosterEvidence:
    """Returning and incoming minutes for one season, dated by first appearance.

    Every row records the day the athlete **first appeared** for this team, so
    `share_as_of` can answer the walk-forward question — who was known to be on
    this roster before that morning — rather than the retrospective one.

    `did_not_play` rows are excluded, which is not optional: 69,344 of 196,876
    player rows in the 2026 file are did-not-play rows with null minutes, and a
    share computed over them is a third too low with nothing about it looking
    wrong.
    """
    empty = pd.DataFrame(
        columns=[
            "team_id",
            "athlete_id",
            "first_slate_date",
            "previous_minutes",
            "previous_team_id",
            "previous_team_rating",
        ]
    )
    if player_games is None or player_games.empty:
        return RosterEvidence(empty, {}, dict(previous_net_rating), season)

    frame = player_games.copy()
    frame = frame[~frame["did_not_play"].fillna(False).astype(bool)]
    frame["minutes"] = pd.to_numeric(frame["minutes"], errors="coerce").fillna(0.0)
    frame["season"] = pd.to_numeric(frame["season"], errors="coerce")

    previous = frame[frame["season"] == season - 1]
    current = frame[frame["season"] == season]
    if previous.empty or current.empty:
        return RosterEvidence(empty, {}, dict(previous_net_rating), season)

    by_athlete = previous.groupby(["athlete_id", "team_id"])["minutes"].sum()
    minutes_by_athlete = by_athlete.groupby(level="athlete_id").sum().to_dict()
    # A player who moved mid-season is attributed to the team he played most
    # for, which is the only defensible single answer and is stated rather
    # than hidden in a `first()`.
    dominant = (
        by_athlete.reset_index()
        .sort_values("minutes")
        .drop_duplicates("athlete_id", keep="last")
        .set_index("athlete_id")["team_id"]
        .to_dict()
    )
    minutes_by_team = previous.groupby("team_id")["minutes"].sum().to_dict()

    appearances = (
        current[current["minutes"] > 0]
        .groupby(["team_id", "athlete_id"])["slate_date"]
        .min()
        .reset_index()
        .rename(columns={"slate_date": "first_slate_date"})
    )
    appearances["first_slate_date"] = appearances["first_slate_date"].astype(str)
    appearances["previous_minutes"] = appearances["athlete_id"].map(minutes_by_athlete)
    appearances["previous_minutes"] = appearances["previous_minutes"].fillna(0.0)
    appearances["previous_team_id"] = appearances["athlete_id"].map(dominant)
    appearances["previous_team_rating"] = appearances["previous_team_id"].map(
        dict(previous_net_rating)
    )
    return RosterEvidence(
        appearances=appearances,
        previous_minutes_by_team=minutes_by_team,
        previous_net_rating=dict(previous_net_rating),
        season=int(season),
    )


def prepare_prior(
    prepared: PreparedGames,
    *,
    season: int,
    tiers: TierTable | None = None,
    schedules: Mapping[int, pd.DataFrame] | None = None,
    player_games: pd.DataFrame | None = None,
    window: int = PRIOR_WINDOW_SEASONS,
) -> Prior:
    """Everything season `season` inherits, from seasons strictly before it.

    Called **once per season**, never inside the day loop. It fits each earlier
    season on its own, fits the season-to-season carryover across those fits,
    fits the venue structure across them, and turns the last completed season
    into a per-team prior mean.

    `prepared` may hold every season this lab has cached; only those strictly
    earlier than `season` and inside `window` are read, and the ones that were
    available are recorded on the result.
    """
    rows = prepared.rows
    if rows.empty:
        return Prior(
            season=season,
            league_efficiency=0.0,
            league_tempo=0.0,
            league_efficiency_strength=0.0,
            league_tempo_strength=0.0,
        )
    seasons = tuple(
        sorted(
            s
            for s in {int(x) for x in rows["season"].dropna().unique()}
            if season - window <= s < season
        )
    )
    if not seasons:
        return Prior(
            season=season,
            league_efficiency=float(rows["efficiency"].mean()),
            league_tempo=float(
                rows.drop_duplicates("game_id")["game_possessions"].mean()
            ),
            league_efficiency_strength=0.0,
            league_tempo_strength=0.0,
            tiers=tiers,
        )

    strength = dict(DECLARED_PRIOR_STRENGTH)
    fitted: dict[int, tuple] = {}
    for one in seasons:
        subset = rows[rows["season"] == one]
        if subset.empty:
            continue
        fitted[one] = _season_fit(subset, strength=strength)

    latest = max(fitted) if fitted else None
    if latest is None:
        return Prior(
            season=season,
            league_efficiency=float(rows["efficiency"].mean()),
            league_tempo=float(
                rows.drop_duplicates("game_id")["game_possessions"].mean()
            ),
            league_efficiency_strength=0.0,
            league_tempo_strength=0.0,
            tiers=tiers,
            seasons_used=seasons,
        )

    offence, defence, tempo, league_efficiency, league_tempo, observation_sd, tempo_sd = (
        fitted[latest]
    )
    net = {team: offence.get(team, 0.0) - defence.get(team, 0.0) for team in offence}

    roster = None
    if player_games is not None and not player_games.empty:
        roster = build_roster_evidence(
            player_games, season=season, previous_net_rating=net
        )

    # The season-to-season model, fitted on consecutive pairs among the fitted
    # seasons. Roster evidence for those pairs is retrospective — the pairs are
    # complete seasons in the past — which is legitimate: what may not be used
    # is information from after the game being priced, and every one of these
    # seasons ended before this one started.
    observation = {
        OFFENCE: observation_sd,
        DEFENCE: observation_sd,
        TEMPO: tempo_sd,
    }
    fits: dict[str, CarryoverFit] = {}
    for component, getter in (
        (OFFENCE, 0),
        (DEFENCE, 1),
        (TEMPO, 2),
    ):
        pairs = _pair_frame(fitted, getter, player_games, component)
        fits[component] = _carryover(
            pairs,
            component,
            observation_sd=observation[component],
            use_roster=component in ROSTER_TERMS_APPLY_TO,
        )

    if tiers is None and schedules:
        tiers = tier_table(dict(schedules), seasons)

    def tier_of(team) -> str:
        if tiers is None:
            return Tier.UNPLACED.value
        return tiers.tier_for(team).value

    tier_means: dict[str, dict[str, float]] = {}
    for component, values in ((OFFENCE, offence), (DEFENCE, defence), (TEMPO, tempo)):
        buckets: dict[str, list[float]] = {}
        for team, value in values.items():
            buckets.setdefault(tier_of(team), []).append(float(value))
        tier_means[component] = {
            tier: float(np.mean(v)) for tier, v in buckets.items() if v
        }

    priors: dict = {}
    for team in sorted(set(offence) | set(defence) | set(tempo), key=repr):
        tier = tier_of(team)
        priors[team] = TeamPrior(
            team_id=team,
            offence=fits[OFFENCE].carryover * float(offence.get(team, 0.0)),
            defence=fits[DEFENCE].carryover * float(defence.get(team, 0.0)),
            tempo=fits[TEMPO].carryover * float(tempo.get(team, 0.0)),
            tier=tier,
            source=f"season {latest} carried forward",
        )

    # The league mean itself is a forecast: efficiency has drifted from 103.3 to
    # 108.5 per 100 across eight seasons, which is far more than a season's
    # sampling error, so the previous season's level is a prior and not a fact.
    league_strength, tempo_strength = _league_strengths(fitted, observation_sd, tempo_sd)

    venue = _venue_effects(
        rows[rows["season"].isin(seasons)],
        fitted,
        tiers,
        seasons=seasons,
    )

    return Prior(
        season=season,
        league_efficiency=league_efficiency,
        league_tempo=league_tempo,
        league_efficiency_strength=league_strength,
        league_tempo_strength=tempo_strength,
        team=priors,
        fits=fits,
        venue=venue,
        tiers=tiers,
        roster=roster,
        seasons_used=seasons,
        tier_offence=tier_means[OFFENCE],
        tier_defence=tier_means[DEFENCE],
        tier_tempo=tier_means[TEMPO],
    )


def _pair_frame(
    fitted: Mapping[int, tuple],
    component_index: int,
    player_games: pd.DataFrame | None,
    component: str,
) -> pd.DataFrame:
    """`(previous, current)` per team over consecutive fitted seasons."""
    rows = []
    seasons = sorted(fitted)
    for season in seasons:
        if season - 1 not in fitted:
            continue
        before = fitted[season - 1][component_index]
        after = fitted[season][component_index]
        shared = sorted(set(before) & set(after), key=repr)
        if not shared:
            continue
        previous_values = np.array([before[t] for t in shared], dtype=float)
        current_values = np.array([after[t] for t in shared], dtype=float)
        block = pd.DataFrame(
            {
                "season": season,
                "team_id": shared,
                "previous": previous_values - previous_values.mean(),
                "current": current_values - current_values.mean(),
            }
        )
        if player_games is not None and component in ROSTER_TERMS_APPLY_TO:
            net = {
                t: fitted[season - 1][0].get(t, 0.0) - fitted[season - 1][1].get(t, 0.0)
                for t in fitted[season - 1][0]
            }
            evidence = build_roster_evidence(
                player_games, season=season, previous_net_rating=net
            )
            shares = evidence.share_as_of("9999-12-31")
            block = block.join(shares, on="team_id")
            block["returning"] = block["returning"].fillna(0.0)
            block["incoming"] = block["incoming"].fillna(0.0)
            block["incoming_level"] = block["incoming_level"].fillna(0.0)
            block["incoming_level_product"] = block["incoming"] * block["incoming_level"]
        rows.append(block)
    if not rows:
        return pd.DataFrame(columns=["season", "team_id", "previous", "current"])
    return pd.concat(rows, ignore_index=True)


def _league_strengths(
    fitted: Mapping[int, tuple], observation_sd: float, tempo_sd: float
) -> tuple[float, float]:
    """How many games of this season it takes to outweigh last season's level.

    `σ²_observation / σ²_drift`, with the drift measured across the fitted
    seasons' league means. With one season there is no drift to measure and the
    answer is zero — the current season's own mean is used from the first game,
    which is right, because with no earlier season there is nothing else.
    """
    seasons = sorted(fitted)
    if len(seasons) < 3:
        return 0.0, 0.0
    efficiency = np.array([fitted[s][3] for s in seasons], dtype=float)
    tempo = np.array([fitted[s][4] for s in seasons], dtype=float)
    drift_efficiency = float(np.std(np.diff(efficiency), ddof=1))
    drift_tempo = float(np.std(np.diff(tempo), ddof=1))
    league = observation_sd**2 / drift_efficiency**2 if drift_efficiency > 0 else 0.0
    pace = tempo_sd**2 / drift_tempo**2 if drift_tempo > 0 else 0.0
    return float(league), float(pace)


# --------------------------------------------------------------------------
# The fit itself
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Ratings:
    """One walk-forward fit: three numbers a team, and what they are made of."""

    season: int
    #: The slate day these ratings were built to price. Nothing dated on or
    #: after it was read.
    as_of: str
    #: The latest game day the fit actually saw. `price_backtest`'s stamp.
    priced_through: str
    games: int
    team_games: int
    league_efficiency: float
    league_tempo: float
    offence: dict = field(default_factory=dict)
    defence: dict = field(default_factory=dict)
    tempo: dict = field(default_factory=dict)
    prior_weight: dict = field(default_factory=dict)
    prior: Prior | None = None
    venue: VenueEffects = field(default_factory=VenueEffects)
    graph: Connectivity = field(default_factory=lambda: Connectivity({}, {}, {}, np.zeros((0, 0)), 0))
    residual_sd: float = 0.0
    venue_level_home_effect: bool = False
    venue_effect_note: str = ""

    # -- reading one team --------------------------------------------------

    def tier_of(self, team_id) -> str:
        if self.prior is None:
            return Tier.UNPLACED.value
        return self.prior.tier_of(team_id)

    def offensive_efficiency(self, team_id) -> float:
        """Points per 100 possessions against an average defence, neutral floor."""
        return self.league_efficiency + float(self.offence.get(team_id, 0.0))

    def defensive_efficiency(self, team_id) -> float:
        """Points per 100 allowed to an average offence, neutral floor."""
        return self.league_efficiency + float(self.defence.get(team_id, 0.0))

    def expected_tempo(self, home_team_id, away_team_id) -> float:
        return (
            self.league_tempo
            + float(self.tempo.get(home_team_id, 0.0))
            + float(self.tempo.get(away_team_id, 0.0))
        )

    def prior_weight_for(self, team_id, component: str) -> float:
        return float(self.prior_weight.get((component, team_id), 1.0))

    def prior_weight_distribution(
        self, quantiles: Sequence[float] = (0.1, 0.25, 0.5, 0.75, 0.9)
    ) -> dict[str, dict[float, float]]:
        """Per component, so a thin tempo fit cannot hide behind a thick one."""
        out: dict[str, dict[float, float]] = {}
        for component in COMPONENTS:
            values = [
                value
                for (name, _team), value in self.prior_weight.items()
                if name == component
            ]
            out[component] = (
                {q: float(np.quantile(values, q)) for q in quantiles}
                if values
                else {q: 1.0 for q in quantiles}
            )
        return out

    def summary_line(self) -> str:
        median = self.prior_weight_distribution((0.5,))
        parts = ", ".join(
            f"{c} {median[c][0.5]:.0%}" for c in COMPONENTS
        )
        return (
            f"Season {self.season} as of {self.as_of} (priced through "
            f"{self.priced_through or 'nothing'}): {self.games:,} games, "
            f"{len(self.offence)} teams, league {self.league_efficiency:.2f} per "
            f"100 at {self.league_tempo:.2f} possessions, residual sd "
            f"{self.residual_sd:.2f}. Median prior weight: {parts}. "
            + self.graph.summary_line()
        )


def fit(
    history: pd.DataFrame,
    *,
    prior: Prior,
    as_of: str,
    season: int | None = None,
    venue_level_home_effect: bool | None = None,
    competition: Competition = CBB,
    output_dir: Path | None = None,
) -> Ratings:
    """Adjusted offence, defence and tempo from games strictly before `as_of`.

    `history` is `prepare(...).rows` filtered to the season being priced. The
    guard is structural: a single row dated on or after `as_of` raises, because
    a fit that quietly filtered its own leak away would look exactly like a
    clean one — which is what the football lab's defect 13 looked like for a
    whole build.

    The ridge penalty centre is the prior, so this is a normal prior updated by
    the games played so far and `prior_weight` is that posterior's own arithmetic
    rather than a rule of thumb. λ per component is `σ²_observation / σ²_prior`,
    measured by `prepare_prior`.

    `venue_level_home_effect` decides whether each venue's own shrunk departure
    is applied on top of its tier's effect. Left as None it is read from the
    recorded `venue_home_effect` verdict, and **a missing verdict ships
    nothing** — the tier effect prices and the departures are reported. The
    comparison the verdict records is pre-registered in the experiment ledger
    as *"fitted venue-level home effect: ROI exceeds one league-wide constant"*,
    and the price backtest is what decides it.
    """
    day = str(as_of)
    frame = history if history is not None else pd.DataFrame()
    if not frame.empty:
        leaked = frame[frame["slate_date"].astype(str) >= day]
        if not leaked.empty:
            raise WalkForwardViolation(
                f"{len(leaked):,} of {len(frame):,} history rows are dated on or "
                f"after {day}, the day being priced. A model that has seen the "
                "game it is pricing does not have an edge, it has the answer."
            )

    if venue_level_home_effect is None:
        applied = verdicts.ships(
            "venue_home_effect", competition, output_dir=output_dir
        )
        note = (
            "the recorded `venue_home_effect` verdict is in force"
            if applied
            else "no `venue_home_effect` verdict is recorded, so the tier effect "
            "prices and the per-venue departures are reported, not applied"
        )
    else:
        applied = bool(venue_level_home_effect)
        note = "set by the caller"

    league_efficiency, league_tempo = _league_levels(frame, prior)
    teams = sorted(
        set(prior.team)
        | (set(frame["team_id"]) | set(frame["opponent_id"]) if not frame.empty else set()),
        key=repr,
    )
    index = {team: i for i, team in enumerate(teams)}
    size = len(teams)
    if size == 0:
        return Ratings(
            season=int(season or prior.season),
            as_of=day,
            priced_through="",
            games=0,
            team_games=0,
            league_efficiency=league_efficiency,
            league_tempo=league_tempo,
            prior=prior,
            venue=prior.venue,
            venue_level_home_effect=applied,
            venue_effect_note=note,
        )

    means = _prior_means(teams, prior, day)
    strength = {c: prior.strength(c) for c in COMPONENTS}

    offence, defence, prior_weight, residual_sd = _fit_efficiency(
        frame,
        index=index,
        means=means,
        strength=strength,
        league_efficiency=league_efficiency,
        venue=prior.venue,
        prior=prior,
        apply_venue_departures=applied,
    )
    tempo, tempo_weight = _fit_tempo(
        frame,
        index=index,
        means=means,
        strength=strength[TEMPO],
        league_tempo=league_tempo,
    )
    prior_weight.update(tempo_weight)

    graph = connectivity(frame)
    priced_through = (
        str(frame["slate_date"].astype(str).max()) if not frame.empty else ""
    )
    return Ratings(
        season=int(season or prior.season),
        as_of=day,
        priced_through=priced_through,
        games=int(frame["game_id"].nunique()) if not frame.empty else 0,
        team_games=int(len(frame)),
        league_efficiency=league_efficiency,
        league_tempo=league_tempo,
        offence=offence,
        defence=defence,
        tempo=tempo,
        prior_weight=prior_weight,
        prior=prior,
        venue=prior.venue,
        graph=graph,
        residual_sd=residual_sd,
        venue_level_home_effect=applied,
        venue_effect_note=note,
    )


def _league_levels(frame: pd.DataFrame, prior: Prior) -> tuple[float, float]:
    """This season's league efficiency and tempo, shrunk toward last season's.

    The level is not a constant of the sport: efficiency has drifted from 103.3
    to 108.5 points per 100 across eight cached seasons, which is why the prior
    is the previous season's level rather than a number in this file, and why it
    is outweighed by this season's own games within a few dozen of them.
    """
    if frame.empty:
        return prior.league_efficiency, prior.league_tempo
    observed_efficiency = float(frame["efficiency"].mean())
    games = frame.drop_duplicates("game_id")
    observed_tempo = float(games["game_possessions"].mean())
    if prior.league_efficiency <= 0:
        return observed_efficiency, observed_tempo
    weight_e = float(prior.league_efficiency_strength)
    weight_t = float(prior.league_tempo_strength)
    efficiency = (
        (len(frame) * observed_efficiency + weight_e * prior.league_efficiency)
        / (len(frame) + weight_e)
        if len(frame) + weight_e > 0
        else observed_efficiency
    )
    tempo = (
        (len(games) * observed_tempo + weight_t * prior.league_tempo)
        / (len(games) + weight_t)
        if len(games) + weight_t > 0
        else observed_tempo
    )
    return efficiency, tempo


def _prior_means(teams: Sequence, prior: Prior, day: str) -> dict[str, np.ndarray]:
    """Each team's prior departure, with the roster terms if they are known.

    A team with no previous-season rating takes its **tier's** mean, and
    `Tier.UNPLACED` takes the mid-major one, which is `conferences.Tier`'s own
    recorded rule rather than a decision made here.
    """
    shares = (
        prior.roster.share_as_of(day)
        if prior.roster is not None
        else pd.DataFrame(columns=["returning", "incoming", "incoming_level"])
    )
    returning_mean = (
        float(prior.fits[OFFENCE].returning) if OFFENCE in prior.fits else 0.0
    )
    del returning_mean  # the centring is inside the carryover fit, not here

    out = {c: np.zeros(len(teams)) for c in COMPONENTS}
    for position, team in enumerate(teams):
        record = prior.team.get(team)
        tier = prior.tier_of(team)
        if tier == Tier.UNPLACED.value:
            tier = UNPLACED_PRIOR_TIER.value
        for component, tier_means in (
            (OFFENCE, prior.tier_offence),
            (DEFENCE, prior.tier_defence),
            (TEMPO, prior.tier_tempo),
        ):
            base = (
                getattr(record, component)
                if record is not None
                else float(tier_means.get(tier, 0.0))
            )
            fit_for = prior.fits.get(component)
            if (
                fit_for is not None
                and fit_for.uses_roster
                and team in shares.index
            ):
                row = shares.loc[team]
                base += (
                    fit_for.returning * float(row["returning"])
                    + fit_for.incoming * float(row["incoming"])
                    + fit_for.incoming_level
                    * float(row["incoming"])
                    * float(row["incoming_level"])
                )
            out[component][position] = base
    return out


def _fit_efficiency(
    frame: pd.DataFrame,
    *,
    index: Mapping,
    means: Mapping[str, np.ndarray],
    strength: Mapping[str, float],
    league_efficiency: float,
    venue: VenueEffects,
    prior: Prior,
    apply_venue_departures: bool,
) -> tuple[dict, dict, dict, float]:
    """Offence and defence, ridged toward the prior, venue effects taken out.

    The venue terms are **subtracted from the response** rather than fitted
    here. They come from completed seasons, they are held fixed through this
    one, and re-estimating them nightly off a part-season would let a November
    fit with four hundred games decide what a home court is worth.
    """
    size = len(index)
    columns = 2 * size
    penalty = np.concatenate(
        [
            np.full(size, float(strength[OFFENCE])),
            np.full(size, float(strength[DEFENCE])),
        ]
    )
    centre = np.concatenate([means[OFFENCE], means[DEFENCE]])
    if frame.empty:
        offence = {team: float(means[OFFENCE][i]) for team, i in index.items()}
        defence = {team: float(means[DEFENCE][i]) for team, i in index.items()}
        weights = {(OFFENCE, team): 1.0 for team in index}
        weights.update({(DEFENCE, team): 1.0 for team in index})
        return offence, defence, weights, 0.0

    count = len(frame)
    design = np.zeros((count, columns))
    order = np.arange(count)
    design[order, frame["team_id"].map(index).to_numpy()] = 1.0
    design[order, frame["opponent_id"].map(index).to_numpy() + size] = 1.0

    response = (
        frame["efficiency"].to_numpy(dtype=float)
        - league_efficiency
        - _venue_terms(frame, venue, prior, apply_venue_departures)
    )
    normal = design.T @ design + np.diag(penalty)
    coefficients = np.linalg.solve(normal, design.T @ response + penalty * centre)
    residual = response - design @ coefficients
    residual_sd = float(np.std(residual, ddof=1)) if count > 1 else 0.0

    # The prior's share of each parameter, exactly: the row sum of A⁻¹Λ, which
    # is how much of the estimate would move if the whole prior moved by one.
    share = np.linalg.solve(normal, penalty)
    share = np.clip(share, 0.0, 1.0)

    offence = {team: float(coefficients[i]) for team, i in index.items()}
    defence = {team: float(coefficients[i + size]) for team, i in index.items()}
    weights = {(OFFENCE, team): float(share[i]) for team, i in index.items()}
    weights.update({(DEFENCE, team): float(share[i + size]) for team, i in index.items()})
    return offence, defence, weights, residual_sd


def _venue_terms(
    frame: pd.DataFrame,
    venue: VenueEffects,
    prior: Prior,
    apply_departures: bool,
) -> np.ndarray:
    """What the venue adds to each team-game's efficiency, before team skill."""
    at_home = (frame["venue_state"].astype(str) == VenueState.HOME.value).to_numpy()
    quasi = (
        frame["venue_state"].astype(str) == VenueState.QUASI_NEUTRAL.value
    ).to_numpy()
    local = frame["is_local"].to_numpy(dtype=bool)
    opponent_local = frame["opponent_is_local"].to_numpy(dtype=bool)
    tiers = frame["local_team_id"].map(prior.tier_of).to_numpy()

    offence_effect = np.array([venue.home_offence(t) for t in tiers])
    defence_effect = np.array([venue.home_defence(t) for t in tiers])
    terms = np.where(at_home & local, offence_effect, 0.0)
    terms += np.where(at_home & opponent_local, defence_effect, 0.0)
    terms += np.where(quasi & local, venue.quasi_offence, 0.0)
    terms += np.where(quasi & opponent_local, venue.quasi_defence, 0.0)

    if apply_departures and "venue_id" in frame.columns:
        departure = frame["venue_id"].map(venue.departure_for).fillna(0.0).to_numpy(float)
        terms += np.where(at_home & local, departure / 2.0, 0.0)
        terms -= np.where(at_home & opponent_local, departure / 2.0, 0.0)
    return terms


def _fit_tempo(
    frame: pd.DataFrame,
    *,
    index: Mapping,
    means: Mapping[str, np.ndarray],
    strength: float,
    league_tempo: float,
) -> tuple[dict, dict]:
    """Possessions per forty minutes, as the sum of the two sides' effects.

    One row per **game**, not per team-game: the two teams share a possession
    count, so a team-game frame would count each game twice and halve the
    standard error of something measured once.
    """
    size = len(index)
    if frame.empty:
        tempo = {team: float(means[TEMPO][i]) for team, i in index.items()}
        return tempo, {(TEMPO, team): 1.0 for team in index}

    games = frame.drop_duplicates("game_id")
    count = len(games)
    design = np.zeros((count, size))
    order = np.arange(count)
    np.add.at(design, (order, games["team_id"].map(index).to_numpy()), 1.0)
    np.add.at(design, (order, games["opponent_id"].map(index).to_numpy()), 1.0)
    response = games["game_possessions"].to_numpy(dtype=float) - league_tempo
    penalty = np.full(size, float(strength))
    normal = design.T @ design + np.diag(penalty)
    coefficients = np.linalg.solve(normal, design.T @ response + penalty * means[TEMPO])
    share = np.clip(np.linalg.solve(normal, penalty), 0.0, 1.0)
    tempo = {team: float(coefficients[i]) for team, i in index.items()}
    return tempo, {(TEMPO, team): float(share[i]) for team, i in index.items()}


# --------------------------------------------------------------------------
# The seam to `distributions.build`
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Matchup:
    """The three numbers a game is priced from, and every reason not to.

    This is the dataclass `reports/gameday_card.Matchup` declares as a Protocol,
    and the field names are that Protocol's, exactly. The card reads
    `priceable` first and `unpriceable_reason` beside it; nothing downstream
    ever sees a probability for a game this refuses.

    `prior_weight` is the **largest** prior share among the six parameters that
    enter this price, not the average, and `None` would mean *not recorded*,
    which is a different claim from 0.0 — so it is always set here.
    """

    home_points_per_possession: float
    away_points_per_possession: float
    possessions: float
    prior_weight: float | None
    venue_state: str
    priceable: bool
    unpriceable_reason: str = ""
    event_id: str = ""
    home_team_id: object = None
    away_team_id: object = None
    home_tier: str = Tier.UNPLACED.value
    away_tier: str = Tier.UNPLACED.value
    effective_resistance: float = float("inf")
    home_prior_weight: float = 1.0
    away_prior_weight: float = 1.0
    venue_home_effect: float = 0.0
    priced_through: str = ""
    as_of: str = ""

    @property
    def expected_margin(self) -> float:
        """Home minus away, in points, before overtime. A convenience for logs."""
        return (
            (self.home_points_per_possession - self.away_points_per_possession)
            * self.possessions
        )

    @property
    def expected_total(self) -> float:
        return (
            self.home_points_per_possession + self.away_points_per_possession
        ) * self.possessions

    def summary_line(self) -> str:
        if not self.priceable:
            return f"not priced: {self.unpriceable_reason}"
        return (
            f"{self.home_points_per_possession:.4f} / "
            f"{self.away_points_per_possession:.4f} points per possession over "
            f"{self.possessions:.1f} possessions ({self.venue_state}), margin "
            f"{self.expected_margin:+.1f}, total {self.expected_total:.1f}, "
            f"{self.prior_weight:.0%} prior, resistance "
            f"{self.effective_resistance:.2f}."
        )


def matchup(
    ratings: Ratings,
    *,
    home_team_id,
    away_team_id,
    venue_state: str,
    local_team_id=None,
    venue_id=None,
    event_id: str = "",
) -> Matchup:
    """The three numbers for one game, or a refusal that says why.

    Five things stop a price, and every one of them is an honest output:

    1. an **unknown venue state** — CLAUDE.md's *"a game mislabelled neutral is
       a multi-point error applied to every market on it"*, and this sport's
       neutral has three values;
    2. **connectivity** — the two teams are in different components of the
       games-played graph, or joined by less than one head-to-head meeting's
       worth of evidence, so any difference between their ratings is the prior
       talking;
    3. a **quasi-neutral game whose local side is unknown**, which would put a
       venue effect on the wrong team a third of the time;
    4. a rating outside the support the per-possession distribution can
       represent, which means something upstream is wrong rather than extreme;
    5. a **non-positive tempo**, for the same reason.

    `local_team_id` is which participant is in its own city or arena. For an
    ordinary home game it is the home team and may be left out; for a
    quasi-neutral one it must be supplied, because the designation is wrong 32.5%
    of the time.
    """
    state = str(venue_state or "")
    common = dict(
        event_id=event_id,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        home_tier=ratings.tier_of(home_team_id),
        away_tier=ratings.tier_of(away_team_id),
        venue_state=state,
        priced_through=ratings.priced_through,
        as_of=ratings.as_of,
    )

    def refuse(reason: str, **extra) -> Matchup:
        return Matchup(
            home_points_per_possession=0.0,
            away_points_per_possession=0.0,
            possessions=0.0,
            prior_weight=None,
            priceable=False,
            unpriceable_reason=reason,
            **common,
            **extra,
        )

    known = {v.value for v in VenueState} - {VenueState.UNKNOWN.value}
    if state not in known:
        return refuse(
            "the venue state is unknown or contradictory, so the game is "
            "quarantined rather than defaulted to neutral"
        )

    if state == VenueState.HOME.value and local_team_id is None:
        local_team_id = home_team_id
    if state == VenueState.QUASI_NEUTRAL.value and local_team_id is None:
        return refuse(
            "this game is flagged neutral in a participant's own city and the "
            "lab cannot tell whose. The designation is the wrong team 32.5% of "
            "the time, so it is refused rather than guessed"
        )

    connected, reason = ratings.graph.connects(home_team_id, away_team_id)
    resistance = ratings.graph.resistance_between(home_team_id, away_team_id)
    if not connected:
        return refuse(reason, effective_resistance=resistance)

    weights = [
        ratings.prior_weight_for(home_team_id, OFFENCE),
        ratings.prior_weight_for(home_team_id, DEFENCE),
        ratings.prior_weight_for(home_team_id, TEMPO),
        ratings.prior_weight_for(away_team_id, OFFENCE),
        ratings.prior_weight_for(away_team_id, DEFENCE),
        ratings.prior_weight_for(away_team_id, TEMPO),
    ]
    home_weight = max(weights[:3])
    away_weight = max(weights[3:])

    home_offence = float(ratings.offence.get(home_team_id, 0.0))
    home_defence = float(ratings.defence.get(home_team_id, 0.0))
    away_offence = float(ratings.offence.get(away_team_id, 0.0))
    away_defence = float(ratings.defence.get(away_team_id, 0.0))

    home_effect, away_effect, applied = _match_venue_effect(
        ratings,
        state=state,
        home_team_id=home_team_id,
        away_team_id=away_team_id,
        local_team_id=local_team_id,
        venue_id=venue_id,
    )

    home = ratings.league_efficiency + home_offence + away_defence + home_effect
    away = ratings.league_efficiency + away_offence + home_defence + away_effect
    possessions = ratings.expected_tempo(home_team_id, away_team_id)

    support = float(len(distributions.PER_POSSESSION_POINTS) - 1)
    for side, value in (("home", home), ("away", away)):
        if not np.isfinite(value) or not 0.0 < value / POSSESSION_SCALE < support:
            return refuse(
                f"the fitted {side} efficiency of {value:.1f} per 100 possessions "
                "is outside the support of the measured per-possession "
                "distribution — a rating no possession could produce is a defect "
                "upstream, not an extreme team",
                effective_resistance=resistance,
            )
    if not np.isfinite(possessions) or possessions <= 0:
        return refuse(
            f"the fitted tempo of {possessions:.1f} possessions is not a game",
            effective_resistance=resistance,
        )

    return Matchup(
        home_points_per_possession=home / POSSESSION_SCALE,
        away_points_per_possession=away / POSSESSION_SCALE,
        possessions=float(possessions),
        prior_weight=float(max(home_weight, away_weight)),
        priceable=True,
        unpriceable_reason="",
        effective_resistance=resistance,
        home_prior_weight=float(home_weight),
        away_prior_weight=float(away_weight),
        venue_home_effect=float(applied),
        **common,
    )


def _match_venue_effect(
    ratings: Ratings,
    *,
    state: str,
    home_team_id,
    away_team_id,
    local_team_id,
    venue_id,
) -> tuple[float, float, float]:
    """What this venue adds to each side, and the margin effect it amounts to."""
    venue = ratings.venue
    if state == VenueState.NEUTRAL.value or local_team_id is None:
        return 0.0, 0.0, 0.0
    tier = ratings.tier_of(local_team_id)
    if state == VenueState.QUASI_NEUTRAL.value:
        offence, defence, departure = venue.quasi_offence, venue.quasi_defence, 0.0
    else:
        offence, defence = venue.home_offence(tier), venue.home_defence(tier)
        departure = (
            venue.departure_for(venue_id) if ratings.venue_level_home_effect else 0.0
        )
    if local_team_id == home_team_id:
        return offence + departure / 2.0, defence - departure / 2.0, offence - defence + departure
    if local_team_id == away_team_id:
        return defence - departure / 2.0, offence + departure / 2.0, -(offence - defence + departure)
    return 0.0, 0.0, 0.0


def to_distribution(
    game: Matchup, *, segment: str = distributions.FULL_GAME, **kwargs
) -> distributions.GameDistribution:
    """The joint distribution this matchup implies. One call, one contract.

    It exists so that the seam between the two modules is exercised by a test
    rather than asserted in a docstring, and so that no caller ever has to know
    the argument names twice.
    """
    if not game.priceable:
        raise RatingsError(
            "This matchup was refused and carries no price: "
            + (game.unpriceable_reason or "no reason recorded")
        )
    return distributions.build(
        home_points_per_possession=game.home_points_per_possession,
        away_points_per_possession=game.away_points_per_possession,
        possessions=game.possessions,
        segment=segment,
        prior_weight=game.prior_weight,
        **kwargs,
    )


# --------------------------------------------------------------------------
# State it, then measure it
# --------------------------------------------------------------------------


def roster_turnover(
    player_games: pd.DataFrame, *, seasons: Iterable[int], teams: Iterable | None = None
) -> list[dict]:
    """The measured rate of roster turnover, season by season.

    Cooper: *"Roster turnover in this sport is enormous — transfer portal,
    graduation, early entries — and measure the current rate rather than quoting
    mine."* This is that measurement, and it is the empirical argument for the
    whole November regime: if three quarters of a team's minutes are new, last
    season's rating is a prior and not a fit.
    """
    frame = player_games[~player_games["did_not_play"].fillna(False).astype(bool)].copy()
    frame["minutes"] = pd.to_numeric(frame["minutes"], errors="coerce").fillna(0.0)
    frame["season"] = pd.to_numeric(frame["season"], errors="coerce")
    allowed = set(teams) if teams is not None else None
    totals = frame.groupby(["season", "team_id", "athlete_id"])["minutes"].sum().reset_index()

    out: list[dict] = []
    for season in sorted(seasons):
        previous = totals[totals["season"] == season - 1]
        current = totals[totals["season"] == season]
        if previous.empty or current.empty:
            continue
        rosters = current.groupby("team_id")["athlete_id"].apply(set)
        elsewhere = (
            previous.sort_values("minutes")
            .drop_duplicates("athlete_id", keep="last")
            .set_index("athlete_id")["team_id"]
            .to_dict()
        )
        returning: list[float] = []
        incoming: list[float] = []
        for team, group in previous.groupby("team_id"):
            if allowed is not None and team not in allowed:
                continue
            total = float(group["minutes"].sum())
            if total <= 0:
                continue
            roster = rosters.get(team, set())
            returning.append(
                float(group[group["athlete_id"].isin(roster)]["minutes"].sum()) / total
            )
            this_year = current[current["team_id"] == team]
            played = float(this_year["minutes"].sum())
            if played > 0:
                incoming.append(
                    float(
                        this_year[
                            this_year["athlete_id"].map(
                                lambda a: elsewhere.get(a) not in (None, team)
                            )
                        ]["minutes"].sum()
                    )
                    / played
                )
        if not returning:
            continue
        out.append(
            {
                "season": int(season),
                "teams": len(returning),
                "returning_minutes_share": float(np.mean(returning)),
                "returning_minutes_median": float(np.median(returning)),
                "incoming_transfer_share": float(np.mean(incoming)) if incoming else 0.0,
            }
        )
    return out


def connectivity_timeline(
    prepared: PreparedGames, *, season: int, days: Sequence[str]
) -> list[dict]:
    """The connectivity diagnostic on each of a set of days. The refusal, dated.

    This is the table in the module docstring, re-derivable rather than quoted:
    a report that cannot recompute its own headline is a report nobody can
    check.
    """
    rows = prepared.rows
    season_rows = rows[rows["season"] == season]
    out: list[dict] = []
    for day in days:
        history = season_rows[season_rows["slate_date"].astype(str) < str(day)]
        graph = connectivity(history)
        quantiles = graph.resistance_quantiles((0.5,))
        out.append(
            {
                "day": str(day),
                "games": graph.games,
                "teams": graph.teams,
                "components": graph.components,
                "largest_component": (
                    max(graph.component_sizes.values()) if graph.component_sizes else 0
                ),
                "median_resistance": quantiles[0.5],
                "priceable_share": graph.priceable_share(),
                "fiedler_value": graph.fiedler_value,
            }
        )
    return out


def fit_report(ratings: Ratings, prepared: PreparedGames | None = None) -> str:
    """Everything a run should print about a fit, in one block of prose.

    Deliberately not a dashboard. It prints the sample size beside every number,
    the prior weight distribution per component, the connectivity diagnostic,
    and the venue effects per tier — and it says in words that none of it is
    evidence of an edge, because a table of fitted coefficients reads like a
    result and is not one.
    """
    lines = [ratings.summary_line()]
    if prepared is not None:
        lines.append(prepared.summary_line())
        if prepared.quasi_local_side_unknown:
            lines.append(
                f"  {prepared.quasi_local_side_unknown:,} quasi-neutral team-games "
                "have no identified local side and were fitted as neutral."
            )
    if ratings.prior is not None:
        lines.append(ratings.prior.summary_line())
    lines.append(ratings.venue.summary_line())
    lines.append(f"  Venue-level departures: {ratings.venue_effect_note}.")

    distribution = ratings.prior_weight_distribution()
    lines.append("Prior weight by component (share of the rating that is prior):")
    for component in COMPONENTS:
        quantiles = distribution[component]
        lines.append(
            "  "
            + component
            + ": "
            + ", ".join(f"p{int(q * 100)}={v:.0%}" for q, v in sorted(quantiles.items()))
        )
    lines.append(
        "None of the above is evidence of an edge. Calibration and fit quality "
        "can rule a model out and never in; the price backtest decides."
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The seam: one callable the backtest, the card and the freeze all price through
# ---------------------------------------------------------------------------

#: Prepared once per season and reused across that season's slate days. The
#: `Prior` docstring is explicit that it is built from seasons strictly earlier
#: than the one being priced, so it does not move within a season and rebuilding
#: it daily would be ~147x the work for the same object. The roster evidence
#: inside it does move, and moves legitimately — a player who has appeared has
#: appeared — which is why the key carries the day's month rather than the day.
_SEASON_CACHE: dict[tuple, "Prior"] = {}
_TIER_CACHE: dict[tuple, "TierTable"] = {}
#: Keyed on (season, raw_dir). **Keying on the season alone was a defect**: a
#: caller pointing at a different `--raw-dir` — which every card test does —
#: got back the frame read from whichever directory was consulted first, and
#: silently priced against another tree's schedule.
_SCHEDULE_CACHE: dict[tuple, "pd.DataFrame"] = {}
_CLASSIFIED_CACHE: dict[tuple, "pd.DataFrame"] = {}
#: The per-season fixture lookup `matchups_for` builds; rebuilding it from
#: 6,318 schedule rows on every slate day is the same waste in miniature.
_FIXTURES_CACHE: dict[tuple, dict] = {}


def clear_caches() -> None:
    """Drop every memo. Tests that change the cached feeds call this."""
    for cache in (
        _SEASON_CACHE, _TIER_CACHE, _SCHEDULE_CACHE, _CLASSIFIED_CACHE,
        _LOCAL_TEAMS_CACHE, _VENUE_IDS_CACHE, _FIXTURES_CACHE,
    ):
        cache.clear()


def _cached_schedule(season: int, raw_dir: Path | str | None = None) -> "pd.DataFrame":
    """One season's schedule, from the hoopR cache.

    Reading the schedule for the day being priced is **not** a walk-forward
    leak. It supplies who is playing and where, both of which are knowable
    hours before tip and are exactly what the card knows. Nothing here reads a
    score: `fit` is handed `history`, which the backtest has already cut to
    games strictly earlier than the day.
    """
    root = Path(raw_dir) if raw_dir else Path(config.RAW_DIR)
    key = (int(season), str(root))
    if key in _SCHEDULE_CACHE:
        return _SCHEDULE_CACHE[key]
    path = root / CBB.data_dir_segment / "schedules" / f"mbb_schedule_{season}.parquet"
    if not path.is_file():
        raise FileNotFoundError(
            f"No cached schedule for season {season} at {path}. The model "
            "cannot learn who is playing tonight, and inventing a fixture is "
            "worse than declining to price one. Run scripts/fetch_cbb_data.py."
        )
    frame = pd.read_parquet(path)
    _SCHEDULE_CACHE[key] = frame
    return frame


def _cached_classified(season: int, raw_dir: Path | str | None = None) -> "pd.DataFrame":
    root = Path(raw_dir) if raw_dir else Path(config.RAW_DIR)
    key = (int(season), str(root))
    if key in _CLASSIFIED_CACHE:
        return _CLASSIFIED_CACHE[key]
    out = classify(_cached_schedule(season, raw_dir))
    _CLASSIFIED_CACHE[key] = out
    return out



def local_teams(schedules: Mapping[int, "pd.DataFrame"]) -> dict:
    """The local side of every quasi-neutral game, memoised on the seasons.

    See `_LOCAL_TEAMS_CACHE`. `clear_caches()` drops this along with the rest.
    """
    key = _schedule_key(schedules)
    hit = _LOCAL_TEAMS_CACHE.get(key)
    if hit is None:
        # The frames are stored beside the answer so their `id()`s stay valid.
        hit = (tuple(schedules.values()), _local_teams_uncached(schedules))
        _LOCAL_TEAMS_CACHE[key] = hit
    return hit[1]


def venue_ids(schedules: Mapping[int, "pd.DataFrame"]) -> dict:
    """Game id to venue id, memoised on the seasons."""
    key = _schedule_key(schedules)
    hit = _VENUE_IDS_CACHE.get(key)
    if hit is None:
        hit = (tuple(schedules.values()), _venue_ids_uncached(schedules))
        _VENUE_IDS_CACHE[key] = hit
    return hit[1]


def matchups_for(
    *,
    day: str,
    history: "pd.DataFrame",
    prices: "pd.DataFrame",
    competition: Competition = CBB,
    raw_dir: Path | str | None = None,
    player_games: "pd.DataFrame | None" = None,
) -> dict[str, "Matchup"]:
    """One `Matchup` per priced event, or no entry at all.

    This is the single seam between the ratings and everything that consumes
    them — the price backtest, the gameday card and the forward freeze all call
    it, so a game priced in a measurement is priced the same way it would be on
    a card. Two pricing paths is how the football lab shipped a ladder whose
    −6.5 beat its −7.5 on a team it made a favourite.

    **A missing entry is not a probability of zero.** An event this returns
    nothing for reads `no opinion` downstream, which is a different census
    bucket from the model declining to find value, and both are different from
    the model refusing to price the matchup at all. That last case *does* get an
    entry — a `Matchup` with `priceable=False` and a reason — because "the
    schedule graph has not connected these two teams by anything but the prior"
    is a finding the report should carry, not a silence.

    **Joined on `game_id`, never on a name.** The store carries the hoopR game
    id that the purchase plan resolved at buy time, so this join does not go
    near the provider's spelling of a school. That matters more here than in
    any sibling lab: the retention probe measured 20.5% of provider team names
    unresolved, biased to **46.7% at the low-major end** — the exact population
    this lab exists to ask about. Names are resolved once, at purchase, where a
    failure is visible as an unmatched event rather than as a quiet absence.
    """
    season = season_for_slate_date(day)
    if not season:
        return {}

    schedule = _cached_schedule(season, raw_dir)
    classified = _cached_classified(season, raw_dir)

    # EVERY SEASON IN THE HISTORY NEEDS ITS OWN SCHEDULE, not just the one
    # being priced. `prepare` reads venue and locality off the schedule, and the
    # prior is fitted on seasons strictly earlier than this one — so supplying
    # only this season's schedule left those earlier seasons with no local team
    # on any game. Their two quasi-neutral venue columns were then structurally
    # zero, and the fit raised `Singular matrix` on 2019, 2020 and 2021 while
    # working on 2022. The ridge in `_season_fit` makes that survivable; this
    # makes it correct, and the two fixes are not substitutes for one another.
    history_seasons = sorted(
        {int(s) for s in pd.to_numeric(history.get("season"), errors="coerce").dropna().unique()}
        | {season}
    ) if "season" in getattr(history, "columns", []) else [season]
    schedules: dict[int, pd.DataFrame] = {}
    for one in history_seasons:
        try:
            schedules[one] = _cached_schedule(one, raw_dir)
        except FileNotFoundError:
            # A season with no cached schedule contributes no venue or locality
            # evidence. It is counted by `prepare` rather than silently dropped.
            continue

    # THE TIER TABLE IS BUILT FROM SEASONS STRICTLY EARLIER, which is
    # `conferences.tier_table`'s own rule and was being broken here. Letting the
    # priced season in moves **34 of 367 teams (9.3%)** across a tier boundary,
    # measured by `scripts/fit_ratings.py`. A tier is not a label: it selects
    # which home-court effect is applied, so a team on the wrong side of a cut
    # point is a multi-point error on every market on its home games — and the
    # error is a leak, because it uses the season's own conference membership to
    # price that season.
    earlier = tuple(s for s in sorted(schedules) if s < season)
    seasons_for_tiers = earlier or (season,)
    # Same lesson as the schedule cache: the seasons do not identify the
    # frames, so the key carries the frames' identity too.
    tier_key = tuple(
        (int(s), id(schedules[s]), len(schedules[s])) for s in seasons_for_tiers
    )
    tiers = _TIER_CACHE.get(tier_key)
    if tiers is None:
        # With no earlier season there is nothing honest to build from, and the
        # priced season is used rather than leaving every team unplaced. That is
        # a leak too, and it is the smaller one; it is recorded here rather than
        # hidden because a first-season lab should know which of the two it has.
        tiers = tier_table(
            {s: schedules[s] for s in seasons_for_tiers}, seasons_for_tiers
        )
        _TIER_CACHE[tier_key] = tiers

    prepared = prepare(history, schedules=schedules)

    # The prior does not move within a season, so it is built once. The month
    # is in the key because the roster evidence inside it legitimately does
    # move as players appear.
    prior_key = (season, str(day)[:7])
    prior = _SEASON_CACHE.get(prior_key)
    if prior is None:
        prior = prepare_prior(
            prepared,
            season=season,
            tiers=tiers,
            schedules=schedules,
            player_games=player_games,
        )
        _SEASON_CACHE[prior_key] = prior

    # `fit` takes `prepare(...).rows`, not raw team-games — it reads the
    # derived `efficiency` and `possessions` columns that `prepare` computes
    # and validates. Handing it the raw frame raises on a missing column, which
    # is the right failure: a fit that silently skipped the preparation would
    # be fitting on unvalidated possessions.
    #
    # AND IT TAKES ONE SEASON, which is the harder half. `fit`'s own contract is
    # "history filtered to the season being priced", because **a team is not the
    # team it was last March** — the transfer portal sees to that. Handing it
    # every season of history put 31,828 team-games of old evidence in the
    # design matrix on opening night, and the prior's weight collapsed to
    # **0.0% and stayed there all season**, measured by `scripts/fit_ratings.py`.
    #
    # That is not a rounding error, it is the November regime deleted: Cooper's
    # requirement is that the prior's weight is reported in every price so a
    # November number can never be presented as a February one, and a card
    # priced through this seam would have printed 0% on 3 November and 0% on 20
    # February. The earlier seasons still do their work — they build the PRIOR,
    # which is exactly the channel they are supposed to reach the fit through.
    season_rows = prepared.rows
    if "season" in season_rows.columns:
        season_rows = season_rows[season_rows["season"] == season]
    ratings = fit(
        season_rows,
        prior=prior,
        as_of=day,
        season=season,
        competition=competition,
    )

    # Fixture facts, keyed by game id: who is playing and where. Cached per
    # season — it is a property of the schedule, not of the day, and rebuilding
    # it from 6,318 rows on each of ~600 walk-forward days is the same waste
    # `local_teams` was committing on a larger scale.
    fixture_key = (int(season), str(Path(raw_dir) if raw_dir else config.RAW_DIR))
    fixtures = _FIXTURES_CACHE.get(fixture_key)
    if fixtures is None:
        fixtures = {}
        for row in classified.to_dict("records"):
            game_id = row.get("id")
            if game_id is None:
                continue
            try:
                fixtures[int(game_id)] = row
            except (TypeError, ValueError):
                continue
        _FIXTURES_CACHE[fixture_key] = fixtures

    local = local_teams({season: schedule})
    venues = venue_ids({season: schedule})

    out: dict[str, Matchup] = {}
    seen: set[str] = set()
    for record in prices.to_dict("records"):
        event_id = clean_text(record.get("event_id"))
        if not event_id or event_id in seen:
            continue
        seen.add(event_id)
        raw_game = record.get("game_id")
        try:
            game_id = int(raw_game)
        except (TypeError, ValueError):
            # No id means no fixture, and a fixture guessed from two school
            # names is the join this seam exists to avoid.
            continue
        fixture = fixtures.get(game_id)
        if fixture is None:
            continue
        try:
            home_team_id = int(fixture.get("home_id"))
            away_team_id = int(fixture.get("away_id"))
        except (TypeError, ValueError):
            continue
        out[event_id] = matchup(
            ratings,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            venue_state=clean_text(fixture.get("venue_state")),
            local_team_id=local.get(game_id),
            venue_id=venues.get(game_id),
            event_id=event_id,
        )
    return out
