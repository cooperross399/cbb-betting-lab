#!/usr/bin/env python3
"""Refuse a tree in which an allowlisted market has no receipt a human signed.

    PYTHONPATH=src python scripts/check_allowlist_receipts.py
    PYTHONPATH=src python scripts/check_allowlist_receipts.py --base-ref <sha>

This is the executable half of a sentence three documents already made.
`docs/what_we_can_and_cannot_claim.md`, `data/manual/README.md` and
`src/cbb_betting_lab/reports/what_we_can_claim.py` all said a market is added
to the allowlist *"in a pull request whose policy gate is green"*, and until
`.github/workflows/policy-gate.yml` was written there was no such gate: nothing
under `.github/workflows/` ever opened a receipt. The mechanism existed —
`staging_provider_policy.load()` verifies the receipts and fails the whole
policy closed — but it ran only when the card ran, on a schedule, after the
merge. A pull request carrying an unreceipted allowlist was green.

WHAT THIS SCRIPT ASKS, in the order it asks it.

1. **The card's own question.** `staging_provider_policy.load()` is called on
   the tree as it stands, exactly as the gameday card calls it, and its
   verdict is printed. This is not a re-implementation: a gate that restates
   the rule can drift from the rule, and the point of a gate is to be the same
   door.

2. **Every allowlisted entry, whatever the mode says.** `load()` verifies
   receipts only when the file declares a mode other than `manual_only`, so an
   entry parked in the allowlist of a manual-only file is not checked by it.
   That entry is one word away from live and this script verifies it anyway,
   with `verify_receipt()`, one market at a time. A market whose receipt does
   not stand up is named, with the reason `verify_receipt()` gave, verbatim.
   The missing evidence record and the evidence record that no longer hashes
   to what the receipt cites are two of those reasons — the second is the
   stale-approval case the checksum exists for, and it is the check that
   caught the NHL lab's own withdrawn approval.

3. **What this diff ADDS.** With `--base-ref`, the allowlist in the policy
   file at that commit is compared with the one on disk. Every market this
   change adds must already be backed by a receipt in this same tree — added
   by this pull request or already committed. It is deliberately redundant
   with (2): (2) is what makes the gate red, and this is what makes the job
   summary say *which market this pull request is trying to add*, which is the
   sentence a human reads before deciding whether to merge.

WHAT IT CANNOT BE TALKED OUT OF. There is no `--force`, no allowlist-of-
allowlists and no environment waiver. A receipt whose `signed_by` reads as
Claude in any spelling is refused by
`staging_provider_policy._signer_is_forbidden`, so the one thing this
repository could always have produced by itself — a JSON file saying the
market is fine, signed with its own name — is the one thing that can never
satisfy this gate. This script writes nothing: not the policy, not a receipt,
not the evidence. There is still no `grant()`.

WHAT IT CANNOT DO. It cannot tell a real signature from a forged one. Nothing
here is cryptographic and no identity is checked: `signed_by` is a string in a
JSON file, and all this gate can say about it is that it is not one of the
spellings of Claude it knows to refuse. Whether the person named actually
signed is decided by the human reviewing the pull request, and the summary
this script prints says so in those words rather than claiming an enforcement
it does not have.

EXIT STATUS. `0` when every allowlisted market is receipted, `1` when one is
not, and `2` when the check could not be run at all — an unreadable base ref,
a manual directory that is not there, a policy file that exists and cannot be
parsed. `2` is not a pass: "I could not check" and "there was nothing to
check" must never take the same branch. That last case is the one this script
got wrong until 2026-09-05: `load()` answers a corrupt or truncated policy
file with an empty policy, which is the correct fail-closed answer for the
CARD and the wrong REPORT for a gate, because it printed the same sentence as
a repository that allowlists nothing. An absent policy file, and a policy file
that parses and allowlists nothing, remain the ordinary green case.

A policy file that PARSES and whose ALLOWLIST ENTRIES cannot be read is the
same broken gate wearing valid JSON, and is `2` as well: an allowlist of bare
strings, an entry with no `market`, a directory where the policy file belongs,
a symlink pointing at nothing. `load()` keeps only the entries it can read as
objects that name a market, so each of those quietly becomes an allowlist of
nothing — which is the exact shape of the defect above, one layer in.

ONE VERDICT, WRITTEN FROM THE EXIT STATUS. The summary ends with exactly one
`POLICY GATE VERDICT:` line, built by `verdict_line()` out of the status
`main()` is about to return, and `main()` scrubs that marker from every other
line before printing. Market names, receipt notes and `verify_receipt()`
reasons are text from files this gate does not control; before that scrub, a
market could be NAMED with the sentence a green run prints and a reviewer
reading a red run's summary would find a green verdict inside it.

The scrub matches the LETTERS of the wording, not the wording — the same
shape `staging_provider_policy._signer_is_forbidden` uses to refuse
`C.L.A.U.D.E.` — because the first version matched literal fragments and
three respellings walked straight through it: `POLICY-GATE-VERDICT`, the same
words spaced out, and a planted verdict carrying a `|`, which `_plain()` had
itself escaped to a backslash and a pipe a moment earlier, so that the
literal no longer matched. `_plain()` folds everything outside printable
ASCII to a space for the same reason, since a homoglyph breaks a letter run
without breaking what a human reads.

The scrub then MANUFACTURED the marker for one more round. One pass over the
patterns in a fixed order rewrote a market named `POLICY GATE: <the green
sentence>` into `POLICY GATE: [verdict text removed]`, whose letters spell
the marker — a line that was not in the file it read and was not caught by
either written-down gap, because it was the scrub's own output. So the
guarantee is a POST-CONDITION now: the passes repeat until the text stops
changing, and a line that still matches when they run out is replaced whole.
What `without_a_second_verdict` returns matches none of the patterns it
scrubs with, whatever it was handed. What it still cannot SEE — a
misspelling, a paraphrase — is written down in its own docstring and held
open by a test, rather than described as closed; neither can spell the
marker, which is what makes them survivable.

AND EVERY OFF-DISK STRING GOES THROUGH `_plain()` FIRST. The `mode` field is
one: `policy.declared_mode` is the string out of the policy file and
`policy.mode` is what `load()` made of it, and both were interpolated raw —
the only strings in `report()` that skipped `_plain()`. So one line of a JSON
file wrote a newline (a whole markdown line of its own) and a `|` (a whole
column) into a red run's summary, in a bullet shaped like this gate's own
finding. They are printed like every other string this gate did not write.

AND ONLY THIS SCRIPT WRITES THAT SUMMARY. `$GITHUB_STEP_SUMMARY` is a
per-STEP file whose contents are concatenated into one job summary, so a
sibling step in the gate's job that echoed the green sentence into its own
summary put a green verdict in front of the reviewer of a red run, and no
scrub here could reach it: this script never sees that text. It is also a
plain environment variable, which a job-level or workflow-level `env:`
overrides for every step at once — that one does not add a verdict, it takes
the only one there is somewhere nobody reads. The rule
`check_only_the_receipt_checker_writes_the_gates_job_summary` in
`tests/test_workflows.py` is the other half: `GITHUB_STEP_SUMMARY` is named
NOWHERE in that workflow — not in a step, not in a job-level `env:`, not in a
workflow-level one — exactly one step runs this checker, and every other step
in the job is one of the two actions that check out the tree and install the
interpreter. What that rule does not reach is written into its own docstring:
what those two actions do with the same write handle, and a `run:` block in
this checker's own step that assembles the variable name instead of spelling
it.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from cbb_betting_lab import staging_provider_policy as SPP
from cbb_betting_lab.competitions import CBB


#: The policy file, relative to the repository root. The gate reads the base
#: commit's copy of exactly this path.
POLICY_RELATIVE = f"data/manual/{SPP.POLICY_FILENAME}"

OK, RED, BROKEN = 0, 1, 2

#: The words the run's ANSWER is spelled with, and the only place any of them
#: are spelled. `verdict_line()` builds one line out of the exit status,
#: `main()` calls it exactly once, and `main()` scrubs `VERDICT_MARKER` out of
#: every other line before printing — so a run that exits non-zero cannot
#: contain the sentence a green run prints, whatever a policy file's market
#: name or `mode` field, a receipt note or a `verify_receipt()` reason tries
#: to plant in the summary. It can still contain a PARAPHRASE of it, which is
#: the gap `without_a_second_verdict` writes down and a test holds open. That
#: was
#: a real hole: the verdict used to be prose written on the branch that
#: produced it, and prose in a job summary is text a reader can be given twice.
VERDICT_MARKER = "POLICY GATE VERDICT"
VERDICTS = {
    OK: (
        "green — no allowlisted market in this tree lacks a receipt this gate "
        "accepted"
    ),
    RED: (
        "red — an allowlisted market in this tree has no receipt this gate "
        "accepted"
    ),
    BROKEN: (
        "broken — this gate did not run and checked no allowlist at all, which "
        "is not evidence that any market is receipted"
    ),
}

#: Said on BOTH verdicts, from one place, because an overclaim beside a green
#: tick is the more dangerous one.
SIGNATURE_NOTE = (
    "What this gate checks about a signature, exactly: that `signed_by` is not "
    "one of the spellings of Claude it knows to refuse — any value whose "
    "letters spell `claude`, whatever the case and whatever the punctuation "
    "between them. That is the whole of it. Nothing here is cryptographic and "
    "no identity is verified, so this gate cannot tell a real signature from a "
    "forged one and does not claim to: whether the person named actually "
    "signed a receipt is decided by the human reviewing this pull request, "
    "not here."
)


def verdict_line(status: int) -> str:
    """The one line that says how the run ended, built from the exit status.

    Not from the branch that ran, and not from anything read off disk: the
    caller passes the status it is about to return. And it is the only line
    of a run's summary that spells `VERDICT_MARKER` — not because nothing
    else tries, but because every other line goes through
    `without_a_second_verdict`, which checks its OWN OUTPUT against the
    patterns and takes a line whole rather than return one that still
    matches.
    """
    return f"**{VERDICT_MARKER}: {VERDICTS[status]}.**"


#: What a redacted verdict span is replaced with.
#:
#: This comment used to read "it spells none of the fragments below, so a
#: scrub can never manufacture a fresh match", and the second half was false.
#: `REDACTION` spells none of them ON ITS OWN; joined to the letters already
#: beside it in the line, it does. A market named `POLICY GATE: <the green
#: sentence>` matches no marker pattern — `green` puts letters between the
#: `GATE` and the `VERDICT` — so the marker pattern passes over it, and then
#: the green-sentence pattern rewrites it to `POLICY GATE: [verdict text
#: removed]`, whose letters spell `POLICYGATEVERDICT`. One pass in a fixed
#: order manufactured the marker it had just been asked to remove. What
#: `without_a_second_verdict` promises now is a property of its RESULT, not
#: of this string: it re-scrubs to a fixed point and, if the result still
#: matches any pattern, replaces the line whole.
REDACTION = "[verdict text removed]"

#: How many times the scrub is re-run before it gives up on converging.
#: A substitution cannot promise convergence by itself — `REDACTION` is
#: longer than the shortest span it replaces, so a pass can make a line grow
#: — and the fixed point is therefore a bounded search with a fallback rather
#: than a loop that trusts itself to end.
SCRUB_PASSES = 8

#: What a line becomes when the scrub could not reach a fixed point inside
#: `SCRUB_PASSES`. It takes the whole line, findings and all: this gate's
#: guarantee is about what its summary CANNOT say, and a line of a policy
#: file's text is never worth more than that. Checked against every pattern
#: at import, so it can never be the thing that spells the marker.
WHOLE_LINE_REDACTION = "[a line of this run's own findings was removed whole]"


def _letters(text: str) -> str:
    """`text` with everything that is not a letter dropped."""
    return "".join(character for character in text if character.isalpha())


def _spelled_out(fragment: str) -> re.Pattern[str]:
    """A pattern matching any span whose LETTERS spell `fragment`'s letters.

    The shape `staging_provider_policy._signer_is_forbidden` already uses to
    refuse `C.L.A.U.D.E.`: the letters in order, any case, any run of
    non-letters between them. A scrub that matched the literal string was
    defeated by every respelling of the same sentence — `POLICY-GATE-VERDICT`,
    `P O L I C Y  G A T E  V E R D I C T`, and, worst of the three, a planted
    verdict carrying a `|`, because `_plain()` escapes that to `\\|` and the
    literal no longer matched the text this script had just made.
    """
    letters = _letters(fragment)
    assert letters, "a verdict fragment with no letters cannot be scrubbed"
    return re.compile("[^A-Za-z]*".join(re.escape(c) for c in letters), re.IGNORECASE)


#: The scrub, compiled once: the marker and every verdict sentence, each
#: matched by the letters that spell it.
VERDICT_PATTERNS = tuple(
    _spelled_out(fragment) for fragment in (VERDICT_MARKER, *VERDICTS.values())
)

# The two strings the scrub writes may not themselves be scrubbable, or the
# fixed point below would never be reached and every line would be taken
# whole. Asserted here rather than read off the page, because both are one
# careless word away from spelling the marker.
assert not any(pattern.search(REDACTION) for pattern in VERDICT_PATTERNS), REDACTION
assert not any(
    pattern.search(WHOLE_LINE_REDACTION) for pattern in VERDICT_PATTERNS
), WHOLE_LINE_REDACTION


def without_a_second_verdict(line: str) -> str:
    """`line` with every verdict word this script can print taken out of it.

    Applied to EXPLANATION lines only, so that the one verdict a run prints
    is the one `verdict_line()` built from its exit status. Without this the
    green sentence is plantable: a market NAMED with it, or a receipt note
    carrying it, is copied into the table of a red run, and the reader sees
    a red gate whose summary says every market is receipted.

    WHAT IT GUARANTEES, and the only thing it guarantees: the string it
    RETURNS matches none of `VERDICT_PATTERNS`. Not "the input was clean" and
    not "the wording was found" — the output is checked, and a line that
    still matches after `SCRUB_PASSES` is replaced by
    `WHOLE_LINE_REDACTION`, which is checked against the same patterns at
    import. So no line this function returns can spell the marker, whatever
    was fed to it.

    That guarantee had to be written as a POST-CONDITION because the earlier
    version — one pass over `VERDICT_PATTERNS` in a fixed order — could
    manufacture the marker it existed to remove. A market named `POLICY
    GATE: <the green sentence>` matches no marker pattern, because `green`
    puts letters between `GATE` and `VERDICT`; the marker pattern therefore
    passes over it untouched, and the green-sentence pattern that runs next
    rewrites the tail to `REDACTION`, leaving `POLICY GATE: [verdict text
    removed]` — which spells `POLICYGATEVERDICT`. Neither documented gap
    covered it: it is not a misspelling and not a paraphrase, it is the
    scrub's own output. Now the passes repeat until the text stops changing
    (`POLICY GATE: [verdict` is a marker match on the second pass and goes
    too), and the post-condition catches anything that does not settle.

    WHAT THIS STILL LETS THROUGH, written down rather than claimed shut, and
    held open by `test_the_gaps_the_verdict_scrub_still_has_are_the_ones_
    written_down` in `tests/test_workflows.py` so that the day one closes,
    the sentence has to be re-read rather than quietly becoming false:

    1. **A misspelling.** The scrub matches the letters of the marker, so
       `POLICY GATE VERDCT` and `POLICY GATE VERD1CT` spell something else
       and survive. They no longer match the marker a reader searches for
       either, which is the whole of the mitigation.
    2. **A paraphrase.** `_plain()` output saying "this gate found every
       market receipted" carries none of the pinned wording and is not
       touched. The scrub removes THE SENTENCES THIS SCRIPT PRINTS, never
       everything that could be read as approval.

    Both are the same limit: this is a scrub of a known wording, not a
    classifier of meaning. Neither can spell the marker, which is why the
    post-condition above is the assertion the summary tests are allowed to
    rest on.
    """
    text = line
    for _ in range(SCRUB_PASSES):
        once = text
        for pattern in VERDICT_PATTERNS:
            once = pattern.sub(REDACTION, once)
        if once == text:
            break
        text = once
    if any(pattern.search(text) for pattern in VERDICT_PATTERNS):
        return WHOLE_LINE_REDACTION
    return text


def _plain(value: object, limit: int = 160) -> str:
    """A value read off disk, made safe to put in one markdown table cell.

    Market names, receipt filenames and `verify_receipt()` reasons are text
    from files this gate does not control. A newline in one of them writes a
    whole line of the job summary; a `|` writes a whole column. Neither may
    be a way to write a sentence a reviewer reads as this gate's finding.

    WHAT IT RETURNS, asserted below rather than assumed: a string that is
    printable ASCII, holds no newline, and is at most `max(limit, 7)`
    characters long. The floor of 7 is the bound and not slack in it: the two
    fixed strings this function can return are returned whatever `limit`
    says, and both are longer than a small one — `_plain('abcdefghij',
    limit=2)` is the three-character `'...'` and `_plain('', limit=2)` is the
    seven-character `'(empty)'`. Every call in this file passes a `limit` of
    80 or more, and there `max(limit, 7)` is `limit`, which is the bound this
    sentence used to state of every call. That is a property of the OUTPUT.
    It is not a claim about the
    input, and the sentence here used to make one — "every string this gate
    legitimately prints is ASCII — the market names, the receipt filenames
    and the reasons `staging_provider_policy` returns". Not one of those
    three is under this gate's control. A market name is whatever somebody
    typed into a JSON file, and a name legitimately spelled with a non-ASCII
    letter is a thing that can exist. What is true is that this gate CHOOSES
    to render only ASCII and pays for it: such a name is shown with spaces
    where those characters were, and a reviewer reading the summary sees the
    gaps rather than the name.

    That cost is accepted because a homoglyph is the one respelling
    `without_a_second_verdict` cannot see: a Cyrillic `\u041e` is a letter,
    so it breaks the letter run the scrub matches while reading to a human as
    the `O` in `POLICY`. Folding it to a space leaves the marker unspellable.
    The ellipsis this function truncated with was itself outside ASCII, so
    its own output broke the rule its first sentence stated; it is `...` now,
    and the assertion below is what stops that from quietly coming back.
    """
    text = "".join(
        character if (character.isascii() and character.isprintable()) else " "
        for character in str(value)
    )
    text = text.replace("|", "\\|").replace("`", "'").strip()
    if len(text) > limit:
        text = text[: max(limit - 3, 0)] + "..."
    text = text or "(empty)"
    assert text.isascii() and text.isprintable() and len(text) <= max(limit, 7), (
        f"_plain() returned {text!r}, which is not the one-line printable ASCII "
        "its callers paste into a markdown table cell"
    )
    return text


def _markets_in(payload: object) -> set[str]:
    """The market names in a parsed policy document, or an empty set.

    Anything unparseable reads as an EMPTY allowlist, which makes every market
    on disk count as added by this change. That is the strict direction: a
    base commit this script cannot read must never shrink what it compares.
    """
    if not isinstance(payload, dict):
        return set()
    found = set()
    for item in payload.get("allowlist", []) or []:
        if isinstance(item, dict) and item.get("market"):
            found.add(str(item["market"]))
    return found


def unreadable_policy(path: Path) -> str:
    """Why the policy file on disk cannot be read as a policy, or `""`.

    An ABSENT file is not unreadable. A repository with no policy file
    allowlists nothing, which is this lab's shipping state and a green run.
    A file that is THERE and cannot be parsed is a gate that did not run:
    `staging_provider_policy.load()` answers it with an empty policy — right
    for the card, which must fail closed, and wrong for this report, which
    would otherwise print "no market is allowlisted" over a policy file
    nobody could read.

    "Cannot be parsed" is not only "is not JSON". A policy file whose
    ALLOWLIST ENTRIES cannot be read is the same broken gate wearing valid
    JSON: `load()` and `_markets_in()` both keep only the entries that are
    objects carrying a `market`, so an allowlist of bare strings, or an entry
    with no `market` key, silently becomes an allowlist of nothing and takes
    the green "nothing to check" branch. Every one of those is exit 2 here.
    So is a DIRECTORY where the policy file belongs, and a symlink pointing
    at nothing: both are a path that exists and holds no policy anyone read.
    """
    if path.is_symlink() and not path.exists():
        return (
            f"`{POLICY_RELATIVE}` is a symlink that points at nothing, so there "
            "is a policy file in this tree that no allowlist could be read from."
        )
    if not path.exists():
        return ""
    if not path.is_file():
        return (
            f"`{POLICY_RELATIVE}` exists and is not a regular file (it is a "
            f"{'directory' if path.is_dir() else 'special file'}), so no "
            "allowlist was read from it. A directory where the policy file "
            "belongs is a gate that could not run, not a repository that "
            "allowlists nothing."
        )
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return (
            f"`{POLICY_RELATIVE}` exists and could not be read "
            f"({exc.__class__.__name__}: {_plain(exc, limit=200)})."
        )
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        return (
            f"`{POLICY_RELATIVE}` exists and is not parseable JSON "
            f"(line {exc.lineno}, column {exc.colno}: {exc.msg}). A corrupt or "
            "truncated policy file is a file whose allowlist nobody read."
        )
    if not isinstance(payload, dict):
        return (
            f"`{POLICY_RELATIVE}` exists and parses to a "
            f"{type(payload).__name__}, not a JSON object, so it declares no "
            "mode and no allowlist that could be checked."
        )
    listed = payload.get("allowlist", [])
    if listed is not None and not isinstance(listed, list):
        return (
            f"`{POLICY_RELATIVE}` exists and its `allowlist` is a "
            f"{type(listed).__name__} rather than a list, so every entry in it "
            "would be read as no entry at all."
        )
    for index, item in enumerate(listed or []):
        if not isinstance(item, dict):
            return (
                f"`{POLICY_RELATIVE}` exists and entry {index} of its "
                f"`allowlist` is a {type(item).__name__}, not an object. "
                "`load()` keeps only the entries it can read as objects, so "
                "this entry would vanish and the gate would report an "
                "allowlist nobody wrote."
            )
        market = item.get("market")
        if not isinstance(market, str) or not market.strip():
            return (
                f"`{POLICY_RELATIVE}` exists and entry {index} of its "
                f"`allowlist` carries `market: {_plain(repr(market), limit=80)}`, "
                "which names no "
                "market. `load()` keeps only the entries that name one, so "
                "this entry would be read as no entry at all and the gate "
                "would check an allowlist shorter than the file's."
            )
    return ""


def base_allowlist(root: Path, ref: str) -> tuple[set[str], str]:
    """The markets allowlisted at `ref`, and one line saying where they came
    from. Raises `RuntimeError` when the ref itself cannot be read."""
    resolved = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", f"{ref}^{{commit}}"],
        capture_output=True,
        text=True,
    )
    if resolved.returncode != 0:
        raise RuntimeError(
            f"cannot resolve the base commit `{ref}` in {root}: "
            f"{resolved.stderr.strip() or 'git said nothing'}"
        )
    shown = subprocess.run(
        ["git", "-C", str(root), "show", f"{ref}:{POLICY_RELATIVE}"],
        capture_output=True,
        text=True,
    )
    if shown.returncode != 0:
        return set(), (
            f"`{POLICY_RELATIVE}` does not exist at the base commit `{ref}`, so "
            "every market allowlisted here is one this change adds."
        )
    try:
        payload = json.loads(shown.stdout)
    except json.JSONDecodeError:
        return set(), (
            f"`{POLICY_RELATIVE}` at the base commit `{ref}` is not readable JSON, "
            "so every market allowlisted here is treated as one this change adds."
        )
    markets = _markets_in(payload)
    listed = ", ".join(f"`{m}`" for m in sorted(markets)) or "no market"
    return markets, f"The base commit `{ref}` allowlisted {listed}."


def report(root: Path, base_ref: str) -> tuple[int, list[str]]:
    """The status, and the lines that EXPLAIN it, in markdown.

    These lines are the finding and never the verdict. The verdict is one
    line, `verdict_line(status)`, and `main()` is the only caller that writes
    it — out of the status this function returns, after scrubbing
    `VERDICT_MARKER` from everything here. A branch cannot print a verdict
    other than the one it returns, because no branch here prints a verdict.
    """
    manual = root / "data" / "manual"
    lines = ["## Policy gate: human acceptance receipts", ""]
    if not manual.is_dir():
        lines.append(
            f"**Broken gate.** There is no `{_plain(manual, limit=400)}` to read. "
            "This run checked nothing; it is not evidence that the allowlist is "
            "receipted."
        )
        return BROKEN, lines

    broken = unreadable_policy(SPP.policy_path(manual))
    if broken:
        lines.append(f"**Broken gate.** {_plain(broken, limit=600)}")
        lines.append("")
        lines.append(
            "This run checked NO allowlist. `load()` reads a policy file it "
            "cannot parse as manual-only with an empty allowlist — the right "
            "answer for the card, which must fail closed and read nothing from "
            "staging, and the wrong report from a gate, because it is also what "
            "a repository that allowlists nothing looks like. The two are not "
            "the same and this run is the first, not the second: it is not "
            "evidence that every allowlisted market is receipted."
        )
        return BROKEN, lines

    policy = SPP.load(manual)
    lines.append(f"- Policy file: `{POLICY_RELATIVE}`")
    # `declared_mode` is the `mode` STRING OUT OF THE POLICY FILE, and `mode`
    # is what `load()` made of it. Both used to be interpolated raw, and they
    # were the only off-disk strings in this function that skipped `_plain()`
    # — so a one-line edit to the policy file wrote a newline and a `|` into
    # this summary, forging a markdown column or a whole extra bullet that
    # reads as this gate's own finding. They go through `_plain()` like every
    # other string this gate did not write.
    lines.append(f"- Mode declared in the file: `{_plain(policy.declared_mode or 'none')}`")
    lines.append(f"- Mode in force after `load()`: `{_plain(policy.mode)}`")
    lines.append(f"- Receipts read from: `data/manual/{SPP.RECEIPTS_DIRNAME}/*.json`")
    lines.append("")
    lines.append(f"The card's own reading: {_plain(policy.summary_line(CBB), limit=400)}")
    lines.append("")

    markets = sorted(policy.allowlist)
    if not markets:
        lines.append(
            "**No market is allowlisted.** There is nothing for a receipt to "
            "stand behind, and that is the state this lab ships in. This is not "
            "a judgement that any market lacks value; it is the absence of an "
            "approval."
        )
    else:
        lines.append(f"### The {len(markets)} allowlisted market(s), one at a time")
        lines.append("")
        lines.append("| Market | Receipt | Verdict |")
        lines.append("|:---|:---|:---|")

    failures: dict[str, str] = {}
    for market in markets:
        receipt, reason = SPP.verify_receipt(policy.allowlist[market], manual)
        if receipt is None:
            failures[market] = reason
            lines.append(f"| `{_plain(market)}` | — | **RED** — lacks {_plain(reason)} |")
        else:
            lines.append(f"| `{_plain(market)}` | `{_plain(Path(receipt).name)}` | green |")
    lines.append("")

    added_note = ""
    added: set[str] = set()
    if base_ref:
        try:
            base_markets, added_note = base_allowlist(root, base_ref)
        except RuntimeError as exc:
            lines.append(
                f"**Broken gate.** {_plain(exc, limit=400)}. This run did not "
                "compare the allowlist against the base commit; it is not "
                "evidence that nothing was added."
            )
            return BROKEN, lines
        added = set(markets) - base_markets
        lines.append("### What this change adds")
        lines.append("")
        lines.append(f"- {_plain(added_note, limit=400)}")
        if added:
            lines.append(
                "- This change ADDS "
                + ", ".join(f"`{_plain(m)}`" for m in sorted(added))
                + " to the allowlist."
            )
        else:
            lines.append("- This change adds no market to the allowlist.")
        lines.append("")
    else:
        lines.append(
            "### What this change adds\n\n- No base commit was given, so this run "
            "did not compare the allowlist against one. Every allowlisted market "
            "above was still verified receipt by receipt.\n"
        )

    if failures:
        lines.append("### What each allowlisted market lacked")
        lines.append("")
        for market in sorted(failures):
            note = " — and this change is what adds it" if market in added else ""
            lines.append(f"- **`{_plain(market)}`** lacks {_plain(failures[market])}{note}.")
        lines.append("")
        lines.append(
            "A market reaches the card only behind a receipt that names the "
            "market, cites an evidence record that exists and still hashes to "
            "the value the receipt was signed against, carries a non-empty "
            "`signed_by`, and carries a date."
        )
        lines.append("")
        lines.append(SIGNATURE_NOTE)
        return RED, lines

    lines.append("### What was checked")
    lines.append("")
    if markets:
        lines.append(
            f"- Each of the {len(markets)} allowlisted market(s) was matched to a "
            "receipt naming it, citing an evidence record that still hashes to "
            "the cited value, carrying a `signed_by` that is not one of the "
            "spellings of Claude this gate refuses, and dated."
        )
    else:
        lines.append("- Nothing is allowlisted, so there was nothing to receipt.")
    lines.append("")
    lines.append(SIGNATURE_NOTE)
    return OK, lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="The policy gate's receipt check.")
    parser.add_argument(
        "--repo-root",
        default="",
        help="The checkout to read. Defaults to the working directory.",
    )
    parser.add_argument(
        "--base-ref",
        default="",
        help=(
            "A commit whose policy file this one is compared against, so the "
            "summary can name the markets this change adds. Empty means no "
            "comparison; every allowlisted market is still verified."
        ),
    )
    args = parser.parse_args(argv)

    root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd().resolve()
    status, lines = report(root, args.base_ref.strip())
    # The verdict is written HERE, once, out of the status, and nothing else
    # printed by this run may spell the marker it is written with. A market
    # name, a receipt note or a `verify_receipt()` reason is text from a file
    # this gate does not control, and a reader who finds two verdicts in one
    # summary has been handed the wrong one.
    explained = [without_a_second_verdict(line) for line in lines]
    body = (
        "\n".join([*explained, "", "### Verdict", "", verdict_line(status)]).rstrip()
        + "\n"
    )

    summary = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(body)
    print(body)

    if status == BROKEN:
        print(
            "::error::The policy gate could not run. That is a broken gate, NOT "
            "evidence that every allowlisted market is receipted.",
            file=sys.stderr,
        )
    elif status == RED:
        print(
            "::error::An allowlisted market has no valid human acceptance receipt. "
            "The card would load this policy as manual-only; this pull request may "
            "not be merged until a receipt Cooper signed stands behind every "
            "allowlisted market.",
            file=sys.stderr,
        )
    return status


if __name__ == "__main__":
    raise SystemExit(main())
