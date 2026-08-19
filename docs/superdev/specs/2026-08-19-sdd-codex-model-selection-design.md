# SDD Codex model selection — Design (anchor)

**Date:** 2026-08-19 · **Status:** approved
**Mode:** human-in-loop
**Decision log:** ./2026-08-19-sdd-codex-model-selection-decisions.md
**Companions:** `skills/subagent-driven-development/codex-worker.md`; planned `skills/subagent-driven-development/codex-model-selection.md`
**Origin:** brainstorm with Tadas

## 1. Problem & intent   [ANCHOR]

The subagent-driven-development (SDD) skill can coordinate native Claude Code
subagents or explicitly selected local Codex workers, but its present model guidance
uses three relative classes (`cheap`, `standard`, and `most capable`) and its Codex
reference explains discovery without explaining which live Codex model belongs to
which SDD role. An operator can discover seven models yet still lack a compact routing
rule. The change must make model choice obvious without turning the core skill into a
volatile model catalog or displacing Claude Code as coordinator.

Success is a two-tier policy that reads the same in the core workflow—`very smart` and
`medium`—and resolves by dispatch mechanism. Native Claude dispatch remains supported.
For Codex-worker dispatch, `very smart` resolves to `gpt-5.6-sol` and `medium` resolves
to `gpt-5.6-terra`. A separate appendix explains the distinction and the CLI nuances,
while live discovery remains authoritative for availability and effort support.

## 2. Requirements   [ANCHOR]

| ID | Requirement | Source | Priority | Acceptance signal |
|----|-------------|--------|----------|-------------------|
| R1 | SDD exposes exactly two operator-facing model tiers: `very smart` and `medium`. | stated | must | Core guidance contains two tiers and no third routing tier. |
| R2 | Codex-worker routing maps `very smart` to `gpt-5.6-sol` and `medium` to `gpt-5.6-terra`. | stated | must | Codex appendix states both exact mappings. |
| R3 | Claude Code remains a supported coordinator and native subagent dispatch path, resolving `very smart` to `opus` and `medium` to `sonnet`. | stated + existing skill convention | must | Core guidance gives both native aliases, distinguishes native Claude dispatch from Codex-worker dispatch, and does not require Codex. |
| R4 | Design/gate work retains a mandatory `very smart` floor; normal implementation and review default to `medium`, with justified escalation. | stated + D1 | must | Role table and scenarios preserve the gate floor and advisory routing. |
| R5 | Codex selection validates model availability and effort support from the daemon's live model list and never silently substitutes another model. | discovered | must | Appendix states discovery, validation, and explicit failure behavior. |
| R6 | Detailed Codex model and CLI guidance lives outside the core SKILL so the primary workflow remains concise and harness-neutral. | stated | should | Core skill links one separate appendix; mechanics remain in references. |
| R7 | Guidance must not publish a broad model catalog or time-sensitive pricing claims. | stated + D2 | must | Appendix compares only Sol and Terra and defers volatile facts to live/official sources. |

## 3. Use cases   [ANCHOR]

| UC | As a role, I do this and see this | Exercises R# | Realized by §5 area(s) |
|----|-----------------------------------|--------------|------------------------|
| UC1 | As a Claude Code coordinator, I route an ordinary implementation to a native Claude `medium` subagent and complete the normal SDD review loop without starting Codex. | R1, R3, R4 | 5.1, 5.2 |
| UC2 | As a Claude Code coordinator using a Codex worker, I discover live models and start an ordinary implementation on `gpt-5.6-terra` with a supported effort. | R1, R2, R4, R5 | 5.1, 5.3 |
| UC3 | As a coordinator, I keep main-session brainstorming/design on native Claude `opus`; for a dispatched high-judgment review or gate, I select `very smart` and resolve it to Claude `opus` or Codex `gpt-5.6-sol` according to the explicitly selected dispatch mechanism. | R2, R3, R4 | 5.1, 5.2, 5.3 |
| UC4 | As an operator reading the skill, I can understand Sol versus Terra and correctly pin a Codex session/turn without reading a catalog of unrelated models. | R2, R5, R6, R7 | 5.3, 5.4 |
| UC5 | As a coordinator whose required Codex tier is absent or lacks the requested effort, I receive an explicit blocker rather than an unannounced fallback. | R5 | 5.3, 5.4 |

## 4. Approach narrative

The design separates stable routing policy from provider-specific resolution. The core
SDD skill names only two semantic tiers and assigns roles to them, preserving one
workflow across dispatch mechanisms. Native Claude dispatch resolves those semantic
tiers using the Claude models available to Claude Code. Only when the operator or plan
explicitly selects a Codex worker does the linked appendix map the tiers to Sol and
Terra. The existing Codex worker reference continues to own daemon/session/recovery
mechanics, while the new appendix owns model meaning, live validation, and focused
model/effort examples. This split keeps Claude Code present, makes Codex routing
concrete, and contains volatile provider details behind a conditional link.

## 5. Design

### 5.1 Two-tier role policy

This area supplies the stable vocabulary that every dispatch mechanism resolves.

- **Design:** Replace three-way cheap/standard/most-capable guidance with exactly two
  tiers. `medium` is the default for planned implementation, routine integration,
  ordinary debugging, and per-task review. `very smart` is mandatory for architecture,
  design reasoning, spec/plan/final/deviation gates, and is an available escalation for
  unusually ambiguous or high-risk task work. Every active reviewer, checkride,
  brainstorming, and self-brainstorming prompt that selects a model uses the same tier
  vocabulary; no dependent prompt retains a provider-relative third policy.
- **Interface / contract:** Every dispatch explicitly selects one of the two tiers;
  omission/inheritance is still prohibited.
- **Depends on:** 5.2 and 5.3 for mechanism-specific resolution.
- **Serves:** R1, R4 · **Governed by:** D1, D2, D6, D7 · **Realizes:** UC1, UC2, UC3

### 5.2 Claude Code compatibility

This area preserves Claude Code as coordinator and native subagent provider while the
shared policy becomes more precise.

- **Design:** The core skill remains harness-neutral at the role-policy layer. For
  native Claude Code subagents, `very smart` resolves to the stable `opus` alias and
  `medium` resolves to the stable `sonnet` alias. The coordinator passes that alias
  explicitly in every dispatch. If the required alias is unavailable, the dispatch is
  blocked and reported; it is not silently collapsed to the other tier. Selecting
  native Claude does not require the Codex daemon. Main-session brainstorming and
  design also remain native Claude work and use `opus`; Codex workers are explicitly
  delegated implementation or review/gate roles, not a substitute for that scope.
- **Interface / contract:** Codex model IDs never appear as requirements for native
  Claude dispatch. Claude Code continues to coordinate Codex workers when those are
  explicitly selected.
- **Depends on:** 5.1.
- **Serves:** R3, R4, R6 · **Governed by:** D4, D5 · **Realizes:** UC1, UC3

### 5.3 Codex tier resolution

This area turns the stable tier vocabulary into exact, validated Codex worker choices.

- **Design:** A separate appendix defines `very smart = gpt-5.6-sol` and
  `medium = gpt-5.6-terra`. Before dispatch, the coordinator runs live `model list`,
  confirms that the selected ID exists, and chooses only a returned supported effort.
  Missing models or unsupported efforts are explicit blockers; no other model is
  silently promoted into a tier.
- **Interface / contract:** The appendix compares only Sol and Terra, labels live
  discovery authoritative for runtime capability, and does not recommend Luna or
  older generations.
- **Depends on:** Codex worker daemon and 5.1.
- **Serves:** R2, R4, R5, R7 · **Governed by:** D2, D3, D4 · **Realizes:** UC2, UC3, UC4, UC5

### 5.4 Reference boundary and CLI appendix

This area keeps policy discoverable without duplicating the broker's full operating
manual.

- **Design:** `SKILL.md` carries the role policy and a conditional link.
  `codex-model-selection.md` explains Sol versus Terra, live discovery, effort as an
  independent axis, model pinning on session/turn calls, and resumed-session behavior.
  `codex-worker.md` remains canonical for daemon lifecycle, JSON field extraction,
  worktrees, observation, control, and recovery. Cross-links prevent either appendix
  from pretending to be the full workflow.
- **Interface / contract:** Examples use the real CLI surface but do not change it.
  Pricing and exhaustive model tables are out of scope.
- **Depends on:** 5.1 and 5.3.
- **Serves:** R5, R6, R7 · **Governed by:** D2, D3 · **Realizes:** UC4, UC5

## 6. Decisions

### D1 — Advisory role routing with mandatory gate floor   (status: locked)

- **Decision:** Default normal implementation/review to the lower tier, allow justified
  escalation, and require the upper tier for architecture/design/gate work.
- **Alternatives:** Strict routing gains uniformity but loses task-sensitive judgment;
  advisory routing gains task-sensitive judgment but sacrifices absolute uniformity.
- **Why:** Gate misses are expensive and late, while most well-specified task work does
  not require the frontier model.
- **Revisit-when:** Representative SDD evaluations show another rule improves success,
  latency, or total cost.

### D2 — Two operator-facing model tiers only   (status: locked)

- **Decision:** Present only `very smart` and `medium`.
- **Alternatives:** A model-by-model catalog gains completeness but sacrifices a stable,
  memorable rule; two semantic tiers gain compactness but deliberately omit niche
  model choices.
- **Why:** Two semantic choices are sufficient for the requested SDD routing decision.
- **Revisit-when:** Live availability or measured SDD outcomes show a third tier is
  operationally necessary.

### D3 — Pin the Codex tiers to Sol and Terra   (status: locked)

- **Decision:** Resolve `very smart` to `gpt-5.6-sol` and `medium` to
  `gpt-5.6-terra`; do not silently substitute other models.
- **Alternatives:** Dynamic best-fit mapping gains tolerance of catalog changes but
  sacrifices predictable tier behavior; exact mapping gains clarity but blocks when a
  pinned model is unavailable.
- **Why:** Exact IDs produce a clear, testable contract, and the broker can validate
  them through live discovery.
- **Revisit-when:** Either ID is unavailable/renamed or measured evaluations justify a
  new mapping.

### D4 — Preserve Claude Code through mechanism-specific resolution   (status: locked)

- **Decision:** Keep semantic tiers in the core skill, resolve them to Claude choices
  for native dispatch and to Sol/Terra only for explicitly selected Codex workers.
- **Alternatives:** Codex-only core guidance gains one literal mapping but sacrifices
  the existing Claude path; semantic tiers resolved per mechanism preserve both paths
  but require a small provider-specific appendix.
- **Why:** Claude Code remains coordinator by explicit requirement, and the established
  Codex broker is an opt-in worker path rather than a replacement harness.
- **Revisit-when:** SDD adopts one mandatory execution harness or native Claude model
  selection disappears.

### D5 — Resolve native Claude tiers with stable aliases   (status: locked)

- **Decision:** Native Claude dispatch resolves `very smart` to `opus` and `medium` to
  `sonnet`, passes the alias explicitly, and blocks rather than silently substitutes
  when the required alias is unavailable. Main-session design remains Claude `opus`.
- **Alternatives:** Exact aliases gain deterministic, reviewable dispatch at the
  sacrifice of automatic fallback; relative “corresponding tier” wording gains catalog
  flexibility but sacrifices an enforceable medium-tier contract.
- **Why:** The same two-tier policy must be actionable on Claude Code as well as Codex,
  and these stable aliases already appear in Superdev's Claude guidance.
- **Revisit-when:** Claude Code changes or removes either alias.

### D6 — Migrate every active routing consumer atomically   (status: locked)

- **Decision:** Update every active Superdev prompt/reference that selects a model to
  use the shared two-tier policy in the same implementation task.
- **Alternatives:** Central-only editing gains a smaller diff but sacrifices contract
  consistency; atomic migration gains one enforceable policy but touches more linked
  documentation.
- **Why:** A stale reviewer or checkride prompt can override the central skill at the
  exact high-judgment boundary this change is meant to protect.
- **Revisit-when:** A new consumer requires a deliberately different policy and the
  anchor is amended first.

### D7 — Include synonym-bearing tool references   (status: locked)

- **Decision:** Treat the checkride executor prompt and `using-superdev` Codex routing
  reference as active consumers, and structurally reject their retired synonyms and
  Luna/fallback policy.
- **Alternatives:** Literal phrase inventory gains simplicity but misses semantic
  aliases; semantic inventory gains complete enforcement at the cost of a broader
  search/test list.
- **Why:** Both files directly select worker models and can bypass D2/D3 even though
  they use different words from the central policy.
- **Revisit-when:** The anchor intentionally adds a model or tier.

### D8 — Validate through checkpoint reviewers   (status: locked)

- **Decision:** Use a focused structural RED/GREEN check plus fresh semantic reviewers
  at the documentation checkpoint instead of a large repeated model-call campaign.
- **Alternatives:** Repeated control/before/after calls gain variance measurements but
  cost disproportionate time; checkpoint reviewers gain focused application and
  consistency judgment but do not produce a statistical distribution.
- **Why:** The operator explicitly calibrated the validation method for this focused
  skill-documentation change while retaining independent review.
- **Revisit-when:** A future regression shows checkpoint review misses routing failures.

### D9 — Separate the two Codex dispatch mechanisms   (status: locked)

- **Decision:** Native Codex-harness `spawn_agent` guidance and Claude-coordinated local
  broker guidance share Sol/Terra mappings but retain distinct lifecycle/discovery
  instructions and name that boundary explicitly.
- **Alternatives:** Forcing broker mechanics into the Codex harness reference gains one
  apparent path but breaks native dispatch; explicit separation gains correctness at
  the cost of one extra boundary sentence.
- **Why:** The checkpoint reviewer demonstrably conflated the two mechanisms, while
  `using-superdev` proves the tools reference is harness-specific.
- **Revisit-when:** Both mechanisms are actually unified.

## 7. Assumptions & open questions

| ID | Assumption / question | Affects | Status |
|----|----------------------|---------|--------|
| A1 | Claude Code exposes the stable `opus` and `sonnet` dispatch aliases used by the existing Superdev prompt conventions. | R3, R4 / UC1, UC3 / D4, D5 / §5.2 | verified in existing skill references (`skills/brainstorming/spec-document-reviewer-prompt.md`, `skills/writing-skills/anthropic-best-practices.md`); absence at runtime becomes a blocker rather than silent tier collapse |
| A2 | The Codex daemon's live model response remains the authoritative source for model IDs and supported efforts. | R5 / UC2, UC5 / D3 / §5.3 | verified by `docs/superdev/specs/2026-08-18-codex-worker-server-design.md` R8/AH2 and its tracked checkride receipt |

## 8. Not doing

- A third `cheap` tier — rejected by D2; reconsider only under D2's revisit trigger.
- Recommendations for Luna, legacy generations, or every discovered model — rejected
  because the requested surface is exactly two tiers.
- Static pricing, latency, context-window, or effort matrices — rejected because they
  are volatile and live/official sources are authoritative.
- Automatic fallback from a missing Sol/Terra model — rejected because it silently
  changes the meaning of a tier; an operator may make an explicit revised choice.
- Changes to Codex worker RPC or CLI commands — unnecessary; this work documents how
  to use the existing surface.

## 9. Acceptance — hints & receipts   [ANCHOR: the hints]

| # | Acceptance hint (operator terms) | Proves | Lane | Receipt (filled at gate) |
|---|----------------------------------|--------|------|--------------------------|
| AH1 | An ordinary native Claude implementation can be routed through SDD at the medium tier without a Codex dependency. | UC1 / R1, R3, R4 | fast | Structural GREEN: `SddModelSelectionTests.test_core_skill_links_two_tier_codex_appendix_and_preserves_claude` (`tests/codex-worker/test_skill_integration.py:193`); native `medium`/`sonnet` and no-daemon contract at `skills/subagent-driven-development/SKILL.md:120-138`. Fresh semantic checkpoint pending coordinator. |
| AH2 | An ordinary Codex implementation resolves the medium tier to Terra after validating the live model and effort. | UC2 / R1, R2, R4, R5 | fast | Structural GREEN: `SddModelSelectionTests.test_codex_appendix_defines_only_sol_and_terra_tier_mappings` and `test_codex_appendix_requires_live_effort_validation_and_no_fallback` (`tests/codex-worker/test_skill_integration.py:206-227`); Terra mapping and live validation at `skills/subagent-driven-development/codex-model-selection.md:10-13, 27-33, 40-44`. Fresh semantic checkpoint pending coordinator. |
| AH3 | Main-session brainstorming/design stays on Claude `opus`, while a dispatched high-judgment review or gate resolves the mandatory very-smart tier to Claude `opus` or Codex Sol according to the explicitly selected mechanism. | UC3 / R2, R3, R4 | fast | Structural GREEN: `SddModelSelectionTests.test_core_skill_links_two_tier_codex_appendix_and_preserves_claude` (`tests/codex-worker/test_skill_integration.py:193`); native main-session and dispatch split at `skills/subagent-driven-development/SKILL.md:123-138`, Sol mapping at `skills/subagent-driven-development/codex-model-selection.md:10-13, 47-54`. Fresh semantic checkpoint pending coordinator. |
| AH4 | A reader can explain Sol versus Terra and pin model plus effort using the focused appendix, without a third tier or unrelated-model catalog. | UC4 / R2, R5, R6, R7 | fast | Structural GREEN: `SddModelSelectionTests.test_codex_appendix_defines_only_sol_and_terra_tier_mappings` and `test_codex_appendix_requires_live_effort_validation_and_no_fallback` (`tests/codex-worker/test_skill_integration.py:206-227`); focused distinction/pinning at `skills/subagent-driven-development/codex-model-selection.md:10-20, 35-77`. Fresh semantic checkpoint pending coordinator. |
| AH5 | Missing pinned models and unsupported efforts stop with an explicit, actionable blocker rather than silent substitution. | UC5 / R5 | fast | Structural GREEN: `SddModelSelectionTests.test_codex_appendix_requires_live_effort_validation_and_no_fallback` (`tests/codex-worker/test_skill_integration.py:213-227`); explicit block/no-substitution at `skills/subagent-driven-development/codex-model-selection.md:30-33`. Fresh semantic checkpoint pending coordinator. |
| AH6 | If native Claude lacks the required `opus` or `sonnet` alias, dispatch stops with an explicit blocker rather than silently collapsing to the other tier. | UC1, UC3 / R3, R4 | fast | Structural GREEN: `SddModelSelectionTests.test_core_skill_links_two_tier_codex_appendix_and_preserves_claude` (`tests/codex-worker/test_skill_integration.py:193`); native alias blocker at `skills/subagent-driven-development/SKILL.md:131-133`. Fresh semantic checkpoint pending coordinator. |

## 10. Drift protocol

Sections 1–3 and the §9 acceptance hints are the anchor and are never silently edited
to match implementation. In this human-in-loop change, a material anchor deviation is
pushed to the human before finishing.

For changes in §§4–8:

1. Identify the governing D# and test its revisit trigger.
2. Append the build fork to the decision log with the next D-number.
3. Amend the affected design area and mark superseded decisions explicitly.
4. If the change reaches an R#, UC#, or acceptance hint, stop and obtain human
   direction rather than weakening the anchor silently.
