"""Capture the board repeatedly, and record whether a price survived.

This module is the instrument that decides whether any finding in this lab is
real money, and Cooper's brief is explicit that it is not an afterthought:

> Build the **line-movement capture** in the first week of the build, not late
> [...] it is the instrument that decides whether any finding is real money,
> and it needs to be running before the season so it has history of its own.

## The question it exists to answer

A backtest can only ever say "this price, at this moment, would have won". It
cannot say whether the price was still there when a human reached for it. In
this sport that gap is the whole argument: the plausible edge lives in
low-major games, and low-major games have the smallest limits and the fastest
moves. **A soft number you cannot bet is not an edge.**

So every capture writes the board as it stood, and every capture *after the
first* answers a question about the one before it: is that exact quote — same
event, market, player, selection, line, book, price — still on the board?

## Survival is a property of a quote, not of a market

`selection_key()` builds the identity, and the price is part of it. A book that
moved a total from 142.5 to 143 has not "kept" the 142.5 quote; it has removed
it. That is the honest reading, because the 142.5 is what a backtest would have
staked and it is precisely what is no longer available.

Three outcomes, and the third is why `UNKNOWN` exists rather than a default:

- `SURVIVED` — the quote was in the next capture.
- `GONE` — the next capture covered this event and this market, and the quote
  was not in it.
- `UNKNOWN` — the next capture did not cover this event and market at all, so
  nothing can be said. A fetch that skipped an event is not a book that pulled
  a price, and scoring it as `GONE` would manufacture a reachability finding
  out of a coverage gap. This is the same failure mode as *"a starved fetch and
  an unquoted market look identical"*, one layer down.

## Why its own store and its own branch

The captures are evidence that cannot be rebuilt. A price that existed at
19:04 and not at 19:19 leaves no trace anywhere else, and no amount of money
buys it back afterwards — the historical archive serves one snapshot per event,
not the minute-by-minute board.

So the store is append-only, deduped on price identity (never on the whole row,
which is how the NHL lab wrote every quote twice and narrowed every interval by
root two), and published to a ref of its own rather than to `card-feed` — a
capture must never be able to overwrite a card, and a card must never be able
to overwrite a capture.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from cbb_betting_lab import stores
from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.season import clean_text, slate_date

#: One capture's worth of the board. `captured_at` is the identity of the
#: capture, not of the quote — two books quoting the same price are two rows,
#: and the same book quoting it twice in one capture is one.
CAPTURE_COLUMNS: tuple[str, ...] = (
    "captured_at",
    "slate_date",
    "event_id",
    "commence_time",
    "home_team",
    "away_team",
    "market",
    "segment",
    "player",
    "selection",
    "line",
    "book",
    "american_odds",
)

#: What makes two rows the same quote. The price is IN the identity: a book
#: that moved its number has removed the old quote, and that is the honest
#: reading because the old number is what a backtest would have staked.
QUOTE_IDENTITY: tuple[str, ...] = (
    "event_id",
    "market",
    "segment",
    "player",
    "selection",
    "line",
    "book",
    "american_odds",
)

SURVIVED = "survived"
GONE = "gone"
UNKNOWN = "unknown"


@dataclass(frozen=True)
class Survival:
    """What became of one capture's quotes at the next capture."""

    earlier: str
    later: str
    survived: int = 0
    gone: int = 0
    unknown: int = 0

    @property
    def judged(self) -> int:
        """Quotes the later capture could actually speak to."""
        return self.survived + self.gone

    @property
    def survival_rate(self) -> float | None:
        """None rather than 0.0 when nothing could be judged.

        A rate over an empty denominator is not zero, and reporting it as zero
        would say "every price vanished" about a capture that simply did not
        run.
        """
        return (self.survived / self.judged) if self.judged else None

    def line(self) -> str:
        if self.survival_rate is None:
            return (
                f"{self.earlier} -> {self.later}: nothing could be judged. "
                f"{self.unknown:,} quotes were in events the later capture did "
                "not cover, which is a coverage gap and not a market that moved."
            )
        return (
            f"{self.earlier} -> {self.later}: "
            f"**{self.survival_rate:.1%}** of {self.judged:,} judged quotes "
            f"survived ({self.gone:,} gone). {self.unknown:,} unjudgeable."
        )


def stage_board(
    payloads: Iterable[Mapping] | Mapping,
    *,
    captured_at: str,
    competition: Competition = CBB,
) -> pd.DataFrame:
    """Flatten the provider's board into this lab's vocabulary and stamp it.

    THE STAGING ITSELF IS NOT DONE HERE. `providers.staging.stage_payloads` is
    the one place a provider payload becomes a row in this lab's vocabulary,
    and this function calls it rather than reimplementing it.

    The first draft of this module did reimplement it — a second loop over
    bookmakers and outcomes, resolving selections its own way. That is the
    NHL lab's join-vocabulary bug family being invited back in through the
    front door: two staging paths are two vocabularies, and two spellings of
    one bet become two keys that never join. The capture store and the card
    must agree about what a row *is*, or survival is measured against
    something the card never staked.

    All this adds is `captured_at`, which is the identity of the capture rather
    than of the quote.
    """
    from cbb_betting_lab.providers import staging

    frame, _counts = staging.stage_payloads(payloads, competition=competition)
    if frame.empty:
        return pd.DataFrame(columns=list(CAPTURE_COLUMNS))
    frame = frame.copy()
    frame["captured_at"] = str(captured_at)
    missing = [c for c in CAPTURE_COLUMNS if c not in frame.columns]
    if missing:
        raise KeyError(
            f"The staged board is missing {missing}. `stage_payloads` and "
            "`CAPTURE_COLUMNS` have drifted apart, and a capture written from "
            "a different shape than the card stages cannot be joined to it."
        )
    return frame[list(CAPTURE_COLUMNS)]


def append_capture(frame: pd.DataFrame, path: Path | str) -> int:
    """Append a capture, deduped on price identity within the capture.

    Deduped on the QUOTE plus its capture, never on the whole row. The NHL
    lab's store deduped on rows including timestamps, so every price was
    written twice; ROI was unchanged and every interval was root-two too
    narrow. **A duplicated store does not look wrong — it looks significant.**
    """
    return stores.append(
        frame,
        Path(path),
        columns=CAPTURE_COLUMNS,
        dedupe_on=("captured_at", *QUOTE_IDENTITY),
    )


def survival_between(
    earlier: pd.DataFrame, later: pd.DataFrame
) -> Survival:
    """What became of `earlier`'s quotes by the time of `later`."""
    stamp_a = str(earlier["captured_at"].iloc[0]) if not earlier.empty else ""
    stamp_b = str(later["captured_at"].iloc[0]) if not later.empty else ""
    if earlier.empty:
        return Survival(earlier=stamp_a, later=stamp_b)

    # What the later capture COVERED, at (event, market) resolution. A quote
    # in an event/market the later capture never fetched is unjudgeable, and
    # calling it gone would turn a coverage gap into a reachability finding.
    covered = set(
        map(tuple, later[["event_id", "market"]].drop_duplicates().to_numpy())
    ) if not later.empty else set()
    present = set(
        map(tuple, later[list(QUOTE_IDENTITY)].to_numpy())
    ) if not later.empty else set()

    survived = gone = unknown = 0
    for row in earlier[list(QUOTE_IDENTITY)].itertuples(index=False, name=None):
        if (row[0], row[1]) not in covered:
            unknown += 1
        elif row in present:
            survived += 1
        else:
            gone += 1
    return Survival(
        earlier=stamp_a, later=stamp_b,
        survived=survived, gone=gone, unknown=unknown,
    )


def survival_series(store: pd.DataFrame) -> list[Survival]:
    """Survival for every consecutive pair of captures in the store."""
    if store.empty or "captured_at" not in store:
        return []
    stamps = sorted(str(s) for s in store["captured_at"].dropna().unique())
    out: list[Survival] = []
    for earlier, later in zip(stamps, stamps[1:]):
        out.append(
            survival_between(
                store[store["captured_at"].astype(str) == earlier],
                store[store["captured_at"].astype(str) == later],
            )
        )
    return out


def render(store: pd.DataFrame, *, competition: Competition = CBB) -> str:
    lines: list[str] = []
    add = lines.append
    add(f"# Line movement — {competition.title}")
    add("")
    add(
        "**What this measures is reachability, not edge.** A backtest can say "
        "that a price would have won. Only this can say whether the price was "
        "still there when a human reached for it. In this sport that gap is "
        "the whole argument: the plausible edge lives in low-major games, and "
        "low-major games have the smallest limits and the fastest moves."
    )
    add("")
    if store.empty:
        add(
            "**No capture has run yet.** That is a true statement about a "
            "fresh clone and about a lab whose season has not started. It is "
            "not a fault, and it is not a market with no movement."
        )
        return "\n".join(lines) + "\n"

    stamps = sorted(str(s) for s in store["captured_at"].dropna().unique())
    add(
        f"**{len(store):,} quotes across {len(stamps)} captures**, "
        f"{stamps[0]} to {stamps[-1]}, over "
        f"{store['event_id'].nunique():,} events and "
        f"{store['book'].nunique()} books."
    )
    add("")
    series = survival_series(store)
    if not series:
        add(
            "Only one capture exists, so **nothing can be said about survival "
            "yet**. Survival is a statement about a quote at the *next* "
            "capture, and there has not been one."
        )
        return "\n".join(lines) + "\n"

    add("| From | To | Judged | Survived | Gone | Unjudgeable |")
    add("|:---|:---|---:|---:|---:|---:|")
    for s in series:
        rate = "—" if s.survival_rate is None else f"{s.survival_rate:.1%}"
        add(
            f"| {s.earlier} | {s.later} | {s.judged:,} | {rate} | "
            f"{s.gone:,} | {s.unknown:,} |"
        )
    add("")
    add(
        "**Unjudgeable is not gone.** A quote in an event the later capture "
        "did not cover says nothing about whether the book pulled the price. "
        "Scoring those as gone would manufacture a reachability finding out of "
        "a coverage gap — the same failure as reading a starved fetch as an "
        "unquoted market, one layer down."
    )
    return "\n".join(lines) + "\n"


def store_path(competition: Competition, processed_dir: Path | str) -> Path:
    return Path(processed_dir) / competition.output_name("line_movement", ".csv")
