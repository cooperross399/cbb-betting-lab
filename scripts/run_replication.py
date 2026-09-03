#!/usr/bin/env python3
"""Re-score the backtest's own rule on a season it was never selected on.

    # Re-render the report from the record it was already measured into.
    # Touches no network, re-scores nothing, spends nothing:
    PYTHONPATH=src python scripts/run_replication.py --rebuild-report-only

    # The declared split: discovery 2021-2023, held out 2024.
    PYTHONPATH=src python scripts/run_replication.py \
        --model cbb_betting_lab.models.ratings:matchups_for

    # A different held-out season, which the record will say was not the
    # declared one:
    PYTHONPATH=src python scripts/run_replication.py --seasons 2023

`price_backtest.py` ends by naming this script's module and stating its whole
specification in one sentence: *"It cannot replicate itself. A held-out season
is `replication.py`'s job, and a window that merely fails to contradict is not
confirmation."*

`cbb_betting_lab.reports.replication` owns every judgement. **This file owns the
wiring**, and there is exactly one thing the wiring has to get right:

## The held-out season must be scored by the SAME code as the discovery season

So this script does not have a scorer. It imports `scripts/run_price_backtest.py`
and calls that file's `load_store`, `load_tables`, `resolve_model`,
`make_price_day`, `grade`, `fixture_index` and `player_index`, then hands the
result to `price_backtest`'s own `walk_forward`, `add_edge` and `bets_from`. A
replication that re-implements the scorer is not a test of the rule; it is a
comparison of two scorers, and it disagrees with the discovery run in exactly
the cells where the two implementations diverged — which is to say, in the
interesting ones, for the wrong reason.

Importing a sibling script by path is unusual and is the smaller cost. The
alternative is a second copy of the grading wiring, and the three sibling labs
between them lost measurements to a store deduplicated on its timestamps, a
settlement column that had never been built reading as a zero, and a
distribution loaded once outside the season loop. A second copy of that wiring
would be a fourth opportunity.

## Five refusals, each with its own exit code

1. **No discovery record.** Nothing has been bought, nothing has been scored,
   and there is no rule to replicate. Exit 2, nothing written.
2. **A held-out season inside the discovery window.** The loudest one, and the
   only failure here that would produce a clean, confident, entirely worthless
   report: re-scoring a rule on a season it was chosen on reproduces the
   selection rather than the effect, and it does so with a tighter interval
   every time the sample grows. Exit 5, nothing written.
3. **No model.** There is no fallback pricer, for the same reason
   `run_price_backtest.py` has none: a replication that silently prices with
   something other than the model the discovery run used has measured a
   different rule and printed intervals while doing it. Exit 3.
4. **No price for the held-out season.** The purchase may still be running.
   Exit 2, nothing written — an empty report reads as a null result and a null
   result is a claim.
5. **The model had an opinion on nothing.** A wiring fault wearing a finding's
   clothes. Exit 4.

## The holdout is a second look, and it is counted before it is taken

`experiment_ledger.Hypothesis.key()` puts the **stage** in the dedupe key
precisely so that *"putting a discovery finding to the holdout is a second look,
and the whole design collapses if it is not counted as one."* So this script
appends one `stage="holdout"` hypothesis per (market, tier) cell it is about to
test — with `predicted_direction` taken from the **sign of the discovery
result**, which is a genuinely falsifiable prediction and the only one a
replication makes — and only then reads the ledger's cumulative count. The
correction applied to the held-out intervals therefore already includes this
run's own looks.

They are recorded **before** the scoring, not after, which is the only ordering
under which a pre-registered direction means anything. The ledger has no update
API by design, so the realised direction is written into this run's own record
rather than back into the ledger, and the report prints both.

## `--rebuild-report-only`, so improving a sentence never costs a re-run

The retention probe's rule. This run walks every slate day of a season and
re-grades every wager in it; a report that can only be produced by re-running
the measurement is a report nobody improves, and a hand-edited generated file
survives exactly one re-run.
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from cbb_betting_lab import experiment_ledger as E
from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import (
    DEFAULT_COMPETITION_KEY,
    Competition,
    competition_for,
)
from cbb_betting_lab.config import MANUAL_DIR, OUTPUTS_DIR, PROCESSED_DIR
from cbb_betting_lab.markets import MARKETS_BY_KEY, PLAYER
from cbb_betting_lab.promotion import PromotionError, criteria_path, load_criteria
from cbb_betting_lab.providers import historical as H
from cbb_betting_lab.reports import price_backtest as PB
from cbb_betting_lab.reports import replication as R
from cbb_betting_lab.season import clean_text


#: The sibling script whose wiring this one reuses rather than copies. Named
#: relative to this file so a checkout anywhere resolves it, and imported under
#: a module name that could not collide with anything on `sys.path`.
BACKTEST_SCRIPT = "run_price_backtest.py"
BACKTEST_MODULE = "cbb_run_price_backtest"

#: The search name every hypothesis this run records goes under, so the ledger
#: can be read for "how many holdout looks has this lab taken" without parsing
#: hypothesis text.
SEARCH = "replication"

#: Exit codes, so a workflow can tell the refusals apart.
EXIT_OK = 0
EXIT_NOTHING_TO_MEASURE = 2
EXIT_NO_MODEL = 3
EXIT_NO_OPINION = 4
EXIT_NOT_HELD_OUT = 5


def backtest_wiring():
    """`scripts/run_price_backtest.py`, imported as a module.

    It has an `if __name__ == "__main__"` guard, so importing it runs no
    measurement and opens no file. Cached in `sys.modules` under a name of this
    file's choosing, because two executions of the same script module would
    define two `NothingToMeasure` classes and an `except` clause would then
    catch one of them.
    """
    existing = sys.modules.get(BACKTEST_MODULE)
    if existing is not None:
        return existing
    path = Path(__file__).resolve().with_name(BACKTEST_SCRIPT)
    if not path.is_file():
        raise ImportError(
            f"{path} does not exist, and this script deliberately has no scorer "
            "of its own: a replication that re-implements the scorer is not a "
            "test of the rule, it is a comparison of two scorers."
        )
    spec = importlib.util.spec_from_file_location(BACKTEST_MODULE, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"{path} could not be loaded as a module.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[BACKTEST_MODULE] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# Scoring one held-out season, through the discovery run's own wiring
# --------------------------------------------------------------------------


def score_season(
    backtest,
    *,
    season: int,
    competition: Competition,
    processed_dir: Path,
    window,
    model,
    threshold: float,
) -> tuple[pd.DataFrame, int, str]:
    """One held-out season's graded bets, its opinion count, and a log line.

    The opinion count is returned rather than derived later because zero bets
    and zero opinions are different things and only one of them is a finding.
    The football lab's props backtest reported zero bets and had that read as
    "the model never disagrees enough with the market" when in truth its price
    columns had never been built.

    Every step is the discovery run's own: `one_bet_per_wager` collapses the
    store to one bet per wager at the best price, `walk_forward` hands the
    pricer only games strictly earlier than the day it is pricing,
    `assert_walk_forward` checks the stamp rather than the code path, and
    `bets_from` applies **the discovery run's** edge threshold rather than a new
    one. A replication at a different threshold is a replication of a different
    rule.
    """
    store = backtest.load_store(competition, Path(processed_dir), window)
    season_rows = store[pd.to_numeric(store["season"], errors="coerce") == int(season)]
    season_rows = season_rows.reset_index(drop=True)
    if season_rows.empty:
        raise backtest.NothingToMeasure(
            f"The price store holds no row for season {season}, so the held-out "
            "season cannot be scored. A season with no bought price is not a "
            "season that failed to replicate — those are different claims and "
            "this run refuses to write the second one. Nothing was written."
        )
    quotes = len(season_rows)
    wagers = PB.one_bet_per_wager(season_rows)

    tables = backtest.load_tables(
        Path(processed_dir),
        competition,
        players=any(
            (MARKETS_BY_KEY.get(m) is not None and MARKETS_BY_KEY[m].family == PLAYER)
            for m in {clean_text(m) for m in wagers["market"].dropna().unique()}
        ),
    )
    team_games = tables["team_games"]

    accounting = backtest.OpinionAccounting(offered=len(wagers))
    priced = PB.walk_forward(
        wagers,
        team_games,
        price_day=backtest.make_price_day(
            model, competition=competition, accounting=accounting
        ),
    )
    PB.assert_walk_forward(priced)
    priced = PB.add_edge(priced)
    opinions = int(
        pd.to_numeric(priced["model_probability"], errors="coerce").notna().sum()
    )

    # `_as_int` is the discovery run's own game-id coercion, called rather than
    # re-implemented. A fixture lookup that resolved ids even slightly
    # differently between the two runs would drop a different set of games from
    # each, and the difference would present as a failure to replicate.
    game_ids = {
        g
        for g in (
            backtest._as_int(v)
            for v in priced.get("game_id", pd.Series(dtype="object"))
        )
        if g is not None
    }
    census = backtest.GradingCensus()
    universe = backtest.grade(
        priced,
        fixtures=backtest.fixture_index(team_games, tables["game_segments"], game_ids),
        players=backtest.player_index(tables[backtest.PLAYER_TABLE], game_ids),
        census=census,
    )
    bets = PB.bets_from(universe, threshold=float(threshold))
    line = (
        f"  season {season}: {quotes:,} quote(s) collapse to {len(wagers):,} "
        f"wager(s) at the best price; the model has an opinion on "
        f"{opinions:,}; {len(bets):,} clear the {threshold:.0%} threshold the "
        f"discovery run declared; {len(PB.settled(bets)):,} of those are graded."
    )
    return bets, opinions, line


# --------------------------------------------------------------------------
# The ledger: the holdout is a second look, counted before it is taken
# --------------------------------------------------------------------------


def record_holdout_looks(
    claims,
    *,
    seasons,
    ledger_path: Path,
    tested_on: str,
) -> tuple[int, int]:
    """Append one holdout hypothesis per cell about to be tested. Returns (new, total).

    `predicted_direction` is the **sign of the discovery result**, which is the
    one prediction a replication actually makes and is falsifiable in exactly
    the way `experiment_ledger.DirectionRequired` insists on: a cell that comes
    back the other way is a reversal, and a reversal is a result.

    Cells the discovery window demonstrated nothing in are skipped. There is no
    hypothesis to put to the holdout there, and recording one would inflate the
    correction without buying any protection — the same line
    `scripts/record_experiments.py` draws around retention probing and
    settlement validation.
    """
    ledger = E.load(Path(ledger_path))
    hypotheses = [
        E.Hypothesis(
            search=SEARCH,
            name=(
                f"{claim['market']} / {claim['tier']}: the discovery result "
                "holds on a season it was not selected on"
            ),
            tested_on=str(tested_on),
            seasons=tuple(int(s) for s in seasons),
            outcome="pending",
            predicted_direction="higher" if claim["sign"] > 0 else "lower",
            stage="holdout",
        )
        for claim in claims
        if claim.get("claims") and claim.get("sign")
    ]
    added = ledger.record(*hypotheses)
    if added:
        E.save(ledger, Path(ledger_path))
    return added, len(hypotheses)


# --------------------------------------------------------------------------
# Console output
# --------------------------------------------------------------------------


def print_verdicts(record: Mapping) -> None:
    """Per market and per tier. Never a pooled Division I headline."""
    minimum = int((record.get("criteria") or {}).get("minimum_bets", 0))
    counts = record.get("counts") or {}
    print("")
    print("REPLICATION, PER MARKET AND PER CONFERENCE TIER")
    print(
        "  A cell replicates only on the SAME SIGN and its OWN interval "
        "excluding zero."
    )
    print(
        "  A window that merely fails to contradict is not confirmation, and a "
        "held-out"
    )
    print(f"  interval that includes zero is '{S.NO_DEMONSTRATED_EDGE}'.")
    rows = record.get("markets") or []
    if not rows:
        print(f"  {R.NOTHING_TO_MEASURE.capitalize()}: the discovery record measured no cell.")
        return
    for row in R.ordered_cells(rows):
        cell = row.get("holdout") or {}
        roi, interval, corrected = R.roi_cells(cell, criteria_minimum_bets=minimum)
        print(
            f"  {row['tier']} / {row['market']}: {row['state'].upper()} — "
            f"{int(row.get('holdout_bets', 0)):,} held-out bets / "
            f"{int(row.get('holdout_clusters', 0)):,} "
            f"{cell.get('cluster_unit', 'game')}s  {roi}  [{interval}]  "
            f"corrected [{corrected}]"
        )
    print("")
    print(
        f"  {counts.get(R.REPLICATED, 0)} replicated / "
        f"{counts.get(R.DID_NOT_REPLICATE, 0)} did not replicate / "
        f"{counts.get(R.REVERSED, 0)} reversed / "
        f"{counts.get(R.NOT_ENOUGH_EVIDENCE, 0)} not enough evidence / "
        f"{counts.get(R.NOTHING_TO_REPLICATE, 0)} nothing to replicate / "
        f"{counts.get(R.UNTESTABLE, 0)} untestable."
    )
    found = [r for r in rows if r.get("found_on_the_holdout")]
    for row in found:
        print(
            f"  ! {row['tier']} / {row['market']} demonstrates something on the "
            "holdout that the discovery window did not. That is a NEW "
            "DISCOVERY made on the only clean season this lab had, not a "
            "replication."
        )
    suspect = [
        r
        for r in rows
        if r.get("settlement_suspect") and r.get("state") == R.REPLICATED
    ]
    for row in suspect:
        print(
            f"  ! {row['tier']} / {row['market']} replicated and settles on a "
            "rule this lab cannot verify. A constant settlement offset "
            "replicates by construction — treat it as a settlement artefact "
            "first and a finding second."
        )
    print("")
    print("PER TIER, ACROSS MARKETS — and pooled, which is never the headline.")
    for row in record.get("by_tier") or []:
        print(
            f"  {row.get('name', row.get('tier', ''))}: "
            f"{int(row.get('bets', 0)):,} bets / {int(row.get('clusters', 0)):,} "
            f"{row.get('cluster_unit', 'game')}s — "
            f"{R.verdict_text(row, minimum_bets=minimum)}"
        )


# --------------------------------------------------------------------------
# The two modes
# --------------------------------------------------------------------------


def rebuild_report_only(*, record_path: Path, report_path: Path) -> int:
    """Re-render the markdown from the record. Scores nothing, spends nothing."""
    if not record_path.is_file():
        print(
            f"::error::{record_path} does not exist, so there is no record to "
            "re-render. Run this script without --rebuild-report-only first; "
            "the report is a pure function of the record and cannot be "
            "produced without one.",
            file=sys.stderr,
        )
        return EXIT_NOTHING_TO_MEASURE
    try:
        record = R.read_record(record_path)
    except R.ReplicationError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE
    R.write_report(record, report_path)
    print(f"Wrote {report_path} from {record_path}.")
    print(
        "The run being rendered held out season(s) "
        f"{record.get('held_out_seasons')} against a discovery window of "
        f"{record.get('discovery_seasons')}, generated "
        f"{record.get('generated_at') or 'at an unrecorded time'}."
    )
    print("Nothing was re-scored, no table was read and no credit was spent.")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    parser.add_argument(
        "--seasons",
        default=",".join(str(s) for s in R.DECLARED_HELD_OUT_SEASONS),
        help=(
            "The season(s) to hold out, labelled by the year each season ENDS. "
            "Defaults to the split declared in `replication.py` before any "
            "price was bought. A season inside the discovery record's own "
            "window is refused: re-scoring a rule on the data it was chosen on "
            "reproduces the selection, not the effect."
        ),
    )
    parser.add_argument(
        "--model",
        default="",
        help=(
            "`module:attribute` returning one matchup per event for a slate "
            "day. Defaults to `run_price_backtest.DEFAULT_MODEL`, which is the "
            "model the discovery run used unless it was told otherwise — the "
            "backtest record does not carry the model that priced it, so this "
            "agreement is asserted by the operator and said so in the report."
        ),
    )
    parser.add_argument(
        "--window",
        default="",
        help=(
            "Which snapshot store to score. Defaults to the discovery record's "
            "own `snapshot_phase`: a replication on a different window is a "
            "replication of a different rule."
        ),
    )
    parser.add_argument(
        "--rebuild-report-only",
        action="store_true",
        help=(
            "Re-render the markdown from the existing run record. Scores "
            "nothing, reads no table, spends nothing."
        ),
    )
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument(
        "--manual-dir",
        default=str(MANUAL_DIR),
        help=(
            "Where `promotion_criteria.json` is read from. The criteria are "
            "read and never defaulted — a margin that falls back to whatever "
            "the code says today is not a pre-registered margin."
        ),
    )
    parser.add_argument(
        "--ledger",
        default="",
        help=(
            "The experiment ledger the family-wise correction is read from, "
            "and the one this run's holdout looks are appended to. Always the "
            "CUMULATIVE count, never the day's."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    competition = competition_for(args.competition)
    output_dir = Path(args.output_dir)
    record_path = R.record_path(competition, output_dir)
    report_path = R.report_path(competition, output_dir)

    if args.rebuild_report_only:
        return rebuild_report_only(record_path=record_path, report_path=report_path)

    print(f"{competition.title} — replication on a held-out season")

    # ---- the criteria, read and never defaulted ----------------------------
    try:
        criteria = load_criteria(competition, manual_dir=args.manual_dir)
        R.assert_criteria_agree(criteria)
    except (PromotionError, R.ReplicationError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE

    # ---- the discovery record ----------------------------------------------
    discovery_path = PB.record_path(competition, output_dir)
    if not discovery_path.is_file():
        print(
            f"::error::{discovery_path} does not exist, so there is no rule "
            "to replicate. Run `scripts/run_price_backtest.py` first. "
            "**Nothing here says a result failed to replicate**: a missing "
            "discovery record is an absent measurement, and an absent "
            "measurement reported as a null is the one thing this repository "
            "is arranged against.",
            file=sys.stderr,
        )
        return EXIT_NOTHING_TO_MEASURE
    try:
        discovery = PB.read_record(discovery_path)
    except PB.BacktestError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE

    # ---- the held-out season, refused if it is not held out ----------------
    wanted = [int(s) for s in str(args.seasons).split(",") if s.strip().isdigit()]
    try:
        discovery_seasons = R.seasons_from_label(str(discovery.get("season_label", "")))
        R.assert_held_out(seasons=wanted, discovery_seasons=discovery_seasons)
    except R.NotHeldOut as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOT_HELD_OUT
    except R.ReplicationError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE

    print(
        f"Discovery: {discovery.get('bets_graded', 0):,} graded bets on season(s) "
        f"{list(discovery_seasons)}. Held out: {wanted}."
    )
    if set(wanted) != set(R.DECLARED_HELD_OUT_SEASONS):
        print(
            f"::warning::{wanted} is not the split declared {R.DECLARED_ON} "
            f"(discovery {list(R.DECLARED_DISCOVERY_SEASONS)}, holdout "
            f"{list(R.DECLARED_HELD_OUT_SEASONS)}). A holdout chosen after the "
            "discovery numbers were seen is a second look at the data rather "
            "than a pre-registered test, and the record says so."
        )

    # ---- the same wiring the discovery run used ----------------------------
    try:
        backtest = backtest_wiring()
    except ImportError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE

    window_name = str(args.window or discovery.get("snapshot_phase") or H.CARD_WINDOW.name)
    if window_name not in H.WINDOWS:
        print(
            f"::error::Unknown snapshot window {window_name!r}. Known: "
            f"{sorted(H.WINDOWS)}.",
            file=sys.stderr,
        )
        return EXIT_NOTHING_TO_MEASURE
    window = H.WINDOWS[window_name]

    model_spec = str(args.model or backtest.DEFAULT_MODEL)
    try:
        model = backtest.resolve_model(model_spec)
    except backtest.ModelNotWired as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NO_MODEL

    threshold = float(discovery.get("edge_threshold", PB.BET_EDGE_THRESHOLD))
    print(
        f"Window {window.name}, model {model_spec}, edge threshold "
        f"{threshold:.0%} — all three taken from the discovery run rather than "
        "re-chosen, except the model, which the backtest record does not carry."
    )

    # ---- the holdout is a second look, counted before it is taken ----------
    ledger_path = Path(args.ledger) if args.ledger else PB.ledger_path(output_dir)
    # Which cells carry a claim is read at the count BEFORE this run appends to
    # it, because the count after depends on how many claims there are and a
    # value cannot be its own input. The count before is the smaller of the two,
    # so this errs towards calling a cell a claim and therefore towards
    # recording a look — which widens the correction rather than narrowing it,
    # and is the only direction an approximation here may fail in. The record
    # itself re-reads every claim at the final cumulative count.
    looks_before = PB.looks_from_ledger(ledger_path)
    claims = R.discovery_claims(discovery, looks=looks_before)
    added, holdout_looks = record_holdout_looks(
        claims,
        seasons=wanted,
        ledger_path=ledger_path,
        tested_on=datetime.now(timezone.utc).date().isoformat(),
    )
    looks = PB.looks_from_ledger(ledger_path)
    if not ledger_path.is_file():
        print(
            f"::warning::{ledger_path} does not exist, so the family-wise "
            "correction is applied across one look. That is a lab that has "
            "tested nothing, which is not what this one is."
        )
    print(
        f"Experiment ledger: {holdout_looks:,} holdout look(s) for this run "
        f"({added:,} newly recorded), cumulative count {looks_before:,} before "
        f"and {looks:,} after, widening every 95% interval by "
        f"x{S.bonferroni_factor(looks):.2f}. Putting a discovery finding to the "
        "holdout is a second look and is counted as one — before it is taken, "
        "so the correction on these intervals already includes them."
    )

    # ---- score each held-out season, apart ---------------------------------
    scored: dict[int, pd.DataFrame] = {}
    lines: list[str] = []
    opinions = 0
    for season in wanted:
        try:
            bets, season_opinions, line = score_season(
                backtest,
                season=season,
                competition=competition,
                processed_dir=Path(args.processed_dir),
                window=window,
                model=model,
                threshold=threshold,
            )
        except backtest.NothingToMeasure as exc:
            print(f"::error::{exc}", file=sys.stderr)
            return EXIT_NOTHING_TO_MEASURE
        scored[season] = bets
        opinions += int(season_opinions)
        lines.append(line)
    print("Held-out scoring:")
    for line in lines:
        print(line)

    if opinions == 0:
        # Zero *bets* with opinions behind them is a finding: the model looked
        # at the held-out season and disagreed with nobody enough to bet. Zero
        # *opinions* is a wiring fault wearing a finding's clothes, and it is
        # the one the football lab published.
        print(
            "::error::The model was asked about every wager in the held-out "
            "season(s) and had an opinion on none of them. Zero opinions reads "
            "as 'the model never disagrees enough with the market', which is a "
            "finding — and in the football lab it was a wiring fault, its price "
            "columns never built. This exits rather than publishing that "
            "ambiguity as a replication. Nothing was written.",
            file=sys.stderr,
        )
        return EXIT_NO_OPINION

    # ---- the record --------------------------------------------------------
    try:
        record = R.build_record(
            discovery=discovery,
            holdout_bets=scored,
            criteria=criteria,
            looks=looks,
            competition=competition,
            model=model_spec,
            generated_at=datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
            criteria_source=str(criteria_path(competition, args.manual_dir)),
            ledger_source=str(ledger_path),
            ledger_found=ledger_path.is_file(),
            holdout_looks_recorded=holdout_looks,
        )
    except R.NotHeldOut as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOT_HELD_OUT
    except R.ReplicationError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE

    R.write_record(record, record_path)
    R.write_report(record, report_path)

    print_verdicts(record)
    print("")
    print(f"Wrote {record_path}")
    print(f"Wrote {report_path}")
    print(
        "Re-render the report from that record for free with "
        "--rebuild-report-only; improving a sentence must never cost a re-run."
    )
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
