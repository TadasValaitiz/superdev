# Codex worker → Claude callback checkride

Date: 2026-08-20

Overall verdict: **PASS** at candidate `07ff933`.

The first fresh executor was dispatched as `gpt-5.6-terra`, medium effort, and recorded
17 fully reconstructable top-level invocations after a controller no-elision correction.
The fresh independent evaluator was dispatched as `gpt-5.6-sol`, high effort, identity
`/root/callback_task8_implementer/callback_checkride_evaluator`; its first verdict was
NEEDS_WORK with five blocks covering recovery guidance, stopped-daemon recovery,
verbatim callback evidence, missing live mechanisms, and the Unicode lifecycle boundary.

Fix wave `9937c8e` added per-kind callback recovery, explicit no-turn `daemon start`,
daemon-owned envelope sizing, sanitized destination-labelled frame capture, and live
file/priority, replay, failed-terminal, artifact, and raw-method rides. A second fresh
Terra/medium executor recorded the focused reride. Follow-up `07ff933` qualified daemon
stop-timeout recovery and removed an artificial foreground-child cleanup refusal. The
same independent evaluator then closed B1–B5 and returned PASS with no blocking findings.

Direct evidence:

- [Initial executor transcript](2026-08-20-codex-worker-claude-callbacks-evidence/executor-transcript.md)
- [Focused executor reride](2026-08-20-codex-worker-claude-callbacks-evidence/executor-focused-reride.md)
- [Evaluator history and final PASS](2026-08-20-codex-worker-claude-callbacks-evidence/evaluator-verdict.md)
- [Focused sanitized callback records](2026-08-20-codex-worker-claude-callbacks-evidence/focused-reride/)
- [Real Claude caller evidence](2026-08-20-codex-worker-claude-callbacks-evidence/claude-caller/validated-common-evidence.json)

All callback claims are local `written` and correlated receipts. Neither executor nor
evaluator claims Claude delivery, token usage, provider capacity, or transport capacity.
