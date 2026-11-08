"""Nothing far down an alternate ladder (decision 86)."""

from __future__ import annotations

from pathlib import Path

from cbb_betting_lab.models import rung_cap
from cbb_betting_lab.reports.card_pricing import Quote, Wager


def _w(market, selection, line, books=3, event="e1", segment="game"):
    return Wager(
        key=(event, market, selection, line, segment),
        event_id=event, slate_date="2026-11-10", commence_time="2026-11-10T23:00:00Z",
        home_team="Home", away_team="Away", market=market, segment=segment,
        player="", selection=selection, line=line, tier="mid_major",
        quotes=tuple(Quote(f"b{i}", -110) for i in range(books)),
    )


def test_the_main_line_is_the_one_most_books_quote():
    wagers = [_w("spread", "home", -4.5, books=5), _w("spread", "away", 4.5, books=5),
              _w("spread", "home", -5.0, books=1)]
    assert rung_cap.main_lines(wagers)[("e1", "spread")] == -4.5


def test_a_rung_past_the_cap_is_withdrawn_and_one_inside_is_kept():
    main = [_w("spread", "home", -4.5, books=6), _w("spread", "away", 4.5, books=6),
            _w("total_points", "over", 150.5, books=6)]
    inside = [_w("alternate_spread", "home", -12.5), _w("alternate_spread", "away", 3.5),
              _w("alternate_total_points", "under", 158.5)]
    outside = [_w("alternate_spread", "home", -13.5), _w("alternate_spread", "away", -5.5),
               _w("alternate_total_points", "over", 159.0)]
    wagers = main + inside + outside
    out, removed = rung_cap.apply({w.key: 0.5 for w in wagers}, wagers)
    assert removed == len(outside)
    assert set(out) == {w.key for w in main + inside}


def test_a_ladder_with_no_main_line_on_the_board_is_kept():
    rung = _w("alternate_spread", "home", -20.5)
    assert rung_cap.apply({rung.key: 0.5}, [rung]) == ({rung.key: 0.5}, 0)


def test_halves_and_main_markets_are_never_capped():
    wagers = [_w("spread", "home", -4.5, books=6), _w("spread", "home", -30.5, books=1),
              _w("spread_h1", "home", -20.5, segment="h1")]
    out, removed = rung_cap.apply({w.key: 0.5 for w in wagers}, wagers)
    assert removed == 0 and len(out) == 3


def test_the_card_caps_after_the_closing_gate_and_before_select():
    source = (Path(__file__).resolve().parents[1] / "src/cbb_betting_lab/reports/gameday_card.py").read_text()
    at = source.index("rung_cap.apply(trusted, wagers)")
    assert source.index("closing_gate.apply(trusted, wagers, gate)") < at < source.index("result = select(")
