"""The competition registry. Every sport-specific fact lives here and nowhere else.

This lab is **NCAA Division I men's basketball, and only that.** Cooper,
2026-08-31: women's basketball and the lower divisions are separate projects in
their own repositories if they ever happen — the same call he made for NCAAF.
Do not add them here, not as a registry entry, not as an adapter.

The registry stays anyway, and it is not wasted work. It is what stops
sport-specific facts scattering through the code: provider sport key, market
registry, season calendar, timezone, day boundary, credit cap, policy key,
output prefix. That is what made this machinery copyable out of the NHL lab
into the football lab and out of the football lab into this one. It is a
**portability** device rather than a multi-sport one, and
`tests/test_competition_registry_is_the_only_place.py` fails the build when a
sport literal appears anywhere else.

## The day boundary, which is a basketball problem the siblings did not have

The NFL plays on a Sunday afternoon and the NHL at seven in the evening. D-I
men's basketball tips games every fifteen minutes for twelve hours, from an
11:00 Eastern morning game to a 22:30 Pacific tip — and 22:30 Pacific is
**01:30 Eastern the following morning**. Assigning that game to its Eastern
calendar date puts it on tomorrow's slate, where tomorrow's card will not price
it and yesterday's settlement will not find it.

So a game belongs to the **slate day** it was played on, which runs from
:data:`DAY_BOUNDARY_HOUR` Eastern to the same hour the next morning. That is
the convention ESPN, the NCAA and every book use when they say "Tuesday's
games", and it is the convention this lab joins on.

This is the NHL lab's most expensive bug, ported as a rule rather than
rediscovered: **69% of every price it bought was silently discarded** by a UTC
date meeting a league date, and the survivors were systematically the afternoon
games. Here the exposure is larger, because the late window is where the
low-major games live and the low-major games are the entire reason this lab
exists.

The boundary is not asserted. `tests/test_slate_day_matches_the_source.py`
checks this lab's `slate_date()` against the source's own game date over every
cached game, and fails if they disagree on more than a handful.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo


#: A basketball day runs 06:00 Eastern to 06:00 Eastern. A game tipping at
#: 01:30 Eastern belongs to the night before, which is where the board, the
#: card and the box score all put it.
DAY_BOUNDARY_HOUR = 6


@dataclass(frozen=True)
class Competition:
    """One competition: what it is called, where its data comes from, what it costs."""

    #: The key used everywhere inside this repository. Also the directory
    #: segment under `data/` and the prefix on every output file, so a second
    #: competition could never write over this one's evidence.
    key: str
    #: Human title for reports.
    title: str
    #: The Odds API sport key. The provider's vocabulary, not ours.
    provider_sport_key: str
    #: The Odds API futures/outrights keys, which are separate sports to the
    #: provider even though they are the same competition to us.
    futures_sport_keys: tuple[str, ...]
    #: The data-source adapter module. Named rather than imported so the
    #: registry stays importable without pulling every adapter into every
    #: process.
    data_adapter: str
    #: The registry of markets this competition prices.
    market_registry: str
    #: The calendar timezone. A game belongs to the day it is played in this
    #: zone — shifted by the day boundary above — never to its UTC date.
    timezone: ZoneInfo
    #: Hard per-day credit cap. Not advisory: the fetch spends front-to-back
    #: and stops. Derived from the competition's own worst slate by
    #: `scripts/estimate_credit_cost.py`, never guessed. A cap below the worst
    #: slate is a cap that starves it, and **a starved fetch and an unquoted
    #: market look identical in the reports.**
    daily_credit_cap: int
    #: Provider name in the staging policy. Allowlisting a market here never
    #: allowlists it anywhere else.
    policy_provider_name: str = "the_odds_api"

    @property
    def data_dir_segment(self) -> str:
        return self.key

    def output_name(self, stem: str, suffix: str) -> str:
        """`cbb_forward_evidence.md` — never a bare `forward_evidence.md`.

        An unprefixed output is a file two competitions would both write, and
        the second one to run would silently become the record.
        """
        return f"{self.key}_{stem}{suffix}"

    def verdict_dir(self, outputs_dir: Path) -> Path:
        return Path(outputs_dir) / self.key

    def policy_key(self) -> str:
        return f"{self.policy_provider_name}:{self.key}"


#: NCAA Division I men's basketball. The only entry, deliberately.
CBB = Competition(
    key="cbb",
    title="NCAA Division I men's basketball",
    provider_sport_key="basketball_ncaab",
    # Verified against the provider's own sports listing rather than guessed;
    # see `docs/cbb_data_sources.md`. Futures are a separate sport key to the
    # provider and settle on a different clock, which is why they are listed
    # apart rather than folded into the game-market list.
    futures_sport_keys=("basketball_ncaab_championship_winner",),
    data_adapter="cbb_betting_lab.data.sources",
    market_registry="cbb_betting_lab.markets",
    timezone=ZoneInfo("America/New_York"),
    # Derived by `scripts/estimate_credit_cost.py` from the real schedule.
    # Re-derived whenever the market list changes. The placeholder here is
    # deliberately large enough that it can only ever be lowered by
    # measurement, never raised by a slate it failed to hold.
    daily_credit_cap=60_000,
)

#: Women's basketball, D-II and D-III are deliberately absent, and their
#: absence is enforced rather than assumed. They are not a registry entry
#: waiting to be filled in: they are separate repositories if they ever happen.
#: `tests/test_population_purity.py` fails the build if a women's or non-D-I
#: identifier reaches the population through a provider key, an ESPN id or a
#: scraped page.
COMPETITIONS: dict[str, Competition] = {CBB.key: CBB}

#: Anything defaulting to a competition uses this rather than the string "cbb".
DEFAULT_COMPETITION_KEY = CBB.key


def competition_for(key: str) -> Competition:
    text = str(key or "").strip().lower()
    try:
        return COMPETITIONS[text]
    except KeyError as exc:
        raise KeyError(
            f"Unknown competition {key!r}. Known: {sorted(COMPETITIONS)}"
        ) from exc


def competition_keys() -> tuple[str, ...]:
    return tuple(sorted(COMPETITIONS))
