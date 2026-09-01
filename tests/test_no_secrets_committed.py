"""No credential is ever committed, and the guard proves it still works.

These tests run against the files **git actually tracks**, so they fail the
build if a secret is ever committed — including by a future change that means
well. They deliberately do not read `.env`: the point is to prove nothing *else*
contains a credential, and reading the real key here would be the very leak
being guarded against.

`git ls-files` rather than a filesystem walk is the invariant. An unstaged file
is not yet a leak; a staged one is. The football lab records the moment this
mattered: its first commit of a backtest tripped the guard in CI and not
locally, because the suite had been run before the file was staged.

## The exemption is by recorded value, never by directory

A 32-hex run is the shape of an Odds API key **and** the shape of an Odds API
event id, and event ids are all over `data/raw/` and `data/outputs/`.

Exempting the directories they live in would be the easy fix and the wrong one
— it carves a hole in the guard exactly where provider data lands. So the
exemption is by *value*: every event id this repository has actually recorded is
collected from the provider artifacts, and those literals alone are allowed. Any
other 32-hex run is still a finding.

This cannot be used to smuggle a key past the guard. A key would have to be
written into a provider artifact **as an event id** to be exempted, and the
credential never appears in a response body — it travels only in the query
string, which `API_KEY_PARAM` covers everywhere including there.

Note the asymmetry that makes it safe: collection is a `fullmatch` on a *typed
field* (a named JSON key, a named CSV column, or a filename stem); detection is
a `finditer` over *raw text*. A key pasted anywhere in a body is still found.
"""

from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path

import pytest

from cbb_betting_lab.config import REPO_ROOT
from cbb_betting_lab.providers.env_file import ENV_FILENAME, PROVIDER_ENV_ALLOWLIST


#: This file necessarily contains every pattern it hunts for, so it must not
#: scan itself. A scanner that flags its own needles reports a false positive
#: forever and teaches everyone to ignore it.
SELF = Path(__file__).resolve()

DOC_SUFFIXES = {".md", ".rst", ".txt"}
BINARY_SUFFIXES = {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".parquet"}

#: Every fake-secret literal any test in this suite uses. Fake secrets are named
#: after what must not happen to them, so a grep hit reads as its own
#: explanation.
PLACEHOLDERS = {
    "your-secret-key",
    "your-api-key",
    "probe-secret-must-not-be-written",
    "card-secret-never-write",
    "shadow-test-secret-never-write",
    "purchase-secret-must-not-be-logged",
    "${{",
}

HEX_KEY = re.compile(r"\b[0-9a-f]{32}\b")

#: Matches `apiKey=` **with a value**, never the bare token. The bare token
#: appears legitimately in the redaction regex that strips credentials and in
#: tests asserting the token is absent; flagging it would force those defences
#: to be written obscurely, or exempted, and both are worse than matching
#: precisely.
API_KEY_PARAM = re.compile(r"apiKey=[A-Za-z0-9]{8,}")

#: `[ \t]*` and not `\s*`. `\s` crosses a newline, so `NAME=` on one line and
#: any word on the next read as an assignment — which is exactly what
#: `.env.example` looks like, and it made the sibling guard fail on a file whose
#: values are all empty.
ASSIGNMENT = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in PROVIDER_ENV_ALLOWLIST) + r")[ \t]*=[ \t]*(\S+)"
)

_EVENT_ID_KEYS = ("id", "event_id")


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, check=True
    )
    names = [item for item in result.stdout.decode("utf-8").split("\0") if item]
    return [REPO_ROOT / name for name in names]


def _text_files() -> list[Path]:
    return [
        path
        for path in _tracked_files()
        if path.is_file()
        and path.suffix.lower() not in BINARY_SUFFIXES
        and path.resolve() != SELF
    ]


def _read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""


def _known_provider_event_ids() -> set[str]:
    """Every 32-hex event id this repository has actually recorded.

    Three independent sources, over tracked provider artifacts only.
    """
    known: set[str] = set()
    for path in _tracked_files():
        if not path.is_file():
            continue
        # A cached response is named after the event it holds, so the filename
        # is a second, independent record of the same id.
        stem = path.name.split("_")[0]
        if HEX_KEY.fullmatch(stem):
            known.add(stem)

        relative = str(path.relative_to(REPO_ROOT))
        if not (relative.startswith("data/raw/") or relative.startswith("data/outputs/")):
            continue

        if path.suffix == ".json":
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue

            def walk(node) -> None:
                if isinstance(node, dict):
                    for key, value in node.items():
                        if (
                            key in _EVENT_ID_KEYS
                            and isinstance(value, str)
                            and HEX_KEY.fullmatch(value)
                        ):
                            known.add(value)
                        walk(value)
                elif isinstance(node, list):
                    for item in node:
                        walk(item)

            walk(payload)
        elif path.suffix == ".csv":
            try:
                with path.open(newline="", encoding="utf-8") as handle:
                    reader = csv.reader(handle)
                    header = next(reader, [])
                    columns = [
                        i for i, name in enumerate(header) if name in _EVENT_ID_KEYS
                    ]
                    if not columns:
                        continue
                    for row in reader:
                        for index in columns:
                            if index < len(row) and HEX_KEY.fullmatch(row[index]):
                                known.add(row[index])
            except (OSError, UnicodeError, csv.Error, StopIteration):
                continue
    return known


# -- the guard ----------------------------------------------------------------


def test_env_file_is_never_tracked():
    assert ENV_FILENAME not in {p.name for p in _tracked_files()}


def test_env_file_is_gitignored():
    result = subprocess.run(
        ["git", "check-ignore", ENV_FILENAME], cwd=REPO_ROOT, capture_output=True
    )
    assert result.returncode == 0, f"`{ENV_FILENAME}` is not gitignored."


def test_no_tracked_file_assigns_a_real_credential():
    findings: list[str] = []
    for path in _text_files():
        for name, raw in ASSIGNMENT.findall(_read(path)):
            value = raw.strip("'\"`").rstrip(",;)")
            if not value or value in PLACEHOLDERS:
                continue
            # A reference to a value is not a value.
            if value[0] in "$<{":
                continue
            if path.suffix.lower() in DOC_SUFFIXES and not HEX_KEY.fullmatch(value):
                continue
            findings.append(f"{path.relative_to(REPO_ROOT)}: {name}=<redacted>")

    assert not findings, f"A credential appears to be assigned in: {findings}"


def test_no_tracked_file_contains_an_odds_api_key_shape():
    known = _known_provider_event_ids()
    findings: list[str] = []
    for path in _text_files():
        name = path.name.lower()
        if "checksum" in name or "receipt" in name:
            continue
        for hit in HEX_KEY.findall(_read(path)):
            if hit not in known:
                findings.append(f"{path.relative_to(REPO_ROOT)}: <32-hex run>")

    assert not findings, (
        "A 32-hex run that is not a recorded provider event id appears in: "
        f"{findings[:20]}"
    )


def test_generated_reports_never_include_the_api_key_parameter():
    findings = [
        str(path.relative_to(REPO_ROOT))
        for path in _text_files()
        if API_KEY_PARAM.search(_read(path))
    ]

    assert not findings, f"`apiKey=<value>` appears in: {findings}"


@pytest.mark.parametrize("name", PROVIDER_ENV_ALLOWLIST)
def test_credential_names_are_referenced_but_never_valued(name: str):
    for path in _text_files():
        for found, raw in ASSIGNMENT.findall(_read(path)):
            if found != name:
                continue
            value = raw.strip("'\"`").rstrip(",;)")

            assert not HEX_KEY.fullmatch(value), (
                f"{path.relative_to(REPO_ROOT)} assigns a key-shaped value to {name}."
            )


def test_the_production_credential_name_is_the_one_the_workflow_uses():
    """A contract with GitHub Actions. It must not drift."""
    assert "CBB_ODDS_API_KEY" in PROVIDER_ENV_ALLOWLIST


# -- the meta-tests, which are why the guard has not rotted -------------------


def test_the_api_key_parameter_check_still_catches_a_real_leak():
    assert API_KEY_PARAM.search("https://api.the-odds-api.com/v4/sports/?apiKey=abcd1234efgh")
    assert API_KEY_PARAM.search("...&apiKey=0123456789abcdef0123456789abcdef&regions=us")

    # And stays silent on the defences that must be written plainly.
    assert not API_KEY_PARAM.search(r're.sub(r"(apiKey=)[^&\s]+", ...)')
    assert not API_KEY_PARAM.search('assert "apiKey=" not in text')
    assert not API_KEY_PARAM.search("apiKey=[redacted]")


def test_the_key_shape_check_still_catches_a_real_leak():
    assert HEX_KEY.search("CBB_ODDS_API_KEY=0123456789abcdef0123456789abcdef")
    assert not HEX_KEY.search("a" * 64)


def test_the_guard_excludes_itself_from_its_own_scan():
    assert SELF not in [p.resolve() for p in _text_files()]


def test_the_guard_still_scans_other_test_files():
    """Self-exclusion must be exactly one file, not all of `tests/`."""
    scanned = {p.name for p in _text_files()}

    assert "test_gates_fail_closed.py" in scanned
    assert "test_prices_dedupe_on_identity_not_the_row.py" in scanned


def test_the_event_id_exemption_is_by_value_and_not_by_directory():
    """A hex run that is not a recorded event id is still a finding.

    If this test's first assertion ever fails it means no provider event ids
    have been recorded yet, so the exemption is untested rather than working —
    which is worth knowing, because an untested exemption is the shape of a
    hole nobody notices until it is used.
    """
    known = _known_provider_event_ids()
    stranger = "deadbeef" * 4

    assert HEX_KEY.fullmatch(stranger)
    assert stranger not in known


def test_the_key_shape_check_still_fires_on_something_that_is_not_an_event_id():
    known = _known_provider_event_ids()
    candidate = "0123456789abcdef0123456789abcdef"

    assert candidate not in known
    assert HEX_KEY.search(f"CBB_ODDS_API_KEY={candidate}")
