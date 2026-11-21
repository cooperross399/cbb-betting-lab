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


def _site():
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parents[1] / "web" / "site_pages.py"
    spec = importlib.util.spec_from_file_location("_site_pages_for_sizing", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_tracker_base_is_the_cards_base():
    """Cooper, 2026-11-20: the site counts every bet at 1u (to win 1u)."""
    assert _site().TRACKED_STAKE == sizing.BASE_UNITS == 1.0


def test_a_long_price_is_sized_by_quarter_kelly():
    """Cooper, 2026-11-20: quarter Kelly off the 1u base for the longer odds."""
    assert sizing.units(0.0, -150) == 1.0 and sizing.units(0.0, 199, 0.5) == 1.0
    assert sizing.units(1.0, 150) == sizing.MAX_UNITS, "below +200 the trust size stands"
    assert sizing.units(1.0, 300, 0.02) == 0.17, "trust never sizes a long price"
    assert sizing.units(0.0, 300, 0.10) == 0.83
    assert sizing.units(0.0, 400, 0.5) == sizing.KELLY_CAP
    assert sizing.units(0.0, 1500) == 0.03, "no edge kept: sized at the 2% bar"
    assert sizing.units(0.0, 900, -0.1) == 0.0
    assert sizing.units(0.0, None) == sizing.BASE_UNITS


def test_the_card_and_the_site_read_one_rule():
    module = _site()
    assert module.KELLY_FROM == sizing.KELLY_FROM
    assert module.KELLY_FRACTION == sizing.KELLY_FRACTION
    assert module.KELLY_BANKROLL == sizing.KELLY_BANKROLL
    assert module.KELLY_DEFAULT_EDGE == sizing.KELLY_DEFAULT_EDGE
    for price in (-300, 120, 199, 200, 350, 500, 501, 1500, 1501, 4000):
        for edge in (None, -0.05, 0.0, 0.02, 0.08, 0.3):
            expected = sizing.kelly_units(price, edge)
            expected = sizing.BASE_UNITS if expected is None else expected
            assert module.tracked_stake(price, edge) == expected, (price, edge)
