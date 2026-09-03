"""Whether an edge could have been taken, which is not the question a backtest answers.

`reports/price_backtest.py` says in two places that this file is the thing that
answers whether an edge is **reachable**, and until now it did not exist. Its
line 141 reserves the optional column `survived_to_next_capture` for this
module, and its closing section says the backtest *"cannot say an edge is
reachable. That is `reachability.py`'s question, and an edge living entirely in
prices that vanished is reported there as not reachable regardless of its
size."* Those two comments are this module's specification.

## The rule, in Cooper's words

> A soft number you cannot bet is not an edge. The low-major games with the
> loosest lines have the smallest limits and move fastest. Any measured edge
> that lives entirely in prices that vanish before a human could act is
> reported as NOT REACHABLE, in those words.

That is the college-basketball-specific rule, and it is the one place where
this lab's whole thesis can be true and worthless at the same time. The reason
to build a fourth lab is that the low-major end of a Tuesday board is plausibly
priced with less attention than a Big Ten Saturday. The counterweight is that
the same games carry trivial limits and the fastest moves. **Those two facts
point in opposite directions and this report prints both**, per conference
tier, because a pooled number hides exactly the tension it exists to measure.

## What is measured, and with whose instrument

`line_movement.py` is the instrument. It is captured four times a day on a
cron, it is append-only, and it holds the one fact nothing else can reconstruct:
whether a given quote — same event, market, player, selection, line, book and
**price** — was still on the board at the next capture. Nothing here
reimplements that. Every survival judgment in this file is produced by calling
:func:`line_movement.survival_between` or :func:`line_movement.survival_series`,
and a test pins the labels this module attaches to bets against the aggregate
those same functions return over the same frames.

Two slicing conventions are used to keep that call cheap, and both are
*provably* answer-preserving rather than approximations:

* **Per-bet labelling slices the later capture to the bet's own
  ``(event_id, market)``.** `survival_between` decides coverage at exactly that
  resolution and decides presence on an identity that contains both fields, so
  the slice can change neither answer.
* **Per-tier and per-book survival slice only the *earlier* side.** Filtering
  the later capture by book would be wrong and quietly so: a quote whose
  ``(event, market)`` the next capture covered *through a different book* is
  `GONE`, and hiding that book would relabel it `UNKNOWN` — turning a price
  that really was pulled into a coverage gap, which is this instrument's one
  cardinal error running backwards.

## Unjudgeable is never vanished, and vanished is never unjudgeable

`line_movement` has three outcomes and the third is the point of it. A quote in
an event the next capture never fetched says nothing about whether a book
pulled the price. This module carries that third value all the way into the
report: `SURVIVED`, `GONE` and `UNKNOWN` are three buckets in every table and
the unjudgeable bucket is **never folded into either of the others**. Folding it
into `GONE` would manufacture a not-reachable finding out of a fetch that
skipped an event; folding it into `SURVIVED` would manufacture reachability out
of the same gap. Both are worse than the honest empty cell.

## The normalisation that would otherwise fake a vanished price

A bet frame and a capture store meet across a CSV round-trip, and that
round-trip does not preserve spellings: an absent `player` is `""` on one side
and `NaN` on the other, a line is `142.5` here and `"142.5"` there. Compared
raw, the identical quote does not match itself — and the failure is silent and
**directional**: an unmatched quote looks like a price that was pulled, which
is a reachability finding manufactured out of a join. That is the fifth member
of the NHL lab's join-vocabulary bug family, and `stores._dedupe_value` is the
one normaliser this repository has for it. Both sides of every comparison here
go through it before `line_movement` is asked anything.

## Beating an opening number is not a bet

`docs/what_we_can_and_cannot_claim.md` requires that sentence *"wherever such a
figure appears"*, so :data:`OPENING_NUMBER_IS_NOT_A_BET` is printed in the
header, beside the first-capture split, and again in the closing section. The
first capture of a slate day is the closest thing this lab holds to an opening
number, and a return computed against it is a description of how the market
moved, not of a wager anybody could have placed.

## What this instrument cannot see, said out loud

**Limits.** The provider serves a price and a book; it does not serve the
maximum stake that book would accept on a Thursday low-major total. So a quote
that survived to the next capture is evidence that the *number* was still
there, and it is not evidence that a bet of any size would have been taken. The
brief names trivial limits and vanishing prices in the same breath, and this
report can measure only the second. Saying so is the difference between a
partial instrument and an overstated one.

## Not enough evidence, in September

There is no college basketball between April and November, the capture script
writes nothing when the board is empty, and today the store holds at most a few
days of off-season captures. So the honest output of this module right now is
**"not enough evidence"** in those words, with the census that justifies it —
never a crash, and never an empty table, because an empty table reads as a null
result and a null result is a claim.

## Re-renderable from its record

The retention probe's rule, for the same reason: :func:`build_record` holds
every count a run made and :func:`render` is a pure function of it — no clock,
no network, no store. Improving a sentence must never cost a re-run, because a
report that can only be produced by re-running the measurement is a report
nobody improves.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

import pandas as pd

from cbb_betting_lab import line_movement as LM
from cbb_betting_lab import stats as S
from cbb_betting_lab import stores
from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.reports import price_backtest as PB

#: Bumped whenever the record's shape changes, so a stale record fails loudly
#: at re-render rather than rendering a report with holes in it.
RECORD_VERSION = 1

#: The literal a report prints when an edge exists and cannot be taken. Cooper:
#: *"a soft number you cannot bet is not an edge."* Restated here rather than
#: imported from `forward_evidence`, which is a 2,000-line module this report
#: has no other reason to load — and pinned equal to it by
#: `tests/test_reachability.py::test_the_not_reachable_phrase_is_one_phrase`.
NOT_REACHABLE = "not reachable"

#: Its opposite, and it is deliberately not the word "reachable" on its own. A
#: price that survived to the next capture was still on the board; whether the
#: book would have taken a stake of any size is a question about limits, which
#: this instrument cannot see. See :data:`LIMITS_ARE_NOT_OBSERVABLE`.
REACHABLE_IN_SURVIVING_PRICES = "reachable in prices that survived"

#: Below the declared floors there is no number, only these words. Same phrase
#: `stats.RoiInterval.verdict` uses, so a thin store and a thin sample read
#: identically to somebody skimming.
NOT_ENOUGH_EVIDENCE = "not enough evidence"

#: The column `price_backtest.OPTIONAL_BET_COLUMNS` reserves for this module.
#: It turns the split on rather than being faked when absent.
SURVIVED_COLUMN = "survived_to_next_capture"

#: The capture stamp, which is the identity of a capture and never of a quote.
CAPTURE_COLUMN = "captured_at"

#: Cooper's instruction: regions stay `us,us2`. Restated rather than imported
#: so a pure report module does not pull in the HTTP provider, and pinned equal
#: to `providers.odds_api.DEFAULT_REGIONS` by a test.
REGIONS = "us,us2"

#: Survival is a statement about a quote at the **next** capture. One capture
#: is not thin evidence, it is no evidence, and this is structural rather than
#: a threshold anybody chose.
MINIMUM_CAPTURES = 2

#: Declared in advance. Below this many *judged* quotes the board-level
#: survival rate is "not enough evidence" rather than a number. One in-season
#: featured-board capture is on the order of twenty thousand quotes across a
#: full slate, and an off-season capture is zero — the capture script writes
#: nothing when the board is empty. So this bar separates "the season has not
#: started" from "the instrument is running", and it is nowhere near a bar that
#: a real pair of captures has to strain for.
MINIMUM_JUDGED_QUOTES = 1_000

#: Printed in the header, beside the first-capture split, and again at the end.
OPENING_NUMBER_IS_NOT_A_BET = (
    "**Beating an opening number is not a bet.** The first capture of a slate "
    "day is the earliest number this lab holds, and a return measured against "
    "it describes how the market moved rather than a wager anybody placed. No "
    "figure in this report is evidence about a price that had already gone by "
    "the time a card was produced."
)

#: The limitation that keeps this report from overstating its own instrument.
LIMITS_ARE_NOT_OBSERVABLE = (
    "**Limits are not observable from this instrument.** The provider serves a "
    "price and a book; it does not serve the maximum stake that book would "
    "accept on a Thursday low-major total. A quote that survived to the next "
    "capture is evidence that the *number* was still there, and it is not "
    "evidence that a stake of any size would have been taken. The brief names "
    "trivial limits and vanishing prices together; this report measures only "
    "the second, and a surviving price at a trivial limit is still not a bet."
)

#: Printed wherever a book appears. A price Cooper cannot open manufactures an
#: untakeable edge, which is the single thing this lab is most trying not to do.
REGIONS_CAVEAT = (
    f"**Regions stay `{REGIONS}`.** Every quote below comes from a book inside "
    "those regions, because a price at a book Cooper cannot open is not "
    "reachable by definition and manufactures untakeable edges. A book absent "
    "from this table was not measured and found unreachable — it was never "
    "captured, and the two are different claims."
)

#: The three buckets, in the order every table prints them. `line_movement`'s
#: own vocabulary, unchanged, because a fourth spelling of these three states
#: is a fourth chance to fold the unjudgeable into the vanished.
BUCKETS: tuple[str, ...] = (LM.SURVIVED, LM.GONE, LM.UNKNOWN)

#: How each bucket is titled in a table. The unjudgeable bucket is named for
#: what it is rather than for what it is not.
BUCKET_TITLES: dict[str, str] = {
    LM.SURVIVED: "survived to the next capture",
    LM.GONE: "gone by the next capture",
    LM.UNKNOWN: "unjudgeable — the next capture did not cover it",
}

#: The pooled row's tier label. Never a tier, and never printed alone.
POOLED = "pooled"

#: Where a quote's tier could not be established because nothing supplied one.
UNTIERED = "untiered"


class ReachabilityError(RuntimeError):
    """Reachability could not be judged honestly, so it was not judged."""


# --------------------------------------------------------------------------
# The store
# --------------------------------------------------------------------------


def store_path(competition: Competition, processed_dir: Path | str) -> Path:
    """The line-movement store. `line_movement` owns the name; this asks it."""
    return LM.store_path(competition, Path(processed_dir))


def load_store(
    competition: Competition = CBB, processed_dir: Path | str = "."
) -> pd.DataFrame:
    """The capture store, or an empty frame in its own shape.

    A missing store is an ordinary state in September and is **not** an error:
    the season opens in November and the capture script writes nothing when the
    board is empty, because an empty capture would later read as every price
    having vanished. So this returns an empty frame with the right columns and
    :func:`store_summary` says in words that the instrument has not run yet.
    """
    return stores.read_store(
        store_path(competition, processed_dir), columns=LM.CAPTURE_COLUMNS
    )


def store_summary(store: pd.DataFrame, *, path: Path | str = "") -> dict:
    """The census that justifies whatever verdict this run is allowed to give.

    Every number in a report carries its sample size, and for this report the
    sample size is the store: how many quotes, across how many captures, over
    how many events, books and slate days, between which two timestamps. When
    that census is below :data:`MINIMUM_CAPTURES` or
    :data:`MINIMUM_JUDGED_QUOTES` the run is entitled to no survival number at
    all, and `enough_evidence` says so with the reason attached rather than
    leaving a reader to infer it from an empty table.
    """
    summary: dict = {
        "path": str(path),
        "quotes": int(len(store)),
        "captures": 0,
        "first_capture": "",
        "last_capture": "",
        "events": 0,
        "books": 0,
        "slate_days": 0,
        "judged_quotes": 0,
        "enough_evidence": False,
        "reason": "",
    }
    if store.empty:
        summary["reason"] = (
            "The line-movement store holds no captures. The season opens in "
            "November, there is no college basketball between April and "
            "November, and the capture script writes nothing when the board "
            "is empty — because an empty capture would later read as every "
            "price having vanished. This is an observation about the calendar "
            "and not a fault."
        )
        return summary

    stamps = sorted(str(s) for s in store[CAPTURE_COLUMN].dropna().unique())
    summary["captures"] = len(stamps)
    summary["first_capture"] = stamps[0] if stamps else ""
    summary["last_capture"] = stamps[-1] if stamps else ""
    summary["events"] = int(store["event_id"].nunique())
    summary["books"] = int(store["book"].nunique())
    summary["slate_days"] = int(store["slate_date"].nunique())
    summary["judged_quotes"] = sum(s.judged for s in LM.survival_series(store))

    if summary["captures"] < MINIMUM_CAPTURES:
        summary["reason"] = (
            f"The store holds {summary['captures']} capture(s), below the "
            f"{MINIMUM_CAPTURES} this module requires. Survival is a statement "
            "about a quote at the **next** capture, and there has not been "
            "one. That is not thin evidence, it is no evidence."
        )
        return summary
    if summary["judged_quotes"] < MINIMUM_JUDGED_QUOTES:
        summary["reason"] = (
            f"{summary['judged_quotes']:,} quotes could be judged across "
            f"{summary['captures']} captures, below the "
            f"{MINIMUM_JUDGED_QUOTES:,} declared in advance. One in-season "
            "capture of the featured board runs to tens of thousands of "
            "quotes across a full slate, so a store under this bar is a store "
            "captured out of season rather than an instrument with something "
            "to say."
        )
        return summary
    summary["enough_evidence"] = True
    return summary


# --------------------------------------------------------------------------
# Identity, in one spelling on both sides
# --------------------------------------------------------------------------


def _normalise_identity(frame: pd.DataFrame) -> pd.DataFrame:
    """Every identity column in one spelling, on both sides of a comparison.

    `stores._dedupe_value` is the repository's one normaliser for this and is
    used deliberately rather than copied: `""`, `None` and `NaN` are the same
    absent player; `142.5` and `"142.50"` are the same line. A CSV round-trip
    preserves neither, and an identity that does not match itself across that
    round-trip looks exactly like a price a book pulled.

    That failure is silent **and directional** — it can only ever invent
    vanished prices, never surviving ones — which makes it the one join defect
    that could produce a not-reachable finding out of nothing.
    """
    out = frame.copy()
    for column in LM.QUOTE_IDENTITY:
        if column in out.columns:
            out[column] = out[column].map(stores._dedupe_value)
        else:
            out[column] = ""
    return out


def _identity_tuples(frame: pd.DataFrame) -> list[tuple]:
    return [
        tuple(row)
        for row in frame[list(LM.QUOTE_IDENTITY)].itertuples(index=False, name=None)
    ]


def _survival_word(value: object) -> str:
    """One of the three states from an already-stamped column.

    A **missing** value is `UNKNOWN` and never `GONE`. Nothing recorded is not
    a price that was pulled, and reading it as one is the whole failure this
    module exists to avoid, arriving through a null instead of through a join.
    """
    text = stores._dedupe_value(value).casefold()
    if text in {"1", "true", "yes", "y", LM.SURVIVED, "survived"}:
        return LM.SURVIVED
    if text in {"0", "false", "no", "n", LM.GONE, "gone", "vanished"}:
        return LM.GONE
    return LM.UNKNOWN


# --------------------------------------------------------------------------
# Labelling bets, using line_movement's own judgment
# --------------------------------------------------------------------------


def label_survival(bets: pd.DataFrame, store: pd.DataFrame) -> pd.Series:
    """`SURVIVED` / `GONE` / `UNKNOWN` for each staked bet, decided by `line_movement`.

    Every label is produced by an actual call to
    :func:`line_movement.survival_between`; this function's only work is
    deciding *which* capture a bet's price was taken at and handing that
    function the right two frames.

    Which capture:

    * If the bets carry :data:`CAPTURE_COLUMN`, that is the capture, full stop.
    * Otherwise the bet is matched into the store on quote identity and taken
      at the **earliest** capture that held it — the first moment a card could
      have seen that exact price. A quote the store never held is `UNKNOWN`:
      this instrument has nothing to say about a price it never observed, and
      calling that `GONE` would score a coverage gap as a vanished price.
    * A bet taken at the store's **last** capture is `UNKNOWN` too. There is no
      next capture yet, so nothing can be said — the cron has not caught up
      with the bet, which is not the same as the book pulling the number.

    The later capture is sliced to the bet's own ``(event_id, market)`` before
    `survival_between` is called. That slice cannot change the answer:
    coverage is decided at exactly that resolution and presence is decided on
    an identity containing both fields.
    `tests/test_reachability.py::test_the_labels_agree_with_line_movement_itself`
    pins the equivalence against the unsliced function.
    """
    if bets.empty:
        return pd.Series(dtype="object")
    unknown = pd.Series([LM.UNKNOWN] * len(bets), index=bets.index, dtype="object")
    if store.empty or CAPTURE_COLUMN not in store.columns:
        return unknown

    normalised_store = _normalise_identity(store)
    normalised_store[CAPTURE_COLUMN] = store[CAPTURE_COLUMN].astype(str)
    stamps = sorted(str(s) for s in normalised_store[CAPTURE_COLUMN].dropna().unique())
    following = dict(zip(stamps, stamps[1:]))
    if not following:
        # One capture. `survival_series` would return nothing here too.
        return unknown

    # The earliest capture that held each quote, for bets with no stamp of
    # their own. Built in capture order so "earliest" needs no comparison.
    first_seen: dict[tuple, str] = {}
    for stamp in stamps:
        chunk = normalised_store[normalised_store[CAPTURE_COLUMN] == stamp]
        for identity in _identity_tuples(chunk):
            first_seen.setdefault(identity, stamp)

    # The later capture, grouped by (event_id, market) — the resolution at
    # which `survival_between` decides coverage.
    grouped: dict[str, dict[tuple, pd.DataFrame]] = {}
    for stamp in set(following.values()):
        chunk = normalised_store[normalised_store[CAPTURE_COLUMN] == stamp]
        grouped[stamp] = {
            key: frame for key, frame in chunk.groupby(["event_id", "market"])
        }

    normalised_bets = _normalise_identity(bets)
    stamped = (
        bets[CAPTURE_COLUMN].astype(str)
        if CAPTURE_COLUMN in bets.columns
        else pd.Series([""] * len(bets), index=bets.index)
    )
    empty_later = pd.DataFrame(columns=list(LM.CAPTURE_COLUMNS))

    labels: list[str] = []
    for position, identity in enumerate(_identity_tuples(normalised_bets)):
        stamp = stamped.iloc[position]
        if not stamp or stamp == "nan":
            stamp = first_seen.get(identity, "")
        later_stamp = following.get(stamp, "")
        if not later_stamp:
            labels.append(LM.UNKNOWN)
            continue
        later = grouped[later_stamp].get((identity[0], identity[1]), empty_later)
        earlier = pd.DataFrame(
            [dict(zip(LM.QUOTE_IDENTITY, identity), **{CAPTURE_COLUMN: stamp})]
        )
        judged = LM.survival_between(earlier, later)
        if judged.survived:
            labels.append(LM.SURVIVED)
        elif judged.gone:
            labels.append(LM.GONE)
        else:
            labels.append(LM.UNKNOWN)
    return pd.Series(labels, index=bets.index, dtype="object")


def attach_survival(bets: pd.DataFrame, store: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    """Put a `reachability` column on the bets, and say where it came from.

    Provenance is recorded rather than assumed, because the three sources are
    three different strengths of claim and a reader must be able to tell them
    apart:

    * ``column`` — the bets already carry :data:`SURVIVED_COLUMN`, stamped when
      the opinion was frozen against a live board. This is the strongest form:
      the survival was judged against the capture the price was actually taken
      from.
    * ``store`` — the bets were matched into the capture store here.
    * ``none`` — neither. Survival is then **unmeasured**, which is not the
      same as measured and found fine, and the report says so in those terms.
    """
    if bets.empty:
        return bets.assign(reachability=pd.Series(dtype="object")), {
            "source": "none",
            "bets": 0,
            "survived": 0,
            "gone": 0,
            "unknown": 0,
            "note": (
                "No staked bet was supplied, so there was nothing to split. "
                "This is a wiring state and not a null result."
            ),
        }

    if SURVIVED_COLUMN in bets.columns and bets[SURVIVED_COLUMN].notna().any():
        labels = bets[SURVIVED_COLUMN].map(_survival_word)
        source = "column"
        note = (
            f"Survival was read from the `{SURVIVED_COLUMN}` column the bets "
            "already carried, which is the strongest form of this evidence: "
            "the quote was judged against the capture the price was actually "
            "taken from. A missing value is unjudgeable and never vanished."
        )
    elif not store.empty:
        labels = label_survival(bets, store)
        source = "store"
        note = (
            "Survival was judged here by matching each staked quote into the "
            "line-movement store and asking `line_movement.survival_between` "
            "what became of it at the next capture. A quote the store never "
            "held is unjudgeable, never vanished."
        )
    else:
        labels = pd.Series([LM.UNKNOWN] * len(bets), index=bets.index, dtype="object")
        source = "none"
        note = (
            "Neither the bets nor a line-movement store carried survival, so "
            "reachability is **unmeasured here rather than measured and found "
            "fine**. A return reported without it is a return over prices that "
            "may not have existed by the time anybody could take them."
        )

    counts = labels.value_counts()
    return bets.assign(reachability=labels), {
        "source": source,
        "bets": int(len(bets)),
        "survived": int(counts.get(LM.SURVIVED, 0)),
        "gone": int(counts.get(LM.GONE, 0)),
        "unknown": int(counts.get(LM.UNKNOWN, 0)),
        "note": note,
    }


# --------------------------------------------------------------------------
# Board-level survival: per capture pair, per tier, per book
# --------------------------------------------------------------------------


def _survival_row(judged: LM.Survival, **extra) -> dict:
    row = {
        "earlier": judged.earlier,
        "later": judged.later,
        "judged": judged.judged,
        "survived": judged.survived,
        "gone": judged.gone,
        "unknown": judged.unknown,
        "survival_rate": judged.survival_rate,
    }
    row.update(extra)
    return row


def capture_pairs(store: pd.DataFrame) -> list[dict]:
    """Survival between every consecutive pair, straight from `survival_series`."""
    return [_survival_row(s) for s in LM.survival_series(store)]


def _totals(rows: Sequence[Mapping], **extra) -> dict:
    survived = sum(int(r["survived"]) for r in rows)
    gone = sum(int(r["gone"]) for r in rows)
    unknown = sum(int(r["unknown"]) for r in rows)
    judged = survived + gone
    row = {
        "earlier": rows[0]["earlier"] if rows else "",
        "later": rows[-1]["later"] if rows else "",
        "judged": judged,
        "survived": survived,
        "gone": gone,
        "unknown": unknown,
        "survival_rate": (survived / judged) if judged else None,
    }
    row.update(extra)
    return row


def survival_by_book(store: pd.DataFrame) -> list[dict]:
    """Survival per book, filtering only the **earlier** side of each pair.

    Filtering the later capture by book would be wrong in the direction this
    module must never be wrong in. A quote whose ``(event, market)`` the next
    capture covered through some *other* book is `GONE` — the price really was
    pulled — and hiding that other book would relabel it `UNKNOWN`, converting
    a vanished price into a coverage gap. So only the earlier side is sliced,
    and `line_movement` sees the whole later board exactly as it would
    otherwise.
    """
    if store.empty or CAPTURE_COLUMN not in store.columns:
        return []
    stamps = sorted(str(s) for s in store[CAPTURE_COLUMN].dropna().unique())
    stamp_column = store[CAPTURE_COLUMN].astype(str)
    rows: list[dict] = []
    for book in sorted(str(b) for b in store["book"].dropna().unique()):
        per_pair: list[dict] = []
        for earlier_stamp, later_stamp in zip(stamps, stamps[1:]):
            earlier = store[(stamp_column == earlier_stamp) & (store["book"].astype(str) == book)]
            later = store[stamp_column == later_stamp]
            per_pair.append(_survival_row(LM.survival_between(earlier, later)))
        quotes = int((store["book"].astype(str) == book).sum())
        rows.append(_totals(per_pair, book=book, quotes=quotes))
    return rows


def survival_by_tier(store: pd.DataFrame, tiers: Mapping) -> list[dict]:
    """Survival per conference tier, again slicing only the earlier side.

    This is one half of the thesis and it is the half that is easy to forget.
    The low-major end of the board is the looser end **and** the faster one; a
    tier that prices badly and holds its number for fifteen minutes is a
    different proposition from one that prices badly and is gone in two. The
    report prints this table beside the return table for exactly that reason,
    because the two point in opposite directions and one without the other is
    half an argument.

    `tiers` maps `event_id` to a tier. Quotes on events it does not cover are
    reported under :data:`UNTIERED` rather than dropped or guessed — a quote
    whose tier nobody supplied is not a low-major quote.
    """
    if store.empty or CAPTURE_COLUMN not in store.columns:
        return []
    mapping = {str(k): str(v) for k, v in dict(tiers).items()}
    tier_of = store["event_id"].astype(str).map(mapping).fillna(UNTIERED)
    stamps = sorted(str(s) for s in store[CAPTURE_COLUMN].dropna().unique())
    stamp_column = store[CAPTURE_COLUMN].astype(str)
    present = {str(t) for t in tier_of.unique()}
    ordered = [t for t in PB.TIER_ORDER if t in present]
    ordered += sorted(present - set(ordered))
    rows: list[dict] = []
    for tier in ordered:
        per_pair: list[dict] = []
        for earlier_stamp, later_stamp in zip(stamps, stamps[1:]):
            earlier = store[(stamp_column == earlier_stamp) & (tier_of == tier)]
            later = store[stamp_column == later_stamp]
            per_pair.append(_survival_row(LM.survival_between(earlier, later)))
        quotes = int((tier_of == tier).sum())
        rows.append(_totals(per_pair, tier=tier, quotes=quotes))
    return rows


def tier_map_from_bets(bets: pd.DataFrame) -> dict:
    """`event_id -> tier`, taken from the bets rather than refitted.

    The capture store carries no tier — `line_movement.CAPTURE_COLUMNS` is the
    board as the provider served it — and this module will not refit conference
    tiers to fill the gap. A tier is a walk-forward measurement made in
    `conferences.py` from seasons strictly before the one being priced, and a
    second derivation here would be a second answer. So the tier comes from the
    frame that already carries the one this lab used.
    """
    if bets.empty or "tier" not in bets.columns or "event_id" not in bets.columns:
        return {}
    pairs = bets[["event_id", "tier"]].dropna().astype(str).drop_duplicates()
    return dict(zip(pairs["event_id"], pairs["tier"]))


# --------------------------------------------------------------------------
# The returns, split by reachability
# --------------------------------------------------------------------------


def _interval(frame: pd.DataFrame, *, looks: int) -> S.RoiInterval:
    """Two-way clustered interval over a graded frame. Game and day, wider wins.

    `stats.interval_two_way` and nothing else. One game supplies a spread, a
    total, two team totals and a dozen props, and they are one evening seen
    fifteen ways; a per-bet interval over them is narrower than the truth by
    roughly the square root of the cluster size. The football lab's forward
    ledger got this wrong by a factor of 10.3 and its own docstring says why it
    mattered: *a narrow interval is how "no demonstrated edge" quietly becomes
    a claim.*
    """
    usable = PB.settled(frame)
    if usable.empty:
        return S.RoiInterval(0.0, 0.0, 0.0, 0, 0, looks=looks)
    return S.interval_two_way(
        usable.assign(
            profit_units=pd.to_numeric(usable["profit_units"], errors="coerce")
        ),
        looks=looks,
    )


def _tier_column(bets: pd.DataFrame) -> pd.Series:
    """The tier of every bet, with a missing one named rather than dropped.

    A bet whose tier is null is not a low-major bet and it is not nothing
    either. Dropping those rows would let the pooled row hold bets that no tier
    row holds, and the two would silently disagree — so they land under
    :data:`UNTIERED`, which is a tier label a reader can see.
    """
    return bets["tier"].map(stores._dedupe_value).replace("", UNTIERED)


def _tiers_in(tier_of: pd.Series) -> list[str]:
    present = {str(t) for t in tier_of.unique()}
    ordered = [t for t in PB.TIER_ORDER if t in present]
    return ordered + sorted(present - set(ordered))


def _cell(
    frame: pd.DataFrame, *, looks: int, tier: str, bucket: str, market: str = ""
) -> dict:
    """One measured cell as plain data, in `price_backtest`'s record vocabulary.

    `PB._interval_row` is used deliberately rather than copied. Two reports
    that serialise a `RoiInterval` two ways drift, and the direction they drift
    in is never the conservative one — `stats.py`'s own docstring is about
    exactly that, one layer up. `interval_from_row` reads these rows back, so
    the two reports also stay re-renderable by the same code.
    """
    row = dict(
        PB._interval_row(
            _interval(frame, looks=looks),
            name=BUCKET_TITLES[bucket],
            market=market,
            tier=tier,
        )
    )
    row["reachability"] = bucket
    return row


def split_by_reachability(bets: pd.DataFrame, *, looks: int = 1) -> list[dict]:
    """The lead table: tier x reachability, with the pooled rows beside them.

    **Per tier, never a pooled headline.** The pooled rows are computed because
    `docs/when_this_ends.md` applies its stopping rule to the pooled figure as
    well, and they are printed in the same table as the tier rows, under
    :data:`price_backtest.POOLED_CAVEAT`, never on their own.

    All three buckets are printed for every tier, including the unjudgeable
    one. A cell of unjudgeable bets is not a hole in the table; it is the
    measure of how much of this sample the instrument could not speak to, and
    hiding it would let a thin judgment pass for a complete one.
    """
    if bets.empty or "reachability" not in bets.columns:
        return []
    rows: list[dict] = []
    tier_of = _tier_column(bets)
    for tier in _tiers_in(tier_of):
        cell = bets[tier_of == tier]
        for bucket in BUCKETS:
            rows.append(
                _cell(
                    cell[cell["reachability"] == bucket],
                    looks=looks,
                    tier=tier,
                    bucket=bucket,
                )
            )
    for bucket in BUCKETS:
        rows.append(
            _cell(
                bets[bets["reachability"] == bucket],
                looks=looks,
                tier=POOLED,
                bucket=bucket,
            )
        )
    return rows


def split_by_market(bets: pd.DataFrame, *, looks: int = 1) -> list[dict]:
    """Market x tier x reachability, for reading a tier verdict apart.

    A tier is not one instrument. A moneyline on a low-major Tuesday and an
    alternate total on the same game move at different speeds, and a tier
    verdict that is really one market's behaviour should be visible as such.
    """
    if bets.empty or "reachability" not in bets.columns:
        return []
    rows: list[dict] = []
    tier_of = _tier_column(bets)
    for tier in _tiers_in(tier_of):
        for market in sorted(str(m) for m in bets["market"].dropna().unique()):
            cell = bets[(tier_of == tier) & (bets["market"].astype(str) == market)]
            if cell.empty:
                continue
            for bucket in BUCKETS:
                chunk = cell[cell["reachability"] == bucket]
                if chunk.empty:
                    continue
                rows.append(
                    _cell(chunk, looks=looks, tier=tier, bucket=bucket, market=market)
                )
    return rows


def _bucket_row(rows: Sequence[Mapping], tier: str, bucket: str) -> dict:
    for row in rows:
        if row.get("tier") == tier and row.get("reachability") == bucket:
            return dict(row)
    return {}


def reachability_verdict(rows: Sequence[Mapping], tier: str) -> dict:
    """The one sentence a tier's split is permitted to be described by.

    **The sign is read by `stats.RoiInterval.verdict` and nowhere else.** This
    function compares that verdict's *words* against
    `stats.DEMONSTRATED_EDGE`; it never looks at whether a number is above or
    below zero itself. The NHL lab's claims document announced a replicated
    **loss** as good news because a headline predicate tested everything except
    which side of zero the number sat on, and the one place a sign is read into
    a verdict string stays `stats.py`.

    The rule, declared here rather than discovered later:

    * The survived set shows a demonstrated edge — the edge is
      :data:`REACHABLE_IN_SURVIVING_PRICES`. Which is still not a play: no
      market is allowlisted and limits are unobservable.
    * The vanished set shows a demonstrated edge and the survived set does not
      — the edge lives entirely in prices that were gone by the next capture
      and is **not reachable**, in those words, regardless of its size or its
      significance.
    * Neither set clears the floor — **not enough evidence**, and no number.
    * Otherwise — **no demonstrated edge**, in those exact words.
    """
    survived_row = _bucket_row(rows, tier, LM.SURVIVED)
    vanished_row = _bucket_row(rows, tier, LM.GONE)
    unknown_row = _bucket_row(rows, tier, LM.UNKNOWN)
    survived = PB.interval_from_row(survived_row or {})
    vanished = PB.interval_from_row(vanished_row or {})
    survived_verdict = survived.verdict()
    vanished_verdict = vanished.verdict()

    if survived_verdict == S.DEMONSTRATED_EDGE:
        verdict = REACHABLE_IN_SURVIVING_PRICES
        sentence = (
            f"The measured edge is present in prices that were still on the "
            f"board at the next capture ({survived.line()}), so it is "
            f"**{REACHABLE_IN_SURVIVING_PRICES}**. That is not a play: no "
            "market is allowlisted, and a surviving number is not a limit."
        )
    elif vanished_verdict == S.DEMONSTRATED_EDGE:
        verdict = NOT_REACHABLE
        sentence = (
            f"The measured edge lives entirely in prices that did not survive "
            f"to the next capture ({vanished.line()}), while the prices that "
            f"did survive show {survived_verdict} ({survived.line()}). It is "
            f"therefore **{NOT_REACHABLE}** — regardless of its size or its "
            "significance."
        )
    elif not survived.enough_evidence and not vanished.enough_evidence:
        verdict = NOT_ENOUGH_EVIDENCE
        sentence = (
            f"**{NOT_ENOUGH_EVIDENCE.capitalize()}.** {survived.bets:,} bets "
            f"survived and {vanished.bets:,} vanished, both below the "
            f"{S.MINIMUM_BETS:,} declared in advance, so neither side of the "
            "split gets a number."
        )
    else:
        verdict = S.NO_DEMONSTRATED_EDGE
        sentence = (
            f"Neither side of the split demonstrates an edge: survived "
            f"{survived.line()}; vanished {vanished.line()}. Reachability "
            "decides nothing here, because there is nothing to reach."
        )
    return {
        "tier": tier,
        "verdict": verdict,
        "sentence": sentence,
        "survived_bets": survived.bets,
        "vanished_bets": vanished.bets,
        "unjudgeable_bets": int(unknown_row.get("bets", 0)),
        "survived_verdict": survived_verdict,
        "vanished_verdict": vanished_verdict,
    }


# --------------------------------------------------------------------------
# The opening number, which is not a bet
# --------------------------------------------------------------------------


def first_capture_of_each_day(store: pd.DataFrame) -> dict:
    """`slate_date -> the earliest capture stamp that covered it`."""
    if store.empty or CAPTURE_COLUMN not in store.columns:
        return {}
    frame = store[["slate_date", CAPTURE_COLUMN]].dropna().astype(str)
    if frame.empty:
        return {}
    return frame.groupby("slate_date")[CAPTURE_COLUMN].min().to_dict()


def opening_number_split(
    bets: pd.DataFrame, store: pd.DataFrame, *, looks: int = 1
) -> dict:
    """Bets taken at a slate day's first capture, apart from the rest.

    The first capture is the earliest number this lab holds, which makes it
    this instrument's opening number. A return measured against it describes
    how the market moved rather than a wager anybody placed, so it is reported
    **apart** and :data:`OPENING_NUMBER_IS_NOT_A_BET` is printed beside it every
    time it appears.

    This needs a capture stamp on the bets. Without one the split is refused
    rather than approximated: guessing which bets were early would put the
    caveat on the wrong rows, which is worse than not splitting at all.
    """
    if bets.empty:
        return {
            "measured": False,
            "note": (
                "No staked bet reached this report, so nothing could be split "
                "by when its price was taken. " + OPENING_NUMBER_IS_NOT_A_BET
            ),
        }
    if CAPTURE_COLUMN not in bets.columns:
        return {
            "measured": False,
            "note": (
                "The bets carry no capture stamp, so which of them were taken "
                "at a slate day's first capture cannot be established. The "
                "split is refused rather than approximated: guessing which "
                "bets were early would put this caveat on the wrong rows, "
                "which is worse than not splitting at all. "
                + OPENING_NUMBER_IS_NOT_A_BET
            ),
        }
    firsts = first_capture_of_each_day(store)
    if not firsts:
        return {
            "measured": False,
            "note": (
                "The line-movement store holds no capture, so no slate day has "
                "a first one. " + OPENING_NUMBER_IS_NOT_A_BET
            ),
        }
    stamp = bets[CAPTURE_COLUMN].astype(str)
    expected = bets["slate_date"].astype(str).map(firsts)
    at_open = stamp == expected
    return {
        "measured": True,
        "at_first_capture": PB._interval_row(
            _interval(bets[at_open], looks=looks),
            name="taken at the slate day's first capture",
        ),
        "later": PB._interval_row(
            _interval(bets[~at_open], looks=looks),
            name="taken at a later capture",
        ),
        "note": OPENING_NUMBER_IS_NOT_A_BET,
    }


# --------------------------------------------------------------------------
# The record
# --------------------------------------------------------------------------


def build_record(
    bets: pd.DataFrame | None = None,
    store: pd.DataFrame | None = None,
    *,
    competition: Competition = CBB,
    looks: int = 1,
    generated_at: str = "",
    store_path_hint: Path | str = "",
) -> dict:
    """Every count this run made, as plain data. :func:`render` is pure over it.

    The retention probe's rule, applied for the retention probe's reason:
    improving a sentence must never cost a re-run. Nothing in here is a
    `RoiInterval`, a frame or a timestamp read from a clock — it is JSON, and
    `scripts/run_reachability.py --rerender` rebuilds the whole report from it
    without touching the store.
    """
    bets = pd.DataFrame() if bets is None else bets
    store = pd.DataFrame(columns=list(LM.CAPTURE_COLUMNS)) if store is None else store
    if not bets.empty:
        PB.require_columns(bets, PB.BET_COLUMNS, "the graded bet frame")

    labelled, provenance = attach_survival(bets, store)
    tiers = tier_map_from_bets(labelled)
    rows = split_by_reachability(labelled, looks=looks)
    tier_labels = [t for t in dict.fromkeys(r["tier"] for r in rows)]

    return {
        "record_version": RECORD_VERSION,
        "competition": competition.key,
        "title": competition.title,
        "generated_at": generated_at,
        "regions": REGIONS,
        "looks": int(looks),
        "correction_factor": S.bonferroni_factor(int(looks)),
        "minimum_bets": S.MINIMUM_BETS,
        "minimum_captures": MINIMUM_CAPTURES,
        "minimum_judged_quotes": MINIMUM_JUDGED_QUOTES,
        "store": store_summary(store, path=store_path_hint),
        "capture_pairs": capture_pairs(store),
        "by_book": survival_by_book(store),
        "board_by_tier": survival_by_tier(store, tiers) if tiers else [],
        "survival_provenance": provenance,
        "by_tier_and_reachability": rows,
        "by_market_tier_and_reachability": split_by_market(labelled, looks=looks),
        "verdicts": [reachability_verdict(rows, tier) for tier in tier_labels],
        "opening_number": opening_number_split(labelled, store, looks=looks),
        "games": int(labelled["event_id"].nunique()) if not labelled.empty else 0,
        "days": int(labelled["slate_date"].nunique()) if not labelled.empty else 0,
    }


# --------------------------------------------------------------------------
# Rendering — a pure function of the record
# --------------------------------------------------------------------------


def _rate(value: object) -> str:
    return "—" if value is None else f"{float(value):.1%}"


def _plural(count: int, singular: str, plural: str = "") -> str:
    """`1 slate day`, `4 slate days`. A generated report still has to read."""
    return f"{count:,} {singular if count == 1 else (plural or singular + 's')}"


def _roi_row(row: Mapping, label: str) -> str:
    roi, interval, corrected = PB.roi_cells(dict(row))
    return (
        f"| {row.get('tier', '')} | {label} | {row.get('bets', 0):,} | "
        f"{row.get('clusters', 0):,} | {roi} | {interval} | {corrected} | "
        f"{row.get('verdict', '')} |"
    )


def render(record: Mapping) -> str:
    """The report, as a pure function of the record. No clock, no store, no network."""
    lines: list[str] = []
    add = lines.append
    add(f"# {record.get('title', CBB.title)} — reachability")
    add("")
    if record.get("generated_at"):
        add(f"Generated {record['generated_at']}.")
        add("")
    add(
        "**A soft number you cannot bet is not an edge.** This report does not "
        "ask whether a price would have won; `price_backtest.py` asks that. It "
        "asks whether the price was still on the board when a human reached "
        "for it, and it reports the return of the prices that survived apart "
        "from the return of the prices that did not."
    )
    add("")
    add(
        "**The two facts point in opposite directions, so both are printed.** "
        "The low-major end of the board is the looser end — that is the reason "
        "this lab exists — and it is also the end with the smallest limits and "
        "the fastest moves. A tier that prices badly and holds its number is a "
        "different proposition from a tier that prices badly and is gone in "
        "two minutes, and a pooled number hides exactly that difference."
    )
    add("")
    add(REGIONS_CAVEAT)
    add("")
    add(OPENING_NUMBER_IS_NOT_A_BET)
    add("")
    add(LIMITS_ARE_NOT_OBSERVABLE)
    add("")

    looks = int(record.get("looks", 1))
    add(
        f"**Family correction: {looks:,} cumulative hypotheses** in the "
        f"experiment ledger, widening every 95% interval by "
        f"x{record.get('correction_factor', 1.0):.2f}. That is the ledger's "
        "cumulative count and never the day's."
    )
    add("")
    add(
        f"**Below {record.get('minimum_bets', S.MINIMUM_BETS):,} bets there is "
        f"no number**, only the words *{NOT_ENOUGH_EVIDENCE}*. That floor was "
        "declared before any price was captured."
    )
    add("")

    lines.extend(_instrument_section(record))
    lines.extend(_split_section(record))
    lines.extend(_opening_section(record))
    lines.extend(_cannot_say_section())
    return "\n".join(lines).rstrip() + "\n"


def _instrument_section(record: Mapping) -> list[str]:
    lines = ["## The instrument", ""]
    add = lines.append
    store = dict(record.get("store") or {})
    add(
        "`line_movement.py` is the instrument and this report does not "
        "reimplement it. Every survival judgment below is produced by calling "
        "`line_movement.survival_between`, which is captured four times a day "
        "on a cron and is append-only, because a price that existed at 19:04 "
        "and not at 19:19 leaves no trace anywhere else and no amount of money "
        "buys it back."
    )
    add("")
    if store.get("captures"):
        add(
            f"**{_plural(int(store.get('quotes', 0)), 'quote')} across "
            f"{_plural(int(store.get('captures', 0)), 'capture')}**, "
            f"{store.get('first_capture')} to {store.get('last_capture')}, over "
            f"{_plural(int(store.get('events', 0)), 'event')}, "
            f"{_plural(int(store.get('books', 0)), 'book')} and "
            f"{_plural(int(store.get('slate_days', 0)), 'slate day')}. "
            f"{store.get('judged_quotes', 0):,} of those quotes could be judged "
            "against a later capture."
        )
    else:
        add(
            "**The store holds no capture at all**, so there is no timestamp "
            "range, no book count and no survival to report from it."
        )
    add("")
    if not store.get("enough_evidence"):
        add(f"**{NOT_ENOUGH_EVIDENCE.capitalize()}.** {store.get('reason', '')}")
        add("")
        add(
            "So no board-level survival rate is printed. It is said in words "
            "rather than shown as an empty table, because an empty table reads "
            "as a null result and a null result is a claim."
        )
        add("")
        return lines

    add("### Survival between consecutive captures")
    add("")
    add("| From | To | Judged | Survived | Gone | Unjudgeable |")
    add("|:---|:---|---:|---:|---:|---:|")
    for row in record.get("capture_pairs") or []:
        add(
            f"| {row['earlier']} | {row['later']} | {row['judged']:,} | "
            f"{_rate(row['survival_rate'])} | {row['gone']:,} | "
            f"{row['unknown']:,} |"
        )
    add("")
    add(
        "**Unjudgeable is not gone.** A quote in an event the later capture "
        "did not cover says nothing about whether the book pulled the price. "
        "Scoring those as gone would manufacture a reachability finding out of "
        "a coverage gap, and this report keeps them in a third column all the "
        "way through rather than folding them into either answer."
    )
    add("")

    tier_rows = record.get("board_by_tier") or []
    if tier_rows:
        add("### Survival per conference tier")
        add("")
        add(
            "This is the half of the thesis that is easy to forget. If the "
            "low-major rate here is materially below the high-major rate, the "
            "looser board is also the faster one, and any low-major return "
            "below has to be read against it."
        )
        add("")
        add("| Tier | Quotes | Judged | Survived | Gone | Unjudgeable |")
        add("|:---|---:|---:|---:|---:|---:|")
        for row in tier_rows:
            add(
                f"| {row['tier']} | {row['quotes']:,} | {row['judged']:,} | "
                f"{_rate(row['survival_rate'])} | {row['gone']:,} | "
                f"{row['unknown']:,} |"
            )
        add("")
        if any(row["tier"] == UNTIERED for row in tier_rows):
            add(
                f"A quote under `{UNTIERED}` is one whose event no supplied bet "
                "placed in a tier. It is reported rather than dropped or "
                "guessed: a quote whose tier nobody supplied is not a "
                "low-major quote."
            )
            add("")

    book_rows = record.get("by_book") or []
    if book_rows:
        add("### Survival per book")
        add("")
        add(REGIONS_CAVEAT)
        add("")
        add("| Book | Quotes | Judged | Survived | Gone | Unjudgeable |")
        add("|:---|---:|---:|---:|---:|---:|")
        for row in book_rows:
            add(
                f"| {row['book']} | {row['quotes']:,} | {row['judged']:,} | "
                f"{_rate(row['survival_rate'])} | {row['gone']:,} | "
                f"{row['unknown']:,} |"
            )
        add("")
    return lines


def _split_section(record: Mapping) -> list[str]:
    lines = ["## The staked bets, split by whether the price survived", ""]
    add = lines.append
    provenance = dict(record.get("survival_provenance") or {})
    rows = record.get("by_tier_and_reachability") or []

    add(
        f"**{provenance.get('bets', 0):,} staked bets**: "
        f"{provenance.get('survived', 0):,} at a price that survived to the "
        f"next capture, {provenance.get('gone', 0):,} at a price that was gone "
        f"by it, and {provenance.get('unknown', 0):,} the instrument could not "
        f"judge. Source: `{provenance.get('source', 'none')}`."
    )
    add("")
    add(provenance.get("note", ""))
    add("")

    if not rows:
        add(
            f"**{PB.NOTHING_TO_MEASURE.capitalize()}.** No staked bet reached "
            "this report, so there is no return to split. It is said in words "
            "rather than shown as an empty table, because an empty table reads "
            "as a null result and a null result is a claim."
        )
        add("")
        return lines

    add(PB.POOLED_CAVEAT)
    add("")
    add(
        "| Tier | Reachability | Bets | Games | ROI | 95% interval | "
        "Family-corrected | Verdict |"
    )
    add("|:---|:---|---:|---:|---:|:---|:---|:---|")
    for row in rows:
        add(_roi_row(row, str(row.get("name", ""))))
    add("")

    add("### Verdicts")
    add("")
    for verdict in record.get("verdicts") or []:
        add(f"- **{verdict['tier']}** — {verdict['sentence']}")
    add("")

    market_rows = record.get("by_market_tier_and_reachability") or []
    if market_rows:
        add("### Per market, inside each tier")
        add("")
        add(
            "A tier is not one instrument. A moneyline on a low-major Tuesday "
            "and an alternate total on the same game move at different speeds, "
            "and a tier verdict that is really one market's behaviour should "
            "be visible as such."
        )
        add("")
        add(
            "| Tier | Market | Reachability | Bets | Games | ROI | "
            "95% interval | Family-corrected | Verdict |"
        )
        add("|:---|:---|:---|---:|---:|---:|:---|:---|:---|")
        for row in market_rows:
            roi, interval, corrected = PB.roi_cells(dict(row))
            add(
                f"| {row.get('tier', '')} | {row.get('market', '')} | "
                f"{row.get('name', '')} | {row.get('bets', 0):,} | "
                f"{row.get('clusters', 0):,} | {roi} | {interval} | "
                f"{corrected} | {row.get('verdict', '')} |"
            )
        add("")
    return lines


def _opening_section(record: Mapping) -> list[str]:
    lines = ["## The opening number, which is not a bet", ""]
    add = lines.append
    opening = dict(record.get("opening_number") or {})
    add(opening.get("note", OPENING_NUMBER_IS_NOT_A_BET))
    add("")
    if not opening.get("measured"):
        return lines
    add(S.ROI_TABLE_HEADER.replace("| Market |", "| Priced at |"))
    for key in ("at_first_capture", "later"):
        row = dict(opening.get(key) or {})
        if not row:
            continue
        roi, interval, corrected = PB.roi_cells(row)
        add(
            f"| {row.get('name', key)} | {row.get('bets', 0):,} | "
            f"{row.get('clusters', 0):,} | {roi} | {interval} | {corrected} | "
            f"{row.get('verdict', '')} |"
        )
    add("")
    return lines


def _cannot_say_section() -> list[str]:
    return [
        "## What this report cannot say",
        "",
        "- It cannot say a market is a play. **No market is allowlisted**, "
        "`staging_provider_policy` ships manual-only, and that is the correct "
        "state. An excluded market is never a pass, an avoid, or a no-value "
        "call.",
        "- It cannot say a surviving price would have been **filled**. "
        + LIMITS_ARE_NOT_OBSERVABLE,
        "- It cannot judge a bet the capture store never saw. A quote this "
        "instrument never held is unjudgeable, never vanished, and the third "
        "column carries that all the way through.",
        "- It cannot make an opening number into a bet. "
        + OPENING_NUMBER_IS_NOT_A_BET,
        "- It cannot measure reachability from the historical archive. The "
        "archive serves **one snapshot per event**, so a bought price has no "
        "next capture and its survival is unmeasured rather than measured and "
        "found fine. Forward captures cannot be back-dated, which is why the "
        "cron runs before the season.",
        "",
    ]


# --------------------------------------------------------------------------
# Paths and the record on disk
# --------------------------------------------------------------------------


def record_path(competition: Competition, output_dir: Path | str) -> Path:
    return Path(output_dir) / competition.output_name("reachability", ".json")


def report_path(competition: Competition, output_dir: Path | str) -> Path:
    return Path(output_dir) / competition.output_name("reachability", ".md")


def write_record(record: Mapping, path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(dict(record), indent=2, default=str) + "\n", encoding="utf-8"
    )
    return target


def read_record(path: Path | str) -> dict:
    """The record, refusing a version this module does not write.

    A stale record renders a report with holes in it and nothing looks wrong,
    which is the retention probe's rule and the reason it has a version at all.
    """
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    version = int(payload.get("record_version", 0))
    if version != RECORD_VERSION:
        raise ReachabilityError(
            f"{Path(path).name} is a version {version} record and this module "
            f"writes version {RECORD_VERSION}. Re-run the measurement rather "
            "than re-rendering a record whose shape has changed — a stale "
            "record renders a report with holes in it and nothing looks wrong."
        )
    return payload


def write_report(record: Mapping, path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(record), encoding="utf-8")
    return target
