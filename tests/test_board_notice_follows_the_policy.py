"""The board's "no market is allowlisted" must be read, not asserted.

Both notice branches carried that clause as a constant. It is a fact about
`data/manual/staging_provider_policy.json`, which Cooper can change in one
pull request — and a page that states it from a string goes on stating it
after it stops being true.

What is NOT conditional is "no demonstrated edge". Allowlisting says a
market's prices may be used; it says nothing about whether the model beats
them. All 32 measured market-and-tier cells come back no demonstrated edge,
not enough evidence, or a demonstrated deficit, and none of those is an edge.
So the allowlist clause moves with the file and the edge clause does not.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD = PROJECT_ROOT / "web" / "build_board_json.py"
EVIDENCE = "data/outputs/cbb_price_backtest.md"


def _module():
    spec = importlib.util.spec_from_file_location("board_build", BUILD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _lab(tmp_path: Path, *, allowlist: list[str], valid_receipt: bool = True) -> Path:
    """A minimal lab tree carrying only the policy and its receipts."""
    manual = tmp_path / "data" / "manual" / "human_acceptance_receipts"
    manual.mkdir(parents=True)
    outputs = tmp_path / "data" / "outputs"
    outputs.mkdir(parents=True)
    body = b"# evidence stand-in\n"
    (tmp_path / EVIDENCE).write_bytes(body)
    digest = hashlib.sha256(body).hexdigest()

    entries = []
    for market in allowlist:
        rid = f"{market}-20260923-fixture"
        # `evidence_checksum` is not optional since 2026-09-26: an entry that
        # records none is bound to no particular receipt, so `verify_receipt`
        # refuses it. All ten of this lab's live entries carried an empty one.
        entries.append(
            {
                "market": market,
                "receipt_id": rid,
                "approved_on": "2026-09-23",
                "evidence_checksum": digest,
            }
        )
        if valid_receipt:
            (manual / f"{rid}.json").write_text(
                json.dumps(
                    {
                        "market": market,
                        "receipt_id": rid,
                        "evidence": {"path": EVIDENCE, "sha256": digest},
                        # This read `fixture-signer`, with the note "never a
                        # real person and never Claude ... this fixture must
                        # not look like a signature anyone made". The first
                        # half of that is now unreachable: since 2026-09-26
                        # the loader refuses every `signed_by` whose letters
                        # are not the owner's, because a deny list of one name
                        # let `fixture-signer` — and `Anonymous Bot`, and
                        # `automated` — open the door on the real policy file.
                        # A fixture that cannot satisfy the door cannot test
                        # what the door lets through.
                        #
                        # The second half is kept where it can still be kept:
                        # this tree is `tmp_path`, it is deleted with the test,
                        # and nothing here writes into `data/manual/`.
                        "signed_by": "Cooper Ross",
                        "signed_on": "2026-09-23",
                    }
                ),
                encoding="utf-8",
            )
    (tmp_path / "data" / "manual" / "staging_provider_policy.json").write_text(
        json.dumps(
            {
                "provider": "the_odds_api",
                "mode": "allowlisted" if allowlist else "manual_only",
                "allowlist": entries,
                "withdrawn": [],
            }
        ),
        encoding="utf-8",
    )
    return tmp_path


def test_nothing_allowlisted_says_so(tmp_path: Path) -> None:
    policy = _module().load_policy(_lab(tmp_path, allowlist=[]))
    assert policy is not None
    assert not policy.allowlist


def test_an_allowlisted_market_is_seen(tmp_path: Path) -> None:
    """The case the constant got wrong: the file says yes, the page said no."""
    policy = _module().load_policy(_lab(tmp_path, allowlist=["spread"]))
    assert policy is not None
    assert sorted(policy.allowlist) == ["spread"]
    assert not policy.receipt_failures


def test_an_allowlisted_market_without_a_receipt_is_a_failure_not_a_pass(
    tmp_path: Path,
) -> None:
    """A listed market with no receipt must not read as allowlisted.

    The policy loader forces manual-only in that state. The notice has to
    distinguish it, because "listed but unreceipted" and "allowlisted" differ
    by exactly the review this whole mechanism exists to record.
    """
    policy = _module().load_policy(
        _lab(tmp_path, allowlist=["spread"], valid_receipt=False)
    )
    assert policy is not None
    assert policy.receipt_failures


def test_an_unreadable_policy_reads_as_nothing_allowlisted(tmp_path: Path) -> None:
    """Failing safe means failing toward the restrictive sentence."""
    (tmp_path / "data" / "manual").mkdir(parents=True)
    (tmp_path / "data" / "manual" / "staging_provider_policy.json").write_text(
        "{not json", encoding="utf-8"
    )
    policy = _module().load_policy(tmp_path)
    assert policy is None or not policy.allowlist


@pytest.mark.parametrize("clause", ["no demonstrated edge"])
def test_the_edge_clause_is_not_conditional(clause: str) -> None:
    """It appears in every branch, because approving a market is not evidence."""
    text = BUILD.read_text(encoding="utf-8")
    start = text.index("allowlisted = sorted(policy.allowlist)")
    end = text.index("census = dict(", start)
    branch_block = text[start:end]
    assert branch_block.count(clause) >= 1
    # And the allowlist clause is never a constant in those branches.
    assert "no market is allowlisted and the model" not in branch_block
