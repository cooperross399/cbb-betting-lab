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


def test_heavy_favourites_need_four_percent_and_bet_down_to_says_so():
    bars = CB.Bars(base=0.02, card_slot="morning")
    fav = _wager(odds=(-200,))
    assert bars.threshold(fav, -200) == CB.HEAVY_FAVOURITE_EDGE
    assert bars.threshold(fav, -149) == 0.02
    # p = 0.69 at -200 is a 3.5% edge: a pick under the old bar, none now.
    assert _pick(fav, 0.69, CB.Bars(base=0.02, on=False))
    assert _pick(fav, 0.69, bars) == []
    picked = _pick(fav, 0.70, bars)
    assert picked and picked[0]["bet_down_to"] <= -150
    number = picked[0]["bet_down_to"]
    assert CP.expected_value(0.70, number) >= CB.HEAVY_FAVOURITE_EDGE
    # A price just inside the line clears at 2%, so the number stops at -149.
    near = CB.Bars(base=0.02, card_slot="morning").bet_down_to(0.62, fav, price_band=CP.PRICE_BAND)
    assert near == -149


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
