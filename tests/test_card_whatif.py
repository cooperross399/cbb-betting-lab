"""The what-if replay (Cooper, 2026-11-26, "all 3"): each card rule switched one at a time."""

from __future__ import annotations

import pandas as pd

from cbb_betting_lab.models import card_bars as CB
from cbb_betting_lab.reports import card_pricing as CP
from cbb_betting_lab.reports import card_whatif as W
from cbb_betting_lab.reports.card_pricing import Quote, Wager, select


def _row(event, market, selection, price, edge, *, line="", slot="morning", tier="high_major",
         home="Iowa State Cyclones", away="Memphis Tigers", day="2026-11-27"):
    payout = price / 100.0 if price > 0 else 100.0 / -price
    return {
        "slate_date": day, "card_slot": slot, "event_id": event, "commence_time": f"{day}T23:00:00Z",
        "home_team": home, "away_team": away, "market": market, "segment": "game", "player": "",
        "selection": selection, "line": line, "tier": tier, "american_odds": str(price), "book": "b",
        "probability": str((1 + edge) / (1 + payout)), "edge": str(edge),
    }


def test_select_keeps_every_candidate_that_cleared_the_flat_bar():
    alt = Wager(
        key=("h", "a", "alternate_spread", "game", "home", -12.5), event_id="e1", slate_date="2026-11-27",
        commence_time="2026-11-28T00:00:00Z", home_team="h", away_team="a", market="alternate_spread",
        segment="game", player="", selection="home", line=-12.5, tier="high_major",
        quotes=(Quote(book="b", american_odds=250.0),),
    )
    # p = 0.30 at +250 is a 5% edge: clears the flat bar, not the 7% long-alt bar.
    result = select([alt], {alt.key: 0.30}, approved=lambda m: True,
                    tip_state_for=lambda w: CP.TipState.UPCOMING, threshold=CP.EDGE_THRESHOLD,
                    bars=CB.Bars(base=CP.EDGE_THRESHOLD, card_slot="morning"))
    assert result.selections == []
    assert [c["market"] for c in result.candidates] == ["alternate_spread"]
    assert abs(result.candidates[0]["edge"] - 0.05) < 1e-9


def test_switching_one_rule_changes_only_what_that_rule_touches():
    candidates = W.frame([
        _row("e1", "alternate_spread", "home", 250, 0.05, line="-12.5"),
        _row("e2", "moneyline", "away", -120, 0.03, home="Duke Blue Devils", away="Army Black Knights"),
    ])
    today = W.replay(candidates, CB.default_rules())
    assert list(today["event_id"]) == ["e2"]
    without = W.replay(candidates, CB.default_rules() - {"long_alt"})
    assert sorted(without["event_id"]) == ["e1", "e2"]
    outcomes = {tuple(str(r[c]) for c in W.IDENTITY): "won" for r in candidates.to_dict("records")}
    result = W.build(candidates, outcomes)
    long_alt = next(v for v in result["variants"] if v["key"] == "long_alt")
    # The rung at +250 is sized 0.6u on the ladder and would have won 1.5u.
    assert abs(long_alt["delta"]["high_major"] - 1.5) < 1e-9
    assert "Without: 7% bar" in W.render(result)


def test_the_evening_card_reads_the_replayed_morning_and_is_sized_down():
    candidates = W.frame([
        _row("e1", "moneyline", "home", 150, 0.03),
        _row("e2", "moneyline", "home", 150, 0.05, slot="evening", home="X", away="Y"),
    ])
    picks = W.replay(candidates, CB.default_rules())
    evening = picks[picks["card_slot"] == "evening"]
    assert list(evening["units"]) == [CB.EVENING_NEW_GAME_SIZE]
    full = W.replay(candidates, CB.default_rules() - {"evening_size"})
    assert list(full[full["card_slot"] == "evening"]["units"]) == [1.0]


def test_a_rerun_of_a_slot_replaces_its_candidates():
    first = W.append(W.frame([]), [_row("e1", "moneyline", "home", 150, 0.03)], slate_date="2026-11-27", card_slot="morning")
    again = W.append(first, [_row("e2", "moneyline", "home", 150, 0.03)], slate_date="2026-11-27", card_slot="morning")
    assert list(again["event_id"]) == ["e2"]
    evening = W.append(again, [_row("e3", "moneyline", "home", 150, 0.03)], slate_date="2026-11-27", card_slot="evening")
    assert sorted(evening["event_id"]) == ["e2", "e3"]


def test_profit_and_an_empty_file():
    assert W.profit("won", -150, 1.0) == 1.0
    assert W.profit("lost", -150, 1.0) == -1.5
    assert W.profit("lost", 250, 0.6) == -0.6
    assert W.profit("pending", 150, 1.0) is None
    assert "No candidates are on file yet" in W.render(W.build(W.frame([]), {}))
