#!/usr/bin/env python3
"""The body for the `CBB CARD RELAY` cloud routine, ready to create.

    PYTHONPATH=src python scripts/create_card_relay_routine.py

**The routine exists**: `trig_013PaobEWhpXv7vwN3wVxEXS`, created 2026-09-04
once Cooper granted the Claude GitHub app access to this repository (creating
it before that returned `HTTP 403 "You don't have access to a repository this
routine uses."`; a revoked grant is restored at
`https://github.com/settings/installations` -> Claude -> Repository access).

**This file does not change the live routine, and the live routine does not
read this file.** They drifted once already: the live prompt gained the Drive
search and read-back steps on 2026-09-05 and this copy kept the old four
steps until 2026-09-25, when it was re-read from the live routine. Updating the
routine is a separate, deliberate act, and a routine update REPLACES
`job_config.ccr` wholesale — so a prompt change starts from the live `ccr`, not
from a hand-built one. The cron is a top-level field and can be updated alone.

Its cron comes from `schedule_contract.relay_cron_expression()`, which the
tests hold to both ends of the chain.
"""

from __future__ import annotations

import json
import uuid

from cbb_betting_lab.schedule_contract import relay_cron_expression

#: Read off the working `EPL CARD RELAY` routine rather than guessed. Reusing
#: the connector Cooper already authorised is the difference between a routine
#: that works on its first fire and one that asks him for a second thing.
GOOGLE_DRIVE = {
    "connector_uuid": "9b7b2ec6-7435-4960-947c-64783b6d5d5d",
    "name": "Google_Drive",
    "url": "https://drivemcp.googleapis.com/mcp/v1",
    "transport_type": "http",
    "permitted_tools": [],
    "tool_policy_overrides": [],
    "clear_tool_policy_overrides": False,
}

ENVIRONMENT_ID = "env_01K3AkKFBnT5QXEA8EZ3SDGN"

#: Three runs a day, season only, on the READERS' clock:
#: `CRON_TZ=America/New_York 52 3,10,17 * 11,12,1,2,3,4 *`.
#:
#:   03:52 ET  the morning card when GitHub fires on time
#:   10:52 ET  the morning card at worst lateness, and the evening card on time
#:   17:52 ET  the evening card at worst lateness
#:
#: It was `37 9,15,16,22 * 11,12,1,2,3,4 *` — fixed in UTC, sized for 5.3 hours
#: of lateness, and checked in EST only. From 2027-03-14 its two late runs would
#: have been 11:37 and 18:37 EDT, after both of Cooper's reads (11:15 and 18:15
#: ET) for the whole tournament. The reasons for each hour, and the budgets they
#: rest on, are in `schedule_contract`.
CRON = relay_cron_expression()

PROMPT = """You are a RELAY, not a reader. Your entire job is to copy the current college basketball card out of a repository and into Google Drive, where Cooper's "CBB CARD" scheduled task in the regular Claude app reads it. Cooper does not read your output; he reads that task. So do not summarise, interpret, rank, score, or comment on the card, do not send a push notification, and do not send an email. Copy it and stop.

The repository cooperross399/cbb-betting-lab is checked out for you. Never place a bet, never edit any repository file, never alter the card's content in any way.

CALENDAR: the 2026-27 D-I season runs 2026-11-01 to 2027-04-05. Outside that window, stop immediately with the single line "Offseason - no card."

STEP 1 - Read the card. The files live on the `card-feed` branch, which is an ORPHAN branch: none of them exists on the default branch you have checked out, and the two share no history, so looking in the working tree will ALWAYS come up empty. That failure reads like an access problem and is a branch problem. Fetch it explicitly:

    git fetch origin card-feed
    git show FETCH_HEAD:latest_status.json
    git show FETCH_HEAD:latest_card_comment.md

STEP 2 - Read `latest_status.json`. It carries `date`, `card_slot` (`morning` or `evening`), `decision`, `degraded` and `run_url`. THIS SPORT PUBLISHES MORE THAN ONE CARD A DAY: the slate spans twelve hours and 55% of games have not tipped at 19:00 ET, so the morning and evening cards are different cards for different games. The slot is part of the identity and must never be dropped.

STEP 3 - Decide whether this card is already relayed. Search Drive with `title contains 'CBB Card'`, then **DO NOT TRUST THAT SEARCH** and filter what it returns yourself. Two properties of Drive search were measured on 2026-09-05 in the sibling NHL lab, on a real file, and both will mislead you here:

  a) The `contains` operator TOKEN-matches rather than substring-matches. A file titled "NHL RELAY VERIFICATION 2026-09-05 - not a card" matched `title contains 'NHL Card'` while never holding that phrase, because the title carries "NHL" and "card" as separate words. So keep ONLY files whose title is exactly `CBB Card <date> <slot>` or begins with `CBB Card <date> <slot> (updated`. Anything else is not a card, whatever the search returned. **This bites harder here than in any other lab**, because the slot means two legitimate cards a day differ only in their last word: `CBB Card 2027-01-12 morning` and `CBB Card 2027-01-12 evening` are one token apart, so a date-only filter collapses them and the evening card looks already published.

  b) The search index is EVENTUALLY CONSISTENT. A rename took about two minutes to appear in results, so an empty result does not prove a file is absent. If your filtered search finds nothing for this date and slot, do NOT conclude it is absent on one look. Search THREE TIMES IN TOTAL, doing other useful work between them - assemble the text you are about to write, count its bytes, prepare the read-back comparison - and only then conclude.

     DO NOT write a fixed-period wait, and do not reach for `sleep`. A standalone `sleep 60` is BLOCKED in this sandbox, and the obvious workaround fails SILENTLY: backgrounding it and running `wait <id>` on the returned id returns instantly, because that is a harness task id and not a shell job. A live run on 2026-09-05 did exactly that, turned a 60-second retry into 14 seconds, and reported having waited. That is the trap worth naming: a nonexistent flag ERRORS, but a wait that does not wait SUCCEEDS. Counting searches cannot be defeated that way, which is why this rule is a count and not a duration.

If the card is still absent after those three searches, proceed and write - a duplicate is a far smaller harm than a missing card. If a file titled exactly `CBB Card <date> <slot>` already exists and the card text you just read is byte-identical to what it holds, stop and change nothing. If it differs, create "CBB Card <date> <slot> (updated HH:MM UTC)" so the newer one sorts after it. The connector's update_file changes title and parent only and NOT content, so a new file is the only way to record a change.

STEP 4 - Write ONE Google Drive file with the Google Drive connector, using create_file:
  - title: "CBB Card <date> <slot>" using the `date` and `card_slot` fields verbatim, e.g. "CBB Card 2027-01-12 morning".
  - contentMimeType: "text/markdown", and set disableConversionToGoogleType to true.
  - textContent: the line `status: ` followed by the exact contents of latest_status.json on one line, then a blank line, then the ENTIRE contents of latest_card_comment.md, verbatim and unedited. Do not trim tables, drop sections, reorder anything, or reformat.

STEP 5 - Confirm the bytes landed. `create_file` returning success is not evidence that they did; that is the same mistake as trusting a green CI run. Read the file back with `download_file_content`, which returns base64 of the real stored bytes, decode it, and compare against what you wrote. Do NOT use `read_file_content` for this check: it returns a markdown-rendered representation that escapes underscores and appends trailing double-spaces, so a perfectly correct file will look corrupted and you will report a fault that does not exist.

STEP 6 - Your final message is ONE line: the title you wrote and its Drive link, or, if the fetch failed, the single sentence "The card could not be read from card-feed this run." Nothing else. Do not restate the card. Do not describe it as missing, blocked, stale or late - a read failure here is about this session's access and says NOTHING about the pipeline, and `degraded` in the status file is the pipeline's own report of itself, which you relay rather than interpret. If the read-back in step 5 did not match, say THAT in your one line instead, because a silently truncated card is worse than an absent one.

Housekeeping: never delete anything from Drive."""


def body() -> dict:
    return {
        "name": "CBB CARD RELAY",
        "cron_expression": CRON,
        "enabled": True,
        "mcp_connections": [GOOGLE_DRIVE],
        "job_config": {
            "ccr": {
                "environment_id": ENVIRONMENT_ID,
                "session_context": {
                    "model": "claude-sonnet-5",
                    "sources": [
                        {"git_repository": {
                            "url": "https://github.com/cooperross399/cbb-betting-lab"
                        }}
                    ],
                    # Read-only by intent. A relay that can Write or Edit is a
                    # relay that can alter the card it is copying.
                    "allowed_tools": [
                        "preset:default", "Bash", "Glob", "Grep", "Read",
                        "WebFetch", "TodoWrite",
                    ],
                },
                "events": [{"data": {
                    "uuid": str(uuid.uuid4()),
                    "session_id": "",
                    "type": "user",
                    "parent_tool_use_id": None,
                    "message": {"role": "user", "content": PROMPT},
                }}],
            }
        },
    }


if __name__ == "__main__":
    print(json.dumps(body(), indent=2))
