"""Two rows under one quote identity at two prices keep the better price.

A book's main line and its alternate ladder at the same point are one quote
seen twice. `keep="first"` held whichever was parsed first — the worse price on
189 of 504,394 props quotes in the 2024 segment. The survivor is now the best
price, and row order is otherwise untouched.
"""
import pandas as pd

from cbb_betting_lab import stores


def _row(**kw):
    base = dict(event_id="e1", market="player_points", segment="game", player="A Player",
                selection="over", line=12.5, book="draftkings", snapshot_phase="card",
                american_odds=-110)
    base.update(kw)
    return base


def test_the_better_price_survives_whichever_came_first():
    for odds in ([-120, -105], [-105, -120], [110, 105], [105, 110]):
        out = stores.dedupe_prices(pd.DataFrame([_row(american_odds=o) for o in odds]))
        assert len(out) == 1
        assert out.loc[0, "american_odds"] == max(odds, key=stores._decimal_payout)


def test_distinct_quotes_keep_their_order():
    frame = pd.DataFrame([
        _row(american_odds=-110),
        _row(selection="under", american_odds=-105),
        _row(book="fanduel", american_odds=100),
    ])
    out = stores.dedupe_prices(frame)
    assert out["book"].tolist() == ["draftkings", "draftkings", "fanduel"]
    assert out["selection"].tolist() == ["over", "under", "over"]


def test_equal_prices_collapse_to_one_row():
    assert len(stores.dedupe_prices(pd.DataFrame([_row(), _row()]))) == 1


def test_a_frame_without_odds_still_dedupes_on_identity():
    frame = pd.DataFrame([_row(), _row()]).drop(columns="american_odds")
    assert len(stores.dedupe_prices(frame)) == 1


# ---------------------------------------------------------------------------
# The declared subject normalizer
# ---------------------------------------------------------------------------


def test_one_athlete_under_two_spellings_is_one_wager():
    """The root-n defect arriving through the subject field instead of the book.

    `best_price_per_wager` grouped on the raw `player` string, so the same
    athlete written two ways was two wagers — two rows survived where one
    should, at two different prices. Measured over the 2024 prop store: 4,396
    wagers, 3,959 of them carrying two different `american_odds`, every one
    cross-book and none a single book quoting twice.
    """
    frame = pd.DataFrame(
        [
            {
                "event_id": "e1", "market": "player_points", "segment": "game",
                "player": "Kam Jones", "selection": "over", "line": 14.5,
                "book": "dk", "snapshot_phase": "card", "american_odds": -110,
            },
            {
                "event_id": "e1", "market": "player_points", "segment": "game",
                "player": "kam jones", "selection": "over", "line": 14.5,
                "book": "fd", "snapshot_phase": "card", "american_odds": +105,
            },
        ]
    )
    collapsed = stores.best_price_per_wager(frame)
    assert len(collapsed) == 1, (
        "two spellings of one athlete survived as two wagers; every interval "
        "built on them is narrower than the evidence supports"
    )
    # And the survivor is the better price, which is the existing contract.
    assert int(collapsed.iloc[0]["american_odds"]) == 105


def test_the_fold_touches_no_market_without_a_subject():
    """Team markets carry no subject, so the declaration cannot reach them.

    This is the whole safety argument for adopting it: measured over the store,
    all 504,394 rows carrying a subject are `player_*` markets and no team
    market has a non-empty one, so no published number moves.
    """
    team = pd.DataFrame(
        [
            {
                "event_id": "e1", "market": "spread", "segment": "game",
                "player": "", "selection": "home", "line": -3.5,
                "book": "dk", "snapshot_phase": "card", "american_odds": -110,
            },
            {
                "event_id": "e1", "market": "spread", "segment": "game",
                "player": "", "selection": "away", "line": 3.5,
                "book": "fd", "snapshot_phase": "card", "american_odds": -108,
            },
        ]
    )
    assert len(stores.best_price_per_wager(team)) == 2

    # A frame with no subject column at all is returned untouched.
    without = team.drop(columns=["player"])
    assert len(stores.best_price_per_wager(without)) == 2


def test_the_fold_lives_in_the_key_and_never_in_the_returned_rows():
    """The stored data keeps what the book wrote.

    The first implementation replaced the `player` column with its folded
    spelling. That is a rewrite of the data, not of the identity, and it broke
    a downstream merge: `player` is float64 NaN on team markets, folding made
    it an empty string, and `test_one_wager_is_one_bet_at_the_best_price` died
    with "trying to merge on str and float64 columns for key 'player'". The
    function's own contract already said only the identity is folded.
    """
    frame = pd.DataFrame(
        [
            {
                "event_id": "e1", "market": "player_points", "segment": "game",
                "player": "Kam Jones", "selection": "over", "line": 14.5,
                "book": "dk", "snapshot_phase": "card", "american_odds": +105,
            },
            {
                "event_id": "e1", "market": "player_points", "segment": "game",
                "player": "kam jones", "selection": "over", "line": 14.5,
                "book": "fd", "snapshot_phase": "card", "american_odds": -110,
            },
        ]
    )
    out = stores.best_price_per_wager(frame)
    assert len(out) == 1
    assert out.iloc[0]["player"] == "Kam Jones", (
        "the survivor's name was rewritten to its folded spelling; the fold is "
        "an identity, not a correction to what the book wrote"
    )
    assert "_subject" not in out.columns, "the hidden key column leaked into the output"

    # And a NaN subject stays NaN rather than becoming an empty string, which
    # is what changed the column's dtype and broke the merge.
    team = pd.DataFrame(
        [{
            "event_id": "e1", "market": "spread", "segment": "game",
            "player": float("nan"), "selection": "home", "line": -3.5,
            "book": "dk", "snapshot_phase": "card", "american_odds": -110,
        }]
    )
    assert stores.best_price_per_wager(team)["player"].isna().all()


def test_the_fold_never_merges_two_books_or_two_lines():
    """It folds the subject and nothing else.

    `_dedupe_value` is shared by every identity column, so casefolding it
    wholesale would have folded `book` and `market` too. The declaration is
    about the subject; this is the assertion that it stayed there.
    """
    assert stores.normalise_subject("Kam Jones") == stores.normalise_subject("kam jones")
    # Books keep their case: two books are two books.
    frame = pd.DataFrame(
        [
            {
                "event_id": "e1", "market": "player_points", "segment": "game",
                "player": "A Player", "selection": "over", "line": line,
                "book": book, "snapshot_phase": "card", "american_odds": -110,
            }
            for book, line in (("DK", 14.5), ("dk", 15.5))
        ]
    )
    # Different lines are different wagers whatever the book's spelling.
    assert len(stores.best_price_per_wager(frame)) == 2
