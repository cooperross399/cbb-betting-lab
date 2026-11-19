"""The card's own record: every pick, once, graded, with its closing value.

Cooper, 2026-11-19 ("do all 3"): the Record page counted one full-game pick per
game off the board, so most card picks were never graded on the site.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from cbb_betting_lab.reports import card_record as cr

WEB = Path(__file__).resolve().parents[1] / "web"

COMMENT = """**NCAA Division I men's basketball — 2026-11-19, morning slot.**
# CBB card — 2026-11-19 (morning)

## Selections

| Game | Market | Selection | Price | Bet down to | Size | When | Book | Model | Edge | Push mass | Prior weight | Tier |
|:---|:---|:---|---:|---:|---:|:---|:---|---:|---:|---:|---:|:---|
| VCU Rams at Santa Clara Broncos | moneyline (game) | away | +125 | +120 | 0.25u | Near tip | bovada | 41.1% | +4.46% | 0.00% | 59% | mid_major |
| Memphis Tigers at Iowa State Cyclones | alternate_team_total (game) | home_under +77.5 | +490 | +439 | 0.15u | Now | fanduel | 39.1% | +11.75% | 0.00% | 100% | high_major |
| High Point Panthers at Liberty Flames | spread_h1 (h1) | away -2.5 | -110 | -120 | 0.25u | Now | fanduel | 55.0% | +3.00% | 0.00% | 100% | mid_major |

**Bet down to** is the worst price.

## Exposure
"""

OLD_COMMENT = """# CBB card — 2026-11-02 (evening)

## Selections

| Game | Market | Selection | Price | Book | Model | Edge | Push mass | Prior weight | Tier |
|:---|:---|:---|---:|:---|---:|---:|---:|---:|:---|
| High Point Panthers at Liberty Flames | alternate_spread (game) | away -12.5 | +225 | fanduel | 26.0% | +3.95% | 0.00% | 100% | mid_major |
"""


def _site():
    spec = importlib.util.spec_from_file_location("site_pages_for_card_test", WEB / "site_pages.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_comment_is_read_by_its_header_whatever_columns_it_carries():
    picks = cr.parse_comment(COMMENT)
    assert [p["market"] for p in picks] == ["moneyline", "alternate_team_total", "spread_h1"]
    ml, tt, half = picks
    assert (ml["away_team"], ml["home_team"], ml["selection"], ml["line"]) == ("VCU Rams", "Santa Clara Broncos", "away", None)
    assert ml["american_odds"] == 125 and ml["bet_down_to"] == 120 and ml["book"] == "bovada"
    assert abs(ml["model_probability"] - 0.411) < 1e-9 and abs(ml["edge"] - 0.0446) < 1e-9
    assert (tt["selection"], tt["line"]) == ("home_under", 77.5)
    assert (half["segment"], half["line"], half["american_odds"]) == ("h1", -2.5, -110)
    old = cr.parse_comment(OLD_COMMENT)
    assert len(old) == 1 and old[0]["line"] == -12.5 and old[0]["bet_down_to"] is None
    assert old[0]["card_slot"] == "evening" and old[0]["tier"] == "mid_major"


def test_a_card_with_no_selections_table_reads_as_nothing():
    assert cr.parse_comment("# CBB card — 2026-11-01 (morning)\n\nNo selections.\n") == []
    assert cr.parse_comment("no card at all") == []


def test_one_pick_is_one_bet_kept_at_its_first_price():
    morning = cr.parse_comment(COMMENT)
    evening = [dict(p, card_slot="evening", american_odds=150.0) for p in morning]
    moved = dict(morning[0], card_slot="evening", line=None, selection="home")
    merged = cr.merge(evening, morning, [moved])
    assert len(merged) == 4
    vcu = merged[(merged["market"] == "moneyline") & (merged["selection"] == "away")]
    assert len(vcu) == 1 and vcu.iloc[0]["card_slot"] == "morning" and float(vcu.iloc[0]["american_odds"]) == 125


def test_the_structured_state_wins_over_its_own_comment_and_a_rehearsal_is_refused():
    state = {
        "slate_date": "2026-11-19", "card_slot": "morning", "decision": "selections",
        "selections": [{"event_id": "e1", "commence_time": "2026-11-20T03:00:00Z", "home_team": "Santa Clara Broncos",
                        "away_team": "VCU Rams", "market": "moneyline", "segment": "game", "player": "",
                        "selection": "away", "line": None, "american_odds": 125, "book": "bovada",
                        "model_probability": 0.411, "edge": 0.0446, "tier": "mid_major", "bet_down_to": 120}],
    }
    merged = cr.merge(cr.parse_comment(COMMENT), cr.from_state(state))
    vcu = merged[merged["market"] == "moneyline"].iloc[0]
    assert vcu["source"] == "state" and vcu["event_id"] == "e1"
    assert cr.from_state(dict(state, decision="rehearsal")) == []


def test_the_selections_file_round_trips(tmp_path):
    path = cr.write_selections(cr.merge(cr.parse_comment(COMMENT)), tmp_path / "s.csv")
    back = cr.read_selections(path)
    assert len(back) == 3 and len(cr.merge(back, cr.parse_comment(COMMENT))) == 3
    assert cr.read_selections(tmp_path / "absent.csv").empty


def test_a_comment_pick_finds_its_event_by_day_and_teams_and_refuses_two():
    picks = cr.merge(cr.parse_comment(COMMENT))
    ledger = pd.DataFrame([
        {"snapshot_date": "2026-11-19", "event_id": "e1", "commence_time": "2026-11-20T03:00:00Z",
         "home_team": "Santa Clara Broncos", "away_team": "VCU Rams"},
        {"snapshot_date": "2026-11-19", "event_id": "m1", "commence_time": "2026-11-19T23:00:00Z",
         "home_team": "Iowa State Cyclones", "away_team": "Memphis Tigers"},
        {"snapshot_date": "2026-11-19", "event_id": "m2", "commence_time": "2026-11-19T23:30:00Z",
         "home_team": "Iowa State Cyclones", "away_team": "Memphis Tigers"},
    ])
    filled = cr.fill_events(picks, ledger)
    by_market = dict(zip(filled["market"], filled["event_id"]))
    assert by_market["moneyline"] == "e1"
    assert not by_market["alternate_team_total"]  # two candidates: left without one


def _store(captured_at: str, rows: list[tuple]) -> pd.DataFrame:
    out = []
    for market, selection, line, odds, book in rows:
        out.append({"captured_at": captured_at, "slate_date": "2026-11-19", "event_id": "e1",
                    "commence_time": "2026-11-20T03:00:00Z", "home_team": "Santa Clara Broncos",
                    "away_team": "VCU Rams", "market": market, "segment": "game", "player": "",
                    "selection": selection, "line": line, "book": book, "american_odds": odds})
    return pd.DataFrame(out)


def test_closing_value_is_the_closing_chance_minus_the_price_and_halves_carry_none():
    picks = cr.fill_events(cr.merge(cr.parse_comment(COMMENT)), pd.DataFrame([
        {"snapshot_date": "2026-11-19", "event_id": "e1", "commence_time": "2026-11-20T03:00:00Z",
         "home_team": "Santa Clara Broncos", "away_team": "VCU Rams"}]))
    store = _store("2026-11-20T02:30:00Z", [("moneyline", "home", None, -150, "a"), ("moneyline", "away", None, 130, "a")])
    out = cr.with_closing_value(picks, store)
    vcu = out[out["market"] == "moneyline"].iloc[0]
    fair_away = (100 / 230) / (100 / 230 + 150 / 250)
    assert abs(vcu["close_probability"] - round(fair_away, 4)) < 1e-4
    assert abs(vcu["clv"] - round(fair_away - 100 / 225, 4)) < 1e-4
    assert out[out["market"] == "spread_h1"].iloc[0]["clv"] is None
    # A capture after tip is not the close.
    late = _store("2026-11-20T04:00:00Z", [("moneyline", "home", None, -150, "a"), ("moneyline", "away", None, 130, "a")])
    assert cr.with_closing_value(picks, late)["clv"].isna().all()


def test_a_game_without_a_final_is_pending_never_a_loss():
    picks = cr.merge(cr.parse_comment(COMMENT))
    from cbb_betting_lab.providers import team_names

    graded = cr.grade(
        picks,
        team_games=pd.DataFrame(columns=["game_id", "season", "slate_date", "team_id", "opponent_id", "home_away"]),
        player_games=pd.DataFrame(columns=["game_id", "team_id", "athlete_display_name"]),
        game_segments=pd.DataFrame(columns=["game_id"]),
        team_index=team_names.TeamIndex(),
        now=datetime(2026, 11, 20, tzinfo=timezone.utc),
    )
    assert set(graded["outcome"]) == {"pending"}
    record = cr.build_record(graded, as_of="2026-11-20")
    assert record["picks"] == 3 and record["outcomes"] == {"pending": 3}
    assert {r["result"] for r in record["rows"]} == {None}


def test_the_site_grades_every_card_pick_at_the_tracked_stake_by_category():
    site = _site()
    record = {"picks": 4, "outcomes": {}, "as_of": "2026-11-20", "rows": [
        {"date": "2026-11-19", "slot": "morning", "home": "Santa Clara Broncos", "away": "VCU Rams", "market": "moneyline",
         "segment": "game", "category": "Straight up", "selection": "away", "line": None, "price": 125.0, "betDownTo": 120.0,
         "book": "bovada", "tier": "mid_major", "result": "win", "clv": 0.012},
        {"date": "2026-11-19", "slot": "morning", "home": "Iowa State Cyclones", "away": "Memphis Tigers",
         "market": "alternate_team_total", "segment": "game", "category": "Team totals", "selection": "home_under",
         "line": 77.5, "price": 490.0, "book": "fanduel", "tier": "high_major", "result": "loss", "clv": -0.02},
        {"date": "2026-11-19", "slot": "evening", "home": "Liberty Flames", "away": "High Point Panthers",
         "market": "spread_h1", "segment": "h1", "category": "ATS", "selection": "away", "line": -2.5, "price": -110.0,
         "book": "fanduel", "tier": "mid_major", "result": "win", "clv": None},
        {"date": "2026-11-19", "slot": "evening", "home": "X", "away": "Y", "market": "moneyline", "segment": "game",
         "category": "Straight up", "selection": "home", "line": None, "price": -150.0, "result": None},
    ]}
    rows = site.card_tracker_rows(record, [])
    assert len(rows) == 3  # the pending pick is not staked
    assert [r["label"] for r in rows] == ["VCU Rams to win", "Iowa State Cyclones under 77.5", "High Point Panthers -2.5"]
    assert [r["market"] for r in rows] == ["Moneyline", "Alt team total", "1st half spread"]
    assert rows[0]["units"] == round(0.25 * 1.25, 4) and rows[1]["units"] == -0.15
    assert abs(rows[2]["units"] - 0.25) < 1e-9 and abs(rows[2]["staked"] - 0.275) < 1e-9
    page = site.tracker_page(rows, 1, record)
    assert page["source"] == "card"
    assert {c["key"] for c in page["byCategory"]} == {"Straight up", "Team totals", "ATS"}
    assert {c["key"] for c in page["bySlot"]} == {"morning", "evening"}
    assert page["clv"] == {"picks": 2, "meanPct": -0.4, "beatClosePct": 50.0}
    assert (page["overall"]["w"], page["overall"]["l"]) == (2, 1)


def test_without_a_card_record_the_board_is_the_record(tmp_path):
    site = _site()
    assert site.load_card_record(tmp_path / "absent.json") is None
    assert site.card_tracker_rows(None) == []
    assert site.tracker_page([], 0)["source"] == "board"
