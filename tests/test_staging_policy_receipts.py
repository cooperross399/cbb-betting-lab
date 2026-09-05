"""A market is allowed by a receipt on disk that checks out, not by a JSON field.

`staging_provider_policy.allows()` read `mode != manual_only and market in
allowlist`, and nothing in the repository opened
`data/manual/human_acceptance_receipts/`. The brief's single human stop — *"I
sign the acceptance receipt that allowlists a market"* — was therefore a string
in a file a script could have written. These tests build synthetic receipts in
temporary directories and hold `load()` to the rule: every allowlisted market
needs a receipt that names it, cites an evidence record whose sha256 matches the
bytes on disk, is signed by a person who is not Claude, and is dated. One market
lacking any of that shuts the whole door.

Nothing here touches `data/manual/`, and nothing here writes a receipt into the
repository. `tmp_path` throughout.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cbb_betting_lab import staging_provider_policy as SPP
from cbb_betting_lab.competitions import CBB

REPO = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# A synthetic lab: <root>/data/manual, receipts beside the policy, evidence
# under <root>/data/outputs. Receipts cite the evidence relative to <root>.
# ---------------------------------------------------------------------------


@pytest.fixture()
def root(tmp_path: Path) -> Path:
    (tmp_path / "data" / "manual" / SPP.RECEIPTS_DIRNAME).mkdir(parents=True)
    (tmp_path / "data" / "outputs").mkdir(parents=True)
    return tmp_path


def manual(root: Path) -> Path:
    return root / "data" / "manual"


def evidence(root: Path, name: str = "cbb_price_backtest.json", body: bytes = b'{"roi": -0.039}\n') -> tuple[str, str]:
    """Write an evidence record; return its repo-relative path and sha256."""
    path = root / "data" / "outputs" / name
    path.write_bytes(body)
    return f"data/outputs/{name}", hashlib.sha256(body).hexdigest()


def entry(market: str, receipt_id: str = "r-spread-1") -> SPP.AllowlistEntry:
    return SPP.AllowlistEntry(
        market=market, receipt_id=receipt_id, approved_on="2026-12-01",
        roi_floor=-0.02, evidence_checksum="", minimum_bets=200,
    )


def policy_with(root: Path, *markets: str, receipt_id: str = "r-spread-1") -> None:
    policy = SPP.StagingProviderPolicy(
        mode="reviewed",
        allowlist={m: entry(m, receipt_id if len(markets) == 1 else f"r-{m}") for m in markets},
    )
    SPP.save(policy, manual(root))


def receipt(root: Path, filename: str = "r-spread-1.json", **overrides) -> Path:
    rel, digest = evidence(root)
    payload = {
        "receipt_id": "r-spread-1",
        "market": "spread",
        "evidence": {"path": rel, "sha256": digest},
        "signed_by": "Cooper Ross",
        "signed_on": "2026-12-01",
        "note": "synthetic, in a temporary directory, for a test",
    }
    payload.update(overrides)
    path = manual(root) / SPP.RECEIPTS_DIRNAME / filename
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# The door opens for exactly one shape of receipt
# ---------------------------------------------------------------------------


def test_a_valid_receipt_behind_the_market_allows_it(root):
    policy_with(root, "spread")
    path = receipt(root)
    loaded = SPP.load(manual(root))

    assert loaded.mode == "reviewed"
    assert loaded.receipt_failures == {}
    assert loaded.allows("spread")
    assert not loaded.allows("moneyline"), "only the allowlisted market is allowed"
    assert loaded.receipts == {"spread": str(path)}
    line = loaded.summary_line(CBB)
    assert "allowlists 1 market(s): spread" in line
    assert "verified human acceptance receipt" in line


def test_the_evidence_may_be_cited_flat_or_nested(root):
    policy_with(root, "spread")
    rel, digest = evidence(root)
    receipt(root, evidence=None, evidence_path=rel, evidence_sha256=digest)
    assert SPP.load(manual(root)).allows("spread")


def test_an_absolute_evidence_path_is_accepted(root):
    policy_with(root, "spread")
    rel, digest = evidence(root)
    receipt(root, evidence={"path": str(root / rel), "sha256": digest})
    assert SPP.load(manual(root)).allows("spread")


# ---------------------------------------------------------------------------
# Every way a receipt can be lacking shuts the WHOLE door and says why
# ---------------------------------------------------------------------------


def assert_manual_only(loaded: SPP.StagingProviderPolicy, market: str, *words: str) -> None:
    assert loaded.mode == SPP.MANUAL_ONLY
    assert loaded.declared_mode == "reviewed"
    assert not loaded.allows(market)
    assert market in loaded.receipt_failures, loaded.receipt_failures
    reason = loaded.receipt_failures[market]
    for word in words:
        assert word in reason, f"{word!r} not in reason {reason!r}"
    line = loaded.summary_line(CBB)
    assert "manual-only, forced" in line
    assert f"`{market}` lacks" in line
    for word in words:
        assert word in line
    assert "produces no selection" in line


def test_no_receipt_directory_is_manual_only(root):
    policy_with(root, "spread")
    (manual(root) / SPP.RECEIPTS_DIRNAME).rmdir()
    assert_manual_only(SPP.load(manual(root)), "spread", "receipt directory")


def test_an_empty_receipt_directory_is_manual_only(root):
    policy_with(root, "spread")
    assert_manual_only(SPP.load(manual(root)), "spread", "any receipt", "there is none")


def test_a_receipt_naming_another_market_is_manual_only(root):
    policy_with(root, "spread")
    receipt(root, market="moneyline")
    assert_manual_only(SPP.load(manual(root)), "spread", "naming market `spread`")


def test_a_receipt_with_another_receipt_id_is_manual_only(root):
    """The entry says which receipt it rests on; a different one does not count."""
    policy_with(root, "spread", receipt_id="r-spread-2")
    receipt(root)  # r-spread-1
    assert_manual_only(SPP.load(manual(root)), "spread", "receipt_id `r-spread-2`")


def test_a_receipt_whose_evidence_is_missing_from_disk_is_manual_only(root):
    policy_with(root, "spread")
    receipt(root, evidence={"path": "data/outputs/never_written.json", "sha256": "0" * 64})
    assert_manual_only(SPP.load(manual(root)), "spread", "does not exist")


def test_a_receipt_whose_evidence_hash_does_not_match_is_manual_only(root):
    """The NHL lab's own catch, made mandatory: the receipt was signed against
    one set of numbers and the file now holds another."""
    policy_with(root, "spread")
    rel, _ = evidence(root)
    receipt(root, evidence={"path": rel, "sha256": hashlib.sha256(b"other numbers").hexdigest()})
    assert_manual_only(SPP.load(manual(root)), "spread", "hashes to")


def test_evidence_that_moves_after_signing_shuts_the_door(root):
    """Valid at signing, then the record is re-rendered with different bytes."""
    policy_with(root, "spread")
    receipt(root)
    assert SPP.load(manual(root)).allows("spread")
    (root / "data" / "outputs" / "cbb_price_backtest.json").write_bytes(b'{"roi": -0.016}\n')
    assert_manual_only(SPP.load(manual(root)), "spread", "hashes to")


def test_a_receipt_citing_no_evidence_is_manual_only(root):
    policy_with(root, "spread")
    receipt(root, evidence=None)
    assert_manual_only(SPP.load(manual(root)), "spread", "evidence record path and its sha256")


@pytest.mark.parametrize(
    "signer",
    ["Claude", "claude", "CLAUDE", "Claude Fable 5.1", "claude-code", "c.l.a.u.d.e",
     "Claude Code on behalf of Cooper", "  Claude  "],
)
def test_a_receipt_signed_by_claude_in_any_spelling_is_manual_only(root, signer):
    """Claude may withdraw an allowlist and may never grant one — and may never
    sign the receipt that grants one, under any spelling or case."""
    policy_with(root, "spread")
    receipt(root, signed_by=signer)
    assert_manual_only(SPP.load(manual(root)), "spread", "human signer", "Claude may")


@pytest.mark.parametrize("signer", ["", "   ", None])
def test_a_receipt_with_no_signer_is_manual_only(root, signer):
    policy_with(root, "spread")
    receipt(root, signed_by=signer)
    assert_manual_only(SPP.load(manual(root)), "spread", "signed_by")


@pytest.mark.parametrize("when", ["", None, "yesterday", "2026-13-01", "01/12/2026"])
def test_a_receipt_without_a_signed_on_date_is_manual_only(root, when):
    policy_with(root, "spread")
    receipt(root, signed_on=when)
    assert_manual_only(SPP.load(manual(root)), "spread", "signed_on")


def test_an_unreadable_receipt_is_manual_only(root):
    policy_with(root, "spread")
    (manual(root) / SPP.RECEIPTS_DIRNAME / "r-spread-1.json").write_text("{not json", encoding="utf-8")
    assert_manual_only(SPP.load(manual(root)), "spread", "readable receipt")


def test_a_receipt_that_is_not_an_object_is_manual_only(root):
    policy_with(root, "spread")
    (manual(root) / SPP.RECEIPTS_DIRNAME / "r-spread-1.json").write_text("[1, 2]", encoding="utf-8")
    assert_manual_only(SPP.load(manual(root)), "spread", "JSON object")


def test_a_superseded_receipt_is_a_record_and_not_a_permission(root):
    """`superseded/` holds withdrawn receipts. They are kept, and they grant nothing."""
    policy_with(root, "spread")
    superseded = manual(root) / SPP.RECEIPTS_DIRNAME / "superseded"
    superseded.mkdir()
    receipt(root, filename="superseded/r-spread-1.json")
    assert (superseded / "r-spread-1.json").is_file()
    assert_manual_only(SPP.load(manual(root)), "spread", "any receipt")


def test_one_market_lacking_a_receipt_shuts_the_door_on_every_market(root):
    """Fail closed as a whole, never market by market."""
    policy_with(root, "spread", "moneyline")
    rel, digest = evidence(root)
    receipt(root, filename="r-spread.json", receipt_id="r-spread", market="spread",
            evidence={"path": rel, "sha256": digest})
    loaded = SPP.load(manual(root))

    assert not loaded.allows("spread"), "the market WITH a valid receipt is also shut"
    assert not loaded.allows("moneyline")
    assert loaded.mode == SPP.MANUAL_ONLY
    assert set(loaded.receipt_failures) == {"moneyline"}
    assert loaded.receipts == {"spread": str(manual(root) / SPP.RECEIPTS_DIRNAME / "r-spread.json")}
    line = loaded.summary_line(CBB)
    assert "`moneyline` lacks" in line and "allowlists 2 market(s)" in line


def test_a_manual_only_file_is_not_examined_and_stays_manual_only(root):
    """A file that already declares manual-only allows nothing whatever the
    receipts say; there is nothing to force and no failure to report."""
    SPP.save(SPP.StagingProviderPolicy(mode=SPP.MANUAL_ONLY, allowlist={"spread": entry("spread")}), manual(root))
    receipt(root)
    loaded = SPP.load(manual(root))
    assert loaded.mode == SPP.MANUAL_ONLY
    assert loaded.receipt_failures == {}
    assert not loaded.allows("spread")
    assert "manual-only" in loaded.summary_line(CBB)


# ---------------------------------------------------------------------------
# Withdrawal still works on a forced-manual-only policy, and preserves the file
# ---------------------------------------------------------------------------


def test_withdraw_then_save_keeps_the_declared_mode_and_grants_nothing(root):
    """The machine's one permitted edit — a withdrawal — must not rewrite the
    human's `mode` field on the way through, and cannot open the door."""
    policy_with(root, "spread", "moneyline")
    loaded = SPP.load(manual(root))
    assert loaded.mode == SPP.MANUAL_ONLY
    assert SPP.withdraw(loaded, "moneyline", reason="test", at="2027-01-01T00:00:00+00:00")
    SPP.save(loaded, manual(root))

    written = json.loads((manual(root) / SPP.POLICY_FILENAME).read_text(encoding="utf-8"))
    assert written["mode"] == "reviewed"
    assert [e["market"] for e in written["allowlist"]] == ["spread"]
    assert written["withdrawn"][0]["market"] == "moneyline"
    again = SPP.load(manual(root))
    assert not again.allows("spread") and not again.allows("moneyline")


# ---------------------------------------------------------------------------
# The repository's own state
# ---------------------------------------------------------------------------


def test_the_repository_has_no_receipt_and_its_policy_is_manual_only():
    """The state this lab expects to remain in. If a receipt ever appears here,
    it was Cooper who put it there, and this test is the place to rewrite."""
    receipts = REPO / "data" / "manual" / SPP.RECEIPTS_DIRNAME
    signed = sorted(receipts.glob("*.json")) if receipts.is_dir() else []
    assert signed == [], f"receipts exist in the repository: {signed}"
    loaded = SPP.load()
    assert loaded.mode == SPP.MANUAL_ONLY
    assert loaded.allowlist == {}
    assert loaded.receipt_failures == {}


def test_there_is_still_no_grant():
    for forbidden in ("grant", "allow", "approve", "sign", "write_receipt", "promote_market"):
        assert not hasattr(SPP, forbidden), f"{forbidden} exists on the policy module"
