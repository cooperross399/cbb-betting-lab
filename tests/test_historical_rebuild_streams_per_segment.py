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

The fix for **U** then introduced a third defect, and it is the one this file
mostly exists for now:

- **X.** The rebuild `unlink()`ed the store and *then* staged rows into the
  empty path. `stores.append` refuses to write fewer rows than it read — but
  with the target already deleted it always read **zero**, so the anti-shrink
  guard compared every rebuild against nothing and could never fire. The very
  comment above that unlink explained that the store had once shrunk from 2.9M
  rows to 2.3M, which is exactly the event that guard exists to catch. A
  rebuild that staged nothing at all then printed a warning and returned **0**:
  a green exit over a store that no longer existed.

`rebuild_store` builds beside the target, counts the previous store BEFORE
touching it, and renames only once the result is verified. Every test below
drives the real function; only `rebuild_from_cache` is faked, because the
suite carries no corpus of bought provider responses and buying one costs ten
times live rate.

The workflow-order defect (**S**) is pinned in `test_workflows.py`.
"""

from __future__ import annotations

import inspect

import pandas as pd
import pytest

from cbb_betting_lab import stores
from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.providers import historical as H
from cbb_betting_lab.reports import retention_probe as RP


WINDOW = H.CARD_WINDOW


def _event(index: int) -> RP.ProbeEvent:
    return RP.ProbeEvent(
        game_id=500_000 + index,
        season=2025,
        slate_date="2025-01-15",
        commence_time="2025-01-15T23:00:00Z",
        snapshot="2025-01-15T22:00:00Z",
        tier="high_major",
        month="2025-01",
        window="late",
        home_team_id=index,
        away_team_id=index + 1,
        home_name=f"h{index}",
        away_name=f"a{index}",
    )


def _segment(wave: str, season: int) -> H.PlanSegment:
    return H.PlanSegment(
        wave=wave,
        season=season,
        window=WINDOW.name,
        keys=("h2h",),
        keys_refused={},
        events=(_event(season),),
        regions=2,
        blocked_reason="",
    )


def _plan(*segments: H.PlanSegment) -> H.PurchasePlan:
    return H.PurchasePlan(segments=tuple(segments), window=WINDOW, seed=1)


def _row(quote: int) -> dict:
    """One staged price row, distinct from every other by `line`.

    Distinct on purpose: `append_prices` dedupes on the quote, so rows that
    differed only in some column outside `stores.PRICE_IDENTITY` would collapse
    into one and a test counting rows would be counting the deduper instead of
    the rebuild.
    """
    return {
        "event_id": "evt-1",
        "market": "moneyline",
        "segment": "full_game",
        "player": "",
        "selection": "home",
        "line": float(quote),
        "book": "bookone",
        "snapshot_phase": WINDOW.name,
        "american_odds": -110.0,
        "provider_key": "h2h",
        "game_id": 500_001,
        "season": 2025,
        "slate_date": "2025-01-15",
        "commence_time": "2025-01-15T23:00:00Z",
        "home_team": 1,
        "away_team": 2,
        "home_name": "h",
        "away_name": "a",
        "tier": "high_major",
        "tip_window": "late",
        "snapshot_requested": "2025-01-15T22:00:00Z",
        "lead_minutes": 60,
        "book_last_update": "2025-01-15T22:00:00Z",
    }


def _existing_store(processed_dir, quotes: range) -> "object":
    """Write a store the rebuild will be asked to replace, and return its path."""
    target = H.store_path(CBB, processed_dir, WINDOW)
    target.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.DataFrame([_row(q) for q in quotes], columns=list(H.PRICE_COLUMNS))
    frame.to_csv(target, index=False, lineterminator="\n")
    return target


def _fake_rebuild(rows_per_segment):
    """A `rebuild_from_cache` that answers from a dict, and records its calls."""
    calls: list[tuple[str, int]] = []

    def fake(*, plan, cache_dir, indexes, chunk_size=8, segments=None):
        assert segments is not None and len(segments) == 1, (
            "rebuild_store called rebuild_from_cache over more than one segment; "
            "every row of a wave as Python dicts is what OOM-killed the runner"
        )
        segment = segments[0]
        calls.append((segment.wave, int(segment.season)))
        quotes = rows_per_segment.get((segment.wave, int(segment.season)), ())
        return [_row(q) for q in quotes], {"unparseable_selection": 1}, list(segment.events)

    fake.calls = calls
    return fake


# ---------------------------------------------------------------------------
# The seam the streaming caller needs (defect T)
# ---------------------------------------------------------------------------


def test_rebuild_accepts_a_segment_filter():
    """Without it the only way to bound memory is to build one plan per
    segment, which is a second copy of the plan-building rule."""
    params = inspect.signature(H.rebuild_from_cache).parameters
    assert "segments" in params, (
        "rebuild_from_cache has no `segments` parameter, so a caller cannot "
        "stream a large wave one season at a time and a 4.8M-row wave will "
        "exhaust the runner again."
    )
    assert params["segments"].default is None, "segments must default to the whole plan"


def test_the_rebuild_streams_one_segment_at_a_time(tmp_path, monkeypatch):
    """THE ASSERTION FOR DEFECT T, AND IT IS ABOUT *WHEN* ROWS ARE WRITTEN.

    Counting `rebuild_from_cache` calls is not the streaming property. The
    version of this test that only counted them left the whole defect open:
    accumulate every segment's rows in a list and call `append_prices` once
    after the loop, and the call count, `segments_rebuilt`, `rows_staged` and
    `rows_held` are all identical while a 4.8M-row wave is held in memory as
    Python dicts again — which is what OOM-killed the runner and took 1,199,926
    credits of unpersisted responses with it.

    So the two are recorded on ONE timeline and the interleaving is what is
    asserted: build segment, write it, build the next, write that. The row
    counts per write differ (3 then 4) so a single hoisted write of 7 cannot
    masquerade as either of them.
    """
    events: list[tuple] = []
    real_append = H.append_prices

    def fake(*, plan, cache_dir, indexes, chunk_size=8, segments=None):
        assert segments is not None and len(segments) == 1, (
            "rebuild_store called rebuild_from_cache over more than one segment; "
            "every row of a wave as Python dicts is what OOM-killed the runner"
        )
        segment = segments[0]
        events.append(("built", segment.wave, int(segment.season)))
        quotes = {("core_team", 2024): range(3), ("core_team", 2025): range(3, 7)}
        rows = [_row(q) for q in quotes.get((segment.wave, int(segment.season)), ())]
        return rows, {"unparseable_selection": 1}, list(segment.events)

    def watched_append(rows, target, *, window):
        events.append(("wrote", len(rows)))
        return real_append(rows, target, window=window)

    monkeypatch.setattr(H, "rebuild_from_cache", fake)
    monkeypatch.setattr(H, "append_prices", watched_append)

    result = H.rebuild_store(
        plan=_plan(_segment("core_team", 2024), _segment("core_team", 2025)),
        cache_dir=tmp_path / "cache",
        indexes={},
        processed_dir=tmp_path / "processed",
    )

    assert events == [
        ("built", "core_team", 2024),
        ("wrote", 3),
        ("built", "core_team", 2025),
        ("wrote", 4),
    ], (
        "the rebuild did not write each segment's rows before building the "
        "next. Every other count in this test is identical when the append is "
        "hoisted out of the segment loop, which re-introduces defect T with "
        "the whole suite green."
    )
    assert result.segments_rebuilt == 2
    assert result.rows_staged == 7


def test_the_rebuild_derives_from_the_cache_and_not_from_the_stale_store(
    tmp_path, monkeypatch
):
    """Defect U. The rows the previous store held must not survive into the
    rebuilt one unless the cache put them there."""
    processed = tmp_path / "processed"
    _existing_store(processed, range(100, 103))
    monkeypatch.setattr(H, "rebuild_from_cache", _fake_rebuild({("core_team", 2025): range(10)}))

    result = H.rebuild_store(
        plan=_plan(_segment("core_team", 2025)),
        cache_dir=tmp_path / "cache",
        indexes={},
        processed_dir=processed,
    )

    held = stores.read_store(result.target, columns=H.PRICE_COLUMNS)
    assert result.rows_held == 10
    assert sorted(held["line"].tolist()) == [float(q) for q in range(10)], (
        "the stale store's rows are still in the rebuilt file, so the rebuild "
        "appended onto it rather than deriving from the cache"
    )


# ---------------------------------------------------------------------------
# Defect X: the guard that could not fire, and the green exit over a ruin
# ---------------------------------------------------------------------------


def test_a_rebuild_that_shrinks_the_store_is_refused(tmp_path, monkeypatch):
    """THE ONE THIS FILE EXISTS FOR. The store went from 2.9M rows to 2.3M
    once; `stores.append` refuses a shrink, and deleting the target first made
    its floor zero for ever."""
    processed = tmp_path / "processed"
    target = _existing_store(processed, range(20))
    monkeypatch.setattr(H, "rebuild_from_cache", _fake_rebuild({("core_team", 2025): range(5)}))

    with pytest.raises(H.PurchaseError) as raised:
        H.rebuild_store(
            plan=_plan(_segment("core_team", 2025)),
            cache_dir=tmp_path / "cache",
            indexes={},
            processed_dir=processed,
        )

    assert "5" in str(raised.value) and "20" in str(raised.value), (
        "the refusal does not name both counts, so an operator cannot see how "
        "much was about to be lost"
    )
    assert len(stores.read_store(target, columns=H.PRICE_COLUMNS)) == 20, (
        "the original store did not survive the refusal"
    )


def test_a_rebuild_that_stages_nothing_is_refused_rather_than_returning_zero(
    tmp_path, monkeypatch
):
    """An empty cache must not be the thing that destroys the store. This is
    the green-exit half of defect X and it is tested apart from the shrink
    half: a fixture that tripped both would prove which guard fired for
    neither."""
    processed = tmp_path / "processed"
    target = _existing_store(processed, range(4))
    monkeypatch.setattr(H, "rebuild_from_cache", _fake_rebuild({}))

    with pytest.raises(H.PurchaseError) as raised:
        H.rebuild_store(
            plan=_plan(_segment("core_team", 2025)),
            cache_dir=tmp_path / "cache",
            indexes={},
            processed_dir=processed,
        )

    assert "zero" in str(raised.value)
    assert len(stores.read_store(target, columns=H.PRICE_COLUMNS)) == 4


def test_an_empty_rebuild_over_no_store_at_all_is_still_refused(tmp_path, monkeypatch):
    """The shrink guard cannot fire here — there is nothing to shrink — so this
    is the case that proves the zero-row refusal is its own guard rather than
    the shrink guard wearing a different message."""
    monkeypatch.setattr(H, "rebuild_from_cache", _fake_rebuild({}))
    processed = tmp_path / "processed"

    with pytest.raises(H.PurchaseError, match="zero"):
        H.rebuild_store(
            plan=_plan(_segment("core_team", 2025)),
            cache_dir=tmp_path / "cache",
            indexes={},
            processed_dir=processed,
        )
    assert not H.store_path(CBB, processed, WINDOW).exists()


def test_a_refused_rebuild_leaves_no_scratch_file_behind(tmp_path, monkeypatch):
    """A half-built file beside the store is the next run's stale store."""
    processed = tmp_path / "processed"
    _existing_store(processed, range(20))
    monkeypatch.setattr(H, "rebuild_from_cache", _fake_rebuild({("core_team", 2025): range(5)}))

    with pytest.raises(H.PurchaseError):
        H.rebuild_store(
            plan=_plan(_segment("core_team", 2025)),
            cache_dir=tmp_path / "cache",
            indexes={},
            processed_dir=processed,
        )

    leftovers = sorted(p.name for p in processed.iterdir() if ".rebuilding" in p.name)
    assert not leftovers, f"the rebuild left {leftovers} beside the store"


def test_a_shrink_needs_a_written_reason_and_records_it(tmp_path, monkeypatch):
    """The opt-out is a reason, not a flag. An operator who means it writes
    why, and the result carries the sentence so the run that did it is
    identifiable afterwards."""
    processed = tmp_path / "processed"
    target = _existing_store(processed, range(20))
    monkeypatch.setattr(H, "rebuild_from_cache", _fake_rebuild({("core_team", 2025): range(5)}))

    result = H.rebuild_store(
        plan=_plan(_segment("core_team", 2025)),
        cache_dir=tmp_path / "cache",
        indexes={},
        processed_dir=processed,
        allow_shrink_reason="the 2021 cache was re-cut and 15 rows were duplicates",
    )

    assert result.rows_held == 5
    assert "re-cut" in result.shrink_allowed_because
    assert len(stores.read_store(target, columns=H.PRICE_COLUMNS)) == 5


def test_an_unreadable_previous_store_is_refused_rather_than_floored_at_zero(
    tmp_path, monkeypatch
):
    """A guard's floor has to come from somewhere real. A store that cannot be
    parsed has an unknown row count, and treating unknown as zero is how the
    shrink guard was disarmed the first time."""
    processed = tmp_path / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    target = H.store_path(CBB, processed, WINDOW)
    target.write_bytes(b"\x00\x01 not,a,csv\n\x00")
    monkeypatch.setattr(H, "rebuild_from_cache", _fake_rebuild({("core_team", 2025): range(5)}))

    with pytest.raises(H.PurchaseError, match="could not be read"):
        H.rebuild_store(
            plan=_plan(_segment("core_team", 2025)),
            cache_dir=tmp_path / "cache",
            indexes={},
            processed_dir=processed,
        )

    assert target.read_bytes() == b"\x00\x01 not,a,csv\n\x00"


def test_a_shrink_reason_does_not_also_disable_the_unreadable_store_refusal(
    tmp_path, monkeypatch
):
    """ONE FLAG DISARMED TWO DIFFERENTLY-NAMED GUARDS.

    `except stores.CorruptStoreError: if not allow_shrink_reason:` meant the
    flag whose help text is entirely about permitting a shrink also switched
    off the refusal to rebuild over a store nobody can count — and switching
    that off sets `previous_rows = None`, which makes the shrink comparison
    itself (`previous_rows is not None and ...`) skip as well. An operator
    permitting fifteen duplicate rows could replace a 2.9M-row store with
    12,000 rows and no floor would have run at all.
    """
    processed = tmp_path / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    target = H.store_path(CBB, processed, WINDOW)
    corrupt = b"\x00\x01 not,a,csv\n\x00"
    target.write_bytes(corrupt)
    monkeypatch.setattr(H, "rebuild_from_cache", _fake_rebuild({("core_team", 2025): range(5)}))

    with pytest.raises(H.PurchaseError, match="could not be read"):
        H.rebuild_store(
            plan=_plan(_segment("core_team", 2025)),
            cache_dir=tmp_path / "cache",
            indexes={},
            processed_dir=processed,
            allow_shrink_reason="the 2021 cache was re-cut and 15 rows were duplicates",
        )

    assert target.read_bytes() == corrupt, (
        "a reason written about a measured shrink replaced a store whose row "
        "count nobody could read, with no floor having run"
    )


def test_the_unreadable_store_has_its_own_written_opt_out(tmp_path, monkeypatch):
    """The escape hatch still exists — it is just a different, named decision,
    and the result records that NO floor ran under it. `previous_rows` is
    `None`, which is the shrink guard saying it had nothing to compare."""
    processed = tmp_path / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    target = H.store_path(CBB, processed, WINDOW)
    target.write_bytes(b"\x00\x01 not,a,csv\n\x00")
    monkeypatch.setattr(H, "rebuild_from_cache", _fake_rebuild({("core_team", 2025): range(5)}))

    result = H.rebuild_store(
        plan=_plan(_segment("core_team", 2025)),
        cache_dir=tmp_path / "cache",
        indexes={},
        processed_dir=processed,
        allow_unreadable_store_reason="the OOM-killed writer truncated the CSV",
    )

    assert result.previous_rows is None, (
        "the result claims a floor it did not have"
    )
    assert "OOM-killed" in result.unreadable_store_allowed_because
    assert result.shrink_allowed_because == "", (
        "the unreadable-store opt-out is being recorded as a shrink override, "
        "which is the two guards sharing one field again"
    )
    assert len(stores.read_store(target, columns=H.PRICE_COLUMNS)) == 5


def test_the_script_passes_each_opt_out_to_its_own_guard(tmp_path):
    """Read from the source: the rebuild branch needs a corpus the suite does
    not carry. Two flags, two parameters — a script that forwarded one flag to
    both would put the defect back a layer up."""
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "scripts" / "buy_historical_prices.py").read_text()
    rebuild = source[source.index("if args.rebuild:"):source.index("if not args.live:")]

    assert "allow_shrink_reason=args.allow_shrink_reason.strip()" in rebuild
    assert "allow_unreadable_store_reason=(" in rebuild
    assert "args.allow_unreadable_store_reason.strip()" in rebuild
    assert "--allow-unreadable-store-reason" in source, (
        "the second opt-out has no flag, so the only way to take it is to edit "
        "the source — which means in practice the refusal is unconditional and "
        "the help text says otherwise"
    )


def test_the_store_is_only_replaced_once_the_rebuild_is_verified(
    tmp_path, monkeypatch
):
    """The property the unlink destroyed, asserted directly: while the rebuild
    is running, the file on disk is still the OLD store."""
    processed = tmp_path / "processed"
    target = _existing_store(processed, range(20))
    seen: list[int] = []

    def fake(*, plan, cache_dir, indexes, chunk_size=8, segments=None):
        # Read the target mid-rebuild. It must still be the previous store.
        seen.append(len(stores.read_store(target, columns=H.PRICE_COLUMNS)))
        return [_row(q) for q in range(30)], {}, list(segments[0].events)

    monkeypatch.setattr(H, "rebuild_from_cache", fake)
    result = H.rebuild_store(
        plan=_plan(_segment("core_team", 2025)),
        cache_dir=tmp_path / "cache",
        indexes={},
        processed_dir=processed,
    )

    assert seen == [20], (
        "the store was already gone or already replaced while the rebuild was "
        "still staging rows"
    )
    assert result.previous_rows == 20
    assert len(stores.read_store(target, columns=H.PRICE_COLUMNS)) == 30


# ---------------------------------------------------------------------------
# The script's spelling of all of the above
# ---------------------------------------------------------------------------


def test_all_waves_is_a_recognised_spelling():
    """The workflow's rebuild step passes `--waves all`. If the script stops
    recognising it, the rebuild silently derives the store from nothing."""
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "scripts" / "buy_historical_prices.py").read_text()
    assert '"all"' in source or "'all'" in source, "`--waves all` is not handled"


def test_the_script_delegates_the_rebuild_rather_than_unlinking(tmp_path):
    """Read from the source, because the live rebuild branch needs a corpus the
    suite does not carry. Two things: the script must call `rebuild_store`, and
    it must not delete the target itself — a caller that unlinks first disarms
    every guard inside the function it then calls."""
    from pathlib import Path

    source = (Path(__file__).resolve().parents[1] / "scripts" / "buy_historical_prices.py").read_text()
    rebuild = source[source.index("if args.rebuild:"):source.index("if not args.live:")]

    assert "H.rebuild_store(" in rebuild, "the rebuild branch no longer calls rebuild_store"
    assert ".unlink()" not in rebuild, (
        "the script deletes the store before rebuilding it again. That is "
        "defect X: the anti-shrink guard's floor becomes zero and it can never "
        "refuse anything."
    )
    assert "return 4" in rebuild, (
        "a refused rebuild exits 0, so the workflow step goes green over a "
        "store that was not rebuilt"
    )
