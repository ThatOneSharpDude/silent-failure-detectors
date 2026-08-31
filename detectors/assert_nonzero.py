"""RULE 2 -- a file that parses is not a file with data.

THE FAILURE. A producer fails, writes a well-formed but empty artifact, and every consumer downstream
succeeds. Schema validation passes, the JSON loads, the CSV has its header, the job exits 0, and the
monitoring that watches for exceptions sees nothing, because nothing threw. The number that depended
on the artifact silently becomes zero -- and zero is a legal value for almost every count, so no
range check catches it either.

SCAR. A feeder stored count=0 for long enough that a table which should have held 24,507 rows held
none, and the only symptom was a downstream average that looked unusually stable.

THE RULE. Anything that emits a count asserts the count is non-zero, at the point of production, and
says so out loud when it is not. "It ran" is not the success condition; "it produced" is.

    assert_nonzero({"positions": 8017, "capture_failures": 0})
"""
from __future__ import annotations

from .core import Finding


def assert_nonzero(named_counts, expected_nonzero=None):
    d = dict(named_counts)
    names = list(expected_nonzero if expected_nonzero is not None else d.keys())
    empty = [k for k in names if not d.get(k)]
    if empty:
        return Finding(
            "assert_nonzero", "ALARM",
            "%d artifact(s) parsed cleanly and carried nothing: %s" % (len(empty), ", ".join(empty)),
            d)
    return Finding("assert_nonzero", "CLEAN",
                   "all %d artifact(s) carry at least one row" % len(names), d)
