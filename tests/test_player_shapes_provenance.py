"""The guard that makes the frozen player constants safe to trust.

`data/processed/cbb_player_shapes.json` is fitted once, on seasons strictly
earlier than the one this lab prices, and then never refitted. Everything that
makes that claim worth anything is in `models.player_shapes.load_player_shapes`:
it compares each constant's recorded fit window against the season being priced
and raises before it returns.

This file is the test of that guard, and it is written the way a leak test has
to be written -- **from the leaking file inward**. The central case is not "the
real file loads"; it is *a shapes file claiming a window that includes 2024 must
refuse to load for a 2024 price*. A guard that has only ever been shown a clean
file is not a guard, it is a parser.

The reason it matters here rather than in general: `models/distributions.py`
carries four constants fitted "2018-19 through 2024-25" and this lab prices
season 2024. Every team price ever produced in this repository was made with a
shape that had already seen the graded season, and nothing failed -- a shape
leak does not move a calibration plot. So the only place it can be caught is
before the number is handed over.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from cbb_betting_lab.models import player_shapes as PS

REPO = Path(__file__).resolve().parents[1]
FROZEN = REPO / "data" / "processed" / "cbb_player_shapes.json"
PRICED_SEASON = 2024


def _constant(**overrides) -> dict:
    payload = {
        "value": 4.0,
        "held_out_value": 4.0,
        "fit_seasons": [2019, 2020, 2021, 2022],
        "fitted_through": 2022,
        "validation_season": 2023,
        "sample_size": 10,
        "held_out_sample_size": 10,
        "input_sha256": "0" * 64,
        "held_out_input_sha256": "0" * 64,
        "units": "games",
        "provenance": "declared",
        "note": "a fixture",
    }
    payload.update(overrides)
    return payload


def _document(constants: dict, **overrides) -> dict:
    document = {
        "schema_version": 1,
        "fit_seasons": [2019, 2020, 2021, 2022],
        "fitted_through": 2022,
        "validation_season": 2023,
        "constants": constants,
        "unfittable": {},
        "disagreements": {},
    }
    document.update(overrides)
    return document


def _write(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "cbb_player_shapes.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# The case the guard exists for
# --------------------------------------------------------------------------


def test_a_window_that_includes_the_priced_season_refuses_to_load(tmp_path: Path) -> None:
    """The central case. A constant that saw 2024 may not price 2024."""
    path = _write(
        tmp_path,
        _document(
            {
                "conditional_dispersion": _constant(
                    fit_seasons=[2021, 2022, 2023, 2024], fitted_through=2024, validation_season=2025
                )
            },
            fit_seasons=[2021, 2022, 2023, 2024],
            fitted_through=2024,
            validation_season=2025,
        ),
    )
    with pytest.raises(PS.ProvenanceError) as raised:
        PS.load_player_shapes(path, priced_season=PRICED_SEASON)
    message = str(raised.value)
    assert "conditional_dispersion" in message
    assert "2024" in message


def test_a_window_ending_at_the_priced_season_refuses_even_without_listing_it(
    tmp_path: Path,
) -> None:
    """`fitted_through` alone is enough to refuse.

    A file may list its fit seasons sparsely -- the seasons it happened to have
    rows for -- while `fitted_through` records how far the window reached. The
    guard reads both, so a window that *ends* at the priced season is refused
    even when the season is not in the list.
    """
    path = _write(
        tmp_path,
        _document(
            {"role_prior": _constant(fit_seasons=[2019, 2024], fitted_through=2024, validation_season=2018)},
            fit_seasons=[2019, 2024],
            fitted_through=2024,
            validation_season=2018,
        ),
    )
    with pytest.raises(PS.ProvenanceError):
        PS.load_player_shapes(path, priced_season=PRICED_SEASON)


def test_one_leaking_constant_among_clean_ones_still_refuses(tmp_path: Path) -> None:
    """The guard is not a majority vote. One bad window refuses the whole file."""
    path = _write(
        tmp_path,
        _document(
            {
                "minutes_half_life": _constant(),
                "role_prior": _constant(),
                "value_pmf": _constant(
                    fit_seasons=[2022, 2023, 2024], fitted_through=2024, validation_season=2025
                ),
                "residual_correlation": _constant(),
            }
        ),
    )
    with pytest.raises(PS.ProvenanceError) as raised:
        PS.load_player_shapes(path, priced_season=PRICED_SEASON)
    assert "value_pmf" in str(raised.value)


def test_the_validation_season_is_protected_as_well_as_the_priced_one(tmp_path: Path) -> None:
    """A constant validated on 2023 may not price 2023.

    The design's L4: a guard that excludes only the fitted seasons blesses
    choosing a constant on the holdout and then pricing that same season, which
    spends the holdout twice. The fit window here is entirely earlier than 2023,
    so only the validation rule can refuse this.
    """
    path = _write(tmp_path, _document({"minutes_half_life": _constant()}))
    with pytest.raises(PS.ProvenanceError) as raised:
        PS.load_player_shapes(path, priced_season=2023)
    assert "holds out season 2023" in str(raised.value)


def test_a_constant_with_no_window_refuses(tmp_path: Path) -> None:
    """The undated lookup table. Refused rather than assumed innocent."""
    payload = _constant()
    del payload["fit_seasons"]
    path = _write(tmp_path, _document({"role_prior": payload}))
    with pytest.raises(PS.ProvenanceError) as raised:
        PS.load_player_shapes(path, priced_season=PRICED_SEASON)
    assert "fit_seasons" in str(raised.value)


@pytest.mark.parametrize("field", ["fitted_through", "validation_season"])
def test_a_constant_missing_any_provenance_field_refuses(tmp_path: Path, field: str) -> None:
    payload = _constant()
    del payload[field]
    path = _write(tmp_path, _document({"minutes_pmf": payload}))
    with pytest.raises(PS.ProvenanceError) as raised:
        PS.load_player_shapes(path, priced_season=PRICED_SEASON)
    assert field in str(raised.value)


def test_a_window_that_contradicts_itself_refuses(tmp_path: Path) -> None:
    """`fitted_through` earlier than the latest fit season bounds nothing."""
    path = _write(
        tmp_path,
        _document(
            {"role_prior": _constant(fit_seasons=[2019, 2024], fitted_through=2019)},
        ),
    )
    with pytest.raises(PS.ProvenanceError) as raised:
        PS.load_player_shapes(path, priced_season=PRICED_SEASON)
    assert "disagree" in str(raised.value)


def test_a_holdout_that_is_inside_the_fit_refuses(tmp_path: Path) -> None:
    """A holdout that is in the fit is not a holdout."""
    path = _write(
        tmp_path,
        _document({"value_pmf": _constant(validation_season=2021)}),
    )
    with pytest.raises(PS.ProvenanceError) as raised:
        PS.load_player_shapes(path, priced_season=PRICED_SEASON)
    assert "not a holdout" in str(raised.value)


def test_a_document_level_window_reaching_the_priced_season_refuses(tmp_path: Path) -> None:
    """Every constant clean, the file's own header not. Still refused.

    The header is what a reader quotes. A file whose constants say 2022 and
    whose header says 2024 is a file somebody edited by hand, and the guard has
    no way to know which half is the lie.
    """
    path = _write(
        tmp_path,
        _document(
            {"minutes_half_life": _constant()},
            fit_seasons=[2019, 2024],
            fitted_through=2024,
        ),
    )
    with pytest.raises(PS.ProvenanceError):
        PS.load_player_shapes(path, priced_season=PRICED_SEASON)


def test_an_empty_constants_block_refuses(tmp_path: Path) -> None:
    """A file with nothing in it is a failed write, not a model with no opinions."""
    path = _write(tmp_path, _document({}))
    with pytest.raises(PS.ShapesFileError):
        PS.load_player_shapes(path, priced_season=PRICED_SEASON)


# --------------------------------------------------------------------------
# The file this branch actually froze
# --------------------------------------------------------------------------


def test_the_frozen_file_loads_for_the_season_this_lab_prices() -> None:
    shapes = PS.load_player_shapes(FROZEN, priced_season=PRICED_SEASON)
    assert shapes.fitted_through < PRICED_SEASON
    assert shapes.validation_season != PRICED_SEASON
    assert set(shapes.fit_seasons) == {2019, 2020, 2021, 2022}


@pytest.mark.parametrize("season", [2019, 2020, 2021, 2022, 2023])
def test_the_frozen_file_refuses_every_season_it_was_fitted_or_validated_on(season: int) -> None:
    with pytest.raises(PS.ProvenanceError):
        PS.load_player_shapes(FROZEN, priced_season=season)


def test_no_constant_in_the_frozen_file_ever_read_the_priced_season() -> None:
    """Belt and braces, read straight off the file rather than through the loader."""
    document = json.loads(FROZEN.read_text(encoding="utf-8"))
    for name, payload in document["constants"].items():
        seasons = payload["fit_seasons"]
        assert max(seasons) < PRICED_SEASON, f"{name} was fitted through {max(seasons)}"
        assert payload["validation_season"] < PRICED_SEASON, name
        assert PRICED_SEASON not in seasons, name


def test_every_constant_carries_a_sample_size_and_a_sha_of_its_own_rows() -> None:
    """A constant with no sample and no input hash cannot be checked by anyone later."""
    document = json.loads(FROZEN.read_text(encoding="utf-8"))
    for name, payload in document["constants"].items():
        assert payload["sample_size"] > 0, name
        assert payload["held_out_sample_size"] > 0, name
        assert len(payload["input_sha256"]) == 64, name
        assert len(payload["held_out_input_sha256"]) == 64, name
        assert payload["input_sha256"] != payload["held_out_input_sha256"], (
            f"{name} claims the same input rows for its fitted and held-out values; "
            "one of them is not what it says it is."
        )


def test_every_constant_reports_a_held_out_value_beside_its_fitted_one() -> None:
    document = json.loads(FROZEN.read_text(encoding="utf-8"))
    for name, payload in document["constants"].items():
        assert payload["held_out_value"] is not None, name
        assert "agreement" in payload, name


def test_the_frozen_file_is_strict_json_with_no_nan_tokens() -> None:
    """`json.dumps` writes a bare `NaN` by default, which is not JSON.

    A constant that could not be measured in a bucket is stored as `null` -- an
    absence a reader in any language can refuse on, rather than a token that
    parses in Python and nowhere else.
    """
    text = FROZEN.read_text(encoding="utf-8")
    assert "NaN" not in text
    assert "Infinity" not in text
    json.loads(text)  # strict by default: raises on NaN


def test_disagreements_are_published_rather_than_smoothed() -> None:
    """Where fitted and held out differ materially the file says so, by name."""
    shapes = PS.load_player_shapes(FROZEN, priced_season=PRICED_SEASON)
    document = json.loads(FROZEN.read_text(encoding="utf-8"))
    flagged = {name for name, payload in document["constants"].items() if payload["disagrees"]}
    assert set(shapes.disagreements()) == flagged
    for name in flagged:
        assert document["constants"][name]["agreement"].startswith("fitted ")


def test_an_unfittable_constant_refuses_to_produce_a_value(tmp_path: Path) -> None:
    """The whole point of recording something unfittable rather than inventing it.

    `value()` must not fall back to anything. The caller is meant to read
    `refusal_for` and refuse the market, so that a market nobody could fit and a
    market priced on a made-up number never look the same in a census.
    """
    path = _write(
        tmp_path,
        _document(
            {"rate_shrinkage_k": _constant()},
            unfittable={
                "rate_shrinkage_k": {
                    "reason": "k is not stable across evidence banks.",
                    "cost": "every market that reads it is refused for the season.",
                }
            },
        ),
    )
    shapes = PS.load_player_shapes(path, priced_season=PRICED_SEASON)
    assert "rate_shrinkage_k" in shapes.unfittable()
    assert "not stable" in (shapes.refusal_for("rate_shrinkage_k") or "")
    with pytest.raises(PS.ShapesFileError) as raised:
        shapes.value("rate_shrinkage_k")
    assert "do not substitute a value" in str(raised.value)


def test_a_missing_file_says_what_writes_it(tmp_path: Path) -> None:
    with pytest.raises(PS.ShapesFileError) as raised:
        PS.load_player_shapes(tmp_path / "nothing.json", priced_season=PRICED_SEASON)
    assert "fit_player_model.py" in str(raised.value)


# --------------------------------------------------------------------------
# The fitter cannot be reached from a price
# --------------------------------------------------------------------------


def test_the_fit_script_is_not_importable_from_the_model_package() -> None:
    """Nothing under `src/` may import the fitter.

    `scripts/fit_player_model.py` reads the settlement table whole -- every
    realised stat line of every fit season. That frame must not be reachable
    from anything a pricer imports, and the cheapest durable way to say so is
    that no module under `src/` names it.
    """
    offenders: list[str] = []
    for path in sorted((REPO / "src").rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""] + [alias.name for alias in node.names]
            if any("fit_player_model" in name for name in names):
                offenders.append(f"{path.relative_to(REPO)}:{node.lineno}")
    assert not offenders, (
        "these modules import the fitter, which reads the whole settlement table: "
        + ", ".join(offenders)
    )


def test_the_loader_needs_a_season_and_offers_no_way_round_the_guard() -> None:
    """`priced_season` is keyword-only and required; there is no override.

    A guard with a `strict=False` is a comment. This asserts the signature
    itself, so adding an escape hatch turns this red rather than quietly
    widening what may be priced.
    """
    import inspect

    signature = inspect.signature(PS.load_player_shapes)
    season = signature.parameters["priced_season"]
    assert season.kind is inspect.Parameter.KEYWORD_ONLY
    assert season.default is inspect.Parameter.empty
    assert set(signature.parameters) == {"path", "priced_season"}
