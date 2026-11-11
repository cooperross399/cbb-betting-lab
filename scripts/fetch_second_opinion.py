#!/usr/bin/env python3
"""Fetch the card's second opinion: a published ratings table, free.

    PYTHONPATH=src python scripts/fetch_second_opinion.py
    PYTHONPATH=src python scripts/fetch_second_opinion.py --season 2027 --as-of 2026-11-05

Spends no API credit and reads no credential. Writes
`data/raw/cbb/second_opinion/<season>.csv` in the columns
`card_factors.load_second_opinion` reads, with the names it could not place
beside it in `<season>.unresolved.json`.

Exit codes: 0 written and readable by the card; 1 the source could not be
fetched or parsed (nothing written, the previous table stands); 2 written but
under the `SECOND_OPINION_MIN_TEAMS` floor, so the card will not read it.
Every path is soft in the workflows: a card without a second opinion is a
card, and the log says which it was.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from cbb_betting_lab.config import RAW_DIR
from cbb_betting_lab.data import hoopr, second_opinion
from cbb_betting_lab.models import card_factors
from cbb_betting_lab.season import season_for_slate_date


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, default=None, help="hoopR season (its end year)")
    parser.add_argument("--as-of", default=None, help="the day the table is dated, YYYY-MM-DD")
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument(
        "--payload",
        default=None,
        help="read this file instead of fetching (tests and offline rehearsal)",
    )
    args = parser.parse_args(argv)

    today = datetime.now(ZoneInfo("America/New_York")).date()
    as_of = str(args.as_of or today.isoformat())[:10]
    season = int(args.season or season_for_slate_date(as_of) or 0)
    if not season:
        print(f"::error::No season for {as_of}.", file=sys.stderr)
        return 1
    raw_dir = Path(args.raw_dir)

    if args.payload:
        payload = Path(args.payload).read_bytes()
        url = str(args.payload)
    else:
        # ESPN's power index, keyed by team id (decision 71). The T-Rank
        # table this used to fetch answered HTTP 403 to every Actions run, and
        # its robots.txt closes it to this agent (`docs/cbb_data_sources.md`,
        # "Deliberately not used"), so it is no longer asked.
        code = _from_bpi(season, as_of, raw_dir)
        extra = _more_tables(season, as_of, raw_dir)
        return 0 if extra else code
    try:
        table = second_opinion.parse(payload)
    except second_opinion.SecondOpinionError as exc:
        print(f"::warning::The second opinion from {url} could not be read: {exc}", file=sys.stderr)
        return 1

    schedule_path = hoopr.FEEDS["schedules"].path(season, raw_dir)
    if not schedule_path.is_file():
        print(
            f"::warning::No cached schedule for {season} at {schedule_path}, so the "
            "table's names cannot be resolved. Run scripts/fetch_cbb_data.py first.",
            file=sys.stderr,
        )
        return 1
    import pandas as pd

    schedule = pd.read_parquet(schedule_path)
    resolved, unresolved = second_opinion.resolve(table, schedule)
    path = second_opinion.write(
        resolved, raw_dir=raw_dir, season=season, as_of=as_of, unresolved=unresolved
    )
    count = int(resolved["team_id"].notna().sum())
    print(
        f"Second opinion: {len(table)} team(s) read from {url}, {count} resolved to "
        f"this lab's ids, {len(unresolved)} not. Wrote {path} dated {as_of}."
    )
    if unresolved:
        print("Unresolved: " + ", ".join(sorted(unresolved)[:40]) + (" …" if len(unresolved) > 40 else ""))
    if count < card_factors.SECOND_OPINION_MIN_TEAMS:
        print(
            f"::warning::{count} resolved teams is under the "
            f"{card_factors.SECOND_OPINION_MIN_TEAMS} the card needs; it will price "
            "without a second opinion.",
            file=sys.stderr,
        )
        return 2
    return 0


def _from_bpi(season: int, as_of: str, raw_dir: Path) -> int:
    """ESPN's power index, keyed by the ids this lab already uses."""
    try:
        table = second_opinion.parse_bpi(second_opinion.fetch_bpi(), season=season)
    except second_opinion.SecondOpinionError as exc:
        print(f"::warning::The fallback second opinion could not be read either: {exc}", file=sys.stderr)
        return 1
    path = second_opinion.write(
        table, raw_dir=raw_dir, season=season, as_of=as_of, source=second_opinion.BPI_SOURCE
    )
    count = int(table["team_id"].notna().sum())
    print(
        f"Second opinion: {count} team(s) read from ESPN's power index by team id "
        f"(offence and defence; no tempo). Wrote {path} dated {as_of}."
    )
    if count < card_factors.SECOND_OPINION_MIN_TEAMS:
        print(f"::warning::{count} teams is under the {card_factors.SECOND_OPINION_MIN_TEAMS} the card needs.", file=sys.stderr)
        return 2
    return 0


def _schedule(season: int, raw_dir: Path):
    import pandas as pd

    path = hoopr.FEEDS["schedules"].path(season, raw_dir)
    return pd.read_parquet(path) if path.is_file() else None


def _write_named(table, *, source: str, season: int, as_of: str, raw_dir: Path, schedule) -> bool:
    """Resolve a name-keyed table and write it as `<season>.<source>.csv`."""
    if schedule is None:
        print(f"::warning::{source}: no cached schedule for {season}, so its names cannot be resolved.", file=sys.stderr)
        return False
    resolved, unresolved = second_opinion.resolve(table, schedule)
    path = second_opinion.write(resolved, raw_dir=raw_dir, season=season, as_of=as_of,
                                source=source, unresolved=unresolved, primary=False)
    count = int(resolved["team_id"].notna().sum())
    print(f"Second opinion ({source}): {len(table)} team(s) read, {count} resolved, "
          f"{len(unresolved)} not. Wrote {path} dated {as_of}.")
    if unresolved:
        print(f"  Unresolved ({source}): " + ", ".join(sorted(unresolved)[:30]) + (" …" if len(unresolved) > 30 else ""))
    return count >= card_factors.SECOND_OPINION_MIN_TEAMS


def _more_tables(season: int, as_of: str, raw_dir: Path) -> bool:
    """Every further published table this run can lawfully read (decision 92):
    KenPom with Cooper's key, the NET where robots.txt allows it, and any table
    Cooper dropped by hand. Each is soft and says why when it is skipped."""
    import os

    schedule = _schedule(season, raw_dir)
    wrote = False
    key = os.environ.get("KENPOM_API_KEY", "").strip()
    if key:
        try:
            from cbb_betting_lab.data import kenpom

            payload = second_opinion.fetch_kenpom(key, season)
            print("KenPom ratings fields: " + ", ".join(kenpom.field_names(payload)))
            table = second_opinion.parse_kenpom(payload)
            wrote |= _write_named(table, source=second_opinion.KENPOM_SOURCE, season=season,
                                  as_of=as_of, raw_dir=raw_dir, schedule=schedule)
        except second_opinion.SecondOpinionError as exc:
            print(f"::warning::KenPom could not be read: {exc}", file=sys.stderr)
        _kenpom_fanmatch(key, as_of, raw_dir, schedule)
    else:
        print("KenPom: no KENPOM_API_KEY secret, so not read.")
    allowed, why = second_opinion.allowed_by_robots(second_opinion.NET_URL)
    if allowed:
        try:
            net = second_opinion.parse_net(second_opinion._get(second_opinion.NET_URL))
            import pandas as pd

            reference = None
            primary = card_factors.second_opinion_path(raw_dir, season)
            if primary.is_file():
                reference = pd.read_csv(primary)
            wrote |= _write_named(second_opinion.net_to_ratings(net, reference),
                                  source=second_opinion.NET_SOURCE, season=season,
                                  as_of=as_of, raw_dir=raw_dir, schedule=schedule)
        except second_opinion.SecondOpinionError as exc:
            print(f"::warning::The NET could not be read: {exc}", file=sys.stderr)
    else:
        print(f"NET: {why}.")
    for source, path in sorted(second_opinion.drops(as_of).items()):
        try:
            table = second_opinion.parse(path.read_bytes())
        except second_opinion.SecondOpinionError as exc:
            print(f"::warning::The dropped table {path} could not be read: {exc}", file=sys.stderr)
            continue
        day = path.stem.rsplit("_", 1)[-1]
        wrote |= _write_named(table, source=source, season=season, as_of=day,
                              raw_dir=raw_dir, schedule=schedule)
    return wrote


def _kenpom_fanmatch(key: str, as_of: str, raw_dir: Path, schedule) -> None:
    """KenPom's projected scores for today, and for every day of the last
    `kenpom.BACKFILL_DAYS` not already on disk (decision 96). Soft: a day that
    cannot be read is skipped and the log says so; the key is never printed."""
    from datetime import date, timedelta

    from cbb_betting_lab.data import kenpom

    if schedule is None:
        print("::warning::KenPom FanMatch: no cached schedule, so its names cannot be resolved.", file=sys.stderr)
        return
    today = date.fromisoformat(as_of)
    days = [(today - timedelta(days=n)).isoformat() for n in range(kenpom.BACKFILL_DAYS, -1, -1)]
    named = False
    fetched = games = quiet = 0
    for day in days:
        if day != as_of and kenpom.fanmatch_path(raw_dir, day).is_file():
            continue
        try:
            payload = kenpom.fetch(key, "fanmatch", d=day)
        except kenpom.KenPomError as exc:
            if "HTTP 404" in str(exc) and day != as_of:
                # KenPom answers 404 for a day it has no games for (measured
                # 2026-11-11: every day before the season's first). Recorded as
                # an empty day so it is not asked again on every run.
                kenpom.write_fanmatch(kenpom.parse_fanmatch(b"[]", day=day), raw_dir=raw_dir, day=day)
                quiet += 1
                continue
            print(f"::warning::KenPom FanMatch for {day} could not be read: {exc}", file=sys.stderr)
            continue
        if not named and kenpom.field_names(payload):
            print("KenPom FanMatch fields: " + ", ".join(kenpom.field_names(payload)))
            named = True
        try:
            table = kenpom.parse_fanmatch(payload, day=day)
        except kenpom.KenPomError as exc:
            print(f"::warning::KenPom FanMatch for {day}: {exc}", file=sys.stderr)
            continue
        resolved, unresolved = kenpom.resolve(table, schedule)
        path = kenpom.write_fanmatch(resolved, raw_dir=raw_dir, day=day)
        fetched += 1
        both = int((resolved["home_id"].notna() & resolved["away_id"].notna()).sum()) if len(resolved) else 0
        games += both
        if day == as_of:
            print(f"KenPom FanMatch {day}: {len(table)} game(s) projected, {both} with both teams resolved. Wrote {path}.")
            if unresolved:
                print("  Unresolved (KenPom FanMatch): " + ", ".join(unresolved[:30]))
    print(f"KenPom FanMatch: {fetched} day(s) read this run, {games} resolved game(s) written"
          + (f"; {quiet} earlier day(s) KenPom has no games for, recorded as empty." if quiet else "."))


if __name__ == "__main__":
    raise SystemExit(main())
