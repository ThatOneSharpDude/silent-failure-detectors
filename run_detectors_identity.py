"""run_detectors_identity.py -- rule 3, measured on public third-party sports data.

    py datasets/chadwick/fetch_chadwick.py   # once, needs network
    py run_detectors_identity.py             # offline thereafter

WHAT THIS DOES AND DOES NOT SHOW -- read this before quoting a number from it.

DOES. It demonstrates, on data nobody here produced, that deriving identity from a name is not a
safe operation: names collide, and names carry characters whose normalisation is a choice. The
register is a third-party artifact whose existence is itself the evidence, since it was built to
solve exactly this problem for public baseball datasets.

DOES NOT. It does not corroborate the trial's chance-level reproducibility (47-49%), and must
not be presented as if it did. That failure was driven mainly by OTHER mutable fields in the
identity key -- a market string respelled between writers, a line arriving as None on one path and
0.0 on another -- with name handling only one contributor. This measures a single component of the
mechanism, on a different population, and it comes out an order of magnitude smaller for current
players. The honest claim is that the mechanism is real and publicly measurable, not that its
magnitude here validates ours.
"""
from __future__ import annotations

import collections
import csv
import os
import sys

from detectors import Finding, assert_nonzero, record_the_decision, run_all

EXTRACT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "datasets", "chadwick", "chadwick_modern.csv")


def main():
    if not os.path.exists(EXTRACT):
        print("no extract yet -- run:  py datasets/chadwick/fetch_chadwick.py")
        return 2
    with open(EXTRACT, encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))

    out = [assert_nonzero({"players": len(rows)})]

    # RULE 3, on its own. raw key = the normalised name a naive join would build.
    # canonical id = key_person, the register's stored identity.
    out.append(record_the_decision([(r["name_key"], r["person_id"]) for r in rows]))

    code = run_all(out)

    m = collections.defaultdict(set)
    for r in rows:
        m[r["name_key"]].add(r["person_id"])
    worst = sorted(((len(v), k) for k, v in m.items()), reverse=True)[:6]
    dia = sum(1 for r in rows if r["has_diacritic"] == "1")

    print("""
  MLB players active 2015 or later, keyed by normalised name:

    most-collided names   %s

    %d of %d players (%.1f%%) carry a diacritic in their name. That is the larger surface. A
    collision needs two people to exist; a normalisation difference needs only one writer to fold
    accents and another not to, and then the same player has two keys. This project has already
    shipped that exact bug -- a transaction check missed "Marquez" because the source wrote
    "Marquez" with an acute accent.

  SCALE, HONESTLY. Among current players the collision rate is about 1%%, not a crisis. Across the
  whole register of 518,743 people it is 23.6%%, because history is long and names repeat. Neither
  number is the one from our A/B result, and this run is not offered as confirmation of it -- see
  the module docstring. What it establishes is that the failure mode is a property of name-keying
  itself and is measurable by anyone, on data we did not generate.""" % (
        ", ".join("%s x%d" % (k, n) for n, k in worst), dia, len(rows),
        100.0 * dia / max(len(rows), 1)))
    return code


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
