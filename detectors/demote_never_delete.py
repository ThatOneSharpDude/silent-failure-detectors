"""RULE 1 -- a row you drop cannot later be counted as missing.

THE FAILURE. A filter removes rows it judges unusable, and the removed rows leave no trace. Every
downstream figure is then computed on a population the filter invented, and the filter's own error
rate is unmeasurable, because the evidence of the error was the thing it deleted. The population is
smaller AND cleaner-looking, so every quality metric improves as the filter gets more aggressive.
This is the shape that makes a bad filter indistinguishable from a good one.

THE RULE. Never remove; mark. A row that fails a check keeps its place in the table and gains a
column saying which check it failed. Coverage is then arithmetic instead of an assumption, and the
filter can be audited on its own decisions.

WHAT THIS DETECTS. A gap between a table's population and the population that reached it. You give
it the count that entered and the rows that came out; if rows vanished without a recorded reason,
that is the finding. It also fires on the subtler version -- rows are marked, but one reason code
accounts for so much of the table that the code is doing the work a delete used to do.

    demote_never_delete(rows, entered=9184, reason_key="why")
"""
from __future__ import annotations

from .core import Finding, counts

DOMINANT_SHARE = 0.90      # one reason covering ~everything is a delete wearing a label


def demote_never_delete(rows, entered=None, reason_key=None, tolerate=0):
    rows = list(rows)
    n = len(rows)
    d = {"rows_present": n}

    if entered is not None:
        d["rows_that_entered"] = entered
        lost = entered - n
        d["unaccounted_for"] = lost
        if lost > tolerate:
            return Finding(
                "demote_never_delete", "ALARM",
                "%d of %d rows left no trace -- coverage here is an assumption, not a count"
                % (lost, entered), d)

    if reason_key:
        c = counts(rows, reason_key)
        marked = sum(v for k, v in c.items() if k not in (None, "", "ok", "OK"))
        d["rows_carrying_a_reason"] = marked
        if c:
            top, top_n = c.most_common(1)[0]
            d["most_common_reason"] = "%s (%d)" % (top, top_n)
            if n and top_n >= DOMINANT_SHARE * n:
                return Finding(
                    "demote_never_delete", "WATCH",
                    "one reason covers %.0f%% of the table; it is absorbing what a delete used to"
                    % (100.0 * top_n / n), d)

    return Finding("demote_never_delete", "CLEAN",
                   "every row that entered is still addressable", d)
