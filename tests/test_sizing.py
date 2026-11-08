"""The size column follows the trust the model has earned (decision 87)."""

from __future__ import annotations

from cbb_betting_lab.models import sizing


def test_an_untrusted_or_unknown_tier_is_the_base_size():
    assert sizing.units(0.0) == sizing.BASE_UNITS
    assert sizing.units(None) == sizing.BASE_UNITS
    assert sizing.units(float("nan")) == sizing.BASE_UNITS
    assert sizing.units(-0.4) == sizing.BASE_UNITS


def test_earned_trust_sizes_up_in_steps_and_never_past_the_cap():
    assert sizing.units(0.37) == 0.35
    assert sizing.units(1.0) == sizing.MAX_UNITS
    assert sizing.units(5.0) == sizing.MAX_UNITS
    sizes = [sizing.units(w / 20) for w in range(21)]
    assert sizes == sorted(sizes)


def test_the_tracker_rule_is_untouched():
    """Cooper's 2026-11-04 rule: the site counts every bet at 0.25u."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "web" / "site_pages.py"
    spec = importlib.util.spec_from_file_location("_site_pages_for_sizing", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.TRACKED_STAKE == sizing.BASE_UNITS
