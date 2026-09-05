"""The card's schedule, and the cron lateness it has to survive.

Cooper, 2026-08-31: *"Do not trust the nominal cron time. GitHub has been firing
my repos' crons 4.5-5.3 hours late since 2026-08-27. Check every deadline
against `nominal + OBSERVED_LATENESS_H`."*

This module holds those constants in one place so the workflow, the docs and
the test that proves the schedule works all read the same numbers. Raising
:data:`OBSERVED_LATENESS_H` when GitHub gets worse is a one-line change that
proves itself, because the test recomputes the whole table from it.

The reasoning is in `docs/card_cadence.md`.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Worst lateness observed on Cooper's repositories since 2026-08-27, in hours.
#: Measured, not documented behaviour. Every deadline is checked against
#: `nominal + this`, never against nominal.
OBSERVED_LATENESS_H = 5.3

#: Eastern standard time offset. The college basketball season runs almost
#: entirely in EST; DST begins 2027-03-14, near the end, and moves every landing
#: an hour *earlier* in ET, which is the safe direction.
EST_OFFSET_H = -5

#: A game tipping inside this many minutes of a run is not carded by it.
#: This is the lead the historical store was bought at (T-60,
#: `providers.historical.CARD_WINDOW`) and so the lead every measured number
#: rests on. `gates.IMMINENT_MINUTES` **is** this constant — it imports it —
#: so the per-game tip guard and the schedule read one number. They used to be
#: two (15 and 60), and a game tipping in 16-59 minutes could be selected at a
#: price no measurement ever covered. This module imports nothing from `gates`,
#: which is what keeps that import acyclic.
CARD_LEAD_MINUTES = 60


@dataclass(frozen=True)
class CardSlot:
    """One publishing slot: when it nominally fires and what it must precede."""

    name: str
    #: Nominal cron hours in UTC. Two of them: a primary and a backup an hour
    #: later, where the backup stands down if the primary published cleanly.
    cron_hours_utc: tuple[int, ...]
    #: The ET hour this slot's games start at. The slot must land before it even
    #: at worst-case lateness.
    must_precede_et_hour: int
    what: str

    def worst_case_landing_et(self) -> float:
        """The latest ET hour this slot can land, at observed worst lateness."""
        primary = min(self.cron_hours_utc)
        return (primary + OBSERVED_LATENESS_H + EST_OFFSET_H) % 24

    def backup_worst_case_landing_et(self) -> float:
        backup = max(self.cron_hours_utc)
        return (backup + OBSERVED_LATENESS_H + EST_OFFSET_H) % 24

    def holds(self) -> bool:
        """True when even the backup trigger lands before its block starts."""
        return self.backup_worst_case_landing_et() < self.must_precede_et_hour


#: 11:00 ET is the earliest tip in a full season (3 games); 12:00 ET is the
#: earliest with meaningful volume. The morning slot is held to 11:00.
MORNING = CardSlot(
    name="morning",
    cron_hours_utc=(9, 10),
    must_precede_et_hour=11,
    what="every cardable game tipping at least an hour after the run",
)

#: 45.3% of the slate has tipped by 19:00 ET and 84.5% by 21:00. The evening
#: slot exists for the 55% the morning card priced fourteen hours out or not at
#: all, and is held to the 19:00 ET block.
EVENING = CardSlot(
    name="evening",
    cron_hours_utc=(16, 17),
    must_precede_et_hour=19,
    what="every cardable game not already frozen today, tipping at least an "
         "hour after the run",
)

SLOTS: tuple[CardSlot, ...] = (MORNING, EVENING)
SLOT_NAMES: tuple[str, ...] = tuple(s.name for s in SLOTS)


def slot_for(name: str) -> CardSlot:
    for slot in SLOTS:
        if slot.name == str(name):
            return slot
    raise KeyError(f"Unknown card slot {name!r}. Known: {SLOT_NAMES}")
