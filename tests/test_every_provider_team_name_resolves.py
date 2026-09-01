"""Every spelling the provider actually uses resolves to exactly one school.

This is the highest-value test in the repository, and it exists because the
retention probe measured the damage rather than assuming there was none.

**20.5% of provider team names did not resolve** — 75 of 365 — and the misses
were not spread evenly. Match rate by conference tier across 144 sampled games:

    high_major   86.8%
    mid_major    76.1%
    low_major    46.7%

The low-major end of the board is this lab's entire thesis: *"360 teams on a
Tuesday night in January is the opposite [of a tightly-priced league]. If the
market's efficiency is not uniform across the board, this is where that shows
up."* A join that silently drops half of it would have measured the high-major
board and reported the answer as college basketball's.

Nothing errored. The purchase would have bought those events, the staging would
have discarded them, and the report would have shown a smaller population with
no indication that a fifth of the vocabulary was unreadable.

The 365 names in `data/manual/provider_team_names_observed.json` are OBSERVED,
read off 140 cached historical slate listings from the 2026-09-01 probe. They
are not a guess about what the provider might call a school.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbb_betting_lab.data import hoopr
from cbb_betting_lab.providers import team_names as T

OBSERVED = Path(__file__).resolve().parents[1] / "data" / "manual" / "provider_team_names_observed.json"


@pytest.fixture(scope="module")
def observed() -> list[str]:
    payload = json.loads(OBSERVED.read_text(encoding="utf-8"))
    names = payload["names"]
    assert len(names) == 365, (
        f"{len(names)} observed names. D-I has 365 teams; a different count "
        "means the fixture was regenerated from a different population."
    )
    return names


@pytest.fixture(scope="module")
def index():
    try:
        schedule = hoopr.load("schedules", 2026)
    except Exception:  # noqa: BLE001
        pytest.skip("The 2026 schedule is not cached.")
    if schedule.empty:
        pytest.skip("The 2026 schedule is not cached.")
    return T.build_index(schedule)


def test_every_observed_provider_name_resolves(observed, index):
    unresolved = sorted(n for n in observed if index.resolve(n) is None)
    assert not unresolved, (
        f"{len(unresolved)} of {len(observed)} provider spellings resolve to "
        f"nothing:\n  " + "\n  ".join(unresolved) + "\n\n"
        "Each one is a game this lab silently cannot price. Add it to "
        "SEED_ALIASES with the provider's spelling VERBATIM, nickname included."
    )


def test_no_two_schools_answer_to_one_name(observed, index):
    """A name resolving to two schools must resolve to neither. Settling a bet
    against the wrong game is worse than not settling it."""
    collisions = {}
    for name in observed:
        forms = T.variants(name)
        teams: set = set()
        for form in forms:
            teams |= index.aliases.get(form, set())
        if len(teams) > 1:
            collisions[name] = teams
    for name, teams in collisions.items():
        assert index.resolve(name) is None, (
            f"{name!r} matches {len(teams)} schools and still resolved. An "
            "ambiguous name resolves to nothing, never to a coin flip."
        )


def test_the_st_token_is_read_both_ways(index):
    """The expensive one. The provider writes `Michigan St` for Michigan STATE
    and `St. John's` for SAINT John's — one token, two schools, and no rule of
    position separates them. Mapping it to one reading cost 20.5% of the
    vocabulary."""
    assert index.resolve("Michigan St Spartans") == index.resolve("Michigan State Spartans")
    assert index.resolve("Michigan St Spartans") is not None
    saint = index.resolve("St. John's Red Storm")
    assert saint is not None
    assert saint != index.resolve("Michigan St Spartans")


def test_state_and_the_plain_school_stay_different_programmes():
    """The normaliser must not merge them. Michigan and Michigan State are two
    schools, and an aggressive normaliser that merged them would turn a whole
    category of bets into settlements against the wrong game."""
    assert T.normalise("Michigan") != T.normalise("Michigan State")
    assert "michigan state" in T.variants("Michigan St")
    assert "michigan" not in T.variants("Michigan St")


def test_variants_are_bounded():
    """A pathological input must not explode combinatorially."""
    assert len(T.variants("N S E W SE SW NE NW St")) <= 64
    assert T.variants("") == frozenset()


@pytest.mark.parametrize(
    "provider_spelling",
    [
        "Fort Wayne Mastodons",       # ESPN: Purdue Fort Wayne
        "Grand Canyon Antelopes",     # ESPN: Grand Canyon Lopes
        "Long Beach St 49ers",        # ESPN nickname is literally "Beach"
        "UMKC Kangaroos",             # ESPN: Kansas City Roos
        "GW Revolutionaries",         # ESPN: George Washington
        "Loyola (Chi) Ramblers",      # parenthesised disambiguator
        "Loyola (MD) Greyhounds",
        "CSU Bakersfield Roadrunners",
        "Tenn-Martin Skyhawks",       # ESPN: UT Martin
        "Texas A&M-CC Islanders",
    ],
)
def test_the_names_that_share_no_token_with_espn(provider_spelling, index):
    """These cannot be reached by any normalisation rule — the provider and
    ESPN simply call the school different things. They are in SEED_ALIASES
    because they were observed, and this test is what keeps them there."""
    assert index.resolve(provider_spelling) is not None, provider_spelling


def test_loyola_chicago_and_loyola_maryland_are_not_the_same_school(index):
    a = index.resolve("Loyola (Chi) Ramblers")
    b = index.resolve("Loyola (MD) Greyhounds")
    assert a is not None and b is not None and a != b
