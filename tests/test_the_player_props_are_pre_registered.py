"""The player-prop family was registered before the model existed.

That ordering is the whole content of a pre-registration. A direction written
down after the numbers are seen is not a prediction, and nothing about the
ledger entry itself distinguishes the two afterwards — the entry looks
identical either way. What distinguishes them is that on the commit which
registered these, **there was no player model to measure anything with**.

That started as one assertion over five absent files. Three of them have since
arrived — the frozen constants, their fitter and their loader — so the claim is
now carried by two tests instead of one: no model exists (`player_rates.py` and
`player_distributions.py`, the files that could actually price a prop, are
still absent), and nothing about the constants could have been tuned on what
they will be graded against (fitted on 2019-2022, validated on 2023, floor at
2024, which is the only season the family names). Neither is a promise, and
neither can be satisfied by deleting a line.

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


#: The files that constitute the MODEL — the thing the 33 hypotheses make a
#: prediction about. None exists yet, and while that is true the ordering claim
#: needs no argument at all.
MODEL_FILES = (
    "src/cbb_betting_lab/models/player_rates.py",
    "src/cbb_betting_lab/models/player_distributions.py",
)

#: Its INPUTS, which do now exist. Named rather than merely allowed, so a third
#: file appearing under this heading is a red test and a decision somebody
#: makes on purpose.
INPUT_FILES = (
    "src/cbb_betting_lab/models/player_shapes.py",
    "scripts/fit_player_model.py",
    "data/processed/cbb_player_shapes.json",
)


def test_the_model_these_hypotheses_predict_about_still_does_not_exist() -> None:
    """The registration precedes the thing it registers.

    This test used to assert that all five files were absent, and it said in
    its own docstring that the commit which builds the model is expected to
    change it. That commit has now landed for three of them: the frozen
    constants, their fitter and the loader are on disk. So the assertion is
    split rather than deleted, because deleting it is exactly what it exists to
    make difficult.

    What survives unchanged: no player model exists. `player_rates.py` and
    `player_distributions.py` are the model, and nothing here can price a prop
    without them. While that holds, the ordering is a fact about the tree.
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
