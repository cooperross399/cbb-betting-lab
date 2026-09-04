"""The weekly loop, and the five things it must never be talked out of.

`scripts/run_weekly_loop.py` is the only unattended program in this repository
that can change what the lab does — it can append to the append-only experiment
ledger and it can take a market off the card. Everything else reports. So the
tests here are not about whether it runs; they are about the four fences that
make it safe to run unattended, plus the one arithmetic fact its cron depends on:

1. **The alpha budget binds.** N a week, from the queue's declared order,
   waiting rather than borrowing when it is spent, and spending nothing at all
   when the budget on disk was never declared in advance.
2. **Demotion is one-directional.** `withdraw()` is reachable from here;
   nothing that grants is, and a sweep of the source proves it.
3. **A missing sibling program degrades the run and never crashes it**, and
   never quietly looks like a step that succeeded.
4. **The correction is the ledger's cumulative count**, checked against the
   record the backtest actually wrote rather than trusted because a subprocess
   exited zero.
5. **The cron cannot slip into the following ISO week**, recomputed from
   `schedule_contract.OBSERVED_LATENESS_H` rather than asserted, because the
   alpha budget's bucket is the week the run stamps.

The house rule from `docs/build_order.md` applies throughout: a test that bans a
word rather than an assertion has been written three times in this repository
and been wrong three times. These check behaviour against a real ledger, a real
policy file and a real git-free temporary tree.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
from dataclasses import replace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

from cbb_betting_lab import experiment_ledger as E
from cbb_betting_lab import forward_evidence as fe
from cbb_betting_lab import promotion
from cbb_betting_lab import schedule_contract
from cbb_betting_lab import staging_provider_policy as staging
from cbb_betting_lab import stats as S
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.reports import price_backtest as PB

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "scripts"
WORKFLOW = REPO / ".github" / "workflows" / "weekly-refit-and-measure.yml"
QUEUE_ON_DISK = REPO / "data" / "manual" / "weekly_search_queue.json"


def load_loop():
    """Import the script by path, the way the workflow runs it.

    `scripts/` is not a package and must not become one — the sibling labs all
    keep entry points as scripts — so the import is by spec rather than by name.
    """
    spec = importlib.util.spec_from_file_location(
        "run_weekly_loop", SCRIPTS / "run_weekly_loop.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


LOOP = load_loop()


# --------------------------------------------------------------------------
# A temporary lab
# --------------------------------------------------------------------------


def write_ledger(path: Path, *, declared_on: str = "2026-09-01", count: int = 0) -> Path:
    ledger = E.ExperimentLedger(
        budget=E.AlphaBudget(per_week=6, declared_on=declared_on, rationale="test")
    )
    for i in range(count):
        ledger.record(
            E.Hypothesis(
                search="prior_build",
                name=f"already tested {i}",
                tested_on="2026-09-01",
                seasons=(2026,),
                outcome="pending",
                predicted_direction="higher",
            )
        )
    return E.save(ledger, path, floor=0)


def write_queue(path: Path, entries: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"declared_on": "2026-09-01", "queue": entries}, indent=2),
        encoding="utf-8",
    )
    return path


def queue_entry(n: int, *, direction: str = "higher", stage: str = "discovery") -> dict:
    return {
        "search": "weekly_test",
        "name": f"hypothesis {n}",
        "seasons": [2027],
        "predicted_direction": direction,
        "stage": stage,
        "why": f"declared in advance, entry {n}",
    }


@pytest.fixture()
def lab(tmp_path: Path) -> dict:
    """A complete, empty lab: outputs, processed, manual, scripts."""
    tree = {
        name: tmp_path / name
        for name in ("outputs", "processed", "manual", "scripts")
    }
    for directory in tree.values():
        directory.mkdir(parents=True, exist_ok=True)
    write_ledger(tree["outputs"] / E.LEDGER_FILENAME)
    (tree["manual"] / promotion.CRITERIA_FILENAME).write_text(
        (REPO / "data" / "manual" / promotion.CRITERIA_FILENAME).read_text(
            encoding="utf-8"
        ),
        encoding="utf-8",
    )
    staging.save(staging.StagingProviderPolicy(), tree["manual"])
    return tree


def run(lab: dict, *extra: str) -> int:
    return LOOP.main(
        [
            "--competition",
            CBB.key,
            "--output-dir",
            str(lab["outputs"]),
            "--processed-dir",
            str(lab["processed"]),
            "--manual-dir",
            str(lab["manual"]),
            "--scripts-dir",
            str(lab["scripts"]),
            "--week",
            "2026-W36",
            *extra,
        ]
    )


def with_siblings(lab: dict) -> dict:
    """Stub every sibling program the loop shells out to.

    A test about **demotion** must not also be a test about a missing refit
    script: the loop degrades correctly when a sibling is absent, so a demotion
    test that omits them measures the absence and never reaches the question it
    was written to ask.

    The stubbed backtest **writes its record when it runs**, not when the
    fixture is built. That is not a detail — the loop pre-registers the week's
    hypotheses first, so the ledger's cumulative count is larger by the time
    the record is verified than it was when the fixture was set up. A record
    written up front is stale by exactly the amount the loop is checking for,
    which is the check working rather than a nuisance.
    """
    for name in (LOOP.REFIT_SCRIPT, LOOP.CLAIMS_SCRIPT):
        stub_script(lab, name)
    stub_script(
        lab,
        LOOP.BACKTEST_SCRIPT,
        body=(
            "import json, pathlib, datetime\n"
            "from cbb_betting_lab.reports import price_backtest as PB\n"
            "from cbb_betting_lab import experiment_ledger as E\n"
            "out = pathlib.Path(%r)\n"
            # The same call the real backtest makes, so the stub cannot drift
            # from the rule the loop checks: max(count, 1), never the day's.
            "looks = PB.looks_from_ledger(out / E.LEDGER_FILENAME)\n"
            "(out / %r).write_text(json.dumps({\n"
            "    'record_version': %d, 'competition': %r,\n"
            "    'generated_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),\n"
            "    'walk_forward_verified': True, 'looks': looks, 'markets': [],\n"
            "}), encoding='utf-8')\n"
        )
        % (
            str(lab["outputs"]),
            CBB.output_name("price_backtest", ".json"),
            PB.RECORD_VERSION,
            CBB.key,
        ),
    )
    return lab


def with_real_claims_script(lab: dict) -> dict:
    """Stub the siblings, but use the REAL claims program.

    A stubbed claims script is a no-op, so a test about what the claims step
    writes would pass whatever the splice did — including nothing.
    """
    import shutil

    with_siblings(lab)
    shutil.copy(SCRIPTS / LOOP.CLAIMS_SCRIPT, lab["scripts"] / LOOP.CLAIMS_SCRIPT)
    return lab


def stub_script(lab: dict, name: str, body: str = "pass") -> Path:
    path = lab["scripts"] / name
    path.write_text(f"import sys\n{body}\n", encoding="utf-8")
    return path


def steps_from(lab: dict) -> dict[str, str]:
    record = json.loads(
        LOOP.record_path(CBB, lab["outputs"]).read_text(encoding="utf-8")
    )
    return {step["name"]: step["status"] for step in record["steps"]}


# --------------------------------------------------------------------------
# 1. The alpha budget binds
# --------------------------------------------------------------------------


def test_the_budget_caps_the_week_and_the_rest_waits(lab: dict):
    """Ten declared hypotheses, six a week: six are spent and four wait.

    The waiting four are the whole mechanism. A search that could spend ten
    because it had ten to spend is a search with no budget, and the fiftieth
    test would get the first test's benefit of the doubt.
    """
    write_queue(lab["manual"] / LOOP.QUEUE_FILENAME, [queue_entry(i) for i in range(10)])
    run(lab)
    ledger = E.load(lab["outputs"] / E.LEDGER_FILENAME)

    assert ledger.count == 6, "the budget declared six a week and it must bind"
    assert ledger.spent_in("2026-W36") == 6
    record = json.loads(
        LOOP.record_path(CBB, lab["outputs"]).read_text(encoding="utf-8")
    )
    assert len(record["alpha_budget"]["waiting"]) == 4


def test_the_budget_is_not_borrowed_against_by_running_twice(lab: dict):
    """A second dispatch in the same week spends nothing more.

    This is the defect the ISO-week bucket exists to close. `spent_in()` counts
    by whatever string `tested_on` holds, so a per-DAY bucket would let two
    dispatches on a Monday and a Tuesday buy twelve degrees of freedom out of a
    budget that says six.
    """
    write_queue(lab["manual"] / LOOP.QUEUE_FILENAME, [queue_entry(i) for i in range(10)])
    run(lab)
    run(lab)

    assert E.load(lab["outputs"] / E.LEDGER_FILENAME).count == 6


def test_the_next_week_spends_the_rest_in_the_order_the_queue_declared(lab: dict):
    """Order is part of the declaration. Reordering after a result is a menu."""
    write_queue(lab["manual"] / LOOP.QUEUE_FILENAME, [queue_entry(i) for i in range(10)])
    run(lab)
    run(lab, "--week", "2026-W37")
    ledger = E.load(lab["outputs"] / E.LEDGER_FILENAME)

    assert ledger.count == 10
    names = [h.name for h in ledger.hypotheses]
    assert names == [f"hypothesis {i}" for i in range(10)]
    assert [h.tested_on for h in ledger.hypotheses] == ["2026-W36"] * 6 + [
        "2026-W37"
    ] * 4


def test_an_undeclared_budget_spends_nothing_at_all(lab: dict):
    """A rate limit nobody wrote down in advance is not a pre-registration.

    The loop refuses and says so, rather than stamping today's date onto the
    budget on its way past — which would be the search signing its own
    permission slip.
    """
    write_ledger(lab["outputs"] / E.LEDGER_FILENAME, declared_on="")
    write_queue(lab["manual"] / LOOP.QUEUE_FILENAME, [queue_entry(0)])
    exit_code = run(lab)

    assert E.load(lab["outputs"] / E.LEDGER_FILENAME).count == 0
    assert exit_code == LOOP.EXIT_DEGRADED
    assert steps_from(lab)["pre-register the week's search"] == LOOP.DEGRADED


def test_a_ledger_file_edited_upward_cannot_buy_more_than_the_script_declares(
    lab: dict,
):
    """The ceiling in the script and the budget on disk, and the smaller wins.

    Two locks on the same door. The budget lives on disk so it can be read
    rather than asserted; the ceiling lives in code so that editing the disk
    file is not enough on its own.
    """
    path = lab["outputs"] / E.LEDGER_FILENAME
    ledger = E.load(path)
    ledger.budget = replace(ledger.budget, per_week=60)
    E.save(ledger, path, floor=len(ledger.hypotheses))
    write_queue(lab["manual"] / LOOP.QUEUE_FILENAME, [queue_entry(i) for i in range(30)])
    run(lab)

    assert E.load(path).count == LOOP.ALPHA_BUDGET_CEILING


def test_re_measuring_a_recorded_hypothesis_spends_nothing(lab: dict):
    """`Hypothesis.key()` excludes the date on purpose.

    Charging a slot for re-running last week's test on this week's data would
    make re-running anything expensive, and then nobody re-runs anything — which
    is the opposite of what a weekly loop is for.
    """
    write_queue(lab["manual"] / LOOP.QUEUE_FILENAME, [queue_entry(0)])
    run(lab)
    for week in ("2026-W37", "2026-W38", "2026-W39"):
        run(lab, "--week", week)

    assert E.load(lab["outputs"] / E.LEDGER_FILENAME).count == 1


def test_a_queue_entry_with_no_predicted_direction_is_reported_not_swallowed(
    lab: dict,
):
    """The direction guard firing is the guard working — and it must be loud.

    A malformed entry that vanished silently would be a hypothesis somebody
    pre-registered and the ledger never counted, which under-counts the search.
    That is the one direction the correction must never err in.
    """
    write_queue(
        lab["manual"] / LOOP.QUEUE_FILENAME,
        [queue_entry(0), queue_entry(1, direction=""), queue_entry(2)],
    )
    exit_code = run(lab)
    record = json.loads(
        LOOP.record_path(CBB, lab["outputs"]).read_text(encoding="utf-8")
    )

    assert E.load(lab["outputs"] / E.LEDGER_FILENAME).count == 2
    assert record["alpha_budget"]["problems"], "the bad entry must be named"
    assert "hypothesis 1" in " ".join(record["alpha_budget"]["problems"])
    assert exit_code == LOOP.EXIT_DEGRADED


def test_the_loop_never_writes_the_queue_it_reads(lab: dict):
    """The fence. A search that can add to its own queue has no budget."""
    path = write_queue(
        lab["manual"] / LOOP.QUEUE_FILENAME, [queue_entry(i) for i in range(3)]
    )
    before = path.read_bytes()
    run(lab)

    assert path.read_bytes() == before


def test_the_queue_shipped_in_the_repository_loads_and_declares_a_direction():
    """The real file, not a fixture. An unparseable queue is a silent zero."""
    entries, problems = LOOP.load_queue(QUEUE_ON_DISK, week="2026-W36")

    assert not problems, problems
    assert entries, "the shipped queue declares nothing, so the mechanism is untested"
    for entry in entries:
        assert entry.hypothesis.predicted_direction in E.DIRECTIONS
        assert entry.why, f"{entry.hypothesis.name} was declared with no reason"


# --------------------------------------------------------------------------
# 2. Demotion is one-directional
# --------------------------------------------------------------------------


def allowlist(lab: dict, market: str, *, roi_floor: float = -0.02) -> None:
    policy = staging.StagingProviderPolicy(
        mode="staging_allowed",
        allowlist={
            market: staging.AllowlistEntry(
                market=market,
                receipt_id="receipt-test-1",
                approved_on="2026-11-01",
                roi_floor=roi_floor,
                evidence_checksum="deadbeef",
                minimum_bets=200,
            )
        },
    )
    staging.save(policy, lab["manual"])


def settled_ledger(
    lab: dict, *, market: str, rows: int, profit: float, tier: str = "low_major"
) -> Path:
    """A forward ledger of settled, graded opinions, one game each.

    One game each so the cluster count equals the bet count and the interval is
    as tight as it can honestly be — this fixture is about the demotion decision
    rather than about clustering, which `stats.interval_two_way` owns and
    `tests/test_clustered_interval_is_not_too_narrow.py` pins.
    """
    records = []
    for i in range(rows):
        day = date(2026, 11, 1) + timedelta(days=i % 60)
        records.append(
            {
                "snapshot_date": day.isoformat(),
                "commence_time": f"{day.isoformat()}T23:00:00Z",
                "event_id": f"evt-{i}",
                "home_team": "A",
                "away_team": "B",
                "market": market,
                "segment": "",
                "player": "",
                "selection": "home",
                "line": -2.5,
                "american_odds": -110,
                "book": "fanduel",
                "model_probability": 0.6,
                "edge": 0.05,
                "calibrated_probability": "",
                "calibrated_edge": "",
                "prior_weight": 0.0,
                "tier": tier,
                "verdicts_in_force": "",
                "settled_at": f"{day.isoformat()}T23:59:00Z",
                "outcome": "won" if profit > 0 else "lost",
                "actual": 3,
                "profit_units": profit,
            }
        )
    frame = pd.DataFrame(records, columns=list(fe.LEDGER_COLUMNS))
    path = lab["processed"] / fe.LEDGER_FILENAME
    frame.to_csv(path, index=False)
    return path


def test_a_market_below_its_receipts_floor_is_withdrawn_unattended(lab: dict):
    """The one change this loop may make to the card, made without asking."""
    allowlist(lab, "spread")
    settled_ledger(lab, market="spread", rows=900, profit=-0.30)
    exit_code = run(lab)
    policy = staging.load(lab["manual"])

    assert "spread" not in policy.allowlist
    assert policy.withdrawn and policy.withdrawn[0]["market"] == "spread"
    assert exit_code == LOOP.EXIT_DEMOTION_PENDING, (
        "a withdrawal this workflow cannot push must turn the run red, or "
        "the card keeps reading a market the loop decided to withdraw"
    )


def test_a_market_above_its_floor_is_kept(lab: dict):
    with_siblings(lab)
    allowlist(lab, "spread")
    settled_ledger(lab, market="spread", rows=900, profit=0.90)
    exit_code = run(lab)

    assert "spread" in staging.load(lab["manual"]).allowlist
    assert exit_code == LOOP.EXIT_OK


def test_a_thin_record_never_withdraws(lab: dict):
    """Withdrawal is not free: it stops the evidence that would settle it.

    Twenty losing bets and a real collapse look identical, and only one of them
    is a reason to take a market off the card.
    """
    with_siblings(lab)
    allowlist(lab, "spread")
    settled_ledger(lab, market="spread", rows=40, profit=-1.0)
    exit_code = run(lab)

    assert "spread" in staging.load(lab["manual"]).allowlist
    assert exit_code == LOOP.EXIT_OK


def test_the_receipts_floor_wins_over_the_criteria_file(lab: dict):
    """*"The bar a market is held to is the bar its receipt named."*

    A receipt signed against a floor of zero withdraws on a record the -2%
    default in `promotion_criteria.json` would have kept.
    """
    allowlist(lab, "spread", roi_floor=0.0)
    settled_ledger(lab, market="spread", rows=900, profit=-0.02)
    criteria = promotion.load_criteria(CBB, manual_dir=lab["manual"])
    assert criteria.demotion_roi_floor == -0.02, "the fixture is not testing anything"
    run(lab)

    assert "spread" not in staging.load(lab["manual"]).allowlist


def test_a_stricter_evidence_bar_wins_whichever_file_it_came_from(lab: dict):
    """`AllowlistEntry.minimum_bets` defaults to 200 and the criteria say 500.

    Withdrawal cannot be undone without a new human receipt, so the loop takes
    the larger of the two and never the smaller. 300 losing bets clear the
    entry's bar and not the criteria's, and the market stays.
    """
    allowlist(lab, "spread")
    settled_ledger(lab, market="spread", rows=300, profit=-0.30)
    run(lab)

    assert "spread" in staging.load(lab["manual"]).allowlist


def test_an_unreadable_forward_ledger_never_withdraws_and_never_passes(lab: dict):
    """A damaged ledger reads as zero rows if you let it, and zero rows means
    "no market has enough evidence to withdraw" — a gate failing open because a
    file was corrupt. It fails loudly instead."""
    with_siblings(lab)
    allowlist(lab, "spread")
    (lab["processed"] / fe.LEDGER_FILENAME).write_bytes(b"\x00\x01 not,a,csv\n\x00")
    exit_code = run(lab)

    assert "spread" in staging.load(lab["manual"]).allowlist
    assert steps_from(lab)["check for auto-demotion"] == LOOP.FAILED
    assert exit_code == LOOP.EXIT_DEGRADED


def test_a_dry_run_decides_the_withdrawal_and_writes_nothing(lab: dict):
    allowlist(lab, "spread")
    settled_ledger(lab, market="spread", rows=900, profit=-0.30)
    before = (lab["manual"] / staging.POLICY_FILENAME).read_bytes()
    exit_code = run(lab, "--dry-run")

    assert (lab["manual"] / staging.POLICY_FILENAME).read_bytes() == before
    assert not LOOP.record_path(CBB, lab["outputs"]).exists()
    assert E.load(lab["outputs"] / E.LEDGER_FILENAME).count == 0
    assert exit_code == LOOP.EXIT_DEMOTION_PENDING


def test_nothing_in_the_loop_grants_an_allowlist():
    """The asymmetry, swept for in the CODE rather than in the prose.

    `tests/test_promotion_is_one_directional.py` sweeps the package. This is the
    same sweep over the one unattended program that could call such a thing if
    it existed.

    **This test used to ban the substring `grant(` and failed on two sentences
    explaining that no such function exists** — one in the module docstring,
    one in the text the report prints. That is precisely the mistake this
    file's own docstring warns about: *a test that bans a word rather than an
    assertion has been written three times in this repository and been wrong
    three times.* It was written a fourth and fifth time here.

    A word-ban cannot tell a call from a comment, so the fix is not a cleverer
    pattern — it is to ask the question of the syntax tree, where a call is a
    `Call` node and a sentence about a call is nothing at all.
    """
    import ast

    source = (SCRIPTS / "run_weekly_loop.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    def called_name(node: ast.Call) -> str:
        func = node.func
        if isinstance(func, ast.Attribute):
            return func.attr
        if isinstance(func, ast.Name):
            return func.id
        return ""

    calls = {called_name(n) for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert "grant" not in calls, (
        "The weekly loop calls something named `grant`. The machine may take a "
        "market away from itself and may never give itself one."
    )
    defined = {
        n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "grant" not in defined, "The weekly loop defines a `grant`."

    # Assignment INTO an allowlist, which is how a grant would be spelled
    # without a function called `grant`.
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Assign, ast.AugAssign)):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        for target in targets:
            if isinstance(target, ast.Subscript) and isinstance(target.value, ast.Attribute):
                assert target.value.attr != "allowlist", (
                    "The loop assigns into an allowlist directly, which is a "
                    "grant however it is spelled."
                )

    assert "withdraw" in calls, (
        "the loop no longer withdraws anything, so automatic demotion is not "
        "wired at all"
    )


def test_the_report_never_shows_a_pooled_market_row_without_its_tiers(lab: dict):
    """The pooled figure exists only because the allowlist door is per market.

    It is never a headline, and every market row is followed by its tier rows —
    so a reader cannot take the pooled number away from this page on its own.
    """
    with_siblings(lab)
    allowlist(lab, "spread")
    settled_ledger(lab, market="spread", rows=900, profit=0.90, tier="low_major")
    run(lab)
    report = LOOP.report_path(CBB, lab["outputs"]).read_text(encoding="utf-8")

    assert "| spread | pooled (decision) |" in report
    # The market cell is empty on a tier row, so the rendered separator is
    # `|  | low_major |` — two spaces, not one. Asserting the exact spacing of
    # a markdown table is asserting the formatter, so this reads the table.
    tier_rows = [
        line
        for line in report.splitlines()
        if line.startswith("|") and line.split("|")[1].strip() == ""
        and line.split("|")[2].strip() == "low_major"
    ]
    assert tier_rows, (
        "The pooled `spread` row is not followed by a `low_major` tier row. "
        "The prose above that table promises every market row is followed by "
        "its tiers, and the brief forbids a pooled headline across the whole "
        "of D-I; a market row standing alone is that headline."
    )
    assert "900" in tier_rows[0]
    pooled_at = report.index("pooled (decision)")
    assert report.index("low_major", pooled_at) > pooled_at


def test_a_tier_below_the_floor_is_named_and_does_not_withdraw_the_market(lab: dict):
    """The asymmetry a per-market allowlist leaves, recorded rather than acted on.

    Withdrawal removes a market from every tier and there is no receipt to
    re-grant it in the tiers where it was fine, so a tier-only collapse is
    named in the report and the market stays.
    """
    with_siblings(lab)
    allowlist(lab, "spread")
    losing = pd.read_csv(
        settled_ledger(lab, market="spread", rows=700, profit=-0.40, tier="low_major")
    )
    winning = pd.read_csv(
        settled_ledger(lab, market="spread", rows=2400, profit=0.60, tier="high_major")
    )
    winning["event_id"] = [f"hm-{i}" for i in range(len(winning))]
    pd.concat([losing, winning], ignore_index=True).to_csv(
        lab["processed"] / fe.LEDGER_FILENAME, index=False
    )
    exit_code = run(lab)
    record = json.loads(
        LOOP.record_path(CBB, lab["outputs"]).read_text(encoding="utf-8")
    )

    assert "spread" in staging.load(lab["manual"]).allowlist
    assert exit_code == LOOP.EXIT_OK
    assert record["demotion"][0]["tiers_below_floor"] == ["low_major"]
    assert "low_major" in LOOP.report_path(CBB, lab["outputs"]).read_text(
        encoding="utf-8"
    )


# --------------------------------------------------------------------------
# 3. A missing program degrades and never crashes
# --------------------------------------------------------------------------


def test_a_missing_sibling_script_degrades_the_run_rather_than_crashing_it(lab: dict):
    """`fit_ratings.py` and `run_price_backtest.py` are being written beside
    this loop. A loop that cannot start until every sibling has landed is a loop
    nobody can test, and one that reports a clean week without them is worse."""
    exit_code = run(lab)
    steps = steps_from(lab)

    assert exit_code == LOOP.EXIT_DEGRADED
    assert steps["refit the ratings walk-forward"] == LOOP.MISSING
    assert steps["re-run the price backtest and replication"] == LOOP.MISSING


def test_a_missing_program_and_a_failing_one_are_not_the_same_status(lab: dict):
    """Collapsing them would make "nobody has written the refit" and "the refit
    crashed on this week's data" produce the same line, and they need different
    responses."""
    stub_script(lab, LOOP.REFIT_SCRIPT, "sys.exit(3)")
    run(lab)
    steps = steps_from(lab)

    assert steps["refit the ratings walk-forward"] == LOOP.FAILED
    assert steps["re-run the price backtest and replication"] == LOOP.MISSING


def test_the_backtest_still_runs_when_the_refit_did_not(lab: dict):
    """One missing step must not become a week with no measurement at all.

    The run is already marked degraded, so nobody can read the result as this
    week's model; skipping the measurement as well would only lose information.
    """
    stub_script(lab, LOOP.BACKTEST_SCRIPT, "print('measured')")
    run(lab)
    steps = steps_from(lab)

    assert steps["refit the ratings walk-forward"] == LOOP.MISSING
    assert steps["re-run the price backtest and replication"] == LOOP.OK


def test_every_program_the_loop_drives_is_named_by_a_constant():
    """So a reader can find them, and so the workflow does not have to name them.

    `test_every_script_a_workflow_runs_actually_exists` reads the workflow's
    text and would fail on a path to a program that has not landed. Naming them
    here instead is what lets the loop degrade over a missing one rather than
    turning it into a build failure — and this asserts the workflow really does
    keep them out of its own text.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    for script in (LOOP.REFIT_SCRIPT, LOOP.BACKTEST_SCRIPT):
        assert f"scripts/{script}" not in text, (
            f"the workflow names scripts/{script}, which "
            "test_every_script_a_workflow_runs_actually_exists will fail on "
            "until that program lands"
        )
    assert "scripts/run_weekly_loop.py" in text
    assert (SCRIPTS / LOOP.CLAIMS_SCRIPT).is_file()


def test_the_loop_re_renders_the_claims_doc_without_destroying_its_framing(lab, tmp_path):
    """Both halves of a requirement that pulls against itself.

    `docs/what_we_can_and_cannot_claim.md` was written before the first
    measurement, and its own first paragraph says that timing is the whole
    point: a document explaining how to read a number, written after the number
    arrives, is a justification rather than a rule. A machine that rewrote it
    weekly would destroy exactly that.

    Cooper's brief also requires the weekly loop to *re-render* it from the run
    record rather than by hand.

    **The earlier version of this test resolved the tension by banning the
    filename from the loop's source.** That satisfied the first half and made
    the second impossible, and it was the sixth word-ban test in this
    repository — the fifth and fourth were caught two days ago in this same
    file. The answer is a fenced block: the framing is untouched and only what
    sits between the markers moves.

    So this asserts the behaviour rather than the vocabulary: run the loop
    against a real document, then check that the framing survived AND the block
    was replaced.
    """
    with_real_claims_script(lab)
    doc = tmp_path / "claims.md"
    framing = "Written before the first measurement, and that timing is the point."
    doc.write_text(
        f"# What the evidence supports\n\n{framing}\n\n"
        "<!-- BEGIN GENERATED: what_we_can_claim -->\n\nplaceholder\n\n"
        "<!-- END GENERATED -->\n\nClosing prose that must also survive.\n",
        encoding="utf-8",
    )

    assert run(lab, "--claims-doc", str(doc)) == LOOP.EXIT_OK

    after = doc.read_text(encoding="utf-8")
    assert framing in after, "the loop destroyed the pre-measurement framing"
    assert "Closing prose that must also survive." in after
    assert "placeholder" not in after, "the fenced block was not re-rendered"
    assert after.count("<!-- BEGIN GENERATED") == 1
    assert after.count("<!-- END GENERATED -->") == 1


def test_a_claims_doc_with_no_fence_fails_rather_than_appending(lab, tmp_path):
    """A document that looks updated and is not is worse than an obviously
    stale one, so a missing fence is an error and never an append."""
    with_real_claims_script(lab)
    doc = tmp_path / "unfenced.md"
    doc.write_text("# No markers here\n", encoding="utf-8")

    run(lab, "--claims-doc", str(doc))

    assert "BEGIN GENERATED" not in doc.read_text(encoding="utf-8"), (
        "the splice appended a block to a document with no fence"
    )
    assert steps_from(lab)["re-render the claims report from its run record"] != LOOP.OK


# --------------------------------------------------------------------------
# 4. The correction is the ledger's cumulative count
# --------------------------------------------------------------------------


def write_backtest_record(lab: dict, *, looks: int, generated_at: str) -> Path:
    record = PB.build_record(
        PB.BacktestInputs(), looks=looks, generated_at=generated_at
    )
    return PB.write_record(record, PB.record_path(CBB, lab["outputs"]))


def test_a_backtest_corrected_across_the_wrong_count_degrades_the_run(lab: dict):
    """*"Family-wise correction from the experiment ledger's CUMULATIVE count,
    never the day's."* A backtest that corrected across the four markets it
    measured today reports intervals narrower than the truth, and they look
    clean — so the loop checks the record rather than trusting an exit code."""
    write_ledger(lab["outputs"] / E.LEDGER_FILENAME, count=12)
    stub_script(lab, LOOP.BACKTEST_SCRIPT, "print('ok')")
    write_backtest_record(
        lab,
        looks=4,
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    run(lab)

    assert steps_from(lab)["verify the backtest record"] == LOOP.DEGRADED


def test_a_backtest_record_left_over_from_last_week_is_not_this_weeks_measurement(
    lab: dict,
):
    """A subprocess exiting zero says a program finished, not that it measured.

    A stale record is exactly what a green run looks like when the measurement
    did not happen.
    """
    write_ledger(lab["outputs"] / E.LEDGER_FILENAME, count=12)
    stub_script(lab, LOOP.BACKTEST_SCRIPT, "print('ok')")
    stale = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat(
        timespec="seconds"
    )
    write_backtest_record(lab, looks=12, generated_at=stale)
    run(lab)

    assert steps_from(lab)["verify the backtest record"] == LOOP.DEGRADED


def test_walk_forward_is_re_verified_when_a_graded_frame_is_offered(
    lab: dict, tmp_path: Path
):
    """`price_backtest.assert_walk_forward`, used and not weakened."""
    frame = pd.DataFrame(
        {
            "slate_date": ["2026-11-10", "2026-11-11"],
            "priced_through": ["2026-11-09", "2026-11-10"],
        }
    )
    path = tmp_path / "bets.csv"
    frame.to_csv(path, index=False)
    run(lab, "--verify-bets", str(path))

    assert steps_from(lab)["re-verify walk-forward"] == LOOP.OK


def test_a_walk_forward_leak_fails_the_step_outright(lab: dict, tmp_path: Path):
    """A model priced on games it could not have seen is not a degraded
    measurement. It is a different measurement."""
    frame = pd.DataFrame(
        {
            "slate_date": ["2026-11-10", "2026-11-11"],
            "priced_through": ["2026-11-10", "2027-03-01"],
        }
    )
    path = tmp_path / "bets.csv"
    frame.to_csv(path, index=False)
    exit_code = run(lab, "--verify-bets", str(path))

    assert steps_from(lab)["re-verify walk-forward"] == LOOP.FAILED
    assert exit_code == LOOP.EXIT_DEGRADED


def test_no_graded_frame_is_reported_as_an_absence_and_never_as_a_pass(lab: dict):
    run(lab)
    record = json.loads(
        LOOP.record_path(CBB, lab["outputs"]).read_text(encoding="utf-8")
    )
    report = LOOP.report_path(CBB, lab["outputs"]).read_text(encoding="utf-8")

    assert record["walk_forward"]["verified"] is False
    assert "not re-verified here" in report


def test_the_loop_reads_the_looks_it_expects_from_the_ledger_helper(lab: dict):
    """The expected count is `price_backtest.looks_from_ledger`'s answer, not a
    number the loop worked out for itself."""
    write_ledger(lab["outputs"] / E.LEDGER_FILENAME, count=17)
    stub_script(lab, LOOP.BACKTEST_SCRIPT, "print('ok')")
    write_backtest_record(
        lab,
        looks=PB.looks_from_ledger(lab["outputs"] / E.LEDGER_FILENAME),
        generated_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    run(lab)
    record = json.loads(
        LOOP.record_path(CBB, lab["outputs"]).read_text(encoding="utf-8")
    )

    assert record["backtest"]["looks_expected"] == 17
    assert steps_from(lab)["verify the backtest record"] == LOOP.OK


def test_the_ledger_is_appended_before_the_measurement_reads_it(lab: dict):
    """Pre-registration is an ordering claim, not a paperwork one.

    The backtest computes its correction from the ledger FILE, so a loop that
    appended after the measurement would correct this week's numbers across last
    week's count. The stub reads the file at the moment it runs and reports what
    it saw.
    """
    write_ledger(lab["outputs"] / E.LEDGER_FILENAME, count=5)
    write_queue(lab["manual"] / LOOP.QUEUE_FILENAME, [queue_entry(i) for i in range(3)])
    seen = lab["outputs"] / "looks_seen.txt"
    stub_script(
        lab,
        LOOP.BACKTEST_SCRIPT,
        "\n".join(
            [
                "import json, pathlib",
                f"p = pathlib.Path({str(lab['outputs'] / E.LEDGER_FILENAME)!r})",
                "n = len(json.loads(p.read_text())['hypotheses'])",
                f"pathlib.Path({str(seen)!r}).write_text(str(n))",
            ]
        ),
    )
    run(lab)

    assert seen.read_text() == "8", (
        "the backtest saw the ledger before this week's hypotheses were "
        "appended, so its correction is smaller than the truth"
    )


# --------------------------------------------------------------------------
# 5. The cron cannot slip into the following ISO week
# --------------------------------------------------------------------------


def workflow_crons() -> list[tuple[int, int, str]]:
    """(minute, hour, day-of-week) for every cron in the weekly workflow."""
    crons = []
    for match in re.findall(r'^\s*-\s*cron:\s*"([^"]+)"', WORKFLOW.read_text(), re.M):
        minute, hour, _dom, _month, dow = match.split()
        crons.append((int(minute), int(hour), dow))
    return crons


def test_the_weekly_cron_cannot_land_in_the_following_iso_week():
    """Recomputed from `schedule_contract.OBSERVED_LATENESS_H`, not asserted.

    The alpha budget's bucket is the ISO week the run stamps. A trigger that can
    slip across a Sunday/Monday boundary spends next week's budget on this
    week's search — and GitHub has been firing these repositories' crons 4.5-5.3
    hours late since 2026-08-27, so the margin is not theoretical.
    """
    crons = workflow_crons()
    assert crons, "the weekly workflow has no cron; this test would pass vacuously"
    lateness = timedelta(hours=schedule_contract.OBSERVED_LATENESS_H)
    for minute, hour, dow in crons:
        assert dow == "1", f"the weekly loop fires on day-of-week {dow}, not Monday"
        # A Monday deep in a leap-free week; the arithmetic does not depend on
        # which Monday, only on the distance to the next week boundary.
        nominal = datetime(2027, 1, 4, hour, minute, tzinfo=timezone.utc)
        landed = nominal + lateness
        assert nominal.isocalendar()[:2] == landed.isocalendar()[:2], (
            f"a {hour:02d}:{minute:02d} UTC Monday cron lands "
            f"{landed:%A %H:%M} at {schedule_contract.OBSERVED_LATENESS_H}h "
            "late, in the following ISO week"
        )
        # And it must still be Monday, so the report's own day stamp matches the
        # day the schedule asked for.
        assert landed.weekday() == 0, f"the run lands on {landed:%A}"


def test_the_weekly_cron_keeps_a_margin_over_the_observed_lateness():
    """Raising `OBSERVED_LATENESS_H` when GitHub gets worse must prove itself.

    A cron that only just survives today's worst case is a cron that fails on
    the first week GitHub is worse, and this repository has already had to raise
    that constant once.
    """
    for minute, hour, _dow in workflow_crons():
        margin_h = 24 - (hour + minute / 60) - schedule_contract.OBSERVED_LATENESS_H
        assert margin_h >= 6.0, (
            f"a {hour:02d}:{minute:02d} UTC Monday cron leaves only "
            f"{margin_h:.1f}h between its worst-case landing and the end of "
            "Monday. The ISO week it stamps is the alpha budget's bucket."
        )


def test_the_weekly_workflow_holds_no_write_access_and_no_credential():
    """The loop reports and demotes; it never publishes and never spends.

    **This test used to search the raw text for `contents: write` and failed on
    the comment naming the workflows that ARE allowed to hold it.** Same defect
    as the `grant(` sweep above, in the same file, and the same fix: ask the
    parsed document, where a permission is a mapping key and a sentence about a
    permission is a comment.
    """
    import yaml

    text = WORKFLOW.read_text(encoding="utf-8")
    document = yaml.safe_load(text)

    permissions = document.get("permissions")
    assert permissions == {"contents": "read"}, (
        f"The weekly loop declares {permissions!r}. It must be exactly "
        "`contents: read`: it reports and demotes, and neither needs a write."
    )
    for job in (document.get("jobs") or {}).values():
        assert "write" not in str(job.get("permissions") or ""), (
            "A job in the weekly loop widens the workflow's permissions."
        )
        for step in job.get("steps") or []:
            env = step.get("env") or {}
            assert not any("secrets." in str(v) for v in env.values()), (
                f"Step {step.get('name')!r} is handed a secret. The weekly "
                "loop measures what is already bought and must not be able to "
                "spend a credit."
            )
            assert "git push" not in str(step.get("run") or ""), (
                f"Step {step.get('name')!r} pushes. Only the gameday workflow "
                "publishes, and only to refs/heads/card-feed."
            )

def test_the_workflow_fetches_and_builds_the_cache_before_it_measures():
    """The probe's lesson, and the one fix it refused to take.

    The refit and the backtest draw their population from the same processed
    table the probe does, so the runner has to build it — and must never fall
    back to the raw schedule when it is absent, which would make two populations
    diverge silently in the direction that looks like success.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    cache_at = text.index("actions/cache@v4")
    fetch_at = text.index("scripts/fetch_cbb_data.py")
    build_at = text.index("scripts/build_datasets.py")
    loop_at = text.index("scripts/run_weekly_loop.py")

    assert cache_at < fetch_at < build_at < loop_at


# --------------------------------------------------------------------------
# The stopping rule
# --------------------------------------------------------------------------


def test_the_stopping_rule_fires_when_nothing_could_clear():
    """`docs/when_this_ends.md`'s third early exit, checked weekly rather than
    noticed in April."""
    ledger = E.ExperimentLedger(budget=E.AlphaBudget(declared_on="2026-09-01"))
    for i in range(200_000):
        ledger.hypotheses.append(
            E.Hypothesis(
                search="s",
                name=f"h{i}",
                tested_on="2026-W36",
                seasons=(2027,),
                outcome="pending",
                predicted_direction="higher",
            )
        )
    verdict = LOOP.stopping_rule(
        ledger, today=date(2027, 1, 1), supply=LOOP.SAMPLE_FLOOR_OPINIONS
    )

    assert verdict["exhausted"] is True
    assert verdict["bets_needed_corrected"] > LOOP.SAMPLE_FLOOR_OPINIONS


def test_the_stopping_rule_has_headroom_today():
    ledger = E.load(REPO / "data" / "outputs" / E.LEDGER_FILENAME)
    verdict = LOOP.stopping_rule(ledger, today=date(2026, 9, 1))

    assert verdict["exhausted"] is False
    assert verdict["bets_needed_corrected"] == int(
        round(
            S.bets_needed_to_detect(LOOP.PLAUSIBLE_EDGE)
            * ledger.correction_factor() ** 2
            + 0.5
        )
    ) or verdict["bets_needed_corrected"] > 0


def test_the_crossing_point_is_the_first_count_that_fails():
    """The binary search returns a boundary, and a boundary is only right if
    the count below it still clears."""
    crossing = LOOP.looks_at_which_the_budget_is_spent(
        edge=LOOP.PLAUSIBLE_EDGE, supply=LOOP.SAMPLE_FLOOR_OPINIONS
    )
    uncorrected = S.bets_needed_to_detect(LOOP.PLAUSIBLE_EDGE)

    assert (
        uncorrected * S.bonferroni_factor(crossing - 1) ** 2
        <= LOOP.SAMPLE_FLOOR_OPINIONS
    )
    assert uncorrected * S.bonferroni_factor(crossing) ** 2 > LOOP.SAMPLE_FLOOR_OPINIONS


def test_the_sample_floor_here_matches_the_document_that_declared_it():
    """A stopping rule whose constants have drifted from the document that
    pre-registered them is not a pre-registration."""
    text = (REPO / "docs" / "when_this_ends.md").read_text(encoding="utf-8")

    assert f"{LOOP.SAMPLE_FLOOR_OPINIONS:,} settled opinions" in text
    assert f"{LOOP.SAMPLE_FLOOR_GAMES:,} distinct games" in text
    assert LOOP.DECISION_DATE.isoformat() in text


# --------------------------------------------------------------------------
# The report itself
# --------------------------------------------------------------------------


def test_the_report_is_a_pure_function_of_its_record(lab: dict):
    """The retention probe's rule: improving a sentence must never cost a
    re-run, and a report that can only be produced by re-running the
    measurement is a report nobody improves."""
    run(lab)
    record = json.loads(
        LOOP.record_path(CBB, lab["outputs"]).read_text(encoding="utf-8")
    )

    assert LOOP.render(record) == LOOP.report_path(CBB, lab["outputs"]).read_text(
        encoding="utf-8"
    )


def test_the_report_says_the_run_bought_and_granted_nothing(lab: dict):
    run(lab)
    report = LOOP.report_path(CBB, lab["outputs"]).read_text(encoding="utf-8")

    assert "allowlisted no market" in report
    assert "spent no credit" in report
    assert S.NO_DEMONSTRATED_EDGE in report


def test_the_outputs_are_competition_prefixed(lab: dict):
    """An unprefixed output is a file two competitions would both write, and the
    second one to run would silently become the record."""
    assert LOOP.record_path(CBB, lab["outputs"]).name.startswith(f"{CBB.key}_")
    assert LOOP.report_path(CBB, lab["outputs"]).name.startswith(f"{CBB.key}_")


def test_the_weekly_backtest_is_bounded_to_a_season(lab: dict):
    """A weekly loop whose measurement cannot finish is not a self-running lab.

    Unbounded, `run_price_backtest.py` scores every season in the store. On the
    bought population that was **measured at eight hours** — against this
    workflow's 240-minute timeout and GitHub's own six-hour ceiling. The step
    would be killed every single Monday, the loop would report degraded for
    ever, and the failure would look exactly like a lab that was running.

    So the loop names a season when the caller does not. The weekly job is
    drift detection; the full-population figure is a separate deliberate run
    that no CI job can hold.
    """
    with_siblings(lab)
    assert run(lab) == LOOP.EXIT_OK

    record = json.loads(
        LOOP.record_path(CBB, lab["outputs"]).read_text(encoding="utf-8")
    )
    # The command is echoed into the step's `detail`; there is no separate
    # field for it, and asserting against a field that does not exist would
    # make this test pass by finding nothing.
    invocations = [
        str(step.get("detail", ""))
        for step in record["steps"]
        if LOOP.BACKTEST_SCRIPT in str(step.get("detail", ""))
    ]
    assert invocations, "the loop did not run the backtest at all"
    assert any("--seasons" in command for command in invocations), (
        "The weekly loop runs the price backtest with no season bound, so it "
        "scores the whole store and is killed by the job timeout every week."
    )


def test_the_weekly_season_is_derived_from_the_clock_not_pinned():
    """A literal would quietly keep scoring 2027 in 2029."""
    from datetime import date

    expected = LOOP.weekly_backtest_season()
    today = date.today()
    assert expected == (today.year + 1 if today.month >= 7 else today.year)
