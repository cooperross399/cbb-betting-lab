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
60-minute card lead the tip guard enforces. Re-taken for the fixed slots of
2026-09-29, with the morning backup's bar (slot + 20-minute run + lead):

| | morning slot alone can freeze | evening slot adds |
|:---|---:|---:|
| EST (freeze bar 09:20 ET) | **99.97%** | 0.00% |
| EDT (freeze bar 10:20 ET) | **99.97%** | 0.00% |

(Under the lateness-driven crons the EDT bar was 11:24 ET and the share
99.41%.) The morning run lands early enough to precede essentially every tip in
the season, so by TIP TIME a single slot reaches the whole slate. The evening
slot adds no games the morning could not have frozen.

What it buys is **price quality on late tips**. A game tipping at 23:00 ET
frozen from a board fetched at 07:00 ET is frozen sixteen hours out,
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

**Why this matters.** It is the difference between "one snapshot a day is a
cheaper cadence" and "one snapshot a day is a smaller sample". It is the
former: the stopping rule's floor of 10,000 opinions across 2,000 games is
about reach, and reach is ~100% either way. The cost of halving the cadence is
worse prices on late games, of unknown size, measurable from November.

**The lab runs TWO slots.** This measurement was taken while deciding whether
to halve the cadence for credit reasons; the card was dropped to one slot on
2026-09-16 and put back the same day, because the premise behind it — that the
provider balance never refills — was wrong and `docs/credit_cost.md` now says
so. The measurement stands on its own: it is what the second slot buys, and the
answer is price quality on late tips rather than reach. It is kept because the
question returns whenever the budget is tight, and the answer should not have
to be re-derived under pressure.

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
**Since 2026-09-29 each lands at a fixed time**: its cron fires eight hours
before the slot and the run waits for it (decision 61).

| Slot | Lands (UTC) | EST | EDT | Crons (UTC) | Freezes |
|:---|:---|:---|:---|:---|:---|
| `morning` | 12:00, 13:00 | 07:00, 08:00 | 08:00, 09:00 | 04:00, 05:00 | every cardable game tipping at least 60 minutes after the run |
| `evening` | 20:00, 21:00 | 15:00, 16:00 | 16:00, 17:00 | 12:00, 13:00 | every cardable game **not already frozen today** and tipping at least 60 minutes after the run |

The crons were 07:00/08:00 and 14:00/15:00 UTC from 2026-09-25 to 09-29, with
no wait, and 09:00/10:00 and 16:00/17:00 before that.

## The lateness, and why the card now waits for it

**Do not trust the nominal cron time.** `schedule_contract.OBSERVED_LATENESS_H`
is **7.4 hours**, held to `data/outputs/cbb_cron_lateness.json`: 565 scheduled
runs across Cooper's six repositories, 7.38 hours at worst on every day since
2026-08-27 but the first, when EPL's two Thursday crons ran 9.61 and 9.85 hours
late (`docs/decision_log.md` #57).

**Until 2026-09-29 the card rode it.** Its crons were set early enough that a
landing anywhere from nominal to nominal + 7.4h still froze its block and
reached the relay — which meant a card landed anywhere in a seven-hour window,
the evening card priced the 19:00 ET block seven to ten hours out, and four
slot/offset/trigger cells could not freeze their block at worst lateness (the
morning backup in EST, both morning triggers and the evening backup in EDT).
Those four were recorded rather than closed.

**Now it absorbs it.** Each cron fires `WAIT_LEAD_H` — eight hours — before its
slot, and the workflow's `wait` and `wait-more` jobs hold the run until the
slot, exactly as `line-movement.yml` does since #103. Any lateness up to eight
hours lands the card on its slot; beyond eight the run starts late and goes at
once, which is what every run did before. The slots then only have to satisfy
constraints that do not move with GitHub.

**A landing is not a deadline.** A run cannot freeze a game tipping inside
`schedule_contract.CARD_LEAD_MINUTES` — sixty minutes — of the moment it runs:
`gates.IMMINENT_MINUTES` **is** that constant and `_rows_to_freeze` drops such a
game before it reaches the append-only store. Every bar below is the slot, plus
the whole 20-minute run allowance (the freeze happens somewhere inside it),
plus that lead.

## Why these hours: the latest whose backup freezes its block AND reaches Cooper

A cron is fixed in UTC, so under EDT (from 2027-03-14, and in the first week of
any season whose first Sunday of November falls after the 1st) every slot reads
an hour LATER on an Eastern clock. EDT is therefore the offset that binds. Each
slot is the latest whole hour whose **backup**, under EDT, satisfies both:

* it can **freeze** its block's first tip: slot + 20 min + 60 min before it;
* it is **on `card-feed` before the relay run that carries it**, with margin.
  The relay (`CBB CARD RELAY`, `CRON_TZ=America/New_York 52 3,10,17`) is
  Cooper's routine and was not moved; the chat tasks read Drive at 11:15 and
  18:15 ET.

| Trigger | Lands EST / EDT | On `card-feed` by (EDT) | Freezes tips after (EDT) | Block | Relay |
|:---|:---|:---|:---|:---|:---|
| `morning` primary, 12:00 UTC | 07:00 / 08:00 | 08:20 | 09:20 | 11:00 | 10:52 |
| `morning` backup, 13:00 UTC | 08:00 / 09:00 | 09:20 | 10:20 | 11:00 | 10:52 |
| `evening` primary, 20:00 UTC | 15:00 / 16:00 | 16:20 | 17:20 | 19:00 | 17:52 |
| `evening` backup, 21:00 UTC | 16:00 / 17:00 | **17:20** | 18:20 | 19:00 | 17:52 |

One hour later fails each pair: a 14:00 UTC morning backup is 10:00 EDT and
can freeze nothing before 11:20; a 22:00 UTC evening backup is 18:00 EDT, on
the feed after the 17:52 relay and the 18:15 read. The tightest cell is the
evening backup under EDT, 32 minutes clear of its relay run.

**The trade that was made.** Letting only the primaries hold would have bought
one more hour of price on every card — 13:00 and 21:00 UTC primaries — at the
cost of backups that miss their block and their relay under EDT, which is the
whole NCAA tournament. The backup exists for the day the primary is dropped,
and a backup that cannot deliver on the season's most-watched days is not one.

**What the move buys.** The evening card prices the 19:00 ET block **four hours
out in EST and three in EDT**, every day, instead of anything from seven to
ten. The morning card lands at 07:00 EST, after the previous night is final
(including the 01:00 ET Honolulu game), so settlement is always complete. All
four cells that could not freeze their block now can.

**Beyond eight hours** the card is late but not lost: each primary still
freezes its block and reaches its relay up to about 9h30m late under EDT (9h39m
morning, 9h32m evening), and more in EST. A repeat of the 9.85-hour day of
2026-08-27 would put the evening card on the feed after the 17:52 relay under
EDT. That is recorded, not chased.

**The season's first day needs no special cron.** Every slot is at or after
12:00 UTC, so every cron fires on its slot's own UTC date and the 1 November
slot's cron fires on 1 November, inside the season's month field.
`schedule_contract.cron_hour_for` refuses any slot before 08:00 UTC, whose cron
would fall on 31 October and leave the season without its first card.

`tests/test_the_card_schedule_survives_cron_lateness.py` pins all of it: cron +
lead = slot for every cron the workflow declares; the wait script releasing
every cron's run at its slot for any lateness up to the lead; both triggers of
both slots freezing their block (asked of `gates.tip_state` on real Eastern
instants) and reaching their relay run in EST and EDT; that no later hour
holds; the season's first and last days; the slot name each cron publishes as;
and the job chain, its explicit conditions and the job-level concurrency group.

## What the second card is not

It is not a second opinion, it is not a correction, and it is not a chance to
improve on the morning. It exists because 55% of the slate had not been priced
by anybody at 09:00 ET, and for no other reason.

## Two games a season tip before the morning backup can freeze them

**This section said thirty-seven games and 0.59% until 2026-09-29.** Under the
lateness-driven crons the worst-late morning backup could freeze nothing tipping
at or before 11:24 ET, and 37 games of the completed 2025-26 season, 34 of them
the 11:00 ET block, tipped at or before that. One of them was the 2026-27
opener: Notre Dame against Villanova in Rome, 09:30 ET on 2026-11-01.

With the fixed slots the morning backup's bar is **09:20 EST / 10:20 EDT**, and
measured to the minute on the same 6,318 games **two** tip at or before it: a
08:00 ET neutral-site game on 2025-11-03, and the Honolulu game at 01:00 ET on
2025-11-10, which a time-of-day bar counts although it belongs to the previous
night's slate and the evening card prices it. The Rome opener is frozen by both
morning triggers: the slot lands 07:00 EST that morning, DST having ended at
06:00 UTC. `tests/test_the_card_schedule_survives_cron_lateness.py` pins the two
by date and time rather than bounding a share.
