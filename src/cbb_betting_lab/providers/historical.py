"""Buying historical prices, in priority order, in an order whose every prefix
is a sample rather than a prefix.

The pessimistic full-catalogue buy is **17.6M credits against a 4,992,714
quota**, so this purchase cannot be run to completion in one month and was never
going to be. It is bought in Cooper's stated priority order — core team markets
across every season first, then ladders and halves, then props, then futures —
and it is resumable across months, because the thing that stops a run is a
credit cap and the thing that resumes it is a cache.

Everything below exists because a sibling lab paid for it.

## 1. A partial purchase is a SAMPLE, not a prefix

This is the rule this module is really about, and it is the one with no
precedent in the sibling labs — none of them ever had a purchase too big to
finish.

If events are bought in tip order, or in game-id order, or in the order the
schedule happens to list them, then a run that stops at 40% of a wave has bought
**November**, or **the East coast**, or **whatever the feed sorts first**. Book
coverage differs by season, by conference tier and by tip window — those are
three separate mechanisms, not one — so a prefix that is concentrated in any of
them measures the concentration rather than the board. And this lab's whole
thesis is about the low-major end, which is exactly the end a naive order
starves: low-major games tip late, cluster in the conference-play months, and
sort last under almost every alphabetical key.

So :func:`stratified_order` assigns each event a position of `(i + 0.5) / n_c`
within its own `(tier, month, tip window)` cell and sorts on that. Every prefix
of length `k` then holds `k · n_c / N` events from cell `c`, to within one event
— by construction, not by luck. Whatever the cap stops after is a proportionally
stratified sample of the wave, and :func:`achieved_stratification` measures and
prints how close it actually landed rather than asserting it.

The retention probe stratifies *equally* per cell, because it is looking for
the corners of the board. This stratifies *proportionally*, because the bought
prices become a population that gets modelled and measured, and a population
that over-weights a rare corner would need re-weighting at every later step.
Both report their achieved shape; neither assumes it.

## 2. The cap is enforced against the MEASURED running total

The NHL lab capped a purchase at 200,000 and spent **289,984**, while its code
and its test both asserted the cap "cannot be breached". It estimated from the
markets it *asked* for; the provider bills per market **returned**, and every
alternate ladder bills on its own.

What this module actually guarantees, stated as narrowly as it is true:

* before every request, `spend.credits_spent` (measured, from
  `x-requests-last`) plus that one request's pessimistic bound is checked
  against the cap — that is `odds_api._guard`;
* **after** every response, the measured running total is checked against the
  cap again, and a run that has crossed it stops immediately rather than
  continuing to the next event.

The second check is not redundant. A response can bill more than the request's
pessimistic bound if the provider returns market keys that were not asked for,
and the probe has already observed unwired keys coming back. When that happens
the run stops and :func:`render` prints the overshoot in credits. It does not
say the cap cannot be breached, because that is the sentence the NHL lab's test
contained.

## 3. Every cached response is named by the chunk's FINGERPRINT

The football lab tagged each cached chunk response with the chunk's *length*, so
four ten-market chunks all wrote `..._10.json`, collided, and three of four
answers were lost — silently, because the survivor was a valid response to a
real request. The length of a list is not its identity;
:func:`~cbb_betting_lab.providers.odds_api.markets_fingerprint` is.

The cache is also the resume state. A re-run walks the same plan in the same
order and skips every `(event, chunk)` whose response is already on disk, so it
costs nothing to re-run and the run that gets furthest is the union of every run
so far.

## 4. Buy once, stage from the cache

The raw response is written to disk **before** anything is normalised, and
:func:`stage_event` is a pure function of a cached payload. So the mapping from
the provider's vocabulary into this lab's can be fixed, extended and re-run for
ever without spending a credit twice — `--rebuild-store` does exactly that with
no network at all. It is the retention probe's "the report is a pure function of
the record" rule applied to prices instead of prose, and it matters more here
because prices cost ten times live rate.

## 5. One window per store, and the lead time is on every row

A snapshot 60 minutes before tip and a snapshot 10 minutes before tip are two
different measurements. `stores.best_price_per_wager` collapses every book's
quote on a wager to the best one, so a store holding both takes the better of a
card-time price and a near-close price for the same wager — a price nobody could
have taken, which inflates every measured edge. The window is in the store's
**filename**, on every row as `snapshot_phase`, and checked on append against
what the store already holds.

The requested instant is recorded rather than the served one:
`OddsApiProvider.historical_event_odds` returns the response's `data` and not
its envelope, so the exact snapshot the archive served is not visible from here.
What *is* visible is each bookmaker's own `last_update`, and that is stored per
row — so the lead time actually achieved is measurable rather than assumed.

## 6. Dedupe on price identity, never on the row

`stores.dedupe_prices` keys on the quote — event, market, segment, player,
selection, line, book, snapshot phase — and carries no timestamp. The NHL lab
deduplicated on the whole row, wrote every quote twice, and every interval came
out root-two too narrow while nothing about the output looked wrong.

## 7. Never ask for a market before its cut-off

Historical featured markets (`h2h`, `spreads`, `totals`) exist for
`basketball_ncaab` from **2020-11-16**; everything else — props, halves, every
alternate ladder, and `team_totals` — from **2023-05-03**, site-wide. That date
falls after the 2022-23 season ended, so the full catalogue is buyable for
**2024, 2025 and 2026 only** (seasons labelled by the year they end).

Asking anyway costs nothing and returns nothing, **which looks exactly like "no
book quoted it"**. The plan therefore filters keys per event date, records every
refusal with its cut-off, and :func:`guard_cutoffs` raises if a plan that
survived the filter still contains a violation.

## 8. An empty ACCOUNT is not a fact about the archive

Rule 2 is about this run's own cap. This rule is about the balance behind it,
and they fail in opposite directions.

A run that hits its cap has bought less than it planned: the segments it did not
reach are simply unbought, and re-running buys them. A run whose **account**
empties mid-flight keeps making requests that the provider no longer answers.
Those responses stage nothing, the events under them land in the census as
having produced no quote, and the report then publishes "the archive does not
retain this" out of a fact about our wallet. That is fabricating a fact about
retention, and it is the one failure this module's whole census discipline
exists to prevent arriving through the one door it did not watch.

So `x-requests-remaining` is read as a measurement and acted on:

* `scripts/buy_historical_prices.py` refuses to **start** a run whose declared
  cap exceeds the balance the provider reports — the same pre-flight the card
  and the probe have always had, which this script did not;
* :func:`buy` re-reads the measured remaining balance after **every** response
  and stops the run with :class:`~cbb_betting_lab.providers.odds_api.QuotaExhausted`
  the moment it falls below a floor derived from the widest single request the
  run can make;
* a run stopped that way is recorded as `stopped_on_quota` and :func:`render`
  prints **STOPPED ON QUOTA** in place of the ordinary partial-buy wording,
  lists every segment the run never reached as unasked, and says in the census
  section that nothing in it may be read as evidence about retention.

**No quota number is ever assumed.** When the provider reports none, the breaker
has nothing to watch and the report says exactly that rather than letting the
absence of a stop read as a clean bill of health.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from cbb_betting_lab import markets as M
from cbb_betting_lab import selection as SEL
from cbb_betting_lab import stores
from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.conferences import Tier
from cbb_betting_lab.providers import team_names
from cbb_betting_lab.providers.env_file import redact
from cbb_betting_lab.providers.odds_api import (
    HISTORICAL_EVENTS_LIST_COST,
    HISTORICAL_MULTIPLIER,
    CreditCapReached,
    OddsApiProvider,
    ProviderError,
    QuotaExhausted,
    Spend,
    markets_fingerprint,
)

# The population, the tier of a game, and the cell a game sits in are imported
# from the retention probe rather than re-derived here. The probe and the
# purchase disagreeing about which games count, or about which tier a game is
# in, would make every coverage number the probe produced inapplicable to the
# prices this module buys — and the disagreement would be invisible, because
# both sides would look internally consistent. One definition, two readers.
from cbb_betting_lab.reports import retention_probe as RP


# ---------------------------------------------------------------------------
# Declared in advance. Nothing in this block is tuned after a run.
# ---------------------------------------------------------------------------

#: Featured markets exist historically for this sport from here. Recorded
#: identically in `scripts/estimate_credit_cost.py` and
#: `reports/retention_probe.py`, read from the-odds-api.com on 2026-09-01.
FEATURED_HISTORY_FROM = RP.FEATURED_HISTORY_FROM

#: Everything else — props, halves, every alternate ladder, and `team_totals`
#: — from here, site-wide. After the 2022-23 season ended.
ADDITIONAL_HISTORY_FROM = RP.ADDITIONAL_HISTORY_FROM

#: The seasons whose **full** catalogue is buyable at all. Labelled by the year
#: they end, like everything else in this lab.
FULL_CATALOGUE_SEASONS: tuple[int, ...] = (2024, 2025, 2026)

#: The seasons whose featured markets are buyable. 2021 is partial: the archive
#: starts 2020-11-16 and that season had already begun.
FEATURED_SEASONS: tuple[int, ...] = (2021, 2022, 2023, 2024, 2025, 2026)


@dataclass(frozen=True)
class SnapshotWindow:
    """One lead time before tip, and the store it is allowed to write to.

    Two windows, never mixed. See rule 5 in the module docstring.
    """

    name: str
    minutes_before_tip: int
    why: str

    def snapshot_for(self, commence_time: str) -> str:
        return RP.snapshot_for(commence_time, minutes_before=self.minutes_before_tip)


#: The card-time window. Sixty minutes matches
#: `schedule_contract.CARD_LEAD_MINUTES` and the retention probe's snapshot, so
#: a retention conclusion drawn at that lead applies to the prices bought here.
CARD_WINDOW = SnapshotWindow(
    name="card",
    minutes_before_tip=60,
    why=(
        "The lead the card actually publishes at "
        "(`schedule_contract.CARD_LEAD_MINUTES` = 60) and the lead the "
        "retention probe measured coverage at. Edge is measured against a "
        "price available at card time, so this is the window a claim about "
        "this lab's own cards has to rest on."
    ),
)

#: The near-close window. A price ten minutes out is not a price this lab's card
#: could ever have taken; it exists to measure how much of a card-time edge is
#: still there at the close, and how far the number moved.
CLOSE_WINDOW = SnapshotWindow(
    name="close",
    minutes_before_tip=10,
    why=(
        "Near-close. **Not a window this lab can bet** — the card publishes an "
        "hour out. It exists so that closing-line movement can be measured "
        "against the card price, and it is kept in its own store because "
        "collapsing to the best price across both windows would hand every "
        "wager a price nobody could have taken."
    ),
)

WINDOWS: dict[str, SnapshotWindow] = {
    CARD_WINDOW.name: CARD_WINDOW,
    CLOSE_WINDOW.name: CLOSE_WINDOW,
}

#: Provider keys per request. Chunking does not change what a run is billed —
#: the bound is `keys x regions x 10` however it is split. It changes three
#: other things: a 422 or a timeout costs one chunk rather than a whole event,
#: a run near its cap gets most of an event instead of none, and each cached
#: response stays small enough to read by eye.
MARKET_CHUNK_SIZE = 8

#: Fixed so a re-run walks the same order and re-uses the same cache. A
#: purchase that re-drew its order on every run would buy a differently-shaped
#: sample each month and the union of them would be shaped like nothing.
DEFAULT_SEED = 20260901

#: Deliberately well below Cooper's 1,500,000 monthly authorisation. A run is
#: meant to be repeated across months; the cap is what makes each one bounded,
#: not what makes the purchase complete. The dry run prints the bound of the
#: plan it was given; set the cap from that.
DEFAULT_CREDIT_CAP = 200_000

#: Bumped whenever an older record would render **wrongly** under today's
#: renderer, so a stale record fails loudly rather than producing a report with
#: holes in it.
#:
#: Stated that way rather than as "whenever the shape changes", because the two
#: are not the same rule and only the first is the one worth enforcing. Keys
#: added for the balance circuit-breaker (`stopped_on_quota`, `quota_floor`,
#: `quota_ever_reported`, `unreached_segments`, `zero_billed_responses`,
#: `fallback_charges`) are absent from every record written before it existed,
#: and `render` reads each with a default that is *true of those records*: none
#: of them could have stopped on quota, because nothing measured it. Bumping for
#: those would buy nothing and would make the committed record unrenderable —
#: which is a worse outcome than the one the version guard exists to prevent.
#: A key whose absence would make the report SAY something false is a bump.
RECORD_SCHEMA_VERSION = 1

REPORT_STEM = "historical_purchase"
CACHE_DIRNAME = "historical_purchase"
STORE_STEM = "historical_prices"

#: The last line of a dry run. CI greps for this phrase at the end of the line,
#: which is why there is no full stop after it.
NOTHING_WAS_SPENT = "no credit was spent"


class PurchaseError(RuntimeError):
    """The purchase refused to run, or refused to trust what it had."""


# ---------------------------------------------------------------------------
# The waves — Cooper's priority order, and it is also the order of decreasing
# confidence that a market is quoted at all.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Wave:
    """One priority band of the purchase."""

    name: str
    order: int
    tiers: tuple[int, ...]
    title: str
    why: str
    #: Seasons this wave may be bought for at all, from the archive's cut-offs.
    seasons: tuple[int, ...]
    #: Non-empty when this module cannot buy the wave. Named rather than
    #: dropped: a wave that vanishes from the plan is a wave nobody notices is
    #: missing, and "we did not buy it" and "it does not exist" are the two
    #: things this repository spends most of its effort keeping apart.
    blocked_reason: str = ""

    @property
    def buyable(self) -> bool:
        return not self.blocked_reason


WAVES: tuple[Wave, ...] = (
    Wave(
        name="core_team",
        order=1,
        tiers=(1,),
        title="Core team markets",
        seasons=FEATURED_SEASONS,
        why=(
            "Moneyline, spread, total and team total. Quoted on essentially "
            "every game by every book, settleable from the team-game table "
            "alone, and the only family with six seasons of archive behind it "
            "— `h2h`, `spreads` and `totals` reach back to 2020-11-16. "
            "`team_totals` is **not** a featured market and only reaches back "
            "to 2023-05-03, so this wave asks for different key sets in "
            "different seasons rather than asking for a market that could not "
            "exist and recording the silence as absence."
        ),
    ),
    Wave(
        name="ladders_and_halves",
        order=2,
        tiers=(2,),
        title="Alternate ladders and the halves",
        seasons=FULL_CATALOGUE_SEASONS,
        why=(
            "Every rung of a ladder prices off the same distribution object as "
            "its featured line, so a ladder is the cheapest way to add rows "
            "without adding a model. Halves are a genuinely different "
            "quantity, and a first half **can** end level where a full game "
            "cannot (3.54% of 90,766 college first halves against 0.000% of "
            "94,194 full games). Three seasons only: everything here is past "
            "the 2023-05-03 cut-off."
        ),
    ),
    Wave(
        name="props",
        order=3,
        tiers=(3,),
        title="Player props",
        seasons=FULL_CATALOGUE_SEASONS,
        why=(
            "Bought last of the per-event families and worth stating plainly: "
            "**nothing in this lab reaches `Availability.CONFIRMED`, so no "
            "player prop can produce a selection.** These prices are bought to "
            "be modelled, frozen and settled, and they are evidence about the "
            "model rather than a bet the card can make. That is not a pass, an "
            "avoid, or a no-value call. Coverage is also expected to be thin "
            "and concentrated on televised high-major games, which is exactly "
            "why the event order is stratified by tier."
        ),
    ),
    Wave(
        name="futures",
        order=4,
        tiers=(4,),
        title="Futures",
        seasons=FULL_CATALOGUE_SEASONS,
        blocked_reason=(
            "Futures are served under a separate sport key "
            f"(`{CBB.futures_sport_keys[0]}`) as a whole-competition "
            "snapshot rather than per event, and "
            "`providers/odds_api.OddsApiProvider` exposes no historical bulk "
            "endpoint. This script therefore cannot buy them, and the wave is "
            "named here with its cost rather than dropped — a wave that "
            "vanishes from a plan is one nobody notices is missing. Adding "
            "that endpoint is a change to a module this one does not own."
        ),
        why=(
            "Last, and their own section of every report for ever: a futures "
            "stake is tied up for months and settles on a different clock, so "
            "no futures return is ever folded into a headline computed over "
            "game bets."
        ),
    ),
)

WAVES_BY_NAME: dict[str, Wave] = {w.name: w for w in WAVES}


def wave_for(name: str) -> Wave:
    try:
        return WAVES_BY_NAME[str(name)]
    except KeyError as exc:
        raise PurchaseError(
            f"Unknown wave {name!r}. Known, in priority order: "
            f"{[w.name for w in WAVES]}"
        ) from exc


# ---------------------------------------------------------------------------
# The archive's cut-offs
# ---------------------------------------------------------------------------


def cutoff_for(provider_key: str) -> str:
    """The earliest slate date the archive can answer for this provider key.

    Featured keys reach back to 2020-11-16; everything else to 2023-05-03. The
    featured set comes from `markets.bulk_provider_keys()` — the registry —
    rather than from a literal here, so a key moving between the two sets moves
    its cut-off with it.
    """
    return (
        FEATURED_HISTORY_FROM
        if str(provider_key) in set(M.bulk_provider_keys())
        else ADDITIONAL_HISTORY_FROM
    )


def keys_available_on(keys: Sequence[str], slate_date: str) -> tuple[tuple[str, ...], dict[str, str]]:
    """Split a key list into what the archive can answer for on a given day.

    Returns `(allowed, refused)` where `refused` maps each refused key to its
    cut-off. **Refusing costs nothing and returns nothing** — which is exactly
    the point: asking anyway also costs nothing and returns nothing, and the
    two are indistinguishable in a coverage report.
    """
    day = str(slate_date)[:10]
    allowed: list[str] = []
    refused: dict[str, str] = {}
    for key in sorted(set(str(k) for k in keys)):
        floor = cutoff_for(key)
        if day < floor:
            refused[key] = floor
        else:
            allowed.append(key)
    return tuple(allowed), refused


# ---------------------------------------------------------------------------
# The event order — rule 1
# ---------------------------------------------------------------------------


def _tiebreak(game_id: object, seed: int) -> str:
    """A stable tiebreak that does not depend on `hash()`.

    `hash()` is salted per process for strings, so an order built from it would
    differ between runs and the cache would miss on every resume. sha256 of the
    seed and the game id is the same everywhere, for ever.
    """
    return hashlib.sha256(f"{int(seed)}:{game_id}".encode("utf-8")).hexdigest()


def stratified_order(
    events: Sequence[RP.ProbeEvent], *, seed: int = DEFAULT_SEED
) -> tuple[RP.ProbeEvent, ...]:
    """Order events so that **every prefix** is a proportional sample.

    Each event is placed at `(i + 0.5) / n_c` within its own
    `(tier, month, tip window)` cell, and the whole list is sorted on that
    position. A prefix of length `k` then contains `k · n_c / N` events from
    cell `c` to within one event — for every cell, at every `k`, by
    construction.

    That is the property the module docstring's rule 1 is about, and it is what
    makes a run that stops at the cap a **sample of the wave** rather than a
    prefix of it. `tests/test_historical_purchase.py` asserts it directly, at
    every prefix length, on all three axes.

    Deterministic: the within-cell shuffle is seeded per cell and the tiebreak
    is a sha256 rather than `hash()`, so a resumed run walks the same order and
    hits the same cache files.
    """
    by_cell: dict[str, list[RP.ProbeEvent]] = {}
    for event in events:
        by_cell.setdefault(event.stratum, []).append(event)

    ranked: list[tuple[float, str, RP.ProbeEvent]] = []
    for cell in sorted(by_cell):
        members = sorted(by_cell[cell], key=lambda e: e.game_id)
        # Shuffled inside the cell so the sample within a cell is not itself
        # ordered by game id — ESPN's ids are assigned in roughly chronological
        # order, so an unshuffled cell would buy the earliest games in it.
        random.Random(f"{int(seed)}:{cell}").shuffle(members)
        size = len(members)
        for position, event in enumerate(members):
            ranked.append(
                ((position + 0.5) / size, _tiebreak(event.game_id, seed), event)
            )
    ranked.sort(key=lambda item: (item[0], item[1]))
    return tuple(event for _, _, event in ranked)


#: The three axes the order is spread across, and the attribute each reads.
STRATIFICATION_AXES: tuple[tuple[str, str], ...] = (
    ("conference_tier", "tier"),
    ("month", "month"),
    ("tip_window", "window"),
)


def achieved_stratification(
    bought: Sequence[RP.ProbeEvent], population: Sequence[RP.ProbeEvent]
) -> list[dict]:
    """How close what was actually bought landed to the population it came from.

    **Measured, never assumed.** A purchase that reports itself as stratified
    while being anything but is worse than an admittedly biased one, because
    every later conclusion inherits the bias and nobody can see it. One row per
    axis value, with the population share, the bought share, and the difference.
    """
    rows: list[dict] = []
    total_bought = len(bought)
    total_population = len(population)
    for axis, attribute in STRATIFICATION_AXES:
        values = sorted(
            {str(getattr(e, attribute)) for e in population}
            | {str(getattr(e, attribute)) for e in bought}
        )
        for value in values:
            in_population = sum(
                1 for e in population if str(getattr(e, attribute)) == value
            )
            in_bought = sum(1 for e in bought if str(getattr(e, attribute)) == value)
            population_share = (
                in_population / total_population if total_population else 0.0
            )
            bought_share = in_bought / total_bought if total_bought else 0.0
            rows.append(
                {
                    "axis": axis,
                    "value": value,
                    "population": in_population,
                    "population_share": round(population_share, 4),
                    "bought": in_bought,
                    "bought_share": round(bought_share, 4),
                    "difference": round(bought_share - population_share, 4),
                }
            )
    return rows


def worst_deviation(rows: Sequence[Mapping]) -> float:
    """The largest absolute share deviation across every axis value."""
    return max((abs(float(r["difference"])) for r in rows), default=0.0)


# ---------------------------------------------------------------------------
# The plan
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlanSegment:
    """One wave in one season: what to ask for, on which events, in what order."""

    wave: str
    season: int
    window: str
    keys: tuple[str, ...]
    #: Provider key -> the cut-off that refused it. Never asked, and never
    #: recorded as absent.
    keys_refused: dict[str, str]
    events: tuple[RP.ProbeEvent, ...]
    regions: int
    blocked_reason: str = ""

    @property
    def buyable(self) -> bool:
        return bool(self.keys) and bool(self.events) and not self.blocked_reason

    @property
    def pessimistic_bound(self) -> int:
        """What this segment could cost if every asked market returned at every
        book, plus the snapshot listings.

        The direction to be wrong in, and the only direction. The real spend
        comes in under it because an asked-for market nobody quotes costs
        nothing — and the gap between the two is itself information about how
        much of the catalogue this sport's books actually hang.
        """
        if not self.buyable:
            return 0
        listings = len({e.snapshot for e in self.events}) * HISTORICAL_EVENTS_LIST_COST
        odds = (
            len(self.events)
            * len(self.keys)
            * int(self.regions)
            * HISTORICAL_MULTIPLIER
        )
        return int(listings + odds)

    def to_json(self) -> dict:
        return {
            "wave": self.wave,
            "season": int(self.season),
            "window": self.window,
            "keys": list(self.keys),
            "keys_refused": dict(sorted(self.keys_refused.items())),
            "events_planned": len(self.events),
            "regions": int(self.regions),
            "pessimistic_bound": self.pessimistic_bound,
            "blocked_reason": self.blocked_reason,
        }


@dataclass(frozen=True)
class PurchasePlan:
    """Every segment, in priority order."""

    segments: tuple[PlanSegment, ...]
    window: SnapshotWindow
    seed: int

    @property
    def pessimistic_bound(self) -> int:
        return sum(s.pessimistic_bound for s in self.segments)

    def buyable_segments(self) -> tuple[PlanSegment, ...]:
        return tuple(s for s in self.segments if s.buyable)

    def to_json(self) -> dict:
        return {
            "window": self.window.name,
            "window_minutes_before_tip": self.window.minutes_before_tip,
            "seed": int(self.seed),
            "pessimistic_bound": self.pessimistic_bound,
            "segments": [s.to_json() for s in self.segments],
        }


def build_plan(
    events_by_season: Mapping[int, Sequence[RP.ProbeEvent]],
    *,
    waves: Sequence[str] = (),
    window: SnapshotWindow = CARD_WINDOW,
    regions: int = 2,
    seed: int = DEFAULT_SEED,
    max_events_per_segment: int = 0,
) -> PurchasePlan:
    """The whole purchase, in priority order, with every event order stratified.

    Segments are emitted **wave-major**: every season of wave 1 before any of
    wave 2. That is Cooper's order and it is also the order of decreasing
    confidence that a market is quoted at all, so a purchase that runs out of
    credits has the family it is most sure of, across every season, rather than
    a little of everything.

    Within a wave the seasons run oldest-first, because the earliest season is
    the one whose archive is most likely to disappoint and finding that out
    early is worth more than finding it out last.
    """
    wanted = [wave_for(name) for name in waves] if waves else list(WAVES)
    wanted.sort(key=lambda w: w.order)

    segments: list[PlanSegment] = []
    for wave in wanted:
        keys = tuple(sorted({k for t in wave.tiers for k in M.provider_keys_in_tier(t)}))
        for season in sorted(events_by_season):
            events = list(events_by_season[season])
            if season not in wave.seasons:
                # Recorded as a refusal rather than silently absent: the reason
                # this season is not in this wave is an archive cut-off, and
                # that is a fact worth printing beside the plan.
                segments.append(
                    PlanSegment(
                        wave=wave.name,
                        season=int(season),
                        window=window.name,
                        keys=(),
                        keys_refused={k: cutoff_for(k) for k in keys},
                        events=(),
                        regions=int(regions),
                        blocked_reason=(
                            f"Season {season} is before the archive's cut-off "
                            f"for every key in this wave."
                        ),
                    )
                )
                continue
            if not wave.buyable:
                segments.append(
                    PlanSegment(
                        wave=wave.name,
                        season=int(season),
                        window=window.name,
                        keys=keys,
                        keys_refused={},
                        events=tuple(stratified_order(events, seed=seed)),
                        regions=int(regions),
                        blocked_reason=wave.blocked_reason,
                    )
                )
                continue

            ordered = stratified_order(events, seed=seed)
            if max_events_per_segment > 0:
                # Truncating the *stratified* order is safe in a way that
                # truncating any other order is not: the first k of this list
                # are already a proportional sample of the whole.
                ordered = ordered[: int(max_events_per_segment)]
            if not ordered:
                continue
            # The cut-off bites per event date, not per season: the archive
            # starts 2020-11-16, part-way through the 2021 season. The segment
            # asks for the keys every one of its events can answer for, and any
            # event that would need a narrower set is dropped into its own
            # refusal rather than silently asked with the wider one.
            earliest = min(e.slate_date for e in ordered)
            allowed, refused = keys_available_on(keys, earliest)
            if not allowed:
                segments.append(
                    PlanSegment(
                        wave=wave.name,
                        season=int(season),
                        window=window.name,
                        keys=(),
                        keys_refused=refused,
                        events=(),
                        regions=int(regions),
                        blocked_reason=(
                            f"Every key in this wave is refused before "
                            f"{earliest}: the archive does not hold them."
                        ),
                    )
                )
                continue
            segments.append(
                PlanSegment(
                    wave=wave.name,
                    season=int(season),
                    window=window.name,
                    keys=allowed,
                    keys_refused=refused,
                    events=ordered,
                    regions=int(regions),
                )
            )
    return PurchasePlan(segments=tuple(segments), window=window, seed=int(seed))


def guard_cutoffs(plan: PurchasePlan) -> None:
    """Raise if any segment would ask for a key before the archive holds it.

    Belt and braces over the planner's own filter. A market asked for before
    its cut-off returns nothing, and nothing is indistinguishable from "no book
    quoted it" — which is the single most consequential way a report in this
    repository can be wrong.
    """
    for segment in plan.segments:
        if not segment.events or not segment.keys:
            continue
        earliest = min(e.slate_date for e in segment.events)
        _allowed, refused = keys_available_on(segment.keys, earliest)
        if refused:
            raise PurchaseError(
                f"Segment {segment.wave}/{segment.season} would ask for "
                f"{sorted(refused)} on games from {earliest}, and the archive "
                f"only holds them from {sorted(set(refused.values()))}. "
                "Refusing: it costs nothing and returns nothing, which looks "
                "exactly like a market no book quoted."
            )


# ---------------------------------------------------------------------------
# Paths — the cache, the store, the record
# ---------------------------------------------------------------------------


def cache_dir_for(competition: Competition, raw_dir: Path, window: SnapshotWindow) -> Path:
    return Path(raw_dir) / competition.data_dir_segment / CACHE_DIRNAME / window.name


def cache_path(
    cache_dir: Path, event: RP.ProbeEvent, chunk: Sequence[str]
) -> Path:
    """Where one chunk's raw response for one event lives.

    **The filename carries the chunk's fingerprint, never its length.** See
    rule 3. It is also the resume state: a file here is a question already
    paid for.
    """
    return (
        Path(cache_dir)
        / event.slate_date
        / f"{event.game_id}__{markets_fingerprint(tuple(chunk))}.json"
    )


def slate_cache_path(cache_dir: Path, snapshot: str) -> Path:
    stamp = "".join(ch for ch in str(snapshot) if ch.isalnum())
    return Path(cache_dir) / "slates" / f"slate__{stamp}.json"


def store_path(
    competition: Competition, processed_dir: Path, window: SnapshotWindow
) -> Path:
    """One store per window. The window is in the name, not just in a column.

    A column can be filtered wrongly; a filename cannot be opened wrongly by
    accident. `stores.assert_single_window` is the second guard, on the frame.
    """
    return Path(processed_dir) / competition.output_name(
        f"{STORE_STEM}__{window.name}", ".csv"
    )


def record_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPORT_STEM, ".json")


def report_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name(REPORT_STEM, ".md")


# ---------------------------------------------------------------------------
# Staging a response into this lab's vocabulary — rule 4
# ---------------------------------------------------------------------------

#: One row per quote. The first eight are `stores.PRICE_IDENTITY` in order, so
#: a reader can see at a glance that the identity carries no timestamp.
PRICE_COLUMNS: tuple[str, ...] = stores.PRICE_IDENTITY + (
    "american_odds",
    "provider_key",
    "game_id",
    "season",
    "slate_date",
    "commence_time",
    "home_team",
    "away_team",
    "home_name",
    "away_name",
    "tier",
    "tip_window",
    "snapshot_requested",
    "lead_minutes",
    "book_last_update",
)


def _text(value: object) -> str:
    from cbb_betting_lab.season import clean_text

    return clean_text(value)


def _selection_and_player(
    market: M.Market,
    outcome: Mapping,
    *,
    provider_home: str,
    provider_away: str,
) -> tuple[str | None, float | None, str]:
    """`(selection, line, player)` in **this lab's** vocabulary, or a None.

    Dispatched off the registry — `market.yes_no`, `market.family`,
    `market.settles_on` — rather than off a hand-written list of provider keys,
    so wiring a new market brings its staging with it.

    `None` for the selection means **unparseable**, never a guess. That is the
    fifth member of the NHL lab's join-vocabulary bug family: an outcome staged
    under a spelling the join does not use misses everything downstream and
    nothing errors. Unparseable rows are counted in the census instead.
    """
    name = _text(outcome.get("name"))
    description = _text(outcome.get("description"))
    point = SEL.normalise_line(outcome.get("point"))

    if market.yes_no:
        # Yes -> over 0.5, No -> under 0.5. Never `yes`/`no`: two spellings of
        # one bet become two keys, and the card stakes it twice.
        return SEL.yes_no_selection(name), SEL.YES_NO_LINE, description
    if market.family == M.PLAYER:
        return SEL.over_under_selection(name), point, description
    if market.settles_on in {"team_score", "half_team_score"}:
        return (
            SEL.team_total_selection(name, description, provider_home, provider_away),
            point,
            "",
        )
    if market.settles_on in {"game_total", "half_total"}:
        return SEL.over_under_selection(name), point, ""
    # Margin markets: moneyline and every spread. A moneyline carries no line,
    # and `normalise_line` returns None rather than 0.0 for it — a pick'em is a
    # line of zero and a moneyline is no line at all.
    return SEL.team_selection(name, provider_home, provider_away), point, ""


def stage_event(
    payload: Mapping,
    *,
    event: RP.ProbeEvent,
    window: SnapshotWindow,
    provider_event_id: str,
) -> tuple[list[dict], dict[str, int]]:
    """One cached response in, price rows plus a census out. **Pure.**

    No network, no clock, no randomness — so the mapping from the provider's
    vocabulary into this lab's can be fixed and re-run for ever without
    spending a credit twice. That is rule 4, and at ten times live rate it is
    worth more here than anywhere else in the repository.

    The census counts every outcome that did not become a row. A quote that
    vanishes without appearing in it is a defect, not a decision — the same
    discipline as `gates.AccountingIdentity`.
    """
    census: dict[str, int] = {}

    def drop(reason: str) -> None:
        census[reason] = census.get(reason, 0) + 1

    provider_home = _text(payload.get("home_team"))
    provider_away = _text(payload.get("away_team"))
    rows: list[dict] = []
    for bookmaker in payload.get("bookmakers") or []:
        if not isinstance(bookmaker, Mapping):
            drop("bookmaker_not_an_object")
            continue
        book = _text(bookmaker.get("key"))
        if not book:
            drop("bookmaker_carried_no_key")
            continue
        book_updated = _text(bookmaker.get("last_update"))
        for provider_market in bookmaker.get("markets") or []:
            if not isinstance(provider_market, Mapping):
                drop("market_not_an_object")
                continue
            provider_key = _text(provider_market.get("key"))
            market = M.market_for_provider_key(provider_key)
            if market is None:
                # Data about the provider, not an error. Counted rather than
                # dropped, exactly as the retention probe counts it.
                drop(f"unwired_provider_key:{provider_key or 'blank'}")
                continue
            outcomes = provider_market.get("outcomes") or []
            if not isinstance(outcomes, list) or not outcomes:
                # A market present with no outcomes is not a price. Staging it
                # would make an empty shell read as a quote.
                drop("market_present_with_no_outcomes")
                continue
            for outcome in outcomes:
                if not isinstance(outcome, Mapping):
                    drop("outcome_not_an_object")
                    continue
                selection, line, player = _selection_and_player(
                    market,
                    outcome,
                    provider_home=provider_home,
                    provider_away=provider_away,
                )
                if selection is None or selection not in SEL.KNOWN_SELECTIONS:
                    drop("unparseable_selection")
                    continue
                odds = outcome.get("price")
                try:
                    american = float(odds)
                except (TypeError, ValueError):
                    # A missing price stays missing. A quote with no number on
                    # it is not a quote, and inventing one is the one thing
                    # this repository never does.
                    drop("outcome_carried_no_price")
                    continue
                rows.append(
                    {
                        "event_id": str(provider_event_id),
                        "market": market.key,
                        "segment": market.segment,
                        "player": player,
                        "selection": selection,
                        "line": line,
                        "book": book,
                        "snapshot_phase": window.name,
                        "american_odds": american,
                        "provider_key": provider_key,
                        "game_id": int(event.game_id),
                        "season": int(event.season),
                        "slate_date": event.slate_date,
                        "commence_time": event.commence_time,
                        "home_team": int(event.home_team_id),
                        "away_team": int(event.away_team_id),
                        "home_name": event.home_name,
                        "away_name": event.away_name,
                        "tier": event.tier,
                        "tip_window": event.window,
                        "snapshot_requested": event.snapshot,
                        "lead_minutes": int(window.minutes_before_tip),
                        "book_last_update": book_updated,
                    }
                )
    return rows, census


def append_prices(
    rows: Sequence[Mapping], path: Path, *, window: SnapshotWindow
) -> int:
    """Dedupe on the **quote**, refuse a second window, append. Returns rows held.

    Three guards, in order:

    1. every incoming row must carry this window — a mislabelled row is how two
       windows end up in one file with nothing looking wrong;
    2. the store's existing window must be the same one, checked with
       `stores.assert_single_window` against what is already on disk;
    3. `stores.dedupe_prices` keys on `stores.PRICE_IDENTITY`, which carries
       **no timestamp**. Deduping on the whole row is the NHL lab's defect: it
       wrote every quote twice, ROI was unchanged, and every interval came out
       root-two too narrow.
    """
    target = Path(path)
    frame = pd.DataFrame(list(rows), columns=list(PRICE_COLUMNS))
    if not frame.empty:
        wrong = sorted(
            {str(w) for w in frame["snapshot_phase"].unique()} - {window.name}
        )
        if wrong:
            raise PurchaseError(
                f"{len(wrong)} row(s) carry snapshot windows {wrong} and this "
                f"store is the {window.name!r} store. Refusing: mixing a "
                "card-time price and a near-close price for one wager hands it "
                "a price nobody could have taken, and `best_price_per_wager` "
                "would then take the better of the two."
            )
    existing = stores.read_store(target, columns=PRICE_COLUMNS)
    if not existing.empty:
        held = stores.assert_single_window(existing)
        if held and held != window.name:
            raise PurchaseError(
                f"{target} already holds the {held!r} window and this run is "
                f"buying {window.name!r}. One window per store — the window is "
                "in the filename precisely so this cannot happen by accident."
            )
    if frame.empty:
        return len(existing)
    frame = stores.dedupe_prices(frame)
    return stores.append(
        frame,
        target,
        columns=PRICE_COLUMNS,
        dedupe_on=stores.PRICE_IDENTITY,
    )


# ---------------------------------------------------------------------------
# The run
# ---------------------------------------------------------------------------


@dataclass
class BuyState:
    """Everything one run accumulates, so `buy` stays readable."""

    spend: Spend = field(default_factory=Spend)
    rows: list[dict] = field(default_factory=list)
    census: dict[str, int] = field(default_factory=dict)
    bought_events: list[RP.ProbeEvent] = field(default_factory=list)
    cached_events: list[RP.ProbeEvent] = field(default_factory=list)
    unmatched: list[dict] = field(default_factory=list)
    failures: list[dict] = field(default_factory=list)
    responses_bought: int = 0
    responses_from_cache: int = 0
    completed: bool = True
    stopped_because: str = ""
    #: How far a single response billed past its own pessimistic bound. Zero is
    #: the expected value and a positive number is the NHL lab's defect
    #: happening again, in the open.
    worst_overrun: int = 0
    per_segment: list[dict] = field(default_factory=list)
    #: True only when the run stopped because the ACCOUNT ran out of credits,
    #: as opposed to because this run hit its own cap. Kept apart from
    #: `completed` because the two mean opposite things about what the run's
    #: silence proves: a capped run left markets unbought, an exhausted-quota
    #: run left markets UNANSWERED, and an unanswered market in a census is
    #: indistinguishable from one the provider does not retain.
    stopped_on_quota: bool = False
    #: The floor the circuit-breaker watched, and the last remaining quota the
    #: provider actually reported. `None` means the provider reported none at
    #: any point in the run — which is a third answer, not a zero.
    quota_floor: int = 0
    quota_last_measured: int | None = None
    #: Whether the provider reported a remaining quota at any point in the run.
    #: False means the circuit-breaker had nothing to watch for the whole run —
    #: not that the balance was healthy. The report has to say which of those
    #: two it is, or the absence of a stop reads as a measured all-clear.
    quota_ever_reported: bool = False
    #: How many times the breaker looked and found no balance to compare.
    #:
    #: `quota_ever_reported` alone is two answers where there are three. A
    #: provider (or a proxy) that reports a balance once and then stops leaves
    #: it True while the breaker is blind for the rest of the run, which is the
    #: worst of the three states and the one that reads as the best. Anything
    #: above zero means the run was NOT watched throughout, and no sentence
    #: anywhere may then treat an absence as a fact about the archive.
    quota_unwatched_responses: int = 0
    #: Segments the run never reached, in plan order. They are NOT absent from
    #: the archive and they are NOT unquoted; they were never asked. Recorded
    #: so the segment table shows them instead of simply ending early, which is
    #: how "we stopped" becomes "the provider had nothing".
    unreached_segments: list[dict] = field(default_factory=list)

    def note(self, reason: str, n: int = 1) -> None:
        self.census[reason] = self.census.get(reason, 0) + int(n)


def _read_cache(path: Path, *, use_cache: bool):
    if not (use_cache and Path(path).is_file()):
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        # A damaged cache file is not evidence of anything. Re-ask rather than
        # record its emptiness as an answer.
        return None


def _write_cache(path: Path, payload) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Temp-then-move: the football lab lost a rehearsal to a redirect that
    # created a zero-byte file when the command producing it failed, and a
    # zero-byte cache file is a bought answer thrown away.
    scratch = target.with_suffix(target.suffix + ".partial")
    scratch.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", "utf-8")
    scratch.replace(target)


def buy(
    *,
    plan: PurchasePlan,
    provider: OddsApiProvider,
    indexes: Mapping[int, team_names.TeamIndex],
    credit_cap: int,
    cache_dir: Path,
    competition: Competition = CBB,
    chunk_size: int = MARKET_CHUNK_SIZE,
    use_cache: bool = True,
    generated_at: str = "",
    population_by_season: Mapping[int, Sequence[RP.ProbeEvent]] | None = None,
    quota_floor: int | None = None,
) -> dict:
    """Walk the plan in priority order, buy what is not cached, and record it.

    The record is the artefact. `render` is a pure function of it, so the
    report's wording can be improved for ever without spending a credit twice —
    and at ten times the live rate that rule earns more here than anywhere else.

    `quota_floor` is the ACCOUNT balance below which the run stops. It is
    derived rather than invented: the default is the pessimistic bound of the
    single largest request this run can make, `10 x chunk_size x regions`, so
    the breaker trips while there is still enough balance for the request in
    flight to have been answered in full. Passing a number overrides it;
    nothing here ever assumes one when the provider reports none.
    """
    guard_cutoffs(plan)
    state = BuyState()
    listings: dict[str, list[dict]] = {}
    cache_root = Path(cache_dir)
    # The widest single request this plan can make. Used as the default floor
    # because it is the smallest balance at which the NEXT request could still
    # be answered whole; a floor of zero would let the run make a request the
    # account cannot pay for, and a partially-billed response is exactly the
    # thing whose silence is unreadable.
    regions_in_plan = max(
        [int(s.regions) for s in plan.buyable_segments()] or [1]
    )
    floor = (
        int(quota_floor)
        if quota_floor is not None
        else HISTORICAL_MULTIPLIER * int(chunk_size) * regions_in_plan
    )
    state.quota_floor = floor

    def measured_total_ok(where: str) -> bool:
        """The check the NHL lab did not have. See rule 2."""
        if state.spend.credits_spent <= int(credit_cap):
            return True
        state.completed = False
        state.stopped_because = (
            f"The **measured** running total reached "
            f"{state.spend.credits_spent:,} against a cap of "
            f"{int(credit_cap):,} while fetching {where}. The run stopped at "
            "once. A response billed more than its own pessimistic bound, "
            "which happens when the provider returns market keys that were not "
            "asked for — the NHL lab's 289,984-against-a-200,000-cap defect, "
            "caught here rather than discovered in an invoice."
        )
        return False

    def check_quota(where: str) -> None:
        """The circuit-breaker. Raises `QuotaExhausted` rather than returning.

        THIS IS NOT THE CREDIT CAP. The cap is this run's own budget and
        stopping against it leaves markets UNBOUGHT. This watches the account's
        balance, and running it out leaves markets UNANSWERED — the provider
        simply stops returning quotes, those responses stage no rows, and the
        census reason they land under reads as the provider not retaining that
        market. Publishing that is a statement about the archive made out of a
        fact about our wallet, which is a fabricated fact about retention.

        The remaining quota is read from `x-requests-remaining` **on the
        response just received**, never assumed and never carried forward from
        an earlier one. When that response reports none, this returns without
        stopping and without inventing a number, and counts the look as one the
        breaker could not make: the record then distinguishes a run watched
        throughout from one watched once and blind afterwards, which is the
        state that otherwise reads as the healthiest of the three.
        """
        remaining = state.spend.remaining_credits()
        if remaining is None:
            state.quota_unwatched_responses += 1
            return
        state.quota_ever_reported = True
        state.quota_last_measured = remaining
        if remaining >= floor:
            return
        raise QuotaExhausted(
            f"The provider reports {remaining:,} credit(s) remaining on the "
            f"account, below this run's floor of {floor:,}, measured while "
            f"fetching {where}. **STOPPED ON QUOTA.** The run stopped at once "
            "rather than continuing: once the balance is gone the provider "
            "stops returning quotes, and a response with no quotes in it is "
            "indistinguishable in a census from a market the archive does not "
            "retain. Everything this run did not reach is UNASKED, not absent."
        )

    def stop_on_quota(exc: QuotaExhausted) -> None:
        state.completed = False
        state.stopped_on_quota = True
        state.stopped_because = redact(str(exc))

    for segment in plan.segments:
        segment_record = {
            **segment.to_json(),
            "events_bought": 0,
            "events_from_cache": 0,
            "credits_spent_here": 0,
            "rows_staged": 0,
        }
        # A BLOCKED SEGMENT IS RECORDED WHETHER OR NOT THE RUN HAS STOPPED.
        #
        # This used to sit after the stop check, so a segment blocked by an
        # archive cut-off that happened to fall after a quota stop never
        # reached `per_segment` and was swept into `unreached_segments`
        # instead. Its real, known reason — the provider's archive does not go
        # back that far — was then replaced in the report by "we ran out of
        # money before we got there", which is a different and false statement
        # about why nothing was asked. The cut-off is true of that segment
        # regardless of what the budget did, so it is recorded regardless.
        if not segment.buyable:
            state.per_segment.append(segment_record)
            continue
        if not state.completed:
            # Buy nothing more, but keep walking the plan so the blocked
            # segments after the stop keep their own reason. A `break` here
            # is what handed them the budget's reason instead.
            continue
        chunks = RP.market_chunks(segment.keys, size=chunk_size)
        index = indexes.get(int(segment.season))
        if index is None:
            state.failures.append(
                {
                    "wave": segment.wave,
                    "season": segment.season,
                    "what": "team name index",
                    "error": (
                        "No team-name index for this season, so no provider "
                        "event could be resolved to one of our games. Nothing "
                        "was fetched for it."
                    ),
                }
            )
            state.per_segment.append(segment_record)
            continue
        credits_at_segment_start = state.spend.credits_spent

        for event in segment.events:
            if not state.completed:
                break
            listing = listings.get(event.snapshot)
            if listing is None:
                path = slate_cache_path(cache_root, event.snapshot)
                cached = _read_cache(path, use_cache=use_cache)
                if cached is not None:
                    listing = [x for x in cached if isinstance(x, dict)]
                    state.responses_from_cache += 1
                else:
                    try:
                        listing = provider.list_historical_events(
                            event.snapshot,
                            spend=state.spend,
                            credit_cap=int(credit_cap),
                        )
                    except CreditCapReached as exc:
                        state.completed = False
                        state.stopped_because = redact(str(exc))
                        break
                    except ProviderError as exc:
                        state.failures.append(
                            {
                                "game_id": event.game_id,
                                "what": "historical event listing",
                                "snapshot": event.snapshot,
                                "error": redact(str(exc)),
                            }
                        )
                        listings[event.snapshot] = []
                        continue
                    state.responses_bought += 1
                    # CACHE BEFORE STOPPING. This response is bought and paid
                    # for whatever the guards decide next; discarding it makes
                    # the resumed run buy it a second time. The odds path below
                    # has always written first for exactly this reason and this
                    # one did not, so a cap stop threw away a listing it had
                    # already been billed for.
                    _write_cache(path, listing)
                    if not measured_total_ok(f"the slate listing at {event.snapshot}"):
                        break
                    try:
                        check_quota(f"the slate listing at {event.snapshot}")
                    except QuotaExhausted as exc:
                        stop_on_quota(exc)
                        break
                listings[event.snapshot] = listing

            provider_event_id, reason = RP.match_provider_event(listing, event, index)
            if not provider_event_id:
                # A school this lab cannot spell is not a market the provider
                # does not retain. Counted, in no denominator anywhere.
                state.unmatched.append(
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

            served_entirely_from_cache = True
            event_rows: list[dict] = []
            for chunk in chunks:
                path = cache_path(cache_root, event, chunk)
                payload = _read_cache(path, use_cache=use_cache)
                if payload is None:
                    served_entirely_from_cache = False
                    before = state.spend.credits_spent
                    bound = (
                        HISTORICAL_MULTIPLIER * len(chunk) * int(segment.regions)
                    )
                    try:
                        payload = provider.historical_event_odds(
                            provider_event_id,
                            event.snapshot,
                            tuple(chunk),
                            spend=state.spend,
                            credit_cap=int(credit_cap),
                        )
                    except CreditCapReached as exc:
                        state.completed = False
                        state.stopped_because = redact(str(exc))
                        break
                    except ProviderError as exc:
                        state.failures.append(
                            {
                                "game_id": event.game_id,
                                "what": "historical event odds",
                                "markets_fingerprint": markets_fingerprint(
                                    tuple(chunk)
                                ),
                                "keys": list(chunk),
                                "error": redact(str(exc)),
                            }
                        )
                        continue
                    state.responses_bought += 1
                    charged = state.spend.credits_spent - before
                    state.worst_overrun = max(state.worst_overrun, charged - bound)
                    _write_cache(path, payload)
                    if not measured_total_ok(f"event {event.game_id}"):
                        break
                    try:
                        check_quota(f"event {event.game_id}")
                    except QuotaExhausted as exc:
                        stop_on_quota(exc)
                        break
                else:
                    state.responses_from_cache += 1
                staged, census = stage_event(
                    payload if isinstance(payload, Mapping) else {},
                    event=event,
                    window=plan.window,
                    provider_event_id=provider_event_id,
                )
                event_rows.extend(staged)
                for reason_, count in census.items():
                    state.note(reason_, count)

            state.rows.extend(event_rows)
            segment_record["rows_staged"] += len(event_rows)
            if served_entirely_from_cache:
                state.cached_events.append(event)
                segment_record["events_from_cache"] += 1
            else:
                state.bought_events.append(event)
                segment_record["events_bought"] += 1

        segment_record["credits_spent_here"] = (
            state.spend.credits_spent - credits_at_segment_start
        )
        state.per_segment.append(segment_record)

    # WHAT THE RUN NEVER REACHED, NAMED.
    #
    # A run that stops early simply ends its loop, and every segment after the
    # stop then vanishes from `per_segment` — so the report's segment table
    # ends where the credits did, with nothing on the page saying that the rows
    # below it were ever planned. That is how "we stopped asking" turns into
    # "the provider had nothing": the absence looks like the plan, not like the
    # budget. These are recorded as unreached, are in no denominator, and carry
    # no census reason of their own.
    recorded = {(str(s["wave"]), int(s["season"])) for s in state.per_segment}
    for segment in plan.segments:
        if (segment.wave, int(segment.season)) in recorded:
            continue
        state.unreached_segments.append({**segment.to_json(), "not_reached": True})

    return build_record(
        competition=competition,
        plan=plan,
        state=state,
        credit_cap=int(credit_cap),
        chunk_size=int(chunk_size),
        regions=provider.regions,
        sport_key=provider.sport_key,
        generated_at=generated_at,
        population_by_season=population_by_season or {},
        live=True,
    )


def build_record(
    *,
    competition: Competition,
    plan: PurchasePlan,
    state: BuyState,
    credit_cap: int,
    chunk_size: int,
    regions: str,
    sport_key: str,
    generated_at: str,
    population_by_season: Mapping[int, Sequence[RP.ProbeEvent]],
    live: bool,
) -> dict:
    """Everything the report will ever need, in one JSON-safe dictionary."""
    population: list[RP.ProbeEvent] = []
    for season in sorted(population_by_season):
        population.extend(population_by_season[season])
    # Events reached this run, whether the answer was bought or already cached:
    # the achieved stratification is a statement about the prices now in hand,
    # not about the credits this particular run spent.
    reached = list(state.bought_events) + list(state.cached_events)
    stratification = achieved_stratification(reached, population)

    return {
        "schema_version": RECORD_SCHEMA_VERSION,
        "generated_at": str(generated_at),
        "competition": competition.key,
        "competition_title": competition.title,
        "sport_key": str(sport_key),
        "regions": str(regions),
        "live": bool(live),
        "completed": bool(state.completed),
        "stopped_because": str(state.stopped_because),
        # THE SCHEMA VERSION DELIBERATELY DID NOT MOVE FOR THESE KEYS.
        #
        # Every one of them is absent from a record written before the quota
        # breaker existed, and `render` reads each with a `False`/`0`/`None`
        # default. That default is not a guess: no record written before the
        # breaker could have stopped on quota, because nothing measured it. So
        # an old record renders exactly as truthfully as it did, and bumping
        # the version would only make the committed record unrenderable.
        "stopped_on_quota": bool(state.stopped_on_quota),
        "quota_floor": int(state.quota_floor),
        "quota_ever_reported": bool(state.quota_ever_reported),
        "quota_unwatched_responses": int(state.quota_unwatched_responses),
        "quota_last_measured": (
            None if state.quota_last_measured is None else int(state.quota_last_measured)
        ),
        "unreached_segments": [dict(s) for s in state.unreached_segments],
        "zero_billed_responses": int(state.spend.zero_billed_responses),
        "fallback_charges": {
            str(k): int(v) for k, v in sorted(state.spend.fallback_charges.items())
        },
        "window": plan.window.name,
        "window_minutes_before_tip": int(plan.window.minutes_before_tip),
        "window_why": plan.window.why,
        "seed": int(plan.seed),
        "chunk_size": int(chunk_size),
        "credit_cap": int(credit_cap),
        "pessimistic_bound": int(plan.pessimistic_bound),
        "credits_spent": int(state.spend.credits_spent),
        "credits_estimated": int(state.spend.credits_estimated),
        "requests_made": int(state.spend.requests_made),
        "responses_bought": int(state.responses_bought),
        "responses_from_cache": int(state.responses_from_cache),
        "worst_single_response_overrun": int(state.worst_overrun),
        # What the LAST response reported, which is empty when it reported
        # nothing — not the last figure the run ever saw. See `Spend`.
        "quota_remaining": str(state.spend.quota_remaining),
        "quota_remaining_last_reported": str(
            state.spend.quota_remaining_last_reported
        ),
        "responses_since_quota_reported": int(
            state.spend.responses_since_quota_reported
        ),
        "spend_notes": list(state.spend.notes),
        "waves": [
            {
                "name": w.name,
                "order": w.order,
                "title": w.title,
                "tiers": list(w.tiers),
                "seasons": list(w.seasons),
                "why": w.why,
                "blocked_reason": w.blocked_reason,
            }
            for w in WAVES
        ],
        "plan": plan.to_json(),
        "segments": [dict(s) for s in state.per_segment],
        "events_reached": len(reached),
        "events_bought": len(state.bought_events),
        "events_from_cache": len(state.cached_events),
        "population_events": len(population),
        "rows_staged": len(state.rows),
        "staging_census": {k: int(v) for k, v in sorted(state.census.items())},
        "unmatched_events": [dict(u) for u in state.unmatched],
        "request_failures": [dict(f) for f in state.failures],
        "achieved_stratification": stratification,
        "worst_share_deviation": round(worst_deviation(stratification), 4),
        "cutoffs": {
            "featured_from": FEATURED_HISTORY_FROM,
            "everything_else_from": ADDITIONAL_HISTORY_FROM,
            "full_catalogue_seasons": list(FULL_CATALOGUE_SEASONS),
            "featured_seasons": list(FEATURED_SEASONS),
        },
    }


def dry_run_record(
    *,
    competition: Competition,
    plan: PurchasePlan,
    credit_cap: int,
    chunk_size: int,
    regions: str,
    sport_key: str,
    population_by_season: Mapping[int, Sequence[RP.ProbeEvent]],
    generated_at: str = "",
) -> dict:
    """The same record shape with nothing bought in it. Spends nothing."""
    return build_record(
        competition=competition,
        plan=plan,
        state=BuyState(
            completed=False,
            stopped_because="This was a dry run. Nothing was requested.",
        ),
        credit_cap=int(credit_cap),
        chunk_size=int(chunk_size),
        regions=regions,
        sport_key=sport_key,
        generated_at=generated_at,
        population_by_season=population_by_season,
        live=False,
    )


# ---------------------------------------------------------------------------
# The report — a pure function of the record
# ---------------------------------------------------------------------------


def _pct(value: float) -> str:
    return f"{100.0 * float(value):.1f}%"


def render(record: Mapping) -> str:
    """The markdown report, computed only from the run record.

    No clock, no network, no randomness: the same record renders to the same
    bytes for ever.
    """
    version = int(record.get("schema_version", 0))
    if version != RECORD_SCHEMA_VERSION:
        raise PurchaseError(
            f"This run record is schema version {version} and this renderer "
            f"speaks version {RECORD_SCHEMA_VERSION}. Refusing to render: a "
            "report with silently missing sections is worse than no report."
        )

    out: list[str] = []
    add = out.append
    add(f"# Historical price purchase — {record.get('competition_title','')}")
    add("")
    add(
        "The pessimistic full-catalogue buy is far larger than one month's "
        "authorisation, so this purchase is **bought in priority order and "
        "resumed across months**: core team markets across every season first, "
        "then ladders and halves, then props, then futures."
    )
    add("")
    add(
        "**A partial purchase is a sample, not a prefix.** Events are bought in "
        "an order whose every prefix is spread proportionally across "
        "conference tier, month of the season and tip window — because book "
        "coverage differs on all three and this lab's thesis is about the "
        "low-major end, which is precisely what a naive order starves. The "
        "achieved shape is measured below rather than asserted."
    )
    add("")

    # -- what this run was, and what it cost --------------------------------
    live = bool(record.get("live"))
    completed = bool(record.get("completed"))
    add("## What this run was, and what it cost")
    add("")
    add("| | |")
    add("|---|---|")
    add(f"| Generated | {record.get('generated_at') or 'unrecorded'} |")
    add(f"| Sport key | `{record.get('sport_key','')}` |")
    add(f"| Regions | `{record.get('regions','')}` |")
    add(
        f"| Snapshot window | **{record.get('window','')}**, "
        f"{int(record.get('window_minutes_before_tip', 0))} minutes before tip |"
    )
    add(f"| Event order seed | {int(record.get('seed', 0))} |")
    add(f"| Credit cap | **{int(record.get('credit_cap', 0)):,}** |")
    add(
        f"| Pessimistic bound of the plan | "
        f"{int(record.get('pessimistic_bound', 0)):,} |"
    )
    add(f"| Credits actually spent | **{int(record.get('credits_spent', 0)):,}** |")
    add(f"| Requests made | {int(record.get('requests_made', 0)):,} |")
    add(f"| Responses bought | {int(record.get('responses_bought', 0)):,} |")
    add(
        f"| Responses served from cache (free) | "
        f"{int(record.get('responses_from_cache', 0)):,} |"
    )
    # "The provider billed nothing for this response" is a measurement and it
    # is printed as one. Folded into the total it is invisible, and a run whose
    # responses mostly billed zero reads as a cheap run rather than as a run
    # that mostly came back empty — two different things with the same total.
    #
    # A record written before that count existed says so rather than printing
    # `0`, which would assert that none of its responses billed zero. Under the
    # old code every such response was charged the pessimistic bound and left
    # no trace, so `0` is exactly the thing nobody can know about those runs.
    if not live:
        zero_billed_text = "not applicable: nothing was requested"
    elif "zero_billed_responses" in record:
        zero_billed_text = f"{int(record['zero_billed_responses']):,}"
    else:
        zero_billed_text = "unrecorded: this record predates the count"
    add(f"| Responses the provider billed at zero | {zero_billed_text} |")
    # WHAT THE BALANCE BREAKER ACTUALLY SAW, DECIDED ONCE AND READ EVERYWHERE.
    #
    # Three states, not two. `quota_ever_reported` alone cannot tell a run the
    # breaker watched from end to end apart from one where the provider sent a
    # balance on its first response and then stopped while the account drained
    # — and that second run is the dangerous one, because a True flag reads as
    # the safe answer. `quota_unwatched_responses` counts the looks the breaker
    # could not make. Only a run with a breaker, a reported balance, and zero
    # unwatched looks was watched throughout, and only that run may have an
    # absence below described as a fact about the archive.
    #
    # Every one of these keys is absent from a record written before the
    # breaker existed, and each default here fails CLOSED: no breaker, not
    # watched, nothing claimed.
    breaker_ran = live and "quota_floor" in record
    quota_ever_reported = bool(record.get("quota_ever_reported"))
    quota_unwatched = int(record.get("quota_unwatched_responses", 0))
    quota_watched_throughout = (
        breaker_ran
        and quota_ever_reported
        and "quota_unwatched_responses" in record
        and quota_unwatched == 0
    )

    # A balance is only stated as the balance AFTERWARDS when the last response
    # of the run actually carried one. Otherwise the last figure the provider
    # gave is printed as exactly that, with its age.
    current_quota = str(record.get("quota_remaining", "")).strip()
    last_quota = str(record.get("quota_remaining_last_reported", "")).strip()
    if current_quota:
        quota_text = current_quota
    elif last_quota:
        quota_text = (
            f"not reported on the last response; **{last_quota}** as of "
            f"{int(record.get('responses_since_quota_reported', 0)):,} "
            "response(s) before the end, which is the last figure the provider "
            "gave and not the balance the run finished on"
        )
    else:
        quota_text = "unrecorded"
    add(f"| Quota remaining afterwards | {quota_text} |")
    # A record written before the balance breaker existed carries no floor. It
    # says so rather than printing `0`, which would read as a floor of zero —
    # a breaker that can never fire — rather than as no breaker at all.
    if not live:
        floor_text = "not applicable: nothing was requested"
    elif "quota_floor" in record:
        floor_text = f"{int(record['quota_floor']):,}"
    else:
        floor_text = "none: this record predates the balance circuit-breaker"
    add(f"| Account balance floor this run watched | {floor_text} |")
    add(f"| Run completed | **{'yes' if completed else 'no'}** |")
    # The same treatment the two rows above get, and for the same reason. A
    # flat **no** on a record that predates the breaker reads as a measured
    # all-clear over a run in which nothing was measured — which is the exact
    # shape of the defect this row was added to prevent, printed by the row
    # itself, two lines under a floor that says no breaker existed.
    if not live:
        stopped_text = "not applicable: nothing was requested"
    elif "stopped_on_quota" in record:
        stopped_text = "**yes**" if record.get("stopped_on_quota") else "**no**"
    else:
        stopped_text = "unrecorded: this record predates the balance circuit-breaker"
    add(f"| **Stopped on quota** | {stopped_text} |")
    add("")
    fallbacks = record.get("fallback_charges") or {}
    if fallbacks:
        add(
            "**"
            + ", ".join(
                f"{int(count):,} response(s) with a(n) {name} `x-requests-last`"
                for name, count in sorted(fallbacks.items())
            )
            + "** were charged the pessimistic bound rather than a measured "
            "cost. The three are counted apart because they are three different "
            "faults: an absent header is the provider or a proxy changing, an "
            "unreadable one is an assumption of ours breaking, and a negative "
            "one is the provider itself. A response that reported **0** is not "
            "in this count — zero is an answer, and it is charged as zero."
        )
        add("")
    add(f"{record.get('window_why','')}")
    add("")

    overrun = int(record.get("worst_single_response_overrun", 0))
    if overrun > 0:
        add(
            f"> **A response billed {overrun:,} credits more than its own "
            "pessimistic bound.** That is the NHL lab's defect happening in "
            "the open: it capped a run at 200,000 and spent 289,984 because it "
            "estimated from markets *asked* while the provider bills per market "
            "*returned*. The cap here is re-checked against the measured "
            "running total after every response, so the run stops rather than "
            "drifting — but the overrun is printed rather than absorbed."
        )
        add("")
    if not live:
        add(
            "**This record is a dry run.** No request was made, no credential "
            "was read, and nothing was bought. Every count below is zero, which "
            "is the correct answer for a run that asked nothing."
        )
        add("")
    elif record.get("stopped_on_quota"):
        # THE ONE CASE THAT MUST NOT READ AS "the ordinary case". Stopping at
        # this run's own cap leaves markets unbought; running the ACCOUNT out
        # leaves markets unanswered, and an unanswered market is what a census
        # cannot tell apart from a market the archive does not hold.
        add(
            "> # STOPPED ON QUOTA"
        )
        add(
            f"> {record.get('stopped_because') or 'The account ran out of credits.'}"
        )
        add(
            "> **This is not the ordinary partial buy.** A run that stops at "
            "its own credit cap has bought less than it planned to; a run that "
            "stops because the ACCOUNT is empty has also stopped getting "
            "answers. Once the balance is gone the provider returns no quotes, "
            "those responses stage no rows, and the census reason they land "
            "under is indistinguishable from the provider not retaining the "
            "market. **Nothing below may be read as a statement about what the "
            "archive holds.** Top the balance up and re-run to resume; nothing "
            "already cached is bought twice."
        )
        add("")
    elif not completed:
        add(
            "> **This run did not complete.** "
            f"{record.get('stopped_because') or 'It stopped early.'} That is "
            "the ordinary case for this purchase and not a fault: it is bigger "
            "than one month's credits by design. **What it bought is still a "
            "proportional sample of the wave**, because the event order makes "
            "every prefix one — see the stratification table below, which "
            "measures that rather than assuming it. Re-run to resume; nothing "
            "already cached is bought twice."
        )
        add("")
    elif quota_watched_throughout:
        # THE ONLY BRANCH ALLOWED TO SAY "ABSENT FROM THE ARCHIVE".
        #
        # It is a claim about the provider built on a claim about our balance,
        # and it is only true when the balance was actually measured — on every
        # response, not on one of them. This sentence used to be printed for
        # every completed run, including a run in which the breaker never read
        # a single balance, with the "nothing to watch" paragraph appended
        # three lines below it and never retracting it. Two contradictory
        # statements about the same absence, and the false one first and in the
        # summary voice.
        add(
            "The run completed inside its cap, and the account's balance was "
            "measured on every response and stayed above this run's floor "
            "throughout. Anything absent below is absent from the archive "
            "rather than absent from the budget — but only for the segments "
            "the plan actually contained, which are listed in full."
        )
        add("")
    else:
        add(
            "The run completed inside its cap and bought every segment the "
            "plan contained. **What is absent below cannot be attributed to "
            "the archive**, because the account's balance was not measured "
            "throughout this run — see the note immediately below — and an "
            "unanswered request and an unretained market look identical here."
        )
        add("")
    if live and not breaker_ran:
        # Not "the breaker had nothing to watch": there was no breaker. A
        # report that describes a mechanism which did not exist at the time is
        # inventing the run's own history.
        add(
            "> **This record predates the balance circuit-breaker.** Nothing "
            "read `x-requests-remaining` during this run, so nothing would "
            "have stopped it had the account emptied part-way through. That is "
            "not a measurement that the balance was healthy; it is the absence "
            "of one, and no quota figure has been assumed in its place."
        )
        add("")
    elif breaker_ran and not quota_ever_reported:
        # An unwatched breaker is not a clean bill of health, and a report that
        # stays silent here lets the absence of a stop read as one.
        add(
            "> **The provider reported no remaining account quota on any "
            "response in this run, so the balance circuit-breaker had nothing "
            "to watch.** That is not a measurement that the balance was "
            "healthy; it is the absence of one. No quota figure has been "
            "assumed in its place."
        )
        add("")
    elif breaker_ran and not quota_watched_throughout:
        # The third state, and the one that reads as the safest while being the
        # worst: a balance arrived, so the breaker looks armed, and then the
        # provider (or a proxy) stopped sending the header while the account
        # drained. The old code carried the first figure forward for ever and
        # compared THAT against the floor on every later response.
        add(
            f"> **The provider stopped reporting a remaining account quota: "
            f"the breaker looked {quota_unwatched:,} time(s) and found no "
            "balance to compare.** It was therefore blind for that part of the "
            "run. The figure in the table above is the last one the provider "
            "gave, not the balance the run ended on, and it is not carried "
            "forward as though it were: a stale balance compared against a "
            "floor is a breaker that cannot fire while reporting that it is "
            "armed. **Nothing below may be read as a statement about what the "
            "archive holds.**"
        )
        add("")
    for note in record.get("spend_notes", []) or []:
        add(f"- {note}")
    if record.get("spend_notes"):
        add("")

    # -- the priority order --------------------------------------------------
    add("## The purchase, in priority order")
    add("")
    add(
        "Cooper's order, and also the order of decreasing confidence that a "
        "market is quoted at all. Every season of a wave is bought before any "
        "of the next wave, so a purchase that runs out of credits holds the "
        "family it is most sure of across every season rather than a little of "
        "everything."
    )
    add("")
    for wave in record.get("waves", []):
        add(
            f"**{int(wave['order'])}. {wave['title']}** (`{wave['name']}`, "
            f"market tier {', '.join(str(t) for t in wave['tiers'])}; seasons "
            f"{', '.join(str(s) for s in wave['seasons'])})"
        )
        add("")
        add(f"{wave['why']}")
        add("")
        if wave.get("blocked_reason"):
            add(f"> **Not bought by this script.** {wave['blocked_reason']}")
            add("")

    add(
        "| Wave | Season | Keys | Events planned | Pessimistic bound | "
        "Events bought | From cache | Credits | Rows staged |"
    )
    add("|:---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for segment in record.get("segments", []):
        note = " ⛔" if segment.get("blocked_reason") else ""
        add(
            f"| `{segment['wave']}`{note} | {int(segment['season'])} | "
            f"{len(segment.get('keys', []))} | "
            f"{int(segment.get('events_planned', 0)):,} | "
            f"{int(segment.get('pessimistic_bound', 0)):,} | "
            f"{int(segment.get('events_bought', 0)):,} | "
            f"{int(segment.get('events_from_cache', 0)):,} | "
            f"{int(segment.get('credits_spent_here', 0)):,} | "
            f"{int(segment.get('rows_staged', 0)):,} |"
        )
    unreached = record.get("unreached_segments", []) or []
    for segment in unreached:
        # Printed in the same table, marked, rather than left off it. A table
        # that simply ends where the run did makes the unbought half of the
        # plan invisible, and an invisible plan row is how "we never asked"
        # reads as "there was nothing to ask for".
        add(
            f"| `{segment['wave']}` ⏹ | {int(segment['season'])} | "
            f"{len(segment.get('keys', []))} | "
            f"{int(segment.get('events_planned', 0)):,} | "
            f"{int(segment.get('pessimistic_bound', 0)):,} | "
            "— | — | — | — |"
        )
    add("")
    if unreached:
        add(
            f"⏹ **{len(unreached)} segment(s) were planned and never reached.** "
            "The run stopped before them. Their markets were **never asked "
            "for**, so they are in no denominator, contribute no census reason, "
            "and establish nothing whatever about what the archive retains — "
            "asking costs nothing and returns nothing, which looks exactly like "
            "a market no book quoted."
        )
        add("")
    blocked = [s for s in record.get("segments", []) if s.get("blocked_reason")]
    if blocked:
        add("⛔ segments that were not asked for, and why:")
        add("")
        for segment in blocked:
            refused = segment.get("keys_refused") or {}
            floors = sorted(set(refused.values()))
            detail = (
                f" {len(refused)} key(s) refused before {', '.join(floors)}."
                if refused
                else ""
            )
            add(
                f"- `{segment['wave']}` / {int(segment['season'])} — "
                f"{segment['blocked_reason']}{detail}"
            )
        add("")
    add(
        f"**The archive's own cut-offs decide what is buyable.** Featured "
        f"markets exist for this sport from "
        f"{record['cutoffs']['featured_from']}; everything else — props, "
        f"halves, every alternate ladder, and `team_totals` — from "
        f"{record['cutoffs']['everything_else_from']}, site-wide. So the full "
        "catalogue is buyable for seasons "
        f"{', '.join(str(s) for s in record['cutoffs']['full_catalogue_seasons'])} "
        "only. A key refused above was **never asked for**: asking costs "
        "nothing and returns nothing, which looks exactly like a market no "
        "book quoted."
    )
    add("")

    # -- the stratification --------------------------------------------------
    add("## The achieved stratification of what was actually bought")
    add("")
    reached = int(record.get("events_reached", 0))
    population = int(record.get("population_events", 0))
    add(
        f"**{reached:,} of {population:,} events in hand** "
        f"({_pct(reached / population) if population else '—'} of the "
        "population the plan was drawn from). Worst share deviation across "
        f"every axis value: **{_pct(record.get('worst_share_deviation', 0.0))}**."
    )
    add("")
    add(
        "This table is the honesty check on rule 1. If the order worked, every "
        "difference is small at every prefix length; if it did not, this is "
        "where that is visible. A purchase that reports itself as stratified "
        "while being anything but is worse than an admittedly biased one, "
        "because every later conclusion inherits the bias and nobody can see it."
    )
    add("")
    add("| Axis | Value | Population | Population share | Bought | Bought share | Difference |")
    add("|:---|:---|---:|---:|---:|---:|---:|")
    for row in record.get("achieved_stratification", []):
        add(
            f"| {row['axis']} | {row['value']} | {int(row['population']):,} | "
            f"{_pct(row['population_share'])} | {int(row['bought']):,} | "
            f"{_pct(row['bought_share'])} | {float(row['difference']):+.1%} |"
        )
    add("")

    # -- what came back ------------------------------------------------------
    add("## What came back")
    add("")
    add(
        f"**{int(record.get('rows_staged', 0)):,} price rows staged** into this "
        "lab's vocabulary from the cached responses. Staging is a pure function "
        "of the cache, so the mapping can be fixed and re-run for ever without "
        "buying anything twice — which at ten times the live rate is the most "
        "valuable property in this module."
    )
    add("")
    census = record.get("staging_census", {}) or {}
    if census:
        add(
            "Every outcome that did not become a row, counted. A quote that "
            "vanishes without appearing here is a defect, not a decision:"
        )
        add("")
        if record.get("stopped_on_quota"):
            # The census counts what the RESPONSES WE RECEIVED contained. When
            # the account emptied mid-run the later responses contained nothing,
            # and the segments after the stop were never requested at all — so
            # neither is evidence about the archive, and the table must not be
            # read as though it were.
            add(
                "> **This run STOPPED ON QUOTA, so this table counts only the "
                "responses the provider was still answering.** The segments "
                "after the stop were never requested and appear in no row of "
                "it. Nothing in this census attributes anything to the "
                "provider's retention, and nothing in it may be quoted as "
                "evidence that a market is not retained."
            )
            add("")
        elif live and not quota_watched_throughout:
            # The same disclaimer for the case that LOOKS fine. A run whose
            # balance was never measured — or measured once and then not again
            # — may have emptied the account part-way through and carried on
            # asking, and every one of those responses is an empty payload in
            # this table under a reason that reads as the provider not
            # retaining the market.
            add(
                "> **The account's balance was not measured throughout this "
                "run, so this census is not evidence about the archive.** An "
                "empty response from an exhausted account and an empty "
                "response from a market the provider does not retain are the "
                "same bytes; only a measured balance tells them apart, and "
                "this run does not have one for every response. Nothing in "
                "this census may be quoted as evidence that a market is not "
                "retained."
            )
            add("")
        add("| Reason | Outcomes |")
        add("|:---|---:|")
        for reason, count in sorted(census.items()):
            add(f"| `{reason}` | {int(count):,} |")
        add("")
    unmatched = record.get("unmatched_events", []) or []
    if unmatched:
        add(
            f"**{len(unmatched)} game(s) could not be matched to a provider "
            "event and are in no denominator anywhere.** A school this lab "
            "cannot spell is not a market the provider does not retain, and "
            "scoring it as a missing price would quietly turn one into the "
            "other."
        )
        add("")
        add("| Game | Date | Tier | Why |")
        add("|:---|:---|:---|:---|")
        for miss in unmatched[:25]:
            add(
                f"| {miss.get('away_name','')} at {miss.get('home_name','')} | "
                f"{miss.get('slate_date','')} | {miss.get('tier','')} | "
                f"{miss.get('reason','')} |"
            )
        add("")
    failures = record.get("request_failures", []) or []
    if failures:
        add(f"**{len(failures)} request(s) failed.** They bought nothing and prove nothing:")
        add("")
        for failure in failures[:20]:
            add(
                f"- {failure.get('what','')} — {failure.get('error','')}"
            )
        add("")

    # -- what this does not establish ---------------------------------------
    add("## What this does not establish")
    add("")
    add(
        "- **Buying a price is not measuring anything.** These rows are an "
        "input to a backtest, and a backtest that beats the number nobody "
        "could still take is not a bet."
    )
    add(
        "- **A market absent from a segment this run did not reach is not a "
        "market the archive lacks.** A starved fetch and an unquoted market "
        "look identical, which is why the cap, the bound, the measured spend, "
        "the completed flag, the account balance floor and the STOPPED ON "
        "QUOTA flag are all above, and why every segment the run never reached "
        "is listed by name rather than left off the table."
    )
    add(
        "- **Nothing here allowlists anything.** No market reaches the card "
        "without a reviewed human acceptance receipt, and player props cannot "
        "produce a selection at all: nothing in this sport reaches "
        "`Availability.CONFIRMED`. That is not a pass, an avoid, or a "
        "no-value call."
    )
    add(
        f"- **One window per store.** This run wrote the "
        f"`{record.get('window','')}` store only. A store holding two windows "
        "would hand a wager the better of a card-time and a near-close price — "
        "a price nobody could have taken."
    )
    return "\n".join(out) + "\n"


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
        raise PurchaseError(f"No run record at {target}.")
    try:
        record = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise PurchaseError(
            f"The run record at {target} could not be read. Refusing to render "
            "a partial report over a good one."
        ) from exc
    if not isinstance(record, dict):
        raise PurchaseError(f"The run record at {target} is not a JSON object.")
    return record


def write_report(record: Mapping, path: Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(record), encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# Rebuilding the store from the cache — no network, no credential, no spend
# ---------------------------------------------------------------------------


def rebuild_from_cache(
    *,
    plan: PurchasePlan,
    cache_dir: Path,
    indexes: Mapping[int, team_names.TeamIndex],
    chunk_size: int = MARKET_CHUNK_SIZE,
    segments: Sequence[PlanSegment] | None = None,
) -> tuple[list[dict], dict[str, int], list[RP.ProbeEvent]]:
    """Re-stage cached responses for a plan, or for some of its segments.

    **Touches no network.** This is rule 4's payoff: the vocabulary mapping can
    be corrected, extended or argued about for ever, and re-running it costs
    nothing. Returns the rows, the census, and the events that had at least one
    cached response.

    **`segments` exists because holding a whole wave in memory killed a
    runner.** Every staged row is a Python dict, and a 1.2M-credit wave stages
    4.8M of them; rebuilding that in one call on a 7GB runner was OOM-killed
    two minutes in, and because persistence sat after the rebuild, the run's
    responses were lost with it. Callers stream one segment at a time — a
    wave-season, a few hundred thousand rows — and append each before touching
    the next, so peak memory is one segment and not the plan.
    """
    cache_root = Path(cache_dir)
    rows: list[dict] = []
    census: dict[str, int] = {}
    reached: list[RP.ProbeEvent] = []
    listings: dict[str, list[dict]] = {}

    chosen = list(segments) if segments is not None else list(plan.segments)
    for segment in chosen:
        if not segment.buyable:
            continue
        index = indexes.get(int(segment.season))
        if index is None:
            continue
        chunks = RP.market_chunks(segment.keys, size=chunk_size)
        for event in segment.events:
            listing = listings.get(event.snapshot)
            if listing is None:
                cached = _read_cache(
                    slate_cache_path(cache_root, event.snapshot), use_cache=True
                )
                listing = [x for x in (cached or []) if isinstance(x, dict)]
                listings[event.snapshot] = listing
            provider_event_id, _reason = RP.match_provider_event(listing, event, index)
            if not provider_event_id:
                continue
            found = False
            for chunk in chunks:
                payload = _read_cache(
                    cache_path(cache_root, event, chunk), use_cache=True
                )
                if payload is None:
                    continue
                found = True
                staged, part = stage_event(
                    payload if isinstance(payload, Mapping) else {},
                    event=event,
                    window=plan.window,
                    provider_event_id=provider_event_id,
                )
                rows.extend(staged)
                for reason, count in part.items():
                    census[reason] = census.get(reason, 0) + count
            if found:
                reached.append(event)
    return rows, census, reached


@dataclass(frozen=True)
class RebuildResult:
    """What a completed rebuild replaced, and with what."""

    target: Path
    #: Rows the previous store held, counted BEFORE anything touched it.
    #: `None` only when the previous store could not be read at all and the
    #: operator opted out in writing — in which case there is no floor and the
    #: anti-shrink guard did not run.
    previous_rows: int | None
    rows_staged: int
    rows_held: int
    events_reached: int
    segments_rebuilt: int
    census: dict[str, int]
    shrink_allowed_because: str = ""
    #: Set only when the operator opted out of the unreadable-store refusal in
    #: writing. When it is set, `previous_rows` is `None` and NO floor ran:
    #: the shrink comparison needs a previous count and there was not one.
    unreadable_store_allowed_because: str = ""


def rebuild_store(
    *,
    plan: PurchasePlan,
    cache_dir: Path,
    indexes: Mapping[int, team_names.TeamIndex],
    processed_dir: Path,
    competition: Competition = CBB,
    chunk_size: int = MARKET_CHUNK_SIZE,
    allow_shrink_reason: str = "",
    allow_unreadable_store_reason: str = "",
    on_segment: Callable[[PlanSegment, int, int, int], None] | None = None,
) -> RebuildResult:
    """Re-derive the price store from the raw cache, and only then replace it.

    BUILD BESIDE, VERIFY, THEN REPLACE — never unlink first.

    The previous version of this deleted the target and *then* staged rows into
    the empty path one segment at a time. Everything about that is defensible
    except the order, and the order is what made two guards unable to fire:

    * `stores.append` refuses to write fewer rows than it read. With the target
      already deleted it always read **zero**, so the anti-shrink guard compared
      every rebuild against nothing and could never refuse one. The comment over
      that unlink explained that the store had once shrunk from 2.9M rows to
      2.3M — which is precisely the event a shrink guard exists to catch, and
      deleting first guaranteed it could not.
    * a rebuild that staged nothing at all — an empty cache, or every cached
      response failing to stage — printed a warning and **returned 0**. A green
      exit over a destroyed store: the caller saw success, CI saw success, and
      the store was gone.

    So: the previous store's rows are counted first, the rebuild is assembled
    into a scratch path beside the target, and the target is replaced only once
    the result is verified non-empty and no smaller than what it replaces. Every
    refusal leaves the original store exactly where it was.

    TWO GUARDS, TWO OPT-OUTS. `allow_shrink_reason` permits a rebuild that
    holds fewer rows than the store it replaces — a MEASURED shrink, where both
    counts are known and the operator has decided the loss is intended.
    `allow_unreadable_store_reason` permits a rebuild over a store that cannot
    be counted at all, where no floor exists and therefore no shrink guard can
    run. These used to share one flag, so the reason an operator wrote about
    fifteen duplicate rows also disarmed the refusal over an unreadable store
    and, through `previous_rows = None`, the shrink comparison itself. Each is
    an explicit written reason rather than a bare flag, and an empty reason is
    no opt-out.

    The rebuild still derives FROM THE CACHE AND NOT FROM THE STORE, which is
    the property the unlink was reaching for: the scratch path starts empty, so
    nothing a stale restored store happens to hold is carried forward. And it
    still streams one segment at a time, because holding a 4.8M-row wave in
    memory as Python dicts OOM-killed a runner and took 1,199,926 credits of
    unsaved responses with it.
    """
    target = store_path(competition, Path(processed_dir), plan.window)
    previous_rows: int | None
    try:
        # `for_append=True` on purpose: a store that cannot be read is a store
        # whose row count is unknown, and an unknown floor is no floor. Reading
        # it leniently here would hand the shrink guard a zero and make it
        # unable to fire for the second time in this function's history.
        previous_rows = len(
            stores.read_store(target, columns=PRICE_COLUMNS, for_append=True)
        )
    except stores.CorruptStoreError as exc:
        # ITS OWN OPT-OUT, NOT THE SHRINK GUARD'S.
        #
        # This used to read `if not allow_shrink_reason`, so the flag whose
        # help text is entirely about permitting a SHRINK also switched off the
        # refusal to rebuild over a store nobody could count — and switching it
        # off sets `previous_rows = None`, which makes the shrink comparison
        # below (`previous_rows is not None and ...`) skip as well. One written
        # reason about fifteen duplicate rows, and a 12,000-row rebuild could
        # replace a 2.9M-row store with no floor having run at all. Two guards
        # with two different failure modes get two different opt-outs.
        if not allow_unreadable_store_reason:
            raise PurchaseError(
                f"{target} exists but could not be read, so this rebuild cannot "
                "count what it would be replacing and the anti-shrink guard has "
                "no floor to compare against. Refusing, and leaving the file "
                "exactly where it is. Pass an explicit written reason to "
                "`--allow-unreadable-store-reason` to override — a guard whose "
                "floor is unknown must not silently default to zero, and "
                "`--allow-shrink-reason` deliberately does NOT override this: "
                "permitting a measured shrink and permitting an unmeasurable "
                "one are different decisions."
            ) from exc
        previous_rows = None

    scratch = target.with_name(target.name + ".rebuilding")
    scratch.parent.mkdir(parents=True, exist_ok=True)
    scratch.unlink(missing_ok=True)

    rows_staged = 0
    rows_held = 0
    events_reached = 0
    segments_rebuilt = 0
    census: dict[str, int] = {}
    try:
        for segment in plan.segments:
            if not segment.buyable:
                continue
            rows, part, reached = rebuild_from_cache(
                plan=plan,
                cache_dir=cache_dir,
                indexes=indexes,
                chunk_size=chunk_size,
                segments=[segment],
            )
            rows_held = append_prices(rows, scratch, window=plan.window)
            rows_staged += len(rows)
            events_reached += len(reached)
            segments_rebuilt += 1
            for reason, count in part.items():
                census[reason] = census.get(reason, 0) + count
            if on_segment is not None:
                on_segment(segment, len(rows), len(reached), rows_held)
            del rows

        if rows_staged == 0:
            raise PurchaseError(
                "The rebuild staged **zero** price rows, so there is nothing to "
                f"replace {target.name} with. Either the cache under "
                f"{Path(cache_dir)} is empty, or every response in it failed to "
                "stage — two different faults, told apart by the census "
                f"({len(census)} reason(s) counted: an empty census means an "
                "empty cache). Refusing, and leaving the existing store "
                "untouched: a rebuild that produces nothing must not be the "
                "thing that destroys what it was rebuilding."
            )
        if (
            previous_rows is not None
            and rows_held < previous_rows
            and not allow_shrink_reason
        ):
            raise PurchaseError(
                f"The rebuild holds {rows_held:,} rows against the "
                f"{previous_rows:,} the existing {target.name} already holds. "
                "Refusing, and leaving the existing store untouched. This store "
                "is append-only and cannot be re-bought — the prices it settled "
                "against are gone — and this is exactly the event that took it "
                "from 2.9M rows to 2.3M the last time. If the shrink is "
                "intended, re-run with an explicit written reason."
            )
    except BaseException:
        # Every failure path, not only the two refusals above: a KeyboardInterrupt
        # or an OOM part-way through must not leave a half-built scratch file
        # beside the store for the next run to mistake for anything.
        scratch.unlink(missing_ok=True)
        raise

    # One atomic rename. Until this line the original store is the store.
    scratch.replace(target)
    return RebuildResult(
        target=target,
        previous_rows=previous_rows,
        rows_staged=rows_staged,
        rows_held=rows_held,
        events_reached=events_reached,
        segments_rebuilt=segments_rebuilt,
        census=census,
        shrink_allowed_because=str(allow_shrink_reason),
        unreadable_store_allowed_because=str(allow_unreadable_store_reason),
    )


# ---------------------------------------------------------------------------
# Loading the population
# ---------------------------------------------------------------------------


def load_events(
    *,
    seasons: Sequence[int],
    processed_dir: Path,
    raw_dir: Path,
    competition: Competition = CBB,
    window: SnapshotWindow = CARD_WINDOW,
) -> tuple[dict[int, list[RP.ProbeEvent]], dict[int, team_names.TeamIndex], dict[int, dict]]:
    """The countable games of each season, placed in a cell, plus a name index.

    Delegates to `reports.retention_probe.load_inputs` and
    `reports.retention_probe.candidate_events` rather than re-deriving either.
    The purchase and the probe disagreeing about which games count, or about
    which tier a game is in, would make every coverage number the probe
    produced inapplicable to the prices this module buys — and neither side
    would look wrong.
    """
    events: dict[int, list[RP.ProbeEvent]] = {}
    indexes: dict[int, team_names.TeamIndex] = {}
    censuses: dict[int, dict] = {}
    for season in sorted({int(s) for s in seasons}):
        team_games, schedule, tiers, index = RP.load_inputs(
            processed_dir=Path(processed_dir),
            raw_dir=Path(raw_dir),
            competition=competition,
            season=season,
        )
        candidates, census = RP.candidate_events(
            team_games,
            schedule,
            tiers,
            competition=competition,
            season=season,
            minutes_before_tip=window.minutes_before_tip,
        )
        events[season] = list(candidates)
        indexes[season] = index
        censuses[season] = census
    return events, indexes, censuses


def tier_counts(events: Sequence[RP.ProbeEvent]) -> dict[str, int]:
    counts: dict[str, int] = {t.value: 0 for t in Tier}
    for event in events:
        counts[str(event.tier)] = counts.get(str(event.tier), 0) + 1
    return {k: v for k, v in sorted(counts.items()) if v}
