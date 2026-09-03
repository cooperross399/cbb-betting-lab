"""Reachability: whether a measured edge was a price anybody could have taken.

`reports/price_backtest.py` names `reachability.py` twice — once to reserve the
optional column `survived_to_next_capture` for it, once to say the backtest
*"cannot say an edge is reachable"* — and those two comments are the module's
specification. This file pins the ways that answer could be manufactured or
lost, and every test is named for the specific failure it prevents:

* an unjudgeable quote folded into the vanished bucket, which turns a fetch
  that skipped an event into a not-reachable finding;
* a quote that does not match itself across a CSV round-trip, which is the same
  finding manufactured out of a join and is silent **and directional** — it can
  only ever invent vanished prices;
* per-book survival computed by filtering the later capture, which turns a
  price a book really did pull into a coverage gap;
* a pooled Division I headline printed without its tier rows;
* a per-bet interval where a clustered one belongs, which is how the football
  lab's forward ledger came out 10.3x too narrow;
* a thin September store crashing, or printing an empty table that reads as a
  null result — which is a claim;
* a report that can only be produced by re-running the measurement.
"""

from __future__ import annotations

import json
import runpy
import sys
from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab import line_movement as LM
from cbb_betting_lab import reachability as RE
from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.conferences import Tier
from cbb_betting_lab.reports import price_backtest as PB

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run_reachability.py"


# --------------------------------------------------------------------------
# Fixtures, in the stores' own vocabularies
# --------------------------------------------------------------------------


def board(captured_at: str, quotes, *, slate_date: str = "2027-01-12") -> pd.DataFrame:
    """One capture, in `line_movement.CAPTURE_COLUMNS` exactly."""
    rows = []
    for event_id, market, selection, line, book, odds in quotes:
        rows.append(
            {
                "captured_at": captured_at,
                "slate_date": slate_date,
                "event_id": event_id,
                "commence_time": f"{slate_date}T23:00:00Z",
                "home_team": "Duke",
                "away_team": "Kansas",
                "market": market,
                "segment": "full_game",
                "player": "",
                "selection": selection,
                "line": line,
                "book": book,
                "american_odds": odds,
            }
        )
    return pd.DataFrame(rows, columns=list(LM.CAPTURE_COLUMNS))


A = ("e1", "total_points", "over", 142.5, "draftkings", -110.0)
B = ("e1", "total_points", "under", 142.5, "draftkings", -110.0)
C = ("e2", "spread", "home", -3.5, "fanduel", -110.0)


def bets_from_board(frame: pd.DataFrame, **overrides) -> pd.DataFrame:
    """A graded bet frame carrying the same quotes a capture holds."""
    out = frame.copy()
    out["tier"] = overrides.pop("tier", Tier.LOW_MAJOR.value)
    out["model_probability"] = 0.6
    out["outcome"] = "won"
    out["profit_units"] = 0.9
    for key, value in overrides.items():
        out[key] = value
    return out


def staked(
    n_events: int,
    *,
    tier: str,
    bucket: str,
    profits,
    first_day: int = 1,
    days: int = 10,
    per_event: int = 4,
    event_prefix: str = "g",
) -> pd.DataFrame:
    """`n_events` x `per_event` graded bets, already labelled by `bucket`.

    The survival column is supplied directly, which exercises the `column`
    provenance path — the strongest form of this evidence, where the quote was
    judged against the capture the price was actually taken from.
    """
    rows = []
    for index in range(n_events):
        event = f"{event_prefix}{index}"
        day = f"2027-01-{first_day + index % days:02d}"
        for slot in range(per_event):
            profit = profits[(index * per_event + slot) % len(profits)]
            rows.append(
                {
                    "event_id": event,
                    "slate_date": day,
                    "market": "spread" if slot % 2 else "total_points",
                    "segment": "full_game",
                    "selection": "home" if slot % 2 else "over",
                    "line": -3.5 if slot % 2 else 142.5,
                    "american_odds": -110.0,
                    "tier": tier,
                    "model_probability": 0.58,
                    "outcome": "won" if profit > 0 else "lost",
                    "profit_units": profit,
                    "book": "draftkings",
                    RE.SURVIVED_COLUMN: bucket,
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# The specification: the two comments that named this module
# --------------------------------------------------------------------------


def test_price_backtest_named_this_module_and_reserved_its_column():
    """The spec, pinned. `price_backtest` reserves `survived_to_next_capture`
    for this module and defers the reachability question to it by name. If
    either of those moves, this module has been orphaned and nothing else
    would notice."""
    assert RE.SURVIVED_COLUMN in PB.OPTIONAL_BET_COLUMNS
    source = Path(PB.__file__).read_text(encoding="utf-8")
    assert "reachability.py" in source
    assert "reported there as not reachable" in source


def test_the_not_reachable_phrase_is_one_phrase():
    """*"In those words"* means one spelling. Two modules with two spellings of
    the same verdict is two verdicts, and a reader greping for one finds half
    the report."""
    from cbb_betting_lab import forward_evidence

    assert RE.NOT_REACHABLE == "not reachable"
    assert RE.NOT_REACHABLE == forward_evidence.NOT_REACHABLE


def test_the_regions_are_the_providers_own_default():
    """Cooper's instruction: regions stay `us,us2`. A price at a book he cannot
    open is not reachable and manufactures untakeable edges."""
    from cbb_betting_lab.providers.odds_api import DEFAULT_REGIONS

    assert RE.REGIONS == "us,us2"
    assert RE.REGIONS == DEFAULT_REGIONS


# --------------------------------------------------------------------------
# Labelling: line_movement decides, this module only asks
# --------------------------------------------------------------------------


def test_the_labels_agree_with_line_movement_itself():
    """THE EQUIVALENCE THIS MODULE'S SPEED DEPENDS ON.

    Per-bet labelling slices the later capture to the bet's own
    `(event_id, market)` before calling `survival_between`, because coverage is
    decided at exactly that resolution and presence on an identity containing
    both fields. If that slice ever stopped being answer-preserving, this
    module would be quietly reimplementing survival — which is the one thing
    it must not do.
    """
    moved = ("e1", "total_points", "over", 143.0, "draftkings", -110.0)
    earlier = board("t1", [A, B, C])
    later = board("t2", [moved, B])  # A moved, B stayed, e2 never covered.
    store = pd.concat([earlier, later], ignore_index=True)

    labels = RE.label_survival(earlier, store)
    counts = labels.value_counts()
    truth = LM.survival_between(earlier, later)

    assert int(counts.get(LM.SURVIVED, 0)) == truth.survived == 1
    assert int(counts.get(LM.GONE, 0)) == truth.gone == 1
    assert int(counts.get(LM.UNKNOWN, 0)) == truth.unknown == 1


def test_an_event_the_next_capture_never_covered_is_unjudgeable_not_vanished():
    """THE CARDINAL ERROR. A fetch that skipped an event is not a book that
    pulled a price. Scoring it as vanished manufactures a not-reachable finding
    out of a coverage gap, and a not-reachable finding is one this lab would
    act on."""
    store = pd.concat([board("t1", [A, C]), board("t2", [A])], ignore_index=True)
    labels = RE.label_survival(board("t1", [C]), store)
    assert list(labels) == [LM.UNKNOWN]


def test_a_quote_the_store_never_held_is_unjudgeable_never_vanished():
    """This instrument has nothing to say about a price it never observed."""
    store = pd.concat([board("t1", [A]), board("t2", [A])], ignore_index=True)
    labels = RE.label_survival(board("t1", [C]), store)
    assert list(labels) == [LM.UNKNOWN]


def test_a_bet_at_the_last_capture_is_unjudgeable_because_there_is_no_next_one():
    """Survival is a statement about a quote at the NEXT capture. The cron not
    having caught up with a bet is not the book pulling the number."""
    store = pd.concat([board("t1", [A]), board("t2", [A])], ignore_index=True)
    late = board("t2", [A])
    assert list(RE.label_survival(late, store)) == [LM.UNKNOWN]


def test_a_moved_price_is_vanished_because_the_price_is_in_the_identity():
    """A book that moved a total from 142.5 to 143 has not kept the 142.5. The
    old number is what a backtest would have staked and it is exactly what is
    no longer available."""
    moved = ("e1", "total_points", "over", 143.0, "draftkings", -110.0)
    store = pd.concat([board("t1", [A]), board("t2", [moved])], ignore_index=True)
    assert list(RE.label_survival(board("t1", [A]), store)) == [LM.GONE]


def test_a_blank_player_and_a_missing_player_are_the_same_quote(tmp_path):
    """THE JOIN DEFECT THAT COULD ONLY EVER INVENT VANISHED PRICES.

    A bets frame and a capture store meet across a CSV round-trip, and that
    round-trip does not preserve spellings: an absent `player` is `""` in
    memory and `NaN` off disk, and a line is `142.5` one side and `"142.5"` the
    other. Compared raw, the identical quote does not match itself — and the
    failure is **directional**. An unmatched quote looks like a price the book
    pulled, so the defect can only ever manufacture a not-reachable finding,
    never suppress one.

    This test round-trips the store through CSV exactly as the cron does, and
    hands `label_survival` an in-memory bet frame. Without the normalisation in
    `_normalise_identity` the surviving quote below comes back GONE.
    """
    path = tmp_path / "lm.csv"
    LM.append_capture(board("t1", [A]), path)
    LM.append_capture(board("t2", [A]), path)
    store = pd.read_csv(path)
    assert store["player"].isna().all(), "the round-trip must really lose the ''"

    in_memory = board("t1", [A])  # player is "", line is a float
    assert list(RE.label_survival(in_memory, store)) == [LM.SURVIVED]


def test_a_missing_survival_value_is_unjudgeable_and_never_vanished():
    """Nothing recorded is not a price that was pulled. Reading a null as
    'vanished' is this module's cardinal error arriving through a column
    instead of through a join."""
    frame = staked(2, tier=Tier.LOW_MAJOR.value, bucket=LM.SURVIVED, profits=[0.5])
    frame.loc[frame.index[:4], RE.SURVIVED_COLUMN] = None
    labelled, provenance = RE.attach_survival(frame, pd.DataFrame())
    assert provenance["source"] == "column"
    assert provenance["unknown"] == 4
    assert provenance["gone"] == 0


# --------------------------------------------------------------------------
# Board survival: per book, per tier
# --------------------------------------------------------------------------


def test_per_book_survival_does_not_hide_the_later_board_from_line_movement():
    """FILTERING THE LATER CAPTURE BY BOOK WOULD RUN THE CARDINAL ERROR BACKWARDS.

    A quote whose `(event, market)` the next capture covered **through a
    different book** is GONE: the price really was pulled. Slicing the later
    frame to the same book would leave that pair uncovered and relabel it
    UNKNOWN, converting a vanished price into a coverage gap and flattering
    every book's survival rate. Only the earlier side is ever sliced.
    """
    other_book = ("e1", "total_points", "over", 142.5, "fanduel", -110.0)
    store = pd.concat(
        [board("t1", [A]), board("t2", [other_book])], ignore_index=True
    )
    rows = {row["book"]: row for row in RE.survival_by_book(store)}
    assert rows["draftkings"]["gone"] == 1
    assert rows["draftkings"]["unknown"] == 0
    assert rows["draftkings"]["survival_rate"] == 0.0


def test_survival_is_reported_per_tier_because_the_two_facts_point_apart():
    """The low-major end is the looser end AND the faster one. A report that
    prints only one of those is half an argument."""
    store = pd.concat(
        [board("t1", [A, C]), board("t2", [A])], ignore_index=True
    )
    rows = {
        row["tier"]: row
        for row in RE.survival_by_tier(
            store, {"e1": Tier.HIGH_MAJOR.value, "e2": Tier.LOW_MAJOR.value}
        )
    }
    assert rows[Tier.HIGH_MAJOR.value]["survived"] == 1
    # e2 was never covered by the later capture: unjudgeable, not vanished.
    assert rows[Tier.LOW_MAJOR.value]["gone"] == 0
    assert rows[Tier.LOW_MAJOR.value]["unknown"] == 1


def test_a_quote_whose_tier_nobody_supplied_is_not_a_low_major_quote():
    """It is reported under `untiered` rather than dropped or guessed. Dropping
    it would let the pooled census hold quotes no tier row holds."""
    store = pd.concat([board("t1", [A, C]), board("t2", [A, C])], ignore_index=True)
    rows = {row["tier"]: row for row in RE.survival_by_tier(store, {"e1": Tier.HIGH_MAJOR.value})}
    assert RE.UNTIERED in rows
    assert rows[RE.UNTIERED]["quotes"] == 2


def test_the_tier_map_is_taken_from_the_bets_and_never_refitted():
    """A tier is a walk-forward measurement made in `conferences.py` from
    seasons strictly before the one being priced. A second derivation here
    would be a second answer."""
    bets = staked(2, tier=Tier.MID_MAJOR.value, bucket=LM.SURVIVED, profits=[0.5])
    assert set(RE.tier_map_from_bets(bets).values()) == {Tier.MID_MAJOR.value}
    assert RE.tier_map_from_bets(pd.DataFrame()) == {}


# --------------------------------------------------------------------------
# The verdict
# --------------------------------------------------------------------------


def _record_for(survived: pd.DataFrame, vanished: pd.DataFrame, **kwargs) -> dict:
    bets = pd.concat([survived, vanished], ignore_index=True)
    return RE.build_record(bets, None, generated_at="2026-09-03T00:00:00+00:00", **kwargs)


def test_an_edge_that_lives_only_in_vanished_prices_is_not_reachable():
    """COOPER'S RULE, VERBATIM IN SPIRIT.

    *"Any measured edge that lives entirely in prices that vanish before a
    human could act is reported as NOT REACHABLE, in those words."* The
    vanished set here returns +50% over 240 bets across 60 games; the surviving
    set returns nothing. The size and the significance of the vanished number
    are irrelevant, and the report says so.
    """
    vanished = staked(60, tier=Tier.LOW_MAJOR.value, bucket=LM.GONE, profits=[0.4, 0.6])
    survived = staked(
        60,
        tier=Tier.LOW_MAJOR.value,
        bucket=LM.SURVIVED,
        profits=[1.0, -1.0],
        event_prefix="s",
    )
    record = _record_for(survived, vanished)

    verdicts = {v["tier"]: v for v in record["verdicts"]}
    assert verdicts[Tier.LOW_MAJOR.value]["verdict"] == RE.NOT_REACHABLE
    assert verdicts[RE.POOLED]["verdict"] == RE.NOT_REACHABLE

    text = RE.render(record)
    assert "not reachable" in text
    assert "regardless of its size or its significance" in text
    # And the surviving side is reported in the only permitted words.
    assert S.NO_DEMONSTRATED_EDGE in text


def test_an_edge_present_in_surviving_prices_is_not_called_not_reachable():
    """The opposite case must not read the same. A verdict that says 'not
    reachable' whatever the survived set did would be a constant, not a
    measurement."""
    survived = staked(60, tier=Tier.LOW_MAJOR.value, bucket=LM.SURVIVED, profits=[0.4, 0.6])
    vanished = staked(
        60,
        tier=Tier.LOW_MAJOR.value,
        bucket=LM.GONE,
        profits=[1.0, -1.0],
        event_prefix="v",
    )
    record = _record_for(survived, vanished)
    verdicts = {v["tier"]: v for v in record["verdicts"]}
    assert verdicts[Tier.LOW_MAJOR.value]["verdict"] == RE.REACHABLE_IN_SURVIVING_PRICES
    assert verdicts[Tier.LOW_MAJOR.value]["verdict"] != RE.NOT_REACHABLE


def test_the_sign_is_read_by_stats_and_by_nothing_here():
    """`stats.RoiInterval.verdict` is the ONLY place a sign becomes a verdict
    string. The NHL lab's claims document announced a replicated **loss** as
    good news because a headline predicate tested everything except which side
    of zero the number sat on. A demonstrated deficit in the vanished set is
    not an edge and is not 'not reachable' either — there is nothing to reach.
    """
    vanished = staked(60, tier=Tier.LOW_MAJOR.value, bucket=LM.GONE, profits=[-0.4, -0.6])
    survived = staked(
        60,
        tier=Tier.LOW_MAJOR.value,
        bucket=LM.SURVIVED,
        profits=[1.0, -1.0],
        event_prefix="s",
    )
    record = _record_for(survived, vanished)
    verdicts = {v["tier"]: v for v in record["verdicts"]}
    assert verdicts[Tier.LOW_MAJOR.value]["vanished_verdict"] == S.DEMONSTRATED_DEFICIT
    assert verdicts[Tier.LOW_MAJOR.value]["verdict"] == S.NO_DEMONSTRATED_EDGE


def test_below_the_declared_floor_there_is_no_number_only_not_enough_evidence():
    """A +12% return over 40 bets and a coin flip are the same claim at that
    sample size, and printing the +12% invites somebody to quote it out of the
    row that qualifies it."""
    survived = staked(5, tier=Tier.LOW_MAJOR.value, bucket=LM.SURVIVED, profits=[0.9])
    vanished = staked(
        5, tier=Tier.LOW_MAJOR.value, bucket=LM.GONE, profits=[0.9], event_prefix="v"
    )
    record = _record_for(survived, vanished)
    assert all(
        row["bets"] < S.MINIMUM_BETS for row in record["by_tier_and_reachability"]
    )
    verdicts = {v["tier"]: v for v in record["verdicts"]}
    assert verdicts[Tier.LOW_MAJOR.value]["verdict"] == RE.NOT_ENOUGH_EVIDENCE
    text = RE.render(record)
    assert "not enough evidence" in text
    assert "+90.0%" not in text, "no number below the floor"


# --------------------------------------------------------------------------
# The three buckets, and the arithmetic
# --------------------------------------------------------------------------


def test_the_unjudgeable_bucket_is_never_folded_into_either_answer():
    """Folding unjudgeable into vanished manufactures a not-reachable finding
    out of a fetch that skipped an event; folding it into survived manufactures
    reachability out of the same gap. Both are worse than an honest empty
    cell, so all three buckets are printed for every tier."""
    survived = staked(3, tier=Tier.LOW_MAJOR.value, bucket=LM.SURVIVED, profits=[0.9])
    vanished = staked(
        3, tier=Tier.LOW_MAJOR.value, bucket=LM.GONE, profits=[-1.0], event_prefix="v"
    )
    unjudged = staked(
        3, tier=Tier.LOW_MAJOR.value, bucket="", profits=[0.9], event_prefix="u"
    )
    bets = pd.concat([survived, vanished, unjudged], ignore_index=True)
    record = RE.build_record(bets, None)

    provenance = record["survival_provenance"]
    assert provenance["survived"] + provenance["gone"] + provenance["unknown"] == len(bets)
    assert provenance["unknown"] == 12

    buckets = {
        (row["tier"], row["reachability"]): row
        for row in record["by_tier_and_reachability"]
    }
    for bucket in RE.BUCKETS:
        assert (Tier.LOW_MAJOR.value, bucket) in buckets
        assert (RE.POOLED, bucket) in buckets
    assert buckets[(RE.POOLED, LM.UNKNOWN)]["bets"] == 12
    assert RE.BUCKET_TITLES[LM.UNKNOWN] in RE.render(record)


def test_the_interval_is_the_clustered_one_and_not_a_second_copy():
    """`stats.interval_two_way` and nothing else. Two copies of a formula
    drift, and the direction they drift in is never the conservative one — the
    football lab's forward ledger landed at `s/G` where a cluster standard
    error is `s/sqrt(G)`, which is 10.3x too narrow on the one report that
    grows all season."""
    vanished = staked(60, tier=Tier.LOW_MAJOR.value, bucket=LM.GONE, profits=[1.0, -0.9])
    record = RE.build_record(vanished, None)
    row = next(
        r
        for r in record["by_tier_and_reachability"]
        if r["tier"] == Tier.LOW_MAJOR.value and r["reachability"] == LM.GONE
    )
    expected = S.interval_two_way(vanished.assign(profit_units=vanished["profit_units"]))
    assert row["roi"] == pytest.approx(expected.roi)
    assert row["low"] == pytest.approx(expected.low)
    assert row["high"] == pytest.approx(expected.high)
    assert row["cluster_unit"] in {"game", "day"}
    assert row["clusters"] == expected.clusters


def test_an_unclustered_interval_would_be_narrower_and_is_not_what_is_reported():
    """The defect reproduced rather than asserted away.

    One game supplies many correlated bets. Here every bet on a game wins or
    loses together — a spread, a total, two team totals and a handful of props
    settled by the same possessions — so 480 bets are 60 observations. A
    per-bet interval over them is narrower than the truth by roughly the square
    root of the cluster size, which is the shape of the football lab's
    10.3x error on the one report that grows all season.
    """
    vanished = staked(
        60, tier=Tier.LOW_MAJOR.value, bucket=LM.GONE, profits=[1.0], per_event=8
    )
    # Every bet on a game shares that game's result. That is the correlation
    # the clustering exists for, and it is exactly what a per-bet interval
    # cannot see.
    together = vanished["event_id"].map(lambda e: 1.0 if int(e[1:]) % 2 else -0.9)
    vanished = vanished.assign(profit_units=together)
    record = RE.build_record(vanished, None)
    row = next(
        r for r in record["by_tier_and_reachability"] if r["reachability"] == LM.GONE
    )
    per_bet = S.interval_by_cluster(
        vanished.assign(bets=1).rename(columns={"profit_units": "profit"})[
            ["profit", "bets"]
        ]
    )
    assert row["standard_error"] > per_bet.standard_error


# --------------------------------------------------------------------------
# House rules: never a pooled headline, always a sample size
# --------------------------------------------------------------------------


def test_the_pooled_row_is_never_printed_without_its_tier_rows():
    """A pooled figure exists because `docs/when_this_ends.md` applies its
    stopping rule to it. It is never the headline, and it is never alone."""
    bets = pd.concat(
        [
            staked(3, tier=Tier.HIGH_MAJOR.value, bucket=LM.SURVIVED, profits=[0.9]),
            staked(
                3,
                tier=Tier.LOW_MAJOR.value,
                bucket=LM.GONE,
                profits=[-1.0],
                event_prefix="l",
            ),
        ],
        ignore_index=True,
    )
    record = RE.build_record(bets, None)
    tiers = [row["tier"] for row in record["by_tier_and_reachability"]]
    assert tiers.count(RE.POOLED) == len(RE.BUCKETS)
    assert Tier.HIGH_MAJOR.value in tiers and Tier.LOW_MAJOR.value in tiers
    # The pooled rows come last, after every tier they pool.
    assert tiers.index(RE.POOLED) > tiers.index(Tier.LOW_MAJOR.value)

    text = RE.render(record)
    assert PB.POOLED_CAVEAT in text
    assert text.index(Tier.HIGH_MAJOR.value) < text.index("| pooled |")


def test_a_bet_with_no_tier_is_named_rather_than_dropped():
    """Dropping it would let the pooled row hold bets that no tier row holds,
    and the two would silently disagree."""
    bets = staked(3, tier=Tier.LOW_MAJOR.value, bucket=LM.SURVIVED, profits=[0.9])
    bets.loc[bets.index[:4], "tier"] = None
    record = RE.build_record(bets, None)
    tiers = {row["tier"] for row in record["by_tier_and_reachability"]}
    assert RE.UNTIERED in tiers
    pooled = next(
        r
        for r in record["by_tier_and_reachability"]
        if r["tier"] == RE.POOLED and r["reachability"] == LM.SURVIVED
    )
    assert pooled["bets"] == len(bets)


def test_book_and_timestamp_are_recorded():
    """*"Record book and timestamp. A price at a book Cooper cannot open is not
    reachable; regions stay us,us2."*"""
    store = pd.concat(
        [
            board("2027-01-12T19:04:00Z", [A, C]),
            board("2027-01-12T19:19:00Z", [A, C]),
        ],
        ignore_index=True,
    )
    record = RE.build_record(pd.DataFrame(), store)
    assert record["regions"] == "us,us2"
    assert record["store"]["first_capture"] == "2027-01-12T19:04:00Z"
    assert record["store"]["last_capture"] == "2027-01-12T19:19:00Z"
    assert {row["book"] for row in record["by_book"]} == {"draftkings", "fanduel"}
    assert [row["earlier"] for row in record["capture_pairs"]] == [
        "2027-01-12T19:04:00Z"
    ]


def test_beating_an_opening_number_is_not_a_bet_wherever_the_figure_appears():
    """`docs/what_we_can_and_cannot_claim.md`: *"A backtest that beats the
    opening number is not a bet, and that sentence appears wherever such a
    figure appears."*"""
    store = pd.concat([board("t1", [A]), board("t2", [A])], ignore_index=True)
    bets = bets_from_board(board("t1", [A]))
    record = RE.build_record(bets, store)
    assert record["opening_number"]["measured"] is True
    assert record["opening_number"]["at_first_capture"]["bets"] == 1
    text = RE.render(record)
    assert text.count("Beating an opening number is not a bet") >= 2


def test_the_opening_split_is_refused_rather_than_guessed_without_a_stamp():
    """Guessing which bets were early would put the caveat on the wrong rows,
    which is worse than not splitting at all."""
    bets = staked(3, tier=Tier.LOW_MAJOR.value, bucket=LM.SURVIVED, profits=[0.9])
    record = RE.build_record(bets, None)
    assert record["opening_number"]["measured"] is False
    assert "refused rather than approximated" in record["opening_number"]["note"]
    assert "Beating an opening number is not a bet" in RE.render(record)


def test_limits_are_named_as_unobservable_rather_than_assumed_fine():
    """The brief names trivial limits and vanishing prices together. This
    instrument measures only the second, and a surviving price at a trivial
    limit is still not a bet."""
    text = RE.render(RE.build_record())
    assert "Limits are not observable from this instrument" in text
    assert "surviving price at a trivial limit is still not a bet" in text


# --------------------------------------------------------------------------
# A thin September store
# --------------------------------------------------------------------------


def test_an_absent_store_reports_not_enough_evidence_and_does_not_crash():
    """It is September. The season opens on 2026-11-01, the capture script
    writes nothing when the board is empty, and the ordinary state of the store
    is absent. A crash would look like a broken pipeline when the truth is a
    calendar."""
    record = RE.build_record(pd.DataFrame(), pd.DataFrame(columns=list(LM.CAPTURE_COLUMNS)))
    assert record["store"]["enough_evidence"] is False
    text = RE.render(record)
    assert "not enough evidence" in text.lower()
    assert "there is no college basketball between April and November" in text
    assert "| From | To |" not in text, "no empty table"


def test_one_capture_is_no_evidence_rather_than_thin_evidence():
    """Survival is a statement about a quote at the NEXT capture, and there has
    not been one."""
    record = RE.build_record(pd.DataFrame(), board("t1", [A, B, C]))
    assert record["store"]["captures"] == 1
    assert record["store"]["enough_evidence"] is False
    assert "That is not thin evidence, it is no evidence" in record["store"]["reason"]
    assert record["capture_pairs"] == []


def test_a_store_below_the_declared_quote_floor_says_so_with_its_census():
    """Below `MINIMUM_JUDGED_QUOTES` the board rate is not a number. An
    off-season pair of captures is a store captured out of season, not an
    instrument with something to say."""
    store = pd.concat([board("t1", [A, B]), board("t2", [A, B])], ignore_index=True)
    summary = RE.store_summary(store)
    assert summary["captures"] == 2
    assert summary["judged_quotes"] == 2
    assert summary["enough_evidence"] is False
    assert f"{RE.MINIMUM_JUDGED_QUOTES:,} declared in advance" in summary["reason"]


def thick_store(*, gone_in_low_major: int = 0) -> tuple[pd.DataFrame, dict]:
    """Two captures over `MINIMUM_JUDGED_QUOTES` worth of board, plus tiers.

    Sized to clear the declared floor, because every other store test in this
    file is about a store that does not. `gone_in_low_major` pulls that many
    low-major quotes out of the later capture, which is how the board table
    shows a tier whose prices move faster than another's.
    """
    quotes, tiers = [], {}
    for event_index in range(40):
        event = f"e{event_index}"
        tiers[event] = (
            Tier.LOW_MAJOR.value if event_index % 2 else Tier.HIGH_MAJOR.value
        )
        for selection in ("over", "under"):
            for step in range(5):
                for book in ("draftkings", "fanduel", "betmgm"):
                    quotes.append(
                        (
                            event,
                            "total_points",
                            selection,
                            142.5 + step * 0.5,
                            book,
                            -110.0,
                        )
                    )
    low = [q for q in quotes if tiers[q[0]] == Tier.LOW_MAJOR.value]
    # Taken with a stride so the dropped quotes are spread across every
    # low-major event. Dropping an event's whole board would make it
    # UNJUDGEABLE rather than GONE — the later capture would not have covered
    # that (event, market) at all — and this fixture is about prices a book
    # pulled while still quoting the game.
    dropped = set(low[::5][:gone_in_low_major])
    later = [q for q in quotes if q not in dropped]
    store = pd.concat(
        [board("2027-01-12T19:04:00Z", quotes), board("2027-01-12T19:19:00Z", later)],
        ignore_index=True,
    )
    return store, tiers


def test_a_store_over_the_floor_prints_the_board_tables_it_earned():
    """The other half of the thin-store rule. A store that clears the declared
    floor gets its survival rate, per capture pair, per tier and per book —
    each with the sample size that entitles it to one."""
    store, tiers = thick_store(gone_in_low_major=120)
    # The tier map comes from the bets and is never refitted here, so the bet
    # frame is what tells the board table which events are low-major.
    record = RE.build_record(
        pd.DataFrame(
            [
                {
                    "event_id": event,
                    "slate_date": "2027-01-12",
                    "market": "total_points",
                    "segment": "full_game",
                    "selection": "over",
                    "line": 142.5,
                    "american_odds": -110.0,
                    "tier": tier,
                    "model_probability": 0.6,
                    "outcome": "won",
                    "profit_units": 0.9,
                }
                for event, tier in tiers.items()
            ]
        ),
        store,
    )
    assert record["store"]["enough_evidence"] is True
    text = RE.render(record)
    assert "### Survival between consecutive captures" in text
    assert "### Survival per conference tier" in text
    assert "### Survival per book" in text

    by_tier = {row["tier"]: row for row in record["board_by_tier"]}
    assert by_tier[Tier.LOW_MAJOR.value]["gone"] == 120
    assert by_tier[Tier.HIGH_MAJOR.value]["gone"] == 0
    # The looser end being the faster end is the whole point of this table.
    assert (
        by_tier[Tier.LOW_MAJOR.value]["survival_rate"]
        < by_tier[Tier.HIGH_MAJOR.value]["survival_rate"]
    )


def test_an_empty_table_is_never_printed_in_place_of_words():
    """An empty table reads as a null result and a null result is a claim."""
    text = RE.render(RE.build_record())
    assert PB.NOTHING_TO_MEASURE.capitalize() in text
    assert "|:---|" not in text


# --------------------------------------------------------------------------
# Re-rendering
# --------------------------------------------------------------------------


def test_the_report_re_renders_byte_identically_from_the_run_record(tmp_path):
    """Improving a sentence must never cost a re-run. A report that can only be
    produced by re-running the measurement is a report nobody improves, and a
    hand-edited generated file survives exactly one re-run."""
    survived = staked(60, tier=Tier.LOW_MAJOR.value, bucket=LM.SURVIVED, profits=[0.4, 0.6])
    vanished = staked(
        60, tier=Tier.LOW_MAJOR.value, bucket=LM.GONE, profits=[1.0, -1.0], event_prefix="v"
    )
    record = _record_for(survived, vanished)
    first = RE.render(record)

    path = RE.write_record(record, tmp_path / "record.json")
    reloaded = RE.read_record(path)
    assert RE.render(reloaded) == first


def test_a_stale_record_version_is_refused_rather_than_rendered_with_holes(tmp_path):
    path = tmp_path / "record.json"
    path.write_text(json.dumps({"record_version": RE.RECORD_VERSION + 1}), encoding="utf-8")
    with pytest.raises(RE.ReachabilityError) as caught:
        RE.read_record(path)
    assert "renders a report with holes in it" in str(caught.value)


def test_the_record_rows_read_back_through_the_backtests_own_reader():
    """One record vocabulary across both reports. Two serialisations of a
    `RoiInterval` drift, and `interval_from_row` is what re-renders them."""
    bets = staked(60, tier=Tier.LOW_MAJOR.value, bucket=LM.GONE, profits=[0.4, 0.6])
    record = RE.build_record(bets, None)
    row = record["by_tier_and_reachability"][0]
    interval = PB.interval_from_row(row)
    assert interval.bets == row["bets"]
    assert interval.verdict() == row["verdict"]


# --------------------------------------------------------------------------
# The script
# --------------------------------------------------------------------------


def run_script(argv, monkeypatch) -> int:
    monkeypatch.setattr(sys, "argv", ["run_reachability.py", *argv])
    try:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    except SystemExit as exit_code:
        return int(exit_code.code or 0)
    return 0


def test_the_script_runs_with_nothing_on_disk_and_spends_nothing(tmp_path, capsys, monkeypatch):
    """The state of this repository today: no capture store, no settled
    forward opinion. It must write an honest record, not fail."""
    code = run_script(
        [
            "--processed-dir",
            str(tmp_path / "processed"),
            "--output-dir",
            str(tmp_path / "outputs"),
        ],
        monkeypatch,
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "no credit was spent" in out
    assert "not enough evidence" in out.lower()
    record = RE.read_record(RE.record_path(CBB, tmp_path / "outputs"))
    assert record["store"]["enough_evidence"] is False
    assert RE.report_path(CBB, tmp_path / "outputs").is_file()


def test_the_script_reads_the_forward_ledgers_own_column_names(tmp_path, capsys, monkeypatch):
    """The forward ledger spells the slate day `snapshot_date` and survival
    `price_survived`. Two spellings of one field is how a join quietly matches
    nothing, so both are renamed on the way in and the rename is printed."""
    processed = tmp_path / "processed"
    processed.mkdir(parents=True)
    bets = staked(60, tier=Tier.LOW_MAJOR.value, bucket=LM.GONE, profits=[0.4, 0.6])
    bets = bets.rename(
        columns={"slate_date": "snapshot_date", RE.SURVIVED_COLUMN: "price_survived"}
    )
    bets.to_csv(processed / CBB.output_name("forward_evidence", ".csv"), index=False)

    code = run_script(
        ["--processed-dir", str(processed), "--output-dir", str(tmp_path / "outputs")],
        monkeypatch,
    )
    out = capsys.readouterr().out
    assert code == 0
    assert "Read `snapshot_date` as `slate_date`" in out
    assert "Read `price_survived` as `survived_to_next_capture`" in out
    record = RE.read_record(RE.record_path(CBB, tmp_path / "outputs"))
    assert record["survival_provenance"]["source"] == "column"
    assert record["survival_provenance"]["gone"] == len(bets)


def test_the_script_refuses_a_bet_frame_missing_a_column(tmp_path, capsys, monkeypatch):
    """A missing column read as a zero is how the football lab's backtest
    reported zero bets and had that read as 'the model never disagrees enough'.
    Nothing is defaulted."""
    processed = tmp_path / "processed"
    processed.mkdir(parents=True)
    bets = staked(3, tier=Tier.LOW_MAJOR.value, bucket=LM.GONE, profits=[0.4]).drop(
        columns=["profit_units"]
    )
    path = processed / "bets.csv"
    bets.to_csv(path, index=False)
    code = run_script(
        [
            "--bets",
            str(path),
            "--processed-dir",
            str(processed),
            "--output-dir",
            str(tmp_path / "outputs"),
        ],
        monkeypatch,
    )
    assert code == 2
    assert "profit_units" in capsys.readouterr().err


def test_the_script_re_renders_and_checks_without_touching_the_store(tmp_path, capsys, monkeypatch):
    """`--check` is what fails the build when somebody hand-edits a generated
    report, and it must not need the store to do it."""
    outputs = tmp_path / "outputs"
    processed = tmp_path / "processed"
    run_script(["--processed-dir", str(processed), "--output-dir", str(outputs)], monkeypatch)
    capsys.readouterr()

    assert run_script(["--output-dir", str(outputs), "--check"], monkeypatch) == 0
    assert "matches its run record" in capsys.readouterr().out

    report = RE.report_path(CBB, outputs)
    report.write_text(report.read_text(encoding="utf-8") + "\nedited by hand\n", encoding="utf-8")
    assert run_script(["--output-dir", str(outputs), "--check"], monkeypatch) == 1
    assert "does not match" in capsys.readouterr().err

    assert run_script(["--output-dir", str(outputs), "--rerender"], monkeypatch) == 0
    assert "edited by hand" not in report.read_text(encoding="utf-8")


def test_the_recorded_store_path_is_relative_to_the_repository(tmp_path):
    """The record is a committed artifact. An absolute path in it churns the
    diff on every machine that runs the script, which makes a real change to
    the census harder to see rather than easier."""
    module = runpy.run_path(str(SCRIPT))
    inside = REPO / "data" / "processed" / "cbb_line_movement.csv"
    assert module["record_path_hint"](inside) == "data/processed/cbb_line_movement.csv"
    outside = tmp_path / "elsewhere.csv"
    assert module["record_path_hint"](outside) == str(outside)


def test_the_script_warns_when_a_tier_measured_an_unreachable_edge(tmp_path, capsys, monkeypatch):
    """A not-reachable finding is one this lab would act on, so it reaches
    stdout rather than only the markdown."""
    processed = tmp_path / "processed"
    processed.mkdir(parents=True)
    bets = pd.concat(
        [
            staked(60, tier=Tier.LOW_MAJOR.value, bucket=LM.GONE, profits=[0.4, 0.6]),
            staked(
                60,
                tier=Tier.LOW_MAJOR.value,
                bucket=LM.SURVIVED,
                profits=[1.0, -1.0],
                event_prefix="s",
            ),
        ],
        ignore_index=True,
    )
    bets.to_csv(processed / CBB.output_name("forward_evidence", ".csv"), index=False)
    code = run_script(
        ["--processed-dir", str(processed), "--output-dir", str(tmp_path / "outputs")],
        monkeypatch,
    )
    out = capsys.readouterr().out
    assert code == 0
    assert RE.NOT_REACHABLE in out
    assert "::warning::" in out
