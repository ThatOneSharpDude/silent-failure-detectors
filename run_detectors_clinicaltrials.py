"""run_detectors_clinicaltrials.py -- the four detectors, unmodified, on clinical trial registration.

    py run_detectors_clinicaltrials.py      # offline; reads the shipped sample

WHY THIS FILE EXISTS. The abstract says the detectors recover decision-dependent absence in 40,000
registered clinical trials. An earlier version of this repository computed those figures with
hand-written arithmetic in `datasets/clinicaltrials/clinicaltrials.py` and never called a detector,
so "run unmodified" was not true for this domain. This runs the same detector modules, with no
changes, on interventional trials:

  * RULE 2 assert_nonzero       the sample is not silently empty
  * RULE 4 monitor_for_absence  are posted results present, and does presence depend on how the
                                trial ended? The stratum is the trial's final status, which is a
                                decision (complete it, stop it, withdraw it) taken before results
  * RULE 1 demote_never_delete  the registry KEEPS withdrawn and terminated trials, each carrying
                                the status that explains its missing outcome -- the retention that
                                makes the gap measurable at all

A KNOWN CASE, AND THAT IS THE POINT. A trial withdrawn before enrolment cannot have results, so this
is a validation: the detector must fire where absence is known to depend on the decision, and it
does. It is not offered as a discovery about clinical research.

Exits 1 because an ALARM fires, as `run_detectors.py` does. Check the printed findings, not the exit
code: a crash also exits 1.
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "datasets", "clinicaltrials"))

from detectors import (assert_nonzero, demote_never_delete, monitor_for_absence,  # noqa: E402
                       run_all)


def findings(rows):
    interv = [{"status": r["status"], "has_results": int(bool(r["has_results"]))}
              for r in rows if r.get("study_type") == "INTERVENTIONAL"]
    return [
        assert_nonzero({"trials_sampled": len(rows), "interventional": len(interv)}),
        monitor_for_absence(interv, defined_key="has_results", floor=0.95, stratum_key="status"),
        demote_never_delete(interv, reason_key="status"),
    ]


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    import clinicaltrials as ct
    rows = ct.load()
    print("=" * 92)
    print("  THE DETECTORS, UNMODIFIED, ON CLINICAL TRIAL REGISTRATION  (%d studies)" % len(rows))
    print("=" * 92)
    return run_all(findings(rows))


if __name__ == "__main__":
    raise SystemExit(main())
