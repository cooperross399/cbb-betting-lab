"""The card does not bet where the model loses to the closing line (decision 82).

Cooper, 2026-11-08: *"bet only where we beat the closing line."* The
closing-line alarm (`reports/closing_alarm.py`, decision 68) reads the model's
settled leans against the last capture before tip, per tier and main market,
and names a cell whose family-corrected interval of mean closing-line value
lies entirely below zero. It named the cell and withdrew nothing. This module is
the withdrawal: on a card day, every full-game wager in a named cell is taken
off the probability map the edge bar reads, so the card cannot select it.

**What a cell covers.** The alarm grades moneyline, spread and total_points.
The alternate ladders take their main market's verdict (`line_move.MAIN_MARKET`),
because a rung is the same opinion about the same game at another number.
Since decision 94 the alarm also grades the high-hold markets on their own --
both alternate ladders and full-game team totals, at their own prices against
the main close -- and a tripped high-hold cell is closed here too, so a ladder
is off the card when either its main market or the ladder itself loses to the
close. The alternate team total takes the team total's verdict (`LADDER_OF`).
Halves and props are untouched: the alarm does not read them.

**Direction.** This only ever removes a wager from the card's reach. It never
adds one, never touches the allowlist (`staging_provider_policy.json` is not
edited, so lifting an alarm restores the cell with no grant), and never touches
the forward ledger, which keeps freezing the model's own probability for every
wager, gated or not, so the alarm keeps measuring the cells it has closed.

**Conditioned on what, known when.** The alarm the card reads is the one the
same Gameday Refresh run wrote after settling last night, from settled rows
only. A record dated after the card day, or older than `MAX_AGE_DAYS`, is not
read: a stale alarm is no alarm, never a guess. Registered as
`closing_gate_2026_11_08`, one per tier.

**The mismatch, disclosed.** The alarm grades the raw model's leans. The card
reads the trust-weighted probability, which in a tier trusted at zero is pure
price shopping against the fair price. A cell the alarm closes is therefore
closed on the evidence that the model's own view of that market has been
losing to the close, which is the evidence available; whether the card's
price-shopped selections in that cell would also have lost to it is a separate
question the registration measures.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping

from cbb_betting_lab.models.line_move import MAIN_MARKET

#: False turns the gate off and the card selects as it did before decision 82.
GATE_ON = True
#: The oldest alarm record the card reads, in days before the card day.
MAX_AGE_DAYS = 3
RECORD_NAME = "cbb_closing_alarm.json"
FULL_GAME = ("game", "full_game")
#: Ladders the alarm does not grade itself, and the cell whose verdict each
#: takes. A rung is the same opinion as its market at another number, so an
#: alternate team total is closed wherever the team total is (decision 94:
#: the 2026-11-09 evening card bought three of them in tiers whose team
#: totals the gate had closed).
LADDER_OF = {"alternate_team_total": "team_total"}


@dataclass
class Gate:
    """The (tier, main market) cells closed tonight, and why the set is what it is."""

    closed: frozenset = field(default_factory=frozenset)
    as_of: str | None = None
    reason: str = ""

    def closes(self, wager) -> bool:
        if str(getattr(wager, "segment", "") or "") not in FULL_GAME:
            return False
        if str(getattr(wager, "player", "") or "").strip():
            return False
        market = str(getattr(wager, "market", "") or "")
        tier = str(getattr(wager, "tier", "") or "")
        if (tier, market) in self.closed:
            return True
        main = MAIN_MARKET.get(market) or LADDER_OF.get(market)
        return main is not None and (tier, main) in self.closed

    def line(self) -> str:
        if not self.closed:
            return f"Closing-line gate: nothing closed ({self.reason or 'no alarm'})."
        cells = ", ".join(f"{t.replace('_', '-')} {m}" for t, m in sorted(self.closed))
        return (
            f"Closing-line gate: {cells} closed tonight; the model's leans there have lost to the "
            f"close (alarm of {self.as_of})."
        )


def _parse_cell(text: str) -> tuple[str, str] | None:
    parts = [p.strip() for p in str(text).split("/")]
    if len(parts) != 2 or not all(parts):
        return None
    return parts[0], parts[1]


def load(path: Path | str, day: str) -> Gate:
    """The gate for `day`, from the alarm record at `path`. Absent, unreadable,
    future-dated or stale records close nothing, and say so."""
    if not GATE_ON:
        return Gate(reason="the gate is off")
    path = Path(path)
    if not path.is_file():
        return Gate(reason=f"no alarm record at {path}")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
        as_of = str(record.get("as_of") or "")[:10]
        age = (date.fromisoformat(str(day)[:10]) - date.fromisoformat(as_of)).days
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        return Gate(reason=f"the alarm record could not be read ({type(exc).__name__})")
    if age < 0:
        return Gate(as_of=as_of, reason=f"the alarm is dated {as_of}, after the card day")
    if age > MAX_AGE_DAYS:
        return Gate(as_of=as_of, reason=f"the alarm of {as_of} is older than {MAX_AGE_DAYS} days")
    closed = frozenset(c for c in map(_parse_cell, record.get("alarms") or []) if c is not None)
    return Gate(closed=closed, as_of=as_of, reason="" if closed else f"no alarm tripped on {as_of}")


def apply(probabilities: Mapping, wagers: Iterable, gate: Gate | None) -> tuple[dict, int]:
    """The probability map with every wager in a closed cell removed, and how
    many were removed. Unchanged when there is no gate."""
    out = dict(probabilities or {})
    if gate is None or not gate.closed:
        return out, 0
    removed = 0
    for wager in wagers:
        if wager.key in out and gate.closes(wager):
            del out[wager.key]
            removed += 1
    return out, removed
