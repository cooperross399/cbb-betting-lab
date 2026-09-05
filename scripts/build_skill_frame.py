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

**It refuses to write if any graded bet lacks its complement.** A missing
complement would land that bet under no pair, silently excluded from the
de-vig — and the excluded rows would not be a random sample, because a book
that hangs only one side of a wager is a book doing something unusual with it.

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
import sys
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


def build(graded: pd.DataFrame, store: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Graded bets plus one complement row each. Returns (frame, missing)."""
    store = stores.dedupe_prices(store)
    store = store.assign(_pk=[FS.pair_key(r) for r in store.to_dict("records")])
    graded = graded.assign(_pk=[FS.pair_key(r) for r in graded.to_dict("records")])

    need = {
        (pk, bk, FS.COMPLEMENT[sel])
        for pk, bk, sel in zip(graded["_pk"], graded["book"], graded["selection"])
        if pk is not None and sel in FS.COMPLEMENT
    }
    keys = list(zip(store["_pk"], store["book"], store["selection"]))
    comp = store[pd.Series([k in need for k in keys], index=store.index)]
    comp = comp.drop_duplicates(subset=["_pk", "book", "selection"], keep="first")

    found = set(zip(comp["_pk"], comp["book"], comp["selection"]))
    missing = len(need - found)

    # Complement rows exist only to complete the pair: no opinion, no outcome,
    # so they are unscorable by construction. They supply the hold; they are
    # not bets, and the flag says so rather than being left blank.
    comp = comp.reindex(columns=[c for c in graded.columns if c != "_pk"])
    comp["model_probability"] = np.nan
    comp["outcome"] = ""
    comp[FS.SELECTED_COLUMN] = False
    frame = pd.concat([graded.drop(columns=["_pk"]), comp], ignore_index=True)
    return frame, missing


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

    frame, missing = build(graded, store)
    if missing:
        print(
            f"::error::{missing:,} graded bet(s) have no complement at their own "
            "book in the store. Refusing to write: those bets would be silently "
            "excluded from the de-vig, and a book hanging one side of a wager is "
            "not a random sample of books.",
            file=sys.stderr,
        )
        return 1
    frame.to_csv(out_path, index=False)
    complements = len(frame) - len(graded)
    print(
        f"Wrote {out_path.name}: {len(frame):,} rows = {len(graded):,} scorable + "
        f"{complements:,} complement-only. No request was made and no credit was spent."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
