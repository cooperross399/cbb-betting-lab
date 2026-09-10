"""Design section 10's scoring, and every way it could flatter the model.

`reports/prop_grading.py` is the first thing in this repository that turns a
player prop into a number. Everything the lab has learned about how a
measurement goes wrong applies to it at once, so this file is organised by the
way it would be wrong rather than by function:

1. **The gate.** Nothing is scored until both receipts have been filed IN THIS
   PROCESS, and a market refused by name is filtered after the gate and never
   given a verdict.
2. **The de-vig.** Two methods over one pairing pass, joined on the book;
   a rung with no complement gets no fair price and is counted; the vigged
   comparison is never a headline.
3. **The headline.** The least favourable comparison wins, a demonstrated edge
   needs every comparison to show one, and the two reserved phrases are used in
   exactly the reserved way.
4. **The floors.** Below 200 wagers or 30 clusters there is a phrase and no
   number — and a re-render cannot turn the phrase back into a verdict.
5. **The clustering.** Three arms, the widest wins, and the athlete arm really
   can be the widest. Rows are quotes and floors are bets.
6. **Coverage.** Rungs are counted along the ladder and not in points, and the
   far ladder is unbenchmarked whatever its interval says.
7. **No pooling.** There is no all-of-Division-I row anywhere, in the record or
   in the report.
8. **The restatement.** It may widen and only widen, it moves no measurement,
   and it re-derives every derived word.
9. **The control.** It is the role prior at the projected-minutes bucket with
   the credibility weight at zero, and a control that cannot price a subject
   excludes the row rather than borrowing the model's own number.
10. **The wiring.** The run files its dispositions through the one function
    that decides, settles through the shipped backtest's own code, and assigns
    no bucket of its own.

Every test that takes a census receipt drops it again afterwards: the receipt is
process-global, and one leaking out of this file would make the gate look shut
in a file that never ran it.
"""

from __future__ import annotations

import ast
import dataclasses
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from conftest import reconcile_a_fixture_census  # noqa: E402

from cbb_betting_lab import stats as S  # noqa: E402
from cbb_betting_lab.competitions import CBB  # noqa: E402
from cbb_betting_lab.models import player_census as PC  # noqa: E402
from cbb_betting_lab.models import player_rates as PR  # noqa: E402
from cbb_betting_lab.reports import prop_grading as G  # noqa: E402

SCRIPT_PATH = REPO / "scripts" / "run_prop_grading.py"


@pytest.fixture(autouse=True)
def _no_receipt_leaves_this_file():
    PC.forget_reconciliations()
    yield
    PC.forget_reconciliations()


@pytest.fixture()
def receipt(tmp_path):
    """Both halves of the gate, over a two-quote fixture store."""
    return reconcile_a_fixture_census(tmp_path)


# --------------------------------------------------------------------------
# A population small enough to check by hand
# --------------------------------------------------------------------------


def pair(
    *,
    event="E1",
    day="2024-01-02",
    market="player_points",
    player="Al Jones",
    line=10.5,
    book="draftkings",
    tier="high_major",
    over_odds=-110,
    under_odds=-110,
    over_won=True,
    model_over=0.5,
    control_over=0.5,
    model_push=0.0,
    control_push=0.0,
):
    """Both sides of one wager at one book. The store counts them as two.

    The two sides settle oppositely by construction, which is what a real
    two-sided pair does and is the reason the calibration tables this module
    prints are symmetric about 50%.
    """
    common = dict(
        event_id=event,
        slate_date=day,
        market=market,
        segment="game",
        player=player,
        line=line,
        book=book,
        tier=tier,
    )
    return [
        dict(
            common,
            selection="over",
            american_odds=over_odds,
            outcome="won" if over_won else "lost",
            model_probability=model_over,
            model_push_mass=model_push,
            control_probability=control_over,
            control_push_mass=control_push,
        ),
        dict(
            common,
            selection="under",
            american_odds=under_odds,
            outcome="lost" if over_won else "won",
            model_probability=1.0 - model_over - model_push,
            model_push_mass=model_push,
            control_probability=1.0 - control_over - control_push,
            control_push_mass=control_push,
        ),
    ]


def a_population(
    *,
    pairs=150,
    tier="high_major",
    model_over=0.60,
    control_over=0.50,
    over_won=None,
    market=None,
    games=40,
    athletes=40,
    days=20,
) -> pd.DataFrame:
    """`pairs` two-sided wagers spread over games, days, athletes and markets.

    **A pair is two wagers**, because the store's own census counts an over and
    an under separately, so a call for 100 pairs produces 200 wagers and 200
    rows at one book.

    The outcome alternates unless `over_won` is given, so a caller that wants a
    model with real skill sets it and one that wants noise leaves it alone.
    """
    markets = (market,) if market else G.PRICED_MARKETS
    # Every (event, market, athlete) combination, in a fixed order, so a wager
    # key can never collide with another: two pairs sharing a key are one
    # four-row group the de-vig refuses as `not_two_sided`, and a fixture that
    # did that would silently score nothing while looking like a population.
    combinations = [
        (event, name, athlete)
        for event in range(games)
        for name in markets
        for athlete in range(athletes)
    ]
    rows: list[dict] = []
    for index in range(pairs):
        event, name, athlete = combinations[index % len(combinations)]
        rows += pair(
            # The tier is part of the EVENT and not of the wager key -- a game
            # is high-major or mid-major, a wager is not -- so two tiers built
            # over the same event ids would be one set of wagers quoted twice
            # and the de-vig would refuse every one of them as `not_two_sided`.
            # Measured: three tiers concatenated over shared event ids scored
            # exactly zero rows while every count above still looked right.
            event=f"{tier}-E{event}",
            day=f"2024-01-{(index % days) + 1:02d}",
            market=name,
            player=f"Player {athlete}",
            # The line advances only once every combination has been used, so
            # the ladders here are as short as the shape allows. A fixture that
            # accidentally built thirteen-rung ladders would push half its own
            # rows past the benchmarked cut and test the far-ladder path while
            # claiming to test the near one. That happened on the first draft.
            line=10.5 + (index // len(combinations)),
            tier=tier,
            over_won=(index % 2 == 0) if over_won is None else over_won,
            model_over=model_over,
            control_over=control_over,
        )
    return pd.DataFrame(rows)


def inputs_for(frame: pd.DataFrame, **overrides) -> G.PropGradingInputs:
    return G.PropGradingInputs(graded=frame, **overrides)


# --------------------------------------------------------------------------
# 1. The gate
# --------------------------------------------------------------------------


def test_nothing_is_scored_until_both_receipts_have_been_filed(tmp_path):
    """The census alone is not enough, and neither is nothing.

    Mutation: delete the `guard_graded_frame` line from `build_record` — RED.
    """
    frame = a_population(pairs=4)
    assert PC.reconciled() == ()
    with pytest.raises(PC.WagerCountMismatch, match="no wager census has reconciled"):
        G.build_record(inputs_for(frame))

    from conftest import census_expected_record

    store = tmp_path / "p.csv"
    pd.DataFrame(
        [
            {
                "event_id": "E1", "market": "player_points", "segment": "game",
                "player": "Al Jones", "selection": side, "line": "10.5",
                "snapshot_phase": "card", "book": "draftkings", "season": "2024",
                "slate_date": "2024-01-02", "game_id": "G1",
                "american_odds": "-110",
            }
            for side in ("over", "under")
        ]
    ).to_csv(store, index=False)
    roster = tmp_path / "r.csv"
    pd.DataFrame(
        [("G1", "1", "Al Jones")],
        columns=["game_id", "athlete_id", "athlete_display_name"],
    ).to_csv(roster, index=False)
    taken = PC.census(store, roster=roster)
    expected = tmp_path / "e.json"
    expected.write_text(json.dumps(census_expected_record(taken), indent=1), "utf-8")
    PC.assert_reconciles(store=store, roster=roster, expected=expected)

    with pytest.raises(PC.WagerCountMismatch, match="no run has accounted for the props"):
        G.build_record(inputs_for(frame))


def test_the_guard_is_the_first_statement_and_the_filter_follows_it():
    """A gate after the de-vig is a gate on the report, not on the run."""
    source = (REPO / "src" / "cbb_betting_lab" / "reports" / "prop_grading.py").read_text(
        encoding="utf-8"
    )
    tree = ast.parse(source)
    target = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "build_record"
    )
    body = [
        statement
        for statement in target.body
        if not (
            isinstance(statement, ast.Expr)
            and isinstance(statement.value, ast.Constant)
            and isinstance(statement.value.value, str)
        )
    ]
    assert "guard_graded_frame" in ast.dump(body[0])
    # The filter runs before anything reads the frame. It is looked for in the
    # opening statements rather than in exactly the second, because the frame
    # is bound and then filtered back onto its own name — the shape
    # `tests/test_forward_evidence.py` requires so that no variable is left
    # holding the unfiltered frame.
    opening = ast.dump(ast.Module(body=list(body[:3]), type_ignores=[]))
    assert "without_markets_refused_by_name" in opening
    assert "devig" not in opening, (
        "the de-vig runs before the refusal filter, so a market refused by "
        "name is paired and priced before anything drops it"
    )
    assert (
        "cbb_betting_lab.reports.prop_grading.build_record"
        in PC.GRADING_ENTRY_POINTS
    ), "this module grades wagers and must be a declared entry point"


def test_a_market_refused_by_name_is_never_scored_and_never_given_a_verdict(receipt):
    """It is filtered after the gate. It is not a pass, an avoid or a no-value call.

    Mutation: drop the `without_markets_refused_by_name` call — RED, because the
    refused market appears in the record and carries a verdict.
    """
    refused = sorted(PR.MARKETS_REFUSED_BY_NAME)[0]
    frame = pd.concat(
        [a_population(pairs=50), a_population(pairs=50, market=refused)],
        ignore_index=True,
    )
    record = G.build_record(inputs_for(frame))
    text = json.dumps(record) + G.render(record)
    for market in PR.MARKETS_REFUSED_BY_NAME:
        assert market not in text.replace(
            json.dumps(list(PR.MARKETS_REFUSED_BY_NAME))[1:-1], ""
        ).replace(f"`{market}`", "").replace(f'"{market}"', ""), (
            f"{market} reached a scored cell. It is refused BY NAME and may "
            "never carry a number or a verdict."
        )
    assert record["devig_census"]["supplied"] == 100, (
        "the refused market's rows were counted into the de-vig, so the filter "
        "ran after the population was formed rather than before it"
    )


# --------------------------------------------------------------------------
# 2. The de-vig
# --------------------------------------------------------------------------


def test_both_de_vigs_normalise_the_pair_and_are_not_the_same_number():
    """Two methods, one pairing pass, and they disagree where they should.

    On a symmetric pair the two are equal — there is nothing for a
    favourite-longshot correction to correct. On an asymmetric one they must
    differ, or the report is printing one method under two names.
    """
    even = pd.DataFrame(pair(over_odds=-110, under_odds=-110))
    priced, census = G.devig(even)
    assert census.devigged == 2 and census.reconciles
    assert priced["fair_proportional"].sum() == pytest.approx(1.0)
    assert priced["fair_power"].sum() == pytest.approx(1.0)
    assert priced["fair_proportional"].iloc[0] == pytest.approx(
        priced["fair_power"].iloc[0], abs=1e-9
    )

    skewed = pd.DataFrame(pair(over_odds=-400, under_odds=+280))
    priced, census = G.devig(skewed)
    assert census.devigged == 2
    assert priced["fair_proportional"].sum() == pytest.approx(1.0)
    assert priced["fair_power"].sum() == pytest.approx(1.0)
    assert abs(
        priced["fair_proportional"].iloc[0] - priced["fair_power"].iloc[0]
    ) > 1e-3, (
        "the two de-vigs agree on a heavy favourite. They must not: the whole "
        "reason both are reported is that they shade a favourite differently "
        "and this lab has not measured which is right."
    )


def test_the_power_de_vig_shades_a_favourite_up_and_a_longshot_down():
    """The direction, measured, because the module's docstring states it.

    A docstring that names a direction and gets it backwards is a false
    sentence in the tree — and the first draft of this module's did, saying
    proportional shaded a favourite up when it shades it down. So the direction
    is pinned at the prices it was measured on.
    """
    from cbb_betting_lab.reports.forecast_skill import implied_probability

    def fair(over_odds, under_odds):
        first, second = implied_probability(over_odds), implied_probability(under_odds)
        exponent = G.power_exponent(first, second)
        return first / (first + second), first**exponent

    favourite_proportional, favourite_power = fair(-400, 300)
    assert favourite_proportional == pytest.approx(0.7619, abs=1e-4)
    assert favourite_power == pytest.approx(0.7824, abs=1e-4)
    assert favourite_power > favourite_proportional

    longshot_proportional, longshot_power = fair(150, -180)
    assert longshot_proportional == pytest.approx(0.3836, abs=1e-4)
    assert longshot_power == pytest.approx(0.3760, abs=1e-4)
    assert longshot_power < longshot_proportional

    even_proportional, even_power = fair(-110, -110)
    assert even_power == pytest.approx(even_proportional, abs=1e-12), (
        "a symmetric pair has no favourite-longshot asymmetry, so the two "
        "methods must agree on it exactly"
    )


def test_a_pair_is_the_same_book_and_never_two_books():
    """Design section 10 joins on the book. Pairing across books is not a hold.

    Two books each quoting one side is two half-pairs and no fair price, not one
    cross-book pair — a cross-book pair understates the hold, sometimes to
    nothing, and what comes out of it is an arbitrage wearing a fair price's
    clothes.
    """
    rows = pair(book="draftkings")[:1] + pair(book="fanduel")[1:]
    priced, census = G.devig(pd.DataFrame(rows))
    assert census.devigged == 0
    assert census.no_complement == 2
    assert census.reconciles
    assert priced["fair_proportional"].isna().all(), (
        "a row with no complement at its own book was given a fair price"
    )


def test_a_pair_whose_overround_is_not_above_one_is_refused_and_counted():
    """Dividing by a number at or below one inflates both sides above the price."""
    priced, census = G.devig(pd.DataFrame(pair(over_odds=+120, under_odds=+120)))
    assert census.overround_not_above_one == 2
    assert census.devigged == 0
    assert census.reconciles
    assert priced["fair_power"].isna().all()


def test_a_record_is_refused_when_a_census_does_not_reconcile(receipt, monkeypatch):
    """A measurement that silently loses rows still prints an interval."""
    real = G.devig

    def broken(frame):
        priced, census = real(frame)
        census.devigged += 2
        return priced, census

    monkeypatch.setattr(G, "devig", broken)
    with pytest.raises(G.PropGradingError, match="does not reconcile"):
        G.build_record(inputs_for(a_population(pairs=10)))


def test_the_vigged_comparison_is_computed_and_is_never_the_headline(receipt):
    """It is decisive in one direction only, and the report says so in words."""
    record = G.build_record(inputs_for(a_population(pairs=300)))
    scored = [cell for cell in record["by_tier"] if cell["rows"]]
    assert scored, "this fixture scored nothing, so it checks nothing"
    for cell in scored:
        assert cell["headline"] in G.HEADLINE_KEYS
        assert "vigged" not in (cell["headline"] or "")
    assert record["by_tier"][0]["vigged_market_advantage"], (
        "the vigged comparison was not computed at all. It is printed as a "
        "diagnostic precisely because losing to it is decisive."
    )
    report = G.render(record)
    assert "never a headline" in report
    assert G.VIG_HANDICAP.split(".")[0] in report


# --------------------------------------------------------------------------
# 3. The headline and the reserved phrases
# --------------------------------------------------------------------------


def test_the_headline_is_the_comparison_least_favourable_to_the_model(receipt):
    """Whichever de-vig the model does worst against, in every cell."""
    record = G.build_record(inputs_for(a_population(pairs=400)))
    for cell in record["by_tier"] + record["by_market_and_tier"]:
        if not cell.get("advantages"):
            continue
        headline = cell["advantages"][cell["headline"]]["value"]
        worst = min(
            cell["advantages"][key]["value"]
            for key in G.HEADLINE_KEYS
            if key in cell["advantages"]
        )
        assert headline == worst, (
            f"{cell['label']} headlines {cell['headline']} at {headline} while "
            f"a de-vig comparison reads {worst}. The headline is the least "
            "favourable to the model, always."
        )


def test_an_interval_that_includes_zero_is_no_demonstrated_edge_in_those_words():
    """The reserved phrase, reproduced verbatim and never paraphrased."""
    cell = {
        "rows": 500,
        "enough_evidence": True,
        "benchmarked": True,
        "headline": G.HEADLINE_KEYS[0],
        "advantages": {
            G.HEADLINE_KEYS[0]: {
                "value": 0.01,
                "enough_evidence": True,
                "verdict": S.NO_DEMONSTRATED_EDGE,
            }
        },
    }
    assert G.verdict_of(cell) == "no demonstrated edge"


def test_an_interval_excluding_zero_on_the_losing_side_is_a_demonstrated_deficit():
    """A finding, and never a null result."""
    cell = {
        "rows": 500,
        "enough_evidence": True,
        "benchmarked": True,
        "headline": G.HEADLINE_KEYS[0],
        "advantages": {
            G.HEADLINE_KEYS[0]: {
                "value": -0.05,
                "enough_evidence": True,
                "verdict": S.DEMONSTRATED_DEFICIT,
            }
        },
    }
    assert G.verdict_of(cell) == "demonstrated deficit"


def test_a_demonstrated_edge_needs_every_de_vig_and_every_convention_to_show_one():
    """One comparison excluding zero is not the same thing shown twice.

    The headline is the least favourable POINT ESTIMATE, and a cell whose
    weakest comparison happens to exclude zero while a stronger one does not is
    a cell where the two methods disagree about whether anything was shown.
    """
    advantages = {
        key: {"value": 0.05 + index * 0.01, "enough_evidence": True,
              "verdict": S.DEMONSTRATED_EDGE}
        for index, key in enumerate(G.HEADLINE_KEYS)
    }
    cell = {
        "rows": 500, "enough_evidence": True, "benchmarked": True,
        "headline": G.HEADLINE_KEYS[0], "advantages": advantages,
    }
    assert G.verdict_of(cell) == S.DEMONSTRATED_EDGE

    advantages[G.HEADLINE_KEYS[-1]]["verdict"] = S.NO_DEMONSTRATED_EDGE
    assert G.verdict_of(cell) == S.NO_DEMONSTRATED_EDGE, (
        "one comparison stopped excluding zero and the cell still claimed an "
        "edge. A claim made under one de-vig and not another is a claim about "
        "the de-vig."
    )


# --------------------------------------------------------------------------
# 4. The floors
# --------------------------------------------------------------------------


def test_below_the_declared_floor_there_is_a_phrase_and_not_a_number(receipt):
    """199 wagers is not a small edge. It is no number at all."""
    # One pair is two wagers and both sides are scored, so the scored count is
    # always even: 99 pairs is 198 wagers, which is under the floor.
    frame = a_population(pairs=99)
    record = G.build_record(inputs_for(frame))
    cell = next(c for c in record["by_tier"] if c["tier"] == "high_major")
    assert cell["rows"] == 198 < G.MINIMUM_ROWS
    assert not cell["enough_evidence"]
    assert "not enough evidence" in cell["verdict"]
    report = G.render(record)
    assert f"below the {G.MINIMUM_ROWS:,} declared in advance" in report
    advantage_rows = [
        line
        for line in report.splitlines()
        if "de-vig proportional /" in line or "de-vig power /" in line
    ]
    assert advantage_rows, "the advantage table did not render at all"
    for line in advantage_rows:
        assert "—" in line, (
            "a cell below the declared floor printed an estimate: " + line
        )


def test_the_floor_is_a_floor_on_wagers_and_not_on_quotes(receipt):
    """A wager quoted at five books is five rows and one bet.

    Mutation: use `len(frame)` instead of `wagers_in(frame)` in `measure` — RED,
    because 100 wagers over five books clears a 200-BET floor on row count.
    """
    rows: list[dict] = []
    for index in range(100):
        for book in ("a", "b", "c", "d", "e"):
            rows += pair(
                event=f"E{index}", player=f"Player {index}", book=book,
                line=10.5 + index,
            )
    frame = pd.DataFrame(rows)
    record = G.build_record(inputs_for(frame))
    cell = next(c for c in record["by_tier"] if c["tier"] == "high_major")
    assert cell["scored_rows"] == 1000
    assert cell["rows"] == 200, "the wager count is the quote count divided by books"
    assert G.wagers_in(frame) == 200


def test_below_the_cluster_floor_there_is_no_interval_either(receipt):
    """A cluster-robust sandwich with nine clusters is an artefact, not a fact."""
    frame = a_population(pairs=400, games=3, athletes=3)
    frame = frame.assign(slate_date="2024-01-02")
    record = G.build_record(inputs_for(frame))
    cell = next(c for c in record["by_tier"] if c["tier"] == "high_major")
    row = cell["advantages"][cell["headline"]]
    assert row["below_the_cluster_floor"]
    assert not row["enough_evidence"]
    assert f"below the {G.MINIMUM_CLUSTERS:,} declared in advance" in row["verdict"]


def test_a_re_render_cannot_turn_the_cluster_floor_back_into_a_verdict(receipt):
    """The defect this module's own `rebuild_cell` exists for.

    `restatement.rebuild_cell` re-derives `enough_evidence` from the stored bet
    count alone, so a cell the RUN refused for having seven clusters came back
    from a re-render carrying a verdict about an interval nobody was willing to
    state. Measured on the first record this module wrote.

    Mutation: pass `rebuild=None` in `restated` — RED.
    """
    frame = a_population(pairs=400, games=3, athletes=3).assign(
        slate_date="2024-01-02"
    )
    record = G.build_record(inputs_for(frame), looks=1)
    before = next(c for c in record["by_tier"] if c["tier"] == "high_major")
    moved = G.restated(record, looks=95, record_name="x")
    after = next(c for c in moved["by_tier"] if c["tier"] == "high_major")
    assert after["advantages"][after["headline"]]["verdict"] == (
        before["advantages"][before["headline"]]["verdict"]
    )
    assert "not enough evidence" in after["verdict"]


# --------------------------------------------------------------------------
# 5. The clustering
# --------------------------------------------------------------------------


def test_the_interval_clusters_three_ways_and_the_athlete_arm_can_win():
    """The athlete is not a refinement of the game and is not optional.

    A population where one athlete's whole ladder moves together and the games
    are otherwise independent: the athlete arm is the widest and
    `interval_three_way` must take it.
    """
    rows = []
    for athlete in range(40):
        # Every rung on one athlete carries the same sign, and each of his rungs
        # sits on a different game and a different day — so the game and the day
        # arms see independent observations and only the athlete arm sees the
        # dependence.
        sign = 1.0 if athlete % 2 == 0 else -1.0
        for rung in range(10):
            rows.append(
                {
                    "event_id": f"E{athlete * 10 + rung}",
                    "slate_date": f"2024-01-{(rung % 20) + 1:02d}",
                    "subject": f"player {athlete}",
                    "value": sign,
                }
            )
    frame = pd.DataFrame(rows)
    three = S.interval_three_way(frame, profit_column="value")
    two = S.interval_two_way(frame, profit_column="value")
    assert three.cluster_unit == S.SUBJECT_CLUSTER_UNIT
    assert three.standard_error > two.standard_error, (
        "the athlete arm was not the widest on a population built so that it "
        "is. A naive interval over these 400 rows is several times too narrow."
    )


def test_a_scored_cell_reports_its_athlete_count_beside_its_wager_count(receipt):
    """So a reader can see how many subject-opinions the interval rests on."""
    frame = a_population(pairs=1000, games=10, athletes=25)
    record = G.build_record(inputs_for(frame))
    cell = next(c for c in record["by_tier"] if c["tier"] == "high_major")
    assert cell["athletes"] == frame["player"].nunique() == 25
    assert cell["rows"] == 2 * len(frame) // 2
    assert "athlete(s)" in G.render(record)


def test_two_spellings_of_one_athlete_are_one_wager_and_not_two(receipt):
    """The declared fold, in the denominator as well as in the cluster.

    `stores.normalise_subject` is the lab's declaration and the store's own
    census counts under it: 261,870 wagers under the book's raw spelling and
    257,474 under the fold. A count taken here under the raw spelling would put
    one athlete's wager in the denominator twice and let a cell clear the
    200-bet floor on wagers that are one bet.

    Mutation: put `player` back into `WAGER_IDENTITY` — RED.
    """
    rows = pair(player="Al Jones") + pair(player="AL JONES")
    frame = pd.DataFrame(rows)
    assert len(frame) == 4
    assert G.wagers_in(frame) == 2, (
        "two capitalisations of one athlete counted as four wagers. That is "
        "this lab's own documented root-n interval defect arriving through the "
        "subject field."
    )


# --------------------------------------------------------------------------
# 6. Coverage and the far ladder
# --------------------------------------------------------------------------


def test_rungs_are_counted_along_the_ladder_and_never_in_points():
    """The ladders in this store are not evenly spaced.

    Measured on the 2024 card store: adjacent quoted lines are 1.0 apart on
    1,444 steps and 2.0 apart on 858, and a points ladder can run
    `9.5, 11.5, 12.5, 14.5`. A fixed half-point unit calls one rung out on an
    assists ladder two rungs and one rung out on that points ladder four.
    """
    frame = pd.DataFrame(
        [
            {
                "event_id": "E1", "market": "player_points", "player": "Al Jones",
                "line": line, "selection": "over", "american_odds": odds,
            }
            for line, odds in ((9.5, -400), (11.5, -150), (12.5, -110), (14.5, 200))
        ]
    )
    assert list(G.rungs_from_the_money(frame)) == [2.0, 1.0, 0.0, 1.0]


def test_the_money_is_the_rung_the_market_prices_closest_to_even():
    """A market-defined centre, so the coverage table is about the offer.

    Using the model's own central estimate would make it a statement about the
    model instead, and a ladder quoted only on one side of its median would then
    report its coverage against a centre the market never named.
    """
    frame = pd.DataFrame(
        [
            {
                "event_id": "E1", "market": "player_points", "player": "Al Jones",
                "line": line, "selection": "over", "american_odds": odds,
            }
            # The median LINE is 12.5; the rung priced nearest to even is 14.5.
            for line, odds in ((10.5, -600), (12.5, -300), (14.5, -105), (16.5, 400))
        ]
    )
    assert list(G.rungs_from_the_money(frame)) == [2.0, 1.0, 0.0, 1.0]


def test_the_far_ladder_is_unbenchmarked_whatever_its_interval_says(receipt):
    """An 'edge' out there is a statement about which rungs a book hung.

    Design section 10: two-sided coverage is ~99% at the money and ~1% beyond
    three rungs out, so what survives past the cut is a small and selected slice
    of a much larger offer, and the selection is the book's.
    """
    rows: list[dict] = []
    for index in range(300):
        # A ten-rung ladder per athlete, priced so the money is the first rung
        # and the last is far out.
        for rung, odds in enumerate((-105, -200, -300, -400, -500, -600, -700, -800)):
            rows += pair(
                event=f"E{index % 40}",
                player=f"Player {index}",
                line=10.5 + rung,
                over_odds=odds,
                # A real hold on every rung: a pair whose two implied
                # probabilities sum below one is refused as an arbitrage
                # wearing a fair price's clothes, and a fixture built that way
                # would leave no far ladder to judge at all.
                under_odds=-110,
                over_won=(index % 2 == 0),
                model_over=0.9,
            )
    record = G.build_record(inputs_for(pd.DataFrame(rows)))
    cell = next(c for c in record["by_tier"] if c["tier"] == "high_major")
    far = cell["unbenchmarked_cell"]
    assert far["rows"] > 0, "this fixture produced no far-ladder rows to judge"
    assert far["benchmarked"] is False
    assert far["verdict"] == G.UNBENCHMARKED, (
        "a far-ladder cell was given an ordinary verdict. Whatever its interval "
        "says, it is not an edge and is not reported as one."
    )
    assert G.UNBENCHMARKED_SENTENCE.split(".")[0] in G.render(record)


def test_coverage_is_reported_beside_every_verdict_in_wagers(receipt):
    """And in wagers on both sides, because a share above 100% is a unit error.

    Measured on the first run of this report: the scored side was counted in
    quotes and the offered side in wagers, and high-major coverage printed as
    128.5% of settled.
    """
    frame = a_population(pairs=300)
    offered = {"high_major": {"offered": 900, "priced": 700, "settled": 650}}
    record = G.build_record(inputs_for(frame, offered=offered))
    cell = next(c for c in record["by_tier"] if c["tier"] == "high_major")
    coverage = cell["coverage"]
    assert coverage["offered"] == 900 and coverage["settled"] == 650
    assert 0.0 <= coverage["two_sided_share_of_settled"] <= 1.0
    report = G.render(record)
    assert "Coverage, in wagers:" in report


# --------------------------------------------------------------------------
# 7. No pooling, and the baselines come first
# --------------------------------------------------------------------------


def test_there_is_no_pooled_division_one_row_anywhere(receipt):
    """Not in the record, not in the report, and no function computes one.

    Mutation: add a `pooled` cell to `build_record` — RED.
    """
    frame = pd.concat(
        [a_population(pairs=250, tier=tier) for tier in G.GRADED_TIERS],
        ignore_index=True,
    )
    record = G.build_record(inputs_for(frame))
    assert "pooled" not in record
    assert {c["tier"] for c in record["by_tier"]} == set(G.GRADED_TIERS)
    source = (
        REPO / "src" / "cbb_betting_lab" / "reports" / "prop_grading.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert not [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and "pool" in node.name.lower()
    ], "a function that pools the tiers now exists in this module"
    report = G.render(record)
    assert "banned in this repository" in report


def test_beating_the_control_is_never_printed_as_beating_the_market(receipt):
    """The single likeliest misreading of this report, said on the page.

    The control is a NEGATIVE control. A model can beat it decisively — the
    per-athlete evidence is worth something over a role table — and still lose
    to a de-vigged fair price, which is the only comparison that bears on
    whether anything could be bet.

    Mutation: pick the headline from all six advantages instead of the four
    de-vig ones — RED, because a tier whose control comparison excludes zero
    then carries `demonstrated edge` as its verdict.
    """
    frame = a_population(pairs=400, model_over=0.80, control_over=0.50, over_won=True)
    record = G.build_record(inputs_for(frame))
    cell = next(c for c in record["by_tier"] if c["tier"] == "high_major")
    assert cell["headline"] in G.HEADLINE_KEYS
    assert cell["control_headline"] in G.CONTROL_KEYS
    assert cell["verdict"] == cell["advantages"][cell["headline"]]["verdict"], (
        "the tier's verdict is not the market comparison's"
    )
    report = G.render(record)
    assert G.CONTROL_IS_NOT_THE_MARKET in report
    assert "Beating the control is not beating the market" in report


def test_the_two_baselines_are_printed_before_the_model(receipt):
    """Design section 10's order, held on the rendered page and not on intent.

    A table that leads with the model invites a reader to read its number before
    the two that qualify it.
    """
    record = G.build_record(inputs_for(a_population(pairs=300)))
    report = G.render(record)
    devig_at = report.index("de-vigged fair price (proportional) | baseline")
    control_at = report.index("identity-blind role-prior control (conditional) |")
    model_at = report.index("**the model (conditional)**")
    assert devig_at < model_at and control_at < model_at, (
        "the model's own number is printed above a baseline"
    )


def test_every_probability_clip_is_counted(receipt):
    """A clip is a number this module changed, and a changed number is counted."""
    rows = pair(model_over=1.0, control_over=1.0)
    frame = pd.concat([a_population(pairs=250), pd.DataFrame(rows)], ignore_index=True)
    record = G.build_record(inputs_for(frame))
    clips = record["probability_clips"]
    assert clips, "a probability of exactly 1.0 was scored without being clipped"
    assert any("model" in name for name in clips)
    assert "clipped" in G.render(record)


# --------------------------------------------------------------------------
# 7b. The pre-registration, closed
# --------------------------------------------------------------------------


def _registered() -> list[dict]:
    """The 33, off the TRACKED ledger. Never re-typed in this file."""
    payload = json.loads(
        (REPO / "data" / "outputs" / "experiment_ledger.json").read_text("utf-8")
    )
    return [
        {
            "search": entry["search"],
            "name": entry["name"],
            "predicted_direction": entry["predicted_direction"],
        }
        for entry in payload["hypotheses"]
        if entry["search"] in (G.SEARCH_VS_DEVIG, G.SEARCH_VS_CONTROL)
    ]


def test_every_one_of_the_thirty_three_finds_the_cell_that_answers_it(receipt):
    """Thirty market-by-tier cells and three controls, matched by name.

    The join between the ledger and this record is a parse of the registered
    name, and a parse can go wrong. So a registered name that finds no cell
    RAISES rather than dropping out of the answered table, which is the failure
    mode that would leave every count on the page looking right.

    Mutation: rename `player_points` in `PRICED_MARKETS` — RED.
    """
    hypotheses = _registered()
    assert len(hypotheses) == 33
    # Five athletes per event so all ten markets are reached: the combination
    # order is event-outer, and a population narrow enough to stay inside one
    # event's first few markets would leave twenty of the thirty cells empty
    # and this test asserting nothing about them.
    frame = pd.concat(
        [a_population(pairs=200, tier=tier, athletes=5) for tier in G.GRADED_TIERS],
        ignore_index=True,
    )
    record = G.build_record(inputs_for(frame, hypotheses=hypotheses))
    answered = record["hypotheses"]
    assert len(answered) == 33
    assert {row["search"] for row in answered} == {
        G.SEARCH_VS_DEVIG,
        G.SEARCH_VS_CONTROL,
    }
    assert sum(1 for row in answered if row["market"]) == 30
    assert sum(1 for row in answered if not row["market"]) == 3
    assert {row["predicted_direction"] for row in answered} == {"lower"}
    # The control hypotheses are answered by the CONTROL comparison and never
    # by the de-vig one: they are different questions and the ledger registered
    # them separately.
    assert all(row["rows"] for row in answered), (
        "a registered cell scored nothing on this fixture, so the comparison "
        "it names is untested here"
    )
    for row in answered:
        if row["market"]:
            assert row["comparison"] in G.HEADLINE_KEYS
        else:
            assert row["comparison"] in G.CONTROL_KEYS
    report = G.render(record)
    assert "The pre-registered hypotheses, answered" in report
    for row in answered:
        assert row["reading"] in report


def test_a_registered_hypothesis_with_no_cell_refuses_the_record(receipt):
    """A hypothesis may not quietly vanish from the answered set."""
    frame = a_population(pairs=200)
    with pytest.raises(G.PropGradingError, match="no such cell"):
        G.build_record(
            inputs_for(
                frame,
                hypotheses=[
                    {
                        "search": G.SEARCH_VS_DEVIG,
                        "name": "player_dunks / high_major: the model's mean "
                        "log loss is below the de-vigged two-sided fair price's",
                        "predicted_direction": "lower",
                    }
                ],
            )
        )


def test_the_answered_readings_are_re_derived_when_the_correction_moves(receipt):
    """A stale reading beside a fresh interval on one page is decision 46's defect.

    The reading a hypothesis carries is `verdict_of` asked about the comparison
    that hypothesis registered -- NOT the headline row's own verdict, which is
    what this test used to assert. The row's verdict reads the sign of one
    interval and applies none of `verdict_of`'s other three rules, so the old
    assertion passed only because it compared the table against the very thing
    the table was wrong to print.
    """
    frame = a_population(pairs=600, model_over=0.75, over_won=True)
    record = G.build_record(
        inputs_for(frame, hypotheses=_registered()), looks=1
    )
    moved = G.restated(record, looks=10_000, record_name="x")
    for before, after in zip(record["hypotheses"], moved["hypotheses"]):
        assert before["name"] == after["name"]
        cell = next(
            c
            for c in moved["by_market_and_tier"] + moved["by_tier"]
            if c["tier"] == after["tier"] and c.get("market", "") == after["market"]
        )
        against = "control" if after["search"] == G.SEARCH_VS_CONTROL else "market"
        assert after["reading"] == G.verdict_of(cell, against=against), (
            "the answered table printed a reading the cell no longer holds"
        )


# --------------------------------------------------------------------------
# 8. The restatement
# --------------------------------------------------------------------------


def test_a_restatement_widens_and_moves_no_measurement(receipt):
    """The estimate, the raw bounds, the standard error and the counts are the
    measurement, and a re-render does not re-measure."""
    record = G.build_record(inputs_for(a_population(pairs=900, days=45, games=60)), looks=30)
    moved = G.restated(record, looks=95, record_name="x")
    before = record["by_tier"][0]["advantages"][G.HEADLINE_KEYS[0]]
    after = moved["by_tier"][0]["advantages"][G.HEADLINE_KEYS[0]]
    for field in ("value", "low", "high", "standard_error", "rows", "clusters"):
        assert after[field] == before[field], f"{field} moved during a re-render"
    assert after["adjusted_low"] < before["adjusted_low"]
    assert after["adjusted_high"] > before["adjusted_high"]
    assert moved["looks"] == 95
    assert moved[G_RESTATED_FROM]["looks"] == 30


G_RESTATED_FROM = "restated_from"


def test_a_restatement_can_retract_a_claim_and_can_never_make_one(receipt):
    """A wider correction may only ever take a verdict away."""
    frame = a_population(pairs=600, model_over=0.75, over_won=True, control_over=0.5)
    record = G.build_record(inputs_for(frame), looks=1)
    verdicts = [c["verdict"] for c in record["by_tier"] if c["rows"]]
    widened = G.restated(record, looks=10_000, record_name="x")
    for before, after in zip(
        verdicts, [c["verdict"] for c in widened["by_tier"] if c["rows"]]
    ):
        if before == S.DEMONSTRATED_EDGE:
            assert after in (S.DEMONSTRATED_EDGE, S.NO_DEMONSTRATED_EDGE)
        assert after != S.DEMONSTRATED_EDGE or before == S.DEMONSTRATED_EDGE, (
            "a wider correction created a claim the narrower one did not make"
        )


def test_the_report_is_a_pure_function_of_the_record(receipt, tmp_path):
    """No clock, no frame, no ledger. Re-rendering costs nothing and repeats."""
    record = G.build_record(inputs_for(a_population(pairs=300)), looks=95)
    G.write_record(record, tmp_path / "r.json")
    read_back = G.read_record(tmp_path / "r.json")
    assert G.render(read_back) == G.render(record)
    assert G.render(G.restated(read_back, looks=95)) == G.render(
        G.restated(G.restated(read_back, looks=95), looks=95)
    )


def test_a_stale_record_version_is_refused_rather_than_rendered(tmp_path):
    """A report with holes in it is worse than no report."""
    (tmp_path / "r.json").write_text(json.dumps({"record_version": 0}), "utf-8")
    with pytest.raises(G.PropGradingError, match="version 0 record"):
        G.read_record(tmp_path / "r.json")


# --------------------------------------------------------------------------
# 9. The control
# --------------------------------------------------------------------------


def _script():
    spec = importlib.util.spec_from_file_location("run_prop_grading", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["run_prop_grading"] = module
    spec.loader.exec_module(module)
    return module


class _Shapes:
    """Just enough of `PlayerShapes` to answer the two constants the control reads."""

    def __init__(self, priors, league):
        self._priors = priors
        self._league = league

    def value(self, name):
        return {"role_prior": self._priors, "value_pmf": self._league}[name]


def test_the_control_is_the_role_prior_at_the_bucket_with_the_weight_at_zero():
    """L6's control, and it is buildable from the estimator's public helpers.

    `player_rates.shrink_rate` with `k` large enough that the credibility weight
    is nil returns the prior rate exactly; the control projection is that, for
    every stat, plus the league scoring mix. His ROLE stays — the minutes
    lattice and the bucket are untouched — and his identity goes.
    """
    module = _script()
    rate, weight = PR.shrink_rate(
        bank_stat=500.0, prior_minutes=200.0, prior_rate=0.31, k=1e12
    )
    assert weight == pytest.approx(0.0, abs=1e-9)
    assert rate == pytest.approx(0.31, abs=1e-9)

    projection = PR.PlayerProjection(
        event_id="E1",
        athlete_id="1",
        minutes_bucket=3,
        minutes_pmf=(0.0, 1.0),
        rates={"points": 0.9, "rebounds": 0.4},
        prior_weight={"points": 0.8, "rebounds": 0.7},
        value_pmf=(0.3, 0.5, 0.2),
        value_prior_events=40.0,
        value_mix_weight=0.8,
        priceable=True,
    )
    shapes = _Shapes(
        {"points": [0.1] * 9, "rebounds": [0.2] * 9},
        [0.25, 0.55, 0.20],
    )
    blind = module.identity_blind(projection, shapes=shapes)
    assert blind.rates == {"points": 0.1, "rebounds": 0.2}
    assert set(blind.prior_weight.values()) == {0.0}
    assert blind.value_pmf == (0.25, 0.55, 0.20)
    assert blind.value_mix_weight == 0.0
    # His role is kept, and every other field is the real projection's.
    assert blind.minutes_pmf == projection.minutes_pmf
    assert blind.minutes_bucket == projection.minutes_bucket
    assert blind.event_id == projection.event_id


def test_a_stat_the_role_table_cannot_answer_for_refuses_the_whole_control():
    """Half a control is not a control, and would be compared as if it were one."""
    module = _script()
    projection = PR.PlayerProjection(
        minutes_bucket=0,
        rates={"points": 0.9, "blocks": 0.1},
        prior_weight={"points": 0.8, "blocks": 0.1},
        priceable=True,
    )
    assert module.identity_blind(projection, shapes=_Shapes({"points": [0.1] * 9}, [1, 0, 0])) is None


def test_a_row_the_control_could_not_price_is_excluded_and_counted(receipt):
    """Never filled from the model's own number: that compares it with itself."""
    frame = a_population(pairs=250)
    frame.loc[frame.index[:20], "control_probability"] = None
    record = G.build_record(inputs_for(frame))
    assert record["population_census"]["no_control_probability"] == 20
    assert record["population_census"]["reconciles"]
    kept = sum(int(cell["scored_rows"]) for cell in record["by_tier"])
    assert kept == len(frame) - 20, (
        "a row the control could not price was scored anyway, which compares "
        "the model against itself"
    )


# --------------------------------------------------------------------------
# 10. The wiring
# --------------------------------------------------------------------------


def test_the_run_files_its_dispositions_and_reconciles_them():
    """It grades, so it owes the second receipt in its own process.

    A receipt lives for the length of one process and does not outlive it, so a
    grading run cannot borrow `scripts/run_prop_accounting.py`'s.
    """
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "RunDisposition(" in source
    assert "assert_every_offered_prop_is_accounted" in source
    assert "assert_reconciles" in source
    tree = ast.parse(source)
    assigned = {
        node.value.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        for node in [node]
        for node in ast.walk(node)
        if isinstance(node, ast.Attribute) and node.attr.startswith("BUCKET_")
    }
    assert not assigned, (
        f"the run assigns its own buckets {sorted(assigned)}. Every filing is "
        "made by `gameday_card.opinions_for`, the one function in the tree that "
        "decides what becomes of a prop; a second opinion out here is the shape "
        "of defect that gives an identity two counts of the same thing."
    )


def test_the_run_settles_through_the_shipped_backtest_and_not_a_copy():
    """A local copy would be free to disagree about which row settles a prop."""
    module = _script()
    backtest = module._backtest_module()
    for name in ("_grade_one", "player_index", "fixture_index", "GradingCensus"):
        assert hasattr(backtest, name)
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "from cbb_betting_lab.settlement import" not in source, (
        "the grading run imports the settlement resolver directly. It settles "
        "through the shipped backtest's own wiring so the two cannot disagree."
    )


def test_the_smoke_flag_can_never_pass_and_says_so():
    """`--days N` prices part of a store whose offered side is the whole of it."""
    module = _script()
    parser = module.build_parser()
    action = next(a for a in parser._actions if a.dest == "days")
    assert "never pass" in (action.help or "")


def test_the_rebuild_flag_reads_the_ledger_rather_than_replaying_the_record(
    tmp_path, receipt
):
    """`--rebuild-report-only` restates at TODAY's count, not the run's.

    Replaying the correction a record stores is what let this lab hold three
    corrections in force across its own documents at once, and a re-render —
    the cheapest and most-run operation here — was the thing repeating the
    oldest of them.
    """
    module = _script()
    record = G.build_record(inputs_for(a_population(pairs=400)), looks=1)
    outputs = tmp_path / "outputs"
    outputs.mkdir()
    G.write_record(record, outputs / "cbb_prop_grading.json")
    G.write_report(record, outputs / "cbb_prop_grading.md", looks=1)
    narrow = (outputs / "cbb_prop_grading.md").read_text(encoding="utf-8")
    assert "Family correction: 1 cumulative" in narrow

    (outputs / "experiment_ledger.json").write_text(
        (REPO / "data" / "outputs" / "experiment_ledger.json").read_text("utf-8"),
        encoding="utf-8",
    )
    assert module.main(["--rebuild-report-only", "--output-dir", str(outputs)]) == 0
    wide = (outputs / "cbb_prop_grading.md").read_text(encoding="utf-8")
    # Read from the ledger the test just copied in, not typed. The literal 95
    # here made this test fail on the next registration for a reason it does
    # not test: what it checks is that the re-render reads the LEDGER, and the
    # ledger's count is whatever the ledger says.
    held = len(
        json.loads((outputs / "experiment_ledger.json").read_text("utf-8"))["hypotheses"]
    )
    assert held > 1, "the copied ledger has to be wider than the record's own count"
    assert f"Family correction: {held:,} cumulative" in wide
    assert "scored at 1" in wide, (
        "a restated report has to name BOTH counts: what the run was scored at "
        "and what its verdicts are stated at"
    )
    # The record is untouched: it is the evidence of what was measured.
    assert G.read_record(outputs / "cbb_prop_grading.json")["looks"] == 1


def test_a_rebuild_with_no_record_refuses_rather_than_writing_an_empty_page(tmp_path):
    """The report is a pure function of the record and cannot exist without one."""
    module = _script()
    assert module.main(
        ["--rebuild-report-only", "--output-dir", str(tmp_path)]
    ) == module.EXIT_NOTHING_TO_MEASURE


def test_the_run_writes_nothing_under_data_manual_and_creates_no_grant():
    """Claude may withdraw an allowlist and may never grant one."""
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    assert "data/manual" not in source.replace(
        "writes nothing under `data/manual/`", ""
    )
    assert "grant(" not in source.replace("creates no\n`grant()`", "")


# --------------------------------------------------------------------------
# 11. The reading a table prints
#
# Every number below was already right. What was wrong was the WORD printed
# beside it, in three tables, each of which took a shortcut past the one
# function that is allowed to decide what a cell may be called. A verdict is
# the part a reader quotes, so a table that derives it a second way is a
# second answer to a question this module answers once.
# --------------------------------------------------------------------------


def _a_tier_cell(receipt) -> dict:
    """One real tier cell, built the way the run builds it."""
    record = G.build_record(inputs_for(a_population(pairs=400)), looks=1)
    return record["by_tier"][0]


def test_the_far_ladder_prints_no_edge_under_the_heading_that_forbids_one(receipt):
    """`UNBENCHMARKED_SENTENCE` promises, in those words, that whatever the
    interval below says it is NOT an edge and is not reported as one. The
    advantage table under it printed each row's own verdict, which reads the
    sign of the corrected bounds and knows nothing about where the row lives.
    """
    record = G.build_record(inputs_for(a_population(pairs=400)), looks=1)
    tier = record["by_tier"][0]
    # A far-ladder cell that DOES carry an edge on every comparison. Built by
    # taking a real cell and moving it past the cut, so every other key is
    # whatever the run would have written.
    far = json.loads(json.dumps(tier))
    far["benchmarked"] = False
    far["enough_evidence"] = True
    for row in far["advantages"].values():
        row["verdict"] = S.DEMONSTRATED_EDGE
        row["enough_evidence"] = True
    far["verdict"] = G.verdict_of(far)
    tier["unbenchmarked_cell"] = far

    page = G.render(record)
    assert G.UNBENCHMARKED_SENTENCE in page, "the fixture did not reach the far block"
    start = page.index("the far ladder")
    block = page[start:]
    end = block.find("\n## ")
    block = block if end < 0 else block[:end]
    assert S.DEMONSTRATED_EDGE not in block, (
        "the far-ladder block printed 'demonstrated edge' under a heading "
        "promising in its own words that it never would"
    )
    assert G.UNBENCHMARKED in block


def test_the_far_ladder_suppresses_a_deficit_for_the_same_reason(receipt):
    """Not because a deficit is unflattering: past the cut the SIGN is a
    statement about which rungs a book hung two sides on, either way."""
    cell = {"benchmarked": False}
    assert G.reading_of(cell, {"verdict": S.DEMONSTRATED_DEFICIT}) == G.UNBENCHMARKED
    assert G.reading_of(cell, {"verdict": S.DEMONSTRATED_EDGE}) == G.UNBENCHMARKED
    # A refusal is not rewritten: it already says there is no number.
    phrase = "not enough evidence (7 day cluster(s), below the 30 declared)"
    assert G.reading_of(cell, {"verdict": phrase}) == phrase
    # And a benchmarked cell is left entirely alone.
    assert (
        G.reading_of({"benchmarked": True}, {"verdict": S.DEMONSTRATED_EDGE})
        == S.DEMONSTRATED_EDGE
    )


def test_a_calibration_bin_counts_wagers_and_prints_both_counts(receipt):
    """Rows are quotes. A wager hung at three books lands in one bin three
    times, and the column that used to be headed *Wagers* held that count."""
    one_book = a_population(pairs=300)
    three_books = pd.concat(
        [one_book.assign(book=name) for name in ("draftkings", "fanduel", "betmgm")],
        ignore_index=True,
    )
    record = G.build_record(inputs_for(three_books), looks=1)
    bins = record["by_tier"][0]["calibration"][
        f"model__{G.CONVENTION_CONDITIONAL}"
    ]
    counted = [row for row in bins if row["rows"]]
    assert counted, "the fixture produced no populated calibration bin"
    for row in counted:
        assert row["wagers"] * 3 == row["rows"], (
            "three books quoting one wager is three rows and one bet"
        )
        assert row["enough_wagers"] == (row["wagers"] >= G.MINIMUM_BUCKET), (
            "the floor is a floor on bets"
        )

    page = G.render(record)
    assert "| Predicted band | Wagers | Quotes |" in page
    assert f"below the {G.MINIMUM_BUCKET}-wager floor" in page or all(
        row["enough_wagers"] for row in counted
    )
    for row in counted:
        assert f"| {row['bin']} | {row['wagers']:,} | {row['rows']:,} |" in page, (
            "the rendered row did not carry the two counts in the two columns"
        )


def test_a_bin_over_the_row_floor_but_under_the_wager_floor_gets_no_frequency(receipt):
    """The floor moved from quotes to bets, which can only ever refuse more.

    25 wagers hung at three books is 75 rows: over the 30-row floor the first
    version of this table used, and under the 30-WAGER floor it uses now.
    """
    rows = []
    for index in range(G.MINIMUM_BUCKET - 5):
        for book in ("draftkings", "fanduel", "betmgm"):
            rows += pair(
                event=f"E{index}",
                day=f"2024-01-{(index % 20) + 1:02d}",
                player=f"Player {index}",
                book=book,
                model_over=0.65,
                control_over=0.5,
            )
    record = G.build_record(inputs_for(pd.DataFrame(rows)), looks=1)
    bins = record["by_tier"][0]["calibration"][f"model__{G.CONVENTION_CONDITIONAL}"]
    over = [row for row in bins if row["rows"] >= G.MINIMUM_BUCKET]
    assert over, "the fixture did not clear the ROW floor anywhere"
    assert all(not row["enough_wagers"] for row in over), (
        "a bin cleared the old row floor on bets that do not clear the new one, "
        "and it still printed a frequency"
    )
    page = G.render(record)
    assert f"below the {G.MINIMUM_BUCKET}-wager floor" in page


def test_a_control_hypothesis_is_read_against_the_control_family(receipt):
    """`verdict_of` rule 4 -- a demonstrated edge needs EVERY comparison to
    show one -- was applied to the de-vig family and to nothing else, so the
    three control hypotheses were read off their headline row alone."""
    record = G.build_record(
        inputs_for(a_population(pairs=600, model_over=0.75, over_won=True),
                   hypotheses=_registered()),
        looks=1,
    )
    tier = record["by_tier"][0]
    # The verdicts are SET rather than fitted: this test is about the rule that
    # reads them, and a fixture tuned until an edge appeared would be testing
    # the fixture. Every other key on the cell is the run's own.
    for key in G.CONTROL_KEYS:
        tier["advantages"][key]["verdict"] = S.DEMONSTRATED_EDGE
        tier["advantages"][key]["enough_evidence"] = True
    assert G.verdict_of(tier, against="control") == S.DEMONSTRATED_EDGE

    # Now let ONE convention disagree. The headline is unchanged and still says
    # edge; the cell has not shown the same thing twice.
    other = next(k for k in G.CONTROL_KEYS if k != tier["control_headline"])
    tier["advantages"][other]["verdict"] = S.NO_DEMONSTRATED_EDGE
    assert G.verdict_of(tier, against="control") == S.NO_DEMONSTRATED_EDGE, (
        "one control convention disagreed and the cell still claimed an edge"
    )

    answered = G.answered_hypotheses(
        record["hypotheses"],
        by_tier=record["by_tier"],
        by_market_and_tier=record["by_market_and_tier"],
    )
    control = [a for a in answered if a["search"] == G.SEARCH_VS_CONTROL
               and a["tier"] == tier["tier"]]
    assert control, "no control hypothesis found for this tier"
    assert all(a["reading"] == S.NO_DEMONSTRATED_EDGE for a in control), (
        "the answered table read the headline row instead of the cell"
    )


def test_a_market_hypothesis_is_never_answered_with_the_control_comparison(receipt):
    """The two comparisons answer different questions and the ledger's own
    `search` says which. Beating a role prior is not beating a price."""
    record = G.build_record(
        inputs_for(a_population(pairs=600, model_over=0.75, over_won=True),
                   hypotheses=_registered()),
        looks=1,
    )
    answered = G.answered_hypotheses(
        record["hypotheses"],
        by_tier=record["by_tier"],
        by_market_and_tier=record["by_market_and_tier"],
    )
    seen = 0
    for entry in answered:
        # A cell with no advantages names no headline, and the empty string is
        # the honest answer there rather than a comparison it did not make.
        if not entry["comparison"]:
            continue
        seen += 1
        if entry["search"] == G.SEARCH_VS_CONTROL:
            assert entry["comparison"] in G.CONTROL_KEYS
        else:
            assert entry["comparison"] in G.HEADLINE_KEYS
    assert seen, "every hypothesis came back with an empty comparison"


def test_verdict_of_refuses_a_comparison_this_record_does_not_carry():
    """Fail closed: a typo in the comparison name must not silently fall back
    to the market's verdict, which is the more flattering of the two here."""
    with pytest.raises(G.PropGradingError):
        G.verdict_of({"advantages": {}}, against="devig")


def test_a_version_one_record_is_refused_rather_than_re_rendered(tmp_path):
    """A version-1 calibration table has only the quote count, and rendering it
    would print the overstated sample the bump exists to retire."""
    path = tmp_path / "cbb_prop_grading.json"
    path.write_text(json.dumps({"record_version": 1}), encoding="utf-8")
    with pytest.raises(G.PropGradingError) as caught:
        G.read_record(path)
    assert "version 1" in str(caught.value)


# --------------------------------------------------------------------------
# 12. What a prop null could have found
#
# Twenty-three cells here read `no demonstrated edge`. Measured, their
# detectable effects run from 0.0056 to 0.0587 in log-loss units, and EIGHT of
# them carry a measured gap at least half that size -- near-misses, not blanks.
# The two tier headlines are the tightest in the record: mid-major is losing by
# 0.0045 against a detectable 0.0056. Without this column that reads as "no
# difference found" when it means "losing by nearly enough to prove it".
# --------------------------------------------------------------------------


def test_a_prop_null_says_what_advantage_it_could_have_demonstrated(receipt):
    """The column is in the page, and it is the corrected bound restated."""
    record = G.build_record(inputs_for(a_population(pairs=900, days=45, games=60)), looks=95)
    page = G.render(record)
    assert "| Could detect |" in page
    cell = record["by_tier"][0]
    row = (cell.get("advantages") or {}).get(cell.get("headline") or "")
    assert row and row.get("standard_error"), "the fixture produced no interval"
    printed = G._detectable_cell(row)
    assert printed in page

    # Two separate claims, because they are two different things and comparing
    # a rendered string against an exact float at 1e-9 is how a test comes to
    # pin a display format instead of a property.
    #
    # The ARITHMETIC: the detectable effect is the distance from the estimate
    # to the corrected bound, exactly. Not a new statistic that could disagree
    # with the interval printed beside it.
    exact = S.bonferroni_z(int(row["looks"])) * float(row["standard_error"])
    assert exact == pytest.approx(row["adjusted_high"] - row["value"], abs=1e-12)

    # The FORMAT: the cell shows that number to four places, which is the
    # precision the advantage column beside it uses.
    assert printed == f"±{exact:.4f}"


def test_the_prop_detectable_effect_moves_with_the_family(receipt):
    """Derived from the row's own `looks`, so a restatement carries it."""
    record = G.build_record(inputs_for(a_population(pairs=900, days=45, games=60)), looks=30)
    cell = record["by_tier"][0]
    row = dict((cell.get("advantages") or {}).get(cell.get("headline") or ""))
    narrow = float(G._detectable_cell(row).strip("±"))
    wide = float(G._detectable_cell(dict(row, looks=400)).strip("±"))
    assert wide > narrow, (
        "a wider search left the detectable effect alone, so it is being read "
        "from something other than the row's own family size"
    )


def test_a_prop_row_with_no_number_gets_no_detectable_effect(receipt):
    """Below the floors there is no figure, and that includes this one."""
    assert G._detectable_cell(None) == "—"
    # A row BELOW THE FLOOR that carries a real standard error. Written this
    # way because `{"enough_evidence": False}` alone has no standard error
    # either, so it returns an em dash through the second check whether or not
    # the floor is tested at all -- and a mutant deleting the floor check left
    # this test green until it was written like this.
    below = {"enough_evidence": False, "standard_error": 0.05, "looks": 95}
    assert G._detectable_cell(below) == "—", (
        "a cell below the declared floor has no number, and that includes the "
        "one saying what it could have detected"
    )
    assert G._detectable_cell(
        {"enough_evidence": True, "standard_error": 0.0, "looks": 95}
    ) == "—", (
        "a comparison with no standard error can demonstrate NOTHING, and "
        "±0.0000 would read as the sharpest row in the table"
    )


def test_the_detectable_effect_is_in_log_loss_units_not_percent(receipt):
    """This table's estimate is a log-loss difference. A percentage here would
    invite a reader to compare it against a different report's ROI column."""
    record = G.build_record(inputs_for(a_population(pairs=900, days=45, games=60)), looks=95)
    cell = record["by_tier"][0]
    row = (cell.get("advantages") or {}).get(cell.get("headline") or "")
    printed = G._detectable_cell(row)
    assert "%" not in printed, "the detectable effect is not a percentage here"
    assert printed.startswith("±")
