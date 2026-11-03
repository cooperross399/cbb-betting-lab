"""What the model learned from last night, every morning.

    PYTHONPATH=src python scripts/run_nightly_learning.py --as-of 2026-11-03

Grades the last slate day before `--as-of` that has finished games: prices each
of them walk-forward through `ratings.matchups_for` (the card's own seam,
fitted on games strictly before that day) and compares the projection with the
final score; then fits the same seam again with that day included and reports
how far each team's rating moved. Adds the trust weights and the layer audit's
switches, writes `data/outputs/<sport>_nightly_learning.{json,md}`, and keeps
one row per graded night in `data/processed/<sport>_nightly_learning_history.csv`,
which Gameday Refresh carries on the card feed (`reports/nightly_learning.py`,
decision 78).

SOFT, the way the layer audit is: it reads no price, spends no credit and
changes nothing the card prices with, so a run that cannot grade still cards.

Exit codes: 0 graded and written; 2 nothing to grade (no results table, or no
finished game before the day), in which case a short report is still written.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from cbb_betting_lab import forward_evidence
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from cbb_betting_lab.models import card_factors, ratings, trust
from cbb_betting_lab.reports import nightly_learning as NL
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.reports.card_matchups import InputsAbsent, load_player_games, load_team_games


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--as-of", default=None, help="Today (YYYY-MM-DD) in the league's timezone by default. The night graded is the last slate day before it.")
    parser.add_argument("--day", default=None, help="Grade this slate day instead of the last one before --as-of.")
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--outputs-dir", default=str(OUTPUTS_DIR))
    parser.add_argument("--history", default=None, help="The season history CSV; under --processed-dir by default.")
    parser.add_argument("--summary", default=None, help="Also append the report to this file (the run summary).")
    return parser


def results_by_game(team_games: pd.DataFrame) -> dict:
    """game_id -> {team_id: points}, for finished games only."""
    out: dict = {}
    frame = team_games.dropna(subset=["game_id", "team_id", "team_score"])
    for row in frame[["game_id", "team_id", "team_score"]].itertuples(index=False):
        try:
            out.setdefault(int(row.game_id), {})[int(row.team_id)] = float(row.team_score)
        except (TypeError, ValueError):
            continue
    return out


def team_names(season: int, raw_dir) -> dict:
    """team_id -> a short display name, from the season's cached schedule."""
    try:
        schedule = ratings._cached_schedule(season, raw_dir)  # noqa: SLF001 - the card's own cache
    except Exception:  # noqa: BLE001 - names are labels, an id still reads
        return {}
    names: dict = {}
    for side in ("home", "away"):
        cols = [f"{side}_id", f"{side}_location", f"{side}_short_display_name", f"{side}_display_name"]
        if f"{side}_id" not in schedule.columns:
            continue
        for row in schedule[[c for c in cols if c in schedule.columns]].to_dict("records"):
            try:
                team = int(row[f"{side}_id"])
            except (TypeError, ValueError):
                continue
            label = row.get(f"{side}_location") or row.get(f"{side}_short_display_name") or row.get(f"{side}_display_name")
            if label and team not in names:
                names[team] = str(label)
    return names


def _price(day: str, ids, team_games, player_games, raw_dir):
    prices = pd.DataFrame([{"event_id": str(g), "game_id": g} for g in ids])
    matchups = ratings.matchups_for(
        day=day,
        history=PB.history_before(team_games, day),
        prices=prices,
        raw_dir=Path(raw_dir),
        player_games=None if player_games is None else PB.history_before(player_games, day),
    )
    return matchups, ratings.last_fit().get("ratings")


def _trust(as_of: str, outputs_dir, processed_dir) -> tuple[str, dict]:
    try:
        ledger = forward_evidence.read_ledger(Path(processed_dir) / forward_evidence.LEDGER_FILENAME)
    except Exception:  # noqa: BLE001 - the seed alone still reads
        ledger = None
    try:
        table = trust.build(as_of, outputs_dir=outputs_dir, ledger=ledger)
    except Exception as exc:  # noqa: BLE001
        return f"Trust table not read ({type(exc).__name__}).", {}
    weights = {t: {"weight": round(v.weight, 4), "seed": round(v.seed, 4), "settled_rows": v.ledger_rows}
               for t, v in table.by_tier.items()}
    return table.line(), weights


def _layers(raw_dir) -> dict:
    path = card_factors.layer_audit_path(raw_dir)
    if not path.is_file():
        return {}
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    layers = record.get("layers") or []
    return {
        "as_of": str(record.get("as_of", ""))[:10],
        "on": [v["label"] for v in layers if v.get("on")],
        "switched": [v["label"] for v in layers if v.get("on") != v.get("default")],
    }


def run(as_of: str, *, day: str | None, processed_dir, raw_dir, outputs_dir) -> tuple[dict, int]:
    notes: list[str] = []
    trust_line, weights = _trust(as_of, outputs_dir, processed_dir)
    layers = _layers(raw_dir)
    try:
        team_games = load_team_games(CBB, processed_dir)
    except (FileNotFoundError, InputsAbsent) as exc:
        notes.append(f"The results tables are not on disk ({exc}).")
        return NL.build_record(day=day or "", as_of=as_of, graded=[], moves=[], before=None, after=None,
                               trust_line=trust_line, trust_weights=weights, layers=layers, notes=notes), 2
    try:
        player_games = load_player_games(CBB, processed_dir)
    except Exception:  # noqa: BLE001 - the lineup layer then moves nothing
        player_games = None
    dates = team_games["slate_date"].astype(str)
    results = results_by_game(team_games)
    if day is None:
        finished = sorted({d for d in dates.unique() if d < as_of})
        day = finished[-1] if finished else None
    if not day:
        notes.append(f"No finished game before {as_of} in the results table.")
        return NL.build_record(day="", as_of=as_of, graded=[], moves=[], before=None, after=None,
                               trust_line=trust_line, trust_weights=weights, layers=layers, notes=notes), 2
    ids = sorted({int(g) for g in team_games.loc[dates == day, "game_id"].dropna()})
    try:
        matchups, before = _price(day, ids, team_games, player_games, raw_dir)
    except Exception as exc:  # noqa: BLE001 - a night that cannot be priced is a note
        notes.append(f"{day} could not be priced ({type(exc).__name__}: {exc}).")
        matchups, before = {}, None
    # The day after the graded one: the fit that has taken the night in. Never
    # past `as_of`, so a re-run on a later morning still reads the same night.
    next_day = (pd.Timestamp(day) + pd.Timedelta(days=1)).date().isoformat()
    after_day = min(next_day, as_of) if as_of > day else next_day
    try:
        _ignored, after = _price(after_day, ids, team_games, player_games, raw_dir)
    except Exception as exc:  # noqa: BLE001
        notes.append(f"The ratings could not be refitted through {day} ({type(exc).__name__}: {exc}).")
        after = None
    season = int(getattr(after or before, "season", 0) or 0)
    names = team_names(season, raw_dir) if season else {}
    graded = NL.grade(matchups, results, names)
    played = {t for g in graded for t in (g.home_team_id, g.away_team_id)}
    moves = NL.rating_moves(before, after, names, played=played)
    unpriced = len(ids) - len(graded)
    if unpriced > 0:
        notes.append(
            f"{unpriced:,} of {len(ids):,} game(s) on {day} carry no graded projection: "
            "a non-D-I opponent, a team the prior does not know, or a score not yet in the tables."
        )
    record = NL.build_record(day=day, as_of=as_of, graded=graded, moves=moves, before=before, after=after,
                             trust_line=trust_line, trust_weights=weights, layers=layers, notes=notes)
    return record, 0 if graded else 2


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    as_of = str(args.as_of or datetime.now(CBB.timezone).date().isoformat())[:10]
    record, status = run(as_of, day=args.day, processed_dir=args.processed_dir,
                         raw_dir=args.raw_dir, outputs_dir=args.outputs_dir)
    history_path = Path(args.history) if args.history else Path(args.processed_dir) / CBB.output_name("nightly_learning_history", ".csv")
    history = NL.update_history(history_path, record) if record.get("day") else NL.read_history(history_path)
    text = NL.render(record, history)
    json_path, md_path = NL.save(record, text, args.outputs_dir, CBB)
    print(text)
    print(f"Nightly learning written to {md_path} and {json_path}; season history at {history_path} ({len(history)} night(s)).")
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return status


if __name__ == "__main__":
    sys.exit(main())
