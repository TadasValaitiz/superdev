# Named worker defaults and continuation

Operator: a developer who wants to start working without selecting policy every time,
recognize worker names in the remote agent picker, and send follow-up work.

Journey: create a read-only verification worker using defaults; inspect it in the
native remote agents view; continue it by the same name; stop only the disposable
verification service.

Good looks like: explicit requested default model and medium effort in creation output,
the exact worker name in the native view, a completed follow-up on the same thread
with unchanged policy, and cleanup that never touches the user's listeners.
Actual inputs are short prompts and a real authenticated Codex app-server.
If real model access or the native view is unavailable, report the gap; do not substitute.

## Residuals — 2026-10-02

- Advisory, deferred to a future CLI readability pass: unformatted `daemon status`
  includes a long migration history on one JSON line, obscuring the current listener
  and service version. It remains truthful and machine-readable; this patch does not
  change status output. An operator should be able to identify the current service
  without losing the preserved migration provenance.
- Advisory, upstream/native CLI discoverability: entering `/agents` in an ordinary
  remote prompt silently cleared without opening the agent list. Use the explicit
  `codex --remote <url> agents` entry point for this journey. This plugin does not
  implement native slash commands; the correction is recorded in the operator
  scenario and manual handoff, not misrepresented as a plugin fix.
- Advisory, deferred to the maintenance-output contract: successful daemon stop
  reports `listener: null` after teardown rather than echoing the stopped endpoint.
  The invocation and isolated state prove the target; a receipt should also make
  that identity self-contained. Verify existing listener identity after disposable
  cleanup; do not infer it from the post-stop null alone.
