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
import re
from datetime import date
from pathlib import Path

import pytest

from cbb_betting_lab import season

_REPO = Path(__file__).resolve().parents[1]
_LEDGER = _REPO / "data" / "outputs" / "experiment_ledger.json"

#: When this lab looks for a game at all, from the tracked workflow. The
#: gameday cron runs November through April and nothing else, so a month
#: outside it is a month with no slate to freeze.
_GAMEDAY = _REPO / ".github" / "workflows" / "cbb-gameday-refresh.yml"

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

    # Both sources are TRACKED. An earlier version of this test read the
    # season's first game out of `data/raw/cbb/schedules/mbb_schedule_2027.
    # parquet`, which is not in the repository -- so it passed on a laptop
    # with the raw store linked and failed in CI, where the file does not
    # exist. A pre-registration whose ordering can only be checked on the
    # machine that made it proves nothing to anybody else.
    import yaml

    workflow = yaml.safe_load(_GAMEDAY.read_text(encoding="utf-8"))
    crons = [
        entry["cron"]
        for entry in (workflow[True] if True in workflow else workflow["on"])["schedule"]
    ]
    months = {
        int(part)
        for cron in crons
        for part in cron.split()[3].split(",")
        if part.isdigit()
    }
    assert months, f"no month field parsed out of {crons}"
    assert stamped.month not in months, (
        f"the window was registered in month {stamped.month}, which is a month "
        f"the gameday pipeline runs in ({sorted(months)}). A direction fixed "
        "once games are being played is not a prediction."
    )
    # The lab's own July cut puts this registration inside the season it
    # registers -- before any of it has been played.
    assert season.season_for_slate_date(stamped.isoformat()) == 2027

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
    """Every live deficit survives the correction the ledger holds TODAY.

    The cost is the point rather than an objection to it, but it has to be
    stated: a registration widens every interval this lab holds, and a claim
    that dissolved under one was never worth its width.

    **The count is read, not pinned.** This began as `== 98`, the size of the
    family on the day the forward window was registered, and the next
    registration -- the rebound differential, three more entries -- broke it. A
    literal here tests the calendar rather than the cost, and fails loudest
    exactly when a new registration is being made, which is the moment the cost
    check most needs to run. The ledger is the authority on its own size, and
    decision 46 already says so for every report; a test that replays
    yesterday's count is the same defect one layer down.

    **That rewrite first said the registration broke this "while retracting
    nothing", and that was false.** Going 98 -> 101 withdrew a published
    `demonstrated deficit` from `mid_major / player_threes` on the blind
    null-baseline side, in both the full-store and the held-out backtest -- its
    corrected high bound moved from -0.000007 to +0.000163. A wider family can
    only ever retract, this lab's rule is that the retraction is narrated in the
    commit that causes it, and the message on the `assert` below says exactly
    that. It was narrated nowhere. Which is also the point of the roster this
    check reads: it saw one cell of the record, and not that one.
    """
    from cbb_betting_lab import stats as S

    payload = json.loads(_LEDGER.read_text(encoding="utf-8"))
    looks = len(payload["hypotheses"])
    assert looks >= 98, (
        f"the ledger holds {looks} hypotheses and this lab had registered 98 by "
        "2026-09-10. It is append-only, so it cannot have shrunk: the file was "
        "cut, or this test is reading the wrong one."
    )

    examined, retracted = _readings_across_every_record(S, looks)
    assert examined > 200, (
        f"only {examined} published readings were examined; this repository's "
        "records carry well over two hundred. The roster stopped resolving -- "
        "a block was renamed, or a record moved -- and a cost check that reads "
        "nothing passes everything."
    )

    narration = " ".join(
        re.sub(r"\s+", " ", (_REPO / name).read_text(encoding="utf-8"))
        for name in ("CLAUDE.md", "docs/project_status.md")
    )
    unnarrated = [cell for cell in retracted if not _is_narrated(cell, narration)]
    assert not unnarrated, (
        "a wider family retracted "
        f"{len(unnarrated)} published reading(s) that no hand-written document "
        "names: "
        + "; ".join(
            f"{c['record']} {c['block']} {c['tier']}/{c['market']}"
            f"{'/' + c['name'] if c['name'] else ''} "
            f"(demonstrated at {c['scored']}, not at {looks})"
            for c in unnarrated[:6]
        )
        + ". A wider correction can only ever retract, and this lab's rule is "
        "that the retraction is narrated in the commit that causes it. Name the "
        "cell in CLAUDE.md or docs/project_status.md, or do not make the "
        "registration."
    )


def _cells(payload):
    """Every scored cell in a record, whatever block it lives in.

    Blocks are discovered rather than listed, because the defect this function
    exists for was a roster that named ONE of them. `by_tier` holds three rows;
    the record also carries `by_market_and_tier` and `null_baseline`, and the
    reading this lab actually retracted on 2026-09-10 was in the last of those.
    """
    scored = payload.get("looks")
    for block, rows in payload.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            value = row.get("roi", row.get("value"))
            error = row.get("standard_error")
            if value is None or error is None:
                continue
            if not row.get("enough_evidence"):
                continue
            yield {
                "block": block,
                "tier": row.get("tier"),
                "market": row.get("market"),
                "name": row.get("name"),
                "value": value,
                "standard_error": error,
                "scored": row.get("looks", scored),
            }


#: Every record that publishes a verdict a person could act on.
SCORED_RECORDS = (
    "cbb_price_backtest.json",
    "holdout/cbb_price_backtest.json",
    "core_team_only/cbb_price_backtest.json",
    "holdout/cbb_replication.json",
)


def _readings_across_every_record(S, looks):
    """(readings examined, readings that today's correction retracts)."""
    examined = 0
    retracted = []
    for relative in SCORED_RECORDS:
        path = _REPO / "data" / "outputs" / relative
        if not path.is_file():
            raise AssertionError(
                f"{relative} is on this check's roster and is not on disk. "
                "Re-render it or take it off the roster in this commit."
            )
        payload = json.loads(path.read_text(encoding="utf-8"))
        for cell in _cells(payload):
            scored = cell["scored"]
            if scored is None:
                continue
            examined += 1
            was = _demonstrated(S, cell, scored)
            now = _demonstrated(S, cell, looks)
            if was and not now:
                retracted.append({**cell, "record": relative})
    return examined, retracted


def _demonstrated(S, cell, looks):
    """Whether the cell's interval at `looks` excludes zero, either side."""
    half = S.bonferroni_z(looks) * cell["standard_error"]
    return (cell["value"] + half) < 0.0 or (cell["value"] - half) > 0.0


def _is_narrated(cell, narration: str) -> bool:
    """Whether a hand-written document names the cell that lost its reading.

    Spelled the several ways this repository writes a cell, because the rule is
    that a reader meets the retraction -- not that it is recorded in one canonical
    format.
    """
    tier, market = cell.get("tier"), cell.get("market")
    if not tier or not market:
        return False
    hyphen = tier.replace("_", "-")
    cell_named = any(
        spelling in narration
        for spelling in (
            f"{tier} / {market}",
            f"{market} / {tier}",
            f"{hyphen} / {market}",
            f"{market} / {hyphen}",
        )
    )
    # **And the RULE, when the cell is a blind side that has one.** Naming the
    # cell alone let one narrated rule vouch for its siblings: `low_major /
    # spread` appeared in a sentence about `always the favourite`, and that
    # silently covered `always home` and `always away`, which had also lost
    # their readings and which no document mentioned. Three retractions, one
    # sentence, two of them invisible.
    rule = cell.get("name")
    return cell_named and (rule in narration if rule else True)
