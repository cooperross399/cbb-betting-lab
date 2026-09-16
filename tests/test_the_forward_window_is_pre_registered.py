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

    examined, retracted_cells = _readings_across_every_record(S, looks)
    retracted = [key for key, _ in retracted_cells]
    recorded = _recorded_retractions()

    missing = sorted(set(retracted) - set(recorded))
    assert not missing, (
        f"{len(missing)} published reading(s) that today's correction retracts "
        f"are absent from {RETRACTIONS.name}:\n  "
        + "\n  ".join(" | ".join(key) for key in missing)
        + "\n\nA wider correction can only ever retract, so every registration "
        "has a cost and the cost is computable. State it there, with the count "
        "it was demonstrated at and the count it crossed, or do not make the "
        "registration."
    )

    # The numbers in the table, against the records they claim to describe.
    by_key = {key: cell for key, cell in retracted_cells}
    for key, stated in recorded.items():
        cell = by_key.get(key)
        if cell is None:
            continue
        assert abs(cell["value"] - stated["roi"]) < 5e-5, (
            f"{RETRACTIONS.name} states an ROI of {stated['roi']:+.2%} for "
            f"{' | '.join(key)}; the record holds {cell['value']:+.2%}."
        )
        assert cell["scored"] == stated["demonstrated_at"], (
            f"{RETRACTIONS.name} says that reading was demonstrated at "
            f"{stated['demonstrated_at']} hypotheses; its record was scored at "
            f"{cell['scored']}."
        )
        crossed = _crossing_point(S, cell)
        assert crossed == stated["crossed_at"], (
            f"{RETRACTIONS.name} says it crossed at {stated['crossed_at']}; "
            f"re-derived from the record it crosses at {crossed}."
        )

    surplus = sorted(set(recorded) - set(retracted))
    assert not surplus, (
        f"{len(surplus)} row(s) in {RETRACTIONS.name} name a reading that is "
        "NOT retracted at the ledger's current count:\n  "
        + "\n  ".join(" | ".join(key) for key in surplus)
        + "\n\nThis direction is the half that makes the other half mean "
        "something: without it the table could be pre-filled with every cell in "
        "the repository and would then accept any retraction in silence. A row "
        "here is a claim that a specific reading was withdrawn; if the reading "
        "still stands, the row is false."
    )


#: The hand-written ledger of readings the growing family has withdrawn.
RETRACTIONS = _REPO / "docs" / "retracted_readings.md"

#: Every record that publishes a verdict a person could act on.
#:
#: **`cbb_prop_grading.json` was missing and `cbb_forecast_skill.json` was
#: missing**, which is how four stale prop intervals reached the documents while
#: every guard ran green. A record that publishes a verdict belongs here; the
#: floors below make dropping one fail rather than quietly shrink the search.
#: **These are EXACT counts, not floors.** They were floors, set 14% under what
#: the records actually yield -- 795 readings against 682 -- so 113 published
#: readings could vanish with both tests green: twenty per cent of the
#: prop-grading record, four live demonstrated findings among them, or a walker
#: that quietly stopped descending into `pooled`. A coverage number that permits
#: a collapse is not a coverage number. When a record legitimately gains or loses
#: a reading this fails, and the commit that caused it says so.
SCORED_RECORDS = {
    "cbb_price_backtest.json": 225,
    "holdout/cbb_price_backtest.json": 224,
    "core_team_only/cbb_price_backtest.json": 69,
    "holdout/cbb_replication.json": 67,
    "cbb_prop_grading.json": 194,
    "cbb_forecast_skill.json": 43,
    "cbb_what_we_can_claim.json": 23,
}


#: The population each published record rests on, as a floor and never an
#: equality. A bought store only grows, so a published record's population can
#: only grow with it — and the day one of these goes DOWN, something has
#: replaced a standing measurement with a narrower one.
#:
#: THIS IS THE CHECK THAT WAS MISSING ON 2026-09-16. One run of the weekly loop
#: wrote its bounded single-season backtest over
#: `data/outputs/cbb_price_backtest.json`: `season_label` 2021-2026 -> 2026,
#: bets 191,053 -> 37,255, games 26,591 -> 4,927. It reported `Clean run` and
#: exited 0. The reading-count pin above caught it — 225 readings became 67 —
#: but only because the readings happened to be counted; nothing was watching
#: the POPULATION, and the forecast-skill record was narrowed in the same run
#: from the whole history to one season with no count to notice.
#:
#: Cross-checking the two records against each other would NOT have caught it:
#: they were narrowed together and therefore agreed. A floor is the shape that
#: works, because it compares the record to what the lab has already published
#: rather than to another record that can move at the same time.
#:
#: Raising a floor is a commit that says what was bought. Lowering one is the
#: thing this refuses.
POPULATION_FLOORS = {
    "cbb_price_backtest.json": {"bets_graded": 191_053, "games": 26_591, "days": 791},
    "holdout/cbb_price_backtest.json": {"bets_graded": 119_275, "games": 16_815},
    "core_team_only/cbb_price_backtest.json": {"bets_graded": 159_354, "games": 26_582},
}


def test_no_published_record_rests_on_a_smaller_population_than_it_did():
    """A published population never shrinks, and a bounded run must never
    overwrite a standing one.

    Mutation: point the weekly loop's backtest back at `data/outputs` and run
    it — RED here on `bets_graded`, within one run and before any document is
    re-rendered from the narrower record.
    """
    for relative, floors in POPULATION_FLOORS.items():
        path = _REPO / "data" / "outputs" / relative
        assert path.is_file(), (
            f"{relative} carries a population floor and is not on disk. A record "
            "that vanishes is not a record that got smaller, and it is not "
            "allowed to pass by being absent."
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        for field, floor in floors.items():
            actual = payload.get(field)
            assert isinstance(actual, int), (
                f"{relative} carries no integer `{field}`, so its population "
                "cannot be checked at all."
            )
            assert actual >= floor, (
                f"{relative} now rests on {actual:,} {field} and this lab has "
                f"published {floor:,}. A bought store only grows, so a published "
                "population can only grow with it: something has replaced a "
                "standing measurement with a narrower one. The weekly loop's "
                "bounded window is the way this happened before — it belongs in "
                "`data/drift/`, not here."
            )


def _key(record: str, cell: dict) -> tuple:
    """A reading's identity, structural rather than prose.

    Deliberately not a name to grep for. The rule before this one -- "the cell is
    named somewhere in one of two documents" -- was satisfiable by text written
    for a different record on a different occasion, and unsatisfiable altogether
    for a row with no market or no tier.

    **The key carries the leaf and the season, and without them it was not
    injective.** `block` was frozen at the top-level dict key and `tier` /
    `market` / `name` were inherited from ancestors, so every reading nested
    under one `markets` row -- its `discovery` cell, its `holdout` cell, each
    per-season cell -- collapsed to one key: 795 readings over 580 keys, 215 of
    them sharing. Both halves of the check compare SETS, so one row in the table
    discharged the obligation for every reading that shared its key, and the
    surplus half rejected a row only when none of the readings under its key was
    retracted. A retraction ledger whose keys collide is a ledger with blanks in
    it.

    Built from names, never from list indices. An index would be injective and
    would also break the table whenever a record re-rendered in a different
    order, which trains a reader to retype the key rather than read it. Block,
    leaf and season are all carried in the data.
    """
    return (
        record,
        cell.get("block") or "",
        cell.get("leaf") or "",
        str(cell.get("season") or ""),
        cell.get("tier") or "",
        cell.get("label") or "",
        cell.get("market") or "",
        cell.get("name") or "",
    )


def _cells(
    node,
    record_looks,
    block=None,
    leaf=None,
    season=None,
    tier=None,
    label=None,
    market=None,
    name=None,
):
    """Every scored reading in a record, AT ANY DEPTH.

    **The first version walked top-level lists only**, and the claim written
    beside it -- "reads every scored block of every published record" -- was
    therefore false in the commit that made it. `holdout/cbb_replication.json`
    keys its measurements one level down, inside `discovery` and `holdout`
    sub-dicts of each `markets` row, so its 32 markets contributed nothing and
    the record yielded 8 readings out of 67. One of the cells it could not see is
    a published `demonstrated deficit` that today's correction retracts -- the
    same cell the other guard's roster reaches by name. The check written to
    catch a blind spot had one, in the direction it had just been widened.
    """
    if isinstance(node, dict):
        tier = node.get("tier", tier)
        # `label` is carried SEPARATELY, never merged into `tier`. The
        # forecast-skill record keys a tier `label` while the prop-grading record
        # uses `label` for an advantage's name, so folding one into the other
        # disambiguated four readings and collided eighty-eight others.
        label = node.get("label", label)
        market = node.get("market", market)
        name = node.get("name", name)
        season = node.get("season", season)
        # `estimate` as well: a regression coefficient stores its point estimate
        # under that name, and 33 of them in cbb_forecast_skill.json were walked
        # past in silence -- neither counted nor keyed nor retractable -- while
        # that record's own prose calls one of them "the whole answer". Five are
        # published today as a demonstrated edge or deficit.
        value = node.get("roi", node.get("value", node.get("estimate")))
        if value is not None and node.get("standard_error") is not None:
            if node.get("enough_evidence", True):
                scored = node.get("looks", record_looks)
                if scored is not None:
                    yield {
                        "block": block,
                        "leaf": leaf,
                        "season": season,
                        "tier": tier,
                        "label": label,
                        "market": market,
                        "name": name,
                        "value": value,
                        "standard_error": node["standard_error"],
                        "scored": scored,
                    }
        for key, child in node.items():
            yield from _cells(
                child,
                record_looks,
                block if block else key,
                key if block else None,
                season,
                tier,
                label,
                market,
                name,
            )
    elif isinstance(node, list):
        for child in node:
            yield from _cells(
                child, record_looks, block, leaf, season, tier, label, market, name
            )


def test_the_roster_names_every_record_that_publishes_a_verdict():
    """Membership pinned, not just the counts.

    Both loops here are `for relative, floor in SCORED_RECORDS.items()`, so a
    record that is not a key is not looked at, not counted, and not missed.
    Setting a count to zero fails loudly; DELETING the line passes green -- a
    strictly stronger disarm than the one the counts were hardened against. And
    it is the same failure as the original: two records were missing from this
    roster, which is how four stale prop intervals reached the documents with
    every guard green. The counts were made unfakeable and the names were left a
    hand-maintained literal.
    """
    outputs = _REPO / "data" / "outputs"
    publishing = set()
    for path in sorted(outputs.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        looks = payload.get("looks") if isinstance(payload, dict) else None
        if any(True for _ in _cells(payload, looks)):
            publishing.add(str(path.relative_to(outputs)))
    named = set(SCORED_RECORDS)
    assert named == publishing, (
        "the roster and the records on disk that publish a scored reading "
        "disagree.\n"
        f"  publishes a verdict and is NOT on the roster: {sorted(publishing - named)}\n"
        f"  on the roster and publishes nothing: {sorted(named - publishing)}\n"
        "A record missing from this dict is not checked and does not complain."
    )


def _readings_across_every_record(S, looks):
    """(readings examined, the keys of those today's correction retracts)."""
    examined = 0
    retracted = []
    for relative, floor in SCORED_RECORDS.items():
        path = _REPO / "data" / "outputs" / relative
        assert path.is_file(), (
            f"{relative} is on this check's roster and is not on disk. "
            "Re-render it or take it off the roster in this commit."
        )
        payload = json.loads(path.read_text(encoding="utf-8"))
        cells = list(_cells(payload, payload.get("looks")))
        assert len(cells) == floor, (
            f"{relative} yields {len(cells)} scored readings; this check is "
            f"pinned to {floor}. If the record gained or lost a reading, say so "
            "in this commit and move the number. If it did not, coverage changed "
            "underneath the walker -- a renamed block, a moved record, a stop in "
            "the descent -- and a cost check that reads less passes more."
        )
        examined += len(cells)
        for cell in cells:
            half_then = S.bonferroni_z(cell["scored"]) * cell["standard_error"]
            half_now = S.bonferroni_z(looks) * cell["standard_error"]
            if abs(cell["value"]) > half_then and abs(cell["value"]) <= half_now:
                retracted.append((_key(relative, cell), cell))
    return examined, retracted


def _recorded_retractions() -> dict[tuple, dict]:
    """The hand-written retraction table, keyed and with its numbers kept.

    **Every column is parsed, because the ones that were not were unverified.**
    The first version sliced `fields[:5]` and threw the rest away -- so the ROI,
    the count a reading was demonstrated at and the count it crossed at were
    never compared to anything, while the guard's own failure message instructed
    an author to "state it there, with the count it was demonstrated at and the
    count it crossed". A column nothing reads is a column anyone can make up.
    """
    assert RETRACTIONS.is_file(), (
        f"{RETRACTIONS.name} is gone. It is the only place this lab states what "
        "a registration cost; without it nothing records a withdrawn reading."
    )
    dash = "\u2014"
    rows: dict[tuple, dict] = {}
    for line in RETRACTIONS.read_text(encoding="utf-8").splitlines():
        if not line.startswith("| `"):
            continue
        fields = [f.strip().strip("`") for f in line.strip().strip("|").split("|")]
        assert len(fields) == 11, (
            f"a row of {RETRACTIONS.name} has {len(fields)} columns, expected 11: "
            f"{line!r}. If the table's shape changed, change this parser with it "
            "rather than letting it read a prefix and ignore the rest."
        )
        blank = lambda value: "" if value == dash else value
        key = tuple(blank(field) for field in fields[:8])
        assert key not in rows, f"{RETRACTIONS.name} names {key} twice."
        rows[key] = {
            "roi": float(fields[8].rstrip("%")) / 100.0,
            "demonstrated_at": int(fields[9]),
            "crossed_at": int(fields[10]),
        }
    assert rows, (
        f"{RETRACTIONS.name} has no rows this parser recognises. Rows start "
        "`| ` followed by a back-ticked record path; if the table's shape "
        "changed, change this with it rather than letting it read nothing."
    )
    return rows


def _crossing_point(S, cell) -> int:
    """The first cumulative count at which this reading stops excluding zero."""
    for looks in range(cell["scored"], 1000):
        if abs(cell["value"]) <= S.bonferroni_z(looks) * cell["standard_error"]:
            return looks
    raise AssertionError(f"{cell!r} does not cross within 1000 hypotheses")
