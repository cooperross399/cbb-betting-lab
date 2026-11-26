"""Replay the card's candidates through each card rule switched on and off.

    PYTHONPATH=src python scripts/run_card_whatif.py

Reads the carried candidates (`cbb_card_candidates.csv`, restored from
`card-feed`), grades them once with the forward ledger's settlement, replays
every slot with today's card rules and with each rule switched the other way,
and writes `data/outputs/cbb_card_whatif.md` (`reports/card_whatif.py`).

SOFT in Gameday Refresh: it reads no price from any provider, spends no credit
and changes nothing the card reads.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from cbb_betting_lab import season
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from cbb_betting_lab.reports import card_record, card_whatif


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    args = parser.parse_args(argv)

    processed, outputs = Path(args.processed_dir), Path(args.output_dir)
    candidates = card_whatif.read(processed / card_whatif.CANDIDATES_FILENAME)
    outcomes: dict = {}
    if not candidates.empty:
        from run_forward_evidence import load_tables, load_team_index  # noqa: E402  (scripts/ is on the path)

        seasons = tuple(sorted({season.season_for_slate_date(d) for d in candidates["slate_date"].astype(str) if d}))
        tables = load_tables(processed, competition=CBB)
        index, _, _ = load_team_index(Path(args.raw_dir), competition=CBB, seasons=seasons)
        unique = candidates.drop_duplicates(list(card_whatif.IDENTITY))
        graded = card_record.grade(
            unique,
            team_games=tables["team_games"],
            player_games=tables["player_games"],
            game_segments=tables["game_segments"],
            team_index=index,
        )
        outcomes = card_whatif.outcomes_for(unique, graded)
    result = card_whatif.build(candidates, outcomes)
    outputs.mkdir(parents=True, exist_ok=True)
    path = outputs / card_whatif.REPORT_FILENAME
    path.write_text(card_whatif.render(result), encoding="utf-8")
    print(f"Card what-if: {result['candidates']:,} candidate(s) over {len(result['days'])} day(s). Wrote {path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
