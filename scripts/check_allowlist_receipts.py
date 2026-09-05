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
allowlists and no environment waiver. A receipt signed by Claude in any
spelling is refused by `staging_provider_policy._signer_is_forbidden`, so the
one thing this repository could always have produced by itself — a JSON file
saying the market is fine — is the one thing that can never satisfy this gate.
This script writes nothing: not the policy, not a receipt, not the evidence.
There is still no `grant()`.

EXIT STATUS. `0` when every allowlisted market is receipted, `1` when one is
not, and `2` when the check could not be run at all — an unreadable base ref,
a manual directory that is not there. `2` is not a pass: "I could not check"
and "there was nothing to check" must never take the same branch.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from cbb_betting_lab import staging_provider_policy as SPP
from cbb_betting_lab.competitions import CBB


#: The policy file, relative to the repository root. The gate reads the base
#: commit's copy of exactly this path.
POLICY_RELATIVE = f"data/manual/{SPP.POLICY_FILENAME}"

OK, RED, BROKEN = 0, 1, 2


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
    """The verdict and the lines that explain it, in markdown."""
    manual = root / "data" / "manual"
    lines = ["## Policy gate: human acceptance receipts", ""]
    if not manual.is_dir():
        lines.append(
            f"**Broken gate.** There is no `{manual}` to read. This run checked "
            "nothing; it is not evidence that the allowlist is receipted."
        )
        return BROKEN, lines

    policy = SPP.load(manual)
    lines.append(f"- Policy file: `{POLICY_RELATIVE}`")
    lines.append(f"- Mode declared in the file: `{policy.declared_mode or 'none'}`")
    lines.append(f"- Mode in force after `load()`: `{policy.mode}`")
    lines.append(f"- Receipts read from: `data/manual/{SPP.RECEIPTS_DIRNAME}/*.json`")
    lines.append("")
    lines.append(f"The card's own reading: {policy.summary_line(CBB)}")
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
            lines.append(f"| `{market}` | — | **RED** — lacks {reason} |")
        else:
            lines.append(f"| `{market}` | `{Path(receipt).name}` | green |")
    lines.append("")

    added_note = ""
    added: set[str] = set()
    if base_ref:
        try:
            base_markets, added_note = base_allowlist(root, base_ref)
        except RuntimeError as exc:
            lines.append(
                f"**Broken gate.** {exc}. This run did not compare the allowlist "
                "against the base commit; it is not evidence that nothing was added."
            )
            return BROKEN, lines
        added = set(markets) - base_markets
        lines.append("### What this change adds")
        lines.append("")
        lines.append(f"- {added_note}")
        if added:
            lines.append(
                "- This change ADDS "
                + ", ".join(f"`{m}`" for m in sorted(added))
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
        lines.append("### Verdict")
        lines.append("")
        for market in sorted(failures):
            note = " — and this change is what adds it" if market in added else ""
            lines.append(f"- **`{market}`** lacks {failures[market]}{note}.")
        lines.append("")
        lines.append(
            "A market reaches the card only behind a receipt a person signed: one "
            "that names the market, cites an evidence record that exists and still "
            "hashes to the value the receipt was signed against, carries a signer "
            "who is not Claude, and carries a date. This repository can write the "
            "policy file and can never write the signature, which is the whole "
            "point of the file."
        )
        return RED, lines

    lines.append("### Verdict")
    lines.append("")
    if markets:
        lines.append(
            f"- Every one of the {len(markets)} allowlisted market(s) is backed by "
            "a receipt naming it, citing an evidence record that still hashes to "
            "the cited value, signed by a person who is not Claude, and dated."
        )
    else:
        lines.append("- Nothing is allowlisted, so there is nothing to receipt.")
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
    body = "\n".join(lines).rstrip() + "\n"

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
