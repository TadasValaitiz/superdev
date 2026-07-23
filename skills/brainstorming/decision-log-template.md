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
**Decided by:** <human / agent role / self-brainstorm round N>

- **Trigger:** the question, observation, or drift event that forced this fork.
- **Options weighed:**
  - A: <option> — gains <…> / sacrifices <…>
  - B: <option> — gains <…> / sacrifices <…>
- **Decided:** <choice> — <the reasoning, including evidence consulted (files read,
  probes run, measurements cited with their honesty tier)>.
- **Rests on:** <ASSUMPTION A# | evidence | stated requirement R#> — provisional status
  is mandatory when resting on an unratified assumption.
- **Affects:** R#…, spec §5.x, <files/interfaces once known>.
- **Revisit-when:** <concrete reopening trigger>.
```
