"""A player name that resolves to nobody is unknown, and unknown is not a void.

`scripts/run_price_backtest.py` graded a prop whose player name matched no row
of `cbb_player_games.csv` for that game as `Outcome.VOID`, *"does not appear in
this game's box score"*. That conflates two different facts:

* a **did-not-play** — a player the box score lists, marked `did_not_play`,
  whose stake the book returns (an assumption, stated in `settlement.py`);
* an **unresolved name** — a string this lab could not match to anybody on
  either team. A misspelling, a nickname, a provider naming a player the feed
  spells differently, or a player traded before tip. Nothing is known about
  him, least of all whether he played.

`VOID` is a book's verdict and enters the bet count with zero profit;
`UNSETTLEABLE` is this lab's admission and enters the exclusion count. Folding
the second into the first pads the record with bets that were never graded, and
does it silently — every such row reads as a legitimate returned stake.

The rule pinned here: an unresolved name is `UNSETTLEABLE`, counted in the
census under its own field, and printed; `VOID` is reached only through
`settlement._player_guard` on a **resolved** player row that carries
`did_not_play`; a resolved player who played is graded on his stat line.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pandas as pd

from cbb_betting_lab.selection import FULL_GAME, OVER
from cbb_betting_lab.settlement import Outcome

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run_price_backtest.py"
MODULE = "cbb_price_backtest_under_test_unresolved_name"

GAME = 5001
HOME_TEAM, AWAY_TEAM = 10, 20
PLAYED, BENCHED = "Alpha Player", "Beta Bench"


def backtest():
    """The script imported as a module; its `__main__` guard runs nothing."""
    existing = sys.modules.get(MODULE)
    if existing is not None:
        return existing
    spec = importlib.util.spec_from_file_location(MODULE, SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[MODULE] = module
    spec.loader.exec_module(module)
    return module


def _team_games() -> pd.DataFrame:
    common = {"game_id": GAME, "season": 2026, "slate_date": "2026-01-10",
              "periods": 2, "overtime": False}
    return pd.DataFrame([
        {**common, "team_id": HOME_TEAM, "opponent_id": AWAY_TEAM, "home_away": "home",
         "team_score": 70, "opponent_score": 65, "margin": 5, "total": 135,
         "team_score_h1": 35, "opponent_score_h1": 30, "team_score_h2": 35,
         "opponent_score_h2": 35},
        {**common, "team_id": AWAY_TEAM, "opponent_id": HOME_TEAM, "home_away": "away",
         "team_score": 65, "opponent_score": 70, "margin": -5, "total": 135,
         "team_score_h1": 30, "opponent_score_h1": 35, "team_score_h2": 35,
         "opponent_score_h2": 35},
    ])


def _player_games() -> pd.DataFrame:
    """Two rows the box score carries: one who played, one who did not."""
    common = {"game_id": GAME, "season": 2026, "slate_date": "2026-01-10",
              "team_id": HOME_TEAM, "opponent_id": AWAY_TEAM, "home_away": "home"}
    return pd.DataFrame([
        {**common, "athlete_id": 1, "athlete_display_name": PLAYED,
         "did_not_play": False, "minutes": 31, "points": 22, "rebounds": 6,
         "assists": 4},
        # The did-not-play row, exactly as `build_player_games` carries it: the
        # flag set and no stat line at all.
        {**common, "athlete_id": 2, "athlete_display_name": BENCHED,
         "did_not_play": True, "minutes": None, "points": None,
         "rebounds": None, "assists": None},
    ])


def _wager(player: str, *, line: float = 18.5) -> dict:
    return {
        "event_id": f"e{GAME}", "market": "player_points", "segment": FULL_GAME,
        "player": player, "selection": OVER, "line": line, "book": "dk",
        "american_odds": -110, "game_id": GAME, "season": 2026,
        "slate_date": "2026-01-10",
    }


def _grade(*players: str):
    module = backtest()
    frame = pd.DataFrame([_wager(p) for p in players])
    census = module.GradingCensus()
    graded = module.grade(
        frame,
        fixtures=module.fixture_index(_team_games(), pd.DataFrame(), {GAME}),
        players=module.player_index(_player_games(), {GAME}),
        census=census,
    )
    return graded, census


def test_an_unresolved_name_is_unsettleable_and_counted_under_its_own_field():
    graded, census = _grade("Nobody Of That Name")
    row = graded.iloc[0]
    assert row["outcome"] == Outcome.UNSETTLEABLE.value, row["outcome"]
    assert pd.isna(row["actual"]) and pd.isna(row["profit_units"])
    assert "resolves to nobody" in row["settlement_note"]
    assert "unknown, not a did-not-play" in row["settlement_note"]

    assert census.rows == 1
    assert census.unsettleable == 1
    assert census.unresolved_player == 1
    # It is NOT a book's verdict: nothing graded, nothing void.
    assert census.graded == 0
    assert census.void == 0

    printed = "\n".join(census.lines())
    assert "1 name a player who resolves to nobody" in printed
    assert "never a void" in printed


def test_a_resolved_player_recorded_as_did_not_play_is_void():
    """The only road to VOID: a row this lab found, carrying `did_not_play`."""
    graded, census = _grade(BENCHED)
    row = graded.iloc[0]
    assert row["outcome"] == Outcome.VOID.value, row["outcome"]
    assert row["profit_units"] == 0.0
    assert "did_not_play" in row["settlement_note"] or "did not play" in row["settlement_note"]
    assert census.graded == 1
    assert census.void == 1
    assert census.unsettleable == 0
    assert census.unresolved_player == 0


def test_a_resolved_player_who_played_is_graded_on_his_stat_line():
    graded, census = _grade(PLAYED)
    row = graded.iloc[0]
    assert row["outcome"] == Outcome.WON.value, row["outcome"]
    assert row["actual"] == 22
    assert row["profit_units"] > 0
    assert census.graded == 1
    assert census.won == 1
    assert census.void == 0
    assert census.unresolved_player == 0


def test_the_three_are_told_apart_in_one_frame_and_the_census_adds_up():
    graded, census = _grade(PLAYED, BENCHED, "Nobody Of That Name", "Another Stranger")
    outcomes = list(graded["outcome"])
    assert outcomes == [
        Outcome.WON.value,
        Outcome.VOID.value,
        Outcome.UNSETTLEABLE.value,
        Outcome.UNSETTLEABLE.value,
    ]
    assert census.rows == 4
    assert census.graded == 2 and census.won == 1 and census.void == 1
    assert census.unsettleable == 2 and census.unresolved_player == 2
    assert census.graded + census.unsettleable == census.rows
    assert "2 name a player who resolves to nobody" in "\n".join(census.lines())


def test_the_spelling_that_voided_an_unresolved_name_is_gone():
    """The old note, verbatim, must not come back on either path."""
    source = SCRIPT.read_text(encoding="utf-8")
    assert "does not appear in this game's box score" not in source
