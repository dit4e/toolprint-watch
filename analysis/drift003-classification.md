# DRIFT-003 qualification — are the 124 "description changed" events real?

DRIFT-003 fires when a tool's description changed while its schema held. A fair
reader will ask whether that count is inflated by environmental/non-semantic
noise. This checks.

**Method.** Seeded random sample (seed 20261102) of 30 of the 124 DRIFT-003
events. Each tool's before/after description is reconstructed from the captured
surface history and classified: ENVIRONMENTAL (identical after normalizing
whitespace/markdown, or only numbers/punctuation changed), GENUINE (meaningful
words added/removed), or UNVERIFIABLE (before-text not retained — the baseline
stores component hashes, not description text). Reproduce with
`analysis/drift003_classify.py`; the full sample is `analysis/drift003-sample.json`.

**Result (n=30):** GENUINE 24 · ENVIRONMENTAL **0** · UNVERIFIABLE 6.

**Conclusion.** Zero environmental noise. Every reconstructable change (24/24)
was a genuine content edit, so the 124 figure is **not** inflated by non-semantic
churn and needs no downward adjustment. The 6 unverifiable cases are a
data-retention limit, not evidence of noise.

**Honest caveat worth stating alongside the number:** changes cluster by release.
A single `@azure/mcp` release on 2026-09-13 edited the same boilerplate across 14
tools — genuine edits, but one decision, not 14. Event counts should be read with
that in mind.
