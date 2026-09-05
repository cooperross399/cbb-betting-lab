"""The forecast-skill entry point, run the way an operator runs it.

`reports/forecast_skill.py` owns every number and is tested on its own terms in
`test_forecast_skill.py`. This file tests the **wiring**, and each test is named
for one way the answer to Cooper's item 3 could be lost or manufactured:

* a ledger that does not exist yet — no forward opinion has been frozen and
  settled — producing an empty report, which reads as a null result, which is a
  claim;
* a ledger that parses into the wrong shape, whose absent columns would be
  padded with NA and fitted over;
* a model whose probability never differs from the price, whose disagreement
  coefficient is then **undefined rather than zero** — publishing 0.000 there
  publishes a wiring fault as the answer to the question this lab exists to ask;
* the ledger's `snapshot_date` not becoming the slate day, so the day cluster
  silently becomes one cluster;
* the market coefficient, or Brier, or the buckets printed **before** the
  disagreement coefficient, which is the order in which a reader forms the
  belief the first line exists to prevent;
* a pooled Division I line printed without its tier lines;
* a family correction taken from the day's count rather than the ledger's
  cumulative one;
* a report that can only be produced by re-running the measurement, which is a
  report nobody improves and a generated file somebody edits by hand.

The fixture is a small settled ledger on disk, in the real
`forward_evidence.LEDGER_COLUMNS` shape, because that is the file the script
defaults to and the shape is the thing most likely to drift.
"""

from __future__ import annotations

import contextlib
import io
import json
import runpy
import socket
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.conferences import Tier
from cbb_betting_lab.experiment_ledger import LEDGER_FILENAME as EXPERIMENT_LEDGER
from cbb_betting_lab.forward_evidence import (
    LEDGER_COLUMNS,
    expected_value,
    profit_units,
)
from cbb_betting_lab.forward_evidence import LEDGER_FILENAME as FORWARD_LEDGER
from cbb_betting_lab.reports import forecast_skill as FS
from cbb_betting_lab.selection import FULL_GAME

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "run_forecast_skill.py"

#: A constant hold, so the de-vig has something to remove and the arithmetic in
#: the assertions is exact.
OVERROUND = 1.045

#: Above `forecast_skill.MINIMUM_CLUSTERS` on both cluster units, so the run
#: produces a number rather than the *not enough evidence* phrase — the phrase
#: is tested in `test_forecast_skill.py` and would hide every wiring assertion
#: here behind an em dash.
GAMES = 80
DAYS = 40
RUNGS = 6


def _american(probability: float) -> float:
    payout = 1.0 / probability - 1.0
    return 100.0 * payout if payout >= 1.0 else -100.0 / payout


def settled_ledger(
    *, kind: str = "noise", games: int = GAMES, days: int = DAYS, seed: int = 19
) -> pd.DataFrame:
    """A forward ledger in the real column shape, frozen and settled.

    `kind="noise"` makes the model's disagreement pure noise, which is the
    expected result and the one every wiring assertion here is written against.
    `kind="agrees"` makes the model's probability **equal** the de-vigged price
    on every row, which is the not-identified case.
    `kind="anti"` makes the home side win with probability
    `fair - 0.5 x (model - fair)`, so the bigger the model's claimed edge the
    worse the bet — the same data-generating process
    `test_forecast_skill.graded_frame` uses for its `anti` fixture, and the only
    one that drives the script's realised-return line, which is printed only
    when the return actually falls across the claimed-edge buckets.
    """
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    for game in range(games):
        day = f"2027-02-{(game % days) + 1:02d}"
        for rung in range(RUNGS):
            line = -7.5 + 3.0 * rung
            fair = float(rng.uniform(0.32, 0.68))
            model = (
                fair
                if kind == "agrees"
                else float(np.clip(fair + rng.normal(0.0, 0.06), 0.02, 0.98))
            )
            realised = (
                float(np.clip(fair - 0.5 * (model - fair), 0.02, 0.98))
                if kind == "anti"
                else fair
            )
            home_won = float(rng.random()) < realised
            for selection, side_line, raw, probability, won in (
                ("home", line, fair * OVERROUND, model, home_won),
                ("away", -line, (1.0 - fair) * OVERROUND, 1.0 - model, not home_won),
            ):
                odds = _american(raw)
                outcome = "won" if won else "lost"
                rows.append(
                    {
                        "snapshot_date": day,
                        "commence_time": f"{day}T23:00:00Z",
                        "event_id": f"e{game:03d}",
                        "home_team": f"Home {game}",
                        "away_team": f"Away {game}",
                        "market": "alternate_spread",
                        "segment": FULL_GAME,
                        "player": "",
                        "selection": selection,
                        "line": side_line,
                        "american_odds": odds,
                        "book": "dk",
                        "model_probability": probability,
                        "edge": expected_value(probability, odds),
                        "calibrated_probability": "",
                        "calibrated_edge": "",
                        "prior_weight": 0.4,
                        "tier": (
                            Tier.HIGH_MAJOR.value
                            if game % 2
                            else Tier.LOW_MAJOR.value
                        ),
                        "verdicts_in_force": "accumulating evidence",
                        "settled_at": f"{day}T06:00:00Z",
                        "outcome": outcome,
                        "actual": 0.0,
                        "profit_units": profit_units(outcome, odds),
                    }
                )
    return pd.DataFrame(rows, columns=list(LEDGER_COLUMNS))


class Lab:
    """The directory layout an operator hands the script, built in tmp_path."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.processed = root / "processed"
        self.outputs = root / "outputs"
        for directory in (self.processed, self.outputs):
            directory.mkdir(parents=True, exist_ok=True)
        self.record_path = FS.record_path(CBB, self.outputs)
        self.report_path = FS.report_path(CBB, self.outputs)
        self.ledger_path = self.processed / FORWARD_LEDGER

    def with_ledger(self, frame: pd.DataFrame | None = None, **kwargs) -> "Lab":
        (settled_ledger(**kwargs) if frame is None else frame).to_csv(
            self.ledger_path, index=False
        )
        return self

    def with_experiment_ledger(self, hypotheses: int) -> "Lab":
        (self.outputs / EXPERIMENT_LEDGER).write_text(
            json.dumps(
                {
                    "alpha_budget": {"per_week": 6, "declared_on": "2026-09-01"},
                    "hypotheses": [
                        {
                            "search": "fixture",
                            "name": f"hypothesis {i}",
                            "tested_on": "2026-09-01",
                            "seasons": [2027],
                            "outcome": "",
                            "predicted_direction": "higher",
                            "stage": "discovery",
                        }
                        for i in range(hypotheses)
                    ],
                }
            ),
            encoding="utf-8",
        )
        return self

    def run(self, *argv: str) -> tuple[int, str]:
        saved = sys.argv[:]
        sys.argv = [
            str(SCRIPT),
            "--processed-dir",
            str(self.processed),
            "--output-dir",
            str(self.outputs),
            *argv,
        ]
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                runpy.run_path(str(SCRIPT), run_name="__main__")
            return 0, buffer.getvalue()
        except SystemExit as exit_code:
            return int(exit_code.code or 0), buffer.getvalue()
        finally:
            sys.argv = saved

    def record(self) -> dict:
        return json.loads(self.record_path.read_text(encoding="utf-8"))

    def report(self) -> str:
        return self.report_path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def scored(tmp_path_factory):
    """One full run, kept for the module because it fits a real regression."""
    lab = Lab(tmp_path_factory.mktemp("forecast_skill")).with_ledger()
    lab.with_experiment_ledger(24)
    exit_code, output = lab.run()
    return lab, exit_code, output


# ---------------------------------------------------------------------------
# Nothing to measure is an exit code, never an empty report
# ---------------------------------------------------------------------------


def test_a_ledger_that_does_not_exist_yet_is_a_message_and_an_exit_code(tmp_path):
    """Forward evidence cannot be back-dated, so an absent ledger is normal.

    It is not a null result. *"An empty table reads as a null result and a null
    result is a claim."*
    """
    lab = Lab(tmp_path)
    exit_code, output = lab.run()

    assert exit_code != 0, "a lab with nothing to measure must not report success"
    assert "does not exist" in output
    assert "run_forward_evidence.py" in output
    assert not lab.record_path.exists(), "nothing is written when nothing was fitted"
    assert not lab.report_path.exists()


def test_a_ledger_that_exists_and_holds_no_rows_is_refused(tmp_path):
    """A ledger created and never appended to is not a model that never
    disagrees with the market. The two look identical in a report."""
    lab = Lab(tmp_path).with_ledger(
        pd.DataFrame(columns=list(LEDGER_COLUMNS))
    )
    exit_code, output = lab.run()
    assert exit_code != 0
    assert "holds no rows" in output
    assert not lab.record_path.exists()


def test_a_ledger_missing_a_column_is_refused_rather_than_padded(tmp_path):
    """`stores.read_store` pads absent columns with NA when it is not appending.

    That is right for a defensive read and wrong here: a padded frame would fit
    a regression over a column of NaNs and report *not enough evidence*, which
    is a finding. The football lab's backtest read a missing settlement column
    as a zero, reported zero bets, and had that read as "the model never
    disagrees enough with the market".
    """
    lab = Lab(tmp_path).with_ledger(
        settled_ledger(games=20).drop(columns=["model_probability"])
    )
    exit_code, output = lab.run()
    assert exit_code != 0
    assert "model_probability" in output
    assert not lab.record_path.exists()


def test_a_model_that_never_disagrees_is_not_identified_and_writes_nothing(tmp_path):
    """Undefined is not zero, and the difference is wiring against finding.

    A disagreement column that never varies has no coefficient. Publishing
    `0.000` there would publish "the model adds nothing" when what actually
    happened is that the model was never asked, or was asked and handed back the
    price. It gets its own exit code so a caller can tell it apart from a ledger
    that is not there yet.
    """
    lab = Lab(tmp_path).with_ledger(kind="agrees")
    exit_code, output = lab.run()

    assert exit_code == 3, output
    assert "not identified" in output
    assert "undefined rather than zero" in output
    assert not lab.record_path.exists()
    assert not lab.report_path.exists()


# ---------------------------------------------------------------------------
# A real run
# ---------------------------------------------------------------------------


def test_the_run_writes_a_record_and_a_report_and_exits_zero(scored):
    lab, exit_code, output = scored
    assert exit_code == 0, output
    assert lab.record_path.is_file() and lab.report_path.is_file()
    record = lab.record()
    assert record["record_version"] == FS.RECORD_VERSION
    assert record["competition"] == CBB.key
    assert record["devig_method"] == FS.DEVIG_METHOD
    assert record["pair_scope"] == "book"
    assert record["population_census"]["scored"] == GAMES * RUNGS * 2
    assert record["devig_census"]["reconciles"] is True
    assert record["population_census"]["reconciles"] is True


def test_the_snapshot_date_becomes_the_slate_date(scored):
    """The ledger files its day under `snapshot_date`; the day cluster needs it.

    Without the rename every row would share one missing slate date, the day
    cluster would be a single cluster, and the two-way "wider wins" rule would
    silently have only one unit to choose from.
    """
    lab, _, _ = scored
    record = lab.record()
    assert record["pooled"]["days"] == DAYS
    assert record["pooled"]["games"] == GAMES
    fitted = record["pooled"]["fit"]
    assert fitted["days"] == DAYS and fitted["games"] == GAMES


def test_the_disagreement_coefficient_is_printed_before_anything_else(scored):
    """The order a reader forms a belief in is the order the numbers arrive in.

    The market coefficient of 0.97 is the reassuring one and the disagreement
    coefficient of 0.03 is the answer; printing them the other way round is how
    a reader leaves with the wrong one.
    """
    _, _, output = scored
    first = output.index("THE COEFFICIENT ON THE DISAGREEMENT")
    assert first < output.index("THE MARKET COEFFICIENT")
    assert first < output.index("BRIER, MODEL AGAINST MARKET")
    assert first < output.index("CLAIMED EDGE AGAINST WHAT HAPPENED")
    assert "THE WHOLE ANSWER" in output
    assert "market 0.97" not in output or "0.03" in output


def test_the_pooled_line_never_appears_without_its_tier_lines(scored):
    """A pooled Division I figure is only ever printed beside its tiers."""
    _, _, output = scored
    pooled = output.index("pooled (never the headline")
    for tier in (Tier.HIGH_MAJOR.value, Tier.LOW_MAJOR.value):
        assert output.index(f"  {tier}: ") < pooled, tier
    assert "three tiers are three" in output


def test_the_report_puts_every_tier_before_the_pooled_section(scored):
    lab, _, _ = scored
    report = lab.report()
    assert report.index("## Per conference tier") < report.index("## Pooled")
    for tier in (Tier.HIGH_MAJOR.value, Tier.LOW_MAJOR.value):
        assert f"### {tier}" in report
    assert "This is never the headline" in report


def test_every_printed_coefficient_carries_its_sample_size(scored):
    """A number without a sample size is not a result."""
    lab, _, output = scored
    assert "wagers across" in output
    for line in output.splitlines():
        if " wagers across " in line:
            assert " over " in line, line
    for row in FS.pooled_fit_of(lab.record())["coefficients"]:
        assert row["rows"] > 0 and row["clusters"] > 0, row


def test_the_census_is_printed_and_reconciles(scored):
    _, _, output = scored
    assert "wagers supplied" in output
    assert "de-vigged" in output
    assert "reconciles                     yes" in output
    assert "scorable (won or lost)" in output


def test_a_push_is_excluded_from_the_regression_and_named_in_the_census(tmp_path):
    """A push is not half a win, and a denominator that quietly includes one
    measures a different quantity from the one it names.

    It is also never *dropped*: the census names it, on stdout and in the
    report, so a reader can see the difference between the population and the
    board."""
    ledger = settled_ledger(games=60)
    pushed = ledger.index[:40]
    ledger.loc[pushed, "outcome"] = "push"
    ledger.loc[pushed, "profit_units"] = 0.0
    lab = Lab(tmp_path).with_ledger(ledger).with_experiment_ledger(2)

    exit_code, output = lab.run()
    assert exit_code == 0, output
    assert "pushed — a push is not half a win" in output
    record = lab.record()
    assert record["population_census"]["push"] == 40
    assert record["population_census"]["scored"] == len(ledger) - 40
    assert record["population_census"]["reconciles"] is True
    assert "A push is not half a win" in lab.report()


def test_the_family_correction_reads_the_experiment_ledgers_cumulative_count(scored):
    """Never the day's count. *A search that runs every week is not twelve
    tests. It is twelve tests a week, forever.*"""
    lab, _, output = scored
    record = lab.record()
    assert record["looks"] == 24
    assert record["correction_factor"] > 1.0
    assert "24 cumulative hypotheses" in output
    assert "never the day's" in output
    assert "**Family correction: 24 cumulative hypotheses**" in lab.report()


def test_a_missing_experiment_ledger_warns_rather_than_correcting_silently(tmp_path):
    """One look is a lab that has tested nothing, which is not what this one is."""
    lab = Lab(tmp_path).with_ledger(games=40)
    exit_code, output = lab.run()
    assert exit_code == 0, output
    assert "::warning::" in output
    assert "tested nothing" in output
    assert lab.record()["looks"] == 1


# ---------------------------------------------------------------------------
# Re-rendering
# ---------------------------------------------------------------------------


def test_rebuild_report_only_re_renders_byte_identically_and_fits_nothing(scored):
    """Improving a sentence must never cost a re-run — and it must not be able
    to change the numbers, either."""
    lab, _, _ = scored
    before = lab.report()
    record_before = lab.record()

    lab.report_path.write_text("hand-edited nonsense\n", encoding="utf-8")
    exit_code, output = lab.run("--rebuild-report-only")

    assert exit_code == 0, output
    assert lab.report() == before, "the re-render must be byte identical"
    assert lab.record() == record_before, "re-rendering must not touch the record"
    assert "Nothing was re-fitted" in output
    assert "no credit was spent" in output


def test_rebuild_report_only_without_a_record_is_a_message_and_an_exit_code(tmp_path):
    lab = Lab(tmp_path)
    exit_code, output = lab.run("--rebuild-report-only")
    assert exit_code != 0
    assert "no record to re-render" in output
    assert not lab.report_path.exists()


# ---------------------------------------------------------------------------
# It spends nothing and opens nothing
# ---------------------------------------------------------------------------


def test_the_run_opens_no_socket(tmp_path, monkeypatch):
    """This reads what the freeze-and-settle organ already wrote. It cannot
    spend a credit, and a socket opened here would be a surprise rather than a
    cost."""

    def refuse(*args, **kwargs):
        raise AssertionError("run_forecast_skill.py opened a socket")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)

    lab = Lab(tmp_path).with_ledger(games=40).with_experiment_ledger(3)
    exit_code, output = lab.run()
    assert exit_code == 0, output
    assert lab.record_path.is_file()


def test_the_script_names_no_spending_flag():
    """One flag name across every entry point that can spend, and this one
    cannot spend at all — so it must not look like it could."""
    text = SCRIPT.read_text(encoding="utf-8")
    for wrong in ('"--real"', '"--go"', '"--execute"', '"--spend"', '"--live"'):
        assert wrong not in text, f"{SCRIPT.name} declares {wrong}"


def test_the_forward_ledger_carries_no_selected_flag_and_the_run_says_so(scored):
    """Over the forward ledger the selected subset is not supplied, in words."""
    lab, exit_code, output = scored
    assert exit_code == 0, output
    record = lab.record()
    assert record["selected"]["available"] is False
    assert "TWO POPULATIONS" in output
    assert f"{FS.SELECTED_LABEL}: not supplied" in output
    assert "THE THRESHOLD-SELECTED BETS, BESIDE IT" not in output
    assert f"Population of every line above: {FS.ALL_OPINIONS_LABEL}" in output


def test_a_graded_frame_with_the_flag_prints_the_selected_subset_beside_the_whole(tmp_path):
    """The backtest's export carries `selected`; the run then reports both populations.

    The whole is printed first and named the skill measure; the subset after,
    named the winner's-curse comparison, with its own smaller count.
    """
    from cbb_betting_lab.reports import price_backtest as PB

    frame = settled_ledger().rename(columns={"snapshot_date": "slate_date"})
    edged = PB.add_edge(frame)
    frame[FS.SELECTED_COLUMN] = PB.bet_mask(edged).to_numpy()
    assert 0 < int(frame[FS.SELECTED_COLUMN].sum()) < len(frame)
    graded_path = tmp_path / "graded.csv"
    frame.to_csv(graded_path, index=False)

    lab = Lab(tmp_path).with_experiment_ledger(24)
    exit_code, output = lab.run("--graded", str(graded_path))
    assert exit_code == 0, output
    record = lab.record()

    whole = record["populations"]["all_opinions"]
    subset = record["populations"]["selected"]
    assert subset["available"] is True
    assert 0 < subset["rows"] < whole["rows"]
    assert whole["rows"] == record["pooled"]["rows"]
    assert f"{FS.ALL_OPINIONS_LABEL}: {whole['rows']:,} scorable wagers" in output
    assert f"{FS.SELECTED_LABEL}: {subset['rows']:,} scorable wagers" in output
    assert "THE THRESHOLD-SELECTED BETS, BESIDE IT" in output
    # The skill measure is printed before the comparison, every time.
    assert output.index("THE COEFFICIENT ON THE DISAGREEMENT") < output.index(
        "THE THRESHOLD-SELECTED BETS, BESIDE IT"
    )
    assert f"— {FS.SELECTED_ROLE}" in output or FS.SELECTED_ROLE.upper() in output
    report = lab.report()
    assert "## The threshold-selected bets, beside it" in report
    assert f"{subset['rows']:,} of {whole['rows']:,} scorable wagers" in report


def test_the_frame_builders_census_is_read_beside_the_frame_and_stated(tmp_path):
    """The frame is a subset of the graded set, and the run has to say by how much.

    `scripts/build_skill_frame.py` excludes every graded wager whose own book
    hung one side only and writes `<frame>__unpairable.json` beside the frame.
    Nothing in the frame itself records the exclusion, so without reading that
    file this script would print the frame's length as the graded population
    and be wrong by however many rows were dropped — silently, which is the
    one thing the old blanket refusal was right about.
    """
    from cbb_betting_lab.reports import price_backtest as PB

    frame = settled_ledger().rename(columns={"snapshot_date": "slate_date"})
    edged = PB.add_edge(frame)
    frame[FS.SELECTED_COLUMN] = PB.bet_mask(edged).to_numpy()
    graded_path = tmp_path / "cbb_skill_frame.csv"
    frame.to_csv(graded_path, index=False)
    (tmp_path / "cbb_skill_frame__unpairable.json").write_text(
        json.dumps(
            {
                "supplied": len(frame) + 2,
                "paired": len(frame),
                "unpairable": 2,
                "unpairable_selected": 1,
                "share": 2 / (len(frame) + 2),
                "reconciles": True,
                "reason": "their own book hung only one side of the wager",
                "by_market": {"team_total": 1, "alternate_spread": 1},
                "by_book": {"draftkings": 1, "betmgm": 1},
            }
        ),
        encoding="utf-8",
    )

    lab = Lab(tmp_path).with_experiment_ledger(24)
    exit_code, output = lab.run("--graded", str(graded_path))
    assert exit_code == 0, output

    excluded = lab.record()["populations"]["excluded_unpairable"]
    assert excluded["available"] is True
    assert excluded["rows"] == 2
    assert excluded["supplied"] == len(frame) + 2
    assert excluded["reconciles"] is True
    # Stated on stdout, in the section that states the populations.
    assert "TWO POPULATIONS" in output
    assert f"{FS.UNPAIRABLE_LABEL}: 2 of {len(frame) + 2:,} graded wagers" in output
    assert "counts of the subset that remained" in output
    assert output.index("TWO POPULATIONS") < output.index(FS.UNPAIRABLE_LABEL)
    # And in the written report.
    assert "2 graded wager(s) are in neither population above" in lab.report()


def test_a_frame_with_no_census_beside_it_says_not_supplied_never_none(tmp_path):
    """Absent is not zero, and a run must not turn one into the other.

    The forward ledger has no frame-builder and no census. Printing "none
    excluded" for it would state a quantity nobody counted, which is exactly
    the residual-arithmetic error the price backtest's accounting identity was
    rewritten to stop making.
    """
    lab = Lab(tmp_path).with_ledger().with_experiment_ledger(24)
    exit_code, output = lab.run()
    assert exit_code == 0, output
    assert lab.record()["populations"]["excluded_unpairable"]["available"] is False
    assert f"{FS.UNPAIRABLE_LABEL}: not supplied" in output
    assert "unknown rather than yes" in output
    assert FS.UNPAIRABLE_NOT_SUPPLIED in lab.report()


def test_a_bucket_is_named_the_same_way_on_stdout_as_in_the_report(scored):
    """One name per row. `-inf% to -10%` on a console and `below -10%` in a
    report is two names for one bucket, and a reader comparing them is
    comparing two tables that are not the same table."""
    lab, _, output = scored
    report = lab.report()
    assert "inf" not in output, "no bucket may be printed with an infinity in it"
    for bucket in lab.record()["pooled"]["buckets"]:
        if not bucket["rows"]:
            continue
        label = FS.bucket_label(bucket["low"], bucket["high"])
        assert f"claimed {label}:" in output or not bucket["enough"], label
        assert f"| {label} |" in report, label


# ---------------------------------------------------------------------------
# The realised-return line: reached by a real run, and both of its branches
# ---------------------------------------------------------------------------

#: How many hypotheses the fixture ledger declares, and therefore how many looks
#: the family-wise correction is taken over. Named so the assertions below read
#: the same number the run corrects by.
ANTI_LOOKS = 24

#: Enough games that two claimed-edge buckets clear `stats.MINIMUM_BETS` at the
#: **ends** of the range. At 120 games only the two lowest buckets cleared it,
#: the comparison ran between them, the return did not fall across those two,
#: and the line under test was never printed — which is exactly how it went
#: untested.
ANTI_GAMES = 400


def script_namespace() -> dict:
    """The script's module namespace, without running `main`.

    `runpy.run_path` under any `run_name` but `__main__` executes the module
    and stops at the `if __name__ == "__main__"` guard, which is how a printing
    helper gets called directly with a record built to reach one branch.
    """
    return runpy.run_path(str(SCRIPT), run_name="run_forecast_skill_under_test")


def test_the_realised_return_line_is_reached_by_a_real_run_and_carries_its_verdict(
    tmp_path,
):
    """The anti-predictive return line, printed by the script, end to end.

    Added 2026-09-05: the line existed and no test executed it. The end-to-end
    fixture is `kind="noise"`, whose realised return does not fall across the
    claimed-edge buckets, so the branch was never entered — a console line that
    could have printed anything at all.

    What it must print, for each of the two buckets it compares: the point
    estimate, the settled bet count, the clustering that produced the interval,
    the raw 95% interval, the **family-corrected** interval labelled apart from
    it with the look count it was corrected over, and the verdict in the
    reserved words. An interval printed without its verdict is a verdict the
    reader supplies.
    """
    lab = Lab(tmp_path).with_ledger(kind="anti", games=ANTI_GAMES)
    lab.with_experiment_ledger(ANTI_LOOKS)
    exit_code, output = lab.run()
    assert exit_code == 0, output

    lines = [line for line in output.splitlines() if "realised return" in line]
    assert lines, (
        "the anti-predictive return line was not reached by this run; the "
        "branch prints only when the return falls across the claimed-edge "
        f"buckets, so the fixture must produce that shape. Output:\n{output}"
    )

    pooled = lab.record()["pooled"]["anti_predictive_return"]
    assert pooled["measurable"] and pooled["falls_at_the_top"], pooled
    assert pooled["looks"] == ANTI_LOOKS, (
        "the correction must come from the experiment ledger's cumulative "
        f"count, not from the day's; got {pooled}"
    )

    verdicts = {
        S.NO_DEMONSTRATED_EDGE,
        S.DEMONSTRATED_EDGE,
        S.DEMONSTRATED_DEFICIT,
    }
    for line in lines:
        assert line.count("settled wagers across") == 2, line
        assert line.count("95% interval [") == 2, (
            f"both buckets must print the raw interval; got {line}"
        )
        assert line.count("family-corrected [") == 2, (
            "both buckets must print the family-corrected interval beside the "
            f"raw one; got {line}"
        )
        assert line.count(f"across {ANTI_LOOKS:,} looks") == 3, (
            "each bucket's correction and the comparison itself must say how "
            f"many looks it was taken over; got {line}"
        )
        # Anchored on the em dash that closes each interval, because
        # `no demonstrated edge` contains `demonstrated edge` and a bare
        # substring count would call one verdict two.
        assert sum(line.count(f"looks — {word}") for word in verdicts) == 2, (
            "every printed interval carries its verdict in the reserved "
            f"words; got {line}"
        )
        assert "the family-corrected intervals" in line, (
            f"the comparison must say which intervals it read; got {line}"
        )

    # The corrected interval is genuinely wider than the raw one, so the two
    # printed pairs are two numbers and not the same number twice.
    for end in ("lowest_bucket", "highest_bucket"):
        bucket = pooled[end]
        assert bucket["roi_adjusted_low"] < bucket["roi_low"], bucket
        assert bucket["roi_adjusted_high"] > bucket["roi_high"], bucket
        assert bucket["verdict"], bucket


def test_the_realised_return_line_claims_a_fall_only_on_disjoint_corrected_intervals():
    """Both branches of the line, on the same shape with only the intervals moved.

    The real run above lands in the *not demonstrated* branch, which is the
    honest answer on that data and leaves the other branch unexecuted. These two
    records differ only in the corrected bounds, so the sentence the line is
    permitted to print is the only thing that can change.
    """
    printer = script_namespace()["print_buckets"]

    def record(*, adjusted_high: float) -> dict:
        def bucket(low, high, roi, ci, adjusted):
            return {
                "low": low,
                "high": high,
                "rows": 400,
                "roi": roi,
                "roi_low": ci[0],
                "roi_high": ci[1],
                "roi_adjusted_low": adjusted[0],
                "roi_adjusted_high": adjusted[1],
                "looks": 12,
                "bets": 400,
                "clusters": 90,
                "cluster_unit": "day",
                "verdict": S.NO_DEMONSTRATED_EDGE,
            }

        return {
            "by_tier": [],
            "pooled": {
                "label": "all",
                "buckets": [
                    {
                        "low": 0.0,
                        "high": 0.02,
                        "rows": 400,
                        "games": 90,
                        "enough": True,
                        "model_implied": 0.5,
                        "market_implied": 0.5,
                        "realised": 0.5,
                        "wilson_low": 0.45,
                        "wilson_high": 0.55,
                        "gap_to_model": 0.0,
                    }
                ],
                "anti_predictive_return": {
                    "measurable": True,
                    "falls_at_the_top": True,
                    "return_falls_by": 0.15,
                    "looks": 12,
                    "demonstrated": adjusted_high < -0.02,
                    "demonstrated_before_correction": True,
                    "lowest_bucket": bucket(
                        0.0, 0.02, 0.06, (0.02, 0.10), (-0.02, 0.14)
                    ),
                    "highest_bucket": bucket(
                        0.20, float("inf"), -0.09, (-0.14, -0.04),
                        (-0.20, adjusted_high),
                    ),
                },
            },
        }

    demonstrated = io.StringIO()
    with contextlib.redirect_stdout(demonstrated):
        printer(record(adjusted_high=-0.05))
    shown = demonstrated.getvalue()
    assert "! realised return" in shown, shown
    assert "the family-corrected intervals do not overlap across 12 looks" in shown
    assert "raising the threshold is the wrong response" in shown
    assert shown.count(S.NO_DEMONSTRATED_EDGE) == 2, shown

    overlapping = io.StringIO()
    with contextlib.redirect_stdout(overlapping):
        printer(record(adjusted_high=0.02))
    hedged = overlapping.getvalue()
    assert ". realised return" in hedged, hedged
    assert "the family-corrected intervals overlap across 12 looks" in hedged
    assert "the fall is not demonstrated" in hedged
    assert "raising the threshold is the wrong response" not in hedged
    assert hedged.count(S.NO_DEMONSTRATED_EDGE) == 2, hedged
