#!/usr/bin/env python3
"""Build the shot-zone panel for one season. Design: the directional analogue.

    # The league page and the record:
    PYTHONPATH=src python scripts/run_shot_zones.py --season 2026

    # One matchup, printed:
    PYTHONPATH=src python scripts/run_shot_zones.py --season 2026 \\
        --offense "UAB Blazers" --defense "Missouri State Bears"

`reports/shot_zones.py` owns every number and every refusal. This file owns the
wiring: which season's play-by-play and schedule are opened, where the record
is written, and turning a refusal into an exit code rather than a traceback.

**It buys nothing and spends no credit.** The play-by-play is already in the
raw store, pinned and hashed by `data/raw/cbb/manifest.json`, and this script
only reads it.

The season is a **required argument with no default**. A default would be the
current season, the current season is the only one that passes the coverage
bar today, and a reader who did not pass `--season` would get a page with no
indication that the other seven are refused.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cbb_betting_lab.competitions import CBB  # noqa: E402
from cbb_betting_lab.reports import shot_zones as SZ  # noqa: E402

# The sport's name is the registry's to write, never this file's. A literal
# "cbb" here is a second place the lab would have to be widened from.
RAW = REPO / "data" / "raw" / CBB.data_dir_segment
OUTPUTS = REPO / "data" / "outputs"
REPORT_STEM = "shot_zones"

EXIT_OK = 0
EXIT_REFUSED = 3
EXIT_INPUTS_ABSENT = 4


def team_names(schedule: pd.DataFrame) -> dict:
    """Every team id the schedule names, from both sides of every game."""
    names: dict = {}
    for side in ("home", "away"):
        ids, shown = f"{side}_id", f"{side}_display_name"
        if ids not in schedule or shown not in schedule:
            continue
        for team, name in zip(schedule[ids], schedule[shown]):
            if pd.notna(team) and pd.notna(name):
                names[str(int(team))] = str(name)
    return names


def resolve(name: str, names: dict) -> int:
    """A team id from what a person typed, or a refusal that lists near misses.

    Refuses an ambiguous prefix rather than taking the first match: two schools
    share a first word often enough ("Miami", "Saint Mary's") that silently
    picking one would put the wrong team's floor under the right team's name.
    """
    wanted = name.strip().casefold()
    exact = [i for i, n in names.items() if n.casefold() == wanted]
    if len(exact) == 1:
        return int(exact[0])
    near = sorted({n for n in names.values() if wanted in n.casefold()})
    if len(near) == 1:
        return int(next(i for i, n in names.items() if n == near[0]))
    raise SZ.ShotZoneError(
        f"{name!r} names {len(near)} teams in this season's schedule"
        + (f": {near[:8]}" if near else "; nothing matched")
        + ". Pass the display name exactly."
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True)
    parser.add_argument("--raw-dir", default=str(RAW))
    parser.add_argument("--output-dir", default=str(OUTPUTS))
    parser.add_argument("--offense", default="")
    parser.add_argument("--defense", default="")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)

    raw = Path(args.raw_dir)
    pbp_path = raw / "pbp" / f"play_by_play_{args.season}.parquet"
    schedule_path = raw / "schedules" / f"mbb_schedule_{args.season}.parquet"
    for path in (pbp_path, schedule_path):
        if not path.is_file():
            print(
                f"::error::{path} is absent. Fetch it with "
                f"`python scripts/fetch_cbb_data.py --season {args.season}`; "
                "this script buys nothing and reads only what is already "
                "pinned in the manifest.",
                file=sys.stderr,
            )
            return EXIT_INPUTS_ABSENT

    schedule = pd.read_parquet(schedule_path)
    pbp = pd.read_parquet(pbp_path, columns=list(SZ.REQUIRED_COLUMNS))
    names = team_names(schedule)

    print(
        f"NCAA Division I men's basketball — shot zones, {args.season}\n"
        f"Play-by-play: {pbp_path} ({len(pbp):,} rows)\n"
        f"Schedule:     {schedule_path} ({len(schedule):,} games)"
    )
    try:
        record = SZ.build_record(
            SZ.ShotZoneInputs(
                pbp=pbp,
                season=args.season,
                schedule=schedule,
                source=str(pbp_path),
                team_names=names,
            ),
            generated_at=pd.Timestamp.now("UTC").isoformat(timespec="seconds"),
        )
    except SZ.ShotZoneError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_REFUSED

    cover, member = record["coverage"], record["membership"]
    print(
        f"\n{cover['charted_games']:,} of {cover['games']:,} games charted "
        f"({cover['share']:.1%}); {member['attempts_division_one']:,} "
        f"Division-I attempts described over "
        f"{member['division_one_teams']:,} programmes."
    )
    for row in record["league"]:
        print(
            f"  {row['label']:<20s} {row['attempts']:>7,}  "
            f"{row['attempt_share']:6.1%}  {row['points_per_attempt']:.3f} PPA"
        )

    if args.offense or args.defense:
        if not (args.offense and args.defense):
            print(
                "::error::--offense and --defense are given together or not "
                "at all. One side of a matchup is half a panel, and the half "
                "that is missing is the one that would say whether the other "
                "half means anything.",
                file=sys.stderr,
            )
            return EXIT_REFUSED
        try:
            page = SZ.render_matchup(
                record,
                offense=resolve(args.offense, names),
                defense=resolve(args.defense, names),
            )
        except SZ.ShotZoneError as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return EXIT_REFUSED
        print()
        print(page)

    if not args.no_write:
        out = Path(args.output_dir)
        stem = f"{REPORT_STEM}_{args.season}"
        record_path = SZ.write_record(record, out / CBB.output_name(stem, ".json"))
        report_path = SZ.write_report(record, out / CBB.output_name(stem, ".md"))
        print(f"\nWrote {record_path} and {report_path}.")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
