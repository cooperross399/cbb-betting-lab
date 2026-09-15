"""Write what the feature library measures on the real archive, as a record.

**This exists because a skipped test is not a test.** The calibration checks --
does eFG% average what college basketball averages, do the player rates
reconcile to their team totals -- need the raw archive, and the archive is
gitignored, so on a clean checkout those tests skipped. This repository refuses a
skip outright: "a gate that passes when it should fail".

So the measurement is made HERE, against the real data, and committed as a
record; the tests then read the record, which is tracked. That is the pattern the
rest of the lab already uses -- every report writes a record and its test
compares against it -- and it means the calibration is checked on every clone,
against numbers that were computed on the archive once and cannot drift silently
afterwards.

Re-run it when the feature code changes:
    PYTHONPATH=src python scripts/build_feature_calibration.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from cbb_betting_lab.competitions import CBB  # noqa: E402
from cbb_betting_lab.models import player_features as PF  # noqa: E402
from cbb_betting_lab.models import team_features as TF  # noqa: E402

RECORD = REPO / "data" / "outputs" / "cbb_feature_calibration.json"
SEASON = 2025

#: Bumped when a field's shape or meaning changes, per this lab's convention.
RECORD_VERSION = 1


def build() -> dict:
    games = pd.read_csv(REPO / "data" / "processed" / "cbb_team_games.csv")
    season = games[(games["season"] == SEASON) & (games["game_state"] == "countable")]
    if season.empty:
        raise SystemExit(f"no countable {SEASON} rows; the archive is not built here")
    team = TF.per_game_features(season)

    # The sport segment comes from the Competition, never a literal: this repo
    # has sibling labs and one hardcoded "cbb" is how a script starts reading
    # the wrong one. `test_competition_registry_is_the_only_place` enforces it.
    box = pd.read_parquet(
        REPO / "data" / "raw" / CBB.data_dir_segment / "player_box"
        / f"player_box_{SEASON}.parquet"
    )
    players = PF.player_game_features(box)
    grouped = players.groupby(["game_id", "team_id"], observed=True)

    return {
        "record_version": RECORD_VERSION,
        "season": SEASON,
        "team_games": int(len(team)),
        "player_games": int(len(players)),
        "team_means": {
            column: float(team[column].mean())
            for column in (
                "efg_pct", "turnover_rate", "off_reb_pct", "def_reb_pct",
                "free_throw_rate", "off_efficiency", "def_efficiency", "tempo",
                "true_shooting_pct", "three_point_rate", "block_rate", "steal_rate",
            )
        },
        "player_means": {
            column: float(players[column].mean())
            for column in ("usage_rate", "true_shooting_pct", "turnover_rate", "game_score")
        },
        # The identities, measured on the archive. A denominator error breaks
        # these and nothing else would show it.
        "identities": {
            "minutes_share_per_team_game": float(grouped["minutes_share"].sum().mean()),
            "usage_weighted_per_team_game": float(
                players.assign(w=players.usage_rate * players.minutes_share)
                .groupby(["game_id", "team_id"], observed=True)["w"].sum().mean()
            ),
            "off_reb_weighted_per_team_game": float(
                players.assign(w=players.off_reb_rate * players.minutes_share)
                .groupby(["game_id", "team_id"], observed=True)["w"].sum().mean()
            ),
        },
    }


def main() -> int:
    RECORD.write_text(json.dumps(build(), indent=2) + "\n", encoding="utf-8")
    print(f"wrote {RECORD.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
