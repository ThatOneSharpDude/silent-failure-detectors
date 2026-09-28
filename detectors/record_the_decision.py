"""RULE 3 -- store the decision that was taken, not the inputs you could re-derive it from.

THE FAILURE. A system records a bet, an assignment, a routing choice -- but stores the raw fields and
recomputes the decision on read. The recomputation is a different function than the one that ran: the
code changed, a lookup table moved, a name normalised differently. So the record of what happened is
reconstructed from what would happen now, and the two quietly disagree.

SCAR. A randomised trial on a selection gate stamped each arm with a deterministic coin, a hash of the
position's identity, so any assignment could be audited by re-deriving it. The arm WAS written onto
each row, which is the only reason what follows is measurable. Re-deriving every stored arm with the
coin's exactly known formula gives a step: all 2,480 arms stamped from 5 September re-derive, and the
1,258 stamped before match 50.6%, a coin flip. Something changed that nothing records, and every
earlier assignment became unverifiable from its own row. An earlier version keyed on raw fields also
put five bets in both arms, which is what this detector finds.

THE RULE. Write the decision down, at the moment it is taken, next to the inputs. The inputs are for
diagnosis. The stored decision is what actually happened, and it is the only thing an audit can use.

WHAT THIS DETECTS. Give it (key, decision) pairs as they were recorded. If one key ever carries more
than one decision, the decision is not a function of the thing it was supposedly about, and anything
keyed on it -- dedup, assignment, join, coverage -- is unreliable in a way no balance test will show.
Pass whatever key the system CLAIMS the decision depends on: here, a bet and the arm stamped on it.

    record_the_decision([(r["bet_token"], r["stored_arm"]) for r in trial_rows])
"""
from __future__ import annotations

import collections

from .core import Finding


def record_the_decision(pairs, tolerate_share=0.0):
    m = collections.defaultdict(set)
    for raw, canon in pairs:
        m[raw].add(canon)
    n = len(m)
    split = sum(1 for v in m.values() if len(v) > 1)
    d = {"distinct_raw_keys": n, "keys_mapping_to_more_than_one_id": split,
         "share": ("%.1f%%" % (100.0 * split / n)) if n else "n/a"}
    if not n:
        return Finding("record_the_decision", "WATCH", "no identity pairs supplied", d)
    if split > tolerate_share * n:
        return Finding(
            "record_the_decision", "ALARM",
            "%d of %d keys carry more than one decision -- the decision is not a function of "
            "the thing it was taken about" % (split, n), d)
    return Finding("record_the_decision", "CLEAN",
                   "every key carries exactly one decision", d)
