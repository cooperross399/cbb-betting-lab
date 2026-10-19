#!/usr/bin/env python3
"""Fetch one logo per Division I team into `web/logos/<ABBR>.png`.

    python web/fetch_logos.py              # the season ESPN is in today
    python web/fetch_logos.py --season 2027

The board draws a logo in every team circle. It reads `teams[abbr].logo` from
board.json, falls back to `./logos/<ABBR>.png`, and then to the coloured
abbreviation. This script fills that folder once; `build_board_json.py` writes
the key only for a file that exists when it runs.

**The universe is ESPN's conference walk, not `/teams?groups=50`.** That
endpoint returns 362 schools and silently omits Queens, Lindenwood and
Southern Indiana (CLAUDE.md, `population.py`). The walk asks ESPN's core API
for the conferences under Division I (group 50) for the season, then each
conference for its teams: 365 schools across 32 conferences for 2026-27,
measured 2026-10-18. A walk that fails stops the run rather than falling back
to the short list.

**The file name is ESPN's own abbreviation**, which is what the builder keys
`teams` by (it reads the ESPN scoreboard). Two schools sharing an
abbreviation would share a logo on the board, so a shared one is refused:
neither file is written and the run says so.

Source order per team, first that answers 200 with a real PNG (signature,
IHDR, every IDAT byte inflating to the size the header promises, more than
2 KB, 500 px on a side):

1. ESPN's CDN, `logos[0].href` straight off the site API's team record, or,
   when that file is not 500 px, the same image through ESPN's resizer on the
   same host. ESPN is asked with urllib's default User-Agent, which it answers.
2. Wikimedia Commons' search API, for a team ESPN has no usable logo for: the
   first SVG/PNG file result's 500-px thumbnail. Commons asks for a
   descriptive User-Agent with a contact and rate-limits (HTTP 429), so it
   gets one, a pause between calls, and a back-off that honours Retry-After.
3. Nothing. The page shows the abbreviation.

Idempotent: a file that is already a valid logo is kept and not fetched
again, and its recorded source is carried forward from the previous
`SOURCES.md`. `SOURCES.md` is rewritten each run with every team of the walk,
the file it has (or none) and the URL that file came from.

Stdlib only. Fetches no odds, spends no credit, places no bet.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

HERE = Path(__file__).resolve().parent
LOGOS = HERE / "logos"
ET = ZoneInfo("America/New_York")

SITE = "https://site.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball"
CORE = "https://sports.core.api.espn.com/v2/sports/basketball/leagues/mens-college-basketball"
DIVISION_ONE_GROUP = "50"
ESPN_CDN = "a.espncdn.com"
COMMONS = "https://commons.wikimedia.org/w/api.php"
COMMONS_USER_AGENT = (
    "maverickhightower-logo-fetch/1.0 "
    "(+https://github.com/cooperross399/cbb-betting-lab; contact via the repository's issues) python-urllib"
)

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MIN_BYTES = 2048
SIDE = 500
#: Bytes per pixel for each PNG colour type at 8 bits per sample.
_CHANNELS = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}

SOURCES_HEADER = """# Team logos

One file per Division I team, named by ESPN's abbreviation (the key the
board's `teams` map uses). Written by `web/fetch_logos.py`; do not edit by hand.

The logos are the trademarks of their leagues and clubs, shown for
identification only.

| File | Team | ESPN id | Source |
|:-----|:-----|:--------|:-------|
"""


# --------------------------------------------------------------------------
# PNG validation (stdlib: signature, IHDR, and a full inflate of the IDATs)
# --------------------------------------------------------------------------

def png_problem(data: bytes) -> str | None:
    """Why `data` is not a usable logo, or None when it is."""
    if len(data) <= MIN_BYTES:
        return f"{len(data)} bytes, not more than {MIN_BYTES}"
    if not data.startswith(PNG_SIGNATURE):
        return "not a PNG (signature)"
    pos, idat, width = len(PNG_SIGNATURE), [], None
    height = depth = colour = interlace = 0
    while pos + 8 <= len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        if len(body) != length:
            return "truncated chunk"
        if width is None:
            if kind != b"IHDR" or length != 13:
                return "first chunk is not IHDR"
            width, height, depth, colour, _c, _f, interlace = struct.unpack(">IIBBBBB", body)
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
        pos += 12 + length
    if width is None:
        return "no IHDR"
    if not idat:
        return "no image data"
    if SIDE not in (width, height):
        return f"{width}x{height}, not {SIDE} px on a side"
    try:
        raw = zlib.decompress(b"".join(idat))
    except zlib.error as exc:
        return f"image data does not inflate: {exc}"
    if colour not in _CHANNELS or depth not in (1, 2, 4, 8, 16):
        return f"unsupported colour type {colour} / depth {depth}"
    bits = _CHANNELS[colour] * depth
    if interlace:
        # Adam7: seven passes, each its own scanlines; a short stream is a
        # truncated image just as it is when not interlaced.
        expected = 0
        for x0, y0, dx, dy in ((0, 0, 8, 8), (4, 0, 8, 8), (0, 4, 4, 8), (2, 0, 4, 4), (0, 2, 2, 4), (1, 0, 2, 2), (0, 1, 1, 2)):
            w, h = (width - x0 + dx - 1) // dx, (height - y0 + dy - 1) // dy
            if w and h:
                expected += h * (1 + (w * bits + 7) // 8)
    else:
        expected = height * (1 + (width * bits + 7) // 8)
    if len(raw) < expected:
        return f"image data inflates to {len(raw)} bytes, {expected} expected"
    return None


# --------------------------------------------------------------------------
# HTTP
# --------------------------------------------------------------------------

def _get(url: str, *, user_agent: str | None = None, attempts: int = 4) -> bytes:
    """GET `url`; retry 429 and 5xx with back-off (Retry-After when given)."""
    headers = {"User-Agent": user_agent} if user_agent else {}
    delay = 2.0
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as resp:  # noqa: S310 - fixed hosts
                return resp.read()
        except urllib.error.HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
            wait = delay
            retry_after = exc.headers.get("Retry-After") if exc.headers else None
            if retry_after and retry_after.isdigit():
                wait = max(wait, float(retry_after))
            time.sleep(min(wait, 60.0))
            delay *= 2
        except urllib.error.URLError:
            if attempt == attempts - 1:
                raise
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")  # pragma: no cover


def _json(url: str, **kw) -> dict:
    return json.loads(_get(url, **kw))


# --------------------------------------------------------------------------
# The universe: ESPN's conference walk
# --------------------------------------------------------------------------

def default_season(today=None) -> int:
    """ESPN names a college basketball season by the year it ends in."""
    today = today or datetime.now(ET).date()
    return today.year + 1 if today.month >= 8 else today.year


def _ids(items: list[dict], kind: str) -> list[str]:
    found = []
    for item in items:
        match = re.search(rf"/{kind}/(\d+)", item.get("$ref", ""))
        if match:
            found.append(match.group(1))
    return found


def _paged(url: str) -> list[dict]:
    items, page = [], 1
    while True:
        payload = _json(f"{url}{'&' if '?' in url else '?'}limit=200&page={page}")
        items.extend(payload.get("items", []))
        if page >= int(payload.get("pageCount") or 1):
            return items
        page += 1


def conference_walk(season: int) -> dict[str, str]:
    """team id -> conference id, for every team ESPN places in Division I."""
    base = f"{CORE}/seasons/{season}/types/2/groups"
    conferences = _ids(_paged(f"{base}/{DIVISION_ONE_GROUP}/children"), "groups")
    if not conferences:
        raise SystemExit(f"ESPN listed no Division I conferences for season {season}; nothing was written.")
    walk: dict[str, str] = {}
    for conference in conferences:
        for team_id in _ids(_paged(f"{base}/{conference}/teams"), "teams"):
            walk[team_id] = conference
    if not walk:
        raise SystemExit(f"ESPN's conference walk for season {season} returned no teams; nothing was written.")
    return walk


def team_records(walk: dict[str, str]) -> dict[str, dict]:
    """id -> {abbr, name, logo} from the site API, which carries the logo hrefs.

    The bulk `groups=50` listing answers for 362 of them in one call; every
    walk id it omits is asked for on its own.
    """
    bulk = _json(f"{SITE}/teams?limit=400&groups={DIVISION_ONE_GROUP}")
    by_id: dict[str, dict] = {}
    for league in (bulk.get("sports") or [{}])[0].get("leagues", []):
        for entry in league.get("teams", []):
            team = entry.get("team") or {}
            by_id[str(team.get("id"))] = team
    records = {}
    for team_id in walk:
        team = by_id.get(team_id)
        if team is None:
            team = _json(f"{SITE}/teams/{team_id}").get("team") or {}
        logos = team.get("logos") or []
        records[team_id] = {
            "abbr": (team.get("abbreviation") or "").strip(),
            "name": team.get("displayName") or team.get("name") or team_id,
            "logo": (logos[0].get("href") if logos else None),
        }
    return records


# --------------------------------------------------------------------------
# Sources
# --------------------------------------------------------------------------

def from_espn(record: dict) -> tuple[bytes, str] | None:
    """`logos[0].href`, or the same image through ESPN's own resizer.

    A few `/500/` hrefs serve the 4096-px master (Alcorn State and Davidson,
    measured 2026-10-18). ESPN's combiner on the same host returns that
    image at 500 px, so the second try is still ESPN's file, just scaled.
    """
    href = record.get("logo")
    if not href:
        return None
    candidates = [href]
    parsed = urllib.parse.urlsplit(href)
    if parsed.netloc == ESPN_CDN and parsed.path.lower().endswith(".png"):
        candidates.append(f"https://{ESPN_CDN}/combiner/i?img={urllib.parse.quote(parsed.path)}&w={SIDE}&h={SIDE}")
    for url in candidates:
        try:
            data = _get(url)
        except (urllib.error.URLError, OSError):
            continue
        if png_problem(data) is None:
            return data, url
    return None


def from_commons(record: dict) -> tuple[bytes, str] | None:
    query = urllib.parse.urlencode({
        "action": "query", "generator": "search", "gsrsearch": f"{record['name']} logo",
        "gsrnamespace": "6", "prop": "imageinfo", "iiprop": "url", "iiurlwidth": str(SIDE),
        "format": "json",
    })
    try:
        payload = _json(f"{COMMONS}?{query}", user_agent=COMMONS_USER_AGENT)
    except (urllib.error.URLError, OSError, ValueError):
        return None
    pages = sorted((payload.get("query") or {}).get("pages", {}).values(), key=lambda p: p.get("index", 0))
    for page in pages:
        if not page.get("title", "").lower().endswith((".svg", ".png")):
            continue
        info = (page.get("imageinfo") or [{}])[0]
        thumb = info.get("thumburl")
        if not thumb:
            continue
        time.sleep(1.0)
        try:
            data = _get(thumb, user_agent=COMMONS_USER_AGENT)
        except (urllib.error.URLError, OSError):
            return None
        return (data, thumb) if png_problem(data) is None else None
    return None


# --------------------------------------------------------------------------
# SOURCES.md
# --------------------------------------------------------------------------

ROW = re.compile(r"^\|\s*(?P<file>[^|]+?)\s*\|\s*(?P<team>[^|]+?)\s*\|\s*(?P<id>[^|]+?)\s*\|\s*(?P<source>[^|]+?)\s*\|\s*$")


def read_sources(path: Path) -> dict[str, str]:
    """file name -> source, from a previous SOURCES.md (empty when none)."""
    if not path.is_file():
        return {}
    found = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match and match["file"].endswith(".png"):
            found[match["file"].strip("`")] = match["source"]
    return found


def _cell(text: str) -> str:
    return text.replace("|", "/")


def write_sources(path: Path, rows: list[tuple[str, str, str, str]]) -> None:
    body = SOURCES_HEADER + "".join(
        f"| {_cell(f)} | {_cell(team)} | {_cell(team_id)} | {_cell(source)} |\n"
        for f, team, team_id, source in rows
    )
    _write(path, body.encode("utf-8"))


def _write(path: Path, data: bytes) -> None:
    tmp = path.with_name(path.name + ".part")
    tmp.write_bytes(data)
    os.replace(tmp, path)


# --------------------------------------------------------------------------

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--season", type=int, default=0, help="ESPN season year (the year it ends in). Default: today's.")
    ap.add_argument("--logos", default=str(LOGOS), help="Folder to fill (default: web/logos beside this script).")
    args = ap.parse_args(argv)
    season = args.season or default_season()
    logos = Path(args.logos)
    logos.mkdir(parents=True, exist_ok=True)
    sources_path = logos / "SOURCES.md"
    previous = read_sources(sources_path)

    walk = conference_walk(season)
    records = team_records(walk)
    print(f"Season {season}: {len(walk)} Division I teams in {len(set(walk.values()))} conferences (ESPN conference walk).")

    by_abbr: dict[str, list[str]] = {}
    for team_id, record in records.items():
        by_abbr.setdefault(record["abbr"], []).append(team_id)
    shared = {abbr: ids for abbr, ids in by_abbr.items() if len(ids) > 1 or not abbr}
    for abbr, ids in sorted(shared.items()):
        names = ", ".join(records[i]["name"] for i in ids)
        print(f"REFUSED: abbreviation {abbr or '(blank)'!r} is shared by {names}; no file written for it.")

    rows, tally = [], {"kept": 0, "espn": 0, "commons": 0, "none": 0, "refused": 0}
    for team_id, record in sorted(records.items(), key=lambda kv: (kv[1]["abbr"], kv[0])):
        abbr, name = record["abbr"], record["name"]
        if abbr in shared:
            tally["refused"] += 1
            rows.append(("—", name, team_id, "none: abbreviation shared with another school"))
            continue
        if "/" in abbr or abbr in (".", ".."):
            tally["refused"] += 1
            rows.append(("—", name, team_id, f"none: abbreviation {abbr!r} is not a file name"))
            continue
        filename = f"{abbr}.png"
        target = logos / filename
        if target.is_file() and png_problem(target.read_bytes()) is None:
            tally["kept"] += 1
            rows.append((filename, name, team_id, previous.get(filename, "existing file (source not recorded)")))
            continue
        got = from_espn(record)
        kind = "espn"
        if got is None:
            time.sleep(1.0)
            got, kind = from_commons(record), "commons"
        if got is None:
            tally["none"] += 1
            rows.append(("—", name, team_id, "none: no source answered; the page shows the abbreviation"))
            print(f"no logo: {abbr} {name}")
            continue
        data, url = got
        _write(target, data)
        tally[kind] += 1
        rows.append((filename, name, team_id, url))

    rows.sort(key=lambda r: (r[0] == "—", r[0], r[1]))
    write_sources(sources_path, rows)
    print(
        f"{len(records)} teams: {tally['kept']} kept, {tally['espn']} from ESPN, "
        f"{tally['commons']} from Wikimedia Commons, {tally['none']} with no logo, "
        f"{tally['refused']} refused. Sources in {sources_path}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
