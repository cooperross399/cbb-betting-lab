"""Audit tonight's layers against what happened, and switch them for the next card.

    PYTHONPATH=src python scripts/run_layer_audit.py --as-of 2026-11-20

Re-prices the last `layer_audit.WINDOW_DAYS` slate days before `--as-of`,
newest first, through `ratings.matchups_for` — the card's own seam — with each
day fitted only on games strictly before it, and judges every switchable layer
in `card_factors` on the games it moved (`models/layer_audit.py`). Writes the
switches to `data/raw/<sport>/layer_audit/latest.json`, which the card and the
board read under `card_factors.load_layer_audit`, and prints the table.

SOFT, the way the second opinion is: Gameday Refresh runs it with
`continue-on-error`, and a run that cannot audit leaves the card on its
declared layers. It stops pricing new days at `--budget-minutes` and judges
what it has. Spends no credit and reads no price.

Exit codes: 0 audited and written; 2 nothing to audit (no results table, or no
finished game in the window), in which case nothing is written.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

import pandas as pd

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import PROCESSED_DIR, RAW_DIR
from cbb_betting_lab.models import layer_audit, ratings
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.reports.card_matchups import InputsAbsent, load_player_games, load_team_games


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--as-of", default=None, help="The day the audit is for (YYYY-MM-DD); today in the league's timezone by default. Only games before it are read.")
    parser.add_argument("--days", type=int, default=layer_audit.WINDOW_DAYS, help="Slate days to re-price.")
    parser.add_argument("--budget-minutes", type=float, default=20.0, help="Stop pricing new days after this long.")
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--summary", default=None, help="Also append the table to this file (the run summary).")
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


def audit(as_of: str, *, days: int, budget_minutes: float, processed_dir, raw_dir) -> tuple[dict | None, str]:
    team_games = load_team_games(CBB, processed_dir)
    try:
        player_games = load_player_games(CBB, processed_dir)
    except Exception:  # noqa: BLE001 - the lineup layer then moves nothing, and says so
        player_games = None
    dates = team_games["slate_date"].astype(str)
    window = sorted({d for d in dates.unique() if d < as_of}, reverse=True)[:days]
    if not window:
        return None, f"no finished game before {as_of} in the results table"
    results = results_by_game(team_games)
    started = time.monotonic()
    records: list[dict] = []
    priced: list[str] = []
    notes: list[str] = []
    for day in window:
        if (time.monotonic() - started) / 60.0 > budget_minutes:
            notes.append(f"stopped at the {budget_minutes:g}-minute budget after {len(priced)} day(s)")
            break
        ids = sorted({int(g) for g in team_games.loc[dates == day, "game_id"].dropna()})
        prices = pd.DataFrame([{"event_id": str(g), "game_id": g} for g in ids])
        try:
            matchups = ratings.matchups_for(
                day=day,
                history=PB.history_before(team_games, day),
                prices=prices,
                raw_dir=Path(raw_dir),
                player_games=None if player_games is None else PB.history_before(player_games, day),
            )
        except Exception as exc:  # noqa: BLE001 - one day that cannot be priced is a note, not the end
            notes.append(f"{day} could not be priced ({type(exc).__name__}: {exc})")
            continue
        priced.append(day)
        for event_id, game in matchups.items():
            scores = results.get(int(event_id), {})
            home, away = getattr(game, "home_team_id", None), getattr(game, "away_team_id", None)
            if home not in scores or away not in scores:
                continue
            record = layer_audit.game_moves(
                game, day=day, game_id=int(event_id),
                actual_margin=scores[home] - scores[away], actual_total=scores[home] + scores[away],
            )
            if record is not None:
                records.append(record)
    frame = pd.DataFrame(records)
    if frame.empty:
        return None, f"no priceable finished game in the {len(priced)} day(s) re-priced"
    verdicts = layer_audit.judge(frame)
    return layer_audit.payload(verdicts, as_of=as_of, frame=frame, days_priced=priced, notes=notes), ""


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    as_of = str(args.as_of or datetime.now(CBB.timezone).date().isoformat())[:10]
    try:
        record, reason = audit(
            as_of, days=args.days, budget_minutes=args.budget_minutes,
            processed_dir=args.processed_dir, raw_dir=args.raw_dir,
        )
    except (FileNotFoundError, InputsAbsent) as exc:
        record, reason = None, f"the results tables are not on disk ({exc})"
    if record is None:
        print(f"Layer audit for {as_of}: nothing written, {reason}. The card keeps its declared layers.")
        return 2
    path = layer_audit.save(record, args.raw_dir)
    text = layer_audit.render(record)
    print(text)
    switched = [v["label"] for v in record["layers"] if v["on"] != v["default"]]
    print(f"Layer audit written to {path}: " + (
        "switched from the declared card: " + ", ".join(switched) if switched else "every layer as declared"
    ) + ".")
    if args.summary:
        with open(args.summary, "a", encoding="utf-8") as handle:
            handle.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
