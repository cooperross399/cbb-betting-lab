"""How big a selection is, by how far the model has earned trust (decision 87).

Cooper, 2026-11-08 (*"DO all 7"*, item 4). Every selection used to read the
same size. The trust table (`models/trust.py`) already says, per tier, how much
of the model's disagreement with the price has been realised: 0 in a tier where
the card is price shopping against the fair price, up to 1 where the model's
view is worth its whole disagreement. The size follows it:

    size = BASE_UNITS * (1 + trust weight), rounded to STEP, at most MAX_UNITS

so a tier trusted at zero is the base 1u, and only a tier whose own settled
record has earned trust is sized up, never past 2u. No trust table, or a tier
it does not name, is the base size: the fail-safe direction.

**A long price is sized by quarter Kelly (decision 115).** Cooper, 2026-11-20:
*"Change the record/profit to reflect 1u risk/to win and quarter kelly sizing
based off that for the longer odds"*. From +200 (where the NHL Due List ladder
of decision 97 used to start) the size is

    KELLY_FRACTION * KELLY_BANKROLL * edge / payout, rounded to 0.01u, at most 1u

with 1u taken as 1% of the bankroll, `edge` the selection's own expected value
per unit at the price (what the 2% bar reads) and `payout` the profit per unit
staked. A selection with no edge is sized at the 2% bar; one at zero or less
is 0u. The same rule counts every tracked bet on the site
(`web/site_pages.tracked_stake`), so the card and the record agree.

This is a column on the card and nothing else. **The site's tracker counts
every bet at 1u (to win 1u on a minus price) up to +199, and by quarter Kelly
from +200**, so the record reads the same whatever trust says. The base was
0.25u, trust-scaled to 0.5u, until 2026-11-21; it is 1u scaled to 2u now, in the
same proportion, so the trust hypothesis registered as
`trust_sizing_2026_11_08` measures the same thing. Nothing here is a bet: this
lab never places one.
"""

from __future__ import annotations

BASE_UNITS = 1.0
MAX_UNITS = 2.0
STEP = 0.2
#: From this price a selection is sized by quarter Kelly, not by trust.
KELLY_FROM = 200
KELLY_FRACTION = 0.25
#: 1u is 1% of the bankroll.
KELLY_BANKROLL = 100.0
#: A long price is never sized past this.
KELLY_CAP = 1.0
#: The card's edge bar: the edge a selection that kept none is sized at.
KELLY_DEFAULT_EDGE = 0.02

EXPLANATION = (
    f"**Size** is {BASE_UNITS:g}u (to win {BASE_UNITS:g}u on a minus price), "
    "scaled up by the trust the model has earned in the game's tier (the trust "
    f"line above), at most {MAX_UNITS:g}u. A tier trusted at zero is the base "
    f"size. From +{KELLY_FROM} the size is quarter Kelly on the pick's own edge, "
    f"with 1u as 1% of the bankroll, never more than {KELLY_CAP:g}u. The site's "
    f"record counts every bet at {BASE_UNITS:g}u, or to win {BASE_UNITS:g}u on a "
    f"minus price, up to +{KELLY_FROM - 1}, and by the same quarter Kelly from "
    f"+{KELLY_FROM}, whatever trust says."
)


def kelly_units(price, edge=None) -> float | None:
    """The quarter-Kelly size for `price` at `edge`, or None below +200 (or
    for no usable price), where the trust size stands."""
    try:
        p = float(price)
    except (TypeError, ValueError):
        return None
    if p != p or p < KELLY_FROM:
        return None
    try:
        e = float(edge)
    except (TypeError, ValueError):
        e = KELLY_DEFAULT_EDGE
    if e != e:
        e = KELLY_DEFAULT_EDGE
    if e <= 0:
        return 0.0
    raw = KELLY_FRACTION * KELLY_BANKROLL * e / (p / 100.0)
    return round(min(max(raw, 0.0), KELLY_CAP), 2)


def units(weight, price=None, edge=None) -> float:
    """The size for a selection at `price` and `edge` in a tier trusted at
    `weight`."""
    kelly = kelly_units(price, edge)
    if kelly is not None:
        return kelly
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
