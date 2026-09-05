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

**The gate rules** apply to the two workflows whose green tick is a claim
about this repository — `tests.yml`, which is the required status check named
`Tests`, and `ledger-guard.yml` — and they are the reason branch protection
would mean anything. Until this file nothing pinned that check: the job could
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

CBB is private. There is no branch protection on this repository today, so
nothing on GitHub's side gates a merge on `Tests` — the sibling labs are
public and protected, and there the context this file pins is the one
protection requires. Here, pinning it is what makes protection meaningful the
day it is switched on, and what makes a red `Tests` a fact rather than a
suggestion until then.
"""

from __future__ import annotations

import re
import shlex
import shutil
import subprocess
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

#: The workflows whose run blocks are executed under stubs and held to the
#: gate rules. The other five are operational: they hold credentials on
#: purpose, keep going on purpose (`continue-on-error` on a report step so the
#: evidence still uploads), and are covered by the corpus rules only.
GATE_WORKFLOWS = frozenset({TESTS_WORKFLOW, LEDGER_WORKFLOW})

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


def run_block_under_stubs(
    block: str, failing: set[str] | None, sandbox: Path, *, present_dirs: tuple[str, ...] = ()
) -> BlockRun:
    """Execute one run block with every command replaced by a stub.

    `failing` is the set of command words whose stub returns 1; `None` means
    all of them; an empty set means none. Nothing real executes: PATH is an
    empty directory inside the sandbox, the working directory is the sandbox,
    and the environment is built from scratch. `present_dirs` are created in
    the sandbox first, for rules that need a directory to exist.

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
    marker = sandbox / "preamble_completed"
    for log in (failure_log, any_failure_log, unmodelled_log):
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
    )
    parsed = subprocess.run([HARNESS_SHELL, "-n"], input=preamble, capture_output=True, text=True)
    if parsed.returncode != 0:
        raise RuntimeError(f"the stub preamble does not parse: {parsed.stderr}")

    script = sandbox / "run_block.sh"
    script.write_text(preamble + block + "\n:\n", encoding="utf-8")
    environment = {
        "PATH": str(empty_path_dir),
        "LC_ALL": "C",
        "HOME": str(sandbox),
        "GITHUB_WORKSPACE": str(sandbox),
        "RUNNER_TEMP": str(sandbox),
    }
    for name in RUNNER_FILE_VARIABLES:
        target = sandbox / name.lower()
        target.touch()
        environment[name] = str(target)
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
    return BlockRun(
        completed.returncode,
        failure_log.read_text(encoding="utf-8").split(),
        unmodelled,
        completed.stderr,
        any_failure_log.read_text(encoding="utf-8").split(),
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
    found = {"pytest": 0, "gate": 0, "checkout": 0, "python-version": 0, "upload": 0, "required-check": 0}
    for path in paths:
        document = load(path)
        found["pytest"] += sum(1 for _ in pytest_lines(document))
        found["gate"] += sum(1 for _ in gate_lines(document))
        found["checkout"] += sum(1 for _ in steps_using(document, "actions/checkout"))
        found["upload"] += sum(1 for _ in steps_using(document, "actions/upload-artifact"))
        found["python-version"] += sum(1 for m in mappings(document) if "python-version" in m)
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
    tests.yml, it is not delegated, it carries no `if:`, no
    `continue-on-error`, no `strategy:` (a matrix renames the context), runs
    on a Linux runner (the executed rules model bash), and its pytest and
    gate steps carry no `shell:`, no `working-directory:`, no condition but
    `always()`. The workflow fires on pull_request with no branches or paths
    filter, and on push.
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
}


# --------------------------------------------------------------------------
# The rules applied to the real workflows.
# --------------------------------------------------------------------------


def test_the_workflow_directory_is_not_empty() -> None:
    assert WORKFLOWS_DIR.is_dir(), f"{WORKFLOWS_DIR} does not exist"
    assert WORKFLOW_FILES, f"No workflow files under {WORKFLOWS_DIR}; every rule here would pass by having nothing to check"


def test_both_gate_workflows_exist() -> None:
    """Absence is never a pass. A deleted tests.yml is not a workflow that
    passes every rule; it is no required check at all."""
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
        run: |
          set -euo pipefail
          python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"
      - name: Gate on the results
        if: always()
        run: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"
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
PYTHON_VERSION_LINE = "python-version: '3.12'"
PERSIST_LINE = "          persist-credentials: false\n"
COMPILE_LINE = "python -m compileall -q -f src scripts"
COMPILE_GUARD = '            [ -d "$d" ] || { echo "::error::$d is missing"; exit 1; }\n'
SUITE_LINE = 'python -m pytest -q -rs --junit-xml="$RUNNER_TEMP/junit.xml"'
SUITE_STEP_HEADER = "      - name: Run the suite\n"
GATE_STEP = (
    "      - name: Gate on the results\n"
    "        if: always()\n"
    '        run: python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"\n'
)
GATE_COMMAND = 'python scripts/check_test_results.py "$RUNNER_TEMP/junit.xml"'
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
    "the_credential_is_never_spelled_onto_a_command_line": "test_a_dereferenced_credential_is_rejected",
    "credit_spending_workflows_carry_no_cron": "test_a_cron_on_a_spending_workflow_is_rejected",
    "every_script_a_workflow_runs_exists": "test_a_missing_script_is_rejected",
    "python_version_is_pinned_to_an_exact_minor": "test_an_unpinned_python_version_is_rejected",
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
        ("step", mutate(SUITE_STEP_HEADER, SUITE_STEP_HEADER + "        env:\n          PYTEST_ADDOPTS: '-x'\n")),
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
    assert missing_subjects([workflow(tmp_path, hollow)]) == ["checkout", "gate", "pytest", "python-version", "required-check", "upload"]
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
