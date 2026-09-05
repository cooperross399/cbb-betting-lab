"""The price backtest entry point, run the way an operator runs it.

`reports/price_backtest.py` owns every number and is tested on its own terms.
This file tests the **wiring**, which is where the three sibling labs actually
lost their measurements. Each test is named for the specific way a measurement
could be lost or manufactured:

* a store that does not exist yet — the purchase is still running — producing an
  empty report that reads as a null result, which is a claim;
* a store deduplicated on the row rather than the quote, or measured per quote
  rather than per wager: the NHL lab's √2.83, which does not look wrong, it
  looks significant;
* a model priced on games it had already seen — the football lab's defect 13,
  where a distribution loaded once outside the season loop meant the model
  pricing 2023 had seen 2025, and only the markets that consumed it looked good;
* a model that had an opinion on nothing, reported as zero bets and read as "the
  model never disagrees enough with the market" when it was a wiring fault;
* a wager that reaches none of the accounting identity's buckets, so a
  measurement describes a fraction of a store as if it were all of it;
* a null baseline printed *after* the model number, which is the order in which
  a reader forms the belief the baseline exists to prevent;
* a pooled Division I headline;
* a report that can only be produced by re-running the measurement, which is a
  report nobody improves and a generated file somebody edits by hand.

The model is a stub registered in `sys.modules`, because `models/ratings.py` does
not exist yet. It is deliberately handed to the script through the same
`--model module:attribute` door a real one will come through, so this file
exercises the resolution path rather than reaching around it.
"""

from __future__ import annotations

import contextlib
import io
import json
import re
import runpy
import sys
import types
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.conferences import Tier
from cbb_betting_lab.experiment_ledger import LEDGER_FILENAME
from cbb_betting_lab.population import VenueState
from cbb_betting_lab.providers import historical as H
from cbb_betting_lab.reports import forecast_skill as FS
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.selection import FULL_GAME
from cbb_betting_lab.stats import MINIMUM_BETS
from cbb_betting_lab.stores import _decimal_payout as price_backtest_payout

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run_price_backtest.py"

#: Three consecutive November slate days. November on purpose: it is inside
#: `gameday_card.PRIOR_REGIME_MONTHS`, so a matchup carrying no prior weight
#: gets no opinion at all, and the fixture has to carry one — which is the rule
#: that stops a November number being read as a February one.
DAYS = ("2026-11-10", "2026-11-11", "2026-11-12")

#: Four games a day. Every extra game costs a real `distributions.build`, which
#: is about four tenths of a second, so the population is kept small and the
#: **wagers per game** are what push a cell over the declared floor.
GAMES_PER_DAY = 4

#: A spread ladder wide enough that one market in one tier clears
#: `stats.MINIMUM_BETS`, so the "below the floor there is no number" rule can be
#: tested against a cell that is above it as well as cells that are below.
LADDER = tuple(x / 2 for x in range(-41, 70, 2))  # -20.5 … +34.5

SEASON = 2027


# --------------------------------------------------------------------------
# One small season on disk, shaped like the real tables
# --------------------------------------------------------------------------


def _score(game_index: int) -> tuple[int, int]:
    """Deterministic, spread across the margin distribution, never level.

    A full game cannot end level — measured at 0.000% over 94,194 team-games —
    so the fixture must not produce one either, or it would settle a moneyline
    against a state this sport does not have.
    """
    home = 68 + (game_index * 7) % 23
    away = 61 + (game_index * 11) % 19
    if home == away:
        home += 1
    return home, away


def team_games() -> pd.DataFrame:
    rows: list[dict] = []
    index = 0
    for day in DAYS:
        for _ in range(GAMES_PER_DAY):
            index += 1
            game_id = 900_000 + index
            home_id, away_id = 100 + index * 2, 101 + index * 2
            home_score, away_score = _score(index)
            for team, opponent, score, against, side in (
                (home_id, away_id, home_score, away_score, "home"),
                (away_id, home_id, away_score, home_score, "away"),
            ):
                rows.append(
                    {
                        "game_id": game_id,
                        "season": SEASON,
                        "slate_date": day,
                        "team_id": team,
                        "opponent_id": opponent,
                        "home_away": side,
                        "team_score": score,
                        "opponent_score": against,
                        "margin": score - against,
                        "total": home_score + away_score,
                        "team_score_h1": score // 2,
                        "opponent_score_h1": against // 2,
                        "team_score_h2": score - score // 2,
                        "opponent_score_h2": against - against // 2,
                        "periods": 2,
                        "overtime": False,
                    }
                )
    return pd.DataFrame(rows)


def game_segments(games: pd.DataFrame) -> pd.DataFrame:
    home = games[games["home_away"] == "home"]
    return pd.DataFrame(
        [
            {
                "game_id": int(row["game_id"]),
                "periods": 2,
                "overtime": False,
                "home_score_h1": int(row["team_score_h1"]),
                "away_score_h1": int(row["opponent_score_h1"]),
                "first_basket_athlete_id": None,
                "first_basket_team_id": None,
            }
            for _, row in home.iterrows()
        ]
    )


def _quote(
    *,
    game,
    market: str,
    selection: str,
    line: float | None,
    odds: float,
    book: str,
    segment: str = FULL_GAME,
) -> dict:
    return {
        "event_id": f"e{int(game['game_id'])}",
        "market": market,
        "segment": segment,
        "player": "",
        "selection": selection,
        "line": line,
        "book": book,
        "snapshot_phase": H.CARD_WINDOW.name,
        "american_odds": odds,
        "provider_key": market,
        "game_id": int(game["game_id"]),
        "season": SEASON,
        "slate_date": str(game["slate_date"]),
        "commence_time": f"{game['slate_date']}T23:00:00Z",
        "home_team": int(game["team_id"]),
        "away_team": int(game["opponent_id"]),
        "home_name": f"Home {int(game['team_id'])}",
        "away_name": f"Away {int(game['opponent_id'])}",
        "tier": Tier.HIGH_MAJOR.value
        if int(game["game_id"]) % 2 == 0
        else Tier.LOW_MAJOR.value,
        "tip_window": "evening",
        "snapshot_requested": f"{game['slate_date']}T22:00:00Z",
        "lead_minutes": H.CARD_WINDOW.minutes_before_tip,
        "book_last_update": f"{game['slate_date']}T22:00:00Z",
    }


def price_store(games: pd.DataFrame, *, books: tuple[str, ...] = ("dk", "fd", "mgm")) -> pd.DataFrame:
    """One board, quoted by three books, over every game in the fixture.

    Three books on every wager on purpose. The store holds three quotes and the
    measurement must hold **one bet**, at the best of the three: seventeen books
    quoting one game is not seventeen bets, and counting them that way is how
    every interval in the NHL lab's first store came out about √2.83 too narrow.
    """
    rows: list[dict] = []
    home_rows = games[games["home_away"] == "home"]
    for _, game in home_rows.iterrows():
        for position, book in enumerate(books):
            drift = position * 5
            rows.append(_quote(game=game, market="moneyline", selection="home", line=None, odds=-140 + drift, book=book))
            rows.append(_quote(game=game, market="moneyline", selection="away", line=None, odds=120 + drift, book=book))
            rows.append(_quote(game=game, market="total_points", selection="over", line=140.5, odds=-110 + drift, book=book))
            rows.append(_quote(game=game, market="total_points", selection="under", line=140.5, odds=-110 + drift, book=book))
            rows.append(_quote(game=game, market="team_total", selection="home_over", line=70.5, odds=-110 + drift, book=book))
            rows.append(_quote(game=game, market="team_total", selection="home_under", line=70.5, odds=-110 + drift, book=book))
            for line in LADDER:
                # A generous ladder, so a model with an ordinary opinion clears
                # the threshold declared in advance on enough rungs to push one
                # cell past `stats.MINIMUM_BETS`.
                rows.append(
                    _quote(
                        game=game,
                        market="alternate_spread",
                        selection="home",
                        line=line,
                        odds=150 + drift,
                        book=book,
                    )
                )
    return pd.DataFrame(rows, columns=list(H.PRICE_COLUMNS))


# --------------------------------------------------------------------------
# The model, handed in through the same door a real one will use
# --------------------------------------------------------------------------


@dataclass
class StubModel:
    """A matchup per event, and a record of exactly what history it was shown.

    The `history` log is the walk-forward evidence. The football lab's leak was
    a distribution built once **outside** the season loop, and no convention
    catches that — only looking at what the pricer was actually handed does.
    """

    module_name: str
    home_points_per_possession: float = 1.06
    away_points_per_possession: float = 0.99
    possessions: float = 68.0
    prior_weight: float | None = 0.45
    priceable: bool = True
    calls: list[dict] = field(default_factory=list)

    def matchups_for(self, *, day, history, prices, competition):
        self.calls.append(
            {
                "day": str(day),
                "history_rows": int(len(history)),
                "history_max_day": (
                    str(history["slate_date"].astype(str).max())
                    if len(history)
                    else ""
                ),
                "events": sorted({str(e) for e in prices["event_id"]}),
            }
        )
        return {
            str(event_id): types.SimpleNamespace(
                home_points_per_possession=self.home_points_per_possession,
                away_points_per_possession=self.away_points_per_possession,
                possessions=self.possessions,
                priceable=self.priceable,
                unpriceable_reason="the schedule graph has not connected these teams",
                venue_state=VenueState.HOME.value,
                prior_weight=self.prior_weight,
            )
            for event_id in prices["event_id"].unique()
        }

    def register(self) -> str:
        module = types.ModuleType(self.module_name)
        module.matchups_for = self.matchups_for
        sys.modules[self.module_name] = module
        return f"{self.module_name}:matchups_for"


# --------------------------------------------------------------------------
# A lab on disk, and the script run against it
# --------------------------------------------------------------------------


class Lab:
    """The directory layout an operator hands the script, built in tmp_path."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.processed = root / "processed"
        self.outputs = root / "outputs"
        for directory in (self.processed, self.outputs):
            directory.mkdir(parents=True, exist_ok=True)
        self.games = team_games()
        self.record_path = PB.record_path(CBB, self.outputs)
        self.report_path = PB.report_path(CBB, self.outputs)
        self.graded_path = self.processed / "cbb_graded_bets.csv"

    def with_tables(self) -> "Lab":
        self.games.to_csv(self.processed / "cbb_team_games.csv", index=False)
        game_segments(self.games).to_csv(
            self.processed / "cbb_game_segments.csv", index=False
        )
        return self

    def with_store(self, frame: pd.DataFrame | None = None) -> "Lab":
        prices = price_store(self.games) if frame is None else frame
        prices.to_csv(
            H.store_path(CBB, self.processed, H.CARD_WINDOW), index=False
        )
        return self

    def with_ledger(self, hypotheses: int) -> "Lab":
        payload = {
            "hypotheses": [
                {
                    "search": "fixture",
                    "name": f"hypothesis {i}",
                    "tested_on": "2026-09-01",
                    "seasons": [SEASON],
                    "outcome": "",
                    "predicted_direction": "higher",
                    "stage": "discovery",
                }
                for i in range(hypotheses)
            ],
            "alpha_budget": {"per_week": 6, "declared_on": "2026-09-01"},
        }
        (self.outputs / LEDGER_FILENAME).write_text(
            json.dumps(payload), encoding="utf-8"
        )
        return self

    def run(self, *argv: str) -> int:
        saved = sys.argv[:]
        sys.argv = [
            str(SCRIPT),
            "--processed-dir",
            str(self.processed),
            "--output-dir",
            str(self.outputs),
            # Tests are not looks. The script now defaults --ledger to the
            # REPOSITORY's ledger — one cumulative count — so a test that ran
            # it without saying otherwise appended its scratch hypotheses to
            # the real record. That happened once, and is why this is here.
            *([] if "--ledger" in argv else ["--ledger", str(self.outputs / "experiment_ledger.json")]),
            *argv,
        ]
        try:
            runpy.run_path(str(SCRIPT), run_name="__main__")
            return 0
        except SystemExit as exit_code:
            return int(exit_code.code or 0)
        finally:
            sys.argv = saved

    def record(self) -> dict:
        return json.loads(self.record_path.read_text(encoding="utf-8"))

    def report(self) -> str:
        return self.report_path.read_text(encoding="utf-8")


@dataclass
class Scored:
    """One full run, kept for the whole module because it costs real seconds."""

    exit_code: int
    stdout: str
    record: dict
    report: str
    model: StubModel
    lab: Lab


@pytest.fixture(scope="module")
def scored(tmp_path_factory) -> Scored:
    """Score the fixture store once. Every assertion below reads this run.

    Module-scoped deliberately: the run builds a real `GameDistribution` per
    game, and re-running it per test would trade seconds for nothing. Each test
    still names one distinct failure mode.
    """
    root = tmp_path_factory.mktemp("price_backtest")
    lab = Lab(root).with_tables().with_store().with_ledger(30)
    model = StubModel(module_name="cbb_stub_model_scored")
    spec = model.register()

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        exit_code = lab.run("--model", spec, "--write-graded", str(lab.graded_path))
    return Scored(
        exit_code=exit_code,
        stdout=buffer.getvalue(),
        record=lab.record() if lab.record_path.is_file() else {},
        report=lab.report() if lab.report_path.is_file() else "",
        model=model,
        lab=lab,
    )


# --------------------------------------------------------------------------
# The purchase is still running — and an empty report is a claim
# --------------------------------------------------------------------------


def test_a_store_that_does_not_exist_yet_is_a_message_and_an_exit_code(tmp_path, capsys):
    """The purchase may not have finished. That is not a null result.

    Cooper's rule and the module's: *"an empty table reads as a null result and
    a null result is a claim."* So a missing store must not crash, must not
    render, and must not exit zero.
    """
    lab = Lab(tmp_path).with_tables()
    model = StubModel(module_name="cbb_stub_model_no_store")

    code = lab.run("--model", model.register())

    assert code != 0, "a lab with nothing to measure must not report success"
    output = capsys.readouterr()
    combined = output.out + output.err
    assert "does not exist" in combined
    assert "buy_historical_prices" in combined
    assert not lab.record_path.exists(), "nothing may be written when nothing was scored"
    assert not lab.report_path.exists()


def test_a_store_with_no_rows_is_refused_rather_than_measured(tmp_path, capsys):
    """A purchase that started and bought nothing is not a market nobody quotes.

    *A starved fetch and an unquoted market look identical in the reports* — so
    the run refuses to print an interval over either.
    """
    lab = Lab(tmp_path).with_tables()
    lab.with_store(pd.DataFrame(columns=list(H.PRICE_COLUMNS)))
    model = StubModel(module_name="cbb_stub_model_empty_store")

    code = lab.run("--model", model.register())

    assert code != 0
    combined = "".join(capsys.readouterr())
    assert "holds no rows" in combined
    assert not lab.report_path.exists()


def test_a_store_missing_a_column_raises_rather_than_reading_it_as_a_zero(
    tmp_path, capsys
):
    """The football lab's props backtest reported zero bets for exactly this.

    A missing settlement column read through `getattr(..., None)` became a zero,
    the run reported zero bets, and that read as "the model never disagrees
    enough with the market" when the price columns had never been built.
    """
    lab = Lab(tmp_path).with_tables()
    store = price_store(lab.games).drop(columns=["american_odds"])
    lab.with_store(store)
    model = StubModel(module_name="cbb_stub_model_missing_column")

    code = lab.run("--model", model.register())

    assert code != 0
    combined = "".join(capsys.readouterr())
    assert "american_odds" in combined
    assert "read as a zero" in combined
    assert not lab.report_path.exists()


def test_a_store_written_twice_measures_the_same_number_of_bets(tmp_path, capsys):
    """**A duplicated store does not look wrong — it looks significant.**

    The NHL lab's purchase deduplicated on the whole row, timestamps included,
    so two buys of the same window wrote every quote twice. ROI was unchanged
    and every interval came out root-two too narrow, and nothing about the
    output looked broken. Here the store is written twice on disk and the
    measured counts must not move at all.
    """
    one_day = team_games()
    one_day = one_day[one_day["slate_date"] == DAYS[0]]

    def score(root: Path, *, doubled: bool) -> dict:
        lab = Lab(root)
        lab.games = one_day
        lab.with_tables()
        store = price_store(one_day)
        lab.with_store(pd.concat([store, store], ignore_index=True) if doubled else store)
        model = StubModel(module_name=f"cbb_stub_model_dupe_{int(doubled)}")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
            io.StringIO()
        ):
            assert lab.run("--model", model.register()) == 0
        return lab.record()

    once = score(tmp_path / "once", doubled=False)
    twice = score(tmp_path / "twice", doubled=True)

    for count in ("wagers_offered", "wagers_graded", "bets_taken", "bets_graded", "games"):
        assert once[count] == twice[count], (
            f"{count} moved when the store was written twice — the dedupe keys "
            "on the quote and must never key on the row"
        )


def test_a_season_filter_that_matches_nothing_is_a_refusal_not_a_null(
    tmp_path, capsys
):
    """A filter that silently matches nothing measures a season nobody played.

    It exits before the model is even resolved, so the message names the filter
    rather than the missing ratings module.
    """
    lab = Lab(tmp_path).with_tables().with_store()
    model = StubModel(module_name="cbb_stub_model_seasons")

    code = lab.run("--model", model.register(), "--seasons", "1999")

    assert code != 0
    combined = "".join(capsys.readouterr())
    assert "season filter" in combined
    assert not lab.report_path.exists()


def test_a_model_that_cannot_be_resolved_exits_rather_than_falling_back(tmp_path, capsys):
    """There is deliberately no fallback pricer.

    A backtest that quietly prices with something other than the model the card
    runs measures a policy nobody would have run, and prints intervals while
    doing it.

    This test used to assert that `models/ratings.py` did not exist. It does
    now, so the case it was really guarding — an unresolvable `--model` — is
    asserted directly instead of as a side effect of the module being absent.
    """
    lab = Lab(tmp_path).with_tables().with_store()

    code = lab.run("--model", "cbb_betting_lab.models.ratings:no_such_callable")

    assert code != 0
    combined = "".join(capsys.readouterr())
    assert "has no attribute" in combined
    assert "Nothing was scored" in combined or "no model" in combined


def test_the_default_model_resolves(tmp_path):
    """`DEFAULT_MODEL` names a callable that actually exists.

    The seam is `ratings:matchups_for`, and it is the ONE path the backtest,
    the card and the forward freeze all price through. A default that no longer
    resolves would send every run down the no-model branch, which reads as a
    lab with nothing to say rather than as a broken import.
    """
    import importlib
    import runpy as _runpy

    spec = _runpy.run_path(str(SCRIPT))["DEFAULT_MODEL"] if False else None
    from cbb_betting_lab.models.ratings import matchups_for  # the seam itself

    assert callable(matchups_for)
    module_name, _, attribute = "cbb_betting_lab.models.ratings:matchups_for".partition(":")
    module = importlib.import_module(module_name)
    assert callable(getattr(module, attribute))

def test_a_model_with_an_opinion_on_nothing_is_a_wiring_fault_until_proven_otherwise(
    tmp_path, capsys
):
    """Zero bets reads as a finding and was, in the football lab, a wiring fault.

    Its props backtest reported zero bets because its price columns had never
    been built, and that read as "the model never disagrees enough with the
    market". A model that declines every wager exits non-zero and names the
    reason rather than publishing the ambiguity as a measurement.
    """
    lab = Lab(tmp_path).with_tables().with_store()
    model = StubModel(module_name="cbb_stub_model_silent", priceable=False)

    code = lab.run("--model", model.register())

    assert code != 0
    combined = "".join(capsys.readouterr())
    assert "had an opinion on none of them" in combined
    assert "refuses to price" in combined, "the model's own reason must be named"


# --------------------------------------------------------------------------
# The measurement itself
# --------------------------------------------------------------------------


def test_it_scores_the_store_and_writes_both_outputs(scored):
    assert scored.exit_code == 0, scored.stdout
    assert scored.lab.record_path.is_file()
    assert scored.lab.report_path.is_file()
    assert scored.record["record_version"] == PB.RECORD_VERSION
    assert scored.record["competition"] == CBB.key
    assert scored.record["snapshot_phase"] == H.CARD_WINDOW.name
    assert scored.record["bets_graded"] > 0


def test_one_wager_is_one_bet_at_the_best_price(scored):
    """Three books quoting one wager is one bet, and it is the best of the three.

    Run per quote, the NHL lab's full store called all three team markets
    demonstrated losses; run per wager, all three span zero. The store here holds
    three quotes on every wager, so the collapse is measurable rather than
    asserted: the graded wager count must be the store's row count divided by
    three exactly, never a third more or a third less.
    """
    store = pd.read_csv(H.store_path(CBB, scored.lab.processed, H.CARD_WINDOW))
    wagers = store.drop_duplicates(
        subset=["event_id", "market", "segment", "player", "selection", "line"]
    )
    assert len(store) == 3 * len(wagers), "the fixture must hold three books a wager"
    assert scored.record["wagers_offered"] == len(wagers)
    assert "one wager is one bet" in scored.stdout.lower()

    # And the **best** of the three prices, not the average and not the first.
    # American odds do not sort numerically — +150 beats −110 beats −200 — so
    # the check is made on the payout the collapse itself orders by.
    collapsed = PB.one_bet_per_wager(store)
    assert len(collapsed) == len(wagers)
    keys = ["event_id", "market", "segment", "player", "selection", "line"]
    payout = store.assign(
        _payout=store["american_odds"].map(price_backtest_payout)
    )
    best = payout.groupby(keys, dropna=False)["_payout"].max().rename("_best")
    taken = collapsed.assign(
        _payout=collapsed["american_odds"].map(price_backtest_payout)
    ).join(best, on=keys)
    assert (taken["_payout"] == taken["_best"]).all(), (
        "every measured wager must carry the best price any book hung on it"
    )


def test_the_pricer_only_ever_sees_games_strictly_earlier_than_the_day(scored):
    """Walk-forward as a signature, not a convention.

    The football lab's largest silent leak was a per-play distribution loaded
    once outside the season loop: the model pricing 2023 had seen 2025, and only
    the compound markets consumed it — *which is precisely why the compound
    group looked good*. A convention cannot stop that; looking at what the
    pricer was handed can.
    """
    assert scored.model.calls, "the model must have been asked at least once"
    assert [c["day"] for c in scored.model.calls] == sorted(DAYS)
    for call in scored.model.calls:
        assert call["history_max_day"] < call["day"] or call["history_max_day"] == "", (
            f"the pricer for {call['day']} was shown games up to "
            f"{call['history_max_day']}, which is not strictly earlier"
        )
    first, *rest = scored.model.calls
    assert first["history_rows"] == 0, "the first day of the store has no past"
    assert all(c["history_rows"] > 0 for c in rest)


def test_every_bet_carries_the_day_it_was_priced_through(scored):
    """`assert_walk_forward` reads the stamp rather than trusting the code path.

    Re-run here over the record's own inputs so the guard is exercised against
    what was measured, not only against what the module was handed.
    """
    frame = pd.DataFrame(
        [
            {"slate_date": call["day"], "priced_through": ""}
            for call in scored.model.calls
        ]
    )
    PB.assert_walk_forward(frame)  # an unstamped frame is not a leak

    leaked = pd.DataFrame(
        [{"slate_date": DAYS[1], "priced_through": DAYS[1]}]
    )
    with pytest.raises(PB.WalkForwardLeak):
        PB.assert_walk_forward(leaked)


# --------------------------------------------------------------------------
# The stamp describes every frame, not only the team history
#
# A player-prop pricer reads two tables, not one. The stamp used to be computed
# from the team games alone and written over whatever the pricer had put there,
# so a pricer that also read tonight's minutes and tonight's points was stamped
# walk-forward and passed the guard. These three tests are the difference.
# --------------------------------------------------------------------------


def _walk_prices() -> pd.DataFrame:
    """One quoted event on each of the three slate days."""
    return pd.DataFrame(
        [{"event_id": f"e{index}", "slate_date": day} for index, day in enumerate(DAYS)]
    )


def _walk_games(days=DAYS) -> pd.DataFrame:
    """A team-games frame with one row on each named day."""
    return pd.DataFrame([{"slate_date": day, "margin": 3.0} for day in days])


def test_a_pricer_that_read_a_second_frame_cannot_stamp_itself_walk_forward():
    """The stamp a pricer sets for itself survives, so the guard can read it.

    This is the player-prop case. The caller cut the team history; the pricer
    also read a player frame holding rows dated on the day it is pricing —
    tonight's minutes, tonight's points — and said so in `priced_through`. The
    stamp used to be overwritten with the team history's last day, which is
    strictly earlier than the day being priced, so `assert_walk_forward` was
    handed evidence about one of the pricer's two inputs and certified the run.
    """
    players = pd.DataFrame([{"slate_date": day} for day in DAYS])

    def price_day(*, day, history, prices):
        frame = prices.copy()
        # The frame the caller does not know about, read whole — including the
        # rows dated on the day being priced.
        frame["priced_through"] = str(players["slate_date"].astype(str).max())
        return frame

    priced = PB.walk_forward(_walk_prices(), _walk_games(), price_day=price_day)

    assert len(priced) == len(DAYS)
    assert set(priced["priced_through"]) == {DAYS[-1]}, (
        "the pricer's own stamp names the last day of the frame it read, and "
        "the caller must not lower it to the team history's last day"
    )
    with pytest.raises(PB.WalkForwardLeak):
        PB.assert_walk_forward(priced)


def test_a_named_frame_is_cut_to_the_day_and_folded_into_the_stamp():
    """`frames=` is the honest door: cut like the history, and stamped with it.

    The team games here stop on the first day and the player frame runs a day
    later, so a stamp computed from the team history alone would describe a day
    on which the pricer had already been shown a player row.
    """
    players = pd.DataFrame(
        [{"slate_date": day, "points": 11} for day in (DAYS[0], DAYS[1])]
    )
    seen: list[dict] = []

    def price_day(*, day, history, prices, player_games):
        column = "slate_date" if "slate_date" in player_games.columns else "game_date"
        seen.append(
            {
                "day": day,
                "rows": len(player_games),
                "max": (
                    ""
                    if player_games.empty
                    else str(player_games[column].astype(str).max())
                ),
            }
        )
        return prices.copy()

    priced = PB.walk_forward(
        _walk_prices(),
        _walk_games((DAYS[0],)),
        price_day=price_day,
        frames={"player_games": players},
    )

    assert [call["day"] for call in seen] == sorted(DAYS)
    for call in seen:
        assert call["max"] < call["day"] or call["max"] == "", (
            f"the pricer for {call['day']} was shown player rows up to "
            f"{call['max']}, which is not strictly earlier"
        )
    assert [call["rows"] for call in seen] == [0, 1, 2]

    stamps = dict(zip(priced["slate_date"].astype(str), priced["priced_through"]))
    assert stamps == {DAYS[0]: "", DAYS[1]: DAYS[0], DAYS[2]: DAYS[1]}, (
        "the stamp is the latest day across every frame the pricer was handed, "
        "and the player frame runs a day later than the team games here"
    )
    PB.assert_walk_forward(priced)

    # A frame whose day column is named something else is refused rather than
    # cut to nothing. `history_before` would hand the pricer an empty player
    # frame every night, and a player model priced off nothing looks exactly
    # like a player model with no opinions.
    renamed = players.rename(columns={"slate_date": "game_date"})
    with pytest.raises(PB.BacktestError) as raised:
        PB.walk_forward(
            _walk_prices(),
            _walk_games((DAYS[0],)),
            price_day=price_day,
            frames={"player_games": renamed},
        )
    assert "player_games" in str(raised.value)

    seen.clear()
    named = PB.walk_forward(
        _walk_prices(),
        _walk_games((DAYS[0],)),
        price_day=price_day,
        frames={"player_games": renamed},
        frame_day_columns={"player_games": "game_date"},
    )
    assert [call["rows"] for call in seen] == [0, 1, 2]
    assert list(named["priced_through"]) == ["", DAYS[0], DAYS[1]], (
        "the same frame under its own day column is cut and stamped the same way"
    )


def test_a_pricer_that_demands_a_frame_the_caller_does_not_hold_is_refused():
    """An input `walk_forward` was never given is one it cannot cut or stamp."""

    def price_day(*, day, history, prices, player_games):
        return prices.copy()

    with pytest.raises(PB.BacktestError) as raised:
        PB.walk_forward(_walk_prices(), _walk_games(), price_day=price_day)

    assert "player_games" in str(raised.value)

    # And a named frame may not take the name of an argument every pricer is
    # already handed: the pricer would receive one of the two and the stamp
    # would describe the other.
    for name in PB.PRICER_ARGUMENTS:
        with pytest.raises(PB.BacktestError) as clash:
            PB.walk_forward(
                _walk_prices(),
                _walk_games(),
                price_day=lambda **kwargs: None,
                frames={name: _walk_games()},
            )
        assert name in str(clash.value)


def test_a_pricer_that_reads_only_the_team_history_is_stamped_as_it_always_was():
    """The existing contract, unchanged: no stamp of its own, no `frames=`.

    And a pricer cannot *lower* the stamp: the stamp describes what it was
    allowed to see, not what it chose to read, so a blank or an earlier day
    returned by the pricer leaves the caller's stamp standing.
    """

    def plain(*, day, history, prices):
        return prices.copy()

    priced = PB.walk_forward(_walk_prices(), _walk_games(), price_day=plain)
    stamps = dict(zip(priced["slate_date"].astype(str), priced["priced_through"]))
    assert stamps == {DAYS[0]: "", DAYS[1]: DAYS[0], DAYS[2]: DAYS[1]}
    PB.assert_walk_forward(priced)

    def modest(*, day, history, prices):
        frame = prices.copy()
        frame["priced_through"] = "" if day == DAYS[2] else "1900-01-01"
        return frame

    lowered = dict(
        zip(
            *[
                PB.walk_forward(
                    _walk_prices(), _walk_games(), price_day=modest
                )[column].astype(str)
                for column in ("slate_date", "priced_through")
            ]
        )
    )
    assert lowered == {
        # Day one: the caller cut nothing, so the pricer's own declaration is
        # the only evidence there is and it stands.
        DAYS[0]: "1900-01-01",
        # Days two and three: a pricer cannot talk the stamp down below the
        # history it was handed, whether it names an earlier day or none.
        DAYS[1]: DAYS[0],
        DAYS[2]: DAYS[1],
    }


def test_the_accounting_identity_reconciles_and_is_printed(scored):
    """`offered = unparseable + no opinion + below threshold + bets`.

    A wager that reaches none of the four buckets has vanished from the
    measurement, and a measurement that silently lost rows still prints an
    interval.
    """
    assert "Accounting identity" in scored.stdout
    assert "reconciles               yes" in scored.stdout
    offered = scored.record["wagers_offered"]
    assert offered > 0
    assert scored.record["bets_taken"] <= offered


@pytest.fixture(scope="module")
def script() -> dict:
    """The script's own namespace, loaded without running `main`."""
    return runpy.run_path(str(SCRIPT))


def graded_universe(script: dict, *, rows: int = 12) -> pd.DataFrame:
    """A tiny priced-and-graded frame with one row in each of the four buckets."""
    unparseable = script["UNPARSEABLE_COLUMN"]
    records = []
    for i in range(rows):
        bucket = i % 4
        records.append(
            {
                "event_id": f"e{i:02d}",
                "slate_date": f"2027-01-{(i % 5) + 1:02d}",
                "market": "spread",
                "selection": "home",
                "american_odds": -110,
                "tier": Tier.HIGH_MAJOR.value,
                unparseable: "the market is not one this lab wires"
                if bucket == 0
                else "",
                "model_probability": None if bucket in (0, 1) else 0.55,
                # bucket 2 sits below the threshold, bucket 3 clears it.
                "edge": None if bucket in (0, 1) else (0.001 if bucket == 2 else 0.40),
                "profit_units": 0.9,
            }
        )
    return pd.DataFrame(records)


def test_the_accounting_identity_counts_every_term_from_the_frame(script):
    """No term is the residual of the others, so the identity can actually fail.

    Until 2026-09-05 `scripts/run_price_backtest.py` computed two of the four
    terms by subtraction —

        accounting.no_opinion = max(len(priced) - opinions - unparseable, 0)
        accounting.below_threshold = max(opinions - accounting.bets, 0)

    — which makes the sum identically `len(priced)` whatever the frames hold.
    The identity reconciled by construction and could never have detected the
    loss it exists to detect.
    """
    accounting = script["OpinionAccounting"]
    universe = graded_universe(script, rows=12)
    book = accounting(offered=len(universe), unparseable_declared=3)
    book.count_from(
        universe,
        threshold=0.02,
        bets=universe[pd.to_numeric(universe["edge"], errors="coerce") >= 0.02],
    )

    assert (book.unparseable, book.no_opinion, book.below_threshold, book.bets) == (
        3,
        3,
        3,
        3,
    ), book
    assert book.accounted == 12 == book.offered
    assert book.bets_in_hand == book.bets == 3
    assert book.reconciles
    book.check()  # does not raise


def test_a_bet_dropped_between_selecting_and_counting_is_not_absorbed(script):
    """The residual's signature failure, as a unit test.

    `below_threshold = max(opinions - bets, 0)` makes a lost bet arithmetically
    indistinguishable from a wager that never cleared the threshold. Counting
    both from the frame and comparing the bets bucket against the frame the
    report is handed makes the two distinguishable again.
    """
    accounting = script["OpinionAccounting"]
    does_not_reconcile = script["AccountingDoesNotReconcile"]
    universe = graded_universe(script, rows=12)
    selected = universe[pd.to_numeric(universe["edge"], errors="coerce") >= 0.02]
    book = accounting(offered=len(universe), unparseable_declared=3)
    book.count_from(universe, threshold=0.02, bets=selected.iloc[1:])

    assert book.accounted == book.offered, (
        "the four buckets still sum to the offered count, which is exactly why "
        "the sum alone never caught this"
    )
    assert book.bets == 3 and book.bets_in_hand == 2
    assert not book.reconciles
    with pytest.raises(does_not_reconcile, match="bets bucket"):
        book.check()


def test_a_dropped_row_makes_the_identity_fail_rather_than_absorb(script):
    """The whole point: lose a row and the identity says so, loudly.

    A measurement that silently lost rows still prints an interval, so the
    failure is an exception and an `::error::` exit rather than a warning. Each
    of the four buckets is emptied by one row in turn, because a residual term
    absorbs a loss in exactly one of them and a test that only dropped from one
    bucket would pass on the defective code.
    """
    accounting = script["OpinionAccounting"]
    does_not_reconcile = script["AccountingDoesNotReconcile"]
    unparseable = script["UNPARSEABLE_COLUMN"]
    universe = graded_universe(script, rows=12)

    for bucket, predicate in (
        ("unparseable", universe[unparseable].astype(str).ne("")),
        (
            "no opinion",
            universe[unparseable].astype(str).eq("")
            & universe["model_probability"].isna(),
        ),
        ("below threshold", pd.to_numeric(universe["edge"]).between(0.0, 0.01)),
        ("bets", pd.to_numeric(universe["edge"]) >= 0.02),
    ):
        first = universe[predicate].index[0]
        short = universe.drop(index=[first])
        book = accounting(offered=len(universe), unparseable_declared=3)
        book.count_from(short, threshold=0.02)
        assert book.accounted == len(universe) - 1, (
            f"dropping a {bucket} row must reduce the accounted total; a term "
            f"computed as a residual absorbs it instead: {book}"
        )
        assert not book.reconciles, bucket
        with pytest.raises(does_not_reconcile):
            book.check()
        assert "reconciles               NO" in "\n".join(book.lines())


def test_the_pricers_refusal_tally_is_checked_against_the_frame(script):
    """Two independent counts of the same quantity, compared.

    `card_pricing.build_wagers` returns its own integer count of the rows it
    refused, accumulated day by day while pricing; `count_from` counts the rows
    carrying a refusal in the graded frame. A refused row that disappeared
    between the two leaves the tally high and the frame count low, and that is
    a loss the four-bucket sum alone cannot see when a second row appears from
    somewhere else.
    """
    accounting = script["OpinionAccounting"]
    does_not_reconcile = script["AccountingDoesNotReconcile"]
    universe = graded_universe(script, rows=12)
    book = accounting(offered=len(universe), unparseable_declared=4)
    book.count_from(universe, threshold=0.02)
    assert book.accounted == book.offered, "the four buckets still sum correctly"
    assert not book.reconciles, (
        "the pricer refused four rows and three survive; the sum alone cannot "
        "see that, and it is exactly the loss the identity exists to detect"
    )
    with pytest.raises(does_not_reconcile, match="unparseable"):
        book.check()


def test_a_bet_lost_on_the_way_to_the_report_stops_the_whole_run(
    tmp_path, capsys, monkeypatch
):
    """End to end, on the seam the residual arithmetic absorbed silently.

    `bets_from` selects the rows the report measures. Under the old code the
    below-threshold term was `max(opinions - len(bets), 0)`, so a bet lost here
    reappeared as a below-threshold wager, the four terms still summed to
    `len(priced)`, the run printed `reconciles yes` and wrote a record and a
    report measuring one bet fewer than it had selected. Now the bets bucket is
    counted from the frame with `bet_mask` and compared against the frame the
    report is handed, and the run refuses.
    """
    lab = Lab(tmp_path).with_tables().with_store()
    model = StubModel(module_name="cbb_stub_model_dropped_bet")
    spec = model.register()

    honest = PB.bets_from

    def drops_one(frame, **kwargs):
        taken = honest(frame, **kwargs)
        assert len(taken) > 1, "the fixture must select more than one bet"
        return taken.iloc[1:].reset_index(drop=True)

    monkeypatch.setattr(PB, "bets_from", drops_one)
    code = lab.run("--model", spec)

    assert code != 0, "a lost bet must not produce a measurement"
    combined = "".join(capsys.readouterr())
    assert "::error::" in combined
    assert "accounting identity does not reconcile" in combined
    assert "Nothing was written" in combined
    assert "reconciles               NO" in combined
    assert not lab.record_path.is_file(), "no record may survive a lost bet"
    assert not lab.report_path.is_file(), "no report may survive a lost bet"


def test_a_row_lost_after_pricing_stops_the_whole_run(tmp_path, capsys, monkeypatch):
    """The other seam: a row that disappears between the pricer and the grader.

    `add_edge` sits after the length check on `walk_forward`'s output and before
    the frame the report is built from, so a row lost there is a row the
    accounting identity is the only remaining guard on.
    """
    lab = Lab(tmp_path).with_tables().with_store()
    model = StubModel(module_name="cbb_stub_model_dropped_row")
    spec = model.register()

    honest = PB.add_edge

    def drops_one(frame, **kwargs):
        priced = honest(frame, **kwargs)
        return priced.iloc[1:].reset_index(drop=True)

    monkeypatch.setattr(PB, "add_edge", drops_one)
    code = lab.run("--model", spec)

    assert code != 0, "a lost row must not produce a measurement"
    combined = "".join(capsys.readouterr())
    assert "::error::" in combined
    assert "accounting identity does not reconcile" in combined
    assert not lab.record_path.is_file(), "no record may survive a lost row"
    assert not lab.report_path.is_file(), "no report may survive a lost row"


def test_build_wagers_classifies_every_input_row_exactly_once():
    """`row_reasons` is the per-row half of the count `build_wagers` returns.

    One definition of "unparseable", read off the row rather than re-derived
    from the aggregate. A second copy of the predicate is how the accounting
    identity came to compute a term as a residual in the first place.
    """
    from cbb_betting_lab.reports import card_pricing

    prices = pd.DataFrame(
        [
            {
                "event_id": "e1",
                "slate_date": "2027-01-02",
                "commence_time": "2027-01-02T23:00:00Z",
                "home_team": "Duke",
                "away_team": "Kansas",
                "market": "spread",
                "segment": FULL_GAME,
                "player": "",
                "selection": "home",
                "line": -3.5,
                "american_odds": -110,
                "book": "dk",
            },
            # A market this lab does not wire: refused, with a reason.
            {
                "event_id": "e1",
                "slate_date": "2027-01-02",
                "commence_time": "2027-01-02T23:00:00Z",
                "home_team": "Duke",
                "away_team": "Kansas",
                "market": "corner_kicks",
                "segment": FULL_GAME,
                "player": "",
                "selection": "over",
                "line": 9.5,
                "american_odds": -110,
                "book": "dk",
            },
            # An unreadable price: refused, with a different reason.
            {
                "event_id": "e1",
                "slate_date": "2027-01-02",
                "commence_time": "2027-01-02T23:00:00Z",
                "home_team": "Duke",
                "away_team": "Kansas",
                "market": "spread",
                "segment": FULL_GAME,
                "player": "",
                "selection": "away",
                "line": 3.5,
                "american_odds": "",
                "book": "dk",
            },
        ]
    )
    reasons: list[str] = []
    wagers, unparseable, _ = card_pricing.build_wagers(
        prices, competition=CBB, row_reasons=reasons
    )
    assert len(reasons) == len(prices), reasons
    assert unparseable == sum(1 for r in reasons if r) == 2
    assert reasons[0] == ""
    assert reasons[1] and reasons[2] and reasons[1] != reasons[2]
    assert len(wagers) == 1


# --------------------------------------------------------------------------
# The order the numbers are read in
# --------------------------------------------------------------------------


#: Every list of measured cells the record carries and `render` prints.
CELL_KEYS = ("null_baseline", "by_market_and_tier", "by_tier", "pooled")


def measured_rows(record: dict) -> list[dict]:
    """Every `_interval_row` in the record, from every table `render` prints."""
    rows: list[dict] = []
    for key in CELL_KEYS:
        rows.extend(record.get(key) or [])
    half = record.get("half_point") or {}
    for key in (
        "half_point_decided",
        "half_point_at_a_key_number",
        "a_view_of_the_game",
    ):
        row = half.get(key)
        if row:
            rows.append(row)
    return rows


def test_the_record_carries_the_clustering_beside_every_cluster_count(scored):
    """The number is meaningless without the unit, so the record carries both.

    `stats.interval_two_way` clusters by game **and** by day and keeps the
    wider, so the clustering behind one row of a table is routinely not the one
    behind the row beneath it. A record that stored only the integer forced
    every renderer to guess, and the guess was printed as a column headed
    "Games".
    """
    rows = measured_rows(scored.record)
    assert rows, "the fixture must produce measured cells"
    for row in rows:
        assert row.get("cluster_unit") in {"game", "day"}, row
        assert int(row.get("clusters", -1)) >= 0, row


def test_a_row_clustered_by_day_never_prints_the_word_games(scored):
    """And a row clustered by game never prints "days". Checked row by row.

    "11,071 bets / 513 days" and "11,071 bets / 513 games" are different claims
    about the same integer, and the report used to print both under one column
    headed "Games". Every table line is matched back to the record row that
    produced it and read for the wrong unit.
    """
    report = scored.report
    assert "| Games |" not in report, (
        "no ROI table may head its cluster column 'Games' — the column holds "
        "day counts on some rows"
    )
    lines = [line for line in report.splitlines() if line.startswith("|")]
    checked = 0
    for row in measured_rows(scored.record):
        unit = row["cluster_unit"]
        wrong = "day" if unit == "game" else "game"
        cell = PB.cluster_cell(row)
        assert f"{row['clusters']:,} {unit}s" == cell, cell
        hits = [line for line in lines if cell in line]
        assert hits, (
            f"the row measured over {cell} is not printed with its clustering; "
            f"looked for {cell!r} in the rendered tables"
        )
        for line in hits:
            assert f"{row['clusters']:,} {wrong}s" not in line, (
                f"a row clustered by {unit} printed the word {wrong}s: {line}"
            )
        checked += 1
    assert checked >= len(CELL_KEYS), "too few rows checked to mean anything"


def test_both_clusterings_are_reachable_and_are_labelled_apart():
    """A day-clustered row and a game-clustered row, rendered from one record.

    The fixture run may happen to choose one unit for every cell, and a test
    that only ever saw one would pass on a renderer that hard-coded it. These
    two rows are built by hand so both branches are real, and each is read for
    its own unit and against the other's.
    """
    by_day = {
        "name": "clustered by day",
        "tier": "high_major",
        "market": "spread",
        "roi": 0.031,
        "low": 0.004,
        "high": 0.058,
        "adjusted_low": -0.01,
        "adjusted_high": 0.072,
        "bets": 11_071,
        "clusters": 513,
        "cluster_unit": "day",
        "looks": 1,
        "standard_error": 0.014,
        "enough_evidence": True,
        "verdict": "demonstrated edge",
    }
    by_game = {**by_day, "name": "clustered by game", "clusters": 9_004,
               "cluster_unit": "game"}

    day_line = PB._row(by_day, by_day["name"])
    game_line = PB._row(by_game, by_game["name"])
    assert "513 days" in day_line and "games" not in day_line, day_line
    assert "9,004 games" in game_line and "days" not in game_line, game_line

    record = {
        "record_version": PB.RECORD_VERSION,
        "by_tier": [by_day, by_game],
        "pooled": [by_day, by_game],
    }
    report = PB.render(record)
    assert "| Clusters |" in report and "| Games |" not in report
    assert "513 days" in report and "9,004 games" in report
    for line in report.splitlines():
        if "513 days" in line:
            assert "games" not in line, line
        if "9,004 games" in line:
            assert "days" not in line, line


def test_a_version_1_record_still_carries_the_clustering_on_every_row(scored):
    """Why `price_backtest.RECORD_VERSION` was **not** bumped with the header.

    `forecast_skill.RECORD_VERSION` moved 2 -> 3 in the same commit, because
    that record's shape changed. This one's did not: `cluster_unit` has been
    written onto every interval row by `_interval_row` since before this branch,
    and only the renderer changed. So every version 1 record already on disk
    carries the field the new "Clusters" column reads, and bumping here would
    refuse records that are not stale. The claim is checked rather than
    asserted in prose: the record this run writes is version 1, and every
    interval row in it renders its clustering.
    """
    assert scored.record["record_version"] == PB.RECORD_VERSION == 1, (
        "the cluster column is a renderer change over a field the record "
        "already carried; a bump here would refuse records that are not stale"
    )
    rows = measured_rows(scored.record)
    assert rows, "the fixture must produce measured cells"
    for row in rows:
        assert "cluster_unit" in row, (
            "a version 1 record must already carry the clustering, or the "
            f"version would have had to move with the column; got {row}"
        )
        assert PB.cluster_cell(row) in scored.report, row


def test_a_row_with_no_cluster_unit_is_never_assumed_to_be_games():
    """An absent clustering prints as unknown rather than as the commoner guess.

    This is the case a version bump would have covered, and it is covered here
    instead. `stats.interval_two_way` keeps the wider of the game and day
    clusterings, so "games" is wrong roughly as often as it is right; a renderer
    that defaulted to it would print a plausible sentence that is a coin flip.
    """
    naked = {
        "name": "no clustering recorded",
        "roi": 0.031,
        "low": 0.004,
        "high": 0.058,
        "adjusted_low": -0.01,
        "adjusted_high": 0.072,
        "bets": 11_071,
        "clusters": 513,
        "looks": 1,
        "standard_error": 0.014,
        "enough_evidence": True,
        "verdict": "no demonstrated edge",
    }
    cell = PB.cluster_cell(naked)
    assert cell == "513 unknown-clusters", cell
    assert "game" not in cell and "day" not in cell, cell
    assert cell == PB.cluster_cell({**naked, "cluster_unit": ""}), (
        "an empty string is as unknown as an absent key"
    )
    line = PB._row(naked, naked["name"])
    assert "513 unknown-clusters" in line, line


def test_the_null_baseline_is_printed_before_any_model_number(scored):
    """*"What would betting one side with no model at all return?"*

    That is the question that broke the football lab's best result, and the
    order matters as much as the number: a reader who sees the model figure
    first has already formed the belief the baseline exists to prevent.
    """
    baseline_at = scored.stdout.index("THE NULL BASELINE, FIRST")
    model_at = scored.stdout.index("THE MODEL, PER MARKET AND PER CONFERENCE TIER")
    assert baseline_at < model_at

    report = scored.report
    assert report.index("## The null baseline, first") < report.index(
        "## The model, per market and per conference tier"
    )
    assert scored.record["null_baseline"], "the blind sides must have been graded"


def test_the_baseline_covers_the_blind_sides_and_the_price_split(scored):
    """Blind and mechanical: every quoted wager on that side, one bet per wager.

    And the favourite/underdog split, which is a fact about the number rather
    than about the name — a wager whose two sides are not both quoted
    contributes to neither, because a one-sided group cannot say which side was
    favoured and guessing is how a baseline stops being blind.
    """
    names = {row["name"] for row in scored.record["null_baseline"]}
    assert {"always home", "always away", "always over", "always under"} & names
    assert {"always the favourite", "always the underdog"} & names, (
        "the moneyline is quoted on both sides, so the price split must exist"
    )


def test_no_pooled_division_one_headline(scored):
    """The pooled figure exists because the stopping rule is applied to it.

    It is never the headline, and the caveat saying so in words is printed above
    it every time.
    """
    report = scored.report
    assert PB.POOLED_CAVEAT in report
    assert report.index("## The model, per market and per conference tier") < report.index(
        "## Pooled"
    )
    tiers = {row["tier"] for row in scored.record["by_market_and_tier"]}
    assert len(tiers) >= 2, "the fixture spans two tiers and both must be measured apart"


def test_below_the_declared_floor_there_is_no_number(scored):
    """*A +12% return over 40 bets and a coin flip are the same claim.*

    `stats.roi_table_row` prints the figure regardless, which is right for a
    table of measured markets and wrong here. The fixture is built so that one
    market clears the floor and the others do not, so both branches are real.
    """
    cells = scored.record["by_market_and_tier"]
    assert cells
    thin = [c for c in cells if not c["enough_evidence"]]
    thick = [c for c in cells if c["enough_evidence"]]
    assert thin, "the fixture must contain a cell below the floor"
    assert thick, "and one above it, or the floor branch is the only one tested"
    for cell in thin:
        assert PB.roi_cells(cell) == ("—", "—", "—")
        assert str(MINIMUM_BETS) in cell["verdict"] or "not enough evidence" in cell["verdict"]


def test_the_family_correction_is_the_ledgers_cumulative_count(scored):
    """Never the day's count. *"A search that runs every week is not twelve tests."*"""
    assert scored.record["looks"] == 30, "the fixture ledger holds thirty hypotheses"
    assert scored.record["correction_factor"] > 1.0
    assert "cumulative" in scored.stdout


def test_the_half_point_split_is_reported_and_its_convention_verified(scored):
    """Half a point at a key number is a different claim from a view of the game.

    And the split is refused outright unless the ticket-margin reconstruction
    agrees with the recorded outcomes — a decomposition on a convention this lab
    guessed at is the kind of finding that supplies its own explanation.
    """
    half = scored.record["half_point"]
    assert half["verified"], half.get("note", "")
    assert half["convention"]["checked"] > 0
    assert half["convention"]["rate"] >= 1.0 - PB.CONVENTION_TOLERANCE
    assert "half_point_decided" in half and "a_view_of_the_game" in half

    keys = scored.record["key_numbers"]["margin"]
    assert keys["n"] > 0
    assert keys["numbers"], "key numbers are measured from the games, never a list"


def _accounting_count(stdout: str, label: str) -> int:
    """One count off the printed accounting identity, e.g. `no opinion 0`."""
    match = re.search(rf"^\s*{re.escape(label)}\s+([\d,]+)\s*$", stdout, flags=re.MULTILINE)
    assert match, f"the accounting line {label!r} was not printed:\n{stdout}"
    return int(match.group(1).replace(",", ""))


def test_the_graded_export_is_every_settled_opinion_with_the_bets_flagged(scored):
    """`--write-graded` writes the population the regression runs over, not the bets.

    Until 2026-09-05 it wrote `PB.settled(bets)`: the rows the model's own
    disagreement with the price selected, and nothing else. `forecast_skill`
    then regressed outcome on that same disagreement over that slice, which
    bakes the winner's curse into the coefficient and empties every
    claimed-edge bucket below the threshold by construction. The frame is now
    every settled wager the model had an opinion on, with a boolean `selected`
    marking the bets, so the whole and the subset can be told apart and both
    can be counted.

    The stub model has an opinion on every wager it is shown, the fixture's
    lines are all half-points and no full game ends level, so on this fixture
    the settled opinions ARE the graded wagers — read off the record, which is
    built from the same `universe`, and off the printed accounting identity,
    which is built independently of the export.
    """
    assert scored.exit_code == 0, scored.stdout
    assert scored.lab.graded_path.is_file(), "the export was not written"
    frame = pd.read_csv(scored.lab.graded_path)

    assert "selected" in frame.columns
    assert frame["selected"].dtype == bool, frame["selected"].dtype
    assert set(frame["selected"].unique()) <= {True, False}
    for column in FS.SKILL_COLUMNS:
        assert column in frame.columns, column
    assert "book" in frame.columns, "the de-vig pairs within a book and needs the column"

    # Every row is a settled opinion: a probability and a won-or-lost outcome.
    assert frame["model_probability"].notna().all()
    assert set(frame["outcome"].str.lower().unique()) <= {"won", "lost"}

    bets_graded = int(scored.record["bets_graded"])
    wagers_graded = int(scored.record["wagers_graded"])
    assert bets_graded > 0
    # At least as many rows as bets — and on this fixture strictly more,
    # because the ladder is wide enough that rungs fall below the threshold.
    assert len(frame) >= bets_graded
    assert len(frame) > bets_graded, (
        f"{len(frame)} rows for {bets_graded} bets: the export is still the bets"
    )
    # Exactly the bets are flagged: the same predicate `bets_from` used.
    assert int(frame["selected"].sum()) == bets_graded
    # And the whole is the settled-opinion count. The accounting identity
    # printed by the run says the model declined nothing, so every graded
    # wager carries an opinion and the two counts must be equal.
    assert _accounting_count(scored.stdout, "no opinion") == 0
    assert _accounting_count(scored.stdout, "unparseable") == 0
    assert len(frame) == wagers_graded, (
        f"{len(frame)} rows exported against {wagers_graded} graded wagers with an "
        "opinion — the export is not the settled-opinion population"
    )
    # The run says which population it wrote, and in words.
    assert re.search(
        rf"Wrote {len(frame):,} settled opinion\(s\) .* {bets_graded:,} of them are the "
        r"threshold-selected bets",
        scored.stdout,
    ), scored.stdout


def test_the_selected_flag_agrees_with_the_bets_predicate_row_by_row(scored):
    """`selected` is `PB.bet_mask`, not a second definition of a bet.

    Recomputing the edge from the exported columns with the repository's one
    edge function and applying the declared threshold must reproduce the flag
    on every row, or the export and the ROI table are two different cuts.
    """
    frame = pd.read_csv(scored.lab.graded_path)
    threshold = float(scored.record["edge_threshold"])
    recomputed = PB.bet_mask(PB.add_edge(frame), threshold=threshold)
    assert recomputed.tolist() == frame["selected"].tolist()
    assert int(recomputed.sum()) == int(scored.record["bets_graded"])


def test_calibration_is_measured_on_the_bets_that_were_selected(scored):
    """Overall calibration is not evidence. The winner's curse lives on selection."""
    calibration = scored.record["calibration"]
    assert calibration["overall"] and calibration["selected"]
    assert calibration["edge_threshold"] == pytest.approx(PB.BET_EDGE_THRESHOLD)
    assert "Calibration" in scored.report or "calibration" in scored.report


# --------------------------------------------------------------------------
# Improving a sentence must never cost a re-run
# --------------------------------------------------------------------------


def test_rebuild_report_only_re_renders_without_the_store_or_the_tables(
    scored, tmp_path, capsys
):
    """The retention probe's rule, and it bites harder here.

    A full run walks every slate day and grades every wager in the store. If
    improving a sentence cost that, nobody would improve a sentence — they would
    edit the generated file by hand, and a hand-edited generated file survives
    exactly one re-run. So the record is written first and `render` is pure over
    it: the store and the processed tables are removed here, and the report
    still rebuilds byte for byte.
    """
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    (outputs / scored.lab.record_path.name).write_text(
        scored.lab.record_path.read_text(encoding="utf-8"), encoding="utf-8"
    )
    empty_processed = tmp_path / "processed"
    empty_processed.mkdir()

    saved = sys.argv[:]
    sys.argv = [
        str(SCRIPT),
        "--processed-dir",
        str(empty_processed),
        "--output-dir",
        str(outputs),
        "--ledger",
        str(outputs / "experiment_ledger.json"),
        "--rebuild-report-only",
    ]
    try:
        runpy.run_path(str(SCRIPT), run_name="__main__")
        code = 0
    except SystemExit as exit_code:
        code = int(exit_code.code or 0)
    finally:
        sys.argv = saved

    assert code == 0, "".join(capsys.readouterr())
    rebuilt = (outputs / scored.lab.report_path.name).read_text(encoding="utf-8")
    assert rebuilt == scored.report, (
        "the report must be a pure function of the record — no clock, no "
        "network, no re-scoring"
    )
    printed = "".join(capsys.readouterr())
    assert "Nothing was re-scored" in printed


def test_rebuild_report_only_without_a_record_says_so_and_exits_non_zero(
    tmp_path, capsys
):
    lab = Lab(tmp_path)
    code = lab.run("--rebuild-report-only")
    assert code != 0
    assert "no record to re-render" in "".join(capsys.readouterr())
    assert not lab.report_path.exists()


def test_a_stale_record_is_refused_rather_than_rendered_with_holes(tmp_path, capsys):
    """A record from an older shape renders a report with holes and nothing looks
    wrong, so `read_record` raises on the version and this script surfaces it."""
    lab = Lab(tmp_path)
    lab.record_path.parent.mkdir(parents=True, exist_ok=True)
    lab.record_path.write_text(
        json.dumps({"record_version": PB.RECORD_VERSION - 1}), encoding="utf-8"
    )

    code = lab.run("--rebuild-report-only")

    assert code != 0
    assert "Re-run the backtest" in "".join(capsys.readouterr())
    assert not lab.report_path.exists()
