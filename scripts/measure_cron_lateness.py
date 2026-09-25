#!/usr/bin/env python3
"""How late GitHub fires Cooper's scheduled workflows, measured from the runs.

    PYTHONPATH=src python scripts/measure_cron_lateness.py
    PYTHONPATH=src python scripts/measure_cron_lateness.py --since 2026-08-27

Writes `data/outputs/cbb_cron_lateness.json`. Needs the `gh` CLI signed in to
an account that can read every repository named in `REPOSITORIES`, and spends
nothing: it reads the Actions API and workflow files, never a provider.

**Why it exists.** `schedule_contract.OBSERVED_LATENESS_H` is the one number
every card, relay and weekly deadline in this repository is checked against,
and it was a sentence — *"4.5-5.3 hours late since 2026-08-27"* — for four
weeks while the same account's crons ran 7.38 hours late. A constant that
guards every deadline has to be an observation someone can re-take, so this is
the observation and `tests/test_the_card_schedule_survives_cron_lateness.py`
holds the constant to the record it writes.

**Every repository, not only this one.** The constant is *"the worst lateness
observed on Cooper's repositories"*: GitHub's scheduler does not know which
lab a cron belongs to, and this lab's card crons fire only November to April,
so in the off-season the siblings are the only evidence of what a card cron
will face. The worst run measured on 2026-09-25 was not in this repository.

**How a run is matched to the cron that fired it.** The API does not say. So
each run is read against the crons its workflow declared AT THE COMMIT THAT
FIRED IT, and the runs of one workflow are matched to its nominal instants in
firing order, latest run first, each taking the latest unmatched instant at or
before it. That is the least lateness any first-in-first-out assignment
allows, dropped runs included, so **every figure written is a lower bound**:
where the matching is ambiguous it is resolved in GitHub's favour. On a day
with thirteen hourly crons and thirteen runs, the first run of the day belongs
to the first cron under any order, so its figure is exact.

Runs in the first day after a cron change are dropped, because a late firing
of the old schedule would otherwise be matched to an instant of the new one.
"""

from __future__ import annotations

import argparse
import base64
import json
import statistics
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

from cbb_betting_lab.config import OUTPUTS_DIR

OWNER = "cooperross399"

#: Every repository of Cooper's that runs a scheduled workflow. The
#: constant is account-wide, so the record is too.
REPOSITORIES = (
    "cbb-betting-lab",
    "football-betting-lab",
    "nhl-betting-lab",
    "epl-betting-lab",
    "golf-betting-lab",
    "ncaaf-betting-lab",
)

#: The window the constant is defined over: *"since 2026-08-27"*, the day
#: Cooper first reported the lateness.
DEFAULT_SINCE = date(2026, 8, 27)

OUTPUT = OUTPUTS_DIR / "cbb_cron_lateness.json"

#: Runs fired by a schedule within this long of the commit that changed it
#: are not matched. See the module docstring.
SETTLE_AFTER_CRON_CHANGE = timedelta(days=1)

TOP_N = 25


def gh_json(path: str, paginate: bool = False) -> list | dict:
    command = ["gh", "api", path]
    if paginate:
        command.insert(2, "--paginate")
        command += ["--jq", ".workflow_runs[]"]
    completed = subprocess.run(command, capture_output=True, text=True, check=True)
    if not paginate:
        return json.loads(completed.stdout)
    return [json.loads(line) for line in completed.stdout.splitlines() if line.strip()]


def parse_instant(text: str) -> datetime:
    return datetime.fromisoformat(text.replace("Z", "+00:00"))


def cron_field(spec: str, low: int, high: int) -> set[int]:
    values: set[int] = set()
    for part in spec.split(","):
        step = 1
        if "/" in part:
            part, step_text = part.split("/")
            step = int(step_text)
        if part == "*":
            first, last = low, high
        elif "-" in part:
            first, last = (int(x) for x in part.split("-"))
        else:
            first = last = int(part)
        values.update(range(first, last + 1, step))
    return values


def cron_instants(expression: str, start: datetime, end: datetime) -> list[datetime]:
    """Every UTC instant in [start, end] that `expression` names. Five fields,
    lists, ranges and steps; day-of-month and day-of-week OR together when both
    are restricted, as cron has it."""
    minute, hour, day_of_month, month, day_of_week = expression.split()
    minutes, hours = cron_field(minute, 0, 59), cron_field(hour, 0, 23)
    days, months = cron_field(day_of_month, 1, 31), cron_field(month, 1, 12)
    weekdays = {d % 7 for d in cron_field(day_of_week, 0, 7)}
    either_open = day_of_month == "*" or day_of_week == "*"
    instants = []
    day = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while day <= end:
        cron_weekday = (day.weekday() + 1) % 7
        if day.month in months:
            on_day = (day.day in days) and (cron_weekday in weekdays) if either_open \
                else (day.day in days) or (cron_weekday in weekdays)
            if on_day:
                for h in sorted(hours):
                    for m in sorted(minutes):
                        instant = day.replace(hour=h, minute=m)
                        if start <= instant <= end:
                            instants.append(instant)
        day += timedelta(days=1)
    return instants


@dataclass(frozen=True)
class Run:
    repository: str
    workflow: str
    run_id: int
    created: datetime
    head_sha: str
    head_committed: datetime
    url: str


_CRONS_AT: dict[tuple[str, str, str], tuple[str, ...]] = {}


def crons_at(repository: str, workflow: str, sha: str) -> tuple[str, ...]:
    key = (repository, workflow, sha)
    if key not in _CRONS_AT:
        document = gh_json(f"repos/{OWNER}/{repository}/contents/{workflow}?ref={sha}")
        text = base64.b64decode(document["content"]).decode("utf-8")
        parsed = yaml.safe_load(text) or {}
        triggers = parsed.get("on", parsed.get(True)) or {}
        schedule = triggers.get("schedule") if isinstance(triggers, dict) else None
        _CRONS_AT[key] = tuple(str(entry["cron"]) for entry in (schedule or []))
    return _CRONS_AT[key]


def scheduled_runs(repository: str, fetch_from: date) -> list[Run]:
    raw = gh_json(
        f"repos/{OWNER}/{repository}/actions/runs?event=schedule"
        f"&created=>={fetch_from.isoformat()}&per_page=100",
        paginate=True,
    )
    runs = []
    for item in raw:
        if item.get("run_attempt", 1) != 1:
            continue
        runs.append(Run(
            repository=repository,
            workflow=item["path"],
            run_id=int(item["id"]),
            created=parse_instant(item["created_at"]),
            head_sha=item["head_sha"],
            head_committed=parse_instant(item["head_commit"]["timestamp"]),
            url=item["html_url"],
        ))
    return sorted(runs, key=lambda r: r.created)


def match(runs: list[Run], crons: tuple[str, ...]) -> list[tuple[Run, datetime, str]]:
    """Least-lateness first-in-first-out matching. See the module docstring."""
    if not runs or not crons:
        return []
    start = runs[0].created - timedelta(days=8)
    by_instant: dict[datetime, str] = {}
    for expression in crons:
        for instant in cron_instants(expression, start, runs[-1].created):
            by_instant.setdefault(instant, expression)
    nominals = sorted(by_instant)
    matched = []
    j = len(nominals) - 1
    for run in reversed(runs):
        while j >= 0 and nominals[j] > run.created:
            j -= 1
        if j < 0:
            break
        matched.append((run, nominals[j], by_instant[nominals[j]]))
        j -= 1
    return matched


def measure(since: date) -> dict:
    observations = []
    per_workflow = []
    # Fetch a week before the window so the first runs inside it can be
    # matched against instants whose earlier neighbours are known.
    fetch_from = since - timedelta(days=7)
    for repository in REPOSITORIES:
        grouped: dict[str, list[Run]] = defaultdict(list)
        for run in scheduled_runs(repository, fetch_from):
            grouped[run.workflow].append(run)
        for workflow, runs in sorted(grouped.items()):
            # Split into stretches over which the declared crons did not change.
            stretches: list[tuple[tuple[str, ...], list[Run], datetime | None]] = []
            for run in runs:
                crons = crons_at(repository, workflow, run.head_sha)
                if not stretches or stretches[-1][0] != crons:
                    changed = run.head_committed if stretches else None
                    stretches.append((crons, [], changed))
                stretches[-1][1].append(run)
            for crons, stretch, changed in stretches:
                settled = [
                    r for r in stretch
                    if changed is None or r.created >= changed + SETTLE_AFTER_CRON_CHANGE
                ]
                rows = [
                    {
                        "repository": run.repository,
                        "workflow": Path(run.workflow).name,
                        "cron": expression,
                        "nominal_utc": nominal.isoformat(),
                        "created_utc": run.created.isoformat(),
                        "lateness_h": round((run.created - nominal).total_seconds() / 3600, 3),
                        "run_url": run.url,
                    }
                    for run, nominal, expression in match(settled, crons)
                    if nominal.date() >= since
                ]
                if not rows:
                    continue
                observations.extend(rows)
                lateness = [row["lateness_h"] for row in rows]
                per_workflow.append({
                    "repository": repository,
                    "workflow": Path(workflow).name,
                    "crons": list(crons),
                    "matched_runs": len(rows),
                    "median_h": round(statistics.median(lateness), 2),
                    "max_h": max(lateness),
                })

    if not observations:
        raise SystemExit("no scheduled run could be matched; refusing to write an empty record")

    by_hour: dict[int, list[float]] = defaultdict(list)
    for row in observations:
        by_hour[parse_instant(row["nominal_utc"]).hour].append(row["lateness_h"])
    worst = max(observations, key=lambda row: row["lateness_h"])
    return {
        "measured_at_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "since": since.isoformat(),
        "repositories": [f"{OWNER}/{name}" for name in REPOSITORIES],
        "method": (
            "Scheduled runs, first attempts only, matched first-in-first-out to "
            "the crons their workflow declared at the commit that fired them, "
            "each run taking the latest unmatched nominal instant at or before "
            "it. Every figure is therefore a LOWER bound on the real lateness. "
            "Lateness is created_at minus the nominal cron instant."
        ),
        "matched_runs": len(observations),
        "worst_h": worst["lateness_h"],
        "worst": worst,
        "by_nominal_hour_utc": {
            f"{hour:02d}": {
                "runs": len(values),
                "median_h": round(statistics.median(values), 2),
                "max_h": max(values),
            }
            for hour, values in sorted(by_hour.items())
        },
        "by_workflow": sorted(per_workflow, key=lambda w: -w["max_h"]),
        "worst_runs": sorted(observations, key=lambda row: -row["lateness_h"])[:TOP_N],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--since", type=date.fromisoformat, default=DEFAULT_SINCE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)

    record = measure(args.since)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    worst = record["worst"]
    print(
        f"{record['matched_runs']} runs matched since {record['since']}. Worst: "
        f"{worst['lateness_h']:.2f}h, {worst['repository']} {worst['workflow']} "
        f"`{worst['cron']}` due {worst['nominal_utc']} fired {worst['created_utc']}."
    )
    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
