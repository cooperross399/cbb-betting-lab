"""The clobber guard, run against a real `card-feed` ref across every case.

Cooper's brief, verbatim: *"Verify this against a real git ref across every
case; string assertions about shell logic in a workflow file are
near-worthless."* So this test builds a scratch repository, writes a real
`latest_status.json` into a real orphan commit on a real `card-feed` branch,
and runs `.github/workflows/lib/clobber_guard.sh` — the same bytes the
workflow runs — against it.

What it is defending. The publish step is `if: always()` and last-write-wins,
because "no commit for today" has to keep meaning "the run did not finish".
That combination is how the EPL lab lost a good card: a late backup trigger
produced a blocked card, published last, and replaced the morning's real one.
Defect 17 in `docs/ported_defects.md`.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
GUARD = REPO / ".github" / "workflows" / "lib" / "clobber_guard.sh"


def git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


@pytest.fixture()
def feed(tmp_path: Path):
    """A scratch repository with a real orphan `card-feed` branch."""
    root = tmp_path / "repo"
    root.mkdir()
    git("init", "-q", "-b", "main", cwd=root)
    git("config", "user.email", "t@example.com", cwd=root)
    git("config", "user.name", "t", cwd=root)
    (root / "seed").write_text("seed\n")
    git("add", "seed", cwd=root)
    git("commit", "-qm", "seed", cwd=root)

    def publish_tip(status: dict | None) -> str:
        """Write a tip commit onto refs/card-feed-tip, as the workflow does
        after fetching. Returns the commit sha, which is what PARENT holds."""
        if status is None:
            return ""
        blob = subprocess.run(
            ["git", "hash-object", "-w", "--stdin"],
            cwd=root, input=json.dumps(status), capture_output=True, text=True,
            check=True,
        ).stdout.strip()
        tree = subprocess.run(
            ["git", "mktree"], cwd=root,
            input=f"100644 blob {blob}\tlatest_status.json\n",
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        commit = git("commit-tree", tree, "-m", "tip", cwd=root)
        git("update-ref", "refs/card-feed-tip", commit, cwd=root)
        return commit

    def run(*, tip: dict | None, day: str, slot: str, degraded: str) -> str:
        parent = publish_tip(tip)
        result = subprocess.run(
            ["bash", str(GUARD)],
            cwd=root,
            capture_output=True,
            text=True,
            env={
                "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
                "PARENT": parent,
                "TIP_REF": "refs/card-feed-tip",
                "DAY": day,
                "CARD_SLOT": slot,
                "DEGRADED": degraded,
            },
        )
        assert result.returncode == 0, (
            f"The guard exited {result.returncode}. Standing down is not a "
            f"failure and must not fail the step.\n{result.stderr}"
        )
        return result.stdout.strip()

    return run


CLEAN = {"date": "2027-01-12", "card_slot": "morning", "degraded": "false"}


def test_the_case_the_guard_exists_for(feed):
    """A clean card is on the feed and this run is degraded. Stand down."""
    assert feed(tip=CLEAN, day="2027-01-12", slot="morning", degraded="true") == "skip"


def test_unknown_health_counts_as_degraded(feed):
    """A run whose health step never executed cannot report 'false'. Treating
    an unreadable health as clean is how a broken run overwrites a good one
    while looking careful."""
    assert feed(tip=CLEAN, day="2027-01-12", slot="morning", degraded="unknown") == "skip"


def test_a_clean_run_may_replace_a_clean_tip(feed):
    assert feed(tip=CLEAN, day="2027-01-12", slot="morning", degraded="false") == "publish"


def test_no_tip_at_all_publishes(feed):
    """The first run of the season, or a deleted branch. A first-of-the-day
    failure must still write a commit, or the reader cannot tell 'the run did
    not finish' from 'the run stood down'."""
    assert feed(tip=None, day="2027-01-12", slot="morning", degraded="true") == "publish"


def test_a_different_day_publishes(feed):
    assert feed(tip=CLEAN, day="2027-01-13", slot="morning", degraded="true") == "publish"


def test_a_different_slot_on_the_same_day_publishes(feed):
    """The college basketball difference, and it is not cosmetic. The slate
    spans twelve hours and there are two card slots a day; a guard comparing
    the date alone would read every evening refresh as a clobber of the
    morning card and stand down for the half of the slate the evening slot
    exists to cover."""
    assert feed(tip=CLEAN, day="2027-01-12", slot="evening", degraded="true") == "publish"


def test_a_degraded_tip_is_replaceable_by_anything(feed):
    """A degraded card is exactly what the backup trigger exists to replace."""
    tip = {**CLEAN, "degraded": "true"}
    assert feed(tip=tip, day="2027-01-12", slot="morning", degraded="true") == "publish"
    assert feed(tip=tip, day="2027-01-12", slot="morning", degraded="false") == "publish"


def test_a_tip_with_no_degraded_field_is_not_a_clean_tip(feed):
    """An older run that did not stamp its health reads as unknown, which
    publishes — the safe direction, because publishing over an unreadable tip
    loses nothing a reader could have used."""
    tip = {"date": "2027-01-12", "card_slot": "morning"}
    assert feed(tip=tip, day="2027-01-12", slot="morning", degraded="true") == "publish"


def test_an_unparseable_tip_publishes(feed, tmp_path):
    """`latest_status.json` absent from the tip tree entirely."""
    root = tmp_path / "empty"
    root.mkdir()
    git("init", "-q", "-b", "main", cwd=root)
    git("config", "user.email", "t@example.com", cwd=root)
    git("config", "user.name", "t", cwd=root)
    (root / "x").write_text("x\n")
    git("add", "x", cwd=root)
    git("commit", "-qm", "x", cwd=root)
    commit = git("rev-parse", "HEAD", cwd=root)
    git("update-ref", "refs/card-feed-tip", commit, cwd=root)
    result = subprocess.run(
        ["bash", str(GUARD)], cwd=root, capture_output=True, text=True,
        env={
            "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
            "PARENT": commit, "TIP_REF": "refs/card-feed-tip",
            "DAY": "2027-01-12", "CARD_SLOT": "morning", "DEGRADED": "true",
        },
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "publish"


def test_slate_date_cannot_be_read_as_date(feed):
    """`"date"` must not match inside `"slate_date"`. The guard's field reader
    requires the name's own opening quote for exactly this reason; a reader
    that matched the substring would take a rehearsal's slate date for the
    tip's day and stand down on the wrong comparison."""
    tip = {
        "slate_date": "2027-01-99",
        "date": "2027-01-12",
        "card_slot": "morning",
        "degraded": "false",
    }
    assert feed(tip=tip, day="2027-01-12", slot="morning", degraded="true") == "skip"


def test_the_guard_the_workflow_calls_is_the_guard_this_test_runs():
    """A copy of the logic inlined into the YAML would drift from this file
    silently, and the test would keep passing against the dead copy."""
    workflow = (REPO / ".github" / "workflows" / "cbb-gameday-refresh.yml").read_text()
    assert "lib/clobber_guard.sh" in workflow, (
        "The gameday workflow no longer calls the guard script. If the logic "
        "was inlined, this test is now measuring nothing."
    )
    assert GUARD.is_file()
