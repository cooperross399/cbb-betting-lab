"""Which projection picks the side of the spread best? (decision 118)

    PYTHONPATH=src python scripts/study_ats_sources.py [--processed-dir DIR] [--raw-dir DIR]

Cooper, 2026-11-21: *"use the kenpom and all the other rankings to get that
ATS hit to 55%"*. Before anything is wired, this measures it. For every game
the forward ledger froze at the main full-game spread this season, it reads:

* the market's line (the median over books at the first snapshot) and the
  final margin the ledger settled it on;
* the card's own margin (from its frozen cover probability at that line);
* KenPom's projected margin for that day (FanMatch, `data/raw/cbb/kenpom/`,
  never committed and never printed per game);
* the published ratings tables on file for the day before (KenPom, ESPN's
  power index, the NET; `second_opinion/history/`), each turned into a margin
  as the difference of the two net ratings at the game's tempo plus a home
  edge on a true home floor;

and reports, per source and per tier, how often the side it is on covers,
and how that rate moves when only games where it disagrees with the line by
at least 1, 2, 3 or 4 points are counted. Also a consensus (the mean of every
source present) and the games on which KenPom and the card agree.

Results only: it reads no price from any provider, spends no credit, selects
and withdraws nothing, and prints only aggregate rates. A rate is reported
with its games beside it and an interval: a hit rate over a few hundred games
moves by several points either way by chance alone.
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import PROCESSED_DIR, RAW_DIR
from cbb_betting_lab.models import card_factors as CF
from cbb_betting_lab.models import spread_bias as SB
from cbb_betting_lab.providers import team_names

HOME_EDGE = 3.0
THRESHOLDS = (0.0, 1.0, 2.0, 3.0, 4.0)
BREAK_EVEN = 0.5238


def games_from_ledger(ledger: pd.DataFrame) -> pd.DataFrame:
    rows = ledger[
        (ledger["market"].astype(str) == "spread")
        & (ledger["segment"].astype(str).isin(("game", "full_game")))
        & (ledger["selection"].astype(str) == "home")
    ].copy()
    rows["p"] = pd.to_numeric(rows["model_probability"], errors="coerce")
    rows["line"] = pd.to_numeric(rows["line"], errors="coerce")
    rows["actual"] = pd.to_numeric(rows["actual"], errors="coerce")
    rows["date"] = rows["snapshot_date"].astype(str).str[:10]
    first = rows.groupby("event_id")["date"].transform("min")
    rows = rows[rows["date"] == first]
    games = rows.groupby("event_id").agg(
        date=("date", "first"), home=("home_team", "first"), away=("away_team", "first"),
        tier=("tier", "first"), line=("line", "median"), actual=("actual", "first"),
        p=("p", "median"),
    ).reset_index()
    games = games.dropna(subset=["line", "actual"])
    quantile = NormalDist().inv_cdf
    games["card"] = [
        SB.SIGMA * quantile(float(p)) - line if p == p and 0.001 < p < 0.999 else np.nan
        for p, line in zip(games["p"], games["line"])
    ]
    return games


def kenpom_margins(games: pd.DataFrame, raw_dir: Path) -> list[float]:
    cache: dict[str, dict] = {}
    out = []
    for row in games.itertuples():
        if row.date not in cache:
            table: dict = {}
            path = CF.kenpom_path(raw_dir, row.date)
            if path.is_file():
                try:
                    frame = pd.read_csv(path)
                    for f in frame.itertuples():
                        try:
                            h, a = int(f.home_id), int(f.away_id)
                        except (TypeError, ValueError):
                            continue
                        table[(h, a)] = float(f.home_pred) - float(f.away_pred)
                except (OSError, ValueError, AttributeError):
                    table = {}
            cache[row.date] = table
        table = cache[row.date]
        value = np.nan
        if row.home_id is not None and row.away_id is not None:
            if (row.home_id, row.away_id) in table:
                value = table[(row.home_id, row.away_id)]
            elif (row.away_id, row.home_id) in table:
                value = -table[(row.away_id, row.home_id)]
        out.append(value)
    return out


def table_margins(games: pd.DataFrame, raw_dir: Path) -> dict[str, list[float]]:
    """Each source's margin from its newest dated table strictly before the day."""
    folder = CF.second_opinion_history_path(raw_dir, "x", "x").parent
    files: dict[str, list[tuple[str, Path]]] = {}
    if folder.is_dir():
        for path in folder.glob("*.csv"):
            stamp, _, source = path.stem.partition(".")
            if source:
                files.setdefault(source, []).append((stamp, path))
    loaded: dict[Path, dict] = {}
    out: dict[str, list[float]] = {}
    for source, dated in files.items():
        dated.sort()
        values = []
        for row in games.itertuples():
            usable = [p for s, p in dated if s < row.date and (pd.Timestamp(row.date) - pd.Timestamp(s)).days <= 3]
            value = np.nan
            if usable and row.home_id is not None and row.away_id is not None:
                path = usable[-1]
                if path not in loaded:
                    try:
                        frame = pd.read_csv(path).dropna(subset=["team_id"])
                        frame["team_id"] = frame["team_id"].astype(int)
                        for c in ("adj_off", "adj_def", "adj_tempo"):
                            frame[c] = pd.to_numeric(frame.get(c), errors="coerce")
                        tempo = frame["adj_tempo"].mean() if frame["adj_tempo"].notna().any() else 68.0
                        loaded[path] = {
                            int(t): (float(o) - float(d), float(tp) if tp == tp else tempo)
                            for t, o, d, tp in zip(frame["team_id"], frame["adj_off"], frame["adj_def"], frame["adj_tempo"])
                            if o == o and d == d
                        }
                    except (OSError, ValueError, KeyError):
                        loaded[path] = {}
                table = loaded[path]
                if row.home_id in table and row.away_id in table:
                    (nh, th), (na, ta) = table[row.home_id], table[row.away_id]
                    pace = (th + ta) / 2.0
                    value = (nh - na) * pace / 100.0 + (0.0 if row.neutral else HOME_EDGE)
            values.append(value)
        out[source] = values
    return out


def interval(hits: int, n: int) -> str:
    if n == 0:
        return ""
    p = hits / n
    half = 1.96 * math.sqrt(p * (1 - p) / n)
    return f"{100 * (p - half):.1f}% to {100 * (p + half):.1f}%"


def rate(frame: pd.DataFrame, column: str, threshold: float = 0.0) -> tuple[int, int]:
    part = frame.dropna(subset=[column])
    edge = part[column] + part["line"]
    cover = part["actual"] + part["line"]
    keep = (edge.abs() >= threshold) & (edge != 0) & (cover != 0)
    edge, cover = edge[keep], cover[keep]
    return int((np.sign(edge) == np.sign(cover)).sum()), int(len(edge))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--season", type=int, default=2027)
    parser.add_argument("--output", default="data/outputs/cbb_ats_sources.md")
    args = parser.parse_args(argv)
    raw = Path(args.raw_dir)

    ledger = pd.read_csv(Path(args.processed_dir) / "cbb_forward_evidence.csv", low_memory=False)
    games = games_from_ledger(ledger)
    schedule = pd.read_parquet(raw / CBB.data_dir_segment / "schedules" / f"mbb_schedule_{args.season}.parquet")
    index = team_names.build_index(schedule)
    games["home_id"] = [index.resolve(n) for n in games["home"]]
    games["away_id"] = [index.resolve(n) for n in games["away"]]
    games["home_id"] = [int(v) if v is not None else None for v in games["home_id"]]
    games["away_id"] = [int(v) if v is not None else None for v in games["away_id"]]
    neutral = {}
    if "neutral_site" in schedule.columns:
        for r in schedule.itertuples():
            try:
                neutral[(int(r.home_id), int(r.away_id))] = bool(r.neutral_site)
            except (TypeError, ValueError, AttributeError):
                continue
    games["neutral"] = [neutral.get((h, a), False) for h, a in zip(games["home_id"], games["away_id"])]

    games["kenpom"] = kenpom_margins(games, raw)
    sources = ["card", "kenpom"]
    for source, values in table_margins(games, raw).items():
        games[f"table_{source}"] = values
        sources.append(f"table_{source}")
    present = [s for s in sources if games[s].notna().any()]
    games["consensus"] = games[[s for s in present if s != "card"]].mean(axis=1, skipna=True) if len(present) > 1 else np.nan
    sources.append("consensus")
    both = games.dropna(subset=["card", "kenpom"])
    agree = both[np.sign(both["card"] + both["line"]) == np.sign(both["kenpom"] + both["line"])]
    games["kenpom_when_card_agrees"] = np.nan
    games.loc[agree.index, "kenpom_when_card_agrees"] = agree["kenpom"]
    sources.append("kenpom_when_card_agrees")

    lines = [
        "# Which projection picks the side of the spread best",
        "",
        f"{len(games)} games the forward ledger froze at the main spread, {games['date'].min()} to {games['date'].max()}; "
        f"{sum(v is not None for v in games['home_id'])} home teams resolved. A side wins when it covers the "
        f"first-snapshot median line; pushes are dropped. Break-even at -110 is {100 * BREAK_EVEN:.1f}%.",
        "",
        "| Source | Edge at least | Games | Covered | Rate | 95% interval |",
        "|:---|---:|---:|---:|---:|:---|",
    ]
    for source in sources:
        if source not in games or not games[source].notna().any():
            lines.append(f"| {source} | — | 0 | — | — | no projection on file |")
            continue
        for t in THRESHOLDS:
            hits, n = rate(games, source, t)
            if n:
                lines.append(f"| {source} | {t:g} | {n} | {hits} | {100 * hits / n:.1f}% | {interval(hits, n)} |")
    lines += ["", "## Per tier, every game", "", "| Source | Tier | Games | Rate |", "|:---|:---|---:|---:|"]
    for source in sources:
        if source not in games or not games[source].notna().any():
            continue
        for tier in ("high_major", "mid_major", "low_major"):
            hits, n = rate(games[games["tier"] == tier], source)
            if n:
                lines.append(f"| {source} | {tier} | {n} | {100 * hits / n:.1f}% |")
    lines += ["", "## Correlation of each source's disagreement with the line and the result against the line", ""]
    cover = games["actual"] + games["line"]
    for source in sources:
        if source in games and games[source].notna().sum() > 30:
            part = games[source].notna()
            r = np.corrcoef(games.loc[part, source] + games.loc[part, "line"], cover[part])[0, 1]
            lines.append(f"- {source}: r = {r:+.3f} over {int(part.sum())} games")
    text = "\n".join(lines) + "\n"
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    Path(args.output).write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
