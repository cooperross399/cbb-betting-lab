"""The model: a distribution over scores, and the ratings that parameterise it.

Four modules today, and the split between them is deliberate.

`distributions` turns *three numbers* — each side's expected points per
possession and the game's expected possessions — into a **joint distribution
over (home score, away score)**. It knows nothing about teams, seasons or
dates. Every market on the game is then a different question asked of the same
object, which is the property that makes a −3 and a −3.5 and a +7.5 on the same
game price consistently instead of nearly consistently.

`ratings` produces those three numbers, walk-forward, and — just as
importantly — reports **how much of them is still the preseason prior**, and
refuses to produce them at all when the schedule graph has not yet connected
the two teams to each other by anything but that prior.

The seam between the two is `ratings.Matchup`, which carries the three numbers,
the venue state, the prior weight and the priceable flag. It carries the prior
weight because a November price and a February price look identical on a card
and are not the same claim, and the only place that distinction can survive is
beside the number itself.

`player_shapes` reads the frozen player constants and refuses to hand back any
whose fit window touches the season being priced **or the declared validation
season** — a guard that excluded only the priced season would bless fitting on
the holdout.

`slate` is the single construction site: one slate day's model, both halves,
built from frames cut strictly before the day. It exists because a prop must be
representable on a game whose spread is not priceable, and nesting the player
projections inside `Matchup` — which may not exist for a game — made that
sentence unsayable. `matchups` and `players` are independently keyed by
`event_id`, and neither's absence implies the other's.
"""
