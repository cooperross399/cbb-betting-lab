"""What the card is allowed to read, and the one signature that changes it.

Nothing staged reaches the card. The card reads only markets a **reviewed
policy** allowlists, and a market enters that policy only with a human
acceptance receipt Cooper has signed. This module is the door.

## The one direction the machine may move this file

**Claude may withdraw an allowlist. Claude may never grant one.**

That is the NHL lab's precedent and it holds here. Its 2026-08-27 approval was
withdrawn on 2026-08-29 because the evidence it cited had moved underneath it —
the receipt was signed against +1.4% over 4,830 bets and the full population
said −1.6% over 73,918. **The gate caught it on its own**, because the receipt's
evidence checksums stopped matching, which is exactly what that check is for.
Withdrawal can only ever reduce what the card may do, so it is safe to automate;
granting cannot, so it never is.

`withdraw()` exists and is callable by an automated run. `grant()` does not
exist. Adding a market is editing `data/manual/staging_provider_policy.json`
with a receipt beside it, in a pull request whose **`Policy Gate`** check is
green, merged by Cooper.

`Policy Gate` is `.github/workflows/policy-gate.yml`, and until 2026-09-05 this
paragraph named a gate that did not exist: nothing under `.github/workflows/`
opened a receipt, so a pull request carrying an unreceipted allowlist was
green and this sentence was true of nothing. The check now runs on every pull
request — no `paths:` filter, because a filtered check is not reported on the
pull requests it filters out — and runs
`scripts/check_allowlist_receipts.py`, which calls :func:`load` exactly as the
card calls it and then :func:`verify_receipt` on every allowlisted entry one at
a time, including the entries a `manual_only` file leaves :func:`load` itself
skipping. It names, in the job summary, every market it checked, the receipt
behind it or what that market lacked, and which markets the change ADDS. It is
red until a receipt stands behind every allowlisted market, and it exits `2`
rather than `0` on a policy file that exists and cannot be read, because
"nothing to check" and "I could not check" must not share a branch. That
covers more than a file that is not JSON: an allowlist that is not a list, an
entry that is a bare string or names no market, a directory where the file
belongs and a symlink into nothing each turn into an allowlist of nothing in
:func:`load`, and a gate reporting on an allowlist nobody read has checked
nothing. The job summary ends with one verdict line built from the exit
status, with the verdict wording removed from every other line first, so a
red run cannot contain the sentence a green run prints — market names,
receipt notes and the policy file's own `mode` field are text from files the
gate does not control, and the last of those was printed raw until
2026-09-05, so one line of JSON wrote a newline and a `|` into the summary as
a markdown line and a markdown column of its own. That removal matches the
LETTERS of the wording rather than the wording, the way
:func:`_signer_is_forbidden` refuses `C.L.A.U.D.E.`, because a literal match
was walked past by `POLICY-GATE-VERDICT` and by a verdict carrying a `|`; it
then repeats to a fixed point and checks its own output, because one pass in
a fixed order rewrote `POLICY GATE: <the green sentence>` into `POLICY GATE:
[verdict text removed]` and so wrote the marker it had been asked to remove.
What it still cannot see — a misspelling, a paraphrase — is written into the
scrub's own docstring and held open by a test rather than described as
closed; neither spells the marker. The checker is also the ONLY writer of
that summary: the job summary is a per-step file GitHub concatenates, so a
sibling step could otherwise put a green verdict above the real one in a red
run, and `GITHUB_STEP_SUMMARY` is a plain environment variable, so a
job-level or workflow-level `env:` could send the checker's own verdict to a
file nobody opens. It is named nowhere in the workflow — not in a step, not
in a job `env:`, not in a workflow `env:`. What that rule does not reach is
written into its own docstring: what `actions/checkout` and
`actions/setup-python` do with the same write handle, and a `run:` block in
the checker's own step that assembles the variable name rather than spelling
it. No condition stands between a pull request
and that verdict: the job carries no `if:`, no `needs:` and no `strategy:`,
because GitHub reports a check skipped by a condition as a success. Exactly
one job in the whole workflow corpus carries the name that publishes this
check, since a context is a job `name:` and nothing scopes it to a file.

What it checks about the signature is what :func:`_signer_is_forbidden` and
:func:`_signer_is_accepted` check between them: that `signed_by` is not one of
the spellings of Claude it refuses, AND that its letters are one of
:data:`ACCEPTED_SIGNERS`. Until 2026-09-26 only the first ran, which is a deny
list of one name, so every string that did not spell `claude` was a signature:
`Anonymous Bot` and `fixture-signer` each loaded a market live in a
measurement. Nothing here is cryptographic and no identity is verified, so
whether the signer is really Cooper is still the judgement of whoever reviews
the pull request rather than a thing this gate can enforce — what the second
list buys is that the forgery has to carry HIS name, not any name.

It is not a context branch protection requires: measured 2026-09-05, main
requires `Tests` and nothing else, so a red `Policy Gate` is a fact in the pull
request rather than a hold on the merge button. Adding the context is a
repository setting and Cooper's to make.

## The receipt is checked, not named

Until 2026-09-05 `allows()` read `mode != manual_only and market in allowlist`,
and nothing anywhere opened `data/manual/human_acceptance_receipts/`. The
brief's single human stop was a JSON field a script could have written. Now
:func:`load` requires, for **every** allowlisted market, a receipt file under
`<manual_dir>/human_acceptance_receipts/*.json` that

* names that market (`"market"`),
* cites an evidence record (`"evidence": {"path": ..., "sha256": ...}`, or
  `"evidence_path"` / `"evidence_sha256"`) — a relative path is read against
  the repository root, two directories above `manual_dir` — where the record
  **exists on disk and hashes to that value**,
* carries a non-empty `"signed_by"` that is not Claude in any spelling or case
  **and is one of** :data:`ACCEPTED_SIGNERS`,
* and a `"signed_on"` date (`YYYY-MM-DD`).

The entry must name a `receipt_id`, and the receipt must carry the same id (as
its `"receipt_id"` field or its file stem). The entry must also record an
`evidence_checksum`, and the receipt must cite that same digest. `superseded/`
is not read: a withdrawn receipt is a record, not a permission. Any allowlisted
market lacking a valid receipt makes the **whole** policy load as manual-only —
fail closed, not market-by-market — with the reasons kept on the object and
printed by `summary_line()`, so the card says which market lacked what. The
evidence hash check is the NHL lab's own catch, made mandatory: when the
evidence moves underneath a receipt, the checksum stops matching and the door
shuts on its own.

## What 2026-09-26 closed, each measured before it was closed

Five of these were reachable by anything that can write a file in this
checkout, which is the threat model: an agent with code execution here must not
be able to stand in for Cooper. "Only forgeable by something that can run code
here" is the attack, not a mitigation.

* **The `receipt_id` was optional.** `if entry.receipt_id:` meant an entry that
  omitted it bound to whichever receipt happened to name its market. A policy
  whose only entry read `{"market": "spread"}` loaded live behind a file called
  `whatever.json`.
* **The entry's `evidence_checksum` was optional, and every live one was
  empty.** :func:`_examine_receipt` reads an empty one as "not recorded" and
  declines to judge it — honest for a function asked about one receipt, and its
  docstring says the empty case is "what the caller's own reporting is for".
  The caller's reporting was silence. :func:`verify_receipt` now refuses the
  entry, because not-recorded must not read as checked.
* **Two receipts could claim one approval, and the earlier FILENAME won.**
  :func:`verify_receipt` returned the first file that verified in sorted order,
  so `aaa-forged.json` beat `r1.json`, the genuine receipt stayed on disk for a
  reviewer to find, and the market was bound to the forgery. Ambiguity refuses.
* **Evidence could live outside the checkout.** An absolute path was taken as
  given, so a receipt citing `/tmp/anything` verified — a record in no diff, in
  no pull request, and absent from the runner the merge-time gate runs on. The
  record must now resolve inside the repository, asked after `resolve()` so a
  symlink is judged by where it lands.
* **`withdrawn` was written and never read.** :func:`withdraw` appended to it
  and :func:`save` wrote it out, and then re-adding the market with its original
  receipt still on disk loaded it live again: a revocation became an approval.
  :func:`_revocation_of` makes the withdrawal win whenever it is not older than
  the approval it revokes, so re-approval is a NEWER human act and nothing else.

Nothing here writes a receipt. There is still no `grant()`.

## Automatic demotion, one direction only

An allowlisted market whose **forward ROI interval falls below the floor
declared at approval** is auto-withdrawn. The floor is recorded on the entry at
approval time rather than looked up later, so the bar a market is held to is the
bar its receipt named and not the bar that would be convenient in March.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path

from cbb_betting_lab.competitions import Competition
from cbb_betting_lab.config import MANUAL_DIR


POLICY_FILENAME = "staging_provider_policy.json"
RECEIPTS_DIRNAME = "human_acceptance_receipts"

#: The check every sentence in this repository promises, spelled exactly as
#: GitHub reports it. It is a CONTRACT STRING: `CLAUDE.md`'s contract table
#: holds it and `tests/test_contract_strings.py` pins the table against this
#: constant, against the workflow's own `name:` and its job's `name:`, and
#: against every document that promises the gate. Renaming the workflow
#: without renaming the references is therefore a red build rather than four
#: sentences about a check that no longer reports.
POLICY_GATE_CHECK = "Policy Gate"
#: The file that declares that check.
POLICY_GATE_WORKFLOW = ".github/workflows/policy-gate.yml"

#: The default, and the state this lab expects to stay in. Manual-only means
#: the card reads nothing from staging and produces no selection.
MANUAL_ONLY = "manual_only"

#: The signer a receipt may never carry, matched case-insensitively on the
#: letters of `signed_by` with everything else stripped, so `claude`, `CLAUDE`,
#: `Claude Fable 5.1`, `claude-code` and `c.l.a.u.d.e` all refuse.
FORBIDDEN_SIGNER = "claude"

#: The signatures this door opens for, as the LETTERS of `signed_by` with case,
#: spacing, punctuation and digits removed — so `Cooper Ross`, `cooper ross`,
#: `COOPER ROSS` and `cooperross399` all fold to `cooperross` and are accepted,
#: and everything else is not.
#:
#: Until 2026-09-26 there was no such list. `_signer_is_forbidden` is a DENY
#: list of exactly one name, so every string that does not spell `claude`
#: passed: `Anonymous Bot`, `fixture-signer`, `automated`, the empty-adjacent
#: `.` — measured, all four loaded a market live. A deny list of one name
#: asks "is this the one signer we refuse"; the door needs to ask "is this the
#: signer whose approval it is". Both run now, in that order, because the
#: refusal a reader most needs to see is the one that names Claude.
#:
#: IT COMES FROM SOURCE AND NOWHERE ELSE. No argument, environment variable,
#: git config or config file reaches it, deliberately and for the same reason
#: the reviewer allow-list in the sibling labs is a source constant: the
#: threat model is an agent with code execution on this machine, and anything
#: that agent can write is not an identity check. Changing this list is a
#: source edit in a pull request a human merges. `tests/test_staging_policy_
#: receipts.py::test_the_accepted_signer_list_is_unreachable_from_configuration`
#: holds that shut.
ACCEPTED_SIGNERS: tuple[str, ...] = ("cooperross",)


@dataclass(frozen=True)
class AllowlistEntry:
    """One market a human has approved, and the terms they approved it on."""

    market: str
    receipt_id: str
    approved_on: str
    #: The forward ROI below which this market auto-withdraws. Declared at
    #: approval, never re-read from a later report.
    roi_floor: float
    #: sha256 of the evidence bundle the receipt was signed against. When the
    #: evidence moves, this stops matching and the gate goes red — which is how
    #: the NHL lab caught its own stale approval.
    evidence_checksum: str
    minimum_bets: int = 200
    note: str = ""


@dataclass
class StagingProviderPolicy:
    """The whole policy. Absent or unreadable means manual-only."""

    provider: str = "the_odds_api"
    #: The mode in force. :func:`load` sets this to `MANUAL_ONLY` whenever an
    #: allowlisted market lacks a valid receipt, whatever the file declares.
    mode: str = MANUAL_ONLY
    allowlist: dict[str, AllowlistEntry] = field(default_factory=dict)
    withdrawn: list[dict] = field(default_factory=list)
    #: What the policy file says its mode is. Kept apart from `mode` so that a
    #: machine `save()` after a `withdraw()` writes the human's field back
    #: unchanged: withdrawal is the one edit the machine may make to this file.
    declared_mode: str = ""
    #: market -> why its receipt did not stand up. Non-empty means `mode` was
    #: forced to manual-only by :func:`load`.
    receipt_failures: dict[str, str] = field(default_factory=dict)
    #: market -> the receipt file that stood behind it, for the record.
    receipts: dict[str, str] = field(default_factory=dict)

    def allows(self, market: str) -> bool:
        return (
            self.mode != MANUAL_ONLY
            and not self.receipt_failures
            and str(market) in self.allowlist
        )

    def entry(self, market: str) -> AllowlistEntry | None:
        return self.allowlist.get(str(market))

    def summary_line(self, competition: Competition) -> str:
        who = f"`{self.provider}:{competition.key}`"
        if self.receipt_failures:
            lacking = "; ".join(
                f"`{market}` lacks {reason}"
                for market, reason in sorted(self.receipt_failures.items())
            )
            return (
                f"{who} is **manual-only, forced**: the policy file declares mode "
                f"`{self.declared_mode or 'unknown'}` and allowlists "
                f"{len(self.allowlist)} market(s), but {lacking}. No market is "
                "read from staging and the card produces no selection until a "
                "valid human acceptance receipt stands behind every allowlisted "
                "market."
            )
        if self.mode == MANUAL_ONLY:
            if self.allowlist:
                return (
                    f"{who} is **manual-only**. {len(self.allowlist)} market(s) "
                    "are listed but the mode is manual-only, so none is read "
                    "from staging and the card produces no selection."
                )
            return (
                f"{who} is **manual-only**. No "
                "market is allowlisted, the card produces no selection, and "
                "that is the correct state for a lab with no signed receipt."
            )
        markets = ", ".join(sorted(self.allowlist)) or "none"
        return (
            f"{who} allowlists {len(self.allowlist)} "
            f"market(s): {markets}, each behind a verified human acceptance "
            "receipt."
        )


def policy_path(manual_dir: Path | None = None) -> Path:
    return (Path(manual_dir) if manual_dir else Path(MANUAL_DIR)) / POLICY_FILENAME


def receipts_dir(manual_dir: Path | None = None) -> Path:
    return (Path(manual_dir) if manual_dir else Path(MANUAL_DIR)) / RECEIPTS_DIRNAME


def repository_root(manual_dir: Path | None = None) -> Path:
    """Where a receipt's relative evidence path is read from: two directories
    above `manual_dir`, because the manual directory is `<repo>/data/manual`."""
    return (Path(manual_dir) if manual_dir else Path(MANUAL_DIR)).resolve().parents[1]


def _signer_letters(signed_by: str) -> str:
    return "".join(ch for ch in str(signed_by).casefold() if ch.isalpha())


def _signer_is_forbidden(signed_by: str) -> bool:
    return FORBIDDEN_SIGNER in _signer_letters(signed_by)


def _signer_is_accepted(signed_by: str) -> bool:
    """Whether `signed_by` is one of :data:`ACCEPTED_SIGNERS`.

    EQUALITY on the folded letters, not containment. Containment would accept
    `Claude, for Cooper Ross` on the strength of the two words at the end —
    and while `_signer_is_forbidden` catches that particular one, it catches
    it for a different reason, and a rule that is only correct because a
    neighbouring rule covers its mistakes is one edit from being wrong.
    """
    return _signer_letters(signed_by) in {
        _signer_letters(name) for name in ACCEPTED_SIGNERS
    }


def _evidence_of(receipt: dict) -> tuple[str, str]:
    evidence = receipt.get("evidence")
    if isinstance(evidence, dict):
        return str(evidence.get("path", "") or ""), str(evidence.get("sha256", "") or "")
    return (
        str(receipt.get("evidence_path", "") or ""),
        str(receipt.get("evidence_sha256", "") or ""),
    )


def _examine_receipt(
    path: Path, payload: object, entry: AllowlistEntry, root: Path
) -> str:
    """Why this receipt does not stand behind `entry`, or "" when it does.

    Every check is spelled out as a reason, because the summary line prints
    the reason and a reader must be able to act on it.
    """
    name = path.name
    if not isinstance(payload, dict):
        return f"a receipt that is a JSON object ({name} is not one)"
    if str(payload.get("market", "")) != entry.market:
        return f"a receipt naming market `{entry.market}` ({name} names `{payload.get('market', '')}`)"
    if entry.receipt_id:
        carried = str(payload.get("receipt_id", "") or "")
        if carried != entry.receipt_id and path.stem != entry.receipt_id:
            return (
                f"a receipt carrying receipt_id `{entry.receipt_id}` ({name} "
                f"carries `{carried or path.stem}`)"
            )
    evidence_path, cited = _evidence_of(payload)
    if not evidence_path or not cited:
        return f"an evidence record path and its sha256 ({name} cites neither or one)"
    record = Path(evidence_path)
    if not record.is_absolute():
        record = root / record
    # THE EVIDENCE MUST BE IN THE TREE THE REVIEWER READ.
    #
    # A relative path is read against the repository root and an absolute one
    # was taken as given, so until 2026-09-26 a receipt could cite
    # `/tmp/anything` — measured, it loaded a market live — and so could a
    # relative path with enough `../` in it. Evidence outside the checkout is
    # evidence that is not in the pull request, not in the diff a human
    # reviews and not on the runner the merge-time gate runs on. `resolve()`
    # first, so a symlink INSIDE the tree that points outside it is caught by
    # where it lands rather than by how it is spelled.
    #
    # An absolute path that lands inside the repository is still fine; that is
    # a spelling, not an escape, and a test has pinned it since 2026-09-05.
    try:
        resolved = record.resolve()
        inside = resolved.is_relative_to(root.resolve())
    except (OSError, RuntimeError, ValueError):
        inside = False
    if not inside:
        return (
            f"an evidence record inside the repository ({name} cites "
            f"`{evidence_path}`, which resolves outside it, where no reviewer "
            "of this change can see it)"
        )
    if not record.is_file():
        return f"an evidence record on disk ({name} cites `{evidence_path}`, which does not exist)"
    actual = hashlib.sha256(record.read_bytes()).hexdigest()
    if actual.casefold() != cited.strip().casefold():
        return (
            f"an evidence record hashing to its cited sha256 ({name} cites "
            f"{cited[:12]}… for `{evidence_path}`, which hashes to {actual[:12]}…)"
        )
    # THE ENTRY'S OWN CHECKSUM, WHICH NOTHING READ UNTIL 2026-09-17.
    #
    # `AllowlistEntry.evidence_checksum` declares an enforcement in its own
    # docstring — "when the evidence moves, this stops matching and the gate
    # goes red, which is how the NHL lab caught its own stale approval" — and
    # was read by no code at all. `load()` parsed it, `save()` wrote it back,
    # and the module-level `evidence_checksum()` helper that produces the value
    # had zero callers. A guard that exists only in prose is documentation.
    #
    # It is NOT the same check as the hash above. That one asks whether the
    # receipt's cited sha256 matches the evidence file it names, which catches
    # evidence that moved under a receipt. This one asks whether the receipt
    # still cites the evidence THE ENTRY WAS WRITTEN AGAINST — so swapping in a
    # different receipt, internally consistent with different evidence, is
    # caught too. The first binds a receipt to a file; this binds the allowlist
    # to a receipt.
    #
    # Empty is "not recorded", never "matches": an entry written before the
    # field was populated cannot be checked and must not read as checked.
    if entry.evidence_checksum:
        if entry.evidence_checksum.strip().casefold() != cited.strip().casefold():
            return (
                f"a receipt citing the evidence this allowlist entry was signed "
                f"against ({name} cites {cited[:12]}…, the entry records "
                f"{entry.evidence_checksum[:12]}…)"
            )

    signed_by = str(payload.get("signed_by", "") or "").strip()
    if not signed_by:
        return f"a non-empty signed_by ({name} has none)"
    if _signer_is_forbidden(signed_by):
        return (
            f"a human signer ({name} is signed by `{signed_by}`, and Claude may "
            "never sign a receipt)"
        )
    if not _signer_is_accepted(signed_by):
        return (
            f"a signature from somebody whose approval this door opens for "
            f"({name} is signed by `{signed_by}`, which is not one of "
            f"{sorted(ACCEPTED_SIGNERS)})"
        )
    signed_on = str(payload.get("signed_on", "") or "").strip()
    if not signed_on:
        return f"a signed_on date ({name} has none)"
    try:
        date.fromisoformat(signed_on)
    except ValueError:
        return f"a signed_on date in YYYY-MM-DD ({name} has `{signed_on}`)"
    return ""


def _revocation_of(
    entry: AllowlistEntry, withdrawn: object
) -> str:
    """Why a recorded withdrawal refuses `entry`, or "" when none does.

    A REVOCATION OUTRANKS THE APPROVAL IT REVOKES. `withdrawn` is the file's
    own record of the markets the machine took back, and until 2026-09-26
    nothing read it at verification time: `withdraw()` appended to it and
    `save()` wrote it out, and then re-adding the market to the allowlist,
    with its original receipt still on disk, loaded live again. Measured: a
    market withdrawn on 2026-09-25 for falling through its ROI floor, whose
    receipt is dated 2026-09-23, was allowed.

    The withdrawal wins when it is NOT OLDER than the receipt the entry names.
    An approval signed AFTER a withdrawal is a human re-approving in the
    ordinary way and is not refused here — that is a new decision, and it
    still needs everything else on this page. An unparseable or undated
    withdrawal wins too: a record that a permission was taken away, whose date
    cannot be read, is not a reason to hand the permission back.
    """
    if not isinstance(withdrawn, (list, tuple)):
        return ""
    for record in withdrawn:
        if not isinstance(record, dict):
            continue
        if str(record.get("market", "")) != entry.market:
            continue
        when = str(record.get("withdrawn_at", "") or "").strip()
        reason = str(record.get("reason", "") or "").strip() or "no reason recorded"
        stamp = when[:10]
        try:
            withdrawn_on = date.fromisoformat(stamp)
        except ValueError:
            return (
                f"an allowlist entry this policy has not already withdrawn "
                f"(`withdrawn` records `{entry.market}` taken back at "
                f"`{when or 'no date'}`, which is not a readable date, for: "
                f"{reason})"
            )
        try:
            signed_on = date.fromisoformat(str(entry.approved_on or "")[:10])
        except ValueError:
            signed_on = None
        if signed_on is None or withdrawn_on >= signed_on:
            return (
                f"an allowlist entry this policy has not already withdrawn "
                f"(`withdrawn` records `{entry.market}` taken back on "
                f"{withdrawn_on.isoformat()}, at or after the "
                f"{signed_on.isoformat() if signed_on else 'undated'} approval "
                f"this entry rests on, for: {reason})"
            )
    return ""


def verify_receipt(
    entry: AllowlistEntry,
    manual_dir: Path | None = None,
    *,
    withdrawn: object = None,
) -> tuple[Path | None, str]:
    """`(receipt_path, "")` when a valid receipt stands behind `entry`, else
    `(None, what_is_lacking)`.

    Reads only `<manual_dir>/human_acceptance_receipts/*.json` — not
    `superseded/`, whose contents are records of decisions that were unmade.
    Never writes anything.

    `withdrawn` is the policy file's own withdrawal record, which :func:`load`
    always passes and a direct caller may omit. It can only ever ADD a
    refusal: there is no value a caller can pass that turns a refusal into an
    acceptance, which is what keeps it from being a way in.
    """
    directory = receipts_dir(manual_dir)
    if not directory.is_dir():
        return None, f"a receipt directory at `{directory}` (there is none)"
    # THE `receipt_id` IS NOT OPTIONAL.
    #
    # The guard used to read `if entry.receipt_id:`, so an entry that simply
    # omitted the field bound to WHICHEVER receipt in the directory happened to
    # name its market — measured, an entry reading `{"market": "spread"}` alone
    # loaded live behind a file called `whatever.json`. An approval that does
    # not say which approval it is is not one.
    if not str(entry.receipt_id or "").strip():
        return None, (
            f"a `receipt_id` on its allowlist entry (`{entry.market}` names "
            "none, so any receipt naming the market would stand behind it)"
        )
    # AN ENTRY THAT RECORDS NO CHECKSUM IS NOT BOUND TO A RECEIPT.
    #
    # `_examine_receipt` reads an empty `evidence_checksum` as "not recorded"
    # and declines to judge it, which is the honest answer for a function
    # asked about ONE RECEIPT — and its own docstring says the empty case is
    # "what the caller's own reporting is for". THIS IS THAT CALLER, and until
    # 2026-09-26 its reporting was silence: all ten of this lab's live entries
    # carried an empty `evidence_checksum`, so the binding the field exists for
    # was enforced on none of them. Measured: with the field empty, a receipt
    # citing evidence the entry had never been signed against was accepted and
    # the market loaded live.
    #
    # Not-recorded must not read as checked, so the door that cannot check it
    # does not open. `_examine_receipt` keeps its own semantics; this is a
    # second question, asked one layer up, about the ALLOWLIST rather than
    # about the receipt — and it is asked HERE rather than in `load()` so that
    # the merge-time gate, which calls this function market by market, asks
    # exactly the same question the card asks.
    if not str(entry.evidence_checksum or "").strip():
        return None, (
            f"an `evidence_checksum` on its allowlist entry (`{entry.market}` "
            "records none, so nothing binds this market to the evidence its "
            "receipt was signed against, and any receipt carrying the right "
            "`receipt_id` would stand behind it)"
        )
    revoked = _revocation_of(entry, withdrawn)
    if revoked:
        return None, revoked
    root = repository_root(manual_dir)
    candidates = sorted(p for p in directory.glob("*.json") if p.is_file())
    if not candidates:
        return None, f"any receipt under `{directory}` (there is none)"
    reasons: list[str] = []
    accepted: list[Path] = []
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            reasons.append(f"a readable receipt ({path.name}: {exc.__class__.__name__})")
            continue
        reason = _examine_receipt(path, payload, entry, root)
        if not reason:
            accepted.append(path)
            continue
        reasons.append(reason)
    # EXACTLY ONE RECEIPT, OR NONE.
    #
    # This loop used to return the FIRST file that verified, in sorted order,
    # which is alphabetical order of filename. So a second file claiming the
    # same `receipt_id` and market, citing evidence its author wrote, SHADOWED
    # the genuine receipt whenever its name sorted earlier — measured:
    # `aaa-forged.json` won over `r1.json`, the genuine receipt stayed on disk
    # for a reviewer to find, and the market loaded live bound to the forgery.
    # Two receipts claiming one approval is not an approval; it is a question,
    # and this door answers a question with no.
    if len(accepted) > 1:
        names = ", ".join(f"`{p.name}`" for p in accepted)
        return None, (
            f"exactly one receipt claiming `{entry.receipt_id}` ({len(accepted)} "
            f"do: {names} — which of them is the approval cannot be read off "
            "the directory, so none of them is)"
        )
    if accepted:
        return accepted[0], ""
    # The most specific reason wins: a receipt that named the market and failed
    # a later check explains more than one that never mentioned it.
    naming = [r for r in reasons if not r.startswith("a receipt naming market")]
    if naming:
        return None, naming[0]
    return None, f"a receipt naming market `{entry.market}` under `{directory}`"


def load(manual_dir: Path | None = None) -> StagingProviderPolicy:
    """The policy, or a manual-only one.

    Every failure mode returns manual-only. A policy file that cannot be read
    is not an excuse to read staging; it is a reason not to. And a policy
    whose allowlist is not backed, market for market, by a receipt that
    :func:`verify_receipt` accepts loads as manual-only **whole**, with the
    reasons on `receipt_failures`.
    """
    path = policy_path(manual_dir)
    if not path.is_file():
        return StagingProviderPolicy()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return StagingProviderPolicy()
    if not isinstance(payload, dict):
        return StagingProviderPolicy()
    entries = {}
    for item in payload.get("allowlist", []) or []:
        if not isinstance(item, dict) or not item.get("market"):
            continue
        entries[str(item["market"])] = AllowlistEntry(
            market=str(item["market"]),
            receipt_id=str(item.get("receipt_id", "")),
            approved_on=str(item.get("approved_on", "")),
            roi_floor=float(item.get("roi_floor", 0.0) or 0.0),
            evidence_checksum=str(item.get("evidence_checksum", "")),
            minimum_bets=int(item.get("minimum_bets", 200) or 200),
            note=str(item.get("note", "")),
        )
    declared = str(payload.get("mode", MANUAL_ONLY))
    withdrawn = list(payload.get("withdrawn", []) or [])
    failures: dict[str, str] = {}
    receipts: dict[str, str] = {}
    if declared != MANUAL_ONLY:
        for market in sorted(entries):
            receipt, reason = verify_receipt(
                entries[market], manual_dir, withdrawn=withdrawn
            )
            if receipt is None:
                failures[market] = reason
            else:
                receipts[market] = str(receipt)
    return StagingProviderPolicy(
        provider=str(payload.get("provider", "the_odds_api")),
        mode=MANUAL_ONLY if failures else declared,
        allowlist=entries,
        withdrawn=withdrawn,
        declared_mode=declared,
        receipt_failures=failures,
        receipts=receipts,
    )


def save(policy: StagingProviderPolicy, manual_dir: Path | None = None) -> Path:
    """Write the policy file. Writes no receipt, and never will.

    The mode written is the one the file declared (`declared_mode`) when the
    policy came from :func:`load`, so a run that loaded a receipt-less policy as
    manual-only and then withdrew a market puts the human's own mode field back
    unchanged. `load` re-checks the receipts on the next read regardless, so
    nothing written here can make `allows()` true.
    """
    path = policy_path(manual_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "provider": policy.provider,
                "mode": policy.declared_mode or policy.mode,
                "allowlist": [
                    {
                        "market": e.market,
                        "receipt_id": e.receipt_id,
                        "approved_on": e.approved_on,
                        "roi_floor": e.roi_floor,
                        "evidence_checksum": e.evidence_checksum,
                        "minimum_bets": e.minimum_bets,
                        "note": e.note,
                    }
                    for e in sorted(policy.allowlist.values(), key=lambda x: x.market)
                ],
                "withdrawn": policy.withdrawn,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def withdraw(
    policy: StagingProviderPolicy, market: str, *, reason: str, at: str = ""
) -> bool:
    """Remove a market from the allowlist. The only direction the machine moves.

    Returns True when something was removed. Idempotent: withdrawing an absent
    market is a no-op rather than an error, because a demotion run must be safe
    to re-run.
    """
    entry = policy.allowlist.pop(str(market), None)
    if entry is None:
        return False
    policy.withdrawn.append(
        {
            "market": entry.market,
            "receipt_id": entry.receipt_id,
            "approved_on": entry.approved_on,
            "withdrawn_at": at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "reason": reason,
        }
    )
    return True


def evidence_checksum(*paths: Path) -> str:
    """A stable digest of the evidence a receipt is signed against.

    Content, not mtime. The point is that a *re-run producing the same numbers*
    leaves the checksum alone while a re-run producing different numbers breaks
    it — so a stale approval is caught by arithmetic rather than by somebody
    remembering to look.
    """
    digest = hashlib.sha256()
    for path in sorted(Path(p) for p in paths):
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        if Path(path).is_file():
            digest.update(Path(path).read_bytes())
        else:
            digest.update(b"<absent>")
        digest.update(b"\0")
    return digest.hexdigest()
