---
name: finishing-a-development-branch
description: Use when implementation is complete, all tests pass, and you need to decide how to integrate the work - guides completion of development work by presenting structured options for merge, PR, or cleanup
---

# Finishing a Development Branch

## Overview

Guide completion of development work by presenting clear options and handling chosen workflow.

**Core principle:** Verify tests → Deviation audit → Detect environment → Present options → Execute choice → Clean up.

**Announce at start:** "I'm using the finishing-a-development-branch skill to complete this work."

## The Process

### Step 1: Verify Tests — fast suite + area-selected slow (never the monolith)

Per test-driven-development/testing-lanes.md, this gate runs the FAST suite as one
command, then the slow tests that cover what this branch touched — **each as its own
killable command, never the whole slow tier in one invocation** (a monolithic run gets
stuck → you kill it → you rerun from zero, and it serializes badly against other agents).

```bash
# 1. Fast suite — one command (from the project's CLAUDE.md "Test lanes" / plan Global Constraints)
<fast command, e.g. pytest tests -m "not slow" -n auto>

# 2. Slow-by-area — SEPARATE commands, one per dir/module/marker covering the branch's changes.
#    Pick by matching test paths/markers to the files you changed; include slow tests you
#    authored for this change. When unsure, include it — the scheduled sweep backstops misses.
<slow command for area A>
<slow command for area B>
```

If a slow unit hangs, kill THAT command and rerun it alone — the fast run and the other
slow areas already passed. Whole-suite truth is re-established by the scheduled sweep
(a separate task on main), not here.

**If any of these fail:**
```
Tests failing (<N> failures in <which command>). Must fix before completing:

[Show failures]

Cannot proceed with merge/PR until the fast suite and the area's slow tests are green.
```

Stop. Don't proceed to Step 2.

**If they pass:** Continue to Step 2. (Note which slow areas you ran, and any you
deliberately deferred to the sweep, in the finishing report — an unrun area is a named
gap, not a silent one.)

### Step 2: Deviation & Acceptance Audit — prove the done bar before the merge decision

Dispatch the deviation-auditor subagent per
[deviation-auditor-prompt.md](deviation-auditor-prompt.md), passing the plan's **Mode**
(autonomous | human-in-loop). It does two things: (B) proves each discharged anchor Use
Case / acceptance hint (UC#/AH#) with a RECEIPT — a live-arc transcript on the real
surface, a test+output, or a file:line — and names any it can't; (A) cross-checks the
original docs (anchor, domain delta ledger, CLI surface), the code, the decision log,
the reports, and any other Context-pack artifact. It returns an acceptance table + a
divergence table.

- **UNMET acceptance hint:** routed by Mode — autonomous files the drafted owned
  backlog item (referencing the UC#/AH#) and the branch may close with the gap named;
  human-in-loop surfaces the pushback package to the operator BEFORE options. Either
  way the unmet hint is named in the options message, never silently merged as done.

- **BLOCKERS (unlogged deviations):** treat exactly like failing tests — stop. Log
  the deviation (D#, phase: build, amend the governing spec sections) or revert it.
  Re-run the audit once. Cannot proceed to options with an unlogged deviation.
- **doc-stale rows:** amend the named doc sections on the branch NOW — the merge
  carries the docs; merging stale docs manufactures the next false diagnosis.
- **CLEAN or logged-clean:** proceed — and include the audit table in the Step 5
  options message, so the human chooses with the drift in view, not just the green.

No spec/plan exists (ad-hoc branch)? Skip, and say "no deviation audit — no
spec/plan on this branch" in the options message. Never fabricate an audit.


### Step 3: Detect Environment

**Determine workspace state before presenting options:**

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
```

This determines which menu to show and how cleanup works:

| State | Menu | Cleanup |
|-------|------|---------|
| `GIT_DIR == GIT_COMMON` (normal repo) | Standard 4 options | No worktree to clean up |
| `GIT_DIR != GIT_COMMON`, named branch | Standard 4 options | Provenance-based (see Step 7) |
| `GIT_DIR != GIT_COMMON`, detached HEAD | Reduced 3 options (no merge) | No cleanup (externally managed) |

### Step 4: Determine Base Branch

```bash
# Try common base branches
git merge-base HEAD main 2>/dev/null || git merge-base HEAD master 2>/dev/null
```

Or ask: "This branch split from main - is that correct?"

### Step 5: Present Options

**Normal repo and named-branch worktree — present exactly these 4 options:**

```
Implementation complete. What would you like to do?

1. Merge back to <base-branch> locally
2. Push and create a Pull Request
3. Keep the branch as-is (I'll handle it later)
4. Discard this work

Which option?
```

**Detached HEAD — present exactly these 3 options:**

```
Implementation complete. You're on a detached HEAD (externally managed workspace).

1. Push as new branch and create a Pull Request
2. Keep as-is (I'll handle it later)
3. Discard this work

Which option?
```

**Don't add explanation** - keep options concise.

### Step 6: Execute Choice

#### Option 1: Merge Locally

```bash
# Get main repo root for CWD safety
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
cd "$MAIN_ROOT"

# Merge first — verify success before removing anything
git checkout <base-branch>
git pull
git merge <feature-branch>

# Verify tests on merged result
<test command>

# Only after merge succeeds: cleanup worktree (Step 7), then delete branch
```

Then: Cleanup worktree (Step 7), then delete branch:

```bash
git branch -d <feature-branch>
```

#### Option 2: Push and Create PR

```bash
# Push branch
git push -u origin <feature-branch>
```

**Do NOT clean up worktree** — user needs it alive to iterate on PR feedback.

#### Option 3: Keep As-Is

Report: "Keeping branch <name>. Worktree preserved at <path>."

**Don't cleanup worktree.**

#### Option 4: Discard

**Confirm first:**
```
This will permanently delete:
- Branch <name>
- All commits: <commit-list>
- Worktree at <path>

Type 'discard' to confirm.
```

Wait for exact confirmation.

If confirmed:
```bash
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
cd "$MAIN_ROOT"
```

Then: Cleanup worktree (Step 7), then force-delete branch:
```bash
git branch -D <feature-branch>
```

### Step 7: Cleanup Workspace

**Only runs for Options 1 and 4.** Options 2 and 3 always preserve the worktree.

```bash
GIT_DIR=$(cd "$(git rev-parse --git-dir)" 2>/dev/null && pwd -P)
GIT_COMMON=$(cd "$(git rev-parse --git-common-dir)" 2>/dev/null && pwd -P)
WORKTREE_PATH=$(git rev-parse --show-toplevel)
```

**If `GIT_DIR == GIT_COMMON`:** Normal repo, no worktree to clean up. Done.

**If worktree path is under `.worktrees/`, `worktrees/`, or `.claude/worktrees/`:** Superdev created this worktree — we own cleanup. **Exception — enterable rooms:** a room retires its OWN worktree at its close gate (worktree merged AND removed before the room reports closed; the orchestrator verifies via `git worktree list`). This skill's cleanup step never removes a room's worktree from outside — the room is the creator, and the creator retires.

```bash
MAIN_ROOT=$(git -C "$(git rev-parse --git-common-dir)/.." rev-parse --show-toplevel)
cd "$MAIN_ROOT"
git worktree remove "$WORKTREE_PATH"
git worktree prune  # Self-healing: clean up any stale registrations
```

**Otherwise:** The host environment (harness) owns this workspace. Do NOT remove it. If your platform provides a workspace-exit tool, use it. Otherwise, leave the workspace in place.

## Quick Reference

| Option | Merge | Push | Keep Worktree | Cleanup Branch |
|--------|-------|------|---------------|----------------|
| 1. Merge locally | yes | - | - | yes |
| 2. Create PR | - | yes | yes | - |
| 3. Keep as-is | - | - | yes | - |
| 4. Discard | - | - | - | yes (force) |

## Common Mistakes

**Skipping test verification**
- **Problem:** Merge broken code, create failing PR
- **Fix:** Always verify tests before offering options

**Open-ended questions**
- **Problem:** "What should I do next?" is ambiguous
- **Fix:** Present exactly 4 structured options (or 3 for detached HEAD)

**Cleaning up worktree for Option 2**
- **Problem:** Remove worktree user needs for PR iteration
- **Fix:** Only cleanup for Options 1 and 4

**Deleting branch before removing worktree**
- **Problem:** `git branch -d` fails because worktree still references the branch
- **Fix:** Merge first, remove worktree, then delete branch

**Running git worktree remove from inside the worktree**
- **Problem:** Command fails silently when CWD is inside the worktree being removed
- **Fix:** Always `cd` to main repo root before `git worktree remove`

**Cleaning up harness-owned worktrees**
- **Problem:** Removing a worktree the harness created causes phantom state
- **Fix:** Only clean up worktrees under `.worktrees/` or `worktrees/`

**No confirmation for discard**
- **Problem:** Accidentally delete work
- **Fix:** Require typed "discard" confirmation

## Red Flags

**Never:**
- Proceed with failing tests
- Present merge options with an UNLOGGED deviation (audit blocker = failing test)
- Merge without verifying tests on result
- Delete work without confirmation
- Force-push without explicit request
- Remove a worktree before confirming merge success
- Clean up worktrees you didn't create (provenance check)
- Run `git worktree remove` from inside the worktree

**Always:**
- Verify tests before offering options
- Run the deviation audit after tests, before options — and show its table with the options
- Detect environment before presenting menu
- Present exactly 4 options (or 3 for detached HEAD)
- Get typed confirmation for Option 4
- Clean up worktree for Options 1 & 4 only
- `cd` to main repo root before worktree removal
- Run `git worktree prune` after removal
