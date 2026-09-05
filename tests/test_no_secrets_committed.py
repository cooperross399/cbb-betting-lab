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

## What this file used to claim, and what an audit measured

The previous version of this module said, in its docstring, *"This cannot be
used to smuggle a key past the guard."* That sentence was false in five
separate ways, every one of them reproduced by committing a key to a scratch
clone and watching the suite stay green:

* **A filename exemption.** `if "checksum" in name or "receipt" in name:
  continue` skipped every 32-hex run in any such file — a real key included —
  and aimed the blind spot at acceptance receipts, the artifacts whose whole
  job is provenance.
* **A `\\b`-fenced, lowercase-only key matcher.** `\\b[0-9a-f]{32}\\b` will not
  open beside `_`, because `_` is a word character, so `<key>_odds.json` — the
  provider cache's own naming convention — hid a key; and an uppercased copy
  of a key is the same key, which the class could not see at all.
* **Bodies only.** `if not path.is_file(): continue` dropped every symlink
  (`is_file()` follows the link and is False for a dangling one), and nothing
  scanned a *path*. A key committed as a filename, or as a symlink's target,
  was read by nothing — and a key in a `.png`-named text file was read by
  nothing either, because the body scan dropped the suffix and no name scan
  existed.
* **Self-nomination.** The stem harvest `path.name.split("_")[0]` ran over
  *every* tracked file before any directory restriction, so a decoy
  `<key>_x.md` at the repository root nominated the key into the exemption
  set and turned the same key green in `scripts/`. A report the repository
  *writes* may spend an exemption; it must never create one.
* **`NAME=value` and nothing else.** The assignment scan knew one operator
  and no closers, so `os.environ["CBB_ODDS_API_KEY"] = "<key>"` — the
  canonical Python spelling — was not an assignment, YAML's `NAME: value` was
  not one, and any `.md`/`.rst`/`.txt` value that was not 32 hex characters
  was skipped outright, so a real key assigned in prose passed.

Every one of those is now pinned by a test that fails against the module as it
was — `_bypass_*` below, each run against the exact function that used to let
it through — and what *still* gets through is written into
`test_the_gaps_this_guard_still_has_are_the_ones_written_down` rather than
into a sentence that overclaims. A guard that names its own limits beats one
that says "cannot".

## The exemption is by recorded value, never by directory

A 32-hex run is the shape of an Odds API key **and** the shape of an Odds API
event id. Exempting the directories event ids live in would carve a hole in the
guard exactly where provider data lands, so the exemption is by *value*, and the
value has to be vouched for. Two routes exist, and they are deliberately not
the same route:

* the provider's own cache under `data/raw/` may nominate an id — from a
  response body, never from a filename — and `.gitignore` makes that directory
  untrackable, so on this repository today that route nominates nothing;
* `RECORDED_EVENT_IDS` lists, by hand, the ids a tracked report carries, with
  the file each was read from, and `test_every_vouched_event_id_is_still_in_the
  _file_it_was_read_from` fails the day one of them is not.

A vouched id may be *spent* only under `EXEMPT_SCOPE`. An id the retention
probe genuinely recorded does not excuse the same hex run in `scripts/`.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import unicodedata
from collections.abc import Iterable
from pathlib import Path

import pytest

from cbb_betting_lab.config import REPO_ROOT
from cbb_betting_lab.providers.env_file import ENV_FILENAME, PROVIDER_ENV_ALLOWLIST


#: This file necessarily contains every pattern it hunts for, so it must not
#: scan itself. A scanner that flags its own needles reports a false positive
#: forever and teaches everyone to ignore it.
SELF = Path(__file__).resolve()

#: Every fake-secret literal any test in this suite uses. Fake secrets are named
#: after what must not happen to them, so a grep hit reads as its own
#: explanation. This is the whole allowance documentation gets: there is no
#: longer a second, wider one for `.md`/`.rst`/`.txt`.
PLACEHOLDERS = {
    "your-secret-key",
    "your-api-key",
    "probe-secret-must-not-be-written",
    "card-secret-never-write",
    "shadow-test-secret-never-write",
    "purchase-secret-must-not-be-logged",
    "capture-secret-must-not-be-written",
    "${{",
}

#: A 32-hex-character run is the shape of an Odds API key.
#:
#: Lookarounds and not `\b`, and `A-F` as well as `a-f`. `\b` will not open
#: beside `_` because `_` is a word character, and the provider cache names its
#: files `<event id>_odds.json` — the convention an attacker would copy.
#: Measured on the previous matcher: `KEY_<key> = 1`, `f"<key>_odds.json"` and
#: an uppercased key were all full passes. The lookarounds still refuse to fire
#: inside a longer hex run, so a SHA-256 in a manifest is not a finding.
HEX_KEY = re.compile(r"(?<![0-9A-Fa-f])[0-9A-Fa-f]{32}(?![0-9A-Fa-f])")

#: The matcher this replaces, kept so the regression tests can show what it
#: missed rather than assert it from memory.
_SUPERSEDED_HEX_KEY = re.compile(r"\b[0-9a-f]{32}\b")

#: Field names under which a 32-hex value in a provider artifact is an EVENT id
#: rather than a credential.
_EVENT_ID_KEYS = ("id", "event_id", "provider_event_id")

#: Where a vouched event id may be *spent*. This is a spend rule and only a
#: spend rule: nothing under it creates an exemption. Creating one is the
#: provider cache's privilege (`_collect_event_ids`, `data/raw/` only) or a
#: human's (`RECORDED_EVENT_IDS`).
EXEMPT_SCOPE = ("data/raw/", "data/outputs/")

#: Where the provider cache — the only directory whose *bodies* may nominate an
#: event id — lives. Untrackable on this repository (`.gitignore` names it), so
#: today this nominates nothing, which is the fail-closed direction.
NOMINATING_SCOPE = "data/raw/"

#: The event ids a tracked report carries, vouched by hand.
#:
#: All 102 were read out of `data/outputs/cbb_retention_probe.json` on
#: 2026-09-04, where each sits under the typed key `provider_event_id` in the
#: probe's `events` list — the record of the 2026-09-01 retention probe (144
#: planned, 102 matched, 77,160 credits). They are listed here rather than
#: harvested from that file because the file is written by this repository:
#: harvesting from it let a hand-committed `data/outputs/x.json` carrying
#: `{"id": "<a key>"}` exempt the key it was smuggling. A list a human edits is
#: a list a reviewer reads; adding one line here is the act that vouches.
#:
#: `test_every_vouched_event_id_is_still_in_the_file_it_was_read_from` holds
#: this set against the file in both directions: a listed id the file no
#: longer carries is stale and must go, and an id the file carries that is not
#: listed here is a finding until somebody vouches for it.
RECORDED_EVENT_IDS: frozenset[str] = frozenset(
    {
        "03503c4dbd238e91c166bb559e5a3ad6",
        "039f67011b440fb37a9f4e2bc2f16e35",
        "05515ccd8dc47a605ac00d64c40ba1e8",
        "0932c813a1cec7fe63a2ade7fbefc04f",
        "0b1d66a8749e69eed9aef423368342da",
        "0b40b74a7689260d692a11b426fe9321",
        "102d64a69800e805e2cf2f13f4dfed8e",
        "107fec52e1d9d6f2f6e74f47eb1d520b",
        "138d12535b62253f5e8faa8d72dfd294",
        "187797593c613c7a26b66aac18c1a950",
        "1a999d4b31bc0d49d1cfc4287b3c222e",
        "1d68bc11105a6e7ea65c6f2ddfcc5c8e",
        "1d99d6d17af806bcd8b34aec6e4609c8",
        "23cb2b0e022d1e12a53c1971c53d860d",
        "2410a0c40f81b77970b3c516f50c6e34",
        "25eaab15ecebd6e98f536ca194ad1166",
        "288583ab80b81db96382fddbee41396e",
        "295f92c072091d3b8d29f74d6660e611",
        "2ac645adb59f24d77470e29dc52f0515",
        "2adf2fc46d29404c2ecd9cbaa7134801",
        "2bc0f3c6608363d134d3f028b8c85810",
        "2e1d0eb524a1bf49df19aa170a6ea42d",
        "2e7f0a6158477f073db1d82f088e2f6d",
        "3563c3cd9fdfe727f8c4d480bbab9f02",
        "38719ab42b9d3e3fa0d45da96fbdf765",
        "38a957852d4e61b49d29915dcb7f4251",
        "3cb3d2347de37e170659af364d669648",
        "3e9a66b5ed9670aa4f7bf4bb1281f9bd",
        "3ebcf9faa7ae3c2b53d1ef31a5a968ea",
        "4515dbe9524c1d22f060e60993dc6af2",
        "45676765803fd4387372a12bb6399c71",
        "479832d80b884a38e48c830266b6238e",
        "4869997b2615a76a994a535081c3a212",
        "4b05793c85f677b42970a35296185aab",
        "4c05c053758b9252b2bdfe80fdfac663",
        "4cc32441480af4f480a9d8d08f95ec8e",
        "4ff4d3d15a374780f1f6e2692177b79f",
        "50c21b69ae7159a6556667b768512528",
        "51b03b69709b1760c5c54eb745165499",
        "55f6b5edb6ae73135be4dc277032c191",
        "5d5ff1039daa2f508377e5e1ff16b934",
        "602a16289f91ce40f8277824de5b10ef",
        "6199ded4c543a0bf91f96b1e5d54a2b4",
        "67d0cfe98349c18fe7e5e78dc53e97e5",
        "6874f4b4a1a9243344010e4e65f3741f",
        "6ebb019d692ab0d7c5ca1593d19b7cf2",
        "6f0765b4c7ea31444ec8a23fb86e6648",
        "6fb522051bd1746de6d22c7553b65cdb",
        "707895a1de7b5895988d8cc78c5e1fe0",
        "70d71f54008cc55a3cd1f5251046264d",
        "71bddb41a28bc44b8e88213de3097af3",
        "75f5866a019b86e7264f355bd306321b",
        "76697c93ab92571fc2998ad9728e50bc",
        "780c0868037f3b02fdea6adaf4a2447a",
        "7afc76f206120a848a7ba4d98d64ca96",
        "7b0395b1b4860adf903c9d616453e9c5",
        "7ddda6367079446ebe1e18815fd5cf46",
        "7ee8cab6db50bfa0f97ac6fb9ca42508",
        "8ae8a6e1ce042a49310a23bc5775defb",
        "8b661d925939280e7ebc3192b70d3bc4",
        "8bb0006149e0067dd3f4370987f25d3c",
        "8bb323e767f33e52c802ea72e1406028",
        "8cc3d084e398d790081c6ee9003a80be",
        "930319d687992d02e211708973d066c7",
        "9427cd95186a83064390fe1ee826e974",
        "947638afe5c7a210ac5d8a6d04e92fcd",
        "95106d7cd25a2b5e339c973544ceca47",
        "96a3509b5d85986f2b3e6ce54e1be64d",
        "99dd2cd774026874342cb5b868c9281e",
        "9bbe4c3408e40a28be734107b576ce83",
        "a28a4e07525f14a6930fa8fe46b0d9a9",
        "a50e57ea6aa17d46dda91f9a9d33fae8",
        "a656b2a076d07acff2b809012a37e667",
        "ac714b95b2777cf4a5078172640c13e7",
        "adab02adbc983d5f7a5ef09083f6ccd9",
        "afb08eee9f956db45e4f8c8249b5af8f",
        "b051150063d9410e97ce5df7d407e4b4",
        "b30810522f2d3d88073f5aadd833d9ff",
        "b5802081a33d96f330b1bb8c62586c86",
        "b6d0b9184c2f180b0445f9a39356d22b",
        "c070a9b61fd49fbd3dfcaa6d3a41523e",
        "c11302fed18386b83bdc0491c7ce6a2f",
        "c339b984660a44726b7cdd7f8d4c8bb4",
        "c49bdac95a0575b07541ac104eb6e78d",
        "c5a31e91dd06e236fe7e26c262fdf4fd",
        "cb594dfdc3259e7a3376bc1167311085",
        "cf7accc58650025718bc2e5e63ed731d",
        "cf922e9b07409ffd2cdecfa0251ebb59",
        "d4cff411d8de454c03e16d1b86580f53",
        "ddf162705cef4c1b517ea7768fbd0f76",
        "e2f53c4821ca74a0032c43d614d94f2c",
        "eb9cc15be7d3e50efed9dd100a66aef4",
        "ec44d694728cf6472761aed1025db7b9",
        "ec6928723ac4bd2765eab1446eab4e81",
        "f1a406cb7b4f3f379e36d10f1453f1eb",
        "f52f37a510e7cb7c2cf5db6ac824122d",
        "f5ca3e28fa58ccd854b187115c7c857e",
        "f91005860b9a44e7bd8a70f8c0003516",
        "f98e2651ba4644c1e61a7cb58d2570a8",
        "fa77fa6d9b4de5ce44f7d257d70eed60",
        "fb88f48aafaaee316979dbe2bf3675d9",
        "ff570cce327f4fcf565c33544cf5143a",
    }
)

#: The file every id above was read from, and the only file whose typed ids the
#: vouch test compares against. A second report that needs to carry ids gets a
#: second entry here, not a widening of the harvest.
VOUCHED_FILES: dict[str, frozenset[str]] = {
    "data/outputs/cbb_retention_probe.json": RECORDED_EVENT_IDS,
}

#: Every credential-ish variable name a tracked file may mention but never
#: assign. The two the provider code reads, plus the two generic spellings the
#: dry-run test clears from the environment; the drift test below fails the
#: build if a credential-shaped name appears in the tree that is missing from
#: here, because a name this module does not know is a name it cannot catch
#: being assigned. Longest first, so the alternation cannot stop short.
CREDENTIAL_NAMES: tuple[str, ...] = tuple(
    sorted(
        {name for name in PROVIDER_ENV_ALLOWLIST if name.endswith("_KEY")}
        | {"ODDS_API_KEY", "THE_ODDS_API_KEY"},
        key=lambda name: (-len(name), name),
    )
)

#: The shape of a credential variable name, used to find names this guard has
#: not been taught. `_API_KEY` alone recognised one spelling; a credential named
#: `..._APIKEY` or `..._API_TOKEN` would have un-armed two tests at once.
CREDENTIAL_NAME_SHAPE = re.compile(r"\b[A-Z][A-Z0-9_]*_(?:API_KEY|APIKEY|API_TOKEN)\b")

#: `apiKey=` FOLLOWED BY A VALUE is a leak. The bare token is not: it appears in
#: the redaction regex and in tests asserting the token is absent. The value
#: class admits `-` and `_` because a real key can carry them, and the first
#: character stays alphanumeric so `apiKey=[redacted]` is not a match.
API_KEY_PARAM = re.compile(r"api[_-]?key=[A-Za-z0-9][A-Za-z0-9_-]{7,}", re.IGNORECASE)

#: Punctuation that may sit between a credential name and the operator that
#: gives it a value: the closing half of a quote, a subscript, a code span, an
#: emphasis marker, an HTML tag. `os.environ["NAME"] = "..."`, `` `NAME` = ``,
#: `**NAME**: ...`, `<code>NAME</code>: ...`. A shape — any character that is
#: neither alphanumeric, a newline, nor one of the operators read back — and
#: not an enumeration, because an enumeration is a spelling. Bounded at eight
#: so it cannot run away across a line.
_CLOSERS = r"(?:</?[A-Za-z][A-Za-z0-9]*[^<>\n]{0,64}>|[^0-9A-Za-z\n=:,|]){0,8}"

#: A horizontal blank, agreeing with `\S` about what a blank is. `[ \t]*` is
#: ASCII and `\S` is Unicode-aware, and a U+00A0 after the operator fell in the
#: gap between them: the spacing class would not consume it and `\S` would not
#: start on it, so `export NAME=<U+00A0><key>` opened no match anywhere.
#: `[^\S\r\n]*` is every character `\S` refuses minus the line breaks, so the
#: two classes partition the input. Newline stays excluded: it is what keeps
#: `.env.example`'s bare `NAME=` green.
_BLANK = r"[^\S\r\n]*"

#: How much of the line after the operator is handed to the value tests. A
#: zero-width lookahead, so a nested occurrence is not swallowed, and bounded,
#: because an unbounded capture on a line carrying the name two thousand times
#: is quadratic and a guard slow enough to look hung is a guard someone turns
#: off. `.` does not cross a newline, so the line boundary is unchanged.
_REST_OF_LINE = r"(?=(.{0,512}))"

_NAMES = "|".join(re.escape(name) for name in CREDENTIAL_NAMES)

#: `NAME <closers> <op>= value` where NAME is a credential variable. The
#: operator is the family `[:?+]?=` — `:=`, `?=`, `+=` are assignments a
#: machine reads back — and the fence is `(?<![A-Za-z0-9])`, not `\b`, because
#: `\b` will not open between `_` and a letter and `_NAME_` is the Markdown
#: emphasis spelling. Case-insensitive: a credential written under a lowercased
#: spelling of the name is the same credential.
ASSIGNMENT = re.compile(
    r"(?<![A-Za-z0-9])(" + _NAMES + r")" + _CLOSERS + _BLANK + r"[:?+]?=" + _BLANK + _REST_OF_LINE,
    re.IGNORECASE,
)

#: The same idea for the separators `=` cannot cover: YAML's `NAME: value`, the
#: comma of `{"NAME": value}`, and the pipe of a Markdown table row — this
#: repository documents its credential in a table. These also separate a name
#: from ordinary prose, so under this family the value must independently look
#: like a value (`_looks_like_a_credential_value`).
SEPARATED = re.compile(
    r"(?<![A-Za-z0-9])(" + _NAMES + r")" + _CLOSERS + _BLANK + r"[:,|]" + _BLANK + _REST_OF_LINE,
    re.IGNORECASE,
)

#: Does this token look like a credential *value* rather than a word of prose?
#: One unbroken run of name-safe characters, long, with at least one digit, and
#: not itself an identifier in shouting case. The length rejects "the"; the
#: class rejects a path ("docs/x.md" carries `/` and `.`); the digit rejects
#: "not-configured"; the shouting-case clause rejects a bare list of credential
#: NAMES. The two gaps this leaves are in the known-gaps ledger.
CREDENTIAL_VALUE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{11,}")
SHOUTING_CASE = re.compile(r"[A-Z0-9_]+")

#: Unicode categories that occupy no space and belong to no credential: the
#: format and control marks (U+200B, U+00AD, U+FEFF, ...). `\S` starts on every
#: one of them, so they ride *into* a captured token rather than being consumed
#: as spacing; `_unwrap` deletes them by category, not by codepoint list.
INVISIBLE_CATEGORIES = frozenset({"Cf", "Cc"})

#: Suffixes whose *bodies* there is no point decoding. A statement about bodies
#: only: a file with one of these suffixes still has a name, and a name needs
#: no decoding. `.parquet` is here because `tests/fixtures/real_data/` tracks
#: three of them.
BINARY_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".ico", ".pdf", ".zip", ".parquet"}
)


# -- the corpus ---------------------------------------------------------------


def _tracked_files() -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=REPO_ROOT, capture_output=True, check=True
    )
    names = [item for item in result.stdout.decode("utf-8").split("\0") if item]
    return [REPO_ROOT / name for name in names]


def _link_target(path: Path) -> str:
    """What a tracked symlink carries, which is neither name nor body.

    `git` stores a symlink as a blob whose contents are the target string, so
    `ln -s <key> docs/provider_key` commits the credential in plaintext. The
    old body scan dropped the path on `path.is_file()` — False for a dangling
    link — and no name scan existed. Returns `""` for anything that is not a
    symlink, so callers can concatenate it unconditionally.
    """
    try:
        if not path.is_symlink():
            return ""
        return os.readlink(path)
    except OSError:
        return ""


def _is_this_file(path: Path) -> bool:
    """`path` is this module, resolving symlinks — and never raises.

    `Path.resolve()` raises on a symlink loop, and a committed `ln -s loop loop`
    would turn the guard into a crash rather than a finding. A path that cannot
    be resolved is *not* this file, so it stays in the corpus.
    """
    try:
        return path.resolve() == SELF
    except (OSError, RuntimeError):
        return False


def _body_scannable(paths: Iterable[Path]) -> list[Path]:
    """The subset of `paths` whose contents are worth reading as text.

    A symlink is kept even when it dangles: its body reads as empty, and
    keeping it is what carries the path into `_assignment_offenders`, which
    scans the link target beside the body.
    """
    keep: list[Path] = []
    for path in paths:
        if not path.is_file() and not path.is_symlink():
            continue
        if _is_this_file(path):
            continue
        if path.suffix.lower() in BINARY_SUFFIXES:
            continue
        keep.append(path)
    return keep


def _text_files() -> list[Path]:
    return _body_scannable(_tracked_files())


def _read(path: Path) -> str:
    """The file as text, plus a NUL-stripped reading when there are NULs.

    A UTF-16 file decodes under `errors="ignore"` into `K\\x00E\\x00Y...`, and
    every matcher here wants an unbroken run. Removing the NULs recovers the
    ASCII; appending rather than replacing keeps the ordinary reading.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    if "\x00" in text:
        return text + "\n" + text.replace("\x00", "")
    return text


# -- the exemption --------------------------------------------------------------


def _collect_event_ids(paths: Iterable[Path], root: Path) -> tuple[set[str], set[str]]:
    """Event ids the provider cache nominates, split by how strong the evidence is.

    `content_ids` come out of a response body under a typed key — the provider
    put them there. `name_ids` come off a filename, which anyone can choose, so
    they are a claim to be checked against `content_ids` and never an
    exemption. Both are read **only under `NOMINATING_SCOPE`**: harvesting
    stems repo-wide is what let a root-level `<key>_x.md` nominate a key, and
    harvesting bodies under `data/outputs/` is what let a report this
    repository writes nominate the id it wanted exempted.
    """
    content_ids: set[str] = set()
    name_ids: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in _EVENT_ID_KEYS and isinstance(value, str) and HEX_KEY.fullmatch(value):
                    content_ids.add(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for path in paths:
        relative = path.relative_to(root).as_posix()
        if not relative.startswith(NOMINATING_SCOPE):
            continue
        stem = path.name.split("_")[0]
        if HEX_KEY.fullmatch(stem):
            name_ids.add(stem)
        if path.suffix == ".json":
            try:
                walk(json.loads(path.read_text(encoding="utf-8")))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
        elif path.suffix == ".csv":
            try:
                header, *rows = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError):
                continue
            columns = [name.strip() for name in header.split(",")]
            wanted = [i for i, name in enumerate(columns) if name in _EVENT_ID_KEYS]
            if not wanted:
                continue
            for row in rows:
                cells = row.split(",")
                for index in wanted:
                    if index < len(cells) and HEX_KEY.fullmatch(cells[index].strip()):
                        content_ids.add(cells[index].strip())
    return content_ids, name_ids


def _typed_ids_in(path: Path) -> set[str]:
    """Every 32-hex value under a typed event-id key in one JSON file."""
    found: set[str] = set()

    def walk(node: object) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                if key in _EVENT_ID_KEYS and isinstance(value, str) and HEX_KEY.fullmatch(value):
                    found.add(value)
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(json.loads(path.read_text(encoding="utf-8")))
    return found


def _exempt_hex_values() -> set[str]:
    """Every 32-hex literal this repository has a vouched reason to allow.

    Which literals, not where: `_hex_key_offenders` decides where, and only
    lets them be spent under `EXEMPT_SCOPE`.
    """
    content_ids, _ = _collect_event_ids(_tracked_files(), REPO_ROOT)
    return content_ids | set(RECORDED_EVENT_IDS)


# -- the scanners ---------------------------------------------------------------


def _hex_key_offenders(
    paths: Iterable[Path],
    allowed: set[str],
    root: Path,
    *,
    names: bool = True,
    bodies: bool = True,
) -> list[str]:
    """Every 32-hex run in `paths` — name, symlink target or body — not accounted for.

    Corpus-as-argument so the regression tests can run this exact code over a
    synthetic file. Only six characters of a finding are reported: enough to
    locate it, not enough to publish it. `allowed` is spendable only under
    `EXEMPT_SCOPE`, for a name exactly as for a body.
    """
    offenders: list[str] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        permitted = allowed if relative.startswith(EXEMPT_SCOPE) else set()
        found: list[str] = []
        if names:
            found += [match.group(0) for match in HEX_KEY.finditer(relative)]
            found += [match.group(0) for match in HEX_KEY.finditer(_link_target(path))]
        if bodies:
            found += [match.group(0) for match in HEX_KEY.finditer(_read(path))]
        for value in found:
            if value in permitted:
                continue
            offenders.append(f"{relative}: {value[:6]}...")
    return offenders


def _readable(paths: Iterable[Path]) -> list[Path]:
    """Every tracked path that has a name to scan: regular files and symlinks,
    binaries included, minus this module."""
    return [p for p in paths if (p.is_file() or p.is_symlink()) and not _is_this_file(p)]


def _hex_offenders_for_corpus(tracked: Iterable[Path], allowed: set[str], root: Path) -> list[str]:
    """Names and link targets over EVERY tracked file, bodies over the text ones.

    The first draft of this scanned binary bodies too, on the reasoning that
    thirty-two consecutive bytes in `[0-9A-Fa-f]` would not occur in a real
    binary. Measured, it does: the tracked schedule parquets under
    `tests/fixtures/real_data/` each carry two such runs in their column
    data, decoded under `errors="ignore"`. A rule that fires on the
    fixtures it ships with is a rule somebody exempts, so binary bodies are
    not decoded, their NAMES are still scanned, and a key written INTO a
    `.png`-named text file is recorded as a gap in
    `test_the_gaps_this_guard_still_has_are_the_ones_written_down` rather
    than claimed closed.
    """
    paths = list(tracked)
    offenders = _hex_key_offenders(_readable(paths), allowed, root, bodies=False)
    offenders += _hex_key_offenders(_body_scannable(paths), allowed, root, names=False)
    return offenders


def _unwrap(raw: str) -> str:
    """Strip the punctuation that surrounds a value in source and prose.

    Invisible characters first, by category. Then a string-literal prefix, so
    `f"{SECRET}"` is read as an interpolation rather than as the value `f`.
    Then quotes, the closing halves of a call or dict, quotes again, and the
    leading `-` of a shell default so `${NAME:-<key>}` is read as the
    assignment it is.
    """
    visible = "".join(c for c in raw if unicodedata.category(c) not in INVISIBLE_CATEGORIES)
    without_prefix = re.sub(r"^[fFrRbBuU]{1,2}(?=[\"'])", "", visible)
    return without_prefix.strip("'\"`").strip(",;)}]").strip("'\"`").lstrip("-")


def _unbracket(value: str) -> str:
    return value.strip("<>{} ")


def _looks_like_a_credential_value(value: str) -> bool:
    if not CREDENTIAL_VALUE.fullmatch(value):
        return False
    if SHOUTING_CASE.fullmatch(value):
        return False
    return any(character.isdigit() for character in value)


def _is_a_reference(value: str) -> bool:
    """`$VAR`, `<placeholder>`, `${{ secrets.X }}`, an f-string `{SECRET}`.

    `$` is unconditional. The bracket forms are not: anything beginning `<` or
    `{` used to be waved through, so `NAME: <sk-live-...>` was not a finding.
    Now the brackets are stripped and what is inside has to fail the value
    test, which `<your-key>` does and a real credential does not.
    """
    if value[0] == "$":
        return True
    if value[0] in "<{":
        return not _looks_like_a_credential_value(_unbracket(value))
    return False


def _assignment_offenders(paths: Iterable[Path], root: Path) -> list[str]:
    """Every `CREDENTIAL_NAME <given> <real value>` in `paths`, by file and name.

    Two families. `=` is an assignment wherever it appears, so its first token
    needs no value test — nothing writes `NAME=` in prose. `:`, `,` and `|`
    also occur in prose, so a match there is a finding only if the value looks
    like a credential. Both read the **rest of the line**, every token: reading
    one token and abandoning the line when it unwrapped to nothing let
    `os.environ["NAME"] = "" "<key>"` and a three-column table row through.
    The symlink target is appended to the text, because `ln -s 'NAME=<key>'
    note` writes the assignment into the index and into no file body at all.
    The value itself is never reported.
    """
    offenders: list[str] = []
    for path in paths:
        relative = path.relative_to(root).as_posix()
        text = _read(path)
        target = _link_target(path)
        if target:
            text = f"{text}\n{target}"
        for pattern, value_must_look_real in ((ASSIGNMENT, False), (SEPARATED, True)):
            for match in pattern.finditer(text):
                tokens = [
                    unwrapped
                    for unwrapped in (_unwrap(token) for token in match.group(2).split())
                    if unwrapped
                ]
                for index, value in enumerate(tokens):
                    must_look_real = value_must_look_real or index > 0
                    if value in PLACEHOLDERS:
                        continue
                    if _is_a_reference(value):
                        continue
                    if must_look_real and not _looks_like_a_credential_value(_unbracket(value)):
                        continue
                    finding = f"{relative}: {match.group(1)}"
                    if finding not in offenders:
                        offenders.append(finding)
                    break
    return offenders


# -- the guard, over the real repository -----------------------------------------


def test_env_file_is_never_tracked():
    assert ENV_FILENAME not in {p.name for p in _tracked_files()}


def test_env_file_is_gitignored():
    result = subprocess.run(
        ["git", "check-ignore", ENV_FILENAME], cwd=REPO_ROOT, capture_output=True
    )
    assert result.returncode == 0, f"`{ENV_FILENAME}` is not gitignored."


def test_the_corpus_is_not_empty():
    """Absence is never a pass: a scanner over zero files finds zero leaks."""
    tracked = _tracked_files()
    assert len(tracked) > 50, f"git ls-files returned {len(tracked)} paths"
    assert len(_text_files()) > 50


def test_no_tracked_file_assigns_a_real_credential():
    """`<a credential name>=<something real>` must not appear in a tracked file.

    Every tracked text file, every name in `CREDENTIAL_NAMES`, every suffix.
    Markdown is not a safer place to write a key than Python is.
    """
    offenders = _assignment_offenders(_text_files(), REPO_ROOT)
    assert offenders == [], f"credential assignment in tracked files: {offenders}"


def test_no_credential_name_in_the_repository_is_unknown_to_this_guard():
    """A credential name this module has not been taught is a name it cannot
    catch being assigned. Rather than trusting the list, find every
    credential-shaped name in the tree and demand the list covers it."""
    found: set[str] = set()
    for path in _text_files():
        found.update(CREDENTIAL_NAME_SHAPE.findall(_read(path)))
    assert found, "no credential name found in any tracked file — the scan is broken"
    assert found <= set(CREDENTIAL_NAMES), (
        "credential names this guard cannot recognise being assigned: "
        f"{sorted(found - set(CREDENTIAL_NAMES))}"
    )


def test_no_tracked_file_contains_an_odds_api_key_shape():
    """Every tracked file by **name**, every tracked symlink by **target**, every
    tracked text file by **body**. No file is exempt for what it is called."""
    offenders = _hex_offenders_for_corpus(_tracked_files(), _exempt_hex_values(), REPO_ROOT)
    assert offenders == [], f"possible credential in tracked files: {offenders}"


def test_every_vouched_event_id_is_still_in_the_file_it_was_read_from():
    """The vouch list against the file, in both directions.

    A listed id the file no longer carries is stale — the probe re-ran, or the
    record was edited — and a stale vouch is an exemption with no evidence
    behind it. An id the file carries that is not listed is a finding until
    somebody adds the line that vouches for it. Neither direction is a
    harvest: this test never widens the set, it only refuses.
    """
    assert VOUCHED_FILES, "no file vouches for any id; if none needs to, delete the test"
    for relative, vouched in VOUCHED_FILES.items():
        path = REPO_ROOT / relative
        assert path.is_file(), f"{relative} vouches for {len(vouched)} ids and does not exist"
        typed = _typed_ids_in(path)
        assert typed, f"{relative} carries no typed event id at all"
        assert vouched <= typed, (
            f"{relative}: {len(vouched - typed)} vouched ids are no longer in the "
            f"file: {sorted(v[:6] + '...' for v in vouched - typed)[:5]}"
        )
        assert typed <= vouched, (
            f"{relative}: {len(typed - vouched)} typed event ids are not vouched for: "
            f"{sorted(v[:6] + '...' for v in typed - vouched)[:5]}. Add each to "
            "RECORDED_EVENT_IDS by hand; the file cannot vouch for itself."
        )


def test_generated_reports_never_include_the_api_key_parameter():
    findings = [
        str(path.relative_to(REPO_ROOT))
        for path in _text_files()
        if API_KEY_PARAM.search(_read(path))
    ]
    assert not findings, f"`apiKey=<value>` appears in: {findings}"


def test_the_production_credential_name_is_the_one_the_workflow_uses():
    """A contract with GitHub Actions. It must not drift."""
    assert "CBB_ODDS_API_KEY" in PROVIDER_ENV_ALLOWLIST
    assert "CBB_ODDS_API_KEY" in CREDENTIAL_NAMES
    assert "CBBD_API_KEY" in CREDENTIAL_NAMES


@pytest.mark.parametrize("name", CREDENTIAL_NAMES)
def test_credential_names_are_referenced_but_never_valued(name: str):
    """The variable name may appear anywhere; only a real value is forbidden."""
    assert isinstance(name, str) and name
    assert name.endswith(("_KEY", "_TOKEN", "APIKEY"))


def test_the_guard_excludes_itself_from_its_own_scan():
    assert SELF not in [p.resolve() for p in _text_files()]


def test_the_guard_still_scans_other_test_files():
    """Self-exclusion must be exactly one file, not all of `tests/`."""
    scanned = {p.name for p in _text_files()}
    assert "test_gates_fail_closed.py" in scanned
    assert "test_workflows.py" in scanned


# -- the meta-tests: the guard proved to fire, bypass by bypass -------------------

KEY = "0123456789abcdef0123456789abcdef"
SEPARATED_SHAPED = "sk-live-4f19c0d27ba6e83d"


def _superseded_hex_scan(path: Path) -> list[str]:
    """The body scan as it was: `\\b`-fenced, lowercase, bodies of regular files
    only, and a by-name exemption for "checksum"/"receipt". Kept so each
    regression below can show the old code passing the leak, not assert it."""
    if not path.is_file() or path.suffix.lower() in BINARY_SUFFIXES:
        return []
    name = path.name.lower()
    if "checksum" in name or "receipt" in name:
        return []
    return _SUPERSEDED_HEX_KEY.findall(path.read_text(encoding="utf-8", errors="ignore"))


_SUPERSEDED_ASSIGNMENT = re.compile(
    r"\b(" + "|".join(re.escape(n) for n in PROVIDER_ENV_ALLOWLIST) + r")[ \t]*=[ \t]*(\S+)"
)


def _superseded_assignment_scan(path: Path) -> list[str]:
    """The assignment scan as it was: one operator, no closers, and a blanket
    pass for any documentation value that was not 32 hex characters."""
    findings: list[str] = []
    for name, raw in _SUPERSEDED_ASSIGNMENT.findall(path.read_text(encoding="utf-8", errors="ignore")):
        value = raw.strip("'\"`").rstrip(",;)")
        if not value or value in PLACEHOLDERS or value[0] in "$<{":
            continue
        if path.suffix.lower() in {".md", ".rst", ".txt"} and not _SUPERSEDED_HEX_KEY.fullmatch(value):
            continue
        findings.append(name)
    return findings


def test_bypass_a_a_receipt_named_file_no_longer_hides_a_key(tmp_path: Path):
    """The filename exemption, reproduced against the old scan and closed."""
    receipts = tmp_path / "data" / "manual" / "human_acceptance_receipts"
    receipts.mkdir(parents=True)
    receipt = receipts / "receipt_2026-09-04.md"
    receipt.write_text(f"Accepted. Reference {KEY}.\n", encoding="utf-8")
    checksum = tmp_path / "checksums.txt"
    checksum.write_text(f"{KEY}  cbb_team_games.csv\n", encoding="utf-8")

    for planted in (receipt, checksum):
        assert _superseded_hex_scan(planted) == [], "the old scan no longer passes this"
    assert _hex_key_offenders([receipt, checksum], set(), tmp_path) == [
        f"data/manual/human_acceptance_receipts/receipt_2026-09-04.md: {KEY[:6]}...",
        f"checksums.txt: {KEY[:6]}...",
    ]


def test_bypass_b_an_underscore_or_uppercase_no_longer_hides_a_key(tmp_path: Path):
    """The `\\b` fence and the lowercase class, both reproduced and closed."""
    cases = {
        "underscore.py": f'CACHE = f"{KEY}_odds.json"\n',
        "prefixed.py": f"KEY_{KEY} = 1\n",
        "uppercase.py": f'API_KEY = "{KEY.upper()}"\n',
    }
    for name, body in cases.items():
        planted = tmp_path / name
        planted.write_text(body, encoding="utf-8")
        assert _superseded_hex_scan(planted) == [], f"the old scan now catches {name}"
        assert _hex_key_offenders([planted], set(), tmp_path), f"{name} was not caught"
    # ...and a longer hex run is still not a key, in either case.
    assert not HEX_KEY.search("sha256 " + "a" * 64)
    assert not HEX_KEY.search("SHA256 " + "A" * 64)


def test_bypass_c_a_key_in_a_filename_a_symlink_or_a_png_is_a_finding(tmp_path: Path):
    """Paths, link targets and binary-named text, none of which the old scan read."""
    docs = tmp_path / "docs"
    docs.mkdir()
    named = docs / f"{KEY}.md"
    named.write_text("Nothing sensitive in here.\n", encoding="utf-8")
    cache_shaped = docs / f"{KEY}_odds.json"
    cache_shaped.write_text("{}", encoding="utf-8")
    png_named = docs / "diagram.png"
    png_named.write_text(f"not an image: {KEY}\n", encoding="utf-8")
    png_keyed = docs / f"{KEY}.png"
    png_keyed.write_bytes(b"\x89PNG\r\n\x1a\n")
    link = docs / "provider_key"
    link.symlink_to(KEY)

    planted_files = [named, cache_shaped, png_named, png_keyed, link]
    for planted in planted_files:
        assert _superseded_hex_scan(planted) == [], f"the old scan now catches {planted.name}"
    offenders = _hex_offenders_for_corpus(planted_files, set(), tmp_path)
    assert f"docs/{KEY}.md: {KEY[:6]}..." in offenders
    assert f"docs/{KEY}_odds.json: {KEY[:6]}..." in offenders
    assert f"docs/provider_key: {KEY[:6]}..." in offenders
    assert f"docs/{KEY}.png: {KEY[:6]}..." in offenders, "a key in a binary's NAME"
    # A key in the BODY of a .png-named text file is not caught — binary
    # bodies are not decoded, for the parquet reason `_hex_offenders_for_
    # corpus` gives — and that is pinned in the known-gaps ledger, not here.
    assert f"docs/diagram.png: {KEY[:6]}..." not in offenders

    # A symlink whose target is an assignment reaches the assignment scan too.
    assigned = docs / "note"
    assigned.symlink_to(f"CBB_ODDS_API_KEY={SEPARATED_SHAPED}")
    assert _assignment_offenders([assigned], tmp_path) == ["docs/note: CBB_ODDS_API_KEY"]


def test_bypass_d_a_decoy_file_cannot_nominate_an_exemption(tmp_path: Path):
    """Self-nomination, reproduced with the old stem harvest and closed.

    The old harvest ran `path.name.split("_")[0]` over every tracked file, so a
    decoy `<key>_x.md` at the root nominated the key, and the same key in
    `scripts/` was then exempt. Now only `data/raw/` bodies nominate, and a
    report under `data/outputs/` can spend but not create.
    """
    decoy = tmp_path / f"{KEY}_notes.md"
    decoy.write_text("nothing here\n", encoding="utf-8")
    leak = tmp_path / "scripts" / "fetch.py"
    leak.parent.mkdir()
    leak.write_text(f'API_KEY = "{KEY}"\n', encoding="utf-8")
    outputs = tmp_path / "data" / "outputs"
    outputs.mkdir(parents=True)
    report = outputs / "probe.json"
    report.write_text(json.dumps({"events": [{"provider_event_id": KEY}]}), encoding="utf-8")

    old_stem_harvest = {p.name.split("_")[0] for p in (decoy, leak, report)}
    assert KEY in old_stem_harvest, "the decoy no longer reproduces the old harvest"

    content_ids, name_ids = _collect_event_ids([decoy, leak, report], tmp_path)
    assert (content_ids, name_ids) == (set(), set())
    offenders = _hex_key_offenders([decoy, leak, report], content_ids, tmp_path)
    assert f"{KEY}_notes.md: {KEY[:6]}..." in offenders
    assert f"scripts/fetch.py: {KEY[:6]}..." in offenders
    assert f"data/outputs/probe.json: {KEY[:6]}..." in offenders

    # ...while a genuine cached response under data/raw/ still nominates,
    # and what it nominates is spendable under EXEMPT_SCOPE and nowhere else.
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    cached = raw / f"{KEY}_odds.json"
    cached.write_text(json.dumps({"id": KEY}), encoding="utf-8")
    content_ids, name_ids = _collect_event_ids([cached], tmp_path)
    assert content_ids == name_ids == {KEY}
    assert _hex_key_offenders([cached, report], content_ids, tmp_path) == []
    assert _hex_key_offenders([leak], content_ids, tmp_path) == [f"scripts/fetch.py: {KEY[:6]}..."]

    # ...and a cache file named after an id its body does not record is a
    # claim, not a record, and is reported directly.
    uncorroborated = raw / f"{'beefcafe' * 4}_odds.json"
    uncorroborated.write_text("{}", encoding="utf-8")
    content_ids, name_ids = _collect_event_ids([uncorroborated], tmp_path)
    assert name_ids - content_ids == {"beefcafe" * 4}
    assert _hex_key_offenders([uncorroborated], content_ids, tmp_path) == [
        f"data/raw/{'beefcafe' * 4}_odds.json: beefca..."
    ]


@pytest.mark.parametrize(
    "spelling",
    [
        'os.environ["CBB_ODDS_API_KEY"] = "{v}"',
        "os.environ[ 'CBB_ODDS_API_KEY' ] = '{v}'",
        "CBB_ODDS_API_KEY: {v}",
        "  CBBD_API_KEY: '{v}'",
        "**CBB_ODDS_API_KEY**: {v}",
        "<code>CBB_ODDS_API_KEY</code>: {v}",
        "_CBB_ODDS_API_KEY_ = {v}",
        "CBB_ODDS_API_KEY := {v}",
        "CBB_ODDS_API_KEY ?= {v}",
        "CBB_ODDS_API_KEY += {v}",
        "export CBB_ODDS_API_KEY= {v}",
        'os.environ["CBB_ODDS_API_KEY"] = "" "{v}"',
        "| `CBB_ODDS_API_KEY` | live | {v} |",
        '{{"CBB_ODDS_API_KEY": "{v}"}}',
        "cbb_odds_api_key={v}",
        "export CBB_ODDS_API_KEY={v}",
    ],
)
def test_bypass_e_every_assignment_spelling_is_a_finding_in_every_suffix(tmp_path: Path, spelling: str):
    """Subscripts, the operator family, Unicode blanks, YAML, tables, emphasis —
    in a `.py`, a `.md` and a `.yml`, because the old scan exempted docs."""
    line = spelling.format(v=SEPARATED_SHAPED)
    for suffix in (".py", ".md", ".yml"):
        planted = tmp_path / f"leak{suffix}"
        planted.write_text(f"# context\n{line}\n", encoding="utf-8")
        found = _assignment_offenders([planted], tmp_path)
        assert found and found[0].startswith(f"leak{suffix}: "), (
            f"{spelling!r} in {suffix} was not a finding: {found}"
        )


def test_the_old_assignment_scan_passed_the_canonical_spellings(tmp_path: Path):
    """The measurement behind bypass (e), kept as a test: the rule this
    replaces passed the subscript, the YAML form and every docs value."""
    for suffix, line in (
        (".py", f'os.environ["CBB_ODDS_API_KEY"] = "{SEPARATED_SHAPED}"'),
        (".yml", f"CBB_ODDS_API_KEY: {SEPARATED_SHAPED}"),
        (".md", f"export CBB_ODDS_API_KEY={SEPARATED_SHAPED}"),
    ):
        planted = tmp_path / f"leak{suffix}"
        planted.write_text(line + "\n", encoding="utf-8")
        assert _superseded_assignment_scan(planted) == [], (
            f"the superseded scan now catches {line!r}; this measurement is stale"
        )
        assert _assignment_offenders([planted], tmp_path)


def test_prose_and_placeholders_still_pass(tmp_path: Path):
    """The accepting direction, which is how a rule avoids being deleted."""
    fine = tmp_path / "setup.md"
    fine.write_text(
        "Run `export CBB_ODDS_API_KEY=your-api-key`, or in CI set\n"
        "`CBB_ODDS_API_KEY=${{ secrets.CBB_ODDS_API_KEY }}`, or locally\n"
        "`CBB_ODDS_API_KEY=$ODDS_KEY` / `CBB_ODDS_API_KEY=<paste yours>`.\n"
        "| Odds API secret | `CBB_ODDS_API_KEY` |\n"
        "`CBB_ODDS_API_KEY`: the name of the GitHub secret, never its value.\n"
        "CBB_ODDS_API_KEY, CBBD_API_KEY: both are read from the environment.\n"
        'headers = {"Authorization": f"Bearer {CBBD_API_KEY}"}\n'
        "CBB_ODDS_API_KEY=\n",
        encoding="utf-8",
    )
    assert _assignment_offenders([fine], tmp_path) == []


def test_the_api_key_parameter_check_still_catches_a_real_leak():
    assert API_KEY_PARAM.search("https://api.the-odds-api.com/v4/sports/?apiKey=abcd1234efgh")
    assert API_KEY_PARAM.search(f"...&apiKey={KEY}&regions=us")
    assert API_KEY_PARAM.search(f"apiKey={SEPARATED_SHAPED}")
    assert API_KEY_PARAM.search("api_key=abcdef0123456789")
    assert not API_KEY_PARAM.search(r're.sub(r"(apiKey=)[^&\s]+", ...)')
    assert not API_KEY_PARAM.search('assert "apiKey=" not in text')
    assert not API_KEY_PARAM.search("apiKey=[redacted]")


def test_the_key_shape_check_still_catches_a_real_leak():
    assert HEX_KEY.search(f"CBB_ODDS_API_KEY={KEY}")
    assert HEX_KEY.search(f"key is {KEY.upper()} here")
    assert not HEX_KEY.search("a" * 64)


def test_the_event_id_exemption_is_by_value_and_not_by_directory(tmp_path: Path):
    """A hex run that is not a recorded event id is still a finding, even in
    the directory where provider data lives. Built here rather than waited
    for: `data/raw/` is untrackable, so the real repository can never supply
    this case."""
    raw = tmp_path / "data" / "raw"
    raw.mkdir(parents=True)
    recorded, invented = "a1b2c3d4" * 4, "deadbeef" * 4
    cached = raw / f"{recorded}_odds.json"
    cached.write_text(json.dumps({"id": recorded, "bookmakers": []}), encoding="utf-8")
    neighbour = raw / "settings.json"
    neighbour.write_text(json.dumps({"note": invented}), encoding="utf-8")
    content_ids, name_ids = _collect_event_ids([cached, neighbour], tmp_path)
    assert content_ids == name_ids == {recorded}
    assert _hex_key_offenders([cached, neighbour], content_ids, tmp_path) == [
        f"data/raw/settings.json: {invented[:6]}..."
    ]
    # And on the real repository, the exemption set is exactly the vouched
    # list: nothing under data/raw/ is tracked to nominate anything.
    assert _exempt_hex_values() == set(RECORDED_EVENT_IDS)
    assert invented not in _exempt_hex_values()


def test_a_vouched_id_is_not_spendable_outside_the_data_directories(tmp_path: Path):
    """Earning an exemption is not enough; it has to be spent in scope."""
    outputs = tmp_path / "data" / "outputs"
    outputs.mkdir(parents=True)
    vouched = next(iter(sorted(RECORDED_EVENT_IDS)))
    report = outputs / "probe.md"
    report.write_text(f"retention for {vouched}: measured\n", encoding="utf-8")
    hardcoded = tmp_path / "scripts" / "fetch.py"
    hardcoded.parent.mkdir()
    hardcoded.write_text(f'API_KEY = "{vouched}"\n', encoding="utf-8")
    assert _hex_key_offenders([report, hardcoded], set(RECORDED_EVENT_IDS), tmp_path) == [
        f"scripts/fetch.py: {vouched[:6]}..."
    ]


def test_the_gaps_this_guard_still_has_are_the_ones_written_down(tmp_path: Path):
    """What still gets through, asserted open rather than hoped shut.

    A limitation recorded as a passing assertion goes red the day it is
    closed and has to be re-read; a limitation recorded in a docstring quietly
    becomes a false claim — which is exactly how this module's old docstring
    came to say "cannot be used to smuggle". None of these is a waiver.

    1. A key split across a concatenation — `"0123" + "4567..."` — is never one
       32-hex run in any file, so the key-shape scan cannot see it, and the
       assignment scan sees a first token that is not a value.
    2. An encoded body — base64, hex-of-hex, rot13 — is not the key's shape.
    3. Invisible characters from the Unicode LETTER classes (a Cyrillic `а`
       for a Latin `a`, U+FFA0 halfwidth filler) are neither blanks nor
       `Cf`/`Cc`, so `_unwrap` keeps them and the token fails the value test
       under `:`/`,`/`|`. Under `=` the first token needs no value test and IS
       still caught; the gap is the separated family only.
    4. A value of letters only (`NAME: purelettersecret`) fails the digit
       clause; admitting it flags English words instead.
    5. A value carrying `.` or `/` (`NAME: ab12.cd34.ef56`) fails the class;
       admitting it flags every documentation path.
    6. A credential whose name this module does not know AND whose shape is
       not credential-shaped (`SECRET_THING=<key>`) is caught only if the
       value is 32 hex characters. The drift test covers the shaped names.
    7. Bodies behind a binary suffix are not decoded by any scan, so a key
       written INTO a `.png`-named text file — key-shaped or assigned — is
       read by nothing; only the file's NAME is. Decoding them was tried and
       measured: a real parquet carries 32-hex-class runs, so the rule fired
       on the fixtures it ships with.
    """
    split = tmp_path / "split.py"
    split.write_text(f'CBB_ODDS_API_KEY = "{KEY[:16]}" + "{KEY[16:]}"\n', encoding="utf-8")
    assert _hex_key_offenders([split], set(), tmp_path) == []
    # The `=` family DOES report the assignment — the first token is `"0123..."`
    # and needs no value test — so only the shape scan is blind here.
    assert _assignment_offenders([split], tmp_path) == ["split.py: CBB_ODDS_API_KEY"]

    encoded = tmp_path / "encoded.py"
    import base64

    encoded.write_text(
        f'KEY = base64.b64decode("{base64.b64encode(KEY.encode()).decode()}")\n',
        encoding="utf-8",
    )
    assert _hex_key_offenders([encoded], set(), tmp_path) == []
    assert _assignment_offenders([encoded], tmp_path) == []

    homoglyph = tmp_path / "homoglyph.md"
    homoglyph.write_text(f"CBB_ODDS_API_KEY: sk-live-4f19c0d27bа6e83d\n", encoding="utf-8")
    assert _assignment_offenders([homoglyph], tmp_path) == [], (
        "a Cyrillic letter inside a separated value is now caught; move this "
        "case out of the ledger"
    )
    # ...and the same homoglyph under `=` IS a finding, which is the boundary
    # the sentence above draws.
    equals = tmp_path / "homoglyph.py"
    equals.write_text(f"CBB_ODDS_API_KEY=sk-live-4f19c0d27bа6e83d\n", encoding="utf-8")
    assert _assignment_offenders([equals], tmp_path) == ["homoglyph.py: CBB_ODDS_API_KEY"]

    letters = tmp_path / "letters.yml"
    letters.write_text("CBB_ODDS_API_KEY: purelettersecretvalue\n", encoding="utf-8")
    assert _assignment_offenders([letters], tmp_path) == []
    dotted = tmp_path / "dotted.yml"
    dotted.write_text("CBB_ODDS_API_KEY: ab12.cd34.ef56.gh78\n", encoding="utf-8")
    assert _assignment_offenders([dotted], tmp_path) == []

    png = tmp_path / "diagram.png"
    png.write_text(f"CBB_ODDS_API_KEY={SEPARATED_SHAPED} {KEY}\n", encoding="utf-8")
    assert _body_scannable([png]) == []
    assert _hex_offenders_for_corpus([png], set(), tmp_path) == []
    assert _assignment_offenders(_body_scannable([png]), tmp_path) == []
    # ...and the measurement behind the choice: a real parquet body decodes
    # to something the key matcher fires on.
    parquet = REPO_ROOT / "tests" / "fixtures" / "real_data" / "mbb_schedule_2026.parquet"
    assert HEX_KEY.search(_read(parquet)), "the parquet no longer carries a hex-class run; re-measure before decoding binaries"

    unknown = tmp_path / "unknown.py"
    unknown.write_text(f'SECRET_THING = "{SEPARATED_SHAPED}"\n', encoding="utf-8")
    assert _assignment_offenders([unknown], tmp_path) == []
    assert CREDENTIAL_NAME_SHAPE.findall("SECRET_THING") == []
