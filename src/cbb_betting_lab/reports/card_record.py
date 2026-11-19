"""Every pick the card made, graded, with its closing-line value: the card's record.

Cooper, 2026-11-19: *"is the record page perfected?"*, then *"do all 3"*. The
site's record counted one full-game moneyline, spread or total per game, read
off the board, so of the hundreds of picks the two daily cards made it graded a
handful. This module is the card's own record: **every selection either card
made**, across every market and both slots, settled by the same machinery that
settles the forward ledger and read against the closing line.

**Where the picks come from.** Each card run writes its selections, as
`card_pricing.select` kept them, to `cbb_card_state.json`; that is the
structured source and it carries the provider's event id. The cards before this
module existed are read back from their published comments (`latest_card_comment.md`
on `card-feed`, one version per run), whose *Selections* table names the game,
the market, the side, the line, the price and the book. A pick from a comment
has no event id; it is found in the forward ledger, or in the line captures, by
its day and its two teams.

**One pick is one bet.** The same side of the same market at the same number on
the same game, picked by the morning card and again by the evening card, is one
pick, kept at the FIRST price it was published at. A pick at a different number
is a different bet and is kept.

**Settlement** is `forward_evidence`'s, row by row (`_settle_row`), so a card
pick is graded exactly as the forward ledger grades the same frozen opinion. A
game with no final yet is `pending`, never a loss. A row the results cannot
grade is `unsettleable` and is counted, never folded into a loss or a push.

**Closing-line value** is `closing_alarm.close_probability` against the price:
the closing chance that the pick wins, read from the last capture at or before
tip, minus the implied probability of the price taken (so the vig counts
against it). Positive means the price beat the close. The captures hold the
full-game moneyline, spread and total, so a half or a player prop has no close
and carries none; an alternate team total is read as a team total.

Reads no price from any provider, spends no credit, places nothing. It records
what the card said and what happened; it is not a claim of edge, and it
registers no hypothesis.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from cbb_betting_lab import forward_evidence as fe
from cbb_betting_lab import season
from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.models import line_move
from cbb_betting_lab.reports import closing_alarm

#: The record of every card pick, carried on `card-feed` from run to run.
SELECTIONS_FILENAME = "cbb_card_selections.csv"
#: The graded record the site reads (`web/site_pages.py`).
RECORD_FILENAME = "cbb_card_record.json"

COLUMNS: tuple[str, ...] = (
    "slate_date",
    "card_slot",
    "event_id",
    "commence_time",
    "home_team",
    "away_team",
    "market",
    "segment",
    "player",
    "selection",
    "line",
    "american_odds",
    "bet_down_to",
    "book",
    "model_probability",
    "edge",
    "tier",
    "source",
)

#: What makes two picks the same bet. The price and the book are not on it:
#: they are what moves between the morning and evening cards.
IDENTITY: tuple[str, ...] = (
    "slate_date",
    "home_team",
    "away_team",
    "market",
    "segment",
    "player",
    "selection",
    "line",
)

SLOT_ORDER = {"morning": 0, "evening": 1}

#: The four ways the site reads a bet (Cooper, 2026-11-18: straight up, ATS,
#: totals and leans). Team totals are their own row rather than folded into
#: totals: one team's score is not the game's.
CATEGORY_PREFIXES: tuple[tuple[str, str], ...] = (
    ("moneyline", "Straight up"),
    ("alternate_spread", "ATS"),
    ("spread", "ATS"),
    ("alternate_team_total", "Team totals"),
    ("team_total", "Team totals"),
    ("alternate_total_points", "Totals"),
    ("total_points", "Totals"),
)

#: Ledger outcomes as the site writes them.
RESULT = {"won": "win", "lost": "loss", "push": "push", "void": "void"}

#: The markets whose close the captures can give, and the market each is read as.
CLV_MARKET = {
    "moneyline": "moneyline",
    "spread": "spread",
    "alternate_spread": "alternate_spread",
    "total_points": "total_points",
    "alternate_total_points": "alternate_total_points",
    "team_total": "team_total",
    "alternate_team_total": "team_total",
}


def category(market: object) -> str:
    text = str(market or "")
    for prefix, name in CATEGORY_PREFIXES:
        if text.startswith(prefix):
            return name
    return "Other"


# --------------------------------------------------------------------------
# Reading the picks
# --------------------------------------------------------------------------

_HEADER = re.compile(r"^#\s*CBB card\s*[—-]+\s*(\d{4}-\d{2}-\d{2})\s*\((\w+)\)", re.M)
_MARKET = re.compile(r"^(\S+)\s*\((\w+)\)$")


def _number(text: object) -> float | None:
    raw = str(text or "").strip().replace("−", "-").replace("%", "").replace("+", "")
    if not raw or raw in ("—", "-"):
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _cells(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_comment(text: str) -> list[dict]:
    """The *Selections* table of one published card, one dict per pick.

    Columns are read by their header, because the table has gained columns
    over the season (*Bet down to*, *Size*, *When*). A card with no table, or
    a rehearsal, yields nothing."""
    header = _HEADER.search(text or "")
    if not header:
        return []
    day, slot = header.group(1), header.group(2).lower()
    lines = (text or "").splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if line.strip() == "## Selections")
    except StopIteration:
        return []
    names: list[str] | None = None
    picks: list[dict] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if stripped.startswith("## "):
            break
        if not stripped.startswith("|"):
            if names is not None and picks and stripped:
                break
            continue
        cells = _cells(stripped)
        if names is None:
            names = [c.lower() for c in cells]
            continue
        if all(set(c) <= set(":-") for c in cells):
            continue
        row = dict(zip(names, cells))
        game = row.get("game", "")
        if " at " not in game:
            continue
        away, home = game.split(" at ", 1)
        market = _MARKET.match(row.get("market", ""))
        if not market:
            continue
        parts = row.get("selection", "").split()
        if not parts:
            continue
        price = _number(row.get("price"))
        if price is None:
            continue
        model = _number(row.get("model"))
        edge = _number(row.get("edge"))
        picks.append(
            {
                "slate_date": day,
                "card_slot": slot,
                "event_id": "",
                "commence_time": "",
                "home_team": home.strip(),
                "away_team": away.strip(),
                "market": market.group(1),
                "segment": market.group(2),
                "player": "",
                "selection": parts[0],
                "line": _number(parts[1]) if len(parts) > 1 else None,
                "american_odds": price,
                "bet_down_to": _number(row.get("bet down to")),
                "book": row.get("book", ""),
                "model_probability": None if model is None else model / 100.0,
                "edge": None if edge is None else edge / 100.0,
                "tier": row.get("tier", ""),
                "source": "comment",
            }
        )
    return picks


def from_state(payload: Mapping | None) -> list[dict]:
    """The selections one card run kept (`cbb_card_state.json`). A rehearsal's
    are refused, exactly as the change marker refuses them."""
    if not isinstance(payload, Mapping):
        return []
    if str(payload.get("decision", "")) == "rehearsal":
        return []
    day, slot = str(payload.get("slate_date", "")), str(payload.get("card_slot", ""))
    out = []
    for row in payload.get("selections") or []:
        if not isinstance(row, Mapping):
            continue
        out.append(
            {
                "slate_date": str(row.get("slate_date") or day),
                "card_slot": slot,
                "event_id": season.clean_text(row.get("event_id")),
                "commence_time": season.clean_text(row.get("commence_time")),
                "home_team": season.clean_text(row.get("home_team")),
                "away_team": season.clean_text(row.get("away_team")),
                "market": season.clean_text(row.get("market")),
                "segment": season.clean_text(row.get("segment")) or fe.FULL_GAME,
                "player": season.clean_text(row.get("player")),
                "selection": season.clean_text(row.get("selection")),
                "line": fe.normalise_line(row.get("line")),
                "american_odds": _number(row.get("american_odds")),
                "bet_down_to": _number(row.get("bet_down_to")),
                "book": season.clean_text(row.get("book")),
                "model_probability": _number(row.get("model_probability")),
                "edge": _number(row.get("edge")),
                "tier": season.clean_text(row.get("tier")),
                "source": "state",
            }
        )
    return out


def frame(rows: Iterable[Mapping] | pd.DataFrame) -> pd.DataFrame:
    data = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(list(rows))
    for column in COLUMNS:
        if column not in data.columns:
            data[column] = None
    return data[list(COLUMNS)].copy()


def _identity(data: pd.DataFrame) -> pd.DataFrame:
    key = pd.DataFrame(index=data.index)
    for column in IDENTITY:
        if column == "line":
            key[column] = pd.to_numeric(data[column], errors="coerce").round(2).fillna(-9999.0)
        else:
            key[column] = data[column].fillna("").astype(str).str.strip()
    return key


def merge(*sources: Iterable[Mapping] | pd.DataFrame) -> pd.DataFrame:
    """Every pick once: the earliest slot's price wins, and within a slot a
    structured row wins over one read back from a comment."""
    parts = [frame(s) for s in sources]
    parts = [p for p in parts if not p.empty]
    if not parts:
        return frame([])
    data = pd.concat(parts, ignore_index=True)
    data["_slot"] = data["card_slot"].map(SLOT_ORDER).fillna(9)
    data["_src"] = (data["source"].fillna("") != "state").astype(int)
    data = data.sort_values(["slate_date", "_slot", "_src"], kind="stable")
    key = _identity(data)
    keep = ~key.duplicated(keep="first")
    return data[keep].drop(columns=["_slot", "_src"]).reset_index(drop=True)


def read_selections(path: Path | str) -> pd.DataFrame:
    target = Path(path)
    if not target.is_file() or target.stat().st_size == 0:
        return frame([])
    try:
        return frame(pd.read_csv(target, dtype=str, keep_default_na=False))
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return frame([])


def write_selections(data: pd.DataFrame, path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    frame(data).to_csv(tmp, index=False)
    tmp.replace(target)
    return target


# --------------------------------------------------------------------------
# Finding the event
# --------------------------------------------------------------------------


def fill_events(data: pd.DataFrame, *sources: pd.DataFrame) -> pd.DataFrame:
    """Give a comment-read pick its event id and tip time from the forward
    ledger or the captures, matched on day and the two teams. A pick that
    matches no event, or two, is left without one."""
    out = data.copy()
    lookup: dict[tuple[str, str, str], set[tuple[str, str]]] = {}
    for source in sources:
        if source is None or source.empty:
            continue
        cols = {"event_id", "commence_time", "home_team", "away_team"}
        if not cols <= set(source.columns):
            continue
        part = source[list(cols | ({"snapshot_date"} & set(source.columns)) | ({"slate_date"} & set(source.columns)))]
        part = part.drop_duplicates()
        for row in part.itertuples(index=False):
            day = season.slate_date(season.clean_text(row.commence_time), CBB) if season.clean_text(row.commence_time) else ""
            if not day:
                day = season.clean_text(getattr(row, "snapshot_date", "") or getattr(row, "slate_date", ""))
            if not day or not season.clean_text(row.event_id):
                continue
            lookup.setdefault((day, str(row.home_team), str(row.away_team)), set()).add(
                (str(row.event_id), str(row.commence_time))
            )
    for i, row in out.iterrows():
        if season.clean_text(row["event_id"]):
            continue
        found = lookup.get((str(row["slate_date"]), str(row["home_team"]), str(row["away_team"])), set())
        if len(found) == 1:
            event_id, commence = next(iter(found))
            out.at[i, "event_id"] = event_id
            out.at[i, "commence_time"] = commence
    return out


# --------------------------------------------------------------------------
# Grading
# --------------------------------------------------------------------------


def _record(row: Mapping) -> dict:
    record = {column: row.get(column) for column in fe.SNAPSHOT_COLUMNS}
    record["snapshot_date"] = row.get("slate_date")
    if not season.clean_text(row.get("commence_time")):
        # Noon Eastern on the slate day: a tip time only for the slate date's
        # sake, which is all settlement reads it for.
        record["commence_time"] = f"{row.get('slate_date')}T17:00:00Z"
    if not season.clean_text(row.get("event_id")):
        record["event_id"] = f"card:{row.get('slate_date')}:{row.get('away_team')}@{row.get('home_team')}"
    return record


def grade(
    data: pd.DataFrame,
    *,
    team_games: pd.DataFrame,
    player_games: pd.DataFrame,
    game_segments: pd.DataFrame,
    team_index,
    now: datetime | None = None,
    competition: Competition = CBB,
) -> pd.DataFrame:
    """Each pick settled row by row, as the forward ledger settles it."""
    out = data.copy()
    for column in ("outcome", "actual", "note"):
        out[column] = None
    if out.empty:
        return out
    moment = now or datetime.now(timezone.utc)
    records = [_record(row) for row in out.to_dict("records")]
    rows = [fe._frozen_row(r) for r in records]
    days = {d for d in (season.row_slate_date(r, competition) for r in rows) if d}
    fixtures = fe._build_fixture_index(team_games, game_segments, days)
    resolved: dict = {}
    needed: set = set()
    for row in rows:
        day = season.row_slate_date(row, competition)
        if not day:
            continue
        key = (day, row.home_team, row.away_team)
        if key not in resolved:
            resolved[key] = fixtures.resolve(row.home_team, row.away_team, day, team_index)
        if resolved[key] is not None:
            needed.add(resolved[key])
    players = fe._build_player_index(player_games, needed)
    result = fe.SettlementResult()
    settled_at = moment.isoformat()
    for i, (row, record) in enumerate(zip(rows, records)):
        day = season.row_slate_date(row, competition)
        game_id = resolved.get((day, row.home_team, row.away_team)) if day else None
        if game_id is None and day:
            elapsed = fe._days_since(day, moment)
            if elapsed is not None and elapsed <= fe.PATIENCE_DAYS:
                out.at[out.index[i], "outcome"] = "pending"
                continue
        settled = fe._settle_row(
            row, record, game_id, fixtures, players, result, settled_at, competition, team_index
        )
        out.at[out.index[i], "outcome"] = settled.get("outcome")
        out.at[out.index[i], "actual"] = settled.get("actual")
    return out


# --------------------------------------------------------------------------
# Closing-line value
# --------------------------------------------------------------------------


def with_closing_value(data: pd.DataFrame, store: pd.DataFrame | None) -> pd.DataFrame:
    """`close_probability` (the closing chance the pick wins) and `clv` (that
    chance minus the price's implied probability) for every pick the captures
    can read; None for the rest."""
    out = data.copy()
    out["close_probability"] = None
    out["clv"] = None
    close = closing_alarm.closing_consensus(store) if store is not None else {}
    if not close or out.empty:
        return out
    for i, row in out.iterrows():
        market = CLV_MARKET.get(str(row.get("market") or ""))
        if market is None or str(row.get("segment") or "") not in closing_alarm.FULL_GAME:
            continue
        if season.clean_text(row.get("player")):
            continue
        probe = {
            "market": market,
            "selection": row.get("selection"),
            "event_id": row.get("event_id"),
            "line": row.get("line"),
        }
        chance = closing_alarm.close_probability(probe, close)
        implied = line_move._implied(row.get("american_odds"))
        if chance is None or implied is None:
            continue
        out.at[i, "close_probability"] = round(float(chance), 4)
        out.at[i, "clv"] = round(float(chance) - float(implied), 4)
    return out


# --------------------------------------------------------------------------
# The record
# --------------------------------------------------------------------------


def _clean(value):
    if value is None:
        return None
    if isinstance(value, float) and value != value:
        return None
    return value


def _float(value) -> float | None:
    """A number from a CSV string, a float or NaN; None when there is none.
    Unlike `_number` it keeps the sign: a line of -12.5 stays -12.5."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return None if value != value else float(value)
    text = str(value).strip().replace("−", "-")
    if not text:
        return None
    try:
        out = float(text)
    except ValueError:
        return None
    return None if out != out else out


def build_record(data: pd.DataFrame, *, as_of: str, comments_read: int = 0) -> dict:
    """The rows the site reads, and the census that says what they are."""
    rows = []
    for row in data.to_dict("records"):
        outcome = str(row.get("outcome") or "")
        rows.append(
            {
                "date": str(row.get("slate_date") or ""),
                "slot": str(row.get("card_slot") or ""),
                "eventId": _clean(row.get("event_id")) or None,
                "home": row.get("home_team"),
                "away": row.get("away_team"),
                "market": row.get("market"),
                "segment": row.get("segment"),
                "category": category(row.get("market")),
                "selection": row.get("selection"),
                "line": _float(row.get("line")),
                "price": _float(row.get("american_odds")),
                "betDownTo": _float(row.get("bet_down_to")),
                "book": row.get("book") or None,
                "model": _float(row.get("model_probability")),
                "edge": _float(row.get("edge")),
                "tier": row.get("tier") or None,
                "outcome": outcome or None,
                "result": RESULT.get(outcome),
                "closeProbability": _float(row.get("close_probability")),
                "clv": _float(row.get("clv")),
            }
        )
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["outcome"] or "none"] = counts.get(r["outcome"] or "none", 0) + 1
    with_clv = [r["clv"] for r in rows if r["clv"] is not None and r["result"] in ("win", "loss", "push")]
    return {
        "as_of": as_of,
        "picks": len(rows),
        "comments_read": comments_read,
        "outcomes": dict(sorted(counts.items())),
        "clv": {
            "picks": len(with_clv),
            "mean": round(sum(with_clv) / len(with_clv), 4) if with_clv else None,
            "beatClosePct": round(100.0 * sum(1 for v in with_clv if v > 0) / len(with_clv), 1) if with_clv else None,
        },
        "rows": sorted(rows, key=lambda r: (r["date"], SLOT_ORDER.get(r["slot"], 9), str(r["away"]))),
        "notes": [
            "Every selection either daily card made, across every market and both slots. The same side at the same number on the same game is one pick, kept at the first price it was published at.",
            "Settled by the forward ledger's own settlement. A game without a final is pending; a row the results cannot grade is unsettleable and counted apart.",
            "Closing-line value is the closing chance the pick wins, from the last capture at or before tip, minus the implied probability of the price taken. Halves have no captured close and carry none.",
        ],
    }


def write_record(record: Mapping, output_dir: Path | str) -> Path:
    target = Path(output_dir) / RECORD_FILENAME
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, indent=1, default=str) + "\n", encoding="utf-8")
    return target
