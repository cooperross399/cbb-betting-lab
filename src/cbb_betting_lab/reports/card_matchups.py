"""The model's opinion for the card, built exactly as the backtest builds it.

`scripts/run_gameday_card.py` called `gameday_card.run_card` for the whole of
the build without ever passing `matchups`, and `run_card` defaults that
argument to `None`. So the production card would have priced **no opinion on
anything** — every wager `no opinion`, nothing selectable, nothing for the
forward-evidence organ to accumulate — through an entire season, while every
line of stdout read as a healthy run. `opinions_for` even printed the reason:
*"no rating exists for this game — `models/ratings.py` is not written"*, a
sentence that had been false since the module was written. This module is the
missing wire.

## The same seam, the same cut, the same join

Three things here are borrowed rather than re-implemented, because a second
copy of each is a known defect family in the sibling labs:

* **The model** is `price_backtest.DEFAULT_MODEL`, resolved by
  `price_backtest.resolve_model` and called through `price_backtest.call_model`
  — the callable and the calling convention the measured numbers came from. A
  card that priced through a different path would be shipping a policy nobody
  measured.
* **The history** is `price_backtest.history_before(team_games, day)`: games
  dated **strictly earlier** than the slate day, which is the walk-forward
  rule every backtest day was priced under. The card has no future to leak,
  today; a rehearsal of a past day does, and the same cut protects both. The
  **player** history is cut by that same function from `cbb_player_games.csv`
  and handed in beside it, which is what the next paragraph is about.
* **The join** is on hoopR's `game_id`, resolved from the provider's two
  school names through `providers.team_names` and
  `forward_evidence._FixtureIndex.resolve` — the settlement resolver, so a
  game is found for pricing by the same rule it will later be found for
  grading. Built from the **schedule** rather than the results table, because
  tonight's game has no result row yet.

## What is refused, and why it is a refusal

The processed table the model fits on (`cbb_team_games.csv`) or the cached
schedule for the season being absent raises :class:`InputsAbsent`. A model that
*requires* an argument this caller does not build raises
`price_backtest.ModelArgumentUnsupplied` — the seam refusing rather than
under-supplying, which is what it used to do in silence. The entry point turns
either into `::error::` and `decision=refused`. It is not degraded to
"price nothing and carry on", because that is precisely the state this module
exists to end: a card with no opinion on anything is indistinguishable, from
the outside, from a card whose model was never asked. **The card must say it
priced no opinion; it may never silently price none.**

## The player table is now an input, and it was not before

Until this commit `player_games` settled and did not price, and the sentence
saying so was in this file. The player seam changes that: the card cuts
`cbb_player_games.csv` with the same `history_before` and hands the cut frame
to the model under the name `player_history`, so that a model which declares it
— `models/slate.py:slate_model` does — receives a frame the card can name, has
cut, and stamps. A model that does not declare it, which is every model shipped
today, never sees it and `call_model` filters it out; the card still reports
how many rows it was prepared to show and what the model said it read, because
those two numbers differing is the only visible symptom of a model reading a
table nobody handed it.

The table is **required**, on the same ground the team table is: grading and
pricing without it do not fail, they succeed quietly and wrongly. The columns
read are `slate.PLAYER_COLUMNS_THE_ESTIMATOR_READS` — the seventeen
`player_rates` narrows its day pool to — and until 2026-09-06 they were the
eight `slate.REQUIRED_PLAYER_COLUMNS` declares, which carry no box score.
Measured on the tracked sample corpus over the four-game board
`tests/test_player_seam.py::_card_board` builds — 20 `player_points` quotes on
10 athletes — driven through this module with `models/slate.py:slate_model`: on
the eight-column cut all 10 subjects resolve and all 10 are refused under R6
("no per-minute rate exists to shrink"), 0 props priced and design 4's
structural check never asked; on the seventeen the same board prices all 20
props and the check runs over 10 regulars at a ratio of 0.9575.

Re-measured on the 207,954,921-byte, 1,493,589-row table in `data/processed/`,
best of three each: **1.09 seconds for the eight, 1.33 for the seventeen, 1.77
for all thirty-two** — so the saving over the whole table is real, it is under
half a second, and it was never the reason. The other fifteen are still not
read, and a later change that needs one adds it to the seam's list rather than
to a `usecols` here.

## The model is handed the board's subjects, not only its games

`attach_game_ids` resolves one `(event_id, game_id)` per event, and until this
commit that two-column frame **was** the price frame the model was given. The
team half reads exactly those two columns, so nothing looked wrong. The player
half reads `market` and `player` to find the subjects of the day and
`home_team`/`away_team` to find the roster they are resolved against, and a
frame carrying none of them yields no subject at all: measured on the board
above, 0 projections, an empty resolution census, 0 name refusals, and all 20
props declined as *"the model was never asked about this event's athletes"* —
which was true, and this frame was the reason.

:func:`model_prices` is the fix: one row per board quote that joined to a game,
in the **price store's** vocabulary rather than the board's, because that is
the vocabulary `player_rates._subjects_of_the_day` reads and
`scripts/run_price_backtest.py` already hands it. The one trap is that
`home_team` names two different things in the two vocabularies — a hoopR team
id in the store, a provider school spelling on the board — so the translation
happens exactly once, here, off the fixture the game id was resolved from, and
the provider's spellings travel beside the ids as `home_name`/`away_name`
rather than being dropped or silently renamed.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from cbb_betting_lab.competitions import Competition
from cbb_betting_lab.config import PROCESSED_DIR, RAW_DIR
from cbb_betting_lab.data import hoopr
from cbb_betting_lab.forward_evidence import _FixtureIndex, _pair
from cbb_betting_lab.models import slate
from cbb_betting_lab.providers import team_names
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.season import clean_text, season_for_slate_date

#: The processed table the team model fits on.
REQUIRED_TABLE = "team_games"

#: The player table the player seam projects from. It stopped being a
#: settlement-only table the moment `models/slate.py` landed: the card cuts it
#: with `history_before` and hands the cut frame to the model. `game_segments`
#: still settles and does not price, so its absence remains settlement's
#: business and not the card's.
PLAYER_TABLE = "player_games"

#: Both, in the order they are read — the team table first, so a checkout with
#: neither says the same thing it said before this commit.
REQUIRED_TABLES: tuple[str, ...] = (REQUIRED_TABLE, PLAYER_TABLE)

#: The frame handed to the model, in the vocabulary of the price store the
#: measurement was made over rather than of the provider's board.
#: `home_team`/`away_team` are hoopR team **ids**, as they are in
#: `data/processed/cbb_historical_prices__card.csv`; the provider's school
#: spellings ride beside them under the store's own `home_name`/`away_name`.
#: See :func:`model_prices`.
#:
#: This is the SUPPLY side of `slate.PRICE_COLUMNS_THE_ESTIMATOR_READS`, and
#: since 2026-09-07 the seam checks that list before it builds anything: a
#: frame short of one of those six is `slate.NO_SUBJECT_COLUMNS`, refused in
#: words naming the column, rather than zero subjects reported as a night on
#: which nobody was quoted. `tests/test_player_seam.py::test_s12_the_price_
#: columns_the_card_supplies_are_the_price_columns_the_estimator_reads` holds
#: this tuple over that one, so a column dropped here fails at the card rather
#: than emptying the player half of every run.
MODEL_PRICE_COLUMNS: tuple[str, ...] = (
    "event_id",
    "game_id",
    "market",
    "player",
    "home_team",
    "away_team",
    "home_name",
    "away_name",
)


class InputsAbsent(RuntimeError):
    """A file the model needs is not on disk. Nothing was priced."""


@dataclass
class CardMatchups:
    """What the model was asked, what it was given, and what it answered."""

    #: Kept as the plain dict it has always been, so every existing reader —
    #: `run_gameday_card`, `summary_line`, the card's own tests — is unchanged.
    #: `slate` below is the same answer with the player half beside it.
    matchups: dict[str, object] = field(default_factory=dict)
    day: str = ""
    #: Distinct events on the board for this slate day.
    events: int = 0
    #: Events whose two schools resolved to one scheduled game on the day.
    resolved: int = 0
    #: Provider spellings the index could not resolve, with how often.
    unresolved_names: dict[str, int] = field(default_factory=dict)
    #: Events whose names resolved but named no game on the schedule that day.
    no_fixture: int = 0
    #: Team-game rows the model was allowed to see, and the latest day among them.
    history_rows: int = 0
    priced_through: str = ""
    table_path: str = ""
    model: str = PB.DEFAULT_MODEL
    #: Both halves in one container. `matchups` above is `slate.matchups`.
    slate: slate.SlateModel = field(default_factory=slate.SlateModel)
    #: Player rows the card CUT and was prepared to show, and the latest day
    #: among them. Reported separately from `slate.player_priced_through`,
    #: which is what the model said it actually read: the two differing is the
    #: only visible symptom of a model reading a table nobody handed it.
    player_history_rows: int = 0
    player_history_through: str = ""
    player_table_path: str = ""

    @property
    def player_priced_through(self) -> str:
        """What the model reported reading of the player table. `""` for none."""
        return self.slate.player_priced_through

    @property
    def resolution_census(self) -> Mapping[str, int]:
        """Resolution route -> subjects. Empty while no estimator is written."""
        return self.slate.resolution_census

    def summary_line(self) -> str:
        priceable = sum(
            1 for m in self.matchups.values() if bool(getattr(m, "priceable", False))
        )
        unresolved = sum(self.unresolved_names.values())
        return (
            f"Model `{self.model}` asked about {self.events:,} event(s) on {self.day}: "
            f"{self.resolved:,} resolved to a scheduled game, {self.no_fixture:,} "
            f"named no game on the schedule that day, {unresolved:,} name(s) did "
            f"not resolve. It returned {len(self.matchups):,} matchup(s), "
            f"{priceable:,} priceable. History: {self.history_rows:,} team-game "
            f"row(s) strictly before {self.day}"
            + (f", through {self.priced_through}" if self.priced_through else "")
            + f", from `{self.table_path}`."
        )

    def player_summary_line(self) -> str:
        """What the player half was offered, what it read, and what it said.

        Printed beside :meth:`summary_line` every run. A census with no line of
        its own is a census nobody reads, and design 13's fifth failure mode —
        name resolution drifting by tier — is only catchable if the number is
        in front of somebody every night rather than in a JSON file.
        """
        athletes = sum(len(by_athlete) for by_athlete in self.slate.players.values())
        line = (
            f"Player history: {self.player_history_rows:,} row(s) strictly "
            f"before {self.day}"
            + (
                f", through {self.player_history_through}"
                if self.player_history_through
                else ""
            )
            + f", from `{self.player_table_path}`. The model read "
            + (self.player_priced_through or "none of it")
            + f" and projected {athletes:,} athlete(s) on "
            f"{len(self.slate.players):,} event(s); "
            f"{len(self.slate.name_refusals):,} name(s) refused."
        )
        if self.slate.player_absence_reason:
            line += f" {self.slate.player_absence_reason}."
        return line


def table_path(
    competition: Competition, processed_dir: Path | str | None, stem: str
) -> Path:
    directory = Path(processed_dir) if processed_dir else Path(PROCESSED_DIR)
    return directory / competition.output_name(stem, ".csv")


def team_games_path(competition: Competition, processed_dir: Path | str | None) -> Path:
    return table_path(competition, processed_dir, REQUIRED_TABLE)


def player_games_path(competition: Competition, processed_dir: Path | str | None) -> Path:
    return table_path(competition, processed_dir, PLAYER_TABLE)


def load_player_games(
    competition: Competition, processed_dir: Path | str | None
) -> pd.DataFrame:
    """The player table the player seam projects from, or a refusal naming it.

    Two lists, and they are two different questions.
    `slate.REQUIRED_PLAYER_COLUMNS` is what must EXIST — a table without one of
    those eight cannot be cut, stamped or projected from at all, so its absence
    refuses the run here rather than downstream. `slate.PLAYER_COLUMNS_THE_
    ESTIMATOR_READS` is what is READ, and it is the seventeen `player_rates`
    forms a per-minute rate from. Reading the eight was the defect: every
    athlete on the card path was refused under R6 and the card's whole player
    half was structurally empty while nothing in the run said so.

    A box-score column that is missing from the file is **not** required here
    and is **not** defaulted. It is simply absent from the frame, and R6 then
    refuses each athlete in a sentence naming the column, while the team half
    of the card still prices. Requiring it instead would make a table built
    without `steals` refuse the whole card, which is the shape of defect this
    lab has already paid for once.

    Cost, re-measured on the 207,954,921-byte, 1,493,589-row table in
    `data/processed/`, best of three: 1.09 seconds for the eight, 1.33 for the
    seventeen read here, 1.77 for all thirty-two.
    """
    path = player_games_path(competition, processed_dir)
    if not path.is_file():
        raise InputsAbsent(
            f"{path} does not exist, so no athlete on tonight's board can be "
            "projected and the player half of the model cannot be asked. Run "
            "`scripts/fetch_cbb_data.py` and then `scripts/build_datasets.py`. "
            "Nothing was priced: a card that projected no athlete because the "
            "table was absent is indistinguishable from one whose player model "
            "declined every subject, and this run refuses to publish that "
            "ambiguity as a night of evidence."
        )
    header = pd.read_csv(path, nrows=0)
    missing = [c for c in slate.REQUIRED_PLAYER_COLUMNS if c not in header.columns]
    if missing:
        raise InputsAbsent(
            f"{path} is missing {missing}, which the player seam requires. "
            "Nothing is defaulted: a missing column read as a zero is how a "
            "wiring fault becomes a finding. Nothing was priced."
        )
    wanted = [
        column
        for column in slate.PLAYER_COLUMNS_THE_ESTIMATOR_READS
        if column in header.columns
    ]
    return pd.read_csv(path, usecols=wanted, low_memory=False)


def load_team_games(
    competition: Competition, processed_dir: Path | str | None
) -> pd.DataFrame:
    """The results table the model fits on, or a refusal naming the file."""
    path = team_games_path(competition, processed_dir)
    if not path.is_file():
        raise InputsAbsent(
            f"{path} does not exist, so the model cannot be asked for an "
            "opinion on any game. Run `scripts/fetch_cbb_data.py` and then "
            "`scripts/build_datasets.py`. Nothing was priced and nothing was "
            "frozen: a card with no opinion on anything is indistinguishable "
            "from a card whose model was never asked, and this run refuses to "
            "publish that ambiguity as a night of evidence."
        )
    frame = pd.read_csv(path, low_memory=False)
    if "slate_date" not in frame.columns:
        raise InputsAbsent(
            f"{path} has no `slate_date` column, so the walk-forward cut cannot "
            "be made and the model was not asked."
        )
    return frame


def load_schedule(
    season: int, raw_dir: Path | str | None
) -> pd.DataFrame:
    """The hoopR schedule for one season, or a refusal naming the file."""
    feed = hoopr.FEEDS["schedules"]
    path = feed.path(int(season), Path(raw_dir) if raw_dir else Path(RAW_DIR))
    if not path.is_file():
        raise InputsAbsent(
            f"No cached schedule for season {season} at {path}. Without it no "
            "event on the board can be joined to a game, so the model cannot be "
            "asked about any of them. Run `scripts/fetch_cbb_data.py`. Nothing "
            "was priced."
        )
    try:
        return pd.read_parquet(path)
    except (OSError, ValueError) as exc:
        raise InputsAbsent(f"{path} could not be read ({exc}). Nothing was priced.") from exc


def fixture_index_from_schedule(schedule: pd.DataFrame) -> _FixtureIndex:
    """The settlement resolver's index, built from the schedule.

    `forward_evidence._build_fixture_index` builds the same structure from the
    results table, which cannot describe a game that has not been played. The
    schedule can, and the resolver — with its `among` disambiguation for a
    school name two programmes share — is reused unchanged.
    """
    by_pair: dict = {}
    by_team_day: dict = {}
    game: dict = {}
    if schedule is None or schedule.empty:
        return _FixtureIndex(by_pair, by_team_day, game)
    for record in schedule.to_dict("records"):
        day = clean_text(record.get("game_date"))[:10]
        try:
            game_id = int(record.get("id") if record.get("id") is not None else record.get("game_id"))
            home = int(record.get("home_id"))
            away = int(record.get("away_id"))
        except (TypeError, ValueError):
            continue
        if not day:
            continue
        by_pair[(day, _pair(home, away))] = game_id
        by_team_day.setdefault((day, home), []).append((game_id, away))
        by_team_day.setdefault((day, away), []).append((game_id, home))
        game[game_id] = {"home_team_id": home, "away_team_id": away}
    return _FixtureIndex(by_pair, by_team_day, game)


def attach_game_ids(
    rows: pd.DataFrame,
    *,
    day: str,
    schedule: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, int], int]:
    """One joined row per event, plus what could not be joined.

    Returns the per-event join — `event_id`, `game_id`, and the two hoopR team
    ids the fixture named — the unresolved provider spellings with their
    counts, and the number of events whose names resolved but matched no
    scheduled game.

    **The team ids are carried out of here rather than re-derived.** They are
    already in hand: `game_id` came from the fixture index, and that index
    holds the fixture's two ids beside it. The player half needs them to know
    which roster a quoted spelling is resolved against, and the only other
    place to get them is a second resolution of the provider's two school
    names — a second join, on names, in the report layer, against the rule
    `ratings.matchups_for` states in its own docstring. A game that resolves
    but whose fixture record carries no readable pair leaves both `None`, which
    reaches the estimator as "no team filter" rather than as a wrong one.
    """
    columns = ["event_id", "game_id", "home_team", "away_team"]
    if rows is None or rows.empty or "event_id" not in rows.columns:
        return pd.DataFrame(columns=columns), {}, 0
    wanted = ["event_id", "home_team", "away_team"]
    present = [c for c in wanted if c in rows.columns]
    events = rows[present].drop_duplicates(subset=["event_id"])
    index = team_names.build_index(schedule)
    fixtures = fixture_index_from_schedule(schedule)
    out: list[dict] = []
    no_fixture = 0
    for record in events.to_dict("records"):
        event_id = clean_text(record.get("event_id"))
        if not event_id:
            continue
        home = clean_text(record.get("home_team"))
        away = clean_text(record.get("away_team"))
        game_id = fixtures.resolve(home, away, str(day), index)
        if game_id is None:
            if index.resolve(home) is not None and index.resolve(away) is not None:
                no_fixture += 1
            out.append(
                {"event_id": event_id, "game_id": None,
                 "home_team": None, "away_team": None}
            )
            continue
        fixture = fixtures.game.get(int(game_id), {})
        out.append(
            {
                "event_id": event_id,
                "game_id": int(game_id),
                "home_team": fixture.get("home_team_id"),
                "away_team": fixture.get("away_team_id"),
            }
        )
    frame = pd.DataFrame(out, columns=columns)
    return frame, dict(index.unresolved), no_fixture


def model_prices(rows: pd.DataFrame, joined: pd.DataFrame) -> pd.DataFrame:
    """The board's quotes in the price store's vocabulary, for the model.

    One row per board quote whose event joined to a scheduled game. The team
    half reads `event_id` and `game_id` off the first row it sees for an event
    and ignores the rest (`matchups_for` dedupes on `event_id`), so this frame
    is the same answer it was given before for that half. The player half reads
    `market` and `player` to find the day's subjects, counts a subject's quotes
    to weight the resolution census, and reads `home_team`/`away_team` to pick
    the roster the spelling is resolved against — none of which existed on the
    two-column frame this call site used to hand over, so no board ever
    produced a subject and the whole player half read as a night on which
    nobody was quoted.

    **`home_team` is a team id here and a school name on the board.** The two
    vocabularies collide on one word, and the collision is the reason this
    function exists rather than a `rows[[...]]` at the call site: an
    accidentally-passed board frame would resolve every spelling against a
    league-wide roster instead of two teams, which is a name matched to the
    wrong athlete rather than a refusal. The provider's spellings are kept
    beside the ids as `home_name`/`away_name`, which is what the store calls
    them, so nothing is dropped and nothing is renamed in place.
    """
    if rows is None or rows.empty or joined is None or joined.empty:
        return pd.DataFrame(columns=list(MODEL_PRICE_COLUMNS))
    fixture_of = {
        clean_text(record.get("event_id")): record
        for record in joined.to_dict("records")
    }
    out: list[dict] = []
    for record in rows.to_dict("records"):
        event_id = clean_text(record.get("event_id"))
        fixture = fixture_of.get(event_id)
        if not event_id or fixture is None:
            continue
        out.append(
            {
                "event_id": event_id,
                "game_id": _whole(fixture.get("game_id")),
                "market": clean_text(record.get("market")),
                "player": clean_text(record.get("player")),
                "home_team": _whole(fixture.get("home_team")),
                "away_team": _whole(fixture.get("away_team")),
                "home_name": clean_text(record.get("home_team")),
                "away_name": clean_text(record.get("away_team")),
            }
        )
    return pd.DataFrame(out, columns=list(MODEL_PRICE_COLUMNS))


def _whole(value: object) -> object:
    """An id as an int where it is one, and untouched where it is not.

    A pandas column carrying one unjoined event holds `None` and therefore
    floats, so a game id that went in as 401823218 comes back out of
    :func:`attach_game_ids` as 401823218.0. `player_rates._id_key` folds the
    two spellings together for the team join, but `PlayerProjection.game_id` is
    STORED, and a float id written into `cbb_player_lines.csv` later is a join
    key that no longer matches the integer one every other table carries.
    """
    if value is None or isinstance(value, str):
        return value
    try:
        if value != value:  # NaN
            return None
        return int(value)
    except (TypeError, ValueError):
        return value


def matchups_for_card(
    rows: pd.DataFrame,
    *,
    competition: Competition,
    day: str,
    processed_dir: Path | str | None = None,
    raw_dir: Path | str | None = None,
    model: Callable | str = PB.DEFAULT_MODEL,
) -> CardMatchups:
    """One matchup per event the model can price, for the card's day.

    Raises :class:`InputsAbsent` when either results table or the season's
    schedule is not on disk. Returns an empty mapping — and says so in its
    summary — when the inputs exist and no event on the board joins to a game.

    **Both frames are cut by `history_before` and both are handed to the
    model**, under the names the walk-forward harness uses: `history` and
    `player_history`. A model that declares neither, or only the first, is
    handed only what it declares — `call_model` filters — so this call site is
    identical for `ratings.matchups_for`, which reads no player table, and for
    `slate.slate_model`, which does. That is what makes the swap a one-line
    change to `DEFAULT_MODEL` rather than a change to the card.

    That sentence was **false when it was written**, in two places, and both
    are closed here. The player frame was cut to eight columns carrying no box
    score, so `player_rates` refused every athlete under R6; and the price
    frame was `attach_game_ids`' two columns, so the estimator found no subject
    to refuse in the first place. Driven through this function with
    `slate.slate_model` over the four-game board
    `tests/test_player_seam.py::_card_board` builds on the tracked sample
    corpus — 20 `player_points` quotes on 10 athletes — the three states are:
    two-column price frame, 0 projections and all 20 props declined "the model
    was never asked about this event's athletes"; eight-column player frame, 10
    subjects resolved and all 10 refused under R6, 0 props priced; repaired, 10
    priceable, all 20 props priced and design 4's structural check run over 10
    regulars. What still stops a shipped nightly run is `DEFAULT_MODEL` alone —
    it resolves the team seam, which declares no `player_history` — and that is
    now genuinely the one-line gate this paragraph always claimed it was.

    Whatever the model returns is coerced to a `slate.SlateModel`, so the card
    reads one container whether the model answered with a bare mapping of
    matchups or with both halves.
    """
    resolved_model = PB.resolve_model(model) if isinstance(model, str) else model
    model_name = model if isinstance(model, str) else getattr(model, "__qualname__", repr(model))
    team_games = load_team_games(competition, processed_dir)
    player_games = load_player_games(competition, processed_dir)
    season = season_for_slate_date(day)
    schedule = load_schedule(season, raw_dir)

    # One definition of "strictly earlier", for both tables. A second copy of
    # this cut is how a card comes to be fitted on a population no measurement
    # ever saw; the football lab's defect 13 was the same comparison written
    # with `<=` in one of its two places.
    history = PB.history_before(team_games, day)
    player_history = PB.history_before(player_games, day)
    priced_through = (
        str(history["slate_date"].astype(str).max()) if not history.empty else ""
    )
    player_through = PB.latest_day(player_history)
    prices, unresolved, no_fixture = attach_game_ids(rows, day=day, schedule=schedule)
    joined = prices.dropna(subset=["game_id"]) if not prices.empty else prices
    # The board's own quotes, joined to their games and translated into the
    # store's vocabulary. `events` and `resolved` below are still counted off
    # the per-event join, because they are counts of EVENTS.
    asked = model_prices(rows, joined)

    answered: object = None
    if not joined.empty:
        answered = PB.call_model(
            resolved_model,
            "the gameday card's matchups_for_card",
            day=str(day),
            history=history,
            prices=asked,
            competition=competition,
            raw_dir=Path(raw_dir) if raw_dir else Path(RAW_DIR),
            player_history=player_history,
        )
    built = slate.SlateModel.coerce(
        answered,
        day=str(day),
        team_priced_through=priced_through,
        # NOT `player_through`. The stamp is what the MODEL read, and a model
        # that never declared the frame read none of it; writing the card's own
        # cut here would put the card's knowledge on the model's row, which is
        # precisely the stamp defect `_stamp_series` exists to prevent.
        player_priced_through="",
    )
    return CardMatchups(
        matchups=dict(built.matchups),
        day=str(day),
        events=int(len(prices)),
        resolved=int(len(joined)),
        unresolved_names=unresolved,
        no_fixture=int(no_fixture),
        history_rows=int(len(history)),
        priced_through=priced_through,
        table_path=str(team_games_path(competition, processed_dir)),
        model=str(model_name),
        slate=built,
        player_history_rows=int(len(player_history)),
        player_history_through=player_through,
        player_table_path=str(player_games_path(competition, processed_dir)),
    )
