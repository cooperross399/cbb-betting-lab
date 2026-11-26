"""Decision 122: the sharp book sets the fair price and is never a price the card takes."""

from __future__ import annotations

from cbb_betting_lab.models import trust as T
from cbb_betting_lab.providers import odds_api
from cbb_betting_lab.reports.card_pricing import Quote, Wager


def _w(selection, prices, books=("dk", "fd", "mgm")):
    return Wager(
        key=("h", "a", "moneyline", "game", selection, None), event_id="e", slate_date="2026-11-27",
        commence_time="2026-11-28T00:00:00Z", home_team="h", away_team="a", market="moneyline",
        segment="game", player="", selection=selection, line=None, tier="high_major",
        quotes=tuple(Quote(book=b, american_odds=float(p)) for b, p in zip(books, prices)),
    )


def test_the_reference_overrides_the_median_where_it_quotes():
    us = [_w("home", (-150, -150, -150)), _w("away", (130, 130, 130))]
    ref = [_w("home", (-170,), books=("pinnacle",)), _w("away", (155,), books=("pinnacle",))]
    reference = T.reference_probabilities(ref)
    median = T.market_probabilities(us)
    sharp = T.market_probabilities(us, reference=reference)
    assert sharp[us[0].key] == reference[us[0].key]
    assert sharp[us[0].key] > median[us[0].key]
    assert abs(sharp[us[0].key] + sharp[us[1].key] - 1.0) < 1e-9


def test_no_reference_is_the_old_fair_price_and_off_switch_restores_it(monkeypatch):
    us = [_w("home", (-150, -150, -150)), _w("away", (130, 130, 130))]
    assert T.market_probabilities(us, reference={}) == T.market_probabilities(us)
    ref = T.reference_probabilities([_w("home", (-170,), books=("pinnacle",)), _w("away", (155,), books=("pinnacle",))])
    monkeypatch.setattr(T, "REFERENCE_ON", False)
    assert T.market_probabilities(us, reference=ref) == T.market_probabilities(us)


def test_the_us_regions_are_unchanged():
    assert odds_api.DEFAULT_REGIONS == "us,us2"
    assert odds_api.REFERENCE_BOOKMAKERS == "pinnacle"
