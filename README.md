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

## The same detectors on federal mortgage data

Every result above comes from one operator's own pipeline, which makes *"you found three bugs in
your own system"* a fair objection. So the detectors are also run, unmodified, against the **HMDA
Loan Application Register** — mortgage applications collected under federal mandate from thousands
of institutions with no connection to this work.

```bash
py datasets/hmda/fetch_hmda.py   # once, needs network (~17MB)
py run_detectors_hmda.py         # offline thereafter
```

Delaware 2023: 44,128 applications, of which 21,889 (49.6%) were originated. The rest is the
population the lenders did not write.

**An interest rate is recorded on 96.3% of originated loans and 0.0% of denied ones.** Coverage
differs across decision strata by 99.7 percentage points. This is not a data-quality defect to be
cleaned — the counterfactual rate does not exist, and the reporting standard concedes as much by
defining the field as not applicable unless the loan was originated. It is the same shape as a
closing price that stops existing once the market moves away from the rung you took.

The more useful result is what comes back **clean**. Rule 1 passes because HMDA *requires* a denied
application to be retained with the reason it was denied — which is the only reason the coverage
figure above is computable. Rule 3 is satisfied structurally, because the decision is a stored field
rather than something a reader re-derives, so it is not run at all: a check that cannot fail is not
evidence. The betting system here violated both rules and could not measure itself as a result.

Federal mortgage reporting converged on both rules without reference to this work. That is the
argument that these are properties of self-evaluating systems rather than lessons from one pipeline.

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

## A third domain: what a name fails to identify

Result 2 is the paper's least independently checkable claim, because the 51.7% figure lives in a
private store. The Chadwick Bureau register — a free third-party crosswalk between the player IDs
used by MLBAM, Retrosheet, Baseball-Reference and FanGraphs — lets anyone measure one component of
the same mechanism. It exists *because* name-keying does not work, which makes its existence part
of the evidence.

```bash
py datasets/chadwick/fetch_chadwick.py   # once, needs network (~65MB)
py run_detectors_identity.py             # offline thereafter
```

| population | ambiguous names | people affected |
|---|---|---|
| whole register (518,743 people) | 9.19% | **23.61%** |
| anyone with an MLBAM id | 6.32% | 15.29% |
| MLB, played 2015 or later | 0.55% | **1.19%** |

Among current players the collision rate is about 1% — real (`jose fernandez` x4, `luis garcia` x3,
`will smith` x2) but not a crisis. The larger surface is normalisation: **10.3% of active players
carry a diacritic**, and a collision needs two people to exist while a normalisation difference needs
only one writer to fold accents and another not to. This project shipped that exact bug — a
transaction check missed *Márquez* because it compared against *marquez*.

**What this does not do.** It does not corroborate the 51.7% figure and is not offered as if it did.
That failure was driven mainly by *other* mutable fields in the identity key — a market string
respelled between writers, a line arriving as `None` on one path and `0.0` on another — with name
handling only one contributor. This measures one component, on a different population, and it comes
out an order of magnitude smaller. The claim it supports is that the mechanism is real and publicly
measurable, not that its size here validates ours.

---

## Related work

[`RELATED_WORK.md`](RELATED_WORK.md) positions this against four literatures — betting market
efficiency, selection and reject inference, A/B experiment quality monitoring, and ML data
validation — and marks which sources were read during the pass versus cited from background. It is
explicit about what is *not* novel here: selection bias, MNAR and reject inference are established,
and this work supplies evidence that a known problem persists rather than claiming to have found it.

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
