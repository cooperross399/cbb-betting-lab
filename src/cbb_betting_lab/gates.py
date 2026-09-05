"""The gates that fail closed, and the accounting identity that proves it.

Each gate is the analogue of the NHL lab's "goalie saves needs a confirmed
starter": a market that is modelled, measured, and still cannot produce a
selection, because the lab lacks the feed that would make the bet real.

The rule every gate obeys: **ambiguity falls on the not-a-play side, always.**
A missing or unparseable value is not a reason to let a pick through; it is a
reason to pull it.

And the rule that keeps that from becoming vandalism, which is Cooper's:
**abstain rather than nuke a real slate.** Each gate is per game or per player,
every exclusion is counted, and the identity below reconciles — a selection
that vanishes without appearing in a count is a defect, not a decision.

## The tip-time guard is continuous here, not a single deadline

The sibling labs check one kickoff or one puck drop. This sport tips games
every fifteen minutes for twelve hours: an 11:00 Eastern morning game and a
23:00 Eastern West Coast game are on the same card. So the guard runs against
each game's own tip, on every evaluation, and a card produced at noon carries
opinions on games that have already started **and must not**.

The consequence for the card's design is in `docs/card_cadence.md`: one freeze
a day cannot serve a slate whose games start eleven hours apart, so the card
runs more than once and **the first opinion of the day for a given game is
never retroactively replaced.**

## Availability cannot reach `confirmed`, and that is measured

Investigated 2026-09-01, honestly, expecting to find nothing. What exists:

* **ESPN's injuries endpoint returns an empty array for men's college
  basketball, permanently.** The endpoint is live and structurally present —
  `.../mens-college-basketball/injuries` is HTTP 200 — and carries **zero**
  records, against 76 for the NBA *during the NBA off-season*. The
  college-football sibling endpoint, queried during a live week, held three
  records, two dated 2022 and one 2020, two of them marked `Active`. That is
  abandoned residue, not a feed. Every one of 567 players across 40 D-I rosters
  reported `Active` with an empty `injuries` array.
* **CollegeBasketballData has no injuries, availability or status endpoint at
  all** — 38 paths, none of them availability. Its roster schema has no status
  field.
* **Conference and NCAA player-availability reports are real and narrow.** Eight
  leagues publish them through one third-party iframe vendor with no public
  API, covering roughly **115-120 of 365 teams**, **conference games only**, at
  T-15h and T-2h. The NCAA's own policy applies *only* to championship games.

**That coverage arithmetic is the whole finding.** A model fed this feed would
see a high-major's injuries in January and nothing at all for two hundred
low-major teams, and nothing for anybody in November and December — which is
exactly the window this lab most wants to price. Ingesting it would create the
asymmetric blind spot rather than close it.

So availability is modelled as **unobserved**, and the five states below keep
"a report exists and this player is not on it" strictly apart from "no report
exists at all". A gate that read a missing feed as "nobody is injured" would
clear an entire slate.

**Nothing can reach `CONFIRMED`.** Player props are priced, frozen and settled;
they cannot produce a selection, and the card says so in those words.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

from cbb_betting_lab.schedule_contract import CARD_LEAD_MINUTES


class TipState(str, Enum):
    """Whether a game can still be bet."""

    #: Tip is in the future by more than the safety margin.
    UPCOMING = "upcoming"
    #: Tip is within the safety margin. Treated as started.
    IMMINENT = "imminent"
    #: Tip has passed.
    STARTED = "started"
    #: The commence time is missing or unparseable. **Quarantined.**
    UNCONFIRMED = "unconfirmed"


class Availability(str, Enum):
    """What is known about whether a player will play.

    Five states, and the last two are the ones that matter. They are kept apart
    because collapsing them is how a missing feed becomes a clean slate.
    """

    #: Reachable in principle, reachable in practice by nothing this lab has.
    CONFIRMED = "confirmed"
    #: A report exists and lists the player as out.
    EXCLUDED = "excluded"
    DOUBTFUL = "doubtful"
    QUESTIONABLE = "questionable"
    #: **A report exists for this game and this player is not on it.** Evidence,
    #: not confirmation — a coach may still sit him.
    UNDESIGNATED = "undesignated"
    #: **No report exists at all.** The default for roughly two thirds of D-I
    #: and for every non-conference game. It means nothing is known, and it must
    #: never be read as "nobody is injured".
    NO_REPORT = "no_report"


#: A game tipping inside this many minutes is treated as started, and it is
#: `schedule_contract.CARD_LEAD_MINUTES` — **the same number, read from the one
#: place it is declared**, never a second literal. The historical store was
#: bought at T-60, so every measured number this lab has rests on a price
#: captured at least an hour before tip; a game tipping in sixteen to
#: fifty-nine minutes would be selected at a price the measurement never
#: covered. Until 2026-09-05 this read `15`, and that window was open.
#:
#: The card is also published, read and acted on by a human, and a price on a
#: game tipping in four minutes is not a price anybody can take — the lead
#: covers that too.
IMMINENT_MINUTES = CARD_LEAD_MINUTES


def imminent_note() -> str:
    """The sentence the card prints about what `imminent` means, in numbers."""
    return (
        f"`imminent` is a game tipping inside {IMMINENT_MINUTES} minutes of the "
        f"run — the T-{CARD_LEAD_MINUTES} lead the historical store was bought at "
        "and the lead every measured number rests on — and it carries no stake, "
        "exactly like a game that has already started."
    )


def tip_state(
    commence_time: object, *, now: datetime | None = None
) -> TipState:
    """Whether a game can still be bet, from its own tip time.

    A missing or unparseable commence time returns `UNCONFIRMED`, which
    quarantines. That is not pedantry: the EPL lab had to retrofit this guard
    after a card carried a fixture that had already kicked off.
    """
    moment = now or datetime.now(timezone.utc)
    text = str(commence_time or "").strip()
    if not text:
        return TipState.UNCONFIRMED
    try:
        tip = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return TipState.UNCONFIRMED
    if tip.tzinfo is None:
        # A naive timestamp could be any of three calendars. Guessing one moves
        # every game by up to eight hours, in an unknown direction.
        return TipState.UNCONFIRMED
    delta = (tip - moment).total_seconds() / 60.0
    if delta <= 0:
        return TipState.STARTED
    if delta <= IMMINENT_MINUTES:
        return TipState.IMMINENT
    return TipState.UPCOMING


def can_be_played(state: TipState) -> bool:
    """Only an upcoming game can carry a stake. Ambiguity is not upcoming."""
    return state is TipState.UPCOMING


def can_produce_a_selection(availability: Availability) -> bool:
    """Only a confirmed player may be selected — and nothing reaches confirmed.

    Deliberately written as a real predicate rather than `return False`, so
    that the day a feed exists this is one verdict away from being true, and so
    the reason is legible at the call site.
    """
    return availability is Availability.CONFIRMED


def availability_note(availability: Availability) -> str:
    """The sentence the card prints beside a market this gate blocked."""
    if availability is Availability.CONFIRMED:
        return ""
    if availability is Availability.NO_REPORT:
        return (
            "**cannot produce a selection** — no availability report exists for "
            "this game. Division I men's basketball has no mandated injury "
            "report, and roughly two thirds of the division is never covered by "
            "the conference reports that do exist. This is not a pass, an avoid "
            "or a no-value call: it is a market the lab prices, freezes and "
            "settles but may not bet."
        )
    if availability is Availability.UNDESIGNATED:
        return (
            "**cannot produce a selection** — a report exists for this game and "
            "this player is not on it. That is evidence, not confirmation."
        )
    return (
        f"**cannot produce a selection** — the player is listed "
        f"{availability.value}."
    )


@dataclass
class AccountingIdentity:
    """priced = no_opinion + below_threshold + unparseable + ambiguous + bets.

    Reconciled and printed every run. Its job is to make silence legible: a
    market that produces nothing should say which of five reasons it produced
    nothing for, and a row that reaches none of the five is a defect.
    """

    priced: int = 0
    no_opinion: int = 0
    below_threshold: int = 0
    unparseable: int = 0
    ambiguous: int = 0
    #: Gated: modelled and measured, but the lab lacks the feed to bet it.
    gated: int = 0
    bets: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def accounted(self) -> int:
        return (
            self.no_opinion
            + self.below_threshold
            + self.unparseable
            + self.ambiguous
            + self.gated
            + self.bets
        )

    def reconciles(self) -> bool:
        return self.priced == self.accounted

    def summary_line(self) -> str:
        state = "reconciles" if self.reconciles() else "DOES NOT RECONCILE"
        return (
            f"{self.priced:,} priced = {self.no_opinion:,} no opinion + "
            f"{self.below_threshold:,} below threshold + "
            f"{self.unparseable:,} unparseable + {self.ambiguous:,} ambiguous + "
            f"{self.gated:,} gated + {self.bets:,} bets ({state}"
            + (
                f", off by {self.priced - self.accounted:+,}"
                if not self.reconciles()
                else ""
            )
            + ")."
        )

    def raise_if_unreconciled(self) -> None:
        if not self.reconciles():
            raise ValueError(
                "The accounting identity does not reconcile: "
                + self.summary_line()
                + " A row that reaches none of the six buckets vanished "
                "silently, and a silent drop is how a biased subset becomes "
                "the record of a night."
            )
