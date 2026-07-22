# CLI Surface Document Template

REQUIRED as a SEPARATE companion file — `YYYY-MM-DD-<topic>-cli-surface.md`, next to
the design doc — whenever the work adds, renames, reworks, or removes CLI commands.
The design doc says what the system is; this document says **how the operator drives
it**: every command with full arguments, grouped into families, with the composition
reasoning and the operational sequences. It is written for two readers at once — the
implementer (contract) and the operator (manual) — and it feeds downstream prompts via
the plan's Context pack.

```markdown
# <Topic> — CLI Surface (status: draft | ratified <who, when>)

**Design doc:** ./YYYY-MM-DD-<topic>-design.md · **Decision log:** ./…-decisions.md

## 1. `<tool> <family>` — <family purpose>

One section per FAMILY (group commands by the noun they operate on, not by when
they were built). Per family, the command table:

| Command | Purpose | Args (all of them) | Command model | Gate | Status |
|---|---|---|---|---|---|
| `<family> <verb> <args…>` | one line | `--flag <type> [default]` — every arg, no "etc." | `<Verb><Noun>Command` (Pydantic) | READ / FILTER / RECORD | NEW / EXISTS-KEEP / EXISTS-REWORK / RENAMED (old kept as alias?) / DEPRECATED |

- **Args are exhaustive** — the table is the contract the implementer builds and
  the reviewer diffs. Every command's args ARE its Pydantic Command model
  ((Request) -> Response under the hood); the model appears in the design doc's
  domain section, so arg discrepancies across commands show up as model diffs.
- **Gate** states what the command may do: READ (no state), FILTER (validates,
  refuses), RECORD (writes state). A command that both decides and writes is two
  commands waiting to be split — justify it or split it.

### 1b. Composition rationale

Why THIS command shape and not another — the fork log for the family:
- Where we chose TWO commands over one (an operator decision belongs between
  the steps — human-in-the-loop is a feature, not friction).
- Where we chose ONE command over two (no decision lives between them; a forced
  stop would be ceremony).
- Where a PIPE is the composition (`<cmd-a> | <cmd-b>`): what flows across, and
  why a pipe beats a flag.
Each fork cites its D# in the decision log.

## §. Operator workflows — sequences, not just commands

The narrative the command tables can't carry: for each real operating scenario,
the SEQUENCE — what runs first, what you look at, what decision you make, what
runs next:

    <scenario name>
    1. `<cmd>` → read <what> from the output
    2. decide: <the human fork — what you're judging>
    3. `<cmd>` → …
    Recovery: on <error/refusal>, run `<cmd>` to clear/diagnose, then resume at step <n>.

Include the error paths deliberately: which errors clear themselves, which need a
clearing command, which mean stop-and-escalate. The docs are the operator's hints —
a command whose failure mode is only discoverable by reading source is unfinished.

## §. Docs to update (same branch, not later)

| Doc | What changes |
|---|---|
| <reference page / family page> | new/changed command rows |
| <help text / --help output> | flags + one-line purposes |
| <operator runbook if sequences changed> | the workflow above, transplanted |

## §. Delta summary

One paragraph: the whole surface change in prose — new commands, renames (and
their aliases), reworks, deprecations. The reviewer reads this first and checks
the tables against it.
```

**Downstream use:** the plan's Context pack lists this file; every task that builds a
command names its family section in Read-first; the task reviewer diffs delivered
args against the table; the finishing gate's docs check uses §Docs-to-update as its
checklist.
