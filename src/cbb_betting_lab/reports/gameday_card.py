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
from cbb_betting_lab.competitions import Competition
from cbb_betting_lab.conferences import Tier, TierTable, tier_table
from cbb_betting_lab.gates import (
    AccountingIdentity,
    Availability,
    TipState,
    availability_note,
    can_be_played,
    tip_state,
)
from cbb_betting_lab.markets import FUTURES, MARKETS_BY_KEY, PLAYER, per_event_provider_keys
from cbb_betting_lab.models import distributions
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

#: The workflow's own mention regex, character for character. Written here so
#: the renderer fails on the same string the workflow would fail on, one step
#: earlier and with the offending text named.
_MENTION = re.compile(r"(^|[^A-Za-z0-9_/])@[A-Za-z0-9][A-Za-z0-9-]*", re.MULTILINE)


class CardError(RuntimeError):
    """The card refused. Every subclass says what it refused and why."""


class SlateDateRefused(CardError):
    """A live run was asked to price a day that is not today, without `--rehearsal`."""


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
    side. `models/ratings.py` does not exist yet, so this is a **Protocol**
    rather than a dataclass: declaring the shape costs nothing at runtime,
    keeps the type hints honest, and cannot become a second definition that
    drifts from the real `ratings.Matchup` the day it lands. A duplicated
    dataclass is the `_bonferroni_factor` defect in miniature.

    Until that module exists, no game carries a matchup, every wager is
    `NO_OPINION`, and the card says so in those words rather than pretending
    the model declined.
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
    """
    value = getattr(matchup, name, default)
    return default if value is None and default is not None else value


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
    name of a night, so :meth:`ledger_rows` withholds it. The rows are still
    staged: they were paid for and they are evidence, they are just not a
    stratum.
    """

    rows: pd.DataFrame
    counts: staging.StagingCounts
    spend: Spend
    #: Where the board came from, in words a report can print.
    source: str
    events_on_the_board: int = 0
    events_asked_per_event: int = 0
    per_event_asked: bool = False
    per_event_complete: bool = True
    #: Events whose per-event call failed on its own. Scattered rather than
    #: ordered, so they do not make the stage a prefix.
    events_failed: int = 0
    notes: list[str] = field(default_factory=list)
    degraded: list[str] = field(default_factory=list)

    @property
    def ledger_rows(self) -> pd.DataFrame:
        """The rows that may be frozen: complete strata only. See the class docstring."""
        if self.per_event_complete or self.rows.empty:
            return self.rows
        if "provider_key" not in self.rows.columns:
            return self.rows.iloc[0:0]
        keep = self.rows["provider_key"].astype(str).isin(BULK_SAFE_MARKETS)
        return self.rows.loc[keep].reset_index(drop=True)


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
        events_on_the_board=counts.events,
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
        events_on_the_board=counts.events,
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
    board.events_on_the_board = len(on_the_day)

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
            f"judged — {parts or 'none'}. Only `upcoming` may carry a stake; "
            "`unconfirmed` is a tip time this lab could not read and it "
            "quarantines exactly like a game that has already started."
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
    directory = Path(raw_dir) / competition.data_dir_segment / "schedules"
    schedules: dict[int, pd.DataFrame] = {}
    for path in sorted(directory.glob("mbb_schedule_*.parquet")):
        try:
            schedules[int(path.stem.rsplit("_", 1)[-1])] = pd.read_parquet(path)
        except (OSError, ValueError):
            continue
    if not schedules:
        return Placement(
            note=(
                f"No cached schedule under `{directory}`, so no walk-forward "
                "tier table could be built and every game is `unplaced`. The "
                "card still prices and freezes; it simply cannot stratify, and "
                "an unstratified number is never reported as a D-I headline."
            )
        )

    season = season_for_slate_date(day)
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

    def decline(self, reason: str) -> None:
        self.declined[reason] = self.declined.get(reason, 0) + 1

    def summary_line(self) -> str:
        return (
            f"{self.priced:,} of {self.wagers:,} priced wager(s) carry a "
            "modelled opinion. An absent opinion is **not** a probability of "
            "zero: it is the model declining, or never being asked."
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


def opinions_for(
    wagers: Iterable[Wager],
    matchups: Mapping[str, object] | None,
    *,
    day: str,
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

    1. **No matchup.** No rating exists for this game. That is the state of this
       lab today — `models/ratings.py` is not written — so every wager reads
       `no opinion`, which is not a probability of zero and is not the model
       declining to find value.
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
    """
    probabilities: dict[tuple, float] = {}
    census = OpinionCensus()
    joints: dict[tuple[str, str], distributions.GameDistribution | str] = {}
    in_prior_regime = _month_of(day) in PRIOR_REGIME_MONTHS
    matchups = matchups or {}

    for wager in wagers:
        census.wagers += 1
        market = MARKETS_BY_KEY.get(wager.market)
        if market is not None and market.family == PLAYER:
            census.decline(
                "this lab has no player model, so no player prop carries a "
                "modelled opinion. The prop is priced by the board, frozen and "
                "settled; it is **not** a pass, an avoid or a no-value call"
            )
            continue
        if market is not None and market.family == FUTURES:
            census.decline(
                "a futures market does not settle on tonight's game and is "
                "priced on its own clock, never folded into a card"
            )
            continue

        matchup = matchups.get(wager.event_id)
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
    return probabilities, census


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
    rows_off_this_slate: int = 0
    degraded: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    @property
    def decision(self) -> Decision:
        if self.rehearsal:
            return Decision.REHEARSAL
        if self.selections:
            return Decision.SELECTIONS
        if not self.board.events_on_the_board and self.board.rows.empty:
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
    matchups: Mapping[str, object] | None = None,
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
    freezable = _freezable_rows(board.ledger_rows, day=day, guard=guard)
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

    identity = reconcile(
        result,
        unparseable=unparseable,
        withdrawn_after_pricing=len(withdrawn),
        notes=[
            f"{count:,} price row(s) refused: {reason}."
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
        verdicts_line=verdicts.describe(
            competition, output_dir=Path(output_dir) if output_dir else None
        ),
        rows_off_this_slate=off_slate,
        degraded=list(board.degraded),
        notes=list(board.notes),
    )


def _freezable_rows(
    rows: pd.DataFrame, *, day: str, guard: TipGuard
) -> pd.DataFrame:
    """One row per wager, at the best price, for games that have not tipped.

    Two collapses, for two different reasons.

    **Not yet tipped**, because an opinion frozen after tip is not a frozen
    opinion. **One row per wager at the best price**, because
    `write_snapshot` dedupes on the selection key and the selection key does not
    carry the book: hand it every quote and it keeps whichever arrived first,
    which is the provider's bookmaker order. That is an arbitrary book rather
    than the price the card would have taken. Collapsing here makes the frozen
    price deterministic and makes it the same price `card_pricing.select` reads
    when it takes the best price last. Every book's quote is still written to
    `data/staging/`, which is where the line-shopping and price-survival
    evidence lives.
    """
    if rows.empty:
        return rows
    frame = rows
    if "slate_date" in frame.columns:
        frame = frame.loc[frame["slate_date"].astype(str) == str(day)]
    if frame.empty:
        return frame
    upcoming = frame["commence_time"].map(
        lambda t: can_be_played(tip_state(t, now=guard.now()))
    )
    frame = frame.loc[upcoming]
    if frame.empty:
        return frame
    return stores.best_price_per_wager(frame.reset_index(drop=True))


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
    lines += _identity_section(run)
    lines += _gates_section(run)
    lines += _board_section(run)
    lines += _model_section(run)
    lines += _what_this_is_not_section(run)
    return "\n".join(lines).rstrip() + "\n"


def _selections_section(run: CardRun) -> list[str]:
    lines = ["## Selections", ""]
    if not run.selections:
        lines += [
            "**None.** No wager on this slate cleared every bar, and the first "
            "bar every one of them met is that its market is not allowlisted by "
            "a reviewed policy.",
            "",
            "That is not a pass, an avoid, or a no-value call, and it is not "
            "the model declining to find value. It is the state this lab is "
            "designed to be in until Cooper signs an acceptance receipt for a "
            "market: **Claude may withdraw an allowlist and may never grant "
            "one.** No selection, no lean, no pass and no stake.",
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
            "after pricing** because their game tipped, became imminent, or "
            "stopped having a readable tip time between the board being read and "
            "this card being written. Their stake is removed and they are "
            "counted in the identity below:",
            "",
        ]
        lines += [f"* {note}" for note in run.tip.withdrawn_after_pricing]
        lines.append("")
    return lines


def _identity_section(run: CardRun) -> list[str]:
    identity = run.identity
    lines = [
        "## The accounting identity",
        "",
        identity.summary_line(),
        "",
        f"The unit is a **wager**, plus the price rows that could not be made "
        f"into one: {run.result.priced_wagers:,} wager(s) and "
        f"{identity.unparseable:,} unreadable row(s). A wager is one bet however "
        "many books hang it — twenty-one books quoting one game is not "
        "twenty-one bets, and counting quotes as bets is what made every "
        "interval in the NHL lab's first store √2.83 too narrow.",
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
    if run.rows_off_this_slate:
        lines += [
            f"{run.rows_off_this_slate:,} staged row(s) belong to a slate day "
            f"other than {run.slate_date} and were not considered here. The "
            "bulk endpoint returns every upcoming game; a row for tomorrow "
            "frozen under today's date would look unfrozen tomorrow and be "
            "priced twice.",
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
        f"{board.events_on_the_board:,} game(s) on this slate day; "
        f"{board.counts.staged:,} staged quote(s) over "
        f"{board.counts.events:,} event block(s).",
        "",
        board.counts.summary_line(),
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
            f"{board.events_asked_per_event:,} of {board.events_on_the_board:,} "
            "game(s)"
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
    lines = [
        "## What the model said",
        "",
        run.opinions.summary_line(),
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
        "* No market is allowlisted. Claude may withdraw an allowlist and may "
        "never grant one.",
        "",
    ]


def render_comment(run: CardRun) -> str:
    """The card as it reaches the feed. Mentions nobody, and is checked.

    The lead exists so a reader who sees only the first line knows the day, the
    slot and whether the run was healthy. Everything after it is the card
    verbatim — the relay copies it without summarising and the chat task
    presents it without ranking anything.
    """
    lead = [
        f"**{run.competition.title} — {run.slate_date}, {run.card_slot} slot.** "
        f"Decision: `{run.decision.value}`. "
        + ("This run was degraded." if run.is_degraded else "This run was clean."),
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
