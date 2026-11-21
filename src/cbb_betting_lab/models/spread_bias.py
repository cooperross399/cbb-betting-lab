"""The card's spread bias against the market, taken out per tier (decision 117).

Cooper, 2026-11-21: *"Stay with every game and just fix our model so that it
is predicting the correct spread more often."* Over the 670 settled games the
forward ledger holds at the main spread (2026-11-02 to 2026-11-20), the card's
own margin sat on average about two points on the AWAY side of the market's
spread, and more in high-major. It called the underdog on about 70% of games
and its side covered 333 times in 670. Its disagreement with the line carried
no information (r = -0.05), but its average disagreement is a bias, and a
bias can be removed.

This module measures that bias the way the card can know it on the day: for
each tier, the mean of the card's margin minus the market's over the main
spread rows the forward ledger froze in the `WINDOW_DAYS` slate days before
the day, at least `MIN_GAMES` games, clamped to `CLAMP` points. The
`spread_bias` layer in `card_factors` then moves the card's home margin by
minus that figure; the total is held. Walk-forward over the same 670 games
the per-tier version covered 346 of 670 (51.6%) against 333 (49.7%) — a small
gain that is not a demonstrated one, registered as `spread_bias_2026_11_21`,
one per tier, before it was built.

**The ledger already carries the correction.** Once the layer is on, every
frozen probability is priced with the shift in force that day, so its own
disagreement is the RESIDUAL bias. Read naively, the estimate would fall to
zero, the layer would switch the correction off, and the bias would return
the next fortnight. Each day's applied shift is therefore kept in the file
(`by_day`), carried run to run on card-feed, and added back to that day's
rows before they are averaged. A day with no recorded shift had none applied.

Results and lines only: no price is bought, nothing is selected or withdrawn,
and the allowlist and the forward ledger are untouched. `ON = False` makes
every shift zero.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from statistics import NormalDist
from typing import Mapping

import pandas as pd

from cbb_betting_lab.competitions import CBB

ON = True
WINDOW_DAYS = 14
MIN_GAMES = 20
CLAMP = 4.0
#: The standard deviation, in points, that turns a frozen cover probability at
#: the market's line back into the card's disagreement with that line:
#: margin - market = SIGMA x the normal quantile of the probability. Within a
#: point or two of a pick'em the answer barely depends on it.
SIGMA = 11.0
#: How old the newest recorded shift may be before a reader stops using it.
MAX_AGE_DAYS = 3
TIERS = ("high_major", "mid_major", "low_major")
FILE = "spread_bias.json"
DIR = "layer_audit"
_PROB_EDGE = 1e-3


def path(raw_dir: Path | str | None) -> Path:
    base = Path(raw_dir) if raw_dir is not None else Path("data/raw")
    return base / CBB.data_dir_segment / DIR / FILE


def higher_tier(home_tier: object, away_tier: object) -> str:
    """A game's tier as the card places it: the higher of its two sides."""
    known = [str(t) for t in (home_tier, away_tier) if str(t) in TIERS]
    if not known:
        return "unplaced"
    return min(known, key=TIERS.index)


def disagreements(ledger: pd.DataFrame) -> pd.DataFrame:
    """One row per event: its slate date, tier and the card's disagreement.

    Read from the main full-game spread's home rows with a model probability,
    the first snapshot of each event, the median over its books.
    """
    need = {"snapshot_date", "event_id", "market", "segment", "selection", "model_probability", "tier"}
    if ledger is None or len(ledger) == 0 or not need.issubset(ledger.columns):
        return pd.DataFrame(columns=["date", "tier", "disagreement"])
    rows = ledger[
        (ledger["market"].astype(str) == "spread")
        & (ledger["segment"].astype(str).isin(("game", "full_game")))
        & (ledger["selection"].astype(str) == "home")
    ].copy()
    rows["p"] = pd.to_numeric(rows["model_probability"], errors="coerce")
    rows = rows[(rows["p"] > _PROB_EDGE) & (rows["p"] < 1 - _PROB_EDGE)]
    if rows.empty:
        return pd.DataFrame(columns=["date", "tier", "disagreement"])
    quantile = NormalDist().inv_cdf
    rows["disagreement"] = [SIGMA * quantile(float(p)) for p in rows["p"]]
    rows["date"] = rows["snapshot_date"].astype(str).str[:10]
    first = rows.groupby("event_id")["date"].transform("min")
    rows = rows[rows["date"] == first]
    out = rows.groupby("event_id").agg(
        date=("date", "first"), tier=("tier", "first"), disagreement=("disagreement", "median")
    )
    return out.reset_index(drop=True)


def estimate(ledger: pd.DataFrame, *, day: str, by_day: Mapping | None = None) -> dict:
    """Each tier's shift for `day`, in points of home margin, from days before it."""
    day = str(day)[:10]
    games = disagreements(ledger)
    shifts = {tier: 0.0 for tier in TIERS}
    detail: dict = {}
    if not ON or games.empty:
        return {"shifts": shifts, "games": {t: 0 for t in TIERS}}
    target = pd.Timestamp(day)
    dates = pd.to_datetime(games["date"], errors="coerce")
    window = games[(dates < target) & (dates >= target - pd.Timedelta(days=WINDOW_DAYS))].copy()
    applied = by_day or {}
    window["raw"] = [
        float(d) + float((applied.get(str(date)) or {}).get(str(tier), 0.0) or 0.0)
        for d, date, tier in zip(window["disagreement"], window["date"], window["tier"])
    ]
    counts = {}
    for tier in TIERS:
        part = window[window["tier"].astype(str) == tier]
        counts[tier] = int(len(part))
        if len(part) >= MIN_GAMES:
            mean = float(part["raw"].mean())
            if math.isfinite(mean):
                shifts[tier] = round(max(-CLAMP, min(CLAMP, mean)), 3)
        detail[tier] = counts[tier]
    return {"shifts": shifts, "games": counts}


def read(file: Path) -> dict:
    try:
        payload = json.loads(Path(file).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def shifts_for(raw_dir: Path | str | None, *, day: str) -> tuple[dict, str]:
    """The shifts in force on `day`: the newest entry dated on or before it.

    An entry dated after the day is never read, so a walk-forward over past
    days prices each on the shift that was knowable then. Empty, with a reason,
    when there is none within `MAX_AGE_DAYS`.
    """
    if not ON:
        return {}, "the spread-bias layer is off"
    file = path(raw_dir)
    if not file.is_file():
        return {}, f"no spread-bias table on disk at {file}"
    by_day = (read(file).get("by_day") or {})
    day = str(day)[:10]
    usable = sorted(d for d in by_day if str(d)[:10] <= day)
    if not usable:
        return {}, f"no spread-bias entry dated on or before {day}"
    newest = usable[-1]
    if (pd.Timestamp(day) - pd.Timestamp(newest)).days > MAX_AGE_DAYS:
        return {}, f"the newest spread-bias entry is {newest}, more than {MAX_AGE_DAYS} days before {day}"
    entry = by_day[newest] or {}
    return {t: float(v) for t, v in entry.items() if t in TIERS}, ""


def update(file: Path, ledger: pd.DataFrame, *, day: str) -> dict:
    """Estimate `day`'s shifts, record them under `by_day`, and write the file."""
    day = str(day)[:10]
    payload = read(file)
    by_day = dict(payload.get("by_day") or {})
    result = estimate(ledger, day=day, by_day={d: v for d, v in by_day.items() if d < day})
    by_day[day] = result["shifts"]
    payload = {
        "as_of": day,
        "window_days": WINDOW_DAYS,
        "min_games": MIN_GAMES,
        "clamp": CLAMP,
        "sigma": SIGMA,
        "games": result["games"],
        "by_day": dict(sorted(by_day.items())),
    }
    Path(file).parent.mkdir(parents=True, exist_ok=True)
    Path(file).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
