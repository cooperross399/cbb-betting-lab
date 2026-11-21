"""The size column follows the trust the model has earned (decision 87)."""

from __future__ import annotations

from cbb_betting_lab.models import sizing


def test_an_untrusted_or_unknown_tier_is_the_base_size():
    assert sizing.units(0.0) == sizing.BASE_UNITS
    assert sizing.units(None) == sizing.BASE_UNITS
    assert sizing.units(float("nan")) == sizing.BASE_UNITS
    assert sizing.units(-0.4) == sizing.BASE_UNITS


def test_earned_trust_sizes_up_in_steps_and_never_past_the_cap():
    assert sizing.units(0.37) == 1.4
    assert sizing.units(1.0) == sizing.MAX_UNITS
    assert sizing.units(5.0) == sizing.MAX_UNITS
    sizes = [sizing.units(w / 20) for w in range(21)]
    assert sizes == sorted(sizes)


def test_the_tracker_rule_is_untouched():
    """Cooper's rule, 1u since 2026-11-21: the site counts every bet at the card's base."""
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "web" / "site_pages.py"
    spec = importlib.util.spec_from_file_location("_site_pages_for_sizing", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.TRACKED_STAKE == sizing.BASE_UNITS


def test_a_long_price_is_sized_by_the_nhl_due_list_ladder():
    """Cooper, 2026-11-11: the NHL Due List's price ranges, .25u/.15u/.1u/.05u."""
    assert sizing.units(0.0, -150) == 1.0 and sizing.units(0.0, 199) == 1.0
    assert sizing.units(1.0, 150) == sizing.MAX_UNITS, "below +200 the trust size stands"
    assert sizing.units(1.0, 200) == 0.6 and sizing.units(0.0, 500) == 0.6
    assert sizing.units(0.0, 501) == 0.4 and sizing.units(0.0, 1500) == 0.4
    assert sizing.units(0.0, 1501) == 0.2 and sizing.units(0.0, 5000) == 0.2
    assert sizing.units(0.0, None) == sizing.BASE_UNITS


def test_the_card_and_the_site_read_one_ladder():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "web" / "site_pages.py"
    spec = importlib.util.spec_from_file_location("_site_pages_for_ladder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.STAKE_BRACKETS == sizing.PRICE_BRACKETS
    assert module.STAKE_LONGEST == sizing.LONGEST_UNITS
    for price in (-300, 120, 199, 200, 350, 500, 501, 1500, 1501, 4000):
        expected = sizing.ladder_units(price) or sizing.BASE_UNITS
        assert module.tracked_stake(price) == expected, price
