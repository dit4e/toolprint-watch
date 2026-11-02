# What an API key does and doesn't protect (why credential-free monitoring is valid)

A common assumption is that a server requiring an API key keeps its tool surface
private. It does not — and, per the MCP specification, it isn't meant to.

All of the credential-requiring servers in the watchlist are **stdio** servers
(run via `npx`/`uvx`). For stdio, the MCP spec explicitly places authorization
out of scope: *"Implementations using an STDIO transport SHOULD NOT follow [the
authorization] specification, and instead retrieve credentials from the
environment."* The key is a credential for the vendor's **upstream service**
(its cloud API — quota, billing, data), used only when a tool is actually
**called**. The tool **list** is static metadata baked into the package and is
served regardless of the key.

So when the watch scans these servers with a placeholder key (`${WATCH_PLACEHOLDER}`,
`fc-…`, `xoxb-…`) and gets back a full `tools/list`, that is **expected and
correct**, not a leak or a vulnerability. The spec defines no per-method
authorization, requires no authentication of `tools/list`, and nowhere designates
the tool list as sensitive.

**Why this matters for this project (the only reason it's noted here):** it is
precisely what makes credential-free drift monitoring valid. The definitions —
the thing a rug-pull would alter — are not behind the key, so the monitor can
observe them on key-gated servers without holding any credential. It is a
methodology note, not a finding about any vendor.

Reproduce the count: `python3 analysis/credential_exposure.py`.
