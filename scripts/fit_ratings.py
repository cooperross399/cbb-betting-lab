#!/usr/bin/env python3
"""Fit the ratings walk-forward, and report what the fit is actually made of.

    # The default: the latest season the processed tables hold, refitted on
    # every one of its slate days from games strictly earlier than each.
    PYTHONPATH=src python scripts/fit_ratings.py --competition cbb

    # Several seasons, and a report re-rendered from the record for free.
    PYTHONPATH=src python scripts/fit_ratings.py --seasons 2024 2025 2026
    PYTHONPATH=src python scripts/fit_ratings.py --rebuild-report-only

`scripts/run_weekly_loop.py` has held `REFIT_SCRIPT = "fit_ratings.py"` since it
was written, and this file did not exist. Every weekly run therefore reported
step 2 as `MISSING` — *"nobody has written the refit yet"* — and finished red
with nothing refitted. That is the whole reason this program exists, and it is
worth saying plainly: **the loop was correct and the repository was not.**

It spends nothing, opens no socket and buys no price. It reads
`data/processed/cbb_team_games.csv`, `data/processed/cbb_player_games.csv` and
the cached hoopR schedules under `data/raw/cbb/schedules/`, and it writes two
files: a run record in JSON and a report rendered purely from it.

## What a fit report is for, and the failure it is arranged against

`models/ratings.py` ends its own `fit_report()` with the sentence this file
takes as its brief: *"a table of fitted coefficients reads like a result and is
not one."* A report that prints the coefficients and stops has done the easy
half. So every fitted number here is printed **beside a measurement of the same
quantity taken a different way**, with its sample size, and the two are allowed
to disagree in public:

* the **prior's weight** is not asserted to decay, it is recomputed on every
  slate day and the decay is checked — and a violation ends this program
  non-zero, because a prior weight that rises as games arrive is not a
  posterior and the card would be printing a number that means nothing;
* **connectivity** is not quoted from the module docstring's table, it is
  re-derived by `ratings.connectivity_timeline` on the days the report prints;
* the **tier home-court effect** the model applies is printed against a
  within-pair estimate of the same effect, which is exact by construction — see
  *The venue audit* below, and read it before quoting a high-major number;
* **roster turnover** is measured here, on this lab's own tables. The NHL lab's
  20.4% and the football lab's 9.8% are facts about other sports and neither is
  quoted anywhere in this file.

## Walk-forward, structurally, and checked on the stamp

The cut is not made by this file. `price_backtest.walk_forward` walks the slate
days in order and hands the fitter only games **strictly earlier** than the day
it is fitting for; every row that comes back is stamped with `priced_through`,
the latest game day the fitter was actually allowed to see, and
`price_backtest.assert_walk_forward` raises if any stamp reaches the day it
priced. `ratings.fit` raises independently on the same condition. Two guards,
neither of which is a convention.

That is deliberately the same machinery the price backtest uses rather than a
second copy of it. The football lab's largest silent leak was a distribution
loaded once outside the season loop, and *"a convention cannot stop that; a
signature can."*

The games handed to `walk_forward` are the **priced season's** rows only. That
is `ratings.fit`'s own documented contract — *"team ratings — the current
season's games, strictly before `as_of`. A team is not the team it was last
March"* — and everything the fit inherits from earlier seasons arrives through
the `Prior`, which is built once, out of the loop, from seasons strictly
earlier than the priced one. See *The seam does not do this* below, because the
seam the card runs does something else and the difference is measured here
rather than argued about.

## The seam does not do this, and the gap is the largest number in the report

`ratings.matchups_for` — the seam the card, the freeze and the price backtest
all price through — passes `prepare(history).rows` to `fit` **without cutting
it to the priced season**, and `run_price_backtest.py` hands it every cached
season. Fitted that way the design matrix carries several seasons of a team's
games on 15 November, so the ridge toward the preseason prior is swamped and
`prior_weight` — the field `Matchup` carries specifically so that *"a November
number can never be printed as if it were a February one"* — reads **0.000**
from the opening Monday to the last day of March.

This program measures both conventions on the same days and prints them side by
side. It does not change `models/ratings.py`: that module is not this task's to
edit, the finding is recorded here, in `tests/test_fit_ratings.py` (the decay
tests and `test_the_seam_does_not_cut_its_history_to_the_priced_season`) and
in `tests/test_ratings_fit_is_well_posed.py::test_the_seam_does_not_delete_the_
november_prior_regime` — this used to cite a `test_prior_weight_decays.py` that
never existed —
and the sibling-lab rule about not silently repairing something that holds
measured numbers applies with the same force inside this repository.

## The venue audit, which is the reason this file is longer than a fit script

`ratings._venue_effects` fits the tier home-court effect on the residuals of a
season fit that carries **no team effects in the second stage**. The report
prints what it produced against a within-pair estimate: for every pair of teams
that met at *both* home venues in the same season, the mean of the two home
margins is the home advantage with every team effect cancelling exactly, by
subtraction and not by assumption.

The two disagree, and they disagree in one tier and not the others. The numbers
are in the report with their sample sizes; they are not repeated here, because
a docstring that carries a measurement is a docstring that goes stale the first
time the data is rebuilt. What belongs here is the reading: **the audit is not
evidence that the model is wrong about basketball. It is evidence about which
of the model's own numbers a reader may quote**, and the tier home effect is
applied to every market on every game, which is what makes it worth a section.

The mechanism this suggests — shrunk ratings for weak opponents leaving a
positive residual that only the home side of a high-major schedule ever
collects — is a hypothesis and is labelled as one in the report.
`docs/what_we_can_and_cannot_claim.md`: *"A finding that is really a mechanism
is the most persuasive kind and the most dangerous, because it supplies its own
explanation and so stops the search for another one."* The two measurements are
the evidence; the mechanism is a lead.

## Nothing here is evidence of an edge

Not one number in this report is a return. The fit is not a price, forecast
error is not profit, and calibration can rule a model out and never in. Where
an interval includes zero this report says **no demonstrated edge** in the
lab's own words, which for a fitted quantity reads as *no demonstrated effect*;
the phrase comes from `stats.NO_DEMONSTRATED_EDGE` rather than being typed, so
a second copy cannot drift from the first.

## Re-renderable, because improving a sentence must never cost a re-run

The retention probe's rule. The record is written first and `render` is a pure
function of it — no clock, no tables, no fit — so `--rebuild-report-only`
rewrites the markdown having recomputed nothing. A report that can only be
produced by re-running the measurement is a report nobody improves, and a
hand-edited generated file survives exactly one re-run.

## Missing inputs are an exit code, never an empty report

A missing processed table, a missing cached schedule, a season filter that
matches nothing: each ends this program with a message naming the file and a
non-zero exit, and nothing is written. An empty fit report reads as a fit that
found nothing, and a fit that found nothing is a claim.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import (
    CBB,
    DEFAULT_COMPETITION_KEY,
    Competition,
    competition_for,
)
from cbb_betting_lab.conferences import Tier, tier_table
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from cbb_betting_lab.experiment_ledger import LEDGER_FILENAME
from cbb_betting_lab.models import ratings as R
from cbb_betting_lab.population import division_one_team_ids
from cbb_betting_lab.reports import price_backtest as PB


#: Bumped whenever the record's shape changes, so a stale record fails loudly at
#: re-render rather than rendering a report with holes in it. The rule
#: `price_backtest` and `retention_probe` already follow, for the same reason.
RECORD_VERSION = 1

#: The stem both outputs share. `Competition.output_name` prefixes it, so
#: nothing else in `data/outputs/` could ever overwrite a CBB record.
OUTPUT_STEM = "ratings_fit"

#: The processed tables a run needs. `team_games` is the fit population and a
#: missing one is refused rather than worked around — fitting on nothing does
#: not fail, it succeeds quietly and prints a league mean over zero games.
REQUIRED_TABLE = "team_games"

#: Optional, and it turns two sections on rather than being faked when absent:
#: the roster terms in the prior, and the roster-turnover measurement. Reported
#: as an absence, never as a zero.
PLAYER_TABLE = "player_games"

#: Only the columns a fit consults. `player_games` is 208 MB and this run reads
#: five of its thirty-two columns; reading the rest costs a minute and settles
#: nothing.
PLAYER_COLUMNS: tuple[str, ...] = (
    "season",
    "slate_date",
    "team_id",
    "athlete_id",
    "minutes",
    "did_not_play",
)

#: Days of the month the report tables print, plus the first and last fit day of
#: each season. The record holds **every** fit day, so this is a rendering
#: choice and changing it costs a re-render rather than a re-fit. The values are
#: the module docstring's own table in `models/ratings.py` — 5, 10, 15, 20, 25,
#: 1 — so the two can be read against each other.
REPORT_DAYS_OF_MONTH: tuple[int, ...] = (1, 5, 10, 15, 20, 25)

#: The window the prior's monotone decay is required over. Cooper's rule is
#: about the November-to-February regime — *"a rating built only on this
#: season's games is uninformative until roughly December"* — and March adds
#: conference tournaments and a fortnight where a third of the board stops
#: playing, which is a different question from whether the ridge is behaving.
DECAY_MONTHS: tuple[str, ...] = ("11", "12", "01", "02")

#: Below this, a difference in prior weight is floating-point noise and nothing
#: else. Used only to decide whether a step counts as a rise at all.
DECAY_TOLERANCE = 1e-9

#: **The rise that matters.** Half a percentage point, and the number is not
#: chosen — it is read off how this quantity is already rendered everywhere it
#: appears. `Matchup.summary_line` prints `{prior_weight:.0%}` and
#: `ratings.fit_report` prints its quantiles the same way, so half a point is
#: the smallest difference that can ever reach a reader of any output this lab
#: produces. A rise smaller than that is invisible by construction.
#:
#: This constant exists because the first version of this check asserted that
#: the median prior weight falls between **every** pair of consecutive slate
#: days, and that assertion is wrong — see `decay_check`. It is written from a
#: pre-existing rendering fact rather than from the size of the rises that were
#: found, which is the direction this repository is arranged against.
DECAY_MATERIAL = 0.005

#: Components, in the order every table prints them. Named from the model so a
#: loop here cannot disagree with the dataclass there.
COMPONENTS: tuple[str, ...] = R.COMPONENTS

#: Tiers, in the order every table prints them, plus the pair bucket for games
#: whose two teams are in different tiers. `unplaced` is its own row and is
#: never folded into a tier's number — `conferences.Tier.UNPLACED` says so.
TIER_ORDER: tuple[str, ...] = (
    Tier.HIGH_MAJOR.value,
    Tier.MID_MAJOR.value,
    Tier.LOW_MAJOR.value,
    Tier.UNPLACED.value,
)
MIXED_TIER = "mixed"

#: Printed above every pooled figure, in full, every time. CLAUDE.md: *"Never
#: report a pooled headline across the whole of Division I."*
POOLED_CAVEAT = (
    "Pooled across every tier. **This is never the headline.** High-major, "
    "mid-major and low-major are three different distributions and this lab "
    "exists because the third is plausibly priced with less attention; a "
    "pooled row is printed only alongside its tier rows, and only so the "
    "tier rows can be read against something."
)

#: Exit codes, so a workflow can tell the failures apart. The weekly loop
#: reports any non-zero as a failed step and prints the tail, which is the
#: signal a broken refit should produce.
EXIT_OK = 0
EXIT_NOTHING_TO_FIT = 2
EXIT_NO_SCHEDULE = 3
EXIT_PRIOR_WEIGHT_NOT_MONOTONE = 4
EXIT_WALK_FORWARD_LEAK = 5
EXIT_STALE_RECORD = 6


class NothingToFit(RuntimeError):
    """A precondition is absent, so nothing was fitted and nothing was written."""


# --------------------------------------------------------------------------
# Loading, and refusing
# --------------------------------------------------------------------------


def load_team_games(processed_dir: Path, competition: Competition) -> pd.DataFrame:
    """The fit population, or a refusal naming the file that is missing.

    Refused rather than defaulted. A fit handed an empty frame does not raise:
    `ratings.fit` returns every team at its prior with a prior weight of 1.0,
    which is a *correct* answer to a question nobody asked, and the report built
    on it would print a league efficiency, a connectivity diagnostic and a
    tidy set of tier rows with nothing anywhere saying the table was empty.
    """
    path = Path(processed_dir) / competition.output_name(REQUIRED_TABLE, ".csv")
    if not path.is_file():
        raise NothingToFit(
            f"{path} does not exist. Run `scripts/build_datasets.py` first — "
            "this program fits on the processed team-games table and does not "
            "build it. Nothing was fitted and no report was written, because a "
            "fit report over no games still prints a league mean and a set of "
            "tier rows, and nothing about it looks wrong."
        )
    frame = pd.read_csv(path, low_memory=False)
    if frame.empty:
        raise NothingToFit(
            f"{path} exists and holds no rows. That is a build that started and "
            "produced nothing, which is a different fault from a season that "
            "has not been played yet — and this program refuses to print a fit "
            "over either."
        )
    missing = [
        column
        for column in (
            "game_id",
            "season",
            "slate_date",
            "team_id",
            "opponent_id",
            "home_away",
            "venue_state",
            "game_state",
            "team_score",
            "margin",
            "total",
            "periods",
            "possessions_estimated",
        )
        if column not in frame.columns
    ]
    if missing:
        raise NothingToFit(
            f"{path} is missing {missing}. A missing column read as a zero is "
            "how the football lab's backtest reported zero bets and had that "
            "read as a finding. Nothing is defaulted and nothing was fitted."
        )
    return frame


def load_player_games(processed_dir: Path, competition: Competition) -> pd.DataFrame:
    """Player rows for the roster terms, or an empty frame and a stated absence.

    Optional on purpose, and the difference matters: with the table the prior
    carries returning minutes, incoming transfers and their level adjustment;
    without it the prior falls back to last season's rating carried forward,
    which `RosterEvidence` calls *"the honest answer, not a degraded one"*. What
    is not acceptable is a run that quietly fits the weaker prior and reports
    the stronger one, so the record carries `player_games_available` and the
    report says which prior produced its numbers.
    """
    path = Path(processed_dir) / competition.output_name(PLAYER_TABLE, ".csv")
    if not path.is_file():
        return pd.DataFrame(columns=list(PLAYER_COLUMNS))
    header = list(pd.read_csv(path, nrows=0).columns)
    wanted = [c for c in PLAYER_COLUMNS if c in header]
    if "athlete_id" not in wanted or "minutes" not in wanted:
        return pd.DataFrame(columns=list(PLAYER_COLUMNS))
    return pd.read_csv(path, usecols=wanted, low_memory=False)


def load_schedules(seasons, raw_dir: Path | None) -> dict:
    """The cached hoopR schedules, keyed by season.

    Venue state, locality and the conference walk that places a team in a tier
    all come off the schedule, and a season without one contributes none of
    them. `ratings._cached_schedule` raises with the path and the fetch command
    when a file is absent; that is re-raised as this program's own refusal
    rather than caught and worked around, because a fit whose earlier seasons
    have no local team on any game is the arrangement that made `_season_fit`
    raise `Singular matrix` on 2019, 2020 and 2021 —
    `tests/test_ratings_fit_is_well_posed.py` is the record of it.
    """
    out: dict = {}
    for season in sorted(seasons):
        # `_cached_schedule` is private and is called rather than reimplemented,
        # for the same reason `run_price_backtest.py` imports two private names
        # out of `forward_evidence`: it is the one place that knows where a
        # season's parquet lives and what to say when it does not, and a second
        # reader of the same file is a second thing that can disagree about the
        # path. `matchups_for` reads it through this function too, so a fit
        # produced here sees exactly the schedule a card would.
        out[int(season)] = R._cached_schedule(int(season), raw_dir)
    return out


def seasons_to_fit(frame: pd.DataFrame, requested: list[int]) -> list[int]:
    """Which seasons this run fits, and a refusal when the filter matches none.

    The default is the **latest season the table actually holds a countable
    game for**, not today's season. During the season those are the same thing;
    in September they are not, and a weekly loop that refits a season with no
    games would report a fit over an empty frame every Monday of the off-season.
    """
    available = sorted(
        {
            int(s)
            for s in pd.to_numeric(
                frame.loc[
                    frame["game_state"].astype(str) == "countable", "season"
                ],
                errors="coerce",
            )
            .dropna()
            .unique()
        }
    )
    if not available:
        raise NothingToFit(
            "The processed team-games table holds no countable game in any "
            "season. Every row is a non-D-I opponent or an unclassifiable "
            "fixture, so there is nothing to fit and nothing was written."
        )
    if not requested:
        return [available[-1]]
    wanted = [s for s in requested if s in available]
    if not wanted:
        raise NothingToFit(
            f"No countable game survives the season filter {sorted(requested)}. "
            f"The table holds {available}. A filter matching nothing is a "
            "refusal, never an empty measurement."
        )
    return wanted


# --------------------------------------------------------------------------
# The walk-forward fit
# --------------------------------------------------------------------------


@dataclass
class SeasonFit:
    """One season's walk-forward run: every day's diagnostics, every game priced.

    Kept as two frames rather than one because they answer different questions
    at different grains — `days` is one row per fit and `games` is one row per
    game the fit was asked about — and because the walk-forward stamp lives on
    the game rows, which is what `assert_walk_forward` reads.

    The measurement fields below are filled in by `main` after the walk-forward
    finishes, and they are **declared here rather than attached on the fly**.
    An attribute a dataclass never declared is one `build_record` can ask for
    and get an `AttributeError` from on the day somebody reorders two lines —
    or, worse, one that a `getattr(..., None)` reads as an empty section, which
    is how the football lab's backtest turned a column it had never built into
    the finding that its model never disagreed enough.
    """

    season: int
    days: pd.DataFrame = field(default_factory=pd.DataFrame)
    games: pd.DataFrame = field(default_factory=pd.DataFrame)
    prior: R.Prior | None = None
    prepared: R.PreparedGames | None = None
    final: R.Ratings | None = None
    tier_of: dict = field(default_factory=dict)
    connectivity_timeline: list = field(default_factory=list)
    decay: dict = field(default_factory=dict)
    per_tier: list = field(default_factory=list)
    venue_audit: list = field(default_factory=list)
    measured_home_advantage: list = field(default_factory=list)
    seam_comparison: list = field(default_factory=list)
    tier_leak: dict = field(default_factory=dict)
    refusals: list = field(default_factory=list)


def fit_one_season(
    *,
    season: int,
    prepared: R.PreparedGames,
    schedules: dict,
    player_games: pd.DataFrame,
    competition: Competition,
    output_dir: Path,
) -> SeasonFit:
    """Refit on every slate day of one season, and price that day's games.

    The order is the whole point:

    1. the **prior** is built once, from seasons strictly earlier than this one,
       exactly as `Prior`'s docstring requires — *"prepared once per season,
       never inside the daily loop"*. Nothing inside it moves during the season
       except the roster evidence, and that moves because roster information
       genuinely arrives: `RosterEvidence.share_as_of(day)` reads only athletes
       who had already appeared before that morning, so the object may be built
       once and cut at use;
    2. the **tier table** is built from those same earlier seasons, which is
       `conferences.tier_table`'s own rule and is *not* what the seam does —
       see `tier_leak` below, which measures the difference;
    3. `price_backtest.walk_forward` supplies each day's history, cut strictly
       earlier than the day, and stamps every returned row with the last game
       day the fit was allowed to see.

    Every game gets a row whether or not it was priced. A refusal is an honest
    output and `models/ratings.py` says so in as many words; dropping the
    refused games would make the report describe the priced fraction as if it
    were the board.
    """
    rows = prepared.rows
    season_rows = rows[rows["season"] == season]
    if season_rows.empty:
        return SeasonFit(season=season)

    # Strictly earlier seasons, and **only the prior window's**. Two separate
    # reasons, and the second was found by running:
    #
    # * strictly earlier, because that is `conferences.tier_table`'s own rule.
    #   The seam builds this table over every season it holds a schedule for,
    #   the priced one included, and teams change tier when it does — counted in
    #   `tier_leak`;
    # * only the window, because otherwise the table depends on how many seasons
    #   the run **happened to load**. Fitting 2026 alone gave a three-season
    #   table and fitting `--seasons 2024 2025 2026` gave 2026 a five-season one,
    #   which moved teams between tiers and moved the per-tier rows with them. A
    #   season's numbers must not depend on what else was in the same command.
    #   `PRIOR_WINDOW_SEASONS` is the bound the prior already uses, with the
    #   reason `models/ratings.py` gives for it: *"enough that a venue has
    #   forty-odd home games in the window, few enough that a programme five
    #   years ago is not evidence about this one."*
    earlier = {
        s: sched
        for s, sched in schedules.items()
        if season - R.PRIOR_WINDOW_SEASONS <= s < season
    }
    tiers = (
        tier_table(earlier, tuple(sorted(earlier)))
        if earlier
        else tier_table({season: schedules[season]}, (season,))
    )
    prior = R.prepare_prior(
        prepared,
        season=season,
        tiers=tiers,
        schedules=earlier or schedules,
        player_games=player_games if not player_games.empty else None,
    )

    # One row per game, from the home side, so a game is one observation. The
    # home and away rows of one game carry equal-and-opposite margins and the
    # same total; counting both would halve every standard error of something
    # measured once.
    fixtures = season_rows[
        season_rows["home_away"].astype(str).str.lower() == "home"
    ].copy()
    if fixtures.empty:
        return SeasonFit(season=season)
    fixtures["event_id"] = fixtures["game_id"].astype(str)
    fixtures["slate_date"] = fixtures["slate_date"].astype(str)

    diagnostics: list[dict] = []
    # The previous fit day's prior weights, so each day can report how many
    # **individual teams** moved the wrong way rather than only how the median
    # moved. The two are different questions and the answer to the second does
    # not imply the answer to the first — see `decay_check`.
    previous_weight: dict = {}
    previous_teams: set = set()

    def fit_day(*, day: str, history: pd.DataFrame, prices: pd.DataFrame):
        ratings = R.fit(
            history,
            prior=prior,
            as_of=day,
            season=season,
            competition=competition,
            output_dir=output_dir,
        )
        quantiles = ratings.prior_weight_distribution((0.1, 0.25, 0.5, 0.75, 0.9))
        graph = ratings.graph

        teams_now = {team for _component, team in ratings.prior_weight}
        rises: dict[str, dict] = {
            component: {"teams": 0, "largest": 0.0, "worst_team": None}
            for component in COMPONENTS
        }
        for (component, team), value in ratings.prior_weight.items():
            was = previous_weight.get((component, team))
            if was is None or component not in rises:
                continue
            step = float(value) - float(was)
            if step > DECAY_TOLERANCE:
                entry = rises[component]
                entry["teams"] += 1
                if step > entry["largest"]:
                    entry["largest"] = step
                    entry["worst_team"] = team
        added = len(teams_now - previous_teams) if previous_teams else 0
        previous_weight.clear()
        previous_weight.update(ratings.prior_weight)
        previous_teams.clear()
        previous_teams.update(teams_now)

        diagnostics.append(
            {
                "day": str(day),
                "season": int(season),
                "priced_through": ratings.priced_through,
                "games": int(ratings.games),
                "team_games": int(ratings.team_games),
                "teams": int(len(ratings.offence)),
                "league_efficiency": float(ratings.league_efficiency),
                "league_tempo": float(ratings.league_tempo),
                "residual_sd": float(ratings.residual_sd),
                "prior_weight": {
                    component: {
                        str(q): float(v) for q, v in sorted(quantiles[component].items())
                    }
                    for component in COMPONENTS
                },
                "teams_added": int(added),
                "per_team_rises": rises,
                "connectivity": {
                    "teams": int(graph.teams),
                    "components": int(graph.components),
                    "largest_component": (
                        int(max(graph.component_sizes.values()))
                        if graph.component_sizes
                        else 0
                    ),
                    "median_resistance": _finite(
                        graph.resistance_quantiles((0.5,))[0.5]
                    ),
                    "priceable_share": float(graph.priceable_share()),
                    "fiedler_value": float(graph.fiedler_value),
                },
            }
        )

        out = []
        for record in prices.to_dict("records"):
            # `pd.NA`, not `None`, is what a missing local side looks like in a
            # column `prepare` builds — and `matchup` tests `is None` before it
            # compares the local side to the two participants, so a `pd.NA`
            # would sail past the quasi-neutral refusal and then raise on
            # `pd.NA == home_team_id`. `matchups_for` never meets this because
            # it reads its local side out of a plain dict. Normalised here
            # rather than caught, because the exception would land on one game
            # in a season and read as a crash rather than as a wrong answer.
            game = R.matchup(
                ratings,
                home_team_id=record["team_id"],
                away_team_id=record["opponent_id"],
                venue_state=str(record["venue_state"]),
                local_team_id=_or_none(record.get("local_team_id")),
                venue_id=_or_none(record.get("venue_id")),
                event_id=str(record["event_id"]),
            )
            out.append(
                {
                    "event_id": str(record["event_id"]),
                    "game_id": record["game_id"],
                    "season": int(season),
                    "home_team_id": record["team_id"],
                    "away_team_id": record["opponent_id"],
                    "venue_state": str(record["venue_state"]),
                    "home_tier": game.home_tier,
                    "away_tier": game.away_tier,
                    "priceable": bool(game.priceable),
                    "unpriceable_reason": game.unpriceable_reason,
                    "effective_resistance": _finite(game.effective_resistance),
                    "prior_weight": (
                        float(game.prior_weight)
                        if game.prior_weight is not None
                        else float("nan")
                    ),
                    "predicted_margin": (
                        float(game.expected_margin) if game.priceable else float("nan")
                    ),
                    "predicted_total": (
                        float(game.expected_total) if game.priceable else float("nan")
                    ),
                    "actual_margin": float(record["margin"]),
                    "actual_total": float(record["total"]),
                    "possessions": float(record["game_possessions"]),
                }
            )
        return pd.DataFrame(out)

    priced = PB.walk_forward(
        fixtures[
            [
                "event_id",
                "slate_date",
                "game_id",
                "team_id",
                "opponent_id",
                "venue_state",
                "local_team_id",
                "venue_id",
                "margin",
                "total",
                "game_possessions",
            ]
        ],
        season_rows,
        price_day=fit_day,
    )
    # Checked on the stamp rather than trusted from the code path, because the
    # code path is exactly what was wrong in the lab this guard is ported from.
    PB.assert_walk_forward(priced)

    days = pd.DataFrame(diagnostics).sort_values("day").reset_index(drop=True)
    final = R.fit(
        season_rows,
        prior=prior,
        as_of=_day_after(str(season_rows["slate_date"].astype(str).max())),
        season=season,
        competition=competition,
        output_dir=output_dir,
    )
    return SeasonFit(
        season=season,
        days=days,
        games=priced,
        prior=prior,
        prepared=prepared,
        final=final,
        tier_of={team: prior.tier_of(team) for team in final.offence},
    )


def _day_after(day: str) -> str:
    """The morning after a slate day, `YYYY-MM-DD`.

    `ratings.fit` raises when any history row is dated **on** `as_of`, so a
    fit that is meant to see the whole season has to be asked for the day after
    its last game rather than for its last game. Writing that as a helper rather
    than inline is not tidiness: the obvious `as_of=last_day` raises, and the
    obvious fix — filtering the last day out — silently drops a day of games
    from the end-of-season fit and nothing about the result looks wrong.
    """
    return (pd.Timestamp(str(day)) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")


def _or_none(value):
    """`pd.NA`, `NaN` and `None` all become `None`. Everything else passes through.

    Three spellings of *absent* reach this program — `None` from a dict lookup,
    `numpy.nan` from a float column, `pandas.NA` from an object column — and
    `models/ratings.py` tests for exactly one of them. See the call site.
    """
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        return value
    return value


def _finite(value):
    """A float, or `None` when it is not finite. A record is not a float dump.

    `json.dumps` writes `Infinity` and `NaN`, neither of which is JSON, and
    every strict reader rejects both. An effective resistance of infinity is the
    *commonest* value on the opening Monday — it is what the refusal is made of
    — so leaving it as a float would make the record unreadable by anything but
    Python, and re-rendering the report is supposed to be free.
    """
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _jsonable(value):
    """The record, made of things JSON has: no numpy scalars, no `inf`, no `NA`.

    Applied to the whole record before it is either written or rendered, so the
    in-memory report and the one `--rebuild-report-only` produces from the file
    are the same string. Sanitising only on the way to disk would give two
    reports that differ in exactly the cells where a number was missing — which
    is the set of cells a reader is most likely to be checking.
    """
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        return _finite(value)
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return value


# --------------------------------------------------------------------------
# Measurements the fitted numbers are read against
# --------------------------------------------------------------------------


def decay_check(
    days: pd.DataFrame,
    *,
    printed: list[str],
    months: tuple[str, ...] = DECAY_MONTHS,
) -> dict:
    """Whether the prior's share of a rating falls the way it is supposed to.

    Cooper's rule is that the prior's weight is reported in every price *so the
    card can never present a November number as if it were a February one*. The
    rule is only worth anything if the number behaves, so this checks it rather
    than asserting it, over November through February, and a failure ends the
    run non-zero.

    **The first version of this check was wrong, and the way it was wrong is
    worth keeping.** It asserted that the median prior weight falls between
    every pair of consecutive slate days, and ran it on 2025-26: 4 rises in
    offence, 5 in defence, 3 in tempo out of 114 steps, none larger than
    0.00027. Two things produce them and neither is the ridge running backwards:

    * the median is an **order statistic over a set that grows**. One team
      joined the fit on 2025-11-04 — a programme with no previous season, so it
      is absent from the prior and enters the index only when it first plays —
      and a member arriving at a weight near 1.0 shifts every rank above it;
    * `prior_weight` is the row sum of `A⁻¹Λ`, and `A⁻¹` has **negative
      off-diagonal entries**. A team's own share therefore depends on games
      played by teams it is connected to, not only on its own, so it is not a
      monotone function of its own game count. Measured on the same season, the
      largest single-team rise is 0.055 in tempo and 0.011 in offence.

    That is a property of a coupled ridge, not a defect, and asserting it away
    would have been a test that could only be made to pass by weakening it. So
    the check now asks the question the rule actually asks, in three parts:

    1. **the printed series** — the days the report tabulates — must fall at
       every step. This is what a reader sees, and it is the claim the report
       makes;
    2. **the day-to-day median** may wobble, but never by as much as
       :data:`DECAY_MATERIAL`, which is the resolution this quantity is already
       rendered at everywhere it appears;
    3. **individual teams** are counted and the worst rise is reported, so that
       the coupling above is a number in the record rather than a paragraph in
       a docstring.

    Parts 1 and 2 decide the run. Part 3 is reported and decides nothing,
    because nothing declared in advance says what it should be.
    """
    if days.empty:
        return {"checked": False, "note": "no fit day was produced", "components": {}}
    window = days[days["day"].astype(str).str[5:7].isin(months)]
    if len(window) < 2:
        return {
            "checked": False,
            "note": (
                f"{len(window)} fit day(s) fall in months {list(months)}, which "
                "is not enough to check a decay between consecutive days"
            ),
            "components": {},
        }
    shown = window[window["day"].astype(str).isin(list(printed))]
    out: dict = {
        "checked": True,
        "days": int(len(window)),
        "printed_days": int(len(shown)),
        "months": list(months),
        "material_rise": DECAY_MATERIAL,
        "teams_added": int(pd.to_numeric(window["teams_added"], errors="coerce").sum()),
        "components": {},
    }
    monotone = True
    for component in COMPONENTS:
        printed_rises = _rises(shown, component)
        daily_rises = _rises(window, component)
        material = [r for r in daily_rises if r["rose_by"] > DECAY_MATERIAL]
        series = [
            float(row["prior_weight"][component]["0.5"])
            for row in window.to_dict("records")
        ]
        per_team = [
            row["per_team_rises"].get(component, {}) for row in window.to_dict("records")
        ]
        teams_risen = sum(int(entry.get("teams", 0)) for entry in per_team)
        largest_team = max(
            (float(entry.get("largest", 0.0)) for entry in per_team), default=0.0
        )
        # Every team compared against itself on every step but the first: the
        # denominator the rise count has to be read against, or a large number
        # of tiny wobbles reads as a large number of broken teams.
        team_day_steps = int(
            pd.to_numeric(window["teams"], errors="coerce").iloc[1:].sum()
        )
        out["components"][component] = {
            "first_day": str(window.iloc[0]["day"]),
            "last_day": str(window.iloc[-1]["day"]),
            "first": series[0],
            "last": series[-1],
            "day_steps": int(len(window) - 1),
            "printed_monotone": not printed_rises,
            "printed_rises": printed_rises[:10],
            "daily_rise_count": len(daily_rises),
            "team_day_steps": team_day_steps,
            "team_rise_share": (
                float(teams_risen / team_day_steps) if team_day_steps else 0.0
            ),
            "daily_largest_rise": max(
                (r["rose_by"] for r in daily_rises), default=0.0
            ),
            "material_rises": material[:10],
            "material_rise_count": len(material),
            "team_rise_steps": teams_risen,
            "largest_team_rise": largest_team,
        }
        monotone = monotone and not printed_rises and not material
    out["monotone"] = monotone
    return out


def _rises(frame: pd.DataFrame, component: str) -> list[dict]:
    """Every step where the median prior weight for `component` went up."""
    rows = frame.to_dict("records")
    out: list[dict] = []
    for index in range(1, len(rows)):
        step = float(rows[index]["prior_weight"][component]["0.5"]) - float(
            rows[index - 1]["prior_weight"][component]["0.5"]
        )
        if step > DECAY_TOLERANCE:
            out.append(
                {
                    "from_day": str(rows[index - 1]["day"]),
                    "to_day": str(rows[index]["day"]),
                    "rose_by": float(step),
                }
            )
    return out


def per_tier_fits(fit: SeasonFit, *, looks: int) -> list[dict]:
    """One row per tier: what was fitted, and how wrong it was out of sample.

    Two different kinds of number, deliberately in one table.

    The **fitted** columns describe the model at the end of the season: how many
    teams the tier holds, how much of their rating is still the preseason prior,
    and how far apart the tier's teams are. The **measured** columns are
    walk-forward: every game is scored by the fit that existed the morning of
    the game and by no other, so the error is out of sample by construction.

    A game is attributed to a tier only when **both** teams are in it. A
    high-major hosting a low-major is neither tier's game and is reported as
    `mixed`; folding it into the home team's tier is how a buy-game schedule
    ends up describing a conference.

    Every row carries its `n`, and the pooled row is printed only beside these
    and never instead of them.
    """
    if fit.games.empty or fit.final is None:
        return []
    games = fit.games.copy()
    games["bucket"] = np.where(
        games["home_tier"] == games["away_tier"], games["home_tier"], MIXED_TIER
    )
    priced = games[games["priceable"]].copy()
    priced["margin_error"] = priced["predicted_margin"] - priced["actual_margin"]
    priced["total_error"] = priced["predicted_total"] - priced["actual_total"]

    weights = _prior_weight_by_tier(fit)
    spreads = _rating_spread_by_tier(fit)
    teams = _teams_by_tier(fit)

    out: list[dict] = []
    for bucket in (*TIER_ORDER, MIXED_TIER):
        offered = games[games["bucket"] == bucket]
        if offered.empty:
            continue
        scored = priced[priced["bucket"] == bucket]
        out.append(
            _tier_row(
                bucket,
                offered=offered,
                scored=scored,
                # `mixed` is a bucket of games and not a set of teams, so its
                # team count is **absent** rather than zero. A zero in that cell
                # would read as "no team is in this tier", which is a claim, and
                # the cell renders as an em dash instead.
                teams=None if bucket == MIXED_TIER else teams.get(bucket, 0),
                weights={} if bucket == MIXED_TIER else weights.get(bucket, {}),
                spread={} if bucket == MIXED_TIER else spreads.get(bucket, {}),
                looks=looks,
            )
        )
    if out:
        out.append(
            _tier_row(
                "POOLED",
                offered=games,
                scored=priced,
                teams=int(len(fit.final.offence)),
                weights=_prior_weight_all(fit),
                spread=_rating_spread_all(fit),
                looks=looks,
            )
        )
    return out


def _tier_row(
    label: str,
    *,
    offered: pd.DataFrame,
    scored: pd.DataFrame,
    teams: int,
    weights: dict,
    spread: dict,
    looks: int,
) -> dict:
    margin = mean_interval(scored, "margin_error", looks=looks)
    total = mean_interval(scored, "total_error", looks=looks)
    return {
        "tier": label,
        "teams": None if teams is None else int(teams),
        "games_offered": int(len(offered)),
        "games_priced": int(len(scored)),
        "priced_share": float(len(scored) / len(offered)) if len(offered) else 0.0,
        "median_prior_weight": {c: weights.get(c, float("nan")) for c in COMPONENTS},
        "rating_sd": {c: spread.get(c, float("nan")) for c in COMPONENTS},
        "margin_bias": margin,
        "margin_absolute_error": (
            float(scored["margin_error"].abs().mean()) if not scored.empty else float("nan")
        ),
        "total_bias": total,
        "total_absolute_error": (
            float(scored["total_error"].abs().mean()) if not scored.empty else float("nan")
        ),
    }


def mean_interval(frame: pd.DataFrame, column: str, *, looks: int) -> dict:
    """A mean and its two-way clustered 95% interval, as plain record data.

    `stats.interval_two_way` is the lab's one implementation of a clustered
    interval and it is used here rather than a second copy — *"two copies of a
    formula drift, and the direction they drift in is never the conservative
    one."* It is ROI-shaped, so the quantity being averaged is handed to it as
    `profit_units` and one row is one observation; the arithmetic it does to a
    ratio of sums over clusters is exactly the arithmetic a clustered mean
    wants, and it reports the wider of the game- and day-clustered answers.

    Clustering matters here for the same reason it matters to a return. A
    hundred-game Tuesday is priced by **one** fit, so the day's errors share
    whatever that fit got wrong, and treating them as a hundred independent
    observations understates the interval by roughly the square root of the
    slate — which is the football lab's forward-ledger defect, arriving by a
    different door.
    """
    empty = _interval_record(S.RoiInterval(0.0, 0.0, 0.0, 0, 0, looks=looks))
    if frame.empty or column not in frame.columns:
        return empty
    usable = frame[pd.to_numeric(frame[column], errors="coerce").notna()]
    if usable.empty:
        return empty
    return _interval_record(
        S.interval_two_way(
            usable.assign(
                profit_units=pd.to_numeric(usable[column], errors="coerce")
            ),
            looks=looks,
        )
    )


def mean_by_cluster(
    frame: pd.DataFrame, column: str, *, cluster: str, unit: str, looks: int
) -> dict:
    """A mean and a 95% interval clustered on one named unit.

    Used where `interval_two_way`'s rule — compute the game- and day-clustered
    answers and take the wider — has nothing to choose between. The venue audit
    has one observation per **pair of teams**, already averaged over that pair's
    two meetings, and the only other candidate unit is the season: three of
    them in a prior window, which is a standard error on two degrees of freedom.
    Taking the wider of a credible estimate and an unestimable one is not
    conservatism, it is reporting noise as caution, so the unit is named here
    and printed in the record beside every figure it produced.
    """
    empty = _interval_record(
        S.RoiInterval(0.0, 0.0, 0.0, 0, 0, looks=looks, cluster_unit=unit)
    )
    if frame.empty or column not in frame.columns:
        return empty
    usable = frame[pd.to_numeric(frame[column], errors="coerce").notna()]
    if usable.empty:
        return empty
    values = pd.to_numeric(usable[column], errors="coerce")
    per_cluster = usable.assign(_value=values).groupby(cluster).agg(
        profit=("_value", "sum"), bets=("_value", "size")
    )
    return _interval_record(
        S.interval_by_cluster(per_cluster, looks=looks, cluster_unit=unit)
    )


def _interval_record(interval: S.RoiInterval) -> dict:
    """One interval, flattened. `render` never touches a `RoiInterval`.

    The record has to survive a JSON round trip and be renderable by a function
    that recomputes nothing, so the dataclass's derived properties are read
    once, here, and stored. `price_backtest.interval_from_row` rebuilds one from
    a row of exactly this shape when a caller needs the object back.
    """
    return {
        "mean": float(interval.roi),
        "low": float(interval.low),
        "high": float(interval.high),
        "n": int(interval.bets),
        "clusters": int(interval.clusters),
        "cluster_unit": interval.cluster_unit,
        "standard_error": float(interval.standard_error),
        "looks": int(interval.looks),
        "adjusted_low": float(interval.adjusted_low),
        "adjusted_high": float(interval.adjusted_high),
        "enough_evidence": bool(interval.enough_evidence),
        # `survives_correction` and not "excludes zero": it is the family-wise
        # corrected interval that has to exclude zero, and it also requires the
        # declared sample floor. The two are one predicate in `stats.py` and
        # splitting them here would be a second copy that could disagree.
        "survives_correction": bool(interval.survives_correction),
    }


def _prior_weight_by_tier(fit: SeasonFit) -> dict:
    out: dict = {}
    for component in COMPONENTS:
        buckets: dict[str, list[float]] = {}
        for (name, team), value in fit.final.prior_weight.items():
            if name != component:
                continue
            buckets.setdefault(fit.tier_of.get(team, Tier.UNPLACED.value), []).append(
                float(value)
            )
        for tier, values in buckets.items():
            out.setdefault(tier, {})[component] = float(np.median(values))
    return out


def _prior_weight_all(fit: SeasonFit) -> dict:
    distribution = fit.final.prior_weight_distribution((0.5,))
    return {c: float(distribution[c][0.5]) for c in COMPONENTS}


def _rating_spread_by_tier(fit: SeasonFit) -> dict:
    out: dict = {}
    for component, values in (
        (R.OFFENCE, fit.final.offence),
        (R.DEFENCE, fit.final.defence),
        (R.TEMPO, fit.final.tempo),
    ):
        buckets: dict[str, list[float]] = {}
        for team, value in values.items():
            buckets.setdefault(fit.tier_of.get(team, Tier.UNPLACED.value), []).append(
                float(value)
            )
        for tier, group in buckets.items():
            out.setdefault(tier, {})[component] = (
                float(np.std(group, ddof=1)) if len(group) > 1 else float("nan")
            )
    return out


def _rating_spread_all(fit: SeasonFit) -> dict:
    return {
        component: (
            float(np.std(list(values.values()), ddof=1)) if len(values) > 1 else float("nan")
        )
        for component, values in (
            (R.OFFENCE, fit.final.offence),
            (R.DEFENCE, fit.final.defence),
            (R.TEMPO, fit.final.tempo),
        )
    }


def _teams_by_tier(fit: SeasonFit) -> dict:
    counts: dict[str, int] = {}
    for team in fit.final.offence:
        tier = fit.tier_of.get(team, Tier.UNPLACED.value)
        counts[tier] = counts.get(tier, 0) + 1
    return counts


# --------------------------------------------------------------------------
# The venue audit
# --------------------------------------------------------------------------


def reciprocal_home_advantage(
    rows: pd.DataFrame, *, tiers, seasons: tuple[int, ...], looks: int
) -> list[dict]:
    """Home advantage from pairs that met at **both** home venues, by tier.

    The estimator is subtraction rather than regression, and that is its whole
    value. If A and B meet at A's arena and at B's, then

        margin(A at A) = (A − B) + H        margin(B at B) = (B − A) + H

    and the mean of the two is `H` with every team effect cancelling **exactly**
    — no shrinkage, no design matrix, no assumption that the opponent's rating
    was well identified. `ratings._venue_effects` fits its tier effects on the
    residuals of a season fit whose second stage carries no team effects at all,
    so the two are genuinely independent instruments for one quantity, which is
    the only reason comparing them is worth anything.

    A pair is attributed to a tier only when both teams are in it; pairs across
    tiers are their own bucket, because there is no honest answer to *whose*
    home effect a Duke-at-Davidson pair measures.

    **What this estimator's population is, stated rather than glossed:**
    reciprocal home-and-home pairs are overwhelmingly conference games. It says
    nothing about the home advantage in a November non-conference game, and if
    those differ then the fitted number and this one are measuring two different
    things rather than disagreeing about one. That possibility is the reason
    this section reports a comparison and never a correction.
    """
    if rows.empty:
        return []
    frame = rows[
        (rows["season"].isin(list(seasons)))
        & (rows["venue_state"].astype(str) == "home")
        & (rows["is_local"].astype(bool))
    ]
    if frame.empty:
        return []
    frame = frame.assign(
        pair=[
            "|".join(sorted((str(a), str(b))))
            for a, b in zip(frame["team_id"], frame["opponent_id"])
        ]
    )
    by_host = (
        frame.groupby(["season", "pair", "team_id"])
        .agg(
            margin=("margin", "mean"),
            possessions=("game_possessions", "mean"),
            games=("game_id", "size"),
        )
        .reset_index()
    )
    hosts = by_host.groupby(["season", "pair"])["team_id"].transform("nunique")
    reciprocal = by_host[hosts == 2]
    if reciprocal.empty:
        return []

    def tier_of(team) -> str:
        return tiers.tier_for(team).value if tiers is not None else Tier.UNPLACED.value

    pairs = (
        reciprocal.groupby(["season", "pair"])
        .agg(
            margin=("margin", "mean"),
            possessions=("possessions", "mean"),
            games=("games", "sum"),
        )
        .reset_index()
    )
    left = pairs["pair"].str.split("|").str[0]
    right = pairs["pair"].str.split("|").str[1]
    pairs = pairs.assign(
        left_tier=[tier_of(_as_team(t)) for t in left],
        right_tier=[tier_of(_as_team(t)) for t in right],
    )
    pairs = pairs.assign(
        bucket=np.where(
            pairs["left_tier"] == pairs["right_tier"], pairs["left_tier"], MIXED_TIER
        ),
        per_100=100.0 * pairs["margin"] / pairs["possessions"],
        # A pair meeting in two different seasons is two observations, because
        # the two rosters are two rosters. The key carries the season for that
        # reason and it is not a formatting detail.
        cluster=pairs["season"].astype(str) + ":" + pairs["pair"],
    )

    def bucket_row(label: str, group: pd.DataFrame) -> dict:
        return {
            "tier": label,
            "pairs": int(len(group)),
            "games": int(group["games"].sum()),
            "seasons": sorted({int(s) for s in group["season"]}),
            "per_100": mean_by_cluster(
                group, "per_100", cluster="cluster", unit="pair", looks=looks
            ),
            "points": mean_by_cluster(
                group, "margin", cluster="cluster", unit="pair", looks=looks
            ),
        }

    out: list[dict] = []
    for bucket in (*TIER_ORDER, MIXED_TIER):
        group = pairs[pairs["bucket"] == bucket]
        if group.empty:
            continue
        out.append(bucket_row(bucket, group))
    if out:
        out.append(bucket_row("POOLED", pairs))
    return out


#: The refusal families `models/ratings.py` can produce, matched on a phrase
#: that is stable across days. The reasons themselves embed that morning's
#: component count and that pair's resistance, so grouping on the raw string
#: turns one refusal into a hundred rows that each read as a separate finding
#: and are then truncated mid-word — which is what the first run of this report
#: printed. The example is kept beside the count so the detail is not lost.
REFUSAL_FAMILIES: tuple[tuple[str, str], ...] = (
    (
        "different components",
        "the two teams are in different components of the games-played graph",
    ),
    (
        "effective resistance",
        "less connecting evidence than one head-to-head meeting (effective "
        "resistance at or above the bar)",
    ),
    (
        "played no countable game",
        "a team has played no countable game this season, so its rating is the "
        "preseason prior and nothing else",
    ),
    (
        "quarantined",
        "the venue state is unknown or contradictory",
    ),
    (
        "cannot tell whose",
        "a quasi-neutral game whose local participant could not be identified",
    ),
    (
        "outside the support",
        "a fitted efficiency outside the support of the per-possession "
        "distribution",
    ),
    ("is not a game", "a fitted tempo that is not a game"),
    ("cannot play itself", "a team cannot play itself"),
)


def refusal_families(refused: pd.DataFrame) -> list[dict]:
    """Refusals grouped by why, not by the day's arithmetic. See `REFUSAL_FAMILIES`."""
    if refused.empty:
        return []
    counts: dict[str, dict] = {}
    for reason in refused["unpriceable_reason"].astype(str):
        family = next(
            (label for needle, label in REFUSAL_FAMILIES if needle in reason),
            reason[:120],
        )
        entry = counts.setdefault(family, {"reason": family, "count": 0, "example": ""})
        entry["count"] += 1
        if not entry["example"]:
            entry["example"] = reason[:240]
    return sorted(counts.values(), key=lambda row: -row["count"])


def _as_team(text: str):
    """A team id back out of the pair key, as the type the tier table is keyed by."""
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return text


def venue_audit(fit: SeasonFit, measured: list[dict]) -> list[dict]:
    """The fitted tier home effect beside the measurement, per tier.

    Read the `inside` column first. It is not a verdict about basketball; it is
    a statement about which of the model's own numbers a reader may quote. A
    fitted effect outside a measured interval is applied to every market on
    every game of that tier, which is `CLAUDE.md`'s *"multi-point error applied
    to every market on it"* — the same sentence the quasi-neutral finding is
    filed under, and the same size of number.
    """
    if fit.prior is None:
        return []
    venue = fit.prior.venue
    by_tier = {row["tier"]: row for row in measured}
    out: list[dict] = []
    for tier in TIER_ORDER:
        row = by_tier.get(tier)
        fitted = float(venue.home_margin(tier))
        record = {
            "tier": tier,
            "fitted_per_100": fitted,
            "fitted_points_at_league_tempo": fitted
            * float(fit.final.league_tempo if fit.final else 0.0)
            / R.POSSESSION_SCALE,
            "measured": row["per_100"] if row else None,
            "pairs": int(row["pairs"]) if row else 0,
        }
        if row:
            interval = row["per_100"]
            record["inside"] = bool(interval["low"] <= fitted <= interval["high"])
            # Against the **wider** family-corrected interval as well. The raw
            # interval is the narrower one, so a fitted number can fall outside
            # it and inside the corrected one — and reporting only the raw
            # answer would call something a disagreement that the correction
            # says is not one. Both are printed and the corrected one is the
            # conservative reading.
            record["inside_corrected"] = bool(
                float(interval.get("adjusted_low", interval["low"]))
                <= fitted
                <= float(interval.get("adjusted_high", interval["high"]))
            )
            record["gap_per_100"] = fitted - float(interval["mean"])
        else:
            record["inside"] = None
            record["inside_corrected"] = None
            record["gap_per_100"] = float("nan")
        out.append(record)
    return out


# --------------------------------------------------------------------------
# The seam comparison, and the tier leak
# --------------------------------------------------------------------------


def seam_comparison(
    *,
    season: int,
    prepared: R.PreparedGames,
    prior: R.Prior,
    days: list[str],
    competition: Competition,
    output_dir: Path,
) -> list[dict]:
    """The prior's weight under this file's cut and under the seam's, per day.

    `ratings.matchups_for` hands `fit` every season of history it was given, and
    `run_price_backtest.py` gives it all of them. This refits the same days both
    ways and prints the two medians beside each other, because the difference is
    not a nuance: under the seam's convention a team's design row count on the
    opening Monday is several seasons of games rather than none, so the ridge
    toward the preseason prior is outweighed before a ball is thrown and
    `prior_weight` — the field the card prints so a November number cannot read
    as a February one — is flat and near zero all season.

    The cut here is asserted rather than assumed. Both frames are checked to
    hold nothing dated on or after the day, and `ratings.fit` raises on the same
    condition independently, so a mistake in this function cannot produce a leak
    that merely looks like a finding.
    """
    rows = prepared.rows
    season_rows = rows[rows["season"] == season]
    out: list[dict] = []
    for day in days:
        own = season_rows[season_rows["slate_date"].astype(str) < str(day)]
        pooled = rows[rows["slate_date"].astype(str) < str(day)]
        assert own.empty or str(own["slate_date"].astype(str).max()) < str(day)
        assert pooled.empty or str(pooled["slate_date"].astype(str).max()) < str(day)
        entry: dict = {"day": str(day), "season_only": {}, "pooled": {}}
        for label, frame in (("season_only", own), ("pooled", pooled)):
            ratings = R.fit(
                frame,
                prior=prior,
                as_of=str(day),
                season=season,
                competition=competition,
                output_dir=output_dir,
            )
            distribution = ratings.prior_weight_distribution((0.5,))
            entry[label] = {
                "team_games": int(ratings.team_games),
                "median_prior_weight": {
                    c: float(distribution[c][0.5]) for c in COMPONENTS
                },
            }
        out.append(entry)
    return out


def tier_leak(schedules: dict, season: int) -> dict:
    """How many teams change tier when the priced season is allowed into the table.

    `models/ratings.py` states the rule — *"conference tiers —
    `conferences.tier_table` on seasons strictly before, which is that module's
    own rule"* — and `matchups_for` builds the table over every season it holds
    a schedule for, the priced one included. A tier is not a label here: the
    home-court effect the model applies is chosen by it, and the tiers' fitted
    effects differ by several points per hundred possessions, so a team on the
    wrong side of a cut point is a multi-point error on every market on its
    home games.

    Counted rather than argued. The number is small and it is not zero, and
    which of those two it is could not be known without measuring it.
    """
    earlier = {
        s: sched
        for s, sched in schedules.items()
        if season - R.PRIOR_WINDOW_SEASONS <= s < season
    }
    if not earlier:
        return {"checked": False, "note": "no earlier season is cached"}
    including = dict(earlier)
    including[season] = schedules[season]
    before = tier_table(earlier, tuple(sorted(earlier)))
    after = tier_table(including, tuple(sorted(including)))
    teams = set(before.team_tier) | set(after.team_tier)
    changed = [
        team
        for team in teams
        if before.team_tier.get(team, Tier.UNPLACED)
        != after.team_tier.get(team, Tier.UNPLACED)
    ]
    return {
        "checked": True,
        "season": int(season),
        "teams": int(len(teams)),
        "changed": int(len(changed)),
        "share": float(len(changed) / len(teams)) if teams else 0.0,
        "strictly_before": before.summary_line(),
        "including_priced": after.summary_line(),
    }


# --------------------------------------------------------------------------
# Roster turnover, measured here
# --------------------------------------------------------------------------


def roster_turnover_rows(
    player_games: pd.DataFrame, *, seasons, division_one: set
) -> dict:
    """Turnover on the population this lab prices, and on the raw table beside it.

    `ratings.roster_turnover` takes an optional team filter and the difference
    it makes is not small, so both are reported. The unrestricted figure
    includes every team that appears in the player table — several hundred
    non-D-I programmes whose rows are sparse and whose minutes are recorded
    unevenly — and it is the figure the model's own docstring carries. The
    restricted figure covers the teams the schedule feed gives a conference to,
    which is the board this lab prices and the only population a card is ever
    produced for.

    Cooper's instruction was *"measure the current rate rather than quoting
    mine"*, and the sibling labs' numbers are deliberately absent from this file
    for that reason: hockey's turnover and football's turnover are facts about
    hockey and football.
    """
    if player_games.empty:
        return {
            "available": False,
            "note": (
                "the processed player-games table is absent, so turnover was "
                "not measured. It is reported as an absence rather than as a "
                "zero, and the prior fell back to last season's rating carried "
                "forward with no roster terms."
            ),
            "division_one": [],
            "unrestricted": [],
        }
    wanted = sorted(set(int(s) for s in seasons))
    return {
        "available": True,
        "note": "",
        "division_one_teams": int(len(division_one)),
        "division_one": R.roster_turnover(
            player_games, seasons=wanted, teams=division_one
        ),
        "unrestricted": R.roster_turnover(player_games, seasons=wanted),
    }


# --------------------------------------------------------------------------
# The record
# --------------------------------------------------------------------------


def report_days(days: pd.DataFrame) -> list[str]:
    """The subset of fit days the report tables print.

    A rendering choice and nothing more: the record holds every fit day, so
    changing this costs a `--rebuild-report-only` rather than a refit. The days
    are the ones `models/ratings.py`'s own connectivity table uses, so the two
    can be read against each other without arithmetic.
    """
    if days.empty:
        return []
    all_days = [str(d) for d in days["day"]]
    chosen = {all_days[0], all_days[-1]}
    chosen |= {d for d in all_days if int(d[8:10]) in REPORT_DAYS_OF_MONTH}
    return sorted(chosen)


def build_record(
    *,
    competition: Competition,
    seasons: list[int],
    fits: dict,
    prepared: R.PreparedGames,
    team_games_supplied: int,
    turnover: dict,
    looks: int,
    player_games_available: bool,
    generated_at: str,
    processed_dir: Path,
    raw_dir: Path,
) -> dict:
    """Every count this run made, as plain data. `render` is pure over it.

    The retention probe's rule, and it applies here with the same force it
    applies to a backtest: a report that can only be produced by re-running the
    measurement is a report nobody improves, and a hand-edited generated file
    survives exactly one re-run.
    """
    seasons_record: list[dict] = []
    for season in seasons:
        fit = fits[season]
        days = fit.days
        printed = report_days(days)
        seasons_record.append(
            {
                "season": int(season),
                "fit_days": int(len(days)),
                "first_day": str(days.iloc[0]["day"]) if not days.empty else "",
                "last_day": str(days.iloc[-1]["day"]) if not days.empty else "",
                "games_offered": int(len(fit.games)),
                "games_priced": (
                    int(fit.games["priceable"].sum()) if not fit.games.empty else 0
                ),
                "prior_summary": fit.prior.summary_line() if fit.prior else "",
                "venue_summary": fit.prior.venue.summary_line() if fit.prior else "",
                "final_summary": fit.final.summary_line() if fit.final else "",
                "venue_effect_note": fit.final.venue_effect_note if fit.final else "",
                "report_days": printed,
                "timeline": [
                    row for row in days.to_dict("records") if str(row["day"]) in printed
                ],
                "connectivity_timeline": fit.connectivity_timeline,
                "decay": fit.decay,
                "per_tier": fit.per_tier,
                "venue_audit": fit.venue_audit,
                "measured_home_advantage": fit.measured_home_advantage,
                "seam_comparison": fit.seam_comparison,
                "tier_leak": fit.tier_leak,
                "refusals": fit.refusals,
            }
        )
    return _jsonable({
        "record_version": RECORD_VERSION,
        "competition": competition.key,
        "title": competition.title,
        "generated_at": generated_at,
        "processed_dir": str(processed_dir),
        "raw_dir": str(raw_dir),
        "seasons": [int(s) for s in seasons],
        "prior_window_seasons": int(R.PRIOR_WINDOW_SEASONS),
        "team_games_supplied": int(team_games_supplied),
        "prepared_summary": prepared.summary_line(),
        "prepared_reconciles": bool(prepared.reconciles()),
        "prepared_counts": {
            "supplied": int(prepared.supplied),
            "fittable": int(len(prepared.rows)),
            "not_countable": int(prepared.not_countable),
            "venue_unknown": int(prepared.venue_unknown),
            "overtime": int(prepared.overtime),
            "periods_unknown": int(prepared.periods_unknown),
            "too_few_possessions": int(prepared.too_few_possessions),
            "quasi_local_side_unknown": int(prepared.quasi_local_side_unknown),
            "has_venue_ids": bool(prepared.has_venue_ids),
            # `PreparedGames.reconciles()` returns a boolean and this is the
            # number behind it. *"A row that vanished without appearing in a
            # count is a defect, not a decision"* — and a defect stated as
            # `False` is one nobody can size.
            "unaccounted": int(
                prepared.supplied
                - len(prepared.rows)
                - prepared.not_countable
                - prepared.venue_unknown
                - prepared.overtime
                - prepared.periods_unknown
                - prepared.too_few_possessions
            ),
        },
        "player_games_available": bool(player_games_available),
        "roster_turnover": turnover,
        "looks": int(looks),
        "correction_factor": float(S.bonferroni_factor(int(looks))),
        "minimum_sample": int(S.MINIMUM_BETS),
        "no_demonstrated_edge_phrase": S.NO_DEMONSTRATED_EDGE,
        "max_effective_resistance": float(R.MAX_EFFECTIVE_RESISTANCE),
        "minimum_game_possessions": float(R.MINIMUM_GAME_POSSESSIONS),
        "seasons_detail": seasons_record,
    })


# --------------------------------------------------------------------------
# Rendering — a pure function of the record
# --------------------------------------------------------------------------


def _n(value) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "—"


def _f(value, digits: int = 2, sign: bool = False) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(number):
        return "—"
    return f"{number:+.{digits}f}" if sign else f"{number:.{digits}f}"


def _yes_no(value) -> str:
    """`yes`, a shouted `no`, or an em dash. `None` is *not measured*, not *no*."""
    if value is None:
        return "—"
    return "yes" if value else "**no**"


def _pct(value, digits: int = 0) -> str:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return "—"
    if not math.isfinite(number):
        return "—"
    return f"{number:.{digits}%}"


def interval_cells(record: dict, digits: int = 2, minimum: int = S.MINIMUM_BETS):
    """Mean, raw interval, family-corrected interval, and the sentence.

    **Below the declared sample floor there is no number.** `price_backtest`
    has its own row renderer for exactly this reason and this one copies its
    rule rather than its code: *"a +12% return over 40 bets and a coin flip are
    the same claim at that sample size"*, and printing the figure invites
    somebody to quote it out of the row that qualifies it.

    The corrected interval is returned **beside** the raw one and not instead of
    it, which is CLAUDE.md's rule: *"family-wise correction from the experiment
    ledger's cumulative count, reported beside the raw figure."* A report that
    printed only the raw interval and then judged it against the corrected one
    would be showing a reader one number and deciding on another.
    """
    if not record or int(record.get("n", 0)) < minimum:
        return "—", "—", "—", (
            f"not enough evidence ({_n(record.get('n', 0) if record else 0)} "
            f"observations, below the {minimum:,} declared in advance)"
        )
    mean = _f(record["mean"], digits, sign=True)
    interval = (
        f"{_f(record['low'], digits, sign=True)} to "
        f"{_f(record['high'], digits, sign=True)}"
    )
    corrected = (
        f"{_f(record.get('adjusted_low'), digits, sign=True)} to "
        f"{_f(record.get('adjusted_high'), digits, sign=True)}"
    )
    words = (
        "excludes zero after the family correction"
        if record.get("survives_correction")
        else f"**{S.NO_DEMONSTRATED_EDGE}**"
    )
    return mean, interval, corrected, words


def render(record: dict) -> str:
    """The report, as a pure function of the record. No clock, no fit, no table."""
    lines: list[str] = []
    add = lines.append
    title = record.get("title") or CBB.title
    add(f"# {title} — ratings fit")
    add("")
    if record.get("generated_at"):
        add(f"Generated {record['generated_at']}.")
        add("")

    add(
        "**Nothing in this report is a return.** A fit is not a price, forecast "
        "error is not profit, and calibration can rule a model out and never "
        "in. Where an interval includes zero this report says "
        f"**{record.get('no_demonstrated_edge_phrase', S.NO_DEMONSTRATED_EDGE)}** "
        "in the lab's own words, which for a fitted quantity reads as *no "
        "demonstrated effect*. The price backtest is what decides whether any "
        "of this is worth money."
    )
    add("")
    add(
        "**Walk-forward, checked on the stamp.** Every rating that priced a "
        "game was fitted on that season's games strictly earlier than the "
        "morning of the game, every priced row carries the last game day the "
        "fit was allowed to see, and `price_backtest.assert_walk_forward` reads "
        "the stamp rather than trusting the code path — because the code path "
        "is exactly what was wrong in the lab this guard is ported from."
    )
    add("")
    add(
        f"**Sample floor: {_n(record.get('minimum_sample', S.MINIMUM_BETS))} "
        "observations.** Below it a cell prints an em dash and the words *not "
        "enough evidence*, never a figure."
    )
    add("")
    add(
        f"**Family correction: {_n(record.get('looks', 1))} cumulative "
        "hypotheses** in the experiment ledger, widening every 95% interval by "
        f"x{_f(record.get('correction_factor', 1.0))}. That is the ledger's "
        "cumulative count and never the day's."
    )
    add("")

    counts = record.get("prepared_counts", {})
    add("## The fit population, reconciled")
    add("")
    add(
        f"{_n(record.get('team_games_supplied'))} team-game rows were read from "
        f"`{record.get('processed_dir')}`, and the seasons this run fits are "
        f"{record.get('seasons')} with a prior window of "
        f"{record.get('prior_window_seasons')} earlier seasons."
    )
    add("")
    add(f"> {record.get('prepared_summary', '')}")
    add("")
    add(
        "Every exclusion is a count and not a decision. Overtime games are out "
        "because `distributions.build` appends overtime itself and fitting on "
        "final scores would count it twice; a missing period count is not "
        "evidence of a regulation finish and is excluded separately. "
        "The identity "
        + ("reconciles" if record.get("prepared_reconciles") else "**DOES NOT RECONCILE**")
        + ": "
        f"{_n(counts.get('fittable'))} fittable + {_n(counts.get('not_countable'))} "
        f"not countable + {_n(counts.get('venue_unknown'))} venue unknown + "
        f"{_n(counts.get('overtime'))} overtime + {_n(counts.get('periods_unknown'))} "
        f"period count missing + {_n(counts.get('too_few_possessions'))} below "
        f"{_f(record.get('minimum_game_possessions'), 0)} possessions = "
        f"{_n(counts.get('supplied'))} supplied."
    )
    add("")
    if counts.get("unaccounted"):
        add(
            f"**{_n(counts['unaccounted'])} row(s) reached none of those "
            "buckets.** `ratings.prepare` keeps rows whose period count equals "
            "regulation, counts the ones above it as overtime and the missing "
            "ones as unknown — and a game filed with a period count *below* "
            "regulation is in none of the three, so it leaves the fit without "
            "appearing anywhere. `PreparedGames.reconciles()` is what noticed, "
            "which is the accounting identity doing its job; the count is "
            "printed here because *a defect stated as a boolean is one nobody "
            "can size*. It is small, it is real, and it is not silent any more."
        )
        add("")
    if counts.get("quasi_local_side_unknown"):
        add(
            f"{_n(counts['quasi_local_side_unknown'])} quasi-neutral team-games "
            "have no identified local side and were fitted as neutral, which the "
            "measurement says is close to right — and it is counted here so that "
            "*close to right* is a number rather than a claim."
        )
        add("")
    if not record.get("player_games_available"):
        add(
            "**The player-games table was absent**, so the prior carries no "
            "roster terms and turnover was not measured. That is reported as an "
            "absence and never as a zero."
        )
        add("")

    for season in record.get("seasons_detail", []):
        lines.extend(_render_season(season, record))

    lines.extend(_render_turnover(record))

    add("## What this report is not")
    add("")
    add(
        "It is not evidence of an edge. `models/ratings.py` ends its own fit "
        "report with the sentence this one takes as its brief: *a table of "
        "fitted coefficients reads like a result and is not one.* Fit quality "
        "and calibration can rule a model out; only a price backtest against "
        "prices the card could actually have taken can say whether any of it "
        "would have made money, and no number here is one."
    )
    add("")
    return "\n".join(lines).rstrip() + "\n"


def _render_season(season: dict, record: dict) -> list[str]:
    lines: list[str] = []
    add = lines.append
    add(f"## Season {season['season']}")
    add("")
    add(
        f"{_n(season.get('fit_days'))} fits, one per slate day from "
        f"{season.get('first_day')} to {season.get('last_day')}. "
        f"{_n(season.get('games_priced'))} of {_n(season.get('games_offered'))} "
        "games were priced; the rest were refused and the reasons are below. "
        "A refusal is an honest output, and a game the model declines to price "
        "is a different thing from a game it prices at no value."
    )
    add("")
    add(f"> {season.get('final_summary', '')}")
    add("")
    add(f"> {season.get('prior_summary', '')}")
    add("")
    add(f"> {season.get('venue_summary', '')}")
    add("")
    add(f"Venue-level departures: {season.get('venue_effect_note', '')}.")
    add("")

    # -- the prior's weight over time ------------------------------------
    add(f"### The prior's weight over time — season {season['season']}")
    add("")
    add(
        "The share of a rating that is still the preseason prior, as the median "
        "across teams, per component. It is read off the posterior rather than "
        "assumed: the ridge's penalty centre **is** the prior, so `prior_weight` "
        "is the row sum of `A⁻¹Λ` — the fraction of the rating that would move "
        "if the whole prior moved by one. Cooper's rule is that this number is "
        "printed in every price so that *a November number can never be printed "
        "as if it were a February one*, and the rule is only worth anything if "
        "the number behaves."
    )
    add("")
    add(
        "| Day | Games fitted on | Teams | Offence | Defence | Tempo | "
        "Residual sd |"
    )
    add("|:---|---:|---:|---:|---:|---:|---:|")
    for row in season.get("timeline", []):
        weight = row.get("prior_weight", {})
        add(
            f"| {row['day']} | {_n(row['games'])} | {_n(row['teams'])} | "
            f"{_pct(weight.get('offence', {}).get('0.5'), 1)} | "
            f"{_pct(weight.get('defence', {}).get('0.5'), 1)} | "
            f"{_pct(weight.get('tempo', {}).get('0.5'), 1)} | "
            f"{_f(row.get('residual_sd'))} |"
        )
    add("")
    decay = season.get("decay", {})
    if not decay.get("checked"):
        add(f"**The decay could not be checked:** {decay.get('note', '')}")
        add("")
    else:
        verdict = "**holds**" if decay.get("monotone") else "**IS BROKEN**"
        add(
            f"Monotone decay over November through February {verdict}: "
            f"{_n(decay.get('printed_days'))} printed days out of "
            f"{_n(decay.get('days'))} fit days, and no day-to-day rise as large "
            f"as {_pct(decay.get('material_rise'), 1)} — which is the resolution "
            "this quantity is rendered at everywhere it appears, so a smaller "
            "one cannot reach a reader."
        )
        add("")
        add(
            "| Component | First | Last | Printed series falls | Median rises "
            "(day to day) | Largest | Rises a reader could see | Team-days that "
            "rose | Largest single team |"
        )
        add("|:---|---:|---:|:---|---:|---:|---:|:---|---:|")
        for component in COMPONENTS:
            entry = decay.get("components", {}).get(component, {})
            steps = entry.get("team_rise_steps", 0)
            possible = entry.get("team_day_steps", 0)
            add(
                f"| {component} | {_pct(entry.get('first'), 1)} "
                f"({entry.get('first_day', '')}) | {_pct(entry.get('last'), 1)} "
                f"({entry.get('last_day', '')}) | "
                f"{'yes' if entry.get('printed_monotone') else '**no**'} | "
                f"{_n(entry.get('daily_rise_count', 0))} of "
                f"{_n(entry.get('day_steps', 0))} | "
                f"{_f(entry.get('daily_largest_rise'), 6)} | "
                f"{_n(entry.get('material_rise_count', 0))} | "
                f"{_n(steps)} of {_n(possible)} "
                f"({_pct(entry.get('team_rise_share'), 0)}) | "
                f"{_f(entry.get('largest_team_rise'), 4)} |"
            )
        add("")
        add(
            "The last two columns are reported and decide nothing, and they are "
            "**team-days rather than teams** — one team on one day is one step. "
            "`prior_weight` is the row sum of `A⁻¹Λ` and `A⁻¹` has negative "
            "off-diagonal entries, so a team's own prior share depends on games "
            "played by the teams it is connected to and is **not** a monotone "
            "function of its own game count. Roughly half of all team-days move "
            "the wrong way by a fraction of a point, which is what a coupled "
            "ridge does and not a defect; it is counted here so that it is a "
            "number in the record rather than a paragraph. "
            f"{_n(decay.get('teams_added'))} team(s) joined the fit during the "
            "window, each entering at a weight near 1.0, which is the other "
            "thing that moves an order statistic."
        )
        add("")
        for component in COMPONENTS:
            entry = decay.get("components", {}).get(component, {})
            for rise in entry.get("printed_rises", []) + entry.get(
                "material_rises", []
            ):
                add(
                    f"- **`{component}` rose by {_f(rise['rose_by'], 6)} between "
                    f"{rise['from_day']} and {rise['to_day']}.** That is either "
                    "on the series this report prints or larger than the "
                    "rendering resolution, so it is a rise a reader could see "
                    "and it is a defect rather than a wobble."
                )
        if any(
            decay.get("components", {}).get(c, {}).get("printed_rises")
            or decay.get("components", {}).get(c, {}).get("material_rises")
            for c in COMPONENTS
        ):
            add("")

    # -- the seam ---------------------------------------------------------
    seam = season.get("seam_comparison", [])
    if seam:
        add(f"### The seam prices a different fit — season {season['season']}")
        add("")
        add(
            "`ratings.matchups_for` hands `fit` every season of history it was "
            "given, and `run_price_backtest.py` gives it all of them, so the "
            "design matrix on the opening Monday already holds several seasons "
            "of each team's games. `ratings.fit`'s own contract is the other "
            "one — *history filtered to the season being priced*, because *a "
            "team is not the team it was last March* — and this report fits "
            "that way. Both are refitted on the days below **from the same "
            "prior and the same tier table**, so the only thing that differs "
            "between the two columns is where the history was cut. The seam's "
            "other departure — a tier table built over the season it is pricing "
            "— is a separate finding and is counted separately below."
        )
        add("")
        add(
            "| Day | Team-games (season) | Prior weight (season) | "
            "Team-games (seam) | Prior weight (seam) |"
        )
        add("|:---|---:|---:|---:|---:|")
        for row in seam:
            own = row.get("season_only", {})
            pooled = row.get("pooled", {})
            add(
                f"| {row['day']} | {_n(own.get('team_games'))} | "
                f"{_pct(own.get('median_prior_weight', {}).get('offence'), 1)} | "
                f"{_n(pooled.get('team_games'))} | "
                f"{_pct(pooled.get('median_prior_weight', {}).get('offence'), 1)} |"
            )
        add("")
        add(
            "Offence's median is printed for compactness and every component is "
            "in the record; offence and defence differ, and both are there. "
            "**The right-hand "
            "column is the number a card produced through the seam would "
            "print**, and it does not move all season."
        )
        add("")

    leak = season.get("tier_leak", {})
    if leak.get("checked"):
        add(
            f"**Tier table:** {_n(leak.get('changed'))} of {_n(leak.get('teams'))} "
            f"teams ({_pct(leak.get('share'), 1)}) change tier when the priced "
            "season is allowed into `conferences.tier_table`. This report builds "
            "it from seasons strictly earlier, which is that module's own rule; "
            "the seam builds it over every season it holds a schedule for. A "
            "tier is not a label — it chooses which home-court effect is "
            "applied — so a team on the wrong side of a cut point is a "
            "multi-point error on every market on its home games."
        )
        add("")
        add(f"- strictly before: {leak.get('strictly_before', '')}")
        add(f"- including the priced season: {leak.get('including_priced', '')}")
        add("")

    # -- connectivity ------------------------------------------------------
    add(f"### Connectivity, and the refusal — season {season['season']}")
    add("")
    add(
        "Effective resistance on the games-played graph, re-derived by "
        "`ratings.connectivity_timeline` rather than quoted. It is not a "
        "metaphor for identifiability, it **is** it: under a paired-comparison "
        "model with no prior, the variance of an estimated rating *difference* "
        "is proportional to the effective resistance between the two teams. The "
        f"bar is {_f(record.get('max_effective_resistance'), 2)} — exactly one "
        "head-to-head meeting, and exactly two independent common opponents."
    )
    add("")
    add(
        "| Day | Games | Teams | Components | Largest | Median resistance | "
        "Share priceable |"
    )
    add("|:---|---:|---:|---:|---:|---:|---:|")
    for row in season.get("connectivity_timeline", []):
        add(
            f"| {row['day']} | {_n(row['games'])} | {_n(row['teams'])} | "
            f"{_n(row['components'])} | {_n(row['largest_component'])} | "
            f"{_f(row.get('median_resistance'), 3)} | "
            f"{_pct(row.get('priceable_share'), 1)} |"
        )
    add("")
    add(
        "A component count stops refusing days before the evidence arrives — "
        "the graph becomes one component while the typical pair is still joined "
        "by about half a common opponent's worth of results — which is the whole "
        "argument for resistance over components, and it is visible in the two "
        "columns above rather than asserted."
    )
    add("")
    refusals = season.get("refusals", [])
    if refusals:
        add(
            "Why a game was not priced, commonest first. Grouped by the reason "
            "and not by its wording: every refusal carries that morning's "
            "component count and that pair's resistance, so counting raw "
            "strings turns one refusal into a hundred rows."
        )
        add("")
        for row in refusals:
            add(f"- **{_n(row['count'])} x** {row['reason']}")
            if row.get("example"):
                add(f"  - as it reaches a reader: *{row['example']}*")
        add("")

    # -- per tier ----------------------------------------------------------
    add(f"### Per tier — season {season['season']}")
    add("")
    add(
        "The fitted columns describe the model at the end of the season; the "
        "measured columns are walk-forward, every game scored by the fit that "
        "existed on its own morning. A game belongs to a tier only when **both** "
        "teams are in it — a high-major hosting a low-major is `mixed`, because "
        "folding it into the home team's tier is how a buy-game schedule ends "
        "up describing a conference. Intervals are clustered by game and by day "
        "and the wider is reported: a hundred-game Tuesday is priced by one fit, "
        "so its errors are not a hundred independent observations."
    )
    add("")
    add(
        "| Tier | Teams | Games priced | Priced share | Prior weight (off/def/tempo) "
        "| Margin bias | 95% interval | Family-corrected | Reading | Margin MAE "
        "| Total bias | 95% interval | Family-corrected |"
    )
    add("|:---|---:|---:|---:|:---|---:|:---|:---|:---|---:|---:|:---|:---|")
    for row in season.get("per_tier", []):
        margin, margin_interval, margin_corrected, margin_words = interval_cells(
            row.get("margin_bias")
        )
        total, total_interval, total_corrected, _ = interval_cells(
            row.get("total_bias")
        )
        weight = row.get("median_prior_weight", {})
        add(
            f"| {row['tier']} | {_n(row['teams'])} | {_n(row['games_priced'])} | "
            f"{_pct(row.get('priced_share'), 1)} | "
            f"{_pct(weight.get('offence'), 0)} / {_pct(weight.get('defence'), 0)} / "
            f"{_pct(weight.get('tempo'), 0)} | {margin} | {margin_interval} | "
            f"{margin_corrected} | {margin_words} | "
            f"{_f(row.get('margin_absolute_error'))} | {total} | "
            f"{total_interval} | {total_corrected} |"
        )
    add("")
    add(f"> {POOLED_CAVEAT}")
    add("")
    add(
        "Bias is **predicted minus actual**, in points of margin from the home "
        "side, so a positive figure is a model that expects the home team to win "
        "by more than it did."
    )
    add("")

    # -- venue audit -------------------------------------------------------
    audit = season.get("venue_audit", [])
    measured = season.get("measured_home_advantage", [])
    if audit and measured:
        add(f"### The venue audit — season {season['season']}")
        add("")
        add(
            "The tier home-court effect the model applies, beside an estimate of "
            "the same quantity taken by subtraction. For every pair of teams "
            "that met at **both** home venues in a season, the mean of the two "
            "home margins is the home advantage with every team effect "
            "cancelling exactly — no shrinkage, no design matrix, no assumption "
            "that the opponent's rating was well identified. "
            "`ratings._venue_effects` fits its tier effects on the residuals of "
            "a season fit whose second stage carries no team effects at all, so "
            "the two are independent instruments for one number."
        )
        add("")
        add(
            "| Tier | Fitted (per 100) | Measured (per 100) | 95% interval | "
            "Family-corrected | Pairs | Fitted inside 95% | Fitted inside "
            "corrected | Gap |"
        )
        add("|:---|---:|---:|:---|:---|---:|:---|:---|---:|")
        by_tier = {row["tier"]: row for row in measured}
        for row in audit:
            found = by_tier.get(row["tier"])
            mean, interval, corrected, _ = interval_cells(
                found.get("per_100") if found else None
            )
            add(
                f"| {row['tier']} | {_f(row.get('fitted_per_100'), 2, sign=True)} | "
                f"{mean} | {interval} | {corrected} | {_n(row.get('pairs'))} | "
                f"{_yes_no(row.get('inside'))} | "
                f"{_yes_no(row.get('inside_corrected'))} | "
                f"{_f(row.get('gap_per_100'), 2, sign=True)} |"
            )
        add("")
        add(
            "Two `inside` columns, because the corrected interval is the wider "
            "one and a fitted number can fall outside the raw interval and "
            "inside the corrected one. **The corrected column is the one that "
            "decides**, and the list below is drawn from it: reading a "
            "disagreement off the narrower interval is exactly what a "
            "family-wise correction exists to stop."
        )
        add("")
        pooled = by_tier.get("POOLED")
        if pooled:
            mean, interval, _corrected, _words = interval_cells(pooled.get("per_100"))
            add(
                f"> {POOLED_CAVEAT} Pooled over every reciprocal pair: {mean} per "
                f"100 possessions, {interval}, over {_n(pooled.get('pairs'))} pairs."
            )
            add("")
        add(
            "**What this estimator's population is, stated rather than glossed.** "
            "Reciprocal home-and-home pairs are overwhelmingly conference games. "
            "The measurement says nothing about a November non-conference game, "
            "and if home advantage genuinely differs between the two then the "
            "fitted number and this one are measuring different things rather "
            "than disagreeing about one. That possibility is why this section "
            "reports a comparison and never applies a correction."
        )
        add("")
        outside = [row for row in audit if row.get("inside_corrected") is False]
        if outside:
            add(
                f"**{len(outside)} tier(s) have a fitted home effect outside the "
                "family-corrected measured interval.** The effect is applied to "
                "every market on "
                "every game of that tier, which is `CLAUDE.md`'s *multi-point "
                "error applied to every market on it* — the same sentence the "
                "quasi-neutral finding is filed under, and the same size of "
                "number:"
            )
            add("")
            for row in outside:
                points = row.get("fitted_points_at_league_tempo")
                add(
                    f"- **{row['tier']}**: fitted "
                    f"{_f(row.get('fitted_per_100'), 2, sign=True)} per 100 "
                    f"({_f(points, 1, sign=True)} points at this season's league "
                    f"tempo) against a measured "
                    f"{_f((row.get('measured') or {}).get('mean'), 2, sign=True)} "
                    f"over {_n(row.get('pairs'))} reciprocal pairs — a gap of "
                    f"{_f(row.get('gap_per_100'), 2, sign=True)} per 100."
                )
            add("")
            add(
                "**A second instrument says the same thing**, and it is the "
                "walk-forward table above rather than another slice of the same "
                "arithmetic. The margin bias per tier is measured on games the "
                "fit had not seen, one game at a time, all season; the venue "
                "estimate is measured on completed seasons by subtraction. They "
                "share no design matrix, no shrinkage and no season, so where "
                "the tier with the largest fitted-versus-measured gap is also "
                "the tier the model most over-predicts at home, that is two "
                "measurements agreeing rather than one measurement twice."
            )
            add("")
            add(
                "One mechanism would produce exactly this, and it is offered as "
                "a **lead and not a finding**: `_venue_effects` regresses the "
                "residuals of a shrunk season fit on home indicators with no "
                "team effects in the second stage, so a home win over an "
                "opponent whose rating was shrunk toward the league mean leaves "
                "a positive residual — and only the home side of a schedule "
                "that hosts weak opponents ever collects it. "
                "`docs/what_we_can_and_cannot_claim.md` is explicit that *a "
                "finding that is really a mechanism is the most persuasive kind "
                "and the most dangerous*, so the two measurements above are the "
                "evidence and this paragraph is not."
            )
            add("")
    return lines


def _render_turnover(record: dict) -> list[str]:
    lines: list[str] = []
    add = lines.append
    turnover = record.get("roster_turnover", {})
    add("## Roster turnover, measured here")
    add("")
    if not turnover.get("available"):
        add(f"**Not measured.** {turnover.get('note', '')}")
        add("")
        return lines
    add(
        "The empirical argument for the whole November regime: if a large share "
        "of a team's minutes are new, last season's rating is a prior and not a "
        "fit. Measured on this lab's own tables — no figure here is quoted from "
        "a sibling lab, because turnover in hockey and turnover in football are "
        "facts about hockey and football."
    )
    add("")
    add(
        "Two populations, because the difference between them is large and "
        "choosing one silently would be a choice nobody could see. **D-I only** "
        f"covers the {_n(turnover.get('division_one_teams'))} team ids the "
        "schedule feed gives a conference to across seasons "
        f"{turnover.get('schedule_seasons')} — the board this lab prices. "
        "**Unrestricted** is every team in the player table, several hundred of "
        "which are non-D-I programmes with sparse and unevenly recorded rows, "
        "and it is the population `models/ratings.py`'s own docstring quotes. "
        "The two answer different questions and the restricted one is the "
        "answer to the question this lab asks."
    )
    add("")
    add(
        "| Season | Teams (D-I) | Returning minutes (D-I) | Incoming transfers "
        "(D-I) | Teams (all) | Returning (all) | Incoming (all) |"
    )
    add("|:---|---:|---:|---:|---:|---:|---:|")
    unrestricted = {row["season"]: row for row in turnover.get("unrestricted", [])}
    for row in turnover.get("division_one", []):
        other = unrestricted.get(row["season"], {})
        add(
            f"| {row['season']} | {_n(row['teams'])} | "
            f"{_pct(row['returning_minutes_share'], 1)} | "
            f"{_pct(row['incoming_transfer_share'], 1)} | "
            f"{_n(other.get('teams'))} | "
            f"{_pct(other.get('returning_minutes_share'), 1)} | "
            f"{_pct(other.get('incoming_transfer_share'), 1)} |"
        )
    add("")
    add(
        "Returning minutes is the share of a team's **previous** season minutes "
        "played by athletes back on its roster; incoming transfers is the share "
        "of a team's **current** minutes played by athletes who were at another "
        "school last season. The two do not sum to one and are not meant to: a "
        "freshman is in neither."
    )
    add("")
    add(
        "**A season's figure is about its own denominator.** Each row divides by "
        "the *previous* season's minutes, so a season following a short or "
        "disrupted one is measured against a smaller and differently composed "
        "base and is not comparable to its neighbours on the same terms. Any row "
        "that looks like a reversal of the trend should be read against the "
        "season above it before it is read as a change in the sport."
    )
    add("")
    return lines


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------


def record_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(OUTPUT_STEM, ".json")


def report_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(OUTPUT_STEM, ".md")


def write_record(record: dict, path: Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")
    return target


def read_record(path: Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    version = int(payload.get("record_version", 0))
    if version != RECORD_VERSION:
        raise NothingToFit(
            f"{Path(path).name} is a version {version} record and this program "
            f"writes version {RECORD_VERSION}. Re-run the fit rather than "
            "re-rendering a record whose shape has changed — a stale record "
            "renders a report with holes in it and nothing looks wrong."
        )
    return payload


def write_report(record: dict, path: Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(record), encoding="utf-8")
    return target


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def parse_seasons(values: list[str] | None) -> list[int]:
    """Seasons from the command line, however the caller spells them.

    `run_weekly_loop.py` splits its own `--seasons` on whitespace and passes the
    pieces as separate arguments; `run_price_backtest.py` takes them
    comma-separated in one. Both spellings are accepted here rather than
    picking a side, because the loop is the caller that matters and a refit that
    exits on argparse is reported as a **failed** step — the program existed and
    did not do its job — which is a worse signal than the one it replaces.
    """
    out: list[int] = []
    for value in values or []:
        for piece in str(value).replace(",", " ").split():
            if piece.strip().isdigit():
                out.append(int(piece))
    return sorted(set(out))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument(
        "--seasons",
        nargs="*",
        default=[],
        help=(
            "Seasons to refit, labelled by the year they END. Space- or "
            "comma-separated. Default: the latest season the processed table "
            "holds a countable game for."
        ),
    )
    parser.add_argument(
        "--ledger",
        default="",
        help=(
            "The experiment ledger the family-wise correction is read from. "
            "Defaults to the one beside the outputs. Always the CUMULATIVE "
            "count, never the day's."
        ),
    )
    parser.add_argument(
        "--rebuild-report-only",
        action="store_true",
        help=(
            "Re-render the markdown from the existing run record. Fits nothing, "
            "reads no table, spends nothing."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    competition = competition_for(args.competition)
    output_dir = Path(args.output_dir)
    processed_dir = Path(args.processed_dir)
    raw_dir = Path(args.raw_dir)
    json_path = record_path(competition, output_dir)
    markdown_path = report_path(competition, output_dir)

    if args.rebuild_report_only:
        try:
            record = read_record(json_path)
        except FileNotFoundError:
            print(
                f"::error::{json_path} does not exist, so there is no record to "
                "re-render. Run the fit first; a report written from nothing is "
                "a report about nothing.",
                file=sys.stderr,
            )
            return EXIT_NOTHING_TO_FIT
        except NothingToFit as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return EXIT_STALE_RECORD
        write_report(record, markdown_path)
        print(f"Re-rendered {markdown_path} from {json_path}. Nothing was refitted.")
        return EXIT_OK

    print(f"{competition.title} — walk-forward ratings fit")
    print("Spends nothing, opens no socket, buys no price.")

    # Schedules are cached by season inside `models/ratings.py` and the cache
    # key does not carry the directory, so a run pointed at a different
    # `--raw-dir` in the same process would silently read the first one's
    # parquet. Dropped up front rather than reasoned about.
    R.clear_caches()

    try:
        team_games = load_team_games(processed_dir, competition)
        seasons = seasons_to_fit(team_games, parse_seasons(args.seasons))
    except NothingToFit as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_FIT

    window = sorted(
        set(range(min(seasons) - R.PRIOR_WINDOW_SEASONS, max(seasons) + 1))
        & {
            int(s)
            for s in pd.to_numeric(team_games["season"], errors="coerce").dropna().unique()
        }
    )
    try:
        schedules = load_schedules(window, raw_dir)
    except FileNotFoundError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NO_SCHEDULE

    print(
        f"Seasons {seasons}, prior window {R.PRIOR_WINDOW_SEASONS}, reading "
        f"seasons {window} of {len(team_games):,} team-game rows."
    )

    frame = team_games[team_games["season"].isin(window)]
    prepared = R.prepare(frame, schedules=schedules)
    print(prepared.summary_line())
    if not prepared.reconciles():
        print(
            "  The accounting identity does NOT reconcile. Rows left the fit "
            "without appearing in any exclusion count; the report prints how "
            "many. See `PreparedGames.reconciles`."
        )
    if prepared.rows.empty:
        print(
            "::error::No team-game row survived preparation, so there is "
            "nothing to fit. Every supplied row was excluded by one of the "
            "counted reasons above; a fit over an empty frame returns every "
            "team at its prior and prints a tidy report about nothing.",
            file=sys.stderr,
        )
        return EXIT_NOTHING_TO_FIT

    # Two different windows, on purpose. The **prior** may only see seasons in
    # its own window; the **turnover measurement** is a description of the sport
    # and not an input to any fit, so it reads every season the table holds and
    # reports a seven-season trend rather than the three the prior happens to
    # need. Filtering both to the prior's window is how the first run of this
    # report printed a transfer-portal series starting in 2024.
    all_player_games = load_player_games(processed_dir, competition)
    player_games = all_player_games
    if all_player_games.empty:
        print(
            "The processed player-games table is absent: the prior carries no "
            "roster terms and turnover is reported as an absence, never a zero."
        )
    else:
        player_games = all_player_games[all_player_games["season"].isin(window)]
        print(
            f"Player-games: {len(all_player_games):,} rows, of which "
            f"{len(player_games):,} are in the prior window {window}."
        )

    ledger = Path(args.ledger) if args.ledger else output_dir / LEDGER_FILENAME
    looks = PB.looks_from_ledger(ledger if ledger.is_file() else None)
    if not ledger.is_file():
        print(
            f"No experiment ledger at {ledger}, so the family-wise correction "
            "could not be applied and every interval below is uncorrected. That "
            "is stated rather than quietly treated as a correction of one."
        )

    fits: dict[int, SeasonFit] = {}
    for season in seasons:
        print(f"Fitting season {season}...")
        try:
            fit = fit_one_season(
                season=season,
                prepared=prepared,
                schedules=schedules,
                player_games=player_games,
                competition=competition,
                output_dir=output_dir,
            )
        except (PB.WalkForwardLeak, R.WalkForwardViolation) as exc:
            # Both guards end here, and they are two different guards: the first
            # reads the stamp on a priced row, the second is `ratings.fit`
            # refusing history that reaches the day it is pricing. Either one
            # firing means the fit saw a game it was pricing, and a run that has
            # done that must not write a report — the leaked numbers would look
            # like every other number in it.
            print(f"::error::{exc}", file=sys.stderr)
            return EXIT_WALK_FORWARD_LEAK
        if fit.days.empty:
            print(
                f"::error::Season {season} produced no fit day. Nothing was "
                "written.",
                file=sys.stderr,
            )
            return EXIT_NOTHING_TO_FIT

        printed = report_days(fit.days)
        fit.connectivity_timeline = R.connectivity_timeline(
            prepared, season=season, days=printed
        )
        fit.decay = decay_check(fit.days, printed=printed)
        fit.per_tier = per_tier_fits(fit, looks=looks)
        fit.measured_home_advantage = reciprocal_home_advantage(
            prepared.rows,
            tiers=fit.prior.tiers if fit.prior else None,
            seasons=tuple(fit.prior.seasons_used) if fit.prior else (),
            looks=looks,
        )
        fit.venue_audit = venue_audit(fit, fit.measured_home_advantage)
        fit.seam_comparison = seam_comparison(
            season=season,
            prepared=prepared,
            prior=fit.prior,
            days=printed,
            competition=competition,
            output_dir=output_dir,
        )
        fit.tier_leak = tier_leak(schedules, season)
        fit.refusals = refusal_families(fit.games[~fit.games["priceable"]])
        fits[season] = fit
        print(
            f"  {len(fit.days):,} fits, {int(fit.games['priceable'].sum()):,} of "
            f"{len(fit.games):,} games priced. "
            + ("prior decay holds." if fit.decay.get("monotone") else "PRIOR DECAY BROKEN.")
        )

    # The D-I team set is read from every schedule this run can see, not only
    # the prior window's, because a team that was D-I in 2020 and is not now was
    # still D-I in 2020 and its turnover that season is a real observation. The
    # seasons outside the window are loaded leniently: a missing old parquet
    # narrows this measurement and must not fail a refit that does not need it.
    turnover_seasons = sorted(
        {
            int(s)
            for s in pd.to_numeric(all_player_games.get("season"), errors="coerce")
            .dropna()
            .unique()
        }
        if not all_player_games.empty
        else set()
    )
    schedules_for_ids = dict(schedules)
    for season in turnover_seasons:
        if season in schedules_for_ids:
            continue
        try:
            schedules_for_ids[season] = R._cached_schedule(season, raw_dir)
        except FileNotFoundError:
            continue
    division_one: set = set()
    for schedule in schedules_for_ids.values():
        division_one |= division_one_team_ids(schedule)
    turnover = roster_turnover_rows(
        all_player_games,
        seasons=[s for s in turnover_seasons if s - 1 in turnover_seasons],
        division_one=division_one,
    )
    turnover["schedule_seasons"] = sorted(schedules_for_ids)

    record = build_record(
        competition=competition,
        seasons=seasons,
        fits=fits,
        prepared=prepared,
        team_games_supplied=int(len(team_games)),
        turnover=turnover,
        looks=looks,
        player_games_available=not player_games.empty,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        processed_dir=processed_dir,
        raw_dir=raw_dir,
    )
    write_record(record, json_path)
    write_report(record, markdown_path)
    print(f"Wrote {json_path}")
    print(f"Wrote {markdown_path}")

    broken = [s for s in seasons if not fits[s].decay.get("monotone", True)]
    if broken:
        # Named down to the component and the two days, because a red step whose
        # message is a list of seasons is a red step nobody can act on.
        for season in broken:
            for component, entry in (
                fits[season].decay.get("components", {}).items()
            ):
                for rise in entry.get("printed_rises", []) + entry.get(
                    "material_rises", []
                ):
                    print(
                        f"::error::season {season}: the median `{component}` "
                        f"prior weight rose by {rise['rose_by']:.4f} between "
                        f"{rise['from_day']} and {rise['to_day']}.",
                        file=sys.stderr,
                    )
        print(
            "::error::The prior's median weight rose where it may not, in "
            f"season(s) {broken}, by more than the "
            f"{DECAY_MATERIAL:.1%} a reader of any output this lab produces "
            "could see. `prior_weight` is the field a card prints so that a "
            "November number cannot read as a February one, and a number that "
            "goes up as evidence arrives does not say what that field claims. "
            "The record and the report were written so the evidence is on disk; "
            "this run is a failure.",
            file=sys.stderr,
        )
        return EXIT_PRIOR_WEIGHT_NOT_MONOTONE
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
