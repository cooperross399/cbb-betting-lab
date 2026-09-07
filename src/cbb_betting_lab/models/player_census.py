"""The wager census, and the gate that stops a grading run whose denominator moved.

Design section 10 ends with a sentence this module exists to obey: *"Gate before
grading: reconcile 261,870 wagers (measured, by event/market/player/selection/
line) against the brief's 257,474. A 1.7% unexplained denominator is a
wrong-denominator error of the same family. The run stops until it reconciles."*

**This module states no result.** It computes no probability, no de-vig, no log
loss, no ROI, no interval and no verdict. It counts rows in a table and refuses.
Every number in this docstring is a count I took over
`data/processed/cbb_historical_prices__card.csv` (sha256
`143d7d30...b82b78b`, 977,613,435 bytes) with `usecols=` and
`chunksize=500_000`, never on the whole file, on 2026-09-06.

## 1. What the gate is actually for

The defect is the one `stores.py` was written against, arriving through a
different column. The NHL lab counted every book's quote on one selection as an
independent bet and every interval came out about root-2.83 too narrow; `stores.
best_price_per_wager` collapses a quote to a wager on the price identity minus
the book. **That collapse is only as good as the spelling of the subject**, and
on this store it is not good enough: the same athlete is quoted under two
capitalisations by two different books, so one wager is counted twice.

Measured: 64 folded names carry exactly two raw spellings each (128 raw
spellings), and they collapse **4,396** wager keys, which is 1.679% of 261,870 —
design section 10's "1.7%". 3,959 of those 4,396 keys carry more than one
distinct `american_odds`, so under the raw key `best_price_per_wager` returns
TWO rows for one athlete-line-side. Every one of the 4,396 is cross-book: **0**
carry a book that quoted both spellings at the same key, so none of them is one
book quoting twice. Overwhelmingly the second spelling is one title-caser's:
`'A.J. HOGGARD'` beside `'A.J. Hoggard'`, `'AJ Storr'` beside `'Aj Storr'`,
`'Tucker DeVries'` beside `'Tucker Devries'`.

## 2. Why this gate is an ATTRIBUTION and not an equality

Design section 10 asks for 261,870 to be reconciled *against* 257,474. Written
as an equality it is a gate that can never open, because **both numbers are
correct counts of the same rows** under two spellings of the subject:

    key = (event_id, market, segment, player, selection, line, snapshot_phase)
      player taken raw            261,870 wagers   1,357 names
      player.strip()              261,870 wagers   1,357 names  (no whitespace anywhere)
      player.strip().casefold()   257,474 wagers   1,293 names

So the gate implemented here is: **every wager of the difference must be named.**
`reconcile` requires the residual to be exactly 0 — not small — after every
collapse has been attributed to an enumerated `Collision`. Today 4,396 are
counted and 4,396 are attributed, residual 0. That is a disagreement with the
design's wording, reported rather than silently patched, and it is the shape
that can fail: a 65th collision group, or a collapse that no group explains,
stops the run.

## 3. What it refuses on

`reconcile` **raises** `WagerCountMismatch`. It never warns, never returns a
bool a caller can drop, never returns the smaller number and never "reconciles"
by picking a side. Eight clauses, and clause 2 is the one that matters:

1. a per-market count, or a per-market quote count, that is not what the frozen
   census artifact declares;
2. any part of (raw - folded) not attributed to an enumerated collision;
3. a collision whose two spellings were quoted by ONE book at ONE wager key --
   that is a duplicated quote, a different defect, and it must not be folded
   away silently (measured today: 0 of 4,396);
4. a collision whose fold merges two `athlete_id`s inside one game -- that is
   destroying a subject, not normalising a spelling (measured today: 0);
5. a census invariant off -- season, segment, snapshot phase, events, days,
   books, quotes, rows, subjects;
6. a source digest that is not the pinned one. The store is a SYMLINK into a
   shared tree, so an unpinned gate certifies whichever file the link pointed
   at;
7. either market refused BY NAME appearing in the priced totals;
8. an expectation the frozen artifact does not carry at all. Every comparison
   above is guarded by `if want is not None`, so a deleted key used to mean the
   clause was silently not compared while it still counted towards
   `Attribution.checked` -- a tick the gate had not earned. `compared_checks`
   is now reported beside `checked` and the two are equal on any attribution
   that returns.

Counts are compared PER MARKET and never only as a total: two per-market errors
of opposite sign cancel in a total, and the gate would pass on a store that had
changed twice.

## 4. The trap in the headline numbers

Neither 261,870 nor 257,474 is a grading denominator. **Both include the 723
wagers on the two markets refused BY NAME** (`player_first_basket` 1,823 quotes
/ 721 wagers, `player_double_double` 2 quotes / 2 wagers -- design section 6's
figures, reproduced exactly). The priced-market denominators are 261,147 raw and
256,751 folded. A run that grades 257,474 cells has priced two refused markets,
so the refused pair is counted, carried in its own bucket with `priced=False`
travelling with it, and never summed into the priced total. A refusal that is
counted is evidence the refusal held; a refusal dropped from the census is
indistinguishable from a market nobody looked at.

## 5. The blockers this gate does not close

Reported here because a number the design does not declare is not a number to
invent:

* **No athlete-level denominator exists or can exist yet.** The price store has
  no `athlete_id` column. The graded denominator is only knowable after section
  7's R1 cascade runs and its refusals are removed; an approximation of R1's
  pre-match fold (NFKD to ASCII, punctuation and spacing collapsed) counts
  251,949, i.e. at least 5,525 below the design's number. This gate is
  string-level and says so.
* **The lab has declared no subject normalizer.** The design names the key but
  never says which spelling of `player` is the subject, and the denominator is a
  function of that choice: 261,870 / 257,474 / 257,378 / 255,553 / 251,949 over
  five reasonable folds. This module counts under BOTH named normalizers and
  refuses to pick one; `SUBJECT_NORMALIZERS` is the menu and the artifact
  records that nothing is declared.
* **One quoted subject is genuinely ambiguous** and no fold can fix it: 'Justin
  Moore', game 401604303 (Villanova against Drexel, 2023-12-02), is two
  `athlete_id`s under one display name. It is the only one of 9,098 quoted
  (game, folded-name) pairs the 2024 roster says covers more than one athlete,
  and section 7's R1 refuses more than one candidate rather than picking. It is
  counted here and pinned, not folded.

## 6. Where it is called

From the grading entry point BEFORE any scoring code runs, never only from a
test: a gate that lives in the suite is a gate on the merge, not on the run.
`GRADING_ENTRY_POINTS` names the entry points, `guard_graded_frame` is what they
call, and `tests/test_player_census_reconciles.py` holds the assertion that
names them, so the day a fifth one is wired the assertion has to be re-read.

The list said TWO until 2026-09-06 and it was wrong. `forward_evidence` and
`reachability` both build a clustered `stats.RoiInterval` over a settled wager
frame and both print a family-corrected Verdict per market, and neither was
named or guarded. Measured 2026-09-06 with the guard lines deleted and nothing
else changed: `scripts/run_forward_evidence.py --settle` over a night holding
one `player_points` prop exited **0** and wrote
`| player_points | unplaced | 1 | 1 games | +87.0% | -inf% to +inf% | -inf% to
+inf% | **not enough evidence** — 1 bets, below 200 |` into the Opinions table
and the matching `roi`/`adjusted_low`/`verdict` entry into the JSON, with
`reconciled() == ()`. Below the floor, so no number was claimed — but the door
was open, and a 240-row fixture ledger through `render_ledger` came out with a
ROI, a family-corrected interval and a verdict string on the same path. The
test that claimed to cover "the whole of the grading surface" could not see
them: it scanned for one spelling of a verb list
(`log_loss|logloss|brier|de_?vig|fair_price|scorable|settled_opinions|roi_interval`)
and neither module contains any of those tokens. The scan now looks for what a
grader DOES — constructs a `RoiInterval`, calls `stats.interval_two_way` or
`interval_by_cluster`, or names a scoring verb — and the test says in its own
name that a lexical scan is a floor and not a proof.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from cbb_betting_lab import stores
from cbb_betting_lab.config import PROCESSED_DIR
from cbb_betting_lab.models import player_rates


class WagerCountMismatch(RuntimeError):
    """The wager census did not reconcile, and nothing may be graded.

    A `RuntimeError` and not a warning, and carrying the whole per-market table
    rather than the first difference, because a caller who is told only that
    something moved will re-run and take the number that comes back.
    """


#: What makes two quotes one wager. **Derived from `stores.PRICE_IDENTITY`, not
#: retyped.** A literal here drifts from the code that actually collapses
#: quotes, and that drift is the whole finding in section 1 of the docstring:
#: the shipped `best_price_per_wager` keys on exactly these seven columns
#: (`segment` is constant 'game' and `snapshot_phase` constant 'card' across all
#: 504,394 player rows, so on this store it is the design's five), and
#: `stores._dedupe_value` strips but does not casefold.
WAGER_KEY: tuple[str, ...] = tuple(
    column for column in stores.PRICE_IDENTITY if column != "book"
)

#: The column of `WAGER_KEY` the subject normalizer is applied to, found by name
#: rather than by index so a change to `PRICE_IDENTITY`'s order cannot silently
#: fold the wrong column.
SUBJECT_COLUMN = "player"

#: Every market this census counts. A market whose key starts with this is a
#: player prop; the two refused BY NAME are player props and are counted.
PLAYER_MARKET_PREFIX = "player_"

#: Read from `player_rates`, never restated. `priced=False` travels with these
#: two through every count in this module.
MARKETS_REFUSED_BY_NAME: tuple[str, ...] = tuple(
    sorted(player_rates.MARKETS_REFUSED_BY_NAME)
)

#: The ten the model prices, likewise read and not restated.
PRICED_MARKETS: tuple[str, ...] = tuple(player_rates.PRICED_MARKETS)

#: 500,000 rows at a time. The store is 977,613,435 bytes and 3,863,325 rows; a
#: whole-file `pd.read_csv` of it is minutes of wall clock and gigabytes of
#: resident memory, and this module is structurally incapable of one --
#: `tests/test_player_census_reconciles.py` monkeypatches `pd.read_csv` and
#: fails the module if any call omits `chunksize` or `usecols`.
CHUNK_ROWS = 500_000

DEFAULT_STORE_PATH = Path(PROCESSED_DIR) / "cbb_historical_prices__card.csv"
DEFAULT_ROSTER_PATH = Path(PROCESSED_DIR) / "cbb_player_games.csv"
DEFAULT_EXPECTED_PATH = Path(PROCESSED_DIR) / "cbb_player_census.json"


# --------------------------------------------------------------------------
# The subject, which the lab has not declared
# --------------------------------------------------------------------------

Subject = Callable[[str], str]


def raw_subject(name: str) -> str:
    """The book's spelling, untouched. Counts 261,870 wagers, 1,357 names."""
    return name


def casefold_subject(name: str) -> str:
    """Stripped and casefolded. Counts 257,474 wagers, 1,293 names.

    Measured: `strip()` alone changes nothing on this store (1,357 names either
    way -- there is no whitespace anywhere in the `player` column), so the whole
    1.679% is the casefold.
    """
    return name.strip().casefold()


#: The two normalizers this census counts under, by name. **The lab has declared
#: neither as the subject.** The design names the key and never says which
#: spelling of `player` it means, so this module counts under both and refuses
#: to pick; picking is a declaration for the design to make and it moves every
#: athlete-clustered interval (section 10's own athlete figure is 9,170 for
#: `player_points` under `raw` and 8,803 under `casefold`, so adopting the fold
#: widens those intervals by about sqrt(9170/8803) = 2.1%).
SUBJECT_NORMALIZERS: Mapping[str, Subject] = {
    "raw": raw_subject,
    "casefold": casefold_subject,
}


# --------------------------------------------------------------------------
# What a census is
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class MarketCount:
    """One market's row count and its two wager counts.

    `quotes` is rows. `wagers_raw` and `wagers_folded` are distinct `WAGER_KEY`
    tuples under the two named normalizers. A row count is never a wager count
    anywhere in this module, which is the whole point of carrying both.
    """

    market: str
    quotes: int
    wagers_raw: int
    wagers_folded: int
    priced: bool

    @property
    def collapsed(self) -> int:
        return self.wagers_raw - self.wagers_folded


@dataclass(frozen=True)
class Collision:
    """One folded name whose raw spellings collapse wager keys.

    `same_book` is measured at the WAGER KEY, not at the name: one book quoting
    'AJ Storr' on Tuesday and 'Aj Storr' on Friday is two wagers, and only two
    spellings from one book at ONE key is a duplicated quote.
    """

    folded: str
    spellings: tuple[str, ...]
    books_by_spelling: Mapping[str, tuple[str, ...]]
    wagers_collapsed: int
    same_book: bool
    roster_ambiguous: bool
    odds_disagreements: int


@dataclass(frozen=True)
class Census:
    """Every count this gate takes, with the fingerprint of what it counted."""

    source_path: str
    source_sha256: str
    source_bytes: int
    rows_scanned: int
    player_quotes: int
    events: int
    game_ids: int
    slate_dates: int
    books: tuple[str, ...]
    seasons: tuple[str, ...]
    segments: tuple[str, ...]
    snapshot_phases: tuple[str, ...]
    subjects_raw: int
    subjects_folded: int
    points_subjects_raw: int
    points_subjects_folded: int
    by_market: tuple[MarketCount, ...]
    collisions: tuple[Collision, ...]
    ambiguous_subjects: tuple[tuple[str, str, tuple[str, ...]], ...]
    roster_checked: bool
    events_with_two_game_ids: int
    null_key_fields: Mapping[str, int]

    # -- totals, all derived so no two of them can disagree --------------
    @property
    def total_raw(self) -> int:
        return sum(m.wagers_raw for m in self.by_market)

    @property
    def total_folded(self) -> int:
        return sum(m.wagers_folded for m in self.by_market)

    @property
    def priced_raw(self) -> int:
        return sum(m.wagers_raw for m in self.by_market if m.priced)

    @property
    def priced_folded(self) -> int:
        return sum(m.wagers_folded for m in self.by_market if m.priced)

    @property
    def refused_raw(self) -> int:
        return sum(m.wagers_raw for m in self.by_market if not m.priced)

    @property
    def refused_folded(self) -> int:
        return sum(m.wagers_folded for m in self.by_market if not m.priced)

    @property
    def difference(self) -> int:
        return self.total_raw - self.total_folded

    @property
    def attributed(self) -> int:
        return sum(c.wagers_collapsed for c in self.collisions)

    @property
    def residual(self) -> int:
        """The wagers of the difference that no collision explains. Must be 0."""
        return self.difference - self.attributed

    def market(self, key: str) -> MarketCount | None:
        for count in self.by_market:
            if count.market == key:
                return count
        return None

    def table(self) -> str:
        """The per-market table, printed on every refusal and every pass."""
        lines = [
            f"{'market':26s} {'quotes':>9s} {'raw':>9s} {'folded':>9s} {'delta':>7s}"
        ]
        for count in sorted(self.by_market, key=lambda m: -m.wagers_raw):
            mark = "" if count.priced else "  REFUSED BY NAME"
            lines.append(
                f"{count.market:26s} {count.quotes:9,d} {count.wagers_raw:9,d} "
                f"{count.wagers_folded:9,d} {count.collapsed:7,d}{mark}"
            )
        lines.append(
            f"{'-- priced --':26s} {'':>9s} {self.priced_raw:9,d} "
            f"{self.priced_folded:9,d}"
        )
        lines.append(
            f"{'-- refused by name --':26s} {'':>9s} {self.refused_raw:9,d} "
            f"{self.refused_folded:9,d}"
        )
        lines.append(
            f"{'-- all --':26s} {self.player_quotes:9,d} {self.total_raw:9,d} "
            f"{self.total_folded:9,d} {self.difference:7,d}"
        )
        return "\n".join(lines)


@dataclass(frozen=True)
class Expected:
    """The frozen census this run is checked against, and where each number came from.

    Loaded from `data/processed/cbb_player_census.json`. **No expected count is
    written in this module's body**, so a run cannot be made to pass by editing
    the code that does the comparing; `test_the_expectations_are_not_editable_
    from_the_call_site` walks this module's AST and fails on a literal that
    matches any of them.

    `sources` carries, per field, whether the number is DECLARED by the design
    (section 6's ten per-market wager counts, section 10's two totals and its
    athlete figure, the verdict table's store census) or PINNED here from a
    measurement the design never declared. A pinned number is not evidence of
    anything today -- it was measured and then compared with itself -- and can
    only ever refuse later. The refusal message says which each one is.
    """

    schema_version: int
    source_path: str
    source_sha256: str
    source_bytes: int
    quotes: Mapping[str, int]
    wagers_raw: Mapping[str, int]
    invariants: Mapping[str, object]
    subjects: Mapping[str, int]
    totals: Mapping[str, int]
    sources: Mapping[str, str]
    declared_subject: str | None
    notes: Mapping[str, str] = field(default_factory=dict)

    def source_of(self, name: str) -> str:
        return str(self.sources.get(name, "PINNED (measured here, not declared)"))


@dataclass(frozen=True)
class Attribution:
    """What `reconcile` returns when it does not raise. Never a bool.

    A bool is droppable -- `if not gate(): pass` is one keystroke from `gate()`
    on its own line -- so the only two outcomes are this record and an exception.

    `checked` is every clause the gate ATTEMPTED and `compared_checks` is how
    many of them compared a value against an expectation the artifact carried.
    The two are equal on every attribution `reconcile` can now return, because
    an absent expectation raises -- and they are reported separately anyway, so
    that "52 clauses ran" is a number a reader can check rather than infer from
    `declared_checks + pinned_checks`, which are a partition of `checked` by
    where the expectation came from and were reproduced in full by a record
    with every value deleted.
    """

    census: Census
    expected: Expected
    checked: tuple[str, ...]
    declared_checks: int
    pinned_checks: int
    compared_checks: int

    def report(self) -> str:
        return (
            f"{self.census.total_raw:,} wagers under `raw` and "
            f"{self.census.total_folded:,} under `casefold`, a difference of "
            f"{self.census.difference:,} ("
            f"{self.census.difference / max(self.census.total_raw, 1) * 100:.3f}% "
            f"of the raw count), attributed in full to "
            f"{len(self.census.collisions)} collision groups with residual "
            f"{self.census.residual}. Priced markets only: "
            f"{self.census.priced_raw:,} raw / {self.census.priced_folded:,} "
            f"folded; the {self.census.refused_raw:,} wagers on "
            f"{', '.join(MARKETS_REFUSED_BY_NAME)} are in neither.\n"
            f"{self.census.table()}"
        )


# --------------------------------------------------------------------------
# Taking the census
# --------------------------------------------------------------------------


def _digest(path: Path) -> tuple[str, int]:
    """sha256 and byte length, read in blocks.

    The store is a symlink into a shared tree. Its target's mtime is older than
    the link's, and nothing in this repository pins its contents, so a gate that
    did not fingerprint it would certify whichever file the link pointed at.
    """
    hasher = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1 << 22)
            if not block:
                break
            size += len(block)
            hasher.update(block)
    return hasher.hexdigest(), size


def _player_chunks(
    path: Path, columns: Iterable[str], *, chunksize: int
) -> Iterable[pd.DataFrame]:
    """Player rows of the store, one chunk at a time, and never more.

    Every read in this module goes through here, so `usecols` and `chunksize`
    are not a habit a later edit can forget: there is one call to `pd.read_csv`
    for the price store and it carries both.
    """
    wanted = list(dict.fromkeys(columns))
    for chunk in pd.read_csv(
        path, usecols=wanted, chunksize=chunksize, dtype=str, low_memory=False
    ):
        rows = len(chunk)
        players = chunk[
            chunk["market"].str.startswith(PLAYER_MARKET_PREFIX, na=False)
        ]
        yield rows, players


def _spellings(path: Path, *, chunksize: int) -> dict[str, set[str]]:
    """Folded name to the raw spellings the store carries for it.

    A first pass over two columns, because a folded name with one spelling can
    never collapse a key and the detail accounting below can then be restricted
    to the 64 that can. Measured: 2.9s over the whole store.
    """
    found: dict[str, set[str]] = defaultdict(set)
    for _, players in _player_chunks(path, ["market", "player"], chunksize=chunksize):
        for name in players["player"].dropna().unique():
            found[casefold_subject(name)].add(name)
    return found


def _roster_ids(
    roster: Path, games: set[str], *, chunksize: int
) -> dict[tuple[str, str], set[str]]:
    """(game_id, folded display name) to the athlete ids the box score carries.

    Restricted to the games the store quotes, which is 1,180 of them, so the
    208 MB roster collapses to 37,248 pairs. Read chunked for the same reason
    the store is.
    """
    ids: dict[tuple[str, str], set[str]] = defaultdict(set)
    for chunk in pd.read_csv(
        roster,
        usecols=["game_id", "athlete_id", "athlete_display_name"],
        chunksize=chunksize,
        dtype=str,
        low_memory=False,
    ):
        chunk = chunk[chunk["game_id"].isin(games)]
        for game, name, athlete in zip(
            chunk["game_id"], chunk["athlete_display_name"], chunk["athlete_id"]
        ):
            if isinstance(name, str) and isinstance(athlete, str):
                ids[(game, casefold_subject(name))].add(athlete)
    return ids


def census(
    path: Path | str = DEFAULT_STORE_PATH,
    *,
    roster: Path | str | None,
    chunksize: int = CHUNK_ROWS,
) -> Census:
    """Count the wagers this lab would grade, twice, and enumerate the difference.

    `roster` is keyword and has NO default: the caller must decide. Passing
    `None` runs the census without the roster and records `roster_checked=False`,
    and `reconcile` then RAISES rather than passing a gate two of whose seven
    clauses did not run. A gate that silently skipped its own check is not a
    gate, which is the defect the demotion gate shipped when a corrupt ledger
    read as "no allowlisted market has fallen through its floor".

    Cost, measured 2026-09-06 on the 977,613,435-byte store: 3.0s for the name
    pass, 6.8s for the key pass, 1.2s for the roster, about 12s in total and
    under 400 MB resident. It is a gate, run once before a grading run, not a
    hot loop.
    """
    store = Path(path)
    digest, size = _digest(store)
    spellings = _spellings(store, chunksize=chunksize)
    collision_names = {
        folded for folded, raw in spellings.items() if len(raw) > 1
    }

    subject_index = WAGER_KEY.index(SUBJECT_COLUMN)
    market_index = WAGER_KEY.index("market")
    columns = list(WAGER_KEY) + [
        "book",
        "season",
        "slate_date",
        "game_id",
        "american_odds",
    ]

    quotes: Counter[str] = Counter()
    raw_keys: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    folded_keys: dict[str, set[tuple[str, ...]]] = defaultdict(set)
    detail: dict[tuple[str, ...], dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    detail_odds: dict[tuple[str, ...], set[str]] = defaultdict(set)
    seasons: set[str] = set()
    segments: set[str] = set()
    phases: set[str] = set()
    books: set[str] = set()
    dates: set[str] = set()
    event_games: dict[str, set[str]] = defaultdict(set)
    nulls: Counter[str] = Counter()
    rows_scanned = 0
    player_quotes = 0

    for rows, players in _player_chunks(store, columns, chunksize=chunksize):
        rows_scanned += rows
        if players.empty:
            continue
        player_quotes += len(players)
        quotes.update(players["market"])
        seasons.update(players["season"].dropna().unique())
        segments.update(players["segment"].dropna().unique())
        phases.update(players["snapshot_phase"].dropna().unique())
        books.update(players["book"].dropna().unique())
        dates.update(players["slate_date"].dropna().unique())
        for column in WAGER_KEY:
            nulls[column] += int(players[column].isna().sum())
        for event, game in zip(players["event_id"], players["game_id"]):
            event_games[str(event)].add(str(game))
        held = [players[column].tolist() for column in WAGER_KEY]
        book_column = players["book"].tolist()
        odds_column = players["american_odds"].tolist()
        for position in range(len(players)):
            row = tuple(str(column[position]) for column in held)
            market = row[market_index]
            raw_keys[market].add(row)
            folded = casefold_subject(row[subject_index])
            folded_row = (
                row[:subject_index] + (folded,) + row[subject_index + 1 :]
            )
            folded_keys[market].add(folded_row)
            if folded in collision_names:
                detail[folded_row][row[subject_index]].add(book_column[position])
                detail_odds[folded_row].add(odds_column[position])

    refused = set(MARKETS_REFUSED_BY_NAME)
    by_market = tuple(
        MarketCount(
            market=market,
            quotes=int(quotes[market]),
            wagers_raw=len(raw_keys[market]),
            wagers_folded=len(folded_keys[market]),
            priced=market not in refused,
        )
        for market in sorted(raw_keys)
    )

    quoted_games = {game for games in event_games.values() for game in games}
    roster_ids: dict[tuple[str, str], set[str]] = {}
    if roster is not None:
        roster_ids = _roster_ids(Path(roster), quoted_games, chunksize=chunksize)

    collisions = _collisions(
        detail,
        detail_odds,
        spellings,
        event_games=event_games,
        roster_ids=roster_ids,
        roster_checked=roster is not None,
        subject_index=subject_index,
    )

    subjects_raw: set[tuple[str, str]] = set()
    subjects_folded: set[tuple[str, str]] = set()
    points_raw: set[tuple[str, str]] = set()
    points_folded: set[tuple[str, str]] = set()
    for market, keys in raw_keys.items():
        for key in keys:
            subject = (key[0], key[subject_index])
            subjects_raw.add(subject)
            if market == "player_points":
                points_raw.add(subject)
    ambiguous: list[tuple[str, str, tuple[str, ...]]] = []
    seen_pairs: set[tuple[str, str]] = set()
    for market, keys in folded_keys.items():
        for key in keys:
            subject = (key[0], key[subject_index])
            subjects_folded.add(subject)
            if market == "player_points":
                points_folded.add(subject)
            if roster is None:
                continue
            for game in event_games[key[0]]:
                pair = (game, key[subject_index])
                if pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                athletes = roster_ids.get(pair, set())
                if len(athletes) > 1:
                    ambiguous.append((game, key[subject_index], tuple(sorted(athletes))))

    return Census(
        source_path=str(store),
        source_sha256=digest,
        source_bytes=size,
        rows_scanned=rows_scanned,
        player_quotes=player_quotes,
        events=len(event_games),
        game_ids=len(quoted_games),
        slate_dates=len(dates),
        books=tuple(sorted(books)),
        seasons=tuple(sorted(seasons)),
        segments=tuple(sorted(segments)),
        snapshot_phases=tuple(sorted(phases)),
        subjects_raw=len(subjects_raw),
        subjects_folded=len(subjects_folded),
        points_subjects_raw=len(points_raw),
        points_subjects_folded=len(points_folded),
        by_market=by_market,
        collisions=collisions,
        ambiguous_subjects=tuple(sorted(ambiguous)),
        roster_checked=roster is not None,
        events_with_two_game_ids=sum(
            1 for games in event_games.values() if len(games) > 1
        ),
        null_key_fields={column: int(count) for column, count in sorted(nulls.items())},
    )


def _collisions(
    detail: Mapping[tuple[str, ...], Mapping[str, set[str]]],
    detail_odds: Mapping[tuple[str, ...], set[str]],
    spellings: Mapping[str, set[str]],
    *,
    event_games: Mapping[str, set[str]],
    roster_ids: Mapping[tuple[str, str], set[str]],
    roster_checked: bool,
    subject_index: int,
) -> tuple[Collision, ...]:
    """Group the collapsing keys by folded name, and flag the two that refuse.

    A folded name is a `Collision` only when it actually collapses a key. 64
    folded names carry two spellings on this store and all 64 collapse; a name
    quoted under two spellings on two different games collapses nothing and
    would not appear here.
    """
    collapsed: Counter[str] = Counter()
    same_book: set[str] = set()
    odds_disagree: Counter[str] = Counter()
    ambiguous: set[str] = set()
    for folded_row, per_spelling in detail.items():
        if len(per_spelling) < 2:
            continue
        folded = folded_row[subject_index]
        collapsed[folded] += len(per_spelling) - 1
        booksets = list(per_spelling.values())
        if set.intersection(*booksets):
            same_book.add(folded)
        if len(detail_odds[folded_row]) > 1:
            odds_disagree[folded] += 1
        if roster_checked:
            for game in event_games.get(folded_row[0], ()):
                if len(roster_ids.get((game, folded), set())) > 1:
                    ambiguous.add(folded)

    books_by_spelling: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    for folded_row, per_spelling in detail.items():
        folded = folded_row[subject_index]
        if folded not in collapsed:
            continue
        for spelling, seen in per_spelling.items():
            books_by_spelling[folded][spelling].update(seen)

    return tuple(
        Collision(
            folded=folded,
            spellings=tuple(sorted(spellings[folded])),
            books_by_spelling={
                spelling: tuple(sorted(seen))
                for spelling, seen in sorted(books_by_spelling[folded].items())
            },
            wagers_collapsed=count,
            same_book=folded in same_book,
            roster_ambiguous=folded in ambiguous,
            odds_disagreements=int(odds_disagree[folded]),
        )
        for folded, count in sorted(collapsed.items())
    )


# --------------------------------------------------------------------------
# The frozen expectations
# --------------------------------------------------------------------------


def load_expected(path: Path | str = DEFAULT_EXPECTED_PATH) -> Expected:
    """Read the frozen census artifact. It is the only source of an expected count.

    Raises rather than defaulting: a gate whose expectations are missing has no
    expectations, and returning an empty record would let every count through.
    """
    target = Path(path)
    if not target.is_file():
        raise WagerCountMismatch(
            f"{target} is missing. It carries every expected count this gate "
            "compares against, and without it nothing is being checked. A gate "
            "with no expectations passes every store, which is worse than no "
            "gate because it prints a tick."
        )
    record = json.loads(target.read_text(encoding="utf-8"))
    return Expected(
        schema_version=int(record["schema_version"]),
        source_path=str(record["source"]["path"]),
        source_sha256=str(record["source"]["sha256"]),
        source_bytes=int(record["source"]["bytes"]),
        quotes={str(k): int(v) for k, v in record["quotes"].items()},
        wagers_raw={str(k): int(v) for k, v in record["wagers_raw"].items()},
        invariants=dict(record["invariants"]),
        subjects={str(k): int(v) for k, v in record["subjects"].items()},
        totals={str(k): int(v) for k, v in record["totals"].items()},
        sources={str(k): str(v) for k, v in record["sources"].items()},
        declared_subject=record.get("declared_subject"),
        notes=dict(record.get("notes", {})),
    )


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------


def reconcile(taken: Census, expected: Expected) -> Attribution:
    """Raise unless every count is what was declared and every collapse is named.

    Returns an `Attribution` or raises `WagerCountMismatch`. There is no third
    outcome and no bool.

    **An expectation the artifact does not carry is a complaint, not a skip.**
    Every value comparison below is guarded by `if want is not None`, and until
    this commit an absent key meant the clause was silently not compared while
    `note()` still appended it to `Attribution.checked` and counted it into
    `declared_checks` or `pinned_checks`. The two counts are what stands for "52
    clauses ran", and they came off the `sources` block rather than off the
    value sections, so they were reproduced in full by a record with every value
    deleted. Measured before the repair, against the real module: an
    expectations record whose `quotes`, `totals`, `subjects` and `invariants`
    were emptied to `{}` reconciled a census with three quotes where the record
    had been written from a census with two, returned normally,
    `len(checked) == 30`, `pinned_checks == 30`, and `"quotes[player_points]" in
    checked` was True. `load_expected`'s own docstring says an empty record
    "would let every count through" and it guards only against a missing FILE.

    So the clauses whose expectation is absent are collected and refused
    together at the end, naming each one. A count that is present and moved
    already raises; a count that has been deleted from the artifact now raises
    too, and the gate cannot certify a store on a clause it did not compare.
    `Attribution.compared_checks` is the number of clauses that compared a
    value, beside the `len(checked)` that counts every clause attempted, so a
    reader can see the difference rather than infer it.
    """
    complaints: list[str] = []
    checked: list[str] = []
    missing: list[str] = []
    declared = 0
    pinned = 0
    compared = 0

    def note(name: str) -> None:
        nonlocal declared, pinned
        checked.append(name)
        if expected.source_of(name).startswith("design"):
            declared += 1
        else:
            pinned += 1

    def carried(name: str, want: object | None) -> object | None:
        """Record whether the artifact carried an expectation for `name`.

        Returns `want` unchanged so the comparison below reads the same as it
        did; the bookkeeping is the point. A clause reaching here with `None`
        did not compare anything and must not be counted as though it had.
        """
        nonlocal compared
        if want is None:
            missing.append(name)
        else:
            compared += 1
        return want

    if taken.source_sha256 != expected.source_sha256:
        complaints.append(
            f"The price store is not the one this census was taken against. "
            f"Pinned sha256 {expected.source_sha256} over "
            f"{expected.source_bytes:,} bytes; this file is "
            f"{taken.source_sha256} over {taken.source_bytes:,} bytes. "
            f"{taken.source_path} is a symlink into a shared tree, so an "
            "unpinned gate certifies whichever file the link pointed at."
        )
    note("source_sha256")

    markets = {count.market for count in taken.by_market}
    absent = sorted(set(expected.wagers_raw) - markets)
    surplus = sorted(markets - set(expected.wagers_raw))
    if absent or surplus:
        complaints.append(
            f"The store's markets are not the census's. Declared and absent: "
            f"{absent}. Present and undeclared: {surplus}. A market that "
            "appeared is a market nobody registered a hypothesis for; a market "
            "that vanished is a denominator that moved without anyone saying so."
        )
    for count in sorted(taken.by_market, key=lambda m: m.market):
        note(f"wagers_raw[{count.market}]")
        want_wagers = carried(
            f"wagers_raw[{count.market}]", expected.wagers_raw.get(count.market)
        )
        if want_wagers is not None and count.wagers_raw != want_wagers:
            complaints.append(
                f"{count.market}: {count.wagers_raw:,} wagers under `raw`, "
                f"expected {want_wagers:,} (difference "
                f"{count.wagers_raw - want_wagers:+,}). Source of the "
                f"expectation: {expected.source_of(f'wagers_raw[{count.market}]')}."
            )
        note(f"quotes[{count.market}]")
        want_quotes = carried(
            f"quotes[{count.market}]", expected.quotes.get(count.market)
        )
        if want_quotes is not None and count.quotes != want_quotes:
            complaints.append(
                f"{count.market}: {count.quotes:,} quotes, expected "
                f"{want_quotes:,} (difference {count.quotes - want_quotes:+,}). "
                f"Source of the expectation: "
                f"{expected.source_of(f'quotes[{count.market}]')}."
            )

    for name, value in (
        ("total_raw", taken.total_raw),
        ("total_folded", taken.total_folded),
        ("priced_raw", taken.priced_raw),
        ("priced_folded", taken.priced_folded),
        ("refused_raw", taken.refused_raw),
        ("refused_folded", taken.refused_folded),
    ):
        note(name)
        want = carried(name, expected.totals.get(name))
        if want is not None and value != want:
            complaints.append(
                f"{name}: {value:,}, expected {want:,} (difference "
                f"{value - want:+,}). Source of the expectation: "
                f"{expected.source_of(name)}."
            )

    note("residual")
    if taken.residual != 0:
        complaints.append(
            f"The gap between the two counts is not fully attributed. "
            f"{taken.total_raw:,} wagers under `raw` and "
            f"{taken.total_folded:,} under `casefold` is a difference of "
            f"{taken.difference:,}; {taken.attributed:,} of them are named by "
            f"{len(taken.collisions)} collision groups, leaving a residual of "
            f"{taken.residual:,}. The residual must be 0, not small: this gate "
            "is not the claim that the two numbers are equal -- they are not, "
            "and both are correct counts of the same rows -- it is the claim "
            "that every wager of the difference is named."
        )

    note("same_book_collisions")
    duplicated = [c for c in taken.collisions if c.same_book]
    if duplicated:
        complaints.append(
            f"{len(duplicated)} collision group(s) carry one book quoting two "
            f"spellings at ONE wager key: {[c.folded for c in duplicated][:8]}. "
            "That is a duplicated quote, not a spelling fold, and folding it "
            "away hides the store defect `stores.dedupe_prices` exists to "
            "catch. Measured when this gate was written: 0 of 4,396."
        )

    note("roster_ambiguous_collisions")
    merging = [c for c in taken.collisions if c.roster_ambiguous]
    if merging:
        complaints.append(
            f"{len(merging)} collision group(s) fold two athlete_ids inside one "
            f"game: {[c.folded for c in merging][:8]}. That is destroying a "
            "subject, not normalising a spelling."
        )

    note("roster_checked")
    if not taken.roster_checked:
        complaints.append(
            "This census ran without a roster, so the two clauses that read one "
            "-- whether a fold merges two athlete_ids, and how many quoted "
            "subjects are ambiguous before any fold -- did not run. A gate that "
            "skipped its own check is not a gate; pass `roster=` or do not "
            "grade."
        )

    for count in taken.by_market:
        if count.priced == (count.market in set(MARKETS_REFUSED_BY_NAME)):
            complaints.append(
                f"{count.market} is marked priced={count.priced} and "
                f"`player_rates.MARKETS_REFUSED_BY_NAME` says otherwise. The "
                "two markets refused by name are counted in their own bucket "
                "and never summed into the priced total: a run that grades "
                f"{taken.total_raw:,} cells has priced two refused markets."
            )

    for name, value in (
        ("rows_scanned", taken.rows_scanned),
        ("player_quotes", taken.player_quotes),
        ("events", taken.events),
        ("game_ids", taken.game_ids),
        ("slate_dates", taken.slate_dates),
        ("events_with_two_game_ids", taken.events_with_two_game_ids),
        ("books", len(taken.books)),
        ("collision_groups", len(taken.collisions)),
        ("ambiguous_subjects", len(taken.ambiguous_subjects)),
    ):
        note(name)
        want = carried(name, expected.invariants.get(name))
        if want is not None and value != int(want):
            complaints.append(
                f"{name}: {value:,}, expected {int(want):,}. Source of the "
                f"expectation: {expected.source_of(name)}."
            )
    for name, value in (
        ("seasons", taken.seasons),
        ("segments", taken.segments),
        ("snapshot_phases", taken.snapshot_phases),
    ):
        note(name)
        want = carried(name, expected.invariants.get(name))
        if want is not None and list(value) != list(want):
            complaints.append(
                f"{name}: {list(value)}, expected {list(want)}. Source of the "
                f"expectation: {expected.source_of(name)}."
            )

    for name, value in (
        ("raw", taken.subjects_raw),
        ("folded", taken.subjects_folded),
        ("player_points_raw", taken.points_subjects_raw),
        ("player_points_folded", taken.points_subjects_folded),
    ):
        note(f"subjects[{name}]")
        want = carried(f"subjects[{name}]", expected.subjects.get(name))
        if want is not None and value != want:
            complaints.append(
                f"subjects[{name}]: {value:,}, expected {want:,}. These are the "
                "athlete clusters section 10 says the interval must be widened "
                "to; a change here moves every athlete-clustered interval. "
                f"Source of the expectation: {expected.source_of(f'subjects[{name}]')}."
            )

    nulls = {k: v for k, v in taken.null_key_fields.items() if v}
    note("null_key_fields")
    if nulls:
        complaints.append(
            f"The wager key carries nulls: {nulls}. A null in the key makes two "
            "different wagers compare equal, and the count that comes back is "
            "smaller for a reason nobody wrote down."
        )

    if missing:
        complaints.append(
            f"{len(missing)} clause(s) were counted as checked and never "
            f"compared, because the frozen artifact carries no expectation for "
            f"them: {missing}. `Attribution.checked` would report "
            f"{len(checked)} clauses and only {compared} of the value "
            "comparisons ran. A gate that certifies a store on a clause it did "
            "not compare is printing a tick it did not earn -- which is worse "
            "than no gate -- and this is what a regenerated "
            "cbb_player_census.json that dropped a `quotes[...]`, a `totals` or "
            "a `subjects` entry while keeping its `sources` row would look "
            "like. Restore the expectation or say, in the artifact, that the "
            "clause no longer applies."
        )

    if complaints:
        raise WagerCountMismatch(
            "The wager census does not reconcile, so nothing may be graded. "
            "Design section 10: 'The run stops until it reconciles.'\n\n"
            + "\n\n".join(f"  * {line}" for line in complaints)
            + "\n\n"
            + taken.table()
        )
    return Attribution(
        census=taken,
        expected=expected,
        checked=tuple(checked),
        declared_checks=declared,
        pinned_checks=pinned,
        compared_checks=compared,
    )


# --------------------------------------------------------------------------
# The receipt, and what a grading entry point must call
# --------------------------------------------------------------------------

#: Set by `assert_reconciles`, read by `guard_graded_frame`. A dict and not a
#: file: a file on disk would be a grant, it would survive the store changing
#: under it, and a later run would grade on somebody else's tick. This lives for
#: the length of one process, keyed by the digest of the store that reconciled.
_RECONCILED: dict[str, Attribution] = {}

#: The entry points through which a player wager could reach a grading number.
#: Found by reading the tree for what BUILDS an interval or PRINTS a verdict,
#: not by matching one spelling of one verb -- which is the mistake the first
#: version of this list made, and it cost two of the four:
#:
#: * `reports.forecast_skill.build_record` is design section 10's own metric --
#:   it de-vigs, scores log loss and Brier, and builds the clustered intervals.
#:   It already carries `player` as an optional column and casefolds it in the
#:   de-vig pair scope, so a frame of player props handed to it today would be
#:   graded with no census having run. That is the live route, and it is why the
#:   guard is wired INTO it rather than only asserted about it.
#: * `reports.price_backtest.settled_opinions` is the ROI half: the population
#:   the market-against-model regression runs over. One production caller,
#:   `scripts/run_price_backtest.py`.
#: * `forward_evidence.render_ledger` prints the Opinions table: ROI, a 95%
#:   interval, a family-corrected interval and a Verdict, per market and per
#:   tier, over EVERY settled row -- `_bet_rows` excludes player props from the
#:   BETS table and from that table only, because a prop nobody can place is
#:   not a bet, and the evidence still belongs in Opinions. Added 2026-09-06.
#: * `forward_evidence.report_payload` is the same computation as JSON. Guarded
#:   separately, not by delegation: `write_report` calls both and
#:   `reports.what_we_can_claim` calls this one alone. Added 2026-09-06.
#: * `reachability.build_record` splits that same forward ledger by market,
#:   tier and price survival and turns each cell into a clustered interval and
#:   a verdict sentence. `scripts/run_reachability.py` defaults `--bets` to
#:   `data/processed/cbb_forward_evidence.csv`. Added 2026-09-06.
#:
#: Each name is `module.function`, and each function calls `guard_graded_frame`
#: as its FIRST statement, before it reads a probability or derives a column.
#: `tests/test_player_census_reconciles.py` asserts that every name here calls
#: it first, that each refuses a player frame with no receipt, and -- as a
#: floor rather than a proof, in the test's own name -- that no module outside
#: the pinned list builds an interval or scores a probability.
GRADING_ENTRY_POINTS: tuple[str, ...] = (
    "cbb_betting_lab.forward_evidence.render_ledger",
    "cbb_betting_lab.forward_evidence.report_payload",
    "cbb_betting_lab.reachability.build_record",
    "cbb_betting_lab.reports.forecast_skill.build_record",
    "cbb_betting_lab.reports.price_backtest.settled_opinions",
)


def assert_reconciles(
    *,
    store: Path | str = DEFAULT_STORE_PATH,
    roster: Path | str | None = DEFAULT_ROSTER_PATH,
    expected: Path | str = DEFAULT_EXPECTED_PATH,
    chunksize: int = CHUNK_ROWS,
) -> Attribution:
    """Take the census, reconcile it, and record the receipt for this process.

    This is what a grading run calls before any scoring code runs. It raises on
    anything unreconciled and returns the attribution otherwise.
    """
    attribution = reconcile(
        census(store, roster=roster, chunksize=chunksize), load_expected(expected)
    )
    _RECONCILED[attribution.census.source_sha256] = attribution
    return attribution


def reconciled() -> tuple[Attribution, ...]:
    """Every census that has reconciled in this process. Empty before the gate runs."""
    return tuple(_RECONCILED.values())


def forget_reconciliations() -> None:
    """Drop the receipts. For tests that must see the gate fail closed."""
    _RECONCILED.clear()


def player_markets_in(frame: pd.DataFrame) -> tuple[str, ...]:
    """The player markets a frame carries, by name, sorted."""
    if frame is None or len(frame) == 0 or "market" not in getattr(frame, "columns", ()):
        return ()
    markets = frame["market"].astype(str)
    found = markets[markets.str.startswith(PLAYER_MARKET_PREFIX, na=False)]
    return tuple(sorted(set(found)))


def guard_graded_frame(frame: pd.DataFrame, *, what: str) -> tuple[str, ...]:
    """Refuse a frame carrying player wagers until this process has reconciled.

    Returns the player markets it found, which is `()` on every team-market run
    and costs one vectorised prefix test on a frame already in memory. It raises
    on a player market with no receipt, so the gate cannot be walked past by
    wiring a player frame into an existing report.

    Fail CLOSED: the receipt starts empty, so a caller who never ran the census
    is refused rather than waved through.
    """
    found = player_markets_in(frame)
    if not found:
        return ()
    if not _RECONCILED:
        raise WagerCountMismatch(
            f"{what} was handed {len(found)} player market(s) {list(found)} and "
            "no wager census has reconciled in this process. Design section 10 "
            "gates grading on reconciling the store's wager count "
            "(261,870 under the book's own spelling, 257,474 under a casefold, "
            "a difference of 4,396 that must be named wager by wager) and the "
            "run stops until it does. Call "
            "`cbb_betting_lab.models.player_census.assert_reconciles()` first, "
            "or grade nothing."
        )
    return found
