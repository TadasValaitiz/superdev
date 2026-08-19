# SDD Codex model selection — Decision log

**Design doc:** ./2026-08-19-sdd-codex-model-selection-design.md
Append-only; newest at the bottom. D-numbering shared with the spec's §6.

---

## D1 — Advisory role routing with mandatory gate floor
**When:** 2026-08-19T05:12:43Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** The Codex worker supports multiple live-discovered models, but the SDD skill does not yet explain how to choose among them.
- **Options weighed:**
  - A: advisory role defaults with justified overrides — gains adaptability to task complexity, account availability, measured quality, latency, and cost / sacrifices absolute uniformity.
  - B: strict model routing for every role — gains predictability / sacrifices flexibility and can become stale as the live catalog changes.
- **Decided:** Use advisory defaults. Keep the existing mandatory most-capable floor for design reasoning and design/final-gate review roles, where late misses are expensive.
- **Rests on:** Human direction and the official OpenAI model guidance consulted on 2026-08-19: Sol for frontier complex reasoning/coding, Terra for balanced intelligence and cost, Luna for cost-sensitive high-volume work.
- **Affects:** Model-selection guidance in `skills/subagent-driven-development/SKILL.md` and the planned separate Codex model/CLI appendix.
- **Revisit-when:** Representative SDD evaluations show a different routing policy produces better task success, latency, or cost.

## D2 — Two operator-facing model tiers only
**When:** 2026-08-19T05:54:13Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** A broader model catalog would make the SDD routing guidance harder to remember and more likely to become stale.
- **Options weighed:**
  - A: document each available Codex model and generation — gains completeness / sacrifices a stable, simple operating rule.
  - B: expose exactly two semantic tiers — gains a compact routing decision / deliberately omits niche price, latency, and legacy-model choices.
- **Decided:** The skill exposes only `very smart` and `medium` tiers. It does not present a third cheap tier or a catalog of older model generations.
- **Rests on:** Human direction: “2 tiers very smart, medium — that's it.”
- **Affects:** The main SDD model-selection rule, the Codex-specific appendix, and examples of model selection.
- **Revisit-when:** The live Codex catalog cannot supply either tier or measured SDD evaluations demonstrate that two tiers are insufficient.

## D3 — Pin the two tiers to Sol and Terra
**When:** 2026-08-19T06:00:15Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** The semantic tiers require concrete Codex model IDs before they can guide worker dispatch.
- **Options weighed:**
  - A: map `very smart` to `gpt-5.6-sol` and `medium` to `gpt-5.6-terra` — gains a clear, testable rule / requires an explicit availability failure when either model is absent.
  - B: allow any live model to be silently substituted into either tier — gains availability / makes the tier's capability meaning unpredictable.
- **Decided:** For now, `very smart` means `gpt-5.6-sol` and `medium` means `gpt-5.6-terra`. Other models are excluded from normal skill recommendations.
- **Rests on:** Human confirmation and the live model discovery already exercised by the Codex worker acceptance run.
- **Affects:** Tier definitions, role-routing examples, live-discovery validation, and CLI appendix examples.
- **Revisit-when:** Either pinned model is unavailable or renamed, or measured SDD evaluations justify changing the mapping.

## D4 — Preserve Claude Code; resolve tiers per dispatch mechanism
**When:** 2026-08-19T06:01:07Z · **Phase:** brainstorm ·
**Status:** locked
**Decided by:** human

- **Trigger:** Concrete Sol/Terra mappings must not accidentally turn the harness-neutral SDD skill into a Codex-only workflow.
- **Options weighed:**
  - A: replace the existing Claude routing with Codex model IDs — gains one literal mapping / removes Claude Code as the primary coordinator and breaks non-Codex dispatches.
  - B: retain semantic tiers in the core skill and resolve them by dispatch mechanism — gains one stable policy across Claude and Codex / requires a small Codex-specific appendix.
- **Decided:** Claude Code remains a first-class coordinator and subagent dispatch mechanism. The core skill uses `very smart` and `medium`; Codex-worker dispatches resolve them to Sol/Terra, while native Claude dispatches use the corresponding Claude model tiers available in that harness.
- **Rests on:** Human requirement: “Make sure that Claude Code also remains,” plus the existing broker boundary in which Claude Code owns coordination.
- **Affects:** Core skill wording, Codex appendix scope, examples, and compatibility acceptance.
- **Revisit-when:** The SDD workflow adopts a single mandatory execution harness or Claude Code no longer supports explicit model selection.

## D5 — Resolve native Claude tiers with stable aliases
**When:** 2026-08-19T06:07:50Z · **Phase:** brainstorm spec-review ·
**Status:** locked
**Decided by:** coordinator clarification of D4

- **Trigger:** Independent spec review found that D4 preserved native Claude dispatch
  but did not define a testable resolution for its `medium` tier.
- **Options weighed:**
  - A: resolve `very smart` to `opus` and `medium` to `sonnet` — gains stable,
    actionable Claude Code dispatch aliases / sacrifices automatic substitution when an
    alias is unavailable.
  - B: leave both as “corresponding available tiers” — gains catalog flexibility /
    sacrifices deterministic routing and makes accidental tier collapse unverifiable.
- **Decided:** Native Claude Code dispatch resolves `very smart` to `opus` and `medium`
  to `sonnet`. Both are passed explicitly. An unavailable required alias is a reported
  blocker, not a silent fallback. Main-session brainstorming/design remains native
  Claude `opus`; the Codex worker remains an explicitly delegated task path.
- **Rests on:** D4, existing Superdev prompt conventions, and the user's requirement
  that Claude Code remain.
- **Affects:** Claude compatibility design, core model-selection guidance, and
  acceptance scenarios.
- **Revisit-when:** Claude Code changes or removes either stable alias.

## D6 — Migrate every active routing consumer atomically
**When:** 2026-08-19T06:43:00Z · **Phase:** plan ·
**Status:** locked
**Decided by:** coordinator from independent plan review

- **Trigger:** The first plan changed the central Model Selection section but left
  active reviewer, checkride, brainstorming, and self-brainstorming prompts on the
  retired `most capable` / `standard` / `top tier under Codex` vocabulary.
- **Options weighed:**
  - A: update only the central policy — gains the smallest diff / sacrifices a single
    enforceable contract because dependent prompts can bypass the new mappings.
  - B: migrate every active routing consumer in the same task — gains consistency and
    testability / expands the documentation diff across linked skills.
- **Decided:** Migrate all active Superdev model-routing consumers atomically to
  `very smart` / `medium` and the explicit Claude aliases, with Codex resolution
  delegated to the new appendix. Structural tests reject retired routing vocabulary in
  those consumers.
- **Rests on:** R1–R4, D2–D5, and the plan review finding that contradictory active
  prompts would make correct routing optional.
- **Affects:** §5.1 and the implementation plan's file map, structural tests, and
  evaluation context.
- **Revisit-when:** A newly added model-routing consumer intentionally defines a
  different policy and the anchor is amended to permit it.

## D7 — Treat synonym-bearing tool references as routing consumers
**When:** 2026-08-19T06:48:43Z · **Phase:** plan ·
**Status:** locked
**Decided by:** coordinator from plan re-review

- **Trigger:** A literal inventory of `most capable` / `standard model` missed the
  checkride executor's `standard tier` and `using-superdev`'s Codex routing table with
  Luna and nearest-tier substitution.
- **Options weighed:**
  - A: patch only the initially matched files — gains a narrow diff / sacrifices D6
    because synonym-bearing consumers retain contradictory behavior.
  - B: inventory model-routing semantics, including synonyms and tables — gains a
    complete contract boundary / requires stronger structural guards.
- **Decided:** The checkride executor prompt and `using-superdev` Codex tools reference
  are active routing consumers. Migrate them in the same task and reject `standard
  tier`, Luna, and nearest-tier fallback in structural tests.
- **Rests on:** D2, D3, D6 and the plan re-review evidence.
- **Affects:** §5.1 consumer boundary, plan file map, Step 5, and structural tests.
- **Revisit-when:** The routing contract intentionally adds another model or tier via an
  anchor amendment.

## D8 — Use checkpoint reviewers instead of a large model-call campaign
**When:** 2026-08-19T06:51:49Z · **Phase:** build ·
**Status:** locked
**Decided by:** human

- **Trigger:** The planned 45-call control/before/after campaign was disproportionate
  to a focused skill-documentation change.
- **Options weighed:**
  - A: run three scenarios five times across three variants — gains distributional
    evidence / sacrifices time and attention far beyond this change's risk.
  - B: keep one small structural RED/GREEN check, then use fresh reviewer agents at the
    documentation checkpoint — gains focused semantic review and normal SDD independence
    / sacrifices repetition statistics.
- **Decided:** Remove the large Claude CLI campaign and its harness. Use the focused
  structural check for the missing/present contract, then dispatch quick fresh reviewer
  agents after the documentation checkpoint to apply scenarios and inspect the complete
  routing surface.
- **Rests on:** Human direction: “replace testing with small reviewer agents, quick after
  some checkpoint.”
- **Affects:** Implementation plan test lane, task steps, file map, and acceptance
  receipts. The normal SDD task review and final whole-branch review remain required.
- **Revisit-when:** A future behavioral regression demonstrates that checkpoint review
  is insufficient for model-routing skill changes.

## D9 — Distinguish native Codex dispatch from the Claude-side broker
**When:** 2026-08-19T07:02:56Z · **Phase:** build ·
**Status:** locked
**Decided by:** coordinator from semantic checkpoint evidence

- **Trigger:** A fresh reviewer read `using-superdev/references/codex-tools.md` as an
  unconditional switch from native Claude to the local Codex-worker broker, even though
  `using-superdev` loads that reference only when the current harness is Codex.
- **Options weighed:**
  - A: require broker daemon/model-list/session commands in the Codex harness reference
    — gains one mechanism / breaks native Codex `spawn_agent` guidance and conflates two
    distinct dispatch surfaces.
  - B: name the mechanism boundary explicitly while sharing the two mappings — preserves
    native Codex multi-agent dispatch and Claude-coordinated broker dispatch / requires
    one clarification and structural assertion.
- **Decided:** `using-superdev/references/codex-tools.md` governs native Codex-harness
  multi-agent dispatch and does not require/start the broker. The SDD Codex model
  appendix governs an explicitly selected local broker from Claude Code. Both use
  Terra/Sol, but each validates effort through its own live surface.
- **Rests on:** `skills/using-superdev/SKILL.md` Platform Adaptation routing, D3, D4,
  D7, and the measured reviewer ambiguity.
- **Affects:** Codex tools reference, structural test, and D8 semantic checkpoint.
- **Revisit-when:** Native Codex dispatch and the broker are unified behind one actual
  mechanism.
