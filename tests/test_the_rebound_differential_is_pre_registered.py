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

#: The claim the recorder has to keep making, as a sentence.
UNDERPOWERED_CLAIM = "All three are underpowered"

#: And the ways of un-making it that a substring search would have missed.
NEGATIONS = (
    "not underpowered",
    "no way underpowered",
    "never underpowered",
    "hardly underpowered",
    "far from underpowered",
    "are powered",
    "is powered",
    "adequately powered",
    "sufficiently powered",
    "well powered",
    "not one of the three is underpowered",
)
TIERS = {"high_major", "mid_major", "low_major"}


def _recorder():
    """The recorder's constants, without importing it (it has side effects)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("_recorder", _RECORDER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prose(text: str) -> str:
    """Comment text as a reader reads it: markers stripped, then unwrapped.

    `re.sub(r"\\s+", " ", source)` on a comment block joins each line to the
    next with that line's `#` marker still in it, so a banned sentence split
    across two comment lines reads as `...the four seasons are the ones # the
    effect size actually needs...` and a literal search does not find it. The
    forbidden sentence was put back verbatim that way and the guard stayed green.
    """
    stripped = "\n".join(
        re.sub(r"^\s*#:?\s?", "", line) for line in text.splitlines()
    )
    return re.sub(r"\s+", " ", stripped).strip()


def _window_comment() -> str:
    """The REBOUND_WINDOW comment, and nothing either side of it.

    One helper, used by both the underpowered check and the test that pins its
    boundary. They computed the slice separately, so widening one back to
    `REBOUND_SLOPE =` -- the edit that lets the constants' comment vouch for the
    window's -- left the other asserting about a slice nobody used.
    """
    source = _RECORDER.read_text(encoding="utf-8")
    return source[
        source.index("#: The rebound-differential") : source.index("REBOUND_WINDOW =")
    ]


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

    # Scoped to the REBOUND_WINDOW comment ALONE. Reading up to `REBOUND_SLOPE =`
    # swept in the constants' own comment, which says "the powered/underpowered
    # claim agree with each other" -- a sentence about what this test checks, not
    # about the three hypotheses. A bare substring search was satisfied by that
    # one line, so the guard passed on a window comment that had been rewritten
    # to say anything at all. The commit that added the guard added the decoy.
    prose = _prose(_window_comment())
    assert UNDERPOWERED_CLAIM in prose, (
        f"scripts/record_experiments.py no longer states {UNDERPOWERED_CLAIM!r}, "
        "and the arithmetic above says it is true. The comment is the only place "
        "a reader meets this, so the claim is pinned as a sentence rather than as "
        "a word: `\"underpowered\" in block` was satisfied by \"not "
        "underpowered\", so the comment could assert the exact opposite while "
        "this same function computed the shortfall and accepted it."
    )
    for negation in NEGATIONS:
        assert negation not in prose, (
            f"the window comment contains {negation!r}. Every tier is "
            "underpowered by this function's own arithmetic; the prose beside it "
            "does not get to say otherwise."
        )


def test_every_power_figure_in_the_comment_reproduces_from_the_constants() -> None:
    """The comment says the figures reproduce. This is what checking that means.

    They did not. Five pooled figures were printed beside the sentence "Those
    pooled figures do reproduce" and every one was ~0.3% high -- computed from a
    standard error of about 1.3143 while the constants beside them record 1.31 --
    at the same time as the per-tier 12.02 in the same comment WAS computed from
    1.31. Two halves of one comment, two standard errors, and a claim of
    agreement between them.

    It was not caught because nothing compared the prose to the arithmetic; the
    word "reproduce" was doing the work a test should. Every number the comment
    quotes is now parsed out of it and recomputed.
    """
    from cbb_betting_lab import stats as S

    recorder = _recorder()
    block = _window_comment()

    def detectable(games, power):
        error = recorder.REBOUND_SLOPE_STANDARD_ERROR * math.sqrt(
            recorder.REBOUND_GAMES_MEASURED / games
        )
        return (S.bonferroni_z(101) + (S.Z80 if power else 0.0)) * error

    season = recorder.REBOUND_GAMES_PER_SEASON
    expected = {
        "one season": detectable(season, False),
        "two seasons": detectable(season * 2, False),
        "three seasons": detectable(season * 3, False),
        "three at 80% power": detectable(season * 3, True),
        "four at 80% power": detectable(season * 4, True),
        "per tier, four seasons, 80% power": detectable(
            season * len(recorder.REBOUND_WINDOW) / len(TIERS), True
        ),
    }
    quoted = {f"{value:.2f}" for value in expected.values()}
    printed = set(re.findall(r"\b\d{1,2}\.\d{2}\b", block)) - {
        f"{recorder.REBOUND_SLOPE:.2f}",
        f"{recorder.REBOUND_SLOPE_STANDARD_ERROR:.2f}",
    }
    stray = printed - quoted
    assert not stray, (
        f"the REBOUND_WINDOW comment prints {sorted(stray)}, and no power figure "
        f"derived from the recorded constants rounds to any of them. The "
        f"derivable figures are {sorted(quoted)}. Either the prose is stale or "
        "the constants are; they cannot both be right, and the comment is the "
        "only place a reader meets either."
    )
    for label, value in expected.items():
        assert f"{value:.2f}" in block, (
            f"the comment no longer quotes the {label} figure ({value:.2f}). "
            "Every figure the window rests on is stated there on purpose."
        )


def test_the_underpowered_search_region_excludes_the_constants_comment() -> None:
    """The region boundary pinned, because widening it back changes nothing today.

    `test_the_registered_tests_are_underpowered_and_the_recorder_says_so` greps a
    slice of the recorder for the word "underpowered". That slice originally ran
    to `REBOUND_SLOPE =`, which swept in the constants' own comment -- and that
    comment contains "the powered/underpowered claim agree with each other", a
    sentence about what the TEST checks. One decoy line satisfied the grep on its
    own, so the guard passed on a window comment rewritten to say anything at
    all. The commit that added the guard added the decoy.

    Reverting the boundary passes while the real comment still says the word, so
    the boundary is asserted directly.
    """
    source = _RECORDER.read_text(encoding="utf-8")
    region = _window_comment()
    assert "REBOUND_SLOPE" not in region, (
        "the searched region now reaches the constants and their comment. "
        "Anything written there can satisfy the underpowered check on the window "
        "comment's behalf."
    )
    decoy = "powered/underpowered claim agree"
    assert decoy in source, (
        f"the decoy string {decoy!r} is gone from the recorder. That is fine in "
        "itself -- but this test exists to prove the region EXCLUDES it, so "
        "without it there is nothing being excluded and the assertion above is "
        "vacuous. Point this at whatever text now sits between the window "
        "comment and the constants."
    )
    assert decoy not in region, (
        "the decoy sits inside the searched region again."
    )


def test_the_recorder_does_not_claim_the_window_is_sized_to_the_effect() -> None:
    """The sentence that was wrong, kept out by name.

    "the four seasons are the ones the effect size actually needs" stood in the
    recorder    beside an arithmetic that says otherwise.
    """
    flat = _prose(_RECORDER.read_text(encoding="utf-8"))
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
