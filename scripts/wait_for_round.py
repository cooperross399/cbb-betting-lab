#!/usr/bin/env python3
"""Hold a scheduled run until the round it was scheduled for.

    python3 scripts/wait_for_round.py --schedule "13 15 * * *" --budget-minutes 340

**A DELIBERATE COPY, NOT AN IMPORT.** This is the NHL lab's
`scripts/wait_for_round.py` (merged there in its PRs #276 and #278), ported by
copying because the labs share no code (`tests/test_no_sibling_lab_import.py`).
It is free to diverge, and it already has: the hand-started `--at` wait the
NHL copy carries is not ported, because nothing here dispatches a capture for
later. A run started by hand captures at once, as it always did.

WHY. GitHub starts this account's scheduled runs hours late. In this
repository since 2026-09-08, `line-movement.yml`'s crons ran a median 3.1 h
and at worst 6.6 h late, and the account-wide worst is 7.38 h
(`data/outputs/cbb_cron_lateness.json`). The captures exist to bracket the
hours a board moves, and the 23:13 UTC round is the one an hour before the
19:00 ET block, 55% of the slate. Three hours late it lands after that block
has tipped, and a quote captured after tip-off is no price at all. The 03:13
round, six hours late, lands after the whole night has finished. Lateness moves
by hours from day to day, so no cron time can be aimed at a round.

**The card uses it too, since 2026-09-29.** `cbb-gameday-refresh.yml` fires
each card cron :data:`ROUND_LEAD` before a fixed slot and waits here, before
its `already-published` guard, so the card lands at the slot rather than
wherever the lateness put it (decision 61). For the card a "round" is a slot,
and `schedule_contract.WAIT_LEAD_H` is held equal to :data:`ROUND_LEAD` by
`tests/test_the_card_schedule_survives_cron_lateness.py`.

So every cron fires :data:`ROUND_LEAD` before its round, and the run waits
here, before the capture, until the round. Lateness up to the lead then costs
nothing; beyond it, the run captures as soon as it starts, which is what every
run did before. A run is never held past its round and never captures early
because GitHub started it early.

A job may run for at most six hours, so the wait is split across two jobs,
each waiting at most `--budget-minutes`; the second picks up where the first
stopped, because the round is recomputed from the same cron each time.

The round is the most recent time the cron named, at or before now, plus
:data:`ROUND_LEAD`: a scheduled run always starts after its cron time, and
never a day late. Only the cron's minute and hour are read, so each must be a
single number. No schedule (a manual dispatch) means no wait. Nothing here
fetches, spends a credit or reads a secret.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone

#: How far before its round every Line Movement cron, and every card cron, fires. Covers the
#: account-wide worst lateness measured since 2026-08-27 on every day but the
#: first (7.38 h, a 06:00 UTC cron), and this workflow's own worst (6.58 h).
#: The two runs of 2026-08-27 (9.61 h and 9.85 h) are not covered; a run that
#: late captures 1-2 hours after its round, as every late run did before.
ROUND_LEAD = timedelta(hours=8)


def round_for(schedule: str, now: datetime) -> datetime:
    """The round a run fired by `schedule` is for."""
    fields = schedule.split()
    if len(fields) != 5:
        raise ValueError(f"not a five-field cron: {schedule!r}")
    minute, hour = int(fields[0]), int(fields[1])
    fired = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
    if fired > now:
        fired -= timedelta(days=1)
    return fired + ROUND_LEAD


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--schedule", default="", help="github.event.schedule")
    parser.add_argument("--budget-minutes", type=float, default=340.0)
    args = parser.parse_args(argv)

    if not args.schedule.strip():
        print("Started by hand: running now.")
        return 0
    now = datetime.now(timezone.utc)
    try:
        target = round_for(args.schedule, now)
    except ValueError as exc:
        print(f"::error::{exc}")
        return 2
    stamp = f"{target:%Y-%m-%d %H:%M} UTC"
    remaining = target - now
    if remaining <= timedelta(0):
        print(
            f"This round was due at {stamp}; the run started {-remaining} "
            "after it, so it runs now."
        )
        return 0
    wait = min(remaining, timedelta(minutes=args.budget_minutes))
    print(f"Round due at {stamp}; waiting {wait} of the {remaining} left.")
    sys.stdout.flush()
    time.sleep(wait.total_seconds())
    if wait < remaining:
        print("This job's budget is spent; the next wait job holds the rest.")
    else:
        print(f"Reached {stamp}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
