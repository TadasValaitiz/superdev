# Pipelines companion template — how state moves

REQUIRED as a SEPARATE companion file — `YYYY-MM-DD-<topic>-pipelines.md`, next to the
design doc — whenever the work adds or changes BEHAVIOR: a use case that moves domain
objects through time (a command that writes, a replay, a search, a lifecycle, a judgment).
The domain-model companion says WHAT exists and which invariants make it authoritative;
this document says HOW the operator's use cases move those objects through time — verbs,
ordering, capabilities, short-circuiting, atomicity, recovery. It sits deliberately between
domain design and implementation planning: the plan maps every step here to a file, a task,
and a test; the checkride plan drives its pipelines; the task reviewer checks each step's
transition and refusal against it.

Written in Pass 2 of the design (SKILL.md step 8b) from the use cases (§3) and the rulings,
and updated after every later ruling that changes a flow. Each pipeline carries a `P#` and
each step a `P#.n`, so plan tasks, reviewers, and the checkride plan can cite them.

**What a pipeline is here.** One use case's path from a typed Request to a typed Response
or a typed refusal, through NAMED steps that each consume one frozen typed input and return
one frozen typed output or one closed typed refusal. Pure kernels and injected effects are
labelled per step. An implementation may merge adjacent pure steps or split a large one,
but every authority transition shown must remain individually testable.

```markdown
# <Topic> — Pipelines (status: draft | ratified <who, when>)

**Design doc:** ./YYYY-MM-DD-<topic>-design.md · **Domain model:** ./…-domain-model.md ·
**Decision log:** ./…-decisions.md · **CLI surface:** ./…-cli-surface.md (if any)
**Governed by:** D#… (the rulings whose behavior this document renders)

## 1. Cross-pipeline laws

Numbered laws that bind EVERY pipeline below, each citing its D#. Typical members: thin
adapters (a CLI leaf parses one Request, invokes one use case, renders one Response or
refusal); capabilities prevent leakage (a step receives only the handles it may use);
who owns the economics / the evidence and who may never recreate it; attempts versus
outcomes; no hidden lifecycle (progress derives from frozen facts, never from a mutable
running/complete flag); exact reinvocation is recovery (no automatic retry); every number
reconstructable from stored authority.

1. **<law>** — <one or two sentences> (D#)

## 2. Behavioral topology

One text diagram of how the pipelines connect — which feeds which, which loop, which
read only over stored authority:

    P1 <verb phrase> (read-only)
      |
    P2 <verb phrase> ──> P3 <verb phrase> (reused per leg) ──> back to P2
    independently over stored authority: P4 reads · P5 judgments

## 3. P<n> — <use case verb phrase>          (one section per pipeline)

**Entry:** `<tool> <command …>` or the internal caller · **Serves:** UC# ·
**Contract:** `<Verb>Request -> <Noun>Response | typed refusal` ·
**Authority:** READ (writes nothing) | RECORD (what it may write, and only that)

| Step | Typed transition | Nature | Refusal boundary | Durable effect |
|---|---|---|---|---|
| P<n>.1 <name> | `<InputType> -> <OutputType>` | pure / injected read / injected append / canonical kernel | <what refuses here, as a typed code> | none / <exactly what is written> |
| P<n>.2 … | … | … | … | … |

**Transaction boundary:** what commits together — or nothing (name the write set).
**State after success:** what is now true that was not before: which objects exist,
which facts were appended, which invariants (I#, domain-model §7) now hold over them.
**Recovery:** for each failure class (usage · typed refusal · interruption · systemic
fault) — what is durable, what is not, and the exact reinvocation that resumes; what is
never retried automatically and why.
**Cannot do:** the capability fences — what this pipeline never reads, never writes,
never decides (the negative space the plan and the reviewer hold it to).

## 4. State evolution — the lifecycle table

| Object (domain-model §3) | Created by | Appended/mutated by | Terminal when | Read by |
|---|---|---|---|---|
| <Object> | P<n>.<step> | P<m>.<step> (append-only facts) | <derived condition, never a flag> | P<k> |

State is DERIVED from frozen facts; a row whose "terminal when" is a mutable status
field is a design smell — name the facts that imply it instead.

## 5. Refusal catalogue

| Code | Raised at (P#.n) | Exit class | Remedy the operator is told |
|---|---|---|---|
| `<TYPED_CODE>` | P<n>.<step> | 2 usage / 3 operational | `<runnable command>` |

Every refusal that a use case can meet appears here once; an exit 1 (internal error) is
never a planned row. This table is what the checkride's refusal-path steps are judged
against.

## 6. Flexible and deferred

**FLEXIBLE:** what may still move (step merging/splitting, internal representation) within
what bounds. **DEFERRED, with landing places:** each deferral names the session/item that
owns it — bare "later" is a finding.
```

**Downstream use:** the plan's Context pack lists this file; every task that implements a
step carries `Pipeline steps: P#.n → typed in/out → refusal test` (writing-plans task
structure); the implementer's Read-first quotes those rows; the task reviewer checks the
transition, the refusal type, and the transaction boundary against this document; the
checkride plan's journeys name the P#s they drive and the refusal catalogue rows they
exercise; the finishing gate's acceptance receipt for a UC cites the P# it ran through.
