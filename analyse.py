#!/usr/bin/env python3
"""Turn the git history of baseline.json into a drift rate.

"The git log is the dataset" is only true if something reads it. This walks
every commit that touched the baseline, diffs consecutive versions, and reports
how often definitions actually changed - per server, and overall.

Adoption is not drift. A server joining the watchlist brings its whole tool
surface with it, and counting that as change measures this repository's
growth rather than the ecosystem's. Servers are compared only across
revisions in which they were already being watched; what they brought with
them is reported separately, and kept out of the rate.

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
    first = tool_hashes(at(history[0][0]) or {})
    previous = first
    # The first revision is the watchlist's own starting point, not a day on
    # which anything drifted, so its servers count as adopted too.
    adopted_servers, adopted_tools = len(first), sum(len(t) for t in first.values())
    retired_servers = retired_tools = 0
    # When each server entered the watchlist. The record's own first_observed
    # is preferred where it survives - it is a UTC stamp from the moment of
    # adoption, where a commit date is local and can land a day early. The
    # history is the fallback, because approve --refresh dropped that field
    # until toolprint 0.3.2 and no window could be computed for four days.
    first_seen = {identity: history[0][1][:10] for identity in first}

    for sha, when in history[1:]:
        document = at(sha)
        if document is None:
            continue
        current = tool_hashes(document)

        # A server entering or leaving the watchlist is adoption, not drift.
        # Counting its whole tool surface as "appeared" made adding nine
        # servers look like the largest drift event in the record - 89 of the
        # first 235 counted changes were simply the watchlist growing, and the
        # rate they fed was a rate of nothing in particular.
        for identity in set(current) - set(previous):
            adopted_servers += 1
            adopted_tools += len(current[identity])
            first_seen.setdefault(identity, when[:10])
        for identity in set(previous) - set(current):
            retired_servers += 1
            retired_tools += len(previous[identity])

        for identity in set(previous) & set(current):
            before, after = previous[identity], current[identity]
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
    print("Adopted            : {} tools across {} servers{}".format(
        adopted_tools, adopted_servers,
        ", {} tools across {} retired".format(retired_tools, retired_servers)
        if retired_servers else ""))
    print("Drift              : {} (modified {}, tools added {}, tools removed {})".format(
        events, sum(changed.values()), sum(appeared.values()), sum(removed.values())))
    observed(events)

    if args.by_server:
        latest = at(history[-1][0]) or {}
        for identity, record in (latest.get("servers") or {}).items():
            stamped = (record.get("first_observed") or "")[:10]
            if stamped and identity in first_seen:
                first_seen[identity] = stamped
        watched = windows(first_seen, observation_dates())
        totals = Counter()
        for counter in (changed, appeared, removed):
            totals.update(counter)
        print("\nDrift by server (window = days watched; adoption excluded):")
        print("  {:<44} {:>5} {:>7} {:>9}".format("server", "days", "changes", "per day"))
        # Every watched server, not only the ones that moved. The quiet ones
        # are the denominator: a list of just the servers that drifted reads
        # like every server drifts.
        for identity in sorted(watched, key=lambda i: (-totals[i], i)):
            days, count = watched[identity], totals[identity]
            print("  {:<44} {:>5} {:>7} {:>9}".format(
                identity[:44], days, count,
                "{:.3f}".format(count / days) if days else "-"))
        for identity in sorted(set(totals) - set(watched)):
            print("  {:<44} {:>5} {:>7} {:>9}".format(identity[:44], "?", totals[identity], "-"))
        quiet = sum(1 for i in watched if not totals[i])
        print("  {} of {} watched servers never drifted.".format(quiet, len(watched)))
    return 0


def observed(events):
    """The denominator. A count of rug pulls means nothing without it.

    Server-days come from observations.csv, which carries the watchlist size
    for each date - so a day when 27 servers were watched contributes 27, not
    36. Adoption is excluded from the numerator upstream, so this is a rate of
    drift per server-day and not of activity in general.
    """
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
        print("Drift rate         : {:.3f} per server-day".format(events / server_days))


def observation_dates():
    """Dates the collector actually recorded a run, oldest first."""
    if not os.path.exists("observations.csv"):
        return []
    with open("observations.csv") as fh:
        return sorted({r["date"] for r in csv.DictReader(fh) if r.get("date")})


def windows(first_seen, dates):
    """Days each server has actually been watched.

    The watchlist grows, so servers have different observation windows. Dividing
    by a flat server-day total would credit a server added last week with the
    whole run's quiet time - an error in the direction that flatters the result,
    which is the worst direction for it to be wrong in.

    Counted in observation days, not calendar days, and for the same reason:
    the collector has already missed a day, and charging a server for a day
    nobody looked at inflates its window and flatters its rate.
    """
    return {identity: sum(1 for d in dates if d >= first)
            for identity, first in first_seen.items()}


if __name__ == "__main__":
    sys.exit(main())
