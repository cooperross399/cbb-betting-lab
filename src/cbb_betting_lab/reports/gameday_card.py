"""The card, and every gate that stands between a price and a stake.

`card_pricing.py` computes edges and cannot decide anything. This module decides
everything and computes no edge. That split is deliberate and it is stated at
both ends, because **a gate reachable by two paths is a gate with a bypass, and
the bypass is always the pricing path** — pricing is where the interesting code
is and where a convenience shortcut looks harmless.

So this file holds: the board fetch, the placement of a game in a tier, the
model's opinion or its refusal to have one, the four gates that fail closed, the
freeze, the accounting identity, and the prose. It imports `expected_value` from
nowhere: it never computes an edge itself.

## What this card is, today and on purpose

**No market is allowlisted.** `staging_provider_policy.py` has `withdraw()` and
does not have `grant()`, so the only way a market reaches this card is a
reviewed acceptance receipt Cooper signs. Until then every priced wager is
stopped at the first bar, and the card produces **no selection, no lean, no pass
and no stake** and says why in the gate's own words.

That is the correct output. It is not a degraded run, it is not an empty slate,
and it is not the model declining to find value. An excluded market is **never**
reported as a pass, an avoid, or a no-value call — the card carries
:data:`ACCUMULATING_NOTE` above everything else so a reader who stops after one
line has still read the true thing.

## The accounting identity, printed every run and raised on rather than warned

    priced = no_opinion + below_threshold + unparseable + ambiguous + gated + bets

Reconciled every run by :func:`reconcile`, which **raises** when it does not
balance. A wager that reaches none of the buckets vanished silently, and a
silent drop is how a card recommends from a sixth of a slate and reports it as
the whole one.

Its unit needs stating, because it is not one unit. `priced` counts **wagers
plus the price rows that could not be made into wagers**. Those are different
sizes — a wager may carry twenty books' quotes and an unreadable row carries one
— and they are added anyway, because the alternative is worse. Counting in rows
would force a selection to be worth `len(quotes)` bets, which is precisely the
NHL lab's √2.83 interval defect written into the card; counting in wagers alone
would drop `unparseable` out of the identity, and the identity exists to make
the unreadable rows impossible to lose. So the mixture is deliberate, it is
stated here, and both figures are printed separately on the card as well as
summed.

:data:`BAR_BUCKETS` maps each of `card_pricing.Bar`'s eight values onto exactly
one bucket, as data, so the test that pins the mapping reads the same table the
code does rather than a copy of it.

## The tip guard runs continuously, and this sport is why

The sibling labs check one kickoff or one puck drop. **D-I men's basketball tips
games every fifteen minutes for twelve hours** — 11:00 ET to 23:00 ET, 45.3% of
6,318 games in 2025-26 still untipped at 19:00 ET — so a single deadline is
meaningless here. :class:`TipGuard` judges each wager against **its own** tip,
and it judges twice: once when the bars are applied, and again immediately
before the card is written, against a freshly read clock. The second pass is not
belt and braces. Fetching a 200-game slate per event takes minutes, and a game
that was upcoming when its price was read can have tipped by the time the card
renders. Anything that has crossed the line in between is quarantined and **its
stake is removed** — counted into `gated`, never quietly dropped.

## The first opinion of the day is never retroactively replaced

Two cards a day is only safe under that rule, and without it two cards a day is
two bites at the same apple: the evening run would re-price the games the
morning run got wrong and the ledger would record the better of two guesses.
`forward_evidence.write_snapshot` enforces it by keying on the frozen selection
key and appending only what is not already there; this module's job is to hand
it **the same `key_for` the probability map was built with**, which it does by
construction — `card_pricing.default_key_for(competition)` is built once in
:func:`run_card` and passed to both.

### One row per wager, at the best price, and why the caller has to do that

`write_snapshot` dedupes on the selection key, and the selection key does not
carry the book. Hand it every book's quote and it freezes **whichever row
arrived first**, which is bookmaker order in the provider's response — an
arbitrary book, not the price the card would have taken. So this module collapses
to one row per wager at the best price with `stores.best_price_per_wager` before
freezing, which is the same collapse `card_pricing.select` makes when it takes
the best price last. The full board, every book, is written to `data/staging/`
where the line-shopping and price-survival evidence needs it. See the report
accompanying this module for the defect note.

## The prior's weight is reported in every November price, and gates one

Cooper: *"report the prior's weight in every price so the card can never present
a November number as if it were a February one."* November is a prior, not a
fit: the win/loss graph is nearly disconnected between conferences, so an
adjusted rating in the first weeks is identified almost entirely by the
preseason prior.

This card enforces that rather than only printing it. Inside
:data:`PRIOR_REGIME_MONTHS` a game whose rating carries **no recorded prior
weight** gets no opinion at all, counted under its own reason. A blank prior
weight is not zero — zero is the substantive claim that none of the price came
from the prior — and manufacturing that claim for a game in November is exactly
the misreading the rule exists to prevent.

## Correlation is counted, never summed

A game's spread, its moneyline, both team totals, the game total and a starter's
points are one event seen six ways. `card_pricing` caps exposure at one position
per game and twenty per slate, both declared in advance; this module prints the
exposure and **never prints a total edge, a combined stake or a sum of edges**.
There is a test that greps the rendered card for one.

## Zero email, and it takes two changes rather than one

The card comment **mentions nobody**. An `@mention` overrides an ignored
repository subscription, so the EPL lab kept emailing Cooper after he set the
subscription to ignored, because the comment still mentioned him.
:func:`guard_mentions_nobody` runs the workflow's own regex over the comment and
**raises** rather than scrubbing: mangling a school's name to remove an `@`
would fabricate a name, and this lab does not fabricate names. The freeze
happens before the render, so a card that refuses to render still leaves the
evidence — which is what makes raising here cheap.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from pathlib import Path
from types import SimpleNamespace
from typing import Protocol

import pandas as pd

from cbb_betting_lab import forward_evidence, stores, verdicts
from cbb_betting_lab.data import hoopr
from cbb_betting_lab.competitions import Competition
from cbb_betting_lab.conferences import Tier, TierTable, tier_table
from cbb_betting_lab.gates import (
    AccountingIdentity,
    Availability,
    TipState,
    availability_note,
    can_be_played,
    IMMINENT_MINUTES,
    imminent_note,
    tip_state,
)
from cbb_betting_lab.markets import FUTURES, MARKETS_BY_KEY, PLAYER, per_event_provider_keys
from cbb_betting_lab.models import distributions, player_census, player_rates, slate
from cbb_betting_lab.population import VenueState
from cbb_betting_lab.providers import staging, team_names
from cbb_betting_lab.providers.odds_api import (
    BULK_SAFE_MARKETS,
    CreditCapReached,
    OddsApiProvider,
    ProviderError,
    Spend,
)
from cbb_betting_lab.reports.card_pricing import (
    BAR_ORDER,
    EDGE_THRESHOLD,
    PRICE_BAND,
    Bar,
    SelectionResult,
    Wager,
    build_wagers,
    default_key_for,
    select,
    selection_fingerprint,
)
from cbb_betting_lab.reports.retention_probe import game_tier
from cbb_betting_lab.season import clean_text, season_for_slate_date, slate_date
from cbb_betting_lab.selection import (
    AWAY,
    FULL_GAME,
    HOME,
    OVER,
    UNDER,
    normalise_line,
)
from cbb_betting_lab.staging_provider_policy import StagingProviderPolicy
from cbb_betting_lab.staging_provider_policy import load as load_policy


#: The exact sentence CLAUDE.md pins as a contract string. Matched literally by
#: `tests/test_contract_strings.py`, so it is written once, here, and every
#: rendering path reads it rather than retyping it.
ACCUMULATING_NOTE = (
    "This card is **accumulating evidence, not making recommendations.**"
)

#: The marker Cooper's automation greps for when the card's advice has moved.
#: Printed only when there is a previous card for this slate day to compare
#: against — a marker that fires when nothing happened stops being read long
#: before it stops being sent.
SELECTIONS_CHANGED = "Selections changed"

#: The first line of a rehearsal's output, and the reason a rehearsal can never
#: be mistaken for a card even if something published it by accident.
REHEARSAL_LABEL = "REHEARSAL — not a card"

#: Where a rehearsal's frozen opinions go, under the archive root. The gameday
#: workflow restores and publishes `priced_snapshots/` and knows nothing about
#: this directory, so a rehearsal's snapshot cannot reach the card feed however
#: the run is invoked.
REHEARSAL_ARCHIVE_SEGMENT = "rehearsals"

#: The months in which a rating is still substantially the preseason prior. The
#: brief calls the whole regime "November"; the graph does not reconnect on 1
#: December, and the buy-games that make ratings hardest to read are 98%
#: concentrated in these two months (541 of 551 in 2025-26). How fast the prior
#: decays inside the regime is a measured question, recorded by the
#: `november_prior_schedule` verdict; whether a price made inside it must carry
#: its prior weight is not, and is enforced here.
PRIOR_REGIME_MONTHS: frozenset[int] = frozenset({11, 12})

#: How many earlier seasons the walk-forward tier table may look at. Tiers for a
#: game are what the seasons **strictly before** it said, never what its own
#: season will say.
TIER_LOOKBACK_SEASONS = 3

#: The markets the bulk endpoint serves, derived from the registry rather than
#: named here. When the per-event stage is cut short by the cap, these are the
#: markets whose coverage is still complete across the whole slate, and they are
#: the only ones that may be frozen from such a run — the rest are a tip-ordered
#: prefix. A market carrying both a bulk key and a per-event-only key would be
#: complete for the wrong reason; none exists today and this is where that would
#: need re-deriving if one ever did.
BULK_MARKETS: frozenset[str] = frozenset(
    market.key
    for market in MARKETS_BY_KEY.values()
    if set(market.provider_keys) & set(BULK_SAFE_MARKETS)
)

#: The columns handed to `forward_evidence.write_snapshot`. Named rather than
#: sliced off `staging.STAGED_COLUMNS`, because a positional slice of somebody
#: else's tuple silently freezes the wrong field the day that tuple is
#: reordered — and a snapshot is the one artefact in this lab that cannot be
#: rebuilt afterwards. `provider_key` is deliberately absent: it is the
#: provider's vocabulary, and nothing downstream of the freeze speaks it.
FROZEN_COLUMNS: tuple[str, ...] = (
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
)

#: The workflow's own mention regex, character for character. Written here so
#: the renderer fails on the same string the workflow would fail on, one step
#: earlier and with the offending text named.
_MENTION = re.compile(r"(^|[^A-Za-z0-9_/])@[A-Za-z0-9][A-Za-z0-9-]*", re.MULTILINE)


class CardError(RuntimeError):
    """The card refused. Every subclass says what it refused and why."""


class CardWouldEmail(CardError):
    """The comment carries something that reads as an `@mention`.

    Raised rather than scrubbed. An `@mention` overrides an ignored repository
    subscription, so publishing this comment would resume Cooper's email
    however his notification settings are set — and removing the `@` by
    rewriting a school's name would fabricate a name, which this lab does not
    do. The freeze has already happened by the time this can raise, so the
    evidence survives and only the prose is lost.
    """


class Decision(str, Enum):
    """The word the workflow greps off stdout as `decision=<word>`.

    Every value is `[a-z-]+`, which is what the workflow's regex accepts. They
    describe **what happened**, never what the lab thinks of a bet.
    """

    #: At least one wager cleared every bar. Impossible while no market is
    #: allowlisted, and kept as a real branch rather than a stub so the day a
    #: receipt is signed the card does not need rewriting.
    SELECTIONS = "selections"
    #: The card was produced and nothing cleared. The expected, correct state.
    NO_SELECTIONS = "no-selections"
    #: The board carried no game on this slate day. A real state in this sport
    #: — there are days in the season with no basketball — and it is reported
    #: as that rather than as a fault.
    NO_SLATE = "no-slate"
    #: A rehearsal. Never a card, never published, and given its own word so a
    #: rehearsal's outcome can never be read as a card's.
    REHEARSAL = "rehearsal"
    #: Nothing was requested and nothing was frozen. A dry run.
    DRY_RUN = "dry-run"
    #: The run refused to start or to continue. Quota below the cap, a slate
    #: date that is not today without a rehearsal flag, or an identity that did
    #: not reconcile.
    REFUSED = "refused"


#: Which bucket of the accounting identity each bar falls in. **Data, not
#: prose**, so `tests/test_gameday_card.py` reads this table rather than a copy
#: of it, and a bar added to `card_pricing.BAR_ORDER` without a bucket here
#: fails the build instead of silently vanishing from the identity.
#:
#: The two judgment calls, recorded rather than left implicit:
#:
#: * `NOT_APPROVED` is **gated**, not "no opinion". The lab has an opinion and
#:   may not act on it, which is exactly what `gated` means — modelled, priced,
#:   and missing the one thing that would make the bet real. Here that thing is
#:   a signed acceptance receipt rather than a feed.
#: * `OUTSIDE_PRICE_BAND` is **ambiguous**. Out past −400 and +600 the largest
#:   apparent edges in any price store are the rows that are wrong — a stale
#:   quote, a mis-keyed line, a book's error left hanging — and the lab cannot
#:   tell those from a real edge. That is ambiguity, not a judgment about the
#:   bet.
BAR_BUCKETS: dict[Bar, str] = {
    Bar.NOT_APPROVED: "gated",
    Bar.NO_OPINION: "no_opinion",
    Bar.BELOW_THRESHOLD: "below_threshold",
    Bar.OUTSIDE_PRICE_BAND: "ambiguous",
    Bar.AVAILABILITY: "gated",
    Bar.TIP_GUARD: "gated",
    Bar.CORRELATED_GAME: "gated",
    Bar.SLATE_CAP: "gated",
}


# --------------------------------------------------------------------------
# The seam to the ratings model
# --------------------------------------------------------------------------


class Matchup(Protocol):
    """The three numbers a game is priced from, and what they are made of.

    This is `models/__init__.py`'s described seam, read from the consuming
    side. It stays a **Protocol** now that `models/ratings.py` exists, and for
    the reason it was one before: declaring the shape costs nothing at runtime,
    keeps the type hints honest, and cannot become a second definition that
    drifts from the real `ratings.Matchup`. A duplicated dataclass is the
    `_bonferroni_factor` defect in miniature. The card reads matchups through
    `_matchup_field`, so a test double carrying these names is as good a
    matchup here as the shipped dataclass — which is what keeps the doubles in
    `tests/` from having to import the model.

    A game with no entry is `NO_OPINION`, and the card says so in those words
    rather than pretending the model declined.
    """

    #: Expected points per possession, each side.
    home_points_per_possession: float
    away_points_per_possession: float
    #: Expected possessions per team over forty minutes — tempo.
    possessions: float
    #: How much of the rating is still the preseason prior, in [0, 1]. **None
    #: means not recorded**, which is a different claim from 0.0.
    prior_weight: float | None
    #: `population.VenueState`. `UNKNOWN` quarantines the game.
    venue_state: str
    #: False when the schedule graph has not connected these two teams by
    #: anything but the prior. An unpriced game is an honest output.
    priceable: bool
    unpriceable_reason: str


def _matchup_field(matchup: object, name: str, default=None):
    """Read one field off whatever the caller passed.

    `getattr` with a default rather than attribute access, so a partially
    populated matchup declines rather than raising. A missing field is missing
    information, and missing information is not a reason to price a game.

    An **explicit `None` is kept**, never replaced by the default. A matchup
    that says `priceable=None` has not said it is priceable, and substituting
    `True` there would turn "the ratings module did not answer" into "the
    ratings module said yes" — ambiguity resolving to the play side, which is
    the one direction every gate in this lab refuses to resolve in.
    """
    return getattr(matchup, name, default)


# --------------------------------------------------------------------------
# The board
# --------------------------------------------------------------------------


@dataclass
class Board:
    """One read of the price board, in this lab's vocabulary, with what it cost.

    `rows` is every staged quote — every book, every market — because that is
    what the line-shopping and price-survival evidence is made of and it is
    written to `data/staging/` intact.

    `per_event_complete` is the flag that decides what may be frozen. The
    featured markets arrive in one bulk call covering the whole slate, so they
    are complete or absent. The ladders and props are asked per event in tip
    order, and a stage stopped by the cap partway through leaves a **prefix**:
    the early tips kept and the late ones dropped, which in this sport is the
    West Coast, low-major end of the board — exactly the end this lab was built
    to look at. A prefix frozen into the ledger is a biased subset wearing the
    name of a night, so :func:`_rows_to_freeze` withholds every market outside
    :data:`BULK_MARKETS` when this is False. The rows are still staged: they
    were paid for and they are evidence, they are just not a stratum.
    """

    rows: pd.DataFrame
    counts: staging.StagingCounts
    spend: Spend
    #: Where the board came from, in words a report can print.
    source: str
    #: Every event this read saw, on any day. The bulk endpoint returns the
    #: whole upcoming board, so this is deliberately not "games tonight" —
    #: `CardRun.events_on_this_slate` is that, and conflating them is how a
    #: card reports tomorrow's fixtures as tonight's coverage.
    events_in_the_read: int = 0
    #: Events the free listing put on the slate day being carded, at fetch
    #: time. Zero for a board read from a file, which cannot know.
    events_listed_for_the_slate: int = 0
    events_asked_per_event: int = 0
    per_event_asked: bool = False
    per_event_complete: bool = True
    #: Events whose per-event call failed on its own. Scattered rather than
    #: ordered, so they do not make the stage a prefix.
    events_failed: int = 0
    notes: list[str] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)


def board_from_payloads(
    payloads: Iterable[Mapping] | Mapping,
    *,
    competition: Competition,
    source: str = "a staged fixture",
    spend: Spend | None = None,
) -> Board:
    """Read provider payloads into a board. Touches no network.

    This is the seam the offline test drives: the same `staging.stage_payloads`
    a live fetch uses, over a fixture instead of a response. A test that stubbed
    the staging step would prove the card renders and nothing about whether the
    board it renders can be read.
    """
    rows, counts = staging.stage_payloads(payloads, competition=competition)
    return Board(
        rows=rows,
        counts=counts,
        spend=spend or Spend(),
        source=source,
        events_in_the_read=counts.events,
    )


def read_staged_board(
    path: Path | str, *, competition: Competition
) -> Board:
    """A board read back from a staged CSV. Touches no network and no credential.

    The staged file is this lab's vocabulary already, so nothing is re-read from
    the provider's. Counts cannot be reconstructed from it — the refusals were
    counted when the response was read and a CSV of what survived cannot say
    what did not — so the counts come back empty and the card says the board
    came from a file rather than from the provider.
    """
    frame = stores.read_store(Path(path), columns=staging.STAGED_COLUMNS)
    counts = staging.StagingCounts(
        events=int(frame["event_id"].nunique()) if not frame.empty else 0,
        events_staged=int(frame["event_id"].nunique()) if not frame.empty else 0,
        outcomes=len(frame),
        staged=len(frame),
    )
    return Board(
        rows=frame,
        counts=counts,
        spend=Spend(),
        source=f"a staged fixture at `{Path(path).name}`",
        events_in_the_read=counts.events,
        notes=[
            "This board was read from a staged file rather than from the "
            "provider, so nothing was requested, no credential was read and no "
            "credit was spent. The staging refusal counts cannot be "
            "reconstructed from a file of the rows that survived, so they are "
            "reported as zero rather than as measured."
        ],
    )


def fetch_board(
    provider: OddsApiProvider,
    *,
    competition: Competition,
    credit_cap: int,
    day: str,
    market_tiers: tuple[int, ...] = (1, 2, 3),
) -> Board:
    """Fetch the board under a hard cap, in two stages, and never a prefix.

    Stage one is the bulk call: `h2h`, `spreads` and `totals` for the whole
    upcoming slate, billed `markets x regions` regardless of how many events
    come back. On a hundred-game January Tuesday that is the difference between
    six credits and six hundred, which is why the featured markets are never
    asked per event.

    Stage two is the ladders, the halves and the props, which the bulk endpoint
    refuses with a 422 that names nothing. It is asked per event, and it is
    asked **all or not at all**: the pessimistic bound of the whole stage is
    checked against what the cap has left before the first request, and a stage
    that will not fit is skipped entirely rather than truncated. A skipped stage
    is a stated absence; a truncated one is a tip-ordered prefix that looks
    exactly like a market nobody quotes.

    The cap itself is enforced inside the adapter, before every request, against
    the **measured** running total from `x-requests-last`. Nothing here does its
    own credit arithmetic — the NHL lab capped a run at 200,000 and spent
    289,984 by estimating from markets asked rather than markets returned, and
    its test asserted the cap "cannot be breached" the whole time.
    """
    spend = Spend()
    board = Board(
        rows=pd.DataFrame(columns=list(staging.STAGED_COLUMNS)),
        counts=staging.StagingCounts(),
        spend=spend,
        source="the provider",
    )

    # Free, and the complete slate — the bulk response only carries events some
    # book has priced, which is not the same list.
    try:
        events = provider.list_events()
    except ProviderError as exc:
        board.degraded.append(f"The events listing could not be read: {exc}")
        events = []
    on_the_day = [
        event
        for event in events
        if slate_date(event.get("commence_time"), competition) == day
    ]
    board.events_in_the_read = len(events)
    board.events_listed_for_the_slate = len(on_the_day)

    frames: list[pd.DataFrame] = []
    bulk_keys = tuple(sorted(BULK_SAFE_MARKETS))
    try:
        payloads = provider.fetch_bulk(bulk_keys, spend=spend, credit_cap=credit_cap)
        rows, counts = staging.stage_payloads(payloads, competition=competition)
        frames.append(rows)
        board.counts.merge(counts)
    except ProviderError as exc:
        # Nothing else is worth asking for: without the featured markets there
        # is no core stratum, and a card built only of ladders is a card built
        # of the markets nobody watches.
        board.degraded.append(
            f"The bulk slate could not be fetched ({exc}). No featured market "
            "was read, so nothing was frozen from this run."
        )
        board.rows = pd.concat(frames, ignore_index=True) if frames else board.rows
        return board

    per_event_keys = tuple(
        k for k in per_event_provider_keys(tiers=market_tiers) if k not in BULK_SAFE_MARKETS
    )
    regions = len([r for r in provider.regions.split(",") if r.strip()]) or 1
    stage_bound = len(on_the_day) * len(per_event_keys) * regions
    board.per_event_asked = bool(on_the_day and per_event_keys)

    if not board.per_event_asked:
        board.notes.append(
            "No per-event market was asked for: "
            + ("the slate is empty." if not on_the_day else "no tier asked for one.")
        )
    elif spend.credits_spent + stage_bound > int(credit_cap):
        board.per_event_asked = False
        board.notes.append(
            f"The ladders, halves and props were **not asked for**. Their "
            f"pessimistic bound is {stage_bound:,} credits over "
            f"{len(on_the_day):,} game(s) at {len(per_event_keys)} provider "
            f"key(s) x {regions} region(s), and {spend.credits_spent:,} of the "
            f"{int(credit_cap):,} cap is already spent. The whole stage was "
            "skipped rather than truncated: a stage stopped partway through "
            "leaves the early tips and drops the late ones, and a starved fetch "
            "and an unquoted market look identical in a coverage report. **This "
            "says nothing about whether those markets are quoted.**"
        )
    else:
        ordered = sorted(on_the_day, key=lambda e: str(e.get("commence_time") or ""))
        for event in ordered:
            event_id = clean_text(event.get("id"))
            if not event_id:
                continue
            try:
                payload = provider.fetch_event_odds(
                    event_id, per_event_keys, spend=spend, credit_cap=credit_cap
                )
            except CreditCapReached as exc:
                # A prefix. Every per-event row goes to staging and none of it
                # to the ledger; `ledger_rows` enforces that.
                board.per_event_complete = False
                board.degraded.append(
                    f"The per-event stage stopped at the cap after "
                    f"{board.events_asked_per_event:,} of {len(ordered):,} "
                    f"game(s) ({exc}). Those rows are staged and are **not** "
                    "frozen: they are the earliest tips on the slate, and a "
                    "tip-ordered prefix written into the ledger is a biased "
                    "subset wearing the name of a night."
                )
                break
            except ProviderError as exc:
                board.events_failed += 1
                board.degraded.append(
                    f"One game's per-event markets could not be read ({exc})."
                )
                continue
            rows, counts = staging.stage_payloads(payload, competition=competition)
            frames.append(rows)
            board.counts.merge(counts)
            board.events_asked_per_event += 1

    board.rows = (
        pd.concat(frames, ignore_index=True)[list(staging.STAGED_COLUMNS)]
        if frames
        else board.rows
    )
    return board


# --------------------------------------------------------------------------
# The tip guard, which runs against each game's own tip and runs twice
# --------------------------------------------------------------------------


@dataclass
class TipCensus:
    """What the tip guard saw, per state, and the games it quarantined.

    Counted per **game** rather than per wager, because a game is what tips.
    Twelve markets on one started game is one quarantined game, and reporting
    it as twelve exclusions is how a card's real news gets buried under noise.
    """

    states: dict[str, set] = field(default_factory=dict)
    #: Selections withdrawn by the second pass, after the bars were applied.
    withdrawn_after_pricing: list[str] = field(default_factory=list)

    def see(self, event_id: str, state: TipState) -> None:
        self.states.setdefault(state.value, set()).add(str(event_id))

    def games(self, state: TipState) -> int:
        return len(self.states.get(state.value, set()))

    def summary_line(self) -> str:
        # Distinct games, not the sum of the buckets: one game read `upcoming`
        # when the bars were applied and `started` on the second pass appears in
        # two buckets and is still one game.
        seen = len({game for games in self.states.values() for game in games})
        parts = ", ".join(
            f"{state}={len(games):,}" for state, games in sorted(self.states.items())
        )
        return (
            f"Tip guard, run against each game's own tip: {seen:,} game(s) "
            f"judged — {parts or 'none'}. Only `upcoming` may carry a stake. "
            + imminent_note()
            + " `unconfirmed` is a tip time this lab could not read and it "
            "quarantines the same way."
        )


class TipGuard:
    """Each game against its own tip, on every evaluation, on a clock read now.

    The clock is a callable rather than a captured `datetime` on purpose. A
    200-game slate takes minutes to fetch per event, and a guard holding one
    timestamp for the whole run would clear a game that tipped while the run was
    still working — which is the failure the EPL lab had to retrofit a guard for
    after a card carried a fixture that had already kicked off.
    """

    def __init__(self, now: Callable[[], datetime] | None = None) -> None:
        self.now = now or (lambda: datetime.now(timezone.utc))
        self.census = TipCensus()

    def state_for(self, wager: Wager) -> TipState:
        state = tip_state(wager.commence_time, now=self.now())
        self.census.see(wager.event_id, state)
        return state

    def recheck(self, selections: Sequence[Mapping]) -> tuple[list[dict], list[dict]]:
        """The second pass. Returns `(kept, withdrawn)` on a freshly read clock."""
        kept: list[dict] = []
        withdrawn: list[dict] = []
        for row in selections:
            state = tip_state(row.get("commence_time"), now=self.now())
            self.census.see(str(row.get("event_id", "")), state)
            if can_be_played(state):
                kept.append(dict(row))
            else:
                withdrawn.append(dict(row))
                self.census.withdrawn_after_pricing.append(
                    f"{row.get('label', '')} — {state.value}"
                )
        return kept, withdrawn


# --------------------------------------------------------------------------
# Placing a game: which schools, which tier
# --------------------------------------------------------------------------


@dataclass
class Placement:
    """Which tier each game is in, and every game that could not be placed.

    An unplaced game is a real state (`conferences.Tier.UNPLACED`), reported
    separately and never folded into a tier's number. **No pooled headline
    across the whole of Division I is ever reported**, so a game whose tier is
    unknown cannot be quietly averaged into one.
    """

    tiers: dict[str, Tier] = field(default_factory=dict)
    table: TierTable | None = None
    unresolved_names: dict[str, int] = field(default_factory=dict)
    seasons_used: tuple[int, ...] = ()
    note: str = ""

    def counts(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for tier in self.tiers.values():
            out[tier.value] = out.get(tier.value, 0) + 1
        return out

    def summary_line(self) -> str:
        if self.table is None:
            return self.note or (
                "No walk-forward tier table was available, so every game on "
                "this card is `unplaced`. That is a stated absence rather than "
                "a tier."
            )
        parts = ", ".join(f"{k}={v:,}" for k, v in sorted(self.counts().items()))
        return (
            f"Tiers from season(s) {list(self.seasons_used)}, strictly before "
            f"this one: {parts or 'none'}. A game takes the higher of its two "
            "sides' tiers, because the board's attention follows the stronger "
            "programme."
        )


def place_games(
    board: Board,
    *,
    competition: Competition,
    day: str,
    raw_dir: Path | str | None,
) -> Placement:
    """Resolve each event's two schools and place the game in a tier.

    Degrades rather than empties, every step of the way. A missing schedule
    cache, an unreadable parquet, a provider spelling the alias map has never
    seen — each one leaves the affected game `unplaced` and says so, and none of
    them stops the card. `providers/team_names.py`'s alias map is knowingly
    incomplete (the provider's `basketball_ncaab` was inactive when it was
    seeded, so there was no live board to read real spellings off), and a name
    it cannot resolve is reported loudly rather than guessed at.
    """
    if raw_dir is None:
        return Placement(note="No raw directory was given, so no tier table was built.")
    # The feed registry owns the filename, not this module. A second copy of
    # `mbb_schedule_{season}.parquet` here would be a sport literal outside the
    # registry and a rename upstream would leave it silently finding nothing —
    # which reads as "no cached schedule" and places every game `unplaced`
    # rather than failing.
    feed = hoopr.FEEDS["schedules"]
    season = season_for_slate_date(day)
    schedules: dict[int, pd.DataFrame] = {}
    for candidate in range(feed.first_season, season + 1):
        path = feed.path(candidate, Path(raw_dir))
        if not path.is_file():
            continue
        try:
            schedules[candidate] = pd.read_parquet(path)
        except (OSError, ValueError):
            continue
    if not schedules:
        return Placement(
            note=(
                f"No cached schedule under `{Path(raw_dir)}`, so no "
                "walk-forward tier table could be built and every game is "
                "`unplaced`. The card still prices and freezes; it simply "
                "cannot stratify, and an unstratified number is never reported "
                "as a Division I headline."
            )
        )

    earlier = tuple(s for s in sorted(schedules) if s < season)
    if not earlier:
        return Placement(
            note=(
                f"No season before {season} is cached, so no walk-forward tier "
                "table could be built. Tiering off the season being priced "
                "would leak its own results into the stratum every game lands "
                "in, so every game is `unplaced` instead."
            )
        )
    used = earlier[-TIER_LOOKBACK_SEASONS:]
    table = tier_table(schedules, used)
    index = team_names.build_index(schedules.get(season, schedules[earlier[-1]]))

    tiers: dict[str, Tier] = {}
    if not board.rows.empty:
        fixtures = board.rows[["event_id", "home_team", "away_team"]].drop_duplicates()
        for row in fixtures.to_dict("records"):
            home = index.resolve(row.get("home_team"))
            away = index.resolve(row.get("away_team"))
            if home is None or away is None:
                tiers[str(row["event_id"])] = Tier.UNPLACED
                continue
            tiers[str(row["event_id"])] = Tier(game_tier(home, away, table))
    return Placement(
        tiers=tiers,
        table=table,
        unresolved_names=dict(index.unresolved),
        seasons_used=used,
    )


# --------------------------------------------------------------------------
# The opinion, or the refusal to have one
# --------------------------------------------------------------------------


@dataclass
class OpinionCensus:
    """Why the model did or did not have an opinion, grouped by reason.

    Grouped, never one line per wager: with 35 markets over a 200-game slate,
    one line per refusal is seventeen thousand copies of one sentence, and
    noise on a card is how the line that matters gets skipped.
    """

    wagers: int = 0
    priced: int = 0
    declined: dict[str, int] = field(default_factory=dict)
    #: Frozen key -> the push mass the joint puts on the line, for the wagers
    #: that were priced. Reported beside every number, because the edge
    #: definition this repository uses has no push term.
    push_mass: dict[tuple, float] = field(default_factory=dict)
    #: Frozen key -> the prior's weight in the rating behind the price.
    prior_weight: dict[tuple, float] = field(default_factory=dict)
    #: Design 4's check (a), pooled over the regular athletes this run priced —
    #: whatever `models.player_distributions.population_structural_checks`
    #: returned, or empty when no player distribution was built at all. Design 4
    #: asks for the ratio to be REPORTED as well as stopped on:
    #: :meth:`structural_check_line` is the report and `assert_structural_checks`
    #: is the stop. Carrying it here was not enough and the comment that said so
    #: was wrong for a commit: the reporter had no caller in `src/` or
    #: `scripts/` until :func:`_model_section` printed it onto the card.
    structural_check: dict[str, float] = field(default_factory=dict)
    #: Design 13's failure mode 5, per tier: whatever
    #: `models.player_rates.resolution_census` returned over the athletes this
    #: run holds a projection for, or empty when it holds none. Design 13 asks
    #: for the per-tier resolution rate to be PRINTED every run and for the run
    #: to STOP when it moves more than 2pp across tiers;
    #: :meth:`tier_resolution_line` is the print and
    #: `player_rates.assert_tier_resolution_holds` is the stop, and neither had
    #: a caller anywhere in `src/` or `scripts/` until :func:`opinions_for`
    #: called them.
    tier_resolution: dict[str, dict[str, int]] = field(default_factory=dict)
    #: Name refusals carry no tier, because they carry no athlete and design 9
    #: tiers a player by his OWN team. Counted beside the census rather than
    #: folded into a tier, which would be a read from the team side.
    untiered_name_refusals: int = 0

    def decline(self, reason: str) -> None:
        self.declined[reason] = self.declined.get(reason, 0) + 1

    def summary_line(self) -> str:
        return (
            f"{self.priced:,} of {self.wagers:,} priced wager(s) carry a "
            "modelled opinion. An absent opinion is **not** a probability of "
            "zero: it is the model declining, or never being asked."
        )

    def structural_check_line(self) -> str:
        """Design 4's "report the ratio", said in one sentence or not at all.

        Three states, and they are three different facts. No player
        distribution was built, so the check was never asked. Fewer regulars
        than `STRUCTURAL_CHECK_POPULATION_FLOOR`, so it ran and may not stop —
        printed with the count, because a check that silently declines to run is
        indistinguishable from one that passed and that is the shape of the
        defect this whole path exists against. Or it ran over a population and
        the run is still going, which means it passed.

        A fourth number rides on the head line whenever it is not zero: the
        regulars whose `player_points` the fit refused. They were built, they
        are not below the minutes floor and they still carry no points mixture,
        so they are out of both sums — and a population that quietly shrank
        because a constant was refused would otherwise read exactly like a
        population that was small.
        """
        checks = self.structural_check
        if not checks:
            return (
                "Design 4's structural check was not asked: this card built no "
                "player distribution."
            )
        athletes = int(checks.get("population_athletes", 0))
        floor = int(checks.get("population_floor", 0))
        offered = int(checks.get("population_athletes_offered", 0))
        below = int(checks.get("population_below_regular_floor", 0))
        minutes = float(checks.get("regular_min_projected_minutes", 0.0))
        refused = int(checks.get("population_points_refused", 0))
        head = (
            f"Design 4's structural check (a): {athletes:,} of {offered:,} "
            f"athlete(s) priced are regulars at {minutes:.1f}+ projected "
            f"minutes ({below:,} below, counted apart and never pooled)"
        )
        if refused:
            head += (
                f", and {refused:,} regular(s) whose `player_points` the fit "
                "refused, counted apart as well"
            )
        if athletes < floor:
            return (
                f"{head}. Fewer than the declared floor of {floor}, so the "
                "ratio is reported and STOPS NOTHING — pooled over this few it "
                "would be the per-athlete number the floor exists against."
            )
        return (
            f"{head}. Pooled unconditional points VMR "
            f"{checks['unconditional_points_vmr']:.4f} against the frozen "
            f"{checks['unconditional_points_vmr_target']:.4f}, a ratio of "
            f"{checks['unconditional_points_vmr_ratio']:.4f}. The run continued, "
            "so it is inside design 4's 15% stop."
        )

    def tier_resolution_line(self) -> str:
        """Design 13's failure mode 5, said in one sentence or not at all.

        Design 13: print the per-tier resolution rate every run, and stop the
        run if the priceable rate moves more than 2pp across tiers. A resolution
        rate that runs with tier is a biased sample rather than a smaller one —
        the team-name version of this join lost 20.5% of provider names with
        46.7% of the misses at the low-major end, which is the measurement the
        rule is written against.

        Three states, and they are three different facts. No athlete carries a
        projection, so there was nothing to tier. One tier carries subjects, so
        the check has nothing to compare and `assert_tier_resolution_holds`
        returns without looking — said in terms, because a check that cannot run
        must never read like one that passed. Or two or more tiers carry
        subjects, the spread is printed, and the run is still going, which means
        it is inside the declared tolerance.

        `Tier.UNPLACED` is reported and never folded into the comparison: a
        first-Division-I-season roster would otherwise move a check about the
        join.
        """
        census = self.tier_resolution
        refused = self.untiered_name_refusals
        tail = (
            f" {refused:,} name(s) were refused before any tier could be read "
            "and are counted apart: an unresolved spelling carries no athlete, "
            "so it carries no team and no tier."
            if refused
            else ""
        )
        if not census:
            return (
                "Design 13's per-tier resolution rate was not asked: this card "
                "holds no player projection to tier." + tail
            )
        rates = {
            tier: 100.0 * int(counts.get("priceable", 0)) / int(counts["subjects"])
            for tier, counts in sorted(census.items())
            if tier != Tier.UNPLACED.value and int(counts.get("subjects", 0))
        }
        spelled = ", ".join(
            f"{tier} {rates[tier]:.1f}% of "
            f"{int(census[tier]['subjects']):,}"
            for tier in sorted(rates)
        )
        unplaced = census.get(Tier.UNPLACED.value)
        aside = (
            f" {int(unplaced['subjects']):,} unplaced subject(s) are reported "
            "and never folded into the comparison."
            if unplaced and int(unplaced.get("subjects", 0))
            else ""
        )
        if len(rates) < 2:
            return (
                f"Design 13's per-tier resolution rate: {spelled or 'nothing'}. "
                "Fewer than two tiers carry a subject, so the 2pp check has "
                "nothing to compare and STOPS NOTHING on this card."
                + aside
                + tail
            )
        spread = max(rates.values()) - min(rates.values())
        return (
            f"Design 13's per-tier resolution rate: {spelled}. The priceable "
            f"rate moves {spread:.2f} percentage points across tiers, against "
            f"the declared {player_rates.TIER_RESOLUTION_TOLERANCE_POINTS}pp. "
            "The run continued, so it is inside it."
            + aside
            + tail
        )

    def event_dispersion_line(self) -> str:
        """Which of the frozen file's two event dispersions priced this card.

        **A disclosure, not a check.** Nothing stops on it and no number in it
        is produced: the frozen file freezes two candidates for the scoring-
        event count's Panjer dispersion under `points_compound_reconciliation`
        and says in terms that "the choice belongs to the model, not to the
        fit". `models.player_distributions.POINTS_EVENT_DISPERSION_KEY` makes
        that choice, and the paragraph that argues for it concedes the choice
        moves design 4's produced ratio by 0.167 — the whole width of the stop
        budget — offering as the thing that keeps it honest that both numbers
        are printed beside each other on every run.

        **They were not.** The only mapping carrying both keys was
        `PlayerDistribution.structural_checks`, which has no caller in `src/`
        or `scripts/`; `population_structural_checks` returned nine keys and
        neither dispersion was among them. Rendered, a card that priced eight
        player props carried neither number and not the word "dispersion" at
        all, so a reviewer asking which dispersion priced the card had nothing
        to read and a later refit could move `measured_event_dispersion`
        without changing anything anyone could see.

        Two states, and they are two different facts. No player distribution
        was built, so no dispersion was chosen. Or one was, and the sentence
        names which frozen key it came from at full precision — the key name is
        recovered by matching the value the engine USED against the two
        candidates, never retyped here, so moving
        `POINTS_EVENT_DISPERSION_KEY` moves this sentence with it.
        """
        checks = self.structural_check
        used = checks.get("points_event_dispersion_used")
        if used is None:
            return (
                "No scoring-event dispersion was chosen on this card: it built "
                "no player distribution."
            )
        candidates = {
            name: checks[name]
            for name in ("effective_event_dispersion", "measured_event_dispersion")
            if name in checks
        }
        chosen = [name for name, value in candidates.items() if value == used]
        other = [name for name, value in candidates.items() if value != used]
        if len(chosen) != 1 or len(other) != 1:
            # The mapping carried the used value and not the pair it has to be
            # disclosed against. Say so rather than printing one number as
            # though the choice had been shown.
            return (
                f"The compound points sum was priced at an event dispersion of "
                f"{used!r}, and the frozen file's two candidates for it are not "
                "both on this run's structural check, so which one that is "
                "cannot be shown here."
            )
        return (
            "Scoring-event dispersion: this card priced the compound points "
            f"sum at `{chosen[0]}` = {used!r}, and the frozen file's other "
            f"candidate `{other[0]}` = {candidates[other[0]]!r} was not used. "
            "The file freezes both and leaves the choice to the model, so both "
            "are printed here rather than only in the constant's docstring."
        )

    def table(self) -> str:
        if not self.declined:
            return "The model had an opinion on every priced wager."
        lines = ["| Why the model has no opinion | Wagers |", "|:---|---:|"]
        lines += [
            f"| {reason} | {count:,} |"
            for reason, count in sorted(self.declined.items(), key=lambda kv: (-kv[1], kv[0]))
        ]
        return "\n".join(lines)


def _side_and_which(selection: str) -> tuple[str, str]:
    """`home_over` -> (`over`, `home`). Anything else -> (selection, '')."""
    if selection.startswith("home_"):
        return selection[len("home_") :], HOME
    if selection.startswith("away_"):
        return selection[len("away_") :], AWAY
    return selection, ""


def _read_market(
    wager: Wager, joint: distributions.GameDistribution
) -> tuple[float | None, float, str]:
    """`(probability, push_mass, reason)` for one wager off one joint.

    **The push counts against the bet.** `forward_evidence.expected_value` is
    the one definition of edge in this repository and it is `p·(1+payout) − 1`,
    which has no push term — so a probability that folded the push in would be
    price-dependent, and one that divided it out (`w/(w+l)`, the conventional
    push-adjusted probability) would overstate the edge by the push mass, in the
    flattering direction, on precisely the whole-number lines where the market
    concentrates. Taking `p = win` understates it by exactly the push mass
    instead, which is the conservative direction and is a number the joint
    already knows. It is returned so the card can print it beside every price:
    that is also Cooper's rule that a card must say how much of a spread or
    total edge is half a point at a key number rather than a differing view of
    the game.
    """
    market = MARKETS_BY_KEY.get(wager.market)
    if market is None:
        return None, 0.0, "the market is not one this lab wires"
    settles = market.settles_on
    selection = wager.selection
    line = normalise_line(wager.line)

    try:
        if settles in {"game_margin", "half_margin"}:
            if selection not in (HOME, AWAY):
                return None, 0.0, "the selection does not name a side of this game"
            if line is None:
                # A moneyline. A level first half is not a loss and not a win;
                # `resolves_ties` is False for that segment and the level mass
                # is what the two sides do not sum to.
                return (
                    float(joint.moneyline(selection)),
                    0.0 if joint.resolves_ties else float(joint.tie_probability()),
                    "",
                )
            win, push, _ = joint.margin(float(line), selection)
            return float(win), float(push), ""
        if settles in {"game_total", "half_total"}:
            if selection not in (OVER, UNDER):
                return None, 0.0, "the selection does not name a side of this total"
            if line is None:
                return None, 0.0, "a total with no line cannot be read off a distribution"
            win, push, _ = joint.total(float(line), selection)
            return float(win), float(push), ""
        if settles in {"team_score", "half_team_score"}:
            side, which = _side_and_which(selection)
            if which not in (HOME, AWAY) or side not in (OVER, UNDER):
                return None, 0.0, "the selection does not name a school and a side"
            if line is None:
                return None, 0.0, "a team total with no line cannot be read off a distribution"
            win, push, _ = joint.team_total(float(line), side, which)
            return float(win), float(push), ""
    except distributions.DistributionError as exc:
        return None, 0.0, f"the distribution refused this line ({exc})"
    return (
        None,
        0.0,
        f"no reader exists for the settlement quantity `{settles}`",
    )


def _player_distributions_module():
    """`models.player_distributions`, or `None` if it cannot be imported.

    Imported inside the call, for the reason `slate._player_rates_module` is: a
    module-scope import binds the answer once per process and would make an
    engine that fails to import take the whole card down, so a card that could
    still price every spread would print nothing at all.
    :data:`slate.NO_DISTRIBUTION_ENGINE` is the sentence that says which of the
    two states the lab is in, and it is reachable only because of this.
    """
    try:
        from cbb_betting_lab.models import player_distributions  # noqa: PLC0415
    except ImportError:
        return None
    return player_distributions


def _player_decline(
    model: "slate.SlateModel", wager: Wager
) -> tuple[str, str]:
    """`(bucket, reason)` for a prop that carries no probability; `("", "")` when it can be priced.

    The bucket is one of `models.player_census.OFFERED_BUCKETS`, read from that
    module and never spelled here, and it is returned rather than derived from
    the sentence because the sentences are the model's own words and a
    classifier over them would go wrong the first time one was reworded. It is
    what design section 10's pre-grading gate counts: every prop wager the store
    offers lands in exactly one bucket and the buckets must sum to the store's
    own count with a residual of exactly 0.

    **Seven** states, counted separately and never summed, and the separation
    is the deliverable of the seam this reads. Seven and not six: the bullets
    below have been seven since `player_first_team_basket` and the six other
    unregistered markets got their own sentence, and the head count was not
    moved with them. They map onto the identity's buckets as
    :data:`~models.player_census.BUCKET_REFUSED_BY_NAME`,
    :data:`~models.player_census.BUCKET_UNREGISTERED_MARKET`,
    :data:`~models.player_census.BUCKET_NAME_UNRESOLVED`,
    :data:`~models.player_census.BUCKET_ATHLETE_REFUSED` for the athlete's own
    refusal, and :data:`~models.player_census.BUCKET_NEVER_ASKED` for the three
    absences — the event nobody was asked about, the subject with no
    projection, and the two structural absences of the engine and its
    constants, which are one bucket with three sentences counted apart inside
    it because all three are the model holding nothing to refuse:

    * **refused by name** — `player_first_basket` or `player_double_double`.
      This is asked FIRST, before anything about the athlete, because it is a
      statement about the market and is true whatever the athlete's evidence
      looks like. Until 2026-09-06 there was no such branch, so a first-basket
      wager on a well-evidenced athlete fell through to *no engine* and the
      card printed "no probability exists for this line yet" — a temporary
      wiring absence — for a market the design refuses permanently. The
      refusal is printed in the design's own words, which say plainly that it
      is a model refusal and not a data absence.
    * **the name** — R1, R1a and R1b. The book's spelling did not resolve to
      exactly one athlete on a **prior** roster. No athlete id exists and none
      is invented; the refusal is filed under the spelling as the book wrote
      it. This is asked BEFORE the event, and the order is load-bearing rather
      than tidy. `slate.SlateModel.was_asked_about_players` is
      `event_id in players`, and `players` gains an entry only where a
      resolution SUCCEEDED (`player_rates.player_projections_for` writes
      `projections.setdefault(event_id, {})[athlete]` on the resolved branch
      only) — so an event on which every quoted spelling was refused for the
      name is not in `players` at all, and asking the event first printed the
      *never asked* sentence over bucket C on exactly the nights bucket C
      exists to describe. R1b makes that certain rather than incidental: it is
      filed inside `if len(roster) == 0`, computed once per event before the
      spelling loop, so it is all-or-nothing per event and can never be
      accompanied by a surviving projection — its sentence reached no output
      anywhere in `src/` or `scripts/` until this order was fixed. Measured
      through the shipped `slate._player_half` on a price frame quoting
      `Sean Bairstow` on teams 77/88 against a player table carrying only team
      55: `name_refusals[('e1', 'Sean Bairstow')]` is `R1B_NO_PRIOR_ROSTER`,
      `resolution_census` is `{'refused_no_prior_roster': 1,
      'quotes:refused_no_prior_roster': 1}`, `players` is `{}` — and the card
      printed "the model was never asked about this event's athletes". The
      same board is driven by `tests/test_player_seam.py::test_s12_a_name_
      refused_on_an_event_with_no_survivor_still_prints_r1bs_words` through
      the shipped `slate_model`. The two buckets are disjoint by `slate`'s invariant
      I4, so a pair carrying a name refusal never carries a projection and
      this order can hide nothing.
    * **never asked** — the model holds no projection for this event at all
      *and* this spelling was not refused for the name. `no opinion`, and the
      slate's own sentence says which absence it is: a night with no player
      evidence, an estimator that is not written, or a day in no season.
    * **not one of the ten** — the board carries player markets this model is
      not registered against at all. Measured on `markets.PLAYER_MARKETS`: 19
      player markets, of which 10 are priced and 2 are refused by name, leaving
      **seven** — `player_blocks`, `player_field_goals`, `player_frees_made`,
      `player_frees_attempts`, `player_blocks_steals`, `player_triple_double`
      and `player_first_team_basket`. The model was never asked about any of
      them and the frozen file carries a constant for none of them:
      `player_rates.STAT_KEYS` is seven names and blocks, field goals, free
      throws and a triple-double are not among them. Until 2026-09-06 all seven
      read *no engine*, which said the engine was not written — true of the lab
      then and never true of these.

      `player_first_team_basket` is worth naming separately: it is a DIFFERENT
      key from `player_first_basket` and is not in `MARKETS_REFUSED_BY_NAME`, so
      the design's first-basket refusal does not cover it and it lands here
      instead. Every word of that refusal — the opening tip, the mutually
      exclusive family, the partial field — applies to it as well, and this
      bucket says only that the model was never asked. Refusing it by name is a
      decision for whoever owns that mapping, not an edit to make in passing.
    * **the athlete** — R2 to R5, printed in the projection's own words.
    * **no engine** — `models/player_distributions.py` could not be imported.
      A statement about the lab rather than about the player, and reachable
      because the import is made inside the call.
    * **no constants** — the slate carries a priceable projection and not the
      frozen constants it was built from, so nothing can be built from it.
      A `SlateModel` assembled by hand or coerced from a bare mapping is in this
      state; one built by `slate.slate_model` never is.

    Returning `""` means every one of those is answered and the wager can be
    read off a distribution — see :func:`_read_player_market`. None of these is
    a pass, an avoid or a no-value call, and the missing entry is never counted
    as a refusal: `ratings.matchups_for`'s docstring draws the same line for the
    team half, in the same words.
    """
    refused = player_rates.MARKETS_REFUSED_BY_NAME.get(clean_text(wager.market))
    if refused:
        return player_census.BUCKET_REFUSED_BY_NAME, refused
    if clean_text(wager.market) not in player_rates.MARKET_COMPONENTS:
        return player_census.BUCKET_UNREGISTERED_MARKET, (
            "the player model is registered against ten markets and this is "
            "not one of them, so it was never asked about this line: "
            f"{', '.join(player_rates.PRICED_MARKETS)}. An unregistered market "
            "is not a refusal and it is not a pass, an avoid or a no-value call"
        )
    # THE NAME IS ASKED BEFORE THE EVENT, and the order is the whole of the
    # C/D separation on a night when nothing on the game resolved. See the
    # docstring's bucket-C paragraph: `was_asked_about_players` is
    # `event_id in players`, `players` is filled only by a resolution that
    # SUCCEEDED, and R1b is all-or-nothing per event — so asking the event
    # first prints D over every C on exactly the events C exists to describe.
    refusal = model.name_refusal(wager.event_id, wager.player)
    if refusal:
        return player_census.BUCKET_NAME_UNRESOLVED, refusal
    if not model.was_asked_about_players(wager.event_id):
        reason = model.player_absence_reason or slate.NO_PLAYER_SLATE
        return player_census.BUCKET_NEVER_ASKED, (
            "the model was never asked about this event's athletes, so this "
            f"prop carries no opinion: {reason}"
        )
    projection = model.projection_for(wager.event_id, wager.player)
    if projection is None:
        return player_census.BUCKET_NEVER_ASKED, (
            "the model projects athletes on this event and holds no projection "
            "for this subject, so it has no opinion on him. An absent "
            "projection is not a probability of zero"
        )
    if not bool(getattr(projection, "priceable", False)):
        return player_census.BUCKET_ATHLETE_REFUSED, clean_text(
            getattr(projection, "unpriceable_reason", "")
        ) or (
            "the player model refuses this subject and recorded no reason, "
            "which is itself a fault: a refusal with no sentence is a silence"
        )
    if _player_distributions_module() is None:
        return player_census.BUCKET_NEVER_ASKED, slate.NO_DISTRIBUTION_ENGINE
    if getattr(model, "shapes", None) is None:
        return player_census.BUCKET_NEVER_ASKED, slate.NO_ENGINE_CONSTANTS
    return "", ""


def _read_player_market(
    wager: Wager, distribution: object
) -> tuple[float | None, float, str]:
    """`(probability, push_mass, reason)` for one prop off one cached object.

    The player half of :func:`_read_market`, and deliberately the same shape,
    the same push convention and the same three-way return. **The push counts
    against the bet**: `forward_evidence.expected_value` is `p·(1+payout) − 1`
    and has no push term, so `p = win` understates the edge by exactly the push
    mass — the conservative direction — while `win/(1-push)` would overstate it
    in the flattering direction on precisely the whole-number lines. All ten
    player markets carry `push_possible=True`, `settlement._settle_player_column`
    settles 14 rebounds against a line of 14 as a returned stake, and the engine
    puts exact lattice mass there rather than a density at an integer.

    One `PlayerDistribution` per (event, athlete) is the caller's cache, and it
    is what makes a points rung and a pra rung on one player two questions asked
    of one object rather than two models that can disagree.

    Two refusals reach this function as `MarketRefused` and are printed in the
    engine's own words: R4's line above the count lattice ceiling, and R5's
    market whose constant the fit would not invent. The two markets refused BY
    NAME never get here — `_player_decline` asks about them first, before
    anything about the athlete — and that ordering is asserted in
    `tests/test_gameday_card.py`. A refusal is never turned into `(0, 0, 1)`:
    a confident zero that is an artefact of where a lattice was truncated would
    be the most attractive-looking number on the card.
    """
    engine = _player_distributions_module()
    if engine is None:  # pragma: no cover - the caller has already asked
        return None, 0.0, slate.NO_DISTRIBUTION_ENGINE
    if wager.selection not in (OVER, UNDER):
        return None, 0.0, "the selection does not name a side of this player line"
    line = normalise_line(wager.line)
    if line is None:
        return (
            None,
            0.0,
            "a player prop with no line cannot be read off a count "
            "distribution: there is no rung to price",
        )
    try:
        win, push, _ = distribution.market(
            clean_text(wager.market), float(line), wager.selection
        )
    except engine.PlayerDistributionError as exc:
        return None, 0.0, str(exc)
    return float(win), float(push), ""


def opinions_for(
    wagers: Iterable[Wager],
    matchups: "Mapping[str, object] | slate.SlateModel | None",
    *,
    day: str,
    dispositions: "player_census.RunDisposition | None" = None,
) -> tuple[dict[tuple, float], OpinionCensus]:
    """The probability map, keyed by the frozen selection key, and why not.

    One `GameDistribution` per (game, segment), built once and read many times.
    That is `models/distributions.py`'s central rule — **one game, one object**
    — and it is why a −3.5 and a −6.5 and the moneyline on the same game can
    never disagree here: they are six questions asked of one 2-D array. The
    football lab priced its featured spread from one model and its alternate
    ladder from a normal approximation to that model, and shipped a ladder whose
    −6.5 was better value than its −7.5 for a team it made a favourite. Nothing
    in that output looked wrong.

    Four things stop a game being priced at all, before any market is read:

    1. **No matchup.** No rating exists for this game, so the model was never
       asked about it. That reads `no opinion`, which is not a probability of
       zero and is not the model declining to find value.
    2. **The ratings module refuses.** The schedule graph has not connected
       these two teams by anything but the prior, so any adjusted rating is
       identified by the prior alone. An unpriced game is an honest output; a
       confidently priced one built on no connecting evidence is not.
    3. **The venue state cannot be read.** A game mislabelled neutral is a
       multi-point error applied to every market on it, and "neutral" here has
       three values rather than two — 5.5% of flagged-neutral games in 2025-26
       were in a participant's own city. Unknown quarantines.
    4. **A November price with no recorded prior weight.** See
       :data:`PRIOR_REGIME_MONTHS`.

    **The player half is read from the same object and answers separately.**
    `matchups` is coerced to a :class:`models.slate.SlateModel` — a bare
    mapping, which is what `ratings.matchups_for` and every test double return,
    becomes one with an empty player half — and the two halves are then looked
    up independently. A prop on a game whose spread this function refuses at
    step 2 still prices, which is the property `models/slate.py` exists for and
    which nesting the projections inside `Matchup` made unrepresentable. The
    player branch therefore has to stay **above** the matchup lookup below;
    moving it under makes that state unreachable again.

    **Since 2026-09-06 that branch prices rather than only declining.** A
    priceable projection plus the slate's own provenance-checked constants build
    one `models.player_distributions.PlayerDistribution` per (event, athlete),
    cached here beside `joints`, and every rung on that athlete is read off it.
    **What that changes for the card, stated correctly.** This paragraph used to
    say it changes one number — `census.priced` — and nothing else, and gave the
    selection gate as the reason. That is wrong twice over, and the same
    docstring conceded it four lines later by saying "prices, freezes and
    settles" is now literally true of the player family.

    Three outputs move, not one:

    * `census.priced` counts the props;
    * the returned `probabilities` map now carries a player key per priced rung;
    * `census.push_mass` carries the exact lattice mass on the line beside it,
      which is new for this family — all ten player markets are
      `push_possible=True` and a whole-number rebounds line settles as a
      returned stake.

    And the freeze is **not** behind the selection gate. `run_card` freezes from
    :func:`_rows_to_freeze`, which takes the WAGERS and never consults
    `result.selections`: its three filters are tip state, complete strata and
    best price. `forward_evidence.write_snapshot` is then handed this whole
    `probabilities` map, computes `edge = expected_value(probability,
    american_odds)` per row, and appends `model_probability` and `edge` to
    `priced_snapshots/<day>.csv`. So a player rung this function prices becomes a
    dated, per-wager model-against-price number on disk, in a file that is
    append-only within the day — the first such row can never be re-priced or
    withdrawn. Driven end to end in
    `tests/test_player_distributions.py::test_a_priced_prop_reaches_the_freeze_
    and_the_selection_gate_is_not_what_stops_it`.

    What the selection gate DOES stop is a bet: `gates.can_produce_a_selection`
    is `CONFIRMED`-only and no availability feed exists for Division I men's
    basketball, so no prop can become a selection. It stops nothing upstream of
    that. What stops a shipped nightly run from writing those rows today is
    `price_backtest.DEFAULT_MODEL`, which still resolves the team seam —
    `card_matchups.py` documents moving it as a one-line swap, and
    `scripts/run_gameday_card.py` already passes the full container. That is a
    gate on one constant, not on this function.

    **That was not true when it was written, and the swap alone would have
    priced nothing.** The card's own loader read the eight columns
    `slate.REQUIRED_PLAYER_COLUMNS` declares, which carry no box score, so
    every athlete came back refused under R6; and the frame it handed the model
    as `prices` was `attach_game_ids`' `event_id` and `game_id` — no `market`,
    no `player`, no team ids — so the estimator found no subject to refuse in
    the first place and this function declined every prop with "the model was
    never asked about this event's athletes". Both are closed in
    `card_matchups.py` and measured there; the constant really is the last gate
    now.

    `availability_note`'s "a market the lab prices, freezes and settles but may
    not bet" was aspirational for the player family until this commit. Two of
    its three verbs are now literally true of it — priced here, frozen by
    `run_card`. The third is not this branch's to claim: nothing this engine
    produces has been graded, and design 10's 261,870-wager reconciliation
    gates any grading of it.

    **`dispositions` is design section 10's pre-grading gate, filled here.**
    This is the only function in the tree that decides what became of a prop
    wager, so it is the only one that can say which bucket the wager landed in,
    and the gate needs that from the RUN rather than from the frame the run left
    behind — a frame carries a probability or a blank, and a blank cannot say
    whether the name failed to resolve, the athlete was refused or the market is
    refused by name. When a `models.player_census.RunDisposition` is passed, one
    `file()` call is made per player wager, in exactly one bucket, before the
    loop moves on; `file()` raises on a second filing of the same wager, so
    "exactly one bucket" is enforced at the call and not assumed at the sum.
    Passing nothing files nothing and changes no output, which is what every
    caller that is not about to grade does.

    **This function RAISES `StructuralCheckFailed`.** Design 4's stop rule — the
    single automatic refusal the design puts on the engine's own output — is
    evaluated once, after the loop, over the regular athletes this card priced,
    by :func:`_run_the_structural_check`. It had no caller anywhere outside a
    test until this commit, so a card could price ten markets on an athlete
    whose assembled mixture missed a frozen target it cannot influence and
    nothing said a word. It is a raise and not a census line on purpose: see
    `models.player_distributions.StructuralCheckFailed`.
    """
    probabilities: dict[tuple, float] = {}
    census = OpinionCensus()
    joints: dict[tuple[str, str], distributions.GameDistribution | str] = {}
    # One `PlayerDistribution` per (event_id, athlete_id), built once and read
    # many times — design 2's rule, and the player half of `joints` above. A
    # points rung, a threes rung and a pra rung on one athlete are three
    # questions asked of one object, so they cannot disagree; the football lab
    # shipped a ladder whose -6.5 beat its -7.5 because it had two.
    players: dict[tuple, object] = {}
    in_prior_regime = _month_of(day) in PRIOR_REGIME_MONTHS
    model = slate.SlateModel.coerce(matchups, day=day)

    for wager in wagers:
        census.wagers += 1
        market = MARKETS_BY_KEY.get(wager.market)
        if market is not None and market.family == PLAYER:

            def account(bucket: str, why: str, _wager: Wager = wager) -> None:
                """File this wager in one bucket of the pre-grading identity.

                A closure over the wager rather than five call sites repeating
                the same four arguments: the identity is only as good as its
                being filed on EVERY path out of the player branch, and five
                hand-copied calls is the shape the widened early returns in
                `models/slate.py` had when three of them ran in no test.
                """
                if dispositions is not None:
                    dispositions.file(
                        _wager.key,
                        market=clean_text(_wager.market),
                        bucket=bucket,
                        reason=why,
                    )

            bucket, reason = _player_decline(model, wager)
            if reason:
                census.decline(reason)
                account(bucket, reason)
                continue
            projection = model.projection_for(wager.event_id, wager.player)
            # Keyed on (event, athlete) and NOT on the book's spelling: two
            # spellings of one athlete on one game are one subject — the price
            # store holds 64 folded names carrying two raw spellings each, 4,396
            # wager keys of a book's title-caser — and building a second object
            # for the second spelling would give one player two models whose
            # rungs could disagree.
            #
            # The id comes from `resolved`, which is the mapping `players` is
            # keyed by and the one the seam's own invariant I5 ties to it, not
            # from `projection.athlete_id`: a projection whose field disagreed
            # with its container key would otherwise be built twice under one
            # subject. `_player_decline` has already established that this pair
            # resolves to a priceable projection, so the id is never `None` here.
            subject = (
                clean_text(wager.event_id),
                model.resolved.get((clean_text(wager.event_id), clean_text(wager.player))),
            )
            cached = players.get(subject)
            if cached is None:
                engine = _player_distributions_module()
                try:
                    cached = engine.build(projection, shapes=model.shapes)
                except engine.PlayerDistributionError as exc:
                    # Every one of the ten markets refused, R4's lower half, a
                    # lattice that carries mass at zero minutes: the engine's own
                    # sentence, never a paraphrase and never a price.
                    cached = str(exc)
                except (TypeError, ValueError) as exc:
                    cached = (
                        "the player distribution could not be built for this "
                        f"subject ({exc})"
                    )
                players[subject] = cached
            if isinstance(cached, str):
                # The engine refused the whole subject: every one of the ten
                # markets, R4's lower half, a lattice carrying mass at zero
                # minutes. That is a refusal OF THE ATHLETE and is filed as one
                # -- the same bucket an R2-R6 projection refusal lands in, one
                # level down, and never the row-level bucket.
                census.decline(cached)
                account(player_census.BUCKET_ATHLETE_REFUSED, cached)
                continue
            probability, push, reason = _read_player_market(wager, cached)
            if probability is None:
                said = reason or "the model has no reader for this market"
                # The athlete HAS a distribution and this rung could not be read
                # off it: no side named, no line to price, or the engine
                # refusing this market on this subject (R4's ceiling, R5's
                # constant). A row-level absence, not a statement about him.
                census.decline(said)
                account(player_census.BUCKET_UNREADABLE, said)
                continue
            probabilities[wager.key] = probability
            census.push_mass[wager.key] = push
            census.priced += 1
            account(player_census.BUCKET_PRICED, "")
            continue
        if market is not None and market.family == FUTURES:
            census.decline(
                "a futures market does not settle on tonight's game and is "
                "priced on its own clock, never folded into a card"
            )
            continue

        matchup = model.matchup_for(wager.event_id)
        if matchup is None:
            census.decline(
                "no rating exists for this game — `models/ratings.py` is not "
                "written, so the model was never asked"
            )
            continue
        if not bool(_matchup_field(matchup, "priceable", True)):
            reason = clean_text(_matchup_field(matchup, "unpriceable_reason", ""))
            census.decline(
                "the ratings module refuses to price this matchup"
                + (f": {reason}" if reason else "")
            )
            continue
        venue = clean_text(_matchup_field(matchup, "venue_state", VenueState.UNKNOWN.value))
        if venue in ("", VenueState.UNKNOWN.value):
            census.decline(
                "the venue state is unknown or contradictory, so the game is "
                "quarantined rather than defaulted to neutral"
            )
            continue
        prior = _as_float(_matchup_field(matchup, "prior_weight", None))
        if in_prior_regime and prior is None:
            census.decline(
                "this is a November-regime price and the rating behind it "
                "records no prior weight. A blank prior weight is not zero, and "
                "a November number must never be presentable as a February one"
            )
            continue

        segment = market.segment if market is not None else FULL_GAME
        cached = joints.get((wager.event_id, segment))
        if cached is None:
            try:
                cached = distributions.build(
                    home_points_per_possession=float(
                        _matchup_field(matchup, "home_points_per_possession", 0.0)
                    ),
                    away_points_per_possession=float(
                        _matchup_field(matchup, "away_points_per_possession", 0.0)
                    ),
                    possessions=float(_matchup_field(matchup, "possessions", 0.0)),
                    segment=segment,
                    prior_weight=prior,
                )
            except (distributions.DistributionError, TypeError, ValueError) as exc:
                cached = f"the distribution could not be built ({exc})"
            joints[(wager.event_id, segment)] = cached
        if isinstance(cached, str):
            census.decline(cached)
            continue

        probability, push, reason = _read_market(wager, cached)
        if probability is None:
            census.decline(reason or "the model has no reader for this market")
            continue
        probabilities[wager.key] = probability
        census.push_mass[wager.key] = push
        if prior is not None:
            census.prior_weight[wager.key] = prior
        census.priced += 1

    # Design 4's stop rule, on the only population a run ever has: the athletes
    # this card actually built a distribution for. It runs AFTER the loop and
    # not inside it because the thing being checked is a pooled number over a
    # population — the frozen target is `pooled_vmr` over 242,634 rows of
    # regulars — and there is no population until the loop has finished. It ran
    # nowhere at all until this commit: `assert_structural_checks` had no caller
    # outside its own test file, so design 4's single automatic refusal on the
    # engine's own output could not fire on a card, a backtest or anything else.
    _run_the_structural_check(players, model, census)
    _run_the_resolution_check(model, census)
    return probabilities, census


def _run_the_structural_check(
    players: Mapping[tuple, object],
    model: "slate.SlateModel",
    census: OpinionCensus,
) -> None:
    """Report design 4's ratio, and stop the run when it is off by over 15%.

    `players` is the (event, athlete) cache `opinions_for` filled, so its values
    are one `PlayerDistribution` per subject the card priced, plus the refusal
    STRINGS for the subjects whose engine declined. The strings are dropped
    here: a refused subject produced no mixture, so it has no VMR to pool, and
    counting it would be pooling an absence.

    An object whose `player_points` alone is refused is the same fact one level
    down, and it is `population_structural_checks` that drops it — not this
    function and not a `try` around this call. This line sits outside every
    `except` `opinions_for` owns, so a `MarketRefused` raised while pooling
    would kill the card and every team wager on it; the census bucket is in the
    returned mapping and :func:`_model_section` prints it onto the card through
    :meth:`OpinionCensus.structural_check_line`. That last clause is the one
    this docstring got wrong when the stop was wired: the reporter existed, was
    named here as though it ran, and had no caller anywhere outside a test.

    Silent when the card built nothing — a team-only slate is not a structural
    failure and must not read as one — and silent when the slate carries no
    checked constants, because `population_structural_checks` reads the target
    and the regulars floor out of the frozen file and there is no honest number
    without it. Both of those states leave `census.structural_check` empty, and
    :meth:`OpinionCensus.structural_check_line` says which on the card.
    """
    built = [
        distribution
        for distribution in players.values()
        if not isinstance(distribution, str)
    ]
    if not built or model.shapes is None:
        return
    engine = _player_distributions_module()
    census.structural_check = dict(
        engine.population_structural_checks(built, shapes=model.shapes)
    )
    engine.assert_structural_checks(census.structural_check)


def _run_the_resolution_check(
    model: "slate.SlateModel", census: OpinionCensus
) -> None:
    """Report design 13's per-tier resolution rate, and stop the run at 2pp.

    Design 13's failure mode 5 asks for two things and **neither had a caller**.
    `player_rates.resolution_census` is the report and
    `player_rates.assert_tier_resolution_holds` is the stop, and
    `grep -rn` over `src/` and `scripts/` found both only in
    `tests/test_player_rates.py` — so the single automatic refusal design 13
    puts on the JOIN could not fire on a card, a backtest or anything else, in
    exactly the way design 4's could not until it was given one. The two are
    the same shape of defect and are repaired here side by side.

    Computed over RESOLVED subjects, which is a limitation and not a choice:
    design 9 tiers a player by `conferences.tier_table` on his own team, and an
    unresolved spelling has no team. `player_rates.resolution_census`'s own
    docstring records that, and the refused names are counted apart by
    `untiered_name_refusals` rather than tiered off the event's two sides —
    which would put a read from the team half back into the player half.

    `tiers=None`, so each athlete is tiered by `projection.player_tier`, the
    tier the estimator recorded for him when it resolved him. A `TierTable`
    built here would be a second tiering of the same athlete and could disagree
    with the one in the projection.

    Silent when the model holds no projection: a team-only slate is not a
    biased join and must not read as one. That state leaves
    `census.tier_resolution` empty and
    :meth:`OpinionCensus.tier_resolution_line` says so on the card.
    """
    if not model.players:
        return
    census.tier_resolution = {
        tier: dict(counts)
        for tier, counts in player_rates.resolution_census(
            model.players, tiers=None
        ).items()
    }
    census.untiered_name_refusals = len(model.name_refusals)
    player_rates.assert_tier_resolution_holds(census.tier_resolution)


def _month_of(day: str) -> int:
    try:
        return date.fromisoformat(str(day)[:10]).month
    except (TypeError, ValueError):
        return 0


def _as_float(value: object) -> float | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


# --------------------------------------------------------------------------
# The accounting identity
# --------------------------------------------------------------------------


def reconcile(
    result: SelectionResult,
    *,
    unparseable: int,
    withdrawn_after_pricing: int = 0,
    notes: Iterable[str] = (),
) -> AccountingIdentity:
    """Fold the bars into the six buckets and prove the arithmetic.

    Raises when it does not balance. That is the point of the identity and it
    is why it raises rather than warning: a wager that reaches none of the
    buckets vanished, and a silent drop is how a biased subset becomes the
    record of a night.

    `withdrawn_after_pricing` is the tip guard's second pass — selections that
    cleared every bar and then had their game tip before the card was written.
    They move from `bets` to `gated`, which is what "its stake is removed"
    means arithmetically.
    """
    missing = [bar for bar in BAR_ORDER if bar not in BAR_BUCKETS]
    if missing:
        raise CardError(
            f"{[b.value for b in missing]} has no bucket in BAR_BUCKETS, so it "
            "would vanish from the accounting identity. Every bar lands in "
            "exactly one bucket, and the mapping is data so that this cannot be "
            "true silently."
        )
    identity = AccountingIdentity(
        priced=result.priced_wagers + int(unparseable),
        unparseable=int(unparseable),
        notes=list(notes),
    )
    for bar in BAR_ORDER:
        count = int(result.bar_counts.get(bar.value, 0))
        if not count:
            continue
        bucket = BAR_BUCKETS[bar]
        setattr(identity, bucket, getattr(identity, bucket) + count)
    identity.gated += int(withdrawn_after_pricing)
    identity.bets = len(result.selections) - int(withdrawn_after_pricing)
    identity.raise_if_unreconciled()
    return identity


# --------------------------------------------------------------------------
# One run
# --------------------------------------------------------------------------


@dataclass
class CardRun:
    """Everything one run of the card produced. The renderer reads only this."""

    competition: Competition
    slate_date: str
    card_slot: str
    generated_at: str
    board: Board
    policy: StagingProviderPolicy
    placement: Placement
    opinions: OpinionCensus
    result: SelectionResult
    identity: AccountingIdentity
    tip: TipCensus
    selections: list[dict] = field(default_factory=list)
    withdrawn_after_pricing: list[dict] = field(default_factory=list)
    rehearsal: bool = False
    snapshot_path: Path | None = None
    snapshot_rows_offered: int = 0
    staged_path: Path | None = None
    fingerprint: str = ""
    previous_fingerprint: str = ""
    verdicts_line: str = ""
    #: Games this card could actually be about. Never `Board.events_in_the_read`
    #: — the bulk endpoint returns the whole upcoming board, and reporting
    #: tomorrow's fixtures as tonight's coverage is how a thin night reads as a
    #: full one.
    events_on_this_slate: int = 0
    rows_off_this_slate: int = 0
    degraded: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def decision(self) -> Decision:
        if self.rehearsal:
            return Decision.REHEARSAL
        if self.selections:
            return Decision.SELECTIONS
        if not self.events_on_this_slate:
            return Decision.NO_SLATE
        return Decision.NO_SELECTIONS

    @property
    def is_degraded(self) -> bool:
        return bool(self.degraded or self.board.degraded)

    @property
    def selections_changed(self) -> bool | None:
        """True, False, or None when there is nothing to compare against."""
        if not self.previous_fingerprint:
            return None
        return self.fingerprint != self.previous_fingerprint


def run_card(
    board: Board,
    *,
    competition: Competition,
    day: str,
    card_slot: str,
    archive_dir: Path | str,
    policy: StagingProviderPolicy | None = None,
    matchups: "Mapping[str, object] | slate.SlateModel | None" = None,
    placement: Placement | None = None,
    availability_for: Callable[[Wager], Availability] | None = None,
    now: Callable[[], datetime] | None = None,
    rehearsal: bool = False,
    previous_fingerprint: str = "",
    output_dir: Path | str | None = None,
) -> CardRun:
    """Gate, price, freeze, and account for every row. In that order.

    The order is load-bearing at both ends.

    **The freeze happens before the render**, so a run that cannot write its
    prose still leaves the evidence. Historical prices can be re-bought; a night
    that was not frozen is gone permanently, and in this sport a night is up to
    two hundred games.

    **The tip guard's second pass happens after the bars and before the
    identity**, so a selection whose game tipped while the run was working
    reaches the identity as `gated` rather than as a bet.
    """
    policy = policy if policy is not None else load_policy()
    placement = placement if placement is not None else Placement()
    guard = TipGuard(now)
    key_for = default_key_for(competition)
    generated = (now or (lambda: datetime.now(timezone.utc)))()

    # Only this slate day. The bulk endpoint returns every upcoming game, and a
    # row for tomorrow frozen under today's snapshot date carries tomorrow's
    # slate date in its own key — so it would look unfrozen tomorrow and be
    # priced twice. Counted rather than dropped.
    rows = board.rows
    off_slate = 0
    if not rows.empty and "slate_date" in rows.columns:
        on_day = rows["slate_date"].astype(str) == str(day)
        off_slate = int((~on_day).sum())
        rows = rows.loc[on_day].reset_index(drop=True)

    wagers, unparseable, refusals = build_wagers(
        rows, competition=competition, key_for=key_for, tiers=placement.tiers
    )
    probabilities, opinions = opinions_for(wagers, matchups, day=day)

    # The tip guard is read for **every** wager on the board, not only for the
    # ones that reach it inside `select`. `select` applies its bars in order and
    # `NOT_APPROVED` is first, so on a card with no allowlisted market — which
    # is every card this lab will produce until Cooper signs a receipt — nothing
    # would ever reach the tip check and the card would report an empty tip
    # census on a slate with games already in progress. A gate that is only
    # exercised behind another gate is a gate nobody has seen run.
    for wager in wagers:
        guard.state_for(wager)

    result = select(
        wagers,
        probabilities,
        approved=policy.allows,
        availability_for=availability_for or (lambda _w: Availability.NO_REPORT),
        tip_state_for=guard.state_for,
        threshold=EDGE_THRESHOLD,
        price_band=PRICE_BAND,
    )
    kept, withdrawn = guard.recheck(result.selections)

    # Freeze first. Only wagers whose game is still upcoming: an opinion frozen
    # after tip is not forward evidence, it is a note about a game in progress.
    freezable = _rows_to_freeze(
        wagers, guard=guard, per_event_complete=board.per_event_complete
    )
    # A rehearsal freezes too — into its own archive, which the gameday
    # workflow neither restores nor publishes. Rehearsing everything except the
    # one step that cannot be re-made would rehearse the wrong thing: the
    # freeze is where the append-only-within-a-day rule either holds or does
    # not, and that is exactly what a rehearsal is for.
    snapshot = forward_evidence.write_snapshot(
        freezable,
        probabilities,
        key_for=key_for,
        verdicts_in_force=_verdicts_in_force(competition, output_dir),
        snapshot_date=day,
        archive_dir=archive_dir,
        prior_weights=_by_key(opinions.prior_weight),
        tiers=placement.tiers,
    )

    # `unparseable` is the rows **on this slate day** that could not be grouped
    # into a wager, and nothing else.
    #
    # It is tempting to fold `providers/staging.py`'s refusals in here too, and
    # it would be wrong: those are counted per *outcome* over the whole read,
    # including games on other slate days, and an identity whose two sides
    # describe different populations reconciles over whichever population
    # survived. Staging has its own identity — `outcomes = staged + four
    # refusals` — it reconciles on its own, and the card prints it beside this
    # one. Two links, each over one population, with the count that joins them
    # (`rows_off_this_slate`) printed between them.
    identity = reconcile(
        result,
        unparseable=unparseable,
        withdrawn_after_pricing=len(withdrawn),
        notes=[
            f"{count:,} price row(s) refused when grouped into wagers: {reason}."
            for reason, count in sorted(refusals.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
    )

    enriched = [_enrich(row, opinions, competition=competition) for row in kept]
    return CardRun(
        competition=competition,
        slate_date=day,
        card_slot=card_slot,
        generated_at=generated.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        board=board,
        policy=policy,
        placement=placement,
        opinions=opinions,
        result=result,
        identity=identity,
        tip=guard.census,
        selections=enriched,
        withdrawn_after_pricing=withdrawn,
        rehearsal=bool(rehearsal),
        snapshot_path=snapshot,
        snapshot_rows_offered=len(freezable),
        fingerprint=selection_fingerprint(enriched),
        previous_fingerprint=str(previous_fingerprint or ""),
        events_on_this_slate=(
            int(rows["event_id"].nunique()) if not rows.empty else 0
        ),
        verdicts_line=verdicts.describe(
            competition, output_dir=Path(output_dir) if output_dir else None
        ),
        rows_off_this_slate=off_slate,
        degraded=list(board.degraded),
        notes=list(board.notes),
    )


def _rows_to_freeze(
    wagers: Iterable[Wager], *, guard: TipGuard, per_event_complete: bool
) -> pd.DataFrame:
    """One row per wager, at the best price, for games that have not tipped.

    Built **from the wagers**, never from the board's raw rows, and that is the
    fix for a defect this file had and a test caught. `write_snapshot` keys
    every row it is handed through the injected `key_for`, and `selection_key`
    *raises* on a segment outside the three it knows. Hand it the raw frame and
    a single malformed row — a staged file written by an older stager, or one a
    human edited — takes down the freeze, which is the one step in this whole
    pipeline that cannot be re-made afterwards. `build_wagers` has already
    refused and **counted** those rows; taking its output means only rows that
    survived a guard can ever reach the freeze.

    Three filters, for three separate reasons.

    **Not yet tipped**, because an opinion frozen after tip is not a frozen
    opinion. This is the third continuous reading of the guard in one run and it
    is recorded like the others.

    **One row per wager at the best price**, because `write_snapshot` dedupes on
    the selection key and the selection key does not carry the book: hand it
    every quote and it keeps whichever arrived first, which is the provider's
    bookmaker order — an arbitrary book rather than the price the card would
    have taken. `stores.best_price_per_wager` is the one implementation of
    "best" in this repository, and it is reused rather than reimplemented
    because American odds do not sort numerically. Every book's quote is still
    written to `data/staging/`, which is where the line-shopping and
    price-survival evidence lives.

    **Complete strata only.** When the per-event stage was cut short, the
    markets it carried are a tip-ordered prefix and are withheld from the
    ledger — see :class:`Board`.
    """
    rows: list[dict] = []
    for wager in wagers:
        if not can_be_played(guard.state_for(wager)):
            continue
        if not per_event_complete and wager.market not in BULK_MARKETS:
            continue
        for quote in wager.quotes:
            rows.append(
                {
                    "event_id": wager.event_id,
                    "commence_time": wager.commence_time,
                    "slate_date": wager.slate_date,
                    "home_team": wager.home_team,
                    "away_team": wager.away_team,
                    "market": wager.market,
                    "segment": wager.segment,
                    "player": wager.player,
                    "selection": wager.selection,
                    "line": wager.line,
                    "american_odds": quote.american_odds,
                    "book": quote.book,
                }
            )
    frame = pd.DataFrame(rows, columns=list(FROZEN_COLUMNS))
    if frame.empty:
        return frame
    return stores.best_price_per_wager(frame)


def _by_key(mapping: Mapping[tuple, float]) -> dict:
    """`write_snapshot` looks a value up by frozen key or by event id; this is
    already keyed by frozen key, so it is passed through unchanged."""
    return dict(mapping)


def _verdicts_in_force(
    competition: Competition, output_dir: Path | str | None
) -> tuple[str, ...]:
    """Which recorded policies were shipping when this opinion was frozen.

    A ledger row whose model cannot be reconstructed is an anecdote, so the
    verdicts are frozen into the snapshot beside the price rather than looked up
    later from files that will have moved.
    """
    directory = Path(output_dir) if output_dir else None
    return tuple(
        policy
        for policy in sorted(verdicts.VERDICT_FILES)
        if verdicts.ships(policy, competition, output_dir=directory)
    )


def _enrich(
    row: Mapping, opinions: OpinionCensus, *, competition: Competition
) -> dict:
    """Attach the push mass and the prior's weight to a selection.

    The key is rebuilt through the same `selection_key` both sides of every join
    use, rather than matched on a label. Two hand-built copies of a key is the
    NHL lab's five-member bug family, and a label is a hand-built key with
    prettier punctuation.
    """
    out = dict(row)
    key = default_key_for(competition)(
        SimpleNamespace(
            market=out.get("market", ""),
            selection=out.get("selection", ""),
            line=out.get("line"),
            segment=out.get("segment", FULL_GAME),
            player=out.get("player", ""),
            home_team=out.get("home_team", ""),
            away_team=out.get("away_team", ""),
            commence_time=out.get("commence_time", ""),
        )
    )
    out["push_mass"] = opinions.push_mass.get(key)
    out["prior_weight"] = opinions.prior_weight.get(key)
    return out


# --------------------------------------------------------------------------
# The prose
# --------------------------------------------------------------------------


def mentions_nobody(text: str) -> bool:
    """Whether this text is free of anything that reads as an `@mention`."""
    return _MENTION.search(str(text)) is None


def guard_mentions_nobody(text: str) -> str:
    """Return the text, or raise naming what would have emailed Cooper."""
    match = _MENTION.search(str(text))
    if match is None:
        return text
    raise CardWouldEmail(
        f"The card comment contains {match.group(0).strip()!r}, which reads as "
        "an @mention. A mention overrides an ignored repository subscription, "
        "so this comment would email Cooper however his notification settings "
        "are set. It is refused rather than rewritten: removing the `@` would "
        "mean altering a name, and this lab does not alter names. The frozen "
        "opinions for this slate were written before this check ran and are "
        "unaffected."
    )


def render_card(run: CardRun) -> str:
    """The card itself. Says what it is in its first two lines."""
    lines: list[str] = []
    title = f"CBB card — {run.slate_date} ({run.card_slot})"
    if run.rehearsal:
        lines += [
            f"# {REHEARSAL_LABEL}",
            "",
            f"A rehearsal of the {run.card_slot} card for **{run.slate_date}**. "
            "It settles nothing, it publishes nothing, its frozen opinions go "
            f"to their own archive under `{REHEARSAL_ARCHIVE_SEGMENT}/`, and "
            "nothing below is advice about a game.",
            "",
        ]
    else:
        lines += [f"# {title}", ""]
    lines += [
        ACCUMULATING_NOTE,
        "",
        run.policy.summary_line(run.competition),
        "",
    ]

    lines += _selections_section(run)
    lines += _exposure_section(run)
    lines += _identity_section(run)
    lines += _gates_section(run)
    lines += _board_section(run)
    lines += _model_section(run)
    lines += _what_this_is_not_section(run)
    return "\n".join(lines).rstrip() + "\n"


def _bars_that_stopped_wagers(run: CardRun) -> list[tuple[Bar, int]]:
    """Every bar that stopped at least one wager, in the order they are applied.

    **Read off `result.bar_counts`, never asserted**, for the same reason the
    allowlist line in :func:`_what_this_is_not_section` is read off the policy.
    `select` counts a wager under the **first** bar it meets and then stops
    asking, so this list is the card's whole answer to "why nothing" — and on
    the day a receipt is signed it is a different answer than it is today.
    """
    return [
        (bar, int(run.result.bar_counts.get(bar.value, 0)))
        for bar in BAR_ORDER
        if int(run.result.bar_counts.get(bar.value, 0))
    ]


def _selections_section(run: CardRun) -> list[str]:
    lines = ["## Selections", ""]
    if not run.selections:
        # WHY NOTHING IS READ OFF THE RUN, NOT TYPED INTO THE PROSE. This
        # paragraph asserted the allowlist bar unconditionally until a
        # verification pass reproduced the card it produces with a market
        # allowlisted and every wager stopped at the edge threshold: the header
        # read "allowlists 1 market(s)", the identity table read
        # `not allowlisted = 0`, and this paragraph still told the reader the
        # missing receipt was the reason. A card that names the wrong gate is
        # worse than a card that names none — the reader acts on the reason,
        # and the one reason that must never be invented is the one that says
        # the lab has not yet been asked a question it has in fact answered.
        stopped = _bars_that_stopped_wagers(run)
        barred = sum(count for _, count in stopped)
        only_the_allowlist = len(stopped) == 1 and stopped[0][0] is Bar.NOT_APPROVED
        lines.append("**None.** No wager on this slate cleared every bar.")
        lines.append("")
        if not stopped:
            lines += [
                "No bar was reached, because there was no priced wager on this "
                "slate day to reach one. That is an absence of board coverage "
                "and it is reported as one.",
                "",
            ]
        elif only_the_allowlist:
            lines += [
                f"The first bar every one of them met — all {barred:,} of them "
                "— is that its market is not allowlisted by a reviewed policy. "
                "No later question was asked of any wager on this card.",
                "",
            ]
        else:
            lines += [
                "These are the bars they met, in the order the bars are "
                "applied. A wager is counted under the **first** bar it meets "
                "and is asked nothing after it, so a market stopped by the "
                "allowlist was never put to the model at all:",
                "",
            ]
            lines += [
                f"* {bar.value} — {count:,} wager(s)" for bar, count in stopped
            ]
            lines.append("")
        # The receipt half of the paragraph is the policy's to state, exactly
        # as in `_what_this_is_not_section`.
        if not run.policy.allowlist:
            lines += [
                "That is not a pass, an avoid, or a no-value call, and it is "
                "not the model declining to find value. It is the state this "
                "lab is designed to be in until Cooper signs an acceptance "
                "receipt for a market: **Claude may withdraw an allowlist and "
                "may never grant one.** No selection, no lean, no pass and no "
                "stake.",
                "",
            ]
        else:
            lines += [
                "None of the above is a pass, an avoid, or a no-value call. "
                "Where a gate stopped a market the card names the gate, and "
                "where the edge threshold stopped one that is a statement "
                "about the prices this run could actually reach at card time "
                "and not a view about the bet. **Claude may withdraw an "
                "allowlist and may never grant one.** No selection, no lean, "
                "no pass and no stake.",
                "",
            ]
    else:
        lines += [
            "| Game | Market | Selection | Price | Book | Model | Edge | Push mass | Prior weight | Tier |",
            "|:---|:---|:---|---:|:---|---:|---:|---:|---:|:---|",
        ]
        for row in run.selections:
            push = row.get("push_mass")
            prior = row.get("prior_weight")
            line = "" if row.get("line") is None else f" {float(row['line']):+g}"
            lines.append(
                f"| {row['away_team']} at {row['home_team']} "
                f"| {row['market']} ({row['segment']}) "
                f"| {row['selection']}{line} "
                f"| {float(row['american_odds']):+g} "
                f"| {row['book']} "
                f"| {float(row['model_probability']):.1%} "
                f"| {float(row['edge']):+.2%} "
                f"| {'—' if push is None else f'{float(push):.2%}'} "
                f"| {'not recorded' if prior is None else f'{float(prior):.0%}'} "
                f"| {row['tier']} |"
            )
        lines += [
            "",
            "Each edge is stated **per wager** and none of them is added to "
            "another. A game's spread, its moneyline, both team totals, the "
            "game total and a starter's points are one event seen six ways; "
            "their edges are not additive and their outcomes are not "
            "independent.",
            "",
            "The push mass is the probability the joint distribution puts on "
            "the line landing exactly. The edge above **understates** the true "
            "expectation by that amount, because the one definition of edge in "
            "this repository has no push term and counting the push against the "
            "bet is the conservative direction. It is also the answer to how "
            "much of the number is half a point at a key number rather than a "
            "differing view of the game.",
            "",
        ]
    if run.withdrawn_after_pricing:
        lines += [
            f"**{len(run.withdrawn_after_pricing):,} selection(s) were withdrawn "
            "after pricing** because their game tipped, came inside the "
            f"{IMMINENT_MINUTES}-minute lead, or stopped having a readable tip "
            "time between the board being read and this card being written. "
            "Their stake is removed and they are counted in the identity below:",
            "",
        ]
        lines += [f"* {note}" for note in run.tip.withdrawn_after_pricing]
        lines.append("")
    return lines


def _exposure_section(run: CardRun) -> list[str]:
    """Printed every run, including the runs with nothing on them.

    A cap that is only reported on the night it first binds is a cap nobody has
    read, and one first written on that night is a cap chosen to fit it. Both
    figures here were declared in advance and neither binds today, which is the
    correct order.
    """
    return [
        "## Exposure",
        "",
        run.result.exposure.summary_line(),
        "",
    ]


def _identity_section(run: CardRun) -> list[str]:
    identity = run.identity
    lines = [
        "## The accounting identity",
        "",
        identity.summary_line(),
        "",
        f"The unit is a **wager**, plus the price rows on this slate day that "
        f"could not be made into one: {run.result.priced_wagers:,} wager(s) and "
        f"{identity.unparseable:,} unreadable row(s). A wager is one bet however "
        "many books hang it — twenty-one books quoting one game is not "
        "twenty-one bets, and counting quotes as bets is what made every "
        "interval in the NHL lab's first store √2.83 too narrow.",
        "",
        "**This is the second of two identities and they are deliberately not "
        "merged.** The board section below carries the first, over the "
        "provider's *outcomes*: `outcomes = staged + unwired market + unknown "
        "selection + unreadable price + unplaceable event`. It reconciles on "
        "its own. Folding it into this one would put two populations on either "
        "side of a single equals sign — the outcomes are counted across every "
        "day the read saw, and these wagers are this slate day only — and an "
        "identity whose two sides describe different populations reconciles "
        "over whichever population survived. The count that joins them is the "
        "off-slate figure below.",
        "",
        "| Bar | Wagers | Bucket |",
        "|:---|---:|:---|",
    ]
    for bar in BAR_ORDER:
        count = int(run.result.bar_counts.get(bar.value, 0))
        lines.append(f"| {bar.value} | {count:,} | {BAR_BUCKETS[bar]} |")
    lines.append("")
    if identity.notes:
        lines += ["Rows that could not be read at all:", ""]
        lines += [f"* {note}" for note in identity.notes]
        lines.append("")
    lines += [
        f"{run.rows_off_this_slate:,} staged row(s) belong to a slate day other "
        f"than {run.slate_date} and were not considered here. The bulk endpoint "
        "returns every upcoming game, not tonight's; a row for tomorrow frozen "
        "under today's date would look unfrozen tomorrow and be priced twice.",
        "",
    ]
    return lines


def _gates_section(run: CardRun) -> list[str]:
    lines = ["## The gates, each of which fails closed", ""]
    lines += [
        "**Availability.** " + availability_note(Availability.NO_REPORT),
        "",
        "Measured, not assumed: ESPN's men's-college-basketball injuries "
        "endpoint returns zero records permanently (against 76 for the NBA in "
        "the NBA's own off-season), CollegeBasketballData has no availability "
        "endpoint at all, and the conference reports that do exist cover "
        "roughly 115 of 365 teams, conference games only. Nothing can reach "
        "`confirmed`, so no player prop can produce a selection.",
        "",
        "**Tip time.** " + run.tip.summary_line(),
        "",
        "It is judged twice — once when the bars are applied and once again on "
        "a freshly read clock immediately before this card was written — "
        "because this sport tips games every fifteen minutes for twelve hours "
        "and a slate takes minutes to fetch.",
        "",
        "**Venue.** A game whose venue state is unknown or contradictory is "
        "quarantined rather than defaulted to neutral. Venue has three values "
        "in this sport and not two: of 709 games flagged neutral in 2025-26, 39 "
        "were in a participant's own city and 7 in their own arena.",
        "",
        "**Tier.** " + run.placement.summary_line(),
        "",
        "No pooled headline across the whole of Division I is ever reported. "
        "High-major, mid-major and low-major are different distributions, and "
        "`unplaced` is a state reported separately rather than folded into a "
        "tier's number.",
        "",
    ]
    if run.placement.unresolved_names:
        total = sum(run.placement.unresolved_names.values())
        lines += [
            f"**{len(run.placement.unresolved_names):,} provider team name(s) "
            f"did not resolve**, over {total:,} lookup(s). Each one is a game "
            "this lab cannot place, and a silent loss looks exactly like a "
            "quiet market. The alias map is knowingly incomplete: the "
            "provider's college basketball key was inactive when it was seeded, "
            "so there was no live board to read real spellings off.",
            "",
        ]
    return lines


def _board_section(run: CardRun) -> list[str]:
    board = run.board
    lines = [
        "## The board this card was made from",
        "",
        f"Source: {board.source}.",
        "",
        f"{run.events_on_this_slate:,} game(s) priced on this slate day, out of "
        f"{board.events_in_the_read:,} the read saw — the board carries every "
        "upcoming game, not tonight's. "
        f"{board.counts.staged:,} staged quote(s) over "
        f"{board.counts.events:,} event block(s).",
        "",
        board.counts.summary_line(),
        "",
        board.counts.refusal_table(),
        "",
        board.spend.summary_line(),
        "",
        "The cap is enforced inside the provider adapter before every request, "
        "against the **measured** running total from the response headers, "
        "never against the pre-flight estimate.",
        "",
    ]
    if board.per_event_asked:
        lines += [
            f"Ladders, halves and props were asked for on "
            f"{board.events_asked_per_event:,} of "
            f"{board.events_listed_for_the_slate:,} game(s)"
            + (
                " — **incomplete**, and those rows are staged but not frozen."
                if not board.per_event_complete
                else "."
            ),
            "",
        ]
    for note in board.notes:
        lines += [note, ""]
    if run.snapshot_path is not None:
        lines += [
            f"Frozen: `{run.snapshot_path.name}`, from "
            f"{run.snapshot_rows_offered:,} wager(s) offered. **The first "
            "opinion of the day for a game is never retroactively replaced** — "
            "this run may add a game the earlier slot could not reach and may "
            "never re-price one it did.",
            "",
        ]
    else:
        lines += [
            f"Nothing new was frozen from {run.snapshot_rows_offered:,} wager(s) "
            "offered: every one of them was already frozen for this slate day, "
            "or none could be. A snapshot that already stands is not rewritten.",
            "",
        ]
    if run.staged_path is not None:
        lines += [
            f"The whole board, every book, was written to `{run.staged_path}` — "
            "which the card cannot read. Line shopping and price survival are "
            "measured from there; the freeze keeps one row per wager at the "
            "best price, which is the price this card would have taken.",
            "",
        ]
    return lines


def _model_section(run: CardRun) -> list[str]:
    """What the model said, what it declined, and what its own check reported.

    The third of those is new and it is the half of design 4 that was written
    and never called. `_run_the_structural_check` filled
    `OpinionCensus.structural_check` and raised through
    `assert_structural_checks` when the pooled ratio was off by more than 15%,
    so the STOP was wired; `OpinionCensus.structural_check_line` — the only
    thing that says which of the three states a run was in — was called nowhere
    in `src/` or `scripts/`, and three docstrings said otherwise. A card whose
    check ran over a full population and passed, a card whose population was
    below the floor so the ratio stopped nothing, and a card that built no
    player distribution at all rendered a byte-identical section, which is
    precisely the ambiguity `structural_check_line`'s own docstring exists
    against: a check that silently declines to run is indistinguishable from
    one that passed.

    It is a line and not a bullet under the decline table on purpose. The table
    is one row per REASON A WAGER CARRIES NO OPINION; this is a statement about
    the population the priced ones were built from, and folding it in would put
    a structural report in a column headed "Wagers".

    `OpinionCensus.tier_resolution_line` is the fourth line and the same repair
    for design 13's failure mode 5, whose report half and stop half BOTH had no
    caller: `player_rates.resolution_census` and
    `player_rates.assert_tier_resolution_holds` appeared nowhere in `src/` or
    `scripts/`, so the per-tier join rate the design says to print every run was
    printed on no run and the 2pp stop could not fire on anything.

    `OpinionCensus.event_dispersion_line` is the fifth line and the same shape
    of repair one level down. `POINTS_EVENT_DISPERSION_KEY` chooses between two
    frozen candidates for the scoring-event dispersion, concedes the choice
    moves design 4's produced ratio by 0.167, and twice offered as its
    justification that both numbers are "printed beside each other on every
    run" — and nothing printed either. A rendered card carried neither number
    and not the word "dispersion". It is a DISCLOSURE and not a check: nothing
    stops on it, and it is here because the argument for the constant is made
    out of it.
    """
    lines = [
        "## What the model said",
        "",
        run.opinions.summary_line(),
        "",
        run.opinions.structural_check_line(),
        "",
        run.opinions.tier_resolution_line(),
        "",
        run.opinions.event_dispersion_line(),
        "",
        run.opinions.table(),
        "",
        f"Recorded verdicts in force: {run.verdicts_line}.",
        "",
    ]
    if _month_of(run.slate_date) in PRIOR_REGIME_MONTHS:
        lines += [
            "**This is a November-regime slate.** Roster turnover in this sport "
            "is enormous and the win/loss graph is nearly disconnected between "
            "conferences this early, so a rating now is identified almost "
            "entirely by the preseason prior. Every price on this card carries "
            "the prior's weight beside it, and a price whose rating records no "
            "prior weight is refused rather than shown — a November number must "
            "never be presentable as a February one.",
            "",
        ]
    changed = run.selections_changed
    if changed is None:
        lines += [
            "No earlier card for this slate day was available to this run, so "
            "nothing is claimed about whether the selections changed.",
            "",
        ]
    elif changed:
        lines += [f"**{SELECTIONS_CHANGED}** since the last card for this slate day.", ""]
    else:
        lines += ["The selections are unchanged since the last card for this slate day.", ""]
    return lines


def _what_this_is_not_section(run: CardRun) -> list[str]:
    # The allowlist line is read off the policy rather than asserted. A card
    # that says "no market is allowlisted" while carrying a market's selections
    # would be false on the one day it mattered most, and this lab's whole
    # design is that what ships is auditable against the decision that shipped
    # it rather than asserted in code.
    allowlist = (
        "* No market is allowlisted. Claude may withdraw an allowlist and may "
        "never grant one."
        if not run.policy.allowlist
        else "* Every market above was allowlisted by a reviewed policy with a "
        "human acceptance receipt behind it — verified when the policy was "
        "loaded, not asserted: a receipt file naming the market, citing an "
        "evidence record whose sha256 still matches the file on disk, signed "
        "by a person who is not Claude, and dated. A policy with one "
        "allowlisted market lacking any of that loads manual-only in its "
        "entirety. Claude may withdraw an allowlist and may never grant one."
    )
    return [
        "## What this card is not",
        "",
        "* It is not a recommendation. " + ACCUMULATING_NOTE,
        "* An excluded market is **never** reported as a pass, an avoid, or a "
        "no-value call. Where a market produced nothing, the card says which "
        "gate stopped it.",
        "* No number here is a measured edge. Every number above is a count of "
        "what this run did, and each one is stated with what it is out of.",
        "* Nothing here is wired to a sportsbook, and no bet was placed.",
        allowlist,
        "",
    ]


def render_comment(run: CardRun) -> str:
    """The card as it reaches the feed. Mentions nobody, and is checked.

    The lead exists so a reader who sees only the first line knows the day, the
    slot and whether the run was healthy. Everything after it is the card
    verbatim — the relay copies it without summarising and the chat task
    presents it without ranking anything.
    """
    # THE CARD SPEAKS ONLY FOR ITSELF. It cannot say the RUN was clean,
    # because the run is a workflow with steps either side of this one — the
    # feed refresh before it and settlement after — and this process sees
    # neither. A real dispatch published a comment reading "This run was
    # clean." beside a `latest_status.json` reading `"degraded": "true"`, and
    # both were produced by the same run. The workflow's health step is the
    # single decider; a second opinion here is not a second check, it is a
    # disagreement the reader has to arbitrate.
    #
    # So the lead reports what THIS process observed and names the authority
    # for the rest.
    state = (
        "The card itself rendered with problems."
        if run.is_degraded
        else "The card itself rendered without a problem; `latest_status.json` "
        "carries the run's health, which this process cannot see."
    )
    lead = [
        f"**{run.competition.title} — {run.slate_date}, {run.card_slot} slot.** "
        f"Decision: `{run.decision.value}`. " + state,
        "",
    ]
    if run.is_degraded:
        lead += ["What went wrong:", ""]
        lead += [f"* {note}" for note in (run.degraded or run.board.degraded)]
        lead.append("")
    return guard_mentions_nobody("\n".join(lead) + render_card(run))


def card_path(competition: Competition, outputs_dir: Path | str) -> Path:
    return Path(outputs_dir) / competition.output_name("gameday_card", ".md")


def comment_path(competition: Competition, outputs_dir: Path | str) -> Path:
    return Path(outputs_dir) / competition.output_name("card_comment", ".md")


def state_path(competition: Competition, outputs_dir: Path | str) -> Path:
    """Where the previous run's fingerprint is kept, so `Selections changed`
    fires on a change rather than on every run."""
    return Path(outputs_dir) / competition.output_name("card_state", ".json")


def write_outputs(run: CardRun, outputs_dir: Path | str) -> tuple[Path, Path]:
    """Write the card and the comment. Returns both paths.

    The comment is rendered **first**, so a card that would have emailed Cooper
    raises before either file is written rather than leaving a card on disk
    whose comment the workflow will refuse.
    """
    comment = render_comment(run)
    card = render_card(run)
    directory = Path(outputs_dir)
    directory.mkdir(parents=True, exist_ok=True)
    target_card = card_path(run.competition, directory)
    target_comment = comment_path(run.competition, directory)
    target_card.write_text(card, encoding="utf-8")
    target_comment.write_text(comment, encoding="utf-8")
    return target_card, target_comment
