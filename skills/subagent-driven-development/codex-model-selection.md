# Codex model selection

Read this reference only when the operator or plan selects a Codex worker. Native
Claude Code routing remains in `SKILL.md`; this does not choose Codex by default.

| SDD tier | Codex model | Use |
|---|---|---|
| `medium` | `gpt-5.6-terra` | Default normal implementation, integration/debugging, and ordinary review. |
| `very-smart` | `gpt-5.6-sol` | Explicit elevation for difficult, high-risk, architecture, or final-gate work. |

`medium` → `gpt-5.6-terra`; `very smart` → `gpt-5.6-sol`. These are the only
operator-facing tiers. The default effort is `medium`; it is independent of the tier
and never inherits from `CLAUDE_EFFORT`.

On `start`, resolve the tier against live discovery and confirm that its model supports
the requested effort. If it does not, block with the CLI's typed refusal; never silently
fall back or substitute. `--model <live-id>` is mutually exclusive with `--tier` for
the exceptional raw-model case. The resolved model, effort, access, and cwd are fixed
at creation; `run` continues them rather than reselecting policy.

Use `codex-worker model list` only to inspect the live catalog and each model's
`supported_efforts`; choose an effort returned for that exact selected model.

Use the product form, not raw session/turn commands, for normal dispatch:

```sh
codex-worker start --name implement-a31 --prompt-file task.md --tier medium
codex-worker start --name review-b32 --prompt-file review.md --tier very-smart --read-only
```

For the live catalog or a raw-model investigation, see the technical appendix in
[Codex worker commands](codex-worker.md). It owns advanced recovery mechanics.
