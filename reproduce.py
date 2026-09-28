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
import math
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
    "declined_pct_from_boundary": "95",
    "prop_share_of_positions": "81",
    "prop_rows": "14104",
    "prop_noclose_pct": "24.9",
    "taken_noclose_pct": "41.3",
    "linemoved": "20060",
    "bracketing": "66",
    "bracketing_pct": "0.33",
    "logged": "139061",
    "still_quoted": "0",
    "player_absent": "119001",
    "linemoved_still_quoted": "0",
    "within_day_gap": "8.7",
    "within_day_gap_excludes_zero": "yes",
    "pooled_gap_matched": "8.0",
    "pooled_gap_excludes_zero": "yes",
    "failure_log_first_day": "7",
    "failure_wnba_pct": "90",
    "player_absent_pct": "86",
    "roi_acted": "+2.19",
    "roi_declined": "-2.24",
    "boundary_day": "12",
    "roi_acted_matched": "-0.94",
    "roi_gap_unmatched": "+4.4",
    "roi_gap_matched": "+1.3",
    "trial_n": "1163",
    "trial_days": "9",
    "trial_arm_bet": "591",
    "trial_arm_hold": "572",
    "trial_match_lo": "47",
    "trial_match_hi": "49",
    "trial_both_arms": "5",
    "control_n": "3738",
    "control_match_pct": "83.4",
    "control_both_arms": "0",
    "control_pre_n": "1258",
    "control_pre_pct": "50.6",
    "control_post_n": "2480",
    "control_post_pct": "100.0",
    "ct_detector_level": "ALARM",
    "ct_detector_depends_on_status": "yes",
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
    first_declined = min(int(r["day"]) for r in pos if r["acted"] == "0")
    after = [r for r in pos if int(r["day"]) >= first_declined]
    check("... declined share once declines were recorded (%)", "declined_pct_from_boundary",
          pct(sum(1 for r in after if r["acted"] == "0"), len(after), "%.0f"))
    check("player-prop share of all positions (%)", "prop_share_of_positions",
          pct(sum(1 for r in pos if r["is_prop"] == "1"), len(pos), "%.0f"))
    reg = rows("registry.csv")
    check("tests in the append-only registry", "registry", str(len(reg)))

    print("\nRESULTS - the metric is undefined, not merely noisy")
    props = [r for r in pos if r["is_prop"] == "1"]
    check("prop rows", "prop_rows", str(len(props)))
    check("prop rows with no closing price (%)", "prop_noclose_pct",
          pct(sum(1 for r in props if r["has_close"] == "0"), len(props)))
    taken = [r for r in props if r["acted"] == "1"]
    check("... among positions taken, POOLED (%)", "taken_noclose_pct",
          pct(sum(1 for r in taken if r["has_close"] == "0"), len(taken)))
    # The pooled figure is confounded by time: taken positions cluster early, when capture was worse,
    # and declined volume exploded late, when it was better. Compare like with like: within each day
    # holding both, taken minus declined, weighted by that day's taken count, bootstrapped by day.
    byday = collections.defaultdict(lambda: {"t": [], "d": []})
    for r in props:
        byday[r["day"]]["t" if r["acted"] == "1" else "d"].append(r)
    nc = lambda rs: sum(1 for r in rs if r["has_close"] == "0") / len(rs)
    both = sorted((d for d, v in byday.items() if v["t"] and v["d"]), key=int)
    diff = {d: (nc(byday[d]["t"]) - nc(byday[d]["d"]), len(byday[d]["t"])) for d in both}
    wavg = lambda ds: 100.0 * sum(diff[d][0] * diff[d][1] for d in ds) / sum(diff[d][1] for d in ds)
    gap = wavg(both)
    check("within-day gap, taken lack a close LESS often by (pp)", "within_day_gap", "%.1f" % -gap)
    rng = random.Random(0)
    b = sorted(wavg([rng.choice(both) for _ in both]) for _ in range(2000))
    lo, hi = b[50], b[1949]
    print("  %-52s CI [%+.1f, %+.1f]" % ("... day-clustered 95% interval, taken minus declined", lo, hi))
    check("... interval excludes zero", "within_day_gap_excludes_zero", "no" if lo <= 0 <= hi else "yes")
    # The SIZE depends on how days are weighted, so it is not the headline. What survives every
    # weighting is the DIRECTION on most days: a sign test over days, which needs no weights at all.
    eq = 100.0 * sum(diff[d][0] for d in both) / len(both)
    dw = 100.0 * (sum(diff[d][0] * len(byday[d]["d"]) for d in both)
                  / sum(len(byday[d]["d"]) for d in both))
    print("  %-52s taken-weighted %+.1f | equal days %+.1f | declined-weighted %+.1f"
          % ("... sensitivity of the gap to weighting (pp)", gap, eq, dw))
    # THE HEADLINE COMPARISON: pooled over the SAME days (both populations recorded), day-clustered.
    # It answers the practical question, "is the subset CLV is computed on representative?", and it
    # is not. Within days the sign reverses (above), which is reported as a limitation.
    def pooled(ds):
        tt = [r for d in ds for r in byday[d]["t"]]
        dd = [r for d in ds for r in byday[d]["d"]]
        return 100.0 * (nc(tt) - nc(dd))
    pg = pooled(both)
    check("same 60 days, pooled: taken lack a close MORE often by (pp)", "pooled_gap_matched", "%.1f" % pg)
    rng = random.Random(0)
    b = sorted(pooled([rng.choice(both) for _ in both]) for _ in range(2000))
    lo, hi = b[50], b[1949]
    print("  %-52s CI [%+.1f, %+.1f]" % ("... day-clustered 95% interval", lo, hi))
    check("... interval excludes zero", "pooled_gap_excludes_zero", "no" if lo <= 0 <= hi else "yes")
    # A day-level sign test is NOT valid here: with few taken positions a day, a taken no-close rate
    # of exactly 0 is common, so taken "wins" more than half of days under the null. Shown with its
    # permutation null so no one re-derives the wrong p-value from it.
    better = sum(1 for d in both if diff[d][0] < 0)
    prng = random.Random(1)
    null = []
    for _ in range(1000):
        w = 0
        for d in both:
            rs = byday[d]["t"] + byday[d]["d"]
            flags = [1] * len(byday[d]["t"]) + [0] * len(byday[d]["d"])
            prng.shuffle(flags)
            tt = [r for r, f in zip(rs, flags) if f]
            dd = [r for r, f in zip(rs, flags) if not f]
            w += nc(tt) < nc(dd)
        null.append(w)
    print("  %-52s %d of %d days; permutation null mean %.1f (not 30), p = %.2f"
          % ("(info) days taken better covered", better, len(both), sum(null) / len(null),
             min(1.0, 2.0 * sum(1 for x in null if x >= better) / len(null))))

    cf = rows("capture_failures.csv")
    moved = [r for r in cf if r["why"] == "line-moved"]
    brack = sum(1 for r in moved if r["brackets_two_sided"] == "1")
    check("capture failures from line movement", "linemoved", str(len(moved)))
    check("... with bracketing two-sided rungs", "bracketing", str(brack))
    check("... as a share (%)", "bracketing_pct", pct(brack, len(moved), "%.2f"))
    check("capture failures logged in total", "logged", str(len(cf)))
    n_absent = sum(1 for r in cf if r["why"] == "player-absent")
    check("... where the player had no market at all", "player_absent", str(n_absent))
    check("... as a share of failed captures (%)", "player_absent_pct", pct(n_absent, len(cf), "%.0f"))
    print("       (failed captures are POLLING EVENTS, not positions: one position can fail many times)")
    check("... first day with a logged failure", "failure_log_first_day",
          str(min(int(r["day"]) for r in cf if r["day"] != "")))
    check("... share that are WNBA (%)", "failure_wnba_pct",
          pct(sum(1 for r in cf if r["sport"] == "WNBA"), len(cf), "%.0f"))
    check("line-moved failures where our rung WAS still quoted (0 by construction)", "linemoved_still_quoted",
          str(sum(1 for r in moved if r["our_rung_available"] == "1")))
    check("failures where our rung WAS still quoted (0 by construction)", "still_quoted",
          str(sum(1 for r in cf if r["our_rung_available"] == "1")))
    print("       (a failure is only logged when the rung is absent, so this zero is a definition,")
    print("        not a finding; it is shown so no one mistakes it for one)")

    print("\nRESULTS - unmatched windows")
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
    check("acted minus declined ROI, unmatched windows (pp)", "roi_gap_unmatched",
          "%+.1f" % (roi(pnl, "acted") - roi(pnl, "declined")))
    check("acted minus declined ROI, matched days (pp)", "roi_gap_matched",
          "%+.1f" % (roi(pnl, "acted", matched) - roi(pnl, "declined", matched)))
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
    # From the system's configuration at the time, not from this data (edges are withheld):
    # a pick needed edge x eff_mult x cal_mult >= min_edge, and edge is capped at 13.0pp.
    cap, eff, cal, bar = 13.0, 0.90, 0.981, 12.0
    print("       configuration: best reachable %.1f x %.2f x %.3f = %.2f < bar %.1f  (unreachable)"
          % (cap, eff, cal, cap * eff * cal, bar))

    print("\nRESULTS - a trial that cannot be audited")
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
    print("       the original key was not recorded, so these only show that NO reconstruction re-derives")
    print("       the arms; the control below, whose formula IS known, is the evidence that matters")
    arms = collections.defaultdict(set)
    for r in tr:
        arms[r["bet_token"]].add(r["stored_arm"])
    check("... distinct bets that sit in BOTH arms", "trial_both_arms",
          str(sum(1 for v in arms.values() if len(v) > 1)))
    print("       (of %d distinct bets)" % len(arms))
    # POSITIVE CONTROL. Epoch 2 keyed the same coin on the canonical identity with a known formula.
    # Same audit, same machinery: if this reproduces far above chance, epoch 1's failure is its key.
    ctl = rows("trial_epoch2_control.csv")
    check("control: corrected epoch positions (n)", "control_n", str(len(ctl)))
    check("control: re-hash reproduces stored arm (%)", "control_match_pct",
          pct(sum(r["match_known_formula"] == "1" for r in ctl), len(ctl)))
    step = min(int(r["day"]) for r in ctl if all(x["match_known_formula"] == "1"
                                                   for x in ctl if int(x["day"]) >= int(r["day"])))
    pre = [r for r in ctl if int(r["day"]) < step]
    post = [r for r in ctl if int(r["day"]) >= step]
    print("  %-52s day %d  (every arm from here on re-derives)" % ("control: the step", step))
    check("control: arms stamped BEFORE the step (n)", "control_pre_n", str(len(pre)))
    check("control: ... re-derive (%)", "control_pre_pct",
          pct(sum(r["match_known_formula"] == "1" for r in pre), len(pre)))
    check("control: arms stamped FROM the step (n)", "control_post_n", str(len(post)))
    check("control: ... re-derive (%)", "control_post_pct",
          pct(sum(r["match_known_formula"] == "1" for r in post), len(post)))
    carms = collections.defaultdict(set)
    for r in ctl:
        carms[r["bet_token"]].add(r["stored_arm"])
    check("control: distinct bets in BOTH arms", "control_both_arms",
          str(sum(1 for v in carms.values() if len(v) > 1)))


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
    sys.path.insert(0, HERE)
    import io as _io
    import contextlib as _cl
    import run_detectors_clinicaltrials as rdc
    with _cl.redirect_stdout(_io.StringIO()):
        found = {f.detector: f for f in rdc.findings(ctrows)}
    mfa = found["monitor_for_absence"]
    check("clinical trials: monitor_for_absence, unmodified", "ct_detector_level", mfa.level)
    check("... flags coverage depending on trial status", "ct_detector_depends_on_status",
          "yes" if "depends on status" in str(mfa.detail.get("note", "")) else "no")
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
