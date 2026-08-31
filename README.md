# Silent failure in self-evaluating systems

**Fox Camann** · University of Denver · quantitative finance
Companion code and data for an MIT Sloan Sports Analytics Conference submission.

A system that grades itself using data it produced will fail in ways its own output cannot show.
This repository is the record of three such failures on a live sports betting book, every figure in
the paper regenerated from the shipped data, and four detectors that would have caught them.

The claim is not that a model beat a market. Neither return figure here is distinguishable from
zero. The claim is about **measurement**: each failure below left every dashboard green, and two of
them made the system look *better* the worse they got.

---

## The three failures

**1. A metric that was undefined, not merely noisy.**
Closing-line value was computed over the rows where a closing price existed — 62.7% of prop
positions, and only 53.8% of the positions actually taken. The missing rows are not random. A
position is hardest to price at the close precisely when the market has moved away from it, so the
average was taken over the easy cases and reported as the average.

The obvious response is to poll faster. It does not work, and the data says so: across 13,047
capture failures, the exact rung we had taken was still quoted in **zero** of them, and only 0.41%
had two-sided rungs on both sides to interpolate between. The price is not being missed. It has
stopped existing.

**2. A randomised trial that was never randomised.**
Arms looked balanced — 353 against 350 across nine days. The assignment was not stored; it was
recomputed on read from an identity key built out of raw fields, and those fields drift. One
position could draw two different assignments on two different reads. **51.7% of 9,074 assignments
were irreproducible.** Every balance check the experiment passed was a check on the recomputation.

**3. Population choice determines the sign.**
Return on the positions the system acted on: **+1.60%**. Return on all positions it evaluated,
including the 87% it declined: **−1.40%**. Same model, same window, same prices. The gate is not a
neutral filter over a fixed population — it *creates* the population, so it cannot be evaluated on
it. Both intervals cross zero once clustered by day; the finding is the sign change, not either
number.

---

## Reproduce it

```bash
python reproduce.py        # every printed figure, regenerated from data/
python run_detectors.py    # the four detectors, pointed at the same data
```

No network, no dependencies, no arguments. Python 3.8+.

`reproduce.py` prints each value beside the value in the paper and marks any disagreement
`MISMATCH`. It currently reports zero. If it ever reports one, **the paper is wrong, not the data** —
that is the point of shipping it this way. The abstract's figures were first computed by hand and had
silently drifted within six days, because settlement keeps landing on rows dated before the cutoff. A
paper about measurement drifting from its own data is not one you want to submit with drift in it.

`run_detectors.py` exits non-zero, and is supposed to. This data is the record of a system that broke
these rules.

---

## The four rules

Each detector is one design rule, with the failure that taught it in the module docstring.

| module | rule |
|---|---|
| `detectors/demote_never_delete.py` | A row you drop cannot later be counted as missing. Mark it, never remove it. |
| `detectors/assert_nonzero.py` | A file that parses is not a file with data. Anything emitting a count asserts the count. |
| `detectors/record_the_decision.py` | Store the decision taken, not the inputs you could re-derive it from. |
| `detectors/monitor_for_absence.py` | Report coverage beside every aggregate. An aggregate without it is not a result. |

They take plain row dicts, not this project's schema, because none of these failures are specific to
betting — they belong to any pipeline judged on data it generated itself.

---

## What is in `data/`, and what is deliberately not

Shipped: day index, sport, market class, whether the system acted, whether a close existed, whether
the row was graded; per-day staked/returned totals; capture-failure reasons with the rung counts
available at the time; salted identity token pairs.

Withheld: every player, game, team, book, market description, line, price, model probability and
edge. Day indices are **relative** — day 0 is the first day of the window and nothing joins to a
calendar or an odds feed. Bet outcomes appear only as per-day aggregates, because a day's net is not
tradeable and an individual position would be. Identity tokens are salted with a salt generated at
export and discarded, so they cannot be inverted by anyone, including me.

The paper makes no claim about predictive edge, so none of the withheld fields are needed to check
any result in it. Every number in the abstract regenerates from what is here.

`data/CUTOFF.txt` carries the freeze date and window length. Rows are frozen at entry, including the
declined ones, which is what makes result 3 measurable at all.

---

## Limitations, stated plainly

The instrumentation postdates the system by roughly six weeks, so the window is what could be
measured honestly, not the system's full history. Both ROI intervals cross zero under a
day-clustered bootstrap; neither is evidence of edge, and the paper does not offer them as such. The
detectors catch these failure shapes — they do not repair the underlying data, and a metric that was
never defined cannot be recovered after the fact. Result 2's irreproducibility rate is measured on
A/B assignments in the private store; the extract here carries the identity-drift pairs that caused
it, which is a related but not identical figure, and `run_detectors.py` labels it as its own number.

---

MIT licensed. Questions, corrections and replication attempts are all welcome — open an issue.
