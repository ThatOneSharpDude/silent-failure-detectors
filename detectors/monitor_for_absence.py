"""RULE 4 -- monitor for the absence of a measurement, not only for bad measurements.

THE FAILURE. A quality metric is computed over the rows where it is defined. Rows where it could not
be computed are not bad values -- they are no value -- so they leave the average untouched. The
metric therefore reports on a subset that selected itself, and the more often measurement fails, the
healthier the surviving subset looks. There is no threshold to alert on, because nothing is out of
range; the thing that is wrong is the denominator.

SCAR. Closing-line value looked fine across the book. It was defined on 75.1% of prop positions, and
the missing rows were not random: on the same day, positions taken lacked a close 8.7 points less
often than positions declined. Of 20,060 line-movement failures, the rung we had taken was still
quoted in ZERO, and only 0.33% had two-sided rungs on both sides to interpolate between; in 119,001
more the player had no market at all. So the missingness is not a polling-rate problem with an
engineering fix -- the price does not exist to be captured. The metric was undefined, not noisy, and
every average computed over it was an average over a subset the system itself selected.

A WARNING ABOUT THIS DETECTOR'S OWN OUTPUT. The stratum spread it reports is pooled. When strata grow
at different times, a pooled spread mixes time with the stratum and can even reverse sign. Treat an
ALARM as "coverage depends on the stratum" and measure the size within a fixed time slice.

THE RULE. Report coverage beside every aggregate, always, in the same breath. An aggregate whose
coverage is not stated is not a result. And when coverage is low, test whether the missingness is
related to the outcome before treating the observed subset as representative.

    monitor_for_absence(rows, defined_key="has_close", floor=0.95)
"""
from __future__ import annotations

from .core import Finding

DEFAULT_FLOOR = 0.95
MNAR_GAP_PP = 5.0     # coverage differing this much between strata is a warning about the subset


def monitor_for_absence(rows, defined_key, floor=DEFAULT_FLOOR, stratum_key=None):
    rows = list(rows)
    n = len(rows)
    if not n:
        return Finding("monitor_for_absence", "WATCH", "no rows supplied", {})

    def _yes(r):
        return str(r.get(defined_key)).strip().lower() in ("1", "true", "yes")

    have = sum(1 for r in rows if _yes(r))
    cov = have / float(n)
    d = {"rows": n, "measured": have, "coverage": "%.1f%%" % (100.0 * cov),
         "floor": "%.1f%%" % (100.0 * floor)}

    if stratum_key:
        strata = {}
        for r in rows:
            strata.setdefault(r.get(stratum_key), []).append(r)
        covs = {k: sum(1 for r in v if _yes(r)) / float(len(v))
                for k, v in strata.items() if len(v) >= 30}
        if len(covs) >= 2:
            hi, lo = max(covs.values()), min(covs.values())
            d["coverage_spread_across_strata"] = "%.1fpp" % (100.0 * (hi - lo))
            if 100.0 * (hi - lo) >= MNAR_GAP_PP:
                d["note"] = ("coverage depends on %s, so the measured subset is not a random "
                             "sample of the whole" % stratum_key)

    if cov < floor:
        return Finding(
            "monitor_for_absence", "ALARM",
            "the metric is undefined on %.1f%% of rows -- any average over it describes the "
            "cases where measurement happened to succeed" % (100.0 * (1 - cov)), d)
    return Finding("monitor_for_absence", "CLEAN",
                   "coverage %.1f%% is at or above the declared floor" % (100.0 * cov), d)
