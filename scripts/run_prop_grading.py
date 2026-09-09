#!/usr/bin/env python3
"""Score the player-prop model against a de-vigged fair price. Design section 10.

    # The whole store, walk-forward, model and control, scored once:
    PYTHONPATH=src python scripts/run_prop_grading.py --progress

    # Re-render the report from the committed record at today's ledger count:
    PYTHONPATH=src python scripts/run_prop_grading.py --rebuild-report-only

`reports/prop_grading.py` owns every number. **This file owns the wiring**: the
gate, the walk-forward pricing, the control, the settlement, and handing the
result over.

## The gate, first, and it is two receipts

Nothing here scores anything until both halves of design section 10's gate have
run **in this process**:

1. `player_census.assert_reconciles` — the store's own wager count, taken with
   `usecols=` and `chunksize=` over the 978 MB file, reconciled clause by clause
   against the frozen artifact.
2. `player_census.assert_every_offered_prop_is_accounted` — the run's own
   accounting that every prop the store offered landed in exactly one bucket,
   with a residual of exactly 0.

The second is filed by `reports.gameday_card.opinions_for` as it prices, one
`file()` per wager, which is the only function in the tree that decides what
becomes of a prop and therefore the only one that can say which bucket a wager
landed in. `scripts/run_prop_accounting.py` is the census-only run of the same
identity; this is the run that goes on to grade, so it files its own
dispositions rather than trusting a receipt from another process. A receipt
lives for the length of one process and does not outlive it: that is deliberate,
and it is why this script cannot skip the accounting by pointing at
`data/outputs/cbb_prop_accounting.json`.

## The control is priced HERE, beside the model, on the same walk-forward cut

The identity-blind role-prior control is the model with the athlete's identity
removed and his ROLE kept: the same minutes lattice, the same lines, the same
engine — with every per-minute rate replaced by the role prior at his
projected-minutes bucket and the scoring mix replaced by the league's. That is
`player_rates.shrink_rate` with the credibility weight at zero, and
`tests/test_player_model_leakage.py` has asserted it is buildable from that
module's public helpers since before the engine existed.

It is priced in the same loop, off the same `SlateModel`, so it can never see a
different day's evidence from the model it is a control for. **It is not a
second model and it files no disposition**: the accounting identity is about
what became of each prop under THE model, and filing the control's decisions
into it would count every wager twice.

A subject the control cannot price is counted, not defaulted. Its wager keeps a
missing control probability, `prop_grading.scorable` excludes the row and the
population census reports it under `no_control_probability` — the alternative,
falling back to the model's own number, would compare the model against itself
and the comparison would look fine.

## Settlement is the backtest's, imported rather than rewritten

`_grade_one` and `player_index` live in `scripts/run_price_backtest.py` and are
loaded by path, because `scripts/` is not a package and never will be. A second
copy of the settlement wiring would be free to disagree with the shipped one
about which box-score row settles a prop, and the direction such a copy drifts
in gives a plausible number and the wrong bet with nothing raising.

## What it writes

`data/outputs/cbb_prop_grading.{json,md}`. The record keeps what the run was
scored at; the report is re-rendered at the experiment ledger's CURRENT count
through `restatement`, so registering a hypothesis retracts what it has to
retract and can never manufacture a claim.

## What it does not do

It files no acceptance receipt, writes nothing under `data/manual/`, creates no
`grant()`, and allowlists nothing. It places no bet and recommends none: no
player prop can reach `Availability.CONFIRMED` in this lab, so nothing measured
here can become a selection whatever it says. `player_first_basket` and
`player_double_double` are refused BY NAME, are never scored, and are not a
pass, an avoid or a no-value call.
"""

from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from cbb_betting_lab import restatement as RESTATEMENT
from cbb_betting_lab import stats as S
from cbb_betting_lab.experiment_ledger import load as load_ledger
from cbb_betting_lab.competitions import (
    Competition,
    DEFAULT_COMPETITION_KEY,
    competition_for,
)
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from cbb_betting_lab.models import player_census as PC
from cbb_betting_lab.models import player_distributions as PD
from cbb_betting_lab.models import player_rates as PR
from cbb_betting_lab.models import slate
from cbb_betting_lab.providers import historical as H
from cbb_betting_lab.reports import card_matchups, card_pricing, gameday_card
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.reports import prop_grading as PG
from cbb_betting_lab.season import clean_text
from cbb_betting_lab.stores import normalise_subject

#: The model that answers for both halves of a slate. **Not
#: `price_backtest.DEFAULT_MODEL`**, which resolves the team seam alone and
#: declares no `player_history`: under it every prop lands in `never_asked`, the
#: accounting identity still closes at residual 0, and this run would score a
#: model that was never asked a single question.
PLAYER_MODEL = "cbb_betting_lab.models.slate:slate_model"

#: What the control IS, in one string, written into the record so a reader of
#: the record never has to infer it from a script.
CONTROL_DESCRIPTION = (
    "identity-blind role-prior control: the same engine, the same minutes "
    "lattice and the same lines, with every per-minute rate replaced by "
    "`role_prior[stat][projected-minutes bucket]` and the scoring mix replaced "
    "by the league `value_pmf` — `player_rates.shrink_rate` at credibility "
    "weight zero"
)

#: Every column of the price store this run opens.
STORE_COLUMNS_THE_RUN_READS: tuple[str, ...] = (
    "event_id",
    "market",
    "segment",
    "player",
    "selection",
    "line",
    "book",
    "snapshot_phase",
    "american_odds",
    "game_id",
    "season",
    "slate_date",
    "commence_time",
    "home_team",
    "away_team",
    "home_name",
    "away_name",
    "tier",
)

CHUNK_ROWS = PC.CHUNK_ROWS

EXIT_OK = 0
EXIT_NOTHING_TO_MEASURE = 2
EXIT_DOES_NOT_RECONCILE = 3
EXIT_NO_MODEL = 4
EXIT_INPUTS_ABSENT = 5


class NothingToMeasure(RuntimeError):
    """A precondition is absent, so nothing was scored and nothing was written."""


# --------------------------------------------------------------------------
# The settlement wiring, loaded from the shipped backtest rather than copied
# --------------------------------------------------------------------------


def _backtest_module():
    """`scripts/run_price_backtest.py`, by path. `scripts/` is not a package.

    Loaded rather than re-implemented so this run settles a prop exactly the way
    the shipped backtest does — same fixture bundle, same player index, same
    ambiguity refusal, same `settle()` call. `tests/test_prop_grading.py` holds
    the two functions this reaches for by name, so a rename over there is a red
    build here rather than a silent fallback.
    """
    path = Path(__file__).resolve().parent / "run_price_backtest.py"
    spec = importlib.util.spec_from_file_location("_prop_grading_backtest", path)
    if spec is None or spec.loader is None:  # pragma: no cover - unreachable
        raise NothingToMeasure(f"{path} could not be loaded, so nothing can settle.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    for name in ("_grade_one", "player_index", "fixture_index", "GradingCensus"):
        if not hasattr(module, name):
            raise NothingToMeasure(
                f"{path} no longer defines {name!r}. This run settles through "
                "the shipped backtest's own wiring on purpose; a local copy "
                "would be free to disagree with it about which box-score row "
                "settles a prop."
            )
    return module


# --------------------------------------------------------------------------
# The store, fingerprinted and read by the run itself
# --------------------------------------------------------------------------


def store_digest(path: Path) -> tuple[str, int]:
    """sha256 and byte length of the file THIS run opened, read in blocks.

    Computed here rather than taken off the census: a digest handed over by the
    thing it is meant to check is not a check, and `data/processed/` is a tree
    of symlinks into a shared checkout.
    """
    hasher = hashlib.sha256()
    size = 0
    with open(path, "rb") as handle:
        while True:
            block = handle.read(1 << 22)
            if not block:
                break
            size += len(block)
            hasher.update(block)
    return hasher.hexdigest(), size


def load_offered_props(path: Path, *, chunksize: int = CHUNK_ROWS) -> pd.DataFrame:
    """Every player-prop quote in the store, and no other row.

    `usecols=` and `chunksize=` on the one `read_csv` this module makes of the
    price store: the file is 978 MB and the player rows are an eighth of it.
    """
    header = pd.read_csv(path, nrows=0)
    missing = [c for c in STORE_COLUMNS_THE_RUN_READS if c not in header.columns]
    if missing:
        raise NothingToMeasure(
            f"{path} is missing {missing}. Nothing is defaulted: a missing "
            "column read as a zero is how a wiring fault becomes a finding."
        )
    kept: list[pd.DataFrame] = []
    for chunk in pd.read_csv(
        path,
        usecols=list(STORE_COLUMNS_THE_RUN_READS),
        chunksize=chunksize,
        low_memory=False,
    ):
        props = chunk[
            chunk["market"].astype(str).str.startswith(PC.PLAYER_MARKET_PREFIX, na=False)
        ]
        if not props.empty:
            kept.append(props)
    if not kept:
        raise NothingToMeasure(
            f"{path} holds no row whose market begins "
            f"`{PC.PLAYER_MARKET_PREFIX}`. A store with no prop in it and a "
            "store this run failed to read look identical from here."
        )
    return pd.concat(kept, ignore_index=True)


# --------------------------------------------------------------------------
# The control
# --------------------------------------------------------------------------


def identity_blind(projection, *, shapes):
    """The same projection with the athlete's identity taken out of the rates.

    His ROLE stays: the projected-minutes bucket picks the role prior, and the
    minutes lattice is untouched. His identity goes: the per-minute rate is the
    bucket's prior rather than his own banked rate shrunk toward it, and the
    1/2/3 scoring mix is the league's rather than his own shrunk toward it.
    That is exactly `shrink_rate` at credibility weight zero, and it is written
    as a `dataclasses.replace` of the real projection rather than as a second
    estimator so that every other field — the event, the lattice, the refusals,
    the walk-forward stamp — is the same object's.

    A stat the fit refused (R5) is absent from `projection.rates` and stays
    absent here: the control does not get to price a market the model was
    refused.
    """
    priors = shapes.value("role_prior")
    league = shapes.value("value_pmf")
    bucket = int(projection.minutes_bucket)
    rates = {
        stat: float(priors[stat][bucket])
        for stat in projection.rates
        if stat in priors and 0 <= bucket < len(priors[stat])
    }
    if len(rates) != len(projection.rates):
        # A rate the role table cannot answer for is a control that is not the
        # control, so the whole subject is refused rather than half-built.
        return None
    return dataclasses.replace(
        projection,
        rates=rates,
        prior_weight={stat: 0.0 for stat in rates},
        value_pmf=(float(league[0]), float(league[1]), float(league[2])),
        value_prior_events=0.0,
        value_mix_weight=0.0,
    )


def control_probabilities(
    wagers, model_slate, *, priced_keys: set, refusals: Counter
) -> tuple[dict, dict]:
    """`(probability, push)` maps for the control, keyed like the model's.

    Only the wagers the MODEL priced are asked, because the comparison is
    per-wager: a row the model declined has no model number to compare a control
    number against, and pricing it here would build a population the headline
    does not run over.

    One control `PlayerDistribution` per (event, athlete), cached exactly the
    way `opinions_for` caches the model's — design 2's rule, one subject one
    object, so a points rung and a pra rung on one athlete are two questions
    asked of one object and can never disagree.
    """
    probabilities: dict = {}
    pushes: dict = {}
    built: dict = {}
    for wager in wagers:
        if wager.key not in priced_keys:
            continue
        subject = (
            clean_text(wager.event_id),
            model_slate.resolved.get(
                (clean_text(wager.event_id), clean_text(wager.player))
            ),
        )
        cached = built.get(subject)
        if cached is None:
            projection = model_slate.projection_for(wager.event_id, wager.player)
            blind = (
                identity_blind(projection, shapes=model_slate.shapes)
                if projection is not None
                else None
            )
            if blind is None:
                cached = (
                    "the control could not be formed for this subject: the role "
                    "table answers for fewer stats than the model priced"
                )
            else:
                try:
                    cached = PD.build(blind, shapes=model_slate.shapes)
                except PD.PlayerDistributionError as exc:
                    cached = str(exc)
                except (TypeError, ValueError) as exc:
                    cached = f"the control distribution could not be built ({exc})"
            built[subject] = cached
        if isinstance(cached, str):
            refusals[cached] += 1
            continue
        probability, push, reason = gameday_card._read_player_market(wager, cached)
        if probability is None:
            refusals[reason or "the control has no reader for this market"] += 1
            continue
        probabilities[wager.key] = float(probability)
        pushes[wager.key] = float(push)
    return probabilities, pushes


# --------------------------------------------------------------------------
# The per-day pricer
# --------------------------------------------------------------------------


def make_price_day(
    model,
    *,
    competition: Competition,
    run: PC.RunDisposition,
    raw_dir: Path,
    rows: list,
    tier_of_key: dict,
    control_refusals: Counter,
    row_refusals: Counter,
    rows_that_became_no_wager: list,
    progress=None,
):
    """The `price_day` callable `walk_forward` drives, one slate day at a time.

    Every frame parameter is named for the key the caller cut it under and none
    carries a default: `price_backtest._refuse_undeclared_frames` refuses a
    pricer whose frame parameter has one, on the ground that a default is a
    pricer left to find the table some other way and every other way is uncut
    and unstamped.

    **The dispositions are filed by `opinions_for` and not here**, one per prop
    as it decides, in exactly one bucket, before the loop moves on.
    """

    def price_day(
        *,
        day: str,
        history: pd.DataFrame,
        prices: pd.DataFrame,
        player_history: pd.DataFrame,
    ):
        frame = prices.copy()
        model_slate = slate.SlateModel.coerce(
            PB.call_model(
                model,
                "the prop grading run's per-day pricer (make_price_day)",
                day=day,
                history=history,
                prices=frame,
                competition=competition,
                raw_dir=raw_dir,
                player_history=player_history,
            ),
            day=day,
            team_priced_through=PB.latest_day(history),
            player_priced_through="",
        )

        row_reasons: list[str] = []
        wagers, unparseable, reasons = card_pricing.build_wagers(
            frame,
            competition=competition,
            key_for=card_pricing.default_key_for(competition),
            row_reasons=row_reasons,
        )
        if unparseable:
            # NOT filed into a bucket and not silently dropped either: a row
            # that never became a wager has no wager key to file under, so it
            # is counted and the accounting identity below refuses.
            for reason, count in reasons.items():
                row_refusals[reason] += int(count)
            rows_that_became_no_wager.append((str(day), int(unparseable)))

        probabilities, _census = gameday_card.opinions_for(
            wagers, model_slate, day=day, dispositions=run
        )
        control, control_push = control_probabilities(
            wagers,
            model_slate,
            priced_keys=set(probabilities),
            refusals=control_refusals,
        )
        push_mass = _census.push_mass

        tier_by_event = {
            str(event): str(tier)
            for event, tier in zip(frame["event_id"], frame["tier"])
        }
        for wager in wagers:
            # Filled beside the filing, so the buckets can be reported per
            # tier afterwards. The wager key carries no event id -- it is
            # (market, segment, athlete, home, away, selection, line, day) --
            # so a caller that tried to recover the tier from the key alone
            # would recover nothing. The tier is the store's own column on the
            # wager's event and is never re-derived: design 9 tiers a team in
            # one place.
            tier_of_key[wager.key] = tier_by_event.get(str(wager.event_id), "")
        game_by_event = {
            str(event): game
            for event, game in zip(frame["event_id"], frame["game_id"])
        }
        for wager in wagers:
            if wager.key not in probabilities:
                continue
            for quote in wager.quotes:
                rows.append(
                    {
                        "event_id": wager.event_id,
                        "game_id": game_by_event.get(str(wager.event_id)),
                        "slate_date": wager.slate_date,
                        "market": wager.market,
                        "segment": wager.segment,
                        "player": wager.player,
                        "selection": wager.selection,
                        "line": wager.line,
                        "book": quote.book,
                        "american_odds": quote.american_odds,
                        "tier": tier_by_event.get(str(wager.event_id), "")
                        or wager.tier,
                        "model_probability": probabilities[wager.key],
                        "model_push_mass": float(push_mass.get(wager.key, 0.0)),
                        "control_probability": control.get(wager.key),
                        "control_push_mass": control_push.get(wager.key),
                    }
                )

        if progress is not None:
            progress(
                f"  {day}: {len(frame):,} quote(s) -> {len(wagers):,} wager(s), "
                f"{len(probabilities):,} priced, {len(control):,} controlled, "
                f"{len(rows):,} scored row(s) so far"
            )

        team_through = PB.latest_day(history)
        player_through = str(model_slate.player_priced_through)
        frame["player_priced_through"] = player_through
        frame["priced_through"] = max(team_through, player_through)
        return frame

    return price_day


# --------------------------------------------------------------------------
# Settlement
# --------------------------------------------------------------------------


def settle_rows(
    frame: pd.DataFrame,
    *,
    processed: Path,
    competition: Competition,
    backtest,
) -> tuple[pd.DataFrame, object]:
    """Add `outcome` to every scored row, through the shipped backtest's wiring."""
    if frame.empty:
        return frame.assign(outcome=pd.Series(dtype="object")), backtest.GradingCensus()
    team_games = pd.read_csv(
        processed / competition.output_name("team_games", ".csv"), low_memory=False
    )
    segments_path = processed / competition.output_name("game_segments", ".csv")
    game_segments = (
        pd.read_csv(segments_path, low_memory=False)
        if segments_path.is_file()
        else pd.DataFrame()
    )
    player_games = pd.read_csv(
        processed / competition.output_name("player_games", ".csv"), low_memory=False
    )
    game_ids = {
        int(value)
        for value in pd.to_numeric(frame["game_id"], errors="coerce").dropna().unique()
    }
    fixtures = backtest.fixture_index(team_games, game_segments, game_ids)
    players = backtest.player_index(player_games, game_ids)
    census = backtest.GradingCensus()
    outcomes: list[str] = []
    for record in frame.to_dict("records"):
        census.rows += 1
        outcome, _actual, note = backtest._grade_one(
            record, fixtures=fixtures, players=players, census=census
        )
        outcomes.append(outcome.value)
        if outcome.value == "unsettleable":
            census.unsettleable += 1
            if note:
                census.note(note)
            continue
        census.graded += 1
        census.won += int(outcome.value == "won")
        census.lost += int(outcome.value == "lost")
        census.push += int(outcome.value == "push")
        census.void += int(outcome.value == "void")
    return frame.assign(outcome=outcomes), census


def offered_counts(run: PC.RunDisposition, tier_of_key: dict, settled: pd.DataFrame) -> dict:
    """`tier` and `tier/market` -> what the store offered, priced and settled.

    Coverage is reported against THIS rather than against the scored frame: a
    frame that has already been filtered cannot say what it was filtered from.
    The offered and priced halves come from the run's own filing, which is the
    card's decision at the moment it made it; the settled half is counted off
    the settlement pass.
    """
    counts: dict = {}

    def bump(key: str, field: str, by: int = 1) -> None:
        counts.setdefault(key, {"offered": 0, "priced": 0, "settled": 0})[field] += by

    for key, (market, bucket) in run.filed.items():
        tier = tier_of_key.get(key) or ""
        if not tier:
            continue
        for scope in (tier, f"{tier}/{market}"):
            bump(scope, "offered")
            if bucket == PC.BUCKET_PRICED:
                bump(scope, "priced")
    if not settled.empty:
        graded = settled[
            settled["outcome"].astype(str).str.strip().str.lower().isin(("won", "lost"))
        ]
        # One row per wager, not per quote: `offered` and `priced` are wager
        # counts and a settled figure counted over quotes would not be
        # comparable with them.
        #
        # **The athlete is folded before the count is taken.** `offered` and
        # `priced` are keyed by `selection.selection_key`, which casefolds the
        # player, so a settled count taken on the book's raw spelling would be
        # the larger of the two numbers the census names -- 261,870 against
        # 257,474 -- sitting in the same coverage line as the smaller one.
        wagers = graded.assign(
            _subject=graded["player"].map(normalise_subject)
        ).drop_duplicates(
            subset=["event_id", "market", "_subject", "selection", "line"]
        )
        for tier, market in zip(wagers["tier"].astype(str), wagers["market"].astype(str)):
            if not tier:
                continue
            bump(tier, "settled")
            bump(f"{tier}/{market}", "settled")
    return counts


# --------------------------------------------------------------------------
# The two modes
# --------------------------------------------------------------------------


def registered_hypotheses(ledger_path: Path) -> list[dict]:
    """The 33 pre-registered player-prop hypotheses, read off the tracked ledger.

    Read rather than typed. The record then carries the question each cell
    answers, and `reports.prop_grading.answered_hypotheses` refuses a record in
    which a registered name found no cell — so a market renamed on one side and
    not the other is a refusal rather than a hypothesis that quietly vanishes
    from the answered table while every count still looks right.

    An absent ledger yields none, and the report then says in words that it was
    handed none rather than printing an empty table.
    """
    if not ledger_path.is_file():
        return []
    return [
        {
            "search": entry.search,
            "name": entry.name,
            "predicted_direction": entry.predicted_direction,
        }
        for entry in load_ledger(ledger_path).hypotheses
        if entry.search in (PG.SEARCH_VS_DEVIG, PG.SEARCH_VS_CONTROL)
    ]


def rebuild_report_only(
    *, record_path: Path, report_path: Path, ledger: Path | None = None
) -> int:
    """Re-render the markdown from the record. Scores nothing, spends nothing.

    **It re-reads the experiment ledger and restates every reading at today's
    cumulative count.** Replaying the correction the record stores is what let
    this lab hold three different corrections across its own documents at once.
    """
    if not record_path.is_file():
        print(
            f"::error::{record_path} does not exist, so there is no record to "
            "re-render. Run this script without --rebuild-report-only first; "
            "the report is a pure function of the record.",
            file=sys.stderr,
        )
        return EXIT_NOTHING_TO_MEASURE
    try:
        record = PG.read_record(record_path)
    except PG.PropGradingError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE
    correction = RESTATEMENT.current(ledger)
    was = int(record.get("looks", 1) or 1)
    stated = RESTATEMENT.widened(was, correction)
    PG.write_report(record, report_path, looks=stated)
    print(f"Wrote {report_path} from {record_path}.")
    if not correction.found:
        print(
            f"::warning::No experiment ledger at {ledger}, so every reading "
            f"stands at the {was:,} hypotheses this run was scored at. An "
            "absent ledger is an unknown family, never an empty one."
        )
    elif stated != was:
        print(
            f"Readings restated at {stated:,} cumulative hypotheses "
            f"(x{S.bonferroni_factor(stated):.4f}); the run was scored at "
            f"{was:,}."
        )
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument(
        "--window",
        default=H.CARD_WINDOW.name,
        choices=sorted(H.WINDOWS),
        help=(
            "Which snapshot store to score. `card` is the only window this "
            "lab's own card could have taken, and the census gate is frozen "
            "against that store."
        ),
    )
    parser.add_argument("--model", default=PLAYER_MODEL)
    parser.add_argument(
        "--days",
        type=int,
        default=0,
        help=(
            "Price only the first N slate days. FOR WIRING ONLY, and it can "
            "never pass: the store's side of the accounting identity is the "
            "whole store, so a run that priced part of it accounts for part of "
            "it and the gate refuses with the residual it found."
        ),
    )
    parser.add_argument("--chunksize", type=int, default=CHUNK_ROWS)
    parser.add_argument(
        "--progress",
        action="store_true",
        help=(
            "Print one line per slate day as it is priced. The whole store is "
            "140 slate days and hours of wall clock, and a run with no output "
            "is indistinguishable from a run that has hung."
        ),
    )
    parser.add_argument(
        "--write-scored",
        default="",
        help=(
            "Also write every scored row to this CSV. The record is the "
            "measurement; this is the frame it was computed from, for a later "
            "session that wants to check a cell by hand."
        ),
    )
    parser.add_argument("--no-write", action="store_true")
    parser.add_argument("--rebuild-report-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    competition = competition_for(args.competition)
    processed = Path(args.processed_dir)
    outputs = Path(args.output_dir)
    record_path = PG.record_path(competition, outputs)
    report_path = PG.report_path(competition, outputs)
    experiment_ledger = PG.ledger_path(outputs)

    if args.rebuild_report_only:
        return rebuild_report_only(
            record_path=record_path,
            report_path=report_path,
            ledger=experiment_ledger,
        )

    store = H.store_path(competition, processed, H.WINDOWS[args.window])
    print(f"{competition.title} — the player-prop model, scored (design section 10)")
    if not store.is_file():
        print(f"::error::{store} does not exist. Nothing was scored.", file=sys.stderr)
        return EXIT_INPUTS_ABSENT
    digest, size = store_digest(store)
    print(f"Store: {store} — {size:,} bytes, sha256 {digest}")

    # ---- receipt one -------------------------------------------------------
    try:
        attribution = PC.assert_reconciles(
            store=store,
            roster=processed / competition.output_name("player_games", ".csv"),
            expected=processed / competition.output_name("player_census", ".json"),
            chunksize=int(args.chunksize),
        )
    except PC.WagerCountMismatch as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_DOES_NOT_RECONCILE
    print(attribution.report())
    if attribution.census.source_sha256 != digest:
        print(
            "::error::the census counted a different file from the one this "
            f"run fingerprinted ({attribution.census.source_sha256} against "
            f"{digest}). Nothing was scored.",
            file=sys.stderr,
        )
        return EXIT_DOES_NOT_RECONCILE

    try:
        backtest = _backtest_module()
        props = load_offered_props(store, chunksize=int(args.chunksize))
        team_games = card_matchups.load_team_games(competition, processed)
        player_games = card_matchups.load_player_games(competition, processed)
    except NothingToMeasure as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE
    except card_matchups.InputsAbsent as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_INPUTS_ABSENT

    days = sorted(str(d) for d in props["slate_date"].dropna().unique())
    if args.days:
        whole = len(days)
        days = days[: int(args.days)]
        props = props[props["slate_date"].astype(str).isin(set(days))]
        print(
            f"!! --days {args.days}: this run prices {len(days)} of the store's "
            f"{whole} slate day(s). The store's side of the accounting identity "
            "is still the WHOLE store, so the gate refuses with the residual it "
            "finds and nothing is scored."
        )
    print(
        f"{len(props):,} prop quote(s) over {len(days):,} slate day(s), "
        f"{props['event_id'].nunique():,} event(s)."
    )

    try:
        model = PB.resolve_model(args.model)
    except PB.ModelNotWired as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NO_MODEL

    run = PC.RunDisposition(
        what=f"scripts/run_prop_grading.py ({args.model})", store_sha256=digest
    )
    rows: list[dict] = []
    tier_of_key: dict = {}
    control_refusals: Counter = Counter()
    row_refusals: Counter = Counter()
    rows_that_became_no_wager: list = []
    try:
        priced = PB.walk_forward(
            props,
            team_games,
            price_day=make_price_day(
                model,
                competition=competition,
                run=run,
                raw_dir=Path(args.raw_dir),
                rows=rows,
                tier_of_key=tier_of_key,
                control_refusals=control_refusals,
                row_refusals=row_refusals,
                rows_that_became_no_wager=rows_that_became_no_wager,
                progress=print if args.progress else None,
            ),
            frames={"player_history": player_games},
        )
    except PB.ModelNotWired as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NO_MODEL
    PB.assert_walk_forward(priced)
    print(
        f"Walk-forward: {len(priced):,} row(s) came back stamped, every one "
        "priced by a model cut to rows strictly earlier than its own night."
    )

    unparseable_rows = sum(count for _day, count in rows_that_became_no_wager)
    if unparseable_rows:
        print(
            f"!! {unparseable_rows:,} store row(s) on "
            f"{len(rows_that_became_no_wager):,} day(s) never became a wager, "
            "so this run cannot say what became of them. The identity below "
            "will refuse."
        )
        for reason, count in sorted(row_refusals.items(), key=lambda kv: -kv[1]):
            print(f"     {count:,} x {reason}")

    # ---- receipt two -------------------------------------------------------
    try:
        accounted = PC.assert_every_offered_prop_is_accounted(run)
    except PC.WagerCountMismatch as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_DOES_NOT_RECONCILE
    print()
    print(accounted.report())

    scored = pd.DataFrame(rows)
    if scored.empty:
        print(
            "::error::the run priced no prop, so there is nothing to score. An "
            "empty measurement is never printed as a reconciled one.",
            file=sys.stderr,
        )
        return EXIT_NOTHING_TO_MEASURE
    scored, grading_census = settle_rows(
        scored, processed=processed, competition=competition, backtest=backtest
    )
    print()
    for line in grading_census.lines():
        print(line)
    if control_refusals:
        print(
            f"The control declined {sum(control_refusals.values()):,} wager(s) "
            f"the model priced, in {len(control_refusals):,} distinct "
            "sentence(s). Those rows carry a MISSING control probability and "
            "are excluded from the scored population and counted there — never "
            "filled from the model's own number."
        )
        for reason, count in sorted(control_refusals.items(), key=lambda kv: -kv[1])[:5]:
            print(f"     {count:,} x {reason}")

    looks = PG.looks_from_ledger(experiment_ledger)
    if not PB.ledger_was_read(experiment_ledger):
        # An absent ledger is an UNKNOWN family, never an empty one, and
        # `looks_from_ledger` answers 1 for both. A correction of x1.00 widens
        # nothing, so a missing ledger makes every interval below look more
        # significant than the search that produced it justifies. It is said
        # loudly rather than carried silently in the record.
        print(
            f"::warning::No experiment ledger at {experiment_ledger}, so every "
            "interval below is corrected for ONE hypothesis. This lab's ledger "
            "holds 95 and every published interval is widened by x1.7689; a "
            "record written here states a correction nobody has justified. "
            "Point --output-dir at the tree that carries the ledger.",
            file=sys.stderr,
        )
    inputs = PG.PropGradingInputs(
        graded=scored,
        source=str(store),
        season_label=", ".join(
            sorted(str(s) for s in props["season"].dropna().astype(str).unique())
        ),
        snapshot_phase=args.window,
        model=str(args.model),
        control=CONTROL_DESCRIPTION,
        store={
            "path": str(store),
            "sha256": digest,
            "bytes": size,
            "rows_scanned": attribution.census.rows_scanned,
            "player_quotes": attribution.census.player_quotes,
            "events": attribution.census.events,
            "slate_dates": attribution.census.slate_dates,
        },
        offered=offered_counts(run, tier_of_key, scored),
        hypotheses=registered_hypotheses(experiment_ledger),
        accounting={
            "offered": accounted.offered,
            "accounted": accounted.accounted,
            "residual": accounted.residual,
            "buckets": {name: run.bucket(name) for name in PC.OFFERED_BUCKETS},
            "no_opinion": run.no_opinion,
            "control_declined": int(sum(control_refusals.values())),
        },
    )
    try:
        record = PG.build_record(
            inputs,
            competition=competition,
            looks=looks,
            generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
    except PG.PropGradingError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_DOES_NOT_RECONCILE

    population = record["population_census"]
    print()
    print(
        f"Scored {population['scored']:,} row(s) — one per book quoting a "
        f"wager — over "
        f"{sum(int(c['rows']) for c in record['by_tier']):,} distinct wager(s); "
        f"{population['unbenchmarked']:,} row(s) past {PG.BENCHMARKED_RUNGS} "
        "rungs are reported apart and unbenchmarked."
    )
    print(
        f"Family correction: {looks:,} cumulative hypotheses in "
        f"{experiment_ledger.name}, widening every 95% interval by "
        f"x{S.bonferroni_factor(looks):.4f}."
    )
    for cell in record["by_tier"]:
        print(
            f"  {cell['tier']:12s} {int(cell['rows']):>8,d} wagers "
            f"({int(cell['scored_rows']):>8,d} rows) — {cell['verdict']}"
        )

    if args.write_scored:
        target = Path(args.write_scored)
        target.parent.mkdir(parents=True, exist_ok=True)
        scored.to_csv(target, index=False)
        print(f"Wrote {len(scored):,} scored row(s) to {target}.")
    if not args.no_write:
        PG.write_record(record, record_path)
        PG.write_report(record, report_path, looks=looks)
        print(f"Wrote {record_path} and {report_path}.")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
