"""The two calendar conventions, checked against the source rather than asserted.

Both are members of the join-vocabulary bug family, which reached five members
in the NHL lab and cost weeks. Both are cheap to get wrong and silent when
wrong: a season label that is off by one makes every filter miss, and a date
that is off by one drops the late games and keeps the early ones.

These tests read the real hoopR schedule when it is cached and fall back to
pinned literals from it when it is not, so CI proves the convention without a
network call and a local run proves it against the bytes.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import RAW_DIR
from cbb_betting_lab.season import season_for_slate_date, slate_date


#: Read out of `mbb_schedule_2026.parquet` and `mbb_schedule_2027.parquet` on
#: 2026-09-01. hoopR labels a season by the year it ENDS.
SOURCE_SEASON_SPANS = {
    2026: ("2025-11-03", "2026-04-07"),
    2027: ("2026-11-02", "2027-03-06"),
}


def test_the_season_label_is_the_ending_year_like_hoopR():
    for season, (first, last) in SOURCE_SEASON_SPANS.items():
        assert season_for_slate_date(first) == season, (
            f"hoopR files {first} under season {season}. Labelling by the "
            "starting year makes every season filter miss on one side of the "
            "join, silently."
        )
        assert season_for_slate_date(last) == season


def test_july_is_the_cut_and_nothing_countable_falls_near_it():
    assert season_for_slate_date("2026-06-30") == 2026
    assert season_for_slate_date("2026-07-01") == 2027


def test_the_slate_day_is_the_eastern_calendar_date():
    """Measured, not chosen. See `competitions.DAY_BOUNDARY_HOUR`."""
    assert slate_date("2027-01-12T17:00:00Z", CBB) == "2027-01-12"  # noon ET
    assert slate_date("2027-01-12T16:00:00Z", CBB) == "2027-01-12"  # 11am ET
    assert slate_date("2027-01-13T04:00:00Z", CBB) == "2027-01-12"  # 23:00 ET


def test_the_hawaii_game_is_filed_on_its_eastern_date_like_espn_files_it():
    """The one game in the 2025-26 season that tips before 08:00 Eastern.

    East Texas A&M at Hawai'i, 20:00 in Honolulu on 2025-11-09, which is
    2025-11-10T06:00Z and 01:00 Eastern on 2025-11-10. **ESPN files it under
    2025-11-10.** A six-hour "basketball day" boundary — which is what the
    first version of this lab used, by analogy with hockey — would put it on
    2025-11-09 and miss the join. It is the single row in the season that can
    tell the two conventions apart, so it gets its own test.
    """
    assert slate_date("2025-11-10T06:00:00Z", CBB) == "2025-11-10"


def test_no_boundary_hour_is_silently_reintroduced():
    """The constant is named so a future session can change it deliberately."""
    from cbb_betting_lab.competitions import DAY_BOUNDARY_HOUR

    assert DAY_BOUNDARY_HOUR == 0, (
        "The boundary was measured against ESPN's own filed date over 6,318 "
        "games: 0 disagreements at 0 hours, 1 at six. Changing it needs a "
        "re-measurement, not a re-reading of the docstring."
    )


@pytest.mark.parametrize("season", sorted(SOURCE_SEASON_SPANS))
def test_against_the_real_schedule_when_it_is_cached(season: int):
    """When the parquet is on disk, check every row rather than three literals."""
    path = Path(RAW_DIR) / "cbb" / "schedules" / f"mbb_schedule_{season}.parquet"
    if not path.is_file():
        pytest.skip(f"{path.name} is not cached; the pinned literals stand in.")
    frame = pd.read_parquet(path, columns=["season", "date"])
    days = frame["date"].map(
        lambda x: slate_date(pd.Timestamp(x).tz_convert("UTC").isoformat(), CBB)
    )
    labels = days.map(season_for_slate_date)
    assert (labels == frame["season"]).all(), (
        "This lab's season label disagrees with hoopR's on "
        f"{int((labels != frame['season']).sum())} of {len(frame)} rows."
    )
