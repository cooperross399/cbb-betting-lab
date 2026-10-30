"""How far the card trusts the model against the price, per tier.

Cooper, 2026-10-30: build the plan's upgrades "how you see fit". This is the
first of them, borrowed from the NHL lab's `self_learning.py`, and it answers
the failure this lab has measured rather than guessed at: the model loses to
the de-vigged market on Brier in every tier, it is about ten points
overconfident on the bets it selects, and a higher edge bar makes that worse.

**The rule.** Before the card asks whether a wager clears the edge bar, the
model's probability is pulled toward the market's::

    trusted = market + w_tier * (model - market)

where `market` is the de-vigged two-sided price (each book's own pair,
normalised, the median across books) and `w_tier` is how much of the model's
disagreement with that price has actually been realised in that tier. `w = 1`
is the model as it stands; `w = 0` is the market, which can never clear the
bar because the market's own fair price carries no edge.

**Where `w` comes from, conditioned on what, known when.**

* **The seed** is the disagreement coefficient `cbb_forecast_skill.json`
  fitted per tier over the six bought seasons (`outcome ~ market +
  (model - market)`, clustered; the same regression, so the same `w`). Every
  one of those seasons ended before this season opened, so the seed is known
  on every day it is applied, and it is applied only from `TRUST_FROM`. A
  price backtest over those same seasons must never price with it: that would
  fit `w` on the games it then grades.
* **The live update** is the same regression on this season's settled forward
  ledger, through the same de-vig (scope `wager`, because a frozen row is the
  best price and not one book's quote), with the seed as a ridge prior worth
  `PRIOR_ROWS` rows. Only rows settled before the card's day are read.
* `w` is clamped to `[0, 1]`: below zero would bet against the model's own
  opinion, above one would amplify an opinion this lab has never shown is
  realised.

**What it is not.** It reads no price the card does not already hold, spends no
credit, and touches neither the allowlist nor the forward ledger: the ledger
keeps freezing the model's own probability, so the forward test still measures
the model and a later reading can re-derive any `w` from it. It is a hypothesis
registered in the experiment ledger (`trust_learning_2026_10_30`) and is judged
where every other one is.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from statistics import median
from typing import Iterable, Mapping

import pandas as pd

#: The first slate day the trust table is applied. The seed is fitted on
#: seasons that all end before it.
TRUST_FROM = "2026-11-01"

#: The seed's weight as a ridge prior, in ledger rows at a typical
#: disagreement. A season's forward ledger overtakes it in a few weeks.
PRIOR_ROWS = 2000
#: The typical squared disagreement (ten points) that turns `PRIOR_ROWS` into
#: a penalty on the sum of squares.
TYPICAL_DISAGREEMENT_SQ = 0.01

#: The seed's source, under `data/outputs/`.
SEED_RECORD = "cbb_forecast_skill.json"

#: Tiers with no seed and no ledger rows get this: the market.
UNSEEDED = 0.0


def clamp(w: float) -> float:
    return max(0.0, min(1.0, float(w)))


@dataclass(frozen=True)
class TierTrust:
    tier: str
    seed: float
    seed_rows: int
    ledger_rows: int
    weight: float


@dataclass
class TrustTable:
    """`w` per tier, and how each was arrived at."""

    day: str
    by_tier: dict[str, TierTrust] = field(default_factory=dict)
    active: bool = True
    reason: str = ""

    def weight(self, tier: str) -> float:
        found = self.by_tier.get(str(tier or ""))
        return found.weight if found is not None else UNSEEDED

    def line(self) -> str:
        if not self.active:
            return f"Trust in the model against the price: not applied ({self.reason})."
        parts = [
            f"{t.tier.replace('_', '-')} {t.weight:.3f} (seed {t.seed:.3f}, "
            f"{t.ledger_rows:,} settled forward row(s))"
            for t in sorted(self.by_tier.values(), key=lambda t: t.tier)
        ]
        return (
            "Trust in the model against the price, per tier (0 is the market, 1 "
            "is the model as it stands): " + "; ".join(parts) + ". Every wager's "
            "probability is pulled to market + trust x (model - market) before "
            "the edge bar; a wager with no two-sided price carries no trusted "
            "opinion."
        )


def seed_from_record(path: Path | str) -> dict[str, tuple[float, int]]:
    """tier -> (clamped disagreement coefficient, rows it was fitted on)."""
    try:
        record = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    out: dict[str, tuple[float, int]] = {}
    for tier in record.get("by_tier") or []:
        fit = tier.get("fit") or {}
        if not fit.get("fitted"):
            continue
        for coefficient in fit.get("coefficients") or []:
            if coefficient.get("name") != "disagreement" or not coefficient.get("enough_evidence"):
                continue
            estimate = coefficient.get("estimate")
            if isinstance(estimate, (int, float)) and math.isfinite(estimate):
                out[str(tier.get("label"))] = (clamp(estimate), int(tier.get("rows") or 0))
    return out


def _settled_pairs(ledger: pd.DataFrame, *, before: str) -> pd.DataFrame:
    """Settled won/lost ledger rows before `before`, with a de-vigged price."""
    from cbb_betting_lab.reports import forecast_skill as FS

    if ledger is None or ledger.empty:
        return pd.DataFrame()
    frame = ledger.copy()
    frame = frame[frame["snapshot_date"].astype(str) < str(before)]
    frame = frame[frame["outcome"].astype(str).isin(["won", "lost"])]
    # Team markets only: the seed was fitted on them, and a player row here
    # would be graded by a module the player census does not guard.
    frame = frame[frame["player"].fillna("").astype(str).str.strip() == ""]
    if frame.empty:
        return frame
    frame, _census = FS.devig(frame, scope="wager")
    frame["model_probability"] = pd.to_numeric(frame["model_probability"], errors="coerce")
    frame = frame.dropna(subset=["market_implied", "model_probability"])
    return frame.assign(won=(frame["outcome"].astype(str) == "won").astype(float))


def posterior(seed: float, pairs: pd.DataFrame) -> float:
    """Ridge regression of (won - market) on (model - market), shrunk to the seed."""
    penalty = PRIOR_ROWS * TYPICAL_DISAGREEMENT_SQ
    if pairs is None or pairs.empty:
        return clamp(seed)
    d = (pairs["model_probability"] - pairs["market_implied"]).to_numpy(dtype=float)
    r = (pairs["won"] - pairs["market_implied"]).to_numpy(dtype=float)
    return clamp((float((d * r).sum()) + penalty * seed) / (float((d * d).sum()) + penalty))


def build(day: str, *, outputs_dir: Path | str, ledger: pd.DataFrame | None) -> TrustTable:
    """The table the card prices `day` with."""
    if str(day) < TRUST_FROM:
        return TrustTable(day=str(day), active=False,
                          reason=f"{day} is before {TRUST_FROM}, the first day the seed is known")
    seeds = seed_from_record(Path(outputs_dir) / SEED_RECORD)
    if not seeds:
        return TrustTable(day=str(day), active=False,
                          reason=f"no fitted disagreement coefficient in {SEED_RECORD}")
    pairs = _settled_pairs(ledger, before=str(day)) if ledger is not None else pd.DataFrame()
    table = TrustTable(day=str(day))
    for tier, (seed, rows) in seeds.items():
        mine = pairs[pairs["tier"].astype(str) == tier] if not pairs.empty else pairs
        table.by_tier[tier] = TierTrust(tier, seed, rows, int(len(mine)), posterior(seed, mine))
    return table


def _record(wager) -> dict:
    return {
        "event_id": wager.event_id, "market": wager.market, "segment": wager.segment,
        "player": wager.player, "selection": wager.selection, "line": wager.line,
    }


def market_probabilities(wagers: Iterable) -> dict[tuple, float]:
    """Wager key -> de-vigged market probability, the median over books that
    quote both sides. A wager with no such book is absent: a missing price
    stays missing."""
    from cbb_betting_lab.reports import forecast_skill as FS

    wagers = list(wagers)
    by_pair: dict[tuple, list] = {}
    for wager in wagers:
        key = FS.pair_key(_record(wager))
        if key is not None:
            by_pair.setdefault(key, []).append(wager)
    out: dict[tuple, float] = {}
    for sides in by_pair.values():
        if len(sides) != 2 or sides[0].selection == sides[1].selection:
            continue
        first, second = sides
        a = {q.book: FS.implied_probability(q.american_odds) for q in first.quotes}
        b = {q.book: FS.implied_probability(q.american_odds) for q in second.quotes}
        fair = []
        for book in a.keys() & b.keys():
            total = a[book] + b[book]
            if total == total and total > FS.MINIMUM_OVERROUND:
                fair.append(a[book] / total)
        if fair:
            out[first.key] = float(median(fair))
            out[second.key] = 1.0 - out[first.key]
    return out


def apply(probabilities: Mapping, wagers: Iterable, table: TrustTable | None) -> dict:
    """The probability map the edge bar reads. Unchanged when `table` is absent
    or inactive; otherwise every wager is pulled toward its market price, and a
    wager with no two-sided price is dropped (no trusted opinion)."""
    if table is None or not table.active:
        return dict(probabilities or {})
    wagers = list(wagers)
    market = market_probabilities(wagers)
    out: dict = {}
    for wager in wagers:
        raw = (probabilities or {}).get(wager.key)
        try:
            raw = float(raw)
        except (TypeError, ValueError):
            continue
        if raw != raw or wager.key not in market:
            continue
        m = market[wager.key]
        out[wager.key] = m + table.weight(wager.tier) * (raw - m)
    return out
