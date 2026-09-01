"""Resolving a provider's spelling of a school to one team, or to nothing.

This is the highest-risk join in the lab. The NHL lab had 32 clubs and its
join-vocabulary bug family still reached five members; this one has **365
schools** whose names arrive in at least five shapes each — `UConn`,
`Connecticut`, `UConn Huskies`, `CONN`, `Connecticut Huskies` — plus a long
tail that is genuinely ambiguous between programmes (`Miami`, `Saint Mary's`,
`Loyola`, `Columbia` against `Colombia`).

The rules, all of which exist because a sibling lab paid for them:

1. **One index, built from the results source.** Every alias comes from the
   feed that also supplies the settlement, so the two sides of the join cannot
   describe different universes.
2. **`None`, never a guess.** An unresolvable name produces `no opinion`, which
   is different from a probability of zero, and every caller treats it as
   different. The football lab's note: *"a lone candidate on the wrong team is
   a void, not a match."*
3. **Ambiguity resolves to nothing, never to a coin flip.** Two schools whose
   normalised names collide return `None` unless the fixture disambiguates
   them.
4. **Unresolved names are reported loudly and counted.** A name this lab cannot
   resolve is a market it silently cannot price, and the NHL lab's UTC-date
   defect proved that a silent 69% loss looks exactly like a quiet market.

Measured on the 2025-26 schedule: 366 team ids, 366 distinct `location`
strings, **zero collisions on `location`** — which is why `location` is the
primary key of the index and the noisier forms are aliases onto it.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd


#: Words that carry no identity and appear inconsistently across sources.
#: `state` and `saint` are deliberately NOT here: "Michigan" and "Michigan
#: State" are different programmes, and so are "Mary's" and "Saint Mary's".
_NOISE = re.compile(r"\b(?:university|univ|college|the)\b")

#: Punctuation and spacing normalised away. Apostrophes matter to humans and
#: not to identity: `Saint Mary's` and `Saint Marys` are one school.
_PUNCT = re.compile(r"[^a-z0-9 ]+")
_SPACE = re.compile(r"\s+")

#: Common prefixes that both sources spell both ways.
_EXPANSIONS = {
    "st": "saint",
    "st.": "saint",
    "n": "north",
    "s": "south",
    "e": "east",
    "w": "west",
    "cent": "central",
    "mt": "mount",
    "ft": "fort",
}


def normalise(name: object) -> str:
    """A school name reduced to its identity.

    Accent-folded, lower-cased, punctuation-stripped, noise words removed, and
    a handful of prefixes expanded. Deliberately conservative: an aggressive
    normaliser merges `Miami (OH)` into `Miami`, and merging two real
    programmes is far worse than failing to match one spelling.
    """
    text = str(name or "")
    if not text or text.lower() == "nan":
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.casefold()
    text = _PUNCT.sub(" ", text)
    text = _NOISE.sub(" ", text)
    words = [_EXPANSIONS.get(w, w) for w in text.split()]
    return _SPACE.sub(" ", " ".join(words)).strip()


@dataclass
class TeamIndex:
    """Aliases to team ids, and the record of what could not be resolved."""

    #: normalised alias -> set of team ids carrying it
    aliases: dict[str, set] = field(default_factory=dict)
    #: team id -> its canonical display name, for reports
    display: dict = field(default_factory=dict)
    #: Names asked for and not resolved, with how often. Reported loudly.
    unresolved: dict[str, int] = field(default_factory=dict)
    #: Aliases claimed by more than one programme. Kept for the report; they
    #: resolve to nothing, which is the safe direction.
    ambiguous: dict[str, set] = field(default_factory=dict)

    def add(self, team_id, *names: object) -> None:
        for name in names:
            key = normalise(name)
            if not key:
                continue
            self.aliases.setdefault(key, set()).add(team_id)

    def resolve(self, name: object, *, among: set | None = None):
        """A team id, or None.

        `among` is the fixture's two team ids. It is the disambiguator that
        makes an otherwise-ambiguous name usable — and it is also the guard
        that turns *the wrong* lone candidate into a miss rather than a match.
        """
        key = normalise(name)
        if not key:
            return None
        candidates = self.aliases.get(key)
        if not candidates:
            # Record the miss under the raw spelling, which is what a human
            # needs to see to fix the map.
            raw = str(name or "").strip()
            if raw:
                self.unresolved[raw] = self.unresolved.get(raw, 0) + 1
            return None
        if among is not None:
            candidates = candidates & set(among)
        if len(candidates) != 1:
            raw = str(name or "").strip()
            if raw and not candidates:
                self.unresolved[raw] = self.unresolved.get(raw, 0) + 1
            return None
        return next(iter(candidates))

    def unresolved_report(self, *, limit: int = 40) -> str:
        if not self.unresolved:
            return "Every provider team name resolved."
        rows = sorted(self.unresolved.items(), key=lambda kv: -kv[1])
        total = sum(self.unresolved.values())
        lines = [
            f"**{len(rows)} distinct team names did not resolve**, over "
            f"{total:,} rows. Each one is a game this lab silently cannot "
            "price, and a silent loss looks exactly like a quiet market:",
            "",
            "| Name as the provider spells it | Rows |",
            "|:---|---:|",
        ]
        lines += [f"| `{name}` | {count:,} |" for name, count in rows[:limit]]
        if len(rows) > limit:
            lines.append(f"| … and {len(rows) - limit} more | |")
        return "\n".join(lines)


#: Spellings a provider uses that the results source does not, seeded by hand.
#:
#: **This map is incomplete and knowingly so.** `basketball_ncaab` is inactive
#: at the provider today (verified from its own sports listing, 2026-09-01,
#: `active=False`), so there is no live board to read real spellings off. These
#: entries are the ones a human can be confident about — schools whose common
#: name differs from ESPN's `location` string — and the rest is what
#: `scripts/discover_provider_teams.py` is for: on the first live board it
#: reports every name that did not resolve, loudly, and each one is added here
#: with the date it was observed. Guessing them now would be inventing data.
SEED_ALIASES: dict[str, tuple[str, ...]] = {
    # ESPN's `location`, then the other spellings that mean the same school.
    "UConn": ("Connecticut", "Connecticut Huskies", "UConn Huskies"),
    "Ole Miss": ("Mississippi", "Mississippi Rebels", "Ole Miss Rebels"),
    "Pitt": ("Pittsburgh", "Pittsburgh Panthers"),
    "Ohio State": ("Ohio St", "Ohio St."),
    "Michigan State": ("Michigan St", "Michigan St."),
    "NC State": ("North Carolina State", "North Carolina St"),
    "UCF": ("Central Florida", "Central Florida Knights"),
    "USC": ("Southern California", "Southern Cal"),
    "SMU": ("Southern Methodist",),
    "TCU": ("Texas Christian",),
    "LSU": ("Louisiana State",),
    "BYU": ("Brigham Young",),
    "VCU": ("Virginia Commonwealth",),
    "UNLV": ("Nevada Las Vegas", "Nevada-Las Vegas"),
    "UAB": ("Alabama Birmingham", "Alabama-Birmingham"),
    "UTEP": ("Texas El Paso", "Texas-El Paso"),
    "UTSA": ("Texas San Antonio", "Texas-San Antonio"),
    "UMass": ("Massachusetts", "Massachusetts Minutemen"),
    "Saint Joseph's": ("St Joseph's", "St. Joseph's", "Saint Josephs"),
    "Saint Mary's": ("St Mary's", "St. Mary's", "Saint Mary's (CA)"),
    "St. John's": ("Saint John's", "St Johns"),
    "Miami": ("Miami (FL)", "Miami Florida", "Miami FL"),
    "Miami (OH)": ("Miami Ohio", "Miami OH"),
    "Loyola Chicago": ("Loyola (IL)", "Loyola Illinois"),
    "Loyola Marymount": ("Loyola Marymount Lions",),
    "Southern Miss": ("Southern Mississippi",),
    "Charleston": ("College of Charleston", "Col of Charleston"),
    "Detroit Mercy": ("Detroit",),
    "Grambling": ("Grambling State",),
    "Nicholls": ("Nicholls State",),
    "McNeese": ("McNeese State",),
    "Purdue Fort Wayne": ("Fort Wayne", "IPFW"),
    "Omaha": ("Nebraska Omaha", "Nebraska-Omaha"),
    "Little Rock": ("Arkansas Little Rock", "Arkansas-Little Rock"),
    "UT Arlington": ("Texas Arlington", "Texas-Arlington"),
    "Kansas City": ("UMKC", "Missouri Kansas City"),
}


def build_index(
    schedule: pd.DataFrame, *, division_one_only: bool = True
) -> TeamIndex:
    """Every alias the results source knows, from both sides of every game.

    `division_one_only` restricts the index to teams the feed gives a
    conference to. That is not tidiness: with the 363 non-D-I teams included,
    seven aliases become ambiguous — `colorado` matches both Colorado and a
    non-D-I school, and an ambiguous alias resolves to nothing. Since the
    provider only ever prices D-I games, including the rest can only turn
    matches into misses.
    """
    index = TeamIndex()
    allowed: set | None = None
    if division_one_only:
        from cbb_betting_lab.population import division_one_team_ids

        allowed = division_one_team_ids(schedule)
    for side in ("home", "away"):
        columns = [
            f"{side}_id",
            f"{side}_location",
            f"{side}_name",
            f"{side}_abbreviation",
            f"{side}_display_name",
            f"{side}_short_display_name",
        ]
        present = [c for c in columns if c in schedule.columns]
        if f"{side}_id" not in present:
            continue
        frame = schedule[present].drop_duplicates()
        for row in frame.to_dict("records"):
            team_id = row.get(f"{side}_id")
            if team_id is None or (isinstance(team_id, float) and team_id != team_id):
                continue
            if allowed is not None and team_id not in allowed:
                continue
            index.display.setdefault(
                team_id, row.get(f"{side}_display_name") or row.get(f"{side}_location")
            )
            index.add(
                team_id,
                row.get(f"{side}_location"),
                row.get(f"{side}_display_name"),
                row.get(f"{side}_short_display_name"),
                row.get(f"{side}_abbreviation"),
                # `location` + `name` is how most providers spell it, and it is
                # already the display name for nearly every school — but not
                # all, so it is added explicitly rather than assumed.
                f"{row.get(f'{side}_location') or ''} {row.get(f'{side}_name') or ''}",
            )
    # Seed the provider spellings the results source does not carry, keyed on
    # the canonical `location` so a rename upstream breaks loudly rather than
    # silently orphaning a row of the map.
    by_location = {normalise(name): team for team, name in index.display.items()}
    location_key = {}
    for side in ("home", "away"):
        column = f"{side}_location"
        if column in schedule.columns and f"{side}_id" in schedule.columns:
            for row in schedule[[f"{side}_id", column]].drop_duplicates().to_dict("records"):
                location_key[normalise(row[column])] = row[f"{side}_id"]
    for canonical, spellings in SEED_ALIASES.items():
        team = location_key.get(normalise(canonical)) or by_location.get(normalise(canonical))
        if team is None or (allowed is not None and team not in allowed):
            # A seed naming a school this season's feed does not carry is not
            # an error — programmes reclassify — but it is not a silent pass
            # either, and the discovery script reports it.
            continue
        index.add(team, *spellings)

    # An alias claimed by more than one programme is not an alias. Dropping it
    # turns an ambiguous match into a miss, which is the safe direction.
    index.ambiguous = {k: v for k, v in index.aliases.items() if len(v) > 1}
    return index


def save(index: TeamIndex, path: Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(
            {
                "aliases": {k: sorted(int(i) for i in v) for k, v in sorted(index.aliases.items())},
                "display": {str(k): v for k, v in sorted(index.display.items(), key=lambda kv: str(kv[0]))},
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return target
