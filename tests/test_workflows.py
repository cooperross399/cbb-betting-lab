"""Discipline tests over the workflow files themselves.

The gameday workflow holds `contents: write`, and GitHub cannot scope that
permission to a single ref: a token that may write `card-feed` may write
`main`. Nothing in GitHub's model narrows it, so the narrowing has to live
here, and the workflow's own comment points at this file as the reason it is
safe to hold that permission at all.

These are string assertions about YAML, which the brief is right to call
near-worthless for *logic* — that is why the clobber guard is a script with its
own behavioural test. String assertions are exactly the right tool for the
questions below, which are about what is *present in the file*: which
workflows request write access, where their pushes point, and whether any of
them stages a working tree wholesale.
"""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"

#: The CLOSED SET of workflows allowed to write to this repository, and the one
#: ref each may write. Changing it is a deliberate act that has to happen here
#: first, and a workflow absent from it may not hold `contents: write` at all.
#:
#: GitHub cannot scope `contents: write` to a ref — a token that may write
#: `line-movement` may write `main` — so this mapping is the scope. It started
#: as a single workflow and a single ref; the line-movement capture made it a
#: set, because a capture must never be able to overwrite a card and a card
#: must never be able to overwrite a capture. The rule was never "one writer",
#: it was "a declared, closed set of writers and refs", and that is what this
#: is now.
WRITERS: dict[str, str] = {
    "cbb-gameday-refresh.yml": "refs/heads/card-feed",
    "line-movement.yml": "refs/heads/line-movement",
}


def workflow_files() -> list[Path]:
    found = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    assert found, "No workflow files found; this test would pass vacuously."
    return found


def test_only_declared_workflows_request_write_access():
    writers = sorted(
        path.name
        for path in workflow_files()
        if re.search(r"^\s*contents:\s*write\s*$", path.read_text(), re.MULTILINE)
    )
    assert writers == sorted(WRITERS), (
        f"Workflows requesting `contents: write`: {writers}. The declared set "
        f"is {sorted(WRITERS)}. GitHub cannot scope that permission to a ref, "
        "so a workflow holding it that is not declared here is an undeclared "
        "way for a run to write `main`."
    )


def test_every_workflow_declares_its_permissions():
    """An undeclared `permissions:` block inherits the repository default,
    which can be write. Silence must not be a way to acquire write access."""
    for path in workflow_files():
        assert re.search(r"^permissions:\s*$", path.read_text(), re.MULTILINE), (
            f"{path.name} declares no `permissions:` block, so it inherits the "
            "repository default — which is not necessarily read."
        )


def real_lines(path: Path) -> list[str]:
    """Every line that is not a YAML/shell comment.

    Both this file's first draft and its first fix tripped over the same thing:
    the gameday workflow's own comments quote `git push` while explaining the
    rule, and a grep that reads a comment as code fails on the documentation
    rather than on the behaviour.
    """
    return [
        line for line in path.read_text().splitlines() if not line.strip().startswith("#")
    ]


def test_every_git_push_targets_the_ref_its_workflow_declared():
    """A push to any other ref is a workflow writing the repository proper.

    Each writer may push to ITS OWN declared ref and no other. The capture
    workflow pushing to `card-feed` would be as wrong as it pushing to `main`:
    a capture must never be able to overwrite a card.
    """
    pattern = re.compile(r"^\s*git push\b.*$")
    for path in workflow_files():
        pushes = [l for l in real_lines(path) if pattern.match(l)]
        if pushes:
            assert path.name in WRITERS, (
                f"{path.name} pushes but is not a declared writer: "
                f"{[p.strip() for p in pushes]}"
            )
        expected = WRITERS.get(path.name, "")
        for line in pushes:
            target = line.rstrip().rstrip('"\'')
            assert target.endswith(f":{expected}"), (
                f"{path.name} may push only to {expected}:\n  {line.strip()}"
            )


def test_no_workflow_stages_a_working_tree_wholesale():
    """`git add -A` on a runner's working tree is how a credential reaches a
    public ref. The card feed is built with plumbing — hash-object, mktree,
    commit-tree — so only files named one at a time can ever be published."""
    forbidden = re.compile(r"^\s*git\s+add\b(?!.*--dry-run)")
    for path in workflow_files():
        offenders = [l.strip() for l in real_lines(path) if forbidden.match(l)]
        assert not offenders, (
            f"{path.name} runs `git add`: {offenders}. The working tree at "
            "publish time holds staged prices, cached feeds and possibly a "
            "local .env. Name each file instead."
        )


def test_no_workflow_force_pushes():
    pattern = re.compile(r"^\s*git push\b.*$")
    for path in workflow_files():
        for line in [l for l in real_lines(path) if pattern.match(l)]:
            for flag in ("--force", " -f ", "+refs/heads/"):
                assert flag not in line, f"A workflow force-pushes: {line.strip()}"


def test_the_secret_is_only_ever_bound_to_an_env_mapping():
    """`${{ secrets.* }}` may appear only as the value of an `env:` key.

    The risk this guards is the VALUE reaching a command line, where a process
    list is world-readable and a CI log echoes commands. Naming the key in an
    error message is not that — an earlier version of this test failed on
    `echo "::error::CBB_ODDS_API_KEY is not set"`, which mentions the name and
    reveals nothing. The distinction is the whole point: guard the value, not
    the word.
    """
    binding = re.compile(r"^\s*[A-Z_]+:\s*\$\{\{\s*secrets\.[A-Za-z_]+\s*\}\}\s*$")
    for path in workflow_files():
        for line in real_lines(path):
            if "secrets." not in line:
                continue
            assert binding.match(line), (
                f"{path.name} interpolates a secret outside an `env:` "
                f"mapping:\n  {line.strip()}\n"
                "The value must reach the process through the environment, "
                "never through a command line."
            )


def test_the_credential_is_never_spelled_onto_a_command_line():
    """`$CBB_ODDS_API_KEY` as an argument to anything, rather than read from
    the environment by the script that needs it."""
    for path in workflow_files():
        for line in real_lines(path):
            stripped = line.strip()
            if "CBB_ODDS_API_KEY" not in stripped:
                continue
            # A presence check dereferences it; that is the one safe use, and
            # it compares against emptiness rather than against a value.
            if re.search(r'-z\s+"\$\{CBB_ODDS_API_KEY(:-)?\}?"', stripped):
                continue
            # Naming it in a message is fine. Dereferencing it is not.
            assert not re.search(r"\$\{?CBB_ODDS_API_KEY", stripped), (
                f"{path.name} dereferences the credential in a shell line:\n"
                f"  {stripped}"
            )


def test_the_probe_and_purchase_workflows_carry_no_cron():
    """Credit-spending discovery runs on dispatch only. A cron on either is a
    standing order to re-answer a settled question at full price."""
    for name in ("provider-retention-probe.yml", "historical-purchase.yml"):
        path = WORKFLOWS / name
        if not path.is_file():
            continue
        assert "schedule:" not in path.read_text(), (
            f"{name} carries a cron. The probe answers its question once per "
            "sport and the purchase is a one-way spend; neither repeats."
        )


def test_every_script_a_workflow_runs_actually_exists():
    """A workflow naming a script that is not in the repository is a workflow
    that has never run.

    This test was written because three of them were missing at once —
    `run_gameday_card.py`, `run_forward_evidence.py` and
    `run_what_we_can_claim.py` — in the workflow that produces the card, which
    is the whole delivery chain. Nothing failed, because nothing had dispatched
    it. A green workflow file is not a workflow that works, and an unreferenced
    filename is the cheapest possible way to find that out.
    """
    referenced: dict[str, set[str]] = {}
    for path in workflow_files():
        for match in re.findall(r"scripts/[A-Za-z0-9_]+\.py", path.read_text()):
            referenced.setdefault(match, set()).add(path.name)

    assert referenced, "No workflow runs any script; this test would pass vacuously."
    root = WORKFLOWS.parents[1]
    missing = {
        script: sorted(where)
        for script, where in sorted(referenced.items())
        if not (root / script).is_file()
    }
    assert not missing, (
        "Workflows reference scripts that do not exist:\n"
        + "\n".join(f"  {s} — named by {', '.join(w)}" for s, w in missing.items())
    )


def test_the_purchase_workflow_names_the_directory_the_module_actually_writes():
    """The most expensive defect in this repository, pinned.

    The purchase workflow spelled its cache and artifact paths by hand as
    `data/raw/cbb/historical_<window>`. `historical.cache_dir_for` returns
    `data/raw/cbb/historical_purchase/<window>`. So:

    * the `actions/cache` step saved nothing, and resume never resumed;
    * the artifact step uploaded nothing, warning where it should have failed;
    * a run that spent **1,299,945 credits** buying 1.82M price rows persisted
      only its own report.

    The responses survived by luck — a sibling cache happened to cover the
    whole of `data/raw/cbb`. Nothing about that was designed.

    A path duplicated between Python and YAML is a path that will disagree.
    This test is the only thing that makes the duplication safe, so it derives
    the expected string from the module rather than restating it.
    """
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.providers import historical as H

    path = WORKFLOWS / "historical-purchase.yml"
    if not path.is_file():
        return
    text = path.read_text()

    for window in (H.CARD_WINDOW, H.CLOSE_WINDOW):
        expected = H.cache_dir_for(CBB, Path("data/raw"), window)
        # The workflow templates the window, so compare the parent segment.
        stem = str(expected.parent).replace("data/raw/", "data/raw/")
        assert stem in text, (
            f"The purchase workflow does not mention {stem!r}, which is where "
            f"`cache_dir_for` actually writes. A workflow caching or uploading "
            "some other directory persists nothing and warns rather than fails."
        )


def test_the_purchase_workflow_builds_the_store_it_uploads():
    """The live buy caches raw responses and stages rows in memory; it does not
    write the processed CSV. That is a defensible design — the cache is the
    source of truth and the store is derived — but only if something derives
    it. The first run reported 1.82M rows staged and left no store on disk."""
    path = WORKFLOWS / "historical-purchase.yml"
    if not path.is_file():
        return
    text = path.read_text()
    assert "--rebuild" in text, (
        "Nothing in the purchase workflow rebuilds the store from the cached "
        "responses, so a completed purchase leaves no store behind."
    )
    rebuild_at = text.index("--rebuild")
    upload_at = text.index("upload-artifact")
    assert rebuild_at < upload_at, (
        "The store is rebuilt after it is uploaded, so the upload carries the "
        "previous run's store or none at all."
    )
