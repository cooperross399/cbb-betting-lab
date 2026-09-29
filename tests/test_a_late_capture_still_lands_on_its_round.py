"""A scheduled Line Movement run waits for its round, however late GitHub
starts it.

These crons, written at their rounds, ran a median 3.1 h and at worst 6.6 h
late over 86 runs from 2026-09-08 to 09-29, so the 23:13 UTC round landed
after the 19:00 ET block had tipped. Each cron now fires `ROUND_LEAD` before
its round and the run waits (`scripts/wait_for_round.py`). These tests pin the
arithmetic the wait rests on and the wiring that puts it in front of the
capture: a correct script the capture does not wait for fixes nothing, and a
wait whose failure skips the capture is worse than no wait.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = PROJECT_ROOT / ".github" / "workflows" / "line-movement.yml"
SCRIPT = PROJECT_ROOT / "scripts" / "wait_for_round.py"

#: The rounds the capture brackets the slate with, in UTC (hour, minute):
#: mid-morning, early afternoon, an hour before the 19:00 ET block, and late
#: in the evening slate. They are what the crons said before the wait existed.
ROUNDS = {(14, 13), (18, 13), (23, 13), (3, 13)}


def _load_script():
    spec = importlib.util.spec_from_file_location("_cbb_wait_for_round", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


wfr = _load_script()


def _document() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _crons() -> list[str]:
    document = _document()
    triggers = document.get("on", document.get(True))
    crons = [str(entry["cron"]) for entry in triggers["schedule"]]
    assert crons, "line-movement.yml declares no cron; every test below would pass vacuously"
    return crons


# --------------------------------------------------------------------------
# The arithmetic
# --------------------------------------------------------------------------


def test_every_cron_plus_the_lead_is_one_of_the_rounds() -> None:
    """The set of rounds, both ways: no cron lands off a round, and no round
    lost its cron. A cron left at its round would land eight hours late."""
    lead = int(wfr.ROUND_LEAD.total_seconds() // 60)
    landed = set()
    for cron in _crons():
        minute, hour = cron.split()[:2]
        total = (int(hour) * 60 + int(minute) + lead) % (24 * 60)
        landed.add(divmod(total, 60))
    assert landed == ROUNDS
    assert len(_crons()) == len(ROUNDS), "two crons for one round would capture it twice"


def test_every_cron_names_a_single_minute_and_hour_on_every_day() -> None:
    """The wait reads one minute and one hour back out of the cron that fired
    it; a list or a step would raise there and the run would capture at once.
    Every day and every month, because the capture runs year-round and a
    round moved across midnight must not need a day or month field."""
    now = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
    for cron in _crons():
        minute, hour, day, month, weekday = cron.split()
        assert minute.isdigit() and hour.isdigit(), cron
        assert (day, month, weekday) == ("*", "*", "*"), cron
        wfr.round_for(cron, now)


def test_the_lead_covers_the_lateness_this_workflow_has_seen() -> None:
    assert wfr.ROUND_LEAD >= timedelta(hours=7.4)


@pytest.mark.parametrize("late_h", [0.0, 0.01, 1.0, 3.1, 6.6, 7.38, 7.99])
@pytest.mark.parametrize("round_h", sorted(ROUNDS))
def test_a_run_started_up_to_the_lead_late_waits_for_its_round(round_h, late_h) -> None:
    hour, minute = round_h
    cron_at = datetime(2026, 11, 2, hour, minute, tzinfo=timezone.utc) - wfr.ROUND_LEAD
    cron = f"{cron_at.minute} {cron_at.hour} * * *"
    started = cron_at + timedelta(hours=late_h)
    target = wfr.round_for(cron, started)
    assert target == datetime(2026, 11, 2, hour, minute, tzinfo=timezone.utc)
    assert target >= started


def test_the_late_evening_round_crosses_midnight_utc() -> None:
    """19:13 UTC fires for 03:13 UTC the NEXT day, and a run started after
    midnight UTC still finds the cron on the day before."""
    after_midnight = datetime(2026, 11, 3, 1, 0, tzinfo=timezone.utc)
    assert wfr.round_for("13 19 * * *", after_midnight) == datetime(
        2026, 11, 3, 3, 13, tzinfo=timezone.utc
    )
    before_midnight = datetime(2026, 11, 2, 22, 0, tzinfo=timezone.utc)
    assert wfr.round_for("13 19 * * *", before_midnight) == datetime(
        2026, 11, 3, 3, 13, tzinfo=timezone.utc
    )


def test_a_run_later_than_the_lead_captures_at_once() -> None:
    started = datetime(2026, 11, 2, 15, 13, tzinfo=timezone.utc) + timedelta(hours=9.85)
    assert wfr.round_for("13 15 * * *", started) < started


def test_a_malformed_cron_is_refused() -> None:
    now = datetime(2026, 11, 2, 12, 0, tzinfo=timezone.utc)
    for bad in ("13 3,15 * * *", "13 */2 * * *", "13 15 * *"):
        with pytest.raises(ValueError):
            wfr.round_for(bad, now)


class _Clock:
    def __init__(self, now: datetime) -> None:
        self.now = now
        self.slept: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)


def _run(monkeypatch, now: datetime, argv: list[str]) -> tuple[int, _Clock]:
    clock = _Clock(now)

    class _FrozenDatetime(datetime):
        @classmethod
        def now(cls, tz=None):  # noqa: D401 - a frozen clock
            return clock.now

    monkeypatch.setattr(wfr, "datetime", _FrozenDatetime)
    monkeypatch.setattr(wfr.time, "sleep", clock.sleep)
    return wfr.main(argv), clock


def test_the_wait_is_split_across_two_budgets(monkeypatch) -> None:
    """An on-time run waits eight hours: 340 minutes in the first job and the
    rest in the second, which recomputes the round from the same cron."""
    fired = datetime(2026, 11, 2, 15, 13, 30, tzinfo=timezone.utc)
    code, clock = _run(monkeypatch, fired, ["--schedule", "13 15 * * *", "--budget-minutes", "340"])
    assert code == 0 and clock.slept == [340 * 60]
    code, clock = _run(monkeypatch, fired + timedelta(minutes=340), ["--schedule", "13 15 * * *", "--budget-minutes", "340"])
    assert code == 0 and clock.slept == [(480 - 340) * 60 - 30]


def test_a_manual_dispatch_and_a_late_run_do_not_wait(monkeypatch) -> None:
    fired = datetime(2026, 11, 2, 15, 13, tzinfo=timezone.utc)
    code, clock = _run(monkeypatch, fired, ["--schedule", "", "--budget-minutes", "340"])
    assert code == 0 and clock.slept == []
    code, clock = _run(monkeypatch, fired + timedelta(hours=9), ["--schedule", "13 15 * * *"])
    assert code == 0 and clock.slept == []


def test_a_malformed_cron_fails_the_wait_job(monkeypatch) -> None:
    code, clock = _run(monkeypatch, datetime(2026, 11, 2, tzinfo=timezone.utc), ["--schedule", "13 3,15 * * *"])
    assert code == 2 and clock.slept == []


# --------------------------------------------------------------------------
# The wiring
# --------------------------------------------------------------------------


def _wait_step(job: dict) -> dict:
    (step,) = [s for s in job["steps"] if "wait_for_round.py" in str(s.get("run", ""))]
    return step


def test_the_capture_waits_behind_both_wait_jobs() -> None:
    jobs = _document()["jobs"]
    assert set(jobs) == {"wait", "wait-more", "capture"}
    assert "needs" not in jobs["wait"]
    assert jobs["wait-more"]["needs"] == "wait"
    assert jobs["capture"]["needs"] == "wait-more"


def test_a_failed_wait_never_skips_the_capture() -> None:
    """Spelled out on both downstream jobs. A job with no `if`, or a bare
    one, carries an implicit success() over everything upstream, so a wait
    that failed would cost the round. `always()` would be wrong the other
    way: it keeps running a run somebody cancelled."""
    jobs = _document()["jobs"]
    for name in ("wait-more", "capture"):
        condition = str(jobs[name].get("if", ""))
        assert "!cancelled()" in condition, name
        assert "always()" not in condition, name


def test_both_waits_read_the_cron_that_fired_the_run() -> None:
    jobs = _document()["jobs"]
    for name in ("wait", "wait-more"):
        step = _wait_step(jobs[name])
        assert step["env"]["SCHEDULE"] == "${{ github.event.schedule }}", name
        assert '--schedule "$SCHEDULE"' in step["run"], name
        budget = float(step["run"].split("--budget-minutes")[1].split()[0])
        assert budget < int(jobs[name]["timeout-minutes"]), name
        assert "secrets." not in str(jobs[name]), name
    budgets = [
        float(_wait_step(jobs[name])["run"].split("--budget-minutes")[1].split()[0])
        for name in ("wait", "wait-more")
    ]
    assert timedelta(minutes=sum(budgets)) >= wfr.ROUND_LEAD


def test_concurrency_is_on_the_capture_job_not_the_workflow() -> None:
    """A workflow-level group keeps one run pending and cancels the one
    before it, and every run now spends hours pending behind its wait."""
    document = _document()
    assert "concurrency" not in document
    assert document["jobs"]["capture"]["concurrency"] == {
        "group": "line-movement", "cancel-in-progress": False,
    }
    for name in ("wait", "wait-more"):
        assert "concurrency" not in document["jobs"][name], name
