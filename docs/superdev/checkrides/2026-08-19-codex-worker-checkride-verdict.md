# Codex worker CLI final checkride verdict — 2026-08-19

**Verdict: PASS**

I would hand this surface to the operator as-is. All prior findings F1–F7 and A1–A3 are closed, and the corrected transcript is internally consistent and reconstructable.

## Final evidence

- **Chronology and accounting:** The transcript declares six scenario launcher invocations (line 9) and presents exactly six in §§1–6. The first control attempt is honestly retained with exit `1`; its linked raw JSONL has 18 contiguous records, correctly itemized as 15 command records, one prompt-file record, daemon start, and daemon exit (lines 29–72, 379). The immediate rerun is separate and passes with 25 chronological records.
- **Real coding and control:** Two distinct live-discovered model/effort pairs complete separate code/file tasks in isolated worktrees (lines 11–27). The control rerun proves accepted steer, terminal completion, exact `steered.txt` bytes, zero broad files, accepted interrupt, terminal `interrupted`, and honest idle refusals (lines 56–72 and linked raw sequences 15–25).
- **Non-streaming concurrency:** Two waiters are started before completion; status and events remain responsive while both wait; both receive the same authoritative terminal result; cursor pagination and truncation are exercised (lines 74–90 and linked raw sequences 15–24).
- **Safety:** The socket result reports mode `0600`; TCP-listener inspection is no longer Unix-filtered and returns no listener; live collision, unsafe stale endpoint refusal, replacement, restart, and cleanup are recorded (lines 74–90). Deterministic fake-upstream approval evidence is clearly labeled, covers command/file/user-input requests, declines each, emits secret-free audit events, and reaches terminal completion without stalling (lines 92–108).
- **Recovery:** UUID resume and fresh-registry raw-thread repair preserve conversation context and immutable cwd, with every daemon shutdown/start recorded chronologically (lines 110–126 and linked raw sequences 8–38). Unknown UUID recovery now points to `session list` or raw-thread repair (lines 175–185).
- **Actionable refusals:** Unsupported `--turn` names the bad flag and valid selectors with exit `2` (lines 187–200). Wait timeout states that work remains active and supplies concrete status/wait/steer/interrupt commands with exit `1` (lines 214–248, 326–336).
- **A3 closure:** Manual accounting reconciles 19 invocations—11 original plus 8 fresh retry commands (line 378). The original daemon is explicitly shut down and confirmed absent before retry (lines 250–272). The fresh retry uses new socket/turn identifiers, records start → active status → timeout → terminal completion for the same turn, and includes the complete verbatim completion JSON (lines 274–348). Final shutdown is followed by an explicit status invocation, daemon-unavailable JSON, empty stderr, and exit `1` (lines 350–374).

No remaining blocking or advisory findings.
