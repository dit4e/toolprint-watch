# toolprint-watch

A fixed set of 27 public MCP servers, checked daily against an approved
baseline, to answer a question the product depends on: **how often do MCP tool
definitions actually change without anyone reviewing them?**

Collected with [toolprint](https://github.com/dit4e/toolprint). Split out of
that repository so a year of daily observation commits does not bury the tool's
own history.

**The git history of `baseline.json` is the dataset.** Every commit that touches
it is a definition change, with a timestamp and a diff:

```bash
git log -p --follow baseline.json
```

`observations.csv` carries the denominator — how many server-days produced no
drift — because a drift rate needs both halves and "we saw three rug pulls" is
meaningless without "out of how many observations".

## How servers were selected

Every entry was verified against the npm or PyPI registry and then **probed**:
it is here only because it actually starts and serves `tools/list` with no
credentials. Nothing was included on the strength of a package name appearing in
a directory.

Deliberately not padded. A larger list built from npm keyword search fills up
with abandoned single-author packages that will never change, which inflates the
denominator and teaches nothing. 27 servers people actually run beats 60 that
include 30 dead ones.

Three groups, on purpose:

| Group | Why |
|---|---|
| Actively published reference servers | `filesystem`, `memory`, `everything`, `sequential-thinking`, `git`, `time`, `fetch`. Released frequently, so they set the baseline rate for routine churn. |
| Archived, frozen reference servers | `puppeteer`, `github`, `postgres`. Last published 2024–2025. **Controls: if these drift, something is wrong.** |
| Vendor and community servers | Where a real rug pull would most plausibly appear. |

## The finding that shaped this list

Of 18 well-known public remote MCP endpoints probed, **two** served `tools/list`
without credentials — DeepWiki and Context7. The other sixteen returned 401 or
403: Linear, Notion, Stripe, Vercel, Sentry, GitHub, Cloudflare, Hugging Face,
PayPal, Grafana, Neon, Prisma, Semgrep, Webflow, Sanity, GitMCP.

That matters more than it first looks. Remote servers are the category where a
definition change is **completely invisible** to the people using them: no
package update, no lockfile line, no local signal at all. And they are also the
category nobody outside the vendor can audit, because `tools/list` is behind
OAuth. The people best placed to detect a remote rug pull are the customers who
already hold credentials — which is an argument for `toolprint check` running in
their CI, not for a public observatory.

So the watchlist is stdio-weighted by necessity, not by preference. That is a
limitation of the dataset and should be stated whenever it is cited.

## Protocol versions observed

Of the servers that responded, one spoke `2026-07-28`, most spoke `2025-11-25`,
and two still spoke `2024-11-05`. The ecosystem is spread across three protocol
eras, twenty months apart.

## Running it by hand

```bash
toolprint baseline --connect --yes --config servers.json \
                   --baseline baseline.json
toolprint check    --connect --yes --config servers.json \
                   --baseline baseline.json
```

## Servers that ask for an API key

Most of them do not actually need one. **MCP servers check credentials at
`tools/call`, not at `tools/list`** — the gate is whether the environment
variable is *set*, not whether it is valid. Ten servers that refused to start
without a key were tested with the literal string
`not-a-real-key-0000000000`, and all ten served their full tool definitions.

So nine of them are on this list with `${WATCH_PLACEHOLDER}`, a value the
workflow sets in plain sight. There is no credential here to protect, and
nothing in this repository is a secret.

Two limits on that:

- **Remote HTTP endpoints are different.** Linear, Notion, Stripe, Vercel,
  Sentry and Hugging Face all reject a placeholder bearer token with 401 or 403,
  because their auth happens at the transport layer rather than inside the
  server. Watching those needs a real token.
- **A placeholder may not see everything.** A server could return a different
  tool set to an authenticated caller — tools gated by plan or scope. What is
  recorded here is the unauthenticated view, which may be a subset. Treat a
  no-drift result as "the public surface did not change".

## Adding servers as it runs

Yes — the list is meant to grow. Edit `servers.json` and commit; the next daily
run picks it up.

```bash
# add an entry to servers.json, then either wait for the schedule or:
toolprint check   --yes --config servers.json --baseline baseline.json
toolprint approve --yes --config servers.json --baseline baseline.json --by "$USER"
```

A newly watched server produces **no drift**, which is correct — nothing moved.
`check` reports it separately as *newly watched, not yet in the baseline*, and
`approve` adopts it, stamping `first_observed` with that date. The scheduled
workflow runs `approve` every day for exactly this reason, so additions are
adopted without anyone intervening.

**`first_observed` is what keeps the arithmetic honest.** Servers joined at
different times, so they have different observation windows. `analyse.py
--by-server` divides each server's changes by its own window; a flat
server-day total would credit a server added last week with the whole run's
quiet time, which is an error in the direction that flatters the result.

Removing a server is the same idea in reverse: drop it from `servers.json` and
it stops being observed, but its baseline entry and its history stay. Deleting
those would erase the record of what it looked like. `check` lists servers it
expected and did not see, which also catches a server that has simply broken.

Good candidates are servers that (a) exist on npm or PyPI, and (b) actually
serve `tools/list` with no credentials. Check the second before adding — roughly
a third of the ones tried failed on a missing API key:

```bash
toolprint scan --connect --config /tmp/candidate.json
```

## Caveats

- Runs on a GitHub-hosted runner, so `npx -y pkg` resolves the latest published
  version each day. Package churn and definition churn are therefore the same
  signal here; distinguishing them needs a pinned second run.
- Only tool *definitions* are observed. A server whose runtime behaviour changes
  without its definitions changing — the postmark-mcp case — is invisible to
  this, and to the tool generally.
- No credentials are used, so servers that gate `tools/list` are absent.

## Layout

| Path | What it is |
|---|---|
| `servers.json` | The watchlist, in MCP client config format |
| `baseline.json` | The approved state. **Its git history is the dataset.** |
| `observations.csv` | One row per run: the denominator |
| `observations/` | Per-run drift detail, written only on days with changes |
| `analyse.py` | Reads the history and reports a rate |
| `.github/workflows/watch.yml` | Daily collector |

## Licence

Apache-2.0 for the code. The observations are factual records about publicly
published packages and endpoints; use them freely, and cite the limitations
above if you do.
