#!/usr/bin/env python3
"""Report the provider quota remaining, without spending any of it.

The `/v4/sports` listing is documented as costing nothing and returns the
`x-requests-remaining` and `x-requests-used` headers, so this is the cheapest
possible way to answer "how much is left".

    PYTHONPATH=src python scripts/check_provider_quota.py

It also answers a question this lab does not otherwise know: **when the monthly
quota resets.** The reset shows up as `x-requests-used` falling, and watching
for that costs nothing. Until it is observed, any purchase needing most of a
month is planned as though the reset were the least convenient day it could be.

With `--list-sports` it also prints every basketball sport key the provider
serves, which is how the futures keys reach the registry as evidence rather
than as a guess.

Prints the numbers and nothing about the credential beyond whether one is
present.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone

from cbb_betting_lab.competitions import DEFAULT_COMPETITION_KEY, competition_for
from cbb_betting_lab.config import OUTPUTS_DIR
from cbb_betting_lab.providers.env_file import load_provider_env, redact
from cbb_betting_lab.providers.odds_api import OddsApiProvider, ProviderError


HISTORY_FILENAME = "quota_history.json"
SPORTS_FILENAME = "provider_sports.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--competition", default=DEFAULT_COMPETITION_KEY)
    parser.add_argument(
        "--fail-under",
        type=int,
        default=0,
        help="Exit non-zero when fewer than this many credits remain.",
    )
    parser.add_argument(
        "--list-sports",
        action="store_true",
        help="Also record every sport key the provider serves. Still free.",
    )
    args = parser.parse_args(argv)

    load_provider_env()
    provider = OddsApiProvider(competition_for(args.competition))
    try:
        headers = provider.quota()
    except ProviderError as exc:
        print(redact(f"Could not reach the provider: {exc}"), file=sys.stderr)
        return 2

    remaining = str(headers.get("x-requests-remaining", "")).strip()
    used = str(headers.get("x-requests-used", "")).strip()
    now = datetime.now(timezone.utc).isoformat()
    print(
        f"Quota: {remaining or 'unknown'} remaining, {used or 'unknown'} used. "
        "This check itself is documented as free."
    )

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    if args.list_sports:
        try:
            sports = provider.list_sports()
        except ProviderError as exc:
            print(redact(f"Could not list sports: {exc}"), file=sys.stderr)
            sports = []
        basketball = [
            s
            for s in sports
            if "basketball" in str(s.get("key", "")).lower()
            or "basketball" in str(s.get("group", "")).lower()
        ]
        print(f"\n{len(sports)} sport keys served; {len(basketball)} are basketball:")
        for s in sorted(basketball, key=lambda x: str(x.get("key", ""))):
            print(
                f"  {s.get('key','')}  |  {s.get('title','')}  |  "
                f"active={s.get('active')}  outrights={s.get('has_outrights')}"
            )
        (OUTPUTS_DIR / SPORTS_FILENAME).write_text(
            json.dumps({"fetched_at": now, "sports": sports}, indent=2) + "\n",
            encoding="utf-8",
        )

    # Append to a history file so the reset day becomes observable rather than
    # assumed. A fall in `used` between two readings is the reset, and knowing
    # the day turns a purchase that spans two months from a guess into a plan.
    path = OUTPUTS_DIR / HISTORY_FILENAME
    history: list[dict] = []
    if path.is_file():
        try:
            history = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            history = []
    if history and used.isdigit():
        previous = history[-1].get("used")
        if isinstance(previous, int) and int(used) < previous:
            print(
                f"::notice::The quota reset between {history[-1]['at']} and "
                f"{now}: used fell from {previous} to {used}."
            )
    history.append(
        {
            "at": now,
            "remaining": int(remaining) if remaining.isdigit() else None,
            "used": int(used) if used.isdigit() else None,
        }
    )
    path.write_text(json.dumps(history[-200:], indent=2) + "\n", encoding="utf-8")

    if args.fail_under and remaining.isdigit() and int(remaining) < args.fail_under:
        print(
            f"::error::Only {remaining} credits remain, below the "
            f"{args.fail_under} this run wanted. Nothing was bought.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
