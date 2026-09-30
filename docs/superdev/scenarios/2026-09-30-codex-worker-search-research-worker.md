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
