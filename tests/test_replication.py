"""Replication on a held-out season, and the one sentence it exists to enforce.

`price_backtest.py` ends by naming `replication.py` and specifying it in a
sentence: *"It cannot replicate itself. A held-out season is `replication.py`'s
job, and a window that merely fails to contradict is not confirmation."* Every
test here is named for a specific way that sentence could be broken, and the
first one reproduces the sibling lab's version of the mistake before anything
else is asserted.

The failure modes this file was built around. The list is maintained by hand
and nothing enforces it, so it is a reading aid rather than a coverage claim --
it went five modes out of date once already, and a reader who audits coverage
from it and concludes a guard is unreached is the way a guard gets deleted.
Read the test names for what is actually covered:

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
* **A replication that no longer describes the discovery run it names**, and
  the three quieter halves of that: a discovery record that is present and
  cannot be parsed, a record that never stamped what it was built against, and
  an absent discovery record — which is the one case that is not a refusal, and
  so is the one that must be said out loud rather than passed over in silence.

The end-to-end tests build two seasons on disk out of `test_run_price_backtest`'s
own fixture builders rather than a second copy of them, score the first with the
real backtest script and hold the second out. That is deliberate: a replication
fixture that built its store differently from the backtest fixture would be
testing that two fixtures agree.
"""

from __future__ import annotations

import contextlib
import dataclasses
import importlib.util
import io
import json
import shutil
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
        # Tests are not looks: give the script a ledger under its own outputs
        # rather than the repository's one, which it now defaults to.
        argv = list(argv)
        if "--ledger" not in argv and "--output-dir" in argv:
            argv += ["--ledger", str(Path(argv[argv.index("--output-dir") + 1]) / "experiment_ledger.json")]
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

    def replicate(self, *argv: str, output_dir: Path | None = None) -> tuple[int, str]:
        """The script against this lab's tables, writing to `output_dir`.

        `output_dir` defaults to the shared `self.outputs`, which is what every
        test that wants the real end-to-end run uses. A test asserting that a
        refusal wrote NOTHING passes its own directory instead: an absence in
        the shared tree is an assertion about what every other test in the
        module did, and this module has two things that write the record there.
        """
        return run_script(
            "--processed-dir",
            str(self.processed),
            "--output-dir",
            str(self.outputs if output_dir is None else output_dir),
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


def test_a_held_out_season_inside_the_discovery_window_is_refused(
    two_seasons, tmp_path
):
    """The script's loudest refusal, with its own exit code and nothing written.

    In an output tree of its own, holding nothing but the discovery record the
    refusal has to read before it can tell the seasons overlap. "Nothing
    written" asserted against the SHARED tree was an assertion about what every
    other test in this module had done: `test_it_scores_the_held_out_season_
    and_writes_both_outputs` writes that record, and so does the `replicated`
    fixture, so the assert held only while this test happened to run first.
    `pytest tests/test_replication.py::test_a_rebuild_beside_the_discovery_run_
    it_names_re_renders_and_says_nothing ::test_a_held_out_season_inside_the_
    discovery_window_is_refused` reds the second of the two on that line. Here
    the tree is this test's own, so the absence is this refusal's.
    """
    alone = tmp_path / "discovery-only"
    alone.mkdir()
    shutil.copy(PB.record_path(CBB, two_seasons.outputs), PB.record_path(CBB, alone))
    record_path, report_path = R.record_path(CBB, alone), R.report_path(CBB, alone)
    assert not record_path.exists() and not report_path.exists(), (
        "this test's own tree already holds the outputs whose absence it is "
        "about to assert"
    )

    code, output = two_seasons.replicate(
        "--model",
        two_seasons.model_spec,
        "--seasons",
        str(DISCOVERY_SEASON),
        output_dir=alone,
    )

    assert code == 5
    assert "inside the discovery window" in output
    assert "reproduces the selection rather than the effect" in output
    assert not record_path.exists()
    assert not report_path.exists()


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


def test_the_run_reads_the_ledgers_cumulative_count(replicated):
    """Never the day's. The correction in the record is the one on disk.

    On `replicated` rather than `two_seasons` for the reason the staleness
    tests below are: the record and report this reads are written by
    `test_it_scores_the_held_out_season_and_writes_both_outputs`, and reading
    them off the raw fixture makes this test's result depend on TEST ORDER
    rather than on the code. Standalone it red on a missing record, for a
    reason that had nothing to do with the cumulative count.
    """
    record = json.loads(replicated.record_path.read_text(encoding="utf-8"))
    ledger = E.load(replicated.outputs / LEDGER_FILENAME)

    assert record["looks"] == ledger.count
    assert record["looks"] >= 30, "the fixture ledger holds thirty prior hypotheses"
    assert record["correction_factor"] == pytest.approx(
        S.bonferroni_factor(record["looks"])
    )
    assert "cumulative" in replicated.report_path.read_text(encoding="utf-8")


def test_the_holdout_is_counted_in_the_ledger_before_it_is_taken(tmp_path):
    """*Putting a discovery finding to the holdout IS a second look.*

    `Hypothesis.key()` puts the stage in the dedupe key for exactly this, and
    the whole design collapses if a holdout is not counted. Recorded before the
    scoring, because a predicted direction written after the number is seen is
    not a prediction — and the direction recorded is the sign of the discovery
    result, which is the one thing a replication predicts.

    A cell the discovery window claimed nothing in is STILL a look — the
    replication reads its held-out interval to say whether something was found
    on the holdout — so it is recorded too, as a two-sided hypothesis with no
    sign to carry. Until 2026-09-05 such cells were skipped and the family
    correction was short by exactly those looks.
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

    assert (added, planned) == (3, 3), "every cell scored on the holdout is a look"
    ledger = E.load(ledger_path)
    assert ledger.by_stage()["holdout"] == 3
    directions = {h.name.split(":")[0]: h.predicted_direction for h in ledger.hypotheses}
    assert directions["moneyline / low_major"] == "higher"
    assert directions["spread / high_major"] == "lower"
    # The unclaimed cell's discovery sign was +1 and must NOT be carried in: a
    # sign that did not survive its correction is not a prediction.
    assert directions["total_points / low_major"] == E.TWO_SIDED

    # Re-running must not inflate the correction, or nobody will re-run anything.
    again, _ = script.record_holdout_looks(
        claims, seasons=[2024], ledger_path=ledger_path, tested_on="2026-09-03"
    )
    assert again == 0
    assert E.load(ledger_path).count == 3


def test_every_cell_scored_on_the_holdout_is_a_recorded_look_not_only_the_claimed_ones(tmp_path):
    """N discovery cells of which K claimed -> N holdout hypotheses, not K.

    `replication.build_record` scores EVERY discovery cell on the held-out
    seasons. `record_holdout_looks` used to append one hypothesis only
    `if claim.get("claims") and claim.get("sign")`, so the ledger held K looks
    while N were taken and the correction on every held-out interval was
    computed across too small a family. The claimed cells carry the discovery
    sign; the rest are two-sided; the key `(search, name, seasons, stage)` is
    distinct per cell so no two cells collapse into one entry.
    """
    script = load_script()
    ledger_path = tmp_path / LEDGER_FILENAME
    markets = ["moneyline", "spread", "total_points", "team_total"]
    tiers = ["high_major", "mid_major", "low_major"]
    cells = [(m, t) for m in markets for t in tiers]  # N = 12
    n_cells = len(cells)
    claimed = {("moneyline", "low_major"): 1, ("spread", "mid_major"): -1}  # K = 2
    claims = [
        {
            "market": m,
            "tier": t,
            "claims": (m, t) in claimed,
            # Every cell has a sign — an ROI is never exactly zero — so the
            # filter under test cannot be satisfied by an absent sign alone.
            "sign": claimed.get((m, t), 1),
        }
        for m, t in cells
    ]
    assert sum(c["claims"] for c in claims) == 2 < n_cells

    added, planned = script.record_holdout_looks(
        claims, seasons=[2024], ledger_path=ledger_path, tested_on="2026-09-05"
    )

    assert (added, planned) == (n_cells, n_cells), (
        f"{planned} holdout hypotheses recorded for {n_cells} cells scored — the "
        "family correction undercounts by every unrecorded look"
    )
    ledger = E.load(ledger_path)
    assert ledger.count == n_cells
    assert ledger.by_stage()["holdout"] == n_cells
    assert ledger.by_stage()["discovery"] == 0
    assert len({h.key() for h in ledger.hypotheses}) == n_cells, "two cells share a key"
    by_cell = {h.name.split(":")[0]: h for h in ledger.hypotheses}
    assert by_cell["moneyline / low_major"].predicted_direction == "higher"
    assert by_cell["spread / mid_major"].predicted_direction == "lower"
    unclaimed = [h for name, h in by_cell.items() if tuple(name.split(" / ")) not in claimed]
    assert len(unclaimed) == n_cells - 2
    assert {h.predicted_direction for h in unclaimed} == {E.TWO_SIDED}
    assert all(h.stage == "holdout" for h in ledger.hypotheses)
    # A two-sided look can fail but never reverse; a directed one can.
    for h in unclaimed:
        assert not dataclasses.replace(h, realised_direction="lower").reversed_prediction()
    assert dataclasses.replace(
        by_cell["moneyline / low_major"], realised_direction="lower"
    ).reversed_prediction()

    # The ledger's own correction now widens across N looks, not K.
    assert S.bonferroni_factor(ledger.count) > S.bonferroni_factor(2)


def test_a_two_sided_look_is_admitted_at_the_holdout_stage_only():
    """The discovery stage still refuses a cut written without a direction."""
    E.Hypothesis(
        search="s", name="n", tested_on="d", seasons=(2024,), outcome="pending",
        predicted_direction=E.TWO_SIDED, stage="holdout",
    )
    with pytest.raises(E.DirectionRequired):
        E.Hypothesis(
            search="s", name="n", tested_on="d", seasons=(2024,), outcome="pending",
            predicted_direction=E.TWO_SIDED, stage="discovery",
        )
    with pytest.raises(E.DirectionRequired):
        E.Hypothesis(
            search="s", name="n", tested_on="d", seasons=(2024,), outcome="pending",
            predicted_direction="", stage="holdout",
        )


def test_rebuild_report_only_re_renders_without_the_store_or_the_tables(
    replicated, tmp_path
):
    """Improving a sentence must never cost a re-run, and must not need the data.

    On `replicated` rather than `two_seasons` for the same reason the staleness
    tests below are: the record this reads is written by the end-to-end test,
    and depending on that is depending on test order.
    """
    elsewhere = tmp_path / "outputs"
    elsewhere.mkdir()
    (elsewhere / R.record_path(CBB, elsewhere).name).write_text(
        replicated.record_path.read_text(encoding="utf-8"), encoding="utf-8"
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
    ) == replicated.report_path.read_text(encoding="utf-8")


def test_rebuild_report_only_without_a_record_says_so_and_exits_non_zero(tmp_path):
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    code, output = run_script("--output-dir", str(outputs), "--rebuild-report-only")
    assert code == 2
    assert "there is no record to re-render" in output


def _fields_named_missing(reason: str) -> list[str]:
    """The field names the cannot-answer refusal says the stamp is missing.

    Read out of the sentence rather than searched for inside it. The same
    reason also names every compared field in its "`build_record` stamps all
    of ..." clause, so `"days" in reason` is true whether the refusal listed
    `days` as missing or not — a test built on that substring would pass
    against a refusal that named nothing.
    """
    head, _, tail = reason.partition("stamp is missing ")
    assert head and tail, f"not a cannot-answer refusal: {reason}"
    listed, _, _ = tail.partition(" —")
    return [name.strip() for name in listed.split(",") if name.strip()]


def test_the_compared_discovery_fields_are_the_five_the_record_stamps():
    """The list, written out, and held against what `build_record` writes.

    `COMPARED_DISCOVERY_FIELDS` is read by the refusal, by the comparison and
    by the tests below, so a test that spells it `R.COMPARED_DISCOVERY_FIELDS`
    asserts nothing about its contents: dropping `days` from the tuple drops it
    from the expectation in the same edit and the suite stays green. Measured
    -- that mutation left all 35 green before this test existed.

    So the five names are LITERAL here, and they are held against the record a
    real run writes rather than against the constant: `build_record` stamps
    eight keys and these are the five that identify the discovery run. The
    other three describe the replication and could not identify anything.
    """
    assert R.COMPARED_DISCOVERY_FIELDS == (
        "generated_at",
        "bets_graded",
        "wagers_graded",
        "games",
        "days",
    )
    stamp = json.loads(
        (REPO / "data/outputs/holdout/cbb_replication.json").read_text(
            encoding="utf-8"
        )
    )["discovery"]
    assert set(R.COMPARED_DISCOVERY_FIELDS) <= set(stamp), (
        "the check requires a field the committed record does not carry, so "
        "`--rebuild-report-only` refuses the lab's own published replication"
    )
    assert set(stamp) - set(R.COMPARED_DISCOVERY_FIELDS) == {
        "cells",
        "claims",
        "looks_when_scored",
    }, (
        "`build_record` writes a discovery key this list neither compares nor "
        "names as uncompared, so nobody knows which of the two it is"
    )


def test_a_replication_that_no_longer_describes_its_discovery_run_is_refused(tmp_path):
    """The record stamps the discovery run; nothing ever read the stamp back.

    `build_record` has always written `discovery.generated_at`, `bets_graded`,
    `wagers_graded`, `games` and `days` — the exact key that proves the two
    records still belong together. `record["discovery"]["generated_at"]`
    appeared once in the whole repository: at the line that writes it. So a
    discovery re-score left the replication quoting a run that no longer
    existed, and `--rebuild-report-only` re-rendered the quotation without
    re-reading anything. Measured 2026-09-17, the committed pair were nine days
    and 8,593 bets apart and nothing said so.

    Both directions are asserted. A pair that agrees must return no reasons —
    otherwise the check is a permanent red that gets switched off — and each
    kind of disagreement must be named with BOTH figures, because "the
    discovery run is newer" is an assertion and two timestamps is a fact.
    """
    discovery = tmp_path / "cbb_price_backtest.json"
    stamped = {
        "generated_at": "2026-09-17T15:56:40Z",
        "bets_graded": 110_682,
        "wagers_graded": 411_034,
        "games": 16_812,
        "days": 513,
    }
    discovery.write_text(json.dumps(stamped), encoding="utf-8")
    record = {"discovery": dict(stamped)}

    assert R.stale_discovery(record, discovery) == [], (
        "a replication and the discovery record it names, in agreement, are "
        "reported stale — so the check would be red from the day it landed"
    )

    discovery.write_text(
        json.dumps({**stamped, "generated_at": "2026-09-18T09:00:00Z"}), encoding="utf-8"
    )
    reasons = R.stale_discovery(record, discovery)
    assert len(reasons) == 1 and "2026-09-18T09:00:00Z" in reasons[0]
    assert "2026-09-17T15:56:40Z" in reasons[0], (
        "the reason names only the new stamp, so a reader cannot check it "
        "against what the record claims"
    )

    discovery.write_text(
        json.dumps({**stamped, "bets_graded": 119_275}), encoding="utf-8"
    )
    reasons = R.stale_discovery(record, discovery)
    assert len(reasons) == 1 and "119,275" in reasons[0] and "110,682" in reasons[0]

    # EVERY COUNT SEPARATELY, because four fields compared in one loop are four
    # terms of the same formula and a fixture that moves only one of them tests
    # only one. The four stamped values are deliberately far apart, so a reason
    # that named the wrong field would carry the wrong figures too. Dropping
    # `days` from the compared tuple left the whole file green before this
    # loop existed.
    for field in ("bets_graded", "wagers_graded", "games", "days"):
        moved = int(stamped[field]) + 1
        discovery.write_text(json.dumps({**stamped, field: moved}), encoding="utf-8")
        reasons = R.stale_discovery(record, discovery)
        assert len(reasons) == 1, (
            f"moving {field} alone produced {len(reasons)} reasons: {reasons}"
        )
        assert f"{moved:,} {field}" in reasons[0], (
            f"{field} moved and the refusal does not say so: {reasons[0]}"
        )
        assert f"{int(stamped[field]):,}" in reasons[0], (
            f"the reason names the new {field} and not the stamped one, so a "
            f"reader cannot check it against the record: {reasons[0]}"
        )

    # An ABSENT discovery record is "cannot check", not "disagrees". Refusing
    # there would make this a permanent red in any record-only tree — a rebuild
    # from a distributed record, a test world that writes no discovery file —
    # and a check that is always red is a check somebody deletes. The script
    # warns instead; only a pair that is present and disagrees is refused.
    discovery.unlink()
    assert R.stale_discovery(record, discovery) == []

    # A discovery record that is PRESENT and cannot be parsed is neither of
    # those. Nothing was compared, and something is sitting there claiming to
    # be the run this replication names, so the failure to read it is the
    # answer -- reporting `[]` here would be the shape this whole check exists
    # to close: an unreadable file rendering as a pair that agrees.
    discovery.write_text('{"generated_at": "2026-09-1', encoding="utf-8")
    reasons = R.stale_discovery(record, discovery)
    assert len(reasons) == 1, reasons
    assert "could not be read" in reasons[0] and discovery.name in reasons[0]

    # A record whose stamp cannot IDENTIFY THE RUN cannot answer at all, and
    # cannot-answer is reported as a failure rather than as a pass. This is the
    # discipline of the sibling this function's docstring says it copies:
    # `what_we_can_claim.stale_inputs` returns a reason for a record with no
    # `evidence_inputs`, and `test_a_record_that_never_wrote_down_what_it_read_
    # cannot_pass_the_check` holds it to returncode 1. This branch used to
    # return `[]` -- the same list an agreeing pair returns, indistinguishable
    # at the call site -- and the caller's absent-file warning does not cover
    # it, because that warning is keyed on the FILE being missing.
    discovery.write_text(json.dumps(stamped), encoding="utf-8")
    unstamped = R.stale_discovery({"discovery": {}}, discovery)
    assert len(unstamped) == 1, unstamped
    assert "does not write down which discovery run" in unstamped[0]
    assert R.stale_discovery({}, discovery) == unstamped, (
        "a record with no `discovery` key at all is treated differently from "
        "one with an empty stamp, and neither of them can answer"
    )
    # A `discovery` key that is not a MAPPING refuses too. Both shapes below,
    # because they are not interchangeable: a string is missing every field
    # under `in` and would refuse even without the `isinstance` guard, while a
    # LIST of the field names CONTAINS all five under `in` — so it walks past
    # the refusal and raises `AttributeError` on the first `.get`. A fixture of
    # only the string tests the guard not at all. Measured: with the guard
    # replaced by `unstamped or {}`, the string case stays green.
    assert R.stale_discovery({"discovery": "2026-09-17"}, discovery) == unstamped
    assert (
        R.stale_discovery(
            {"discovery": list(R.COMPARED_DISCOVERY_FIELDS)}, discovery
        )
        == unstamped
    ), (
        "a `discovery` key that is a list rather than a mapping raises out of "
        "the check instead of refusing, so a hand-edited record crashes the "
        "re-render rather than being told what is wrong with it"
    )

    # AND THE REFUSAL IS KEYED ON THE COMPARED FIELDS, NOT ON THE STAMP BEING
    # EMPTY. `build_record` writes EIGHT keys into `discovery` and only five
    # are ever read back, so a stamp truncated down to the other three is
    # still a stamp -- truthy, non-empty -- and identifies no run whatever.
    # `if not stamped` was false for it, every comparison above was skipped,
    # and `[]` came back: the agreeing pair's answer, for a record that cannot
    # be asked. Both directions are asserted here, because a refusal keyed too
    # WIDELY is the permanent red that gets the check deleted.
    uncompared = {"cells": 32, "claims": 1, "looks_when_scored": 130}
    truncated = R.stale_discovery({"discovery": dict(uncompared)}, discovery)
    assert len(truncated) == 1, truncated
    assert "does not write down which discovery run" in truncated[0]
    # Read the missing-list out of the sentence rather than looking for each
    # name anywhere in it: the same sentence also names every compared field in
    # its "`build_record` stamps all of ..." clause, so a bare substring search
    # would pass against a refusal that listed nothing at all.
    assert _fields_named_missing(truncated[0]) == list(R.COMPARED_DISCOVERY_FIELDS), (
        "the refusal does not name the fields the stamp is missing, so a "
        f"reader cannot tell what was cut out of it: {truncated[0]}"
    )
    # Every compared field alone is enough to lose, and losing any one of them
    # loses the ability to answer: a fixture that dropped them all together
    # would pass just as well against a check that required only ONE of them.
    for field in R.COMPARED_DISCOVERY_FIELDS:
        one_short = {k: v for k, v in stamped.items() if k != field}
        reasons = R.stale_discovery({"discovery": one_short}, discovery)
        assert len(reasons) == 1 and _fields_named_missing(reasons[0]) == [field], (
            f"a stamp missing only {field} is compared on the four that "
            f"remain and reported as agreeing: {reasons}"
        )
    # And the whole eight-key stamp `build_record` really writes still agrees.
    assert R.stale_discovery({"discovery": {**stamped, **uncompared}}, discovery) == [], (
        "the shape `build_record` actually writes is reported stale, so the "
        "check is red on every record this lab produces"
    )
    # An absent `generated_at` is not the same as a truncated one. The stamp is
    # written as `str(discovery.get("generated_at", ""))`, so a discovery run
    # with no timestamp is stamped `""` -- a record that answered honestly, and
    # the four counts still carry the comparison.
    empty_timestamp = {**stamped, "generated_at": ""}
    discovery.write_text(json.dumps(empty_timestamp), encoding="utf-8")
    assert R.stale_discovery({"discovery": dict(empty_timestamp)}, discovery) == [], (
        "a discovery run that filed no timestamp is refused as a truncated "
        "record, which makes the check red on a record nothing edited"
    )
    discovery.write_text(json.dumps(stamped), encoding="utf-8")


# --------------------------------------------------------------------------
# The staleness check, driven through the script rather than called directly
# --------------------------------------------------------------------------
#
# `stale_discovery` has its own unit test above. These six drive the WIRING:
# `--rebuild-report-only` reading a record off disk, deciding whether the
# discovery record beside it is the one that record was built against, and
# saying so in its own output with its own exit code. Measured by mutation
# before they were written: `stale = []` in `rebuild_report_only`, and deleting
# the whole absent-record warning, each left the suite green. The check existed,
# the function was tested, and nothing executed the path that uses it — which is
# the same shape as the defect it was written to catch.
#
# The four states the pair can be in, one test each, because they are four
# different answers and only one of them is a pass:
#
#   present and agrees        -> re-render, say nothing
#   present and disagrees     -> refuse
#   present and unreadable    -> refuse, naming the file it could not read
#   absent                    -> re-render, and say the pair went UNCHECKED
#
# and a fifth and sixth for the record whose stamp cannot IDENTIFY the run —
# absent entirely, or truncated down to the three keys `build_record` writes
# and this check never compares. Neither is a question about the pair; both are
# questions about the record, and no file can answer either, so both refuse.
# The first three, the fifth and the sixth used to be one branch as far as the
# caller could see — `[]` — and four of them are the shape "could not check,
# rendered as a pass". The sixth is its own test because the fifth's condition
# (`if not stamped`) was FALSE for it: a stamp that keeps any key at all is
# truthy, so the empty-stamp test could not have caught it.
#
# One deviation per test. The agreeing pair is the real one the fixture
# produced, so a test that passes here cannot be passing because its fixture
# satisfied some other guard at the same time.


@pytest.fixture(scope="module")
def replicated(two_seasons):
    """`two_seasons` with its held-out run scored, produced here rather than assumed.

    The tests below read `two_seasons.record_path`, which is written by
    `test_it_scores_the_held_out_season_and_writes_both_outputs`. Depending on
    that is depending on TEST ORDER: running one of them alone, deselecting the
    end-to-end test, or any random-order plugin would red them for a reason
    that has nothing to do with the code under test. The fixture is
    module-scoped like `two_seasons`, so when the end-to-end test has already
    run this costs a `is_file()`, and when it has not it scores the holdout
    itself.

    That second case means this fixture WRITES `two_seasons.record_path`, so it
    is a second producer of the shared tree's outputs. Any test asserting those
    outputs are absent would then be asserting something this fixture can
    falsify -- which is why `test_a_held_out_season_inside_the_discovery_
    window_is_refused` asserts the absence in an output tree of its own
    instead, and why every test that READS the record depends on this fixture
    rather than on `two_seasons`.
    """
    if not two_seasons.record_path.is_file():
        code, output = two_seasons.replicate(
            "--model", two_seasons.model_spec, "--seasons", str(HOLDOUT_SEASON)
        )
        assert code == 0, output
    assert two_seasons.record_path.is_file(), (
        "the held-out run exited 0 and wrote no record, so there is nothing "
        "for the staleness tests below to rebuild from"
    )
    return two_seasons


def _a_replication_record_of_its_own(replicated, destination: Path) -> Path:
    """The replication record alone, in a tree with no store and no report.

    The discovery record is deliberately NOT copied: each test below puts it
    there itself, or does not, or puts an unreadable one there, because that is
    the one thing each of them varies. A helper that copied both would make the
    absent case a second helper, and the two would drift.
    """
    destination.mkdir(parents=True, exist_ok=True)
    shutil.copy(replicated.record_path, R.record_path(CBB, destination))
    assert not R.report_path(CBB, destination).exists(), (
        "the report must not pre-exist, or 'the refusal wrote nothing' below "
        "would be satisfied by a file the refusal never touched"
    )
    return destination


def _the_discovery_run_it_was_built_against(replicated, destination: Path) -> Path:
    """The very discovery record the fixture's replication was scored against."""
    source = PB.record_path(CBB, replicated.outputs)
    assert source.is_file(), "the fixture's discovery run must have written one"
    target = PB.record_path(CBB, destination)
    shutil.copy(source, target)
    return target


def _reasons_printed(output: str) -> list[str]:
    """The individual reason lines of a refusal, which the caller indents.

    Counting them is the difference between "the refusal named the thing I
    changed" and "the refusal named the thing I changed and nothing else".
    """
    return [line for line in output.splitlines() if line.startswith("::error::  ")]


def test_a_rebuild_beside_the_discovery_run_it_names_re_renders_and_says_nothing(
    replicated, tmp_path
):
    """The agreeing direction, asserted first, because it is the one that rots.

    A staleness check that complains about a pair which genuinely agrees is a
    permanent red, and a permanent red is a check somebody switches off. So the
    real pair the fixture produced — this replication and the discovery record
    it was actually scored against — must re-render silently: no refusal, and
    no "could not check" either, because the record IS beside it and it WAS
    checked.

    Mutation: make the absent-record branch in `rebuild_report_only` fire
    unconditionally (`if discovery_path is not None:`). This goes red on the
    warning, along with the two refusal tests below that also assert the run
    did not claim the file was missing; the absent-record test stays green,
    which is the point — the warning must fire there and nowhere else.
    """
    beside = _a_replication_record_of_its_own(replicated, tmp_path / "agreeing")
    _the_discovery_run_it_was_built_against(replicated, beside)

    code, output = run_script(
        "--output-dir",
        str(beside),
        "--processed-dir",
        str(tmp_path / "does-not-exist"),
        "--rebuild-report-only",
    )

    assert code == 0, output
    assert R.report_path(CBB, beside).is_file()
    assert "no longer describes the discovery run" not in output, (
        "a pair that agrees is called stale, so the check is red from the day "
        "it lands and the next person deletes it"
    )
    assert "is not beside this record" not in output, (
        "the discovery record is beside this one and was read, so reporting "
        "the pair as unchecked understates what the run actually did"
    )


def test_a_rebuild_whose_discovery_run_was_re_scored_underneath_it_is_refused(
    replicated, tmp_path
):
    """The disagreeing direction, through the script, with both figures named.

    The record stamps `discovery.bets_graded`; a re-scored discovery run leaves
    the replication quoting a count that no longer exists. Re-rendering then
    republishes a comparison that is no longer between those two things, so
    this path refuses rather than warns — the report's whole subject is whether
    a discovery finding held out, and that sentence means nothing once the
    discovery half has moved.

    Exactly one field is moved, so exactly one reason is expected: the printed
    reasons are COUNTED and the untouched `generated_at` reason is asserted
    absent, because a test that merely looked for its own substring would pass
    just as well on a refusal that fired for a second, unrelated reason.

    Mutation: `stale = []` in `rebuild_report_only` — 3 failed, 31 passed:
    this and the two refusal tests below it, which are the three that consume
    the check. The agreeing and absent cases stay green, because `[]` is the
    right answer for both of them.
    """
    beside = _a_replication_record_of_its_own(replicated, tmp_path / "re-scored")
    discovery_path = _the_discovery_run_it_was_built_against(replicated, beside)

    stamped = json.loads(
        R.record_path(CBB, beside).read_text(encoding="utf-8")
    )["discovery"]
    was = int(stamped["bets_graded"])
    discovery = json.loads(discovery_path.read_text(encoding="utf-8"))
    discovery["bets_graded"] = was + 8_593
    discovery_path.write_text(json.dumps(discovery), encoding="utf-8")

    code, output = run_script(
        "--output-dir",
        str(beside),
        "--processed-dir",
        str(tmp_path / "does-not-exist"),
        "--rebuild-report-only",
    )

    assert code == 2, output
    assert "no longer describes the discovery run it names" in output
    printed = _reasons_printed(output)
    assert len(printed) == 1, (
        "one field was moved and the refusal printed "
        f"{len(printed)} reasons: {printed}. A second reason means either this "
        "test is passing on a disagreement it did not create, or the check "
        "reports the same move twice"
    )
    assert "was generated at" not in output, (
        "the discovery record's `generated_at` was not touched and the refusal "
        "reports it as changed, so the reason that made this test pass is not "
        "the reason it was written for"
    )
    assert f"{was + 8_593:,} bets_graded" in output and f"{was:,}" in output, (
        "the refusal names one side of the disagreement, so a reader cannot "
        "check it against what the record claims"
    )
    assert "Re-run the replication rather than re-rendering it." in output
    assert not R.report_path(CBB, beside).is_file(), (
        "the refusal still wrote the report, which is the republication it "
        "exists to prevent"
    )


def test_a_rebuild_with_no_discovery_record_beside_it_says_it_could_not_check(
    replicated, tmp_path
):
    """An absent discovery record renders as UNCHECKED, never as agreement.

    This is the half that matters. `stale_discovery` returns `[]` for a file it
    cannot read, and that is the honest answer — cannot-check is not disagrees,
    and refusing in a record-only tree would make the check a permanent red. But
    `[]` is also exactly what an agreeing pair returns, so the two are
    indistinguishable at the call site, and a run that could not check would
    otherwise be reported as a run that checked and found nothing wrong.

    So the caller has to say which one happened, and this asserts that it does:
    the re-render still succeeds, and the output says the pair is unchecked
    rather than checked and found fine. Without this assertion the absent case
    reads as a pass, which is the one shape this repository keeps shipping.

    Mutation: delete the warning in `rebuild_report_only` — the run still exits
    0 and still writes the report, every other test here stays green, and only
    this one goes red.
    """
    beside = _a_replication_record_of_its_own(replicated, tmp_path / "record-only")
    assert not PB.record_path(CBB, beside).exists(), "nothing to check against"

    code, output = run_script(
        "--output-dir",
        str(beside),
        "--processed-dir",
        str(tmp_path / "does-not-exist"),
        "--rebuild-report-only",
    )

    assert code == 0, output
    assert R.report_path(CBB, beside).is_file(), (
        "a record-only tree must still be able to re-render; refusing here is "
        "the permanent red the empty return exists to avoid"
    )
    assert "unchecked rather than checked and found fine" in output, (
        "the run could not check whether this replication still describes its "
        "discovery run and said nothing, so the re-render reads as a pass"
    )
    assert PB.record_path(CBB, beside).name in output, (
        "the absence is reported without naming the file that is absent, so a "
        "reader cannot tell which half of the pair went missing"
    )
    assert "no longer describes the discovery run" not in output, (
        "an absent discovery record is reported as a disagreement, which is a "
        "claim about a file nobody read"
    )


def test_a_rebuild_beside_a_discovery_record_it_cannot_read_is_refused(
    replicated, tmp_path
):
    """A discovery record that is present and unparseable is the quiet one.

    An ABSENT discovery record is loud by its absence and the caller warns. A
    DISAGREEING one is refused and names both figures. A file that is sitting
    right there and cannot be parsed -- truncated by a killed run, half
    written, or overwritten by a partial download -- looked like neither:
    `stale_discovery` returns its reason, and nothing executed that branch, so
    deleting the reason and returning `[]` left the suite green and re-rendered
    the report at exit 0 with no complaint. An unreadable check rendering as a
    pass is the exact shape this whole staleness check was written to close,
    shipped inside the check itself.

    Mutation: replace the `except (OSError, ValueError)` return in
    `stale_discovery` with `return []` -- 2 failed, 32 passed: this test on the
    exit code, and the unit test above on the reason. Nothing else moves.
    """
    beside = _a_replication_record_of_its_own(replicated, tmp_path / "unreadable")
    discovery_path = _the_discovery_run_it_was_built_against(replicated, beside)
    whole = discovery_path.read_text(encoding="utf-8")
    discovery_path.write_text(whole[: len(whole) // 2], encoding="utf-8")

    code, output = run_script(
        "--output-dir",
        str(beside),
        "--processed-dir",
        str(tmp_path / "does-not-exist"),
        "--rebuild-report-only",
    )

    assert code == 2, output
    printed = _reasons_printed(output)
    assert len(printed) == 1, printed
    assert "could not be read" in printed[0]
    assert discovery_path.name in printed[0], (
        "the refusal does not name the file it could not read, so a reader "
        "cannot tell which half of the pair is damaged"
    )
    assert "is not beside this record" not in output, (
        "an unreadable discovery record is reported as an absent one, which is "
        "a claim about a file that is sitting right there"
    )
    assert not R.report_path(CBB, beside).is_file(), (
        "the refusal still wrote the report, so an unverifiable comparison was "
        "republished anyway"
    )


def test_a_rebuild_of_a_record_that_never_stamped_its_discovery_run_is_refused(
    replicated, tmp_path
):
    """CANNOT ANSWER is reported as a failure, never as a pass.

    The other four shapes are questions about a pair of files. This one is a
    question about the record: with no `discovery` stamp there is nothing to
    compare the file against, and no later run can recover what the
    replication was built on. It used to `return []` -- the same list an
    agreeing pair returns -- and the caller's absent-file warning does not
    cover it either, because that warning is keyed on the FILE being missing
    and here the file is present. So a hand-edited or truncated record sat
    beside a discovery record from some other run and `--rebuild-report-only`
    republished the comparison at exit 0, silently.

    The sibling this check's docstring says it copies does the same thing and
    says why: `what_we_can_claim.stale_inputs` returns a reason for a record
    with no `evidence_inputs`, and
    `test_a_record_that_never_wrote_down_what_it_read_cannot_pass_the_check`
    holds it to a non-zero exit.

    Mutation: restore `return []` in the `if missing:` branch -- this test on
    the exit code, and the unit test above on the reason. Nothing else moves.
    """
    beside = _a_replication_record_of_its_own(replicated, tmp_path / "unstamped")
    _the_discovery_run_it_was_built_against(replicated, beside)
    record_target = R.record_path(CBB, beside)
    payload = json.loads(record_target.read_text(encoding="utf-8"))
    assert payload.pop("discovery"), "the fixture's record must carry the stamp"
    record_target.write_text(json.dumps(payload), encoding="utf-8")

    code, output = run_script(
        "--output-dir",
        str(beside),
        "--processed-dir",
        str(tmp_path / "does-not-exist"),
        "--rebuild-report-only",
    )

    assert code == 2, output
    printed = _reasons_printed(output)
    assert len(printed) == 1, printed
    assert "does not write down which discovery run" in printed[0]
    assert "is not beside this record" not in output, (
        "a record with no stamp is reported as a missing FILE, which is a "
        "claim about a file that is present"
    )
    assert not R.report_path(CBB, beside).is_file(), (
        "the refusal still wrote the report, so a comparison nothing could "
        "check was republished anyway"
    )


def test_a_rebuild_whose_stamp_lost_the_fields_the_check_reads_is_refused(
    replicated, tmp_path
):
    """A TRUNCATED stamp is a stamp, and it identifies no run at all.

    The refusal above covers a record whose `discovery` key is gone. This one
    covers the shape that reaches the same dead end through a stamp that is
    still there: `build_record` writes EIGHT keys and `stale_discovery` reads
    back FIVE, so a stamp cut down to `cells`, `claims` and `looks_when_scored`
    is non-empty, truthy, and answers nothing. `if not stamped:` was false for
    it, every comparison was skipped, and the empty list an AGREEING pair
    returns came back -- the same "checked and agreed" rendering the branch's
    own comment says must refuse, arriving through the branch itself.

    Driven through the script rather than by calling the function, because the
    defect is only reachable once the truncated stamp has been WRITTEN to disk
    and read back by `read_record`: an in-memory dict never proves the record
    survives the round trip, and `read_record` is the gate that would have to
    reject it if anything did.

    Mutation: `if missing:` -> `if not stamped:` in `stale_discovery` -- this
    test on the exit code and the unit test above on the reason. The other four
    script-level staleness tests stay green, because a full stamp, an absent
    file and an unreadable file are unaffected by which condition is used.
    """
    beside = _a_replication_record_of_its_own(replicated, tmp_path / "truncated")
    _the_discovery_run_it_was_built_against(replicated, beside)
    record_target = R.record_path(CBB, beside)
    payload = json.loads(record_target.read_text(encoding="utf-8"))
    kept = {
        key: value
        for key, value in payload["discovery"].items()
        if key not in R.COMPARED_DISCOVERY_FIELDS
    }
    assert kept, (
        "`build_record` no longer writes any key this check does not compare, "
        "so a truncation to the uncompared keys is an empty stamp and this "
        "test now duplicates the one above rather than testing its own shape"
    )
    payload["discovery"] = kept
    record_target.write_text(json.dumps(payload), encoding="utf-8")

    code, output = run_script(
        "--output-dir",
        str(beside),
        "--processed-dir",
        str(tmp_path / "does-not-exist"),
        "--rebuild-report-only",
    )

    assert code == 2, output
    printed = _reasons_printed(output)
    assert len(printed) == 1, printed
    assert "does not write down which discovery run" in printed[0]
    assert _fields_named_missing(printed[0]) == list(R.COMPARED_DISCOVERY_FIELDS), (
        f"the refusal does not name what the stamp lost: {printed[0]}"
    )
    assert "is not beside this record" not in output, (
        "a truncated stamp is reported as a missing FILE, which is a claim "
        "about a file that is present and was copied in by this test"
    )
    assert not R.report_path(CBB, beside).is_file(), (
        "the refusal still wrote the report, so a comparison nothing could "
        "check was republished anyway"
    )
