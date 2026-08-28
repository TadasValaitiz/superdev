# Decision Log Template

One decision log per work stream, created **at the start of brainstorming** (before the
design doc exists) and appended to through every later phase — spec, planning, and build.
It is the recall surface: when anyone asks "why is it built this way?" or a mid-build
change forces re-arbitration, this file holds the deeper thinking the spec distilled away.

**Rules:**

- **Append-only, chronological.** Never rewrite an entry; supersede it with a new one.
- **Capture at the moment of decision** — during brainstorming that means the entry is
  written when the fork is resolved in dialogue, not reconstructed afterward. Memory of
  reasoning decays within hours; the log is written while the reasoning is alive.
- **Shared numbering with the spec:** the spec's §6 Decisions are the distilled subset of
  this log, same D-numbers. The log may hold more (dead ends, reversed calls, small forks
  that never graduate to the spec); the spec never holds a D# the log lacks.
- **Every phase appends:** brainstorm and spec-writing forks (phase: brainstorm/spec),
  planning forks the spec didn't settle (phase: plan), build-time deviations and
  drift-protocol outcomes (phase: build).
- **Real timestamps** from the clock (`date -u +%Y-%m-%dT%H:%M:%SZ`), never estimated.
- **Enforced at the merge gate:** the finishing skill's deviation audit cross-checks
  code, reports, and docs against this log — an unlogged deviation blocks the merge.

---

```markdown
# <Topic> — Decision log

**Design doc:** ./YYYY-MM-DD-<topic>-design.md
Append-only; newest at the bottom. D-numbering shared with the spec's §6.

---

## D<n> — <short title>
**When:** <ISO-8601 UTC> · **Phase:** brainstorm | spec | plan | build ·
**Status:** locked | provisional | superseded-by D<m>
**Decided by:** <who, AND the selection event: which variant they picked and any RIDER
they attached — e.g. "operator (live, in-session; selected C with an explicit
sampler-extensibility requirement)". A rider is the operator amending the offered menu;
it enters the law with the same force as the variant itself.>

- **Trigger:** the question, observation, or drift event that forced this fork — name
  the AMBIGUITY that made it a fork, not just the topic.
- **Options weighed:**
  - A: <option> — gains <…> / sacrifices <…>
  - B: <option> — gains <…> / sacrifices <…>
- **Decided:** <choice + rider> — <the reasoning, including evidence consulted (files
  read, probes run, measurements cited with their honesty tier)>.
- **Not X:** <when the decided thing could be mistaken for a neighbouring concept, say
  what it is NOT and why the difference matters. Omit if no confusion is plausible.>
- **Extension law:** <when the ruling governs its own descendants — what every future
  addition of this kind must contribute. Omit for rulings with no descendant class.>
- **Anti-patterns:** <the specific cheap escapes implementers would reach for, forbidden
  by name — e.g. "sampler fields do not live in dict[str, Any]". Omit if none.>
- **Rests on:** <D#s this builds on · ASSUMPTION A# · evidence | requirement R#> —
  provisional status is mandatory when resting on an unratified assumption.
- **Affects:** R#…, spec §5.x, <files/interfaces/future surfaces once known>.
- **Revisit-when:** <concrete, falsifiable reopening trigger — a condition, never a date>.
```

---

## Worked example (condensed from a real entry — the bar, made concrete)

> ## D461 — MVP allocation search supports feasible grid and seeded feasible generation behind an additive typed seam
> **When:** 2026-08-27T10:03:00+03:00 · **Phase:** optimization brainstorm · **Status:** locked for MVP architecture
> **Decided by:** operator (live, in-session; selected C with an explicit sampler-extensibility requirement)
>
> - **Trigger:** generated allocation search needs both transparent small-space enumeration
>   and broader reproducible exploration, while "seeded allocation sampler" was AMBIGUOUS
>   with outcome-fitted calibration. The operator also requires that later samplers can be
>   added without refactoring studies, candidates, replay, or evidence.
> - **Decided:** a closed discriminated union of `FeasibleAllocationGrid` and
>   `SeededFeasibleAllocationSearch`; the latter is candidate generation only — it reads
>   no trial outcome, score, market data, or calibration target.
> - **Not isotonic calibration:** that fits an outcome-dependent monotonic mapping and
>   belongs to a separately authorized fitting seam — neither a sampler variant nor a
>   candidate generator.
> - **Extension law:** every added sampler contributes one typed immutable configuration,
>   one deterministic generator, one explicit union registration, validation, and
>   generation receipts; downstream trial/replay/persistence code remains unchanged.
> - **Anti-patterns:** no opaque plugin bag — sampler fields do not live in
>   `dict[str, Any]`; no generic `Sampler[CandidateT, StateT, …]` in the public domain.
> - **Rests on:** D382–D385, D397, D403, D425, D449, D451, D459–D460; operator selection C.
> - **Affects:** sampler configuration union; generator registry; study identity;
>   generation receipts; CLI/API schema.
> - **Revisit-when:** another candidate domain proves its public sampler configuration has
>   IDENTICAL semantics, not merely similar iteration mechanics.

Notice what the example does that a minimal entry does not: the trigger names the
ambiguity; the selection records the rider; the "Not X" kills the plausible confusion;
the extension law governs descendants; the anti-patterns forbid the cheap escape by name;
the lineage runs both directions. An entry with all slots honestly empty is fine — an
entry whose slots were never considered is not.
