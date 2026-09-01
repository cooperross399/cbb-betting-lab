# How the card reaches Cooper, and the scars in the chain

**Zero email.** Cooper, 2026-08-28: *"i dont want emails anymore."* Nothing in
this chain sends one, and the two changes that stop them are both made, because
**one without the other does nothing**: the card comment mentions nobody, *and*
the repository subscription is set to ignored. An `@mention` overrides an
ignored subscription.

The chain has four links. Only the first is load-bearing; the rest are a reading
layer, and a routine that did not run is not the card failing.

```
  GitHub Actions              git ref                Claude Code cloud        regular Claude
  CBB Gameday Refresh  ──▶  card-feed branch  ──▶    CBB CARD RELAY     ──▶  chat scheduled task
  (fetch, price, freeze,     latest_card_comment.md   (copies, verbatim,      (reads the newest
   settle, publish)          latest_status.json        into Google Drive)      Drive file, presents)
                             forward_evidence.csv
                             snapshots/
```

---

## Link 1 — the workflow, which is the only thing that matters

`.github/workflows/cbb-gameday-refresh.yml`, workflow name **`CBB Gameday
Refresh`**. Four crons: 09:00 and 10:00 UTC for the `morning` slot, 16:00 and
17:00 UTC for the `evening` slot, each a primary and a backup. The reasoning is
in `docs/card_cadence.md`; the short version is that the slate spans twelve
hours and one freeze cannot serve it.

**It needs no laptop and no terminal.** Never tell Cooper to open a terminal to
get a card.

---

## Link 2 — `card-feed`, an orphan branch

It shares no history with `main`, so a normal checkout does not contain it and
looking in the working tree always comes up empty. Every reader must:

```bash
git fetch origin card-feed
git show FETCH_HEAD:latest_status.json
git show FETCH_HEAD:latest_card_comment.md
```

The EPL routine's prompt shouts this because a live run *"fell through to a web
fetch and an unauthenticated clone that a private repo can only refuse. It read
as an access problem and was a branch problem."*

**`latest_status.json`:**

```json
{"date": "2027-01-12", "slate_date": "2027-01-12", "card_slot": "morning",
 "decision": "no-selections", "degraded": "false",
 "trigger": "schedule", "run_url": "https://github.com/..."}
```

`degraded` is the **string** `"true"` / `"false"` / `"unknown"`, and `"unknown"`
counts as degraded. `card_slot` exists because this lab publishes more than one
card a day and a single `date` cannot tell the morning card from the evening
refresh.

**Published with git plumbing only** — `hash-object`, `mktree`, `commit-tree`,
`push` — never a checkout and never `git add`. A `git add -A` on a working tree
holding a staged price file and a `.env` is how a credential reaches a ref.
`tests/test_workflows.py` pins every `git push` in every workflow to
`:refs/heads/card-feed`, because **GitHub cannot scope `contents: write` to a
ref and that test is the scope.**

### Two guards, and they are different

**Run-level, "already published?"** — gates the *backup* trigger. A manual
dispatch never skips; a degraded tip never satisfies it (that is exactly what
the backup exists for); and it fetches with an **authenticated** remote, because
on a private repo an unauthenticated fetch made the sibling's guard **fail
open** — it read "no card-feed branch yet", the backup never stood down, and
every game day fetched the slate twice and posted twice.

**Publish-level, the clobber guard** — skips publishing when all three hold: the
tip has the same `(date, card_slot)`, the tip's `degraded` is `"false"`, and
this run's `degraded` is not `"false"`. Gated behind a non-empty parent, so a
first-of-the-day failure still publishes and *"no commit for today"* still means
*"the run did not finish"*.

It exists because the feed is last-writer-wins under `if: always()`, and in the
EPL lab a late-firing trigger landed past the deadline and, firing last,
replaced a good card with a blocked one. **Comparing `date` alone would make the
evening refresh read as a clobber of the morning card**, so it compares
`(date, card_slot)`.

**Verified against a real git ref across all seven cases**, not by asserting on
strings in a YAML file — `tests/test_card_feed_publish_guard.py` builds a
scratch repository, creates a real `card-feed` ref with a crafted status file,
and runs the actual shell. The brief is explicit that *"string assertions about
shell logic in a workflow file are near-worthless."*

**Never publish the absence of evidence.** The publish runs `if: always()`, so a
run that died before the restore step holds no ledger. It carries the branch
copy forward instead, with a warning, rather than replacing a season of evidence
with a commit that omits it.

---

## Link 3 — `CBB CARD RELAY`, a Claude Code cloud routine

**It is a relay, not a reader.** It copies the card into Google Drive verbatim
and stops. It summarises nothing, sends nothing, and Cooper never reads its
output.

**One dated file per run.** The Drive connector's `update_file` changes title and
parent only, **not content**, so updating one file in place is not possible —
each run creates `CBB Card <date> <slot>`, and a re-run whose content is
byte-identical changes nothing.

**Cron: `37 9,15,16,22 * 11,12,1,2,3,4 *`** — four runs a day through the season
only. That is a **pair per slot**, and the pairing is the brief's rule that one
trigger cannot hold both the relay deadline and a freshness requirement:

| Run | Catches |
|:---|:---|
| 09:37 UTC | the morning workflow firing on time (card ready ~09:15) |
| 15:37 UTC | the morning workflow firing at the worst observed lateness (~15:18) |
| 16:37 UTC | the evening workflow firing on time |
| 22:37 UTC | the evening workflow at worst-case lateness (~22:18) |

Without the second of each pair, a late GitHub cron means no card that slot.
Without the first, an on-time card sits unread for six hours — and the morning
card exists precisely to precede an 11:00 ET tip.

---

## Link 4 — the chat-side scheduled task, and the one thing Cooper does

**A chat-side task cannot be created from Claude Code and cannot clone a private
repository.** That is why the relay exists at all: the reader can reach Google
Drive and cannot reach the repo. Establishing what the reader can actually access
before designing anything is the whole reason this chain has three links instead
of one.

This is **one paste**, and it is the only setup step Cooper performs. The prompt
is in the final report and in `docs/chat_task_prompt.md`.

---

## Zero email, both halves

1. The card comment **mentions nobody**. `tests/test_gameday_card.py` asserts no
   `@` handle appears.
2. The repository subscription is set to **ignored**.

An `@mention` overrides an ignored subscription, so putting one back into the
comment would resume the emails. Neither half is sufficient alone, and that is
recorded here because the EPL lab learned it by continuing to get email after
doing only one.

---

## Verifying the chain

**A green workflow run is not a delivered card.** The EPL lab spent five days
green and empty. The chain is verified end to end by reading the card that
actually lands in Drive — not by asserting that a step exited zero.

Order of verification, and each step must be observed rather than assumed:

1. The workflow run is green **and** `git show FETCH_HEAD:latest_card_comment.md`
   returns a card.
2. The relay run's final line names a Drive file.
3. That Drive file is opened and read, and its content is the card.
4. The chat task returns the card.
