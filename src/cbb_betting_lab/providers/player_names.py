"""Resolving a provider's spelling of an athlete to one player, or to nothing.

This is `providers.team_names` for people, and it exists for the same reason.
That module's docstring records the most expensive defect this lab has found:
**20.5% of provider TEAM names did not resolve**, the misses ran with
conference tier, and *a join that fails on half the low-major board is a biased
sample rather than a smaller one.* It was fixed by refusing to guess — an
ambiguous token expands into **every** reading and `resolve()` returns nothing
when the readings disagree.

The player names had the same problem and none of the treatment. Measured here
on 2026-09-05, walk-forward against `data/processed/cbb_player_games.csv` and
the prop rows of the card price store: **763 of 9,584 (game, player) pairs
carrying a prop — 7.96% — did not resolve.** The old normaliser
(`forward_evidence.normalise_person`, now a delegate to `normalise` below) did
three things: folded accents, stripped punctuation to spaces, and dropped
generational suffixes. Everything else the provider does to a name it could not
read.

What the misses actually were, counted rather than assumed. Each row is the
pairs recovered by adding that reading to all the others (leave-one-out):

    parenthetical or quoted aside   190   `Blake Hinson (PITT)`, `Efrem "Butta" Johnson`
    a run of initials joined         62   `KJ Adams` against `K.J. Adams Jr.`
    a hyphenated name's parts        22   `Reese Dixon-Waters` against `Reese Waters`
    the apostrophe deleted           18   `Kelel Ware` against `Kel'el Ware`
    a first name abbreviated         15   `S. Bairstow` against `Sean Bairstow`
    a lone medial initial             1   `Stephan D. Swenson`

Together they take 763 unresolved pairs to **372 (3.88%)**, recovering
**391 of 763 (51.2%)**, and they add **no ambiguity at all**: the one pair
whose name matched two athletes before still matches two and still refuses.
The remaining 372 are not reachable by any rule and must not be: they are
nicknames the two sources disagree on (`Kam Jones` / `Kameron Jones`,
`Pop Isaacs` / `Richard Isaacs`, `Ticket Gaines` / `Davonte Gaines`), given
names against short forms (`Clifford` / `Cliff`, `Joshua` / `Josh`) and plain
misspellings on one side (`Zhruic Phelps` for `Zhuric Phelps`,
`Roddy Gaylee Jr.` for `Roddy Gayle Jr.`). A rule that reached those would
reach past them too.

The rules, which are `team_names`' rules with the nouns changed:

1. **One index, built from the results source**, and keyed by game, so the
   candidates are already the two rosters that played it. The football lab's
   line: *a lone candidate on the wrong team is a void, not a match.*
2. **`None`, never a guess.** An unresolvable name is unknown, and unknown is
   not a did-not-play — see `tests/test_an_unresolved_name_is_not_a_void.py`.
3. **Ambiguity resolves to nothing, never to a coin flip.** A name matching two
   athletes on the two teams refuses. This is the whole reason the readings can
   be generous: a generous reading that reaches two people costs a refusal, not
   a settlement against the wrong athlete.
4. **Unresolved names are counted and reported**, because a name this lab
   cannot read is a prop it silently cannot price.

**There is deliberately no per-player alias map here, and that is the one place
this module departs from its sibling.** `team_names.SEED_ALIASES` can name
schools because the 365 schools are a fixed, public vocabulary. Writing down
that `Kameron Jones` means athlete 4433176 would be reading the answer off the
box score this resolver is scored against — an in-sample map wearing a
vocabulary's clothes. The observed spellings are committed at
`data/manual/provider_player_names_observed.json` as a **pin** for the tests,
not as a lookup this module consults at run time.
"""

from __future__ import annotations

import itertools
import re
import unicodedata
from dataclasses import dataclass, field

import pandas as pd

#: A parenthesised or quoted aside. The provider hangs three different things
#: here and none of them is part of the name: a team tag (`Blake Hinson
#: (PITT)`, `Jamal Shead (Hou)`), a disambiguator (`Jaylin (2002) Williams`)
#: and a nickname (`Myron (MJ) Amey, Jr.`, `Efrem "Butta" Johnson`). It is
#: read BOTH ways — with the aside and without — because a nickname in
#: parentheses is sometimes the only name the other source carries.
_ASIDE = re.compile(r"\([^)]*\)|\"[^\"]*\"|“[^”]*”")

#: Punctuation and spacing normalised away.
_PUNCT = re.compile(r"[^a-z0-9 ]+")
_SPACE = re.compile(r"\s+")

#: Generational suffixes. They appear on one side of this join and not the
#: other — `KJ Adams` and `K.J. Adams Jr.` are one player — and no D-I roster
#: distinguishes two athletes by suffix alone.
_SUFFIXES = frozenset({"jr", "sr", "ii", "iii", "iv", "v"})

#: Apostrophes: `'` and the typographic `’`, which the provider and ESPN
#: do not agree on either.
_APOSTROPHES = "'’"

#: A bound on the expansion, in the spirit of `team_names._MAX_AMBIGUOUS_TOKENS`.
#: The worst real name observed (`Myron (MJ) Amey, Jr.`) produces 4 readings and
#: a doubly-hyphenated name would produce 12; 64 is comfortably above both and
#: stops a pathological input from exploding.
_MAX_READINGS = 64

#: A name with more hyphenated components than this is left whole. Two is above
#: every observed case and keeps the product small.
_MAX_HYPHENATED = 2


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def _join_initials(words: list[str]) -> list[str]:
    """`['k', 'j', 'adams']` -> `['kj', 'adams']`.

    A run of adjacent single letters is one initialism written apart. The two
    sources disagree about the periods and therefore about the spaces:
    `K.J. Adams` punctuates to `k j adams` and `KJ Adams` to `kj adams`. This
    is a canonical form rather than a reading, applied identically to both
    sides of the join, because there is no name for which the two are different
    people. A run of ONE letter is left alone — that is a middle initial, and
    it has its own reading below.
    """
    out: list[str] = []
    run: list[str] = []
    for word in words:
        if len(word) == 1:
            run.append(word)
            continue
        if run:
            out.append("".join(run))
            run = []
        out.append(word)
    if run:
        out.append("".join(run))
    return out


def _words(text: str, *, drop_apostrophe: bool) -> list[str]:
    folded = _fold(str(text)).casefold()
    for mark in _APOSTROPHES:
        folded = folded.replace(mark, "" if drop_apostrophe else " ")
    folded = _PUNCT.sub(" ", folded)
    return _join_initials([w for w in folded.split() if w not in _SUFFIXES])


def normalise(name: object) -> str:
    """A player's name reduced to identity: the conservative reading.

    Accent-folded, lower-cased, punctuation-stripped, generational suffix
    dropped, and runs of initials joined. Deliberately separate from
    `team_names.normalise`, which expands `st` to `saint` and strips `college`
    — right for schools and wrong for people.

    This is one string. It is what a caller wants for a key or a display; it is
    NOT what the join is made on, because a single reading is exactly the thing
    that cost 20.5% of the team vocabulary. Use `variants`.
    """
    text = str(name or "")
    if not text or text.strip().lower() == "nan":
        return ""
    return _SPACE.sub(" ", " ".join(_words(text, drop_apostrophe=False))).strip()


def _hyphen_forms(text: str) -> list[str]:
    """`Reese Dixon-Waters` -> itself, `Reese Dixon`, `Reese Waters`.

    A hyphenated name is written in full by one source and in half by the
    other, in both directions and unpredictably: ESPN carries
    `Chad Baker-Mazara` where the provider writes `Chad Baker`, and
    `Reese Waters` where the provider writes `Reese Dixon-Waters`. Both halves
    are candidate readings and neither is preferred; if the two halves reach
    two different athletes the resolve refuses, which is the point.
    """
    parts = text.split()
    hyphenated = [i for i, p in enumerate(parts) if "-" in p.strip("-")]
    if not hyphenated or len(hyphenated) > _MAX_HYPHENATED:
        return [text]
    choices: list[list[str]] = []
    for i, part in enumerate(parts):
        if i in hyphenated:
            halves = [h for h in part.split("-") if h]
            choices.append([part, *halves])
        else:
            choices.append([part])
    return [" ".join(combo) for combo in itertools.product(*choices)]


def variants(name: object) -> frozenset[str]:
    """Every normalised form this spelling could plausibly mean.

    One string in, a SET out, because the provider's spelling of a person is
    ambiguous in ways that have more than one reading and picking one is
    guessing. `Myron (MJ) Amey, Jr.` yields `myron amey` and `myron mj amey`;
    only the first is on the box score. `Kelel Ware` yields `kelel ware`, which
    is how ESPN's `Kel'el Ware` reads once the apostrophe is deleted rather
    than spaced.

    The alternative — one canonical form, chosen by a rule that is right most
    of the time — is what `forward_evidence.normalise_person` was, and it left
    7.96% of the prop board unreadable.
    """
    raw = str(name or "")
    if not raw or raw.strip().lower() == "nan":
        return frozenset()

    bases = [raw]
    without_aside = _ASIDE.sub(" ", raw)
    if without_aside.strip() and without_aside != raw:
        bases.append(without_aside)

    forms: set[str] = set()
    for base in bases:
        for hyphenated in _hyphen_forms(base):
            drops = (False, True) if any(a in hyphenated for a in _APOSTROPHES) else (False,)
            for drop_apostrophe in drops:
                words = _words(hyphenated, drop_apostrophe=drop_apostrophe)
                readings = [words]
                # A lone medial initial — `Stephan D. Swenson` — is carried by
                # one source and dropped by the other. Both readings stand.
                medial = [i for i in range(1, len(words) - 1) if len(words[i]) == 1]
                if medial:
                    readings.append([w for i, w in enumerate(words) if i not in medial])
                for reading in readings:
                    text = _SPACE.sub(" ", " ".join(reading)).strip()
                    if text:
                        forms.add(text)
                    if len(forms) >= _MAX_READINGS:
                        return frozenset(forms)
    return frozenset(forms)


def abbreviations(name: object) -> frozenset[str]:
    """Readings with the first name cut to its initial: `sean bairstow` -> `s bairstow`.

    **These are index-side aliases only, and the asymmetry is deliberate.** The
    provider abbreviates a first name it has no room for (`S. Bairstow`,
    `H. Dickinson`, `D. Batcho`), so the box score's full spelling must answer
    to the abbreviation. Emitting the same form from a QUERY would be a
    different and much worse thing: `Jaylen Smith` would abbreviate to
    `j smith`, collide with a `Jordan Smith` on the same floor, and turn a name
    that resolves today into a refusal. So a full name never asks by initial;
    only a name that already arrived as an initial does, and for that name the
    abbreviation IS its ordinary reading.
    """
    forms: set[str] = set()
    for form in variants(name):
        words = form.split()
        if len(words) >= 2 and len(words[0]) > 1:
            forms.add(" ".join([words[0][0], *words[1:]]))
    return frozenset(forms)


def _game_key(game_id: object):
    """One key type for both sides of the join.

    `game_id` reaches this index as an int from one frame and a float from a
    CSV round-trip of the other. `settlement`'s docstring already records the
    athlete-id version of this bug — *the join-vocabulary bug family wearing an
    id instead of a name* — and keying on the raw value would reintroduce it
    one level up.
    """
    if game_id is None:
        return None
    if isinstance(game_id, float) and game_id != game_id:  # NaN
        return None
    try:
        return int(game_id)
    except (TypeError, ValueError):
        text = str(game_id).strip()
        return text or None


def _athlete_order(athlete: object) -> tuple:
    """A total order over athlete ids that does not depend on dict insertion.

    Ids arrive as floats from a CSV round-trip and as ints from a parquet read,
    so a plain sort would raise on a mixed set; numeric ones sort numerically
    and anything else sorts as text after them.
    """
    try:
        return (0, float(athlete), "")
    except (TypeError, ValueError):
        return (1, 0.0, str(athlete))


@dataclass
class PlayerIndex:
    """Aliases to athletes, per game, and the record of what did not resolve."""

    #: (game_id, normalised alias) -> the athlete ids carrying it
    aliases: dict[tuple, set] = field(default_factory=dict)
    #: (game_id, athlete_id) -> the box-score row, which is what settles a prop
    rows: dict[tuple, dict] = field(default_factory=dict)
    #: athlete_id -> the display name the results source spells him
    display: dict = field(default_factory=dict)
    #: Names asked for and not resolved, with how often. Reported loudly.
    unresolved: dict[str, int] = field(default_factory=dict)
    #: Names asked for that reached more than one athlete. They resolve to
    #: nothing, which is the safe direction, and they are counted separately
    #: because an ambiguous name is a different fact from an unreadable one.
    ambiguous: dict[str, int] = field(default_factory=dict)

    def add(self, game_id: object, athlete_id: object, name: object, row: dict) -> None:
        game = _game_key(game_id)
        if game is None or athlete_id is None:
            return
        if isinstance(athlete_id, float) and athlete_id != athlete_id:
            return
        forms = variants(name) | abbreviations(name)
        if not forms:
            return
        self.rows.setdefault((game, athlete_id), row)
        self.display.setdefault(athlete_id, str(name))
        for form in forms:
            self.aliases.setdefault((game, form), set()).add(athlete_id)

    def candidates(self, game_id: object, name: object) -> list[dict]:
        """Every box-score row this spelling could name, in athlete-id order.

        Zero rows is unresolved and one is a match; **more than one is
        ambiguous and the caller must settle nothing**, which is why this
        returns the list rather than a decision. Ordering is by athlete id so
        two runs over the same data cannot disagree about which of two
        candidates came first — a tie broken by dict order is a coin flip with
        the coin hidden.
        """
        game = _game_key(game_id)
        if game is None:
            return []
        found: set = set()
        for form in variants(name):
            found |= self.aliases.get((game, form), set())
        return [
            self.rows[(game, athlete)]
            for athlete in sorted(found, key=_athlete_order)
            if (game, athlete) in self.rows
        ]

    def resolve(self, game_id: object, name: object) -> dict | None:
        """One box-score row, or None — and None is recorded either way.

        A name reaching two athletes returns None exactly as a name reaching
        none does. `team_names.resolve`'s comment holds here word for word: an
        ambiguous name resolves to nothing, never to a coin flip.
        """
        found = self.candidates(game_id, name)
        raw = str(name or "").strip()
        if len(found) == 1:
            return found[0]
        if raw:
            book = self.ambiguous if found else self.unresolved
            book[raw] = book.get(raw, 0) + 1
        return None

    def unresolved_report(self, *, limit: int = 40) -> str:
        if not self.unresolved:
            return "Every provider player name resolved."
        rows = sorted(self.unresolved.items(), key=lambda kv: -kv[1])
        total = sum(self.unresolved.values())
        lines = [
            f"**{len(rows)} distinct player names did not resolve**, over "
            f"{total:,} rows. Each one is a prop this lab cannot settle, and it "
            "is counted as unsettleable rather than voided — unknown is not a "
            "did-not-play:",
            "",
            "| Name as the provider spells it | Rows |",
            "|:---|---:|",
        ]
        lines += [f"| `{name}` | {count:,} |" for name, count in rows[:limit]]
        if len(rows) > limit:
            lines.append(f"| … and {len(rows) - limit} more | |")
        return "\n".join(lines)


def build_index(player_games: pd.DataFrame, game_ids: set | None = None) -> PlayerIndex:
    """Every athlete in the requested games, under every spelling of his name.

    Keyed by game rather than by athlete so the candidate set is already the
    two rosters that took the floor. `did_not_play` rows are kept: they are how
    a resolved player who never entered reaches `settlement._player_guard` and
    comes back `VOID`. A name with no row at all is unresolved, which is a
    different verdict and a different counter.
    """
    index = PlayerIndex()
    if player_games is None or player_games.empty:
        return index
    wanted = player_games
    if game_ids is not None:
        if not game_ids:
            return index
        wanted = player_games[player_games["game_id"].isin(game_ids)]
    for record in wanted.to_dict("records"):
        index.add(
            record.get("game_id"),
            record.get("athlete_id"),
            record.get("athlete_display_name"),
            record,
        )
    return index
