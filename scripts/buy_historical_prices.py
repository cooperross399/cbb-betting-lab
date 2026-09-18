#!/usr/bin/env python3
"""Buy historical prices, in the brief's priority order, under a hard cap.

    # Costs nothing, makes no request, needs no credential:
    PYTHONPATH=src python scripts/buy_historical_prices.py --waves core_team

    # Spends credits:
    PYTHONPATH=src python scripts/buy_historical_prices.py \
        --waves core_team --live --credit-cap 1200000

**Dry by default.** Without `--live` this builds the plan, prints what each
wave would cost and which provider keys are refused for falling before their
archive cut-off, and stops. It opens no socket, reads no credential and spends
nothing.

## Why waves, and why this order

The full catalogue costs 35,173,680 credits against a balance of 4,992,714 —
seven times everything the account will ever hold. So the purchase is
prioritised rather than complete, in the order the brief names: **core team
markets across every season first, then ladders, then props, then futures.**
`docs/credit_cost.md` has the arithmetic and the reasoning.

Each wave is bought by its own dispatch. That is deliberate: a wave is a
decision about spending a large fraction of a finite balance, and running four
of them from one invocation would make the third and fourth happen as a
side-effect of the first.

## The cap is checked against what was spent, not what was predicted

The NHL lab capped a run at 200,000 and it spent **289,984** — because the
estimate counted the market keys *asked for* while the provider bills per
market *returned*, and every alternate ladder bills on its own. Both the code
and its test asserted the cap "cannot be breached".

So the cap here is enforced against the **measured** running total read from
the `x-requests-last` response header, before every request. The estimate is
still printed, still pessimistic, and is never the gate.

A response the provider bills at **0** is charged 0, because that is what the
provider measured. Charging it the pessimistic bound — which this script did
until the `x-requests-last` parse was split into its three real cases — spends
a cap against money that was never spent, stops a run early, and then states
that phantom figure in the record and the report as what the run cost.

## The account's balance is a gate, not a print-out

The cap above is this run's own budget; the balance is what pays for it, and
they fail in opposite directions. A run that hits its cap leaves markets
UNBOUGHT. A run whose account empties mid-flight leaves markets UNANSWERED: the
provider stops returning quotes, those responses stage no rows, and the census
reason they land under is indistinguishable from the provider not retaining the
market. Publishing that is a statement about the archive assembled out of a
fact about our wallet.

So this script now does what the card has always done and it never did: it asks
the free `/v4/sports` endpoint what the balance is and **refuses to start** a
run whose cap the account cannot cover. Inside the run, `providers.historical`
re-reads the measured balance after every response and stops with
`QuotaExhausted` when it falls below a floor derived from the widest single
request the run can make. A run stopped that way is recorded and rendered as
**STOPPED ON QUOTA**, **this script exits 7**, every segment it never reached is
listed by name as unasked, and the census says in so many words that nothing in
it may be read as evidence about retention. Exit 7 rather than 0 because a
quota stop that leaves CI green is the same defect one layer up: the operator
reads a successful purchase and the banner stays inside an artifact.

**Exiting red had to be paid for in the workflow, and for one round it was
not.** This docstring said "every persistence step in the workflow is
`if: always()`, so the red step loses nothing that was bought", and that was
false about the one persistence step that matters most. `actions/cache`'s save
is not a step: it is a post-step the runner registers and then skips whenever
the job's conclusion is not success, and `if: always()` on the combined action
governs only the restore half. So a quota-stopped run turned the job red and
its bought responses never entered the `cbb-bought-<window>-` chain the next
dispatch restores from — every response it had already paid for would be bought
again at ten times the live rate. `historical-purchase.yml` now restores with
`actions/cache/restore` and saves with an explicit `actions/cache/save` step
carrying `if: always()`, placed immediately after Buy, so the two steps that
persist what was bought — the 90-day raw-response artifact and that cache save
— both really do run on a red job.

No quota number is ever assumed. The balance is read from the response in hand
and never carried forward from an earlier one, so a provider that reports a
balance once and then stops leaves the breaker BLIND rather than armed against
a stale figure — and the report says which of the three it was: watched
throughout, watched then blinded, or never able to watch at all. Only a run
watched throughout may have an absence in it described as a fact about the
archive.

## Exit codes

`0` bought what it planned to. `1` every requested wave is blocked. `2` no
countable events. `3` no credential. `4` the rebuild refused (a shrink, a
zero-row rebuild, or an unreadable store) and the existing store is untouched.
`5` the free pre-flight could not be read at all. `6` the pre-flight refused: the
account cannot cover this run's cap. `7` the run stopped on quota mid-flight.

## A partial buy is a sample, not a prefix

Events are bought in an order whose every prefix is spread across the season
and across conference tiers — `stratified_order()`. A buy that stops halfway
through must leave a *sample* of the season behind it, not its first half. Book
coverage differs by tier and by month, and a prefix-ordered partial buy would
measure the high-major November board and call it college basketball.

## Resuming costs nothing

Every response is cached raw under `data/raw/cbb/historical_<window>/`, keyed
by event and by a fingerprint of the market chunk. A re-run reads the cache and
re-requests only what is missing, so an interrupted purchase resumes rather
than restarts, and `--rebuild` re-derives the price store from the cache
without a single request.

`--rebuild` **builds beside the store and replaces it only once the result is
verified.** It used to delete the store first and stage into the empty path,
which disarmed the two guards standing over it: the anti-shrink refusal always
read a floor of zero, and a rebuild that staged nothing printed a warning and
exited 0 over a store that no longer existed. A shrink and a zero-row rebuild
are now refusals with a non-zero exit, and on every refusal the original store
is still on disk.

Three guards, and the two that have an opt-out have **one each**.
`--allow-shrink-reason "<why>"` permits a MEASURED shrink, where both counts are
known. `--allow-unreadable-store-reason "<why>"` permits a rebuild over a store
that cannot be counted at all, where no floor exists and so no shrink guard can
run. These shared one flag until this round, which meant a written reason about
fifteen duplicate rows also switched off the unreadable-store refusal and, with
it, the shrink comparison itself — one flag disarming two differently-named
guards. Both take a written reason rather than a bare flag; an empty reason is
not an override.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from cbb_betting_lab.competitions import CBB
from cbb_betting_lab.config import OUTPUTS_DIR, PROCESSED_DIR, RAW_DIR
from cbb_betting_lab.providers import historical as H
from cbb_betting_lab.providers.env_file import redact
from cbb_betting_lab.providers.odds_api import (
    PURCHASE_STARVATION,
    OddsApiProvider,
    ProviderError,
    sufficient_quota,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--waves",
        default="core_team",
        help="Comma-separated wave names, in order: "
        + ", ".join(w.name for w in H.WAVES),
    )
    parser.add_argument("--credit-cap", type=int, default=1_200_000)
    parser.add_argument("--chunk-size", type=int, default=8)
    parser.add_argument("--max-events-per-segment", type=int, default=0)
    parser.add_argument("--seed", type=int, default=20260901)
    parser.add_argument("--window", default="card", choices=sorted(H.WINDOWS))
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Re-derive the price store from the cached responses. No requests.",
    )
    parser.add_argument(
        "--allow-shrink-reason",
        default="",
        help=(
            "Override the rebuild's anti-shrink refusal, which compares a "
            "MEASURED rebuild against a MEASURED previous store. Takes a "
            "WRITTEN REASON rather than a bare flag, because the store is "
            "append-only, cannot be re-bought, and has silently shrunk once "
            "already: 2.9M rows to 2.3M. An empty reason is not an override. "
            "It does NOT override the unreadable-store refusal below."
        ),
    )
    parser.add_argument(
        "--allow-unreadable-store-reason",
        default="",
        help=(
            "Override the rebuild's refusal to replace a store it cannot READ. "
            "A separate reason from --allow-shrink-reason on purpose: an "
            "uncountable store leaves the anti-shrink guard with no floor, so "
            "this opt-out means NO floor runs at all, not that a known shrink "
            "was permitted. An empty reason is not an override."
        ),
    )
    parser.add_argument("--processed-dir", default=str(PROCESSED_DIR))
    parser.add_argument("--raw-dir", default=str(RAW_DIR))
    parser.add_argument("--output-dir", default=str(OUTPUTS_DIR))
    args = parser.parse_args(argv)

    window = H.WINDOWS[args.window]
    wave_names = tuple(w.strip() for w in args.waves.split(",") if w.strip())
    if "all" in wave_names:
        # Every wave. The rebuild passes this, because the store must derive
        # from EVERY wave's cached responses and not only this run's — a
        # rebuild scoped to one wave appended onto a stale restored store, and
        # the store shrank while the raw cache held everything (defect U).
        wave_names = tuple(w.name for w in H.WAVES)
    waves = [H.wave_for(name) for name in wave_names]

    blocked = [w for w in waves if not w.buyable]
    for wave in blocked:
        # Not a pass, an avoid, or a no-value call. A wave that cannot be
        # bought says why, in the report and here.
        print(f"::warning::Wave '{wave.name}' is not buyable: {wave.blocked_reason}")
    waves = [w for w in waves if w.buyable]
    if not waves:
        print("Every requested wave is blocked. Nothing to plan.")
        return 1

    seasons = sorted({s for wave in waves for s in wave.seasons})
    print(
        f"{CBB.title} — historical purchase\n"
        f"Waves: {', '.join(w.name for w in waves)}. Seasons: "
        f"{', '.join(str(s) for s in seasons)}. Window: {window.name} "
        f"(T-{window.minutes_before_tip}m)."
    )

    events_by_season, indexes, _ = H.load_events(
        seasons=seasons,
        processed_dir=Path(args.processed_dir),
        raw_dir=Path(args.raw_dir),
        window=window,
    )
    if not any(events_by_season.values()):
        print("::error::No countable events. Run build_datasets.py first.")
        return 2

    plan = H.build_plan(
        events_by_season,
        waves=[w.name for w in waves],
        window=window,
        seed=args.seed,
        max_events_per_segment=args.max_events_per_segment,
    )
    # Refuses a plan asking for a key before its archive cut-off. Asking for a
    # market that could not exist and recording the silence as absence is how a
    # lab concludes "not retained" about a market the provider never had.
    H.guard_cutoffs(plan)

    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cache_dir = H.cache_dir_for(CBB, Path(args.raw_dir), window)

    if args.rebuild:
        # BUILD BESIDE, VERIFY, THEN REPLACE — one segment at a time.
        #
        # The whole of that order lives in `H.rebuild_store`, and this branch
        # only prints. It used to unlink the target first and stage into the
        # empty path, which derived from the cache correctly and disarmed two
        # guards doing it: `stores.append`'s anti-shrink refusal always read a
        # zero floor, and a rebuild that staged nothing printed a warning and
        # returned 0 over a store it had already destroyed.
        #
        # A shrink and a zero-row rebuild are refusals with a non-zero exit
        # here, and on every refusal the original store is still on disk.
        def announce(segment, rows, reached, held) -> None:
            print(
                f"  {segment.wave}/{segment.season}: {rows:,} rows from "
                f"{reached:,} cached events -> rebuild holds {held:,}"
            )

        try:
            result = H.rebuild_store(
                plan=plan, cache_dir=cache_dir, indexes=indexes,
                processed_dir=Path(args.processed_dir), competition=CBB,
                chunk_size=args.chunk_size,
                allow_shrink_reason=args.allow_shrink_reason.strip(),
                allow_unreadable_store_reason=(
                    args.allow_unreadable_store_reason.strip()
                ),
                on_segment=announce,
            )
        except H.PurchaseError as exc:
            print(f"::error::{exc}")
            print(
                "The existing store was NOT touched. Nothing was requested and "
                "no credit was spent."
            )
            return 4
        previous = (
            f"{result.previous_rows:,}"
            if result.previous_rows is not None
            else "an unreadable number of"
        )
        print(
            f"Rebuilt {result.rows_staged:,} price rows from "
            f"{result.events_reached:,} cached events over "
            f"{result.segments_rebuilt} segment(s). {result.target.name} now "
            f"holds {result.rows_held:,} rows, replacing {previous} rows. "
            "No request was made and no credit was spent."
        )
        if result.shrink_allowed_because:
            print(
                "::warning::The anti-shrink refusal was overridden by an "
                f"explicit operator reason: {result.shrink_allowed_because}"
            )
        if result.unreadable_store_allowed_because:
            # Louder than the shrink override, because it is a bigger claim: a
            # shrink override permits a known loss, this one permits an
            # UNKNOWN one. `previous_rows` is None here and no floor ran.
            print(
                "::warning::The previous store could not be read, so NO "
                "anti-shrink floor ran on this rebuild and the number of rows "
                "replaced is unknown. Overridden by an explicit operator "
                f"reason: {result.unreadable_store_allowed_because}"
            )
        if result.census:
            print("\nWhat did not become a row:")
            for reason, count in sorted(result.census.items(), key=lambda kv: -kv[1]):
                print(f"  {count:>9,}  {reason}")
        return 0

    if not args.live:
        record = H.dry_run_record(
            competition=CBB, plan=plan, credit_cap=args.credit_cap,
            chunk_size=args.chunk_size, regions=str(plan.segments[0].regions if plan.segments else 2),
            sport_key=CBB.provider_sport_key,
            population_by_season=events_by_season, generated_at=generated_at,
        )
        H.write_record(record, H.record_path(CBB, Path(args.output_dir)))
        print(H.render(record))
        print(
            "\nDry run. Nothing was requested, no credential was read, "
            "and no credit was spent"
        )
        return 0

    if not os.environ.get("CBB_ODDS_API_KEY"):
        print("::error::CBB_ODDS_API_KEY is not set. Nothing was requested.")
        return 3

    provider = OddsApiProvider(CBB)

    # THE PRE-FLIGHT THIS SCRIPT DID NOT HAVE.
    #
    # `sufficient_quota` has existed for as long as the card has, and only the
    # card called it. This script — the one that spends by far the most, at ten
    # times the live rate — started every run without asking what the balance
    # was. Starting short is not a cheaper run: once the account empties the
    # provider stops returning quotes, and a response with no quotes in it is
    # indistinguishable in the census from a market the archive never retained.
    # That publishes a fact about our wallet as a fact about the provider.
    #
    # `/v4/sports` is free, so this costs nothing to ask. An unreadable answer
    # does NOT block the run — the guard exists to catch a known shortfall, not
    # to make an unreadable response fatal — and the in-run circuit-breaker in
    # `H.buy` still watches the measured balance after every response.
    try:
        headers = provider.quota()
    except ProviderError as exc:
        print(redact(f"::error::{exc}"), file=sys.stderr)
        print("::error::Refusing to start. Nothing was requested.")
        return 5
    # THE REASON IS THIS SCRIPT'S, NOT THE CARD'S. `sufficient_quota` used
    # to carry the card's sentence about frozen early tips and a biased night
    # written into the ledger; this script writes no ledger and buys past
    # seasons in an order whose every prefix is already a sample, so that
    # reason describes nothing that happens here.
    enough, note = sufficient_quota(
        headers, int(args.credit_cap), why=PURCHASE_STARVATION
    )
    print(note)
    if not enough:
        print(
            "::error::Refusing to start a purchase the account cannot pay for. "
            "Nothing was requested and nothing was written.",
            file=sys.stderr,
        )
        return 6

    record = H.buy(
        plan=plan, provider=provider, indexes=indexes,
        credit_cap=args.credit_cap, cache_dir=cache_dir, competition=CBB,
        chunk_size=args.chunk_size, generated_at=generated_at,
        population_by_season=events_by_season,
    )
    H.write_record(record, H.record_path(CBB, Path(args.output_dir)))
    H.write_report(record, H.report_path(CBB, Path(args.output_dir)))
    print(H.render(record))

    # A QUOTA STOP IS A RED STEP, NOT A GREEN ONE.
    #
    # `H.buy` swallows `QuotaExhausted` internally so that everything bought
    # before the stop is still recorded and rendered — which is right — and the
    # only trace afterwards is `record['stopped_on_quota']`, inside a file
    # nobody opens while the job is green. Returning 0 here meant that the one
    # failure this module's whole census discipline exists to prevent was the
    # one failure CI never showed: the workflow's Buy step passed, the store
    # was rebuilt from a truncated cache, and the operator read a successful
    # purchase with the STOPPED ON QUOTA banner hidden in an artifact. A
    # rebuild that refuses to overwrite a store exits 4 and turns the job red;
    # this is strictly worse than that and exited 0.
    #
    # WHAT A RED JOB COSTS, MEASURED RATHER THAN ASSERTED. This comment used
    # to read "every persistence step in the workflow is `if: always()`, so a
    # non-zero exit here loses nothing that was bought" — written as a
    # guarantee with nothing enforcing it, and false about the resume cache:
    # `actions/cache`'s save is a POST-step gated on the job succeeding, not an
    # `if:` step, so a red job silently dropped this run's responses out of the
    # `cbb-bought-<window>-` chain and the next dispatch re-bought them.
    # `historical-purchase.yml` now carries a separate `actions/cache/save`
    # step with `if: always()` right after Buy, alongside the 90-day artifact
    # upload, and `tests/test_workflows.py::
    # test_the_bought_responses_reach_the_resume_cache_on_a_red_job` fails if
    # either goes away. With both in place a non-zero exit here loses nothing
    # that was bought.
    if record.get("stopped_on_quota"):
        print(
            "::error::STOPPED ON QUOTA. The account\u2019s measured balance fell "
            "below this run\u2019s floor and the run stopped rather than "
            "continuing to ask questions the provider would no longer answer. "
            "This is NOT the ordinary partial buy: every segment after the stop "
            "is UNASKED, and nothing in this run\u2019s census may be read as "
            "evidence about what the archive retains. Top the balance up and "
            "re-run: everything this run bought was saved to the resume cache "
            "and uploaded as an artifact by steps that run whatever this exit "
            "code is, so nothing already cached is bought twice.",
            file=sys.stderr,
        )
        return 7
    return 0


if __name__ == "__main__":
    sys.exit(main())
