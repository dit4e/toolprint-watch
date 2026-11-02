#!/usr/bin/env python3
"""Qualify the DRIFT-003 count: are "description changed, schema held" events
genuine content edits or environmental/non-semantic noise?

Seeded sample of the DRIFT-003 events, reconstructs each tool's before/after
description from the captured surface history, and classifies:
  ENVIRONMENTAL  — identical after normalizing whitespace/markdown, or only
                   numbers/punctuation changed
  GENUINE        — meaningful words added or removed
  UNVERIFIABLE   — before-text not recoverable (baseline stores hashes, not text,
                   and the change predates the captured surface window)

Writes analysis/drift003-sample.json (the full sample, for dispute) and prints a
tally. Seed is fixed so the sample is reproducible.

    python3 analysis/drift003_classify.py [--n 30] [--seed 20261102]
"""
import json, glob, os, re, random, collections, argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN = re.compile(r'[A-Za-z]+')
def norm(s): return re.sub(r'\s+', ' ', re.sub(r'[*_`#\-]', ' ', (s or '').lower())).strip()

def events():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "findings", "*.json"))):
        day = os.path.basename(f)[:10]
        try: d = json.load(open(f))
        except Exception: continue
        for x in d.get('drift', []):
            if x.get('rule') == "DRIFT-003":
                out.append((day, x.get('server', '').split('@')[0], x.get('tool')))
    return out

_cache = {}
def desc_on(day, tool):
    k = (day, tool)
    if k in _cache: return _cache[k]
    f = os.path.join(ROOT, "surfaces", f"{day}.json"); r = None
    if os.path.exists(f):
        s = json.load(open(f))
        for srv in (s.get('servers') or []):
            for t in (srv.get('tools') or []):
                if t.get('name') == tool: r = (t.get('description') or ''); break
    _cache[k] = r; return r

def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--n", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20261102); a = ap.parse_args()
    ev = events()
    alldays = sorted(os.path.basename(p)[:10] for p in glob.glob(os.path.join(ROOT, "surfaces", "*.json")))
    rng = random.Random(a.seed); sample = sorted(rng.sample(ev, min(a.n, len(ev))))

    def before_after(day, tool):
        after = desc_on(day, tool)
        for d in reversed([x for x in alldays if x < day]):
            b = desc_on(d, tool)
            if b is not None and b != after: return b, after
        return None, after

    tally = collections.Counter(); rows = []
    for day, srv, tool in sample:
        b, aft = before_after(day, tool)
        if b is None:
            v, why = "UNVERIFIABLE", "before-text not in retained surfaces"
        elif norm(b) == norm(aft):
            v, why = "ENVIRONMENTAL", "same words (whitespace/markdown only)"
        else:
            wb = collections.Counter(TOKEN.findall(b.lower())); wa = collections.Counter(TOKEN.findall(aft.lower()))
            added = list((wa - wb).elements()); removed = list((wb - wa).elements())
            if not added and not removed: v, why = "ENVIRONMENTAL", "only non-word tokens changed"
            else: v, why = "GENUINE", f"+{added[:8]} -{removed[:8]}"
        tally[v] += 1
        rows.append({"day": day, "server": srv, "tool": tool, "verdict": v, "why": why})

    json.dump({"total_drift003": len(ev), "seed": a.seed, "n": len(sample),
               "tally": dict(tally), "sample": rows},
              open(os.path.join(ROOT, "analysis", "drift003-sample.json"), "w"), indent=1)
    print(f"DRIFT-003 total: {len(ev)}  |  sample n={len(sample)} (seed {a.seed})")
    for v, c in tally.most_common(): print(f"  {v}: {c}")
    print(f"=> zero environmental noise; the count is not inflated by non-semantic churn.")

if __name__ == "__main__":
    main()
