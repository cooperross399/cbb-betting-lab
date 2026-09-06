"""What this lab believes about one athlete's minutes and per-minute rates.

This is the estimator half of the player model. It turns a **cut** player frame
— rows dated strictly earlier than the day being priced — into one
:class:`PlayerProjection` per (event, athlete) the book quoted, or into a
full-sentence refusal saying why there is none. It does not produce a
probability: `models/player_distributions.py` is not written, so a priceable
projection's last word is still that no engine exists to turn it into a price.

## The defect this file is arranged against

Every prop quote in the store is season 2024. The frozen constants in
`data/processed/cbb_player_shapes.json` were fitted on 2019-2022 and validated
on 2023, and `models/player_shapes.py` refuses to hand them back for a season
their window touches. That closes the *shape* leak. The *outcome* leak is
closed here, and by exactly one rule:

    **Nothing in this module opens a file.**

The player table arrives as the `player_history` argument, cut once by
`reports/price_backtest.history_before` at the caller and handed down through
`models/slate.py`. A `read_csv` anywhere below this line would reach the
settlement table — 1,493,589 rows, seasons 2019 through 2026, 404,489 of them
dated after the season being priced — and `config.PROCESSED_DIR` is an absolute
path, which is precisely the route the walk-forward guard has written down as
open (gap 6 of nine). The estimator therefore reads no path, holds no
module-level frame, and takes the day it may not reach as an argument.

The second rule follows from the first: **the roster searched is a prior
roster.** `providers.player_names.build_index` keys aliases off the box score
*of the game itself*, so resolving tonight's spelling against it would read the
game being priced. That index is reused here — the class, unchanged, so R1's
readings are the settlement resolver's own code and not a second copy — but it
is populated from prior rows and keyed by `event_id`, never by tonight's
`game_id`.

## What it computes, and what each number is made of

*Minutes.* `projected_minutes` is an EWMA of minutes over **played** games,
half-life 4 games, read from the frozen file rather than written here: a second
copy of a half-life is how the fit and the price come to disagree about one.
The file's own note records that the argmin was half-life 2 on the fit window
and 3 on the holdout, that 4 was declared anyway, and that the declaration cost
0.0320 minutes of RMSE.

The minutes object is **not** a mean and a standard deviation. It is the
empirical pmf over integers 1..45 for the projected-minutes bucket,
exponentially tilted to the projected mean, with **exactly zero mass at zero**.
That is not a rounding convention: the book voids a did-not-play, so the priced
quantity is `P(stat > line | the wager stands)` = `P(· | he appears)`.
`dnp_probability` is stored beside it as a diagnostic and is never multiplied
into anything — :func:`minutes_lattice` never receives it, and
`tests/test_player_rates.py` prices the same athlete against two shapes files
differing only in `dnp_base_rate` and asserts the lattice is bit-identical.

*Rates.* Minutes-weighted, never per-game-averaged — a four-minute night must
not weigh what a thirty-four-minute night says about a rate — and shrunk toward
a **role prior indexed by projected minutes**, nine buckets, one table per stat:

    w_c = prior_minutes / (prior_minutes + k_c)
    r_c = w_c * (bank_c / prior_minutes) + (1 - w_c) * role_prior_c[bucket]

`k` is in prior **minutes** and the bucket is the **projected**-minutes bucket,
never the realised one. The role prior is **allowed to run downward**: rebounds
falls from 0.16823 per minute in the 8-12 bucket to 0.13048 in the 36+ bucket,
because big men foul out, and a monotone functional form would be wrong about
that forever. Nothing here imposes a shape;
`test_the_role_prior_is_allowed_to_run_downward` asserts that it does not.

*The 1/2/3 mix.* The player's own free-throw / two / three split, shrunk toward
the league shape on a bank of prior scoring events, so a centre and a shooting
guard differ. It is what makes `player_threes` fall out of the points object
rather than arrive as a separate count — and it is also fitted standalone, so
the two readings can be compared rather than assumed equal (open question 4 of
the contract, still open, recorded here rather than decided).

## The five refusals, and the one this file adds

R1 and R1a are **name** refusals: they have no athlete id, so they are never a
:class:`PlayerProjection`. They are returned in `name_refusals`, keyed by the
book's spelling exactly as filed. R2 through R5 are projections with
`priceable=False` and a full-sentence `unpriceable_reason`. A subject with no
entry at all is **no opinion**, which is a different census bucket and is never
summed with a refusal.

R6 is added here and is not in the design, because the wiring made it real: the
card reads only the eight columns `slate.REQUIRED_PLAYER_COLUMNS` declares, and
a per-minute rate cannot be formed from them. Rather than invent a rate or fall
back to a role table under a player's name, a subject whose frame carries no
box-score columns is refused in a sentence that names the missing columns and
the caller that cut them out. See
`test_the_gaps_this_estimator_still_has_are_the_ones_written_down`.

## What it costs, measured rather than estimated

One call prices one day. Measured on this machine against the real
1,493,589-row player table cut at 2024-01-20 (1,001,050 rows survive the cut),
a synthetic board of the 143 events the card store quotes that day, 1,430
subjects and 10,010 rungs: **2.54 seconds**, best of three. The subjects are
synthetic because the price store reachable from this worktree carries **zero**
`player_*` rows — 2,946,929 rows across spread, total_points, moneyline and
team_total and nothing else — so that number is a cost, not a census, and no
refusal count taken against that store may be reported as a census of the prop
store.

Where the time goes, in case it has to come down: an alias index and a
`groupby(...).ewm(...)` per event, 143 of each. It is not the day cut — that is
`history_before` at the caller, measured at 0.15 seconds on the same frame.

## What it does not do, stated because a silence reads as a claim

No opponent, no pace, no venue, no rest, no home/away term. The player price
reads **nothing** from `ratings.Matchup`, so a refusing matchup does not refuse
the prop on the same game. There is no cross-season carry-over: the bank resets
at every season boundary, which combined with R2 refuses every player —
returning starters included — for roughly the first four appearances of every
season. That is the largest single driver of the November refusal census and it
has to be read before the census is.

Nothing in this module measures anything. No number below is an edge, a loss or
a verdict, and no path here can select a bet.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Mapping, Sequence

import numpy as np
import pandas as pd

from cbb_betting_lab import settlement
from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.conferences import Tier, TierTable
from cbb_betting_lab.markets import MARKETS_BY_KEY, PLAYER
from cbb_betting_lab.models.player_shapes import PlayerShapes, ShapesFileError
from cbb_betting_lab.providers import player_names
from cbb_betting_lab.season import clean_text, season_for_slate_date

__all__ = [
    "PlayerRatesError",
    "PlayerProjection",
    "PlayerSlate",
    "Resolution",
    "player_projections_for",
    "projection_for",
    "prior_roster",
    "resolve_subject",
    "trailing_evidence",
    "minutes_projection",
    "role_prior_bucket",
    "minutes_lattice",
    "tilt_to_mean",
    "shrink_rate",
    "shrink_value_mix",
    "mean_for_market",
    "refusal_census",
    "resolution_census",
    "assert_tier_resolution_holds",
    "STAT_KEYS",
    "SETTLEMENT_COLUMN",
    "MARKET_COMPONENTS",
]


class PlayerRatesError(ValueError):
    """A projection could not be formed, and the caller was about to price anyway.

    Never raised for a subject this lab has no opinion about — that is an
    absence, and an absence returns nothing rather than raising. This is for
    the caller-side mistakes: a frame with no day column, a shapes file whose
    declared block has drifted from the thresholds enforced here, a name handed
    to :func:`projection_for` that no prior-roster athlete answers to.
    """


# --------------------------------------------------------------------------
# Vocabulary. The file, the box score and the market do not agree on names,
# and this lab has the join-vocabulary bug family written down five times.
# --------------------------------------------------------------------------

#: The stats a per-minute rate is fitted and formed for. `points_events` is the
#: count of scoring events — a made free throw, a made two, a made three — and
#: is latent: no column of `cbb_player_games.csv` carries it, and it is built
#: from three that do. `points` carries BOTH a shrunk rate here and a compound
#: route through `points_events` times the value mix; the fitter's own comment
#: says which is which ("carried so the design's coherence identity D3 has a
#: mean to check"), so the compound is the price and `rates["points"]` is the
#: check. `blocks` is deliberately absent: it is not among the ten priced
#: markets and the frozen file carries no constant for it. That is a match, not
#: a gap.
STAT_KEYS: tuple[str, ...] = (
    "points",
    "points_events",
    "rebounds",
    "assists",
    "threes",
    "steals",
    "turnovers",
)

#: A stat key to the column of `data/processed/cbb_player_games.csv` that
#: settles it. `points_events` maps to the empty string because it settles on
#: nothing: it is `free_throws_made + field_goals_made`, an identity of the box
#: score rather than a column of it.
SETTLEMENT_COLUMN: Mapping[str, str] = {
    "points": "points",
    "points_events": "",
    "rebounds": "rebounds",
    "assists": "assists",
    "threes": "three_point_field_goals_made",
    "steals": "steals",
    "turnovers": "turnovers",
}

#: `markets.Market.key` to the stat keys it sums. The four combination markets
#: carry no constant and no rate of their own: they are built from components
#: over the shared minutes draw, which is why a points line and a pra line on
#: one player can never disagree. Both rival measurements agreed that own-history
#: buys nothing on the mean (MAE 5.097 against 5.099, quoted from the design,
#: not re-measured here).
MARKET_COMPONENTS: Mapping[str, tuple[str, ...]] = {
    "player_points": ("points",),
    "player_rebounds": ("rebounds",),
    "player_assists": ("assists",),
    "player_threes": ("threes",),
    "player_steals": ("steals",),
    "player_turnovers": ("turnovers",),
    "player_pra": ("points", "rebounds", "assists"),
    "player_points_rebounds": ("points", "rebounds"),
    "player_points_assists": ("points", "assists"),
    "player_rebounds_assists": ("rebounds", "assists"),
}

#: The ten markets this model is registered against, in the ledger's order.
PRICED_MARKETS: tuple[str, ...] = tuple(MARKET_COMPONENTS)

#: The two markets the design refuses BY NAME, in the design's own words.
#:
#: **A refusal that reaches no output is not a refusal.** Until 2026-09-06 this
#: mapping had exactly one reader in the whole tree — the exception message in
#: :func:`mean_for_market` — so a first-basket wager on a priceable athlete
#: fell through to "no probability exists for this line yet", which describes a
#: temporary wiring absence, and the claims document listed both markets as
#: "priced, frozen and settled", which asserts a price exists and blames the
#: availability gate. Both inverted the one distinction these sentences exist
#: to draw. Every path that can surface one of these markets now reads this
#: mapping, and `tests/test_player_rates.py` pins the wording clause by clause
#: rather than by one substring.
#:
#: The first-basket text is the design's verbatim census wording. Three clauses
#: had been dropped from it — the mutually-exclusive sum, the measured size of
#: the partial field, and the evidence half of the model-refusal claim — and
#: the evidence half is the one that matters, because every OTHER refusal in
#: this module is a data absence. Without it a reader is asked to take the
#: distinction on trust.
MARKETS_REFUSED_BY_NAME: Mapping[str, str] = {
    "player_first_basket": (
        "refused: this market settles on the scorer of the game's first field "
        "goal, which is decided by the starting five and the opening tip. "
        "Neither is knowable at T-60 in this sport, no tip-winner data exists "
        "in any table here, and a per-minute rate says nothing about minute "
        "zero. It is also a mutually exclusive family -- the probabilities "
        "across a game's players must sum to at most one, and the store quotes "
        "422 names over 1,180 games, a partial field, so no normalisation "
        "exists and independently priced names would over-sum with nothing "
        "looking wrong. This is a model refusal, not a data absence: "
        "`first_basket_athlete_id` is present on 100% of game-segment rows and "
        "the market is perfectly settleable. Not a pass, not an avoid, not a "
        "no-value call."
    ),
    "player_double_double": (
        "refused: the store holds two quotes on one player-game. There is "
        "nothing to measure, and pricing it would add a pre-registered "
        "hypothesis -- widening every other interval in the lab -- in exchange "
        "for a sample of one."
    ),
}

#: The column of the player frame that carries its day. Equal to
#: `slate.SLATE_DAY_COLUMN` and to `walk_forward`'s default, so no call site
#: passes `frame_day_columns` and there is one answer to what a day is.
SLATE_DAY_COLUMN = "slate_date"

#: Everything the estimator reads off a player row, and nothing else. The cut
#: frame arrives with all thirty-two columns of `cbb_player_games.csv`; the day's
#: pool is narrowed to these before anything is copied, because the copy is per
#: priced day and the other fifteen columns are carried through it for nothing.
_POOL_COLUMNS: tuple[str, ...] = (
    "slate_date",
    "season",
    "game_id",
    "athlete_id",
    "athlete_display_name",
    "team_id",
    "opponent_id",
    "did_not_play",
    "minutes",
    "points",
    "rebounds",
    "assists",
    "steals",
    "turnovers",
    "field_goals_made",
    "three_point_field_goals_made",
    "free_throws_made",
)

#: The box-score columns a per-minute rate is formed from. NOT the same list as
#: `slate.REQUIRED_PLAYER_COLUMNS`, which is the eight columns the seam
#: declares — a frame carrying only those eight can project minutes and cannot
#: form a rate. See R6 and the written-down gaps.
REQUIRED_STAT_COLUMNS: tuple[str, ...] = (
    "points",
    "rebounds",
    "assists",
    "steals",
    "turnovers",
    "field_goals_made",
    "three_point_field_goals_made",
    "free_throws_made",
)


# --------------------------------------------------------------------------
# The declared block, restated here and asserted equal to the file's
# --------------------------------------------------------------------------
#
# `data/processed/cbb_player_shapes.json` keeps `bucket_edges`,
# `bucket_labels`, `minutes_support`, `refusal_thresholds` and
# `prior_season_min_games` in a `declared` block that `PlayerShapes` exposes no
# accessor for and `_check_constant` never inspects. So unlike the twelve
# fitted constants they carry no fit window, and design L4 says to assert that
# NO constant lacks one.
#
# They are declared here, from the design, and
# `test_the_refusal_thresholds_this_module_enforces_equal_the_declared_block`
# asserts they equal the file's — a passing assertion that goes red the day the
# two drift. `_assert_declared_agrees` makes the same check at price time, so a
# drifted file refuses rather than prices. This is the contract's open question
# 1, resolved as option (b): declaring them and holding them against the file,
# rather than growing `player_shapes.py` an accessor in a commit that is
# otherwise not touching it.

#: Nine buckets over PROJECTED minutes; `np.digitize(v, edges, right=False)`.
BUCKET_EDGES: tuple[float, ...] = (8.0, 12.0, 16.0, 20.0, 24.0, 28.0, 32.0, 36.0)
BUCKET_LABELS: tuple[str, ...] = (
    "0-8", "8-12", "12-16", "16-20", "20-24", "24-28", "28-32", "32-36", "36+",
)

#: The minutes lattice runs 1..45 inclusive. The 46-long pmf this module
#: returns is indexed by minutes with a 0.0 prepended.
MINUTES_SUPPORT: tuple[int, int] = (1, 45)

#: R2 and R3, declared and not measured on 2024.
MIN_PRIOR_GAMES = 4
MIN_PRIOR_MINUTES = 60.0
MIN_PROJECTED_MINUTES = 8.0

#: The fit's own player-season selection, on the PRIOR season's appearances.
#: Not enforced at price time — nothing here selects a player-season — and
#: declared so `tests/test_player_model_leakage.py` L9(c) can hold the fitter to
#: it, which no test in this repository did before this commit.
PRIOR_SEASON_MIN_GAMES = 5

#: Design 13, failure mode 5: print the per-tier resolution rate every run and
#: stop if it moves more than this many percentage points across tiers. A gate,
#: not a price, and computed over resolved subjects only — an unresolved name
#: has no athlete and therefore no team to be tiered by (contract open
#: question 7).
TIER_RESOLUTION_TOLERANCE_POINTS = 2.0


# --------------------------------------------------------------------------
# The refusals, in the words the design gives where it gives them
# --------------------------------------------------------------------------

R1_UNRESOLVED = (
    "refused: this lab could not read the book's spelling of this player as "
    "exactly one athlete on either roster."
)

R1A_TONIGHT_ONLY = (
    "refused: this name resolves only in tonight's box score, which is a "
    "player this lab has not seen, not a name it cannot read. The clause after "
    "the comma is the design's and this module cannot check it: the roster "
    "searched is a PRIOR roster, so a spelling that reaches no prior athlete "
    "is a debutant and an unreadable spelling at once, and separating the two "
    "would need the box score of the game being priced. "
    "`providers/player_names.py` measured 372 unreachable spellings on "
    "2026-09-05, against 9,584 (game, player) pairs, on a settlement-time join "
    "this module may not make."
)

R1B_NO_PRIOR_ROSTER = (
    "refused: neither team on this game has a player row earlier than today in "
    "this season or the one before it, so there is no roster to read the name "
    "against. This is the lab having seen nobody, not the athlete being "
    "unknown, and it is counted apart from both name refusals."
)

R2_TOO_THIN = (
    "refused: fewer than four prior appearances / fewer than sixty prior "
    "minutes; this would be a role-table price wearing a player's name."
)

R3_NO_MINUTES = (
    "refused: this athlete carries no minutes projection, or one below eight "
    "minutes. Below eight the distribution is dominated by whether he plays at "
    "all, which this lab cannot know at sixty minutes to tip -- the projection "
    "would be a statement about the coach and would be published as one about "
    "the player. Not a pass, not an avoid, not a no-value call."
)

R4_OUTSIDE_SUPPORT = (
    "refused: the mean this projection implies is not a quantity the lattice "
    "can carry -- it is non-finite, or at or below 0.02, or the minutes "
    "projection reaches the ceiling of the declared support and the tilt to it "
    "has no solution. Clipping it silently is how an absurd projection becomes "
    "a plausible price."
)

R5_NO_WALK_FORWARD_FIT = (
    "refused: a constant this market needs was recorded unfittable by "
    "`scripts/fit_player_model.py`, and fitting one on the season being priced "
    "is not a fallback. The fit's own words follow."
)

R6_NO_BOX_SCORE_COLUMNS = (
    "refused: the player frame handed to this model carries no box-score "
    "columns, so no per-minute rate exists to shrink. The eight columns "
    "`slate.REQUIRED_PLAYER_COLUMNS` declares are enough to project minutes "
    "and are not enough to price a stat, and a rate invented from the columns "
    "that are present would be the role table wearing a player's name. The "
    "missing columns follow."
)

#: The route a resolution came by, for the census. Three names, not the
#: design's five: `providers.player_names` resolves by taking the intersection
#: of a SET of readings with the index, not by walking an ordered cascade, so
#: "fold", "suffix" and "token_subset" name steps that code does not have and a
#: census reporting them would be a fiction. What is observable is whether the
#: conservative reading matched, whether the book abbreviated the first name,
#: and whether some other reading was needed.
ROUTE_EXACT = "exact"
ROUTE_INITIAL = "initial"
ROUTE_VARIANT = "variant"
ROUTES: tuple[str, ...] = (ROUTE_EXACT, ROUTE_INITIAL, ROUTE_VARIANT)

#: Census keys for the buckets that are not a resolution.
ROUTE_REFUSED_NAME = "refused_name"
ROUTE_REFUSED_DEBUTANT = "refused_debutant"
ROUTE_REFUSED_NO_ROSTER = "refused_no_prior_roster"

_TRUE_TOKENS = frozenset({"true", "t", "yes", "y", "1"})
_DNP = "did_not_play"


# --------------------------------------------------------------------------
# Value objects
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Resolution:
    """One book spelling, read against a prior roster, or refused.

    `candidates` is the count, not a choice: zero is unresolved, one is a
    match, and **more than one refuses**. It never picks. `team_names`'
    comment holds here word for word — an ambiguous name resolves to nothing,
    never to a coin flip — and it is what lets the readings be generous.
    """

    athlete_id: object = None
    display_name: str = ""
    route: str = ""
    candidates: int = 0
    in_tonights_box_only: bool = False
    refusal: str = ""

    @property
    def resolved(self) -> bool:
        return self.candidates == 1 and self.athlete_id is not None


@dataclass(frozen=True)
class PlayerProjection:
    """What this lab believes about one athlete on one game, or why it does not.

    Every field is either read off the cut frame or off a provenance-checked
    constant. `priced_through` is the frame-level maximum `slate_date` of the
    frame this projection was formed from — the same value on every projection
    of a day — and NOT the athlete's own last game. That is deliberate and it
    is `price_backtest._stamp_series`' rule quoted: *the stamp describes what
    the pricer was ALLOWED to see, not what it chose to read.* Read the other
    way, L2's assertion that the pricer-reported stamp equals the harness cut
    would fail for every player whose last game was a week ago.
    """

    event_id: str = ""
    game_id: object = None
    athlete_id: object = None
    display_name: str = ""
    provider_name: str = ""
    team_id: object = None
    opponent_id: object = None
    player_tier: str = Tier.UNPLACED.value
    projected_minutes: float = float("nan")
    minutes_bucket: int = -1
    minutes_pmf: tuple[float, ...] = ()
    rates: Mapping[str, float] = field(default_factory=dict)
    prior_weight: Mapping[str, float] = field(default_factory=dict)
    prior_minutes: float = 0.0
    prior_games: int = 0
    value_pmf: tuple[float, float, float] = (0.0, 0.0, 0.0)
    value_prior_events: float = 0.0
    value_mix_weight: float = 0.0
    dnp_probability: float = float("nan")
    resolution_route: str = ""
    priceable: bool = False
    unpriceable_reason: str = ""
    priced_through: str = ""
    #: Stat keys whose constant the fit recorded unfittable, with the fit's own
    #: sentence. A DECLARED ADDITION to the contract's field list: R5 is a
    #: market-level refusal and the contract's own `refusals` section says its
    #: words come from `shapes.refusal_for(name)`, which a projection with
    #: nowhere to put them cannot report.
    refused_stats: Mapping[str, str] = field(default_factory=dict)

    def mean_minutes(self) -> float:
        """The mean of the minutes lattice, which is what the tilt targeted."""
        if not self.minutes_pmf:
            return float("nan")
        weights = np.asarray(self.minutes_pmf, dtype=float)
        return float(weights @ np.arange(len(weights)))


@dataclass(frozen=True)
class PlayerSlate:
    """One day's player half: opinions, name refusals, and what was read.

    A DECLARED DEVIATION from design 2, which gives `player_projections_for` a
    return of `tuple[dict[event][athlete], str]`. That shape cannot carry an
    R1/R1a refusal — a name that does not resolve **has no athlete id**, so a
    container keyed only by athlete id makes design 7's own rule (*every
    refusal is an entry with a full-sentence reason*) unrepresentable for the
    two refusals design 11 says must be counted and printed every run. It also
    leaves the card holding the book's spelling with no way to reach an athlete
    except by matching, which design 2 forbids. `projections` itself keeps the
    design's exact shape; the other four fields are what the tuple could not
    say. `models/slate.py:_unpack` accepts both.
    """

    projections: Mapping[str, Mapping[object, PlayerProjection]] = field(
        default_factory=dict
    )
    resolved: Mapping[tuple[str, str], object] = field(default_factory=dict)
    name_refusals: Mapping[tuple[str, str], str] = field(default_factory=dict)
    priced_through: str = ""
    resolution_census: Mapping[str, int] = field(default_factory=dict)

    def summary_line(self) -> str:
        athletes = sum(len(by_athlete) for by_athlete in self.projections.values())
        priceable = sum(
            1
            for by_athlete in self.projections.values()
            for projection in by_athlete.values()
            if projection.priceable
        )
        return (
            f"{athletes:,} athlete(s) projected on {len(self.projections):,} "
            f"event(s), {priceable:,} priceable; "
            f"{len(self.name_refusals):,} name(s) refused; read through "
            f"{self.priced_through or 'nothing'}."
        )


# --------------------------------------------------------------------------
# Reading the frame the way the rest of the lab reads it
# --------------------------------------------------------------------------


def _did_not_play(series: pd.Series) -> np.ndarray:
    """`settlement._is_true`, applied to a column, and equal to it value by value.

    Not a second copy of the truth reading: the distinct values of the column
    are handed to `settlement._is_true` itself and the answers are mapped back,
    so there is one definition and this is a lookup over it. A `did_not_play`
    column has two distinct values in every real frame, so the cost is two
    calls and one `map`.

    The bug this is arranged against is written down in `settlement`'s own
    docstring: a CSV round-trip turns `True` into the string `"True"`, and
    `bool("False")` is `True`, so reading this column with `bool()` marks every
    player who **did** play as absent and voids the entire prop book.
    """
    if series.dtype == bool:
        return series.to_numpy(dtype=bool)
    answers: dict = {}
    for value in pd.unique(series):
        try:
            answers[value] = settlement._is_true({_DNP: value}, _DNP) is True
        except TypeError:  # an unhashable cell: it is not a boolean either
            continue
    mapped = series.map(answers)
    return mapped.fillna(False).to_numpy(dtype=bool)


def _latest_day(frame: pd.DataFrame | None) -> str:
    """The maximum `slate_date` in a frame, or `""`.

    The same rule `price_backtest.latest_day` applies, restated here only so
    `models/` need not import `reports/` — an edge that does not exist in this
    tree. `tests/test_player_rates.py` asserts the two agree, including on the
    literal string `"nan"`, which sorts above every real date.
    """
    if frame is None or len(frame) == 0 or SLATE_DAY_COLUMN not in frame.columns:
        return ""
    days = frame[SLATE_DAY_COLUMN].dropna().astype(str)
    days = days[(days != "") & (days.str.strip().str.lower() != "nan")]
    return "" if days.empty else str(days.max())


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.full(len(frame), np.nan), index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _assert_declared_agrees(shapes: PlayerShapes) -> None:
    """The thresholds enforced here are the ones the frozen file declares.

    Two copies of a threshold is how a fit and a price come to refuse different
    populations while both look correct. This raises rather than warns, because
    a drifted threshold does not fail — it prices a population the constants
    were not fitted for, and nothing downstream can see that.
    """
    declared = shapes.document.get("declared") or {}
    expected = {
        "bucket_edges": list(BUCKET_EDGES),
        "bucket_labels": list(BUCKET_LABELS),
        "minutes_support": list(MINUTES_SUPPORT),
        "refusal_thresholds": {
            "min_prior_games": MIN_PRIOR_GAMES,
            "min_prior_minutes": MIN_PRIOR_MINUTES,
            "min_projected_minutes": MIN_PROJECTED_MINUTES,
        },
        "prior_season_min_games": PRIOR_SEASON_MIN_GAMES,
    }
    drifted = {
        name: (declared.get(name), value)
        for name, value in expected.items()
        if declared.get(name) != value
    }
    if drifted:
        raise PlayerRatesError(
            f"{shapes.path}: the `declared` block and the thresholds this "
            f"estimator enforces disagree on {sorted(drifted)}. The file says "
            f"{ {k: v[0] for k, v in drifted.items()} } and this module says "
            f"{ {k: v[1] for k, v in drifted.items()} }. The `declared` block "
            "carries no fit window and the provenance guard does not inspect "
            "it, so this equality is the only thing holding the two copies "
            "together; it is refused rather than reconciled."
        )


# --------------------------------------------------------------------------
# The prior roster, and reading a name against it
# --------------------------------------------------------------------------


def prior_roster(
    player_history: pd.DataFrame,
    *,
    day: str,
    season: int,
    team_ids: Sequence[object],
) -> pd.DataFrame:
    """R1a's roster: rows for either team, strictly earlier, never tonight.

    "Strictly earlier" is two conditions and both are applied: `slate_date <
    day`, and a season of either this one or the one before it. The frame that
    reaches this module has already been cut by `history_before` at the caller;
    the day filter here narrows and can never widen, and it is what makes this
    function's name true when it is called directly rather than through
    :func:`player_projections_for`.

    The prior season is here for the ROSTER and not for the bank. The fitter
    resets every trailing bank at the season boundary and says outright that
    admitting carry-over "would need a decay constant nobody has fitted", so a
    returning senior is a name this lab recognises and an evidence bank of
    zero, and R2 refuses him for his first four appearances. That is the
    largest single driver of the November refusal census.
    """
    if player_history is None or len(player_history) == 0:
        return player_history if player_history is not None else pd.DataFrame()
    frame = player_history
    if SLATE_DAY_COLUMN in frame.columns:
        # Character for character `price_backtest.history_before`'s comparison.
        # That module's own docstring names the cost of a second copy: "the
        # football lab's defect 13 was the same comparison written with `<=` in
        # one of its two places."
        frame = frame[frame[SLATE_DAY_COLUMN].astype(str) < str(day)]
    seasons = _numeric(frame, "season")
    frame = frame[seasons.isin([int(season), int(season) - 1])]
    if "team_id" in frame.columns and team_ids is not None:
        wanted = {_id_key(team) for team in team_ids}
        frame = frame[frame["team_id"].map(_id_key).isin(wanted)]
    return frame


def _id_key(value: object) -> object:
    """One key type for an id that arrives as 147, 147.0 and "147.0".

    `providers.player_names._game_key` records this bug family wearing an id;
    the team side of the join has it too, and a team id read as a float from a
    CSV round-trip and as an int from a parquet read is the same team.
    """
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        text = clean_text(value)
        return text or None


def _prior_index(roster: pd.DataFrame, *, event_id: str) -> player_names.PlayerIndex:
    """A `PlayerIndex` over PRIOR rows, keyed by the event rather than the game.

    `providers.player_names.build_index` cannot be used at price time and this
    is the only reason why: it keys `(game_id, alias)` off the box-score rows
    **of the game itself**, so resolving tonight's spelling against it is
    exactly the R1a leak. The class is reused unchanged — so R1's readings, its
    abbreviation asymmetry and its ambiguity rule are the settlement resolver's
    own code and not a second copy — and only what goes into it changes:
    distinct (athlete, spelling) pairs from prior games, filed under the
    event's id in the slot `game_id` occupies. `_game_key` already falls
    through to the string form, which a 32-character event id takes.
    """
    index = player_names.PlayerIndex()
    if roster is None or len(roster) == 0:
        return index
    columns = [c for c in ("athlete_id", "athlete_display_name", "team_id") if c in roster.columns]
    seen: set = set()
    for record in roster[columns].to_dict("records"):
        athlete = record.get("athlete_id")
        name = record.get("athlete_display_name")
        marker = (_athlete_key(athlete), clean_text(name))
        if marker in seen:
            continue
        seen.add(marker)
        index.add(event_id, athlete, name, dict(record))
    return index


def _athlete_key(value: object) -> object:
    """An athlete id rendered the same whether it arrived as 3149059 or 3149059.0."""
    return _id_key(value)


def resolve_subject(provider_name: str, *, roster: pd.DataFrame) -> Resolution:
    """R1's cascade. There is no fuzzy terminal step, and more than one refuses.

    Design C's `difflib >= 0.88` is deleted and stays deleted: combined with
    R1a it has no correct answer available for a debutant and will confidently
    match the nearest teammate. Zero candidates and two candidates are
    different facts and are refused with different sentences, because one is a
    player this lab has not seen and the other is a name it cannot read.

    The roster handed in must already be a PRIOR roster — this function does
    not cut, and cutting inside it would be a second definition of what "prior"
    means. :func:`player_projections_for` cuts once, with :func:`prior_roster`.
    """
    spelling = clean_text(provider_name)
    if not spelling:
        return Resolution(refusal=R1_UNRESOLVED)
    if roster is None or len(roster) == 0:
        return Resolution(refusal=R1B_NO_PRIOR_ROSTER, in_tonights_box_only=False)
    index = _prior_index(roster, event_id="__subject__")
    return _resolve_against(index, event_id="__subject__", provider_name=spelling)


def _resolve_against(
    index: player_names.PlayerIndex, *, event_id: str, provider_name: str
) -> Resolution:
    found = index.candidates(event_id, provider_name)
    if len(found) > 1:
        return Resolution(candidates=len(found), refusal=R1_UNRESOLVED)
    if not found:
        return Resolution(candidates=0, refusal=R1A_TONIGHT_ONLY, in_tonights_box_only=True)
    row = found[0]
    display = clean_text(row.get("athlete_display_name"))
    return Resolution(
        athlete_id=row.get("athlete_id"),
        display_name=display,
        route=_route_for(provider_name, display),
        candidates=1,
    )


def _route_for(provider_name: str, display_name: str) -> str:
    """Which reading did the work, named for what the resolver actually does."""
    asked = player_names.normalise(provider_name)
    if asked and asked == player_names.normalise(display_name):
        return ROUTE_EXACT
    first = asked.split()[0] if asked else ""
    if len(first) == 1:
        return ROUTE_INITIAL
    return ROUTE_VARIANT


# --------------------------------------------------------------------------
# The trailing bank
# --------------------------------------------------------------------------


def trailing_evidence(roster: pd.DataFrame, *, half_life: float) -> pd.DataFrame:
    """Per (season, athlete), the evidence a pricer holds before the next game.

    Every column is over **played rows only** and over rows that are all
    strictly prior, because the frame reaching this function has already been
    cut at `slate_date < day`. The bank resets at every season boundary: there
    is no cross-season carry-over, exactly as `fit_player_model.with_trailing`
    has none, and admitting one would need a decay constant nobody has fitted.

    This is the same estimator as the fitter's, and it may not import it:
    `tests/test_player_shapes_provenance.py::test_the_fit_script_is_not_
    importable_from_the_model_package` fails any module under `src/` that names
    `fit_player_model`, because that script reads the whole settlement table.
    Two copies of an estimator is how two windows come to disagree, so
    `tests/test_player_rates.py::test_the_estimator_reproduces_the_fitters_
    trailing_columns` holds this function against the fitter's row-level
    columns for every row of a fixture: the fitter's trailing values on row *i*
    are what this function returns when handed the rows strictly before *i*.

    Returned columns: `projected_minutes` (EWMA of minutes over played games,
    evaluated at the last played row), `prior_games`, `prior_minutes`,
    `bank_<stat>` for every :data:`STAT_KEYS` entry, and `bank_ones`,
    `bank_twos`, `bank_threes` for the value mix. Indexed by
    `(season, athlete_key)`.
    """
    prepared = _prepare(roster)
    columns = [
        "projected_minutes",
        "prior_games",
        "prior_minutes",
        *[f"bank_{stat}" for stat in STAT_KEYS],
        # `bank_threes` is deliberately NOT repeated here: the value mix's
        # three-point component and the `threes` rate's bank are the same
        # column of the box score (`three_point_field_goals_made`), and listing
        # it twice makes `row["bank_threes"]` a Series rather than a number.
        "bank_ones",
        "bank_twos",
        "team_id",
        "opponent_id",
        "athlete_display_name",
    ]
    if prepared.empty:
        empty = pd.DataFrame(columns=columns)
        empty.index = pd.MultiIndex.from_arrays([[], []], names=["season", "athlete"])
        return empty

    played = prepared[prepared["played"]].copy()
    keys = ["season", "athlete"]
    grouped_all = prepared.groupby(keys, sort=False)
    out = pd.DataFrame(index=grouped_all.size().index)

    # The last team the athlete appeared for, and the display name he appeared
    # under. Taken from the LAST row rather than the first: a transfer's rows
    # carry two team ids and the current one is the later.
    out["team_id"] = grouped_all["team_id"].last()
    out["opponent_id"] = grouped_all["opponent_id"].last()
    out["athlete_display_name"] = grouped_all["athlete_display_name"].last()

    if played.empty:
        out["projected_minutes"] = np.nan
        out["prior_games"] = 0
        out["prior_minutes"] = 0.0
        for column in [f"bank_{s}" for s in STAT_KEYS] + ["bank_ones", "bank_twos"]:
            out[column] = 0.0
        return out[columns]

    grouped = played.groupby(keys, sort=False)
    out["prior_games"] = grouped.size().reindex(out.index).fillna(0).astype(int)
    out["prior_minutes"] = grouped["minutes"].sum().reindex(out.index).fillna(0.0)
    for stat in STAT_KEYS:
        out[f"bank_{stat}"] = grouped[stat].sum().reindex(out.index).fillna(0.0)
    for part in ("ones", "twos"):
        out[f"bank_{part}"] = grouped[part].sum().reindex(out.index).fillna(0.0)

    # The EWMA, computed exactly as the fitter computes it: pandas' own
    # `.ewm(halflife=...)` with the default `adjust=True`, over the PLAYED
    # subsequence only, and read at the last played row. A hand-rolled
    # recursion here would be a second estimator with a different bias at the
    # start of a group, which is where every projection in November lives.
    ewma = (
        played.groupby(keys, sort=False)["minutes"]
        .apply(lambda values: values.ewm(halflife=float(half_life)).mean().iloc[-1])
    )
    out["projected_minutes"] = ewma.reindex(out.index)
    return out[columns]


def _prepare(roster: pd.DataFrame) -> pd.DataFrame:
    """The columns the estimator shares, sorted the way the fitter sorts them.

    Did-not-play rows are kept rather than dropped at the door, because the
    minutes projection has to exist *on* them: a projection built only where a
    player appeared cannot say what was expected of the night he sat, and that
    is the whole content of the stored `dnp_probability` diagnostic. `played`
    is `appeared AND minutes is a number AND minutes >= 1.0`, which is the
    fitter's rule; a row logged as having appeared and carrying no minutes
    cannot produce a per-minute rate and is counted in neither bucket.
    """
    if roster is None or len(roster) == 0:
        return pd.DataFrame()
    out = pd.DataFrame(index=roster.index)
    out["season"] = _numeric(roster, "season")
    out["athlete"] = roster["athlete_id"].map(_athlete_key) if "athlete_id" in roster else None
    out["slate_date"] = (
        roster[SLATE_DAY_COLUMN].astype(str)
        if SLATE_DAY_COLUMN in roster.columns
        else ""
    )
    out["game_id"] = _numeric(roster, "game_id")
    out["team_id"] = roster["team_id"] if "team_id" in roster.columns else None
    out["opponent_id"] = roster["opponent_id"] if "opponent_id" in roster.columns else None
    out["athlete_display_name"] = (
        roster["athlete_display_name"].map(clean_text)
        if "athlete_display_name" in roster.columns
        else ""
    )
    out["minutes"] = _numeric(roster, "minutes")
    appeared = (
        ~_did_not_play(roster[_DNP])
        if _DNP in roster.columns
        else np.ones(len(roster), dtype=bool)
    )
    out["appeared"] = appeared
    out["played"] = appeared & out["minutes"].notna().to_numpy() & (
        out["minutes"].fillna(0.0).to_numpy() >= 1.0
    )

    if _has_stat_columns(roster):
        threes = _numeric(roster, "three_point_field_goals_made").fillna(0.0)
        out["threes"] = threes
        out["twos"] = _numeric(roster, "field_goals_made").fillna(0.0) - threes
        out["ones"] = _numeric(roster, "free_throws_made").fillna(0.0)
        out["points_events"] = out["ones"] + out["twos"] + out["threes"]
        for column in ("points", "rebounds", "assists", "steals", "turnovers"):
            out[column] = _numeric(roster, column).fillna(0.0)
    else:
        for column in (*STAT_KEYS, "ones", "twos"):
            out[column] = np.nan

    out = out[out["athlete"].notna() & out["season"].notna()]
    out = out.sort_values(
        ["season", "athlete", "slate_date", "game_id"], kind="mergesort"
    )
    return out.reset_index(drop=True)


def _has_stat_columns(frame: pd.DataFrame) -> bool:
    return all(column in frame.columns for column in REQUIRED_STAT_COLUMNS)


def _missing_stat_columns(frame: pd.DataFrame) -> list[str]:
    return [column for column in REQUIRED_STAT_COLUMNS if column not in frame.columns]


def minutes_projection(
    evidence: pd.DataFrame, *, athlete_id: object
) -> tuple[float, int, float]:
    """`(projected_minutes, prior_games, prior_minutes)` as of the cut frame.

    Reads the evidence frame :func:`trailing_evidence` returned and nothing
    else. An athlete with no row there has no projection at all, which is R3
    and is a refusal rather than a zero.
    """
    key = _athlete_key(athlete_id)
    rows = evidence[evidence.index.get_level_values("athlete") == key]
    if rows.empty:
        return float("nan"), 0, 0.0
    row = rows.iloc[-1]
    projected = float(row["projected_minutes"])
    return projected, int(row["prior_games"]), float(row["prior_minutes"])


def role_prior_bucket(projected_minutes: float, *, bucket_edges: Sequence[float]) -> int:
    """`np.digitize(v, edges, right=False)`; -1 where there is no projection.

    The same function the fitter's `bucket_of` is, so the bucket a rate was
    fitted in is the bucket it is priced in. Buckets are over PROJECTED
    minutes; using realised minutes here would be screening on the game being
    priced, which is L9.
    """
    value = float(projected_minutes)
    if not math.isfinite(value):
        return -1
    return int(np.digitize(value, np.asarray(bucket_edges, dtype=float), right=False))


# --------------------------------------------------------------------------
# The minutes lattice
# --------------------------------------------------------------------------


def tilt_to_mean(
    pmf: Sequence[float], *, support: Sequence[float], target: float
) -> np.ndarray:
    """Exponentially tilt a lattice pmf to a target mean, over any support.

    `distributions.tilt_to_efficiency` is the same operation and cannot be
    imported for this: `distributions._POINTS` is a module-level `arange(6)`
    and the support check refuses any target above 5.0, so calling it with a
    45-long minutes base raises `DistributionError("Points per possession of
    24.0 is outside the support (0.0, 5.0)")`. That is a real disagreement with
    design 3, which says to import it.

    So the method is copied and the support is a parameter, and
    `test_tilt_to_mean_reproduces_tilt_to_efficiency_on_the_six_point_lattice`
    asserts the two agree to 1e-12 on that lattice — which is what makes this
    provably the same operation rather than a second one.

    Refuses rather than clips when the target is at or beyond the support's
    ends: the tilt has no solution there, and a clipped mean is an absurd
    projection wearing a plausible price.
    """
    weights = np.asarray(pmf, dtype=float)
    points = np.asarray(support, dtype=float)
    if weights.ndim != 1 or weights.size < 2 or np.any(weights < 0):
        raise PlayerRatesError("The lattice handed to `tilt_to_mean` is not a pmf.")
    if points.shape != weights.shape:
        raise PlayerRatesError(
            f"The support has {points.size} points and the pmf has "
            f"{weights.size}; a tilt over two different lattices is two "
            "different distributions."
        )
    total = weights.sum()
    if not math.isfinite(float(total)) or total <= 0:
        raise PlayerRatesError("The lattice handed to `tilt_to_mean` has no mass.")
    weights = weights / total
    goal = float(target)
    lowest, highest = float(points.min()), float(points.max())
    if not lowest < goal < highest:
        raise PlayerRatesError(
            f"A mean of {goal} is outside the support ({lowest}, {highest}) of "
            "the measured shape. There is no tilt that reaches it, and "
            "clipping it silently is how an absurd projection becomes a "
            "plausible price."
        )
    theta = 0.0
    for _ in range(64):
        tilted = weights * np.exp(theta * points)
        tilted /= tilted.sum()
        mean = float(tilted @ points)
        variance = float(tilted @ (points**2)) - mean**2
        theta += (goal - mean) / max(variance, 1e-12)
        if abs(goal - mean) < 1e-13:
            break
    tilted = weights * np.exp(theta * points)
    return tilted / tilted.sum()


def minutes_lattice(
    *, projected_minutes: float, bucket: int, shapes: PlayerShapes
) -> tuple[float, ...]:
    """The 46-long minutes pmf, index == minutes, with EXACTLY zero at zero.

    The mass at zero is not a rounding convention and not a small number. The
    book **voids** a did-not-play, so the quantity a prop prices is
    `P(stat > line | the wager stands)` — conditional on him appearing — and a
    lattice carrying `P(0 minutes)` would discount every projection by the
    chance of a void that pays nothing back. `dnp_probability` is stored beside
    this as a diagnostic and never enters here: this function does not receive
    it and cannot read it.

    The base is the empirical pmf for the projected-minutes bucket, fitted on
    2019-2022 over support 1..45 (multi-overtime nights folded onto 45 rather
    than dropped, which the fit reports), then tilted to the projected mean —
    so the bucket supplies the shape and the athlete supplies the level. The
    bucket means the file carries run 6.73, 10.10, 14.03, 18.32, 22.44, 26.50,
    30.19, 33.46, 36.22.
    """
    table = shapes.value("minutes_pmf")
    low, high = int(table["support_low"]), int(table["support_high"])
    if (low, high) != MINUTES_SUPPORT:
        raise PlayerRatesError(
            f"{shapes.path}: the minutes pmf declares support ({low}, {high}) "
            f"and this module declares {MINUTES_SUPPORT}. The lattice index is "
            "the number of minutes, so a support that moved would silently "
            "renumber every rung."
        )
    rows = table["pmf"]
    if not 0 <= int(bucket) < len(rows):
        raise PlayerRatesError(
            f"Bucket {bucket} is outside the {len(rows)} the frozen file "
            "carries; a projection with no bucket is R3, not a default."
        )
    base = rows[int(bucket)]
    if base is None:
        raise PlayerRatesError(
            f"{shapes.path}: bucket {BUCKET_LABELS[int(bucket)]!r} of the "
            "minutes pmf is null, so this bucket was never fitted and there is "
            "no shape to tilt."
        )
    support = np.arange(low, high + 1, dtype=float)
    tilted = tilt_to_mean(base, support=support, target=float(projected_minutes))
    lattice = np.zeros(high + 1, dtype=float)
    lattice[low : high + 1] = tilted
    return tuple(float(value) for value in lattice)


# --------------------------------------------------------------------------
# Shrinkage
# --------------------------------------------------------------------------


def shrink_rate(
    *, bank_stat: float, prior_minutes: float, prior_rate: float, k: float
) -> tuple[float, float]:
    """`(r_c, w_c)`: the credibility-weighted per-minute rate and its weight.

        w_c = prior_minutes / (prior_minutes + k_c)
        r_c = w_c * (bank_c / prior_minutes) + (1 - w_c) * role_prior_c[bucket]

    `k` is in prior **minutes**, and the observed rate is the bank over the
    bank's minutes — minutes-weighted, never per-game-averaged, because a
    four-minute night must not weigh what a thirty-four-minute night says.

    Public so `tests/test_player_rates.py` can compose the coincident-window
    identity with `w` forced to 1.0. That is deliberate and it is why there is
    no `shrinkage: bool = True` flag on the estimator: this repository treats a
    mode flag as the `strict=False` a guard cannot have, and a test that needs
    the unshrunk number can build it from this function rather than ask the
    estimator to stop being itself.

    At the R2 floor of 60 prior minutes the weight for points is
    `60 / (60 + 102.834) = 0.3685`, which is the measured reason R2 refuses
    there: below it the majority of the projection is an average player in this
    role, published under a named player's name.
    """
    minutes = float(prior_minutes)
    denominator = minutes + float(k)
    if not math.isfinite(minutes) or minutes <= 0 or denominator <= 0:
        return float(prior_rate), 0.0
    weight = minutes / denominator
    observed = float(bank_stat) / minutes
    return weight * observed + (1.0 - weight) * float(prior_rate), weight


def shrink_value_mix(
    *,
    bank_ones: float,
    bank_twos: float,
    bank_threes: float,
    league: Sequence[float],
    k_events: float,
) -> tuple[tuple[float, float, float], float, float]:
    """`(mix, prior_events, weight)`: the player's own 1/2/3 split, shrunk.

    The bank is in prior **scoring events** — a made free throw, a made two, a
    made three — and `k_events` is fitted in the same unit, by minimising the
    multinomial deviance of the next game's realised mix. At the frozen
    9.2201 events a player with 10 prior scoring events already carries weight
    0.5203, which is why this shrinks much faster than the rate does.

    This is what makes `player_threes` fall out of the points object rather
    than arrive as a separate count: a centre and a shooting guard with the
    same points rate have different mixes and therefore different three
    distributions.
    """
    shape = np.asarray(league, dtype=float)
    bank = np.array([float(bank_ones), float(bank_twos), float(bank_threes)])
    if shape.shape != (3,) or np.any(shape < 0) or not math.isclose(
        float(shape.sum()), 1.0, rel_tol=0.0, abs_tol=1e-9
    ):
        raise PlayerRatesError(
            f"The league value pmf {list(shape)} is not a three-point pmf. A "
            "scoring event is worth one, two or three points and nothing else."
        )
    events = float(bank.sum())
    if not math.isfinite(events) or events <= 0:
        return (float(shape[0]), float(shape[1]), float(shape[2])), 0.0, 0.0
    weight = events / (events + float(k_events))
    mix = weight * (bank / events) + (1.0 - weight) * shape
    return (float(mix[0]), float(mix[1]), float(mix[2])), events, weight


def mean_for_market(projection: PlayerProjection, market_key: str) -> float:
    """`mu` for one market: the components' rates times the shared minutes.

    The combination markets are built from components over the **shared**
    minutes draw, never from their own history, so a points line and a pra line
    on one player cannot disagree. That is design 5's coherence identity D3 and
    `tests/test_player_rates.py` asserts it to 1e-9 off this function.

    A mean, not a probability. Nothing here selects a bet and nothing can:
    turning a mean into a price needs `models/player_distributions.py`, which
    is not written.
    """
    components = MARKET_COMPONENTS.get(market_key)
    if components is None:
        raise PlayerRatesError(
            f"{market_key!r} is not one of the ten markets this model is "
            f"registered against: {', '.join(PRICED_MARKETS)}. "
            + (
                MARKETS_REFUSED_BY_NAME[market_key]
                if market_key in MARKETS_REFUSED_BY_NAME
                else "It is not refused by name either, so it is a key nothing "
                "here has an opinion about."
            )
        )
    minutes = float(projection.projected_minutes)
    total = 0.0
    for stat in components:
        if stat not in projection.rates:
            return float("nan")
        total += float(projection.rates[stat]) * minutes
    return total


# --------------------------------------------------------------------------
# The construction site
# --------------------------------------------------------------------------


def player_projections_for(
    *,
    day: str,
    player_history: pd.DataFrame,
    prices: pd.DataFrame,
    shapes: PlayerShapes,
    competition: Competition = CBB,
    tiers: TierTable | None = None,
) -> PlayerSlate:
    """Every athlete the book quoted on `day`, projected or refused.

    Keyword-only, and every frame parameter is **without a default**:
    `price_backtest._refuse_undeclared_frames` refuses a pricer whose frame
    parameter carries a default and refuses `**kwargs` on sight. This module
    sits behind that seam and must not undo it.

    `player_history` must already be cut at `slate_date < day` — the cut is
    `history_before`, made once, at the caller, and forking it would be a
    second definition of what "before" means. The frame is checked here anyway,
    because a guard whose floor comes only from the thing it guards cannot see
    that thing get the floor wrong.

    The subjects are read off `prices`: the distinct (event_id, player) pairs of
    the day's PLAYER-family rows. That is what stops the resolution census
    double-counting the roughly 7.2 ladder rungs a points subject carries
    (design 13, failure mode 2 — quoted, not re-measured here). A market
    refused by name contributes its subjects to the census and no projection.

    Returns a :class:`PlayerSlate`. A subject with no entry in `projections` is
    **no opinion**; an entry with `priceable=False` is a **refusal**; a pair in
    `name_refusals` is a refusal with no athlete at all. The three are counted
    separately, always, and `models/slate.py` asserts that `resolved` and
    `name_refusals` are disjoint and that their union is exactly the day's
    distinct pairs.
    """
    _refuse_a_competition_these_constants_were_not_fitted_on(competition)
    _assert_declared_agrees(shapes)
    priced_through = _latest_day(player_history)
    _refuse_a_frame_that_reaches_the_day(player_history, day=day)

    subjects, quotes, events = _subjects_of_the_day(prices)
    if not subjects:
        return PlayerSlate(priced_through=priced_through, resolution_census={})

    season = season_for_slate_date(day)
    half_life = float(shapes.value("minutes_half_life"))
    missing_columns = _missing_stat_columns(player_history)

    pool = prior_roster(
        player_history,
        day=day,
        season=season,
        team_ids=[team for event in events.values() for team in event["teams"]],
    )
    # One `_id_key` pass over the day's pool, not one per event. The pool is the
    # cut frame narrowed to two seasons and the board's teams; on a full slate
    # that is tens of thousands of rows and a hundred and fifty games, and a
    # per-event Python map over it is the difference between a second and a
    # minute a day over the 140 quoted days.
    pool = pool[[c for c in _POOL_COLUMNS if c in pool.columns]].copy()
    pool["_team_key"] = (
        pool["team_id"].map(_id_key) if "team_id" in pool.columns else None
    )
    pool_seasons = _numeric(pool, "season")

    projections: dict[str, dict[object, PlayerProjection]] = {}
    resolved: dict[tuple[str, str], object] = {}
    refusals: dict[tuple[str, str], str] = {}
    census: dict[str, int] = {}

    for event_id, spellings in subjects.items():
        detail = events[event_id]
        wanted = {_id_key(team) for team in detail["teams"]}
        on_this_game = pool["_team_key"].isin(wanted) if wanted else pool["_team_key"].notna()
        roster = pool[on_this_game]
        index = _prior_index(roster, event_id=event_id)
        evidence = trailing_evidence(
            pool[on_this_game & (pool_seasons == season)], half_life=half_life
        )

        for spelling in spellings:
            key = (event_id, spelling)
            weight = quotes.get(key, 0)
            if len(roster) == 0:
                refusals[key] = R1B_NO_PRIOR_ROSTER
                _tally(census, ROUTE_REFUSED_NO_ROSTER, weight)
                continue
            resolution = _resolve_against(
                index, event_id=event_id, provider_name=spelling
            )
            if not resolution.resolved:
                refusals[key] = resolution.refusal
                _tally(
                    census,
                    ROUTE_REFUSED_DEBUTANT
                    if resolution.in_tonights_box_only
                    else ROUTE_REFUSED_NAME,
                    weight,
                )
                continue

            projection = _project(
                day=day,
                event_id=event_id,
                game_id=detail["game_id"],
                provider_name=spelling,
                resolution=resolution,
                evidence=evidence,
                shapes=shapes,
                tiers=tiers,
                priced_through=priced_through,
                missing_columns=missing_columns,
            )
            athlete = _athlete_key(resolution.athlete_id)
            projections.setdefault(event_id, {})[athlete] = projection
            resolved[key] = athlete
            _tally(census, resolution.route, weight)

    return PlayerSlate(
        projections=projections,
        resolved=resolved,
        name_refusals=refusals,
        priced_through=priced_through,
        resolution_census=census,
    )


def _tally(census: dict[str, int], route: str, quotes: int) -> None:
    """One subject and its rungs, counted apart. A rung is not an opinion."""
    census[route] = census.get(route, 0) + 1
    census[f"quotes:{route}"] = census.get(f"quotes:{route}", 0) + int(quotes)


def _refuse_a_frame_that_reaches_the_day(frame: pd.DataFrame, *, day: str) -> None:
    if frame is None or len(frame) == 0 or SLATE_DAY_COLUMN not in frame.columns:
        return
    days = frame[SLATE_DAY_COLUMN].astype(str)
    reaching = days[days >= str(day)]
    if len(reaching):
        raise PlayerRatesError(
            f"the player frame handed to the estimator for {day} carries "
            f"{len(reaching):,} row(s) dated {reaching.min()} or later, which "
            "is not strictly earlier than the day being priced. The cut is "
            "`history_before`, made once at the caller; this is the "
            "construction site refusing to project from a frame that reaches "
            "the game it is projecting."
        )


def _refuse_a_competition_these_constants_were_not_fitted_on(
    competition: Competition,
) -> None:
    """The frozen constants are college basketball box scores, and only those.

    `competition` is taken because every model in this tree declares it and
    `slate_model` passes it through; it is not decoration. A role prior of
    0.4395 points per minute in the 36+ bucket is a fact about this sport, and
    handing these shapes another competition's frame would price it with
    numbers nobody fitted for it — the shape leak `models/player_shapes.py`
    exists to refuse, wearing a sport instead of a season.
    """
    if competition.key != CBB.key:
        raise PlayerRatesError(
            f"the frozen player constants were fitted on {CBB.key} box scores "
            f"and this is a price for {competition.key}. There is no shapes "
            "file for it, and reusing these would be the season-leak refusal "
            "wearing a sport: a constant used where nobody measured it."
        )


def _subjects_of_the_day(prices: pd.DataFrame):
    """The distinct (event, spelling) pairs on this frame, their rungs, their teams.

    The caller supplies the day's price frame — `walk_forward` hands the pricer
    one day at a time — so there is no day filter here and none is wanted: a
    second definition of which rows belong to a day is how two cuts come to
    disagree.

    Distinct PAIRS, not rows: `player_points` carries a measured mean of 7.19
    lines per subject across a mean 4.6 books (design 10, quoted), so counting
    rows would report a resolution census of ladder rungs and call it a census
    of players.

    **A market refused by name contributes no subject.** This used to select
    every key whose family is PLAYER, so a `player_first_basket` rung put its
    athlete into the subject set, resolved him, gave him a full priceable
    projection, and tallied him into the resolution census — for a market the
    design refused before the run. Two things went wrong with that. The
    projection is one the design says must not exist, and the per-tier
    resolution rate that design 13 failure mode 5 stops the run on at 2pp was
    being computed over a board including two refused markets' quotes, so the
    gate was reading a different board from the one being priced.

    A subject quoted ONLY on refused markets therefore disappears from the
    census entirely, which is correct: he is not a subject of this model. A
    subject quoted on both keeps his projection, from the priced rungs alone.
    """
    subjects: dict[str, list[str]] = {}
    quotes: dict[tuple[str, str], int] = {}
    events: dict[str, dict] = {}
    if prices is None or len(prices) == 0 or "market" not in prices.columns:
        return subjects, quotes, events
    if "player" not in prices.columns or "event_id" not in prices.columns:
        return subjects, quotes, events

    player_keys = {
        market.key
        for market in MARKETS_BY_KEY.values()
        if market.family == PLAYER and market.key not in MARKETS_REFUSED_BY_NAME
    }
    frame = prices[prices["market"].map(clean_text).isin(player_keys)]
    if len(frame) == 0:
        return subjects, quotes, events

    for record in frame.to_dict("records"):
        event_id = clean_text(record.get("event_id"))
        spelling = clean_text(record.get("player"))
        if not event_id or not spelling:
            continue
        key = (event_id, spelling)
        quotes[key] = quotes.get(key, 0) + 1
        if key[1] not in subjects.setdefault(event_id, []):
            subjects[event_id].append(spelling)
        if event_id not in events:
            events[event_id] = {
                "game_id": record.get("game_id"),
                "teams": tuple(
                    team
                    for team in (record.get("home_team"), record.get("away_team"))
                    if _id_key(team) is not None
                ),
            }
    return subjects, quotes, events


def _project(
    *,
    day: str,
    event_id: str,
    game_id: object,
    provider_name: str,
    resolution: Resolution,
    evidence: pd.DataFrame,
    shapes: PlayerShapes,
    tiers: TierTable | None,
    priced_through: str,
    missing_columns: Sequence[str],
) -> PlayerProjection:
    """One athlete, projected or refused, with the refusals in a fixed order.

    The order is R5, then R3's "no projection at all", then R2, then R3's floor
    of eight, then R4 and the lattice, then R6. It is fixed here rather than
    left to whichever check runs first because a subject failing two refusals
    is counted under one of them, and a census whose buckets depend on
    evaluation order is a census that moves when the code is tidied.
    """
    athlete = _athlete_key(resolution.athlete_id)
    rows = evidence[evidence.index.get_level_values("athlete") == athlete]
    row = rows.iloc[-1] if len(rows) else None
    team_id = row["team_id"] if row is not None else None
    opponent_id = row["opponent_id"] if row is not None else None
    tier = (
        tiers.tier_for(team_id).value if tiers is not None else Tier.UNPLACED.value
    )
    base = dict(
        event_id=event_id,
        game_id=game_id,
        athlete_id=resolution.athlete_id,
        display_name=resolution.display_name,
        provider_name=provider_name,
        team_id=team_id,
        opponent_id=opponent_id,
        player_tier=tier,
        resolution_route=resolution.route,
        priced_through=priced_through,
    )

    refused_stats, structural = _unfittable(shapes)
    if structural:
        return PlayerProjection(
            **base,
            priceable=False,
            unpriceable_reason=f"{R5_NO_WALK_FORWARD_FIT} {structural}",
            refused_stats=refused_stats,
        )

    projected, prior_games, prior_minutes = minutes_projection(
        evidence, athlete_id=resolution.athlete_id
    )
    bucket = role_prior_bucket(projected, bucket_edges=BUCKET_EDGES)
    dnp = _dnp_probability(shapes, bucket)
    base.update(
        projected_minutes=projected,
        minutes_bucket=bucket,
        prior_minutes=prior_minutes,
        prior_games=prior_games,
        dnp_probability=dnp,
        refused_stats=refused_stats,
    )

    if not math.isfinite(projected):
        return PlayerProjection(**base, priceable=False, unpriceable_reason=R3_NO_MINUTES)
    if prior_games < MIN_PRIOR_GAMES or prior_minutes < MIN_PRIOR_MINUTES:
        return PlayerProjection(**base, priceable=False, unpriceable_reason=R2_TOO_THIN)
    if projected < MIN_PROJECTED_MINUTES:
        return PlayerProjection(**base, priceable=False, unpriceable_reason=R3_NO_MINUTES)

    try:
        lattice = minutes_lattice(
            projected_minutes=projected, bucket=bucket, shapes=shapes
        )
    except PlayerRatesError as error:
        return PlayerProjection(
            **base,
            priceable=False,
            unpriceable_reason=f"{R4_OUTSIDE_SUPPORT} {error}",
        )
    base.update(minutes_pmf=lattice)

    if missing_columns:
        return PlayerProjection(
            **base,
            priceable=False,
            unpriceable_reason=(
                f"{R6_NO_BOX_SCORE_COLUMNS} Missing: {', '.join(missing_columns)}."
            ),
        )

    rates, weights = _rates(row, shapes=shapes, bucket=bucket, refused=refused_stats)
    mix, events, mix_weight = shrink_value_mix(
        bank_ones=float(row["bank_ones"]),
        bank_twos=float(row["bank_twos"]),
        bank_threes=float(row["bank_threes"]),
        league=shapes.value("value_pmf"),
        k_events=float(shapes.value("value_mix_shrinkage_events")),
    )
    base.update(
        rates=rates,
        prior_weight=weights,
        value_pmf=mix,
        value_prior_events=events,
        value_mix_weight=mix_weight,
    )

    means = [float(rate) * projected for rate in rates.values()]
    if not rates or any(not math.isfinite(mu) for mu in means) or max(means) <= 0.02:
        return PlayerProjection(
            **base, priceable=False, unpriceable_reason=R4_OUTSIDE_SUPPORT
        )
    return PlayerProjection(**base, priceable=True, unpriceable_reason="")


def _rates(
    row, *, shapes: PlayerShapes, bucket: int, refused: Mapping[str, str]
) -> tuple[dict[str, float], dict[str, float]]:
    priors = shapes.value("role_prior")
    ks = shapes.value("rate_shrinkage_k")
    rates: dict[str, float] = {}
    weights: dict[str, float] = {}
    for stat in STAT_KEYS:
        if stat in refused:
            continue
        rate, weight = shrink_rate(
            bank_stat=float(row[f"bank_{stat}"]),
            prior_minutes=float(row["prior_minutes"]),
            prior_rate=float(priors[stat][bucket]),
            k=float(ks[stat]),
        )
        rates[stat] = rate
        weights[stat] = weight
    return rates, weights


def _unfittable(shapes: PlayerShapes) -> tuple[dict[str, str], str]:
    """R5, read off the frozen file's own `unfittable` block.

    Two levels, because the block's keys are either a constant name or
    `constant.market`. A per-stat refusal drops that stat from `rates` and
    leaves the rest of the projection standing; a whole-constant refusal of
    anything every market needs — the minutes shape, the half-life, the role
    table, the credibility table, the value mix — makes the projection itself
    unpriceable, because there is nothing left to price it with.

    The shipped file's `unfittable` block is empty, so no market is refused by
    the fit today and this path is exercised against a synthetic file.
    """
    refused: dict[str, str] = {}
    for constant in ("role_prior", "rate_shrinkage_k"):
        for stat in STAT_KEYS:
            sentence = shapes.refusal_for(f"{constant}.{stat}")
            if sentence:
                refused[stat] = sentence
    for constant in (
        "minutes_pmf",
        "minutes_half_life",
        "role_prior",
        "rate_shrinkage_k",
        "value_pmf",
        "value_mix_shrinkage_events",
    ):
        sentence = shapes.refusal_for(constant)
        if sentence:
            return refused, f"{constant}: {sentence}"
    return refused, ""


def _dnp_probability(shapes: PlayerShapes, bucket: int) -> float:
    """The bucket's base did-not-play rate, unshrunk, and a DIAGNOSTIC only.

    It is the bucket base rate itself and nothing else, because the frozen file
    carries no credibility constant for it: `dnp_base_rate`'s own note calls it
    "the shrink target for a stored dnp_probability" and no `k` in prior games
    or prior rows was ever fitted, so there is nothing to shrink a player's own
    absence rate toward it with. Inventing one would be a constant with no fit
    window, which is exactly what the provenance guard exists to refuse.

    It is never multiplied into a price. :func:`minutes_lattice` does not
    receive it and cannot read it, and
    `test_the_did_not_play_diagnostic_never_reaches_the_lattice` prices the
    same athlete against two shapes files differing only here and asserts the
    lattice and the rates are bit-identical.
    """
    if bucket < 0:
        return float("nan")
    try:
        table = shapes.value("dnp_base_rate")
    except ShapesFileError:
        return float("nan")
    if not 0 <= bucket < len(table):
        return float("nan")
    return float(table[bucket])


# --------------------------------------------------------------------------
# One subject, for a caller that already has a roster
# --------------------------------------------------------------------------


def projection_for(
    *,
    day: str,
    event_id: str,
    game_id: object,
    home_team_id: object,
    away_team_id: object,
    provider_name: str,
    roster: pd.DataFrame,
    shapes: PlayerShapes,
    tiers: TierTable | None = None,
    priced_through: str,
) -> PlayerProjection:
    """One athlete's projection, or a raise if the name does not resolve.

    A raise rather than a refusing projection, and that is not an oversight:
    R1 and R1a have **no athlete id**, so a `PlayerProjection` carrying one
    would have had to invent it, which is the join-vocabulary bug family in its
    purest form. The caller that wants those refusals wants
    :func:`player_projections_for`, which files them in `name_refusals` keyed
    by the book's spelling exactly as filed.
    """
    _assert_declared_agrees(shapes)
    season = season_for_slate_date(day)
    prior = prior_roster(
        roster, day=day, season=season, team_ids=(home_team_id, away_team_id)
    )
    resolution = resolve_subject(provider_name, roster=prior)
    if not resolution.resolved:
        raise PlayerRatesError(
            f"{provider_name!r} on event {event_id} did not resolve to exactly "
            f"one athlete on the prior roster ({resolution.candidates} "
            f"candidate(s)). {resolution.refusal} There is no athlete id to "
            "hang a projection on, and inventing one is the join-vocabulary "
            "bug family; ask `player_projections_for`, which files this as a "
            "name refusal keyed by the spelling as the book filed it."
        )
    evidence = trailing_evidence(
        prior[_numeric(prior, "season") == season] if len(prior) else prior,
        half_life=float(shapes.value("minutes_half_life")),
    )
    return _project(
        day=day,
        event_id=event_id,
        game_id=game_id,
        provider_name=clean_text(provider_name),
        resolution=resolution,
        evidence=evidence,
        shapes=shapes,
        tiers=tiers,
        priced_through=priced_through,
        missing_columns=_missing_stat_columns(roster),
    )


# --------------------------------------------------------------------------
# Censuses. A refusal and an absence are never summed.
# --------------------------------------------------------------------------


def refusal_census(
    projections: Mapping[str, Mapping[object, PlayerProjection]],
) -> Mapping[str, int]:
    """How many athletes each refusal turned away, by the refusal's first words.

    Keyed by the leading clause of the sentence rather than by a code, so a
    census cannot name a refusal the model does not actually say. `priceable`
    is counted too: a census that only counted refusals could not be read as a
    fraction of anything.
    """
    counts: dict[str, int] = {"priceable": 0}
    for by_athlete in projections.values():
        for projection in by_athlete.values():
            if projection.priceable:
                counts["priceable"] += 1
                continue
            head = projection.unpriceable_reason.split(";")[0].split(".")[0].strip()
            counts[head] = counts.get(head, 0) + 1
    return counts


def resolution_census(
    projections: Mapping[str, Mapping[object, PlayerProjection]],
    *,
    tiers: TierTable,
) -> Mapping[str, Mapping[str, int]]:
    """Per-tier resolution, printed EVERY run (design 13, failure mode 5).

    Computed over **resolved subjects only**, and that is a limitation rather
    than a choice: design 9 tiers a player by `conferences.tier_table` on his
    OWN team, which an unresolved name does not have. Tiering the R1/R1a rows
    by the event's two teams would reintroduce a read from the team side, so
    they are reported under `untiered` by
    :func:`untiered_name_refusals` instead, with their count, and the 2pp tier
    check is stated as being over resolved subjects.

    The measured reason this is printed rather than filed: the team-name
    version of this join failed on **20.5% of provider team names, 46.7% of
    them at the low-major end**, and a join that fails on half the low-major
    board is a biased sample rather than a smaller one.
    """
    out: dict[str, dict[str, int]] = {}
    for by_athlete in projections.values():
        for projection in by_athlete.values():
            tier = projection.player_tier
            if tiers is not None and projection.team_id is not None:
                tier = tiers.tier_for(projection.team_id).value
            bucket = out.setdefault(tier, {"subjects": 0, "priceable": 0, **{r: 0 for r in ROUTES}})
            bucket["subjects"] += 1
            bucket["priceable"] += int(projection.priceable)
            if projection.resolution_route in bucket:
                bucket[projection.resolution_route] += 1
    return out


def untiered_name_refusals(slate: PlayerSlate) -> int:
    """How many refused names carry no tier, because they carry no athlete."""
    return len(slate.name_refusals)


def assert_tier_resolution_holds(
    census: Mapping[str, Mapping[str, int]],
    *,
    tolerance_points: float = TIER_RESOLUTION_TOLERANCE_POINTS,
) -> None:
    """Stop the run when the priceable rate moves more than 2pp across tiers.

    Design 13, failure mode 5. A gate, not a price: it refuses to let a run
    continue, and it can never turn a refusal into an opinion. Computed over
    resolved subjects, over the three real tiers only —
    :attr:`Tier.UNPLACED` is reported separately by
    `conferences` convention and folding it in would let a first-D-I-season
    roster move the check.
    """
    rates: dict[str, float] = {}
    for tier, counts in census.items():
        if tier == Tier.UNPLACED.value:
            continue
        subjects = int(counts.get("subjects", 0))
        if subjects:
            rates[tier] = 100.0 * int(counts.get("priceable", 0)) / subjects
    if len(rates) < 2:
        return
    spread = max(rates.values()) - min(rates.values())
    if spread > float(tolerance_points):
        raise PlayerRatesError(
            "the priceable rate moves "
            f"{spread:.2f} percentage points across tiers "
            f"({ {t: round(r, 2) for t, r in sorted(rates.items())} }), which "
            f"is more than the declared {tolerance_points}pp. A resolution "
            "rate that runs with tier is a biased sample rather than a smaller "
            "one -- the team-name version of this defect lost 20.5% of names "
            "with 46.7% of the misses at the low-major end -- and the run "
            "stops rather than reporting a census of the games it could read."
        )
