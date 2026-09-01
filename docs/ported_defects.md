# Every defect inherited from a sibling lab, and the test here that pins it

**This is the fourth lab.** The football lab's `CLAUDE.md` states the cost
plainly: these repositories share no code, the same defect classes appeared
independently in each, and six NHL fixes were hand-ported into football on
2026-08-31. A fourth lab means a fourth hand-port.

**The sibling labs are not touched.** Not to refactor, not to extract shared
code, not to fix a defect noticed there. That prohibition is absolute. They hold
measured numbers that cannot be rebought, and one of the entries below is a live
defect in a sibling that is recorded here and deliberately left alone.

The list is kept so the port is **auditable** rather than assumed. If it grows
long enough that extraction into a shared package is obviously worth it, the
arithmetic goes in the final report as a recommendation and nothing is acted on.

---

## Inherited and closed before they could happen here

| # | Defect | Came from | What it cost there | Test here |
|---:|:---|:---|:---|:---|
| 1 | **Deduping a price store on the whole row, timestamps included** | NHL | Every quote written twice. ROI unchanged, every interval **√2 too narrow**. Its first "clean" run reported 144,060 bets and nothing looked wrong. | `test_prices_dedupe_on_identity_not_the_row.py` — and `PRICE_IDENTITY` carries no timestamp, asserted as a property |
| 2 | **Counting every book's quote as an independent bet** | NHL | 2.83 quotes per selection, so intervals √2.83 too narrow. Per quote, its full store said all three team markets were **demonstrated losses**; per wager, all three span zero. | same file — `best_price_per_wager` collapses to one bet at the best price |
| 3 | **A headline that never read the sign** | NHL | `what_we_can_claim` announced *"at least one result survived the correction and then replicated"* on a market returning **−6.6%**. | `test_the_headline_reads_the_sign.py` — `RoiInterval.verdict()` returns `demonstrated deficit`, never `edge` |
| 4 | **UTC dates meeting league game dates in a join** | NHL | **69% of every bought price silently discarded**, and the survivors were systematically the afternoon games. | `test_slate_day_and_season_match_the_source.py` — checked against ESPN's own filed date over 6,318 games |
| 5 | **Two hand-built copies of a join key** (five-member bug family: provider names vs abbreviations, `home -1.5` vs `home_minus`, outcomes staged in the provider's vocabulary, a CSV round-trip turning an empty player into the string `"nan"`) | NHL | Weeks. Each failure was silent. | one `selection.selection_key`, called by both sides of every join; `season.clean_text` is the only reader of CSV-borne text |
| 6 | **Yes/no markets staged under two spellings** (the anytime-scorer bug) | NHL | One wager staked twice, published as two independent best bets at two prices, frozen into the ledger twice. | `selection.yes_no_selection` maps Yes→`over`, No→`under`; `double_double`, `triple_double` and `first_basket` all go through it |
| 7 | **A credit cap estimated from markets *asked* rather than markets *returned*** | NHL | A run capped at 200,000 spent **289,984**, while the code and its test both asserted the cap "cannot be breached". | `test_the_credit_cap_holds_the_worst_slate.py`; the cap is enforced against the measured running total from `x-requests-last` |
| 8 | **A cache filename tagged with a chunk's *length*** | football | Four ten-market chunks collided and three were lost. The NHL lab's `_markets_fingerprint` existed for exactly this and was not ported. | `odds_api.markets_fingerprint`, and the probe's own collision test |
| 9 | **A secrets guard exempting a *directory* rather than a *value*** | football | 32-hex event ids are the same shape as an API key. Exempting `data/raw/` would carve a hole exactly where provider data lands. | `test_no_secrets_committed.py::test_the_event_id_exemption_is_by_value_and_not_by_directory` |
| 10 | **A `\s*` in a credential-assignment regex** | football | `\s` crosses a newline, so `NAME=` on one line and any word on the next read as an assignment — which is what `.env.example` looks like, and the guard failed on a file whose values are all empty. | `ASSIGNMENT` uses `[ \t]*`, with the reason in the source |
| 11 | **A verdict decided by whichever season ran last** | football | +2.3% on 2025 shipped a policy; −1.8% on 2023 did not. Same policy, same script, opposite verdicts, and the card read whichever ran most recently. | `verdicts.read` returns `ships=False` unless `seasons_cleared ⊇ seasons_tested` |
| 12 | **A pre-registered hypothesis with no predicted direction** | football | Three of twelve slots spent on cuts that could only ever be exploratory. | `experiment_ledger.Hypothesis` raises `DirectionRequired` |
| 13 | **A walk-forward leak from a distribution loaded once outside the loop** | football | The per-play yardage distribution used to price 2023 had seen 2025. **Only the compound markets consumed it, which is precisely why the compound group looked good.** | `test_ratings_are_walk_forward.py` corrupts every later game and asserts the fit is byte-identical |
| 14 | **A segment that hardcoded the full-game tie rule** | football | A first half priced level at 0.4% when **7.4% of NFL first halves actually end level**. | segments carry `resolves_ties`; measured here at **3.54% of 90,766 college first halves**, with full games at **0.000%** |
| 15 | **A missing column read as a zero by `getattr(..., None)`** | football | A backtest reported zero bets, which read as "the model never disagrees enough". The price columns had never been built. | a missing settlement column raises; `stores.read_store(for_append=True)` raises rather than returning empty |
| 16 | **`git show X > file` creating a zero-byte file when the show fails** | football | pandas refuses a zero-byte CSV. It killed the first rehearsal on exactly the branch state the first real run would have had. | every restore is temp-then-move; every CSV read is defensive |
| 17 | **A publish step under `if: always()` clobbering a good card** | EPL | A late-firing trigger landed past the deadline and, firing last, replaced the day's card with a blocked one. | the publish-level clobber guard, verified against a **real git ref** across all six cases — string assertions about shell logic are near-worthless |
| 18 | **An unauthenticated fetch making a guard fail open** | football | On a private repo it read "no card-feed branch yet", the backup trigger never stood down, and every game day fetched the slate twice and posted the card twice. | the already-published guard authenticates, and a test asserts it can |
| 19 | **An `@mention` overriding an ignored repository subscription** | EPL | Emails continued after the subscription was set to ignored, because the card comment still mentioned him. Two changes are needed, not one. | the card comment mentions nobody, and a test asserts it |
| 20 | **A hardcoded fixture window** | EPL | Correct for one week. After that every provider price fell outside it, every market read `unavailable`, and **every card came back Blocked while the fetch, the mapping and the completeness checks all passed.** A green run with no card is the signature. | the slate is derived from the fixtures in hand, never written down |
| 21 | **Concluding a market "isn't offered" from one market key** | EPL | `total_2_5` was excluded for a season. The complete line was absent from the bulk `totals` market and present all along in `alternate_totals`. | every retention conclusion rolls up to the **market**, never the provider key |

---

## Found in a sibling during this build, recorded and deliberately not fixed there

### The football lab's forward-ledger interval is about ten times too narrow

`football-betting-lab/src/football_betting_lab/forward_evidence.py`,
`interval_by_game`. It computes

    variance = Σ(wᵢ² · s² / G) · G ;  standard_error = √(variance / G)

which is algebraically `s·√(Σwᵢ²)/√G`; with roughly equal clusters `Σwᵢ² ≈ 1/G`,
so it lands at **`s/G` where a cluster standard error is `s/√G`**.

**Reproduced independently before it was reported.** On 632 synthetic bets over
200 clusters: the ratio estimator gives 0.03694, a cluster bootstrap over whole
games gives 0.03683, and that formula gives **0.00356 — 10.3× too narrow.**

It is on the one report in that lab which grows all season, and whose own
docstring says *"a narrow interval is how 'no demonstrated edge' quietly becomes
a claim."* Its sibling function in the same repository — `props_backtest._interval`
— is the correct ratio estimator, so the two disagree by a factor of ten inside
one codebase.

**Not fixed there**, per Cooper's absolute instruction. Fixed here in
`stats.interval_by_cluster`, with the defective formula reproduced verbatim in
`tests/test_clustered_interval_is_not_too_narrow.py` so it cannot come back.

**Worth Cooper's attention**: the football lab's forward ledger begins
accumulating from 2026-09-09, and every interval it reports until this is fixed
will be about ten times too tight. It has not yet produced a published number,
so nothing measured is invalidated — but the first one it produces would be.

---

## Defects original to this lab, found by disbelieving a number

Not inherited, but recorded in the same place because the next lab will inherit
*them*.

| # | Defect | How it was found | Test |
|---:|:---|:---|:---|
| A | **A made free throw counted as a made field goal.** ESPN's play type is `MadeFreeThrow` — one word — so `str.contains("Free Throw")` matches **none** of 253,589 free-throw rows in a season. | The possession validation the brief demanded returned an obviously wrong number (estimator 138.9 against a count of 153.9). | `test_free_throws_are_not_baskets.py` |
| A′ | The same defect would have settled **`player_first_basket` on whoever made the game's first free throw** — a plausible name, a real player, a wrong bet, and nothing would have looked broken. | Only visible because the possession check failed loudly first. | same file |
| B | **A season labelled by its starting year.** hoopR labels a season by the year it **ends**; this lab briefly did the opposite, which would have made every `season == 2027` filter miss every `season == 2027` row. | Verified against the real parquet rather than assumed. | `test_slate_day_and_season_match_the_source.py` |
| C | **A six-hour "basketball day" boundary**, reasoned by analogy with hockey. Measured against ESPN's own filed date over 6,318 games: **0 disagreements at midnight, 1 at six hours.** No D-I game tips between midnight and 08:00 ET, so the boundary protected nothing and broke the one Hawai'i game. | Measured rather than argued. | same file, plus a test for the Hawai'i game specifically |
| D | **A gate test that banned a word instead of an assertion.** It failed on the note that says *"this is not a pass, an avoid or a no-value call"* — the required phrasing. | The test failed on correct code. | `test_gates_fail_closed.py` now strips negated clauses first |
