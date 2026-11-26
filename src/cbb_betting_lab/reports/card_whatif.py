"""What each card rule did to the card's record: the what-if replay.

Cooper, 2026-11-26 (*"all 3"*). Eight card changes landed between 2026-11-18
and 2026-11-26, and a record of the picks the card made cannot say which of
them earned or cost units: a pick a rule removed is not on it at all. So each
card run now also keeps every **candidate** it considered — every wager that
cleared the flat 2% bar at its best in-band price and every gate except the
stricter bars of `models/card_bars.py` — in `cbb_card_candidates.csv`, carried
on `card-feed` as `card_candidates.csv`.

This module replays each slot's candidates through `card_bars.Bars` with the
rules in force today, and again with each rule switched the other way, one at
a time, and grades every replayed pick with the forward ledger's own
settlement (`card_record.grade`). The difference between a variant and
today's card is what that one rule did.

**What it is not.** A replay picks from the candidates' best price at the
flat bar, so where a stricter bar would have taken a different book's price
the replay keeps the flat one; and the trust table, the line-move restraint
and the model layers are whatever they were on the night, never replayed.
It reads no price from any provider, spends no credit, changes nothing the
card reads and registers no hypothesis: every rule it replays was registered
before it was built (`card_bars_2026_11_20`, `card_bars_2026_11_26`). Per
tier, never pooled across Division I.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Iterable, Mapping

import pandas as pd

from cbb_betting_lab.models import card_bars, sizing
from cbb_betting_lab.reports import card_pricing

#: Every candidate a card run considered, carried on `card-feed`.
CANDIDATES_FILENAME = "cbb_card_candidates.csv"
#: The report Gameday Refresh publishes as `latest_card_whatif.md`.
REPORT_FILENAME = "cbb_card_whatif.md"

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
    "tier",
    "american_odds",
    "book",
    "probability",
    "edge",
)

#: What makes two picks the same bet (`card_record.IDENTITY`).
IDENTITY: tuple[str, ...] = (
    "slate_date", "home_team", "away_team", "market", "segment", "player", "selection", "line",
)

TIERS: tuple[str, ...] = ("high_major", "mid_major", "low_major")

RULE_NAMES: dict[str, str] = {
    "high_hold": "5% bar on alt ladders and team totals (decision 116)",
    "heavy_favourite": "4% bar at -150 or shorter (decision 116, off since 120)",
    "evening_new_game": "4% bar on the evening card's new games (decision 116)",
    "morning_floor": "evening re-lists only at the morning's number (decision 116)",
    "long_alt": "7% bar on alt spreads at +200 or longer (decision 120)",
    "rank": "big edges shrunk, moneylines first, for a game's slot (decision 120)",
    "evening_size": "evening new games at half size (decision 120)",
}


# --------------------------------------------------------------------------
# The carried file
# --------------------------------------------------------------------------


def frame(rows: Iterable[Mapping] | pd.DataFrame) -> pd.DataFrame:
    data = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(list(rows))
    for column in COLUMNS:
        if column not in data.columns:
            data[column] = ""
    return data[list(COLUMNS)].reset_index(drop=True)


def read(path: Path | str) -> pd.DataFrame:
    target = Path(path)
    if not target.is_file() or target.stat().st_size == 0:
        return frame([])
    try:
        return frame(pd.read_csv(target, dtype=str, keep_default_na=False))
    except (OSError, pd.errors.ParserError, pd.errors.EmptyDataError):
        return frame([])


def write(data: pd.DataFrame, path: Path | str) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(target.name + ".tmp")
    frame(data).to_csv(tmp, index=False)
    tmp.replace(target)
    return target


def append(existing: pd.DataFrame, rows: Iterable[Mapping], *, slate_date: str, card_slot: str) -> pd.DataFrame:
    """This run's candidates replace any earlier run of the same day and slot."""
    current = frame([{**dict(r), "slate_date": slate_date, "card_slot": card_slot} for r in rows])
    old = frame(existing)
    keep = ~((old["slate_date"].astype(str) == str(slate_date)) & (old["card_slot"].astype(str) == str(card_slot)))
    return frame(pd.concat([old[keep], current], ignore_index=True))


# --------------------------------------------------------------------------
# The replay
# --------------------------------------------------------------------------


def _num(value) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def _wager(row: Mapping) -> SimpleNamespace:
    line = _num(row.get("line"))
    return SimpleNamespace(
        market=str(row.get("market", "")), segment=str(row.get("segment", "")),
        home_team=str(row.get("home_team", "")), away_team=str(row.get("away_team", "")),
        selection=str(row.get("selection", "")), line=line,
    )


def _size(price: float) -> float:
    """The record's 1u ladder (decision 115): the trust scaling is the card's, not the replay's."""
    ladder = sizing.ladder_units(price)
    return sizing.BASE_UNITS if ladder is None else float(ladder)


def _slot(rows: list[dict], *, card_slot: str, morning, rules: frozenset) -> list[dict]:
    bars = card_bars.Bars(base=card_pricing.EDGE_THRESHOLD, card_slot=card_slot, morning=morning, rules=rules)
    cleared = []
    for row in rows:
        price, edge = _num(row.get("american_odds")), _num(row.get("edge"))
        if price is None or edge is None:
            continue
        wager = _wager(row)
        if edge < max(card_pricing.EDGE_THRESHOLD, bars.threshold(wager, price)):
            continue
        cleared.append((bars.rank_edge(wager, edge), row, wager, price))
    cleared.sort(key=lambda c: (-c[0], str(c[1].get("market")), str(c[1].get("selection")), str(c[1].get("line"))))
    kept, games = [], set()
    for _rank, row, wager, price in cleared:
        if row.get("event_id") in games:
            continue
        if len(kept) >= card_pricing.MAX_POSITIONS_PER_SLATE:
            break
        games.add(row.get("event_id"))
        probability = _num(row.get("probability"))
        kept.append({
            **row,
            "card_slot": card_slot,
            "units": _size(price) * bars.size_scale(row),
            "bet_down_to": bars.bet_down_to(probability, wager, price_band=card_pricing.PRICE_BAND)
            if probability is not None else None,
        })
    return kept


def replay(candidates: pd.DataFrame, rules: frozenset) -> pd.DataFrame:
    """Every slot's card as `rules` would have picked it, one pick per bet."""
    data = frame(candidates)
    picks: list[dict] = []
    for day in sorted(set(data["slate_date"].astype(str))):
        today = data[data["slate_date"].astype(str) == day]
        morning_rows = _slot(
            today[today["card_slot"] == "morning"].to_dict("records"), card_slot="morning", morning=None, rules=rules
        )
        picks.extend(morning_rows)
        evening = today[today["card_slot"] == card_bars.EVENING].to_dict("records")
        if evening:
            morning = card_bars.Morning.from_rows(morning_rows, day=day) if morning_rows else None
            picks.extend(_slot(evening, card_slot=card_bars.EVENING, morning=morning, rules=rules))
    out = pd.DataFrame(picks)
    if out.empty:
        return pd.DataFrame(columns=list(COLUMNS) + ["units", "bet_down_to"])
    out["_order"] = out["card_slot"].map({"morning": 0, "evening": 1}).fillna(2)
    out = out.sort_values(["slate_date", "_order"]).drop_duplicates(list(IDENTITY), keep="first")
    return out.drop(columns="_order").reset_index(drop=True)


def profit(outcome: object, price: float, units: float) -> float | None:
    """Units won or lost: a minus price risks enough to win `units`."""
    outcome = str(outcome or "")
    if outcome == "push" or outcome == "void":
        return 0.0
    if outcome not in ("won", "lost"):
        return None
    if price < 0:
        risk, win = units * -price / 100.0, units
    else:
        risk, win = units, units * price / 100.0
    return win if outcome == "won" else -risk


def outcomes_for(candidates: pd.DataFrame, graded: pd.DataFrame) -> dict:
    """identity -> outcome, from candidates graded once by `card_record.grade`."""
    out = {}
    for row in graded.to_dict("records"):
        out[tuple(str(row.get(c, "")) for c in IDENTITY)] = row.get("outcome")
    return out


def tally(picks: pd.DataFrame, outcomes: Mapping) -> dict:
    """Per tier: picks, wins, losses, pushes, units, risked."""
    result = {t: {"picks": 0, "won": 0, "lost": 0, "push": 0, "units": 0.0, "risked": 0.0, "pending": 0} for t in TIERS}
    for row in picks.to_dict("records"):
        tier = str(row.get("tier", ""))
        if tier not in result:
            continue
        cell = result[tier]
        cell["picks"] += 1
        outcome = outcomes.get(tuple(str(row.get(c, "")) for c in IDENTITY))
        price, units = _num(row.get("american_odds")), _num(row.get("units")) or 0.0
        gained = profit(outcome, price, units) if price is not None else None
        if gained is None:
            cell["pending"] += 1
            continue
        if outcome in ("won", "lost", "push"):
            cell[outcome] += 1
        cell["units"] += gained
        if outcome in ("won", "lost"):
            cell["risked"] += units * (-price / 100.0 if price < 0 else 1.0)
    return result


def variants(today: frozenset | None = None) -> list[tuple[str, str, frozenset]]:
    """Today's card, then each rule switched the other way, one at a time."""
    base = card_bars.default_rules() if today is None else frozenset(today)
    out = [("today", "Today's card", base)]
    for rule in card_bars.RULES:
        if rule in base:
            out.append((rule, f"Without: {RULE_NAMES.get(rule, rule)}", base - {rule}))
        else:
            out.append((rule, f"With: {RULE_NAMES.get(rule, rule)}", base | {rule}))
    return out


def build(candidates: pd.DataFrame, outcomes: Mapping, *, today: frozenset | None = None) -> dict:
    """Every variant's tally per tier, and its difference from today's card."""
    rows = []
    reference = None
    for key, label, rules in variants(today):
        picks = replay(candidates, rules)
        counts = tally(picks, outcomes)
        if reference is None:
            reference = counts
        rows.append({"key": key, "label": label, "tiers": counts,
                     "delta": {t: counts[t]["units"] - reference[t]["units"] for t in TIERS}})
    data = frame(candidates)
    days = sorted(d for d in set(data["slate_date"].astype(str)) if d)
    return {"days": days, "candidates": int(len(data)), "variants": rows}


def _cell(counts: Mapping) -> str:
    graded = counts["won"] + counts["lost"]
    if not counts["picks"]:
        return "—"
    roi = f"{100.0 * counts['units'] / counts['risked']:+.1f}%" if counts["risked"] else "—"
    pending = f", {counts['pending']} pending" if counts["pending"] else ""
    return f"{counts['won']}-{counts['lost']}-{counts['push']} {counts['units']:+.2f}u ({roi}, n={graded}{pending})"


def render(result: Mapping) -> str:
    days = result["days"]
    lines = [
        "# What each card rule did",
        "",
        "Each slot's candidates (every wager that cleared the flat 2% bar and every gate "
        "except the stricter bars) replayed through the card's rules as they stand today, "
        "and again with each rule switched the other way, one at a time. Graded by the "
        "forward ledger's settlement at the candidate's own price, sized on the record's 1u "
        "ladder. **Per tier; the column under each rule is what switching it would have "
        "changed**, in units. A small sample, and not a demonstrated effect either way.",
        "",
    ]
    if not days:
        lines += ["No candidates are on file yet: the card started keeping them on 2026-11-26.", ""]
        return "\n".join(lines)
    lines += [
        f"**Window:** {days[0]} to {days[-1]} ({len(days)} slate day(s), {result['candidates']:,} candidate(s)).",
        "",
        "| Variant | " + " | ".join(t.replace("_", "-") for t in TIERS) + " |",
        "|:---|" + "---:|" * len(TIERS),
    ]
    for row in result["variants"]:
        lines.append("| " + row["label"] + " | " + " | ".join(_cell(row["tiers"][t]) for t in TIERS) + " |")
    lines += [
        "",
        "**Units each switch would have changed against today's card** (positive: the switch would have earned more).",
        "",
        "| Switch | " + " | ".join(t.replace("_", "-") for t in TIERS) + " |",
        "|:---|" + "---:|" * len(TIERS),
    ]
    for row in result["variants"][1:]:
        lines.append("| " + row["label"] + " | " + " | ".join(f"{row['delta'][t]:+.2f}u" for t in TIERS) + " |")
    lines += [
        "",
        "*A replay takes each candidate's best price at the flat bar and leaves the trust "
        "table, the line-move restraint and the model layers as they were on the night. "
        "Generated by `scripts/run_card_whatif.py`; it reads no price and spends no credit.*",
        "",
    ]
    return "\n".join(lines)
