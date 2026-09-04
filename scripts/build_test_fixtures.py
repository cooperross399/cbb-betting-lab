#!/usr/bin/env python3
"""Cut the tracked real-data sample the suite runs on where the tables are absent.

    PYTHONPATH=src python scripts/build_test_fixtures.py

`data/processed/*.csv` and `data/raw/cbb/schedules/` are gitignored — 208MB of
player-games and 460MB of hoopR releases have no business in a repository —
and until this file existed every test that read them **skipped** on a clone
without a build. That was 80 tests in CI, every one of them waiting on data CI
can never have, and `python -m pytest -q` exits 0 on a skip. The settlement
proofs, the provider-name resolution, the slate-day check against the source
and the cron-lateness arithmetic had therefore never once run on the machine
whose green tick the lab reads. A skip that cannot resolve is a test that does
not exist, wearing a test's name.

So this script cuts a **real** sample — rows the builder actually wrote, not a
fixture somebody typed — small enough to track, and the tests read it whenever
the full table is not on disk. The rules of the cut are written here so the
sample is reproducible from the full data and so a reader knows exactly what
the CI numbers are numbers *over*:

* **Processed tables.** Every home row of the most recent completed season in
  `cbb_team_games.csv`, sorted by `game_id`, and every `SAMPLE_STRIDE`-th one
  is kept until `SAMPLE_GAMES` games are drawn. A stride and not a head, so the
  draw spans November to April and every month has games in it — the
  retention probe stratifies by month and a November-only sample would leave
  its cells empty. Both team rows, every player row and the segment row of
  each drawn game come along, so the identities the settlement suite checks
  (`h1 + h2 == final`, `pra == points + rebounds + assists`, the double-double
  flag against the declared rule) can be checked on exactly the rows a book
  would grade.
* **Schedules.** Every row of the seasons in `SCHEDULE_SEASONS`, restricted to
  `SCHEDULE_COLUMNS` — the columns something in `src/` or `scripts/` actually
  reads, found by grepping for each name, plus the `home_`/`away_` pairs code
  reaches through an f-string. All rows and not a sample, because the
  provider-name test needs the whole D-I universe and the cron-lateness test
  needs the whole tip-time distribution. Dropping the 51 unread columns
  (logos, colours, broadcast, linescores, the whole game JSON) takes 1.76MB to
  340KB.

The manifest records which season, which stride, how many rows, and the sha256
of each source file, so a sample cut from a rebuilt table is distinguishable
from one cut from the table it claims.

**Nothing here is a substitute for the full run.** Locally, with the tables
built, the same tests read the full season and print the full counts; the
sample is what CI has, and every printed number says which of the two it is
over. Sample size is stated beside every measured number, and "400 games" and
"6,299 games" are different sample sizes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import PROCESSED_DIR, RAW_DIR, REPO_ROOT

#: Where the sample lives. Under `tests/` and not `data/`, because `data/` is
#: where the lab's *evidence* lives and a test fixture is not evidence.
FIXTURE_DIR = REPO_ROOT / "tests" / "fixtures" / "real_data"

#: The season the processed sample is cut from: the most recent completed one,
#: matching `tests/test_settlement_settles_real_games.py`'s `SEASON`.
SAMPLE_SEASON = 2026

#: How many games the processed sample holds, and the stride that spans the
#: season. 6,299 D-I games / 15 ≈ 420, capped at 400.
SAMPLE_GAMES = 400
SAMPLE_STRIDE = 15

#: The schedules the suite reads: the season under test, the one before it
#: (a walk-forward tier table needs a season strictly earlier), and the next
#: one (the season-label test checks both edges of the boundary).
SCHEDULE_SEASONS = (2025, 2026, 2027)

#: The schedule columns anything in this repository reads. Derived by grepping
#: `src/`, `scripts/` and `tests/` for each column name as a quoted literal,
#: then adding every `home_`/`away_` pair the code builds with an f-string
#: (`f"{side}_conference_id"`), which a literal grep cannot see.
SCHEDULE_COLUMNS: tuple[str, ...] = (
    "id",
    "game_id",
    "season",
    "date",
    "game_date",
    "game_date_time",
    "neutral_site",
    "notes_headline",
    "venue_id",
    "venue_address_city",
    "venue_address_state",
    "status_type_name",
    "status_type_completed",
    "team_box",
    "player_box",
    *(
        f"{side}_{column}"
        for side in ("home", "away")
        for column in (
            "id",
            "location",
            "name",
            "abbreviation",
            "display_name",
            "short_display_name",
            "conference_id",
            "score",
            "venue_id",
            "winner",
        )
    ),
)

PROCESSED_TABLES = ("cbb_team_games.csv", "cbb_player_games.csv", "cbb_game_segments.csv")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def drawn_game_ids(team_games: pd.DataFrame) -> list[int]:
    """The `SAMPLE_GAMES` game ids the stride lands on, in ascending order."""
    home = team_games[
        (team_games["season"] == SAMPLE_SEASON) & (team_games["home_away"] == "home")
    ]
    ids = sorted(int(g) for g in home["game_id"].unique())
    if not ids:
        raise SystemExit(f"no season {SAMPLE_SEASON} home rows in cbb_team_games.csv")
    drawn = ids[::SAMPLE_STRIDE][:SAMPLE_GAMES]
    if len(drawn) < SAMPLE_GAMES:
        raise SystemExit(
            f"only {len(drawn)} games at stride {SAMPLE_STRIDE}; {SAMPLE_GAMES} "
            "were asked for. Lower the stride rather than shipping a thinner "
            "sample than the tests were written against."
        )
    return drawn


def cut_processed(processed_dir: Path, out: Path) -> dict:
    team_games = pd.read_csv(processed_dir / "cbb_team_games.csv", low_memory=False)
    games = drawn_game_ids(team_games)
    keep = set(games)
    manifest: dict = {"game_ids": games, "tables": {}}
    frames = {
        "cbb_team_games.csv": team_games[
            (team_games["season"] == SAMPLE_SEASON) & team_games["game_id"].isin(keep)
        ],
    }
    players = pd.read_csv(processed_dir / "cbb_player_games.csv", low_memory=False)
    frames["cbb_player_games.csv"] = players[
        (players["season"] == SAMPLE_SEASON) & players["game_id"].isin(keep)
    ]
    segments = pd.read_csv(processed_dir / "cbb_game_segments.csv")
    frames["cbb_game_segments.csv"] = segments[segments["game_id"].isin(keep)]
    for name, frame in frames.items():
        if frame.empty:
            raise SystemExit(f"{name}: the draw selected no rows; refusing to write an empty sample")
        target = out / name
        frame.to_csv(target, index=False)
        manifest["tables"][name] = {
            "rows": int(len(frame)),
            "columns": list(frame.columns),
            "source": str((processed_dir / name).relative_to(REPO_ROOT)) if processed_dir.is_relative_to(REPO_ROOT) else str(processed_dir / name),
            "source_sha256": sha256(processed_dir / name),
        }
    return manifest


def cut_schedules(raw_dir: Path, out: Path) -> dict:
    manifest: dict = {}
    for season in SCHEDULE_SEASONS:
        source = raw_dir / CBB.data_dir_segment / "schedules" / f"mbb_schedule_{season}.parquet"
        if not source.is_file():
            raise SystemExit(f"{source} is not cached; run scripts/fetch_cbb_data.py first")
        frame = pd.read_parquet(source)
        columns = [c for c in SCHEDULE_COLUMNS if c in frame.columns]
        missing = [c for c in SCHEDULE_COLUMNS if c not in frame.columns]
        trimmed = frame[columns]
        if trimmed.empty:
            raise SystemExit(f"{source.name} trimmed to nothing")
        target = out / source.name
        trimmed.to_parquet(target, index=False)
        manifest[source.name] = {
            "rows": int(len(trimmed)),
            "columns": columns,
            "columns_absent_at_source": missing,
            "source_sha256": sha256(source),
        }
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--out", default=str(FIXTURE_DIR))
    args = parser.parse_args(argv)

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {
        "built_on": date.today().isoformat(),
        "sample_season": SAMPLE_SEASON,
        "sample_games": SAMPLE_GAMES,
        "sample_stride": SAMPLE_STRIDE,
        "rule": (
            f"every home row of season {SAMPLE_SEASON} sorted by game_id, every "
            f"{SAMPLE_STRIDE}th kept up to {SAMPLE_GAMES} games; both team rows, "
            "every player row and the segment row of each drawn game; every "
            "schedule row of the listed seasons restricted to the columns the "
            "code reads"
        ),
        "processed": cut_processed(Path(args.processed_dir), out),
        "schedules": cut_schedules(Path(args.raw_dir), out),
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    for name, table in manifest["processed"]["tables"].items():
        print(f"{name}: {table['rows']:,} rows")
    for name, table in manifest["schedules"].items():
        print(f"{name}: {table['rows']:,} rows, {len(table['columns'])} columns")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
