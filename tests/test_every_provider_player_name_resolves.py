"""Every spelling the provider uses for a player resolves to one athlete, or to nobody.

This is `test_every_provider_team_name_resolves.py` for people, and it exists
for the same reason. That test's docstring records the most expensive defect
this lab has found: **20.5% of provider TEAM names did not resolve**, the
misses ran with conference tier, and a join that fails on half the low-major
board is a biased sample rather than a smaller one.

The player names were never given the same treatment. Measured 2026-09-05,
walk-forward against `data/processed/cbb_player_games.csv` and the prop rows of
the card price store — 9,584 (game, player) pairs over 1,180 games and 1,357
distinct provider spellings:

    unresolved before   763   7.96%
    unresolved after    372   3.88%

and the 391 recovered pairs cost **no ambiguity at all**: the one pair whose
name reached two athletes before still reaches two and still refuses.

The vocabulary in `data/manual/provider_player_names_observed.json` is
OBSERVED. Every `provider` string is a spelling the provider actually used,
every `espn` string is what the box score calls that athlete, and every cited
game carries its COMPLETE roster — so a spelling is resolved against the two
teams that took the floor rather than in isolation, which is the only version
of this test that means anything. `Justin Moore` resolves in most games and
must refuse in the one where both teams dressed a Justin Moore.

The 60 spellings recorded `unresolved` are pinned too, and that direction
matters as much as the other one. They are nicknames the two sources disagree
on (`Kam Jones` / `Kameron Jones`), given names against short forms
(`Clifford` / `Cliff`) and plain misspellings (`Zhruic` for `Zhuric`). A
reading generous enough to reach them would reach past them, and this file
fails if one of them starts resolving.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbb_betting_lab.providers import player_names as P

OBSERVED = (
    Path(__file__).resolve().parents[1]
    / "data"
    / "manual"
    / "provider_player_names_observed.json"
)


@pytest.fixture(scope="module")
def vocabulary() -> dict:
    payload = json.loads(OBSERVED.read_text(encoding="utf-8"))
    assert len(payload["entries"]) == 1359, (
        f"{len(payload['entries'])} observed entries. A different count means "
        "the fixture was regenerated from a different population, and the "
        "rates quoted in this file no longer describe it."
    )
    assert len(payload["games"]) == 273, len(payload["games"])
    return payload


@pytest.fixture
def index(vocabulary) -> P.PlayerIndex:
    """An index over the committed rosters — every athlete of every cited game.

    Function-scoped on purpose. `PlayerIndex` records what it was asked for and
    could not resolve, so two tests sharing one index would be reading each
    other's misses, and the counts below would depend on the order pytest
    happened to run them in.
    """
    built = P.PlayerIndex()
    for game_id, roster in vocabulary["games"].items():
        game = int(game_id)
        for athlete_id, display in roster:
            built.add(
                game,
                athlete_id,
                display,
                {
                    "game_id": game,
                    "athlete_id": athlete_id,
                    "athlete_display_name": display,
                },
            )
    assert len(built.rows) > 8_000, f"{len(built.rows)} athlete-games is not 273 rosters"
    return built


def test_every_observed_provider_spelling_reaches_the_athlete_it_names(vocabulary, index):
    wrong = []
    for entry in vocabulary["entries"]:
        if entry["verdict"] != "resolved":
            continue
        row = index.resolve(entry["game_id"], entry["provider"])
        if row is None or row["athlete_id"] != entry["athlete_id"]:
            wrong.append(
                f"{entry['provider']!r} in game {entry['game_id']} -> "
                f"{None if row is None else row['athlete_display_name']!r}, "
                f"expected {entry['espn']!r}"
            )
    assert not wrong, (
        f"{len(wrong)} of the observed spellings do not reach the athlete they "
        "name:\n  " + "\n  ".join(wrong[:40])
    )


def test_the_count_of_resolvable_spellings_is_the_measured_one(vocabulary):
    resolved = [e for e in vocabulary["entries"] if e["verdict"] == "resolved"]
    assert len(resolved) == 1298, len(resolved)


def test_a_name_no_rule_reaches_stays_unreached_and_is_counted(vocabulary, index):
    """Over-reach is the failure this half of the file exists to catch.

    A reading loose enough to turn `Kameron Jones` into `Kam Jones` would also
    turn one guard into another, and nothing would error. These 60 stay
    unresolved, and each one lands in `index.unresolved` under the raw spelling
    a human needs in order to see it.
    """
    unreachable = [e for e in vocabulary["entries"] if e["verdict"] == "unresolved"]
    assert len(unreachable) == 60, len(unreachable)
    reached = {
        e["provider"]: index.resolve(e["game_id"], e["provider"])
        for e in unreachable
    }
    over = {k: v["athlete_display_name"] for k, v in reached.items() if v is not None}
    assert not over, (
        f"{len(over)} spellings no rule should reach now resolve: {over}. A "
        "reading that reaches these reaches past them, and settling a prop "
        "against the wrong athlete does not error."
    )
    for entry in unreachable:
        assert entry["provider"] in index.unresolved, entry["provider"]
    assert sum(index.unresolved.values()) == 60, sum(index.unresolved.values())


def test_a_name_two_athletes_answer_to_refuses_and_never_picks(vocabulary, index):
    """The one real collision in the measured board, kept as a fixture.

    Both teams in game 401604303 dressed a Justin Moore. The spelling is
    perfect, it names a real player, and it names two of them. `team_names`'
    rule holds word for word here: an ambiguous name resolves to nothing, never
    to a coin flip.
    """
    collisions = [e for e in vocabulary["entries"] if e["verdict"] == "ambiguous"]
    assert len(collisions) == 1, collisions
    entry = collisions[0]
    assert len(index.candidates(entry["game_id"], entry["provider"])) == 2
    assert index.resolve(entry["game_id"], entry["provider"]) is None
    assert index.ambiguous.get(entry["provider"]) == 1
    # And it is NOT filed as unreadable: two athletes answering to one name is
    # a different fact from a name nobody answers to, and the census that
    # reports them apart is the one that says which is happening.
    assert entry["provider"] not in index.unresolved


def test_the_same_spelling_resolves_where_only_one_man_answers_to_it(vocabulary, index):
    """The collision is a property of the GAME, not of the string.

    `Justin Moore (Villanova)` is the same person and resolves cleanly in the
    games where the other bench has no Justin Moore. A resolver that blacklisted
    the string would lose those, which is the smaller-sample mistake wearing the
    safe-direction costume.
    """
    elsewhere = [
        e
        for e in vocabulary["entries"]
        if e["verdict"] == "resolved" and e["provider"].startswith("Justin Moore")
    ]
    assert elsewhere, "no clean Justin Moore in the observed vocabulary"
    for entry in elsewhere:
        row = index.resolve(entry["game_id"], entry["provider"])
        assert row is not None and row["athlete_id"] == entry["athlete_id"], entry


@pytest.mark.parametrize(
    ("provider", "espn"),
    [
        ("Blake Hinson (PITT)", "Blake Hinson"),        # a team tag
        ("RJ Davis (UNC)", "RJ Davis"),
        ("Yves Missi (BAYLOR)", "Yves Missi"),
        ("Jamal Shead (Hou)", "Jamal Shead"),
        ("Jaylin (2002) Williams", "Jaylin Williams"),  # a disambiguator
        ('Efrem "Butta" Johnson', "Efrem Johnson"),     # a quoted nickname
        ("Myron (MJ) Amey, Jr.", "Myron Amey Jr."),     # a parenthesised one
        ("KJ Adams", "K.J. Adams Jr."),                 # initials joined
        ("R.J. Davis", "RJ Davis"),                     # and apart
        ("Kelel Ware", "Kel'el Ware"),                  # an apostrophe deleted
        ("JaKobi Gillespie", "Ja'Kobi Gillespie"),
        ("Reese Dixon-Waters", "Reese Waters"),         # half a hyphenated name
        ("Chad Baker", "Chad Baker-Mazara"),            # the other half
        ("S. Bairstow", "Sean Bairstow"),               # an initialised first name
        ("H. Dickinson", "Hunter Dickinson"),
        ("Stephan D. Swenson", "Stephan Swenson"),      # a lone medial initial
    ],
)
def test_each_class_of_miss_the_measurement_found(provider, espn, vocabulary, index):
    """One named example per reading, so a rule cannot be dropped quietly.

    Every pair here is observed: the left string is what the provider sent and
    the right is what the box score calls him. Before this module they were all
    misses.
    """
    entries = [e for e in vocabulary["entries"] if e["provider"] == provider]
    assert entries, f"{provider!r} is not in the observed vocabulary"
    entry = entries[0]
    row = index.resolve(entry["game_id"], provider)
    assert row is not None, f"{provider!r} resolves to nobody"
    assert row["athlete_display_name"] == espn, row["athlete_display_name"]


def test_the_unresolved_report_names_the_spellings_a_human_must_fix(index):
    index.unresolved.clear()
    assert "Every provider player name resolved." == index.unresolved_report()
    entry_game = next(iter(index.rows))[0]
    index.resolve(entry_game, "Nobody Of That Name")
    report = index.unresolved_report()
    assert "1 distinct player names did not resolve" in report
    assert "`Nobody Of That Name`" in report
    assert "unknown is not a did-not-play" in report
