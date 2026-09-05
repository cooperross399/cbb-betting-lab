"""There is one experiment ledger, and every reader and writer uses it.

The family-wise correction is the ledger's cumulative count. That sentence has
a hidden premise — that there is one cumulative count — and for two days there
were two: a tracked copy under `data/outputs/holdout/` that `run_replication`
appended its holdout looks to, while `run_price_backtest` read its correction
from the original. They were identical only because the one replication so far
recorded zero looks. The first holdout look would have gone into the copy and
the next backtest's correction would have been short by exactly that look.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]


def test_there_is_exactly_one_tracked_ledger_json():
    import subprocess

    tracked = subprocess.run(
        ["git", "ls-files", "--", "data/outputs"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split()
    ledgers = [p for p in tracked if p.endswith("experiment_ledger.json")]
    assert ledgers == ["data/outputs/experiment_ledger.json"], (
        f"tracked ledger files: {ledgers}. A second ledger is a second cumulative count."
    )


def test_the_guard_names_one_ledger():
    text = (REPO / ".github" / "workflows" / "ledger-guard.yml").read_text(encoding="utf-8")
    assert "holdout/experiment_ledger" not in text
    named = set(re.findall(r"data/outputs/(?:[a-z_/]+/)?experiment_ledger\.json", text))
    assert named == {"data/outputs/experiment_ledger.json"}, named


def test_scripts_do_not_default_the_ledger_to_the_output_dir():
    """`--output-dir` moves records and reports. It must not move the ledger."""
    for name in ("run_replication.py", "run_price_backtest.py"):
        src = (REPO / "scripts" / name).read_text(encoding="utf-8")
        assert "PB.ledger_path(output_dir)" not in src, (
            f"{name} still resolves the ledger beside --output-dir, which is how a "
            "holdout run ends up appending to a copy"
        )
        assert "PB.ledger_path(OUTPUTS_DIR)" in src, f"{name} does not default to the repository ledger"
