# SDD Codex model selection — Design (anchor)

**Date:** 2026-08-19 · **Status:** draft
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
| R3 | Claude Code remains a supported coordinator and native subagent dispatch path. | stated | must | Core guidance distinguishes native Claude dispatch from Codex-worker dispatch without requiring Codex. |
| R4 | Design/gate work retains a mandatory `very smart` floor; normal implementation and review default to `medium`, with justified escalation. | stated + D1 | must | Role table and scenarios preserve the gate floor and advisory routing. |
| R5 | Codex selection validates model availability and effort support from the daemon's live model list and never silently substitutes another model. | discovered | must | Appendix states discovery, validation, and explicit failure behavior. |
| R6 | Detailed Codex model and CLI guidance lives outside the core SKILL so the primary workflow remains concise and harness-neutral. | stated | should | Core skill links one separate appendix; mechanics remain in references. |
| R7 | Guidance must not publish a broad model catalog or time-sensitive pricing claims. | stated + D2 | must | Appendix compares only Sol and Terra and defers volatile facts to live/official sources. |

## 3. Use cases   [ANCHOR]

| UC | As a role, I do this and see this | Exercises R# | Realized by §5 area(s) |
|----|-----------------------------------|--------------|------------------------|
| UC1 | As a Claude Code coordinator, I route an ordinary implementation to a native Claude `medium` subagent and complete the normal SDD review loop without starting Codex. | R1, R3, R4 | 5.1, 5.2 |
| UC2 | As a Claude Code coordinator using a Codex worker, I discover live models and start an ordinary implementation on `gpt-5.6-terra` with a supported effort. | R1, R2, R4, R5 | 5.1, 5.3 |
| UC3 | As a coordinator assigning architecture or a final gate, I select the `very smart` tier and resolve it to native Claude's top tier or `gpt-5.6-sol`, according to the dispatch mechanism. | R2, R3, R4 | 5.1, 5.2, 5.3 |
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
  unusually ambiguous or high-risk task work.
- **Interface / contract:** Every dispatch explicitly selects one of the two tiers;
  omission/inheritance is still prohibited.
- **Depends on:** 5.2 and 5.3 for mechanism-specific resolution.
- **Serves:** R1, R4 · **Governed by:** D1, D2 · **Realizes:** UC1, UC2, UC3

### 5.2 Claude Code compatibility

This area preserves Claude Code as coordinator and native subagent provider while the
shared policy becomes more precise.

- **Design:** The core skill remains harness-neutral. For native Claude subagents,
  `medium` and `very smart` resolve to the corresponding explicit Claude model choices
  exposed by Claude Code; the highest available Claude tier remains mandatory for
  design and gate roles. Selecting native Claude does not require the Codex daemon.
- **Interface / contract:** Codex model IDs never appear as requirements for native
  Claude dispatch. Claude Code continues to coordinate Codex workers when those are
  explicitly selected.
- **Depends on:** 5.1.
- **Serves:** R3, R4, R6 · **Governed by:** D4 · **Realizes:** UC1, UC3

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
  unrestricted choice gains flexibility but loses a reliable quality floor.
- **Why:** Gate misses are expensive and late, while most well-specified task work does
  not require the frontier model.
- **Revisit-when:** Representative SDD evaluations show another rule improves success,
  latency, or total cost.

### D2 — Two operator-facing model tiers only   (status: locked)

- **Decision:** Present only `very smart` and `medium`.
- **Alternatives:** A model-by-model catalog gains completeness but becomes harder to
  remember and easier to stale; three price/capability tiers add choice the operator
  explicitly declined.
- **Why:** Two semantic choices are sufficient for the requested SDD routing decision.
- **Revisit-when:** Live availability or measured SDD outcomes show a third tier is
  operationally necessary.

### D3 — Pin the Codex tiers to Sol and Terra   (status: locked)

- **Decision:** Resolve `very smart` to `gpt-5.6-sol` and `medium` to
  `gpt-5.6-terra`; do not silently substitute other models.
- **Alternatives:** Dynamic best-fit mapping gains tolerance of catalog changes but
  makes tier behavior unpredictable; listing all models violates D2.
- **Why:** Exact IDs produce a clear, testable contract, and the broker can validate
  them through live discovery.
- **Revisit-when:** Either ID is unavailable/renamed or measured evaluations justify a
  new mapping.

### D4 — Preserve Claude Code through mechanism-specific resolution   (status: locked)

- **Decision:** Keep semantic tiers in the core skill, resolve them to Claude choices
  for native dispatch and to Sol/Terra only for explicitly selected Codex workers.
- **Alternatives:** Codex-only core guidance gains one literal mapping but removes the
  existing Claude path; separate unrelated policies invite workflow drift.
- **Why:** Claude Code remains coordinator by explicit requirement, and the established
  Codex broker is an opt-in worker path rather than a replacement harness.
- **Revisit-when:** SDD adopts one mandatory execution harness or native Claude model
  selection disappears.

## 7. Assumptions & open questions

| ID | Assumption / question | Affects | Status |
|----|----------------------|---------|--------|
| A1 | Claude Code continues to expose at least two explicit model capability choices that can implement the semantic tiers. | R3, R4 / UC1, UC3 / D4 / §5.2 | ratified by human, 2026-08-19, as a required compatibility contract; absence becomes a harness blocker rather than silent tier collapse |
| A2 | The Codex daemon's live model response remains the authoritative source for model IDs and supported efforts. | R5 / UC2, UC5 / D3 / §5.3 | ratified by existing broker design and live acceptance evidence |

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
| AH1 | An ordinary native Claude implementation can be routed through SDD at the medium tier without a Codex dependency. | UC1 / R1, R3, R4 | fast | |
| AH2 | An ordinary Codex implementation resolves the medium tier to Terra after validating the live model and effort. | UC2 / R1, R2, R4, R5 | fast | |
| AH3 | Architecture and final-gate work resolve the mandatory very-smart tier to the correct provider-specific choice. | UC3 / R2, R3, R4 | fast | |
| AH4 | A reader can explain Sol versus Terra and pin model plus effort using the focused appendix, without a third tier or unrelated-model catalog. | UC4 / R2, R5, R6, R7 | fast | |
| AH5 | Missing pinned models and unsupported efforts stop with an explicit, actionable blocker rather than silent substitution. | UC5 / R5 | fast | |

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
