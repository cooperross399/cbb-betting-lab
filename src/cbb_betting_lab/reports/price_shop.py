"""Price shopping: a book's price that beats the market's own fair price.

Cooper, 2026-11-09 (*"How can this improve more. I want results and
profits"*), ideas 1 and 2 of the reply (decision 91).

The card prices a game with the model. This report does not use the model at
all. It reads each line-movement capture, takes the **fair price** of every
main-market pair the way the trust table does (the median over books of each
book's own de-vigged two-sided quote, `trust.MIN_FAIR_BOOKS` books or more,
`models/trust.py`), and lists every side where the best book's price is worth
at least `SHOP_EDGE` more than that fair price: `fair x decimal - 1`. A book
that is slow to move is the oldest edge there is, and it needs no opinion
about the game.

Week one says why it is worth a look and not yet a claim: over the first
captures of the season, a 2% shop against the all-book median closed better
than it was taken on about three bets in five, by about 3% of the stake,
over 42 sides; the interval spans zero. Captures were four a day, so most
shops were never seen. The capture now runs hourly through the slate
(`.github/workflows/line-movement.yml`), and this report runs after each one.

**Closing-line value** (idea 2) grades each side the first time it was a
shop: the fair price of the same side **at the same line** at the last
capture at or before tip that quotes that line with enough books, times the
shop's decimal price, minus one. Positive means the price was better than
where the market closed. A spread or total whose line moved so far that no
book quoted it at the close is ungraded rather than guessed, and the count
of those is printed, because the moves that strand a line are the moves
closing-line value is about.

Graded per tier and never pooled (a tier comes from the forward ledger's own
`tier` for the event; an event the ledger never froze is `unplaced`, shown
apart). Intervals are clustered by game and corrected at the experiment
ledger's cumulative count. Registered as `price_shop_2026_11_09`, one per
tier. Closing-line value is not a return, and it never selects, stakes or
withdraws anything: this report is advice the card does not read.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

from cbb_betting_lab import stats as S
from cbb_betting_lab.models.trust import MIN_FAIR_BOOKS
from cbb_betting_lab.reports.card_pricing import PRICE_BAND

#: The least a book's price must beat the fair price by to be listed: the
#: card's own edge bar, so a shop and a pick clear the same height.
SHOP_EDGE = 0.02

#: The main markets the capture holds, by their allowlist names.
MARKETS = ("moneyline", "spread", "total_points")
TIERS = ("high_major", "mid_major", "low_major")
UNPLACED = "unplaced"
FULL_GAME = ("game", "full_game")

#: A share of the graded sides below which a tier's cell carries no interval.
MIN_GRADED = 30

JSON_NAME = "cbb_price_shop.json"
MD_NAME = "cbb_price_shop.md"


def _decimal(american: pd.Series) -> pd.Series:
    a = pd.to_numeric(american, errors="coerce")
    out = pd.Series(np.nan, index=a.index, dtype=float)
    plus = a >= 100
    minus = a <= -100
    out[plus] = 1.0 + a[plus] / 100.0
    out[minus] = 1.0 + 100.0 / (-a[minus])
    return out


def fair_board(store: pd.DataFrame | None, *, min_books: int = MIN_FAIR_BOOKS) -> pd.DataFrame:
    """One row per capture, event, main market, line and side, before tip.

    `pair_line` is the line the two sides share: the home line on a spread
    (the away side's line negated), the total on a total, and 0 on a
    moneyline. `fair` is the median of the books' own de-vigged quotes, over
    books quoting both sides; a pair with fewer than `min_books` such books
    has no fair price and no row. `best_*` is the best price any book quoted
    on that side in that capture."""
    columns = ["captured_at", "event_id", "commence", "home_team", "away_team", "market",
               "pair_line", "line", "selection", "fair", "books", "best_decimal",
               "best_american", "best_book"]
    if store is None or store.empty:
        return pd.DataFrame(columns=columns)
    frame = store.copy()
    frame = frame[frame["market"].astype(str).isin(MARKETS)]
    frame = frame[frame["segment"].astype(str).isin(FULL_GAME)]
    if "player" in frame.columns:
        frame = frame[frame["player"].fillna("").astype(str).str.strip() == ""]
    frame["captured_at"] = pd.to_datetime(frame["captured_at"], utc=True, errors="coerce")
    frame["commence"] = pd.to_datetime(frame["commence_time"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["captured_at", "commence"])
    frame = frame[frame["captured_at"] < frame["commence"]]
    frame["decimal"] = _decimal(frame["american_odds"])
    frame = frame.dropna(subset=["decimal"])
    if frame.empty:
        return pd.DataFrame(columns=columns)
    line = pd.to_numeric(frame["line"], errors="coerce")
    frame["line"] = line
    pair = line.where(~((frame["market"] == "spread") & (frame["selection"] == "away")), -line)
    frame["pair_line"] = pair.where(frame["market"] != "moneyline", 0.0).fillna(0.0)
    frame["event_id"] = frame["event_id"].astype(str)
    frame["book"] = frame["book"].astype(str)
    frame["selection"] = frame["selection"].astype(str)
    frame["first_side"] = frame["selection"].isin(("home", "over"))
    frame = frame[frame["first_side"] | frame["selection"].isin(("away", "under"))]
    keys = ["captured_at", "event_id", "market", "pair_line"]
    # Each book's own two-sided quote, de-vigged; then the median over books.
    per_book = (
        frame.assign(implied=1.0 / frame["decimal"])
        .groupby(keys + ["book", "first_side"])["implied"].first()
        .unstack("first_side")
    )
    if True not in per_book.columns or False not in per_book.columns:
        return pd.DataFrame(columns=columns)
    per_book = per_book.dropna(subset=[True, False])
    per_book["devig"] = per_book[True] / (per_book[True] + per_book[False])
    fair = per_book.groupby(level=keys)["devig"].agg(["median", "size"])
    fair = fair[fair["size"] >= min_books].rename(columns={"median": "fair_first", "size": "books"})
    if fair.empty:
        return pd.DataFrame(columns=columns)
    best = frame.loc[frame.groupby(keys + ["selection"])["decimal"].idxmax()]
    out = best.merge(fair.reset_index(), on=keys, how="inner")
    out["fair"] = out["fair_first"].where(out["first_side"], 1.0 - out["fair_first"])
    out = out.rename(columns={"decimal": "best_decimal", "book": "best_book"})
    out["best_american"] = pd.to_numeric(out["american_odds"], errors="coerce")
    out["books"] = out["books"].astype(int)
    return out[columns].reset_index(drop=True)


def shops(board: pd.DataFrame, *, allowlisted: Iterable[str] | None = None,
          edge: float = SHOP_EDGE) -> pd.DataFrame:
    """The board's sides whose best price beats the fair price by `edge`,
    inside the card's price band and, when `allowlisted` is given, on an
    allowlisted market only."""
    if board.empty:
        return board.assign(shop_edge=pd.Series(dtype=float))
    out = board.assign(shop_edge=board["fair"] * board["best_decimal"] - 1.0)
    out = out[out["shop_edge"] >= edge]
    out = out[out["best_american"].between(PRICE_BAND[0], PRICE_BAND[1])]
    if allowlisted is not None:
        out = out[out["market"].isin(set(allowlisted))]
    return out.reset_index(drop=True)


def latest(board: pd.DataFrame, shop_rows: pd.DataFrame) -> tuple[str | None, pd.DataFrame]:
    """The newest capture's stamp and its shops, best first."""
    if board.empty:
        return None, shop_rows.iloc[0:0]
    newest = board["captured_at"].max()
    mine = shop_rows[shop_rows["captured_at"] == newest]
    return newest.isoformat(), mine.sort_values(["commence", "shop_edge"], ascending=[True, False])


def graded(board: pd.DataFrame, shop_rows: pd.DataFrame, *, now=None) -> pd.DataFrame:
    """Each side's FIRST shop, with its closing-line value where the close
    quoted the same line. Only games that have tipped are graded."""
    if shop_rows.empty:
        return shop_rows.assign(close_fair=pd.Series(dtype=float), clv=pd.Series(dtype=float))
    now = pd.Timestamp.now(tz="UTC") if now is None else pd.Timestamp(now)
    side = ["event_id", "market", "pair_line", "selection"]
    first = shop_rows.sort_values("captured_at").groupby(side, as_index=False).head(1)
    first = first[first["commence"] <= now]
    close = board.sort_values("captured_at").groupby(side, as_index=False).tail(1)
    close = close.rename(columns={"fair": "close_fair", "captured_at": "closed_at"})[side + ["close_fair", "closed_at"]]
    final = board.groupby("event_id")["captured_at"].max().rename("final_capture")
    out = first.merge(close, on=side, how="left").merge(final, on="event_id", how="left")
    # The close is the event's LAST capture before tip. A line that capture no
    # longer quotes with enough books has no closing price and stays ungraded;
    # a shop taken in that last capture has nothing after it to be graded by.
    stale = (out["closed_at"] != out["final_capture"]) | (out["closed_at"] <= out["captured_at"])
    out.loc[stale, "close_fair"] = np.nan
    out["clv"] = out["close_fair"] * out["best_decimal"] - 1.0
    return out.reset_index(drop=True)


def _cell(rows: pd.DataFrame, *, tier: str, looks: int) -> dict:
    done = rows.dropna(subset=["clv"])
    cell = {"tier": tier, "shops": int(len(rows)), "graded": int(len(done)),
            "ungraded": int(len(rows) - len(done)),
            "games": int(done["event_id"].nunique()) if len(done) else 0,
            "mean": None, "low": None, "high": None, "beat_close": None}
    if len(done) < MIN_GRADED:
        if len(done):
            cell["mean"] = float(done["clv"].mean())
            cell["beat_close"] = float((done["clv"] > 0).mean())
        return cell
    per_game = done.groupby("event_id").agg(profit=("clv", "sum"), bets=("clv", "size")).reset_index()
    interval = S.interval_by_cluster(per_game, looks=looks)
    cell.update(mean=float(interval.roi), low=float(interval.adjusted_low),
                high=float(interval.adjusted_high), beat_close=float((done["clv"] > 0).mean()))
    return cell


def build_record(store: pd.DataFrame | None, *, tiers: Mapping[str, str] | None, looks: int,
                 as_of: str, allowlisted: Iterable[str] | None = None, now=None) -> dict:
    board = fair_board(store)
    found = shops(board, allowlisted=allowlisted)
    stamp, current = latest(board, found)
    grades = graded(board, found, now=now)
    tiers = dict(tiers or {})
    if not grades.empty:
        grades["tier"] = grades["event_id"].map(lambda e: tiers.get(str(e), UNPLACED))
    cells = [_cell(grades[grades["tier"] == t] if not grades.empty else grades, tier=t, looks=looks)
             for t in TIERS + (UNPLACED,)]
    listing = [
        {
            "event_id": r.event_id, "commence": r.commence.isoformat(),
            "game": f"{r.away_team} at {r.home_team}", "market": r.market,
            "selection": r.selection, "line": r.line, "book": r.best_book,
            "american": int(r.best_american), "fair_american": _american(r.fair),
            "edge": round(float(r.shop_edge), 4), "books": int(r.books),
        }
        for r in current.itertuples()
    ]
    return {
        "as_of": as_of,
        "looks": int(looks),
        "correction_factor": S.bonferroni_factor(looks),
        "shop_edge": SHOP_EDGE,
        "min_books": MIN_FAIR_BOOKS,
        "captures": int(board["captured_at"].nunique()) if not board.empty else 0,
        "latest_capture": stamp,
        "current": listing,
        "cells": cells,
    }


def _american(probability: float) -> int | None:
    if not probability or probability <= 0 or probability >= 1:
        return None
    if probability >= 0.5:
        return int(round(-100.0 * probability / (1.0 - probability)))
    return int(round(100.0 * (1.0 - probability) / probability))


def _side(row: Mapping) -> str:
    market, selection, line = row["market"], row["selection"], row.get("line")
    if market == "moneyline":
        return f"{selection} moneyline"
    if line is None:
        return selection
    return f"{selection} {line:+g}" if market == "spread" else f"{selection} {line:g}"


def _pct(value) -> str:
    return "—" if value is None else f"{value:+.1%}"


def render(record: Mapping) -> str:
    lines = [
        "# CBB price shop",
        "",
        f"As of {record['as_of']}. Every main-market side where one book's price beats the "
        f"market's fair price (the median of {record['min_books']}+ books' own no-vig quotes) "
        f"by at least {record['shop_edge']:.0%}. No model is read: this is a slow book, not an "
        "opinion about the game. Advice only; the card does not read it.",
        "",
        "## Right now",
        "",
    ]
    current = record["current"]
    if record["latest_capture"] is None:
        lines += ["No capture holds an untipped game with a fair price yet.", ""]
    elif not current:
        lines += [f"Nothing clears the bar in the capture of {record['latest_capture']}.", ""]
    else:
        lines += [
            f"From the capture of {record['latest_capture']}.",
            "",
            "| Tip (UTC) | Game | Side | Book | Price | Fair | Edge |",
            "|:---|:---|:---|:---|---:|---:|---:|",
        ]
        for row in current:
            fair = "—" if row["fair_american"] is None else f"{row['fair_american']:+d}"
            lines.append(
                f"| {row['commence'][:16].replace('T', ' ')} | {row['game']} | {_side(row)} | "
                f"{row['book']} | {row['american']:+d} | {fair} | {row['edge']:+.1%} |"
            )
        lines.append("")
    lines += [
        "## Did the shops beat the close?",
        "",
        f"Each side's first shop, graded against the fair price of the same side at the same line "
        f"at the last capture before tip ({record['captures']:,} capture(s) read). Per tier, "
        f"clustered by game, corrected across {record['looks']} cumulative hypotheses "
        f"(x{record['correction_factor']:.4f}); a tier needs {MIN_GRADED} graded sides for an "
        "interval. Closing-line value is not a return.",
        "",
        "| Tier | Shops | Graded | Games | Mean CLV | Corrected | Beat the close | Line gone at close |",
        "|:---|---:|---:|---:|---:|:---|---:|---:|",
    ]
    for c in record["cells"]:
        corrected = "—" if c["low"] is None else f"{_pct(c['low'])} to {_pct(c['high'])}"
        verdict = ""
        if c["low"] is not None:
            verdict = (" (demonstrated edge)" if c["low"] > 0 else
                       " (demonstrated deficit)" if c["high"] < 0 else " (no demonstrated edge)")
        beat = "—" if c["beat_close"] is None else f"{c['beat_close']:.0%}"
        lines.append(
            f"| {c['tier'].replace('_', '-')} | {c['shops']:,} | {c['graded']:,} | {c['games']:,} | "
            f"{_pct(c['mean'])} | {corrected}{verdict} | {beat} | {c['ungraded']:,} |"
        )
    lines += [
        "",
        "Line gone at close: the side's line was no longer quoted by enough books at the last "
        "capture, so it is ungraded rather than guessed. Unplaced games are ones the forward "
        "ledger never froze.",
        "",
    ]
    return "\n".join(lines)


def write(record: Mapping, output_dir: Path | str) -> tuple[Path, Path]:
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)
    json_path, md_path = base / JSON_NAME, base / MD_NAME
    json_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render(record), encoding="utf-8")
    return json_path, md_path
