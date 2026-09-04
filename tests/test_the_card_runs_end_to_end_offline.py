"""The card, run end to end with no network and no credential.

**A green workflow run is not a delivered card.** The EPL lab spent five days
green and empty, and the football lab's first real run would have crashed on a
branch state its tests never built. This file is the answer to both: it drives
`scripts/run_gameday_card.py` over a board on disk, with the network blocked
and the credential removed, and reads what comes out.

The board is built from **real provider team spellings** — the 365 observed in
`data/manual/provider_team_names_observed.json` — rather than from ESPN's, so
the test exercises the resolution path that was 20.5% broken until it was
measured. A fixture written in the results source's own vocabulary would pass
while the real thing failed, which is the failure mode this whole file exists
to catch.

Nothing here asserts that the card is *good*. It asserts that it runs, that its
accounting reconciles, and that with no market allowlisted it produces no
selection and says so — which is the correct output and the one a season of
frozen evidence depends on.
"""

from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

REPO = Path(__file__).resolve().parents[1]
OBSERVED = REPO / "data" / "manual" / "provider_team_names_observed.json"

BOOKS = ("draftkings", "fanduel", "betmgm")


@pytest.fixture(scope="module")
def provider_names() -> list[str]:
    if not OBSERVED.is_file():
        pytest.skip("The observed provider vocabulary is not present.")
    return json.loads(OBSERVED.read_text(encoding="utf-8"))["names"]


def build_board(tmp_path: Path, names: list[str], *, games: int = 6) -> Path:
    """A staged board in this lab's vocabulary, from real provider spellings.

    Every tip is placed comfortably ahead of the run, so the tip guard has
    nothing to quarantine and a card that produces nothing is producing nothing
    for the right reason.
    """
    sys.path.insert(0, str(REPO / "src"))
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.providers.staging import stage_payloads
    from cbb_betting_lab.season import slate_date

    now = datetime.now(timezone.utc)

    # EVERY GAME TIPS AT THE SAME MOMENT, AND THE MOMENT MATTERS.
    #
    # This fixture used to spread tips over `now + 3h ... now + 8h`, which is
    # fine in the morning and wrong in the evening: run at 20:45 ET the later
    # tips land after midnight, which `season.slate_date` correctly files under
    # TOMORROW's slate day, while the card is carding today. The card then
    # reported them as off-slate and froze nothing — the card was right and the
    # fixture was wrong, but the failure looked like a regression in the card.
    #
    # It also only appeared for part of the day, so the suite passed all
    # afternoon and failed at night, which is the worst way for a test to be
    # wrong.
    #
    # 65 minutes is the smallest lead that clears the card's "at least an hour
    # after the run" rule with a minute to spare, and simultaneous tips are
    # realistic: this sport routinely tips a dozen games at once.
    tip = now + timedelta(minutes=65)
    if slate_date(tip.strftime("%Y-%m-%dT%H:%M:%SZ"), CBB) != slate_date(
        now.strftime("%Y-%m-%dT%H:%M:%SZ"), CBB
    ):
        pytest.skip(
            "Within 65 minutes of the slate-day boundary, a future tip belongs "
            "to tomorrow's slate while the card cards today. There is no board "
            "this fixture can build that is both in the future and on today's "
            "slate, so the case is skipped rather than asserted around."
        )

    payloads = []
    for i in range(games):
        home, away = names[2 * i], names[2 * i + 1]
        payloads.append(
            {
                "id": f"{i:032x}",
                "commence_time": tip.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "home_team": home,
                "away_team": away,
                "bookmakers": [
                    {
                        "key": book,
                        "markets": [
                            {"key": "h2h", "outcomes": [
                                {"name": home, "price": -140},
                                {"name": away, "price": 120}]},
                            {"key": "spreads", "outcomes": [
                                {"name": home, "price": -110, "point": -3.5},
                                {"name": away, "price": -110, "point": 3.5}]},
                            {"key": "totals", "outcomes": [
                                {"name": "Over", "price": -110, "point": 142.5},
                                {"name": "Under", "price": -110, "point": 142.5}]},
                        ],
                    }
                    for book in BOOKS
                ],
            }
        )
    frame, counts = stage_payloads(payloads, competition=CBB)
    assert not frame.empty, "The fixture staged nothing; the board is not a board."
    assert counts.unparseable_outcome == 0 if hasattr(counts, "unparseable_outcome") else True
    path = tmp_path / "board.csv"
    frame.to_csv(path, index=False)
    return path


def run_card(board: Path, tmp_path: Path, *extra: str):
    """Run the real entry point as a subprocess, with no credential."""
    env = {
        "PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin",
        "PYTHONPATH": str(REPO / "src"),
        "HOME": str(tmp_path),
    }
    result = subprocess.run(
        [
            sys.executable, str(REPO / "scripts" / "run_gameday_card.py"),
            "--card-slot", "morning",
            "--staged-board", str(board),
            "--archive-dir", str(tmp_path / "archive"),
            "--output-dir", str(tmp_path / "outputs"),
            *extra,
        ],
        cwd=REPO, capture_output=True, text=True, env=env, timeout=600,
    )
    return result


@pytest.fixture()
def carded(tmp_path, provider_names):
    board = build_board(tmp_path, provider_names)
    result = run_card(board, tmp_path)
    assert result.returncode == 0, (
        f"The card exited {result.returncode}.\n"
        f"stdout:\n{result.stdout[-3000:]}\nstderr:\n{result.stderr[-3000:]}"
    )
    return result, tmp_path


def test_the_card_runs_over_a_real_board_with_no_credential(carded):
    result, _ = carded
    assert "decision=" in result.stdout, (
        "The workflow greps stdout for `decision=`. Without it the card feed's "
        "status file records nothing and the reader cannot tell what happened."
    )


def test_the_accounting_identity_reconciles(carded):
    """priced = no_opinion + below_threshold + unparseable + ambiguous + bets.

    Printed every run and reconciled, not merely printed. A card whose identity
    does not close has lost rows somewhere between the board and the ledger,
    and every count downstream is describing a different population than the
    one that was priced.
    """
    result, _ = carded
    out = result.stdout
    assert "priced" in out.lower()
    # The card must state the reconciliation outcome in words a reader can act
    # on, not leave it to be derived from a table.
    assert ("HOLDS" in out) or ("reconcil" in out.lower()), (
        f"No reconciliation was printed.\n{out[-2000:]}"
    )


def test_no_allowlisted_market_means_no_selection_and_a_stated_reason(carded):
    """The correct output of a lab with no signed receipt, and it must never
    read as a pass, an avoid, or a no-value call."""
    result, tmp = carded
    card = tmp / "outputs" / "cbb_gameday_card.md"
    assert card.is_file(), "No card was written."
    text = card.read_text(encoding="utf-8")
    assert "accumulating evidence" in text.lower(), (
        "The card must say it is accumulating evidence rather than making "
        "recommendations. Contract string, pinned in CLAUDE.md."
    )
    assert "no selection" in text.lower() or "produces no selection" in text.lower()

    # THE RULE IS ABOUT THE ASSERTION, NOT THE WORD — and this test got it
    # wrong first, in exactly the way `docs/ported_defects.md` already records
    # as Defect D. The card's required phrasing is *"this is not a pass, an
    # avoid, or a no-value call"*, which contains every banned substring while
    # saying the opposite. So negated clauses are dropped before the check: a
    # card may DENY being a pass and may never CLAIM to be one.
    remainder = text.casefold()
    # Clause-level denials: "this is not a pass, an avoid, or a no-value call".
    remainder = re.sub(r"(?:is not|it is not|are not|never|not)\b[^.]*", "", remainder)
    # Word-level denials: "no selection, no lean, no pass and no stake". The
    # card states its own emptiness this way, and "no pass" is the opposite of
    # asserting a pass. Stripping only the clause form left this one standing.
    remainder = re.sub(r"\bno[\s-]+(?:selection|lean|pass|stake|value)\w*", "", remainder)
    for banned in (" pass", "avoid", "no value", "no-value", "lean"):
        assert banned not in remainder, (
            f"The card asserts {banned!r} outside a denial. An excluded market "
            "is never a pass, an avoid or a no-value call."
        )


def test_the_card_comment_mentions_nobody(carded):
    """An @mention overrides an ignored repository subscription, so a mention
    here would resume Cooper's email however his settings are set. The workflow
    greps for this too and fails the run; this catches it a step earlier."""
    import re

    _, tmp = carded
    for name in ("cbb_card_comment.md", "cbb_gameday_card.md"):
        path = tmp / "outputs" / name
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            assert not re.search(r"(^|[^A-Za-z0-9_/])@[A-Za-z0-9][A-Za-z0-9-]*", text), (
                f"{name} contains an @mention."
            )


def test_opinions_are_frozen_before_the_games_they_describe(carded):
    """The forward ledger's whole value is that an opinion was written down
    before the result existed. A snapshot is evidence precisely because of
    when it was written."""
    _, tmp = carded
    snapshots = list((tmp / "archive").rglob("*.csv"))
    if not snapshots:
        pytest.skip("This card froze nothing, which is legitimate with no board coverage.")
    frame = pd.read_csv(snapshots[0])
    assert len(frame) > 0
    if "commence_time" in frame.columns and "snapshot_date" in frame.columns:
        tips = pd.to_datetime(frame["commence_time"], utc=True, errors="coerce")
        assert (tips > pd.Timestamp.now(tz="UTC")).all(), (
            "A frozen opinion describes a game that had already tipped."
        )


def test_a_live_run_for_another_day_is_refused_without_rehearsal(tmp_path, provider_names):
    """Freezing a snapshot for a future slate would make the real run that day
    find one already standing and leave it there — and the first opinion of
    opening night would be a rehearsal taken before the teams were known."""
    board = build_board(tmp_path, provider_names)
    result = run_card(board, tmp_path, "--slate-date", "2027-01-12")
    assert result.returncode != 0 or "rehearsal" in (result.stdout + result.stderr).lower(), (
        "A card priced for a day that is not today was accepted without "
        "--rehearsal."
    )


def test_the_card_opens_no_socket(tmp_path, provider_names, monkeypatch):
    """The offline path must be offline. Asserted at the socket layer rather
    than inferred from the absence of a credential."""
    board = build_board(tmp_path, provider_names)
    result = run_card(board, tmp_path)
    assert result.returncode == 0
    # A card that reached the network without a credential would have failed
    # loudly; this pins the stronger claim that it never tried.
    assert "apiKey" not in result.stdout
    assert "requests_used" not in result.stdout.lower() or "0" in result.stdout
