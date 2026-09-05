#!/usr/bin/env python3
"""The body for the `CBB CARD RELAY` cloud routine, ready to create.

    # Prints the body and the one blocker:
    python scripts/create_card_relay_routine.py

**This routine cannot be created until the Claude Code GitHub app is granted
access to `cooperross399/cbb-betting-lab`.** Creating it returns:

    HTTP 403 "You don't have access to a repository this routine uses."

The three sibling labs' routines work, and they name sibling repositories, so
the grant is per-repository and this repository is new. Nothing else in the
chain is blocked: the workflow publishes to `card-feed` on its own, and the
feed is readable by anything with repository access.

**The fix is one click and it is Cooper's**, because granting a GitHub app
access to a repository is an account permission that no token in this
environment can change (listing installations already returns 403 here):

    https://github.com/settings/installations
      -> Claude  ->  Repository access  ->  add `cbb-betting-lab`  ->  Save

Once that is done this file's body creates the routine unchanged. It is kept
as a script rather than as prose in a doc so that the thing which is blocked is
also the thing which unblocks, with no retyping.
"""

from __future__ import annotations

import json
import uuid

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

#: Four runs a day, season only, as a PAIR PER SLOT.
#:
#: GitHub has been firing these repositories' crons 4.5-5.3 hours late since
#: 2026-08-27, and one trigger cannot hold both the relay deadline and a
#: freshness requirement. So each slot gets a run for the on-time case and a
#: run for the worst observed lateness:
#:
#:   09:37 UTC  the morning workflow firing on time (card ready ~09:15)
#:   15:37 UTC  the morning workflow at worst observed lateness (~15:18)
#:   16:37 UTC  the evening workflow firing on time
#:   22:37 UTC  the evening workflow at worst observed lateness (~22:18)
#:
#: Without the second of each pair a late cron means no card that slot; without
#: the first, an on-time card sits unread for six hours — and the morning card
#: exists precisely to precede an 11:00 ET tip.
CRON = "37 9,15,16,22 * 11,12,1,2,3,4 *"

PROMPT = """You are a RELAY, not a reader. Your entire job is to copy the current college basketball card out of a repository and into Google Drive, where Cooper's "CBB CARD" scheduled task in the regular Claude app reads it. Cooper does not read your output; he reads that task. So do not summarise, interpret, rank, score, or comment on the card, do not send a push notification, and do not send an email. Copy it and stop.

The repository cooperross399/cbb-betting-lab is checked out for you. Never place a bet, never edit any repository file, never alter the card's content in any way.

CALENDAR: the 2026-27 D-I season runs 2026-11-01 to 2027-04-05. Outside that window, stop immediately with the single line "Offseason - no card."

STEP 1 - Read the card. The files live on the `card-feed` branch, which is an ORPHAN branch: none of them exists on the default branch you have checked out, and the two share no history, so looking in the working tree will ALWAYS come up empty. That failure reads like an access problem and is a branch problem. Fetch it explicitly:

    git fetch origin card-feed
    git show FETCH_HEAD:latest_status.json
    git show FETCH_HEAD:latest_card_comment.md

STEP 2 - Read `latest_status.json`. It carries `date`, `card_slot` (`morning` or `evening`), `decision`, `degraded` and `run_url`. THIS SPORT PUBLISHES MORE THAN ONE CARD A DAY: the slate spans twelve hours and 45% of games have not tipped at 19:00 ET, so the morning and evening cards are different cards for different games. The slot is part of the identity and must never be dropped.

STEP 3 - Write ONE Google Drive file with the Google Drive connector, using create_file:
  - title: "CBB Card <date> <slot>" using the `date` and `card_slot` fields verbatim, e.g. "CBB Card 2027-01-12 morning".
  - Search Drive first with `title contains 'CBB Card'`. If a file with that exact title already exists and the card text you just read is byte-identical to what it holds, stop and change nothing. If it differs, create "CBB Card <date> <slot> (updated HH:MM UTC)" so the newer one sorts after it. The connector's update_file changes title and parent only and NOT content, so a new file is the only way to record a change.
  - contentMimeType: "text/markdown", and set disableConversionToGoogleType to true.
  - textContent: the line `status: ` followed by the exact contents of latest_status.json on one line, then a blank line, then the ENTIRE contents of latest_card_comment.md, verbatim and unedited. Do not trim tables, drop sections, reorder anything, or reformat.

STEP 4 - Your final message is ONE line: the title you wrote and its Drive link, or, if the fetch failed, the single sentence "The card could not be read from card-feed this run." Nothing else. Do not restate the card. Do not describe it as missing, blocked, stale or late - a read failure here is about this session's access and says NOTHING about the pipeline, and `degraded` in the status file is the pipeline's own report of itself, which you relay rather than interpret.

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
