"""Champion, challenger, and the two directions the machine may move.

Cooper's brief asks for a lab that improves itself, and immediately fences what
that is allowed to mean:

> **Self-improving must not mean "search until something looks good."** An
> automated edge-hunter without a cumulative tally does not find edges; it
> manufactures them on a schedule, with clean intervals and good prose.

This module is one half of that fence (the experiment ledger is the other). It
holds the rules by which a challenger model may replace a champion, and the
rule by which an allowlisted market is taken away from the card.

## The asymmetry, which is the whole design

**The machine may take a market away from itself. It may never give itself
one.**

- `demote()` is automatic, runs unattended, and needs nobody's permission. An
  allowlisted market whose forward ROI interval falls below the floor declared
  at its approval is withdrawn on the next weekly run.
- There is **no `grant()`** here, and there is none in
  `staging_provider_policy` either. Allowlisting a market requires a receipt
  Cooper signs. That is the single human stop in this project and the reason
  the rest of it can run unattended.

An automated system that can both grant and withdraw its own permissions is a
system whose safety rests on its own judgment being right. One that can only
withdraw is safe by construction, and the cost — a human in the loop for every
grant — is a cost worth paying exactly once per market.

## Why the promotion criteria live on disk

`data/manual/promotion_criteria.json`, written **before** any challenger is
measured. A margin chosen after seeing the comparison is not a margin, it is a
description of the result; and a threshold in code can be edited in the same
commit that reports the number it let through.

The football lab's verdict defect is the concrete version of this: a script
that scored one season and wrote a verdict file, so the policy shipped or did
not depending on which season had been run last — **same policy, same script,
opposite verdicts**. Its fix, ported here, is that a promotion must clear in
*every* season tested, not in the one that happened to run.

## What "beating the champion" has to mean

Four conditions, all of them, and the ordering matters:

1. **On the price backtest**, never on calibration. Calibration can rule a
   model out and can never rule one in — the EPL lab shipped a change that
   improved calibration on every market and cost about 140 units.
2. **Out of sample**, on a holdout the challenger was not fitted on and that
   was declared before discovery closed.
3. **By the pre-registered margin**, after the experiment ledger's cumulative
   correction is applied to the interval.
4. **In every season tested**, not on the pooled average of them. Pooling lets
   one good season carry two bad ones.

A challenger that clears three of the four does not get promoted, and the
record says which one it failed.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from cbb_betting_lab.competitions import CBB, Competition
from cbb_betting_lab.config import MANUAL_DIR

#: Written before the first challenger, and read rather than asserted.
CRITERIA_FILENAME = "promotion_criteria.json"


class PromotionError(RuntimeError):
    """Raised when the criteria file is missing or unreadable.

    It raises rather than defaulting. A missing criteria file must not mean
    "use the built-in defaults" — that is how a threshold quietly becomes
    whatever the code says today, which is the thing this file exists to stop.
    """


@dataclass(frozen=True)
class Criteria:
    """The bar a challenger must clear, declared in advance."""

    #: Percentage points of ROI the challenger must beat the champion by, on
    #: the price backtest, out of sample. Not "greater than": the arms' own
    #: intervals span several times the gap between two similar models, and
    #: comparing two overlapping intervals and taking the larger number is how
    #: a lab ships noise.
    roi_margin_points: float
    #: The challenger's own interval must exclude zero after correction. A
    #: challenger that merely beats a losing champion is still losing.
    require_interval_excludes_zero: bool
    #: Below this, the verdict is "not enough evidence" rather than a number.
    minimum_bets: int
    #: Must clear in EVERY season tested, never on the pooled average.
    must_clear_every_season: bool
    #: The forward ROI floor below which an allowlisted market is withdrawn.
    demotion_roi_floor: float
    #: How many settled forward bets before demotion may fire. A market
    #: withdrawn on twenty bets is withdrawn on noise.
    demotion_minimum_bets: int
    declared_on: str = ""
    why: str = ""


@dataclass(frozen=True)
class SeasonResult:
    """One season's priced comparison between two models."""

    season: int
    bets: int
    champion_roi: float
    challenger_roi: float
    challenger_low: float
    challenger_high: float

    @property
    def margin_points(self) -> float:
        """The challenger's edge over the champion, in PERCENTAGE POINTS.

        ROI is carried as a fraction everywhere in this lab (0.02 is 2%), and
        the criteria are declared in points because that is how a human reads
        them. The conversion lives here, once, because the first version of
        this module compared a fraction against a points threshold and was
        therefore a hundred times too strict — a challenger beating the
        champion by 2 points measured as 0.02 against a bar of 1.5, and no
        challenger could ever have been promoted.

        A unit mismatch in this direction fails safe and is still a defect: it
        would have read as "nothing ever clears the bar", which is exactly the
        answer this lab expects, so nothing would have looked wrong.
        """
        return (self.challenger_roi - self.champion_roi) * 100.0


@dataclass
class PromotionVerdict:
    """Whether a challenger may be promoted, and exactly why not."""

    promoted: bool = False
    reasons: list[str] = field(default_factory=list)
    seasons: tuple[SeasonResult, ...] = ()
    correction_factor: float = 1.0

    def line(self) -> str:
        if self.promoted:
            return (
                f"PROMOTED on {len(self.seasons)} season(s), correction "
                f"x{self.correction_factor:.2f}."
            )
        return "NOT PROMOTED: " + "; ".join(self.reasons)


def criteria_path(competition: Competition = CBB, manual_dir: Path | str | None = None) -> Path:
    directory = Path(manual_dir) if manual_dir else Path(MANUAL_DIR)
    return directory / CRITERIA_FILENAME


def load_criteria(
    competition: Competition = CBB, *, manual_dir: Path | str | None = None
) -> Criteria:
    path = criteria_path(competition, manual_dir)
    if not path.is_file():
        raise PromotionError(
            f"No promotion criteria at {path}. This file is read, never "
            "defaulted: a margin that falls back to whatever the code says "
            "today is not a pre-registered margin."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return Criteria(
        roi_margin_points=float(payload["roi_margin_points"]),
        require_interval_excludes_zero=bool(payload["require_interval_excludes_zero"]),
        minimum_bets=int(payload["minimum_bets"]),
        must_clear_every_season=bool(payload["must_clear_every_season"]),
        demotion_roi_floor=float(payload["demotion_roi_floor"]),
        demotion_minimum_bets=int(payload["demotion_minimum_bets"]),
        declared_on=str(payload.get("declared_on", "")),
        why=str(payload.get("why", "")),
    )


def judge(
    results: Sequence[SeasonResult],
    *,
    criteria: Criteria,
    correction_factor: float = 1.0,
) -> PromotionVerdict:
    """Whether the challenger clears every bar. All four, in order.

    `correction_factor` comes from the experiment ledger's CUMULATIVE count,
    never the day's. The fiftieth comparison does not get the first one's
    benefit of the doubt.
    """
    verdict = PromotionVerdict(
        seasons=tuple(results), correction_factor=float(correction_factor)
    )
    if not results:
        verdict.reasons.append("no seasons were scored")
        return verdict

    thin = [r for r in results if r.bets < criteria.minimum_bets]
    if thin:
        verdict.reasons.append(
            f"{len(thin)} season(s) below the {criteria.minimum_bets:,}-bet "
            "floor declared in advance — not enough evidence, which is not the "
            "same as a negative result"
        )

    short = [r for r in results if r.margin_points < criteria.roi_margin_points]
    if short:
        worst = min(r.margin_points for r in short)
        verdict.reasons.append(
            f"{len(short)} season(s) missed the {criteria.roi_margin_points:+.2f} "
            f"point margin (worst {worst:+.2f})"
        )

    if criteria.require_interval_excludes_zero:
        # The interval is widened by the correction BEFORE it is read. A
        # challenger whose raw interval excludes zero and whose corrected one
        # does not has not cleared anything.
        spanning = []
        for r in results:
            centre = (r.challenger_high + r.challenger_low) / 2.0
            half = (r.challenger_high - r.challenger_low) / 2.0 * correction_factor
            if (centre - half) <= 0.0 <= (centre + half):
                spanning.append(r.season)
        if spanning:
            verdict.reasons.append(
                f"the corrected interval includes zero in {len(spanning)} "
                f"season(s) {spanning} — no demonstrated edge"
            )

    if criteria.must_clear_every_season and verdict.reasons:
        return verdict
    verdict.promoted = not verdict.reasons
    return verdict


def should_demote(
    *, roi: float, low: float, high: float, bets: int, criteria: Criteria
) -> tuple[bool, str]:
    """Whether an allowlisted market's forward record has fallen through the floor.

    One direction only. This function can return True and cause a market to be
    withdrawn; nothing anywhere returns a value that causes one to be granted.
    """
    if bets < criteria.demotion_minimum_bets:
        return False, (
            f"{bets:,} settled bets is below the {criteria.demotion_minimum_bets:,} "
            "needed to withdraw a market. A market withdrawn on this much "
            "evidence is withdrawn on noise, and withdrawal is not free: it "
            "stops the forward evidence that would settle the question."
        )
    if high < criteria.demotion_roi_floor:
        return True, (
            f"the whole interval [{low:+.2%}, {high:+.2%}] over {bets:,} bets "
            f"sits below the {criteria.demotion_roi_floor:+.2%} floor declared "
            "at approval"
        )
    if roi < criteria.demotion_roi_floor:
        return False, (
            f"ROI {roi:+.2%} is below the floor but the interval "
            f"[{low:+.2%}, {high:+.2%}] still reaches it over {bets:,} bets. "
            "Not withdrawn: an interval that includes the floor has not "
            "demonstrated the market fell through it."
        )
    return False, f"ROI {roi:+.2%} over {bets:,} bets is above the floor."
