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
with a receipt beside it, in a pull request whose policy gate is green, merged
by Cooper.

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
from datetime import datetime, timezone
from pathlib import Path

from cbb_betting_lab.competitions import Competition
from cbb_betting_lab.config import MANUAL_DIR


POLICY_FILENAME = "staging_provider_policy.json"
RECEIPTS_DIRNAME = "human_acceptance_receipts"

#: The default, and the state this lab expects to stay in. Manual-only means
#: the card reads nothing from staging and produces no selection.
MANUAL_ONLY = "manual_only"


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
    mode: str = MANUAL_ONLY
    allowlist: dict[str, AllowlistEntry] = field(default_factory=dict)
    withdrawn: list[dict] = field(default_factory=list)

    def allows(self, market: str) -> bool:
        return self.mode != MANUAL_ONLY and str(market) in self.allowlist

    def entry(self, market: str) -> AllowlistEntry | None:
        return self.allowlist.get(str(market))

    def summary_line(self, competition: Competition) -> str:
        if self.mode == MANUAL_ONLY:
            return (
                f"`{self.provider}:{competition.key}` is **manual-only**. No "
                "market is allowlisted, the card produces no selection, and "
                "that is the correct state for a lab with no signed receipt."
            )
        markets = ", ".join(sorted(self.allowlist)) or "none"
        return (
            f"`{self.provider}:{competition.key}` allowlists {len(self.allowlist)} "
            f"market(s): {markets}."
        )


def policy_path(manual_dir: Path | None = None) -> Path:
    return (Path(manual_dir) if manual_dir else Path(MANUAL_DIR)) / POLICY_FILENAME


def load(manual_dir: Path | None = None) -> StagingProviderPolicy:
    """The policy, or a manual-only one.

    Every failure mode returns manual-only. A policy file that cannot be read
    is not an excuse to read staging; it is a reason not to.
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
    return StagingProviderPolicy(
        provider=str(payload.get("provider", "the_odds_api")),
        mode=str(payload.get("mode", MANUAL_ONLY)),
        allowlist=entries,
        withdrawn=list(payload.get("withdrawn", []) or []),
    )


def save(policy: StagingProviderPolicy, manual_dir: Path | None = None) -> Path:
    path = policy_path(manual_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "provider": policy.provider,
                "mode": policy.mode,
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
