"""The 2027 forward window, registered before it opened.

Every historical season this lab holds is spent. 2021-2023 was discovery, 2024
the declared holdout, and the replication run reached 2025-26 and said so in
its own record. Forward collection is the only clean evidence left, and unlike
a price it **cannot be back-dated**: a night the pipeline did not freeze is
gone permanently.

So the three entries registered on 2026-09-10 are the last pre-registration
this lab can make honestly, and everything that makes them worth their own
correction is a fact about the tree rather than a promise in a docstring:

1. they were registered **before the window opened** -- eight weeks before the
   2026-11-02 opener, with zero rows of forward evidence in existence;
2. the window is **three seasons**, because one cannot answer the question;
3. there are **three of them**, one per tier, which is the floor the
   no-pooled-Division-I rule allows;
4. the direction is **declared**, and it is the one six seasons of evidence
   say will fail.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parents[1]
_LEDGER = _REPO / "data" / "outputs" / "experiment_ledger.json"

#: The 2026-27 Division I season's first game, from the tracked schedule.
_SCHEDULE = _REPO / "data" / "raw" / "cbb" / "schedules" / "mbb_schedule_2027.parquet"

SEARCH = "forward_2027"
TIERS = {"high_major", "mid_major", "low_major"}


def _entries() -> list[dict]:
    payload = json.loads(_LEDGER.read_text(encoding="utf-8"))
    return [h for h in payload["hypotheses"] if h.get("search") == SEARCH]


def test_three_entries_one_per_tier_and_no_pooled_row() -> None:
    """The floor the no-pooling rule allows, and not one entry more.

    Every hypothesis widens every interval this lab has already published. The
    historical build registered 33 market-by-tier cells; a forward window with
    a tenth of the sample cannot support that resolution, and registering it
    would buy nothing but a wider correction for everybody.
    """
    entries = _entries()
    assert len(entries) == 3, (
        f"{len(entries)} forward entries are registered. Three is the floor the "
        "no-pooled-Division-I rule allows and the ceiling the sample supports."
    )
    named = {t for t in TIERS for e in entries if e["name"].startswith(f"{t}:")}
    assert named == TIERS
    for entry in entries:
        assert "division" not in entry["name"].lower()
        assert "pooled" not in entry["name"].lower(), (
            "a pooled all-of-Division-I forward row is exactly the headline "
            "this lab refuses to report"
        )


def test_the_window_was_registered_before_it_opened() -> None:
    """The ordering, against the tree rather than against a comment.

    Two independent facts, neither of which is a promise. The registration is
    dated before the season's first game, and at that date the forward ledger
    held **nothing** -- so no row of the evidence these entries will be graded
    on could have been seen when the direction was written down.
    """
    entries = _entries()
    registered = {date.fromisoformat(e["tested_on"]) for e in entries}
    assert len(registered) == 1, "the three were registered on one date or none"
    stamped = registered.pop()

    pd = pytest.importorskip("pandas")
    schedule = pd.read_parquet(_SCHEDULE, columns=["date"])
    opener = min(date.fromisoformat(str(d)[:10]) for d in schedule["date"])
    assert stamped < opener, (
        f"the window was registered {stamped}, on or after the {opener} opener. "
        "A direction fixed after the first game is not a prediction."
    )

    forward = json.loads(
        (_REPO / "data" / "outputs" / "cbb_forward_evidence.json").read_text("utf-8")
    )
    assert int(forward.get("frozen_opinions", 0)) == 0, (
        "forward evidence already existed when this window was registered, so "
        "the direction cannot be shown to have been written blind"
    )
    assert not forward.get("rows"), "the forward ledger is not empty"


def test_the_window_is_three_seasons_because_one_cannot_answer_it() -> None:
    """One season's detectable return is ~10% against a 1-3% edge.

    Registering 2027 alone would spend the last clean holdout on a question
    the sample cannot answer, and its null would say nothing about the model.
    """
    for entry in _entries():
        seasons = list(entry["seasons"])
        assert len(seasons) >= 3, (
            f"{entry['name']!r} is registered over {seasons}. One forward "
            "season can demonstrate a return of roughly 9.5%-11.9% once "
            "corrected, against a realistic edge of 1%-3%."
        )
        assert min(seasons) >= 2027, (
            "a forward window may not name a season this lab already holds "
            "prices for; that is a holdout spent before it opened"
        )


def test_the_direction_is_declared_and_is_the_one_expected_to_fail() -> None:
    """Six seasons say this fails. Writing it down is what makes it a test."""
    entries = _entries()
    assert {e["predicted_direction"] for e in entries} == {"higher"}
    assert {e["stage"] for e in entries} == {"holdout"}, (
        "nothing here is being searched: the model exists and its direction is "
        "fixed before a game is played, which is a holdout and not discovery"
    )
    assert {e["outcome"] for e in entries} == {"pending"}


def test_the_registration_cost_is_paid_by_everything_already_published() -> None:
    """98 hypotheses, and both live deficits survive the wider correction.

    The cost is the point rather than an objection to it, but it has to be
    stated: these three widen every interval this lab holds, and a claim that
    dissolved under them was never worth its width.
    """
    from cbb_betting_lab import stats as S

    payload = json.loads(_LEDGER.read_text(encoding="utf-8"))
    assert len(payload["hypotheses"]) == 98

    record = json.loads(
        (_REPO / "data" / "outputs" / "cbb_price_backtest.json").read_text("utf-8")
    )
    deficits = [
        c for c in record["by_tier"] if c.get("verdict") == "demonstrated deficit"
    ]
    assert deficits, "the record holds no demonstrated deficit to check"
    for cell in deficits:
        half = (cell["high"] - cell["low"]) / 2.0
        widened = cell["roi"] + S.bonferroni_factor(98) * half
        assert widened < 0.0, (
            f"{cell['name']} stops being a demonstrated deficit at 98 "
            "hypotheses. Registering the forward window retracted a published "
            "finding, which has to be stated in the commit that does it."
        )
