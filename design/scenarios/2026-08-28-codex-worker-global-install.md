# Scenario intent — globally installed Codex worker

**Date:** 2026-08-28
**Surface:** Superdev Codex worker installation, compatibility preflight, and plain PATH
operation

## Operator goal

Select a Codex worker from any repository and have the loaded Superdev skill establish
one trustworthy, version-compatible global command without source-launcher fallbacks or
manual package archaeology. Existing named work must survive tool replacement, and an
operator must be able to tell what happened and how to recover from a refusal.

## Journey intent

The operator begins in a shell where the worker may be absent, stale, newer than the
loaded plugin, already compatible, shadowed, or temporarily un-installable. The loaded
skill resolves its trusted bundled source and performs its one preflight. After that
gate, normal operation uses only the short PATH command, including from an unrelated
repository. A read-only, callback-disabled status worker reports the repository's Git
state without modifying it. Replacing the installed tool preserves durable mappings;
the operator deliberately resumes a detached name before inspecting it. Stopping the
runtime never deletes the mapping.

## What good looks like

- The selected PATH command is visibly owned by UV and exactly matches the loaded plugin
  version; source checkout and editable-install provenance are absent.
- Absence installs, mismatches repair in either direction, and an exact match performs no
  reinstall. The success output distinguishes those three outcomes.
- A shadow, missing UV, failed install, root/version mismatch, or missing external Codex
  stops safely with an actionable recovery and preserves prior bytes/state.
- A copied non-editable package still imports and runs under Python 3.9 after its source
  directory is moved away.
- Simulated lower/higher executable fixtures are labelled separately from measured real
  UV installation and command behavior.
- The unrelated-repository journey uses literal short PATH commands, creates exactly one
  intended read-only/no-callback name, reports independently verified Git state, and
  leaves that repository unchanged.
- Tool reinstall leaves durable mapping bytes and session/thread identity unchanged;
  resume/reattach precedes status, and runtime-only stop preserves the mapping.
- If a completion is incomplete after a named mapping exists, the refusal retains every
  known identity and supplies runnable status/history recovery instead of an empty route.
