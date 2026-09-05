#!/usr/bin/env python3
"""Append this build's hypotheses to the append-only experiment ledger.

    PYTHONPATH=src python scripts/record_experiments.py

**Every hypothesis this lab has ever put to the data**, so that the correction
applied to any new claim is computed over the cumulative count rather than over
today's. `experiment_ledger.py`'s docstring is the argument; the short form is
that a search running every week is not twelve tests, it is twelve tests a week
forever, and at a nominal 5% threshold roughly one look in twenty clears by
chance.

## What belongs here, and what does not

A hypothesis is something that **could have produced a finding** — a claim
about edge, about a subgroup, about an adjustment. Every one of them spends a
degree of freedom whether it succeeded or not, and the ones that failed are
precisely what make a survivor unlikely to be chance.

Three kinds of work in this build are deliberately **not** recorded, because
recording them would inflate the correction without buying any protection:

- **Retention probing.** "Does the archive hold `player_blocks`?" is a question
  about the provider's storage, not about this lab's returns. It cannot produce
  a false positive about an edge.
- **Settlement validation.** "Does `h1 + h2` equal the final score?" has a right
  answer that is knowable independently, and it was checked against 45,383
  games rather than estimated.
- **Defect reproduction.** Reproducing a bug before fixing it is not a test of
  a hypothesis about the world.

The line is whether the answer could have been *flattering*. A retention probe
cannot flatter anybody.

## Predicted direction is required, and that is a change from the sibling

The football lab recorded its own defect here: *"three of the twelve hypotheses
were written with no predicted direction, so they could not be falsified by
direction and three slots were spent on cuts that could only ever be
exploratory."* Four of its mechanisms then reversed outright — and knowing they
reversed was worth more than the null result, which is only sayable because a
direction had been written down first. So `Hypothesis` raises without one.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from cbb_betting_lab import experiment_ledger as E
from cbb_betting_lab.config import OUTPUTS_DIR

#: The seasons the priced population covers. Featured markets reach back to
#: 2020-11-16, so six; the full catalogue only to 2023-05-03, so three.
FEATURED = (2021, 2022, 2023, 2024, 2025, 2026)
FULL = (2024, 2025, 2026)


#: Everything this build has put, or is about to put, to the priced data.
#:
#: Recorded BEFORE the backtest runs, not after, which is the only ordering
#: under which a pre-registered direction means anything. `outcome` is
#: `pending` until the measurement writes back.
HYPOTHESES: tuple[E.Hypothesis, ...] = (
    # --- The core question, per market. One per market is the real family
    # size, and it is large on purpose: the alternative is to test thirty
    # things and correct as though we had tested one.
    #
    # "higher" throughout means: ROI at the shipped bar is higher than zero.
    *(
        E.Hypothesis(
            search="core_team_markets",
            name=f"{market}: ROI at the card-time price is above zero",
            tested_on="2026-09-01",
            seasons=FEATURED,
            outcome="pending",
            predicted_direction="higher",
            stage="discovery",
        )
        for market in ("moneyline", "spread", "total_points", "team_total")
    ),
    # --- The thesis, and the one place this build predicts a LOWER number on
    # purpose. Cooper's case for a fourth lab is that efficiency is not
    # uniform across the board: "360 teams on a Tuesday night in January is
    # the opposite [of a tightly-priced league]". So low-major is predicted
    # above zero and high-major BELOW it, and writing the second one down is
    # what makes the pair falsifiable rather than a slice to be read after.
    E.Hypothesis(
        search="conference_tier",
        name="low_major: team-market ROI is above zero",
        tested_on="2026-09-01", seasons=FEATURED, outcome="pending",
        predicted_direction="higher", stage="discovery",
    ),
    E.Hypothesis(
        search="conference_tier",
        name="mid_major: team-market ROI is above zero",
        tested_on="2026-09-01", seasons=FEATURED, outcome="pending",
        predicted_direction="higher", stage="discovery",
    ),
    E.Hypothesis(
        search="conference_tier",
        name="high_major: team-market ROI is above zero",
        tested_on="2026-09-01", seasons=FEATURED, outcome="pending",
        predicted_direction="lower", stage="discovery",
    ),
    E.Hypothesis(
        search="conference_tier",
        name="low_major ROI exceeds high_major ROI",
        tested_on="2026-09-01", seasons=FEATURED, outcome="pending",
        predicted_direction="higher", stage="discovery",
    ),
    # --- Ladders and halves.
    *(
        E.Hypothesis(
            search="ladders_and_halves",
            name=f"{market}: ROI at the card-time price is above zero",
            tested_on="2026-09-01",
            seasons=FULL,
            outcome="pending",
            predicted_direction="higher",
            stage="discovery",
        )
        for market in (
            "alternate_spread", "alternate_total_points", "alternate_team_total",
            "spread_h1", "spread_h2", "total_points_h1", "total_points_h2",
            "moneyline_h1", "moneyline_h2", "team_total_h1", "team_total_h2",
        )
    ),
    # --- The modelling choices the brief names. Each ships only by winning the
    # price backtest, so each is phrased as a comparison of ROI against the
    # variant it would replace.
    E.Hypothesis(
        search="model_structure",
        name="explicit end-game segment: ROI exceeds extrapolated full-game efficiency",
        tested_on="2026-09-01", seasons=FEATURED, outcome="pending",
        predicted_direction="higher", stage="discovery",
    ),
    E.Hypothesis(
        search="model_structure",
        name="overtime as its own segment: ROI exceeds a scaled regulation distribution",
        tested_on="2026-09-01", seasons=FEATURED, outcome="pending",
        predicted_direction="higher", stage="discovery",
    ),
    E.Hypothesis(
        search="model_structure",
        name="fitted venue-level home effect: ROI exceeds one league-wide constant",
        tested_on="2026-09-01", seasons=FEATURED, outcome="pending",
        predicted_direction="higher", stage="discovery",
    ),
    E.Hypothesis(
        search="model_structure",
        name="quasi_neutral as a third venue state: ROI exceeds treating it as neutral",
        tested_on="2026-09-01", seasons=FEATURED, outcome="pending",
        predicted_direction="higher", stage="discovery",
    ),
    # --- The November regime. The brief warns of BOTH the most plausible edge
    # and the most likely catastrophic overconfidence, and a hypothesis cannot
    # predict both — so it is split into two, each falsifiable on its own, and
    # the pair is what the report reads.
    E.Hypothesis(
        search="november_prior",
        name="returning-production prior: ROI before December exceeds a flat prior",
        tested_on="2026-09-01", seasons=FEATURED, outcome="pending",
        predicted_direction="higher", stage="discovery",
    ),
    E.Hypothesis(
        search="november_prior",
        name="November ROI is below the rest of the season's",
        tested_on="2026-09-01", seasons=FEATURED, outcome="pending",
        # The overconfidence half. Predicted LOWER because a rating built on a
        # nearly-disconnected win/loss graph is identified almost entirely by
        # the prior, and a confident price on no connecting evidence is the
        # failure mode the connectivity diagnostic exists to refuse.
        predicted_direction="lower", stage="discovery",
    ),
    # --- Schedule states, tested the way the NHL lab tested back-to-backs: a
    # measured adjustment ships BECAUSE it wins the price backtest, and a
    # better-calibrated one that loses it is refused.
    *(
        E.Hypothesis(
            search="schedule_states",
            name=f"{state}: ROI with the adjustment exceeds ROI without it",
            tested_on="2026-09-01", seasons=FEATURED, outcome="pending",
            predicted_direction="higher", stage="discovery",
        )
        for state in (
            "short rest", "travel distance", "altitude",
            "conference tournament fatigue (four games in four days)",
        )
    ),
    # --- Reachability. Not an edge hypothesis, but it CAN flatter: a result
    # that lives only among prices that vanish is a finding until somebody
    # splits it. Predicted LOWER because that is the brief's own warning —
    # "the low-major games with the loosest lines have the smallest limits and
    # move fastest" — and a prediction that agrees with the flattering outcome
    # would be worth nothing.
    E.Hypothesis(
        search="reachability",
        name="ROI among prices that SURVIVED to the next capture exceeds ROI among those that did not",
        tested_on="2026-09-01", seasons=FEATURED, outcome="pending",
        predicted_direction="lower", stage="discovery",
    ),
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    args = parser.parse_args(argv)

    path = Path(args.output_dir) / E.LEDGER_FILENAME
    ledger = E.load(path)
    before = ledger.count
    # The entry count as loaded, handed to save() as the floor it may not
    # write below. save() used to re-read the file instead, which compared
    # this object's count with itself; see its docstring.
    loaded = len(ledger.hypotheses)
    added = ledger.record(*HYPOTHESES)
    E.save(ledger, path, floor=loaded)

    print(
        f"Experiment ledger: {before} distinct hypotheses before, "
        f"{ledger.count} after ({added} new)."
    )
    print(
        f"Any new 95% interval must be widened by "
        f"x{ledger.correction_factor():.2f} before it means what it says."
    )
    print(f"Wrote {path}")
    report = Path(args.output_dir) / "cbb_experiment_ledger.md"
    report.write_text(E.render(ledger), encoding="utf-8")
    print(f"Wrote {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
