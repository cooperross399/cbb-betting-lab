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
        exit_code = lab.run("--model", spec)
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


# --------------------------------------------------------------------------
# The order the numbers are read in
# --------------------------------------------------------------------------


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
