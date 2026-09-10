"""Forward evidence cannot be back-dated, so every guard here protects a night.

The asymmetry this whole module exists for: a historical price can be bought in
March, and a night that was not frozen is gone. In this sport a night is up to
**200 games** (the opening Monday of 2022-23), and there are 147 slate days in a
season. Every test below is named after the specific way a night could be lost
or corrupted:

* a later run re-pricing an opinion frozen that morning, so the ledger becomes a
  record of hindsight wearing a timestamp;
* a moneyline's blank line reading back from CSV as NaN, so the same opinion
  keys two different ways and gets frozen twice — the fifth member of the NHL
  lab's join-vocabulary bug family, in a new costume;
* a zero-row night re-settling forever because it left no ledger trace;
* an append silently compacting a ledger whose prices are gone;
* a headline reading "positive" over a replicated loss, which is exactly what
  the NHL lab shipped at −6.6%.

`settlement.py` used to be imported through `importorskip` while it was being
written in parallel. It has landed, and a skip that fires when a module fails
to import is a pass over a broken integration — so it is a plain import now.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

import json
import pandas as pd
from pathlib import Path
import pytest

import cbb_betting_lab.settlement  # noqa: E402,F401  (an ImportError here is a failure, never a skip)

from cbb_betting_lab import forward_evidence as fe  # noqa: E402
from cbb_betting_lab import stats, stores  # noqa: E402
from cbb_betting_lab.competitions import CBB  # noqa: E402
from cbb_betting_lab.conferences import Tier  # noqa: E402
from cbb_betting_lab.providers.team_names import TeamIndex  # noqa: E402
from cbb_betting_lab.selection import FULL_GAME, selection_key  # noqa: E402
from cbb_betting_lab.settlement import Outcome  # noqa: E402


NOW = datetime(2027, 1, 20, 12, 0, tzinfo=timezone.utc)


@pytest.fixture
def census_receipt(tmp_path):
    """A wager-census receipt for this process, dropped again afterwards.

    `render_ledger` and `report_payload` are declared grading entry points as
    of 2026-09-06 — the Opinions table prints ROI, a 95% interval, a
    family-corrected interval and a Verdict per market and per tier over every
    settled row, player props included, and neither function was named in
    `player_census.GRADING_ENTRY_POINTS` nor called the guard. Both now refuse
    a ledger carrying a player market until design section 10's census has
    reconciled in this process.

    The receipt is process-global, so this fixture clears it on both sides: a
    leak forward would make the gate look shut in a file that never ran it, and
    a leak backward would let a test that means to see the refusal see a pass.
    """
    from conftest import reconcile_a_fixture_census

    from cbb_betting_lab.models import player_census

    player_census.forget_reconciliations()
    try:
        yield reconcile_a_fixture_census(tmp_path)
    finally:
        player_census.forget_reconciliations()



def key_for(row):
    """The injected key. One callable, so the map and the snapshot cannot drift."""
    return selection_key(
        row,
        market=row.market,
        selection=row.selection,
        line=row.line,
        competition=CBB,
        segment=row.segment,
    )


# --------------------------------------------------------------------------
# Fixtures: one January night, two games, one of them with a player prop.
# --------------------------------------------------------------------------

#: 18:00 Eastern on 2027-01-12, which is the slate day the join must land on.
TIP = "2027-01-12T23:00:00Z"
DAY = "2027-01-12"


def price(
    *,
    event_id="e1",
    home="Purdue",
    away="Butler",
    market="moneyline",
    selection="home",
    line=None,
    odds=-110,
    book="dk",
    player="",
    commence_time=TIP,
    segment=FULL_GAME,
):
    return {
        "event_id": event_id,
        "commence_time": commence_time,
        "home_team": home,
        "away_team": away,
        "market": market,
        "segment": segment,
        "player": player,
        "selection": selection,
        "line": line,
        "american_odds": odds,
        "book": book,
    }


def team_games() -> pd.DataFrame:
    """Two games on 2027-01-12: Purdue beat Butler 80-70, Duke beat UNC 61-60."""
    rows = []
    for game_id, home, away, home_score, away_score in (
        (1, 10, 20, 80, 70),
        (2, 30, 40, 61, 60),
    ):
        for team, opponent, score, against, side in (
            (home, away, home_score, away_score, "home"),
            (away, home, away_score, home_score, "away"),
        ):
            rows.append(
                {
                    "game_id": game_id,
                    "season": 2027,
                    "slate_date": DAY,
                    "team_id": team,
                    "opponent_id": opponent,
                    "home_away": side,
                    "team_score": score,
                    "opponent_score": against,
                    "margin": score - against,
                    "total": home_score + away_score,
                    "team_score_h1": score // 2,
                    "opponent_score_h1": against // 2,
                    "periods": 2,
                    "overtime": False,
                }
            )
    return pd.DataFrame(rows)


def player_games() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": 1,
                "athlete_id": 111,
                "athlete_display_name": "Zach Edey",
                "team_id": 10,
                "opponent_id": 20,
                "did_not_play": False,
                "points": 24.0,
                "rebounds": 12.0,
                "assists": 2.0,
            },
            {
                "game_id": 1,
                "athlete_id": 222,
                "athlete_display_name": "Braden Smith",
                "team_id": 10,
                "opponent_id": 20,
                "did_not_play": False,
                "points": 9.0,
                "rebounds": 3.0,
                "assists": 11.0,
            },
        ]
    )


def game_segments() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": 1,
                "periods": 2,
                "overtime": False,
                "home_score_h1": 40,
                "away_score_h1": 35,
                "first_basket_athlete_id": 111.0,
                "first_basket_team_id": 10.0,
            },
            {
                "game_id": 2,
                "periods": 2,
                "overtime": False,
                "home_score_h1": 30,
                "away_score_h1": 31,
                "first_basket_athlete_id": None,
                "first_basket_team_id": None,
            },
        ]
    )


def team_index() -> TeamIndex:
    index = TeamIndex()
    index.add(10, "Purdue")
    index.add(20, "Butler")
    index.add(30, "Duke")
    index.add(40, "North Carolina")
    return index


def freeze(tmp_path, rows, probabilities=None, day=DAY, **kwargs):
    return fe.write_snapshot(
        pd.DataFrame(rows),
        probabilities or {},
        key_for=key_for,
        verdicts_in_force=["calibration_correction"],
        snapshot_date=day,
        archive_dir=tmp_path,
        **kwargs,
    )


def settle(tmp_path, *, now=NOW, players=None):
    return fe.settle_snapshots(
        archive_dir=tmp_path,
        ledger_path=tmp_path / fe.LEDGER_FILENAME,
        team_games=team_games(),
        player_games=player_games() if players is None else players,
        game_segments=game_segments(),
        team_index=team_index(),
        now=now,
    )


# --------------------------------------------------------------------------
# The first opinion of the day is never retroactively replaced
# --------------------------------------------------------------------------


def test_a_later_run_adds_an_unfrozen_game_and_never_reprices_a_frozen_one(tmp_path):
    """The evening card must reach the evening slate without touching the morning.

    `gates.py` and the brief are both explicit: this sport tips games every
    fifteen minutes for twelve hours, so one freeze a day cannot serve a slate,
    and *"the first opinion of the day for any given game is never retroactively
    replaced."* Both halves have to hold at once or the organ is useless in one
    direction and dishonest in the other.
    """
    noon = price(event_id="e1")
    first = freeze(tmp_path, [noon], {key_for(fe._frozen_row(noon)): 0.60})
    assert first is not None

    evening = price(event_id="e2", home="Duke", away="North Carolina")
    second = freeze(
        tmp_path,
        [noon, evening],
        {
            # The model has moved. It must not be allowed to move the record.
            key_for(fe._frozen_row(noon)): 0.90,
            key_for(fe._frozen_row(evening)): 0.55,
        },
    )
    assert second is not None, "A game the morning run could not price must be addable."

    frame = fe.read_snapshot(second)
    assert len(frame) == 2
    frozen = frame.set_index("event_id")["model_probability"].astype(float)
    assert math.isclose(frozen["e1"], 0.60), (
        "The noon opinion was re-priced by the evening run. That turns the "
        "forward ledger into a record of hindsight wearing a timestamp."
    )
    assert math.isclose(frozen["e2"], 0.55)


def test_a_third_run_with_nothing_new_writes_nothing_at_all(tmp_path):
    """Idempotence at the freeze stage, byte for byte."""
    rows = [price(), price(event_id="e2", home="Duke", away="North Carolina")]
    probabilities = {key_for(fe._frozen_row(r)): 0.6 for r in rows}
    path = freeze(tmp_path, rows, probabilities)
    before = path.read_bytes()

    assert freeze(tmp_path, rows, probabilities) is None
    assert path.read_bytes() == before


def test_a_moneyline_whose_line_is_blank_is_not_refrozen_after_a_csv_round_trip(
    tmp_path,
):
    """An empty cell reads back as NaN, and `NaN is not None`.

    This is the fifth member of the NHL lab's join-vocabulary bug family wearing
    a new costume. A moneyline carries no line; the CSV writes an empty cell;
    `float("nan")` comes back. If the key is rebuilt from the raw cell the
    archived row keys differently from the identical live row, so the morning's
    moneyline looks unfrozen at four o'clock and is frozen a second time — at a
    second price, into an append-only ledger.
    """
    moneyline = price(market="moneyline", line=None)
    freeze(tmp_path, [moneyline], {key_for(fe._frozen_row(moneyline)): 0.6})
    path = fe.snapshot_path(tmp_path, DAY)
    assert pd.isna(fe.read_snapshot(path)["line"].iloc[0]), "A blank line must stay blank."

    assert freeze(tmp_path, [moneyline], {}) is None
    assert len(fe.read_snapshot(path)) == 1


def test_a_line_of_zero_is_a_pickem_and_is_never_confused_with_no_line(tmp_path):
    """`None` and `0.0` are different bets, so they are different keys."""
    pickem = price(market="spread", selection="home", line=0.0)
    moneyline = price(market="moneyline", selection="home", line=None)
    freeze(tmp_path, [pickem, moneyline], {})
    frame = fe.read_snapshot(fe.snapshot_path(tmp_path, DAY))
    assert len(frame) == 2
    spread_line = frame.loc[frame["market"] == "spread", "line"].iloc[0]
    assert float(spread_line) == 0.0
    assert pd.isna(frame.loc[frame["market"] == "moneyline", "line"].iloc[0])


# --------------------------------------------------------------------------
# The columns that keep a blank and a zero apart
# --------------------------------------------------------------------------


def test_a_market_with_no_calibration_map_gets_a_blank_not_a_copy(tmp_path):
    """"No map" and "calibrates to itself" must not look the same a year later."""
    rows = [
        price(market="moneyline", selection="home"),
        price(market="total_points", selection="over", line=145.5),
    ]
    probabilities = {key_for(fe._frozen_row(r)): 0.60 for r in rows}
    freeze(
        tmp_path,
        rows,
        probabilities,
        calibration={"total_points": lambda p: p},  # an identity map, deliberately
    )
    frame = fe.read_snapshot(fe.snapshot_path(tmp_path, DAY)).set_index("market")
    assert pd.isna(frame.loc["moneyline", "calibrated_probability"]), (
        "A market with no calibration map must be blank. Writing the raw number "
        "there makes an uncalibrated market indistinguishable from one whose map "
        "happens to be the identity, and only one of those is true."
    )
    assert float(frame.loc["total_points", "calibrated_probability"]) == 0.60


def test_a_missing_prior_weight_stays_blank_because_zero_is_a_claim(tmp_path):
    """Zero says none of this price came from the November prior. That is a claim."""
    with_weight = price(event_id="e1")
    without = price(event_id="e2", home="Duke", away="North Carolina")
    freeze(tmp_path, [with_weight, without], {}, prior_weights={"e1": 0.85})
    frame = fe.read_snapshot(fe.snapshot_path(tmp_path, DAY)).set_index("event_id")
    assert float(frame.loc["e1", "prior_weight"]) == 0.85
    assert pd.isna(frame.loc["e2", "prior_weight"])


def test_a_game_with_no_tier_is_unplaced_and_never_blank(tmp_path):
    """The tier must be knowable at settle time, because no pooled D-I headline
    is ever reported and a tier recomputed later is not the tier priced under."""
    rows = [price(event_id="e1"), price(event_id="e2", home="Duke", away="North Carolina")]
    freeze(tmp_path, rows, {}, tiers={"e1": Tier.HIGH_MAJOR})
    frame = fe.read_snapshot(fe.snapshot_path(tmp_path, DAY)).set_index("event_id")
    assert frame.loc["e1", "tier"] == Tier.HIGH_MAJOR.value
    assert frame.loc["e2", "tier"] == Tier.UNPLACED.value


def test_the_verdicts_in_force_are_frozen_with_the_opinion(tmp_path):
    """A ledger row whose model cannot be reconstructed is an anecdote."""
    freeze(tmp_path, [price()], {})
    frame = fe.read_snapshot(fe.snapshot_path(tmp_path, DAY))
    assert frame["verdicts_in_force"].iloc[0] == "calibration_correction"


def test_an_absent_probability_is_no_opinion_and_never_a_probability_of_zero(tmp_path):
    freeze(tmp_path, [price()], {})
    frame = fe.read_snapshot(fe.snapshot_path(tmp_path, DAY))
    assert pd.isna(frame["model_probability"].iloc[0])
    assert pd.isna(frame["edge"].iloc[0])


def test_a_snapshot_cannot_be_filed_under_a_name_nothing_can_parse(tmp_path):
    with pytest.raises(fe.SnapshotDateError):
        freeze(tmp_path, [price()], {}, day="tuesday")


# --------------------------------------------------------------------------
# Settling: idempotence through two independent sources of "done"
# --------------------------------------------------------------------------


def test_a_second_settle_pass_settles_nothing_new(tmp_path):
    """The whole point of the sidecar. A re-run must be a no-op, not a re-append."""
    freeze(tmp_path, [price(), price(event_id="e2", home="Duke", away="North Carolina")], {})
    first = settle(tmp_path)
    assert first.snapshots_settled == 1
    assert first.ledger_rows == 2

    second = settle(tmp_path)
    assert second.snapshots_settled == 0, "A settled snapshot must not settle twice."
    assert second.rows_seen == 0
    assert second.ledger_rows == 2, "The ledger must not grow on a re-run."


def test_a_zero_row_day_marks_itself_settled_and_does_not_resettle_forever(tmp_path):
    """A night that froze nothing leaves no ledger trace, so the marker is the
    only thing that can say it is done.

    This is precisely why idempotence needs two independent sources. The
    ledger's `snapshot_date` set cannot answer for a day that put no rows in it,
    and a day that re-settles forever is a day whose "waiting" count is noise
    for the rest of the season.
    """
    assert freeze(tmp_path, [], {}) is None
    path = fe.snapshot_path(tmp_path, DAY)
    assert path.is_file(), (
        "A run that froze nothing must still leave a record that it ran. "
        "'No opinion tonight' and 'the pipeline did not run tonight' must never "
        "look the same."
    )

    first = settle(tmp_path)
    assert first.snapshots_settled == 1
    assert first.rows_seen == 0
    assert fe.marker_path(path).is_file()

    second = settle(tmp_path)
    assert second.snapshots_settled == 0


def test_the_ledger_alone_can_say_a_day_is_done_when_the_marker_is_lost(tmp_path):
    """The second source, covering for the first. They fail in opposite directions."""
    freeze(tmp_path, [price()], {})
    settle(tmp_path)
    fe.marker_path(fe.snapshot_path(tmp_path, DAY)).unlink()

    again = settle(tmp_path)
    assert again.snapshots_settled == 0, (
        "The ledger already holds this day. Re-settling it would append a "
        "second copy of every opinion into an append-only store."
    )
    assert again.ledger_rows == 1
    assert fe.marker_path(fe.snapshot_path(tmp_path, DAY)).is_file()


def test_the_marker_is_a_sidecar_and_the_snapshot_keeps_its_name(tmp_path):
    """A snapshot's filename is part of the evidence, and evidence is not renamed."""
    freeze(tmp_path, [price()], {})
    settle(tmp_path)
    snapshot = fe.snapshot_path(tmp_path, DAY)
    assert snapshot.is_file() and snapshot.name == f"{DAY}.csv"
    assert fe.marker_path(snapshot).name == f"{DAY}.csv.settled"
    assert fe.snapshot_files(tmp_path) == [snapshot], (
        "A marker must never be picked up as a snapshot."
    )


def test_the_game_index_is_built_once_per_pass_and_not_once_per_row(
    tmp_path, monkeypatch
):
    """A per-row scan of 1,493,589 player-game rows turns a second into an hour.

    A settle step that times out does not fail loudly; it silently stops
    accumulating the only evidence in this lab that cannot be re-bought.
    """
    calls = {"fixtures": 0, "players": 0}
    real_fixtures = fe._build_fixture_index
    real_players = fe._build_player_index

    def counting_fixtures(*args, **kwargs):
        calls["fixtures"] += 1
        return real_fixtures(*args, **kwargs)

    def counting_players(*args, **kwargs):
        calls["players"] += 1
        return real_players(*args, **kwargs)

    monkeypatch.setattr(fe, "_build_fixture_index", counting_fixtures)
    monkeypatch.setattr(fe, "_build_player_index", counting_players)

    rows = [
        price(event_id="e1"),
        price(event_id="e1", market="total_points", selection="over", line=145.5),
        price(event_id="e2", home="Duke", away="North Carolina"),
        price(
            event_id="e1",
            market="player_points",
            selection="over",
            line=18.5,
            player="Zach Edey",
        ),
    ]
    freeze(tmp_path, rows, {})
    freeze(tmp_path, [price(event_id="e2", home="Duke", away="North Carolina")], {}, day="2027-01-13")
    settle(tmp_path)

    assert calls == {"fixtures": 1, "players": 1}, (
        "The index must be built once per pass, over the days the pass needs — "
        f"not per row. Got {calls}."
    )


# --------------------------------------------------------------------------
# Settling: ambiguity always falls on the not-settled side
# --------------------------------------------------------------------------


def test_a_row_with_no_commence_time_is_unsettleable_and_does_not_block_the_night(
    tmp_path,
):
    """A NaN commence time has no slate date, so it has no join key, ever.

    Waiting on it would be waiting on a key that cannot form — and in this sport
    that would hold the other 199 games of the night hostage. It is
    `UNSETTLEABLE` immediately, counted, and stated.
    """
    rows = [price(event_id="e1"), price(event_id="e2", commence_time=float("nan"))]
    freeze(tmp_path, rows, {})
    frame = fe.read_snapshot(fe.snapshot_path(tmp_path, DAY))
    assert frame.loc[frame["event_id"] == "e2", "commence_time"].iloc[0] in ("", None) or pd.isna(
        frame.loc[frame["event_id"] == "e2", "commence_time"].iloc[0]
    ), "A NaN commence time must never round-trip as the literal string 'nan'."

    result = settle(tmp_path)
    assert result.snapshots_settled == 1, "One unkeyable row must not block the night."
    ledger = fe.read_ledger(tmp_path / fe.LEDGER_FILENAME).set_index("event_id")
    assert ledger.loc["e2", "outcome"] == Outcome.UNSETTLEABLE.value
    assert pd.isna(ledger.loc["e2", "profit_units"]), (
        "An unknown outcome has no profit. Zero would be a fabricated number."
    )
    assert ledger.loc["e1", "outcome"] in {Outcome.WON.value, Outcome.LOST.value}


def test_a_game_with_no_result_waits_inside_the_patience_window(tmp_path):
    """hoopR publishes late and restates. Waiting is not a verdict."""
    freeze(
        tmp_path,
        [price(event_id="e9", home="Purdue", away="Butler", commence_time="2027-01-18T23:00:00Z")],
        {},
        day="2027-01-18",
    )
    result = settle(tmp_path, now=NOW)
    assert result.snapshots_waiting == 1
    assert result.snapshots_settled == 0
    assert "2027-01-18" in result.waiting_days
    assert not fe.marker_path(fe.snapshot_path(tmp_path, "2027-01-18")).exists()


def test_a_game_with_no_result_past_the_patience_window_is_unsettleable_never_guessed(
    tmp_path,
):
    freeze(
        tmp_path,
        [price(event_id="e9", commence_time="2027-01-01T23:00:00Z")],
        {},
        day="2027-01-01",
    )
    result = settle(tmp_path, now=NOW)
    assert result.snapshots_settled == 1
    assert result.rows_unsettleable == 1
    assert result.rows_without_a_fixture == 1
    ledger = fe.read_ledger(tmp_path / fe.LEDGER_FILENAME)
    assert ledger["outcome"].iloc[0] == Outcome.UNSETTLEABLE.value


def test_a_day_settles_atomically_so_the_ledger_never_holds_half_a_night(tmp_path):
    """`snapshot_date in ledger` must mean "done", never "partly done"."""
    rows = [
        price(event_id="e1", commence_time="2027-01-18T23:00:00Z"),
        price(
            event_id="e404",
            home="Gonzaga",
            away="Saint Mary's",
            commence_time="2027-01-18T23:00:00Z",
        ),
    ]
    freeze(tmp_path, rows, {}, day="2027-01-18")
    result = settle(tmp_path, now=NOW)
    assert result.snapshots_waiting == 1
    assert result.ledger_rows == 0, (
        "Half a night in the ledger would break the second idempotence source: "
        "the snapshot_date set could then mean either done or partly done."
    )


def test_a_player_named_by_two_athletes_in_one_game_is_ambiguous_never_a_coin_flip(
    tmp_path,
):
    twins = pd.concat(
        [
            player_games(),
            pd.DataFrame(
                [
                    {
                        "game_id": 1,
                        "athlete_id": 333,
                        "athlete_display_name": "Zach Edey",
                        "team_id": 20,
                        "opponent_id": 10,
                        "did_not_play": False,
                        "points": 4.0,
                        "rebounds": 1.0,
                        "assists": 0.0,
                    }
                ]
            ),
        ],
        ignore_index=True,
    )
    freeze(
        tmp_path,
        [price(market="player_points", selection="over", line=18.5, player="Zach Edey")],
        {},
    )
    result = settle(tmp_path, players=twins)
    assert result.rows_ambiguous_player == 1
    assert result.rows_unsettleable == 1
    ledger = fe.read_ledger(tmp_path / fe.LEDGER_FILENAME)
    assert ledger["outcome"].iloc[0] == Outcome.UNSETTLEABLE.value


def test_a_player_absent_from_the_box_score_is_void_because_he_never_entered(tmp_path):
    freeze(
        tmp_path,
        [
            price(
                market="player_points",
                selection="over",
                line=18.5,
                player="Somebody Who Did Not Dress",
            )
        ],
        {},
    )
    result = settle(tmp_path)
    assert result.rows_void == 1
    ledger = fe.read_ledger(tmp_path / fe.LEDGER_FILENAME)
    assert ledger["outcome"].iloc[0] == Outcome.VOID.value


def test_a_player_is_resolved_by_athlete_identity_and_not_by_a_raw_string(tmp_path):
    """Suffixes and accents differ across sources; identity does not."""
    assert fe.normalise_person("Zach Edey Jr.") == fe.normalise_person("zach edey")
    assert fe.normalise_person("Kevin McCullar III") == fe.normalise_person("Kevin McCullar")
    assert fe.normalise_person(float("nan")) == ""
    freeze(
        tmp_path,
        [price(market="player_points", selection="over", line=18.5, player="ZACH  EDEY")],
        {},
    )
    settle(tmp_path)
    ledger = fe.read_ledger(tmp_path / fe.LEDGER_FILENAME)
    assert ledger["outcome"].iloc[0] in {Outcome.WON.value, Outcome.LOST.value}


def test_an_unknown_market_settles_nothing_rather_than_guessing(tmp_path):
    """`markets.py` names every market this lab prices and every one it defers.

    A key in neither arrived from somewhere unaccounted for, and guessing a
    settlement rule for it is how a lab manufactures evidence.
    """
    freeze(tmp_path, [price(market="a_market_nobody_wired")], {})
    result = settle(tmp_path)
    assert result.rows_unsettleable == 1
    assert result.rows_settled == 0
    ledger = fe.read_ledger(tmp_path / fe.LEDGER_FILENAME)
    assert ledger["outcome"].iloc[0] == Outcome.UNSETTLEABLE.value
    assert pd.isna(ledger["profit_units"].iloc[0])


def test_the_away_side_settles_from_the_away_row_and_never_the_home_one(tmp_path):
    """Every quantity in `cbb_team_games.csv` is signed for its own team.

    Purdue beat Butler by ten. Settling the away moneyline from the home row
    reads a margin of +10 for a team that lost by ten — a plausible number, the
    wrong bet, and nothing raises. `settlement` refuses the wrong row rather
    than flipping it, which only helps if this side of the join hands it the
    right one.
    """
    freeze(
        tmp_path,
        [
            price(event_id="e1", selection="home"),
            price(event_id="e1", selection="away", book="fd"),
        ],
        {},
    )
    result = settle(tmp_path)
    assert result.rows_settled == 2, result.summary_line()
    ledger = fe.read_ledger(tmp_path / fe.LEDGER_FILENAME).set_index("selection")
    assert ledger.loc["home", "outcome"] == Outcome.WON.value
    assert ledger.loc["away", "outcome"] == Outcome.LOST.value
    assert float(ledger.loc["home", "actual"]) == 10.0
    assert float(ledger.loc["away", "actual"]) == -10.0


def test_a_team_total_settles_on_the_side_its_selection_names(tmp_path):
    """`home_over` and `away_over` are different bets on different numbers."""
    freeze(
        tmp_path,
        [
            price(market="team_total", selection="home_over", line=75.5),
            price(market="team_total", selection="away_over", line=75.5, book="fd"),
        ],
        {},
    )
    settle(tmp_path)
    ledger = fe.read_ledger(tmp_path / fe.LEDGER_FILENAME).set_index("selection")
    assert ledger.loc["home_over", "outcome"] == Outcome.WON.value  # Purdue 80
    assert ledger.loc["away_over", "outcome"] == Outcome.LOST.value  # Butler 70


def test_a_first_basket_prop_is_settled_from_the_game_segments_row(tmp_path):
    """That market's `game` argument is a segments row, not a team-games row.

    A made free throw is not a basket, which is why the scorer lives in
    `cbb_game_segments` at all — see `tests/test_free_throws_are_not_baskets.py`.
    """
    freeze(
        tmp_path,
        [
            price(
                market="player_first_basket",
                selection="over",
                line=0.5,
                player="Zach Edey",
            ),
            price(
                market="player_first_basket",
                selection="over",
                line=0.5,
                player="Braden Smith",
                book="fd",
            ),
        ],
        {},
    )
    result = settle(tmp_path)
    assert result.rows_settled == 2, result.summary_line()
    ledger = fe.read_ledger(tmp_path / fe.LEDGER_FILENAME).set_index("player")
    assert ledger.loc["Zach Edey", "outcome"] == Outcome.WON.value
    assert ledger.loc["Braden Smith", "outcome"] == Outcome.LOST.value


def test_a_futures_row_is_deferred_and_is_never_called_a_pass_or_an_avoid(tmp_path):
    """A futures market settles on the tournament months later. It is deferred,
    counted, and stated — an excluded market is never a pass, an avoid, or a
    no-value call."""
    freeze(
        tmp_path,
        [price(market="championship_winner", selection="home", odds=+1200)],
        {},
    )
    result = settle(tmp_path)
    assert result.rows_futures_deferred == 1
    line = result.summary_line()
    assert "not a pass, an avoid or a no-value call" in line
    for forbidden in ("no value", "avoid it", "we pass"):
        assert forbidden not in line.casefold()


def test_the_summary_line_makes_an_empty_night_legible(tmp_path):
    result = settle(tmp_path)
    line = result.summary_line()
    assert "0 snapshots found" in line
    assert "gone permanently" in line, (
        "Silence must say what it means. A pass that settles nothing because "
        "nothing was frozen is a pipeline failure, not a quiet night."
    )


def test_the_join_uses_the_slate_date_from_commence_time_not_the_snapshot_name(
    tmp_path,
):
    """The NHL lab discarded 69% of every price it bought to this exact bug.

    A card frozen late on the 11th for a game that tips on the 12th is filed
    under the 11th and must settle against the 12th.
    """
    freeze(tmp_path, [price(commence_time=TIP)], {}, day="2027-01-11")
    result = settle(tmp_path)
    assert result.rows_settled == 1, (
        "The snapshot is named 2027-01-11 and the game is played on 2027-01-12. "
        "Joining on the filename discards it."
    )


# --------------------------------------------------------------------------
# The ledger can only grow
# --------------------------------------------------------------------------


def test_the_append_guard_raises_rather_than_shrinking_a_ledger(tmp_path):
    """A ledger that already holds duplicates must not be silently compacted.

    Deduplication looks harmless and is not: these rows were frozen against
    prices that were quoted for a few minutes on a Tuesday in January and are
    gone. A store that can shrink will, one honest-seeming write at a time.
    """
    path = tmp_path / fe.LEDGER_FILENAME
    duplicated = pd.DataFrame(
        [_ledger_row(event_id="e1", profit=1.0) for _ in range(3)],
        columns=list(fe.LEDGER_COLUMNS),
    )
    duplicated.to_csv(path, index=False, lineterminator="\n")

    with pytest.raises(ValueError, match="append-only"):
        fe.append_ledger(
            pd.DataFrame([_ledger_row(event_id="e2", profit=-1.0)]), path
        )


def test_an_unreadable_ledger_raises_instead_of_being_overwritten_by_a_short_one(
    tmp_path,
):
    """`read_store(..., for_append=True)`, and the reason it exists."""
    path = tmp_path / fe.LEDGER_FILENAME
    path.write_text("a,b,c\n1,2,3\n1,2,3,4,5,6\n", encoding="utf-8")
    with pytest.raises(stores.CorruptStoreError):
        fe.append_ledger(pd.DataFrame([_ledger_row(event_id="e1", profit=1.0)]), path)


def test_appending_the_same_settled_row_twice_keeps_the_row_recorded_first(tmp_path):
    path = tmp_path / fe.LEDGER_FILENAME
    original = _ledger_row(event_id="e1", profit=1.0)
    fe.append_ledger(pd.DataFrame([original]), path)
    fe.append_ledger(pd.DataFrame([{**original, "profit_units": -1.0}]), path)
    ledger = fe.read_ledger(path)
    assert len(ledger) == 1
    assert float(ledger["profit_units"].iloc[0]) == 1.0


def _ledger_row(
    *,
    event_id="e1",
    profit=1.0,
    market="moneyline",
    tier=Tier.HIGH_MAJOR.value,
    outcome=Outcome.WON.value,
    edge=0.05,
    odds=100,
    commence_time=TIP,
    book="dk",
    selection="home",
):
    return {
        "snapshot_date": DAY,
        "commence_time": commence_time,
        "event_id": event_id,
        "home_team": "Purdue",
        "away_team": "Butler",
        "market": market,
        "segment": FULL_GAME,
        "player": "",
        "selection": selection,
        "line": None,
        "american_odds": odds,
        "book": book,
        "model_probability": 0.6,
        "edge": edge,
        "calibrated_probability": None,
        "calibrated_edge": None,
        "prior_weight": None,
        "tier": tier,
        "verdicts_in_force": "",
        "settled_at": "2027-01-13T06:00:00+00:00",
        "outcome": outcome,
        "actual": None,
        "profit_units": profit,
    }


# --------------------------------------------------------------------------
# The report: four guards, and the direction is not decoration
# --------------------------------------------------------------------------


def _ledger(n, *, profit, market="spread", tier=Tier.LOW_MAJOR.value, edge=0.05):
    """`n` settled rows spread over `n // 3` games and three slate days."""
    rows = []
    for i in range(n):
        rows.append(
            _ledger_row(
                event_id=f"g{i // 3}",
                profit=profit(i),
                market=market,
                tier=tier,
                edge=edge,
                outcome=Outcome.WON.value if profit(i) > 0 else Outcome.LOST.value,
                commence_time=f"2027-01-{12 + (i % 3):02d}T23:00:00Z",
            )
        )
    return pd.DataFrame(rows, columns=list(fe.LEDGER_COLUMNS))


def test_an_interval_including_zero_reads_no_demonstrated_edge_in_those_words():
    report = fe.render_ledger(_ledger(300, profit=lambda i: 1.0 if i % 2 else -1.0))
    assert stats.NO_DEMONSTRATED_EDGE in report
    assert f"**{stats.NO_DEMONSTRATED_EDGE}**" in report

    # And no verdict cell is allowed to soften it. The report's closing sentence
    # names these words in order to forbid them, so the check is on the verdicts
    # themselves rather than on the prose around them.
    verdicts = [
        line.rsplit("|", 2)[-2].strip()
        for line in report.splitlines()
        if line.startswith("|") and line.count("|") > 3
    ]
    for verdict in verdicts:
        for banned in ("promising", "trending positive", "small but positive"):
            assert banned not in verdict.casefold(), verdict


def test_a_thin_market_gets_a_phrase_and_never_a_number():
    report = fe.render_ledger(_ledger(30, profit=lambda i: 1.0))
    assert "not enough evidence" in report
    assert "30 bets, below 200" in report


def test_a_replicated_loss_is_reported_as_negative_and_never_as_an_edge():
    """The NHL lab shipped "survived and replicated" over a market at −6.6%.

    Its headline predicate tested measured + survives-correction + replicated
    and never read the sign. The direction is not decoration.
    """
    report = fe.render_ledger(_ledger(400, profit=lambda i: -1.0))
    assert "interval excludes zero, **negative**" in report
    assert "**positive**" not in report


def test_a_replicated_win_is_reported_as_positive():
    report = fe.render_ledger(_ledger(400, profit=lambda i: 1.0))
    assert "interval excludes zero, **positive**" in report
    assert "**negative**" not in report


def test_a_settlement_suspect_is_not_evidence_at_any_sample_size():
    """400 winning bets is not evidence if the settlement rule is unverified.

    The football lab's single largest false finding was a settlement offset it
    could not see, and a constant settlement offset replicates by construction.
    """
    ledger = _ledger(400, profit=lambda i: 1.0, market="spread_h2")
    report = fe.render_ledger(ledger, settlement_suspects=frozenset({"spread_h2"}))
    assert "**not evidence**" in report
    assert "interval excludes zero, **positive**" not in report, (
        "A suspect market was folded into an aggregate and reported as "
        "positive. A number that is not evidence must never be averaged into a "
        "number presented as evidence."
    )
    assert "held out of this roll-up" in report


def test_a_second_half_market_is_footnoted_even_when_nobody_marked_it_suspect():
    """`SECOND_HALF_INCLUDES_OVERTIME` is a book rule, not a fact about the sport."""
    report = fe.render_ledger(_ledger(300, profit=lambda i: 1.0, market="total_points_h2"))
    assert "Settlement ambiguity" in report
    assert "`total_points_h2`" in report
    assert "cannot read a book's rulebook" in report


def test_the_family_correction_comes_from_the_cumulative_count_not_this_table():
    ledger = _ledger(400, profit=lambda i: 1.0 if i % 3 else -1.0)
    uncorrected = fe.render_ledger(ledger)
    corrected = fe.render_ledger(ledger, families=250)
    assert "No experiment-ledger count was supplied" in uncorrected
    assert "250 hypotheses ever tested" in corrected
    assert "narrower than the truth" in uncorrected, (
        "An uncorrected interval that looks corrected is worse than none at all."
    )


def test_no_pooled_division_one_headline_is_reported():
    """Cooper's rule: high-major, mid-major and low-major are different
    distributions and are never collapsed into one lead number."""
    ledger = pd.concat(
        [
            _ledger(300, profit=lambda i: 1.0, tier=Tier.HIGH_MAJOR.value),
            _ledger(300, profit=lambda i: -1.0, tier=Tier.LOW_MAJOR.value),
        ],
        ignore_index=True,
    )
    report = fe.render_ledger(ledger)
    assert "No figure pooled across the whole of Division I appears here." in report
    payload = fe.report_payload(ledger)
    assert payload["no_pooled_division_one_headline"] is True
    assert {row["tier"] for row in payload["rows"]} == {
        Tier.HIGH_MAJOR.value,
        Tier.LOW_MAJOR.value,
    }
    assert all("tier" in row and row["tier"] for row in payload["rows"])


def test_opinions_and_bets_are_reported_separately():
    """Mixing them flatters whichever is worse."""
    ledger = pd.concat(
        [
            _ledger(300, profit=lambda i: 1.0, edge=0.09),
            _ledger(300, profit=lambda i: -1.0, edge=-0.04),
        ],
        ignore_index=True,
    )
    report = fe.render_ledger(ledger)
    assert "## Opinions, per market and per tier" in report
    assert "## Bets, per market and per tier" in report
    payload = fe.report_payload(ledger)
    cuts = {row["cut"] for row in payload["rows"]}
    assert cuts == {"opinions", "bets"}
    opinions = sum(r["bets"] for r in payload["rows"] if r["cut"] == "opinions")
    wagers = sum(r["bets"] for r in payload["rows"] if r["cut"] == "bets")
    assert opinions == 600 and wagers == 300


def test_a_player_prop_is_an_opinion_and_never_a_bet_and_never_called_a_pass(
    census_receipt,
):
    """Nothing in this sport reaches `Availability.CONFIRMED`.

    A prop is priced, frozen and settled and cannot produce a selection, so it
    can never be counted as a bet — and the report must say that in the gate's
    own words rather than describing it as a pass, an avoid or a no-value call.

    Takes `census_receipt` because `render_ledger` is a declared grading entry
    point as of 2026-09-06 and refuses a player ledger with no receipt. The
    refusal is asserted next door; this test is about what the report says once
    the gate has been satisfied, which is the run an operator actually makes.
    """
    ledger = _ledger(300, profit=lambda i: 1.0, market="player_points", edge=0.20)
    report = fe.render_ledger(ledger)
    assert "cannot produce a\nselection" in report or "cannot produce a selection" in report
    assert "not a pass, an\navoid, or a no-value call" in report or (
        "not a pass, an avoid, or a no-value call" in report
    )
    payload = fe.report_payload(ledger)
    assert not [r for r in payload["rows"] if r["cut"] == "bets"], (
        "A player prop cleared the edge threshold and was counted as a bet. "
        "There is no feed in this sport that would make that bet real."
    )


def test_futures_are_reported_apart_with_hold_time_and_never_in_a_game_headline():
    futures = _ledger(4, profit=lambda i: -1.0, market="championship_winner")
    futures["settled_at"] = "2027-04-06T06:00:00+00:00"
    games = _ledger(300, profit=lambda i: 1.0)
    report = fe.render_ledger(pd.concat([futures, games], ignore_index=True))
    assert "## Futures" in report
    assert "median hold **84 days**" in report
    assert "never folded into one" in report
    payload = fe.report_payload(pd.concat([futures, games], ignore_index=True))
    assert "championship_winner" not in {row["market"] for row in payload["rows"]}


def test_unsettleable_and_void_rows_never_enter_an_interval_as_zeros():
    settled = _ledger(300, profit=lambda i: 1.0)
    junk = pd.DataFrame(
        [
            _ledger_row(event_id=f"x{i}", profit=None, outcome=Outcome.UNSETTLEABLE.value)
            for i in range(50)
        ]
        + [
            _ledger_row(event_id=f"v{i}", profit=0.0, outcome=Outcome.VOID.value)
            for i in range(50)
        ],
        columns=list(fe.LEDGER_COLUMNS),
    )
    payload = fe.report_payload(pd.concat([settled, junk], ignore_index=True))
    assert payload["measurable_rows"] == 300
    assert payload["frozen_opinions"] == 400
    opinions = sum(r["bets"] for r in payload["rows"] if r["cut"] == "opinions")
    assert opinions == 300, (
        "A void is a bet that never existed and an unsettleable outcome is "
        "unknown. Averaging either in at zero fabricates a number."
    )


def test_reachability_is_reported_separately_when_the_ledger_carries_it():
    ledger = _ledger(300, profit=lambda i: 1.0)
    ledger["price_survived"] = [i % 2 == 0 for i in range(len(ledger))]
    report = fe.render_ledger(ledger)
    assert "## Reachability" in report
    assert "survived" in report and "vanished" in report

    without = fe.render_ledger(_ledger(300, profit=lambda i: 1.0))
    assert "does not carry price survival" in without, (
        "Reachability unmeasured must say so, rather than being silently absent."
    )


def test_an_edge_that_lives_only_in_prices_that_vanished_is_not_reachable():
    """From the brief: a soft number you cannot bet is not an edge."""
    ledger = _ledger(600, profit=lambda i: 1.0 if i % 2 else -1.0)
    ledger["price_survived"] = [i % 2 == 0 for i in range(len(ledger))]
    # Winners are exactly the rows whose price had already gone.
    ledger.loc[ledger["price_survived"], "profit_units"] = -1.0
    ledger.loc[~ledger["price_survived"], "profit_units"] = 1.0
    report = fe.render_ledger(ledger)
    assert fe.NOT_REACHABLE in report


def test_every_reported_number_carries_its_sample_size():
    report = fe.render_ledger(_ledger(300, profit=lambda i: 1.0))
    assert "| 300 |" in report
    assert "frozen opinions in the ledger" in report


def test_the_report_writes_both_renders_from_one_computation(tmp_path):
    ledger = _ledger(300, profit=lambda i: 1.0)
    markdown, payload = fe.write_report(ledger, output_dir=tmp_path)
    assert markdown.name == fe.REPORT_MARKDOWN_FILENAME
    assert payload.name == fe.REPORT_JSON_FILENAME
    assert markdown.read_text(encoding="utf-8").startswith("# Forward evidence")


def test_render_never_mutates_the_ledger_it_was_handed():
    ledger = _ledger(30, profit=lambda i: 1.0)
    before = list(ledger.columns)
    fe.render_ledger(ledger)
    assert list(ledger.columns) == before


# --------------------------------------------------------------------------
# The arithmetic that turns a price into a profit
# --------------------------------------------------------------------------


def test_american_odds_do_not_sort_numerically_and_the_payout_knows_it():
    assert fe.profit_units(Outcome.WON, 150) == pytest.approx(1.5)
    assert fe.profit_units(Outcome.WON, -200) == pytest.approx(0.5)
    assert fe.profit_units(Outcome.LOST, -110) == -1.0
    assert fe.profit_units(Outcome.PUSH, -110) == 0.0
    assert fe.profit_units(Outcome.VOID, -110) == 0.0


def test_a_won_bet_at_an_unreadable_price_has_no_profit_rather_than_zero():
    assert fe.profit_units(Outcome.WON, "") is None
    assert fe.profit_units(Outcome.UNSETTLEABLE, -110) is None


def test_edge_is_expected_value_per_unit_and_is_none_without_a_probability():
    assert fe.expected_value(0.6, 100) == pytest.approx(0.2)
    assert fe.expected_value(None, 100) is None
    assert fe.expected_value(0.6, "") is None


# ---------------------------------------------------------------------------
# A market refused by name carries no verdict
# ---------------------------------------------------------------------------


def test_a_market_refused_by_name_never_reaches_a_verdict_table():
    """The Opinions table prints ROI, intervals and a Verdict, and filtered nothing.

    `_bet_rows` excludes every player prop from the BETS table — a bet nobody
    can place is not a bet — and that is a different table answering a
    different question. The Opinions table carried the whole PLAYER family,
    including the two markets this lab refuses to price AT ALL, for reasons
    that have nothing to do with the number.

    Latent rather than live: the committed record carries 0 rows, so no such
    verdict has been printed. It goes live the day the player engine lets the
    card freeze a prop, which is why it is closed first.
    """
    from cbb_betting_lab.models.player_rates import MARKETS_REFUSED_BY_NAME

    assert MARKETS_REFUSED_BY_NAME, "no market is refused by name any more"
    frame = pd.DataFrame(
        [
            {"market": key, "tier": "high_major", "edge_value": 0.05}
            for key in list(MARKETS_REFUSED_BY_NAME) + ["player_points", "spread"]
        ]
    )
    kept = fe._without_markets_refused_by_name(frame)
    assert not set(kept["market"]) & set(MARKETS_REFUSED_BY_NAME), (
        "a market refused by name survived into a table that carries a Verdict "
        "column"
    )
    # And it filters those and nothing else.
    assert set(kept["market"]) == {"player_points", "spread"}

    # The list is read from the model, never copied here: adding one there
    # filters it here without anybody remembering to.
    invented = pd.DataFrame([{"market": "player_invented", "tier": "t", "edge_value": 0.1}])
    assert len(fe._without_markets_refused_by_name(invented)) == 1


def test_the_rendered_ledger_prints_no_verdict_for_a_refused_market(census_receipt):
    """The helper working is not the same as the helper being CALLED.

    Written first as a test of `_without_markets_refused_by_name` alone, which
    passed with the call site deleted — the exact vacuity this file has been
    finding elsewhere all day. This drives `render_ledger` and reads the
    rendered table, so removing the filter from either table turns it red.
    """
    from cbb_betting_lab.models.player_rates import MARKETS_REFUSED_BY_NAME

    refused = sorted(MARKETS_REFUSED_BY_NAME)[0]
    rows = _ledger(300, profit=lambda i: 1.0 if i % 2 else -1.0, market=refused)
    report = fe.render_ledger(rows)

    table_lines = [
        line
        for line in report.splitlines()
        if line.startswith("|") and refused in line
    ]
    assert not table_lines, (
        f"{refused} appears in a table row of the rendered ledger:\n  "
        + "\n  ".join(table_lines[:3])
        + "\nThat table carries a Verdict column, and this market is refused "
        "before any number is computed."
    )


def test_the_no_price_sentence_is_read_off_the_rows():
    """It said "this lab has no price for them either" whatever the rows held.

    True while the card gave every prop a census bucket and no probability.
    False the moment the engine prices one — and printed directly above an
    Opinions table whose ROI rows came from those very rows. A reader auditing
    whether any player number here can be trusted would be told, by the report
    holding the numbers, that the numbers do not exist.
    """
    import inspect

    source = inspect.getsource(fe.render_ledger)
    assert "model_probability" in source, (
        "the paragraph no longer reads what the rows carry, so it is asserting "
        "again"
    )
    assert "carry a model probability" in source
    assert "This lab has no price for them either" in source, (
        "the no-price branch is gone; it is still the truth when nothing is "
        "priced and must still be sayable"
    )


#: Every module that builds a `stats.RoiInterval` or prints a verdict, and how
#: a market refused BY NAME is kept out of it.
#:
#: **A roster with an inverse, because naming three doors found a fourth.**
#: `render_ledger` was fixed first. `report_payload` renders the same numbers
#: as JSON and was left unfiltered, so the refused market kept its verdict in
#: the data while the markdown no longer showed one. `reachability.build_record`
#: builds its own clustered interval and its own verdict and knew nothing about
#: the refusal at all. Three doors, found one at a time, which is exactly the
#: failure mode a list of known doors has.
#:
#: So the test below scans the tree for the construct and requires every module
#: carrying it to be accounted for here. A new one fails until somebody says
#: which case it is.
VERDICT_PRODUCING_MODULES = {
    # Filtered: a graded frame reaches these and a refused market must not.
    "forward_evidence.py": "filtered",
    "reachability.py": "filtered",
    # Added 2026-09-07: design section 10's scoring of the player-prop model.
    # It is the only module here whose whole population is player props, so the
    # filter is not a precaution on it -- it is the thing that keeps
    # `player_first_basket` and `player_double_double` out of a table that is
    # otherwise entirely about markets like them.
    "reports/prop_grading.py": "filtered",
    # These score team markets only. A player prop never reaches them: the
    # model has been scored on ten markets and every one is a team market, and
    # `price_backtest` is the thing that scores them.
    "reports/price_backtest.py": "team markets only",
    "reports/replication.py": "team markets only",
    "reports/forecast_skill.py": "team markets only",
    "reports/retention_probe.py": "team markets only",
    # These re-render a record somebody else computed; they add no interval of
    # their own to a market that was not already in it.
    "reports/what_we_can_claim.py": "renders a record",
    "reports/why_the_model.py": "renders a record",
    "restatement.py": "renders a record",
    # The construct itself.
    "stats.py": "defines the interval",
}


def test_every_verdict_producing_module_is_accounted_for():
    """A fourth door must fail this test rather than open quietly."""
    import subprocess

    repo = Path(__file__).resolve().parents[1]
    listing = subprocess.run(
        ["git", "ls-files", "-z", "src/cbb_betting_lab"],
        cwd=repo, capture_output=True, check=True,
    )
    found = set()
    for name in listing.stdout.decode("utf-8").split("\0"):
        if not name.endswith(".py"):
            continue
        text = (repo / name).read_text(encoding="utf-8", errors="replace")
        if "RoiInterval(" in text or ".verdict()" in text:
            found.add(name.split("src/cbb_betting_lab/", 1)[-1])

    assert found == set(VERDICT_PRODUCING_MODULES), (
        "the set of modules that build an interval or print a verdict has "
        f"changed.\n  new: {sorted(found - set(VERDICT_PRODUCING_MODULES))}"
        f"\n  gone: {sorted(set(VERDICT_PRODUCING_MODULES) - found)}\n"
        "Say which case each new one is: does a graded frame reach it, and if "
        "so does a market refused by name get filtered out first?"
    )



def test_the_filtered_modules_are_driven_not_grepped():
    """Grepping for the filter's NAME matches its import, not its use.

    Written first as `assert "without_markets_refused_by_name" in text`, which
    stayed green with the call deleted from `reachability.build_record` — the
    import line still carried the name. It is the third time today a test has
    proved a helper exists rather than that it is called, so both filtered
    modules are driven with a refused-market row and read for a verdict.
    """
    from cbb_betting_lab import reachability as RC
    from cbb_betting_lab.models.player_rates import MARKETS_REFUSED_BY_NAME

    refused = sorted(MARKETS_REFUSED_BY_NAME)[0]

    # **The census gate now answers first, and refusing is the right answer.**
    # `guard_graded_frame` is required by its own test to be the FIRST
    # statement in every grading entry point — a gate that runs after the
    # de-vig is a gate on the report, not on the run — so with no receipt it
    # refuses anything player-shaped, including a market that could never be
    # graded anyway. Fail-closed. This test used to drive straight through to
    # the filter; it cannot any more, and that is a stronger position.
    from cbb_betting_lab.models import player_census

    assert player_census.reconciled() == ()
    with pytest.raises(player_census.WagerCountMismatch):
        fe.report_payload(
            _ledger(300, profit=lambda i: 1.0 if i % 2 else -1.0, market=refused)
        )

    # And the filter still runs immediately after the gate, so a receipt does
    # not let a refused market into the payload. The ORDER is the claim, and
    # the order is what is read — driving it would need a reconciled census
    # over the real store, which this test has none of and must not fake.
    import inspect

    _assert_gate_precedes_filter(fe.report_payload)

    # reachability, which builds its own interval and its own verdict. It
    # takes a GRADED bet frame, not a ledger, so the columns it requires are
    # supplied rather than defaulted — `require_columns` refuses a missing one
    # on purpose and this test must not route around that.
    from cbb_betting_lab.reports import price_backtest as PB

    ledger = _ledger(300, profit=lambda i: 1.0 if i % 2 else -1.0, market=refused)
    graded = pd.DataFrame(
        {
            column: (
                ledger[column]
                if column in ledger.columns
                else _bet_column_filler(column, len(ledger))
            )
            for column in PB.BET_COLUMNS
        }
    )
    with pytest.raises(player_census.WagerCountMismatch):
        RC.build_record(bets=graded)

    _assert_gate_precedes_filter(RC.build_record)

    # prop_grading, the third filtered door and the only one whose population
    # is nothing but player props.
    from cbb_betting_lab.reports import prop_grading as PG

    with pytest.raises(player_census.WagerCountMismatch):
        PG.build_record(
            PG.PropGradingInputs(
                graded=pd.DataFrame(
                    {
                        column: _bet_column_filler(column, 8)
                        for column in (*PG.GRADED_COLUMNS, "market")
                    }
                ).assign(market=refused)
            )
        )

    _assert_gate_precedes_filter(PG.build_record)



def _bet_column_filler(column: str, n: int):
    """A plausible value for a graded-bet column the ledger fixture lacks.

    Only for columns `require_columns` demands and the ledger does not carry;
    nothing here is a price, an odds or an outcome the test then measures.
    """
    if column == "slate_date":
        return ["2027-01-12"] * n
    if column in {"model_probability", "edge_value", "implied_probability"}:
        return [0.5] * n
    if column == "profit":
        return [0.0] * n
    return [""] * n


def _assert_gate_precedes_filter(function) -> None:
    """Every gate call precedes every filter CALL — not the import that names it.

    **`str.index` returns the FIRST occurrence, and the token appears in the
    import too.** The first version of this compared
    `source.index("guard_graded_frame")` against
    `source.index("without_markets_refused_by_name")`, and
    `reachability.build_record` carries that second token three times: the new
    call, a pre-existing `from ... import (...)`, and a pre-existing call.
    Measured: replace BOTH filter calls with `bets = bets`, leave the import,
    and 122 tests pass — including this assertion, whose message reads
    "build_record filters before it gates". It could not tell a filtered
    function from an unfiltered one.

    This walks the syntax tree instead: it finds the Call nodes, requires at
    least one of each, and compares the LAST gate call against the FIRST filter
    call, so a filter that runs before any gate fails whatever else the file
    says.
    """
    import ast
    import inspect
    import textwrap

    tree = ast.parse(textwrap.dedent(inspect.getsource(function)))

    # **A filter whose result is thrown away filters nothing.** The first AST
    # version collected Call nodes by name, so replacing
    # `bets = without_markets_refused_by_name(bets)` with the bare expression
    # `without_markets_refused_by_name(bets)` kept the Call, kept this green,
    # and filtered nothing — 122 tests passed while a 300-row
    # `player_first_basket` frame came back from `build_record` with a verdict.
    # That is the same failure as the `str.index` version this replaced: it
    # proved the helper was NAMED, not that it did the work.
    #
    # So a filter call counts only when its value is BOUND — the parent node is
    # an assignment whose target is a plain name — and the name it binds must
    # be the name it was given, or the frame that flows on is not the filtered
    # one.
    bound_filters: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        value = node.value
        if not isinstance(target, ast.Name) or not isinstance(value, ast.Call):
            continue
        called = getattr(value.func, "attr", None) or getattr(value.func, "id", None)
        if called not in {
            "without_markets_refused_by_name",
            "_without_markets_refused_by_name",
        }:
            continue
        # **No escape hatch for a non-name argument.** The previous version
        # read `if passed_name is None or target.id == passed_name`, and the
        # disjunction SKIPPED the check whenever the argument was not a bare
        # name — a `.copy()`, a slice, a keyword-only call. Reproduced:
        # `unused = _PR.without_markets_refused_by_name(bets.copy())` kept this
        # green, and a 300-row `player_double_double` frame then came back from
        # `build_record` with a verdict. That is the third version of this
        # assertion defeated the same way: it proved a construct was PRESENT,
        # not that the frame flowing on was the filtered one.
        #
        # The filter must take a bare name and bind the result back to THAT
        # name, so the frame every later line sees is the filtered one.
        passed = value.args[0] if value.args else None
        if not isinstance(passed, ast.Name):
            continue
        if target.id == passed.id:
            bound_filters.append(node.lineno)

    gates, filters = [], list(bound_filters)
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "attr", None) or getattr(node.func, "id", None)
        if name == "guard_graded_frame":
            gates.append(node.lineno)
    assert gates, f"{function.__qualname__} calls no census gate at all"
    assert filters, (
        f"{function.__qualname__} binds no refusal filter at all. A call whose "
        "result is discarded is not a filter: the frame that flows on is the "
        "unfiltered one, and a market refused by name reaches whatever this "
        "builds."
    )
    assert max(gates) < min(filters), (
        f"{function.__qualname__} filters at line {min(filters)} before it "
        f"gates at line {max(gates)}. The gate must be the first statement: a "
        "gate that runs after the de-vig is a gate on the report, not the run."
    )


# --------------------------------------------------------------------------
# What a forward null could have found
#
# This organ needs the column more than any other in the lab. Scaling the
# historical standard errors to one season's bet count, a single forward
# season can demonstrate a return of roughly 9.5% to 11.9% once the family
# correction is applied, against a real edge of one to three percent. A first
# season reporting `no demonstrated edge` is reporting that it could not have
# seen one, and the three words alone do not say so.
# --------------------------------------------------------------------------


def test_a_forward_null_says_what_return_it_could_have_demonstrated():
    """The column is in the page and carries a figure for a measured row."""
    report = fe.render_ledger(_ledger(400, profit=lambda i: 1.0 if i % 2 else -1.0))
    assert "| Could detect |" in report
    assert "±" in report, (
        "every row cleared the floor and none of them said what it could have "
        "demonstrated"
    )


def test_a_forward_row_below_the_floor_states_no_detectable_return():
    """Below the declared floor there is no figure, and that includes this one."""
    # The profit VARIES. With `profit=lambda i: 1.0` every bet wins, the
    # standard error is zero, and the em dash arrives through the NaN check
    # whether or not the floor is tested at all -- so the test could not fail
    # and a mutant deleting the floor sailed past it. A row needs real
    # variance for the floor to be the only thing standing between it and a
    # printed figure.
    report = fe.render_ledger(_ledger(30, profit=lambda i: 1.0 if i % 2 else -1.0))
    assert "| Could detect |" in report
    assert "30 | " in report, "the fixture did not reach the table"
    assert "±" not in report, (
        "a row under the 200-bet floor printed a detectable return, which is "
        "the reading the floor exists to prevent"
    )


def test_the_forward_detectable_return_is_the_corrected_bound():
    """Not a second statistic: the bound already applied, from the other side."""
    interval = stats.RoiInterval(
        roi=0.0, low=-0.09, high=0.09, bets=14_724, clusters=140,
        standard_error=0.0459, looks=98,
    )
    assert interval.roi + interval.minimum_detectable_effect == pytest.approx(
        interval.adjusted_high, abs=1e-12
    )
    assert fe._detectable(interval, minimum_bets=200) == (
        f"±{interval.minimum_detectable_effect:.1%}"
    )
    assert fe._detectable(interval, minimum_bets=20_000) == "—", (
        "the floor is checked against the row's bets, not against nothing"
    )


def test_one_forward_season_cannot_demonstrate_a_realistic_edge():
    """The measured reason this column exists here.

    A mid-major season is about 14,700 bets. Scaled from the historical
    standard error, that sample can demonstrate a return of roughly 9%-10%
    once 98 hypotheses are corrected for. A real edge is 1%-3%, so a single
    season's null is a statement about the sample and not about the model —
    and this test fails if that ever stops being true, which would mean the
    forward window had become powerful enough to read literally.
    """
    season = stats.RoiInterval(
        roi=0.0, low=-0.09, high=0.09, bets=14_724, clusters=140,
        standard_error=0.02734, looks=98,
    )
    mde = season.minimum_detectable_effect
    assert 0.05 < mde < 0.15, (
        f"one mid-major season's detectable return is {mde:.1%}; the plan to "
        "register 2027 over multiple seasons rests on it being far above a "
        "realistic 1-3% edge"
    )
    assert mde > 0.03, "a 3% edge is the optimistic end of realistic"
