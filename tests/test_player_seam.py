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

Nothing here measures anything. `gates.can_produce_a_selection(NO_REPORT)` is
False and stays False, so no prop reaches a card; every number below is a
count off a fixture, and none of it is a pass, an avoid or a no-value call.
"""

from __future__ import annotations

import ast
import types
from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.markets import FULL_GAME
from cbb_betting_lab.models import slate
from cbb_betting_lab.reports import card_pricing, gameday_card
from cbb_betting_lab.reports import price_backtest as PB

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

    Same reasoning as `_matchup`, and with more force: `player_rates.py` is not
    written, so there is nothing to import. The seam reads exactly two fields
    off a projection — `priceable` and `unpriceable_reason` — and this carries
    them plus enough of the rest to be recognisable.
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
    refused for the name, is not refused for the athlete, and comes to rest on
    the one honest remaining answer — that
    `models/player_distributions.py` is not written, so no probability exists
    for the line yet.

    That last step is the whole point. Under a nested container the prop could
    not have got that far: there would have been nothing to look in. The
    distance between "the model was never asked about this game" and "the model
    projects this athlete and the engine that would price him is not built" is
    exactly what this seam exists to preserve, and it is a distance no census
    that summed the two could report.
    """
    model = slate.SlateModel(
        day=DAY,
        matchups={},  # NO matchup for e1. Not a refusing one — none at all.
        players={"e1": {4001: _projection()}},
        resolved={("e1", "A. Player"): 4001},
        player_priced_through=EARLIER,
    )

    spread = _wager(event_id="e1", market="spread")
    prop = _wager(event_id="e1", market="player_points", player="A. Player", line=14.5)
    probabilities, census = gameday_card.opinions_for(
        [spread, prop], model, day=DAY
    )

    assert probabilities == {}, "nothing may be priced while there is no engine"
    assert census.wagers == 2
    assert census.priced == 0

    reasons = list(census.declined)
    assert any("no rating exists for this game" in r for r in reasons), (
        "the spread must read `no opinion`: there is no matchup for this event"
    )
    assert slate.NO_DISTRIBUTION_ENGINE in reasons, (
        "the prop reached the player half and was answered on its own terms. "
        f"It instead read: {reasons}"
    )
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
    """
    model = slate.SlateModel(
        day=DAY,
        matchups={"e1": _matchup(priceable=False)},
        players={"e1": {4001: _projection()}},
        resolved={("e1", "A. Player"): 4001},
        player_priced_through=EARLIER,
    )

    spread = _wager(event_id="e1", market="spread")
    prop = _wager(event_id="e1", market="player_points", player="A. Player", line=14.5)
    _, census = gameday_card.opinions_for([spread, prop], model, day=DAY)

    assert any("ratings module refuses" in r for r in census.declined)
    assert slate.NO_DISTRIBUTION_ENGINE in census.declined
    assert len(census.declined) == 2, (
        "two wagers, two different reasons, and neither inherited the other's"
    )


def test_s1_the_four_player_buckets_are_four_different_sentences() -> None:
    """Never asked, the name, the athlete, no engine — and never summed.

    Design 7: *"a missing entry means no opinion and is a different census
    bucket. The two are counted separately, always."* Four wagers, four
    distinct sentences, and the refusal for the athlete is printed in the
    projection's own words rather than paraphrased.
    """
    refusal = (
        "refused: fewer than four prior appearances / fewer than sixty prior "
        "minutes; this would be a role-table price wearing a player's name."
    )
    name_refusal = (
        "refused: this name resolves only in tonight's box score, which is a "
        "player this lab has not seen, not a name it cannot read."
    )
    model = slate.SlateModel(
        day=DAY,
        matchups={},
        players={
            "e1": {
                4001: _projection(athlete_id=4001),
                4002: _projection(athlete_id=4002, priceable=False, reason=refusal),
            }
        },
        resolved={("e1", "A. Player"): 4001, ("e1", "B. Player"): 4002},
        name_refusals={("e1", "C. Player"): name_refusal},
        player_priced_through=EARLIER,
    )

    wagers = [
        _wager(event_id="e1", market="player_points", player="A. Player", line=14.5),
        _wager(event_id="e1", market="player_points", player="B. Player", line=9.5),
        _wager(event_id="e1", market="player_points", player="C. Player", line=6.5),
        _wager(event_id="e9", market="player_points", player="D. Player", line=11.5),
    ]
    _, census = gameday_card.opinions_for(wagers, model, day=DAY)

    assert census.wagers == 4 and census.priced == 0
    assert set(census.declined.values()) == {1}, (
        "each wager landed in its own bucket; a bucket with two in it means "
        f"two states collapsed into one sentence: {census.declined}"
    )
    assert slate.NO_DISTRIBUTION_ENGINE in census.declined
    assert refusal in census.declined, "R2 must print in the projection's own words"
    assert name_refusal in census.declined, "R1a must print in its own words"
    assert any("never asked" in r for r in census.declined), (
        "an event the model was never asked about is its own bucket"
    )


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
    """The stamp is read the same way on both sides of the seam.

    `_latest_day` is not a second cut — the cut is `history_before`, made once,
    at the caller. It is a maximum, and a maximum written twice is still two
    places a `"nan"` can sort above every real date.
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

    memos = [name for name in module_level if name.endswith("_CACHE")]
    assert memos == ["_SHAPES_CACHE"], (
        f"slate.py declares module-level memo(s) {memos}. The only permitted "
        "one holds provenance-checked constants and no game row; a memo of a "
        "frame, a projection or a distribution makes the poisoned-future leak "
        "test pass by never recomputing anything."
    )
    assert hasattr(slate, "clear_caches"), "and it must be droppable"
    slate.clear_caches()
    assert slate._SHAPES_CACHE == {}


# --------------------------------------------------------------------------
# The limitations this seam still has, recorded as passing assertions
# --------------------------------------------------------------------------


def test_the_gaps_this_seam_still_has_are_the_ones_written_down() -> None:
    """Four, of which one has since closed; each goes red the day it does.

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
    2. **No engine.** `models/player_distributions.py` is not written, so a
       priceable projection still yields no probability.
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
    assert not (models / "player_distributions.py").exists(), (
        "the distribution engine now exists, so a priceable projection can "
        "carry a probability and `NO_DISTRIBUTION_ENGINE` is no longer the "
        "last word on a prop. Delete this clause and the sentence with it."
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
