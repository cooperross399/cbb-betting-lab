"""The workflows' invariants, parsed and executed rather than grepped.

Two families of rule live here, and the difference between them is the whole
reason this file was rewritten.

**The corpus rules** read every file under `.github/workflows/`: which
workflows may hold `contents: write` and where each may push (GitHub cannot
scope that permission to a ref, so a token that may write `card-feed` may
write `main`, and this file is the only scope there is); that nothing stages
a working tree wholesale; that the secrets context reaches a process only
through an `env:` mapping and never a command line; that the credit-spending
probe and purchase carry no cron; that every script a workflow names exists.
These used to be regular expressions over raw lines. A regex over a line
proves only that a spelling is absent: `git  push` with two spaces, a push
behind a `&&`, a `${{ secrets['X'] }}` bracket accessor, and `python-version:
3.10` — the YAML float 3.1 — all walked past the rules that "checked" them.
Every rule now reads `yaml.safe_load`'s tree, and the shell rules read the
joined logical lines of each `run:` block through `shlex`.

**The gate rules** apply to the three workflows whose green tick is a claim
about this repository — `tests.yml`, which is the required status check named
`Tests`; `ledger-guard.yml`, whose tick says no recorded hypothesis was
removed; and `policy-gate.yml`, whose tick says every allowlisted market is
backed by a receipt a person signed — and they are the reason branch
protection would mean anything. Until this file nothing pinned that check: the job could
be renamed (a required context that no job reports stays pending forever and
reads as nothing to merge over), emptied (`echo` in place of `pytest`),
disabled (`if: false`, `continue-on-error`), narrowed (`-x`, a positional
path, `PYTEST_ADDOPTS` in an `env:` nobody reads), moved onto a matrix (which
renames the context to `Tests (3.12)`), or deleted, and the suite stayed
green because the suite does not read the file that runs it. Every one of
those is reproduced in the self-regression half of this file and rejected.

DO NOT MATCH TEXT. EXECUTE THE THING AND OBSERVE WHAT IT DOES.
--------------------------------------------------------------
The swallow rule does not read a run block for `|| true`. It writes the block
to a sandbox, replaces every command word with a shell function of known exit
status, runs it under `bash -e` — the shell GitHub runs a `run:` block with —
and reads the exit code. That is what catches `if ! cmd; then echo; fi`,
`set +e`, `set +o pipefail`, `trap 'exit 0' ERR`, a swallow behind a function,
a backgrounded gate, and every future rewording, because none of those is a
spelling: they are all the same observable, a block that reaches its end
after a command in it failed. Nothing real runs — PATH is an empty directory
and a command that reaches the shell without a stub is reported as
"unmodelled", which is a failure of the check and not a pass.
`test_nothing_real_runs_under_the_stub_harness` is the proof.

The byte-compile step is executed the same way. `python -m compileall src`
exits 0 when `src/` does not exist — measured, not recalled — so the block is
run in a sandbox with no such directory, every stub succeeding, and must exit
non-zero; then with the directories present, and must exit zero.

What this file cannot see is written into
`test_the_disclosed_holes_are_real`, asserted open, so a hole that closes
turns the file red and the sentence gets rewritten rather than outliving the
fix. The rules that are still textual — the credential-on-a-command-line
rule, the process-substitution and launcher bans — are labelled as such.

CBB is PUBLIC and main is protected. Measured 2026-09-05 with
`gh api repos/cooperross399/cbb-betting-lab/branches/main/protection`:
`required_status_checks.contexts` is `["Tests"]`, `enforce_admins.enabled` is
true, and `allow_force_pushes` and `allow_deletions` are both false. So the
context this file pins IS the context protection requires, and a red `Tests`
holds the merge button rather than only being a fact in the pull request.
An earlier version of this docstring said the repository was private and that
nothing on GitHub's side gated a merge; it carries the command now so the
next session re-measures instead of trusting it.

No rule in this file reads that API — the suite runs offline and with no
credential, and that is deliberate. The two limits that fall out of the same
payload are recorded in `test_the_disclosed_holes_are_real` rather than
enforced here: `Ledger Guard` is not a required context, and
`required_status_checks.strict` is false.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Iterator, NamedTuple

import pytest
import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS_DIR = PROJECT_ROOT / ".github" / "workflows"

#: The required status check context. GitHub reports a job under its `name:`,
#: so this is the string branch protection (when it is on) asks for, and the
#: string every rule in the gate family is anchored to.
REQUIRED_CHECK = "Tests"
TESTS_WORKFLOW = "tests.yml"
LEDGER_WORKFLOW = "ledger-guard.yml"
#: The check that makes "in a pull request whose policy gate is green" a
#: sentence about something. Held to the gate rules like the other two: it is
#: not operational, holds no credential, and its tick is a claim.
POLICY_GATE_WORKFLOW = "policy-gate.yml"

#: The workflows whose run blocks are executed under stubs and held to the
#: gate rules. The other six are operational: they hold credentials on
#: purpose, keep going on purpose (`continue-on-error` on a report step so the
#: evidence still uploads), and are covered by the corpus rules only.
GATE_WORKFLOWS = frozenset({TESTS_WORKFLOW, LEDGER_WORKFLOW, POLICY_GATE_WORKFLOW})

#: The junit gate and the ledger gate, by file name. The evidence chain in
#: tests.yml is pytest -> junit -> this script; every rule about that chain
#: reads one of its two ends.
GATE_SCRIPT = "check_test_results.py"
LEDGER_SCRIPT = "check_ledger_append_only.py"

#: The credential names no gate workflow may bind into an `env:`. The suite
#: must pass without either, and its absence is the proof that no test
#: depends on a live provider.
CREDENTIAL_NAMES = frozenset({"CBB_ODDS_API_KEY", "CBBD_API_KEY"})

#: The CLOSED SET of workflows allowed to write to this repository, and the
#: one ref each may write. GitHub cannot scope `contents: write` to a ref, so
#: this mapping is the scope. A workflow absent from it may not hold the
#: permission at all, and a writer may push to its own ref and no other: a
#: capture must never be able to overwrite a card.
WRITERS: dict[str, str] = {
    "cbb-gameday-refresh.yml": "refs/heads/card-feed",
    "line-movement.yml": "refs/heads/line-movement",
}

#: Credit-spending discovery runs on dispatch only. A cron on either is a
#: standing order to re-answer a settled question at full price.
NO_CRON_WORKFLOWS = ("provider-retention-probe.yml", "historical-purchase.yml")

#: The `secrets` CONTEXT being reached into, in any spelling GitHub accepts:
#: dot, bracket, paren, any casing. A rule that knew one punctuation mark was
#: defeated by typing a different one, and `${{ toJSON(secrets) }}` needs
#: none of them and interpolates every secret at once.
SECRET_REFERENCE = re.compile(r"(?i)\bsecrets\s*[.\[)]")
GITHUB_EXPRESSION = re.compile(r"(?s)\$\{\{.*?\}\}")
SECRETS_WORD = re.compile(r"(?i)\bsecrets\b")

OR_LIST = re.compile(r"\|\|(?!\|)")
NONZERO_EXIT = re.compile(r"\bexit\s+[1-9]")
CONDITION = re.compile(r"^\s*(?:if|elif|while|until)\b")
DISABLES_ERREXIT = re.compile(r"\bset\b[^;&|]*\+(?:[a-z]*e[a-z]*\b|o\s+(?:errexit|pipefail)\b)")
ENABLES_PIPEFAIL = re.compile(r"^\s*set\b[^;&|]*-[a-zA-Z]*o\s+pipefail\b")
DISABLES_PIPEFAIL = re.compile(r"\bset\b[^;&|]*\+o?\s*pipefail\b")
PIPELINE = re.compile(r"(?<!\|)\|(?!\|)")
#: A script piped into `tee`, whose status is tee's unless the block sets
#: pipefail. Continuations are joined before this is applied, so the flags
#: between the script and the pipe do not hide it.
SCRIPT_THROUGH_TEE = re.compile(r"\bpython\b[^|]*\|\s*tee\b")
#: A pipeline with no pipe character: `<(cmd)` runs in a subshell whose status
#: nothing propagates. A construct ban, labelled as one.
PROCESS_SUBSTITUTION = re.compile(r"[<>]\(")
#: A single `&` that is not `&&`, `>&` or `&>`: errexit does not apply to an
#: asynchronous command and `wait` with no argument returns 0.
BACKGROUND = re.compile(r"(?<![&>])&(?![&>])")
#: The same capability without the operator. An enumeration, labelled as one.
ASYNC_LAUNCHER = re.compile(r"\b(?:setsid|coproc)\b")
CONTINUATION = re.compile(r"(?:\\|\|\||&&|\|)$")

#: pytest flags that stop the run early, narrow it, reconfigure it, or launder
#: its evidence. Both spellings of every alias: a flag banned as `-x` and
#: allowed as `--exitfirst` is not banned. `--override-ini`/`-o`,
#: `--config-file`/`-c` and `--confcutdir` reconfigure rather than select, and
#: `testpaths` is one of the things they reconfigure. `--runxfail` disarms the
#: gate: the junit then records an xpass as a plain pass.
NARROWING_PYTEST_LONG_FLAGS = frozenset(
    {
        "--maxfail", "--ignore", "--ignore-glob", "--deselect", "--exitfirst",
        "--override-ini", "--config-file", "--confcutdir", "--runxfail",
        "--collect-only", "--co", "--last-failed", "--lf", "--stepwise", "--sw",
        "--stepwise-skip", "--sw-skip", "--stepwise-reset", "--sw-reset",
    }
)
#: Matched as letters inside a short-option cluster, so `-xq` and `-qcci.ini`
#: are caught too.
NARROWING_PYTEST_SHORT_FLAGS = frozenset("xkmoc")
PYTEST_ADDOPTS = "PYTEST_ADDOPTS"
PYTEST_ADDOPTS_TOKEN = re.compile(r"(?i)\bPYTEST_ADDOPTS\b")
JUNIT_FLAGS = frozenset({"--junit-xml", "--junitxml"})
#: The WHITELIST. Everything the suite line may carry besides its junit flag,
#: and nothing else. A blocklist of narrowing flags is a list of spellings and
#: it let `--version`, `-h` and `--help` straight through — each of which exits
#: 0, runs no test and writes no junit, so a junit already sitting at the gated
#: path became this run's evidence and the clean-tree check saw nothing move.
#: A whitelist has no such hole to find: an argument nobody wrote down is
#: refused whether or not anybody thought of it.
SUITE_ARGUMENT_WHITELIST = frozenset({"-q", "-rs"})
#: The junit may only be written under the runner's temp directory, in either
#: spelling. A path inside the checkout can be a tracked file.
RUNNER_TEMP_PREFIXES = ("$RUNNER_TEMP/", "${{ runner.temp }}/")
#: The gate's command line, pinned as a whole rather than searched for as a
#: substring. `: python scripts/check_test_results.py <path>` CONTAINS the
#: script and the path and runs nothing.
GATE_COMMAND_SHAPE = ("python", "scripts/" + GATE_SCRIPT)
GATE_MARKER_FLAG = "--newer-than"
#: `python -m pytest` searches the working directory before site-packages.
SAFE_PATH_VARIABLE = "PYTHONSAFEPATH"
BRACED_VARIABLE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}(?![A-Za-z0-9_])")
SHELL_OPERATOR_TOKENS = frozenset(
    {"|", "||", "&&", "&", ";", ";;", ">", ">>", "<", "<<", "2>", "&>", "(", ")"}
)
COMMAND_TERMINATORS = frozenset(";|&<>(){}\n")
#: `shell:` values that leave a block under the shell the executed rules grade
#: it under. Anything carrying an argument (`bash {0}` drops the `-e`), a
#: path, another interpreter or whitespace is a custom command line.
SAFE_SHELLS = frozenset({"bash", "sh"})
#: The only `if:` a step in the evidence chain may carry: it WIDENS when the
#: step runs. Every other expression can evaluate false.
PERMITTED_CHAIN_CONDITION = "always()"
#: GitHub's ceiling on `timeout-minutes` for a job. A larger value parses and
#: is silently reduced to this, so `historical-purchase.yml` declaring 1440
#: promised itself a day and was always going to be killed at six hours. The
#: parser accepts it; only this rule refuses it.
GITHUB_JOB_TIMEOUT_CEILING_MINUTES = 360
#: The runner family the executed rules model. GitHub's default shell is
#: `bash -e {0}` on Linux and `pwsh` on Windows, with no `shell:` key
#: appearing anywhere — so the runner IS a shell declaration.
LINUX_RUNNER = re.compile(r"^ubuntu-")


# --------------------------------------------------------------------------
# Reading the corpus.
# --------------------------------------------------------------------------


def workflow_files_in(directory: Path) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.iterdir() if p.is_file() and p.suffix in {".yml", ".yaml"})


WORKFLOW_FILES = workflow_files_in(WORKFLOWS_DIR)
GATE_FILES = [p for p in WORKFLOW_FILES if p.name in GATE_WORKFLOWS]

every_workflow = pytest.mark.parametrize("path", WORKFLOW_FILES, ids=[p.name for p in WORKFLOW_FILES])
every_gate_workflow = pytest.mark.parametrize("path", GATE_FILES, ids=[p.name for p in GATE_FILES])


def load(path: Path) -> Any:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def triggers(document: Any) -> Any:
    """The `on:` block, whichever of its two keys it landed under. Bare `on` is
    a YAML 1.1 boolean and lands under `True`; quoted it lands under `"on"`."""
    if isinstance(document, dict):
        if "on" in document:
            return document["on"]
        if True in document:
            return document[True]
    return None


def trigger_config(document: Any, event: str) -> Any:
    """The configuration of one event, or `False` if the event is absent.

    `None` means the event is present with no configuration (`pull_request:`
    on its own), which is distinct from absent."""
    trigger = triggers(document)
    if isinstance(trigger, dict):
        return trigger[event] if event in trigger else False
    if isinstance(trigger, list):
        return None if event in trigger else False
    if isinstance(trigger, str):
        return None if trigger == event else False
    return False


def mappings(node: Any) -> Iterator[dict]:
    """Every mapping in the document, at any depth. Placement is half the
    rule: a `permissions:` or an `env:` on a step is as dangerous as one at
    the top."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from mappings(value)
    elif isinstance(node, list):
        for item in node:
            yield from mappings(item)


def jobs_of(document: Any) -> dict[str, dict]:
    jobs = document.get("jobs") if isinstance(document, dict) else None
    if not isinstance(jobs, dict):
        return {}
    return {str(k): v for k, v in jobs.items() if isinstance(v, dict)}


def steps_of(job: dict) -> list[dict]:
    steps = job.get("steps")
    return [s for s in steps if isinstance(s, dict)] if isinstance(steps, list) else []


def steps_using(document: Any, action: str) -> Iterator[dict]:
    for mapping in mappings(document):
        uses = mapping.get("uses")
        if isinstance(uses, str) and uses.split("@", 1)[0] == action:
            yield mapping


def run_blocks(document: Any) -> Iterator[tuple[str, str]]:
    for mapping in mappings(document):
        command = mapping.get("run")
        if isinstance(command, str):
            yield str(mapping.get("name", "<unnamed step>")), command


def commands(block: str) -> list[str]:
    """The LOGICAL lines of a run block that bash will execute: comments
    dropped, continuations joined. `pytest \\` on one line and `-k slow` on
    the next hid the `-k` from every line-shaped rule."""
    joined: list[str] = []
    for raw in block.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if joined and CONTINUATION.search(joined[-1]):
            previous = joined[-1]
            if previous.endswith("\\"):
                previous = previous[:-1].rstrip()
            joined[-1] = f"{previous} {line}"
        else:
            joined.append(line)
    return [line[:-1].rstrip() if line.endswith("\\") else line for line in joined]


def tokens(line: str) -> list[str]:
    try:
        return shlex.split(line)
    except ValueError:
        return line.split()


def simple_commands(line: str) -> list[list[str]]:
    """The line split into its commands at shell operators, each as tokens.

    `cd x && git push origin HEAD:refs/heads/y` is two commands, and the push
    is the second. A regex anchored at the start of the line never saw it."""
    found: list[list[str]] = []
    current: list[str] = []
    for token in tokens(line):
        if token in SHELL_OPERATOR_TOKENS:
            if current:
                found.append(current)
            current = []
            continue
        current.append(token)
    if current:
        found.append(current)
    return found


# --------------------------------------------------------------------------
# The stub harness: run the block, read the exit code.
# --------------------------------------------------------------------------

HARNESS_SHELL = shutil.which("bash")

SHELL_KEYWORDS = frozenset(
    {"if", "then", "else", "elif", "fi", "for", "while", "until", "do", "done", "case",
     "esac", "in", "function", "select", "time", "coproc", "!", "{", "}", "[[", "]]"}
)
SHELL_BUILTINS = frozenset(
    {"set", "unset", "exit", "return", "echo", "printf", "test", "[", "]", ":", "true",
     "false", "cd", "pwd", "read", "eval", "exec", "export", "local", "shift", "trap",
     "source", ".", "wait", "break", "continue", "declare", "typeset", "let", "mapfile",
     "readarray", "alias", "unalias", "bind", "builtin", "caller", "command", "compgen",
     "complete", "dirs", "disown", "enable", "fc", "fg", "bg", "getopts", "hash", "help",
     "history", "jobs", "kill", "logout", "popd", "pushd", "readonly", "suspend", "times",
     "type", "ulimit", "umask", "shopt"}
)
STUB_SAFE_NAME = re.compile(r"^[A-Za-z_./][A-Za-z0-9_./+-]*$")
PREFIX_ASSIGNMENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*\+?=")
COMMAND_NOT_FOUND = re.compile(r"[:\s]([^:\s]+): command not found")
RUNNER_FILE_VARIABLES = ("GITHUB_STEP_SUMMARY", "GITHUB_OUTPUT", "GITHUB_ENV", "GITHUB_PATH")
VARIABLE_WITH_DEFAULT = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\s*:?[-=+?]")
VARIABLE_BRACED = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)")
VARIABLE_BARE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)")


def _uncommented(block: str) -> str:
    return "\n".join(l for l in block.splitlines() if not l.strip().startswith("#"))


def _shell_regions(text: str) -> list[str]:
    """The text with `$(...)` and backtick spans lifted out, plus those spans.
    A command inside a substitution still runs, so it still needs a stub."""
    outer: list[str] = []
    inner: list[str] = []
    index, size = 0, len(text)
    while index < size:
        character = text[index]
        if character == "'":
            close = text.find("'", index + 1)
            close = size if close < 0 else close
            outer.append(text[index: close + 1])
            index = close + 1
            continue
        if character == "\\":
            outer.append(text[index: index + 2])
            index += 2
            continue
        if text.startswith("$(", index):
            depth, cursor = 1, index + 2
            while cursor < size and depth:
                if text[cursor] == "'":
                    close = text.find("'", cursor + 1)
                    cursor = (size if close < 0 else close) + 1
                    continue
                if text[cursor] == "\\":
                    cursor += 2
                    continue
                if text[cursor] == "(":
                    depth += 1
                elif text[cursor] == ")":
                    depth -= 1
                cursor += 1
            inner.append(text[index + 2: max(cursor - 1, index + 2)])
            outer.append(" ")
            index = cursor
            continue
        if character == "`":
            close = text.find("`", index + 1)
            close = size if close < 0 else close
            inner.append(text[index + 1: close])
            outer.append(" ")
            index = close + 1
            continue
        outer.append(character)
        index += 1
    regions = ["".join(outer)]
    for span in inner:
        regions.extend(_shell_regions(span))
    return regions


def _scan_command_words(region: str, found: list[str]) -> None:
    current: list[str] = []
    quote: str | None = None
    at_command, skip_next = True, False
    index, size = 0, len(region)

    def flush() -> None:
        nonlocal current, at_command, skip_next
        token = "".join(current)
        current = []
        if not token:
            return
        if skip_next:
            skip_next = False
            return
        if not at_command:
            return
        if token in SHELL_KEYWORDS or PREFIX_ASSIGNMENT.match(token):
            return
        at_command = False
        if token in SHELL_BUILTINS or re.fullmatch(r"[0-9]+", token):
            return
        if "$" in token or "*" in token or "?" in token:
            return
        if token not in found:
            found.append(token)

    while index < size:
        character = region[index]
        if quote is not None:
            if character == quote:
                quote = None
            elif quote == '"' and character == "\\":
                index += 1
            current.append(character)
            index += 1
            continue
        if character in "'\"":
            quote = character
            current.append(character)
            index += 1
            continue
        if character == "\\":
            index += 2
            continue
        if character in "<>":
            flush()
            skip_next = True
            index += 1
            continue
        if character == "\n" or character in ";|&(){}`":
            flush()
            at_command, skip_next = True, False
            index += 1
            continue
        if character.isspace():
            flush()
            index += 1
            continue
        current.append(character)
        index += 1
    flush()


def command_words(block: str) -> list[str]:
    """Every word this block would invoke as a command. Over-collection is
    safe (an unused stub) and under-collection is not (an unmodelled
    command), and the harness reports the second from the other side."""
    found: list[str] = []
    for region in _shell_regions(_uncommented(block)):
        _scan_command_words(region, found)
    return found


def referenced_variables(block: str) -> list[str]:
    named = set(VARIABLE_BRACED.findall(block)) | set(VARIABLE_BARE.findall(block))
    return sorted(named - set(VARIABLE_WITH_DEFAULT.findall(block)))


def _quote(text: str) -> str:
    return "'" + text.replace("'", "'\\''") + "'"


def stub_preamble(
    words: list[str],
    failing: set[str] | None,
    failure_log: Path,
    any_failure_log: Path,
    unmodelled_log: Path,
    marker: Path,
    invocation_log: Path | None = None,
) -> str:
    """One shell function per command word, of known exit status.

    Written flat rather than through a helper: bash does not inherit an ERR
    trap into a nested frame without `set -E`, and written nested a `trap
    'exit 0' ERR` was not caught. A failing stub logs to `failure_log` only
    when it ran in the top-level shell (the pid test keeps `echo "$(cmd)"`
    exempt) and to `any_failure_log` always, which is what sees a
    backgrounded failure.
    """
    assert HARNESS_SHELL, "no bash on PATH: the executed rules cannot run"
    lines = [
        "command_not_found_handle() { printf '%s\\n' \"$1\" >> " + _quote(str(unmodelled_log)) + "; return 127; }",
        "readonly PATH",
    ]
    for word in words:
        status = 1 if (failing is None or word in failing) else 0
        body = ["%s() {" % word]
        if invocation_log is not None:
            # What was invoked, with its arguments, and only from the TOP-LEVEL
            # shell — the same pid test the failure log uses, so a word inside
            # `echo "$(cmd)"` is not counted as the step having run it. This is
            # how `: python scripts/check_test_results.py x` is told apart from
            # actually running the gate: under `:` the word `python` is an
            # ARGUMENT and no stub is ever entered.
            body.append('  __INVOKE_PID="$( exec %s -c \'echo $PPID\' )"' % _quote(HARNESS_SHELL))
            body.append(
                '  if [ "$__INVOKE_PID" = "$$" ]; then { printf \'%s\' '
                + _quote(word)
                + '; printf \' %s\' "$@"; printf \'\\n\'; } >> '
                + _quote(str(invocation_log)) + "; fi"
            )
        if status:
            body.append("  printf '%s\\n' " + _quote(word) + " >> " + _quote(str(any_failure_log)))
            body.append('  __SWALLOW_PID="$( exec %s -c \'echo $PPID\' )"' % _quote(HARNESS_SHELL))
            body.append(
                '  if [ "$__SWALLOW_PID" = "$$" ]; then printf \'%s\\n\' '
                + _quote(word) + " >> " + _quote(str(failure_log)) + "; fi"
            )
        body.append("  printf 'stub:%s\\n' " + _quote(word))
        body.append("  return %d" % status)
        body.append("}")
        lines.append("\n".join(body))
    lines.append(": > %s" % _quote(str(marker)))
    return "\n".join(lines) + "\n"


class BlockRun(NamedTuple):
    exit_code: int
    top_level_failures: list[str]
    unmodelled: list[str]
    stderr: str
    any_failures: list[str]
    #: (command word, arguments) for every TOP-LEVEL invocation, when the run
    #: asked for them. Empty otherwise; the recording costs a subshell per
    #: call and only the gate rule needs it.
    invocations: tuple[tuple[str, tuple[str, ...]], ...] = ()


def run_block_under_stubs(
    block: str,
    failing: set[str] | None,
    sandbox: Path,
    *,
    present_dirs: tuple[str, ...] = (),
    record_invocations: bool = False,
    environment: dict[str, str] | None = None,
) -> BlockRun:
    """Execute one run block with every command replaced by a stub.

    `failing` is the set of command words whose stub returns 1; `None` means
    all of them; an empty set means none. Nothing real executes: PATH is an
    empty directory inside the sandbox, the working directory is the sandbox,
    and the environment is built from scratch. `present_dirs` are created in
    the sandbox first, for rules that need a directory to exist. `environment`
    adds variables the block reads under a `:-` default, which the harness
    otherwise leaves unset; it may not name PATH.

    A `:` is appended after the block. Without it a block that ends in a
    failing command exits non-zero whatever it did with the failure, so `set
    +e` would read as clean. With it the question is the right one: once a
    top-level command has failed, this block must not reach its end.
    """
    assert HARNESS_SHELL, "no bash on PATH: the executed rules cannot run"
    sandbox = Path(sandbox)
    failure_log = sandbox / "top_level_failures.txt"
    any_failure_log = sandbox / "any_failures.txt"
    unmodelled_log = sandbox / "unmodelled_commands.txt"
    invocation_log = sandbox / "invocations.txt"
    marker = sandbox / "preamble_completed"
    for log in (failure_log, any_failure_log, unmodelled_log, invocation_log):
        log.write_text("", encoding="utf-8")
    if marker.exists():
        marker.unlink()
    empty_path_dir = sandbox / "empty-path"
    empty_path_dir.mkdir(exist_ok=True)
    for name in present_dirs:
        (sandbox / name).mkdir(parents=True, exist_ok=True)

    words = command_words(block)
    unstubbable = [w for w in words if not STUB_SAFE_NAME.match(w)]
    preamble = stub_preamble(
        [w for w in words if STUB_SAFE_NAME.match(w)], failing,
        failure_log, any_failure_log, unmodelled_log, marker,
        invocation_log if record_invocations else None,
    )
    parsed = subprocess.run([HARNESS_SHELL, "-n"], input=preamble, capture_output=True, text=True)
    if parsed.returncode != 0:
        raise RuntimeError(f"the stub preamble does not parse: {parsed.stderr}")

    script = sandbox / "run_block.sh"
    script.write_text(preamble + block + "\n:\n", encoding="utf-8")
    environment_override = environment
    environment = {
        "PATH": str(empty_path_dir),
        "LC_ALL": "C",
        "HOME": str(sandbox),
        "GITHUB_WORKSPACE": str(sandbox),
        "RUNNER_TEMP": str(sandbox),
    }
    for name in RUNNER_FILE_VARIABLES:
        target = sandbox / name.lower()
        target.write_text("", encoding="utf-8")
        environment[name] = str(target)
    for name, value in (environment_override or {}).items():
        assert name != "PATH", "a block under stubs runs with an empty PATH and nothing else"
        environment[name] = value
    for name in referenced_variables(block):
        environment.setdefault(name, "__harness__")

    completed = subprocess.run(
        [HARNESS_SHELL, "-e", str(script)], cwd=sandbox, env=environment,
        capture_output=True, text=True, timeout=60,
    )
    if not marker.exists():
        raise RuntimeError(f"the stub preamble did not run to completion: {completed.stderr}")
    unmodelled = sorted(
        set(unstubbable)
        | set(unmodelled_log.read_text(encoding="utf-8").split())
        | set(COMMAND_NOT_FOUND.findall(completed.stderr))
    )
    invocations: list[tuple[str, tuple[str, ...]]] = []
    for line in invocation_log.read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if parts:
            invocations.append((parts[0], tuple(parts[1:])))
    return BlockRun(
        completed.returncode,
        failure_log.read_text(encoding="utf-8").split(),
        unmodelled,
        completed.stderr,
        any_failure_log.read_text(encoding="utf-8").split(),
        tuple(invocations),
    )


def swallow_findings(block: str) -> list[str]:
    """Run the block under every single-failure configuration; report swallows.

    Every command failing, then each command failing alone: with everything
    failing a block stops at its first gate and a swallow further down is
    never reached. A block carrying a background operator is judged on the
    second failure log as well.
    """
    findings: list[str] = []
    words = command_words(block)
    backgrounded = [
        line for line in commands(block)
        if BACKGROUND.search(without_quoted_spans(line)) or ASYNC_LAUNCHER.search(without_quoted_spans(line))
    ]
    with tempfile.TemporaryDirectory() as directory:
        sandbox = Path(directory)
        for failing in [None] + [{word} for word in words]:
            result = run_block_under_stubs(block, failing, sandbox)
            label = "every command failing" if failing is None else "only %s failing" % ", ".join(sorted(failing))
            if result.unmodelled:
                findings.append(
                    f"with {label}, {result.unmodelled} reached the shell with no stub "
                    "behind it, so this block was never modelled. A gate that could not "
                    "run the thing has not cleared it."
                )
                continue
            if result.exit_code == 0 and result.top_level_failures:
                findings.append(
                    f"with {label}, {sorted(set(result.top_level_failures))} failed and "
                    "the block still exited 0. In CI that is a green step over a failed command."
                )
                continue
            if result.exit_code == 0 and backgrounded and result.any_failures:
                findings.append(
                    f"with {label}, {sorted(set(result.any_failures))} failed and the "
                    f"block still exited 0 while running {backgrounded} in the background."
                )
    return findings


def without_quoted_spans(line: str) -> str:
    """The line with every quoted span replaced by spaces of the same width,
    so `echo 'set +e'` is not a disabled errexit and `echo "exit 1"` is not
    an exit."""
    text: list[str] = []
    index, size = 0, len(line)
    while index < size:
        character = line[index]
        if character == "\\":
            text.append(" ")
            index += 2
            continue
        if character in "'\"":
            cursor = index + 1
            while cursor < size:
                if character == '"' and line[cursor] == "\\":
                    cursor += 2
                    continue
                if line[cursor] == character:
                    break
                cursor += 1
            text.append(" " * (min(cursor, size - 1) - index + 1))
            index = cursor + 1
            continue
        text.append(character)
        index += 1
    return "".join(text)


def _top_level_pieces(line: str) -> list[list[str]]:
    blanked = without_quoted_spans(line)
    segments: list[list[str]] = []
    chunks: list[str] = []
    current: list[str] = []
    depth = 0
    index, size = 0, len(blanked)
    while index < size:
        character = blanked[index]
        if character in "({":
            depth += 1
        elif character in ")}":
            depth = max(0, depth - 1)
        if depth == 0 and blanked.startswith("||", index):
            chunks.append("".join(current))
            current = []
            index += 2
            continue
        if depth == 0 and blanked.startswith("&&", index):
            chunks.append("".join(current))
            segments.append(chunks)
            chunks, current = [], []
            index += 2
            continue
        if depth == 0 and character == ";":
            chunks.append("".join(current))
            segments.append(chunks)
            chunks, current = [], []
            index += 1
            continue
        current.append(character)
        index += 1
    chunks.append("".join(current))
    segments.append(chunks)
    return segments


def unguarded_or_branches(line: str) -> list[str]:
    """The `||` branches on this line that do NOT end in a non-zero exit,
    evaluated per or-list: an `exit 1` belonging to another command on the
    same line, or inside a quoted string, excuses nothing."""
    branches: list[str] = []
    for chunks in _top_level_pieces(line):
        if len(chunks) < 2 or CONDITION.search(chunks[0]):
            continue
        for position in range(1, len(chunks)):
            branch = "||".join(chunks[position:])
            if not NONZERO_EXIT.search(branch):
                branches.append(branch.strip())
    return branches


def pytest_arguments(line: str) -> list[str]:
    found = re.search(r"\bpytest\b", line)
    if found is None:
        return []
    return tokens(line[found.end():])


def pytest_lines(document: Any) -> Iterator[tuple[str, str]]:
    for name, block in run_blocks(document):
        for line in commands(block):
            if re.search(r"\bpytest\b", line):
                yield name, line


def gate_lines(document: Any) -> Iterator[tuple[str, str]]:
    for name, block in run_blocks(document):
        for line in commands(block):
            if GATE_SCRIPT in line:
                yield name, line


def same_path(text: str) -> str:
    return BRACED_VARIABLE.sub(r"$\1", text.strip())


def arguments_after(line: str, marker: str) -> list[str]:
    position = line.find(marker)
    if position < 0:
        return []
    tail = line[position + len(marker):]
    cut: list[str] = []
    quote: str | None = None
    for character in tail:
        if quote is not None:
            if character == quote:
                quote = None
            cut.append(character)
            continue
        if character in "'\"":
            quote = character
            cut.append(character)
            continue
        if character in COMMAND_TERMINATORS:
            break
        cut.append(character)
    arguments: list[str] = []
    for token in tokens("".join(cut)):
        if token in SHELL_OPERATOR_TOKENS:
            break
        arguments.append(token)
    return arguments


def junit_paths_on(line: str) -> list[str]:
    arguments = pytest_arguments(line)
    found: list[str] = []
    index = 0
    while index < len(arguments):
        head, _, tail = arguments[index].partition("=")
        if head in JUNIT_FLAGS:
            if tail:
                found.append(same_path(tail))
            elif index + 1 < len(arguments) and not arguments[index + 1].startswith("-"):
                found.append(same_path(arguments[index + 1]))
                index += 1
            else:
                found.append("")
        index += 1
    return found


def gate_path_on(line: str) -> str:
    for argument in arguments_after(line, GATE_SCRIPT):
        if not argument.startswith("-"):
            return same_path(argument)
    return ""


def steps_running(document: Any, marker: str) -> list[dict]:
    """Every STEP whose run block mentions `marker`, as the step mapping.

    `run_blocks` yields the text and loses the step, and a rule about a
    step's `env:` needs the step.
    """
    found: list[dict] = []
    for job in jobs_of(document).values():
        for step in steps_of(job):
            command = step.get("run")
            if isinstance(command, str) and any(re.search(marker, line) for line in commands(command)):
                found.append(step)
    return found


def tracked_paths() -> set[str]:
    """Every path `git ls-files` reports, for the rules that must know whether
    a path names a file the next clone will have."""
    result = subprocess.run(
        ["git", "ls-files", "-z"], cwd=PROJECT_ROOT, capture_output=True, check=True
    )
    return {item for item in result.stdout.decode("utf-8").split("\0") if item}


def junit_paths_written(document: Any) -> set[str]:
    return {p for _, line in pytest_lines(document) for p in junit_paths_on(line)}


def junit_paths_gated(document: Any) -> set[str]:
    return {gate_path_on(line) for _, line in gate_lines(document)}


def _condition(node: dict) -> str | None:
    """The `if:` as written, unwrapped from `${{ }}`. YAML parses `if: false`
    to the BOOLEAN False, so this stringifies before comparing."""
    if "if" not in node:
        return None
    raw = str(node["if"]).strip()
    if raw.startswith("${{") and raw.endswith("}}"):
        raw = raw[3:-2].strip()
    return raw


def required_check_jobs(paths: list[Path]) -> list[tuple[str, str, dict]]:
    """Every job across `paths` whose `name:` is the required check context."""
    found: list[tuple[str, str, dict]] = []
    for path in paths:
        document = load(path)
        for job_id, job in jobs_of(document).items():
            if job.get("name") == REQUIRED_CHECK:
                found.append((path.name, job_id, job))
    return found


def missing_subjects(paths: list[Path]) -> list[str]:
    """Which of the things the loop-shaped rules iterate over are absent from
    the whole corpus. A loop over nothing passes."""
    found = {"pytest": 0, "gate": 0, "checkout": 0, "python-version": 0, "upload": 0, "required-check": 0, "timeout-minutes": 0}
    for path in paths:
        document = load(path)
        found["pytest"] += sum(1 for _ in pytest_lines(document))
        found["gate"] += sum(1 for _ in gate_lines(document))
        found["checkout"] += sum(1 for _ in steps_using(document, "actions/checkout"))
        found["upload"] += sum(1 for _ in steps_using(document, "actions/upload-artifact"))
        found["python-version"] += sum(1 for m in mappings(document) if "python-version" in m)
        found["timeout-minutes"] += sum(1 for job in jobs_of(document).values() if "timeout-minutes" in job)
    found["required-check"] += len(required_check_jobs(paths))
    return sorted(subject for subject, count in found.items() if count == 0)


# --------------------------------------------------------------------------
# The corpus rules: every workflow.
# --------------------------------------------------------------------------


def check_parses_and_declares_a_trigger(path: Path) -> None:
    document = load(path)
    assert isinstance(document, dict), f"{path.name} did not parse to a mapping"
    assert triggers(document), f"{path.name} declares no `on:` trigger; a workflow that never runs reports nothing"


def check_no_trigger_is_path_filtered(path: Path) -> None:
    trigger = triggers(load(path))
    if not isinstance(trigger, dict):
        return
    for event, config in trigger.items():
        if not isinstance(config, dict):
            continue
        for key in ("paths", "paths-ignore"):
            assert key not in config, (
                f"{path.name}: `{event}` carries a `{key}:` filter. A path-filtered "
                "required check stays pending instead of passing, and the change that "
                "breaks a guard rarely touches the guard's own file."
            )


def check_permissions_are_declared_and_writers_are_the_closed_set(path: Path) -> None:
    """`permissions:` at the top, parsed; `contents: write` anywhere in the
    tree only in a declared writer."""
    document = load(path)
    assert isinstance(document, dict) and "permissions" in document, (
        f"{path.name} declares no top-level `permissions:`, so it inherits the "
        "repository default, which is not necessarily read."
    )
    writes = [
        m for m in mappings(document)
        if isinstance(m.get("permissions"), dict) and m["permissions"].get("contents") == "write"
    ]
    writes += [m for m in mappings(document) if m.get("permissions") == "write-all"]
    if path.name in WRITERS:
        assert writes, f"{path.name} is a declared writer and holds no `contents: write`"
    else:
        assert not writes, (
            f"{path.name} holds `contents: write` and is not in WRITERS. GitHub cannot "
            "scope that permission to a ref, so this is an undeclared way to write main."
        )


def check_git_pushes_target_the_declared_ref_and_never_force(path: Path) -> None:
    """Every `git push`, wherever on the line, from the tokens rather than a
    line-anchored regex: `cd x && git push` and `git  push` are pushes."""
    expected = WRITERS.get(path.name, "")
    for name, block in run_blocks(load(path)):
        for line in commands(block):
            for command in simple_commands(line):
                if len(command) < 2 or command[0] != "git" or command[1] != "push":
                    continue
                assert path.name in WRITERS, f"{path.name}: step {name!r} pushes and is not a declared writer: {line!r}"
                rest = command[2:]
                for token in rest:
                    assert token not in {"--force", "-f", "--force-with-lease"} and not token.startswith("--force"), (
                        f"{path.name}: step {name!r} force-pushes: {line!r}"
                    )
                    assert not token.startswith("+"), f"{path.name}: step {name!r} force-pushes via a `+` refspec: {line!r}"
                refspecs = [t for t in rest if not t.startswith("-")]
                assert len(refspecs) >= 2, (
                    f"{path.name}: step {name!r} pushes with no explicit refspec: {line!r}. "
                    "A push that lets git choose the destination is a push whose destination "
                    "this file cannot check."
                )
                for refspec in refspecs[1:]:
                    assert refspec.endswith(f":{expected}"), (
                        f"{path.name}: step {name!r} may push only to {expected}: {line!r}"
                    )


def check_no_workflow_stages_a_working_tree_wholesale(path: Path) -> None:
    """`git add` at any position on any line. The card feed is built with
    plumbing — hash-object, mktree, commit-tree — so only files named one at
    a time can ever be published."""
    for name, block in run_blocks(load(path)):
        for line in commands(block):
            for command in simple_commands(line):
                if len(command) >= 2 and command[0] == "git" and command[1] == "add":
                    assert "--dry-run" in command or "-n" in command, (
                        f"{path.name}: step {name!r} runs `git add`: {line!r}. The working "
                        "tree at publish time holds staged prices and possibly a .env."
                    )


def check_the_secrets_context_reaches_only_an_env_mapping(path: Path) -> None:
    """The secrets context, parsed: it may be the value of a key inside an
    `env:` mapping and nothing else — never inside a `run:`, a `with:`, or a
    name. Every accessor spelling, any casing, and `${{ secrets }}` whole."""
    document = load(path)

    def accesses(value: object) -> bool:
        if not isinstance(value, str):
            return False
        if SECRET_REFERENCE.search(value):
            return True
        return any(SECRETS_WORD.search(e.group(0)) for e in GITHUB_EXPRESSION.finditer(value))

    def walk(node: object, under_env: bool, where: str) -> None:
        if isinstance(node, dict):
            declared = [k for k in node if str(k).strip().lower() == "secrets"]
            assert not declared, (
                f"{path.name}: a `secrets:` key at {where}. `secrets: inherit` hands over "
                "every secret in the repository; an explicit block hands over the named ones."
            )
            for key, value in node.items():
                if isinstance(value, (dict, list)):
                    walk(value, str(key) == "env", f"{where}.{key}")
                elif accesses(value):
                    assert under_env, (
                        f"{path.name}: the secrets context is interpolated outside an "
                        f"`env:` mapping at {where}.{key}. The value must reach a process "
                        "through the environment, never a command line or an input."
                    )
                elif accesses(str(key)):
                    raise AssertionError(f"{path.name}: the secrets context in a KEY at {where}")
        elif isinstance(node, list):
            for i, item in enumerate(node):
                walk(item, False, f"{where}[{i}]")

    walk(document, False, path.stem)
    # And the raw text of every run block, comments included: a commented-out
    # `${{ secrets.X }}` inside a script is one uncomment away from live.
    for name, block in run_blocks(document):
        assert not accesses(block), f"{path.name}: step {name!r} references the secrets context inside its run block"


def check_the_credential_is_never_spelled_onto_a_command_line(path: Path) -> None:
    """`$CBB_ODDS_API_KEY` as an argument to anything. A textual rule and
    labelled as one: it reads the joined logical lines of each run block and
    allows exactly the presence test (`-z "$X"`) and the name inside a
    message."""
    for name, block in run_blocks(load(path)):
        for line in commands(block):
            for credential in CREDENTIAL_NAMES:
                if credential not in line:
                    continue
                stripped = re.sub(r'-z\s+"\$\{?%s(:-)?\}?"' % credential, "", line)
                stripped = re.sub(r'-n\s+"\$\{?%s(:-)?\}?"' % credential, "", stripped)
                assert not re.search(r"\$\{?" + credential, stripped), (
                    f"{path.name}: step {name!r} dereferences {credential} in a shell line: {line!r}"
                )


def check_credit_spending_workflows_carry_no_cron(path: Path) -> None:
    if path.name not in NO_CRON_WORKFLOWS:
        return
    assert trigger_config(load(path), "schedule") is False, (
        f"{path.name} carries a cron. The probe answers its question once per sport "
        "and the purchase is a one-way spend; neither repeats."
    )


def check_every_script_a_workflow_runs_exists(path: Path) -> None:
    referenced = set()
    for _, block in run_blocks(load(path)):
        for line in commands(block):
            referenced.update(re.findall(r"scripts/[A-Za-z0-9_]+\.py", line))
    missing = sorted(s for s in referenced if not (PROJECT_ROOT / s).is_file())
    assert not missing, f"{path.name} names scripts that do not exist: {missing}"


def check_job_timeouts_are_within_githubs_ceiling(path: Path) -> None:
    """Every `timeout-minutes` is a positive integer no larger than the
    ceiling GitHub enforces. An absent one is GitHub's default (the ceiling
    itself) and is allowed."""
    for job_id, job in jobs_of(load(path)).items():
        if "timeout-minutes" not in job:
            continue
        declared = job["timeout-minutes"]
        assert isinstance(declared, int) and not isinstance(declared, bool) and declared > 0, (
            f"{path.name}: job {job_id!r} declares `timeout-minutes: {declared!r}`, which is not a positive integer"
        )
        assert declared <= GITHUB_JOB_TIMEOUT_CEILING_MINUTES, (
            f"{path.name}: job {job_id!r} declares `timeout-minutes: {declared}`; GitHub caps a job at "
            f"{GITHUB_JOB_TIMEOUT_CEILING_MINUTES} and applies the cap silently, so this line promises "
            "time the run will never get"
        )


def check_python_version_is_pinned_to_an_exact_minor(path: Path) -> None:
    for mapping in mappings(load(path)):
        version = mapping.get("python-version")
        if version is None:
            continue
        assert isinstance(version, str), (
            f"{path.name}: python-version {version!r} is not a string. Unquoted 3.10 "
            "parses as the float 3.1."
        )
        assert re.fullmatch(r"\d+\.\d+", version), f"{path.name}: python-version {version!r} is not an exact X.Y pin."


CORPUS_CHECKS: dict[str, Callable[[Path], None]] = {
    "parses_and_declares_a_trigger": check_parses_and_declares_a_trigger,
    "no_trigger_is_path_filtered": check_no_trigger_is_path_filtered,
    "permissions_are_declared_and_writers_are_the_closed_set": check_permissions_are_declared_and_writers_are_the_closed_set,
    "git_pushes_target_the_declared_ref_and_never_force": check_git_pushes_target_the_declared_ref_and_never_force,
    "no_workflow_stages_a_working_tree_wholesale": check_no_workflow_stages_a_working_tree_wholesale,
    "the_secrets_context_reaches_only_an_env_mapping": check_the_secrets_context_reaches_only_an_env_mapping,
    "the_credential_is_never_spelled_onto_a_command_line": check_the_credential_is_never_spelled_onto_a_command_line,
    "credit_spending_workflows_carry_no_cron": check_credit_spending_workflows_carry_no_cron,
    "every_script_a_workflow_runs_exists": check_every_script_a_workflow_runs_exists,
    "python_version_is_pinned_to_an_exact_minor": check_python_version_is_pinned_to_an_exact_minor,
    "job_timeouts_are_within_githubs_ceiling": check_job_timeouts_are_within_githubs_ceiling,
}


# --------------------------------------------------------------------------
# The gate rules: tests.yml and ledger-guard.yml.
# --------------------------------------------------------------------------


def check_no_step_or_job_continues_on_error(path: Path) -> None:
    for mapping in mappings(load(path)):
        assert "continue-on-error" not in mapping, (
            f"{path.name}: `continue-on-error` on {mapping.get('name', 'a job')}. A step "
            "that reports success after failing is worse than no step."
        )


def check_no_gate_workflow_binds_a_credential(path: Path) -> None:
    for mapping in mappings(load(path)):
        environment = mapping.get("env")
        if not isinstance(environment, dict):
            continue
        bound = CREDENTIAL_NAMES.intersection(map(str, environment))
        assert not bound, f"{path.name}: `env:` binds {sorted(bound)}. The suite must pass with no credential in scope."


def check_permissions_are_read_only(path: Path) -> None:
    for mapping in mappings(load(path)):
        granted = mapping.get("permissions")
        if granted is None:
            continue
        rendered = " ".join(f"{k}:{v}" for k, v in granted.items()) if isinstance(granted, dict) else str(granted)
        assert "write" not in rendered, f"{path.name} grants write permission ({rendered}); a gate reads and never writes"


def check_checkout_never_persists_credentials(path: Path) -> None:
    for step in steps_using(load(path), "actions/checkout"):
        assert (step.get("with") or {}).get("persist-credentials") is False, (
            f"{path.name}: checkout does not set `persist-credentials: false`; a gate that can push can rewrite the evidence"
        )


def check_every_piped_run_block_sets_pipefail(path: Path) -> None:
    for name, block in run_blocks(load(path)):
        lines = [without_quoted_spans(l) for l in commands(block)]
        if not any(PIPELINE.search(l) for l in lines):
            continue
        assert ENABLES_PIPEFAIL.search(lines[0]), (
            f"{path.name}: step {name!r} pipes but does not open with `set -o pipefail`; "
            "the pipeline's status would be its last command's."
        )
        for line in lines:
            assert not DISABLES_PIPEFAIL.search(line), f"{path.name}: step {name!r} turns pipefail back off: {line!r}"


def check_no_run_block_swallows_a_failure(path: Path) -> None:
    """Every run block EXECUTED with its commands failing, and it must not
    exit 0. The textual nets are a cheap second net for the shapes execution
    cannot see (a subshell, a pipeline element)."""
    for name, block in run_blocks(load(path)):
        for line in commands(block):
            blanked = without_quoted_spans(line)
            assert not DISABLES_ERREXIT.search(blanked), f"{path.name}: step {name!r} turns off errexit: {line!r}"
            assert not PROCESS_SUBSTITUTION.search(blanked), f"{path.name}: step {name!r} uses process substitution: {line!r}"
            assert not BACKGROUND.search(blanked), f"{path.name}: step {name!r} backgrounds a command: {line!r}"
            assert not ASYNC_LAUNCHER.search(blanked), f"{path.name}: step {name!r} detaches a command: {line!r}"
            unguarded = unguarded_or_branches(line)
            assert not unguarded, f"{path.name}: step {name!r} swallows a failure: {line!r} -> {unguarded}"
        findings = swallow_findings(block)
        assert not findings, f"{path.name}: step {name!r} was executed under stubs and " + "; ".join(findings)


def check_the_suite_is_never_narrowed(path: Path) -> None:
    """Every argument after `pytest` is a flag, none narrows, and
    PYTEST_ADDOPTS appears in no env mapping and no run line."""
    document = load(path)
    for mapping in mappings(document):
        environment = mapping.get("env")
        if isinstance(environment, dict):
            bound = [k for k in environment if str(k).strip().upper() == PYTEST_ADDOPTS]
            assert not bound, f"{path.name}: `env:` binds {PYTEST_ADDOPTS} on {mapping.get('name', 'a job or the workflow')}"
    for name, block in run_blocks(document):
        for line in commands(block):
            assert not PYTEST_ADDOPTS_TOKEN.search(line), f"{path.name}: step {name!r} sets {PYTEST_ADDOPTS} from the shell: {line!r}"
    for name, line in pytest_lines(document):
        for argument in pytest_arguments(line):
            assert argument.startswith("-"), (
                f"{path.name}: step {name!r} passes the positional {argument!r} to pytest; a "
                "path selects a subset exactly as --ignore does"
            )
            if argument.startswith("--"):
                assert argument.split("=", 1)[0] not in NARROWING_PYTEST_LONG_FLAGS, f"{path.name}: step {name!r} narrows the suite with {argument}"
            elif argument != "-":
                narrowing = set(argument[1:].split("=", 1)[0]) & NARROWING_PYTEST_SHORT_FLAGS
                assert not narrowing, f"{path.name}: step {name!r} narrows the suite with {argument}"


def check_every_upload_fails_when_there_is_nothing_to_upload(path: Path) -> None:
    for step in steps_using(load(path), "actions/upload-artifact"):
        assert (step.get("with") or {}).get("if-no-files-found") == "error", (
            f"{path.name}: upload {step.get('name')!r} does not set `if-no-files-found: error`; "
            "an empty artifact lets 'nothing was compared' pass for a completed check"
        )


def check_the_suite_and_the_gate_are_both_present(path: Path) -> None:
    """Both ends of the evidence chain or neither, and never a delegated job."""
    document = load(path)
    for job_name, job in jobs_of(document).items():
        assert "uses" not in job, (
            f"{path.name}: job {job_name!r} delegates to {job['uses']!r}; every rule here "
            "reads run blocks and a called workflow has none here to read"
        )
    suite = [n for n, _ in pytest_lines(document)]
    gate = [n for n, _ in gate_lines(document)]
    assert bool(suite) == bool(gate), (
        f"{path.name}: the suite runs in {suite} and the gate runs in {gate}. One end of "
        f"the evidence chain is missing; pytest alone exits 0 on a skipped test."
    )


def check_the_gate_reads_the_evidence_this_run_wrote(path: Path) -> None:
    """The junit path pytest writes IS the path the gate reads, the gate is the
    tracked script, and no other line names that path."""
    document = load(path)
    written = junit_paths_written(document)
    gated = junit_paths_gated(document)
    if not written and not gated:
        return
    assert written, f"{path.name}: {GATE_SCRIPT} reads {sorted(gated)} and no pytest invocation writes a junit at all"
    assert gated, f"{path.name}: pytest writes {sorted(written)} and nothing invokes {GATE_SCRIPT}"
    assert written == gated, f"{path.name}: pytest writes {sorted(written)} and the gate reads {sorted(gated)}"
    for name, line in gate_lines(document):
        assert f"scripts/{GATE_SCRIPT}" in line, (
            f"{path.name}: step {name!r} runs a {GATE_SCRIPT} that is not the tracked "
            f"scripts/{GATE_SCRIPT}: {line!r}"
        )
    for name, block in run_blocks(document):
        for line in commands(block):
            normalised = BRACED_VARIABLE.sub(r"$\1", line)
            for junit in sorted(written):
                if not junit or junit not in normalised:
                    continue
                produced = junit_paths_on(line).count(junit)
                gated_here = int(GATE_SCRIPT in line and gate_path_on(line) == junit)
                assert produced or gated_here, (
                    f"{path.name}: step {name!r} names the junit path without producing or "
                    f"gating it: {line!r}. A step between the two can replace the evidence."
                )
                assert normalised.count(junit) <= produced + gated_here, (
                    f"{path.name}: step {name!r} names the junit path more often than it produces or gates it: {line!r}"
                )


def check_no_workflow_overrides_the_shell(path: Path) -> None:
    for mapping in mappings(load(path)):
        if "shell" not in mapping:
            continue
        declared = mapping["shell"]
        assert isinstance(declared, str) and declared in SAFE_SHELLS, (
            f"{path.name}: `shell: {declared!r}` on {mapping.get('name', 'a step, a job default or the workflow')}. "
            "`bash {0}` drops the errexit every executed rule assumes."
        )


def check_no_condition_disables_the_chain(path: Path) -> None:
    """A step that is present but never runs is a step that is gone. Only
    `always()` is permitted on a chain step, and no `if:` at all on its job."""
    document = load(path)
    for job_name, job in jobs_of(document).items():
        chain = [s for s in steps_of(job) if isinstance(s.get("run"), str) and ("pytest" in s["run"] or GATE_SCRIPT in s["run"] or LEDGER_SCRIPT in s["run"])]
        if not chain:
            continue
        assert _condition(job) is None, f"{path.name}: job {job_name!r} carries `if: {_condition(job)}` and contains the chain"
        for step in chain:
            condition = _condition(step)
            assert condition is None or condition == PERMITTED_CHAIN_CONDITION, (
                f"{path.name}: a chain step carries `if: {condition}`; only `{PERMITTED_CHAIN_CONDITION}` is permitted"
            )


def check_the_byte_compile_step_fails_on_a_missing_directory(path: Path) -> None:
    """`compileall` exits 0 on a path that does not exist, so the block has to
    be the thing that notices. Executed: every stub SUCCEEDING, in a sandbox
    with no `src/`, the block must exit non-zero; with the directories
    present it must exit zero; and `-f` must be passed, or a stale .pyc from
    the cache masks a module that no longer compiles."""
    document = load(path)
    blocks = [(n, b) for n, b in run_blocks(document) if any("compileall" in l for l in commands(b))]
    if path.name == TESTS_WORKFLOW:
        assert blocks, f"{path.name} has no byte-compile step"
    for name, block in blocks:
        directories: list[str] = []
        for line in commands(block):
            if "compileall" not in line:
                continue
            arguments = arguments_after(line, "compileall")
            assert "-f" in arguments, f"{path.name}: step {name!r} runs compileall without -f: {line!r}"
            directories += [a for a in arguments if not a.startswith("-")]
        assert directories, f"{path.name}: step {name!r} runs compileall over no directory"
        with tempfile.TemporaryDirectory() as directory:
            absent = run_block_under_stubs(block, set(), Path(directory))
            assert absent.unmodelled == [], f"{path.name}: step {name!r} could not be modelled: {absent.unmodelled}"
            assert absent.exit_code != 0, (
                f"{path.name}: step {name!r} exits 0 with {directories} absent. compileall "
                "reports nothing for a path that is not there, so the block must assert "
                "each directory exists before compiling it."
            )
        with tempfile.TemporaryDirectory() as directory:
            present = run_block_under_stubs(block, set(), Path(directory), present_dirs=tuple(directories))
            assert present.exit_code == 0, f"{path.name}: step {name!r} fails even with {directories} present; a step that always fails gets deleted"


def check_the_required_check_is_pinned(path: Path) -> None:
    """The job branch protection would gate on, pinned property by property.

    Exactly one job in the whole corpus carries `name: Tests`, it is in
    tests.yml, it is not delegated, it carries no `if:`, no `needs:`, no
    `continue-on-error`, no `strategy:` (a matrix renames the context), runs
    on a Linux runner (the executed rules model bash), and its pytest and
    gate steps carry no `shell:`, no `working-directory:`, no condition but
    `always()`. The workflow fires on pull_request with no branches or paths
    filter, and on push.

    `needs:` IS `if: false` REWORDED, and it is one line. A required job with
    `needs: prep`, where `prep` carries `if: false` or simply fails, does not
    run — and GitHub's own troubleshooting documentation says a required
    check SKIPPED BY A CONDITION is reported as **Success**. (A check skipped
    by a PATH filter stays pending, which is why `no_trigger_is_path_filtered`
    is a different rule with a different reason.) So `needs` is refused on the
    required job outright, and no OTHER job in this file may carry an `if:` at
    all: a conditional job that nothing depends on is harmless today and is
    one word — a `needs:` — away from disabling the check.
    """
    if path.name != TESTS_WORKFLOW:
        return
    document = load(path)
    assert document.get("name") == REQUIRED_CHECK, f"{path.name} is not named {REQUIRED_CHECK!r}"
    everywhere = required_check_jobs(WORKFLOW_FILES if path.parent == WORKFLOWS_DIR else [path])
    assert len(everywhere) == 1, (
        f"{len(everywhere)} jobs carry name: {REQUIRED_CHECK!r} ({[(f, j) for f, j, _ in everywhere]}). "
        "Exactly one job may report the required check; zero leaves it pending forever "
        "and two makes the context ambiguous."
    )
    assert everywhere[0][0] == path.name, f"the required check lives in {everywhere[0][0]}, not {path.name}"
    job = everywhere[0][2]
    assert "uses" not in job, "the required check delegates to a reusable workflow"
    assert "strategy" not in job, "the required check runs a matrix; the context becomes `Tests (…)` and the protected name never reports"
    assert "if" not in job, f"the required check carries `if: {_condition(job)}`"
    assert "needs" not in job, (
        f"the required check carries `needs: {job.get('needs')!r}`. A job it waits on "
        "can be skipped by its own `if:` or fail, and GitHub reports a required check "
        "skipped by a condition as Success. One line, and the gate is gone."
    )
    conditional = {
        job_id: _condition(other)
        for job_id, other in jobs_of(document).items()
        if other is not job and _condition(other) is not None
    }
    assert not conditional, (
        f"{path.name}: {conditional} carry an `if:`. Only the required job runs here, "
        "and a conditional job beside it is one `needs:` away from skipping the check "
        "into a green tick."
    )
    assert "continue-on-error" not in job, "the required check continues on error"
    assert isinstance(job.get("runs-on"), str) and LINUX_RUNNER.match(job["runs-on"]), (
        f"the required check runs on {job.get('runs-on')!r}; the executed rules model `bash -e`, which is Linux's default and not Windows'"
    )
    defaults = (job.get("defaults") or {}).get("run") or {}
    assert "shell" not in defaults and "working-directory" not in defaults, "the required check's job defaults change the shell or directory"
    top_defaults = (document.get("defaults") or {}).get("run") or {}
    assert "shell" not in top_defaults and "working-directory" not in top_defaults, "workflow defaults change the shell or directory"
    steps = steps_of(job)
    suite_steps = [s for s in steps if isinstance(s.get("run"), str) and re.search(r"\bpytest\b", s["run"])]
    gate_steps = [s for s in steps if isinstance(s.get("run"), str) and GATE_SCRIPT in s["run"]]
    assert suite_steps, "the required check has no step that runs pytest"
    assert gate_steps, f"the required check has no step that runs {GATE_SCRIPT}"
    for step in suite_steps + gate_steps:
        assert "continue-on-error" not in step, f"chain step {step.get('name')!r} continues on error"
        assert "shell" not in step, f"chain step {step.get('name')!r} overrides the shell"
        assert "working-directory" not in step, f"chain step {step.get('name')!r} moves the working directory; a smaller tree is a smaller suite"
        condition = _condition(step)
        assert condition is None or condition == PERMITTED_CHAIN_CONDITION, f"chain step {step.get('name')!r} carries `if: {condition}`"
    for step in suite_steps:
        assert _condition(step) is None, f"the suite step carries `if: {_condition(step)}`; the suite runs unconditionally"
    pull_request = trigger_config(document, "pull_request")
    assert pull_request is not False, f"{path.name} does not fire on pull_request, so no PR is ever checked"
    if isinstance(pull_request, dict):
        for key in ("branches", "branches-ignore", "paths", "paths-ignore", "types"):
            assert key not in pull_request, f"{path.name}: pull_request carries `{key}:`; a filtered required check does not report on the PRs it filters out"
    assert trigger_config(document, "push") is not False, f"{path.name} does not fire on push"


def check_the_suite_line_carries_only_whitelisted_arguments(path: Path) -> None:
    """The suite line's arguments, against a WHITELIST, and the junit pinned.

    `check_the_suite_is_never_narrowed` reads a blocklist, and a blocklist is
    a list of spellings. `python -m pytest --version --junit-xml=<path>` is
    not on it: `--version` exits 0, runs nothing and writes NO junit, so
    whatever already sits at that path is what the gate reads. Point the flag
    at a tracked file and the gate passes over committed evidence while the
    clean-tree check sees nothing move, because nothing did.

    So: every argument must be one of `SUITE_ARGUMENT_WHITELIST` or the junit
    flag in its `=` form; there must be exactly one junit; and that path must
    begin with the runner's temp directory, contain no `..`, and name no
    tracked file. The freshness marker in `scripts/check_test_results.py` is
    the other half — this rule stops the argument that writes no junit, and
    that one stops evidence written before the run.
    """
    tracked = tracked_paths()
    for name, line in pytest_lines(load(path)):
        arguments = pytest_arguments(line)
        junits: list[str] = []
        for argument in arguments:
            head, separator, tail = argument.partition("=")
            if head in JUNIT_FLAGS:
                assert separator and tail, (
                    f"{path.name}: step {name!r} spells the junit flag as {argument!r}. "
                    "It must be `--junit-xml=<path>`: the separated form hides the "
                    "path from an argument-by-argument read."
                )
                junits.append(same_path(tail))
                continue
            assert argument in SUITE_ARGUMENT_WHITELIST, (
                f"{path.name}: step {name!r} passes {argument!r} to pytest. The suite "
                f"line may carry only {sorted(SUITE_ARGUMENT_WHITELIST)} and one "
                "--junit-xml=<path>. This is a whitelist because the blocklist let "
                "--version, -h and --help through, and each exits 0 and writes no junit."
            )
        assert len(junits) == 1, (
            f"{path.name}: step {name!r} writes {len(junits)} junit path(s) ({junits}); "
            "exactly one is required, or the gate has nothing to read or a choice of what to read"
        )
        junit = junits[0]
        assert junit.startswith(RUNNER_TEMP_PREFIXES), (
            f"{path.name}: step {name!r} writes its junit to {junit!r}. It must be "
            f"under one of {list(RUNNER_TEMP_PREFIXES)}: the runner's temp directory "
            "is fresh every run, and a path inside the checkout can be a tracked file."
        )
        remainder = junit
        for prefix in RUNNER_TEMP_PREFIXES:
            if remainder.startswith(prefix):
                remainder = remainder[len(prefix):]
                break
        assert ".." not in Path(remainder).parts, (
            f"{path.name}: step {name!r} escapes the runner temp with {junit!r}"
        )
        assert remainder not in tracked and junit not in tracked, (
            f"{path.name}: step {name!r} writes its junit at {junit!r}, which is a "
            "tracked path. Committed evidence is not this run's evidence."
        )


def check_the_gate_line_is_pinned_as_a_whole_command(path: Path) -> None:
    """The gate's command line, token by token, not searched for by substring.

    Every other rule asked whether a line CONTAINS `check_test_results.py`
    and the junit path. `: python scripts/check_test_results.py "$RUNNER_TEMP/
    junit.xml"` contains both, satisfies all of them, and runs nothing: `:`
    is a shell builtin that ignores its arguments and returns 0. Measured
    2026-09-04 — that line passed all fourteen gate rules, and so did the
    same line behind `echo`.

    The shape is pinned instead: `python scripts/check_test_results.py
    <junit> --newer-than <marker>`, with both paths under the runner's temp.
    `check_the_gate_step_really_runs_the_gate` is the executed half.
    """
    document = load(path)
    gate_steps = steps_running(document, re.escape(GATE_SCRIPT))
    if not gate_steps:
        return
    for step in gate_steps:
        lines = [line for line in commands(step["run"]) if not line.startswith("set ")]
        assert len(lines) == 1, (
            f"{path.name}: the gate step {step.get('name')!r} runs {len(lines)} commands "
            f"({lines}); it runs the gate and nothing else"
        )
        found = tokens(same_path(lines[0]))
        assert tuple(found[:2]) == GATE_COMMAND_SHAPE, (
            f"{path.name}: the gate step {step.get('name')!r} begins with {found[:2]} "
            f"and must begin with {list(GATE_COMMAND_SHAPE)}. A line that merely "
            "CONTAINS the script — behind a `:`, an `echo`, or any other word — "
            "passes every substring rule and executes nothing."
        )
        assert len(found) == 5 and found[3] == GATE_MARKER_FLAG, (
            f"{path.name}: the gate step {step.get('name')!r} runs {found}; the pinned "
            f"command is {list(GATE_COMMAND_SHAPE)} <junit> {GATE_MARKER_FLAG} <marker>"
        )
        for argument in (found[2], found[4]):
            assert argument.startswith(RUNNER_TEMP_PREFIXES), (
                f"{path.name}: the gate step reads {argument!r}, which is not under "
                f"one of {list(RUNNER_TEMP_PREFIXES)}"
            )


def check_the_gate_step_really_runs_the_gate(path: Path) -> None:
    """Executed: the gate step must actually invoke the script.

    Every stub succeeds and the invocations are recorded, so the question is
    not what the line says but which command word the shell entered and with
    what first argument. Under `: python scripts/check_test_results.py x` the
    word `python` is an ARGUMENT to a builtin, no stub is entered, and this
    rule sees an empty invocation list — which is the finding.
    """
    document = load(path)
    gate_steps = steps_running(document, re.escape(GATE_SCRIPT))
    if not gate_steps:
        return
    for step in gate_steps:
        with tempfile.TemporaryDirectory() as directory:
            result = run_block_under_stubs(step["run"], set(), Path(directory), record_invocations=True)
            assert result.unmodelled == [], (
                f"{path.name}: the gate step {step.get('name')!r} could not be modelled: {result.unmodelled}"
            )
            ran_the_gate = [
                (word, arguments) for word, arguments in result.invocations
                if arguments and arguments[0] == f"scripts/{GATE_SCRIPT}"
            ]
            assert ran_the_gate, (
                f"{path.name}: the gate step {step.get('name')!r} was executed under stubs "
                f"and never invoked anything with scripts/{GATE_SCRIPT} as its first "
                f"argument. Top-level invocations were {list(result.invocations)}. A step "
                "that names the gate without running it is a step that has checked nothing."
            )


def check_the_suite_step_disables_the_path_shadows(path: Path) -> None:
    """`PYTHONSAFEPATH: '1'` on the step that runs pytest.

    `python -m pytest` puts the working directory at the head of sys.path, so
    a tracked `pytest.py` at the repository root IS pytest for that step —
    measured on 2026-09-04: exit 0, no junit, and the workflow untouched, so
    no rule in this file could see it. `tests/test_the_guards_exist.py` bans
    the tracked file; this is the interpreter refusing to look there at all.
    """
    document = load(path)
    for step in steps_running(document, r"\bpytest\b"):
        environment = step.get("env")
        value = environment.get(SAFE_PATH_VARIABLE) if isinstance(environment, dict) else None
        assert str(value) == "1", (
            f"{path.name}: the step {step.get('name')!r} runs pytest without "
            f"`{SAFE_PATH_VARIABLE}: '1'` in its env (found {value!r}). A tracked "
            "pytest.py at the root replaces the suite without touching this file."
        )


def check_the_required_workflow_holds_no_secret_at_all(path: Path) -> None:
    """`tests.yml` gets no credential, so the secrets context may not appear in
    it at all — not even in an `env:` mapping, which the corpus rule permits.

    `check_the_secrets_context_reaches_only_an_env_mapping` is deliberately the
    looser rule, because the operational workflows genuinely do bind a
    credential that way. This file does not: its own header says the job is
    given no credential deliberately, the suite must pass without one, and a
    step below asserts that at run time. Measured before this rule existed:
    binding `TOK` to the secrets context on the suite step's `env:` passed the
    whole module, while the header two hundred lines above claimed the linter
    "refuses the secrets context anywhere in this file". The rule now matches
    the sentence instead of the sentence matching nothing.

    Scoped to the required workflow by name, so adding a credential to a
    gameday or purchase workflow is still the corpus rule's business.
    """
    if path.name != TESTS_WORKFLOW:
        return
    text = path.read_text(encoding="utf-8")
    for number, line in enumerate(text.splitlines(), start=1):
        if line.lstrip().startswith("#"):
            continue
        assert not SECRET_REFERENCE.search(line) and not any(
            SECRETS_WORD.search(e.group(0)) for e in GITHUB_EXPRESSION.finditer(line)
        ), (
            f"{path.name}:{number} reaches the secrets context. This job is given no "
            "credential deliberately — that is what proves no test depends on a live "
            "provider and what makes a run on a fork safe. The name may appear in prose; "
            "the context may not appear at all."
        )


GATE_CHECKS: dict[str, Callable[[Path], None]] = {
    "no_step_or_job_continues_on_error": check_no_step_or_job_continues_on_error,
    "no_gate_workflow_binds_a_credential": check_no_gate_workflow_binds_a_credential,
    "permissions_are_read_only": check_permissions_are_read_only,
    "checkout_never_persists_credentials": check_checkout_never_persists_credentials,
    "every_piped_run_block_sets_pipefail": check_every_piped_run_block_sets_pipefail,
    "no_run_block_swallows_a_failure": check_no_run_block_swallows_a_failure,
    "the_suite_is_never_narrowed": check_the_suite_is_never_narrowed,
    "every_upload_fails_when_there_is_nothing_to_upload": check_every_upload_fails_when_there_is_nothing_to_upload,
    "the_suite_and_the_gate_are_both_present": check_the_suite_and_the_gate_are_both_present,
    "the_gate_reads_the_evidence_this_run_wrote": check_the_gate_reads_the_evidence_this_run_wrote,
    "no_workflow_overrides_the_shell": check_no_workflow_overrides_the_shell,
    "no_condition_disables_the_chain": check_no_condition_disables_the_chain,
    "the_byte_compile_step_fails_on_a_missing_directory": check_the_byte_compile_step_fails_on_a_missing_directory,
    "the_required_check_is_pinned": check_the_required_check_is_pinned,
    "the_suite_line_carries_only_whitelisted_arguments": check_the_suite_line_carries_only_whitelisted_arguments,
    "the_gate_line_is_pinned_as_a_whole_command": check_the_gate_line_is_pinned_as_a_whole_command,
    "the_gate_step_really_runs_the_gate": check_the_gate_step_really_runs_the_gate,
    "the_suite_step_disables_the_path_shadows": check_the_suite_step_disables_the_path_shadows,
    "the_required_workflow_holds_no_secret_at_all": check_the_required_workflow_holds_no_secret_at_all,
}


# --------------------------------------------------------------------------
# The rules applied to the real workflows.
# --------------------------------------------------------------------------


def test_the_workflow_directory_is_not_empty() -> None:
    assert WORKFLOWS_DIR.is_dir(), f"{WORKFLOWS_DIR} does not exist"
    assert WORKFLOW_FILES, f"No workflow files under {WORKFLOWS_DIR}; every rule here would pass by having nothing to check"


def test_every_gate_workflow_exists() -> None:
    """Absence is never a pass. A deleted tests.yml is not a workflow that
    passes every rule; it is no required check at all.

    Named `test_both_gate_workflows_exist` while there were two; renamed when
    `policy-gate.yml` made it three, because a test whose name says `both`
    over a set of three is a sentence that has stopped being true.
    """
    present = {p.name for p in GATE_FILES}
    assert present == set(GATE_WORKFLOWS), f"gate workflows missing: {sorted(set(GATE_WORKFLOWS) - present)}"


def test_the_executed_rules_have_a_shell_to_run_in() -> None:
    assert HARNESS_SHELL, "bash is not on PATH; the executed rules cannot report anything, which is a broken gate and not a clean one"


@every_workflow
@pytest.mark.parametrize("rule", sorted(CORPUS_CHECKS), ids=sorted(CORPUS_CHECKS))
def test_every_workflow_obeys_the_corpus_rules(path: Path, rule: str) -> None:
    CORPUS_CHECKS[rule](path)


@every_gate_workflow
@pytest.mark.parametrize("rule", sorted(GATE_CHECKS), ids=sorted(GATE_CHECKS))
def test_every_gate_workflow_obeys_the_gate_rules(path: Path, rule: str) -> None:
    GATE_CHECKS[rule](path)


def test_exactly_one_job_in_the_corpus_reports_the_required_check() -> None:
    found = required_check_jobs(WORKFLOW_FILES)
    assert [(f, j) for f, j, _ in found] == [(TESTS_WORKFLOW, "tests")], found


def test_no_rule_in_this_file_is_vacuous() -> None:
    missing = missing_subjects(WORKFLOW_FILES)
    assert not missing, f"Nothing under {WORKFLOWS_DIR} contains: {missing}; the rules iterate over these and report green over nothing"


def test_every_real_gate_run_block_is_actually_executed() -> None:
    blocks = [(p.name, n, b) for p in GATE_FILES for n, b in run_blocks(load(p))]
    assert blocks, "no run block in any gate workflow"
    stubbed = {(f, n): command_words(b) for f, n, b in blocks}
    assert any(stubbed.values()), f"no gate run block yields a command word: {stubbed}"


def test_the_purchase_workflow_names_the_directory_the_module_actually_writes() -> None:
    """The most expensive defect in this repository, pinned: the purchase
    workflow cached and uploaded a hand-spelled path the module never wrote,
    and a 1,299,945-credit run persisted only its own report."""
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.providers import historical as H

    path = WORKFLOWS_DIR / "historical-purchase.yml"
    assert path.is_file(), "historical-purchase.yml is missing"
    text = path.read_text(encoding="utf-8")
    for window in (H.CARD_WINDOW, H.CLOSE_WINDOW):
        expected = str(H.cache_dir_for(CBB, Path("data/raw"), window).parent)
        assert expected in text, f"the purchase workflow does not mention {expected!r}, where `cache_dir_for` writes"


def test_the_purchase_workflow_builds_the_store_it_uploads() -> None:
    path = WORKFLOWS_DIR / "historical-purchase.yml"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "--rebuild" in text, "nothing in the purchase workflow rebuilds the store from the cached responses"
    # The STORE upload, by name. The first `upload-artifact` in the file is now
    # the raw-response upload, which deliberately precedes the rebuild (defect
    # S: persist the purchase before anything that can die). Anchoring on the
    # first occurrence made this test fail on the fix for a worse defect.
    store_upload = text.index("Upload the store, the record and the cache")
    assert text.index("--rebuild") < store_upload, (
        "the store is rebuilt after it is uploaded, so the artifact carries the "
        "previous run's store or none at all"
    )


def test_the_weekly_loop_measures_the_newest_bought_store_and_not_a_pinned_cache_key(
    tmp_path: Path,
) -> None:
    """`actions/cache` writes at its post-step ONLY when the primary key MISSED.

    The weekly loop's key — `cbb-data-v1-<WEEKLY_SEASONS>-<hashFiles(...)>` — is
    the same string every Monday, so the first Monday missed and saved, and
    every Monday after it hit that key exactly, restored the first Monday's
    `data/processed` with the bought price store inside it, and saved nothing.
    Every purchase made after that first Monday was invisible to the loop,
    which re-measured one frozen store for the rest of the season and read
    exactly like a lab that was running.

    The replacement is pinned here on four points, two of them executed. The
    card store is deleted BEFORE anything that can fail, so no path through
    the step leaves a store of unknown provenance behind — `run_weekly_loop.py`
    can report a population that is MISSING and cannot report one that is
    STALE. It is refetched from the newest purchase run whose store artifact
    has not expired. The raw-response artifact is excluded by name, because
    `historical-cache-<wave>-<window>` also ends in the window and is the
    gigabytes this step must not pull. And the run it came from and the row
    count reach the job summary, so a store that did not move this week is
    something the run says rather than something nobody can see.
    """
    from cbb_betting_lab.competitions import CBB
    from cbb_betting_lab.providers import historical as H

    path = WORKFLOWS_DIR / "weekly-refit-and-measure.yml"
    assert path.is_file(), "weekly-refit-and-measure.yml is missing"
    document = load(path)

    permissions = document.get("permissions")
    assert permissions == {"contents": "read", "actions": "read"}, (
        f"the weekly loop's permissions are {permissions!r}. It needs `actions: "
        "read` to reach the purchase's store artifact and must never hold "
        "`contents: write`."
    )

    steps = steps_of(next(iter(jobs_of(document).values())))
    restore = [i for i, s in enumerate(steps) if s.get("id") == "store"]
    loop = [i for i, s in enumerate(steps) if "run_weekly_loop.py" in str(s.get("run", ""))]
    assert restore, (
        "no step with `id: store` restores the bought price store. Without it "
        "the store arrives only inside the pinned `cbb-data-v1` cache, which "
        "saves once and is then frozen for the rest of the season."
    )
    assert loop, "no step in the weekly workflow runs run_weekly_loop.py"
    assert restore[0] < loop[0], (
        "the store is restored after the loop that measures it, so the loop "
        "reads whatever the cache left behind"
    )

    step = steps[restore[0]]
    environment = step.get("env", {})
    assert environment.get("WINDOW") == H.CARD_WINDOW.name, (
        f"the step names window {environment.get('WINDOW')!r}; the loop's "
        f"backtest scores {H.CARD_WINDOW.name!r}"
    )
    expected_store = str(H.store_path(CBB, Path("data/processed"), H.CARD_WINDOW))
    assert environment.get("STORE") == expected_store, (
        f"the step names {environment.get('STORE')!r}; `historical.store_path` "
        f"writes {expected_store!r}. A hand-spelled path the module never "
        "writes is the defect this repository already paid 1,299,945 credits for."
    )
    purchase = environment.get("PURCHASE_WORKFLOW", "")
    assert (WORKFLOWS_DIR / purchase).is_file(), (
        f"the step reads artifacts from {purchase!r}, which is not a workflow "
        "in this repository"
    )
    assert "Upload the store, the record and the cache" in (
        (WORKFLOWS_DIR / purchase).read_text(encoding="utf-8")
    ), f"{purchase} does not upload a store artifact for this step to read"

    block = str(step.get("run", ""))
    lines = commands(block)
    removals = [i for i, line in enumerate(lines) if '"$STORE"' in line and line.split()[0] == "rm"]
    # `command_words`, not the first token: `RUN_IDS=$(gh run list ...)` is a
    # call to `gh` and its first token is an assignment.
    gh_calls = [i for i, line in enumerate(lines) if "gh" in command_words(line)]
    assert removals, "the step never deletes the store the pinned cache restored"
    assert gh_calls, "the step never asks the purchase workflow for anything"
    assert max(removals) < min(gh_calls), (
        "the stale store is deleted after the first command that can fail, so a "
        "failed lookup leaves last season's store on disk for the loop to "
        "re-measure as though it were this week's"
    )
    assert "historical-cache-" in block, (
        "the step does not exclude `historical-cache-<wave>-<window>`, the raw "
        "response artifact, which also ends in the window name and is orders of "
        "magnitude larger than the store"
    )
    reported = [
        line for line in lines
        if "GITHUB_STEP_SUMMARY" in line and "ROWS" in line and "FROM_RUN" in line
    ]
    assert reported, (
        "no line writes both the run the store came from and its row count to "
        f"the job summary; the step writes: {lines}"
    )
    assert any("::warning::" in line for line in lines), (
        "the step restores nothing quietly when no artifact survives"
    )

    def sandbox(name: str) -> Path:
        made = tmp_path / name
        made.mkdir()
        return made

    # EXECUTED, because the ordering above is a claim about what runs and not
    # about what is spelled. With BOTH `rm` and `gh` failing, whichever the
    # block reaches first is the one that gets logged: `rm` here, and `gh` from
    # any version that asks the purchase for an artifact while last season's
    # store is still on disk.
    stopped = run_block_under_stubs(block, {"rm", "gh"}, sandbox("rm"))
    assert stopped.exit_code != 0, "a failed removal is swallowed"
    assert stopped.any_failures == ["rm"], (
        "the block did not reach the removal first, so a failed lookup leaves a "
        f"store of unknown provenance on disk: {stopped.any_failures}"
    )
    assert not stopped.unmodelled, stopped.unmodelled

    # And a failed lookup or download is not swallowed either. The step's own
    # `continue-on-error` is the deliberate soft edge — the refit and the
    # demotion check do not read this store — but the block itself must report.
    unreachable = run_block_under_stubs(block, {"gh"}, sandbox("gh"))
    assert unreachable.exit_code != 0, (
        "the block reaches its end after `gh` failed, so a run that could not "
        "read the purchase reports a clean restore"
    )
    assert not unreachable.unmodelled, unreachable.unmodelled


# --------------------------------------------------------------------------
# The gameday workflow's fault paths, executed rather than read.
#
# The gameday workflow is operational: it keeps `continue-on-error` and `||
# true` on purpose, so the gate rules do not apply to it. These tests take
# three of its run blocks — restore, card, publish — render the `${{ }}`
# context GitHub would, and execute them: under stubs, where the question is
# which exit code the block reaches its end with; and, for the restore step,
# against a real scratch remote, where the question is whether an absent
# branch and a failed fetch are told apart.
# --------------------------------------------------------------------------

GAMEDAY_WORKFLOW = "cbb-gameday-refresh.yml"
#: `${{ expr }}`, which GitHub substitutes before bash ever sees the block. Bash
#: reads an unrendered one as a bad substitution, so the harness renders them
#: first, and refuses an expression it was not given a value for.
EXPRESSION = re.compile(r"\$\{\{\s*(.*?)\s*\}\}")
#: The one line of the restore step that names the real remote. The real-git
#: test replaces exactly this line with a scratch path and nothing else, so a
#: change to how the remote is spelled is a change this test sees.
RESTORE_REMOTE_LINE = 'REMOTE="https://x-access-token:${GH_TOKEN}@github.com/${{ github.repository }}"'
#: What the `${{ }}` context holds on a real scheduled morning run, as far as
#: these three blocks read it. Outcomes are supplied per case.
GAMEDAY_CONTEXT: dict[str, str] = {
    "github.repository": "owner/repository",
    "github.server_url": "https://github.com",
    "github.run_id": "1",
    "inputs.rehearsal_slate_date": "",
    "inputs.rehearsal_slate_date || ''": "",
    "inputs.credit_cap || '40000'": "40000",
    "steps.identity.outputs.day": "2026-11-02",
    "steps.identity.outputs.slot": "morning",
    "steps.identity.outputs.trigger": "schedule",
    "steps.card.outputs.decision || 'degraded'": "blocked",
}


def rendered(block: str, values: dict[str, str] | None = None) -> str:
    context = {**GAMEDAY_CONTEXT, **(values or {})}

    def substitute(match: re.Match[str]) -> str:
        expression = match.group(1)
        assert expression in context, f"the block reads `${{{{ {expression} }}}}` and this test gave it no value"
        return context[expression]

    text = EXPRESSION.sub(substitute, block)
    assert "${{" not in text, text
    return text


def gameday_step(step_id: str) -> str:
    document = load(WORKFLOWS_DIR / GAMEDAY_WORKFLOW)
    for step in steps_of(jobs_of(document)["card"]):
        if step.get("id") == step_id:
            assert isinstance(step.get("run"), str), f"step {step_id!r} has no run block"
            return step["run"]
    raise AssertionError(f"{GAMEDAY_WORKFLOW} has no step with id {step_id!r} in the card job")


def runner_file(sandbox: Path, name: str) -> str:
    return (sandbox / name.lower()).read_text(encoding="utf-8")


#: What a card prints on its way to a verdict, shortened to the lines the step
#: reads. The real script prints `degraded=` and then `decision=` as its last
#: two lines; a refusal prints `decision=refused` and no `degraded=` line.
CARD_CLEAN = "Froze 412 wager(s) offered.\ndegraded=false\ndecision=no-selections\n"
CARD_DEGRADED = "::warning::the board was stale\ndegraded=true\ndecision=no-selections\n"
CARD_REFUSED = "::error::Refusing to start.\ndecision=refused\n"
CARD_TRACEBACK = "Traceback (most recent call last):\n  ValueError: the identity does not reconcile\n"


def run_card_step(
    root: Path, *, prints: str, status: int | str, tee_fails: bool = False
) -> tuple[subprocess.CompletedProcess[str], Path]:
    """The card block, executed against a card of known stdout and known exit
    status, with the real `tee`, `grep` and `tail` behind it.

    The stub harness cannot ask this question: its `tee` never reads its
    stdin, so the card's own `printf` dies of SIGPIPE and every card it models
    exits 141 whatever the stub was told to return. The exit code IS the
    contract here, so the card is faked and everything else is real.

    `status` is the number the card exits with; `"killed"` is the runner's OOM
    killer taking it (SIGKILL, 137), which no `return` can model.
    """
    block = rendered(gameday_step("card"))
    workspace = root / "card-workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir()
    # `exec sh -c 'kill -KILL $$'`, not `kill $BASHPID`: the pipeline element
    # has to die of the signal itself for the status to be a real 137, and
    # `BASHPID` does not exist in the bash 3.2 some of these machines carry.
    ending = "exec sh -c 'kill -KILL $$'" if status == "killed" else f"return {status}"
    preamble = ["python() {", "  printf '%s' " + _quote(prints), "  " + ending, "}"]
    if tee_fails:
        # A tee that writes everything it was given and then reports a
        # failure: the transcript survives and tee's status describes tee.
        preamble.append('tee() { command tee "$@"; return 1; }')
    script = workspace / "run_block.sh"
    script.write_text("\n".join(preamble) + "\n" + block, encoding="utf-8")
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(workspace),
        "LC_ALL": "C",
        "CBB_ODDS_API_KEY": "set",
    }
    for name in RUNNER_FILE_VARIABLES:
        target = workspace / name.lower()
        target.write_text("", encoding="utf-8")
        environment[name] = str(target)
    assert HARNESS_SHELL
    completed = subprocess.run(
        [HARNESS_SHELL, "-e", str(script)], cwd=workspace, env=environment,
        capture_output=True, text=True, timeout=60,
    )
    return completed, workspace


def test_the_card_step_models_every_command_and_refuses_without_its_credential(tmp_path: Path) -> None:
    """Two questions the stub harness can still answer about the card block:
    that every command in it is modelled — a block with an unmodelled command
    was never executed by anything — and that with no credential bound it
    exits before invoking a single command."""
    block = rendered(gameday_step("card"))
    assert ENABLES_PIPEFAIL.search(commands(block)[0]), (
        "the card step does not open with `set -o pipefail`; without it the pipeline's "
        "status is tee's and the card's own exit code is unreadable"
    )
    modelled = run_block_under_stubs(block, set(), tmp_path, environment={"CBB_ODDS_API_KEY": "set"})
    assert modelled.unmodelled == [], modelled

    without_credential = run_block_under_stubs(block, set(), tmp_path)
    assert without_credential.exit_code != 0 and without_credential.any_failures == [], (
        "the card step ran the card without its credential name bound"
    )


def test_a_refused_or_degraded_card_is_not_a_failed_card_step(tmp_path: Path) -> None:
    """The rejected fix's defect: `set -euo pipefail` alone turned the card's
    DELIBERATE non-zero exits into a fault. `run_gameday_card.py` returns 2 on
    a refusal and `return 1 if run.is_degraded else 0` on its last line — both
    are runs that reached a verdict, rendered a card and are meant to be
    published stamped with the word they printed. Failing the step on either
    hands the run to the `if: failure()` step, which overwrites that card with
    a fault card, and loses the `decision=` word on the way.

    So: exit 0, 1 and 2 with a decision word behind them all leave the step
    successful, and each publishes the word the card actually printed."""
    for status, prints, decision, health in (
        (0, CARD_CLEAN, "no-selections", "false"),
        (1, CARD_DEGRADED, "no-selections", "true"),
        (2, CARD_REFUSED, "refused", "unknown"),
    ):
        completed, workspace = run_card_step(tmp_path, prints=prints, status=status)
        output = runner_file(workspace, "GITHUB_OUTPUT")
        assert completed.returncode == 0, (
            f"a card that exited {status} after printing decision={decision} failed the step: "
            f"{completed.stdout}{completed.stderr}"
        )
        assert f"decision={decision}\n" in output, f"exit {status}: {output!r}"
        assert f"card_degraded={health}\n" in output, f"exit {status}: {output!r}"


def test_a_card_that_could_not_run_fails_the_card_step(tmp_path: Path) -> None:
    """The other half of the contract, and the half the old test pinned
    backwards. A card that never reached a verdict is a fault: a traceback
    (Python's own exit 1, with no `decision=` line behind it — the status
    alone cannot tell it from a degraded run, which also exits 1), a killed
    process, an exit code the script does not define. Each one must fail the
    step, and the decision word must survive whenever the card printed one:
    what it decided before it died is evidence, not noise."""
    crashed, workspace = run_card_step(tmp_path, prints=CARD_TRACEBACK, status=1)
    assert crashed.returncode != 0, "a card that printed no decision passed as a verdict"
    assert "decision=" not in runner_file(workspace, "GITHUB_OUTPUT"), (
        "a card that printed no decision word had one invented for it"
    )

    killed, workspace = run_card_step(tmp_path, prints=CARD_CLEAN, status="killed")
    assert killed.returncode != 0, "a killed card (SIGKILL, 137) read green"
    assert "decision=no-selections\n" in runner_file(workspace, "GITHUB_OUTPUT"), (
        "the card printed a decision and being killed erased it"
    )

    undefined, workspace = run_card_step(tmp_path, prints=CARD_CLEAN, status=3)
    assert undefined.returncode != 0, "an exit code the card script does not define read green"


def test_the_card_step_never_reports_tees_status(tmp_path: Path) -> None:
    """The original defect and its overcorrection, from the same block. Both
    directions: a failing `tee` does not fail a card that reached a verdict,
    and a succeeding `tee` does not green a card that did not. `PIPESTATUS`,
    not the pipeline's own status, is what this step reads."""
    survived, workspace = run_card_step(tmp_path, prints=CARD_CLEAN, status=0, tee_fails=True)
    assert survived.returncode == 0, (
        "tee failed over a card that returned a decision and the step reported tee's status: "
        f"{survived.stdout}{survived.stderr}"
    )
    assert "decision=no-selections\n" in runner_file(workspace, "GITHUB_OUTPUT")

    still_a_fault, workspace = run_card_step(tmp_path, prints=CARD_TRACEBACK, status=1, tee_fails=True)
    assert still_a_fault.returncode != 0, "a crashed card read green because tee was blamed instead"


def run_health(tmp_path: Path, *, card_degraded: str, card: str = "success") -> BlockRun:
    """The health block, executed with the card rendered and every other step
    successful, so the only variable is what the card said about itself."""
    outputs = tmp_path / "data/outputs"
    outputs.mkdir(parents=True, exist_ok=True)
    (outputs / "cbb_gameday_card.md").write_text("# CBB card\n", encoding="utf-8")
    block = rendered(
        gameday_step("health"),
        {
            "steps.feeds.outcome": "success",
            "steps.settle.outcome": "success",
            "steps.card.outcome": card,
            "steps.restore.outcome": "success",
            "steps.card.outputs.card_degraded": card_degraded,
        },
    )
    return run_block_under_stubs(block, set(), tmp_path)


def test_a_card_that_reported_itself_degraded_makes_the_run_degraded(tmp_path: Path) -> None:
    """A degraded card now leaves the card step SUCCESSFUL, which is right —
    it reached a verdict — so the health step can no longer learn about it
    from that step's outcome alone. It reads the card's own `degraded=` line
    instead. Without this the feed carried `degraded: "false"` over a card
    that said it was degraded, and the already-published guard let that card
    stand instead of letting the next slot replace it."""
    clean = run_health(tmp_path, card_degraded="false")
    assert clean.exit_code == 0 and clean.unmodelled == [], clean
    assert "degraded=false\n" in runner_file(tmp_path, "GITHUB_OUTPUT"), runner_file(tmp_path, "GITHUB_OUTPUT")

    for reported in ("true", "unknown", ""):
        degraded = run_health(tmp_path, card_degraded=reported)
        assert degraded.exit_code == 0 and degraded.unmodelled == [], degraded
        assert "degraded=true\n" in runner_file(tmp_path, "GITHUB_OUTPUT"), (
            f"the card reported its health as {reported!r} and the run was stamped clean"
        )


def test_a_failed_feed_fetch_fails_the_restore_step(tmp_path: Path) -> None:
    """The defect: `if ! git fetch ...; then echo 'No card-feed branch'; exit 0`
    read every failure as an absent branch. Executed with git failing, the
    block must exit non-zero, record `feed=unreachable`, and write the
    refusal into the step summary — and never claim the branch is absent."""
    block = rendered(gameday_step("restore"))

    failed = run_block_under_stubs(block, {"git"}, tmp_path)
    assert "git" in failed.any_failures, "git was never invoked, so nothing was tested"
    assert failed.unmodelled == [], failed
    assert failed.exit_code != 0, "the feed fetch failed and the restore step still exited 0"
    output = runner_file(tmp_path, "GITHUB_OUTPUT")
    assert "feed=unreachable" in output and "feed=absent" not in output and "feed=restored" not in output, output
    assert "Not published" in runner_file(tmp_path, "GITHUB_STEP_SUMMARY")

    everything = run_block_under_stubs(block, None, tmp_path)
    assert everything.exit_code != 0


def scratch_remote(root: Path) -> str:
    """A real, empty bare repository, addressed by the `file://` transport the
    shallow fetch needs (a plain path ignores `--depth`)."""
    remote = root / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", str(remote)], check=True)
    return remote.as_uri()


def push_card_feed(root: Path, ledger: str, snapshots: dict[str, str]) -> None:
    """A real orphan commit on refs/heads/card-feed in the scratch remote,
    built with the same plumbing the publish step uses."""
    remote = root / "remote.git"

    def blob(text: str) -> str:
        return subprocess.run(
            ["git", "-C", str(remote), "hash-object", "-w", "--stdin"],
            input=text, capture_output=True, text=True, check=True,
        ).stdout.strip()

    def tree(entries: str) -> str:
        return subprocess.run(
            ["git", "-C", str(remote), "mktree"], input=entries, capture_output=True, text=True, check=True
        ).stdout.strip()

    snapshot_tree = tree("".join(f"100644 blob {blob(body)}\t{name}\n" for name, body in snapshots.items()))
    root_tree = tree(f"100644 blob {blob(ledger)}\tforward_evidence.csv\n040000 tree {snapshot_tree}\tsnapshots\n")
    # `commit-tree` refuses without a committer identity, and a CI runner has no
    # global git config — the identity travels in the environment so the test does
    # not depend on whose machine it runs on, and does not write anyone's config.
    commit = subprocess.run(
        ["git", "-C", str(remote), "commit-tree", root_tree, "-m", "tip"],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, **GIT_IDENTITY},
    ).stdout.strip()
    subprocess.run(["git", "-C", str(remote), "update-ref", "refs/heads/card-feed", commit], check=True)


#: A committer for the throwaway remotes these tests build. Never a real
#: identity, never written to a config file: a test that needs `git config
#: --global` to have been run is a test that passes on a laptop and fails on a
#: runner, which is exactly what happened.
GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "cbb tests",
    "GIT_AUTHOR_EMAIL": "tests@example.invalid",
    "GIT_COMMITTER_NAME": "cbb tests",
    "GIT_COMMITTER_EMAIL": "tests@example.invalid",
}


def run_restore_for_real(root: Path, remote_url: str) -> tuple[subprocess.CompletedProcess[str], Path]:
    """The restore block, with its remote line and nothing else replaced,
    executed with real git inside a fresh checkout-shaped directory."""
    block = gameday_step("restore")
    assert block.count(RESTORE_REMOTE_LINE) == 1, "the restore step no longer names its remote on the one line this test replaces"
    block = rendered(block.replace(RESTORE_REMOTE_LINE, f'REMOTE="{remote_url}"'))
    workspace = root / "workspace"
    if workspace.exists():
        shutil.rmtree(workspace)
    workspace.mkdir()
    subprocess.run(["git", "init", "-q", str(workspace)], check=True)
    script = workspace / "run_block.sh"
    script.write_text(block, encoding="utf-8")
    environment = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "HOME": str(workspace), "LC_ALL": "C", "GH_TOKEN": "unused"}
    for name in RUNNER_FILE_VARIABLES:
        target = workspace / name.lower()
        target.write_text("", encoding="utf-8")
        environment[name] = str(target)
    assert HARNESS_SHELL
    completed = subprocess.run(
        [HARNESS_SHELL, "-e", str(script)], cwd=workspace, env=environment, capture_output=True, text=True, timeout=120
    )
    return completed, workspace


def test_the_restore_step_tells_an_absent_branch_from_a_failed_fetch(tmp_path: Path) -> None:
    """Against a real remote in all three states. Absent: the legitimate
    first run, exit 0 and `feed=absent`. Present: the ledger and every
    snapshot come back byte for byte and `feed=restored`. Unreachable: exit
    non-zero, `feed=unreachable`, the refusal in the summary, and nothing on
    disk that could be mistaken for a restored feed."""
    remote = scratch_remote(tmp_path)

    absent, workspace = run_restore_for_real(tmp_path, remote)
    assert absent.returncode == 0, absent.stderr
    assert "feed=absent" in runner_file(workspace, "GITHUB_OUTPUT")
    assert not (workspace / "data/processed/cbb_forward_evidence.csv").exists()
    assert runner_file(workspace, "GITHUB_STEP_SUMMARY") == ""

    ledger = "snapshot_date,game_id,edge\n2026-11-01,401,0.01\n2026-11-01,402,-0.02\n"
    snapshots = {"2026-11-01.csv": "game_id,price\n401,-110\n", "2026-11-02.csv": "game_id,price\n402,+105\n"}
    push_card_feed(tmp_path, ledger, snapshots)
    present, workspace = run_restore_for_real(tmp_path, remote)
    assert present.returncode == 0, present.stderr
    assert "feed=restored" in runner_file(workspace, "GITHUB_OUTPUT")
    assert (workspace / "data/processed/cbb_forward_evidence.csv").read_text(encoding="utf-8") == ledger
    for name, body in snapshots.items():
        assert (workspace / "data/archive/priced_snapshots" / name).read_text(encoding="utf-8") == body
    assert "Ledger restored: 2 rows." in present.stdout

    unreachable, workspace = run_restore_for_real(tmp_path, (tmp_path / "no-such-remote.git").as_uri())
    assert unreachable.returncode != 0, "an unreachable remote was read as an absent branch"
    output = runner_file(workspace, "GITHUB_OUTPUT")
    assert "feed=unreachable" in output and "feed=absent" not in output, output
    assert "Not published" in runner_file(workspace, "GITHUB_STEP_SUMMARY")
    assert not (workspace / "data/processed/cbb_forward_evidence.csv").exists()
    assert "No card-feed branch" not in unreachable.stdout + unreachable.stderr


def test_an_unreachable_remote_leaves_gits_own_message_in_the_log(tmp_path: Path) -> None:
    """`2>&1` into /dev/null made the `feed=unreachable` path undiagnosable:
    the run said it could not ask the remote and never said why, so a DNS
    failure, an expired token and a 500 read identically — on the one run
    that ever takes this path. git's own message must reach the log."""
    remote = (tmp_path / "no-such-remote.git").as_uri()
    unreachable, _ = run_restore_for_real(tmp_path, remote)
    assert unreachable.returncode != 0
    logged = unreachable.stdout + unreachable.stderr
    assert "no-such-remote.git" in logged, (
        f"the restore step refused without saying what git said: {logged!r}"
    )
    assert "does not appear to be a git repository" in logged or "Could not read from remote" in logged, logged


def test_the_restore_step_blanks_a_credential_out_of_the_message_it_replays(tmp_path: Path) -> None:
    """The message git writes is replayed, and the remote it names carries the
    token. git strips the userinfo out of the URL it prints; this proves the
    step does not depend on it doing so. Executed: the block's own redaction
    lines, over a message that does carry one."""
    redactions = [line for line in commands(gameday_step("restore")) if line.startswith("sed ")]
    assert len(redactions) == 2, (
        f"the restore step replays git's error on {len(redactions)} path(s), not the two that fail: {redactions}"
    )
    carrier = tmp_path / "git_error.txt"
    carrier.write_text(
        "fatal: unable to access 'https://x-access-token:notatoken@github.com/o/r/': 500\n", encoding="utf-8"
    )
    assert HARNESS_SHELL
    for line in redactions:
        replayed = subprocess.run(
            [HARNESS_SHELL, "-c", f'GIT_ERROR="$1"\n{line}\n', "sh", str(carrier)],
            capture_output=True, text=True, timeout=30,
        )
        assert replayed.returncode == 0, replayed.stderr
        printed = replayed.stdout + replayed.stderr
        assert "notatoken" not in printed, f"the replayed message carries the credential: {printed!r}"
        assert "x-access-token:***@github.com" in printed, printed
        assert "500" in printed, f"the redaction ate the diagnosis: {printed!r}"


def test_no_workflow_pipes_a_script_through_tee_without_pipefail() -> None:
    """A pipeline's status is its LAST command's, and `tee` succeeds whatever
    the script in front of it did. That was the card defect; the same shape
    stood in front of the purchase, where the swallowed exit code is a quota
    reading nobody read before spending against it."""
    piping: list[str] = []
    offenders: list[str] = []
    for path in WORKFLOW_FILES:
        for name, block in run_blocks(load(path)):
            lines = [without_quoted_spans(line) for line in commands(block)]
            if not any(SCRIPT_THROUGH_TEE.search(line) for line in lines):
                continue
            piping.append(f"{path.name}: {name!r}")
            if not ENABLES_PIPEFAIL.search(lines[0]):
                offenders.append(f"{path.name}: {name!r} does not open with `set -o pipefail`")
            for line in lines:
                if DISABLES_PIPEFAIL.search(line):
                    offenders.append(f"{path.name}: {name!r} turns pipefail back off: {line!r}")
    assert len(piping) >= 6, (
        f"only {len(piping)} run block(s) pipe a script through tee ({piping}); this rule "
        "was written over six of them — the card, both quota readings on either side of the "
        "purchase, the quota check, and both on either side of the probe — and a rule that "
        "matches nothing reports green over everything"
    )
    assert not offenders, offenders


PUBLISH_OUTCOMES = {
    "restore failed": ("failure", "skipped", "true"),
    "run died before restore": ("skipped", "skipped", "true"),
    "restore cancelled": ("cancelled", "skipped", "unknown"),
    "restore failed, health unreadable": ("failure", "skipped", "unknown"),
}


def run_publish(tmp_path: Path, restore: str, card: str, degraded: str, failing: set[str]) -> BlockRun:
    block = rendered(
        gameday_step("publish"),
        {
            "steps.restore.outcome": restore,
            "steps.card.outcome": card,
            "steps.health.outputs.degraded || 'unknown'": degraded,
        },
    )
    return run_block_under_stubs(block, failing, tmp_path)


def test_a_clean_run_with_a_restored_feed_publishes(tmp_path: Path) -> None:
    """The control: the publish block runs to its end under stubs, and git is
    reached — so a refusal below is the refusal and not an accident."""
    clean = run_publish(tmp_path, "success", "success", "false", set())
    assert clean.exit_code == 0 and clean.unmodelled == [], clean
    reached = run_publish(tmp_path, "success", "success", "false", {"git"})
    assert "git" in reached.any_failures, "git was never reached on a clean run, so the refusal tests below prove nothing"


def test_the_deliberate_fault_path_still_publishes(tmp_path: Path) -> None:
    """Restore succeeded, the card failed, health says degraded: the fault
    card is published, stamped degraded. This is the path the `if: failure()`
    step exists for and it must stay open."""
    fault = run_publish(tmp_path, "success", "failure", "true", set())
    assert fault.exit_code == 0, fault
    assert "Not published" not in runner_file(tmp_path, "GITHUB_STEP_SUMMARY")


@pytest.mark.parametrize("case", sorted(PUBLISH_OUTCOMES), ids=sorted(PUBLISH_OUTCOMES))
def test_a_run_that_did_not_restore_the_feed_never_reaches_publish(tmp_path: Path, case: str) -> None:
    """The defect's second half: a fetch failure upstream must not reach the
    push. With git failing, `any_failures` is empty only if no git command
    was invoked at all — the refusal came first."""
    restore, card, degraded = PUBLISH_OUTCOMES[case]
    refused = run_publish(tmp_path, restore, card, degraded, {"git"})
    assert refused.unmodelled == [], refused
    assert refused.exit_code != 0, f"{case}: the publish step ran to its end without a restored feed"
    assert refused.any_failures == [], f"{case}: git was invoked before the refusal: {refused.any_failures}"
    assert "Not published" in runner_file(tmp_path, "GITHUB_STEP_SUMMARY"), f"{case}: the summary does not say why"


def test_a_failed_card_never_publishes_as_clean(tmp_path: Path) -> None:
    """Health derives `degraded` from the card outcome; the publish step reads
    the same fact again. If the two ever disagree, nothing is pushed."""
    disagreement = run_publish(tmp_path, "success", "failure", "false", {"git"})
    assert disagreement.exit_code != 0 and disagreement.any_failures == [], disagreement


# --------------------------------------------------------------------------
# The self-regression suite: every rule watched failing.
# --------------------------------------------------------------------------

GOOD_WORKFLOW = """\
name: Tests
"on":
  push:
    branches: [main]
  pull_request:

permissions:
  contents: read

jobs:
  tests:
    name: Tests
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - name: Check out the repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 1
          persist-credentials: false
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Byte-compile every module
        run: |
          set -euo pipefail
          for d in src scripts; do
            [ -d "$d" ] || { echo "::error::$d is missing"; exit 1; }
          done
          python -m compileall -q -f src scripts
      - name: Run the suite
        env:
          PYTHONSAFEPATH: '1'
        run: |
          set -euo pipefail
          : > "$RUNNER_TEMP/suite_started_at"
          python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"
      - name: Gate on the results
        if: always()
        run: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml" --newer-than "$RUNNER_TEMP/suite_started_at"
      - name: Upload the test evidence
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: test-results
          path: ${{ runner.temp }}/junit.xml
          if-no-files-found: error
"""

TRIGGER_BLOCK = '"on":\n  push:\n    branches: [main]\n  pull_request:\n'
PERMISSIONS_BLOCK = "permissions:\n  contents: read\n"
JOB_HEADER = "  tests:\n    name: Tests\n    runs-on: ubuntu-latest\n"
TIMEOUT_LINE = "    timeout-minutes: 30\n"
PYTHON_VERSION_LINE = "python-version: '3.12'"
PERSIST_LINE = "          persist-credentials: false\n"
COMPILE_LINE = "python -m compileall -q -f src scripts"
COMPILE_GUARD = '            [ -d "$d" ] || { echo "::error::$d is missing"; exit 1; }\n'
SUITE_LINE = 'python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"'
SUITE_STEP_HEADER = "      - name: Run the suite\n"
GATE_COMMAND = (
    'python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml" '
    '--newer-than "$RUNNER_TEMP/suite_started_at"'
)
GATE_STEP = (
    "      - name: Gate on the results\n"
    "        if: always()\n"
    f"        run: {GATE_COMMAND}\n"
)
SUITE_MARKER_LINE = ': > "$RUNNER_TEMP/suite_started_at"'
SAFEPATH_BLOCK = "        env:\n          PYTHONSAFEPATH: '1'\n"
GATE_STEP_HEADER = "      - name: Gate on the results\n"
UPLOAD_POLICY = "if-no-files-found: error"

ALL_CHECKS = {**CORPUS_CHECKS, **GATE_CHECKS}


def mutate(anchor: str, replacement: str, text: str = GOOD_WORKFLOW) -> str:
    assert anchor in text, f"anchor no longer in the control workflow: {anchor!r}"
    return text.replace(anchor, replacement, 1)


def gate_block(*lines: str) -> str:
    body = "".join(f"          {line}\n" for line in lines)
    return mutate(f"        run: {GATE_COMMAND}\n", "        run: |\n" + body)


def workflow(tmp_path: Path, text: str, name: str = TESTS_WORKFLOW) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def assert_rejects(check: Callable[[Path], None], path: Path) -> None:
    with pytest.raises(AssertionError):
        check(path)


@pytest.mark.parametrize("rule", sorted(ALL_CHECKS), ids=sorted(ALL_CHECKS))
def test_the_control_workflow_passes_every_rule(tmp_path: Path, rule: str) -> None:
    """Without this, a rejection could be coming from a typo in the YAML."""
    ALL_CHECKS[rule](workflow(tmp_path, GOOD_WORKFLOW))


PROOFS = {
    "parses_and_declares_a_trigger": "test_a_workflow_with_no_trigger_is_rejected",
    "no_trigger_is_path_filtered": "test_a_paths_filter_is_rejected",
    "permissions_are_declared_and_writers_are_the_closed_set": "test_an_undeclared_writer_is_rejected",
    "git_pushes_target_the_declared_ref_and_never_force": "test_a_push_to_the_wrong_ref_or_a_force_push_is_rejected",
    "no_workflow_stages_a_working_tree_wholesale": "test_git_add_is_rejected_wherever_it_sits_on_the_line",
    "the_secrets_context_reaches_only_an_env_mapping": "test_a_secret_outside_an_env_mapping_is_rejected",
    "the_required_workflow_holds_no_secret_at_all": "test_a_secret_in_the_required_workflows_env_is_rejected",
    "the_credential_is_never_spelled_onto_a_command_line": "test_a_dereferenced_credential_is_rejected",
    "credit_spending_workflows_carry_no_cron": "test_a_cron_on_a_spending_workflow_is_rejected",
    "every_script_a_workflow_runs_exists": "test_a_missing_script_is_rejected",
    "python_version_is_pinned_to_an_exact_minor": "test_an_unpinned_python_version_is_rejected",
    "job_timeouts_are_within_githubs_ceiling": "test_a_timeout_above_githubs_ceiling_is_rejected",
    "no_step_or_job_continues_on_error": "test_continue_on_error_is_rejected",
    "no_gate_workflow_binds_a_credential": "test_an_env_bound_credential_is_rejected",
    "permissions_are_read_only": "test_write_permissions_on_a_gate_are_rejected",
    "checkout_never_persists_credentials": "test_a_credential_persisting_checkout_is_rejected",
    "every_piped_run_block_sets_pipefail": "test_a_pipeline_without_pipefail_is_rejected",
    "no_run_block_swallows_a_failure": "test_a_swallowed_failure_is_rejected",
    "the_suite_is_never_narrowed": "test_a_narrowing_pytest_flag_is_rejected",
    "every_upload_fails_when_there_is_nothing_to_upload": "test_a_warning_upload_policy_is_rejected",
    "the_suite_and_the_gate_are_both_present": "test_echo_in_place_of_pytest_is_rejected",
    "the_gate_reads_the_evidence_this_run_wrote": "test_a_planted_junit_file_is_rejected",
    "no_workflow_overrides_the_shell": "test_a_custom_shell_is_rejected",
    "no_condition_disables_the_chain": "test_a_condition_on_the_chain_is_rejected",
    "the_byte_compile_step_fails_on_a_missing_directory": "test_a_byte_compile_step_that_tolerates_a_missing_directory_is_rejected",
    "the_required_check_is_pinned": "test_a_renamed_or_hollowed_required_check_is_rejected",
    "the_suite_line_carries_only_whitelisted_arguments": "test_an_argument_that_is_not_on_the_whitelist_is_rejected",
    "the_gate_line_is_pinned_as_a_whole_command": "test_a_gate_line_that_only_contains_the_gate_is_rejected",
    "the_gate_step_really_runs_the_gate": "test_a_gate_step_that_never_invokes_the_gate_is_rejected",
    "the_suite_step_disables_the_path_shadows": "test_a_suite_step_without_pythonsafepath_is_rejected",
}


def test_every_rule_has_a_case_that_proves_it_fires() -> None:
    unproven = sorted(set(ALL_CHECKS) - set(PROOFS))
    assert not unproven, f"rules with no synthetic case proving they fire: {unproven}"
    missing = sorted(n for n in PROOFS.values() if n not in globals())
    assert not missing, f"named proofs that do not exist: {missing}"


def test_a_workflow_with_no_trigger_is_rejected(tmp_path: Path) -> None:
    assert_rejects(check_parses_and_declares_a_trigger, workflow(tmp_path, mutate(TRIGGER_BLOCK, "")))
    for text in ("- not: a workflow\n", "just a string\n", ""):
        assert_rejects(check_parses_and_declares_a_trigger, workflow(tmp_path, text))


def test_a_paths_filter_is_rejected(tmp_path: Path) -> None:
    for spelling in (
        '"on":\n  push:\n    paths:\n      - src/**\n  pull_request:\n',
        "on:\n  push:\n  pull_request:\n    paths-ignore:\n      - docs/**\n",
    ):
        path = workflow(tmp_path, mutate(TRIGGER_BLOCK, spelling))
        assert_rejects(check_no_trigger_is_path_filtered, path)


def test_an_undeclared_writer_is_rejected(tmp_path: Path) -> None:
    assert_rejects(
        check_permissions_are_declared_and_writers_are_the_closed_set,
        workflow(tmp_path, mutate("  contents: read", "  contents: write")),
    )
    # ...at job level too, which a top-level-only read never saw.
    assert_rejects(
        check_permissions_are_declared_and_writers_are_the_closed_set,
        workflow(tmp_path, mutate(JOB_HEADER, JOB_HEADER + "    permissions:\n      contents: write\n")),
    )
    assert_rejects(
        check_permissions_are_declared_and_writers_are_the_closed_set,
        workflow(tmp_path, mutate(PERMISSIONS_BLOCK, "")),
    )
    # A declared writer that holds no write is a writer that cannot do its job.
    assert_rejects(
        check_permissions_are_declared_and_writers_are_the_closed_set,
        workflow(tmp_path, GOOD_WORKFLOW, "line-movement.yml"),
    )


@pytest.mark.parametrize(
    "push",
    [
        "git push origin HEAD:refs/heads/main",
        "cd out && git push origin HEAD:refs/heads/main",
        "git  push origin HEAD:refs/heads/card-feed --force",
        "git push -f origin HEAD:refs/heads/card-feed",
        "git push origin +HEAD:refs/heads/card-feed",
        "git push --force-with-lease origin HEAD:refs/heads/card-feed",
        "git push origin",
    ],
)
def test_a_push_to_the_wrong_ref_or_a_force_push_is_rejected(tmp_path: Path, push: str) -> None:
    text = mutate("  contents: read", "  contents: write")
    text = mutate(f"        run: {GATE_COMMAND}\n", f"        run: |\n          {push}\n", text)
    assert_rejects(check_git_pushes_target_the_declared_ref_and_never_force, workflow(tmp_path, text, "cbb-gameday-refresh.yml"))
    # The same push from a workflow that is not a writer at all.
    assert_rejects(check_git_pushes_target_the_declared_ref_and_never_force, workflow(tmp_path, text, "provider-quota.yml"))


def test_the_declared_push_is_accepted(tmp_path: Path) -> None:
    text = mutate("  contents: read", "  contents: write")
    text = mutate(f"        run: {GATE_COMMAND}\n", "        run: |\n          git push origin HEAD:refs/heads/card-feed\n", text)
    check_git_pushes_target_the_declared_ref_and_never_force(workflow(tmp_path, text, "cbb-gameday-refresh.yml"))


@pytest.mark.parametrize("line", ["git add -A", "git add .", "cd data && git add outputs/", "true && git add x.md"])
def test_git_add_is_rejected_wherever_it_sits_on_the_line(tmp_path: Path, line: str) -> None:
    assert_rejects(
        check_no_workflow_stages_a_working_tree_wholesale,
        workflow(tmp_path, mutate(f"        run: {GATE_COMMAND}\n", f"        run: |\n          {line}\n")),
    )
    check_no_workflow_stages_a_working_tree_wholesale(
        workflow(tmp_path, mutate(f"        run: {GATE_COMMAND}\n", "        run: git add --dry-run x\n"), "dry.yml")
    )


@pytest.mark.parametrize(
    "accessor",
    [
        "${{ secrets.CBB_ODDS_API_KEY }}",
        "${{ secrets['CBB_ODDS_API_KEY'] }}",
        "${{ toJSON(secrets) }}",
        "${{ SECRETS.X }}",
        "${{ secrets }}",
    ],
)
def test_a_secret_outside_an_env_mapping_is_rejected(tmp_path: Path, accessor: str) -> None:
    # On a command line...
    assert_rejects(
        check_the_secrets_context_reaches_only_an_env_mapping,
        workflow(tmp_path, mutate(GATE_COMMAND, f"python x.py --key {accessor}")),
    )
    # ...as a `with:` input...
    assert_rejects(
        check_the_secrets_context_reaches_only_an_env_mapping,
        workflow(tmp_path, mutate("          fetch-depth: 1\n", f"          fetch-depth: 1\n          token: {accessor}\n")),
    )
    # ...and inside an env mapping it is accepted, which is the accepting
    # direction that keeps the operational workflows legal.
    check_the_secrets_context_reaches_only_an_env_mapping(
        workflow(tmp_path, mutate(GATE_STEP_HEADER, GATE_STEP_HEADER + f"        env:\n          CBB_ODDS_API_KEY: {accessor}\n"), "ok.yml")
    )


def test_secrets_inherit_is_rejected(tmp_path: Path) -> None:
    assert_rejects(
        check_the_secrets_context_reaches_only_an_env_mapping,
        workflow(tmp_path, mutate("jobs:\n", "jobs:\n  called:\n    uses: ./.github/workflows/other.yml\n    secrets: inherit\n")),
    )


@pytest.mark.parametrize(
    "line",
    ['python x.py "$CBB_ODDS_API_KEY"', "curl -H \"x: ${CBBD_API_KEY}\" u", "echo $CBB_ODDS_API_KEY"],
)
def test_a_dereferenced_credential_is_rejected(tmp_path: Path, line: str) -> None:
    assert_rejects(
        check_the_credential_is_never_spelled_onto_a_command_line,
        workflow(tmp_path, mutate(f"        run: {GATE_COMMAND}\n", f"        run: |\n          {line}\n")),
    )
    check_the_credential_is_never_spelled_onto_a_command_line(
        workflow(tmp_path, mutate(f"        run: {GATE_COMMAND}\n", '        run: |\n          if [ -z "${CBB_ODDS_API_KEY:-}" ]; then echo "CBB_ODDS_API_KEY is not set"; exit 1; fi\n'), "ok.yml")
    )


def test_a_cron_on_a_spending_workflow_is_rejected(tmp_path: Path) -> None:
    text = mutate(TRIGGER_BLOCK, '"on":\n  workflow_dispatch:\n  schedule:\n    - cron: "0 9 * * *"\n')
    for name in NO_CRON_WORKFLOWS:
        assert_rejects(check_credit_spending_workflows_carry_no_cron, workflow(tmp_path, text, name))
    check_credit_spending_workflows_carry_no_cron(workflow(tmp_path, text, "line-movement.yml"))


def test_a_missing_script_is_rejected(tmp_path: Path) -> None:
    assert_rejects(
        check_every_script_a_workflow_runs_exists,
        workflow(tmp_path, mutate(GATE_COMMAND, "python scripts/this_script_does_not_exist.py")),
    )


@pytest.mark.parametrize("version", ["3.10", "'3.x'", "'latest'", "'3'", "'3.12.1'", "3"])
def test_an_unpinned_python_version_is_rejected(tmp_path: Path, version: str) -> None:
    assert_rejects(check_python_version_is_pinned_to_an_exact_minor, workflow(tmp_path, mutate(PYTHON_VERSION_LINE, f"python-version: {version}")))


@pytest.mark.parametrize("declared", ["1440", "361", "0", "-30", "'360'", "abc", "true"])
def test_a_timeout_above_githubs_ceiling_is_rejected(tmp_path: Path, declared: str) -> None:
    assert_rejects(
        check_job_timeouts_are_within_githubs_ceiling,
        workflow(tmp_path, mutate(TIMEOUT_LINE, f"    timeout-minutes: {declared}\n")),
    )


@pytest.mark.parametrize("declared", ["360", "30", "1"])
def test_a_timeout_within_githubs_ceiling_is_accepted(tmp_path: Path, declared: str) -> None:
    check_job_timeouts_are_within_githubs_ceiling(
        workflow(tmp_path, mutate(TIMEOUT_LINE, f"    timeout-minutes: {declared}\n"), "ok.yml")
    )


def test_continue_on_error_is_rejected(tmp_path: Path) -> None:
    assert_rejects(check_no_step_or_job_continues_on_error, workflow(tmp_path, mutate(GATE_STEP_HEADER, GATE_STEP_HEADER + "        continue-on-error: true\n")))
    assert_rejects(check_no_step_or_job_continues_on_error, workflow(tmp_path, mutate(JOB_HEADER, JOB_HEADER + "    continue-on-error: true\n")))
    assert_rejects(check_the_required_check_is_pinned, workflow(tmp_path, mutate(SUITE_STEP_HEADER, SUITE_STEP_HEADER + "        continue-on-error: true\n")))


@pytest.mark.parametrize("credential", sorted(CREDENTIAL_NAMES))
def test_an_env_bound_credential_is_rejected(tmp_path: Path, credential: str) -> None:
    assert_rejects(check_no_gate_workflow_binds_a_credential, workflow(tmp_path, mutate(GATE_STEP_HEADER, GATE_STEP_HEADER + f"        env:\n          {credential}: ''\n")))


def test_write_permissions_on_a_gate_are_rejected(tmp_path: Path) -> None:
    assert_rejects(check_permissions_are_read_only, workflow(tmp_path, mutate("  contents: read", "  contents: write")))


def test_a_credential_persisting_checkout_is_rejected(tmp_path: Path) -> None:
    assert_rejects(check_checkout_never_persists_credentials, workflow(tmp_path, mutate(PERSIST_LINE, "")))
    assert_rejects(check_checkout_never_persists_credentials, workflow(tmp_path, mutate(PERSIST_LINE, "          persist-credentials: true\n")))


def test_a_pipeline_without_pipefail_is_rejected(tmp_path: Path) -> None:
    assert_rejects(check_every_piped_run_block_sets_pipefail, workflow(tmp_path, gate_block(f'{GATE_COMMAND} | tee "$RUNNER_TEMP/gate.txt"')))
    assert_rejects(check_every_piped_run_block_sets_pipefail, workflow(tmp_path, gate_block("set -euo pipefail", "set +o pipefail", f"{GATE_COMMAND} | tee x")))
    assert_rejects(check_every_piped_run_block_sets_pipefail, workflow(tmp_path, gate_block("echo 'set -o pipefail'", f"{GATE_COMMAND} | tee x")))
    check_every_piped_run_block_sets_pipefail(workflow(tmp_path, gate_block("set -euo pipefail", f"{GATE_COMMAND} | tee x"), "ok.yml"))


SWALLOWS = {
    "or-true": [f"{GATE_COMMAND} || true"],
    "or-colon": [f"{GATE_COMMAND} || :"],
    "or-echo": [f"{GATE_COMMAND} || echo 'no junit'"],
    "or-exit-0": [f"{GATE_COMMAND} || exit 0"],
    "or-brace-exit-0": [f"{GATE_COMMAND} || {{ echo 'nothing to gate'; exit 0; }}"],
    "or-bin-true": [f"{GATE_COMMAND} || /bin/true"],
    "exit-belongs-to-another-or-list": [f"test -f x || {{ echo 'no file'; exit 1; }}; {GATE_COMMAND} || true"],
    "exit-inside-a-quoted-message": [f'{GATE_COMMAND} || echo "gate failed; will exit 1 later"'],
    "if-not-then": [f"if ! {GATE_COMMAND}; then echo '::warning::no junit'; fi"],
    "if-then-else": [f"if {GATE_COMMAND}; then echo ok; else echo 'no junit'; fi"],
    "while-not": [f"while ! {GATE_COMMAND}; do break; done"],
    "bang-prefix": [f"! {GATE_COMMAND}"],
    "set-plus-e": ["set +e", GATE_COMMAND],
    "set-plus-o-pipefail": ["set -euo pipefail", "set +o pipefail", GATE_COMMAND],
    "trap-err-exit-0": ["trap 'exit 0' ERR", GATE_COMMAND],
    "shell-function": [f"gate() {{ {GATE_COMMAND}; }}", "gate || true"],
    "status-captured": [f"{GATE_COMMAND} && rc=0 || rc=$?", 'echo "the gate said $rc"'],
    "process-substitution": ["set -euo pipefail", f"cat < <({GATE_COMMAND})"],
    "background-then-wait": [f"{GATE_COMMAND} &", "wait"],
    "detached-setsid": [f"setsid {GATE_COMMAND}"],
}


@pytest.mark.parametrize("case", sorted(SWALLOWS), ids=sorted(SWALLOWS))
def test_a_swallowed_failure_is_rejected(tmp_path: Path, case: str) -> None:
    assert_rejects(check_no_run_block_swallows_a_failure, workflow(tmp_path, gate_block(*SWALLOWS[case])))


def test_the_executed_rule_catches_what_no_or_list_pattern_can_see(tmp_path: Path) -> None:
    """None of these contains `||`, and every one exits 0 under `bash -e`
    where the house idiom exits 1. The textual nets are shown SILENT on each,
    which is what makes them evidence about the executed rule."""
    for lines in (
        [f"if ! {GATE_COMMAND}; then echo '::warning::no junit'; fi"],
        [f"if {GATE_COMMAND}; then echo ok; else echo 'no junit'; fi"],
        ["trap 'exit 0' ERR", GATE_COMMAND],
        ["set +e", GATE_COMMAND],
    ):
        block = "\n".join(lines) + "\n"
        for line in commands(block):
            assert not OR_LIST.search(line)
            assert not unguarded_or_branches(line)
        assert swallow_findings(block), f"executing {block!r} under stubs did not reveal the swallow"


def test_the_legitimate_failure_path_is_accepted(tmp_path: Path) -> None:
    legitimate = f"{GATE_COMMAND} || {{ echo '::error::the gate failed'; exit 1; }}"
    assert unguarded_or_branches(legitimate) == []
    assert swallow_findings(f"set -euo pipefail\n{legitimate}\n") == []
    check_no_run_block_swallows_a_failure(workflow(tmp_path, gate_block("set -euo pipefail", legitimate)))
    check_no_run_block_swallows_a_failure(
        workflow(tmp_path, gate_block("set -euo pipefail", 'if [ -n "${A:-}" ] || [ -n "${B:-}" ]; then', "  echo '::error::x'", "  exit 1", "fi", legitimate), "cond.yml")
    )


def test_nothing_real_runs_under_the_stub_harness(tmp_path: Path) -> None:
    block = "python -c \"open('pwned', 'w').write('x')\"\ntouch also-pwned\n/bin/sh -c 'touch third'\n"
    result = run_block_under_stubs(block, None, tmp_path)
    assert result.unmodelled == [], f"a command reached the shell without a stub: {result.unmodelled} ({result.stderr!r})"
    for name in ("pwned", "also-pwned", "third"):
        assert not (tmp_path / name).exists(), f"{name} was really created"
    escaped = run_block_under_stubs("PATH=/usr/bin:/bin\ntouch escaped\n", None, tmp_path)
    assert escaped.exit_code != 0 and not (tmp_path / "escaped").exists()


def test_the_stub_harness_reports_a_command_it_could_not_model(tmp_path: Path) -> None:
    result = run_block_under_stubs('GATE="python scripts/check_test_results.py"\neval "$GATE" || true\n', None, tmp_path)
    assert result.unmodelled, f"an unstubbed command ran and the harness did not notice: {result!r}"


def test_the_stub_harness_distinguishes_a_top_level_failure(tmp_path: Path) -> None:
    top_level = run_block_under_stubs("git status\n", None, tmp_path)
    assert top_level.top_level_failures == ["git"] and top_level.exit_code != 0
    substituted = run_block_under_stubs('echo "$(git status)"\n', None, tmp_path)
    assert substituted.top_level_failures == [] and substituted.exit_code == 0


def test_the_stub_harness_honours_the_requested_failure_set(tmp_path: Path) -> None:
    block = "alpha\nbeta || true\n"
    assert run_block_under_stubs(block, None, tmp_path).exit_code != 0
    only_beta = run_block_under_stubs(block, {"beta"}, tmp_path)
    assert only_beta.exit_code == 0 and only_beta.top_level_failures == ["beta"]
    assert run_block_under_stubs(block, set(), tmp_path).exit_code == 0
    assert swallow_findings(block)


def test_commands_joins_the_shapes_bash_joins() -> None:
    assert commands("a \\\nb") == ["a b"]
    assert commands("a ||\nb") == ["a || b"]
    assert commands("a &&\nb") == ["a && b"]
    assert commands("a |\nb") == ["a | b"]
    assert commands("# a comment\nreal") == ["real"]
    assert simple_commands("cd x && git push origin HEAD:refs/heads/y") == [["cd", "x"], ["git", "push", "origin", "HEAD:refs/heads/y"]]


NARROWING_FLAGS = [
    "-x", "-xq", "-k", "-m", "-qk", "--exitfirst", "--maxfail=1", "--ignore=tests/test_workflows.py",
    "--ignore-glob=tests/test_*.py", "--deselect=tests/test_workflows.py::test_x", "--collect-only", "--co",
    "--last-failed", "--lf", "--stepwise", "--sw", "--stepwise-skip", "--sw-skip", "--stepwise-reset", "--sw-reset",
    "--override-ini=testpaths=tests/test_x.py", "-o", "-qo", "--config-file=ci.ini", "-cci.ini", "-qcci.ini",
    "--confcutdir=tests", "--runxfail",
]


@pytest.mark.parametrize("flag", NARROWING_FLAGS)
def test_a_narrowing_pytest_flag_is_rejected(tmp_path: Path, flag: str) -> None:
    assert_rejects(check_the_suite_is_never_narrowed, workflow(tmp_path, mutate(SUITE_LINE, f'python -m pytest -q -rs {flag} --junit-xml="$RUNNER_TEMP/junit.xml"')))


def test_every_banned_flag_is_in_the_set_that_is_proved_to_fire() -> None:
    proved = {a.split("=", 1)[0] for a in NARROWING_FLAGS}
    unproved = sorted(f for f in NARROWING_PYTEST_LONG_FLAGS if f not in proved)
    assert not unproved, f"flags banned with no case proving the ban fires: {unproved}"


@pytest.mark.parametrize("flag", ["-q", "-rs", "-vv", "--tb=short", "--durations=10", "--failed-first"])
def test_a_non_narrowing_pytest_flag_is_accepted(tmp_path: Path, flag: str) -> None:
    check_the_suite_is_never_narrowed(workflow(tmp_path, mutate(SUITE_LINE, f'python -m pytest -q -rs {flag} --junit-xml="$RUNNER_TEMP/junit.xml"')))


@pytest.mark.parametrize("positional", ["tests/test_workflows.py", "tests", "tests/test_x.py::test_one", "tests/test_no_secrets_committed.py tests/test_contract_strings.py", "./tests/"])
def test_a_positional_selection_is_rejected(tmp_path: Path, positional: str) -> None:
    assert_rejects(check_the_suite_is_never_narrowed, workflow(tmp_path, mutate(SUITE_LINE, f'python -m pytest -q -rs {positional} --junit-xml="$RUNNER_TEMP/junit.xml"')))


def test_a_narrowing_flag_behind_a_backslash_continuation_is_rejected(tmp_path: Path) -> None:
    continued = 'python -m pytest -q -rs \\\n            -k "not slow" \\\n            --junit-xml="$RUNNER_TEMP/junit.xml"'
    path = workflow(tmp_path, mutate(SUITE_LINE, continued))
    lines = [line for _, line in pytest_lines(load(path))]
    assert lines and "-k" in pytest_arguments(lines[0])
    assert_rejects(check_the_suite_is_never_narrowed, path)


def test_pytest_addopts_in_an_env_mapping_is_rejected(tmp_path: Path) -> None:
    for placement, text in (
        ("step", mutate(SAFEPATH_BLOCK, SAFEPATH_BLOCK + "          PYTEST_ADDOPTS: '-x'\n")),
        ("job", mutate(JOB_HEADER, JOB_HEADER + "    env:\n      PYTEST_ADDOPTS: '-k gate'\n")),
        ("workflow", mutate(PERMISSIONS_BLOCK, PERMISSIONS_BLOCK + "\nenv:\n  PYTEST_ADDOPTS: '--collect-only'\n")),
    ):
        assert_rejects(check_the_suite_is_never_narrowed, workflow(tmp_path, text, f"addopts-{placement}.yml"))


@pytest.mark.parametrize("line", ['echo "PYTEST_ADDOPTS=-x" >> "$GITHUB_ENV"', "export PYTEST_ADDOPTS=--collect-only", "PYTEST_ADDOPTS='-k gate' python -m pytest -q"], ids=["github-env", "export", "prefix"])
def test_pytest_addopts_set_from_the_shell_is_rejected(tmp_path: Path, line: str) -> None:
    assert_rejects(check_the_suite_is_never_narrowed, workflow(tmp_path, mutate(f"        run: {GATE_COMMAND}\n", f"        run: |\n          {line}\n")))


def test_a_warning_upload_policy_is_rejected(tmp_path: Path) -> None:
    for policy in ("warn", "ignore"):
        assert_rejects(check_every_upload_fails_when_there_is_nothing_to_upload, workflow(tmp_path, mutate(UPLOAD_POLICY, f"if-no-files-found: {policy}")))
    assert_rejects(check_every_upload_fails_when_there_is_nothing_to_upload, workflow(tmp_path, mutate("          " + UPLOAD_POLICY + "\n", "")))


def test_echo_in_place_of_pytest_is_rejected(tmp_path: Path) -> None:
    """The suite replaced by an echo: the gate is still there, so the pairing
    rule fires; and the required-check rule fires because the job runs no
    pytest at all."""
    hollow = workflow(tmp_path, mutate(SUITE_LINE, "echo 'the suite runs somewhere else now'"))
    assert_rejects(check_the_suite_and_the_gate_are_both_present, hollow)
    assert_rejects(check_the_required_check_is_pinned, hollow)
    # ...and the gate deleted outright, which every loop-shaped rule passes.
    no_gate = workflow(tmp_path, mutate(GATE_STEP, ""))
    assert_rejects(check_the_suite_and_the_gate_are_both_present, no_gate)
    assert_rejects(check_the_required_check_is_pinned, no_gate)


def test_a_job_delegated_to_a_reusable_workflow_is_rejected(tmp_path: Path) -> None:
    delegated = 'name: Tests\n"on": [push, pull_request]\npermissions:\n  contents: read\njobs:\n  tests:\n    name: Tests\n    uses: ./.github/workflows/reusable.yml\n'
    path = workflow(tmp_path, delegated)
    assert_rejects(check_the_suite_and_the_gate_are_both_present, path)
    assert_rejects(check_the_required_check_is_pinned, path)


@pytest.mark.parametrize(
    "planted",
    [
        'cp fixtures/green.xml "$RUNNER_TEMP/junit.xml"',
        'tee "$RUNNER_TEMP/junit.xml" < fixtures/green.xml',
        'cat fixtures/green.xml > "$RUNNER_TEMP/junit.xml"',
        'cp fixtures/green.xml "${RUNNER_TEMP}/junit.xml"',
    ],
)
def test_a_planted_junit_file_is_rejected(tmp_path: Path, planted: str) -> None:
    assert_rejects(
        check_the_gate_reads_the_evidence_this_run_wrote,
        workflow(tmp_path, mutate(GATE_STEP, f"      - name: Refresh the evidence\n        run: {planted}\n" + GATE_STEP)),
    )


@pytest.mark.parametrize(
    "gate",
    ["python scripts/check_test_results.py tests/fixtures/green.xml", 'python scripts/check_test_results.py "$RUNNER_TEMP/other.xml"', "python scripts/check_test_results.py", 'python vendor/check_test_results.py "$RUNNER_TEMP/junit.xml"'],
    ids=["tracked-fixture", "another-path", "no-argument", "vendored-copy"],
)
def test_a_gate_pointed_away_from_this_run_is_rejected(tmp_path: Path, gate: str) -> None:
    assert_rejects(check_the_gate_reads_the_evidence_this_run_wrote, workflow(tmp_path, mutate(GATE_COMMAND, gate)))


@pytest.mark.parametrize("suite", ["python -m pytest -q -rs", 'python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/other.xml"'], ids=["no-junit-flag", "different-path"])
def test_a_suite_that_does_not_write_the_gated_file_is_rejected(tmp_path: Path, suite: str) -> None:
    assert_rejects(check_the_gate_reads_the_evidence_this_run_wrote, workflow(tmp_path, mutate(SUITE_LINE, suite)))


def test_the_evidence_rule_accepts_the_other_spelling_of_the_same_path(tmp_path: Path) -> None:
    braced = mutate(SUITE_LINE, 'python -m pytest -q -rs --junit-xml="${RUNNER_TEMP}/junit.xml"').replace(GATE_COMMAND, GATE_COMMAND.replace("$RUNNER_TEMP", "${RUNNER_TEMP}"))
    check_the_gate_reads_the_evidence_this_run_wrote(workflow(tmp_path, braced))


SHELL_PLACEMENTS: dict[str, Callable[[str], str]] = {
    "step": lambda v: mutate(GATE_STEP_HEADER, GATE_STEP_HEADER + f"        shell: {v}\n"),
    "job-defaults": lambda v: mutate(JOB_HEADER, JOB_HEADER + f"    defaults:\n      run:\n        shell: {v}\n"),
    "workflow-defaults": lambda v: mutate(PERMISSIONS_BLOCK, PERMISSIONS_BLOCK + f"\ndefaults:\n  run:\n    shell: {v}\n"),
}


@pytest.mark.parametrize("placement", sorted(SHELL_PLACEMENTS))
@pytest.mark.parametrize("value", ["bash {0}", "/bin/bash {0}", "bash -c {0}", "pwsh", "python", "sh {0}", "Bash"])
def test_a_custom_shell_is_rejected(tmp_path: Path, placement: str, value: str) -> None:
    path = workflow(tmp_path, SHELL_PLACEMENTS[placement](value), "shell.yml")
    assert_rejects(check_no_workflow_overrides_the_shell, path)
    if placement != "step":
        assert_rejects(check_the_required_check_is_pinned, workflow(tmp_path, SHELL_PLACEMENTS[placement](value)))


@pytest.mark.parametrize("placement", sorted(SHELL_PLACEMENTS))
@pytest.mark.parametrize("value", ["bash", "sh"])
def test_the_bare_shell_keywords_are_accepted(tmp_path: Path, placement: str, value: str) -> None:
    check_no_workflow_overrides_the_shell(workflow(tmp_path, SHELL_PLACEMENTS[placement](value), "shell-ok.yml"))


@pytest.mark.parametrize("condition", ["false", "${{ false }}", "github.event_name == 'schedule'", "${{ !cancelled() && false }}", "success() && false"])
def test_a_condition_on_the_chain_is_rejected(tmp_path: Path, condition: str) -> None:
    gated = mutate("        if: always()\n        run: python scripts/check_test_results.py", f"        if: {condition}\n        run: python scripts/check_test_results.py")
    assert_rejects(check_no_condition_disables_the_chain, workflow(tmp_path, gated))
    assert_rejects(check_the_required_check_is_pinned, workflow(tmp_path, gated))
    suite = mutate(SUITE_STEP_HEADER, SUITE_STEP_HEADER + f"        if: {condition}\n")
    assert_rejects(check_no_condition_disables_the_chain, workflow(tmp_path, suite))
    job = mutate(JOB_HEADER, JOB_HEADER + f"    if: {condition}\n")
    assert_rejects(check_no_condition_disables_the_chain, workflow(tmp_path, job))
    assert_rejects(check_the_required_check_is_pinned, workflow(tmp_path, job))


def test_always_is_the_one_condition_the_chain_may_carry_and_the_suite_carries_none(tmp_path: Path) -> None:
    check_no_condition_disables_the_chain(workflow(tmp_path, GOOD_WORKFLOW))
    # `always()` on the SUITE step is refused by the pin: the suite runs
    # unconditionally, and an always() there would be an `if:` to edit later.
    assert_rejects(check_the_required_check_is_pinned, workflow(tmp_path, mutate(SUITE_STEP_HEADER, SUITE_STEP_HEADER + "        if: always()\n")))


@pytest.mark.parametrize(
    "compile_block",
    [
        "python -m compileall -q -f src scripts",
        "set -euo pipefail\npython -m compileall -q -f src scripts",
        'set -euo pipefail\nfor d in src scripts; do\n  [ -d "$d" ] || { echo "::error::$d is missing"; exit 1; }\ndone\npython -m compileall -q src scripts',
        'set -euo pipefail\nfor d in src scripts; do\n  [ -d "$d" ] || echo "::warning::$d is missing"\ndone\npython -m compileall -q -f src scripts',
    ],
    ids=["no-guard", "no-guard-with-set-e", "no-force", "guard-that-warns"],
)
def test_a_byte_compile_step_that_tolerates_a_missing_directory_is_rejected(tmp_path: Path, compile_block: str) -> None:
    """Measured: `python -m compileall -q src` exits 0 when src/ does not
    exist. A guard that only warns, or no guard, passes a repository whose
    source tree was moved."""
    body = "".join(f"          {line}\n" for line in compile_block.splitlines())
    text = mutate(
        "        run: |\n          set -euo pipefail\n          for d in src scripts; do\n" + COMPILE_GUARD + "          done\n          " + COMPILE_LINE + "\n",
        "        run: |\n" + body,
    )
    assert_rejects(check_the_byte_compile_step_fails_on_a_missing_directory, workflow(tmp_path, text))


def test_compileall_really_exits_zero_on_a_missing_path(tmp_path: Path) -> None:
    """The measurement the rule rests on, kept as a test."""
    import sys

    result = subprocess.run([sys.executable, "-m", "compileall", "-q", str(tmp_path / "never")], capture_output=True)
    assert result.returncode == 0, "compileall now fails on a missing path; the executed rule is redundant and this docstring is stale"


def test_a_workflow_without_a_byte_compile_step_is_rejected(tmp_path: Path) -> None:
    text = mutate("      - name: Byte-compile every module\n        run: |\n          set -euo pipefail\n          for d in src scripts; do\n" + COMPILE_GUARD + "          done\n          " + COMPILE_LINE + "\n", "")
    assert_rejects(check_the_byte_compile_step_fails_on_a_missing_directory, workflow(tmp_path, text))


@pytest.mark.parametrize(
    "mutation",
    [
        ("    name: Tests\n", "    name: Test Suite\n"),
        ("    name: Tests\n", ""),
        ("    runs-on: ubuntu-latest\n", "    runs-on: windows-latest\n"),
        ("    runs-on: ubuntu-latest\n", "    runs-on: ubuntu-latest\n    strategy:\n      matrix:\n        python: ['3.12']\n"),
        (SUITE_STEP_HEADER, SUITE_STEP_HEADER + "        working-directory: tests/unit\n"),
        (TRIGGER_BLOCK, '"on":\n  push:\n    branches: [main]\n'),
        (TRIGGER_BLOCK, '"on":\n  push:\n    branches: [main]\n  pull_request:\n    branches: [main]\n'),
        (TRIGGER_BLOCK, '"on":\n  push:\n    branches: [main]\n  pull_request:\n    paths: [src/**]\n'),
        (TRIGGER_BLOCK, '"on":\n  pull_request:\n'),
        ("name: Tests\n", "name: CI\n"),
    ],
    ids=["renamed-job", "unnamed-job", "windows", "matrix", "working-directory", "no-pull-request", "pr-branches", "pr-paths", "no-push", "renamed-workflow"],
)
def test_a_renamed_or_hollowed_required_check_is_rejected(tmp_path: Path, mutation: tuple[str, str]) -> None:
    anchor, replacement = mutation
    assert_rejects(check_the_required_check_is_pinned, workflow(tmp_path, mutate(anchor, replacement)))


def test_two_jobs_reporting_the_required_check_are_rejected(tmp_path: Path) -> None:
    second = mutate("jobs:\n", "jobs:\n  other:\n    name: Tests\n    runs-on: ubuntu-latest\n    steps:\n      - run: 'true'\n")
    assert_rejects(check_the_required_check_is_pinned, workflow(tmp_path, second))
    assert len(required_check_jobs([workflow(tmp_path, second, "two.yml")])) == 2


def test_a_missing_gate_workflow_is_a_failure_not_an_empty_parametrisation() -> None:
    """The pin runs over GATE_FILES, which is derived from the directory; if
    tests.yml vanished the parametrisation would be empty. `test_both_gate_
    workflows_exist` is the assertion that turns that into red, and this
    checks the derivation actually reports absence."""
    assert workflow_files_in(WORKFLOWS_DIR / "absent") == []
    assert [p.name for p in GATE_FILES] == sorted(GATE_WORKFLOWS)


def test_a_workflow_with_none_of_the_subjects_reports_them_missing(tmp_path: Path) -> None:
    hollow = 'name: Hollow\n"on": [push]\npermissions:\n  contents: read\njobs:\n  nothing:\n    runs-on: ubuntu-latest\n    steps:\n      - name: Do nothing\n        run: "true"\n'
    assert missing_subjects([workflow(tmp_path, hollow)]) == ["checkout", "gate", "pytest", "python-version", "required-check", "timeout-minutes", "upload"]
    assert missing_subjects([workflow(tmp_path, GOOD_WORKFLOW, "good.yml")]) == []


def test_the_disclosed_holes_are_real(tmp_path: Path) -> None:
    """What still gets through, asserted open.

    1. `( cmd ) || true`: the failure is in a subshell, errexit never sees
       it, the executed rule reports nothing; the textual net catches it.
    2. `bash -c 'cmd || true'`: the inner shell is a stub, so the inner text
       is never executed or read. Nothing here catches it.
    3. Indirection through a variable: reported as UNMODELLED, so the check
       fails for "could not model this" rather than "this swallows".
    4. `cd tests/unit && pytest` narrows by directory with a clean command
       line. `working-directory:` is caught on the required check's steps;
       the `cd` is not.
    5. `PYTEST_ADD""OPTS=-x` assembled from pieces defeats the token rule.
    6. The credential-on-a-command-line rule is textual and reads `$NAME`:
       `python x.py --key "$(printenv CBB_ODDS_API_KEY)"` names the variable
       with no `$` in front of it and passes. The rule catches the `$` shape
       wherever it sits, including an intermediate assignment.
    7. The six operational workflows are held to the corpus rules only.
       Their `continue-on-error`, `|| true` and `if-no-files-found: warn` are
       deliberate and are not executed here — and warn is the family of the
       purchase defect this file pins by path. That is a scope, stated.

    Three more from attacking the 2026-09-04 rules, each measured:

    8. The whole-command pin is EXACT, and that cuts both ways. `python3` in
       place of `python`, or the gate's two arguments in the other order, is
       refused although either would run. A rule that pins a command pins the
       command; the cost is that a legitimate rewording is a red build until
       someone edits this file too.
    9. The junit path has to be spelled the SAME way in the suite line and
       the gate line. `${{ runner.temp }}/junit.xml` written and
       `$RUNNER_TEMP/junit.xml` gated is the same file and is refused, by
       `the_gate_reads_the_evidence_this_run_wrote`, which compares strings.
    10. `PYTHONSAFEPATH` is required on the step that runs pytest and on no
       other step and in no other workflow — and the exposure it leaves
       behind is NOT one shape but two. `python -m pytest` and
       `python -m compileall` put the WORKING DIRECTORY at `sys.path[0]`,
       which is the route a tracked root `pytest.py` takes.
       `python scripts/check_test_results.py` does not: run below, the
       interpreter puts the SCRIPT'S OWN directory at `sys.path[0]` and the
       working directory nowhere on the path. So the gate step's exposure is
       a tracked `scripts/<stdlib name>.py`, and the byte-compile step's is
       the root-level one; the six operational workflows run both shapes.
       An earlier version of this item named the working directory for all of
       them, which is the wrong mechanism for the gate step. Both arms are run
       below, and so is the one that shows what the variable buys: under
       `PYTHONSAFEPATH=1` a module in the working directory is not importable
       at all and the script's own directory is off the path too. Neither
       exposure is closed on the steps that do not set it.
    11. Branch protection is measured out of band, and no rule in this file
       reads it. Measured 2026-09-05 with
       `gh api repos/cooperross399/cbb-betting-lab/branches/main/protection`,
       main requires the context `Tests` and no other — so a red
       `Ledger Guard`, a gate this file executes under stubs like the other,
       does not hold the merge button — and `required_status_checks.strict`
       is false, so a green tick may have been earned against a base main has
       since moved past. What IS assertable here is the half that makes the
       first sentence bite: the ledger gate reports under a context this file
       does not pin as required.
    """
    subshell = f"( {GATE_COMMAND} ) || true"
    assert swallow_findings(subshell + "\n") == []
    assert unguarded_or_branches(subshell) == ["true"]

    nested = f"bash -c '{GATE_COMMAND} || true'"
    assert swallow_findings(nested + "\n") == []
    assert unguarded_or_branches(nested) == []

    findings = swallow_findings('GATE="python gate.py || true"\neval "$GATE"\n')
    assert findings and "never modelled" in findings[0]

    check_the_suite_is_never_narrowed(workflow(tmp_path, mutate(SUITE_LINE, 'cd tests/unit && python -m pytest -q --junit-xml="$RUNNER_TEMP/j.xml"'), "moved.yml"))
    for assembled in ('export PYTEST_ADD""OPTS=-x', "export PYTEST_${X}ADDOPTS=-x"):
        assert not PYTEST_ADDOPTS_TOKEN.search(assembled)

    check_the_credential_is_never_spelled_onto_a_command_line(
        workflow(tmp_path, mutate(f"        run: {GATE_COMMAND}\n", '        run: python x.py --key "$(printenv CBB_ODDS_API_KEY)"\n'), "indirect.yml")
    )
    # 6 is honest only while the `$` shapes ARE rejected, the intermediate
    # assignment included.
    for direct in ('python x.py --key "$CBB_ODDS_API_KEY"', 'X=$CBB_ODDS_API_KEY\n          python x.py --key "$X"'):
        assert_rejects(
            check_the_credential_is_never_spelled_onto_a_command_line,
            workflow(tmp_path, mutate(f"        run: {GATE_COMMAND}\n", f"        run: |\n          {direct}\n"), "direct.yml"),
        )

    # 8 and 9 are honest only while those spellings ARE refused.
    for reworded in (
        "        run: python3 scripts/check_test_results.py",
        "        run: /usr/bin/env python scripts/check_test_results.py",
    ):
        assert_rejects(
            check_the_gate_line_is_pinned_as_a_whole_command,
            workflow(tmp_path, GOOD_WORKFLOW.replace("        run: python scripts/check_test_results.py", reworded)),
        )
    assert_rejects(
        check_the_gate_reads_the_evidence_this_run_wrote,
        workflow(tmp_path, mutate(SUITE_LINE, 'python -m pytest -q -rs --junit-xml="${{ runner.temp }}/junit.xml"')),
    )
    # 10: only the pytest step is required to carry it.
    safepath_steps = [
        step.get("name")
        for path in GATE_FILES
        for job in jobs_of(load(path)).values()
        for step in steps_of(job)
        if isinstance(step.get("env"), dict) and SAFE_PATH_VARIABLE in step["env"]
    ]
    assert safepath_steps == ["Run the suite"], safepath_steps

    # 10, the mechanism, RUN rather than recalled: `-m` and `script.py` do not
    # leave the same directory on sys.path, so they do not leave the same
    # hole. The environment is built explicitly, because the step that runs
    # this suite sets PYTHONSAFEPATH and would otherwise decide both arms.
    probe_root = tmp_path / "sys-path-probe"
    (probe_root / "scripts").mkdir(parents=True)
    probe = "import sys\nprint(sys.path[0])\n"
    (probe_root / "scripts" / "probe.py").write_text(probe, encoding="utf-8")
    (probe_root / "asmodule.py").write_text(probe, encoding="utf-8")

    def _probe(argv: list[str], *, safe_path: bool) -> subprocess.CompletedProcess:
        environment = dict(os.environ)
        environment.pop(SAFE_PATH_VARIABLE, None)
        if safe_path:
            environment[SAFE_PATH_VARIABLE] = "1"
        return subprocess.run(
            [sys.executable, *argv],
            cwd=probe_root, env=environment, capture_output=True, text=True, timeout=60,
        )

    by_script = _probe(["scripts/probe.py"], safe_path=False)
    by_module = _probe(["-m", "asmodule"], safe_path=False)
    assert by_script.returncode == 0, by_script.stderr
    assert by_module.returncode == 0, by_module.stderr
    assert by_script.stdout.strip() == str(probe_root / "scripts"), by_script.stdout
    assert Path(by_module.stdout.strip()).resolve() == probe_root.resolve(), by_module.stdout

    # And with the variable the suite step sets, NEITHER directory is there:
    # a module sitting in the working directory is not importable at all, and
    # the script's own directory is off the path too.
    assert _probe(["-m", "asmodule"], safe_path=True).returncode != 0
    guarded = _probe(["scripts/probe.py"], safe_path=True)
    assert guarded.returncode == 0, guarded.stderr
    assert guarded.stdout.strip() != str(probe_root / "scripts"), guarded.stdout

    # 11: the ledger gate reports under a context this file does not pin as
    # required, which is why protection requiring only `Tests` leaves it out.
    ledger_job_names = {
        job.get("name") for job in jobs_of(load(WORKFLOWS_DIR / LEDGER_WORKFLOW)).values()
    }
    assert REQUIRED_CHECK not in ledger_job_names, ledger_job_names

    operational = [p for p in WORKFLOW_FILES if p.name not in GATE_WORKFLOWS]
    assert len(operational) == 6, [p.name for p in operational]
    warning_uploads = [
        p.name for p in operational
        for step in steps_using(load(p), "actions/upload-artifact")
        if (step.get("with") or {}).get("if-no-files-found") != "error"
    ]
    assert warning_uploads, "every operational upload now errors on nothing to upload; move this out of the ledger and into the corpus rules"


def _step_names(path: Path) -> list[str]:
    """The `- name:` entries of a workflow, in order, comments excluded."""
    return [
        line.split("name:", 1)[1].strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip().startswith("- name:")
    ]


def test_the_purchase_uploads_raw_responses_before_anything_can_die() -> None:
    """Defect S. Run 33917619764 spent 1,199,926 credits, then the store
    rebuild was OOM-killed and every later step — the raw-response upload and
    both cache saves — was skipped. Nothing was persisted.

    The raw responses ARE the purchase; the store is derived from them for
    free. So the upload of the responses must come before the rebuild, and
    before anything else that can fail. Order is read from the file.
    """
    names = _step_names(WORKFLOWS_DIR / "historical-purchase.yml")
    buy = names.index("Buy")
    upload = next(i for i, n in enumerate(names) if n.startswith("Upload the raw bought responses"))
    rebuild = next(i for i, n in enumerate(names) if n.startswith("Build the store"))
    assert buy < upload < rebuild, (
        f"Step order is {names[buy:rebuild + 1]}. The raw-response upload must "
        "sit between Buy and the rebuild, so a rebuild that dies cannot take "
        "the purchase with it."
    )


def test_the_purchase_rebuild_covers_every_wave() -> None:
    """Defect U. A rebuild scoped to the run's own wave appended onto a stale
    restored store, and the store shrank from 2.9M rows to 2.3M while the raw
    cache held everything."""
    text = (WORKFLOWS_DIR / "historical-purchase.yml").read_text(encoding="utf-8")
    rebuild = text[text.index("Build the store from the cached responses"):]
    rebuild = rebuild[: rebuild.index("- name:", 10)]
    assert "--waves all" in rebuild, (
        "The rebuild step scopes itself to this run's wave, so the store it "
        "writes omits every other wave the cache holds."
    )


# --------------------------------------------------------------------------
# The ledger guard on a branch's first push.
# --------------------------------------------------------------------------

ZERO_SHA = "0" * 40


def _base_resolution_block() -> str:
    """The real `run:` text of the guard's base-resolution step, by name."""
    document = yaml.safe_load((WORKFLOWS_DIR / LEDGER_WORKFLOW).read_text(encoding="utf-8"))
    for job in document["jobs"].values():
        for step in steps_of(job):
            if step.get("name") == "Resolve the base commit, or stop":
                return step["run"]
    raise AssertionError("the ledger guard has no 'Resolve the base commit, or stop' step")


def _resolve_base(event: str, before: str, failing: set[str], sandbox: Path) -> tuple[int, str]:
    """Run the real step under stubs with the event's env, and read what it
    resolved. `GITHUB_OUTPUT` is pointed at a sandbox file because the step
    appends `sha=...` there and `set -u` would otherwise abort on it."""
    out = sandbox / "github_output"
    out.write_text("", encoding="utf-8")
    prefix = (
        f"EVENT_NAME={_quote(event)}; PR_BASE_SHA=''; PUSH_BEFORE_SHA={_quote(before)}; "
        f"GITHUB_OUTPUT={_quote(str(out))}\n"
    )
    result = run_block_under_stubs(prefix + _base_resolution_block(), failing, sandbox)
    assert not result.unmodelled, f"commands reached the shell with no stub: {result.unmodelled}"
    return result.exit_code, out.read_text(encoding="utf-8")


def test_a_first_push_compares_against_main_instead_of_failing() -> None:
    """A branch's first push carries an all-zeros `before` — there is no
    previous tip. The guard used to exit 1 there, so every new branch opened
    with this check red and the PR run green, and a guard that is red on every
    first push is a guard people learn to ignore (seen on #6, #7 and #8).

    For a new branch the ledger's true base IS main: every commit on it is
    after main by definition. So the step fetches origin/main and compares
    against that, and the check runs rather than declining to."""
    with tempfile.TemporaryDirectory() as directory:
        code, output = _resolve_base("push", ZERO_SHA, set(), Path(directory))
    assert code == 0, "the guard still refuses to run on a first push"
    assert "sha=origin/main" in output, f"expected origin/main as the base, got {output!r}"


def test_a_later_push_still_compares_against_its_own_previous_tip() -> None:
    """The fallback is for the zero SHA only. A real `before` is the right
    base for a subsequent push and must not be replaced by main."""
    with tempfile.TemporaryDirectory() as directory:
        code, output = _resolve_base("push", "a" * 40, set(), Path(directory))
    assert code == 0
    assert "sha=" + "a" * 40 in output
    assert "origin/main" not in output


def test_a_first_push_that_cannot_fetch_main_fails_loudly() -> None:
    """If origin/main cannot be fetched there is no base, and the step must
    say the check did not run rather than pass by default."""
    with tempfile.TemporaryDirectory() as directory:
        code, output = _resolve_base("push", ZERO_SHA, {"git"}, Path(directory))
    assert code != 0, "a first push with no reachable main resolved a base from nothing"
    assert "sha=" not in output


def test_the_purchase_restores_the_latest_cache_of_any_wave() -> None:
    """The cache restore must not be scoped to this run's wave.

    A wave-scoped first restore key HIT for a wave bought before and shadowed
    the any-wave fallback, so a rebuild dispatched as `core_team` restored only
    core_team's responses and rebuilt "all waves" from a disk that held one —
    2,946,929 rows reported while the props cache held the complete surviving
    set. The rebuild's `--waves all` was defeated one layer up.

    So: the key is unique per run (always a miss, so the post-step always
    saves), and the ONLY restore key is the any-wave prefix, which resolves to
    the most recently created cache — the last run of any wave, which already
    accumulated everything before it.
    """
    document = yaml.safe_load((WORKFLOWS_DIR / "historical-purchase.yml").read_text(encoding="utf-8"))
    restores = [
        step for job in document["jobs"].values() for step in steps_of(job)
        if str(step.get("uses", "")).startswith("actions/cache")
        and "historical_purchase" in str((step.get("with") or {}).get("path", ""))
    ]
    assert len(restores) == 1, f"expected one response-cache restore step, found {len(restores)}"
    with_ = restores[0]["with"]
    assert "github.run_id" in with_["key"], "the save key must be unique per run so every run saves"
    assert "inputs.waves" not in with_["key"], "the key must not be wave-scoped"
    restore_keys = [k.strip() for k in str(with_.get("restore-keys", "")).splitlines() if k.strip()]
    assert restore_keys, "no restore-keys: a run would start from an empty cache every time"
    assert all("inputs.waves" not in k for k in restore_keys), (
        f"a wave-scoped restore key {restore_keys!r} hits before the any-wave one "
        "and shadows it — the exact defect this test pins"
    )


def test_the_purchase_can_merge_an_orphaned_lineage_from_its_artifact() -> None:
    """The any-wave restore key resolves to ONE cache — the latest — so a run
    whose cache was saved before another run started is a lineage the chain
    never restores again. The 609-event ladders run survived only in its own
    cache and its artifact while every later run restored the props lineage.

    The workflow must be able to merge a named run's raw-response artifact on
    top of the restored cache before the rebuild, so the post-save holds the
    union and every later run inherits it."""
    document = yaml.safe_load((WORKFLOWS_DIR / "historical-purchase.yml").read_text(encoding="utf-8"))
    triggers = document.get("on") or document.get(True) or {}
    inputs = triggers["workflow_dispatch"]["inputs"]
    assert "merge_artifact_runs" in inputs
    names = [s.get("name", "") for job in document["jobs"].values() for s in steps_of(job)]
    merge = next(i for i, n in enumerate(names) if n.startswith("Merge prior runs"))
    restore = next(i for i, n in enumerate(names) if n == "Restore the bought responses")
    rebuild = next(i for i, n in enumerate(names) if n.startswith("Build the store"))
    assert restore < merge < rebuild, f"merge must sit between restore and rebuild; order is {names[restore:rebuild+1]}"
    step = [s for job in document["jobs"].values() for s in steps_of(job) if str(s.get("name","")).startswith("Merge prior runs")][0]
    assert "cp -Rn" in step["run"], "an existing response must never be overwritten by an older lineage's copy"
# --------------------------------------------------------------------------
# The four rules added on 2026-09-04, each watched failing.
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    "argument",
    ["--version", "-h", "--help", "-vv", "--tb=short", "--durations=10", "--failed-first", "-p", "--co", "-x"],
)
def test_an_argument_that_is_not_on_the_whitelist_is_rejected(tmp_path: Path, argument: str) -> None:
    """`--version`, `-h` and `--help` are the three that matter: each exits 0,
    runs no test and writes NO junit. The rest are on the list because a
    whitelist refuses everything nobody wrote down, which is the point of
    having one."""
    text = mutate(SUITE_LINE, f'python -m pytest -q -rs {argument} --junit-xml="$RUNNER_TEMP/junit.xml"')
    assert_rejects(check_the_suite_line_carries_only_whitelisted_arguments, workflow(tmp_path, text))


@pytest.mark.parametrize("flag", ["-q", "-rs"])
def test_the_whitelisted_arguments_are_accepted(tmp_path: Path, flag: str) -> None:
    text = mutate(SUITE_LINE, f'python -m pytest {flag} --junit-xml="$RUNNER_TEMP/junit.xml"')
    check_the_suite_line_carries_only_whitelisted_arguments(workflow(tmp_path, text))


@pytest.mark.parametrize(
    "suite_line",
    [
        'python -m pytest -q -rs --junit-xml="tests/fixtures/green.xml"',
        'python -m pytest -q -rs --junit-xml="junit.xml"',
        'python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/../tests/fixtures/green.xml"',
        'python -m pytest -q -rs --junit-xml "$RUNNER_TEMP/junit.xml"',
        'python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/a.xml" --junit-xml="$RUNNER_TEMP/b.xml"',
        "python -m pytest -q -rs",
    ],
    ids=["tracked-fixture", "in-the-checkout", "escapes-the-temp", "separated-form", "two-junits", "no-junit"],
)
def test_a_junit_this_run_did_not_write_is_rejected(tmp_path: Path, suite_line: str) -> None:
    """The other half of the `--version` attack: the flag has to point
    somewhere only this run can have written."""
    assert_rejects(
        check_the_suite_line_carries_only_whitelisted_arguments,
        workflow(tmp_path, mutate(SUITE_LINE, suite_line)),
    )


def test_the_tracked_fixture_the_rule_refuses_is_really_tracked() -> None:
    """The rule's teeth rest on `git ls-files`, so the set has to be real."""
    tracked = tracked_paths()
    assert tracked, "git ls-files reported nothing; the tracked-path rule would pass on anything"
    assert "tests/test_workflows.py" in tracked
    assert "$RUNNER_TEMP/junit.xml" not in tracked


@pytest.mark.parametrize(
    "gate_line",
    [
        ': python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml" --newer-than "$RUNNER_TEMP/suite_started_at"',
        'echo python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml" --newer-than "$RUNNER_TEMP/suite_started_at"',
        'true python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml" --newer-than "$RUNNER_TEMP/suite_started_at"',
        'python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"',
        'python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml" --newer-than "tests/fixtures/marker"',
    ],
    ids=["no-op-colon", "echoed", "true-prefix", "no-marker", "marker-in-the-checkout"],
)
def test_a_gate_line_that_only_contains_the_gate_is_rejected(tmp_path: Path, gate_line: str) -> None:
    """Measured 2026-09-04: `: python scripts/check_test_results.py <path>`
    passed all fourteen gate rules as they then stood, because every one of
    them asked whether the line CONTAINED the script and the path."""
    text = mutate(f"        run: {GATE_COMMAND}\n", "        run: |\n          " + gate_line + "\n")
    assert_rejects(check_the_gate_line_is_pinned_as_a_whole_command, workflow(tmp_path, text))


def test_a_gate_step_that_does_more_than_gate_is_rejected(tmp_path: Path) -> None:
    """A second command in the gate step is a place to put the replacement."""
    text = gate_block('cp fixtures/green.xml "$RUNNER_TEMP/junit.xml"', GATE_COMMAND)
    assert_rejects(check_the_gate_line_is_pinned_as_a_whole_command, workflow(tmp_path, text))


@pytest.mark.parametrize(
    "gate_line",
    [
        ': python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml" --newer-than "$RUNNER_TEMP/suite_started_at"',
        'echo python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml" --newer-than "$RUNNER_TEMP/suite_started_at"',
    ],
    ids=["no-op-colon", "echoed"],
)
def test_a_gate_step_that_never_invokes_the_gate_is_rejected(tmp_path: Path, gate_line: str) -> None:
    """The EXECUTED half. Under `:` the word `python` is an argument to a
    builtin: no stub is entered, so the invocation list is empty and the rule
    reports that nothing ran, rather than that a spelling was wrong."""
    text = mutate(f"        run: {GATE_COMMAND}\n", "        run: |\n          " + gate_line + "\n")
    assert_rejects(check_the_gate_step_really_runs_the_gate, workflow(tmp_path, text))


def test_the_executed_gate_rule_sees_the_real_gate_run(tmp_path: Path) -> None:
    """The control: the pinned command IS observed being invoked, with the
    script as its first argument."""
    check_the_gate_step_really_runs_the_gate(workflow(tmp_path, GOOD_WORKFLOW))
    with tempfile.TemporaryDirectory() as directory:
        result = run_block_under_stubs(GATE_COMMAND + "\n", set(), Path(directory), record_invocations=True)
    assert [(w, a[0]) for w, a in result.invocations] == [("python", f"scripts/{GATE_SCRIPT}")]


@pytest.mark.parametrize("value", ["", "'0'", "0", "'true'"], ids=["absent", "zero-string", "zero", "true"])
def test_a_suite_step_without_pythonsafepath_is_rejected(tmp_path: Path, value: str) -> None:
    if value:
        text = mutate(SAFEPATH_BLOCK, f"        env:\n          PYTHONSAFEPATH: {value}\n")
    else:
        text = mutate(SAFEPATH_BLOCK, "")
    assert_rejects(check_the_suite_step_disables_the_path_shadows, workflow(tmp_path, text))


@pytest.mark.parametrize(
    "mutation",
    [
        ("    runs-on: ubuntu-latest\n", "    runs-on: ubuntu-latest\n    needs: prep\n"),
        ("jobs:\n", "jobs:\n  prep:\n    runs-on: ubuntu-latest\n    if: false\n    steps:\n      - run: 'true'\n"),
        ("jobs:\n", "jobs:\n  prep:\n    runs-on: ubuntu-latest\n    if: ${{ github.event_name == 'schedule' }}\n    steps:\n      - run: 'true'\n"),
    ],
    ids=["needs-on-the-required-job", "a-second-job-with-if-false", "a-second-job-with-any-if"],
)
def test_a_needs_or_a_conditional_neighbour_is_rejected(tmp_path: Path, mutation: tuple[str, str]) -> None:
    """`needs:` is `if: false` reworded, and it is one line.

    GitHub's troubleshooting documentation states that a required check
    skipped by a CONDITION reports as Success — unlike one skipped by a path
    filter, which stays pending. So a required job that waits on a job which
    can be skipped is a required job that can be skipped into a green tick,
    and this file could not see it: measured 2026-09-04, `needs: prep` with a
    `prep` carrying `if: false` passed every one of the twenty-four rules.
    """
    anchor, replacement = mutation
    assert_rejects(check_the_required_check_is_pinned, workflow(tmp_path, mutate(anchor, replacement)))


def test_a_secret_in_the_required_workflows_env_is_rejected(tmp_path: Path) -> None:
    """The bypass this rule was written for, in the spelling that worked.

    Binding the secrets context to an `env:` key on the suite step satisfies
    the corpus rule, which permits exactly that, and it passed the whole module
    before this rule existed. The required workflow gets no credential at all,
    so here it must be refused.
    """
    anchor = "      - name: Run the suite\n        env:\n"
    for spelling in (
        "          TOK: ${{ secrets.CBB_ODDS_API_KEY }}\n",
        "          TOK: ${{ secrets['CBB_ODDS_API_KEY'] }}\n",
        "          TOK: ${{ toJSON(secrets) }}\n",
        "          TOK: ${{ SECRETS.CBB_ODDS_API_KEY }}\n",
    ):
        assert_rejects(
            check_the_required_workflow_holds_no_secret_at_all,
            workflow(tmp_path, mutate(anchor, anchor + spelling)),
        )


def test_the_secret_name_in_prose_is_not_a_secret_reference(tmp_path: Path) -> None:
    """The header names the secret in prose deliberately, so the rule must not
    reject the real file. A rule that rejects correct work is a rule somebody
    deletes."""
    check_the_required_workflow_holds_no_secret_at_all(WORKFLOWS_DIR / TESTS_WORKFLOW)


# --------------------------------------------------------------------------
# The gameday card has the tables it prices from, because they are built first.
# --------------------------------------------------------------------------

GAMEDAY_WORKFLOW = "cbb-gameday-refresh.yml"


def _card_job_steps() -> list[dict]:
    path = WORKFLOWS_DIR / GAMEDAY_WORKFLOW
    assert path.is_file(), f"{GAMEDAY_WORKFLOW} is missing"
    document = load(path)
    jobs = jobs_of(document)
    assert "card" in jobs, f"{GAMEDAY_WORKFLOW} has no `card` job; found {sorted(jobs)}"
    steps = steps_of(jobs["card"])
    assert steps, "the card job has no steps"
    return steps


def _step_index_running(steps: list[dict], script: str) -> int:
    """The index of the ONE step whose run block executes `script`."""
    hits = [
        i for i, step in enumerate(steps)
        if isinstance(step.get("run"), str)
        and any(script in line for line in commands(step["run"]))
    ]
    assert len(hits) == 1, f"{script} is run by {len(hits)} step(s) of the card job; expected exactly one"
    return hits[0]


def test_the_gameday_card_runs_after_the_tables_it_prices_from_are_built() -> None:
    """`run_gameday_card.py` now refuses without `cbb_team_games.csv`, so the
    step that builds it must come first in the same job — parsed from the YAML
    and located by the command it runs, not by a step name. A card step ahead
    of the build step would refuse every slot of the season."""
    steps = _card_job_steps()
    build = _step_index_running(steps, "scripts/build_datasets.py")
    card = _step_index_running(steps, "scripts/run_gameday_card.py")
    fetch = _step_index_running(steps, "scripts/fetch_cbb_data.py")

    assert fetch <= build < card, (
        f"fetch at step {fetch}, build at {build}, card at {card}: the tables are "
        "not on disk when the card runs"
    )
    # Within the one block, the fetch precedes the build.
    block = commands(steps[build]["run"])
    fetched = next(i for i, line in enumerate(block) if "fetch_cbb_data.py" in line)
    built = next(i for i, line in enumerate(block) if "build_datasets.py" in line)
    assert fetched < built, "the tables are built before the feeds they are built from are fetched"


def test_the_gameday_tables_step_builds_the_season_the_card_prices() -> None:
    """The build names the current season by hoopR's ending-year label, so the
    schedule the card joins on (`mbb_schedule_2027.parquet` for 2026-27) is
    fetched. A season list that stopped at 2026 would leave every 2026-27
    event with no fixture and the model with nothing to price."""
    steps = _card_job_steps()
    block = "\n".join(commands(steps[_step_index_running(steps, "scripts/build_datasets.py")]["run"]))
    assert re.search(r"SEASONS=\"[^\"]*\b2027\b", block), block


def test_the_gameday_card_step_reads_the_directory_the_build_step_writes() -> None:
    """The card step passes no `--processed-dir`, so it reads the default,
    `data/processed` — which is where `build_datasets.py` writes and where the
    ledger-restore step already `mkdir -p`s. Pinned so a future `--processed-dir`
    on one side and not the other is a red build rather than a refused season."""
    from cbb_betting_lab.config import PROCESSED_DIR, REPO_ROOT

    steps = _card_job_steps()
    card_block = "\n".join(commands(steps[_step_index_running(steps, "scripts/run_gameday_card.py")]["run"]))
    build_block = "\n".join(commands(steps[_step_index_running(steps, "scripts/build_datasets.py")]["run"]))
    default = str(Path(PROCESSED_DIR).relative_to(REPO_ROOT))
    assert default == "data/processed"
    if "--processed-dir" in card_block:
        assert re.search(r"--processed-dir\s+\"?data/processed", card_block), card_block
    assert "--output-dir" not in build_block or "data/processed" in build_block


# --------------------------------------------------------------------------
# The policy gate, executed rather than read.
#
# `docs/what_we_can_and_cannot_claim.md`, `data/manual/README.md` and
# `src/cbb_betting_lab/reports/what_we_can_claim.py` all say a market joins the
# allowlist "in a pull request whose policy gate is green". Until
# `.github/workflows/policy-gate.yml` existed there was no such gate: nothing
# under `.github/workflows/` opened a receipt, and a pull request carrying an
# unreceipted allowlist was green.
#
# The rules below are the gate's pin. The first three read the parsed file —
# its triggers, its permissions, and which command its step actually enters.
# The rest EXECUTE the gate's own run block, verbatim out of the YAML, against
# fabricated checkouts on disk: an unreceipted allowlist, a receipt whose
# evidence has moved underneath it, a receipt signed by Claude, and an
# allowlist entry the diff adds. A string assertion about a workflow's shell
# logic proves a spelling is present; these read the exit code.
# --------------------------------------------------------------------------

POLICY_GATE_PATH = WORKFLOWS_DIR / POLICY_GATE_WORKFLOW
#: The script the gate's step must actually invoke, spelled as the workflow
#: spells it. Pinned as a whole first argument, the way the junit gate is.
RECEIPT_CHECKER = "scripts/check_allowlist_receipts.py"
#: The paths the gate reads, written as literals rather than imported from
#: `staging_provider_policy`. The module is what the gate calls; a test that
#: asked the module where the receipts live could not notice the two of them
#: agreeing on the wrong directory.
POLICY_FILE_RELATIVE = "data/manual/staging_provider_policy.json"
RECEIPTS_RELATIVE = "data/manual/human_acceptance_receipts"
#: Signers this repository could produce by itself, in the spellings
#: `staging_provider_policy.FORBIDDEN_SIGNER` is matched against.
SELF_SIGNATURES = ("Claude", "claude-code", "Claude Opus 5", "C.L.A.U.D.E.")


def policy_gate_step() -> dict:
    """The one step in the policy gate that runs the receipt checker."""
    steps = steps_running(load(POLICY_GATE_PATH), re.escape(RECEIPT_CHECKER))
    assert len(steps) == 1, (
        f"{POLICY_GATE_WORKFLOW} runs {RECEIPT_CHECKER} in {len(steps)} steps; the "
        "rules below execute one block and would silently stop covering the others"
    )
    return steps[0]


def policy_checkout(root: Path) -> Path:
    """A checkout-shaped directory: the data tree the gate reads, plus the
    real `src/` and `scripts/` so the block runs the tracked script."""
    tree = root / "checkout"
    (tree / RECEIPTS_RELATIVE).mkdir(parents=True)
    (tree / "data" / "outputs").mkdir(parents=True)
    (tree / "src").symlink_to(PROJECT_ROOT / "src")
    (tree / "scripts").symlink_to(PROJECT_ROOT / "scripts")
    return tree


def write_policy(tree: Path, *markets: str, mode: str = "reviewed") -> None:
    (tree / POLICY_FILE_RELATIVE).write_text(
        json.dumps(
            {
                "provider": "the_odds_api",
                "mode": mode,
                "allowlist": [
                    {
                        "market": market,
                        "receipt_id": f"r-{market}",
                        "approved_on": "2026-12-01",
                        "roi_floor": -0.02,
                        "evidence_checksum": "",
                        "minimum_bets": 200,
                        "note": "synthetic, in a temporary directory, for a test",
                    }
                    for market in markets
                ],
                "withdrawn": [],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def write_receipt(
    tree: Path,
    market: str,
    *,
    signed_by: str = "Cooper Ross",
    evidence: bytes = b'{"roi": -0.031, "bets": 4830}\n',
    cite_instead: bytes | None = None,
    delete_evidence: bool = False,
) -> Path:
    """A receipt for `market` in `tree`, signed by `signed_by`.

    `cite_instead` cites the sha256 of OTHER bytes than the ones on disk,
    which is the evidence record that moved underneath a signature.
    `delete_evidence` writes the receipt and removes the record it cites.
    """
    relative = f"data/outputs/{market}_evidence.json"
    record = tree / relative
    record.write_bytes(evidence)
    digest = hashlib.sha256(cite_instead if cite_instead is not None else evidence).hexdigest()
    if delete_evidence:
        record.unlink()
    path = tree / RECEIPTS_RELATIVE / f"r-{market}.json"
    path.write_text(
        json.dumps(
            {
                "receipt_id": f"r-{market}",
                "market": market,
                "evidence": {"path": relative, "sha256": digest},
                "signed_by": signed_by,
                "signed_on": "2026-12-01",
                "note": "synthetic, in a temporary directory, for a test",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def run_policy_gate_for_real(
    tree: Path, *, event: str = "push", base_sha: str = ""
) -> tuple[subprocess.CompletedProcess[str], str]:
    """The gate's run block, verbatim, executed against `tree` with a real
    interpreter and real git. Returns the completed process and the job
    summary the step wrote."""
    assert HARNESS_SHELL, "no bash on PATH: the executed rules cannot run"
    binaries = tree.parent / "bin"
    binaries.mkdir(exist_ok=True)
    shim = binaries / "python"
    shim.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n', encoding="utf-8")
    shim.chmod(0o755)
    script = tree / "run_block.sh"
    script.write_text(policy_gate_step()["run"], encoding="utf-8")
    environment = {
        "PATH": f"{binaries}:{os.environ.get('PATH', '/usr/bin:/bin')}",
        "HOME": str(tree),
        "LC_ALL": "C",
        "EVENT_NAME": event,
        "PR_BASE_SHA": base_sha,
    }
    for name in RUNNER_FILE_VARIABLES:
        target = tree.parent / name.lower()
        target.write_text("", encoding="utf-8")
        environment[name] = str(target)
    completed = subprocess.run(
        [HARNESS_SHELL, "-e", str(script)],
        cwd=tree, env=environment, capture_output=True, text=True, timeout=120,
    )
    summary = (tree.parent / "github_step_summary").read_text(encoding="utf-8")
    return completed, summary


def commit_policy_tree(tree: Path) -> str:
    """`git init` plus one commit of the data tree. Returns the commit sha,
    which is what a pull request's base commit is."""
    identity = [
        "-c", "user.name=cbb tests", "-c", "user.email=tests@example.invalid",
        "-c", "commit.gpgsign=false",
    ]
    environment = dict(os.environ, HOME=str(tree.parent), GIT_CONFIG_NOSYSTEM="1", **GIT_IDENTITY)
    subprocess.run(["git", "init", "-q", "-b", "main", str(tree)], check=True, env=environment)
    subprocess.run(["git", "-C", str(tree), "add", "data"], check=True, env=environment)
    subprocess.run(
        ["git", "-C", str(tree), *identity, "commit", "-q", "-m", "base"],
        check=True, env=environment,
    )
    resolved = subprocess.run(
        ["git", "-C", str(tree), "rev-parse", "HEAD"],
        check=True, capture_output=True, text=True, env=environment,
    )
    return resolved.stdout.strip()


def test_the_policy_gate_fires_on_every_pull_request_and_filters_none_of_them() -> None:
    """The trigger, pinned. `pull_request` with no `paths:`, no `branches:`
    and no `types:`.

    The cluster this file closes asked for a gate "on every pull request
    touching data/manual/staging_provider_policy.json", and the natural
    spelling of that is a `paths:` filter. `check_no_trigger_is_path_filtered`
    refuses one, for a reason that applies here exactly: a path-filtered check
    is not reported on the pull requests it filters out, and the change that
    defeats a guard rarely touches the guard's own file. So the gate runs on
    every pull request instead, which is strictly more.
    """
    document = load(POLICY_GATE_PATH)
    pull_request = trigger_config(document, "pull_request")
    assert pull_request is not False, (
        f"{POLICY_GATE_WORKFLOW} does not fire on pull_request, so no pull request "
        "is ever checked and the sentence in the three documents is true of nothing"
    )
    if isinstance(pull_request, dict):
        for key in ("branches", "branches-ignore", "paths", "paths-ignore", "types"):
            assert key not in pull_request, (
                f"{POLICY_GATE_WORKFLOW}: pull_request carries `{key}:`; a filtered "
                "policy gate does not report on the pull requests it filters out"
            )
    for event in ("push", "workflow_dispatch"):
        assert trigger_config(document, event) is not False, (
            f"{POLICY_GATE_WORKFLOW} does not fire on {event}"
        )
    names = {job.get("name") for job in jobs_of(document).values()}
    assert REQUIRED_CHECK not in names, (
        f"{POLICY_GATE_WORKFLOW} reports under the required context {REQUIRED_CHECK!r}; "
        "two jobs under one context makes the context ambiguous"
    )


def test_the_policy_gate_holds_contents_read_and_no_secret_at_all() -> None:
    """Least privilege, read from the parsed file: `contents: read` at the top,
    no other `permissions:` mapping anywhere, and the secrets context absent
    from every line including the comments. A gate that can write can rewrite
    what it is checking, and this one needs no credential to read a receipt."""
    document = load(POLICY_GATE_PATH)
    assert document.get("permissions") == {"contents": "read"}, (
        f"{POLICY_GATE_WORKFLOW} declares `permissions: {document.get('permissions')!r}`; "
        "the policy gate reads a JSON file and hashes a record, and needs `contents: read`"
    )
    elsewhere = [m.get("permissions") for m in mappings(document) if m is not document and "permissions" in m]
    assert not elsewhere, f"{POLICY_GATE_WORKFLOW} re-declares permissions at {elsewhere}"
    for number, line in enumerate(POLICY_GATE_PATH.read_text(encoding="utf-8").splitlines(), start=1):
        assert not SECRET_REFERENCE.search(line) and not any(
            SECRETS_WORD.search(e.group(0)) for e in GITHUB_EXPRESSION.finditer(line)
        ), (
            f"{POLICY_GATE_WORKFLOW}:{number} reaches the secrets context. This gate "
            "is given no credential: it reads tracked files and hashes them."
        )
    for mapping in mappings(document):
        environment = mapping.get("env")
        if isinstance(environment, dict):
            assert not CREDENTIAL_NAMES.intersection(map(str, environment)), (
                f"{POLICY_GATE_WORKFLOW} binds a provider credential"
            )


def test_the_policy_gate_step_really_invokes_the_receipt_checker() -> None:
    """Executed under stubs, every stub succeeding, with the invocations
    recorded: the step must ENTER a command whose first argument is the
    tracked checker. `: python scripts/check_allowlist_receipts.py` contains
    the script and runs nothing, and that is what this rule tells apart."""
    block = policy_gate_step()["run"]
    with tempfile.TemporaryDirectory() as directory:
        result = run_block_under_stubs(
            block, set(), Path(directory), record_invocations=True,
            environment={"EVENT_NAME": "pull_request", "PR_BASE_SHA": "0" * 40},
        )
    assert result.unmodelled == [], f"the policy gate step could not be modelled: {result.unmodelled}"
    assert result.exit_code == 0, f"the policy gate step fails with every command succeeding: {result.stderr}"
    ran = [
        (word, arguments) for word, arguments in result.invocations
        if arguments and arguments[0] == RECEIPT_CHECKER
    ]
    assert ran, (
        f"the policy gate step never invoked anything with {RECEIPT_CHECKER} as its "
        f"first argument. Top-level invocations were {list(result.invocations)}."
    )
    assert any("--base-ref" in arguments for _, arguments in ran), (
        f"the policy gate runs {RECEIPT_CHECKER} without --base-ref, so it never "
        f"compares the allowlist against the base commit: {list(result.invocations)}"
    )


def test_the_policy_gate_block_stops_when_it_cannot_resolve_the_base_commit() -> None:
    """A base ref that cannot be read is a hard stop, not a pass. Executed
    three ways: the checker failing, git failing, and a pull request whose
    base sha is empty. "The base allowlisted nothing" and "I could not read
    the base" must never take the same branch."""
    block = policy_gate_step()["run"]
    pull_request = {"EVENT_NAME": "pull_request", "PR_BASE_SHA": "0" * 40}
    with tempfile.TemporaryDirectory() as directory:
        sandbox = Path(directory)
        checker_failed = run_block_under_stubs(
            block, {"python"}, sandbox, record_invocations=True, environment=pull_request,
        )
        assert checker_failed.exit_code != 0, "the block exits 0 when the receipt checker fails"

        git_failed = run_block_under_stubs(
            block, {"git"}, sandbox, record_invocations=True, environment=pull_request,
        )
        assert git_failed.exit_code != 0, (
            "the block exits 0 when git cannot resolve the base commit, so an "
            "unreadable base reads as a base that allowlisted nothing"
        )
        assert not [
            arguments for _, arguments in git_failed.invocations
            if arguments and arguments[0] == RECEIPT_CHECKER
        ], "the checker ran after the base commit could not be resolved"

        no_base = run_block_under_stubs(
            block, set(), sandbox, record_invocations=True,
            environment={"EVENT_NAME": "pull_request", "PR_BASE_SHA": ""},
        )
        assert no_base.exit_code != 0, (
            "a pull_request run with an empty base sha exits 0; the comparison "
            "never happened and nothing said so"
        )


def test_an_unreceipted_allowlist_makes_the_policy_gate_block_exit_non_zero(tmp_path: Path) -> None:
    """The question the whole gate exists for, executed against real trees.

    An allowlist entry with no receipt beside it must make the block exit
    non-zero and must name the market and what it lacked; the same tree with
    a receipt Cooper signed must exit zero. Both run the gate's own run block
    out of the YAML, so a step that stopped calling the checker fails here.
    """
    red_root = tmp_path / "red"
    red_root.mkdir()
    red = policy_checkout(red_root)
    write_policy(red, "spread")
    refused, summary = run_policy_gate_for_real(red)
    assert refused.returncode != 0, (
        f"an allowlisted market with no receipt passed the policy gate: {refused.stdout}"
    )
    assert "`spread`" in summary and "lacks" in summary, summary
    assert "human acceptance receipt" in refused.stderr, refused.stderr

    green_root = tmp_path / "green"
    green_root.mkdir()
    green = policy_checkout(green_root)
    write_policy(green, "spread")
    write_receipt(green, "spread")
    accepted, summary = run_policy_gate_for_real(green)
    assert accepted.returncode == 0, (
        f"a properly receipted allowlist was refused: {accepted.stdout}\n{accepted.stderr}"
    )
    assert "`spread`" in summary and "r-spread.json" in summary, summary


def test_the_policy_gate_refuses_an_allowlist_entry_no_receipt_names_even_at_manual_only(
    tmp_path: Path,
) -> None:
    """`load()` verifies receipts only when the file declares a mode other
    than `manual_only`, so an entry parked in a manual-only allowlist is not
    checked by the door the card uses — and it is one word away from live.
    The gate checks it anyway, and this is the case that proves it."""
    root = tmp_path / "parked"
    root.mkdir()
    tree = policy_checkout(root)
    write_policy(tree, "total_points", mode="manual_only")
    refused, summary = run_policy_gate_for_real(tree)
    assert refused.returncode != 0, (
        "an unreceipted market parked in a manual-only allowlist passed the gate: "
        f"{refused.stdout}"
    )
    assert "`total_points`" in summary, summary


def test_the_policy_gate_refuses_a_receipt_whose_evidence_moved_underneath_it(
    tmp_path: Path,
) -> None:
    """The stale-approval case the checksum exists for, both halves.

    `staging_provider_policy`'s own docstring records why the checksum is in
    a receipt at all: the NHL lab's approval was withdrawn when the evidence
    it had been signed against moved underneath it, and that lab's gate caught
    it on its own because the checksum stopped matching. This is the same
    question asked here, in both of its shapes: a receipt citing a sha256 the
    record no longer hashes to, and a receipt citing a record that is not on
    disk at all. Both are red, and the summary says which of the two it was.
    No figure from that lab is restated here; this test measures exit codes.
    """
    moved_root = tmp_path / "moved"
    moved_root.mkdir()
    moved = policy_checkout(moved_root)
    write_policy(moved, "spread")
    write_receipt(moved, "spread", evidence=b'{"roi": -0.016}\n', cite_instead=b'{"roi": 0.014}\n')
    refused, summary = run_policy_gate_for_real(moved)
    assert refused.returncode != 0, f"a receipt whose evidence moved passed the gate: {refused.stdout}"
    assert "`spread`" in summary and "hashes to" in summary, summary

    absent_root = tmp_path / "absent"
    absent_root.mkdir()
    absent = policy_checkout(absent_root)
    write_policy(absent, "spread")
    write_receipt(absent, "spread", delete_evidence=True)
    gone, summary = run_policy_gate_for_real(absent)
    assert gone.returncode != 0, f"a receipt citing a record that is not there passed: {gone.stdout}"
    assert "`spread`" in summary and "does not exist" in summary, summary


def test_the_policy_gate_cannot_be_satisfied_by_a_receipt_this_repository_could_write(
    tmp_path: Path,
) -> None:
    """Every field of a receipt except one is something a script can produce.

    The policy file, the market name, the evidence record and its sha256 are
    all machine output; `signed_by` is the whole human stop. So a receipt that
    is perfect in every other respect and signed by Claude — in any spelling,
    any casing, punctuated — must be refused, or this gate checks nothing that
    this repository could not have written for itself. There is no `grant()`
    and this is the reason there is none.
    """
    for index, signature in enumerate(SELF_SIGNATURES):
        root = tmp_path / f"self-signed-{index}"
        root.mkdir()
        tree = policy_checkout(root)
        write_policy(tree, "spread")
        write_receipt(tree, "spread", signed_by=signature)
        refused, summary = run_policy_gate_for_real(tree)
        assert refused.returncode != 0, (
            f"a receipt signed {signature!r} satisfied the policy gate: {refused.stdout}"
        )
        assert "`spread`" in summary, summary
        assert "never sign" in summary or "not Claude" in summary, summary


def test_the_policy_gate_refuses_an_allowlist_entry_this_change_adds(tmp_path: Path) -> None:
    """The diff half, against a real git repository.

    Base commit: an empty allowlist. Head: one market added, no receipt. The
    gate must exit non-zero, and the summary must say which market this change
    adds rather than only that something is unreceipted — the added market is
    the sentence a reviewer needs. Then the receipt is added to the same tree
    and the same comparison goes green, so the rule is "added without a
    receipt" and not "added at all".
    """
    root = tmp_path / "diffed"
    root.mkdir()
    tree = policy_checkout(root)
    write_policy(tree)
    base = commit_policy_tree(tree)

    write_policy(tree, "moneyline", mode="manual_only")
    refused, summary = run_policy_gate_for_real(tree, event="pull_request", base_sha=base)
    assert refused.returncode != 0, (
        f"an allowlist entry added with no receipt passed the policy gate: {refused.stdout}"
    )
    assert "ADDS `moneyline`" in summary, summary
    assert "this change is what adds it" in summary, summary

    write_receipt(tree, "moneyline")
    accepted, summary = run_policy_gate_for_real(tree, event="pull_request", base_sha=base)
    assert accepted.returncode == 0, (
        f"an addition backed by a receipt in the same tree was refused: "
        f"{accepted.stdout}\n{accepted.stderr}"
    )
    assert "ADDS `moneyline`" in summary, summary
    assert "r-moneyline.json" in summary, summary


def test_the_policy_gate_summary_says_which_markets_it_checked_and_what_it_found(
    tmp_path: Path,
) -> None:
    """The job summary has to be readable on its own.

    A reviewer sees the summary, not the log, and "Policy Gate: failed" is not
    a finding. Every allowlisted market must appear in it by name with its
    verdict, whichever way the run went — one market green and one red in the
    same run, and both named.
    """
    root = tmp_path / "mixed"
    root.mkdir()
    tree = policy_checkout(root)
    write_policy(tree, "spread", "total_points")
    write_receipt(tree, "spread")
    refused, summary = run_policy_gate_for_real(tree)
    assert refused.returncode != 0, refused.stdout
    assert "`spread`" in summary and "r-spread.json" in summary, summary
    assert "`total_points`" in summary and "lacks" in summary, summary
    assert POLICY_FILE_RELATIVE in summary and RECEIPTS_RELATIVE in summary, summary
    assert summary.strip(), "the policy gate wrote no job summary at all"
