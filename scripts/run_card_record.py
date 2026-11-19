"""Grade every pick the card has made, with its closing-line value.

    PYTHONPATH=src python scripts/run_card_record.py \
        [--comments-dir DIR] [--selections data/processed/cbb_card_selections.csv]

Reads the carried record of card picks (`cbb_card_selections.csv`, restored
from `card-feed`), adds this run's selections from `cbb_card_state.json` and
any published card comments in `--comments-dir` (the backfill: one file per
past run of `latest_card_comment.md`), settles every pick with the forward
ledger's own settlement, reads each against the closing line, and writes
`data/outputs/cbb_card_record.json` for the site and the updated selections
file for `card-feed` (`reports/card_record.py`).

SOFT in Gameday Refresh: it reads no price from any provider, spends no credit
and changes nothing the card reads.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from cbb_betting_lab import forward_evidence, reachability, season
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from cbb_betting_lab.reports import card_record




def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument("--archive-dir", default=str(forward_evidence.ARCHIVE_DIR))
    parser.add_argument("--selections", default="", help="The carried record of card picks (default: processed dir).")
    parser.add_argument("--state", default="", help="This run's card state (default: output dir).")
    parser.add_argument("--comments-dir", default="", help="Past card comments to read picks back from.")
    args = parser.parse_args(argv)

    processed, outputs = Path(args.processed_dir), Path(args.output_dir)
    selections_path = Path(args.selections) if args.selections else processed / card_record.SELECTIONS_FILENAME
    state_path = Path(args.state) if args.state else outputs / "cbb_card_state.json"

    carried = card_record.read_selections(selections_path)
    from_comments: list[dict] = []
    comments_read = 0
    if args.comments_dir and Path(args.comments_dir).is_dir():
        for path in sorted(Path(args.comments_dir).glob("*.md")):
            try:
                from_comments.extend(card_record.parse_comment(path.read_text(encoding="utf-8")))
                comments_read += 1
            except (OSError, UnicodeError):
                continue
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        state = None
    current = card_record.from_state(state)

    picks = card_record.merge(carried, current, from_comments)
    ledger = forward_evidence.read_ledger(processed / forward_evidence.LEDGER_FILENAME)
    store = reachability.load_store(CBB, processed)
    picks = card_record.fill_events(picks, ledger, store)
    card_record.write_selections(picks, selections_path)

    # Loaded only now: a run that cannot read the tables still keeps the picks.
    # The name index is built over the seasons the PICKS fall in, never the
    # archive's: a pick read back from a comment has no snapshot behind it.
    from run_forward_evidence import load_tables, load_team_index  # noqa: E402  (scripts/ is on the path)

    seasons = tuple(sorted({season.season_for_slate_date(d) for d in picks["slate_date"].dropna().astype(str) if d}))
    tables = load_tables(processed, competition=CBB)
    index, _, _ = load_team_index(Path(args.raw_dir), competition=CBB, seasons=seasons)
    graded = card_record.grade(
        picks,
        team_games=tables["team_games"],
        player_games=tables["player_games"],
        game_segments=tables["game_segments"],
        team_index=index,
    )
    graded = card_record.with_closing_value(graded, store)
    record = card_record.build_record(
        graded, as_of=datetime.now(timezone.utc).date().isoformat(), comments_read=comments_read
    )
    path = card_record.write_record(record, outputs)
    print(
        f"Card record: {record['picks']:,} pick(s) "
        f"({len(carried):,} carried, {len(current):,} from this card, {len(from_comments):,} read from "
        f"{comments_read:,} comment(s)); outcomes {record['outcomes']}; closing value on "
        f"{record['clv']['picks']:,}. Wrote {path} and {selections_path}."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
