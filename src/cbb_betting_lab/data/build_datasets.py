"""Build the processed tables every market settles against.

Three tables, and every settlement column in this lab comes from one of them:

* `team_games.csv` — one row per **team-game**: final score, halftime score,
  second-half score, overtime periods, the four factors' inputs, and an
  estimated possession count validated against play-by-play.
* `player_games.csv` — one row per **player-game**: every quantity a prop
  settles on, plus `did_not_play` and `starter`.
* `game_segments.csv` — one row per **game**: the per-period scoreline and the
  first made field goal, both derived from play-by-play because the schedule's
  own `linescores` column cannot be parsed (see below).

## The linescores trap

The schedule feed carries `home_linescores` / `away_linescores`, which would
give halftime scores for free. It is stored as a **string holding a numpy
repr** — `"[{'displayValue': '33', 'period': 1.0, ...}\\n {'displayValue': ...}]"`
— with newlines instead of commas between elements, so `ast.literal_eval`
fails on it. Halftime is derived from play-by-play instead, which is the
authoritative source anyway.

## The first-basket trap

`score_value` is **non-zero on missed shots too**. Reading the first row with a
non-zero `score_value` returns a miss. The scorer of the first basket is the
first row with `scoring_play == True` **and** a positive `score_value` from a
field goal — a free throw is not a basket, and that is a rule this lab encodes
rather than infers.

## The did-not-play trap

**69,344 of 196,876 player rows in the 2026 file are did-not-play rows** with
null minutes and null points. A mean computed over them is a third too low, and
nothing about it looks wrong. Every consumer filters on `did_not_play`.

## Possessions are not in the feed

Nothing in the ESPN data is a possession. The standard estimator is

    FGA - OREB + TOV + 0.475 * FTA

and this module computes it **and validates it against play-by-play** rather
than assuming it — `possession_validation()` counts real possession changes in
the play stream and reports the gap. Cooper's instruction: *"Derive possessions
from play-by-play where available and validate the standard estimator against
it rather than assuming the estimator."*
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.config import PROCESSED_DIR
from cbb_betting_lab.data import hoopr
from cbb_betting_lab.population import classify
from cbb_betting_lab.season import slate_date

#: The free-throw coefficient in the standard possession estimator. Basketball
#: Reference and KenPom both use 0.475 for men's college; it is the fraction of
#: free-throw attempts that end a possession. Validated, not assumed.
FREE_THROW_POSSESSION_WEIGHT = 0.475

#: Regulation is two halves. Anything beyond period 2 is overtime.
REGULATION_PERIODS = 2

#: The play types that are made free throws, and therefore **not baskets**.
#:
#: This exists because the obvious filter is wrong and its wrongness is silent.
#: The feed's type is `MadeFreeThrow` — **one word, no space** — so a
#: `str.contains("Free Throw")` screen matches none of the 253,589 free-throw
#: rows in a single season, and every one of them counts as a made field goal.
#: That inflated a possession count by 15 per game and, far worse, would have
#: settled `player_first_basket` on whoever made the game's first free throw.
#:
#: Matched after stripping spaces and case, so a future `Made Free Throw` is
#: caught too. `tests/test_free_throws_are_not_baskets.py` pins the vocabulary
#: and fails if ESPN introduces a spelling this does not know.
FREE_THROW_TYPE_KEYS: frozenset[str] = frozenset({"madefreethrow", "missedfreethrow"})

#: The scoring types that ARE field goals, recorded for the test to check
#: against. Not used as an allowlist: a new shot type must not silently stop
#: being a basket, so the filter is the negative one above.
KNOWN_FIELD_GOAL_TYPES: frozenset[str] = frozenset(
    {"jumpshot", "layupshot", "dunkshot", "tipshot"}
)


def _type_key(value: object) -> str:
    """A play type reduced to letters, so spacing and case cannot hide a match."""
    return "".join(ch for ch in str(value or "").lower() if ch.isalpha())


def is_free_throw(type_text: pd.Series) -> pd.Series:
    return type_text.map(lambda x: _type_key(x) in FREE_THROW_TYPE_KEYS)


def is_made_field_goal(frame: pd.DataFrame) -> pd.Series:
    """A made field goal: a scoring play that is not a free throw.

    Both conditions are load-bearing. `score_value` alone is not enough —
    **478,588 non-scoring rows in one season carry a positive `score_value`**,
    because the feed records what a *missed* shot would have been worth.
    """
    return (
        frame["scoring_play"].fillna(False).astype(bool)
        & (frame["score_value"].fillna(0) > 0)
        & ~is_free_throw(frame["type_text"])
    )

TEAM_GAME_COLUMNS = (
    "game_id", "season", "slate_date", "team_id", "opponent_id", "home_away",
    "neutral_site", "venue_state", "game_state",
    "team_score", "opponent_score", "margin", "total",
    "team_score_h1", "opponent_score_h1", "team_score_h2", "opponent_score_h2",
    "periods", "overtime", "possessions_estimated",
    "field_goals_made", "field_goals_attempted",
    "three_point_field_goals_made", "three_point_field_goals_attempted",
    "free_throws_made", "free_throws_attempted",
    "offensive_rebounds", "defensive_rebounds", "total_rebounds",
    "assists", "steals", "blocks", "turnovers", "fouls",
)

PLAYER_GAME_COLUMNS = (
    "game_id", "season", "slate_date", "athlete_id", "athlete_display_name",
    "team_id", "opponent_id", "home_away", "did_not_play", "starter", "minutes",
    "points", "rebounds", "offensive_rebounds", "defensive_rebounds",
    "assists", "steals", "blocks", "turnovers", "fouls",
    "field_goals_made", "field_goals_attempted",
    "three_point_field_goals_made", "free_throws_made", "free_throws_attempted",
    # Derived settlement quantities, materialised so a settlement never has to
    # re-derive one and two callers can never derive it two ways.
    "points_rebounds", "points_assists", "rebounds_assists", "pra",
    "blocks_steals", "double_double", "triple_double",
)


def _slate(frame: pd.DataFrame, competition: Competition) -> pd.Series:
    source = "game_date_time" if "game_date_time" in frame.columns else "game_date"
    return frame[source].map(
        lambda x: slate_date(pd.Timestamp(x).tz_convert("UTC").isoformat(), competition)
        if pd.notna(x) and getattr(pd.Timestamp(x), "tzinfo", None)
        else (str(x)[:10] if pd.notna(x) else "")
    )


def build_game_segments(season: int, *, raw_dir: Path | None = None) -> pd.DataFrame:
    """Per-period scores and the first made field goal, from play-by-play."""
    columns = [
        "game_id", "period_number", "home_score", "away_score", "game_play_number",
        "scoring_play", "score_value", "type_text", "athlete_id_1", "team_id",
        "home_team_id", "away_team_id",
    ]  # home/away_team_id are needed for the per-team first basket below
    pbp = hoopr.load("pbp", season, raw_dir=raw_dir, columns=columns)
    if pbp.empty:
        return pd.DataFrame()

    pbp = pbp.sort_values(["game_id", "game_play_number"], kind="mergesort")

    # The running score at the end of each period. `last` on a sorted frame is
    # the period's final state, which is what a half market settles on.
    ends = (
        pbp.groupby(["game_id", "period_number"])
        .agg(home_score=("home_score", "last"), away_score=("away_score", "last"))
        .reset_index()
    )
    halftime = ends[ends["period_number"] == 1].set_index("game_id")
    periods = ends.groupby("game_id")["period_number"].max()

    # The first made FIELD GOAL. A free throw is not a basket, and score_value
    # is non-zero on misses, so both conditions are required.
    made = pbp[is_made_field_goal(pbp)]
    first = made.groupby("game_id").first()

    # And each TEAM's first basket, which is a different market and a different
    # bet. Storing only the game's first basket makes `player_first_team_basket`
    # settleable for one side and unsettleable for the other — measured at
    # exactly 50% of rows before this was added, which is the shape of a gap
    # that looks like thin coverage and is really a missing column.
    per_team = made.groupby(["game_id", "team_id"]).first().reset_index()
    home_first = per_team[per_team["team_id"] == per_team["home_team_id"]].set_index("game_id")
    away_first = per_team[per_team["team_id"] == per_team["away_team_id"]].set_index("game_id")

    out = pd.DataFrame({"game_id": periods.index})
    out["periods"] = out["game_id"].map(periods)
    out["overtime"] = out["periods"] > REGULATION_PERIODS
    out["home_score_h1"] = out["game_id"].map(halftime["home_score"])
    out["away_score_h1"] = out["game_id"].map(halftime["away_score"])
    out["first_basket_athlete_id"] = out["game_id"].map(first["athlete_id_1"])
    out["first_basket_team_id"] = out["game_id"].map(first["team_id"])
    out["home_first_basket_athlete_id"] = out["game_id"].map(
        home_first["athlete_id_1"]
    )
    out["away_first_basket_athlete_id"] = out["game_id"].map(
        away_first["athlete_id_1"]
    )
    return out


def build_team_games(
    season: int, *, raw_dir: Path | None = None, competition: Competition = CBB
) -> pd.DataFrame:
    box = hoopr.load("team_box", season, raw_dir=raw_dir)
    schedule = hoopr.load("schedules", season, raw_dir=raw_dir)
    segments = build_game_segments(season, raw_dir=raw_dir)

    classified = classify(schedule).set_index("id")
    box = box.copy()
    box["slate_date"] = _slate(box, competition)

    # Opponent columns come from pairing the two rows of each game rather than
    # from a self-join on names. Names are the thing that goes wrong.
    pair = box[["game_id", "team_id", "team_score"]].copy()
    merged = pair.merge(pair, on="game_id", suffixes=("", "_opp"))
    merged = merged[merged["team_id"] != merged["team_id_opp"]]
    opponent = merged.set_index(["game_id", "team_id"])[["team_id_opp", "team_score_opp"]]

    index = pd.MultiIndex.from_frame(box[["game_id", "team_id"]])
    box["opponent_id"] = opponent["team_id_opp"].reindex(index).to_numpy()
    box["opponent_score"] = opponent["team_score_opp"].reindex(index).to_numpy()

    box["margin"] = box["team_score"] - box["opponent_score"]
    box["total"] = box["team_score"] + box["opponent_score"]
    box["home_away"] = box["team_home_away"]

    for column, source in (
        ("neutral_site", "neutral_site"),
        ("venue_state", "venue_state"),
        ("game_state", "game_state"),
    ):
        box[column] = box["game_id"].map(classified[source])

    if not segments.empty:
        seg = segments.set_index("game_id")
        is_home = box["home_away"].astype(str).str.lower().eq("home")
        h1_home = box["game_id"].map(seg["home_score_h1"])
        h1_away = box["game_id"].map(seg["away_score_h1"])
        box["team_score_h1"] = np.where(is_home, h1_home, h1_away)
        box["opponent_score_h1"] = np.where(is_home, h1_away, h1_home)
        box["periods"] = box["game_id"].map(seg["periods"])
        box["overtime"] = box["game_id"].map(seg["overtime"])
    else:
        for column in ("team_score_h1", "opponent_score_h1", "periods", "overtime"):
            box[column] = pd.NA

    # A second half **includes overtime**, matching how most US books grade it.
    # See `markets.SECOND_HALF_INCLUDES_OVERTIME` — a book rule, not a fact
    # about basketball, and recorded as a settlement ambiguity.
    box["team_score_h2"] = box["team_score"] - box["team_score_h1"]
    box["opponent_score_h2"] = box["opponent_score"] - box["opponent_score_h1"]

    box["possessions_estimated"] = (
        box["field_goals_attempted"]
        - box["offensive_rebounds"]
        + box["turnovers"]
        + FREE_THROW_POSSESSION_WEIGHT * box["free_throws_attempted"]
    )

    for column in TEAM_GAME_COLUMNS:
        if column not in box.columns:
            box[column] = pd.NA
    return box[list(TEAM_GAME_COLUMNS)]


def build_player_games(
    season: int, *, raw_dir: Path | None = None, competition: Competition = CBB
) -> pd.DataFrame:
    box = hoopr.load("player_box", season, raw_dir=raw_dir).copy()
    box["slate_date"] = _slate(box, competition)
    box["opponent_id"] = box["opponent_team_id"]

    counts = [
        "points", "rebounds", "assists", "steals", "blocks", "turnovers",
        "offensive_rebounds", "defensive_rebounds", "fouls",
        "field_goals_made", "field_goals_attempted",
        "three_point_field_goals_made", "free_throws_made", "free_throws_attempted",
    ]
    for column in counts:
        if column in box.columns:
            box[column] = pd.to_numeric(box[column], errors="coerce")

    box["points_rebounds"] = box["points"] + box["rebounds"]
    box["points_assists"] = box["points"] + box["assists"]
    box["rebounds_assists"] = box["rebounds"] + box["assists"]
    box["pra"] = box["points"] + box["rebounds"] + box["assists"]
    box["blocks_steals"] = box["blocks"] + box["steals"]

    # Double figures in two of five categories, three for a triple-double.
    doubles = sum(
        (box[c].fillna(0) >= 10).astype(int)
        for c in ("points", "rebounds", "assists", "steals", "blocks")
    )
    box["double_double"] = (doubles >= 2).astype(int)
    box["triple_double"] = (doubles >= 3).astype(int)

    # A did-not-play row has no stat line at all, and every count above is NaN
    # for it. Materialising the derived columns before this filter would let a
    # NaN sum reach a settlement, so the flag is carried and the consumers use
    # it rather than the rows being dropped here — an absent player is evidence
    # too, and `void` is a different outcome from `lost`.
    box["did_not_play"] = box["did_not_play"].fillna(False).astype(bool)

    for column in PLAYER_GAME_COLUMNS:
        if column not in box.columns:
            box[column] = pd.NA
    return box[list(PLAYER_GAME_COLUMNS)]


def possession_validation(season: int, *, raw_dir: Path | None = None) -> dict:
    """Check the standard possession estimator against play-by-play.

    Cooper's instruction, and it is a real check rather than a formality: the
    estimator is a convention, and a convention that is 3% wrong in this sport
    is 2 points on every total.

    A possession ends on a made field goal, a defensive rebound, a turnover, or
    the last of a set of free throws. Counting those transitions in the play
    stream gives an independent number to compare the estimator against.
    """
    columns = [
        "game_id", "team_id", "type_text", "scoring_play", "score_value",
        "game_play_number",
    ]
    pbp = hoopr.load("pbp", season, raw_dir=raw_dir, columns=columns)
    if pbp.empty:
        return {}
    pbp = pbp.sort_values(["game_id", "game_play_number"], kind="mergesort").reset_index(
        drop=True
    )
    text = pbp["type_text"].fillna("")
    free_throw = is_free_throw(text)
    made_free_throw = free_throw & pbp["scoring_play"].fillna(False).astype(bool)

    # A free-throw TRIP ends a possession; an individual free throw does not.
    # The last free throw of a consecutive run by one team is the one that
    # ends it — and only if it was made, because a miss leaves a live ball
    # that the rebound rule below already accounts for.
    same_trip = free_throw & free_throw.shift(-1, fill_value=False) & (
        pbp["team_id"] == pbp["team_id"].shift(-1)
    ) & (pbp["game_id"] == pbp["game_id"].shift(-1))
    trip_ends = made_free_throw & ~same_trip

    ends = (
        is_made_field_goal(pbp)
        | text.str.contains("Defensive Rebound", case=False, na=False)
        | text.str.contains("Turnover", case=False, na=False)
        | trip_ends
    )
    counted = pbp[ends].groupby("game_id").size()

    team = build_team_games(season, raw_dir=raw_dir)
    estimated = team.groupby("game_id")["possessions_estimated"].sum()
    joined = pd.DataFrame({"counted": counted, "estimated": estimated}).dropna()
    if joined.empty:
        return {}
    joined = joined[(joined["counted"] > 40) & (joined["estimated"] > 40)]
    gap = joined["estimated"] - joined["counted"]
    return {
        "season": season,
        "games": int(len(joined)),
        "mean_estimated": float(joined["estimated"].mean()),
        "mean_counted": float(joined["counted"].mean()),
        "mean_gap": float(gap.mean()),
        "median_gap": float(gap.median()),
        "gap_sd": float(gap.std(ddof=1)),
        "correlation": float(joined["estimated"].corr(joined["counted"])),
    }


def build(seasons: tuple[int, ...], *, raw_dir: Path | None = None,
          processed_dir: Path | None = None, allow_shrink: bool = False) -> dict:
    """Build every processed table for the named seasons.

    **A season whose feeds are not cached is SKIPPED AND REPORTED, never
    silently dropped and never fatal.** The distinction cost a real run: the
    2026-27 season has a published schedule and no play-by-play — it has not
    been played — and `build_game_segments` raised on it while the other two
    builders caught the same error and continued. The asymmetry killed the
    whole build, which in turn left settlement with no segments table, which
    marked the run degraded for two reasons that were really one.

    Skipping is reported through `written["skipped"]` and printed by the
    caller, because *"a failed fetch degrades rather than empties, and a
    degraded run is marked, never silently published as a thin slate."* The
    silent `continue` that used to be here was half of that rule.
    """
    target = Path(processed_dir) if processed_dir else Path(PROCESSED_DIR)
    target.mkdir(parents=True, exist_ok=True)
    written: dict[str, int] = {}
    skipped: dict[str, list[int]] = {}

    def _skip(table: str, season: int, why: str) -> None:
        skipped.setdefault(table, []).append(season)

    for name, builder, columns in (
        ("team_games", build_team_games, TEAM_GAME_COLUMNS),
        ("player_games", build_player_games, PLAYER_GAME_COLUMNS),
    ):
        frames = []
        for season in seasons:
            try:
                frames.append(builder(season, raw_dir=raw_dir))
            except hoopr.FeedError as error:
                _skip(name, season, str(error))
                continue
        if not frames:
            continue
        frame = pd.concat(frames, ignore_index=True)
        path = target / f"cbb_{name}.csv"
        # The shrink guard: rows, not existence, each file on its own.
        if path.is_file() and not allow_shrink:
            previous = len(pd.read_csv(path, usecols=[columns[0]]))
            if len(frame) < previous // 2:
                raise ValueError(
                    f"Refusing to write {name} at {len(frame):,} rows over "
                    f"{previous:,}. A partial rebuild looks exactly like a "
                    "light season. Pass allow_shrink=True deliberately."
                )
        frame.to_csv(path, index=False, lineterminator="\n")
        written[name] = len(frame)

    # The same handling as the two builders above. This list comprehension had
    # no `except` and was the one place a missing feed was fatal.
    segments = []
    for season in seasons:
        try:
            frame = build_game_segments(season, raw_dir=raw_dir)
        except hoopr.FeedError:
            _skip("game_segments", season, "feed not cached")
            continue
        if not frame.empty:
            segments.append(frame)
    if segments:
        frame = pd.concat(segments, ignore_index=True)
        frame.to_csv(target / "cbb_game_segments.csv", index=False, lineterminator="\n")
        written["game_segments"] = len(frame)
    if skipped:
        written["skipped"] = skipped  # type: ignore[assignment]
    return written
