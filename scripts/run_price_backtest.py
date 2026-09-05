#!/usr/bin/env python3
"""Score the bought historical prices against the model, walk-forward.

    # Re-render the report from the record it was already measured into.
    # Touches no network, re-scores nothing, spends nothing:
    PYTHONPATH=src python scripts/run_price_backtest.py --rebuild-report-only

    # Score the card-window store against the model:
    PYTHONPATH=src python scripts/run_price_backtest.py

    # One window, some seasons, a model that is not the default:
    PYTHONPATH=src python scripts/run_price_backtest.py \
        --window card --seasons 2024,2025,2026 \
        --model cbb_betting_lab.models.ratings:matchups_for

This is the entry point for `cbb_betting_lab.reports.price_backtest`, which owns
every number. **This file owns the wiring**, and the wiring is where the three
sibling labs actually lost their measurements: a distribution loaded outside the
season loop, a store deduplicated on its timestamps, a settlement column that had
never been built reading as a zero. Each of those produced a report that looked
finished.

It spends nothing and opens no socket. Historical prices are bought by
`scripts/buy_historical_prices.py`; this reads what that bought.

## The order this script runs in, and why each step is where it is

1. **The store, one bet per wager, at the best price.** `one_bet_per_wager` is
   `assert_single_window` then `dedupe_prices` then `best_price_per_wager`, and
   none of the three is optional. Seventeen books quoting one game is not
   seventeen bets: counting quotes as bets put 2.83 of them on every selection
   in the NHL lab's first store and made every interval about √2.83 too narrow.
   Run per quote its three team markets were demonstrated losses; run per wager
   all three spanned zero. **The collapse happens before the model is asked**,
   so the model prices the wager the card would actually take.
2. **Walk-forward, through `walk_forward`, checked by `assert_walk_forward`.**
   The pricer is never handed the whole table; it gets one day and the games
   strictly earlier than it. Every row comes back stamped with the day it was
   priced through, and the stamp is what the assertion reads — not the code
   path, because the code path is exactly what was wrong in the lab this guard
   is ported from.
3. **Grade every wager the board offered**, not only the ones the model liked.
   The null baseline is computed over the whole graded universe and it has to
   exist before any model number is looked at.
4. **The null baseline first.** *"The question that broke the football lab's
   best result was never 'is this robust'. It was — what would betting one side
   with no model at all return?"* So it is printed above every model figure on
   stdout, in the same order `render` prints it in the report.
5. **Per market and per conference tier.** Never a pooled Division I headline.
   The pooled figure exists because `docs/when_this_ends.md` applies the
   stopping rule to it, and it is printed under a caveat that says in words that
   it is never the headline.
6. **Family-wise correction from the experiment ledger's cumulative count**,
   through `looks_from_ledger`, reported beside the raw figure. Never the day's
   count.
7. **Half a point at a measured key number, apart from a view of the game.**
   The key numbers are measured from the games this store covers; a hardcoded
   {3, 7} would be a fact about football.

## The model is named, not written here

`gameday_card.opinions_for` is the one function in this repository that turns a
rating into a probability, and this script calls **that** rather than reading a
distribution itself. If the backtest read markets off a joint by hand it would
be a second pricer, free to disagree with the card about what the card's own
opinion was — and the football lab shipped a ladder whose −6.5 was better value
than its −7.5 for exactly that reason, with nothing in the output looking wrong.

So what this script needs from a model is only what `opinions_for` needs: a
**matchup per event**. `--model` names it as `module:attribute`, and the callable
is invoked once per slate day with the keyword arguments it declares, out of:

``day``
    The slate day being priced, `YYYY-MM-DD`.
``history``
    `cbb_team_games.csv` rows for games **strictly earlier** than that day, and
    nothing else. This is the walk-forward guarantee, given as a signature
    rather than as a convention.
``prices``
    That day's wagers, so the model knows which events it is being asked about.
``competition``
    The registry entry, for a model that wants it.

It returns a mapping of `event_id` to a matchup object carrying
`home_points_per_possession`, `away_points_per_possession`, `possessions`,
`priceable`, `unpriceable_reason`, `venue_state` and `prior_weight` — read with
`getattr`, so a partially populated matchup declines rather than raising.

**`models/ratings.py` is not written yet.** When it is absent this script says so
and exits non-zero. It does not fall back to a pricer of its own: a backtest that
quietly measures a different model from the one the card runs is worse than no
backtest, and an empty report reads as a null result.

## Nothing to measure is an exit code, never an empty report

The purchase may still be running. A missing store, a store with no rows, or
processed tables that are not there yet each end this script with a message and a
**non-zero exit**, and nothing is written. An empty report reads as a null
result and a null result is a claim.

Zero *bets* is treated the same way when the cause is that the model had an
opinion on nothing, because that is a wiring fault wearing a finding's clothes —
the football lab's props backtest reported zero bets and had it read as "the
model never disagrees enough with the market" when in truth its price columns
had never been built. When the model *did* have opinions and none of them
cleared the threshold declared in advance, that is a finding and the run
succeeds.

## The accounting identity is printed every run

    wagers offered = unparseable + no opinion + below threshold + bets

reconciled, and the run exits non-zero if it does not reconcile. A wager that
reaches none of those four buckets has vanished, and a silent drop is how a
measurement ends up describing a sixth of a store as if it were all of it.

## `--rebuild-report-only`, so improving a sentence never costs a re-run

The retention probe's rule, and it applies with more force here: this run walks
every slate day of six seasons and grades every wager in the store. A report
that can only be produced by re-running the measurement is a report nobody
improves, and a hand-edited generated file survives exactly one re-run. So the
record is written first and `render` is a pure function of it; this flag reads
the record and writes the markdown, scoring nothing.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import (
    DEFAULT_COMPETITION_KEY,
    Competition,
    competition_for,
)
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR
from cbb_betting_lab.forward_evidence import normalise_person, profit_units

# Three names from `forward_evidence` that are private and are imported rather
# than copied, deliberately. `_ROW_FOR_SELECTION` and `_SEGMENT_SETTLED` encode
# the two facts that make settlement dangerous — every quantity in
# `cbb_team_games.csv` is signed for its own team, so settling a home wager from
# the away row negates the margin and swaps the team total; and the two
# first-basket markets settle from the segments table rather than the team-games
# table. A second copy of either would drift, and the direction it drifts in
# gives a plausible number and the wrong bet with nothing raising.
# `price_backtest` imports `stores._decimal_payout` for the same reason.
from cbb_betting_lab.forward_evidence import _ROW_FOR_SELECTION as ROW_FOR_SELECTION
from cbb_betting_lab.forward_evidence import _SEGMENT_SETTLED as SEGMENT_SETTLED
from cbb_betting_lab.markets import MARKETS_BY_KEY, PLAYER
from cbb_betting_lab.providers import historical as H
from cbb_betting_lab.reports import calibration_on_selected as CAL
from cbb_betting_lab.reports import card_pricing, gameday_card
from cbb_betting_lab.reports import forecast_skill as FS
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.season import clean_text
from cbb_betting_lab.settlement import Outcome, settle


#: The model seam is the library's, not this script's. `DEFAULT_MODEL`,
#: `MODEL_ARGUMENTS`, `resolve_model`, `call_model` and `ModelNotWired` live in
#: `reports/price_backtest.py` so the gameday card prices through exactly the
#: callable this measurement does; they are re-exported here because
#: `run_replication.py` and the tests read them off this module.
DEFAULT_MODEL = PB.DEFAULT_MODEL
MODEL_ARGUMENTS = PB.MODEL_ARGUMENTS
ModelNotWired = PB.ModelNotWired
resolve_model = PB.resolve_model
call_model = PB.call_model

#: What a run actually reads out of the price store. Every column the wager
#: identity, the join, the grade or the tier split needs, and nothing else —
#: this store runs to tens of millions of rows across six seasons, and the
#: columns left behind are long strings (school names, two timestamps, the
#: provider's own key) that no step here consults. `--seasons` is the other
#: lever: a store too large to hold at once is scored a season at a time.
STORE_COLUMNS: tuple[str, ...] = (
    "event_id",
    "market",
    "segment",
    "player",
    "selection",
    "line",
    "book",
    "snapshot_phase",
    "american_odds",
    "game_id",
    "season",
    "slate_date",
    "commence_time",
    "home_team",
    "away_team",
    "tier",
)

#: The processed tables every run needs: `team_games` settles every team market
#: and `game_segments` settles the two first-basket markets. A missing one is
#: refused rather than worked around, because grading without it settles every
#: row as "no game matches", which does not fail — it succeeds quietly and
#: wrongly, and a measurement built on that still prints an interval.
REQUIRED_TABLES: tuple[str, ...] = ("team_games", "game_segments")

#: Loaded only when the store actually holds a player market. It is 208 MB and
#: wave 1 of the purchase is team markets, so reading it unconditionally would
#: cost a minute of every run to settle nothing.
PLAYER_TABLE = "player_games"

#: Exit codes, so a workflow can tell the three failures apart.
EXIT_OK = 0
EXIT_NOTHING_TO_MEASURE = 2
EXIT_NO_MODEL = 3
EXIT_NO_OPINION = 4


class NothingToMeasure(RuntimeError):
    """A precondition is absent, so nothing was scored and nothing was written."""


# --------------------------------------------------------------------------
# Counting every wager, into exactly one bucket
# --------------------------------------------------------------------------


#: The per-row refusal `card_pricing.build_wagers` reports, stamped onto every
#: priced row: the reason the row could not become a wager, or the empty string
#: when it did. It carries no probability and no bet either way; it exists so
#: the unparseable term of the accounting identity is **counted off the frame**
#: rather than derived from the other three.
UNPARSEABLE_COLUMN = "unparseable_reason"


def _reason_lines(what: str, reasons: Mapping[str, int], *, most: int = 6) -> list[str]:
    """The commonest reasons, largest first, and how many are not shown."""
    if not reasons:
        return []
    ordered = sorted(reasons.items(), key=lambda kv: (-kv[1], kv[0]))
    lines = [f"  why {what}:"]
    lines += [f"    {count:,} x {reason}" for reason, count in ordered[:most]]
    if len(ordered) > most:
        lines.append(f"    and {len(ordered) - most:,} further reason(s)")
    return lines


class AccountingDoesNotReconcile(RuntimeError):
    """The four buckets do not add up to the wagers the board offered."""


@dataclass
class OpinionAccounting:
    """`offered = unparseable + no opinion + below threshold + bets`, reconciled.

    The sibling labs' rule, and this lab's `gameday_card` refuses a card whose
    identity does not reconcile. It matters more here than on a card: a wager
    that reached none of the buckets has vanished from a *measurement*, and a
    measurement that silently lost a third of its rows still prints an interval.

    **Every term is counted from the frame, and none is the residual of the
    others.** Until 2026-09-05 the caller set two of them by subtraction —

        accounting.no_opinion = max(len(priced) - opinions - unparseable, 0)
        accounting.below_threshold = max(opinions - accounting.bets, 0)

    — which makes the sum identically `len(priced)` whatever the frames hold.
    The identity then reconciled by construction and could never have detected
    the loss it exists to detect: drop a third of the rows between the pricer
    and the grader and it still printed `reconciles yes`. :meth:`count_from`
    reads all four off the graded frame with one row landing in exactly one
    bucket, and :meth:`check` raises rather than warns.
    """

    offered: int = 0
    unparseable: int = 0
    no_opinion: int = 0
    below_threshold: int = 0
    bets: int = 0
    #: The pricer's own running tally of rows `card_pricing.build_wagers`
    #: refused, accumulated day by day. It is a **second, independent** count of
    #: the same quantity :meth:`count_from` reads off the frame, and the two are
    #: compared: a row that was refused during pricing and then disappeared
    #: before grading leaves the tally high and the frame count low.
    unparseable_declared: int = 0
    #: How many rows the bets frame the report measures actually holds. `-1`
    #: means no frame was supplied and the cross-check is not made.
    bets_in_hand: int = -1
    #: Grouped, never one line per wager. Thirty-five markets over six seasons
    #: is millions of rows, and one line each is noise that hides the line that
    #: matters.
    unparseable_reasons: dict[str, int] = field(default_factory=dict)
    declined_reasons: dict[str, int] = field(default_factory=dict)
    #: How many priced wagers carry a recorded preseason-prior weight. Reported
    #: because a November number must never be readable as a February one.
    with_prior_weight: int = 0

    def refuse(self, reasons: Mapping[str, int]) -> None:
        for reason, count in reasons.items():
            self.unparseable_reasons[reason] = (
                self.unparseable_reasons.get(reason, 0) + int(count)
            )

    def decline(self, reasons: Mapping[str, int]) -> None:
        for reason, count in reasons.items():
            self.declined_reasons[reason] = (
                self.declined_reasons.get(reason, 0) + int(count)
            )

    def count_from(
        self,
        frame: pd.DataFrame,
        *,
        threshold: float,
        bets: pd.DataFrame | None = None,
    ) -> None:
        """Bucket every row of the graded frame. Four counts, four predicates.

        The predicates are disjoint and exhaustive over `frame` by construction,
        in this priority: a row that cleared the threshold is a **bet** (read
        with `price_backtest.bet_mask`, the one predicate `bets_from` uses, so
        "a bet" here and "a bet" in the report cannot be two different cuts);
        of the rest, a row `build_wagers` refused is **unparseable**; a row with
        no model probability is **no opinion**; the remainder had an opinion
        that did not clear the threshold. Nothing is subtracted, so the sum is a
        real count of `frame` and comparing it to `offered` is a real test.

        `bets` is the frame the report will actually measure. It is recorded so
        the identity can check that the bucket and the frame hold the same rows:
        setting `self.bets = len(bets)` and deriving the neighbouring bucket
        from it — which is what this file did until 2026-09-05 — makes a bet
        lost between `bets_from` and here reappear as a below-threshold wager,
        and the identity reconciles while the report measures one bet fewer.

        **What `offered == unparseable + no opinion + below threshold + bets`
        does and does not prove.** The four predicates are disjoint and
        exhaustive over `frame` by construction, so `accounted` is always
        exactly `len(frame)` and the identity is really the single comparison
        `len(frame) == offered`. That is a real test and it is the one the
        residual arithmetic could not make: it fails the moment a row the board
        offered is not in the graded frame — dropped by a merge, a filter, a
        dtype coercion, a re-index. It does **not** test that the four buckets
        are the right buckets. A row mis-bucketed, an edge threshold read wrong,
        a `bet_mask` that admits the wrong rows: all of those move a row from
        one term to another and the sum is unchanged, so this identity is blind
        to every one of them. Two further comparisons in :meth:`reconciles` are
        not blind, because each is a **second, independently produced count** of
        one term rather than a rearrangement of the same one:
        `unparseable == unparseable_declared` against the pricer's own running
        tally, and `bets == bets_in_hand` against the frame the report measures.
        The bucketing itself is pinned by the tests, not by this arithmetic —
        `test_run_price_backtest.py::
        test_the_accounting_identity_counts_every_term_from_the_frame` and
        `::test_a_dropped_row_makes_the_identity_fail_rather_than_absorb`, which
        empties each of the four buckets by one row in turn.
        """
        if bets is not None:
            self.bets_in_hand = int(len(bets))
        if frame.empty:
            self.unparseable = self.no_opinion = 0
            self.below_threshold = self.bets = 0
            return
        taken = PB.bet_mask(frame, threshold=float(threshold))
        refused = (
            frame[UNPARSEABLE_COLUMN].astype(str).str.strip().ne("")
            if UNPARSEABLE_COLUMN in frame.columns
            else pd.Series(False, index=frame.index)
        )
        has_opinion = pd.to_numeric(
            frame["model_probability"]
            if "model_probability" in frame.columns
            else pd.Series(index=frame.index, dtype="float64"),
            errors="coerce",
        ).notna()
        rest = ~taken
        self.bets = int(taken.sum())
        self.unparseable = int((rest & refused).sum())
        self.no_opinion = int((rest & ~refused & ~has_opinion).sum())
        self.below_threshold = int((rest & ~refused & has_opinion).sum())

    @property
    def accounted(self) -> int:
        return self.unparseable + self.no_opinion + self.below_threshold + self.bets

    @property
    def reconciles(self) -> bool:
        return (
            self.accounted == self.offered
            and self.unparseable == self.unparseable_declared
            and (self.bets_in_hand < 0 or self.bets == self.bets_in_hand)
        )

    def check(self) -> None:
        """Raise unless the identity holds. An error, never a warning.

        A measurement that silently lost rows still prints an interval, so a
        soft landing here is worse than no measurement at all.
        """
        if self.reconciles:
            return
        if self.accounted != self.offered:
            raise AccountingDoesNotReconcile(
                f"{self.accounted:,} wager(s) reached one of the four buckets "
                f"and {self.offered:,} were offered. A wager that reached none "
                "of them has vanished between the board and the measurement."
            )
        if self.unparseable != self.unparseable_declared:
            raise AccountingDoesNotReconcile(
                f"the pricer refused {self.unparseable_declared:,} row(s) as "
                f"unparseable and {self.unparseable:,} such row(s) survive in "
                "the graded frame. The two counts are of the same quantity, so "
                "they disagree only when rows were lost or re-labelled after "
                "pricing."
            )
        raise AccountingDoesNotReconcile(
            f"the bets bucket holds {self.bets:,} wager(s) and the frame the "
            f"report measures holds {self.bets_in_hand:,}. Both are the rows "
            "`price_backtest.bet_mask` marks, so they differ only when a bet "
            "was lost between selecting them and counting them — and a bet "
            "lost there used to reappear as a below-threshold wager and "
            "reconcile."
        )

    def lines(self) -> list[str]:
        out = [
            "Accounting identity — offered = unparseable + no opinion + "
            "below threshold + bets:",
            f"  wagers offered           {self.offered:,}",
            f"  unparseable              {self.unparseable:,}",
            f"  no opinion               {self.no_opinion:,}",
            f"  below the edge threshold {self.below_threshold:,}",
            f"  bets                     {self.bets:,}",
            f"  reconciles               {'yes' if self.reconciles else 'NO'} "
            f"({self.accounted:,} accounted of {self.offered:,} offered; "
            f"{self.unparseable_declared:,} refused by the pricer; "
            f"{self.bets_in_hand:,} bet(s) in the measured frame)",
        ]
        # Grouped by reason and printed rather than only counted. A store where
        # a third of the rows are unparseable is a wiring signal, and a count
        # with no reason beside it is a number nobody can act on.
        out += _reason_lines("unparseable", self.unparseable_reasons)
        out += _reason_lines("no opinion", self.declined_reasons)
        return out


@dataclass
class GradingCensus:
    """Why a wager the board offered did not become a graded bet.

    `UNSETTLEABLE` is never a loss, a pass, an avoid or a no-value call. It is
    this lab admitting it could not grade the row, and it is counted and stated.
    """

    rows: int = 0
    graded: int = 0
    won: int = 0
    lost: int = 0
    push: int = 0
    void: int = 0
    unsettleable: int = 0
    no_fixture: int = 0
    ambiguous_player: int = 0
    #: A prop whose player name resolves to nobody on either team's box score
    #: for that game. Unknown, not a did-not-play: `void` is the book's
    #: treatment of a listed player who did not enter, and this lab only says
    #: it about a player it has actually found, marked `did_not_play`.
    unresolved_player: int = 0
    unreadable_price: int = 0
    errors: dict[str, int] = field(default_factory=dict)
    reasons: dict[str, int] = field(default_factory=dict)

    def note(self, reason: str) -> None:
        text = reason[:160]
        self.reasons[text] = self.reasons.get(text, 0) + 1

    def lines(self) -> list[str]:
        out = [
            f"Grading — {self.graded:,} of {self.rows:,} wagers carry a book's "
            "verdict:",
            f"  won {self.won:,} / lost {self.lost:,} / push {self.push:,} / "
            f"void {self.void:,}",
            f"  unsettleable {self.unsettleable:,} — never a loss, never a "
            "pass, never an avoid",
        ]
        if self.no_fixture:
            out.append(
                f"  of those, {self.no_fixture:,} name a game the processed "
                "tables do not carry"
            )
        if self.ambiguous_player:
            out.append(
                f"  {self.ambiguous_player:,} name a player who matches more "
                "than one athlete in the game; ambiguity is never a coin flip"
            )
        if self.unresolved_player:
            out.append(
                f"  {self.unresolved_player:,} name a player who resolves to "
                "nobody on either team's box score; an unresolved name is "
                "unknown, not a did-not-play, so it is never a void"
            )
        if self.unreadable_price:
            out.append(
                f"  {self.unreadable_price:,} won at a price this lab cannot "
                "read, so the profit is missing rather than zero"
            )
        out += _reason_lines("a wager could not be graded", self.reasons)
        for message, count in sorted(
            self.errors.items(), key=lambda kv: (-kv[1], kv[0])
        )[:5]:
            out.append(f"  settle raised {message} on {count:,} row(s)")
        return out


# --------------------------------------------------------------------------
# Resolving the model
# --------------------------------------------------------------------------


# --------------------------------------------------------------------------
# The walk-forward pricer
# --------------------------------------------------------------------------


def make_price_day(
    model: Callable,
    *,
    competition: Competition,
    accounting: OpinionAccounting,
) -> Callable[..., pd.DataFrame]:
    """The `price_day` callable `walk_forward` drives, one slate day at a time.

    It returns **every** row of the day, priced or not, with a
    `model_probability` that is missing where the model declined. A missing
    probability is not a probability of zero — the difference is the difference
    between "the model declines" and "the model is certain the bet loses" — and
    returning only the priced rows would drop the rest of the day out of the
    universe the null baseline is computed over.

    The key on both sides is built by the **same** callable the card and the
    freeze use. Two hand-built copies of a join key is the NHL lab's
    five-member bug family — provider names against abbreviations, UTC dates
    against league dates, `home -1.5` against `home_minus`, outcomes staged in
    the wrong vocabulary, and a CSV round-trip turning an empty player into the
    string `"nan"` — and every member of it failed silently.
    """
    key_for = card_pricing.default_key_for(competition)

    def price_day(*, day: str, history: pd.DataFrame, prices: pd.DataFrame):
        frame = prices.copy()
        matchups = call_model(
            model,
            day=day,
            history=history,
            prices=frame,
            competition=competition,
        )
        row_reasons: list[str] = []
        wagers, unparseable, reasons = card_pricing.build_wagers(
            frame, competition=competition, key_for=key_for,
            row_reasons=row_reasons,
        )
        accounting.unparseable_declared += int(unparseable)
        accounting.refuse(reasons)
        # Stamped on the row rather than only counted, so the accounting
        # identity can count its unparseable bucket off the same frame it
        # counts the other three off. A term derived from the others is not a
        # term, and an identity whose terms are derived cannot fail.
        frame[UNPARSEABLE_COLUMN] = pd.Series(
            row_reasons, index=frame.index, dtype="object"
        )

        probabilities, census = gameday_card.opinions_for(
            wagers, matchups or {}, day=day
        )
        accounting.decline(census.declined)

        keys = []
        for record in frame.to_dict("records"):
            try:
                # `card_pricing._row` is private and is called rather than
                # re-implemented: it is what normalises a CSV round-trip's
                # `"nan"` player and NaN line before the key is built. A second
                # normalisation here would be a sixth member of the join-key bug
                # family, and every existing member failed silently.
                keys.append(key_for(card_pricing._row(record)))
            except (TypeError, ValueError):
                # Counted by `build_wagers` as unparseable already; here it is
                # simply a row no probability can be attached to.
                keys.append(None)
        accounting.with_prior_weight += sum(
            1 for k in keys if k is not None and k in census.prior_weight
        )
        frame["model_probability"] = pd.to_numeric(
            pd.Series(
                [None if k is None else probabilities.get(k) for k in keys],
                index=frame.index,
                dtype="object",
            ),
            errors="coerce",
        )
        frame["prior_weight"] = pd.to_numeric(
            pd.Series(
                [None if k is None else census.prior_weight.get(k) for k in keys],
                index=frame.index,
                dtype="object",
            ),
            errors="coerce",
        )
        return frame

    return price_day


# --------------------------------------------------------------------------
# Grading
# --------------------------------------------------------------------------


def _as_int(value: object) -> int | None:
    text = clean_text(value)
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def fixture_index(
    team_games: pd.DataFrame, game_segments: pd.DataFrame, game_ids: set
) -> dict[int, dict]:
    """`game_id` -> both team-games perspectives and the game-segments row.

    Joined on `game_id`, which the purchase already resolved and wrote onto
    every price row, so this needs no team-name resolution and — deliberately —
    no agreement between two tables about what day a game was played on. A
    fixture lookup that silently depended on the calendar would drop exactly the
    late West Coast games the day boundary was measured against.

    **Both perspectives are kept.** Every quantity in `cbb_team_games.csv` is
    signed for its own team, so a home wager settled from the away row negates
    the margin and swaps the team total: a plausible number, the wrong bet, and
    nothing raises.
    """
    bundles: dict[int, dict] = {}
    if team_games is None or team_games.empty or not game_ids:
        return bundles
    wanted = team_games[team_games["game_id"].isin(game_ids)]
    for record in wanted.to_dict("records"):
        game_id = _as_int(record.get("game_id"))
        if game_id is None:
            continue
        bundle = bundles.setdefault(
            game_id, {"home": None, "away": None, "segment": None}
        )
        side = clean_text(record.get("home_away"))
        if side in ("home", "away"):
            bundle[side] = record
    if game_segments is not None and not game_segments.empty:
        rows = game_segments[game_segments["game_id"].isin(game_ids)]
        for record in rows.to_dict("records"):
            game_id = _as_int(record.get("game_id"))
            bundle = bundles.get(game_id) if game_id is not None else None
            if bundle is not None:
                bundle["segment"] = record
    return bundles


def player_index(player_games: pd.DataFrame, game_ids: set) -> dict:
    """`(game_id, normalised name)` -> the athlete rows carrying it.

    Keyed by the game so candidates are already filtered to the two teams that
    played it — the football lab's rule: *a lone candidate on the wrong team is
    not a match.* Did-not-play rows are kept: they are how a resolved player
    who never entered reaches `settlement._player_guard` and comes back
    `VOID`. A name with no row at all is unresolved, and `_grade_one` returns
    `UNSETTLEABLE` for it rather than a void.
    """
    index: dict = {}
    if player_games is None or player_games.empty or not game_ids:
        return index
    wanted = player_games[player_games["game_id"].isin(game_ids)]
    for record in wanted.to_dict("records"):
        game_id = _as_int(record.get("game_id"))
        name = normalise_person(record.get("athlete_display_name"))
        if game_id is None or not name:
            continue
        index.setdefault((game_id, name), []).append(record)
    return index


def grade(
    frame: pd.DataFrame,
    *,
    fixtures: Mapping[int, dict],
    players: Mapping,
    census: GradingCensus,
) -> pd.DataFrame:
    """Add `outcome`, `actual` and `profit_units` to every wager. Nothing else.

    `profit_units` is `forward_evidence.profit_units` — the same arithmetic the
    forward ledger settles with, imported rather than repeated, so a backtest
    return and a forward return can be read against each other.

    A won bet at a price this lab cannot read carries a **missing** profit
    rather than a zero. Writing zero there would fabricate a number.
    """
    if frame.empty:
        return frame.assign(
            outcome=pd.Series(dtype="object"),
            actual=pd.Series(dtype="float64"),
            profit_units=pd.Series(dtype="float64"),
            settlement_note=pd.Series(dtype="object"),
        )

    outcomes: list[str] = []
    actuals: list[float | None] = []
    profits: list[float | None] = []
    notes: list[str] = []

    for record in frame.to_dict("records"):
        census.rows += 1
        outcome, actual, note = _grade_one(
            record, fixtures=fixtures, players=players, census=census
        )
        value = outcome.value
        outcomes.append(value)
        actuals.append(actual)
        notes.append(note)
        if value == Outcome.UNSETTLEABLE.value:
            census.unsettleable += 1
            if note:
                census.note(note)
            profits.append(None)
            continue
        census.graded += 1
        census.won += int(value == Outcome.WON.value)
        census.lost += int(value == Outcome.LOST.value)
        census.push += int(value == Outcome.PUSH.value)
        census.void += int(value == Outcome.VOID.value)
        profit = profit_units(value, record.get("american_odds"))
        if profit is None:
            census.unreadable_price += 1
        profits.append(profit)

    return frame.assign(
        outcome=outcomes,
        actual=pd.to_numeric(
            pd.Series(actuals, index=frame.index, dtype="object"), errors="coerce"
        ),
        profit_units=pd.to_numeric(
            pd.Series(profits, index=frame.index, dtype="object"), errors="coerce"
        ),
        settlement_note=notes,
    )


def _grade_one(
    record: Mapping,
    *,
    fixtures: Mapping[int, dict],
    players: Mapping,
    census: GradingCensus,
) -> tuple[Outcome, float | None, str]:
    """One wager, graded, with a reason whenever the verdict is not a number."""
    market = MARKETS_BY_KEY.get(clean_text(record.get("market")))
    game_id = _as_int(record.get("game_id"))
    bundle = fixtures.get(game_id) if game_id is not None else None
    selection = clean_text(record.get("selection"))

    if market is not None and bundle is None:
        census.no_fixture += 1
        return (
            Outcome.UNSETTLEABLE,
            None,
            "the processed tables carry no game with this price row's game_id",
        )

    # Three cases, from the settlement contract rather than guessed: the two
    # first-basket markets take a game-segments row, every other player prop
    # takes none, and a team market takes the team-games row of the side its
    # selection names.
    game = None
    if market is not None and bundle is not None:
        if market.settles_on in SEGMENT_SETTLED:
            game = bundle.get("segment")
        elif market.family != PLAYER:
            game = bundle.get(ROW_FOR_SELECTION.get(selection, "home"))
    if market is not None and market.family != PLAYER and game is None:
        census.no_fixture += 1
        return (
            Outcome.UNSETTLEABLE,
            None,
            f"the fixture resolved but no row exists for the side {selection!r} "
            "names, so the two sides cannot be told apart and the margin would "
            "settle negated",
        )

    player_row = None
    name = clean_text(record.get("player"))
    if name:
        candidates = players.get((game_id, normalise_person(name)), [])
        if len(candidates) > 1:
            census.ambiguous_player += 1
            return (
                Outcome.UNSETTLEABLE,
                None,
                f"{name!r} matches {len(candidates)} athletes on the two teams "
                "in this game; ambiguity settles nothing and is never a coin flip",
            )
        if not candidates:
            # A name that fails to RESOLVE is not a player who did not play.
            # `Outcome.VOID` is the book's treatment of a genuine did-not-play
            # and is reached only through `settlement._player_guard`, on a
            # player row this lab actually found and that carries
            # `did_not_play`. Nothing was found here, and nothing is unknown.
            census.unresolved_player += 1
            return (
                Outcome.UNSETTLEABLE,
                None,
                f"{name!r} resolves to nobody on either team's box score for "
                "this game. An unresolved name is unknown, not a did-not-play: "
                "void needs a player who was found and is recorded as not "
                "having entered",
            )
        player_row = candidates[0]

    try:
        decided = settle(
            market=clean_text(record.get("market")),
            segment=clean_text(record.get("segment")),
            selection=selection,
            line=record.get("line"),
            game=game,
            player=player_row,
        )
    except Exception as exc:  # noqa: BLE001 - counted and named, never swallowed
        message = f"{type(exc).__name__}: {exc}"[:200]
        census.errors[message] = census.errors.get(message, 0) + 1
        return Outcome.UNSETTLEABLE, None, f"settle raised {message}"
    return decided.outcome, decided.actual, decided.note


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def load_store(
    competition: Competition, processed_dir: Path, window: H.SnapshotWindow
) -> pd.DataFrame:
    """The bought price store for one window, or a refusal naming the file."""
    path = H.store_path(competition, Path(processed_dir), window)
    if not path.is_file():
        raise NothingToMeasure(
            f"{path} does not exist. No historical price has been bought for "
            f"the {window.name!r} window yet — `scripts/buy_historical_prices.py "
            f"--live` writes it, and the purchase may still be running. Nothing "
            "was scored and no report was written, because an empty report "
            "reads as a null result and a null result is a claim."
        )
    header = list(pd.read_csv(path, nrows=0).columns)
    missing = [c for c in STORE_COLUMNS if c not in header]
    if missing:
        raise NothingToMeasure(
            f"{path} is missing {missing}. A missing column read as a zero is "
            "how the football lab's backtest reported zero bets and had that "
            "read as 'the model never disagrees enough'. Nothing is defaulted "
            "and nothing was scored."
        )
    # Read only what a run consults, plus anything optional the store happens
    # to carry — `survived_to_next_capture` is `reachability.py`'s column and
    # turns a section on rather than being faked when absent.
    wanted = [
        c
        for c in header
        if c in STORE_COLUMNS or c in PB.OPTIONAL_BET_COLUMNS
    ]
    frame = pd.read_csv(path, usecols=wanted)
    if frame.empty:
        raise NothingToMeasure(
            f"{path} exists and holds no rows. That is a purchase that started "
            "and bought nothing, not a market nobody quotes — a starved fetch "
            "and an unquoted market look identical, and this run refuses to "
            "print an interval over either."
        )
    return frame


def load_tables(processed_dir: Path, competition: Competition, *, players: bool):
    """The results tables settlement grades against. A missing one is refused."""
    directory = Path(processed_dir)
    stems = list(REQUIRED_TABLES) + ([PLAYER_TABLE] if players else [])
    tables: dict[str, pd.DataFrame] = {}
    for stem in stems:
        path = directory / competition.output_name(stem, ".csv")
        if not path.is_file():
            raise NothingToMeasure(
                f"{path} does not exist. Run `scripts/build_datasets.py` first. "
                "Grading without it settles every wager as 'no game matches', "
                "which does not fail — it succeeds quietly and wrongly, and a "
                "measurement built on that still prints an interval."
            )
        tables[stem] = pd.read_csv(path, low_memory=False)
    tables.setdefault(PLAYER_TABLE, pd.DataFrame())
    return tables


def season_label(frame: pd.DataFrame) -> str:
    if frame.empty or "season" not in frame.columns:
        return ""
    seasons = sorted({int(s) for s in pd.to_numeric(frame["season"], errors="coerce").dropna()})
    if not seasons:
        return ""
    if len(seasons) == 1:
        return str(seasons[0])
    return f"{seasons[0]}-{seasons[-1]}"


def key_number_inputs(
    team_games: pd.DataFrame, game_ids: set
) -> tuple[pd.Series, pd.Series]:
    """Margins and totals of **the games this store covers**, one row per game.

    Measured from the games supplied rather than carried over from another
    sport: the NFL's 3 and 7 are a fact about how football scores. One row per
    game rather than per team-game, because the home and away rows of one game
    carry the same total and equal-and-opposite margins, and counting both would
    make every margin distribution symmetric by construction.
    """
    empty = pd.Series(dtype="float64")
    if team_games is None or team_games.empty or not game_ids:
        return empty, empty
    wanted = team_games[team_games["game_id"].isin(game_ids)]
    if wanted.empty or "home_away" not in wanted.columns:
        return empty, empty
    home = wanted[wanted["home_away"].astype(str) == "home"]
    if home.empty:
        return empty, empty
    margins = pd.to_numeric(home.get("margin"), errors="coerce").dropna()
    totals = pd.to_numeric(home.get("total"), errors="coerce").dropna()
    return margins, totals


# --------------------------------------------------------------------------
# Console output — the null baseline first, always
# --------------------------------------------------------------------------


def _cell(row: Mapping) -> str:
    roi, interval, corrected = PB.roi_cells(dict(row))
    return (
        f"{row.get('bets', 0):,} bets / {row.get('clusters', 0):,} "
        f"{row.get('cluster_unit', 'game')}s  {roi}  [{interval}]  "
        f"corrected [{corrected}]  — {row.get('verdict', '')}"
    )


def print_baseline(rows: Sequence[Mapping]) -> None:
    """The no-model return, printed above every model figure. Never after it."""
    print("")
    print("THE NULL BASELINE, FIRST")
    print(
        "  What betting one side with no model at all returns. It is computed "
        "before any"
    )
    print(
        "  model number is looked at, because a model whose bets are 90% unders "
        "in a season"
    )
    print("  when blind unders returned +3% has not found anything.")
    if not rows:
        print(f"  {PB.NOTHING_TO_MEASURE.capitalize()}: no blind side could be graded.")
        return
    measured = [r for r in rows if r.get("enough_evidence")]
    notable = [
        r
        for r in measured
        if r.get("verdict") in (S.DEMONSTRATED_EDGE, S.DEMONSTRATED_DEFICIT)
    ]
    print(
        f"  {len(rows):,} blind side(s) graded; {len(measured):,} clear the "
        f"{S.MINIMUM_BETS:,}-bet floor declared in advance."
    )
    if not notable:
        print(
            "  None of them excludes zero after the family correction — every "
            "blind side is "
            f"'{S.NO_DEMONSTRATED_EDGE}'."
        )
    for row in notable:
        print(f"  {row['tier']} / {row['market']} / {row['name']}: {_cell(row)}")
    print("  The full table, every side and every tier, is in the report.")


def print_model(record: Mapping) -> None:
    """Per market and per tier. Never a pooled Division I headline."""
    print("")
    print("THE MODEL, PER MARKET AND PER CONFERENCE TIER")
    cells = record.get("by_market_and_tier") or []
    if not cells:
        print(
            f"  {PB.NOTHING_TO_MEASURE.capitalize()}: no model bet was graded."
        )
    for row in cells:
        if not row.get("enough_evidence"):
            continue
        print(f"  {row['tier']} / {row['market']}: {_cell(row)}")
    thin = [r for r in cells if not r.get("enough_evidence")]
    if thin:
        print(
            f"  {len(thin):,} further cell(s) sit below the "
            f"{record.get('minimum_bets', S.MINIMUM_BETS):,}-bet floor and "
            "print no number, only 'not enough evidence'."
        )
    biased = [r for r in cells if r.get("side_biased")]
    for row in biased:
        print(
            f"  ! {row['tier']} / {row['market']} is {row['dominant_share']:.0%} "
            f"on {row['dominant_side']} — read it against that side's blind "
            "return above before reading it as a model result."
        )
    print("")
    print("PER TIER, ACROSS MARKETS")
    for row in record.get("by_tier") or []:
        print(f"  {row.get('name', row.get('tier', ''))}: {_cell(row)}")
    print("")
    print("POOLED — never the headline. High-major, mid-major and low-major are")
    print("three different distributions and the stopping rule is applied to each.")
    for row in record.get("pooled") or []:
        if row.get("name") == "every market":
            print(f"  every market (pooled): {_cell(row)}")


def print_half_point(record: Mapping) -> None:
    print("")
    print("HALF A POINT AT A KEY NUMBER, OR A VIEW OF THE GAME")
    margin = (record.get("key_numbers") or {}).get("margin") or {}
    if margin.get("numbers"):
        named = ", ".join(
            f"{n['value']} ({n['share']:.1%})" for n in margin["numbers"]
        )
        print(
            f"  Key numbers measured from {margin['n']:,} games this store "
            f"covers: {named}."
        )
    half = record.get("half_point") or {}
    if not half.get("verified"):
        print(f"  Not reported. {half.get('note', PB.NOTHING_TO_MEASURE)}")
        return
    for key in (
        "half_point_decided",
        "half_point_at_a_key_number",
        "a_view_of_the_game",
    ):
        row = half.get(key) or {}
        if row:
            print(f"  {row.get('name', key)}: {_cell(row)}")


# --------------------------------------------------------------------------
# The two modes
# --------------------------------------------------------------------------


def rebuild_report_only(*, record_path: Path, report_path: Path) -> int:
    """Re-render the markdown from the record. Scores nothing, spends nothing.

    A full run walks every slate day of six seasons and grades every wager in
    the store. If improving a sentence cost that, nobody would improve a
    sentence — they would edit the generated file by hand, and a hand-edited
    generated file survives exactly one re-run.
    """
    if not record_path.is_file():
        print(
            f"::error::{record_path} does not exist, so there is no record to "
            "re-render. Run this script without --rebuild-report-only first; "
            "the report is a pure function of the record and cannot be "
            "produced without one.",
            file=sys.stderr,
        )
        return EXIT_NOTHING_TO_MEASURE
    try:
        record = PB.read_record(record_path)
    except PB.BacktestError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE
    PB.write_report(record, report_path)
    print(f"Wrote {report_path} from {record_path}.")
    print(
        f"The run being rendered scored {int(record.get('bets_graded', 0)):,} "
        f"graded bets from {int(record.get('wagers_graded', 0)):,} graded "
        f"wagers, generated {record.get('generated_at') or 'at an unrecorded time'}."
    )
    print("Nothing was re-scored, no table was read and no credit was spent.")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    parser.add_argument(
        "--window",
        default=H.CARD_WINDOW.name,
        choices=sorted(H.WINDOWS),
        help=(
            "Which snapshot store to score. `card` is the only window this "
            "lab's own card could have taken; `close` exists to measure "
            "movement and is not a price this lab can bet."
        ),
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=(
            "`module:attribute` returning one matchup per event for a slate "
            f"day. Default {DEFAULT_MODEL}."
        ),
    )
    parser.add_argument(
        "--seasons",
        default="",
        help=(
            "Comma-separated seasons to score, labelled by the year they END. "
            "Also the lever for a store too large to hold at once: score it a "
            "season at a time. A filter matching nothing is a refusal, never "
            "an empty measurement."
        ),
    )
    parser.add_argument(
        "--edge-threshold",
        type=float,
        default=PB.BET_EDGE_THRESHOLD,
        help=(
            "Declared in advance and equal to the card's. Moving it after "
            "seeing a number is the defect this repository is arranged against."
        ),
    )
    parser.add_argument(
        "--write-graded",
        default="",
        help=(
            "Write EVERY settled wager the model had an opinion on to this CSV, "
            "carrying `forecast_skill.SKILL_COLUMNS`, `book`, and a boolean "
            "`selected` that is True exactly for the rows that cleared the edge "
            "threshold (the bets). It is what lets the market-vs-model "
            "regression run over the BOUGHT population rather than only over "
            "the forward ledger, which does not exist until the season starts. "
            "The bets alone are NOT that population: they are selected by the "
            "model's disagreement with the price, and regressing outcome on "
            "that disagreement over them alone bakes the winner's curse into "
            "the coefficient. Derived data: it rebuilds from the store for free."
        ),
    )

    parser.add_argument(
        "--rebuild-report-only",
        action="store_true",
        help=(
            "Re-render the markdown from the existing run record. Scores "
            "nothing, reads no table, spends nothing."
        ),
    )
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument(
        "--ledger",
        default="",
        help=(
            "The experiment ledger the family-wise correction is read from. "
            "Defaults to the one beside the outputs. Always the CUMULATIVE "
            "count, never the day's."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    competition = competition_for(args.competition)
    output_dir = Path(args.output_dir)
    record_path = PB.record_path(competition, output_dir)
    report_path = PB.report_path(competition, output_dir)

    if args.rebuild_report_only:
        return rebuild_report_only(
            record_path=record_path, report_path=report_path
        )

    window = H.WINDOWS[args.window]
    print(f"{competition.title} — price backtest")
    print(
        f"Window: {window.name} (T-{window.minutes_before_tip}m). {window.why}"
    )

    # ---- the store, and one bet per wager at the best price ----------------
    try:
        store = load_store(competition, Path(args.processed_dir), window)
    except NothingToMeasure as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE

    wanted_seasons = {
        int(s) for s in str(args.seasons).split(",") if str(s).strip().isdigit()
    }
    if wanted_seasons:
        store = store[
            pd.to_numeric(store["season"], errors="coerce").isin(wanted_seasons)
        ].reset_index(drop=True)
        if store.empty:
            print(
                "::error::No price row survives the season filter "
                f"{sorted(wanted_seasons)}. Nothing was scored.",
                file=sys.stderr,
            )
            return EXIT_NOTHING_TO_MEASURE

    quotes = len(store)
    try:
        wagers = PB.one_bet_per_wager(store)
    except ValueError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE
    print(
        f"Store: {quotes:,} quote(s) collapse to {len(wagers):,} wager(s) at "
        "the best price — one wager is one bet, however many books hang it."
    )

    # ---- the model ---------------------------------------------------------
    try:
        model = resolve_model(args.model)
    except ModelNotWired as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NO_MODEL

    # ---- the results tables ------------------------------------------------
    markets_present = {clean_text(m) for m in wagers["market"].dropna().unique()}
    needs_players = any(
        (MARKETS_BY_KEY.get(m) is not None and MARKETS_BY_KEY[m].family == PLAYER)
        for m in markets_present
    )
    try:
        tables = load_tables(
            Path(args.processed_dir), competition, players=needs_players
        )
    except NothingToMeasure as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE
    team_games = tables["team_games"]

    # ---- walk forward ------------------------------------------------------
    accounting = OpinionAccounting(offered=len(wagers))
    priced = PB.walk_forward(
        wagers,
        team_games,
        price_day=make_price_day(
            model, competition=competition, accounting=accounting
        ),
    )
    # Checked on the stamp rather than trusted from the code path, because the
    # code path is exactly what was wrong in the lab this guard is ported from.
    PB.assert_walk_forward(priced)
    if len(priced) != len(wagers):
        # The pricer is contracted to hand back every row of the day it was
        # given, priced or not. A pricer that returns only the rows it liked
        # shrinks the universe the null baseline is computed over, and the
        # baseline is the one number that has to describe the whole board.
        print(
            f"::error::The pricer returned {len(priced):,} row(s) for "
            f"{len(wagers):,} wager(s). Every wager the board offered must come "
            "back, with a missing probability where the model declined — an "
            "absent opinion is not an opinion of zero. Nothing was written.",
            file=sys.stderr,
        )
        return EXIT_NOTHING_TO_MEASURE
    priced = PB.add_edge(priced)

    opinions = int(
        pd.to_numeric(priced["model_probability"], errors="coerce").notna().sum()
    )

    # ---- grade every wager the board offered -------------------------------
    game_ids = {
        g for g in (_as_int(v) for v in priced.get("game_id", pd.Series(dtype="object")))
        if g is not None
    }
    census = GradingCensus()
    universe = grade(
        priced,
        fixtures=fixture_index(team_games, tables["game_segments"], game_ids),
        players=player_index(tables[PLAYER_TABLE], game_ids),
        census=census,
    )
    bets = PB.bets_from(universe, threshold=float(args.edge_threshold))
    # All four terms read off the graded frame, none of them the residual of
    # the others. `count_from` uses `PB.bet_mask` — the same predicate
    # `bets_from` used one line above — so the bets bucket and the bets frame
    # cannot be two different cuts of the same rows.
    accounting.count_from(
        universe, threshold=float(args.edge_threshold), bets=bets
    )

    for line in accounting.lines():
        print(line)
    try:
        accounting.check()
    except AccountingDoesNotReconcile as exc:
        print(
            f"::error::The accounting identity does not reconcile: {exc} A "
            "measurement that silently lost rows still prints an interval. "
            "Nothing was written.",
            file=sys.stderr,
        )
        return EXIT_NOTHING_TO_MEASURE
    for line in census.lines():
        print(line)
    if accounting.with_prior_weight:
        print(
            f"  {accounting.with_prior_weight:,} priced wager(s) carry a "
            "recorded preseason-prior weight, so a November number cannot be "
            "read as a February one."
        )

    if opinions == 0:
        print(
            "::error::The model was asked about every wager in the store and "
            "had an opinion on none of them. Zero bets reads as 'the model "
            "never disagrees enough with the market', which is a finding — and "
            "in the football lab it was a wiring fault, its price columns "
            "never built. This exits rather than publishing that ambiguity as "
            "a measurement. The declined reasons above name the cause.",
            file=sys.stderr,
        )
        for reason, count in sorted(
            accounting.declined_reasons.items(), key=lambda kv: (-kv[1], kv[0])
        )[:5]:
            print(f"::error::  {count:,} x {reason}", file=sys.stderr)
        return EXIT_NO_OPINION

    # ---- the record --------------------------------------------------------
    # ONE LEDGER. It does not follow --output-dir: a holdout run points
    # --output-dir at data/outputs/holdout/ so its record lands apart, and
    # "the ledger beside the outputs" then meant a COPY — which the replication
    # appended its holdout looks to while this read its correction from the
    # original. One cumulative count, because one ledger.
    ledger = Path(args.ledger) if args.ledger else PB.ledger_path(OUTPUTS_DIR)
    looks = PB.looks_from_ledger(ledger)
    # An absent ledger is not a family of one, and the report must not say it
    # is: no correction at all makes every interval look tighter than it is.
    ledger_read = PB.ledger_was_read(ledger)
    if not ledger_read:
        print(
            f"::warning::No experiment ledger at {ledger}. NO family-wise "
            "correction will be applied and every interval in this run is the "
            "raw one. That is not a family of one — it is an unknown family.",
            file=sys.stderr,
        )
    if not ledger.is_file():
        print(
            f"::warning::{ledger} does not exist, so the family-wise "
            "correction is applied across one look. That is a lab that has "
            "tested nothing, which is not what this one is."
        )
    if args.write_graded:
        # The graded frame is what `forecast_skill` regresses on, and it is
        # EVERY settled wager the model had an opinion on — not the bets. The
        # bets are selected by the model's disagreement with the price; a
        # regression of outcome on that same disagreement fitted over them
        # alone has the winner's curse built into its coefficient, and a
        # claimed-edge bucket table over them is tautological, every row being
        # above the threshold by construction. Until 2026-09-05 this wrote
        # `PB.settled(bets)`, and the skill report's "all opinions" was the
        # bets. The frame is cut from the SAME `universe` the record is built
        # from, with `selected` computed by the SAME predicate `bets_from`
        # uses, so the regression's subset and the ROI table's bets can never
        # be two different cuts — the accounting-identity discipline applied
        # one layer out.
        target = Path(args.write_graded)
        target.parent.mkdir(parents=True, exist_ok=True)
        missing = [c for c in FS.SKILL_COLUMNS if c not in universe.columns]
        if missing:
            print(
                f"::error::The graded frame is missing {missing!r}, so it "
                "cannot be regressed. Nothing was written: a partial frame "
                "would be silently scored on whatever survived.",
                file=sys.stderr,
            )
            return 2
        opinions_frame = PB.settled_opinions(universe)
        opinions_frame = opinions_frame.assign(
            selected=PB.bet_mask(opinions_frame, threshold=float(args.edge_threshold))
        )
        # `book` is carried alongside the declared columns because
        # `forecast_skill` de-vigs WITHIN a book by default, and it refuses to
        # run without it rather than pooling every row into one nameless book —
        # which would pair quotes across books and understate the hold,
        # sometimes to nothing. The refusal is correct; the fix is the column.
        columns = list(FS.SKILL_COLUMNS)
        if "book" in opinions_frame.columns and "book" not in columns:
            columns.append("book")
        columns.append(FS.SELECTED_COLUMN)
        opinions_frame[columns].to_csv(target, index=False)
        selected_count = int(opinions_frame[FS.SELECTED_COLUMN].sum())
        print(
            f"Wrote {len(opinions_frame):,} settled opinion(s) to {target} for "
            f"the market-vs-model regression; {selected_count:,} of them are "
            f"the threshold-selected bets (`{FS.SELECTED_COLUMN}` is True). "
            "The regression's population is every opinion; the selected subset "
            "is reported beside it as the winner's-curse comparison."
        )

    margins, totals = key_number_inputs(team_games, game_ids)

    record = PB.build_record(
        PB.BacktestInputs(
            universe=universe,
            bets=bets,
            margins=margins,
            totals=totals,
            season_label=season_label(universe),
            snapshot_phase=window.name,
        ),
        competition=competition,
        looks=looks,
        ledger_read=ledger_read,
        threshold=float(args.edge_threshold),
        generated_at=datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        calibration=CAL.build_record(
            universe, bets, threshold=float(args.edge_threshold)
        ),
    )

    PB.write_record(record, record_path)
    PB.write_report(record, report_path)

    # ---- what a reader of the log sees, in the report's own order ----------
    print("")
    print(
        f"Family correction: {looks:,} cumulative hypotheses in "
        f"{ledger.name}, widening every 95% interval by "
        f"x{record['correction_factor']:.2f}. The ledger's cumulative count, "
        "never the day's."
    )
    print_baseline(record.get("null_baseline") or [])
    print_model(record)
    print_half_point(record)

    outside = _outside_the_price_band(bets)
    if outside:
        print("")
        print(
            f"{outside:,} of {len(bets):,} bet(s) sit outside "
            f"`card_pricing.PRICE_BAND` {card_pricing.PRICE_BAND}, which the "
            "card declares in advance and this backtest does not apply. The "
            "largest apparent edges in any price store are the rows that are "
            "wrong, and they all live out there."
        )

    print("")
    print(f"Wrote {record_path}")
    print(f"Wrote {report_path}")
    print(
        "Re-render the report from that record for free with "
        "--rebuild-report-only; improving a sentence must never cost a re-run."
    )
    return EXIT_OK


def _outside_the_price_band(bets: pd.DataFrame) -> int:
    if bets.empty or "american_odds" not in bets.columns:
        return 0
    odds = pd.to_numeric(bets["american_odds"], errors="coerce")
    low, high = card_pricing.PRICE_BAND
    return int(((odds < low) | (odds > high)).sum())


if __name__ == "__main__":
    raise SystemExit(main())
