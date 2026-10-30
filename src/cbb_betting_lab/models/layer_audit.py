"""The layer audit: which of tonight's layers have earned their place on the card.

Cooper, 2026-10-30: *"I want the model to regularly check/update itself by
adding/removing certain analytical categories or processes. Whatever you deem
best."* This is that, and the fence around it.

Every gameday run re-prices the last `WINDOW_DAYS` slate days walk-forward,
through the same seam the card prices through (`ratings.matchups_for`), and
asks one question of each layer in `card_factors`: **did it move the predicted
margin and total closer to what happened, or further away?** A layer that is on
is judged by taking its move back out; a layer that is off, and each candidate
in `card_factors.CANDIDATE_LAYERS`, by putting the move it left in the shadow
in. The answer switches the layer for the next card:

* a layer on the card is **switched off** when, over at least `MIN_GAMES` games
  it moved across `MIN_DAYS` days, it made the predictions worse with
  day-clustered z at or below `DROP_Z`;
* a candidate is **added** when it made them better with z at or above `ADD_Z`;
* anything else keeps its declared default (`card_factors.default_switches`).

The rule is stateless, so the audit is reproducible from the tables alone and a
layer switched off comes back the day its measured harm stops clearing the
bar — it is measured in the shadow every day it is off.

**What it judges is results, never prices.** The score is the squared error of
the predicted margin plus that of the predicted total, both in points, against
the final score. That is forecast accuracy on free data, the way the ratings
themselves are refitted every run; it spends no credit and reads no price, so
it cannot hunt for a return. Whether any of this beats the market is still the
price backtest's and the forward ledger's question, judged at the experiment
ledger's count (`layer_audit_2026_10_30`). The bars are this lab's choice,
declared here before any audit ran.

**Walk-forward.** Each past day is priced from games strictly before it, and
`card_factors.load_layer_audit` refuses an audit dated after the day being
priced, so the audit never prices a past day with its own verdict and the price
backtest prices history on the declared defaults.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

import numpy as np
import pandas as pd

from cbb_betting_lab.models import card_factors as CF

#: Slate days re-priced per audit, newest first.
WINDOW_DAYS = 28
#: A layer is judged only on games it moved by more than this, in points of
#: margin plus total; the rest say nothing about it.
MOVE_FLOOR = 0.01
MIN_GAMES = 200
MIN_DAYS = 5
DROP_Z = -2.0
ADD_Z = 2.0


@dataclass(frozen=True)
class LayerVerdict:
    key: str
    label: str
    default: bool
    on: bool
    games: int
    days: int
    #: Mean reduction in squared error per game moved (margin² + total²,
    #: points²); positive means the layer helped.
    gain_per_game: float | None
    standard_error: float | None
    z: float | None
    reason: str


def _margin_total(home: float, away: float, possessions: float) -> tuple[float, float]:
    return (home - away) / 100.0 * possessions, (home + away) / 100.0 * possessions


def game_moves(matchup, *, day: str, game_id, actual_margin: float, actual_total: float) -> dict | None:
    """One game's prediction, result, and every switchable layer's move on it.

    For a layer on the card the move is the difference between the price after
    it and the price before it; for a layer off the card it is what the layer
    left in `context["shadow"]`, applied to the final price.
    """
    layers = list(getattr(matchup, "layers", None) or ())
    if not getattr(matchup, "priceable", False) or not layers:
        return None
    final = layers[-1]
    pred_margin, pred_total = _margin_total(final["home"], final["away"], final["possessions"])
    record = {
        "day": str(day), "game_id": game_id,
        "actual_margin": float(actual_margin), "actual_total": float(actual_total),
        "pred_margin": pred_margin, "pred_total": pred_total,
    }
    shadow = (getattr(matchup, "context", None) or {}).get("shadow") or {}
    previous = None
    for layer in layers:
        here = _margin_total(layer["home"], layer["away"], layer["possessions"])
        key = layer["key"]
        if previous is not None and key in CF.SWITCHABLE and key not in shadow:
            record[f"{key}:margin"] = here[0] - previous[0]
            record[f"{key}:total"] = here[1] - previous[1]
            record[f"{key}:on"] = True
        previous = here
    for key, move in shadow.items():
        if key not in CF.SWITCHABLE:
            continue
        moved = _margin_total(
            final["home"] + move["home"], final["away"] + move["away"],
            final["possessions"] + move["possessions"],
        )
        record[f"{key}:margin"] = moved[0] - pred_margin
        record[f"{key}:total"] = moved[1] - pred_total
        record[f"{key}:on"] = False
    return record


def _gains(frame: pd.DataFrame, key: str) -> pd.DataFrame:
    """Per game the layer moved: how much it cut the squared error."""
    columns = [f"{key}:margin", f"{key}:total", f"{key}:on"]
    if not set(columns) <= set(frame.columns):
        return frame.iloc[0:0].assign(gain=[])
    rows = frame.dropna(subset=columns[:2])
    move_m = rows[f"{key}:margin"].astype(float)
    move_t = rows[f"{key}:total"].astype(float)
    rows = rows[(move_m.abs() + move_t.abs()) > MOVE_FLOOR]
    if rows.empty:
        return rows.assign(gain=[])
    on = rows[f"{key}:on"].astype(bool).to_numpy()
    move_m = rows[f"{key}:margin"].astype(float).to_numpy()
    move_t = rows[f"{key}:total"].astype(float).to_numpy()
    pred_m = rows["pred_margin"].to_numpy(dtype=float)
    pred_t = rows["pred_total"].to_numpy(dtype=float)
    # With and without the layer, whichever of the two the card priced.
    with_m = np.where(on, pred_m, pred_m + move_m)
    with_t = np.where(on, pred_t, pred_t + move_t)
    without_m = with_m - move_m
    without_t = with_t - move_t
    actual_m = rows["actual_margin"].to_numpy(dtype=float)
    actual_t = rows["actual_total"].to_numpy(dtype=float)
    gain = (
        (actual_m - without_m) ** 2 - (actual_m - with_m) ** 2
        + (actual_t - without_t) ** 2 - (actual_t - with_t) ** 2
    )
    return rows.assign(gain=gain)


def clustered_mean(values: pd.Series, clusters: pd.Series) -> tuple[float, float | None]:
    """The mean of `values` and its standard error clustered on `clusters`."""
    n = len(values)
    if n == 0:
        return float("nan"), None
    mean = float(values.mean())
    sums = (values - mean).groupby(clusters.to_numpy()).sum()
    g = len(sums)
    if g < 2:
        return mean, None
    variance = float((sums**2).sum()) * g / (g - 1) / (n**2)
    return mean, math.sqrt(variance) if variance > 0 else None


def judge(frame: pd.DataFrame) -> list[LayerVerdict]:
    """One verdict per switchable layer, by the rule in the module docstring."""
    defaults = CF.default_switches()
    out: list[LayerVerdict] = []
    for key in CF.SWITCHABLE:
        default = defaults[key]
        rows = _gains(frame, key) if not frame.empty else frame
        games = int(len(rows))
        days = int(rows["day"].nunique()) if games else 0
        if games == 0:
            out.append(LayerVerdict(key, CF.LABELS[key], default, default, 0, 0, None, None, None,
                                    "it moved no game in the window; kept as declared"))
            continue
        mean, se = clustered_mean(rows["gain"], rows["day"])
        z = None if se is None else mean / se
        on = default
        if games < MIN_GAMES or days < MIN_DAYS or z is None:
            reason = (
                f"{games:,} game(s) over {days} day(s) is under the {MIN_GAMES} games and "
                f"{MIN_DAYS} days the audit needs; kept as declared"
            )
        elif default and z <= DROP_Z:
            on = False
            reason = f"it made the predictions worse (z {z:+.2f}, bar {DROP_Z:+.1f}); switched off"
        elif not default and z >= ADD_Z:
            on = True
            reason = f"it made the predictions better (z {z:+.2f}, bar {ADD_Z:+.1f}); added to the card"
        else:
            bar = DROP_Z if default else ADD_Z
            reason = f"z {z:+.2f} does not cross the {bar:+.1f} bar; kept as declared"
        out.append(LayerVerdict(key, CF.LABELS[key], default, on, games, days, mean, se, z, reason))
    return out


def payload(verdicts: Iterable[LayerVerdict], *, as_of: str, frame: pd.DataFrame,
            days_priced: list[str], notes: list[str] | None = None) -> dict:
    verdicts = list(verdicts)
    return {
        "as_of": str(as_of)[:10],
        "window": {
            "days": sorted(days_priced),
            "games": int(len(frame)),
        },
        "rule": {
            "window_days": WINDOW_DAYS, "min_games": MIN_GAMES, "min_days": MIN_DAYS,
            "drop_z": DROP_Z, "add_z": ADD_Z, "move_floor": MOVE_FLOOR,
            "score": "squared error of margin plus total, points, against the final score",
        },
        "switches": {v.key: v.on for v in verdicts},
        "layers": [asdict(v) for v in verdicts],
        "notes": list(notes or []),
    }


def render(record: Mapping) -> str:
    lines = [
        f"# Layer audit, {record['as_of']}",
        "",
        f"Re-priced {len(record['window']['days'])} slate day(s), {record['window']['games']:,} "
        "games, walk-forward. Each layer is judged on the games it moved: the "
        "drop in squared error of margin plus total per game when it is in "
        "(positive helps), clustered by day.",
        "",
        "| Layer | On the card | Declared | Games | Days | Gain per game | z | Why |",
        "|:--|:--|:--|--:|--:|--:|--:|:--|",
    ]
    for v in record["layers"]:
        gain = "—" if v["gain_per_game"] is None else f"{v['gain_per_game']:+.2f}"
        z = "—" if v["z"] is None else f"{v['z']:+.2f}"
        lines.append(
            f"| {v['label']} | {'on' if v['on'] else 'off'} | {'on' if v['default'] else 'off'} "
            f"| {v['games']:,} | {v['days']} | {gain} | {z} | {v['reason']} |"
        )
    for note in record.get("notes") or []:
        lines += ["", f"- {note}"]
    lines += [
        "",
        "Judged on results, not prices. Nothing here is a claim that a layer "
        "beats the market; that is the price backtest's question.",
        "",
    ]
    return "\n".join(lines)


def save(record: Mapping, raw_dir: Path | str | None) -> Path:
    path = CF.layer_audit_path(raw_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
