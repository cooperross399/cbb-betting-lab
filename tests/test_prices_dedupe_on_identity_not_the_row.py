"""A duplicated store does not look wrong. It looks significant.

The NHL lab deduplicated its price store on the whole row, timestamps included,
so two buys of the same window wrote every quote twice under two snapshot
labels. **ROI is unchanged by exact duplication and the interval narrows by
root two.** Its first clean run reported 144,060 bets and an interval half
again too tight, and nothing about the output looked broken.

This is a day-one regression test because the defect is invisible without one.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from cbb_betting_lab.stats import interval_by_cluster
from cbb_betting_lab.stores import (
    PRICE_IDENTITY,
    assert_single_window,
    best_price_per_wager,
    dedupe_prices,
)


def _quote(book="dk", odds=-110, fetched="2027-01-12T15:00:00Z", line=145.5):
    return {
        "event_id": "e1",
        "market": "total_points",
        "segment": "game",
        "player": "",
        "selection": "over",
        "line": line,
        "book": book,
        "snapshot_phase": "card",
        "american_odds": odds,
        "fetched_at": fetched,
    }


def test_the_same_quote_fetched_twice_is_one_row():
    frame = pd.DataFrame(
        [_quote(fetched="2027-01-12T15:00:00Z"), _quote(fetched="2027-01-12T18:00:00Z")]
    )
    assert len(frame) == 2
    assert len(dedupe_prices(frame)) == 1, (
        "Two fetches of one quote must collapse. If they do not, every "
        "interval in this lab is root-two too narrow and nothing looks wrong."
    )


def test_the_timestamp_is_not_part_of_price_identity():
    """The guard, stated as a property rather than a behaviour."""
    for field in PRICE_IDENTITY:
        assert "time" not in field and "fetched" not in field and field != "at", (
            f"{field!r} is in PRICE_IDENTITY. A timestamp there re-introduces "
            "the NHL lab's root-two interval defect."
        )


def test_duplication_would_narrow_the_interval_by_root_two():
    """Reproduce the harm, so the guard above is known to be load-bearing."""
    rows = [
        {"event_id": f"g{i}", "profit": p, "bets": 1}
        for i, p in enumerate([1.0, -1.0] * 200)
    ]
    once = pd.DataFrame(rows)
    twice = pd.concat([once, once], ignore_index=True)
    a = interval_by_cluster(once.set_index("event_id"))
    b = interval_by_cluster(twice.groupby("event_id").sum())
    # Same ROI...
    assert math.isclose(a.roi, b.roi, abs_tol=1e-9)
    # ...and the doubled store's per-bet interval is materially tighter.
    doubled_naive = interval_by_cluster(
        twice.reset_index(drop=True).assign(k=range(len(twice))).set_index("k")
    )
    assert doubled_naive.standard_error < a.standard_error / 1.3, (
        "Exact duplication is supposed to tighten a naive interval by about "
        "root two. If it does not, this reproduction is wrong."
    )


def test_many_books_on_one_wager_collapse_to_one_bet_at_the_best_price():
    """Twenty-one books quoting one game is not twenty-one bets."""
    frame = pd.DataFrame(
        [_quote(book="dk", odds=-110), _quote(book="fd", odds=+105), _quote(book="mgm", odds=-120)]
    )
    best = best_price_per_wager(frame)
    assert len(best) == 1
    assert int(best.iloc[0]["american_odds"]) == 105, (
        "American odds do not sort numerically: +105 pays more than -110, and "
        "a naive sort would pick -110."
    )


def test_a_store_holding_two_snapshot_windows_refuses_to_be_measured_as_one():
    frame = pd.DataFrame([_quote(), {**_quote(), "snapshot_phase": "close"}])
    with pytest.raises(ValueError, match="snapshot windows"):
        assert_single_window(frame)


def test_one_window_is_fine_and_names_itself():
    assert assert_single_window(pd.DataFrame([_quote()])) == "card"
