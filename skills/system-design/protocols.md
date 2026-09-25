# Protocols — the seam between altitudes, with worked examples

Every protocol: content in a file with ONE writer, plus a pointer message with a short summary. When a message and its file disagree, the file wins. The two surfaces never mix (D60): `docs/system-design/` is reconciled — grab-and-trust; `docs/orchestration/` is operational — stamped, prunable, never reconciled.

## The ledgers (orchestrator-written, from room reports — D51) {#row-schemas}

Rooms do NOT write any shared file. A room records findings in its OWN item files, and its reports carry them; the ORCHESTRATOR comprehends reports into typed ledgers in his space — he is their sole writer, and comprehension is the feature (only he sees across rooms, so he dedupes and clusters):

- **Residue ledger** — design-class findings; row kinds: `discrepancy | insight | duplicate-risk | question`. Each row cites the room report it came from. Disposition never edits a row: the handover's cluster list and the response block's verdicts cite row ids — those documents ARE the disposition record.
- **Process-feedback ledger** — rooms' R5 lines + his own `measurement` rows (charter→merge wall-clock, review cycles, blocked-wait, token sums); kinds: `friction | brief-gap | measurement | win`. Feeds brief adaptation immediately and `/superdev:self-improvement` in batch.
- **Plan-time ASK-ARCHITECT (D61):** a room that finds the corpus contradicted collects deviations in its own files during grounding→planning, then — after planning, before execution — sends the architect ASK-ARCHITECT directly: a summary + pointer; the orchestrator does not relay. Pointers, never paraphrase. The architect may act at once (per the mode law) or fold it to the next checkpoint.

## The checkpoint handover (orchestrator → architect) — ONE operational document {#checkpoint-handover}

`docs/orchestration/handovers/<milestone>-checkpoint-<n>.md`, orchestrator single-writer, write-once, pruned on the rolling window (D62). Declared from **rule + green lights + feel**. The old separate residue-collection document is DEAD — clusters live inline here (D60):

```markdown
# Handover — checkpoint 3
> OPERATIONAL RECORD — point-in-time, never reconciled. May be outdated the moment you
> read it. Design authority lives in docs/system-design/ (as of its last reconcile).

Green lights: item-3.1 ✓ · item-3.3 ✓   Rule trigger: regime-bridge side merged
Feel: contributions exhausted on this arc — nothing live is producing.

## WHAT WE GOT                                   [facts + the cross-room narrative]
merged: 3.1 regime-migration · warehouse-only-bars. The fee model did not hold — three
rooms independently hit its edges; the milestone's center of gravity moved…

## WHERE WE FEEL GAPS                            [feel, labelled as feel, by angle]
paper-wallet boundary is BLIND in the corpus; two clusters brushed it (angle-09 territory)

## UPCOMING FOCUS                                [what the next charters need]
want to charter: 3.3 bench core — blocked on M17 ruling + paper-wallet vision.
not blocked: 3.4 deploy prep — can charter today.

## MAP CLAIMS
M12 discharged — evidence: src/…/target_book.py:112 + transcript t3
M14 discharged — evidence: replay CLI journey, transcript t4

## CLUSTERS                                      [his authored grouping; rows cited, no rulings]
C1 regime-grant edge cases — rows R-14, R-17, R-22 → map row M14
C2 detector timeline leaks into deployable spec — row R-19 → map row M17 (KEEP — contested?)

## FACTS                                         [inlined; the recurring census is ephemeral]
census delta since reconcile abc1234: BLIND 3→0 · MISMATCH +2 (both fee seam)
charter→merge 2.1d avg · review cycles 2 · blocked-wait 4h
```

The message to the architect is a pointer. (All SHAs, ids, and figures above: SEED-ILLUSTRATIVE.)

## The response — a BLOCK inside the milestone decisions file, then the rulings (D60) {#checkpoint-response}

No response document exists. The sitting's answer opens a checkpoint block in `docs/system-design/…-architecture-decisions.md`, immediately followed by the D# entries it announces — response and rulings in the one file reconciliation already owns:

```markdown
## Checkpoint 3 — response (reconcile def5678)
Sections: GOT agree · GAPS agree, except the fee seam is worse than felt (D468) ·
FOCUS disagree — 2b before 3a; 3a's kernel depends on the fee ruling (D469)
Claims: M12 ACCEPTED · M14 REJECTED — receipt covers the read path only; re-claim with a
write-path receipt
Clusters: C1 → ruled, D466–D468 · C2 → deferred, needs the optimization vision ·
C4 → BOUNCED DOWN — item-work, no design fork; suggest one quick-fix item
Conformance notes: celebration 3 straddles a REPLACE boundary — advisory only.

### D466 — the fee model owns its rounding …
```

Claim verdicts and their reasons survive greppably — the map alone could never tell you WHY a claim was refused. **Bounce-downs land mechanically:** the orchestrator enters each bounced cluster in RESIDUAL TRIAGE (no individual items are filed) or routes them into an upcoming charter; his NEXT handover's WHAT WE GOT confirms the entry — the loop audits itself. The reconcile commit (SKILL.md step 5) closes the sitting; the message back is a pointer.

## The milestone handoff — SPLIT, no shared file (D49/D68) {#milestone-handoff}

Near-homophones, deliberately contrasted: **handovers** are per-CHECKPOINT operational companions (above), pruned; **handoffs** are per-MILESTONE close documents, in the never-pruned keep-set. The old two-section file is dead:

- **Orchestrator's half** — `docs/orchestration/handoffs/<milestone>.md`: what was built, map rows discharged, marker census, retro facts (measured), architectural suggestions harvested from unresolved residue.
- **Architect's half IS the birth of the next milestone's document set** — its INDEX, decisions file, census, glossary, continuation handover, first visions under the new slug in the flat corpus. Not a section anywhere; a working set coming into existence.

A milestone may not close without both halves; close is human-approved in every mode.

## The sitting protocol {#session-protocol}

Open mechanically (census script · stale-D# grep · the pending handover) → agenda by angle, entries as questions → census before forks → forks per the Fork Presentation Standard, ruled per the MODE LAW (SKILL.md#mode-law), D# per ruling with the full entry contract → visions before big rulings (any REPLACE/RESHAPE cluster >1 module) → response block → RECONCILIATION (statuses, banners, canon, census re-run) → the named reconcile commit. A sitting that skipped reconciliation is unfinished.
