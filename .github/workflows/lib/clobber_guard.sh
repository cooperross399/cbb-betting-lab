#!/usr/bin/env bash
#
# The publish-level clobber guard, extracted so it can be tested against a
# real git ref instead of asserted about as a string.
#
# WHY THIS FILE EXISTS AT ALL. The card-feed publish step runs under
# `if: always()`, because a run that dies before it publishes leaves no commit
# for the day and "no commit for today" has to keep meaning "the run did not
# finish". Last-write-wins plus `always()` is exactly how the EPL lab lost a
# good card: a late-firing backup trigger landed after the deadline, produced a
# blocked card, published last, and replaced the morning's real one. Defect 17
# in `docs/ported_defects.md`.
#
# WHY IT IS A FILE RATHER THAN TEN LINES OF YAML. Cooper's brief, verbatim:
# *"Verify this against a real git ref across every case; string assertions
# about shell logic in a workflow file are near-worthless."* A test that greps
# a workflow for the word `degraded` proves the word is present. It cannot
# prove the `if` reads the tip, cannot prove it compares the slot, and cannot
# prove which branch of it runs. So the logic lives here, the workflow calls
# it, and `tests/test_card_feed_publish_guard.py` builds a scratch repository
# with a real `card-feed` ref and runs this exact script across every case.
#
# THE RULE. Skip publishing when ALL THREE of these hold:
#
#   1. the tip is the same (date, card_slot) as this run,
#   2. the tip's `degraded` is the string "false",
#   3. this run's `degraded` is NOT the string "false".
#
# Anything else publishes. In particular:
#
#   * No tip at all publishes. A first-of-the-day failure must still write a
#     commit, or the reader cannot tell "the run did not finish" from "the run
#     stood down".
#   * A different day publishes.
#   * A different SLOT on the same day publishes. This is the college
#     basketball difference and it is not cosmetic: the slate spans twelve
#     hours, 45% of it has not tipped at 19:00 ET, and there are two card slots
#     a day (`docs/card_cadence.md`). A guard comparing the date alone would
#     read every evening refresh as a clobber of the morning card and stand
#     down for the 55% of the slate the evening slot exists to cover.
#   * A degraded tip publishes, whatever this run is. A degraded card is what
#     the backup trigger exists to replace.
#
# `degraded` is a STRING, and "unknown" counts as degraded. A run whose health
# step never executed cannot report "false", and treating an unreadable health
# as clean is how a broken run overwrites a good one while looking careful.
#
# INPUTS, all from the environment so the caller and the test drive it the same
# way:
#
#   PARENT      the resolved parent commit, empty when there is no card-feed
#               tip. Resolved by the caller, because the caller needs it for
#               `git commit-tree -p` anyway and two resolutions could disagree.
#   TIP_REF     the ref the tip was fetched into (default refs/card-feed-tip).
#   DAY         this run's league date, `TZ=America/New_York date +%F`.
#   CARD_SLOT   this run's slot: morning or evening.
#   DEGRADED    this run's degraded string: "true", "false" or "unknown".
#
# OUTPUT: exactly one word on stdout, `publish` or `skip`. The reason goes to
# stderr, where it lands in the job log without polluting the decision. Exit
# status is 0 for both, because "skipped on purpose" is not a failure and a
# non-zero exit would fail the step that is deliberately standing down.

set -eu

TIP_REF="${TIP_REF:-refs/card-feed-tip}"
PARENT="${PARENT:-}"
DAY="${DAY:-}"
CARD_SLOT="${CARD_SLOT:-}"
DEGRADED="${DEGRADED:-unknown}"

say() { printf '%s\n' "$*" >&2; }
publish() { say "$1"; printf 'publish\n'; exit 0; }
skip() { say "$1"; printf 'skip\n'; exit 0; }

# A first run, or a repository whose card-feed branch has been deleted. There
# is nothing to clobber, so the guard has no opinion. Gating the whole check on
# this is what keeps "no commit for today means the run did not finish" true on
# the one day it matters most: the first.
if [ -z "$PARENT" ]; then
  publish "No card-feed tip, so there is no card to clobber."
fi

STATUS="$(git show "$TIP_REF:latest_status.json" 2>/dev/null || printf '{}')"

# A five-line JSON reader rather than jq. Not to avoid a dependency — the
# runner has jq — but because this script is also run by a pytest that must
# work on any machine, and a guard that silently changes behaviour when jq is
# missing is a guard with two implementations.
#
# The first match only, and the name must be preceded by its own quote, so
# `"date"` cannot match inside `"slate_date"`.
_field() {
  printf '%s' "$STATUS" | tr '\n' ' ' \
    | grep -o "\"$1\"[[:space:]]*:[[:space:]]*\"[^\"]*\"" \
    | head -n 1 \
    | sed -e 's/^[^:]*:[[:space:]]*"//' -e 's/"$//'
}

TIP_DAY="$(_field date)"
TIP_SLOT="$(_field card_slot)"
TIP_DEGRADED="$(_field degraded)"
# An absent field is not a clean field. A tip written by an older run that did
# not stamp its slot reads as unknown, which fails the equality below and
# publishes — the safe direction, because publishing over an unreadable tip
# loses nothing that a reader could have used.
[ -n "$TIP_DEGRADED" ] || TIP_DEGRADED="unknown"

if [ "$TIP_DAY" != "$DAY" ]; then
  publish "The tip is for '$TIP_DAY' and this run is for '$DAY'."
fi

if [ "$TIP_SLOT" != "$CARD_SLOT" ]; then
  publish "The tip is slot '$TIP_SLOT' and this run is slot '$CARD_SLOT'. A later slot is a card for games the earlier slot could not reach, never a replacement for it."
fi

if [ "$TIP_DEGRADED" != "false" ]; then
  publish "The tip for $DAY/$CARD_SLOT is degraded ('$TIP_DEGRADED'), which is exactly what this run exists to replace."
fi

if [ "$DEGRADED" = "false" ]; then
  publish "This run is clean, so it may replace the clean tip for $DAY/$CARD_SLOT."
fi

skip "A clean card for $DAY/$CARD_SLOT is already on the feed and this run is degraded ('$DEGRADED'). Refusing to overwrite a good card with a bad one."
