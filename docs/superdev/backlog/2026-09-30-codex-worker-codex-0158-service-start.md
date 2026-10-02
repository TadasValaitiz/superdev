# Codex worker cannot start its service with codex-cli 0.158.0

**Filed:** 2026-09-30
**Source:** live verification of v8.6.0 (`--search` / `--config`), job `superdev-codex-search`
**Class:** HIL-NEEDED. This blocks every `codex-worker start`/`run` on this machine. It predates
v8.6.0: `service.py` is byte-identical from 8.1.0 (2dd410f) to 8.6.0.

## CWS-1: the private Codex socket path is now a symlink

**Status:** Fixed in v8.6.3 (D197 option 1; checkride `docs/superdev/checkrides/2026-09-30-codex-worker-search-checkride.md`).
**Surface:** `codex-worker start` / `run` / `daemon start` (global service startup)

**Observed.** `codex-worker start --name research-f876 --cwd /private/tmp/codex-research-f876 --read-only
--search --no-callback …` returns `-32024 daemon_start_failed` (`child_exited`, exit 1). `daemon.log`:

```
codex-worker daemon failed: private Codex path is not a Unix socket
```

**Measured cause.** codex-cli 0.158.0 (installed 2026-09-28) handles
`codex app-server --listen unix://PATH` differently. It creates PATH as a **symlink** to
`/private/tmp/codex-daemon-<uid>/<sha256>`, where the real socket lives. It also writes a `<sha256>.lock`
there. Reproduced by hand:

```
c -> /private/tmp/codex-daemon-501/153c08428421bb76b04b354ce9b2b376bcbfdfad96708a01315a9066bef0647c
```

`service._verify_private_socket` calls `os.lstat` and requires `S_ISSOCK`, so it refuses the symlink.
It was written for the pre-0.158 behaviour, where the socket was bound directly at the path.

**Why this needs a decision, not a patch.** Following the symlink changes the service's trust and
lifecycle model:

- The socket would live in codex's shared daemon directory (`codex-rs/uds/src/daemon_directory.rs`), not
  in codex-worker's `scw-<uid>-global` directory.
- In the hand repro, after SIGTERM to the spawned `codex` launcher, the repro shell took about 20 more
  minutes to return, and only then was the symlink gone. That fits a server outliving its launcher, but I
  did not confirm it with a process listing. Teardown, the owned-process-group guarantee, and the
  "never kill an unknown peer" rule need re-checking against codex's managed-daemon mode. A codex managed
  daemon (`codex app-server --listen unix:// --managed-daemon`, 0.159.2 from `~/.codex/packages`) is
  already running on this machine.

**Options** (for the human):

1. Accept a symlink whose target is an owner-only socket inside the owner-only
   `/private/tmp/codex-daemon-<uid>/`. Record the identity of the *target* for teardown, and re-verify
   ownership and teardown against the managed-daemon behaviour.
2. Find or ask for a codex flag that binds `--listen unix://PATH` directly (none is listed in
   `codex app-server --help` for 0.158.0).
3. Talk to the codex-managed daemon instead of spawning a private child. This is a larger redesign.

**Acceptance.** `codex-worker start` reaches readiness with codex-cli ≥ 0.158.0. The existing
service-ownership tests still hold, and a checkride covers stop/restart with the new socket layout.

## CWS-2: frozen-dataclass faults crash on Python ≥ 3.11

**Status:** Fixed in v8.6.1 (`exception_state_writable`).
**Surface:** every CLI/daemon error path that raises `RpcFault`/`FacadeFault` through a
`@contextmanager` (for example `acquire_start_lock`).

On 3.11+, `contextlib` assigns `exc.__traceback__`. A frozen dataclass's `__setattr__` rejects it with
`FrozenInstanceError: cannot assign to field '__traceback__'`, so a typed JSON error becomes a Python
traceback. `unittest` hits the same thing (`_clean_tracebacks`), which is why the suite only runs on 3.9.
`pyproject.toml` declares `requires-python >=3.9`, and the preflight does not pin an interpreter. On
2026-09-30 a reinstall from a shell with pyenv 3.12 first on PATH produced a 3.12 tool. It was put back on
3.9.6 (the previous interpreter) with `uv tool install --reinstall --python 3.9 <trusted package>`.

**Fix direction:** let the fault types accept the exception dunders (`__traceback__`, `__cause__`,
`__context__`, `__suppress_context__`, `__notes__`) and stay frozen for their fields. Run the suite on 3.12
as well as 3.9.

## CWS-3: preflight breaks under `FORCE_COLOR`

**Status:** Fixed in v8.6.1 (`uv tool dir --bin --color never`).
**Surface:** `install-codex-worker`

With `FORCE_COLOR=3` in the environment (Claude Code sessions set it), `uv tool dir --bin` prints ANSI
escapes and the preflight refuses: `uv tool dir --bin returned a missing directory: \e[36m…\e[39m`.
Running it with `env -u FORCE_COLOR NO_COLOR=1` works. **Fix direction:** call uv with `--color never`
(or set `NO_COLOR=1`) inside the script.
