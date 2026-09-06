"""The leak tests the estimator can carry, and the ones that must wait.

Design 11 names nine. Six and a half of them are answerable by a rate
estimator and a seam, and the rest are not, so this file carries the six and a
half and says in its own assertions why the others are absent rather than
leaving them looking done.

**Carried here.** L1 poisoned future, L2 the stamp, L3 the frame the estimator
reads, L4 constant provenance, L5 identity sensitivity, L8's mechanical half,
and L9's estimator-level and player-season clauses.

**Refused for this commit, with the reason.** L6 (the identity-blind
role-prior control) and L7 (a seeded leak with a calibrated floor) are
mean-log-loss comparisons against settled outcomes: they need
`models/player_distributions.py`, the de-vig and the grading path, and their
outputs are measured numbers this build may not state. L8's *direction* half —
"small and in the direction of slightly worse" — is the same. L9(d), "the
fitted dispersions match the unfiltered constants to 1%", cannot be written at
all: `data/processed/cbb_player_shapes.json` records no unfiltered counterpart
for any dispersion constant, so the comparison would require a refit inside a
test. Each of those is a passing assertion at the bottom of this file that goes
red the day the thing it waits for arrives.

The distinction L1 rests on, because it is easy to lose: `assert_priced_from_
the_past` **deletes** future rows, and deletion changes the frame's shape, so a
model that legitimately reads a length or groups over all athletes can differ
honestly. Poisoning preserves shape and identity and is the stricter question.
Both are run.
"""

from __future__ import annotations

import ast
import importlib.util
import inspect
import json
import sys
from dataclasses import fields
from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab.models import player_rates as PR
from cbb_betting_lab.models.player_shapes import load_player_shapes
from cbb_betting_lab.reports import price_backtest as PB

REPO = Path(__file__).resolve().parents[1]
MODULE = REPO / "src" / "cbb_betting_lab" / "models" / "player_rates.py"
SHAPES = REPO / "data" / "processed" / "cbb_player_shapes.json"

PRICED_SEASON = 2024
DAY = "2024-01-15"

#: Every constant the estimator reads, and what moving it must move. A constant
#: that is read but hard-coded would pass every provenance test in this
#: repository and still be a number nobody can date.
READ_CONSTANTS: tuple[str, ...] = (
    "minutes_half_life",
    "minutes_pmf",
    "role_prior",
    "rate_shrinkage_k",
    "value_pmf",
    "value_mix_shrinkage_events",
    "dnp_base_rate",
)


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------


def _shapes(path: Path | str = SHAPES):
    return load_player_shapes(path, priced_season=PRICED_SEASON)


def _row(
    day: str,
    *,
    game_id: int,
    athlete_id: float,
    name: str,
    team_id: int = 55,
    minutes: float = 26.0,
    did_not_play: object = "False",
    season: int = PRICED_SEASON,
    points: float = 13.0,
    rebounds: float = 5.0,
    assists: float = 4.0,
    steals: float = 1.0,
    turnovers: float = 2.0,
    fgm: float = 5.0,
    threes: float = 1.0,
    ftm: float = 2.0,
) -> dict:
    return {
        "slate_date": day,
        "season": season,
        "game_id": game_id,
        "athlete_id": athlete_id,
        "athlete_display_name": name,
        "team_id": team_id,
        "opponent_id": 66,
        "home_away": "home",
        "did_not_play": did_not_play,
        "starter": True,
        "minutes": minutes,
        "points": points,
        "rebounds": rebounds,
        "assists": assists,
        "steals": steals,
        "turnovers": turnovers,
        "field_goals_made": fgm,
        "three_point_field_goals_made": threes,
        "free_throws_made": ftm,
    }


#: Three athletes with genuinely different banks, so a permutation of identity
#: has something to move. A pair whose banks are identical is legitimately
#: invariant and would make L5 unfalsifiable.
_ROSTER = (
    (4001.0, "Sean Bairstow", 31.0, 18.0, 4.0, 5.0, 7.0, 3.0),
    (4002.0, "Blake Hinson", 22.0, 9.0, 8.0, 1.0, 3.0, 1.0),
    (4003.0, "Reese Dixon-Waters", 15.0, 6.0, 2.0, 6.0, 2.0, 2.0),
)


def _settled() -> pd.DataFrame:
    """The uncut settlement table: prior games, tonight's game, and a debutant.

    Tonight's rows are the future. They are here so a cut can be shown to
    remove them and a poisoning can be shown not to reach through one.
    """
    rows: list[dict] = []
    for athlete, name, minutes, points, rebounds, assists, fgm, threes in _ROSTER:
        for day in range(1, 9):
            # Minutes move game to game, which is what gives the half-life
            # something to weigh: on a flat sequence every half-life returns the
            # same number and `minutes_half_life` could be hard-coded unnoticed.
            rows.append(
                _row(
                    f"2024-01-{day:02d}",
                    game_id=100 + day,
                    athlete_id=athlete,
                    name=name,
                    minutes=minutes + 6.0 * ((day % 3) - 1),
                    points=points,
                    rebounds=rebounds,
                    assists=assists,
                    fgm=fgm,
                    threes=threes,
                )
            )
        rows.append(
            _row(DAY, game_id=999, athlete_id=athlete, name=name, minutes=minutes)
        )
    rows.append(
        _row(DAY, game_id=999, athlete_id=4099.0, name="Brand New", minutes=20.0)
    )
    return pd.DataFrame(rows)


def _prices(*subjects: str) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "event_id": "e1",
                "market": "player_points",
                "player": subject,
                "selection": "over",
                "line": 14.5,
                "book": "dk",
                "game_id": 999,
                "season": PRICED_SEASON,
                "slate_date": DAY,
                "home_team": 55,
                "away_team": 66,
            }
            for subject in subjects
        ]
    )


def _board() -> pd.DataFrame:
    return _prices(*[name for _, name, *_ in _ROSTER], "Brand New")


def _price(frame: pd.DataFrame, *, day: str = DAY, shapes=None) -> PR.PlayerSlate:
    return PR.player_projections_for(
        day=day,
        player_history=PB.history_before(frame, day),
        prices=_board(),
        shapes=shapes if shapes is not None else _shapes(),
    )


def _record(projection: PR.PlayerProjection) -> dict:
    return {f.name: getattr(projection, f.name) for f in fields(projection)}


def _all_records(slate: PR.PlayerSlate) -> dict:
    return {
        (event, athlete): _record(projection)
        for event, by_athlete in slate.projections.items()
        for athlete, projection in by_athlete.items()
    }


def _poison(frame: pd.DataFrame, *, day: str) -> pd.DataFrame:
    """Every row dated on or after `day`, made absurd, shape and identity kept.

    Minutes to 40, points to 50, `did_not_play` to false — design 11's own
    corruption. It is deliberately not a deletion: deletion changes the frame's
    shape, and a model that reads a length or groups over all athletes can then
    differ honestly. Poisoning changes only what the numbers say.
    """
    out = frame.copy()
    future = out["slate_date"].astype(str) >= str(day)
    assert future.any(), "nothing to poison; the fixture has no future"
    out.loc[future, "minutes"] = 40.0
    out.loc[future, "points"] = 50.0
    out.loc[future, "rebounds"] = 25.0
    out.loc[future, "assists"] = 25.0
    out.loc[future, "did_not_play"] = "False"
    return out


# --------------------------------------------------------------------------
# L1 -- the poisoned future
# --------------------------------------------------------------------------


def test_a_poisoned_future_does_not_move_one_projection() -> None:
    """Corrupt every row from the day onward; every field of every record holds.

    Bit-identical, field by field, with no tolerance: `projected_minutes`, the
    46-long lattice, the seven rates, the seven credibility weights, the value
    mix, the resolution route, the priceable set and the stamp. The projection
    is the sole input to a probability, so nothing is lost by comparing it
    rather than a price.

    It tests R1a for free. The poisoning cannot move `resolution_route` or the
    priceable set unless the model is reading tonight's roster, and the
    debutant in the fixture plays only tonight — so a resolver that reached him
    would both resolve a name it must refuse and change a census bucket.
    """
    settled = _settled()
    clean = _price(settled)
    poisoned = _price(_poison(settled, day=DAY))

    assert _all_records(clean) == _all_records(poisoned)
    assert clean.resolved == poisoned.resolved
    assert clean.name_refusals == poisoned.name_refusals
    assert clean.resolution_census == poisoned.resolution_census
    assert clean.priced_through == poisoned.priced_through == "2024-01-08"

    # The fixture actually has a future, the poison actually changed it, and
    # the debutant is actually refused -- so none of the above is vacuous.
    assert len(PB.history_before(settled, DAY)) < len(settled)
    assert not settled.equals(_poison(settled, day=DAY))
    assert clean.name_refusals == {("e1", "Brand New"): PR.R1A_TONIGHT_ONLY}
    assert len(clean.resolved) == 3


def test_deleting_the_future_and_poisoning_it_are_different_questions() -> None:
    """Both are run, because neither implies the other.

    Deletion is what `assert_priced_from_the_past` does and it changes the
    frame's shape; poisoning preserves shape and identity. A model that read a
    row count would survive the poison and fail the deletion; a model that read
    a value would survive nothing. This asserts the two frames really are
    different objects with different contents and that the answer is the same
    under both.
    """
    settled = _settled()
    poisoned = _poison(settled, day=DAY)
    deleted = settled[settled["slate_date"].astype(str) < DAY]

    assert len(poisoned) == len(settled) != len(deleted)
    baseline = _all_records(_price(settled))
    assert _all_records(_price(poisoned)) == baseline
    assert _all_records(_price(deleted)) == baseline


# --------------------------------------------------------------------------
# L2 -- the stamp
# --------------------------------------------------------------------------


def test_the_stamp_is_what_the_pricer_was_allowed_to_see() -> None:
    """The frame's maximum day, on every projection, strictly earlier than the day.

    Design 2 says "the max slate_date this projection actually read", and read
    literally that is the player's own bank maximum — which would make L2's
    assertion (pricer-reported equals harness cut) fail for every player whose
    last game was a week ago. `price_backtest._stamp_series` settles it in its
    own words: *the stamp describes what the pricer was ALLOWED to see, not
    what it chose to read.* This asserts that reading, including the part that
    makes it checkable: the same value on every projection.
    """
    settled = _settled()
    cut = PB.history_before(settled, DAY)
    slate = _price(settled)

    expected = PB.latest_day(cut)
    assert expected == "2024-01-08" < DAY
    assert slate.priced_through == expected
    stamps = {
        projection.priced_through
        for by_athlete in slate.projections.values()
        for projection in by_athlete.values()
    }
    assert stamps == {expected}, (
        "the stamp differs between projections, so it is the athlete's own last "
        "game rather than the frame the pricer was handed"
    )

    # An athlete whose own last game is earlier than the frame's maximum still
    # carries the frame's stamp -- which is the case the literal reading breaks.
    thin = settled[
        ~(
            (settled["athlete_id"] == 4003.0)
            & (settled["slate_date"].astype(str) >= "2024-01-05")
        )
    ]
    slate = _price(thin)
    assert slate.projections["e1"][4003].priced_through == PB.latest_day(
        PB.history_before(thin, DAY)
    )


def test_an_empty_frame_stamps_nothing_rather_than_today() -> None:
    """`""`, not the day, and it is the one value a leaking pricer would want.

    `assert_walk_forward` exempts the empty stamp, so a model that read the
    settlement table and reported nothing would be certified. That is why
    `models/slate.py` raises when a populated player half carries an empty
    stamp: the two halves of the check live on either side of this line.
    """
    empty = _settled().iloc[:0]
    slate = PR.player_projections_for(
        day=DAY, player_history=empty, prices=_board(), shapes=_shapes()
    )
    assert slate.priced_through == ""
    assert slate.projections == {}


# --------------------------------------------------------------------------
# L3 -- the frame the estimator reads
# --------------------------------------------------------------------------


def test_the_estimator_opens_no_file_and_holds_no_frame() -> None:
    """The rule the whole build rests on, asserted over the module's own tree.

    A `read_csv` here would reach the settlement table — 1,493,589 rows, of
    which 404,489 are dated after the season being priced — and
    `config.PROCESSED_DIR` is an ABSOLUTE path, which is the route the
    walk-forward guard has written down as open (gap 6 of nine): an absolute
    read is not caught by `assert_priced_from_the_past` at all. So the
    assertion is not "it does not leak", it is "it cannot": the module names no
    reader, no path and no config, and declares no module-level frame.
    """
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))

    forbidden = {
        "read_csv", "read_parquet", "read_json", "read_table", "open",
        "read_text", "read_bytes", "glob", "rglob",
    }
    called = {
        node.func.attr if isinstance(node.func, ast.Attribute) else node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, (ast.Attribute, ast.Name))
    }
    assert not called & forbidden, sorted(called & forbidden)

    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
            imported.update(alias.name for alias in node.names)
    for name in ("pathlib", "Path", "cbb_betting_lab.config", "config"):
        assert name not in imported, f"the estimator names {name!r}"
    assert not any("fit_player_model" in name for name in imported), (
        "the fitter reads the whole settlement table and no module under src/ "
        "may name it"
    )

    # Module-level names, and whether anything ever writes to one. The
    # vocabulary tables (`SETTLEMENT_COLUMN`, `MARKET_COMPONENTS`) are dicts and
    # are not memos; what makes a memo is that it is written to at run time, so
    # that is what is asserted rather than the container's type.
    module_level = {
        target.id
        for node in tree.body
        if isinstance(node, (ast.Assign, ast.AnnAssign))
        for target in (node.targets if isinstance(node, ast.Assign) else [node.target])
        if isinstance(target, ast.Name)
    }
    written: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Assign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id in module_level
                ):
                    written.append(target.value.id)
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id in module_level
            and node.func.attr in {"setdefault", "update", "pop", "clear", "append", "add"}
        ):
            written.append(node.func.value.id)
    assert not written, (
        f"module-level state written to at run time: {sorted(set(written))}. A "
        "memo of a frame, a projection or a distribution makes the "
        "poisoned-future test pass by never recomputing anything -- a detector "
        "that cannot fire."
    )

    built_by_pandas = [
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call)
        for target in node.targets
        if isinstance(target, ast.Name)
        and isinstance(node.value.func, ast.Attribute)
        and isinstance(node.value.func.value, ast.Name)
        and node.value.func.value.id in {"pd", "np"}
    ]
    assert not built_by_pandas, f"module-level frames or arrays: {built_by_pandas}"

    decorators = {
        node.attr if isinstance(node, ast.Attribute) else getattr(node, "id", "")
        for definition in ast.walk(tree)
        if isinstance(definition, (ast.FunctionDef, ast.AsyncFunctionDef))
        for node in definition.decorator_list
    }
    assert not decorators & {"lru_cache", "cache", "cached_property"}, sorted(decorators)


def test_the_frame_the_estimator_reads_is_not_the_settlement_table() -> None:
    """A different object, strictly fewer rows, and a maximum before the day.

    `is not` alone is weak — a boolean mask always returns a new object — so
    the row count is asserted too, against a table that is known to hold rows
    dated on the day being priced.
    """
    settled = _settled()
    cut = PB.history_before(settled, DAY)
    assert cut is not settled
    assert len(cut) < len(settled)
    assert PB.latest_day(cut) < DAY
    assert (settled["slate_date"].astype(str) >= DAY).sum() == 4

    with pytest.raises(PR.PlayerRatesError) as raised:
        PR.player_projections_for(
            day=DAY, player_history=settled, prices=_board(), shapes=_shapes()
        )
    assert "4 row(s)" in str(raised.value)


# --------------------------------------------------------------------------
# L4 -- constant provenance
# --------------------------------------------------------------------------


def test_no_numeric_literal_stands_in_for_a_fitted_constant() -> None:
    """Every fitted number is fetched, never written down here.

    The undated-lookup-table case is what design L4 was written for: a role
    prior or a residual table refreshed in place carries no window, and
    afterwards nothing can tell you what it saw. A copy of one inside a pricer
    is the same failure with an extra step, so this asserts that no value the
    frozen file carries — to six decimal places — appears as a literal in the
    module.
    """
    document = json.loads(SHAPES.read_text(encoding="utf-8"))

    def _numbers(value: object, into: set[float]) -> set[float]:
        if isinstance(value, bool):
            return into
        if isinstance(value, (int, float)):
            into.add(round(float(value), 6))
        elif isinstance(value, dict):
            for item in value.values():
                _numbers(item, into)
        elif isinstance(value, list):
            for item in value:
                _numbers(item, into)
        return into

    fitted: set[float] = set()
    for payload in document["constants"].values():
        _numbers(payload["value"], fitted)

    # The `declared` block is the one place this module is ALLOWED to carry a
    # copy, because it is held against the file by a passing assertion that
    # goes red the day the two drift. Everything else must be fetched.
    fitted -= _numbers(document["declared"], set())
    # `minutes_half_life` is 4.0 and `min_prior_games` is 4: the two collide as
    # numbers and are different quantities. The half-life is covered instead by
    # `test_moving_a_constant_moves_the_projection`, which proves it is read.
    fitted -= {round(float(v), 6) for v in (0.0, 1.0, 2.0, 3.0, 4.0)}

    literals = {
        round(float(node.value), 6)
        for node in ast.walk(ast.parse(MODULE.read_text(encoding="utf-8")))
        if isinstance(node, ast.Constant)
        and isinstance(node.value, (int, float))
        and not isinstance(node.value, bool)
    }
    collisions = sorted(literals & fitted)
    assert not collisions, (
        f"these fitted values appear as literals in the estimator: "
        f"{collisions}. A constant written down here carries no fit window."
    )


@pytest.mark.parametrize("constant", READ_CONSTANTS)
def test_moving_a_constant_moves_the_projection(constant: str, tmp_path: Path) -> None:
    """Each constant is READ. A hard-coded copy would survive the test above.

    The check above says no fitted value appears as a literal; this says each
    one is actually consulted, by moving it and demanding the answer move.
    `dnp_base_rate` is the exception and it is the point of the exception: it
    must move the stored diagnostic and nothing else, because it is never
    multiplied into a price.
    """
    document = json.loads(SHAPES.read_text(encoding="utf-8"))
    value = document["constants"][constant]["value"]
    if constant == "minutes_half_life":
        document["constants"][constant]["value"] = 40.0
    elif constant == "minutes_pmf":
        document["constants"][constant]["value"]["pmf"] = [
            [1.0 / 45] * 45 for _ in value["pmf"]
        ]
    elif constant in ("role_prior", "rate_shrinkage_k"):
        document["constants"][constant]["value"] = {
            stat: ([0.5] * 9 if constant == "role_prior" else 5000.0)
            for stat in PR.STAT_KEYS
        }
    elif constant == "value_pmf":
        document["constants"][constant]["value"] = [0.2, 0.2, 0.6]
    elif constant == "value_mix_shrinkage_events":
        document["constants"][constant]["value"] = 100000.0
    else:
        document["constants"][constant]["value"] = [0.99] * 9

    path = tmp_path / f"{constant}.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    moved = _price(_settled(), shapes=_shapes(path))
    baseline = _price(_settled())

    if constant == "dnp_base_rate":
        assert {p["dnp_probability"] for p in _all_records(moved).values()} == {0.99}
        for key, record in _all_records(moved).items():
            other = _all_records(baseline)[key]
            for name in ("minutes_pmf", "rates", "prior_weight", "value_pmf"):
                assert record[name] == other[name], name
        return
    assert _all_records(moved) != _all_records(baseline), (
        f"moving {constant} moved nothing, so the estimator is not reading it"
    )


def test_no_construction_path_builds_a_projection_from_an_unchecked_shapes_file() -> None:
    """The season is always named by the caller, and never by this module.

    `load_player_shapes` is the only way to get a `PlayerShapes`, and it takes
    `priced_season` keyword-only and without a default, so an instance existing
    IS the evidence the guard ran. This asserts the estimator never calls it —
    which would let it choose its own season — and that `shapes` has no default
    anywhere it is taken.
    """
    tree = ast.parse(MODULE.read_text(encoding="utf-8"))
    called = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "load_player_shapes" not in called

    for function in (PR.player_projections_for, PR.projection_for, PR.minutes_lattice):
        parameter = inspect.signature(function).parameters["shapes"]
        assert parameter.default is inspect.Parameter.empty, function.__name__
        assert parameter.kind is inspect.Parameter.KEYWORD_ONLY, function.__name__

    with pytest.raises(Exception):
        load_player_shapes(SHAPES, priced_season=2022)


# --------------------------------------------------------------------------
# L5 -- identity sensitivity
# --------------------------------------------------------------------------


def test_permuting_identity_within_a_game_moves_the_projection() -> None:
    """A role table wearing a name passes L1 through L4 and fails here.

    Identity enters this model only through the rate and minutes bank, so a
    rates-level test cannot be masked by a downstream nonlinearity — which
    makes here the right place for it rather than the probability layer.

    Not asserted per pair: two priceable athletes in the same bucket both fully
    shrunk to the same role prior are legitimately identical. Asserted as a
    fraction over the pairs whose prior banks differ, and the fraction is
    printed.
    """
    settled = _settled()
    baseline = _price(settled)

    names = {athlete: name for athlete, name, *_ in _ROSTER}
    rotated = dict(zip(names, list(names.values())[1:] + list(names.values())[:1]))
    permuted = settled.copy()
    permuted["athlete_display_name"] = [
        rotated.get(athlete, name)
        for athlete, name in zip(permuted["athlete_id"], permuted["athlete_display_name"])
    ]
    moved = _price(permuted)

    def _by_spelling(slate: PR.PlayerSlate) -> dict:
        return {
            spelling: (
                slate.projections[event][athlete].rates,
                slate.projections[event][athlete].projected_minutes,
            )
            for (event, spelling), athlete in slate.resolved.items()
        }

    before, after = _by_spelling(baseline), _by_spelling(moved)
    assert set(before) == set(after) and len(before) == 3
    banks = {
        record["prior_minutes"] for record in _all_records(baseline).values()
    }
    assert len(banks) == 3, "the three athletes must carry three different banks"

    differing = sum(1 for spelling in before if before[spelling] != after[spelling])
    print(f"{differing} of {len(before)} subjects moved when identity was permuted")
    assert differing == len(before), (
        "permuting which athlete each spelling reaches left the projections "
        "unchanged, so the model is a role table wearing a name"
    )


# --------------------------------------------------------------------------
# L8 -- the lag test, mechanical half
# --------------------------------------------------------------------------


def test_the_same_day_cut_a_day_earlier_runs_and_differs() -> None:
    """Both cuts complete, the earlier stamps are strictly earlier, and they differ.

    A model identical under both cuts is ignoring the most recent day. The
    *direction* half of L8 — "small and in the direction of slightly worse" —
    is a scored comparison against realised outcomes: it needs the distribution
    engine, and its output is a measured number this build may not print. It is
    refused below rather than approximated here.
    """
    settled = _settled()
    today = _price(settled, day=DAY)
    yesterday = PR.player_projections_for(
        day="2024-01-08",
        player_history=PB.history_before(settled, "2024-01-08"),
        prices=_board(),
        shapes=_shapes(),
    )

    assert today.projections and yesterday.projections
    assert yesterday.priced_through == "2024-01-07" < today.priced_through
    for by_athlete in yesterday.projections.values():
        for projection in by_athlete.values():
            assert projection.priced_through < "2024-01-08"
    assert _all_records(today) != _all_records(yesterday)


# --------------------------------------------------------------------------
# L9 -- the filter audit, at both levels
# --------------------------------------------------------------------------


def test_the_estimator_never_screens_on_the_game_it_is_pricing() -> None:
    """R2 and R3 read the prior bank only, and this proves it one level down.

    The fitter's own version of this sets every realised column to 999.0 and
    asserts `priced_population`'s index is unchanged. This is the same trick at
    price time: corrupt every realised column of the game being priced and the
    priceable set must not move, because the screens are four prior
    appearances, sixty prior minutes and eight PROJECTED minutes — and
    projected minutes are projected, never realised.
    """
    settled = _settled()
    corrupted = settled.copy()
    tonight = corrupted["slate_date"].astype(str) == DAY
    for column in (
        "minutes", "points", "rebounds", "assists", "steals", "turnovers",
        "field_goals_made", "three_point_field_goals_made", "free_throws_made",
    ):
        corrupted.loc[tonight, column] = 999.0

    before = _price(settled)
    after = _price(corrupted)
    assert {
        (event, athlete, projection.priceable, projection.unpriceable_reason)
        for event, by_athlete in before.projections.items()
        for athlete, projection in by_athlete.items()
    } == {
        (event, athlete, projection.priceable, projection.unpriceable_reason)
        for event, by_athlete in after.projections.items()
        for athlete, projection in by_athlete.items()
    }

    # And the bucket the role prior is read at is the projected one.
    projection = before.projections["e1"][4001]
    assert projection.minutes_bucket == PR.role_prior_bucket(
        projection.projected_minutes, bucket_edges=PR.BUCKET_EDGES
    )


def test_a_player_season_is_selected_on_prior_season_evidence_only() -> None:
    """`PRIOR_SEASON_MIN_GAMES = 5`, applied on season - 1, and held by nothing.

    Measured before this commit: `grep -rn prior_season tests/` returned
    nothing. The constant is applied at `fit_player_model.dispersion_population`
    and declared in the frozen file, and no test in this repository held either.
    Selecting on ">= N played games in the target season" would condition the
    estimate on surviving the season it predicts, which is the same mistake as
    screening on realised minutes one level up.
    """
    spec = importlib.util.spec_from_file_location(
        "fit_player_model", REPO / "scripts" / "fit_player_model.py"
    )
    assert spec and spec.loader
    fitter = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = fitter
    spec.loader.exec_module(fitter)

    declared = json.loads(SHAPES.read_text(encoding="utf-8"))["declared"]
    assert fitter.PRIOR_SEASON_MIN_GAMES == declared["prior_season_min_games"] == 5
    assert PR.PRIOR_SEASON_MIN_GAMES == 5

    trailing = pd.DataFrame(
        {
            "played": [True, True, True],
            "season": [2024, 2024, 2024],
            "athlete_id": [1.0, 2.0, 3.0],
            "minutes": [20.0, 20.0, 20.0],
        }
    )
    counts = {
        (2023, 1.0): 5,   # enough last season -> admitted
        (2023, 2.0): 4,   # too few last season -> dropped
        (2024, 3.0): 40,  # plenty THIS season and no prior one -> admitted anyway
    }
    kept = fitter.dispersion_population(trailing, counts)
    assert sorted(kept["athlete_id"]) == [1.0, 3.0], (
        "the selection read the target season rather than the prior one"
    )
    assert list(kept["has_prior_season"]) == [True, False]


# --------------------------------------------------------------------------
# What is refused for this commit, and what it waits on
# --------------------------------------------------------------------------


def test_the_leak_tests_this_commit_cannot_carry_are_the_ones_written_down() -> None:
    """L6, L7, L8's direction and L9(d), each with what it waits for.

    1. **L6, the negative control.** The identity-blind role-prior control
       priced over the whole store, its mean log loss printed BEFORE the
       headline. It is ledger entries H31 to H33 and it needs the distribution
       engine, the de-vig and the grading path. What this commit can already
       build is the control PROJECTION — `shrink_rate` with `k` large enough
       that `w` is nil is exactly it — so the control is not invented later by
       somebody who has already seen the headline.
    2. **L7, the seeded leak with a calibrated floor.** Realised outcomes
       injected into 1%, 3% and 10% of cells, recording the contamination at
       which the calibration diagnostic separates from noise. It needs settled
       outcomes and the calibration diagnostic, and its output is a measured
       number this build may not state.
    3. **L8's direction half.** "Small and in the direction of slightly worse"
       is a scored comparison; the mechanical half is above.
    4. **L9(d).** "The fitted dispersions match the unfiltered constants to 1%"
       cannot be written: the frozen file records no unfiltered counterpart for
       any dispersion constant. It needs a fitter change — an
       `unfiltered_value` beside each dispersion — and therefore a refit.
    """
    models = REPO / "src" / "cbb_betting_lab" / "models"
    assert not (models / "player_distributions.py").exists(), (
        "the distribution engine exists, so L6, L7 and L8's direction half can "
        "now be written. Write them; do not delete this."
    )

    # The control projection is constructible today, off the public helpers.
    rate, weight = PR.shrink_rate(
        bank_stat=500.0, prior_minutes=200.0, prior_rate=0.31, k=1e12
    )
    assert weight == pytest.approx(0.0, abs=1e-9)
    assert rate == pytest.approx(0.31, abs=1e-9), (
        "the identity-blind control is the role prior at the projected-minutes "
        "bucket, and it is buildable from this module's public helpers"
    )

    document = json.loads(SHAPES.read_text(encoding="utf-8"))
    for name, payload in document["constants"].items():
        assert "unfiltered_value" not in payload, (
            f"{name} now records an unfiltered counterpart, so L9(d) can be "
            "written. Write it."
        )
    assert "conditional_dispersion" in document["constants"]
    assert "unfiltered" not in SHAPES.read_text(encoding="utf-8")


def test_the_output_guard_still_has_no_production_caller() -> None:
    """`assert_priced_from_the_past` is referenced only from tests, still.

    Recorded rather than fixed: wiring it into a run costs a second price of a
    sampled day, and that is a decision about run time rather than about the
    estimator. `assert_walk_forward`, which the backtest DOES call, was
    extended in the seam commit to check every column ending in
    `_priced_through`, so the player stamp is checked on every production run
    even while this one is not.
    """
    callers: set[str] = set()
    for directory in ("src", "scripts"):
        for path in sorted((REPO / directory).rglob("*.py")):
            if path.name == "price_backtest.py":
                continue
            if "assert_priced_from_the_past" in path.read_text(encoding="utf-8"):
                callers.add(str(path.relative_to(REPO)))
    assert not callers, (
        f"{sorted(callers)} now calls the output guard. Say so in the report: "
        "the two leak checks are no longer one production call apart."
    )
    assert "priced_through" in inspect.getsource(PB.assert_walk_forward)
