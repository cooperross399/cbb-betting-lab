"""The player-prop family was registered before the model existed.

That ordering is the whole content of a pre-registration. A direction written
down after the numbers are seen is not a prediction, and nothing about the
ledger entry itself distinguishes the two afterwards — the entry looks
identical either way. What distinguishes them is that on the commit which
registered these, **there was no player model to measure anything with**.

That started as one assertion over five absent files. **Four of them have now
arrived** — the frozen constants, their fitter, their loader, and as of this
commit the estimator, `models/player_rates.py`. So the ordering is no longer
carried by the tree being empty, and this file says what it is carried by
instead.

What still holds without argument: `models/player_distributions.py` does not
exist, and **nothing in this repository can turn a projection into a
probability without it**. `player_rates.py` produces a mean, a 46-long minutes
lattice and a refusal census; it produces no `P(over)`, no de-vigged
comparison and no log loss, so not one of the 33 hypotheses below can have been
looked at. That is the same claim the empty tree used to make, narrowed to the
file that actually stands between a projection and a graded number.

What the rest rests on, now that the inputs exist, is
`test_the_directions_could_not_have_been_written_after_the_numbers`: every
entry is `pending` with an empty realised direction, the ledger is append-only
under its own CI job, and the constants were fitted on 2019-2022 and validated
on 2023 with a price-season floor at 2024 that their loader refuses to cross.
None of those is a promise and none can be satisfied by deleting a line.

The rest pins the shape the design named, so a later session cannot quietly
grow or shrink the family:

- ten priceable markets by three conference tiers, thirty entries, each
  claiming the model's mean log loss is BELOW the de-vigged two-sided fair
  price's in that cell;
- three more, one per tier, against the identity-blind role-prior control;
- `player_first_basket` and `player_double_double` absent, because both are
  refused by name in the design and a refused market costs no hypothesis;
- season 2024 and `discovery` throughout, because every prop quote in the store
  is one season and there is no second one to hold out;
- and 95 cumulative hypotheses, x1.7689, which is what every other interval in
  this lab now pays for them.
"""

from __future__ import annotations

import dataclasses
import importlib.util
import json
from pathlib import Path

from cbb_betting_lab import experiment_ledger as E

_REPO = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "record_experiments", _REPO / "scripts" / "record_experiments.py"
)
assert _spec and _spec.loader
recorder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(recorder)

TRACKED = _REPO / "data" / "outputs" / "experiment_ledger.json"
DEVIG = "player_props_vs_devig"
CONTROL = "player_props_vs_role_prior"

#: The two markets the design refuses BY NAME. Neither may appear as a
#: hypothesis: a refused market costs no degree of freedom, and the second
#: refusal says so outright — pricing `player_double_double` "would add a
#: pre-registered hypothesis, widening every other interval in the lab, in
#: exchange for a sample of one".
REFUSED_MARKETS = ("first_basket", "double_double")


def _tracked() -> dict:
    return json.loads(TRACKED.read_text(encoding="utf-8"))


def _player_entries(payload: dict) -> list[dict]:
    return [h for h in payload["hypotheses"] if h["search"] in (DEVIG, CONTROL)]


#: What is left of the MODEL — the thing the 33 hypotheses make a prediction
#: about. `player_rates.py` moved out of this list in the commit that wrote it;
#: `player_distributions.py` is what remains, and while it is absent no
#: projection in this repository can become a probability, so no hypothesis
#: below can have been looked at.
MODEL_FILES = (
    "src/cbb_betting_lab/models/player_distributions.py",
)

#: Its INPUTS, which do now exist. Named rather than merely allowed, so a fifth
#: file appearing under this heading is a red test and a decision somebody
#: makes on purpose. `player_rates.py` is here rather than above because it
#: forms projections and refusals and cannot score anything: it has no line, no
#: price and no outcome to compare against, and the ten markets it is
#: registered for are named in `MARKET_COMPONENTS` before any of them has been
#: measured.
INPUT_FILES = (
    "src/cbb_betting_lab/models/player_shapes.py",
    "src/cbb_betting_lab/models/player_rates.py",
    "scripts/fit_player_model.py",
    "data/processed/cbb_player_shapes.json",
)


def test_nothing_in_this_tree_can_turn_a_projection_into_a_probability() -> None:
    """The registration precedes the thing it registers, narrowed twice.

    This test used to assert that all five files were absent, and it said in
    its own docstring that the commit which builds the model is expected to
    change it. That commit has now landed for four of them: the frozen
    constants, their fitter, their loader and the estimator are on disk. The
    assertion is narrowed rather than deleted, because deleting it is exactly
    what it exists to make difficult.

    What it now says: `player_distributions.py` does not exist. Without it
    there is no `P(over)`, no de-vigged fair price to compare one against and
    no log loss, and every one of the 33 hypotheses below is a claim about a
    mean log loss. So no number has met them, and could not have.

    The second narrowing is a check on the first, because "the file is absent"
    is a claim about a name: nothing anywhere in `src/` or `scripts/` produces
    a player probability. `models/player_rates.py` returns a mean, a minutes
    lattice and refusals, and its own tests assert that a priceable projection's
    last word is that no engine exists.
    """
    for relative in MODEL_FILES:
        assert not (_REPO / relative).exists(), (
            f"{relative} exists, so a player model can now price these markets "
            "and the ordering is no longer visible in the tree. The hypotheses "
            "stay as written and the directions stay as predicted; move this "
            "assertion into the ordering evidence below and say what it now "
            "rests on."
        )
    for relative in INPUT_FILES:
        assert (_REPO / relative).exists(), (
            f"{relative} is named here as an input the model will read and is "
            "not on disk. Either it was removed, in which case take it off this "
            "list, or this list is wrong."
        )

    from cbb_betting_lab.models import player_rates

    produced = {
        name.lstrip("_")
        for name in dir(player_rates)
        if "probab" in name.lower()
    }
    assert produced == {"dnp_probability"}, (
        f"the estimator now exposes {sorted(produced)}. `dnp_probability` is a "
        "stored diagnostic that is never multiplied into a price; anything else "
        "with a probability in its name is a price, and this family was "
        "registered before one existed."
    )
    fields = {
        field.name for field in dataclasses.fields(player_rates.PlayerProjection)
    }
    assert "model_probability" not in fields and "push_mass" not in fields, (
        "a projection now carries a probability, so the thing the 33 "
        "hypotheses predict about exists. Say what the ordering rests on."
    )


def test_the_directions_could_not_have_been_written_after_the_numbers() -> None:
    """What the ordering rests on now that the inputs exist.

    A pre-registration is worth nothing unless the direction was fixed before
    the measurement. With the constants now on disk, three independent things
    have to hold, and none of them is a promise:

    * **Nothing has been measured.** Every entry is `pending` with an empty
      realised direction, so no number has met these hypotheses yet.
    * **The ledger is append-only**, enforced by
      `scripts/check_ledger_append_only.py` and its own CI job, so these
      entries cannot be edited or back-dated into the middle of the file after
      a result is seen.
    * **The constants could not have been tuned on what they will be graded
      against.** Every hypothesis names season 2024 and nothing else. The
      frozen shapes file was fitted on 2019-2022, validated on 2023, and
      carries a price-season floor at 2024 that its loader refuses to cross.
      A constant fitted on the graded season would make the whole family
      unfalsifiable; this is the check that it was not.
    """
    entries = _player_entries(_tracked())
    assert len(entries) == 33

    seasons = {season for entry in entries for season in entry["seasons"]}
    assert seasons == {2024}, (
        f"the family names seasons {sorted(seasons)}. It is registered against "
        "2024 alone, which is the only season this lab has prop quotes for."
    )

    shapes = json.loads(
        (_REPO / "data" / "processed" / "cbb_player_shapes.json").read_text(
            encoding="utf-8"
        )
    )
    fitted = set(shapes["fit_seasons"]) | {shapes["validation_season"]}
    assert not (fitted & seasons), (
        f"the constants were fitted or validated on {sorted(fitted & seasons)}, "
        "which is a season these hypotheses will be graded on. A constant that "
        "has seen the graded season makes the prediction unfalsifiable."
    )
    assert shapes["price_season_floor"] <= min(seasons)
    assert shapes["never_runs_at_price_time"] is True


def test_nothing_player_shaped_has_been_measured() -> None:
    """Every entry is `pending` with no realised direction.

    A pre-registered hypothesis that already carries an outcome was not
    pre-registered.
    """
    for entry in _player_entries(_tracked()):
        assert entry["outcome"] == "pending", entry["name"]
        assert entry["realised_direction"] == "", entry["name"]


def test_thirty_market_by_tier_cells_are_registered() -> None:
    payload = _tracked()
    devig = [h for h in payload["hypotheses"] if h["search"] == DEVIG]
    assert len(devig) == 30 == len(recorder.PLAYER_MARKETS) * len(recorder.PLAYER_TIERS)
    expected = {
        (
            f"player_{market} / {tier}: the model's mean log loss is below "
            "the de-vigged two-sided fair price's"
        )
        for market in recorder.PLAYER_MARKETS
        for tier in recorder.PLAYER_TIERS
    }
    assert {h["name"] for h in devig} == expected


def test_three_control_cells_are_registered_one_per_tier() -> None:
    control = [h for h in _tracked()["hypotheses"] if h["search"] == CONTROL]
    assert len(control) == 3
    assert {h["name"].split(":", 1)[0] for h in control} == set(recorder.PLAYER_TIERS)
    assert all("role-prior control" in h["name"] for h in control)


def test_the_low_major_cells_are_registered_although_underpowered() -> None:
    """Registered so they cannot be dropped once they are seen.

    The design declares the low-major cell underpowered by construction — 6,198
    quotes, 123 subjects, 19 games — and says it will be reported as "no
    demonstrated edge, n = ..." whatever it returns. Leaving it unregistered
    and reporting it anyway would be the cheapest version of the search this
    ledger exists to price.
    """
    low = [h for h in _player_entries(_tracked()) if "low_major" in h["name"]]
    assert len(low) == len(recorder.PLAYER_MARKETS) + 1 == 11


def test_no_pooled_division_one_player_cell_exists() -> None:
    for entry in _player_entries(_tracked()):
        assert "pooled across Division" not in entry["name"]
        assert any(tier in entry["name"] for tier in recorder.PLAYER_TIERS), entry["name"]


def test_the_refused_markets_cost_no_hypothesis() -> None:
    names = " ".join(h["name"] for h in _player_entries(_tracked()))
    for market in REFUSED_MARKETS:
        assert market not in names, (
            f"player_{market} is refused by name in the design; registering it "
            "would spend a degree of freedom on a market that will not be priced"
        )


def test_every_player_hypothesis_predicts_lower_log_loss_on_one_season_at_discovery() -> None:
    """`lower` because the metric is log loss, and lower is the model winning.

    `discovery` and season 2024 because every prop quote in the store is one
    season: there is no held-out season, so nothing here may ever be called a
    replication, and none of these is entitled to the `either` direction the
    ledger admits at the holdout stage alone.
    """
    entries = _player_entries(_tracked())
    assert len(entries) == 33
    for entry in entries:
        assert entry["predicted_direction"] == "lower", entry["name"]
        assert entry["stage"] == "discovery", entry["name"]
        assert entry["seasons"] == [2024], entry["name"]
        assert entry["tested_on"] == "2026-09-05", entry["name"]


def test_the_family_went_from_62_to_95_and_the_factor_from_1_7095_to_1_7689() -> None:
    """The price of the registration, computed rather than quoted.

    62 is what the ledger held after the replication of 2026-09-05 appended its
    32 holdout looks; 95 is what it holds now. Every interval this lab has
    already published is corrected over the cumulative count, so the 33 entries
    above are paid for by all of them.
    """
    ledger = E.load(TRACKED)
    assert ledger.count == 95
    before = E.ExperimentLedger(
        hypotheses=[h for h in ledger.hypotheses if h.search not in (DEVIG, CONTROL)]
    )
    assert before.count == 62
    assert round(before.correction_factor(), 4) == 1.7095
    assert round(ledger.correction_factor(), 4) == 1.7689
