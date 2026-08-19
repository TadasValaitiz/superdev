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
