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

**On 2026-09-07 the last of those narrowings was spent.**
`reports/prop_grading.py` de-vigs, scores a mean log loss and a Brier, and
prints a verdict per market and per tier, and `scripts/run_prop_grading.py`
runs it over the whole store. So every one of the 33 hypotheses below has now
been looked at, and the ordering can no longer be carried by anything about the
tree being empty. That is the state this file was always going to reach, and
its own docstring said so.

What carries it instead, and none of these can be satisfied by writing or
deleting a file:

* **The constants could not have been tuned on what they are graded against.**
  Every hypothesis names season 2024 and nothing else; the frozen shapes file
  was fitted on 2019-2022, validated on 2023, and carries a price-season floor
  at 2024 that its loader refuses to cross. A constant that had seen the graded
  season would make the whole family unfalsifiable.
* **The ledger is append-only**, under its own CI job, keyed on
  `(search, name, seasons, stage)` and diffed against the PR base — so a
  direction cannot be edited or a cell dropped once a number is seen.
* **The scoring path is NAMED here.** The two files above are pinned by name
  and by the probability names they bind, so a second, unnamed scorer appearing
  anywhere in `src/` or `scripts/` is a red build.

**`pending` is not part of that evidence and this file no longer treats it as
if it were.** All 95 entries in the ledger are `pending`, including the four
core-team hypotheses the price backtest measured on 2026-09-05: this lab's
convention is that the ledger records the registration and the record on disk
carries the result. Reading `pending` as "nothing has been measured" would have
been a false inference from a true field, which is the same shape of mistake the
rest of this repository is arranged against.

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

import ast
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


#: The two directories the sentence "nothing in this tree produces a player
#: probability" is a sentence about. Both, because a P(over) written in a
#: script grades a hypothesis exactly as well as one written in the package,
#: and the pre-registration is a claim about the whole commit.
SEARCHED_TREES = ("src/cbb_betting_lab", "scripts")

#: What a player probability would be CALLED. Six tokens rather than one,
#: because the thing being looked for is not only the word "probability": a
#: P(over) is a de-vigged comparison against a fair price scored by log loss,
#: and every one of those words is a plausible name for the function that
#: produces it. Measured against this tree on 2026-09-06, the six together
#: match exactly two names, both in `models/player_rates.py`; `prob` is
#: deliberately NOT among them, because it matches `problem` and `probe` and a
#: token that fires on unrelated code trains a reader to ignore this test.
PROBABILITY_TOKENS = (
    "probab", "p_over", "log_loss", "devig", "de_vig", "fair_price",
)

#: The only player probability name allowed to exist. `dnp_probability` is a
#: stored diagnostic that is never multiplied into a price, and the assertion
#: on `player_rates`' namespace below says the same thing about the same name
#: from the other direction.
ALLOWED = frozenset({"dnp_probability", "_dnp_probability"})


def _bound_names(source: str) -> set[str]:
    """Every name a module binds, at any depth, however it binds it.

    Functions, classes, plain and annotated assignments, attribute stores and
    arguments. Depth matters: a P(over) written as a method on a class, or as a
    closure inside a report builder, is a player probability in this tree just
    as much as a module-level `def` is, and a scan that only read the top level
    would be a scan a later session could step around without meaning to.
    """
    names: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, ast.Attribute) and isinstance(node.ctx, ast.Store):
            names.add(node.attr)
        elif isinstance(node, ast.arg):
            names.add(node.arg)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _is_a_player_probability_name(name: str, *, in_a_player_file: bool) -> bool:
    """Does `name` name a player probability, judged by the name alone?

    Two halves, and both are needed. A probability token alone would fire on
    `distributions.scoring_probability` and `card_pricing.probability`, which
    are team-model prices this family says nothing about. The player half is
    carried either by the name itself or by the file it is written in — a
    module called `player_something.py` is a player module and everything in it
    is player-shaped, which is how `models/player_probability.py` would be
    caught the moment somebody writes it.
    """
    lowered = name.lower()
    if not any(token in lowered for token in PROBABILITY_TOKENS):
        return False
    return in_a_player_file or "player" in lowered


def _player_probability_names() -> dict[str, list[str]]:
    """`{path: names}` for every player probability name in the searched trees.

    Empty except for the two allowed names, or the ordering evidence below is
    covering less than it says.
    """
    found: dict[str, list[str]] = {}
    for tree in SEARCHED_TREES:
        for path in sorted((_REPO / tree).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            hits = sorted(
                name
                for name in _bound_names(path.read_text(encoding="utf-8"))
                if _is_a_player_probability_name(
                    name,
                    in_a_player_file=(
                        "player" in path.name.lower() or "prop" in path.name.lower()
                    ),
                )
            )
            if hits:
                found[str(path.relative_to(_REPO))] = hits
    return found


#: What is left of the MODEL — the thing the 33 hypotheses make a prediction
#: about. `player_rates.py` moved out of this list in the commit that wrote it;
#: `player_distributions.py` is what remains, and while it is absent no
#: projection in this repository can become a probability, so no hypothesis
#: below can have been looked at.
#: **Empty, and that is the fourth narrowing rather than a surrender.** This
#: began as five files that had to be absent. `player_distributions.py` landed
#: on 2026-09-06 and was the last of them, so nothing is held here by absence
#: any more — and the ordering claim does NOT rest on absence now. It rests on
#: the evidence below, which is stronger than a filename and cannot be
#: satisfied by writing one.
#:
#: Kept as an empty tuple rather than deleted, because the loop over it is what
#: a later session will reach for when a sixth file has to be held out, and
#: because an empty list somebody has to justify emptying is harder to abuse
#: than no list at all.
MODEL_FILES: tuple[str, ...] = ()

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
    "src/cbb_betting_lab/models/player_distributions.py",
    "scripts/fit_player_model.py",
    "data/processed/cbb_player_shapes.json",
)


#: Every player-probability name in the tree, measured on 2026-09-07 AFTER the
#: grading commit, with why each one is there.
#:
#: **This is no longer a list of things that are not a scored claim.** The
#: first four are still the engine's own lattice reads and the stored
#: did-not-play diagnostic. The rest are the scoring path itself:
#: `reports/prop_grading.py` is design section 10's metric — two de-vigs, a
#: mean log loss, a Brier, calibration by decile and a verdict per market and
#: per tier — and `scripts/run_prop_grading.py` is the wiring that prices the
#: store and hands it a frame.
#:
#: Pinned so that a SECOND scoring path, written anywhere in `src/` or
#: `scripts/` under any name carrying `player` or a probability token, is a red
#: build. That is what this list is for now: the family was registered before
#: the scorer existed, and there is exactly one scorer.
PROBABILITY_NAMES_ON_THIS_COMMIT = {
    "src/cbb_betting_lab/models/player_distributions.py": [
        "probability",
        "void_probability",
    ],
    "src/cbb_betting_lab/models/player_rates.py": [
        "_dnp_probability",
        "dnp_probability",
    ],
    "src/cbb_betting_lab/reports/prop_grading.py": [
        "DEVIG_METHODS",
        "DEVIG_POWER",
        "DEVIG_PROPORTIONAL",
        "DEVIG_SENTENCE",
        "DevigCensus",
        "PROBABILITY_FLOOR",
        "SEARCH_VS_DEVIG",
        "devig",
        "devig_census",
        "devigged",
        "log_loss",
        "no_control_probability",
        "no_model_probability",
        "probability",
    ],
    "scripts/run_prop_grading.py": [
        "control_probabilities",
        "probabilities",
        "probability",
    ],
}

#: The two files the scoring path is allowed to live in. A third would be a
#: second scorer, and two scorers can disagree about what the 33 hypotheses
#: were answered with.
THE_SCORING_PATH = (
    "src/cbb_betting_lab/reports/prop_grading.py",
    "scripts/run_prop_grading.py",
)


def test_the_scoring_path_is_the_one_named_here_and_there_is_only_one() -> None:
    """The tree CAN now turn a projection into a scored number. Exactly once.

    This test used to be called
    `test_nothing_in_this_tree_can_turn_a_projection_into_a_probability` and it
    asserted, over the whole of `src/` and `scripts/`, that no player
    probability existed anywhere. That claim is false as of 2026-09-07 and the
    name is renamed rather than the assertion loosened: a test whose NAME says
    something untrue is worse than no test, and this file's whole subject is
    the difference between a prediction and a description.

    What it asserts now:

    1. Every input the model reads is on disk and named, so a fifth appearing
       under that heading is a decision somebody makes on purpose.
    2. The scoring path is exactly the two files in :data:`THE_SCORING_PATH`.
       A third file binding a player probability anywhere in `src/` or
       `scripts/` is red — two scorers can disagree about what the 33
       hypotheses were answered with, and nothing in a report would say which
       one produced the number on the page.
    3. The estimator itself still exposes no probability but the stored
       did-not-play diagnostic, and a `PlayerProjection` still carries neither
       a model probability nor a push mass. The scoring lives downstream of the
       projection, which is what makes the control constructible from the same
       object.

    Mutation: write a `player_over_probability` into any module under `src/` —
    RED, by name and by file.
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
    for relative in THE_SCORING_PATH:
        assert (_REPO / relative).exists(), (
            f"{relative} is named as the scoring path and is not on disk. If it "
            "was renamed, rename it here; if the scoring was removed, say so."
        )

    from cbb_betting_lab.models import player_rates

    produced = {
        name.lstrip("_")
        for name in dir(player_rates)
        if "probab" in name.lower()
    }
    assert produced == {"dnp_probability"}, (
        f"the estimator now exposes {sorted(produced)}. `dnp_probability` is a "
        "stored diagnostic that is never multiplied into a price, and the "
        "scoring lives downstream of the projection rather than inside it."
    )
    fields = {
        field.name for field in dataclasses.fields(player_rates.PlayerProjection)
    }
    assert "model_probability" not in fields and "push_mass" not in fields, (
        "a projection now carries a probability. The control is built by "
        "replacing a projection's RATES and reading the same engine; a "
        "projection that carried its own probability would make that "
        "substitution mean something different."
    )

    # The tree, read rather than described.
    found = _player_probability_names()
    assert found == PROBABILITY_NAMES_ON_THIS_COMMIT, (
        "the set of player probability names in this tree moved. New: "
        f"{sorted(set(found) - set(PROBABILITY_NAMES_ON_THIS_COMMIT))}. Gone: "
        f"{sorted(set(PROBABILITY_NAMES_ON_THIS_COMMIT) - set(found))}. If a "
        "second scoring path was written, say why this family may be answered "
        "twice; if a name moved inside the one that exists, update this list."
    )
    scoring_files = set(found) - {
        "src/cbb_betting_lab/models/player_distributions.py",
        "src/cbb_betting_lab/models/player_rates.py",
    }
    assert scoring_files == set(THE_SCORING_PATH), (
        f"{sorted(scoring_files)} score a player prop and "
        f"{sorted(THE_SCORING_PATH)} are the declared scoring path."
    )

    # The gap in that scan, held open. Red here means somebody taught the scan
    # to read what a function computes rather than what it is called, which is
    # strictly better and makes the paragraph above wrong: rewrite it.
    assert not _is_a_player_probability_name("_over", in_a_player_file=False), (
        "the scan now catches a name carrying neither `player` nor a "
        "probability token, so it is no longer a check on names alone"
    )


def test_the_directions_could_not_have_been_written_after_the_numbers() -> None:
    """What the ordering rests on now that the inputs exist.

    A pre-registration is worth nothing unless the direction was fixed before
    the measurement. The measurement has now happened, so two independent
    things have to hold, and neither of them is a promise:

    * **The ledger is append-only**, enforced by
      `scripts/check_ledger_append_only.py` and its own CI job, so these
      entries cannot be edited or back-dated into the middle of the file after
      a result is seen — which matters more now than it did before the scoring
      landed, not less.
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


def test_pending_is_this_ledgers_convention_and_not_evidence_of_anything() -> None:
    """Every entry is `pending`, and so is every entry this lab HAS measured.

    This test was called `test_nothing_player_shaped_has_been_measured` and its
    docstring said a pending entry means no number has met the hypothesis. That
    was never true of this ledger and is now visibly untrue: all 95 entries are
    `pending` with an empty realised direction, including the four core-team
    hypotheses the price backtest measured on 2026-09-05 and the 32 the
    replication appended. The convention here is that the LEDGER records the
    registration and the RECORD on disk carries the result.

    So the field is asserted — an entry that acquired an outcome would mean the
    convention changed and every reader of this ledger needs to know — but it
    is asserted as a convention and never again as evidence that a family is
    unmeasured. Reading it the other way is a false inference from a true
    field, which is the shape of mistake the rest of this repository is
    arranged against.
    """
    payload = _tracked()
    for entry in _player_entries(payload):
        assert entry["outcome"] == "pending", entry["name"]
        assert entry["realised_direction"] == "", entry["name"]

    every = payload["hypotheses"]
    assert len(every) == 95
    assert {entry["outcome"] for entry in every} == {"pending"}, (
        "some entries now carry an outcome and some do not, so `pending` has "
        "become a claim about which ones were measured. Say what the new "
        "convention is, here, before any report leans on it."
    )
    measured_but_pending = [
        entry["name"]
        for entry in every
        if entry["search"] == "core_team_markets"
    ]
    assert measured_but_pending, (
        "the core-team hypotheses are gone from the ledger. They are the "
        "worked example this test rests on: measured on 2026-09-05, published "
        "in `cbb_price_backtest.json`, and still `pending` here."
    )


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
