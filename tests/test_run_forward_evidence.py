"""The settle entry point, run the way the gameday workflow runs it.

`tests/test_forward_evidence.py` proves the organ. This file proves the *wiring*
— which is where the sibling labs actually lost nights. The football lab's first
rehearsal died on a zero-byte CSV that its module handled perfectly and its
script never noticed; the EPL lab spent five days green and empty because a
workflow that runs is not a workflow that works.

So every test here runs `scripts/run_forward_evidence.py` as a shell would,
through `runpy`, and asserts on what a reader of the Actions log and a reader of
the ledger would see. Each is named for the specific way a night could be lost:

* a second slot of the same day appending the night a second time — the ledger
  is append-only, so a duplicate is not a tidy-up problem, it is a permanent
  root-two narrowing of every interval that ledger will ever produce;
* the same, when the `.settled` sidecars did **not** survive, which is the
  production case rather than an edge case: the gameday workflow publishes only
  `data/archive/priced_snapshots/*.csv` to `card-feed`, so the markers are gone
  by the next run and the ledger's own set of snapshot dates is the only
  idempotence source left standing;
* a missing processed table settling a whole night as "no game matches", which
  does not fail — it succeeds quietly and wrongly, into a store nothing can
  revise;
* an unreadable snapshot taking the rest of the archive down with it.
"""

from __future__ import annotations

import json
import re
import runpy
import socket
import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

import pandas as pd
import pytest

import cbb_betting_lab.settlement  # noqa: E402,F401  (an ImportError here is a failure, never a skip)

from cbb_betting_lab import forward_evidence as fe  # noqa: E402
from cbb_betting_lab import season  # noqa: E402
from cbb_betting_lab.competitions import CBB  # noqa: E402
from cbb_betting_lab.selection import FULL_GAME, selection_key  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run_forward_evidence.py"

#: A slate day comfortably outside the 14-day patience window, so a fixture the
#: results tables do not carry is UNSETTLEABLE rather than waiting. Tests that
#: need the waiting branch ask for a recent day explicitly.
DAY = "2026-01-13"
TIP = "2026-01-14T00:00:00Z"  # 19:00 Eastern on the 13th.


# --------------------------------------------------------------------------
# One January night, built the way the real tables are shaped
# --------------------------------------------------------------------------


def key_for(row):
    """The injected key, identical to the card's. One callable, no drift."""
    return selection_key(
        row,
        market=row.market,
        selection=row.selection,
        line=row.line,
        competition=CBB,
        segment=row.segment,
    )


def price(
    *,
    event_id="e1",
    home="Purdue",
    away="Butler",
    market="moneyline",
    selection="home",
    line=None,
    odds=-110,
    book="dk",
    player="",
    commence_time=TIP,
    segment=FULL_GAME,
) -> dict:
    return {
        "event_id": event_id,
        "commence_time": commence_time,
        "home_team": home,
        "away_team": away,
        "market": market,
        "segment": segment,
        "player": player,
        "selection": selection,
        "line": line,
        "american_odds": odds,
        "book": book,
    }


def team_games(day: str = DAY) -> pd.DataFrame:
    """Purdue beat Butler 80-70; Duke beat North Carolina 61-60."""
    rows = []
    for game_id, home, away, home_score, away_score in ((1, 10, 20, 80, 70), (2, 30, 40, 61, 60)):
        for team, opponent, score, against, side in (
            (home, away, home_score, away_score, "home"),
            (away, home, away_score, home_score, "away"),
        ):
            rows.append(
                {
                    "game_id": game_id,
                    "season": season.season_for_slate_date(day),
                    "slate_date": day,
                    "team_id": team,
                    "opponent_id": opponent,
                    "home_away": side,
                    "team_score": score,
                    "opponent_score": against,
                    "margin": score - against,
                    "total": home_score + away_score,
                    "team_score_h1": score // 2,
                    "opponent_score_h1": against // 2,
                    # The second half is the final score minus the halftime
                    # score, so it CONTAINS overtime — a fact about the table
                    # rather than about basketball, and the reason the h2
                    # markets are settlement suspects.
                    "team_score_h2": score - score // 2,
                    "opponent_score_h2": against - against // 2,
                    "periods": 2,
                    "overtime": False,
                }
            )
    return pd.DataFrame(rows)


def player_games() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": 1,
                "athlete_id": 111,
                "athlete_display_name": "Zach Edey",
                "team_id": 10,
                "opponent_id": 20,
                "did_not_play": False,
                "points": 24.0,
                "rebounds": 12.0,
                "assists": 2.0,
            }
        ]
    )


def game_segments() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "game_id": game_id,
                "periods": 2,
                "overtime": False,
                "home_score_h1": 40,
                "away_score_h1": 35,
                "first_basket_athlete_id": None,
                "first_basket_team_id": None,
            }
            for game_id in (1, 2)
        ]
    )


def schedule() -> pd.DataFrame:
    """A schedule shaped like hoopR's, which is where the name index comes from.

    `home_conference_id` is the Division-I membership marker `population` uses,
    so it is present on every row: a team the feed gives no conference to is
    excluded from the index, and an excluded team resolves to nothing.
    """
    rows = []
    for home_id, home, away_id, away in ((10, "Purdue", 20, "Butler"), (30, "Duke", 40, "North Carolina")):
        rows.append(
            {
                "home_id": home_id,
                "home_location": home,
                "home_name": "Boilermakers",
                "home_display_name": home,
                "home_short_display_name": home,
                "home_abbreviation": home[:4].upper(),
                "home_conference_id": 1,
                "away_id": away_id,
                "away_location": away,
                "away_name": "Bulldogs",
                "away_display_name": away,
                "away_short_display_name": away,
                "away_abbreviation": away[:4].upper(),
                "away_conference_id": 2,
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# A lab on disk, and the script run against it
# --------------------------------------------------------------------------


class Lab:
    """The directory layout the workflow hands the script, built in tmp_path."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.archive = root / "archive"
        self.processed = root / "processed"
        self.raw = root / "raw"
        self.outputs = root / "outputs"
        for directory in (self.archive, self.processed, self.raw, self.outputs):
            directory.mkdir(parents=True, exist_ok=True)
        self.ledger = self.processed / fe.LEDGER_FILENAME

    def with_tables(self, *, day: str = DAY, games: pd.DataFrame | None = None) -> Lab:
        (games if games is not None else team_games(day)).to_csv(
            self.processed / "cbb_team_games.csv", index=False
        )
        player_games().to_csv(self.processed / "cbb_player_games.csv", index=False)
        game_segments().to_csv(self.processed / "cbb_game_segments.csv", index=False)
        return self

    def with_schedule(self, *days: str) -> Lab:
        directory = self.raw / CBB.data_dir_segment / "schedules"
        directory.mkdir(parents=True, exist_ok=True)
        for day in days or (DAY,):
            year = season.season_for_slate_date(day)
            schedule().to_parquet(directory / f"mbb_schedule_{year}.parquet")
        return self

    def freeze(self, rows: list[dict], *, day: str = DAY) -> Path | None:
        """Freeze a night, keyed by the same callable the card would inject.

        The probability map is keyed through `key_for` rather than by hand,
        which is the module's whole point: one callable builds the key on both
        sides, so a fixture cannot drift from the thing it is testing.
        """
        return fe.write_snapshot(
            pd.DataFrame(rows),
            {key_for(SimpleNamespace(**row)): 0.6 for row in rows},
            key_for=key_for,
            verdicts_in_force=["calibration_correction"],
            snapshot_date=day,
            archive_dir=self.archive,
        )

    def run(self, *argv: str) -> int:
        """Run the script the way a shell would, and return its exit status."""
        saved = sys.argv[:]
        sys.argv = [
            str(SCRIPT),
            "--archive-dir",
            str(self.archive),
            "--processed-dir",
            str(self.processed),
            "--raw-dir",
            str(self.raw),
            "--output-dir",
            str(self.outputs),
            *argv,
        ]
        try:
            runpy.run_path(str(SCRIPT), run_name="__main__")
            return 0
        except SystemExit as exit_code:
            return int(exit_code.code or 0)
        finally:
            sys.argv = saved

    def ledger_rows(self) -> int:
        return len(fe.read_ledger(self.ledger))

    def markers(self) -> list[Path]:
        return sorted(self.archive.glob(f"**/*{fe.SETTLED_MARKER_SUFFIX}"))


@pytest.fixture()
def lab(tmp_path) -> Lab:
    return Lab(tmp_path).with_tables().with_schedule()


def a_night() -> list[dict]:
    """Four opinions over two games: two team markets, a prop, a future."""
    return [
        price(),
        price(event_id="e1", market="spread", selection="away", line=6.5, odds=-105),
        price(
            event_id="e1",
            market="player_points",
            selection="over",
            line=19.5,
            player="Zach Edey",
            odds=-115,
        ),
        price(
            event_id="f1",
            home="Purdue",
            away="Butler",
            market="championship_winner",
            selection="home",
            odds=1400,
            book="fd",
        ),
    ]


# --------------------------------------------------------------------------
# Idempotence — the one the workflow's comment promises
# --------------------------------------------------------------------------


def test_settling_the_same_night_twice_appends_it_once(lab, capsys):
    """The evening slot re-settles what the morning slot settled. It must not.

    The gameday workflow runs this script in **both** slots and says so in its
    own comment: *"Idempotent and keyed by snapshot date, so the evening run
    re-settling what the morning run settled is a no-op rather than a
    duplicate."* A duplicated ledger does not look wrong — it looks
    significant, because ROI is unchanged and every interval comes out root-two
    too narrow. That is the NHL lab's price-store defect in the one store here
    that can never be rebuilt.
    """
    lab.freeze(a_night())

    assert lab.run("--settle") == 0
    first = lab.ledger_rows()
    assert first == 4, "the night should have settled all four frozen opinions"

    assert lab.run("--settle") == 0

    assert lab.ledger_rows() == first
    second = capsys.readouterr().out
    assert "0 settled" in second, "the second pass settled a snapshot again"


def test_the_night_is_settled_once_even_when_the_markers_did_not_survive(lab):
    """Production loses the sidecars every run, and the ledger has to hold alone.

    The gameday workflow publishes `data/archive/priced_snapshots/*.csv` to
    `card-feed` and restores from there. A `.settled` sidecar is not a `.csv`,
    so it never reaches the branch and never comes back — meaning the marker is
    *always* missing on the next real run and the ledger's own set of snapshot
    dates is the only idempotence source that actually runs in anger.

    Deleting the markers here reproduces that exactly. A regression on this
    would not be visible in a test that keeps them.
    """
    lab.freeze(a_night())
    assert lab.run("--settle") == 0
    before = lab.ledger_rows()

    for marker in lab.markers():
        marker.unlink()
    assert lab.run("--settle") == 0

    assert lab.ledger_rows() == before
    assert lab.markers(), "the pass should have rewritten the marker it found missing"


def test_a_zero_row_night_does_not_grow_the_ledger_on_a_second_pass(lab, capsys):
    """A night that froze nothing leaves no ledger trace, and must still settle once.

    This is the case the module's two idempotence sources exist for: with only
    the ledger, a zero-row day re-settles forever; with only the marker, a day
    the ledger already holds re-appends when the marker is lost. Neither alone
    is enough, and the script must not paper over either.

    A header-only snapshot is also **not** an unreadable one. "The pipeline had
    no opinion tonight" and "the file is broken" are different statements, and
    reporting the first as the second is how an operator learns to ignore the
    warning that matters.
    """
    fe.write_snapshot(
        [], {}, key_for=key_for, verdicts_in_force=[], snapshot_date=DAY,
        archive_dir=lab.archive,
    )

    assert lab.run("--settle") == 0
    assert lab.ledger_rows() == 0
    assert "could not be parsed" not in capsys.readouterr().out
    assert lab.run("--settle") == 0
    assert lab.ledger_rows() == 0


# --------------------------------------------------------------------------
# What is an error, and what deliberately is not
# --------------------------------------------------------------------------


def test_a_day_with_no_snapshot_is_not_an_error(lab, capsys):
    """There are real days with no basketball, and a red run on one trains an
    operator to ignore red."""
    assert lab.run("--settle") == 0

    out = capsys.readouterr().out
    assert "0 snapshots found" in out
    assert (lab.outputs / fe.REPORT_MARKDOWN_FILENAME).is_file(), (
        "an empty night still re-renders the report; the workflow publishes it"
    )


@pytest.mark.parametrize(
    "table",
    ["cbb_team_games.csv", "cbb_player_games.csv", "cbb_game_segments.csv"],
)
def test_a_missing_processed_table_is_an_error_and_settles_nothing(lab, table, capsys):
    """A missing table does not fail the pass — it succeeds quietly and wrongly.

    Every fixture would miss, every frozen opinion would be recorded
    UNSETTLEABLE, and once the patience window closed that verdict would be in
    an append-only ledger with nothing able to revise it. So the check is a
    precondition, and it runs before the first marker is written.
    """
    lab.freeze(a_night())
    (lab.processed / table).unlink()

    assert lab.run("--settle") == 2

    assert lab.ledger_rows() == 0
    assert not lab.markers(), "a refused pass must not mark a snapshot settled"
    assert table in capsys.readouterr().err


def test_a_missing_schedule_is_an_error_rather_than_a_night_of_missing_fixtures(
    tmp_path, capsys
):
    """An empty name index resolves nothing, and that looks exactly like a night
    that was never played — except it is permanent."""
    lab = Lab(tmp_path).with_tables()  # deliberately no schedule
    lab.freeze(a_night())

    assert lab.run("--settle") == 2

    assert lab.ledger_rows() == 0
    assert not lab.markers()
    err = capsys.readouterr().err
    assert str(season.season_for_slate_date(DAY)) in err
    assert "resolves no fixture" in err


def test_an_unreadable_snapshot_is_named_and_the_rest_of_the_night_settles(lab, capsys):
    """One bad file must not take the archive with it.

    A zero-byte CSV is not hypothetical: `git show X > file` creates the file
    even when the show fails, which is precisely how the football lab's first
    rehearsal died, and the gameday workflow's restore step carries a
    temp-then-move guard because of it. The pass degrades rather than empties —
    the good day settles, the bad one is named in a warning and counted, and the
    run does not go red for a fault no rerun can repair.
    """
    lab.freeze(a_night())
    other = fe.snapshot_dir(lab.archive) / "2026-01-14.csv"
    other.write_bytes(b"")

    assert lab.run("--settle") == 0

    out = capsys.readouterr().out
    assert "::warning::2026-01-14.csv could not be parsed" in out
    numbers = counters(out)
    # A fourth category and a peer of the other three, because a day nobody
    # could read is not a day that settled, waited, or was done earlier.
    assert numbers["could not be parsed, left OPEN"] == 1
    assert numbers["snapshots seen"] == 2
    assert numbers["settled this pass"] == 1, "the broken day must not count as settled"
    assert "2026-01-14" in out
    assert lab.ledger_rows() == 4, "the readable night settled around the broken one"
    assert "HOLDS." in out and "DOES NOT HOLD" not in out


def test_an_unreadable_snapshot_is_not_marked_settled_and_still_grades_once_repaired(
    lab, capsys
):
    """Defect H, found by adversarial review of the settle wiring.

    `read_snapshot` reads leniently, so a file pandas cannot parse came back as
    an EMPTY FRAME. `settle_snapshots` then graded zero rows, wrote the
    `.settled` sidecar and moved on: a night of frozen opinions permanently
    recorded as a night with nothing in it, on the one store in this lab that
    cannot be rebuilt, with nothing in the log looking wrong.

    The marker is the damage. A day left unmarked can still be graded when the
    file is restored from `card-feed` or repaired by hand; a day marked done
    never will be, and the prices it was frozen at are gone.

    So this asserts both halves: no sidecar for the broken day, and the night
    settling in full on the pass after the file is put back.
    """
    broken = fe.snapshot_dir(lab.archive) / f"{DAY}.csv"
    good = lab.freeze(a_night())
    assert good == broken
    intact = broken.read_bytes()
    broken.write_bytes(b"")

    assert lab.run("--settle") == 0
    capsys.readouterr()

    assert lab.ledger_rows() == 0
    assert not lab.markers(), (
        "a snapshot nobody could read must not be marked settled: the marker "
        "closes the night, and the prices it was frozen at are gone"
    )

    # The file comes back — a re-restore from card-feed, or a human repair.
    broken.write_bytes(intact)
    assert lab.run("--settle") == 0

    assert lab.ledger_rows() == 4, "the repaired night must still be gradeable"
    assert lab.markers(), "and settling it must mark it, once"


# --------------------------------------------------------------------------
# The accounting identity
# --------------------------------------------------------------------------


def counters(out: str) -> dict[str, int]:
    """The printed counter block, read back as numbers.

    Parsed from stdout rather than from the `SettlementResult` on purpose: what
    is asserted is what a reader of the Actions log actually sees. A counter
    computed correctly and printed wrongly is a counter nobody can use.
    """
    found: dict[str, int] = {}
    for line in out.splitlines():
        # A trailing parenthetical is allowed: one counter overlaps the totals
        # above it and says so on its own line rather than being read as a peer.
        match = re.match(
            r"^\s{2,}(?P<label>\S.*?)\s{2,}(?P<value>[\d,]+)(\s.*)?$", line
        )
        if match:
            found[match.group("label")] = int(match.group("value").replace(",", ""))
    return found


def test_every_counter_is_printed_and_the_identity_reconciles(lab, capsys):
    """Cooper's rule: the accounting identity is reconciled and printed every run.

    A row that vanishes without appearing in a count is a defect, not a
    decision — so the arithmetic is checked here rather than trusted, over a
    night that deliberately contains one of everything: a settled team market,
    an unsettleable one, a player prop and a future.
    """
    lab.freeze(
        a_night()
        + [
            # A fixture the results tables do not carry, past the patience
            # window: unsettleable, and counted under its own reason.
            price(event_id="e9", home="Gonzaga", away="Saint Mary's", market="moneyline")
        ]
    )

    assert lab.run("--settle") == 0

    out = capsys.readouterr().out
    numbers = counters(out)
    assert numbers["snapshots seen"] == 1
    assert numbers["settled this pass"] == 1
    assert numbers["waiting on a result"] == 0
    assert numbers["settled in an earlier pass"] == 0
    assert (
        numbers["settled (won, lost or pushed)"]
        + numbers["void"]
        + numbers["unsettleable"]
        == numbers["rows seen"]
    )
    assert (
        numbers["no fixture in the results tables"]
        + numbers["more than one athlete named"]
        + numbers["futures, deferred not graded"]
        + numbers["raised inside settle"]
        + numbers["everything else"]
        == numbers["unsettleable"]
    )
    assert numbers["futures, deferred not graded"] == 1
    assert numbers["no fixture in the results tables"] == 1
    assert "HOLDS." in out
    assert "DOES NOT HOLD" not in out


def test_the_ledger_line_compares_the_pass_against_the_file_on_disk(lab, capsys):
    """The one identity that is not arithmetic on the counters themselves.

    Every other line here can only catch a counter that was never incremented.
    This one compares what the pass says it graded against what the ledger
    actually grew by, which is the only way to catch a pass that graded a whole
    night and wrote none of it — the failure that looks exactly like a quiet
    night.
    """
    lab.freeze(a_night())
    assert lab.run("--settle") == 0
    out = capsys.readouterr().out

    assert f"0 + {lab.ledger_rows():,} appended = {lab.ledger_rows():,}" in out
    assert f"against {lab.ledger_rows():,} rows graded" in out
    # Nothing was discarded on a clean pass, so the explanatory line stays off.
    assert "did not reach the ledger" not in out


def test_a_graded_row_that_reaches_no_counter_fails_the_rows_identity(lab, capsys):
    """The rows identity has to be checked against the files, not against itself.

    Found by adversarial review. `SettlementResult.rows_seen` is a **property**
    returning `rows_settled + rows_void + rows_unsettleable`, so the line that
    once read `settled + void + unsettleable = rows seen` was a tautology: it
    held for every pass that could ever run, including one that graded a whole
    night and counted none of it — which is the exact failure it was printed to
    catch. A guard that cannot fail is decoration, and decoration in an
    accounting block is worse than nothing, because a reader trusts it.

    So the check is made against `rows_read`, counted off the snapshot files in
    `settle_snapshots` before anything is graded. This reproduces the failure
    directly: `_record_outcome` is replaced with one that grades the row and
    increments nothing, which is what a new branch added without its counter
    would do. The old line said HOLDS. This one must not.
    """
    lab.freeze(a_night())
    uncounted = lambda record, decided, result, settled_at: fe._ledger_row(  # noqa: E731
        record, decided, settled_at
    )
    original = fe._record_outcome
    fe._record_outcome = uncounted
    try:
        assert lab.run("--settle") == 1
    finally:
        fe._record_outcome = original

    captured = capsys.readouterr()
    assert "DOES NOT HOLD" in captured.out
    assert "reached an outcome" in captured.out
    assert "counted nowhere" in captured.out
    assert "::error::The settle pass does not reconcile." in captured.err


def test_a_waiting_day_counts_nothing_it_threw_away(tmp_path, capsys):
    """A waiting day grades rows speculatively and must un-count them.

    **This test previously pinned the miscount and its explanation; it now pins
    the fix.** `settle_snapshots` walks a snapshot's rows in order and breaks at
    the first whose result is not published, then discards the whole day — and
    every row graded before that break had already incremented `rows_settled`.
    The ledger was always correct and the day always waited atomically, so
    nothing was lost; what was wrong was the accounting identity the workflow
    prints, and the same rows were counted a second time on the pass that
    finally settled the day.

    Explaining a wrong number on its own line is worse than not producing it.
    The identity is the thing that is supposed to catch rows going missing, and
    an identity with a standing exemption written into it cannot.

    The counters are snapshotted before the day is graded and restored when it
    turns out to be waiting, so `rows seen` is what the pass actually kept.
    """
    day = (date.today() - timedelta(days=1)).isoformat()
    # The tables carry the first game of the night and not the second.
    played = team_games(day)
    lab = (
        Lab(tmp_path)
        .with_tables(games=played[played["game_id"] == 1])
        .with_schedule(day)
    )
    lab.freeze(
        [
            price(event_id="e1", commence_time=f"{day}T23:00:00Z"),
            price(
                event_id="e2",
                home="Duke",
                away="North Carolina",
                commence_time=f"{day}T23:00:00Z",
            ),
        ],
        day=day,
    )

    assert lab.run("--settle") == 0

    out = capsys.readouterr().out
    numbers = counters(out)
    assert numbers["waiting on a result"] == 1
    assert numbers["rows seen"] == 0, (
        "A waiting day kept nothing, so it must have counted nothing. Rows "
        "graded before the break are speculative and are rolled back."
    )
    assert lab.ledger_rows() == 0, "a waiting day puts nothing in the ledger"
    assert "HOLDS." in out and "DOES NOT HOLD" not in out


def test_the_day_settles_in_full_once_the_result_arrives(tmp_path, capsys):
    """The other half of the rollback: nothing was lost by un-counting.

    A day that waited must settle completely on the next pass, counting each
    row exactly once — not zero times because it was rolled back, and not twice
    because it was graded before.
    """
    day = (date.today() - timedelta(days=1)).isoformat()
    lab = Lab(tmp_path).with_tables(games=team_games(day)).with_schedule(day)
    lab.freeze(
        [
            price(event_id="e1", commence_time=f"{day}T23:00:00Z"),
            price(
                event_id="e2",
                home="Duke",
                away="North Carolina",
                commence_time=f"{day}T23:00:00Z",
            ),
        ],
        day=day,
    )

    assert lab.run("--settle") == 0
    out = capsys.readouterr().out
    assert counters(out)["waiting on a result"] == 0
    assert lab.ledger_rows() == 2
    assert "HOLDS." in out

def test_a_night_still_waiting_on_its_box_score_is_named_and_not_settled(tmp_path, capsys):
    """Waiting is not a verdict, and a guess would be one.

    A snapshot inside the patience window whose result has not been published
    settles nothing at all — the whole day waits, atomically, because half a day
    in the ledger makes `snapshot_date in ledger` mean either "done" or "partly
    done" and destroys the second idempotence source.
    """
    # The tables exist and are populated; they simply do not carry last night
    # yet, which is what a hoopR asset published a few hours late looks like.
    day = (date.today() - timedelta(days=1)).isoformat()
    lab = Lab(tmp_path).with_tables(games=team_games(DAY)).with_schedule(DAY, day)
    lab.freeze([price(commence_time=f"{day}T23:00:00Z")], day=day)

    assert lab.run("--settle") == 0

    out = capsys.readouterr().out
    numbers = counters(out)
    assert numbers["waiting on a result"] == 1
    assert numbers["settled this pass"] == 0
    assert day in out
    assert lab.ledger_rows() == 0, "a waiting day never puts half a night in the ledger"


def test_a_future_is_deferred_and_never_described_as_a_pass_or_an_avoid(lab, capsys):
    """It settles on the tournament months later; it is not a no-value call."""
    lab.freeze([price(event_id="f1", market="championship_winner", selection="home", odds=1400)])

    assert lab.run("--settle") == 0

    out = capsys.readouterr().out
    assert counters(out)["futures, deferred not graded"] == 1
    assert "not a pass, an avoid or a no-value call" in out


# --------------------------------------------------------------------------
# Reporting, and the mode that costs nothing
# --------------------------------------------------------------------------


def test_report_only_settles_nothing_and_still_rewrites_the_report(lab, capsys):
    """Improving a report's wording must never cost anything twice.

    In the sibling labs the currency was credits. Here it is worse: a settle
    pass run for no reason against a half-published box score writes verdicts
    into a store that cannot be revised. So the re-render reads the ledger and
    nothing else — no snapshot, no results table, no marker.
    """
    lab.freeze(a_night())

    assert lab.run("--report-only") == 0

    assert lab.ledger_rows() == 0
    assert not lab.markers()
    out = capsys.readouterr().out
    assert "Nothing was settled, no snapshot was read, and no marker was written." in out
    assert (lab.outputs / fe.REPORT_MARKDOWN_FILENAME).is_file()
    assert (lab.outputs / fe.REPORT_JSON_FILENAME).is_file()


def test_report_only_needs_no_results_table_at_all(tmp_path):
    """The report is a pure function of the ledger, so it must not demand the
    tables a settle pass needs. A re-render that required a 208MB player table
    would be the cost this flag exists to avoid."""
    lab = Lab(tmp_path)  # no tables, no schedule, no snapshots

    assert lab.run("--report-only") == 0
    assert (lab.outputs / fe.REPORT_MARKDOWN_FILENAME).is_file()


def test_the_default_mode_settles_nothing(lab):
    """This store can only grow and cannot be rebuilt, so growing it is an
    explicit act — the same shape as `run_retention_probe.py` being dry until
    `--live`."""
    lab.freeze(a_night())

    assert lab.run() == 0

    assert lab.ledger_rows() == 0
    assert not lab.markers()


def test_the_report_lands_on_the_paths_claude_md_pins(lab):
    """`data/outputs/cbb_forward_evidence.md` is a contract string. Cooper's
    routines and the card-feed publish step both read it by name."""
    lab.freeze(a_night())
    assert lab.run("--settle") == 0

    markdown = lab.outputs / "cbb_forward_evidence.md"
    payload = lab.outputs / "cbb_forward_evidence.json"

    assert markdown.is_file() and payload.is_file()
    assert lab.ledger.name == "cbb_forward_evidence.csv"
    assert json.loads(payload.read_text())["no_pooled_division_one_headline"] is True


def test_the_report_says_it_is_uncorrected_when_nothing_has_been_hypothesised(lab, capsys):
    """An uncorrected interval that looks corrected is worse than no correction.

    The family factor comes from the experiment ledger's **cumulative** count.
    With no experiment ledger on disk there is no count, and the run says so
    rather than quietly correcting for a single look.
    """
    lab.freeze(a_night())
    assert lab.run("--settle") == 0

    out = capsys.readouterr().out
    assert "UNCORRECTED" in out
    report = (lab.outputs / fe.REPORT_MARKDOWN_FILENAME).read_text()
    assert "no family correction is applied" in report


def test_second_half_markets_are_reported_as_not_evidence(lab):
    """This lab cannot read a book's rulebook, and second-half wagers settle
    including overtime at most US books and not all of them. Those rows measure
    the settlement rule as much as the model, so the script passes them as
    suspects rather than accepting the module's empty default."""
    lab.freeze(
        [price(market="moneyline_h2", segment="h2", selection="home", odds=-120)]
    )
    assert lab.run("--settle") == 0

    report = (lab.outputs / fe.REPORT_MARKDOWN_FILENAME).read_text()
    assert "not evidence" in report


def test_a_ledger_that_cannot_be_parsed_stops_the_pass(lab, capsys):
    """A damaged ledger read as empty is worse than a damaged ledger read at all.

    A zero-byte CSV is the exact shape of the football lab's defect 16:
    `git show X > file` creates the file even when the show fails, and pandas
    refuses to parse the result. Read leniently that is "0 frozen opinions" —
    over a season of them, on a store where the prices are gone. So the run
    stops, before a marker is written and before a report is published.
    """
    lab.freeze(a_night())
    lab.ledger.write_bytes(b"")

    assert lab.run("--settle") == 1

    assert not lab.markers(), "nothing may be marked settled against a broken ledger"
    assert "could not be read" in capsys.readouterr().err


def test_report_only_publishes_nothing_over_a_damaged_ledger(lab, capsys):
    """The report goes to `card-feed`, where it is the only copy anybody reads.

    Publishing "0 frozen opinions" over a season of them would be the most
    misleading output this lab could produce, and it would look completely
    healthy.
    """
    lab.ledger.write_bytes(b"")

    assert lab.run("--report-only") == 1

    assert not (lab.outputs / fe.REPORT_MARKDOWN_FILENAME).exists()
    assert "could not be read" in capsys.readouterr().err


def test_a_team_name_that_never_resolves_is_reported_loudly(lab, capsys):
    """`team_names`' fourth rule, on the settle side.

    A name this lab cannot resolve is a game it silently cannot settle, and the
    NHL lab proved that a silent loss looks exactly like a quiet market. The
    count is worthless if nobody is told which spelling to add to the map.
    """
    lab.freeze([price(event_id="e9", home="Gonzaga", away="Saint Peter's")])

    assert lab.run("--settle") == 0

    out = capsys.readouterr().out
    assert "did not resolve" in out
    assert "Gonzaga" in out and "Saint Peter's" in out


def test_the_settle_pass_opens_no_socket_and_reads_no_credential(lab, monkeypatch):
    """Settlement runs off the disk, and it has to keep doing so.

    A pass that reached out for a box score it could not find would turn a
    publisher's outage into permanently mis-settled evidence: the patience
    window exists precisely so a late result is *waited for* rather than
    fetched under pressure. And a settle pass has no business holding a
    credential at all — it grades opinions that were already priced.

    Blocked at the socket layer rather than asserted in prose, which is the
    stronger claim `tests/test_the_dry_run_is_dry.py` makes about the spending
    scripts.
    """

    def refuse(*args, **kwargs):
        raise AssertionError(
            "The settle pass tried to open a network connection. It settles "
            "against the tables on disk, and a result that is not there yet is "
            "waited for."
        )

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    for name in ("CBB_ODDS_API_KEY", "CBBD_API_KEY", "ODDS_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    lab.freeze(a_night())

    assert lab.run("--settle") == 0
    assert lab.ledger_rows() == 4


def test_the_run_states_what_it_did_not_do(lab, capsys):
    """Silence about a gate is how a gate stops being one."""
    lab.freeze(a_night())
    assert lab.run("--settle") == 0

    out = capsys.readouterr().out
    assert "placed no bet, allowlisted no market and signed no receipt" in out
