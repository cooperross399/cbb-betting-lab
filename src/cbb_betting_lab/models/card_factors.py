"""Tonight's context, layered onto the ratings on the one seam the card reads.

`ratings.matchup` prices a game from three numbers: each side's adjusted
efficiency, the tempo, and the venue. Those are the *season* view of a team.
This module adds what tonight knows that the season does not, in the order the
card applies it, and records each layer so a reader can see what moved the
price and by how much:

1. **Team strength** — the fitted ratings on a neutral floor.
2. **Home court** — the tier's measured home effect, plus the building's own
   shrunk departure from it (`HOME_COURT_DEPARTURE`).
3. **Last five games** — each side's net efficiency over its last
   `FORM_GAMES`, against what the ratings expected of those games, shrunk at
   `FORM_SHRINKAGE_GAMES` (five games keep a quarter of the move) and clamped
   to `FORM_CLAMP` per 100 possessions.
4. **Rest** — days since each side's last game, in four buckets, with each
   bucket's effect fitted from the history the ratings were fitted on, per
   tier where the tier has enough games and league-wide where it does not.
5. **Who is missing** — a rotation player (`ROTATION_MINUTES` a game over the
   club's last `ROTATION_WINDOW`) who did not play in the club's most recent
   game is treated as out tonight, and `AVAILABILITY_SHARE` of his share of
   the club's points comes off its attack, floored at `AVAILABILITY_FLOOR`.
   Read off the box scores, because no free lineup feed exists for this sport.
6. **Second opinion** — a published ratings table fetched the same morning
   (`scripts/fetch_second_opinion.py`), blended at `BLEND_WEIGHT` on offence,
   defence and tempo. Only a table dated on or before the day and no older
   than `SECOND_OPINION_MAX_AGE_DAYS` is read, so a walk-forward over past days
   prices without it rather than with tomorrow's.

**The layer audit switches layers on and off (Cooper, 2026-10-30).** Every
layer above but team strength, and the `CANDIDATE_LAYERS` after it, is
computed on every game whether it is on the card or not; a layer that is off
moves nothing and leaves what it *would* have moved in `context["shadow"]`.
Which are on is read from the audit `scripts/run_layer_audit.py` writes each
gameday run (`models/layer_audit.py`), under the second opinion's rule: only
an audit dated on or before the day and no older than
`LAYER_AUDIT_MAX_AGE_DAYS` is read, so a walk-forward over past days prices
with the declared defaults (`default_switches`) and never with a verdict
reached later. The audit judges results, never prices: a layer is kept when
it makes the predicted margin and total closer to what happened.

Every constant here is this lab's choice, made before any price was read.
None of it was measured against prices before it went on the card; the price
backtest prices through the same seam and is where that measurement lives.

**Walk-forward.** Every frame handed to :func:`build_context` must already be
cut strictly before the day, as `fit` demands of its own history; a row dated
on or after the day raises rather than being filtered, because a filter that
quietly removes a leak looks exactly like no leak.

**What a layer carries.** Each entry in `Matchup.layers` is the price *after*
that layer: both sides in points per 100 possessions and the possessions. No
win chance is computed here, because the joint distribution costs about a
third of a second a game and this seam is called for every event of every day
of a walk-forward; a reader that wants a win chance per layer builds one from
the final distribution it already has (`web/build_board_json.py` does).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping

import numpy as np
import pandas as pd

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.conferences import Tier
from cbb_betting_lab.population import VenueState
from cbb_betting_lab.season import clean_text

# --- the constants, all this lab's choice -----------------------------------

#: Games in the form window, and the shrinkage that decides how much of the
#: window's residual is believed: n / (n + FORM_SHRINKAGE_GAMES).
FORM_GAMES = 5
FORM_SHRINKAGE_GAMES = 15
#: The most a side's net efficiency may move on form, per 100 possessions.
FORM_CLAMP = 3.0

#: Days since the last game -> bucket. The third is the reference: every
#: effect is relative to ordinary rest.
REST_BUCKETS: tuple[tuple[str, int, int], ...] = (
    ("second game in two days", 1, 1),
    ("one day off", 2, 2),
    ("ordinary rest", 3, 5),
    ("six or more days off", 6, 10**6),
)
REST_REFERENCE = "ordinary rest"
#: A bucket's fitted effect is shrunk by n / (n + REST_SHRINKAGE_GAMES) and
#: clamped to REST_CLAMP per 100 possessions. A tier needs REST_MIN_TIER_GAMES
#: in a bucket to carry its own effect; otherwise the league-wide one applies.
REST_SHRINKAGE_GAMES = 300
REST_CLAMP = 2.0
REST_MIN_TIER_GAMES = 150

#: A rotation player averages this many minutes over the club's last
#: ROTATION_WINDOW games, with at least ROTATION_MIN_APPEARANCES of them played.
ROTATION_MINUTES = 18.0
ROTATION_WINDOW = 8
ROTATION_MIN_APPEARANCES = 3
#: How much of a missing player's share of the club's points comes off its
#: attack, and the floor the attack cannot drop below.
AVAILABILITY_SHARE = 0.5
AVAILABILITY_FLOOR = 0.92

#: The second opinion's weight on offence, defence and tempo.
BLEND_WEIGHT = 0.5
SECOND_OPINION_MAX_AGE_DAYS = 2
SECOND_OPINION_MIN_TEAMS = 300
SECOND_OPINION_DIR = "second_opinion"
SECOND_OPINION_COLUMNS = (
    "as_of", "season", "source", "team", "team_id", "adj_off", "adj_def", "adj_tempo",
)

#: Whether each venue's own shrunk departure is applied on top of its tier's
#: effect. `fit` applies it only when the recorded `venue_home_effect` verdict
#: ships; the card applies it here regardless, by Cooper's call (CLAUDE.md,
#: 2026-10-26), and the layer records which of the two put it there.
HOME_COURT_DEPARTURE = True

#: The layers, in the order they are applied, with the label a page shows.
LAYERS: tuple[tuple[str, str], ...] = (
    ("strength", "Team strength"),
    ("home_court", "Home court"),
    ("form", "Last five games"),
    ("rest", "Rest"),
    ("lineup", "Who is missing"),
    ("second_opinion", "Second opinion"),
)
#: Layers the audit may ADD: computed on every game, kept in the shadow, and
#: put on the card only when the audit has measured that they predict results
#: better (`layer_audit.ADD_Z`). Off by default. Applied after the six above,
#: in this order, when on.
CANDIDATE_LAYERS: tuple[tuple[str, str], ...] = (
    ("pace_form", "Pace, last five games"),
    ("three_point_luck", "Three-point defence luck"),
    ("lineup_strict", "Who is missing, two games running"),
)
#: `lineup_strict`: a rotation player counts as out only after missing this
#: many of the club's games in a row. When on, it replaces the single-game
#: rule's factor rather than stacking on it.
LINEUP_STRICT_GAMES = 2
LABELS = dict(LAYERS + CANDIDATE_LAYERS)
#: The layers the audit may switch. Team strength is the model, not a layer
#: on it, and is never switched off.
SWITCHABLE: tuple[str, ...] = tuple(
    key for key, _ in LAYERS + CANDIDATE_LAYERS if key != "strength"
)

#: Pace form: each side's possessions over its last `FORM_GAMES` against the
#: tempo the ratings expected, shrunk like net form and clamped per side.
PACE_FORM_SHRINKAGE_GAMES = 15
PACE_FORM_CLAMP = 3.0
#: Three-point defence luck: the points per 100 possessions a side's opponents
#: scored from three above what their attempts at the season's league-wide
#: rate would have made. Opponents' three-point accuracy is the least repeatable
#: part of a defence's record, so `THREE_LUCK_SHARE` of it is taken back off,
#: once a side has `THREE_LUCK_MIN_GAMES`, clamped to `THREE_LUCK_CLAMP`.
THREE_LUCK_SHARE = 0.5
THREE_LUCK_MIN_GAMES = 5
THREE_LUCK_CLAMP = 3.0

#: Where the audit's switches are read from, and how stale they may be.
LAYER_AUDIT_DIR = "layer_audit"
LAYER_AUDIT_FILE = "latest.json"
LAYER_AUDIT_MAX_AGE_DAYS = 3
#: False while the audit itself re-prices past days, so its measurement is
#: always taken against the declared card and never against its own earlier
#: verdicts (`scripts/run_layer_audit.py` sets it).
READ_LAYER_AUDIT = True


def default_switches() -> dict:
    """The declared card: the six layers on, the candidates off."""
    core = {key for key, _ in LAYERS}
    return {key: key in core for key in SWITCHABLE}


class WalkForwardViolation(ValueError):
    """A frame handed to the context carries a row from the day being priced."""


# --- the day's context --------------------------------------------------------


@dataclass
class SecondOpinion:
    """A published ratings table, as deviations from its own mean."""

    as_of: str
    source: str
    #: team_id -> (offence deviation, defence deviation, tempo deviation), each
    #: per 100 possessions (tempo in possessions) from the table's own mean,
    #: so the sign convention matches `Ratings.offence/defence/tempo`.
    teams: dict = field(default_factory=dict)

    def __len__(self) -> int:
        return len(self.teams)


@dataclass
class DayContext:
    """Everything tonight's layers read, built once per day."""

    day: str
    #: team_id -> shrunk net form per 100, and the games it was read from.
    form: dict = field(default_factory=dict)
    form_games: dict = field(default_factory=dict)
    #: team_id -> days since its last game this season, None for an opener.
    rest_days: dict = field(default_factory=dict)
    #: (tier, bucket) -> effect per 100, net, relative to ordinary rest.
    rest_effects: dict = field(default_factory=dict)
    #: team_id -> the rotation players treated as out, and the attack factor.
    missing: dict = field(default_factory=dict)
    attack_factor: dict = field(default_factory=dict)
    #: The same under `LINEUP_STRICT_GAMES` games missed in a row (candidate).
    missing_strict: dict = field(default_factory=dict)
    attack_factor_strict: dict = field(default_factory=dict)
    second_opinion: SecondOpinion | None = None
    #: team_id -> shrunk possessions residual over the last games (candidate).
    pace_form: dict = field(default_factory=dict)
    #: team_id -> points per 100 the defence's opponents made from three above
    #: expectation, times the share taken back (candidate).
    three_luck: dict = field(default_factory=dict)
    #: layer key -> on the card or not; `default_switches` unless an audit
    #: dated within `LAYER_AUDIT_MAX_AGE_DAYS` of the day said otherwise.
    switches: dict = field(default_factory=default_switches)
    audit_as_of: str | None = None
    #: Why a layer is absent, in sentences a log can print.
    notes: list = field(default_factory=list)

    def is_on(self, key: str) -> bool:
        return bool(self.switches.get(key, default_switches().get(key, False)))

    def rest_bucket(self, team_id) -> str | None:
        days = self.rest_days.get(team_id)
        return rest_bucket(days)

    def rest_effect(self, team_id, tier: str) -> float:
        bucket = self.rest_bucket(team_id)
        if bucket is None or bucket == REST_REFERENCE:
            return 0.0
        if (tier, bucket) in self.rest_effects:
            return float(self.rest_effects[(tier, bucket)])
        return float(self.rest_effects.get(("league", bucket), 0.0))


def rest_bucket(days) -> str | None:
    """The rest bucket for `days` since the last game, None for no last game."""
    if days is None:
        return None
    try:
        value = int(days)
    except (TypeError, ValueError):
        return None
    if value < 1:
        return None
    for label, low, high in REST_BUCKETS:
        if low <= value <= high:
            return label
    return None


def _refuse_leak(frame: pd.DataFrame | None, day: str, what: str) -> pd.DataFrame:
    if frame is None or len(frame) == 0 or "slate_date" not in frame.columns:
        return pd.DataFrame() if frame is None else frame
    dates = frame["slate_date"].astype(str)
    leaked = int((dates >= str(day)).sum())
    if leaked:
        raise WalkForwardViolation(
            f"{leaked:,} of {len(frame):,} {what} rows are dated on or after "
            f"{day}, the day being priced. Tonight's context may read only what "
            "was known before tonight."
        )
    return frame


def _tier_of(ratings, team_id) -> str:
    try:
        return str(ratings.tier_of(team_id))
    except Exception:  # pragma: no cover - a prior without tiers
        return Tier.UNPLACED.value


def _venue_margin(ratings, row) -> float:
    """What the ratings expected the venue to add to this side's net, per 100."""
    state = clean_text(row.get("venue_state"))
    local = row.get("local_team_id")
    if local is None or (isinstance(local, float) and math.isnan(local)):
        local = None
    if state == VenueState.NEUTRAL.value or local is None:
        return 0.0
    venue = ratings.venue
    team = row.get("team_id")
    opponent = row.get("opponent_id")
    if state == VenueState.QUASI_NEUTRAL.value:
        margin = venue.quasi_offence - venue.quasi_defence
    else:
        tier = _tier_of(ratings, local)
        margin = venue.home_offence(tier) - venue.home_defence(tier)
        if ratings.venue_level_home_effect:
            margin += venue.departure_for(row.get("venue_id"))
    if local == team:
        return float(margin)
    if local == opponent:
        return -float(margin)
    return 0.0


def _net_columns(rows: pd.DataFrame) -> pd.DataFrame:
    """Each row's realised net efficiency, per 100 possessions."""
    frame = rows.copy()
    possessions = pd.to_numeric(frame.get("game_possessions"), errors="coerce")
    own = pd.to_numeric(frame.get("efficiency"), errors="coerce")
    allowed = pd.to_numeric(frame.get("opponent_score"), errors="coerce") / possessions * 100.0
    frame["net"] = own - allowed
    frame = frame[np.isfinite(frame["net"])]
    return frame


def team_form(rows: pd.DataFrame, ratings, *, teams=None) -> tuple[dict, dict]:
    """Each team's shrunk net residual over its last `FORM_GAMES` games.

    The residual is realised net minus what the ratings would have expected of
    that game: the two sides' fitted offence and defence and the venue. It is
    computed against the ratings fitted *through* those games, so it is the
    part of recent play the season fit has not yet absorbed — in November,
    where the prior still carries most of the weight, that is most of it.
    """
    if rows is None or len(rows) == 0:
        return {}, {}
    frame = _net_columns(rows)
    if frame.empty:
        return {}, {}
    wanted = None if teams is None else {t for t in teams}
    if wanted is not None:
        frame = frame[frame["team_id"].isin(wanted)]
    frame = frame.sort_values(["team_id", "slate_date", "game_id"])
    form: dict = {}
    games: dict = {}
    offence = ratings.offence
    defence = ratings.defence
    for team, group in frame.groupby("team_id", sort=False):
        recent = group.tail(FORM_GAMES)
        residuals = []
        for row in recent.to_dict("records"):
            opponent = row.get("opponent_id")
            expected = (
                float(offence.get(team, 0.0))
                + float(defence.get(opponent, 0.0))
                - float(offence.get(opponent, 0.0))
                - float(defence.get(team, 0.0))
                + _venue_margin(ratings, row)
            )
            residuals.append(float(row["net"]) - expected)
        n = len(residuals)
        if n == 0:
            continue
        mean = float(np.mean(residuals))
        shrunk = mean * n / (n + FORM_SHRINKAGE_GAMES)
        form[team] = float(np.clip(shrunk, -FORM_CLAMP, FORM_CLAMP))
        games[team] = n
    return form, games


def days_since_last_game(rows: pd.DataFrame, day: str, *, teams=None) -> dict:
    """team_id -> whole days between its last game this season and `day`."""
    if rows is None or len(rows) == 0 or "slate_date" not in rows.columns:
        return {}
    frame = rows[["team_id", "slate_date"]].copy()
    if teams is not None:
        frame = frame[frame["team_id"].isin({t for t in teams})]
    last = frame.groupby("team_id")["slate_date"].max()
    target = pd.Timestamp(str(day)[:10])
    out: dict = {}
    for team, when in last.items():
        stamp = pd.to_datetime(str(when)[:10], errors="coerce")
        if pd.isna(stamp):
            continue
        out[team] = int((target - stamp).days)
    return out


def rest_effects(history: pd.DataFrame, ratings) -> dict:
    """(tier | "league", bucket) -> net effect per 100, relative to ordinary rest.

    Fitted on every countable row the ratings were allowed to see, across
    seasons: each row's net minus its team-season mean net and minus the mean
    for its venue state, bucketed by the team's days since its previous game
    in that season. Shrunk at `REST_SHRINKAGE_GAMES`, clamped at `REST_CLAMP`,
    and never pooled across the tiers where a tier can stand on its own
    (`REST_MIN_TIER_GAMES`); the league-wide value is the fallback, not the
    headline.
    """
    if history is None or len(history) == 0:
        return {}
    frame = _net_columns(history)
    needed = {"team_id", "season", "slate_date", "venue_state"}
    if frame.empty or not needed.issubset(frame.columns):
        return {}
    frame = frame.sort_values(["season", "team_id", "slate_date", "game_id"])
    stamps = pd.to_datetime(frame["slate_date"].astype(str).str[:10], errors="coerce")
    frame = frame.assign(_stamp=stamps)
    previous = frame.groupby(["season", "team_id"])["_stamp"].shift(1)
    frame["_days"] = (frame["_stamp"] - previous).dt.days
    frame = frame[frame["_days"].notna()]
    if frame.empty:
        return {}
    frame["_bucket"] = frame["_days"].map(rest_bucket)
    frame = frame[frame["_bucket"].notna()]
    team_mean = frame.groupby(["season", "team_id"])["net"].transform("mean")
    frame["_residual"] = frame["net"] - team_mean
    side = frame["venue_state"].astype(str) + "/" + frame.get("home_away", "").astype(str)
    frame["_residual"] = frame["_residual"] - frame["_residual"].groupby(side).transform("mean")
    frame["_tier"] = frame["team_id"].map(lambda t: _tier_of(ratings, t))

    out: dict = {}

    def settle(group: pd.DataFrame, key) -> None:
        reference = group[group["_bucket"] == REST_REFERENCE]["_residual"]
        base = float(reference.mean()) if len(reference) else 0.0
        for label, _, _ in REST_BUCKETS:
            if label == REST_REFERENCE:
                continue
            cell = group[group["_bucket"] == label]["_residual"]
            n = int(len(cell))
            if n == 0:
                continue
            raw = float(cell.mean()) - base
            shrunk = raw * n / (n + REST_SHRINKAGE_GAMES)
            out[(key, label)] = float(np.clip(shrunk, -REST_CLAMP, REST_CLAMP))

    settle(frame, "league")
    for tier, group in frame.groupby("_tier"):
        if tier == Tier.UNPLACED.value:
            continue
        counts = group["_bucket"].value_counts()
        if int(counts.get(REST_REFERENCE, 0)) < REST_MIN_TIER_GAMES:
            continue
        kept = group[group["_bucket"].map(lambda b: int(counts.get(b, 0)) >= REST_MIN_TIER_GAMES or b == REST_REFERENCE)]
        settle(kept, str(tier))
    return out


def missing_rotation(
    player_rows: pd.DataFrame, team_rows: pd.DataFrame, *, teams, games_missed: int = 1
) -> tuple[dict, dict]:
    """Who is treated as out tonight, per team, and the attack factor it costs.

    A club's rotation is read off its last `ROTATION_WINDOW` games: a player
    who played at least `ROTATION_MIN_APPEARANCES` of them at `ROTATION_MINUTES`
    or more a game. One who did not play in the club's most recent game — a
    did-not-play row, or no row at all — is treated as out tonight. A player
    rested in one blowout looks the same, and this is read as a cost of having
    no lineup feed rather than a reason to guess.

    `games_missed` asks for that many of the club's most recent games missed in
    a row; the candidate layer `lineup_strict` reads two, so a single rest day
    no longer reads as an absence.
    """
    missing: dict = {}
    factor: dict = {}
    if (
        player_rows is None or len(player_rows) == 0
        or team_rows is None or len(team_rows) == 0
    ):
        return missing, factor
    needed = {"game_id", "team_id", "athlete_display_name", "minutes", "points"}
    if not needed.issubset(player_rows.columns):
        return missing, factor
    wanted = {t for t in teams}
    games = team_rows[team_rows["team_id"].isin(wanted)][["team_id", "game_id", "slate_date"]]
    if games.empty:
        return missing, factor
    games = games.sort_values(["team_id", "slate_date", "game_id"])
    recent = games.groupby("team_id").tail(ROTATION_WINDOW)
    keys = set(zip(recent["team_id"].astype(int), recent["game_id"].astype(int)))
    rows = player_rows[player_rows["team_id"].isin(wanted)]
    rows = rows[[(int(t), int(g)) in keys for t, g in zip(rows["team_id"], rows["game_id"])]]
    if rows.empty:
        return missing, factor
    dnp = rows["did_not_play"].astype(str).str.lower().isin({"true", "1"}) if "did_not_play" in rows.columns else pd.Series(False, index=rows.index)
    minutes = pd.to_numeric(rows["minutes"], errors="coerce")
    played = (~dnp) & (minutes > 0)
    rows = rows.assign(_played=played, _minutes=minutes.where(played, 0.0),
                       _points=pd.to_numeric(rows["points"], errors="coerce").where(played, 0.0))
    last_games = {
        team: list(group["game_id"])[-max(1, int(games_missed)):]
        for team, group in recent.groupby("team_id")
    }
    for team, group in rows.groupby("team_id"):
        team_key = int(team)
        lasts = last_games.get(team)
        if not lasts or len(lasts) < max(1, int(games_missed)):
            continue
        window_games = int(group["game_id"].nunique())
        if window_games == 0:
            continue
        team_points = float(group["_points"].sum())
        if team_points <= 0:
            continue
        by_player = group.groupby("athlete_display_name").agg(
            appearances=("_played", "sum"),
            minutes=("_minutes", "sum"),
            points=("_points", "sum"),
        )
        by_player = by_player[by_player["appearances"] >= ROTATION_MIN_APPEARANCES]
        by_player["minutes_per_game"] = by_player["minutes"] / by_player["appearances"]
        rotation = by_player[by_player["minutes_per_game"] >= ROTATION_MINUTES]
        if rotation.empty:
            continue
        latest = group[group["game_id"].isin(lasts)]
        played_last = set(latest[latest["_played"]]["athlete_display_name"])
        out = []
        share = 0.0
        for name, row in rotation.iterrows():
            if name in played_last:
                continue
            points_share = float(row["points"]) / team_points
            share += points_share
            out.append({
                "name": str(name),
                "points_per_game": round(float(row["points"]) / float(row["appearances"]), 1),
                "minutes_per_game": round(float(row["minutes_per_game"]), 1),
                "share": round(points_share, 3),
            })
        if not out:
            continue
        out.sort(key=lambda r: -r["share"])
        missing[team_key] = out
        factor[team_key] = float(max(AVAILABILITY_FLOOR, 1.0 - AVAILABILITY_SHARE * share))
    return missing, factor


def second_opinion_path(raw_dir: Path | str | None, season: int) -> Path:
    base = Path(raw_dir) if raw_dir else Path("data/raw")
    return base / CBB.data_dir_segment / SECOND_OPINION_DIR / f"{int(season)}.csv"


def load_second_opinion(
    raw_dir: Path | str | None, *, season: int, day: str
) -> tuple[SecondOpinion | None, str]:
    """The second opinion for `day`, or None and the reason.

    Refused when the file is absent, dated after the day (a walk-forward over
    a past day must not read today's table), older than
    `SECOND_OPINION_MAX_AGE_DAYS`, or resolving fewer than
    `SECOND_OPINION_MIN_TEAMS` teams.
    """
    path = second_opinion_path(raw_dir, season)
    if not path.is_file():
        return None, f"no second opinion on disk at {path}"
    try:
        frame = pd.read_csv(path)
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        return None, f"the second opinion at {path} could not be read ({exc})"
    missing = [c for c in SECOND_OPINION_COLUMNS if c not in frame.columns]
    if missing:
        return None, f"the second opinion at {path} lacks {missing}"
    if frame.empty:
        return None, f"the second opinion at {path} holds no team"
    as_of = clean_text(frame["as_of"].astype(str).iloc[0])[:10]
    source = clean_text(frame["source"].astype(str).iloc[0])
    try:
        stamp = pd.Timestamp(as_of)
        target = pd.Timestamp(str(day)[:10])
    except (TypeError, ValueError):
        return None, f"the second opinion's date {as_of!r} could not be read"
    if stamp > target:
        return None, (
            f"the second opinion on disk is dated {as_of}, after {day}; a day "
            "is priced only with what was published by then"
        )
    if (target - stamp).days > SECOND_OPINION_MAX_AGE_DAYS:
        return None, (
            f"the second opinion on disk is dated {as_of}, more than "
            f"{SECOND_OPINION_MAX_AGE_DAYS} days before {day}"
        )
    resolved = frame.dropna(subset=["team_id"]).copy()
    for column in ("adj_off", "adj_def", "adj_tempo"):
        resolved[column] = pd.to_numeric(resolved[column], errors="coerce")
    resolved = resolved.dropna(subset=["adj_off", "adj_def", "adj_tempo"])
    resolved = resolved.drop_duplicates(subset=["team_id"])
    if len(resolved) < SECOND_OPINION_MIN_TEAMS:
        return None, (
            f"the second opinion resolves {len(resolved)} teams, under the "
            f"{SECOND_OPINION_MIN_TEAMS} it needs to be read"
        )
    off = resolved["adj_off"] - resolved["adj_off"].mean()
    de = resolved["adj_def"] - resolved["adj_def"].mean()
    tempo = resolved["adj_tempo"] - resolved["adj_tempo"].mean()
    teams = {
        int(t): (float(o), float(d), float(p))
        for t, o, d, p in zip(resolved["team_id"], off, de, tempo)
    }
    return SecondOpinion(as_of=as_of, source=source, teams=teams), ""


def pace_form(rows: pd.DataFrame, ratings, *, teams=None) -> dict:
    """Each team's shrunk possessions residual over its last `FORM_GAMES`.

    The residual is the game's possessions minus the tempo the ratings expect
    of that pairing, so a side whose recent games have run faster than its
    season says carries some of that into tonight's total.
    """
    if rows is None or len(rows) == 0 or "game_possessions" not in rows.columns:
        return {}
    frame = rows
    if teams is not None:
        frame = frame[frame["team_id"].isin({t for t in teams})]
    frame = frame.sort_values(["team_id", "slate_date", "game_id"])
    out: dict = {}
    for team, group in frame.groupby("team_id", sort=False):
        residuals = []
        for row in group.tail(FORM_GAMES).to_dict("records"):
            actual = pd.to_numeric(row.get("game_possessions"), errors="coerce")
            if not np.isfinite(actual):
                continue
            residuals.append(float(actual) - ratings.expected_tempo(team, row.get("opponent_id")))
        n = len(residuals)
        if n == 0:
            continue
        shrunk = float(np.mean(residuals)) * n / (n + PACE_FORM_SHRINKAGE_GAMES)
        out[team] = float(np.clip(shrunk, -PACE_FORM_CLAMP, PACE_FORM_CLAMP))
    return out


def three_point_luck(rows: pd.DataFrame, *, teams=None) -> dict:
    """team_id -> the share of its opponents' three-point over-performance
    taken back, per 100 of its defensive possessions.

    Positive when opponents have made more threes than their attempts were
    worth at the league's rate this season: the defence's record looks worse
    than it is, so tonight's opponent is expected to score that much less.
    """
    made_col, tried_col = "three_point_field_goals_made", "three_point_field_goals_attempted"
    needed = {"game_id", "team_id", "opponent_id", "game_possessions", made_col, tried_col}
    if rows is None or len(rows) == 0 or not needed <= set(rows.columns):
        return {}
    frame = rows[list(needed)].copy()
    for column in (made_col, tried_col, "game_possessions"):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    frame = frame.dropna()
    tried = float(frame[tried_col].sum())
    if tried <= 0:
        return {}
    league = float(frame[made_col].sum()) / tried
    shooting = frame[["game_id", "team_id", made_col, tried_col]].rename(
        columns={"team_id": "opponent_id", made_col: "opp_made", tried_col: "opp_tried"}
    )
    joined = frame[["game_id", "team_id", "opponent_id", "game_possessions"]].merge(
        shooting, on=["game_id", "opponent_id"], how="inner"
    )
    if teams is not None:
        joined = joined[joined["team_id"].isin({t for t in teams})]
    joined = joined.assign(excess=3.0 * (joined["opp_made"] - league * joined["opp_tried"]))
    out: dict = {}
    for team, group in joined.groupby("team_id"):
        if len(group) < THREE_LUCK_MIN_GAMES:
            continue
        possessions = float(group["game_possessions"].sum())
        if possessions <= 0:
            continue
        per_100 = 100.0 * float(group["excess"].sum()) / possessions
        out[team] = float(np.clip(THREE_LUCK_SHARE * per_100, -THREE_LUCK_CLAMP, THREE_LUCK_CLAMP))
    return out


def layer_audit_path(raw_dir: Path | str | None) -> Path:
    base = Path(raw_dir) if raw_dir else Path("data/raw")
    return base / CBB.data_dir_segment / LAYER_AUDIT_DIR / LAYER_AUDIT_FILE


def load_layer_audit(raw_dir: Path | str | None, *, day: str) -> tuple[dict | None, str, str]:
    """The audit's switches for `day`, its date, and why it was not read.

    Refused when absent, unreadable, dated after the day, or older than
    `LAYER_AUDIT_MAX_AGE_DAYS`; the card then prices on `default_switches`.
    A key the audit does not name keeps its default, and a key it names that
    this module does not know is ignored.
    """
    if not READ_LAYER_AUDIT:
        return None, "", "the layer audit is re-pricing, so it reads no earlier verdict"
    path = layer_audit_path(raw_dir)
    if not path.is_file():
        return None, "", f"no layer audit on disk at {path}"
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return None, "", f"the layer audit at {path} could not be read ({exc})"
    as_of = str((payload or {}).get("as_of") or "")[:10]
    try:
        stamp = pd.Timestamp(as_of)
        target = pd.Timestamp(str(day)[:10])
    except (TypeError, ValueError):
        return None, "", f"the layer audit's date {as_of!r} could not be read"
    if stamp > target:
        return None, as_of, f"the layer audit on disk is dated {as_of}, after {day}"
    if (target - stamp).days > LAYER_AUDIT_MAX_AGE_DAYS:
        return None, as_of, (
            f"the layer audit on disk is dated {as_of}, more than "
            f"{LAYER_AUDIT_MAX_AGE_DAYS} days before {day}"
        )
    switches = default_switches()
    for key, value in ((payload or {}).get("switches") or {}).items():
        if key in switches and isinstance(value, bool):
            switches[key] = value
    return switches, as_of, ""


def build_context(
    *,
    day: str,
    ratings,
    season_rows: pd.DataFrame,
    history_rows: pd.DataFrame,
    player_history: pd.DataFrame | None,
    raw_dir: Path | str | None,
    teams=None,
) -> DayContext:
    """Everything tonight's layers read, from frames cut before `day`."""
    day = str(day)[:10]
    season_rows = _refuse_leak(season_rows, day, "season")
    history_rows = _refuse_leak(history_rows, day, "history")
    player_history = _refuse_leak(player_history, day, "player")
    context = DayContext(day=day)
    if teams is not None:
        teams = {t for t in teams}

    context.form, context.form_games = team_form(season_rows, ratings, teams=teams)
    context.rest_days = days_since_last_game(season_rows, day, teams=teams)
    context.rest_effects = rest_effects(history_rows, ratings)
    if player_history is None or len(player_history) == 0:
        context.notes.append("no player table was handed over, so nobody is treated as missing")
    elif teams is None or not teams:
        context.notes.append("no team was named, so nobody is treated as missing")
    else:
        season = getattr(ratings, "season", None)
        rows = player_history
        if season is not None and "season" in rows.columns:
            rows = rows[pd.to_numeric(rows["season"], errors="coerce") == int(season)]
        context.missing, context.attack_factor = missing_rotation(
            rows, season_rows, teams=teams
        )
        context.missing_strict, context.attack_factor_strict = missing_rotation(
            rows, season_rows, teams=teams, games_missed=LINEUP_STRICT_GAMES
        )
    season = getattr(ratings, "season", None)
    if season is None:
        context.notes.append("the ratings name no season, so no second opinion was read")
    else:
        context.second_opinion, reason = load_second_opinion(raw_dir, season=int(season), day=day)
        if context.second_opinion is None:
            context.notes.append(reason)
    context.pace_form = pace_form(season_rows, ratings, teams=teams)
    context.three_luck = three_point_luck(season_rows, teams=teams)
    switches, as_of, reason = load_layer_audit(raw_dir, day=day)
    if switches is not None:
        context.switches = switches
        context.audit_as_of = as_of
    return context


# --- applying the layers ------------------------------------------------------


def _layer(key: str, home: float, away: float, possessions: float, note: str = "") -> dict:
    return {
        "key": key,
        "label": LABELS[key],
        "home": float(home),
        "away": float(away),
        "possessions": float(possessions),
        "note": note,
    }


def apply(
    base,
    *,
    ratings,
    context: DayContext,
    venue_id=None,
    local_team_id=None,
):
    """`base` with tonight's layers applied, and each layer recorded on it.

    `base.venue_home_add` and `base.venue_away_add` are what
    `ratings._match_venue_effect` added to the two sides, so the strength layer
    can start from the neutral floor. A base that is not priceable is returned
    untouched.
    """
    if not getattr(base, "priceable", False):
        return base
    scale = 100.0
    home = float(base.home_points_per_possession) * scale
    away = float(base.away_points_per_possession) * scale
    possessions = float(base.possessions)
    home_id = base.home_team_id
    away_id = base.away_team_id
    detail: dict = {"day_summary": summary(context)}
    layers: list[dict] = []

    # 1. Strength: the neutral floor.
    home_add = float(getattr(base, "venue_home_add", 0.0))
    away_add = float(getattr(base, "venue_away_add", 0.0))
    layers.append(_layer("strength", home - home_add, away - away_add, possessions))

    # Each layer below is computed as a move — (home, away, possessions) per
    # 100 — from the price as it stands. A layer that is on takes the move; one
    # the audit has switched off still appears in `layers`, unmoved, so the
    # page's order never changes, and its move goes to the shadow, which is
    # what the next audit judges it on.
    shadow: dict = {}

    def take(key: str, move: tuple[float, float, float]) -> None:
        nonlocal home, away, possessions
        if context.is_on(key):
            home += move[0]
            away += move[1]
            possessions += move[2]
            layers.append(_layer(key, home, away, possessions))
        else:
            shadow[key] = {"home": move[0], "away": move[1], "possessions": move[2]}
            if key in LABELS and key in dict(LAYERS):
                layers.append(_layer(key, home, away, possessions, "switched off by the layer audit"))

    # 2. Home court: the tier effect the base already carries, plus the
    #    building's own departure where the fit did not apply it.
    departure = 0.0
    state = str(base.venue_state or "")
    if (
        HOME_COURT_DEPARTURE
        and not ratings.venue_level_home_effect
        and state == VenueState.HOME.value
        and local_team_id is not None
        and venue_id is not None
    ):
        own = float(ratings.venue.departure_for(venue_id))
        if local_team_id == home_id:
            departure = own
        elif local_team_id == away_id:
            departure = -own
    detail["home_court"] = {
        "tier_margin": float(home_add - away_add),
        "departure": float(departure) if context.is_on("home_court") else 0.0,
        "applied_by": "the fit" if ratings.venue_level_home_effect else "the card",
    }
    take("home_court", (departure / 2.0, -departure / 2.0, 0.0))

    # 3. Form.
    form_home = float(context.form.get(home_id, 0.0))
    form_away = float(context.form.get(away_id, 0.0))
    detail["form"] = {
        "home": form_home, "away": form_away,
        "home_games": int(context.form_games.get(home_id, 0)),
        "away_games": int(context.form_games.get(away_id, 0)),
    }
    take("form", (form_home / 2.0 - form_away / 2.0, form_away / 2.0 - form_home / 2.0, 0.0))

    # 4. Rest.
    rest_home = context.rest_effect(home_id, _tier_of(ratings, home_id))
    rest_away = context.rest_effect(away_id, _tier_of(ratings, away_id))
    detail["rest"] = {
        "home_days": context.rest_days.get(home_id),
        "away_days": context.rest_days.get(away_id),
        "home_bucket": context.rest_bucket(home_id),
        "away_bucket": context.rest_bucket(away_id),
        "home": rest_home, "away": rest_away,
    }
    take("rest", (rest_home / 2.0 - rest_away / 2.0, rest_away / 2.0 - rest_home / 2.0, 0.0))

    # 5. Who is missing.
    factor_home = float(context.attack_factor.get(home_id, 1.0))
    factor_away = float(context.attack_factor.get(away_id, 1.0))
    detail["lineup"] = {
        "home_missing": list(context.missing.get(home_id, [])),
        "away_missing": list(context.missing.get(away_id, [])),
        "home_factor": factor_home, "away_factor": factor_away,
    }
    take("lineup", (home * (factor_home - 1.0), away * (factor_away - 1.0), 0.0))

    # 6. Second opinion.
    opinion = context.second_opinion
    blended = False
    move = [0.0, 0.0, 0.0]
    if opinion is not None:
        home_view = opinion.teams.get(_int_or_none(home_id))
        away_view = opinion.teams.get(_int_or_none(away_id))
        own_off_h = float(ratings.offence.get(home_id, 0.0))
        own_def_h = float(ratings.defence.get(home_id, 0.0))
        own_off_a = float(ratings.offence.get(away_id, 0.0))
        own_def_a = float(ratings.defence.get(away_id, 0.0))
        own_t_h = float(ratings.tempo.get(home_id, 0.0))
        own_t_a = float(ratings.tempo.get(away_id, 0.0))
        if home_view is not None:
            move[0] += BLEND_WEIGHT * (home_view[0] - own_off_h)
            move[1] += BLEND_WEIGHT * (home_view[1] - own_def_h)
            move[2] += BLEND_WEIGHT * (home_view[2] - own_t_h)
            blended = True
        if away_view is not None:
            move[1] += BLEND_WEIGHT * (away_view[0] - own_off_a)
            move[0] += BLEND_WEIGHT * (away_view[1] - own_def_a)
            move[2] += BLEND_WEIGHT * (away_view[2] - own_t_a)
            blended = True
        detail["second_opinion"] = {
            "as_of": opinion.as_of,
            "weight": BLEND_WEIGHT,
            "home": None if home_view is None else [round(v, 2) for v in home_view],
            "away": None if away_view is None else [round(v, 2) for v in away_view],
            "own": {
                "home_offence": own_off_h, "home_defence": own_def_h, "home_tempo": own_t_h,
                "away_offence": own_off_a, "away_defence": own_def_a, "away_tempo": own_t_a,
            },
        }
    else:
        detail["second_opinion"] = {"absent": "; ".join(context.notes) or "not read"}
    detail["second_opinion"]["blended"] = blended and context.is_on("second_opinion")
    take("second_opinion", (move[0], move[1], move[2]))

    # Candidates: on the card only when the audit has added them.
    pace_home = float(context.pace_form.get(home_id, 0.0))
    pace_away = float(context.pace_form.get(away_id, 0.0))
    detail["pace_form"] = {"home": pace_home, "away": pace_away}
    take("pace_form", (0.0, 0.0, (pace_home + pace_away) / 2.0))

    luck_home = float(context.three_luck.get(home_id, 0.0))
    luck_away = float(context.three_luck.get(away_id, 0.0))
    detail["three_point_luck"] = {"home": luck_home, "away": luck_away}
    take("three_point_luck", (-luck_away, -luck_home, 0.0))

    # The strict reading REPLACES the single-game one: with "Who is missing" on,
    # its move swaps that layer's factor for the strict factor; with it off, it
    # applies the strict factor alone. Either way one absence is counted once.
    lineup_on = context.is_on("lineup")
    strict_home = float(context.attack_factor_strict.get(home_id, 1.0))
    strict_away = float(context.attack_factor_strict.get(away_id, 1.0))
    ratio_home = strict_home / (factor_home if lineup_on else 1.0)
    ratio_away = strict_away / (factor_away if lineup_on else 1.0)
    detail["lineup_strict"] = {
        "home_missing": list(context.missing_strict.get(home_id, [])),
        "away_missing": list(context.missing_strict.get(away_id, [])),
        "home_factor": strict_home, "away_factor": strict_away,
    }
    take("lineup_strict", (home * (ratio_home - 1.0), away * (ratio_away - 1.0), 0.0))

    detail["switches"] = {key: context.is_on(key) for key in SWITCHABLE}
    detail["audit_as_of"] = context.audit_as_of
    detail["shadow"] = shadow

    if not (np.isfinite(home) and np.isfinite(away) and np.isfinite(possessions)) or possessions <= 0:
        return base
    return _with(
        base,
        home_points_per_possession=home / scale,
        away_points_per_possession=away / scale,
        possessions=float(possessions),
        layers=tuple(layers),
        context=detail,
    )


def _int_or_none(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _with(base, **changes):
    from dataclasses import replace

    return replace(base, **changes)


def summary(context: DayContext, *, teams: Mapping | None = None) -> str:
    """One line for the log: what tonight's context carried."""
    formed = len(context.form)
    rested = sum(1 for v in context.rest_days.values() if v is not None)
    missing = sum(len(v) for v in context.missing.values())
    opinion = (
        f"second opinion from {context.second_opinion.as_of} on {len(context.second_opinion)} teams"
        if context.second_opinion is not None
        else "no second opinion"
    )
    line = (
        f"Tonight's context for {context.day}: form on {formed} team(s), rest on "
        f"{rested}, {missing} rotation player(s) treated as missing, {opinion}."
    )
    if context.notes:
        line += " " + " ".join(n.rstrip(".") + "." for n in context.notes)
    return line
