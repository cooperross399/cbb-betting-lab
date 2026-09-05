"""The append-only gate, exercised without pushing a PR.

`.github/workflows/ledger-guard.yml` is where
`scripts/check_ledger_append_only.py` runs for real, and a workflow is tested
by merging it, so the comparison lives in a script and the script's failures
live here. The workflow's own resolve step — including a branch's first push,
where the all-zeros `before` names no commit — is driven under stubs in
`tests/test_workflows.py`.

An earlier version of this docstring said the removal case had been reproduced
as "twelve of thirty hypotheses deleted, the recorder re-run, x1.60 became
x1.46, the suite stayed green". Re-measured on 2026-09-04, none of that
happens: the old `save()` re-read raises on an in-process shrink, the recorder
re-adds every hypothesis and prints x1.60 again, and x1.46 is the correction
at twelve entries rather than at the eighteen twelve deletions leave (x1.53).
`test_the_old_re_read_fired_on_an_in_process_shrink_and_missed_the_committed_one`
and `test_the_recorder_self_heals_a_ledger_that_was_cut_on_disk` run each of
those, so the corrected sentence has a test behind it. The edit that DOES get
past every runtime guard is one made on disk and committed, and that is the
edit this script's cases are about.

The tests that matter most are the equal-count ones. A gate that only counts
passes an edit that drops the failure and appends a replacement.

This lab pre-registers with `outcome="pending"` and writes the outcome back
after the measurement, so `pending -> measured` is the one permitted
transition; `measured -> anything` and `anything -> pending` are rewrites.
That is pinned from both sides below.

`test_known_gaps_that_still_get_through` is the other half of that honesty:
it runs the script over the edits it still passes and asserts the exit code
is 0, so what this gate does not cover is a recorded fact that goes red when
it changes.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_ledger_append_only.py"
_spec = importlib.util.spec_from_file_location("check_ledger_append_only", _SCRIPT)
assert _spec is not None and _spec.loader is not None
check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(check)

#: The recorder's own pre-registered constant, loaded rather than counted by
#: hand. The tracked ledger has grown past it — the replication appends its
#: holdout looks straight to the file — so "what the recorder can restore" and
#: "what the reports correct against" are two different numbers and neither may
#: be typed into a test.
_RECORDER = Path(__file__).resolve().parents[1] / "scripts" / "record_experiments.py"
_recorder_spec = importlib.util.spec_from_file_location("record_experiments", _RECORDER)
assert _recorder_spec is not None and _recorder_spec.loader is not None
_recorder = importlib.util.module_from_spec(_recorder_spec)
_recorder_spec.loader.exec_module(_recorder)

from cbb_betting_lab import experiment_ledger  # noqa: E402


def entry(
    name: str,
    *,
    search: str = "core_team_markets",
    seasons: tuple[int, ...] = (2025, 2026),
    tested_on: str = "2026-09-01",
    outcome: str = "pending",
    predicted_direction: str = "higher",
    stage: str = "discovery",
) -> dict:
    return {
        "search": search, "name": name, "tested_on": tested_on, "seasons": list(seasons),
        "outcome": outcome, "predicted_direction": predicted_direction, "stage": stage,
        "realised_direction": "",
    }


def write(path: Path, entries: list[dict]) -> Path:
    path.write_text(json.dumps({"hypotheses": entries}, indent=2) + "\n", encoding="utf-8")
    return path


def run(tmp_path: Path, base: list[dict] | None, head: list[dict]) -> int:
    head_path = write(tmp_path / "head.json", head)
    if base is None:
        return check.main(["--base-absent", "--head", str(head_path)])
    base_path = write(tmp_path / "base.json", base)
    return check.main(["--base", str(base_path), "--head", str(head_path)])


THREE = [entry("moneyline"), entry("spread"), entry("total_points")]
MEASURED = [entry("moneyline", outcome="no demonstrated edge"), entry("spread", outcome="no demonstrated edge"), entry("total_points", outcome="demonstrated deficit")]


def test_a_clean_append_passes(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    assert run(tmp_path, THREE, THREE + [entry("team_total")]) == 0
    assert "3 base hypotheses compared" in capsys.readouterr().out


def test_the_first_line_carries_the_count_beside_the_factor(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    run(tmp_path, THREE, THREE)
    first = capsys.readouterr().out.splitlines()[0]
    assert "3 distinct hypotheses" in first
    # The literal: three families at ALPHA = 0.05 give 1.2214...
    assert "x1.22" in first


def test_the_scripts_arithmetic_matches_the_package() -> None:
    assert check.ALPHA == experiment_ledger.ALPHA
    empty = experiment_ledger.ExperimentLedger()
    assert empty.count == 0
    for count in range(0, 201):
        assert check.correction_factor(count) == empty.correction_factor(extra=count), count


def test_the_scripts_key_matches_the_packages() -> None:
    """Stage is part of `Hypothesis.key()`, so it is part of this key too: a
    holdout look at a discovery hypothesis is a second look and must not
    collide with the first."""
    h = experiment_ledger.Hypothesis(search="s", name="n", tested_on="d", seasons=(2026,), outcome="pending", predicted_direction="higher", stage="holdout")
    assert check.key(entry("n", search="s", seasons=(2026,), stage="holdout")) == h.key()
    assert check.key(entry("n", search="s", seasons=(2026,), stage="holdout")) != check.key(entry("n", search="s", seasons=(2026,)))


def test_a_removal_fails_even_when_the_count_grew(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    head = THREE[:2] + [entry("team_total"), entry("alternate_spread")]
    assert run(tmp_path, THREE, head) == 1
    err = capsys.readouterr().err
    assert "removed from the ledger" in err and "total_points" in err


def test_a_count_decrease_fails(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    assert run(tmp_path, THREE, THREE[:2]) == 1
    assert "falls from 3 entries to 2" in capsys.readouterr().err


def test_the_reproduction_on_this_lab_is_caught(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """The audit's reproduction: the tracked ledger with twelve entries removed.

    The tracked ledger held 30 when this was first run and holds 62 since the
    replication of 2026-09-05 appended its 32 holdout looks, so the counts are
    read off the file rather than typed and only the SIZE of the edit — twelve
    entries deleted, which is what the audit reproduced — is fixed here.
    """
    tracked = _SCRIPT.parents[1] / "data" / "outputs" / "experiment_ledger.json"
    base = json.loads(tracked.read_text(encoding="utf-8"))["hypotheses"]
    assert len(base) == 62, (
        f"the tracked ledger holds {len(base)} entries, not 62; re-measure this "
        "reproduction against the file rather than editing the number"
    )
    head = base[:-12]
    assert run(tmp_path, base, head) == 1
    err = capsys.readouterr().err
    assert f"falls from {len(base)} entries to {len(head)}" in err
    assert err.count("removed from the ledger") == 12


def test_pending_may_be_filled_in_once(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """The lab's own design: pre-register pending, measure, write back."""
    assert run(tmp_path, THREE, MEASURED) == 0
    assert "no measured outcome rewritten" in capsys.readouterr().out


def test_a_measured_outcome_cannot_be_rewritten(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Same key, same count, a deficit turned into a finding."""
    head = list(MEASURED)
    head[2] = entry("total_points", outcome="+2.1% ROI, significant")
    assert run(tmp_path, MEASURED, head) == 1
    err = capsys.readouterr().err
    assert "rewritten in the ledger" in err and "'outcome'" in err and "'demonstrated deficit'" in err


def test_a_measured_outcome_cannot_become_pending_again(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """Un-measuring is a rewrite: it buys a second look at the same key."""
    head = list(MEASURED)
    head[2] = entry("total_points", outcome="pending")
    assert run(tmp_path, MEASURED, head) == 1
    assert "only 'pending' may be filled in" in capsys.readouterr().err


@pytest.mark.parametrize("field,value", [("tested_on", "2026-10-01"), ("predicted_direction", "lower")])
def test_re_dating_or_re_directing_a_hypothesis_fails(tmp_path: Path, capsys: pytest.CaptureFixture, field: str, value: str) -> None:
    """A re-dated test is an old look laundered into a fresh one; a
    re-directed one is a prediction rewritten after the number was seen."""
    head = [dict(e) for e in THREE]
    head[0][field] = value
    assert run(tmp_path, THREE, head) == 1
    err = capsys.readouterr().err
    assert "rewritten in the ledger" in err and f"'{field}'" in err


@pytest.mark.parametrize("rewritten_at", [0, 1, 2])
def test_a_duplicate_key_rewrite_fails(tmp_path: Path, capsys: pytest.CaptureFixture, rewritten_at: int) -> None:
    base = [entry("moneyline", outcome="no demonstrated edge")]
    copies = [entry("moneyline", outcome="no demonstrated edge") for _ in range(3)]
    copies[rewritten_at] = entry("moneyline", outcome="+2.1% ROI, significant")
    assert run(tmp_path, base, copies) == 1
    err = capsys.readouterr().err
    assert "rewritten in the ledger" in err


def test_duplicating_an_entry_verbatim_is_not_itself_a_rewrite(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    assert run(tmp_path, [entry("moneyline")], [entry("moneyline") for _ in range(3)]) == 0
    out = capsys.readouterr().out
    assert "1 distinct hypotheses in the head ledger (3 entries)" in out and "x1.00" in out


POISONED = [entry("spread", outcome="no demonstrated edge"), entry("spread", outcome="+2.1% ROI, significant")]


@pytest.mark.parametrize("order", [(0, 1), (1, 0)])
def test_a_contradictory_pair_cannot_land(tmp_path: Path, capsys: pytest.CaptureFixture, order: tuple[int, int]) -> None:
    head = [entry("moneyline")] + [POISONED[i] for i in order]
    assert run(tmp_path, [entry("moneyline")], head) == 1
    err = capsys.readouterr().err
    assert "the head ledger contradicts itself" in err
    assert "core_team_markets / spread (2025, 2026; discovery)" in err
    assert "head entry 1" in err and "head entry 2" in err


@pytest.mark.parametrize("survivor", [0, 1])
def test_an_inherited_contradiction_cannot_be_resolved_by_erasure(tmp_path: Path, capsys: pytest.CaptureFixture, survivor: int) -> None:
    base = [entry("moneyline")] + POISONED
    head = [entry("moneyline"), POISONED[survivor], dict(POISONED[survivor])]
    assert run(tmp_path, base, head) == 1
    err = capsys.readouterr().err
    assert "the base ledger contradicts itself" in err


def test_a_pending_and_a_measured_copy_under_one_key_is_a_contradiction(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """The transition happens in place; a ledger holding both states of one
    hypothesis is a ledger that cannot say which it recorded."""
    head = [entry("moneyline"), entry("moneyline", outcome="no demonstrated edge")]
    assert run(tmp_path, None, head) == 1
    assert "contradicts itself" in capsys.readouterr().err


def test_a_contradiction_is_refused_on_the_first_commit_path(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    assert run(tmp_path, None, [entry("moneyline")] + POISONED) == 1
    captured = capsys.readouterr()
    assert "the head ledger contradicts itself" in captured.err
    assert "first-commit state" not in captured.out


def test_known_gaps_that_still_get_through(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    """What this gate does NOT catch, asserted by running it. None is a
    waiver; they are the edges of the guarantee, and each goes red the day
    it closes so the sentence gets rewritten.

    1. Fields outside FROZEN_FIELDS and outcome (`realised_direction`, a
       future `games` count) are not compared.
    2. An appended hypothesis is taken on trust, whatever it claims.
    3. `--base` is believed: the same file on both sides is clean.
    4. The merge key is literal: `[2025, 2026]` and `[2026, 2025]` are two
       keys, and so is a name with a trailing space.
    5. A pending outcome filled in with a FINDING is accepted, because it is
       indistinguishable from the measurement writing back. The gate cannot
       know whether the number was real; nothing at the diff can.
    """
    loud = entry("moneyline")
    loud["realised_direction"] = "higher"
    assert run(tmp_path, [entry("moneyline")], [loud]) == 0

    assert run(tmp_path, THREE, THREE + [entry("team_total", outcome="+9.9% ROI, significant")]) == 0

    invented = write(tmp_path / "same.json", [entry("moneyline", outcome="+9.9% ROI, significant")])
    assert check.main(["--base", str(invented), "--head", str(invented)]) == 0

    reordered = entry("spread", seasons=(2026, 2025), outcome="+2.1% ROI, significant")
    assert run(tmp_path, [entry("moneyline")], [entry("moneyline"), entry("spread"), reordered]) == 0
    spaced = entry("spread ", outcome="+2.1% ROI, significant")
    assert run(tmp_path, [entry("moneyline")], [entry("moneyline"), entry("spread"), spaced]) == 0

    assert run(tmp_path, [entry("moneyline")], [entry("moneyline", outcome="+9.9% ROI, significant")]) == 0
    capsys.readouterr()


def test_a_missing_head_fails(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    base_path = write(tmp_path / "base.json", THREE)
    assert check.main(["--base", str(base_path), "--head", str(tmp_path / "nowhere.json")]) == 1
    assert "does not exist" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ("", "not parseable JSON"),
        ("{not json", "not parseable JSON"),
        ('["a", "b"]', "not a JSON object"),
        ('{"hypotheses": {}}', "no 'hypotheses' list"),
        ('{"hypotheses": ["x"]}', "not an object"),
        ('{"hypotheses": [{"search": "s"}]}', "missing 'name'"),
    ],
)
def test_a_malformed_head_fails(tmp_path: Path, capsys: pytest.CaptureFixture, payload: str, expected: str) -> None:
    head_path = tmp_path / "head.json"
    head_path.write_text(payload, encoding="utf-8")
    base_path = write(tmp_path / "base.json", THREE)
    assert check.main(["--base", str(base_path), "--head", str(head_path)]) == 1
    assert expected in capsys.readouterr().err


@pytest.mark.parametrize(
    ("seasons", "expected"),
    [
        pytest.param("2021", "has 'seasons' as a str, not a list", id="string"),
        pytest.param(None, "has 'seasons' as a NoneType, not a list", id="null"),
        pytest.param(["2021"], "has a season that is a str, not an int", id="str-season"),
        pytest.param([True], "has a season that is a bool, not an int", id="bool-season"),
    ],
)
def test_every_seasons_branch_refuses_its_own_bad_input(tmp_path: Path, capsys: pytest.CaptureFixture, seasons: object, expected: str) -> None:
    bad = entry("moneyline")
    bad["seasons"] = seasons
    head_path = write(tmp_path / "head.json", [bad])
    base_path = write(tmp_path / "base.json", THREE)
    assert check.main(["--base", str(base_path), "--head", str(head_path)]) == 1
    assert expected in capsys.readouterr().err


def test_a_bool_season_keys_like_the_int_it_hides(tmp_path: Path) -> None:
    assert check.key(entry("n", seasons=(True,))) == check.key(entry("n", seasons=(1,)))


def test_base_absent_passes_on_a_valid_head_and_still_validates(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    assert run(tmp_path, None, THREE) == 0
    assert "first-commit state" in capsys.readouterr().out
    head_path = tmp_path / "head.json"
    head_path.write_text('{"hypotheses": [{"search": "s"}]}', encoding="utf-8")
    assert check.main(["--base-absent", "--head", str(head_path)]) == 1


def test_a_base_that_compared_nothing_fails(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    assert run(tmp_path, [], THREE) == 1
    assert "base was present but nothing was compared" in capsys.readouterr().err


def test_neither_or_both_origin_flags_are_refused(tmp_path: Path) -> None:
    head_path = write(tmp_path / "head.json", THREE)
    base_path = write(tmp_path / "base.json", THREE)
    with pytest.raises(SystemExit) as neither:
        check.main(["--head", str(head_path)])
    assert neither.value.code == 2
    with pytest.raises(SystemExit) as both:
        check.main(["--base", str(base_path), "--base-absent", "--head", str(head_path)])
    assert both.value.code == 2


@pytest.mark.parametrize("waiver", ["--force", "--allow", "--skip"])
def test_no_waiver_flag_exists(tmp_path: Path, waiver: str) -> None:
    head_path = write(tmp_path / "head.json", THREE[:2])
    base_path = write(tmp_path / "base.json", THREE)
    with pytest.raises(SystemExit) as excinfo:
        check.main(["--base", str(base_path), "--head", str(head_path), waiver])
    assert excinfo.value.code == 2


def test_no_environment_variable_turns_a_shrink_green(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LEDGER_GUARD", "SKIP_LEDGER_CHECK", "FORCE", "CI", "ALLOW_SHRINK"):
        monkeypatch.setenv(name, "1")
    assert run(tmp_path, THREE, THREE[:2]) == 1


# ONE ledger. This used to parametrize over a second, tracked copy under
# data/outputs/holdout/ — the copy the replication appended its holdout looks
# to while the backtest read its correction from the original. Asserting the
# copy existed enshrined the fork in a test.
@pytest.mark.parametrize("relative", ["data/outputs/experiment_ledger.json"])
def test_each_tracked_ledger_passes_against_itself(relative: str, capsys: pytest.CaptureFixture) -> None:
    tracked = _SCRIPT.parents[1] / relative
    assert tracked.is_file(), f"{relative} is missing"
    assert check.main(["--base", str(tracked), "--head", str(tracked)]) == 0
    assert "distinct hypotheses in the head ledger" in capsys.readouterr().out.splitlines()[0]


def _thirty(path: Path) -> Path:
    """A thirty-entry ledger on disk, the size of this lab's tracked one."""
    ledger = experiment_ledger.ExperimentLedger()
    ledger.record(*(
        experiment_ledger.Hypothesis(search="s", name=f"h{i}", tested_on="2026-09-01", seasons=(2026,), outcome="pending", predicted_direction="higher")
        for i in range(30)
    ))
    experiment_ledger.save(ledger, path, floor=0)
    return path


def _old_save(ledger, path: Path) -> None:
    """`save()` exactly as it stood on 02e75b7: re-read the target, compare.

    Transcribed rather than described, so the test below exercises the old
    BEHAVIOUR instead of asserting a sentence about it. Only the comparison
    is reproduced; the write is not, because what is under test is which
    edits reached the raise.
    """
    target = Path(path)
    if target.is_file():
        existing = experiment_ledger.load(target)
        if len(ledger.hypotheses) < len(existing.hypotheses):
            raise ValueError(
                f"The experiment ledger would fall from {len(existing.hypotheses)} "
                f"entries to {len(ledger.hypotheses)}. It is append-only."
            )


def test_the_old_re_read_fired_on_an_in_process_shrink_and_missed_the_committed_one(tmp_path: Path) -> None:
    """What the guard before 2026-09-04 actually did, run rather than recalled.

    Four files in this lab used to say that `save()`'s re-read compared
    `n >= n` and "could never fire", and that deleting twelve of thirty
    hypotheses and re-running the recorder dropped the correction from x1.60
    to x1.46. Re-measured, all of that is wrong, and each half is asserted
    below:

    1. the old re-read DOES raise on an in-process shrink — the file still
       holds thirty when the comparison happens;
    2. it does NOT raise once the shorter ledger is already on disk, which is
       what "edited by hand and committed" means, because then the comparison
       is thirty-minus-twelve against itself;
    3. the recorder self-heals, so re-running it after such an edit restores
       every entry and prints x1.60 rather than a smaller factor;
    4. x1.46 is the correction at TWELVE hypotheses. Deleting twelve of
       thirty leaves eighteen, and eighteen is x1.53.
    """
    path = _thirty(tmp_path / experiment_ledger.LEDGER_FILENAME)

    # 1. In process: load thirty, delete twelve, save back. The old re-read
    #    sees thirty on disk against eighteen in memory, and raises.
    in_process = experiment_ledger.load(path)
    del in_process.hypotheses[18:]
    with pytest.raises(ValueError, match="fall from 30 entries to 18"):
        _old_save(in_process, path)

    # 2. Edited on disk and committed: the shorter ledger IS the file, so the
    #    old comparison is 18 >= 18 and nothing is raised. This is the shape
    #    `scripts/check_ledger_append_only.py` and the Ledger Guard exist for.
    edited_on_disk = tmp_path / "committed.json"
    edited_on_disk.write_text(
        json.dumps({"hypotheses": [
            {"search": h.search, "name": h.name, "tested_on": h.tested_on,
             "seasons": list(h.seasons), "outcome": h.outcome,
             "predicted_direction": h.predicted_direction, "stage": h.stage,
             "realised_direction": h.realised_direction}
            for h in in_process.hypotheses
        ]}, indent=2) + "\n",
        encoding="utf-8",
    )
    _old_save(experiment_ledger.load(edited_on_disk), edited_on_disk)  # no raise

    # 3. And the diff-level gate is what does see it.
    assert check.main(["--base", str(path), "--head", str(edited_on_disk)]) == 1

    # 4. The arithmetic the old prose quoted.
    at_twelve = experiment_ledger.ExperimentLedger(hypotheses=in_process.hypotheses[:12])
    at_eighteen = experiment_ledger.ExperimentLedger(hypotheses=in_process.hypotheses[:18])
    at_thirty = experiment_ledger.load(path)
    assert round(at_twelve.correction_factor(), 2) == 1.46
    assert round(at_eighteen.correction_factor(), 2) == 1.53
    assert round(at_thirty.correction_factor(), 2) == 1.60


def test_the_recorder_self_heals_a_ledger_that_was_cut_on_disk(tmp_path: Path) -> None:
    """Re-running the recorder RESTORES the ledger — as far as its own
    pre-registered constant reaches, and not one entry further.

    `ExperimentLedger.record()` skips a key it already holds and appends the
    rest, so the recorder puts every hypothesis in `record_experiments.HYPOTHESES`
    back. That is why "delete twelve of thirty and re-run the recorder" never
    produced the x1.46 four files used to quote: the count comes back to the
    size of that constant and the printed correction is x1.60.

    **The tracked ledger no longer holds thirty.** The full-store run of
    2026-09-05 put every discovery cell to the held-out seasons and recorded
    32 holdout looks — `data/outputs/holdout/cbb_replication.json` carries
    `ledger.holdout_looks_recorded` — so the tracked ledger holds 62 and the
    factor the reports apply is x1.71. Every count below is read off disk
    rather than typed, and only the SIZE of the cut — eighteen entries left,
    which is what the audit reproduced — is fixed here.

    The gap between the two counts is what the second half asserts. The
    recorder heals what it pre-registered and CANNOT heal a holdout look,
    because it has never heard of one: a ledger cut on disk and re-recorded
    comes back SHORT of what the reports corrected against. That is why the
    append-only gate is `Ledger Guard` diffing against the PR base and never
    the recorder re-running.
    """
    import os
    import subprocess
    import sys

    repo = Path(__file__).resolve().parents[1]
    tracked = json.loads((repo / "data" / "outputs" / "experiment_ledger.json").read_text(encoding="utf-8"))
    assert len(tracked["hypotheses"]) == 62, (
        f"the tracked ledger holds {len(tracked['hypotheses'])} entries, not 62; "
        "this test's arithmetic is quoted in four other files and needs re-deriving"
    )
    pre_registered = len(_recorder.HYPOTHESES)
    assert pre_registered < len(tracked["hypotheses"]), (
        "the recorder's constant now carries every tracked entry, so this test "
        "no longer measures the gap it exists to measure"
    )

    cut = dict(tracked)
    cut["hypotheses"] = tracked["hypotheses"][:18]
    (tmp_path / experiment_ledger.LEDGER_FILENAME).write_text(json.dumps(cut, indent=2) + "\n", encoding="utf-8")

    completed = subprocess.run(
        [sys.executable, str(repo / "scripts" / "record_experiments.py"), "--output-dir", str(tmp_path)],
        cwd=repo, capture_output=True, text=True, timeout=300,
        env={**os.environ, "PYTHONPATH": str(repo / "src")},
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    restored = json.loads((tmp_path / experiment_ledger.LEDGER_FILENAME).read_text(encoding="utf-8"))

    healed = experiment_ledger.load(tmp_path / experiment_ledger.LEDGER_FILENAME)
    assert (
        f"18 distinct hypotheses before, {pre_registered} after "
        f"({pre_registered - 18} new)"
    ) in completed.stdout, completed.stdout
    assert f"x{healed.correction_factor():.2f}" in completed.stdout, completed.stdout
    assert len(restored["hypotheses"]) == pre_registered

    # And what it could not heal: the holdout looks the replication appended.
    # They are not in the recorder's constant, so a cut ledger comes back
    # short of the family the reports corrected against.
    assert len(restored["hypotheses"]) < len(tracked["hypotheses"])
    assert not [h for h in restored["hypotheses"] if h.get("stage") == "holdout"], (
        "the recorder restored a holdout look, which it cannot know about; "
        "re-derive the two counts above from the ledger and the replication record"
    )
    whole = experiment_ledger.load(repo / "data" / "outputs" / "experiment_ledger.json")
    assert healed.correction_factor() < whole.correction_factor(), (
        "healing a cut ledger left the correction as strict as the tracked one, "
        "so the shortfall this test is about has stopped existing"
    )


def test_save_refuses_to_write_below_the_floor_the_caller_loaded(tmp_path: Path) -> None:
    """The floor: the count the caller LOADED, which the re-read cannot supply.

    The re-read compares against whatever is at the target path, so it has
    nothing to say when the target does not yet exist — a caller that loads
    from one path and writes to another. The floor is a number the caller
    held before it mutated anything, and it is required rather than defaulted
    so it cannot quietly stop being passed.
    """
    path = _thirty(tmp_path / experiment_ledger.LEDGER_FILENAME)

    reloaded = experiment_ledger.load(path)
    loaded = len(reloaded.hypotheses)
    del reloaded.hypotheses[18:]
    with pytest.raises(ValueError, match="fall from 30 entries \\(the count loaded\\) to 18"):
        experiment_ledger.save(reloaded, path, floor=loaded)
    assert len(experiment_ledger.load(path).hypotheses) == 30, "the refused write reached the disk"

    # The shape the re-read is blind to and the floor is not: a target that
    # does not exist yet, so there is nothing to re-read.
    elsewhere = tmp_path / "elsewhere" / experiment_ledger.LEDGER_FILENAME
    _old_save(reloaded, elsewhere)  # the old comparison has nothing to compare
    with pytest.raises(ValueError, match="fall from 30 entries \\(the count loaded\\) to 18"):
        experiment_ledger.save(reloaded, elsewhere, floor=loaded)
    assert not elsewhere.exists(), "the refused write created the file anyway"

    # A floor is required: the guard is not left to a default.
    with pytest.raises(TypeError):
        experiment_ledger.save(reloaded, path)  # type: ignore[call-arg]
    with pytest.raises(ValueError, match="floor must be"):
        experiment_ledger.save(reloaded, path, floor=-1)

    # And an honest append passes with the loaded count as the floor.
    grown = experiment_ledger.load(path)
    grown.record(experiment_ledger.Hypothesis(search="s", name="h30", tested_on="2026-09-01", seasons=(2026,), outcome="pending", predicted_direction="higher"))
    experiment_ledger.save(grown, path, floor=30)
    assert len(experiment_ledger.load(path).hypotheses) == 31
