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
import urllib.request
from datetime import date
from pathlib import Path

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
) -> Path:
    """`data/raw/cbb/second_opinion/<season>.csv` in the columns the card reads."""
    path = card_factors.second_opinion_path(raw_dir, season)
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
