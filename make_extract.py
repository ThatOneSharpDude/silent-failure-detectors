"""make_extract.py — rebuild the public data extract from the private store. ONE constant to change.

RUN FROM THE PRIVATE REPO. This reads stores that are not public and writes only the reduced,
anonymised CSVs that ship. It is the single place the cutoff is defined:

    CUTOFF = "2026-09-20"          <- change this, run once, done

WHY IT EXISTS. The abstract's figures were first computed by hand on 2026-08-25 and had silently
drifted by 2026-08-30 — settlement and miss-logging keep landing on rows dated before the cutoff, so
"graded" moved 7,160 -> 7,767 and the ROI pair moved -0.47/+1.93 -> -1.40/+1.60. A paper about
measurement drifting away from its own data is not a paper you want to submit. The shipped CSVs are
now the frozen artifact and `reproduce.py` regenerates every printed number from them, so the two
cannot disagree again.

WHAT IS DELIBERATELY NOT HERE. No player, game, team, book, market description, line, price, model
probability, edge, or calendar date. Day indices are RELATIVE. Bet results appear only as per-day
aggregates. The salt is generated fresh each run and discarded, so the tokens cannot be inverted by
anyone, including us. The paper makes no claim about predictive edge, so none of the withheld fields
are needed to check any result in it.
"""
from __future__ import annotations

import collections
import csv
import hashlib
import io
import json
import os
import sys

# ── THE ONE CONSTANT ─────────────────────────────────────────────────────────────────────────────
CUTOFF = "2026-08-24"

PRIVATE = os.path.expanduser("~/Documents/nhl-betting")
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
SALT = os.urandom(16).hex()          # ephemeral by design; never written to disk


def _tok(prefix, s):
    return "" if not s else prefix + hashlib.sha256((SALT + "|" + str(s)).encode()).hexdigest()[:10]


def _load(name):
    out = []
    with io.open(os.path.join(PRIVATE, name), encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.strip().startswith("{"):
                try:
                    out.append(json.loads(line))
                except ValueError:
                    continue
    return out


def _payout(o):
    try:
        v = int(str(o).replace("+", "").strip())
    except (TypeError, ValueError):
        return None
    return v / 100.0 if v > 0 else 100.0 / (-v)


def main():
    sys.path.insert(0, PRIVATE)
    import clv_row_filter as crf

    os.makedirs(OUT, exist_ok=True)
    rows = [r for r in _load("paper_clv.jsonl")
            if str(r.get("date"))[:10] <= CUTOFF and not crf.is_variant(r)]
    days = sorted({str(r.get("date"))[:10] for r in rows})
    didx = {d: i for i, d in enumerate(days)}
    print("cutoff %s : %d rows over %d pricing days" % (CUTOFF, len(rows), len(days)))

    with io.open(os.path.join(OUT, "positions.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["day", "sport", "market_class", "acted", "has_close", "graded"])
        for r in rows:
            w.writerow([didx[str(r.get("date"))[:10]], r.get("sport"), r.get("market_class"),
                        int(str(r.get("tier", "")).upper() in ("LEAN", "OFFICIAL")),
                        int(r.get("closing_raw") is not None),
                        int((r.get("paper_outcome") or r.get("outcome"))
                            in ("WIN", "LOSS", "PUSH", "VOID"))])

    # per-DAY aggregates only. A day's net P&L is not tradeable; an individual position would be.
    agg = collections.defaultdict(collections.Counter)
    for r in rows:
        res = r.get("paper_outcome") or r.get("outcome")
        p = _payout(r.get("entry_odds"))
        if res not in ("WIN", "LOSS") or p is None:
            continue
        pop = "acted" if str(r.get("tier", "")).upper() in ("LEAN", "OFFICIAL") else "declined"
        k = (didx[str(r.get("date"))[:10]], pop)
        agg[k]["staked"] += 1
        agg[k]["returned"] += (1.0 + p) if res == "WIN" else 0.0
    with io.open(os.path.join(OUT, "daily_pnl.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["day", "population", "staked_units", "returned_units"])
        for (d, pop), v in sorted(agg.items()):
            w.writerow([d, pop, v["staked"], round(v["returned"], 4)])

    # two_sided is preserved: a one-sided quote cannot be devigged, so it cannot stand in for a
    # close. Dropping that flag once turned the 0.41% bracketing figure into 11.19%.
    miss = [m for m in _load("capture_misses.jsonl") if str(m.get("date"))[:10] <= CUTOFF]
    with io.open(os.path.join(OUT, "capture_failures.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["day", "sport", "why", "n_available", "n_two_sided",
                    "our_rung_available", "brackets_two_sided"])
        for m in miss:
            L = []
            for a in (m.get("available") or []):
                try:
                    L.append((float(a[0]), bool(a[1]) if len(a) > 1 else True))
                except Exception:
                    continue
            try:
                ours = float(m.get("line"))
            except (TypeError, ValueError):
                ours = None
            has = int(ours is not None and any(abs(x - ours) < 1e-6 for x, _ in L))
            lo = ours is not None and any(x < ours for x, ts in L if ts)
            hi = ours is not None and any(x > ours for x, ts in L if ts)
            w.writerow([didx.get(str(m.get("date"))[:10], ""), m.get("sport"), m.get("why"),
                        len(L), sum(1 for _, ts in L if ts), has, int(lo and hi)])

    with io.open(os.path.join(OUT, "identity_drift.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["day", "raw_field_token", "canonical_token"])
        for r in rows:
            if not r.get("player"):
                continue
            w.writerow([didx[str(r.get("date"))[:10]],
                        _tok("R", "|".join(str(r.get(k) or "")
                                           for k in ("player", "market", "line", "side"))),
                        _tok("C", crf.pick_identity(r))])

    io.open(os.path.join(OUT, "CUTOFF.txt"), "w", encoding="utf-8").write(
        "All data frozen at %s (%d pricing days).\n"
        "Day indices are RELATIVE (day 0 = first day in window) and carry no calendar alignment.\n"
        "The salt is generated per run and discarded; tokens cannot be inverted.\n" % (CUTOFF, len(days)))
    print("wrote %s" % OUT)
    print("NEXT: run reproduce.py and update any paper figure it reports as MISMATCH.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
