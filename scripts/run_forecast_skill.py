#!/usr/bin/env python3
"""Regress every graded outcome on market-implied against model-implied probability.

    # Over the forward evidence ledger — every opinion this lab has frozen and
    # settled. Touches no network, spends nothing:
    PYTHONPATH=src python scripts/run_forecast_skill.py

    # Over a graded-wager table produced somewhere else:
    PYTHONPATH=src python scripts/run_forecast_skill.py \
        --graded data/processed/cbb_graded_wagers.csv --pair-scope wager

    # Re-render the report from the record it was already measured into:
    PYTHONPATH=src python scripts/run_forecast_skill.py --rebuild-report-only

This is the entry point for `cbb_betting_lab.reports.forecast_skill`, which owns
every number. **This file owns the wiring.**

Cooper calls this measurement-discipline item 3 and *"the fastest honest read on
whether anything here is real"*. It is fast because it does not wait for a
return to separate itself from noise: a return is a bet-weighted,
payout-weighted, heavy-tailed function of the thing we actually want to know,
and this asks the question directly. The NHL lab ran it and got **market 0.97,
model 0.03 [-0.037, +0.102]** — the model added nothing, and its claimed edge
was anti-predictive.

## What it reads, and why the forward ledger is the default

`data/processed/cbb_forward_evidence.csv` is the one table in this repository
that already holds a **frozen opinion beside the price it was frozen at beside
the outcome it settled to**, one row per wager, appended every night and never
rewritten. That is exactly this regression's population, and it is the reason
the brief says *every week*: the ledger grows weekly and this number can be
recomputed from it for free.

`--graded` points at any other table with the same columns — a graded-wager
export from the price backtest, once one exists. The module requires
`forecast_skill.SKILL_COLUMNS` and **raises on a missing one** rather than
defaulting it: the football lab's backtest read a missing settlement column as a
zero, reported zero bets, and had that read as "the model never disagrees enough
with the market" when its price columns had never been built.

## Two populations, and which one is printed as the answer

The regression's population is **every settled wager the model had an opinion
on**. When the frame carries the backtest's boolean `selected` column, the rows
it marks — the threshold-selected bets — are measured apart and printed
**beside** the whole, labelled as the winner's-curse comparison. They are not
the skill measure: a model is selected into its bets by its own disagreement
with the price, so a regression of outcome on that disagreement over the bets
alone has the curse built into its coefficient. Until 2026-09-05 the backtest's
export was the bets and nothing else, and this script fitted them as if they
were everything.

The ledger files its day under `snapshot_date` — the day the opinion was frozen,
which for a card frozen at T-minus-tip **is** the slate day. That rename happens
here, in one place, with this sentence beside it, rather than by teaching the
report module a second column name.

## The de-vig scope, which is a real choice and is printed

`--pair-scope book` (the default) de-vigs a quote against **the same book's**
quote on the other side. That is the only pair that actually contains a hold.
`--pair-scope wager` pairs across books and is for a store already collapsed to
one row per wager at the best price; two books' best prices can sum to less than
1.0, and a "de-vig" that divides by a number below one inflates both sides above
what the price implied. The module refuses those pairs in either scope, counts
them, and the report prints the scope that was used — because the two scopes
measure different things and a report that did not say which it used would be
comparable to nothing, including to itself last week.

## Nothing to measure is an exit code, never an empty report

A missing ledger, an empty one, or one with no scorable row ends this script
with a message and a **non-zero exit**, and nothing is written. An empty report
reads as a null result and a null result is a claim.

A fit that is **not identified** gets its own exit code. The commonest cause is a
model whose probability never differs from the de-vigged price, which makes the
disagreement column constant: its coefficient is then undefined rather than
zero, and the difference is the difference between a fact about the wiring and a
finding about the model. Publishing "0.000" there would be publishing a wiring
fault as the answer to the question this lab exists to ask.

## The disagreement coefficient is printed first

Before the market coefficient, before Brier, before the buckets, before
anything. The order a reader forms a belief in is the order the numbers are
printed in, and the coefficient on the disagreement is the whole answer.

## `--rebuild-report-only`, so improving a sentence never costs a re-run

The record is written first and `forecast_skill.render` is a pure function of
it. A report that can only be produced by re-running the measurement is a report
nobody improves — they edit the generated file by hand instead, and a
hand-edited generated file survives exactly one re-run.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from cbb_betting_lab import stats as S
from cbb_betting_lab import stores
from cbb_betting_lab.competitions import (
    DEFAULT_COMPETITION_KEY,
    Competition,
    competition_for,
)
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR
from cbb_betting_lab.forward_evidence import LEDGER_COLUMNS
from cbb_betting_lab.forward_evidence import LEDGER_FILENAME as FORWARD_LEDGER_FILENAME
from cbb_betting_lab.reports import forecast_skill as FS
from cbb_betting_lab.reports import price_backtest as PB


#: Exit codes, so a workflow can tell the failures apart. A regression that
#: could not be identified is not the same event as a ledger that is not there
#: yet, and a caller that cannot distinguish them will retry the wrong one.
EXIT_OK = 0
EXIT_NOTHING_TO_MEASURE = 2
EXIT_NOT_IDENTIFIED = 3

#: The ledger's own name for the slate day. See the module docstring: the day an
#: opinion was frozen is the slate day for a card frozen before tip, and the
#: rename happens in this one place rather than by teaching the report module a
#: second column name.
LEDGER_DAY_COLUMN = "snapshot_date"


class NothingToMeasure(RuntimeError):
    """A precondition is absent, so nothing was fitted and nothing was written."""


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------


def load_graded(path: Path, *, from_ledger: bool) -> pd.DataFrame:
    """The graded wagers, or a refusal naming the file and what is missing.

    Read strictly. `stores.read_store` pads absent columns with NA when it is
    not appending, which is right for a defensive read and wrong here: a frame
    padded into this module's shape would fit a regression over a column of
    NaNs and report *not enough evidence*, which is a finding. So the header is
    checked before anything is parsed into a measurement.
    """
    target = Path(path)
    if not target.is_file():
        raise NothingToMeasure(
            f"{target} does not exist. "
            + (
                "No forward opinion has been frozen and settled yet — "
                "`scripts/run_forward_evidence.py` writes that ledger, one "
                "night at a time, and forward evidence cannot be back-dated. "
                if from_ledger
                else "Point --graded at a table of graded wagers. "
            )
            + "Nothing was fitted and no report was written, because an empty "
            "report reads as a null result and a null result is a claim."
        )
    frame = stores.read_store(target)
    if frame.empty:
        raise NothingToMeasure(
            f"{target} exists and holds no rows. A ledger that has been created "
            "and never appended to is not a model that never disagrees with the "
            "market; the two look identical in a report and only one of them is "
            "a finding."
        )
    if from_ledger:
        missing = [c for c in LEDGER_COLUMNS if c not in frame.columns]
        if missing:
            raise NothingToMeasure(
                f"{target} is missing {missing}. A file that parses into the "
                "wrong shape is not this lab's ledger, and padding the absent "
                "columns would make nonsense read as an empty record."
            )
        # One rename, here, with the reason beside it.
        frame = frame.rename(columns={LEDGER_DAY_COLUMN: "slate_date"})
    missing = [c for c in FS.SKILL_COLUMNS if c not in frame.columns]
    if missing:
        raise NothingToMeasure(
            f"{target} is missing {missing}, which "
            "`forecast_skill.SKILL_COLUMNS` requires. Nothing is defaulted: a "
            "missing column read as a zero is how a wiring fault becomes a "
            "finding, and this regression would happily fit one and print an "
            "interval."
        )
    return frame


def season_label(frame: pd.DataFrame) -> str:
    """The span of slate days this run covers, for the record's own header."""
    if frame.empty or "slate_date" not in frame.columns:
        return ""
    days = sorted({str(d) for d in frame["slate_date"].dropna() if str(d).strip()})
    if not days:
        return ""
    return days[0] if len(days) == 1 else f"{days[0]} to {days[-1]}"


# --------------------------------------------------------------------------
# Console output — the disagreement coefficient first, always
# --------------------------------------------------------------------------


def _coefficient_line(row: Mapping) -> str:
    if not row:
        return "not fitted"
    if not row.get("enough_evidence"):
        return (
            f"— ({row.get('rows', 0):,} rows across {row.get('clusters', 0):,} "
            f"{row.get('cluster_unit', 'game')}s) — {row.get('reading', '')}"
        )
    return (
        f"{row['estimate']:+.3f} [{row['low']:+.3f}, {row['high']:+.3f}], "
        f"family-corrected [{row['adjusted_low']:+.3f}, "
        f"{row['adjusted_high']:+.3f}] over {row['rows']:,} wagers across "
        f"{row['clusters']:,} {row['cluster_unit']}s — {row['reading']}"
    )


def print_disagreement_first(record: Mapping) -> None:
    """The whole answer, above everything else this run computed.

    Printed before the market coefficient, before Brier and before the buckets,
    because the order a reader forms a belief in is the order the numbers arrive
    in. Per tier first and pooled last, and the pooled line carries the reason it
    is never the headline.
    """
    print("")
    print("THE COEFFICIENT ON THE DISAGREEMENT — THE WHOLE ANSWER")
    print(
        "  outcome = a + b_market x market_implied "
        "+ b_disagreement x (model_implied - market_implied)"
    )
    print(
        "  If b_disagreement is indistinguishable from zero, the model knows "
        "nothing the price"
    )
    print(
        "  does not. Below zero it is anti-predictive: the bigger the claimed "
        "edge, the worse"
    )
    print("  the bet. The NHL lab measured 0.03 [-0.037, +0.102].")
    for measured in record.get("by_tier") or []:
        fitted = measured.get("fit") or {}
        if not fitted.get("fitted"):
            print(
                f"  {measured.get('label', '')}: not fitted — "
                f"{fitted.get('reason', FS.NOTHING_TO_MEASURE)}"
            )
            continue
        print(
            f"  {measured.get('label', '')}: "
            f"{_coefficient_line(FS.coefficient(fitted, 'disagreement'))}"
        )
    pooled = (record.get("pooled") or {}).get("fit") or {}
    if pooled.get("fitted"):
        print(
            "  pooled (never the headline — three tiers are three "
            "distributions): "
            f"{_coefficient_line(FS.coefficient(pooled, 'disagreement'))}"
        )
    print(
        f"  Population of every line above: {FS.ALL_OPINIONS_LABEL} — "
        f"{FS.ALL_OPINIONS_ROLE}."
    )


def print_populations(record: Mapping) -> None:
    """Both populations with their counts, before any number from either."""
    populations = record.get("populations") or {}
    whole = populations.get("all_opinions") or {}
    subset = populations.get("selected") or {}
    print("")
    print("TWO POPULATIONS — WHICH ONE IS THE SKILL MEASURE")
    print(
        f"  {FS.ALL_OPINIONS_LABEL}: {int(whole.get('rows', 0)):,} scorable "
        f"wagers in {int(whole.get('games', 0)):,} games — {FS.ALL_OPINIONS_ROLE}"
    )
    if subset.get("available"):
        print(
            f"  {FS.SELECTED_LABEL}: {int(subset.get('rows', 0)):,} scorable "
            f"wagers in {int(subset.get('games', 0)):,} games — {FS.SELECTED_ROLE}"
        )
    else:
        print(
            f"  {FS.SELECTED_LABEL}: not supplied (no `{FS.SELECTED_COLUMN}` "
            "column in the frame) — every number below is over every opinion"
        )


def print_selected_beside(record: Mapping) -> None:
    """The threshold-selected subset, after the whole, named as what it is."""
    selected = record.get("selected") or {}
    if not selected.get("available"):
        return
    print("")
    print(
        "THE THRESHOLD-SELECTED BETS, BESIDE IT — THE WINNER'S-CURSE "
        "COMPARISON, NOT THE SKILL MEASURE"
    )
    print(
        f"  {int(selected.get('rows', 0)):,} scorable wagers the model's own "
        "disagreement with the price selected. A coefficient here is fitted on "
        "the tail of"
    )
    print("  the model's error distribution and says what the selection cost.")
    for measured in selected.get("by_tier") or []:
        fitted = measured.get("fit") or {}
        if not fitted.get("fitted"):
            print(
                f"  {measured.get('label', '')} ({FS.SELECTED_LABEL}): not fitted — "
                f"{fitted.get('reason', FS.NOTHING_TO_MEASURE)}"
            )
            continue
        print(
            f"  {measured.get('label', '')} ({FS.SELECTED_LABEL}): "
            f"{_coefficient_line(FS.coefficient(fitted, 'disagreement'))}"
        )
    pooled = (selected.get("pooled") or {}).get("fit") or {}
    if pooled.get("fitted"):
        print(
            f"  every tier pooled ({FS.SELECTED_LABEL}; a pooled subset is never "
            "the headline either): "
            f"{_coefficient_line(FS.coefficient(pooled, 'disagreement'))}"
        )


def print_market_coefficient(record: Mapping) -> None:
    """The diagnostic, second, and never described as an edge.

    Its null is 1.0 rather than zero, and `Coefficient.verdict` raises rather
    than reading a sign into it — a market coefficient of 0.97 excludes zero on
    the positive side, and a predicate that never asked what the null was would
    announce a demonstrated edge on a number describing the market.
    """
    print("")
    print("THE MARKET COEFFICIENT — A DIAGNOSTIC ON THE DE-VIG, NOT A HEADLINE")
    print(f"  De-vig: {record.get('devig_method', '')}, pair scope "
          f"{record.get('pair_scope', '')}. Its null is 1.0, not zero.")
    hold = record.get("overround") or {}
    if hold.get("pairs"):
        print(
            f"  Hold measured over {hold['pairs']:,} two-sided pairs: median "
            f"{hold['median']:.4f}, range {hold['minimum']:.4f} to "
            f"{hold['maximum']:.4f}."
        )
    for measured in list(record.get("by_tier") or []) + [record.get("pooled") or {}]:
        fitted = measured.get("fit") or {}
        if not fitted.get("fitted"):
            continue
        row = FS.coefficient(fitted, "market_implied")
        if not row:
            continue
        print(f"  {measured.get('label', '')}: {_coefficient_line(row)}")


def print_brier(record: Mapping) -> None:
    """Model against market, side by side, with the vig-inclusive column named."""
    print("")
    print("BRIER, MODEL AGAINST MARKET")
    print(
        "  The raw market column still has the vig in it, so it over-estimates "
        "every side by"
    )
    print(
        "  construction and is being scored with a handicap. If the model loses "
        "to it anyway,"
    )
    print("  that is decisive.")
    for measured in list(record.get("by_tier") or []) + [record.get("pooled") or {}]:
        scores = measured.get("brier") or {}
        if not scores.get("scored"):
            continue
        print(
            f"  {measured.get('label', '')}: model {scores['model']:.5f} / "
            f"de-vigged market {scores['market_devigged']:.5f} / raw market "
            f"{scores['market_raw']:.5f} / base rate "
            f"{scores['base_rate_reference']:.5f}, over {scores['rows']:,} wagers"
        )
        advantage = scores.get("advantage_over_devigged") or {}
        if advantage:
            print(
                f"    advantage over the de-vigged market "
                f"{advantage['value']:+.5f} [{advantage['low']:+.5f}, "
                f"{advantage['high']:+.5f}] over {advantage['rows']:,} wagers "
                f"across {advantage['clusters']:,} {advantage['cluster_unit']}s "
                f"— {advantage['verdict']} (positive means the model is more "
                "accurate)"
            )
        if scores.get("loses_to_the_handicapped_market"):
            print(
                "    ! the model loses to the market even with the vig left in "
                "— decisive"
            )


def print_buckets(record: Mapping) -> None:
    """Anti-predictiveness as a shape rather than as a minus sign."""
    print("")
    print("CLAIMED EDGE AGAINST WHAT HAPPENED")
    print(
        "  A coefficient is one number and a reader can call it noise. A column "
        "that gets"
    )
    print("  steadily more negative as the claimed edge grows is a shape.")
    for measured in list(record.get("by_tier") or []) + [record.get("pooled") or {}]:
        label = measured.get("label", "")
        buckets = [b for b in (measured.get("buckets") or []) if b.get("enough")]
        if not buckets:
            print(
                f"  {label}: no bucket reaches the "
                f"{record.get('minimum_bucket', FS.MINIMUM_BUCKET):,} rows "
                "declared in advance, so no frequency is printed."
            )
            continue
        print(f"  {label}:")
        for bucket in buckets:
            print(
                f"    claimed {FS.bucket_label(bucket['low'], bucket['high'])}: "
                f"model said {bucket['model_implied']:.1%}, price said "
                f"{bucket['market_implied']:.1%}, actually won "
                f"{bucket['realised']:.1%} "
                f"[{bucket['wilson_low']:.1%}, {bucket['wilson_high']:.1%}] "
                f"over {bucket['rows']:,} wagers in {bucket['games']:,} games "
                f"({bucket['gap_to_model'] * 100:+.1f} pp against the model)"
            )
        shape = measured.get("anti_predictive") or {}
        if shape.get("measurable") and shape.get("worse_at_the_top"):
            print(
                f"    ! the shortfall widens by "
                f"{shape['shortfall_widens_by'] * 100:.1f} pp from the lowest "
                "claimed-edge bucket to the highest — the biggest claimed edges "
                "do worst, and raising the threshold is the wrong response."
            )


def print_census(record: Mapping) -> None:
    """`supplied = de-vigged + excluded`, reconciled, and the same for scoring."""
    devig = record.get("devig_census") or {}
    population = record.get("population_census") or {}
    print("")
    print("What could be measured, and what could not:")
    print(f"  wagers supplied                {int(devig.get('supplied', 0)):,}")
    print(f"  de-vigged                      {int(devig.get('devigged', 0)):,}")
    print(f"  excluded from the de-vig       {int(devig.get('excluded', 0)):,}")
    for key, label in (
        ("unknown_selection", "selection this lab does not pair"),
        ("unreadable_price", "price could not be read"),
        ("no_complement", "other side of the wager absent"),
        ("not_two_sided", "pair is not two opposite sides"),
        ("overround_not_above_one", "two sides sum to 1.0 or less"),
    ):
        if int(devig.get(key, 0)):
            print(f"    {int(devig[key]):,} x {label}")
    print(
        f"  reconciles                     "
        f"{'yes' if devig.get('reconciles') else 'NO'}"
    )
    print(f"  scorable (won or lost)         {int(population.get('scored', 0)):,}")
    for key, label in (
        ("no_model_probability", "no model probability"),
        ("push", "pushed — a push is not half a win"),
        ("void", "void"),
        ("unsettleable", "unsettleable — never a loss, never a pass"),
        ("other_outcome", "an outcome this report does not score"),
    ):
        if int(population.get(key, 0)):
            print(f"    {int(population[key]):,} x {label}")


# --------------------------------------------------------------------------
# The two modes
# --------------------------------------------------------------------------


def rebuild_report_only(*, record_path: Path, report_path: Path) -> int:
    """Re-render the markdown from the record. Fits nothing, spends nothing."""
    if not record_path.is_file():
        print(
            f"::error::{record_path} does not exist, so there is no record to "
            "re-render. Run this script without --rebuild-report-only first; "
            "the report is a pure function of the record and cannot be produced "
            "without one.",
            file=sys.stderr,
        )
        return EXIT_NOTHING_TO_MEASURE
    try:
        record = FS.read_record(record_path)
    except FS.ForecastSkillError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE
    FS.write_report(record, report_path)
    print(f"Wrote {report_path} from {record_path}.")
    print(
        "The run being rendered scored "
        f"{int((record.get('population_census') or {}).get('scored', 0)):,} "
        "graded wagers, generated "
        f"{record.get('generated_at') or 'at an unrecorded time'}."
    )
    print("Nothing was re-fitted, no table was read and no credit was spent.")
    return EXIT_OK


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    parser.add_argument(
        "--graded",
        default="",
        help=(
            "A table of graded wagers carrying `forecast_skill.SKILL_COLUMNS`. "
            f"Defaults to the forward evidence ledger, {FORWARD_LEDGER_FILENAME}, "
            "which is the one table holding a frozen opinion beside the price it "
            "was frozen at beside the outcome it settled to."
        ),
    )
    parser.add_argument(
        "--pair-scope",
        default=FS.PAIR_SCOPES[0],
        choices=list(FS.PAIR_SCOPES),
        help=(
            "How the de-vig pairs a quote with the other side. `book` uses the "
            "same book's own quote, which is the only pair that contains a "
            "hold. `wager` pairs across books and understates the hold — use it "
            "only for a store already collapsed to one row per wager at the "
            "best price. The scope used is recorded and printed."
        ),
    )
    parser.add_argument(
        "--edge-threshold",
        type=float,
        default=PB.BET_EDGE_THRESHOLD,
        help=(
            "Recorded so the report can name it. This regression runs over "
            "every graded wager and never applies it: conditioning on the "
            "threshold would condition on the variable whose usefulness is the "
            "question."
        ),
    )
    parser.add_argument(
        "--rebuild-report-only",
        action="store_true",
        help=(
            "Re-render the markdown from the existing run record. Fits nothing, "
            "reads no table, spends nothing."
        ),
    )
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    parser.add_argument(
        "--ledger",
        default="",
        help=(
            "The experiment ledger the family-wise correction is read from. "
            "Defaults to the one beside the outputs. Always the CUMULATIVE "
            "count, never the day's."
        ),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    competition: Competition = competition_for(args.competition)
    output_dir = Path(args.output_dir)
    record_path = FS.record_path(competition, output_dir)
    report_path = FS.report_path(competition, output_dir)

    if args.rebuild_report_only:
        return rebuild_report_only(record_path=record_path, report_path=report_path)

    from_ledger = not str(args.graded).strip()
    graded_path = (
        Path(args.processed_dir) / FORWARD_LEDGER_FILENAME
        if from_ledger
        else Path(args.graded)
    )
    print(f"{competition.title} — forecast skill")
    print(f"Reading {graded_path}")

    try:
        graded = load_graded(graded_path, from_ledger=from_ledger)
    except NothingToMeasure as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE

    experiment_ledger = (
        Path(args.ledger) if args.ledger else FS.ledger_path(output_dir)
    )
    looks = FS.looks_from_ledger(experiment_ledger)
    if not experiment_ledger.is_file():
        print(
            f"::warning::{experiment_ledger} does not exist, so the family-wise "
            "correction is applied across one look. That is a lab that has "
            "tested nothing, which is not what this one is."
        )

    try:
        record = FS.build_record(
            FS.SkillInputs(
                graded=graded,
                source=str(graded_path),
                season_label=season_label(graded),
                pair_scope=args.pair_scope,
                edge_threshold=float(args.edge_threshold),
            ),
            competition=competition,
            looks=looks,
            generated_at=datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat()
            .replace("+00:00", "Z"),
        )
    except FS.ForecastSkillError as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_NOTHING_TO_MEASURE

    print_census(record)
    print_populations(record)

    scored = int((record.get("population_census") or {}).get("scored", 0))
    if not scored:
        print(
            "::error::No wager could be scored. Every supplied row either "
            "carries no de-vigged price, no model probability, or no won/lost "
            "outcome — the census above says which. That is a wiring fact, not "
            "a null result, and nothing was written: an empty report reads as a "
            "null result and a null result is a claim.",
            file=sys.stderr,
        )
        return EXIT_NOTHING_TO_MEASURE

    pooled_fit = (record.get("pooled") or {}).get("fit") or {}
    if not pooled_fit.get("fitted"):
        print(
            "::error::The regression is not identified: "
            f"{pooled_fit.get('reason', FS.NOTHING_TO_MEASURE)} A coefficient "
            "with no variation to explain is undefined rather than zero, and "
            "publishing 0.000 there would publish a wiring fault as the answer "
            "to the question this lab exists to ask. Nothing was written.",
            file=sys.stderr,
        )
        return EXIT_NOT_IDENTIFIED

    FS.write_record(record, record_path)
    FS.write_report(record, report_path)

    print("")
    print(
        f"Family correction: {looks:,} cumulative hypotheses in "
        f"{experiment_ledger.name}, widening every 95% interval by "
        f"x{record['correction_factor']:.2f}. The ledger's cumulative count, "
        "never the day's."
    )
    print(
        f"Below {int(record['minimum_rows']):,} scored wagers or "
        f"{int(record['minimum_clusters']):,} clusters there is no number, only "
        f"'{S.NO_DEMONSTRATED_EDGE}' or 'not enough evidence'. Both floors were "
        "declared in advance."
    )

    print_disagreement_first(record)
    print_market_coefficient(record)
    print_brier(record)
    print_buckets(record)
    print_selected_beside(record)

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
