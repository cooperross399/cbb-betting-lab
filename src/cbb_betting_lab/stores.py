"""Reading and writing the accumulated tables, with the guards that were paid for.

Three rules live here, each of which cost a sibling lab something real.

## 1. Dedupe on price identity, never on the whole row

**A duplicated store does not look wrong. It looks significant.**

The NHL lab's purchase deduplicated on the whole row, timestamps included, so
two buys of the same window wrote every quote twice under two snapshot labels.
ROI is unchanged by exact duplication — and the interval narrows by root two.
Its first "clean" run reported 144,060 bets and an interval half again too
tight, and nothing about the output looked broken.

`dedupe_prices` keys on the **quote** — event, market, segment, player,
selection, line, book, snapshot phase — and never on when it was fetched.

## 2. One wager is one bet, at the best price

The NHL lab's backtest counted every book's quote on the same selection as an
independent bet: 2.83 quotes on average, so every interval was about √2.83 too
narrow, and it measured a strategy nobody would run — every book at its average
price rather than the one best price the card actually takes. Run per quote,
its full store said all three team markets were demonstrated losses; run per
wager, all three span zero. **Twenty-one books quoting one game is not
twenty-one bets.**

`best_price_per_wager` collapses to one row per wager at the best available
price. That is optimistically biased in the other direction — the best price is
the likeliest to be stale — so the two bracket the truth rather than one
replacing the other, and reports state which they used.

## 3. Never mix snapshot windows in one measurement

Each cached price carries the snapshot it came from. Without that, the
best-price collapse takes the better of a card-time price and a closing price
for one wager — a price nobody could have taken, which inflates every measured
edge. `assert_single_window` raises rather than warns.

## 4. A store never shrinks by accident

`read_store(..., for_append=True)` raises on a parse error rather than
returning an empty frame, because writing then would replace a damaged file
with a shorter one. And `append` refuses to write fewer rows than it read.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


class CorruptStoreError(RuntimeError):
    """A store could not be read, and the caller was about to overwrite it."""


#: What makes two rows the same quote. **No timestamp.** Adding one here
#: re-introduces the NHL lab's √2 interval defect, and nothing about the output
#: will look wrong.
PRICE_IDENTITY = (
    "event_id",
    "market",
    "segment",
    "player",
    "selection",
    "line",
    "book",
    "snapshot_phase",
)


def read_store(
    path: Path, *, columns: tuple[str, ...] | None = None, for_append: bool = False
) -> pd.DataFrame:
    """Read a CSV store defensively.

    `for_append=True` **raises** on an unreadable file instead of returning an
    empty frame. The distinction matters: a caller that is about to append and
    silently reads nothing writes a short file over a damaged long one, and the
    damage becomes permanent.
    """
    target = Path(path)
    if not target.is_file():
        return pd.DataFrame(columns=list(columns) if columns else None)
    try:
        frame = pd.read_csv(target)
    except (OSError, UnicodeError, pd.errors.ParserError, pd.errors.EmptyDataError) as exc:
        if for_append:
            raise CorruptStoreError(
                f"{target} could not be read, and this caller was about to "
                "append to it. Refusing: writing now replaces a damaged file "
                "with a shorter one, and that damage is permanent."
            ) from exc
        return pd.DataFrame(columns=list(columns) if columns else None)
    if columns:
        for column in columns:
            if column not in frame.columns:
                frame[column] = pd.NA
        frame = frame[list(columns)]
    return frame


def dedupe_prices(frame: pd.DataFrame) -> pd.DataFrame:
    """One row per quote. Keyed on the quote, never on when it was fetched.

    See the module docstring. This is the single most important function in
    this file and the one whose failure is hardest to see.
    """
    if frame.empty:
        return frame
    key = [column for column in PRICE_IDENTITY if column in frame.columns]
    if not key:
        raise ValueError(
            "A price frame carries none of the identity columns "
            f"{PRICE_IDENTITY}. Deduplicating on the whole row is how a store "
            "silently doubles and every interval narrows by root two."
        )
    return frame.drop_duplicates(subset=key, keep="first").reset_index(drop=True)


def best_price_per_wager(
    frame: pd.DataFrame, *, odds_column: str = "american_odds"
) -> pd.DataFrame:
    """Collapse every book's quote on one wager to the single best price.

    A wager is the quote identity **minus the book**: the same selection at the
    same line on the same event is one bet, however many books hang it.
    """
    if frame.empty:
        return frame
    wager = [
        column
        for column in PRICE_IDENTITY
        if column != "book" and column in frame.columns
    ]
    if not wager or odds_column not in frame.columns:
        return frame
    ordered = frame.assign(
        _payout=frame[odds_column].map(_decimal_payout)
    ).sort_values("_payout", ascending=False, kind="mergesort")
    return (
        ordered.drop_duplicates(subset=wager, keep="first")
        .drop(columns=["_payout"])
        .reset_index(drop=True)
    )


def _decimal_payout(american: object) -> float:
    """Profit per unit staked. The ordering key for 'best price'.

    American odds do not sort numerically: +150 beats -110 beats -200, and a
    naive sort puts -200 above +150. This is the conversion that makes 'best'
    mean best.
    """
    try:
        odds = float(american)
    except (TypeError, ValueError):
        return float("-inf")
    if odds != odds:  # NaN
        return float("-inf")
    if odds > 0:
        return odds / 100.0
    if odds < 0:
        return 100.0 / -odds
    return float("-inf")


def assert_single_window(frame: pd.DataFrame, *, column: str = "snapshot_phase") -> str:
    """Raise if a frame holds more than one snapshot window.

    The first version of this guard in the NHL lab hardcoded a window that
    matched nothing and fell through silently, measuring the mixture it was
    written to prevent. This one derives the answer from the data and raises.
    """
    if frame.empty or column not in frame.columns:
        return ""
    windows = sorted(str(w) for w in frame[column].dropna().unique())
    if len(windows) > 1:
        raise ValueError(
            f"This store holds {len(windows)} snapshot windows ({windows}). "
            "Measuring them as one takes the better of a card-time price and a "
            "closing price for the same wager — a price nobody could have "
            "taken, which inflates every measured edge. Filter to one window."
        )
    return windows[0] if windows else ""


def _dedupe_value(value: object) -> str:
    """One spelling for the purposes of identity.

    NaN, None and the empty string are the same absent value; 142.5 and
    "142.5" are the same line. Both collapses are needed because a store is
    compared against itself across a CSV round-trip, which preserves neither.
    """
    if value is None:
        return ""
    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    # "142.50" and "142.5" are one line; "nan" is the string a careless
    # `str(x or "")` produces from a NaN and must never be an identity.
    if text.lower() in {"nan", "none", "<na>"}:
        return ""
    try:
        number = float(text)
    except ValueError:
        return text
    return str(int(number)) if number.is_integer() else repr(number)


def append(
    frame: pd.DataFrame,
    path: Path,
    *,
    columns: tuple[str, ...],
    dedupe_on: tuple[str, ...] | None = None,
    allow_shrink: bool = False,
) -> int:
    """Append to a store, refusing to shrink it. Returns the new row count."""
    target = Path(path)
    existing = read_store(target, columns=columns, for_append=True)
    before = len(existing)
    combined = pd.concat([existing, frame[list(columns)]], ignore_index=True)
    if dedupe_on:
        key = [c for c in dedupe_on if c in combined.columns]
        if key:
            # NORMALISE THE KEY ON BOTH SIDES BEFORE COMPARING IT.
            #
            # This is the fifth member of the NHL lab's join-vocabulary bug
            # family, and it arrived here exactly as it did there: a CSV
            # round-trip turns an empty `player` into NaN, so the row already
            # on disk and the identical row about to be written compare
            # UNEQUAL, and every re-run appends a second copy of every quote.
            #
            # ROI is unchanged by exact duplication and the interval narrows by
            # root two. **A duplicated store does not look wrong — it looks
            # significant.** So the comparison is made on normalised values
            # rather than on whatever pandas happened to reconstruct.
            #
            # Only the key is normalised, never the stored data: the file keeps
            # what it was given.
            normalised = combined[key].map(_dedupe_value)
            combined = combined[~normalised.duplicated(keep="first")]
    if len(combined) < before and not allow_shrink:
        raise ValueError(
            f"Refusing to write {len(combined):,} rows over a store holding "
            f"{before:,}. This store is append-only and cannot be rebuilt — "
            "the prices it settled against are gone. Something upstream lost "
            "rows."
        )
    target.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(target, index=False, lineterminator="\n")
    return len(combined)
