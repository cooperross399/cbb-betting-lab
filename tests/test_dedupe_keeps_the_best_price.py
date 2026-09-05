"""Two rows under one quote identity at two prices keep the better price.

A book's main line and its alternate ladder at the same point are one quote
seen twice. `keep="first"` held whichever was parsed first — the worse price on
189 of 504,394 props quotes in the 2024 segment. The survivor is now the best
price, and row order is otherwise untouched.
"""
import pandas as pd

from cbb_betting_lab import stores


def _row(**kw):
    base = dict(event_id="e1", market="player_points", segment="game", player="A Player",
                selection="over", line=12.5, book="draftkings", snapshot_phase="card",
                american_odds=-110)
    base.update(kw)
    return base


def test_the_better_price_survives_whichever_came_first():
    for odds in ([-120, -105], [-105, -120], [110, 105], [105, 110]):
        out = stores.dedupe_prices(pd.DataFrame([_row(american_odds=o) for o in odds]))
        assert len(out) == 1
        assert out.loc[0, "american_odds"] == max(odds, key=stores._decimal_payout)


def test_distinct_quotes_keep_their_order():
    frame = pd.DataFrame([
        _row(american_odds=-110),
        _row(selection="under", american_odds=-105),
        _row(book="fanduel", american_odds=100),
    ])
    out = stores.dedupe_prices(frame)
    assert out["book"].tolist() == ["draftkings", "draftkings", "fanduel"]
    assert out["selection"].tolist() == ["over", "under", "over"]


def test_equal_prices_collapse_to_one_row():
    assert len(stores.dedupe_prices(pd.DataFrame([_row(), _row()]))) == 1


def test_a_frame_without_odds_still_dedupes_on_identity():
    frame = pd.DataFrame([_row(), _row()]).drop(columns="american_odds")
    assert len(stores.dedupe_prices(frame)) == 1
