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

What it checks about the signature is what :func:`_signer_is_forbidden`
checks and nothing more: that `signed_by` is not one of the spellings of
Claude it refuses. Nothing there is cryptographic and no identity is
verified, so whether the signer is really Cooper is the judgement of whoever
reviews the pull request rather than a thing this gate can enforce.

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
* carries a non-empty `"signed_by"` that is not Claude in any spelling or case,
* and a `"signed_on"` date (`YYYY-MM-DD`).

When the entry names a `receipt_id`, the receipt must carry the same id (as its
`"receipt_id"` field or its file stem). `superseded/` is not read: a withdrawn
receipt is a record, not a permission. Any allowlisted market lacking a valid
receipt makes the **whole** policy load as manual-only — fail closed, not
market-by-market — with the reasons kept on the object and printed by
`summary_line()`, so the card says which market lacked what. The evidence hash
check is the NHL lab's own catch, made mandatory: when the evidence moves
underneath a receipt, the checksum stops matching and the door shuts on its
own.

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


def _signer_is_forbidden(signed_by: str) -> bool:
    letters = "".join(ch for ch in str(signed_by).casefold() if ch.isalpha())
    return FORBIDDEN_SIGNER in letters


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
    if not record.is_file():
        return f"an evidence record on disk ({name} cites `{evidence_path}`, which does not exist)"
    actual = hashlib.sha256(record.read_bytes()).hexdigest()
    if actual.casefold() != cited.strip().casefold():
        return (
            f"an evidence record hashing to its cited sha256 ({name} cites "
            f"{cited[:12]}… for `{evidence_path}`, which hashes to {actual[:12]}…)"
        )
    signed_by = str(payload.get("signed_by", "") or "").strip()
    if not signed_by:
        return f"a non-empty signed_by ({name} has none)"
    if _signer_is_forbidden(signed_by):
        return (
            f"a human signer ({name} is signed by `{signed_by}`, and Claude may "
            "never sign a receipt)"
        )
    signed_on = str(payload.get("signed_on", "") or "").strip()
    if not signed_on:
        return f"a signed_on date ({name} has none)"
    try:
        date.fromisoformat(signed_on)
    except ValueError:
        return f"a signed_on date in YYYY-MM-DD ({name} has `{signed_on}`)"
    return ""


def verify_receipt(
    entry: AllowlistEntry, manual_dir: Path | None = None
) -> tuple[Path | None, str]:
    """`(receipt_path, "")` when a valid receipt stands behind `entry`, else
    `(None, what_is_lacking)`.

    Reads only `<manual_dir>/human_acceptance_receipts/*.json` — not
    `superseded/`, whose contents are records of decisions that were unmade.
    Never writes anything.
    """
    directory = receipts_dir(manual_dir)
    if not directory.is_dir():
        return None, f"a receipt directory at `{directory}` (there is none)"
    root = repository_root(manual_dir)
    candidates = sorted(p for p in directory.glob("*.json") if p.is_file())
    if not candidates:
        return None, f"any receipt under `{directory}` (there is none)"
    reasons: list[str] = []
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            reasons.append(f"a readable receipt ({path.name}: {exc.__class__.__name__})")
            continue
        reason = _examine_receipt(path, payload, entry, root)
        if not reason:
            return path, ""
        reasons.append(reason)
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
    failures: dict[str, str] = {}
    receipts: dict[str, str] = {}
    if declared != MANUAL_ONLY:
        for market in sorted(entries):
            receipt, reason = verify_receipt(entries[market], manual_dir)
            if receipt is None:
                failures[market] = reason
            else:
                receipts[market] = str(receipt)
    return StagingProviderPolicy(
        provider=str(payload.get("provider", "the_odds_api")),
        mode=MANUAL_ONLY if failures else declared,
        allowlist=entries,
        withdrawn=list(payload.get("withdrawn", []) or []),
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
