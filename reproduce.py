"""reproduce.py — regenerate every figure in the abstract from the shipped files. No network.

Run:  python reproduce.py

Each line prints the value this data produces next to the value printed in the paper, compared as
the paper prints it (same rounding) with ZERO tolerance. If a line says MISMATCH, the paper and the
data disagree and the paper is wrong, not the data. Exit status is 1 on any mismatch.

Zero tolerance is deliberate. An earlier checker allowed "drift tolerance" on figures read from the
live store, and that tolerance hid a headline ROI moving from +1.60% to +0.40% at an unchanged
cutoff. The fix was to freeze the data, not to widen the band: this script reads only files in this
repository, which do not change.

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
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(HERE, "data")

# Every figure the abstract prints, exactly as printed.
PAPER = {
    "positions": "17447",
    "pricing_days": "72",
    "declined_pct": "93",
    "prop_rows": "14104",
    "prop_noclose_pct": "24.9",
    "taken_noclose_pct": "41.3",
    "linemoved": "20060",
    "bracketing": "66",
    "bracketing_pct": "0.33",
    "logged": "139061",
    "still_quoted": "0",
    "roi_acted": "+2.19",
    "roi_declined": "-2.24",
    "boundary_day": "12",
    "roi_acted_matched": "-0.94",
    "trial_n": "1163",
    "trial_days": "9",
    "trial_arm_bet": "591",
    "trial_arm_hold": "572",
    "trial_match_lo": "47",
    "trial_match_hi": "49",
    "trial_both_arms": "5",
    "segment_n": "914",
    "segment_bet": "0",
    "segment_days": "16",
    "registry": "76",
    "hmda_n": "44128",
    "hmda_orig_pct": "96.3",
    "hmda_denied_pct": "0.0",
    "ct_n": "40000",
    "ct_completed_pct": "24.3",
    "ct_withdrawn_n": "1445",
    "ct_withdrawn_pct": "0.0",
}

_bad = []
RESULTS = []          # (label, key, data, paper, ok) for callers that want the verdicts, not the print


def rows(name):
    with open(os.path.join(D, name), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def check(label, key, got):
    ok = got == PAPER[key]
    RESULTS.append((label, key, got, PAPER[key], ok))
    if not ok:
        _bad.append(label)
    print("  %-52s data=%-10s paper=%-10s %s" % (label, got, PAPER[key], "OK" if ok else "MISMATCH"))


def pct(a, b, fmt="%.1f"):
    return fmt % (100.0 * a / b) if b else "nan"


def roi(pnl, pop, days=None):
    sel = [r for r in pnl if r["population"] == pop and (days is None or r["day"] in days)]
    st = sum(float(r["staked_units"]) for r in sel)
    rt = sum(float(r["returned_units"]) for r in sel)
    return 100.0 * (rt - st) / st if st else 0.0


def betting():
    pos = rows("positions.csv")
    print("METHODS")
    check("evaluated positions (n)", "positions", str(len(pos)))
    check("pricing days", "pricing_days", str(len({r["day"] for r in pos})))
    check("share the system declined (%)", "declined_pct",
          pct(sum(1 for r in pos if r["acted"] == "0"), len(pos), "%.0f"))
    reg = rows("registry.csv")
    check("tests in the append-only registry", "registry", str(len(reg)))

    print("\nRESULTS - the metric is undefined, not merely noisy")
    props = [r for r in pos if r["is_prop"] == "1"]
    check("prop rows", "prop_rows", str(len(props)))
    check("prop rows with no closing price (%)", "prop_noclose_pct",
          pct(sum(1 for r in props if r["has_close"] == "0"), len(props)))
    taken = [r for r in props if r["acted"] == "1"]
    check("... among positions taken (%)", "taken_noclose_pct",
          pct(sum(1 for r in taken if r["has_close"] == "0"), len(taken)))

    cf = rows("capture_failures.csv")
    moved = [r for r in cf if r["why"] == "line-moved"]
    brack = sum(1 for r in moved if r["brackets_two_sided"] == "1")
    check("capture failures from line movement", "linemoved", str(len(moved)))
    check("... with bracketing two-sided rungs", "bracketing", str(brack))
    check("... as a share (%)", "bracketing_pct", pct(brack, len(moved), "%.2f"))
    check("capture failures logged in total", "logged", str(len(cf)))
    check("failures where our rung WAS still quoted", "still_quoted",
          str(sum(1 for r in cf if r["our_rung_available"] == "1")))
    print("       (that zero is the point: no polling rate recovers a price nobody is offering)")

    print("\nRESULTS - a population boundary sets the sign")
    pnl = rows("daily_pnl.csv")
    # The store recorded O\nY positions taken until declined rows first appear. Any pooled figure
    # spans that boundary, so it is computed both ways.
    boundary = min(int(r["day"]) for r in pos if r["acted"] == "0")
    check("first day declined positions were recorded", "boundary_day", str(boundary))
    matched = sorted({r["day"] for r in pnl if int(r["day"]) >= boundary})
    check("ROI, positions acted on, pooled (%)", "roi_acted", "%+.2f" % roi(pnl, "acted"))
    check("ROI, acted on, days both were recorded (%)", "roi_acted_matched",
          "%+.2f" % roi(pnl, "acted", matched))
    check("ROI, positions declined (%)", "roi_declined", "%+.2f" % roi(pnl, "declined"))
    # day-clustered bootstrap: resample DAYS, not bets. Rows inside a day share a slate, a feed and
    # a model version, so treating them as independent overstates precision several-fold.
    rng = random.Random(0)
    for pop in ("acted", "declined"):
        b = sorted(roi(pnl, pop, [rng.choice(matched) for _ in matched]) for _ in range(2000))
        lo, hi = b[50], b[1949]
        print("  %-52s CI [%+.2f, %+.2f]  crosses zero: %s"
              % ("day-clustered 95%% CI, matched days, %s" % pop, lo, hi,
                 "YES" if lo <= 0 <= hi else "no"))

    print("\nRESULTS - a filter that could never pass")
    seg = rows("best_segment.csv")
    check("best segment denominator, defect window (n)", "segment_n", str(len(seg)))
    check("... of which reached a bettable tier", "segment_bet",
          str(sum(1 for r in seg if r["reached_bet_tier"] == "1")))
    check("... slate days", "segment_days", str(len({r["day"] for r in seg})))
    print("       pinned at the shrink cap: %d  (the bar sat above the highest edge the model can emit)"
          % sum(1 for r in seg if r["pinned_at_shrink_cap"] == "1"))

    print("\nRESULTS - the experiment that was silently not one")
    tr = rows("trial_epoch1.csv")
    check("trial epoch-1 positions (n)", "trial_n", str(len(tr)))
    check("... days it ran", "trial_days", str(len({r["day"] for r in tr})))
    check("... assigned to the bet arm", "trial_arm_bet",
          str(sum(r["stored_arm"] == "ARM_BET" for r in tr)))
    check("... assigned to the hold arm", "trial_arm_hold",
          str(sum(r["stored_arm"] == "ARM_HOLD" for r in tr)))
    cols = [c for c in tr[0] if c.startswith("match_")]
    rates = {c: 100.0 * sum(r[c] == "1" for r in tr) / len(tr) for c in cols}
    for c, v in rates.items():
        print("  %-52s %.1f%%" % ("re-hashed row reproduces its arm, " + c[6:], v))
    check("... lowest reproduction rate across key constructions", "trial_match_lo",
          "%.0f" % min(rates.values()))
    check("... highest reproduction rate across key constructions", "trial_match_hi",
          "%.0f" % max(rates.values()))
    print("       a fresh coin would reproduce 50%: the assignment cannot be audited from its row")
    arms = collections.defaultdict(set)
    for r in tr:
        arms[r["bet_token"]].add(r["stored_arm"])
    check("... distinct bets that sit in BOTH arms", "trial_both_arms",
          str(sum(1 for v in arms.values() if len(v) > 1)))
    print("       (of %d distinct bets)" % len(arms))


def external():
    print("\nTHE SAME DETECTORS, OTHER DOMAINS")
    path = os.path.join(HERE, "datasets", "hmda", "hmda_extract.csv")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            h = list(csv.DictReader(fh))
        rate = lambda sel: pct(sum(1 for r in sel if r["has_interest_rate"] == "1"), len(sel))
        check("HMDA applications (n)", "hmda_n", str(len(h)))
        check("HMDA rate present, originated (%)", "hmda_orig_pct",
              rate([r for r in h if r["action"] == "originated"]))
        check("HMDA rate present, denied (%)", "hmda_denied_pct",
              rate([r for r in h if r["action"] == "denied"]))
    else:
        _bad.append("HMDA extract missing")
        print("  HMDA extract missing: run  py datasets/hmda/fetch_hmda.py")

    sys.path.insert(0, os.path.join(HERE, "datasets", "clinicaltrials"))
    import clinicaltrials as ct
    ctrows = ct.load()
    s = ct.analyse(ctrows)
    wd = [r for r in ctrows if r.get("study_type") == "INTERVENTIONAL" and r.get("status") == "WITHDRAWN"]
    check("trials sampled (n)", "ct_n", str(s["n_total"]))
    check("results posted, completed interventional (%)", "ct_completed_pct",
          "%.1f" % s["interv_completed_rate"])
    check("withdrawn interventional trials (n)", "ct_withdrawn_n", str(len(wd)))
    check("results posted, withdrawn (%)", "ct_withdrawn_pct",
          pct(sum(1 for r in wd if r["has_results"]), len(wd)))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    print("=" * 92)
    print("  REPRODUCING THE ABSTRACT'S FIGURES FROM THE SHIPPED DATA")
    print("=" * 92)
    print(open(os.path.join(D, "CUTOFF.txt"), encoding="utf-8").read())
    betting()
    external()
    print("=" * 92)
    print("  %d MISMATCH" % len(_bad))
    return 1 if _bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
