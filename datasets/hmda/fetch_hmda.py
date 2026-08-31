"""fetch_hmda.py -- pull one state-year of the HMDA Loan Application Register and reduce it.

WHY THIS DATASET. The betting results in this repository come from one operator's own pipeline, so
the fair objection is that they are three bugs in one system rather than a failure class. HMDA is the
control. It is public, federally mandated, collected by thousands of independent institutions, and
nobody involved in it has read this paper. If the same detectors fire on it, the shape is not ours.

It is also the closest public analogue to the structure that makes self-evaluation fail: the register
records applications that were ORIGINATED alongside those that were DENIED, withdrawn or left
incomplete. The lender's book is action_taken=1; everything else is the population it did not write.

    py fetch_hmda.py                 # Delaware 2023 (44,128 applications, ~17MB download)
    py fetch_hmda.py --state CT --year 2022

Writes hmda_extract.csv next to this file -- booleans and buckets only, no tract, no institution.

THE 403. ffiec.cfpb.gov rejects a bare "Mozilla/5.0" User-Agent with 403 on every path, including its
own documentation page, while accepting no UA at all and accepting full browser header sets. This is
the inverse of the ESPN behaviour documented elsewhere in this project, where plain Mozilla was the
one that worked. The lesson that transfers is not the header value; it is that a 403 is a claim about
your client, not about whether the data exists.
"""
from __future__ import annotations

import csv
import io
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
API = "https://ffiec.cfpb.gov/v2/data-browser-api/view/csv?years=%s&states=%s"
HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) "
                   "Gecko/20100101 Firefox/127.0"),
    "Accept": "text/csv,*/*",
    "Accept-Language": "en-US,en;q=0.5",
}

# HMDA writes several distinct things into one text column. All of them mean "no value here", and
# treating any of them as data is its own silent failure: "1111" parses as a number.
SENTINELS = ("", "NA", "EXEMPT", "1111")

ACTION = {"1": "originated", "2": "approved_not_accepted", "3": "denied", "4": "withdrawn",
          "5": "file_closed_incomplete", "6": "purchased", "7": "preapproval_denied",
          "8": "preapproval_approved_not_accepted"}


def absent(v):
    return str(v or "").strip().upper() in tuple(s.upper() for s in SENTINELS)


def bucket(v, edges):
    try:
        x = float(str(v).strip())
    except (TypeError, ValueError):
        return ""
    for e in edges:
        if x < e:
            return "<%g" % e
    return ">=%g" % edges[-1]


def fetch(state="DE", year="2023"):
    req = urllib.request.Request(API % (year, state), headers=HEADERS)
    print("  downloading HMDA %s %s ..." % (state, year))
    raw = urllib.request.urlopen(req, timeout=600).read()
    print("  %.1f MB" % (len(raw) / 1e6))
    return list(csv.DictReader(io.StringIO(raw.decode("utf-8", "replace"))))


def reduce_rows(rows, state, year):
    out = []
    for r in rows:
        act = r.get("action_taken")
        out.append({
            "state": state, "year": year,
            "action": ACTION.get(act, "other_%s" % act),
            "originated": int(act == "1"),
            # one column per field whose ABSENCE is the thing being measured
            "has_interest_rate": int(not absent(r.get("interest_rate"))),
            "has_total_loan_costs": int(not absent(r.get("total_loan_costs"))),
            "has_dti": int(not absent(r.get("debt_to_income_ratio"))),
            "has_ltv": int(not absent(r.get("loan_to_value_ratio"))),
            "has_property_value": int(not absent(r.get("property_value"))),
            # denial_reason 10 is "not applicable"; a real code is a RECORDED reason
            "denial_reason": ("" if absent(r.get("denial_reason-1"))
                              else str(r.get("denial_reason-1")).strip()),
            "income_bucket": bucket(r.get("income"), [50, 75, 100, 150, 250]),
            "loan_bucket": bucket(r.get("loan_amount"), [15e4, 25e4, 35e4, 5e5, 1e6]),
        })
    return out


def main():
    state, year = "DE", "2023"
    if "--state" in sys.argv:
        state = sys.argv[sys.argv.index("--state") + 1].upper()
    if "--year" in sys.argv:
        year = sys.argv[sys.argv.index("--year") + 1]

    rows = reduce_rows(fetch(state, year), state, year)
    path = os.path.join(HERE, "hmda_extract.csv")
    cols = list(rows[0].keys())
    with io.open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    print("  wrote %s (%d rows)" % (path, len(rows)))
    if not rows:
        raise SystemExit("refusing to write an empty extract")   # rule 2, applied to ourselves
    return 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    raise SystemExit(main())
