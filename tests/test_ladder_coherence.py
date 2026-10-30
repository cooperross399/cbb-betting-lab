"""A book's ladder against itself (`ladder_coherence`)."""

from cbb_betting_lab.ladder_coherence import dominated_quotes, summary_lines
from cbb_betting_lab.reports.card_pricing import Quote, Wager


def _w(selection, line, quotes, market="alternate_spread", player=""):
    return Wager(
        key=("e", market, selection, line), event_id="e", slate_date="2026-11-10",
        commence_time="", home_team="Home", away_team="Away", market=market,
        segment="full_game", player=player, selection=selection, line=line,
        tier="mid_major", quotes=tuple(Quote(b, o) for b, o in quotes.items()),
    )


def test_a_better_line_at_a_better_price_dominates_on_the_same_book():
    found = dominated_quotes([
        _w("home", -6.5, {"a": -110}),
        _w("home", -5.5, {"a": -105}, market="spread"),
    ])
    assert len(found) == 1
    assert (found[0].line, found[0].better_line, found[0].book) == (-6.5, -5.5, "a")


def test_an_ordered_ladder_and_another_books_price_are_not_contradictions():
    assert dominated_quotes([
        _w("home", -6.5, {"a": +105, "b": -120}),
        _w("home", -5.5, {"a": -110}),
    ]) == []


def test_totals_read_in_the_bettors_direction():
    over = dominated_quotes([_w("over", 141.5, {"a": -110}, "alternate_total_points"),
                             _w("over", 140.5, {"a": -108}, "alternate_total_points")])
    under = dominated_quotes([_w("under", 140.5, {"a": -110}, "alternate_total_points"),
                              _w("under", 141.5, {"a": -108}, "alternate_total_points")])
    assert [d.line for d in over] == [141.5]
    assert [d.line for d in under] == [140.5]


def test_rounding_and_players_and_moneylines_are_never_read():
    assert dominated_quotes([_w("home", -6.5, {"a": -110}), _w("home", -5.5, {"a": -109.8})]) == []
    assert dominated_quotes([_w("over", 20.5, {"a": -110}, "player_points", "P"),
                             _w("over", 19.5, {"a": -105}, "player_points", "P")]) == []
    assert dominated_quotes([_w("home", None, {"a": -110}, "moneyline")]) == []


def test_the_card_lines_say_what_was_checked():
    assert "no ladder was checked" in summary_lines([], ladders_read=False)[0]
    assert "contradicted" in summary_lines([], ladders_read=True)[0]
    found = dominated_quotes([_w("home", -6.5, {"a": -110}), _w("home", -5.5, {"a": -105})])
    text = "\n".join(summary_lines(found, ladders_read=True))
    assert "never an edge or a selection" in text and "-6.5 at -110 is beaten by -5.5 at -105" in text
