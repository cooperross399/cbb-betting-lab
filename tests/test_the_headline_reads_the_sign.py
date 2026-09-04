"""A replicated loss is not good news, and the headline must not say it is.

The NHL lab's `what_we_can_claim` announced *"at least one result survived the
correction and then replicated"* on a market returning **-6.6%**. Its headline
predicate tested measured + survives-correction + replicated and never read the
sign. The one document whose job is to stop a number being misread must not be
the thing misreading it.

This is a day-one regression test in this repository because it was a day-one
defect in two of the three siblings.
"""

from __future__ import annotations

import pytest

from cbb_betting_lab.stats import (
    DEMONSTRATED_DEFICIT,
    DEMONSTRATED_EDGE,
    MINIMUM_BETS,
    NO_DEMONSTRATED_EDGE,
    RoiInterval,
)


def _interval(roi: float, half_width: float, bets: int = 50_000) -> RoiInterval:
    return RoiInterval(
        roi=roi,
        low=roi - half_width,
        high=roi + half_width,
        bets=bets,
        clusters=bets // 4,
        standard_error=half_width / 1.959963984540054,
    )


def test_a_significant_loss_is_a_deficit_and_never_an_edge():
    result = _interval(-0.066, 0.02)
    assert result.survives_correction
    assert result.verdict() == DEMONSTRATED_DEFICIT
    assert result.verdict() != DEMONSTRATED_EDGE


def test_a_significant_gain_is_an_edge():
    assert _interval(+0.066, 0.02).verdict() == DEMONSTRATED_EDGE


def test_an_interval_including_zero_says_no_demonstrated_edge_in_those_words():
    assert _interval(+0.05, 0.09).verdict() == NO_DEMONSTRATED_EDGE
    assert _interval(-0.05, 0.09).verdict() == NO_DEMONSTRATED_EDGE


@pytest.mark.parametrize("roi", [-0.30, -0.01, 0.0, 0.01, 0.30])
def test_below_the_declared_floor_the_verdict_is_never_a_number(roi: float):
    """A market under the pre-declared sample floor gets a phrase, not a figure."""
    thin = _interval(roi, 0.01, bets=MINIMUM_BETS - 1)
    assert "not enough evidence" in thin.verdict()
    assert thin.verdict() not in {DEMONSTRATED_EDGE, DEMONSTRATED_DEFICIT}
    assert not thin.survives_correction


def test_the_family_correction_can_turn_an_edge_into_no_demonstrated_edge():
    """Testing many markets must widen the interval, not be optional."""
    one_look = RoiInterval(
        roi=0.05, low=0.01, high=0.09, bets=50_000, clusters=12_000,
        standard_error=0.0204, looks=1,
    )
    many_looks = RoiInterval(
        roi=0.05, low=0.01, high=0.09, bets=50_000, clusters=12_000,
        standard_error=0.0204, looks=40,
    )
    assert one_look.verdict() == DEMONSTRATED_EDGE
    assert many_looks.verdict() == NO_DEMONSTRATED_EDGE
    assert many_looks.adjusted_low < one_look.adjusted_low


# ---------------------------------------------------------------------------
# The headline itself
# ---------------------------------------------------------------------------
#
# Everything above pins `stats.RoiInterval`, which is where the sign is read.
# That is necessary and it is not sufficient: the NHL lab's defect was not in
# its arithmetic, it was in a **headline predicate** that tested
# measured + survives-correction + replicated and never consulted the
# arithmetic's answer. So these tests drive the real document end to end — a
# fabricated price-backtest record on disk, a replication record saying the
# market replicated, and an assertion about the sentence a human reads.

import json
from pathlib import Path

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import REPO_ROOT
from cbb_betting_lab.reports import price_backtest
from cbb_betting_lab.reports import what_we_can_claim as WC


def _cell(
    *,
    market: str = "spread",
    tier: str = "low_major",
    roi: float,
    half_width: float,
    bets: int = 9_000,
    clusters: int = 2_200,
) -> dict:
    return {
        "name": "",
        "market": market,
        "tier": tier,
        "roi": roi,
        "low": roi - half_width,
        "high": roi + half_width,
        "adjusted_low": roi - half_width,
        "adjusted_high": roi + half_width,
        "bets": bets,
        "clusters": clusters,
        "cluster_unit": "game",
        "looks": 1,
        "standard_error": half_width / 1.959963984540054,
        "enough_evidence": bets >= MINIMUM_BETS,
        "verdict": "",
    }


def _write_evidence(
    outputs: Path,
    *,
    cells: list[dict],
    replicated: tuple[str, ...] = (),
    pooled: list[dict] | None = None,
) -> None:
    """A price-backtest record and an optional replication record on disk."""
    outputs.mkdir(parents=True, exist_ok=True)
    record = {
        "record_version": price_backtest.RECORD_VERSION,
        "competition": CBB.key,
        "generated_at": "2027-04-19T00:00:00+00:00",
        "season_label": "2026-27",
        "by_market_and_tier": cells,
        "pooled": pooled or [],
    }
    price_backtest.record_path(CBB, outputs).write_text(
        json.dumps(record, indent=2), encoding="utf-8"
    )
    if replicated:
        WC.replication_path(CBB, outputs).write_text(
            json.dumps(
                {
                    "test_label": "2025-26",
                    "markets": [
                        {"market": m, "state": "replicated"} for m in replicated
                    ],
                }
            ),
            encoding="utf-8",
        )


def _record(tmp_path: Path, **kwargs) -> dict:
    outputs = tmp_path / "outputs"
    _write_evidence(outputs, **kwargs)
    return WC.build_record(
        competition=CBB,
        output_dir=outputs,
        processed_dir=tmp_path / "processed",
        manual_dir=tmp_path / "manual",
    )


def test_a_replicated_loss_is_never_announced_as_an_edge(tmp_path: Path):
    """**The defect, reproduced against the real document.**

    A market returning −6.6% over 9,000 bets whose interval excludes zero and
    which then replicates satisfies the NHL lab's headline predicate exactly:
    measured, survives the correction, replicated. It announced that as *"at
    least one result survived the correction and then replicated"*, which reads
    as good news and was a loss.
    """
    record = _record(
        tmp_path, cells=[_cell(roi=-0.066, half_width=0.02)], replicated=("spread",)
    )

    assert WC.demonstrated_edges(record) == []
    assert len(WC.demonstrated_deficits(record)) == 1

    line = WC.headline(record)
    assert DEMONSTRATED_DEFICIT in line
    assert "loss" in line.casefold()
    assert "profitable" not in line.casefold(), (
        "The headline called a −6.6% market profitable. This is the NHL lab's "
        "defect, reproduced: its predicate never read the sign."
    )
    assert "survived the correction and then replicated" not in line


def test_the_replication_of_a_loss_is_reported_as_making_the_loss_credible(
    tmp_path: Path,
):
    """Replication is evidence a result is real, not evidence it is good."""
    line = WC.headline(
        _record(
            tmp_path,
            cells=[_cell(roi=-0.066, half_width=0.02)],
            replicated=("spread",),
        )
    )

    assert "replicated" in line
    assert "**more** credible" in line
    assert "never evidence that it is good" in line


def test_a_replicated_gain_is_the_only_thing_that_may_be_called_profitable(
    tmp_path: Path,
):
    record = _record(
        tmp_path, cells=[_cell(roi=+0.066, half_width=0.02)], replicated=("spread",)
    )

    line = WC.headline(record)
    assert len(WC.demonstrated_edges(record)) == 1
    assert WC.demonstrated_deficits(record) == []
    assert "profitable" in line
    assert "replicated" in line
    # Even here it is a candidate for a receipt and nothing more.
    assert "human acceptance receipt" in line


def test_a_surviving_gain_that_has_not_replicated_is_a_candidate_not_a_finding(
    tmp_path: Path,
):
    line = WC.headline(_record(tmp_path, cells=[_cell(roi=+0.066, half_width=0.02)]))

    assert "candidates, not findings" in line
    assert "profitable" not in line.casefold()


def test_an_interval_spanning_zero_yields_the_exact_phrase(tmp_path: Path):
    line = WC.headline(_record(tmp_path, cells=[_cell(roi=+0.02, half_width=0.09)]))

    assert NO_DEMONSTRATED_EDGE.capitalize() in line


def test_a_deficit_headline_does_not_open_with_no_demonstrated_edge(tmp_path: Path):
    """The two phrases mean different things and must not be interchanged.

    `no demonstrated edge` is reserved for an interval that **includes** zero. A
    deficit's interval excludes it, and opening a deficit headline with the
    reserved phrase would blur the one distinction the phrase exists to make.
    """
    line = WC.headline(_record(tmp_path, cells=[_cell(roi=-0.066, half_width=0.02)]))

    assert not line.startswith(f"**{NO_DEMONSTRATED_EDGE.capitalize()}")
    assert line.startswith("**The only result that survives is a loss.**")


def test_below_the_sample_floor_the_headline_is_a_phrase_and_not_a_number(
    tmp_path: Path,
):
    record = _record(
        tmp_path,
        cells=[_cell(roi=+0.317, half_width=0.01, bets=57, clusters=41)],
    )
    line = WC.headline(record)

    assert "sample floor" in line
    # The bet count IS printed — a sample size is the thing this document
    # insists on. The *return* is not, at any width.
    assert "57 bets" in line
    for spelling in ("31.7", "+31", "0.317"):
        assert spelling not in line, (
            f"The return appeared in the headline as {spelling!r} over 57 bets. "
            "Below the floor this document prints a phrase and not a number, "
            "because printing the figure invites somebody to quote it out of "
            "the row that qualifies it."
        )
    assert WC.demonstrated_edges(record) == []


def test_the_headline_is_never_the_pooled_division_one_figure(tmp_path: Path):
    """A pooled figure is computed for the stopping rule and never headlined.

    High-major, mid-major and low-major are different distributions. The
    headline reads `record["claims"]`, which is per market **and** tier; the
    pooled block lives in its own key and is structurally unreachable from it.
    """
    pooled_edge = _cell(roi=+0.20, half_width=0.02)
    pooled_edge["name"] = "every market"
    record = _record(tmp_path, cells=[], pooled=[pooled_edge])

    assert WC.demonstrated_edges(record) == []
    assert "nothing has been measured against real prices yet" in WC.headline(record)
    assert record["pooled"], "the pooled block should still be carried, just not headlined"


def test_a_futures_return_never_reaches_a_headline_over_game_bets(tmp_path: Path):
    """Futures tie up stake for months and settle on a different clock.

    A +30% futures result that replicates is still not a headline over game
    bets. The headline says so explicitly rather than claiming nothing was
    measured, because a bought and settled futures price **is** a measurement —
    it is just one that may never be folded into a figure over game bets.
    """
    record = _record(
        tmp_path,
        cells=[_cell(market="championship_winner", roi=+0.30, half_width=0.05)],
        replicated=("championship_winner",),
    )
    line = WC.headline(record)

    assert WC.demonstrated_edges(record) == []
    assert "No game market has been measured against real prices." in line
    assert "never folded into a headline over game bets" in line
    assert "+30" not in line
    assert any(c["is_futures"] for c in record["claims"])


def test_a_second_half_market_is_not_evidence_either_way(tmp_path: Path):
    """A settlement rule this lab cannot verify is neither an edge nor a deficit.

    Second-half wagers settle including overtime at most US books and not at all
    of them. That is a book rule, not a fact about basketball, and a number
    computed on an unverified settlement rule is an artefact at any sample size
    — which is the shape of the football lab's largest false finding.
    """
    record = _record(
        tmp_path,
        cells=[_cell(market="spread_h2", roi=+0.066, half_width=0.02)],
        replicated=("spread_h2",),
    )

    assert WC.demonstrated_edges(record) == []
    assert WC.demonstrated_deficits(record) == []
    assert len(WC.not_evidence(record)) == 1
    assert "not evidence" in WC.headline(record)


def test_the_rendered_headline_is_recomputed_and_not_read_from_the_record(
    tmp_path: Path,
):
    """A record whose stored headline is a lie still renders the true one.

    The headline sits directly above the table it describes. If it were copied
    out of the record, a stale or hand-edited record could put a sentence over
    numbers that contradict it — which is the failure mode this whole document
    exists to prevent, one level up.
    """
    record = _record(tmp_path, cells=[_cell(roi=-0.066, half_width=0.02)])
    record["headline"] = "**Everything is fine and this market is profitable.**"

    rendered = WC.render(record)
    assert "Everything is fine" not in rendered
    assert "The only result that survives is a loss." in rendered


def test_the_sample_floor_here_matches_the_document_that_declared_it():
    """`docs/when_this_ends.md` declared both numbers before any data existed.

    A floor that quietly moved is not a floor, so the constants this report
    prints are pinned against the document that set them.
    """
    text = (Path(REPO_ROOT) / "docs" / "when_this_ends.md").read_text(encoding="utf-8")

    assert f"{WC.SAMPLE_FLOOR_OPINIONS:,} settled opinions" in text
    assert f"{WC.SAMPLE_FLOOR_GAMES:,} distinct games" in text
    assert WC.DECISION_DATE in text


def test_an_absent_ledger_is_never_reported_as_a_family_of_one():
    """The most dangerous shape of an absent measurement in this repository.

    `looks_from_ledger` returns `max(count, 1)`, so a ledger that is not there
    and a ledger holding one entry are the same integer. The renderer stated
    that integer as fact — *"Family correction: 1 cumulative hypotheses in
    experiment ledger"* — about a file it had never opened.

    A correction of x1.00 widens nothing, so an absent ledger makes every
    result on the page look **more** significant than it is, and the sentence
    claiming otherwise reads exactly like a measurement. Caught when a
    discovery run was pointed at a fresh `--output-dir`.
    """
    from cbb_betting_lab.reports import price_backtest as PB

    absent = PB.render({"record_version": PB.RECORD_VERSION, "looks": 1,
                        "ledger_read": False, "correction_factor": 1.0})
    assert "NO FAMILY CORRECTION WAS APPLIED" in absent
    assert "unknown family" in absent
    assert "1 cumulative hypotheses" not in absent, (
        "An absent ledger is still being described as a family of one."
    )

    present = PB.render({"record_version": PB.RECORD_VERSION, "looks": 30,
                         "ledger_read": True, "correction_factor": 1.6})
    assert "30 cumulative hypotheses" in present
    assert "NO FAMILY CORRECTION WAS APPLIED" not in present


def test_ledger_was_read_distinguishes_absent_from_empty():
    from pathlib import Path

    from cbb_betting_lab.reports import price_backtest as PB

    assert PB.ledger_was_read(None) is False
    assert PB.ledger_was_read(Path("/definitely/not/here.json")) is False
    real = Path(__file__).resolve().parents[1] / "data" / "outputs" / "experiment_ledger.json"
    if real.is_file():
        assert PB.ledger_was_read(real) is True
        assert PB.looks_from_ledger(real) > 1
