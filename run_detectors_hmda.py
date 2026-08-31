"""run_detectors_hmda.py -- the same four detectors, on federal mortgage data instead of our own.

    py datasets/hmda/fetch_hmda.py     # once, needs network
    py run_detectors_hmda.py           # offline thereafter

WHAT THIS IS FOR. Every result in this repository otherwise comes from one operator's own pipeline,
which makes "you found three bugs in your own system" a fair objection. HMDA answers it. The register
is collected under federal mandate by thousands of institutions with no connection to this work, and
the detectors are not modified between the two runs -- only the columns they are pointed at.

The outcome is not "HMDA is broken". Two of the four rules are things the reporting standard already
REQUIRES, which is the stronger result: the rules were not invented here, a regulated domain
converged on them independently. The one rule HMDA does not impose is the one where analyses built on
it still go wrong.
"""
from __future__ import annotations

import collections
import csv
import os
import sys

from detectors import (assert_nonzero, demote_never_delete, monitor_for_absence,
                       record_the_decision, run_all)

EXTRACT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "datasets", "hmda", "hmda_extract.csv")


def main():
    if not os.path.exists(EXTRACT):
        print("no extract yet -- run:  py datasets/hmda/fetch_hmda.py")
        return 2
    with open(EXTRACT, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    by_action = collections.Counter(r["action"] for r in rows)
    denied = [r for r in rows if r["action"] == "denied"]
    orig = [r for r in rows if r["action"] == "originated"]

    print()
    print("  %s %s -- %d applications" % (rows[0]["state"], rows[0]["year"], len(rows)))
    for k, v in by_action.most_common():
        print("      %-32s %6d  %5.1f%%" % (k, v, 100.0 * v / len(rows)))
    print("  the lender's book is 'originated'; everything else is the population it did not write")

    out = [assert_nonzero({"hmda_applications": len(rows), "denied": len(denied),
                           "originated": len(orig)})]

    # RULE 4, the live finding. An interest rate exists only where a loan was written. For a denied
    # application there is no rate to be missing -- the value is undefined, not absent. So any
    # statement of the form "the average rate was X" is a statement about approved applicants only,
    # and approval is not random with respect to the applicant.
    out.append(monitor_for_absence(rows, defined_key="has_interest_rate", floor=0.95,
                                   stratum_key="action"))

    # RULE 1, satisfied by regulation. A denied application is retained WITH the reason it was
    # denied, rather than dropped from the register. This is exactly demote-never-delete, and it is
    # the only reason the coverage figure above is computable at all.
    out.append(demote_never_delete(denied, reason_key="denial_reason"))

    # RULE 3 is NOT run here, deliberately. HMDA stores the decision as a field (action_taken)
    # instead of re-deriving it, so there is no second derivation to disagree with the first and
    # nothing for the detector to compare. Feeding it each row's decision paired against itself
    # would return CLEAN without having tested anything -- a check that cannot fail is not
    # evidence, and reporting one next to three real results would inflate all four. The absence
    # of this line is the finding: the rule is satisfied structurally, upstream of measurement.

    code = run_all(out)

    ir = sum(1 for r in orig if r["has_interest_rate"] == "1")
    print("""
  WHAT THE ALARM MEANS HERE. An interest rate is present on %.1f%% of originated loans and on
  %.1f%% of denied ones. That is not a data-quality defect to be cleaned; it is the counterfactual
  being unavailable. It is the same shape as a closing price that stops existing once the market
  moves away from the rung you took -- and here the reporting standard itself concedes the value
  does not exist, by defining the field as not applicable unless the loan was originated.

  WHAT THE CLEAN RESULTS MEAN. Rule 1 passes because HMDA MANDATES it: a denial is retained with
  the reason it was denied, which is the only reason the coverage figure above can be computed.
  Rule 3 is satisfied structurally -- the decision is a stored field rather than something a reader
  re-derives -- so it is not run at all above, because a check that cannot fail is not evidence.
  The betting system in this repository violated both rules and could not measure itself as a
  result. Federal mortgage reporting arrived at both without reference to this work, which is the
  argument that they are properties of self-evaluating systems and not lessons from one pipeline.""" % (
        100.0 * ir / max(len(orig), 1),
        100.0 * sum(1 for r in denied if r["has_interest_rate"] == "1") / max(len(denied), 1)))
    return code


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
