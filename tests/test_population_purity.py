"""No women's or non-D-I identifier reaches the population.

`competitions.py` cited this file as the thing that "fails the build if a
women's or non-D-I identifier reaches the population through a provider key,
an ESPN id or a scraped page", and until 2026-09-04 it did not exist. What
CAN be enforced from inside this repository is narrower than that sentence,
and it is written here at its real width:

* the provider side: the registry names the men's sport key and only the
  men's; the women's key `basketball_wncaab` appears in no registry entry and
  in no non-docstring constant under `src/` or `scripts/`
  (`tests/test_competition_registry_is_the_only_place.py` is the scan; this
  file asserts the registry half and reuses the scan on a planted module);
* the results side: `population.division_one_team_ids` admits a team only
  when the feed gives it a conference, and `classify_game` files a game with
  a non-D-I side under `NON_DI_OPPONENT` rather than `COUNTABLE` — proved
  here on a hand-built schedule and on the tracked 2025-26 schedule, where
  the 551 games with a non-D-I side (CLAUDE.md's count) must all be excluded.

What is NOT enforced, said plainly: a scraped page is not read by anything in
this repository today, so "a scraped page" has no guard because it has no
code. The day one is written, this file is where its exclusion gets pinned.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab import population as P
from cbb_betting_lab.competitions import CBB, COMPETITIONS
from conftest import schedule_fixture

WOMENS_SPORT_KEY = "basketball_wncaab"


def test_the_registry_names_the_mens_key_and_only_the_mens_key() -> None:
    assert CBB.provider_sport_key == "basketball_ncaab"
    for competition in COMPETITIONS.values():
        assert WOMENS_SPORT_KEY not in competition.provider_sport_key
        assert all(WOMENS_SPORT_KEY not in key for key in competition.futures_sport_keys)
        assert "wncaab" not in competition.provider_sport_key


def test_the_womens_key_is_a_finding_in_shipped_code(tmp_path: Path) -> None:
    """The registry scan treats the women's key as banned even though no
    entry names it, so a session that widens the lab by literal is caught."""
    from test_competition_registry_is_the_only_place import BANNED_SPORT_KEYS, offending_strings

    assert WOMENS_SPORT_KEY in BANNED_SPORT_KEYS
    planted = tmp_path / "widened.py"
    planted.write_text(f'SPORT = "{WOMENS_SPORT_KEY}"\n', encoding="utf-8")
    assert offending_strings(planted)


def _schedule(rows: list[dict]) -> pd.DataFrame:
    base = {
        "notes_headline": "", "status_type_name": "STATUS_FINAL",
        "home_conference_id": None, "away_conference_id": None,
    }
    return pd.DataFrame([{**base, **row} for row in rows])


def test_a_team_without_a_conference_is_not_division_one() -> None:
    schedule = _schedule([
        {"home_id": 1, "away_id": 2, "home_conference_id": 10, "away_conference_id": 11},
        {"home_id": 1, "away_id": 999, "home_conference_id": 10},  # 999 never carries one
    ])
    assert P.division_one_team_ids(schedule) == {1, 2}


def test_a_game_with_a_non_division_one_side_is_never_countable() -> None:
    schedule = _schedule([
        {"home_id": 1, "away_id": 2, "home_conference_id": 10, "away_conference_id": 11},
        {"home_id": 1, "away_id": 999, "home_conference_id": 10},
        {"home_id": 999, "away_id": 2, "away_conference_id": 11},
    ])
    di = P.division_one_team_ids(schedule)
    states = [P.classify_game(row, di) for row in schedule.to_dict("records")]
    assert states[0] is P.GameState.COUNTABLE
    assert states[1] is P.GameState.NON_DI_OPPONENT
    assert states[2] is P.GameState.NON_DI_OPPONENT
    classified = P.classify(schedule)
    assert list(classified["game_state"]) == ["countable", "non_di_opponent", "non_di_opponent"]


def test_a_game_with_an_unknown_side_is_not_countable_either() -> None:
    """A missing id is not a D-I id. Absence is never a pass."""
    row = {"home_id": None, "away_id": 2, "notes_headline": "", "status_type_name": "STATUS_FINAL"}
    assert P.classify_game(row, {2}) is P.GameState.UNKNOWN


def test_the_real_season_excludes_every_game_with_a_non_division_one_side() -> None:
    """CLAUDE.md: 6,318 games in 2025-26, 5,752 D-I versus D-I, 551 with a
    non-D-I side. Over the tracked schedule, every one of the 551 must land
    outside `countable`, and the D-I universe must be the 365 teams the
    conference walk yields."""
    schedule = pd.read_parquet(schedule_fixture(2026))
    di = P.division_one_team_ids(schedule)
    assert len(di) == 365, f"{len(di)} D-I team ids; the NCAA count is 365"
    classified = P.classify(schedule)
    non_di = classified[
        ~classified["home_id"].isin(di) | ~classified["away_id"].isin(di)
    ]
    assert len(non_di) == 551, f"{len(non_di)} games with a non-D-I side; CLAUDE.md counts 551"
    assert (non_di["game_state"] != P.GameState.COUNTABLE.value).all()
    assert non_di["game_state"].eq(P.GameState.NON_DI_OPPONENT.value).sum() >= 540
    countable = classified[classified["game_state"] == P.GameState.COUNTABLE.value]
    assert countable["home_id"].isin(di).all() and countable["away_id"].isin(di).all()
    print(
        f"\n  population: {len(countable):,} countable of {len(schedule):,} games; "
        f"{len(non_di):,} with a non-D-I side, all excluded (2025-26, tracked schedule)."
    )


def test_a_scraped_page_has_no_guard_because_it_has_no_code() -> None:
    """The honest edge of this file: nothing under src/ fetches or parses an
    HTML page, so there is nothing to exclude. If that changes, this test is
    the one that must start reading it."""
    src = Path(__file__).resolve().parents[1] / "src" / "cbb_betting_lab"
    scrapers = [
        p for p in src.rglob("*.py")
        if "BeautifulSoup" in p.read_text(encoding="utf-8") or "html.parser" in p.read_text(encoding="utf-8")
    ]
    assert scrapers == [], f"a page parser has appeared ({scrapers}); pin its population exclusion here"
