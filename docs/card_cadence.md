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

## What the second slot actually buys, measured

**Not coverage.** Measured 2026-09-16 over the 6,300 played games of the
2025-26 schedule, against `schedule_contract`'s own landings and the
60-minute card lead the tip guard enforces:

| | morning slot alone can freeze | evening slot adds |
|:---|---:|---:|
| EST (freeze bar 10:30 ET) | **99.97%** | 0.00% |
| EDT (freeze bar 11:30 ET) | **99.41%** | 0.00% |

The morning run lands early enough to precede essentially every tip in the
season, so by TIP TIME a single slot reaches the whole slate. The evening slot
adds no games the morning could not have frozen.

What it buys is **price quality on late tips**. A game tipping at 23:00 ET
frozen from a board fetched at 10:30 ET is frozen twelve and a half hours out,
and "one freeze cannot price a noon tip and an eleven o'clock tip" is a claim
about the PRICE, not about reach.

**And that cost is currently unmeasured.** The bought card store cannot answer
it: every row carries `lead_minutes = 60`, so it holds one lead and says
nothing about what the board looked like that morning. `book_last_update` is no
help either — it sits ~1.08h before tip for every quote in all three tip
windows, which is the snapshot's own time showing through rather than price
stability. The instrument that WILL answer it is `line-movement.yml`, which
captures the board four times a day and holds nothing yet because it is the
off-season.

**Why this matters now.** It is the difference between "one snapshot a day is a
cheaper cadence" and "one snapshot a day is a smaller sample". It is the
former: the stopping rule's floor of 10,000 opinions across 2,000 games is
about reach, and reach is ~100% either way. The cost of halving the cadence is
worse prices on late games, of unknown size, measurable from November.

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

**A landing is not a deadline.** A run cannot freeze a game tipping inside
`schedule_contract.CARD_LEAD_MINUTES` — sixty minutes — of the moment it fires:
`gates.IMMINENT_MINUTES` **is** that constant, `gates.tip_state` calls such a
game `imminent`, and `reports/gameday_card.py._rows_to_freeze` drops it before
the rows reach the append-only store. So the figure that matters is the landing
plus the lead, and this table used to print the landing alone.

The season runs almost entirely in EST (UTC−5). Taking the worst observed
lateness of 5.3 hours, in EST:

| Slot | Nominal | Worst-case fire | In ET | Can freeze tips after | Against its block |
|:---|:---|:---|:---|:---|:---|
| `morning` primary | 09:00 UTC | 14:18 UTC | **09:18 ET** | 10:18 ET | clears the 11:00 ET first tip by 42 min |
| `morning` backup | 10:00 UTC | 15:18 UTC | **10:18 ET** | 11:18 ET | **misses the 11:00 ET first tip by 18 min** |
| `evening` primary | 16:00 UTC | 21:18 UTC | **16:18 ET** | 17:18 ET | clears the 19:00 ET block (55% of the slate) by 1h42 |
| `evening` backup | 17:00 UTC | 22:18 UTC | **17:18 ET** | 18:18 ET | clears the 19:00 ET block by 42 min |

**The morning backup does not cover its block, and this document said it did.**
The old fifth column read *"the 11:00 ET first tip, by 42 min"*, computed
against the 10:18 landing with no lead term — and 42 minutes is **inside** the
lab's own 60-minute guard, so the games that column claimed were covered are
exactly the ones the tip guard quarantines. `schedule_contract.holds()` had the
same omission, twenty-seven lines below the constant it omitted: it went red
only at 6.0 hours of lateness, while the honest bar was already violated at
5.0, and GitHub has been at 5.3 since 2026-08-27. The morning backup has
therefore never covered the 11:00 ET block at the lateness this repository is
built for.

At the *nominal* time every trigger lands five hours earlier and all four cover
their blocks with room, which is the ordinary case and costs nothing. The
column above is the degraded case, and for the morning backup the degraded case
is also the case where the primary was dropped — both have to go wrong before a
game is lost.

**From 2027-03-14 every figure above is an hour later, and two more cells stop
holding.** DST begins that day and the offset moves from UTC−5 to UTC−4. A cron
is fixed in UTC, so the same instant reads an hour *later* on an Eastern clock:
10:00 UTC is 05:00 EST on the 13th and 06:00 EDT on the 14th. An earlier
version of `schedule_contract.py` said the opposite — "earlier, the safe
direction" — and had the sign backwards. In EDT at 5.3 hours late the morning
primary lands 10:18 ET and so can freeze nothing tipping before 11:18, missing
the 11:00 ET first tip the EST version of it clears; the morning **backup**
lands **11:18 ET**, after the tip entirely; the evening primary lands 17:18 and
still clears the 19:00 ET block; the evening **backup** lands 18:18 and reaches
nothing before 19:18, so it too misses its block.

**Four cells in total, then, not one**, and this document recorded one of them:

| Cannot freeze its block | Lands | Can freeze tips after | Block |
|:---|:---|:---|:---|
| `morning` backup, EST | 10:18 ET | 11:18 ET | 11:00 ET |
| `morning` primary, EDT | 10:18 ET | 11:18 ET | 11:00 ET |
| `morning` backup, EDT | 11:18 ET | 12:18 ET | 11:00 ET |
| `evening` backup, EDT | 18:18 ET | 19:18 ET | 19:00 ET |

Those are recorded gaps, not moved crons. Each bites only when the primary was
dropped **and** GitHub is at its worst observed lateness **and** a game tips in
the first hour of the block — except the EST morning backup, which is the whole
season rather than the last three weeks of it. Closing the morning slot's EST
cell would mean moving its pair to 08:00/09:00 UTC and its EDT cells
07:00/08:00; closing the evening backup's EDT cell would mean 15:00/16:00. All
of that cards every day of the season an hour or two earlier, with that much
less information, to buy a handful of first-hour tips on the days the primary
also failed. `tests/test_the_card_schedule_survives_cron_lateness.py` pins the sign
on those two instants and **the whole set of four cells**, in both directions,
so the day the lateness constant or a cron changes, the record changes with it
or the build goes red. It also puts a landing and a block's first tip on one
real clock and asks `gates.tip_state` itself, which is the check that was
missing: the schedule and the guard had never been multiplied together, so a
contract claiming a slot covered its block and a guard quarantining every game
in it were both green at once.

**A slot that fires late has not failed.** The tip guard quarantines whatever
has already started, per game, and the run reports the coverage it achieved.
That is an honest partial card. What the schedule buys is that the partial case
is rare rather than routine.

`tests/test_the_card_schedule_survives_cron_lateness.py` computes this table
from `OBSERVED_LATENESS_H`, `CARD_LEAD_MINUTES` and the real schedule, and
fails if a slot's worst case stops being able to **freeze** its block — so
raising the lateness constant when GitHub gets worse is a one-line change that
proves itself. It used to check "precedes" rather than "can freeze", which is
the sixty minutes this page had to be rewritten for.

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

## Thirty-seven games a season cannot be carded, and that is stated rather than chased

**This section said three games and 0.05%, and the real figure is 37 and
0.59%.** Both halves of the old number were wrong, and they were wrong in
opposite directions, which is why nothing looked odd:

* The bar was taken as the morning backup's **landing**, 10:18 ET, rather than
  the earliest tip it can freeze, 11:18 ET. That is the missing card lead, and
  it is worth 35 games.
* The measurement behind it read the tip's **hour** and compared it to 10.3, so
  it was really asking "does this game tip before 11:00?". That over-counted by
  one: the third of the three games is VCU against Virginia Tech at **10:30
  ET** on 2025-11-28 — the Battle 4 Atlantis third-place game, on a neutral
  floor in Nassau — recorded here as "one at 10:00", and it tips *after* a
  10:18 landing. Two games tip before the landing, not three.

Measured to the minute on the completed 2025-26 season, 6,318 games: the
worst-late morning backup can freeze nothing tipping at or before **11:18 ET**,
and **37 games — 0.59% of the slate — tip at or before it**, spread one to
three at a time over 27 dates from 2025-11-03 to 2026-03-14. Thirty-four of the
37 are the 11:00 ET block itself, which is the block the morning slot exists to
precede.

**The 2026-27 season opener is one of them**: Notre Dame against Villanova at
the Palazzetto dello Sport in Rome, 09:30 ET on Sunday 2026-11-01. A single
game, and the season's first, which is exactly the kind of thing that looks like
a fault on the day and is not.

Moving the cron earlier to catch the rest would card the entire day earlier,
with less information, to buy a set of games that is only lost when the morning
primary was dropped as well. The football lab reached the same conclusion about
its six 09:30 ET international kickoffs — *"the real fix is per-game carding
rather than per-day, which is a design change and not a scheduling one"* — and
recorded it rather than chasing it. The tip guard quarantines these games
correctly, the run reports the coverage it achieved, and
`tests/test_the_card_schedule_survives_cron_lateness.py` now pins the measured
share against the schedule fixture rather than bounding it: the old assertion
was `< 0.001`, which the true 0.59% fails by six times, and the bound was **not
widened to accommodate it** — it was replaced by the number itself, which is
stricter in both directions and goes red the day the schedule constants move.

**It is a coverage gap, not a fault** — but it is 0.59%, and a gap recorded at
a twentieth of its size is not really recorded.

## The cadence, as of 2026-09-16: one slot

**The evening slot has no cron.** The balance does not carry two snapshots a
day through a season — 1,287,023 needed against 1,110,311 remaining once the
sibling labs' 36,175 a month is counted against the same balance, and the
balance does not reset. The measurement above is why that was an acceptable
trade rather than a cut: one slot still reaches the slate, so the stopping
rule's floor of 10,000 opinions across 2,000 games is still in range.

`schedule_contract.SCHEDULED_SLOTS` is the authority. `cron_expressions()`
derives from it, and
`test_the_gameday_workflow_crons_are_exactly_the_ones_the_contract_declares`
compares it against the workflow in both directions, so a cron that reappears
and a cron that silently disappears both fail. The morning **backup** stays:
dropping it is the quiet failure, because a workflow missing its backup looks
exactly like a healthy one until the primary is skipped.

The daily credit cap came down with the cadence, 40,000 to **20,000**. The day
it bounds is now one snapshot, and a cap left at twice the cadence would not
have bounded the day at all — it would have permitted the spend the schedule
was changed to avoid. 20,000 keeps the property the old number was chosen for:
above the worst night this sport has produced (19,206), by the same margin
40,000 left over 38,412.

**What this costs is price quality on late tips, and it is not yet measurable.**
A 23:00 ET game is now frozen off a board fetched twelve and a half hours
earlier. `line-movement.yml` captures the board four times a day and will
measure it from November; until then the cost is stated rather than known.

**The evening slot is still defined and still dispatchable by hand.** It is
what buying credit restores — two crons back — and deleting it would delete the
record of what was given up.
