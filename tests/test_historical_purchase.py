"""Every prefix of the purchase order is a proportional sample of the wave.

`providers/historical.py` cited this file as asserting `stratified_order`'s
property "directly, at every prefix length, on all three axes", and until
2026-09-04 it did not exist. The property is what makes a run that stops at
the credit cap a **sample of the wave** rather than a prefix of it: if the
order were by game id, a capped run would buy November and nothing else, and
the retention verdicts would be verdicts about one month.

Asserted, for a synthetic wave with deliberately unequal cells: at every
prefix length `k`, every cell holds `k * n_c / N` events to within one, and
the same holds marginally on each of the three axes. Then determinism: the
same input gives the same order, so a resumed run walks the same files.
"""

from __future__ import annotations

import itertools
from collections import Counter

from cbb_betting_lab.providers import historical as H
from cbb_betting_lab.reports import retention_probe as RP

TIERS = ("high_major", "mid_major", "low_major")
MONTHS = ("2025-11", "2025-12", "2026-01", "2026-02", "2026-03")
WINDOWS = ("early", "late")


def _event(index: int, tier: str, month: str, window: str) -> RP.ProbeEvent:
    return RP.ProbeEvent(
        game_id=400_000 + index, season=2026, slate_date=f"{month}-15",
        commence_time=f"{month}-15T23:00:00Z", snapshot=f"{month}-15T22:00:00Z",
        tier=tier, month=month, window=window,
        home_team_id=index, away_team_id=index + 1, home_name=f"h{index}", away_name=f"a{index}",
    )


def _wave() -> list[RP.ProbeEvent]:
    """Unequal cells on purpose: a wave whose cells are all the same size
    would be proportional under an order that merely alternated."""
    events: list[RP.ProbeEvent] = []
    index = 0
    for tier, month, window in itertools.product(TIERS, MONTHS, WINDOWS):
        size = {"high_major": 9, "mid_major": 6, "low_major": 3}[tier] + (2 if window == "late" else 0)
        for _ in range(size):
            events.append(_event(index, tier, month, window))
            index += 1
    return events


def _assert_proportional(ordered: list[RP.ProbeEvent], key, *, tolerance: float = 1.0) -> None:
    """Every prefix holds `k * n_c / N` of each group to within `tolerance`.

    The guarantee `stratified_order` makes is per CELL, to within one event.
    A marginal on one axis is a sum over the cells sharing that axis value,
    and each of those may be off by one in the same direction, so the honest
    bound on a marginal is the number of cells it sums — not one. Asserted at
    that width rather than at a width the construction does not promise.
    """
    total = len(ordered)
    sizes = Counter(key(e) for e in ordered)
    running: Counter = Counter()
    for k, event in enumerate(ordered, start=1):
        running[key(event)] += 1
        for cell, n_c in sizes.items():
            expected = k * n_c / total
            assert abs(running[cell] - expected) <= tolerance + 1e-9, (
                f"at prefix {k} of {total}, group {cell!r} holds {running[cell]} events "
                f"against a proportional {expected:.2f} (tolerance {tolerance})"
            )


def test_every_prefix_is_a_proportional_sample_of_every_cell() -> None:
    wave = _wave()
    ordered = list(H.stratified_order(wave))
    assert sorted(e.game_id for e in ordered) == sorted(e.game_id for e in wave), "the order lost or duplicated an event"
    _assert_proportional(ordered, key=lambda e: e.stratum)


def test_every_prefix_is_proportional_on_each_axis_alone() -> None:
    """The marginals, at the width the cell property implies: a tier sums
    the cells of every (month, window), so its bound is that count."""
    ordered = list(H.stratified_order(_wave()))
    cells_per = {"tier": len(MONTHS) * len(WINDOWS), "month": len(TIERS) * len(WINDOWS), "window": len(TIERS) * len(MONTHS)}
    for axis, cells in cells_per.items():
        _assert_proportional(ordered, key=lambda e, axis=axis: getattr(e, axis), tolerance=cells)


def test_a_game_id_order_would_not_have_this_property() -> None:
    """The control: the naive order fails the assertion, so passing it above
    is evidence about `stratified_order` and not about the wave."""
    wave = sorted(_wave(), key=lambda e: e.game_id)
    total = len(wave)
    sizes = Counter(e.month for e in wave)
    running: Counter = Counter()
    worst = 0.0
    for k, event in enumerate(wave, start=1):
        running[event.month] += 1
        for cell, n_c in sizes.items():
            worst = max(worst, abs(running[cell] - k * n_c / total))
    assert worst > 1.0, "the naive order is proportional too, so this wave proves nothing"


def test_the_order_is_deterministic_and_seeded() -> None:
    wave = _wave()
    first = [e.game_id for e in H.stratified_order(wave)]
    second = [e.game_id for e in H.stratified_order(list(reversed(wave)))]
    assert first == second, "the order depends on input order, so a resumed run would not walk the same files"
    other = [e.game_id for e in H.stratified_order(wave, seed=H.DEFAULT_SEED + 1)]
    assert other != first, "a different seed gives the same order; the within-cell shuffle is not seeded"
    assert sorted(other) == sorted(first)


def test_an_empty_wave_orders_to_nothing_rather_than_raising() -> None:
    assert list(H.stratified_order([])) == []
