"""The Results page settles YESTERDAY'S slate, named in Eastern time.

Until 2026-11-16 `web/settle_results.py` settled the UTC date less one. From
00:00 to 05:00 UTC (7 PM to midnight Eastern, the heart of every evening
slate) that is tonight's Eastern date, so each evening publish settled the
slate still being played. The board's lean record counted tonight's early
finals while the Tracker, which names its day in Eastern time, did not:
132-156 on the board against 132-154 on the Tracker on 2026-11-15.
"""

from __future__ import annotations

import importlib.util
from datetime import date, datetime, timezone
from pathlib import Path

SETTLE = Path(__file__).resolve().parents[1] / "web" / "settle_results.py"


def _settle():
    spec = importlib.util.spec_from_file_location("settle_results_eastern", SETTLE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_an_evening_publish_settles_last_night_not_tonight():
    # 21:37 ET on Sunday 2026-11-15 is 02:37 UTC on Monday.
    now = datetime(2026, 11, 16, 2, 37, tzinfo=timezone.utc)
    assert _settle().slate_yesterday(now) == date(2026, 11, 14)


def test_a_morning_publish_settles_last_night():
    now = datetime(2026, 11, 16, 13, 44, tzinfo=timezone.utc)
    assert _settle().slate_yesterday(now) == date(2026, 11, 15)


def test_the_two_pages_name_their_day_in_the_same_zone():
    settle = _settle()
    spec = importlib.util.spec_from_file_location("build_site_pages_zone", SETTLE.parent / "build_site_pages.py")
    text = spec.origin and Path(spec.origin).read_text(encoding="utf-8")
    assert 'ZoneInfo("America/New_York")' in text
    assert str(settle.SLATE_TZ) == "America/New_York"
