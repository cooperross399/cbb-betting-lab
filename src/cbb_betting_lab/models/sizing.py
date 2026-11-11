"""How big a selection is, by how far the model has earned trust (decision 87).

Cooper, 2026-11-08 (*"DO all 7"*, item 4). Every selection used to read the
same size. The trust table (`models/trust.py`) already says, per tier, how much
of the model's disagreement with the price has been realised: 0 in a tier where
the card is price shopping against the fair price, up to 1 where the model's
view is worth its whole disagreement. The size follows it:

    size = BASE_UNITS * (1 + trust weight), rounded to STEP, at most MAX_UNITS

so a tier trusted at zero is the base 0.25u, and only a tier whose own settled
record has earned trust is sized up, never past 0.5u. No trust table, or a tier
it does not name, is the base size: the fail-safe direction.

**A long price is sized by its price, not by trust (decision 97).** Cooper,
2026-11-11: *"Use the same unit price ranges for cbb that we do for the NHL due
list"*, *".25u,.15u,.1u,.05u"*. The NHL lab's Due List ladder
(`PROP_STAKE_BRACKETS` there, copied here, not imported): up to +199 the size
above; +200 to +500 is 0.15u, +501 to +1500 is 0.1u, longer than +1500 is
0.05u. The same ladder counts every tracked bet on the site
(`web/site_pages.tracked_stake`), so the card and the record agree.

This is a column on the card and nothing else. **The site's tracker counts
every bet at 0.25u (to win 0.25u on a minus price) up to +199, by Cooper's
rule of 2026-11-04, and at the price ladder above from +200**, so the record
reads the same whatever trust says. Nothing here is a bet: this lab never places
one. Registered as `trust_sizing_2026_11_08`, one per tier.
"""

from __future__ import annotations

BASE_UNITS = 0.25
MAX_UNITS = 0.5
STEP = 0.05
#: (longest price in the bracket, size); longer than the last is LONGEST_UNITS.
#: The NHL lab's Due List ladder, Cooper 2026-11-11.
PRICE_BRACKETS: tuple[tuple[int, float], ...] = ((500, 0.15), (1500, 0.1))
LONGEST_UNITS = 0.05
#: A price shorter than this is sized by trust; from it, by the ladder.
LADDER_FROM = 200

EXPLANATION = (
    f"**Size** is {BASE_UNITS:g}u, scaled up by the trust the model has earned "
    f"in the game's tier (the trust line above), at most {MAX_UNITS:g}u. A tier "
    "trusted at zero is the base size. A long price is sized by its price "
    "instead: +200 to +500 0.15u, +501 to +1500 0.1u, longer than +1500 0.05u "
    "(the NHL Due List ladder). The site's record counts every bet at "
    f"{BASE_UNITS:g}u, or to win {BASE_UNITS:g}u on a minus price, up to +199, "
    "and at that ladder from +200, whatever trust says."
)


def ladder_units(price) -> float | None:
    """The size the price ladder sets for `price`, or None below +200
    (or for no usable price), where the trust size stands."""
    try:
        p = float(price)
    except (TypeError, ValueError):
        return None
    if p != p or p < LADDER_FROM:
        return None
    for longest, size in PRICE_BRACKETS:
        if p <= longest:
            return size
    return LONGEST_UNITS


def units(weight, price=None) -> float:
    """The size for a selection at `price` in a tier trusted at `weight`."""
    ladder = ladder_units(price)
    if ladder is not None:
        return ladder
    try:
        w = float(weight)
    except (TypeError, ValueError):
        return BASE_UNITS
    if w != w:
        return BASE_UNITS
    w = min(max(w, 0.0), 1.0)
    raw = BASE_UNITS * (1.0 + w)
    stepped = round(raw / STEP) * STEP
    return round(min(max(stepped, BASE_UNITS), MAX_UNITS), 2)
