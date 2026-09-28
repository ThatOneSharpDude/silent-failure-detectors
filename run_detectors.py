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
    # Restricted to days on which BOTH strata were recorded: before that the store kept only taken
    # positions, so a spread computed across the boundary would partly measure the boundary.
    days_both = {r["day"] for r in props if r["acted"] == "0"} & {r["day"] for r in props if r["acted"] == "1"}
    props_both = [r for r in props if r["day"] in days_both]
    out.append(monitor_for_absence(props_both, defined_key="has_close", floor=0.95, stratum_key="acted"))

    # RULE 3: does one bet ever carry two stored arms? This is the trial that cannot be audited.
    # Keyed on the bet (date + canonical identity), not on the raw fields: a raw key without a date
    # "collides" whenever a player's line recurs on another day, which would inflate the alarm.
    trial = rows("trial_epoch1.csv")
    out.append(record_the_decision([(r["bet_token"], r["stored_arm"]) for r in trial]))

    # RULE 1: this table is the rule. 139,061 capture failures are RETAINED, each with the reason
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
