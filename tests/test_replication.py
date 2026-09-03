"""Replication on a held-out season, and the one sentence it exists to enforce.

`price_backtest.py` ends by naming `replication.py` and specifying it in a
sentence: *"It cannot replicate itself. A held-out season is `replication.py`'s
job, and a window that merely fails to contradict is not confirmation."* Every
test here is named for a specific way that sentence could be broken, and the
first one reproduces the sibling lab's version of the mistake before anything
else is asserted.

The failure modes, in the order they are tested:

* **A window that merely fails to contradict, reported as confirmation.** The
  NHL lab's `blocked_shots`: same sign, an interval far too wide to exclude
  anything, and a verdict of "held". An interval spanning zero is equally
  compatible with the discovery result, with no effect, and with the opposite
  effect.
* **A replication that reads only the sign**, and so cannot fail.
* **A replicated loss read as good news** — the NHL lab's headline predicate,
  which tested measured + survives-correction + replicated and never looked at
  which side of zero the number sat on.
* **A number printed below the floor declared in advance**, where a +12% return
  over 40 bets and a coin flip are the same claim.
* **A second bar invented here** instead of `promotion.py`'s pre-registered one.
* **A "held-out" season the rule was actually selected on**, which reproduces
  the selection rather than the effect and does it with a tighter interval every
  time the sample grows. This is the only failure in the module that would
  produce a clean, confident and entirely worthless report.
* **A discovery window read as empty** because its label could not be parsed,
  which makes every season look held out.
* **A result found ON the holdout**, reported as though the holdout had
  confirmed it.
* **One good season carrying the others** — the football lab's verdict defect,
  same policy and same script, opposite verdicts.
* **A pooled Division I state** leaking into a per-tier claim through the
  claims document's wildcard.
* **A settlement artefact**, which replicates by construction.
* **A report that can only be produced by re-running the measurement**, which is
  a report nobody improves.

The end-to-end tests build two seasons on disk out of `test_run_price_backtest`'s
own fixture builders rather than a second copy of them, score the first with the
real backtest script and hold the second out. That is deliberate: a replication
fixture that built its store differently from the backtest fixture would be
testing that two fixtures agree.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest

import test_run_price_backtest as BT
from cbb_betting_lab import experiment_ledger as E
from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.conferences import Tier
from cbb_betting_lab.experiment_ledger import LEDGER_FILENAME
from cbb_betting_lab.promotion import Criteria, load_criteria
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.reports import replication as R
from cbb_betting_lab.reports import what_we_can_claim as WWCC
from cbb_betting_lab.selection import FULL_GAME

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run_replication.py"

#: The two seasons the end-to-end fixture builds, labelled by the year each
#: season ENDS. 2024 is held out because that is the split `replication.py`
#: declared before any price was bought; using a different one here would test
#: the module's warning path rather than its normal one.
DISCOVERY_SEASON = 2023
HOLDOUT_SEASON = 2024

#: A criteria object for the unit tests, so a floor can be varied without
#: touching `data/manual/promotion_criteria.json`. The **real** file's values
#: are pinned separately by
#: `test_the_floor_and_the_interval_rule_come_from_the_promotion_criteria`,
#: which is what stops this fixture from quietly becoming the bar.
def criteria(**overrides) -> Criteria:
    values = {
        "roi_margin_points": 1.5,
        "require_interval_excludes_zero": True,
        "minimum_bets": 200,
        "must_clear_every_season": True,
        "demotion_roi_floor": -0.02,
        "demotion_minimum_bets": 500,
        "declared_on": "2026-09-01",
        "why": "a fixture, not the bar",
    }
    values.update(overrides)
    return Criteria(**values)


# --------------------------------------------------------------------------
# Synthetic graded bets, with the interval width chosen rather than hoped for
# --------------------------------------------------------------------------


def graded(
    *,
    market: str = "moneyline",
    tier: str = Tier.LOW_MAJOR.value,
    profits: tuple[float, ...],
    bets_per_game: int = 10,
    first_game: int = 0,
    first_day: date = date(2023, 11, 1),
) -> pd.DataFrame:
    """One game per day, `bets_per_game` bets each, at a chosen profit per game.

    One game per day on purpose: `stats.interval_two_way` clusters by game and
    by day and reports the wider, so making the two units identical means a test
    that fixes a per-game profit has fixed the interval it is asserting about.
    A fixture whose interval depended on how games happened to fall across days
    would be a fixture that fails on a leap year.
    """
    rows: list[dict] = []
    for index, profit in enumerate(profits):
        game = first_game + index
        day = (first_day + timedelta(days=index)).isoformat()
        for _ in range(bets_per_game):
            rows.append(
                {
                    "event_id": f"e{game}",
                    "slate_date": day,
                    "market": market,
                    "segment": FULL_GAME,
                    "selection": "home",
                    "line": None,
                    "american_odds": -110,
                    "tier": tier,
                    "model_probability": 0.6,
                    "outcome": "won" if profit > 0 else "lost",
                    "profit_units": float(profit),
                }
            )
    return pd.DataFrame(rows)


def tight(value: float, *, games: int = 300, **kwargs) -> pd.DataFrame:
    """A return of `value` per bet with almost no between-game variation.

    Its interval excludes zero by a wide margin, so it is the shape of a cell
    that has genuinely demonstrated something.
    """
    profits = tuple(value + (0.01 if i % 2 else -0.01) for i in range(games))
    return graded(profits=profits, **kwargs)


def noisy(value: float, *, games: int = 300, swing: float = 1.0, **kwargs) -> pd.DataFrame:
    """A return of `value` per bet, buried in between-game variation.

    Its interval spans zero however many bets it holds. This is the shape of the
    NHL lab's second window: the same sign as the discovery result and a sample
    that could not have excluded anything.
    """
    share = 0.5 + value / (2 * swing)
    winners = int(round(games * share))
    profits = tuple(
        swing if i < winners else -swing for i in range(games)
    )
    return graded(profits=profits, **kwargs)


def discovery_record(
    frames: dict[tuple[str, str], pd.DataFrame],
    *,
    season_label: str = "2021-2023",
    looks: int = 1,
) -> dict:
    """A real `price_backtest` record over the supplied cells.

    Built by calling `PB.build_record` rather than by hand-writing a dict, so
    the replication module is tested against the shape the backtest actually
    writes. A hand-written fixture record is a fixture for a record shape that
    may no longer exist.
    """
    frame = pd.concat(
        [
            f.assign(market=market, tier=tier)
            for (market, tier), f in frames.items()
        ],
        ignore_index=True,
    )
    return PB.build_record(
        PB.BacktestInputs(
            universe=frame,
            bets=frame,
            season_label=season_label,
            snapshot_phase="card",
        ),
        looks=looks,
    )


def build(
    *,
    discovery: dict,
    holdout: dict[int, pd.DataFrame],
    looks: int = 1,
    crit: Criteria | None = None,
) -> dict:
    return R.build_record(
        discovery=discovery,
        holdout_bets=holdout,
        criteria=crit or criteria(),
        looks=looks,
        model="tests:stub",
    )


def state_of(record: dict, market: str, tier: str) -> str:
    for row in record["markets"]:
        if row["market"] == market and row["tier"] == tier:
            return row["state"]
    raise AssertionError(f"no cell for {market}/{tier} in {record['markets']}")


def why_of(record: dict, market: str, tier: str) -> str:
    for row in record["markets"]:
        if row["market"] == market and row["tier"] == tier:
            return row["why"]
    raise AssertionError(f"no cell for {market}/{tier}")


# --------------------------------------------------------------------------
# The defect this module exists to not repeat
# --------------------------------------------------------------------------


def test_a_window_that_merely_fails_to_contradict_is_not_confirmation():
    """**The NHL lab's `blocked_shots` mistake, reproduced and refused.**

    A market is selected in discovery. It is put to a second window whose
    return has the **same sign** and whose interval, over a sample too wide to
    exclude anything, does **not contradict** the first. The NHL lab called
    that "held".

    It is not. An interval that spans zero is compatible with the discovery
    result, with no effect at all, and with the opposite effect. A test that
    cannot fail is not a test. So the state must not be `replicated`, and the
    reason printed beside it must say `no demonstrated edge` in those exact
    words.
    """
    cell = ("moneyline", Tier.LOW_MAJOR.value)
    discovery = discovery_record({cell: tight(0.06)})
    holdout = noisy(0.10, games=300, first_game=9000)

    record = build(discovery=discovery, holdout={2024: holdout})

    # The discovery window really did demonstrate something, or this test would
    # be asserting about a cell with nothing to replicate.
    assert record["markets"][0]["discovery"]["claims"] is True
    # The held-out return has the SAME SIGN and a bigger point estimate.
    assert record["markets"][0]["holdout"]["roi"] > 0

    assert state_of(record, *cell) == R.DID_NOT_REPLICATE, (
        "a held-out interval that includes zero has confirmed nothing, however "
        "flattering its point estimate"
    )
    assert S.NO_DEMONSTRATED_EDGE in why_of(record, *cell)
    assert "merely fails to contradict is not confirmation" in why_of(record, *cell)
    report = R.render(record)
    assert S.NO_DEMONSTRATED_EDGE in report
    # And it is said in the summary as well as in the per-cell reason, so a
    # reader who reads only the table's caption still reads the verdict.
    assert (
        f"includes zero. Each of those is {S.NO_DEMONSTRATED_EDGE}" in report
    )
    assert R.REPLICATED not in {r["state"] for r in record["markets"]}


def test_the_same_sign_and_an_interval_excluding_zero_is_the_only_replication():
    """Both conditions, never one. A sign test alone cannot fail."""
    cell = ("moneyline", Tier.LOW_MAJOR.value)
    discovery = discovery_record({cell: tight(0.06)})

    replicating = build(
        discovery=discovery, holdout={2024: tight(0.05, first_game=9000)}
    )
    assert state_of(replicating, *cell) == R.REPLICATED
    assert "Same sign AND its own interval excludes zero" in why_of(
        replicating, *cell
    )

    same_sign_only = build(
        discovery=discovery, holdout={2024: noisy(0.05, first_game=9000)}
    )
    assert state_of(same_sign_only, *cell) == R.DID_NOT_REPLICATE


def test_a_held_out_season_that_reverses_the_sign_is_reported_as_a_reversal():
    """A reversal is a result, not a failure, and it is not the same as a null.

    Two different sentences: `did not replicate` means the window said nothing;
    `reversed` means it said the opposite. The experiment ledger requires a
    predicted direction for exactly this reason — four of the football lab's
    mechanisms reversed outright, and knowing that was worth more than the null.
    """
    cell = ("moneyline", Tier.LOW_MAJOR.value)
    discovery = discovery_record({cell: tight(0.06)})

    record = build(discovery=discovery, holdout={2024: tight(-0.06, first_game=9000)})

    assert state_of(record, *cell) == R.REVERSED
    assert "said the opposite" in why_of(record, *cell)
    row = record["markets"][0]
    assert row["predicted_direction"] == "higher"
    assert row["realised_direction"] == "lower"


def test_a_replicated_loss_is_a_more_credible_loss_and_never_good_news():
    """The NHL lab announced a −6.6% market as a result that survived and replicated.

    Its headline predicate tested measured + survives-correction + replicated
    and never read which side of zero the number sat on. A loss that replicates
    is a **more** credible loss, so `replicated` here must be reachable from a
    negative discovery result — and the verdict string beside it must come from
    `RoiInterval.verdict()`, which reads the sign.
    """
    cell = ("moneyline", Tier.HIGH_MAJOR.value)
    discovery = discovery_record({cell: tight(-0.06, tier=Tier.HIGH_MAJOR.value)})

    record = build(
        discovery=discovery,
        holdout={
            2024: tight(-0.05, tier=Tier.HIGH_MAJOR.value, first_game=9000)
        },
    )

    assert state_of(record, *cell) == R.REPLICATED
    assert record["markets"][0]["holdout"]["verdict"] == S.DEMONSTRATED_DEFICIT
    report = R.render(record)
    assert "It cannot say a replicated result is **good**" in report
    assert S.DEMONSTRATED_DEFICIT in report


# --------------------------------------------------------------------------
# The bar comes from `promotion.py`, and no number is printed below it
# --------------------------------------------------------------------------


def test_below_the_pre_registered_floor_there_is_no_number():
    """*A +12% return over 40 bets and a coin flip are the same claim.*

    Below the floor the state is the phrase `not enough evidence` — which is
    not the same claim as `did not replicate` — and the report prints an em dash
    where the return would go, in every one of the three numeric columns.
    """
    cell = ("moneyline", Tier.LOW_MAJOR.value)
    discovery = discovery_record({cell: tight(0.06)})
    # 20 games x 10 bets = 200 bets, comfortably under a 2,000 floor and
    # comfortably over `stats.MINIMUM_BETS`, so the only thing withholding the
    # number is the pre-registered promotion floor.
    thin = tight(0.06, games=20, first_game=9000)

    record = build(
        discovery=discovery,
        holdout={2024: thin},
        crit=criteria(minimum_bets=2000),
    )

    assert state_of(record, *cell) == R.NOT_ENOUGH_EVIDENCE
    assert "below the 2,000 declared in advance" in why_of(record, *cell)
    row = [r for r in record["markets"] if r["market"] == cell[0]][0]
    assert R.roi_cells(row["holdout"], criteria_minimum_bets=2000) == ("—", "—", "—")
    # And the verdict column must not contradict the withheld number: the row's
    # own `RoiInterval.verdict()` clears `stats.MINIMUM_BETS` and would read
    # "demonstrated edge" beside three em dashes.
    assert row["holdout"]["verdict"] == S.DEMONSTRATED_EDGE
    assert R.verdict_text(row["holdout"], minimum_bets=2000).startswith(
        R.NOT_ENOUGH_EVIDENCE
    )
    assert R.NOT_ENOUGH_EVIDENCE in R.render(record)


def test_the_floor_and_the_interval_rule_come_from_the_promotion_criteria():
    """This module reads `promotion.py`'s bar and does not write a second one.

    A bar written here would be a bar chosen after the pre-registered one
    already existed, which is the same defect one level up from the one
    `data/manual/promotion_criteria.json` exists to prevent.

    And `require_interval_excludes_zero` set to false would define replication
    as "the same sign" — the `blocked_shots` mistake exactly — so the module
    refuses to run rather than silently picking which document to believe.
    """
    real = load_criteria()
    assert real.minimum_bets == 2000
    assert real.require_interval_excludes_zero is True
    assert real.must_clear_every_season is True

    cell = ("moneyline", Tier.LOW_MAJOR.value)
    discovery = discovery_record({cell: tight(0.06)})
    # The floor is read from the criteria rather than hardcoded: the same
    # holdout is "not enough evidence" under one floor and a verdict under
    # another, and nothing but the criteria object changed.
    thin = tight(0.06, games=30, first_game=9000)
    assert (
        state_of(
            build(
                discovery=discovery,
                holdout={2024: thin},
                crit=criteria(minimum_bets=2000),
            ),
            *cell,
        )
        == R.NOT_ENOUGH_EVIDENCE
    )
    assert (
        state_of(
            build(
                discovery=discovery,
                holdout={2024: thin},
                crit=criteria(minimum_bets=100),
            ),
            *cell,
        )
        == R.REPLICATED
    )

    with pytest.raises(R.ReplicationError, match="blocked_shots"):
        R.assert_criteria_agree(criteria(require_interval_excludes_zero=False))
    with pytest.raises(R.ReplicationError):
        build(
            discovery=discovery,
            holdout={2024: thin},
            crit=criteria(require_interval_excludes_zero=False),
        )


# --------------------------------------------------------------------------
# The held-out season has to actually be held out
# --------------------------------------------------------------------------


def test_a_season_the_rule_was_selected_on_is_refused():
    """Re-scoring a rule on the data it was chosen on reproduces the selection.

    The most expensive failure available to this module, because it is the only
    one that produces a clean, confident and entirely worthless report: the
    intervals come out *tighter* than the discovery window's and everything
    replicates. `promotion.py` requires a holdout *"the challenger was not
    fitted on and that was declared before discovery closed"*.
    """
    cell = ("moneyline", Tier.LOW_MAJOR.value)
    discovery = discovery_record({cell: tight(0.06)}, season_label="2021-2023")

    with pytest.raises(R.NotHeldOut, match="inside the discovery window"):
        build(discovery=discovery, holdout={2022: tight(0.06, first_game=9000)})

    R.assert_held_out(seasons=[2024], discovery_seasons=[2021, 2022, 2023])
    with pytest.raises(R.NotHeldOut):
        R.assert_held_out(seasons=[], discovery_seasons=[2021])


def test_an_unreadable_discovery_window_is_refused_rather_than_read_as_empty():
    """An empty discovery window makes every season look held out.

    That is the silent version of the failure above and the reason
    `seasons_from_label` raises instead of returning `()`. With no seasons on
    the discovery side, `assert_held_out` finds no overlap and waves through a
    replication run on the very season the rule was selected on.
    """
    assert R.seasons_from_label("2024") == (2024,)
    assert R.seasons_from_label("2021-2024") == (2021, 2022, 2023, 2024)
    for bad in ("", "   ", "twenty-four", "2021-2020", "2021-2022-2023"):
        with pytest.raises(R.ReplicationError):
            R.seasons_from_label(bad)

    cell = ("moneyline", Tier.LOW_MAJOR.value)
    discovery = discovery_record({cell: tight(0.06)}, season_label="")
    with pytest.raises(R.ReplicationError):
        build(discovery=discovery, holdout={2024: tight(0.06, first_game=9000)})


def test_the_declared_split_is_coherent_and_a_departure_from_it_is_stated():
    """A holdout chosen after the numbers were seen is not a holdout.

    The split is declared in the module, before any price was bought, so it
    could not have been chosen with a result in view. It has to be internally
    coherent — every declared season inside the bought population, and the two
    halves disjoint — and a run that departs from it has to say so, because
    picking the held-out season after the discovery numbers exist converts a
    pre-registered test into a second look and nothing in the arithmetic would
    show it.
    """
    assert set(R.DECLARED_DISCOVERY_SEASONS) <= set(R.BOUGHT_SEASONS)
    assert set(R.DECLARED_HELD_OUT_SEASONS) <= set(R.BOUGHT_SEASONS)
    assert not set(R.DECLARED_DISCOVERY_SEASONS) & set(R.DECLARED_HELD_OUT_SEASONS)
    assert set(R.DECLARED_DISCOVERY_SEASONS) | set(R.DECLARED_HELD_OUT_SEASONS) == set(
        R.BOUGHT_SEASONS
    )
    # Labelled by the year each season ENDS, matching every other season filter
    # in this repository. An earlier version of this lab labelled by the
    # starting year, which would have made every filter miss on one side.
    assert R.BOUGHT_SEASONS == tuple(sorted(R.BOUGHT_SEASONS))

    cell = ("moneyline", Tier.LOW_MAJOR.value)
    discovery = discovery_record({cell: tight(0.06)}, season_label="2021-2022")

    declared = build(
        discovery=discovery_record({cell: tight(0.06)}, season_label="2021-2023"),
        holdout={2024: tight(0.05, first_game=9000)},
    )
    assert declared["declared_in_advance"] is True
    assert "not the split declared in advance" not in R.render(declared)

    improvised = build(
        discovery=discovery, holdout={2023: tight(0.05, first_game=9000)}
    )
    assert improvised["declared_in_advance"] is False
    assert "**This is not the split declared in advance.**" in R.render(improvised)


def test_a_result_found_on_the_holdout_is_not_a_replication():
    """A cell that demonstrated nothing in discovery cannot have replicated.

    If it demonstrates something on the held-out season, that is a **new
    discovery made on the only clean season this lab had left** — the holdout is
    now spent on it and it has no held-out test of its own. Reading it as a
    confirmation is how a holdout is quietly converted into a second discovery
    window.
    """
    cell = ("moneyline", Tier.LOW_MAJOR.value)
    discovery = discovery_record({cell: noisy(0.02)})
    assert discovery["by_market_and_tier"][0]["verdict"] == S.NO_DEMONSTRATED_EDGE

    record = build(discovery=discovery, holdout={2024: tight(0.08, first_game=9000)})

    assert state_of(record, *cell) == R.NOTHING_TO_REPLICATE
    assert record["markets"][0]["found_on_the_holdout"] is True
    assert "NEW DISCOVERY MADE ON THE HOLDOUT" in why_of(record, *cell)
    report = R.render(record)
    assert "Found on the holdout, which is not a replication" in report
    assert R.REPLICATED not in {r["state"] for r in record["markets"]}


def test_a_cell_must_replicate_in_every_held_out_season():
    """`must_clear_every_season`, and the football lab's verdict defect.

    That lab scored one season and wrote a verdict file, so **the same policy
    under the same script produced opposite verdicts** depending on which season
    had been run last. Pooling two held-out seasons is the identical failure
    with a smoother surface: one good season carries the other.
    """
    cell = ("moneyline", Tier.LOW_MAJOR.value)
    discovery = discovery_record({cell: tight(0.06)}, season_label="2021-2022")

    record = build(
        discovery=discovery,
        holdout={
            2023: tight(0.06, first_game=9000),
            2024: noisy(0.06, first_game=20000),
        },
    )

    assert state_of(record, *cell) == R.DID_NOT_REPLICATE, (
        "one season replicating and one not is not a replication"
    )
    per_season = {d["season"]: d["state"] for d in record["markets"][0]["seasons"]}
    assert per_season == {2023: R.REPLICATED, 2024: R.DID_NOT_REPLICATE}
    report = R.render(record)
    assert "Every held-out season on its own" in report
    assert "never on their pooled average" in report

    assert R.combine_seasons([R.REPLICATED, R.REPLICATED]) == R.REPLICATED
    assert R.combine_seasons([R.REPLICATED, R.REVERSED]) == R.REVERSED
    assert (
        R.combine_seasons([R.NOT_ENOUGH_EVIDENCE, R.DID_NOT_REPLICATE])
        == R.DID_NOT_REPLICATE
    )
    assert R.combine_seasons([]) == R.UNTESTABLE


# --------------------------------------------------------------------------
# Per market and per tier, and nothing pooled standing alone
# --------------------------------------------------------------------------


def test_no_pooled_number_carries_a_replication_state():
    """A pooled row would become a per-tier claim through the wildcard.

    `what_we_can_claim.replication_states` records a row with no tier under the
    key `"*"`, which then applies to **every** tier of that market. A pooled
    Division I state written into `markets` would therefore be reported as a
    claim about a distribution it was never measured on, which is the pooled
    headline this repository forbids, arriving through a side door.
    """
    cells = {
        ("moneyline", Tier.HIGH_MAJOR.value): tight(
            -0.06, tier=Tier.HIGH_MAJOR.value
        ),
        ("moneyline", Tier.LOW_MAJOR.value): tight(0.06),
    }
    discovery = discovery_record(cells)
    record = build(
        discovery=discovery,
        holdout={
            2024: pd.concat(
                [
                    tight(-0.05, tier=Tier.HIGH_MAJOR.value, first_game=9000),
                    tight(0.05, first_game=20000),
                ],
                ignore_index=True,
            )
        },
    )

    assert {r["tier"] for r in record["markets"]} == {
        Tier.HIGH_MAJOR.value,
        Tier.LOW_MAJOR.value,
    }
    assert all(r.get("tier") for r in record["markets"]), (
        "every entry the claims document reads must name its tier"
    )
    for row in record["pooled"] + record["by_tier"]:
        assert "state" not in row

    states = WWCC.replication_states(record)
    assert ("moneyline", "*") not in states
    assert states[("moneyline", Tier.LOW_MAJOR.value)] == R.REPLICATED
    assert states[("moneyline", Tier.HIGH_MAJOR.value)] == R.REPLICATED

    report = R.render(record)
    assert PB.POOLED_CAVEAT in report
    assert "Per tier, across markets" in report


def test_every_measured_number_carries_its_sample_size():
    """A number without a sample size is not a result."""
    cell = ("total_points", Tier.MID_MAJOR.value)
    discovery = discovery_record(
        {cell: tight(0.06, tier=Tier.MID_MAJOR.value)}
    )
    record = build(
        discovery=discovery,
        holdout={
            2024: tight(
                0.05,
                market="total_points",
                tier=Tier.MID_MAJOR.value,
                first_game=9000,
            )
        },
    )
    row = record["markets"][0]
    assert row["holdout_bets"] == 3000
    assert row["holdout_clusters"] == 300
    assert f"{row['holdout_bets']:,}" in why_of(record, *cell)

    report = R.render(record)
    assert "| Held-out bets | Games |" in report
    assert "3,000" in report
    assert "graded held-out bets across" in report


def test_a_second_half_cell_that_replicates_is_a_settlement_suspect_first():
    """*A constant settlement offset replicates by construction.*

    The football lab's largest false finding returned +11.7% over 3,109 held-out
    bets and survived split-half, fragility and a Bonferroni correction across
    twenty markets, because a systematic settlement error is present in every
    window. Second-half markets settle including overtime at most US books and
    not at all of them, and this lab cannot read a book's rulebook.
    """
    cell = ("spread_h2", Tier.LOW_MAJOR.value)
    discovery = discovery_record({cell: tight(0.06, market="spread_h2")})
    record = build(
        discovery=discovery,
        holdout={2024: tight(0.05, market="spread_h2", first_game=9000)},
    )

    assert state_of(record, *cell) == R.REPLICATED
    assert record["markets"][0]["settlement_suspect"] is True
    report = R.render(record)
    assert "replicates by construction" in report
    assert "settlement artefact first and a finding second" in report


# --------------------------------------------------------------------------
# The family-wise correction, and the record the report is a function of
# --------------------------------------------------------------------------


def test_the_correction_is_the_cumulative_count_and_it_can_undo_a_replication():
    """A correction that is not applied is a correction, printed.

    The same held-out numbers replicate under one look and do not under three
    hundred. If the count were the day's rather than the ledger's cumulative
    one, the second of these would read like the first — *a search that runs
    every week is not twelve tests, it is twelve tests a week, forever.*
    """
    cell = ("moneyline", Tier.LOW_MAJOR.value)
    discovery = discovery_record({cell: tight(0.002)})
    holdout = tight(0.002, first_game=9000)

    one = build(discovery=discovery, holdout={2024: holdout}, looks=1)
    many = build(discovery=discovery, holdout={2024: holdout}, looks=300)

    assert one["correction_factor"] == pytest.approx(1.0)
    assert many["correction_factor"] > 1.0
    assert many["correction_factor"] == pytest.approx(S.bonferroni_factor(300))
    assert state_of(one, *cell) == R.REPLICATED
    assert state_of(many, *cell) != R.REPLICATED
    assert f"{300:,} cumulative hypotheses" in R.render(many)


def test_the_report_re_renders_from_the_record_with_no_recomputation(tmp_path):
    """Improving a sentence must never cost a re-run.

    A replication walks every slate day of a season and re-grades every wager in
    it. If a wording change cost that, nobody would make one — they would edit
    the generated markdown by hand, and a hand-edited generated file survives
    exactly one re-run.
    """
    cell = ("moneyline", Tier.LOW_MAJOR.value)
    discovery = discovery_record({cell: tight(0.06)})
    record = build(discovery=discovery, holdout={2024: tight(0.05, first_game=9000)})

    path = R.write_record(record, tmp_path / "cbb_replication.json")
    round_tripped = R.read_record(path)
    assert R.render(round_tripped) == R.render(record)
    assert R.render(json.loads(path.read_text(encoding="utf-8"))) == R.render(record)


def test_a_stale_record_is_refused_rather_than_rendered_with_holes(tmp_path):
    """A record whose shape has changed renders a report with holes and looks fine."""
    path = tmp_path / "cbb_replication.json"
    path.write_text(json.dumps({"record_version": 0}), encoding="utf-8")
    with pytest.raises(R.ReplicationError, match="version 0 record"):
        R.read_record(path)


def test_nothing_to_measure_is_said_in_words():
    """An empty table reads as a null result, and a null result is a claim."""
    discovery = PB.build_record(
        PB.BacktestInputs(season_label="2021-2023", snapshot_phase="card")
    )
    record = build(discovery=discovery, holdout={2024: pd.DataFrame()})

    assert record["markets"] == []
    report = R.render(record)
    # Sentence case at the start of a sentence, exactly as `price_backtest`
    # prints the same words; the phrase itself is the shared constant.
    assert R.NOTHING_TO_MEASURE.capitalize() in report
    assert R.NOTHING_TO_MEASURE == PB.NOTHING_TO_MEASURE
    assert "nothing to put to a held-out season" in report


def test_the_record_is_the_shape_the_claims_document_already_reads():
    """`what_we_can_claim` was written expecting this file. It must find it.

    That module names `data/outputs/cbb_replication.json`, reads a `markets`
    list of `{market, tier, state}` and a `test_label`, and treats the absence
    of a row as *"no held-out test has been run"* rather than as a failure to
    replicate. Those are different claims and the sibling labs have confused
    them before, so the interop is pinned rather than assumed.
    """
    assert R.REPORT_STEM == WWCC.REPLICATION_STEM
    assert R.record_path(CBB, Path("/tmp/x")) == WWCC.replication_path(
        CBB, Path("/tmp/x")
    )
    assert R.record_path(CBB, Path("/tmp/x")).name == "cbb_replication.json"

    cells = {
        ("moneyline", Tier.LOW_MAJOR.value): tight(0.06),
        ("total_points", Tier.LOW_MAJOR.value): noisy(0.02, market="total_points"),
    }
    discovery = discovery_record(cells)
    record = build(
        discovery=discovery,
        holdout={
            2024: pd.concat(
                [
                    tight(0.05, first_game=9000),
                    noisy(0.02, market="total_points", first_game=20000),
                ],
                ignore_index=True,
            )
        },
    )
    states = WWCC.replication_states(record)
    assert states[("moneyline", Tier.LOW_MAJOR.value)] == R.REPLICATED
    assert record["test_label"] == "2024 (held out)"
    # `untestable` is the one state that document skips, and it must mean "no
    # test was run" rather than "the test failed".
    untestable = {"markets": [{"market": "x", "tier": "y", "state": R.UNTESTABLE}]}
    assert WWCC.replication_states(untestable) == {}


# --------------------------------------------------------------------------
# The script, run the way an operator runs it
# --------------------------------------------------------------------------


def load_script():
    spec = importlib.util.spec_from_file_location("cbb_run_replication", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules["cbb_run_replication"] = module
    spec.loader.exec_module(module)
    return module


def run_script(*argv: str) -> tuple[int, str]:
    module = load_script()
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        code = module.main(list(argv))
    return int(code), buffer.getvalue()


def _reseason(games: pd.DataFrame, *, season: int, november: int) -> pd.DataFrame:
    """One fixture season re-labelled as another, dates and ids and all.

    `test_run_price_backtest`'s builders are reused rather than copied: a
    replication fixture that built its store differently from the backtest
    fixture would be testing that two fixtures agree, which is not a fact about
    this repository.
    """
    days = {
        old: f"{november}-11-{10 + index:02d}" for index, old in enumerate(BT.DAYS)
    }
    out = games.copy()
    out["slate_date"] = out["slate_date"].astype(str).map(days)
    out["season"] = season
    out["game_id"] = out["game_id"] + season * 1000
    return out


class TwoSeasons:
    """A discovery season and a held-out season on disk, scored end to end."""

    def __init__(self, root: Path) -> None:
        base = BT.team_games()
        self.discovery_games = _reseason(base, season=DISCOVERY_SEASON, november=2022)
        self.holdout_games = _reseason(base, season=HOLDOUT_SEASON, november=2023)
        self.lab = BT.Lab(root)
        self.lab.games = pd.concat(
            [self.discovery_games, self.holdout_games], ignore_index=True
        )
        self.lab.with_tables()
        store = pd.concat(
            [
                BT.price_store(self.discovery_games).assign(season=DISCOVERY_SEASON),
                BT.price_store(self.holdout_games).assign(season=HOLDOUT_SEASON),
            ],
            ignore_index=True,
        )
        self.lab.with_store(store)
        self.lab.with_ledger(30)
        self.outputs = self.lab.outputs
        self.processed = self.lab.processed
        self.criteria_dir = root / "manual"
        self.criteria_dir.mkdir(parents=True, exist_ok=True)
        # A fixture floor, not the bar. 200 matches `stats.MINIMUM_BETS` so the
        # fixture never prints a number the backtest would have withheld; the
        # real 2,000 is pinned against the real file by its own test, and a
        # 2,000-bet-per-cell fixture would cost minutes of distribution
        # building to assert nothing this file does not already assert.
        (self.criteria_dir / "promotion_criteria.json").write_text(
            json.dumps(
                {
                    "roi_margin_points": 1.5,
                    "require_interval_excludes_zero": True,
                    "minimum_bets": 200,
                    "must_clear_every_season": True,
                    "demotion_roi_floor": -0.02,
                    "demotion_minimum_bets": 500,
                    "declared_on": "2026-09-01",
                }
            ),
            encoding="utf-8",
        )
        self.record_path = R.record_path(CBB, self.outputs)
        self.report_path = R.report_path(CBB, self.outputs)

    def score_discovery(self, spec: str) -> int:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
            return self.lab.run("--model", spec, "--seasons", str(DISCOVERY_SEASON))

    def replicate(self, *argv: str) -> tuple[int, str]:
        return run_script(
            "--processed-dir",
            str(self.processed),
            "--output-dir",
            str(self.outputs),
            "--manual-dir",
            str(self.criteria_dir),
            *argv,
        )


@pytest.fixture(scope="module")
def two_seasons(tmp_path_factory):
    """Score the discovery season once. Every script test below reads this lab.

    Module-scoped because the discovery run builds a real `GameDistribution` per
    game and re-running it per test would trade seconds for nothing.
    """
    root = tmp_path_factory.mktemp("replication")
    lab = TwoSeasons(root)
    model = BT.StubModel(module_name="cbb_stub_model_replication")
    spec = model.register()
    assert lab.score_discovery(spec) == 0, "the discovery run must produce a record"
    lab.model_spec = spec
    return lab


def test_a_missing_discovery_record_is_a_message_and_an_exit_code(tmp_path):
    """No purchase, no backtest, no rule to replicate — and no empty report.

    "Nothing has been replicated" and "nothing replicated" are different claims,
    and today only the first is true.
    """
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    code, output = run_script("--output-dir", str(outputs), "--seasons", "2024")

    assert code == 2
    assert "there is no rule to replicate" in output
    assert not R.record_path(CBB, outputs).exists()
    assert not R.report_path(CBB, outputs).exists()


def test_a_held_out_season_inside_the_discovery_window_is_refused(two_seasons):
    """The script's loudest refusal, with its own exit code and nothing written."""
    code, output = two_seasons.replicate(
        "--model", two_seasons.model_spec, "--seasons", str(DISCOVERY_SEASON)
    )

    assert code == 5
    assert "inside the discovery window" in output
    assert "reproduces the selection rather than the effect" in output
    assert not two_seasons.record_path.exists()
    assert not two_seasons.report_path.exists()


def test_it_scores_the_held_out_season_and_writes_both_outputs(two_seasons):
    """The whole wiring, end to end, on a season the rule was never selected on."""
    code, output = two_seasons.replicate(
        "--model", two_seasons.model_spec, "--seasons", str(HOLDOUT_SEASON)
    )

    assert code == 0, output
    assert two_seasons.record_path.is_file()
    assert two_seasons.report_path.is_file()
    record = json.loads(two_seasons.record_path.read_text(encoding="utf-8"))

    assert record["held_out_seasons"] == [HOLDOUT_SEASON]
    assert record["discovery_seasons"] == [DISCOVERY_SEASON]
    assert not set(record["held_out_seasons"]) & set(record["discovery_seasons"])
    assert record["declared_in_advance"] is True
    assert record["holdout"]["bets_graded"] > 0
    assert record["markets"], "the discovery record measured cells to put to a holdout"
    assert {r["state"] for r in record["markets"]} <= set(R.STATES)
    # The rule is the discovery run's, not a new one.
    discovery = json.loads(
        PB.record_path(CBB, two_seasons.outputs).read_text(encoding="utf-8")
    )
    assert record["edge_threshold"] == discovery["edge_threshold"]
    assert record["snapshot_phase"] == discovery["snapshot_phase"]
    # Every held-out game is in the held-out season and none is a discovery game.
    holdout_ids = set(two_seasons.holdout_games["game_id"])
    discovery_ids = set(two_seasons.discovery_games["game_id"])
    assert not holdout_ids & discovery_ids

    report = two_seasons.report_path.read_text(encoding="utf-8")
    assert "merely fails to contradict is not confirmation" in report
    assert S.NO_DEMONSTRATED_EDGE in report
    assert "REPLICATION, PER MARKET AND PER CONFERENCE TIER" in output


def test_the_run_reads_the_ledgers_cumulative_count(two_seasons):
    """Never the day's. The correction in the record is the one on disk."""
    record = json.loads(two_seasons.record_path.read_text(encoding="utf-8"))
    ledger = E.load(two_seasons.outputs / LEDGER_FILENAME)

    assert record["looks"] == ledger.count
    assert record["looks"] >= 30, "the fixture ledger holds thirty prior hypotheses"
    assert record["correction_factor"] == pytest.approx(
        S.bonferroni_factor(record["looks"])
    )
    assert "cumulative" in two_seasons.report_path.read_text(encoding="utf-8")


def test_the_holdout_is_counted_in_the_ledger_before_it_is_taken(tmp_path):
    """*Putting a discovery finding to the holdout IS a second look.*

    `Hypothesis.key()` puts the stage in the dedupe key for exactly this, and
    the whole design collapses if a holdout is not counted. Recorded before the
    scoring, because a predicted direction written after the number is seen is
    not a prediction — and the direction recorded is the sign of the discovery
    result, which is the one thing a replication predicts.

    Cells with nothing to replicate spend no degree of freedom and are not
    recorded, the same line `scripts/record_experiments.py` draws around
    retention probing.
    """
    script = load_script()
    ledger_path = tmp_path / LEDGER_FILENAME
    claims = [
        {"market": "moneyline", "tier": "low_major", "claims": True, "sign": 1},
        {"market": "spread", "tier": "high_major", "claims": True, "sign": -1},
        {"market": "total_points", "tier": "low_major", "claims": False, "sign": 1},
    ]

    added, planned = script.record_holdout_looks(
        claims, seasons=[2024], ledger_path=ledger_path, tested_on="2026-09-03"
    )

    assert (added, planned) == (2, 2), "a cell with no claim spends no degree of freedom"
    ledger = E.load(ledger_path)
    assert ledger.by_stage()["holdout"] == 2
    directions = {h.name.split(":")[0]: h.predicted_direction for h in ledger.hypotheses}
    assert directions["moneyline / low_major"] == "higher"
    assert directions["spread / high_major"] == "lower"

    # Re-running must not inflate the correction, or nobody will re-run anything.
    again, _ = script.record_holdout_looks(
        claims, seasons=[2024], ledger_path=ledger_path, tested_on="2026-09-03"
    )
    assert again == 0
    assert E.load(ledger_path).count == 2


def test_rebuild_report_only_re_renders_without_the_store_or_the_tables(
    two_seasons, tmp_path
):
    """Improving a sentence must never cost a re-run, and must not need the data."""
    elsewhere = tmp_path / "outputs"
    elsewhere.mkdir()
    (elsewhere / R.record_path(CBB, elsewhere).name).write_text(
        two_seasons.record_path.read_text(encoding="utf-8"), encoding="utf-8"
    )

    code, output = run_script(
        "--output-dir",
        str(elsewhere),
        "--processed-dir",
        str(tmp_path / "does-not-exist"),
        "--rebuild-report-only",
    )

    assert code == 0, output
    assert R.report_path(CBB, elsewhere).is_file()
    assert "Nothing was re-scored" in output
    assert R.report_path(CBB, elsewhere).read_text(
        encoding="utf-8"
    ) == two_seasons.report_path.read_text(encoding="utf-8")


def test_rebuild_report_only_without_a_record_says_so_and_exits_non_zero(tmp_path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    code, output = run_script("--output-dir", str(outputs), "--rebuild-report-only")
    assert code == 2
    assert "there is no record to re-render" in output
