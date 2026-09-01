"""The interpreter: a provider response, read into this lab's vocabulary.

`providers/odds_api.py` fetches and counts what it cost, and deliberately does
not normalise anything. This module is the other half, and it is a separate
file on purpose — **the thing that spends money and the thing that interprets
the answer must not be able to become one.** A fetch can be wrong, incomplete
or surprising, and a mis-read response can be wrong in a completely different
way, without either failure being able to hide inside the other.

Nothing this module writes can reach the card. It writes to `data/staging/` and
:func:`write_staged` refuses any other destination; the card reads only markets
a reviewed policy allowlists, and no market is allowlisted.

## Every row is staged in this lab's vocabulary, never the provider's

This is the NHL lab's join-vocabulary bug family — five members, weeks lost, and
every one of them silent. The two that land squarely here:

* **Outcomes staged in the provider's spelling.** The provider names a
  moneyline's sides after the schools, so a row staged as `Duke` instead of
  `home` misses every downstream join and nothing errors.
* **Yes/no markets staged under two spellings.** `player_double_double` is
  priced Yes/No by the provider and as the underlying count **over 0.5** by this
  lab. Both spellings settle identically, so two spellings are one wager staked
  twice — published as two independent best bets at two prices and frozen into
  the ledger twice. :data:`selection.YES_NO_LINE` is the one line those markets
  ever carry, and `yes_no_selection` is the only thing that maps them.

So every selection here comes from `selection.py`, every market from
`markets.market_for_provider_key`, and every slate day from `season.slate_date`.
No spelling is invented in this file.

## Unparseable is a counted outcome, never a dropped row

Four things can stop an outcome becoming a staged row, and all four are counted
with the provider key that produced them:

1. **The market key is not wired.** `market_for_provider_key` returns None
   rather than raising, because an unwired key arriving in a response is *data
   about the provider* on a request that has already been paid for.
2. **The outcome resolves to no known selection.** A `Draw` outcome, a team
   name that is neither school, a futures winner — this sport has no draw and
   this vocabulary has no word for "wins the tournament", and inventing one is
   how a staged row joins something it is not.
3. **The price is missing or unreadable.** A missing value stays missing. The
   football lab read a missing settlement column as a zero through
   `getattr(..., None)` and reported a backtest of zero bets, which read as "the
   model never disagrees enough" rather than "the column was never built".
4. **The event cannot be placed.** Without both school names there is no
   `selection_key` — the key carries them — and without a commence time there is
   no slate day and no tip guard. Both fail closed, per event, counted.

:class:`StagingCounts` reconciles `outcomes = staged + the four refusals`. A row
that reaches none of the five vanished silently, and a silent drop is how a
biased subset becomes the record of a night. With a 200-game slate and 35
markets that arithmetic is the only thing standing between a partial read and a
confident one.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from cbb_betting_lab.competitions import Competition
from cbb_betting_lab.config import STAGING_DIR
from cbb_betting_lab.markets import PLAYER, TEAM, market_for_provider_key
from cbb_betting_lab.season import clean_text, slate_date
from cbb_betting_lab.selection import (
    YES_NO_LINE,
    normalise_line,
    over_under_selection,
    team_selection,
    team_total_selection,
    yes_no_selection,
)


#: The long-form row this lab stages. One row per outcome per book, because a
#: book is part of a quote's identity (`stores.PRICE_IDENTITY`) and collapsing
#: books here would destroy the line-shopping evidence before it was recorded.
#: **No timestamp**: adding one re-introduces the NHL lab's whole-row dedupe,
#: which wrote every quote twice and made every interval root-two too narrow
#: while nothing about the output looked wrong.
STAGED_COLUMNS: tuple[str, ...] = (
    "event_id",
    "commence_time",
    "slate_date",
    "home_team",
    "away_team",
    "market",
    "segment",
    "player",
    "selection",
    "line",
    "american_odds",
    "book",
    "provider_key",
)

#: Which settlement quantity gets which selection vocabulary. Dispatching on the
#: **named settlement quantity** rather than on the market key means a market
#: added to the registry is staged correctly on the day it is wired, and a
#: market whose quantity is unfamiliar is refused rather than guessed at.
TEAM_SIDE_QUANTITIES: frozenset[str] = frozenset({"game_margin", "half_margin"})
GAME_TOTAL_QUANTITIES: frozenset[str] = frozenset({"game_total", "half_total"})
TEAM_TOTAL_QUANTITIES: frozenset[str] = frozenset({"team_score", "half_team_score"})

#: Refusal reasons, as fixed strings so a report groups on them rather than on
#: prose that drifts. Grouped counts are the point: seventeen rows of one
#: identical sentence is noise, and noise is how the line that matters is
#: skipped.
UNWIRED_MARKET = "the market key is not wired"
UNKNOWN_SELECTION = "the outcome resolves to no known selection"
UNREADABLE_PRICE = "the price is missing or unreadable"
UNPLACEABLE_EVENT = "the event carries no usable teams or commence time"


class StagingEscapeError(RuntimeError):
    """Something tried to write staged rows outside `data/staging/`.

    Raised rather than corrected. Staged rows are unreviewed provider data; the
    only thing keeping them away from the card is that they live somewhere the
    card does not read, and a writer that silently redirected would remove that
    guarantee without removing anybody's belief in it.
    """


@dataclass
class StagingCounts:
    """The accounting identity for one read of a provider response.

    `outcomes = staged + unwired + unknown_selection + unreadable_price +
    unplaceable_event`, and :meth:`reconciles` proves it every run.
    """

    events: int = 0
    #: Events that produced at least one staged row.
    events_staged: int = 0
    bookmakers: int = 0
    outcomes: int = 0
    staged: int = 0
    #: provider key -> count, for each of the four refusals. Keyed by provider
    #: key because that is the unit a coverage question is asked in, and rolled
    #: up to the market by the caller — **every retention conclusion rolls up to
    #: the market, never the provider key**, which is the EPL lab's `total_2_5`
    #: defect: the complete line was absent from `totals` and present all along
    #: in `alternate_totals`, and the market was written off for a season.
    unwired_market: dict[str, int] = field(default_factory=dict)
    unknown_selection: dict[str, int] = field(default_factory=dict)
    unreadable_price: dict[str, int] = field(default_factory=dict)
    unplaceable_event: dict[str, int] = field(default_factory=dict)

    def _add(self, bucket: dict[str, int], key: str, amount: int = 1) -> None:
        bucket[key] = bucket.get(key, 0) + int(amount)

    @property
    def refused(self) -> int:
        return (
            sum(self.unwired_market.values())
            + sum(self.unknown_selection.values())
            + sum(self.unreadable_price.values())
            + sum(self.unplaceable_event.values())
        )

    def reconciles(self) -> bool:
        return self.outcomes == self.staged + self.refused

    def merge(self, other: "StagingCounts") -> "StagingCounts":
        """Fold another read's counts in. Used across a slate of events."""
        self.events += other.events
        self.events_staged += other.events_staged
        self.bookmakers += other.bookmakers
        self.outcomes += other.outcomes
        self.staged += other.staged
        for name in (
            "unwired_market",
            "unknown_selection",
            "unreadable_price",
            "unplaceable_event",
        ):
            for key, value in getattr(other, name).items():
                self._add(getattr(self, name), key, value)
        return self

    def summary_line(self) -> str:
        state = "reconciles" if self.reconciles() else "DOES NOT RECONCILE"
        return (
            f"{self.events:,} event(s), {self.bookmakers:,} bookmaker block(s), "
            f"{self.outcomes:,} outcome(s) = {self.staged:,} staged + "
            f"{sum(self.unwired_market.values()):,} unwired market + "
            f"{sum(self.unknown_selection.values()):,} unknown selection + "
            f"{sum(self.unreadable_price.values()):,} unreadable price + "
            f"{sum(self.unplaceable_event.values()):,} unplaceable event "
            f"({state})."
        )

    def refusal_table(self) -> str:
        """Refusals grouped by reason and provider key, never one row each."""
        groups = (
            (UNWIRED_MARKET, self.unwired_market),
            (UNKNOWN_SELECTION, self.unknown_selection),
            (UNREADABLE_PRICE, self.unreadable_price),
            (UNPLACEABLE_EVENT, self.unplaceable_event),
        )
        lines = ["| Reason | Provider key | Outcomes |", "|:---|:---|---:|"]
        rows = 0
        for reason, bucket in groups:
            for key, count in sorted(bucket.items(), key=lambda kv: (-kv[1], kv[0])):
                lines.append(f"| {reason} | `{key}` | {count:,} |")
                rows += 1
        if not rows:
            return "Every outcome in this response was staged."
        return "\n".join(lines)

    def raise_if_unreconciled(self) -> None:
        if not self.reconciles():
            raise ValueError(
                "The staging identity does not reconcile: "
                + self.summary_line()
                + " An outcome that reached none of the five buckets vanished "
                "silently, and a silent drop is how a biased subset becomes "
                "the record of a night."
            )


def _american(value: object) -> float | None:
    """An American price as a float, or None. Never a guess, never a zero.

    `0` is not a price in American odds — it is what an unreadable field looks
    like after a careless `float(x or 0)`, and a zero price makes every edge
    computed against it nonsense in the flattering direction.
    """
    text = clean_text(value)
    if not text:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    if number != number or number == 0.0:
        return None
    return number


def _selection_for(
    market, outcome: Mapping, *, home_team: str, away_team: str
) -> tuple[str | None, str, float | None]:
    """`(selection, player, line)` in this lab's vocabulary, or `(None, …)`.

    None rather than a guess, every time. The provider hands over an outcome
    name, an optional `description` — which is the school on a team total and
    the athlete on a prop — and an optional `point`.
    """
    name = outcome.get("name")
    description = clean_text(outcome.get("description"))

    if market.yes_no:
        # The one place a yes/no market becomes a count over 0.5. Both spellings
        # settle identically, so allowing a second one stakes one wager twice.
        return yes_no_selection(name), description, YES_NO_LINE

    point = normalise_line(outcome.get("point"))

    if market.family == PLAYER:
        return over_under_selection(name), description, point

    if market.family == TEAM:
        if market.settles_on in TEAM_TOTAL_QUANTITIES:
            # Both schools arrive under one provider key: the side is in the
            # description and Over/Under is in the name.
            return (
                team_total_selection(name, description, home_team, away_team),
                "",
                point,
            )
        if market.settles_on in GAME_TOTAL_QUANTITIES:
            return over_under_selection(name), "", point
        if market.settles_on in TEAM_SIDE_QUANTITIES:
            # A `Draw` outcome lands here and resolves to None. There is no draw
            # in this sport; a row carrying one came from somewhere it should
            # not have, and it is counted rather than carried.
            return team_selection(name, home_team, away_team), "", point

    # A futures winner ("wins the championship") has no word in this
    # vocabulary, and neither does an unfamiliar settlement quantity. Both are
    # counted as unknown selections rather than given an invented spelling.
    return None, description, point


def stage_event(
    payload: Mapping, *, competition: Competition
) -> tuple[list[dict], StagingCounts]:
    """One provider event payload, read into long-form rows and counts.

    Accepts the shape both odds endpoints return: an event object carrying
    `bookmakers -> markets -> outcomes`. The bulk endpoint returns a list of
    these and the per-event endpoint returns one; :func:`stage_payloads` folds
    either.

    The event is placed **before** any outcome is read. Without both school
    names there is no `selection_key` — it carries them — and without a commence
    time there is no slate day and nothing for the tip guard to judge. A price
    on a game this lab cannot place is not a price it can use, so the whole
    event is refused, its outcomes are counted, and the run continues. Per
    event, never per slate: Cooper's rule is **abstain rather than nuke a real
    slate**, and a guard that dropped a night because one event was malformed
    would have done more damage than the error it prevented.
    """
    counts = StagingCounts(events=1)
    rows: list[dict] = []

    event_id = clean_text(payload.get("id"))
    commence_time = clean_text(payload.get("commence_time"))
    home_team = clean_text(payload.get("home_team"))
    away_team = clean_text(payload.get("away_team"))
    bookmakers = [b for b in (payload.get("bookmakers") or []) if isinstance(b, Mapping)]

    placeable = bool(event_id and commence_time and home_team and away_team)
    day = slate_date(commence_time, competition) if placeable else ""

    for bookmaker in bookmakers:
        counts.bookmakers += 1
        book = clean_text(bookmaker.get("key")) or clean_text(bookmaker.get("title"))
        for block in bookmaker.get("markets") or []:
            if not isinstance(block, Mapping):
                continue
            provider_key = clean_text(block.get("key"))
            outcomes = [o for o in (block.get("outcomes") or []) if isinstance(o, Mapping)]
            counts.outcomes += len(outcomes)

            if not placeable:
                counts._add(counts.unplaceable_event, provider_key or "<no key>", len(outcomes))
                continue

            market = market_for_provider_key(provider_key)
            if market is None:
                counts._add(counts.unwired_market, provider_key or "<no key>", len(outcomes))
                continue

            for outcome in outcomes:
                selection, player, line = _selection_for(
                    market, outcome, home_team=home_team, away_team=away_team
                )
                if selection is None:
                    counts._add(counts.unknown_selection, provider_key)
                    continue
                price = _american(outcome.get("price"))
                if price is None:
                    counts._add(counts.unreadable_price, provider_key)
                    continue
                rows.append(
                    {
                        "event_id": event_id,
                        "commence_time": commence_time,
                        "slate_date": day,
                        "home_team": home_team,
                        "away_team": away_team,
                        "market": market.key,
                        "segment": market.segment,
                        "player": player,
                        "selection": selection,
                        "line": line,
                        "american_odds": price,
                        "book": book,
                        "provider_key": provider_key,
                    }
                )
                counts.staged += 1

    if rows:
        counts.events_staged = 1
    return rows, counts


def stage_payloads(
    payloads: Iterable[Mapping] | Mapping, *, competition: Competition
) -> tuple[pd.DataFrame, StagingCounts]:
    """Every event in a bulk or per-event response, folded into one frame."""
    if isinstance(payloads, Mapping):
        payloads = [payloads]
    rows: list[dict] = []
    counts = StagingCounts()
    for payload in payloads:
        if not isinstance(payload, Mapping):
            continue
        staged, event_counts = stage_event(payload, competition=competition)
        rows.extend(staged)
        counts.merge(event_counts)
    return pd.DataFrame(rows, columns=list(STAGED_COLUMNS)), counts


def staging_dir_for(
    competition: Competition, staging_dir: Path | str | None = None
) -> Path:
    """`data/staging/<competition>/`. Competition-prefixed like every output."""
    root = Path(staging_dir) if staging_dir else Path(STAGING_DIR)
    return root / competition.data_dir_segment


def staging_path(
    competition: Competition,
    *,
    day: str,
    slot: str = "",
    staging_dir: Path | str | None = None,
) -> Path:
    """Where one read of the board lands. One file per slate day and slot.

    Per slot, not per day: `docs/card_cadence.md` runs two slots because a noon
    tip and an eleven-o'clock tip cannot share one freeze, and two reads of the
    board written over each other would destroy the second half of that
    evidence — the late, West Coast, low-major end of the slate, which is the
    end this lab was built to look at.
    """
    stem = clean_text(day) or "undated"
    if slot:
        stem = f"{stem}_{clean_text(slot)}"
    return staging_dir_for(competition, staging_dir) / f"{stem}.csv"


def write_staged(
    rows: pd.DataFrame | Iterable[Mapping],
    path: Path | str,
    *,
    staging_dir: Path | str | None = None,
) -> Path:
    """Write staged rows, and refuse any destination outside `data/staging/`.

    The refusal is the point. Staged rows are unreviewed provider data whose
    only protection is that they live where the card does not read; a writer
    that could be pointed at `data/processed/` would remove the protection
    without removing anyone's belief in it. Checked on the **resolved** path, so
    a `..` cannot walk out of the directory.
    """
    root = (Path(staging_dir) if staging_dir else Path(STAGING_DIR)).resolve()
    target = Path(path).resolve()
    if not target.is_relative_to(root):
        raise StagingEscapeError(
            f"Refusing to write staged rows to {target}: it is outside "
            f"{root}. Nothing staged may live where the card could read it — "
            "the card reads only markets a reviewed policy allowlists, and no "
            "market is allowlisted."
        )
    frame = (
        rows
        if isinstance(rows, pd.DataFrame)
        else pd.DataFrame(list(rows), columns=list(STAGED_COLUMNS))
    )
    for column in STAGED_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    target.parent.mkdir(parents=True, exist_ok=True)
    frame[list(STAGED_COLUMNS)].to_csv(target, index=False, lineterminator="\n")
    return target
