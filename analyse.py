#!/usr/bin/env python3
"""Turn the git history of baseline.json into a drift rate.

"The git log is the dataset" is only true if something reads it. This walks
every commit that touched the baseline, diffs consecutive versions, and reports
how often definitions actually changed - per server, and overall.

    python3 analyse.py            # summary
    python3 analyse.py --by-server

Standard library only, like everything else here.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
from collections import Counter, OrderedDict

BASELINE = "baseline.json"


def revisions():
    """Every commit that touched the baseline, oldest first."""
    result = subprocess.run(
        ["git", "log", "--reverse", "--format=%H %aI", "--", BASELINE],
        capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit("not a git repository, or git is unavailable - the history "
                 "of {} is the dataset, so there is nothing to read without "
                 "it".format(BASELINE))
    return [line.split(" ", 1) for line in result.stdout.strip().splitlines() if line]


def at(sha):
    blob = subprocess.run(["git", "show", "{}:{}".format(sha, BASELINE)],
                          capture_output=True, text=True)
    if blob.returncode != 0:
        return None
    try:
        return json.loads(blob.stdout)
    except ValueError:
        return None


def tool_hashes(document):
    """{server: {tool: composite_hash}} for one baseline revision."""
    out = {}
    for identity, server in (document.get("servers") or {}).items():
        out[identity] = {name: rec.get("composite_hash")
                         for name, rec in (server.get("tools") or {}).items()}
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--by-server", action="store_true")
    args = parser.parse_args(argv)

    if not os.path.exists(BASELINE):
        sys.exit("no {} here; run this from the repository root".format(BASELINE))

    history = revisions()
    if len(history) < 2:
        print("Only {} baseline revision(s) so far. A rate needs at least two,\n"
              "and a useful one needs weeks.".format(len(history)))
        observed(0)
        return 0

    changed = Counter()
    appeared = Counter()
    removed = Counter()
    events = 0
    previous = tool_hashes(at(history[0][0]) or {})

    for sha, when in history[1:]:
        document = at(sha)
        if document is None:
            continue
        current = tool_hashes(document)
        for identity in set(previous) | set(current):
            before, after = previous.get(identity, {}), current.get(identity, {})
            for name in set(before) & set(after):
                if before[name] != after[name]:
                    changed[identity] += 1
                    events += 1
            for name in set(after) - set(before):
                appeared[identity] += 1
                events += 1
            for name in set(before) - set(after):
                removed[identity] += 1
                events += 1
        previous = current

    print("Baseline revisions : {}".format(len(history)))
    print("First observation  : {}".format(history[0][1][:10]))
    print("Latest observation : {}".format(history[-1][1][:10]))
    print("Definition changes : {} (modified {}, appeared {}, removed {})".format(
        events, sum(changed.values()), sum(appeared.values()), sum(removed.values())))
    observed(events)

    if args.by_server:
        latest = at(history[-1][0]) or {}
        watched = windows(latest, history[-1][1])
        totals = Counter()
        for counter in (changed, appeared, removed):
            totals.update(counter)
        print("\nBy server (window = days since first observed):")
        print("  {:<44} {:>5} {:>7} {:>9}".format("server", "days", "changes", "per day"))
        order = sorted(watched, key=lambda i: (-totals[i], i))
        for identity in order:
            days = watched[identity]
            count = totals[identity]
            print("  {:<44} {:>5} {:>7} {:>9}".format(
                identity[:44], days, count,
                "{:.3f}".format(count / days) if days else "-"))
        unwatched = sorted(set(totals) - set(watched))
        for identity in unwatched:
            print("  {:<44} {:>5} {:>7} {:>9}".format(identity[:44], "?", totals[identity], "-"))
    return 0


def observed(events):
    """The denominator. A count of rug pulls means nothing without it."""
    if not os.path.exists("observations.csv"):
        return
    with open("observations.csv") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        return
    # The column was renamed when "reachable" started being measured rather
    # than copied from the baseline; tolerate both spellings so old rows count.
    def watched(row):
        for key in ("watched", "servers"):
            if row.get(key):
                return int(row[key])
        return 0

    server_days = sum(watched(r) for r in rows)
    print("Observation days   : {} ({} server-days)".format(len(rows), server_days))
    if server_days:
        print("Change rate        : {:.3f} per server-day".format(events / server_days))


def windows(document, latest_date):
    """Days each server has actually been watched.

    The watchlist grows, so servers have different observation windows. Dividing
    by a flat server-day total would credit a server added last week with the
    whole run's quiet time - an error in the direction that flatters the result,
    which is the worst direction for it to be wrong in.
    """
    import datetime

    out = {}
    for identity, record in (document.get("servers") or {}).items():
        first = (record.get("first_observed") or "")[:10]
        if not first:
            continue
        try:
            start = datetime.date.fromisoformat(first)
            end = datetime.date.fromisoformat(latest_date[:10])
        except ValueError:
            continue
        out[identity] = max((end - start).days, 0) + 1
    return out


if __name__ == "__main__":
    sys.exit(main())
