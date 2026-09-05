"""Build the frame `forecast_skill` de-vigs from: every graded bet plus its complement.

    PYTHONPATH=src python scripts/build_skill_frame.py

`forecast_skill` de-vigs a quote by pairing it with the SAME book's quote on
the other side of the wager — the only pair that actually contains a hold. The
price backtest's `--write-graded` export carries only the side the model bet,
so handed to `forecast_skill` directly every row reads "the other side of the
wager is not in the frame" and nothing is scored. That refusal is correct: a
fair price cannot come from a one-sided quote.

This script supplies the complements from the price store. It was an ad-hoc
heredoc the first time; the second time it is a script, because a step that is
re-typed is a step that drifts, and this one has to agree with the module that
will later pair the rows.

**Every rule here is the lab's own function, called rather than copied:**
`stores.dedupe_prices` for the quote identity, `forecast_skill.pair_key` for
what makes two rows one wager (home -3.5 and away +3.5 are one wager; keyed on
the line as filed they never pair), and `forecast_skill.COMPLEMENT` for the
other side's name.

## A graded bet whose book hung only one side

Until 2026-09-05 this script **refused to write if any graded bet lacked its
complement**, and the reasoning was sound as far as it went: a missing
complement would land that bet under no pair, silently excluded from the
de-vig, and the excluded rows are not a random sample because a book that hangs
only one side of a wager is a book doing something unusual with it.

What that reasoning missed is that *silently* was the whole objection. A book
that hung one side and not the other supplies **no hold**, so the wager
genuinely cannot be de-vigged and excluding it is the only honest arithmetic
available. On the full store, 2 graded rows out of 566,377 are in that
position — 0.00035% — and refusing the frame over them stopped the lab's
measurement outright.

So the rule is neither "refuse" nor "drop quietly". The unpairable rows are
excluded, **counted, named, and reconciled**: `supplied = paired +
unpairable + no_pair_key`, three terms each counted off the rows,
printed in the same shape as the price backtest's accounting identity (see
`OpinionAccounting` in `scripts/run_price_backtest.py`) and written to a JSON
record beside the frame, so `forecast_skill` and any later reader can state
the population from a count rather than from the frame's length.

## The store's own unpaired rows are a different population

A reader who counts pairs in the price store directly finds a much larger
number and should not read it as this script's business. Counted on the
3,863,325-row card store (`stores.dedupe_prices` dropped nothing: 3,863,325 in,
3,863,325 out), **146,617 of the 1,850,597 total-side rows — 7.92% — have no
complement at their own book**, against 28 of 2,012,728 on the handicap side.

That 7.92% is player props and essentially nothing else: 146,612 of the 146,617
(99.997%) are `player_*` markets, all in the 2024 season, the only season this
store carries props at all. Within the props it is not marginal — 146,612 of
504,394 prop rows, 29.1% — and it is one-directional: 146,523 of them are the
`over`. 141,664 of them (96.6%) have the same book quoting the other side at a
*different* number, which is how a book prices a prop it is not willing to hang
symmetrically, and is a genuine one-sided quote at the line as filed rather
than a failure of `pair_key`.

**None of those rows is ever asked for here.** This script looks for a
complement only for a row in the graded export, and the graded export carries
**no player prop at all — 0 of 566,377 rows**. That is by declaration, not by
accident: `gameday_card.opinions_for` refuses the whole `PLAYER` family with
*"this lab has no player model, so no player prop carries a modelled opinion"*,
and the backtest prices through that same function, so a prop is never an
opinion, never a bet and never graded. The five non-prop rows in that 146,617
are draftkings `team_total` quotes on four November-2024 slate dates, and one of
them is the `home_over` 74.5 already named as one of the two graded rows this
script excludes.

So the store-side 7.92% is benign **for this frame** — it is a market family the
measurement never enters. It is not evidence that the pairing rule is broken,
and it is not headroom: the number that the refusal threshold below is read
against is the graded-side share, which is 2 in 566,377.

**Above a declared share it still refuses.** Excluding a handful of rows from
half a million is bookkeeping; excluding a large share is a broken join wearing
the costume of a data quirk. :data:`MAX_UNPAIRABLE_SHARE` is where the two are
separated, and the reasoning is in its comment.

**It refuses a graded frame without the `selected` column.** Until 2026-09-05
the export was the threshold-selected bets and nothing else, so a graded file
left over from that backtest is the winner's-curse slice with no mark on it —
handed to `forecast_skill` it would be fitted as "every opinion" and read as
the skill measure. The flag is what tells the two apart; a frame without it is
refused with the re-run command rather than passed through. Complement rows
carry `selected=False`: they are not bets, they are not opinions, they are the
other side of the price.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

from cbb_betting_lab import stores
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import PROCESSED_DIR
from cbb_betting_lab.providers import historical as H
from cbb_betting_lab.reports import forecast_skill as FS

DEFAULT_GRADED = "cbb_graded_bets.csv"
DEFAULT_OUT = "cbb_skill_frame.csv"

#: The largest share of the graded rows that may be excluded as unpairable
#: before this script refuses to write at all.
#:
#: **0.01% — one row in ten thousand.** The number is not a feeling; it is
#: placed between the two things it has to tell apart, both measured on the
#: real 566,377-row graded export:
#:
#: * **Bookkeeping, below it.** The observed unpairable rows are 2 of 566,377,
#:   which is 0.00035%. This threshold is 28x that, so the quirk can grow by
#:   more than an order of magnitude — to 56 rows — before the lab's
#:   measurement stops again over rows that carry no hold and never could.
#: * **A broken join, above it.** A join that breaks does not lose a scattering
#:   of rows; it loses a whole slice, because what breaks is a key column, a
#:   line convention or a book's spelling. The *smallest* single book in the
#:   graded export is 0.021% of it (119 rows) and the smallest single market is
#:   0.052% (292 rows). So a break that took out one entire book — the
#:   narrowest join-shaped failure this export can express — is twice this
#:   threshold and still refuses, and a break that took out a market is five
#:   times it.
#:
#: Deliberately a share and not a row count. On a frame small enough that a
#: single unpairable row exceeds this, the refusal is right rather than
#: over-strict: one row in a hundred IS a large share of that measurement, and
#: at that size nothing distinguishes a quirk from a break.
MAX_UNPAIRABLE_SHARE = 0.0001

#: How many unpairable rows are written out one by one. A count with no example
#: beside it is a number nobody can act on, and the whole point of this census
#: is that somebody goes and looks at what was dropped. Capped because the
#: refusal above lets a few dozen rows through and a record is not a log.
UNPAIRABLE_ROWS_NAMED = 25

#: What a breakdown calls a cell that is not there. Named rather than blank,
#: and never dropped: an unpairable row whose book was never recorded is a fact
#: worth seeing, and a tally that silently omitted it would total fewer rows
#: than the `unpairable` count printed directly above it.
MISSING_LABEL = "(missing)"

#: Why these rows are excluded, in words, carried into the record so the
#: report can state it without re-deriving it.
UNPAIRABLE_REASON = (
    "their own book hung only one side of the wager, so the quote contains no "
    "hold and no fair price can be taken from it"
)

#: The columns that name an excluded row. Every one is in `FS.SKILL_COLUMNS`
#: or is `book`, which is what makes the pair a same-book pair.
NAMING_COLUMNS: tuple[str, ...] = (
    "event_id",
    "slate_date",
    "market",
    "segment",
    "selection",
    "line",
    "american_odds",
    "tier",
    "book",
    FS.SELECTED_COLUMN,
)


def _tally(frame: pd.DataFrame, column: str) -> dict[str, int]:
    """Counts by one column, as plain data. Absent column, empty tally.

    Every excluded row reaches a key, so the tallies total `unpairable` and a
    breakdown cannot quietly stop describing the census it sits under.
    `value_counts` drops the missing value, so a row whose `book` was never
    recorded would otherwise leave the by-book block without leaving the count
    above it — the same silent-drop shape this whole file argues against, one
    level down.

    **The cast alone is not enough, and which part carries the weight depends
    on the pandas.** This file's `.astype(str).fillna("")` was read as dead
    code on the grounds that the cast has already turned NaN into the literal
    `"nan"`. That was true through pandas 2 and is **false on the pandas this
    lab runs**: on 3.0.5 `astype(str)` leaves a missing value missing, so the
    `fillna` was the only thing keeping the row in the tally — and deleting it
    as dead would have dropped exactly the rows this census exists to show.
    `mask` on the pre-cast column does the job on both, and files the cell
    under a name a reader can see rather than under `""`, which prints as a
    blank in the by-book block and reads like a formatting glitch.
    """
    if column not in frame.columns or frame.empty:
        return {}
    values = frame[column]
    counts = values.astype(str).mask(values.isna(), MISSING_LABEL).value_counts()
    return {str(key): int(value) for key, value in counts.items()}


@dataclass
class UnpairableCensus:
    """`supplied = paired + unpairable + no_pair_key`, and what that cannot see.

    Modelled on `run_price_backtest.OpinionAccounting`, and for the same
    reason: a measurement that silently lost rows still prints an interval, and
    the interval looks exactly like one that did not.

    **Every term is counted from the graded frame, and none is the residual of
    the others.** Until 2026-09-05 :func:`build` set

        paired = len(graded) - len(excluded)

    — a residual, which made `supplied == paired + unpairable` hold for any two
    frames whatever and so could never detect the loss the census exists to
    detect. It is the same defect this lab had just fixed in
    `OpinionAccounting.count_from`, and it arrived here by copying the *shape*
    of that identity instead of its rule. `paired` is now the count of graded
    rows that actually found their complement at their own book, and the
    residual is gone.

    **What the identity proves.** The three predicates — found the complement,
    wanted one and did not find it, has no complement in the lab's vocabulary
    to want — are disjoint and exhaustive over the rows :func:`build` buckets,
    so `accounted` is exactly the number of rows it bucketed, and the identity
    is really the single comparison *the rows bucketed are the rows supplied*.
    That is a real test, and it is the one the residual could not make: it
    fails the moment a graded row is lost between the frame handed to
    :func:`build` and the keys it buckets — a dedupe, a filter, a re-index, a
    `zip` over columns of unequal length. `supplied` is read off the frame at
    entry, before anything is joined to it, so the two counts have somewhere to
    disagree.

    **What it cannot see.** It does not prove the three buckets are the *right*
    buckets. A row put in the wrong one moves a count from one term to another
    and leaves the sum unchanged, so this identity is blind to every
    mis-bucketing: a pair key that matches too loosely, a complement looked up
    at the wrong book, a selection wrongly judged keyless. Nothing in the
    arithmetic can catch those and the tests are what pin them —
    `tests/test_build_skill_frame.py::
    test_every_census_term_is_counted_off_the_frame_and_none_is_a_residual`
    and `::test_moving_one_row_between_buckets_is_what_the_identity_cannot_see`,
    which states that blindness rather than implying a coverage this
    arithmetic does not have.

    The second comparison in :meth:`reconciles` reaches a failure the first is
    blind to: :attr:`complements`, the size of the complement block the returned
    frame carries, against :attr:`paired_wagers`, the distinct wagers the paired
    rows asked for. The two are equal in any correct run — it is a guard, not a
    measurement — and it fires when that block stops holding exactly one row per
    paired wager. That failure has the worst consequences here and no other
    symptom: `stores.dedupe_prices` keys on the quote including `snapshot_phase`,
    so the same complement legitimately survives it twice, and two complement
    rows on one wager double that wager's hold in the de-vig while every term of
    the identity still adds up perfectly.

    What no arithmetic here reaches is the case where `build` itself loses a
    graded row between the frame it was handed and the keys it buckets — the
    three predicates would simply bucket what survived. `main` makes that a
    real comparison across a real boundary: the rows it read from the CSV
    against the `supplied` the census reports.
    """

    #: Graded rows handed to :func:`build`, counted at entry.
    supplied: int = 0
    #: Graded rows that found their complement at their own book. Counted from
    #: the rows themselves — never `supplied` minus anything.
    paired: int = 0
    #: Graded rows excluded: they wanted a complement at their own book and the
    #: store did not have it.
    unpairable: int = 0
    #: Of the excluded rows, how many the price backtest had marked as bets.
    #: Reported apart because a dropped **bet** is a dropped stake, and the
    #: winner's-curse comparison shrinks with it.
    unpairable_selected: int = 0
    #: Graded rows whose selection has no complement at all in
    #: `FS.COMPLEMENT` — a wager `pair_key` cannot key. **Its own term in the
    #: identity**, because a row with no pair key did not pair: folding it into
    #: `paired` (which this file did until 2026-09-05) counts a row as having
    #: found a complement it never went looking for. It is not `unpairable`
    #: either — that term is read against the refusal threshold and means *a
    #: book hung one side only*, which is a claim about a book, not about this
    #: lab's vocabulary. These rows stay in the frame, and
    #: `forecast_skill.DevigCensus` counts them under `unknown_selection`,
    #: which is where a reader already looks for them.
    no_pair_key: int = 0
    #: Complement rows in the frame returned beside this census: one per paired
    #: wager, and the other side of the guard :attr:`paired_wagers` states.
    #: `-1` means no frame was built and the cross-check is not made.
    complements: int = -1
    #: Distinct wagers the paired rows asked a complement for. Compared to
    #: :attr:`complements` and never to :attr:`paired`: the same quote filed
    #: twice in the graded export is two paired rows wanting one complement, so
    #: `paired` legitimately exceeds this.
    paired_wagers: int = -1
    by_market: dict[str, int] = field(default_factory=dict)
    by_book: dict[str, int] = field(default_factory=dict)
    by_tier: dict[str, int] = field(default_factory=dict)
    #: The excluded rows themselves, up to :data:`UNPAIRABLE_ROWS_NAMED`.
    rows: list[dict] = field(default_factory=list)
    max_share: float = MAX_UNPAIRABLE_SHARE

    @property
    def accounted(self) -> int:
        return self.paired + self.unpairable + self.no_pair_key

    @property
    def reconciles(self) -> bool:
        """Every supplied row bucketed, and one complement per paired wager.

        Two comparisons, not one. The first is the identity; the second is the
        cross-check against the frame's own complement block, which is the part
        that is not blind to a bucketing error. See the class docstring.
        """
        return self.accounted == self.supplied and (
            self.complements < 0 or self.complements == self.paired_wagers
        )

    @property
    def share(self) -> float:
        """Unpairable as a share of the graded rows supplied. Zero over zero is zero."""
        return 0.0 if self.supplied <= 0 else self.unpairable / self.supplied

    @property
    def refuses(self) -> bool:
        """Above the declared share this is a broken join, not a data quirk."""
        return self.share > self.max_share

    def to_json(self) -> dict:
        return {
            "supplied": int(self.supplied),
            "paired": int(self.paired),
            "unpairable": int(self.unpairable),
            "unpairable_selected": int(self.unpairable_selected),
            "no_pair_key": int(self.no_pair_key),
            "accounted": int(self.accounted),
            "complements": int(self.complements),
            "paired_wagers": int(self.paired_wagers),
            "share": float(self.share),
            "max_share": float(self.max_share),
            "reconciles": bool(self.reconciles),
            "reason": UNPAIRABLE_REASON,
            "by_market": dict(self.by_market),
            "by_book": dict(self.by_book),
            "by_tier": dict(self.by_tier),
            "rows": list(self.rows),
            "rows_named_capped_at": int(UNPAIRABLE_ROWS_NAMED),
        }

    def lines(self) -> list[str]:
        """The identity, in the shape the price backtest prints its own."""
        out = [
            "Unpairable census — supplied = paired + unpairable + no_pair_key:",
            f"  graded rows supplied  {self.supplied:,}",
            f"  paired                {self.paired:,}",
            f"  unpairable            {self.unpairable:,}",
            f"  no_pair_key           {self.no_pair_key:,}",
            f"  reconciles            {'yes' if self.reconciles else 'NO'} "
            f"({self.accounted:,} accounted of {self.supplied:,} supplied; "
            f"{self.complements:,} complement row(s) for "
            f"{self.paired_wagers:,} paired wager(s))",
            f"  unpairable share      {self.share:.6%} of the graded rows, "
            f"against a refusal threshold of {self.max_share:.6%}",
        ]
        if self.unpairable:
            out.append(f"  excluded because {UNPAIRABLE_REASON}.")
            out.append(
                f"  of the excluded, {self.unpairable_selected:,} had been "
                "marked as threshold-selected bets."
            )
        if self.no_pair_key:
            out.append(
                f"  the {self.no_pair_key:,} no_pair_key row(s) carry a selection "
                "with no complement at all; they never went looking for one, so "
                "they are neither paired nor unpairable. They are kept in the "
                "frame and counted by forecast_skill's de-vig census as "
                "`unknown_selection`."
            )
        out += _tally_lines("market", self.by_market)
        out += _tally_lines("book", self.by_book)
        out += _tally_lines("tier", self.by_tier)
        if self.rows:
            out.append(f"  the excluded rows (up to {UNPAIRABLE_ROWS_NAMED:,}):")
            for row in self.rows:
                out.append(
                    "    "
                    + " ".join(
                        f"{key}={row.get(key)!r}"
                        for key in NAMING_COLUMNS
                        if key in row
                    )
                )
        return out


def _tally_lines(what: str, counts: dict[str, int]) -> list[str]:
    if not counts:
        return []
    out = [f"  unpairable by {what}:"]
    for key, value in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        out.append(f"    {key:<28} {value:,}")
    return out


def build(graded: pd.DataFrame, store: pd.DataFrame) -> tuple[pd.DataFrame, UnpairableCensus]:
    """Graded bets that pair, plus one complement row each, plus the census.

    The returned frame **excludes** every graded row whose own book hung only
    one side of the wager. The census says how many there were, what they were
    and where they came from, and `supplied = paired + unpairable +
    no_pair_key` reconciles over the frame handed in — so a caller can state
    the population from a count instead of from the length of what came back.
    Read `UnpairableCensus` for what that identity does and does not prove.
    """
    # Counted here, off the frame exactly as handed in and before anything is
    # joined to or derived from it: the one number in the census that is not
    # read off the bucketing below, and so the one the bucketing can disagree
    # with. `main` is where that disagreement becomes visible.
    supplied = int(len(graded))
    store = stores.dedupe_prices(store)
    store = store.assign(_pk=[FS.pair_key(r) for r in store.to_dict("records")])
    graded = graded.assign(_pk=[FS.pair_key(r) for r in graded.to_dict("records")])

    wanted = [
        (pk, bk, FS.COMPLEMENT[sel]) if pk is not None and sel in FS.COMPLEMENT else None
        for pk, bk, sel in zip(graded["_pk"], graded["book"], graded["selection"])
    ]
    need = {key for key in wanted if key is not None}
    keys = list(zip(store["_pk"], store["book"], store["selection"]))
    comp = store[pd.Series([k in need for k in keys], index=store.index)]
    # One complement row per wager, and the census counts the block afterwards
    # to say so. `stores.dedupe_prices` keys on the quote **including**
    # `snapshot_phase`, so the same complement legitimately survives it twice,
    # and two complement rows on one wager double that wager's hold in the
    # de-vig while every term of the identity still adds up.
    comp = comp.drop_duplicates(subset=["_pk", "book", "selection"], keep="first")

    found = set(zip(comp["_pk"], comp["book"], comp["selection"]))
    # Three predicates, three counts, every one read off the rows themselves,
    # and one row in exactly one bucket. Two earlier versions of this block were
    # wrong in the same direction and are worth naming:
    #   * `len(need - found)` counted missing *keys*, and two graded rows can
    #     want the same key, so it was never a count of rows at all;
    #   * `paired = len(graded) - len(excluded)` was a residual, so the identity
    #     reconciled for any pair of frames whatever — and it counted a row with
    #     no pair key as having found a complement it never looked for.
    paired_mask = pd.Series(
        [key is not None and key in found for key in wanted], index=graded.index
    )
    unpairable_mask = pd.Series(
        [key is not None and key not in found for key in wanted], index=graded.index
    )
    keyless_mask = pd.Series([key is None for key in wanted], index=graded.index)
    excluded = graded[unpairable_mask]

    # Two of the counts below are guards rather than measurements, and saying
    # so is more use to the next reader than a comment implying otherwise.
    # `supplied` equals the three bucket counts for every input this function
    # can be given; `complements` equals `paired_wagers` for every input where
    # the block above still deduplicates. Substitute either pair for the other
    # and the whole suite passes. What they buy is a place for a *later* edit to
    # be caught — a filter or a dedupe added to `graded` above, a complement
    # block that stops being one row per wager — and each is defended by a test
    # that damages the census directly, or breaks the dedupe, rather than by an
    # input frame that cannot produce the failure:
    # `test_a_row_that_reached_no_bucket_makes_the_identity_fail_rather_than_absorb`,
    # `test_a_wager_quoted_two_complements_fails_the_identity_though_the_terms_add_up`,
    # `test_one_complement_per_paired_wager_even_when_the_store_holds_it_twice`,
    # and, across the one boundary that has two real sides, `main`'s comparison
    # of `supplied` against the rows it read from the CSV.
    census = UnpairableCensus(
        supplied=supplied,
        paired=int(paired_mask.sum()),
        unpairable=int(unpairable_mask.sum()),
        no_pair_key=int(keyless_mask.sum()),
        complements=int(len(comp)),
        paired_wagers=len({k for k, ok in zip(wanted, paired_mask) if ok}),
        by_market=_tally(excluded, "market"),
        by_book=_tally(excluded, "book"),
        by_tier=_tally(excluded, "tier"),
        rows=[
            {key: _plain(row.get(key)) for key in NAMING_COLUMNS if key in excluded.columns}
            for row in excluded.head(UNPAIRABLE_ROWS_NAMED).to_dict("records")
        ],
    )
    if FS.SELECTED_COLUMN in excluded.columns and not excluded.empty:
        census.unpairable_selected = int(FS.selected_mask(excluded).sum())

    # Kept: the rows that paired, and the rows that never had a pair to look
    # for. Written as the union of the two terms the census counted rather than
    # as `~unpairable_mask`, so the frame and the census cannot come to disagree
    # about which rows survived without one of them changing.
    kept = graded[paired_mask | keyless_mask]
    # Complement rows exist only to complete the pair: no opinion, no outcome,
    # so they are unscorable by construction. They supply the hold; they are
    # not bets, and the flag says so rather than being left blank.
    comp = comp.reindex(columns=[c for c in graded.columns if c != "_pk"])
    comp["model_probability"] = np.nan
    comp["outcome"] = ""
    comp[FS.SELECTED_COLUMN] = False
    frame = pd.concat([kept.drop(columns=["_pk"]), comp], ignore_index=True)
    return frame, census


def _plain(value: object) -> object:
    """A cell that json.dumps will accept, with NaN spelled as null."""
    if value is None:
        return None
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        number = float(value)
        return None if number != number else number
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    return str(value)


def census_path(out_path: Path) -> Path:
    """The JSON record beside the frame. Named off the frame it describes."""
    return out_path.with_name(f"{out_path.stem}__unpairable.json")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--graded", default="", help=f"defaults to <processed-dir>/{DEFAULT_GRADED}")
    parser.add_argument("--out", default="", help=f"defaults to <processed-dir>/{DEFAULT_OUT}")
    args = parser.parse_args(argv)

    processed = Path(args.processed_dir)
    graded_path = Path(args.graded) if args.graded else processed / DEFAULT_GRADED
    out_path = Path(args.out) if args.out else processed / DEFAULT_OUT
    store_path = H.store_path(CBB, processed, H.CARD_WINDOW)
    for path in (graded_path, store_path):
        if not path.is_file():
            print(f"::error::{path} does not exist. Nothing was written.", file=sys.stderr)
            return 2

    graded = pd.read_csv(graded_path, low_memory=False)
    if "book" not in graded.columns:
        print(
            "::error::The graded frame carries no `book` column, so a complement "
            "cannot be found at the same book. Re-run the backtest with "
            "--write-graded; it carries `book` for exactly this reason.",
            file=sys.stderr,
        )
        return 2
    if FS.SELECTED_COLUMN not in graded.columns:
        print(
            f"::error::The graded frame carries no `{FS.SELECTED_COLUMN}` column. "
            "Before 2026-09-05 the export was the threshold-selected bets and "
            "nothing else; a frame without the flag cannot be told apart from "
            "that winner's-curse slice, and handed to forecast_skill it would be "
            "fitted as every opinion and read as the skill measure. Re-run the "
            "backtest with --write-graded; it now writes every settled opinion "
            "and marks the bets. Nothing was written.",
            file=sys.stderr,
        )
        return 2
    store = pd.read_csv(store_path, low_memory=False)
    selected = int(FS.selected_mask(graded).sum())
    print(
        f"graded {len(graded):,} settled opinion(s), of which {selected:,} are the "
        f"threshold-selected bets | store {len(store):,}"
    )

    frame, census = build(graded, store)
    print("")
    for line in census.lines():
        print(line)
    print("")

    if census.supplied != len(graded):
        print(
            f"::error::The census counted {census.supplied:,} graded rows, but "
            f"{len(graded):,} were read from {graded_path.name}. Rows were lost "
            "between the file and the census, so every count below it — the "
            "population, the excluded share, the threshold this script refuses "
            "at — describes some other frame. Nothing was written.",
            file=sys.stderr,
        )
        return 1
    if not census.reconciles:
        print(
            f"::error::The unpairable census does not reconcile: "
            f"{census.paired:,} paired plus {census.unpairable:,} unpairable "
            f"plus {census.no_pair_key:,} with no pair key is "
            f"{census.accounted:,}, against the {census.supplied:,} graded rows "
            f"supplied, and the frame carries {census.complements:,} complement "
            f"row(s) for {census.paired_wagers:,} paired wager(s). A row that "
            "reached no bucket has vanished from the measurement, and a wager "
            "quoted two complements has had its hold counted twice; either way "
            "the regression would still print an interval. Nothing was "
            "written.",
            file=sys.stderr,
        )
        return 1
    if census.refuses:
        print(
            f"::error::{census.unpairable:,} of {census.supplied:,} graded row(s) "
            f"have no complement at their own book — {census.share:.6%} of the "
            f"frame, above the {census.max_share:.6%} this script will exclude. "
            "Excluding a handful of rows from half a million is bookkeeping; "
            "excluding a share this large is a broken join wearing the costume "
            "of a data quirk, and the census above says which markets and books "
            "it fell on. Nothing was written.",
            file=sys.stderr,
        )
        return 1

    frame.to_csv(out_path, index=False)
    record_path = census_path(out_path)
    record_path.write_text(
        json.dumps(census.to_json(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    # Read off the census rather than as `len(frame) - paired`: a difference
    # is a subtraction, and a subtraction is how the identity above came to
    # reconcile by construction in the first place.
    scorable = census.paired + census.no_pair_key
    print(
        f"Wrote {out_path.name}: {len(frame):,} rows = {scorable:,} scorable + "
        f"{census.complements:,} complement-only, with {census.unpairable:,} graded "
        f"row(s) excluded as unpairable. No request was made and no credit was spent."
    )
    print(
        f"Wrote {record_path.name}: the census, so a reader can state the "
        "population from a count rather than from the frame's length."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
