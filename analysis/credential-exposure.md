# Tool definitions are served before authentication

MCP authenticates at `tools/call`, not at `tools/list`. A server can require an
API key to *do* anything and still hand its entire tool catalogue — every name,
description, input/output schema — to an unauthenticated (or fake-key) client.

The watch demonstrates this incidentally: credential-requiring servers are
configured with a **placeholder key** (`servers.json`: `${WATCH_PLACEHOLDER}`,
`fc-…`, `xoxb-…`). Result (latest run):

**8 of 8 credential-requiring servers served their full `tools/list` to a key
that is not real** — brave-search-new, brave-search-old, exa, firecrawl, gitlab,
google-maps, slack, tavily.

**Framing — this is a protocol behaviour, not a per-vendor flaw.** It is how MCP
is specified; naming these servers as "leaking" would be wrong. Two honest
implications:

1. It is *why* credential-free drift monitoring is possible at all — the thing a
   rug-pull would alter (the definition) is not credential-protected.
2. Anyone assuming an API-key requirement protects what their agent is told about
   a server's tools is mistaken. The definitions are public either way.

Reproduce: `python3 analysis/credential_exposure.py`.
