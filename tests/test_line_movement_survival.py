"""Survival, and the difference between a price that went and one nobody looked at.

The reachability question is the one that decides whether any finding in this
lab is money: **a soft number you cannot bet is not an edge.** This file pins
the three-way answer, because the third value is the one a careless
implementation drops.
"""

from __future__ import annotations

import pandas as pd
import pytest

from cbb_betting_lab import line_movement as LM


def board(captured_at: str, quotes):
    """Build a capture frame directly, in the store's own vocabulary."""
    rows = []
    for event_id, market, selection, line, book, odds in quotes:
        rows.append(
            {
                "captured_at": captured_at,
                "slate_date": "2027-01-12",
                "event_id": event_id,
                "commence_time": "2027-01-12T23:00:00Z",
                "home_team": "Duke",
                "away_team": "Kansas",
                "market": market,
                "segment": "full_game",
                "player": "",
                "selection": selection,
                "line": line,
                "book": book,
                "american_odds": odds,
            }
        )
    return pd.DataFrame(rows, columns=list(LM.CAPTURE_COLUMNS))


A = ("e1", "total_points", "over", 142.5, "draftkings", -110.0)
B = ("e1", "total_points", "under", 142.5, "draftkings", -110.0)
C = ("e2", "spread", "home", -3.5, "fanduel", -110.0)


def test_a_quote_still_on_the_board_survived():
    s = LM.survival_between(board("t1", [A]), board("t2", [A]))
    assert (s.survived, s.gone, s.unknown) == (1, 0, 0)
    assert s.survival_rate == 1.0


def test_a_moved_line_is_gone_not_survived():
    """A book that moved a total from 142.5 to 143 has not kept the 142.5.

    The price is part of the quote's identity because the 142.5 is what a
    backtest would have staked, and it is exactly what is no longer available.
    """
    moved = ("e1", "total_points", "over", 143.0, "draftkings", -110.0)
    s = LM.survival_between(board("t1", [A]), board("t2", [moved]))
    assert (s.survived, s.gone, s.unknown) == (0, 1, 0)


def test_a_moved_price_at_the_same_line_is_also_gone():
    repriced = ("e1", "total_points", "over", 142.5, "draftkings", -125.0)
    s = LM.survival_between(board("t1", [A]), board("t2", [repriced]))
    assert (s.survived, s.gone, s.unknown) == (0, 1, 0)


def test_an_event_the_later_capture_never_covered_is_unknown_not_gone():
    """THE CASE THAT MATTERS. A fetch that skipped an event is not a book that
    pulled a price. Scoring it as gone manufactures a reachability finding out
    of a coverage gap — the same failure as reading a starved fetch as an
    unquoted market, one layer down."""
    s = LM.survival_between(board("t1", [A, C]), board("t2", [A]))
    assert (s.survived, s.gone, s.unknown) == (1, 0, 1)
    # And the rate is over the JUDGED quotes only.
    assert s.judged == 1
    assert s.survival_rate == 1.0


def test_a_market_the_later_capture_never_covered_is_unknown():
    """Coverage is judged at (event, market), not at the event alone. An event
    fetched for spreads but not totals says nothing about a total's quote."""
    spread_only = ("e1", "spread", "home", -3.5, "draftkings", -110.0)
    s = LM.survival_between(board("t1", [A]), board("t2", [spread_only]))
    assert (s.survived, s.gone, s.unknown) == (0, 0, 1)
    assert s.survival_rate is None


def test_no_judgeable_quotes_reports_no_rate_rather_than_zero():
    """A rate over an empty denominator is not zero. Reporting it as zero would
    say 'every price vanished' about a capture that simply did not run."""
    s = LM.survival_between(board("t1", [A]), board("t2", []))
    assert s.survival_rate is None
    assert "nothing could be judged" in s.line()


def test_an_empty_earlier_capture_judges_nothing():
    s = LM.survival_between(board("t1", []), board("t2", [A]))
    assert (s.survived, s.gone, s.unknown) == (0, 0, 0)


def test_the_series_pairs_consecutive_captures_in_time_order():
    store = pd.concat(
        [board("t3", [A]), board("t1", [A, B]), board("t2", [A])],
        ignore_index=True,
    )
    series = LM.survival_series(store)
    assert [(s.earlier, s.later) for s in series] == [("t1", "t2"), ("t2", "t3")]
    # B was dropped between t1 and t2, and it was covered, so it is gone.
    assert (series[0].survived, series[0].gone) == (1, 1)


def test_one_capture_can_say_nothing_about_survival():
    assert LM.survival_series(board("t1", [A])) == []
    text = LM.render(board("t1", [A]))
    assert "nothing can be said about survival" in text


def test_an_empty_store_is_not_a_market_with_no_movement():
    text = LM.render(pd.DataFrame(columns=list(LM.CAPTURE_COLUMNS)))
    assert "No capture has run yet" in text
    assert "not a market with no movement" in text


def test_the_store_dedupes_on_the_quote_and_not_the_row(tmp_path):
    """The NHL lab's store deduped on rows including timestamps, so every price
    was written twice; ROI was unchanged and every interval was root-two too
    narrow. A duplicated store does not look wrong — it looks significant."""
    path = tmp_path / "lm.csv"
    LM.append_capture(board("t1", [A, A]), path)
    frame = pd.read_csv(path)
    assert len(frame) == 1, "The same quote in one capture is one row."
    LM.append_capture(board("t1", [A]), path)
    assert len(pd.read_csv(path)) == 1, "Re-appending a capture must be a no-op."
    LM.append_capture(board("t2", [A]), path)
    assert len(pd.read_csv(path)) == 2, "The same quote in a NEW capture is new."


def test_staging_goes_through_the_one_staging_path():
    """A second staging path is a second vocabulary, and two spellings of one
    bet become two keys that never join. The capture store and the card must
    agree about what a row is, or survival is measured against something the
    card never staked."""
    source = (LM.__file__).replace(".pyc", ".py")
    text = open(source, encoding="utf-8").read()
    assert "staging.stage_payloads" in text
    for invented in ("for book in event", "bookmakers) or ()"):
        assert invented not in text, (
            "line_movement re-implements the staging loop. It must call "
            "providers.staging.stage_payloads instead."
        )
