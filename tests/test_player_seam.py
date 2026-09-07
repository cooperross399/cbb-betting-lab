"""The seam between the team model and the player model, and what it must hold.

The property this whole file exists for is one sentence:

    **a prop must be representable on a game whose spread is not priceable.**

Two of the three rival designs made that sentence unsayable by nesting the
player projections inside `ratings.Matchup`, which returns *one entry per
priced event, or no entry at all*. `matchup()` refuses on five grounds — an
unknown venue state, a disconnected schedule graph, a quasi-neutral game with
an unknown local side, a rating outside the support, a non-positive tempo — and
not one of them is a statement about whether a player's minutes are
projectable. A container that could not hold the two answers apart would delete
every prop on every refused game silently, and the design measured where the
deletion would land: ~1.8% of quotes, concentrated before 20 November, with a
2.3x tier skew and zero low-major. `test_a_prop_prices_on_a_game_whose_spread_
does_not` asserts the sentence directly, in both directions, and it is the
assertion nesting could not have made.

Around it:

* **S1** the two censuses are independent, both ways;
* **S2** a bare dict still runs — every existing test double returns one;
* **S3** one construction site, checked by walking the tree rather than by
  convention;
* **S4** the seam fits both of its shipped callers, read off the signature;
* **S5** the seam refuses a frame that reaches the day being priced;
* **S8** the four buckets are disjoint;
* **S9** both production walk-forwards hand the player frame in — without it
  the replication raises at runtime and nothing else in the suite notices;
* **S10** the module keeps no memo that could fake a leak test.

Nothing here measures anything. Since 2026-09-06 a priceable projection carries
a PROBABILITY through the card rather than a sentence saying it cannot, and that
changes exactly one thing here: the buckets a prop can land in. It still cannot
become a bet — `gates.can_produce_a_selection(NO_REPORT)` is False and stays
False — and it is still not graded, which design 10's wager reconciliation
gates. Every number below is a count off a fixture, and none of it is a pass, an
avoid or a no-value call.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.gates import Availability, can_produce_a_selection
from cbb_betting_lab.markets import FULL_GAME
from cbb_betting_lab.conferences import Tier
from cbb_betting_lab.models import player_rates as PR
from cbb_betting_lab.models import slate
from cbb_betting_lab.reports import card_pricing, gameday_card
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.season import season_for_slate_date

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "src"
SCRIPTS = REPO / "scripts"

DAY = "2024-01-15"
EARLIER = "2024-01-14"


# --------------------------------------------------------------------------
# Fixtures: a board with a spread and a prop on the same two events
# --------------------------------------------------------------------------


def _matchup(*, priceable: bool) -> types.SimpleNamespace:
    """A matchup shaped like `ratings.Matchup`, priceable or refusing.

    A `SimpleNamespace` rather than the real dataclass on purpose: the card
    reads matchups through `_matchup_field`, so anything carrying the Protocol's
    names is as good a matchup here as the shipped one, and a test that had to
    import the model to describe its own input would be testing two things.
    """
    if priceable:
        return types.SimpleNamespace(
            home_points_per_possession=1.06,
            away_points_per_possession=0.99,
            possessions=68.0,
            priceable=True,
            unpriceable_reason="",
            venue_state="home",
            prior_weight=0.45,
        )
    return types.SimpleNamespace(
        home_points_per_possession=0.0,
        away_points_per_possession=0.0,
        possessions=0.0,
        priceable=False,
        unpriceable_reason=(
            "the schedule graph has not connected these two teams by anything "
            "but the prior"
        ),
        venue_state="home",
        prior_weight=None,
    )


def _projection(
    *,
    athlete_id: object = 4001,
    priceable: bool = True,
    reason: str = "",
) -> types.SimpleNamespace:
    """A projection shaped like `player_rates.PlayerProjection`.

    Same reasoning as `_matchup`: the seam reads exactly two fields off a
    projection — `priceable` and `unpriceable_reason` — and this carries them
    plus enough of the rest to be recognisable. It is used only where a
    projection REFUSES; the tests that price one use `_real_player_half`, which
    builds the real estimator's output, because the distribution engine reads
    the minutes lattice, seven rates and a value mix that a double cannot
    honestly carry.
    """
    return types.SimpleNamespace(
        event_id="e1",
        athlete_id=athlete_id,
        display_name="A Player",
        provider_name="A. Player",
        projected_minutes=27.4,
        priceable=priceable,
        unpriceable_reason=reason,
        priced_through=EARLIER,
    )


def _wager(*, event_id: str, market: str, player: str = "", line: float | None = -3.5):
    """One wager on one event, keyed the way the card keys it."""
    selection = "over" if player else "home"
    return card_pricing.Wager(
        key=(event_id, market, selection, line, player),
        event_id=event_id,
        slate_date=DAY,
        commence_time=f"{DAY}T23:00:00Z",
        home_team="Home State",
        away_team="Away Tech",
        market=market,
        segment=FULL_GAME,
        player=player,
        selection=selection,
        line=line,
        tier="high_major",
        quotes=(card_pricing.Quote(book="dk", american_odds=-110.0),),
    )


def _real_player_half(*, carry_shapes: bool = True):
    """`(PlayerSlate, PlayerShapes)` from the real estimator and the real file.

    `tests/test_player_rates.py` is loaded by path for its row builders, the way
    `tests/test_player_distributions.py` loads it: the alternative is a second
    fixture frame that drifts from the estimator's own, and this repository has
    the two-copies-of-one-thing family written down five times. The shapes go
    through `load_player_shapes`, never `json.load`, because an instance
    existing IS the evidence that the provenance guard ran for this season.
    """
    from cbb_betting_lab.models import player_rates
    from cbb_betting_lab.models.player_shapes import load_player_shapes

    spec = importlib.util.spec_from_file_location(
        "player_rates_fixtures", REPO / "tests" / "test_player_rates.py"
    )
    assert spec and spec.loader
    fixtures = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = fixtures
    spec.loader.exec_module(fixtures)

    shapes = load_player_shapes(
        REPO / "data" / "processed" / "cbb_player_shapes.json", priced_season=2024
    )
    result = player_rates.player_projections_for(
        day=DAY,
        player_history=fixtures._history(),
        prices=fixtures._prices("Sean Bairstow"),
        shapes=shapes,
    )
    return result, (shapes if carry_shapes else None)


def _team_history(days=(EARLIER,)) -> pd.DataFrame:
    return pd.DataFrame([{"slate_date": d, "margin": 3.0, "season": 2024} for d in days])


def _player_history(days=(EARLIER,)) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "slate_date": d,
                "season": 2024,
                "game_id": 1,
                "athlete_id": 4001,
                "athlete_display_name": "A Player",
                "team_id": 55,
                "did_not_play": False,
                "minutes": 28.0,
            }
            for d in days
        ]
    )


# --------------------------------------------------------------------------
# THE PROPERTY THAT MATTERS
# --------------------------------------------------------------------------


def test_a_prop_prices_on_a_game_whose_spread_does_not() -> None:
    """The sentence nesting inside `Matchup` made unsayable, asserted directly.

    Event `e1` carries **no matchup at all** and a priceable projection. The
    spread on it reads `no opinion`; the prop reaches the player half, is not
    refused for the name, is not refused for the athlete, and — since
    2026-09-06, when `models/player_distributions.py` was wired into the card —
    **carries a probability**. Until then the strongest form of this test
    available was that the prop came to rest on its own sentence rather than the
    team half's; the engine exists now, so the test asserts the price.

    That last step is the whole point. Under a nested container the prop could
    not have got that far: there would have been nothing to look in. The
    distance between "the model was never asked about this game" and "the model
    prices this athlete on a game it has no rating for" is exactly what this
    seam exists to preserve, and it is a distance no census that summed the two
    could report.

    The projection is the **real** estimator's, built from a cut frame, and the
    constants are the real frozen file loaded through the real provenance guard.
    A hand-assembled projection would prove the seam passes objects around; this
    proves a price comes out of the far end.
    """
    result, shapes = _real_player_half()
    model = slate.SlateModel(
        day=DAY,
        matchups={},  # NO matchup for e1. Not a refusing one — none at all.
        players=dict(result.projections),
        resolved=dict(result.resolved),
        player_priced_through=str(result.priced_through),
        shapes=shapes,
    )

    spread = _wager(event_id="e1", market="spread")
    prop = _wager(
        event_id="e1", market="player_points", player="Sean Bairstow", line=14.5
    )
    probabilities, census = gameday_card.opinions_for(
        [spread, prop], model, day=DAY
    )

    assert census.wagers == 2
    assert census.priced == 1
    assert prop.key in probabilities, (
        "the prop carries no probability on a game with no rating, which is the "
        f"whole property this file exists for. It read: {list(census.declined)}"
    )
    assert 0.0 < probabilities[prop.key] < 1.0
    assert prop.key in census.push_mass, "the push is stored beside the price"
    assert spread.key not in probabilities

    reasons = list(census.declined)
    assert reasons == [
        next(r for r in reasons if "no rating exists for this game" in r)
    ], f"the spread must read `no opinion` and nothing else declined: {reasons}"
    assert not any("never asked about this event's athletes" in r for r in reasons), (
        "the prop was turned away at the team half, which is the exact "
        "coupling this container exists to remove"
    )


def test_a_spread_prices_on_a_game_carrying_no_projection() -> None:
    """And the reverse, which is the same claim read the other way round.

    The matchup is priceable and the event carries no projection at all, so the
    spread prices and every prop on it reads `no opinion` — bucket D, never
    bucket B. A refusal and an absence are different facts and are never summed.
    """
    model = slate.SlateModel(
        day=DAY,
        matchups={"e1": _matchup(priceable=True)},
        players={},
        player_absence_reason=slate.NO_RATE_ESTIMATOR,
    )

    spread = _wager(event_id="e1", market="spread")
    prop = _wager(event_id="e1", market="player_points", player="A. Player", line=14.5)
    probabilities, census = gameday_card.opinions_for([spread, prop], model, day=DAY)

    assert spread.key in probabilities, "the spread must price"
    assert prop.key not in probabilities
    assert census.priced == 1
    reason = next(iter(census.declined))
    assert "never asked about this event's athletes" in reason
    assert "player_rates.py" in reason, (
        "the census must say WHICH absence this is. A night with no player "
        "evidence and a lab with no estimator look identical from the outside "
        "and one of them is a wiring fault"
    )


# --------------------------------------------------------------------------
# S1 — the two censuses are independent
# --------------------------------------------------------------------------


def test_s1_a_refusing_matchup_does_not_refuse_the_prop_on_the_same_game() -> None:
    """A `Matchup` that refuses is still not a statement about the athlete.

    Inheriting `matchup()`'s refusals would delete ~1.8% of prop quotes,
    concentrated before 20 November, with a 2.3x tier skew and zero low-major
    — a census of the games the team model liked, printed as a census of the
    store. The two are decoupled here and both are counted.

    Since the engine was wired the decoupling can be asserted at full strength:
    the spread is refused BY THE RATINGS MODULE and the prop on the same event
    carries a probability in the same call. One refusal, one price, and neither
    inherited the other's answer.
    """
    result, shapes = _real_player_half()
    model = slate.SlateModel(
        day=DAY,
        matchups={"e1": _matchup(priceable=False)},
        players=dict(result.projections),
        resolved=dict(result.resolved),
        player_priced_through=str(result.priced_through),
        shapes=shapes,
    )

    spread = _wager(event_id="e1", market="spread")
    prop = _wager(
        event_id="e1", market="player_points", player="Sean Bairstow", line=14.5
    )
    probabilities, census = gameday_card.opinions_for([spread, prop], model, day=DAY)

    assert any("ratings module refuses" in r for r in census.declined)
    assert census.priced == 1 and prop.key in probabilities
    assert spread.key not in probabilities
    assert len(census.declined) == 1, (
        "two wagers, one refusal and one price, and neither inherited the "
        f"other's answer: {census.declined}"
    )


def test_s1_the_player_buckets_are_all_different_sentences() -> None:
    """Priced, the athlete, the name, never asked, not one of the ten.

    Design 7: *"a missing entry means no opinion and is a different census
    bucket. The two are counted separately, always."* Five wagers, one price and
    four distinct sentences, and the refusal for the athlete is printed in the
    projection's own words rather than paraphrased.

    Until the engine was wired the first of these was a fifth SENTENCE — a
    priceable projection reading "no probability exists for this line yet". It
    is a probability now, and the bucket it left behind is a different fact
    again: a player market the model is not registered against at all
    (`player_blocks` is one of seven such in `markets.PLAYER_MARKETS`, counted
    in `tests/test_player_distributions.py`), which was reading the
    missing-engine sentence and never should have.

    The priceable projection here is the real estimator's; the refused one is a
    double, because a projection that refuses is exactly two fields and building
    a real R2 refusal would test the estimator's thresholds a second time.
    """
    refusal = (
        "refused: fewer than four prior appearances / fewer than sixty prior "
        "minutes; this would be a role-table price wearing a player's name."
    )
    name_refusal = (
        "refused: this name resolves only in tonight's box score, which is a "
        "player this lab has not seen, not a name it cannot read."
    )
    result, shapes = _real_player_half()
    players = {event: dict(by_athlete) for event, by_athlete in result.projections.items()}
    players["e1"][4002] = _projection(athlete_id=4002, priceable=False, reason=refusal)
    model = slate.SlateModel(
        day=DAY,
        matchups={},
        players=players,
        resolved={**result.resolved, ("e1", "B. Player"): 4002},
        name_refusals={("e1", "C. Player"): name_refusal},
        player_priced_through=str(result.priced_through),
        shapes=shapes,
    )

    wagers = [
        _wager(event_id="e1", market="player_points", player="Sean Bairstow", line=14.5),
        _wager(event_id="e1", market="player_points", player="B. Player", line=9.5),
        _wager(event_id="e1", market="player_points", player="C. Player", line=6.5),
        _wager(event_id="e9", market="player_points", player="D. Player", line=11.5),
        _wager(event_id="e1", market="player_blocks", player="Sean Bairstow", line=1.5),
    ]
    probabilities, census = gameday_card.opinions_for(wagers, model, day=DAY)

    assert census.wagers == 5 and census.priced == 1
    assert list(probabilities) == [wagers[0].key]
    assert set(census.declined.values()) == {1}, (
        "each declined wager landed in its own bucket; a bucket with two in it "
        f"means two states collapsed into one sentence: {census.declined}"
    )
    assert refusal in census.declined, "R2 must print in the projection's own words"
    assert name_refusal in census.declined, "R1a must print in its own words"
    assert any("never asked" in r for r in census.declined), (
        "an event the model was never asked about is its own bucket"
    )
    assert any("registered against ten markets" in r for r in census.declined), (
        "a player market outside the ten is its own bucket and must not read as "
        "a refusal, a missing engine or an opinion"
    )
    assert slate.NO_DISTRIBUTION_ENGINE not in census.declined
    assert slate.NO_ENGINE_CONSTANTS not in census.declined


# --------------------------------------------------------------------------
# S2 — a bare dict still runs
# --------------------------------------------------------------------------


def test_s2_a_bare_mapping_of_matchups_is_wrapped_and_nothing_breaks() -> None:
    """Every test double in `tests/` and the shipped model return one of these.

    They are wrapped rather than rewritten. The wrap has to say something about
    the player half — `player_priced_through` empty and a full sentence saying
    why — because an empty player half with no sentence is a silence, and a
    silence is what a wiring fault looks like from the outside.
    """
    wrapped = slate.SlateModel.coerce({"e1": _matchup(priceable=True)}, day=DAY)

    assert wrapped.day == DAY
    assert set(wrapped.matchups) == {"e1"}
    assert wrapped.players == {}
    assert wrapped.resolved == {} and wrapped.name_refusals == {}
    assert wrapped.player_priced_through == ""
    assert wrapped.player_absence_reason, "an empty player half must say why"
    assert not wrapped.was_asked_about_players("e1")

    spread = _wager(event_id="e1", market="spread")
    probabilities, census = gameday_card.opinions_for([spread], wrapped, day=DAY)
    assert spread.key in probabilities and census.priced == 1

    # And the bare mapping goes in the front door too — `opinions_for` coerces,
    # so the six existing call sites that pass a dict keep working unchanged.
    same, _ = gameday_card.opinions_for(
        [spread], {"e1": _matchup(priceable=True)}, day=DAY
    )
    assert same == probabilities


def test_s2_none_is_an_empty_slate_and_anything_else_is_refused() -> None:
    """`None` is a caller that never reached the model. A list is a fault."""
    empty = slate.SlateModel.coerce(None, day=DAY)
    assert empty.matchups == {} and empty.players == {}
    assert empty.player_absence_reason

    with pytest.raises(slate.SlateError) as raised:
        slate.SlateModel.coerce([("e1", _matchup(priceable=True))], day=DAY)
    assert "list" in str(raised.value), "the refusal must name what it got"

    # A slate built for another day is refused rather than reused: a slate
    # carried across days was priced from another day's cut, which is the
    # football lab's defect 13 wearing a container.
    built = slate.SlateModel(day=EARLIER)
    with pytest.raises(slate.SlateError) as reused:
        slate.SlateModel.coerce(built, day=DAY)
    assert EARLIER in str(reused.value) and DAY in str(reused.value)


# --------------------------------------------------------------------------
# S3 — one construction site
# --------------------------------------------------------------------------


def _python_files() -> list[Path]:
    return sorted(
        [p for p in SRC.rglob("*.py") if "__pycache__" not in p.parts]
        + [p for p in SCRIPTS.rglob("*.py") if "__pycache__" not in p.parts]
    )


def _files_naming(attribute: str) -> set[str]:
    """Every file under `src/` or `scripts/` whose AST names `attribute`.

    Reads the tree rather than trusting a convention, which is how this
    repository asserts every other one-path rule it has.
    """
    found: set[str] = set()
    for path in _python_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            named = (
                isinstance(node, ast.Attribute) and node.attr == attribute
            ) or (isinstance(node, ast.Name) and node.id == attribute)
            imported = isinstance(node, ast.ImportFrom) and any(
                alias.name == attribute for alias in node.names
            )
            if named or imported:
                found.add(str(path.relative_to(REPO)))
    return found


def test_s3_the_estimator_has_one_caller_and_it_is_the_seam() -> None:
    """`player_projections_for` is named in exactly one place, and it is here.

    A second caller is a second construction site, and two pricing paths for
    one quantity is how the football lab shipped a ladder whose −6.5 beat its
    −7.5 on a team it had made a favourite. Nothing in that output looked
    wrong.
    """
    callers = _files_naming("player_projections_for")
    assert callers == {"src/cbb_betting_lab/models/slate.py"}, (
        f"`player_projections_for` is named in {sorted(callers)}. The estimator "
        "has one caller and it is the seam; a second one is a second price for "
        "one quantity."
    )


def test_s3_the_seam_is_reached_through_coerce_at_both_production_callers() -> None:
    """Both production callers route the model's answer through one door.

    `make_price_day`'s pricer and `matchups_for_card` are the two places a
    model is called for a slate day. Each hands its answer to
    `SlateModel.coerce`, so a bare mapping and a full slate arrive downstream
    as the same object and neither caller grows its own idea of what a model
    returns.
    """
    for relative in (
        "scripts/run_price_backtest.py",
        "src/cbb_betting_lab/reports/card_matchups.py",
    ):
        source = (REPO / relative).read_text(encoding="utf-8")
        assert "SlateModel.coerce" in source, (
            f"{relative} calls a model and does not coerce its answer. A caller "
            "that reads the raw return grows its own idea of what a model "
            "returns, and the two ideas then differ on the day one of them "
            "starts returning both halves."
        )
        assert "player_history" in source, (
            f"{relative} does not name the cut player frame, so it cannot hand "
            "one to a model that declares it"
        )


# --------------------------------------------------------------------------
# S4 — the seam fits its two callers
# --------------------------------------------------------------------------


def test_s4_the_seam_fits_both_of_the_callers_that_would_ship_it() -> None:
    """Read off the signature, so this costs no season of data to run.

    `unsupplied_arguments`'s own docstring gives the reason: it is a function
    rather than four lines inside `call_model` *"so a caller can be checked
    against a model without calling it, which is the only way to assert the
    shipped seam still fits its shipped callers"*.
    """
    backtest_builds = {"day", "history", "prices", "competition", "player_history"}
    card_builds = backtest_builds | {"raw_dir"}

    assert PB.unsupplied_arguments(slate.slate_model, backtest_builds) == []
    assert PB.unsupplied_arguments(slate.slate_model, card_builds) == []
    assert PB.unsupplied_arguments(slate.slate_model, {"day"}) == [
        "history", "player_history", "prices",
    ], "the check is reading this signature, not returning empty for everything"


def test_s4_every_frame_parameter_is_keyword_only_and_has_no_default() -> None:
    """`player_games=None` is not a model that works without player games.

    It is a model left to find them some other way, and every other way is
    uncut and unstamped. `_refuse_undeclared_frames` refuses a defaulted frame
    parameter on exactly that ground, and this sits behind that seam and must
    not undo it.
    """
    import inspect

    parameters = inspect.signature(slate.slate_model).parameters
    for name in ("day", "history", "player_history", "prices"):
        parameter = parameters[name]
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, name
        assert parameter.default is inspect.Parameter.empty, (
            f"`{name}` carries a default, which declares that the model copes "
            "without it. Only the caller can declare that a frame was cut."
        )
    assert not any(
        p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values()
    ), "a signature that accepts anything declares nothing"


def test_s4_the_seams_own_argument_check_is_the_harnesss_check() -> None:
    """`slate.fits_its_callers` and `PB.unsupplied_arguments` are one rule.

    The seam may not import `reports/` — that edge does not exist in this tree
    and creating it would make the import graph circular the day the harness
    wants a model type. So the rule is restated, and the restatement is held
    against the original here rather than assumed to agree.
    """
    for offered in (
        set(),
        {"day"},
        {"day", "history"},
        {"day", "history", "prices"},
        {"day", "history", "prices", "player_history"},
        {"day", "history", "prices", "player_history", "competition", "raw_dir"},
    ):
        assert slate.fits_its_callers(offered) == PB.unsupplied_arguments(
            slate.slate_model, offered
        ), offered


def test_s4_the_latest_day_this_module_reads_is_the_harnesss_definition() -> None:
    """The stamp is read the same way on both sides of the seam, and the copy has a reason.

    `_latest_day` is not a second cut — the cut is `history_before`, made once,
    at the caller. It is a maximum, and a maximum written twice is still two
    places a `"nan"` can sort above every real date.

    **The second half of this test holds the REASON the copy exists**, because
    that reason was stated wrongly and went stale without anything noticing.
    `_latest_day`'s docstring justified not importing `price_backtest.latest_day`
    on the ground that "`reports/price_backtest.py` imports nothing from
    `models/`, and the seam is what would make that circular". Commit 0d4f195
    added `from cbb_betting_lab.models import player_census` to
    `price_backtest.py` — and the same import to `reports/forecast_skill.py` —
    so the antecedent was false from that commit on. Nothing was wrong with the
    behaviour; the written reason for a structural decision was, which is worse
    than no reason at all: the next reader checks it, finds it false, and
    "fixes" the duplication by importing `reports/` from `models/`.

    So both halves of the corrected reason are asserted here, from the sources:
    `models/slate.py` imports nothing from `reports/` (the rule), and
    `reports/price_backtest.py` DOES import from `models/` (the fact that makes
    the old sentence false and the new one true). Either going red means the
    docstring has to be re-read rather than assumed.
    """
    frames = [
        pd.DataFrame(columns=["slate_date"]),
        pd.DataFrame({"slate_date": []}),
        pd.DataFrame({"slate_date": ["2024-01-02", "2024-01-09"]}),
        pd.DataFrame({"slate_date": ["2024-01-02", None, "nan", ""]}),
        pd.DataFrame({"margin": [1.0, 2.0]}),
    ]
    for frame in frames:
        assert slate._latest_day(frame) == PB.latest_day(frame), frame.to_dict()

    def _modules_imported_by(path: Path) -> set[str]:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names.add(node.module or "")
            elif isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
        return names

    models = SRC / "cbb_betting_lab" / "models"
    reports = SRC / "cbb_betting_lab" / "reports"

    imported_by_slate = _modules_imported_by(models / "slate.py")
    assert not any(
        name.startswith("cbb_betting_lab.reports") for name in imported_by_slate
    ), (
        "`models/slate.py` now imports from `reports/`, which is the edge "
        "`_latest_day`'s duplication exists to avoid. `reports` already depends "
        "on `models`, so this closes `models -> reports -> models`. It may not "
        f"raise today, which is the danger. Imported: {sorted(imported_by_slate)}"
    )

    imported_by_backtest = _modules_imported_by(reports / "price_backtest.py")
    assert any(
        name.startswith("cbb_betting_lab.models") for name in imported_by_backtest
    ), (
        "`reports/price_backtest.py` no longer imports from `models/`. That was "
        "the state `_latest_day`'s ORIGINAL justification described, and commit "
        "0d4f195 ended it; the docstring now says reports depends on models and "
        "that importing back would close the cycle. Re-read it and say which of "
        "the two states the tree is in — do not leave a third stale reason. "
        f"Imported: {sorted(imported_by_backtest)}"
    )
    # Both absence sentences say which absence they are, and `_player_half`'s
    # bullets have to name them the same way. The estimator bullet said "the
    # estimator is not written" while :data:`NO_RATE_ESTIMATOR` said "could not
    # be imported" — a docstring describing a check the constant does not make,
    # and the same drift `NO_DISTRIBUTION_ENGINE` was re-pointed for.
    for sentence in (slate.NO_RATE_ESTIMATOR, slate.NO_DISTRIBUTION_ENGINE):
        assert "could not be imported" in sentence, sentence
        assert "is not written" not in sentence, sentence
    half = slate._player_half.__doc__ or ""
    # Each bullet is its own text and not the prose that follows the list: the
    # paragraph after it names two of these constants, and a split that swept
    # it into the last bullet would report every constant as named twice.
    bullets = [bullet.split("\n\n")[0] for bullet in half.split("\n    * ")[1:]]
    assert len(bullets) >= 5, (
        "`_player_half`'s docstring lists fewer than the five absences it "
        f"returns; a return with no bullet is an absence nobody documented: {bullets}"
    )
    named = {
        constant: [bullet for bullet in bullets if constant in bullet]
        for constant in ("NO_SUBJECT_COLUMNS", "NO_RATE_ESTIMATOR", "NO_PLAYER_HISTORY")
    }
    for constant, matches in named.items():
        assert len(matches) == 1, (
            f"`_player_half`'s docstring names {constant} in {len(matches)} "
            "bullet(s) and must name it in exactly one. A return with no "
            f"bullet is an absence nobody documented: {bullets}"
        )
    # Found by the constant it names rather than by position, because the
    # position moved: the price frame's check was added ahead of this one, and
    # a test that asserted "the first bullet" would have failed on a correct
    # docstring while passing on one whose estimator bullet had drifted.
    assert "could not be imported" in named["NO_RATE_ESTIMATOR"][0], (
        "`_player_half`'s NO_RATE_ESTIMATOR bullet no longer describes that "
        "sentence in its own terms. It read 'the estimator is not written' "
        "while the sentence said 'could not be imported' — a tree that LOST a "
        "file and a lab that never had one are different facts. It reads: "
        f"{named['NO_RATE_ESTIMATOR'][0].strip()!r}"
    )


# --------------------------------------------------------------------------
# S5 — the seam refuses a frame that reaches the day
# --------------------------------------------------------------------------


@pytest.mark.parametrize("reaching", [DAY, "2024-02-01"])
def test_s5_a_player_frame_that_reaches_the_day_is_refused(reaching: str) -> None:
    """The construction site asks the question the harness asks of the stamp.

    A stamp's floor comes from the caller. A guard whose floor comes only from
    the thing it guards cannot see that thing get the floor wrong — so the
    construction site checks the frames in its hands, before it builds
    anything, and names both the day and the row count that reaches it.
    """
    with pytest.raises(slate.SlateLeak) as raised:
        slate.slate_model(
            day=DAY,
            history=_team_history(),
            player_history=_player_history((EARLIER, reaching)),
            prices=pd.DataFrame({"event_id": ["e1"], "game_id": [1]}),
        )
    message = str(raised.value)
    assert DAY in message and reaching in message
    assert "1 row(s)" in message, "the refusal must say how much reaches the day"
    assert "player history" in message


def test_s5_a_team_frame_that_reaches_the_day_is_refused_the_same_way() -> None:
    """Both frames, one rule. The cut is one function and so is the check."""
    with pytest.raises(slate.SlateLeak) as raised:
        slate.slate_model(
            day=DAY,
            history=_team_history((EARLIER, DAY)),
            player_history=_player_history(),
            prices=pd.DataFrame({"event_id": ["e1"], "game_id": [1]}),
        )
    assert "team history" in str(raised.value)


def test_s5_the_same_frame_handed_in_twice_is_refused() -> None:
    """One keyword wide, and it would project athletes off team-game rows."""
    frame = _team_history()
    with pytest.raises(slate.SlateError) as raised:
        slate.slate_model(
            day=DAY,
            history=frame,
            player_history=frame,
            prices=pd.DataFrame({"event_id": ["e1"], "game_id": [1]}),
        )
    assert "same object" in str(raised.value)


def test_s5_a_player_frame_missing_a_declared_column_is_refused_not_defaulted() -> None:
    """`require_columns`' rule, one level down.

    A missing column read as a zero is how the football lab's props backtest
    reported zero bets and had that read as a finding about the model.
    """
    frame = _player_history().drop(columns=["minutes", "did_not_play"])
    with pytest.raises(slate.SlateError) as raised:
        slate.slate_model(
            day=DAY,
            history=_team_history(),
            player_history=frame,
            prices=pd.DataFrame({"event_id": ["e1"], "game_id": [1]}),
        )
    assert "minutes" in str(raised.value) and "did_not_play" in str(raised.value)


def test_s5_a_day_in_no_season_is_an_empty_slate_not_a_raise() -> None:
    """`matchups_for` returns `{}` for one, and this matches it, with the reason.

    Every well-formed date belongs to a season — `season_for_slate_date` cuts
    on 1 July and returns 0 only for a day it cannot read — so the day that
    reaches this branch is an unreadable one, which is exactly the case a
    silent empty slate would hide.
    """
    from cbb_betting_lab.season import season_for_slate_date

    unreadable = "not-a-day"
    assert season_for_slate_date(unreadable) == 0

    built = slate.slate_model(
        day=unreadable,
        history=_team_history(),
        player_history=_player_history(),
        prices=pd.DataFrame({"event_id": ["e1"], "game_id": [1]}),
    )
    assert built.matchups == {} and built.players == {}
    assert built.player_absence_reason == slate.NO_SEASON


# --------------------------------------------------------------------------
# S8 — the buckets are disjoint, and the invariants say so
# --------------------------------------------------------------------------


def test_s8_a_pair_that_is_both_resolved_and_refused_is_a_contradiction() -> None:
    """A refusal and an opinion on one spelling would be counted twice.

    In opposite directions, which is worse than counting it once wrongly: the
    resolution rate and the refusal census would both move, and the sum would
    still reconcile.
    """
    model = slate.SlateModel(
        day=DAY,
        players={"e1": {4001: _projection()}},
        resolved={("e1", "A. Player"): 4001},
        name_refusals={("e1", "A. Player"): "refused: ..."},
        player_priced_through=EARLIER,
    )
    with pytest.raises(slate.SlateError) as raised:
        slate._assert_invariants(
            model, prices=pd.DataFrame({"event_id": ["e1"]}), day=DAY
        )
    assert "both resolved" in str(raised.value)


def test_s8_a_resolution_reaching_no_projection_is_refused() -> None:
    """A name matched to an athlete the model never projected reaches nothing."""
    model = slate.SlateModel(
        day=DAY,
        players={"e1": {4001: _projection()}},
        resolved={("e1", "A. Player"): 9999},
        player_priced_through=EARLIER,
    )
    with pytest.raises(slate.SlateError) as raised:
        slate._assert_invariants(
            model, prices=pd.DataFrame({"event_id": ["e1"]}), day=DAY
        )
    assert "9999" in str(raised.value)


def test_s8_a_projection_on_an_event_nobody_quoted_is_refused() -> None:
    """A bet on a game with no price is not a bet, and counting one invents it."""
    model = slate.SlateModel(
        day=DAY,
        players={"e404": {4001: _projection()}},
        player_priced_through=EARLIER,
    )
    with pytest.raises(slate.SlateError) as raised:
        slate._assert_invariants(
            model, prices=pd.DataFrame({"event_id": ["e1"]}), day=DAY
        )
    assert "e404" in str(raised.value)


def test_s8_a_populated_player_half_with_a_blank_stamp_is_refused() -> None:
    """The blank is the one value a leaking pricer would want.

    `assert_walk_forward` exempts `""` — a blank means *this frame was not
    read* — so a pricer that read the settlement table and then declined to say
    what it read would pass the guard by saying nothing at all.
    """
    model = slate.SlateModel(
        day=DAY,
        players={"e1": {4001: _projection()}},
        player_priced_through="",
    )
    with pytest.raises(slate.SlateError) as raised:
        slate._assert_invariants(
            model, prices=pd.DataFrame({"event_id": ["e1"]}), day=DAY
        )
    assert "assert_walk_forward" in str(raised.value)


def test_s8_a_stamp_at_or_after_the_day_is_refused() -> None:
    """The projection's own declaration is checked, not only the frame's."""
    model = slate.SlateModel(
        day=DAY,
        players={"e1": {4001: _projection()}},
        player_priced_through=DAY,
    )
    with pytest.raises(slate.SlateLeak):
        slate._assert_invariants(
            model, prices=pd.DataFrame({"event_id": ["e1"]}), day=DAY
        )


# --------------------------------------------------------------------------
# S9 — both production walk-forwards hand the frame in
# --------------------------------------------------------------------------


def test_s9_both_production_walk_forwards_declare_the_player_frame() -> None:
    """Without `frames=` the replication raises at runtime and nothing notices.

    `make_price_day`'s pricer declares `player_history`, and
    `_refuse_undeclared_frames` refuses a pricer that reaches past what the
    caller cut — so a `walk_forward` call without the frame is a
    `BacktestError` on the first day it prices. The backtest's own tests would
    catch it; the replication's would not, because the replication is not run
    in this suite. Asserted on the call site rather than on a mock, so it is a
    fact about the shipped script.
    """
    for relative in ("scripts/run_price_backtest.py", "scripts/run_replication.py"):
        tree = ast.parse((REPO / relative).read_text(encoding="utf-8"))
        calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "walk_forward"
        ]
        assert calls, f"{relative} no longer calls walk_forward"
        for call in calls:
            frames = [k for k in call.keywords if k.arg == "frames"]
            assert frames, (
                f"{relative} calls walk_forward with no `frames=`. The pricer "
                "declares `player_history`, so this run raises BacktestError "
                "on its first priced day and scores nothing."
            )
            keys = [
                k.value
                for k in ast.walk(frames[0].value)
                if isinstance(k, ast.Constant) and isinstance(k.value, str)
            ]
            assert "player_history" in keys, (
                f"{relative} hands in a frame under a name the pricer does not "
                f"declare: {keys}"
            )
            assert not any(k.arg == "frame_day_columns" for k in call.keywords), (
                "the player table's day column is `slate_date`, which is "
                "walk_forward's default. A second place naming it is a second "
                "place it can be named wrongly, and the frame would then be "
                "cut to nothing every night rather than raise."
            )


def test_s9_the_stand_in_player_frame_carries_the_columns_the_seam_declares() -> None:
    """A board with no props is not a broken table, and must not look like one.

    `walk_forward` raises on a frame it cannot cut — correctly, because
    `history_before` would otherwise hand the pricer an empty frame every night
    and a player model priced off nothing looks exactly like a player model
    with no opinions. So the stand-in for "the board carries no player market"
    is a frame with the declared columns and no rows, not `pd.DataFrame()`.
    """
    stand_in = pd.DataFrame(columns=list(slate.REQUIRED_PLAYER_COLUMNS))
    assert slate.SLATE_DAY_COLUMN in stand_in.columns
    assert slate.SLATE_DAY_COLUMN == "slate_date", (
        "equal to walk_forward's default `game_day_column`, which is why no "
        "call site passes `frame_day_columns`"
    )
    # The real refusal, exercised rather than asserted about: a bare frame.
    prices = pd.DataFrame(
        {"slate_date": [DAY], "event_id": ["e1"]}
    )
    games = pd.DataFrame({"slate_date": [EARLIER]})

    def price_day(*, day, history, prices, player_history):  # pragma: no cover
        return prices.copy()

    with pytest.raises(PB.BacktestError):
        PB.walk_forward(
            prices, games, price_day=price_day,
            frames={"player_history": pd.DataFrame()},
        )
    priced = PB.walk_forward(
        prices, games, price_day=price_day,
        frames={"player_history": stand_in},
    )
    assert len(priced) == 1


# --------------------------------------------------------------------------
# The real wiring: what the shipped pricer is handed, and what it stamps
# --------------------------------------------------------------------------


def _backtest_module():
    """`scripts/run_price_backtest.py`, imported the way the replication does."""
    import importlib.util

    name = "cbb_run_price_backtest_seam"
    spec = importlib.util.spec_from_file_location(
        name, SCRIPTS / "run_price_backtest.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    import sys

    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_BACKTEST_DAYS = ("2024-01-14", "2024-01-15", "2024-01-16")


def _store() -> pd.DataFrame:
    """One spread quote per day, in the store's own columns."""
    return pd.DataFrame(
        [
            {
                "event_id": f"e{i}",
                "game_id": 900_000 + i,
                "market": "spread",
                "segment": FULL_GAME,
                "player": "",
                "selection": "home",
                "line": -3.5,
                "book": "dk",
                "american_odds": -110.0,
                "provider_key": "spreads",
                "snapshot_phase": "card",
                "slate_date": day,
                "commence_time": f"{day}T23:00:00Z",
                "home_team": "Home State",
                "away_team": "Away Tech",
                "tier": "high_major",
                "season": 2024,
            }
            for i, day in enumerate(_BACKTEST_DAYS)
        ]
    )


def _uncut_players() -> pd.DataFrame:
    """The settlement table's shape: the past, tonight, and the future."""
    days = list(_BACKTEST_DAYS) + ["2024-02-20", "2025-01-01"]
    return pd.DataFrame(
        [
            {
                "slate_date": d,
                "season": 2024,
                "game_id": 1,
                "athlete_id": 4001,
                "athlete_display_name": "A Player",
                "team_id": 55,
                "did_not_play": False,
                "minutes": 28.0,
            }
            for d in days
        ]
    )


def _recording_model(*, stamp_reaches_the_day: bool = False):
    """A model that declares `player_history` and reports what it was shown."""
    seen: list[dict] = []

    def matchups_for(*, day, history, prices, competition, player_history):
        seen.append(
            {
                "day": str(day),
                "rows": int(len(player_history)),
                "max": PB.latest_day(player_history),
                "id": id(player_history),
            }
        )
        return slate.SlateModel(
            day=str(day),
            matchups={},
            players={},
            player_priced_through=(
                str(day) if stamp_reaches_the_day else PB.latest_day(player_history)
            ),
        )

    return matchups_for, seen


def test_the_shipped_pricer_is_handed_the_cut_player_frame_and_stamps_it() -> None:
    """Through `make_price_day` and `walk_forward`, not through a hand-built pricer.

    Three things at once, and none of them is provable against a fixture pricer:

    * the frame the model receives is **not** the settlement table — a boolean
      mask always returns a new object, so this alone is weak, which is why the
      row count is asserted too and the uncut table is known to hold rows dated
      on and after every priced day;
    * its latest day is strictly earlier than the day being priced;
    * the `player_priced_through` on the returned rows is **the model's own**,
      carried through `_stamp_series` untouched.

    The stamp is the half that matters. A stamp the harness computes describes
    what the caller cut; it cannot detect a pricer that read a different frame,
    which is the defect that existed here before `frames=` and the reason the
    player stamp is written by the pricer rather than for it.
    """
    backtest = _backtest_module()
    model, seen = _recording_model()
    uncut = _uncut_players()
    price_day = backtest.make_price_day(
        model,
        competition=CBB,
        accounting=backtest.OpinionAccounting(offered=3),
    )
    priced = PB.walk_forward(
        _store(),
        pd.DataFrame(
            [{"slate_date": d, "margin": 3.0, "season": 2024} for d in _BACKTEST_DAYS]
        ),
        price_day=price_day,
        frames={"player_history": uncut},
    )

    assert [call["day"] for call in seen] == sorted(_BACKTEST_DAYS)
    for call in seen:
        assert call["id"] != id(uncut), "the model was handed the settlement table"
        assert call["rows"] < len(uncut), (
            "the model was handed every row, so nothing was cut"
        )
        assert call["max"] == "" or call["max"] < call["day"], (
            f"the model for {call['day']} was shown player rows through "
            f"{call['max']}, which is not strictly earlier"
        )

    assert "player_priced_through" in priced.columns, (
        "the pricer wrote no player stamp, so `assert_walk_forward` has nothing "
        "to check about the second of its two inputs"
    )
    stamps = dict(
        zip(priced["slate_date"].astype(str), priced["player_priced_through"])
    )
    assert stamps == {
        _BACKTEST_DAYS[0]: "",
        _BACKTEST_DAYS[1]: _BACKTEST_DAYS[0],
        _BACKTEST_DAYS[2]: _BACKTEST_DAYS[1],
    }, "the stamp is the model's own report of the cut frame it was handed"
    PB.assert_walk_forward(priced)


def test_a_player_stamp_reaching_the_day_fails_the_walk_forward_guard() -> None:
    """The negative control for the check above: it can actually go red.

    `assert_walk_forward` read `priced_through` and nothing else until this
    commit, so a `player_priced_through` column was decorative — a pricer that
    read a private player frame through day D could report D and still be
    certified. It now checks **every** column ending in `_priced_through`,
    which is strictly more than it checked before and never less.
    """
    backtest = _backtest_module()
    model, _ = _recording_model(stamp_reaches_the_day=True)
    price_day = backtest.make_price_day(
        model,
        competition=CBB,
        accounting=backtest.OpinionAccounting(offered=3),
    )
    priced = PB.walk_forward(
        _store(),
        pd.DataFrame(
            [{"slate_date": d, "margin": 3.0, "season": 2024} for d in _BACKTEST_DAYS]
        ),
        price_day=price_day,
        frames={"player_history": _uncut_players()},
    )

    with pytest.raises(PB.WalkForwardLeak) as raised:
        PB.assert_walk_forward(priced)
    assert "player_priced_through" in str(raised.value), (
        "the guard must name which of the two stamps reached the day"
    )


# --------------------------------------------------------------------------
# S10 — the module keeps no memo that could fake a leak test
# --------------------------------------------------------------------------


def test_s10_the_seam_declares_no_module_level_frame_or_projection_memo() -> None:
    """A memo keyed on `(event, athlete)` is a detector that cannot fire.

    The poisoned-future test corrupts every player row dated on or after the
    day and re-prices, expecting a bit-identical answer. A module-level memo of
    a projection would return the pre-corruption object and the test would pass
    for the wrong reason — which is worse than not having the test, because it
    reads as evidence.

    One memo is permitted and it is named: the provenance-checked shapes
    object, keyed on `(path, priced_season)`, which holds no game row.
    """
    tree = ast.parse(
        (SRC / "cbb_betting_lab" / "models" / "slate.py").read_text(encoding="utf-8")
    )
    module_level: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            module_level.append(node.target.id)
        elif isinstance(node, ast.Assign):
            module_level += [t.id for t in node.targets if isinstance(t, ast.Name)]

    # **Every mutable module global, not the ones whose names end in `_CACHE`.**
    # Filtering on the name first meant a memo called `_seen`, `_projections`
    # or `_by_event` passed without being looked at, and nothing else in the
    # suite inspects this module's globals — so the check read as a scan and
    # was a spelling convention. A memo is a mutable container at module
    # level; that is what is looked for now, whatever it is called.
    values = {name: getattr(slate, name, None) for name in module_level}
    mutable = {
        name: type(value).__name__
        for name, value in values.items()
        if isinstance(value, (dict, list, set))
    }
    assert set(mutable) == {"_SHAPES_CACHE"}, (
        f"slate.py declares mutable module-level container(s) {mutable}. The "
        "only permitted one holds provenance-checked constants and no game "
        "row; a memo of a frame, a projection or a distribution makes the "
        "poisoned-future leak test pass by never recomputing anything, "
        "whatever the name on it."
    )
    assert hasattr(slate, "clear_caches"), "and it must be droppable"
    slate.clear_caches()
    assert slate._SHAPES_CACHE == {}


# --------------------------------------------------------------------------
# The limitations this seam still has, recorded as passing assertions
# --------------------------------------------------------------------------


def test_the_gaps_this_seam_still_has_are_the_ones_written_down() -> None:
    """Four, of which two have since closed; each goes red the day it does.

    The repository's form for a limitation: not a docstring claim that quietly
    becomes false, but an assertion that fails on the commit which fixes it and
    forces somebody to say so.

    1. **CLOSED.** `models/player_rates.py` did not exist when this seam
       landed, so `slate_model` returned an empty player half carrying
       `slate.NO_RATE_ESTIMATOR`. The estimator was written in the next commit,
       which turned this clause red and is what moved `player_rates.py` from
       `MODEL_FILES` to `INPUT_FILES` in
       `tests/test_the_player_props_are_pre_registered.py`. The clause is
       replaced by its successor rather than deleted: the seam is now wired to
       an estimator, and what it hands the card is a projection.
    2. **CLOSED, and replaced by its successor.**
       `models/player_distributions.py` was not written, so a priceable
       projection yielded no probability and `NO_DISTRIBUTION_ENGINE` was the
       last word on a prop. The engine was written and, on 2026-09-06, wired:
       `gameday_card.opinions_for` builds one `PlayerDistribution` per (event,
       athlete) from `SlateModel.shapes` — the constants this seam already had
       provenance-checked for the season — and
       `test_a_prop_prices_on_a_game_whose_spread_does_not` now asserts a
       PRICE on a game the team model has no rating for, which is the strongest
       form this file's central sentence has ever had. The sentence went with
       the clause: `slate.NO_DISTRIBUTION_ENGINE` no longer says the file is not
       written, it says the file could not be imported, and it is kept reachable
       for the reason `NO_RATE_ESTIMATOR` is.

       The successor is that **a priced prop still reaches no output.** It may
       not be bet — `gates.can_produce_a_selection` is CONFIRMED-only and
       Division I men's basketball has no availability report — and it may not
       be graded, because design 10's 261,870-wager reconciliation has not run.
       The assertion below is the first half of that and goes red the day a
       market with no availability report can produce a selection. Clause 3 is
       the second half: no production caller resolves `slate_model`, so no
       shipped run has built a distribution at all.
    3. **`DEFAULT_MODEL` still names the team seam.** `slate_model` is proved
       to fit both production callers (S4) and is not yet what they resolve.
       Moving it is blocked on a gate, not on the estimator:
       `test_gameday_card.py::test_a_model_the_card_cannot_supply_refuses_
       instead_of_pricing_without_it` monkeypatches `ratings.matchups_for` and
       asserts the card refuses naming both `player_games` and
       `matchups_for_card`, and under a moved `DEFAULT_MODEL` that patch is no
       longer on the path `call_model` inspects. Moving it changes the model
       string the next replication run records.
    4. **`matchups_for`'s `player_games` is withheld.** Design 2.4 directs the
       cut frame into it. Filling it flips `CarryoverFit.uses_roster` on the
       efficiency term and applies `share_as_of(day)` in `_prior_means`, which
       changes every team number this lab has published — none of which has
       been re-measured with the roster terms on. It is one keyword away, and
       it does not move inside a commit that measures nothing.
    """
    models = SRC / "cbb_betting_lab" / "models"
    assert (models / "player_rates.py").exists(), (
        "the estimator has been removed, so `slate_model`'s player half is "
        "structurally empty again and every prop census is a census of zero "
        "projections. Put `player_rates.py` back in MODEL_FILES in "
        "tests/test_the_player_props_are_pre_registered.py if that is deliberate."
    )
    assert (models / "player_distributions.py").exists(), (
        "the distribution engine has been removed, so every prop is back to a "
        "census bucket with no probability. Say so, and put the sentence back."
    )
    assert not can_produce_a_selection(Availability.NO_REPORT), (
        "a market with no availability report can now produce a selection, and "
        "since 2026-09-06 the props carry probabilities. Nothing may be bet or "
        "graded through this engine until design 10's 261,870-wager "
        "reconciliation has run: say what changed and what it rests on."
    )
    assert PB.DEFAULT_MODEL == "cbb_betting_lab.models.ratings:matchups_for", (
        "DEFAULT_MODEL has moved. Update the prose at price_backtest.py, "
        "run_price_backtest.py and run_replication.py that names the old one, "
        "and state in the report that the next replication run records a "
        "different model string than data/outputs/holdout/cbb_replication.json "
        "does — the record does not carry the model that priced it, so nothing "
        "else would notice."
    )
    tree = ast.parse((models / "slate.py").read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "matchups_for"
    ]
    assert len(calls) == 1, "the seam calls the team model exactly once"
    assert not any(k.arg == "player_games" for k in calls[0].keywords), (
        "`player_games` is now passed into `matchups_for`, which turns on the "
        "roster terms in the carryover fit and changes every published team "
        "number. Re-measure in the same commit, or take it out again."
    )


def test_the_seams_player_half_actually_runs(fixture_raw_dir) -> None:
    """The half nothing executed until now.

    Measured by mutation against a shadow copy of `src/`: prepending an early
    return to `_player_half` gave a whole-suite failure set byte-identical to
    the unmutated baseline, and returning a bare `SlateModel` from
    `slate_model` before `matchups_for` left 226 of 227 tests green across the
    seam, rates, leakage and card modules. So the estimator call, the shapes
    lookup, the live unpack path and three of the four structural-absence
    sentences were asserted only where a test supplied them itself.

    The reason was mechanical rather than anybody's oversight: every existing
    call raises before reaching the player half, and the one path that would
    not raise needs a cached hoopR schedule. The tracked fixtures are seasons
    2025 to 2027, so this drives a real 2026 game — the seam's cut is
    season-independent, and 2026 is not a season the frozen constants were
    fitted or validated on.
    """
    day = "2025-11-29"
    game_id = 401823218
    home_id, away_id = 2459, 91

    player_history = pd.DataFrame(
        [
            {
                "slate_date": "2025-11-2%d" % d,
                "season": 2026,
                "game_id": game_id - 1,
                "athlete_id": 4001,
                "athlete_display_name": "A Player",
                "team_id": home_id,
                "did_not_play": False,
                "minutes": 28.0,
                "points": 14.0,
                "rebounds": 5.0,
                "assists": 3.0,
                "threes": 2.0,
                "steals": 1.0,
                "turnovers": 2.0,
            }
            for d in (1, 2, 3, 4, 5, 6, 7, 8)
        ]
    )
    prices = pd.DataFrame(
        [
            {
                "event_id": "e1",
                "game_id": game_id,
                "market": "player_points",
                "player": "A Player",
                "selection": "over",
                "line": 13.5,
                "book": "dk",
                "season": 2026,
                "slate_date": day,
                "home_team": home_id,
                "away_team": away_id,
            }
        ]
    )

    # **The real team table, not the two-column stand-in the other tests use.**
    # `ratings.prepare` reads `game_state` and `venue_state`, which the
    # stand-in does not carry — every other call in this file raises before
    # reaching it, which is part of why the player half was never executed.
    from conftest import processed_table

    team_path, corpus = processed_table("cbb_team_games.csv")
    team_games = pd.read_csv(team_path, low_memory=False)
    team_games = team_games[team_games["slate_date"].astype(str) < day]
    print(f"team corpus={corpus} rows_before_{day}={len(team_games):,}")

    model = slate.slate_model(
        day=day,
        history=team_games,
        player_history=player_history,
        prices=prices,
        raw_dir=fixture_raw_dir,
    )

    # The half ran: it produced a stamp of its own, off the player frame rather
    # than the team frame, and it is strictly earlier than the day.
    assert model.player_priced_through, (
        "the player half produced no stamp, so it did not run — which is the "
        "state this test exists to make impossible"
    )
    assert model.player_priced_through < day
    assert model.player_priced_through == max(
        player_history["slate_date"].astype(str)
    )

    # And it reached a verdict about the subject rather than a structural
    # absence: either a projection or a named refusal, never silence.
    reached = bool(model.players) or bool(model.name_refusals) or bool(
        model.resolution_census
    )
    assert reached, (
        "the player half ran and said nothing about a quoted, resolvable "
        "subject with eight prior appearances"
    )

    # **And every projection carries a real tier.** Per-tier reporting is a
    # hard rule of this lab, and the estimator was called with no tier table at
    # all: measured, 25 of 25 projections built from the real 2024-01-20 cut
    # carried `unplaced`. The commit that writes `cbb_player_lines.csv` would
    # have written that into every row, or reached for the price store's
    # per-game `tier` column — which files a high-major starter under whichever
    # tier his opponent decided.
    projections = [p for by in model.players.values() for p in by.values()]
    assert projections, "no projection to check a tier on"
    tiers = {p.player_tier for p in projections}
    assert Tier.UNPLACED.value not in tiers, (
        f"a projection carries {Tier.UNPLACED.value!r}; the tier table the "
        "team half built was not handed to the estimator"
    )
    # It is the player's OWN team's tier, read back from the matchup that
    # named it — not a second tier table that could drift from the
    # strictly-earlier rule `matchups_for` applies.
    matchup = model.matchups[next(iter(model.matchups))]
    assert tiers == {matchup.home_tier}, (
        f"projection tiers {tiers} do not match the home side's "
        f"{matchup.home_tier!r}, and the subject plays for the home team"
    )

    # **And the constants travel with the slate.** The card builds the
    # distribution engine from `model.shapes`, which is the object
    # `load_player_shapes` checked FOR THIS SEASON; a card that opened the file
    # itself would be a second load site with a season argument it would have to
    # derive, and `_player_half` already records what an unchecked season
    # argument cost once.
    assert model.shapes is not None, (
        "the slate carries projections and not the constants they were built "
        "from, so nothing downstream can price them without opening the frozen "
        "file a second time"
    )
    assert int(model.shapes.priced_season) == 2026

    # **The wiring, end to end, on a real slate — and what it says here is a
    # refusal, in the estimator's own words.** The frame THIS test hands in is
    # narrower than the one the card reads: a value mix needs the box score and
    # this frame carries no `field_goals_made`,
    # `three_point_field_goals_made` or `free_throws_made`, so the subject is
    # refused under R6. That state is no longer the card's — since
    # `load_player_games` reads `slate.PLAYER_COLUMNS_THE_ESTIMATOR_READS` the
    # card forms a rate, which
    # `test_s11_the_card_path_can_actually_build_a_player_distribution` drives —
    # and it is still every caller's who hands over less, which is why R6 is
    # exercised here rather than deleted with the clause it used to cite. What
    # matters for the wiring is which sentence comes out: the PROJECTION'S, not
    # a missing engine and not missing constants.
    prop = _wager(event_id="e1", market="player_points", player="A Player", line=13.5)
    probabilities, census = gameday_card.opinions_for([prop], model, day=day)
    assert probabilities == {} and census.priced == 0
    reason = next(iter(census.declined))
    assert reason == projections[0].unpriceable_reason, (
        "the card paraphrased the refusal instead of printing the estimator's "
        f"own sentence: {reason}"
    )
    assert "no per-minute rate exists to shrink" in reason
    assert slate.NO_DISTRIBUTION_ENGINE not in census.declined
    assert slate.NO_ENGINE_CONSTANTS not in census.declined


def test_shapes_checked_for_another_season_are_refused(fixture_raw_dir) -> None:
    """The injection point past the provenance guard, closed.

    `load_player_shapes` refuses a season the constants were fitted or
    validated on — but it checks the SEASON ARGUMENT it is given, not the day
    anything is later priced for. Probed against the real frozen file:
    `priced_season=2023` is refused, because 2023 is the declared validation
    season, while `priced_season=2025` is accepted and returns byte-identical
    constants. So a caller could load for a permitted season and hand the
    object to a slate pricing a forbidden one, and the refusal never fired —
    the validation season priced with the constants validated on it, which is
    the one thing the frozen file exists to prevent.
    """
    from cbb_betting_lab.models.player_shapes import load_player_shapes

    frozen = REPO / "data" / "processed" / "cbb_player_shapes.json"
    day = "2025-11-29"

    # The bypass, as it was available: constants checked for a season that is
    # not this slate's.
    wrong = load_player_shapes(frozen, priced_season=2025)
    assert int(wrong.priced_season) == 2025

    model = slate.slate_model(
        day=day,  # season 2026
        history=_countable_team_games(day),
        player_history=_player_history(("2025-11-21",)),
        prices=_absence_prices(),
        shapes=wrong,
        raw_dir=fixture_raw_dir,
    )
    assert not model.players, "a slate priced on constants checked for another season"
    assert "checked for season 2025" in model.player_absence_reason
    assert "prices season 2026" in model.player_absence_reason

    # And the matching object is accepted, so the refusal is about the mismatch
    # rather than about supplying shapes at all.
    right = load_player_shapes(frozen, priced_season=2026)
    ok = slate.slate_model(
        day=day,
        history=_countable_team_games(day),
        player_history=_player_history(("2025-11-21",)),
        prices=_absence_prices(),
        shapes=right,
        raw_dir=fixture_raw_dir,
    )
    assert "checked for season" not in (ok.player_absence_reason or "")


def _countable_team_games(day: str) -> pd.DataFrame:
    """The real team table cut before `day`. `ratings.prepare` needs its columns."""
    from conftest import processed_table

    path, _ = processed_table("cbb_team_games.csv")
    frame = pd.read_csv(path, low_memory=False)
    return frame[frame["slate_date"].astype(str) < day]


# --------------------------------------------------------------------------
# The three structural absences, driven through the caller that unpacks them
# --------------------------------------------------------------------------

#: A day the tracked schedule fixtures carry, in a season the frozen constants
#: were neither fitted nor validated on. The tests below all price it, so
#: the only thing that differs between them is which absence they arrange.
ABSENCE_DAY = "2025-11-29"

#: The real fixture game on :data:`ABSENCE_DAY`, and the two teams playing it.
ABSENCE_GAME = 401823218
ABSENCE_TEAMS = (2459, 91)


def _absence_prices() -> pd.DataFrame:
    """One quoted event on `ABSENCE_DAY`, in the vocabulary the seam requires.

    A spread and no player market: the board state the absence tests below are
    about is the tree, the night or the frozen file, not the board.

    It used to be `event_id` and `game_id` alone, which was enough for
    `matchups_for` and is no longer enough for the seam: since 2026-09-07
    `slate_model` checks the price frame against
    `slate.PRICE_COLUMNS_THE_ESTIMATOR_READS` before it builds anything and
    reports :data:`slate.NO_SUBJECT_COLUMNS` for a frame the estimator cannot
    form a subject from. Widening it here is not a workaround: every real
    caller supplies these — `cbb_historical_prices__card.csv` carries all six
    and `card_matchups.MODEL_PRICE_COLUMNS` builds all six — and a fixture
    poorer than the store meant each of these tests could have been passing on
    the price frame's absence rather than on its own subject.
    """
    return pd.DataFrame(
        [
            {
                "event_id": "e1",
                "game_id": ABSENCE_GAME,
                "market": "spreads",
                "player": "",
                "home_team": ABSENCE_TEAMS[0],
                "away_team": ABSENCE_TEAMS[1],
            }
        ]
    )


def _absence_player_prices() -> pd.DataFrame:
    """The same event, quoted as a player market the estimator can find a subject in.

    `player_rates._subjects_of_the_day` reads `market`, `player` and the two
    team ids off the price frame, so the bare two-column frame the other
    absence tests use produces no subject at all. This one does.
    """
    return pd.DataFrame(
        [
            {
                "event_id": "e1",
                "game_id": ABSENCE_GAME,
                "market": "player_points",
                "player": "A Player",
                "selection": "over",
                "line": 13.5,
                "book": "dk",
                "season": season_for_slate_date(ABSENCE_DAY),
                "slate_date": ABSENCE_DAY,
                "home_team": ABSENCE_TEAMS[0],
                "away_team": ABSENCE_TEAMS[1],
            }
        ]
    )


def test_s12_a_name_refused_on_an_event_with_no_survivor_still_prints_r1bs_words(
    fixture_raw_dir,
) -> None:
    """Bucket C, on the only nights bucket C can be the whole event.

    `models/slate.py`'s header says C — `(event, the book's spelling)` refused
    for the name — and D — the event is not in `players` at all — "are counted
    separately and never summed". `gameday_card._player_decline` asked D first,
    and D is `event_id in players`, and `players` gains an entry only where a
    resolution SUCCEEDED. So on an event where every quoted spelling was
    refused for the name, the card printed D over C: the *name* refusal never
    reached a reader as words, only as a count.

    R1b made that certain rather than incidental. It is filed inside
    `if len(roster) == 0`, and the roster is computed once per event before the
    spelling loop, so R1b is all-or-nothing per event and can never be
    accompanied by a surviving projection — its sentence therefore reached NO
    output anywhere in `src/` or `scripts/`. `grep -rn` put the only read of a
    name refusal's TEXT at `gameday_card.py`'s bucket-C branch;
    `card_matchups.py` reads `len(...)` of the mapping and nothing else.

    Driven here through the shipped `slate.slate_model` on a real fixture game:
    the board quotes an athlete on teams 2459/91 and the player table carries
    only team 55, so the seam's prior-roster window finds no row for either
    side and R1b is the event's whole story. Measured on exactly this board,
    with the old order put back: the seam produces
    `name_refusals[('e1', 'A Player')] = R1B_NO_PRIOR_ROSTER`,
    `resolution_census = {'refused_no_prior_roster': 1,
    'quotes:refused_no_prior_roster': 1}` and `players = {}` either way — and
    under the old order the card declined BOTH wagers below into one bucket
    reading "the model was never asked about this event's athletes", the R1b
    sentence appearing nowhere.

    Bucket D is asserted alongside it, on the same card, so the fix cannot have
    been "always answer C": an event nobody quoted a player market on is still
    reported as never asked, and the two sentences are still different.
    """
    model = slate.slate_model(
        day=ABSENCE_DAY,
        history=_countable_team_games(ABSENCE_DAY),
        player_history=_player_history(("2025-11-21",)),
        prices=_absence_player_prices(),
        raw_dir=fixture_raw_dir,
    )

    assert model.players == {}, (
        "an athlete resolved, so this board no longer arranges the state under "
        "test: pick two teams the player frame has no row for"
    )
    assert model.name_refusals == {("e1", "A Player"): PR.R1B_NO_PRIOR_ROSTER}
    assert model.resolution_census.get(PR.ROUTE_REFUSED_NO_ROSTER) == 1
    assert not model.was_asked_about_players("e1"), (
        "`players` is empty and `was_asked_about_players` still says yes, so "
        "the ordering this test is about no longer exists"
    )

    quoted = _wager(event_id="e1", market="player_points", player="A Player", line=13.5)
    unquoted = _wager(event_id="e9", market="player_points", player="D Player", line=9.5)
    probabilities, census = gameday_card.opinions_for(
        [quoted, unquoted], model, day=ABSENCE_DAY
    )

    assert probabilities == {} and census.priced == 0
    assert set(census.declined.values()) == {1}, (
        "the name refusal and the never-asked bucket collapsed into one "
        f"sentence: {census.declined}"
    )
    assert PR.R1B_NO_PRIOR_ROSTER in census.declined, (
        "R1b is counted and printed every run per design 11 — it is the "
        "positive evidence that the model is not reading tonight's roster — "
        f"and it reached no reader: {census.declined}"
    )
    assert "no roster to read the name against" in PR.R1B_NO_PRIOR_ROSTER
    assert any("never asked" in reason for reason in census.declined), (
        "the event nobody quoted a player market on lost its own bucket, so C "
        "has swallowed D in the other direction"
    )
    assert not any(
        "never asked" in reason and "no roster to read" in reason
        for reason in census.declined
    )


def test_s12_a_tree_with_no_estimator_says_so_through_the_seams_own_caller(
    monkeypatch, fixture_raw_dir
) -> None:
    """`_player_half`'s NO_RATE_ESTIMATOR return, executed for the first time.

    The three early returns in `_player_half` — this one, the empty-frame one
    and the provenance guard's — were widened from six values to seven when
    `SlateModel.shapes` landed, and a line tracer over this file,
    `test_gameday_card.py`, `test_player_distributions.py` and
    `test_player_rates.py` recorded all three as never executed. `grep -rn
    NO_PLAYER_HISTORY tests/` returned nothing at all, and `NO_RATE_ESTIMATOR`
    appeared only as a hand-set `player_absence_reason=` field value and inside
    docstring-phrase assertions — so the module docstring's claim that a tree
    which loses a module "says which absence this is" was held for the
    SENTENCES' wording and not for the returns that produce them. Measured
    here, by reverting all three to their old six-element form and running this
    file, `test_gameday_card.py`, `test_player_distributions.py`,
    `test_player_rates.py`, `test_the_card_runs_end_to_end_offline.py`,
    `test_run_price_backtest.py` and `test_reachability.py`: 315 of 318 tests
    stayed green and the only three red were the three written below.

    That arity is the whole risk. `slate_model` unpacks seven values from this
    call, so a six-tuple is `ValueError: not enough values to unpack (expected
    7, got 6)` raised on exactly the three nights these sentences exist for:
    a tree that has lost `player_rates.py`, a night whose player frame is empty
    — the first slate date of any season, since `history_before` cuts strictly
    earlier — and a season `load_player_shapes` refuses. Each of the three
    tests here therefore drives the SEAM'S OWN CALLER rather than `_player_half`
    directly, because the caller is where the arity is read.

    The import is broken the only honest way, the way
    `test_player_distributions.py::test_the_card_says_which_absence_it_is_when_
    it_cannot_reach_the_engine` breaks the engine's: removed from `sys.modules`
    and from the package, so the real `from ... import` inside
    `_player_rates_module` is what fails rather than a patched-out branch.
    """
    import cbb_betting_lab.models as MODELS

    monkeypatch.setitem(sys.modules, "cbb_betting_lab.models.player_rates", None)
    monkeypatch.delattr(MODELS, "player_rates", raising=False)
    assert slate._player_rates_module() is None, (
        "the estimator still imports, so this test is asserting nothing"
    )

    model = slate.slate_model(
        day=ABSENCE_DAY,
        history=_countable_team_games(ABSENCE_DAY),
        player_history=_player_history(("2025-11-21",)),
        prices=_absence_prices(),
        raw_dir=fixture_raw_dir,
    )

    assert model.player_absence_reason == slate.NO_RATE_ESTIMATOR
    assert model.players == {} and model.resolved == {} and model.name_refusals == {}
    assert model.resolution_census == {}
    assert model.shapes is None, (
        "a slate that never reached an estimator carries constants, so the "
        "card would build an engine for projections that do not exist"
    )
    assert model.matchups, (
        "the team half was discarded with the player half; losing the "
        "estimator must cost the props and nothing else"
    )
    assert model.player_priced_through == "", (
        "a stamp with no projection behind it would certify a read that never "
        "happened; `assert_walk_forward` exempts the empty string"
    )

    # And the sentence reaches a reader, in the bucket that says which absence
    # it is rather than as the model having no opinion.
    prop = _wager(event_id="e1", market="player_points", player="A Player", line=13.5)
    _, census = gameday_card.opinions_for([prop], model, day=ABSENCE_DAY)
    assert census.priced == 0
    reason = next(iter(census.declined))
    assert slate.NO_RATE_ESTIMATOR in reason
    assert "player_rates.py" in reason


def test_s12_a_night_with_no_player_rows_is_a_different_absence_from_no_estimator(
    fixture_raw_dir,
) -> None:
    """`_player_half`'s NO_PLAYER_HISTORY return, executed for the first time.

    `grep -rn NO_PLAYER_HISTORY tests/` returned nothing before this test, so
    the constant existed, was reachable, and no assertion had ever seen it come
    out of anything. It is a real night and not a hypothetical: the cut is
    `history_before`, which is strictly earlier, so the first slate date of any
    season hands this seam an empty player frame while the team half still
    prices off the prior season's rows.

    The point of the bucket is that it is NOT the previous test's. Both leave
    `players` empty; one is a lab with no model and one is a night with no
    evidence, and `models/slate.py`'s header says they are counted separately
    and never summed. Asserted here as two different sentences out of the same
    caller on the same board.
    """
    empty = pd.DataFrame(columns=list(slate.REQUIRED_PLAYER_COLUMNS))
    assert len(empty) == 0

    model = slate.slate_model(
        day=ABSENCE_DAY,
        history=_countable_team_games(ABSENCE_DAY),
        player_history=empty,
        prices=_absence_prices(),
        raw_dir=fixture_raw_dir,
    )

    assert model.player_absence_reason == slate.NO_PLAYER_HISTORY
    assert model.player_absence_reason != slate.NO_RATE_ESTIMATOR, (
        "a night with no evidence and a lab with no model print one sentence, "
        "which is the collapse this module's header forbids"
    )
    assert model.players == {} and model.shapes is None
    assert model.matchups, "the team half prices on a night with no player rows"

    prop = _wager(event_id="e1", market="player_points", player="A Player", line=13.5)
    _, census = gameday_card.opinions_for([prop], model, day=ABSENCE_DAY)
    reason = next(iter(census.declined))
    assert slate.NO_PLAYER_HISTORY in reason
    assert "player_rates.py" not in reason, (
        "an empty frame is reported as a missing estimator, which sends an "
        "operator looking for a wiring fault that is not there"
    )


def test_s12_a_frozen_file_that_refuses_this_season_returns_the_guards_own_words(
    monkeypatch, tmp_path: Path, fixture_raw_dir
) -> None:
    """`_player_half`'s provenance-guard return, executed for the first time.

    The third widened early return, and the one whose sentence is not a
    constant at all: it is `str(exc)` from the real `ShapesFileError`, kept
    verbatim because the guard names the constant and the window and a
    paraphrase would lose exactly the part an operator needs.

    Driven through the REAL guard rather than a raise stubbed in. The shipped
    `data/processed/cbb_player_shapes.json` declares `fit_seasons`
    [2019, 2020, 2021, 2022] and `validation_season` 2023, and the schedule
    fixtures this file can price are seasons 2025-2027 — so no day this seam
    can actually reach `_player_half` on is a season the shipped file refuses.
    A copy of it declaring the priced season as its validation season is
    therefore the only way to make the shipped `load_player_shapes` refuse on a
    day the rest of the seam can run, and it is `load_player_shapes` that
    refuses: `_shapes_for` is left alone, its memo included, and only the file
    it opens is redirected.

    Note what is asserted about `shapes` on the way out. The return hands back
    `None`, not the argument, so a slate whose constants were refused cannot
    carry constants — and `gameday_card._player_decline` reads
    `NO_ENGINE_CONSTANTS` off exactly that field. A six-element return here
    would have made `slate_model` raise instead, on a day whose only fault is
    that the frozen file has seen it.
    """
    from cbb_betting_lab.models.player_shapes import load_player_shapes

    frozen = REPO / "data" / "processed" / "cbb_player_shapes.json"
    document = json.loads(frozen.read_text(encoding="utf-8"))
    assert int(document["validation_season"]) == 2023, (
        "the frozen file's validation season moved; this test builds its copy "
        "around it and the number in the docstring above is now wrong"
    )
    document["validation_season"] = season_for_slate_date(ABSENCE_DAY)
    refusing = tmp_path / "refuses-this-season.json"
    refusing.write_text(json.dumps(document), encoding="utf-8")

    slate.clear_caches()
    monkeypatch.setattr(
        slate,
        "load_player_shapes",
        lambda path, *, priced_season: load_player_shapes(
            refusing, priced_season=priced_season
        ),
    )
    monkeypatch.setattr(slate, "_SHAPES_CACHE", {})

    model = slate.slate_model(
        day=ABSENCE_DAY,
        history=_countable_team_games(ABSENCE_DAY),
        player_history=_player_history(("2025-11-21",)),
        prices=_absence_prices(),
        raw_dir=fixture_raw_dir,
    )

    assert model.players == {}
    assert model.shapes is None, (
        "the slate carries the constants the guard just refused, so the card "
        "would build an engine from them"
    )
    reason = model.player_absence_reason
    assert reason and reason not in (
        slate.NO_RATE_ESTIMATOR,
        slate.NO_PLAYER_HISTORY,
        slate.NO_PROJECTION_FORMED,
    ), f"the guard's refusal was reported as one of the other absences: {reason}"
    assert str(season_for_slate_date(ABSENCE_DAY)) in reason, (
        "the guard's sentence names the season it refused and the seam must "
        f"pass it through unparaphrased: {reason}"
    )
    assert "validation" in reason, (
        f"the refusal reaching the slate is not the provenance guard's: {reason}"
    )
    assert model.matchups, "the team half is discarded with the constants"

    prop = _wager(event_id="e1", market="player_points", player="A Player", line=13.5)
    _, census = gameday_card.opinions_for([prop], model, day=ABSENCE_DAY)
    assert census.priced == 0
    assert reason in next(iter(census.declined))


# --------------------------------------------------------------------------
# S11: the shipped card path can actually reach the estimator
# --------------------------------------------------------------------------

#: A day the tracked schedule fixtures carry and the tracked player sample has
#: prior evidence for. Season 2026 is not a season the frozen constants were
#: fitted or validated on, which is why the other real-corpus tests in this
#: file use it too.
CARD_DAY = "2026-02-07"


def _deepest_rosters(day: str, *, games: int, subjects: int):
    """`games` fixtures on `day`, each with the `subjects` best-evidenced names.

    Chosen from whichever corpus `conftest` hands over — the full processed
    table when it is built, the tracked sample when it is not — because a day
    and a roster hard-coded against one of them is a test that asserts
    something on a laptop and nothing in CI. The pick is on prior appearances
    and prior minutes ONLY, which are R2's own two thresholds: the point is to
    hand the estimator a board it has evidence about, and nothing here reads an
    outcome, a price or a settled result.

    Returns the schedule records, a name list per record, and the corpus label
    to print beside any count taken over it.
    """
    from conftest import processed_table, schedule_fixture

    schedule = pd.read_parquet(schedule_fixture(season_for_slate_date(day)))
    on_day = schedule[schedule["game_date"].astype(str) == day]
    assert not on_day.empty, f"the schedule fixture carries no game on {day}"

    path, corpus = processed_table("cbb_player_games.csv")
    frame = pd.read_csv(
        path,
        usecols=[
            "slate_date", "season", "game_id", "team_id", "athlete_display_name",
            "minutes", "did_not_play",
        ],
        low_memory=False,
    )
    # **This season only, and strictly before the day.** The estimator's bank
    # resets at every season boundary — admitting a carry-over needs a decay
    # constant nobody has fitted — so an athlete whose minutes are all last
    # season's has no projection at all, and picking him would build a board
    # the estimator refuses under R3 while the corpus looked deep. The full
    # processed table carries eight seasons and the tracked sample carries one,
    # which is exactly how that reads as a corpus difference rather than as the
    # rule it is.
    played = frame[
        (frame["slate_date"].astype(str) < day)
        & (frame["season"].astype(int) == int(season_for_slate_date(day)))
        & (~frame["did_not_play"].astype(str).str.strip().str.lower().eq("true"))
    ]
    evidence = (
        played.groupby(["team_id", "athlete_display_name"])
        .agg(games=("game_id", "count"), minutes=("minutes", "sum"))
        .reset_index()
    )
    # R2's floor, restated from the estimator rather than retyped: fewer than
    # four played games or sixty prior minutes is a role-table price wearing a
    # player's name, and a board of those would prove nothing about the wiring.
    regulars = evidence[
        (evidence["games"] >= PR.MIN_PRIOR_GAMES)
        & (evidence["minutes"] >= PR.MIN_PRIOR_MINUTES)
    ].sort_values("minutes", ascending=False)
    by_team: dict[int, list[str]] = {}
    for record in regulars.to_dict("records"):
        by_team.setdefault(int(record["team_id"]), []).append(
            str(record["athlete_display_name"])
        )

    ranked = sorted(
        on_day.to_dict("records"),
        key=lambda r: -(
            len(by_team.get(int(r["home_id"]), ()))
            + len(by_team.get(int(r["away_id"]), ()))
        ),
    )[:games]
    rosters = []
    for record in ranked:
        names = (
            by_team.get(int(record["home_id"]), [])[: subjects // 2]
            + by_team.get(int(record["away_id"]), [])[: subjects // 2]
        )
        rosters.append(names)
    return ranked, rosters, corpus


def _card_board(day: str, *, games: int = 4, subjects: int = 4):
    """A board for `day` through the real stager: two team markets and props.

    Built from provider-shaped payloads rather than assembled as a frame, so
    the `player` column arrives where the card gets it — the provider's
    `description` — rather than from a test that agreed with itself.
    """
    fixtures, rosters, corpus = _deepest_rosters(day, games=games, subjects=subjects)
    tip = datetime.fromisoformat(f"{day}T19:00:00").replace(tzinfo=CBB.timezone)
    payloads = []
    for record, names in zip(fixtures, rosters):
        home, away = str(record["home_display_name"]), str(record["away_display_name"])
        markets = [
            {"key": "h2h", "outcomes": [
                {"name": home, "price": -140},
                {"name": away, "price": 120},
            ]},
        ]
        if names:
            markets.append({"key": "player_points", "outcomes": [
                {"name": side, "description": name, "price": -110, "point": 12.5}
                for name in names
                for side in ("Over", "Under")
            ]})
        payloads.append({
            "id": f"evt-{int(record['id'])}",
            "commence_time": tip.astimezone(timezone.utc)
            .replace(microsecond=0).isoformat().replace("+00:00", "Z"),
            "home_team": home,
            "away_team": away,
            "bookmakers": [
                {"key": "draftkings", "title": "DraftKings", "markets": markets}
            ],
        })
    return gameday_card.board_from_payloads(payloads, competition=CBB), corpus


def test_s11_the_card_path_can_actually_build_a_player_distribution(
    fixture_raw_dir, fixture_processed_dir
) -> None:
    """The seam is reachable from `reports/card_matchups.py`, and was not.

    **The defect, in two halves, both measured before they were repaired.**
    `matchups_for_card` said in its own docstring that its call site was
    identical for the team seam and for `slate.slate_model`, so that shipping
    the player half was "a one-line change to `DEFAULT_MODEL` rather than a
    change to the card". Driven with that swap over a four-game board carrying
    32 `player_points` quotes on 16 athletes, on the tracked sample corpus:

    * `attach_game_ids` handed the model a frame of `event_id` and `game_id`.
      `player_rates._subjects_of_the_day` reads `market`, `player` and the two
      team ids, so it found **no subject at all** — 0 projections, an empty
      resolution census, 0 name refusals — and every prop was declined as *"the
      model was never asked about this event's athletes"*, which was true.
    * with a price frame the model could read, `load_player_games`' eight
      columns then refused **13 of 16** subjects under R6 ("no per-minute rate
      exists to shrink") for 0 priced props, because those eight carry no box
      score. The same board over `slate.PLAYER_COLUMNS_THE_ESTIMATOR_READS`
      priced 26 of 48 wagers.

    Either one alone was enough to make design 4's stop rule unreachable on the
    card: `_run_the_structural_check` returns before evaluating anything when
    no distribution was built, so the single automatic refusal the design puts
    on the engine's own output could not fire on the only path that ships.

    **This asserts shape, not size.** The numbers above are the sample corpus's
    and the counts here are printed rather than pinned, because `conftest`
    hands the full processed table to a laptop and the tracked sample to CI.
    Nothing is graded: every count is a census off a fixture board, and no ROI,
    edge or verdict is stated or implied.
    """
    from cbb_betting_lab.reports import card_matchups

    board, corpus = _card_board(CARD_DAY)
    props = board.rows[board.rows["market"] == "player_points"]
    assert not props.empty, "the fixture board carries no prop to ask about"
    print(
        f"player corpus={corpus} board events={board.rows['event_id'].nunique()} "
        f"rows={len(board.rows):,} prop rows={len(props):,} "
        f"subjects={props['player'].nunique()}"
    )

    built = card_matchups.matchups_for_card(
        board.rows,
        competition=CBB,
        day=CARD_DAY,
        processed_dir=fixture_processed_dir,
        raw_dir=fixture_raw_dir,
        model=slate.slate_model,
    )

    # The subjects reach the estimator at all. This is the half `attach_game_ids`
    # deleted, and its symptom was an empty census rather than a refusal.
    projections = [p for by in built.slate.players.values() for p in by.values()]
    assert projections, (
        "the card asked the seam about a board carrying "
        f"{props['player'].nunique()} quoted athletes and got no projection: "
        f"census={dict(built.slate.resolution_census)}, "
        f"absence={built.slate.player_absence_reason!r}"
    )
    assert built.slate.resolution_census, "subjects were projected and none was counted"

    # And a rate was formed. This is the half the eight columns deleted, and
    # its symptom was R6 on every athlete.
    priceable = [p for p in projections if p.priceable]
    refusals = {p.unpriceable_reason for p in projections if not p.priceable}
    assert priceable, (
        "every athlete on the card path is refused, so no distribution is "
        f"built: {sorted(r[:90] for r in refusals)}"
    )
    assert not any(r.startswith(PR.R6_NO_BOX_SCORE_COLUMNS) for r in refusals), (
        "the card is still handing the estimator a frame with no box score"
    )
    assert set(slate.PLAYER_COLUMNS_THE_ESTIMATOR_READS) >= set(
        PR.REQUIRED_STAT_COLUMNS
    )

    # Which is what design 4's stop rule needs to be ASKED on this path.
    wagers, _, _ = card_pricing.build_wagers(board.rows, competition=CBB)
    probabilities, census = gameday_card.opinions_for(wagers, built.slate, day=CARD_DAY)
    priced_props = [
        wager for wager in wagers
        if wager.key in probabilities and str(wager.market).startswith("player_")
    ]
    assert priced_props, "no prop on the card carries a probability"
    assert census.structural_check, (
        "the card built distributions and design 4's structural check was "
        "still not asked"
    )
    assert census.structural_check["population_athletes"] >= 1.0
    print(
        f"projections={len(projections)} priceable={len(priceable)} "
        f"priced={census.priced:,} of {census.wagers:,} wager(s), "
        f"props priced={len(priced_props):,}; "
        f"{census.structural_check_line()}"
    )


def test_s11_the_columns_the_card_reads_are_the_columns_the_estimator_reads(
) -> None:
    """One list, restated once, and held equal to the one the estimator uses.

    `slate.PLAYER_COLUMNS_THE_ESTIMATOR_READS` is a copy of
    `player_rates._POOL_COLUMNS`, made because `slate` imports the estimator
    inside the call — so that `NO_RATE_ESTIMATOR` stays reachable in a tree
    that has lost the file — and a module-level import would trade one
    reachable sentence for one import-time crash. A copy nobody checks is how
    the two drift, and a drift here is silent: the card would read a column
    short and every athlete would come back refused, which is exactly the state
    this pair of tests exists against.

    The eight are deliberately NOT grown into this list. `slate_model` raises
    `SlateError` on a frame missing a required column, so requiring the box
    score would turn a table built without `steals` into a refusal of the whole
    card, team half included, where R6 refuses the athlete and names the
    column.
    """
    assert tuple(slate.PLAYER_COLUMNS_THE_ESTIMATOR_READS) == tuple(PR._POOL_COLUMNS), (
        "the seam's declared read list and the estimator's day pool have "
        "drifted; the card would read whichever is shorter"
    )
    assert set(slate.REQUIRED_PLAYER_COLUMNS) < set(
        slate.PLAYER_COLUMNS_THE_ESTIMATOR_READS
    ), "the columns the seam requires to exist must be a subset of what it reads"
    assert not set(PR.REQUIRED_STAT_COLUMNS) <= set(slate.REQUIRED_PLAYER_COLUMNS), (
        "the required-to-exist list now carries the box score, so a processed "
        "table built without one stat column refuses the whole card instead of "
        "refusing the athlete under R6. Say why that is the better trade."
    )


def test_s11_the_frame_the_card_hands_the_model_is_the_stores_vocabulary() -> None:
    """`home_team` is a team id in the frame and a school name on the board.

    The translation `model_prices` makes, asserted on both sides of it, because
    one word means two things here and the failure it produces is silent rather
    than loud: hand the estimator the board's own frame and every quoted
    spelling is resolved against a league-wide roster instead of two teams,
    which is a name matched to the wrong athlete rather than a refusal.

    The store is the authority on the vocabulary — `home_team`/`away_team` are
    hoopR ids in `cbb_historical_prices__card.csv` and the school names live in
    `home_name`/`away_name` — because that is the frame
    `scripts/run_price_backtest.py` hands the same estimator, and two callers
    handing one function two vocabularies is the defect this pins.
    """
    from conftest import schedule_fixture
    from cbb_betting_lab.reports import card_matchups

    board, _ = _card_board(CARD_DAY)
    schedule = pd.read_parquet(schedule_fixture(season_for_slate_date(CARD_DAY)))
    joined, _, _ = card_matchups.attach_game_ids(
        board.rows, day=CARD_DAY, schedule=schedule
    )
    joined = joined.dropna(subset=["game_id"])
    asked = card_matchups.model_prices(board.rows, joined)

    assert list(asked.columns) == list(card_matchups.MODEL_PRICE_COLUMNS)
    assert len(asked) == len(board.rows), "a quote on a joined game was dropped"
    by_id = {int(record["id"]): record for record in schedule.to_dict("records")}
    for record in asked.to_dict("records"):
        fixture = by_id[int(record["game_id"])]
        assert record["home_team"] == int(fixture["home_id"]), (
            "the frame's `home_team` is not the fixture's team id, so the "
            "estimator resolves every spelling against a league-wide roster"
        )
        assert record["away_team"] == int(fixture["away_id"])
        assert isinstance(record["home_team"], int), (
            "the id arrives as a float, and a float game or team id written "
            "into a stored row no longer joins to the tables that carry ints"
        )
        assert record["home_name"] == str(fixture["home_display_name"])
        assert record["away_name"] == str(fixture["away_display_name"])

    props = asked[asked["market"] == "player_points"]
    assert not props.empty and (props["player"].str.len() > 0).all(), (
        "the athlete the book quoted did not survive into the frame the model "
        "reads, which is the state in which no board produces a subject"
    )


# --------------------------------------------------------------------------
# S12 — the third frame, declared and checked at the boundary
# --------------------------------------------------------------------------


def test_s12_the_price_columns_the_card_supplies_are_the_price_columns_the_estimator_reads(
) -> None:
    """The third declared list, held against its reader and against both callers.

    Two frames reaching this seam had a declared column list and a boundary
    check — `REQUIRED_PLAYER_COLUMNS` and `PLAYER_COLUMNS_THE_ESTIMATOR_READS`
    — and the third had neither, so the layer below assumed a vocabulary the
    layer above never promised. That is the shape of every wiring fault this
    seam has had, and it is what
    `slate.PRICE_COLUMNS_THE_ESTIMATOR_READS` closes.

    A copy nobody checks is how two lists drift, and a drift here is silent in
    the worst direction: a frame short of `market` or `player` produces no
    subject at all, and a frame short of `home_team`/`away_team` resolves every
    spelling against a league-wide roster instead of two teams — a name matched
    to the wrong athlete rather than a refusal.

    Both shipped suppliers are held to it: `card_matchups.MODEL_PRICE_COLUMNS`,
    which the card builds, and the real header of
    `data/processed/cbb_historical_prices__card.csv`, which
    `scripts/run_price_backtest.py` hands the same estimator. Two callers
    handing one function two vocabularies is the defect this pins.
    """
    from cbb_betting_lab.reports import card_matchups

    assert tuple(slate.PRICE_COLUMNS_THE_ESTIMATOR_READS) == tuple(PR._SUBJECT_COLUMNS), (
        "the seam's declared price-frame list and the columns "
        "`_subjects_of_the_day` reads have drifted; the seam would refuse a "
        "frame the estimator can read, or accept one it cannot"
    )
    assert set(card_matchups.MODEL_PRICE_COLUMNS) >= set(
        slate.PRICE_COLUMNS_THE_ESTIMATOR_READS
    ), (
        "the card builds a price frame missing a column the seam requires, so "
        "every card run would report the player half as a wiring absence"
    )

    store = REPO / "data" / "processed" / "cbb_historical_prices__card.csv"
    if store.is_file():
        header = pd.read_csv(store, nrows=0)
        missing = [
            column
            for column in slate.PRICE_COLUMNS_THE_ESTIMATOR_READS
            if column not in header.columns
        ]
        assert not missing, (
            f"{store} carries no {missing}, so the backtest's own price frame "
            "would be refused by the seam it feeds"
        )


def test_s12_a_price_frame_that_forms_no_subject_is_a_refusal_not_an_absence_of_quotes(
    monkeypatch, fixture_raw_dir, fixture_processed_dir
) -> None:
    """The break nobody predicted, refused in words at the boundary.

    `attach_game_ids` returns one row per event, and that frame — not the
    board's quotes — was what the card handed the model. `player_rates.
    _subjects_of_the_day` returns an empty subject set for a frame with no
    `market` or no `player` column, so the day came back with 0 projections, an
    empty resolution census and 0 name refusals, and `_unpack` reported
    `NO_PROJECTION_FORMED` — *"either no player market was quoted or every
    quoted subject was refused for the name"* — for a board carrying quotes on
    real athletes. A fact about the wiring, printed as a fact about the board.

    Reproduced here at the card's own entry point by putting the historical
    two-column frame back, on a board that does carry props. What the seam says
    now is :data:`slate.NO_SUBJECT_COLUMNS` with the missing columns named, and
    the team half still prices — which is the trade this check makes
    deliberately: a price frame is not the player table, and refusing the whole
    slate for it would delete every spread on the card.

    Mutation: delete the `if price_frame_refusal:` return in `_player_half` —
    this test goes red on the sentence, reporting `NO_PROJECTION_FORMED`.
    """
    from cbb_betting_lab.reports import card_matchups

    board, corpus = _card_board(CARD_DAY)
    props = board.rows[board.rows["market"] == "player_points"]
    assert not props.empty, "the fixture board carries no prop to ask about"

    def _the_frame_the_card_used_to_hand_over(rows, joined):
        return joined[["event_id", "game_id"]].copy()

    monkeypatch.setattr(
        card_matchups, "model_prices", _the_frame_the_card_used_to_hand_over
    )
    built = card_matchups.matchups_for_card(
        board.rows,
        competition=CBB,
        day=CARD_DAY,
        processed_dir=fixture_processed_dir,
        raw_dir=fixture_raw_dir,
        model=slate.slate_model,
    )

    reason = built.slate.player_absence_reason
    assert reason.startswith(slate.NO_SUBJECT_COLUMNS), (
        "a price frame the estimator cannot form a subject from was reported "
        f"as something other than a wiring absence: {reason!r}"
    )
    assert reason != slate.NO_PROJECTION_FORMED
    for column in ("market", "player", "home_team", "away_team"):
        assert column in reason.rsplit("Missing", 1)[-1], (
            f"the refusal does not name the missing {column!r}, so an operator "
            f"cannot act on it: {reason!r}"
        )
    assert not built.slate.players and not built.slate.resolution_census

    # And the team half is untouched. This is the half a `SlateError` here
    # would have deleted, and the reason the check refuses the player half in
    # words rather than raising.
    assert built.matchups, (
        "the price frame's refusal took the team half with it, which is the "
        "trade `REQUIRED_PLAYER_COLUMNS` argues against in the other direction"
    )
    print(
        f"corpus={corpus} events={len(built.matchups):,} priced by the team "
        f"half; player half refused: {reason[:80]}..."
    )


def test_s12_the_union_of_the_two_name_buckets_is_the_boards_quoted_pairs(
    monkeypatch, fixture_raw_dir, fixture_processed_dir
) -> None:
    """I6: the half of the disjointness claim that was checked nowhere.

    Three docstrings assert that `resolved` and `name_refusals` are disjoint
    AND that their union is exactly the day's distinct player-market (event,
    spelling) pairs — `SlateModel`'s own, `player_projections_for`'s ("`models/
    slate.py` asserts ... that their union is exactly the day's distinct
    pairs") and `player_rates.subjects_quoted`'s. Only the disjointness half was
    checked: `_assert_invariants` I4 intersected the two and stopped. A subject
    that fell out of the estimator's loop into neither bucket was an athlete
    the book quoted, projected on nobody, counted in no census and named in no
    sentence — the silent direction of the same defect the resolution census
    exists to make loud.

    Held here at the card's own entry point, in three parts: the union agrees
    with `subjects_quoted` on the real board; a pair removed from `resolved`
    raises; a pair added to `name_refusals` that nobody quoted raises. The two
    doctored runs go through the shipped `slate_model`, because the invariant
    is asserted there and a test that called `_assert_invariants` directly
    would pass with the call site deleted.
    """
    from cbb_betting_lab.reports import card_matchups

    board, corpus = _card_board(CARD_DAY)
    seen: dict[str, object] = {}
    real = PR.player_projections_for

    def _record(**kwargs):
        seen["prices"] = kwargs["prices"]
        result = real(**kwargs)
        seen["result"] = result
        return result

    monkeypatch.setattr(PR, "player_projections_for", _record)
    built = card_matchups.matchups_for_card(
        board.rows,
        competition=CBB,
        day=CARD_DAY,
        processed_dir=fixture_processed_dir,
        raw_dir=fixture_raw_dir,
        model=slate.slate_model,
    )
    quoted = PR.subjects_quoted(seen["prices"])
    union = set(built.slate.resolved) | set(built.slate.name_refusals)
    assert quoted, "the board produced no subject, so the invariant is vacuous here"
    assert union == quoted, (
        f"{len(quoted - union)} quoted pair(s) reached neither bucket and "
        f"{len(union - quoted)} pair(s) in neither census were counted anyway"
    )
    print(f"corpus={corpus} union={len(union)} pair(s) == quoted={len(quoted)}")

    from dataclasses import replace as _replace

    dropped = dict(seen["result"].resolved)
    lost = sorted(dropped)[0]
    dropped.pop(lost)
    monkeypatch.setattr(
        PR,
        "player_projections_for",
        lambda **kwargs: _replace(real(**kwargs), resolved=dropped),
    )
    with pytest.raises(slate.SlateError) as raised:
        card_matchups.matchups_for_card(
            board.rows,
            competition=CBB,
            day=CARD_DAY,
            processed_dir=fixture_processed_dir,
            raw_dir=fixture_raw_dir,
            model=slate.slate_model,
        )
    assert "reached neither bucket" in str(raised.value), str(raised.value)
    assert "no census counted" in str(raised.value)

    invented = dict(seen["result"].name_refusals)
    invented[("no-such-event", "no such athlete")] = "refused"
    monkeypatch.setattr(
        PR,
        "player_projections_for",
        lambda **kwargs: _replace(real(**kwargs), name_refusals=invented),
    )
    with pytest.raises(slate.SlateError) as raised:
        card_matchups.matchups_for_card(
            board.rows,
            competition=CBB,
            day=CARD_DAY,
            processed_dir=fixture_processed_dir,
            raw_dir=fixture_raw_dir,
            model=slate.slate_model,
        )
    assert "manufactured out of a name" in str(raised.value), str(raised.value)


def test_s12_an_incomplete_frozen_file_refuses_the_player_half_instead_of_raising(
    monkeypatch, tmp_path: Path, fixture_raw_dir, fixture_processed_dir
) -> None:
    """A constant the file does not carry is a wiring fault, not a traceback.

    `load_player_shapes` checks PROVENANCE and never completeness, so a frozen
    file that lost `role_prior` loads, passes the guard, and then raises
    `ShapesFileError: ... carries no constant named 'role_prior'` from inside
    `_rates`, on the first athlete of the first event. Nothing on the way out
    catches it — `slate._player_half` has no `try` — so an incomplete file took
    the whole slate down, TEAM HALF INCLUDED, on a card whose spreads were fine.
    That is the crash-instead-of-refusal shape `minutes_half_life` was repaired
    for at caller level, wearing an absent constant instead of a refused one.

    A constant recorded UNFITTABLE is a different fact and keeps its different
    answer: R5, a `priceable=False` projection carrying the fit's own sentence,
    which the card prints. This is the file saying nothing at all.

    Both halves are driven here through `matchups_for_card` — the shipped card
    path — and the second half is the measurement: with
    `missing_constants` answering `[]`, the same run raises `ShapesFileError`
    out of the card.
    """
    from cbb_betting_lab.models.player_shapes import ShapesFileError, load_player_shapes
    from cbb_betting_lab.reports import card_matchups

    frozen = REPO / "data" / "processed" / "cbb_player_shapes.json"
    document = json.loads(frozen.read_text(encoding="utf-8"))
    assert "role_prior" in document["constants"], (
        "the frozen file no longer carries `role_prior`; this test deletes it "
        "to build the incomplete-file state and has nothing to delete"
    )
    del document["constants"]["role_prior"]
    incomplete = tmp_path / "incomplete.json"
    incomplete.write_text(json.dumps(document), encoding="utf-8")

    slate.clear_caches()
    monkeypatch.setattr(
        slate,
        "load_player_shapes",
        lambda path, *, priced_season: load_player_shapes(
            incomplete, priced_season=priced_season
        ),
    )
    monkeypatch.setattr(slate, "_SHAPES_CACHE", {})

    board, corpus = _card_board(CARD_DAY)
    built = card_matchups.matchups_for_card(
        board.rows,
        competition=CBB,
        day=CARD_DAY,
        processed_dir=fixture_processed_dir,
        raw_dir=fixture_raw_dir,
        model=slate.slate_model,
    )
    reason = built.slate.player_absence_reason
    assert reason.startswith(PR.NO_SUCH_CONSTANT), (
        f"an incomplete frozen file was reported as something else: {reason!r}"
    )
    assert "role_prior" in reason, (
        f"the refusal does not name the constant that is missing: {reason!r}"
    )
    assert not built.slate.players and built.slate.shapes is None
    assert built.matchups, "the incomplete file took the team half with it"
    assert PR.missing_constants(
        load_player_shapes(incomplete, priced_season=season_for_slate_date(CARD_DAY))
    ) == ["role_prior"]
    print(f"corpus={corpus} incomplete file refused: {reason[:70]}...")

    # What the check is worth, measured on the same run: without it the card
    # raises out of the subject loop and the team half goes with it.
    monkeypatch.setattr(PR, "missing_constants", lambda shapes: [])
    with pytest.raises(ShapesFileError) as raised:
        card_matchups.matchups_for_card(
            board.rows,
            competition=CBB,
            day=CARD_DAY,
            processed_dir=fixture_processed_dir,
            raw_dir=fixture_raw_dir,
            model=slate.slate_model,
        )
    assert "role_prior" in str(raised.value)
