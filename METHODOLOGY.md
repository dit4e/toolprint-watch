# Methodology — MCP tool-definition drift monitor

## What this watches

Every day, the collector connects to each server in [`servers.json`](servers.json),
asks for its `tools/list`, and records the tool definitions each server broadcasts
to every client — names, titles, descriptions, input/output schemas, annotations.
It diffs today's surface against a stored baseline and records what changed. All of
it comes from the servers' own published packages, installed as any user would,
with no credentials.

## The three tiers (and why frozen is a control group)

The watchlist is not a flat list. Its 36 servers fall into three tiers, defined in
[`server-tiers.json`](server-tiers.json) and classified by the actual package each
entry runs (verified 2026-09-27):

| Tier | Count | What it is | What drift means |
|---|---:|---|---|
| **reference** | 7 | Actively maintained MCP steering-group reference servers | Expected churn — the baseline for "normal" change |
| **frozen** | 7 | Archived/deprecated reference servers (moved to `modelcontextprotocol/servers-archived`) | **Signal, not noise** — these should not change |
| **vendor-community** | 22 | Third-party vendor and community servers | Where real capability change is most likely |

The **frozen tier is the control group.** These servers are archived and should be
inert. If a definition on a frozen server changes, it is not routine maintenance —
it points to something upstream moving: a transitive dependency, a re-publish under
the same version, or a shared SDK whose version the server echoes rather than its
own. A drift signal that appears in the frozen tier is therefore interpreted
differently from the same signal in the reference or vendor tiers.

### Provenance of the frozen set

The seven frozen servers are exactly the `@modelcontextprotocol/server-*` reference
servers that the MCP project moved out of the active `servers` repository into
`servers-archived` (confirmed against the servers repository, 2026-09-27):
puppeteer, github, postgres, gitlab, slack, google-maps, and brave-search (the
original, since replaced by Brave's own maintained server, which is tracked
separately in the vendor tier as `brave-search-new`).

## Why tiers live in a separate file

The collector and `toolprint` read only `servers.json["mcpServers"]`. Tier tags are
kept in `server-tiers.json` so classification can never alter the live config that
the daily run feeds to MCP clients. Reading tiers is a pure overlay by server name.

## What a reader should take from the data

- **Change is constant** across the reference and vendor tiers — most days carry
  several tool-definition changes that no downstream operator reviewed.
- **The frozen control mostly holds still**, which is what makes any movement there
  worth a second look.
- Effects are classified read / write / external / irreversible / unknown as a
  matter of *visibility* — knowing which calls change state — not as a safety
  verdict on any server.
