# Related work, and what is actually new here

An earlier draft of this work claimed that "nothing in current practice reports it." That claim was
made without checking and it was wrong. This document is the check, written so the boundary between
established results and our contribution is explicit enough to argue with.

**Verification status.** Sources marked ✔ were retrieved and read during this literature pass. Those
marked ○ are cited from standard knowledge of the field and should be confirmed against the primary
text before the manuscript is submitted. No claim of novelty below rests on an ○ source alone.

---

## 1. Sports betting market efficiency and the closing line

✔ *Inefficient Forecasts at the Sportsbook: An Analysis of Real-Time Betting Line Movement*,
Management Science (2024) — line movement from open to close across four sportsbooks for 3,681 MLB
games.
✔ *Weak Form Efficiency in Sports Betting Markets* — 155,000+ contests, 16 seasons, major North
American sports.
✔ *Betting Markets and Market Efficiency: Evidence from College Football* — 11,000+ games, 1985–2003.

✔ Scavone, *Getting Precise About Closing Line Value*, Unabated (31 Jul 2026) — practitioner
treatment; notes that props have "very few market-making books" and "very few market signals", i.e.
that CLV is UNRELIABLE there. It does not address the close being ABSENT.

**What this literature establishes.** The closing line is the market's most informed price and is the
standard benchmark against which forecasting skill is measured. Whether it is fully efficient is
actively contested, and several papers find exploitable deviations.

**Where our work sits.** Every study we found operates on **dense game-level markets** — moneylines,
spreads, game totals — where a closing price exists for essentially every contest. In that setting the
question we ask cannot arise: the close is always there, so its *availability* is not a variable. Our
setting is player props, where a specific rung at a specific line is quoted only while a book chooses
to offer it. The relevant quantity is therefore not whether the close is efficient but whether it
**exists**, and that question appears to be unasked because the datasets these papers use are ones
where the answer is trivially yes.

This is a scope difference, not a disagreement. We take the closing line's status as a benchmark from
this literature and ask what happens when the benchmark is absent on a quarter of the prop sample.

---

## 2. Selection, reject inference, and missing data

○ Heckman, *Sample Selection Bias as a Specification Error*, Econometrica 47(1), 1979.
○ Little & Rubin, *Statistical Analysis with Missing Data* — the MCAR / MAR / MNAR taxonomy.
○ The credit-scoring reject-inference literature, where a lender observes repayment only for
applicants it approved.

✔ Kamat, *Outcome-Classified Precision Auditing of Filter Rules in Algorithmic DEX Trading:
Evidence from 2,400 Rejection Events*, arXiv:2607.02830 (July 2026) — audits a production filter
stack by following the market after each REJECTED event and classifying the outcome. The closest
recent instance we found of grading declined decisions in a live trading system; same design as our
frozen-at-entry declined positions, different domain, and no treatment of missing prices.

**This literature agrees with us, and that is the point.** Our population result — that a pooled
return figure changes sign because the recorded population changed definition partway through the
window — is a textbook selection effect. We do not claim to have discovered it. We claim it is still happening in production systems
that believe they have controlled for it, and we measure what it costs.

Two things we can add rather than restate:

1. **The counterfactual is observable in our setting, and is not in credit.** A lender cannot see
   whether a rejected applicant would have repaid, which is precisely why reject inference is a
   literature of *imputation methods*. A declined bet resolves anyway — the game is played, the
   player records the stat — so the outcome of the rejected population is directly observable if the
   position is frozen at entry. Sports betting is an unusually clean laboratory for the problem
   credit risk has to approximate. That framing is available to us and we should use it.
2. **The failure mode is architectural, not statistical.** Heckman corrections assume you have the
   declined population to correct *with*. The systems we examine had already deleted it. No estimator
   recovers a row that was never written down, which is why our first design rule is about storage
   and not about inference.

**Not novel, and we should say so plainly:** selection bias, MNAR, and reject inference. Overclaiming
here is the fastest way to lose a reviewer who knows the field, and the honest framing is stronger
anyway — we are supplying evidence that a known problem persists, with a measurement of its size.

---

## 3. Experiment quality monitoring — the closest prior work

This is where the sharpest boundary lies, so it is the part that was checked hardest.

✔ Fabijan et al., *Diagnosing Sample Ratio Mismatch in Online Controlled Experiments*, KDD 2019.
✔ *Ensure A/B Test Quality at Scale with Automated Randomization Validation and Sample Ratio
Mismatch Detection* (eBay), arXiv:2208.07766 — production randomization validation via **population
stability index (PSI)** plus sequential SRM detection.
○ Kohavi, Tang & Xu, *Trustworthy Online Controlled Experiments* (2020) — SRM as the canonical
trust check; A/A tests as a platform validation.
✔ US 12,147,397 B2, *Method and system for detecting data bucket inconsistencies for A/B
experimentation* (Yahoo Ad Tech; filed 2017, granted 2024) — detects units assigned to more than one
bucket by INTERSECTING the logged identifier sets of each bucket.
✔ Practitioner guidance on deterministic bucketing (e.g. hash of salt and a stable unit id) treats
"recompute the assignment if the log is lost" as a design property, which presumes the key is stable.

**What is established.** Sample ratio mismatch is the standard first-line indicator of a broken
experiment, and mature platforms automate it. The eBay paper is the state of the art we found for
industrial randomization validation.

**The gap, stated precisely.** SRM and PSI are **distributional** checks. They ask whether the arms
have the expected proportions and whether the assigned populations are statistically stable. They do
not ask whether a *given unit* would receive the same assignment if the assignment were derived
again.

Our failure passes both. The first version's arms were balanced 591 to 572 across nine days, so an
SRM test would have returned clean, and a PSI check would have found the populations stable, because
the defect was not in the ratio. Under the second version's exactly known formula, re-deriving every
stored arm gives a step: all 2,480 arms stamped from 5 September re-derive, and the 1,258 stamped
before match 50.6%, a coin flip, with nothing in the system recording what changed. Aggregate balance
was preserved while per-unit assignment became unverifiable.

**What is NOT ours.** Detecting a unit that sits in two arms is prior art: the Yahoo patent does it
by log intersection, and our `record_the_decision` detector is the same check (it finds our five
bets). Deterministic hashing on a stable key is standard practice.

**Our contribution here**, stated narrowly enough to defend: re-deriving each unit's assignment from
the row it is stored on, and comparing, is a different check from both SRM and overlap detection.
It is the one that exposes our failure. Overlap detection finds 5 of 1,158 bets in the first version
and none in the second; re-derivation under a known formula shows that every arm stamped before a
silent change on 5 September can no longer be verified from its row, which is what removes the
experiment's defence against silent re-rolling. We exhibit a production instance where the ratio
check and the overlap check both look nearly clean and the per-unit check does not. We found no
published source that runs this check; if a reviewer knows one, that narrows the contribution to the
measurement, and the paper survives that.

---

## 4. Data validation and silent failure in ML pipelines

✔ Sculley et al., *Hidden Technical Debt in Machine Learning Systems*, NeurIPS 2015 — boundary
erosion, entanglement, hidden feedback loops, undeclared consumers.
✔ Breck et al., *The ML Test Score* (2017) — a 28-point rubric across data, model, infrastructure and
monitoring.
✔ TensorFlow Data Validation and Amazon Deequ — declarative data-quality constraints on recurring
pipelines.
✔ *Data Smells: Categories, Causes and Consequences* (arXiv:2203.10384).

**What is established.** That silent data-quality failure is a first-class problem in production ML
is not in dispute — it is the explicit motivation for an entire tooling category. "Hidden feedback
loops" in Sculley et al. is a close conceptual relative of what we describe.

**The gap.** These systems validate **the data that arrives**, against constraints declared in
advance: schema conformance, range checks, null rates, distributional drift. Two of our three
failures are invisible to that design:

* A constraint cannot fire on rows that were never written. Our first design rule exists because the
  filter deleted its own evidence — there is no arriving record to validate.
* A null-rate constraint on the closing price would either fire constantly (it is legitimately absent)
  or be whitelisted, at which point *coverage conditional on the decision* — the quantity that
  actually matters — is invisible. In our HMDA run, an interest rate is null on 100% of denied
  applications, which is correct behaviour and would be whitelisted by any sane constraint set. The
  finding is not the null rate; it is that the null rate is 0% for one stratum and 100% for another,
  and that the strata are chosen by the system being evaluated.

So the contribution is not "data validation is needed" — that is settled — but that constraint-based
validation is the wrong shape for failures defined by *absence conditional on a decision*.

---

## 5. On how many domains to compare against

A note on scope discipline, because the temptation runs the other way.

**Demonstration generalises; analogy does not.** Running the detectors unmodified on real outside
datasets (HMDA, ClinicalTrials.gov) is evidence, and both are framed as validations on known cases:
decision-dependent absence exists there by design, so the detectors must fire, and they do. Listing
domains the argument merely *resembles* (insurance underwriting, revenue management, hiring) buys
nothing, because a reviewer correctly reads an undemonstrated analogy as an assertion.

There is a specific downside too. The broader the claim, the more the work reads as a restatement of
selection bias, which is textbook and nearly fifty years old. Breadth makes the contribution look
*less* novel, not more. The defensible position is a **narrow claim with wide evidence**: the
phenomenon is known, our measurement of its size and our detection method are not.

Recommended structure, at most three datasets, chosen so each exhibits a **different** rule failing:

| dataset | status | what it shows |
|---|---|---|
| betting book | done | all four rules violated; the failures and their cost |
| HMDA | done | rules 1 and 3 mandated by regulation; rule 4 fails structurally |
| ClinicalTrials.gov | done | rule 1 mandated (withdrawn trials retained); rule 4 fires on status |

Still open: a public dataset where **rule 3 fails independently**. The trial result rests on one
system's rows; its stored arms and per-row reproduction flags ship in the extract, so it is
checkable, but it is one instance. A public dataset exhibiting assignment or identity recomputation
drift would move it onto independently checkable ground.

---

## Summary of the claim

**Established, and cited as agreement:** selection bias and reject inference; MNAR missingness; the
closing line as a skill benchmark, and its unreliability in props; grading rejected decisions in a
production filter; silent data-quality failure as a production problem; SRM and bucket-overlap
detection as experiment trust checks.

**What we add:**

1. A measurement of how often the closing price is *absent rather than noisy* in thin markets, with
   the result that no polling rate recovers it — across 20,060 line-movement failures, zero occurred
   while the wagered rung was still quoted, and in 119,001 more the player had no market at all; and
   that the absence depends on the system's own decision within the same day.
2. A production instance where aggregate experiment balance held and overlap checks were nearly
   clean while no unit's assignment could be re-derived from its own row — a failure that
   ratio-based and overlap-based monitoring cannot detect.
3. Four design rules with open-source detectors, shown to fire on a second domain the authors have no
   connection to, and shown to come back clean exactly where federal regulation already mandates the
   rules.
