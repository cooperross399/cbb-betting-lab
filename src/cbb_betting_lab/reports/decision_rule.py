"""The April rule, written as code before the season's first result exists.

`docs/when_this_ends.md` declared on 2026-09-01 what the forward ledger is read
against on 2027-04-19: a sample floor, and a table that turns each tier's
corrected interval into one of four outcomes. This module is that table and
nothing else. Writing it now, while the ledger is empty, is the point: a rule
coded after the numbers arrive is a rule that could have been bent to them.

**What is read.** Every settled full-game and half TEAM opinion in the forward
ledger, one wager per row at the price it was frozen at — opinions, not bets,
because the card places none and a frozen opinion scored against its own price
is the same test. Player props are left out (none can be selected,
`gates.Availability` never reaches `CONFIRMED`), and so are futures, which never
enter a game headline. Rows that are void, unsettleable or carry no readable
profit are dropped by `forward_evidence._measurable`, the ledger's one reader.

**The interval** is `forward_evidence._interval`: clustered two ways, by game
and by slate day, corrected across the experiment ledger's cumulative count.

**The outcome**, per tier and for the pooled figure, which is never the
headline:

* below `FLOOR_OPINIONS` settled opinions or `FLOOR_GAMES` distinct games:
  **the test did not run** — diagnose the pipeline, do not read the number;
* corrected interval spans zero: **stop**, no edge after a clean season;
* corrected interval below zero: **stop**, a confirmed loser;
* corrected interval above zero: **a candidate, not a green light** — a second
  season confirms or kills it — and, for the tier clause, **not reachable** in
  those words when the return lives only in prices that did not survive to the
  next capture.

The floors are applied to the pooled ledger, as the document states them; a
tier below them is read the same way, since a tier with fewer opinions than the
whole season's floor cannot have run a test the whole season could not.

The model changing during the season does not change this rule (decision 69):
the April read is over every frozen opinion, and each change is dated in the
decision log so the read can be cut by model if it needs to be.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Mapping

import pandas as pd

from cbb_betting_lab import forward_evidence as FE
from cbb_betting_lab import line_movement as LM
from cbb_betting_lab import reachability
from cbb_betting_lab.competitions import CBB, Competition

DECISION_DATE = "2027-04-19"
FLOOR_OPINIONS = 10_000
FLOOR_GAMES = 2_000
TIERS = ("high_major", "mid_major", "low_major")

DID_NOT_RUN = "the test did not run"
STOP_NO_EDGE = "stop: no edge"
STOP_LOSER = "stop: confirmed loser"
CANDIDATE = "candidate, not a green light"
NOT_REACHABLE = "not reachable"


def opinions(ledger: pd.DataFrame, competition: Competition = CBB) -> pd.DataFrame:
    """Settled team opinions with a readable profit: what the rule reads."""
    measurable = FE._measurable(ledger, competition)
    games, _futures = FE._split_families(measurable)
    if games.empty:
        return games
    team = [not FE._is_player_market(m) for m in games["market"]]
    return games[team].reset_index(drop=True)


def outcome(interval, *, opinions_n: int, games_n: int, survived_roi: float | None = None) -> str:
    """One row of the table in `docs/when_this_ends.md`."""
    if opinions_n < FLOOR_OPINIONS or games_n < FLOOR_GAMES:
        return DID_NOT_RUN
    if interval.adjusted_high < 0:
        return STOP_LOSER
    if interval.adjusted_low <= 0:
        return STOP_NO_EDGE
    if survived_roi is not None and survived_roi <= 0:
        return NOT_REACHABLE
    return CANDIDATE


def _survived_roi(rows: pd.DataFrame, store: pd.DataFrame | None) -> float | None:
    """Return over the opinions whose price was still there at the next capture.

    None when nothing could be labelled, which leaves the tier clause unread
    rather than read as passed; the report says so beside the row.
    """
    if store is None or store.empty or rows.empty:
        return None
    labels = reachability.label_survival(rows, store).to_numpy()
    kept = rows[labels == LM.SURVIVED]
    if kept.empty:
        return 0.0 if (labels == LM.GONE).any() else None
    return float(kept["profit"].sum() / len(kept))


def _row(label: str, rows: pd.DataFrame, *, looks: int, store) -> dict:
    interval = FE._interval(rows, looks=looks)
    games_n = int(rows["event_id"].nunique()) if len(rows) else 0
    survived = _survived_roi(rows, store)
    return {
        "cut": label,
        "opinions": int(len(rows)),
        "games": games_n,
        "roi": float(interval.roi) if len(rows) else None,
        "adjusted_low": float(interval.adjusted_low) if len(rows) else None,
        "adjusted_high": float(interval.adjusted_high) if len(rows) else None,
        "survived_roi": survived,
        "outcome": outcome(interval, opinions_n=len(rows), games_n=games_n, survived_roi=survived),
    }


def build_record(
    ledger: pd.DataFrame,
    *,
    looks: int,
    as_of: str,
    store: pd.DataFrame | None = None,
    competition: Competition = CBB,
) -> dict:
    rows = opinions(ledger, competition)
    tiers = [
        _row(tier, rows[rows["tier"] == tier] if len(rows) else rows, looks=looks, store=store)
        for tier in TIERS
    ]
    pooled = _row("pooled (never the headline)", rows, looks=looks, store=store)
    return {
        "as_of": as_of,
        "decision_date": DECISION_DATE,
        "final": as_of >= DECISION_DATE,
        "looks": int(looks),
        "floor_opinions": FLOOR_OPINIONS,
        "floor_games": FLOOR_GAMES,
        "tiers": tiers,
        "pooled": pooled,
    }


def _pct(value) -> str:
    return "—" if value is None else f"{value:+.1%}"


def render(record: Mapping) -> str:
    when = (
        "This is the decision."
        if record["final"]
        else f"This is a dry run: the rule is read on {record['decision_date']}, and "
        "nothing in this report is a verdict before then."
    )
    lines = [
        "# CBB decision rule",
        "",
        f"As of {record['as_of']}. {when} The rule and its floors were declared in "
        "`docs/when_this_ends.md` on 2026-09-01. Intervals are clustered by game and by "
        f"day and corrected across {record['looks']} cumulative hypotheses.",
        "",
        "| Tier | Opinions | Games | Return | Corrected | Survived-price return | Outcome |",
        "|:---|---:|---:|---:|:---|---:|:---|",
    ]
    for row in list(record["tiers"]) + [record["pooled"]]:
        corrected = (
            "—" if row["adjusted_low"] is None
            else f"{_pct(row['adjusted_low'])} to {_pct(row['adjusted_high'])}"
        )
        lines.append(
            f"| {row['cut'].replace('_', '-')} | {row['opinions']:,} | {row['games']:,} | "
            f"{_pct(row['roi'])} | {corrected} | {_pct(row['survived_roi'])} | {row['outcome']} |"
        )
    lines += [
        "",
        f"The floor is {record['floor_opinions']:,} settled opinions across "
        f"{record['floor_games']:,} distinct games. Below it the test did not run, and "
        "the number is not read. A candidate is never a green light: a second season "
        "confirms or kills it. A survived-price return of — means survival could not "
        "be labelled, so the reachability clause is unread rather than passed. The "
        "pooled row is computed for the stopping rule and is never the headline.",
        "",
    ]
    return "\n".join(lines)


def write(record: Mapping, output_dir: Path | str) -> tuple[Path, Path]:
    base = Path(output_dir)
    base.mkdir(parents=True, exist_ok=True)
    json_path = base / "cbb_decision_rule.json"
    md_path = base / "cbb_decision_rule.md"
    json_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render(record), encoding="utf-8")
    return json_path, md_path
