# Codex worker global-install checkride observations

**Filed:** 2026-08-28
**Source:** `docs/superdev/checkrides/2026-08-28-codex-worker-global-install-evidence/evaluator-verdict.md`
**Class:** nonblocking operator-experience backlog

## CWGI-1 — Classify preflight success

**Status:** Backlog
**Surface:** `install-codex-worker` success output

Absent installation, lower/higher version repair, and exact-version idempotence all
currently render `codex-worker ready: <path> (<version>)`. This is truthful but hides
whether the preflight mutated the user's tool. The checkride reconstructs the distinction
only through UV call logs.

**Desired operator outcome:** render a concise, machine-testable classification such as
`installed`, `repaired <from> -> <to>`, or `already ready`, while retaining canonical
path and exact version. Preserve idempotence and the rule that a newer incompatible tool
is replaced rather than silently accepted.

**Acceptance:** isolated absent, older, newer, and exact-match cases each emit the correct
classification; exact match performs zero install calls; existing shadow/failure output
and stdout/stderr/exit contracts remain stable.

## CWGI-2 — Preserve recovery identity on incomplete completion

**Status:** Backlog
**Surface:** common `start`/`run` typed `incomplete_completion` refusal

Two retained checkride incidents returned empty `next_actions` and all-null `known_ids`
even though `status-checker-abc` existed in the isolated registry and later status could
identify its session, thread, and failed turn. The refusal was typed and honest, but it
left the operator without the known-worker inspection route.

**Desired operator outcome:** when the common facade has created or resolved a mapping,
an `incomplete_completion` response retains every known instance/name/session/thread/turn
identity and emits runnable short-command status/history recovery. Do not invent an ID
that the operation never established.

**Acceptance:** deterministic and real-surface negative cases prove complete known-ID
retention after mapping creation, runnable status/history next actions, exactly one JSON
object, no traceback, and unchanged behavior when no identity was ever established.
