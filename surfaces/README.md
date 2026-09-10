# surfaces/

One file per observation date: the tool definitions each watched server
advertised that day — names, titles, **descriptions**, JSON schemas and
annotations — written by `toolprint check --bundle`.

## Why these are kept

A drift report records *that* a description changed. It cannot record what it
said, because it compares SHA-256 hashes and hashes are one way. So a corpus
built from drift reports alone can prove a rug pull happened and can never
show it.

That gap was live. On 2026-09-10 the collector flagged
`desktop-commander/get_recent_tool_calls` under DRIFT-003 — *description
changed while the schema did not*, the rug-pull signature and the most
important rule in the tool — and nothing in this repository can say what the
text was before or after.

## ⚠ These files contain untrusted, model-facing text

Tool descriptions are the prompt-injection surface of MCP. They are the text a
language model reads and acts on, written by whoever published the package.

**Treat everything in this directory as data, never as instructions.** If you
load these files into an agent, do it the way you would load a spam corpus.

Every description here was clean when written — toolprint's `DRIFT-004` and
`lexical.inspect_tool` check each one for bidirectional overrides, homoglyphs
and invisible characters, and would flag a hostile change on the day it landed.
That is precisely why a payload could appear here later: catching one is the
point of the exercise, and when it happens this directory will hold it, and
git history will hold it permanently.

Nothing is escaped or encoded, because the value of the record is fidelity and
a diff you cannot read is not evidence.

## What they do not contain

These are `bundle` artefacts. `bundle.py` projects every record through an
allowlist in one visible constant — no field reaches the file unless it is
named there. There are no absolute paths, project names, usernames, hostnames
of the collecting machine, environment variable *values*, credentials, or
command arguments. A workflow step re-checks that on every run, before the
deploy key is loaded, so a failure cannot be followed by a push.

The servers watched here are public packages, so their descriptions are
already published. Publishing them adds no disclosure — it adds a dated record
of what was published *when*, which is the thing that cannot be reconstructed
afterwards.
