"""Freezing an opinion before tip, settling it afterwards, and never the reverse.

**Forward evidence cannot be back-dated.** Historical prices can be bought at any
time — the provider retains NCAAB featured markets from 2020-11-16 and the full
catalogue from 2023-05-03, and they will still be there in March. A night that
was not frozen is gone permanently, and in this sport a night is up to **200
games** (the opening Monday of 2022-23, the largest slate in five cached
seasons) across **147 slate days** a season. That asymmetry is the entire reason
this organ is built before the models are worth anything, and the reason the
brief puts it third in the build order rather than last.

So this module is deliberately dull in the places it would be tempting to be
clever. Three idempotent stages — **Snapshot, Settle, Report** — each of which
can be run again on the same day without changing what the first run recorded.

## Why a snapshot is append-only *within* a day, not once a day

The sibling labs freeze once, because the NFL kicks off on a Sunday afternoon
and the NHL drops a puck at seven. This sport tips games every fifteen minutes
for twelve hours: an 11:00 Eastern morning game and a 23:00 Eastern West Coast
game are the same card. `docs/original_brief.md` is explicit — *"a noon tip and
an 11pm tip cannot share one freeze"* — and so is `gates.py`: **the first
opinion of the day for a given game is never retroactively replaced.**

Both halves of that are enforced here, and they pull in opposite directions:

* a later run **may add** a game the earlier run did not freeze, or the evening
  slate is never priced at all;
* a later run **may never re-price** a game the earlier run did freeze, or the
  ledger silently becomes a record of hindsight wearing a timestamp.

`write_snapshot` resolves them by keying on the **frozen selection key** and
appending only what is not already there. Nothing is ever rewritten. A key is
recomputed from the archived row's own columns through the *same injected*
`key_for` the caller used, so the two sides cannot drift.

## Why `key_for` is injected rather than imported

The NHL lab's join-vocabulary bug family reached five members and every one of
them was two hand-built copies of a key disagreeing (`selection.py` lists them).
Importing `selection_key` in two places is better than hand-building it in two
places, and it is still two places. Here the probability map and the snapshot
are handed **one callable**, so they agree on the key by construction rather
than by both happening to import the same helper and pass it the same arguments.

## The columns that exist because a blank and a zero are different claims

* **`line`** is `None` for a moneyline and is never coerced to `0.0`. A pick'em
  is a real line of zero; "there is no line" is not. `selection.normalise_line`
  already refuses that coercion and this file refuses it again on the CSV round
  trip, which is where it would actually happen: an empty cell reads back as
  float NaN, and NaN is not None, so a moneyline frozen at noon looked *unfrozen*
  at four o'clock and got re-priced. That is pinned by a test.
* **`calibrated_probability`** is **blank** when the market has no calibration
  map, and never a copy of the raw number. "No map" and "calibrates to itself"
  are different statements about the model, they are indistinguishable a year
  later if both are written as the same float, and only one of them is true.
  Calibration cannot be back-dated either, so it is frozen from the first game
  day or it is never known for that day.
* **`prior_weight`** — how much of this price came from the November preseason
  prior rather than from this season's own games. CBB-specific and required:
  November is a prior, not a fit (`verdicts.november_prior_schedule`), and
  without this column a November number can be read as a February one a season
  later with nothing in the record to contradict it. Missing stays **blank**,
  never `0.0`: zero is the substantive claim that none of the price came from
  the prior, and that claim must not be manufactured for a game in November.
* **`tier`** — high_major / mid_major / low_major / unplaced, frozen at price
  time. **No pooled headline across the whole of Division I is ever reported**,
  so the tier has to be knowable at settle time, and a tier recomputed later
  from a table that has since moved is not the tier the price was made under.
  The caller decides how to place a cross-tier game; this module never derives
  it, because deriving it here *and* in the model is two copies of one rule.
* **`verdicts_in_force`** — which recorded policies were shipping when the
  opinion was frozen. A ledger row whose model cannot be reconstructed is an
  anecdote.

## Settling: two independent sources of "done", and one index

Idempotence is guarded twice on purpose. The `.settled` sidecar says a snapshot
has been through the pass; the ledger's own `snapshot_date` set says its rows
arrived. Neither alone is sufficient — **a snapshot that settled zero rows
leaves no ledger trace at all** and would re-settle forever on the marker's
absence, and a marker lost to a cleanup would re-append a day the ledger already
holds. The marker is a **sidecar rather than a rename** because a snapshot's
filename is part of the evidence, and evidence does not get renamed.

A day settles **atomically**: every row reaches a terminal outcome or the day
waits. Half a day in the ledger would break the second idempotence source, since
`snapshot_date in ledger` could then mean either "done" or "partly done".

The game index is built **once per pass**, not per row. `data/processed` holds
**1,493,589 player-game rows**, 94,194 team-game rows and 45,391 game-segment
rows; a few thousand snapshot rows scanned against that per row turns a second
into an hour, and a settle step that times out is a settle step that silently
stops accumulating the only evidence that cannot be re-bought.

The join is on the **slate date derived from `commence_time`**, never on the
snapshot's own filename. The NHL lab discarded **69% of every price it bought**
by joining a UTC date against a league date, and the survivors were
systematically the afternoon games — the exact subset whose absence looks like a
quiet market rather than a bug. A row whose commence time is missing or
unparseable has no slate date at all and is `UNSETTLEABLE` immediately rather
than waiting: there is no future in which a key that does not exist begins to
join.

## Patience, and what it refuses to do

`PATIENCE_DAYS` = 14. hoopR publishes a season's box scores only once its first
games are played (`data.hoopr.NotPublishedYet`) and restates assets afterwards
(`check_for_restatements`), so a result arriving late is ordinary and a result
arriving never is not. Fourteen days is long enough to cover the publication
cadence and short enough that a genuinely missing game is reported rather than
sat on. **A game with no final result inside that window is `UNSETTLEABLE` —
never guessed, never assumed void, never dropped.** Ambiguity falls on the
not-settled side, always.

Player resolution obeys the same rule and `providers/team_names.py`'s: candidates
are filtered to the two teams in the fixture, **more than one candidate is
`UNSETTLEABLE`** (ambiguous, never a coin flip) and **zero candidates is `VOID`**
(he never entered the game). The football lab's note applies unchanged: *"a lone
candidate on the wrong team is a void, not a match."*

## Reporting: four guards, and the direction is not decoration

Every row of every table passes through `row_verdict`, in this order:

1. a market on the settlement-suspect list is **not evidence**, at any n;
2. below the pre-declared floor it is **not enough evidence**, with its n;
3. an interval including zero is **no demonstrated edge**, in those words;
4. an interval excluding zero says **positive** or **negative**.

Guard four exists because the NHL lab's claims document announced *"at least one
result survived the correction and then replicated"* about a market returning
**−6.6%**: its headline predicate tested measured + survives-correction +
replicated and never read the sign. It had replicated a **loss**. The one
document whose job is to stop a number being misread must not be the thing
misreading it, and `tests/test_the_headline_reads_the_sign.py` pins the
arithmetic while this file pins the prose.

The family correction comes from the experiment ledger's **cumulative** count,
never this week's table — *"a search that runs every week is not twelve tests,
it is twelve tests a week, forever."* When no count is supplied the report says
so, loudly, rather than quietly correcting for one look.

Intervals are `stats.interval_two_way`: clustered by game **and** by day, wider
of the two. The football lab's forward ledger clustered wrong and its intervals
came out **10.3× too narrow** on the one report that grows all season.

And the split that stops a table flattering itself: **OPINIONS** (every settled
row) and **BETS** (the rows clearing the declared edge threshold) are reported
separately and always both, because mixing them flatters whichever is worse. A
player-prop row is an opinion and can never be a bet — nothing reaches
`Availability.CONFIRMED` in this sport, ESPN's men's-college-basketball injuries
endpoint is permanently empty and the conference reports cover ~115 of 365 teams
in conference games only — so it is priced, frozen and settled, and reported in
the gate's own words. **That is not a pass, an avoid, or a no-value call.**
"""

from __future__ import annotations

import json
import re
import unicodedata
from collections.abc import Callable, Iterable, Mapping
from typing import ClassVar
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pandas as pd

from cbb_betting_lab import markets as markets_registry
from cbb_betting_lab import season, stats, stores
from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.conferences import Tier
from cbb_betting_lab.config import DATA_DIR
from cbb_betting_lab.selection import (
    AWAY,
    AWAY_OVER,
    AWAY_UNDER,
    FULL_GAME,
    HOME,
    HOME_OVER,
    HOME_UNDER,
    normalise_line,
)
from cbb_betting_lab.settlement import Outcome, Settled, settle

# The one American-odds-to-profit conversion in this repository, imported
# rather than copied. It is private to `stores`, and reaching for it is still
# the lesser evil: a second copy is the football lab's `_bonferroni_factor`
# defect in miniature — four implementations, one of them carrying a rounded
# constant, and the direction two copies drift in is never the conservative
# one. A rename upstream breaks this import loudly at import time; a duplicate
# would drift silently, and +150 beating −110 is exactly the kind of thing a
# drifted copy gets backwards.
from cbb_betting_lab.stores import _decimal_payout as decimal_payout


#: Where a day's frozen opinions live, under `archive_dir`.
SNAPSHOT_DIRNAME = "priced_snapshots"

#: The append-only settled ledger. Competition-prefixed, like every output, so
#: a second competition could never write over this one's evidence.
LEDGER_FILENAME = "cbb_forward_evidence.csv"
REPORT_MARKDOWN_FILENAME = "cbb_forward_evidence.md"
REPORT_JSON_FILENAME = "cbb_forward_evidence.json"

#: Default archive root. `config.py` does not name one and this module does not
#: edit `config.py`; every caller may pass its own, and the tests always do.
ARCHIVE_DIR = DATA_DIR / "archive"

#: How long a game may go without a final result before its frozen opinions are
#: `UNSETTLEABLE`. See the module docstring: hoopR publishes late and restates,
#: so a result arriving late is ordinary — and a result arriving never is not.
PATIENCE_DAYS = 14

#: The edge a frozen opinion must clear to be counted as a **bet** rather than
#: an opinion. Declared here, in advance, and reported alongside the
#: all-opinions figure so the choice cannot flatter either cut. Moving it after
#: seeing a number is the defect this entire repository is arranged against.
BET_EDGE_THRESHOLD = 0.02

#: Markets whose settlement rule this lab cannot read from the book's rulebook.
#: Second-half wagers settle **including overtime** at most US books and not at
#: all of them (`markets.SECOND_HALF_INCLUDES_OVERTIME`), which is a book rule
#: rather than a fact about basketball. Offered for callers to pass as
#: `settlement_suspects`; the default suspect set is empty, because deciding on
#: a lab's behalf which of its own numbers are not evidence is the caller's job.
#: The report footnotes these rows whether or not they were passed.
SETTLEMENT_AMBIGUOUS_MARKETS: frozenset[str] = frozenset(
    m.key for m in markets_registry.MARKETS if m.segment == "h2"
)

#: One file per snapshot day. Frozen before tip and never rewritten.
SNAPSHOT_COLUMNS: tuple[str, ...] = (
    "snapshot_date",
    "commence_time",
    "event_id",
    "home_team",
    "away_team",
    "market",
    "segment",
    "player",
    "selection",
    "line",
    "american_odds",
    "book",
    "model_probability",
    "edge",
    "calibrated_probability",
    "calibrated_edge",
    "prior_weight",
    "tier",
    "verdicts_in_force",
)

#: What settlement adds. Nothing frozen is ever changed by it.
SETTLEMENT_COLUMNS: tuple[str, ...] = (
    "settled_at",
    "outcome",
    "actual",
    "profit_units",
)

LEDGER_COLUMNS: tuple[str, ...] = SNAPSHOT_COLUMNS + SETTLEMENT_COLUMNS

#: What makes two ledger rows the same settled opinion. **No timestamp** — the
#: NHL lab deduplicated its price store on the whole row, timestamps included,
#: and every interval came out root-two too narrow with nothing looking wrong.
LEDGER_IDENTITY: tuple[str, ...] = (
    "snapshot_date",
    "event_id",
    "market",
    "segment",
    "player",
    "selection",
    "line",
    "book",
)

#: Suffix of the sidecar that says a snapshot has been through the settle pass.
#: A sidecar rather than a rename: the snapshot's own name is evidence.
SETTLED_MARKER_SUFFIX = ".settled"

#: Which team-games row a selection has to be settled from. **Every quantity in
#: `cbb_team_games.csv` is signed for its own team**, so settling a home wager
#: from the away row negates the margin and swaps the team total — a plausible
#: number, the wrong bet, and nothing raises. `settlement._row_is_the_named_side`
#: refuses the wrong row rather than flipping it, and refusing is only useful if
#: this side of the join hands it the right one. A bare `over`/`under` is a game
#: or half **total**, which is symmetric and does not consult the side at all.
_ROW_FOR_SELECTION: dict[str, str] = {
    HOME: "home",
    HOME_OVER: "home",
    HOME_UNDER: "home",
    AWAY: "away",
    AWAY_OVER: "away",
    AWAY_UNDER: "away",
}

#: The two markets whose `game` argument is a `cbb_game_segments.csv` row
#: rather than a team-games row: they settle on who scored the first basket,
#: which lives in the segments table.
_SEGMENT_SETTLED: frozenset[str] = frozenset(
    {"player_first_basket", "player_first_team_basket"}
)

#: The literal a report prints when an edge exists but cannot be taken. From
#: the brief: *"a soft number you cannot bet is not an edge."*
NOT_REACHABLE = "not reachable"


class SnapshotDateError(ValueError):
    """A snapshot was offered under a name that is not a slate day.

    Raised rather than normalised. A day of frozen opinions filed under an
    unparseable name is a day nothing will ever look for again, and this is the
    one kind of evidence that cannot be re-bought.
    """


class SnapshotKeyError(RuntimeError):
    """An already-frozen row could not be re-keyed by the injected `key_for`.

    Raised rather than treated as unknown, because "unknown" is the unsafe
    direction here: a row this run cannot key is a row it cannot tell apart from
    an unfrozen game, and appending anyway would re-price an opinion that was
    frozen hours earlier. The first opinion of the day for a given game is never
    retroactively replaced, so the run stops instead.
    """


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------


def snapshot_dir(archive_dir: Path | str) -> Path:
    return Path(archive_dir) / SNAPSHOT_DIRNAME


def snapshot_path(archive_dir: Path | str, snapshot_date: str) -> Path:
    return snapshot_dir(archive_dir) / f"{_valid_day(snapshot_date)}.csv"


def marker_path(snapshot: Path | str) -> Path:
    """The `.settled` sidecar for a snapshot, beside it and never over it."""
    target = Path(snapshot)
    return target.with_name(target.name + SETTLED_MARKER_SUFFIX)


def snapshot_files(archive_dir: Path | str) -> list[Path]:
    """Every snapshot in the archive, oldest first. Markers are not snapshots."""
    directory = snapshot_dir(archive_dir)
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.csv") if p.is_file())


def _valid_day(value: object) -> str:
    text = str(value or "").strip()
    try:
        parsed = date.fromisoformat(text)
    except (TypeError, ValueError) as exc:
        raise SnapshotDateError(
            f"{value!r} is not a slate day (YYYY-MM-DD). A day of frozen "
            "opinions filed under a name nothing can parse is a day nothing "
            "will look for again, and forward evidence cannot be re-bought."
        ) from exc
    return parsed.isoformat()


# --------------------------------------------------------------------------
# The arithmetic that turns a price and a probability into an opinion
# --------------------------------------------------------------------------


def expected_value(probability: object, american_odds: object) -> float | None:
    """Expected profit per unit staked at this price. `None`, never `0.0`.

    One definition of "edge" in this repository, so two reports cannot disagree
    about what the word means: `p·(1 + payout) − 1`, where `payout` is profit per
    unit at the frozen American price. A missing probability or an unreadable
    price yields `None` — an absent opinion is not an opinion of zero, and every
    caller here treats the two as different.
    """
    p = _as_float(probability)
    if p is None:
        return None
    payout = decimal_payout(american_odds)
    if payout == float("-inf"):
        return None
    return p * (1.0 + payout) - 1.0


def profit_units(outcome: object, american_odds: object) -> float | None:
    """Realised profit per unit staked, or `None` when it cannot be known.

    `None` for `UNSETTLEABLE`, and `None` for a win at a price this lab cannot
    read — a won bet whose payout is unknown is not a won bet worth zero, and
    writing `0.0` there would fabricate a number, which is the one thing the
    honesty rules forbid outright.
    """
    state = _outcome_value(outcome)
    if state in {Outcome.PUSH.value, Outcome.VOID.value}:
        return 0.0
    if state == Outcome.LOST.value:
        return -1.0
    if state != Outcome.WON.value:
        return None
    payout = decimal_payout(american_odds)
    return None if payout == float("-inf") else float(payout)


def _outcome_value(outcome: object) -> str:
    if isinstance(outcome, Outcome):
        return outcome.value
    return season.clean_text(outcome)


def _as_float(value: object) -> float | None:
    """A float, or None. Empty cells, NaN and the string `"nan"` are all None."""
    text = season.clean_text(value)
    if not text:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    return None if number != number else number


def _blank(value: object) -> object:
    """`pd.NA` for a missing number, so a blank cell stays blank on write."""
    return pd.NA if value is None else value


# --------------------------------------------------------------------------
# Stage one: freeze
# --------------------------------------------------------------------------


def _frozen_row(record: Mapping) -> SimpleNamespace:
    """A price row normalised so `key_for` sees the same values on both sides.

    This is the whole defence against the CSV round trip. An empty `line` reads
    back as float NaN, and `NaN is not None`, so the key built from an archived
    moneyline would differ from the key built from the same live moneyline — and
    a row already frozen at noon would look unfrozen at four o'clock and be
    re-priced. `player` gets `clean_text` for the fifth member of the NHL lab's
    join-vocabulary family: NaN is truthy, so `str(x or "")` yields the literal
    string `"nan"`, which matches nothing forever.
    """
    return SimpleNamespace(
        event_id=season.clean_text(record.get("event_id")),
        commence_time=season.clean_text(record.get("commence_time")),
        home_team=season.clean_text(record.get("home_team")),
        away_team=season.clean_text(record.get("away_team")),
        market=season.clean_text(record.get("market")),
        segment=season.clean_text(record.get("segment")) or FULL_GAME,
        player=season.clean_text(record.get("player")),
        selection=season.clean_text(record.get("selection")),
        line=normalise_line(record.get("line")),
        american_odds=_as_float(record.get("american_odds")),
        book=season.clean_text(record.get("book")),
        price_survived=record.get("price_survived"),
    )


def _records(prices: pd.DataFrame | Iterable[Mapping]) -> list[dict]:
    if isinstance(prices, pd.DataFrame):
        return prices.to_dict("records")
    return [dict(row) for row in prices]


def _verdict_text(verdicts_in_force: object) -> str:
    """The policies in force, frozen as text. A string is kept verbatim."""
    if verdicts_in_force is None:
        return ""
    if isinstance(verdicts_in_force, str):
        return verdicts_in_force.strip()
    if isinstance(verdicts_in_force, Mapping):
        return "|".join(sorted(str(k) for k, v in verdicts_in_force.items() if v))
    return "|".join(sorted(str(v) for v in verdicts_in_force))


def _lookup(mapping: Mapping | None, key, event_id):
    """A per-row value keyed by the frozen key, or failing that by event id.

    Both are supported because the two natural units differ: a calibration or a
    tier is a property of the game, while a caller that already has a key-keyed
    map should not have to rebuild it.
    """
    if not mapping:
        return None
    if key in mapping:
        return mapping[key]
    if event_id and event_id in mapping:
        return mapping[event_id]
    return None


def write_snapshot(
    prices: pd.DataFrame | Iterable[Mapping],
    probabilities: Mapping,
    *,
    key_for: Callable[[object], object],
    verdicts_in_force: object,
    snapshot_date: str,
    archive_dir: Path | str,
    calibration: Mapping[str, Callable[[float], float]] | None = None,
    prior_weights: Mapping | None = None,
    tiers: Mapping | None = None,
) -> Path | None:
    """Freeze today's opinions. Append-only within the day; never a re-price.

    Returns the snapshot path when rows were **added**, and `None` when a
    snapshot already stands for that day and holds every opinion offered — so
    the return value answers "was anything frozen just now", which is the
    question a nightly caller actually has. A later run that brings a game the
    earlier run could not price (the evening slate, priced after the morning
    card) writes those rows and returns the path; the morning's rows are not
    read, not recomputed and not touched.

    `key_for` is a callable taking a row with attribute access, exactly as
    `selection.selection_key` expects — the intended shape is::

        key_for = lambda row: selection_key(
            row, market=row.market, selection=row.selection,
            line=row.line, competition=CBB, segment=row.segment,
        )

    It is injected rather than imported so this function and the probability map
    agree on the key by construction. It is applied to the **already-archived**
    rows too, through the same normalisation, which is what makes "already
    frozen" a property of the key rather than of the file's bytes.

    `probabilities` maps that key to a model probability. **An absent key is no
    modelled opinion, not a probability of zero**, and the row is still frozen
    with a blank probability — the price itself is evidence, and it is what
    makes reachability and closing-line movement measurable later.

    `calibration` maps a market key to its calibration function. A market with
    no entry gets a **blank** `calibrated_probability`, never a copy of the raw
    one. `prior_weights` and `tiers` are looked up by frozen key or event id;
    a missing prior weight stays blank, and a missing tier is `unplaced`, which
    is a real state (`conferences.Tier.UNPLACED`) reported separately rather
    than folded into a tier's number.
    """
    day = _valid_day(snapshot_date)
    target = snapshot_path(archive_dir, day)
    verdict_text = _verdict_text(verdicts_in_force)

    stood = target.is_file()
    existing = stores.read_store(target, columns=SNAPSHOT_COLUMNS)
    already: set = set()
    for record in existing.to_dict("records"):
        try:
            already.add(key_for(_frozen_row(record)))
        except Exception as exc:  # noqa: BLE001 - re-raised, never swallowed
            raise SnapshotKeyError(
                f"A row already frozen in {target.name} cannot be re-keyed by "
                "the injected key_for. Refusing to append: without a key this "
                "run cannot tell an unfrozen game from a re-price, and the "
                "first opinion of the day for a game is never replaced."
            ) from exc

    rows: list[dict] = []
    seen_this_run: set = set()
    for record in _records(prices):
        row = _frozen_row(record)
        key = key_for(row)
        if key in already or key in seen_this_run:
            continue
        seen_this_run.add(key)

        probability = (
            _as_float(probabilities.get(key)) if probabilities is not None else None
        )
        edge = expected_value(probability, row.american_odds)

        mapper = (calibration or {}).get(row.market)
        calibrated = None
        if mapper is not None and probability is not None:
            calibrated = _as_float(mapper(probability))
        calibrated_edge = expected_value(calibrated, row.american_odds)

        tier = _lookup(tiers, key, row.event_id)
        rows.append(
            {
                "snapshot_date": day,
                "commence_time": row.commence_time,
                "event_id": row.event_id,
                "home_team": row.home_team,
                "away_team": row.away_team,
                "market": row.market,
                "segment": row.segment,
                "player": row.player,
                "selection": row.selection,
                "line": _blank(row.line),
                "american_odds": _blank(row.american_odds),
                "book": row.book,
                "model_probability": _blank(probability),
                "edge": _blank(edge),
                "calibrated_probability": _blank(calibrated),
                "calibrated_edge": _blank(calibrated_edge),
                "prior_weight": _blank(_as_float(_lookup(prior_weights, key, row.event_id))),
                "tier": _tier_value(tier),
                "verdicts_in_force": verdict_text,
            }
        )

    if not rows:
        if not stood:
            # A run that froze nothing still leaves a record that it ran.
            # "The pipeline had no opinion tonight" and "the pipeline did not
            # run tonight" must never look the same — two different things
            # reported identically is the sibling labs' most expensive class of
            # mistake, and here the second one costs a night of evidence that
            # cannot be re-bought. It still returns None: nothing was frozen.
            target.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(columns=list(SNAPSHOT_COLUMNS)).to_csv(
                target, index=False, lineterminator="\n"
            )
        return None

    frame = pd.DataFrame(rows, columns=list(SNAPSHOT_COLUMNS))
    target.parent.mkdir(parents=True, exist_ok=True)
    combined = (
        frame
        if existing.empty
        else pd.concat([existing, frame], ignore_index=True)[list(SNAPSHOT_COLUMNS)]
    )
    combined.to_csv(target, index=False, lineterminator="\n")
    return target


def _tier_value(tier: object) -> str:
    if isinstance(tier, Tier):
        return tier.value
    text = season.clean_text(tier)
    return text or Tier.UNPLACED.value


def read_snapshot(path: Path | str) -> pd.DataFrame:
    """A snapshot, read leniently. For readers and renderers only.

    An unparseable file comes back as an **empty frame** here, which is the
    right answer for anything that only wants to show what it can find. It is
    the wrong answer for the settle pass — see `read_snapshot_strictly`.
    """
    return stores.read_store(Path(path), columns=SNAPSHOT_COLUMNS)


def read_snapshot_strictly(path: Path | str) -> pd.DataFrame:
    """A snapshot, or `CorruptStoreError`. Never a silently empty frame.

    The lenient read is a trap for a caller that is about to *decide something
    permanent* about the day. A night of frozen opinions read as zero rows is
    settled as a night with nothing in it, the `.settled` sidecar is written,
    and the day is closed forever — while the prices those opinions were frozen
    at are gone and nothing can re-make them. That is the football lab's defect
    16 arriving one layer above the workflow's temp-then-move guard.

    So the settle pass reads through here, and a file it cannot parse leaves the
    day **unsettled** rather than settled-as-empty. A day left open is a day a
    restored or repaired file can still be graded on; a day marked done is not.
    """
    return stores.read_store(Path(path), columns=SNAPSHOT_COLUMNS, for_append=True)


# --------------------------------------------------------------------------
# Stage two: settle
# --------------------------------------------------------------------------


_PERSON_PUNCT = re.compile(r"[^a-z0-9 ]+")
_PERSON_SPACE = re.compile(r"\s+")
#: Generational suffixes appear on one side of this join and not the other.
_PERSON_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "v"})


def normalise_person(name: object) -> str:
    """A player's name reduced to identity, for candidate lookup only.

    Deliberately separate from `providers.team_names.normalise`, which expands
    `st` to `saint` and strips `college` — right for schools and wrong for
    people. Conservative in the same direction as its sibling: this only ever
    produces a *candidate list*, and the decision made from that list is the
    conservative one — more than one candidate is ambiguous and settles nothing.
    """
    text = str(name or "")
    if not text or text.strip().lower() == "nan":
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = _PERSON_PUNCT.sub(" ", text.casefold())
    words = [w for w in text.split() if w not in _PERSON_SUFFIXES]
    return _PERSON_SPACE.sub(" ", " ".join(words)).strip()


@dataclass
class SettlementResult:
    """What the settle pass did, and — more usefully — what it did not do.

    Every field exists so silence stays legible. A pass that settles nothing
    must say whether it saw no snapshots, saw only settled ones, or is waiting
    on box scores, because those three are the difference between a healthy
    night, a finished night, and a pipeline that stopped freezing.
    """

    #: The row-level counters, named once so a caller can snapshot and restore
    #: them without listing them again. A field added to this dataclass and not
    #: to this tuple would silently stop being rolled back on a waiting day,
    #: which is the defect this exists to close returning by another door.
    ROW_COUNTERS: ClassVar[tuple[str, ...]] = (
        "rows_settled",
        "rows_void",
        "rows_unsettleable",
        "rows_without_a_price",
        "rows_without_a_fixture",
        "rows_ambiguous_player",
        "rows_futures_deferred",
    )

    snapshots_seen: int = 0
    snapshots_settled: int = 0
    snapshots_waiting: int = 0
    #: Rows that reached a graded outcome: won, lost or pushed.
    rows_settled: int = 0
    rows_void: int = 0
    rows_unsettleable: int = 0
    #: Settled, but at a price this lab cannot read — counted, and excluded from
    #: every ROI rather than being given a fabricated profit of zero.
    rows_without_a_price: int = 0
    #: Frozen opinions on a fixture no game in the results tables matches.
    rows_without_a_fixture: int = 0
    #: Player rows whose name matched more than one athlete on the two teams.
    rows_ambiguous_player: int = 0
    #: Futures, which settle on the tournament months later and are deferred
    #: here rather than guessed. Never described as a pass or an avoid.
    rows_futures_deferred: int = 0
    #: Snapshot days still inside the patience window, named.
    waiting_days: tuple[str, ...] = ()
    #: Rows READ from the snapshots this pass took up, before any of them was
    #: graded. Independent of every counter above, which is the whole point: the
    #: three outcome counters sum to `rows_seen` by construction and so cannot
    #: disagree with it, while this one comes off the files on disk and can.
    rows_read: int = 0
    #: Snapshots that could not be parsed. They are NOT settled, NOT marked and
    #: NOT graded — a broken file is a day needing a human, not a day with no
    #: opinions, and the two must never be recorded as the same thing.
    snapshots_unreadable: int = 0
    #: Those days, named. A count alone tells an operator nothing to go and look
    #: at, and this is the one fault here that no rerun repairs.
    unreadable_days: tuple[str, ...] = ()
    ledger_rows: int = 0
    #: Exceptions raised inside `settle`, by message. Counted into
    #: `rows_unsettleable` and surfaced, never swallowed.
    settlement_errors: dict[str, int] = field(default_factory=dict)

    @property
    def rows_seen(self) -> int:
        return self.rows_settled + self.rows_void + self.rows_unsettleable

    def summary_line(self) -> str:
        if not self.snapshots_seen:
            return (
                "0 snapshots found. Nothing was frozen, so nothing can settle — "
                "and a night that was not frozen is a night of out-of-sample "
                "evidence gone permanently. Check that the freeze step ran."
            )
        parts = [
            f"{self.snapshots_seen:,} snapshots seen, "
            f"{self.snapshots_settled:,} settled, "
            f"{self.snapshots_waiting:,} waiting"
            + (
                f" ({', '.join(self.waiting_days)}, inside the "
                f"{PATIENCE_DAYS}-day patience window)"
                if self.waiting_days
                else ""
            )
            + (
                f", {self.snapshots_unreadable:,} unreadable and left UNSETTLED "
                f"({', '.join(self.unreadable_days)})"
                if self.snapshots_unreadable
                else ""
            )
            + ".",
            f"{self.rows_seen:,} rows: {self.rows_settled:,} settled, "
            f"{self.rows_void:,} void, {self.rows_unsettleable:,} unsettleable.",
        ]
        reasons = []
        if self.rows_without_a_fixture:
            reasons.append(
                f"{self.rows_without_a_fixture:,} matched no game in the results "
                f"tables within {PATIENCE_DAYS} days"
            )
        if self.rows_ambiguous_player:
            reasons.append(
                f"{self.rows_ambiguous_player:,} named more than one athlete on "
                "the two teams (ambiguous, never a coin flip)"
            )
        if self.rows_futures_deferred:
            reasons.append(
                f"{self.rows_futures_deferred:,} are futures, which settle on the "
                "tournament months later and are deferred here rather than "
                "guessed — not a pass, an avoid or a no-value call"
            )
        if self.settlement_errors:
            total = sum(self.settlement_errors.values())
            first = sorted(self.settlement_errors.items(), key=lambda kv: -kv[1])[0]
            reasons.append(
                f"{total:,} raised inside settle ({first[0]}) and are counted "
                "unsettleable rather than swallowed"
            )
        if reasons:
            parts.append("Of those: " + "; ".join(reasons) + ".")
        if self.rows_without_a_price:
            parts.append(
                f"{self.rows_without_a_price:,} settled rows carry no readable "
                "price; they are counted and excluded from every ROI rather "
                "than given a profit of zero."
            )
        parts.append(f"Ledger holds {self.ledger_rows:,} rows.")
        return " ".join(parts)


@dataclass(frozen=True)
class _FixtureIndex:
    """Every fixture on the days a pass needs, keyed the two ways it is asked.

    Built **once per pass**. A per-row scan of 94,194 team-game rows and
    1,493,589 player-game rows turns a second into an hour, and a settle step
    that times out stops accumulating the only evidence that cannot be
    re-bought.
    """

    by_pair: dict
    by_team_day: dict
    game: dict

    def resolve(self, home_name: str, away_name: str, day: str, index) -> object:
        """The game id for a fixture, or `None`. Ambiguity resolves to nothing.

        `providers.team_names.TeamIndex.resolve` takes `among` — the fixture's
        two ids — which is what makes a genuinely ambiguous school name usable
        and what turns *the wrong* lone candidate into a miss rather than a
        match. The chicken-and-egg (the ids come from the fixture, the fixture
        comes from the ids) is broken by resolving the unambiguous side first
        and using each candidate fixture's other id as `among` for the rest.
        """
        home = index.resolve(home_name)
        away = index.resolve(away_name)
        if home is not None and away is not None:
            return self.by_pair.get((day, _pair(home, away)))
        known, unknown_name, unknown_is_home = (
            (home, away_name, False) if home is not None else (away, home_name, True)
        )
        if known is None:
            return None
        matches = []
        for game_id, other in self.by_team_day.get((day, known), ()):
            if index.resolve(unknown_name, among={known, other}) is not None:
                matches.append(game_id)
        return matches[0] if len(matches) == 1 else None


def _pair(a, b) -> tuple:
    return tuple(sorted((str(a), str(b))))


def _build_fixture_index(
    team_games: pd.DataFrame, game_segments: pd.DataFrame, days: set[str]
) -> _FixtureIndex:
    by_pair: dict = {}
    by_team_day: dict = {}
    game: dict = {}
    if team_games is None or team_games.empty or not days:
        return _FixtureIndex(by_pair, by_team_day, game)

    wanted = team_games[team_games["slate_date"].astype(str).isin(days)]
    if wanted.empty:
        return _FixtureIndex(by_pair, by_team_day, game)

    segments: dict = {}
    if game_segments is not None and not game_segments.empty:
        needed = set(wanted["game_id"])
        rows = game_segments[game_segments["game_id"].isin(needed)]
        segments = {r["game_id"]: r for r in rows.to_dict("records")}

    for record in wanted.to_dict("records"):
        day = str(record.get("slate_date"))
        team = record.get("team_id")
        opponent = record.get("opponent_id")
        game_id = record.get("game_id")
        side = str(record.get("home_away"))
        by_team_day.setdefault((day, team), []).append((game_id, opponent))
        bundle = game.setdefault(game_id, {"home": None, "away": None, "segment": None})
        if side in {"home", "away"}:
            # Both perspectives are kept. `settle` grades a wager from the row
            # of the side the selection names, because every quantity in the
            # team-games table is signed for its own team — settling the away
            # row for a home wager negates the margin and swaps the team total.
            bundle[side] = record
        if side == "home":
            by_pair[(day, _pair(team, opponent))] = game_id
            bundle["home_team_id"] = team
            bundle["away_team_id"] = opponent
        bundle["segment"] = segments.get(game_id)
    return _FixtureIndex(by_pair, by_team_day, game)


def _build_player_index(player_games: pd.DataFrame, game_ids: set) -> dict:
    """`(game_id, normalised name)` -> the athlete rows carrying it.

    Keyed by the game so candidates are already filtered to the two teams that
    played it, which is the football lab's rule: *a lone candidate on the wrong
    team is a void, not a match.*
    """
    index: dict = {}
    if player_games is None or player_games.empty or not game_ids:
        return index
    wanted = player_games[player_games["game_id"].isin(game_ids)]
    for record in wanted.to_dict("records"):
        key = (record.get("game_id"), normalise_person(record.get("athlete_display_name")))
        if not key[1]:
            continue
        index.setdefault(key, []).append(record)
    return index


def _ledger_days(ledger_path: Path) -> set[str]:
    frame = stores.read_store(Path(ledger_path), columns=LEDGER_COLUMNS)
    if frame.empty:
        return set()
    return {season.clean_text(d) for d in frame["snapshot_date"] if season.clean_text(d)}


def _days_since(day: str, now: datetime) -> float | None:
    try:
        played = date.fromisoformat(day)
    except (TypeError, ValueError):
        return None
    return (now.date() - played).days


def settle_snapshots(
    *,
    archive_dir: Path | str,
    ledger_path: Path | str,
    team_games: pd.DataFrame,
    player_games: pd.DataFrame,
    game_segments: pd.DataFrame,
    team_index,
    now: datetime | None = None,
    competition: Competition = CBB,
) -> SettlementResult:
    """Settle every snapshot that can be settled, once, and say what waited.

    Idempotent through **two** independent sources of "done": the `.settled`
    sidecar, and the ledger's own set of snapshot dates. Neither alone is
    enough. A snapshot that settled zero rows leaves no ledger trace, so the
    ledger alone would re-settle it forever; a marker lost to a cleanup would
    re-append a day the ledger already holds. Both are cheap and they fail in
    opposite directions.

    A day settles **atomically**. If any row is still inside the patience window
    with no final result, the whole day waits and nothing is appended — half a
    day in the ledger would make `snapshot_date in ledger` mean either "done" or
    "partly done", which destroys the second idempotence source.

    A snapshot that **cannot be parsed is skipped, not settled**. It is counted
    and named, the rest of the archive settles around it, and no marker is
    written for it — because a marker is this pass saying "this night is
    recorded", and a night read as zero rows is not recorded, it is lost. Left
    unmarked, the day is still gradeable if the file is restored from
    `card-feed` or repaired by hand; marked, it never would be again.
    """
    moment = now or datetime.now(timezone.utc)
    ledger = Path(ledger_path)
    result = SettlementResult()

    files = snapshot_files(archive_dir)
    result.snapshots_seen = len(files)
    if not files:
        result.ledger_rows = len(stores.read_store(ledger, columns=LEDGER_COLUMNS))
        return result

    settled_days = _ledger_days(ledger)
    pending: list[tuple[Path, pd.DataFrame]] = []
    for path in files:
        if marker_path(path).exists():
            continue
        if path.stem in settled_days:
            # The ledger holds this day but the marker is gone. Write it back:
            # the two sources exist to cover each other, not to argue.
            _write_marker(path, note="already present in the ledger")
            continue
        try:
            frame = read_snapshot_strictly(path)
        except stores.CorruptStoreError:
            # Named and counted, and deliberately NOT marked. Read leniently
            # this file is an empty frame, which grades zero rows, writes the
            # sidecar and closes the night — the prices are gone, so that loss
            # is permanent and nothing about the log would look wrong.
            result.snapshots_unreadable += 1
            result.unreadable_days = tuple(
                sorted(set(result.unreadable_days) | {path.stem})
            )
            continue
        pending.append((path, frame))

    if not pending:
        result.ledger_rows = len(stores.read_store(ledger, columns=LEDGER_COLUMNS))
        return result

    # One index build for the whole pass, over only the days it needs.
    prepared: list[tuple[Path, list[SimpleNamespace], list[dict]]] = []
    days: set[str] = set()
    for path, frame in pending:
        records = frame.to_dict("records")
        rows = [_frozen_row(r) for r in records]
        # Counted here, off the file, and never off an outcome. This is the one
        # number a caller can hold the three outcome counters against: those sum
        # to `rows_seen` by construction and can agree with each other while
        # every one of them is wrong.
        result.rows_read += len(rows)
        for row in rows:
            day = season.row_slate_date(row, competition)
            if day:
                days.add(day)
        prepared.append((path, rows, records))

    fixtures = _build_fixture_index(team_games, game_segments, days)

    # Resolve every fixture before touching the player table, so the player
    # index is built once and only over the games this pass actually needs.
    resolved: dict[tuple[str, str, str], object] = {}
    needed_games: set = set()
    for _, rows, _ in prepared:
        for row in rows:
            day = season.row_slate_date(row, competition)
            if not day:
                continue
            fixture_key = (day, row.home_team, row.away_team)
            if fixture_key not in resolved:
                resolved[fixture_key] = fixtures.resolve(
                    row.home_team, row.away_team, day, team_index
                )
            game_id = resolved[fixture_key]
            if game_id is not None:
                needed_games.add(game_id)
    players = _build_player_index(player_games, needed_games)

    settled_at = moment.isoformat()
    appended: list[dict] = []
    for path, rows, records in prepared:
        graded: list[dict] = []
        waiting = False
        # Grading is speculative until the day is known not to be waiting: a
        # break discards `graded`, so the counters it moved have to move back.
        before = _row_counter_snapshot(result)
        for row, record in zip(rows, records):
            day = season.row_slate_date(row, competition)
            game_id = resolved.get((day, row.home_team, row.away_team)) if day else None
            if game_id is None and day:
                elapsed = _days_since(day, moment)
                # `elapsed is None` means the slate date is not a real date, so
                # the join key does not exist and never will. That is
                # unsettleable rather than waiting: waiting forever on a key
                # that cannot form would block the day's other 199 games.
                if elapsed is not None and elapsed <= PATIENCE_DAYS:
                    # The result may still be published or restated. Waiting is
                    # not a verdict, and a guess would be one.
                    waiting = True
                    break
            graded.append(
                _settle_row(
                    row,
                    record,
                    game_id,
                    fixtures,
                    players,
                    result,
                    settled_at,
                    competition,
                )
            )
        if waiting:
            _restore_row_counters(result, before)
            result.snapshots_waiting += 1
            result.waiting_days = tuple(sorted(set(result.waiting_days) | {path.stem}))
            continue
        appended.extend(graded)
        result.snapshots_settled += 1
        _write_marker(path, note=f"{len(graded)} rows", settled_at=settled_at)

    if appended:
        result.ledger_rows = append_ledger(
            pd.DataFrame(appended, columns=list(LEDGER_COLUMNS)), ledger
        )
    else:
        result.ledger_rows = len(stores.read_store(ledger, columns=LEDGER_COLUMNS))
    return result


def _write_marker(path: Path, *, note: str, settled_at: str | None = None) -> Path:
    marker = marker_path(path)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(
        json.dumps(
            {
                "snapshot": path.name,
                "settled_at": settled_at or datetime.now(timezone.utc).isoformat(),
                "note": note,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return marker


def _unsettleable(record: Mapping, note: str, settled_at: str) -> dict:
    return _ledger_row(record, Settled(Outcome.UNSETTLEABLE, None, note), settled_at)


def _ledger_row(record: Mapping, decided: Settled, settled_at: str) -> dict:
    row = {column: record.get(column) for column in SNAPSHOT_COLUMNS}
    row["settled_at"] = settled_at
    row["outcome"] = _outcome_value(decided.outcome)
    row["actual"] = _blank(_as_float(decided.actual))
    row["profit_units"] = _blank(
        profit_units(decided.outcome, record.get("american_odds"))
    )
    return row


def _settle_row(
    row: SimpleNamespace,
    record: Mapping,
    game_id,
    fixtures: _FixtureIndex,
    players: dict,
    result: SettlementResult,
    settled_at: str,
    competition: Competition,
) -> dict:
    """One frozen opinion, graded. Every branch ends somewhere countable."""
    market = markets_registry.MARKETS_BY_KEY.get(row.market)
    if market is None:
        result.rows_unsettleable += 1
        return _unsettleable(
            record,
            f"no registry entry for market {row.market!r}, so there is no named "
            "quantity to settle against",
            settled_at,
        )
    if market.family == markets_registry.FUTURES:
        # A future has no game row and no slate day to wait for; it settles on
        # the tournament months later. It is handed straight to `settle`, which
        # owns the reason it cannot be graded here, so this module does not keep
        # a second copy of that reason to drift from. It is counted separately
        # so a deferred future can never be read as a missing box score — and it
        # is not a pass, an avoid, or a no-value call.
        result.rows_futures_deferred += 1
        return _record_outcome(
            record, _call_settle(market, row, None, None, result), result, settled_at
        )
    if not season.row_slate_date(row, competition):
        result.rows_unsettleable += 1
        return _unsettleable(
            record,
            "the commence time is missing or unparseable, so this opinion has "
            "no slate date and no join key — there is no future in which it "
            "begins to settle",
            settled_at,
        )
    if game_id is None:
        result.rows_unsettleable += 1
        result.rows_without_a_fixture += 1
        return _unsettleable(
            record,
            f"no game in the results tables matches {row.away_team} at "
            f"{row.home_team} within {PATIENCE_DAYS} days of the slate date",
            settled_at,
        )

    bundle = fixtures.game.get(game_id)
    game = _game_row_for(row, market, bundle)
    if bundle is None or (game is None and market.family != markets_registry.PLAYER):
        result.rows_unsettleable += 1
        result.rows_without_a_fixture += 1
        return _unsettleable(
            record,
            "the fixture resolved but the results tables carry no row for the "
            f"side {row.selection!r} names, so the two sides cannot be told "
            "apart and the margin would settle negated",
            settled_at,
        )

    player_row = None
    if row.player:
        candidates = players.get((game_id, normalise_person(row.player)), [])
        if len(candidates) > 1:
            result.rows_unsettleable += 1
            result.rows_ambiguous_player += 1
            return _unsettleable(
                record,
                f"{row.player!r} matches {len(candidates)} athletes on the two "
                "teams in this game; ambiguity settles nothing and is never a "
                "coin flip",
                settled_at,
            )
        if not candidates:
            decided = Settled(
                Outcome.VOID,
                None,
                f"{row.player!r} does not appear in this game's box score, so "
                "he never entered the game",
            )
            result.rows_void += 1
            return _ledger_row(record, decided, settled_at)
        player_row = candidates[0]

    return _record_outcome(
        record,
        _call_settle(market, row, game, player_row, result),
        result,
        settled_at,
    )


def _game_row_for(row: SimpleNamespace, market, bundle) -> object:
    """The row `settle` needs as its `game`, or None when it needs none.

    Three cases, all of them from the settlement contract rather than guessed:
    the two first-basket markets take a **game-segments** row, every other
    player prop takes **none**, and a team market takes the **team-games row of
    the side its selection names** — never the home row by default, because the
    table is signed per team and the wrong row settles the opponent's bet.
    """
    if bundle is None:
        return None
    if market.settles_on in _SEGMENT_SETTLED:
        return bundle.get("segment")
    if market.family == markets_registry.PLAYER:
        return None
    return bundle.get(_ROW_FOR_SELECTION.get(row.selection, "home"))


def _call_settle(market, row: SimpleNamespace, game, player_row, result) -> Settled:
    """`settle`, with one row's failure kept to one row.

    A contract mismatch must not look like a missing box score, so an exception
    is counted under its own name and surfaced in the summary rather than
    swallowed — and it must not stop the other 199 games of the night settling
    either, which is the brief's rule that a run degrades rather than empties.
    """
    try:
        return settle(
            market=market.key,
            segment=row.segment,
            selection=row.selection,
            line=row.line,
            game=game,
            player=player_row,
        )
    except Exception as exc:  # noqa: BLE001 - counted and named, never swallowed
        message = f"{type(exc).__name__}: {exc}"[:200]
        result.settlement_errors[message] = result.settlement_errors.get(message, 0) + 1
        return Settled(Outcome.UNSETTLEABLE, None, f"settle raised {message}")


def _record_outcome(
    record: Mapping, decided: Settled, result: SettlementResult, settled_at: str
) -> dict:
    state = _outcome_value(decided.outcome)
    if state == Outcome.VOID.value:
        result.rows_void += 1
    elif state == Outcome.UNSETTLEABLE.value:
        result.rows_unsettleable += 1
    else:
        result.rows_settled += 1
        if profit_units(decided.outcome, record.get("american_odds")) is None:
            result.rows_without_a_price += 1
    return _ledger_row(record, decided, settled_at)


# --------------------------------------------------------------------------
# The ledger
# --------------------------------------------------------------------------


def _row_counter_snapshot(result: "SettlementResult") -> dict[str, int]:
    """The row counters as they stand, for restoring after a waiting day."""
    return {name: getattr(result, name) for name in SettlementResult.ROW_COUNTERS}


def _restore_row_counters(result: "SettlementResult", saved: dict[str, int]) -> None:
    """Undo the grading a waiting day did before it discovered it was waiting.

    **The rows a waiting day grades are thrown away, and their counters were
    not.** `settle_snapshots` grades a snapshot's rows in order and breaks at
    the first row whose result is not published, then discards the whole day —
    but every row graded before the break had already incremented
    `rows_settled` / `rows_void` / `rows_unsettleable`. The ledger stayed
    correct and the day still waited atomically; what was wrong was the
    accounting identity the workflow prints, and the same rows were counted
    again on the pass that finally settled the day.

    It was found by the one reconciliation line that is not arithmetic over the
    counters themselves — rows graded against what the ledger file actually
    grew by — which is the whole reason that line is computed independently
    rather than derived from the numbers it is checking.
    """
    for name, value in saved.items():
        setattr(result, name, value)


def read_ledger(path: Path | str) -> pd.DataFrame:
    return stores.read_store(Path(path), columns=LEDGER_COLUMNS)


def _with_ledger_columns(ledger: object) -> pd.DataFrame:
    """A copy carrying every ledger column. Never mutates the caller's frame."""
    frame = (
        ledger.copy() if isinstance(ledger, pd.DataFrame) else pd.DataFrame(ledger)
    )
    for column in LEDGER_COLUMNS:
        if column not in frame.columns:
            frame[column] = pd.NA
    return frame


def ledger_identity(record: Mapping) -> tuple:
    """What makes two ledger rows the same settled opinion, **canonically**.

    Normalised rather than read raw, and that is not tidiness. A moneyline's
    blank line is `None` in memory and float NaN after a CSV round trip, and
    `None != NaN` — so a raw-column dedupe on `LEDGER_IDENTITY` matches nothing
    for every market with no line, and the append-only ledger quietly accepts a
    second copy of an opinion it already holds. Caught by
    `test_appending_the_same_settled_row_twice_keeps_the_row_recorded_first`,
    and it is the same defect as the moneyline re-freeze in `_frozen_row`: the
    NHL lab's join-vocabulary family has now cost this repository two members in
    one file, both of them a blank behaving as two different values.
    """
    return (
        season.clean_text(record.get("snapshot_date")),
        season.clean_text(record.get("event_id")),
        season.clean_text(record.get("market")),
        season.clean_text(record.get("segment")),
        season.clean_text(record.get("player")).casefold(),
        season.clean_text(record.get("selection")),
        normalise_line(record.get("line")),
        season.clean_text(record.get("book")),
    )


def append_ledger(rows: pd.DataFrame, path: Path | str) -> int:
    """Append settled rows. **This store can only grow.** Returns the new count.

    Two guards, both of which exist because this is the one store in the lab
    that cannot be rebuilt — the prices these opinions were frozen at were
    quoted for a few minutes on a Tuesday in January and are gone.

    `stores.read_store(..., for_append=True)` raises on a parse error rather
    than returning an empty frame: a caller that silently reads nothing and then
    writes replaces a damaged long file with a short one, and that damage is
    permanent.

    And the write is refused outright if it would produce **fewer** rows than
    the file already holds. The way that happens in practice is a ledger that
    already contains duplicates: deduplicating it looks like tidying and is
    actually deleting settled evidence. So the duplicates are kept, the append
    is refused, and a human is told — rather than the file being quietly
    compacted by a routine nightly write.

    A row whose identity is already on disk is dropped from the incoming batch,
    never written over it. **A re-settled opinion never replaces the one that
    was recorded first.**
    """
    target = Path(path)
    existing = stores.read_store(target, columns=LEDGER_COLUMNS, for_append=True)
    before = len(existing)

    incoming = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(list(rows))
    if incoming.empty:
        return before
    for column in LEDGER_COLUMNS:
        if column not in incoming.columns:
            incoming[column] = pd.NA
    incoming = incoming[list(LEDGER_COLUMNS)]

    on_disk = [ledger_identity(r) for r in existing.to_dict("records")]
    would_hold = len(set(on_disk))
    if would_hold < before:
        raise ValueError(
            f"The forward-evidence ledger at {target.name} holds {before:,} rows "
            f"but only {would_hold:,} distinct settled opinions, so appending "
            "would compact it. Refusing: this ledger is append-only and cannot "
            "be rebuilt — forward evidence cannot be back-dated and the prices "
            "these opinions were frozen at are gone. Resolve the duplicates by "
            "hand rather than letting a nightly write delete them."
        )

    known = set(on_disk)
    fresh: list[dict] = []
    for record in incoming.to_dict("records"):
        identity = ledger_identity(record)
        if identity in known:
            continue
        known.add(identity)
        fresh.append(record)
    if not fresh:
        return before
    return stores.append(
        pd.DataFrame(fresh, columns=list(LEDGER_COLUMNS)),
        target,
        columns=LEDGER_COLUMNS,
    )


# --------------------------------------------------------------------------
# Stage three: report
# --------------------------------------------------------------------------


def row_verdict(
    interval: stats.RoiInterval,
    *,
    suspect: bool = False,
    minimum_bets: int = stats.MINIMUM_BETS,
) -> str:
    """The one sentence a table row is permitted to be described by.

    Four guards, in this order, because the order is the safety:

    1. **not evidence** — the market's settlement rule is one this lab cannot
       verify, and a number computed on an unverified settlement rule is an
       artefact at any sample size. The football lab's single largest false
       finding was a settlement offset it could not see.
    2. **not enough evidence** — with the n and the floor, both. A +12% return
       over 40 bets and a coin flip are the same claim.
    3. **no demonstrated edge** — in those exact words, for any interval that
       includes zero. Never "promising", never "trending positive".
    4. **positive** or **negative** — and the direction is not decoration. The
       NHL lab shipped a headline saying a market had survived and replicated
       when what it had replicated was a **loss** of −6.6%.
    """
    if suspect:
        return (
            "**not evidence** — this market's settlement rule is one this lab "
            f"cannot verify, so its {interval.bets:,} rows measure the rule as "
            "much as the model"
        )
    if interval.bets < minimum_bets:
        return (
            f"**not enough evidence** — {interval.bets:,} bets, below "
            f"{minimum_bets:,}"
        )
    if interval.adjusted_low > 0:
        return "interval excludes zero, **positive**"
    if interval.adjusted_high < 0:
        return "interval excludes zero, **negative**"
    return f"**{stats.NO_DEMONSTRATED_EDGE}**"


#: The extra columns `_measurable` derives. Named so an empty result carries
#: the same shape as a full one and no caller has to special-case the schema.
_DERIVED_COLUMNS: tuple[str, ...] = ("slate_date", "profit", "edge_value")


def _empty_measurable() -> pd.DataFrame:
    frame = pd.DataFrame(columns=list(LEDGER_COLUMNS) + list(_DERIVED_COLUMNS))
    return frame.astype({c: "object" for c in frame.columns})


def _measurable(ledger: pd.DataFrame, competition: Competition) -> pd.DataFrame:
    """Resolved wagers carrying a readable profit, with a day to cluster on.

    Three kinds of row are dropped here and counted in the report's header
    instead, and none of them is a zero:

    * **`UNSETTLEABLE`** — the outcome is unknown, and an unknown outcome
      averaged in as break-even is a fabricated number.
    * **`VOID`** — a bet that never existed. A player who never entered the
      game is not a wager that returned its stake, and folding thousands of
      them in at 0.0 would drag every interval toward zero while inflating
      every n. A **push** is kept, because a push is a wager that happened and
      returned the stake.
    * **settled at a price this lab cannot read** — a won bet whose payout is
      unknown is not a won bet worth zero.
    """
    if ledger is None or ledger.empty:
        return _empty_measurable()
    frame = ledger.copy()
    frame["outcome"] = [_outcome_value(o) for o in frame["outcome"]]
    frame["profit"] = [_as_float(p) for p in frame["profit_units"]]
    frame["edge_value"] = [_as_float(e) for e in frame["edge"]]
    frame["slate_date"] = [
        season.row_slate_date(_frozen_row(r), competition)
        for r in frame.to_dict("records")
    ]
    frame["market"] = [season.clean_text(m) for m in frame["market"]]
    frame["tier"] = [season.clean_text(t) or Tier.UNPLACED.value for t in frame["tier"]]
    keep = frame["outcome"].isin(
        {Outcome.WON.value, Outcome.LOST.value, Outcome.PUSH.value}
    ) & frame["profit"].notna()
    kept = frame[keep].reset_index(drop=True)
    return kept if len(kept) else _empty_measurable()


def _interval(frame: pd.DataFrame, *, looks: int) -> stats.RoiInterval:
    if frame.empty:
        return stats.RoiInterval(0.0, 0.0, 0.0, 0, 0, looks=looks)
    return stats.interval_two_way(
        frame.assign(profit_units=frame["profit"]),
        game_column="event_id",
        day_column="slate_date",
        profit_column="profit_units",
        looks=looks,
    )


def _is_player_market(market_key: object) -> bool:
    market = markets_registry.MARKETS_BY_KEY.get(season.clean_text(market_key))
    return bool(market and market.family == markets_registry.PLAYER)


def _is_futures_market(market_key: object) -> bool:
    market = markets_registry.MARKETS_BY_KEY.get(season.clean_text(market_key))
    return bool(market and market.family == markets_registry.FUTURES)


def _split_families(measurable: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Game markets and futures, apart. Futures never enter a game headline."""
    if measurable.empty:
        return measurable, measurable
    is_future = [_is_futures_market(m) for m in measurable["market"]]
    games = measurable[[not f for f in is_future]].reset_index(drop=True)
    futures = measurable[is_future].reset_index(drop=True)
    return games, futures


def _bet_rows(games: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """The opinions that clear the declared edge **and** could be selected.

    A player prop is excluded here however large its edge, because nothing in
    this sport reaches `Availability.CONFIRMED` and a bet nobody could place is
    not a bet. It stays in the opinions table, which is where the evidence
    belongs. It is **not** a pass, an avoid, or a no-value call.
    """
    if games.empty:
        return games
    keep = [
        edge is not None
        and edge >= float(threshold)
        and not _is_player_market(market)
        for edge, market in zip(games["edge_value"], games["market"])
    ]
    return games[keep].reset_index(drop=True)


def _table(
    frame: pd.DataFrame,
    *,
    looks: int,
    minimum_bets: int,
    suspects: frozenset,
    group: tuple[str, ...],
) -> list[str]:
    lines = [
        "| " + " | ".join(g.replace("_", " ").title() for g in group)
        + " | Bets | Clusters | ROI | 95% interval | Family-corrected | Verdict |",
        "|:---" * len(group) + "|---:|---:|---:|:---|:---|:---|",
    ]
    if frame.empty:
        lines.append(
            "| " + " | ".join("—" for _ in group) + " | 0 | 0 | — | — | — | "
            "**not enough evidence** — 0 bets, below "
            f"{minimum_bets:,} |"
        )
        return lines
    for keys, subset in frame.groupby(list(group), sort=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        interval = _interval(subset, looks=looks)
        suspect = str(keys[0]) in suspects
        lines.append(
            "| "
            + " | ".join(str(k) for k in keys)
            # The cluster unit is printed, not just the count. `interval_two_way`
            # computes the interval by game and by day and reports the wider,
            # and which one won is a fact about the dependence structure the
            # reader needs — a day-clustered row means a whole slate moved
            # together, which is a different claim from a game-clustered one.
            + f" | {interval.bets:,} | {interval.clusters:,} {interval.cluster_unit}s "
            f"| {interval.roi:+.1%} | {interval.low:+.1%} to {interval.high:+.1%} "
            f"| {interval.adjusted_low:+.1%} to {interval.adjusted_high:+.1%} "
            f"| {row_verdict(interval, suspect=suspect, minimum_bets=minimum_bets)} |"
        )
    return lines


def render_ledger(
    ledger: pd.DataFrame,
    *,
    minimum_bets: int = stats.MINIMUM_BETS,
    families: int | None = None,
    settlement_suspects: frozenset = frozenset(),
    bet_threshold: float = BET_EDGE_THRESHOLD,
    competition: Competition = CBB,
) -> str:
    """The forward-evidence report, per market **and** per tier.

    `families` is the experiment ledger's **cumulative** count of everything
    ever tested, never this week's table — *"a search that runs every week is
    not twelve tests, it is twelve tests a week, forever."* When it is not
    supplied the report says so rather than quietly correcting for one look,
    because an uncorrected interval that looks corrected is worse than no
    correction at all.

    **No number pooled across the whole of Division I appears as a lead
    figure.** High-major, mid-major and low-major are different distributions,
    fitted and measured separately; a policy that wins in low-major games and
    loses in high-major ships in low-major only, if it ships at all.
    """
    looks = max(int(families), 1) if families else 1
    suspects = frozenset(str(s) for s in settlement_suspects)
    frame = _with_ledger_columns(ledger)

    total = len(frame)
    outcomes = [_outcome_value(o) for o in frame["outcome"]]
    unsettleable = sum(1 for o in outcomes if o == Outcome.UNSETTLEABLE.value)
    void = sum(1 for o in outcomes if o == Outcome.VOID.value)
    measurable = _measurable(frame, competition)
    priceless = sum(
        1
        for o, p in zip(outcomes, frame["profit_units"])
        if o in {Outcome.WON.value, Outcome.LOST.value, Outcome.PUSH.value}
        and _as_float(p) is None
    )

    lines: list[str] = []
    add = lines.append
    add("# Forward evidence")
    add("")
    add(
        "**Forward evidence cannot be back-dated.** Historical prices can be "
        "bought at any time; a night the pipeline did not freeze and settle is "
        "a night of clean out-of-sample data gone permanently, and in this "
        "sport a night is up to 200 games. Everything below was frozen before "
        "tip and settled afterwards against the box score. Nothing here was "
        "priced with knowledge of a result."
    )
    add("")
    add(
        f"**{total:,} frozen opinions in the ledger.** "
        f"{len(measurable):,} are resolved wagers carrying a readable price and "
        f"are measured below. {unsettleable:,} are **unsettleable**, {void:,} "
        f"are **void** — a bet that never existed rather than one that returned "
        f"its stake — and {priceless:,} settled at a price this lab cannot "
        "read. None of those three is a zero, and none of them enters any "
        "interval."
    )
    add("")
    if families:
        add(
            f"Every interval is corrected across **{looks:,} hypotheses ever "
            "tested**, from the experiment ledger's cumulative count rather "
            "than this table's row count."
        )
    else:
        add(
            "**No experiment-ledger count was supplied, so no family "
            "correction is applied.** Every interval below is therefore "
            "narrower than the truth, and none of them should be read as a "
            "finding. A search that runs every week is not twelve tests; it is "
            "twelve tests a week, forever."
        )
    add("")
    add(
        "Intervals are clustered by game **and** by day, and the wider of the "
        "two is reported. One game supplies a moneyline, a spread, a total, two "
        "team totals and a dozen props: a 100-game Tuesday is not 1,500 "
        "independent observations."
    )
    add("")

    games, _futures = _split_families(measurable)
    opinions = games
    bets = _bet_rows(games, bet_threshold)

    add("## Opinions and bets are reported separately, always")
    add("")
    add(
        f"**{len(opinions):,} opinions** — every settled row, whatever its edge "
        f"— and **{len(bets):,} bets** — the rows clearing the "
        f"{bet_threshold:+.1%} edge declared in advance. Both are printed every "
        "time, because mixing them flatters whichever is worse."
    )
    add("")
    player_rows = sum(1 for m in games["market"] if _is_player_market(m))
    if player_rows:
        add(
            f"{player_rows:,} of those opinions are player props. They are "
            "priced, frozen and settled, and they **cannot produce a "
            "selection**: nothing in this sport reaches `Availability."
            "CONFIRMED`, ESPN's men's-college-basketball injuries endpoint is "
            "permanently empty, and the conference reports that exist cover "
            "roughly 115 of 365 teams in conference games only. They are "
            "therefore excluded from the bet tables. **That is not a pass, an "
            "avoid, or a no-value call.**"
        )
        add("")

    for label, subset in (("Opinions", opinions), ("Bets", bets)):
        add(f"## {label}, per market and per tier")
        add("")
        add(
            "No figure pooled across the whole of Division I appears here. "
            "High-major, mid-major and low-major are different distributions "
            "and are measured as such; `unplaced` is a team with too little "
            "prior non-conference evidence to place and is reported apart "
            "rather than folded into a tier."
        )
        add("")
        lines.extend(
            _table(
                subset,
                looks=looks,
                minimum_bets=minimum_bets,
                suspects=suspects,
                group=("market", "tier"),
            )
        )
        add("")
        add(f"### {label} by tier")
        add("")
        # A settlement suspect is **not evidence**, so it cannot be folded into
        # a roll-up that is presented as evidence. Held out rather than
        # labelled, because a per-tier row has no market column to carry the
        # label on and an unlabelled suspect inside an aggregate is exactly how
        # a number nobody trusts becomes a number everybody quotes.
        clean = (
            subset[[m not in suspects for m in subset["market"]]]
            if not subset.empty
            else subset
        )
        held_out = len(subset) - len(clean)
        lines.extend(
            _table(
                clean,
                looks=looks,
                minimum_bets=minimum_bets,
                suspects=frozenset(),
                group=("tier",),
            )
        )
        add("")
        if held_out:
            add(
                f"{held_out:,} rows are held out of this roll-up because their "
                "market's settlement rule is one this lab cannot verify. They "
                "appear per market above, marked **not evidence**. They are "
                "excluded from an aggregate rather than averaged into one, "
                "because a number that is not evidence must not be folded into "
                "a number presented as evidence."
            )
            add("")

    second_half = sorted(
        {season.clean_text(m) for m in games["market"]} & SETTLEMENT_AMBIGUOUS_MARKETS
    )
    if second_half:
        add(
            f"**Settlement ambiguity.** {', '.join(f'`{m}`' for m in second_half)} "
            "settle including overtime here, which is the convention at most US "
            "books and not a fact about basketball. This lab cannot read a "
            "book's rulebook, so those rows measure the settlement rule as well "
            "as the model."
        )
        add("")

    lines.extend(_reachability_section(games, looks=looks, minimum_bets=minimum_bets))
    lines.extend(_futures_section(measurable, minimum_bets=minimum_bets, looks=looks))

    add(
        "Every figure above carries its sample size. An interval including zero "
        f"is **{stats.NO_DEMONSTRATED_EDGE}** — not promising, not trending "
        "positive, not small but positive."
    )
    return "\n".join(lines) + "\n"


def _reachability_section(
    games: pd.DataFrame, *, looks: int, minimum_bets: int
) -> list[str]:
    """Prices that survived to the next capture, against those that did not.

    From the brief: *"a soft number you cannot bet is not an edge."* The
    plausible edge in this sport lives in exactly the games where the price is
    hardest to get — the low-major end of the board, where limits are trivial
    and the number moves fastest. So survival is reported as its own split, and
    an edge that lives entirely in prices that vanished is **not reachable**, in
    those words, regardless of its size or its significance.
    """
    lines = ["## Reachability", ""]
    if "price_survived" not in games.columns or games["price_survived"].isna().all():
        lines.append(
            "**This ledger does not carry price survival**, so reachability is "
            "unmeasured here rather than measured and found fine. A number "
            "reported without it is a number about prices that may not have "
            "existed by the time anybody could take them."
        )
        lines.append("")
        return lines

    survived = games[games["price_survived"].map(_truthy)]
    vanished = games[~games["price_survived"].map(_truthy)]
    lines.append(
        f"**{len(survived):,} opinions were frozen at a price that still "
        f"existed at the next capture; {len(vanished):,} were not.** A backtest "
        "that beats a price nobody could still take is not a bet."
    )
    lines.append("")
    lines.extend(
        _table(
            games.assign(
                reachability=[
                    "survived" if _truthy(v) else "vanished"
                    for v in games["price_survived"]
                ]
            ),
            looks=looks,
            minimum_bets=minimum_bets,
            suspects=frozenset(),
            group=("reachability",),
        )
    )
    lines.append("")
    survived_interval = _interval(survived, looks=looks)
    vanished_interval = _interval(vanished, looks=looks)
    if (
        vanished_interval.adjusted_low > 0
        and not survived_interval.adjusted_low > 0
    ):
        lines.append(
            f"The measured edge lives entirely in prices that did not survive "
            f"to the next capture, so it is **{NOT_REACHABLE}** — regardless of "
            "its size or its significance."
        )
        lines.append("")
    return lines


def _truthy(value: object) -> bool:
    text = season.clean_text(value).casefold()
    return text in {"1", "1.0", "true", "yes", "survived", "y"}


def _futures_section(
    measurable: pd.DataFrame, *, minimum_bets: int, looks: int
) -> list[str]:
    """Futures, apart, with hold time. **Never folded into a game headline.**

    A futures stake is tied up for months and settles on a different clock; its
    return is not comparable to a single-game bet, so no futures number ever
    enters an ROI computed over game bets.
    """
    lines = ["## Futures", ""]
    _games, futures = _split_families(measurable)
    if futures.empty:
        lines.append(
            "No settled futures in the ledger. When there are, they appear here "
            "and only here: a futures stake is tied up for months and settles "
            "on a different clock, and **no futures return is ever folded into "
            "a headline computed over game bets.**"
        )
        lines.append("")
        return lines
    holds = [
        _hold_days(row.get("snapshot_date"), row.get("settled_at"))
        for row in futures.to_dict("records")
    ]
    known = [h for h in holds if h is not None]
    hold = (
        f"median hold **{sorted(known)[len(known) // 2]:,} days**"
        if known
        else "hold time unknown"
    )
    interval = _interval(futures, looks=looks)
    lines.append(
        f"**{len(futures):,} settled futures, {hold}.** "
        f"{interval.roi:+.1%}, 95% interval {interval.low:+.1%} to "
        f"{interval.high:+.1%} — "
        f"{row_verdict(interval, minimum_bets=minimum_bets)}. This figure is "
        "not comparable to a single-game return and is never folded into one."
    )
    lines.append("")
    return lines


def _hold_days(frozen: object, settled: object) -> int | None:
    start = season.clean_text(frozen)[:10]
    end = season.clean_text(settled)[:10]
    try:
        return (date.fromisoformat(end) - date.fromisoformat(start)).days
    except (TypeError, ValueError):
        return None


def report_payload(
    ledger: pd.DataFrame,
    *,
    minimum_bets: int = stats.MINIMUM_BETS,
    families: int | None = None,
    settlement_suspects: frozenset = frozenset(),
    bet_threshold: float = BET_EDGE_THRESHOLD,
    competition: Competition = CBB,
) -> dict:
    """The same numbers as the markdown, as data. One computation, two renders.

    Two renderers reading two computations is how a JSON summary and a markdown
    report come to disagree in public, which is the shape of the football lab's
    `_bonferroni_factor`-in-four-files defect applied to prose.
    """
    looks = max(int(families), 1) if families else 1
    suspects = frozenset(str(s) for s in settlement_suspects)
    measurable = _measurable(_with_ledger_columns(ledger), competition)
    games, _futures = _split_families(measurable)
    bets = _bet_rows(games, bet_threshold)
    rows = []
    if not games.empty:
        for cut, subset in (("opinions", games), ("bets", bets)):
            if subset.empty:
                continue
            for (market, tier), part in subset.groupby(["market", "tier"], sort=True):
                interval = _interval(part, looks=looks)
                rows.append(
                    {
                        "cut": cut,
                        "market": market,
                        "tier": tier,
                        "bets": interval.bets,
                        "clusters": interval.clusters,
                        "cluster_unit": interval.cluster_unit,
                        "roi": interval.roi,
                        "low": interval.low,
                        "high": interval.high,
                        "adjusted_low": interval.adjusted_low,
                        "adjusted_high": interval.adjusted_high,
                        "verdict": row_verdict(
                            interval,
                            suspect=market in suspects,
                            minimum_bets=minimum_bets,
                        ),
                    }
                )
    return {
        "frozen_opinions": int(len(_with_ledger_columns(ledger))),
        "measurable_rows": int(len(measurable)),
        "families": looks if families else None,
        "minimum_bets": int(minimum_bets),
        "bet_threshold": float(bet_threshold),
        "no_pooled_division_one_headline": True,
        "rows": rows,
    }


def write_report(
    ledger: pd.DataFrame,
    *,
    output_dir: Path | str,
    minimum_bets: int = stats.MINIMUM_BETS,
    families: int | None = None,
    settlement_suspects: frozenset = frozenset(),
    bet_threshold: float = BET_EDGE_THRESHOLD,
    competition: Competition = CBB,
) -> tuple[Path, Path]:
    """Write both renders of the report. Returns `(markdown, json)`."""
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    markdown = directory / REPORT_MARKDOWN_FILENAME
    payload = directory / REPORT_JSON_FILENAME
    markdown.write_text(
        render_ledger(
            ledger,
            minimum_bets=minimum_bets,
            families=families,
            settlement_suspects=settlement_suspects,
            bet_threshold=bet_threshold,
            competition=competition,
        ),
        encoding="utf-8",
    )
    payload.write_text(
        json.dumps(
            report_payload(
                ledger,
                minimum_bets=minimum_bets,
                families=families,
                settlement_suspects=settlement_suspects,
                bet_threshold=bet_threshold,
                competition=competition,
            ),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return markdown, payload
