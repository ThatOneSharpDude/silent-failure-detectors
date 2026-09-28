# Silent failure in self-evaluating systems

**Fox Camann** · University of Denver · quantitative finance
Companion code and data for an MIT Sloan Sports Analytics Conference submission.

A system that grades itself using data it produced will fail in ways its own output cannot show.
This repository is the record of such failures on a live sports betting book, every figure in the
paper regenerated from the shipped data, and four detectors that would have caught them, run
unmodified on federal mortgage data and clinical trial registration as well.

The claim is not that a model beat a market. Neither return figure here is distinguishable from
zero. The claim is about **measurement**: each failure below left every dashboard green, and two of
them made the system look *better* the worse they got.

---

## The finding, and three failures

**The metric is undefined, not merely noisy.**
Closing-line value exists only where a closing price was captured: 75.1% of prop positions, and only
58.7% of the positions actually taken. The missing rows are not random. A position is hardest to
price at the close precisely when the market has moved away from it, so the average is taken over
the easy cases and reported as the average.

The obvious response is to poll faster. It does not work, and the data says so: across 139,061
logged capture failures, the exact rung we had taken was still quoted in **zero** of them, and of
20,060 line-movement failures only 66 (0.33%) had two-sided rungs on both sides to interpolate
between. The price is not being missed. It has stopped existing.

Three failures sit on top of that, each of which left every dashboard green:

**1. A population boundary sets the sign.**
For its first 12 pricing days the store recorded only the positions the system took; declined
decisions start on day 12. Pooled over the whole window, return on the positions acted on reads
**+2.19%**. Restricted to the days on which both populations were recorded, the same figure reads
**-0.94%**. Nothing in any aggregate reports that its population changed definition partway through,
and the sign of the headline depends on it. Declined positions return **-2.24%**; clustered by day it
is the only figure whose interval excludes zero (acted [-7.19, +5.71], declined [-3.82, -0.65]).
None of this is offered as evidence of edge.

This result corrects an earlier version of the paper, which reported the same +2.19% / -2.24% pair
as "population choice flips the sign" without noticing that the pooled window crossed the boundary.

**2. A filter that could never pass.**
For 16 slate days, a category's minimum-edge bar sat above the largest edge the model is allowed to
emit. Every one of 914 positions in what the system itself rated its best-measured segment was priced
and declined; 181 sat pinned at the cap. Nothing errored. The rows were *demoted* rather than
deleted, which is the only reason this can be counted at all.

**3. A randomised trial that cannot be audited.**
For nine days a trial on the selection gate assigned 1,163 positions to a bet arm or a hold arm (591
and 572) with a deterministic coin: a hash of the position's identity and a fixed salt, so the
assignment could never be silently re-rolled. The hash was taken over raw row fields rather than the
canonical identity, and raw fields are spelled differently by different writers. Five bets sit in
both arms. More damaging, re-hashing each frozen row reproduces its stored arm only **47-49%** of the
time across every key construction we could reconstruct, which is the rate of a fresh coin. The arms
were stamped on the rows, but no row can confirm its own assignment, so determinism, the property
that made the trial evidence rather than an observational split, cannot be verified from its output.

`data/trial_epoch1.csv` carries the stored arm and one reproduces-or-not flag per key construction,
so the range is checkable. The exact original construction was not recorded; that is part of the
finding.

---

## Reproduce it

```bash
python reproduce.py        # every printed figure, regenerated from data/
python run_detectors.py    # the four detectors, pointed at the same data
```

No network, no dependencies, no arguments. Python 3.8+.

`reproduce.py` prints each value beside the value in the paper, compared at zero tolerance, and
marks any disagreement `MISMATCH`. It currently reports zero. If it ever reports one, **the paper is
wrong, not the data**. That is the point of shipping it this way. An earlier freeze of this paper
re-read the live store and drifted: late settlements kept landing on rows dated before the cutoff,
and the headline ROI moved from +1.60% to +0.40% at an unchanged cutoff while every check stayed
green. The extract here is the record; the store is never read again.

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

## The same detectors on clinical trial registration

A second outside domain, sharing the structure and nothing else. Every trial on ClinicalTrials.gov is
registered before its outcome is known, so the registry is a record of decisions proposed, not of
results obtained: the reject-inference design this betting store had to be rebuilt to get.

```bash
py datasets/clinicaltrials/clinicaltrials.py   # reads the shipped sample; --refresh re-pulls it
```

The sample is the 40,000 most recent completed, terminated, withdrawn or suspended studies returned by
the public API v2, cached so it does not move. Results are posted for **24.3% of 26,859 completed
interventional trials**, and for **0 of 1,445 withdrawn** ones. Who ran the trial predicts whether an
outcome exists at all: 52.4% for federal sponsors, 38.7% industry, 17.7% other, 3.5% other
government.

Stated as the script states it: four predictions were recorded before the first query returned and
three held. The miss matters. Terminated trials post results *more* often than completed ones (39.3%),
so absence here is not simply conditional on a bad ending. The withdrawn figure was found after
scoring, not predicted, and a trial that never enrolled can have no outcome by construction. That is
the point rather than a flaw: the registry keeps the withdrawn trial, which is the only reason its
absence can be counted. The betting store originally kept only what it acted on.

---

## What is in `data/`, and what is deliberately not

Shipped: day index, sport, whether the row is a player prop, whether the system acted, whether a
close existed, whether the row was graded; per-day staked/returned totals; capture-failure reasons
with the rung counts available at the time; salted identity token pairs; the best-segment rows with
their tier and cap flags; the trial's stored arms with reproduction flags; the hypothesis registry
reduced to sequence, kind and decision.

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

The trial result is the paper's least independently checkable claim, because its assignment log did
not survive. The Chadwick Bureau register — a free third-party crosswalk between the player IDs
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

**What this does not do.** It does not measure the trial's own drift and is not offered as if it did.
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

One operator, one pipeline, 72 pricing days (positions dated on or before 20 September 2026). The
instrumentation postdates the system, so the window is what could be measured honestly, not the
system's full history. The window holds three regimes, measured rather than assumed: days 0-11
recorded only positions taken; from day 12 the full candidate slate was frozen at roughly 25 acted
positions a day; from late August the gates admitted 3-6 a day while frozen volume nearly doubled.
Result 1 is the first boundary; figures that pool the other two are labelled as pooled. The hypothesis registry began mid-window, so it counts the search from that point on. The
acted-on ROI interval crosses zero under a day-clustered bootstrap; no ROI figure here is evidence
of edge, and the paper does not offer one as such. The detectors catch these failure shapes; they do
not repair the underlying data, and a metric that was never defined cannot be recovered after the
fact.

---

MIT licensed. Questions, corrections and replication attempts are all welcome — open an issue.
