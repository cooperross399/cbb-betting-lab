"""Which markets the archive still has prices for, and which have *enough* of them.

Those are two different questions and this module keeps them apart. "Does the
provider retain a price for `alternate_team_totals_h2`" is a yes/no about the
archive. "Can this lab measure `team_total_h2` against three seasons of it" is a
question about sample size, and a market can be retained and still be
unmeasurable. Conflating the two is how a lab buys a season of prices for a
market it will never be able to say anything about.

## The two rules the football lab paid 7,280 credits for

**1. Every retention conclusion rolls up to the MARKET, never the provider key.**
Its probe found three featured prop keys returning nothing across all twenty of
its probed events while their alternate ladders had the same market on the same
events. Read per key that is three unmeasurable markets; read per market — the
unit that gets modelled, measured, approved and carded — it is none. So the
per-key counts here are *detail*, printed under a heading that says they are not
a verdict, and the verdict column is computed over `Market.provider_keys`.

**2. The report re-renders from the run record.** Improving a sentence must
never cost credits twice. `probe()` writes a JSON run record holding every count
it made; `render()` is a pure function of that record with no clock, no network
and no randomness in it; and `scripts/rerender_retention_probe.py` rebuilds the
markdown from the cached record with no network access at all.

## The cache filename is the chunk's fingerprint, not its length

The football lab tagged each cached chunk response with the chunk's *length*, so
its four ten-market chunks all wrote `..._10.json`, collided, and three of the
four answers were lost — silently, because the file that survived was a valid
response to a real request. The length of a list is not its identity.
:func:`cbb_betting_lab.providers.odds_api.markets_fingerprint` is, and it is
what every cache path in this module is built from.

## The stratification IS the thesis

This lab exists because the low-major end of the board is plausibly priced with
less attention than the high-major end. A probe that samples the board uniformly
answers a question about the *average* game, and the average game is a mid-major
January evening. So the sample is stratified on the three axes that could each
independently drive coverage:

* **conference tier**, from `conferences.tier_table` — the thesis axis;
* **month of the season**, because November is a different board from March;
* **tip window**, because a 22:00 Eastern tip is served by fewer traders than a
  19:00 one, and this sport tips for twelve hours a day.

Measured on the completed 2025-26 season — 5,752 D-I v D-I countable games —
those three axes cross into **49 non-empty cells**. The board splits
1,343 high-major / 2,359 mid-major / 2,050 low-major by game, and
1,869 afternoon / 2,967 early-evening / 916 late by tip window.

A game's tier is the **higher** of its two teams' tiers, because that is what
decides how much attention the board pays it: a low-major visiting Duke is
priced as a high-major game. So the low-major stratum means *both* sides are
low-major, which is exactly the end of the board the thesis is about.

**The achieved stratification is reported, never assumed.** An unbalanced probe
that reports itself as balanced is worse than no probe, because every later
conclusion inherits the imbalance without anybody being able to see it. The
report prints population, target and drawn per cell, and says in one line
whether every cell was filled.

## A starved fetch and an unquoted market look identical

The NHL lab's probe once reported its own starvation as market absence. Three
separate things stop that here:

1. A market that was never asked is classified **NOT_PROBED**, which is not one
   of the three retention verdicts. It is deliberately impossible for this
   module to call an unasked market "not retained".
2. Every report states the cap it ran under, the pessimistic bound of the plan
   it was given, the credits actually spent, and whether the run **completed**.
3. A live run refuses to start when the cap is below the plan's pessimistic
   bound, unless the operator passes `--allow-partial` — and a partial run says
   so at the top of its own report.

## What "measurable" means, declared here in advance

:data:`MEASURABLE_EVENT_SHARE` and :data:`MEASURABLE_BOOK_FLOOR` are written
down before any market was probed, and they are not re-tuned afterwards to make
a market qualify. The reasoning:

* `stats.MINIMUM_BETS` is **200** and the full provider catalogue is buyable for
  three seasons only (props, halves and every alternate ladder exist historically
  from 2023-05-03, site-wide). Those three seasons hold **17,234** countable
  D-I v D-I games — 5,723 + 5,759 + 5,752. The smallest tier cell is low-major
  at 2,050 games a season, about 6,150 across the three. A market priced on
  **half** the board leaves roughly 3,000 low-major games, which survives the
  discovery/holdout split and the per-tier split and still clears 200 by an
  order of magnitude. Below half, the low-major cell of a per-tier measurement
  starts to depend on which season happened to get bought.
* A probe of ~49 events cannot resolve a finer line than "more than half". A
  market seen on 25 of 49 events has a Wilson interval spanning roughly 0.37 to
  0.64, so a threshold of 0.45 against 0.55 would be a distinction the
  measurement cannot make. Every share in the report therefore carries its
  Wilson interval and its denominator, and a market whose interval straddles the
  threshold is flagged — and still classified on the conservative side, because
  ambiguity falls on the not-a-play side.
* Two books, not one, because `stores.best_price_per_wager` collapses every
  book's quote on a wager to the best one. With a single book that collapse is a
  no-op, the optimistic and pessimistic brackets in `stores.py` become the same
  number, and the measurement loses the bracket that says whether an edge
  survives price selection.

## What this module does not establish

* Retention is a fact about the archive. It is **not** permission to card
  anything. Nothing in this lab reaches `Availability.CONFIRMED`, so player
  props are priced, frozen and settled and still **cannot be selected**; a
  tier-3 market reading RETAINED_AND_MEASURABLE here is a measurable market and
  not a playable one.
* A market that returns nothing is reported as *the provider returned no price
  for it on any of the N events probed*. It is never called a pass, an avoid, or
  a no-value call — those are claims about a bet, and this probe never priced one.
* This is one snapshot per event, taken
  :data:`SNAPSHOT_MINUTES_BEFORE_TIP` minutes before tip. A market hung only at
  open, or only in-play, is invisible to it, and the report says so.
* Featured markets (`h2h`, `spreads`, `totals`) exist historically for this sport
  from 2020-11-16; everything else from 2023-05-03. Probing a game before the
  relevant cut-off would measure the archive's start date and call it market
  absence, so :func:`guard_history_window` refuses it.
"""

from __future__ import annotations

import json
import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path

import pandas as pd

from cbb_betting_lab import markets as M
from cbb_betting_lab import population as P
from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.conferences import Tier, TierTable
from cbb_betting_lab.providers import team_names
from cbb_betting_lab.providers.env_file import redact
from cbb_betting_lab.providers.odds_api import (
    HISTORICAL_EVENTS_LIST_COST,
    HISTORICAL_MULTIPLIER,
    CreditCapReached,
    OddsApiProvider,
    ProviderError,
    Spend,
    markets_fingerprint,
)
from cbb_betting_lab.season import slate_date_is_derived


# ---------------------------------------------------------------------------
# Declared in advance. Nothing below this block is tuned after a run.
# ---------------------------------------------------------------------------

#: A market is measurable only if it is priced on at least this share of the
#: events where every one of its provider keys was actually asked. See the
#: module docstring for the 200-bet arithmetic and the resolution argument that
#: together pick a half rather than a tenth.
MEASURABLE_EVENT_SHARE = 0.50

#: ...and only if at least this many distinct books quote it. One book is a
#: price; `stores.best_price_per_wager` needs two before "best" means anything.
MEASURABLE_BOOK_FLOOR = 2

#: How long before tip the historical snapshot is taken. Card time, near enough:
#: ladders and props are hung on game day, and a snapshot two days out would
#: measure when a book opens a market rather than whether it has one.
SNAPSHOT_MINUTES_BEFORE_TIP = 60

#: Provider keys per request. Chunking does not change what a run is billed —
#: the bound is `keys x regions x 10` however it is split — it changes three
#: other things: a 422 or a timeout costs one chunk instead of a whole event, a
#: run near its cap gets most of the answer instead of none, and each cached
#: response stays small enough to read by eye.
MARKET_CHUNK_SIZE = 8

#: The seasons whose full catalogue can be bought at all, from the provider's
#: own historical cut-offs. Recorded identically in
#: `scripts/estimate_credit_cost.py`, read from the-odds-api.com on 2026-09-01.
FEATURED_HISTORY_FROM = "2020-11-16"
ADDITIONAL_HISTORY_FROM = "2023-05-03"

#: The default season to probe: the last completed one, which is also inside the
#: full-catalogue window. A probe run on an unfinished season measures how much
#: of the season has happened.
DEFAULT_SEASON = 2026

#: One event per cell. 49 cells is already 49 events; the point of the design is
#: coverage of the corners of the board, not depth in any one of them.
DEFAULT_EVENTS_PER_STRATUM = 1

#: Fixed so a re-run draws the same events and re-uses the same cache rather
#: than paying again for a differently-shaped answer to the same question.
DEFAULT_SEED = 20260901

#: Deliberately below Cooper's 1.5M monthly authorisation by a wide margin, and
#: above the pessimistic bound of the default plan — 50,029 for 49 events at 51
#: keys across two regions — so the default run cannot be starved by its own
#: default. The dry run prints the exact bound; set the cap from that, not from
#: this.
DEFAULT_CREDIT_CAP = 55_000

#: How many completed seasons before the probed one the tier table is built
#: from. Two, not all of them: **29 schools change conference for 2026-27**, so
#: a seven-season pool tiers a team by conferences that no longer exist, and one
#: season can leave a team under `conferences.MINIMUM_GAMES` non-conference D-I
#: games and therefore UNPLACED. Two is the shortest window that is recent
#: enough to survive realignment and long enough to place nearly every team.
TIER_LOOKBACK_SEASONS = 2

#: Bumped whenever the record's shape changes, so a stale record fails loudly at
#: re-render rather than rendering a report with holes in it.
RECORD_SCHEMA_VERSION = 1

REPORT_STEM = "retention_probe"
PROBE_CACHE_DIRNAME = "historical_probe"

#: The last line of a dry run. CI greps for this phrase at the end of the line,
#: which is why there is no full stop after it.
NOTHING_WAS_SPENT = "no credit was spent"


class Retention(str, Enum):
    """What the archive holds for a market, at this probe's sample size."""

    #: Priced on at least `MEASURABLE_EVENT_SHARE` of the events fully asked,
    #: by at least `MEASURABLE_BOOK_FLOOR` books.
    RETAINED_AND_MEASURABLE = "RETAINED_AND_MEASURABLE"
    #: The archive has it, and this probe cannot show it has enough of it.
    RETAINED_BUT_THIN = "RETAINED_BUT_THIN"
    #: Every provider key of this market was asked on at least one event and no
    #: price came back for any of them.
    NOT_RETAINED = "NOT_RETAINED"
    #: **Not a retention verdict.** No event had all of this market's keys
    #: asked, so the run has nothing to say about it. This value exists so that
    #: a starved run cannot report its own starvation as market absence.
    NOT_PROBED = "NOT_PROBED"


class TipWindow(str, Enum):
    """When a game tips, in the sport's own calendar zone."""

    AFTERNOON = "afternoon"
    EARLY_EVENING = "early_evening"
    LATE = "late"


#: Cut points in Eastern hours, from the 2025-26 tip distribution: games run
#: 11:00 to 23:00 with a mode at 19:00. Below 08:00 is the Honolulu tail — a
#: 20:00 Hawaii tip is 01:00 Eastern the next morning, and it is a late game by
#: every meaning that matters here, not an early one.
EARLY_EVENING_FROM_HOUR = 17
LATE_FROM_HOUR = 21
DAY_STARTS_HOUR = 8

#: Tier strength order, for taking the higher of a game's two sides.
_TIER_RANK: dict[str, int] = {
    Tier.UNPLACED.value: 0,
    Tier.LOW_MAJOR.value: 1,
    Tier.MID_MAJOR.value: 2,
    Tier.HIGH_MAJOR.value: 3,
}


class ProbeError(RuntimeError):
    """The probe refused to run, or refused to trust what it had."""


# ---------------------------------------------------------------------------
# The sample
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProbeEvent:
    """One game the probe intends to ask about, and the cell it represents."""

    game_id: int
    season: int
    slate_date: str
    commence_time: str
    snapshot: str
    tier: str
    month: str
    window: str
    home_team_id: int
    away_team_id: int
    home_name: str
    away_name: str

    @property
    def stratum(self) -> str:
        return stratum_key(self.tier, self.month, self.window)

    def to_json(self) -> dict:
        return {
            "game_id": int(self.game_id),
            "season": int(self.season),
            "slate_date": self.slate_date,
            "commence_time": self.commence_time,
            "snapshot": self.snapshot,
            "tier": self.tier,
            "month": self.month,
            "window": self.window,
            "home_team_id": int(self.home_team_id),
            "away_team_id": int(self.away_team_id),
            "home_name": self.home_name,
            "away_name": self.away_name,
        }


def stratum_key(tier: str, month: str, window: str) -> str:
    """`high_major|2026-01|late`. One string so a cell can key a dict and a
    JSON object without three parallel lists drifting apart."""
    return f"{tier}|{month}|{window}"


def tip_window(commence_time: object, competition: Competition) -> str:
    """Which window a tip falls in, or `""` when it cannot be established.

    Empty, never a guess. A tip time with no zone on it cannot be converted, and
    inventing one moves a game by hours and therefore into the wrong cell — and
    a mis-stratified sample reports itself as balanced while being anything but.
    """
    text = str(commence_time or "").strip()
    if not slate_date_is_derived(text):
        return ""
    moment = datetime.fromisoformat(text.replace("Z", "+00:00"))
    hour = moment.astimezone(competition.timezone).hour
    if hour >= LATE_FROM_HOUR or hour < DAY_STARTS_HOUR:
        return TipWindow.LATE.value
    if hour >= EARLY_EVENING_FROM_HOUR:
        return TipWindow.EARLY_EVENING.value
    return TipWindow.AFTERNOON.value


def game_tier(home_team_id: object, away_team_id: object, tiers: TierTable) -> str:
    """The higher of the two sides' tiers.

    The board's attention follows the stronger programme: a low-major visiting a
    high-major is a televised high-major game and is priced like one. Taking the
    higher tier is therefore what makes the low-major stratum mean *both sides
    are low-major*, which is the end of the board this lab was built to look at.
    """
    home = tiers.tier_for(home_team_id).value
    away = tiers.tier_for(away_team_id).value
    return home if _TIER_RANK.get(home, 0) >= _TIER_RANK.get(away, 0) else away


def snapshot_for(commence_time: str, *, minutes_before: int) -> str:
    """The historical snapshot instant for a tip, in UTC ISO with a `Z`."""
    moment = datetime.fromisoformat(str(commence_time).replace("Z", "+00:00"))
    at = moment.astimezone(timezone.utc) - timedelta(minutes=int(minutes_before))
    return at.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def candidate_events(
    team_games: pd.DataFrame,
    schedule: pd.DataFrame,
    tiers: TierTable,
    *,
    competition: Competition = CBB,
    season: int = DEFAULT_SEASON,
    minutes_before_tip: int = SNAPSHOT_MINUTES_BEFORE_TIP,
) -> tuple[list[ProbeEvent], dict[str, int]]:
    """Every game this probe is allowed to draw from, and why the rest are not.

    The population comes from the processed table's **own** `game_state`, so the
    probe and the backtest can never disagree about which games count — the
    non-D-I buy-games are already excluded there, with the count stated. The
    schedule supplies the two things the processed table does not carry: the tip
    timestamp, and the school names the provider will spell its own way.

    Returns the candidates and a census of the exclusions. Nothing is silently
    dropped: a game that vanishes without appearing in that census is a defect.
    """
    census: dict[str, int] = {}

    def drop(reason: str, n: int = 1) -> None:
        census[reason] = census.get(reason, 0) + int(n)

    games = team_games[
        (team_games["season"] == int(season))
        & (team_games["game_state"] == P.GameState.COUNTABLE.value)
        & (team_games["home_away"] == "home")
    ]
    drop("countable_home_rows", len(games))

    columns = [
        "game_id",
        "date",
        "home_id",
        "away_id",
        "home_display_name",
        "away_display_name",
    ]
    present = [c for c in columns if c in schedule.columns]
    if "game_id" not in present or "date" not in present:
        raise ProbeError(
            "The schedule carries no `game_id`/`date` pair, so no tip time can "
            "be joined to a countable game. Refusing to sample: a probe that "
            "cannot place a game in a tip window cannot be stratified by one."
        )
    side = schedule[present].copy()
    side["game_id"] = pd.to_numeric(side["game_id"], errors="coerce")
    side = side.dropna(subset=["game_id"])
    side["game_id"] = side["game_id"].astype("int64")
    merged = games.merge(side, on="game_id", how="left", suffixes=("", "_sched"))

    events: list[ProbeEvent] = []
    for row in merged.to_dict("records"):
        commence = str(row.get("date") or "").strip()
        if not commence:
            drop("no_tip_time_in_schedule")
            continue
        window = tip_window(commence, competition)
        if not window:
            drop("tip_time_carried_no_timezone")
            continue
        slate = str(row.get("slate_date") or "").strip()
        if len(slate) < 7:
            drop("no_slate_date")
            continue
        home_id = row.get("home_id")
        away_id = row.get("away_id")
        if home_id is None or away_id is None or pd.isna(home_id) or pd.isna(away_id):
            drop("schedule_carried_no_team_ids")
            continue
        tier = game_tier(home_id, away_id, tiers)
        events.append(
            ProbeEvent(
                game_id=int(row["game_id"]),
                season=int(row["season"]),
                slate_date=slate,
                commence_time=commence,
                snapshot=snapshot_for(commence, minutes_before=minutes_before_tip),
                tier=tier,
                month=slate[:7],
                window=window,
                home_team_id=int(home_id),
                away_team_id=int(away_id),
                home_name=str(row.get("home_display_name") or ""),
                away_name=str(row.get("away_display_name") or ""),
            )
        )
    census["candidates"] = len(events)
    return events, census


@dataclass
class SamplePlan:
    """The events to ask about, and the honest shape of the draw."""

    events: tuple[ProbeEvent, ...]
    strata: tuple[dict, ...]
    seed: int
    events_per_stratum: int

    @property
    def balanced(self) -> bool:
        """True only when every non-empty cell got `events_per_stratum` events.

        Reported rather than assumed. An unbalanced probe that reports itself as
        balanced is worse than no probe, because every later conclusion inherits
        the imbalance and nobody can see it.

        A cell that simply does not hold enough games counts as short here too.
        That the shortfall was unavoidable is a **reason**, recorded per cell as
        `exhausted`, and it is not a reason to call the design balanced: the
        conclusions still rest on more evidence from some corners of the board
        than others.
        """
        return all(int(s["drawn"]) >= int(s["target"]) for s in self.strata)

    @property
    def underfilled(self) -> tuple[dict, ...]:
        return tuple(s for s in self.strata if int(s["drawn"]) < int(s["target"]))


def stratified_sample(
    candidates: Sequence[ProbeEvent],
    *,
    events_per_stratum: int = DEFAULT_EVENTS_PER_STRATUM,
    seed: int = DEFAULT_SEED,
    max_events: int = 0,
) -> SamplePlan:
    """Draw `events_per_stratum` from every non-empty (tier, month, window) cell.

    Deterministic: cells are visited in sorted order and each cell's members are
    sorted by game id before the draw, so the same seed reaches the same games
    and therefore the same cache files. A probe that re-drew on every run would
    pay again for a differently-shaped answer to the same question.

    `max_events` truncates the plan, and it truncates carefully: one pass across
    the cells before a second, and the cell order for that pass is drawn from
    the same seeded generator rather than being alphabetical. Alphabetical order
    starts at `high_major|2025-11|afternoon` and stays in the high-major
    November corner for eighteen cells, which is the exact corner of the board
    this probe exists to look away from. A truncated plan is still loudly
    unbalanced in the report: every cell it dropped keeps its target and shows a
    shortfall.
    """
    by_stratum: dict[str, list[ProbeEvent]] = {}
    for event in candidates:
        by_stratum.setdefault(event.stratum, []).append(event)

    rng = random.Random(int(seed))
    drawn: dict[str, list[ProbeEvent]] = {}
    for key in sorted(by_stratum):
        members = sorted(by_stratum[key], key=lambda e: e.game_id)
        take = min(int(events_per_stratum), len(members))
        drawn[key] = sorted(rng.sample(members, take), key=lambda e: e.game_id)

    chosen: list[ProbeEvent] = []
    if max_events and max_events > 0:
        order = sorted(drawn)
        rng.shuffle(order)
        for depth in range(int(events_per_stratum)):
            for key in order:
                if depth < len(drawn[key]) and len(chosen) < int(max_events):
                    chosen.append(drawn[key][depth])
    else:
        for key in sorted(drawn):
            chosen.extend(drawn[key])

    kept = {e.game_id for e in chosen}
    strata = []
    for key in sorted(by_stratum):
        tier, month, window = key.split("|")
        strata.append(
            {
                "stratum": key,
                "tier": tier,
                "month": month,
                "window": window,
                "population": len(by_stratum[key]),
                "target": int(events_per_stratum),
                "exhausted": len(by_stratum[key]) < int(events_per_stratum),
                "drawn": sum(1 for e in drawn[key] if e.game_id in kept),
            }
        )
    chosen.sort(key=lambda e: (e.commence_time, e.game_id))
    return SamplePlan(
        events=tuple(chosen),
        strata=tuple(strata),
        seed=int(seed),
        events_per_stratum=int(events_per_stratum),
    )


# ---------------------------------------------------------------------------
# The request plan and its cost
# ---------------------------------------------------------------------------


def probe_provider_keys(tiers: tuple[int, ...] = (1, 2, 3)) -> tuple[str, ...]:
    """Every wired provider key in the named tiers, sorted and deduplicated.

    Futures are absent by construction: they live under a different sport key
    and are not per-event, so asking for them here would return nothing and read
    as absence.
    """
    keys = {k for tier in tiers for k in M.provider_keys_in_tier(tier)}
    return tuple(sorted(keys))


def market_chunks(
    keys: Sequence[str], *, size: int = MARKET_CHUNK_SIZE
) -> tuple[tuple[str, ...], ...]:
    """Split the key list into request-sized chunks, deterministically."""
    ordered = tuple(sorted(set(str(k) for k in keys)))
    step = max(int(size), 1)
    return tuple(ordered[i : i + step] for i in range(0, len(ordered), step))


def cache_path(
    cache_dir: Path, event: ProbeEvent, chunk: Sequence[str]
) -> Path:
    """Where one chunk's raw response for one event is cached.

    **The filename carries the chunk's fingerprint, never its length.** The
    football lab's probe tagged these files with `len(chunk)`, so its four
    ten-market chunks all wrote the same name, collided, and three of the four
    answers were lost without a single error — the survivor was a perfectly
    valid response to a real request.
    """
    return (
        Path(cache_dir)
        / event.slate_date
        / f"{event.game_id}__{markets_fingerprint(tuple(chunk))}.json"
    )


def slate_cache_path(cache_dir: Path, snapshot: str) -> Path:
    """Where one snapshot's historical event listing is cached."""
    stamp = "".join(ch for ch in str(snapshot) if ch.isalnum())
    return Path(cache_dir) / "slates" / f"slate__{stamp}.json"


def pessimistic_bound(
    events: Sequence[ProbeEvent], keys: Sequence[str], *, regions: int
) -> int:
    """What the plan could cost if every asked market returned at every book.

    The direction to be wrong in. The NHL lab's purchase estimated from markets
    *asked* while the provider bills per market *returned*, was capped at 200,000
    and spent 289,984. This bound can only be too high, and the cap is separately
    enforced against the measured running total from `x-requests-last`.
    """
    snapshots = len({e.snapshot for e in events})
    listings = snapshots * HISTORICAL_EVENTS_LIST_COST
    odds = len(events) * len(set(keys)) * int(regions) * HISTORICAL_MULTIPLIER
    return int(listings + odds)


def guard_history_window(events: Sequence[ProbeEvent], keys: Sequence[str]) -> None:
    """Refuse to probe games older than the archive can answer for.

    Featured markets exist for this sport from 2020-11-16 and everything else
    from 2023-05-03, site-wide. A run that asks for `player_points` on a 2022
    game measures the archive's start date and would record it as market
    absence — the same shape of error as reporting starvation as absence, and
    just as invisible in the output.
    """
    if not events:
        return
    earliest = min(e.slate_date for e in events)
    beyond_featured = sorted(set(keys) - set(M.bulk_provider_keys()))
    floor = ADDITIONAL_HISTORY_FROM if beyond_featured else FEATURED_HISTORY_FROM
    if earliest < floor:
        raise ProbeError(
            f"The earliest sampled game is {earliest} and the archive only "
            f"holds these markets from {floor}. A market that could not exist "
            "in the archive would be recorded as a market the provider does "
            "not retain, which is the same defect as reporting a starved fetch "
            "as market absence. Probe a later season, or drop the "
            f"{len(beyond_featured)} non-featured keys."
        )


# ---------------------------------------------------------------------------
# Counting a response
# ---------------------------------------------------------------------------


@dataclass
class KeyObservation:
    """What one provider key returned on one event."""

    rows: int = 0
    books: set[str] = field(default_factory=set)


def count_payload(payload: Mapping) -> dict[str, KeyObservation]:
    """Rows and books per provider key in one historical event response.

    Counts outcomes, not markets: a ladder returning forty rungs at one book is
    forty rows and one book, and both numbers matter — rows say whether a market
    is rich enough to model, books say whether the price is takeable at more
    than one place.
    """
    seen: dict[str, KeyObservation] = {}
    bookmakers = payload.get("bookmakers") if isinstance(payload, Mapping) else None
    for bookmaker in bookmakers or []:
        if not isinstance(bookmaker, Mapping):
            continue
        book = str(bookmaker.get("key") or "").strip()
        for market in bookmaker.get("markets") or []:
            if not isinstance(market, Mapping):
                continue
            key = str(market.get("key") or "").strip()
            if not key:
                continue
            outcomes = market.get("outcomes") or []
            if not isinstance(outcomes, list) or not outcomes:
                # A market present with no outcomes is not a price. Counting it
                # would make an empty shell read as retention.
                continue
            observation = seen.setdefault(key, KeyObservation())
            observation.rows += len(outcomes)
            if book:
                observation.books.add(book)
    return seen


def match_provider_event(
    listing: Sequence[Mapping], event: ProbeEvent, index: team_names.TeamIndex
) -> tuple[str, str]:
    """The provider's id for one of our games, or `("", reason)`.

    `None`, never a guess — rule 2 of `providers/team_names.py`. An unmatched
    game is dropped from every denominator and counted separately, because
    scoring it as "no price" would turn a name this lab cannot spell into a
    market the provider does not retain.
    """
    among = {event.home_team_id, event.away_team_id}
    for candidate in listing:
        if not isinstance(candidate, Mapping):
            continue
        home = index.resolve(candidate.get("home_team"), among=among)
        away = index.resolve(candidate.get("away_team"), among=among)
        if home is None or away is None or home == away:
            continue
        if {int(home), int(away)} != {int(event.home_team_id), int(event.away_team_id)}:
            continue
        provider_id = str(candidate.get("id") or "").strip()
        if provider_id:
            return provider_id, ""
    return "", "no event in the snapshot's listing resolved to both of these teams"


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


@dataclass
class MarketRoll:
    """One market's retention, rolled up from every provider key that feeds it."""

    market: str
    title: str
    tier: int
    provider_keys: tuple[str, ...]
    #: Events where **every** one of this market's provider keys was asked. The
    #: only honest denominator: an event where half the keys went unasked can
    #: prove a market retained and can never prove one absent.
    fully_asked_events: set[int] = field(default_factory=set)
    #: Events where at least one key returned at least one row — including
    #: events that were only partly asked, because one price is one price.
    priced_events: set[int] = field(default_factory=set)
    #: Fully asked, and nothing came back for any key.
    absent_events: set[int] = field(default_factory=set)
    #: Partly asked, and nothing came back from the part that was asked. These
    #: prove nothing in either direction and are in no denominator.
    incomplete_events: set[int] = field(default_factory=set)
    books: set[str] = field(default_factory=set)
    rows: int = 0
    credits: float = 0.0
    priced_by_tier: dict[str, int] = field(default_factory=dict)
    asked_by_tier: dict[str, int] = field(default_factory=dict)

    @property
    def denominator(self) -> int:
        return len(self.fully_asked_events)

    @property
    def numerator(self) -> int:
        """Priced **among the fully asked**. A share needs both sides measured
        on the same set of events, and mixing a partial ask into the numerator
        while keeping it out of the denominator is how a starved run reports a
        share above one."""
        return len(self.priced_events & self.fully_asked_events)

    @property
    def priced_on_partial_ask(self) -> int:
        return len(self.priced_events - self.fully_asked_events)

    @property
    def share(self) -> float:
        return self.numerator / self.denominator if self.denominator else 0.0

    def verdict(self) -> Retention:
        if self.denominator == 0:
            if self.priced_events:
                # Positive evidence from a partial ask. Retention is established
                # and the share is not, so it cannot be called measurable.
                return Retention.RETAINED_BUT_THIN
            return Retention.NOT_PROBED
        if not self.priced_events:
            return Retention.NOT_RETAINED
        if (
            self.share >= MEASURABLE_EVENT_SHARE
            and len(self.books) >= MEASURABLE_BOOK_FLOOR
        ):
            return Retention.RETAINED_AND_MEASURABLE
        return Retention.RETAINED_BUT_THIN

    def to_json(self) -> dict:
        low, high = S.wilson_interval(self.numerator, self.denominator)
        return {
            "market": self.market,
            "title": self.title,
            "tier": int(self.tier),
            "provider_keys": list(self.provider_keys),
            "events_fully_asked": self.denominator,
            "events_priced": self.numerator,
            "events_absent": len(self.absent_events),
            "events_incomplete": len(self.incomplete_events),
            "events_priced_on_a_partial_ask": self.priced_on_partial_ask,
            "share": round(self.share, 4),
            "share_interval": [round(low, 4), round(high, 4)],
            "distinct_books": len(self.books),
            "books": sorted(self.books),
            "rows": int(self.rows),
            "credits_attributed": round(self.credits, 2),
            "priced_by_tier": {k: int(v) for k, v in sorted(self.priced_by_tier.items())},
            "asked_by_tier": {k: int(v) for k, v in sorted(self.asked_by_tier.items())},
            "verdict": self.verdict().value,
            "straddles_threshold": bool(
                self.denominator and low < MEASURABLE_EVENT_SHARE < high
            ),
        }


def roll_up_to_markets(
    observations: Mapping[int, Mapping[str, KeyObservation]],
    asked: Mapping[int, set[str]],
    *,
    event_tier: Mapping[int, str],
    credits_by_key: Mapping[str, float] | None = None,
    provider_keys: Sequence[str] = (),
) -> dict[str, MarketRoll]:
    """Per-key counts in, per-market verdicts out. **This is rule one.**

    `observations[game_id][provider_key]` is what came back; `asked[game_id]` is
    every key that was successfully requested for that game. The two are
    separate arguments on purpose: a key that returned nothing and a key that was
    never asked are different facts, and every defect this module guards against
    comes from treating them as one.

    A market is priced on an event when **any** of its keys returned a row —
    which is the football lab's finding turned into code. Its probe read three
    featured prop keys as dead across all twenty events while the matching
    alternate ladders carried the same market on the same events. Per key, three
    unmeasurable markets; per market, none.
    """
    wanted = set(provider_keys) if provider_keys else {
        k for keys in asked.values() for k in keys
    }
    rolls: dict[str, MarketRoll] = {}
    for market in M.MARKETS:
        if not set(market.provider_keys) & wanted:
            continue
        rolls[market.key] = MarketRoll(
            market=market.key,
            title=market.title,
            tier=market.tier,
            provider_keys=tuple(market.provider_keys),
        )

    per_key_credits = dict(credits_by_key or {})
    for game_id, asked_keys in sorted(asked.items()):
        seen = observations.get(game_id, {})
        tier = str(event_tier.get(game_id, Tier.UNPLACED.value))
        for roll in rolls.values():
            keys = [k for k in roll.provider_keys if k in wanted]
            if not keys:
                continue
            answered = [k for k in keys if k in asked_keys]
            if not answered:
                continue
            priced = [k for k in answered if seen.get(k) and seen[k].rows > 0]
            complete = len(answered) == len(keys)
            if complete:
                roll.fully_asked_events.add(game_id)
                roll.asked_by_tier[tier] = roll.asked_by_tier.get(tier, 0) + 1
            if priced:
                roll.priced_events.add(game_id)
                if complete:
                    roll.priced_by_tier[tier] = roll.priced_by_tier.get(tier, 0) + 1
                for key in priced:
                    roll.rows += seen[key].rows
                    roll.books |= seen[key].books
            elif complete:
                roll.absent_events.add(game_id)
            else:
                roll.incomplete_events.add(game_id)
    for roll in rolls.values():
        for key in roll.provider_keys:
            roll.credits += float(per_key_credits.get(key, 0.0))
        # An event can be in the numerator from a partial ask; it must not also
        # sit in the incomplete bucket, which is for events that proved nothing.
        roll.incomplete_events -= roll.priced_events
    return rolls


def probe(
    *,
    plan: SamplePlan,
    provider: OddsApiProvider,
    index: team_names.TeamIndex,
    provider_keys: Sequence[str],
    credit_cap: int,
    cache_dir: Path,
    competition: Competition = CBB,
    chunk_size: int = MARKET_CHUNK_SIZE,
    use_cache: bool = True,
    allow_partial: bool = False,
    generated_at: str = "",
) -> dict:
    """Ask the archive, count what comes back, and return the run record.

    The record is the artefact. Everything the report says is a function of it,
    so the wording can be improved forever without spending a credit twice.
    """
    keys = tuple(sorted(set(str(k) for k in provider_keys)))
    chunks = market_chunks(keys, size=chunk_size)
    regions = len([r for r in str(provider.regions).split(",") if r.strip()]) or 1
    bound = pessimistic_bound(plan.events, keys, regions=regions)
    if bound > int(credit_cap) and not allow_partial:
        raise ProbeError(
            f"This plan bounds at {bound:,} credits and the cap is "
            f"{int(credit_cap):,}. Refusing to start: a cap below the plan's "
            "pessimistic bound is a cap that starves it, and a starved fetch "
            "and an unquoted market look identical in the reports. Raise the "
            "cap, cut the plan with --max-events, or pass --allow-partial and "
            "read the report's own warning that it may have been truncated."
        )
    guard_history_window(plan.events, keys)

    spend = Spend()
    observations: dict[int, dict[str, KeyObservation]] = {}
    asked: dict[int, set[str]] = {}
    credits_by_key: dict[str, float] = {}
    unwired: dict[str, int] = {}
    per_event_records: list[dict] = []
    unmatched: list[dict] = []
    failures: list[dict] = []
    listings: dict[str, list[dict]] = {}
    served_from_cache = 0
    completed = True
    stopped_because = ""

    cache_root = Path(cache_dir)

    def _read_cache(path: Path):
        if not (use_cache and path.is_file()):
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            # A damaged cache file is not evidence of anything. Re-ask rather
            # than record its emptiness as an answer.
            return None

    def _write_cache(path: Path, payload) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", "utf-8")

    for event in plan.events:
        if not completed:
            break
        listing = listings.get(event.snapshot)
        if listing is None:
            path = slate_cache_path(cache_root, event.snapshot)
            cached = _read_cache(path)
            if cached is not None:
                listing = [x for x in cached if isinstance(x, dict)]
                served_from_cache += 1
            else:
                try:
                    listing = provider.list_historical_events(
                        event.snapshot, spend=spend, credit_cap=int(credit_cap)
                    )
                except CreditCapReached as exc:
                    completed = False
                    stopped_because = redact(str(exc))
                    break
                except ProviderError as exc:
                    failures.append(
                        {
                            "game_id": event.game_id,
                            "what": "historical event listing",
                            "snapshot": event.snapshot,
                            "error": redact(str(exc)),
                        }
                    )
                    listings[event.snapshot] = []
                    continue
                _write_cache(path, listing)
            listings[event.snapshot] = listing

        provider_event_id, reason = match_provider_event(listing, event, index)
        if not provider_event_id:
            unmatched.append(
                {
                    "game_id": event.game_id,
                    "slate_date": event.slate_date,
                    "home_name": event.home_name,
                    "away_name": event.away_name,
                    "tier": event.tier,
                    "reason": reason,
                }
            )
            continue

        asked.setdefault(event.game_id, set())
        observations.setdefault(event.game_id, {})
        event_rows = 0
        event_books: set[str] = set()
        for chunk in chunks:
            path = cache_path(cache_root, event, chunk)
            payload = _read_cache(path)
            charged = 0
            if payload is None:
                before = spend.credits_spent
                try:
                    payload = provider.historical_event_odds(
                        provider_event_id,
                        event.snapshot,
                        chunk,
                        spend=spend,
                        credit_cap=int(credit_cap),
                    )
                except CreditCapReached as exc:
                    completed = False
                    stopped_because = redact(str(exc))
                    break
                except ProviderError as exc:
                    failures.append(
                        {
                            "game_id": event.game_id,
                            "what": "historical event odds",
                            "markets_fingerprint": markets_fingerprint(chunk),
                            "keys": list(chunk),
                            "error": redact(str(exc)),
                        }
                    )
                    continue
                charged = spend.credits_spent - before
                _write_cache(path, payload)
            else:
                served_from_cache += 1
            asked[event.game_id] |= set(chunk)
            counted = count_payload(payload if isinstance(payload, Mapping) else {})
            returned_wired = []
            for key, observation in counted.items():
                if M.market_for_provider_key(key) is None:
                    unwired[key] = unwired.get(key, 0) + 1
                    continue
                returned_wired.append(key)
                existing = observations[event.game_id].setdefault(key, KeyObservation())
                existing.rows += observation.rows
                existing.books |= observation.books
                event_rows += observation.rows
                event_books |= observation.books
            # The provider bills `unique markets RETURNED x regions x 10`, so
            # dividing a request's measured cost across the keys it actually
            # returned is the billing rule read backwards rather than a guess.
            # A chunk that returned nothing cost nothing and is attributed
            # nothing. The report's total is always `spend.credits_spent`, never
            # the sum of these shares.
            if charged and counted:
                share = charged / len(counted)
                for key in counted:
                    credits_by_key[key] = credits_by_key.get(key, 0.0) + share

        per_event_records.append(
            {
                **event.to_json(),
                "provider_event_id": provider_event_id,
                "keys_asked": len(asked.get(event.game_id, ())),
                "rows": int(event_rows),
                "distinct_books": len(event_books),
                "books": sorted(event_books),
            }
        )

    event_tier = {e.game_id: e.tier for e in plan.events}
    rolls = roll_up_to_markets(
        observations,
        asked,
        event_tier=event_tier,
        credits_by_key=credits_by_key,
        provider_keys=keys,
    )

    return build_record(
        competition=competition,
        plan=plan,
        keys=keys,
        chunks=chunks,
        chunk_size=chunk_size,
        rolls=rolls,
        observations=observations,
        asked=asked,
        credits_by_key=credits_by_key,
        unwired=unwired,
        per_event_records=per_event_records,
        unmatched=unmatched,
        failures=failures,
        spend=spend,
        credit_cap=int(credit_cap),
        bound=bound,
        completed=completed,
        stopped_because=stopped_because,
        served_from_cache=served_from_cache,
        allow_partial=allow_partial,
        regions=provider.regions,
        sport_key=provider.sport_key,
        generated_at=generated_at,
        live=True,
    )


def build_record(
    *,
    competition: Competition,
    plan: SamplePlan,
    keys: Sequence[str],
    chunks: Sequence[Sequence[str]],
    chunk_size: int,
    rolls: Mapping[str, MarketRoll],
    observations: Mapping[int, Mapping[str, KeyObservation]],
    asked: Mapping[int, set[str]],
    credits_by_key: Mapping[str, float],
    unwired: Mapping[str, int],
    per_event_records: Sequence[Mapping],
    unmatched: Sequence[Mapping],
    failures: Sequence[Mapping],
    spend: Spend,
    credit_cap: int,
    bound: int,
    completed: bool,
    stopped_because: str,
    served_from_cache: int,
    allow_partial: bool,
    regions: str,
    sport_key: str,
    generated_at: str,
    live: bool,
) -> dict:
    """Everything the report will ever need, in one JSON-safe dictionary."""
    event_tier = {e.game_id: e.tier for e in plan.events}
    tiers_present = sorted({e.tier for e in plan.events})

    per_key = []
    for key in sorted(keys):
        market = M.market_for_provider_key(key)
        events_asked = sum(1 for keys_ in asked.values() if key in keys_)
        priced = [
            game_id
            for game_id, seen in observations.items()
            if seen.get(key) and seen[key].rows > 0
        ]
        books: set[str] = set()
        rows = 0
        for game_id in priced:
            books |= observations[game_id][key].books
            rows += observations[game_id][key].rows
        per_key.append(
            {
                "provider_key": key,
                "market": market.key if market else "",
                "events_asked": events_asked,
                "events_priced": len(priced),
                "rows": int(rows),
                "distinct_books": len(books),
                "credits_attributed": round(float(credits_by_key.get(key, 0.0)), 2),
            }
        )

    book_rows: dict[str, dict] = {}
    for game_id, seen in observations.items():
        tier = str(event_tier.get(game_id, Tier.UNPLACED.value))
        for key, observation in seen.items():
            for book in observation.books:
                entry = book_rows.setdefault(
                    book,
                    {"book": book, "events": set(), "by_tier": {}, "markets": set()},
                )
                entry["events"].add(game_id)
                entry["by_tier"].setdefault(tier, set()).add(game_id)
                market = M.market_for_provider_key(key)
                if market:
                    entry["markets"].add(market.key)

    probed_by_tier: dict[str, int] = {}
    for game_id in asked:
        tier = str(event_tier.get(game_id, Tier.UNPLACED.value))
        probed_by_tier[tier] = probed_by_tier.get(tier, 0) + 1

    books = []
    for book in sorted(book_rows):
        entry = book_rows[book]
        books.append(
            {
                "book": book,
                "events_priced": len(entry["events"]),
                "markets_quoted": len(entry["markets"]),
                "events_by_tier": {
                    tier: len(entry["by_tier"].get(tier, set()))
                    for tier in tiers_present
                },
            }
        )

    coverage = []
    for tier in tiers_present:
        games = [g for g in asked if event_tier.get(g) == tier]
        counts = []
        for game_id in games:
            seen = observations.get(game_id, {})
            counts.append(len({b for o in seen.values() for b in o.books}))
        series = pd.Series(counts, dtype="float64")
        markets_seen = {
            M.market_for_provider_key(k).key
            for g in games
            for k, o in observations.get(g, {}).items()
            if o.rows > 0 and M.market_for_provider_key(k)
        }
        coverage.append(
            {
                "tier": tier,
                "events_probed": len(games),
                "mean_books_per_event": round(float(series.mean()), 2)
                if len(series)
                else 0.0,
                "median_books_per_event": round(float(series.median()), 1)
                if len(series)
                else 0.0,
                "min_books_per_event": int(series.min()) if len(series) else 0,
                "max_books_per_event": int(series.max()) if len(series) else 0,
                "distinct_markets_priced": len(markets_seen),
            }
        )

    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "generated_at": str(generated_at),
        "competition": competition.key,
        "competition_title": competition.title,
        "sport_key": str(sport_key),
        "regions": str(regions),
        "season": int(plan.events[0].season) if plan.events else 0,
        "live": bool(live),
        "completed": bool(completed),
        "stopped_because": str(stopped_because),
        "allow_partial": bool(allow_partial),
        "credit_cap": int(credit_cap),
        "pessimistic_bound": int(bound),
        "credits_spent": int(spend.credits_spent),
        "credits_estimated": int(spend.credits_estimated),
        "requests_made": int(spend.requests_made),
        "responses_served_from_cache": int(served_from_cache),
        "quota_remaining": str(spend.quota_remaining),
        "spend_notes": list(spend.notes),
        "request_failures": [dict(f) for f in failures],
        "thresholds": {
            "measurable_event_share": MEASURABLE_EVENT_SHARE,
            "measurable_book_floor": MEASURABLE_BOOK_FLOOR,
            "minimum_bets": S.MINIMUM_BETS,
            "snapshot_minutes_before_tip": int(SNAPSHOT_MINUTES_BEFORE_TIP),
        },
        "plan": {
            "seed": plan.seed,
            "events_per_stratum": plan.events_per_stratum,
            "strata_non_empty": len(plan.strata),
            "events_planned": len(plan.events),
            "events_probed": len(asked),
            "balanced": plan.balanced,
            "chunk_size": int(chunk_size),
            "chunks": len(chunks),
            "provider_keys": list(keys),
        },
        "strata": [dict(s) for s in plan.strata],
        "events": [dict(e) for e in per_event_records],
        "unmatched_events": [dict(u) for u in unmatched],
        "probed_by_tier": {k: int(v) for k, v in sorted(probed_by_tier.items())},
        "markets": [rolls[k].to_json() for k in sorted(rolls, key=lambda x: (rolls[x].tier, x))],
        "provider_keys_detail": per_key,
        "unwired_provider_keys": {k: int(v) for k, v in sorted(unwired.items())},
        "books": books,
        "book_coverage_by_tier": coverage,
    }


def dry_run_record(
    *,
    competition: Competition,
    plan: SamplePlan,
    keys: Sequence[str],
    chunk_size: int,
    credit_cap: int,
    regions: str,
    sport_key: str,
    generated_at: str = "",
) -> dict:
    """The same record shape with nothing measured in it. Spends nothing."""
    chunks = market_chunks(keys, size=chunk_size)
    region_count = len([r for r in str(regions).split(",") if r.strip()]) or 1
    bound = pessimistic_bound(plan.events, keys, regions=region_count)
    return build_record(
        competition=competition,
        plan=plan,
        keys=tuple(sorted(set(keys))),
        chunks=chunks,
        chunk_size=chunk_size,
        rolls=roll_up_to_markets({}, {}, event_tier={}, provider_keys=keys),
        observations={},
        asked={},
        credits_by_key={},
        unwired={},
        per_event_records=[],
        unmatched=[],
        failures=[],
        spend=Spend(),
        credit_cap=int(credit_cap),
        bound=bound,
        completed=False,
        stopped_because="This was a dry run. Nothing was requested.",
        served_from_cache=0,
        allow_partial=False,
        regions=regions,
        sport_key=sport_key,
        generated_at=generated_at,
        live=False,
    )


# ---------------------------------------------------------------------------
# The report — a pure function of the record
# ---------------------------------------------------------------------------


def _pct(value: float) -> str:
    return f"{100.0 * float(value):.1f}%"


def _by_strength(tiers: Iterable[str]) -> list[str]:
    """High-major first, then mid, then low, then unplaced.

    Alphabetical order puts low-major between high and mid, which reads as
    noise. This lab's whole thesis is a gradient down that axis, and a table
    whose columns are out of order hides the gradient it exists to show.
    """
    return sorted(set(tiers), key=lambda t: (-_TIER_RANK.get(t, 0), t))


def _share_cell(entry: Mapping) -> str:
    """A share is never printed without its denominator and its interval."""
    n = int(entry["events_fully_asked"])
    if not n:
        return "— (0 events)"
    low, high = entry["share_interval"]
    return (
        f"{int(entry['events_priced'])}/{n} = {_pct(entry['share'])} "
        f"[{_pct(low)}, {_pct(high)}]"
    )


#: The one place in the report where the words a market must never be described
#: with are allowed to appear — because it is the sentence saying they do not
#: apply. `tests/test_retention_probe.py` excises this exact string before
#: checking that nothing else in the report calls an unquoted market a fade, an
#: avoid or a no-value call.
NOT_A_BET_DISCLAIMER = (
    "A market the archive returned nothing for is stated as exactly that. "
    "It is not a fade, not an avoid, and not a no-value call: this probe never "
    "priced a bet, so it has no opinion about one. And `NOT_PROBED` is not a "
    "retention verdict at all — it is this module refusing to let an unasked "
    "market be read as an empty one."
)

VERDICT_PROSE = {
    Retention.RETAINED_AND_MEASURABLE.value: (
        "the archive has it on at least half the events asked, at two or more "
        "books"
    ),
    Retention.RETAINED_BUT_THIN.value: (
        "the archive has it, and this probe cannot show it has enough of it"
    ),
    Retention.NOT_RETAINED.value: (
        "every provider key for it was asked and the archive returned no price"
    ),
    Retention.NOT_PROBED.value: (
        "this run never asked for it, so it has nothing to say either way"
    ),
}


def render(record: Mapping) -> str:
    """The markdown report, computed only from the run record.

    No clock, no network, no randomness: the same record renders to the same
    bytes forever. That is what makes it safe to improve this wording, which is
    the football lab's second hard-won rule — its probe cost 7,280 credits and
    re-running it to fix a sentence would have cost that again.
    """
    version = int(record.get("schema_version", 0))
    if version != RECORD_SCHEMA_VERSION:
        raise ProbeError(
            f"This run record is schema version {version} and this renderer "
            f"speaks version {RECORD_SCHEMA_VERSION}. Refusing to render: a "
            "report with silently missing sections is worse than no report."
        )

    out: list[str] = []
    add = out.append
    title = record.get("competition_title", "")
    add(f"# Historical retention probe — {title}")
    add("")
    add(
        "Two questions, kept apart: **which markets the archive still has "
        "prices for**, and **which of them it has enough of to measure "
        "against**. A market can be retained and unmeasurable, and buying a "
        "season of prices for one is how a lab spends credits on rows no "
        "conclusion will ever rest on."
    )
    add("")
    add(
        "Generated by `scripts/run_retention_probe.py` and re-rendered by "
        "`scripts/rerender_retention_probe.py` from "
        f"`{record['competition']}_{REPORT_STEM}.json`. **The report is a pure "
        "function of that record**, so this wording can be improved without "
        "spending a credit twice."
    )
    add("")

    # -- the honesty block ---------------------------------------------------
    completed = bool(record.get("completed"))
    live = bool(record.get("live"))
    add("## What this run was, and what it cost")
    add("")
    add("| | |")
    add("|---|---|")
    add(f"| Generated | {record.get('generated_at') or 'unrecorded'} |")
    add(f"| Sport key | `{record.get('sport_key','')}` |")
    add(f"| Regions | `{record.get('regions','')}` |")
    add(f"| Season probed | {record.get('season', 0)} |")
    add(f"| Snapshot | {record['thresholds']['snapshot_minutes_before_tip']} minutes before tip |")
    add(f"| Credit cap | **{int(record.get('credit_cap', 0)):,}** |")
    add(f"| Pessimistic bound of the plan | {int(record.get('pessimistic_bound', 0)):,} |")
    add(f"| Credits actually spent | **{int(record.get('credits_spent', 0)):,}** |")
    add(f"| Requests made | {int(record.get('requests_made', 0)):,} |")
    add(
        f"| Responses served from cache | "
        f"{int(record.get('responses_served_from_cache', 0)):,} |"
    )
    add(f"| Quota remaining afterwards | {record.get('quota_remaining') or 'unrecorded'} |")
    add(f"| Run completed | **{'yes' if completed else 'no'}** |")
    add("")
    if not live:
        add(
            "**This record is a dry run.** No request was made, no credential "
            "was read and nothing was measured. Every market below reads "
            "`NOT_PROBED`, which is the correct answer for a run that asked "
            "nothing — and is deliberately not one of the three retention "
            "verdicts."
        )
        add("")
    elif not completed:
        add(
            "> **This run did not complete.** "
            f"{record.get('stopped_because') or 'It stopped early.'} Every "
            "market it never finished asking about reads `NOT_PROBED` rather "
            "than `NOT_RETAINED`, because **a starved fetch and an unquoted "
            "market look identical** and the NHL lab's probe once reported its "
            "own starvation as market absence. Nothing below may be read as "
            "the archive being empty of a market this run did not reach."
        )
        add("")
    else:
        add(
            "The run completed inside its cap, so a `NOT_RETAINED` verdict "
            "below is a fact about the archive rather than a fact about the "
            "budget. **A starved fetch and an unquoted market look identical**, "
            "which is why the cap, the bound and the measured spend are all "
            "printed above rather than summarised."
        )
        add("")
    if record.get("spend_notes"):
        for note in record["spend_notes"]:
            add(f"- {note}")
        add("")
    if record.get("request_failures"):
        add(
            f"**{len(record['request_failures'])} request(s) failed** and their "
            "keys are counted as unasked, never as unpriced:"
        )
        for failure in record["request_failures"][:20]:
            add(
                f"- game {failure.get('game_id','')}: {failure.get('what','')} — "
                f"{failure.get('error','')}"
            )
        add("")

    # -- stratification ------------------------------------------------------
    plan = record.get("plan", {})
    strata = list(record.get("strata", []))
    add("## The achieved stratification")
    add("")
    add(
        "The stratification is the point. This lab's thesis is that the "
        "low-major end of the board is priced with less attention, so a sample "
        "that is merely *representative* answers a question about the average "
        "game — and the average game is a mid-major January evening. The draw "
        "crosses **conference tier** (the thesis axis), **month of the "
        "season**, and **tip window**, and a game's tier is the higher of its "
        "two sides', so a low-major cell means both sides are low-major."
    )
    add("")
    balanced = bool(plan.get("balanced"))
    underfilled = [s for s in strata if int(s["drawn"]) < int(s["target"])]
    exhausted = [s for s in underfilled if s.get("exhausted")]
    if balanced:
        add(
            f"**Balanced: every one of the {len(strata)} non-empty cells got "
            f"its full target of {plan.get('events_per_stratum', 0)}.**"
        )
    else:
        add(
            f"**NOT balanced: {len(underfilled)} of {len(strata)} non-empty "
            "cells came up short.** They are marked below. An unbalanced probe "
            "that reports itself as balanced is worse than no probe, because "
            "every later conclusion inherits the imbalance and nobody can see "
            "it."
        )
        if exhausted:
            add("")
            add(
                f"{len(exhausted)} of those cells simply do not hold "
                f"{plan.get('events_per_stratum', 0)} games. That is the "
                "reason, and it is not a reason to call the design balanced: "
                "the conclusions still rest on more evidence from some corners "
                "of the board than others."
            )
    add("")
    add("| Tier | Month | Tip window | Population | Target | Drawn | Probed |")
    add("|---|---|---|---:|---:|---:|---:|")
    probed_ids = {int(e["game_id"]) for e in record.get("events", [])}
    by_stratum_probed: dict[str, int] = {}
    for event in record.get("events", []):
        key = stratum_key(event["tier"], event["month"], event["window"])
        by_stratum_probed[key] = by_stratum_probed.get(key, 0) + 1
    strata = sorted(
        strata,
        key=lambda s: (
            -_TIER_RANK.get(str(s.get("tier", "")), 0),
            str(s.get("month", "")),
            str(s.get("window", "")),
        ),
    )
    for stratum in strata:
        if int(stratum["drawn"]) >= int(stratum["target"]):
            flag = ""
        elif stratum.get("exhausted"):
            flag = " ⚠ (the cell holds no more)"
        else:
            flag = " ⚠"
        add(
            f"| {stratum['tier']} | {stratum['month']} | {stratum['window']} | "
            f"{int(stratum['population']):,} | {int(stratum['target'])} | "
            f"{int(stratum['drawn'])}{flag} | "
            f"{by_stratum_probed.get(stratum['stratum'], 0)} |"
        )
    add("")
    add(
        f"{int(plan.get('events_planned', 0))} events planned, "
        f"{int(plan.get('events_probed', 0))} actually asked about, "
        f"{len(probed_ids)} matched to a provider event."
    )
    add("")
    if record.get("unmatched_events"):
        add(
            f"**{len(record['unmatched_events'])} sampled game(s) could not be "
            "matched to a provider event and are in no denominator anywhere.** "
            "A school this lab cannot spell is not a market the provider does "
            "not retain, and scoring it as a missing price would quietly turn "
            "one into the other."
        )
        add("")
        add("| Game | Date | Tier | Why |")
        add("|---|---|---|---|")
        for miss in record["unmatched_events"][:25]:
            add(
                f"| {miss.get('away_name','')} at {miss.get('home_name','')} | "
                f"{miss.get('slate_date','')} | {miss.get('tier','')} | "
                f"{miss.get('reason','')} |"
            )
        add("")
    if record.get("probed_by_tier"):
        parts = ", ".join(
            f"{tier}: {record['probed_by_tier'][tier]}"
            for tier in _by_strength(record["probed_by_tier"])
        )
        add(f"Events asked about, by conference tier — {parts}.")
        add("")

    # -- retention by market -------------------------------------------------
    add("## Retention, by market")
    add("")
    add(
        "**Rolled up to the market, never to the provider key.** The football "
        "lab's probe found three featured prop keys returning nothing across "
        "all twenty of its probed events while their alternate ladders carried "
        "the same market on the same events: read per key that is three "
        "unmeasurable markets, read per market — the unit that gets modelled, "
        "measured, approved and carded — it is none. The per-key counts are "
        "further down, under a heading that says they are not a verdict."
    )
    add("")
    thresholds = record.get("thresholds", {})
    add(
        "**Measurable, declared in advance:** priced on at least "
        f"{_pct(thresholds.get('measurable_event_share', MEASURABLE_EVENT_SHARE))} "
        "of the events where every one of the market's provider keys was asked, "
        f"at {int(thresholds.get('measurable_book_floor', MEASURABLE_BOOK_FLOOR))} "
        "or more distinct books. The share is reported with its denominator and "
        "a 95% Wilson interval, because a probe this size cannot resolve a "
        "finer line than *more than half* — a market seen on 25 of 49 events "
        "has an interval spanning roughly 37% to 64%."
    )
    add("")
    add(
        "| Market | Tier | Priced on | Books | Rows | Credits | Verdict |"
    )
    add("|---|---:|---|---:|---:|---:|---|")
    for entry in record.get("markets", []):
        flag = " ⚠" if entry.get("straddles_threshold") else ""
        add(
            f"| `{entry['market']}` | {entry['tier']} | {_share_cell(entry)}{flag} | "
            f"{int(entry['distinct_books'])} | {int(entry['rows']):,} | "
            f"{float(entry['credits_attributed']):,.0f} | "
            f"**{entry['verdict']}** |"
        )
    add("")
    if any(e.get("straddles_threshold") for e in record.get("markets", [])):
        add(
            "⚠ marks a market whose Wilson interval straddles the "
            "measurability threshold: at this sample size the probe cannot "
            "separate it from the line, and it is classified on the "
            "conservative side because ambiguity falls on the not-a-play side."
        )
        add("")
    for value, prose in VERDICT_PROSE.items():
        count = sum(1 for e in record.get("markets", []) if e["verdict"] == value)
        add(f"- **{value}** ({count}) — {prose}.")
    add("")
    add(NOT_A_BET_DISCLAIMER)
    add("")
    partial = [
        e
        for e in record.get("markets", [])
        if int(e["events_incomplete"]) or int(e.get("events_priced_on_a_partial_ask", 0))
    ]
    if partial:
        add(
            "These markets had events where some of their provider keys were "
            "asked and others were not — the shape a run leaves behind when it "
            "stops. A partly-asked event can prove a market retained and can "
            "never prove one absent, so it is in the numerator when it carried "
            "a price and in no denominator either way:"
        )
        add("")
        for entry in partial:
            add(
                f"- `{entry['market']}`: "
                f"{int(entry['events_incomplete'])} partly-asked event(s) that "
                "proved nothing, "
                f"{int(entry.get('events_priced_on_a_partial_ask', 0))} that "
                "carried a price."
            )
        add("")

    # -- retention by tier ---------------------------------------------------
    tiers = _by_strength(record.get("probed_by_tier", {}))
    if tiers:
        add("### Retention by conference tier")
        add("")
        add(
            "The thesis axis. Each cell is *events priced / events where every "
            "key of the market was asked*, within that tier."
        )
        add("")
        add("| Market | " + " | ".join(tiers) + " |")
        add("|---|" + "|".join(["---"] * len(tiers)) + "|")
        for entry in record.get("markets", []):
            cells = []
            for tier in tiers:
                asked_n = int(entry.get("asked_by_tier", {}).get(tier, 0))
                priced_n = int(entry.get("priced_by_tier", {}).get(tier, 0))
                cells.append(f"{priced_n}/{asked_n}" if asked_n else "—")
            add(f"| `{entry['market']}` | " + " | ".join(cells) + " |")
        add("")

    # -- books ---------------------------------------------------------------
    add("## Which books appear, and where")
    add("")
    add(
        "**This is the most decision-relevant number the probe can produce for "
        "this lab.** A market quoted at six books on a high-major Saturday and "
        "one book on a low-major Tuesday is not one market: "
        "`stores.best_price_per_wager` collapses every book's quote on a wager "
        "to the best one, so the number of books is the width of the bracket "
        "between the pessimistic and optimistic measurement — and at one book "
        "there is no bracket left."
    )
    add("")
    coverage = sorted(
        record.get("book_coverage_by_tier", []),
        key=lambda c: -_TIER_RANK.get(str(c.get("tier", "")), 0),
    )
    if coverage:
        add(
            "| Tier | Events probed | Mean books/event | Median | Min | Max | "
            "Distinct markets priced |"
        )
        add("|---|---:|---:|---:|---:|---:|---:|")
        for entry in coverage:
            add(
                f"| {entry['tier']} | {int(entry['events_probed'])} | "
                f"{float(entry['mean_books_per_event']):.2f} | "
                f"{float(entry['median_books_per_event']):.1f} | "
                f"{int(entry['min_books_per_event'])} | "
                f"{int(entry['max_books_per_event'])} | "
                f"{int(entry['distinct_markets_priced'])} |"
            )
        add("")
        measured = [c for c in coverage if int(c["events_probed"])]
        if len(measured) >= 2:
            richest = max(measured, key=lambda c: float(c["mean_books_per_event"]))
            thinnest = min(measured, key=lambda c: float(c["mean_books_per_event"]))
            if richest is not thinnest:
                ratio = float(thinnest["mean_books_per_event"]) and (
                    float(richest["mean_books_per_event"])
                    / float(thinnest["mean_books_per_event"])
                )
                add(
                    f"**{richest['tier']} games carry "
                    f"{float(richest['mean_books_per_event']):.2f} distinct "
                    f"books per event over {int(richest['events_probed'])} "
                    f"events, {thinnest['tier']} games "
                    f"{float(thinnest['mean_books_per_event']):.2f} over "
                    f"{int(thinnest['events_probed'])}"
                    + (f" — {ratio:.1f} to 1.**" if ratio else ".**")
                )
                add("")
                add(
                    "That gap is the thesis in one number, and it is also the "
                    "warning beside it: fewer books is a wider spread and a "
                    "narrower best-price bracket, so an edge measured where the "
                    "board is thin is the hardest kind to take. It is measured "
                    "on one event per (tier, month, tip window) cell, which is "
                    "the sample size printed in the column beside it and not a "
                    "season."
                )
                add("")
    books = record.get("books", [])
    if books:
        tier_columns = sorted({t for b in books for t in b.get("events_by_tier", {})})
        header = "| Book | Events priced | Markets quoted |"
        divider = "|---|---:|---:|"
        for tier in tier_columns:
            header += f" {tier} |"
            divider += "---:|"
        add(header)
        add(divider)
        for entry in sorted(books, key=lambda b: (-int(b["events_priced"]), b["book"])):
            row = (
                f"| `{entry['book']}` | {int(entry['events_priced'])} | "
                f"{int(entry['markets_quoted'])} |"
            )
            for tier in tier_columns:
                counts = entry.get("events_by_tier", {})
                probed = int(record.get("probed_by_tier", {}).get(tier, 0))
                row += f" {int(counts.get(tier, 0))}/{probed} |"
            add(row)
        add("")
    else:
        add("No book quoted anything in this run.")
        add("")

    # -- per key, explicitly not a verdict -----------------------------------
    add("## Per provider key — detail, not a verdict")
    add("")
    add(
        "Kept because it is how a dead key gets noticed and fixed, and printed "
        "under this heading because reading it as a retention table is exactly "
        "the mistake that cost the football lab three markets. **Nothing here "
        "is a conclusion.** The conclusions are in the table above, one per "
        "market."
    )
    add("")
    add("| Provider key | Market | Asked on | Priced on | Rows | Books | Credits |")
    add("|---|---|---:|---:|---:|---:|---:|")
    for entry in record.get("provider_keys_detail", []):
        add(
            f"| `{entry['provider_key']}` | `{entry['market'] or '—'}` | "
            f"{int(entry['events_asked'])} | {int(entry['events_priced'])} | "
            f"{int(entry['rows']):,} | {int(entry['distinct_books'])} | "
            f"{float(entry['credits_attributed']):,.0f} |"
        )
    add("")
    dead_but_alive = []
    verdicts = {e["market"]: e["verdict"] for e in record.get("markets", [])}
    for entry in record.get("provider_keys_detail", []):
        if (
            entry["market"]
            and int(entry["events_asked"])
            and not int(entry["events_priced"])
            and verdicts.get(entry["market"], "").startswith("RETAINED")
        ):
            dead_but_alive.append(entry)
    if dead_but_alive:
        add(
            f"**{len(dead_but_alive)} provider key(s) returned nothing while "
            "their market is retained through another key.** This is the "
            "football lab's finding reproducing itself; per key they read as "
            "dead markets, per market they are not:"
        )
        add("")
        for entry in dead_but_alive:
            add(
                f"- `{entry['provider_key']}` — nothing on "
                f"{int(entry['events_asked'])} event(s), but "
                f"`{entry['market']}` is **{verdicts[entry['market']]}**."
            )
        add("")
    if record.get("unwired_provider_keys"):
        add(
            "The archive also returned keys this lab has no wiring for. That is "
            "data about the provider rather than an error, and it is counted "
            "rather than dropped:"
        )
        add("")
        for key, count in sorted(record["unwired_provider_keys"].items()):
            add(f"- `{key}` on {count} response(s).")
        add("")

    # -- limits --------------------------------------------------------------
    add("## What this does not establish")
    add("")
    add(
        f"- **Retention is not permission to card.** Nothing in this lab "
        "reaches `Availability.CONFIRMED` — ESPN's men's college basketball "
        "injuries endpoint is permanently empty and conference reports cover "
        "about 115 of 365 teams, conference games only. Player props are "
        "priced, frozen and settled and still **cannot be selected**, so a "
        "tier-3 market reading RETAINED_AND_MEASURABLE here is measurable and "
        "not playable."
    )
    add(
        f"- **One snapshot per event**, "
        f"{int(record['thresholds']['snapshot_minutes_before_tip'])} minutes "
        "before tip. A market hung only at open, or only in-play, is invisible "
        "to this run and its absence here means nothing about it."
    )
    add(
        f"- **The archive's own start dates bound this.** Featured markets "
        f"exist for this sport from {FEATURED_HISTORY_FROM} and everything else "
        f"from {ADDITIONAL_HISTORY_FROM}, so the full catalogue is buyable for "
        "three seasons only. `guard_history_window` refuses a sample that would "
        "measure the archive's start date and record it as market absence."
    )
    add(
        f"- **Every share carries its denominator.** A market priced on 3 of 3 "
        "events is not the same claim as one priced on 30 of 30, and the "
        "Wilson interval beside each share is what says so."
    )
    add(
        f"- **{S.MINIMUM_BETS} settled bets is the floor for any measurement in "
        "this lab.** Retention here is a necessary condition for reaching it, "
        "never a sufficient one."
    )
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Reading and writing the record
# ---------------------------------------------------------------------------


def record_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPORT_STEM, ".json")


def report_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPORT_STEM, ".md")


def write_record(record: Mapping, path: Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return target


def read_record(path: Path) -> dict:
    target = Path(path)
    if not target.is_file():
        raise ProbeError(
            f"No run record at {target}. The report is re-rendered from the "
            "record and never from the provider, so without it there is "
            "nothing to render — run `scripts/run_retention_probe.py --live` "
            "first, or point --record at a record that exists."
        )
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProbeError(
            f"The run record at {target} could not be read. Refusing to render "
            "a partial report over a good one."
        ) from exc
    if not isinstance(record, dict):
        raise ProbeError(f"The run record at {target} is not a JSON object.")
    return record


def write_report(record: Mapping, path: Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(record), encoding="utf-8")
    return target


def cache_dir_for(competition: Competition, raw_dir: Path) -> Path:
    return Path(raw_dir) / competition.data_dir_segment / PROBE_CACHE_DIRNAME


def load_inputs(
    *,
    processed_dir: Path,
    raw_dir: Path,
    competition: Competition = CBB,
    season: int = DEFAULT_SEASON,
    tier_seasons: tuple[int, ...] = (),
) -> tuple[pd.DataFrame, pd.DataFrame, TierTable, team_names.TeamIndex]:
    """The processed table, the season's schedule, the tiers, and the name index.

    Tiers come from seasons **strictly before** the one being probed, like
    everything else in this lab. A team's tier when a November 2025 game was
    priced is what its 2024-25 non-conference record said, and using the season
    under probe would leak its own result into the stratum it lands in.
    """
    from cbb_betting_lab.conferences import tier_table

    games_path = Path(processed_dir) / "cbb_team_games.csv"
    if not games_path.is_file():
        raise ProbeError(
            f"No processed table at {games_path}. Run "
            "`scripts/build_datasets.py` first: the probe draws its population "
            "from the same `game_state` the backtest does, so the two can never "
            "disagree about which games count."
        )
    team_games = pd.read_csv(games_path)

    schedule_dir = Path(raw_dir) / competition.data_dir_segment / "schedules"
    schedules: dict[int, pd.DataFrame] = {}
    for path in sorted(schedule_dir.glob("mbb_schedule_*.parquet")):
        try:
            schedules[int(path.stem.rsplit("_", 1)[-1])] = pd.read_parquet(path)
        except (OSError, ValueError):
            continue
    if int(season) not in schedules:
        raise ProbeError(
            f"No cached schedule for season {season} under {schedule_dir}. "
            "Run `scripts/fetch_cbb_data.py` first."
        )
    earlier = tuple(s for s in sorted(schedules) if s < int(season))
    prior = tier_seasons or earlier[-TIER_LOOKBACK_SEASONS:]
    if not prior:
        raise ProbeError(
            f"No season before {season} is cached, so no walk-forward tier "
            "table can be built. Tiering off the season under probe would leak "
            "its own result into the stratum every game lands in."
        )
    tiers = tier_table(schedules, prior)
    index = team_names.build_index(schedules[int(season)])
    return team_games, schedules[int(season)], tiers, index
