"""The rebound-differential registration, pinned.

**PR #62 registered three hypotheses and tested none of them.** It edited
`tests/test_the_forward_window_is_pre_registered.py`, whose every test filters
the ledger to `search == "forward_2027"` -- so the five green results in that
file ran over the 2027 forward window and never saw the three
`rebound_differential_vs_spread` entries the commit was named for. A fourth
pooled Division-I entry, a `stage` flipped to `discovery`, or a window reaching
back into a season this lab already holds prices for would all have passed.

This file is that coverage. It also pins the thing the registration actually got
wrong: the four-season window was chosen from a POOLED power calculation while
the three entries are per-tier, and all three are underpowered. That is stated
in `scripts/record_experiments.py` and asserted here, so the claim and the
arithmetic cannot drift apart again -- in either direction. Widen the window
enough to make the tests powered and this file fails until the comment stops
saying they are not.
"""

from __future__ import annotations

import json
import math
import re
from datetime import date
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_LEDGER = _REPO / "data" / "outputs" / "experiment_ledger.json"
_RECORDER = _REPO / "scripts" / "record_experiments.py"

SEARCH = "rebound_differential_vs_spread"
TIERS = {"high_major", "mid_major", "low_major"}


def _recorder():
    """The recorder's constants, without importing it (it has side effects)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("_recorder", _RECORDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _entries(payload: dict | None = None) -> list[dict]:
    if payload is None:
        payload = json.loads(_LEDGER.read_text(encoding="utf-8"))
    return [h for h in payload["hypotheses"] if h.get("search") == SEARCH]


def _shape(entries) -> None:
    """The registration's shape, over whatever ledger it is handed.

    Taken out of the test so it can be run against a SYNTHETIC ledger as well as
    the committed one. Mutating the committed ledger to prove this guard bites
    is not available -- it is append-only and a test must not write it -- and
    without a synthetic payload the assertions here are never shown to fail on
    anything.
    """
    assert len(entries) == 3, (
        f"{len(entries)} {SEARCH} entries in the ledger, expected three -- one "
        "per tier. The ledger is append-only, so a fourth is a registration "
        "someone made without updating this file."
    )
    # The pooled check runs BEFORE the tier-set check. A pooled entry's name
    # head is not a tier, so the tier-set assertion would fire first and report
    # it as a missing tier -- true, but not the thing that is wrong with it.
    for entry in entries:
        head = entry["name"].split(":", 1)[0].strip().lower()
        assert "division" not in head and "pooled" not in head, (
            f"{entry['name']!r} reads as a pooled Division I hypothesis. This "
            "lab never reports one, so it never registers one either."
        )
    tiers = {e["name"].split(":", 1)[0].strip() for e in entries}
    assert tiers == TIERS, f"tiers registered: {sorted(tiers)}"


def test_three_entries_one_per_tier_and_no_pooled_row() -> None:
    """One per tier, and no all-of-Division-I row. The rule has no exception."""
    _shape(_entries())


def test_the_shape_check_refuses_the_registrations_it_exists_to_refuse():
    """The same check, shown failing -- on a ledger built for the purpose.

    Without this the assertions above are only ever seen to PASS, which is the
    state a vacuous guard is indistinguishable from.
    """
    committed = _entries()

    pooled = {**committed[0], "name": "Division I: a team's prior advantage predicts margin"}
    with pytest.raises(AssertionError, match="pooled Division I"):
        _shape(committed[:2] + [pooled])

    with pytest.raises(AssertionError, match="expected three"):
        _shape(committed[:2])

    relabelled = [{**committed[0], "name": "high_major: x"}] * 3
    with pytest.raises(AssertionError, match="tiers registered"):
        _shape(relabelled)


def test_the_window_was_registered_before_a_single_possession_of_it() -> None:
    """Registered 2026-09-10; the first season in the window opens in 2026-11."""
    for entry in _entries():
        registered = date.fromisoformat(entry["tested_on"])
        assert registered == date(2026, 9, 10), entry["tested_on"]
        assert min(entry["seasons"]) >= 2027, (
            f"{entry['name']!r} names season {min(entry['seasons'])}, which this "
            "lab already holds prices for. A window that reaches into bought "
            "data is not a forward test."
        )


def test_the_direction_and_stage_are_declared_and_nothing_is_graded_yet() -> None:
    entries = _entries()
    assert {e["predicted_direction"] for e in entries} == {"higher"}
    assert {e["stage"] for e in entries} == {"holdout"}
    assert {e["outcome"] for e in entries} == {"pending"}


def test_the_window_matches_the_constant_it_was_registered_from() -> None:
    window = tuple(_recorder().REBOUND_WINDOW)
    for entry in _entries():
        assert tuple(entry["seasons"]) == window, (
            f"{entry['name']!r} is registered over {entry['seasons']} while "
            f"REBOUND_WINDOW is {window}. The ledger is append-only: the "
            "constant moved after the entries were written."
        )


def test_the_registered_tests_are_underpowered_and_the_recorder_says_so() -> None:
    """The defect PR #62 shipped, pinned so it cannot be quietly restated.

    The window was sized on the POOLED sample and the entries are PER-TIER. A
    tier's slope is estimated from that tier's games alone, so the pooled figure
    describes a test that was never registered. Split the same sample into exact
    thirds -- the most charitable division available, since the true split is
    more lopsided -- and compare against each tier's own observed slope.

    Asserting the shortfall, rather than asserting a comfortable margin, is
    deliberate: it is what makes a later widening of the window fail here until
    the prose is updated to match.
    """
    from cbb_betting_lab import stats as S

    recorder = _recorder()
    window = len(recorder.REBOUND_WINDOW)
    looks = len(json.loads(_LEDGER.read_text(encoding="utf-8"))["hypotheses"])

    per_tier_games = recorder.REBOUND_GAMES_PER_SEASON * window / len(TIERS)
    error = recorder.REBOUND_SLOPE_STANDARD_ERROR * math.sqrt(
        recorder.REBOUND_GAMES_MEASURED / per_tier_games
    )
    detectable = (S.bonferroni_z(looks) + S.Z80) * error

    underpowered = {
        tier: slope
        for tier, slope in recorder.REBOUND_SLOPE_BY_TIER.items()
        if slope < detectable
    }
    assert underpowered == recorder.REBOUND_SLOPE_BY_TIER, (
        f"at {looks} hypotheses and {window} seasons the per-tier minimum "
        f"detectable slope is {detectable:.2f}, and "
        f"{sorted(set(recorder.REBOUND_SLOPE_BY_TIER) - set(underpowered))} now "
        "clear it. That is good news and it makes the recorder's comment wrong: "
        "it says all three are underpowered. Update the comment in the same "
        "commit that earns it."
    )

    source = _RECORDER.read_text(encoding="utf-8")
    block = source[: source.index("REBOUND_SLOPE =")]
    assert "underpowered" in block.rsplit("#: The rebound-differential", 1)[-1], (
        "scripts/record_experiments.py no longer says these entries are "
        "underpowered, and the arithmetic above says they are. The comment is "
        "the only place a reader meets this; it does not get to stop saying it."
    )


def test_the_recorder_does_not_claim_the_window_is_sized_to_the_effect() -> None:
    """The sentence that was wrong, kept out by name.

    "the four seasons are the ones the effect size actually needs" stood in the
    recorder for a week beside an arithmetic that says otherwise.
    """
    source = _RECORDER.read_text(encoding="utf-8")
    flat = re.sub(r"\s+", " ", source)
    for claim in (
        "the four seasons are the ones the effect size actually needs",
        "Four needs 6.96 and clears it.",
    ):
        assert claim not in flat, (
            f"scripts/record_experiments.py claims {claim!r} again. The power "
            "calculation behind it is pooled; the registered tests are per "
            "tier. If the window has genuinely been re-derived per tier, this "
            "assertion is the thing to change -- with the new arithmetic beside "
            "it."
        )
