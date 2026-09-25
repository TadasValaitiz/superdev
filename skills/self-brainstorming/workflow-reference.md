# Self-Brainstorming Workflow Reference — one angle per run

ONE workflow run brainstorms ONE agreed angle and writes its angle file. Grounding, the
agenda, the between-angle checks (corpus, architect ASK, human), the shape, review and
summary are the CONTROLLER's steps in SKILL.md "The phases" — not in this script. Keep the
schemas and mechanics intact — they ARE the protocol (the per-angle ratchet, the evidence
tiers, the hot angle file).

## Inputs (pass via `args`)

```json
{
  "topic": "short-kebab-topic",
  "brief": "the problem statement / idea, as given",
  "repoRoot": "/abs/path",
  "specDir": "docs/superdev/specs",
  "censusPath": "the committed census",
  "angle": { "n": 2, "slug": "…", "centralQuestion": "…", "whyItMatters": "…", "boundaries": "…" },
  "previousAngles": ["paths of the angle files already closed, in order"],
  "systemDesign": ["corpus passages governing this angle — path:line, quoted by the controller"],
  "architectAnswers": ["answers received since the last angle, with their D#/pointer"],
  "openQuestions": ["carried questions the controller did not block on"],
  "dStart": 12,
  "maxRounds": 6,
  "todayISO": "YYYY-MM-DD",
  "nowISO": "full ISO timestamp for log stamps"
}
```

`dStart` is the next free D# (the controller reads it from the decision log), so lock ids
stay monotonic across runs. `maxRounds` defaults to 6; lower it for a narrow angle.

## Schemas

```js
const Q_SCHEMA = { type: 'object', required: ['locks','reconciled'], properties: {
  locks: { type: 'array', items: { type: 'object',
    required: ['id','title','decision','alternatives','why','status','revisitWhen'],
    properties: {
      id:           { type: 'string' },   // "D12" — monotonic from args.dStart, script-verified
      title:        { type: 'string' },
      decision:     { type: 'string' },
      alternatives: { type: 'array', items: { type: 'string' } }, // each with gains/sacrifices
      why:          { type: 'string' },
      status:       { enum: ['locked','provisional'] },  // provisional iff resting on ASSUMPTION
      holistic:     { type: 'boolean' },  // HYBRID mode: human-owned fork -> provisional + queued
      restsOn:      { type: 'string' },   // evidence cite, corpus path:line, or "A3"
      revisitWhen:  { type: 'string' }
    }}},
  reconciled:   { type: 'boolean' },      // true → no remaining unknown IN THIS ANGLE changes what gets built
  question:     { type: 'string' },       // required when !reconciled — ONE question, inside this angle
  whyItMatters: { type: 'string' },
  options:      { type: 'array', items: { type: 'string' } }, // 2-3 concrete options w/ trade-offs
  parked:       { type: 'array', items: { type: 'string' } }, // belongs to ANOTHER angle
  askArchitect: { type: 'array', items: { type: 'string' } }, // corpus discrepancies / architect-only questions
  newAngle:     { type: 'object' }        // proposed, never worked here
}}

const A_SCHEMA = { type: 'object', required: ['answer','tier','alternatives','recommendation'], properties: {
  answer:         { type: 'string' },
  tier:           { enum: ['EVIDENCE','REASONED','ASSUMPTION'] },
  evidence:       { type: 'array', items: { type: 'string' } }, // files read / probes run / corpus cites
  assumptionText: { type: 'string' },     // required when tier=ASSUMPTION
  alternatives:   { type: 'array', items: { type: 'string' } },
  recommendation: { type: 'string' },
  risks:          { type: 'string' }
}}

const CLOSE_SCHEMA = { type: 'object',
  required: ['anglePath','reconciledOutcome','newForks','askArchitect'], properties: {
  anglePath:         { type: 'string' },  // the angle file, written and COMMITTED
  reconciledOutcome: { type: 'string' },
  newForks:          { type: 'array', items: { type: 'string' } }, // forks the WRITING surfaced
  askArchitect:      { type: 'array', items: { type: 'string' } }, // for the controller to send
  parked:            { type: 'array', items: { type: 'string' } },
  newAngle:          { type: 'object' }
}}
```

## Script skeleton

```js
export const meta = {
  name: 'self-brainstorm-angle',
  description: 'Brainstorm ONE agreed angle: bounded questioner-responder loop, then write and commit its angle file',
  phases: [
    { title: 'Dialogue', detail: 'question <-> evidence-tiered answer, locking per round, this angle only' },
    { title: 'Close',    detail: 'reconcile the angle; write + commit the angle file' },
  ],
}

phase('Dialogue')
const ledger = [], assumptions = [], parked = [], asks = []
let last = null, reconciled = false, round = 0, dHwm = args.dStart - 1, newAngle = null

while (!reconciled && round < (args.maxRounds ?? 6)
       && (!budget.total || budget.remaining() > 30000)) {
  round++
  const q = await agent(questionerPrompt(args, ledger, assumptions, last),
                        { schema: Q_SCHEMA, label: `q${round}`, model: 'opus' })
  for (const lock of q.locks) {              // script-enforced ratchet hygiene
    const n = parseInt(lock.id.slice(1), 10)
    if (!(n > dHwm)) throw new Error(`non-monotonic lock id ${lock.id}`)
    dHwm = n
    if (last?.tier === 'ASSUMPTION' && lock.status === 'locked')
      lock.status = 'provisional'            // the iron rule, enforced in code
    ledger.push({ ...lock, round })
  }
  parked.push(...(q.parked ?? [])); asks.push(...(q.askArchitect ?? []))
  if (q.newAngle) newAngle = q.newAngle    // reported to the controller, never worked here
  if (q.reconciled) { reconciled = true; break }
  last = await agent(responderPrompt(args, q, ledger),
                     { schema: A_SCHEMA, label: `r${round}`, model: 'sonnet' })
  if (last.tier === 'ASSUMPTION')
    assumptions.push({ id: `A-${args.angle.slug}-${assumptions.length + 1}`, text: last.assumptionText, round })
  log(`round ${round}: ${ledger.length} locked, ${assumptions.length} assumptions`)
}

phase('Close')
const close = await agent(closePrompt(args, ledger, assumptions, reconciled),
                          { schema: CLOSE_SCHEMA, label: 'close', model: 'opus' })

return { angle: args.angle.slug, anglePath: close.anglePath, rounds: round,
         reconciled, locks: ledger, nextD: dHwm + 1, assumptions,
         newForks: close.newForks, askArchitect: [...asks, ...close.askArchitect],
         parked: [...parked, ...(close.parked ?? [])], newAngle: close.newAngle ?? newAngle,
         next: 'CONTROLLER: read the angle file, check the corpus, send any architect ASK, then launch the next angle' }
```

## Role prompts

**questionerPrompt(args, ledger, assumptions, lastAnswer)** — the design authority, one angle wide:

```
You are the QUESTIONER for ONE angle of a self-brainstorm — the design authority.
THIS ANGLE: [central question · why it matters · boundaries]
Census: [path]. Previous angle files (settled — do not reopen without new information): [paths].
System-design passages governing this angle (the architect keeps them correct): [path:line …].
Architect answers since the last angle: [...]  Carried open questions: [...]
This angle's ledger so far: [...]  Open assumptions: [...]  Previous answer: [...]

1. LOCK: from the previous answer, emit decisions now settled — id (next D#), decision,
   alternatives WITH gains/sacrifices, why, revisitWhen. ASSUMPTION-tier → provisional, restsOn the A#.
2. ASK: the ONE question, INSIDE THIS ANGLE, that most reduces its remaining uncertainty —
   2-3 concrete options (mechanism, an example from THIS project, consequences). YAGNI.
3. PARK what belongs to another angle; put a corpus discrepancy or an architect-only
   question in askArchitect (never decide against the corpus silently); propose a genuinely
   new angle in newAngle — never work it here.
4. RECONCILED: when no remaining unknown in THIS angle would change what gets built, say so.
```

**responderPrompt(args, q, ledger)** — the grounded oracle, one angle wide:

```
You are the RESPONDER — a grounded oracle, not an imaginative one — for ONE angle.
Angle: [central question · boundaries]  Question: [...] Options: [...]
Previous angle files and system-design passages (respect them): [...]  This angle's ledger: [...]
Answer FROM EVIDENCE: read the code/docs/specs/corpus, run read-only probes, cite what you
consulted. Tier honestly: EVIDENCE / REASONED / ASSUMPTION (state it plainly; "I could not
determine X" is acceptable). Give alternatives, a recommendation with reasoning, and its risks.
```

**closePrompt(args, ledger, assumptions, reconciled)** — close and write hot:

```
CLOSE angle [n · slug] ([reconciled | CAPPED at the round limit — say so in the file]).
State what was reconciled, in prose. WRITE the angle file NOW to
[specDir]/[todayISO]-[topic]-angle-[NN]-[slug].md per skills/brainstorming/item-angle-template.md
— mental model; the journey with `### LOCKED — claim` + "this means…" and a TYPED SKETCH for
every shape-bearing ruling; the invariants it relies on; cannot-do; mismatch; collisions it
did not settle; the provisional locks with their A#; the open architect questions. If the
WRITING surfaces a new fork, list it in newForks — never write it in as decided.
COMMIT the angle file (explicit path) before returning.
```

## Mechanics notes

- **One angle per run:** the run's context is one angle wide (the angle, the census, the
  previous angle FILES by path, the governing corpus passages). That is the token control.
- **The angle file is the hand-off:** the next run reads it; a paused brainstorm resumes from
  the last committed angle file, in this or another session.
- **Between runs is where the controller works:** reading the angle file, the corpus check,
  the architect ASK, the human's questions, and the next run's inputs (SKILL.md step 4).
- **Resume:** a run is resumable (`resumeFromRunId`); if it dies before Close, resume it.
- **Budget:** `maxRounds` (default 6) caps the angle; a capped angle is written as CAPPED,
  never passed off as reconciled.
- **Model/effort:** the Responder pins `sonnet` (`medium`); the Questioner and Close pin
  `opus` (`very smart`). Native Claude roles, not Codex-worker dispatches.
