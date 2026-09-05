#!/usr/bin/env python3
"""Fit the player-prop model's constants and freeze them, before the model exists.

    PYTHONPATH=src python scripts/fit_player_model.py

**This script never runs at price time.** It reads the settlement table whole --
every played row of every fit season, including the realised stat lines the
model is later asked to forecast -- which is exactly the frame a pricer must
never hold. Nothing importable from `cbb_betting_lab` calls it, and
`tests/test_player_shapes_provenance.py` fails the build if the model package
ever grows an import of it. The only thing that crosses from here to the pricer
is `data/processed/cbb_player_shapes.json`, and the loader in
`models/player_shapes.py` refuses that file if its fit window reaches the season
being priced.

## The window, and why it is the whole point

Every prop quote in this lab's store is season **2024** (2023-11-06 ->
2024-04-08). A constant fitted on a window that contains 2024 is a constant the
model could not have had at sixty minutes to tip, and it leaks in a way no
calibration plot will ever show -- `models/distributions.py` carries four such
constants today, all measured "2018-19 through 2024-25", and every one of them
sees the graded season.

So:

* **FIT = seasons 2019, 2020, 2021, 2022.** Every constant below is computed
  from these rows and no others.
* **HOLD OUT = season 2023.** Refitted independently, reported beside every
  fitted value, and *never* used to choose one. The adjudicated design names
  2023 the validation season and protects it as well as the priced season,
  because a guard that only excludes 2024 blesses fitting on 2023.
* **2024, 2025 and 2026 are never read.** `_load_seasons` raises before the
  frame is built, and the frame it returns has already been cut, so no later
  line in this program can reach one.

The permitted window (2019-2023) holds 890,514 player-games, 569,025 of them
played, over 34,165 athletes -- counted, not quoted. Of that the fit slice is
693,925 rows and the holdout 196,589. Every count is recounted at run time and
written into the frozen file with a sha256 of the exact rows each constant was
fitted from.

## What "fitted and held out" means here, and what it does not

Every constant is measured twice, independently, on disjoint seasons. Both
numbers go in the file. Where they disagree materially -- more than 10%
relatively *and* more than a per-constant absolute floor, so that a correlation
moving from -0.008 to -0.000 is not announced as a 96% discrepancy -- the file
says so in the constant's own `agreement` field and this script prints it.
**No constant is chosen because its two numbers agree**, and none is chosen to
make a market look good: there is no market yet and no price has been produced,
which is the reason this is done first and on its own.

Two constants are *declared* rather than selected: the minutes half-life and the
bucket edges. Declared means the value was written down before the curve was
looked at. The curve is measured anyway, on both windows, and stored as evidence
beside the declaration -- and on this window the argmin is 3, not the declared
4, on both the fit and the holdout, by 0.42%. The declaration stands. The
design's account of why: an earlier half-life was "chosen by 0.08% on the season
it called held out, which is how you spend a holdout on nothing."

## The estimators, in the order the file lists them

1. **`minutes_half_life`** -- declared 4. The RMSE curve over half-lives 2, 3,
   4, 5 and 8 and a flat trailing mean is measured on both windows, on a
   population held **fixed** across half-lives (screening on a projection the
   half-life itself produced would compare six different populations).
2. **`minutes_pmf`** -- an empirical pmf over integer minutes 1..45 per
   projected-minutes bucket. Not a mean and an SD: it carries the 40-minute
   ceiling, the measured left tail, and the left skew a Gaussian throws away.
3. **`minutes_residual_sd`** -- per bucket, of realised minus projected.
4. **`role_prior`** -- nine buckets by projected minutes, a per-minute rate per
   market, allowed to run downward. Monotonicity is reported, never imposed, and
   rebounds does in fact fall with minutes.
5. **`rate_shrinkage_k`** -- credibility in prior *minutes*: `w = M/(M+k)`.
   Fitted by minimising the model's own minutes-weighted forecast error over
   `k`, out of sample by construction. Stability across evidence banks is the
   design's declared gate and is measured per band; see the caveat below, which
   is the largest single qualification in this file.
6. **`value_pmf` / `value_mix_shrinkage_events`** -- the 1/2/3 point value of a
   scoring event, and how hard a player's own mix shrinks toward it.
7. **`conditional_dispersion`** -- variance-to-mean of the *count* given actual
   minutes, measured three ways and frozen on one.
8. **`residual_correlation`** -- the Gaussian copula's off-diagonals, on
   residuals taken within (player-season x realised minute).
9. **Structural check targets** -- never fitted to; what the assembled mixture
   must reproduce.

## L9, and the filter this script refuses to apply

The design's L9 forbids fitting on a sample screened by a quantity realised in
the game being fitted -- a `minutes >= 15` screen truncates exactly the left tail
a standing wager is exposed to -- and forbids the same mistake one level up,
where a player-season selected on *that season's* participation conditions the
estimate on surviving the season it predicts.

The design's own dispersion recipe ("25-35 min band, >=12 games") breaks both
rules. It is measured anyway, under `design_band_value`, so the reproduction
gate in section 8 of the design has something to check against; but the value
this file freezes is measured on every played minute from 1 up, with
player-seasons selected on **prior-season** games only and the conditioning on
minutes done by pooling within (player-season, realised minute) rather than by
throwing rows away. Where the two disagree the file says by how much, and on the
points family they disagree by 4%.

## Two things this file could not do, said here rather than buried

**The credibility gate cannot be run as the design declared it.** The design
requires `k` to be stable "across evidence banks from 10 to 900 prior minutes".
Inside the population the model will actually price there is no 10-60 bank at
all: the design's own R2 refusal needs sixty prior minutes before it will quote
a player, so the lowest declared band is empty by construction. The gate that
was actually run covers 60-900 prior minutes, and a second, diagnostic fit on
the R2-refused rows is reported beside it so the emptiness is visible rather
than inferred. Calling a 60-900 check a 10-900 check would have been the easy
thing and it would have been false.

**The design's points-family dispersion reproduces, and the thing it is a
dispersion *of* is not the scoring-event count.** The design declares 1.11 for
the "points family (residual over compound)". Read as the dispersion that makes
an iid compound sum reproduce the measured conditional points VMR, it
reproduces: 1.079 on the design's own two seasons, 1.106 over 2019-2022, both
inside the design's own +/-0.05 gate. Read as the scoring-event count's own
dispersion -- which is how a Panjer family consumes a `phi` -- it is out by about
0.27, because the event count actually disperses at 1.35-1.38.

Those two readings cannot both be used, and the gap between them is a finding
rather than a discrepancy: **free throws arrive in pairs.** Two made free throws
are two scoring events under any honest count, and an iid compound sum charges
them two independent draws from the value pmf when in the game they are one trip
to the line. Feed the true event dispersion through the compound identity and
the points marginal comes out 22% too wide in variance. Both numbers are frozen
under `points_compound_reconciliation`, and the choice between them belongs to
the model rather than to the fit.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Sequence

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "data" / "processed" / "cbb_player_games.csv"
DEFAULT_OUTPUT = REPO_ROOT / "data" / "processed" / "cbb_player_shapes.json"

#: The season this lab's prop store is entirely made of. Nothing here may read
#: it, or anything after it. A floor rather than a list, so a season table that
#: grows a 2027 does not need this file edited to stay honest.
PRICE_SEASON = 2024

#: Declared before anything was measured.
FIT_SEASONS: tuple[int, ...] = (2019, 2020, 2021, 2022)
VALIDATION_SEASON = 2023

#: The two seasons the adjudicated design fitted on. Re-measured here purely so
#: its published numbers have something to be checked against on their own
#: window, which is the only fair place to check them.
DESIGN_SUBWINDOW: tuple[int, ...] = (2021, 2022)

MINUTES_HALF_LIFE = 4.0
HALF_LIVES_REPORTED: tuple[float, ...] = (2.0, 3.0, 4.0, 5.0, 8.0)

#: Declared. Nine buckets over projected minutes. The lowest sits below the
#: design's R3 refusal threshold of eight projected minutes and is fitted anyway,
#: so a later session can see what was refused rather than infer it.
BUCKET_EDGES: tuple[float, ...] = (8.0, 12.0, 16.0, 20.0, 24.0, 28.0, 32.0, 36.0)
BUCKET_LABELS: tuple[str, ...] = (
    "0-8", "8-12", "12-16", "16-20", "20-24", "24-28", "28-32", "32-36", "36+",
)

MINUTES_SUPPORT_LOW = 1
MINUTES_SUPPORT_HIGH = 45

#: Declared refusal thresholds, from the design.
MIN_PRIOR_GAMES = 4
MIN_PRIOR_MINUTES = 60.0
MIN_PROJECTED_MINUTES = 8.0

#: Markets whose per-minute rate is fitted. `points_events` is the count of
#: scoring events (a made free throw, a made two, a made three); `points` is the
#: market quantity, carried so the design's coherence identity D3 has a mean to
#: check. `threes` is fitted standalone as well as falling out of the value mix,
#: so the two can be compared rather than assumed equal.
RATE_MARKETS: tuple[str, ...] = (
    "points", "points_events", "rebounds", "assists", "threes", "steals", "turnovers",
)

#: Count markets whose conditional dispersion the distribution needs. `points`
#: is here as a measurement, not as a parameter: the points family is a compound
#: sum and its dispersion constant lives on the event count.
COUNT_MARKETS: tuple[str, ...] = (
    "points", "points_events", "rebounds", "assists", "threes", "steals", "turnovers",
)

COPULA_COMPONENTS: tuple[str, ...] = (
    "points", "points_events", "rebounds", "assists", "threes", "steals", "turnovers",
)

DESIGN_BAND = (25.0, 35.0)
DESIGN_MIN_GAMES_IN_BAND = 12

#: L9-clean player-season selection: a player-season enters a dispersion or
#: correlation fit on the strength of the PRIOR season's appearances, never its
#: own. A player with no prior season is admitted; excluding him would select on
#: career length, and freshmen are a large share of this population.
PRIOR_SEASON_MIN_GAMES = 5

#: Evidence banks the credibility constant must be stable across, in prior
#: minutes. The design: "stable within 2x across evidence banks from 10 to 900
#: prior minutes or the market is refused." The first band lies entirely inside
#: what the design's own R2 refuses; see `credibility`.
K_STABILITY_BANDS: tuple[tuple[float, float], ...] = (
    (10.0, 60.0), (60.0, 180.0), (180.0, 400.0), (400.0, 900.0),
)
K_STABILITY_MAX_SPREAD = 2.0
K_STABILITY_MIN_ROWS = 500

REGULAR_MIN_PROJECTED_MINUTES = 15.0

#: A fitted and a held-out value are called out as disagreeing when they differ
#: by more than this relatively AND by more than the constant's own absolute
#: floor. Not a gate -- a label, printed and stored.
DISAGREEMENT_RELATIVE = 0.10


class FitError(RuntimeError):
    """A constant could not be fitted, or a window rule was broken."""


# --------------------------------------------------------------------------
# The window guard. Nothing below this line can reach a forbidden season.
# --------------------------------------------------------------------------


def _check_window(seasons: Sequence[int], *, what: str) -> None:
    """Raise unless every requested season is strictly earlier than the price season."""
    bad = sorted({int(s) for s in seasons if int(s) >= PRICE_SEASON})
    if bad:
        raise FitError(
            f"{what} asks for season(s) {bad}, and this lab prices season "
            f"{PRICE_SEASON}. A constant fitted on the season it is later used to "
            "price is a constant the model could not have had at sixty minutes to "
            "tip; it leaks in a way no calibration plot shows. Refused before any "
            "row is read."
        )


def _load_seasons(path: Path, seasons: Sequence[int], *, what: str) -> pd.DataFrame:
    """Read the player table and hand back only the seasons asked for.

    The guard runs first and the cut happens here, so no later line in this
    program holds a frame containing a forbidden season. The defect this file is
    arranged against is a table loaded once, uncut, outside a loop.
    """
    _check_window(seasons, what=what)
    wanted = sorted({int(s) for s in seasons})
    frame = pd.read_csv(path, low_memory=False)
    frame = frame[frame["season"].isin(wanted)].copy()
    if frame.empty:
        raise FitError(f"{what}: seasons {wanted} are not in {path}.")
    _check_window(sorted(int(s) for s in frame["season"].unique()), what=f"{what} (after the cut)")
    return frame


# --------------------------------------------------------------------------
# Derived columns
# --------------------------------------------------------------------------


def _is_true(series: pd.Series) -> pd.Series:
    """A CSV-round-tripped boolean, read the way `settlement._is_true` reads it.

    `bool("False")` is `True`. Reading `did_not_play` with `bool()` marks every
    player who did play as absent; this lab has that bug written down, and this
    is the same reading rather than a second one.
    """
    if series.dtype == bool:
        return series
    text = series.astype(str).str.strip().str.casefold()
    return text.isin({"true", "t", "yes", "y", "1"})


def prepare(frame: pd.DataFrame) -> pd.DataFrame:
    """Every roster row, played or not, with the columns the estimators share.

    Did-not-play rows are kept rather than dropped at the door, because the
    minutes projection has to exist *on* them: a projection built only where a
    player appeared cannot say what was expected of the night he sat, and that is
    the whole content of the stored `dnp_probability` diagnostic.
    """
    out = frame.copy()
    out["appeared"] = ~_is_true(out["did_not_play"])
    out["athlete_id"] = pd.to_numeric(out["athlete_id"], errors="coerce")
    unreadable = int(out["athlete_id"].isna().sum())
    out = out[out["athlete_id"].notna()].copy()
    out.attrs["rows_in_the_table"] = int(len(frame))
    out.attrs["rows_with_no_readable_athlete_id"] = unreadable
    out["minutes"] = pd.to_numeric(out["minutes"], errors="coerce")
    # A row logged as having appeared but carrying no minutes cannot produce a
    # per-minute rate; it is counted (see `census`) rather than quietly folded
    # into either bucket.
    out["played"] = out["appeared"] & out["minutes"].notna() & (out["minutes"] >= 1.0)

    # The compound points family: a scoring event is a made free throw, a made
    # two or a made three. `points == ft + 2*fg + 3pm` is an identity of the box
    # score, not a modelling choice, and `census` counts where it fails.
    out["threes"] = pd.to_numeric(out["three_point_field_goals_made"], errors="coerce").fillna(0.0)
    out["twos"] = pd.to_numeric(out["field_goals_made"], errors="coerce").fillna(0.0) - out["threes"]
    out["ones"] = pd.to_numeric(out["free_throws_made"], errors="coerce").fillna(0.0)
    out["points_events"] = out["ones"] + out["twos"] + out["threes"]
    for column in ("points", "rebounds", "assists", "steals", "turnovers"):
        out[column] = pd.to_numeric(out[column], errors="coerce").fillna(0.0)

    out = out.sort_values(["season", "athlete_id", "slate_date", "game_id"], kind="mergesort")
    return out.reset_index(drop=True)


def census(prepared: pd.DataFrame) -> dict:
    """What the window is made of, counted rather than quoted."""
    played = prepared[prepared["played"]]
    identity = (
        played["points"] - (played["ones"] + 2.0 * played["twos"] + 3.0 * played["threes"])
    ).abs()
    return {
        "rows_in_the_table": int(prepared.attrs.get("rows_in_the_table", len(prepared))),
        "rows_with_no_readable_athlete_id": int(
            prepared.attrs.get("rows_with_no_readable_athlete_id", 0)
        ),
        "rows": int(len(prepared)),
        "appeared_rows": int(prepared["appeared"].sum()),
        "played_rows": int(prepared["played"].sum()),
        "did_not_play_rows": int((~prepared["appeared"]).sum()),
        "appeared_but_no_minutes_rows": int((prepared["appeared"] & ~prepared["played"]).sum()),
        "athletes": int(prepared["athlete_id"].nunique()),
        "seasons": sorted(int(s) for s in prepared["season"].unique()),
        "box_score_points_identity_failures": int((identity > 1e-9).sum()),
    }


def _group_codes(frame: pd.DataFrame) -> np.ndarray:
    """Contiguous integer codes for (season, athlete), on an already-sorted frame."""
    season = frame["season"].to_numpy()
    athlete = frame["athlete_id"].to_numpy()
    changed = np.empty(len(frame), dtype=bool)
    changed[0] = True
    changed[1:] = (season[1:] != season[:-1]) | (athlete[1:] != athlete[:-1])
    return np.cumsum(changed) - 1


def _shift_within(values: np.ndarray, starts: np.ndarray, *, fill: float) -> np.ndarray:
    """`shift(1)` inside each group: the first row of a group gets `fill`."""
    out = np.empty(len(values), dtype=float)
    out[0] = fill
    out[1:] = values[:-1]
    out[starts] = fill
    return out


def _ffill_within(values: np.ndarray, starts: np.ndarray) -> np.ndarray:
    """Forward-fill inside each group; never across a group boundary."""
    positions = np.arange(len(values))
    valid = np.isfinite(values)
    last_valid = np.maximum.accumulate(np.where(valid, positions, -1))
    group_start = np.maximum.accumulate(np.where(starts, positions, -1))
    source = np.where(last_valid >= group_start, last_valid, -1)
    out = np.where(source >= 0, values[np.maximum(source, 0)], np.nan)
    return out


def _prior_sum(values: np.ndarray, starts: np.ndarray) -> np.ndarray:
    """The sum of a column over strictly earlier rows of the same group.

    The game being predicted is never in its own bank; the first row of a group
    gets 0.0, which the design's R2 refusal then screens out anyway.
    """
    running = np.cumsum(values)
    baseline = pd.Series(np.where(starts, running - values, np.nan)).ffill().to_numpy()
    return running - values - baseline


def with_trailing(prepared: pd.DataFrame, half_life: float) -> pd.DataFrame:
    """Per (season, athlete), the evidence a pricer would hold before each game.

    Everything is strictly prior: the game being predicted is never in its own
    bank, and the projection on a did-not-play row is the projection as of the
    last game the player actually appeared in. Cross-season carry-over is
    deliberately absent -- this lab's team model already refuses it ("a team is
    not the team it was last March") and admitting it here would need a decay
    constant nobody has fitted.

    Every column is a whole-array cumulative operation reset at group
    boundaries. A per-group Python lambda over thirty thousand athletes computes
    the same numbers and takes twenty minutes;
    `tests/test_player_shapes_fit.py::test_trailing_columns_match_the_obvious_groupby`
    holds the two against each other so the speed is not bought on trust.
    """
    out = prepared.copy()
    codes = _group_codes(out)
    starts = np.empty(len(out), dtype=bool)
    starts[0] = True
    starts[1:] = codes[1:] != codes[:-1]
    played = out["played"].to_numpy()

    minutes = out["minutes"].to_numpy(dtype=float)
    played_minutes = np.where(played, minutes, np.nan)
    ewma = np.full(len(out), np.nan)
    if played.any():
        sub = pd.Series(played_minutes[played])
        ewma[played] = (
            sub.groupby(codes[played], sort=False)
            .ewm(halflife=half_life)
            .mean()
            .reset_index(level=0, drop=True)
            .sort_index()
            .to_numpy()
        )
    out["projected_minutes"] = _ffill_within(_shift_within(ewma, starts, fill=np.nan), starts)

    out["prior_games"] = _prior_sum(played.astype(float), starts)
    out["prior_minutes"] = _prior_sum(np.where(played, minutes, 0.0), starts)
    for column in (*RATE_MARKETS, "ones", "twos"):
        values = np.where(played, out[column].to_numpy(dtype=float), 0.0)
        out[f"bank_{column}"] = _prior_sum(values, starts)
    out["bank_threes"] = _prior_sum(np.where(played, out["threes"].to_numpy(dtype=float), 0.0), starts)
    out["bucket"] = bucket_of(out["projected_minutes"])
    return out


def bucket_of(projected: pd.Series | np.ndarray) -> np.ndarray:
    """Bucket index 0..8 from projected minutes; -1 where there is no projection."""
    values = np.asarray(projected, dtype=float)
    out = np.digitize(values, np.asarray(BUCKET_EDGES, dtype=float), right=False)
    return np.where(np.isnan(values), -1, out).astype(int)


def evidence_population(frame: pd.DataFrame) -> pd.DataFrame:
    """Played rows carrying enough prior evidence to form an estimate at all.

    The design's R2 -- four prior appearances and sixty prior minutes -- and
    nothing else. Every screen reads the bank, never the game being predicted,
    so L9 holds. R3 (eight projected minutes) is deliberately *not* applied here:
    the role prior and the minutes lattice want a bottom bucket, and refusing to
    fit the bucket the model refuses to price would leave a later session unable
    to see what it was refusing.
    """
    return frame[
        frame["played"]
        & frame["projected_minutes"].notna()
        & (frame["prior_games"] >= MIN_PRIOR_GAMES)
        & (frame["prior_minutes"] >= MIN_PRIOR_MINUTES)
    ].copy()


def priced_population(frame: pd.DataFrame) -> pd.DataFrame:
    """The rows the model will actually be asked to price: R2 and R3 together."""
    evidence = evidence_population(frame)
    return evidence[evidence["projected_minutes"] >= MIN_PROJECTED_MINUTES].copy()


def bank_population(frame: pd.DataFrame) -> pd.DataFrame:
    """Every played row with any prior evidence at all, R2 not applied.

    Exists for one purpose: the design's credibility gate is declared over
    evidence banks from ten prior minutes up, and R2 refuses everything below
    sixty, so the bottom bank cannot be fitted on any population the model
    prices. This is the population it can be fitted on, and every number taken
    from it is labelled as coming from rows the model refuses.
    """
    return frame[frame["played"] & frame["projected_minutes"].notna() & (frame["prior_games"] >= 1)].copy()


# --------------------------------------------------------------------------
# Provenance
# --------------------------------------------------------------------------


def _key_text(column: pd.Series) -> pd.Series:
    """An identifier rendered the same way whether it arrived as 3149059 or 3149059.0.

    The athlete id is a float column here and turns up as `3149059`,
    `3149059.0` and `"3149059.0"` in the same afternoon; a hash that depended on
    which one arrived would be a provenance record nobody could reproduce. A row
    with no readable id hashes as the literal `none`, which is a fact about the
    sample rather than a row to drop quietly.
    """
    numeric = pd.to_numeric(column, errors="coerce")
    return numeric.map(lambda v: "none" if not np.isfinite(v) else f"{int(round(v))}").astype(str)


def rows_sha256(frame: pd.DataFrame) -> str:
    """A sha256 of the exact rows a constant was fitted from.

    Keyed on (game_id, athlete_id) and sorted, so it is invariant to row order
    and to any column this program adds. It identifies the *sample*, which is
    what a later reader needs in order to check the number.
    """
    if frame.empty:
        return hashlib.sha256(b"").hexdigest()
    keys = _key_text(frame["game_id"]) + "|" + _key_text(frame["athlete_id"])
    digest = hashlib.sha256()
    for key in sorted(keys.tolist()):
        digest.update(key.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


@dataclass
class Constant:
    """One frozen number, with everything needed to distrust it."""

    name: str
    value: object
    held_out_value: object
    sample_size: int
    held_out_sample_size: int
    input_sha256: str
    held_out_sha256: str
    units: str
    provenance: str
    note: str
    material_absolute: float = 0.0
    extra: dict = field(default_factory=dict)

    def disagreement(self) -> str | None:
        """Where the fitted and the held-out number differ materially, in words."""
        worst: tuple[float, float, float, str] | None = None
        for label, fitted, held in _numeric_pairs(self.value, self.held_out_value):
            if not (math.isfinite(fitted) and math.isfinite(held)):
                continue
            absolute = abs(fitted - held)
            if absolute <= self.material_absolute:
                continue
            scale = max(abs(fitted), abs(held))
            if scale <= 0:
                continue
            relative = absolute / scale
            if relative <= DISAGREEMENT_RELATIVE:
                continue
            if worst is None or relative > worst[0]:
                worst = (relative, fitted, held, label)
        if worst is None:
            return None
        relative, fitted, held, label = worst
        where = f" at {label}" if label else ""
        return (
            f"fitted {fitted:.5g} against held-out {held:.5g}{where} -- "
            f"{relative * 100:.1f}% apart, and {abs(fitted - held):.5g} in absolute "
            f"terms, against a floor of {self.material_absolute:g}. Both numbers are "
            "in this file; neither was chosen because it was the flattering one."
        )

    def to_json(self, *, fit_seasons: Sequence[int], validation_season: int) -> dict:
        disagreement = self.disagreement()
        payload = {
            "value": self.value,
            "held_out_value": self.held_out_value,
            "fit_seasons": [int(s) for s in fit_seasons],
            "fitted_through": int(max(fit_seasons)),
            "validation_season": int(validation_season),
            "sample_size": int(self.sample_size),
            "held_out_sample_size": int(self.held_out_sample_size),
            "input_sha256": self.input_sha256,
            "held_out_input_sha256": self.held_out_sha256,
            "units": self.units,
            "provenance": self.provenance,
            "note": self.note,
            "material_absolute": self.material_absolute,
            "disagrees": disagreement is not None,
            "agreement": disagreement
            or (
                f"fitted and held-out agree within {DISAGREEMENT_RELATIVE:.0%} "
                f"or {self.material_absolute:g} absolute at every entry"
            ),
        }
        if self.extra:
            payload["evidence"] = self.extra
        return payload


def _numeric_pairs(
    fitted: object, held: object, label: str = ""
) -> Iterable[tuple[str, float, float]]:
    """Walk two parallel structures, yielding comparable leaf numbers."""
    if isinstance(fitted, Mapping) and isinstance(held, Mapping):
        for key in fitted:
            if key in held:
                yield from _numeric_pairs(
                    fitted[key], held[key], f"{label}.{key}" if label else str(key)
                )
    elif isinstance(fitted, (list, tuple)) and isinstance(held, (list, tuple)):
        for index, (left, right) in enumerate(zip(fitted, held)):
            yield from _numeric_pairs(
                left, right, f"{label}[{index}]" if label else f"[{index}]"
            )
    elif isinstance(fitted, (int, float)) and isinstance(held, (int, float)):
        if not isinstance(fitted, bool) and not isinstance(held, bool):
            yield label, float(fitted), float(held)


def jsonable(value: object) -> object:
    """NaN and infinity out, `null` in.

    `json.dumps` writes a bare `NaN`, which is not JSON and which a strict reader
    in another language will reject. A constant that could not be measured in a
    bucket is stored as `null` -- an absence a loader can refuse on, rather than
    a token that parses as a number in Python and nowhere else.
    """
    if isinstance(value, Mapping):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [jsonable(v) for v in value]
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, (np.bool_,)):
        return bool(value)
    return value


# --------------------------------------------------------------------------
# 1. The minutes projection
# --------------------------------------------------------------------------


def minutes_half_life_curve(prepared: pd.DataFrame) -> dict:
    """RMSE of the minutes projection against realised minutes, per half-life.

    Measured on **one fixed population** -- the rows the declared half-life
    would price -- rather than on each half-life's own. Screening on a
    projection the half-life itself produced compares six different populations
    and calls the difference a half-life effect; here the six curves are
    computed over exactly the same rows.
    """
    reference = priced_population(with_trailing(prepared, MINUTES_HALF_LIFE))
    # `with_trailing` copies `prepared` and adds columns, so every half-life's
    # frame carries the same index. The population is pinned by index rather
    # than recomputed per half-life -- that is the whole point of the fixture.
    keys = reference.index

    curve: dict[str, float] = {}
    for half_life in HALF_LIVES_REPORTED:
        frame = with_trailing(prepared, half_life).loc[keys]
        residual = frame["minutes"].to_numpy() - frame["projected_minutes"].to_numpy()
        curve[f"half_life_{half_life:g}"] = float(np.sqrt(np.nanmean(residual**2)))

    with np.errstate(invalid="ignore", divide="ignore"):
        flat = reference["prior_minutes"].to_numpy() / reference["prior_games"].to_numpy()
    residual = reference["minutes"].to_numpy() - flat
    curve["flat_trailing_mean"] = float(np.sqrt(np.nanmean(residual**2)))

    measured = {k: v for k, v in curve.items() if k.startswith("half_life_")}
    best = min(measured, key=measured.__getitem__)
    declared = f"half_life_{MINUTES_HALF_LIFE:g}"
    spread = (max(measured.values()) - min(measured.values())) / min(measured.values())
    return {
        "rmse": curve,
        "rows": int(len(reference)),
        "argmin": best,
        "declared": declared,
        "cost_of_the_declaration": measured[declared] - measured[best],
        "relative_spread_across_half_lives": float(spread),
    }


def minutes_shapes(
    population: pd.DataFrame,
) -> tuple[list[list[float] | None], list[float], list[int], dict]:
    """The minutes pmf and residual SD, per projected-minutes bucket.

    The pmf is empirical over integers 1..45 and carries exactly zero mass at
    zero. Minutes above 45 -- multi-overtime nights -- are folded onto 45 rather
    than dropped: dropping them would thin the right tail of exactly the players
    a book quotes, and the folded count is reported so the choice is visible.
    """
    support = np.arange(MINUTES_SUPPORT_LOW, MINUTES_SUPPORT_HIGH + 1)
    pmfs: list[list[float] | None] = []
    sds: list[float] = []
    counts: list[int] = []
    folded = 0
    for index in range(len(BUCKET_LABELS)):
        rows = population[population["bucket"] == index]
        counts.append(int(len(rows)))
        if rows.empty:
            pmfs.append(None)
            sds.append(float("nan"))
            continue
        minutes = np.rint(rows["minutes"].to_numpy()).astype(int)
        folded += int(np.sum(minutes > MINUTES_SUPPORT_HIGH))
        minutes = np.clip(minutes, MINUTES_SUPPORT_LOW, MINUTES_SUPPORT_HIGH)
        histogram = np.bincount(minutes - MINUTES_SUPPORT_LOW, minlength=len(support)).astype(float)
        pmfs.append((histogram / histogram.sum()).tolist())
        residual = rows["minutes"].to_numpy() - rows["projected_minutes"].to_numpy()
        sds.append(float(np.std(residual, ddof=1)) if len(residual) > 1 else float("nan"))
    return pmfs, sds, counts, {
        "rows_folded_onto_45": int(folded),
        "rows_total": int(len(population)),
        "mass_at_zero_minutes": 0.0,
    }


# --------------------------------------------------------------------------
# 2. The role prior
# --------------------------------------------------------------------------


def role_priors(population: pd.DataFrame) -> tuple[dict[str, list[float]], list[int], dict]:
    """Per-minute rates by projected-minutes bucket, one table per market.

    Minutes-weighted, never per-game-averaged: a four-minute night should not
    weigh what a thirty-four-minute night says about a rate. Allowed to run
    downward -- rebounds falls with minutes, because big men foul out, and a
    monotone functional form would be wrong about that forever. The shrink target
    is the role, never the team: teammates are substitutes for one another, so
    shrinking a bench player toward his team shrinks him toward the star he is
    not.
    """
    counts = [int((population["bucket"] == index).sum()) for index in range(len(BUCKET_LABELS))]
    tables: dict[str, list[float]] = {}
    for market in RATE_MARKETS:
        row: list[float] = []
        for index in range(len(BUCKET_LABELS)):
            rows = population[population["bucket"] == index]
            row.append(
                float(rows[market].sum() / rows["minutes"].sum()) if len(rows) else float("nan")
            )
        tables[market] = row
    shape: dict[str, str] = {}
    for market, row in tables.items():
        clean = [v for v in row if math.isfinite(v)]
        if len(clean) < 2:
            shape[market] = "too few buckets to say"
        elif all(b >= a for a, b in zip(clean, clean[1:])):
            shape[market] = "rises with minutes throughout"
        elif all(b <= a for a, b in zip(clean, clean[1:])):
            shape[market] = "falls with minutes throughout"
        else:
            shape[market] = "not monotone -- reported, not imposed"
    return tables, counts, {"shape_over_buckets": shape}


# --------------------------------------------------------------------------
# 3. Credibility
# --------------------------------------------------------------------------


def _minimise(loss, lo: float, hi: float) -> float:
    """Golden-section on a unimodal loss over [lo, hi]. Returns the argmin."""
    phi = (math.sqrt(5.0) - 1.0) / 2.0
    a, b = lo, hi
    c, d = b - phi * (b - a), a + phi * (b - a)
    fc, fd = loss(c), loss(d)
    for _ in range(80):
        if fc < fd:
            b, d, fd = d, c, fc
            c = b - phi * (b - a)
            fc = loss(c)
        else:
            a, c, fc = c, d, fd
            d = a + phi * (b - a)
            fd = loss(d)
        if b - a < 1e-8:
            break
    return (a + b) / 2.0


def _fit_k(
    bank_rate: np.ndarray,
    prior: np.ndarray,
    prior_minutes: np.ndarray,
    outcome_rate: np.ndarray,
    weight: np.ndarray,
) -> tuple[float, float]:
    """The credibility constant, by minimising the model's own forecast error.

    `pred = prior + M/(M+k) * (bank - prior)`, and `k` minimises the
    minutes-weighted squared error of `pred` against the *next* game's realised
    rate. Out of sample by construction: the bank is strictly prior games, so no
    row is in its own evidence.

    This is the model's loss rather than a variance decomposition of it, and the
    difference matters. A Buhlmann-Straub `k` is the right answer to a question
    about within- and between-player variance components, and only the right
    answer to a question about forecasting if the process variance is the same at
    ten prior minutes and at nine hundred -- which is the very thing the design
    asks to be checked rather than assumed.

    Returns `(k, weighted_mse)`.
    """
    if bank_rate.size == 0:
        return float("nan"), float("nan")
    gap = bank_rate - prior
    residual0 = outcome_rate - prior
    total = float(np.sum(weight))

    def loss(log_k: float) -> float:
        k = math.exp(log_k)
        w = prior_minutes / (prior_minutes + k)
        residual = residual0 - w * gap
        return float(np.sum(weight * residual**2) / total)

    best = _minimise(loss, math.log(0.1), math.log(10_000.0))
    return float(math.exp(best)), loss(best)


def _k_inputs(population: pd.DataFrame, market: str, prior_table: Sequence[float]):
    table = np.asarray(prior_table, dtype=float)
    bucket = population["bucket"].to_numpy()
    prior_minutes = population["prior_minutes"].to_numpy(dtype=float)
    minutes = population["minutes"].to_numpy(dtype=float)
    prior = table[bucket]
    bank = population[f"bank_{market}"].to_numpy(dtype=float) / prior_minutes
    outcome = population[market].to_numpy(dtype=float) / minutes
    keep = np.isfinite(prior) & np.isfinite(bank) & np.isfinite(outcome) & (prior_minutes > 0)
    return bank, prior, prior_minutes, outcome, minutes, keep


def credibility(
    priced: pd.DataFrame,
    refused: pd.DataFrame,
    priors: Mapping[str, Sequence[float]],
) -> tuple[dict[str, float], dict[str, dict], dict[str, str]]:
    """`k` per market, and whether it holds still across evidence banks.

    The design's rule, quoted: the implied `k` must be stable within 2x across
    evidence banks from 10 to 900 prior minutes "or the market is refused".

    **That rule cannot be run as written, and this function does not pretend
    otherwise.** The design's own R2 refuses any player with fewer than sixty
    prior minutes, so inside the population the model will actually price the
    10-60 bank is empty -- not sparse, empty. What is checked here is 60-900,
    and the 10-60 bank is fitted separately on the R2-refused rows and reported
    as `outside_the_priced_population` so that the emptiness is visible rather
    than inferred. A market whose spread over the banks it *can* be checked on
    exceeds 2x comes back in the third return value, is written to the frozen
    file as unfittable, and the model refuses it. Nothing is smoothed to make a
    band agree with its neighbours.
    """
    fitted: dict[str, float] = {}
    report: dict[str, dict] = {}
    unfittable: dict[str, str] = {}
    for market in RATE_MARKETS:
        bank, prior, prior_minutes, outcome, minutes, keep = _k_inputs(priced, market, priors[market])
        k, mse = _fit_k(bank[keep], prior[keep], prior_minutes[keep], outcome[keep], minutes[keep])
        fitted[market] = k

        bands: dict[str, dict] = {}
        checkable: list[float] = []
        for low, high in K_STABILITY_BANDS:
            inside = keep & (prior_minutes >= low) & (prior_minutes < high)
            rows = int(inside.sum())
            if rows < K_STABILITY_MIN_ROWS:
                bands[f"{low:g}-{high:g}"] = {
                    "k": None,
                    "rows": rows,
                    "note": (
                        "empty inside the priced population: the design's R2 refuses "
                        "a player with fewer than sixty prior minutes, so this bank "
                        "never reaches a price. The gate the design declared over "
                        "10-900 prior minutes is therefore run over 60-900."
                        if high <= MIN_PRIOR_MINUTES
                        else "too few rows to fit"
                    ),
                }
                continue
            band_k, _ = _fit_k(
                bank[inside], prior[inside], prior_minutes[inside], outcome[inside], minutes[inside]
            )
            bands[f"{low:g}-{high:g}"] = {"k": float(band_k), "rows": rows}
            if math.isfinite(band_k):
                checkable.append(float(band_k))

        # The refused bank, fitted anyway, so a later session can see what R2 is
        # keeping out rather than take it on faith.
        eb, ep, epm, eo, em, ekeep = _k_inputs(refused, market, priors[market])
        low_bank = ekeep & (epm >= 10.0) & (epm < MIN_PRIOR_MINUTES)
        outside: dict = {"rows": int(low_bank.sum())}
        if low_bank.sum() >= K_STABILITY_MIN_ROWS:
            low_k, _ = _fit_k(eb[low_bank], ep[low_bank], epm[low_bank], eo[low_bank], em[low_bank])
            outside["k"] = float(low_k)
            outside["note"] = (
                "fitted on rows the design's R2 refuses to price. Diagnostic only: "
                "no price is ever formed here, so this number cannot make a market "
                "unfittable and is not allowed to."
            )
        else:
            outside["k"] = None
            outside["note"] = "not enough R2-refused rows to fit even as a diagnostic"

        spread = (
            max(checkable) / min(checkable)
            if len(checkable) >= 2 and min(checkable) > 0
            else float("inf")
        )
        report[market] = {
            "k_by_evidence_bank_prior_minutes": bands,
            "outside_the_priced_population_10_to_60": outside,
            "banks_actually_checked": len(checkable),
            "spread_across_checked_banks": None if not math.isfinite(spread) else float(spread),
            "spread_limit": K_STABILITY_MAX_SPREAD,
            "weighted_mse_at_k": float(mse),
            "rows": int(keep.sum()),
        }
        if not math.isfinite(spread) or spread > K_STABILITY_MAX_SPREAD:
            unfittable[market] = (
                f"the credibility constant k is not stable across evidence banks: it "
                f"spans {spread:.2f}x over the banks that could be checked, against "
                "the 2x the design declared in advance. A single k fitted anyway "
                "would be right at one bank size and wrong at the others, and the "
                "error would be largest in November when the banks are smallest -- "
                "which is where a player prop model is most tempted to have an "
                "opinion. This market's rate is refused; no value was invented."
            )
    return fitted, report, unfittable


# --------------------------------------------------------------------------
# 4. The value of a scoring event
# --------------------------------------------------------------------------


def value_pmf(played: pd.DataFrame) -> tuple[list[float], dict]:
    """The 1/2/3 point value of a scoring event, over every event in the window."""
    ones = float(played["ones"].sum())
    twos = float(played["twos"].sum())
    threes = float(played["threes"].sum())
    total = ones + twos + threes
    pmf = [ones / total, twos / total, threes / total]
    values = np.array([1.0, 2.0, 3.0])
    weights = np.asarray(pmf)
    ev = float(weights @ values)
    ev2 = float(weights @ values**2)
    implied = total * ev
    actual = float(played["points"].sum())
    return pmf, {
        "scoring_events": int(round(total)),
        "expected_value": ev,
        "second_moment_over_first": ev2 / ev,
        "variance_of_value": ev2 - ev**2,
        "implied_point_total": implied,
        "actual_point_total": actual,
        "reconciliation_gap_points": actual - implied,
        "points_vmr_if_the_event_count_were_poisson": ev2 / ev,
    }


def value_mix_shrinkage(priced: pd.DataFrame, pmf: Sequence[float]) -> tuple[float, dict]:
    """How hard a player's own 1/2/3 mix shrinks toward the league shape.

    Fitted in prior *scoring events*, by minimising the multinomial deviance of
    the next game's realised mix under a shrunk bank mix -- the same
    out-of-sample loss the rate constant is fitted on, so the two constants are
    not chosen against two different questions.
    """
    bank = np.column_stack(
        [
            priced["bank_ones"].to_numpy(dtype=float),
            priced["bank_twos"].to_numpy(dtype=float),
            priced["bank_threes"].to_numpy(dtype=float),
        ]
    )
    events = bank.sum(axis=1)
    outcome = np.column_stack(
        [
            priced["ones"].to_numpy(dtype=float),
            priced["twos"].to_numpy(dtype=float),
            priced["threes"].to_numpy(dtype=float),
        ]
    )
    keep = (events > 0) & (outcome.sum(axis=1) > 0) & np.all(bank >= 0, axis=1)
    bank, events, outcome = bank[keep], events[keep], outcome[keep]
    league = np.asarray(pmf, dtype=float)
    bank_mix = bank / events[:, None]
    total = float(np.sum(outcome))

    def loss(log_k: float) -> float:
        k = math.exp(log_k)
        w = (events / (events + k))[:, None]
        mix = w * bank_mix + (1.0 - w) * league[None, :]
        mix = np.clip(mix, 1e-12, None)
        mix = mix / mix.sum(axis=1, keepdims=True)
        return float(-np.sum(outcome * np.log(mix)) / total)

    k = math.exp(_minimise(loss, math.log(0.1), math.log(10_000.0)))
    return float(k), {
        "rows": int(keep.sum()),
        "deviance_at_k": loss(math.log(k)),
        "deviance_at_the_league_shape_alone": loss(math.log(1e12)),
        "deviance_at_the_player_mix_alone": loss(math.log(1e-12)),
    }


# --------------------------------------------------------------------------
# 5. Conditional dispersion
# --------------------------------------------------------------------------


def pooled_vmr(frame: pd.DataFrame, market: str, keys: Sequence[str]) -> tuple[float, int, int]:
    """Variance-to-mean pooled within cells, dof-corrected.

    Cells of one contribute a mean and no variance, so they are dropped and the
    denominator is `sum(n_i - 1)` -- the same dof correction the design's judge
    used when re-measuring these numbers. Returns (vmr, rows used, cells used).
    """
    grouped = frame.groupby(list(keys), sort=False)[market]
    values = frame[market].to_numpy(dtype=float)
    sizes = grouped.transform("size").to_numpy()
    means = grouped.transform("mean").to_numpy()
    inside = sizes >= 2
    used = int(inside.sum())
    if used == 0:
        return float("nan"), 0, 0
    cells = float(np.sum(1.0 / sizes[inside]))
    dof = float(used) - cells
    mean = float(np.mean(values[inside]))
    if dof <= 0 or mean <= 0:
        return float("nan"), used, int(round(cells))
    sse = float(np.sum((values[inside] - means[inside]) ** 2))
    return sse / dof / mean, used, int(round(cells))


def pearson_dispersion(frame: pd.DataFrame, market: str) -> tuple[float, int]:
    """Quasi-Poisson dispersion of the count against a per-player rate times minutes.

    `phi = sum (x - r_i m)^2 / (r_i m) / (N - I)`, with `r_i` the player-season's
    own minutes-weighted rate. Uses **every** played minute -- no band, no game
    count -- which is what makes it the L9-clean cross-check on the cell
    estimator; the price it pays is that any curvature in the rate against
    minutes lands in the residual and inflates it. Both are reported and neither
    is called the truth.
    """
    grouped = frame.groupby(["season", "athlete_id"], sort=False)
    sizes = grouped["minutes"].transform("size").to_numpy()
    stat_sum = grouped[market].transform("sum").to_numpy()
    minute_sum = grouped["minutes"].transform("sum").to_numpy()
    with np.errstate(invalid="ignore", divide="ignore"):
        rate = stat_sum / minute_sum
    expected = rate * frame["minutes"].to_numpy(dtype=float)
    inside = (sizes >= 2) & np.isfinite(expected) & (expected > 0)
    used = int(inside.sum())
    if used == 0:
        return float("nan"), 0
    cells = float(np.sum(1.0 / sizes[inside]))
    dof = float(used) - cells
    if dof <= 0:
        return float("nan"), used
    residual = frame[market].to_numpy(dtype=float)[inside] - expected[inside]
    return float(np.sum(residual**2 / expected[inside]) / dof), used


def dispersion_population(
    trailing: pd.DataFrame, prior_season_games: Mapping[tuple[int, float], int]
) -> pd.DataFrame:
    """Player-seasons selected on the PRIOR season's appearances, per L9.

    Selecting on ">= 10 played games in the target season" conditions the
    estimate on surviving the season it predicts, which is the `minutes >= 15`
    mistake one level up. A player with no prior season at all is admitted:
    excluding him would select on career length, which correlates with the thing
    being measured, and freshmen are a large share of this population.
    """
    played = trailing[trailing["played"]].copy()
    seasons = played["season"].to_numpy()
    athletes = played["athlete_id"].to_numpy(dtype=float)
    prior = np.array(
        [prior_season_games.get((int(s) - 1, float(a)), -1) for s, a in zip(seasons, athletes)]
    )
    out = played[(prior < 0) | (prior >= PRIOR_SEASON_MIN_GAMES)].copy()
    out["minute_cell"] = np.rint(out["minutes"].to_numpy()).astype(int)
    out["has_prior_season"] = prior[(prior < 0) | (prior >= PRIOR_SEASON_MIN_GAMES)] >= 0
    return out


def conditional_dispersions(
    clean: pd.DataFrame, played: pd.DataFrame
) -> tuple[dict[str, float], dict[str, dict]]:
    """VMR of each count given actual minutes -- three estimators, one frozen.

    The frozen value pools within (season, athlete, realised minute): the
    conditioning on minutes is exact, every played minute from 1 up is in, and
    the only screen is a prior-season one. Beside it go a quasi-Poisson
    dispersion against a per-player rate (no cell requirement at all, but it
    charges any curvature of rate against minutes to the residual) and the
    design's own recipe -- a 25-35 minute band and twelve games inside it, both
    of which read a quantity realised in the game being fitted, which the
    design's own L9 forbids. All three are stored. Where they disagree, they
    disagree in the file.
    """
    values: dict[str, float] = {}
    report: dict[str, dict] = {}
    band = played[
        (played["minutes"] >= DESIGN_BAND[0]) & (played["minutes"] <= DESIGN_BAND[1])
    ].copy()
    sizes = band.groupby(["season", "athlete_id"], sort=False)["minutes"].transform("size")
    band = band[sizes >= DESIGN_MIN_GAMES_IN_BAND]

    for market in COUNT_MARKETS:
        vmr, rows, cells = pooled_vmr(clean, market, ["season", "athlete_id", "minute_cell"])
        values[market] = vmr
        pearson, pearson_rows = pearson_dispersion(clean, market)
        band_vmr, band_rows, _ = pooled_vmr(band, market, ["season", "athlete_id"])
        estimates = [v for v in (vmr, pearson, band_vmr) if math.isfinite(v)]
        report[market] = {
            "rows": rows,
            "cells": cells,
            "pearson_dispersion_all_minutes": None if not math.isfinite(pearson) else float(pearson),
            "pearson_rows": pearson_rows,
            "design_band_value": None if not math.isfinite(band_vmr) else float(band_vmr),
            "design_band_rows": band_rows,
            "design_band_note": (
                "the design's own recipe -- 25-35 realised minutes, >=12 games in the "
                "band. Both screens read a quantity realised in the game being "
                "fitted, which the design's L9 forbids. Kept for comparison, not frozen."
            ),
            "spread_across_estimators": (
                float(max(estimates) / min(estimates)) if len(estimates) >= 2 and min(estimates) > 0 else None
            ),
            "panjer_family": (
                "binomial" if vmr < 1.0 else "poisson" if vmr == 1.0 else "negative binomial"
            ),
        }
    return values, report


def compound_reconciliation(
    dispersion: Mapping[str, float], value: Mapping[str, float]
) -> tuple[dict[str, float], dict]:
    """Two numbers that cannot both be right, measured, and the reason why.

    The design builds the points family as a compound sum: `N` scoring events,
    each independently worth 1, 2 or 3 points. Under that structure

        VMR(points | m) = (Var[V] + phi_N * E[V]^2) / E[V]

    and both sides are measurable here without fitting anything. They do not
    agree. The scoring-event count's own dispersion is about 1.38; feeding that
    through the identity predicts a conditional points VMR near 2.84, and the
    measured conditional points VMR is about 2.33. The compound sum overstates
    the points variance by roughly 22%.

    The mechanism is not mysterious and it is not a measurement error: **free
    throws arrive in pairs.** Two made free throws are two scoring events under
    any honest count, and an iid compound sum charges them two independent
    draws from the value pmf; in the game they are one trip to the line and
    behave far more like a single two-point event. Exchangeable events is the
    assumption that fails, and it fails in exactly the direction observed.

    So this function freezes both numbers and refuses to choose between them,
    because the choice belongs to the model rather than to the fit:

    * `measured_event_dispersion` -- what the scoring-event count actually does.
      Use it and `player_threes` still falls out of the same object as
      `player_points`, and the points marginal comes out about 22% too wide in
      variance.
    * `effective_event_dispersion` -- the value that makes the compound identity
      reproduce the measured conditional points VMR. Use it and the points
      marginal is right while the event count it implies is not the event count
      the box score holds.

    The design's own published 1.11 is neither: it is
    `VMR(points|m) / (E[V^2]/E[V])`, a multiplier on the compound-*Poisson*
    points VMR, which is reproduced here to about a hundredth. Read as an event
    count's dispersion -- which is how a Panjer family would consume it -- it is
    out by about 0.24, and that is the reading a distribution engine is most
    likely to take.
    """
    ev = float(value["expected_value"])
    variance = float(value["variance_of_value"])
    measured_events = float(dispersion["points_events"])
    measured_points = float(dispersion["points"])
    implied_points = (variance + measured_events * ev**2) / ev
    effective_events = (measured_points * ev - variance) / ev**2
    poisson_points = float(value["second_moment_over_first"])
    return (
        {
            "measured_event_dispersion": measured_events,
            "effective_event_dispersion": float(effective_events),
            "measured_points_vmr_given_minutes": measured_points,
            "compound_implied_points_vmr": float(implied_points),
            "compound_overstatement": float(implied_points / measured_points),
            "points_vmr_over_compound_poisson": float(measured_points / poisson_points),
        },
        {
            "expected_value_of_a_scoring_event": ev,
            "variance_of_a_scoring_event": variance,
            "compound_poisson_points_vmr": poisson_points,
            "design_published_points_family_dispersion": 1.11,
            "how_the_design_number_reads": (
                "the design's 1.11 reproduces as `points_vmr_over_compound_poisson`, "
                "not as an event-count dispersion. The two differ by about 0.24 and a "
                "Panjer family consuming the wrong one produces a points distribution "
                "roughly 22% too narrow in variance."
            ),
        },
    )


def residual_correlations(clean: pd.DataFrame) -> tuple[dict[str, float], dict]:
    """The copula's off-diagonals, on residuals within (player-season, realised minute).

    Conditioning on the player and on the realised minute is the whole point: on
    *trailing* minutes these run around 0.4, and nearly all of that is the
    minutes channel the mixture already carries. Applying it twice makes every
    pra interval too wide and under-prices every pra over.
    """
    grouped = clean.groupby(["season", "athlete_id", "minute_cell"], sort=False)
    sizes = grouped["minutes"].transform("size").to_numpy()
    inside = sizes >= 2
    residuals = {
        market: (
            clean[market].to_numpy(dtype=float) - grouped[market].transform("mean").to_numpy()
        )[inside]
        for market in COPULA_COMPONENTS
    }
    out: dict[str, float] = {}
    for index, left in enumerate(COPULA_COMPONENTS):
        for right in COPULA_COMPONENTS[index + 1 :]:
            a, b = residuals[left], residuals[right]
            if a.size < 3 or np.std(a) == 0 or np.std(b) == 0:
                out[f"{left}|{right}"] = float("nan")
            else:
                out[f"{left}|{right}"] = float(np.corrcoef(a, b)[0, 1])
    return out, {"rows": int(inside.sum())}


def structural_targets(
    clean: pd.DataFrame, priced: pd.DataFrame, dispersion: Mapping[str, float], value: Mapping
) -> tuple[dict[str, float], dict]:
    """What the assembled mixture must reproduce, and is never fitted to.

    (a) the unconditional within-player points VMR among rotation regulars -- the
    design stops the run if the mixture misses it by more than 15%; (b) the
    points VMR *given* minutes, against what the compound structure predicts from
    the event-count dispersion and the value pmf with nothing fitted to it; and
    (c) corr(points, threes) given minutes. None of these is a free parameter.
    """
    regulars = priced[priced["projected_minutes"] >= REGULAR_MIN_PROJECTED_MINUTES]
    unconditional, unconditional_rows, _ = pooled_vmr(regulars, "points", ["season", "athlete_id"])

    conditional = dispersion["points"]
    ev = value["expected_value"]
    variance = value["variance_of_value"]
    phi_events = dispersion["points_events"]
    implied = (variance + phi_events * ev**2) / ev

    grouped = clean.groupby(["season", "athlete_id", "minute_cell"], sort=False)
    sizes = grouped["minutes"].transform("size").to_numpy()
    inside = sizes >= 2
    points = (clean["points"].to_numpy(dtype=float) - grouped["points"].transform("mean").to_numpy())[inside]
    threes = (clean["threes"].to_numpy(dtype=float) - grouped["threes"].transform("mean").to_numpy())[inside]
    correlation = float(np.corrcoef(points, threes)[0, 1]) if points.size > 2 else float("nan")

    return (
        {
            "unconditional_points_vmr_regulars": float(unconditional),
            "points_vmr_given_minutes": float(conditional),
            "compound_implied_points_vmr_given_minutes": float(implied),
            "compound_reproduction_ratio": float(implied / conditional) if conditional else float("nan"),
            "corr_points_threes_given_minutes": correlation,
        },
        {
            "unconditional_rows": unconditional_rows,
            "correlation_rows": int(inside.sum()),
            "regular_min_projected_minutes": REGULAR_MIN_PROJECTED_MINUTES,
            "compound_note": (
                "`compound_implied` is (Var[V] + phi_N E[V]^2)/E[V] -- what a "
                "compound sum of `phi_N`-dispersed events each worth 1, 2 or 3 "
                "points produces, with nothing fitted to the points column at all. "
                "The ratio to the measured conditional points VMR is the free "
                "structural check the design asks to be reported and not tuned."
            ),
        },
    )


def dnp_base_rates(trailing: pd.DataFrame) -> tuple[list[float], list[int], dict]:
    """Per-bucket base rate of a did-not-play, as the shrink target for a diagnostic.

    Stored because the design's section 9 stores `dnp_probability` on every row
    and a per-player estimate needs somewhere to shrink to. It is a
    **diagnostic**: the minutes lattice carries exactly zero mass at zero
    minutes, and this number is never multiplied into a price. A did-not-play
    voids the wager rather than losing it, and this lab has no availability
    source for this sport at all, so a number here is a base rate and not a
    forecast anyone should act on.
    """
    eligible = trailing[
        trailing["projected_minutes"].notna()
        & (trailing["prior_games"] >= MIN_PRIOR_GAMES)
        & (trailing["prior_minutes"] >= MIN_PRIOR_MINUTES)
    ]
    bucket = eligible["bucket"].to_numpy()
    absent = (~eligible["appeared"]).to_numpy()
    rates: list[float] = []
    counts: list[int] = []
    for index in range(len(BUCKET_LABELS)):
        inside = bucket == index
        counts.append(int(inside.sum()))
        rates.append(float(absent[inside].mean()) if inside.sum() else float("nan"))
    return rates, counts, {
        "population": (
            "every roster row -- appeared or not -- carrying four prior "
            "appearances and sixty prior minutes. The projection on a "
            "did-not-play row is the projection as of the last game the player "
            "actually appeared in."
        ),
        "rows": int(len(eligible)),
        "absences": int(absent.sum()),
    }


# --------------------------------------------------------------------------
# The fit
# --------------------------------------------------------------------------


@dataclass
class Window:
    """Everything one season-window contributes, computed once."""

    prepared: pd.DataFrame
    played: pd.DataFrame
    trailing: pd.DataFrame
    evidence: pd.DataFrame
    priced: pd.DataFrame
    bank: pd.DataFrame
    clean: pd.DataFrame
    census: dict
    sha: str
    evidence_sha: str
    priced_sha: str
    clean_sha: str


def build_window(
    frame: pd.DataFrame, prior_season_games: Mapping[tuple[int, float], int]
) -> Window:
    prepared = prepare(frame)
    trailing = with_trailing(prepared, MINUTES_HALF_LIFE)
    played = prepared[prepared["played"]]
    evidence = evidence_population(trailing)
    priced = evidence[evidence["projected_minutes"] >= MIN_PROJECTED_MINUTES].copy()
    clean = dispersion_population(trailing, prior_season_games)
    return Window(
        prepared=prepared,
        played=played,
        trailing=trailing,
        evidence=evidence,
        priced=priced,
        bank=bank_population(trailing),
        clean=clean,
        census=census(prepared),
        sha=rows_sha256(played),
        evidence_sha=rows_sha256(evidence),
        priced_sha=rows_sha256(priced),
        clean_sha=rows_sha256(clean),
    )


def prior_season_game_counts(path: Path, seasons: Sequence[int]) -> dict[tuple[int, float], int]:
    """Played games per (season, athlete), for the prior-season selection in L9.

    Reads only seasons already inside the permitted window. The season before the
    earliest one available is simply not there, and every athlete in it is
    admitted rather than dropped -- see `dispersion_population`.
    """
    frame = _load_seasons(path, seasons, what="prior-season game counts")
    prepared = prepare(frame)
    played = prepared[prepared["played"]]
    counts = played.groupby(["season", "athlete_id"], sort=False).size()
    return {(int(s), float(a)): int(n) for (s, a), n in counts.items()}


def design_reproduction(frame: pd.DataFrame, counts: Mapping[tuple[int, float], int]) -> dict:
    """The design's published numbers, re-measured on the design's own two seasons.

    The adjudicated design fitted on 2021 and 2022 and published a value pmf, a
    table of conditional dispersions and a half-life curve. Comparing those
    against a fit over 2019-2022 would confound a window difference with a method
    difference, so they are re-measured here on 2021-2022 exactly. This block is
    a check on the design, not a source of any frozen constant, and nothing in
    `constants` reads it.
    """
    window = build_window(frame, counts)
    pmf, evidence = value_pmf(window.played)
    dispersion, dispersion_report = conditional_dispersions(window.clean, window.played)
    correlations, _ = residual_correlations(window.clean)
    targets, _ = structural_targets(window.clean, window.priced, dispersion, evidence)
    compound, _ = compound_reconciliation(dispersion, evidence)
    return {
        "residual_correlation": correlations,
        "design_published_residual_correlation": {
            "points|rebounds": 0.10, "points|assists": 0.01, "rebounds|assists": 0.07,
        },
        "structural_check_targets": targets,
        "design_published_structural": {"unconditional_points_vmr_regulars": 2.991},
        "points_compound_reconciliation": compound,
        "seasons": sorted(int(s) for s in frame["season"].unique()),
        "note": (
            "Re-measured on the design's own fit window so its published numbers "
            "are checked on their own ground. Not a source of any frozen constant."
        ),
        "census": window.census,
        "value_pmf": {"measured": pmf, "design_published": [0.3303, 0.4754, 0.1943],
                      "evidence": evidence},
        "conditional_dispersion": {
            market: {
                "measured_within_player_minute_cell": dispersion[market],
                "measured_on_the_design_band": dispersion_report[market]["design_band_value"],
                "measured_pearson_all_minutes": dispersion_report[market]["pearson_dispersion_all_minutes"],
            }
            for market in COUNT_MARKETS
        },
        "design_published_dispersion": {
            "points_family_residual_over_compound": 1.11,
            "rebounds": 1.15,
            "assists": 1.16,
            "threes": 1.09,
            "steals": 1.05,
            "turnovers": 0.97,
        },
        "minutes_half_life_curve": minutes_half_life_curve(window.prepared),
        "design_published_half_life_rmse": {
            "half_life_2": 6.393, "half_life_3": 6.395, "half_life_4": 6.423,
            "half_life_5": 6.453, "half_life_8": 6.523, "flat_trailing_mean": 6.721,
        },
    }


def _refused_ratios(fitted: Mapping[str, float], report: Mapping[str, dict]) -> list[float]:
    """priced-population k divided by the R2-refused bank's k, per market."""
    out: list[float] = []
    for market, entry in report.items():
        low = entry["outside_the_priced_population_10_to_60"]["k"]
        if low and fitted.get(market):
            out.append(float(fitted[market]) / float(low))
    return out or [float("nan")]


def _widest_spread(report: Mapping[str, dict]) -> tuple[str, float]:
    """The market whose k moves most across the evidence banks that could be checked."""
    best = ("", 0.0)
    for market, entry in report.items():
        spread = entry["spread_across_checked_banks"]
        if spread is not None and spread > best[1]:
            best = (market, float(spread))
    return best


def design_disagreements(reproduction: Mapping) -> list[dict]:
    """Where a re-measured number differs from the one the design published.

    Measured on the design's own two seasons, so a window difference cannot be
    mistaken for a method difference. Each entry carries the design's value, the
    measured one, the tolerance the design itself declared, and what the gap
    costs -- because a disagreement with no consequence attached is a complaint
    rather than a finding.
    """
    if "value_pmf" not in reproduction:
        return []
    out: list[dict] = []

    measured = reproduction["value_pmf"]["measured"]
    published = reproduction["value_pmf"]["design_published"]
    worst = max(abs(a - b) for a, b in zip(measured, published))
    out.append(
        {
            "quantity": "value_pmf",
            "design": published,
            "measured": measured,
            "gap": worst,
            "tolerance": 0.005,
            "agrees": worst <= 0.005,
            "consequence": (
                "none -- it reproduces to four decimal places, which also confirms "
                "that a scoring event is being counted the same way here as there "
                "(a made free throw, a made two, a made three)."
            ),
        }
    )

    published_dispersion = reproduction["design_published_dispersion"]
    for market, entry in reproduction["conditional_dispersion"].items():
        if market in {"points", "points_events"}:
            continue
        target = published_dispersion.get(market)
        if target is None:
            continue
        measured_value = entry["measured_within_player_minute_cell"]
        gap = abs(measured_value - target)
        out.append(
            {
                "quantity": f"conditional_dispersion.{market}",
                "design": target,
                "measured": measured_value,
                "gap": gap,
                "tolerance": 0.05,
                "agrees": gap <= 0.05,
                "consequence": (
                    "the Panjer member is unchanged and the width moves by less than "
                    "the design's own tolerance."
                    if gap <= 0.05
                    else (
                        "outside the design's own reproduction gate. The frozen value "
                        "is the measured one; nothing was moved toward the published "
                        "figure."
                    )
                ),
            }
        )

    # The points family, read both ways. The design published one number and
    # there are two quantities it could name; one of them reproduces, and a
    # Panjer family would naturally consume the other.
    compound = reproduction["points_compound_reconciliation"]
    target = published_dispersion["points_family_residual_over_compound"]
    effective = compound["effective_event_dispersion"]
    out.append(
        {
            "quantity": "points_compound_reconciliation.effective_event_dispersion",
            "design": target,
            "measured": effective,
            "gap": abs(effective - target),
            "tolerance": 0.05,
            "agrees": abs(effective - target) <= 0.05,
            "consequence": (
                "read as the dispersion that makes an iid compound sum reproduce the "
                "measured conditional points VMR -- which is what 'residual over "
                "compound' says -- the design's number reproduces inside its own gate."
            ),
        }
    )
    measured_events = compound["measured_event_dispersion"]
    out.append(
        {
            "quantity": "conditional_dispersion.points_events",
            "design": target,
            "measured": measured_events,
            "gap": abs(measured_events - target),
            "tolerance": 0.05,
            "agrees": abs(measured_events - target) <= 0.05,
            "consequence": (
                "the scoring-event count's OWN dispersion. It is not the quantity the "
                "design published and cannot be substituted for it -- but a Panjer "
                "family consumes a phi on the count, so this is the number an "
                "implementer will reach for, and feeding it through the compound "
                "identity produces a points marginal about "
                f"{(compound['compound_overstatement'] - 1) * 100:.0f}% too wide in "
                "variance. Free throws arrive in pairs: two made free throws are two "
                "scoring events, and an iid compound sum charges them two independent "
                "draws from the value pmf when in the game they are one trip to the "
                "line. Exchangeable events is the assumption that fails, and it fails "
                "in the direction observed. Both numbers are frozen under "
                "`points_compound_reconciliation`; the choice belongs to the model."
            ),
        }
    )

    published_correlation = reproduction["design_published_residual_correlation"]
    for key, target in published_correlation.items():
        measured_value = reproduction["residual_correlation"].get(key)
        if measured_value is None:
            continue
        gap = abs(measured_value - target)
        out.append(
            {
                "quantity": f"residual_correlation.{key}",
                "design": target,
                "measured": measured_value,
                "gap": gap,
                "tolerance": 0.02,
                "agrees": gap <= 0.02,
                "consequence": (
                    "the copula off-diagonal is small either way and a pra interval "
                    "moves by well under a percent."
                    if gap <= 0.02
                    else (
                        "the sign is not the design's. Points and assists are very "
                        "slightly NEGATIVELY correlated once player and realised "
                        "minutes are held fixed -- a possession a player finishes is a "
                        "possession he did not pass -- so a copula built on +0.01 "
                        "widens the points_assists and pra sums where the data says to "
                        "narrow them. The effect is small; the sign error is not the "
                        "kind of thing to leave in a frozen file."
                    )
                ),
            }
        )

    target = reproduction["design_published_structural"]["unconditional_points_vmr_regulars"]
    measured_value = reproduction["structural_check_targets"]["unconditional_points_vmr_regulars"]
    gap = abs(measured_value - target)
    out.append(
        {
            "quantity": "structural_check_targets.unconditional_points_vmr_regulars",
            "design": target,
            "measured": measured_value,
            "gap": gap,
            "tolerance": 0.15 * target,
            "agrees": gap <= 0.15 * target,
            "consequence": (
                "this is the target the assembled mixture must reproduce, not a "
                "parameter. The two populations are defined slightly differently "
                "(rotation regulars here means fifteen projected minutes and a "
                "prior-season selection) and the numbers are close enough that the "
                "design's 15% stop rule is not at risk from the target itself."
            ),
        }
    )

    curve = reproduction["minutes_half_life_curve"]["rmse"]
    published_curve = reproduction["design_published_half_life_rmse"]
    out.append(
        {
            "quantity": "minutes_half_life_curve",
            "design": published_curve,
            "measured": curve,
            "gap": max(abs(curve[k] - published_curve[k]) for k in published_curve if k in curve),
            "tolerance": None,
            "agrees": None,
            "consequence": (
                "the design published no tolerance for this curve and declared the "
                "half-life rather than selecting it, so nothing turns on the gap. The "
                "shape agrees: flat from 2 to 5, clearly worse at 8, clearly worse "
                "still at a flat trailing mean. The argmin differs (2 there, 3 here) "
                "which is exactly the design's own argument for not selecting on it."
            ),
        }
    )
    return out


def fit(input_path: Path, fit_seasons: Sequence[int], validation_season: int) -> dict:
    _check_window(list(fit_seasons) + [validation_season], what="the requested windows")
    if validation_season in fit_seasons:
        raise FitError(
            f"season {validation_season} is both fitted and held out. A holdout "
            "that is in the fit is not a holdout."
        )

    permitted = sorted(set(fit_seasons) | {validation_season})
    counts = prior_season_game_counts(input_path, permitted)

    permitted_frame = _load_seasons(input_path, permitted, what="the permitted window")
    permitted_census = census(prepare(permitted_frame))

    fitw = build_window(
        _load_seasons(input_path, fit_seasons, what="the fit window"), counts
    )
    holdw = build_window(
        _load_seasons(input_path, [validation_season], what="the holdout window"), counts
    )
    sub_seasons = [s for s in DESIGN_SUBWINDOW if s in set(fit_seasons)]
    reproduction = (
        design_reproduction(
            _load_seasons(input_path, sub_seasons, what="the design's own sub-window"), counts
        )
        if sub_seasons
        else {"note": "the design's fit seasons are not inside this run's fit window"}
    )

    constants: dict[str, Constant] = {}
    unfittable: dict[str, dict] = {}

    def add(name: str, **kwargs) -> None:
        constants[name] = Constant(name=name, **kwargs)

    # --- minutes ---------------------------------------------------------
    fit_curve = minutes_half_life_curve(fitw.prepared)
    hold_curve = minutes_half_life_curve(holdw.prepared)
    add(
        "minutes_half_life",
        value=MINUTES_HALF_LIFE,
        held_out_value=MINUTES_HALF_LIFE,
        sample_size=fit_curve["rows"],
        held_out_sample_size=hold_curve["rows"],
        input_sha256=fitw.priced_sha,
        held_out_sha256=holdw.priced_sha,
        units="games",
        material_absolute=0.0,
        provenance="declared before the curve was looked at; the curve is evidence, not the choice",
        note=(
            "The RMSE curve is flat across half-lives 2 to 5 -- "
            f"{fit_curve['relative_spread_across_half_lives'] * 100:.2f}% between best "
            "and worst on the fit window. The argmin on this window is "
            f"{fit_curve['argmin']} on the fit and {hold_curve['argmin']} on the "
            "holdout, and it is not 4. Declaring 4 anyway is the point: the design's "
            "account of the earlier attempt is that a half-life was chosen by 0.08% "
            "on the season it called held out, 'which is how you spend a holdout on "
            "nothing'. The cost of the declaration is "
            f"{fit_curve['cost_of_the_declaration']:.4f} minutes of RMSE."
        ),
        extra={"fit_window_curve": fit_curve, "held_out_curve": hold_curve},
    )

    fit_pmf, fit_sd, fit_rows, fit_minutes_evidence = minutes_shapes(fitw.evidence)
    hold_pmf, hold_sd, hold_rows, hold_minutes_evidence = minutes_shapes(holdw.evidence)
    add(
        "minutes_pmf",
        value={
            "support_low": MINUTES_SUPPORT_LOW,
            "support_high": MINUTES_SUPPORT_HIGH,
            "buckets": list(BUCKET_LABELS),
            "pmf": fit_pmf,
        },
        held_out_value={
            "support_low": MINUTES_SUPPORT_LOW,
            "support_high": MINUTES_SUPPORT_HIGH,
            "buckets": list(BUCKET_LABELS),
            "pmf": hold_pmf,
        },
        sample_size=int(sum(fit_rows)),
        held_out_sample_size=int(sum(hold_rows)),
        input_sha256=fitw.evidence_sha,
        held_out_sha256=holdw.evidence_sha,
        units="probability per integer minute",
        material_absolute=0.004,
        provenance="empirical, per projected-minutes bucket",
        note=(
            "Mass at zero minutes is exactly zero by construction, not by rounding: "
            "the book voids a did-not-play, so the priced quantity is conditional on "
            "the player appearing. Minutes above 45 are folded onto 45 and the count "
            "is in the evidence. Fitted on the R2 population rather than the priced "
            "one, so the bottom bucket -- which R3 refuses to price -- still has a "
            "shape a later session can look at."
        ),
        extra={
            "rows_per_bucket": fit_rows,
            "held_out_rows_per_bucket": hold_rows,
            "fit": fit_minutes_evidence,
            "held_out": hold_minutes_evidence,
        },
    )
    add(
        "minutes_residual_sd",
        value=fit_sd,
        held_out_value=hold_sd,
        sample_size=int(sum(fit_rows)),
        held_out_sample_size=int(sum(hold_rows)),
        input_sha256=fitw.evidence_sha,
        held_out_sha256=holdw.evidence_sha,
        units="minutes",
        material_absolute=0.0,
        provenance="measured per projected-minutes bucket",
        note=(
            "Read per bucket, never as one number. A thirty-four-minute starter's "
            "minutes and a ten-minute reserve's do not disperse alike and a single "
            "SD would be wrong about both."
        ),
        extra={"buckets": list(BUCKET_LABELS), "rows_per_bucket": fit_rows},
    )

    # --- role prior ------------------------------------------------------
    fit_priors, fit_prior_rows, fit_prior_shape = role_priors(fitw.evidence)
    hold_priors, hold_prior_rows, hold_prior_shape = role_priors(holdw.evidence)
    add(
        "role_prior",
        value=fit_priors,
        held_out_value=hold_priors,
        sample_size=int(sum(fit_prior_rows)),
        held_out_sample_size=int(sum(hold_prior_rows)),
        input_sha256=fitw.evidence_sha,
        held_out_sha256=holdw.evidence_sha,
        units="stat per minute",
        material_absolute=0.002,
        provenance="minutes-weighted, by projected-minutes bucket",
        note=(
            "Nine buckets by projected minutes, one table per market, allowed to run "
            "downward -- and rebounds does run downward, from "
            f"{fit_priors['rebounds'][1]:.4f} per minute in the 8-12 bucket to "
            f"{fit_priors['rebounds'][8]:.4f} at 36+. A monotone functional form "
            "would have been wrong about that forever. The bucket is projected, "
            "never realised, so nothing here reads the game it is fitted on."
        ),
        extra={
            "buckets": list(BUCKET_LABELS),
            "rows_per_bucket": fit_prior_rows,
            "fit": fit_prior_shape,
            "held_out": hold_prior_shape,
        },
    )

    # --- credibility -----------------------------------------------------
    fit_k, fit_k_report, k_unfittable = credibility(fitw.priced, fitw.bank, fit_priors)
    hold_k, hold_k_report, hold_k_unfittable = credibility(holdw.priced, holdw.bank, hold_priors)
    add(
        "rate_shrinkage_k",
        value={m: v for m, v in fit_k.items() if m not in k_unfittable},
        held_out_value={m: v for m, v in hold_k.items() if m not in k_unfittable},
        sample_size=int(len(fitw.priced)),
        held_out_sample_size=int(len(holdw.priced)),
        input_sha256=fitw.priced_sha,
        held_out_sha256=holdw.priced_sha,
        units="prior minutes",
        material_absolute=2.0,
        provenance="minimises the model's own out-of-sample minutes-weighted forecast error",
        note=(
            "`w = M/(M+k)` on prior minutes. The design's stability gate was declared "
            "over evidence banks from 10 to 900 prior minutes; inside the priced "
            "population the 10-60 bank is empty, because the design's own R2 refuses "
            "a player with fewer than sixty prior minutes. What was actually checked "
            "is 60-900, and the refused bank is fitted separately and reported as "
            "`outside_the_priced_population_10_to_60`. Calling the one a test of the "
            "other would have been false."
        ),
        extra={
            "fit": fit_k_report,
            "held_out": hold_k_report,
            "refused_markets": sorted(k_unfittable),
            "held_out_would_refuse": sorted(hold_k_unfittable),
            "gate_as_declared": "stable within 2x across evidence banks from 10 to 900 prior minutes",
            "gate_as_run": (
                "stable within 2x across evidence banks from 60 to 900 prior minutes; "
                "the 10-60 bank does not exist inside the priced population"
            ),
        },
    )
    for market, reason in k_unfittable.items():
        unfittable[f"rate_shrinkage_k.{market}"] = {
            "reason": reason,
            "cost": (
                f"the model has no fitted credibility weight for {market}, so it "
                "cannot form a per-minute rate for it. Every market that reads "
                f"{market} is refused for the whole season rather than priced on an "
                "invented constant."
            ),
            "evidence": fit_k_report.get(market, {}),
        }

    # --- the value of a scoring event ------------------------------------
    fit_value, fit_value_evidence = value_pmf(fitw.played)
    hold_value, hold_value_evidence = value_pmf(holdw.played)
    add(
        "value_pmf",
        value=fit_value,
        held_out_value=hold_value,
        sample_size=fit_value_evidence["scoring_events"],
        held_out_sample_size=hold_value_evidence["scoring_events"],
        input_sha256=fitw.sha,
        held_out_sha256=holdw.sha,
        units="probability that a scoring event is worth 1, 2 or 3 points",
        material_absolute=0.002,
        provenance="every scoring event in the window",
        note=(
            "What makes the points family a compound sum rather than a count, and "
            "why `player_threes` falls out of the same object as `player_points` "
            "instead of being a second model. E[V^2]/E[V] is "
            f"{fit_value_evidence['second_moment_over_first']:.4f} -- the "
            "variance-to-mean a Poisson event count alone would produce -- against a "
            "measured unconditional points VMR near 3.0. The gap is the minutes "
            "mixture's, and the design requires it to be produced rather than fitted. "
            "The implied point total reconciles to "
            f"{fit_value_evidence['reconciliation_gap_points']:.0f} points out of "
            f"{fit_value_evidence['actual_point_total']:.0f}."
        ),
        extra={"fit": fit_value_evidence, "held_out": hold_value_evidence},
    )
    fit_mix_k, fit_mix_evidence = value_mix_shrinkage(fitw.priced, fit_value)
    hold_mix_k, hold_mix_evidence = value_mix_shrinkage(holdw.priced, hold_value)
    add(
        "value_mix_shrinkage_events",
        value=fit_mix_k,
        held_out_value=hold_mix_k,
        sample_size=fit_mix_evidence["rows"],
        held_out_sample_size=hold_mix_evidence["rows"],
        input_sha256=fitw.priced_sha,
        held_out_sha256=holdw.priced_sha,
        units="prior scoring events",
        material_absolute=0.5,
        provenance="minimises out-of-sample multinomial deviance of the next game's mix",
        note=(
            "A centre and a shooting guard do not score the same way, and this is how "
            "far a player is allowed to differ from the league shape. Small, which "
            "says the player's own mix is informative early: at "
            f"{fit_mix_k:.1f} prior scoring events the weight on his own mix is "
            "already a half."
        ),
        extra={"fit": fit_mix_evidence, "held_out": hold_mix_evidence},
    )

    # --- dispersion ------------------------------------------------------
    fit_dispersion, fit_dispersion_report = conditional_dispersions(fitw.clean, fitw.played)
    hold_dispersion, hold_dispersion_report = conditional_dispersions(holdw.clean, holdw.played)
    add(
        "conditional_dispersion",
        value=fit_dispersion,
        held_out_value=hold_dispersion,
        sample_size=int(len(fitw.clean)),
        held_out_sample_size=int(len(holdw.clean)),
        input_sha256=fitw.clean_sha,
        held_out_sha256=holdw.clean_sha,
        units="variance-to-mean of the count, given realised minutes",
        material_absolute=0.02,
        provenance="pooled within (season, athlete, realised minute), dof-corrected",
        note=(
            "Selects the Panjer member: below 1 a binomial, at 1 a Poisson, above 1 a "
            "negative binomial. A market genuinely below 1 is not a rounding error -- "
            f"turnovers measures {fit_dispersion['turnovers']:.4f} here and "
            f"{hold_dispersion['turnovers']:.4f} held out, and a negative binomial "
            "cannot represent that at all. `points` is measured but is NOT the "
            "parameter: the points family is a compound sum and its dispersion "
            "constant is `points_events`, which measures "
            f"{fit_dispersion['points_events']:.2f} here. The design published 1.11 "
            "for the 'points family (residual over compound)'; that is a different "
            "quantity, not a second answer to this one, and "
            "`points_compound_reconciliation` holds both with the reason they differ."
        ),
        extra={"fit": fit_dispersion_report, "held_out": hold_dispersion_report},
    )

    fit_compound, fit_compound_evidence = compound_reconciliation(fit_dispersion, fit_value_evidence)
    hold_compound, hold_compound_evidence = compound_reconciliation(hold_dispersion, hold_value_evidence)
    add(
        "points_compound_reconciliation",
        value=fit_compound,
        held_out_value=hold_compound,
        sample_size=int(len(fitw.clean)),
        held_out_sample_size=int(len(holdw.clean)),
        input_sha256=fitw.clean_sha,
        held_out_sha256=holdw.clean_sha,
        units="variance-to-mean of the scoring-event count; dimensionless ratios",
        material_absolute=0.02,
        provenance="derived from `conditional_dispersion` and `value_pmf`, nothing newly fitted",
        note=(
            "THE LARGEST STRUCTURAL FINDING IN THIS FILE. An iid compound sum over the measured "
            "scoring-event dispersion of "
            f"{fit_compound['measured_event_dispersion']:.3f} predicts a conditional "
            f"points VMR of {fit_compound['compound_implied_points_vmr']:.3f}; the "
            f"measured one is {fit_compound['measured_points_vmr_given_minutes']:.3f}, "
            f"so the structure overstates the points variance by "
            f"{(fit_compound['compound_overstatement'] - 1) * 100:.0f}%. Free throws "
            "arrive in pairs: two made free throws are two scoring events, and an iid "
            "compound sum charges them two independent draws from the value pmf when "
            "in the game they are one trip to the line. Exchangeable events is the "
            "assumption that fails, and it fails in the direction observed. Both "
            "numbers are frozen and the choice between them belongs to the model, not "
            "to the fit. The design's published 1.11 is the SECOND of these: it "
            f"reproduces as `effective_event_dispersion` = "
            f"{fit_compound['effective_event_dispersion']:.3f} here and 1.079 on the "
            "design's own two seasons, inside its own +/-0.05 gate. It is not the "
            "event count's dispersion and must not be handed to a Panjer family as one."
        ),
        extra={"fit": fit_compound_evidence, "held_out": hold_compound_evidence},
    )

    fit_corr, fit_corr_evidence = residual_correlations(fitw.clean)
    hold_corr, hold_corr_evidence = residual_correlations(holdw.clean)
    add(
        "residual_correlation",
        value=fit_corr,
        held_out_value=hold_corr,
        sample_size=fit_corr_evidence["rows"],
        held_out_sample_size=hold_corr_evidence["rows"],
        input_sha256=fitw.clean_sha,
        held_out_sha256=holdw.clean_sha,
        units="Pearson correlation of counts, given player-season and realised minute",
        material_absolute=0.02,
        provenance="residuals within (season, athlete, realised minute)",
        note=(
            "The Gaussian copula's off-diagonals, and the reason the combination "
            "markets are built from components over a shared minutes draw. "
            "Conditioning on the realised minute is load-bearing: on trailing minutes "
            "these run around 0.4 and nearly all of it is the minutes channel the "
            "mixture already carries. Applying it twice makes every pra interval too "
            "wide and under-prices every pra over. `points|assists` comes out "
            f"{fit_corr['points|assists']:+.4f} -- the design published +0.01, and the "
            "sign is not the same."
        ),
        extra={"fit": fit_corr_evidence, "held_out": hold_corr_evidence},
    )

    fit_struct, fit_struct_evidence = structural_targets(
        fitw.clean, fitw.priced, fit_dispersion, fit_value_evidence
    )
    hold_struct, hold_struct_evidence = structural_targets(
        holdw.clean, holdw.priced, hold_dispersion, hold_value_evidence
    )
    add(
        "structural_check_targets",
        value=fit_struct,
        held_out_value=hold_struct,
        sample_size=fit_struct_evidence["unconditional_rows"],
        held_out_sample_size=hold_struct_evidence["unconditional_rows"],
        input_sha256=fitw.priced_sha,
        held_out_sha256=holdw.priced_sha,
        units="variance-to-mean; Pearson correlation",
        material_absolute=0.02,
        provenance="measured, and never fitted to",
        note=(
            "Not parameters. These are what the assembled mixture has to reproduce "
            "with nothing tuned to them, and the design stops the run if the "
            "unconditional points VMR is missed by more than 15%. "
            "`compound_reproduction_ratio` is what the compound structure predicts "
            "for the conditional points VMR divided by what was measured: "
            f"{fit_struct['compound_reproduction_ratio']:.4f} on the fit window."
        ),
        extra={"fit": fit_struct_evidence, "held_out": hold_struct_evidence},
    )

    fit_dnp, fit_dnp_rows, fit_dnp_evidence = dnp_base_rates(fitw.trailing)
    hold_dnp, hold_dnp_rows, hold_dnp_evidence = dnp_base_rates(holdw.trailing)
    add(
        "dnp_base_rate",
        value=fit_dnp,
        held_out_value=hold_dnp,
        sample_size=int(sum(fit_dnp_rows)),
        held_out_sample_size=int(sum(hold_dnp_rows)),
        input_sha256=rows_sha256(fitw.trailing),
        held_out_sha256=rows_sha256(holdw.trailing),
        units="probability of a did-not-play",
        material_absolute=0.01,
        provenance="measured per projected-minutes bucket",
        note=(
            "DIAGNOSTIC ONLY. The shrink target for a stored `dnp_probability`. It is "
            "never multiplied into a price: the minutes lattice carries exactly zero "
            "mass at zero minutes, because a did-not-play voids the wager rather than "
            "losing it. This lab has no availability source for this sport -- the "
            "ESPN injuries endpoint is permanently empty and no conference report "
            "covers November -- so a number here is a base rate, not a forecast "
            "anyone should act on."
        ),
        extra={
            "buckets": list(BUCKET_LABELS),
            "rows_per_bucket": fit_dnp_rows,
            "fit": fit_dnp_evidence,
            "held_out": hold_dnp_evidence,
        },
    )

    document = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "generated_by": "scripts/fit_player_model.py",
        "never_runs_at_price_time": True,
        "price_season_floor": PRICE_SEASON,
        "fit_seasons": [int(s) for s in fit_seasons],
        "fitted_through": int(max(fit_seasons)),
        "validation_season": int(validation_season),
        "input": {
            "path": (
                str(input_path.relative_to(REPO_ROOT))
                if input_path.is_relative_to(REPO_ROOT)
                else str(input_path)
            ),
            "permitted_window": permitted,
            "permitted_window_census": permitted_census,
            "fit_census": fitw.census,
            "held_out_census": holdw.census,
            "fit_slice_sha256": fitw.sha,
            "held_out_slice_sha256": holdw.sha,
        },
        "declared": {
            "bucket_edges": list(BUCKET_EDGES),
            "bucket_labels": list(BUCKET_LABELS),
            "refusal_thresholds": {
                "min_prior_games": MIN_PRIOR_GAMES,
                "min_prior_minutes": MIN_PRIOR_MINUTES,
                "min_projected_minutes": MIN_PROJECTED_MINUTES,
            },
            "minutes_support": [MINUTES_SUPPORT_LOW, MINUTES_SUPPORT_HIGH],
            "prior_season_min_games": PRIOR_SEASON_MIN_GAMES,
            "overtime_is_included": (
                "These constants are measured on box scores that include overtime "
                "(about 5.8% of games, scoring roughly 18.5% faster per minute). That "
                "is correct for a marginal predictive distribution and wrong the "
                "moment anyone conditions on regulation. Written down so a later "
                "session does not assume otherwise."
            ),
        },
        "constants": {
            name: constant.to_json(fit_seasons=fit_seasons, validation_season=validation_season)
            for name, constant in constants.items()
        },
        "unfittable": unfittable,
        "disagreements": {
            name: constant.disagreement()
            for name, constant in constants.items()
            if constant.disagreement() is not None
        },
        "design_reproduction": reproduction,
        "design_disagreements": design_disagreements(reproduction),
        "caveats": [
            (
                "The credibility gate could not be run as declared. The design asks "
                "for k to be stable within 2x across evidence banks from 10 to 900 "
                "prior minutes; the design's own R2 refusal empties the 10-60 bank "
                "inside every population the model prices, so the gate that ran covers "
                "60-900. The refused bank was fitted separately anyway, on rows no "
                "price is ever formed from, and it does not overturn the gate: k comes "
                "out lower there for every market, by "
                f"{min(_refused_ratios(fit_k, fit_k_report)):.2f}x to "
                f"{max(_refused_ratios(fit_k, fit_k_report)):.2f}x, all inside 2x of "
                "the priced-population value. Reported under "
                "`rate_shrinkage_k.evidence.fit.<market>."
                "outside_the_priced_population_10_to_60`."
            ),
            (
                f"`{_widest_spread(fit_k_report)[0]}` has the widest credibility spread "
                f"of any market at {_widest_spread(fit_k_report)[1]:.2f}x -- see "
                "`rate_shrinkage_k` -- and it passes the 2x gate rather than clearing "
                "it. A later session tightening that gate should expect it to be the "
                "first market to fail."
            ),
            (
                "Season 2020 was cut short on 2019-11-05 to 2020-03-11 and season 2021 "
                "was played under COVID scheduling. Both are in the fit window. Their "
                "rows are not reweighted and no season effect is fitted; a constant "
                "here is an average over four seasons two of which were unusual, and "
                "the holdout season 2023 is not."
            ),
            (
                "Every constant is measured on box scores that include overtime. "
                "Correct for a marginal predictive distribution, wrong the moment "
                "anyone conditions on regulation."
            ),
            (
                "No constant here says anything about whether a player will appear. "
                "This lab has no availability source for this sport at all, and "
                "`dnp_base_rate` is a base rate stored as a diagnostic, never a "
                "forecast and never multiplied into a price."
            ),
        ],
    }
    return jsonable(document)


# --------------------------------------------------------------------------
# Report
# --------------------------------------------------------------------------


def _render(document: Mapping) -> str:
    lines = ["=" * 78, "PLAYER-PROP SHAPES -- fitted, held out, and frozen", "=" * 78]
    lines.append(
        f"fit seasons {document['fit_seasons']}   fitted_through "
        f"{document['fitted_through']}   held out {document['validation_season']}   "
        f"never read {document['price_season_floor']}+"
    )
    inp = document["input"]
    for label, key in (("permitted", "permitted_window_census"), ("fit", "fit_census"), ("holdout", "held_out_census")):
        c = inp[key]
        lines.append(
            f"  {label:<10} {c['rows']:>8,} rows  {c['played_rows']:>8,} played  "
            f"{c['athletes']:>7,} athletes  {c['did_not_play_rows']:>7,} dnp  "
            f"{c['appeared_but_no_minutes_rows']:>5,} appeared-without-minutes"
        )
    lines.append("")
    for name, payload in document["constants"].items():
        lines.append(
            f"--- {name}   n={payload['sample_size']:,}   holdout n={payload['held_out_sample_size']:,}"
        )
        for label, fitted, held in _numeric_pairs(payload["value"], payload["held_out_value"]):
            if label.startswith("pmf["):
                continue
            flag = ""
            if (
                abs(fitted - held) > payload["material_absolute"]
                and max(abs(fitted), abs(held)) > 0
                and abs(fitted - held) / max(abs(fitted), abs(held)) > DISAGREEMENT_RELATIVE
            ):
                flag = "   <-- DISAGREES"
            lines.append(f"      {(label or name):<46} {fitted: 12.5f}   {held: 12.5f}{flag}")
        lines.append("")

    lines.append("CREDIBILITY STABILITY (the design's gate, and how far it could be run):")
    for market, entry in document["constants"]["rate_shrinkage_k"]["evidence"]["fit"].items():
        spread = entry["spread_across_checked_banks"]
        outside = entry["outside_the_priced_population_10_to_60"]
        low = "n/a" if outside["k"] is None else f"{outside['k']:.1f}"
        spread_text = "n/a" if spread is None else f"{spread:.3f}"
        lines.append(
            f"  {market:<16} spread {spread_text} over "
            f"{entry['banks_actually_checked']} banks that exist inside the priced "
            f"population; the R2-refused 10-60 bank holds {outside['rows']:,} rows "
            f"and fits k = {low}"
        )
    lines.append("")

    lines.append("AGAINST THE DESIGN, RE-MEASURED ON THE DESIGN'S OWN SEASONS 2021-2022:")
    rep = document.get("design_reproduction", {})
    if "value_pmf" in rep:
        measured = rep["value_pmf"]["measured"]
        published = rep["value_pmf"]["design_published"]
        lines.append(
            f"  value pmf   measured {measured[0]:.4f}/{measured[1]:.4f}/{measured[2]:.4f}   "
            f"design {published[0]:.4f}/{published[1]:.4f}/{published[2]:.4f}   "
            f"worst gap {max(abs(a - b) for a, b in zip(measured, published)):.4f} "
            "(design's own gate: 0.005)"
        )
        for market, entry in rep["conditional_dispersion"].items():
            published_map = rep["design_published_dispersion"]
            key = "points_family_residual_over_compound" if market == "points_events" else market
            target = published_map.get(key)
            cell = entry["measured_within_player_minute_cell"]
            band = entry["measured_on_the_design_band"]
            pear = entry["measured_pearson_all_minutes"]
            if target is None:
                lines.append(f"  {market:<16} cell {cell:6.3f}  band {band:6.3f}  pearson {pear:6.3f}   (not published)")
            else:
                gap = abs(cell - target)
                flag = "   <-- outside the design's +/-0.05 gate" if gap > 0.05 else ""
                lines.append(
                    f"  {market:<16} cell {cell:6.3f}  band {band:6.3f}  pearson {pear:6.3f}   "
                    f"design {target:.2f}{flag}"
                )
    lines.append("")

    lines.append("WHERE THE RE-MEASUREMENT DISAGREES WITH THE DESIGN:")
    for entry in document.get("design_disagreements", []):
        if entry["agrees"] is True:
            continue
        verdict = "UNRESOLVED" if entry["agrees"] is False else "no tolerance declared"
        lines.append(f"  {entry['quantity']}  [{verdict}]")
        lines.append(f"    design {entry['design']}   measured {entry['measured']}")
        lines.append(f"    {entry['consequence']}")
    lines.append("")

    lines.append("CAVEATS:")
    for caveat in document.get("caveats", []):
        lines.append(f"  - {caveat}")
    lines.append("")

    if document["unfittable"]:
        lines.append("UNFITTABLE -- no value was invented, and the model refuses these:")
        for name, entry in document["unfittable"].items():
            lines.append(f"  {name}: {entry['reason']}")
            lines.append(f"    cost: {entry['cost']}")
    else:
        lines.append(
            "UNFITTABLE: none. Every constant the design asks for was fitted, and the "
            "one gate that could not be run as declared is named above rather than "
            "quietly narrowed."
        )
    lines.append("")
    if document["disagreements"]:
        lines.append("FITTED AND HELD OUT DISAGREE:")
        for name, text in document["disagreements"].items():
            lines.append(f"  {name}: {text}")
    else:
        lines.append(
            f"No constant's fitted and held-out values differ by more than "
            f"{DISAGREEMENT_RELATIVE:.0%} and its absolute floor together."
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").strip().split("\n")[0])
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--fit-seasons", type=int, nargs="+", default=list(FIT_SEASONS))
    parser.add_argument("--holdout-season", type=int, default=VALIDATION_SEASON)
    args = parser.parse_args(argv)

    document = fit(args.input, args.fit_seasons, args.holdout_season)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(_render(document))
    print(f"\nwrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
