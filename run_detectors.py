"""run_detectors.py -- point all four detectors at the shipped extract. No network, no arguments.

    python run_detectors.py

Three of the four fire. That is the intended output, not a broken run: this data is the record of a
system that violated these rules, which is why the rules exist. Exit code is 1 when any detector
reports ALARM, so the same command works as a CI gate on a system that has since been fixed.
"""
from __future__ import annotations

import csv
import os
import sys

from detectors import (Finding, assert_nonzero, demote_never_delete, monitor_for_absence,
                       record_the_decision, run_all)

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def rows(name):
    with open(os.path.join(D, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def main():
    pos, cf, idf, pnl = (rows("positions.csv"), rows("capture_failures.csv"),
                         rows("identity_drift.csv"), rows("daily_pnl.csv"))
    props = [r for r in pos if r["is_prop"] == "1"]
    out = []

    # RULE 2 first: every later finding is computed over these tables, so a silently empty one
    # would make the rest of this report a set of confident statements about nothing.
    out.append(assert_nonzero({"positions": len(pos), "capture_failures": len(cf),
                               "identity_drift": len(idf), "daily_pnl": len(pnl)}))

    # RULE 4: coverage of the closing price, stratified by whether the system acted. If the two
    # strata disagree, the missingness is related to the decision and the subset is not random.
    out.append(monitor_for_absence(props, defined_key="has_close", floor=0.95, stratum_key="acted"))

    # RULE 3: does one raw key ever resolve to two ids? This is the A/B that was not an A/B.
    out.append(record_the_decision([(r["raw_field_token"], r["canonical_token"]) for r in idf]))

    # RULE 1: this table is the rule. 64,249 capture failures are RETAINED, each with the reason
    # it failed, instead of being dropped as "no close available" -- which is the only reason the
    # zero in the paper is knowable at all. Passing entered=len(cf) here would be circular (it
    # would check the table against itself), so what is checked is the reason distribution: if one
    # code swallowed nearly everything it would be a delete wearing a label.
    out.append(demote_never_delete(cf, reason_key="why"))

    print()
    code = run_all(out)
    print("""
  READING THIS. The alarms are the paper's three results, reproduced by the detectors that would
  have caught them. The design rules each one encodes are in the module docstrings; the failures
  they describe were found on a live book, not constructed for this repo.""")
    return code


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
