# Angle 2 — The checkpoint seam

**Purpose:** understand what crosses between orchestrator and architect — and what freshness each side promises — without reading either skill.
**Formal anchors:** D52, D58–D60, D62; spec §5.1–§5.3 (R5, R9, R10).
**Series:** 2 of 4.

> **Status guide:** LOCKED · FLEXIBLE · DEFERRED · MISMATCH.

## The central question
How do two altitudes converse through files without the files becoming a third, drifting version of the truth?

## Boundaries
Starts when the orchestrator declares a checkpoint; ends at the reconcile commit. Room-side flows are angle 3; who RULES inside the sitting is the mode law (below), everything else about modes stays in D59.

## Concrete consequences
**The two-surface law (D60), the keystone:** docs/system-design/ is the RECONCILED surface — grab anything, it matches reality or wears a marker pricing your trust. docs/orchestration/ is the OPERATIONAL surface — message companions (short message + pointer into a file), stamped "OPERATIONAL RECORD — never reconciled, may be outdated", pruned on a rolling window (close of N deletes N−1, D62), never reconciled. **LOCKED.**
**Per checkpoint, exactly two artifacts + one commit:** the orchestrator's handover doc (narrative trio + map-row claims + residue clusters inline + inlined census/process facts) on the operational surface; the architect's response BLOCK inside milestones/<slug>/decisions.md (section verdicts · claim verdicts accepted/REJECTED-with-reason · cluster dispositions incl. BOUNCED DOWN) followed by its D# rulings, on the reconciled surface; the named reconcile commit closes the sitting (D52). **LOCKED.**
**Mode law (D59):** HUMAN — architect waits, operator rules; AUTONOMOUS — architect produces options+recommendation, ORCHESTRATOR picks (flagged, revisitable D#); reserved forks (money/irreversibility, blast radius, taste) always human; close always human. Applies identically to self-brainstorming ratification gates. **LOCKED.**

## Visible collisions
- **Rich handover vs pointer doctrine:** the narrative trio is judgment only the orchestrator has — it earned a durable doc; but the RESPONSE nearly became a third doc type until the operator's rule: every doc type is a reconciliation surface — so the response lives inside the file reconciliation already owns.
- **Architect idleness vs staging cost:** resolved by the mode law absorbing the pre-pass question — mechanical opens (census, stale-D# grep, agenda-as-questions) allowed in both modes; mode governs RULING, not reading.
- **Census as artifact vs tooling:** a committed recurring marker-census file lost to ephemeral script output quoted in handovers.

## Reconciled outcome
LOCKED: two-surface law, two-artifact checkpoint, mode law with reserved forks, rolling-window pruning. FLEXIBLE: handover section wording, stamp phrasing. DEFERRED: none.
