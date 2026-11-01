"""Same-day box scores from ESPN, for the games hoopR has not published yet.

**Why this exists.** Every in-season rating, form layer and settlement in this
lab reads hoopR's release assets, which are themselves built from ESPN's feed.
On 2026-11-01 the 2027 team box, player box and play-by-play were all "not
published upstream yet", so the model had no result from the season it was
pricing and could only ever price on the preseason prior. hoopR rebuilds
nightly once it starts, but nothing here controls when it starts or whether a
night is missed, and a model whose evidence depends on another project's cron
goes quietly stale the night that cron does not run.

So this reads ESPN directly, in hoopR's own column names, for exactly the
completed games hoopR does not hold. `build_datasets` takes hoopR's row
wherever both exist, so the supplement only ever fills a gap and never
overrides a published row. The ids are ESPN's on both sides (hoopR copies
them), so no name is ever resolved here.

Per game it writes:

* two team rows (`team_box` columns: shooting splits, rebounds, assists,
  steals, blocks, turnovers, fouls);
* one row per athlete (`player_box` columns, `did_not_play` kept);
* one segment row: periods played and the first-half score, from the
  scoreboard's line scores, so `ratings.prepare` can count the game. The
  first-basket columns are left empty because only the play-by-play knows
  them, and settlement refuses those markets on an empty field rather than
  guessing.

Free, keyless, no credit. A failed request leaves that game out and says so;
it is fetched again next run.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import RAW_DIR

BASE = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
SCOREBOARD = BASE + "/scoreboard?dates={day}&groups=50&limit=500"
SUMMARY = BASE + "/summary?event={game_id}"
USER_AGENT = "Mozilla/5.0 (cbb-betting-lab)"
EASTERN = "America/New_York"
#: Seconds between summary requests, so a 200-game Monday is polite.
PAUSE_S = 0.15

DIRECTORY = "espn_box"
KINDS = ("team_box", "player_box", "segments")

#: ESPN's team statistic name -> hoopR's column. A "made-attempted" pair is
#: split into two columns.
TEAM_STATS = {
    "fieldGoalsMade-fieldGoalsAttempted": ("field_goals_made", "field_goals_attempted"),
    "threePointFieldGoalsMade-threePointFieldGoalsAttempted": (
        "three_point_field_goals_made", "three_point_field_goals_attempted"),
    "freeThrowsMade-freeThrowsAttempted": ("free_throws_made", "free_throws_attempted"),
    "totalRebounds": "total_rebounds",
    "offensiveRebounds": "offensive_rebounds",
    "defensiveRebounds": "defensive_rebounds",
    "assists": "assists",
    "steals": "steals",
    "blocks": "blocks",
    "turnovers": "turnovers",
    "teamTurnovers": "team_turnovers",
    "totalTurnovers": "total_turnovers",
    "fouls": "fouls",
    "technicalFouls": "technical_fouls",
    "flagrantFouls": "flagrant_fouls",
    "pointsInPaint": "points_in_paint",
    "fastBreakPoints": "fast_break_points",
    "turnoverPoints": "turnover_points",
    "largestLead": "largest_lead",
}

#: ESPN's athlete stat label -> hoopR's column.
PLAYER_STATS = {
    "MIN": "minutes",
    "PTS": "points",
    "FG": ("field_goals_made", "field_goals_attempted"),
    "3PT": ("three_point_field_goals_made", "three_point_field_goals_attempted"),
    "FT": ("free_throws_made", "free_throws_attempted"),
    "REB": "rebounds",
    "AST": "assists",
    "TO": "turnovers",
    "STL": "steals",
    "BLK": "blocks",
    "OREB": "offensive_rebounds",
    "DREB": "defensive_rebounds",
    "PF": "fouls",
}


class EspnError(RuntimeError):
    """A request or a payload this module could not use."""


def path(kind: str, season: int, raw_dir: Path | str | None = None) -> Path:
    root = Path(raw_dir) if raw_dir else Path(RAW_DIR)
    return root / CBB.data_dir_segment / DIRECTORY / f"{kind}_{int(season)}.parquet"


def load(kind: str, season: int, raw_dir: Path | str | None = None) -> pd.DataFrame:
    """The cached supplement for a season, empty when there is none."""
    target = path(kind, season, raw_dir)
    if not target.is_file():
        return pd.DataFrame()
    return pd.read_parquet(target)


def _get(url: str, timeout: float = 30.0) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read())
    except (urllib.error.URLError, OSError, TimeoutError, ValueError) as exc:
        raise EspnError(f"{url}: {type(exc).__name__}: {exc}") from exc


def _number(text) -> float | None:
    try:
        return float(str(text).strip())
    except (TypeError, ValueError):
        return None


def _split(text) -> tuple[float | None, float | None]:
    parts = str(text or "").split("-")
    if len(parts) != 2:
        return None, None
    return _number(parts[0]), _number(parts[1])


def completed_games(day: str, fetch=_get) -> list[dict]:
    """Completed Division I games ESPN files under this Eastern date."""
    payload = fetch(SCOREBOARD.format(day=day.replace("-", "")))
    out = []
    for event in payload.get("events", []):
        competition = (event.get("competitions") or [{}])[0]
        status = (competition.get("status") or event.get("status") or {}).get("type", {})
        if not status.get("completed"):
            continue
        sides = {c.get("homeAway"): c for c in competition.get("competitors", [])}
        if set(sides) != {"home", "away"}:
            continue
        out.append({"event": event, "competition": competition, "sides": sides})
    return out


def _game_time(event: dict) -> pd.Timestamp:
    return pd.Timestamp(event.get("date")).tz_convert(EASTERN)


def segment_row(game: dict) -> dict:
    """Periods played and the first-half score, from the line scores."""
    home, away = game["sides"]["home"], game["sides"]["away"]
    home_lines = [_number(x.get("value", x.get("displayValue"))) for x in home.get("linescores", [])]
    away_lines = [_number(x.get("value", x.get("displayValue"))) for x in away.get("linescores", [])]
    periods = min(len(home_lines), len(away_lines))
    return {
        "game_id": int(game["event"]["id"]),
        "periods": periods if periods else pd.NA,
        "overtime": periods > 2 if periods else pd.NA,
        "home_score_h1": home_lines[0] if periods else pd.NA,
        "away_score_h1": away_lines[0] if periods else pd.NA,
        "first_basket_athlete_id": pd.NA,
        "first_basket_team_id": pd.NA,
        "home_first_basket_athlete_id": pd.NA,
        "away_first_basket_athlete_id": pd.NA,
        "source": "espn",
    }


def box_rows(game: dict, summary: dict, season: int) -> tuple[list[dict], list[dict]]:
    """hoopR-shaped team rows and player rows for one completed game."""
    event, sides = game["event"], game["sides"]
    game_id = int(event["id"])
    when = _game_time(event)
    common = {
        "game_id": game_id,
        "season": int(season),
        "season_type": int((event.get("season") or {}).get("type") or 2),
        "game_date": when.date().isoformat(),
        "game_date_time": when,
    }
    meta = {}
    for side, competitor in sides.items():
        team = competitor.get("team", {})
        meta[side] = {
            "team_id": int(team.get("id")),
            "team_display_name": team.get("displayName"),
            "team_abbreviation": team.get("abbreviation"),
            "team_location": team.get("location"),
            "team_name": team.get("name"),
            "team_short_display_name": team.get("shortDisplayName"),
            "team_score": _number(competitor.get("score")),
            "team_winner": bool(competitor.get("winner")),
        }
    other = {"home": "away", "away": "home"}

    teams: list[dict] = []
    stats_by_team = {}
    for block in (summary.get("boxscore") or {}).get("teams", []):
        team_id = int((block.get("team") or {}).get("id", -1))
        stats_by_team[team_id] = {s.get("name"): s.get("displayValue") for s in block.get("statistics", [])}
    for side in ("home", "away"):
        mine, theirs = meta[side], meta[other[side]]
        stats = stats_by_team.get(mine["team_id"])
        if stats is None:
            raise EspnError(f"game {game_id}: no box score for team {mine['team_id']}")
        row = {**common, **mine, "team_home_away": side,
               "opponent_team_id": theirs["team_id"],
               "opponent_team_display_name": theirs["team_display_name"],
               "opponent_team_score": theirs["team_score"]}
        for name, column in TEAM_STATS.items():
            value = stats.get(name)
            if isinstance(column, tuple):
                row[column[0]], row[column[1]] = _split(value)
            else:
                row[column] = _number(value)
        teams.append(row)

    players: list[dict] = []
    for block in (summary.get("boxscore") or {}).get("players", []):
        team_id = int((block.get("team") or {}).get("id", -1))
        side = "home" if team_id == meta["home"]["team_id"] else "away"
        mine, theirs = meta[side], meta[other[side]]
        for group in block.get("statistics", []):
            labels = group.get("names") or group.get("labels") or []
            for entry in group.get("athletes", []):
                athlete = entry.get("athlete") or {}
                row = {**common, "athlete_id": _number(athlete.get("id")),
                       "athlete_display_name": athlete.get("displayName"),
                       "team_id": team_id, "home_away": side,
                       "team_score": mine["team_score"],
                       "opponent_team_id": theirs["team_id"],
                       "opponent_team_score": theirs["team_score"],
                       "starter": bool(entry.get("starter")),
                       "did_not_play": bool(entry.get("didNotPlay")),
                       "ejected": bool(entry.get("ejected"))}
                values = entry.get("stats") or []
                for label, value in zip(labels, values):
                    column = PLAYER_STATS.get(label)
                    if column is None:
                        continue
                    if isinstance(column, tuple):
                        row[column[0]], row[column[1]] = _split(value)
                    else:
                        row[column] = _number(value)
                players.append(row)
    return teams, players


@dataclass
class Report:
    days: list[str] = field(default_factory=list)
    already_published: int = 0
    already_cached: int = 0
    fetched: int = 0
    failed: list[str] = field(default_factory=list)

    def line(self) -> str:
        span = f"{self.days[0]} to {self.days[-1]}" if self.days else "no day"
        return (
            f"ESPN supplement, {span}: {self.fetched} game(s) fetched, "
            f"{self.already_published} already published by hoopR, "
            f"{self.already_cached} already cached, {len(self.failed)} failed"
            + (f" ({'; '.join(self.failed[:5])})" if self.failed else "") + "."
        )


def supplement(
    season: int,
    *,
    first_day: str,
    last_day: str,
    published_ids: set[int],
    raw_dir: Path | str | None = None,
    fetch=_get,
    pause_s: float = PAUSE_S,
) -> Report:
    """Fetch every completed game on [first_day, last_day] that hoopR lacks.

    Appends to the season's cached supplement and drops any cached game hoopR
    has since published, so the supplement shrinks to nothing as hoopR
    catches up.
    """
    report = Report()
    cached = {kind: load(kind, season, raw_dir) for kind in KINDS}
    have = set(cached["team_box"]["game_id"].astype(int)) if not cached["team_box"].empty else set()
    new = {kind: [] for kind in KINDS}
    day = date.fromisoformat(first_day)
    end = date.fromisoformat(last_day)
    while day <= end:
        stamp = day.isoformat()
        report.days.append(stamp)
        try:
            games = completed_games(stamp, fetch=fetch)
        except EspnError as exc:
            report.failed.append(f"scoreboard {stamp}: {exc}")
            games = []
        for game in games:
            game_id = int(game["event"]["id"])
            if game_id in published_ids:
                report.already_published += 1
                continue
            if game_id in have:
                report.already_cached += 1
                continue
            try:
                summary = fetch(SUMMARY.format(game_id=game_id))
                teams, players = box_rows(game, summary, season)
            except EspnError as exc:
                report.failed.append(str(exc))
                continue
            new["team_box"].extend(teams)
            new["player_box"].extend(players)
            new["segments"].append(segment_row(game))
            have.add(game_id)
            report.fetched += 1
            if pause_s:
                time.sleep(pause_s)
        day += timedelta(days=1)

    for kind in KINDS:
        frames = [f for f in (cached[kind], pd.DataFrame(new[kind])) if not f.empty]
        if not frames:
            continue
        frame = pd.concat(frames, ignore_index=True)
        frame = frame[~frame["game_id"].astype(int).isin(published_ids)]
        target = path(kind, season, raw_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        if "game_date_time" in frame.columns:
            frame["game_date_time"] = pd.to_datetime(frame["game_date_time"], utc=True).dt.tz_convert(EASTERN)
        frame.to_parquet(target, index=False)
    return report
