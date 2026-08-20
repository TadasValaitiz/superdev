# Codex worker → Claude callback checkride evaluator verdict

Date: 2026-08-20  
Candidate product SHA: `ed3b0237a287aaa75cdf4757d8593c2223f3c32b`  
Role: independent CHECKRIDE EVALUATOR; judgment only, no product edits  
Identity: `/root/callback_task8_implementer/callback_checkride_evaluator`  
Model: `gpt-5.6-sol`, reasoning effort `high` (controller-dispatched configuration; not inferred from runtime output)

## VERDICT: NEEDS_WORK

I would not hand this surface to the operator as-is. The automatic callback, proactive write, origin-retention, credential-scrub, five-worker, and non-destructive restart happy paths are credible, and the product correctly reports socket handoff as `written` rather than `delivered`. The gate remains blocked by misleading recovery instructions and by checkride evidence that does not reconstruct several promised mechanisms.

No command was re-driven by this evaluator. The corrected transcript and tracked raw records directly exposed the operator problems; the local implementation was inspected read-only to confirm their mechanism.

## Blocking findings

### B1. Callback refusals prescribe retries that cannot resolve the refusal

The disabled-binding refusal says callbacks were disabled, marks the error non-retryable, then recommends the same worker's `message --message-file <path>` as the next action (`executor-transcript.md:106-115`, repeated at `159-165`; `executor-live/callback-security/transcript.jsonl:6`). The stale and ambiguous target refusals recommend that same unchanged retry (`executor-live/callback-security/transcript.jsonl:2-3`). The oversize refusal gives no next action at all (`executor-live/callback-security/transcript.jsonl:4`). This contradicts the promised per-kind recovery: inspect status/continue for unavailable or stale, select a unique Claude name for ambiguous, and shorten the message for oversize (`docs/superdev/specs/2026-08-20-codex-worker-claude-callbacks-cli-surface.md:290-301`).

The mechanism is one generic rewrite for every callback fault in `skills/subagent-driven-development/scripts/codex_worker/facade.py:171-187`; it discards the distinction the typed fault vocabulary is meant to provide. To the operator, these are executable-looking dead ends: a disabled worker cannot be made callback-enabled by changing inline text to a file, a stale origin stays stale, and an ambiguous name stays ambiguous. Severity: **blocking** — the operator is misled and remains stuck.

### B2. A stopped daemon has no usable recovery path on the message surface (DESIGN-DOC)

After the non-destructive stop, `message` returns `daemon_stopped` with `next_actions: []` (`executor-transcript.md:128-145`). The intuitive recovery `codex-worker daemon start` is not a command and exits 2 (`executor-transcript.md:205-215`). The CLI deliberately does not autostart for `message`, but the surface offers no obvious non-blocking restart action; using `run` restarts the daemon only by starting another Codex turn (`executor-transcript.md:148-156`), which is not equivalent to retrying a notification.

This is frequent-path lifecycle friction, not polish: after a preserved stop/restart event, the operator cannot discover how to restore the relay without either knowing internal `daemon serve` process management or causing unrelated work. Severity: **blocking** — the operator is stuck. **DESIGN-DOC:** if the remedy adds a real `daemon start` action or changes message autostart semantics, amend the surface/decision record before implementation.

### B3. Callback output/provenance evidence is asserted but not preserved verbatim

The tracked scenario JSONL files preserve subprocess invocations and CLI stdout/stderr, but not the callback frames received by the origin and alternate inboxes. `CallbackInbox` keeps frames only in memory (`tests/codex-worker/live_broker_check.py:127-171`), and fixture teardown deletes the temporary registry/socket root (`:228-231`). Scenario summaries then reduce those frames to booleans and IDs such as `complete_inline_result`, `origin_preserved`, and `replacement_frame_count` (`executor-transcript.md:16-56`).

Consequently, a later reviewer cannot reconstruct from the committed executor evidence the exact callback envelope, complete embedded completion, `from` provenance, priority, origin-versus-alternate destination, or absence of a replacement frame. The harness assertions are useful tests (`live_broker_check.py:1520-1528`, `1585-1609`, `1625-1643`), but they are not the sanitized-but-verbatim checkride transcript required for an independently auditable ride. Severity: **blocking** — the central callback output and provenance claims cannot be reviewed from the evidence artifact.

### B4. Required recovery and compatibility rides are missing or mislabeled

Task 8 requires happy/refusal coverage for message inline/file/priorities/override, restart recovery, artifact read-back, and raw compatibility (`.superdev/sdd/task-8-brief.md:53-57`). The supplied evidence does not complete that matrix:

1. `callback-recovery` explicitly substitutes `"deterministic ... receipt"` strings for pending same-ID restart replay, failed-terminal notification, and artifact digest/read-back (`executor-transcript.md:49-57`; builder at `tests/codex-worker/live_broker_check.py:1686-1694`). The raw ride shows completed/interrupted callbacks and non-replay of an already-written event only (`executor-live/callback-recovery/transcript.jsonl:1-11`).
2. The only ordinary `--message-file` ride reaches a deliberately disabled binding, so there is no successful file-input write receipt (`executor-transcript.md:148-165`).
3. The record labeled `raw compatibility` invokes the raw script entrypoint but only asks for `daemon status` (`executor-transcript.md:168-176`); it does not drive an existing raw session/turn method, so it cannot establish that raw worker methods retain their meaning.

Deterministic tests may support these mechanisms, but the checkride brief explicitly calls for the real surface to be driven. Severity: **blocking** — promised end-to-end operator journeys remain unobserved.

### B5. The measured Unicode refusal bypasses the promised daemon-owned final-envelope gate

The oversize scenario returns in about 69 ms with null worker identities (`executor-live/callback-security/transcript.jsonl:4`) because the client rejects the message text before RPC at `skills/subagent-driven-development/scripts/codex_worker/cli.py:459-467`. The locked surface says the daemon owns sizing of the final serialized envelope and that the refusal is deliberately not a client-side estimate (`docs/superdev/specs/2026-08-20-codex-worker-claude-callbacks-cli-surface.md:214-217`, `290-301`). The daemon also contains the correct final-envelope check, but this ride never reaches it.

The conservative client precheck may be safe for an already-over-cap message body, but the recorded security ride does not prove the promised lifecycle boundary and loses the worker-aware recovery context. Severity: **blocking** for promised-versus-delivered mechanism/evidence. Remove the shortcut and reride, or amend the governing design before retaining two sizing gates.

## Advisory findings

### A1. The corrected count is reconstructable but the transcript remains internally contradictory

The controller correction establishes 17 fully embedded top-level invocations and explains the earlier conflation (`executor-transcript.md:187-223`). The original report still states 23 top-level invocations and `NOT RUN: none` (`:179-185`). The correction is sufficient to avoid a blocking count ambiguity, but replacing the stale report text would make the final evidence easier to scan and harder to quote incorrectly. Severity: **advisory**.

### A2. Compact JSON is dense for terminal inspection

The default one-line JSON is complete and machine-readable, and `--pretty` exists, so this is not a functional block. For human checkrides, using `--pretty` on representative status and refusal commands would make callback state, known IDs, and next actions materially easier to audit. Severity: **advisory**.

## What genuinely passed

- Automatic enabled/disabled/unavailable capture states and redacted status are distinct and readable (`executor-live/callback-common/transcript.jsonl:1-6`).
- Successful proactive and terminal receipts say `written`, carry stable event IDs, and do not make a delivery claim (`executor-transcript.md:16-35`; real Claude validation reports `direct_codex_invocation: false`, `mcp_invocation: false`, and `raw_codex_worker_invocation: false` in `claude-caller/validated-common-evidence.json`).
- Origin retention after ambient replacement/removal, one-message alternate routing, and exactly five named workers are exercised by the live harness; the assertions are strong even though B3 requires their frames to be preserved (`live_broker_check.py:1572-1647`, `1763-1788`).
- Credential scrubbing, stale/PID-reuse refusal, ambiguous-target refusal, disabled override refusal, exact exit classes, and secret-free public output are exercised (`executor-live/callback-security/transcript.jsonl:1-6`).
- Stop is non-destructive and `run` resumes the same worker/session after daemon restart (`executor-transcript.md:128-156`; `executor-live/callback-recovery/transcript.jsonl:7-10`).
- The mechanism is local AF_UNIX daemon transport; the inspected callback path adds no MCP or cloud relay and does not hand callback credentials to the Codex child.

## Re-evaluation scope

After fixes, reride the affected refusal outputs, stopped-daemon recovery, daemon-side Unicode boundary, successful message-file/priorities, pending same-ID restart replay, failed terminal notification, artifact reference/digest/size/read-back, and at least one real raw session/turn method. Preserve sanitized callback frames with destination labels so full-result and origin/alternate provenance can be independently reconstructed. Unaffected happy paths need not be rerun.

---

## Focused fix-wave re-evaluation — 2026-08-20

Candidate product SHA: `07ff9334927f6de17881e513d219521087f1f7be`  
Compared with: `ed3b023..07ff933` (fix wave `9937c8e`, cleanup/recovery correction `07ff933`)  
Role: independent CHECKRIDE EVALUATOR; judgment only, no product or executor-evidence edits  
Identity: `/root/callback_task8_implementer/callback_checkride_evaluator`  
Model: `gpt-5.6-sol`, reasoning effort `high` (controller-dispatched configuration; not inferred from runtime output)

### FINAL VERDICT: PASS

The focused fix wave closes every original blocker B1–B5. The original four scenario
invocations report PASS, the six direct stopped-daemon invocations have the expected exits,
and the original scenario records reconstruct 80 JSONL records and 15 destination-labelled,
credential-sanitized callback frames. The superseding cleanup-focused recovery ride adds 39
records and exits cleanly throughout. The controller also reports a fresh warning-strict full
gate of 361 passing tests after the final correction. From the operator seat, the surface is
now handoff-ready: receipts remain honest `written` socket-handoff claims, refusals are typed
and actionable, provenance and recovery are reconstructable, credentials stay sanitized,
raw methods retain their meaning, and the inspected mechanism remains local AF_UNIX without
MCP, cloud, or direct-Codex callback workarounds.

### Original blocker disposition

1. **B1 — CLOSED.** Callback refusals now give kind-specific, executable recovery instead
   of repeating the failing send. Stale, ambiguous, oversized, and disabled cases preserve
   the selected instance and worker IDs and prescribe status/select-unique/shorten/continue
   actions respectively (`focused-reride/callback-security/transcript.jsonl:3-7`). The
   implementation selects those actions by callback fault kind
   (`skills/subagent-driven-development/scripts/codex_worker/facade.py`,
   `_callback_fault_actions`).

2. **B2 — CLOSED.** D34 locks explicit managed-daemon startup and daemon-owned sizing
   (`docs/superdev/specs/2026-08-20-codex-worker-claude-callbacks-decisions.md:638-658`),
   and the companion surface documents `daemon start` without a turn
   (`docs/superdev/specs/2026-08-20-codex-worker-claude-callbacks-cli-surface.md:290-295`).
   The direct ride stops the selected daemon, receives an exact instance-qualified start
   action, runs that literal action successfully, and observes ready state with zero workers
   before cleanup (`executor-focused-reride.md:62-126`; exact captures under
   `focused-reride/stopped-daemon/`).

3. **B3 — CLOSED.** The tracked scenario records now preserve each callback frame's full
   sanitized `user_line`, `[REDACTED]` auth field, and explicit destination. The 15 frames
   cover `origin`, `origin:reopened`, and `alternate:task8-alternate`; they retain schema,
   event ID, priority, worker provenance, completion/reference payload, and `from_mode`
   (`focused-reride/callback-origin-retention/transcript.jsonl:2,4,6`;
   `focused-reride/callback-proactive/transcript.jsonl:10,12,15,17,20`;
   `focused-reride/callback-recovery/transcript.jsonl:2,7,12,22,34,35`;
   `focused-reride/callback-security/transcript.jsonl:2`).

4. **B4 — CLOSED.** The successful proactive ride covers inline `now`, file-backed `later`,
   one-send alternate routing, subsequent origin retention, and terminal callbacks
   (`focused-reride/callback-proactive/transcript.jsonl:10-20`). Recovery records a pending
   interrupted event before stop and the same event ID written after restart, while an
   already-written event is not replayed (`focused-reride/callback-recovery/transcript.jsonl:9-25`).
   It also preserves completed, interrupted, and failed terminal frames, a terminal artifact
   reference plus SHA-256/size/read-back equality, and successful raw `session show`,
   `session resume`, and `turn status` calls (`focused-reride/callback-recovery/transcript.jsonl:2,7,12-14,22-37`).

5. **B5 — CLOSED.** The client-side UTF-16 refusal shortcut is absent from the fix diff;
   requests may reach the daemon under the new 8 MiB request cap while responses remain
   capped at 1 MiB. The Unicode file ride returns daemon fault `-32037` with selected worker
   identities and a shorten-message action (`focused-reride/callback-security/transcript.jsonl:5`),
   matching D34 and the companion contract
   (`docs/superdev/specs/2026-08-20-codex-worker-claude-callbacks-cli-surface.md:299-308`).

### Blocking findings

None.

The provisional inspection finding against the original recovery record is **CLOSED** at
`07ff933`. A focused RED test first reproduced null instance identity and unqualified actions;
the implementation now retains `known_ids.instance` and shell-quotes that selected instance
in both timeout recovery commands
(`skills/subagent-driven-development/scripts/codex_worker/instance.py:464-482`;
`tests/codex-worker/test_instance.py`,
`LifecycleTests.test_stop_timeout_recovery_commands_keep_selected_instance`). The harness now
shuts down and reaps its own raw foreground fake through the raw socket instead of treating
that harness-owned child as a managed-daemon cleanup case. The superseding live recovery ride
passes, and raw shutdown, foreground process exit, and both managed stops all exit 0
(`executor-focused-reride.md:127-152`;
`focused-reride/callback-recovery-clean/transcript.jsonl:36-39`).

### Advisory findings

1. **A1 remains advisory.** Compact one-line JSON is complete and machine-readable, but
   representative `--pretty` captures would still improve human inspection.

2. **The initial transcript-count advisory is superseded for the focused reride.** Its 11
   top-level invocations and linked one-command captures reconcile cleanly; the original 80
   internal records and the 39-record superseding recovery ride are explicitly counted
   separately (`executor-focused-reride.md:144-154`).
