"""Where everything lives, and the one place a path is written down.

Ported from the sibling labs. Paths are resolved from this file's location
rather than the working directory, because a workflow step and a local shell
have different working directories and a report that lands in the wrong place
is a report nobody reads.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Repository root — three parents up from `src/cbb_betting_lab/config.py`.
REPO_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = REPO_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUTPUTS_DIR = DATA_DIR / "outputs"
MANUAL_DIR = DATA_DIR / "manual"
STAGING_DIR = DATA_DIR / "staging"
DOCS_DIR = REPO_ROOT / "docs"

#: The environment variable holding the Odds API credential. The production
#: value is the GitHub secret of the same name. It is never read into a log,
#: never compared against a literal, and never written to a file.
ODDS_API_KEY_ENV = "CBB_ODDS_API_KEY"

#: The CollegeBasketballData bearer token, same rules.
CBBD_API_KEY_ENV = "CBBD_API_KEY"


def ensure_dirs() -> None:
    for directory in (RAW_DIR, PROCESSED_DIR, OUTPUTS_DIR, MANUAL_DIR, STAGING_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def output_path(name: str) -> Path:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    return OUTPUTS_DIR / name


def env(name: str, default: str = "") -> str:
    """An environment variable, with no logging of the value.

    Deliberately thin. It exists so that a grep for the credential name finds
    one reader rather than a dozen, which is what makes the secrets discipline
    checkable rather than aspirational.
    """
    return os.environ.get(name, default) or default
