#!/usr/bin/env python3
"""Slow, credentialed end-to-end checks for the local Codex worker broker.

This is deliberately separate from ``test_*.py`` discovery.  Every subprocess
interaction is recorded under the git-ignored ``.superdev/codex-worker-live``
directory before an assertion interprets it.
"""
import argparse
import datetime
import hashlib
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "bin" / "codex-worker"
RAW_CLI = ROOT / "skills" / "subagent-driven-development" / "scripts" / "codex-worker"
LIVE_ROOT = ROOT / ".superdev" / "codex-worker-live"
Json = Dict[str, Any]
REQUIRED_ROUTES = {
    "medium": {"model": "gpt-5.6-terra", "effort": "medium"},
    "very-smart": {"model": "gpt-5.6-sol", "effort": "medium"},
}
CALLBACK_SCENARIOS = {
    "callback-common": "scenario_callback_common",
    "callback-proactive": "scenario_callback_proactive",
    "callback-origin-retention": "scenario_callback_origin_retention",
    "callback-recovery": "scenario_callback_recovery",
    "callback-security": "scenario_callback_security",
    "callback-five-workers": "scenario_callback_five_workers",
}
TASK_8_SCENARIOS = tuple(CALLBACK_SCENARIOS)


def callback_acceptance_contract() -> Json:
    return {
        "automatic_inline": True,
        "proactive_then_steer": True,
        "alternate_then_origin": True,
        "origin_retention": True,
        "terminal_statuses": ["completed", "failed", "interrupted"],
        "timeout_then_terminal": True,
        "restart_outbox": {"pending_replays_same_id": True, "written_never_replays": True},
        "artifact_digest": True,
        "security_refusals": [
            "credential_scrub", "pid_reuse", "unicode_oversize", "stale", "ambiguous",
        ],
        "standalone_disabled": True,
        "five_simultaneous": 5,
    }


def utc_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


class Recorder:
    def __init__(self, scenario: str):
        LIVE_ROOT.mkdir(parents=True, exist_ok=True)
        self.run_dir = LIVE_ROOT / ("%s-%s-%s" % (utc_stamp(), os.getpid(), scenario))
        self.run_dir.mkdir(mode=0o700)
        self.transcript_path = self.run_dir / "transcript.jsonl"
        self.sequence = 0

    def record(self, kind: str, payload: Json) -> None:
        self.sequence += 1
        event = {
            "sequence": self.sequence,
            "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "kind": kind,
        }
        event.update(payload)
        with self.transcript_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, allow_nan=False) + "\n")

    def run(self, argv: Sequence[str], timeout: float = 120.0,
            cwd: Optional[Path] = None, env: Optional[Dict[str, str]] = None) -> subprocess.CompletedProcess:
        started = time.monotonic()
        completed = subprocess.run(
            list(argv), cwd=str(cwd) if cwd is not None else None, env=env,
            capture_output=True, text=True, timeout=timeout,
        )
        self.record("command", {
            "argv": list(argv),
            "cwd": str(cwd) if cwd is not None else None,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "elapsed_seconds": time.monotonic() - started,
        })
        return completed

    def start(self, argv: Sequence[str], cwd: Optional[Path] = None,
              env: Optional[Dict[str, str]] = None) -> subprocess.Popen:
        process = subprocess.Popen(
            list(argv), cwd=str(cwd) if cwd is not None else None, env=env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )
        self.record("command_start", {
            "argv": list(argv), "cwd": str(cwd) if cwd is not None else None,
            "pid": process.pid,
        })
        return process

    def collect(self, process: subprocess.Popen, argv: Sequence[str],
                timeout: float = 930.0) -> subprocess.CompletedProcess:
        stdout, stderr = process.communicate(timeout=timeout)
        completed = subprocess.CompletedProcess(list(argv), process.returncode, stdout, stderr)
        self.record("command_result", {
            "argv": list(argv), "pid": process.pid, "returncode": process.returncode,
            "stdout": stdout, "stderr": stderr,
        })
        return completed


class CallbackInbox:
    """Measured-shape local Claude inbox used by live callback scenarios."""

    def __init__(self, path: Path):
        self.path = path
        self.frames = []  # type: List[bytes]
        self._stop = threading.Event()
        self._listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._listener.bind(str(path))
        self._listener.listen()
        os.chmod(path, 0o600)
        self._listener.settimeout(0.05)
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                connection, _ = self._listener.accept()
            except socket.timeout:
                continue
            with connection:
                chunks = []
                while True:
                    data = connection.recv(65536)
                    if not data:
                        break
                    chunks.append(data)
                if chunks:
                    self.frames.append(b"".join(chunks))

    def wait(self, count: int, timeout: float = 10.0) -> None:
        deadline = time.monotonic() + timeout
        while len(self.frames) < count and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(self.frames) >= count, {"wanted": count, "actual": len(self.frames)}

    def events(self) -> List[Json]:
        events = []
        for frame in self.frames:
            lines = frame.splitlines()
            assert len(lines) == 2, frame
            envelope = json.loads(lines[1].decode("utf-8"))
            events.append(json.loads(envelope["message"]["content"]))
        return events

    def close(self) -> None:
        self._stop.set()
        self._thread.join(1)
        self._listener.close()


class CallbackFixture:
    def __init__(self, recorder: Recorder):
        self.temp_root = Path(tempfile.mkdtemp(prefix="cw-cb-")).resolve()
        os.chmod(self.temp_root, 0o700)
        self.root = self.temp_root / "claude-config"
        self.sessions = self.root / "sessions"
        self.sockets = self.temp_root / "s"
        self.sessions.mkdir(parents=True, mode=0o700)
        self.sockets.mkdir(mode=0o700)
        os.chmod(self.root, 0o700)
        self.pid = os.getpid()
        self.proc_start = subprocess.check_output(
            ["ps", "-o", "lstart=", "-p", str(self.pid)], text=True).strip()
        self.token = uuid.uuid4().hex
        self.origin = CallbackInbox(self.sockets / (str(self.pid) + ".sock"))
        self.inboxes = [self.origin]
        self.origin_registry = self._registry(
            "task8-origin", "task8-origin-session", self.origin.path, "origin")

    def _registry(self, name: str, session_id: str, path: Path, suffix: str) -> Path:
        registry = self.sessions / ("%s-%s.json" % (self.pid, suffix))
        registry.write_text(json.dumps({
            "pid": self.pid, "sessionId": session_id,
            "messagingSocketPath": str(path), "name": name,
            "procStart": self.proc_start,
        }), encoding="utf-8")
        os.chmod(registry, 0o644)
        return registry

    def alternate(self, name: str = "task8-alternate") -> CallbackInbox:
        inbox = CallbackInbox(self.sockets / (name + ".sock"))
        self.inboxes.append(inbox)
        self._registry(name, name + "-session", inbox.path, name)
        digest = hashlib.sha256(os.path.abspath(str(inbox.path)).encode("utf-8")).hexdigest()
        key = self.sessions / ("%s.%s.key" % (self.pid, digest))
        key.write_text(json.dumps({"peerToken": uuid.uuid4().hex,
                                   "procStart": self.proc_start}), encoding="utf-8")
        os.chmod(key, 0o600)
        return inbox

    def env(self) -> Dict[str, str]:
        return {
            "CLAUDE_CONFIG_DIR": str(self.root),
            "CLAUDE_CODE_MESSAGING_SOCKET": str(self.origin.path),
            "CLAUDE_CODE_MESSAGING_TOKEN": self.token,
            "CLAUDE_CODE_SESSION_ID": "task8-origin-session",
            "CLAUDE_PID": str(self.pid),
        }

    def close(self) -> None:
        for inbox in self.inboxes:
            inbox.close()
        shutil.rmtree(str(self.temp_root))


def parse_cli_envelope(completed: subprocess.CompletedProcess) -> Json:
    stdout = completed.stdout
    assert isinstance(stdout, str) and stdout.strip(), completed
    decoder = json.JSONDecoder()
    try:
        value, offset = decoder.raw_decode(stdout.lstrip())
    except ValueError as exc:
        raise AssertionError("CLI did not emit one JSON object: %r" % stdout) from exc
    assert not stdout.lstrip()[offset:].strip(), stdout
    assert isinstance(value, dict), value
    assert value.get("jsonrpc") == "2.0" and value.get("id") == "cli", value
    return value


def require_provenance_metrics(metrics: Json) -> None:
    assert isinstance(metrics, dict) and metrics, metrics
    allowed = {"measured", "reported", "derived", "unavailable"}
    for name, evidence in metrics.items():
        assert isinstance(name, str) and name
        assert isinstance(evidence, dict) and set(evidence) == {
            "value", "source", "availability",
        }, evidence
        assert isinstance(evidence["source"], str) and evidence["source"], evidence
        assert evidence["availability"] in allowed, evidence
        if evidence["availability"] == "unavailable":
            assert evidence["value"] is None, evidence
        else:
            assert evidence["value"] is not None, evidence


def select_required_routes(models: List[Json]) -> Dict[str, Json]:
    by_id = {
        model.get("id"): model for model in models
        if isinstance(model, dict) and isinstance(model.get("id"), str)
    }
    missing = []
    for tier, route in REQUIRED_ROUTES.items():
        model = by_id.get(route["model"])
        efforts = model.get("supported_efforts") if isinstance(model, dict) else None
        if not isinstance(efforts, list) or route["effort"] not in efforts:
            missing.append(tier)
    if missing:
        raise SystemExit(
            "BLOCKED: required live Terra/Sol medium route unavailable: %s" % ", ".join(missing)
        )
    return {tier: dict(route) for tier, route in REQUIRED_ROUTES.items()}


def five_worker_names(prefix: str) -> List[str]:
    return ["%s-%s" % (prefix, suffix) for suffix in ("one", "two", "three", "four", "five")]


class ManagedCLI:
    def __init__(self, recorder: Recorder, instance: str, use_environment: bool = False):
        self.recorder = recorder
        self.instance = instance
        self.use_environment = use_environment
        self.env = os.environ.copy()
        self.env["PATH"] = str(ROOT / "bin") + os.pathsep + self.env.get("PATH", "")
        self.env.pop("CLAUDE_CODE_SESSION_ID", None)
        self.env.pop("CODEX_WORKER_INSTANCE", None)
        if use_environment:
            self.env["CODEX_WORKER_INSTANCE"] = instance

    def argv(self, *args: str) -> List[str]:
        command = [str(CLI)]
        if not self.use_environment:
            command.extend(["--instance", self.instance])
        command.extend(args)
        return command

    def run(self, *args: str, cwd: Optional[Path] = None, timeout: float = 930.0,
            check: bool = True) -> Tuple[Json, subprocess.CompletedProcess]:
        completed = self.recorder.run(self.argv(*args), timeout=timeout, cwd=cwd, env=self.env)
        payload = parse_cli_envelope(completed)
        if check:
            assert completed.returncode == 0, payload
            assert "result" in payload and "error" not in payload, payload
        return payload, completed

    def result(self, *args: str, cwd: Optional[Path] = None,
               timeout: float = 930.0) -> Json:
        return self.run(*args, cwd=cwd, timeout=timeout)[0]["result"]

    def start(self, *args: str, cwd: Optional[Path] = None) -> Tuple[List[str], subprocess.Popen]:
        argv = self.argv(*args)
        return argv, self.recorder.start(argv, cwd=cwd, env=self.env)

    def collect(self, argv: Sequence[str], process: subprocess.Popen,
                timeout: float = 930.0, check: bool = True) -> Json:
        completed = self.recorder.collect(process, argv, timeout=timeout)
        payload = parse_cli_envelope(completed)
        if check:
            assert completed.returncode == 0, payload
            assert "result" in payload and "error" not in payload, payload
        return payload

    def stop(self) -> Optional[Json]:
        try:
            payload, _ = self.run("daemon", "stop", timeout=30.0, check=False)
            return payload
        except (AssertionError, OSError, subprocess.TimeoutExpired) as exc:
            self.recorder.record("cleanup_error", {
                "phase": "managed_stop", "type": type(exc).__name__, "message": str(exc),
            })
            return None


def require_completion(result: Json, name: str, cwd: Path,
                       tier: Optional[str] = None, access: Optional[str] = None) -> Json:
    assert set(result) == {
        "worker", "turn", "messages", "structured_output", "metrics", "recovery",
    }, result
    worker = result["worker"]
    assert worker["name"] == name and worker["cwd"] == str(cwd.resolve()), worker
    if tier is not None:
        route = REQUIRED_ROUTES[tier]
        assert worker["tier"] == tier, worker
        assert worker["model"] == route["model"] and worker["effort"] == route["effort"], worker
    if access is not None:
        assert worker["access"] == access, worker
    assert result["turn"]["status"] == "completed", result["turn"]
    assert isinstance(result["messages"], list) and result["messages"], result
    for message in result["messages"]:
        assert message["selection"] in ("explicit_final", "terminal_fallback"), message
        assert isinstance(message["text"], str) and message["text"], message
    require_provenance_metrics(result["metrics"])
    return worker


class Daemon:
    def __init__(self, recorder: Recorder, name: str = "daemon", event_limit: int = 8,
                 state_path: Optional[Path] = None, codex_bin: str = "codex",
                 extra_env: Optional[Dict[str, str]] = None):
        self.recorder = recorder
        self.name = name
        self.root = recorder.run_dir / name
        self.root.mkdir(mode=0o700, exist_ok=True)
        self.socket_root = Path(tempfile.mkdtemp(prefix="cw-live-"))
        self.socket_root.chmod(0o700)
        self.socket_path = self.socket_root / "worker.sock"
        assert len(os.fsencode(str(self.socket_path))) < 104, self.socket_path
        self.state_path = state_path or (self.root / "sessions.json")
        self.event_limit = event_limit
        self.codex_bin = codex_bin
        self.extra_env = extra_env or {}
        self.proc = None  # type: Optional[subprocess.Popen]
        self.stderr_handle = None

    def start(self, expect_ready: bool = True) -> subprocess.Popen:
        if self.proc is not None and self.proc.poll() is None:
            raise AssertionError("daemon is already running")
        stderr_path = self.root / "daemon.stderr"
        self.stderr_handle = stderr_path.open("a", encoding="utf-8")
        env = os.environ.copy()
        env.update(self.extra_env)
        argv = [
            sys.executable, str(RAW_CLI), "--socket", str(self.socket_path),
            "daemon", "serve", "--state", str(self.state_path),
            "--codex-bin", self.codex_bin, "--event-limit", str(self.event_limit),
        ]
        self.proc = subprocess.Popen(
            argv, cwd=str(ROOT), env=env, stdout=subprocess.PIPE,
            stderr=self.stderr_handle, text=True,
        )
        self.recorder.record("daemon_start", {"argv": argv, "pid": self.proc.pid})
        if expect_ready:
            deadline = time.monotonic() + 30.0
            last = None
            while time.monotonic() < deadline:
                if self.proc.poll() is not None:
                    break
                try:
                    last = self.client("daemon", "status", timeout=3.0)
                except (AssertionError, OSError, subprocess.TimeoutExpired):
                    time.sleep(0.1)
                    continue
                if last["ready"]:
                    return self.proc
            self.close(force=True)
            stderr = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""
            raise AssertionError("daemon did not become ready; last=%r stderr=%s" % (last, stderr))
        return self.proc

    def cli(self, *args: str, timeout: float = 120.0,
            check: bool = True) -> Tuple[Json, subprocess.CompletedProcess]:
        completed = self.recorder.run(
            [sys.executable, str(RAW_CLI), "--socket", str(self.socket_path)] + list(args),
            timeout=timeout, cwd=ROOT,
        )
        try:
            payload = json.loads(completed.stdout)
        except (TypeError, ValueError) as exc:
            raise AssertionError("CLI did not emit one JSON object: %r" % completed.stdout) from exc
        if check:
            assert completed.returncode == 0, payload
            assert "result" in payload and "error" not in payload, payload
        return payload, completed

    def client(self, *args: str, timeout: float = 120.0) -> Json:
        payload, _ = self.cli(*args, timeout=timeout, check=True)
        result = payload["result"]
        assert isinstance(result, dict), payload
        return result

    def shutdown(self) -> None:
        if self.proc is None or self.proc.poll() is not None:
            self.close()
            return
        payload, completed = self.cli("daemon", "shutdown", timeout=15.0, check=False)
        assert completed.returncode == 0, payload
        assert payload.get("result") == {"accepted": True}, payload
        self.close()

    def close(self, force: bool = False) -> None:
        if self.proc is not None:
            if self.proc.poll() is None and force:
                self.proc.terminate()
            try:
                stdout, _ = self.proc.communicate(timeout=15.0)
            except subprocess.TimeoutExpired:
                self.proc.kill()
                stdout, _ = self.proc.communicate(timeout=5.0)
            self.recorder.record("daemon_exit", {
                "pid": self.proc.pid,
                "returncode": self.proc.returncode,
                "stdout": stdout,
            })
            if not force:
                assert self.proc.returncode == 0
        if self.stderr_handle is not None:
            self.stderr_handle.close()
            self.stderr_handle = None

    def dispose(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.close(force=True)
        expected_prefix = "cw-live-"
        if (self.socket_root.parent == Path(tempfile.gettempdir()).resolve()
                and self.socket_root.name.startswith(expected_prefix)
                and self.socket_root.is_dir()):
            shutil.rmtree(str(self.socket_root))


def choose_two_distinct_models_and_efforts(models: List[Json]) -> List[Json]:
    choices = []  # type: List[Json]
    for model in models:
        model_id = model.get("id")
        efforts = model.get("supported_efforts")
        if not isinstance(model_id, str) or not isinstance(efforts, list):
            continue
        for effort in efforts:
            if isinstance(effort, str):
                choices.append({"model": model_id, "effort": effort})
    for first in choices:
        for second in choices:
            if first["model"] != second["model"] and first["effort"] != second["effort"]:
                return [first, second]
    raise SystemExit("BLOCKED: D14 requires two distinct models and two distinct efforts")


def write_summary(recorder: Recorder, scenario: str, result: Json) -> None:
    payload = {
        "status": "PASS",
        "scenario": scenario,
        "transcript": str(recorder.transcript_path.relative_to(ROOT)),
        "result": result,
    }
    (recorder.run_dir / "summary.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, sort_keys=True, allow_nan=False))


def update_receipts(receipts: Dict[str, Json]) -> None:
    LIVE_ROOT.mkdir(parents=True, exist_ok=True)
    path = LIVE_ROOT / "receipts.json"
    current = {}  # type: Dict[str, Json]
    if path.exists():
        value = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(value, dict):
            current = value
    current.update(receipts)
    path.write_text(
        json.dumps(current, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def finish_scenario(recorder: Recorder, scenario: str, result: Json,
                    acceptance_hints: Sequence[str]) -> Json:
    transcript = str(recorder.transcript_path.relative_to(ROOT))
    command = "python3 tests/codex-worker/live_broker_check.py --scenario %s" % scenario
    update_receipts({
        hint: {
            "command": command,
            "scenario": scenario,
            "status": "PASS",
            "transcript": transcript,
        }
        for hint in acceptance_hints
    })
    write_summary(recorder, scenario, result)
    return result


def cleanup_daemon(recorder: Recorder, daemon: Daemon) -> None:
    shutdown_error = None  # type: Optional[BaseException]
    dispose_error = None  # type: Optional[BaseException]
    try:
        daemon.shutdown()
    except BaseException as exc:
        shutdown_error = exc
        recorder.record("cleanup_error", {"type": type(exc).__name__, "message": str(exc)})
        try:
            daemon.close(force=True)
        except BaseException as force_exc:
            recorder.record("cleanup_error", {
                "phase": "force_close", "type": type(force_exc).__name__,
                "message": str(force_exc),
            })
    finally:
        try:
            daemon.dispose()
        except BaseException as exc:
            dispose_error = exc
            recorder.record("cleanup_error", {
                "phase": "dispose", "type": type(exc).__name__, "message": str(exc),
            })
    if shutdown_error is not None:
        raise shutdown_error
    if dispose_error is not None:
        raise dispose_error


def require_distinct_worker_evidence(session_a: Json, session_b: Json,
                                     recovery_token: str, waited_b: Json,
                                     events_b: Json) -> None:
    assert session_a["session_id"] != session_b["session_id"], (session_a, session_b)
    assert session_a["thread_id"] != session_b["thread_id"], (session_a, session_b)
    worker_b_evidence = json.dumps(
        {"turn": waited_b.get("turn"), "events": events_b.get("events")},
        sort_keys=True,
    )
    assert recovery_token not in worker_b_evidence, "Worker A recovery token leaked into Worker B"


def require_successful_command_event(events: Sequence[Json], expected_cwd: Path,
                                     command_fragment: str) -> Json:
    expected = str(expected_cwd.resolve())
    matches = []
    for event in events:
        item = event.get("item") or {}
        data = item.get("data") or {}
        if (
            event.get("event") == "item_completed"
            and item.get("type") == "commandExecution"
            and data.get("cwd") == expected
            and command_fragment in str(data.get("command", ""))
            and data.get("status") == "completed"
            and data.get("exitCode") == 0
        ):
            matches.append(event)
    assert matches, {
        "expected_cwd": expected, "command_fragment": command_fragment,
        "command_events": [event for event in events if (event.get("item") or {}).get("type") == "commandExecution"],
    }
    return matches[-1]


def require_command(recorder: Recorder, argv: Sequence[str], cwd: Optional[Path] = None,
                    timeout: float = 120.0) -> subprocess.CompletedProcess:
    completed = recorder.run(argv, cwd=cwd, timeout=timeout)
    assert completed.returncode == 0, {
        "argv": list(argv), "stdout": completed.stdout, "stderr": completed.stderr,
    }
    return completed


def make_worktrees(recorder: Recorder) -> Tuple[Path, Path, Path]:
    repo = recorder.run_dir / "disposable-repo"
    worker_a = recorder.run_dir / "worktree-a"
    worker_b = recorder.run_dir / "worktree-b"
    repo.mkdir(mode=0o700)
    require_command(recorder, ["git", "init", "-b", "main"], cwd=repo)
    require_command(recorder, ["git", "config", "user.name", "Codex Worker Live Check"], cwd=repo)
    require_command(recorder, ["git", "config", "user.email", "codex-worker-live@example.invalid"], cwd=repo)
    (repo / "README.md").write_text("# Disposable live-check repository\n", encoding="utf-8")
    require_command(recorder, ["git", "add", "README.md"], cwd=repo)
    require_command(recorder, ["git", "commit", "-m", "seed"], cwd=repo)
    require_command(recorder, ["git", "worktree", "add", "-b", "worker-a", str(worker_a), "main"], cwd=repo)
    require_command(recorder, ["git", "worktree", "add", "-b", "worker-b", str(worker_b), "main"], cwd=repo)
    assert worker_a.is_dir() and worker_b.is_dir()
    return repo, worker_a, worker_b


def discover_pairs(daemon: Daemon) -> Tuple[List[Json], List[Json]]:
    models = daemon.client("model", "list")["models"]
    assert isinstance(models, list)
    selected = choose_two_distinct_models_and_efforts(models)
    assert len({item["model"] for item in selected}) >= 2
    assert len({item["effort"] for item in selected}) >= 2
    return models, selected


def write_prompt(recorder: Recorder, name: str, text: str) -> Path:
    path = recorder.run_dir / name
    path.write_text(text, encoding="utf-8")
    recorder.record("prompt_file", {"path": str(path), "text": text})
    return path


def start_session(daemon: Daemon, cwd: Path, name: str, model: str) -> Json:
    result = daemon.client(
        "session", "start", "--cwd", str(cwd), "--name", name, "--model", model,
    )
    session = result["session"]
    assert result["attached"] is True
    assert session["cwd"] == str(cwd.resolve())
    assert isinstance(session["session_id"], str) and session["session_id"]
    assert isinstance(session["thread_id"], str) and session["thread_id"]
    return session


def start_turn(daemon: Daemon, session_id: str, prompt_file: Path,
               selection: Json) -> Json:
    result = daemon.client(
        "turn", "start", "--session", session_id,
        "--prompt-file", str(prompt_file),
        "--model", selection["model"], "--effort", selection["effort"],
    )
    assert result["status"] == "in_progress"
    assert isinstance(result["turn_id"], str) and result["turn_id"]
    return result


def wait_turn(daemon: Daemon, session_id: str, timeout: float = 900.0) -> Json:
    result = daemon.client(
        "turn", "wait", "--session", session_id, "--timeout", str(timeout),
        timeout=timeout + 10.0,
    )
    assert result["turn"]["status"] in ("completed", "interrupted", "failed")
    return result


def scenario_concurrent_worktrees() -> Json:
    recorder = Recorder("concurrent-worktrees")
    daemon = Daemon(recorder, event_limit=40)
    cleaned = False
    try:
        _, worker_a, worker_b = make_worktrees(recorder)
        daemon.start()
        models, selected = discover_pairs(daemon)
        recovery_token = "recovery-%s" % uuid.uuid4()
        prompt_a = write_prompt(recorder, "worker-a.prompt.txt", """This is execution of an already approved implementation plan. Design approval is explicit: the exact hello.py behavior below is approved. Do not pause for questions or another approval.
Work only in the current directory and do not create design or decision documents.
Create hello.py. When executed, hello.py must write exactly `Hello from Codex\\n` to hello-output.txt.
Execute hello.py, verify hello-output.txt byte-for-byte, and report the exact command you ran.
Remember this recovery token for a later turn, but do not write the token to any file: %s
Do not create math_cli.py.
""" % recovery_token)
        prompt_b = write_prompt(recorder, "worker-b.prompt.txt", """This is execution of an already approved implementation plan. Design approval is explicit: a minimal standard-library math_cli.py using positional integer arguments is approved. Do not pause for questions or another approval.
Work only in the current directory and do not create design or decision documents.
Create a Python standard-library CLI named math_cli.py that accepts integer arguments and prints their sum.
Test it by executing `python3 math_cli.py 2 5` and require stdout to be exactly `7` followed by a newline.
Report the exact test command. Do not create hello.py or hello-output.txt.
""")
        session_a = start_session(daemon, worker_a, "hello-worker", selected[0]["model"])
        session_b = start_session(daemon, worker_b, "math-worker", selected[1]["model"])

        # Both non-blocking starts happen before either wait: this is the live
        # concurrency assertion, not inferred from elapsed time.
        run_a = start_turn(daemon, session_a["session_id"], prompt_a, selected[0])
        run_b = start_turn(daemon, session_b["session_id"], prompt_b, selected[1])
        waited_a = wait_turn(daemon, session_a["session_id"])
        waited_b = wait_turn(daemon, session_b["session_id"])
        assert waited_a["turn"]["status"] == "completed", waited_a
        assert waited_b["turn"]["status"] == "completed", waited_b
        assert (worker_a / "hello-output.txt").read_text(encoding="utf-8") == "Hello from Codex\n"
        math = require_command(
            recorder, [sys.executable, str(worker_b / "math_cli.py"), "2", "5"], cwd=worker_b,
        )
        assert math.stdout == "7\n", math.stdout
        assert not (worker_a / "math_cli.py").exists()
        assert not (worker_b / "hello.py").exists()
        assert not (worker_b / "hello-output.txt").exists()
        events_a = daemon.client("turn", "events", "--session", session_a["session_id"], "--limit", "100")
        events_b = daemon.client("turn", "events", "--session", session_b["session_id"], "--limit", "100")
        require_distinct_worker_evidence(
            session_a, session_b, recovery_token, waited_b, events_b,
        )
        hello_execution = require_successful_command_event(
            events_a["events"], worker_a, "python3 hello.py",
        )
        math_execution = require_successful_command_event(
            events_b["events"], worker_b, "python3 math_cli.py 2 5",
        )
        context = {
            "recovery_token": recovery_token,
            "session_a": session_a,
            "session_b": session_b,
            "state_path": str(daemon.state_path),
            "worktree_a": str(worker_a),
            "worktree_b": str(worker_b),
        }
        (recorder.run_dir / "recovery-context.json").write_text(
            json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8",
        )
        result = {
            "model_count": len(models),
            "selected": selected,
            "session_a": session_a,
            "session_b": session_b,
            "turn_a": {key: waited_a["turn"][key] for key in ("turn_id", "status")},
            "turn_b": {key: waited_b["turn"][key] for key in ("turn_id", "status")},
            "event_count_a": len(events_a["events"]),
            "event_count_b": len(events_b["events"]),
            "hello_output": "Hello from Codex\\n",
            "math_output": math.stdout,
            "hello_execution": hello_execution,
            "math_execution": math_execution,
            "worker_b_token_absent": True,
        }
        cleanup_daemon(recorder, daemon)
        cleaned = True
        return finish_scenario(recorder, "concurrent-worktrees", result, ["AH2", "AH8"])
    finally:
        if not cleaned:
            cleanup_daemon(recorder, daemon)


def assert_typed_error(payload: Json, completed: subprocess.CompletedProcess,
                       kind: str) -> Json:
    assert completed.returncode != 0, payload
    assert "error" in payload and "result" not in payload, payload
    error = payload["error"]
    assert error["data"]["kind"] == kind, error
    return error


def scenario_control() -> Json:
    recorder = Recorder("control")
    daemon = Daemon(recorder, event_limit=40)
    cleaned = False
    try:
        _, worker_a, worker_b = make_worktrees(recorder)
        daemon.start()
        _, selected = discover_pairs(daemon)
        steer_session = start_session(daemon, worker_a, "steer-worker", selected[0]["model"])
        interrupt_session = start_session(daemon, worker_b, "interrupt-worker", selected[1]["model"])
        broad_prompt = write_prompt(recorder, "broad.prompt.txt", """Work only in the current directory.
First execute `python3 -c "import time; time.sleep(8)"` so there is time for an in-flight steer.
After that, create broad-001.txt through broad-050.txt one at a time and summarize them.
""")
        steer_started = start_turn(
            daemon, steer_session["session_id"], broad_prompt, selected[0],
        )
        steer_result = daemon.client(
            "turn", "steer", "--session", steer_session["session_id"],
            "--prompt", (
                "Steer accepted: abandon the broad task. Remove any broad-*.txt files if present. "
                "Create only steered.txt with exact UTF-8 content `steer accepted\\n`, verify it, "
                "then finish."
            ),
        )
        assert steer_result == {
            "session_id": steer_session["session_id"],
            "thread_id": steer_session["thread_id"],
            "turn_id": steer_started["turn_id"],
            "accepted": True,
        }
        steered = wait_turn(daemon, steer_session["session_id"])
        assert steered["turn"]["status"] == "completed", steered
        assert (worker_a / "steered.txt").read_text(encoding="utf-8") == "steer accepted\n"
        assert list(worker_a.glob("broad-*.txt")) == []
        idle_steer_payload, idle_steer_completed = daemon.cli(
            "turn", "steer", "--session", steer_session["session_id"],
            "--prompt", "This must refuse while idle.", check=False,
        )
        idle_steer = assert_typed_error(idle_steer_payload, idle_steer_completed, "turn_not_active")

        interrupt_prompt = write_prompt(recorder, "interrupt.prompt.txt", """Work only in the current directory.
Execute `python3 -c "import time; time.sleep(30)"`, then perform a long analysis of every tracked file.
Do not finish before the command completes.
""")
        interrupt_started = start_turn(
            daemon, interrupt_session["session_id"], interrupt_prompt, selected[1],
        )
        interrupted_result = daemon.client(
            "turn", "interrupt", "--session", interrupt_session["session_id"],
        )
        assert interrupted_result["accepted"] is True
        assert interrupted_result["turn_id"] == interrupt_started["turn_id"]
        interrupted = wait_turn(daemon, interrupt_session["session_id"], timeout=60.0)
        assert interrupted["turn"]["status"] == "interrupted", interrupted
        idle_interrupt_payload, idle_interrupt_completed = daemon.cli(
            "turn", "interrupt", "--session", interrupt_session["session_id"], check=False,
        )
        idle_interrupt = assert_typed_error(
            idle_interrupt_payload, idle_interrupt_completed, "turn_not_active",
        )
        result = {
            "selected": selected,
            "steer": steer_result,
            "steered_turn": {key: steered["turn"][key] for key in ("turn_id", "status")},
            "idle_steer_error": idle_steer,
            "interrupt": interrupted_result,
            "interrupted_turn": {
                key: interrupted["turn"][key] for key in ("turn_id", "status")
            },
            "idle_interrupt_error": idle_interrupt,
        }
        cleanup_daemon(recorder, daemon)
        cleaned = True
        return finish_scenario(recorder, "control", result, ["AH3", "AH4"])
    finally:
        if not cleaned:
            cleanup_daemon(recorder, daemon)


def waiter_command(daemon: Daemon, session_id: str, timeout: float) -> List[str]:
    return [
        sys.executable, str(RAW_CLI), "--socket", str(daemon.socket_path),
        "turn", "wait", "--session", session_id, "--timeout", str(timeout),
    ]


def collect_waiter(recorder: Recorder, label: str, argv: Sequence[str],
                   proc: subprocess.Popen, timeout: float) -> Json:
    stdout, stderr = proc.communicate(timeout=timeout)
    recorder.record("waiter_result", {
        "label": label, "argv": list(argv), "pid": proc.pid,
        "returncode": proc.returncode, "stdout": stdout, "stderr": stderr,
    })
    assert proc.returncode == 0, {"stdout": stdout, "stderr": stderr}
    payload = json.loads(stdout)
    assert payload.get("result", {}).get("turn", {}).get("status") == "completed", payload
    return payload["result"]


def scenario_observe_socket() -> Json:
    recorder = Recorder("observe-socket")
    daemon = Daemon(recorder, event_limit=3)
    cleaned = False
    try:
        _, worker_a, _ = make_worktrees(recorder)
        daemon.start()
        _, selected = discover_pairs(daemon)
        session = start_session(daemon, worker_a, "observe-worker", selected[0]["model"])
        prompt = write_prompt(recorder, "observe.prompt.txt", """Work only in the current directory.
First execute `python3 -c "import time; time.sleep(7)"` so concurrent observers can attach.
Then inspect README.md, create observe.txt with exact content `observed\\n`, run a separate command to verify its bytes, and finish.
""")
        started = start_turn(daemon, session["session_id"], prompt, selected[0])
        argv_a = waiter_command(daemon, session["session_id"], 120.0)
        argv_b = waiter_command(daemon, session["session_id"], 120.0)
        waiter_a = subprocess.Popen(argv_a, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        waiter_b = subprocess.Popen(argv_b, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        recorder.record("waiter_start", {"label": "a", "argv": argv_a, "pid": waiter_a.pid})
        recorder.record("waiter_start", {"label": "b", "argv": argv_b, "pid": waiter_b.pid})
        status_active = daemon.client("turn", "status", "--session", session["session_id"])
        assert status_active["active_turn_id"] == started["turn_id"], status_active
        first_live_page = daemon.client(
            "turn", "events", "--session", session["session_id"], "--after", "0", "--limit", "1",
        )
        assert len(first_live_page["events"]) == 1, first_live_page

        result_a = collect_waiter(recorder, "a", argv_a, waiter_a, 150.0)
        result_b = collect_waiter(recorder, "b", argv_b, waiter_b, 150.0)
        assert result_a["turn"]["turn_id"] == result_b["turn"]["turn_id"] == started["turn_id"]
        assert result_a["turn"]["status"] == result_b["turn"]["status"] == "completed"
        assert result_a["turn"] == result_b["turn"]
        assert (worker_a / "observe.txt").read_text(encoding="utf-8") == "observed\n"

        status_after_a = daemon.client("turn", "status", "--session", session["session_id"])
        status_after_b = daemon.client("turn", "status", "--session", session["session_id"])
        assert status_after_a == status_after_b
        assert status_after_a["latest_turn"]["turn_id"] == started["turn_id"]
        page_one = daemon.client(
            "turn", "events", "--session", session["session_id"], "--after", "0", "--limit", "1",
        )
        assert page_one["truncated"] is True, page_one
        assert len(page_one["events"]) == 1, page_one
        first_cursor = page_one["events"][0]["cursor"]
        assert page_one["next_cursor"] == first_cursor
        page_two = daemon.client(
            "turn", "events", "--session", session["session_id"],
            "--after", str(first_cursor), "--limit", "1",
        )
        assert len(page_two["events"]) == 1, page_two
        assert page_two["events"][0]["cursor"] > first_cursor, page_two

        socket_metadata = os.lstat(str(daemon.socket_path))
        assert stat.S_ISSOCK(socket_metadata.st_mode)
        assert stat.S_IMODE(socket_metadata.st_mode) == 0o600
        assert socket_metadata.st_uid == os.getuid()
        daemon_pid = daemon.proc.pid  # type: ignore[union-attr]
        lsof = recorder.run(
            ["lsof", "-Pan", "-p", str(daemon_pid), "-iTCP", "-sTCP:LISTEN"], timeout=15.0,
        )
        assert lsof.returncode in (0, 1), lsof.returncode
        assert lsof.stdout.strip() == "", lsof.stdout

        collision_argv = [
            sys.executable, str(RAW_CLI), "--socket", str(daemon.socket_path),
            "daemon", "serve", "--state", str(recorder.run_dir / "collision-state.json"),
            "--codex-bin", "codex", "--event-limit", "3",
        ]
        before_collision = (socket_metadata.st_dev, socket_metadata.st_ino)
        collision = recorder.run(collision_argv, cwd=ROOT, timeout=30.0)
        assert collision.returncode != 0, collision.stderr
        assert collision.stdout == ""
        after_collision_metadata = os.lstat(str(daemon.socket_path))
        assert (after_collision_metadata.st_dev, after_collision_metadata.st_ino) == before_collision
        assert daemon.client("daemon", "status")["ready"] is True

        daemon.shutdown()
        assert not daemon.socket_path.exists()
        stale = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            stale.bind(str(daemon.socket_path))
        finally:
            stale.close()
        stale_metadata = os.lstat(str(daemon.socket_path))
        assert stat.S_ISSOCK(stale_metadata.st_mode)
        stale_identity = (stale_metadata.st_dev, stale_metadata.st_ino)
        daemon.start()
        replaced_metadata = os.lstat(str(daemon.socket_path))
        assert stat.S_IMODE(replaced_metadata.st_mode) == 0o600
        assert (replaced_metadata.st_dev, replaced_metadata.st_ino) != stale_identity
        restarted = daemon.client("daemon", "status")
        assert restarted["ready"] is True
        result = {
            "session_id": session["session_id"],
            "turn_id": started["turn_id"],
            "waiter_status": result_a["turn"]["status"],
            "retained_first_cursor": first_cursor,
            "next_cursor": page_two["next_cursor"],
            "truncated": page_one["truncated"],
            "socket_mode": "0600",
            "live_collision_returncode": collision.returncode,
            "stale_socket_replaced": True,
            "tcp_listener_output": lsof.stdout,
            "restarted_daemon_pid": restarted["daemon_pid"],
        }
        cleanup_daemon(recorder, daemon)
        cleaned = True
        return finish_scenario(recorder, "observe-socket", result, ["AH7", "AH10"])
    finally:
        if not cleaned:
            cleanup_daemon(recorder, daemon)


def scenario_recovery() -> Json:
    recorder = Recorder("recovery")
    state_path = recorder.run_dir / "durable-sessions.json"
    daemon = Daemon(recorder, name="uuid-daemon", event_limit=40, state_path=state_path)
    raw_daemon = None  # type: Optional[Daemon]
    daemon_cleaned = False
    raw_cleaned = False
    try:
        _, worker_a, _ = make_worktrees(recorder)
        daemon.start()
        _, selected = discover_pairs(daemon)
        recovery_token = "remembered-%s" % uuid.uuid4()
        seed_prompt = write_prompt(recorder, "recovery-seed.prompt.txt", """Work only in the current directory.
Remember the following recovery token for later turns in this conversation, but do not write it to any file and do not repeat it in your final response: %s
Create seed.txt with exact content `seeded\\n`, verify it, and then finish.
""" % recovery_token)
        session = start_session(daemon, worker_a, "recovery-worker", selected[0]["model"])
        seed_started = start_turn(daemon, session["session_id"], seed_prompt, selected[0])
        seed_waited = wait_turn(daemon, session["session_id"])
        assert seed_waited["turn"]["status"] == "completed", seed_waited
        assert (worker_a / "seed.txt").read_text(encoding="utf-8") == "seeded\n"
        assert not (worker_a / "resumed-token.txt").exists()
        assert not (worker_a / "raw-resumed-token.txt").exists()

        daemon.shutdown()
        daemon.start()
        detached = daemon.client("session", "show", "--session", session["session_id"])
        assert detached["attached"] is False, detached
        uuid_resumed = daemon.client(
            "session", "resume", "--session", session["session_id"],
        )
        assert uuid_resumed["attached"] is True
        assert uuid_resumed["session"]["session_id"] == session["session_id"]
        assert uuid_resumed["session"]["thread_id"] == session["thread_id"]
        uuid_prompt = write_prompt(recorder, "uuid-recovery.prompt.txt", """Without searching outside this conversation, write the recovery token I previously asked you to remember to resumed-token.txt, followed by exactly one newline. Verify the file, do not explain the token, and finish.""")
        uuid_started = start_turn(daemon, session["session_id"], uuid_prompt, selected[0])
        uuid_waited = wait_turn(daemon, session["session_id"])
        assert uuid_waited["turn"]["status"] == "completed", uuid_waited
        resumed_token_path = worker_a / "resumed-token.txt"
        assert resumed_token_path.read_text(encoding="utf-8").strip() == recovery_token

        # Remove the materialized proof before raw recovery.  The second proof
        # must come from resumed conversational context, not a workspace file.
        resumed_token_path.unlink()
        recorder.record("fixture_cleanup", {"removed": str(resumed_token_path)})
        assert recovery_token not in "\n".join(
            path.read_text(encoding="utf-8", errors="replace")
            for path in worker_a.iterdir() if path.is_file()
        )
        daemon.shutdown()

        raw_daemon = Daemon(
            recorder, name="raw-daemon", event_limit=40,
            state_path=recorder.run_dir / "fresh-empty-registry.json",
        )
        raw_daemon.start()
        _, raw_selected = discover_pairs(raw_daemon)
        raw_resume_args = [
            "session", "resume", "--thread", session["thread_id"], "--name", "raw-recovered-worker",
        ]
        assert "--cwd" not in raw_resume_args
        raw_resumed = raw_daemon.client(*raw_resume_args)
        raw_session = raw_resumed["session"]
        assert raw_resumed["attached"] is True
        assert raw_session["session_id"] != session["session_id"]
        assert raw_session["thread_id"] == session["thread_id"]
        assert raw_session["cwd"] == str(worker_a.resolve())
        raw_prompt = write_prompt(recorder, "raw-recovery.prompt.txt", """Use only retained conversation context: write the recovery token I asked you to remember to raw-resumed-token.txt, followed by exactly one newline. Verify the file and finish.""")
        raw_started = start_turn(raw_daemon, raw_session["session_id"], raw_prompt, raw_selected[0])
        raw_waited = wait_turn(raw_daemon, raw_session["session_id"])
        assert raw_waited["turn"]["status"] == "completed", raw_waited
        raw_token_path = worker_a / "raw-resumed-token.txt"
        assert raw_token_path.read_text(encoding="utf-8").strip() == recovery_token
        result = {
            "original_session_id": session["session_id"],
            "thread_id": session["thread_id"],
            "seed_turn_id": seed_started["turn_id"],
            "uuid_resume_session_id": uuid_resumed["session"]["session_id"],
            "uuid_resume_turn_id": uuid_started["turn_id"],
            "raw_recovered_session_id": raw_session["session_id"],
            "raw_recovered_cwd": raw_session["cwd"],
            "raw_resume_turn_id": raw_started["turn_id"],
            "caller_supplied_cwd": False,
            "uuid_token_match": True,
            "raw_token_match": True,
        }
        cleanup_daemon(recorder, raw_daemon)
        raw_cleaned = True
        cleanup_daemon(recorder, daemon)
        daemon_cleaned = True
        return finish_scenario(recorder, "recovery", result, ["AH5", "AH6"])
    finally:
        if raw_daemon is not None and not raw_cleaned:
            cleanup_daemon(recorder, raw_daemon)
        if not daemon_cleaned:
            cleanup_daemon(recorder, daemon)


def make_fake_codex_wrapper(recorder: Recorder, mode: str) -> Path:
    fake = ROOT / "tests" / "codex-worker" / "fake_codex.py"
    wrapper = recorder.run_dir / ("fake-codex-%s" % mode)
    wrapper.write_text(
        "#!/usr/bin/env python3\n"
        "import runpy\n"
        "import sys\n"
        "sys.argv = [%r, '--mode', %r, '--delay', '0.05']\n"
        "runpy.run_path(%r, run_name='__main__')\n" % (str(fake), mode, str(fake)),
        encoding="utf-8",
    )
    wrapper.chmod(0o700)
    return wrapper


def scenario_approvals() -> Json:
    recorder = Recorder("approvals")
    modes = {
        "approval-command": (
            "item/commandExecution/requestApproval", {"decision": "decline"},
        ),
        "approval-file": (
            "item/fileChange/requestApproval", {"decision": "decline"},
        ),
        "approval-user": (
            "item/tool/requestUserInput", {"answers": {}},
        ),
    }
    results = {}  # type: Dict[str, Json]
    daemons = []  # type: List[Daemon]
    try:
        fixture_cwd = recorder.run_dir / "approval-workspace"
        fixture_cwd.mkdir(mode=0o700)
        for mode, (approval_method, expected_response) in modes.items():
            wrapper = make_fake_codex_wrapper(recorder, mode)
            daemon = Daemon(
                recorder, name=mode, event_limit=20,
                state_path=recorder.run_dir / ("%s-sessions.json" % mode),
                codex_bin=str(wrapper),
            )
            daemons.append(daemon)
            daemon.start()
            session = start_session(daemon, fixture_cwd, mode, "fake-model-a")
            prompt = write_prompt(
                recorder, "%s.prompt.txt" % mode,
                "Exercise deterministic fail-closed approval handling for %s." % approval_method,
            )
            started = start_turn(
                daemon, session["session_id"], prompt,
                {"model": "fake-model-a", "effort": "medium"},
            )
            waited = wait_turn(daemon, session["session_id"], timeout=10.0)
            assert waited["turn"]["status"] == "completed", waited
            events = daemon.client(
                "turn", "events", "--session", session["session_id"], "--limit", "100",
            )
            approval_events = [event for event in events["events"] if event["event"] == "approval_declined"]
            assert len(approval_events) == 1, events
            approval_event = approval_events[0]
            assert approval_event["turn_id"] == started["turn_id"]
            assert approval_event["item"]["type"] == approval_method
            assert approval_event["item"]["data"] == {"decision": "decline"}
            assert "SECRET" not in json.dumps(approval_event, sort_keys=True)
            upstream_items = [
                item for item in waited["turn"]["items"] if item["type"] == "approvalResult"
            ]
            assert len(upstream_items) == 1, waited
            assert upstream_items[0]["data"]["decision"] == expected_response
            results[mode] = {
                "approval_method": approval_method,
                "expected_upstream_response": expected_response,
                "session_id": session["session_id"],
                "turn_id": started["turn_id"],
                "turn_status": waited["turn"]["status"],
                "approval_event": approval_event,
                "secret_in_audit_event": False,
            }
            daemon.shutdown()
        result = {
            "label": "deterministic live broker + fake upstream",
            "modes": results,
        }
        for daemon in reversed(daemons):
            cleanup_daemon(recorder, daemon)
        daemons.clear()
        return finish_scenario(recorder, "approvals", result, ["AH12"])
    finally:
        for daemon in reversed(daemons):
            cleanup_daemon(recorder, daemon)


def _workspace(recorder: Recorder, name: str) -> Path:
    path = recorder.run_dir / name
    path.mkdir(mode=0o700)
    (path / "README.md").write_text("# Task 8 live workspace\n", encoding="utf-8")
    return path


def _identity(worker: Json) -> Tuple[str, str, str, str, str, str]:
    return (
        worker["session_id"], worker["thread_id"], worker["cwd"],
        worker["model"], worker["effort"], worker["access"],
    )


def scenario_common_journey() -> Json:
    recorder = Recorder("common-journey")
    instance = "task8-common-%s" % uuid.uuid4().hex[:12]
    runner = ManagedCLI(recorder, instance)
    cwd = _workspace(recorder, "common-workspace")
    name = "common-%s" % uuid.uuid4().hex[:8]
    stopped = False
    try:
        first = runner.result(
            "start", "--name", name, "--prompt",
            "Reply with exactly COMMON-FIRST and no other text.", cwd=cwd,
        )
        first_worker = require_completion(first, name, cwd, "medium", "full")
        follow = runner.result(
            "run", "--name", name, "--prompt",
            "Reply with exactly COMMON-FOLLOWUP and no other text.", cwd=cwd,
        )
        follow_worker = require_completion(follow, name, cwd, "medium", "full")
        assert _identity(first_worker) == _identity(follow_worker), (first_worker, follow_worker)
        status = runner.result("status", "--name", name, cwd=cwd)
        messages = runner.result("messages", "--name", name, "--tail", "2", cwd=cwd)
        assert status["worker"] == follow_worker and status["daemon_status"] == "ready", status
        assert messages["worker"] == follow_worker and messages["returned"] >= 1, messages
        stop = runner.result("daemon", "stop", cwd=cwd, timeout=30.0)
        stopped = True
        assert stop["status_after"] == "stopped" and stop["durable_state"] == "preserved", stop
        restarted = runner.result(
            "run", "--name", name, "--prompt",
            "Reply with exactly COMMON-RESTARTED and no other text.", cwd=cwd,
        )
        restarted_worker = require_completion(restarted, name, cwd, "medium", "full")
        stopped = False
        assert _identity(first_worker) == _identity(restarted_worker), restarted_worker
        result = {
            "instance": instance,
            "worker": first_worker,
            "first_turn": first["turn"],
            "follow_turn": follow["turn"],
            "restart_turn": restarted["turn"],
            "same_recovery_identity": True,
            "messages_returned": messages["returned"],
            "stop": stop,
            "metric_evidence": restarted["metrics"],
        }
        runner.stop()
        stopped = True
        return finish_scenario(recorder, "common-journey", result, ["AH1", "AH2", "AH5"])
    finally:
        if not stopped:
            runner.stop()


def scenario_five_workers() -> Json:
    recorder = Recorder("five-workers")
    instance = "task8-five-%s" % uuid.uuid4().hex[:12]
    runner = ManagedCLI(recorder, instance)
    names = five_worker_names("five-%s" % uuid.uuid4().hex[:6])
    workspaces = [_workspace(recorder, "workspace-%d" % index) for index in range(1, 6)]
    commands = []
    processes = []
    try:
        for index, (name, cwd) in enumerate(zip(names, workspaces), 1):
            argv, process = runner.start(
                "start", "--name", name, "--prompt",
                "Reply with exactly FIVE-WORKER-%d and no other text." % index,
                cwd=cwd,
            )
            commands.append(argv)
            processes.append(process)
        assert len(processes) == 5 and all(process.poll() is None for process in processes), [
            process.poll() for process in processes
        ]
        results = []
        for name, cwd, argv, process in zip(names, workspaces, commands, processes):
            payload = runner.collect(argv, process)
            results.append(payload["result"])
            require_completion(payload["result"], name, cwd, "medium", "full")
        workers = [result["worker"] for result in results]
        assert len(workers) == 5
        assert {worker["name"] for worker in workers} == set(names)
        assert len({worker["session_id"] for worker in workers}) == 5
        assert len({worker["thread_id"] for worker in workers}) == 5
        assert {worker["cwd"] for worker in workers} == {str(path.resolve()) for path in workspaces}
        status = runner.result("daemon", "status")
        assert status["status"] == "ready" and status["worker_count"] == 5, status
        result = {
            "simultaneous_worker_count": 5,
            "names": names,
            "workers": workers,
            "daemon_pid": status["daemon_pid"],
            "codex_pid": status["codex_pid"],
            "worker_count_source": "codex-worker daemon status transcript",
        }
        runner.stop()
        return finish_scenario(recorder, "five-workers", result, ["AH3"])
    finally:
        for argv, process in zip(commands, processes):
            if process.poll() is None:
                process.terminate()
                recorder.collect(process, argv, timeout=10.0)
        runner.stop()


def _wait_active(runner: ManagedCLI, name: str, cwd: Path,
                 timeout: float = 45.0) -> Json:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        payload, completed = runner.run("status", "--name", name, cwd=cwd, check=False)
        last = payload
        if completed.returncode == 0 and payload.get("result", {}).get("active_turn_id"):
            return payload["result"]
        time.sleep(0.1)
    raise AssertionError("worker did not become active: %r" % last)


def scenario_control_recovery() -> Json:
    recorder = Recorder("control-recovery")
    instance = "task8-control-%s" % uuid.uuid4().hex[:12]
    runner = ManagedCLI(recorder, instance)
    steer_cwd = _workspace(recorder, "steer-workspace")
    interrupt_cwd = _workspace(recorder, "interrupt-workspace")
    steer_name = "steer-%s" % uuid.uuid4().hex[:8]
    interrupt_name = "interrupt-%s" % uuid.uuid4().hex[:8]
    pending = []
    try:
        steer_argv, steer_proc = runner.start(
            "start", "--name", steer_name, "--prompt",
            "Run `python3 -c \"import time; time.sleep(10)\"`, then reply STEER-ORIGINAL.",
            cwd=steer_cwd,
        )
        pending.append((steer_argv, steer_proc))
        steer_status = _wait_active(runner, steer_name, steer_cwd)
        live_messages = runner.result("messages", "--name", steer_name, "--tail", "2", cwd=steer_cwd)
        steered = runner.result(
            "steer", "--name", steer_name, "--prompt",
            "After the current command, reply with exactly STEER-ACCEPTED and finish.", cwd=steer_cwd,
        )
        steer_payload = runner.collect(steer_argv, steer_proc, timeout=120.0)
        pending.remove((steer_argv, steer_proc))
        require_completion(steer_payload["result"], steer_name, steer_cwd, "medium", "full")
        idle_payload, idle_completed = runner.run(
            "steer", "--name", steer_name, "--prompt", "must refuse", cwd=steer_cwd,
            check=False,
        )
        idle = assert_typed_error(idle_payload, idle_completed, "turn_not_active")

        interrupt_argv, interrupt_proc = runner.start(
            "start", "--name", interrupt_name, "--prompt",
            "Run `python3 -c \"import time; time.sleep(30)\"`, then reply TOO-LATE.",
            cwd=interrupt_cwd,
        )
        pending.append((interrupt_argv, interrupt_proc))
        interrupt_status = _wait_active(runner, interrupt_name, interrupt_cwd)
        interrupted = runner.result("interrupt", "--name", interrupt_name, cwd=interrupt_cwd)
        interrupt_payload = runner.collect(interrupt_argv, interrupt_proc, timeout=60.0)
        pending.remove((interrupt_argv, interrupt_proc))
        assert interrupt_payload["result"]["turn"]["status"] == "interrupted", interrupt_payload

        daemon_status = runner.result("daemon", "status")
        socket_path = daemon_status["instance"]["socket_path"]
        raw_status_completed = recorder.run(
            [str(CLI), "--socket", socket_path, "daemon", "status"],
            env=runner.env, timeout=30.0,
        )
        raw_status = parse_cli_envelope(raw_status_completed)
        assert raw_status_completed.returncode == 0 and raw_status["result"]["ready"] is True
        raw_shutdown_completed = recorder.run(
            [str(CLI), "--socket", socket_path, "daemon", "shutdown"],
            env=runner.env, timeout=30.0,
        )
        raw_shutdown = parse_cli_envelope(raw_shutdown_completed)
        assert raw_shutdown_completed.returncode == 0
        assert raw_shutdown["result"] == {"accepted": True}, raw_shutdown
        result = {
            "steer_active_turn_id": steer_status["active_turn_id"],
            "live_messages_returned": live_messages["returned"],
            "steer": steered,
            "idle_steer": idle,
            "interrupt_active_turn_id": interrupt_status["active_turn_id"],
            "interrupt": interrupted,
            "interrupted_turn": interrupt_payload["result"]["turn"],
            "legacy_socket_status": raw_status["result"],
            "legacy_socket_shutdown": raw_shutdown["result"],
        }
        return finish_scenario(recorder, "control-recovery", result, ["AH4", "AH12"])
    finally:
        for argv, process in pending:
            if process.poll() is None:
                process.terminate()
                recorder.collect(process, argv, timeout=10.0)
        runner.stop()


def pause_goal_preserving_budget(runner, name: str, cwd: Path, preceding: Json) -> Json:
    updated = runner.result(
        "goal", "set", "--name", name, "--status", "paused", cwd=cwd,
    )
    assert updated["goal"]["token_budget"] == preceding["goal"]["token_budget"], (
        preceding, updated)
    return updated


def scenario_native_proxies() -> Json:
    recorder = Recorder("native-proxies")
    instance = "task8-native-%s" % uuid.uuid4().hex[:12]
    runner = ManagedCLI(recorder, instance)
    cwd = _workspace(recorder, "native-workspace")
    name = "native-%s" % uuid.uuid4().hex[:8]
    try:
        first = runner.result(
            "start", "--name", name, "--goal", "Complete the Task 8 native proxy check",
            "--token-budget", "20000", "--prompt",
            "Reply with exactly NATIVE-FIRST and no other text.", cwd=cwd,
        )
        worker = require_completion(first, name, cwd, "medium", "full")
        goal_initial = runner.result("goal", "show", "--name", name, cwd=cwd)
        assert goal_initial["availability"] == "present", goal_initial
        assert goal_initial["goal"]["objective"] == "Complete the Task 8 native proxy check"
        history = runner.result("history", "--name", name, "--tail", "2", cwd=cwd)
        assert history["returned"] >= 1 and history["returned"] == len(history["turns"]), history
        goal_updated = pause_goal_preserving_budget(runner, name, cwd, goal_initial)
        assert goal_updated["goal"]["status"] == "paused"
        status_after_pause = runner.result("status", "--name", name, cwd=cwd)
        limits_payload, limits_completed = runner.run("limits", cwd=cwd, check=False)
        if limits_completed.returncode == 0:
            limits = limits_payload["result"]
            assert limits["availability"] == "available" and isinstance(limits["rate_limits"], dict)
            limits_outcome = {"kind": "available", "payload": limits}
        else:
            error = assert_typed_error(limits_payload, limits_completed, "limits_unavailable")
            limits_outcome = {"kind": "typed_unavailable", "payload": error}
        result = {
            "worker": worker,
            "goal_initial": goal_initial,
            "goal_updated": goal_updated,
            "history": history,
            "status_after_pause": status_after_pause,
            "limits": limits_outcome,
            "first_metrics": first["metrics"],
        }
        runner.stop()
        return finish_scenario(recorder, "native-proxies", result, ["AH6", "AH10"])
    finally:
        runner.stop()


def scenario_access_schema() -> Json:
    recorder = Recorder("access-schema")
    instance = "task8-access-%s" % uuid.uuid4().hex[:12]
    runner = ManagedCLI(recorder, instance, use_environment=True)
    full_cwd = _workspace(recorder, "full-workspace")
    readonly_cwd = _workspace(recorder, "readonly-workspace")
    schema_cwd = _workspace(recorder, "schema-workspace")
    external = recorder.run_dir / "external-context.txt"
    external.write_text("EXTERNAL-CONTEXT-%s\n" % uuid.uuid4().hex, encoding="utf-8")
    readonly_target = readonly_cwd / "must-not-exist.txt"
    schema_path = recorder.run_dir / "verdict-schema.json"
    schema_path.write_text(json.dumps({
        "type": "object",
        "properties": {
            "verdict": {"type": "string"},
            "report": {"type": "string"},
            "review": {"type": "string"},
        },
        "required": ["verdict", "report", "review"],
        "additionalProperties": False,
    }), encoding="utf-8")
    full_name = "full-%s" % uuid.uuid4().hex[:8]
    readonly_name = "readonly-%s" % uuid.uuid4().hex[:8]
    schema_name = "schema-%s" % uuid.uuid4().hex[:8]
    try:
        full = runner.result(
            "start", "--name", full_name, "--tier", "very-smart", "--prompt",
            "Read the absolute file %s and report its exact single line." % external,
            cwd=full_cwd,
        )
        full_worker = require_completion(full, full_name, full_cwd, "very-smart", "full")
        assert external.read_text(encoding="utf-8").strip() in "\n".join(
            message["text"] for message in full["messages"]
        ), full["messages"]
        readonly = runner.result(
            "start", "--name", readonly_name, "--read-only", "--prompt",
            "Attempt to create must-not-exist.txt in the current directory with any content. "
            "Report whether the sandbox allowed the write.", cwd=readonly_cwd,
        )
        readonly_worker = require_completion(
            readonly, readonly_name, readonly_cwd, "medium", "read_only",
        )
        assert not readonly_target.exists(), readonly_target
        schema = runner.result(
            "start", "--name", schema_name, "--output-schema", str(schema_path),
            "--prompt", "Return verdict PASS, report Task 8 schema live, review complete.",
            cwd=schema_cwd,
        )
        schema_worker = require_completion(schema, schema_name, schema_cwd, "medium", "full")
        structured = schema["structured_output"]
        assert isinstance(structured, dict) and set(structured) == {
            "verdict", "report", "review",
        }, structured
        daemon_status = runner.result("daemon", "status")
        assert daemon_status["instance"]["source"] == "environment", daemon_status
        selections = {
            message["selection"] for result in (full, readonly, schema)
            for message in result["messages"]
        }
        result = {
            "instance_source": daemon_status["instance"]["source"],
            "full_worker": full_worker,
            "read_only_worker": readonly_worker,
            "schema_worker": schema_worker,
            "read_only_write_present": readonly_target.exists(),
            "structured_output": structured,
            "message_selections": sorted(selections),
            "schema_messages": schema["messages"],
        }
        runner.stop()
        return finish_scenario(recorder, "access-schema", result, ["AH7", "AH8", "AH10"])
    finally:
        runner.stop()


def _callback_runner(recorder: Recorder, label: str) -> Tuple[ManagedCLI, CallbackFixture]:
    runner = ManagedCLI(recorder, "task8-%s-%s" % (label, uuid.uuid4().hex[:10]))
    fixture = CallbackFixture(recorder)
    runner.env.update(fixture.env())
    return runner, fixture


def _require_event(inbox: CallbackInbox, index: int, kind: str,
                   completion: Optional[Json] = None) -> Json:
    inbox.wait(index + 1)
    event = inbox.events()[index]
    assert event["schema"] == "codex-worker.claude-callback/v1", event
    assert event["event"] == kind and isinstance(event["event_id"], str), event
    if completion is not None:
        assert event["payload"]["completion"] == completion, event
    return event


def scenario_callback_common() -> Json:
    recorder = Recorder("callback-common")
    runner, fixture = _callback_runner(recorder, "common")
    cwd = _workspace(recorder, "workspace")
    enabled = "enabled-%s" % uuid.uuid4().hex[:8]
    disabled = "disabled-%s" % uuid.uuid4().hex[:8]
    unavailable = "unavailable-%s" % uuid.uuid4().hex[:8]
    try:
        completed = runner.result("start", "--name", enabled, "--prompt",
                                  "Reply with exactly CALLBACK-COMMON and no other text.", cwd=cwd)
        require_completion(completed, enabled, cwd, "medium", "full")
        terminal = _require_event(fixture.origin, 0, "turn_terminal", completed)
        status = runner.result("status", "--name", enabled, cwd=cwd)
        assert status["callback"]["state"] == "enabled", status
        assert status["callback"]["last_terminal_attempt"]["state"] == "written", status

        silent = runner.result("start", "--name", disabled, "--no-callback", "--prompt",
                               "Reply with exactly CALLBACK-DISABLED and no other text.", cwd=cwd)
        require_completion(silent, disabled, cwd, "medium", "full")
        disabled_status = runner.result("status", "--name", disabled, cwd=cwd)
        assert disabled_status["callback"]["state"] == "disabled", disabled_status
        before = len(fixture.origin.frames)

        for key in ("CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN",
                    "CLAUDE_CODE_SESSION_ID", "CLAUDE_PID"):
            runner.env.pop(key, None)
        standalone = runner.result("start", "--name", unavailable, "--prompt",
                                   "Reply with exactly CALLBACK-UNAVAILABLE and no other text.", cwd=cwd)
        require_completion(standalone, unavailable, cwd, "medium", "full")
        unavailable_status = runner.result("status", "--name", unavailable, cwd=cwd)
        assert unavailable_status["callback"]["state"] == "unavailable", unavailable_status
        assert len(fixture.origin.frames) == before
        result = {"terminal_event_id": terminal["event_id"], "terminal_written": True,
                  "complete_inline_result": True, "disabled": "disabled",
                  "standalone": "unavailable", "delivery_claimed": False}
        runner.stop()
        return finish_scenario(recorder, "callback-common", result, ["AH1", "AH2", "AH6", "AH11"])
    finally:
        runner.stop(); fixture.close()


def scenario_callback_proactive() -> Json:
    recorder = Recorder("callback-proactive")
    runner, fixture = _callback_runner(recorder, "proactive")
    alternate = fixture.alternate()
    cwd = _workspace(recorder, "workspace")
    name = "proactive-%s" % uuid.uuid4().hex[:8]
    pending = None
    try:
        argv, pending = runner.start(
            "start", "--name", name, "--prompt",
            "Run `python3 -c \"import time; time.sleep(5)\"`, then reply PROACTIVE-ORIGINAL.",
            cwd=cwd)
        _wait_active(runner, name, cwd)
        proactive = runner.result("message", "--name", name, "--priority", "now",
                                  "--message", "MEASURED proactive update; continuing.", cwd=cwd)
        proactive_event = _require_event(fixture.origin, 0, "worker_message")
        assert proactive["event_id"] == proactive_event["event_id"]
        steered = runner.result("steer", "--name", name, "--prompt",
                                "Reply with exactly PROACTIVE-STEERED and finish.", cwd=cwd)
        completion_payload = runner.collect(argv, pending, timeout=120.0)
        pending = None
        completion = completion_payload["result"]
        require_completion(completion, name, cwd, "medium", "full")
        terminal = _require_event(fixture.origin, 1, "turn_terminal", completion)
        redirected = runner.result("message", "--name", name,
                                   "--cc-agent-name", "task8-alternate",
                                   "--message", "MEASURED one-send alternate.", cwd=cwd)
        alternate_event = _require_event(alternate, 0, "worker_message")
        assert redirected["event_id"] == alternate_event["event_id"]
        follow = runner.result("run", "--name", name, "--prompt",
                               "Reply with exactly PROACTIVE-RUN and no other text.", cwd=cwd)
        follow_terminal = _require_event(fixture.origin, 2, "turn_terminal", follow)
        assert len(alternate.frames) == 1
        result = {"proactive_event_id": proactive_event["event_id"],
                  "terminal_event_id": terminal["event_id"],
                  "alternate_event_id": alternate_event["event_id"],
                  "follow_terminal_event_id": follow_terminal["event_id"],
                  "steer_accepted": steered["accepted"], "origin_preserved": True}
        runner.stop()
        return finish_scenario(recorder, "callback-proactive", result, ["AH3", "AH4", "AH11"])
    finally:
        if pending is not None and pending.poll() is None:
            pending.terminate()
        runner.stop(); fixture.close()


def scenario_callback_origin_retention() -> Json:
    recorder = Recorder("callback-origin-retention")
    runner, fixture = _callback_runner(recorder, "origin")
    alternate = fixture.alternate("ambient-replacement")
    cwd = _workspace(recorder, "workspace")
    name = "origin-%s" % uuid.uuid4().hex[:8]
    try:
        first = runner.result("start", "--name", name, "--prompt",
                              "Reply with exactly ORIGIN-FIRST and no other text.", cwd=cwd)
        first_event = _require_event(fixture.origin, 0, "turn_terminal", first)
        runner.env.update({"CLAUDE_CODE_MESSAGING_SOCKET": str(alternate.path),
                           "CLAUDE_CODE_MESSAGING_TOKEN": uuid.uuid4().hex,
                           "CLAUDE_CODE_SESSION_ID": "ambient-replacement-session"})
        second = runner.result("run", "--name", name, "--prompt",
                               "Reply with exactly ORIGIN-RETAINED and no other text.", cwd=cwd)
        second_event = _require_event(fixture.origin, 1, "turn_terminal", second)
        for key in ("CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN",
                    "CLAUDE_CODE_SESSION_ID", "CLAUDE_PID", "CLAUDE_CONFIG_DIR"):
            runner.env.pop(key, None)
        third = runner.result("run", "--name", name, "--prompt",
                              "Reply with exactly ORIGIN-UNSET and no other text.", cwd=cwd)
        third_event = _require_event(fixture.origin, 2, "turn_terminal", third)
        assert alternate.frames == []
        result = {"origin_event_ids": [first_event["event_id"], second_event["event_id"],
                                        third_event["event_id"]],
                  "replacement_frame_count": 0, "persisted_origin_only": True}
        runner.stop()
        return finish_scenario(recorder, "callback-origin-retention", result, ["AH2", "AH4"])
    finally:
        runner.stop(); fixture.close()


def scenario_callback_recovery() -> Json:
    recorder = Recorder("callback-recovery")
    runner, fixture = _callback_runner(recorder, "recovery")
    cwd = _workspace(recorder, "workspace")
    timeout_name = "timeout-%s" % uuid.uuid4().hex[:8]
    interrupted_name = "interrupted-%s" % uuid.uuid4().hex[:8]
    pending = None
    try:
        payload, completed = runner.run(
            "start", "--name", timeout_name, "--timeout", "0",
            "--prompt", "Reply with exactly TIMEOUT-LATER and no other text.", cwd=cwd, check=False)
        timeout_error = assert_typed_error(payload, completed, "timeout_active")
        fixture.origin.wait(1, timeout=120.0)
        later_event = _require_event(fixture.origin, 0, "turn_terminal")
        assert later_event["payload"]["completion"]["turn"]["status"] == "completed"

        argv, pending = runner.start(
            "start", "--name", interrupted_name, "--prompt",
            "Run `python3 -c \"import time; time.sleep(30)\"`, then reply TOO-LATE.", cwd=cwd)
        _wait_active(runner, interrupted_name, cwd)
        runner.result("interrupt", "--name", interrupted_name, cwd=cwd)
        interrupted_payload = runner.collect(argv, pending, timeout=60.0)
        pending = None
        assert interrupted_payload["result"]["turn"]["status"] == "interrupted"
        interrupted_event = _require_event(fixture.origin, 1, "turn_terminal",
                                           interrupted_payload["result"])

        callback_status = runner.result("status", "--name", timeout_name, cwd=cwd)["callback"]
        event_id = callback_status["last_terminal_attempt"]["event_id"]
        before_restart = len(fixture.origin.frames)
        runner.result("daemon", "stop", cwd=cwd)
        restarted = runner.result("run", "--name", timeout_name, "--prompt",
                                  "Reply with exactly RECOVERY-RESTARTED.", cwd=cwd)
        fixture.origin.wait(before_restart + 1)
        all_event_ids = [event["event_id"] for event in fixture.origin.events()]
        assert all_event_ids.count(event_id) == 1, all_event_ids
        result = {"wait_timeout_kind": timeout_error["data"]["kind"],
                  "later_terminal_event_id": later_event["event_id"],
                  "interrupted_event_id": interrupted_event["event_id"],
                  "terminal_statuses": ["completed", "interrupted"],
                  "written_event_id": event_id, "written_replayed_after_restart": False,
                  "restart_turn_id": restarted["turn"]["turn_id"],
                  "pending_same_id_contract": "deterministic callback-store/dispatcher receipt",
                  "failed_terminal_contract": "deterministic dispatcher receipt",
                  "artifact_digest_contract": "deterministic immutable-artifact receipt"}
        runner.stop()
        return finish_scenario(recorder, "callback-recovery", result, ["AH5", "AH7", "AH10"])
    finally:
        if pending is not None and pending.poll() is None:
            pending.terminate()
        runner.stop(); fixture.close()


def scenario_callback_security() -> Json:
    recorder = Recorder("callback-security")
    runner, fixture = _callback_runner(recorder, "security")
    cwd = _workspace(recorder, "workspace")
    name = "security-%s" % uuid.uuid4().hex[:8]
    disabled = "security-disabled-%s" % uuid.uuid4().hex[:8]
    try:
        completion = runner.result(
            "start", "--name", name, "--prompt",
            "Inspect your environment without printing values. Reply exactly SCRUBBED if both "
            "CLAUDE_CODE_MESSAGING_SOCKET and CLAUDE_CODE_MESSAGING_TOKEN are absent.", cwd=cwd)
        _require_event(fixture.origin, 0, "turn_terminal", completion)
        text = "\n".join(message["text"] for message in completion["messages"])
        assert "SCRUBBED" in text and fixture.token not in json.dumps(completion)

        original = json.loads(fixture.origin_registry.read_text(encoding="utf-8"))
        stale = dict(original); stale["procStart"] = "PID-REUSED"
        fixture.origin_registry.write_text(json.dumps(stale), encoding="utf-8")
        os.chmod(fixture.origin_registry, 0o644)
        stale_payload, stale_completed = runner.run(
            "message", "--name", name, "--message", "must refuse stale", cwd=cwd, check=False)
        stale_error = assert_typed_error(stale_payload, stale_completed, "callback_target_stale")
        fixture.origin_registry.write_text(json.dumps(original), encoding="utf-8")
        os.chmod(fixture.origin_registry, 0o644)

        alternate = fixture.alternate("ambiguous-target")
        fixture._registry("ambiguous-target", "ambiguous-second", alternate.path, "ambiguous-two")
        ambiguous_payload, ambiguous_completed = runner.run(
            "message", "--name", name, "--cc-agent-name", "ambiguous-target",
            "--message", "must refuse ambiguous", cwd=cwd, check=False)
        ambiguous_error = assert_typed_error(
            ambiguous_payload, ambiguous_completed, "callback_target_ambiguous")

        huge = recorder.run_dir / "unicode-message.txt"
        huge.write_text("😀" * 600000, encoding="utf-8")
        large_payload, large_completed = runner.run(
            "message", "--name", name, "--message-file", str(huge), cwd=cwd,
            timeout=30.0, check=False)
        large_error = assert_typed_error(
            large_payload, large_completed, "callback_payload_too_large")

        runner.result("start", "--name", disabled, "--no-callback", "--prompt",
                      "Reply exactly DISABLED.", cwd=cwd)
        disabled_payload, disabled_completed = runner.run(
            "message", "--name", disabled, "--cc-agent-name", "task8-origin",
            "--message", "must refuse disabled", cwd=cwd, check=False)
        disabled_error = assert_typed_error(
            disabled_payload, disabled_completed, "callback_unavailable")
        result = {"credential_scrubbed": True, "pid_reuse_kind": stale_error["data"]["kind"],
                  "stale_kind": stale_error["data"]["kind"],
                  "ambiguous_kind": ambiguous_error["data"]["kind"],
                  "unicode_oversize_kind": large_error["data"]["kind"],
                  "disabled_kind": disabled_error["data"]["kind"],
                  "public_secret_scan": "absent"}
        runner.stop()
        return finish_scenario(recorder, "callback-security", result, ["AH8", "AH11"])
    finally:
        runner.stop(); fixture.close()


def scenario_callback_five_workers() -> Json:
    recorder = Recorder("callback-five-workers")
    runner, fixture = _callback_runner(recorder, "five")
    names = five_worker_names("callback-five-%s" % uuid.uuid4().hex[:6])
    workspaces = [_workspace(recorder, "workspace-%d" % index) for index in range(5)]
    pending = []
    try:
        for index, (name, cwd) in enumerate(zip(names, workspaces), 1):
            argv, process = runner.start(
                "start", "--name", name, "--prompt",
                "Reply with exactly CALLBACK-FIVE-%d and no other text." % index, cwd=cwd)
            pending.append((argv, process, name, cwd))
        assert len(pending) == 5 and all(process.poll() is None for _, process, _, _ in pending)
        completions = []
        for argv, process, name, cwd in pending:
            payload = runner.collect(argv, process, timeout=180.0)
            completions.append(payload["result"])
            require_completion(payload["result"], name, cwd, "medium", "full")
        pending = []
        fixture.origin.wait(5, timeout=30.0)
        events = fixture.origin.events()
        assert len(events) == 5 and {event["worker"]["name"] for event in events} == set(names)
        assert len({event["event_id"] for event in events}) == 5
        result = {"simultaneous_named_worker_count": 5, "names": names,
                  "event_ids": [event["event_id"] for event in events],
                  "all_terminal_written": True}
        runner.stop()
        return finish_scenario(recorder, "callback-five-workers", result, ["AH1", "AH3", "AH11"])
    finally:
        for argv, process, _, _ in pending:
            if process.poll() is None:
                process.terminate()
                recorder.collect(process, argv, timeout=10.0)
        runner.stop(); fixture.close()


def preflight() -> Json:
    recorder = Recorder("preflight")
    daemon = Daemon(recorder)
    cleaned = False
    try:
        codex_version = recorder.run(["codex", "--version"], timeout=15.0)
        assert codex_version.returncode == 0
        daemon.start()
        status = daemon.client("daemon", "status")
        models = daemon.client("model", "list")["models"]
        assert isinstance(models, list)
        selected = select_required_routes(models)
        result = {
            "codex_version": codex_version.stdout.strip(),
            "daemon_pid": status["daemon_pid"],
            "models": models,
            "selected": selected,
        }
        (LIVE_ROOT / "latest-preflight.json").write_text(
            json.dumps(result, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        cleanup_daemon(recorder, daemon)
        cleaned = True
        write_summary(recorder, "preflight", result)
        return result
    finally:
        if not cleaned:
            cleanup_daemon(recorder, daemon)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preflight", action="store_true", help="validate required Terra/Sol routes")
    parser.add_argument("--scenario", choices=TASK_8_SCENARIOS)
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.preflight:
        preflight()
        return 0
    scenarios = {name: globals()[function_name]
                 for name, function_name in CALLBACK_SCENARIOS.items()}
    if args.scenario is not None:
        scenarios[args.scenario]()
        return 0
    if args.scenario is None:
        preflight()
        for scenario in TASK_8_SCENARIOS:
            scenarios[scenario]()
        print(json.dumps({"status": "PASS", "scenario": "all-live-broker-checks"}))
        return 0
    raise AssertionError("unreachable scenario")


if __name__ == "__main__":
    raise SystemExit(main())
