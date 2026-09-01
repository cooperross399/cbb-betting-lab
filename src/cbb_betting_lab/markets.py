"""Every market this lab prices, and the named quantity each one settles against.

The rule that governs this file, from Cooper's brief: *"If a source cannot
supply what a market needs to **settle**, that market is not wired. Fetching
prices nothing can consume spends credits on rows no join will ever find;
pricing without honest settlement manufactures evidence."*

So every entry names a `settles_on` quantity and the table it is read from, and
`DEFERRED_MARKETS` records — with a reason each — every provider key this lab
knows about and does not wire. Nothing is silently dropped. A market the
provider serves and this file does not mention is a bug, and
`tests/test_every_provider_key_is_wired_or_deferred.py` fails the build for it.

## The three things college basketball changes

**1. There are no quarters.** Men's college basketball plays two twenty-minute
halves. The provider's catalogue is shared across NBA, WNBA and NCAAB, so it
documents `spreads_q1`, `player_points_q1` and two dozen relatives. None of them
can exist in this sport, and none of them can settle. They are deferred with
that reason rather than asked for and quietly found empty — because a market
nobody quotes and a market that cannot exist look identical in a coverage report
and mean completely different things.

**2. There is no draw**, so there is no three-way. `h2h` here is two-way and
`selection.py` does not carry a `draw`.

**3. Overtime belongs to some segments and not others.** Full-game spreads,
totals and moneylines settle **including** overtime. First-half markets
obviously do not. Second-half markets are the trap: most US books settle them
**including** overtime, so a second half is `final − halftime` rather than
`regulation − halftime`. That is a book rule, not a fact about basketball, and
this lab cannot read a book's rulebook. It is wired to the common convention,
`SECOND_HALF_INCLUDES_OVERTIME`, and recorded as a **settlement ambiguity** in
`docs/cbb_data_sources.md` — because the football lab's single largest false
finding was a settlement offset it could not see, and the shape of that mistake
is exactly this.

## Tiers are a staging decision, not a budget one

Credits are not a constraint (`docs/credit_cost.md`). A tier says how confident
this lab is that a market is quoted and settleable, which drives what the probe
asks first and what the purchase buys first — core team markets, then ladders,
then props, then futures, which is Cooper's stated priority order.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from cbb_betting_lab.selection import FIRST_HALF, FULL_GAME, SECOND_HALF


#: The convention this lab settles second-half markets on. Most US books grade
#: a second-half wager including overtime; a minority do not. Wired to the
#: majority rule, stated wherever a second-half number appears, and listed as a
#: settlement ambiguity rather than presented as a fact.
SECOND_HALF_INCLUDES_OVERTIME = True

#: Double figures. A double-double is two of {points, rebounds, assists,
#: steals, blocks} at or above this; a triple-double is three.
DOUBLE_FIGURES = 10

#: The categories a double-double may be made of.
DOUBLE_CATEGORIES: tuple[str, ...] = ("points", "rebounds", "assists", "steals", "blocks")

TEAM = "team"
PLAYER = "player"
FUTURES = "futures"


@dataclass(frozen=True)
class Market:
    """One market: what it is, what settles it, and what it costs to ask for."""

    #: This lab's name for the market. Stable forever: it is a component of
    #: every join key and of every row in the append-only forward ledger.
    key: str
    #: The provider market keys that land here. More than one when a featured
    #: line and its alternate ladder are the same market priced at different
    #: rungs — which is the unit that gets modelled, measured and approved.
    #:
    #: **Every retention conclusion rolls up to the market, never the provider
    #: key.** The football lab's probe found three featured prop keys returning
    #: nothing across all twenty probed events while their alternate ladders had
    #: them: read per key that is three unmeasurable markets, read per market it
    #: is none.
    provider_keys: tuple[str, ...]
    title: str
    family: str
    #: Which part of the game it settles on. Full game includes overtime.
    segment: str
    #: The named quantity it settles against, in this lab's vocabulary. Never a
    #: prose description: a settlement function dispatches on this string, and
    #: `tests/test_every_market_settles_a_real_game.py` proves each one against
    #: real historical games.
    settles_on: str
    #: Which processed table supplies that quantity.
    settlement_table: str
    #: 1 = core team markets, 2 = ladders and halves, 3 = player props,
    #: 4 = futures. The probe and the purchase work in this order.
    tier: int
    #: True when the market is a ladder of rungs rather than one line. Ladders
    #: bill per key like anything else but return far more rows.
    is_ladder: bool = False
    #: True when a whole-number line can push. Modelled exactly rather than
    #: approximated — see `docs/why_the_half_point_matters.md`.
    push_possible: bool = True
    #: True when the market is priced as yes/no by the provider and as a count
    #: over 0.5 by this lab.
    yes_no: bool = False
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.provider_keys:
            raise ValueError(
                f"Market {self.key!r} names no provider key. A market nothing "
                "can be fetched for is a deferral, not a wiring."
            )
        if not self.settles_on:
            raise ValueError(
                f"Market {self.key!r} names no settlement quantity. Cooper's "
                "rule: pricing without honest settlement manufactures evidence."
            )


def _m(**kwargs) -> Market:
    return Market(**kwargs)


#: Tier 1 — the core team markets, on every D-I game.
TEAM_MARKETS: tuple[Market, ...] = (
    _m(key="moneyline", provider_keys=("h2h",), title="Moneyline",
       family=TEAM, segment=FULL_GAME, settles_on="game_margin",
       settlement_table="team_games", tier=1, push_possible=False,
       notes="Two-way. There is no draw in this sport, so there is no "
             "three-way to price and none is built."),
    _m(key="spread", provider_keys=("spreads",), title="Spread",
       family=TEAM, segment=FULL_GAME, settles_on="game_margin",
       settlement_table="team_games", tier=1),
    _m(key="total_points", provider_keys=("totals",), title="Total points",
       family=TEAM, segment=FULL_GAME, settles_on="game_total",
       settlement_table="team_games", tier=1),
    _m(key="team_total", provider_keys=("team_totals",), title="Team total",
       family=TEAM, segment=FULL_GAME, settles_on="team_score",
       settlement_table="team_games", tier=1),
)

#: Tier 2 — the alternate ladders and the halves.
LADDER_AND_HALF_MARKETS: tuple[Market, ...] = (
    _m(key="alternate_spread", provider_keys=("alternate_spreads",),
       title="Spread ladder", family=TEAM, segment=FULL_GAME,
       settles_on="game_margin", settlement_table="team_games", tier=2,
       is_ladder=True,
       notes="Every rung prices and settles off the same distribution object "
             "as the featured spread, so the two can never disagree."),
    _m(key="alternate_total_points", provider_keys=("alternate_totals",),
       title="Total ladder", family=TEAM, segment=FULL_GAME,
       settles_on="game_total", settlement_table="team_games", tier=2,
       is_ladder=True),
    _m(key="alternate_team_total", provider_keys=("alternate_team_totals",),
       title="Team total ladder", family=TEAM, segment=FULL_GAME,
       settles_on="team_score", settlement_table="team_games", tier=2,
       is_ladder=True),
    _m(key="moneyline_h1", provider_keys=("h2h_h1",), title="First-half moneyline",
       family=TEAM, segment=FIRST_HALF, settles_on="half_margin",
       settlement_table="team_games", tier=2, push_possible=True,
       notes="A half CAN end level, unlike a full game. The football lab "
             "priced a level half at 0.4% because its distribution hardcoded "
             "the full-game rule; measured, 7.4% of first halves end level "
             "against 0.35% of full games. Segments carry resolves_ties=False."),
    _m(key="spread_h1", provider_keys=("spreads_h1", "alternate_spreads_h1"),
       title="First-half spread", family=TEAM, segment=FIRST_HALF,
       settles_on="half_margin", settlement_table="team_games", tier=2),
    _m(key="total_points_h1", provider_keys=("totals_h1", "alternate_totals_h1"),
       title="First-half total", family=TEAM, segment=FIRST_HALF,
       settles_on="half_total", settlement_table="team_games", tier=2),
    _m(key="team_total_h1", provider_keys=("team_totals_h1", "alternate_team_totals_h1"),
       title="First-half team total", family=TEAM, segment=FIRST_HALF,
       settles_on="half_team_score", settlement_table="team_games", tier=2),
    _m(key="moneyline_h2", provider_keys=("h2h_h2",), title="Second-half moneyline",
       family=TEAM, segment=SECOND_HALF, settles_on="half_margin",
       settlement_table="team_games", tier=2,
       notes="Settled including overtime, which is a book rule rather than a "
             "fact about basketball. See SECOND_HALF_INCLUDES_OVERTIME."),
    _m(key="spread_h2", provider_keys=("spreads_h2", "alternate_spreads_h2"),
       title="Second-half spread", family=TEAM, segment=SECOND_HALF,
       settles_on="half_margin", settlement_table="team_games", tier=2),
    _m(key="total_points_h2", provider_keys=("totals_h2", "alternate_totals_h2"),
       title="Second-half total", family=TEAM, segment=SECOND_HALF,
       settles_on="half_total", settlement_table="team_games", tier=2),
    _m(key="team_total_h2", provider_keys=("team_totals_h2", "alternate_team_totals_h2"),
       title="Second-half team total", family=TEAM, segment=SECOND_HALF,
       settles_on="half_team_score", settlement_table="team_games", tier=2),
)

#: Tier 3 — player props. Expect coverage to be thin and concentrated on
#: televised high-major games, and establish that by probing **in season**: a
#: market unquoted in September establishes nothing.
PLAYER_MARKETS: tuple[Market, ...] = (
    _m(key="player_points", provider_keys=("player_points", "player_points_alternate"),
       title="Player points", family=PLAYER, segment=FULL_GAME,
       settles_on="player_points", settlement_table="player_games", tier=3,
       is_ladder=True),
    _m(key="player_rebounds", provider_keys=("player_rebounds", "player_rebounds_alternate"),
       title="Player rebounds", family=PLAYER, segment=FULL_GAME,
       settles_on="player_rebounds", settlement_table="player_games", tier=3,
       is_ladder=True),
    _m(key="player_assists", provider_keys=("player_assists", "player_assists_alternate"),
       title="Player assists", family=PLAYER, segment=FULL_GAME,
       settles_on="player_assists", settlement_table="player_games", tier=3,
       is_ladder=True),
    _m(key="player_threes", provider_keys=("player_threes", "player_threes_alternate"),
       title="Player three-pointers made", family=PLAYER, segment=FULL_GAME,
       settles_on="player_threes_made", settlement_table="player_games", tier=3,
       is_ladder=True),
    _m(key="player_blocks", provider_keys=("player_blocks", "player_blocks_alternate"),
       title="Player blocks", family=PLAYER, segment=FULL_GAME,
       settles_on="player_blocks", settlement_table="player_games", tier=3,
       is_ladder=True),
    _m(key="player_steals", provider_keys=("player_steals", "player_steals_alternate"),
       title="Player steals", family=PLAYER, segment=FULL_GAME,
       settles_on="player_steals", settlement_table="player_games", tier=3,
       is_ladder=True),
    _m(key="player_turnovers", provider_keys=("player_turnovers", "player_turnovers_alternate"),
       title="Player turnovers", family=PLAYER, segment=FULL_GAME,
       settles_on="player_turnovers", settlement_table="player_games", tier=3,
       is_ladder=True),
    _m(key="player_field_goals", provider_keys=("player_field_goals",),
       title="Player field goals made", family=PLAYER, segment=FULL_GAME,
       settles_on="player_field_goals_made", settlement_table="player_games", tier=3),
    _m(key="player_frees_made", provider_keys=("player_frees_made",),
       title="Player free throws made", family=PLAYER, segment=FULL_GAME,
       settles_on="player_free_throws_made", settlement_table="player_games", tier=3),
    _m(key="player_frees_attempts", provider_keys=("player_frees_attempts",),
       title="Player free throws attempted", family=PLAYER, segment=FULL_GAME,
       settles_on="player_free_throws_attempted", settlement_table="player_games",
       tier=3),
    _m(key="player_pra",
       provider_keys=("player_points_rebounds_assists",
                      "player_points_rebounds_assists_alternate"),
       title="Player points + rebounds + assists", family=PLAYER,
       segment=FULL_GAME, settles_on="player_pra", settlement_table="player_games",
       tier=3, is_ladder=True,
       notes="Read off the same compound simulation as its components, so the "
             "sum and the parts can never disagree."),
    _m(key="player_points_rebounds",
       provider_keys=("player_points_rebounds", "player_points_rebounds_alternate"),
       title="Player points + rebounds", family=PLAYER, segment=FULL_GAME,
       settles_on="player_points_rebounds", settlement_table="player_games",
       tier=3, is_ladder=True),
    _m(key="player_points_assists",
       provider_keys=("player_points_assists", "player_points_assists_alternate"),
       title="Player points + assists", family=PLAYER, segment=FULL_GAME,
       settles_on="player_points_assists", settlement_table="player_games",
       tier=3, is_ladder=True),
    _m(key="player_rebounds_assists",
       provider_keys=("player_rebounds_assists", "player_rebounds_assists_alternate"),
       title="Player rebounds + assists", family=PLAYER, segment=FULL_GAME,
       settles_on="player_rebounds_assists", settlement_table="player_games",
       tier=3, is_ladder=True),
    _m(key="player_blocks_steals", provider_keys=("player_blocks_steals",),
       title="Player blocks + steals", family=PLAYER, segment=FULL_GAME,
       settles_on="player_blocks_steals", settlement_table="player_games", tier=3),
    _m(key="player_double_double", provider_keys=("player_double_double",),
       title="Player double-double", family=PLAYER, segment=FULL_GAME,
       settles_on="player_double_double", settlement_table="player_games",
       tier=3, push_possible=False, yes_no=True,
       notes="Staged as the count of double-figure categories over 0.5 after "
             "the threshold, never as yes/no. Two spellings of one bet become "
             "two keys, and the card stakes it twice."),
    _m(key="player_triple_double", provider_keys=("player_triple_double",),
       title="Player triple-double", family=PLAYER, segment=FULL_GAME,
       settles_on="player_triple_double", settlement_table="player_games",
       tier=3, push_possible=False, yes_no=True),
    _m(key="player_first_basket", provider_keys=("player_first_basket",),
       title="First basket scorer", family=PLAYER, segment=FULL_GAME,
       settles_on="player_first_basket", settlement_table="play_by_play",
       tier=3, push_possible=False, yes_no=True,
       notes="Settles from play-by-play: the scorer of the game's first made "
             "field goal. A free throw is not a basket, which is a rule this "
             "lab has to encode rather than infer."),
    _m(key="player_first_team_basket", provider_keys=("player_first_team_basket",),
       title="First team basket scorer", family=PLAYER, segment=FULL_GAME,
       settles_on="player_first_team_basket", settlement_table="play_by_play",
       tier=3, push_possible=False, yes_no=True),
)

#: Tier 4 — futures. Their own section of every report, always, and never
#: folded into a headline computed over game bets.
FUTURES_MARKETS: tuple[Market, ...] = (
    _m(key="championship_winner", provider_keys=("outrights",),
       title="National championship winner", family=FUTURES, segment=FULL_GAME,
       settles_on="tournament_champion", settlement_table="tournament_results",
       tier=4, push_possible=False,
       notes="Served under the separate sport key "
             "`basketball_ncaab_championship_winner`. Hold time is months and "
             "is stated beside every number."),
)

MARKETS: tuple[Market, ...] = (
    TEAM_MARKETS + LADDER_AND_HALF_MARKETS + PLAYER_MARKETS + FUTURES_MARKETS
)

MARKETS_BY_KEY: dict[str, Market] = {m.key: m for m in MARKETS}

#: provider key -> this lab's market key. Built once so no caller hand-builds
#: it, which is how two copies of a mapping drift.
PROVIDER_KEY_TO_MARKET: dict[str, str] = {
    provider_key: market.key
    for market in MARKETS
    for provider_key in market.provider_keys
}


#: Every provider key this lab knows about and does not wire, with the reason.
#: Nothing is silently dropped: an excluded market is never reported as a pass,
#: an avoid, or a no-value call.
DEFERRED_MARKETS: dict[str, str] = {
    # --- The quarter family. Men's college basketball plays two halves. ---
    **{
        key: (
            "Men's college basketball plays two twenty-minute halves. There is "
            "no first quarter, so there is nothing to settle against. The "
            "provider documents this key because its basketball catalogue is "
            "shared with the NBA and WNBA. Asking for it would cost nothing and "
            "return nothing, which is exactly why it must be deferred with a "
            "reason rather than asked for and quietly found empty — a market "
            "nobody quotes and a market that cannot exist look identical in a "
            "coverage report and mean completely different things."
        )
        for key in (
            "h2h_q1", "h2h_q2", "h2h_q3", "h2h_q4",
            "spreads_q1", "spreads_q2", "spreads_q3", "spreads_q4",
            "totals_q1", "totals_q2", "totals_q3", "totals_q4",
            "alternate_spreads_q1", "alternate_spreads_q2",
            "alternate_spreads_q3", "alternate_spreads_q4",
            "alternate_totals_q1", "alternate_totals_q2",
            "alternate_totals_q3", "alternate_totals_q4",
            "team_totals_q1", "team_totals_q2", "team_totals_q3", "team_totals_q4",
            "alternate_team_totals_q1", "alternate_team_totals_q2",
            "alternate_team_totals_q3", "alternate_team_totals_q4",
            "player_points_q1", "player_rebounds_q1", "player_assists_q1",
        )
    },
    # --- Settleable in principle, not from anything free. ---
    "player_method_of_first_basket": (
        "Settles on how the first basket was scored — a dunk, a layup, a "
        "three, a tip-in. Play-by-play carries a text description of the shot, "
        "but the vocabulary is not standardised across the feed's own history "
        "and a book's categories are its own. Settling this would mean "
        "inventing a mapping from free text to a book's rulebook, and an "
        "invented settlement rule is how a lab manufactures a constant offset "
        "that replicates by construction. Revisit only with a source that "
        "states shot type as a code."
    ),
    "player_fantasy_points": (
        "Fantasy points are a scoring formula, and the formula differs by "
        "operator. Two books quoting `player_fantasy_points` are not quoting "
        "the same quantity, so there is no single named quantity for this "
        "market to settle against. DFS-only per the provider's own note."
    ),
    "player_fantasy_points_alternate": (
        "Same reason as `player_fantasy_points`: no single settlement quantity "
        "exists across operators."
    ),
}


def market_for_provider_key(provider_key: str) -> Market | None:
    """The market a provider key belongs to, or None when it is not wired.

    None rather than a raise: an unwired key arriving in a response is data
    about the provider, and it is counted in the accounting identity as
    unparseable rather than crashing a fetch that has already been paid for.
    """
    name = PROVIDER_KEY_TO_MARKET.get(str(provider_key))
    return MARKETS_BY_KEY.get(name) if name else None


def markets_in_tier(tier: int) -> tuple[Market, ...]:
    return tuple(m for m in MARKETS if m.tier == tier)


def provider_keys_in_tier(tier: int) -> tuple[str, ...]:
    """Every provider key to ask for at a given tier, deduplicated and sorted.

    Sorted so a cache filename built from the list is stable, and deduplicated
    because a repeated key in a request is a credit spent twice for one answer.
    """
    keys = {k for m in markets_in_tier(tier) for k in m.provider_keys}
    return tuple(sorted(keys))


def bulk_provider_keys() -> tuple[str, ...]:
    """The only keys the bulk endpoint tolerates, from the registry.

    Anything else there makes the provider refuse the whole request with a 422
    that names nothing.
    """
    from cbb_betting_lab.providers.odds_api import BULK_SAFE_MARKETS

    return tuple(sorted(set(PROVIDER_KEY_TO_MARKET) & BULK_SAFE_MARKETS))


def per_event_provider_keys(*, tiers: tuple[int, ...] = (1, 2, 3)) -> tuple[str, ...]:
    """Everything that must be asked per event: all keys the bulk call refuses."""
    from cbb_betting_lab.providers.odds_api import BULK_SAFE_MARKETS

    keys = {k for t in tiers for k in provider_keys_in_tier(t)}
    return tuple(sorted(keys - BULK_SAFE_MARKETS))


def all_known_provider_keys() -> frozenset[str]:
    """Every provider key this lab has an opinion about — wired or deferred."""
    return frozenset(PROVIDER_KEY_TO_MARKET) | frozenset(DEFERRED_MARKETS)
