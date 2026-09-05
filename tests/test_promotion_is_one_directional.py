"""The machine may take a market away from itself and may never give itself one.

That asymmetry is the reason the rest of this lab can run unattended, and it is
the one property here worth a test of its own rather than a comment.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cbb_betting_lab import promotion as P
from cbb_betting_lab import staging_provider_policy as SPP

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture()
def criteria():
    return P.load_criteria()


def test_there_is_no_way_to_grant_an_allowlist_anywhere():
    """`withdraw()` exists in the policy module and `grant()` does not. An
    automated system that can grant its own permissions is safe only if its
    judgment is right; one that can only withdraw is safe by construction."""
    assert hasattr(SPP, "withdraw")
    for module in (SPP, P):
        for forbidden in ("grant", "allow", "approve", "promote_market"):
            assert not hasattr(module, forbidden), (
                f"{module.__name__}.{forbidden} exists. Allowlisting a market "
                "requires a receipt Cooper signs; that is the single human "
                "stop in this project."
            )


def test_the_criteria_are_read_from_disk_and_never_defaulted(tmp_path):
    """A missing criteria file must raise, not fall back. Defaults are how a
    pre-registered threshold quietly becomes whatever the code says today."""
    with pytest.raises(P.PromotionError):
        P.load_criteria(manual_dir=tmp_path)


def test_the_criteria_were_declared_before_anything_was_measured(criteria):
    payload = json.loads(P.criteria_path().read_text(encoding="utf-8"))
    assert payload["declared_on"] == "2026-09-01"
    assert payload["why"], "The criteria must record why they are what they are."


def test_margin_is_compared_in_the_same_unit_it_is_declared_in():
    """ROI is a fraction (0.02 = 2%); the criteria are points (1.5 = 1.5%).

    The first version compared them directly and was a hundred times too
    strict, so no challenger could ever have been promoted — and it would have
    read as 'nothing clears the bar', which is exactly the answer this lab
    expects. Nothing would have looked wrong.
    """
    r = P.SeasonResult(
        season=2025, bets=5000,
        champion_roi=-0.030, challenger_roi=-0.005,
        challenger_low=-0.02, challenger_high=0.01,
    )
    assert r.margin_points == pytest.approx(2.5)


def test_a_challenger_must_clear_every_season_not_the_average(criteria):
    """Pooling lets one good season carry two bad ones. The football lab's
    verdict for one policy flipped depending on which season ran last."""
    good = P.SeasonResult(2025, 5000, -0.05, 0.02, 0.010, 0.030)   # +7.0 points
    bad = P.SeasonResult(2024, 5000, -0.02, -0.02, -0.04, 0.00)    # +0.0 points
    verdict = P.judge([good, bad], criteria=criteria, correction_factor=1.0)
    assert not verdict.promoted
    assert any("margin" in r for r in verdict.reasons)


def test_the_correction_is_applied_before_the_interval_is_read(criteria):
    """A challenger whose raw interval excludes zero and whose corrected one
    does not has not cleared anything."""
    narrow = P.SeasonResult(2025, 5000, -0.05, 0.02, 0.001, 0.039)
    assert P.judge([narrow], criteria=criteria, correction_factor=1.0).promoted
    corrected = P.judge([narrow], criteria=criteria, correction_factor=1.60)
    assert not corrected.promoted
    assert any("includes zero" in r for r in corrected.reasons)


def test_a_thin_season_is_not_enough_evidence_rather_than_a_result(criteria):
    thin = P.SeasonResult(2025, 100, -0.05, 0.05, 0.02, 0.08)
    verdict = P.judge([thin], criteria=criteria, correction_factor=1.0)
    assert not verdict.promoted
    assert any("not enough evidence" in r for r in verdict.reasons)


def test_demotion_needs_the_whole_interval_below_the_floor(criteria):
    """An interval that still reaches the floor has not demonstrated the
    market fell through it."""
    fires, why = P.should_demote(
        roi=-0.05, low=-0.08, high=-0.03, bets=1000, criteria=criteria
    )
    assert fires and "sits below" in why

    holds, why = P.should_demote(
        roi=-0.03, low=-0.09, high=0.01, bets=1000, criteria=criteria
    )
    assert not holds and "still reaches it" in why


def test_demotion_will_not_fire_on_noise(criteria):
    """Withdrawal is not free: it stops the forward evidence that would settle
    the question, and a withdrawn market cannot be re-granted without a new
    human receipt."""
    fires, why = P.should_demote(
        roi=-0.50, low=-0.90, high=-0.40, bets=20, criteria=criteria
    )
    assert not fires
    assert "noise" in why


def test_no_input_makes_should_demote_grant_anything(criteria):
    """The function has one direction. Sweeping the whole input space, it
    never returns anything that could be read as an approval."""
    for roi in (-1.0, -0.1, 0.0, 0.1, 1.0):
        for bets in (0, 499, 500, 100000):
            fires, _ = P.should_demote(
                roi=roi, low=roi - 0.05, high=roi + 0.05, bets=bets, criteria=criteria
            )
            assert fires in (True, False)
            if fires:
                assert roi + 0.05 < criteria.demotion_roi_floor
                assert bets >= criteria.demotion_minimum_bets


def test_saving_an_allowlist_without_a_receipt_grants_nothing_after_load(tmp_path):
    """The door is a receipt file, not a JSON field.

    `save()` will faithfully write a policy whose `mode` is not manual-only and
    whose allowlist names a market — that is what a machine `withdraw()` then
    `save()` needs. What it cannot do is make that market **allowed**: `load()`
    requires a human acceptance receipt under
    `<manual_dir>/human_acceptance_receipts/` behind every allowlisted market,
    and with none there the whole policy comes back manual-only, saying which
    market lacked what. Until 2026-09-05 nothing anywhere read that directory.
    """
    manual = tmp_path / "data" / "manual"
    manual.mkdir(parents=True)
    policy = SPP.StagingProviderPolicy(
        mode="reviewed",
        allowlist={
            "spread": SPP.AllowlistEntry(
                market="spread", receipt_id="r-1", approved_on="2026-11-01",
                roi_floor=-0.02, evidence_checksum="deadbeef",
            )
        },
    )
    assert policy.allows("spread"), "an in-memory policy is the test seam and must still work"

    SPP.save(policy, manual)
    loaded = SPP.load(manual)

    assert loaded.mode == SPP.MANUAL_ONLY
    assert loaded.declared_mode == "reviewed"
    assert not loaded.allows("spread")
    assert not any(loaded.allows(m) for m in ("spread", "moneyline", "total_points", ""))
    assert "spread" in loaded.allowlist, "the entry is kept so withdraw() can still act on it"
    assert "spread" in loaded.receipt_failures
    assert "receipt" in loaded.receipt_failures["spread"]
    from cbb_betting_lab.competitions import CBB
    line = loaded.summary_line(CBB)
    assert "manual-only" in line and "`spread` lacks" in line

    # Saving the loaded object back and re-loading changes nothing: the human's
    # declared mode is preserved, and the door stays shut.
    SPP.save(loaded, manual)
    again = SPP.load(manual)
    assert json.loads((manual / SPP.POLICY_FILENAME).read_text())["mode"] == "reviewed"
    assert again.mode == SPP.MANUAL_ONLY and not again.allows("spread")


def test_the_policy_module_never_writes_a_receipt(tmp_path):
    """Nothing in the module opens the receipts directory for writing. Checked
    on the syntax tree — a call is a `Call` node, a sentence about one is not."""
    import ast
    import inspect

    source = inspect.getsource(SPP)
    tree = ast.parse(source)
    writers = {"write_text", "write_bytes", "mkdir", "open", "dump", "touch", "rename", "replace"}
    calls = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr in writers
    ]
    # `save()` writes the policy file and nothing else; every write call in the
    # module must be inside it.
    save_node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "save")
    inside_save = {id(n) for n in ast.walk(save_node)}
    outside = [c for c in calls if id(c) not in inside_save]
    assert not outside, [ast.unparse(c) for c in outside]
