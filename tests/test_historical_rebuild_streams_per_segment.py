"""The rebuild after the run that lost 1,199,926 credits.

Purchase run 33917619764 bought the ladders-and-halves wave, then the store
rebuild was OOM-killed on a 7GB runner two minutes in, and because every
persistence step sat after the rebuild, nothing from the run was saved. Two
defects in the rebuild itself made that worse and are pinned here:

- **T.** `rebuild_from_cache` held every row of the plan as Python dicts —
  4,811,004 for the lost wave — before anything was written. It now takes a
  `segments` filter so a caller can stream one wave-season at a time.
- **U.** The rebuild appended onto whatever stale store the cache restored,
  so after buying props the store held the original core team plus props and
  nothing from the two waves bought in between. A rebuild derives from the raw
  cache and starts from nothing.

The workflow-order defect (**S**) is pinned in `test_workflows.py`.
"""

from __future__ import annotations

import inspect

from cbb_betting_lab.providers import historical as H


def test_rebuild_accepts_a_segment_filter():
    """The seam the streaming caller needs. Without it the only way to bound
    memory is to build one plan per segment, which is a second copy of the
    plan-building rule."""
    params = inspect.signature(H.rebuild_from_cache).parameters
    assert "segments" in params, (
        "rebuild_from_cache has no `segments` parameter, so a caller cannot "
        "stream a large wave one season at a time and a 4.8M-row wave will "
        "exhaust the runner again."
    )
    assert params["segments"].default is None, "segments must default to the whole plan"


def test_the_script_rebuilds_one_segment_at_a_time_from_nothing():
    """Two properties of the `--rebuild` path, read from its source.

    A test that runs the real rebuild needs a cache of real responses, which
    the suite does not carry. What it can check is that the script (a) removes
    the stale store before appending and (b) drives `rebuild_from_cache` per
    segment — the two behaviours whose absence produced defects U and T.
    """
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "scripts" / "buy_historical_prices.py").read_text()
    rebuild = source[source.index("if args.rebuild:"):source.index("if not args.live:")]

    assert "target.unlink()" in rebuild, (
        "The rebuild does not remove the existing store first. A rebuild that "
        "appends onto a stale restored store is an append with a misleading "
        "name, and it is how the store shrank from 2.9M rows to 2.3M."
    )
    assert "for segment in plan.segments" in rebuild, "the rebuild does not iterate segments"
    assert "segments=[segment]" in rebuild, (
        "The rebuild calls rebuild_from_cache over the whole plan. Every row "
        "of a wave as Python dicts is what OOM-killed the runner."
    )
    assert rebuild.index("for segment in plan.segments") < rebuild.index("H.append_prices("), (
        "append_prices must be called inside the segment loop, or memory is "
        "still the whole plan"
    )


def test_all_waves_is_a_recognised_spelling():
    """The workflow's rebuild step passes `--waves all`. If the script stops
    recognising it, the rebuild silently derives the store from nothing."""
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "scripts" / "buy_historical_prices.py").read_text()
    assert '"all"' in source or "'all'" in source, "`--waves all` is not handled"
