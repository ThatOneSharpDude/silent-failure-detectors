"""reproduce.py — regenerate every figure in the abstract from the shipped CSVs. No network.

Run:  python reproduce.py

Each block prints the value this data produces next to the value printed in the paper. If a line
says MISMATCH, the paper and the data disagree and the paper is wrong, not the data.

WHAT IS AND IS NOT HERE. The data is deliberately reduced to what the claims need:

  * day indices are RELATIVE (day 0 = first day of the window), so nothing joins to a calendar
    or to an external odds feed
  * no player, game, team, book, market description, line, price, model probability or edge
  * bet-level results appear ONLY as per-day aggregates (staked / returned), which reproduce the
    ROI figures and their clustered interval without exposing any individual position
  * identity tokens are salted with an ephemeral salt that was discarded at generation time, so
    they cannot be inverted even by the author

The paper makes no claim about predictive edge, so none of the withheld fields are needed to check
any result in it.
"""
import collections
import csv
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")


def rows(name):
    with open(os.path.join(D, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def check(label, got, paper, fmt="%.1f"):
    g = fmt % got if isinstance(got, float) else str(got)
    p = fmt % paper if isinstance(paper, float) else str(paper)
    ok = "OK" if g == p else "MISMATCH"
    print("  %-52s data=%-10s paper=%-10s %s" % (label, g, p, ok))


print("=" * 92)
print("  REPRODUCING THE ABSTRACT'S FIGURES FROM THE SHIPPED DATA")
print("=" * 92)
print(open(os.path.join(D, "CUTOFF.txt"), encoding="utf-8").read())

pos = rows("positions.csv")
print("METHODS")
check("evaluated positions (n)", len(pos), 8017)
check("of which graded", sum(int(r["graded"]) for r in pos), 7767)
declined = sum(1 for r in pos if r["acted"] == "0")
check("share the system declined (%)", 100.0 * declined / len(pos), 87.0, "%.0f")

print("\nRESULTS — the metric is undefined, not merely noisy")
props = [r for r in pos if r["market_class"] == "PROP"]
check("prop rows", len(props), 6391)
noclose = [r for r in props if r["has_close"] == "0"]
check("prop rows with no closing price (%)", 100.0 * len(noclose) / len(props), 37.3)
taken = [r for r in props if r["acted"] == "1"]
check("... among positions taken (%)",
      100.0 * sum(1 for r in taken if r["has_close"] == "0") / max(len(taken), 1), 46.2)

cf = rows("capture_failures.csv")
moved = [r for r in cf if r["why"] == "line-moved"]
check("capture failures from line movement", len(moved), 13047)
brack = sum(1 for r in moved if r["brackets_two_sided"] == "1")
check("... with bracketing two-sided rungs", brack, 53)
check("... as a share (%)", 100.0 * brack / max(len(moved), 1), 0.41, "%.2f")
avail = sum(1 for r in cf if r["our_rung_available"] == "1")
check("failures where our rung WAS still quoted", avail, 0)
print("       (that zero is the point: no polling rate recovers a price nobody is offering)")

print("\nRESULTS — population choice determines the sign")
pnl = rows("daily_pnl.csv")


def roi(pop, days=None):
    sel = [r for r in pnl if r["population"] == pop and (days is None or r["day"] in days)]
    st = sum(float(r["staked_units"]) for r in sel)
    rt = sum(float(r["returned_units"]) for r in sel)
    return 100.0 * (rt - st) / st if st else 0.0


check("ROI, positions taken (%)", roi("acted"), 1.60, "%.2f")
check("ROI, all evaluated positions (%)", roi("declined"), -1.40, "%.2f")

# day-clustered bootstrap: resample DAYS, not bets. Rows inside a day share a slate, a feed and a
# model version, so treating them as independent overstates precision several-fold.
alldays = sorted({r["day"] for r in pnl})
rng = random.Random(0)
for pop in ("acted", "declined"):
    b = sorted(roi(pop, [rng.choice(alldays) for _ in alldays]) for _ in range(2000))
    lo, hi = b[50], b[1949]
    print("  %-52s CI [%+.2f, %+.2f]  crosses zero: %s"
          % ("clustered 95%% CI, %s" % pop, lo, hi, "YES" if lo <= 0 <= hi else "no"))

print("\nRESULTS — the experiment that was silently not one")
idf = rows("identity_drift.csv")
pair = collections.defaultdict(set)
for r in idf:
    pair[r["raw_field_token"]].add(r["canonical_token"])
split = sum(1 for k, v in pair.items() if len(v) > 1)
print("  %-52s %d of %d raw keys map to >1 canonical id"
      % ("identity drift", split, len(pair)))
print("       one bet drawing two assignments is what made the A/B irreproducible")
print("=" * 92)
