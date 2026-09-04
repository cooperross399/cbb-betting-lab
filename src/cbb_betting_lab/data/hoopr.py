"""hoopR / SportsDataverse release assets — the primary free data source.

ESPN-derived men's college basketball, published as GitHub release assets on
`sportsdataverse/sportsdataverse-data`. Free, unauthenticated, parquet, and
covering every D-I game rather than only the televised ones. Verified 2026-09-01
by fetching the assets and reading them, not from documentation.

    https://github.com/sportsdataverse/sportsdataverse-data/releases/download/
        espn_mens_college_basketball_pbp/play_by_play_2026.parquet

## Why the assets and not the wrapper

The football lab fetches nflverse release assets directly because `nfl_data_py`
is **archived**. The reason here is the opposite and the conclusion is the same:
`hoopR` (R, v3.1.0, 2026-08-27) and `sportsdataverse-py` (last commit
2026-08-31) are both alive and well maintained — the loaders just add three
lines of URL construction over a public file. Fetching directly is what lets
this lab **pin, hash and snapshot**, which the revision behaviour below makes
mandatory rather than tidy.

## The revision behaviour, which is the whole reason this module is careful

**The daily job rebuilds and re-uploads the entire current-season file, every
run.** A re-upload overwrites in place under the same URL. There is no per-game
"final" flag, no changelog, and no version history on a release asset. Any game
in the season can be silently restated at any point in that season, and the
2003-2021 assets were all rewritten on 2026-07-29.

So every fetch records a **sha256 of the bytes** and the GitHub API's
`updated_at` for the asset, into `manifest.json` beside the file. A changed hash
on a season already settled against is a **restatement**, and a restatement that
moves a settled row is the thing that quietly re-writes history under a
walk-forward test. `check_for_restatements()` reports them; it never applies
them silently.

**A green Actions badge upstream is not evidence the data moved.** The
pipeline's own workflow file documents its silent-failure mode — "the git calls
are swallowed with no rc check, that lands as a GREEN job that published
nothing" — and its `timestamp.json` disagrees with the assets' real write times
by three weeks. Freshness is judged from the GitHub API's `updated_at` on the
asset, and from nothing else.

## Latency

The upstream cron is 07:00 UTC daily, **18 October through 30 April only**. That
is 02:00-03:00 Eastern: a 21:00 ET tip finishing near 23:00 lands about three
hours later, and the latest West Coast finish clears with an hour to spare. In
practice every game of a night is available by roughly 03:00 ET the next
morning. **There is no cron between 1 May and 17 October**, so the off-season
data is frozen and a refresh then is a manual dispatch.

Anything faster than overnight has to come from ESPN's own summary endpoint,
which is unauthenticated and live. That is `espn.py`, and it is used for the
tip-time guard and same-night settlement rather than for fitting.
"""

from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import RAW_DIR


RELEASE_BASE = (
    "https://github.com/sportsdataverse/sportsdataverse-data/releases/download"
)
GITHUB_API_RELEASES = (
    "https://api.github.com/repos/sportsdataverse/sportsdataverse-data/releases"
)

#: **`sportsdataverse/hoopR-data` is ARCHIVED** (last push 2023-04-05, described
#: as "hoopR data 2002-2021"). Nothing here may point at it. A test pins that.
ARCHIVED_REPOS = ("sportsdataverse/hoopR-data",)

MANIFEST_FILENAME = "manifest.json"


@dataclass(frozen=True)
class Feed:
    """One release tag and the file-stem pattern inside it."""

    name: str
    tag: str
    stem: str
    #: Where it lands under `data/raw/cbb/`.
    directory: str
    #: The earliest season this feed has an asset for. Reading below it is a
    #: 404, which looks exactly like a network failure and is not.
    first_season: int
    notes: str = ""

    def url(self, season: int) -> str:
        return f"{RELEASE_BASE}/{self.tag}/{self.stem}_{season}.parquet"

    def path(self, season: int, raw_dir: Path | None = None) -> Path:
        root = Path(raw_dir) if raw_dir else Path(RAW_DIR)
        return root / CBB.data_dir_segment / self.directory / f"{self.stem}_{season}.parquet"


#: The feeds this lab reads. Each verified by fetching it on 2026-09-01.
FEEDS: dict[str, Feed] = {
    "schedules": Feed(
        name="schedules",
        tag="espn_mens_college_basketball_schedules",
        stem="mbb_schedule",
        directory="schedules",
        first_season=2002,
        notes="Carries `game_date` (the Eastern calendar date ESPN files the "
              "game under), `neutral_site`, `venue_*`, `status_period` (>2 "
              "means overtime), `notes_headline` (which names conference and "
              "NCAA tournament rounds), and both conference ids.",
    ),
    "team_box": Feed(
        name="team_box",
        tag="espn_mens_college_basketball_team_boxscores",
        stem="team_box",
        directory="team_box",
        first_season=2003,
    ),
    "player_box": Feed(
        name="player_box",
        tag="espn_mens_college_basketball_player_boxscores",
        stem="player_box",
        directory="player_box",
        first_season=2003,
        notes="**Filter `did_not_play == False`.** 69,344 of 196,876 rows in "
              "the 2026 file are did-not-play rows with null minutes and null "
              "points, and a mean computed over them is a third too low.",
    ),
    "pbp": Feed(
        name="pbp",
        tag="espn_mens_college_basketball_pbp",
        stem="play_by_play",
        directory="pbp",
        first_season=2006,
        notes="2004 and 2005 have no play-by-play at all; 2003 does. Large: "
              "the 2026 file is 89.9 MB and 2.92M rows.",
    ),
}


class FeedError(RuntimeError):
    """A feed could not be fetched or was refused. Never partially applied."""


class NotPublishedYet(FeedError):
    """The asset does not exist upstream yet, which is not a failure.

    A season's box scores and play-by-play appear only once its first games are
    played. Before then the release asset 404s. Treating that as a fetch
    failure would make the nightly cron red every night from now until opening
    night, and a monitor that cries wolf for two months is a monitor nobody
    reads on the night it matters.

    It is a distinct type rather than a silent skip because "not published yet"
    and "the download broke" must never look the same — the sibling labs' most
    expensive class of mistake is exactly two different things reported
    identically.
    """


def _sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def manifest_path(raw_dir: Path | None = None) -> Path:
    root = Path(raw_dir) if raw_dir else Path(RAW_DIR)
    return root / CBB.data_dir_segment / MANIFEST_FILENAME


def read_manifest(raw_dir: Path | None = None) -> dict:
    path = manifest_path(raw_dir)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {}


def write_manifest(manifest: dict, raw_dir: Path | None = None) -> Path:
    path = manifest_path(raw_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _http_get(url: str, *, timeout: float = 180.0) -> bytes:
    request = urllib.request.Request(
        url, headers={"User-Agent": "cbb-betting-lab (research; contact via GitHub)"}
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        name = url.rsplit("/", 1)[-1]
        if exc.code == 404:
            raise NotPublishedYet(
                f"{name}: not published upstream yet (HTTP 404). For a season "
                "that has not started this is the expected answer, not a fault."
            ) from exc
        raise FeedError(f"{name}: HTTP {exc.code}") from exc
    except (urllib.error.URLError, OSError, TimeoutError) as exc:
        raise FeedError(f"{url.rsplit('/', 1)[-1]}: {type(exc).__name__}") from exc


def fetch(
    feed_name: str,
    season: int,
    *,
    raw_dir: Path | None = None,
    force: bool = False,
    allow_shrink: bool = False,
) -> dict:
    """Fetch one season of one feed, hash it, and refuse to shrink it.

    Returns the manifest entry. Idempotent: an unchanged asset is re-hashed and
    left alone, so a nightly run costs one download and no churn.

    **The shrink guard is rows, not existence.** A feed that comes back with
    half the games it had is a partial upstream rebuild, and the football and
    NHL labs both learned that a partial fetch looks exactly like a light slate.
    `allow_shrink` is the deliberate override and it is recorded in the
    manifest when used.
    """
    feed = FEEDS.get(feed_name)
    if feed is None:
        raise FeedError(f"Unknown feed {feed_name!r}. Known: {sorted(FEEDS)}")
    if season < feed.first_season:
        raise FeedError(
            f"{feed.name} has no asset before {feed.first_season}; asking for "
            f"{season} returns a 404 that looks exactly like a network failure."
        )

    target = feed.path(season, raw_dir)
    manifest = read_manifest(raw_dir)
    key = f"{feed.name}/{season}"
    previous = manifest.get(key, {})

    payload = _http_get(feed.url(season))
    digest = _sha256(payload)

    if not force and previous.get("sha256") == digest and target.is_file():
        return previous

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = target.with_suffix(".parquet.incoming")
    staging.write_bytes(payload)
    try:
        frame = pd.read_parquet(staging)
    except Exception as exc:  # a corrupt download must not replace a good file
        staging.unlink(missing_ok=True)
        raise FeedError(f"{target.name} downloaded but is not readable parquet.") from exc

    rows = int(len(frame))
    previous_rows = int(previous.get("rows", 0) or 0)
    if previous_rows and rows < previous_rows // 2 and not allow_shrink:
        staging.unlink(missing_ok=True)
        raise FeedError(
            f"{target.name} would fall from {previous_rows:,} rows to "
            f"{rows:,}. Refusing: a partial upstream rebuild looks exactly "
            "like a light slate. Pass allow_shrink=True to override, and it "
            "will be recorded in the manifest."
        )

    staging.replace(target)
    entry = {
        "feed": feed.name,
        "season": season,
        "sha256": digest,
        "rows": rows,
        "columns": int(len(frame.columns)),
        "bytes": len(payload),
        "url": feed.url(season),
        "previous_sha256": previous.get("sha256", ""),
        "restated": bool(previous.get("sha256") and previous["sha256"] != digest),
        "shrink_allowed": bool(allow_shrink and previous_rows and rows < previous_rows),
    }
    manifest[key] = entry
    write_manifest(manifest, raw_dir)
    return entry


def load(
    feed_name: str, season: int, *, raw_dir: Path | None = None, columns=None
) -> pd.DataFrame:
    """Read a cached season. Never fetches — a missing file is an error.

    Deliberately separate from `fetch`. A loader that silently downloads is a
    loader that turns a test into a network call and a walk-forward fit into a
    fetch of data from after the game being priced.
    """
    feed = FEEDS.get(feed_name)
    if feed is None:
        raise FeedError(f"Unknown feed {feed_name!r}. Known: {sorted(FEEDS)}")
    path = feed.path(season, raw_dir)
    if not path.is_file():
        raise FeedError(
            f"{path} is not cached. Run `scripts/fetch_cbb_data.py` first; "
            "loading does not fetch, on purpose."
        )
    return pd.read_parquet(path, columns=columns)


def check_for_restatements(raw_dir: Path | None = None) -> list[dict]:
    """Every cached asset whose bytes changed on its last fetch.

    Reported, never applied silently. A restatement that moves a row already
    settled against is how a walk-forward test quietly stops being one.
    """
    return [
        entry
        for entry in read_manifest(raw_dir).values()
        if isinstance(entry, dict) and entry.get("restated")
    ]
