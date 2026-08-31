"""Shared vocabulary. A detector reports; it does not decide what to do about the report."""
from __future__ import annotations

import collections

# CLEAN  nothing to say
# WATCH  the condition is present but within what the caller declared tolerable
# ALARM  the condition is present and the number it corrupts is being read by someone
LEVELS = ("CLEAN", "WATCH", "ALARM")


class Finding(object):
    __slots__ = ("detector", "level", "headline", "detail")

    def __init__(self, detector, level, headline, detail=None):
        if level not in LEVELS:
            raise ValueError("level must be one of %r" % (LEVELS,))
        self.detector, self.level = detector, level
        self.headline, self.detail = headline, dict(detail or {})

    def __repr__(self):
        return "<%s %s: %s>" % (self.detector, self.level, self.headline)

    def render(self):
        out = ["  [%-5s] %-22s %s" % (self.level, self.detector, self.headline)]
        for k, v in sorted(self.detail.items()):
            out.append("            %-28s %s" % (k, v))
        return "\n".join(out)


def counts(rows, key):
    c = collections.Counter()
    for r in rows:
        c[r.get(key)] += 1
    return c


def run_all(findings):
    """Print findings and return a process exit code. ALARM is the only failing level."""
    print("=" * 92)
    print("  SILENT-FAILURE DETECTORS")
    print("=" * 92)
    worst = 0
    for f in findings:
        print(f.render())
        worst = max(worst, LEVELS.index(f.level))
    print("-" * 92)
    print("  %d finding(s); worst level %s" % (len(findings), LEVELS[worst]))
    return 1 if LEVELS[worst] == "ALARM" else 0
