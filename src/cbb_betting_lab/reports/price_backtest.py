"""The instrument that decides: a model priced against prices it could have taken.

Calibration can rule a model out and never in. Forecast skill (see
`forecast_skill.py`) says whether the model knows anything at all. **This module
is the one that says whether a policy would have made money**, and it is
arranged so that every way the three sibling labs got that wrong is either
impossible here or printed on the front page.

## Walk-forward, structurally rather than by convention

The football lab's largest silent leak was a per-play yardage distribution
loaded **once, outside the season loop**: the distribution used to price 2023
had seen 2025. Only the compound markets consumed it, "which is precisely why
the compound group looked good".

A convention cannot stop that; a signature can. :func:`walk_forward` never hands
a pricer the whole table. It walks slate days in order and calls
``price_day(day=..., history=..., prices=...)`` where ``history`` holds only
games **strictly earlier** than the day being priced, stamps every returned row
with the ``priced_through`` day it was actually built from, and
:func:`assert_walk_forward` raises if any row's ``priced_through`` is not
strictly earlier than the day it bet on. `tests/test_run_price_backtest.py`
pins both halves — `test_the_pricer_only_ever_sees_games_strictly_earlier_than_
the_day` and `test_every_bet_carries_the_day_it_was_priced_through` — and
`tests/test_fit_ratings.py::test_corrupting_every_game_after_a_cut_leaves_the_
earlier_fits_identical` is the corrupt-everything-after-a-cut test, on the
ratings the backtest prices through. (This docstring used to cite a
`tests/test_price_backtest.py` that never existed.)

## One wager is one bet, at the best price

The NHL lab counted every book's quote on the same selection as an independent
bet: 2.83 quotes per selection, so every interval came out about √2.83 too
narrow, and it measured a strategy nobody would run. Run per quote, its full
store called all three team markets demonstrated losses; run per wager, all
three span zero. :func:`one_bet_per_wager` is `stores.assert_single_window` then
`stores.dedupe_prices` then `stores.best_price_per_wager`, in that order, and
none of the three is optional.

`assert_single_window` **raises**. Mixing a card-time price and a closing price
in one best-price collapse takes a price nobody could have taken.

## The null baseline is computed first and printed first

*"The question that broke the football lab's best result was never 'is this
robust'. It was — what would betting one side with no model at all return?"*

So :func:`null_baseline` runs over the whole graded price universe before any
model result is looked at, and :func:`side_concentration` checks whether the
model's bets are simply one side wearing a model's clothes: if at least
:data:`SIDE_CONCENTRATION` of a cell's bets sit on one side and that side's
no-model return has the same sign, the report says so beside the number rather
than under it. A model that bets 90% unders in a season when unders returned
+3% blind has not found anything.

## Half a point at a key number is reported apart from a view of the game

A spread model that is systematically half a point away from the number is not
a model with an opinion about the game; it is a model with an opinion about
rounding, and the two behave completely differently when the market moves.
:func:`half_point_decomposition` splits every graded bet into those whose result
would flip if the line moved half a point against them and those that would not,
and reports the return of each.

**It verifies its own convention before it reports.** The ticket margin is
reconstructed from ``actual``, ``line`` and ``selection``; if the sign of that
reconstruction disagrees with the recorded ``outcome`` on more than
:data:`CONVENTION_TOLERANCE` of rows, the decomposition is refused and the
report says it could not be verified. A decomposition computed on a wrong
handicap convention is exactly the kind of finding that supplies its own
explanation, which `docs/what_we_can_and_cannot_claim.md` names as the most
dangerous kind.

The key numbers themselves are **measured from the games supplied**, never a
list carried over from football. Basketball's margin distribution is not the
NFL's, and a hardcoded {3, 7} would be a fact about a different sport.

## Per market and per conference tier, never a pooled headline

6 high-major conferences / 79 teams, 10 mid-major / 122, 17 low-major / 164 —
three different distributions, and the whole thesis of this lab is that the
third one is priced with less attention. The lead table is market x tier. A
pooled figure exists, because `docs/when_this_ends.md` applies the stopping rule
to it, and it is printed under a heading that says in words that it is never the
headline.

## Below the declared floor there is no number

`stats.MINIMUM_BETS` is 200. Below it :func:`roi_cells` prints an em dash where
the return would go. `stats.roi_table_row` prints the figure regardless, which
is right for a table of measured markets and wrong here, so this module has its
own row renderer and a test that pins the difference: *"a +12% return over 40
bets and a coin flip are the same claim at that sample size"*, and printing the
+12% invites somebody to quote it.

## Nothing to measure is said in words

No historical price has been bought for this sport. Every function here returns
an empty result honestly and :func:`render` prints *"there is nothing to
measure"* rather than an empty table, because an empty table reads as a null
result and a null result is a claim.
"""

from __future__ import annotations

import importlib
import inspect
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from cbb_betting_lab import stats as S
from cbb_betting_lab import stores
from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.conferences import Tier
from cbb_betting_lab.experiment_ledger import LEDGER_FILENAME
from cbb_betting_lab.experiment_ledger import load as load_ledger
from cbb_betting_lab.stores import _decimal_payout as decimal_payout


#: Bumped whenever the record's shape changes, so a stale record fails loudly
#: at re-render rather than rendering a report with holes in it.
#:
#: **Not bumped on 2026-09-05 when the ROI tables started printing the
#: clustering.** That change is in the renderer only: `cluster_unit` has been
#: written by :func:`_interval_row` onto every interval row since before this
#: branch, so a version 1 record already carries the field the new column
#: reads, and every version 1 record on disk renders under the new header with
#: the same numbers it always held. Changing the version here would refuse
#: records that are not stale. What the field's absence would mean is covered
#: instead by :func:`cluster_cell`, which prints `unknown-clusters` rather than
#: guessing "games" — see `test_run_price_backtest.py::
#: test_a_version_1_record_still_carries_the_clustering_on_every_row` and
#: `::test_a_row_with_no_cluster_unit_is_never_assumed_to_be_games`.
RECORD_VERSION = 1

#: What a graded bet must carry before it can be measured. A **missing column
#: raises** — the football lab's backtest read a missing settlement column as a
#: zero through `getattr(..., None)`, reported zero bets, and that read as "the
#: model never disagrees enough" when in truth the price columns had never been
#: built.
BET_COLUMNS: tuple[str, ...] = (
    "event_id",
    "slate_date",
    "market",
    "segment",
    "selection",
    "line",
    "american_odds",
    "tier",
    "model_probability",
    "outcome",
    "profit_units",
)

#: Optional, and each one turns a section on rather than being faked when
#: absent. `survived_to_next_capture` belongs to `reachability.py`;
#: `priced_through` is stamped by :func:`walk_forward`; `actual` is the settled
#: quantity and is what the half-point decomposition is checked against.
OPTIONAL_BET_COLUMNS: tuple[str, ...] = (
    "player",
    "book",
    "snapshot_phase",
    "actual",
    "edge",
    "priced_through",
    "survived_to_next_capture",
)

#: The edge a priced opinion must clear to be counted as a bet. The same value
#: `forward_evidence.BET_EDGE_THRESHOLD` freezes forward opinions at, restated
#: here rather than imported so this module does not depend on a module being
#: written beside it — and pinned equal by a test once both exist.
BET_EDGE_THRESHOLD = 0.02

#: When at least this share of a cell's bets sit on one side, the cell's result
#: is reported beside that side's no-model return, because a model that only
#: ever bets unders is a bet on unders.
SIDE_CONCENTRATION = 0.75

#: How much disagreement between the reconstructed ticket margin and the
#: recorded outcome is tolerated before the half-point decomposition refuses to
#: report. One row in a hundred can be a void, a restated box score or a
#: genuinely odd grade; one row in ten is a wrong convention.
CONVENTION_TOLERANCE = 0.01

#: How much of the population the measured key numbers must cover. A
#: description device, not a threshold that decides anything: it picks how many
#: of the most frequent integer margins get named in the report.
KEY_NUMBER_COVERAGE = 0.5

#: The sides a no-model baseline can take. Blind, mechanical, and the first
#: thing computed.
BASELINE_SIDES: tuple[str, ...] = ("home", "away", "over", "under")

#: Printed above every pooled figure, in full, every time.
POOLED_CAVEAT = (
    "**Pooled across Division I. This is never the headline.** High-major, "
    "mid-major and low-major are different distributions; a policy that wins "
    "in low-major games and loses in high-major ships in low-major only, if it "
    "ships at all. `docs/when_this_ends.md` applies the stopping rule to the "
    "pooled figure as well as to each tier, which is why it is computed — not "
    "so it can be quoted on its own."
)

#: What the report says when the prices do not exist yet. In words, because an
#: empty table reads as a null result and a null result is a claim.
NOTHING_TO_MEASURE = "there is nothing to measure"

#: Tier order for every table in this package, strongest first.
TIER_ORDER: tuple[str, ...] = (
    Tier.HIGH_MAJOR.value,
    Tier.MID_MAJOR.value,
    Tier.LOW_MAJOR.value,
    Tier.UNPLACED.value,
)


class BacktestError(RuntimeError):
    """A backtest could not be run honestly, so it was not run."""


class WalkForwardLeak(BacktestError):
    """A bet was priced by a model that had seen the game it bet on."""


# --------------------------------------------------------------------------
# Frame hygiene
# --------------------------------------------------------------------------


def require_columns(frame: pd.DataFrame, columns: Sequence[str], what: str) -> None:
    """Raise on a missing column. Never default it, never `getattr(..., None)`.

    The football lab's props backtest reported **zero bets** because its price
    columns had never been built and a missing column read as a zero. Zero bets
    reads as "the model never disagrees enough with the market", which is a
    finding; it was a wiring fault. This raises instead.
    """
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise BacktestError(
            f"{what} is missing {missing}. A missing column read as a zero is "
            "how the football lab's backtest reported zero bets and had that "
            "read as 'the model never disagrees enough'. Nothing is defaulted."
        )


def one_bet_per_wager(prices: pd.DataFrame) -> pd.DataFrame:
    """One row per wager, at the best price, from one snapshot window.

    In that order, and none of the three steps is optional. See the module
    docstring and `stores.py` — this is the NHL lab's √2.83 defect, closed by
    calling the three functions that close it rather than by remembering to.
    """
    if prices.empty:
        return prices
    stores.assert_single_window(prices)
    return stores.best_price_per_wager(stores.dedupe_prices(prices))


def add_edge(frame: pd.DataFrame, *, probability_column: str = "model_probability") -> pd.DataFrame:
    """`edge = p·(1 + payout) − 1`, or missing when either side is missing.

    One definition of the word in this repository, matching
    `forward_evidence.expected_value`. A missing probability yields a missing
    edge — an absent opinion is not an opinion of zero, and the two are counted
    differently everywhere downstream.
    """
    if frame.empty:
        return frame.assign(edge=pd.Series(dtype="float64"))
    payout = frame["american_odds"].map(decimal_payout)
    probability = pd.to_numeric(frame[probability_column], errors="coerce")
    edge = probability * (1.0 + payout) - 1.0
    return frame.assign(edge=edge.where(payout > float("-inf")))


def bet_mask(frame: pd.DataFrame, *, threshold: float = BET_EDGE_THRESHOLD) -> pd.Series:
    """True exactly where :func:`bets_from` would keep the row.

    One predicate, used by `bets_from` and by the `selected` column the graded
    export carries, so "a bet" and "a selected row" can never be two different
    cuts of the same frame. A missing edge is not a bet.
    """
    if frame.empty or "edge" not in frame.columns:
        return pd.Series(False, index=frame.index, dtype=bool)
    edge = pd.to_numeric(frame["edge"], errors="coerce")
    return (edge >= float(threshold)).fillna(False).astype(bool)


def bets_from(frame: pd.DataFrame, *, threshold: float = BET_EDGE_THRESHOLD) -> pd.DataFrame:
    """The rows a card would have staked: an edge at or above the threshold.

    The threshold is declared in advance and the all-opinions figure is
    reported beside the bets figure, so neither cut can flatter the other. A
    threshold moved after a number is seen is the defect this whole repository
    is arranged against — and `forecast_skill.py` shows algebraically why
    raising it cannot help.
    """
    if frame.empty or "edge" not in frame.columns:
        return frame.iloc[0:0]
    return frame[bet_mask(frame, threshold=threshold)].reset_index(drop=True)


def settled(frame: pd.DataFrame) -> pd.DataFrame:
    """Rows with a realised profit. `UNSETTLEABLE` is an exclusion, not a loss."""
    if frame.empty or "profit_units" not in frame.columns:
        return frame.iloc[0:0]
    return frame[pd.to_numeric(frame["profit_units"], errors="coerce").notna()]


#: The two outcomes a forecast can be scored against. A push is not half a win,
#: a void is not a loss and `UNSETTLEABLE` is an exclusion; `forecast_skill`
#: imports this rather than restating it so the export and the regression agree
#: on what "settled" means.
SCORABLE_OUTCOMES: frozenset[str] = frozenset({"won", "lost"})


def settled_opinions(
    frame: pd.DataFrame, *, probability_column: str = "model_probability"
) -> pd.DataFrame:
    """Every settled wager the model had an opinion on — bet or not.

    This is the population the market-vs-model regression runs over: a model
    probability, a realised profit, and a won-or-lost outcome. It is NOT
    :func:`bets_from`: the bets are the rows the model's own disagreement with
    the price selected, and regressing outcome on that same disagreement over
    only those rows bakes the winner's curse into the coefficient and makes the
    claimed-edge buckets tautological — every row is, by construction, above
    the threshold. Until 2026-09-05 `--write-graded` exported exactly that.

    The rows kept here are a superset of the settled bets; the export marks the
    bets with a boolean `selected` column computed by :func:`bet_mask` so the
    selected subset can be reported *beside* the whole, never instead of it.
    """
    if frame.empty or probability_column not in frame.columns or "outcome" not in frame.columns:
        return frame.iloc[0:0]
    kept = settled(frame)
    if kept.empty:
        return kept
    probability = pd.to_numeric(kept[probability_column], errors="coerce")
    outcome = kept["outcome"].astype(str).str.strip().str.lower()
    return kept[probability.notna() & outcome.isin(SCORABLE_OUTCOMES)]


# --------------------------------------------------------------------------
# Walk-forward
# --------------------------------------------------------------------------



# --------------------------------------------------------------------------
# The model seam: one callable, resolved and called the same way everywhere
# --------------------------------------------------------------------------

#: Where the model comes from by default. `models/ratings.py:matchups_for` is
#: the single seam between the ratings and everything that consumes them — the
#: price backtest, the replication, the gameday card and the forward freeze all
#: price through it, so a game priced in a measurement is priced the same way it
#: is on a card. It lives here, in the library, so the card does not have to
#: import a script to find it.
DEFAULT_MODEL = "cbb_betting_lab.models.ratings:matchups_for"

#: The keyword arguments a model may declare. It is handed the ones it names and
#: no others, so a model that only wants the day and the history does not have
#: to accept arguments it will not read.
#:
#: This is the vocabulary, not a promise: no single caller builds all of it —
#: the price backtest's per-day pricer builds four of these five — so a model
#: that *requires* one is wired to some callers and not others. Which is why
#: :func:`call_model` checks against what the caller in hand actually supplies
#: rather than against this tuple.
MODEL_ARGUMENTS: tuple[str, ...] = ("day", "history", "prices", "competition", "raw_dir")


class ModelNotWired(RuntimeError):
    """The named model could not be resolved. No fallback pricer exists."""


class ModelArgumentUnsupplied(ModelNotWired):
    """The model requires an argument the caller does not build.

    A subclass of :class:`ModelNotWired` because it is the same fault seen from
    the other end — the model and the caller are not wired to each other — and
    because every entry point that already exits on a wiring fault should exit
    on this one too, rather than growing a second handler that could be
    forgotten at one of them.
    """


def resolve_model(spec: str = DEFAULT_MODEL) -> Callable:
    """`module:attribute` -> the callable, or a refusal that names what is missing.

    There is deliberately no fallback. A backtest that silently prices with
    something other than the model the card runs measures a policy nobody would
    have run, and it does it while printing intervals.
    """
    text = str(spec or "").strip()
    module_name, separator, attribute = text.partition(":")
    if not module_name or not separator or not attribute:
        raise ModelNotWired(
            f"--model {spec!r} is not a `module:attribute` path. It names the "
            "callable that returns one matchup per event for a slate day, for "
            f"example {DEFAULT_MODEL!r}."
        )
    try:
        module = importlib.import_module(module_name)
    except ImportError as exc:
        raise ModelNotWired(
            f"{module_name} could not be imported ({exc}). "
            + (
                "`models/ratings.py` is not written yet — `gameday_card` says "
                "so in its own docstring, and every wager on today's card "
                "reads 'no opinion' for the same reason. "
                if module_name.endswith("ratings")
                else ""
            )
            + "Nothing was scored and nothing was written: a backtest with no "
            "model is an empty report, and an empty report reads as a null "
            "result."
        ) from exc
    try:
        model = getattr(module, attribute)
    except AttributeError as exc:
        raise ModelNotWired(
            f"{module_name} has no attribute {attribute!r}. It must be a "
            "callable taking the keyword arguments it declares out of "
            f"{list(MODEL_ARGUMENTS)} and returning a mapping of event_id to a "
            "matchup object. "
            "Nothing was scored and nothing was written: a backtest with no "
            "model is an empty report, and an empty report reads as a null "
            "result."
        ) from exc
    if not callable(model):
        raise ModelNotWired(f"{spec} resolved to {type(model).__name__}, not a callable.")
    return model


def model_name(model: Callable) -> str:
    """`module.qualname` for a model, for refusals that have to name it."""
    qualname = getattr(model, "__qualname__", None) or getattr(model, "__name__", "")
    module = getattr(model, "__module__", "")
    if qualname and module:
        return f"{module}.{qualname}"
    return qualname or repr(model)


def unsupplied_arguments(model: Callable, provided: Iterable[str]) -> list[str]:
    """The parameters `model` requires that a caller offering `provided` cannot fill.

    Empty means the pair is wired. A non-empty list is a wiring fault and
    :func:`call_model` refuses on it; it is a function rather than four lines
    inside `call_model` so a caller can be checked against a model without
    calling it, which is the only way to assert the shipped seam still fits its
    shipped callers without loading a season of data to run it.

    **A parameter with a default is exempt, and that is a real distinction
    rather than a hole in the check.** A default is the model author's written
    statement that absence is acceptable and that the model has a defined
    behaviour without the argument: `raw_dir=None` means "read the packaged raw
    directory", `competition=CBB` means "this lab". A *required* parameter is
    the opposite statement — the model cannot produce a number without it. The
    signature is the one place the author makes either statement, so it is the
    one place this reads. A model that genuinely needs a table nobody builds
    yet says so by not defaulting it, and then this refuses instead of handing
    it `None`.

    Positional-only parameters are counted unsupplied even when the caller has
    a value of that name: this seam calls by keyword only, so a required
    positional-only parameter cannot be filled here by any caller.
    """
    offered = set(provided)
    try:
        parameters = inspect.signature(model).parameters
    except (TypeError, ValueError):
        # Not introspectable — a builtin, or a C callable. Nothing can be
        # checked and nothing can be filtered. Refusing here would refuse a
        # model that is fine; the callee raises in its own words instead.
        return []
    unsupplied: list[str] = []
    for name, parameter in parameters.items():
        if parameter.default is not inspect.Parameter.empty:
            continue
        if parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            # `*args` and `**kwargs` are never required of a caller.
            continue
        if parameter.kind is inspect.Parameter.POSITIONAL_ONLY or name not in offered:
            unsupplied.append(name)
    return unsupplied


def call_model(model: Callable, caller: str, /, **arguments):
    """Call a model with the arguments it declares — or refuse, naming both.

    Two rules, and the second one is the reason this function exists rather
    than a bare `model(**arguments)` at each call site:

    1. **An argument the model does not declare is not passed.** A model that
       only wants the day and the history should not have to accept a price
       frame it will never read, and a model taking `**kwargs` gets everything.
       Filtering here rather than at the model keeps the walk-forward guarantee
       in one place: `history` is built by :func:`history_before` and is the
       only view of the past anything downstream is given.

    2. **A parameter the model requires and the caller cannot build is a
       refusal, not a quieter call.** Until 2026-09-05 this function filtered
       the arguments by the callee's signature and stopped there, so a model
       declaring `player_games` — as `models.ratings.matchups_for` does, with
       four call sites and all four in `tests/` — was called without it and
       never told. It would have priced the day off whatever its default was
       and returned probabilities that looked like every other day's. That is
       the shape this lab has spent the week removing: a missing input that
       produces a plausible answer instead of an error.

    `caller` is positional-only so it can never be shadowed by an argument the
    model happens to name `caller`, and it has no default because a refusal
    that cannot say whose call it was sends the reader to the wrong file.

    See :func:`unsupplied_arguments` for why a parameter with a default is
    exempt from rule 2.
    """
    missing = unsupplied_arguments(model, arguments)
    if missing:
        raise ModelArgumentUnsupplied(
            f"{model_name(model)} requires "
            + ", ".join(repr(name) for name in missing)
            + f", which {caller} does not build. That caller supplies "
            + f"{sorted(arguments)}. Nothing was priced: a model handed nothing "
            "where it asked for a table would price from a substitute and "
            "report the result in intervals, which is a wrong number wearing "
            "a right number's clothes. Either build the argument at the caller "
            "or give the parameter a default, which declares that the model "
            "has a defined behaviour without it."
        )
    try:
        parameters = inspect.signature(model).parameters
    except (TypeError, ValueError):
        return model(**arguments)
    if any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters.values()):
        return model(**arguments)
    passable = {
        name
        for name, parameter in parameters.items()
        if parameter.kind
        in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY)
    }
    return model(**{k: v for k, v in arguments.items() if k in passable})


def history_before(
    games: pd.DataFrame, day: str, *, game_day_column: str = "slate_date"
) -> pd.DataFrame:
    """The games a pricer may see on `day`: those dated **strictly earlier**.

    One definition, used by :func:`walk_forward` for every measured day and by
    the gameday card for the day it prices. Two copies of this cut is how a
    card comes to be fitted on a population no measurement ever saw; the
    football lab's defect 13 was the same comparison written with `<=` in one
    of its two places.
    """
    if games is None or games.empty or game_day_column not in games.columns:
        return pd.DataFrame(columns=list(getattr(games, "columns", [])))
    return games[games[game_day_column].astype(str) < str(day)]


def walk_forward(
    prices: pd.DataFrame,
    games: pd.DataFrame,
    *,
    price_day: Callable[..., pd.DataFrame | None],
    day_column: str = "slate_date",
    game_day_column: str = "slate_date",
) -> pd.DataFrame:
    """Price each slate day from games **strictly earlier** than it.

    The pricer never receives the whole table, so it cannot accidentally fit on
    the future — which is the football lab's defect 13, where a distribution
    loaded once outside the loop meant the model pricing 2023 had seen 2025, and
    only the markets that consumed it looked good.

    `price_day` is called once per day, in date order, with keyword arguments
    ``day``, ``history`` and ``prices``. It returns the day's priced rows or
    nothing. Every returned row is stamped with ``priced_through``, the latest
    game day the pricer was actually allowed to see, and that stamp is what
    :func:`assert_walk_forward` checks — a report cannot claim to be
    walk-forward, it has to carry the evidence.
    """
    require_columns(prices, (day_column, "event_id"), "the price frame")
    if not prices.empty:
        require_columns(games, (game_day_column,), "the games frame")
    produced: list[pd.DataFrame] = []
    for day in sorted(str(d) for d in prices[day_column].dropna().unique()):
        history = history_before(games, day, game_day_column=game_day_column)
        day_prices = prices[prices[day_column].astype(str) == day]
        priced = price_day(day=day, history=history, prices=day_prices)
        if priced is None or len(priced) == 0:
            continue
        priced = pd.DataFrame(priced).copy()
        through = ""
        if not history.empty:
            through = str(history[game_day_column].astype(str).max())
        priced["priced_through"] = through
        priced[day_column] = day
        unknown = set(priced["event_id"]) - set(day_prices["event_id"])
        if unknown:
            raise BacktestError(
                f"The pricer returned {len(unknown)} row group(s) on {day} for "
                "events nobody quoted that day. A bet on a game with no price "
                "is not a bet, and counting one manufactures a wager the card "
                "could never have taken."
            )
        produced.append(priced)
    if not produced:
        return pd.DataFrame(columns=list(prices.columns) + ["priced_through"])
    return pd.concat(produced, ignore_index=True)


def assert_walk_forward(
    bets: pd.DataFrame, *, day_column: str = "slate_date"
) -> None:
    """Raise if any bet was priced by a model that had seen its own game.

    Checked on the stamp rather than trusted from the code path, because the
    code path is exactly what was wrong in the lab this guard is ported from.
    """
    if bets.empty or "priced_through" not in bets.columns:
        return
    through = bets["priced_through"].astype(str)
    day = bets[day_column].astype(str)
    leaked = bets[(through != "") & (through >= day)]
    if not leaked.empty:
        raise WalkForwardLeak(
            f"{len(leaked):,} bet(s) were priced through a day at or after the "
            "day they bet on. A model that has seen the game it is pricing "
            "does not have an edge, it has the answer — and the football lab's "
            "compound markets looked good for exactly this reason."
        )


# --------------------------------------------------------------------------
# The null baseline, which is computed before anything else is believed
# --------------------------------------------------------------------------


def _interval(frame: pd.DataFrame, *, looks: int) -> S.RoiInterval:
    """Two-way clustered interval over a graded frame. Game and day, wider wins."""
    usable = settled(frame)
    if usable.empty:
        return S.RoiInterval(0.0, 0.0, 0.0, 0, 0, looks=looks)
    return S.interval_two_way(
        usable.assign(
            profit_units=pd.to_numeric(usable["profit_units"], errors="coerce")
        ),
        looks=looks,
    )


def null_baseline(universe: pd.DataFrame, *, looks: int = 1) -> list[dict]:
    """What betting one side with no model at all returns, per market and tier.

    Blind and mechanical: every quoted wager on that side, one bet per wager at
    the best price, graded. It is computed **before** any model number is looked
    at and printed above it, because a model whose bets are 90% unders in a
    season when blind unders returned +3% has not found anything, and the only
    way to see that is to have the blind number in hand first.

    Team totals produce `home_over`/`away_under` and the like; those roll into
    the `over` and `under` baselines by their second word, which is the side the
    bet is on.
    """
    if universe.empty:
        return []
    rows: list[dict] = []
    graded = settled(universe)
    if graded.empty:
        return []
    side = graded["selection"].astype(str).map(_baseline_side)
    for tier in _tiers_in(graded):
        for market in sorted(str(m) for m in graded["market"].dropna().unique()):
            cell = (graded["market"].astype(str) == market) & (
                graded["tier"].astype(str) == tier
            )
            for name in BASELINE_SIDES:
                chunk = graded[cell & (side == name)]
                if chunk.empty:
                    continue
                rows.append(
                    _interval_row(
                        _interval(chunk, looks=looks),
                        market=market,
                        tier=tier,
                        name=f"always {name}",
                    )
                )
            for name, chunk in favourite_and_underdog(graded[cell]).items():
                if chunk.empty:
                    continue
                rows.append(
                    _interval_row(
                        _interval(chunk, looks=looks),
                        market=market,
                        tier=tier,
                        name=f"always the {name}",
                    )
                )
    return rows


def _baseline_side(selection: str) -> str:
    """`home_over` is an over; `away` is an away. The side the bet is on."""
    text = str(selection)
    if "_" in text:
        text = text.split("_", 1)[1]
    return text if text in BASELINE_SIDES else ""


def favourite_and_underdog(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Split a two-sided market into the short price and the long one.

    By price rather than by name, because "favourite" is a fact about the
    number. A wager whose two sides are not both quoted contributes to neither
    — a one-sided group cannot say which side was favoured, and guessing is how
    a baseline stops being blind.
    """
    if frame.empty or "american_odds" not in frame.columns:
        return {"favourite": frame.iloc[0:0], "underdog": frame.iloc[0:0]}
    keys = [
        c
        for c in ("event_id", "market", "segment", "player", "line")
        if c in frame.columns
    ]
    payout = frame["american_odds"].map(decimal_payout)
    working = frame.assign(_payout=payout)
    working = working[working["_payout"] > float("-inf")]
    if working.empty or not keys:
        return {"favourite": frame.iloc[0:0], "underdog": frame.iloc[0:0]}
    grouped = working.groupby(keys, dropna=False)["_payout"]
    sizes = grouped.transform("size")
    two_sided = working[sizes == 2]
    if two_sided.empty:
        return {"favourite": frame.iloc[0:0], "underdog": frame.iloc[0:0]}
    lowest = two_sided.groupby(keys, dropna=False)["_payout"].transform("min")
    favourite = two_sided[two_sided["_payout"] == lowest].drop(columns=["_payout"])
    underdog = two_sided[two_sided["_payout"] > lowest].drop(columns=["_payout"])
    return {"favourite": favourite, "underdog": underdog}


def side_concentration(bets: pd.DataFrame) -> tuple[str, float]:
    """The side this cell's bets mostly sit on, and what share of them do.

    Returns `("", 0.0)` when the bets are spread across sides. Used to say
    beside a result that it may be a side bias rather than a model — see
    :data:`SIDE_CONCENTRATION`.
    """
    if bets.empty:
        return "", 0.0
    sides = bets["selection"].astype(str).map(_baseline_side)
    sides = sides[sides != ""]
    if sides.empty:
        return "", 0.0
    counts = sides.value_counts()
    top = str(counts.index[0])
    return top, float(counts.iloc[0] / len(sides))


# --------------------------------------------------------------------------
# Key numbers and the half point
# --------------------------------------------------------------------------


def key_numbers(
    values: Sequence[float] | pd.Series, *, coverage: float = KEY_NUMBER_COVERAGE
) -> dict:
    """The most common integer outcomes, measured from the games supplied.

    Never a list carried over from another sport. The NFL's key numbers are 3
    and 7 because of how football scores; basketball's margin distribution is a
    different shape, and a hardcoded list would be a fact about the wrong game.

    Returns the integers, most frequent first, that together cover `coverage`
    of the population, each with its measured share and its `n`.
    """
    series = pd.to_numeric(pd.Series(list(values)), errors="coerce").dropna()
    if series.empty:
        return {"n": 0, "numbers": [], "coverage": 0.0}
    rounded = series.round().astype(int).abs()
    counts = rounded.value_counts().sort_values(ascending=False)
    total = int(counts.sum())
    numbers: list[dict] = []
    running = 0
    for value, count in counts.items():
        numbers.append(
            {
                "value": int(value),
                "games": int(count),
                "share": float(count / total),
            }
        )
        running += int(count)
        if running / total >= coverage:
            break
    return {
        "n": total,
        "numbers": numbers,
        "coverage": float(running / total) if total else 0.0,
    }


def ticket_margin(frame: pd.DataFrame) -> pd.Series:
    """How far the settled quantity finished from the number on the ticket.

    Positive is a win, negative is a loss, zero is a push. Reconstructed from
    `actual`, `line` and `selection`:

    * `over` / `home_over` / `away_over`: ``actual − line``
    * `under` / `home_under` / `away_under`: ``line − actual``
    * `home`: ``actual + line`` — `actual` is the home margin and `line` is that
      selection's own handicap, so a home side at −3.5 winning by 4 finishes
      +0.5 clear.
    * `away`: ``line − actual``

    **This reconstruction is never trusted on its own.** :func:`convention_check`
    scores it against the recorded outcome, and the half-point decomposition is
    refused when they disagree. A market convention this module guessed at is
    the kind of finding that supplies its own explanation.
    """
    if frame.empty:
        return pd.Series(dtype="float64")
    actual = pd.to_numeric(frame.get("actual"), errors="coerce")
    line = pd.to_numeric(frame.get("line"), errors="coerce").fillna(0.0)
    selection = frame["selection"].astype(str)
    side = selection.map(_baseline_side)
    margin = pd.Series(float("nan"), index=frame.index, dtype="float64")
    margin = margin.mask(side == "over", actual - line)
    margin = margin.mask(side == "under", line - actual)
    margin = margin.mask(selection == "home", actual + line)
    margin = margin.mask(selection == "away", line - actual)
    return margin


def convention_check(frame: pd.DataFrame) -> dict:
    """Does the reconstructed ticket margin agree with the recorded outcome?

    Returns the agreement rate and its `n`. A won bet must reconstruct positive
    and a lost bet negative; pushes and voids are not scored either way.
    """
    if frame.empty or "actual" not in frame.columns:
        return {"checked": 0, "agreed": 0, "rate": 0.0, "verified": False}
    margin = ticket_margin(frame)
    outcome = frame["outcome"].astype(str)
    scorable = margin.notna() & outcome.isin(["won", "lost"])
    checked = int(scorable.sum())
    if not checked:
        return {"checked": 0, "agreed": 0, "rate": 0.0, "verified": False}
    expected_positive = outcome == "won"
    agreed = int(((margin > 0) == expected_positive)[scorable].sum())
    rate = agreed / checked
    return {
        "checked": checked,
        "agreed": agreed,
        "rate": float(rate),
        "verified": bool(rate >= 1.0 - CONVENTION_TOLERANCE),
    }


def half_point_decomposition(
    bets: pd.DataFrame, *, looks: int = 1, key_number_set: Sequence[int] = ()
) -> dict:
    """How much of a result is half a point at a number, and how much is a view.

    A bet is **half-point-decided** when the settled quantity finished within
    half a point of the ticket's number — move the line half a point against it
    and the result changes. The rest of the bets were decided by a differing
    view of the game.

    Reported apart because they are different claims that behave completely
    differently: a model that is systematically half a point off the number has
    an opinion about rounding, and it evaporates the moment the market moves.
    """
    check = convention_check(bets)
    if not check["verified"]:
        return {
            "verified": False,
            "convention": check,
            "note": (
                "The ticket-margin reconstruction agreed with the recorded "
                f"outcome on {check['rate']:.1%} of {check['checked']:,} "
                "scorable bets, below the "
                f"{1 - CONVENTION_TOLERANCE:.0%} this module requires. The "
                "half-point decomposition is refused rather than computed on a "
                "convention that has not been verified."
            ),
        }
    margin = ticket_margin(bets)
    decided = margin.abs() <= 0.5
    on_key = pd.Series(False, index=bets.index)
    if len(key_number_set):
        numbers = {int(n) for n in key_number_set}
        line = pd.to_numeric(bets.get("line"), errors="coerce")
        on_key = line.round().abs().isin(numbers).fillna(False)
    return {
        "verified": True,
        "convention": check,
        "half_point_decided": _interval_row(
            _interval(bets[decided], looks=looks), name="decided by half a point"
        ),
        "half_point_at_a_key_number": _interval_row(
            _interval(bets[decided & on_key], looks=looks),
            name="decided by half a point at a measured key number",
        ),
        "a_view_of_the_game": _interval_row(
            _interval(bets[~decided], looks=looks),
            name="decided by more than half a point",
        ),
    }


# --------------------------------------------------------------------------
# Cells
# --------------------------------------------------------------------------


def _tiers_in(frame: pd.DataFrame) -> list[str]:
    present = {str(t) for t in frame["tier"].dropna().unique()}
    ordered = [t for t in TIER_ORDER if t in present]
    return ordered + sorted(present - set(ordered))


def _interval_row(
    interval: S.RoiInterval, *, name: str = "", market: str = "", tier: str = ""
) -> dict:
    """One measured cell as plain data, so `render` needs no objects."""
    return {
        "name": name,
        "market": market,
        "tier": tier,
        "roi": interval.roi,
        "low": interval.low,
        "high": interval.high,
        "adjusted_low": interval.adjusted_low,
        "adjusted_high": interval.adjusted_high,
        "bets": interval.bets,
        "clusters": interval.clusters,
        "cluster_unit": interval.cluster_unit,
        "looks": interval.looks,
        "standard_error": interval.standard_error,
        "enough_evidence": interval.enough_evidence,
        "verdict": interval.verdict(),
    }


def interval_from_row(row: dict) -> S.RoiInterval:
    """Rebuild the interval object from a record row, for re-rendering."""
    return S.RoiInterval(
        roi=float(row.get("roi", 0.0)),
        low=float(row.get("low", 0.0)),
        high=float(row.get("high", 0.0)),
        bets=int(row.get("bets", 0)),
        clusters=int(row.get("clusters", 0)),
        standard_error=float(row.get("standard_error", 0.0)),
        looks=int(row.get("looks", 1)),
        cluster_unit=str(row.get("cluster_unit", "game")),
    )


def by_market_and_tier(bets: pd.DataFrame, *, looks: int = 1) -> list[dict]:
    """The lead table: one cell per (market, tier). Never pooled."""
    if bets.empty:
        return []
    rows: list[dict] = []
    for tier in _tiers_in(bets):
        for market in sorted(str(m) for m in bets["market"].dropna().unique()):
            cell = bets[
                (bets["market"].astype(str) == market)
                & (bets["tier"].astype(str) == tier)
            ]
            if cell.empty:
                continue
            row = _interval_row(
                _interval(cell, looks=looks), market=market, tier=tier
            )
            side, share = side_concentration(cell)
            row["dominant_side"] = side
            row["dominant_share"] = share
            row["side_biased"] = bool(side and share >= SIDE_CONCENTRATION)
            rows.append(row)
    return rows


def by_tier(bets: pd.DataFrame, *, looks: int = 1) -> list[dict]:
    if bets.empty:
        return []
    return [
        _interval_row(
            _interval(bets[bets["tier"].astype(str) == tier], looks=looks),
            tier=tier,
            name=tier,
        )
        for tier in _tiers_in(bets)
    ]


def pooled(bets: pd.DataFrame, *, looks: int = 1) -> list[dict]:
    """Per market across every tier, and the whole. Never the headline.

    Computed because `docs/when_this_ends.md` applies the stopping rule to the
    pooled figure too, and printed under :data:`POOLED_CAVEAT` every time.
    """
    if bets.empty:
        return []
    rows = [
        _interval_row(
            _interval(bets[bets["market"].astype(str) == market], looks=looks),
            market=market,
            name=market,
        )
        for market in sorted(str(m) for m in bets["market"].dropna().unique())
    ]
    rows.append(_interval_row(_interval(bets, looks=looks), name="every market"))
    return rows


# --------------------------------------------------------------------------
# The record
# --------------------------------------------------------------------------


def looks_from_ledger(ledger_path: Path | str | None) -> int:
    """The family size for any new claim: the ledger's **cumulative** count.

    Never the day's count. *"A search that runs every week is not twelve tests.
    It is twelve tests a week, forever."*

    An absent ledger returns 1, which applies no correction at all. That is the
    only safe *arithmetic* — inventing a family size would be worse — but it is
    NOT a safe thing to print without saying so, which is what
    `ledger_was_read` exists for. See its docstring.
    """
    if ledger_path is None:
        return 1
    return max(load_ledger(Path(ledger_path)).count, 1)


def ledger_was_read(ledger_path: Path | str | None) -> bool:
    """Whether a ledger actually existed, as distinct from holding one entry.

    **The report said "1 cumulative hypotheses in experiment_ledger.json" for a
    ledger that was not there.** `looks_from_ledger` returns
    `max(count, 1)`, so an absent file and a file with a single entry are the
    same integer, and the renderer stated that integer as a fact about a file
    it had never opened.

    That is the defect this repository is arranged against, in the one place it
    does the most damage: a correction of x1.00 does not widen an interval at
    all, so an absent ledger makes every result look **more** significant than
    it is, and the sentence claiming otherwise reads like a measurement.

    Caught when a discovery run was pointed at a fresh `--output-dir` and
    cheerfully reported a family of one.
    """
    if ledger_path is None:
        return False
    return Path(ledger_path).is_file()


@dataclass
class BacktestInputs:
    """Everything a run measures, already graded. Assembled by the script."""

    #: Every graded wager the board offered, one bet per wager at the best
    #: price. The null baseline runs over this.
    universe: pd.DataFrame = field(default_factory=pd.DataFrame)
    #: The subset a card would have staked.
    bets: pd.DataFrame = field(default_factory=pd.DataFrame)
    #: Settled quantities from the fitted population, for the key numbers.
    margins: pd.Series = field(default_factory=lambda: pd.Series(dtype="float64"))
    totals: pd.Series = field(default_factory=lambda: pd.Series(dtype="float64"))
    season_label: str = ""
    snapshot_phase: str = ""


def build_record(
    inputs: BacktestInputs,
    *,
    competition: Competition = CBB,
    looks: int = 1,
    ledger_read: bool = True,
    threshold: float = BET_EDGE_THRESHOLD,
    generated_at: str = "",
    calibration: dict | None = None,
) -> dict:
    """Every count this run made, as plain data. `render` is pure over it.

    The retention probe's rule, applied here for the same reason: improving a
    sentence must never cost a re-run, and a report that can only be produced by
    re-running the measurement is a report nobody improves.
    """
    universe = inputs.universe
    bets = inputs.bets
    if not universe.empty:
        require_columns(universe, BET_COLUMNS, "the graded price universe")
    if not bets.empty:
        require_columns(bets, BET_COLUMNS, "the graded bet frame")
        assert_walk_forward(bets)

    margin_keys = key_numbers(inputs.margins)
    total_keys = key_numbers(inputs.totals)
    key_set = [n["value"] for n in margin_keys["numbers"]]

    return {
        "record_version": RECORD_VERSION,
        "competition": competition.key,
        "title": competition.title,
        "generated_at": generated_at,
        "season_label": inputs.season_label,
        "snapshot_phase": inputs.snapshot_phase,
        "edge_threshold": float(threshold),
        "minimum_bets": S.MINIMUM_BETS,
        "looks": int(looks),
        # Recorded so `render` cannot restate a family size it never read. An
        # absent ledger and a one-entry ledger are the same integer.
        "ledger_read": bool(ledger_read),
        "correction_factor": S.bonferroni_factor(int(looks)),
        "wagers_offered": int(len(universe)),
        "wagers_graded": int(len(settled(universe))),
        "bets_taken": int(len(bets)),
        "bets_graded": int(len(settled(bets))),
        "games": int(bets["event_id"].nunique()) if not bets.empty else 0,
        "days": int(bets["slate_date"].nunique()) if not bets.empty else 0,
        "null_baseline": null_baseline(universe, looks=looks),
        "by_market_and_tier": by_market_and_tier(bets, looks=looks),
        "by_tier": by_tier(bets, looks=looks),
        "pooled": pooled(bets, looks=looks),
        "all_opinions": (
            _interval_row(_interval(universe, looks=looks), name="every opinion")
            if not universe.empty
            else {}
        ),
        "key_numbers": {"margin": margin_keys, "total": total_keys},
        "half_point": half_point_decomposition(
            settled(bets), looks=looks, key_number_set=key_set
        )
        if not bets.empty
        else {"verified": False, "note": NOTHING_TO_MEASURE},
        "calibration": calibration or {},
    }


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------


def roi_cells(row: dict) -> tuple[str, str, str]:
    """The return, its interval and the corrected interval — or three dashes.

    **Below `stats.MINIMUM_BETS` there is no number.** `stats.roi_table_row`
    prints the figure regardless, which is right for a table of measured
    markets and wrong here: *"a +12% return over 40 bets and a coin flip are the
    same claim at that sample size"*, and printing the +12% invites somebody to
    quote it out of the row that qualifies it.
    """
    if not row:
        return "—", "—", "—"
    if not row.get("enough_evidence"):
        return "—", "—", "—"
    return (
        f"{row['roi']:+.1%}",
        f"{row['low']:+.1%} to {row['high']:+.1%}",
        f"{row['adjusted_low']:+.1%} to {row['adjusted_high']:+.1%}",
    )


#: The header every ROI table in this report uses. It says **Clusters**, not
#: "Games", because `stats.interval_two_way` clusters by game *and* by day and
#: keeps the wider of the two — so two rows of one table are routinely
#: clustered differently, and a column headed "Games" printed a day count on
#: some rows and a game count on others with nothing to tell them apart. The
#: brief asks for both clusterings and for the sample size beside every number;
#: a count whose unit the reader has to guess is not a sample size.
CLUSTER_TABLE_HEADER = (
    "| Market | Bets | Clusters | ROI | 95% interval | Family-corrected "
    "| Verdict |\n"
    "|:---|---:|---:|---:|:---|:---|:---|"
)


def cluster_cell(row: dict) -> str:
    """`513 days` or `11,071 games` — the count and the clustering, always both.

    Read from the row's own `cluster_unit`, which :func:`_interval_row` copies
    off the `RoiInterval` that `stats.interval_two_way` chose. There is no
    default that could silently be wrong: a row carrying no `cluster_unit` was
    not built by this module, and it prints `unknown-clusters` rather than
    being assumed to be games.
    """
    unit = str(row.get("cluster_unit") or "").strip() or "unknown-cluster"
    return f"{int(row.get('clusters', 0) or 0):,} {unit}s"


def _row(row: dict, label: str) -> str:
    roi, interval, corrected = roi_cells(row)
    return (
        f"| {label} | {row.get('bets', 0):,} | {cluster_cell(row)} | "
        f"{roi} | {interval} | {corrected} | {row.get('verdict', '')} |"
    )


def _nothing(what: str) -> list[str]:
    return [
        f"**{NOTHING_TO_MEASURE.capitalize()}.** {what} No historical price has "
        "been bought for this sport yet, so this section has no rows. It is "
        "said in words rather than shown as an empty table, because an empty "
        "table reads as a null result and a null result is a claim.",
        "",
    ]


def render(record: dict) -> str:
    """The report, as a pure function of the record. No clock, no network."""
    lines: list[str] = []
    add = lines.append
    add(f"# {record.get('title', CBB.title)} — price backtest")
    add("")
    if record.get("generated_at"):
        add(f"Generated {record['generated_at']}.")
        add("")
    add(
        "**Walk-forward only.** Every model that priced a game was built from "
        "games strictly earlier than it, and every bet carries the day it was "
        "priced through. The stamp is checked rather than the code path: the "
        "football lab's compound markets looked good because a distribution "
        "loaded once outside the season loop had seen the future."
    )
    add("")
    add(
        "**One wager is one bet, at the best price.** Twenty-one books quoting "
        "one game is not twenty-one bets — counting it that way narrowed the "
        "NHL lab's intervals by about √2.83 and turned three markets that span "
        "zero into three demonstrated losses."
    )
    add("")

    bets = int(record.get("bets_graded", 0))
    add(
        f"**{bets:,} graded bets** from {record.get('wagers_graded', 0):,} "
        f"graded wagers offered, across {record.get('games', 0):,} games and "
        f"{record.get('days', 0):,} slate days, at an edge threshold of "
        f"{record.get('edge_threshold', 0):.0%} declared in advance."
    )
    add("")
    looks = int(record.get("looks", 1))
    if record.get("ledger_read", True):
        add(
            f"**Family correction: {looks:,} cumulative hypotheses** in the "
            f"experiment ledger, widening every 95% interval by "
            f"x{record.get('correction_factor', 1.0):.2f}. That is the ledger's "
            "cumulative count and never the day's — correcting today's findings "
            "across today's tests is a lie if more were tested last week."
        )
    else:
        add(
            "**NO FAMILY CORRECTION WAS APPLIED, because no experiment ledger "
            "was found.** Every interval below is the raw one. This is not a "
            "family of one — it is an unknown family, and an unknown family "
            "corrected by x1.00 makes every result on this page look more "
            "significant than it is. Read nothing here as corrected until a "
            "ledger is in place and this run is repeated."
        )
    add("")
    add(
        f"**Below {record.get('minimum_bets', S.MINIMUM_BETS):,} bets there is "
        "no number**, only the words *not enough evidence*. That floor was "
        "declared before any price was bought."
    )
    add("")

    add("## The null baseline, first")
    add("")
    add(
        "*The question that broke the football lab's best result was never "
        "\"is this robust\". It was: what would betting one side with no model "
        "at all return?* So it is answered here, before any model number "
        "appears, and every model result below is read against it."
    )
    add("")
    baseline = record.get("null_baseline") or []
    if not baseline:
        lines.extend(_nothing("No blind side could be graded."))
    else:
        add(
            "| Tier | Market | Blind side | Bets | Clusters | ROI "
            "| 95% interval | Family-corrected | Verdict |"
        )
        add("|:---|:---|:---|---:|---:|---:|:---|:---|:---|")
        for row in baseline:
            roi, interval, corrected = roi_cells(row)
            add(
                f"| {row['tier']} | {row['market']} | {row['name']} | "
                f"{row['bets']:,} | {cluster_cell(row)} | {roi} | {interval} | "
                f"{corrected} | {row['verdict']} |"
            )
        add("")

    add("## The model, per market and per conference tier")
    add("")
    add(
        "The lead table, and the only one that is a headline. **6 high-major "
        "conferences / 79 teams, 10 mid-major / 122, 17 low-major / 164** are "
        "three different distributions, and this lab exists because the third "
        "is plausibly priced with less attention."
    )
    add("")
    cells = record.get("by_market_and_tier") or []
    if not cells:
        lines.extend(_nothing("No model bet has been graded."))
    else:
        add(
            "| Tier | Market | Bets | Clusters | ROI | 95% interval "
            "| Family-corrected | Verdict |"
        )
        add("|:---|:---|---:|---:|---:|:---|:---|:---|")
        for row in cells:
            roi, interval, corrected = roi_cells(row)
            add(
                f"| {row['tier']} | {row['market']} | {row['bets']:,} | "
                f"{cluster_cell(row)} | {roi} | {interval} | {corrected} | "
                f"{row['verdict']} |"
            )
        add("")
        biased = [r for r in cells if r.get("side_biased")]
        if biased:
            add(
                f"**{len(biased)} cell(s) are one side wearing a model's "
                "clothes.** At least "
                f"{SIDE_CONCENTRATION:.0%} of their bets sit on a single side, "
                "so read each against that side's blind return in the table "
                "above before reading it as a model result:"
            )
            add("")
            for row in biased:
                add(
                    f"- {row['tier']} / {row['market']}: "
                    f"{row['dominant_share']:.0%} of bets on "
                    f"**{row['dominant_side']}**."
                )
            add("")

    add("### Per tier, across markets")
    add("")
    tiers = record.get("by_tier") or []
    if not tiers:
        lines.extend(_nothing("No tier has a graded bet."))
    else:
        add(CLUSTER_TABLE_HEADER.replace("| Market |", "| Tier |"))
        for row in tiers:
            add(_row(row, row.get("name", row.get("tier", ""))))
        add("")

    add("## Pooled")
    add("")
    add(POOLED_CAVEAT)
    add("")
    pooled_rows = record.get("pooled") or []
    if not pooled_rows:
        lines.extend(_nothing("Nothing to pool."))
    else:
        add(CLUSTER_TABLE_HEADER)
        for row in pooled_rows:
            add(_row(row, row.get("name", "")))
        add("")

    add("## Half a point at a key number, or a view of the game")
    add("")
    add(
        "A model that is systematically half a point away from the number has "
        "an opinion about rounding rather than about the game, and it "
        "evaporates the moment the market moves. The two are reported apart."
    )
    add("")
    margin_keys = (record.get("key_numbers") or {}).get("margin") or {}
    if margin_keys.get("numbers"):
        named = ", ".join(
            f"**{n['value']}** ({n['share']:.1%})" for n in margin_keys["numbers"]
        )
        add(
            f"Key numbers **measured** from {margin_keys['n']:,} games in the "
            f"fitted population, most frequent first to "
            f"{margin_keys['coverage']:.0%} coverage: {named}. Never a list "
            "carried over from another sport — the NFL's 3 and 7 are a fact "
            "about how football scores."
        )
        add("")
    half = record.get("half_point") or {}
    if not half.get("verified"):
        add(
            f"**Not reported.** {half.get('note', NOTHING_TO_MEASURE)}"
        )
        add("")
    else:
        add(CLUSTER_TABLE_HEADER.replace("| Market |", "| Decided by |"))
        for key in (
            "half_point_decided",
            "half_point_at_a_key_number",
            "a_view_of_the_game",
        ):
            row = half.get(key) or {}
            if row:
                add(_row(row, row.get("name", key)))
        add("")
        check = half.get("convention") or {}
        add(
            "The handicap convention behind this split was checked against the "
            f"recorded outcomes first: it agreed on {check.get('agreed', 0):,} "
            f"of {check.get('checked', 0):,} scorable bets "
            f"({check.get('rate', 0.0):.2%}). A decomposition on an unverified "
            "convention is the most dangerous kind of finding, because it "
            "supplies its own explanation."
        )
        add("")

    calibration = record.get("calibration") or {}
    if calibration:
        from cbb_betting_lab.reports import calibration_on_selected as C

        lines.extend(C.render_section(calibration))

    add("## What this report cannot say")
    add("")
    add(
        "- It cannot say a market is a play. **No market is allowlisted**, "
        "`staging_provider_policy` ships manual-only, and that is the correct "
        "state. An excluded market is never a pass, an avoid, or a no-value "
        "call."
    )
    add(
        "- It cannot say an edge is **reachable**. That is `reachability.py`'s "
        "question, and an edge living entirely in prices that vanished is "
        "reported there as not reachable regardless of its size."
    )
    add(
        "- It cannot rule a model **in** on calibration. Where a priced test "
        "exists, the priced test decides."
    )
    add(
        "- It cannot replicate itself. A held-out season is "
        "`replication.py`'s job, and a window that merely fails to contradict "
        "is not confirmation."
    )
    return "\n".join(lines).rstrip() + "\n"


# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------


def record_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name("price_backtest", ".json")


def report_path(competition: Competition, output_dir: Path) -> Path:
    return Path(output_dir) / competition.output_name("price_backtest", ".md")


def ledger_path(output_dir: Path) -> Path:
    return Path(output_dir) / LEDGER_FILENAME


def write_record(record: dict, path: Path) -> Path:
    import json

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(record, indent=2, default=str) + "\n", encoding="utf-8")
    return target


def read_record(path: Path) -> dict:
    import json

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    version = int(payload.get("record_version", 0))
    if version != RECORD_VERSION:
        raise BacktestError(
            f"{Path(path).name} is a version {version} record and this module "
            f"writes version {RECORD_VERSION}. Re-run the backtest rather than "
            "re-rendering a record whose shape has changed — a stale record "
            "renders a report with holes in it and nothing looks wrong."
        )
    return payload


def write_report(record: dict, path: Path) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(render(record), encoding="utf-8")
    return target
