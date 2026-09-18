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

import pandas as pd
import re
from datetime import date
from pathlib import Path

import pytest

from cbb_betting_lab import season
from cbb_betting_lab.reports.forecast_skill import bucket_label

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

    # WRITTEN BLIND, PROVED AGAINST THE CALENDAR RATHER THAN AGAINST TODAY.
    #
    # This read the LIVE `cbb_forward_evidence.json` and asserted it held zero
    # frozen opinions. That is a fact about 2026-09-10 being checked against
    # whatever the file happens to say now — so the first night of the season
    # freezes an opinion, the record gains rows, and this goes red. `Tests` is
    # the required check on protected main, so the lab's CI would have broken
    # on 2026-11-02: the one morning of the year when nobody can afford to be
    # reading a red build to find out whether it matters.
    #
    # The window cannot have been registered blind if it was registered before
    # its earliest season had played a game, and that is permanent. The opener
    # is read off the cached schedule rather than typed, so it tracks the
    # calendar the rest of the lab uses.
    earliest = min(int(s) for entry in _entries() for s in entry["seasons"])
    schedule = pd.read_parquet(
        _REPO / "tests" / "fixtures" / "real_data" / f"mbb_schedule_{earliest}.parquet",
        columns=["game_date"],
    )
    opener = schedule["game_date"].astype("string").str.slice(0, 10).min()
    assert stamped.isoformat() < opener, (
        f"the window was registered on {stamped.isoformat()}, and season "
        f"{earliest} opened on {opener}. A direction fixed after the first game "
        "of the window it predicts is not a prediction."
    )


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


def test_every_published_reading_has_a_key_of_its_own():
    """A retraction ledger addresses cells by key, so two cells may not share one.

    **This is the check `_key`'s own docstring describes and nothing enforced.**
    It says "a retraction ledger whose keys collide is a ledger with blanks in
    it", and the collision it was written about -- 795 readings over 580 keys --
    was fixed by hand and then left unguarded, so the next one arrived the same
    way. On 2026-09-17 the 48 restored realised-return readings landed on 8 keys:
    `cbb_forecast_skill.json` went 91 cells / 51 keys while every other record on
    the roster stayed injective, and 40 published readings became unaddressable.

    Both halves of `test_the_registration_cost_is_paid_by_everything_already_published`
    compare SETS. Under a collision `missing = set(retracted) - set(recorded)`
    empties as soon as ONE row exists for the key, `surplus` accepts that row
    while seven readings under it stay unstated, and `by_key` keeps only the last
    cell -- so the ROI, demonstrated-at and crossed-at columns are checked
    against a reading the row does not name. None of that is visible while the
    table is empty, which is exactly when it is cheapest to fix.

    Mutation: drop `band` from `_key`'s tuple (or delete the `claimed_edge`
    branch in `_cells`) and this is RED with the eight colliding keys named,
    while every other test in this file stays green.
    """
    collisions = {}
    for relative in SCORED_RECORDS:
        payload = json.loads(
            (_REPO / "data" / "outputs" / relative).read_text(encoding="utf-8")
        )
        seen: dict[tuple, int] = {}
        for cell in _cells(payload, payload.get("looks")):
            key = _key(relative, cell)
            seen[key] = seen.get(key, 0) + 1
        shared = {key: count for key, count in seen.items() if count > 1}
        if shared:
            collisions[relative] = shared
    assert not collisions, (
        "published readings share a retraction key, so the ledger cannot "
        "address them apart:\n"
        + "\n".join(
            f"  {relative}: {sum(s.values())} cells over {len(s)} key(s)\n"
            + "\n".join(f"    x{count}  " + " | ".join(key) for key, count in sorted(s.items()))
            for relative, s in sorted(collisions.items())
        )
        + "\n\nAdd the dimension that tells them apart to `_key` and to the "
        "table in docs/retracted_readings.md. Do NOT fix this by dropping "
        "cells: a reading that is not walked is not addressable either, and it "
        "is also not counted."
    )


#: The hand-written ledger of readings the growing family has withdrawn.
RETRACTIONS = _REPO / "docs" / "retracted_readings.md"


def _outside_every_fence(text: str) -> str:
    """The ledger's hand-written prose, every generated block removed.

    The generator owns the list of fences; a second copy here would be the
    second hand-maintained roster this file has already been rescued from.
    Loaded lazily so that importing this module does not import the generator,
    which imports this module back for its walker.
    """
    import importlib.util as _importlib

    spec = _importlib.spec_from_file_location(
        "_splice_for_the_retraction_ledger",
        _REPO / "scripts" / "splice_headline_table.py",
    )
    module = _importlib.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.outside_every_fence(text)

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
    # 225 -> 138 on 2026-09-17, and BOTH halves of that are deliberate.
    #
    # The neutral-court exclusion (#80) refused 48,873 side wagers the store
    # cannot orient, 15,207 of them bets. And the backtest declared its scope:
    # it measures TEAM markets, so the 12 prop markets left `all_opinions` and
    # `null_baseline` — blocks the record never published a prop cell from and
    # which were therefore computed over a universe a third larger than the
    # table they sit beside. The blind baseline went 280 readings -> 160.
    #
    # The published table did not move: 32 market-and-tier cells over the same
    # 10 markets, the same 26,591 games and the same 791 days, before and after.
    "cbb_price_backtest.json": 138,
    # 224 -> 137 on 2026-09-17, for the same two reasons as the record above:
    # the neutral-court exclusion refused 29,866 side wagers this cut cannot
    # orient (8,436 of them bets), and the prop markets left `all_opinions` and
    # `null_baseline` when the backtest declared its scope — 280 blind-baseline
    # readings to 160. The published table is unchanged at 32 cells.
    #
    # THIS COMMENT ALSO SAID "the held-out seasons still show ZERO demonstrated
    # deficits before and after", AND THAT IS FALSE TWICE OVER. This record
    # covers the DISCOVERY seasons — `holdout/` is the directory a replication
    # run writes to, not the held-out window — and it holds demonstrated
    # deficits, one of which arrived in #87. The tally is rendered per record
    # and per block by `scripts/splice_headline_table.py` into
    # `docs/retracted_readings.md`; it is not stated here, because a comment is
    # the one place in this repository where a figure has no guard at all and
    # this file was being used as a WITNESS for exactly such a figure.
    "holdout/cbb_price_backtest.json": 137,
    # UNCHANGED at 69, and that is the useful part. This cut carries only the
    # four core team markets, so it never held a prop reading to lose; the
    # scope declaration cost it nothing and its blind baseline stayed at 58.
    # Only the neutral-court exclusion touched it — 39,909 side wagers refused,
    # 13,360 of them bets — and a reading count that did not move while the
    # population did is the evidence that rows were excluded rather than cells
    # lost.
    "core_team_only/cbb_price_backtest.json": 69,
    # 67 -> 66 on 2026-09-17. The replication was re-scored against a model
    # that had just been given its roster evidence for the first time, and one
    # cell stopped carrying a scored reading. Its states are otherwise
    # unchanged — 0 replicated, 0 did not replicate, 0 reversed — so nothing
    # that was ever a finding moved; a cell simply fell below the sample that
    # earns a reading at all.
    "holdout/cbb_replication.json": 66,
    "cbb_prop_grading.json": 194,
    # 43 -> 91 on 2026-09-17. The record GAINED 48 readings and lost none, and
    # all 48 are the same leaf: `roi`, the realised return of one claimed-edge
    # bucket. They did not exist before because they were never computed. The
    # graded export's column projection dropped `profit_units` one line before
    # the write, `forecast_skill` writes an `roi` onto a bucket only when the
    # frame carries that column, and so every claimed-edge bucket on every tier
    # came back blank while the page said anti-predictiveness *"is not measured
    # here"* and that nothing in those buckets *"has been graded to a profit"*.
    # The archive had graded every one of them. The count breaks down as
    # 27 coefficients + 8 Brier-over-devigged + 8 Brier-over-raw = the old 43,
    # plus 48 realised returns = 91, so nothing that was previously read has
    # stopped being read.
    #
    # Those 48 are new readings in a family already corrected at the ledger's
    # cumulative count, and the check below re-derives every one of them at
    # today's count rather than at the count they were measured under, so the
    # cost of the restoration is paid here in the same commit that makes it.
    "cbb_forecast_skill.json": 91,
    # 23 -> 22 on 2026-09-17. Exactly one reading left this record, and it is
    # named rather than absorbed: `claims | high_major | spread_h1`. Its
    # neutral-court bets were refused by #80, its sample fell below the bar
    # that earns a reading at all, and a cell with no reading is not a cell
    # with a null one. It carried `no demonstrated edge`, so nothing that was
    # ever a finding was lost — but a published reading did disappear, and this
    # count is where that has to be said out loud.
    "cbb_what_we_can_claim.json": 22,
    # 0 -> 21 on 2026-09-18, and none of that is a re-measurement: this record
    # published 23 scored readings the whole time and the walker keyed its
    # point estimate under a name it did not read (`mean`). 21 rather than 23
    # because two of the 23 carry `enough_evidence: false` and a cell below the
    # bar is not a scored reading. None of the 21 is retracted at today's
    # count, which is luck and not a check -- it was never checked before.
    "cbb_ratings_fit.json": 21,
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
    # LOWERED ONCE, ON 2026-09-17, AND THE REASON IS THE WHOLE POINT OF THE
    # FLOOR. 191,053 -> 175,846 bets is not a store that shrank: it is 15,207
    # bets on neutral courts that this store cannot orient and now refuses
    # rather than grades, because `home` in a selection is the team the PRICE
    # PROVIDER designated home and `home_away` in the results table is ESPN's,
    # and on a neutral court those disagree about a third of the time.
    #
    # `games` and `days` are UNCHANGED at 26,591 and 791, which is the check
    # that this was an exclusion of rows and not a loss of coverage: the same
    # nights, the same fixtures, fewer gradeable side wagers within them.
    #
    # A future move of this number needs the same kind of sentence. The floor
    # exists so that a shrink has to be argued for, not absorbed.
    "cbb_price_backtest.json": {"bets_graded": 175_690, "games": 26_591, "days": 791},
    # LOWERED A SECOND TIME the same day, when the roster seam was connected.
    # The bets move by a few hundred and the GAMES move UP in two of the three
    # records (26,591 -> 26,622 and 26,582 -> 26,615) because roster evidence
    # lets the ratings price matchups the connectivity refusal used to decline.
    # A floor that only ever falls would have called that a loss; it is the
    # opposite, and it is why `games` is checked beside `bets_graded` rather
    # than instead of it.
    #
    # Both lowered once on 2026-09-17, by the neutral-court exclusion alone, and
    # both keep their `games` unchanged — the check that this removed gradeable
    # rows rather than coverage.
    #
    # THE BEFORE-AND-AFTER FIGURES THAT STOOD HERE DESCRIBED A STATE THE ROSTER
    # BELOW HAD ALREADY LEFT — the roster seam moved both records again in the
    # same day — and `docs/retracted_readings.md` was citing this comment as
    # the WITNESS for one of them, so a stale figure in a source comment was
    # excusing a stale figure on a published page. The floors below are the
    # figures; they are read from the records by the test, and a narration of
    # what they used to be belongs in the commit that moved them.
    "holdout/cbb_price_backtest.json": {"bets_graded": 110_682, "games": 16_812},
    "core_team_only/cbb_price_backtest.json": {"bets_graded": 145_739, "games": 26_582},
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

    **The key carries the claimed-edge BAND, and without it `cbb_forecast_skill`
    was not injective either.** The 48 realised-return readings restored on
    2026-09-17 are one per claimed-edge bucket, and a bucket carries no `market`
    and no per-bucket `name` -- every bucket of a tier reads `realised return`.
    So all eight buckets of a tier collapsed to one key: 91 cells over 51 keys,
    8 keys covering 48 cells, while every other record on the roster stayed
    injective (138/138, 137/137, 69/69, 66/66, 194/194, 22/22). Both halves of
    the cost check compare SETS, so one row in the table would have discharged
    the obligation for all eight buckets of a tier, `by_key` keeps only the last
    cell under a key so the ROI and crossing columns would be checked against a
    reading the row does not name, and 40 of the 48 would be unaddressable.

    The band is the bucket's own name on the page -- `-5% to +0%` -- rendered by
    `forecast_skill.bucket_label`, IMPORTED rather than re-spelled here. A
    second formatter would be free to label a bucket differently, and a key a
    reader cannot find in the report is a key nobody can use.
    """
    return (
        record,
        cell.get("block") or "",
        cell.get("leaf") or "",
        str(cell.get("season") or ""),
        cell.get("tier") or "",
        cell.get("label") or "",
        cell.get("market") or "",
        cell.get("band") or "",
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
    band=None,
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
        # A CLAIMED-EDGE BUCKET IS IDENTIFIED BY ITS BAND AND BY NOTHING ELSE.
        # It carries no market, and every bucket's `name` is `realised return`,
        # so without this the eight buckets of a tier keyed identically -- see
        # `_key`. `claimed_edge` is the field that makes a node a bucket; the
        # label is the producer's own, so the key a failure prints is the name
        # the report gives that row.
        if node.get("claimed_edge") is not None and "low" in node and "high" in node:
            band = bucket_label(node["low"], node["high"])
        # `estimate` as well: a regression coefficient stores its point estimate
        # under that name, and 33 of them in cbb_forecast_skill.json were walked
        # past in silence -- neither counted nor keyed nor retractable -- while
        # that record's own prose calls one of them "the whole answer". Five are
        # published today as a demonstrated edge or deficit.
        #
        # AND `mean`, WHICH IS THE SAME OMISSION ONE RECORD FURTHER ALONG.
        # `cbb_ratings_fit.json` is on the generated record census, is scored
        # at its own `looks`, and publishes 23 nodes carrying `standard_error`,
        # `adjusted_low`/`adjusted_high` and `survives_correction` -- and it
        # keys the point estimate `mean`, so this walker yielded ZERO cells
        # from it. Both documents said the cost check "compares this table
        # against every scored reading in every published record, in both
        # directions" while an entire published record contributed nothing,
        # and `test_the_roster_names_every_record_that_publishes_a_verdict`
        # could not report the gap because it derives its expectation by
        # calling this function: the roster and the walker agreed with each
        # other and neither could see the hole. That is this repository's own
        # lesson -- a roster only guards what it names -- with the walker in
        # the roster's place.
        value = node.get(
            "roi", node.get("value", node.get("estimate", node.get("mean")))
        )
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
                        "band": band,
                        "name": name,
                        "value": value,
                        "standard_error": node["standard_error"],
                        "scored": scored,
                        # CARRIED SO THAT NOBODY HAS TO WALK THE RECORD TWICE.
                        # `scripts/splice_headline_table.py` renders what a
                        # restatement did to a reading -- estimate, error,
                        # population and verdict, before and after -- and the
                        # population and the verdict are the two a reader
                        # cannot re-derive from the three above. A second
                        # walker for them would be a second answer to "what is
                        # a published reading", which is the shape this file
                        # has already been rescued from twice.
                        "bets": node.get("bets", node.get("rows")),
                        "verdict": node.get("verdict"),
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
                band,
                name,
            )
    elif isinstance(node, list):
        for child in node:
            yield from _cells(
                child,
                record_looks,
                block,
                leaf,
                season,
                tier,
                label,
                market,
                band,
                name,
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


def test_the_records_this_file_says_the_walker_cannot_classify_are_the_records_it_cannot_classify():
    """The disclosed limit is derived from the records, not typed on trust.

    **This is the half of the completeness claim that cannot be closed by
    fixing a walker.** `docs/retracted_readings.md` said until 2026-09-18 that
    the cost check reads "every scored reading in every published record, in
    both directions". One half of that was a bug -- the walker did not read
    `mean`, so `cbb_ratings_fit.json` contributed nothing -- and it is fixed.
    The other half is structural and permanent: a retraction is a claim about
    an interval's width, so a cell that publishes a `verdict` with no stored
    `standard_error` cannot be classified as retracted by any walker at all.

    A limit stated falsely is worse than no limit, and a limit stated TRULY and
    then left to rot is the same defect one render later. So the page names the
    records in that position and this derives the same set from disk. Add a
    verdict without an error to a record and the page must say so; give one of
    the five a standard error everywhere and the page must stop saying so.

    Mutation: delete `cbb_retention_probe.json` from the paragraph -> RED
    naming it as disclosed-too-few; add `cbb_price_backtest.json` to the
    paragraph -> RED naming it as disclosed-too-many.
    """
    outputs = _REPO / "data" / "outputs"

    def _nodes(node):
        if isinstance(node, dict):
            yield node
            for child in node.values():
                yield from _nodes(child)
        elif isinstance(node, list):
            for child in node:
                yield from _nodes(child)

    unclassifiable = set()
    for path in sorted(outputs.rglob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for node in _nodes(payload):
            if isinstance(node.get("verdict"), str) and not isinstance(
                node.get("standard_error"), (int, float)
            ):
                unclassifiable.add(path.relative_to(outputs).as_posix())
                break

    assert unclassifiable, (
        "no record on disk publishes a verdict without a standard error. That "
        "would be good news and it has never been true; far more likely the "
        "field was renamed and this check now passes by finding nothing."
    )

    prose = _outside_every_fence(RETRACTIONS.read_text(encoding="utf-8"))
    paragraph = next(
        (
            block
            for block in prose.split("\n\n")
            if "cannot be classified as retracted at all" in block
        ),
        None,
    )
    assert paragraph is not None, (
        f"{RETRACTIONS.name} no longer carries the paragraph that discloses "
        "which published verdicts this check cannot classify. The limit is "
        "permanent; deleting the sentence does not close it."
    )
    named = {
        found
        for found in re.findall(r"`([\w./-]+\.json)`", paragraph)
    }
    assert named == unclassifiable, (
        f"{RETRACTIONS.name}'s disclosed limit and the records on disk "
        "disagree.\n"
        f"  publishes a verdict the walker cannot classify and is NOT named: "
        f"{sorted(unclassifiable - named)}\n"
        f"  named and publishes no such verdict: {sorted(named - unclassifiable)}\n"
        "A limit stated falsely is worse than no limit."
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
    # THE ROWS ARE THE ONES UNDER THE HEADER, NOT EVERY BACK-TICKED ROW IN THE
    # FILE. This read `line.startswith("| `")` over the whole document, and the
    # document is mostly PROSE -- its own opening paragraph says the narration
    # is the part that survives when the table empties. The first narration
    # table anybody wrote with a back-ticked first cell was parsed as a
    # retraction row and the check died on its column count, which is a guard
    # failing on the file's intended use. Narrowing to the block under the
    # header cannot hide a missing retraction: a reading absent from the table
    # is absent whether it was ignored or never written, and `missing` fires
    # either way.
    #
    # WHAT THAT NARROWING COST, AND HOW IT IS PAID BACK BELOW. A row written
    # OUTSIDE the table was no longer read, so `surplus` could not reject a
    # false retraction claim typed under a prose heading -- a real loss of
    # reach, measured by an adversarial review that put a syntactically perfect
    # and entirely false 12-column row below the table and watched eight tests
    # pass. The reach is restored here without re-breaking on the narration:
    # a row anywhere in the document whose FIRST CELL NAMES A FILE UNDER
    # `data/outputs/` is a retraction claim and is read, wherever it sits. The
    # narration tables key their rows by a path INSIDE a record
    # (`selected / by_tier / high_major / fit / disagreement`), which is not a
    # file, so they are still prose to this parser -- and a row that looks like
    # a retraction of a real record can no longer hide by being written
    # somewhere else on the page.
    #
    # AND THE GENERATED FENCES ARE NOT PROSE EITHER. The retraction ledger now
    # carries a `retraction_history` block rendered from the records at each
    # revision that changed them, and its second table keys rows by a record
    # path. Those rows are not retraction claims -- they are a generated tally,
    # pinned byte-for-byte to a fresh render by
    # `test_the_committed_block_is_what_the_record_renders_to` -- and reading
    # them here died on the column count, which is a guard failing on the
    # file's intended use. The fence list lives in the generator, so stripping
    # it here cannot fall behind a fence somebody adds later.
    dash = "\u2014"
    rows: dict[tuple, dict] = {}
    lines = _outside_every_fence(
        RETRACTIONS.read_text(encoding="utf-8")
    ).splitlines()
    body: list[str] = []
    for index, line in enumerate(lines):
        if not line.startswith("| record | block |"):
            continue
        for candidate in lines[index + 2 :]:
            if not candidate.startswith("|"):
                break
            body.append(candidate)
        break
    outputs = _REPO / "data" / "outputs"
    for line in lines:
        if line in body or not line.startswith("| `"):
            continue
        named = line.strip().strip("|").split("|")[0].strip().strip("`")
        if named and (outputs / named).is_file():
            body.append(line)
    for line in body:
        if not line.startswith("| `"):
            continue
        fields = [f.strip().strip("`") for f in line.strip().strip("|").split("|")]
        assert len(fields) == 12, (
            f"a row of {RETRACTIONS.name} has {len(fields)} columns, expected 12: "
            f"{line!r}. If the table's shape changed, change this parser with it "
            "rather than letting it read a prefix and ignore the rest."
        )
        blank = lambda value: "" if value == dash else value
        key = tuple(blank(field) for field in fields[:9])
        assert key not in rows, f"{RETRACTIONS.name} names {key} twice."
        rows[key] = {
            "roi": float(fields[9].rstrip("%")) / 100.0,
            "demonstrated_at": int(fields[10]),
            "crossed_at": int(fields[11]),
        }
    # AN EMPTY TABLE IS A STATE, AND IT IS NOT THE SAME STATE AS A BROKEN ONE.
    #
    # This asserted rows outright, which was right while the table always had
    # some: reading zero rows out of a table full of them is a parser that has
    # stopped working, and it would make the cost check pass by finding nothing
    # to check. But on 2026-09-17 the last row legitimately left — the records
    # underneath were rebuilt three times in two days and every reading the
    # table named either came back or stopped existing — so "no rows" became a
    # true thing the file can say.
    #
    # The two are told apart by the HEADER. The table's header is still there
    # when the shape is intact and the body is empty; it is the first thing to
    # go when somebody rewrites the section. So the parser refuses a file with
    # no header and accepts one with a header and no body.
    text = RETRACTIONS.read_text(encoding="utf-8")
    header = (
        "| record | block | leaf | season | tier | label | market | band | rule |"
    )
    assert header in text, (
        f"{RETRACTIONS.name} has no table header this parser recognises, so "
        "reading zero rows out of it proves nothing. Rows start `| ` followed "
        "by a back-ticked record path; if the table's shape changed, change "
        "this parser with it rather than letting it read nothing."
    )
    return rows


def _crossing_point(S, cell) -> int:
    """The first cumulative count at which this reading stops excluding zero.

    **Searched from ONE, not from the count the record was scored at.** For a
    RETRACTED reading the two are the same answer by construction: a retracted
    reading still excludes zero at its own `scored`, `bonferroni_z` is
    increasing, so the first crossing at or above 1 is the first crossing at or
    above `scored`. `test_the_crossing_point_is_the_same_for_a_retracted_reading`
    pins that, because it is the property that makes this rewrite safe for the
    cost check, which calls this on retracted cells only.

    For a reading that is NOT retracted the two differ, and the from-`scored`
    answer is the misleading one: it returns `scored` itself, which reads as
    "crossed at 130" for a cell that was never demonstrated at 130. The
    retraction ledger's generated block prints this column for readings on both
    sides of a restatement, and a column that says "130" about a cell that
    never cleared the bar there is the sort of figure this file exists to stop
    publishing.
    """
    for looks in range(1, 1000):
        if abs(cell["value"]) <= S.bonferroni_z(looks) * cell["standard_error"]:
            return looks
    raise AssertionError(f"{cell!r} does not cross within 1000 hypotheses")


def test_the_crossing_point_is_the_same_for_a_retracted_reading():
    """The rewrite above is an identity on every reading the cost check uses.

    `_crossing_point` is called by
    `test_the_registration_cost_is_paid_by_everything_already_published` only
    on cells the retraction walk classified as retracted, and widening its
    search from `scored` down to 1 must not move any of those answers. Checked
    against every retracted reading in the tree AND against constructed cells,
    so it is not vacuous on a day when nothing is retracted.
    """
    from cbb_betting_lab import stats as S

    def from_scored(cell):
        for looks in range(cell["scored"], 1000):
            if abs(cell["value"]) <= S.bonferroni_z(looks) * cell["standard_error"]:
                return looks
        raise AssertionError("no crossing")

    payload = json.loads(_LEDGER.read_text(encoding="utf-8"))
    looks = len(payload["hypotheses"])
    _, retracted_cells = _readings_across_every_record(S, looks)

    built = [
        {"value": -0.04024, "standard_error": 0.01137, "scored": 95},
        {"value": -0.07485, "standard_error": 0.02198, "scored": 30},
        {"value": -0.06364, "standard_error": 0.01836, "scored": 62},
    ]
    for cell in built:
        assert abs(cell["value"]) > S.bonferroni_z(cell["scored"]) * cell["standard_error"], (
            "this fixture no longer excludes zero at its own count, so it is "
            "not a retracted reading and proves nothing about the identity"
        )
    for cell in built + [cell for _, cell in retracted_cells]:
        assert _crossing_point(S, cell) == from_scored(cell), (
            f"{cell!r} crosses at a different count depending on where the "
            "search starts, and the cost check compares this column against "
            "the retraction table."
        )
