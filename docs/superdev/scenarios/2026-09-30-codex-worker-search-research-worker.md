# Scenario: one reusable research worker with live web search

**Date:** 2026-09-30 · **Item:** superdev-codex-search · **Plan:** `docs/superdev/checkrides/2026-09-30-codex-worker-search-checkride-plan.md`

## Operator goal (in the operator's words)

"I research questions that need the live web. I want to start one Codex worker with web search on, ask it
a question, then keep asking follow-ups on the same worker, instead of paying to reload everything with a
one-shot `codex exec` every time. I also need to know the machine-wide service can be stopped and
restarted safely without leaving junk behind or killing other rooms' work."

## Starting point

A Claude room with codex-cli 0.158.0 logged in and codex-worker installed by the trusted preflight. The
global service is stopped. There is an empty scratch directory and a research question.

## The journey (intent level, never commands)

1. Check the installed tool is the version I expect.
2. Create a named research worker in the scratch directory, with live web search, and ask the question.
3. Ask a follow-up on the same worker.
4. Look at the worker's status and what it has said.
5. In a throwaway, isolated service: stop the service under a worker, restart it, and keep talking to the
   same worker.
6. Only with the human's go-ahead: do the same stop/restart on the machine-wide service.

## What good looks like

- The service comes up by itself when I create the worker. I don't have to fix sockets or know about codex internals.
- The result tells me plainly that this worker has live web search, and that the setting is fixed for its life.
- Answers cite the pages they used, and I can see that a search actually happened.
- The follow-up lands on the same conversation; I can confirm that from the ids in the result.
- If token usage isn't shown, the output says so honestly rather than showing nothing or guessing.
- Stopping the service tells me what it affects before or as it acts. Afterwards nothing is left running
  or dangling. Restarting brings it back, and my worker continues where it was, still with web search.
- Every refusal tells me exactly what to run next.

## Actual data the journey needs

Real Codex (ChatGPT login), the live web, and the real global service and registry (steps 1–4, 6). Step 5
uses a disposable isolated service home with the same real Codex and web.

## Refresh 2026-10-06 (criteria born from the ride's findings)

**Starting point, corrected.** The scratch directory for a worker the operator means to keep lives under the
project or home, never under `/tmp` or `/private/tmp`. macOS deletes idle `/tmp` entries, and a worker whose
directory vanished must not take the service down with it (F19). Throwaway isolated services may still use `/tmp`.

**What good looks like, added:**
- A worker whose directory vanished is shown as unusable, with one runnable way to let it go. Every other
  worker keeps working (F19, F18, F23).
- After a service restart, re-attaching the worker without starting a turn makes `status` and `messages` show
  its real last turn and answer. An empty or partial read never presents itself as the whole conversation (F22).
- The result of `daemon stop`/`restart` says what happens to the workers on it, and the next command for a
  detached worker re-attaches it without forcing a new turn (F15, F16).
- A read on a stopped service doesn't silently start it again (F25).
- Token usage is either Codex's own count for this turn or labelled unavailable (F6).
- A stopped service doesn't show stored or default values as if they were live (F2).
- Every `run` refusal says why it refused and what to run next (F9).
- The trusted install works on a home that has never had a uv tool (F20).
- Asking a follow-up on the same worker is about continuity, not cheaper turns. The worker re-reads its
  context, and input tokens rise per turn.

**Added after the 8.6.7 verdict (evaluator):**
- A stop lasts. Either reads don't start a stopped service, or every machine-wide window accounts for other
  rooms' reads (F25).
- Installing a new build and changing the machine-wide service generation are one supervised window: a
  quiet-window check, the install, an immediate supervised restart, then post-reads.
- A worker is never lost in its creation window; a deterministic test proves the stop gate covers it (F21).
- Teardown is judged by process and socket identity, including processes outside the owned group. The
  active-work gates are re-ridden whenever the Codex version changes.
- `retire` works on every path: attached and idle, detached and idle, cwd missing, and refused during an
  active turn.
- An isolated test home mirrors the operator's real home. A first install on a fresh home is its own journey (F20).
