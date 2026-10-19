#!/usr/bin/env python3
"""Settle yesterday's frozen board into results.json. Sport-agnostic on the outside;
the finals come from ESPN's public scoreboard for the sport named in site.json.

    python web/settle_results.py --data dist/data --sport epl|cbb [--date YYYY-MM-DD]

Reads history/<date>.json (the board as published), fetches finals, grades each
game's projection and pick, writes results.json. The frozen board is never edited.
The NHL lab settles inside build_site_json.py and does not use this file.

It also sums the season (`season_record`), in the NHL lab's shape: every day a
board was frozen for, each settled once and kept under history/settled/<date>.json,
which rides in the same board-history artifact as the frozen boards. The season
is written into results.json as `seasonRecord` and onto the live board.json's
`record` (picks, straightUp, totals, leans, season) only once a day has settled:
a tally nobody has made is absent, never 0-0. Best bets are `picks`; leans are
graded the same way and kept in `leans`. A day that could not be settled is in
`season.missingNights`.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

#: NO custom User-Agent, deliberately, and this is the opposite of the rule the
#: NHL lab pins for api-web.nhle.com. That host refuses urllib's default and
#: accepts any string; site.api.espn.com is in front of a WAF that does the
#: reverse -- it answers `Python-urllib/3.x` with 200 and returns 403 Access
#: Denied for a descriptive agent AND for a Chrome string alike. Measured
#: 2026-09-23, three trials, both sports, stable.
#:
#: So a polite, identifying agent is exactly what breaks this, which is the
#: wrong way round from every other fetch in these repositories and is why it
#: is written down rather than left to whoever reads the next 403.
#: `test_the_settlement_fetch_sends_no_custom_user_agent` holds it.
ESPN = {
    "epl": "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard?dates={d}&limit=100",
    "cbb": "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/scoreboard?dates={d}&groups=50&limit=400",
}


def fetch(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=30) as r:  # noqa: S310
        return json.load(r)


def finals(sport: str, day: date) -> dict:
    out = {}
    for ev in fetch(ESPN[sport].format(d=f"{day:%Y%m%d}")).get("events", []):
        comp = (ev.get("competitions") or [{}])[0]
        st = ((ev.get("status") or {}).get("type") or {})
        if not st.get("completed"):
            continue
        sides = {c.get("homeAway"): c for c in comp.get("competitors", [])}
        try:
            out[str(ev["id"])] = {"home": int(sides["home"]["score"]), "away": int(sides["away"]["score"]),
                                  "finish": "OT" if (st.get("detail") or "").upper().find("OT") >= 0 else "REG"}
        except (KeyError, ValueError, TypeError):
            continue
    return out


def side_named(label: str, g: dict, teams: dict) -> str | None:
    """Which side a selection label names, or None if it cannot be told.

    The two halves speak different vocabularies. `selection_label` writes the
    team NAME it was handed -- "Newcastle draw no bet", "Notre Dame -4",
    "Kansas ML" -- while the board carries abbreviations: BRE, ND, KU. As
    shipped this compared the one to the other, `label.startswith(abbr)`,
    which is False for every real label, so CBB graded every side pick as the
    away side and EPL leaned on a second arm, `g.get("_homeName", "") in
    label`. Nothing anywhere writes `_homeName`, so that arm read
    `"" in label` -- true of every string -- and every EPL draw-no-bet graded
    as a home pick whichever side was taken. Both failures are silent and land
    in the published record.

    Longest match wins, so a name that is a prefix of the other side's cannot
    claim it. Returning None leaves the pick ungraded: a settled record with a
    hole in it can be repaired, and one confidently settled for the opponent
    cannot.
    """
    best, found = 0, None
    for role in ("home", "away"):
        abbr = ((g.get(role) or {}).get("abbr") or "")
        entry = teams.get(abbr) or {}
        for cand in (entry.get("name"), entry.get("short"), abbr):
            if not cand:
                continue
            c = str(cand).lower()
            if label.startswith(c) and len(c) > best:
                best, found = len(c), role
    return found


def grade_pick(sport, pick, g, hf, af, teams=None):
    if not pick or pick.get("kind", "bet") not in ("bet", "lean"):
        return None
    m, label = (pick.get("market") or "").lower(), (pick.get("label") or "").lower()
    tot = hf + af
    teams = teams or {}
    if sport == "epl":
        if m.startswith("total"):
            return "win" if ("over" in label) == (tot > 2.5) else "loss"
        if m == "btts":
            yes = hf > 0 and af > 0
            return "win" if ("both teams score" in label) == yes else "loss"
        if m == "draw_no_bet":
            if hf == af:
                return "void"
            side = side_named(label, g, teams)
            if side is None:
                return None
            return "win" if (side == "home") == (hf > af) else "loss"
        return None  # corners / double chance need feeds the site does not have; left ungraded
    if sport == "cbb":
        margin = hf - af
        if m == "moneyline":
            side = side_named(label, g, teams)
            if side is None:
                return None
            return "win" if (side == "home") == (margin > 0) else "loss"
        if m == "spread":
            side = side_named(label, g, teams)
            if side is None:
                return None
            home = side == "home"
            line = float(pick.get("line") or (g.get("spread") or {}).get("current") or 0)
            adj = margin + line if home else -margin - line
            return "win" if adj > 0 else "loss" if adj < 0 else "push"
        if m == "total":
            line = float(pick.get("line") or (g.get("total") or {}).get("current") or 0)
            return "push" if tot == line else "win" if ("over" in label) == (tot > line) else "loss"
    return None


#: What a scoreboard that could not be read raises. Yesterday's settlement is
#: not today's board, so none of these may take the publish down.
FETCH_ERRORS = (urllib.error.URLError, json.JSONDecodeError, TimeoutError)

#: A frozen board's name: `<date>.json` or `<date>_<slot>.json`, as
#: build_board_json.py and site_history.py freeze them.
FROZEN_BOARD = re.compile(r"^(\d{4}-\d{2}-\d{2})(?:_(\w+))?\.json$")


def frozen_board(hist: Path, day: date) -> Path | None:
    """The board settled for `day`: the first frozen file for that date, as ever."""
    frozen = sorted(p for p in hist.glob(f"{day.isoformat()}*.json") if FROZEN_BOARD.match(p.name))
    return frozen[0] if frozen else None


def settle_day(sport: str, day: date, board: dict) -> tuple[dict, bool]:
    """One day's results.json body, and whether a game on it still has no final.

    Raises one of FETCH_ERRORS when the day's scoreboard cannot be fetched;
    the caller decides what that means for the page and for the season.

    The pick tallies are the board's: `picks` counts best bets (a pick with no
    `kind` reads as one, as the page reads it) and `leans` counts leans,
    graded the same way and never added to `picks`. A frozen opinion (`kind`
    "pass") is graded into neither.
    """
    fin = finals(sport, day)
    games = []
    picks, leans = {"w": 0, "l": 0, "p": 0}, {"w": 0, "l": 0, "p": 0}
    su, ats, tots = {"w": 0, "l": 0}, {"w": 0, "l": 0, "p": 0}, {"w": 0, "l": 0, "p": 0}
    shown = [g for g in board.get("games", []) if isinstance(g, dict)]
    for g in shown:
        f = fin.get(str(g.get("id")))
        if not f:
            continue
        hf, af = f["home"], f["away"]
        pick = g.get("pick")
        res = grade_pick(sport, pick, g, hf, af, board.get("teams") or {})
        if res in ("win", "loss", "push"):
            tally = leans if pick.get("kind", "bet") == "lean" else picks
            tally[{"win": "w", "loss": "l", "push": "p"}[res]] += 1
        row = {"id": g["id"], "home": {"abbr": g["home"]["abbr"], "final": hf}, "away": {"abbr": g["away"]["abbr"], "final": af}, "finish": f["finish"],
               "pick": {**pick, "result": res} if pick and res else None}
        if sport == "epl":
            row["home"]["projGoals"], row["away"]["projGoals"] = g["home"].get("projGoals"), g["away"].get("projGoals")
            hp, dp, ap_ = g["home"].get("winProb"), g.get("drawProb"), g["away"].get("winProb")
            row["projResult"] = max((("home", hp or 0), ("draw", dp or 0), ("away", ap_ or 0)), key=lambda x: x[1])[0]
            out = "home" if hf > af else "away" if hf < af else "draw"
            su["w" if out == row["projResult"] else "l"] += 1
            over_p = (g.get("total") or {}).get("overProb")
            if isinstance(over_p, (int, float)):
                tots["w" if (over_p > 0.5) == (hf + af > 2.5) else "l"] += 1
            row["markets"] = {"total": {"line": 2.5, "overProb": over_p}, "btts": {"yesProb": (g.get("btts") or {}).get("yesProb")}}
        else:
            row["home"]["projPts"], row["away"]["projPts"] = g["home"].get("projPts"), g["away"].get("projPts")
            hp = g["home"].get("winProb")
            row["projWinner"] = g["home"]["abbr"] if (hp or 0.5) >= 0.5 else g["away"]["abbr"]
            winner = g["home"]["abbr"] if hf > af else g["away"]["abbr"]
            if isinstance(hp, (int, float)):
                su["w" if winner == row["projWinner"] else "l"] += 1
            sp, tt = g.get("spread") or {}, g.get("total") or {}
            row["markets"] = {"spread": {"line": sp.get("current"), "proj": sp.get("proj")}, "total": {"line": tt.get("current"), "proj": tt.get("proj")}}
            if isinstance(sp.get("proj"), (int, float)) and isinstance(sp.get("current"), (int, float)):
                model_home = sp["proj"] < sp["current"]
                adj = (hf - af) + sp["current"]
                ats["p" if adj == 0 else "w" if (adj > 0) == model_home else "l"] += 1
            if isinstance(tt.get("proj"), (int, float)) and isinstance(tt.get("current"), (int, float)):
                t = hf + af
                tots["p" if t == tt["current"] else "w" if (tt["proj"] > tt["current"]) == (t > tt["current"]) else "l"] += 1
        games.append(row)
    summary = {"picks": picks, "leans": leans}
    if sport == "epl":
        summary.update(result=su, totals={"w": tots["w"], "l": tots["l"]})
    else:
        summary.update(straightUp=su, ats=ats, totals=tots)
    body = {"season": board.get("season", ""), "windowLabel": board.get("windowLabel"),
            "notice": None if games else "The games were played but no final was available when this ran; the next build settles them.",
            "summary": summary, "teams": board.get("teams", {}), "games": games}
    return body, len(games) < len(shown)


# ---------- the season ----------

#: Where each settled day is kept, inside the history the publish workflow
#: restores and uploads (dist/data/history, the `board-history` artifact), so
#: the season reads an old day once instead of re-fetching its finals daily.
SETTLED_DIR = "settled"

#: The four season tallies, in the NHL lab's shape (web/SCHEMA.md there).
SEASON_KEYS = ("straightUp", "picks", "leans", "totals")

#: How long a day with a game still lacking a final is settled again each run
#: rather than kept: the NHL lab's patience, so a postponed game cannot hold a
#: day out of the cache forever.
PATIENCE_DAYS = 14


def night_record(results: dict) -> dict:
    """What the season keeps of one settled day: its settled games and summary."""
    return {"games": len(results.get("games") or []), "summary": results.get("summary") or {}}


def _kept_night(path: Path) -> dict | None:
    """A day read from history/settled, or None when none is kept or it cannot be read."""
    if not path.is_file():
        return None
    try:
        night = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    if not isinstance(night, dict) or not isinstance(night.get("summary"), dict):
        return None
    return night


def board_days(hist: Path, through: date) -> list[date]:
    """Every date a board was frozen for, up to and including `through`."""
    days: set[date] = set()
    for path in hist.glob("*.json"):
        m = FROZEN_BOARD.match(path.name)
        if not m:
            continue
        try:
            d = date.fromisoformat(m[1])
        except ValueError:
            continue
        if d <= through:
            days.add(d)
    return sorted(days)


def season_record(sport: str, day: date, hist: Path, latest: dict | None, latest_waiting: bool) -> dict:
    """The season so far: every frozen board up to `day`, settled and summed.

    `day` is the day this run settled and `latest` its results (None when its
    scoreboard could not be read). Every earlier day is read from
    `history/settled/<day>.json` when one is kept, and otherwise settled now
    and kept once no game on it still waits for a final (or once it is
    PATIENCE_DAYS old). A day that cannot be settled -- its scoreboard did not
    answer, or none of its games has a final yet -- is left out and counted in
    `missingNights`, never as 0-0, and the next run tries it again.

    Before any day has settled the four tallies are left out altogether and
    only the span `{nights: 0, firstDate: None, lastDate: None,
    missingNights}` is returned: a tally nobody has made is absent, never 0-0.
    """
    tally = {key: {"w": 0, "l": 0} if key == "straightUp" else {"w": 0, "l": 0, "p": 0} for key in SEASON_KEYS}
    kept = hist / SETTLED_DIR
    nights, missing, first, last = 0, 0, None, None
    for d in board_days(hist, day):
        waiting = False
        if d == day:
            if latest is None:
                missing += 1
                continue
            night, waiting = night_record(latest), latest_waiting
        else:
            cached = kept / f"{d.isoformat()}.json"
            night = _kept_night(cached)
            if night is None:
                path = frozen_board(hist, d)
                try:
                    board = json.loads(path.read_text(encoding="utf-8")) if path else {}
                    settled, waiting = settle_day(sport, d, board if isinstance(board, dict) else {})
                except (*FETCH_ERRORS, OSError, UnicodeError, ValueError, KeyError, TypeError, AttributeError):
                    missing += 1
                    continue
                night = night_record(settled)
                patient = d > day - timedelta(days=PATIENCE_DAYS)
                if not (waiting and patient):
                    kept.mkdir(parents=True, exist_ok=True)
                    cached.write_text(json.dumps({"resultsDate": d.isoformat(), **night}, indent=1), encoding="utf-8")
                waiting = waiting and patient
        if not night["games"]:
            # Games were on the board and none has a final yet: not settled,
            # and said so, rather than a day that happened to go 0-0. A board
            # with no games on it is no night at all.
            if waiting:
                missing += 1
            continue
        nights += 1
        first = first or d.isoformat()
        last = d.isoformat()
        for key in SEASON_KEYS:
            for k, v in (night["summary"].get(key) or {}).items():
                if k in tally[key]:
                    tally[key][k] += int(v)
    span = {"nights": nights, "firstDate": first, "lastDate": last, "missingNights": missing}
    return {**tally, **span} if nights else span


def write_season(data: Path, results: dict, season: dict) -> None:
    """The season into results.json (`seasonRecord`) and onto board.json's `record`.

    Nothing is written before a day has settled: no `seasonRecord`, and the
    board's record keeps only the keys it already carried (`markets`,
    `opinionsSoFar`, ...), so the page shows a dash and "Not tallied yet",
    never 0-0. Every key the board published before is kept.
    """
    if not season.get("nights"):
        return
    results["seasonRecord"] = dict(season)
    board_path = data / "board.json"
    try:
        board = json.loads(board_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return
    if not isinstance(board, dict):
        return
    record = board.get("record") if isinstance(board.get("record"), dict) else {}
    record.update({k: season[k] for k in SEASON_KEYS})
    record["season"] = dict(season)
    board["record"] = record
    board_path.write_text(json.dumps(board, indent=1, ensure_ascii=False, allow_nan=False), encoding="utf-8")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default="dist/data")
    ap.add_argument("--sport", required=True, choices=list(ESPN))
    ap.add_argument("--date", default="")
    args = ap.parse_args(argv)
    data = Path(args.data)
    day = date.fromisoformat(args.date) if args.date else (datetime.now(timezone.utc) - timedelta(days=1)).date()
    hist = data / "history"
    frozen = frozen_board(hist, day)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    base = {"generatedAt": now, "resultsDate": day.isoformat(), "teams": {}, "games": []}
    latest: dict | None = None
    waiting = False
    if not frozen:
        base.update(season="", notice=f"No board was published for {day.isoformat()}, so there is nothing to settle.", summary={})
        results = base
        print("nothing to settle")
    else:
        board = json.loads(frozen.read_text(encoding="utf-8"))
        try:
            latest, waiting = settle_day(args.sport, day, board)
        except FETCH_ERRORS as exc:
            # Yesterday's settlement is not today's board. This step runs after the
            # board is built, and an unhandled raise here took the whole publish
            # down with it -- the 403 above did exactly that on 2026-09-23, so the
            # site served nothing rather than serving a board with one section
            # unavailable.
            #
            # The failure is written into results.json instead of swallowed,
            # because a settlement that quietly stops is indistinguishable from a
            # day with no games, and this page's whole claim is that the record is
            # settled from what was published. The season counts the day in
            # `missingNights` and the next build tries it again.
            base.update(
                season=board.get("season", ""),
                notice=f"Yesterday's results could not be settled: the scoreboard feed answered {type(exc).__name__} ({exc}). The board above is unaffected; settlement is retried on the next build.",
                summary={},
            )
            results = base
            print(f"settlement skipped: {type(exc).__name__}: {exc}")
        else:
            results = {**base, **latest}
            print(f"settled {len(results['games'])} of {len(board.get('games', []))} games for {day}. No bet was placed.")
    try:
        season_so_far = season_record(args.sport, day, hist, latest, waiting)
    except Exception as exc:  # noqa: BLE001 - the season line must never take the day's results or the deploy down
        print(f"the season record could not be summed: {type(exc).__name__}: {exc}")
    else:
        write_season(data, results, season_so_far)
    (data / "results.json").write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
