# SDD model-selection semantic checkpoint

**Date:** 2026-08-19
**Reviewed HEAD:** `380fa7822c961a564802d8307937fbb664a12b20`
**Independent reviewer tier:** `medium` (`gpt-5.6-terra`)
**Status:** PASS

## Scenario outcomes

- Native ordinary work resolved `medium` to `sonnet`, needed no broker, and blocked if
  the required native alias was absent.
- Explicit Claude-coordinated Codex ordinary work resolved `medium` to Terra and used
  broker `model list` → `session start` → `turn start`, with live-supported effort and
  an explicit block when the model or effort was unavailable.
- Main-session brainstorming stayed native Claude `opus`; a native final gate used
  `opus`, and an explicit Codex gate used Sol.
- Native Codex-harness dispatch used Terra/Sol through multi-agent tools and required
  no broker.
- Missing model or effort blocked without fallback.

## Findings

None after the D9 native-Codex/broker boundary fix.
