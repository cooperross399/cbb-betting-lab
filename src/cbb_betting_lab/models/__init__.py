"""The model: a distribution over scores, and the ratings that parameterise it.

Two modules, and the split between them is deliberate.

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
"""
