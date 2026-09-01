#!/usr/bin/env python3
"""Settle last night's frozen opinions, append them to the ledger, re-render the report.

    # What the gameday workflow runs, every slot:
    PYTHONPATH=src python scripts/run_forward_evidence.py --settle --competition cbb

    # Re-render the report from the ledger. Settles nothing, costs nothing:
    PYTHONPATH=src python scripts/run_forward_evidence.py --report-only

This is stage two and stage three of `cbb_betting_lab.forward_evidence` wired to
the filesystem the workflow hands it. Stage one — freezing the opinions before
tip — belongs to the card run; by the time this script executes, the evidence
already exists and this pass can only record it faithfully or lose it.

## Why the default is the read-only one

`--settle` writes to a store that **can only grow and cannot be rebuilt**. The
prices these opinions were frozen at were quoted for a few minutes on a Tuesday
in January and are gone; a night that was not frozen and settled is a night of
clean out-of-sample data gone permanently, and in this sport a night is up to
200 games. So settling is an explicit act and a bare invocation does the
harmless thing, the same way `run_retention_probe.py` is dry until `--live`.

`--report-only` exists because of the sibling labs' rule that **improving a
report's wording must never cost anything twice**. There the cost was credits;
here it is the far worse currency of a settle pass run for no reason against a
half-published box score. The report is a pure function of the ledger, so
re-rendering it needs neither the results tables nor the team index, and this
flag reads neither.

## What "an error" means here, and what it deliberately does not

**A day with no snapshot is not an error.** There are real days with no
basketball, the season has a summer, and a lab that exits red on an empty
August night trains its operator to ignore red. The pass says so in
`SettlementResult.summary_line()`'s own words and returns 0.

**A missing processed table is an error.** Settling against a table that is not
there does not fail — it *succeeds quietly and wrongly*. Every fixture would
miss, every row would be `UNSETTLEABLE`, and once the 14-day patience window
closed that verdict would be written into an append-only ledger where nothing
can revise it. The same argument applies to the raw schedule the team-name index
is built from: an empty index resolves no fixture, and a night of "no game in
the results tables matches" is indistinguishable from a night that genuinely was
not played. Both are refused up front, before a single marker is written.

**A single unreadable snapshot degrades rather than crashes.** It is named, it
is counted, and the other days of the archive settle around it — the brief's
rule that a run degrades rather than empties. See `unreadable_snapshots()` for
what this script can and cannot do about one.

## The accounting identity, printed rather than assumed

Cooper's rule, ported from the NHL lab where the identity is
`priced = no_opinion + below_threshold + unparseable + ambiguous + bets`. Here
the pass has three of them and every one is printed:

    snapshots seen  = settled now + waiting + settled in an earlier pass
    rows seen       = settled + void + unsettleable
    unsettleable    = no fixture + ambiguous player + futures deferred
                      + raised inside settle + everything else

and one that is not arithmetic on the same object at all, which is what makes
it worth printing: **the rows this pass graded, against the rows the ledger
actually grew by.** The first three can only catch a counter that was never
incremented; the fourth catches a pass that graded four hundred opinions and
wrote none of them, which is the failure that looks exactly like a quiet night.

`rows_without_a_price` and `rows_without_a_fixture` are sub-counts and are
printed under the total they belong to rather than beside it, because a reader
who adds a sub-count into a total gets a number that reconciles to nothing.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from cbb_betting_lab import experiment_ledger, forward_evidence as fe, season, stores
from cbb_betting_lab.competitions import DEFAULT_COMPETITION_KEY, Competition, competition_for
from cbb_betting_lab.config import DATA_DIR, OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from cbb_betting_lab.providers import team_names

#: Where the workflow restores the frozen snapshots to, and where the card run
#: writes them. `forward_evidence.snapshot_dir` appends `priced_snapshots`.
ARCHIVE_DIR = DATA_DIR / "archive"

#: The three processed tables a settle pass reads. Every one of them is
#: required: the first two settle team and player markets, and the third is
#: where the first-basket markets settle from. A missing one is refused rather
#: than treated as an empty frame — see the module docstring.
REQUIRED_TABLES: tuple[tuple[str, str], ...] = (
    ("team_games", "cbb_team_games.csv"),
    ("player_games", "cbb_player_games.csv"),
    ("game_segments", "cbb_game_segments.csv"),
)


class InputError(RuntimeError):
    """A precondition that must hold before anything is settled, and does not.

    Raised rather than warned about, and raised *before* the pass rather than
    during it. Every failure in this class has the same shape: it would not
    crash the settle pass, it would make the pass produce confident wrong
    answers into a store that cannot be revised.
    """


# --------------------------------------------------------------------------
# Loading what a settle pass needs
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Inputs:
    """The results tables and the name index, loaded once for the whole pass."""

    team_games: pd.DataFrame
    player_games: pd.DataFrame
    game_segments: pd.DataFrame
    team_index: team_names.TeamIndex
    #: The seasons whose schedules the index was built from, for the log line.
    index_seasons: tuple[int, ...]

    def summary_lines(self) -> list[str]:
        return [
            f"Tables:     team_games {len(self.team_games):,} rows, "
            f"player_games {len(self.player_games):,} rows, "
            f"game_segments {len(self.game_segments):,} rows.",
            f"Team index: {len(self.team_index.aliases):,} aliases over "
            f"{len(self.team_index.display):,} teams, built from season(s) "
            f"{', '.join(str(s) for s in self.index_seasons) or 'none'}"
            + (
                f"; {len(self.team_index.ambiguous):,} alias(es) are claimed by "
                "more than one programme and resolve to nothing, which is the "
                "safe direction."
                if self.team_index.ambiguous
                else "."
            ),
        ]


def load_tables(processed_dir: Path) -> dict[str, pd.DataFrame]:
    """The three processed tables, or an `InputError` naming what is missing.

    Existence is checked for all three before any of them is read, so an
    operator is told everything that is wrong in one run rather than one
    missing file per attempt.
    """
    directory = Path(processed_dir)
    missing = [name for _, name in REQUIRED_TABLES if not (directory / name).is_file()]
    if missing:
        raise InputError(
            f"No processed table at {directory}/{{{', '.join(missing)}}}. "
            "Run `scripts/build_datasets.py` first. This is an error rather "
            "than an empty frame because settling against a table that is not "
            "there does not fail — every fixture would miss, every frozen "
            "opinion would be recorded UNSETTLEABLE, and after the "
            f"{fe.PATIENCE_DAYS}-day patience window that verdict is written "
            "into an append-only ledger that nothing can revise."
        )
    return {
        attribute: pd.read_csv(directory / name) for attribute, name in REQUIRED_TABLES
    }


def snapshot_seasons(archive_dir: Path) -> tuple[int, ...]:
    """The seasons the archived snapshot days belong to, labelled by end year.

    Derived from the snapshot filenames rather than from today's date: a pass
    run in November may still be settling a day that hoopR published late, and
    an index built only for the current season would resolve none of it.

    A file whose name is not a slate day contributes no season. It is not
    dropped silently — `unreadable_snapshots` names it — but it cannot say
    which schedule it needs either.
    """
    seasons = {
        season.season_for_slate_date(path.stem)
        for path in fe.snapshot_files(archive_dir)
    }
    return tuple(sorted(s for s in seasons if s))


def load_team_index(
    raw_dir: Path, *, competition: Competition, seasons: tuple[int, ...]
) -> tuple[team_names.TeamIndex, tuple[int, ...]]:
    """The provider-name index, built from the schedules the archive needs.

    Built from the results source, which is `team_names`' first rule: every
    alias comes from the feed that also supplies the settlement, so the two
    sides of the join cannot describe different universes.

    A missing schedule for a season this pass has snapshots for is an
    `InputError` for the same reason a missing results table is. An empty index
    resolves nothing, so every fixture misses, and a night recorded as "no game
    in the results tables matches" is indistinguishable from a night that was
    never played — except that the first one is a bug and is permanent.
    """
    directory = Path(raw_dir) / competition.data_dir_segment / "schedules"
    frames: list[pd.DataFrame] = []
    loaded: list[int] = []
    absent: list[int] = []
    for year in seasons:
        path = directory / f"mbb_schedule_{year}.parquet"
        if not path.is_file():
            absent.append(year)
            continue
        frames.append(pd.read_parquet(path))
        loaded.append(year)
    if absent:
        raise InputError(
            "No cached schedule for season(s) "
            f"{', '.join(str(y) for y in absent)} under {directory}. Run "
            "`scripts/fetch_cbb_data.py` first. The schedule is where the team "
            "name index comes from, and an empty index resolves no fixture at "
            "all: every frozen opinion of those days would be settled as 'no "
            "game in the results tables matches', which is exactly what a night "
            "that was never played looks like."
        )
    if not frames:
        # No snapshots, so no season was asked for. The pass will report zero
        # snapshots seen and the index is never consulted; building an empty
        # one is honest about that rather than loading a schedule to satisfy a
        # type.
        return team_names.TeamIndex(), ()
    schedule = frames[0] if len(frames) == 1 else pd.concat(frames, ignore_index=True)
    return team_names.build_index(schedule), tuple(loaded)


def load_inputs(
    *, processed_dir: Path, raw_dir: Path, archive_dir: Path, competition: Competition
) -> Inputs:
    tables = load_tables(processed_dir)
    index, index_seasons = load_team_index(
        raw_dir, competition=competition, seasons=snapshot_seasons(archive_dir)
    )
    return Inputs(
        team_games=tables["team_games"],
        player_games=tables["player_games"],
        game_segments=tables["game_segments"],
        team_index=index,
        index_seasons=index_seasons,
    )


def unreadable_snapshots(archive_dir: Path) -> list[Path]:
    """Snapshot files this pass cannot parse, named before it starts.

    `forward_evidence.read_snapshot` reads defensively and returns an **empty
    frame** for a file it cannot parse, which is right for a reader and wrong
    for the operator: the settle pass then grades zero rows, writes a `.settled`
    sidecar and moves on, and a day of frozen opinions is quietly recorded as a
    day with nothing in it. This function is the loud half of that, and it is
    all this script can honestly do — the sidecar is written inside the module.

    A corrupt snapshot is therefore reported, counted, and **not** allowed to
    stop the rest of the archive settling. It is deliberately not an error
    status either: it is a permanent fault needing a human, and exiting red on
    every subsequent run would keep the gameday backup trigger from ever
    standing down, which spends a second slate's credits every day for a file
    no run can repair.
    """
    bad: list[Path] = []
    for path in fe.snapshot_files(archive_dir):
        try:
            stores.read_store(path, columns=fe.SNAPSHOT_COLUMNS, for_append=True)
        except stores.CorruptStoreError:
            bad.append(path)
    return bad


# --------------------------------------------------------------------------
# The accounting identity
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Reconciliation:
    """Every counter of a settle pass, and whether they add up.

    Computed from a `SettlementResult` and from the ledger's own length before
    and after the pass. `holds` is checked rather than assumed, and a pass whose
    counters do not reconcile exits non-zero: a row that vanishes without
    appearing in a count is a defect, not a decision.
    """

    snapshots_seen: int
    snapshots_settled: int
    snapshots_waiting: int
    snapshots_settled_earlier: int
    waiting_days: tuple[str, ...]
    rows_seen: int
    rows_settled: int
    rows_void: int
    rows_unsettleable: int
    rows_without_a_price: int
    rows_without_a_fixture: int
    rows_ambiguous_player: int
    rows_futures_deferred: int
    rows_raised_inside_settle: int
    rows_unsettleable_other: int
    ledger_before: int
    ledger_after: int
    rows_appended: int
    snapshots_unreadable: int

    @classmethod
    def of(
        cls, result: fe.SettlementResult, *, ledger_before: int, unreadable: int
    ) -> Reconciliation:
        raised = sum(result.settlement_errors.values())
        return cls(
            snapshots_seen=result.snapshots_seen,
            snapshots_settled=result.snapshots_settled,
            snapshots_waiting=result.snapshots_waiting,
            # Not a counter the module keeps, and it is the residual on
            # purpose: a snapshot the pass neither settled nor waited on is one
            # it recognised as already done, through the sidecar or through the
            # ledger's own set of snapshot dates.
            snapshots_settled_earlier=(
                result.snapshots_seen
                - result.snapshots_settled
                - result.snapshots_waiting
            ),
            waiting_days=tuple(result.waiting_days),
            rows_seen=result.rows_seen,
            rows_settled=result.rows_settled,
            rows_void=result.rows_void,
            rows_unsettleable=result.rows_unsettleable,
            rows_without_a_price=result.rows_without_a_price,
            rows_without_a_fixture=result.rows_without_a_fixture,
            rows_ambiguous_player=result.rows_ambiguous_player,
            rows_futures_deferred=result.rows_futures_deferred,
            rows_raised_inside_settle=raised,
            # The remainder: a market with no registry entry, a commence time
            # nothing can parse, or a quantity the box score does not carry —
            # 3.64% of games record no halftime score, so half markets land
            # here legitimately and often.
            rows_unsettleable_other=(
                result.rows_unsettleable
                - result.rows_without_a_fixture
                - result.rows_ambiguous_player
                - result.rows_futures_deferred
                - raised
            ),
            ledger_before=ledger_before,
            ledger_after=result.ledger_rows,
            rows_appended=result.ledger_rows - ledger_before,
            snapshots_unreadable=unreadable,
        )

    @property
    def holds(self) -> bool:
        return not self.breaks

    @property
    def breaks(self) -> list[str]:
        """Every identity that does not hold, named. Empty is the healthy case."""
        failures: list[str] = []
        if self.snapshots_settled_earlier < 0:
            failures.append(
                f"{self.snapshots_settled:,} settled + {self.snapshots_waiting:,} "
                f"waiting exceeds the {self.snapshots_seen:,} snapshots seen."
            )
        if (
            self.rows_settled + self.rows_void + self.rows_unsettleable
            != self.rows_seen
        ):
            failures.append(
                f"{self.rows_settled:,} settled + {self.rows_void:,} void + "
                f"{self.rows_unsettleable:,} unsettleable is not the "
                f"{self.rows_seen:,} rows seen."
            )
        if self.rows_unsettleable_other < 0:
            failures.append(
                "the named reasons for being unsettleable add to more than the "
                f"{self.rows_unsettleable:,} unsettleable rows."
            )
        if self.rows_without_a_price > self.rows_settled:
            failures.append(
                f"{self.rows_without_a_price:,} settled rows carry no readable "
                f"price, out of {self.rows_settled:,} settled."
            )
        if self.rows_appended < 0:
            failures.append(
                f"the ledger fell from {self.ledger_before:,} rows to "
                f"{self.ledger_after:,}. It is append-only and the prices its "
                "opinions were frozen at are gone."
            )
        if self.rows_appended > self.rows_seen:
            failures.append(
                f"the ledger grew by {self.rows_appended:,} rows while this "
                f"pass graded {self.rows_seen:,}."
            )
        return failures

    def counter_lines(self) -> list[str]:
        """Every counter, with each sub-count under the total it belongs to."""
        waiting = (
            f"  ({', '.join(self.waiting_days)}, inside the "
            f"{fe.PATIENCE_DAYS}-day patience window)"
            if self.waiting_days
            else ""
        )
        lines = [
            f"  snapshots seen                       {self.snapshots_seen:>9,}",
            f"    settled this pass                  {self.snapshots_settled:>9,}",
            f"    waiting on a result                {self.snapshots_waiting:>9,}"
            + waiting,
            f"    settled in an earlier pass         {self.snapshots_settled_earlier:>9,}",
        ]
        if self.snapshots_unreadable:
            lines.append(
                f"    unreadable, named above            {self.snapshots_unreadable:>9,}"
            )
        lines += [
            f"  rows seen                            {self.rows_seen:>9,}",
            f"    settled (won, lost or pushed)      {self.rows_settled:>9,}",
            f"      of those, no readable price      {self.rows_without_a_price:>9,}",
            f"    void                               {self.rows_void:>9,}",
            f"    unsettleable                       {self.rows_unsettleable:>9,}",
            f"      no fixture in the results tables {self.rows_without_a_fixture:>9,}",
            f"      more than one athlete named      {self.rows_ambiguous_player:>9,}",
            f"      futures, deferred not graded     {self.rows_futures_deferred:>9,}",
            f"      raised inside settle             {self.rows_raised_inside_settle:>9,}",
            f"      everything else                  {self.rows_unsettleable_other:>9,}",
            f"  ledger rows before this pass         {self.ledger_before:>9,}",
            f"  ledger rows after                    {self.ledger_after:>9,}",
        ]
        return lines

    def reconciliation_lines(self) -> list[str]:
        """The identity, spelled out as arithmetic a reader can check by eye."""
        verdict = "HOLDS" if self.holds else "DOES NOT HOLD"
        already_held = self.rows_seen - self.rows_appended
        lines = [
            f"  snapshots:    {self.snapshots_settled:,} settled + "
            f"{self.snapshots_waiting:,} waiting + "
            f"{self.snapshots_settled_earlier:,} settled earlier = "
            f"{self.snapshots_seen:,} seen.",
            f"  rows:         {self.rows_settled:,} settled + {self.rows_void:,} "
            f"void + {self.rows_unsettleable:,} unsettleable = "
            f"{self.rows_seen:,} seen.",
            f"  unsettleable: {self.rows_without_a_fixture:,} no fixture + "
            f"{self.rows_ambiguous_player:,} ambiguous player + "
            f"{self.rows_futures_deferred:,} futures + "
            f"{self.rows_raised_inside_settle:,} raised + "
            f"{self.rows_unsettleable_other:,} other = "
            f"{self.rows_unsettleable:,}.",
            # The one that is not arithmetic on the counters themselves. It
            # compares what the pass says it graded against what the file on
            # disk actually grew by, which is the only line here that can catch
            # a pass that graded a night and wrote none of it.
            f"  ledger:       {self.ledger_before:,} + {self.rows_appended:,} "
            f"appended = {self.ledger_after:,}, against {self.rows_seen:,} rows "
            f"graded ({already_held:,} already held and refused as duplicates).",
            f"  {verdict}.",
        ]
        return lines + [f"  ::error::{failure}" for failure in self.breaks]


# --------------------------------------------------------------------------
# Rendering the report
# --------------------------------------------------------------------------


def family_count(output_dir: Path) -> int | None:
    """The experiment ledger's **cumulative** count, or None when there is none.

    Never this table's row count and never this week's — *"a search that runs
    every week is not twelve tests, it is twelve tests a week, forever."*
    `None` is passed through deliberately: `render_ledger` then says on its own
    front page that no correction was applied, which is louder and more honest
    than quietly correcting for a single look.
    """
    ledger = experiment_ledger.load(
        Path(output_dir) / experiment_ledger.LEDGER_FILENAME
    )
    return ledger.count or None


def render(ledger: pd.DataFrame, *, output_dir: Path, competition: Competition) -> list[str]:
    """Write both renders of the report and describe what was written.

    The second-half markets are passed as **settlement suspects** rather than
    left to the default empty set. Second-half wagers settle including overtime
    at most US books and not at all of them, which is a book's rule rather than
    a fact about basketball; this lab cannot read a rulebook, so those rows
    measure the settlement rule as much as the model and the report says **not
    evidence** against them at any sample size. That is the conservative
    direction, and it is not a pass, an avoid, or a no-value call.
    """
    families = family_count(output_dir)
    markdown, payload = fe.write_report(
        ledger,
        output_dir=output_dir,
        families=families,
        settlement_suspects=fe.SETTLEMENT_AMBIGUOUS_MARKETS,
        competition=competition,
    )
    correction = (
        f"corrected across {families:,} hypotheses from the experiment ledger's "
        "cumulative count"
        if families
        else "UNCORRECTED — the experiment ledger records nothing yet, so every "
        "interval in it is narrower than the truth and the report says so on "
        "its own front page"
    )
    return [
        f"Wrote {markdown}",
        f"Wrote {payload}",
        f"Intervals are {correction}.",
    ]


# --------------------------------------------------------------------------
# Entry point
# --------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--settle",
        action="store_true",
        help=(
            "Settle every snapshot whose games are all final and append them to "
            "the ledger. Without this nothing is settled and nothing is written "
            "to the ledger — the store can only grow and cannot be rebuilt."
        ),
    )
    mode.add_argument(
        "--report-only",
        action="store_true",
        help=(
            "Re-render the report from the ledger already on disk. Settles "
            "nothing, reads no results table, and is the default."
        ),
    )
    parser.add_argument("--archive-dir", default=str(ARCHIVE_DIR))
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument(
        "--ledger",
        default="",
        help="Defaults to <processed-dir>/" + fe.LEDGER_FILENAME + ".",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    competition = competition_for(args.competition)
    archive_dir = Path(args.archive_dir)
    output_dir = Path(args.output_dir)
    ledger_path = (
        Path(args.ledger)
        if args.ledger
        else Path(args.processed_dir) / fe.LEDGER_FILENAME
    )

    print(f"{competition.title} — forward evidence")
    print(f"Archive:    {fe.snapshot_dir(archive_dir)}")
    print(f"Ledger:     {ledger_path}")

    if not args.settle:
        # The default, and the whole of `--report-only`. It reads the ledger and
        # nothing else: no results table, no schedule, no snapshot. Improving a
        # report's wording must never cost anything twice.
        print(
            "Report only. Nothing was settled, no snapshot was read, and no "
            "marker was written."
        )
        ledger = fe.read_ledger(ledger_path)
        print(f"Ledger holds {len(ledger):,} settled opinions.")
        for line in render(ledger, output_dir=output_dir, competition=competition):
            print(line)
        return 0

    # Everything below can write to the append-only ledger, so every
    # precondition is checked before the first marker is written rather than
    # after some of the night is already recorded.
    try:
        inputs = load_inputs(
            processed_dir=Path(args.processed_dir),
            raw_dir=Path(args.raw_dir),
            archive_dir=archive_dir,
            competition=competition,
        )
    except InputError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        print("Nothing was settled and no marker was written.", file=sys.stderr)
        return 2
    for line in inputs.summary_lines():
        print(line)

    # Named before the pass, because afterwards they are indistinguishable from
    # a day on which nothing was frozen.
    unreadable = unreadable_snapshots(archive_dir)
    for path in unreadable:
        print(
            f"::warning::{path.name} could not be parsed. The opinions frozen "
            "in it settle as a day with no rows, and the prices they were "
            "frozen at are gone. The rest of the archive still settles; this "
            "one needs a human."
        )

    ledger_before = len(fe.read_ledger(ledger_path))
    try:
        result = fe.settle_snapshots(
            archive_dir=archive_dir,
            ledger_path=ledger_path,
            team_games=inputs.team_games,
            player_games=inputs.player_games,
            game_segments=inputs.game_segments,
            team_index=inputs.team_index,
            competition=competition,
        )
    except (ValueError, stores.CorruptStoreError) as exc:
        # `append_ledger` refuses a write that would compact the ledger, and
        # `read_store(for_append=True)` refuses to overwrite a damaged file with
        # a short one. Both are guards firing, not crashes, and both need a
        # human rather than a retry — so they are reported in their own words
        # rather than re-worded here.
        print(f"::error::{exc}", file=sys.stderr)
        return 1

    print("")
    print(result.summary_line())
    print("")

    reconciliation = Reconciliation.of(
        result, ledger_before=ledger_before, unreadable=len(unreadable)
    )
    print("Counters:")
    for line in reconciliation.counter_lines():
        print(line)
    print("")
    print("Reconciliation:")
    for line in reconciliation.reconciliation_lines():
        print(line)
    print("")

    if result.settlement_errors:
        # Counted into `rows_unsettleable` above and named here. An exception
        # inside `settle` is a contract mismatch rather than a missing box
        # score, and the two must never look alike.
        print("Exceptions raised inside settle, counted unsettleable:")
        for message, count in sorted(
            result.settlement_errors.items(), key=lambda kv: -kv[1]
        ):
            print(f"  {count:,} x {message}")
        print("")

    # `team_names`' fourth rule: an unresolved name is reported loudly and
    # counted, because a name this lab cannot resolve is a game it silently
    # cannot settle — and the NHL lab proved that a silent loss looks exactly
    # like a quiet market.
    if inputs.team_index.unresolved:
        print(inputs.team_index.unresolved_report())
        print("")

    for line in render(
        fe.read_ledger(ledger_path), output_dir=output_dir, competition=competition
    ):
        print(line)

    print("")
    print(
        "This pass settled frozen opinions against the box score. It priced "
        "nothing, fetched nothing, placed no bet, allowlisted no market and "
        "signed no receipt."
    )
    if not reconciliation.holds:
        print(
            "::error::The settle pass does not reconcile. A row that vanishes "
            "without appearing in a count is a defect, not a decision.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
