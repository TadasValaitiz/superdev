# Self-Brainstorming Workflow Reference

The script skeleton, output schemas, and role prompts. Adapt the prompts' bracketed
slots to the task; keep the schemas and the loop mechanics intact — they ARE the
protocol (the ratchet, the evidence tiers, the saturation contract).

## Inputs (pass via `args`)

```json
{
  "topic": "short-kebab-topic",
  "brief": "the problem statement / idea, as given",
  "repoRoot": "/abs/path",
  "specDir": "docs/superdev/specs",
  "maxRounds": 12,
  "todayISO": "YYYY-MM-DD",
  "nowISO": "full ISO timestamp for log stamps"
}
```

(`todayISO`/`nowISO` are passed in because workflow scripts cannot call `Date.now()`.)
Scale `maxRounds` to the problem: ~6 for a contained utility, 10–15 for a subsystem,
20+ only with an explicit budget directive.

## Schemas

```js
const GROUND_SCHEMA = { type: 'object', required: ['currentState','constraints','priorArt','unknowns'], properties: {
  currentState: { type: 'string' },                       // what exists today, cited
  constraints:  { type: 'array', items: { type: 'string' } },
  priorArt:     { type: 'array', items: { type: 'string' } }, // related specs/decision logs found
  unknowns:     { type: 'array', items: { type: 'string' } }  // load-bearing open questions
}}

const Q_SCHEMA = { type: 'object', required: ['locks','saturated'], properties: {
  locks: { type: 'array', items: { type: 'object',
    required: ['id','title','decision','alternatives','why','status','revisitWhen'],
    properties: {
      id:           { type: 'string' },   // "D7" — monotonic, script-verified
      title:        { type: 'string' },
      decision:     { type: 'string' },
      alternatives: { type: 'array', items: { type: 'string' } }, // each with gains/sacrifices
      why:          { type: 'string' },
      status:       { enum: ['locked','provisional'] },  // provisional iff resting on ASSUMPTION
      holistic:     { type: 'boolean' },  // HYBRID mode: true = human-owned fork -> force provisional + queue for R-H
      restsOn:      { type: 'string' },   // evidence cite or "A3"
      revisitWhen:  { type: 'string' }
    }}},
  saturated:  { type: 'boolean' },        // true → no remaining unknown changes what gets built
  question:   { type: 'string' },         // required when !saturated — ONE question
  whyItMatters: { type: 'string' },       // what this question de-risks
  options:    { type: 'array', items: { type: 'string' } } // 2-3 concrete options w/ trade-offs
}}

const A_SCHEMA = { type: 'object', required: ['answer','tier','alternatives','recommendation'], properties: {
  answer:         { type: 'string' },
  tier:           { enum: ['EVIDENCE','REASONED','ASSUMPTION'] },
  evidence:       { type: 'array', items: { type: 'string' } }, // files read / probes run / cites
  assumptionText: { type: 'string' },     // required when tier=ASSUMPTION: the assumption, stated plainly
  alternatives:   { type: 'array', items: { type: 'string' } }, // follow-up alternatives w/ trade-offs
  recommendation: { type: 'string' },
  risks:          { type: 'string' }
}}

const PATHS_SCHEMA = { type: 'object', required: ['specPath','logPath'], properties: {
  specPath: { type: 'string' }, logPath: { type: 'string' } }}

const REVIEW_SCHEMA = { type: 'object', required: ['status','blocking','advisory'], properties: {
  status: { enum: ['Approved','IssuesFound'] },
  blocking: { type: 'array', items: { type: 'string' } },
  advisory: { type: 'array', items: { type: 'string' } } }}
```

## Script skeleton

```js
export const meta = {
  name: 'self-brainstorm',
  description: 'Questioner-responder brainstorm loop that locks decisions and writes a ratification-ready design spec',
  phases: [
    { title: 'Explore',    detail: 'ground the topic in the repo' },
    { title: 'Dialogue',   detail: 'question ↔ evidence-tiered answer, locking per round' },
    { title: 'Synthesize', detail: 'write design doc (two passes) + decision log' },
    { title: 'Review',     detail: 'spec reviewer over both artifacts' },
  ],
}

phase('Explore')
const ground = await agent(
  `You are grounding a design brainstorm. Topic: ${args.topic}. Brief: ${args.brief}
   Repo: ${args.repoRoot}. Read the relevant code, docs, prior specs and decision logs
   (${args.specDir}). Report ONLY what you actually read — cite paths. List the
   load-bearing unknowns a designer must resolve.`,
  { schema: GROUND_SCHEMA, label: 'ground' })

phase('Dialogue')
const ledger = [], assumptions = []
let last = null, saturated = false, round = 0, dHwm = 0

while (!saturated && round < (args.maxRounds ?? 12)
       && (!budget.total || budget.remaining() > 30000)) {
  round++
  const q = await agent(questionerPrompt(ground, ledger, assumptions, last),
                        { schema: Q_SCHEMA, label: `q${round}`, phase: 'Dialogue' })
  for (const lock of q.locks) {              // script-enforced ratchet hygiene
    const n = parseInt(lock.id.slice(1), 10)
    if (!(n > dHwm)) throw new Error(`non-monotonic lock id ${lock.id}`)
    dHwm = n
    if (last?.tier === 'ASSUMPTION' && lock.status === 'locked')
      lock.status = 'provisional'            // the iron rule, enforced in code
    ledger.push({ ...lock, round })
  }
  if (q.saturated) { saturated = true; break }
  last = await agent(responderPrompt(q, ledger, ground),
                     { schema: A_SCHEMA, label: `a${round}`, phase: 'Dialogue' })
  if (last.tier === 'ASSUMPTION')
    assumptions.push({ id: `A${assumptions.length + 1}`, text: last.assumptionText, round })
  log(`round ${round}: ${ledger.length} locked, ${assumptions.length} assumptions`)
}
log(saturated ? `saturated after ${round} rounds` : `STOPPED UNSATURATED at round ${round}`)

phase('Synthesize')
const paths = await agent(
  `Write BOTH brainstorm artifacts for topic "${args.topic}" (date ${args.todayISO}).
   Templates (follow them exactly):
   - design doc:    <plugin>/skills/brainstorming/design-doc-template.md
   - decision log:  <plugin>/skills/brainstorming/decision-log-template.md
   Inputs: brief=${args.brief}; grounding=${JSON.stringify(ground)};
   ledger=${JSON.stringify(ledger)}; assumptions=${JSON.stringify(assumptions)};
   stamp entries ${args.nowISO}, phase: brainstorm, decided-by: self-brainstorm round N.
   Write the design doc in TWO PASSES: pass 1 the shape + anchor (§1 intent, §2
   requirements, §3 use cases, §4 narrative, §5 design, §9 acceptance hints); pass 2 the
   enrichment (§2 requirements, §3 use cases, §6 decisions w/ revisit-when, §7
   assumptions, §8 not-doing, §9 acceptance hints, and the narrative link-sentence
   opening every §5 area).
   Header: Origin: self-brainstorm. Save under ${args.repoRoot}/${args.specDir}/.
   Do NOT commit.`,
  { schema: PATHS_SCHEMA, label: 'synthesize' })

phase('Review')
let review = await agent(reviewerPrompt(paths), { schema: REVIEW_SCHEMA, label: 'review' })
if (review.status === 'IssuesFound') {
  await agent(`Fix these blocking issues in ${paths.specPath} and ${paths.logPath},
    amending (never erasing) per the templates: ${JSON.stringify(review.blocking)}`,
    { label: 'fix' })
  review = await agent(reviewerPrompt(paths), { schema: REVIEW_SCHEMA, label: 're-review' })
}

return { ...paths, rounds: round, saturated, locked: ledger.length,
         provisional: ledger.filter(l => l.status === 'provisional').length,
         assumptions, review }
```

## Role prompts

**questionerPrompt(ground, ledger, assumptions, lastAnswer)** — the design authority:

```
You are the QUESTIONER in a self-brainstorming loop — the design authority.
Topic/brief: [...]  Grounding: [...]
Decision ledger so far (settled — do not reopen without new information): [...]
Open assumptions: [...]  Previous answer to your last question: [...]

1. LOCK: from the previous answer, emit any decisions now settled — id (next D#),
   decision, alternatives WITH gains/sacrifices, why, revisitWhen (a concrete reopening
   trigger — "never" must be argued). If the answer's tier was ASSUMPTION, status is
   provisional and restsOn names the A#.
2. ASK: the ONE question that most reduces remaining design uncertainty. Attach 2-3
   concrete options with trade-offs. Prefer forks that kill whole branches of the
   design space. YAGNI ruthlessly — do not explore features nobody asked for.
3. SATURATION: when no remaining unknown would change what gets built, say so
   (saturated: true, no question) instead of inventing further questions. Draining
   every conceivable topic is not the goal; a buildable, honest design is.
```

**responderPrompt(q, ledger, ground)** — the grounded oracle:

```
You are the RESPONDER in a self-brainstorming loop — a grounded oracle, not an
imaginative one. Question: [...] Options offered: [...]
Settled ledger (respect it): [...]  Repo: [...]

Answer FROM EVIDENCE: read the relevant code/docs/specs, run read-only probes, and
cite what you actually consulted. Tier your answer honestly:
EVIDENCE (grounded + cited) / REASONED (explicit inference from evidence) /
ASSUMPTION (could not ground it — state the assumption plainly in assumptionText;
NEVER dress a guess as fact; "I could not determine X" is an acceptable answer).
Give follow-up alternatives the questioner may not have seen, a recommendation with
reasoning, and the risks of your recommendation.
```

**reviewerPrompt(paths)** — instantiate the dispatch template in
`skills/brainstorming/spec-document-reviewer-prompt.md` with SPEC_FILE_PATH=paths.specPath,
DECISION_LOG_PATH=paths.logPath; request the REVIEW_SCHEMA fields as the output.

## Mechanics notes

- **Ledger-as-state, not transcript-as-state:** each round sends only the distilled
  ledger + latest exchange. Fresh eyes per round is deliberate (anti-anchoring); the
  workflow journal preserves the full exchange history for archaeology, and every lock
  lands in the durable decision log at synthesis.
- **Resume:** the run is resumable (`resumeFromRunId`) — completed rounds replay from
  cache. If a run dies pre-synthesis, resume rather than restart: the ledger rebuilds
  from cached calls at zero cost.
- **Budget scaling:** with a token directive, the `budget.remaining()` guard paces
  depth; without one, `maxRounds` is the knob. Report which limit ended the run.
- **Model/effort:** the Questioner (design authority) and the synthesis agent (writes
  the design doc) are native Claude Code `opus` (`very smart`) roles, matching
  brainstorming's design reasoning. The `review` agent reuses the spec-reviewer
  template, which already pins the `very smart` tier. The Responder needs tool
  diligence more than brilliance: native Claude Code `sonnet` (`medium`) is the
  calibrated choice there. These are native Claude roles, not Codex-worker dispatches.
