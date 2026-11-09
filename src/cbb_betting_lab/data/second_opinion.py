"""A published ratings table, fetched free and kept as the card's second opinion.

The card's own ratings are fitted from box scores on this lab's rules. A
second, independently built table of adjusted offence, defence and tempo is
blended in at `card_factors.BLEND_WEIGHT`, the way the hockey lab blends a
published pre-game win probability into its moneyline. It is a reference,
never a credit: the page never names it, and `docs/cbb_data_sources.md` is
where the source is written down.

**Two shapes, parsed by name where a header exists and by value where it does
not.** The season file carries a header row; the ranking export does not. In
either, offence and defence are the first two numeric columns whose values sit
where points per 100 possessions sit, offence before defence — the order both
exports use — and tempo is the numeric column whose values sit where
possessions per game sit. A table in which those columns cannot be told apart
is refused rather than guessed.

**Resolved to this lab's team ids through the provider index**, with the
spellings the table uses mapped onto the index's own aliases; a name the index
cannot place is left with no id and listed, never guessed. Fewer than
`card_factors.SECOND_OPINION_MIN_TEAMS` resolved teams is a table the card
will not read, and the fetcher says so with exit 2.

The container this lab is developed in cannot reach the source (its egress is
allow-listed); GitHub's runners can. So the parser is exercised on fixtures
and the fetch is verified from an Actions log.
"""

from __future__ import annotations

import csv
import io
import json
import re
import urllib.error
import urllib.parse
import urllib.request
import urllib.robotparser
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from cbb_betting_lab.models import card_factors
from cbb_betting_lab.providers import team_names

#: Named here and in `docs/cbb_data_sources.md` only.
SOURCE = "barttorvik"
URLS: tuple[str, ...] = (
    "https://barttorvik.com/{season}_team_results.csv",
    "https://barttorvik.com/trank.php?year={season}&csv=1",
)
USER_AGENT = "Mozilla/5.0 (research; cbb-betting-lab)"

#: Header spellings that name each column, after lower-casing and stripping
#: everything but letters.
HEADER_NAMES = {
    "team": ("team", "teamname"),
    "adj_off": ("adjoe", "adjo", "adjoff", "adjustedoffense"),
    "adj_def": ("adjde", "adjd", "adjdef", "adjusteddefense"),
    "adj_tempo": ("adjt", "adjtempo", "tempo", "adjustedtempo"),
}
EFFICIENCY_RANGE = (80.0, 135.0)
TEMPO_RANGE = (55.0, 82.0)


#: The fallback when the primary table refuses this runner (it answered HTTP
#: 403 to every Actions request on 2026-11-01): ESPN's Basketball Power Index,
#: free and keyless, keyed by ESPN team id -- the same id this lab uses -- so it
#: needs no name resolution at all. It publishes offence and defence as points
#: per 70 possessions against an average team, defence positive when GOOD, and
#: no tempo, so a BPI table blends offence and defence and leaves tempo alone.
BPI_SOURCE = "espn_bpi"
BPI_URL = (
    "https://site.api.espn.com/apis/fitt/v3/sports/basketball/"
    "mens-college-basketball/powerindex?limit=500"
)
BPI_POSSESSIONS = 70.0


class SecondOpinionError(RuntimeError):
    """The table could not be fetched or could not be read as one."""


def fetch(season: int, *, timeout: float = 60.0) -> tuple[bytes, str]:
    """The first URL that answers, and which one it was."""
    errors: list[str] = []
    for template in URLS:
        url = template.format(season=int(season))
        request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = response.read()
        except urllib.error.HTTPError as exc:
            errors.append(f"{url}: HTTP {exc.code}")
            continue
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            errors.append(f"{url}: {type(exc).__name__}")
            continue
        if payload.strip():
            return payload, url
        errors.append(f"{url}: empty answer")
    raise SecondOpinionError("; ".join(errors))


def _key(text: object) -> str:
    return re.sub(r"[^a-z]", "", str(text or "").lower())


def _numeric(values: list[str]) -> list[float | None]:
    out: list[float | None] = []
    for value in values:
        try:
            out.append(float(str(value).strip()))
        except (TypeError, ValueError):
            out.append(None)
    return out


def _share_numeric(values: list[str]) -> float:
    numbers = _numeric(values)
    return sum(1 for n in numbers if n is not None) / max(1, len(numbers))


def _mean_in(values: list[str], low: float, high: float) -> bool:
    numbers = [n for n in _numeric(values) if n is not None]
    if len(numbers) < max(10, len(values) // 2):
        return False
    mean = sum(numbers) / len(numbers)
    return low <= mean <= high and all(low - 15 <= n <= high + 15 for n in numbers)


def parse(payload: bytes) -> pd.DataFrame:
    """`team, adj_off, adj_def, adj_tempo` from either export shape."""
    text = payload.decode("utf-8", errors="replace")
    rows = [r for r in csv.reader(io.StringIO(text)) if any(cell.strip() for cell in r)]
    if len(rows) < 2:
        raise SecondOpinionError("the table holds fewer than two rows")
    width = max(len(r) for r in rows)
    rows = [r + [""] * (width - len(r)) for r in rows]
    header = rows[0]
    keys = [_key(h) for h in header]
    positions: dict[str, int] = {}
    for column, names in HEADER_NAMES.items():
        for index, key in enumerate(keys):
            if key in names and column not in positions:
                positions[column] = index
    if len(positions) == 4:
        body = rows[1:]
    else:
        # Headerless: the first row is data. Tell the columns apart by value.
        body = rows
        columns = list(zip(*body))
        numeric_share = [_share_numeric(list(c)) for c in columns]
        team_candidates = [i for i, share in enumerate(numeric_share) if share < 0.2]
        if not team_candidates:
            raise SecondOpinionError("no column reads as team names")
        # The team column is the first mostly-textual column whose values are
        # distinct — a conference column repeats.
        team_index = None
        for index in team_candidates:
            values = [v.strip() for v in columns[index]]
            if len(set(values)) >= 0.9 * len(values):
                team_index = index
                break
        if team_index is None:
            raise SecondOpinionError("no textual column holds one distinct name per row")
        efficiency = [
            i for i, c in enumerate(columns)
            if numeric_share[i] > 0.9 and _mean_in(list(c), *EFFICIENCY_RANGE)
        ]
        tempo = [
            i for i, c in enumerate(columns)
            if numeric_share[i] > 0.9 and _mean_in(list(c), *TEMPO_RANGE)
        ]
        if len(efficiency) < 2 or not tempo:
            raise SecondOpinionError(
                f"could not tell the columns apart: {len(efficiency)} read as "
                f"efficiency and {len(tempo)} as tempo"
            )
        positions = {
            "team": team_index,
            "adj_off": efficiency[0],
            "adj_def": efficiency[1],
            "adj_tempo": tempo[0],
        }
    out = []
    for row in body:
        team = str(row[positions["team"]]).strip()
        if not team:
            continue
        numbers = _numeric([row[positions[c]] for c in ("adj_off", "adj_def", "adj_tempo")])
        if any(n is None for n in numbers):
            continue
        off, de, tempo_value = numbers
        if not (EFFICIENCY_RANGE[0] - 15 <= off <= EFFICIENCY_RANGE[1] + 15):
            continue
        if not (EFFICIENCY_RANGE[0] - 15 <= de <= EFFICIENCY_RANGE[1] + 15):
            continue
        if not (TEMPO_RANGE[0] - 10 <= tempo_value <= TEMPO_RANGE[1] + 10):
            continue
        out.append({"team": team, "adj_off": off, "adj_def": de, "adj_tempo": tempo_value})
    frame = pd.DataFrame(out, columns=["team", "adj_off", "adj_def", "adj_tempo"])
    if frame.empty:
        raise SecondOpinionError("no row carried a team with three readable numbers")
    if frame["adj_off"].mean() < frame["adj_def"].mean() - 5 or frame["adj_off"].mean() > frame["adj_def"].mean() + 5:
        # Offence and defence are both points per 100 and average the same
        # across a league; a gap means a column was mistaken for one of them.
        raise SecondOpinionError(
            "offence and defence do not average alike "
            f"({frame['adj_off'].mean():.1f} vs {frame['adj_def'].mean():.1f}); refusing to guess"
        )
    return frame


#: Spellings the table uses that the provider index does not carry as such.
#: Each is tried after the raw spelling.
def spellings(name: str) -> list[str]:
    raw = str(name or "").strip()
    out = [raw]
    if raw.endswith(" St."):
        out.append(raw[:-4] + " State")
    if " St. " in raw:
        out.append(raw.replace(" St. ", " State "))
    if raw.startswith("St. "):
        out.append("Saint " + raw[4:])
    out.append(raw.replace("N.C.", "NC").replace("Fla.", "Florida").replace("Mich.", "Michigan"))
    out.append(re.sub(r"\bSt\.\s*$", "State", raw))
    seen: list[str] = []
    for spelling in out:
        if spelling and spelling not in seen:
            seen.append(spelling)
    return seen


def resolve(frame: pd.DataFrame, schedule: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """The table with this lab's team ids, and the names that did not resolve."""
    index = team_names.build_index(schedule)
    ids = []
    unresolved: list[str] = []
    for name in frame["team"]:
        team = None
        for spelling in spellings(name):
            team = index.resolve(spelling)
            if team is not None:
                break
        if team is None:
            unresolved.append(str(name))
            ids.append(None)
        else:
            ids.append(int(team))
    out = frame.copy()
    out["team_id"] = pd.array(ids, dtype="Int64")
    # One id claimed by two spellings is two rows for one team; keep neither
    # rather than pick.
    counts = out["team_id"].value_counts()
    doubled = set(counts[counts > 1].index)
    if doubled:
        out.loc[out["team_id"].isin(doubled), "team_id"] = pd.NA
    return out, unresolved


def write(
    frame: pd.DataFrame,
    *,
    raw_dir: Path | str | None,
    season: int,
    as_of: date | str,
    source: str = SOURCE,
    unresolved: list[str] | None = None,
    primary: bool = True,
) -> Path:
    """`data/raw/cbb/second_opinion/<season>.csv` in the columns the card reads."""
    path = card_factors.second_opinion_path(raw_dir, season, source=None if primary else source)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    out.insert(0, "source", source)
    out.insert(0, "season", int(season))
    out.insert(0, "as_of", str(as_of)[:10])
    out = out[list(card_factors.SECOND_OPINION_COLUMNS)]
    out.to_csv(path, index=False)
    sidecar = path.with_suffix(".unresolved.json")
    sidecar.write_text(
        json.dumps(
            {"as_of": str(as_of)[:10], "season": int(season), "unresolved": sorted(unresolved or [])},
            indent=1,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def fetch_bpi(*, timeout: float = 60.0) -> bytes:
    request = urllib.request.Request(BPI_URL, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise SecondOpinionError(f"{BPI_URL}: HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise SecondOpinionError(f"{BPI_URL}: {type(exc).__name__}") from exc


def parse_bpi(payload: bytes, *, season: int | None = None) -> pd.DataFrame:
    """`team, team_id, adj_off, adj_def, adj_tempo` from ESPN's power index.

    Offence and defence are put on this lab's scale -- per 100 possessions,
    defence positive when BAD, as points allowed are -- around a nominal 100;
    the card reads deviations from the table's own mean, so the level is
    irrelevant and only the scale and the sign matter. Tempo is empty: BPI
    publishes none, and the card leaves tempo to the lab's own rating.
    """
    try:
        data = json.loads(payload)
    except ValueError as exc:
        raise SecondOpinionError(f"the power index is not JSON: {exc}") from exc
    year = (data.get("requestedSeason") or data.get("currentSeason") or {}).get("year")
    if season is not None and year is not None and int(year) != int(season):
        raise SecondOpinionError(f"the power index is for {year}, not {season}")
    scale = 100.0 / BPI_POSSESSIONS
    out = []
    for entry in data.get("teams", []):
        team = entry.get("team") or {}
        values = {}
        for category in entry.get("categories", []):
            if category.get("name") != "bpi":
                continue
            names = next((c.get("names") for c in data.get("categories", [])
                          if c.get("name") == "bpi"), None) or []
            values = dict(zip(names, category.get("values", [])))
        off, de = values.get("bpioffense"), values.get("bpidefense")
        try:
            off, de = float(off), float(de)
            team_id = int(team.get("id"))
        except (TypeError, ValueError):
            continue
        out.append({
            "team": team.get("displayName") or team.get("shortDisplayName") or str(team_id),
            "team_id": team_id,
            "adj_off": 100.0 + off * scale,
            "adj_def": 100.0 - de * scale,
            "adj_tempo": float("nan"),
        })
    frame = pd.DataFrame(out, columns=["team", "team_id", "adj_off", "adj_def", "adj_tempo"])
    if frame.empty:
        raise SecondOpinionError("the power index carried no team with offence and defence")
    frame["team_id"] = frame["team_id"].astype("Int64")
    return frame


# --------------------------------------------------------------------------
# More published tables: a consensus, not one opinion (decision 92)
# --------------------------------------------------------------------------
#
# Cooper, 2026-11-09: KenPom, the NCAA's NET and T-Rank "should all have a huge
# influence". Each source below writes its own `<season>.<source>.csv` beside
# the power index's `<season>.csv`, and `card_factors.load_second_opinion`
# reads every readable table and blends their CONSENSUS, so one source's quirk
# moves the card a third as far when three agree against it.
#
# How each is reached, and why:
#
# * KenPom through its own API, on Cooper's subscription, with his key in the
#   `KENPOM_API_KEY` secret. A licensed feed read with the owner's credential;
#   absent the secret it is skipped and the log says so.
# * The NCAA's NET from ncaa.com, ONLY when the site's robots.txt allows this
#   lab's agent. It is a ranking, not a rating, so it is mapped onto the
#   power index's own scale by rank (`net_to_ratings`).
# * T-Rank, Haslametrics or any other table in T-Rank's CSV shape from a file
#   Cooper drops into `data/manual/ratings_drop/<source>_<YYYY-MM-DD>.csv`.
#   barttorvik.com's robots.txt disallows ClaudeBot and anthropic-ai by name,
#   so this lab does not fetch it; a table its owner downloads is his to give.


KENPOM_SOURCE = "kenpom"
KENPOM_URL = "https://kenpom.com/api.php?endpoint=ratings&y={season}"
NET_SOURCE = "ncaa_net"
NET_URL = "https://www.ncaa.com/rankings/basketball-men/d1/ncaa-mens-basketball-net-rankings"
#: The agent names a robots.txt is read for. A fetch goes ahead only when
#: every one of them is allowed: this lab does not pick the name a site has
#: not closed to.
ROBOTS_AGENTS: tuple[str, ...] = ("ClaudeBot", "anthropic-ai", "*")
DROP_DIR = Path("data/manual/ratings_drop")
DROP_NAME = re.compile(r"^(?P<source>[a-z0-9_]+)_(?P<day>\d{4}-\d{2}-\d{2})\.csv$")
#: The spread of a D-I net rating per 100 possessions, used to place a NET
#: rank only when no rated table of the same day is there to borrow a scale
#: from. Measured on the power index's own table of 2026-11-08.
NET_FALLBACK_SD = 11.5


def allowed_by_robots(url: str, *, timeout: float = 30.0) -> tuple[bool, str]:
    """Whether the site's robots.txt allows every agent in ROBOTS_AGENTS.

    A robots.txt that cannot be read is NOT permission: the answer is no."""
    parts = urllib.parse.urlsplit(url)
    robots = f"{parts.scheme}://{parts.netloc}/robots.txt"
    request = urllib.request.Request(robots, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        return False, f"{robots} could not be read ({type(exc).__name__}); not fetched"
    parser = urllib.robotparser.RobotFileParser()
    parser.parse(body.splitlines())
    closed = [agent for agent in ROBOTS_AGENTS if not parser.can_fetch(agent, url)]
    if closed:
        return False, f"{robots} disallows {', '.join(closed)}; not fetched"
    return True, ""


def _get(url: str, *, headers: dict | None = None, timeout: float = 60.0) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        raise SecondOpinionError(f"{url.split('?')[0]}: HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise SecondOpinionError(f"{url.split('?')[0]}: {type(exc).__name__}") from exc


def fetch_kenpom(api_key: str, season: int) -> bytes:
    """KenPom's ratings for `season`, with the subscriber's key. The key is
    sent as a bearer token and never printed, logged or written."""
    if not api_key:
        raise SecondOpinionError("no KenPom key")
    return _get(KENPOM_URL.format(season=int(season)),
                headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"})


def _field(row: dict, names: tuple[str, ...]):
    keyed = {_key(k): v for k, v in row.items()}
    for name in names:
        if name in keyed and keyed[name] not in (None, ""):
            return keyed[name]
    return None


def parse_kenpom(payload: bytes) -> pd.DataFrame:
    """`team, adj_off, adj_def, adj_tempo` from KenPom's ratings JSON.

    Read by field NAME (`AdjOE`, `AdjDE`, `AdjTempo`, `TeamName`, in any case
    or spacing), from a list of rows or a list under `data`. A row whose
    values sit outside the ranges a D-I efficiency and tempo sit in is
    dropped, and a table with none left is refused."""
    try:
        data = json.loads(payload)
    except ValueError as exc:
        raise SecondOpinionError(f"KenPom did not answer JSON: {exc}") from exc
    if isinstance(data, dict):
        data = data.get("data") or data.get("ratings") or data.get("teams") or []
    out = []
    for row in data if isinstance(data, list) else []:
        if not isinstance(row, dict):
            continue
        team = _field(row, HEADER_NAMES["team"] + ("school", "name"))
        try:
            off = float(_field(row, HEADER_NAMES["adj_off"]))
            de = float(_field(row, HEADER_NAMES["adj_def"]))
        except (TypeError, ValueError):
            continue
        tempo = _field(row, HEADER_NAMES["adj_tempo"])
        try:
            tempo = float(tempo)
        except (TypeError, ValueError):
            tempo = float("nan")
        if not team or not (EFFICIENCY_RANGE[0] <= off <= EFFICIENCY_RANGE[1]
                            and EFFICIENCY_RANGE[0] <= de <= EFFICIENCY_RANGE[1]):
            continue
        if tempo == tempo and not TEMPO_RANGE[0] <= tempo <= TEMPO_RANGE[1]:
            tempo = float("nan")
        out.append({"team": str(team).strip(), "adj_off": off, "adj_def": de, "adj_tempo": tempo})
    if not out:
        raise SecondOpinionError("KenPom's answer held no team with offence and defence")
    return pd.DataFrame(out, columns=["team", "adj_off", "adj_def", "adj_tempo"])


_ROW = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
_CELL = re.compile(r"<t[dh][^>]*>(.*?)</t[dh]>", re.S | re.I)
_TAG = re.compile(r"<[^>]+>")


def parse_net(payload: bytes) -> pd.DataFrame:
    """`team, net_rank` from the NCAA's NET page: the first table whose rows
    open with a rank and a school."""
    text = payload.decode("utf-8", "replace")
    out = []
    for row in _ROW.findall(text):
        cells = [re.sub(r"\s+", " ", _TAG.sub("", c)).strip() for c in _CELL.findall(row)]
        if len(cells) < 2 or not cells[0].isdigit():
            continue
        rank, school = int(cells[0]), cells[1].replace("&amp;", "&")
        if school:
            out.append({"team": school, "net_rank": rank})
    frame = pd.DataFrame(out, columns=["team", "net_rank"]).drop_duplicates("team")
    if len(frame) < card_factors.SECOND_OPINION_MIN_TEAMS:
        raise SecondOpinionError(f"the NET page held {len(frame)} ranked school(s); a table needs "
                                 f"{card_factors.SECOND_OPINION_MIN_TEAMS}")
    return frame


def net_to_ratings(net: pd.DataFrame, reference: pd.DataFrame | None = None) -> pd.DataFrame:
    """A NET rank placed on a rating scale: the k-th ranked team takes the k-th
    best net rating of `reference` (a rated table of the same day, as the card
    reads it), or a normal quantile at `NET_FALLBACK_SD` without one. The net
    is split evenly between offence and defence, around a nominal 100, and the
    tempo is left empty: NET says nothing about pace."""
    frame = net.sort_values("net_rank").reset_index(drop=True)
    n = len(frame)
    nets = None
    if reference is not None and len(reference) >= n // 2:
        ref = (pd.to_numeric(reference["adj_off"], errors="coerce")
               - pd.to_numeric(reference["adj_def"], errors="coerce")).dropna()
        ref = ref - ref.mean()
        if len(ref) >= 2:
            qs = (frame.index.to_numpy() + 0.5) / n
            nets = np.quantile(ref.to_numpy(), 1.0 - qs)
    if nets is None:
        from statistics import NormalDist

        dist = NormalDist(0.0, NET_FALLBACK_SD)
        nets = np.array([dist.inv_cdf(1.0 - (i + 0.5) / n) for i in range(n)])
    out = frame.assign(adj_off=100.0 + nets / 2.0, adj_def=100.0 - nets / 2.0, adj_tempo=float("nan"))
    return out[["team", "adj_off", "adj_def", "adj_tempo", "net_rank"]]


def drops(day: str, *, root: Path | str = ".") -> dict[str, Path]:
    """The newest dropped table per source dated on or before `day`."""
    base = Path(root) / DROP_DIR
    found: dict[str, tuple[str, Path]] = {}
    if not base.is_dir():
        return {}
    for path in base.iterdir():
        match = DROP_NAME.match(path.name)
        if not match or match["day"] > str(day)[:10]:
            continue
        source = match["source"]
        if source not in found or match["day"] > found[source][0]:
            found[source] = (match["day"], path)
    return {source: path for source, (_, path) in found.items()}
