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


#: The bytes every synthetic evidence record here holds unless a test says
#: otherwise, and their digest. The digest is a module constant because the
#: allowlist ENTRY has to record it: `verify_receipt` refuses an entry that
#: records no `evidence_checksum`, since an entry that records none is bound to
#: no particular receipt.
EVIDENCE_BODY = b'{"roi": -0.039}\n'
EVIDENCE_DIGEST = hashlib.sha256(EVIDENCE_BODY).hexdigest()


def evidence(root: Path, name: str = "cbb_price_backtest.json", body: bytes = EVIDENCE_BODY) -> tuple[str, str]:
    """Write an evidence record; return its repo-relative path and sha256."""
    path = root / "data" / "outputs" / name
    path.write_bytes(body)
    return f"data/outputs/{name}", hashlib.sha256(body).hexdigest()


def entry(
    market: str,
    receipt_id: str = "r-spread-1",
    *,
    evidence_checksum: str = EVIDENCE_DIGEST,
) -> SPP.AllowlistEntry:
    return SPP.AllowlistEntry(
        market=market, receipt_id=receipt_id, approved_on="2026-12-01",
        roi_floor=-0.02, evidence_checksum=evidence_checksum, minimum_bets=200,
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


def test_every_receipt_in_the_repository_is_one_the_loader_accepts():
    """Rewritten where the old version said to rewrite it.

    It read: "The state this lab expects to remain in. If a receipt ever
    appears here, it was Cooper who put it there, and this test is the place
    to rewrite." It asserted the receipts directory was empty and the policy
    manual-only — the state, as a constant.

    A constant is the wrong shape here for the same reason it was wrong in
    the board's notice and in the workflow census: it is a fact about a file
    a human may change, so the first legitimate change makes the assertion
    false and the only way back to green is to weaken it. This lab has three
    guards that would all have had to be loosened in the same commit as a
    signature, which is exactly when nobody wants to be loosening guards.

    What it holds now is the property the emptiness was standing in for:
    whatever is on disk, every receipt is one the loader accepted, and the
    policy and the receipts agree with each other. An unreceipted allowlist
    still fails. A receipt signed by Claude still fails, in the loader,
    where `FORBIDDEN_SIGNER` refuses it.
    """
    loaded = SPP.load()

    assert loaded.receipt_failures == {}, (
        f"receipts the loader refused: {loaded.receipt_failures}"
    )
    if loaded.allowlist:
        assert loaded.mode != SPP.MANUAL_ONLY, (
            "markets are allowlisted but the mode is manual-only, so the card "
            "reads none of them"
        )
        for market, entry in sorted(loaded.allowlist.items()):
            assert entry.receipt_id, f"{market} is allowlisted with no receipt id"
    else:
        assert loaded.mode == SPP.MANUAL_ONLY, (
            "the mode permits reading staging while nothing is allowlisted"
        )


def test_a_receipt_on_disk_that_belongs_to_no_allowlisted_market_is_visible():
    """A signed receipt for a market nobody allowlisted is not an approval.

    It is also not nothing: it is a decision that was made and then not
    carried into the policy, and reading the directory as if it were the
    allowlist is how the two drift apart.
    """
    receipts = REPO / "data" / "manual" / SPP.RECEIPTS_DIRNAME
    on_disk = {p.stem for p in receipts.glob("*.json")} if receipts.is_dir() else set()
    cited = {e.receipt_id for e in SPP.load().allowlist.values()}
    orphans = sorted(on_disk - cited)
    assert not orphans, (
        "receipts exist that no allowlisted market cites: "
        f"{orphans}. Either the policy is missing an entry or the receipt "
        "was superseded and belongs under superseded/."
    )


def test_there_is_still_no_grant():
    for forbidden in ("grant", "allow", "approve", "sign", "write_receipt", "promote_market"):
        assert not hasattr(SPP, forbidden), f"{forbidden} exists on the policy module"


def test_an_entry_signed_against_different_evidence_is_refused(tmp_path):
    """`AllowlistEntry.evidence_checksum` was a guard written only in prose.

    Its own docstring declares an enforcement — "when the evidence moves, this
    stops matching and the gate goes red, which is how the NHL lab caught its
    own stale approval" — and nothing read it. `load()` parsed it, `save()`
    wrote it back, and the module-level `evidence_checksum()` helper that
    produces the value had zero callers anywhere in src/ or scripts/.

    It is NOT the check that was already there. That one asks whether the
    receipt's cited sha256 matches the evidence file it names, catching evidence
    that moved under a receipt. This asks whether the receipt still cites the
    evidence THE ENTRY was signed against — so a different receipt, internally
    consistent with different evidence, is caught too. One binds a receipt to a
    file; the other binds the allowlist to a receipt.

    Three cases, because the middle one is what makes it honest: matching
    passes, mismatching refuses, and EMPTY is "not recorded" rather than
    "matches" — an entry written before the field was populated must not read
    as checked.
    """
    root = tmp_path
    (root / "data" / "outputs").mkdir(parents=True)
    (manual(root) / SPP.RECEIPTS_DIRNAME).mkdir(parents=True, exist_ok=True)
    _, digest = evidence(root)
    path = receipt(root)
    payload = json.loads(path.read_text(encoding="utf-8"))

    agreeing = SPP.AllowlistEntry(
        market="spread", receipt_id="r-spread-1", approved_on="2026-12-01",
        roi_floor=-0.02, evidence_checksum=digest, minimum_bets=200,
    )
    assert SPP._examine_receipt(path, payload, agreeing, root) == "", (
        "an entry recording the very checksum the receipt cites is refused, so "
        "the check would be red from the day it landed"
    )

    other = "0" * 64
    disagreeing = SPP.AllowlistEntry(
        market="spread", receipt_id="r-spread-1", approved_on="2026-12-01",
        roi_floor=-0.02, evidence_checksum=other, minimum_bets=200,
    )
    reason = SPP._examine_receipt(path, payload, disagreeing, root)
    assert reason, "a receipt citing evidence the entry was not signed against passed"
    assert digest[:12] in reason and other[:12] in reason, (
        f"the refusal names only one side, so a reader cannot check it: {reason}"
    )

    unrecorded = SPP.AllowlistEntry(
        market="spread", receipt_id="r-spread-1", approved_on="2026-12-01",
        roi_floor=-0.02, evidence_checksum="", minimum_bets=200,
    )
    assert SPP._examine_receipt(path, payload, unrecorded, root) == "", (
        "an empty checksum is 'not recorded' and must not refuse; it also must "
        "not be treated as a match, which is what the caller's own reporting "
        "is for"
    )


# ---------------------------------------------------------------------------
# 2026-09-26: the forgeries the door used to accept
#
# Every test below FAILS on the parent commit. Each one was first run as a
# script against that tree and accepted a market Cooper never approved; the
# measurement is quoted in the docstring. Nothing here writes into
# `data/manual/` — `tmp_path` throughout, as the module docstring says.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "signer",
    ["Anonymous Bot", "fixture-signer", "automated", "Cooper", "C. Ross",
     "Cooper Rossington", "the reviewer"],
)
def test_a_signature_from_anybody_but_cooper_is_manual_only(root, signer):
    """`_signer_is_forbidden` is a DENY LIST OF ONE NAME.

    It asks "is this the one signer we refuse", and every string that does not
    spell `claude` walked through it. Measured on the parent commit: a receipt
    signed `Anonymous Bot`, citing evidence written in the same breath, loaded
    `spread` live — `allows("spread")` was True and `receipt_failures` empty.

    The door has to ask the other question too: is this the signature whose
    approval it is. `ACCEPTED_SIGNERS` is that question, and it is matched on
    the folded LETTERS, so `cooper ross` and `COOPER ROSS` are Cooper and
    `Cooper Rossington` is not.
    """
    policy_with(root, "spread")
    receipt(root, signed_by=signer)
    assert_manual_only(SPP.load(manual(root)), "spread", "whose approval this door opens for")


@pytest.mark.parametrize("signer", ["Cooper Ross", "cooper ross", "COOPER ROSS", "cooperross399", "Cooper  Ross!"])
def test_cooper_in_any_spelling_still_opens_the_door(root, signer):
    """The other half, and the one that would make this an outage.

    A refusal list that also refuses the owner has not hardened the gate, it
    has withdrawn ten markets. The ten receipts live on `main` are signed
    `Cooper Ross`.
    """
    policy_with(root, "spread")
    receipt(root, signed_by=signer)
    assert SPP.load(manual(root)).allows("spread"), signer


def test_the_accepted_signer_list_is_unreachable_from_configuration():
    """Identity may not come from anything the machine can write.

    The whole point is that an agent with code execution here cannot stand in
    for Cooper, so a signer list that any environment variable, git config or
    config file could extend would be no check at all. It is a source
    constant; changing it is a pull request a human merges.
    """
    source = (
        Path(SPP.__file__).read_text(encoding="utf-8")
    )
    listing = source.split("ACCEPTED_SIGNERS", 1)[1].split("\n\n", 1)[0]
    for reachable in ("os.environ", "getenv", "os.getenv", "argv", "ConfigParser", "git config"):
        assert reachable not in listing, (
            f"the accepted-signer list is reachable from {reachable}"
        )
    for reachable in ("os.environ", "getenv", "argparse", "sys.argv"):
        assert reachable not in source, (
            f"{reachable} appears in the policy module, which is the door's own "
            "source; the signer list must not be reachable from configuration"
        )
    assert SPP.ACCEPTED_SIGNERS == ("cooperross",)


def test_an_allowlist_entry_with_no_receipt_id_is_manual_only(root):
    """The `receipt_id` line was OPTIONAL, exactly as the `pr:` line was.

    The guard read `if entry.receipt_id:`, so an entry that simply omitted the
    field bound to whichever receipt in the directory happened to name its
    market. Measured on the parent commit: a policy whose only entry was
    `{"market": "spread"}` loaded live behind a receipt called
    `whatever.json`.
    """
    (manual(root) / SPP.POLICY_FILENAME).write_text(
        json.dumps({
            "provider": "the_odds_api", "mode": "reviewed",
            "allowlist": [{"market": "spread", "evidence_checksum": EVIDENCE_DIGEST}],
            "withdrawn": [],
        }),
        encoding="utf-8",
    )
    receipt(root, filename="whatever.json")
    assert_manual_only(SPP.load(manual(root)), "spread", "`receipt_id` on its allowlist entry")


def test_an_entry_recording_no_evidence_checksum_is_manual_only(root):
    """Absent must not read as checked — the same defect as comparing a missing
    file against a missing blob and calling them equal.

    `_examine_receipt` reads an empty `evidence_checksum` as "not recorded" and
    declines to judge it, which is honest for a function asked about one
    receipt, and its docstring says the empty case is "what the caller's own
    reporting is for". The caller's reporting was silence. Measured on the
    parent commit: all ten of this lab's live entries carried an empty
    `evidence_checksum`, and with the field empty a receipt citing evidence the
    entry had never been signed against was accepted and the market loaded
    live.
    """
    SPP.save(
        SPP.StagingProviderPolicy(
            mode="reviewed",
            allowlist={"spread": entry("spread", evidence_checksum="")},
        ),
        manual(root),
    )
    receipt(root)
    assert_manual_only(SPP.load(manual(root)), "spread", "`evidence_checksum` on its allowlist entry")


def test_two_receipts_claiming_one_receipt_id_refuse_rather_than_pick_one(root):
    """A second receipt SHADOWED the genuine one by sorting earlier.

    `verify_receipt` returned the first file that verified, in sorted order,
    which is alphabetical order of filename. Measured on the parent commit,
    with both files claiming `receipt_id` `r-spread-1` and market `spread`:
    `aaa-forged.json`, citing evidence its author had just written, won over
    `r-spread-1.json`; the genuine receipt stayed on disk for a reviewer to
    find, and `load()` bound the market to the forgery.

    Two receipts claiming one approval is not an approval; it is a question,
    and this door answers a question with no.
    """
    policy_with(root, "spread")
    genuine = receipt(root)
    shadow = receipt(root, filename="aaa-also-claims-r-spread-1.json")
    loaded = SPP.load(manual(root))

    assert_manual_only(loaded, "spread", "exactly one receipt claiming `r-spread-1`")
    reason = loaded.receipt_failures["spread"]
    assert genuine.name in reason and shadow.name in reason, (
        f"the refusal does not name both claimants, so nobody can act on it: {reason}"
    )


def test_a_withdrawal_at_or_after_the_approval_refuses_the_market(root):
    """A REVOCATION IS NOT INVISIBLE, and it is not an approval either.

    `withdrawn` is the file's own record of what the machine took back, and
    nothing read it at verification time: `withdraw()` appended to it and
    `save()` wrote it out, and re-adding the market to the allowlist with its
    original receipt still on disk loaded it live again. Measured on the parent
    commit: `spread`, withdrawn 2026-09-25 for falling through its ROI floor,
    approval dated 2026-09-23, was allowed.
    """
    policy_with(root, "spread")
    receipt(root)
    assert SPP.load(manual(root)).allows("spread"), "the fixture itself must start valid"

    payload = json.loads((manual(root) / SPP.POLICY_FILENAME).read_text(encoding="utf-8"))
    payload["withdrawn"] = [{
        "market": "spread", "receipt_id": "r-spread-1",
        "approved_on": "2026-12-01",
        "withdrawn_at": "2026-12-09T00:00:00+00:00",
        "reason": "forward ROI interval fell below the floor declared at approval",
    }]
    (manual(root) / SPP.POLICY_FILENAME).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    assert_manual_only(SPP.load(manual(root)), "spread", "has not already withdrawn")
    assert "forward ROI interval" in SPP.load(manual(root)).receipt_failures["spread"], (
        "the refusal does not carry the reason the market was withdrawn"
    )


def test_an_undated_withdrawal_still_wins(root):
    """A record that a permission was taken away, whose date cannot be read, is
    not a reason to hand the permission back."""
    policy_with(root, "spread")
    receipt(root)
    payload = json.loads((manual(root) / SPP.POLICY_FILENAME).read_text(encoding="utf-8"))
    payload["withdrawn"] = [{"market": "spread", "withdrawn_at": "", "reason": "stale"}]
    (manual(root) / SPP.POLICY_FILENAME).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    assert_manual_only(SPP.load(manual(root)), "spread", "not a readable date")


def test_an_approval_signed_after_a_withdrawal_is_not_refused(root):
    """The rule is "the newer decision wins", not "a withdrawal is forever".

    A human re-approving after a demotion is an ordinary new decision. It still
    needs everything else on this page; it does not need the old withdrawal
    deleted from the record, because deleting the record is how the record
    stops being one.
    """
    policy_with(root, "spread")
    receipt(root)
    payload = json.loads((manual(root) / SPP.POLICY_FILENAME).read_text(encoding="utf-8"))
    payload["withdrawn"] = [{
        "market": "spread", "withdrawn_at": "2026-11-30T00:00:00+00:00",
        "reason": "an earlier demotion, before this approval",
    }]
    (manual(root) / SPP.POLICY_FILENAME).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    assert SPP.load(manual(root)).allows("spread"), (
        "a withdrawal OLDER than the approval it precedes refuses the market, "
        "so no market could ever be re-approved"
    )


def test_evidence_outside_the_repository_is_manual_only(root, tmp_path_factory):
    """Evidence nobody reviewing this change can see is not evidence.

    An absolute path was taken as given. Measured on the parent commit: a
    receipt citing `/tmp/.../outside.md`, hashed correctly, loaded `spread`
    live. The record was in no diff, in no pull request, and absent from the
    runner the merge-time gate runs on.
    """
    outside = tmp_path_factory.mktemp("not_the_repo") / "outside.md"
    outside.write_bytes(b"evidence nobody can review\n")
    digest = hashlib.sha256(outside.read_bytes()).hexdigest()
    SPP.save(
        SPP.StagingProviderPolicy(
            mode="reviewed",
            allowlist={"spread": entry("spread", evidence_checksum=digest)},
        ),
        manual(root),
    )
    receipt(root, evidence={"path": str(outside), "sha256": digest})
    assert_manual_only(SPP.load(manual(root)), "spread", "inside the repository")


def test_evidence_reached_by_traversal_out_of_the_repository_is_manual_only(root, tmp_path_factory):
    """The relative spelling of the same escape."""
    outside = tmp_path_factory.mktemp("not_the_repo") / "outside.md"
    outside.write_bytes(b"evidence nobody can review\n")
    digest = hashlib.sha256(outside.read_bytes()).hexdigest()
    relative = Path(*([".."] * 8)) / outside.relative_to(Path(outside.anchor))
    SPP.save(
        SPP.StagingProviderPolicy(
            mode="reviewed",
            allowlist={"spread": entry("spread", evidence_checksum=digest)},
        ),
        manual(root),
    )
    receipt(root, evidence={"path": str(relative), "sha256": digest})
    assert_manual_only(SPP.load(manual(root)), "spread", "inside the repository")


def test_a_symlink_inside_the_repository_pointing_out_of_it_is_manual_only(root, tmp_path_factory):
    """Where it LANDS, not how it is spelled. `resolve()` is what asks that."""
    outside = tmp_path_factory.mktemp("not_the_repo") / "outside.md"
    outside.write_bytes(b"evidence nobody can review\n")
    digest = hashlib.sha256(outside.read_bytes()).hexdigest()
    link = root / "data" / "outputs" / "looks_local.md"
    link.symlink_to(outside)
    SPP.save(
        SPP.StagingProviderPolicy(
            mode="reviewed",
            allowlist={"spread": entry("spread", evidence_checksum=digest)},
        ),
        manual(root),
    )
    receipt(root, evidence={"path": "data/outputs/looks_local.md", "sha256": digest})
    assert_manual_only(SPP.load(manual(root)), "spread", "inside the repository")


def test_every_live_entry_is_bound_to_one_receipt_and_its_evidence():
    """The repository's own state, asked as a property.

    Nothing binds a market to a receipt unless the ENTRY records which receipt
    and which evidence. On the parent commit all ten live entries carried
    `receipt_id` and nothing else — no `approved_on`, no `evidence_checksum` —
    so the allowlist-to-receipt binding was enforced on none of them.
    """
    loaded = SPP.load()
    assert loaded.receipt_failures == {}, (
        f"receipts the loader refused: {loaded.receipt_failures}"
    )
    for market, e in sorted(loaded.allowlist.items()):
        assert e.receipt_id, f"{market} is allowlisted with no receipt id"
        assert e.evidence_checksum, (
            f"{market} is allowlisted with no evidence_checksum, so no "
            "particular receipt stands behind it"
        )
        assert e.approved_on, (
            f"{market} is allowlisted with no approved_on, so a withdrawal "
            "cannot be dated against it"
        )
        path = Path(loaded.receipts[market])
        cited = json.loads(path.read_text(encoding="utf-8"))["evidence"]["sha256"]
        assert cited.casefold() == e.evidence_checksum.casefold()


# ---------------------------------------------------------------------------
# Two PINS rather than fixes. The sibling labs' forgery report names a
# publicly-constructible verified-approval object and a caller-supplied
# activity payload; neither exists in this lab, and these hold that shut
# rather than describing it as shut.
# ---------------------------------------------------------------------------


def test_the_cards_policy_directory_cannot_be_redirected_by_a_caller():
    """The card reads ITS OWN policy, not one it is handed.

    `verify_receipt` reads the filesystem itself; there is no fetched-activity
    payload a caller could fabricate. The one remaining way in would be
    pointing the card at a directory of forged receipts, so: the card's script
    takes no `--manual-dir`, and `MANUAL_DIR` is derived from
    `config.py`'s own location rather than from the environment or the working
    directory.
    """
    card = (REPO / "scripts" / "run_gameday_card.py").read_text(encoding="utf-8")
    for redirect in ("--manual-dir", "--manual_dir", "--policy", "--receipts"):
        assert redirect not in card, (
            f"run_gameday_card.py takes {redirect}, so the card can be pointed "
            "at a directory of forged receipts"
        )
    assert "load_policy()" in card, (
        "the card no longer loads the policy with no argument, so something "
        "chooses which policy it reads"
    )
    config = (REPO / "src" / "cbb_betting_lab" / "config.py").read_text(encoding="utf-8")
    manual = [line for line in config.splitlines() if line.startswith("MANUAL_DIR")]
    assert manual == ["MANUAL_DIR = DATA_DIR / \"manual\""], manual
    for reachable in ("environ", "getenv", "cwd()"):
        assert reachable not in "\n".join(manual), manual


def test_an_in_memory_policy_is_a_test_seam_that_production_never_reads():
    """`StagingProviderPolicy` IS publicly constructible, on purpose.

    The sibling labs' report names a public frozen dataclass whose
    `isinstance()` guard protects nothing, because a forger hand-builds it and
    calls the receipt-MINTING function. There is no minting function here —
    `test_there_is_still_no_grant` holds that — and the hand-built policy is an
    explicit seam, pinned by
    `test_promotion_is_one_directional.py` with the words "an in-memory policy
    is the test seam and must still work", so that the card's selection path
    can be exercised at all.

    What makes the seam safe is that no production caller uses it: every path
    that reaches the card goes through `load()`, which re-reads and re-verifies
    the receipts from disk. That is the property, and this is it asserted.
    """
    hand_built = SPP.StagingProviderPolicy(
        mode="reviewed", allowlist={"spread": entry("spread")}
    )
    assert hand_built.allows("spread"), "the documented seam has been closed silently"

    for script in ("run_gameday_card.py", "run_weekly_loop.py"):
        source = (REPO / "scripts" / script).read_text(encoding="utf-8")
        assert "StagingProviderPolicy(" not in source, (
            f"{script} constructs a policy instead of loading one, so the "
            "receipts behind it are never read"
        )
    card = (REPO / "src" / "cbb_betting_lab" / "reports" / "gameday_card.py").read_text(
        encoding="utf-8"
    )
    assert "StagingProviderPolicy(" not in card, (
        "the card constructs a policy of its own somewhere, which is a door "
        "that never opens a receipt"
    )
