"""RULE 3 -- store the decision that was taken, not the inputs you could re-derive it from.

THE FAILURE. A system records a bet, an assignment, a routing choice -- but stores the raw fields and
recomputes the decision on read. The recomputation is a different function than the one that ran: the
code changed, a lookup table moved, a name normalised differently. So the record of what happened is
reconstructed from what would happen now, and the two quietly disagree.

SCAR, and it is the worst one here. A randomised A/B ran for nine days with arms that looked balanced
353 to 350. The assignment was recomputed from an identity key built out of raw fields. Those fields
drifted -- a market string respelled, a line arriving as None in one path and 0.0 in another -- so a
single bet could draw two different assignments on two different reads. 51.7% of 9,074 assignments
were irreproducible. The experiment was not underpowered or noisy; it was never a randomised trial,
and every balance check it passed was a check on the recomputation, not on the randomisation.

THE RULE. Write the decision down, at the moment it is taken, next to the inputs. The inputs are for
diagnosis. The stored decision is what actually happened, and it is the only thing an audit can use.

WHAT THIS DETECTS. Give it (raw_key, canonical_key) pairs as they were observed over time. If one raw
key ever mapped to more than one canonical id, the identity is not stable, and anything keyed on it
-- dedup, assignment, join, coverage -- is unreliable in a way no balance test will show.

    record_the_decision([(r["raw_field_token"], r["canonical_token"]) for r in rows])
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
            "%d of %d raw keys resolve to more than one id -- a recomputed decision is not the "
            "decision that was taken" % (split, n), d)
    return Finding("record_the_decision", "CLEAN",
                   "every raw key resolves to exactly one id", d)
