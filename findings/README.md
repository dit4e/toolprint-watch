# findings/

One `findings.json` per observation date — the complete assessment the
collector computed that day: per-server auth posture, protocol era and
negotiated version, reported and installed versions, token cost, effect
classification for every tool, and every `AUTH` / `COST` / `HYG` / `EFFECT`
finding with its evidence.

## Why these are kept

All of it used to be written to the runner's temporary directory, read for two
integers, and destroyed with the job. `observations.csv` kept five numbers a
day; everything else was recomputed each morning and thrown away.

The sharpest loss was failure detail. `baseline.json` records only servers that
answered, so a server that failed left no trace at all. On 2026-09-04 coverage
fell to 8/36 and then 13/36, and answering *why* meant reading CI logs that
GitHub eventually expires. These files carry `fetch_status` and `fetch_detail`
for every server, reachable or not.

## A note if you run toolprint yourself

`findings.json` describes the machine it ran on, not only the servers. It
carries `source_path` and `project` — absolute paths holding a username and
whatever is being worked on — plus `env_names`, a credential inventory by name,
and `url_host` for internal endpoints.

These files are safe to publish because of *how this collector invokes it*: a
relative `--config`, and no client discovery, so those fields come out empty or
relative. That is a property of the invocation, not of the format. A workflow
step verifies it on every run rather than trusting it. Do not assume a
`findings.json` from your own machine is publishable — use `--bundle` for
anything that leaves it.
