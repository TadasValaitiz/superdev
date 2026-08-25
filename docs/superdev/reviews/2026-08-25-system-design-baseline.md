# Baseline (RED) — system-design skill, 2026-08-25
Control subagent (no skill) asked to run a system-design session on a project with an existing design/ corpus.

## Observed divergences the skill must correct
1. **Lifecycle statuses instead of epistemic ones** — invented UNSTARTED/DRAFT/REVIEWED/IN-PROGRESS/DONE; never distinguishes *ruled* from *flexible* from *unexamined* (LOCKED/FLEXIBLE/DEFERRED/BLIND/MISMATCH absent).
2. **Nothing greppable** — no marker grammar in docs or code; statuses are prose words in one file's column.
3. **Angle/map conflation** — its "angle" carries Current State + Target State sections (map content); no five-kind contract, no Purpose/anchors/series, no collisions section.
4. **Invented a blocking gate** — "no implementation until DRAFT → REVIEWED": exactly the design-blocks-development rule D3 forbids; no concept of markers/forward-acting debt.
5. **No visions** — target described inside the angle; nothing to ground the next session on post-migration.
6. **Agenda by reread, not census** — sensible instincts (reread map, check collisions with angle-risk) but no mechanical opening (BLIND/MISMATCH grep), no residue input.
Good instincts to keep: mirrors existing doc family; dated session files; cross-reference note instead of silent drift; open questions flagged explicitly.
