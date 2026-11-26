"""Decision 116: stricter edge bars on the card, which only ever rise."""

from __future__ import annotations

import math

from cbb_betting_lab.models import card_bars as CB
from cbb_betting_lab.reports import card_pricing as CP
from cbb_betting_lab.reports.card_pricing import Quote, Wager, select


def _wager(market="moneyline", selection="home", line=None, odds=(150,), segment="game",
           home="Iowa State Cyclones", away="Memphis Tigers"):
    return Wager(
        key=(home, away, market, segment, selection, line), event_id="e1", slate_date="2026-11-20",
        commence_time="2026-11-21T00:00:00Z", home_team=home, away_team=away, market=market,
        segment=segment, player="", selection=selection, line=line, tier="high_major",
        quotes=tuple(Quote(book=f"b{i}", american_odds=float(o)) for i, o in enumerate(odds)),
    )


def _pick(wager, probability, bars):
    result = select(
        [wager], {wager.key: probability}, approved=lambda m: True,
        tip_state_for=lambda w: CP.TipState.UPCOMING, threshold=CP.EDGE_THRESHOLD, bars=bars,
    )
    return result.selections


MORNING_ROWS = [
    {"slate_date": "2026-11-20", "card_slot": "morning", "home_team": "Iowa State Cyclones",
     "away_team": "Memphis Tigers", "market": "spread", "segment": "game", "selection": "home",
     "line": "-3.5", "bet_down_to": "-115"},
    {"slate_date": "2026-11-19", "card_slot": "morning", "home_team": "Duke Blue Devils",
     "away_team": "Army Black Knights", "market": "moneyline", "segment": "game", "selection": "home",
     "line": "", "bet_down_to": ""},
]


def test_the_bars_only_rise():
    bars = CB.Bars(base=0.02, card_slot="morning")
    for market in ("moneyline", "spread", "alternate_spread", "team_total", "alternate_team_total"):
        for price in (-400, -150, -110, 120, 500):
            assert bars.threshold(_wager(market=market), price) >= 0.02


def test_high_hold_markets_need_five_percent_and_halves_do_not():
    bars = CB.Bars(base=0.02, card_slot="morning")
    assert bars.threshold(_wager(market="alternate_spread", line=-7.5), 150) == CB.HIGH_HOLD_EDGE
    assert bars.threshold(_wager(market="team_total", selection="home_over", line=70.5), -110) == CB.HIGH_HOLD_EDGE
    assert bars.threshold(_wager(market="moneyline"), 150) == 0.02
    assert bars.threshold(_wager(market="team_total", segment="h1", line=35.5), -110) == 0.02
    # At p = 0.42 and +150 the edge is 5.0%: clears the 2% bar, not the 5% one.
    alt = _wager(market="alternate_spread", line=-7.5, odds=(150,))
    assert _pick(alt, 0.42, CB.Bars(base=0.02, on=False))
    assert _pick(alt, 0.419, CB.Bars(base=0.02, card_slot="morning")) == []


def test_the_heavy_favourite_bar_is_off_since_decision_120():
    bars = CB.Bars(base=0.02, card_slot="morning")
    fav = _wager(odds=(-200,))
    assert CB.HEAVY_FAVOURITE_ON is False
    assert bars.threshold(fav, -200) == 0.02
    # p = 0.69 at -200 is a 3.5% edge: a pick again.
    picked = _pick(fav, 0.69, bars)
    assert picked
    assert CP.expected_value(0.69, picked[0]["bet_down_to"]) >= 0.02


def test_long_alternate_spreads_need_seven_percent():
    bars = CB.Bars(base=0.02, card_slot="morning")
    alt = _wager(market="alternate_spread", line=-12.5, odds=(250,))
    assert bars.threshold(alt, 250) == CB.LONG_ALT_EDGE
    assert bars.threshold(alt, 199) == CB.HIGH_HOLD_EDGE
    assert bars.threshold(_wager(market="alternate_spread", segment="h1", line=-6.5), 250) == 0.02
    # p = 0.31 at +250 is an 8.5% edge; p = 0.30 is 5%.
    assert _pick(alt, 0.31, bars)
    assert _pick(alt, 0.30, bars) == []
    number = _pick(alt, 0.31, bars)[0]["bet_down_to"]
    assert number >= CB.LONG_ALT_ODDS
    assert CP.expected_value(0.31, number) >= CB.LONG_ALT_EDGE - 1e-9


def test_a_game_keeps_the_believable_side_and_moneylines_lead():
    bars = CB.Bars(base=0.02, card_slot="morning")
    # A 14% claim on an alternate ladder and a 6% moneyline on the same game:
    # 0.08 + 0.25 * 0.06 = 9.5% against 6% + 2%, so the ladder still leads...
    assert bars.rank_edge(_wager(market="alternate_spread"), 0.14) == 0.08 + 0.25 * 0.06
    assert bars.rank_edge(_wager(market="moneyline"), 0.06) == 0.06 + CB.MONEYLINE_RANK_BONUS
    # ...but a 12% ladder claim (9%) loses to a 7.5% moneyline (9.5%).
    ladder = _wager(market="alternate_spread", line=-7.5, odds=(200,))
    ml = _wager(market="moneyline", odds=(150,))
    probabilities = {ladder.key: (1 + 0.12) / 3.0, ml.key: (1 + 0.075) / 2.5}
    result = select([ladder, ml], probabilities, approved=lambda m: True,
                    tip_state_for=lambda w: CP.TipState.UPCOMING, threshold=CP.EDGE_THRESHOLD, bars=bars)
    assert [r["market"] for r in result.selections] == ["moneyline"]
    # Without bars the claimed edge alone decides, as before.
    result = select([ladder, ml], probabilities, approved=lambda m: True,
                    tip_state_for=lambda w: CP.TipState.UPCOMING, threshold=CP.EDGE_THRESHOLD)
    assert [r["market"] for r in result.selections] == ["alternate_spread"]


def test_the_evening_card_bets_new_games_at_half_size():
    morning = CB.Morning.from_rows(MORNING_ROWS, day="2026-11-20")
    evening = CB.Bars(base=0.02, card_slot="evening", morning=morning)
    assert evening.size_scale({"home_team": "Iowa State Cyclones", "away_team": "Memphis Tigers"}) == 1.0
    assert evening.size_scale({"home_team": "X", "away_team": "Y"}) == CB.EVENING_NEW_GAME_SIZE
    assert CB.Bars(base=0.02, card_slot="morning", morning=morning).size_scale({"home_team": "X", "away_team": "Y"}) == 1.0


def test_the_evening_card_reads_the_morning():
    morning = CB.Morning.from_rows(MORNING_ROWS, day="2026-11-20")
    assert morning.games == {("Iowa State Cyclones", "Memphis Tigers")}
    evening = CB.Bars(base=0.02, card_slot="evening", morning=morning)
    # A game the morning card picked keeps the card's bar on a new side.
    assert evening.threshold(_wager(market="moneyline"), 150) == 0.02
    # A game it did not pick needs 4%.
    other = _wager(home="Duke Blue Devils", away="Army Black Knights")
    assert evening.threshold(other, 150) == CB.EVENING_NEW_GAME_EDGE
    # The morning's own side is re-listed only at or above its bet-down-to.
    side = _wager(market="spread", line=-3.5, odds=(-110,))
    assert evening.threshold(side, -110) == 0.02
    assert math.isinf(evening.threshold(side, -120))
    assert evening.bet_down_to(0.60, side, price_band=CP.PRICE_BAND) == -115
    # The morning card itself reads none of this.
    assert CB.Bars(base=0.02, card_slot="morning", morning=morning).threshold(other, 150) == 0.02


def test_without_a_record_of_morning_picks_no_morning_bar_applies():
    evening = CB.Bars(base=0.02, card_slot="evening", morning=None)
    assert evening.threshold(_wager(home="Duke Blue Devils", away="Army Black Knights"), 150) == 0.02


def test_off_is_the_old_card():
    off = CB.Bars(base=0.02, card_slot="evening", morning=CB.Morning.from_rows(MORNING_ROWS, day="2026-11-20"), on=False)
    for wager, price in ((_wager(market="alternate_spread", line=-7.5), 150), (_wager(odds=(-300,)), -300),
                         (_wager(home="X", away="Y"), 150)):
        assert off.threshold(wager, price) == 0.02
