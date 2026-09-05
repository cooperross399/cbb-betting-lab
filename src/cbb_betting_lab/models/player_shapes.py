"""The frozen player-prop constants, and the guard that makes them safe to trust.

`scripts/fit_player_model.py` writes `data/processed/cbb_player_shapes.json` and
never runs again. This module is the only way to read it, and it exists for one
job that has nothing to do with parsing: **it refuses to hand a constant to a
price whose season the constant was fitted on.**

## Why a loader is the right place for that

The four constants in `models/distributions.py` are all fitted "2018-19 through
2024-25". This lab prices season 2024. Every price the team model has ever
produced was therefore made with a shape that had already seen the graded
season, and nothing anywhere failed -- because a shape leak does not move a
calibration plot the way an outcome leak does. It just makes the model slightly
right about the wrong thing, in a way that survives every check the lab owns.

A comment saying "fit on earlier seasons" cannot stop that. A constant that
carries its own window, and a loader that compares that window against the
season being priced before it returns anything, can. So every constant in the
frozen file records `fit_seasons`, `fitted_through` and `validation_season`, and
:func:`load_player_shapes` raises :class:`ProvenanceError` if any one of them
reaches the priced season -- or if any one of them fails to say.

## What the guard refuses, and why each rule is there

For a price on season `S`, a constant is refused when:

* `S` is one of its `fit_seasons`, or `S <= fitted_through`. The obvious case:
  the constant saw the season it is pricing.
* `S == validation_season`. Less obvious and just as important. The design's L4
  protects the validation season as well as the priced one, because a guard that
  only excludes the priced season blesses fitting on the holdout -- which is how
  the earlier attempt spent 2023 choosing a half-life by 0.08%. A constant
  validated on 2023 must not price 2023.
* it carries no window at all, or an inconsistent one (`fitted_through` that is
  not the last of `fit_seasons`). An undated lookup table is the failure mode
  L4 was written for: the role prior and the minutes residual SD are exactly the
  sort of thing that gets refreshed in place with no window attached, and after
  that nothing can tell you what they saw.

There is no `strict=False`, no override argument and no environment variable.
A guard with a way round it is a comment.

## Markets the fit could not produce a constant for

The frozen file can record a constant as **unfittable** -- measured, found
unstable, and deliberately not invented. :meth:`PlayerShapes.refusal_for` gives
the model the full sentence to put on the refused market. That is the difference
between a market this lab has no opinion on and a market it priced on a number
nobody could stand behind, and the two must never look the same in a census.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

__all__ = [
    "PlayerShapes",
    "ProvenanceError",
    "ShapesFileError",
    "load_player_shapes",
    "DEFAULT_SHAPES_PATH",
]

DEFAULT_SHAPES_PATH = (
    Path(__file__).resolve().parents[3] / "data" / "processed" / "cbb_player_shapes.json"
)

#: Every constant must carry all three. A constant missing any one of them is
#: refused rather than assumed innocent -- see the module docstring on L4.
REQUIRED_PROVENANCE_FIELDS = ("fit_seasons", "fitted_through", "validation_season")


class ShapesFileError(ValueError):
    """The frozen file is missing, unreadable, or does not have the shape claimed."""


class ProvenanceError(ShapesFileError):
    """A constant's fit window reaches the season being priced.

    Deliberately a subclass of the file error rather than a warning: there is no
    degraded mode in which a leaked constant is better than no price.
    """


@dataclass(frozen=True)
class PlayerShapes:
    """Frozen constants that have been checked against the season being priced.

    Only ever built by :func:`load_player_shapes`, so an instance existing is
    itself the evidence that the guard ran and passed for `priced_season`.
    """

    path: Path
    priced_season: int
    fit_seasons: tuple[int, ...]
    fitted_through: int
    validation_season: int
    document: Mapping[str, Any]

    @property
    def constants(self) -> Mapping[str, Any]:
        return self.document["constants"]

    def value(self, name: str) -> Any:
        """The fitted value of one constant.

        Raises rather than returning a default if the constant was recorded
        unfittable: the caller has to decide to refuse the market, and a silent
        fallback is how an invented number reaches a price.
        """
        refusal = self.refusal_for(name)
        if refusal is not None:
            raise ShapesFileError(
                f"{name} was not fitted. {refusal} Ask `refusal_for` and refuse the "
                "market; do not substitute a value."
            )
        try:
            return self.constants[name]["value"]
        except KeyError as error:
            raise ShapesFileError(
                f"{self.path} carries no constant named {name!r}. The constants it "
                f"does carry are: {', '.join(sorted(self.constants))}."
            ) from error

    def held_out_value(self, name: str) -> Any:
        """What the same estimator produced on the held-out season.

        Present so a caller can print the pair. Never the value a price is made
        from -- the holdout is a check, and a model that quietly reaches for it
        has spent it.
        """
        return self.constants[name]["held_out_value"]

    def refusal_for(self, name: str) -> str | None:
        """The full-sentence reason a constant could not be fitted, or None.

        Keys in the file's `unfittable` block are either a constant name or
        `constant.market`, so a market-level refusal is found by either.
        """
        unfittable = self.document.get("unfittable") or {}
        entry = unfittable.get(name)
        if entry is None:
            return None
        return f"{entry.get('reason', '')} {entry.get('cost', '')}".strip()

    def unfittable(self) -> tuple[str, ...]:
        """Every constant, or constant-and-market, the fit refused to invent."""
        return tuple(sorted((self.document.get("unfittable") or {}).keys()))

    def disagreements(self) -> Mapping[str, str]:
        """Constants whose fitted and held-out values differ materially.

        Not an error. A caller that prints a constant should print this beside
        it, because a number that moves between two adjacent seasons is a
        different kind of number from one that does not.
        """
        return dict(self.document.get("disagreements") or {})


def _as_seasons(value: object, *, name: str, path: Path) -> tuple[int, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or not value:
        raise ProvenanceError(
            f"{path}: constant {name!r} records `fit_seasons` as {value!r}, which is "
            "not a non-empty list of seasons. A constant that cannot say what it was "
            "fitted on cannot be checked against the season being priced, and an "
            "undated lookup table is exactly the leak this guard exists to catch."
        )
    try:
        return tuple(int(season) for season in value)
    except (TypeError, ValueError) as error:
        raise ProvenanceError(
            f"{path}: constant {name!r} records `fit_seasons` as {value!r}, which does "
            "not read as seasons."
        ) from error


def _check_constant(name: str, payload: object, *, priced_season: int, path: Path) -> None:
    """Refuse this constant unless its window is strictly earlier than the price."""
    if not isinstance(payload, Mapping):
        raise ShapesFileError(f"{path}: constant {name!r} is not an object.")
    missing = [field for field in REQUIRED_PROVENANCE_FIELDS if payload.get(field) is None]
    if missing:
        raise ProvenanceError(
            f"{path}: constant {name!r} does not record {', '.join(missing)}. A "
            "constant with no fit window cannot be shown to be earlier than the "
            "season it is pricing, so it is refused rather than assumed innocent. "
            "This is the undated-lookup-table case: a role prior or a residual table "
            "refreshed in place carries no window and nothing afterwards can tell you "
            "what it saw."
        )

    fit_seasons = _as_seasons(payload["fit_seasons"], name=name, path=path)
    fitted_through = int(payload["fitted_through"])
    validation_season = int(payload["validation_season"])

    if fitted_through != max(fit_seasons):
        raise ProvenanceError(
            f"{path}: constant {name!r} records `fitted_through` {fitted_through} but "
            f"its latest fit season is {max(fit_seasons)}. The two disagree, so "
            "neither can be trusted to bound what this constant saw."
        )
    if validation_season in fit_seasons:
        raise ProvenanceError(
            f"{path}: constant {name!r} names season {validation_season} as its "
            "holdout and also fits on it. A holdout that is in the fit is not a "
            "holdout, and every held-out number this constant reports is in-sample."
        )

    if priced_season in fit_seasons or priced_season <= fitted_through:
        raise ProvenanceError(
            f"{path}: constant {name!r} was fitted on seasons "
            f"{list(fit_seasons)} and this is a price for season {priced_season}. A "
            "constant fitted on the season it prices is a constant the model could "
            "not have had at sixty minutes to tip. It does not move a calibration "
            "plot -- that is precisely why it has to be refused here, before a price "
            "exists, rather than looked for afterwards in a result."
        )
    if priced_season == validation_season:
        raise ProvenanceError(
            f"{path}: constant {name!r} holds out season {validation_season} and this "
            f"is a price for season {priced_season}. The holdout is protected as well "
            "as the fit: a guard that excludes only the fitted seasons blesses "
            "choosing a constant on the validation season and then pricing it, which "
            "spends the holdout twice."
        )


def load_player_shapes(
    path: Path | str = DEFAULT_SHAPES_PATH, *, priced_season: int
) -> PlayerShapes:
    """Read the frozen constants, or refuse because one of them saw `priced_season`.

    There is no non-refusing mode. Every caller must name the season it is about
    to price, because the question this function answers is not "can this file be
    parsed" but "may these numbers be used *here*".
    """
    path = Path(path)
    priced_season = int(priced_season)
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ShapesFileError(
            f"{path} does not exist. It is written by `scripts/fit_player_model.py`, "
            "which never runs at price time; run it once and commit the result."
        ) from error
    except json.JSONDecodeError as error:
        raise ShapesFileError(f"{path} is not readable as JSON: {error}") from error

    if not isinstance(document, Mapping):
        raise ShapesFileError(f"{path} is not a JSON object.")
    constants = document.get("constants")
    if not isinstance(constants, Mapping) or not constants:
        raise ShapesFileError(
            f"{path} carries no `constants` block. An empty shapes file is not a "
            "model with no opinions; it is a file that failed to be written."
        )

    for name, payload in constants.items():
        _check_constant(name, payload, priced_season=priced_season, path=path)

    fit_seasons = _as_seasons(document.get("fit_seasons"), name="<document>", path=path)
    _check_constant(
        "<document>",
        {
            "fit_seasons": list(fit_seasons),
            "fitted_through": document.get("fitted_through"),
            "validation_season": document.get("validation_season"),
        },
        priced_season=priced_season,
        path=path,
    )

    return PlayerShapes(
        path=path,
        priced_season=priced_season,
        fit_seasons=fit_seasons,
        fitted_through=int(document["fitted_through"]),
        validation_season=int(document["validation_season"]),
        document=document,
    )
