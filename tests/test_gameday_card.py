"""The card, proved end to end with no network and no credential.

This file exists because **a green workflow run is not a delivered card**. The
EPL lab spent five days green and empty, and the gameday workflow here
referenced three scripts that did not exist without anything failing, because
nothing had dispatched it. So the tests below drive the real entry point over a
staged board with the socket layer closed and the credential deleted from the
environment, and read what actually lands on disk.

That offline path is the point of the fixture: it proves the delivery chain can
produce a card **before a single credit is spent on it**, which is the only
moment at which finding out is cheap.

Every regression test names the defect it pins. Three of them are defects this
work found and fixed on the caller's side of a module it may not edit; each says
so in its docstring.
"""

from __future__ import annotations

import json
import runpy
from pathlib import Path
import socket
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

from cbb_betting_lab import forward_evidence
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.conferences import Tier
from cbb_betting_lab.gates import TipState
from cbb_betting_lab.providers import odds_api, staging
from cbb_betting_lab.reports import gameday_card as GC
from cbb_betting_lab.reports.card_pricing import BAR_ORDER, Bar, SelectionResult, Wager
from cbb_betting_lab.staging_provider_policy import (
    MANUAL_ONLY,
    AllowlistEntry,
    StagingProviderPolicy,
)
from cbb_betting_lab.staging_provider_policy import load as load_policy

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run_gameday_card.py"


# ---------------------------------------------------------------------------
# Fixtures: a provider-shaped board, built once and read by everything
# ---------------------------------------------------------------------------


def _iso(moment: datetime) -> str:
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _book(key: str, markets: list[dict]) -> dict:
    return {"key": key, "title": key.title(), "markets": markets}


def _event(
    event_id: str,
    *,
    home: str,
    away: str,
    commence: datetime,
    books: list[dict],
) -> dict:
    return {
        "id": event_id,
        "commence_time": _iso(commence),
        "home_team": home,
        "away_team": away,
        "bookmakers": books,
    }


def board_payloads(now: datetime) -> list[dict]:
    """A board with one cardable game, one started game and one for tomorrow.

    It also carries, deliberately, the four things `providers/staging.py`
    refuses: an unwired provider key, an outcome that resolves to no known
    selection (a `Draw`, which cannot exist in this sport), a price that will
    not read as a number, and a market this lab does wire priced by two books at
    two prices — which is what the best-price collapse is for.
    """
    soon = now + timedelta(hours=6)
    started = now - timedelta(minutes=30)
    tomorrow = now + timedelta(days=1, hours=6)
    return [
        _event(
            "evt-cardable",
            home="Duke Blue Devils",
            away="Kansas Jayhawks",
            commence=soon,
            books=[
                _book(
                    "draftkings",
                    [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Duke Blue Devils", "price": -180},
                                # The worse of the two away prices, and the one
                                # that arrives first.
                                {"name": "Kansas Jayhawks", "price": 120},
                                {"name": "Draw", "price": 900},
                            ],
                        },
                        {
                            "key": "spreads",
                            "outcomes": [
                                {"name": "Duke Blue Devils", "price": -110, "point": -3.0},
                                {"name": "Kansas Jayhawks", "price": -110, "point": 3.0},
                            ],
                        },
                        {
                            "key": "totals",
                            "outcomes": [
                                {"name": "Over", "price": -110, "point": 142.5},
                                {"name": "Under", "price": "", "point": 142.5},
                            ],
                        },
                        {
                            "key": "spreads_q1",
                            "outcomes": [
                                {"name": "Duke Blue Devils", "price": -110, "point": -1.0}
                            ],
                        },
                    ],
                ),
                _book(
                    "fanduel",
                    [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Duke Blue Devils", "price": -175},
                                {"name": "Kansas Jayhawks", "price": 150},
                            ],
                        },
                        {
                            "key": "team_totals",
                            "outcomes": [
                                {
                                    "name": "Over",
                                    "description": "Duke Blue Devils",
                                    "price": -110,
                                    "point": 73.5,
                                }
                            ],
                        },
                    ],
                ),
            ],
        ),
        _event(
            "evt-started",
            home="Gonzaga Bulldogs",
            away="Baylor Bears",
            commence=started,
            books=[
                _book(
                    "draftkings",
                    [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Gonzaga Bulldogs", "price": -140},
                                {"name": "Baylor Bears", "price": 300},
                            ],
                        }
                    ],
                )
            ],
        ),
        _event(
            "evt-tomorrow",
            home="Villanova Wildcats",
            away="Notre Dame Fighting Irish",
            commence=tomorrow,
            books=[
                _book(
                    "draftkings",
                    [
                        {
                            "key": "h2h",
                            "outcomes": [
                                {"name": "Villanova Wildcats", "price": -120},
                                {"name": "Notre Dame Fighting Irish", "price": 400},
                            ],
                        }
                    ],
                )
            ],
        ),
    ]


def a_matchup(**overrides) -> SimpleNamespace:
    """A `gameday_card.Matchup`-shaped object. A pick'em on a neutral floor."""
    fields = {
        "home_points_per_possession": 1.05,
        "away_points_per_possession": 1.05,
        "possessions": 68.0,
        "prior_weight": 0.12,
        "venue_state": "home",
        "priceable": True,
        "unpriceable_reason": "",
    }
    fields.update(overrides)
    return SimpleNamespace(**fields)


def a_policy(*markets: str) -> StagingProviderPolicy:
    """An in-memory policy allowlisting some markets, for tests only.

    **This grants nothing.** `data/manual/staging_provider_policy.json` is
    untouched and stays manual-only — there is a test below that asserts it. The
    object exists so the code path *behind* the first bar can be exercised at
    all: a card whose selection path has never run is a card nobody has tested,
    and the day Cooper signs a receipt is the wrong day to find that out.
    """
    return StagingProviderPolicy(
        mode="reviewed",
        allowlist={
            m: AllowlistEntry(
                market=m,
                receipt_id="test-only",
                approved_on="1970-01-01",
                roi_floor=0.0,
                evidence_checksum="",
                note="constructed in a test; never written to disk",
            )
            for m in markets
        },
    )


@pytest.fixture()
def now() -> datetime:
    return datetime(2027, 1, 12, 15, 0, tzinfo=timezone.utc)


@pytest.fixture()
def board(now) -> GC.Board:
    return GC.board_from_payloads(board_payloads(now), competition=CBB)


@pytest.fixture()
def day(now) -> str:
    from cbb_betting_lab.season import slate_date

    return slate_date(_iso(now + timedelta(hours=6)), CBB)


@pytest.fixture()
def today() -> str:
    return datetime.now(CBB.timezone).date().isoformat()


@pytest.fixture()
def payloads_for_today(today) -> list[dict]:
    """The same board, tipping late **today** in the competition's own calendar.

    The script refuses to card any day but today without `--rehearsal`, in both
    directions, so a fixture pinned to a fixed date can only ever exercise the
    refusal. The cardable tip is placed at 23:45 Eastern, which is after the
    sport's real last tip and comfortably ahead of any run — the point is that
    it lands on today's slate day and in the future, not that it is realistic.
    Deriving it from the Eastern calendar rather than from `now + 6 hours` is
    what stops the test flipping to `no-slate` whenever it happens to run in
    the evening.
    """
    at = datetime.fromisoformat(f"{today}T23:45:00").replace(tzinfo=CBB.timezone)
    if at <= datetime.now(CBB.timezone) + timedelta(minutes=30):
        pytest.skip(
            "There is no future time left on today's Eastern slate day. The "
            "same path is covered deterministically by the tests that call "
            "run_card directly on a fixed clock."
        )
    return board_payloads(at.astimezone(timezone.utc) - timedelta(hours=6))


@pytest.fixture()
def board_for_today(payloads_for_today) -> GC.Board:
    return GC.board_from_payloads(payloads_for_today, competition=CBB)


@pytest.fixture()
def no_network(monkeypatch):
    """Every route to a socket, closed. A card built offline is built offline."""

    def refuse(*args, **kwargs):
        raise AssertionError(
            "The card run tried to open a network connection. The offline path "
            "must reach a rendered card without one."
        )

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.fixture()
def no_credential(monkeypatch):
    for name in ("CBB_ODDS_API_KEY", "ODDS_API_KEY", "THE_ODDS_API_KEY"):
        monkeypatch.delenv(name, raising=False)


def run_script(*argv: str) -> int:
    saved = sys.argv[:]
    sys.argv = [str(SCRIPT), *argv]
    try:
        runpy.run_path(str(SCRIPT), run_name="__main__")
        return 0
    except SystemExit as exit_code:
        return int(exit_code.code or 0)
    finally:
        sys.argv = saved


def stage_to_disk(board: GC.Board, tmp_path: Path, day: str) -> Path:
    staging_dir = tmp_path / "staging"
    target = staging.staging_path(
        CBB, day=day, slot="morning", staging_dir=staging_dir
    )
    return staging.write_staged(board.rows, target, staging_dir=staging_dir)


# ---------------------------------------------------------------------------
# The offline end-to-end path
# ---------------------------------------------------------------------------


def test_the_whole_chain_runs_offline_from_a_staged_board(
    board_for_today, today, tmp_path, capsys, no_network, no_credential
):
    """The entry point, over a fixture, with the socket layer closed.

    This is the test the brief calls "the thing that proves the delivery chain
    can work before a single credit is spent". It runs `scripts/run_gameday_card.py`
    itself rather than a helper, because the workflow runs the script.
    """
    staged = stage_to_disk(board_for_today, tmp_path, today)
    status = run_script(
        "--card-slot", "morning",
        "--staged-board", str(staged),
        "--archive-dir", str(tmp_path / "archive"),
        "--output-dir", str(tmp_path / "outputs"),
        "--raw-dir", str(tmp_path / "raw"),
    )
    out = capsys.readouterr().out

    assert status == 0, out
    card = tmp_path / "outputs" / "cbb_gameday_card.md"
    comment = tmp_path / "outputs" / "cbb_card_comment.md"
    assert card.is_file() and comment.is_file()
    assert out.rstrip().endswith(f"decision={GC.Decision.NO_SELECTIONS.value}")
    assert GC.ACCUMULATING_NOTE in card.read_text(encoding="utf-8")
    assert GC.ACCUMULATING_NOTE in comment.read_text(encoding="utf-8")
    assert (
        tmp_path / "archive" / forward_evidence.SNAPSHOT_DIRNAME / f"{today}.csv"
    ).is_file()


def test_the_workflow_writes_the_two_filenames_the_workflow_reads(board, day, tmp_path):
    """`data/outputs/cbb_gameday_card.md` and `data/outputs/cbb_card_comment.md`.

    Both are named in `.github/workflows/cbb-gameday-refresh.yml`, and both are
    derived from the competition registry's `output_name` rather than typed
    twice. An unprefixed output is a file two competitions would both write.
    """
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive",
    )
    card, comment = GC.write_outputs(run, tmp_path / "outputs")

    assert card.name == "cbb_gameday_card.md"
    assert comment.name == "cbb_card_comment.md"


def test_the_card_says_it_is_accumulating_evidence_and_makes_no_call(
    board, day, tmp_path
):
    """No market is allowlisted, so there is no selection, no lean, no pass and
    no stake — and the card says why in the gate's own words."""
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive",
    )
    text = GC.render_card(run)

    assert run.selections == []
    assert run.decision is GC.Decision.NO_SELECTIONS
    assert GC.ACCUMULATING_NOTE in text
    assert "No selection, no lean, no pass and no stake." in text
    assert "not a pass, an avoid, or a no-value call" in text
    assert "manual-only" in text
    for banned in ("lean", "avoid", "no value", "no-value"):
        # Every mention of one of these words must be inside a denial. A card
        # that says "no value here" has made a call.
        for sentence in text.split("."):
            if banned in sentence.casefold():
                assert any(
                    marker in sentence.casefold()
                    for marker in ("no ", "never", "not ", "is not")
                ), sentence


def test_the_policy_on_disk_is_manual_only_and_nothing_here_changed_it():
    """`grant()` does not exist, and no test may become one."""
    policy = load_policy()

    assert policy.mode == MANUAL_ONLY
    assert policy.allowlist == {}


# ---------------------------------------------------------------------------
# The accounting identity
# ---------------------------------------------------------------------------


def test_every_bar_lands_in_exactly_one_bucket():
    """A bar added upstream without a bucket here would vanish from the
    identity, and the identity would still reconcile — which is the worst
    possible failure of an identity."""
    assert set(BAR_ORDER) == set(GC.BAR_BUCKETS)
    assert set(GC.BAR_BUCKETS.values()) <= {
        "no_opinion", "below_threshold", "ambiguous", "gated"
    }


def test_the_identity_reconciles_over_a_real_board(board, day, tmp_path):
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive",
    )
    identity = run.identity

    assert identity.reconciles(), identity.summary_line()
    assert identity.priced == run.result.priced_wagers + identity.unparseable
    assert identity.priced > 0


def test_the_two_identities_are_printed_separately_and_both_reconcile(
    board, day, tmp_path
):
    """The provider's outcomes and this slate day's wagers are two populations.

    The fixture carries a `Draw` (which cannot exist in this sport), an unwired
    quarter market and an unreadable price. All three are refused when the
    *response* is read, and they are counted in staging's identity — which is
    over every day the read saw. Folding them into the card's identity, which is
    over one slate day, would put two populations either side of one equals
    sign, and an identity like that reconciles over whichever population
    survived.
    """
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive",
    )
    text = GC.render_card(run)

    assert board.counts.refused == 3
    assert board.counts.reconciles(), board.counts.summary_line()
    assert run.identity.reconciles(), run.identity.summary_line()
    assert board.counts.summary_line() in text
    assert run.identity.summary_line() in text
    assert "two identities and they are deliberately not merged" in text
    for reason in ("the market key is not wired", "the price is missing or unreadable"):
        assert reason in text


def test_a_corrupt_row_in_a_staged_file_is_counted_and_never_dropped(
    board, day, tmp_path
):
    """On the offline path the staged file is the input, and `build_wagers` is
    the only guard between it and the card.

    A staged file is data on disk: it can be hand-edited, or written by an
    earlier version of the stager whose vocabulary has since moved. Four things
    stop a row becoming a wager — a market this lab does not wire, a segment
    that is not one of the three, a selection outside the vocabulary, and a
    price that will not read as a number — and every one of them is counted into
    `unparseable`. A row that reached none of them vanished, and a silent drop
    is how a card recommends from a sixth of a slate.
    """
    rows = board.rows.copy()
    corrupt = rows.iloc[[0, 0, 0, 0]].copy().reset_index(drop=True)
    corrupt["american_odds"] = corrupt["american_odds"].astype(object)
    corrupt.loc[0, "market"] = "a_market_this_lab_does_not_wire"
    corrupt.loc[1, "segment"] = "q1"
    corrupt.loc[2, "selection"] = "draw"
    corrupt.loc[3, "american_odds"] = "not a number"
    staged = tmp_path / "staging" / CBB.data_dir_segment / f"{day}_morning.csv"
    staged.parent.mkdir(parents=True, exist_ok=True)
    pd.concat([rows, corrupt], ignore_index=True).to_csv(staged, index=False)

    run = GC.run_card(
        GC.read_staged_board(staged, competition=CBB),
        competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive",
    )

    assert run.identity.unparseable == 4, run.identity.summary_line()
    assert run.identity.reconciles(), run.identity.summary_line()
    text = GC.render_card(run)
    for reason in (
        "the market is not one this lab wires",
        "the segment is not one of game, h1 or h2",
        "the selection is outside this lab's vocabulary",
        "the price is missing or unreadable",
    ):
        assert reason in text


def test_an_identity_that_does_not_reconcile_raises_rather_than_warns():
    """It is an error, not a warning. A wager that reached none of the six
    buckets vanished, and a silent drop is how a card recommends from a sixth of
    a slate and reports it as the whole one."""
    result = SelectionResult()
    result.priced_wagers = 10
    result.bar_counts = {Bar.NO_OPINION.value: 3}

    with pytest.raises(ValueError, match="does not reconcile"):
        GC.reconcile(result, unparseable=0)


def test_a_bar_with_no_bucket_is_refused_rather_than_dropped(monkeypatch):
    monkeypatch.delitem(GC.BAR_BUCKETS, Bar.SLATE_CAP)
    result = SelectionResult()

    with pytest.raises(GC.CardError, match="no bucket"):
        GC.reconcile(result, unparseable=0)


# ---------------------------------------------------------------------------
# The tip guard, which runs continuously
# ---------------------------------------------------------------------------


def test_a_started_game_carries_no_stake_and_is_counted(board, day, tmp_path, now):
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive", now=lambda: now,
    )

    assert run.tip.games(TipState.STARTED) == 1
    assert run.tip.games(TipState.UPCOMING) >= 1
    frozen = forward_evidence.read_snapshot(run.snapshot_path)
    assert "evt-started" not in set(frozen["event_id"]), (
        "An opinion frozen after tip is not forward evidence."
    )


def test_a_game_that_tips_between_pricing_and_the_card_loses_its_stake(
    board, day, tmp_path, now, monkeypatch
):
    """The guard runs continuously, not once.

    This sport tips games every fifteen minutes for twelve hours and a slate
    takes minutes to fetch, so a game that was upcoming when its price was read
    can have tipped by the time the card renders. The second pass withdraws it,
    **its stake is removed**, and the identity moves it from `bets` to `gated`
    rather than losing it.
    """
    tip = now + timedelta(hours=6)
    moved = {"on": False}
    original = GC.TipGuard.recheck

    def recheck_after_the_tip(self, selections):
        # The clock moves past the tip exactly when the second pass begins,
        # which is the situation the second pass exists for: a slate takes
        # minutes to fetch and a game can tip while the run is still working.
        moved["on"] = True
        return original(self, selections)

    monkeypatch.setattr(GC.TipGuard, "recheck", recheck_after_the_tip)

    def advancing() -> datetime:
        return tip + timedelta(minutes=1) if moved["on"] else now

    run = GC.run_card(
        board,
        competition=CBB,
        day=day,
        card_slot="morning",
        archive_dir=tmp_path / "archive",
        policy=a_policy("moneyline"),
        matchups={"evt-cardable": a_matchup()},
        now=advancing,
    )

    assert run.withdrawn_after_pricing, "Nothing was withdrawn; the clock did not advance."
    assert run.selections == []
    assert run.identity.reconciles(), run.identity.summary_line()
    assert run.identity.gated >= len(run.withdrawn_after_pricing)
    assert "withdrawn after pricing" in GC.render_card(run)


def test_an_unreadable_tip_time_quarantines_exactly_like_a_started_game(now):
    guard = GC.TipGuard(lambda: now)
    wager = Wager(
        key=("k",), event_id="e", slate_date="2027-01-12", commence_time="",
        home_team="A", away_team="B", market="moneyline", segment="game",
        player="", selection="home", line=None, tier="unplaced", quotes=(),
    )

    assert guard.state_for(wager) is TipState.UNCONFIRMED
    assert guard.census.games(TipState.UNCONFIRMED) == 1


# ---------------------------------------------------------------------------
# The freeze
# ---------------------------------------------------------------------------


def test_the_first_opinion_of_the_day_is_never_retroactively_replaced(
    board, day, tmp_path, now
):
    """The morning slot freezes what it can reach; the evening slot adds what it
    could not and re-prices nothing.

    Without that rule two cards a day is two bites at the same apple: the
    evening run would re-price the games the morning run got wrong and the
    ledger would record the better of two guesses.
    """
    archive = tmp_path / "archive"
    GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=archive, now=lambda: now,
    )
    morning = forward_evidence.read_snapshot(
        forward_evidence.snapshot_path(archive, day)
    )
    morning_price = float(
        morning.loc[
            (morning["event_id"] == "evt-cardable") & (morning["market"] == "moneyline")
            & (morning["selection"] == "home"),
            "american_odds",
        ].iloc[0]
    )

    # The evening board: the same game at a very different price, plus a game
    # the morning slot never saw.
    later = board_payloads(now)
    for block in later[0]["bookmakers"][0]["markets"]:
        if block["key"] == "h2h":
            for outcome in block["outcomes"]:
                if outcome["name"] == "Duke Blue Devils":
                    outcome["price"] = -101
    later.append(
        _event(
            "evt-late",
            home="Saint Mary's Gaels",
            away="Pepperdine Waves",
            commence=now + timedelta(hours=9),
            books=[
                _book("draftkings", [{
                    "key": "h2h",
                    "outcomes": [
                        {"name": "Saint Mary's Gaels", "price": -300},
                        {"name": "Pepperdine Waves", "price": 240},
                    ],
                }])
            ],
        )
    )
    GC.run_card(
        GC.board_from_payloads(later, competition=CBB),
        competition=CBB, day=day, card_slot="evening",
        archive_dir=archive, now=lambda: now,
    )
    evening = forward_evidence.read_snapshot(
        forward_evidence.snapshot_path(archive, day)
    )

    kept = float(
        evening.loc[
            (evening["event_id"] == "evt-cardable") & (evening["market"] == "moneyline")
            & (evening["selection"] == "home"),
            "american_odds",
        ].iloc[0]
    )
    assert kept == morning_price, "The evening slot re-priced a morning opinion."
    assert (evening["event_id"] == "evt-cardable").sum() == (
        morning["event_id"] == "evt-cardable"
    ).sum()
    assert "evt-late" in set(evening["event_id"]), (
        "The evening slot must add the games the morning slot could not reach."
    )


def test_the_frozen_price_is_the_best_price_and_not_whichever_book_came_first(
    board, day, tmp_path, now
):
    """Regression, and it pins a caller-side fix for an upstream behaviour.

    `forward_evidence.write_snapshot` dedupes on the selection key, and the
    selection key does not carry the book. Hand it every quote and it keeps
    **whichever row arrived first** — bookmaker order in the provider's
    response, which is an arbitrary book rather than the price the card would
    have taken. `gameday_card._freezable_rows` collapses to one row per wager at
    the best price first, which is the same collapse `card_pricing.select`
    makes when it takes the best price last.

    The fixture quotes Kansas at +120 (DraftKings, first) and +150 (FanDuel).
    The frozen row must be +150.
    """
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive", now=lambda: now,
    )
    frozen = forward_evidence.read_snapshot(run.snapshot_path)
    away = frozen.loc[
        (frozen["event_id"] == "evt-cardable")
        & (frozen["market"] == "moneyline")
        & (frozen["selection"] == "away")
    ]

    assert len(away) == 1, "One wager freezes one row."
    assert float(away["american_odds"].iloc[0]) == 150.0
    assert away["book"].iloc[0] == "fanduel"


def test_one_unreadable_row_cannot_take_down_the_freeze(board, day, tmp_path, now):
    """Regression. This defect was in this file and a test found it.

    The freeze was handed the board's **raw rows**, and `write_snapshot` keys
    every row it is given through the injected `key_for` — where
    `selection.selection_key` *raises* on a segment outside the three it knows.
    So a single malformed row in a staged file (an older stager's vocabulary, a
    human edit) crashed the freeze: the one step in this pipeline that cannot be
    re-made afterwards, brought down by a row `build_wagers` had already refused
    and counted.

    The fix is to build the frozen frame from the wagers rather than from the
    frame, so only rows that survived a guard can reach it.
    """
    rows = board.rows.copy()
    poison = rows.iloc[[0]].copy()
    poison["segment"] = "q1"
    poison["market"] = "a_market_this_lab_does_not_wire"
    staged = tmp_path / "staging" / CBB.data_dir_segment / f"{day}_morning.csv"
    staged.parent.mkdir(parents=True, exist_ok=True)
    pd.concat([rows, poison], ignore_index=True).to_csv(staged, index=False)

    run = GC.run_card(
        GC.read_staged_board(staged, competition=CBB),
        competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive", now=lambda: now,
    )
    frozen = forward_evidence.read_snapshot(run.snapshot_path)

    assert len(frozen) > 0, "The freeze produced nothing."
    assert "q1" not in set(frozen["segment"].astype(str))
    assert run.identity.unparseable == 1
    assert run.identity.reconciles()


def test_a_row_for_another_slate_day_is_never_frozen_under_this_one(
    board, day, tmp_path, now
):
    """The bulk endpoint returns every upcoming game. A row for tomorrow frozen
    under today's date carries tomorrow's slate date in its own key, so it would
    look unfrozen tomorrow and be priced twice."""
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive", now=lambda: now,
    )
    frozen = forward_evidence.read_snapshot(run.snapshot_path)

    assert "evt-tomorrow" not in set(frozen["event_id"])
    assert run.rows_off_this_slate > 0
    assert "belong to a slate day" in GC.render_card(run)


def test_a_run_that_freezes_nothing_still_leaves_a_record_that_it_ran(day, tmp_path):
    """"The pipeline had no opinion tonight" and "the pipeline did not run
    tonight" must never look the same."""
    empty = GC.board_from_payloads([], competition=CBB)
    run = GC.run_card(
        empty, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive",
    )

    assert forward_evidence.snapshot_path(tmp_path / "archive", day).is_file()
    assert run.decision is GC.Decision.NO_SLATE


# ---------------------------------------------------------------------------
# The model seam, and the November prior
# ---------------------------------------------------------------------------


def test_every_market_on_a_game_is_read_off_one_distribution(board, day, tmp_path):
    """One game, one object. The football lab priced its featured spread from
    one model and its alternate ladder from a normal approximation to it, and
    shipped a ladder whose −6.5 was better value than its −7.5."""
    wagers, _, _ = _wagers_for(board, day)
    probabilities, census = GC.opinions_for(
        wagers, {"evt-cardable": a_matchup()}, day=day
    )
    by_market = {
        (w.market, w.selection): probabilities[w.key]
        for w in wagers
        if w.key in probabilities
    }

    assert by_market, "Nothing priced; the seam to distributions.py is not wired."
    home = by_market[("moneyline", "home")]
    away = by_market[("moneyline", "away")]
    # A full game cannot end level, so the two sides are complementary — which
    # is the property that stops a card taking both sides of one game.
    assert home + away == pytest.approx(1.0, abs=1e-9)
    # The spread reads the same diagonal as the moneyline.
    assert by_market[("spread", "home")] < home
    assert census.push_mass[
        next(w.key for w in wagers if w.market == "spread" and w.selection == "home")
    ] > 0.0


def test_a_novembers_price_without_a_recorded_prior_weight_is_refused(board, tmp_path):
    """Cooper's rule, enforced rather than only printed: a November number must
    never be presentable as a February one. A blank prior weight is not zero —
    zero is the substantive claim that none of the price came from the prior."""
    november = "2026-11-17"
    wagers, _, _ = _wagers_for(board, november, force_day=True)

    without, census = GC.opinions_for(
        wagers, {"evt-cardable": a_matchup(prior_weight=None)}, day=november
    )
    with_it, _ = GC.opinions_for(
        wagers, {"evt-cardable": a_matchup(prior_weight=0.4)}, day=november
    )

    assert without == {}
    assert any("records no prior weight" in r for r in census.declined)
    assert with_it, "A price that records its prior weight is priceable."


def test_the_prior_weight_reaches_the_frozen_row_and_the_card(board, day, tmp_path, now):
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive",
        matchups={"evt-cardable": a_matchup(prior_weight=0.37)},
        now=lambda: now,
    )
    frozen = forward_evidence.read_snapshot(run.snapshot_path)
    priced = frozen.loc[frozen["event_id"] == "evt-cardable", "prior_weight"].dropna()

    assert len(priced) > 0
    assert float(priced.iloc[0]) == pytest.approx(0.37)


def test_an_unknown_venue_quarantines_the_game_rather_than_defaulting_to_neutral(
    board, day
):
    """A game mislabelled neutral is a multi-point error applied to every market
    on it. Venue has three values in this sport and not two."""
    wagers, _, _ = _wagers_for(board, day)

    probabilities, census = GC.opinions_for(
        wagers, {"evt-cardable": a_matchup(venue_state="unknown")}, day=day
    )

    assert probabilities == {}
    assert any("venue state is unknown" in reason for reason in census.declined)


def test_a_matchup_that_says_nothing_about_being_priceable_is_not_priced(board, day):
    """Ambiguity falls on the not-a-play side, always. A matchup carrying
    `priceable=None` has not said it is priceable, and reading a missing answer
    as yes is the one direction no gate here resolves in."""
    wagers, _, _ = _wagers_for(board, day)

    probabilities, census = GC.opinions_for(
        wagers, {"evt-cardable": a_matchup(priceable=None)}, day=day
    )

    assert probabilities == {}
    assert any("refuses to price" in reason for reason in census.declined)


def test_a_distribution_that_refuses_a_segment_is_counted_not_crashed(day, tmp_path, now):
    """A market whose joint cannot be built is a counted absence, never an
    exception out of the card.

    The live example today is the **second half**: `distributions.build` defaults
    `resolves_ties=True` for that segment and then refuses its own joint,
    because a second half settled including overtime can still end level and the
    invariant reads it as a full game that cannot. That is an upstream defect,
    reported rather than patched from here. This test asserts only the property
    this module owns — the card survives it and says so — so it keeps passing on
    the day the default is corrected.
    """
    tip = now + timedelta(hours=6)
    payload = _event(
        "evt-halves",
        home="Duke Blue Devils",
        away="Kansas Jayhawks",
        commence=tip,
        books=[
            _book("draftkings", [
                {"key": "h2h_h2", "outcomes": [
                    {"name": "Duke Blue Devils", "price": -120},
                    {"name": "Kansas Jayhawks", "price": 100}]},
            ])
        ],
    )
    halves = GC.board_from_payloads([payload], competition=CBB)

    run = GC.run_card(
        halves, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive",
        matchups={"evt-halves": a_matchup()}, now=lambda: now,
    )

    assert run.identity.reconciles(), run.identity.summary_line()
    assert run.opinions.wagers == 2
    assert run.opinions.priced == 2 or any(
        "distribution" in reason for reason in run.opinions.declined
    ), run.opinions.declined
    # Either way the price itself is frozen: it is evidence, and reachability
    # and closing-line movement are measured from it later.
    assert len(forward_evidence.read_snapshot(run.snapshot_path)) == 2


def test_a_matchup_the_ratings_module_refuses_to_price_is_not_priced(board, day):
    """Graph connectivity is an identifiability problem, not a nuisance. An
    unpriced game is an honest output."""
    wagers, _, _ = _wagers_for(board, day)

    probabilities, census = GC.opinions_for(
        wagers,
        {"evt-cardable": a_matchup(priceable=False, unpriceable_reason="disconnected")},
        day=day,
    )

    assert probabilities == {}
    assert any("refuses to price" in reason for reason in census.declined)


def test_with_no_ratings_module_every_wager_is_no_opinion_and_says_so(
    board, day, tmp_path
):
    """The state of this lab today. `no opinion` is not a probability of zero
    and it is not the model declining to find value."""
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive", policy=a_policy("moneyline"),
    )

    assert run.opinions.priced == 0
    assert run.identity.no_opinion > 0
    assert "`models/ratings.py` is not" in GC.render_card(run)


def test_a_player_prop_is_priced_frozen_and_settled_but_never_selected(day):
    """The exact analogue of the NHL lab's goalie saves. It is not a pass, an
    avoid or a no-value call."""
    from cbb_betting_lab.gates import Availability, availability_note

    note = availability_note(Availability.NO_REPORT)

    assert "cannot produce a selection" in note
    assert note in GC.render_card(
        GC.CardRun(
            competition=CBB, slate_date=day, card_slot="morning", generated_at="",
            board=GC.board_from_payloads([], competition=CBB),
            policy=StagingProviderPolicy(), placement=GC.Placement(),
            opinions=GC.OpinionCensus(), result=SelectionResult(),
            identity=GC.reconcile(SelectionResult(), unparseable=0),
            tip=GC.TipCensus(),
        )
    )


# ---------------------------------------------------------------------------
# Correlation and exposure
# ---------------------------------------------------------------------------


def test_one_game_is_one_position_and_the_edges_are_never_summed(
    board, day, tmp_path, now
):
    """Spread, moneyline, team total and game total on one game are one event
    seen four ways. The card reports exposure per game and per slate and never
    prints a sum."""
    run = GC.run_card(
        board,
        competition=CBB,
        day=day,
        card_slot="morning",
        archive_dir=tmp_path / "archive",
        policy=a_policy("moneyline", "spread", "total_points", "team_total"),
        matchups={"evt-cardable": a_matchup()},
        now=lambda: now,
    )
    text = GC.render_card(run)

    assert len(run.selections) <= 1, "One game may carry one position."
    assert run.result.exposure.per_game_cap == 1
    if run.result.bar_counts.get(Bar.CORRELATED_GAME.value):
        assert "a position is already taken on this game" in text
    edges = [float(s["edge"]) for s in run.selections]
    if len(edges) > 1:
        assert f"{sum(edges):+.2%}" not in text
    for banned in ("total edge", "combined edge", "sum of the edges"):
        assert banned not in text.casefold()


def test_the_exposure_caps_are_declared_in_advance_and_printed(board, day, tmp_path):
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive",
    )

    assert "the cap is 1 per game and 20 per slate" in GC.render_card(run)


# ---------------------------------------------------------------------------
# Zero email
# ---------------------------------------------------------------------------


def test_the_card_comment_mentions_nobody(board, day, tmp_path):
    """An `@mention` overrides an ignored repository subscription, so one
    without the other does nothing. The workflow greps for this and fails the
    run; this catches it one step earlier."""
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive",
    )

    assert GC.mentions_nobody(GC.render_comment(run))
    assert GC.mentions_nobody(GC.render_card(run))


def test_a_comment_that_would_email_cooper_is_refused_rather_than_scrubbed():
    """Refused, because removing the `@` would mean altering a name and this lab
    does not alter names. The freeze has already happened by then."""
    with pytest.raises(GC.CardWouldEmail, match="@cooperross399"):
        GC.guard_mentions_nobody("Ready for review by @cooperross399.")

    assert GC.guard_mentions_nobody("An e-mail address is not a mention: a@b.com")


def test_the_renderers_mention_regex_is_the_workflows_own():
    workflow = (
        REPO / ".github" / "workflows" / "cbb-gameday-refresh.yml"
    ).read_text(encoding="utf-8")

    assert GC._MENTION.pattern in workflow, (
        "The renderer and the workflow must refuse the same strings. A "
        "renderer that is laxer than the grep publishes a card the workflow "
        "then fails on, with the mention already written to disk."
    )


# ---------------------------------------------------------------------------
# Rehearsal
# ---------------------------------------------------------------------------


def test_a_rehearsal_labels_itself_and_cannot_reach_the_card_feed(
    board, day, tmp_path, capsys, no_network, no_credential
):
    """It writes to its own archive, which the workflow neither restores nor
    publishes, and its decision word is its own so a rehearsal's outcome can
    never be read as a card's."""
    staged = stage_to_disk(board, tmp_path, day)
    archive = tmp_path / "archive"
    status = run_script(
        "--card-slot", "evening",
        "--slate-date", day,
        "--rehearsal",
        "--staged-board", str(staged),
        "--archive-dir", str(archive),
        "--output-dir", str(tmp_path / "outputs"),
        "--raw-dir", str(tmp_path / "raw"),
    )
    out = capsys.readouterr().out
    card = (tmp_path / "outputs" / "cbb_gameday_card.md").read_text(encoding="utf-8")

    assert status == 0, out
    assert card.startswith(f"# {GC.REHEARSAL_LABEL}")
    assert out.rstrip().endswith(f"decision={GC.Decision.REHEARSAL.value}")
    assert not (archive / forward_evidence.SNAPSHOT_DIRNAME).exists(), (
        "A rehearsal wrote into the archive the workflow publishes."
    )
    assert (
        archive / GC.REHEARSAL_ARCHIVE_SEGMENT / day
        / forward_evidence.SNAPSHOT_DIRNAME / f"{day}.csv"
    ).is_file()


@pytest.mark.parametrize(
    "when,extra",
    [
        # Backwards: the snapshot's name would say its opinions were frozen
        # before results that already existed.
        ("2020-01-01", ("--live",)),
        ("2020-01-01", ()),
        # Forwards, which is worse and does not need a credential: the snapshot
        # is still standing when that day arrives, so the real run appends
        # nothing for those wagers and the first opinion of the night is one
        # taken before anybody knew who was playing.
        ("2099-01-01", ()),
    ],
)
def test_any_day_but_today_is_refused_without_rehearsal(
    when, extra, tmp_path, capsys, no_network, no_credential
):
    """Refused before anything is fetched, read or frozen, in both directions."""
    status = run_script(
        *extra,
        "--card-slot", "morning",
        "--slate-date", when,
        "--archive-dir", str(tmp_path / "archive"),
        "--output-dir", str(tmp_path / "outputs"),
        "--raw-dir", str(tmp_path / "raw"),
    )
    captured = capsys.readouterr()

    assert status == 2
    assert f"Refusing to card {when}" in captured.err
    assert captured.out.rstrip().endswith(f"decision={GC.Decision.REFUSED.value}")
    assert not (tmp_path / "archive").exists()


# ---------------------------------------------------------------------------
# The credit cap and the quota
# ---------------------------------------------------------------------------


class FakeResponse:
    def __init__(self, payload, headers):
        self.status_code = 200
        self._payload = payload
        self.headers = headers

    def json(self):
        return self._payload


class FakeProvider:
    """Enough of `OddsApiProvider` to drive the script without a socket."""

    remaining = "10"

    def __init__(self, competition, **kwargs):
        self.competition = competition
        self.regions = odds_api.DEFAULT_REGIONS
        self.calls: list[str] = []

    def quota(self):
        self.calls.append("quota")
        return {"x-requests-remaining": self.remaining}

    def list_events(self):
        self.calls.append("list_events")
        return []

    def fetch_bulk(self, markets, *, spend, credit_cap):
        self.calls.append("fetch_bulk")
        return []

    def fetch_event_odds(self, event_id, markets, *, spend, credit_cap):
        self.calls.append("fetch_event_odds")
        return {}


def test_the_live_path_runs_end_to_end_against_a_provider_that_answers(
    payloads_for_today, today, tmp_path, monkeypatch, capsys, no_network, no_credential
):
    """The path the workflow actually takes, with the socket layer closed.

    The offline `--staged-board` path proves the card can be rendered; this
    proves the branch that *reaches for the provider* also reaches the freeze —
    quota check, bulk call, per-event stage, staging write, gates, snapshot,
    card. A live path that only ever runs on a game day is a path that debuts
    in production.
    """
    payloads = payloads_for_today

    class AnsweringProvider(FakeProvider):
        remaining = "5000000"

        def list_events(self):
            self.calls.append("list_events")
            return [
                {k: v for k, v in event.items() if k != "bookmakers"}
                for event in payloads
            ]

        def fetch_bulk(self, markets, *, spend, credit_cap):
            self.calls.append("fetch_bulk")
            spend.record({"x-requests-last": "6"}, fallback=6)
            return payloads

        def fetch_event_odds(self, event_id, markets, *, spend, credit_cap):
            self.calls.append("fetch_event_odds")
            spend.record({"x-requests-last": "0"}, fallback=0)
            return {}

    monkeypatch.setattr(odds_api, "OddsApiProvider", AnsweringProvider)
    status = run_script(
        "--live",
        "--card-slot", "morning",
        "--credit-cap", "40000",
        "--archive-dir", str(tmp_path / "archive"),
        "--output-dir", str(tmp_path / "outputs"),
        "--staging-dir", str(tmp_path / "staging"),
        "--raw-dir", str(tmp_path / "raw"),
    )
    out = capsys.readouterr().out

    assert status == 0, out
    assert out.rstrip().endswith(f"decision={GC.Decision.NO_SELECTIONS.value}")
    assert (tmp_path / "outputs" / "cbb_gameday_card.md").is_file()
    # Every book's quote reaches staging, which the card cannot read; the freeze
    # keeps one row per wager at the best price.
    staged = list((tmp_path / "staging").rglob("*.csv"))
    assert staged, "The board was not staged."
    assert len(pd.read_csv(staged[0])) > len(
        forward_evidence.read_snapshot(
            forward_evidence.snapshot_path(tmp_path / "archive", today)
        )
    )


def test_a_run_that_starts_with_less_quota_than_its_cap_refuses(
    tmp_path, monkeypatch, capsys, no_network, no_credential
):
    """Refusing loses a night. Starting short freezes the games the run happened
    to reach — and in this sport the fetch works in tip order, so a starved run
    keeps the early games and drops the late ones, which is the West Coast,
    low-major end of the board this lab was built to look at."""
    monkeypatch.setattr(odds_api, "OddsApiProvider", FakeProvider)
    status = run_script(
        "--live",
        "--card-slot", "morning",
        "--credit-cap", "40000",
        "--archive-dir", str(tmp_path / "archive"),
        "--output-dir", str(tmp_path / "outputs"),
        "--raw-dir", str(tmp_path / "raw"),
    )
    captured = capsys.readouterr()

    assert status == 1
    assert "Refusing to start" in captured.err
    assert captured.out.rstrip().endswith(f"decision={GC.Decision.REFUSED.value}")
    assert not (tmp_path / "archive").exists()


def test_the_cap_is_charged_from_the_measured_header_not_the_estimate(now):
    """The NHL lab capped a run at 200,000 and spent 289,984 by estimating from
    markets asked rather than markets returned, while its test asserted the cap
    could not be breached."""
    seen: list[dict] = []

    def requester(url, *, params, timeout):
        seen.append(dict(params))
        if url.endswith("/events"):
            return FakeResponse([], {})
        return FakeResponse(board_payloads(now), {"x-requests-last": "417"})

    provider = odds_api.OddsApiProvider(
        CBB, environment={"CBB_ODDS_API_KEY": "x" * 20}, requester=requester
    )
    board = GC.fetch_board(
        provider, competition=CBB, credit_cap=40_000, day="2027-01-12"
    )

    assert board.spend.credits_spent == 417
    assert board.spend.credits_estimated == 6, (
        "The pessimistic bound is three markets by two regions; the charge is "
        "the header. Both are kept so the gap between them is readable."
    )


def test_the_per_event_stage_is_skipped_whole_rather_than_truncated(now):
    """A stage stopped partway through leaves a tip-ordered prefix, and a
    starved fetch and an unquoted market look identical in a coverage report."""

    def requester(url, *, params, timeout):
        if url.endswith("/events"):
            return FakeResponse(
                [
                    {
                        "id": "evt-cardable",
                        "commence_time": _iso(now + timedelta(hours=6)),
                        "home_team": "Duke Blue Devils",
                        "away_team": "Kansas Jayhawks",
                    }
                ],
                {},
            )
        return FakeResponse(board_payloads(now), {"x-requests-last": "6"})

    provider = odds_api.OddsApiProvider(
        CBB, environment={"CBB_ODDS_API_KEY": "x" * 20}, requester=requester
    )
    board = GC.fetch_board(
        provider, competition=CBB, credit_cap=10, day="2027-01-12"
    )

    assert board.per_event_asked is False
    assert board.per_event_complete is True
    assert any("not asked for" in note for note in board.notes)
    assert any("says nothing about whether those markets are quoted" in n for n in board.notes)


def test_an_incomplete_per_event_stage_is_staged_but_never_frozen(
    board, day, tmp_path, now
):
    """The rows were paid for and they are evidence; they are not a stratum.
    A tip-ordered prefix written into the ledger is a biased subset wearing the
    name of a night."""
    board.per_event_complete = False
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive", now=lambda: now,
    )
    frozen = forward_evidence.read_snapshot(run.snapshot_path)

    assert set(frozen["market"]) <= GC.BULK_MARKETS
    assert "team_total" in set(board.rows["market"]), (
        "The fixture must carry a per-event market for this test to mean "
        "anything."
    )
    assert "team_total" not in set(frozen["market"])


def test_the_frozen_columns_are_a_subset_of_the_staged_ones_by_name():
    """Named, never sliced off somebody else's tuple. A positional slice
    silently freezes the wrong field the day that tuple is reordered, and a
    snapshot is the one artefact here that cannot be rebuilt."""
    assert set(GC.FROZEN_COLUMNS) < set(staging.STAGED_COLUMNS)
    assert "provider_key" not in GC.FROZEN_COLUMNS
    assert set(GC.FROZEN_COLUMNS) <= set(forward_evidence.SNAPSHOT_COLUMNS) | {
        "slate_date"
    }, (
        "Every frozen column must be one the snapshot carries; `slate_date` is "
        "the exception, and only because the snapshot names its day in the "
        "filename and in `snapshot_date`."
    )


def test_the_bulk_markets_are_derived_from_the_registry():
    """Never named here. A market list written twice drifts, and the direction
    a drifted copy goes is not the conservative one."""
    assert GC.BULK_MARKETS == {"moneyline", "spread", "total_points"}
    assert "team_total" not in GC.BULK_MARKETS, (
        "`team_totals` is not a bulk-safe key; asking for it there makes the "
        "provider refuse the whole request with a 422 that names nothing."
    )


# ---------------------------------------------------------------------------
# Placement
# ---------------------------------------------------------------------------


def test_a_missing_schedule_cache_leaves_every_game_unplaced_and_says_so(
    board, day, tmp_path
):
    """Degrades rather than empties. An unstratified number is never reported as
    a Division I headline."""
    placement = GC.place_games(board, competition=CBB, day=day, raw_dir=tmp_path)

    assert placement.tiers == {}
    assert "unplaced" in placement.summary_line()
    assert "No cached schedule" in placement.note


def test_tiers_come_from_seasons_strictly_before_the_one_being_priced():
    """A team's tier in November 2026 is what its 2025-26 non-conference record
    said, not what its 2026-27 record will say."""
    raw = REPO / "data" / "raw"
    if not any((raw / CBB.data_dir_segment / "schedules").glob("mbb_schedule_*.parquet")):
        pytest.skip("No cached schedule locally; the empty-cache case covers CI.")
    placement = GC.place_games(
        GC.board_from_payloads([], competition=CBB),
        competition=CBB, day="2027-01-12", raw_dir=raw,
    )

    assert placement.table is not None
    assert placement.seasons_used
    assert max(placement.seasons_used) < 2027, (
        "Tiering off the season being priced leaks its own results into the "
        "stratum every game lands in."
    )


def test_a_placed_game_carries_its_tier_into_the_frozen_row(board, day, tmp_path, now):
    placement = GC.Placement(tiers={"evt-cardable": Tier.LOW_MAJOR})
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive", placement=placement, now=lambda: now,
    )
    frozen = forward_evidence.read_snapshot(run.snapshot_path)

    assert set(frozen.loc[frozen["event_id"] == "evt-cardable", "tier"]) == {
        Tier.LOW_MAJOR.value
    }


# ---------------------------------------------------------------------------
# `Selections changed`
# ---------------------------------------------------------------------------


def test_the_changed_marker_does_not_fire_when_there_is_nothing_to_compare(
    board, day, tmp_path
):
    """A notification that fires when nothing happened stops being read long
    before it stops being sent."""
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive",
    )
    text = GC.render_card(run)

    assert run.selections_changed is None
    assert GC.SELECTIONS_CHANGED not in text
    assert "nothing is claimed about whether the selections changed" in text


def test_the_changed_marker_fires_only_on_a_change(board, day, tmp_path):
    run = GC.run_card(
        board, competition=CBB, day=day, card_slot="morning",
        archive_dir=tmp_path / "archive", previous_fingerprint="deadbeefdeadbeef",
    )
    same = GC.run_card(
        board, competition=CBB, day=day, card_slot="evening",
        archive_dir=tmp_path / "archive", previous_fingerprint=run.fingerprint,
    )

    assert GC.SELECTIONS_CHANGED in GC.render_card(run)
    assert GC.SELECTIONS_CHANGED not in GC.render_card(same)


def test_the_run_records_its_fingerprint_for_the_next_run(
    board_for_today, today, tmp_path, capsys, no_network, no_credential
):
    day = today
    staged = stage_to_disk(board_for_today, tmp_path, day)
    run_script(
        "--card-slot", "morning",
        "--staged-board", str(staged),
        "--archive-dir", str(tmp_path / "archive"),
        "--output-dir", str(tmp_path / "outputs"),
        "--raw-dir", str(tmp_path / "raw"),
    )
    capsys.readouterr()
    state = json.loads(
        (tmp_path / "outputs" / "cbb_card_state.json").read_text(encoding="utf-8")
    )

    assert state["slate_date"] == day
    assert state["card_slot"] == "morning"
    assert len(state["fingerprint"]) == 16


# ---------------------------------------------------------------------------
# Helpers used above
# ---------------------------------------------------------------------------


def _wagers_for(board: GC.Board, day: str, *, force_day: bool = False):
    """The wagers a card would price, built through the one keying function."""
    from cbb_betting_lab.reports.card_pricing import build_wagers, default_key_for

    rows = board.rows
    if force_day:
        rows = rows.assign(slate_date=day)
    else:
        rows = rows.loc[rows["slate_date"].astype(str) == str(day)]
    return build_wagers(
        rows.reset_index(drop=True),
        competition=CBB,
        key_for=default_key_for(CBB),
    )


def test_the_card_never_claims_the_RUN_was_healthy():
    """The card is one step of a workflow and cannot see the others.

    Found by dispatching the real thing: a comment reading *"This run was
    clean."* was published beside a `latest_status.json` reading
    `"degraded": "true"`, both from the same run. The feed refresh before this
    step had failed and settlement after it had failed; neither is visible from
    inside the card.

    The brief's rule is that ONE step decides, so the summary, the status file
    and the publish guard cannot disagree. A second opinion rendered here is
    not a second check — it is a disagreement the reader has to arbitrate, and
    the reader is a scheduled task that copies the text verbatim.
    """
    from cbb_betting_lab.reports import gameday_card as GC

    source = Path(GC.__file__).read_text(encoding="utf-8")
    for claim in ("This run was clean", "this run was clean"):
        assert claim not in source, (
            "The card asserts the run's health. It can only speak for the card."
        )
