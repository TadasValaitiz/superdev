# Room retrospective — the PROCESS, not the code

Written by every room at R5 CLOSE, to `⟨retro dir⟩/YYYY-MM-DD-<room>-retro.md` (committed),
and pointed to in the R5 message. **Code-agnostic:** no feature detail except as evidence for
a process point. The orchestrator collects retros into its process-feedback ledger; the human
runs superdev:self-improvement over them from time to time — this file is how the skills
get better. Label every number MEASURED / REPORTED / JUDGEMENT; a guessed number is worse
than none.

## 1. The run in numbers
- Wall-clock from launch to close; time waiting (on whom: human · architect · another room · infra).
- Publishes; checkride legs; review rounds; fix-lane size at its peak.
- Test count before → after (per tier); helper tests deleted.

## 2. The biggest bottleneck
The ONE thing that cost the most time, with evidence (ledger lines, timestamps). Then the next two.

## 3. Was the design accurate?
- How many design questions surfaced during build or ride instead of at the design stop?
  Which should the angles have caught?
- Were the foundation angles / system-design passages right for this room? Wrong, missing, stale?
- Did the architecture summary and the human's review happen at the right moment?

## 4. Was the milestone / room cut right?
- Was the scope clear? Any boundary crossed, or work that belonged to another room?
- Dependencies discovered mid-flight that the upfront map should have shown?
- Was the room too big, too small, or split along the wrong seam?

## 5. Conflicts and coordination
- Code or file conflicts with other rooms or lanes: where, how often, what they cost.
- Waiting on other rooms, the architect, the orchestrator, the human: how long, and why.
- Messages that were missing, late, or unclear.

## 6. Testing
- Checkrides: how many, where placed, which were wasted (a surface later reworked)?
- Tests that slowed the work (legacy tests fought a change; helper tests that had to be kept alive).

## 7. Tooling and infrastructure
Stalls, sleeps, crashed sessions, broken helpers, slow gates — each with what it cost.

## 8. What to change
Concrete proposals, each naming WHERE it should land: a brief, a skill (which one), the
architect protocol, the orchestrator, the human's touchpoints. Mark each keep / change / drop.

## 9. What worked
The practices worth keeping, so a fix doesn't remove them.
