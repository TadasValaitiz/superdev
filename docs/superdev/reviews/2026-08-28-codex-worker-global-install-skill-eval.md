# Codex worker global-install skill evaluation

**Date:** 2026-08-28
**Scope:** Task 2 preflight guidance in `subagent-driven-development`
**Method:** small fresh read-only agent pressure probes; executable behavior remains
covered by deterministic subprocess tests.

## RED baseline — current skill before preflight guidance

### Scenario A: selected Codex worker, command absent

Fresh agent: `/root/uv_global_install_implementer/task2_baseline_absent`

The loaded plugin contained the package, but `command -v codex-worker` failed. The agent
stopped, because the current skill supplied no authorized install/preflight contract:

> “BLOCKED: the selected Codex worker broker is not installed/on PATH; the loaded
> SDD/broker docs specify the short `codex-worker start/run` surface but provide no
> installation/preflight contract.”

Its exact intended diagnosis was:

```sh
command -v codex-worker
command -v uv
uv tool dir --bin
```

It explicitly declined both the source launcher and an improvised UV installation:

> “I would NOT invoke `skills/subagent-driven-development/scripts/codex-worker`, not use
> its absolute path or `python3` wrapper…”

> “I would NOT run `uv tool install` either… the currently loaded skill/broker never
> authorizes or specifies the install source, ownership/version/PATH checks, or
> mutation.”

Baseline failure: safe refusal, but no zero-friction recovery despite a valid loaded
package. The missing structural slot is one mandatory executable preflight before first
Codex dispatch.

### Scenario B: old source launcher shadows UV ownership

Fresh agent: `/root/uv_global_install_implementer/task2_baseline_shadow`

The probe identified the documentation gap directly:

> “the current `SKILL.md` and `codex-worker.md` contain no UV ownership, version,
> install, or PATH-shadowing preflight. Under pressure, they could lead an orchestrator
> to use the stale launcher.”

The agent chose to stop and repair PATH, but clarified that this behavior came from the
ratified branch design rather than the two loaded operating documents:

> “My STOP/recovery choice is the safe intended contract inferred from the branch’s
> ratified global-install spec/package metadata, not guidance presently delivered by
> those two docs.”

Baseline loophole: the operating skill shows short commands immediately, so a stale
PATH command can look authorized. The edited guidance must make verified UV ownership
and exact loaded-manifest equality a prerequisite, while keeping all post-preflight
commands short and preserving native Claude-only behavior.

## GREEN probes

### Scenario A: absent command

Fresh read-only agent: `/root/uv_global_install_implementer/task2_green_absent`

Verdict: **GREEN**. The edited skill made the installer and version check a hard gate
before short dispatch. The reviewer refused source fallback, chose the trusted loaded
root, and preserved native Claude's dependency-free path:

> “Because the plan selected Codex and `command -v codex-worker` is absent, I would not
> dispatch yet and would not fall back to the source launcher/absolute source path.”

> “Native Claude-only work remains dependency-free: it runs neither this preflight nor
> UV.”

It identified one minor clarity boundary: no universal shell expression can derive the
host-provided exact loaded skill path, so the instructions name that trusted value
rather than inventing an environment API. The executable independently self-resolves
and validates its root.

### Scenario B: shadowed command and missing UV

Comparative read-only re-probe:
`/root/uv_global_install_implementer/task2_baseline_shadow`

Verdict after one iteration: **GREEN**. The edited documents now require preflight
success before dispatch, refuse the repository launcher, and route shadow recovery
through `uv tool update-shell`, a new shell or the reported current-shell PATH export.
Missing UV stops only Codex dispatch and names the official UV installation guidance.

The first GREEN review found a mechanical loophole in the two-line snippet: without
shell short-circuiting, a pasted block could run `codex-worker --version` against the
shadow after installer failure. The final snippet closes it with `&&`. The reviewer
confirmed the governing behavior:

> “docs now materially prevent source fallback and premature Codex dispatch.”

> “Native Claude impact: none; both docs explicitly exempt native-Claude-only work from
> this preflight and UV.”

### Executable pressure receipts

Deterministic subprocess tests cover absent, exact-match idempotence, older/newer
replacement, foreign shadow, missing UV, loaded-root mismatch, manifest/package
mismatch, UV bin off PATH, matching UV tool off PATH without reinstall, install failure
preservation, a UV executable path containing spaces, and installed-layout missing
external Codex. The external-Codex case uses `--instance <isolated> daemon start` per
D10; measured `model list` remains RPC-only and was not changed to autostart.
