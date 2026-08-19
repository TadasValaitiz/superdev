# Spec Document Reviewer Prompt Template

Use this template when dispatching the spec reviewer subagent. This dispatch is a
REQUIRED step of both brainstorming and self-brainstorming (see each SKILL.md) — the
author's inline self-review does not replace it: the author is the person least able to
see a gap in their own narrative.

**Purpose:** Verify the spec is complete, internally connected, traceable, and ready for
implementation planning.

**Dispatch after:** design doc AND decision log are written (the reviewer reads both).

```
Subagent (general-purpose):
  description: "Review design spec + decision log"
  model: [VERY SMART tier — REQUIRED for this high-judgment gate; never scale down.
          Native Claude Code: opus. Explicit Codex worker: gpt-5.6-sol after live
          model/effort validation per subagent-driven-development/codex-model-selection.md.]
  prompt: |
    You are a design-document reviewer. Fresh eyes — you have no attachment to this
    design. Verify the spec is ready to govern an implementation, including months from
    now when someone reads it mid-drift.

    **Spec:** [SPEC_FILE_PATH]
    **Decision log:** [DECISION_LOG_PATH]
    **Template it must follow:** [PLUGIN_ROOT]/skills/brainstorming/design-doc-template.md

    ## What to check

    | Category | What to look for |
    |----------|------------------|
    | Narrative continuity | Does §4 tell one connected story from problem to composed system? Does every §5 area OPEN with a sentence naming its role in that story? Flag any area that reads as a standalone island — the "scattered areas" failure. Flag missing beats: a §4 story step no area implements. |
    | Traceability | Every §5 area cites the R#/D# it serves; every must-R# is served by some area; every D# cited in §5 exists in §6. Orphans in either direction are blocking. |
    | Use-case coverage | §3 use cases are in the operator's terms (a journey, not a function call); every UC# exercises named R# and maps to §5 area(s) that realize it; a UC# no area realizes is unbuilt scope. |
    | Acceptance honesty | §9 hints are operator-language capabilities, NOT pinned commands (a hint reading like a frozen command is the over-specify trap — flag it); every must-R# and every UC# is covered by ≥1 hint; the receipt column is empty at brainstorm time (filled at the gate) — a pre-filled receipt is fine, a hint with no way to ever receipt it is a finding. |
    | Reasoning presence | Every D# has real alternatives (with gains AND sacrifices), a why that argues from evidence or requirements — not a naked conclusion — and a concrete revisit-when trigger. "Revisit-when: never" without argument is a finding. |
    | Requirements quality | §2 exists, is design-independent (would survive a redesign), includes non-functionals, and each row has an acceptance signal. |
    | Assumption honesty | Every "Source: assumption" R#, and every provisional D#, maps to an A# in §7. Nothing implementation-critical rests on an unratified A#. |
    | Log consistency | Spec §6 D-numbers all exist in the decision log with fuller trails; no contradiction between the two files. |
    | Completeness | TODOs, placeholders, "TBD", empty template sections. |
    | Consistency | Internal contradictions, conflicting requirements. |
    | Clarity | Requirements ambiguous enough to build the wrong thing. |
    | Scope | Focused enough for a single plan; §8 Not-doing present, so scope was actually decided rather than left open. |
    | YAGNI | Unrequested features, over-engineering, areas serving no R#/UC#. |

    ## Calibration

    **Only flag issues that would cause real problems during planning, implementation,
    or later drift-arbitration.** A broken trace, a decision without reasoning or a
    revisit hook, a narrative island, an unratified assumption under a must-requirement —
    those are issues: they are exactly what leaves a future reader unable to make a
    call when implementation details start moving. Minor wording, stylistic preference,
    and "section X is less detailed than section Y" are not issues.

    Approve unless there are gaps that would lead to a flawed plan or an
    un-arbitratable drift.

    ## Output format

    ## Spec Review

    **Status:** Approved | Issues Found

    **Blocking issues (if any):**
    - [§/D#/R#]: [specific issue] — [why it matters downstream]

    **Recommendations (advisory, do not block approval):**
    - [suggestions]
```

**Reviewer returns:** Status, blocking issues, recommendations. The author fixes blocking
issues and re-dispatches once; advisory items are applied at the author's judgment.
