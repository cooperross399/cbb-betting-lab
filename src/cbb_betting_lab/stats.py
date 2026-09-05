"""The arithmetic, in one place, so no two reports can disagree about it.

The NHL lab has this module and the football lab does not — and the football
lab pays for it: `_bonferroni_factor` is re-implemented in four files and
`_interval` is copy-pasted between two more, with a hardcoded `1.96` in the
copies against `Z95` in the original. Two copies of a formula drift, and the
direction they drift in is never the conservative one.

Everything that produces a number in this repository imports from here.

## The clustered interval, and the defect this file exists to not repeat

**One game supplies many correlated bets.** A team's spread, the game total,
that team's total and its centre's rebounds are one evening seen four ways, and
a naive per-bet interval over them is narrower than the truth. In college
basketball that is not a rounding matter: a hundred-game Tuesday can carry a
thousand wagers across a hundred clusters, and treating them as a thousand
independent observations understates every interval by roughly the square root
of the cluster size.

The football lab's forward ledger got this wrong, and the error is large.
Its `interval_by_game` computes

    variance = Σ(wᵢ² · s² / G) · G     standard_error = √(variance / G)

which is algebraically `s·√(Σwᵢ²)/√G`; with roughly equal clusters `Σwᵢ² ≈ 1/G`
so it lands at `s/G` where a cluster standard error is `s/√G`. Reproduced here
on 632 synthetic bets over 200 clusters before it was fixed: the ratio
estimator below gives 0.03694, a cluster bootstrap gives 0.03683, and the
football lab's formula gives **0.00356 — 10.3× too narrow**, on the one report
that grows all season and whose own docstring says *"a narrow interval is how
'no demonstrated edge' quietly becomes a claim."*

`tests/test_clustered_interval_is_not_too_narrow.py` reproduces the defect and
pins the fix against a cluster bootstrap. The sibling lab is not touched — the
finding is recorded in `docs/ported_defects.md` instead, per Cooper's
instruction.

## Two cluster units, and why the wider one wins

Dependence in this sport runs **within a game**: the same possessions settle
every market on it. That makes the game the canonical cluster.

But it is not the only one. A model with a shared daily component — a pace
prior refit nightly, a calibration map fitted to yesterday — makes an entire
slate correlated, and then the day is the honest unit. This lab cannot know in
advance which applies, so `interval_two_way` computes both and reports the
**wider**. Choosing the narrower after seeing both is exactly the move this
whole document set exists to prevent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from statistics import NormalDist

import pandas as pd


#: Two-sided 95%. Never `1.96` — the rounded copy is what let the football
#: lab's corrected intervals drift from its uncorrected ones.
Z95 = 1.959963984540054

#: The only permitted reading of an interval that includes zero. Reproduced
#: verbatim by every report; `tests/test_the_headline_reads_the_sign.py` pins it.
NO_DEMONSTRATED_EDGE = "no demonstrated edge"

#: And its opposite, which is not "an edge". An interval excluding zero on the
#: losing side is a demonstrated **deficit**, and the NHL lab's claims document
#: once announced one as good news because its headline predicate never read
#: the sign.
DEMONSTRATED_DEFICIT = "demonstrated deficit"
DEMONSTRATED_EDGE = "demonstrated edge"

#: Below this, a market's verdict is "not enough evidence" rather than a
#: number. Declared here, in advance, and per market in `MINIMUM_BETS_BY_TIER`.
MINIMUM_BETS = 200


def bonferroni_z(looks: int) -> float:
    """The z a result must clear once `looks` of them have been tested.

    Bonferroni. The alternative is a sharper correction that needs assumptions
    about how the markets covary, and nothing in this repository has measured
    that. It is also the only correction that can be computed incrementally,
    which matters because this lab's tests arrive one week at a time over a
    season rather than all at once.
    """
    families = max(int(looks), 1)
    if families <= 1:
        return Z95
    return NormalDist().inv_cdf(1 - (0.05 / families) / 2)


def bonferroni_factor(looks: int) -> float:
    """How much wider a 95% interval must be, as a multiplier."""
    return bonferroni_z(looks) / Z95


@dataclass(frozen=True)
class RoiInterval:
    """A return, its interval, and what it took to test it."""

    roi: float
    low: float
    high: float
    bets: int
    clusters: int
    standard_error: float = 0.0
    #: How many results were tested in the same family. The correction is
    #: applied from this, and it is the experiment ledger's cumulative count
    #: rather than the day's wherever the ledger is available.
    looks: int = 1
    cluster_unit: str = "game"

    @property
    def adjusted_low(self) -> float:
        if self.looks <= 1 or not self.standard_error:
            return self.low
        return self.roi - bonferroni_z(self.looks) * self.standard_error

    @property
    def adjusted_high(self) -> float:
        if self.looks <= 1 or not self.standard_error:
            return self.high
        return self.roi + bonferroni_z(self.looks) * self.standard_error

    @property
    def enough_evidence(self) -> bool:
        return self.bets >= MINIMUM_BETS

    @property
    def survives_correction(self) -> bool:
        """Whether the result still excludes zero once the search is counted."""
        if not self.enough_evidence:
            return False
        return not (self.adjusted_low <= 0.0 <= self.adjusted_high)

    @property
    def return_sits_inside_its_own_interval(self) -> bool:
        """Whether `roi` lies between the two bounds printed beside it.

        False is not a rounding matter — it is a row that cannot have come out
        of any estimator, because the interval is built around the estimate. It
        is what a hand-edited or half-refreshed record looks like: a return
        typed over one measurement and bounds left from another. A reader is
        shown both numbers on one line, so a report that finds this False must
        refuse rather than choose which of the two to believe.
        """
        return self.adjusted_low <= self.roi <= self.adjusted_high

    def verdict(self) -> str:
        """The one sentence this result is permitted to be described by.

        **It reads the sign.** The NHL lab's claims document triggered "at
        least one result survived the correction and then replicated" on a
        market that had replicated a *loss*, because its headline predicate
        tested measured + survives-correction + replicated and never looked at
        which side of zero the number sat on. The one document whose job is to
        stop a number being misread must not be the thing misreading it.

        **Which sign it reads is the corrected interval's**, because that pair
        is what a report prints beside this sentence. Reading `roi` instead is
        indistinguishable on real data and wrong on exactly the rows that
        matter: a record carrying a typed `+5%` over corrected bounds of −9% to
        −2% would be handed the words *demonstrated edge* over an interval
        lying entirely on the losing side of zero.
        """
        if not self.enough_evidence:
            return (
                f"not enough evidence ({self.bets:,} bets, below the "
                f"{MINIMUM_BETS:,} declared in advance)"
            )
        if not self.survives_correction:
            return NO_DEMONSTRATED_EDGE
        # **The sign is read off the bounds, not off `roi`.** The two agree for
        # every interval an estimator produced, because the interval is centred
        # on the estimate — so this is the same answer on real data and a
        # different one on a row where the return and its bounds disagree. There
        # the bounds win: they are the pair the verdict is a statement about,
        # and `adjusted_high < 0` is a demonstrated *deficit* however positive
        # the number typed beside it. `return_sits_inside_its_own_interval`
        # exists so a report can refuse such a row outright rather than print
        # a sentence and a figure that contradict each other.
        return DEMONSTRATED_EDGE if self.adjusted_low > 0.0 else DEMONSTRATED_DEFICIT

    def line(self) -> str:
        return (
            f"{self.roi:+.1%} over {self.bets:,} bets across {self.clusters:,} "
            f"{self.cluster_unit}s, 95% interval {self.low:+.1%} to "
            f"{self.high:+.1%}"
            + (
                f", family-corrected {self.adjusted_low:+.1%} to "
                f"{self.adjusted_high:+.1%} across {self.looks:,} looks"
                if self.looks > 1
                else ""
            )
            + f" — {self.verdict()}"
        )


def interval_by_cluster(
    per_cluster: pd.DataFrame,
    *,
    looks: int = 1,
    cluster_unit: str = "game",
    profit_column: str = "profit",
    bets_column: str = "bets",
) -> RoiInterval:
    """ROI and a 95% interval from **between-cluster** variation.

    The ratio-estimator standard error, which is what a cluster bootstrap
    agrees with. `per_cluster` is one row per cluster with the cluster's total
    profit and its bet count — build it with
    `df.groupby(key).agg(profit=(...,"sum"), bets=(...,"size"))`.
    """
    if per_cluster.empty:
        return RoiInterval(0.0, 0.0, 0.0, 0, 0, looks=looks, cluster_unit=cluster_unit)
    total = int(per_cluster[bets_column].sum())
    clusters = int(len(per_cluster))
    if not total:
        return RoiInterval(
            0.0, 0.0, 0.0, 0, clusters, looks=looks, cluster_unit=cluster_unit
        )
    roi = float(per_cluster[profit_column].sum() / total)
    if clusters < 2:
        return RoiInterval(
            roi,
            float("-inf"),
            float("inf"),
            total,
            clusters,
            looks=looks,
            cluster_unit=cluster_unit,
        )
    mean_bets = total / clusters
    residual = per_cluster[profit_column] - roi * per_cluster[bets_column]
    variance = float((residual**2).sum())
    standard_error = math.sqrt(variance / (clusters * (clusters - 1))) / mean_bets
    return RoiInterval(
        roi=roi,
        low=roi - Z95 * standard_error,
        high=roi + Z95 * standard_error,
        bets=total,
        clusters=clusters,
        standard_error=standard_error,
        looks=looks,
        cluster_unit=cluster_unit,
    )


def interval_two_way(
    bets: pd.DataFrame,
    *,
    game_column: str = "event_id",
    day_column: str = "slate_date",
    profit_column: str = "profit_units",
    looks: int = 1,
) -> RoiInterval:
    """Cluster by game **and** by day, and report the wider.

    Dependence runs within a game, which makes the game the canonical unit. But
    a model with a shared daily component makes a whole slate correlated, and
    then the day is the honest unit. This lab cannot know in advance which
    applies, so it computes both and takes the wider — because choosing the
    narrower after seeing both is the move the rest of this repository exists
    to prevent.
    """
    if bets.empty:
        return RoiInterval(0.0, 0.0, 0.0, 0, 0, looks=looks)
    by_game = interval_by_cluster(
        bets.groupby(game_column).agg(
            profit=(profit_column, "sum"), bets=(profit_column, "size")
        ),
        looks=looks,
        cluster_unit="game",
    )
    by_day = interval_by_cluster(
        bets.groupby(day_column).agg(
            profit=(profit_column, "sum"), bets=(profit_column, "size")
        ),
        looks=looks,
        cluster_unit="day",
    )
    return by_game if by_game.standard_error >= by_day.standard_error else by_day


def bets_needed_to_detect(edge: float, *, spread: float = 1.0) -> int:
    """How many bets separate a true edge of this size from zero at 95%."""
    if edge <= 0:
        return 0
    return int(math.ceil((Z95 * spread / edge) ** 2))


def detection_table(
    edges: tuple[float, ...] = (0.05, 0.08, 0.10, 0.15)
) -> list[tuple[float, int]]:
    """The sample-size table. This arithmetic does not depend on the sport."""
    return [(e, bets_needed_to_detect(e)) for e in edges]


def wilson_interval(successes: int, trials: int) -> tuple[float, float]:
    """A proportion's 95% interval, Wilson rather than normal-approximation.

    Wilson because the normal approximation is wrong exactly where this lab
    looks hardest: small counts and proportions near zero or one, which is
    where every rare-event market lives.
    """
    if trials <= 0:
        return 0.0, 0.0
    p = successes / trials
    denominator = 1 + Z95**2 / trials
    centre = (p + Z95**2 / (2 * trials)) / denominator
    half = (
        Z95
        * math.sqrt(p * (1 - p) / trials + Z95**2 / (4 * trials**2))
        / denominator
    )
    return max(0.0, centre - half), min(1.0, centre + half)


def looks_significant_but_is_a_multiple_comparison(
    significant: int, looks: int
) -> bool:
    """True when the count of 'significant' results is what chance would give.

    At a nominal 5% level, one look in twenty clears by accident. A search that
    tested forty things and found two is a search that found nothing.
    """
    if looks <= 0:
        return False
    return significant <= max(1, int(round(0.05 * looks)))


ROI_TABLE_HEADER = (
    "| Market | Bets | Games | ROI | 95% interval | Family-corrected | Verdict |\n"
    "|:---|---:|---:|---:|:---|:---|:---|"
)


def roi_table_row(name: str, interval: RoiInterval) -> str:
    return (
        f"| {name} | {interval.bets:,} | {interval.clusters:,} | "
        f"{interval.roi:+.1%} | {interval.low:+.1%} to {interval.high:+.1%} | "
        f"{interval.adjusted_low:+.1%} to {interval.adjusted_high:+.1%} | "
        f"{interval.verdict()} |"
    )
