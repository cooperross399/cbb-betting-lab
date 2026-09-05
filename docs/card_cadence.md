# Why this lab publishes more than one card a day

**Measured from the completed 2025-26 season, 6,318 games.** Cooper's brief item
7: *"A noon tip and an 11pm tip cannot share one freeze."* This document is the
arithmetic behind that sentence and the schedule it produces.

## The slate's shape

| Tipped by | Share | Games |
|---:|---:|---:|
| 12:00 ET | 0.7% | 45 |
| 14:00 ET | 9.5% | 599 |
| 16:00 ET | 24.8% | 1,569 |
| 19:00 ET | 45.3% | 2,862 |
| 21:00 ET | 84.5% | 5,338 |
| 23:00 ET | 98.4% | 6,218 |

First tip 11:00 ET, last tip 23:00 ET, and one Hawai'i game at 01:00 ET. **The
slate spans twelve hours.**

A single freeze at 09:00 ET would price the 23:00 ET games fourteen hours out —
before the board is meaningfully formed for most of them, and long before any
number a human could act on. A single freeze at 17:00 ET would arrive after a
quarter of the night had already tipped, and the tip guard would correctly
quarantine every one of those games, which is a coverage hole rather than a
result.

## The rule that makes two cards safe

**The first opinion of the day for a given game is never retroactively
replaced.** A later run may add games the earlier run did not freeze; it may
never re-price one it did.

Without that rule, two cards a day is two bites at the same apple: the evening
run would reprice the games the morning run got wrong and the ledger would
record the better of two guesses. `forward_evidence.write_snapshot` is
append-only *within* a day, keyed on the frozen selection key, and that is what
enforces it.

## The slots

Two, each with a **trigger pair** — a primary and a backup an hour apart — and
the backup stands down when the primary has already published that slot cleanly.

| Slot | Nominal crons (UTC) | Freezes |
|:---|:---|:---|
| `morning` | 09:00, 10:00 | every cardable game tipping at least 60 minutes after the run |
| `evening` | 16:00, 17:00 | every cardable game **not already frozen today** and tipping at least 60 minutes after the run |

## The lateness arithmetic, which is why those hours and not later ones

**Do not trust the nominal cron time.** GitHub has been firing Cooper's repos'
crons **4.5 to 5.3 hours late since 2026-08-27**. Every deadline here is checked
against `nominal + OBSERVED_LATENESS_H`, not against nominal.

The season runs almost entirely in EST (UTC−5). Taking the worst observed
lateness of 5.3 hours, in EST:

| Slot | Nominal | Worst-case fire | In ET | Precedes |
|:---|:---|:---|:---|:---|
| `morning` primary | 09:00 UTC | 14:18 UTC | **09:18 ET** | the 11:00 ET first tip, by 1h42 |
| `morning` backup | 10:00 UTC | 15:18 UTC | **10:18 ET** | the 11:00 ET first tip, by 42 min |
| `evening` primary | 16:00 UTC | 21:18 UTC | **16:18 ET** | the 19:00 ET block (55% of the slate), by 2h42 |
| `evening` backup | 17:00 UTC | 22:18 UTC | **17:18 ET** | the 19:00 ET block, by 1h42 |

Even at maximum observed lateness, both slots land before the games they exist
to cover. At the *nominal* time they land hours earlier, which is the ordinary
case and costs nothing.

**From 2027-03-14 every figure above is an hour later, and one of them stops
holding.** DST begins that day and the offset moves from UTC−5 to UTC−4. A cron
is fixed in UTC, so the same instant reads an hour *later* on an Eastern clock:
10:00 UTC is 05:00 EST on the 13th and 06:00 EDT on the 14th. An earlier
version of `schedule_contract.py` said the opposite — "earlier, the safe
direction" — and had the sign backwards. In EDT at 5.3 hours late the morning
primary lands 10:18 ET and still precedes the 11:00 ET first tip; the morning
**backup** lands **11:18 ET**, 18 minutes after it; the evening pair land 17:18
and 18:18 ET and still precede the 19:00 ET block. That is a recorded gap, not
a moved cron. It bites only when the primary was dropped **and** GitHub is at
its worst observed lateness **and** a game tips at 11:00 ET, in the last three
weeks of the season; moving the crons an hour earlier for it would card every
day of the season earlier, with less information.
`tests/test_the_card_schedule_survives_cron_lateness.py` pins the sign on those
two instants and the gap as written, so the day the lateness constant changes,
the record changes with it or the build goes red.

**A slot that fires late has not failed.** The tip guard quarantines whatever
has already started, per game, and the run reports the coverage it achieved.
That is an honest partial card. What the schedule buys is that the partial case
is rare rather than routine.

`tests/test_the_card_schedule_survives_cron_lateness.py` computes this table
from `OBSERVED_LATENESS_H` and the real schedule and fails if a slot's worst
case stops preceding its block — so raising the lateness constant when GitHub
gets worse is a one-line change that proves itself.

**And the crons themselves are pinned, which they were not.** This document
used to say the test went red *"the day the crons move"*. Nothing read the
workflow: every check here computed its table from `schedule_contract` and none
of them had ever opened `.github/workflows/cbb-gameday-refresh.yml`, so a cron
moved in the workflow left the module, this document and the whole test file
agreeing with each other about a schedule the repository no longer ran — the
arithmetic still correct, the prose still confident, and the thing being
described somewhere else. `schedule_contract.cron_expressions()` now derives
the four cron strings from the slots, `SEASON_CRON_MONTHS` holds the month
field the slots never carried, and
`test_the_gameday_workflow_crons_are_exactly_the_ones_the_contract_declares`
compares them against the workflow's parsed `on.schedule` — in both directions,
because a workflow that has *dropped* its backup trigger looks exactly like a
healthy one until the primary is skipped.

## What the second card is not

It is not a second opinion, it is not a correction, and it is not a chance to
improve on the morning. It exists because 55% of the slate had not been priced
by anybody at 09:00 ET, and for no other reason.

## Three games a season cannot be carded, and that is stated rather than chased

The morning slot's backup lands at **10:18 ET** at worst-case lateness. Three
games in the whole 2025-26 season tip before that — one at 01:00 ET in Honolulu,
one at 08:00 and one at 10:00. **0.05% of the slate.**

**The 2026-27 season opener is one of them**: Notre Dame against Villanova at
the Palazzetto dello Sport in Rome, 09:30 ET on Sunday 2026-11-01. A single
game, and the season's first, which is exactly the kind of thing that looks like
a fault on the day and is not.

Moving the cron earlier to catch it would card the entire day earlier, with less
information, to buy three games. The football lab reached the same conclusion
about its six 09:30 ET international kickoffs — *"the real fix is per-game
carding rather than per-day, which is a design change and not a scheduling
one"* — and recorded it rather than chasing it. The tip guard quarantines these
games correctly, the run reports the coverage it achieved, and
`tests/test_the_card_schedule_survives_cron_lateness.py` fails if the
uncardable share ever stops being a handful.

**It is a coverage gap, not a fault.**
