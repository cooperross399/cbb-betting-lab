"""What the model learned from last night: the nightly learning report.

Cooper, 2026-11-03: *"Make sure the model learns from each night of
basketball."* Decision 78.

**The learning itself already runs, and this module changes none of it.**
Every gameday run rebuilds the results tables from hoopR and ESPN's same-day
box scores, and every card refits the ratings from them: `ratings.fit` is a
ridge posterior centred on the preseason prior, so each finished game moves
the teams in it and the prior's share falls as the season fills in. The same
run re-audits the card's layers against the last four weeks of finals
(`models/layer_audit.py`) and re-derives how far the edge bar trusts the model
from the settled forward ledger (`models/trust.py`). What nothing did was
**show** it: a run that fitted on yesterday's results and a run that silently
fitted on Saturday's looked identical from the outside.

So this report is the receipt, one per morning:

1. **How last night's projections did.** Every finished game of the last slate
   day, priced walk-forward through `ratings.matchups_for` exactly as the card
   priced it (games strictly before that day), against the final score: the
   margin and total error, and how often the projected winner won. Per tier,
   never pooled into a single Division I headline.
2. **What the ratings took from it.** The same seam fitted again with that day
   included, and the change in each team's net rating (offence minus defence,
   points per 100 possessions on a neutral floor): the biggest risers and
   fallers, and the median share of each rating still carried by the prior.
3. **The other two learners.** The trust weight per tier with its settled
   forward rows, and which card layers the audit has switched.
4. **The season so far.** One row per graded night, carried on the card feed,
   so the error can be watched falling as the prior gives way to the season.

**What it is not.** It reads no price, spends no credit, freezes nothing,
grants and withdraws nothing, and moves no number the card prices with. Its
accuracy figures are forecast accuracy on free data, which is a descriptive
quantity: no edge is or can be claimed from them, so nothing here is a
hypothesis and nothing is registered for it.
"""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

#: Risers and fallers listed each way.
MOVERS = 10
#: Columns of the season history, one row per graded night.
HISTORY_COLUMNS = (
    "day", "as_of", "games", "margin_mae", "margin_bias", "total_mae",
    "total_bias", "winner_pct", "prior_share_median",
)
TIERS = ("high_major", "mid_major", "low_major")


def _tier_label(tier: str) -> str:
    return str(tier or "unplaced").replace("_", "-")


@dataclass(frozen=True)
class GradedGame:
    game_id: int
    home_team_id: int
    away_team_id: int
    home: str
    away: str
    tier: str
    identified_by: str
    projected_margin: float
    projected_total: float
    actual_margin: float
    actual_total: float

    @property
    def margin_error(self) -> float:
        return self.actual_margin - self.projected_margin

    @property
    def total_error(self) -> float:
        return self.actual_total - self.projected_total

    @property
    def winner_called(self) -> bool | None:
        if self.projected_margin == 0 or self.actual_margin == 0:
            return None
        return (self.projected_margin > 0) == (self.actual_margin > 0)


def game_tier(home_tier: str, away_tier: str) -> str:
    """A game's tier is the tier both teams share; a cross-tier game is the
    lower of the two, which is the side the market knows least about."""
    order = {t: i for i, t in enumerate(TIERS)}
    known = [t for t in (str(home_tier), str(away_tier)) if t in order]
    if not known:
        return "unplaced"
    return max(known, key=lambda t: order[t])


def grade(matchups: Mapping, results: Mapping, names: Mapping) -> list[GradedGame]:
    """One row per priced game whose final score is in `results`."""
    out: list[GradedGame] = []
    for event_id, game in matchups.items():
        if not getattr(game, "priceable", False):
            continue
        try:
            game_id = int(event_id)
        except (TypeError, ValueError):
            continue
        scores = results.get(game_id, {})
        home, away = getattr(game, "home_team_id", None), getattr(game, "away_team_id", None)
        if home not in scores or away not in scores:
            continue
        margin, total = float(game.expected_margin), float(game.expected_total)
        if not (math.isfinite(margin) and math.isfinite(total)):
            continue
        out.append(GradedGame(
            game_id=game_id,
            home_team_id=int(home),
            away_team_id=int(away),
            home=str(names.get(home, home)),
            away=str(names.get(away, away)),
            tier=game_tier(getattr(game, "home_tier", ""), getattr(game, "away_tier", "")),
            identified_by=str(getattr(game, "identified_by", "") or "results"),
            projected_margin=margin,
            projected_total=total,
            actual_margin=float(scores[home] - scores[away]),
            actual_total=float(scores[home] + scores[away]),
        ))
    return out


def accuracy(games: Sequence[GradedGame]) -> dict:
    """Margin and total error, and the share of winners called, over `games`."""
    if not games:
        return {"games": 0}
    m = np.array([g.margin_error for g in games], dtype=float)
    t = np.array([g.total_error for g in games], dtype=float)
    called = [g.winner_called for g in games if g.winner_called is not None]
    return {
        "games": len(games),
        "margin_mae": float(np.mean(np.abs(m))),
        "margin_bias": float(np.mean(m)),
        "total_mae": float(np.mean(np.abs(t))),
        "total_bias": float(np.mean(t)),
        "winner_pct": float(np.mean(called)) if called else None,
        "winner_games": len(called),
    }


def net_ratings(fitted) -> dict:
    """team_id -> offence minus defence, points per 100 on a neutral floor."""
    if fitted is None:
        return {}
    teams = set(getattr(fitted, "offence", {})) | set(getattr(fitted, "defence", {}))
    return {
        t: float(fitted.offence.get(t, 0.0)) - float(fitted.defence.get(t, 0.0))
        for t in teams
    }


def rating_moves(before, after, names: Mapping, *, played: Iterable = ()) -> list[dict]:
    """Every team whose net rating both fits hold, with the change."""
    old, new = net_ratings(before), net_ratings(after)
    played = set(played)
    rows = []
    for team in set(old) & set(new):
        rows.append({
            "team_id": int(team),
            "team": str(names.get(team, team)),
            "tier": _safe_tier(after, team),
            "before": round(old[team], 2),
            "after": round(new[team], 2),
            "change": round(new[team] - old[team], 2),
            "played": team in played,
        })
    rows.sort(key=lambda r: r["change"])
    return rows


def _safe_tier(fitted, team) -> str:
    try:
        return str(fitted.tier_of(team))
    except Exception:  # noqa: BLE001 - a tier is a label here, never a gate
        return "unplaced"


def prior_share(fitted) -> dict:
    """Median prior share per rating component, over every team fitted."""
    if fitted is None:
        return {}
    try:
        dist = fitted.prior_weight_distribution((0.5,))
    except Exception:  # noqa: BLE001
        return {}
    return {c: float(v[0.5]) for c, v in dist.items()}


def build_record(
    *,
    day: str,
    as_of: str,
    graded: Sequence[GradedGame],
    moves: Sequence[dict],
    before,
    after,
    trust_line: str = "",
    trust_weights: Mapping | None = None,
    layers: Mapping | None = None,
    notes: Sequence[str] = (),
) -> dict:
    by_tier = {}
    for tier in TIERS + ("unplaced",):
        mine = [g for g in graded if g.tier == tier]
        if mine:
            by_tier[tier] = accuracy(mine)
    on_prior = [g for g in graded if g.identified_by == "prior"]
    worst = sorted(graded, key=lambda g: abs(g.margin_error), reverse=True)[:5]
    share_after = prior_share(after)
    return {
        "day": day,
        "as_of": as_of,
        "overall_games": len(graded),
        "accuracy": accuracy(graded),
        "by_tier": by_tier,
        "priced_on_prior": accuracy(on_prior) if on_prior else {"games": 0},
        "misses": [
            {"game_id": g.game_id, "game": f"{g.away} at {g.home}",
             "projected_margin": round(g.projected_margin, 1),
             "actual_margin": g.actual_margin,
             "projected_total": round(g.projected_total, 1),
             "actual_total": g.actual_total}
            for g in worst
        ],
        "ratings": {
            "fitted_through_before": getattr(before, "priced_through", ""),
            "fitted_through_after": getattr(after, "priced_through", ""),
            "games_before": int(getattr(before, "games", 0) or 0),
            "games_after": int(getattr(after, "games", 0) or 0),
            "prior_share_before": prior_share(before),
            "prior_share_after": share_after,
            "teams_moved": sum(1 for r in moves if abs(r["change"]) >= 0.05),
            "risers": list(reversed(moves[-MOVERS:])) if moves else [],
            "fallers": list(moves[:MOVERS]) if moves else [],
        },
        "trust": {"line": trust_line, "weights": dict(trust_weights or {})},
        "layers": dict(layers or {}),
        "notes": list(notes),
    }


def history_row(record: Mapping) -> dict:
    acc = record.get("accuracy", {})
    share = record.get("ratings", {}).get("prior_share_after", {})
    shares = [v for v in share.values() if v is not None]
    return {
        "day": record.get("day", ""),
        "as_of": record.get("as_of", ""),
        "games": acc.get("games", 0),
        "margin_mae": _fmt(acc.get("margin_mae")),
        "margin_bias": _fmt(acc.get("margin_bias")),
        "total_mae": _fmt(acc.get("total_mae")),
        "total_bias": _fmt(acc.get("total_bias")),
        "winner_pct": _fmt(acc.get("winner_pct"), 4),
        "prior_share_median": _fmt(float(np.median(shares)) if shares else None, 4),
    }


def _fmt(value, places: int = 2) -> str:
    if value is None:
        return ""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return ""
    return "" if not math.isfinite(f) else f"{f:.{places}f}"


def read_history(path: Path | str) -> list[dict]:
    p = Path(path)
    if not p.is_file() or p.stat().st_size == 0:
        return []
    with p.open(encoding="utf-8", newline="") as handle:
        return [dict(r) for r in csv.DictReader(handle)]


def update_history(path: Path | str, record: Mapping) -> list[dict]:
    """Replace the row for the record's graded day, keep every other, sorted."""
    rows = [r for r in read_history(path) if r.get("day") != record.get("day")]
    if record.get("accuracy", {}).get("games", 0):
        rows.append(history_row(record))
    rows.sort(key=lambda r: r.get("day", ""))
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(HISTORY_COLUMNS))
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k, "") for k in HISTORY_COLUMNS})
    return rows


def _pct(value) -> str:
    return "—" if value is None else f"{float(value):.1%}"


def _pts(value, signed: bool = False) -> str:
    if value is None:
        return "—"
    return f"{float(value):+.1f}" if signed else f"{float(value):.1f}"


def render(record: Mapping, history: Sequence[Mapping] = ()) -> str:
    day = record.get("day", "")
    lines = [f"# What the model learned from {day}", ""]
    acc = record.get("accuracy", {})
    if not acc.get("games"):
        lines += [
            f"No finished game from {day} could be graded against a projection, "
            "so nothing is reported for it. The ratings still refit on every "
            "result the tables hold.",
        ]
        for note in record.get("notes", []):
            lines.append(f"- {note}")
        return "\n".join(lines) + "\n"

    lines += [
        f"**{acc['games']:,} finished game(s) graded**, each priced walk-forward "
        f"through the card's own seam and layers, fitted only on games before "
        f"{day}. Error is final minus projection, home side, in points.",
        "",
        "## How last night's projections did",
        "",
        "| Tier | Games | Margin miss (avg) | Margin bias | Total miss (avg) | Total bias | Winner called |",
        "|:---|---:|---:|---:|---:|---:|---:|",
    ]
    for tier, row in record.get("by_tier", {}).items():
        lines.append(
            f"| {_tier_label(tier)} | {row['games']:,} | {_pts(row.get('margin_mae'))} | "
            f"{_pts(row.get('margin_bias'), True)} | {_pts(row.get('total_mae'))} | "
            f"{_pts(row.get('total_bias'), True)} | {_pct(row.get('winner_pct'))} |"
        )
    prior = record.get("priced_on_prior", {})
    if prior.get("games"):
        lines += ["", f"{prior['games']:,} of them were priced on the preseason prior "
                  f"alone (the results did not yet join the two teams): margin miss "
                  f"{_pts(prior.get('margin_mae'))}, winner called {_pct(prior.get('winner_pct'))}."]
    lines += ["", "Per tier, never pooled. These are forecast-accuracy figures on free "
              "data: they say how close the projections were, not whether any bet "
              "had an edge. Bets are graded on the Record tab and in the forward ledger."]

    misses = record.get("misses", [])
    if misses:
        lines += ["", "**Biggest misses:**"]
        for m in misses:
            lines.append(
                f"- {m['game']}: projected {m['projected_margin']:+.1f} (home), "
                f"finished {m['actual_margin']:+.0f}; total {m['projected_total']:.1f} "
                f"projected, {m['actual_total']:.0f} scored."
            )

    r = record.get("ratings", {})
    lines += [
        "",
        "## What the ratings took from it",
        "",
        f"Refitted on {r.get('games_after', 0):,} game(s) this season, through "
        f"{r.get('fitted_through_after') or 'nothing'} (was {r.get('games_before', 0):,}, "
        f"through {r.get('fitted_through_before') or 'nothing'}). "
        f"{r.get('teams_moved', 0):,} team(s) moved by 0.05 points per 100 or more.",
    ]
    before_share, after_share = r.get("prior_share_before", {}), r.get("prior_share_after", {})
    if after_share:
        parts = ", ".join(
            f"{c} {before_share.get(c, float('nan')):.0%} → {v:.0%}" for c, v in after_share.items()
        )
        lines += ["", f"Median share of each rating still carried by the preseason prior: {parts}. "
                  "This falls as the season's results take over."]
    for title, key in (("Biggest risers", "risers"), ("Biggest fallers", "fallers")):
        rows = [x for x in r.get(key, []) if (x["change"] > 0 if key == "risers" else x["change"] < 0)]
        if not rows:
            continue
        lines += ["", f"**{title}** (net rating, points per 100 on a neutral floor):", "",
                  "| Team | Tier | Before | After | Change |", "|:---|:---|---:|---:|---:|"]
        for x in rows:
            lines.append(f"| {x['team']} | {_tier_label(x['tier'])} | {x['before']:+.2f} | "
                         f"{x['after']:+.2f} | {x['change']:+.2f} |")

    trust = record.get("trust", {})
    layers = record.get("layers", {})
    if trust.get("line") or layers:
        lines += ["", "## The other two learners", ""]
        if trust.get("line"):
            lines.append(f"- {trust['line']}")
        if layers:
            on = ", ".join(layers.get("on", [])) or "none"
            lines.append(f"- Layer audit ({layers.get('as_of', 'not dated')}): on the card: {on}.")
            switched = layers.get("switched", [])
            lines.append("- Switched from the declared card: " + (", ".join(switched) if switched else "nothing") + ".")

    if history:
        lines += ["", "## The season so far", "",
                  "| Night | Games | Margin miss | Total miss | Winner called | Prior share |",
                  "|:---|---:|---:|---:|---:|---:|"]
        for h in list(history)[-14:]:
            share = h.get("prior_share_median", "")
            lines.append(
                f"| {h.get('day', '')} | {h.get('games', '')} | {h.get('margin_mae', '')} | "
                f"{h.get('total_mae', '')} | "
                f"{_pct(float(h['winner_pct'])) if h.get('winner_pct') else '—'} | "
                f"{f'{float(share):.0%}' if share else '—'} |"
            )

    for note in record.get("notes", []):
        lines.append(f"\n_{note}_")
    return "\n".join(lines) + "\n"


def save(record: Mapping, text: str, outputs_dir: Path | str, competition) -> tuple[Path, Path]:
    out = Path(outputs_dir)
    out.mkdir(parents=True, exist_ok=True)
    json_path = out / competition.output_name("nightly_learning", ".json")
    md_path = out / competition.output_name("nightly_learning", ".md")
    json_path.write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")
    md_path.write_text(text, encoding="utf-8")
    return json_path, md_path
