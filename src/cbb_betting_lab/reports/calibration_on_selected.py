"""Calibration on the bets that were actually selected, not on everything priced.

**Overall calibration is not evidence.** That sentence appears in the rendered
report every time, because the NHL lab's model was calibrated across the board —
every bucket straight, nothing to see — and overconfident by **9 to 12
percentage points on precisely the wagers it chose to bet**. A model is selected
into its bets by its own disagreement with the price, so the bets are the tail
of its own error distribution. That is the winner's curse, and an all-opinions
calibration plot cannot see it by construction: the bets are a small, adversely
chosen slice of the rows that plot averages over.

So this module reports **both, side by side**, and says which one is evidence.

## Calibration can rule a model out, and never in

This is a hard rule in `CLAUDE.md`, and it carries two receipts:

* In the EPL lab a change that improved calibration on every market cost about
  **140 units** in the backtest.
* In the NHL lab the by-ice-time correction straightened every volume bucket and
  lost **37.6 units** in the only form a card could actually apply it — because
  the version that gained 162.8 units conditioned on *actual* ice time, which is
  not known before the game.

So a straight line here is never a reason to ship anything. Where a priced test
exists, `price_backtest.py` decides. What this module can do is kill: a model
that is 10 points overconfident on what it picks is choosing its bets by its own
error, and no threshold on that error repairs it.

## The bins are declared here, in advance

:data:`BIN_EDGES` is fixed rather than computed from the data as deciles. Deciles
move with the sample, so the same model measured twice produces two different
tables and neither can be compared to the other. Fixed edges also make the thin
tails visibly thin instead of silently widening to hold 10% of the rows.

Every bucket carries its `n` and a **Wilson** interval — Wilson because the
normal approximation is wrong exactly where this lab looks hardest, at small
counts and proportions near zero or one.

## Pushes are not half a win

A push is excluded from the frequency and **counted in the exclusions line**,
never folded in as 0.5. A calibration figure computed over a denominator that
quietly includes pushes is measuring a different quantity from the one it names,
and the difference grows with exactly the markets where whole-number lines are
common.
"""

from __future__ import annotations

import pandas as pd

from cbb_betting_lab import stats as S


#: Declared in advance and fixed. See the module docstring: deciles move with
#: the sample and make two runs of the same model incomparable.
BIN_EDGES: tuple[float, ...] = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)

#: Below this many rows a bucket prints its count and no frequency. A bucket of
#: nine observations has a Wilson interval wide enough to contain almost any
#: claim, and printing its point estimate invites somebody to read the shape of
#: the line rather than the intervals around it.
MINIMUM_BUCKET = 30

#: Printed in the report every time, in these words.
OVERALL_IS_NOT_EVIDENCE = (
    "**The overall figure is not evidence.** A model is selected into its bets "
    "by its own disagreement with the price, so its bets are the tail of its "
    "own error distribution. The NHL lab's model was calibrated across the "
    "board and overconfident by 9 to 12 percentage points on precisely what it "
    "picked. Read the selected column."
)

#: What the report says when there is nothing to bin.
NOTHING_TO_MEASURE = "there is nothing to measure"


def _scored(frame: pd.DataFrame, *, probability_column: str) -> pd.DataFrame:
    """Rows with a probability and a won/lost outcome. Pushes are excluded."""
    if frame.empty or probability_column not in frame.columns:
        return pd.DataFrame(columns=["probability", "won"])
    probability = pd.to_numeric(frame[probability_column], errors="coerce")
    outcome = frame["outcome"].astype(str)
    keep = probability.notna() & outcome.isin(["won", "lost"])
    return pd.DataFrame(
        {"probability": probability[keep], "won": (outcome[keep] == "won").astype(int)}
    )


def excluded_counts(frame: pd.DataFrame, *, probability_column: str) -> dict:
    """Why a priced row is not in the calibration denominator.

    Printed rather than dropped. A denominator that silently loses rows is how a
    figure ends up measuring a different quantity from the one it names.
    """
    if frame.empty:
        return {"no_probability": 0, "push": 0, "void": 0, "unsettleable": 0}
    outcome = frame["outcome"].astype(str) if "outcome" in frame.columns else pd.Series(
        [""] * len(frame), index=frame.index
    )
    probability = (
        pd.to_numeric(frame[probability_column], errors="coerce")
        if probability_column in frame.columns
        else pd.Series([float("nan")] * len(frame), index=frame.index)
    )
    return {
        "no_probability": int(probability.isna().sum()),
        "push": int((outcome == "push").sum()),
        "void": int((outcome == "void").sum()),
        "unsettleable": int((outcome == "unsettleable").sum()),
    }


def calibration_table(
    frame: pd.DataFrame, *, probability_column: str = "model_probability"
) -> list[dict]:
    """Predicted against observed, per declared bucket, with Wilson intervals."""
    scored = _scored(frame, probability_column=probability_column)
    rows: list[dict] = []
    for low, high in zip(BIN_EDGES[:-1], BIN_EDGES[1:]):
        last = high == BIN_EDGES[-1]
        in_bin = (scored["probability"] >= low) & (
            (scored["probability"] <= high) if last else (scored["probability"] < high)
        )
        chunk = scored[in_bin]
        n = int(len(chunk))
        if not n:
            rows.append(
                {
                    "low": low,
                    "high": high,
                    "n": 0,
                    "predicted": None,
                    "observed": None,
                    "wilson_low": None,
                    "wilson_high": None,
                    "gap": None,
                    "enough": False,
                }
            )
            continue
        wins = int(chunk["won"].sum())
        predicted = float(chunk["probability"].mean())
        observed = wins / n
        wilson_low, wilson_high = S.wilson_interval(wins, n)
        rows.append(
            {
                "low": low,
                "high": high,
                "n": n,
                "predicted": predicted,
                "observed": observed,
                "wilson_low": wilson_low,
                "wilson_high": wilson_high,
                "gap": observed - predicted,
                "enough": n >= MINIMUM_BUCKET,
            }
        )
    return rows


def overconfidence(rows: list[dict]) -> dict:
    """How far predicted sits above observed, weighted by bucket size.

    Positive means **overconfident**: the model said it would win more often
    than it did. Reported in percentage points, which is the unit the NHL lab's
    9-to-12 was quoted in and the unit this number has to be comparable with.
    """
    usable = [r for r in rows if r["n"] and r["enough"]]
    total = sum(r["n"] for r in usable)
    if not total:
        return {"points": None, "n": 0, "buckets": 0}
    weighted = sum((r["predicted"] - r["observed"]) * r["n"] for r in usable)
    return {
        "points": float(weighted / total),
        "n": int(total),
        "buckets": len(usable),
    }


def build_record(
    universe: pd.DataFrame,
    bets: pd.DataFrame,
    *,
    probability_column: str = "model_probability",
    threshold: float | None = None,
) -> dict:
    """Both tables, and the sentence that says which of them is evidence."""
    overall = calibration_table(universe, probability_column=probability_column)
    selected = calibration_table(bets, probability_column=probability_column)
    return {
        "probability_column": probability_column,
        "edge_threshold": threshold,
        "minimum_bucket": MINIMUM_BUCKET,
        "bin_edges": list(BIN_EDGES),
        "overall": overall,
        "selected": selected,
        "overall_overconfidence": overconfidence(overall),
        "selected_overconfidence": overconfidence(selected),
        "overall_excluded": excluded_counts(
            universe, probability_column=probability_column
        ),
        "selected_excluded": excluded_counts(
            bets, probability_column=probability_column
        ),
    }


def _cells(row: dict) -> str:
    """Three table cells: n, observed with its Wilson interval, and the gap.

    A bucket under :data:`MINIMUM_BUCKET` prints its count and **no frequency**.
    The point estimate of nine observations invites somebody to read the shape
    of the line rather than the intervals around it.
    """
    if not row["n"]:
        return "— | — | —"
    if not row["enough"]:
        return f"{row['n']:,} | — | —"
    return (
        f"{row['n']:,} | {row['observed']:.1%} "
        f"[{row['wilson_low']:.1%}, {row['wilson_high']:.1%}] | "
        f"{row['gap'] * 100:+.1f} pp"
    )


def render_section(record: dict) -> list[str]:
    """The calibration section, as lines, for embedding in another report."""
    lines: list[str] = []
    add = lines.append
    add("## Calibration, overall and on the bets that were selected")
    add("")
    add(OVERALL_IS_NOT_EVIDENCE)
    add("")
    add(
        "**Calibration can rule a model out and never in.** In the EPL lab a "
        "change that improved calibration on every market cost about 140 units "
        "in the backtest; in the NHL lab the by-ice-time correction "
        "straightened every volume bucket and lost 37.6 units in the only form "
        "a card could apply it. A straight line here is not a reason to ship "
        "anything."
    )
    add("")

    overall = record.get("overall") or []
    selected = record.get("selected") or []
    if not any(r["n"] for r in overall) and not any(r["n"] for r in selected):
        add(
            f"**{NOTHING_TO_MEASURE.capitalize()}.** No priced opinion has been "
            "graded, so there is nothing to bin. Said in words rather than "
            "shown as an empty table, because an empty table reads as a null "
            "result."
        )
        add("")
        return lines

    add(
        "| Predicted | Overall n | Overall observed | Gap | Selected n | "
        "Selected observed | Gap |"
    )
    add("|:---|---:|:---|---:|---:|:---|---:|")
    for left, right in zip(overall, selected):
        label = f"{left['low']:.0%}–{left['high']:.0%}"
        add(f"| {label} | {_cells(left)} | {_cells(right)} |")
    add("")

    for name, key in (("Overall", "overall_overconfidence"), ("Selected", "selected_overconfidence")):
        summary = record.get(key) or {}
        if summary.get("points") is None:
            add(
                f"- **{name}:** not enough evidence — no bucket reached the "
                f"{record.get('minimum_bucket', MINIMUM_BUCKET)} rows declared "
                "in advance."
            )
            continue
        direction = "overconfident" if summary["points"] > 0 else "underconfident"
        add(
            f"- **{name}: {abs(summary['points']) * 100:.1f} pp "
            f"{direction}** over {summary['n']:,} graded rows in "
            f"{summary['buckets']} usable bucket(s)."
        )
    add("")
    excluded = record.get("selected_excluded") or {}
    if any(excluded.values()):
        add(
            "Excluded from the selected denominator: "
            + ", ".join(f"{v:,} {k.replace('_', ' ')}" for k, v in excluded.items() if v)
            + ". A push is not half a win and is never folded in as one."
        )
        add("")
    return lines


def render(record: dict) -> str:
    """Standalone report. Normally this section is embedded in the backtest."""
    lines = ["# Calibration on the bets that were selected", ""]
    lines.extend(render_section(record))
    return "\n".join(lines).rstrip() + "\n"
