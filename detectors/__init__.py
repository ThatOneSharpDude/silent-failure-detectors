"""Four detectors for failures that a system's own output cannot reveal.

Each one encodes a design rule that was learned by violating it on a live book. They are written
against generic row dicts, not against this project's schema, because the failures are not specific
to betting -- they are specific to any pipeline that is judged using data it produced itself.

    demote_never_delete   a row that is dropped cannot be counted as missing
    assert_nonzero        an artifact that parses is not an artifact with data
    record_the_decision   a decision recomputed later is not the decision that was taken
    monitor_for_absence   a metric with nothing to measure looks exactly like a healthy one

Every detector returns a Finding. None of them raise on ordinary data; the point is to make a
silent condition loud, not to add a new way to crash.
"""
from .core import Finding, run_all
from .demote_never_delete import demote_never_delete
from .assert_nonzero import assert_nonzero
from .record_the_decision import record_the_decision
from .monitor_for_absence import monitor_for_absence

__all__ = ["Finding", "run_all", "demote_never_delete", "assert_nonzero",
           "record_the_decision", "monitor_for_absence"]
