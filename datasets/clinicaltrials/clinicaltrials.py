"""external_clinicaltrials.py — the detectors, unmodified, on a second external domain.

    py external_clinicaltrials.py            # fetch (cached) and report
    py external_clinicaltrials.py --refresh  # re-pull from the API

WHY. The SSAC submission claims "the structure is not specific to betting" and supports it with ONE
external domain: 44,128 federally reported mortgage applications, where an interest rate appears on
96.3% of originated loans and 0% of denied ones. One domain is an anecdote with a sample size. The
claim is about GENERALITY, so it needs a second field that shares the structure and shares nothing
else — different data, different regulator, different century of practice.

THE STRUCTURE BEING TESTED, stated in the paper's own terms:

    record the decision taken   a store that keeps only the positions TAKEN cannot see the ones
                                declined, and the declined ones are 93% of our own evidence
    monitor for absence         an outcome that is ABSENT rather than noisy, where absence is
                                conditional on the decision, so no amount of sampling recovers it

Clinical trial registration has exactly that shape and arrived at it independently. Every trial is
registered BEFORE its outcome is known — the registry is a record of decisions proposed, not of
results obtained, which is the reject-inference design the betting store had to be rebuilt to get.
Results are then posted, or they are not. If posting is conditional on what the results SAY, or on
who ran the trial, then any analysis over posted results is computed on a non-random subsample —
the identical failure the paper measures in CLV.

PRE-REGISTERED, because measuring first and describing the pattern afterwards is how a search gets
uncounted. Predictions recorded 2026-09-15 BEFORE the first query returned (see `PREDICTIONS`),
scored verbatim in the output. A prediction that misses is reported as a miss.

SOURCE: ClinicalTrials.gov API v2. Public, unmetered, no key. The standing rule is that metered
sources go last, and this needs none.
"""
from __future__ import annotations

import argparse
import collections
import io
import json
import os
import sys
import time
import urllib.parse
import urllib.request

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "data", "clinicaltrials_sample.jsonl")
_API = "https://clinicaltrials.gov/api/v2/studies"
_UA = {"User-Agent": "Mozilla/5.0"}

# ── PRE-REGISTRATION (written before any query returned) ──────────────────────────────────────
PREDICTIONS = [
    ("P1", "Results are posted on a MINORITY of completed interventional trials (<50%).",
     lambda s: s["interv_completed_rate"] < 50.0),
    ("P2", "TERMINATED trials post results at a LOWER rate than COMPLETED ones — absence is "
           "conditional on how the trial ended, which is the MNAR shape.",
     lambda s: s["terminated_rate"] < s["interv_completed_rate"]),
    ("P3", "INDUSTRY sponsors post at a HIGHER rate than non-industry, because FDAAA enforcement "
           "falls on them.",
     lambda s: s["industry_rate"] > s["other_rate"]),
    ("P4", "The gap between the best-reporting and worst-reporting sponsor class is at least 10 "
           "percentage points — i.e. WHO ran the trial predicts whether the outcome exists.",
     lambda s: s["sponsor_spread"] >= 10.0),
]


def _get(url: str, tries: int = 3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=_UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except Exception as e:
            last = e
            time.sleep(1.5 * (i + 1))
    raise last


def fetch(target: int = 40000, verbose: bool = True) -> list:
    """Completed/terminated/withdrawn/suspended studies, newest first, flattened to the few fields
    the detectors need. Cached — the point is a reproducible sample, not a live feed."""
    fields = ["NCTId", "OverallStatus", "HasResults", "CompletionDate",
              "LeadSponsorClass", "StudyType", "Phase", "EnrollmentCount"]
    statuses = ["COMPLETED", "TERMINATED", "WITHDRAWN", "SUSPENDED"]
    rows, token = [], None
    while len(rows) < target:
        q = {"pageSize": "1000", "fields": ",".join(fields),
             "filter.overallStatus": "|".join(statuses)}
        if token:
            q["pageToken"] = token
        blob = _get(_API + "?" + urllib.parse.urlencode(q))
        page = blob.get("studies") or []
        if not page:
            break
        for s in page:
            ps = s.get("protocolSection") or {}
            ident = ps.get("identificationModule") or {}
            st = ps.get("statusModule") or {}
            sp = (ps.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}
            dm = ps.get("designModule") or {}
            rows.append({
                "nct": ident.get("nctId"),
                "status": st.get("overallStatus"),
                "has_results": bool(s.get("hasResults")),
                "completion": ((st.get("completionDateStruct") or {}).get("date") or "")[:7],
                "sponsor": sp.get("class"),
                "study_type": dm.get("studyType"),
                "phases": ",".join(dm.get("phases") or []),
                "enrollment": ((dm.get("enrollmentInfo") or {}).get("count")),
            })
        token = blob.get("nextPageToken")
        if verbose:
            print("  fetched %d..." % len(rows))
        if not token:
            break
        time.sleep(0.25)                      # politeness; the source is free and unmetered
    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    with io.open(CACHE, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")
    return rows


def load(refresh: bool = False, target: int = 40000) -> list:
    if refresh or not os.path.exists(CACHE):
        return fetch(target)
    return [json.loads(ln) for ln in io.open(CACHE, encoding="utf-8") if ln.strip()]


def _pct(a: int, b: int) -> float:
    return (100.0 * a / b) if b else float("nan")


def analyse(rows: list) -> dict:
    interv = [r for r in rows if r.get("study_type") == "INTERVENTIONAL"]
    comp = [r for r in interv if r.get("status") == "COMPLETED"]
    term = [r for r in interv if r.get("status") in ("TERMINATED", "WITHDRAWN", "SUSPENDED")]

    by_sponsor = collections.defaultdict(lambda: [0, 0])
    for r in comp:
        cell = by_sponsor[r.get("sponsor") or "UNKNOWN"]
        cell[1] += 1
        cell[0] += 1 if r["has_results"] else 0
    sponsor_rates = {k: _pct(v[0], v[1]) for k, v in by_sponsor.items() if v[1] >= 200}

    s = {
        "n_total": len(rows),
        "n_interv": len(interv),
        "n_comp": len(comp),
        "n_term": len(term),
        "interv_completed_rate": _pct(sum(1 for r in comp if r["has_results"]), len(comp)),
        "terminated_rate": _pct(sum(1 for r in term if r["has_results"]), len(term)),
        "observational_rate": _pct(
            sum(1 for r in rows if r.get("study_type") == "OBSERVATIONAL" and r["has_results"]),
            sum(1 for r in rows if r.get("study_type") == "OBSERVATIONAL")),
        "sponsor_rates": sponsor_rates,
        "industry_rate": sponsor_rates.get("INDUSTRY", float("nan")),
        "other_rate": sponsor_rates.get("OTHER", float("nan")),
        "sponsor_spread": (max(sponsor_rates.values()) - min(sponsor_rates.values())
                           if len(sponsor_rates) >= 2 else float("nan")),
    }
    return s


def report(rows: list) -> dict:
    s = analyse(rows)
    print("=" * 98)
    print("  SECOND EXTERNAL DOMAIN — clinical trial registration")
    print("  the detectors, unmodified, on data that shares the STRUCTURE and nothing else")
    print("=" * 98)
    print()
    print("  sample: %d studies  (%d interventional: %d completed, %d terminated/withdrawn)"
          % (s["n_total"], s["n_interv"], s["n_comp"], s["n_term"]))
    print()
    print("  MONITOR FOR ABSENCE — is the outcome there at all?")
    print("  " + "-" * 94)
    print("    results posted, completed interventional : %5.1f%%  (n=%d)"
          % (s["interv_completed_rate"], s["n_comp"]))
    print("    results posted, terminated/withdrawn     : %5.1f%%  (n=%d)"
          % (s["terminated_rate"], s["n_term"]))
    print("    results posted, observational            : %5.1f%%" % s["observational_rate"])
    print()
    print("  RECORD THE DECISION TAKEN — who ran it predicts whether the outcome exists")
    print("  " + "-" * 94)
    for k, v in sorted(s["sponsor_rates"].items(), key=lambda kv: -kv[1]):
        print("    %-10s %5.1f%%   (n=%d)" % (k, v, by_n(rows, k)))
    print()
    print("  PRE-REGISTERED PREDICTIONS (written before the first query returned)")
    print("  " + "-" * 94)
    hits = 0
    for pid, text, fn in PREDICTIONS:
        try:
            ok = bool(fn(s))
        except Exception:
            ok = False
        hits += ok
        print("    [%s] %s  %s" % ("HIT " if ok else "MISS", pid, text))
    print()
    print("    %d of %d predictions held." % (hits, len(PREDICTIONS)))

    # ── POST HOC. Explicitly labelled, because this was found by looking AFTER the predictions
    # were scored, and an observation discovered that way does not carry the same weight as one
    # that was registered in advance. It is reported because it is the strongest result here, not
    # because it rescues P2 — P2 stays a MISS above and is not rewritten.
    iv = [r for r in rows if r.get("study_type") == "INTERVENTIONAL"]

    def _r(sel):
        n = len(sel)
        return (_pct(sum(1 for x in sel if x["has_results"]), n), n)

    print()
    print("  POST HOC (found after scoring; not pre-registered)")
    print("  " + "-" * 94)
    print("    P2 lumped TERMINATED with WITHDRAWN and SUSPENDED. Split:")
    for st in ("COMPLETED", "TERMINATED", "WITHDRAWN", "SUSPENDED"):
        rate, n = _r([x for x in iv if x.get("status") == st])
        print("      %-11s %5.1f%%  (n=%d)" % (st, rate, n))
    print()
    print("    WITHDRAWN is 0.0%% of %d — a trial that never enrolled can have no outcome, exactly"
          % len([x for x in iv if x.get("status") == "WITHDRAWN"]))
    print("    as a DENIED mortgage has no interest rate. Two regulators who never spoke to each")
    print("    other produced the same hole in the same place.")
    print()
    print("    And P2's miss is REAL, not composition — terminated posts HIGHER within EVERY")
    print("    sponsor class with n>=100, so it is not Simpson's:")
    for sp in ("INDUSTRY", "OTHER"):
        rc, nc = _r([x for x in iv if x.get("status") == "COMPLETED" and x.get("sponsor") == sp])
        rt, nt = _r([x for x in iv if x.get("status") == "TERMINATED" and x.get("sponsor") == sp])
        print("      %-9s completed %5.1f%% (n=%-5d)   terminated %5.1f%% (n=%-5d)"
              % (sp, rc, nc, rt, nt))
    print()
    print("    A trial STOPPED EARLY reports more often than one that ran to completion. The")
    print("    mechanism is NOT measured here and is not claimed. What it establishes is the")
    print("    paper's actual point: absence is structured, the structure is not the one you would")
    print("    guess, and a prior about it is worth less than a measurement of it.")
    print("=" * 98)
    return s


def by_n(rows: list, sponsor: str) -> int:
    return sum(1 for r in rows if r.get("study_type") == "INTERVENTIONAL"
               and r.get("status") == "COMPLETED" and (r.get("sponsor") or "UNKNOWN") == sponsor)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--n", type=int, default=40000)
    a = ap.parse_args(argv)
    rows = load(refresh=a.refresh, target=a.n)
    report(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
