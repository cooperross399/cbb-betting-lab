#!/usr/bin/env python3
"""The feeds behind the CBB site's pages beyond the board.

Four JSON files, two kinds of source:

* `ratings.json` and `season.json` read the **fit the board priced on**
  (`models.ratings.last_fit`, handed in by `build_board_json.main`), so the
  ratings table and the projected conference standings are the numbers the
  card used that run, never a second fit.
* `record.json` and `tracker.json` read the **frozen boards and their
  finals** under `<data>/history`, the same files the Results page settles
  from, so every calibration bucket and every graded bet traces to a board
  as it was posted.

Nothing here fetches a price, spends a credit, places a bet, or names the
source of the card's second opinion. Every published figure carries the
count it rests on, and an interval is published beside every rate.
"""

from __future__ import annotations

import importlib.util
import json
import math
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOGOS = HERE / "logos"

#: ESPN conference ids, as hoopR's schedule carries them in
#: `home_conference_id` / `away_conference_id`. A name the map lacks is
#: printed as "Conference <id>", never guessed.
CONFERENCES = {
    1: "America East", 2: "ACC", 3: "Atlantic 10", 4: "Big East", 5: "Big Sky", 6: "Big South",
    7: "Big Ten", 8: "Big 12", 9: "Big West", 10: "CAA", 11: "Conference USA", 12: "Ivy League",
    13: "MAAC", 14: "MAC", 15: "SWAC", 16: "MEAC", 17: "Southland", 18: "Missouri Valley",
    19: "Northeast", 20: "Ohio Valley", 21: "Pac-12", 22: "Patriot League", 23: "SEC",
    24: "Southern", 25: "Summit League", 26: "WAC", 27: "Sun Belt", 29: "West Coast",
    30: "ASUN", 44: "Mountain West", 45: "Horizon League", 46: "ASUN", 49: "Summit League",
    62: "American",
}

#: Win-chance bands for the calibration table: the favourite's published
#: chance, so every game lands once.
RECORD_BUCKETS = ((0.50, 0.55), (0.55, 0.60), (0.60, 0.65), (0.65, 0.70), (0.70, 0.80), (0.80, 1.01))
MARKET_BUCKET_WIDTH = 0.05
MARKET_BUCKET_MIN_GAMES = 10
#: A fallback for a fit that reports no residual spread, in points. The
#: fit's own number is used whenever it carries one.
FALLBACK_MARGIN_SD = 11.0
#: Days a board's finals are asked for again before an incomplete day is
#: cached as it stands (the Results page's own patience).
PATIENCE_DAYS = 14
SPORT = "cbb"

TIER_LABELS = {"high_major": "High major", "mid_major": "Mid major", "low_major": "Low major", "unplaced": "Unplaced"}


# ----------------------------------------------------------------------------
# small helpers


def _num(value):
    """A finite float, or None. Never a NaN into a JSON file."""
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if math.isfinite(f) else None


def _int(value):
    try:
        if value is None or (isinstance(value, float) and not math.isfinite(value)):
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _round(value, places=3):
    f = _num(value)
    return None if f is None else round(f, places)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _dump(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def wilson(wins: int, n: int, z: float = 1.96) -> list | None:
    """The Wilson score interval, as the NHL lab's calibration page prints it."""
    if n <= 0:
        return None
    p = wins / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [round(max(0.0, centre - half), 4), round(min(1.0, centre + half), 4)]


def implied(american) -> float | None:
    a = _num(american)
    if a is None or a == 0:
        return None
    return 100.0 / (a + 100.0) if a > 0 else -a / (-a + 100.0)


def no_vig_home(moneyline: dict | None) -> float | None:
    """The market's home chance with the margin removed, from a board's
    `moneyline.current` pair, or None when either side is missing."""
    if not isinstance(moneyline, dict):
        return None
    h, a = implied(moneyline.get("home")), implied(moneyline.get("away"))
    if h is None or a is None or h + a <= 0:
        return None
    return h / (h + a)


def payout(american) -> float | None:
    a = _num(american)
    if a is None or a == 0:
        return None
    return a / 100.0 if a > 0 else 100.0 / -a


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _module(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TIER_RANK = {"high_major": 0, "mid_major": 1, "low_major": 2}


def higher_tier(*values) -> str | None:
    """The higher of the tiers named, high over mid over low; an unplaced
    side never outranks a placed one."""
    placed = [str(v).strip().lower() for v in values if v is not None and str(v).strip().lower() in TIER_RANK]
    if not placed:
        return next((str(v) for v in values if v), None)
    return min(placed, key=TIER_RANK.get)


def tier_label(value) -> str | None:
    text = str(getattr(value, "value", value) or "").strip()
    return TIER_LABELS.get(text, text) or None


def conference_name(conference_id) -> str | None:
    cid = _int(conference_id)
    if cid is None:
        return None
    return CONFERENCES.get(cid, f"Conference {cid}")


# ----------------------------------------------------------------------------
# the model pages: ratings.json and season.json


def _schedule(lab: Path, season: int):
    from cbb_betting_lab.reports import card_matchups  # type: ignore

    return card_matchups.load_schedule(int(season), lab / "data" / "raw")


def team_table(fit: dict, schedule) -> dict[int, dict]:
    """Every team the fit rates, with the schedule's own name, abbreviation
    and conference. Keyed by the integer team id."""
    rated = fit["ratings"]
    info: dict[int, dict] = {}
    counts: dict[int, dict[int, int]] = {}
    for side in ("home", "away"):
        cols = [f"{side}_id", f"{side}_abbreviation", f"{side}_display_name", f"{side}_location", f"{side}_conference_id"]
        present = [c for c in cols if c in schedule.columns]
        if f"{side}_id" not in present:
            continue
        frame = schedule[present].dropna(subset=[f"{side}_id"])
        for row in frame.itertuples(index=False):
            values = dict(zip(present, row))
            tid = _int(values.get(f"{side}_id"))
            if tid is None:
                continue
            entry = info.setdefault(tid, {"id": tid, "abbr": None, "name": None, "short": None})
            abbr = values.get(f"{side}_abbreviation")
            if entry["abbr"] is None and isinstance(abbr, str) and abbr.strip():
                entry["abbr"] = abbr.strip()
            name = values.get(f"{side}_display_name")
            if entry["name"] is None and isinstance(name, str) and name.strip():
                entry["name"] = name.strip()
            short = values.get(f"{side}_location")
            if entry["short"] is None and isinstance(short, str) and short.strip():
                entry["short"] = short.strip()
            cid = _int(values.get(f"{side}_conference_id"))
            if cid is not None:
                counts.setdefault(tid, {})[cid] = counts.setdefault(tid, {}).get(cid, 0) + 1
    context = fit.get("context")
    out: dict[int, dict] = {}
    for key, off in getattr(rated, "offence", {}).items():
        tid = _int(key)
        if tid is None:
            continue
        de = _num(getattr(rated, "defence", {}).get(key))
        off = _num(off)
        tempo = _num(getattr(rated, "tempo", {}).get(key))
        base = info.get(tid, {"id": tid, "abbr": None, "name": None, "short": None})
        conference = max(counts.get(tid, {}).items(), key=lambda kv: kv[1])[0] if counts.get(tid) else None
        try:
            tier = tier_label(rated.tier_of(key))
        except Exception:  # noqa: BLE001 - a team the tier table cannot place
            tier = None
        games = None
        team_games = getattr(rated, "team_games", None)
        if isinstance(team_games, dict):
            games = _int(team_games.get(key))
        form = None
        if context is not None:
            form = _round(getattr(context, "form", {}).get(key), 3)
        entry = {
            **base,
            "abbr": base["abbr"] or (base["short"] or str(tid))[:4].upper(),
            "name": base["name"] or base["short"] or str(tid),
            "conferenceId": conference,
            "conference": conference_name(conference),
            "tier": tier,
            "offence": _round(off, 2), "defence": _round(de, 2),
            "net": None if off is None or de is None else round(off - de, 2),
            "tempo": _round(tempo, 2),
            "games": games,
            "form": form,
            "key": key,
        }
        if (LOGOS / f"{entry['abbr']}.png").is_file():
            entry["logo"] = f"./logos/{entry['abbr']}.png"
        out[tid] = entry
    return out


def ratings_page(fit: dict, teams: dict[int, dict], day: date, board: dict | None = None) -> dict:
    rated = fit["ratings"]
    tonight: dict[str, dict] = {}
    for g in (board or {}).get("games") or []:
        if not isinstance(g, dict) or not g.get("home") or not g.get("away"):
            continue
        label = f"{g['away'].get('abbr')} @ {g['home'].get('abbr')}"
        tonight[str(g["home"].get("abbr"))] = {"id": g.get("id"), "label": label, "vs": f"v {g['away'].get('abbr')}"}
        tonight[str(g["away"].get("abbr"))] = {"id": g.get("id"), "label": label, "vs": f"@ {g['home'].get('abbr')}"}
    rows = sorted((t for t in teams.values() if t["net"] is not None), key=lambda t: -t["net"])
    for rank, t in enumerate(rows, start=1):
        t["rank"] = rank
        if t["abbr"] in tonight:
            t["tonight"] = tonight[t["abbr"]]
    tiers: dict[str, int] = {}
    for t in rows:
        tiers[t["tier"] or "Unplaced"] = tiers.get(t["tier"] or "Unplaced", 0) + 1
    published = [{k: v for k, v in t.items() if k != "key"} for t in rows]
    return {
        "generatedAt": _now(),
        "season": int(fit.get("season") or 0),
        "asOf": str(fit.get("day") or day.isoformat()),
        "through": str(getattr(rated, "priced_through", "") or fit.get("day") or ""),
        "league": {
            "efficiency": _round(getattr(rated, "league_efficiency", None), 2),
            "tempo": _round(getattr(rated, "league_tempo", None), 2),
            "marginSd": _round(getattr(rated, "residual_sd", None), 2),
        },
        "tierCounts": tiers,
        "rated": len(published),
        "teams": published,
        "note": (
            "Offence and defence are points per 100 possessions against the Division I average, "
            "after the strength of every opponent played; defence above zero allows more. Net is "
            "offence minus defence. Tempo is possessions per game against the average. Early in a "
            "season each number leans on the team's prior; the weight moves to this season's games as "
            "they are played."
        ),
    }


def season_page(fit: dict, teams: dict[int, dict], schedule, day: date) -> dict:
    """Current and projected conference standings from the fit's ratings.

    Projected wins are **expected wins**: the sum, over each team's remaining
    games, of its chance of winning each one, priced by the lab's `matchup`
    on strength and venue alone (tonight's layers need tonight's inputs) and
    read through a normal margin at the fit's own residual spread. No
    season is simulated, so there is no "chance to finish first"; the page
    says so.
    """
    import pandas as pd  # type: ignore

    from cbb_betting_lab.models import ratings as R  # type: ignore

    rated = fit["ratings"]
    sd = _num(getattr(rated, "residual_sd", None)) or FALLBACK_MARGIN_SD
    frame = schedule.copy()
    when = pd.to_datetime(frame.get("game_date", frame.get("date")), errors="coerce", utc=True)
    frame = frame.assign(_day=when.dt.date)
    completed = frame.get("status_type_completed")
    done = completed.fillna(False).astype(bool) if completed is not None else pd.Series(False, index=frame.index)
    hs, as_ = pd.to_numeric(frame.get("home_score"), errors="coerce"), pd.to_numeric(frame.get("away_score"), errors="coerce")
    # A game dated on or after the page's day is still to be played from the
    # page's point of view, whatever the cached flag says (a page built for
    # a past day on a finished schedule projects the games after it, which is
    # what makes it testable); one before the day that never completed was
    # postponed or cancelled and counts in neither column.
    played = frame[done & hs.notna() & as_.notna() & (frame["_day"] < day)]
    remaining = frame[frame["_day"] >= day]

    by_id = {t["id"]: t for t in teams.values()}
    rec: dict[int, dict] = {tid: {"w": 0, "l": 0, "cw": 0, "cl": 0, "pw": 0.0, "pl": 0.0, "pcw": 0.0, "pcl": 0.0, "left": 0, "cleft": 0} for tid in teams}

    def same_conference(row) -> bool:
        h, a = _int(row.get("home_conference_id")), _int(row.get("away_conference_id"))
        return h is not None and h == a

    for row in played.to_dict("records"):
        h, a = _int(row.get("home_id")), _int(row.get("away_id"))
        if h not in rec or a not in rec:
            continue
        hf, af = float(row["home_score"]), float(row["away_score"])
        if hf == af:
            continue
        winner, loser = (h, a) if hf > af else (a, h)
        rec[winner]["w"] += 1
        rec[loser]["l"] += 1
        if same_conference(row):
            rec[winner]["cw"] += 1
            rec[loser]["cl"] += 1

    priced = 0
    for row in remaining.to_dict("records"):
        h, a = _int(row.get("home_id")), _int(row.get("away_id"))
        if h not in rec or a not in rec:
            continue
        neutral = bool(row.get("neutral_site"))
        try:
            game = R.matchup(
                rated,
                home_team_id=by_id[h]["key"], away_team_id=by_id[a]["key"],
                venue_state="neutral" if neutral else "home",
                local_team_id=None if neutral else by_id[h]["key"],
                venue_id=_int(row.get("venue_id")),
                event_id=str(row.get("game_id") or row.get("id") or ""),
            )
        except Exception:  # noqa: BLE001 - one game the model cannot price is left out of the projection
            continue
        if not getattr(game, "priceable", False):
            continue
        margin = (float(game.home_points_per_possession) - float(game.away_points_per_possession)) * float(game.possessions)
        p_home = _normal_cdf(margin / sd)
        if not math.isfinite(p_home):
            continue
        priced += 1
        conf = same_conference(row)
        for tid, p in ((h, p_home), (a, 1.0 - p_home)):
            rec[tid]["pw"] += p
            rec[tid]["pl"] += 1.0 - p
            rec[tid]["left"] += 1
            if conf:
                rec[tid]["pcw"] += p
                rec[tid]["pcl"] += 1.0 - p
                rec[tid]["cleft"] += 1

    conferences: dict[int | None, list] = {}
    for tid, t in teams.items():
        r = rec[tid]
        conferences.setdefault(t["conferenceId"], []).append({
            "id": tid, "abbr": t["abbr"], "name": t["name"], "short": t["short"], "tier": t["tier"], "net": t["net"],
            "logo": t.get("logo"),
            "record": {"w": r["w"], "l": r["l"]},
            "confRecord": {"w": r["cw"], "l": r["cl"]},
            "projConf": {"w": round(r["cw"] + r["pcw"], 1), "l": round(r["cl"] + r["pcl"], 1)},
            "projOverall": {"w": round(r["w"] + r["pw"], 1), "l": round(r["l"] + r["pl"], 1)},
            "remaining": r["left"], "confRemaining": r["cleft"],
        })
    out_confs = []
    for cid, members in conferences.items():
        members.sort(key=lambda m: (-(m["projConf"]["w"] - m["projConf"]["l"]), -(m["net"] or -99.0)))
        for rank, m in enumerate(members, start=1):
            m["projRank"] = rank
        out_confs.append({"id": cid, "name": conference_name(cid) or "No conference", "teams": members})
    out_confs.sort(key=lambda c: (c["name"] == "No conference", -(max((m["net"] or -99.0) for m in c["teams"]) if c["teams"] else -99.0)))
    phase = "regular" if len(played) else "preseason"
    return {
        "generatedAt": _now(),
        "season": int(fit.get("season") or 0),
        "asOf": day.isoformat(),
        "phase": phase,
        "played": int(len(played)),
        "remaining": int(len(remaining)),
        "projected": priced,
        "conferences": out_confs,
        "method": [
            "Current records count every completed game on the cached schedule; a conference game is one between two members of the same conference.",
            "Projected records add, for each game still to play, the team's chance of winning it: the lab's ratings on strength and venue, read through a normal margin at the fit's own spread. They are expected wins, not a simulation, so no chance to finish first is published.",
            "Tonight's layers (last five, rest, who is missing, the second opinion) need tonight's inputs and are not applied to games weeks away.",
            "Rank is by projected conference wins minus losses, then net rating.",
        ],
    }


def write_model_pages(lab: Path, out: Path, day: date, fit: dict, board: dict | None) -> list[str]:
    """ratings.json and season.json into `out`, from the fit the board priced
    on. Returns the files written; nothing when there was no fit."""
    if not fit or fit.get("ratings") is None:
        return []
    schedule = _schedule(Path(lab), int(fit.get("season") or 0))
    teams = team_table(fit, schedule)
    written = []
    _dump(Path(out) / "ratings.json", ratings_page(fit, teams, day, board))
    written.append("ratings.json")
    _dump(Path(out) / "season.json", season_page(fit, teams, schedule, day))
    written.append("season.json")
    return written


# ----------------------------------------------------------------------------
# the record pages: record.json and tracker.json, from the frozen boards


def _kept_finals(hist: Path, d: date) -> dict | None:
    """Finals for a day from what is already on disk: the settled day's
    graded games, else the finals cache. None when neither is kept."""
    settled = hist / "settled" / f"{d.isoformat()}.json"
    try:
        if settled.is_file():
            night = json.loads(settled.read_text(encoding="utf-8"))
            graded = night.get("graded") if isinstance(night, dict) else None
            if isinstance(graded, list) and graded:
                out = {}
                for g in graded:
                    if isinstance(g, dict) and isinstance(g.get("home"), dict) and isinstance(g.get("away"), dict):
                        hf, af = _int(g["home"].get("final")), _int(g["away"].get("final"))
                        if hf is not None and af is not None:
                            out[str(g.get("id"))] = {"home": hf, "away": af, "finish": g.get("finish") or "REG"}
                if out:
                    return out
        cached = hist / "finals" / f"{d.isoformat()}.json"
        if cached.is_file():
            payload = json.loads(cached.read_text(encoding="utf-8"))
            return payload if isinstance(payload, dict) else None
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError):
        return None
    return None


def graded_games(hist: Path, today: date, settle=None, fetch: bool = True) -> list[dict]:
    """Every frozen board game before today that has a final, newest first.

    Finals come from the settled day when the Results page kept its graded
    games, else from `history/finals/<day>.json`, else (when `fetch`) from the
    scoreboard, cached once every game on the board has a final or the day is
    older than PATIENCE_DAYS. A day whose scoreboard cannot be read is left
    out of this build and asked for again next time.
    """
    settle = settle or _module("settle_results")
    out: list[dict] = []
    for d in settle.board_days(hist, today - timedelta(days=1)):
        path = settle.frozen_board(hist, d)
        if path is None:
            continue
        try:
            board = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if not isinstance(board, dict):
            continue
        games = [g for g in board.get("games") or [] if isinstance(g, dict)]
        finals = _kept_finals(hist, d)
        if finals is None and fetch:
            try:
                finals = settle.finals(SPORT, d)
            except settle.FETCH_ERRORS:
                finals = None
            if finals:
                complete = all(str(g.get("id")) in finals for g in games)
                if complete or d <= today - timedelta(days=PATIENCE_DAYS):
                    (hist / "finals").mkdir(parents=True, exist_ok=True)
                    (hist / "finals" / f"{d.isoformat()}.json").write_text(json.dumps(finals, indent=1), encoding="utf-8")
        if not finals:
            continue
        for g in games:
            f = finals.get(str(g.get("id")))
            if not f:
                continue
            hf, af = _int(f.get("home")), _int(f.get("away"))
            if hf is None or af is None:
                continue
            out.append({"date": d.isoformat(), "game": g, "home": hf, "away": af, "finish": f.get("finish") or "REG", "teams": board.get("teams") or {}})
    out.sort(key=lambda r: (r["date"], str(r["game"].get("tip") or "")), reverse=True)
    return out


def _bucket_rows(samples: list[tuple[float, bool]], edges=RECORD_BUCKETS) -> list[dict]:
    rows = []
    for low, high in edges:
        inside = [(p, hit) for p, hit in samples if low <= p < high]
        n = len(inside)
        wins = sum(1 for _, hit in inside if hit)
        rows.append({
            "low": low, "high": min(high, 1.0), "games": n,
            "predicted": round(sum(p for p, _ in inside) / n, 4) if n else None,
            "actual": round(wins / n, 4) if n else None,
            "interval": wilson(wins, n),
        })
    return rows


def _market_buckets(samples: list[tuple[float, bool]]) -> list[dict]:
    """Five-point bands on the favoured side's chance, merged upward until
    each holds MARKET_BUCKET_MIN_GAMES, with Wilson intervals."""
    edges = []
    p = 0.50
    while p < 1.0 - 1e-9:
        edges.append((round(p, 2), round(min(p + MARKET_BUCKET_WIDTH, 1.01), 2)))
        p += MARKET_BUCKET_WIDTH
    raw = _bucket_rows(samples, edges)
    merged: list[dict] = []
    pending: list[tuple[float, bool]] = []
    low_open = None
    for row in raw:
        inside = [(q, hit) for q, hit in samples if row["low"] <= q < row["high"]]
        if low_open is None:
            low_open = row["low"]
        pending.extend(inside)
        if len(pending) >= MARKET_BUCKET_MIN_GAMES:
            wins = sum(1 for _, hit in pending if hit)
            merged.append({"low": low_open, "high": min(row["high"], 1.0), "games": len(pending),
                           "predicted": round(sum(q for q, _ in pending) / len(pending), 4),
                           "actual": round(wins / len(pending), 4), "interval": wilson(wins, len(pending))})
            pending, low_open = [], None
    if pending and merged:
        last = merged[-1]
        combined = [(q, hit) for q, hit in samples if last["low"] <= q < 1.01]
        wins = sum(1 for _, hit in combined if hit)
        merged[-1] = {"low": last["low"], "high": 1.0, "games": len(combined),
                      "predicted": round(sum(q for q, _ in combined) / len(combined), 4),
                      "actual": round(wins / len(combined), 4), "interval": wilson(wins, len(combined))}
    elif pending:
        wins = sum(1 for _, hit in pending if hit)
        merged.append({"low": low_open, "high": 1.0, "games": len(pending),
                       "predicted": round(sum(q for q, _ in pending) / len(pending), 4),
                       "actual": round(wins / len(pending), 4), "interval": wilson(wins, len(pending))})
    return merged


def _side_abbr(pick: dict, g: dict) -> str | None:
    side = pick.get("side")
    if side in ("home", "away"):
        return (g.get(side) or {}).get("abbr")
    return None


def _closing_point(series, tip):
    """The last point of a line series at or before tip, or None."""
    if not isinstance(series, list):
        return None
    best = None
    for point in series:
        if not isinstance(point, dict):
            continue
        value = _num(point.get("v"))
        stamp = str(point.get("t") or "")
        if value is None or (tip and stamp and stamp > str(tip)):
            continue
        best = value
    return best


def closing_value(pick: dict, game: dict, lines: dict | None) -> dict | None:
    """How a spread or total pick's line compares with the last line the board
    recorded for the game before tip, in points, from the bettor's side.

    Positive means the pick got a better number than the close. Moneyline picks
    are left out: the line history keeps only the home price, and grading one
    side of a market and not the other would bias the share."""
    market = str(pick.get("market") or "").lower()
    side, line = pick.get("side"), _num(pick.get("line"))
    if line is None or not isinstance(lines, dict):
        return None
    tip = game.get("tip")
    if market == "spread" and side in ("home", "away"):
        close_home = _closing_point(lines.get("spread"), tip)
        if close_home is None:
            return None
        close = close_home if side == "home" else -close_home
        return {"close": close, "points": round(line - close, 2)}
    if market == "total" and side in ("over", "under"):
        close = _closing_point(lines.get("total"), tip)
        if close is None:
            return None
        return {"close": close, "points": round((close - line) if side == "over" else (line - close), 2)}
    return None


def load_lines(hist: Path):
    """`history/lines/<day>.json` per day, read once: the per-build line
    series `site_history.py` keeps. A day with no file is an empty mapping."""
    cache: dict[str, dict] = {}

    def lines_for(day: str) -> dict:
        if day not in cache:
            try:
                payload = json.loads((Path(hist) / "lines" / f"{day}.json").read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                payload = {}
            cache[day] = payload if isinstance(payload, dict) else {}
        return cache[day]

    return lines_for


def record_page(graded: list[dict], today: date, lines_for=None) -> dict:
    """Calibration of the published win chances against finals, Brier against
    the frozen no-vig market, the spread and total chances by band, and
    which way the moneyline moved after a pick. Accuracy only, never a
    return: the returns are on All results."""
    moneyline: list[tuple[float, bool]] = []
    by_tier: dict[str, list[tuple[float, bool]]] = {}
    brier_model: list[float] = []
    brier_market: list[float] = []
    spread: list[tuple[float, bool]] = []
    total: list[tuple[float, bool]] = []
    movement = {"toward": 0, "against": 0, "flat": 0, "picks": 0}
    clv: list[tuple[str, float]] = []
    nights: set[str] = set()
    for row in graded:
        g, hf, af = row["game"], row["home"], row["away"]
        nights.add(row["date"])
        p_home = _num((g.get("home") or {}).get("winProb"))
        home_won = hf > af
        if p_home is not None and hf != af:
            fav_p = max(p_home, 1 - p_home)
            fav_won = home_won if p_home >= 0.5 else not home_won
            moneyline.append((fav_p, fav_won))
            tiers = g.get("tiers") or {}
            # Filed under the HIGHER of the two tiers, as All results files a
            # bet, so a high-major favourite over a low-major side and a
            # low-major upset of one land in the same row.
            tier = tier_label(higher_tier(tiers.get("home"), tiers.get("away"))) or "Unplaced"
            by_tier.setdefault(str(tier), []).append((fav_p, fav_won))
            brier_model.append((p_home - (1.0 if home_won else 0.0)) ** 2)
            market = no_vig_home((g.get("moneyline") or {}).get("current"))
            if market is not None:
                brier_market.append((market - (1.0 if home_won else 0.0)) ** 2)
            else:
                brier_market.append(float("nan"))
        sp = g.get("spread") or {}
        cover, line = _num(sp.get("coverProb")), _num(sp.get("current"))
        if cover is not None and line is not None:
            adj = (hf - af) + line
            if adj != 0:
                home_covered = adj > 0
                fav_p = max(cover, 1 - cover)
                spread.append((fav_p, home_covered if cover >= 0.5 else not home_covered))
        tt = g.get("total") or {}
        over, tline = _num(tt.get("overProb")), _num(tt.get("current"))
        if over is not None and tline is not None and (hf + af) != tline:
            went_over = (hf + af) > tline
            fav_p = max(over, 1 - over)
            total.append((fav_p, went_over if over >= 0.5 else not went_over))
        pick = g.get("pick") or {}
        if pick.get("kind", "bet") in ("bet", "lean") and str(pick.get("market", "")).lower() == "moneyline" and pick.get("side") in ("home", "away"):
            ml = g.get("moneyline") or {}
            opened, now = implied((ml.get("open") or {}).get(pick["side"])), implied((ml.get("current") or {}).get(pick["side"]))
            if opened is not None and now is not None:
                movement["picks"] += 1
                key = "toward" if now > opened + 1e-9 else "against" if now < opened - 1e-9 else "flat"
                movement[key] += 1
        if isinstance(pick, dict) and lines_for is not None:
            closing = closing_value(pick, g, lines_for(row["date"]).get(str(g.get("id"))))
            if closing is not None:
                clv.append((str(pick.get("kind", "bet")), closing["points"]))
    paired = [(m, k) for m, k in zip(brier_model, brier_market) if math.isfinite(k)]
    return {
        "generatedAt": _now(),
        "through": max(nights) if nights else None,
        "nights": len(nights),
        "games": len(moneyline),
        "buckets": _bucket_rows(moneyline),
        "byTier": {tier: {"games": len(rows), "buckets": _bucket_rows(rows)} for tier, rows in sorted(by_tier.items())},
        "brier": {
            "games": len(paired),
            "model": round(sum(m for m, _ in paired) / len(paired), 4) if paired else None,
            "market": round(sum(k for _, k in paired) / len(paired), 4) if paired else None,
            "modelAll": round(sum(brier_model) / len(brier_model), 4) if brier_model else None,
        },
        "markets": {
            "spread": {"games": len(spread), "buckets": _market_buckets(spread)},
            "total": {"games": len(total), "buckets": _market_buckets(total)},
        },
        "movement": movement,
        "clv": clv_summary(clv),
        "notes": [
            "Each game is counted once, under the side the board favoured, so a 40% home chance is a 60% away favourite.",
            "Brier is the mean squared error of the home win chance; lower is better, 0.25 is a coin flip. The market column is the frozen board's best moneyline pair with the margin removed, on the games that carried both prices.",
            "Spread and total bands use the chance the board published for the favoured side at the board's own line; pushes are left out.",
            "Movement compares the picked side's price at the first and last reads of the board; no closing line is fetched.",
            "Closing-line value is the picked spread or total line against the last line the board recorded before tip, in points from the bettor's side; positive means the pick got the better number. Moneyline picks are left out because the line history keeps only the home price.",
        ],
    }


def clv_summary(values: list[tuple[str, float]]) -> dict:
    """Mean closing-line value and the share that beat the close, over every
    pick and over bets alone. A tie with the close does not beat it."""
    def summarise(points: list[float]) -> dict:
        if not points:
            return {"picks": 0, "meanPoints": None, "beatClosePct": None}
        return {"picks": len(points), "meanPoints": round(sum(points) / len(points), 2),
                "beatClosePct": round(100.0 * sum(1 for p in points if p > 0) / len(points), 1)}

    return {**summarise([p for _, p in values]), "bets": summarise([p for k, p in values if k == "bet"])}


def _grade(settle, pick: dict, g: dict, hf: int, af: int, teams: dict) -> str | None:
    """A pick graded by the Results page's own rule, whatever its kind."""
    try:
        return settle.grade_pick(SPORT, {**pick, "kind": "bet"}, g, hf, af, teams)
    except (TypeError, ValueError, KeyError):
        return None


def tracker_rows(graded: list[dict], settle=None, lines_for=None) -> list[dict]:
    """One row per graded pick: a bet at a flat unit, an opinion (lean or
    pass) graded for the record and staked nothing."""
    settle = settle or _module("settle_results")
    rows = []
    for row in graded:
        g, hf, af = row["game"], row["home"], row["away"]
        pick = g.get("pick")
        if not isinstance(pick, dict) or pick.get("kind", "bet") not in ("bet", "lean", "pass"):
            continue
        result = _grade(settle, pick, g, hf, af, row.get("teams") or {})
        if result not in ("win", "loss", "push"):
            continue
        kind = pick.get("kind", "bet")
        price = _int(pick.get("price"))
        bet = kind == "bet"
        stake = 1.0 if bet else 0.0
        units = None
        if bet:
            pay = payout(price)
            units = 0.0 if result == "push" or pay is None else (round(pay, 4) if result == "win" else -1.0)
        home, away = (g.get("home") or {}).get("abbr"), (g.get("away") or {}).get("abbr")
        rows.append({
            "date": row["date"], "id": str(g.get("id")), "kind": kind, "group": "team",
            "market": str(pick.get("market") or ""), "label": pick.get("label"), "price": price, "book": pick.get("book"),
            "tier": pick.get("tier"), "team": _side_abbr(pick, g), "teams": [away, home], "line": _num(pick.get("line")),
            "result": result, "staked": stake, "units": units, "final": f"{away} {af}, {home} {hf}",
            **_closing_fields(pick, g, lines_for, row["date"]),
        })
    return rows


def _closing_fields(pick: dict, g: dict, lines_for, day: str) -> dict:
    closing = closing_value(pick, g, lines_for(day).get(str(g.get("id")))) if lines_for else None
    return {"closeLine": None if closing is None else closing["close"],
            "clvPoints": None if closing is None else closing["points"]}


def _tally(rows: list[dict]) -> dict:
    out = {"w": 0, "l": 0, "p": 0, "bets": len(rows), "staked": 0.0, "units": 0.0}
    for r in rows:
        out["w" if r["result"] == "win" else "l" if r["result"] == "loss" else "p"] += 1
        out["staked"] += float(r.get("staked") or 0.0)
        out["units"] += float(r.get("units") or 0.0)
    out["staked"], out["units"] = round(out["staked"], 2), round(out["units"], 2)
    out["returnPct"] = round(100.0 * out["units"] / out["staked"], 2) if out["staked"] else None
    return out


def _grouped(rows: list[dict], key) -> list[dict]:
    groups: dict[str, list[dict]] = {}
    for r in rows:
        for k in key(r):
            if k:
                groups.setdefault(str(k), []).append(r)
    return sorted(({"key": k, **_tally(v)} for k, v in groups.items()), key=lambda d: (-d["units"], d["key"]))


def price_band(price) -> str:
    p = _int(price)
    if p is None:
        return "no price"
    if p <= -200:
        return "−200 and shorter"
    if p < -110:
        return "−199 to −111"
    if p <= 110:
        return "−110 to +110"
    if p < 200:
        return "+111 to +199"
    return "+200 and longer"


def tracker_page(rows: list[dict], nights: int) -> dict:
    bets = [r for r in rows if r["kind"] == "bet"]
    opinions = [r for r in rows if r["kind"] != "bet"]
    dates = sorted({r["date"] for r in rows})
    return {
        "generatedAt": _now(),
        "nights": nights,
        "firstDate": dates[0] if dates else None,
        "lastDate": dates[-1] if dates else None,
        "teamPickDefaultUnits": 1,
        "overall": _tally(bets),
        "byMarket": _grouped(bets, lambda r: [r["market"]]),
        "byTeam": _grouped(bets, lambda r: [r["team"]] if r["team"] else list(r["teams"])),
        "byTier": _grouped(bets, lambda r: [r["tier"] or "no tier"]),
        "byPrice": _grouped(bets, lambda r: [price_band(r["price"])]),
        "byMonth": _grouped(bets, lambda r: [r["date"][:7]]),
        "opinions": {
            "overall": _tally(opinions),
            "byMarket": _grouped(opinions, lambda r: [r["market"]]),
            "byKind": _grouped(opinions, lambda r: [r["kind"]]),
        },
        "rows": rows,
        "notes": [
            "A bet is a frozen opinion the card selected: it cleared the edge bar on an allowlisted market with a human receipt behind it. Each is counted at one flat unit at the board's price.",
            "An opinion is a frozen price the card did not select. It is graded for the record and stakes nothing.",
            "Ten or more bets to read a row; fewer swing with one week.",
        ],
    }


def _publish_clv_on_the_board(path: Path, clv: dict) -> None:
    """The board's record strip reads `record.clvPoints` and `beatClosePct`;
    `build_board_json.py` leaves them null because it holds no history. A
    board that cannot be read is left alone."""
    try:
        board = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return
    if not isinstance(board, dict) or not isinstance(board.get("record"), dict):
        return
    board["record"]["clvPoints"] = clv.get("meanPoints")
    board["record"]["beatClosePct"] = clv.get("beatClosePct")
    board["record"]["clvPicks"] = clv.get("picks", 0)
    _dump(path, board)


def write_record_pages(data: Path, today: date, fetch: bool = True) -> dict:
    hist = Path(data) / "history"
    settle = _module("settle_results")
    graded = graded_games(hist, today, settle, fetch=fetch) if hist.is_dir() else []
    lines_for = load_lines(hist)
    record = record_page(graded, today, lines_for)
    rows = tracker_rows(graded, settle, lines_for)
    tracker = tracker_page(rows, record["nights"])
    _dump(Path(data) / "record.json", record)
    _dump(Path(data) / "tracker.json", tracker)
    _publish_clv_on_the_board(Path(data) / "board.json", record["clv"])
    return {"games": len(graded), "nights": record["nights"], "bets": tracker["overall"]["bets"], "opinions": tracker["opinions"]["overall"]["bets"]}
