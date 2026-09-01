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

#: The one workflow allowed to write to this repository, and the one ref it may
#: write. Changing either is a deliberate act that has to happen here first.
THE_WRITER = "cbb-gameday-refresh.yml"
THE_REF = "refs/heads/card-feed"


def workflow_files() -> list[Path]:
    found = sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml"))
    assert found, "No workflow files found; this test would pass vacuously."
    return found


def test_exactly_one_workflow_requests_write_access():
    writers = [
        path.name
        for path in workflow_files()
        if re.search(r"^\s*contents:\s*write\s*$", path.read_text(), re.MULTILINE)
    ]
    assert writers == [THE_WRITER], (
        f"Workflows requesting `contents: write`: {writers}. Exactly one may, "
        f"and it must be {THE_WRITER}. GitHub cannot scope that permission to "
        "a ref, so a second workflow holding it is a second way for a run to "
        "write `main`."
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


def test_every_git_push_in_every_workflow_targets_the_card_feed_ref():
    """A push to any other ref is a workflow writing the repository proper."""
    pattern = re.compile(r"^\s*git push\b.*$")
    for path in workflow_files():
        for line in [l for l in real_lines(path) if pattern.match(l)]:
            target = line.rstrip().rstrip('"\'')
            assert target.endswith(f":{THE_REF}"), (
                f"{path.name} pushes to something other than {THE_REF}:\n"
                f"  {line.strip()}\n"
                "Every push in this repository ends in that ref."
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
