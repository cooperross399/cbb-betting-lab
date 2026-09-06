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

The player-prop family added on 2026-09-05 was checked against all three before
a line of it was written. None of the thirty-three falls foul: every one of
them compares a model's mean log loss against a benchmark, and every one of
them could have come out flattering. Two pieces of that build are excluded
outright and are deliberately absent below — the **wager reconciliation gate**
(261,870 measured against the brief's 257,474; a denominator has a right answer
and the run stops until it agrees) and the **fit reproduction gate** (every
dispersion constant refit to within ±0.05). Both are settlement validation in
the sense above: knowable independently, and unable to flatter anybody.

## Descriptive-only, and why it is a ledger entry rather than a promise

A third category sits between the two: quantities a run *prints* that are not
tests. The over/under split inside a cell is a mandatory disclosure. A refusal
census describes what the model declined to price. An unapplied diagnostic
column exists so a later session inherits the evidence rather than the
temptation. None is a claim about edge, so charging the family correction for
them would widen every real interval and buy nothing.

The danger is the other direction, and it is not hypothetical: a diagnostic
that came out well is exactly the number somebody later wants to report as a
finding, and it paid no correction, so reporting it reads an uncounted look as
a result. `DESCRIPTIVE_ONLY` below is therefore recorded **in the ledger**, and
`ExperimentLedger.record()` raises `PromotionRefused` on any hypothesis
carrying one of those names. The design document said these "may not be
promoted after the fact"; this is that sentence with a gate under it.

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

#: Every player-prop quote in the store is season 2024, and 90% of the subjects
#: are the same 1,357 names. There is no second season to hold out, so every
#: player hypothesis below is `discovery` and none of them may ever be called a
#: replication.
PLAYER = (2024,)

#: The ten markets the player-prop design prices, in the order its census
#: prints them (by wager count, descending). `player_first_basket` and
#: `player_double_double` are refused BY NAME in the design and are absent here
#: on purpose: a refused market costs no hypothesis, and the second refusal
#: says so in as many words — pricing it "would add a pre-registered
#: hypothesis, widening every other interval in the lab, in exchange for a
#: sample of one". Adding either later is an eleventh market and a new
#: registration, not a reading of this one.
PLAYER_MARKETS = (
    "points", "rebounds", "assists", "threes", "pra",
    "steals", "turnovers", "points_rebounds", "points_assists",
    "rebounds_assists",
)

#: Tier of the **player's own team**, from `conferences.tier_table`. The store's
#: per-game `tier` column is constant for neither side, so cutting on it would
#: file a high-major starter under whichever tier his opponent decided.
PLAYER_TIERS = ("high_major", "mid_major", "low_major")


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
    # --- The player-prop model, pre-registered on 2026-09-05 BEFORE the model
    # exists and before a single player number has been measured. That ordering
    # is the whole point: a direction declared after the numbers are seen is
    # not a prediction, and this family is registered against a design
    # document, not against a result.
    #
    # H1-H30. One per market and tier, thirty of them, and the size is
    # deliberate: the alternative is to look at thirty cells and correct as
    # though one had been looked at. The comparison is against the DE-VIGGED
    # two-sided fair price, joined on the same event, market, athlete, line and
    # book — never against the vigged implied probability, which turns a model
    # that loses into one that appears to win five markets, concentrated
    # exactly where two-sided coverage is thinnest (~1% beyond three rungs).
    #
    # `lower` throughout, because the metric is mean LOG LOSS: lower is the
    # model winning. The design's expected result is stated in the same breath
    # and is the opposite — "no demonstrated edge in any cell, and a deficit
    # against the de-vigged market in most of them" — which is what makes these
    # thirty falsifiable rather than decorative.
    #
    # The ten low-major cells are registered knowing they are underpowered by
    # construction: 6,198 quotes, 123 subjects, 19 games. They are here so they
    # cannot be dropped after they are seen, and they will be reported as "no
    # demonstrated edge, n = ..." whatever they return. There is no pooled
    # Division-I cell, ever.
    *(
        E.Hypothesis(
            search="player_props_vs_devig",
            name=(
                f"player_{market} / {tier}: the model's mean log loss is below "
                "the de-vigged two-sided fair price's"
            ),
            tested_on="2026-09-05",
            seasons=PLAYER,
            outcome="pending",
            predicted_direction="lower",
            stage="discovery",
        )
        for market in PLAYER_MARKETS
        for tier in PLAYER_TIERS
    ),
    # H31-H33. One per tier, pooled across the ten markets, against the
    # identity-blind role-prior control — the same store priced a second time
    # with every player replaced by the role prior at his projected minutes.
    # This is the negative control (L6) and it is the question the de-vig
    # comparison cannot answer: whether the player-specific half of the model
    # buys anything at all. Its number is printed BEFORE the headline.
    *(
        E.Hypothesis(
            search="player_props_vs_role_prior",
            name=(
                f"{tier}: the full model's mean log loss is below the "
                "identity-blind role-prior control's, pooled across the ten "
                "priceable markets"
            ),
            tested_on="2026-09-05",
            seasons=PLAYER,
            outcome="pending",
            predicted_direction="lower",
            stage="discovery",
        )
        for tier in PLAYER_TIERS
    ),
)


#: Quantities the player-prop run will compute and print and may NEVER report
#: as a finding. Each costs no hypothesis, and each is refused as one by
#: `ExperimentLedger.record()` — see this module's docstring, and
#: `DescriptiveOnly` for why the refusal is what makes the exemption honest.
DESCRIPTIVE_ONLY: tuple[E.DescriptiveOnly, ...] = (
    E.DescriptiveOnly(
        search="player_props_diagnostics",
        name="the over/under split within every priced cell",
        declared_on="2026-09-05",
        rationale=(
            "A mandatory disclosure, never netted: a cell that is +4% on overs "
            "and -4% on unders is a side bias, not an edge. Reading either half "
            "on its own doubles the cells without doubling the family, which is "
            "the subgroup search this ledger exists to price."
        ),
    ),
    E.DescriptiveOnly(
        search="player_props_diagnostics",
        name="calibration by |z| bucket",
        declared_on="2026-09-05",
        rationale=(
            "z = (line - mu)/sd IS the edge statistic. The design refuses to "
            "gate on it, because deleting the wagers where model and book most "
            "disagree makes the reported calibration true by construction. "
            "Printing it as a diagnostic is safe; reading a good bucket as a "
            "result is the same selection wearing a different hat."
        ),
    ),
    E.DescriptiveOnly(
        search="player_props_diagnostics",
        name="mean(actual)/mean(mu) per cell, and its matched non-quoted comparison",
        declared_on="2026-09-05",
        rationale=(
            "It reads settled outcomes, so it cannot run at T-60 and it deletes "
            "the cells where the answer was bad — which makes the Bonferroni "
            "correction anticonservative rather than conservative. It has no "
            "power to refuse anything and no standing to be a finding. The "
            "matched non-quoted arm exists to say what the ratio MEANS (level "
            "drift versus selection-by-being-quoted), not to score the model."
        ),
    ),
    E.DescriptiveOnly(
        search="player_props_diagnostics",
        name="the refusal census, per tier and per reason",
        declared_on="2026-09-05",
        rationale=(
            "A count of what the model declined to price, R1 through R5, with "
            "a missing entry (no opinion) counted separately from a refusal. "
            "It describes coverage. It is not a claim about returns, and the "
            "per-tier name-resolution rate inside it is a stop condition — the "
            "run halts if it moves more than 2pp across tiers — never a result."
        ),
    ),
    E.DescriptiveOnly(
        search="player_props_diagnostics",
        name="the minutes-projection R-squared and residual SD",
        declared_on="2026-09-05",
        rationale=(
            "A fit statistic on an input, not a return on a wager. The minutes "
            "model is explicitly unable to know whether a player will play, so "
            "a flattering R-squared here would say nothing about edge and "
            "everything about how predictable rotation minutes are."
        ),
    ),
    E.DescriptiveOnly(
        search="player_props_diagnostics",
        name="the robustness row for minutes half-life in {2, 3, 4, 5}",
        declared_on="2026-09-05",
        rationale=(
            "Half-life 4 is DECLARED, not selected: the fit-window curve is "
            "flat within 1% from 2 to 5. Printing the four is robustness. "
            "Picking the best of four after the fact is a four-way search "
            "reported as one number, and it is precisely how the rival design "
            "spent a holdout season on a 0.08% difference."
        ),
    ),
    E.DescriptiveOnly(
        search="player_props_diagnostics",
        name="every unapplied diagnostic column (pace ratio, opponent allowance)",
        declared_on="2026-09-05",
        rationale=(
            "Computed and stored, never applied to a price. They exist so a "
            "later session inherits the evidence rather than the temptation, "
            "and the bar to admit one was declared in advance: more than 2% of "
            "held-out RMSE, fitted on seasons strictly earlier than the "
            "validation season. Measured today at 0.13-0.29%. A column that "
            "priced nothing cannot have earned anything."
        ),
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
    # Declared BEFORE the hypotheses are recorded, so that a name appearing in
    # both lists is refused by `record()` on this very run rather than shipping
    # and being noticed by whoever reads the report.
    declared = ledger.declare(*DESCRIPTIVE_ONLY)
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
    # The same factor unrounded, because two decimals hide the size of what an
    # append costs the intervals already published. 62 -> 95 hypotheses reads
    # as x1.71 -> x1.77 rounded and as x1.7095 -> x1.7689 exactly, and it is
    # the exact pair that decides whether a bound crosses zero.
    print(f"Exactly: x{ledger.correction_factor():.4f} over {ledger.count} hypotheses.")
    print(
        f"Descriptive-only: {len(ledger.descriptive_only)} quantities declared "
        f"({declared} new). They cost no hypotheses and can never be reported "
        f"as a finding; record() refuses to promote one."
    )
    print(f"Wrote {path}")
    report = Path(args.output_dir) / "cbb_experiment_ledger.md"
    report.write_text(E.render(ledger), encoding="utf-8")
    print(f"Wrote {report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
