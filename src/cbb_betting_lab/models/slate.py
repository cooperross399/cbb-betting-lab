"""One slate day's model, built once, in one place, from frames cut before it.

This module exists because of a shape argument, and the shape argument is the
whole of its content. Two of the three rival designs nested the player
projections **inside** `ratings.Matchup`. `matchups_for` returns *one Matchup
per priced event, or no entry at all* — so nesting makes a true sentence
unrepresentable:

    this prop is priceable on a game whose spread is not.

That is not a corner case. `matchup()` refuses a game on five grounds — an
unknown venue state, a disconnected schedule graph, a quasi-neutral game with
an unknown local side, a rating outside the per-possession support, a
non-positive tempo — and **not one of them says anything about whether a
player's minutes are projectable**. A container that cannot hold the two
answers separately would delete every prop on every game the team model
declined, silently, and the deletion would be concentrated exactly where the
design measured it: ~1.8% of quotes, before 20 November, with a 2.3x tier skew
and zero low-major. A census computed over the survivors would then be a census
of the games the team model liked.

The other rival keyed players by name inside the container, which puts a
name matcher in the report layer — against `ratings.py`'s own rule, *"Joined on
`game_id`, never on a name"*, and against the retention probe's measurement
that 20.5% of provider team names went unresolved, 46.7% of them at the
low-major end. So:

* `matchups` and `players` are **independently keyed by `event_id`**, and
  neither's absence implies the other's;
* the player price reads **nothing** from `Matchup` (design 2), so all four
  states below are representable and are separate census buckets;
* the only text rule anything applies is `season.clean_text`, and it is applied
  to **look a key up**, never to match. The matching happens once, inside
  `models/player_rates.py`, where the prior roster lives.

The four states, which are counted separately and never summed:

A. no matchup, or a matchup that refuses, **and** a priceable projection ->
   the prop prices normally. This is the state nesting made unrepresentable.
B. a projection with `priceable=False` -> REFUSED, its own sentence printed.
C. `(event, the book's spelling)` in `name_refusals` -> REFUSED for the name.
   No athlete id exists and none is invented.
D. the event is not in `players` at all -> NO OPINION. The model was never
   asked. This is a different bucket from B and C and is always counted apart
   from them: `ratings.matchups_for`'s docstring already makes the same
   distinction for the team half, in the same words.

## What this module does not do, and why that is written here

Nothing here measures anything. `models/player_rates.py` and
`models/player_distributions.py` are not written, so **no athlete carries a
projection today and no line carries a probability**. The seam reports that as
a structural absence with a sentence naming the missing file
(:data:`NO_RATE_ESTIMATOR`, :data:`NO_DISTRIBUTION_ENGINE`) rather than as a
model with no opinions, because those two look identical from the outside and
one of them is a wiring fault. `tests/test_player_seam.py` holds that
distinction as a passing assertion that goes red the day either file lands.

## The cut, and the one place two names meet

At price time for a game on day D the model may read **only** rows dated
strictly before D. The player table in memory is the uncut settlement table:
1,493,589 rows spanning seasons 2019-2026, of which 404,489 are in seasons
later than the priced season 2024 and 198,586 are in it. A frame loaded once,
uncut, outside the per-day loop is the football lab's defect 13 and is the
defect this whole build is arranged against.

The cut itself is made **once**, by `reports/price_backtest.history_before`, at
the caller. This module does not re-implement it and does not open a file. It
asserts, before it returns anything, that neither frame it was handed reaches
the day being priced (:class:`SlateLeak`) — the construction-site half of a
check the harness also makes on the stamp, because a guard whose floor comes
only from the caller cannot see the caller getting it wrong.

The uncut settlement table keeps the name `player_games` everywhere it appears.
The cut frame is `player_history`. The two names meet on exactly one line, and
it is in this file.
"""

from __future__ import annotations

import inspect
from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from pathlib import Path

import pandas as pd

from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.models import ratings
from cbb_betting_lab.models.player_shapes import (
    DEFAULT_SHAPES_PATH,
    PlayerShapes,
    ShapesFileError,
    load_player_shapes,
)
from cbb_betting_lab.season import clean_text, season_for_slate_date

# --------------------------------------------------------------------------
# Constants
# --------------------------------------------------------------------------

#: The player frame's own day column. It is deliberately equal to
#: `walk_forward`'s default `game_day_column`, so **no call site passes
#: `frame_day_columns`**: a second place naming a day column is a second place
#: it can be named wrongly, and `walk_forward` would then cut the frame to
#: nothing every night rather than raise — which looks exactly like a player
#: model with no opinions.
SLATE_DAY_COLUMN: str = "slate_date"

#: Read off the real header of `data/processed/cbb_player_games.csv`, which
#: carries 32 columns; these eight are the ones the seam requires to exist
#: before it hands the frame on. They are also the columns a caller builds an
#: empty frame from when the board carries no player market, so that an absent
#: market and a broken table do not arrive looking the same.
#:
#: Nothing here is defaulted when it is missing. `require_columns`' rule, and
#: the reason for it, is that a missing column read as a zero is how the
#: football lab's props backtest reported zero bets and had that read as a
#: finding about the model.
REQUIRED_PLAYER_COLUMNS: tuple[str, ...] = (
    "slate_date",
    "season",
    "game_id",
    "athlete_id",
    "athlete_display_name",
    "team_id",
    "did_not_play",
    "minutes",
)

#: A day in no season this lab carries. `matchups_for` returns `{}` for one
#: rather than raising, and this matches it: an empty slate, with the reason.
NO_SEASON: str = (
    "this slate day falls in no season this lab carries, so neither a rating "
    "nor a projection was asked for"
)

#: The player frame was handed over and holds no row strictly before the day.
NO_PLAYER_HISTORY: str = (
    "no player history was handed to the seam for this day, so no athlete "
    "carries a projection. This is the model never being asked, not the model "
    "declining"
)

#: The estimator itself is not written. Distinct from
#: :data:`NO_PLAYER_HISTORY`, and the distinction is the point: one is a night
#: with no evidence, the other is a lab with no model, and a census that
#: printed the same sentence for both would hide the second inside the first.
NO_RATE_ESTIMATOR: str = (
    "`src/cbb_betting_lab/models/player_rates.py` is not written, so the seam "
    "asked no estimator for a projection and no athlete carries one. This is "
    "the model never being asked, not the model declining, and it is not a "
    "pass, an avoid or a no-value call"
)

#: A projection exists and is priceable, and there is still no probability,
#: because the engine that would turn a projection into one is not written.
#: This is the sentence a *priceable* prop reads today.
NO_DISTRIBUTION_ENGINE: str = (
    "the player model projects this athlete but "
    "`src/cbb_betting_lab/models/player_distributions.py` is not written, so "
    "no probability exists for this line yet. It is not a pass, an avoid or a "
    "no-value call"
)

#: The estimator ran, on rows it was handed, and formed no projection. Distinct
#: again from the three above: this one is a statement about the day's board and
#: the day's roster, not about the tree.
NO_PROJECTION_FORMED: str = (
    "the estimator was handed player history for this day and formed no "
    "projection on it, so either no player market was quoted or every quoted "
    "subject was refused for the name. It is not a pass, an avoid or a "
    "no-value call"
)

#: What a bare mapping of matchups says about its player half: nothing. Every
#: existing test double, and the shipped `ratings.matchups_for`, returns one.
NO_PLAYER_SLATE: str = (
    "the model returned matchups only, so it was never asked about any "
    "athlete and no projection exists for this day. An absent projection is "
    "not a probability of zero"
)


class SlateError(RuntimeError):
    """The seam was handed something it cannot build a slate from."""


class SlateLeak(SlateError):
    """A frame handed to the seam reaches the day being priced, or past it."""


# --------------------------------------------------------------------------
# The one permitted memo, and the reason it is the only one
# --------------------------------------------------------------------------

#: `(str(path), priced_season) -> PlayerShapes`. Keyed on the priced season
#: because `load_player_shapes` has no non-refusing mode: the object's very
#: existence is the evidence that the provenance guard ran **for that season**,
#: and a memo keyed on the path alone would hand a 2025 pricer the object that
#: was checked against 2024.
#:
#: **This is the only module-level memo in this file, and it holds no game
#: row.** A memo keyed on `(event_id, athlete_id)` would make the poisoned-
#: future leak test pass by returning the pre-corruption object — a detector
#: that cannot fire. The per-`(event, athlete)` distribution cache the design
#: asks for belongs on a `SlateModel` instance, one per `slate_model` call, and
#: `tests/test_player_seam.py` walks this module's globals to assert as much.
_SHAPES_CACHE: dict[tuple[str, int], PlayerShapes] = {}


def clear_caches() -> None:
    """Drop the one memo this module keeps. Tests that change the file call it."""
    _SHAPES_CACHE.clear()


# --------------------------------------------------------------------------
# Reading a day off a frame — a max, not a second cut
# --------------------------------------------------------------------------


def _latest_day(frame: "pd.DataFrame | None", *, day_column: str = SLATE_DAY_COLUMN) -> str:
    """The latest day present in one frame, or `""` for a frame with no rows.

    **This is not a second copy of the cut.** The cut is
    `price_backtest.history_before`, made once, at the caller, and this module
    never makes it; this reads a maximum off a frame somebody else already cut,
    which is what the stamp is. It is written here rather than imported because
    `models/` importing `reports/` is an edge that does not exist in this tree
    and this file may not create it — `reports/price_backtest.py` imports
    nothing from `models/`, and the seam is what would make that circular.

    A blank and the string `"nan"` — what a missing day looks like after a CSV
    round trip — are not days, and a stamp reading `"nan"` would sort above
    every real date and fail every run. `tests/test_player_seam.py` asserts
    this agrees with `price_backtest.latest_day` on the same frames, so the two
    are provably one definition rather than two that happen to agree today.
    """
    if frame is None or len(frame) == 0:
        return ""
    if day_column not in getattr(frame, "columns", ()):
        return ""
    days = frame[day_column].dropna().astype(str)
    days = days[(days != "") & (days.str.strip().str.lower() != "nan")]
    return "" if days.empty else str(days.max())


def _rows_reaching(frame: "pd.DataFrame | None", day: str) -> int:
    """How many rows of `frame` are dated on or after `day`. Zero for no column."""
    if frame is None or len(frame) == 0:
        return 0
    if SLATE_DAY_COLUMN not in getattr(frame, "columns", ()):
        return 0
    return int((frame[SLATE_DAY_COLUMN].astype(str) >= str(day)).sum())


def _refuse_a_frame_that_reaches_the_day(
    frame: "pd.DataFrame | None", *, day: str, what: str
) -> str:
    """The frame's latest day, or :class:`SlateLeak` naming what reaches `day`.

    The harness stamps what a pricer was *allowed* to see and checks that stamp
    against the day. That check's floor comes from the caller, and a guard whose
    floor comes only from the thing it is guarding cannot see that thing get the
    floor wrong. So the construction site asks the same question of the frames
    in its hands, and it asks it before it builds anything at all.
    """
    reaching = _rows_reaching(frame, day)
    if reaching:
        latest = _latest_day(frame)
        raise SlateLeak(
            f"{what} handed to the slate for {day} holds {reaching:,} row(s) "
            f"dated on or after {day}, running through {latest}. A model that "
            "has seen the game it is pricing does not have an edge, it has the "
            "answer. Cut the frame with `price_backtest.history_before` — one "
            "definition, at the caller — rather than here: two copies of "
            "'strictly earlier' is the football lab's defect 13, which was the "
            "same comparison written with `<=` in one of its two places."
        )
    return _latest_day(frame)


# --------------------------------------------------------------------------
# The container
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SlateModel:
    """One slate day's model: the team half, the player half, and both censuses.

    `matchups` is **exactly what `matchups_for` returned** — the same value
    objects, not re-keyed and not filtered — so a caller that used to read the
    bare dict reads the same objects here. `players` is keyed
    `event_id -> athlete_id -> PlayerProjection`, with the athlete id as it
    appears in the player table: never `str()`-ed, never float-to-int coerced.
    `providers/player_names.py` records that same bug family wearing an id.

    `resolved` and `name_refusals` share a key — `(event_id, the book's
    spelling **as filed**)` — and are **disjoint**; their union is exactly the
    day's distinct player-market (event, player) pairs. That is what makes
    `projection_for` a dict lookup rather than a match, and it is what stops
    the resolution census double-counting the ~7.2 ladder rungs a points
    subject carries.
    """

    day: str = ""
    matchups: Mapping[str, object] = field(default_factory=dict)
    players: Mapping[str, Mapping[object, object]] = field(default_factory=dict)
    resolved: Mapping[tuple[str, str], object] = field(default_factory=dict)
    name_refusals: Mapping[tuple[str, str], str] = field(default_factory=dict)
    team_priced_through: str = ""
    player_priced_through: str = ""
    #: Non-empty only when `players` is empty and the reason is structural. A
    #: bucket with no sentence is a silence, and a silence is what a wiring
    #: fault looks like from the outside.
    player_absence_reason: str = ""
    #: Resolution route -> subjects, plus `"quotes:<route>"` -> quotes. Printed
    #: every run per design 13's failure mode 5, which says to stop if the
    #: per-tier resolution rate moves more than 2pp across tiers.
    resolution_census: Mapping[str, int] = field(default_factory=dict)

    # -- the team half ----------------------------------------------------

    def matchup_for(self, event_id: object) -> object | None:
        """The `Matchup` for one event, or `None`. A missing one is not a zero."""
        found = self.matchups.get(event_id)
        if found is None:
            found = self.matchups.get(clean_text(event_id))
        return found

    # -- the player half --------------------------------------------------

    def was_asked_about_players(self, event_id: object) -> bool:
        """Whether the model was asked about this event's athletes at all.

        False is `no opinion` — census bucket D — and is a different fact from
        a projection that refuses. The two are never summed.
        """
        return clean_text(event_id) in self.players

    def projection_for(self, event_id: object, name: object) -> object | None:
        """The projection for the book's spelling of a player, or `None`.

        A pure lookup. `clean_text` is applied to find the key, never to match:
        the matching happened once, inside `player_rates`, against a **prior**
        roster. A second matcher here would be the join-vocabulary bug family's
        sixth member, and every one of the first five failed silently.
        """
        athlete_id = self.resolved.get((clean_text(event_id), clean_text(name)))
        if athlete_id is None:
            return None
        return self.players.get(clean_text(event_id), {}).get(athlete_id)

    def name_refusal(self, event_id: object, name: object) -> str:
        """The R1/R1a sentence for a spelling that resolved to no one athlete."""
        return self.name_refusals.get((clean_text(event_id), clean_text(name)), "")

    # -- what it says for itself ------------------------------------------

    def summary_line(self) -> str:
        priceable = sum(
            1 for m in self.matchups.values() if bool(getattr(m, "priceable", False))
        )
        athletes = sum(len(by_athlete) for by_athlete in self.players.values())
        refused = sum(
            1
            for by_athlete in self.players.values()
            for projection in by_athlete.values()
            if not bool(getattr(projection, "priceable", False))
        )
        line = (
            f"{self.day}: {len(self.matchups):,} matchup(s), {priceable:,} "
            f"priceable, through {self.team_priced_through or 'nothing'}. "
            f"{len(self.players):,} event(s) carry a player projection: "
            f"{athletes:,} athlete(s), {refused:,} refused, "
            f"{len(self.name_refusals):,} name(s) refused, through "
            f"{self.player_priced_through or 'nothing'}."
        )
        if self.player_absence_reason:
            line += f" No athlete carries a projection: {self.player_absence_reason}."
        return line

    # -- the door every existing caller comes through ---------------------

    @classmethod
    def coerce(
        cls,
        result: object,
        *,
        day: str,
        team_priced_through: str = "",
        player_priced_through: str = "",
        player_absence_reason: str = "",
    ) -> "SlateModel":
        """Whatever the resolved model returned, as a `SlateModel`.

        Every model that ships today — `ratings.matchups_for` — and every test
        double in `tests/` returns a bare mapping of matchups, and each one is
        wrapped here rather than rewritten. `None` is an empty slate, which is
        what a caller that never reached the model has.

        A `SlateModel` whose `day` differs from the caller's is refused rather
        than reused: a slate carried across days is the football lab's defect
        13 wearing a container, and the whole of this module's value is that a
        day's model was built from that day's cut.
        """
        day = str(day)
        if isinstance(result, cls):
            if str(result.day) and str(result.day) != day:
                raise SlateError(
                    f"a slate built for {result.day} was handed to the pricer "
                    f"for {day}. A slate reused across days was priced from "
                    "another day's cut, which is the whole of what this "
                    "container exists to make visible."
                )
            return result if str(result.day) else replace(result, day=day)
        if result is None:
            return cls(
                day=day,
                team_priced_through=str(team_priced_through),
                player_priced_through=str(player_priced_through),
                player_absence_reason=str(player_absence_reason) or NO_PLAYER_SLATE,
            )
        if isinstance(result, Mapping):
            return cls(
                day=day,
                matchups=dict(result),
                team_priced_through=str(team_priced_through),
                player_priced_through=str(player_priced_through),
                player_absence_reason=str(player_absence_reason) or NO_PLAYER_SLATE,
            )
        raise SlateError(
            f"the model returned {type(result).__name__}, which is neither a "
            "SlateModel, a mapping of matchups nor None. Nothing was priced: a "
            "model whose return value is not read is a model whose opinions "
            "are silently dropped, and a card with no opinion on anything is "
            "indistinguishable from a card whose model was never asked."
        )


# --------------------------------------------------------------------------
# The construction site
# --------------------------------------------------------------------------


def _player_rates_module():
    """`models.player_rates`, or `None` while it is not written.

    Imported inside the call rather than at module scope, deliberately. A
    module-scope import would bind the answer once per process, so a tree that
    grew the estimator would keep reporting it absent until something restarted
    — and the sentence this returns instead of a projection is the only thing
    telling an operator which of the two states the lab is in.
    """
    try:
        from cbb_betting_lab.models import player_rates  # noqa: PLC0415
    except ImportError:
        return None
    return player_rates


def _shapes_for(season: int, *, path: Path | str = DEFAULT_SHAPES_PATH) -> PlayerShapes:
    """The frozen constants, provenance-checked for the season being priced.

    Never `json.load`. `load_player_shapes` has no non-refusing mode: it
    refuses constants whose fit window touches the priced season **or the
    declared validation season**, so the existence of the returned object is
    the evidence that the check ran for this season.
    """
    key = (str(path), int(season))
    hit = _SHAPES_CACHE.get(key)
    if hit is None:
        hit = load_player_shapes(path, priced_season=int(season))
        _SHAPES_CACHE[key] = hit
    return hit


def slate_model(
    *,
    day: str,
    history: "pd.DataFrame",
    player_history: "pd.DataFrame",
    prices: "pd.DataFrame",
    competition: Competition = CBB,
    raw_dir: Path | str | None = None,
    shapes: PlayerShapes | None = None,
) -> SlateModel:
    """The single construction site for one slate day's model.

    Calls `ratings.matchups_for` **unchanged** for the team half and
    `player_rates.player_projections_for` beside it for the player half. The
    two do not read each other: the player price takes no pace, no opponent, no
    venue and no overtime term from `Matchup`, for three reasons the design
    ranks — the team joint's four constants are fitted on a window containing
    the priced season; inheriting `matchup()`'s refusals would delete ~1.8% of
    prop quotes with a 2.3x tier skew and zero low-major, for adjustments worth
    0.13-0.29% of RMSE against an oracle ceiling of 0.7-0.9%; and decoupling
    them is what makes the player census an honest answer rather than a
    statement about the games the team model happened to like.

    **Every frame parameter is keyword-only and carries no default.** That is
    not style. `price_backtest._refuse_undeclared_frames` refuses a pricer
    whose frame parameter carries a default, on the ground that
    `player_games=None` is not a pricer that works without player games — it is
    a pricer left to find them some other way, and every other way is uncut and
    unstamped. This sits behind that seam and must not undo it.

    Raises :class:`SlateLeak` when either frame reaches the day being priced,
    and :class:`SlateError` when the player frame has rows and lacks a column
    the seam requires. Returns an **empty** slate carrying :data:`NO_SEASON`
    for a day in no season this lab carries, matching `matchups_for`'s own
    `return {}` rather than raising.

    ## The one argument this deliberately does **not** pass

    `matchups_for` declares `player_games`, live dead wiring into
    `prepare_prior`, and design 2.4 directs the cut frame into it. **It is
    withheld here, and the withholding is asserted by a test.** Filling it
    flips `CarryoverFit.uses_roster` from False to True on the efficiency term
    and makes `_prior_means` apply `share_as_of(day)` — which changes every
    team price this lab has ever published, none of which has been re-measured
    against the roster terms on. Turning it on inside a commit that measures
    nothing would replace a set of published numbers with a different set and
    leave no record of which run produced which. It is a declared deviation,
    reported rather than taken silently, and it is one keyword away the day
    somebody re-measures.
    """
    day = str(day)

    # I6. Same object twice is not two frames, and the mistake is one keyword
    # wide: the team history and the player history are cut by the same
    # function from different tables, and a caller that passed one twice would
    # get a slate whose player half was projected off team-game rows.
    if player_history is history:
        raise SlateError(
            "the team history and the player history are the same object. They "
            "are two different tables cut by one function; handing the same "
            "frame in twice projects athletes off team-game rows and reports "
            "the result in intervals."
        )

    # L2/L3 at the construction site, before anything is built. The harness
    # checks the stamp; this checks the frames, and the two failures are
    # different: a stamp can only describe what the caller believes it cut.
    team_through = _refuse_a_frame_that_reaches_the_day(
        history, day=day, what="the team history"
    )
    _refuse_a_frame_that_reaches_the_day(
        player_history, day=day, what="the player history"
    )

    if player_history is not None and len(player_history) > 0:
        missing = [
            column
            for column in REQUIRED_PLAYER_COLUMNS
            if column not in getattr(player_history, "columns", ())
        ]
        if missing:
            raise SlateError(
                f"the player history is missing {missing}. Nothing is "
                "defaulted and nothing is read with `getattr(..., None)`: a "
                "missing column read as a zero is how a wiring fault becomes a "
                "finding, and this seam would happily project from one and "
                "hand the result to a card."
            )

    season = season_for_slate_date(day)
    if not season:
        # `matchups_for` returns `{}` here rather than raising, and so does
        # this: a day in no season is a day nobody quoted, not a failure.
        return SlateModel(day=day, team_priced_through=team_through,
                          player_absence_reason=NO_SEASON)

    matchups = ratings.matchups_for(
        day=day,
        history=history,
        prices=prices,
        competition=competition,
        raw_dir=raw_dir,
        # `player_games` is withheld. See the docstring: filling it changes
        # every published team number and this commit measures nothing.
    )

    players, resolved, name_refusals, player_through, census, absence = (
        _player_half(
            day=day,
            player_history=player_history,
            prices=prices,
            competition=competition,
            season=int(season),
            shapes=shapes,
        )
    )

    model = SlateModel(
        day=day,
        matchups=matchups,
        players=players,
        resolved=resolved,
        name_refusals=name_refusals,
        team_priced_through=team_through,
        player_priced_through=player_through,
        player_absence_reason=absence,
        resolution_census=census,
    )
    _assert_invariants(model, prices=prices, day=day)
    return model


def _player_half(
    *,
    day: str,
    player_history: "pd.DataFrame",
    prices: "pd.DataFrame",
    competition: Competition,
    season: int,
    shapes: PlayerShapes | None,
):
    """The player half, or the full sentence saying which absence this is.

    Three absences, and they are not the same fact:

    * the estimator is not written (:data:`NO_RATE_ESTIMATOR`) — a lab with no
      model;
    * the estimator is written and was handed no rows
      (:data:`NO_PLAYER_HISTORY`) — a night with no evidence;
    * the frozen constants refuse this season — the provenance guard firing,
      reported in the guard's own words rather than paraphrased.

    A single "no player opinions" bucket would hide the first inside the
    second, and the first is a wiring fault.
    """
    estimator = _player_rates_module()
    if estimator is None:
        return {}, {}, {}, "", {}, NO_RATE_ESTIMATOR
    if player_history is None or len(player_history) == 0:
        return {}, {}, {}, "", {}, NO_PLAYER_HISTORY

    if shapes is None:
        try:
            shapes = _shapes_for(int(season))
        except ShapesFileError as exc:
            # The provenance guard's own sentence, not a paraphrase of it. It
            # names the constant and the window, and a paraphrase would lose
            # exactly the part an operator needs.
            return {}, {}, {}, "", {}, str(exc)

    result = estimator.player_projections_for(
        day=day,
        player_history=player_history,
        prices=prices,
        shapes=shapes,
        competition=competition,
    )
    return _unpack(result, player_history=player_history)


def _unpack(result: object, *, player_history: "pd.DataFrame"):
    """`player_projections_for`'s return, in this container's five fields.

    The design gives the estimator a return of
    `tuple[dict[event][athlete], str]`. That shape cannot carry an R1/R1a
    refusal: a name that does not resolve **has no athlete id**, so a container
    keyed only by athlete id makes design 7's own rule — *every refusal is an
    entry with a full-sentence reason* — unrepresentable for the two refusals
    design 11 says must be counted and printed every run. Both shapes are
    accepted here, and the record shape is preferred, so the estimator can
    return the richer one without this file having to guess which it got.
    """
    if isinstance(result, tuple):
        projections, priced_through = (list(result) + ["", ""])[:2]
        projections = dict(projections or {})
        return (
            projections,
            {},
            {},
            str(priced_through or _latest_day(player_history)),
            {},
            "" if projections else NO_PROJECTION_FORMED,
        )
    projections = dict(getattr(result, "projections", {}) or {})
    return (
        projections,
        dict(getattr(result, "resolved", {}) or {}),
        dict(getattr(result, "name_refusals", {}) or {}),
        str(getattr(result, "priced_through", "") or _latest_day(player_history)),
        dict(getattr(result, "resolution_census", {}) or {}),
        "" if projections else NO_PROJECTION_FORMED,
    )


def _assert_invariants(model: SlateModel, *, prices: "pd.DataFrame", day: str) -> None:
    """The five things that must hold before a slate leaves this function.

    Each one is a state that would otherwise be discovered downstream as a
    plausible number rather than as an error.
    """
    # I1. Both stamps strictly earlier than the day. The frames were already
    # checked; this catches an estimator that reported a stamp of its own.
    for what, stamp in (
        ("the team", model.team_priced_through),
        ("the player", model.player_priced_through),
    ):
        if stamp and str(stamp) >= day:
            raise SlateLeak(
                f"{what} half of the slate for {day} reports it read through "
                f"{stamp}, which is not strictly earlier than the day it "
                "prices. A stamp at or after the day being priced is the "
                "football lab's compound markets looking good."
            )

    # I2. An empty stamp with a populated player half is a contradiction, and
    # it is the one value a leaking pricer would want: `assert_walk_forward`
    # exempts `""`, so a pricer that read the settlement table and reported
    # nothing would be certified.
    if model.players and not model.player_priced_through:
        raise SlateError(
            "the slate carries player projections and reports no "
            "`player_priced_through`. An empty stamp is exempted by "
            "`assert_walk_forward`, so a projection built from a frame nobody "
            "cut would pass the guard by declining to say what it read."
        )

    # I3. Never a key nobody quoted.
    if model.players:
        quoted = {clean_text(e) for e in prices.get("event_id", [])}
        unquoted = sorted(set(model.players) - quoted)
        if unquoted:
            raise SlateError(
                f"the slate projects athletes on {len(unquoted)} event(s) "
                f"nobody quoted on {day}, first {unquoted[:3]}. A projection on "
                "a game with no price is not a bet the card could ever have "
                "taken, and counting one manufactures a wager."
            )

    # I4. The two player-name buckets are disjoint. Their union being exactly
    # the day's distinct pairs is the estimator's own assertion, made where the
    # price frame is iterated rather than re-derived here from a second read.
    both = set(model.resolved) & set(model.name_refusals)
    if both:
        raise SlateError(
            f"{len(both)} (event, spelling) pair(s) are both resolved to an "
            "athlete and refused for the name. A refusal and an opinion are "
            "different census buckets and a pair in both would be counted "
            "twice, in opposite directions."
        )

    # I5. Every resolved athlete is one this slate actually carries.
    for (event_id, spelling), athlete_id in model.resolved.items():
        if athlete_id not in model.players.get(event_id, {}):
            raise SlateError(
                f"the spelling {spelling!r} on event {event_id} resolves to "
                f"athlete {athlete_id!r}, which carries no projection. A "
                "resolution that reaches nothing is a name matched to an "
                "athlete the model never projected."
            )


def fits_its_callers(caller_arguments) -> list[str]:
    """Which of :func:`slate_model`'s required parameters `caller_arguments` misses.

    The same rule `price_backtest.unsupplied_arguments` applies, restated here
    only so this module can be asked the question without `models/` importing
    `reports/`. `tests/test_player_seam.py` asserts the two agree on this
    function's own signature, so it is provably one rule and not two.
    """
    offered = set(caller_arguments)
    missing: list[str] = []
    for name, parameter in inspect.signature(slate_model).parameters.items():
        if parameter.default is not inspect.Parameter.empty:
            continue
        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        if parameter.kind is inspect.Parameter.POSITIONAL_ONLY or name not in offered:
            missing.append(name)
    return missing
