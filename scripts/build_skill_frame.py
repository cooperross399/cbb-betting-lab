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
excluded, **counted, named, and reconciled**: `supplied = paired + unpairable`,
printed in the same shape as the price backtest's accounting identity (see
`OpinionAccounting` in `scripts/run_price_backtest.py`) and written to a JSON
record beside the frame, so `forecast_skill` and any later reader can state
the population from a count rather than from the frame's length.

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
    """Counts by one column, as plain data. Absent column, empty tally."""
    if column not in frame.columns or frame.empty:
        return {}
    counts = frame[column].astype(str).fillna("").value_counts()
    return {str(key): int(value) for key, value in counts.items()}


@dataclass
class UnpairableCensus:
    """`supplied = paired + unpairable`, reconciled, and the excluded rows named.

    Modelled on `run_price_backtest.OpinionAccounting`, and for the same
    reason: a measurement that silently lost rows still prints an interval, and
    the interval looks exactly like one that did not. **Both terms are counted
    from the graded frame and neither is the residual of the other**, so
    :meth:`reconciles` is a real comparison against `supplied` rather than an
    identity that holds by construction.
    """

    #: Graded rows handed to :func:`build`.
    supplied: int = 0
    #: Graded rows kept, each with its complement found at its own book.
    paired: int = 0
    #: Graded rows excluded: no complement at their own book in the store.
    unpairable: int = 0
    #: Of the excluded rows, how many the price backtest had marked as bets.
    #: Reported apart because a dropped **bet** is a dropped stake, and the
    #: winner's-curse comparison shrinks with it.
    unpairable_selected: int = 0
    #: Graded rows whose selection has no complement at all in
    #: `FS.COMPLEMENT` — a wager `pair_key` cannot key. These are **not**
    #: excluded here and are **not** part of the identity: they stay in the
    #: frame, and `forecast_skill.DevigCensus` counts them under
    #: `unknown_selection`, which is where a reader already looks for them.
    #: Counted here only so this script's silence about them is not mistaken
    #: for their absence.
    no_pair_key: int = 0
    by_market: dict[str, int] = field(default_factory=dict)
    by_book: dict[str, int] = field(default_factory=dict)
    by_tier: dict[str, int] = field(default_factory=dict)
    #: The excluded rows themselves, up to :data:`UNPAIRABLE_ROWS_NAMED`.
    rows: list[dict] = field(default_factory=list)
    max_share: float = MAX_UNPAIRABLE_SHARE

    @property
    def accounted(self) -> int:
        return self.paired + self.unpairable

    @property
    def reconciles(self) -> bool:
        return self.accounted == self.supplied

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
            "Unpairable census — supplied = paired + unpairable:",
            f"  graded rows supplied  {self.supplied:,}",
            f"  paired                {self.paired:,}",
            f"  unpairable            {self.unpairable:,}",
            f"  reconciles            {'yes' if self.reconciles else 'NO'} "
            f"({self.accounted:,} accounted of {self.supplied:,} supplied)",
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
                f"  {self.no_pair_key:,} graded row(s) carry a selection with no "
                "complement at all; they are kept here and counted by "
                "forecast_skill's de-vig census as `unknown_selection`."
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
    and where they came from, and `supplied = paired + unpairable` reconciles
    over the frame handed in — so a caller can state the population from a
    count instead of from the length of what came back.
    """
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
    comp = comp.drop_duplicates(subset=["_pk", "book", "selection"], keep="first")

    found = set(zip(comp["_pk"], comp["book"], comp["selection"]))
    # One row lands in exactly one of the two buckets, and each is counted off
    # the frame rather than derived from the other. `len(need - found)` — what
    # this script counted until 2026-09-05 — counts missing *keys*, and two
    # graded rows can want the same key, so it was never a count of rows.
    unpairable_mask = pd.Series(
        [key is not None and key not in found for key in wanted], index=graded.index
    )
    keyless_mask = pd.Series([key is None for key in wanted], index=graded.index)
    excluded = graded[unpairable_mask]

    census = UnpairableCensus(
        supplied=int(len(graded)),
        paired=int(len(graded) - len(excluded)),
        unpairable=int(len(excluded)),
        no_pair_key=int(keyless_mask.sum()),
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

    kept = graded[~unpairable_mask]
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

    if not census.reconciles:
        print(
            f"::error::The unpairable census does not reconcile: "
            f"{census.paired:,} paired plus {census.unpairable:,} unpairable is "
            f"not the {census.supplied:,} graded rows supplied. A row that "
            "reached neither bucket has vanished from the measurement, and the "
            "regression would still print an interval. Nothing was written.",
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
    complements = len(frame) - census.paired
    print(
        f"Wrote {out_path.name}: {len(frame):,} rows = {census.paired:,} scorable + "
        f"{complements:,} complement-only, with {census.unpairable:,} graded row(s) "
        f"excluded as unpairable. No request was made and no credit was spent."
    )
    print(
        f"Wrote {record_path.name}: the census, so a reader can state the "
        "population from a count rather than from the frame's length."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
