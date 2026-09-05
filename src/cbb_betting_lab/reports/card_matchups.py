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
  today; a rehearsal of a past day does, and the same cut protects both.
* **The join** is on hoopR's `game_id`, resolved from the provider's two
  school names through `providers.team_names` and
  `forward_evidence._FixtureIndex.resolve` — the settlement resolver, so a
  game is found for pricing by the same rule it will later be found for
  grading. Built from the **schedule** rather than the results table, because
  tonight's game has no result row yet.

## What is refused, and why it is a refusal

The processed table the model fits on (`cbb_team_games.csv`) or the cached
schedule for the season being absent raises :class:`InputsAbsent`. The entry
point turns that into `::error::` and `decision=refused`. It is not degraded to
"price nothing and carry on", because that is precisely the state this module
exists to end: a card with no opinion on anything is indistinguishable, from
the outside, from a card whose model was never asked. **The card must say it
priced no opinion; it may never silently price none.**
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
from cbb_betting_lab.providers import team_names
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.season import clean_text, season_for_slate_date

#: The one processed table the model fits on. `game_segments` and
#: `player_games` settle; they do not price, so their absence is settlement's
#: business and not the card's.
REQUIRED_TABLE = "team_games"


class InputsAbsent(RuntimeError):
    """A file the model needs is not on disk. Nothing was priced."""


@dataclass
class CardMatchups:
    """What the model was asked, what it was given, and what it answered."""

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


def team_games_path(competition: Competition, processed_dir: Path | str | None) -> Path:
    directory = Path(processed_dir) if processed_dir else Path(PROCESSED_DIR)
    return directory / competition.output_name(REQUIRED_TABLE, ".csv")


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
    """One `(event_id, game_id)` row per event, plus what could not be joined.

    Returns the price frame the model reads — `event_id` and `game_id`, one row
    per event — the unresolved provider spellings with their counts, and the
    number of events whose names resolved but matched no scheduled game.
    """
    if rows is None or rows.empty or "event_id" not in rows.columns:
        return pd.DataFrame(columns=["event_id", "game_id"]), {}, 0
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
            out.append({"event_id": event_id, "game_id": None})
            continue
        out.append({"event_id": event_id, "game_id": int(game_id)})
    frame = pd.DataFrame(out, columns=["event_id", "game_id"])
    return frame, dict(index.unresolved), no_fixture


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

    Raises :class:`InputsAbsent` when the results table or the season's
    schedule is not on disk. Returns an empty mapping — and says so in its
    summary — when the inputs exist and no event on the board joins to a game.
    """
    resolved_model = PB.resolve_model(model) if isinstance(model, str) else model
    model_name = model if isinstance(model, str) else getattr(model, "__qualname__", repr(model))
    team_games = load_team_games(competition, processed_dir)
    season = season_for_slate_date(day)
    schedule = load_schedule(season, raw_dir)

    history = PB.history_before(team_games, day)
    priced_through = (
        str(history["slate_date"].astype(str).max()) if not history.empty else ""
    )
    prices, unresolved, no_fixture = attach_game_ids(rows, day=day, schedule=schedule)
    joined = prices.dropna(subset=["game_id"]) if not prices.empty else prices

    matchups: Mapping[str, object] | None = None
    if not joined.empty:
        matchups = PB.call_model(
            resolved_model,
            day=str(day),
            history=history,
            prices=joined,
            competition=competition,
            raw_dir=Path(raw_dir) if raw_dir else Path(RAW_DIR),
        )
    return CardMatchups(
        matchups=dict(matchups or {}),
        day=str(day),
        events=int(len(prices)),
        resolved=int(len(joined)),
        unresolved_names=unresolved,
        no_fixture=int(no_fixture),
        history_rows=int(len(history)),
        priced_through=priced_through,
        table_path=str(team_games_path(competition, processed_dir)),
        model=str(model_name),
    )
