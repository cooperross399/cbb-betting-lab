"""Every provider key this lab has met is wired or deferred, never both, never silently dropped.

`markets.py` cited this file as failing the build for "a market the provider
serves and this file does not mention", and until 2026-09-04 it did not exist.
The honest width of what can be asserted from inside the repository:

* the two registries partition: no key is both wired and deferred, and
  `all_known_provider_keys()` is exactly their union;
* every key the retention probe actually asked the provider for — recorded
  in `data/outputs/cbb_retention_probe.json`, the one place this repository
  holds the provider's own answer — is known, and every key the probe
  reported as `unwired_provider_keys` is either now wired or deferred with a
  reason;
* every deferral carries a reason, and every wired market names the quantity
  it settles on and the table it reads it from.

What this cannot see: a key the provider serves that neither the registry
nor the probe record has ever named. That needs a provider catalogue this
repository does not hold; the probe record is the nearest thing to one, and
it is what is checked.
"""

from __future__ import annotations

import json
from pathlib import Path

from cbb_betting_lab import markets as M

PROBE_RECORD = Path(__file__).resolve().parents[1] / "data" / "outputs" / "cbb_retention_probe.json"


def test_no_provider_key_is_both_wired_and_deferred() -> None:
    wired = set(M.PROVIDER_KEY_TO_MARKET)
    deferred = set(M.DEFERRED_MARKETS)
    assert wired, "no wired provider key at all"
    assert deferred, "no deferred provider key at all"
    assert not wired & deferred, f"wired and deferred at once: {sorted(wired & deferred)}"
    assert M.all_known_provider_keys() == frozenset(wired | deferred)


def test_every_deferral_carries_a_reason() -> None:
    for key, reason in M.DEFERRED_MARKETS.items():
        assert isinstance(reason, str) and len(reason.split()) >= 4, f"{key} is deferred without a reason"


def test_every_wired_market_names_its_quantity_and_table() -> None:
    for market in M.MARKETS:
        assert market.provider_keys, f"{market.key} maps to no provider key"
        assert market.settles_on, f"{market.key} names no settlement quantity"
        assert market.settlement_table, f"{market.key} names no settlement table"
        for key in market.provider_keys:
            assert M.PROVIDER_KEY_TO_MARKET[key] == market.key


def test_every_key_the_probe_asked_for_is_known() -> None:
    """The provider's own answer, as recorded: nothing the probe asked for
    has since been dropped from the registries."""
    assert PROBE_RECORD.is_file(), f"{PROBE_RECORD} is tracked; its absence is a broken checkout"
    record = json.loads(PROBE_RECORD.read_text(encoding="utf-8"))
    asked = {key for market in record["markets"] for key in market["provider_keys"]}
    assert len(asked) >= 30, f"the probe record names {len(asked)} provider keys; expected the wired catalogue"
    unknown = sorted(asked - M.all_known_provider_keys())
    assert not unknown, f"the probe asked for provider keys this lab no longer knows: {unknown}"
    for market in record["markets"]:
        assert market["market"] in M.MARKETS_BY_KEY, f"the probe recorded {market['market']!r}, which is no longer wired"


def test_every_key_the_probe_found_unwired_is_now_wired_or_deferred() -> None:
    record = json.loads(PROBE_RECORD.read_text(encoding="utf-8"))
    unwired = record.get("unwired_provider_keys") or []
    names = [u if isinstance(u, str) else u.get("provider_key") or u.get("key") for u in unwired]
    missing = sorted(n for n in names if n and n not in M.all_known_provider_keys())
    assert not missing, f"the probe found provider keys nobody has wired or deferred since: {missing}"


def test_a_key_that_is_neither_settles_nothing() -> None:
    assert M.market_for_provider_key("player_fantasy_points_not_a_key") is None
    assert "player_fantasy_points_not_a_key" not in M.all_known_provider_keys()
