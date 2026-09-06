"""A number that paid no family correction may not become a finding.

The player-prop design of 2026-09-05 registered 33 hypotheses and named seven
more quantities that the run will compute and print and may **never** report as
a finding: the over/under split inside a cell, calibration by |z| bucket,
`mean(actual)/mean(mu)`, the refusal census, the minutes-projection fit, the
half-life robustness row, and the unapplied diagnostic columns.

Exempting them is right. None is a claim about edge, and charging the
Bonferroni correction for seven descriptions would have widened every real
interval in this lab in exchange for no protection at all.

Exempting them is also exactly the shape of the move this ledger exists to
stop, run backwards. A diagnostic that came out well is precisely the number
somebody later wants to quote as a result — and it paid nothing, so quoting it
reads an uncounted look as a finding, with a correction that was computed as
though the look never happened. The design document said these "may not be
promoted after the fact". This file is the difference between that sentence and
a gate.

Three layers, and each is exercised here rather than described:

1. `ExperimentLedger.record()` raises `PromotionRefused` in process;
2. `save()` refuses to drop a declaration, because deleting the declaration is
   how the refusal in (1) would be got around;
3. `scripts/check_ledger_append_only.py` sees both at the diff, which is the
   only layer that reaches a ledger edited on disk and committed.

The tracked ledger is checked too: the seven declarations are on disk, none of
them is also a hypothesis, and the correction is computed over the hypotheses
alone.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from cbb_betting_lab import experiment_ledger as E

_REPO = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO / "scripts" / "check_ledger_append_only.py"
_spec = importlib.util.spec_from_file_location("check_ledger_append_only", _SCRIPT)
assert _spec and _spec.loader
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)

_RECORDER_PATH = _REPO / "scripts" / "record_experiments.py"
_rspec = importlib.util.spec_from_file_location("record_experiments", _RECORDER_PATH)
assert _rspec and _rspec.loader
recorder = importlib.util.module_from_spec(_rspec)
_rspec.loader.exec_module(recorder)

TRACKED = _REPO / "data" / "outputs" / "experiment_ledger.json"


def _declaration(name: str = "calibration by |z| bucket") -> E.DescriptiveOnly:
    return E.DescriptiveOnly(
        search="player_props_diagnostics",
        name=name,
        declared_on="2026-09-05",
        rationale="It is the edge statistic; gating on it makes calibration true by construction.",
    )


def _hypothesis(search: str, name: str) -> E.Hypothesis:
    return E.Hypothesis(
        search=search, name=name, tested_on="2026-10-01", seasons=(2024,),
        outcome="pending", predicted_direction="lower", stage="discovery",
    )


def _write(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_record_refuses_to_promote_a_declared_quantity() -> None:
    ledger = E.ExperimentLedger()
    ledger.declare(_declaration())
    with pytest.raises(E.PromotionRefused, match="descriptive-only"):
        ledger.record(_hypothesis("player_props_diagnostics", "calibration by |z| bucket"))
    assert ledger.count == 0


def test_the_refusal_ignores_seasons_and_stage() -> None:
    """The declaration key is (search, name) and nothing else.

    A hypothesis key carries seasons and stage, so keying the refusal on it
    would let the same quantity through under one different season — which is
    not a different test of anything, it is the same diagnostic wearing a year.
    """
    ledger = E.ExperimentLedger()
    ledger.declare(_declaration())
    for seasons, stage, direction in (((2025,), "discovery", "higher"), ((2024, 2025), "holdout", "either")):
        with pytest.raises(E.PromotionRefused):
            ledger.record(
                E.Hypothesis(
                    search="player_props_diagnostics",
                    name="calibration by |z| bucket",
                    tested_on="2026-10-01", seasons=seasons, outcome="pending",
                    predicted_direction=direction, stage=stage,
                )
            )


def test_declaring_something_already_tested_is_refused_too() -> None:
    """The other direction, which narrows rather than widens.

    Reclassifying a hypothesis as a description takes a counted look back out
    of the family, so every interval already quoted against that family becomes
    retroactively too narrow. It is the ledger shrinking by another route.
    """
    ledger = E.ExperimentLedger()
    ledger.record(_hypothesis("player_props_diagnostics", "calibration by |z| bucket"))
    with pytest.raises(E.PromotionRefused, match="already"):
        ledger.declare(_declaration())
    assert ledger.count == 1


def test_declarations_do_not_widen_the_correction(tmp_path: Path) -> None:
    """The whole reason the exemption exists, asserted rather than assumed."""
    ledger = E.ExperimentLedger(hypotheses=[_hypothesis("s", f"h{i}") for i in range(20)])
    before = ledger.correction_factor()
    ledger.declare(*(_declaration(f"diagnostic {i}") for i in range(7)))
    assert ledger.count == 20
    assert ledger.correction_factor() == before


def test_declarations_survive_a_save_and_load_round_trip(tmp_path: Path) -> None:
    ledger = E.ExperimentLedger(hypotheses=[_hypothesis("s", "h")])
    ledger.declare(_declaration())
    path = tmp_path / E.LEDGER_FILENAME
    E.save(ledger, path, floor=0)
    reloaded = E.load(path)
    assert reloaded.descriptive_only == ledger.descriptive_only
    with pytest.raises(E.PromotionRefused):
        reloaded.record(_hypothesis("player_props_diagnostics", "calibration by |z| bucket"))


def test_save_refuses_to_drop_a_declaration(tmp_path: Path) -> None:
    """Deleting the declaration is how the in-process refusal is got around."""
    ledger = E.ExperimentLedger(hypotheses=[_hypothesis("s", "h")])
    ledger.declare(_declaration(), _declaration("the refusal census"))
    path = tmp_path / E.LEDGER_FILENAME
    E.save(ledger, path, floor=0)

    cut = E.load(path)
    del cut.descriptive_only[1:]
    with pytest.raises(ValueError, match="descriptive-only declarations would fall from 2"):
        E.save(cut, path, floor=len(cut.hypotheses))


def test_a_ledger_written_before_the_field_existed_reads_as_declaring_nothing(tmp_path: Path) -> None:
    """Absent is empty. Present and malformed is an error, never empty."""
    path = _write(tmp_path / E.LEDGER_FILENAME, {"hypotheses": []})
    assert E.load(path).descriptive_only == []
    assert check.read_descriptive({"hypotheses": []}, path, "head") == []
    with pytest.raises(check.LedgerError, match="not a list"):
        check.read_descriptive({"descriptive_only": {}}, path, "head")
    with pytest.raises(check.LedgerError, match="missing 'rationale'"):
        check.read_descriptive(
            {"descriptive_only": [{"search": "s", "name": "n", "declared_on": "d"}]},
            path, "head",
        )


def _base_and_head(tmp_path: Path) -> tuple[Path, dict]:
    payload = {
        "hypotheses": [
            {"search": "s", "name": "h", "tested_on": "2026-09-05", "seasons": [2024],
             "outcome": "pending", "predicted_direction": "lower", "stage": "discovery",
             "realised_direction": ""}
        ],
        "descriptive_only": [
            {"search": "player_props_diagnostics", "name": "calibration by |z| bucket",
             "declared_on": "2026-09-05", "rationale": "It is the edge statistic."}
        ],
    }
    base = _write(tmp_path / "base.json", payload)
    return base, json.loads(json.dumps(payload))


def test_the_diff_guard_passes_an_untouched_pair(tmp_path: Path) -> None:
    base, head = _base_and_head(tmp_path)
    assert check.main(["--base", str(base), "--head", str(_write(tmp_path / "head.json", head))]) == 0


def test_the_diff_guard_refuses_a_removed_declaration(tmp_path: Path, capsys) -> None:
    base, head = _base_and_head(tmp_path)
    head["descriptive_only"] = []
    assert check.main(["--base", str(base), "--head", str(_write(tmp_path / "head.json", head))]) == 1
    assert "a descriptive-only declaration was removed" in capsys.readouterr().err


def test_the_diff_guard_refuses_a_rewritten_rationale(tmp_path: Path, capsys) -> None:
    """A rationale is the reason a later reader can see the promotion is wrong.

    Rewrite it to something that sounds like a hypothesis and the declaration
    is still there while the argument against reading it as one is gone.
    """
    base, head = _base_and_head(tmp_path)
    head["descriptive_only"][0]["rationale"] = "Actually this is a fine thing to report."
    assert check.main(["--base", str(base), "--head", str(_write(tmp_path / "head.json", head))]) == 1
    assert "a descriptive-only declaration was rewritten" in capsys.readouterr().err


def test_the_diff_guard_refuses_the_promotion_itself(tmp_path: Path, capsys) -> None:
    base, head = _base_and_head(tmp_path)
    head["hypotheses"].append({
        "search": "player_props_diagnostics", "name": "calibration by |z| bucket",
        "tested_on": "2026-10-01", "seasons": [2024], "outcome": "pending",
        "predicted_direction": "higher", "stage": "discovery", "realised_direction": "",
    })
    assert check.main(["--base", str(base), "--head", str(_write(tmp_path / "head.json", head))]) == 1
    assert "promoted from descriptive-only to a hypothesis" in capsys.readouterr().err


def test_the_diff_guard_refuses_the_two_edits_together(tmp_path: Path, capsys) -> None:
    """The actual attack: delete the declaration AND register the hypothesis.

    Either edit alone is caught by an obvious rule. Doing both in one commit is
    what somebody would really do, because after the deletion the head ledger
    holds no declaration to contradict the new entry — so the promotion check
    reads the BASE's declarations as well as the head's.
    """
    base, head = _base_and_head(tmp_path)
    head["descriptive_only"] = []
    head["hypotheses"].append({
        "search": "player_props_diagnostics", "name": "calibration by |z| bucket",
        "tested_on": "2026-10-01", "seasons": [2024], "outcome": "pending",
        "predicted_direction": "higher", "stage": "discovery", "realised_direction": "",
    })
    assert check.main(["--base", str(base), "--head", str(_write(tmp_path / "head.json", head))]) == 1
    err = capsys.readouterr().err
    assert "a descriptive-only declaration was removed" in err
    assert "promoted from descriptive-only to a hypothesis" in err


def test_the_tracked_ledger_carries_the_seven_declarations() -> None:
    """On disk, not only in the recorder's constant."""
    payload = json.loads(TRACKED.read_text(encoding="utf-8"))
    declared = payload["descriptive_only"]
    assert len(declared) == len(recorder.DESCRIPTIVE_ONLY) == 7
    assert {(d["search"], d["name"]) for d in declared} == {
        (d.search, d.name) for d in recorder.DESCRIPTIVE_ONLY
    }
    assert all(d["rationale"].strip() for d in declared), (
        "a declaration with no stated reason is an exemption nobody has to justify"
    )
    names = {(h["search"], h["name"]) for h in payload["hypotheses"]}
    assert not names & {(d["search"], d["name"]) for d in declared}


def test_the_correction_is_computed_over_the_hypotheses_alone() -> None:
    ledger = E.load(TRACKED)
    assert ledger.count == len(ledger.hypotheses) == 95
    assert len(ledger.descriptive_only) == 7
    assert round(ledger.correction_factor(), 4) == 1.7689


def test_the_render_escapes_a_pipe_so_the_table_does_not_split() -> None:
    """`calibration by |z| bucket` is a real declared name, pipes and all.

    |z| is the edge statistic and naming it any other way would be a
    euphemism, so the render escapes rather than the declaration renaming
    itself. Unescaped, the pipes ended the cell and the rendered table put a
    different rationale beside a different quantity — a record that reads
    cleanly and says something nobody wrote.
    """
    ledger = E.ExperimentLedger(hypotheses=[_hypothesis("s", "h")])
    ledger.declare(_declaration())
    rendered = E.render(ledger)
    row = next(line for line in rendered.splitlines() if "calibration by" in line)
    assert r"calibration by \|z\| bucket" in row
    unescaped = row.count("|") - row.count(r"\|")
    assert unescaped == 5, (
        f"the declaration row has {unescaped} unescaped pipes; a four-column "
        "markdown row has exactly five"
    )
    tracked = (
        _REPO / "data" / "outputs" / "cbb_experiment_ledger.md"
    ).read_text(encoding="utf-8")
    assert r"calibration by \|z\| bucket" in tracked
