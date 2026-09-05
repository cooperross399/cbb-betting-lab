# Protected manual files

Nothing in this directory is written by an automated run, with exactly one
exception named below. These are the files a human decision lives in, and the
whole point of a decision living in a file is that a script cannot make it.

| File | Who may write it |
|:---|:---|
| `staging_provider_policy.json` | **Cooper**, in a pull request with a signed receipt beside it and a green policy gate. Claude may call `staging_provider_policy.withdraw()` on it — the one exception — because withdrawal can only ever reduce what the card may do. |
| `human_acceptance_receipts/*` | **Cooper.** Claude drafts a receipt with truthful provenance and never signs one. | A receipt is a JSON object with `market`, `receipt_id`, `evidence` (`{"path", "sha256"}` of a record that exists and hashes to that value; a relative path is read from the repository root), `signed_by` (a person, never Claude) and `signed_on` (`YYYY-MM-DD`). `staging_provider_policy.load()` checks all of it for every allowlisted market and loads the whole policy manual-only when any market lacks one. |
| `human_acceptance_receipts/superseded/*` | Moved here when a receipt is withdrawn. Kept, never deleted: a superseded receipt is the record of a decision that was really made. |

The policy ships **manual-only**, which means the card reads nothing from
staging and produces no selection. That is the correct state for a lab with no
signed receipt, and it is the state this lab expects to remain in unless the
measurement says otherwise and Cooper signs.
