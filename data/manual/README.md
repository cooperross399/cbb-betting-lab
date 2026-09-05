# Protected manual files

Nothing in this directory is written by an automated run, with exactly one
exception named below. These are the files a human decision lives in, and the
whole point of a decision living in a file is that a script cannot make it.

| File | Who may write it |
|:---|:---|
| `staging_provider_policy.json` | **Cooper**, in a pull request with a signed receipt beside it and a green **`Policy Gate`** check. Claude may call `staging_provider_policy.withdraw()` on it — the one exception — because withdrawal can only ever reduce what the card may do. |
| `human_acceptance_receipts/*` | **Cooper.** Claude drafts a receipt with truthful provenance and never signs one. | A receipt is a JSON object with `market`, `receipt_id`, `evidence` (`{"path", "sha256"}` of a record that exists and hashes to that value; a relative path is read from the repository root), `signed_by` (a person, never Claude) and `signed_on` (`YYYY-MM-DD`). `staging_provider_policy.load()` checks all of it for every allowlisted market and loads the whole policy manual-only when any market lacks one. |
| `human_acceptance_receipts/superseded/*` | Moved here when a receipt is withdrawn. Kept, never deleted: a superseded receipt is the record of a decision that was really made. |

`Policy Gate` is `.github/workflows/policy-gate.yml`. It runs on every pull
request — there is no `paths:` filter, because a path-filtered check is not
reported on the pull requests it filters out — and runs
`scripts/check_allowlist_receipts.py`, which loads the policy the way the card
loads it and then verifies every allowlisted market's receipt one at a time,
including the entries a `manual_only` file leaves `load()` itself skipping. The
job summary names every market it checked, the receipt behind it or what that
market lacked, and the markets the change adds. It is red while any allowlisted
market lacks a receipt, while a cited evidence record is missing or no longer
hashes to the value the receipt was signed against, or while a receipt is
signed by Claude in any spelling. A policy file that exists and cannot be
read exits 2 and reports a gate that did not run, which is not the same
result as a repository that allowlists nothing and no longer prints the same
sentence as one. "Cannot be read" is wider than "is not JSON": an allowlist
that is not a list, an entry that is a bare string, an entry naming no
market, a directory where the file belongs and a symlink into nothing are all
exit 2, because `load()` turns every one of them into an allowlist of nothing
and a gate that reports on an allowlist nobody read has checked nothing. The
summary ends with one `POLICY GATE VERDICT:` line, built from the exit status,
and the verdict wording is taken out of every other line before printing:
market names and receipt notes are text from files the gate does not control,
and a run that failed may not contain the sentence a run that passed prints.
No condition stands between a pull request and that verdict — the job carries
no `if:`, no `needs:` and no `strategy:`, and a check skipped by a condition
is reported by GitHub as a success. What the gate checks about a signature is exactly this: that
`signed_by` is not one of the spellings of Claude it refuses. Nothing here is
cryptographic and no identity is verified, so whether the person named
actually signed is decided by whoever reviews the pull request. Until
2026-09-05 the row above named a gate that did not exist: nothing under
`.github/workflows/` opened a receipt. It is
not a context branch protection requires — measured 2026-09-05, main requires
`Tests` and nothing else — so a red `Policy Gate` is a fact in the pull request
and not a hold on the merge button.

The policy ships **manual-only**, which means the card reads nothing from
staging and produces no selection. That is the correct state for a lab with no
signed receipt, and it is the state this lab expects to remain in unless the
measurement says otherwise and Cooper signs.
