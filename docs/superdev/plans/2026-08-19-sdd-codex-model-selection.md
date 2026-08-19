# SDD Codex Model Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superdev:subagent-driven-development — the DEFAULT execution route — to implement this plan task-by-task. Use superdev:executing-plans only if the Execution field below says `inline`, or you are deliberately executing in a separate session. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give SDD one two-tier model-routing policy that preserves native Claude Code and maps explicitly selected Codex workers to Sol or Terra, with focused CLI guidance in a separate appendix.

**Architecture:** Keep provider-neutral role routing in the core SDD skill. Resolve the tiers to Claude aliases in that core policy and to exact Codex IDs in a new conditional appendix; keep daemon/session/recovery mechanics canonical in the existing broker reference. Verify the behavior with structural assertions and fresh Claude reading/application scenarios because skill text shapes agent behavior.

**Tech Stack:** Markdown skills/references, Python 3.9 `unittest`, Bash + Claude Code CLI for focused behavior evaluation.

**Execution:** subagent-driven

**Mode:** human-in-loop

**Context pack** — the artifacts downstream workers read:
- Spec: `docs/superdev/specs/2026-08-19-sdd-codex-model-selection-design.md` · Decision log: `docs/superdev/specs/2026-08-19-sdd-codex-model-selection-decisions.md`
- Domain model: none
- CLI surface: no command changes; existing reference `skills/subagent-driven-development/codex-worker.md`
- Prior art: `docs/superdev/specs/2026-08-18-codex-worker-server-design.md`; `skills/writing-skills/SKILL.md`; `skills/writing-skills/testing-skills-with-subagents.md`; `skills/writing-skills/anthropic-best-practices.md`; active model-routing consumers found by the Step 1 `rg` inventory

## Global Constraints

- Expose exactly two operator-facing tiers: `very smart` and `medium`; do not add a third routing tier or model catalog.
- Native Claude: `very smart = opus`, `medium = sonnet`; main-session brainstorming/design remains native Claude `opus`.
- Explicit Codex worker: `very smart = gpt-5.6-sol`, `medium = gpt-5.6-terra`.
- `very smart` is mandatory for architecture/design and design/final gate roles; `medium` is the default for normal implementation and ordinary per-task review, with justified escalation.
- Every dispatched model is explicit. Required model absence or unsupported Codex effort is a reported blocker; never silently substitute or collapse tiers.
- Codex `model list` is authoritative for availability and supported efforts. Effort is independent of tier and must be selected from the chosen model's returned values.
- Claude Code remains coordinator and native dispatch path. Codex workers remain opt-in and do not replace main-session brainstorming/design.
- Do not add static pricing, exhaustive model tables, third-party dependencies, or RPC/CLI behavior changes.

**Test lanes:** fast (the gate): `python3 -W error::ResourceWarning -m unittest discover -s tests/codex-worker -p 'test_*.py'` · slow-by-area (separate killable commands): `bash tests/claude-code/eval-sdd-model-selection.sh control 5 "$CONTROL_JSONL"`, `bash tests/claude-code/eval-sdd-model-selection.sh before 5 "$BEFORE_JSONL"`, and `bash tests/claude-code/eval-sdd-model-selection.sh after 5 "$AFTER_JSONL"` · scheduled sweep: none declared; repository-wide harness sweeps remain separate operator/CI work. The focused structural test runs before every commit; each 15-call Claude variant is a separate killable finishing-gate command.

**Engineering patterns:** none declared/detected — generic review rubric only. This is behavior-shaping documentation; `skills/writing-skills/SKILL.md` is binding for RED/GREEN evaluation.

## The Through-Line

The single task first makes the missing routing contract observable: structural tests
name the exact links, tier mappings, boundaries, failure rules, and every active prompt
that consumes model routing. Three composite application scenarios run five fresh
Claude sessions each against a no-guidance control and the committed pre-change files;
those variants establish RED without losing outputs to early assertion exit. The task
then replaces the central policy, migrates all dependent prompts atomically, adds the
focused Codex appendix, and cross-links the existing broker reference. This is
load-bearing: the core policy owns role routing; the new appendix owns Codex resolution;
all consumers use that vocabulary; the existing broker reference continues to own
mechanics. The same three scenarios then run five fresh sessions each against the
candidate files. Manually scored convergence plus structural GREEN and a tracked
before/after receipt close the task.

**When reality diverges from the task** (an alias is not supported, the Claude evaluator
cannot load the exact worktree skill, or the two-tier policy conflicts with another
binding prompt): re-read this Through-Line, check D3/D4/D5/D6/D7 revisit hooks, append the
fork to the decision log (`phase: build`), and update this task's Interfaces before
continuing. A failure of the two-tier or Claude-preservation anchor goes back to the
human; do not invent a third tier or silently fall back.

## Acceptance (anchored — do not restate here)

This plan discharges UC1, UC2, UC3, UC4, UC5 and AH1, AH2, AH3, AH4, AH5, AH6 from the anchor. The task fills each receipt
with either the warning-strict structural suite, the fresh-session Claude scenario
script, or an exact file/line reference. Any unanswered hint is named and pushed to the
operator because the plan is human-in-loop.

---

### Task 1: Two-tier SDD routing and Codex appendix

**Role in the build:** Make the approved two-tier contract executable in both native
Claude and opt-in Codex paths, and prove the behavior under retrieval/application
pressure (R1, R2, R3, R4, R5, R6, R7; D1, D2, D3, D4, D5, D6, D7).

**Read first:** Spec §§1–5.4, §6 D1–D7, §8, §9; decision log D1–D7;
`skills/subagent-driven-development/SKILL.md` “Codex workers from Claude Code” and
“Model Selection”; `skills/subagent-driven-development/codex-worker.md` “Start and
discover” and “Scope boundary”; `skills/writing-skills/SKILL.md` testing requirements;
`skills/writing-skills/testing-skills-with-subagents.md` pure-reference guidance.

**Files:**
- Create: `skills/subagent-driven-development/codex-model-selection.md`
- Create: `tests/claude-code/eval-sdd-model-selection.sh`
- Create: `docs/superdev/evals/2026-08-19-sdd-model-selection.md`
- Modify: `skills/subagent-driven-development/SKILL.md` Model Selection section
- Modify: `skills/subagent-driven-development/codex-worker.md` Start and discover section
- Modify: `skills/brainstorming/SKILL.md` model declaration
- Modify: `skills/brainstorming/spec-document-reviewer-prompt.md` model placeholder
- Modify: `skills/writing-plans/plan-document-reviewer-prompt.md` model placeholder
- Modify: `skills/requesting-code-review/code-reviewer.md` model placeholder
- Modify: `skills/finishing-a-development-branch/deviation-auditor-prompt.md` model placeholder
- Modify: `skills/cli-checkride/SKILL.md` evaluator model policy
- Modify: `skills/cli-checkride/evaluator-prompt.md` model placeholder
- Modify: `skills/cli-checkride/executor-prompt.md` model placeholder
- Modify: `skills/self-brainstorming/workflow-reference.md` role mappings
- Modify: `skills/using-superdev/references/codex-tools.md` Codex subagent routing
- Modify: `tests/codex-worker/test_skill_integration.py`
- Modify at gate: `docs/superdev/specs/2026-08-19-sdd-codex-model-selection-design.md` §9 receipt cells only

**Interfaces:**
- Consumes: semantic tiers and mappings from spec §5.1–§5.3; existing `codex-worker` CLI commands and live `model list` response.
- Produces: core contract `very smart|medium -> provider-specific explicit model`; all active routing consumers on that vocabulary; `codex-model-selection.md` as the conditional Codex policy/CLI appendix; unchanged `codex-worker.md` as mechanics authority; re-runnable structural and replicated Claude behavior receipts.

- [ ] **Step 1: Add structural assertions that expose the missing contract**

Append these constants and tests to `tests/codex-worker/test_skill_integration.py`:

```python
MODEL_REFERENCE = (
    ROOT / "skills" / "subagent-driven-development" / "codex-model-selection.md"
)
ROUTING_CONSUMERS = (
    ROOT / "skills" / "brainstorming" / "SKILL.md",
    ROOT / "skills" / "brainstorming" / "spec-document-reviewer-prompt.md",
    ROOT / "skills" / "writing-plans" / "plan-document-reviewer-prompt.md",
    ROOT / "skills" / "requesting-code-review" / "code-reviewer.md",
    ROOT / "skills" / "finishing-a-development-branch" / "deviation-auditor-prompt.md",
    ROOT / "skills" / "cli-checkride" / "SKILL.md",
    ROOT / "skills" / "cli-checkride" / "evaluator-prompt.md",
    ROOT / "skills" / "cli-checkride" / "executor-prompt.md",
    ROOT / "skills" / "self-brainstorming" / "workflow-reference.md",
    ROOT / "skills" / "using-superdev" / "references" / "codex-tools.md",
)


class SddModelSelectionTests(unittest.TestCase):
    def test_core_skill_links_two_tier_codex_appendix_and_preserves_claude(self):
        text = SDD.read_text(encoding="utf-8")
        self.assertIn("[Codex model selection](codex-model-selection.md)", text)
        self.assertIn("`very smart`", text)
        self.assertIn("`medium`", text)
        self.assertIn("`opus`", text)
        self.assertIn("`sonnet`", text)
        self.assertIn("main-session brainstorming and design", text.lower())
        section = text.split("## Model Selection", 1)[1].split("\n## ", 1)[0].lower()
        for retired_tier in ("cheap model", "standard model", "most capable model"):
            with self.subTest(retired_tier=retired_tier):
                self.assertNotIn(retired_tier, section)

    def test_codex_appendix_defines_only_sol_and_terra_tier_mappings(self):
        self.assertTrue(MODEL_REFERENCE.is_file())
        text = MODEL_REFERENCE.read_text(encoding="utf-8").lower()
        self.assertIn("`very smart` → `gpt-5.6-sol`", text)
        self.assertIn("`medium` → `gpt-5.6-terra`", text)
        self.assertNotIn("third tier", text.split("## not a model catalog")[0])

    def test_codex_appendix_requires_live_effort_validation_and_no_fallback(self):
        text = MODEL_REFERENCE.read_text(encoding="utf-8").lower()
        for fragment in (
            "model list",
            "supported_efforts",
            "effort is independent",
            "block",
            "never silently substitute",
            "session start",
            "turn start",
            "session resume",
            "codex-worker.md",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_active_routing_consumers_use_two_tier_vocabulary(self):
        retired = (
            "MOST CAPABLE",
            "most capable model",
            "most capable available model",
            "most capable tier",
            "standard model",
            "standard tier",
            "top tier under Codex",
            "gpt-5.6-luna",
            "nearest cheap",
            "cheap, balanced, or frontier",
        )
        for path in ROUTING_CONSUMERS:
            text = path.read_text(encoding="utf-8")
            with self.subTest(path=str(path)):
                for phrase in retired:
                    self.assertNotIn(phrase, text)
                self.assertTrue(
                    "very smart" in text.lower() or "`medium`" in text.lower(),
                    "routing consumer must name a shared SDD tier",
                )
```

- [ ] **Step 2: Add a replicated fresh-session Claude evaluation harness**

Create executable `tests/claude-code/eval-sdd-model-selection.sh` with these exact
contents. Every `claude -p` is a fresh-context sample; failed calls are captured and do
not stop the remaining RED repetitions:

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
VARIANT="${1:?usage: eval-sdd-model-selection.sh control|before|after REPS OUTPUT_JSONL}"
REPS="${2:?repetition count required}"
OUTPUT_JSONL="${3:?output JSONL path required}"
BEFORE_COMMIT=8f9aac8
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
mkdir -p "$(dirname "$OUTPUT_JSONL")"
: > "$OUTPUT_JSONL"

case "$VARIANT" in
  control)
    GUIDANCE="Do not read project files. Use only your general judgment."
    ;;
  before)
    git -C "$REPO_ROOT" show "${BEFORE_COMMIT}:skills/subagent-driven-development/SKILL.md" > "$TMP_ROOT/SKILL.before.md"
    git -C "$REPO_ROOT" show "${BEFORE_COMMIT}:skills/subagent-driven-development/codex-worker.md" > "$TMP_ROOT/codex-worker.before.md"
    GUIDANCE="Read $TMP_ROOT/SKILL.before.md and $TMP_ROOT/codex-worker.before.md. These are the complete pre-change routing references. Do not read current project files."
    ;;
  after)
    GUIDANCE="Read $REPO_ROOT/skills/subagent-driven-development/SKILL.md, $REPO_ROOT/skills/subagent-driven-development/codex-model-selection.md, and $REPO_ROOT/skills/subagent-driven-development/codex-worker.md. Do not use an installed-skill cache."
    ;;
  *)
    echo "unknown variant: $VARIANT" >&2
    exit 2
    ;;
esac

scenario_prompt() {
  case "$1" in
    routine)
      printf '%s' 'A complete plan assigns an ordinary well-specified implementation. Compare native Claude dispatch with an explicitly selected Codex worker. Answer exactly six lines whose keys are Tier, Native model, Codex model, Native daemon required, Codex first validation, and Missing required model.'
      ;;
    gates)
      printf '%s' 'You are doing main-session brainstorming and later dispatching a final whole-branch gate. Compare a native Claude gate with an explicitly selected Codex-worker gate. Answer exactly four lines whose keys are Main-session model, Gate tier, Native gate model, and Codex gate model.'
      ;;
    cli_failure)
      printf '%s' 'Explain Sol versus Terra in one sentence. Then give the ordered Codex-worker command families for discovery, session creation, and turn start, including where model and effort are pinned. The selected model exists but effort turbo is absent from supported_efforts. Also state whether session resume chooses a new model. Answer exactly six lines whose keys are Difference, Command 1, Command 2, Command 3, Unsupported effort outcome, and Resume model behavior.'
      ;;
  esac
}

for scenario in routine gates cli_failure; do
  for rep in $(seq 1 "$REPS"); do
    SAMPLE="$TMP_ROOT/${VARIANT}-${scenario}-${rep}.txt"
    set +e
    claude -p "$GUIDANCE $(scenario_prompt "$scenario") Do not change files." \
      --allowed-tools=Read > "$SAMPLE" 2>&1
    STATUS=$?
    set -e
    python3 - "$VARIANT" "$scenario" "$rep" "$STATUS" "$SAMPLE" <<'PY' >> "$OUTPUT_JSONL"
import json
import pathlib
import sys

variant, scenario, rep, status, sample = sys.argv[1:]
print(json.dumps({
    "variant": variant,
    "scenario": scenario,
    "rep": int(rep),
    "exit_code": int(status),
    "output": pathlib.Path(sample).read_text(encoding="utf-8", errors="replace"),
}, ensure_ascii=False))
PY
  done
done

echo "$OUTPUT_JSONL"
```

Run `chmod +x tests/claude-code/eval-sdd-model-selection.sh` after creating it.

- [ ] **Step 3: Run the structural RED and both replicated baseline variants**

Run separately:

```bash
python3 -W error::ResourceWarning -m unittest \
  discover -s tests/codex-worker -p 'test_skill_integration.py' -v
EVAL_ROOT="$PWD/.superdev/sdd-model-selection-eval/2026-08-19"
mkdir -p "$EVAL_ROOT"
bash tests/claude-code/eval-sdd-model-selection.sh \
  control 5 "$EVAL_ROOT/control.jsonl"
bash tests/claude-code/eval-sdd-model-selection.sh \
  before 5 "$EVAL_ROOT/before.jsonl"
```

Expected: the Python command fails because `codex-model-selection.md` and the new core
link/mappings do not exist. Both JSONL files contain 15 records (three scenarios × five
fresh sessions), including nonzero Claude exits rather than stopping early. Manually
read and score every record against the scenario contracts. The no-guidance control
must exhibit at least one repeated routing/CLI failure or there is no measured behavior
problem to fix; stop and report that result instead of authoring guidance. Record exact
outputs, exit codes, per-contract pass counts, and recurring rationalizations under
`RED — control` and `RED — before` in the evaluation report.

- [ ] **Step 4: Replace the core Model Selection section with the approved two-tier policy**

Edit `skills/subagent-driven-development/SKILL.md` so the section contains these
contracts in the project's established direct voice:

```markdown
## Model Selection

SDD has exactly two operator-facing tiers. Every dispatched subagent pins a model
explicitly; never rely on inherited session defaults.

| Tier | Use for | Native Claude Code |
|---|---|---|
| `medium` | Normal implementation, routine integration/debugging, and ordinary per-task review | `sonnet` |
| `very smart` | Architecture, unusually ambiguous/high-risk work, and every design or final gate | `opus` |

`medium` is the default for planned task work. Escalate an implementation or per-task
review to `very smart` when ambiguity, cross-cutting risk, or failed attempts show that
more judgment is needed. Do not scale design/gate work down: spec and plan reviewers,
final whole-branch review, and finishing deviation/acceptance audit always use `very
smart`.

Main-session brainstorming and design remain native Claude Code work on `opus`; they
are not delegated to a Codex worker. If native Claude lacks the required `sonnet` or
`opus` alias, stop and report the blocker—never silently collapse to the other tier.

When the operator or plan explicitly selects a Codex worker, resolve the same tiers
through [Codex model selection](codex-model-selection.md), then follow [Codex worker
broker](codex-worker.md) for lifecycle and task handoff. Codex is opt-in; native Claude
dispatch does not require its daemon.
```

Preserve the existing principle that task escalation follows actual complexity and
status feedback; remove the old cheap/standard/most-capable three-class routing and its
contradictory cheapest-tier advice.

- [ ] **Step 5: Migrate every active model-routing consumer**

Replace retired provider-relative wording in the ten active consumers named in
`ROUTING_CONSUMERS`. Use these exact contracts:

- `skills/brainstorming/SKILL.md`: main-session design is the `very smart` tier and
  runs on native Claude `opus`; it is never a Codex-worker dispatch. The spec reviewer
  uses `very smart` through its prompt template.
- `skills/self-brainstorming/workflow-reference.md`: Questioner and synthesis are
  native Claude `opus` (`very smart`); Responder is native Claude `sonnet` (`medium`);
  the spec-review gate uses `very smart` through its template. Remove “standard,”
  “most-capable,” and “top tier under Codex” routing language.
- `skills/cli-checkride/SKILL.md`: evaluator is `very smart`; executor is `medium`.
  State that native Claude resolves those tiers to `opus`/`sonnet`, while an explicitly
  selected Codex worker resolves through `../subagent-driven-development/codex-model-selection.md`.
- `skills/cli-checkride/executor-prompt.md`: replace `standard tier` with the `MEDIUM`
  tier and state `Native Claude Code: sonnet`; an explicitly selected Codex executor is
  `gpt-5.6-terra` after live validation.
- `skills/using-superdev/references/codex-tools.md`: retain explicit `model` and
  `reasoning_effort`, `fork_turns: "none"`, and the no-deterministic-command-dispatch
  boundary. Change inherited-cost language to “silently spend the `very smart` tier on
  `medium` work.” Replace the Luna/five-row/nearest-tier table with exactly two rows:

```markdown
| SDD tier | Work | Codex model |
|---|---|---|
| `medium` | Normal implementation, routine integration/debugging, ordinary task review, and diligent execution | `gpt-5.6-terra` |
| `very smart` | Architecture, difficult/high-risk work, escalation, and every design/final gate | `gpt-5.6-sol` |
```

  Require an explicit supported effort for the selected model. If the required model
  or effort is unavailable, block and report; remove Luna and nearest-tier fallback.
- Each reviewer/evaluator prompt below uses this model placeholder, adjusted only for
  the role noun already present in that file:

```markdown
model: [VERY SMART tier — REQUIRED for this high-judgment gate; never scale down.
        Native Claude Code: opus. Explicit Codex worker: gpt-5.6-sol after live
        model/effort validation per subagent-driven-development/codex-model-selection.md.]
```

Apply that placeholder to:

- `skills/brainstorming/spec-document-reviewer-prompt.md`
- `skills/writing-plans/plan-document-reviewer-prompt.md`
- `skills/requesting-code-review/code-reviewer.md`
- `skills/finishing-a-development-branch/deviation-auditor-prompt.md`
- `skills/cli-checkride/evaluator-prompt.md`

Preserve every non-model instruction verbatim. Do not add Codex to main-session design
or change any role's gate floor.

- [ ] **Step 6: Add the focused Codex model/CLI appendix**

Create `skills/subagent-driven-development/codex-model-selection.md` with these
exact contents:

```markdown
# Codex model selection

Read this reference only when the operator or plan explicitly selects a Codex worker.
Claude Code remains coordinator; native Claude model routing stays in `SKILL.md`.

## The two mappings

| SDD tier | Codex model | Operational meaning |
|---|---|---|
| `very smart` | `gpt-5.6-sol` | Frontier choice for architecture, difficult reasoning/coding, escalation, and dispatched design/final gates. |
| `medium` | `gpt-5.6-terra` | Balanced default for normal implementation, routine integration/debugging, and ordinary per-task review. |

Sol is the higher-judgment tier; Terra is the everyday engineering tier. These are the
only normal SDD recommendations for now. OpenAI describes Sol as its flagship for
complex professional work and describes Terra as balancing intelligence and cost
([model catalog](https://developers.openai.com/api/docs/models),
[Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol), checked
2026-08-19). Runtime selection still follows the daemon's live response.

## Discover before dispatch

Run:

```sh
codex-worker --socket "$SOCKET" model list
```

Confirm the exact selected ID exists and read that model's returned
`supported_efforts`. Effort is independent of the SDD tier: choose only a
live-supported value. If the pinned model or desired effort is absent, block and
report it; never silently substitute another model or effort.

## Pin the model and effort

For a normal `medium` task:

```sh
codex-worker --socket "$SOCKET" session start \
  --cwd "$WORKTREE" --name "$ROLE" --model gpt-5.6-terra
codex-worker --socket "$SOCKET" turn start \
  --session "$SESSION_UUID" --prompt-file "$TASK_BRIEF" \
  --model gpt-5.6-terra --effort "$EFFORT"
```

For a dispatched `very smart` task or gate:

```sh
codex-worker --socket "$SOCKET" session start \
  --cwd "$WORKTREE" --name "$ROLE" --model gpt-5.6-sol
codex-worker --socket "$SOCKET" turn start \
  --session "$SESSION_UUID" --prompt-file "$TASK_BRIEF" \
  --model gpt-5.6-sol --effort "$EFFORT"
```

`$EFFORT` means one value returned for that exact model in `supported_efforts`, not a
remembered default. A session retains its latest model annotation; an explicit model
on a later turn may update it. Resume reattaches the same identity and immutable cwd:

```sh
codex-worker --socket "$SOCKET" session resume --session "$SESSION_UUID"
```

Resume is not a model-selection command. After attachment, pin the selected model and
live-supported effort on the next `turn start` when the role requires an explicit
choice.

Follow [Codex worker broker](codex-worker.md) for daemon lifecycle, session identity,
worktrees, task handoff, status/events/wait, steer/interrupt, and recovery. That file is
the mechanics authority; this appendix owns only model and effort choice.

## Not a model catalog

Do not recommend a third tier, enumerate older models, or publish static pricing and
capability matrices. Revisit the two mappings only when a pinned ID is unavailable or
measured SDD evaluations justify a change.
```

- [ ] **Step 7: Cross-link the policy from broker mechanics**

In `skills/subagent-driven-development/codex-worker.md` under “Start and discover,” add
one concise sentence after the live-discovery rule:

```markdown
Resolve SDD's two tiers through [Codex model selection](codex-model-selection.md);
that appendix owns model meaning and effort selection, while this reference owns
worker lifecycle and recovery mechanics.
```

Do not duplicate the mapping table or change any CLI command.

- [ ] **Step 8: Run structural GREEN and the replicated candidate variant**

Run separately:

```bash
python3 -W error::ResourceWarning -m unittest \
  discover -s tests/codex-worker -p 'test_skill_integration.py' -v
EVAL_ROOT="$PWD/.superdev/sdd-model-selection-eval/2026-08-19"
mkdir -p "$EVAL_ROOT"
bash tests/claude-code/eval-sdd-model-selection.sh \
  after 5 "$EVAL_ROOT/after.jsonl"
```

Expected: the structural command exits 0 and the candidate JSONL contains 15 records.
Manually read every record and score the same contracts used for control/before. All
five candidate repetitions per scenario must converge on the correct tier/provider,
Sol-versus-Terra distinction, ordered discovery/session/turn sequence, and explicit
block for missing models or unsupported effort. If not, make the smallest wording
correction consistent with D1–D7 and rerun the entire `after` variant into a new file;
do not overwrite failed evidence or relax a wrong-routing criterion.

- [ ] **Step 9: Write the tracked before/after evaluation receipt**

Complete `docs/superdev/evals/2026-08-19-sdd-model-selection.md` with the title
“SDD model-selection skill evaluation,” the measured date, evaluated commit/worktree
HEAD, Claude version, and method. Add separate `RED — control`, `RED — before`, and
`GREEN — after` tables with one row for each named scenario: routine, gates, and
CLI/failure. Each row records five independently read results, exit codes, per-contract
pass counts, variance, and bounded verbatim examples. Include a rationalization table
for repeated baseline failures. The CLI/failure score covers the Sol/Terra explanation,
ordered `model list` → `session start` → `turn start` sequence, explicit model/effort
pinning, unsupported-effort blocker, and resume semantics. Finish with the exact
commands, JSONL paths/hashes, record counts, and measured UTC timestamps. Do not use
ellipses, placeholders, or invented results.

- [ ] **Step 10: Run the commit gate and fill anchor receipts**

Run:

```bash
python3 -W error::ResourceWarning -m unittest discover \
  -s tests/codex-worker -p 'test_*.py'
git diff --check
```

Expected: warning-strict Codex-worker test suite exits 0 with the current intentional
privilege-dependent skip only; `git diff --check` exits 0. Fill AH1–AH6 receipt cells in
the approved design with the focused test names, Claude evaluation report, and exact
skill/appendix lines. Do not edit hint text.

- [ ] **Step 11: Commit the task**

```bash
git add \
  skills/subagent-driven-development/SKILL.md \
  skills/subagent-driven-development/codex-worker.md \
  skills/subagent-driven-development/codex-model-selection.md \
  skills/brainstorming/SKILL.md \
  skills/brainstorming/spec-document-reviewer-prompt.md \
  skills/writing-plans/plan-document-reviewer-prompt.md \
  skills/requesting-code-review/code-reviewer.md \
  skills/finishing-a-development-branch/deviation-auditor-prompt.md \
  skills/cli-checkride/SKILL.md \
  skills/cli-checkride/evaluator-prompt.md \
  skills/cli-checkride/executor-prompt.md \
  skills/self-brainstorming/workflow-reference.md \
  skills/using-superdev/references/codex-tools.md \
  tests/codex-worker/test_skill_integration.py \
  tests/claude-code/eval-sdd-model-selection.sh \
  docs/superdev/evals/2026-08-19-sdd-model-selection.md \
  docs/superdev/specs/2026-08-19-sdd-codex-model-selection-design.md
git commit -m "docs(sdd): define two-tier Claude and Codex routing"
```
