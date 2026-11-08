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

This is a column on the card and nothing else. **The site's tracker keeps
counting every bet at 0.25u, by Cooper's rule of 2026-11-04**, so the record
reads the same whatever this says. Nothing here is a bet: this lab never places
one. Registered as `trust_sizing_2026_11_08`, one per tier.
"""

from __future__ import annotations

BASE_UNITS = 0.25
MAX_UNITS = 0.5
STEP = 0.05

EXPLANATION = (
    f"**Size** is {BASE_UNITS:g}u, scaled up by the trust the model has earned "
    f"in the game's tier (the trust line above), at most {MAX_UNITS:g}u. A tier "
    "trusted at zero is the base size. The site's record counts every bet at "
    f"{BASE_UNITS:g}u whatever this column says."
)


def units(weight) -> float:
    """The size for a tier trusted at `weight`."""
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
