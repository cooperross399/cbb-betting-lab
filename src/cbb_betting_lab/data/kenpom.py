"""KenPom's own game projections, read with Cooper's key (decision 96).

Cooper, 2026-11-11, having added the `KENPOM_API_KEY` secret: *"work the
kenpom rankings and stats into the model with the other key stats"*.

KenPom's ratings already enter the card through the second-opinion consensus
(`data/second_opinion.py`, decision 92). This module reads the other half of
what the subscription sells: **FanMatch**, KenPom's projected score for every
game on a day (`endpoint=fanmatch&d=<YYYY-MM-DD>`). A projected score is a
margin and a total in points, which is exactly what the card's
`market_ratings` layer blends toward, so the candidate layer `kenpom`
(`card_factors.CANDIDATE_LAYERS`) blends toward it the same way, at
`card_factors.KENPOM_BLEND_WEIGHT`, when the layer audit adds it.

**Conditioned on what, known when.** One file per slate day,
`data/raw/cbb/kenpom/fanmatch/<day>.csv`, and the card reads the file of the
day it prices and no other: a day is never priced with a projection published
for a later one. A past day's FanMatch is KenPom's projection for that day's
games as the site files it; whether the site revises a past day's projection
after the fact is not established here, so the layer audit's walk-forward over
past days reads it as published and says so (`docs/cbb_data_sources.md`).

**Licence.** KenPom is a paid subscription. Its numbers are read by the model
and never shown on the public site or committed: the raw directory is ignored
by git and carried between runs only in the workflow's own artifact. The key
is sent as a bearer token and never printed, logged or written.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from cbb_betting_lab.data import second_opinion
from cbb_betting_lab.models import card_factors

SOURCE = "kenpom"
API_URL = "https://kenpom.com/api.php"
#: How many days back a run fills in FanMatch files it does not have, so the
#: layer audit's four-week walk-forward has KenPom's projection for every day
#: it re-prices. A day already on disk is never asked for again.
BACKFILL_DAYS = 28
FANMATCH_COLUMNS = (
    "day", "home", "away", "home_id", "away_id", "home_pred", "away_pred", "home_wp", "pred_tempo",
)
#: Field spellings FanMatch uses, after lower-casing and stripping everything
#: but letters (`second_opinion._key`). Read by name, never by position.
FIELD_NAMES = {
    "home": ("home", "hometeam", "homename"),
    "away": ("visitor", "visitorteam", "away", "awayteam", "visitorname"),
    "home_pred": ("homepred", "homepredicted", "homescore", "homepts"),
    "away_pred": ("visitorpred", "awaypred", "visitorpredicted", "visitorscore", "awayscore", "visitorpts"),
    "home_wp": ("homewp", "homewinprob", "homewinprobability", "wp"),
    "pred_tempo": ("predtempo", "tempo", "predictedtempo", "possessions"),
    "day": ("dateofgame", "date", "gamedate"),
}
#: A projected score outside this range is not a college basketball score.
SCORE_RANGE = (30.0, 140.0)


class KenPomError(RuntimeError):
    pass


def fanmatch_path(raw_dir: Path | str | None, day: str) -> Path:
    """Where the card reads it (`card_factors.kenpom_path`), so the two agree."""
    return card_factors.kenpom_path(raw_dir, day)


def fetch(api_key: str, endpoint: str, **params) -> bytes:
    """One KenPom API answer. The key goes in the Authorization header only."""
    if not api_key:
        raise KenPomError("no KenPom key")
    query = "&".join([f"endpoint={endpoint}"] + [f"{k}={v}" for k, v in params.items()])
    try:
        return second_opinion._get(
            f"{API_URL}?{query}",
            headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        )
    except second_opinion.SecondOpinionError as exc:
        raise KenPomError(str(exc)) from exc


def rows_of(payload: bytes) -> list[dict]:
    """The rows of a KenPom JSON answer: a list, or a list under a common key."""
    try:
        data = json.loads(payload)
    except ValueError as exc:
        raise KenPomError(f"KenPom did not answer JSON: {exc}") from exc
    if isinstance(data, dict):
        for key in ("data", "games", "fanmatch", "results", "rows"):
            if isinstance(data.get(key), list):
                data = data[key]
                break
        else:
            data = []
    return [row for row in data if isinstance(row, dict)] if isinstance(data, list) else []


def field_names(payload: bytes) -> list[str]:
    """The field NAMES of the first row, for the log: names, never values."""
    rows = rows_of(payload)
    return sorted(str(k) for k in rows[0]) if rows else []


def _field(row: dict, names: tuple[str, ...]):
    keyed = {second_opinion._key(k): v for k, v in row.items()}
    for name in names:
        if name in keyed and keyed[name] not in (None, ""):
            return keyed[name]
    return None


def _float(value) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def parse_fanmatch(payload: bytes, *, day: str) -> pd.DataFrame:
    """`day, home, away, home_pred, away_pred, home_wp, pred_tempo`, one row per
    game KenPom projected. A row without both teams and both projected scores
    inside `SCORE_RANGE` is dropped. A day with no games is an empty frame, not
    an error: KenPom has nothing to project on an off day."""
    out = []
    for row in rows_of(payload):
        home = _field(row, FIELD_NAMES["home"])
        away = _field(row, FIELD_NAMES["away"])
        hp = _float(_field(row, FIELD_NAMES["home_pred"]))
        ap = _float(_field(row, FIELD_NAMES["away_pred"]))
        if not home or not away:
            continue
        if not (SCORE_RANGE[0] <= hp <= SCORE_RANGE[1] and SCORE_RANGE[0] <= ap <= SCORE_RANGE[1]):
            continue
        wp = _float(_field(row, FIELD_NAMES["home_wp"]))
        if wp == wp and wp > 1.0:
            wp = wp / 100.0
        out.append({
            "day": str(day)[:10],
            "home": str(home).strip(),
            "away": str(away).strip(),
            "home_pred": hp,
            "away_pred": ap,
            "home_wp": wp,
            "pred_tempo": _float(_field(row, FIELD_NAMES["pred_tempo"])),
        })
    return pd.DataFrame(out, columns=[c for c in FANMATCH_COLUMNS if c not in ("home_id", "away_id")])


def resolve(frame: pd.DataFrame, schedule: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Both sides' names to this lab's team ids, through the second opinion's
    own resolver; the names that did not resolve."""
    out = frame.copy()
    unresolved: list[str] = []
    for side in ("home", "away"):
        if not len(out):
            out[f"{side}_id"] = pd.array([], dtype="Int64")
            continue
        resolved, missing = second_opinion.resolve(pd.DataFrame({"team": out[side].astype(str)}), schedule)
        out[f"{side}_id"] = resolved["team_id"].to_numpy()
        unresolved.extend(missing)
    return out, sorted(set(unresolved))


def write_fanmatch(frame: pd.DataFrame, *, raw_dir: Path | str | None, day: str) -> Path:
    path = fanmatch_path(raw_dir, day)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    for column in FANMATCH_COLUMNS:
        if column not in out.columns:
            out[column] = pd.NA
    out[list(FANMATCH_COLUMNS)].to_csv(path, index=False)
    return path

