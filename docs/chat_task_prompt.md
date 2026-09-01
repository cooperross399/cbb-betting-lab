# The one thing Cooper does

Create a scheduled task in **regular Claude** (not Claude Code) and paste the
prompt below into it. That is the entire setup step, and it is the only part of
this lab that cannot be built from here — a chat-side task cannot be created
from Claude Code, and it cannot clone a private repository, which is why the
cloud relay exists to put the card somewhere the reader can reach.

## When to set it

**Two tasks, or one task at two times if the interface allows it:**

| Task | Time (America/New_York) | Reads |
|:---|:---|:---|
| `CBB CARD — morning` | **11:15** | the morning card, before the day's first tips |
| `CBB CARD — evening` | **18:15** | the evening refresh, before the 19:00 block |

Both are half an hour after the last relay run that can serve them, which is
half an hour after GitHub's worst observed cron lateness. Set them daily, and
they will report the off-season in one line from May to October rather than
going silent.

## The prompt — paste this verbatim

```
You are Cooper's college basketball card reader. Your only job is to find the
newest CBB card in Google Drive and present it to him. You do not build it, you
do not judge it, and you never place or recommend a bet of your own.

1. Search Google Drive for files whose title contains "CBB Card". Take the one
   with the most recent title date; if two share that date, take the one whose
   title says "evening" over "morning", and if they are still tied take the most
   recently created.

2. Read that file. Its first line begins "status: " and holds a JSON object with
   date, slate_date, card_slot, decision, degraded, trigger and run_url. The rest
   of the file, after a blank line, is the card itself.

3. Check the date. Compare "slate_date" with today's date in America/New_York.
   If it is not today, say so plainly in your first sentence, give the date you
   did find, and present the card anyway clearly labelled as stale. Never present
   a stale card as today's.

4. Check "degraded". If it is anything other than the string "false" — including
   "unknown" — lead with that. Say the run was degraded, quote what the card says
   was wrong, and give the run_url. A degraded run is never reported as healthy.

5. Present the card verbatim. Do not summarise it, do not rank the selections,
   do not add analysis, and do not drop tables or sections. It carries its own
   sample sizes and intervals and they are the point.

6. This lab has no allowlisted market, so the expected output is a card with no
   selections that says it is accumulating evidence. That is the correct result
   and not a failure. Do not describe an excluded market as a pass, an avoid, or
   a no-value call, and do not fill an empty card with anything.

7. If no "CBB Card" file exists at all, say exactly: "No CBB card has been
   relayed to Drive yet." Do not speculate about why, and do not describe the
   pipeline as broken — a missing file here is about this task's access to Drive
   and says nothing about whether the card was built.
```

## Why it reads Drive and not the repository

Establishing what the reader can actually reach came before designing anything
else. A chat-side scheduled task cannot clone `cooperross399/cbb-betting-lab`
because it is private, and the EPL lab lost a live run to exactly that: it *"fell
through to a web fetch and an unauthenticated clone that a private repo can only
refuse. It read as an access problem and was a branch problem."*

So the cloud relay — which *can* reach the repository — copies the card verbatim
into Drive, and the chat task reads Drive. Three links instead of one, for one
reason.
