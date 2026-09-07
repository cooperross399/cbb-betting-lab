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

D is the bucket every wiring fault on this seam has hidden in, because from the
outside a layer that was never asked and a layer that was asked with the wrong
thing produce the identical answer: nothing. So a frame that cannot reach the
estimator is refused **in words, at the boundary, before anything is built**,
and never allowed to arrive as D. Three frames arrive here and each has a
declared list of what the layer below reads off it —
:data:`REQUIRED_PLAYER_COLUMNS` and :data:`PLAYER_COLUMNS_THE_ESTIMATOR_READS`
for the player table, :data:`PRICE_COLUMNS_THE_ESTIMATOR_READS` for the price
frame — and the constants have one too, `player_rates.
CONSTANTS_THE_ESTIMATOR_READS`, asked through `missing_constants`. Each list
lives in one place, is named for what reads it, and is checked in
:func:`slate_model` before `matchups_for` is called. The measured cost of not
doing this, three times. Two are re-measured at the card's own entry point
over the four-game board `tests/test_player_seam.py::_card_board` builds: a
price frame of `event_id` and `game_id` gave 0 subjects on a board quoting 16
athletes and every prop read "the model was never asked", and a frozen file
missing one constant raised `ShapesFileError` out of the subject loop and
deleted the team half of the night with it. The third — a player frame of eight
columns refusing its subjects under R6 while the card said nothing — is
`test_s11_the_card_path_can_actually_build_a_player_distribution`'s
measurement, recorded there rather than restated here.

## What this module does not do, and why that is written here

Nothing here measures anything. `models/player_rates.py` gives an athlete a
projection and `models/player_distributions.py` turns one into count pmfs, so
since 2026-09-06 a priceable projection **does** carry a probability and the
sentence that said otherwise has been re-pointed. What this module adds to that
is one field: :attr:`SlateModel.shapes`, the frozen constants **already
provenance-checked for the season being priced**, carried to the card so the
engine is built from the object the guard ran on rather than from a second
`load_player_shapes` call whose season argument the card would have to derive.
A slate that carries a projection and no constants says so
(:data:`NO_ENGINE_CONSTANTS`) instead of pricing.

Every structural absence is still reported with a sentence naming the missing
file (:data:`NO_RATE_ESTIMATOR`, :data:`NO_DISTRIBUTION_ENGINE`) rather than as
a model with no opinions, because those two look identical from the outside and
one of them is a wiring fault. Both are kept reachable: each module is imported
inside the call that needs it, so a tree that loses one says which absence this
is instead of reporting a night with no evidence.
`tests/test_player_seam.py` holds that distinction as a passing assertion.

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
from cbb_betting_lab.conferences import Tier, TierTable
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

#: What a caller must READ off the player table for the seam to reach a price,
#: as against what it must find there before it hands the frame on. The eight
#: above project minutes and cannot form a per-minute rate, which is R6's whole
#: subject; these seventeen are the columns `player_rates` narrows its day pool
#: to (`player_rates._POOL_COLUMNS`, restated here because `slate` imports the
#: estimator inside the call so :data:`NO_RATE_ESTIMATOR` stays reachable, and
#: held equal to it by `test_player_seam.py::test_s11_the_columns_the_card_
#: reads_are_the_columns_the_estimator_reads`).
#:
#: The distinction is not decorative and it was not free. Until 2026-09-06
#: `reports/card_matchups.load_player_games` read the eight, and every athlete
#: on the card path was therefore refused under R6 — measured on the tracked
#: sample corpus over the four-game board
#: `tests/test_player_seam.py::_card_board` builds, all 10 subjects resolved,
#: all 10 were refused with "no per-minute rate exists to shrink", 0 props were
#: priced and design 4's structural check was never asked. The same board over
#: these seventeen prices all 20 props and runs the check over 10 regulars.
#:
#: This list is NOT the required-to-exist list, and widening that one instead
#: would have been the wrong repair: `slate_model` raises `SlateError` on a
#: frame missing a required column, so requiring the box score here would turn
#: a table built without `steals` into a refusal of the whole card — team half
#: included — where R6 refuses the athlete, names the column and lets the team
#: half price. The absent ones are read as absent, never as zeros.
PLAYER_COLUMNS_THE_ESTIMATOR_READS: tuple[str, ...] = (
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

#: What a caller must supply on the PRICE frame for the estimator to form a
#: subject. `player_rates._SUBJECT_COLUMNS`, restated here for the same reason
#: the seventeen above are — `slate` imports the estimator inside the call so
#: :data:`NO_RATE_ESTIMATOR` stays reachable — and held equal to it by
#: `test_player_seam.py::test_s12_the_price_columns_the_card_supplies_are_the_
#: price_columns_the_estimator_reads`.
#:
#: This list exists because the price frame was the break nobody predicted.
#: Both other frames the seam hands on had a declared list and a boundary
#: check; this one had neither, and `reports/card_matchups` handed the
#: estimator `attach_game_ids`' two columns — `event_id` and `game_id` — for as
#: long as the card path existed. `_subjects_of_the_day` returns an empty
#: subject set for a frame with no `market` or no `player` column, so the day
#: came back with 0 projections, an empty resolution census and 0 name
#: refusals, and every prop on it was declined as *the model was never asked* —
#: census bucket D, which is the sentence for a night on which nobody was
#: quoted. Re-measured on 2026-09-07 by restoring that frame at the card's own
#: entry point over the four-game board `tests/test_player_seam.py::_card_board`
#: builds on the full processed corpus: 32 `player_points` rows on 16 quoted
#: subjects, and all of it reported as bucket D.
#:
#: So this is checked, like the other two, BEFORE anything is built, and a
#: frame the estimator cannot form a subject from is :data:`NO_SUBJECT_COLUMNS`
#: — a wiring absence named in words — and never zero subjects reported as an
#: absence of quotes.
#:
#: It refuses the PLAYER HALF and not the slate, and that is the same trade
#: :data:`REQUIRED_PLAYER_COLUMNS` makes in the other direction: a board with
#: no player market at all is a real and common state, the team half prices on
#: it, and raising `SlateError` here would turn a two-column price frame into a
#: refusal of every spread on the card.
PRICE_COLUMNS_THE_ESTIMATOR_READS: tuple[str, ...] = (
    "event_id",
    "market",
    "player",
    "game_id",
    "home_team",
    "away_team",
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

#: The price frame handed to the seam carries no column the estimator can form
#: a subject from, so the estimator was not asked. Distinct from
#: :data:`NO_PROJECTION_FORMED`, and the distinction is the whole of why this
#: sentence exists: that one says *the estimator was handed rows and formed no
#: projection on them*, which is a fact about the board, and it is what the
#: seam printed on every card run whose price frame carried `event_id` and
#: `game_id` and nothing else. A fact about the wiring reported as a fact about
#: the board is the defect family this module is arranged against, one layer up
#: from where it was first found.
#:
#: The missing column names are appended by the caller: a sentence that says
#: *something was missing* is not a sentence an operator can act on.
NO_SUBJECT_COLUMNS: str = (
    "the price frame handed to the seam carries no column the estimator can "
    "form a subject from, so no athlete was resolved, none was refused and the "
    "estimator was never asked. This is a wiring absence, not a night on which "
    "nobody was quoted, and it is not a pass, an avoid or a no-value call. "
    "`reports/card_matchups.model_prices` builds the frame this seam wants. "
    "Missing"
)

#: The estimator could not be imported. Distinct from
#: :data:`NO_PLAYER_HISTORY`, and the distinction is the point: one is a night
#: with no evidence, the other is a lab with no model, and a census that
#: printed the same sentence for both would hide the second inside the first.
#: The file exists today; this sentence is what a tree that lost it would say,
#: and it is reachable because the import is made inside the call.
NO_RATE_ESTIMATOR: str = (
    "`src/cbb_betting_lab/models/player_rates.py` could not be imported, so "
    "the seam asked no estimator for a projection and no athlete carries one. "
    "This is "
    "the model never being asked, not the model declining, and it is not a "
    "pass, an avoid or a no-value call"
)

#: The engine could not be imported. Re-pointed on 2026-09-06, when
#: `models/player_distributions.py` was written and wired: until then this
#: sentence said the file *is not written*, and a priceable projection's last
#: word was that it carried no probability. It does now.
#:
#: The sentence is kept, and kept **reachable**, for the reason
#: :data:`NO_RATE_ESTIMATOR` is: `reports/gameday_card.py` imports the engine
#: inside the call, so a tree that loses the file says which absence this is
#: instead of reporting a night on which the model happened to have no opinion
#: about any prop. The two look identical from the outside and one of them is a
#: wiring fault.
NO_DISTRIBUTION_ENGINE: str = (
    "the player model projects this athlete and "
    "`src/cbb_betting_lab/models/player_distributions.py` could not be "
    "imported, so no engine was asked for a probability on this line. This is "
    "the model never being asked, not the model declining, and it is not a "
    "pass, an avoid or a no-value call"
)

#: A slate carries a priceable projection and **not** the frozen constants that
#: projection was built from, so nothing can build a distribution from it.
#:
#: This is the state a `SlateModel` assembled by hand is in — `coerce` on a bare
#: mapping of matchups, or a test double — and it is a wiring absence rather
#: than a refusal: `slate_model` loads the constants through the provenance
#: guard for the season it prices and hands them on in :attr:`SlateModel.shapes`,
#: so the engine is never handed a set of constants nobody checked. Reading a
#: file here instead, or defaulting to `DEFAULT_SHAPES_PATH` at the card, would
#: be a second load site with a season argument the card would have to derive —
#: and `_player_half` already records what an unchecked season argument costs.
NO_ENGINE_CONSTANTS: str = (
    "the player model projects this athlete and the slate carries no frozen "
    "constants for the season it prices, so the distribution engine was handed "
    "nothing to build from and no probability exists for this line. This is a "
    "wiring absence, not a refusal, and it is not a pass, an avoid or a "
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
    and this file may not create it.

    **The reason was stated wrongly and is corrected here.** It used to read
    "`reports/price_backtest.py` imports nothing from `models/`, and the seam is
    what would make that circular". That stopped being true on commit 0d4f195,
    which added `from cbb_betting_lab.models import player_census` to
    `price_backtest.py` (and the same import to `reports/forecast_skill.py`);
    `player_census` imports `models/player_rates`, so `reports` already depends
    on `models` at module scope. The dependency runs one way — reports on models
    — and importing back the other way from here would close it into
    `models -> reports -> models`, which is the edge the duplication exists to
    prevent, not one it would create. Today it would not even raise: nothing on
    the return path imports `slate`, so a reader who checks the old sentence,
    finds it false and "fixes" the duplication gets a tree that works and a
    layering rule that no longer has a floor.

    Two copies of "strictly earlier" is the football lab's defect 13, so the
    copy is not left to be trusted: `tests/test_player_seam.py` asserts this
    agrees with `price_backtest.latest_day` on the same frames, and asserts the
    edge is still absent, so the two are provably one definition rather than two
    that happen to agree today.

    A blank and the string `"nan"` — what a missing day looks like after a CSV
    round trip — are not days, and a stamp reading `"nan"` would sort above
    every real date and fail every run.
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


def _price_frame_refusal(prices: "pd.DataFrame | None") -> str:
    """:data:`NO_SUBJECT_COLUMNS` naming what is absent, or `""`.

    The third of the seam's three boundary checks, and the last one written:
    the two frames the caller CUT were both checked before anything was built
    and the frame it JOINED was not, so the layer below assumed a vocabulary
    the layer above had never promised. That is the shape every wiring fault on
    this seam has had — each layer assuming another supplies something and
    nobody checking at the boundary — and this is the boundary.

    An empty frame is not refused. A day with no quotes at all is a real state,
    `_subjects_of_the_day` returns empty for it either way, and the columns of
    a zero-row frame say nothing about what the caller can build; the same rule
    `slate_model` already applies to `REQUIRED_PLAYER_COLUMNS`, which is
    checked only on a frame with rows.
    """
    if prices is None or len(prices) == 0:
        return ""
    missing = [
        column
        for column in PRICE_COLUMNS_THE_ESTIMATOR_READS
        if column not in getattr(prices, "columns", ())
    ]
    if not missing:
        return ""
    return f"{NO_SUBJECT_COLUMNS}: {', '.join(missing)}."


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

    Both halves of that sentence are checked before a slate leaves
    :func:`slate_model` — disjointness by invariant I4 and the union by I6,
    against `player_rates.subjects_quoted` — and the union half was checked
    nowhere until 2026-09-07 while three docstrings asserted it.
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
    #: The frozen constants the projections above were built from, checked by
    #: `load_player_shapes` for **this slate's season** — see
    #: :func:`_shapes_for`, which is the only place they are opened.
    #:
    #: Carried rather than re-loaded downstream. `models/player_distributions.py`
    #: opens no file and takes `shapes` as an argument for the same reason
    #: `player_rates` does; a card that loaded its own would be a second load
    #: site with a season argument it would have to derive, and `_player_half`
    #: records what an unchecked season argument already cost once. `None` means
    #: this slate was assembled without them — every bare mapping through
    #: :meth:`coerce` is — and a prop on one reads
    #: :data:`NO_ENGINE_CONSTANTS` rather than being priced off constants
    #: nobody checked.
    shapes: PlayerShapes | None = None

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
    """`models.player_rates`, or `None` if it cannot be imported.

    Imported inside the call rather than at module scope, deliberately. A
    module-scope import would bind the answer once per process — and would make
    an estimator that fails to import take the whole seam down with it, so a
    card that could still price every spread would print nothing at all. The
    sentence returned instead of a projection is the only thing telling an
    operator which of the two states the lab is in.
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

    ## What the seam requires of the frames it is handed, and where it says so

    Three frames arrive and each one has a DECLARED list of what the layer
    below reads off it, in one place, named for what reads it:
    :data:`REQUIRED_PLAYER_COLUMNS` (what must exist),
    :data:`PLAYER_COLUMNS_THE_ESTIMATOR_READS` (what is read), and
    :data:`PRICE_COLUMNS_THE_ESTIMATOR_READS` (what a subject is formed from).
    All three are checked HERE, before `matchups_for` is called and before
    anything is built, because every wiring fault this seam has had was the
    same shape: each layer assuming another supplied something, and nobody
    checking at the boundary. The card handed over a price frame of `event_id`
    and `game_id` and the day came back with zero subjects; the card's loader
    read eight columns and every athlete came back refused under R6; the
    estimator was called with no tiers and every projection read `unplaced`.
    None of the three raised, and none of them was visible in the output.

    A missing column REFUSES rather than defaults, and which half it refuses
    differs by frame and is argued at each list: the player table's eight
    refuse the whole slate (a table that cannot be cut or stamped is not a
    board), the seventeen refuse the athlete under R6 with the column named,
    and the price frame's six refuse the player half in words
    (:data:`NO_SUBJECT_COLUMNS`) while the team half still prices.

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

    # The third frame, checked on the same rule and in the same place: what the
    # caller JOINED, not what it cut. This is computed here — before
    # `matchups_for`, before `_player_half`, before anything is built — rather
    # than discovered inside the estimator, because the estimator's answer for
    # a frame it cannot read is an empty subject set, which is indistinguishable
    # from a board nobody quoted a player on.
    price_frame_refusal = _price_frame_refusal(prices)

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

    players, resolved, name_refusals, player_through, census, absence, checked = (
        _player_half(
            day=day,
            player_history=player_history,
            prices=prices,
            competition=competition,
            season=int(season),
            shapes=shapes,
            matchups=matchups,
            price_frame_refusal=price_frame_refusal,
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
        shapes=checked,
    )
    _assert_invariants(model, prices=prices, day=day)
    return model


def _tiers_from(matchups: "Mapping[str, ratings.Matchup]") -> TierTable:
    """A team-to-tier lookup taken from the matchups the team half just built.

    **Not a second tier table.** `matchups_for` builds one from seasons
    STRICTLY EARLIER than the priced one — letting the priced season in moves
    34 of 367 teams across a boundary, and uses that season's own conference
    membership to price it — and every `Matchup` carries the two tiers it read
    from that table. Reading them back is therefore the same table, arrived at
    without a second construction that could drift from the rule.

    Without this the estimator was called with no tiers at all and every
    projection carried `unplaced`: measured, 25 of 25 built from the real
    2024-01-20 cut. Per-tier reporting is a hard rule of this lab, so a field
    that never populates is not cosmetic — the commit that writes
    `data/processed/cbb_player_lines.csv` would either write "unplaced" into
    every row or reach for the price store's per-game `tier` column, which is
    the substitution design section 9 names and which files a high-major
    starter under whichever tier his opponent decided.

    A team the matchups do not mention stays `UNPLACED`, which is
    `TierTable.tier_for`'s own answer for a team it does not know.
    """
    team_tier: dict = {}
    for matchup in matchups.values():
        for team_id, tier in (
            (getattr(matchup, "home_team_id", None), getattr(matchup, "home_tier", None)),
            (getattr(matchup, "away_team_id", None), getattr(matchup, "away_tier", None)),
        ):
            if team_id is None or tier is None:
                continue
            try:
                team_tier[team_id] = Tier(tier) if not isinstance(tier, Tier) else tier
            except ValueError:
                continue
    return TierTable(
        team_tier=team_tier,
        conference_tier={},
        team_margin={},
        conference_margin={},
        seasons=(),
    )


def _no_player_half(reason: str):
    """An empty player half carrying one sentence, in :func:`_player_half`'s shape.

    Written because the shape is the thing that broke. `_player_half` returns a
    positional tuple, and when the checked `shapes` object was added to it its
    three early returns were each widened by hand — three copies of one arity,
    none of which any test executed, against a caller that unpacks a fixed
    seven. A six-element tuple on any of those lines is `ValueError: not enough
    values to unpack` raised on exactly the nights those sentences exist for: a
    tree that has lost the estimator, the first slate date of a season, and a
    season the frozen constants refuse. There are five of them now, and they
    are one line.

    One place, so the next field is added once. `shapes` is `None` here and is
    not the argument: an absence that returned the constants it was handed
    would tell a card the engine may be built, on a slate carrying nothing to
    build from.
    """
    return {}, {}, {}, "", {}, reason, None


def _player_half(
    *,
    day: str,
    player_history: "pd.DataFrame",
    prices: "pd.DataFrame",
    competition: Competition,
    season: int,
    shapes: PlayerShapes | None,
    matchups: "Mapping[str, ratings.Matchup]",
    price_frame_refusal: str = "",
):
    """The player half, or the full sentence saying which absence this is.

    Five absences, and they are not the same fact:

    * the price frame carries no column a subject can be formed from
      (:data:`NO_SUBJECT_COLUMNS`) — a caller that handed the seam a frame in
      the wrong vocabulary. Checked on the frames in the seam's hands by
      :func:`_price_frame_refusal` and passed in, so the decision is made
      before anything is built rather than inferred from an empty answer;
    * `models/player_rates.py` could not be imported (:data:`NO_RATE_ESTIMATOR`)
      — a tree that has lost its estimator;
    * the estimator imported and was handed no rows
      (:data:`NO_PLAYER_HISTORY`) — a night with no evidence;
    * the frozen constants refuse this season — the provenance guard firing,
      reported in the guard's own words rather than paraphrased;
    * the frozen constants carry neither a value nor a refusal for something
      every market needs (`player_rates.NO_SUCH_CONSTANT`) — an incomplete
      file, which used to reach the card as a `ShapesFileError` raised out of
      the subject loop and took the TEAM half down with it.

    A single "no player opinions" bucket would hide every one of them inside
    the others, and three of the five are wiring faults — a caller in the wrong
    vocabulary, a tree that has lost a module, a file that is incomplete —
    while one is a real night with no evidence and one is a guard firing
    correctly. They are not summed and they do not share a sentence.

    **The order is the order the questions can be answered in, and it is not
    arbitrary.** The seam asks about the frames in its own hands first, because
    that is the only question it can answer without importing, reading or
    building anything, and because a caller holding a frame in the wrong
    vocabulary gets the same answer whether or not this tree still has an
    estimator. Then the tree, then the night, then the file.

    The :data:`NO_RATE_ESTIMATOR` bullet used to describe the estimator as
    never having been written, which is not what that sentence says and has not
    been true of this tree since the estimator landed. `NO_DISTRIBUTION_ENGINE`
    was re-pointed off exactly that wording on 2026-09-06 and this bullet was
    missed; a docstring describing a check the constant does not make is the
    defect findings 7, 14 and 8 are all instances of. It is named by its
    constant here and not by its position, because its position has since
    moved: the price frame's check was added ahead of it.
    `tests/test_player_seam.py::test_s4_the_latest_day_this_module_reads_is_the_
    harnesss_definition` now holds the bullets against the sentences.

    Returns the five container fields, the absence sentence, and **the shapes
    object the projections were actually built from** — never the argument, and
    never `None` once a projection exists. The card builds the distribution
    engine from that object, so the constants a price is made from are provably
    the ones the guard ran on for this season.
    """
    if price_frame_refusal:
        return _no_player_half(price_frame_refusal)
    estimator = _player_rates_module()
    if estimator is None:
        return _no_player_half(NO_RATE_ESTIMATOR)
    if player_history is None or len(player_history) == 0:
        return _no_player_half(NO_PLAYER_HISTORY)

    if shapes is None:
        try:
            shapes = _shapes_for(int(season))
        except ShapesFileError as exc:
            # The provenance guard's own sentence, not a paraphrase of it. It
            # names the constant and the window, and a paraphrase would lose
            # exactly the part an operator needs.
            return _no_player_half(str(exc))
    else:
        # **A supplied `shapes` is an injection point past the provenance
        # guard, and it was open.** `load_player_shapes` refuses a season the
        # constants were fitted or validated on, but it is the SEASON ARGUMENT
        # it checks, not the day anything is later priced for — so a caller
        # could load for a permitted season and then price a forbidden one with
        # the object. Probed against the real frozen file:
        # `load_player_shapes(priced_season=2023)` is refused because 2023 is
        # the declared validation season, while `priced_season=2025` is
        # accepted and returns byte-identical constants. So
        # `slate_model(day="2023-01-15", shapes=load_player_shapes(
        # priced_season=2025))` priced the validation season with the constants
        # validated on it and the refusal never fired.
        #
        # The object carries the season it was checked for, so the check is one
        # comparison: it must be the season of the day being priced.
        declared = getattr(shapes, "priced_season", None)
        if declared is None or int(declared) != int(season):
            return _no_player_half(
                f"the player shapes handed to the slate were checked for "
                f"season {declared!r} and this slate prices season "
                f"{int(season)}. The provenance guard runs on the season it "
                "is given, so a set of constants checked for one season and "
                "used on another is unchecked — which is how the validation "
                "season would be priced with the constants validated on it."
            )

    # The constants the estimator READS, asked of the object in the seam's
    # hands and asked before the subject loop. `load_player_shapes` checks
    # provenance and never completeness, so a file that lost `role_prior`
    # loads, passes the guard, and raises `ShapesFileError` out of `_rates` on
    # the first athlete — through this function, which has no `try`, and out of
    # `slate_model`, which takes the team half with it.
    missing = estimator.missing_constants(shapes)
    if missing:
        return _no_player_half(f"{estimator.NO_SUCH_CONSTANT}: {', '.join(missing)}.")

    result = estimator.player_projections_for(
        day=day,
        player_history=player_history,
        prices=prices,
        shapes=shapes,
        competition=competition,
        tiers=_tiers_from(matchups),
    )
    return (*_unpack(result, player_history=player_history), shapes)


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
    """The six things that must hold before a slate leaves this function.

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

    # I6. The union. Three docstrings assert that `resolved` and
    # `name_refusals` together are EXACTLY the day's distinct player-market
    # (event, spelling) pairs — this container's own, `player_projections_for`'s
    # ("`models/slate.py` asserts ... that their union is exactly the day's
    # distinct pairs") and `player_rates.subjects_quoted`'s — and until
    # 2026-09-07 only the disjointness half above was checked. Two states it
    # sees, and both are silent: a subject that fell out of the loop into
    # neither bucket, which is an athlete the book quoted and this model never
    # counted in any census; and a pair in the union that nothing quoted, which
    # is a wager manufactured out of a name.
    #
    # The day's pairs are read through the estimator's own `subjects_quoted`,
    # never re-derived here. A copy in this file would have to know that a
    # market refused BY NAME contributes no subject, and the day it stopped
    # knowing that, this invariant would raise on a correct run — which is how
    # a check comes to be deleted.
    estimator = _player_rates_module()
    if estimator is not None and (model.resolved or model.name_refusals):
        quoted_pairs = estimator.subjects_quoted(prices)
        union = set(model.resolved) | set(model.name_refusals)
        unaccounted = sorted(quoted_pairs - union)
        invented = sorted(union - quoted_pairs)
        if unaccounted or invented:
            raise SlateError(
                f"the player half of the slate for {day} resolved or refused "
                f"{len(union):,} (event, spelling) pair(s) against "
                f"{len(quoted_pairs):,} quoted on the board: "
                f"{len(unaccounted)} quoted pair(s) reached neither bucket "
                f"(first {unaccounted[:3]}) and {len(invented)} pair(s) in "
                f"neither census are counted anyway (first {invented[:3]}). A "
                "subject in neither bucket is an athlete the book quoted and "
                "no census counted; a pair in the union nobody quoted is a "
                "wager manufactured out of a name."
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
