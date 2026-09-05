"""What the player-name reader may and may not read into a spelling.

`test_every_provider_player_name_resolves.py` pins the vocabulary; this file
pins the rules, including the ones that say **no**. `providers.player_names` is
generous on purpose — it emits every reading of an ambiguous spelling rather
than choosing one — and generosity is only safe while two things hold:

* two athletes answering to one name refuse, so a loose reading costs a refusal
  rather than a settlement against the wrong man; and
* the readings stay mechanical. A rule that turns `Kameron` into `Kam` or
  `Clifford` into `Cliff` is a guess about people, and there is no roster on
  which it is checkable at run time.

The measurement behind these rules, 2026-09-05, over 9,584 (game, player) pairs
carrying a prop: one canonical reading left 763 unreadable (7.96%); every
reading here together leaves 372 (3.88%), and adds no ambiguity.
"""

from __future__ import annotations

import pandas as pd
import pytest

from cbb_betting_lab.providers import player_names as P

GAME = 700_001


def _index(*roster: tuple[int, str]) -> P.PlayerIndex:
    frame = pd.DataFrame(
        [
            {
                "game_id": GAME,
                "athlete_id": athlete,
                "athlete_display_name": name,
                "did_not_play": False,
            }
            for athlete, name in roster
        ]
    )
    return P.build_index(frame, {GAME})


def test_an_ambiguous_spelling_expands_into_every_reading_rather_than_one():
    """The shape `team_names.variants` established, with the nouns changed."""
    assert P.variants("Myron (MJ) Amey, Jr.") == frozenset({"myron amey", "myron mj amey"})
    assert P.variants("Kel'el Ware") == frozenset({"kel el ware", "kelel ware"})
    assert P.variants("Reese Dixon-Waters") == frozenset(
        {"reese dixon waters", "reese dixon", "reese waters"}
    )
    assert P.variants("Stephan D. Swenson") == frozenset(
        {"stephan d swenson", "stephan swenson"}
    )


def test_a_run_of_initials_is_one_token_however_it_is_punctuated():
    """`K.J.` and `KJ` are one man; the two sources disagree about the periods."""
    assert P.normalise("K.J. Adams Jr.") == P.normalise("KJ Adams")
    assert P.normalise("K.J. Adams Jr.") == "kj adams"
    # A LONE initial is not a run and is not joined to the surname — that would
    # make `Stephan D. Swenson` read `stephan dswenson` and match nothing.
    assert P.normalise("Stephan D. Swenson") == "stephan d swenson"


def test_a_generational_suffix_and_an_accent_are_not_identity():
    assert P.normalise("Zach Edey Jr.") == P.normalise("zach edey")
    assert P.normalise("Kevin McCullar III") == P.normalise("Kevin McCullar")
    assert P.normalise("Álvaro Cárdenas") == "alvaro cardenas"
    assert P.normalise(float("nan")) == ""
    assert P.normalise("") == ""
    assert P.variants("") == frozenset()


def test_a_full_first_name_never_asks_by_its_initial():
    """The asymmetry that keeps `abbreviations` from costing more than it pays.

    The box score answers to `s bairstow` so the provider's `S. Bairstow` can
    reach it. If a QUERY also abbreviated, `Jaylen Smith` would ask for
    `j smith`, collide with the `Jordan Smith` on the same floor, and a name
    that resolves today would start refusing.
    """
    assert "j smith" in P.abbreviations("Jaylen Smith")
    assert "j smith" not in P.variants("Jaylen Smith")

    index = _index((1, "Jaylen Smith"), (2, "Jordan Smith"))
    assert index.resolve(GAME, "Jaylen Smith")["athlete_id"] == 1
    assert index.resolve(GAME, "Jordan Smith")["athlete_id"] == 2
    # The initial genuinely is ambiguous between them, and refuses.
    assert index.resolve(GAME, "J. Smith") is None
    assert index.ambiguous.get("J. Smith") == 1


def test_two_athletes_answering_to_one_name_refuse_and_are_told_from_a_miss():
    index = _index((1, "Justin Moore"), (2, "Justin Moore"), (3, "Ryan Nembhard"))
    assert len(index.candidates(GAME, "Justin Moore")) == 2
    assert index.resolve(GAME, "Justin Moore") is None
    assert index.ambiguous == {"Justin Moore": 1}
    assert index.unresolved == {}

    assert index.resolve(GAME, "Nobody At All") is None
    assert index.unresolved == {"Nobody At All": 1}
    assert index.ambiguous == {"Justin Moore": 1}


def test_the_reader_stops_at_the_edge_of_what_a_rule_can_know():
    """The 372 that stay unreadable, and the reason they must.

    Each pair below is observed on the measured board. A reading that crossed
    any of these lines would also cross them in a game where the two names are
    two people.
    """
    unreachable = [
        ("Kameron Jones", "Kam Jones"),          # a nickname, not an abbreviation
        ("Cliff Omoruyi", "Clifford Omoruyi"),   # a short form of a given name
        ("Richard Isaacs", "Pop Isaacs"),        # the sources disagree entirely
        ("Zhruic Phelps", "Zhuric Phelps"),      # a misspelling on one side
        ("Roddy Gaylee Jr.", "Roddy Gayle Jr."),
        ("Alvaro Cardenas Torre", "Alvaro Cardenas"),  # a dropped surname
        ("Jonathan JJ Starling", "JJ Starling"),
    ]
    for provider, espn in unreachable:
        index = _index((1, espn))
        assert index.resolve(GAME, provider) is None, (
            f"{provider!r} reached {espn!r}. That is a guess about a person, "
            "and there is no roster on which it is checkable."
        )
        assert index.resolve(GAME, espn)["athlete_id"] == 1


def test_the_expansion_is_bounded():
    """A pathological spelling must not explode combinatorially.

    The cap truncates, so it must sit well above every real name: the worst
    observed spelling on the measured board produces 6 readings
    (`Tyon Grant-Foster (GC)`) and this input produces more than 64.
    """
    monster = "Aa-Bb-Cc-Dd-Ee Ff-Gg-Hh-Ii-Jj O'k (X)"
    assert len(P.variants(monster)) == P._MAX_READINGS
    assert P._MAX_READINGS >= 64
    assert len(P.variants("Tyon Grant-Foster (GC)")) == 6
    # More hyphenated components than the reader will take apart: it leaves the
    # name whole rather than expanding, which is a miss and never a wrong match.
    assert P.variants("Aa-Bb-Cc Dd-Ee-Ff Gg-Hh-Jj") == frozenset({"aa bb cc dd ee ff gg hh jj"})


def test_the_index_keys_the_game_the_same_way_from_either_frame():
    """A float game id from a CSV round-trip and an int from a parquet read are
    one game. `settlement` records the athlete-id version of this bug — the
    join-vocabulary family wearing an id instead of a name — and keying on the
    raw value would reintroduce it one level up."""
    index = _index((1, "Zach Edey"))
    assert index.resolve(float(GAME), "Zach Edey")["athlete_id"] == 1
    assert index.resolve(str(GAME), "Zach Edey")["athlete_id"] == 1
    assert index.resolve(GAME + 1, "Zach Edey") is None


def test_a_did_not_play_row_stays_in_the_index():
    """It is the only road to VOID, and losing it would turn every benched
    player into an unreadable name — a real defect wearing this one's clothes.
    """
    frame = pd.DataFrame(
        [
            {
                "game_id": GAME,
                "athlete_id": 9,
                "athlete_display_name": "Beta Bench",
                "did_not_play": True,
                "minutes": None,
                "points": None,
            }
        ]
    )
    index = P.build_index(frame, {GAME})
    row = index.resolve(GAME, "Beta Bench")
    assert row is not None and row["did_not_play"] is True


def test_candidates_come_back_in_a_fixed_order():
    """Two runs over the same data must not disagree about which of two
    candidates came first. A tie broken by dict order is a coin flip with the
    coin hidden."""
    index = _index((77, "Justin Moore"), (11, "Justin Moore"))
    assert [r["athlete_id"] for r in index.candidates(GAME, "Justin Moore")] == [11, 77]


def test_an_empty_frame_indexes_to_nothing_rather_than_raising():
    assert P.build_index(pd.DataFrame(), {GAME}).aliases == {}
    assert P.build_index(None, {GAME}).aliases == {}
    assert _index((1, "Zach Edey")).candidates(GAME, None) == []
    assert _index((1, "Zach Edey")).candidates(None, "Zach Edey") == []
