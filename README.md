# Silent failure in self-evaluating systems

**Fox Camann** · University of Denver · quantitative finance
Companion code and data for an MIT Sloan Sports Analytics Conference submission.

A system that grades itself using data it produced can fail in ways its own output cannot show. This
repository is the record of such failures on a live sports betting book, every figure in the paper
regenerated from the shipped data, and four detectors that catch them, validated unmodified on federal
mortgage data and clinical trial registration.

The claim is not that a model beat a market. No return figure here is offered as evidence of edge.
The claim is about **measurement**: each failure below left every dashboard green.

---

## In plain English

**The one idea:** a system can only grade what it recorded. What it failed to record decides what its
numbers say, and it will not tell you. In every case below, no number looked *bad*. The numbers looked
fine because the damage was in rows that were missing, dropped, or never written down. A dashboard can
show you a wrong number. It cannot show you a number that is not there.

**The betting version.** Bettors judge skill with closing line value (CLV): did you get a better price
than the market's final one? On player props, books often pull a line before the game starts, so there
is no closing price and no CLV for that bet. Here, 25% of prop positions had no closing price. And
whether a bet has one depends on what the system decided: on 39 of 60 days, bets it took were better
covered than bets it passed on. So CLV is always computed on a slice of the book the system itself
picked. The failure log shows why prices go missing: in 86% of failed captures the player's whole
market was gone, and in the rest the line had moved off the number that was bet.

**Three more things that broke without anyone noticing:**

1. **Two numbers measured over different windows.** For its first 12 days the system only saved the
   bets it placed, not the ones it passed on. Its placed bets return +2.19% over all 72 days, but
   -0.94% over the 60 days where the passed-on bets exist to compare against. Compare "placed vs
   passed on" without noticing, and you are comparing two different stretches of time.
2. **A filter that could never pass.** A filter demanded a bigger edge than the model is allowed to
   output. For 16 days, 0 of 914 positions in the segment the system measured best could become a
   bet. No error. It was an off switch that looked like a filter.
3. **A fair coin nobody can check.** A randomised test flipped a reproducible coin for each bet so
   nobody could quietly re-flip it until they liked the answer. Using the coin's exact, known formula,
   every assignment made from 5 September on can be re-checked: all 2,480 match. The 1,258 made before
   5 September match 50.6% of the time, a coin flip. Something changed that day, and nothing in the
   system records what. The test's own record cannot prove the test was fair.

**Validated elsewhere.** Run unchanged on public data where the answer is known in advance, the same
detectors find it: an interest rate on 96.3% of approved mortgages and 0% of denied ones, and posted
results for 24.3% of completed clinical trials and 0% of withdrawn ones. Those regulators *require*
the rejected cases to be kept, which is the only reason the gap is visible at all.

### What this fixes in your own model

It does not make anyone's model more accurate. It stops you believing wrong things about your model,
and in betting a wrong belief costs money: you size up on an edge that is not there, or kill one that
is. It fixes the scoreboard, not the prediction.

| If you... | You probably think... | Ask instead... |
|---|---|---|
| track CLV | "my average CLV is positive, so I have an edge" | what share of my bets even have a close, and does that depend on which bets I took? |
| use a filter to pick bets | "the bets I placed won, so the filter works" | did I save the bets I passed on, over the same days, and how did they do? |
| run an A/B test | "the arms are 50/50, so the test is fair" | can I re-derive each unit's assignment from its record and get the same answer? |
| have thresholds or caps | "no errors, so everything ran" | can this threshold actually be reached? |

The same hole opens in any front office grading itself: a draft model evaluated only on the players it
drafted cannot see the ones it passed on, who still play.

### The four questions, and the detector for each

1. **What did I delete?** Keep and flag anything you filter out, or it can never be counted.
   (`demote_never_delete`)
2. **Is it actually empty?** A file that loads can still hold nothing. Check the counts.
   (`assert_nonzero`)
3. **Did I record the decision, or am I recomputing it?** Recomputing later audits today's code, not
   what happened. (`record_the_decision`)
4. **What is my number not seeing, and does that depend on my own choices?** Put coverage next to
   every average. (`monitor_for_absence`)

Most model builders spend their effort making predictions better. The cheaper, bigger win is often
making sure you can trust the scoreboard.

---

## The finding, and three failures

**The metric is often undefined, and whether it is defined depends on the decision.**
Closing-line value exists only where a closing price was captured: 75.1% of prop positions. On the 60
days where both taken and declined positions were recorded, taken positions were better covered on 39
days (two-sided sign test p = 0.03). The *size* of the difference depends on how days are weighted, so
it is not the headline:

| comparison, taken minus declined, share missing a close | gap (pp) |
|---|---|
| within day, weighted by taken count (day-clustered 95% CI [-15.6, -1.4]) | -8.7 |
| within day, days weighted equally | -1.4 |
| within day, weighted by declined count | +1.6 |
| pooled over the same 60 days | +8.0 |

Pooled comparisons are confounded by time: taken positions cluster early in the window, when capture
was worse, and declined volume grew late, when it was better. Line type (main versus alternate line)
is an unexamined confounder. What survives every cut is that coverage is not independent of the
decision, so CLV describes a subset the system selected. In missing-data terms this establishes that
the missingness is not completely at random; it does not establish that it depends on the outcome.

**What the failure log shows.** 139,061 capture attempts failed. These are *polling events*, not
positions: one position can fail many times, and 90% are WNBA. In 119,001 (86%) the player had no
market at all. In the other 20,060 the line had moved off the wagered rung, and only 66 (0.33%) left a
two-sided quote on each side of it to interpolate between. A failure is logged only when the wagered
rung is absent, so "the rung was never still quoted" is true by definition and is not claimed as a
finding. Nor is it claimed that no price could be modelled: 98.6% of line-moved failures had at least
one two-sided rung, from which a distributional model could estimate one. The claim is narrower: the
close for the rung actually bet was not observable at the source.

Three failures sit on top of that, each of which left every dashboard green:

**1. Unmatched windows.**
For its first 12 pricing days the store recorded only the positions the system took; declined
decisions start on day 12. Return on positions acted on reads **+2.19%** over all 72 days and
**-0.94%** over the 60 days on which declined positions exist. The acted population never changed
definition; the *window* did, because days 0-11 ran +13.3% on 208 units. An earlier version of this
paper compared +2.19% (acted, 72 days) with -2.24% (declined, 60 days) and read the difference as
"population choice flips the sign". On matched days the gap is +1.3pp and neither the acted figure
(day-clustered CI [-7.19, +5.71]) nor the gap is distinguishable from zero. The failure is that
nothing in either aggregate says which days it covers.

**2. A filter that could never pass.**
For 16 slate days, a category's minimum-edge bar sat above the largest edge the model is allowed to
emit. From the system's configuration at the time (edges are withheld from this extract, so this is
not checkable from `data/`): the best reachable score was 13.0 x 0.90 x 0.981 = 11.48 against a bar of
12.0. Every one of 914 positions in the segment the system measured best (its "best-measured cells",
not best-performing) was priced and declined; 181 sat pinned at the cap. Nothing errored. The rows
were *demoted* rather than deleted, which is the only reason this can be counted at all.

**3. A trial that cannot be audited.**
A randomised trial on the selection gate assigned positions to a bet arm or a hold arm with a
deterministic coin, a hash of the position's identity and a fixed salt, so that any assignment could
be audited by re-deriving it and none could be silently re-rolled. The arms were stamped on the rows.

*The known-formula result.* From 24 August the coin used a formula recorded exactly in the code.
Re-deriving every stored arm with it gives a clean step (`data/trial_epoch2_control.csv`): all 2,480
arms stamped from 5 September re-derive (100%), and the 1,258 stamped before match 50.6% of the time,
a coin flip. The code history shows no change to how arms were stamped that week, and the identity
function kept changing after 5 September without breaking later rows. Whatever changed, nothing in
the system records it, and every assignment before that date can no longer be verified from its row.
That is Rule 3 in one picture: re-deriving a decision audits today's inputs, not what happened.

*The first version.* From 13 to 24 August the coin was keyed on raw row fields, whose exact
construction was not recorded. Over those nine days it assigned 1,163 positions (591 to the bet arm,
572 to hold) and put five bets in both arms (`data/trial_epoch1.csv`). Re-deriving those arms under
four plausible reconstructions matches 47-49%; because the original construction is unknown, that
only shows that no reconstruction re-derives them, and it is not offered as evidence of mechanism.
The five double-assigned bets are the direct evidence.

---

## Reproduce it

```bash
python reproduce.py                    # every printed figure, regenerated from data/
python run_detectors.py                # the four detectors, pointed at the same data
python run_detectors_clinicaltrials.py # the same detectors, unmodified, on clinical trials
```

No network, no dependencies, no arguments. Python 3.8+.

`reproduce.py` prints each value beside the value in the paper, compared at zero tolerance, and marks
any disagreement `MISMATCH`. It currently reports zero. If it ever reports one, **the paper is wrong,
not the data**. An earlier freeze of this paper re-read the live store and drifted: late settlements
kept landing on rows dated before the cutoff, and a headline ROI moved from +1.60% to +0.40% at an
unchanged cutoff while every check stayed green. The extract here is the record; the store is never
read again.

The detector scripts exit 1 when an ALARM fires, which is expected here. A crash also exits 1, so read
the printed findings, not the exit code.

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
betting.

---

## Validation on public data where the answer is known

Every result above comes from one operator's own pipeline, which makes *"you found bugs in your own
system"* a fair objection. So the detectors are run, unmodified, on two public registries where
decision-dependent absence is known to exist **by design**. These are validations, not discoveries:
the detectors must fire where the answer is known, and come back clean where the rules are already
mandated.

**HMDA mortgage applications.** Delaware 2023 only: 44,128 applications, 21,889 originated.

```bash
py datasets/hmda/fetch_hmda.py   # once, needs network (~17MB); the extract also ships
py run_detectors_hmda.py
```

An interest rate is recorded on **96.3% of originated loans and 0.0% of denied ones**; the reporting
standard defines the field as not applicable unless the loan was originated. Rule 1 comes back clean
because HMDA *requires* a denied application to be retained with its denial reason, which is the only
reason the coverage figure is computable.

**ClinicalTrials.gov registrations.** The 40,000 most recent completed, terminated, withdrawn or
suspended studies from the public API v2, cached so the sample does not move.

```bash
py run_detectors_clinicaltrials.py   # offline; reads the shipped sample
```

`monitor_for_absence`, unmodified, fires on the 31,631 interventional trials: posted results cover
24.6% of them, and coverage depends on the trial's final status (24.3% of 26,859 completed, 0 of 1,445
withdrawn; a trial withdrawn before enrolment has no outcome by construction). Rule 1 comes back clean
because the registry keeps withdrawn and terminated trials with their status. The separate script
`datasets/clinicaltrials/clinicaltrials.py` also scores four predictions recorded before the first
query returned: three held, and the miss is reported (terminated trials post results *more* often than
completed ones, 39.3%).

In both registries the regulator mandates keeping the declined case, and that retention is what makes
the gap measurable. The betting store originally kept only what it acted on.

---

## What is in `data/`, and what is deliberately not

Shipped: day index, sport, whether the row is a player prop, whether the system acted, whether a close
existed, whether the row was graded; per-day staked/returned totals at a flat 1 unit per paper
position (not a real-money ledger); capture-failure reasons with the rung counts available at the
time; salted identity token pairs; the best-segment rows with their tier and cap flags; the trial's
stored arms with reproduction flags for both versions; the hypothesis registry reduced to sequence,
kind and decision.

`identity_drift.csv` flags as `rct_epoch1` every player row dated inside the first trial's window
(1,553 rows); `trial_epoch1.csv` holds only the 1,163 of those that fell inside the trial's
claimed-edge band and received an arm.

Withheld: every player, game, team, book, market description, line, price, model probability and
edge. Day indices are **relative**: day 0 is the first day of the window and nothing joins to a
calendar or an odds feed. Identity tokens are salted with a salt generated at export and discarded, so
they cannot be inverted by anyone, including me.

`data/CUTOFF.txt` carries the freeze date, window length and the moment the store was read.

---

## A related public measurement: what a name fails to identify

The Chadwick Bureau register, a free crosswalk between the player IDs used by MLBAM, Retrosheet,
Baseball-Reference and FanGraphs, lets anyone measure one component of identity instability. It
exists *because* name-keying does not work.

```bash
py datasets/chadwick/fetch_chadwick.py   # once, needs network (~65MB)
py run_detectors_identity.py             # offline thereafter
```

| population | ambiguous names | people affected |
|---|---|---|
| whole register (518,743 people) | 9.19% | **23.61%** |
| anyone with an MLBAM id | 6.32% | 15.29% |
| MLB, played 2015 or later | 0.55% | **1.19%** |

Among current players the collision rate is about 1%. The larger surface is normalisation: **10.3% of
active players carry a diacritic**, and a normalisation difference needs only one writer to fold
accents and another not to. This project shipped that exact bug. This does not measure the trial's
own failure and is not offered as if it did.

---

## Related work

[`RELATED_WORK.md`](RELATED_WORK.md) positions this against betting market efficiency, selection and
reject inference, experiment quality monitoring (including prior art on detecting units in two arms),
and ML data validation. It is explicit about what is *not* novel: selection bias, missing-data theory,
reject inference, decision logging and overlap detection are established. This work supplies
measurement that a known problem is live and silent in production, and detectors that catch it.

---

## Limitations, stated plainly

One operator, one pipeline, 72 pricing days (positions dated on or before 20 September 2026). The
instrumentation postdates the system, so the window is what could be measured honestly, not the
system's full history. The window holds three regimes: days 0-11 recorded only positions taken; from
day 12 the full candidate slate was frozen at roughly 25 acted positions a day; from late August the
gates admitted 3-6 a day while frozen volume nearly doubled. The size of the coverage gap depends on
weighting and line type is unexamined. Failure counts are polling events, 90% WNBA. The cause of the
5 September step is not recorded. No ROI figure here is evidence of edge. The detectors catch these
failure shapes; they do not repair the underlying data.

---

MIT licensed. Questions, corrections and replication attempts are all welcome; open an issue.
