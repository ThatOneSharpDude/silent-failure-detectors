"""make_extract.py — rebuild the public data extract from the private store. ONE constant to change.

RUN FROM THE PRIVATE REPO. This reads stores that are not public and writes only the reduced,
anonymised CSVs that ship. It is the single place the cutoff is defined:

    CUTOFF = "2026-09-20"          <- change this, run once, done

WHY IT EXISTS. The abstract's figures were first computed by hand and drifted twice: settlement and
late closes keep landing on rows dated before the cutoff, so re-reading the live store at the SAME
cutoff gives different answers weeks later (acted ROI read +1.60% on 30 Aug and +0.40% on 28 Sep for
an unchanged 24 Aug cutoff). The only fix is to stop reading the live store. The shipped CSVs ARE the
frozen artifact; `reproduce.py` regenerates every printed number from them at zero tolerance, and
`CUTOFF.txt` records both the row cutoff and the moment the store was read.

DEFINITIONS, each matching the private checker it replaces (`nhl-betting/reproduce.py`):

    position        non-variant row, game date <= CUTOFF (shadow A/B duplicates excluded)
    prop            the row resolves to a player (clv_row_filter.resolve_player)
    acted           tier in LEAN / OFFICIAL / BET; everything else was declined
    has_close       clv_pp is not None  (a captured close that never scored is still no close)
    capture failure LOGGED at or before the cutoff (`ts`), never filtered on game `date`: late rows
                    are appended with old game dates, so a date filter keeps growing and cannot be
                    reproduced later by anyone, including its author
    trial           rows carrying an epoch-1 `rct_arm` (gate_rct, 2026-08-13..08-24). The arm lives
                    on the frozen row; the separate assignment log did not survive
    best segment    WNBA player rows 2026-08-06..2026-08-24 — the window in which the
                    `wnba_prop_scoring` bar sat above what the shrink cap can emit. It is the
                    defect's own window, fixed on 2026-08-24, and does not move with CUTOFF.

WHAT IS DELIBERATELY NOT HERE. No player, game, team, book, market description, line, price, model
probability, edge, hypothesis text, or calendar date. Day indices are RELATIVE. Bet results appear
only as per-day aggregates. The salt is generated fresh each run and discarded, so the tokens cannot
be inverted by anyone, including us. The paper makes no claim about predictive edge, so none of the
withheld fields are needed to check any result in it.
"""
from __future__ import annotations

import collections
import csv
import datetime
import hashlib
import io
import json
import os
import shutil
import sys

# ── THE ONE CONSTANT ─────────────────────────────────────────────────────────────────────────────
CUTOFF = "2026-09-20"

# Fixed windows: properties of the defects themselves, not of the freeze.
SEGMENT_WINDOW = ("2026-08-06", "2026-08-24")   # unreachable wnba_prop_scoring bar
RCT_EPOCH1 = ("2026-08-13", "2026-08-23")       # gate_rct epoch 1 (raw-field hash); epoch 2 from 08-24
SHRINK_CAP_PP = 13.0

ACTED = ("LEAN", "OFFICIAL", "BET")
PRIVATE = os.path.expanduser("~/Documents/nhl-betting")
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "data")
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


def _date(r):
    return str(r.get("date") or "")[:10]


def _acted(r):
    return str(r.get("tier") or "").upper() in ACTED


def _writer(name, header):
    fh = io.open(os.path.join(OUT, name), "w", encoding="utf-8", newline="")
    w = csv.writer(fh)
    w.writerow(header)
    return fh, w


def write_positions(rows, didx, crf):
    fh, w = _writer("positions.csv", ["day", "sport", "is_prop", "acted", "has_close", "graded"])
    with fh:
        for r in rows:
            w.writerow([didx[_date(r)], r.get("sport"),
                        int(bool(str(crf.resolve_player(r) or "").strip())),
                        int(_acted(r)),
                        int(r.get("clv_pp") is not None),
                        int(bool(str(r.get("paper_outcome") or r.get("result") or "").strip()))])


def write_daily_pnl(rows, didx):
    """Per-DAY aggregates only. A day's net is not tradeable; an individual position would be."""
    agg = collections.defaultdict(collections.Counter)
    for r in rows:
        res = r.get("paper_outcome") or r.get("outcome")
        p = _payout(r.get("entry_odds"))
        if res not in ("WIN", "LOSS") or p is None:
            continue
        k = (didx[_date(r)], "acted" if _acted(r) else "declined")
        agg[k]["staked"] += 1
        agg[k]["returned"] += (1.0 + p) if res == "WIN" else 0.0
    fh, w = _writer("daily_pnl.csv", ["day", "population", "staked_units", "returned_units"])
    with fh:
        for (d, pop), v in sorted(agg.items()):
            w.writerow([d, pop, v["staked"], round(v["returned"], 4)])


def write_capture_failures(didx):
    """two_sided is preserved: a one-sided quote cannot be devigged, so it cannot stand in for a
    close. Dropping that flag once turned the bracketing figure into 11.19%."""
    miss = [m for m in _load("capture_misses.jsonl")
            if str(m.get("ts") or "")[:10] and str(m.get("ts"))[:10] <= CUTOFF]
    fh, w = _writer("capture_failures.csv", ["day", "sport", "why", "n_available", "n_two_sided",
                                             "our_rung_available", "brackets_two_sided"])
    with fh:
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
            has = int(ours is not None and any(abs(x - ours) < 1e-9 for x, _ in L))
            lo = ours is not None and any(x < ours for x, ts in L if ts)
            hi = ours is not None and any(x > ours for x, ts in L if ts)
            w.writerow([didx.get(_date(m), ""), m.get("sport"), m.get("why"),
                        len(L), sum(1 for _, ts in L if ts), has, int(lo and hi)])
    return len(miss)


def write_identity_drift(rows, didx, crf):
    """The raw-field key epoch 1 of the gate trial hashed, beside the canonical identity."""
    fh, w = _writer("identity_drift.csv", ["day", "rct_epoch1", "raw_field_token", "canonical_token"])
    with fh:
        for r in rows:
            if not r.get("player"):
                continue
            d = _date(r)
            w.writerow([didx[d], int(RCT_EPOCH1[0] <= d <= RCT_EPOCH1[1]),
                        _tok("R", "|".join(str(r.get(k) or "")
                                           for k in ("player", "market", "line", "side"))),
                        _tok("C", crf.pick_identity(r))])


def write_best_segment(rows, didx):
    lo, hi = SEGMENT_WINDOW
    fh, w = _writer("best_segment.csv", ["day", "reached_bet_tier", "pinned_at_shrink_cap"])
    n = 0
    with fh:
        for r in rows:
            if r.get("sport") == "WNBA" and r.get("player") and lo <= _date(r) <= hi:
                w.writerow([didx[_date(r)], int(_acted(r)),
                            int(abs(float(r.get("edge_pp") or 0) - SHRINK_CAP_PP) < 1e-6)])
                n += 1
    return n


def write_registry(snapshot):
    """Test count and outcomes only. Hypothesis text is withheld: it names players and segments."""
    reg = [r for r in _load("hypothesis_registry.jsonl") if str(r.get("ts") or "") <= snapshot]
    fh, w = _writer("registry.csv", ["seq", "kind", "decision"])
    with fh:
        for i, r in enumerate(reg):
            w.writerow([i, r.get("kind") or "", r.get("decision") or ""])
    return len(reg)


TRIAL_SALT = "gate-rct-2026-08-13"
TRIAL_FIELDS = ("date", "game", "market", "side", "line", "player", "stat")


def _coin(key):
    u = int(hashlib.sha256(key.encode("utf-8")).hexdigest()[:8], 16) / 0xFFFFFFFF
    return "ARM_BET" if u < 0.5 else "ARM_HOLD"


def write_trial(rows, didx, crf):
    """Epoch 1 of the gate trial: the arm stamped on each frozen row, and whether re-hashing that
    row's own fields reproduces it. The exact epoch-1 key construction is not recorded anywhere, so
    every plausible construction is tried and each gets its own column; the claim is the RANGE."""
    keys = {
        "match_raw_fields": lambda r: TRIAL_SALT + "|" + "|".join(str(r.get(f)) for f in TRIAL_FIELDS),
        "match_raw_fields_blank": lambda r: TRIAL_SALT + "|" + "|".join(str(r.get(f) or "")
                                                                       for f in TRIAL_FIELDS),
        "match_canonical": lambda r: TRIAL_SALT + "|" + "|".join(str(x) for x in crf.pick_identity(r)),
        "match_canonical_epoch": lambda r: TRIAL_SALT + "|e1|" + "|".join(str(x)
                                                                         for x in crf.pick_identity(r)),
    }
    trial = [r for r in rows if r.get("rct_arm") in ("ARM_BET", "ARM_HOLD")
             and int(r.get("rct_epoch") or 1) == 1]
    fh, w = _writer("trial_epoch1.csv", ["day", "bet_token", "stored_arm"] + list(keys))
    with fh:
        for r in trial:
            w.writerow([didx[_date(r)], _tok("B", "|".join([_date(r)] + [str(x) for x in crf.pick_identity(r)])),
                        r["rct_arm"]] + [int(_coin(fn(r)) == r["rct_arm"]) for fn in keys.values()])
    return len(trial)


def copy_clinicaltrials():
    """The second external domain. Pure function of a cached, public ClinicalTrials.gov sample."""
    dst = os.path.join(HERE, "datasets", "clinicaltrials")
    os.makedirs(os.path.join(dst, "data"), exist_ok=True)
    shutil.copyfile(os.path.join(PRIVATE, "data", "clinicaltrials_sample.jsonl"),
                    os.path.join(dst, "data", "clinicaltrials_sample.jsonl"))
    shutil.copyfile(os.path.join(PRIVATE, "external_clinicaltrials.py"),
                    os.path.join(dst, "clinicaltrials.py"))


def main():
    sys.path.insert(0, PRIVATE)
    import clv_row_filter as crf

    snapshot = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(OUT, exist_ok=True)
    rows = [r for r in _load("paper_clv.jsonl") if _date(r) and _date(r) <= CUTOFF
            and not crf.is_variant(r)]
    days = sorted({_date(r) for r in rows})
    didx = {d: i for i, d in enumerate(days)}
    print("cutoff %s : %d positions over %d pricing days" % (CUTOFF, len(rows), len(days)))

    write_positions(rows, didx, crf)
    write_daily_pnl(rows, didx)
    n_miss = write_capture_failures(didx)
    write_identity_drift(rows, didx, crf)
    n_seg = write_best_segment(rows, didx)
    n_reg = write_registry(snapshot)
    n_trial = write_trial(rows, didx, crf)
    copy_clinicaltrials()
    print("trial epoch-1 positions: %d" % n_trial)
    print("capture failures logged by cutoff: %d   best segment rows: %d   registry tests: %d"
          % (n_miss, n_seg, n_reg))

    io.open(os.path.join(OUT, "CUTOFF.txt"), "w", encoding="utf-8").write(
        "Positions dated on or before %s (%d pricing days); store read at %s.\n"
        "The live store keeps settling old rows, so a later read at the same cutoff differs.\n"
        "This extract, not the store, is the record every figure in the paper is computed from.\n"
        "Day indices are RELATIVE (day 0 = first day in window) and carry no calendar alignment.\n"
        "The salt is generated per run and discarded; tokens cannot be inverted.\n"
        % (CUTOFF, len(days), snapshot))
    print("wrote %s" % OUT)
    print("NEXT: run reproduce.py and update any paper figure it reports as MISMATCH.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
