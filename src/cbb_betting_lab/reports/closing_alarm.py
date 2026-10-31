"""Whether the card's leans beat the closing line, per tier and market: the early alarm.

Cooper, 2026-10-31. The forward test is judged in April. Closing-line value is
readable within weeks: a model whose leans are steadily on the wrong side of
where the market closes is losing, whatever its record says yet. So this
report reads the settled forward ledger against the line-movement captures and
says, per tier and main market, how far the model's leans finished from the
close and whether their prices were still there at the next capture.

**A lean** is a frozen full-game team row whose edge cleared
`BET_EDGE_THRESHOLD` (`forward_evidence.expected_value`): the rows the card
would have selected on price alone. Allowlisting and the trust table are not
re-applied, because the alarm judges the model, which is what the ledger keeps.

**Closing-line value** is measured from the bettor's side against the last
capture at or before tip (the consensus over books, `line_move`):

* spread and total: points, positive when the close moved past the frozen line
  in the bettor's favour;
* moneyline: probability, the closing de-vigged price of the side minus the
  implied probability of the frozen price, so the vig counts against it.

Alternate ladders, halves, team totals and props are left out: their close is
not the main market's close, and grading one rung against another would be a
figure about the ladder rather than the model.

**The alarm** trips for a tier and market when it holds at least
`ALARM_MIN_LEANS` leans over `ALARM_MIN_GAMES` games and the family-corrected
interval of mean closing-line value lies entirely below zero, at the experiment
ledger's cumulative count, clustered by game. A tripped alarm names the market
as a candidate for withdrawal; this report withdraws nothing. Claude may
withdraw a market and never grant one, and the withdrawal is a separate,
recorded act. Registered as `closing_line_alarm_2026_10_31`, one per tier.

**Reachability** rides along: each lean's price is labelled survived, gone or
unknown at the next capture by `reachability.label_survival`, the lab's one
survival instrument. Unknown is never folded into either of the others.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import pandas as pd

from cbb_betting_lab import line_movement as LM
from cbb_betting_lab import reachability
from cbb_betting_lab import stats as S
from cbb_betting_lab.forward_evidence import BET_EDGE_THRESHOLD
from cbb_betting_lab.models import line_move

ALARM_MIN_LEANS = 100
ALARM_MIN_GAMES = 20
MARKETS = ("moneyline", "spread", "total_points")
UNIT = {"moneyline": "probability", "spread": "points", "total_points": "points"}
TIERS = ("high_major", "mid_major", "low_major")
FULL_GAME = ("game", "full_game")


def _num(value) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if out == out else None


def closing_consensus(store: pd.DataFrame) -> dict:
    """(event_id, market) -> the main market's consensus at the last capture at
    or before tip: the home line, the total, or the home fair probability."""
    if store is None or store.empty:
        return {}
    frame = store.copy()
    frame["captured_at"] = pd.to_datetime(frame["captured_at"], utc=True, errors="coerce")
    frame["commence"] = pd.to_datetime(frame["commence_time"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["captured_at", "commence"])
    frame = frame[frame["captured_at"] <= frame["commence"]]
    frame = frame[frame["segment"].astype(str).isin(FULL_GAME)]
    if "player" in frame.columns:
        frame = frame[frame["player"].fillna("").astype(str).str.strip() == ""]
    out: dict = {}
    for event_id, rows in frame.groupby("event_id"):
        last = rows[rows["captured_at"] == rows["captured_at"].max()]
        for market in MARKETS:
            value = line_move._consensus(last, market)
            if value is not None:
                out[(str(event_id), market)] = value
    return out


def closing_value(row: Mapping, close: Mapping) -> float | None:
    """One lean's closing-line value, in its market's unit, from its side."""
    market = str(row.get("market") or "")
    selection = str(row.get("selection") or "")
    value = close.get((str(row.get("event_id")), market))
    if value is None:
        return None
    if market == "moneyline":
        implied = line_move._implied(row.get("american_odds"))
        if implied is None or selection not in ("home", "away"):
            return None
        fair = value if selection == "home" else 1.0 - value
        return fair - implied
    line = _num(row.get("line"))
    if line is None:
        return None
    if market == "spread":
        if selection == "home":
            return line - value
        if selection == "away":
            return line + value
        return None
    if selection == "over":
        return value - line
    if selection == "under":
        return line - value
    return None


def leans(ledger: pd.DataFrame) -> pd.DataFrame:
    """The ledger's settled full-game team rows whose edge cleared the bar."""
    if ledger is None or ledger.empty:
        return pd.DataFrame()
    frame = ledger.copy()
    frame = frame[frame["market"].astype(str).isin(MARKETS)]
    frame = frame[frame["segment"].astype(str).isin(FULL_GAME)]
    frame = frame[frame["player"].fillna("").astype(str).str.strip() == ""]
    frame = frame[frame["outcome"].fillna("").astype(str).str.strip() != ""]
    edge = pd.to_numeric(frame["edge"], errors="coerce")
    return frame[edge >= BET_EDGE_THRESHOLD].reset_index(drop=True)


def _cell(rows: pd.DataFrame, *, tier: str, market: str, looks: int) -> dict:
    graded = rows.dropna(subset=["clv"])
    cell = {
        "tier": tier, "market": market, "unit": UNIT[market],
        "leans": int(len(rows)), "graded": int(len(graded)),
        "games": int(graded["event_id"].nunique()) if len(graded) else 0,
        "survived": int((rows["reachability"] == LM.SURVIVED).sum()),
        "gone": int((rows["reachability"] == LM.GONE).sum()),
        "unknown": int((rows["reachability"] == LM.UNKNOWN).sum()),
    }
    if graded.empty:
        cell.update(mean=None, low=None, high=None, beat_close=None, alarm=False)
        return cell
    per_game = graded.groupby("event_id").agg(profit=("clv", "sum"), bets=("clv", "size")).reset_index()
    interval = S.interval_by_cluster(per_game, looks=looks)
    enough = cell["graded"] >= ALARM_MIN_LEANS and cell["games"] >= ALARM_MIN_GAMES
    cell.update(
        mean=float(interval.roi),
        low=float(interval.adjusted_low),
        high=float(interval.adjusted_high),
        beat_close=float((graded["clv"] > 0).mean()),
        alarm=bool(enough and interval.adjusted_high < 0),
    )
    return cell


def build_record(ledger: pd.DataFrame, store: pd.DataFrame, *, looks: int, as_of: str) -> dict:
    rows = leans(ledger)
    close = closing_consensus(store)
    if not rows.empty:
        rows = rows.assign(clv=[closing_value(r, close) for r in rows.to_dict("records")])
        rows["reachability"] = (
            reachability.label_survival(rows, store).to_numpy()
            if store is not None and not store.empty
            else LM.UNKNOWN
        )
    cells = []
    for tier in TIERS:
        for market in MARKETS:
            mine = rows[(rows["tier"].astype(str) == tier) & (rows["market"].astype(str) == market)] if not rows.empty else rows
            if mine.empty:
                cells.append({"tier": tier, "market": market, "unit": UNIT[market], "leans": 0,
                              "graded": 0, "games": 0, "survived": 0, "gone": 0, "unknown": 0,
                              "mean": None, "low": None, "high": None, "beat_close": None,
                              "alarm": False})
            else:
                cells.append(_cell(mine, tier=tier, market=market, looks=looks))
    return {
        "as_of": as_of,
        "looks": int(looks),
        "correction_factor": S.bonferroni_factor(looks),
        "edge_threshold": BET_EDGE_THRESHOLD,
        "alarm_min_leans": ALARM_MIN_LEANS,
        "alarm_min_games": ALARM_MIN_GAMES,
        "leans": int(len(rows)),
        "captures": int(store["captured_at"].nunique()) if store is not None and not store.empty else 0,
        "cells": cells,
        "alarms": [f"{c['tier']} / {c['market']}" for c in cells if c["alarm"]],
    }


def _fmt(value, unit: str) -> str:
    if value is None:
        return "—"
    return f"{value:+.1%}" if unit == "probability" else f"{value:+.2f}"


def render(record: Mapping) -> str:
    lines = [
        "# CBB closing-line alarm",
        "",
        f"As of {record['as_of']}. Whether the model's leans (frozen full-game team rows "
        f"with an edge of at least {record['edge_threshold']:.0%}) beat the closing line, "
        "per tier and main market, from the settled forward ledger and the line-movement "
        f"captures ({record['captures']:,} capture(s) read). Intervals are clustered by game "
        f"and corrected across {record['looks']} cumulative hypotheses "
        f"(x{record['correction_factor']:.4f}). Closing-line value is not a return, and a "
        "lean that beat the close can still lose.",
        "",
    ]
    if record["alarms"]:
        lines += [
            "**Alarm: " + ", ".join(record["alarms"]) + ".** The corrected interval of closing-line "
            "value lies entirely below zero over enough leans and games. Each is a candidate for "
            "withdrawal from the allowlist; this report withdraws nothing.",
            "",
        ]
    elif record["leans"] == 0:
        lines += ["No settled lean yet, so there is nothing to read. The alarm is silent because it is empty, not because it is clear.", ""]
    else:
        lines += [f"No alarm. A cell trips at {record['alarm_min_leans']} leans over {record['alarm_min_games']} games with its corrected interval below zero.", ""]
    lines += [
        "| Tier | Market | Leans | Games | Mean CLV | Corrected | Beat the close | Survived / gone / unknown |",
        "|:---|:---|---:|---:|---:|:---|---:|:---|",
    ]
    for c in record["cells"]:
        unit = c["unit"]
        corrected = "—" if c["low"] is None else f"{_fmt(c['low'], unit)} to {_fmt(c['high'], unit)}"
        beat = "—" if c["beat_close"] is None else f"{c['beat_close']:.0%}"
        lines.append(
            f"| {c['tier'].replace('_', '-')} | {c['market']} | {c['graded']:,} | {c['games']:,} | "
            f"{_fmt(c['mean'], unit)} | {corrected} | {beat} | "
            f"{c['survived']:,} / {c['gone']:,} / {c['unknown']:,} |"
        )
    lines += [
        "",
        "Spread and total values are points; moneyline values are probability, the closing "
        "de-vigged price minus the frozen price's implied probability. Unknown survival means "
        "the next capture did not cover the event, and is never counted as gone.",
        "",
    ]
    return "\n".join(lines)


def write(record: Mapping, output_dir: Path | str) -> tuple[Path, Path]:
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)
    json_path = base / "cbb_closing_alarm.json"
    md_path = base / "cbb_closing_alarm.md"
    json_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render(record), encoding="utf-8")
    return json_path, md_path
