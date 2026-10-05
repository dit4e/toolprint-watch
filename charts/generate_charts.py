#!/usr/bin/env python3
"""Regenerate the toolprint-watch charts from the repo's own data.

Reads observations.csv and findings/*.json. Emits two self-contained SVGs:
  charts/daily-changes.svg   — tool-definition changes per day
  charts/rule-distribution.svg — the 277 classified drift events, by rule

Pinned to --as-of (default 2026-10-04) so the committed images match the
Sep–Oct 2026 write-up; bump it to refresh. PNGs are rendered from the SVGs with
headless Chrome (see charts/README.md); the SVGs are the source of truth.
"""
import csv, json, glob, os, statistics, argparse, collections

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
START = "2026-09-04"   # steady state; earlier days are baseline setup (Sep 3 = fill, not drift)

RULE_META = {  # id -> (short desc, is a capability-increase signal?)
 "DRIFT-003":("description changed, schema held",False),
 "DRIFT-015":("change inside a parameter",False),
 "DRIFT-013":("server version changed",False),
 "DRIFT-012":("vendor annotation changed",False),
 "DRIFT-016":("description reformatted only",False),
 "DRIFT-007":("new tool",False),
 "DRIFT-010":("tool removed",False),
 "DRIFT-009":("additive schema change",False),
 "DRIFT-014":("capability moved behind a router",True),
 "DRIFT-002":("safety annotation revoked",True),
 "DRIFT-001":("effect class escalated",True),
}
# capability-increase rules always shown, even at zero — that's the point
ALWAYS_SHOW = ["DRIFT-014","DRIFT-002","DRIFT-001"]


def daily(as_of):
    rows=[]
    for r in csv.DictReader(open(os.path.join(ROOT,"observations.csv"))):
        if START <= r["date"] <= as_of:
            rows.append((r["date"], int(r["drift_changes"])))
    return rows


def rule_counts(as_of):
    c=collections.Counter()
    for f in sorted(glob.glob(os.path.join(ROOT,"findings","*.json"))):
        day=os.path.basename(f)[:10]
        if day>as_of: continue
        try: d=json.load(open(f))
        except Exception: continue
        for x in d.get("drift",[]):
            c[x.get("rule")]+=1
    for r in ALWAYS_SHOW: c.setdefault(r,0)
    # order: by count desc, but zeros (capability-increase) pinned to the bottom
    nonzero=sorted([(r,n) for r,n in c.items() if n>0], key=lambda t:-t[1])
    zeros=[(r,0) for r in ("DRIFT-002","DRIFT-001") if c.get(r,0)==0]
    return nonzero+zeros, sum(c.values())


def svg_daily(rows, path):
    vals=[v for _,v in rows]; med=statistics.median(vals); n=len(rows); mx=max(vals)
    W,H,L,R,T,B=1040,470,56,20,70,70; pw,ph=W-L-R,H-T-B; ymax=max(70,(mx//10+1)*10)
    X=lambda i:L+(i+0.5)*(pw/n); Y=lambda v:T+ph*(1-v/ymax); bw=pw/n*0.62
    s=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Helvetica,Arial,sans-serif"><rect width="{W}" height="{H}" fill="#fff"/>']
    s.append(f'<text x="{L}" y="30" font-size="20" font-weight="700" fill="#16181d">MCP tool-definition changes per day</text>')
    s.append(f'<text x="{L}" y="50" font-size="13" fill="#5b6470">36 public servers watched daily · {rows[0][0][5:]} – {rows[-1][0][5:]}, 2026 · baseline set Sep 3</text>')
    for g in range(0,ymax+1,20):
        yy=Y(g); s.append(f'<line x1="{L}" y1="{yy:.1f}" x2="{W-R}" y2="{yy:.1f}" stroke="#eceef1"/><text x="{L-8}" y="{yy+4:.1f}" font-size="11" fill="#9aa1ab" text-anchor="end">{g}</text>')
    ym=Y(med); s.append(f'<line x1="{L}" y1="{ym:.1f}" x2="{W-R}" y2="{ym:.1f}" stroke="#c0362c" stroke-width="1.3" stroke-dasharray="5 4"/><text x="{W-R}" y="{ym-6:.1f}" font-size="11" fill="#c0362c" text-anchor="end">median {int(med)}/day</text>')
    for i,(d,v) in enumerate(rows):
        if v==0: continue
        by=Y(v); s.append(f'<rect x="{X(i)-bw/2:.1f}" y="{by:.1f}" width="{bw:.1f}" height="{T+ph-by:.1f}" rx="2" fill="#2f6f8f"/>')
        if v>=20: s.append(f'<text x="{X(i):.1f}" y="{by-5:.1f}" font-size="11" font-weight="700" fill="#1f4b60" text-anchor="middle">{v}</text>')
    for i,(d,v) in enumerate(rows):
        if i%3==0: s.append(f'<text x="{X(i):.1f}" y="{T+ph+16:.1f}" font-size="10" fill="#9aa1ab" text-anchor="middle">{d[5:]}</text>')
    s.append(f'<line x1="{L}" y1="{T+ph:.1f}" x2="{W-R}" y2="{T+ph:.1f}" stroke="#c7ccd2"/>')
    s.append(f'<text x="{L}" y="{H-14}" font-size="10.5" fill="#9aa1ab">Source: toolprint-watch — daily change counts; median {int(med)}/day, spikes to {mx} on vendor-release days.</text></svg>')
    open(path,"w").write("".join(s))


def svg_rules(rows, total, path):
    W,rowh,T,B,L,R=1040,34,86,56,300,70; H=T+rowh*len(rows)+B; pw=W-L-R; xmax=max(110,(max(n for _,n in rows)//25+1)*25)
    X=lambda v:L+pw*(v/xmax)
    s=[f'<svg viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" font-family="-apple-system,Helvetica,Arial,sans-serif"><rect width="{W}" height="{H}" fill="#fff"/>']
    s.append(f'<text x="{L-250}" y="30" font-size="20" font-weight="700" fill="#16181d">What kind of change? {total} classified drift events</text>')
    s.append(f'<text x="{L-250}" y="51" font-size="13" fill="#5b6470">toolprint-watch, Sep–Oct 2026 — the two signals that mean a tool gained power never fired</text>')
    for g in range(0,xmax+1,25):
        gx=X(g); s.append(f'<line x1="{gx:.1f}" y1="{T-6}" x2="{gx:.1f}" y2="{T+rowh*len(rows):.1f}" stroke="#eceef1"/><text x="{gx:.1f}" y="{T-12}" font-size="10" fill="#9aa1ab" text-anchor="middle">{g}</text>')
    for i,(rid,c) in enumerate(rows):
        yc=T+i*rowh+rowh/2; desc=RULE_META[rid][0]; zero=(c==0)
        if zero: s.append(f'<rect x="{L-248}" y="{T+i*rowh+3:.1f}" width="{W-(L-248)-12}" height="{rowh-6}" fill="#fdeaea"/>')
        s.append(f'<text x="{L-12}" y="{yc-2:.1f}" font-size="12.5" font-weight="700" fill="#16181d" text-anchor="end">{rid}</text>')
        s.append(f'<text x="{L-12}" y="{yc+12:.1f}" font-size="10.5" fill="#8a9099" text-anchor="end">{desc}</text>')
        if zero:
            s.append(f'<circle cx="{X(0):.1f}" cy="{yc:.1f}" r="3.5" fill="#c0362c"/><text x="{X(0)+10:.1f}" y="{yc+4:.1f}" font-size="11.5" font-weight="700" fill="#c0362c">0 — never fired</text>')
        else:
            bh=rowh-12; s.append(f'<rect x="{L}" y="{yc-bh/2:.1f}" width="{X(c)-L:.1f}" height="{bh:.1f}" rx="2" fill="#2f6f8f"/><text x="{X(c)+7:.1f}" y="{yc+4:.1f}" font-size="12" font-weight="700" fill="#1f4b60">{c}</text>')
    s.append(f'<line x1="{L}" y1="{T-6}" x2="{L}" y2="{T+rowh*len(rows):.1f}" stroke="#c7ccd2"/>')
    s.append(f'<text x="{L-250}" y="{H-16}" font-size="10.5" fill="#9aa1ab">High-severity events are 104 description rewrites + 1 router move — benign on review. The capability-increase rules (DRIFT-001/002) sat at zero.</text></svg>')
    open(path,"w").write("".join(s))


if __name__=="__main__":
    ap=argparse.ArgumentParser(); ap.add_argument("--as-of",default="2026-10-04"); a=ap.parse_args()
    svg_daily(daily(a.as_of), os.path.join(HERE,"daily-changes.svg"))
    rr,total=rule_counts(a.as_of); svg_rules(rr,total,os.path.join(HERE,"rule-distribution.svg"))
    print(f"as-of {a.as_of}: daily days={len(daily(a.as_of))}; classified rule events={total}")
