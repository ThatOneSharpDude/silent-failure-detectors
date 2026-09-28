"""fetch_chadwick.py -- how often does a player's NAME fail to identify the player?

WHY THIS DATASET. The trial result -- a randomised test whose coin hashed mutable raw fields, so no
row can confirm its own arm -- rests on one system's rows. This is a public, third-party measurement of the same MECHANISM: what happens when
identity is derived from a name instead of being carried as a stored key.

The Chadwick Bureau register is a free crosswalk between the player identifiers used by MLBAM,
Retrosheet, Baseball-Reference, FanGraphs and others. It exists BECAUSE name-keying does not work,
which makes it an unusually direct source: `key_person` is the canonical identity, and the name
fields are exactly the raw fields a naive join would use.

    py fetch_chadwick.py            # modern extract (MLB, played 2015+) -- this is what ships
    py fetch_chadwick.py --full     # also print the figures for the whole register

READ THE LIMITATION IN THE MODULE THAT CONSUMES THIS before quoting any number from it.
"""
from __future__ import annotations

import collections
import csv
import io
import os
import re
import sys
import unicodedata
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BASE = "https://raw.githubusercontent.com/chadwickbureau/register/master/data/people-%s.csv"
SHARDS = "0123456789abcdef"
HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) "
                          "Gecko/20100101 Firefox/127.0")}
MODERN_FROM = 2015


def strip_accents(s):
    s = unicodedata.normalize("NFKD", str(s or ""))
    return "".join(c for c in s if not unicodedata.combining(c))


def norm(s):
    """The normalisation a naive join applies: fold accents, lowercase, drop punctuation."""
    return re.sub(r"[^a-z ]", "", strip_accents(s).lower()).strip()


def has_diacritic(s):
    return strip_accents(s) != str(s or "")


def fetch():
    rows = []
    for sh in SHARDS:
        d = urllib.request.urlopen(urllib.request.Request(BASE % sh, headers=HEADERS),
                                   timeout=300).read().decode("utf-8", "replace")
        rows.extend(list(csv.DictReader(io.StringIO(d))))
        print("    shard %s -> %d people" % (sh, len(rows)))
    if not rows:
        raise SystemExit("empty register -- refusing to continue")     # rule 2, on ourselves
    return rows


def collisions(pop):
    m = collections.defaultdict(set)
    for r in pop:
        f, l = norm(r.get("name_first")), norm(r.get("name_last"))
        if f and l:
            m[f + " " + l].add(r["key_person"])
    names = len(m)
    amb = sum(1 for v in m.values() if len(v) > 1)
    people = sum(len(v) for v in m.values())
    affected = sum(len(v) for v in m.values() if len(v) > 1)
    return m, {"names": names, "ambiguous_names": amb, "people": people, "affected": affected}


def year(r, f):
    try:
        return int((r.get(f) or "").strip())
    except ValueError:
        return None


def main():
    print("  downloading the Chadwick Bureau register (16 shards, ~65MB)...")
    rows = fetch()
    mlb = [r for r in rows if (r.get("key_mlbam") or "").strip()]
    modern = [r for r in mlb if (year(r, "mlb_played_last") or 0) >= MODERN_FROM]

    for label, pop in (("whole register", rows), ("has an MLBAM id", mlb),
                       ("MLB, played %d+" % MODERN_FROM, modern)):
        _, s = collisions(pop)
        print("  %-24s names=%6d  ambiguous=%5d (%5.2f%%)  people affected=%6d (%5.2f%%)"
              % (label, s["names"], s["ambiguous_names"],
                 100.0 * s["ambiguous_names"] / max(s["names"], 1),
                 s["affected"], 100.0 * s["affected"] / max(s["people"], 1)))

    # Only the modern slice ships: it is the population a live betting system actually prices, and
    # it keeps the repository small. The fetcher regenerates every figure above on demand.
    path = os.path.join(HERE, "chadwick_modern.csv")
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["name_key", "person_id", "has_diacritic", "mlb_played_last"])
        for r in modern:
            f, l = norm(r.get("name_first")), norm(r.get("name_last"))
            if not f or not l:
                continue
            w.writerow([f + " " + l, r["key_person"],
                        int(has_diacritic(r.get("name_first")) or
                            has_diacritic(r.get("name_last"))),
                        year(r, "mlb_played_last") or ""])
    print("  wrote %s" % path)
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
