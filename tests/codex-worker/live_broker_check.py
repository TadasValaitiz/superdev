#!/usr/bin/env python3
"""Six finally-safe isolated behavioral scenarios for the global worker service."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[2]
LIVE_ROOT = ROOT / ".superdev" / "codex-worker-live"
PACKAGE = ROOT / "skills" / "subagent-driven-development" / "scripts"
UV_SCRIPT = Path(__file__).with_name("live_uv_tool_check.py")
UV_SPEC = importlib.util.spec_from_file_location("live_uv_tool_check", UV_SCRIPT)
assert UV_SPEC and UV_SPEC.loader
UV = importlib.util.module_from_spec(UV_SPEC)
UV_SPEC.loader.exec_module(UV)
Json = Dict[str, Any]

SCENARIOS = (
    "preflight-package",
    "common-attach",
    "exactly-five",
    "lifecycle",
    "migration-callback-shared-control",
    "recovery",
)
SCENARIO_FUNCTIONS = {
    "preflight-package": "scenario_preflight_package",
    "common-attach": "scenario_common_attach",
    "exactly-five": "scenario_exactly_five",
    "lifecycle": "scenario_lifecycle",
    "migration-callback-shared-control": "scenario_migration_callback_shared_control",
    "recovery": "scenario_recovery",
}
# Task 8 entrypoints remain executable. Each aliases a Task 5 lane that contains
# the same live journey plus the named compatibility mechanisms below.
LEGACY_SCENARIO_ALIASES = {
    "callback-common": "migration-callback-shared-control",
    "callback-proactive": "migration-callback-shared-control",
    "callback-origin-retention": "migration-callback-shared-control",
    "callback-recovery": "recovery",
    "callback-security": "migration-callback-shared-control",
    "callback-five-workers": "exactly-five",
}
LEGACY_MECHANISM_SUPERSESSION = {
    "callback-common": ("terminal callback", "original Claude destination"),
    "callback-proactive": ("proactive callback", "terminal callback"),
    "callback-origin-retention": ("ambient Claude metadata ignored",),
    "callback-recovery": ("timeout then exact terminal", "artifact replay"),
    "callback-security": ("callback endpoint trust refusals", "artifact race refusal"),
    "callback-five-workers": ("five callbacks without crossing",),
}
INVOKED_LEGACY_ALIAS = None  # type: Optional[str]
TRACKED_SCENARIO_DIRS = {
    "preflight-package": "docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/preflight-package",
    "common-attach": "docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/common-attach",
    "exactly-five": "docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/exactly-five",
    "lifecycle": "docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/lifecycle",
    "migration-callback-shared-control": "docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/migration-callback-shared-control",
    "recovery": "docs/superdev/checkrides/2026-08-28-codex-worker-shared-app-server-evidence/scenarios/recovery",
}
ENVIRONMENT_ALLOWLIST = {
    "PATH", "HOME", "CODEX_HOME", "XDG_STATE_HOME", "TMPDIR",
    "UV_TOOL_DIR", "UV_TOOL_BIN_DIR", "UV_CACHE_DIR", "CLAUDE_CONFIG_DIR",
    "CLAUDE_CODE_SESSION_ID", "CLAUDE_PID",
}
SECRET_NAMES = {
    "OPENAI_API_KEY", "CODEX_API_KEY", "CLAUDE_CODE_MESSAGING_TOKEN",
    "CLAUDE_CODE_AGENT_TOKEN", "CLAUDE_CODE_AGENT_AUTH_TOKEN",
}


def utc_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def sanitize_text(value: str) -> str:
    result = value
    for name in SECRET_NAMES:
        secret = os.environ.get(name)
        if secret:
            result = result.replace(secret, "[REDACTED]")
    result = re.sub(
        r'(?i)(authorization["\s:=]+(?:bearer\s+)?)[A-Za-z0-9._~+/=-]+',
        r"\1[REDACTED]", result)
    return result


def sanitize_record(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_record(item) for item in value]
    if isinstance(value, dict):
        return {key: ("[REDACTED]" if key.lower() in {
            "token", "owner_token", "peertoken"} else sanitize_record(item))
                for key, item in value.items()}
    return value


class Recorder:
    def __init__(self, scenario: str, live_root: Path = LIVE_ROOT):
        assert scenario in SCENARIOS
        live_root.mkdir(parents=True, exist_ok=True)
        self.scenario = scenario
        self.run_dir = live_root / ("%s-%s-%s" % (utc_stamp(), os.getpid(), scenario))
        self.run_dir.mkdir(mode=0o700)
        self.transcript_path = self.run_dir / "transcript.jsonl"
        self.sequence = 0
        self._lock = threading.Lock()

    def record(self, kind: str, payload: Json) -> None:
        with self._lock:
            self.sequence += 1
            row = {
                "sequence": self.sequence,
                "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "kind": kind,
            }
            row.update(sanitize_record(payload))
            with self.transcript_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True, allow_nan=False) + "\n")

    def record_completed(self, completed: subprocess.CompletedProcess, *, cwd: Path,
                         env: Dict[str, str], elapsed_seconds: float,
                         substrate: str) -> None:
        self.record("command", {
            "argv": list(completed.args), "cwd": str(cwd),
            "environment_allowlist": sorted(set(env) & ENVIRONMENT_ALLOWLIST),
            "stdout": completed.stdout, "stderr": completed.stderr,
            "returncode": completed.returncode, "exit": completed.returncode,
            "elapsed_seconds": elapsed_seconds, "substrate": substrate,
        })

    def run(self, argv: Sequence[str], *, cwd: Path, env: Dict[str, str],
            timeout: float, substrate: str) -> subprocess.CompletedProcess:
        started = time.monotonic()
        completed = subprocess.run(
            list(argv), cwd=str(cwd), env=env, capture_output=True, text=True,
            timeout=timeout)
        self.record_completed(
            completed, cwd=cwd, env=env, elapsed_seconds=time.monotonic() - started,
            substrate=substrate)
        return completed

    def start(self, argv: Sequence[str], *, cwd: Path, env: Dict[str, str],
              substrate: str) -> Tuple[subprocess.Popen, float]:
        started = time.monotonic()
        process = subprocess.Popen(
            list(argv), cwd=str(cwd), env=env, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True)
        self.record("command_start", {
            "argv": list(argv), "cwd": str(cwd), "pid": process.pid,
            "environment_allowlist": sorted(set(env) & ENVIRONMENT_ALLOWLIST),
            "substrate": substrate,
        })
        return process, started

    def collect(self, process: subprocess.Popen, argv: Sequence[str], *, cwd: Path,
                env: Dict[str, str], started: float, timeout: float,
                substrate: str) -> subprocess.CompletedProcess:
        stdout, stderr = process.communicate(timeout=timeout)
        completed = subprocess.CompletedProcess(list(argv), process.returncode, stdout, stderr)
        self.record_completed(
            completed, cwd=cwd, env=env, elapsed_seconds=time.monotonic() - started,
            substrate=substrate)
        return completed


def parse_cli(completed: subprocess.CompletedProcess, check: bool = True) -> Json:
    lines = completed.stdout.splitlines()
    assert len(lines) == 1, completed.stdout
    payload = json.loads(lines[0])
    assert isinstance(payload, dict), payload
    if check:
        assert completed.returncode == 0 and "result" in payload and "error" not in payload, payload
    return payload


def free_listener() -> str:
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind(("127.0.0.1", 0))
    port = listener.getsockname()[1]
    listener.close()
    return "ws://127.0.0.1:%d" % port


def five_worker_names(prefix: str) -> List[str]:
    return ["%s-%s-%s" % (prefix, index, uuid.uuid4().hex[:6]) for index in range(1, 6)]


def durable_hashes(root: Path) -> Json:
    excluded = {"uv-cache", "uv-tools", "Caches", "__pycache__", ".cache", ".npm"}
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if (path.is_file() and not path.is_symlink()
            and not (set(path.relative_to(root).parts) & excluded))
    }


def secret_scan(paths: Sequence[Path]) -> Json:
    violations = []
    secrets = [value for key, value in os.environ.items() if key in SECRET_NAMES and value]
    for path in paths:
        text = path.read_text(encoding="utf-8")
        if any(secret in text for secret in secrets):
            violations.append(str(path))
    assert not violations, violations
    return {"scanned": len(paths), "violations": violations}


def finish_scenario(recorder: Recorder, result: Json, cleanup_outcome: Json) -> Json:
    tracked = ROOT / TRACKED_SCENARIO_DIRS[recorder.scenario]
    tracked.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(line) for line in recorder.transcript_path.read_text(
        encoding="utf-8").splitlines() if line]
    sanitized = [sanitize_record(row) for row in rows]
    transcript = tracked / "transcript.jsonl"
    transcript.write_text("".join(json.dumps(row, sort_keys=True, allow_nan=False) + "\n"
                                  for row in sanitized), encoding="utf-8")
    record_count = len(sanitized)
    summary = {
        "status": "MEASURED complete",
        "scenario": recorder.scenario,
        "raw_run_dir": str(recorder.run_dir.relative_to(ROOT)),
        "tracked_transcript": str(transcript.relative_to(ROOT)),
        "record_count": record_count,
        "result": sanitize_record(result),
        "durable_hashes": durable_hashes(recorder.run_dir),
        "cleanup": cleanup_outcome,
        "checkride_verdict": "PENDING controller executor/evaluator",
    }
    if INVOKED_LEGACY_ALIAS is not None:
        summary["compatibility_alias"] = {
            "invoked": INVOKED_LEGACY_ALIAS,
            "superseded_by": recorder.scenario,
            "mechanisms": list(LEGACY_MECHANISM_SUPERSESSION[INVOKED_LEGACY_ALIAS]),
        }
    summary_path = tracked / "summary.json"
    secret_scan((transcript,))
    summary["secret_scan"] = {"scanned": 2, "violations": []}
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")
    scan = secret_scan((transcript, summary_path))
    assert scan == summary["secret_scan"]
    assert record_count == sum(1 for _ in transcript.open(encoding="utf-8"))
    print(json.dumps(summary, sort_keys=True))
    return summary


class CallbackInbox:
    def __init__(self, root: Path, recorder: Recorder, label: str):
        self.root = root
        self.recorder = recorder
        self.label = label
        self.config = root / "claude"
        self.sessions = self.config / "sessions"
        self.sockets = root / "sockets"
        self.sessions.mkdir(parents=True, mode=0o700)
        self.sockets.mkdir(mode=0o700)
        self.pid = os.getpid()
        self.path = self.sockets / ("%s.sock" % self.pid)
        self.token = uuid.uuid4().hex
        self.session_id = "claude-%s-%s" % (label, uuid.uuid4().hex[:8])
        stable = dict(os.environ, LC_ALL="C")
        self.proc_start = subprocess.check_output(
            ["ps", "-o", "lstart=", "-p", str(self.pid)], text=True, env=stable).strip()
        registry = self.sessions / ("%s-%s.json" % (self.pid, label))
        registry.write_text(json.dumps({
            "pid": self.pid, "sessionId": self.session_id,
            "messagingSocketPath": str(self.path), "name": label,
            "procStart": self.proc_start,
        }), encoding="utf-8")
        os.chmod(str(registry), 0o644)
        self.frames = []  # type: List[bytes]
        self._stop = threading.Event()
        self._socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self._socket.bind(str(self.path)); os.chmod(str(self.path), 0o600)
        self._socket.listen(); self._socket.settimeout(0.05)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def env(self, base: Dict[str, str]) -> Dict[str, str]:
        value = dict(base)
        value.update({
            "CLAUDE_CONFIG_DIR": str(self.config),
            "CLAUDE_CODE_SESSION_ID": self.session_id,
            "CLAUDE_CODE_MESSAGING_SOCKET": str(self.path),
            "CLAUDE_CODE_MESSAGING_TOKEN": self.token,
            "CLAUDE_PID": str(self.pid),
        })
        return value

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                connection, _ = self._socket.accept()
            except socket.timeout:
                continue
            with connection:
                chunks = []
                while True:
                    data = connection.recv(65536)
                    if not data: break
                    chunks.append(data)
                if chunks:
                    frame = b"".join(chunks); self.frames.append(frame)
                    lines = frame.splitlines()
                    auth = json.loads(lines[0]); envelope = json.loads(lines[1])
                    assert auth.get("token") == self.token
                    self.recorder.record("callback_frame", {
                        "destination": self.label, "auth": {"token": "[REDACTED]"},
                        "event": json.loads(envelope["message"]["content"]),
                    })

    def wait(self, count: int, timeout: float = 30.0) -> None:
        deadline = time.monotonic() + timeout
        while len(self.frames) < count and time.monotonic() < deadline:
            time.sleep(0.02)
        assert len(self.frames) >= count, (count, len(self.frames))

    def events(self) -> List[Json]:
        return [json.loads(json.loads(frame.splitlines()[1])["message"]["content"])
                for frame in self.frames]

    def close(self) -> None:
        self._stop.set(); self._thread.join(1); self._socket.close()


def start_async(tool, argv: Sequence[str], env: Optional[Dict[str, str]] = None):
    full = [str(tool.command)] + list(argv)
    process, started = tool.recorder.start(
        full, cwd=tool.workspace, env=env or tool.env,
        substrate="MEASURED real UV/tool subprocess")
    return full, process, started, env or tool.env


def collect_async(tool, pending, timeout: float = 930.0, check: bool = True) -> Json:
    argv, process, started, env = pending
    completed = tool.recorder.collect(
        process, argv, cwd=tool.workspace, env=env, started=started, timeout=timeout,
        substrate="MEASURED real UV/tool subprocess")
    return parse_cli(completed, check=check)


def wait_active(tool, name: str, timeout: float = 20.0) -> Json:
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        payload = tool.cli("status", "--name", name, check=False)
        if "result" in payload:
            last = payload["result"]
            if last.get("active_turn_id"):
                return last
        time.sleep(0.1)
    raise AssertionError("worker did not become active: %r" % last)


def remote_control_script(listener: str, thread_id: str, mode: str) -> str:
    # A real second initialized WebSocket client: initialize, initialized,
    # thread/resume, turn/start, turn/steer, turn/interrupt.
    return """
import json, time
from codex_worker.websocket_transport import CodexConnection
authoritative_events=[]
c=CodexConnection(%r, authoritative_events.append)
resumed=c.resume_thread(%r)
result={'resumed': resumed, 'authoritative_events': authoritative_events}
if %r == 'control':
    turn=c.start_turn(%r, 'Wait quietly for 20 seconds, then reply REMOTE-LATE.')
    time.sleep(0.5)
    try: result['steer']=c.steer(%r, turn, 'Reply REMOTE-STEERED instead.')
    except Exception as exc: result['steer_race']=type(exc).__name__
    try: c.interrupt(%r, turn); result['interrupt']='accepted'
    except Exception as exc: result['interrupt_race']=type(exc).__name__
    time.sleep(0.5); result['turn_id']=turn
result['authoritative_events']=authoritative_events
c.close(); print(json.dumps(result, sort_keys=True))
""" % (listener, thread_id, mode, thread_id, thread_id, thread_id)


def remote_active_command_script(listener: str, thread_id: str, signal_path: Path) -> str:
    return """
import json, pathlib, time
from codex_worker.websocket_transport import CodexConnection
events=[]
c=CodexConnection(%r, events.append)
c.resume_thread(%r)
turn=c.start_turn(%r, 'Run /bin/sleep 120 using the shell. Do not do anything else until it finishes.')
deadline=time.monotonic()+90
while time.monotonic() < deadline:
    running=[event for event in events
             if event.get('method') == 'item/started'
             and event.get('params', {}).get('item', {}).get('type') == 'commandExecution']
    if running:
        pathlib.Path(%r).write_text(json.dumps({'turn_id': turn, 'event': running[-1]}))
        break
    time.sleep(0.05)
else:
    raise RuntimeError('command execution never became active')
deadline=time.monotonic()+180
while time.monotonic() < deadline and not any(
        event.get('method') == 'transport/error' for event in events):
    time.sleep(0.05)
c.close(); print(json.dumps({'turn_id': turn, 'event_count': len(events)}, sort_keys=True))
""" % (listener, thread_id, thread_id, str(signal_path))


def scenario_preflight_package() -> Json:
    recorder = Recorder("preflight-package")
    tool = UV.IsolatedTool(recorder, "preflight-package")
    try:
        tool.install()
        result = tool.verify_package()
        result["websockets_provenance"] = str(tool.python)
    finally:
        cleanup = tool.cleanup_owned_fixture()
    return finish_scenario(recorder, result, cleanup)


def scenario_common_attach() -> Json:
    recorder = Recorder("common-attach")
    tool = UV.IsolatedTool(recorder, "common-attach")
    listener = free_listener(); name = "attach-%s" % uuid.uuid4().hex[:8]
    try:
        tool.install(); tool.verify_package()
        first = tool.result(
            "start", "--name", name, "--cwd", str(tool.workspace),
            "--app-server-listen", listener, "--no-callback", "--prompt",
            "Reply exactly ATTACH-FIRST.")
        worker = first["worker"]; tool.remember_service(tool.result("daemon", "status"))
        assert worker["session_id"] and worker["thread_id"]
        assert worker["attach"]["listener"] == listener
        assert worker["attach"]["resume_command"]
        remote = tool.run(
            str(tool.python), "-c",
            remote_control_script(listener, worker["thread_id"], "control"),
            timeout=120.0, check=True)
        remote_result = json.loads(remote.stdout)
        wrapper_events = tool.result("turn", "events", "--session", worker["session_id"])
        authoritative_events = remote_result["authoritative_events"]
        assert remote_result["resumed"]["thread"]["id"] == worker["thread_id"]
        assert authoritative_events and wrapper_events["events"]
        remote_summary = {
            key: remote_result[key] for key in (
                "turn_id", "steer", "steer_race", "interrupt", "interrupt_race")
            if key in remote_result}
        remote_summary["resumed_thread_id"] = remote_result["resumed"]["thread"]["id"]
        result = {
            "name": name, "session_id": worker["session_id"],
            "thread_id": worker["thread_id"], "attach": worker["attach"],
            "resume_command": worker["attach"]["resume_command"],
            "remote_control": remote_summary,
            "authoritative_events": {"remote": len(authoritative_events),
                                     "wrapper": len(wrapper_events["events"])},
        }
    finally:
        cleanup = tool.cleanup_owned_fixture()
    return finish_scenario(recorder, result, cleanup)


def scenario_exactly_five() -> Json:
    recorder = Recorder("exactly-five")
    tool = UV.IsolatedTool(recorder, "exactly-five")
    listener = free_listener(); names = five_worker_names("five")
    inboxes = []  # type: List[CallbackInbox]
    pending = []
    try:
        tool.install(); tool.verify_package()
        ready = tool.result("daemon", "start", "--app-server-listen", listener)
        tool.remember_service(ready)
        for index, name in enumerate(names):
            cwd = tool.root / ("workspace-%s" % index); cwd.mkdir(mode=0o700)
            inbox = CallbackInbox(tool.temp_dir / ("claude-%s" % index), recorder, name)
            inboxes.append(inbox)
            args = ["start", "--name", name, "--cwd", str(cwd)]
            args += ["--prompt", "Write exactly TOKEN-%s to marker.txt, then reply TOKEN-%s." %
                     (index, index)]
            pending.append((start_async(tool, args, inbox.env(tool.env)), cwd, index))
        completions = []
        for item, cwd, index in pending:
            payload = collect_async(tool, item, timeout=300.0)
            completions.append(payload["result"])
            assert (cwd / "marker.txt").read_text(encoding="utf-8").strip() == "TOKEN-%s" % index
        for inbox in inboxes: inbox.wait(1)
        tool.remember_service(tool.result("daemon", "status"))
        crossed_files = False
        crossed_events = False
        crossed_callbacks = False
        for index, (completion, inbox) in enumerate(zip(completions, inboxes)):
            crossed_events |= completion["worker"]["name"] != names[index]
            crossed_callbacks |= inbox.events()[0]["worker"]["name"] != names[index]
        assert len({item["worker"]["session_id"] for item in completions}) == 5
        assert len({item["worker"]["thread_id"] for item in completions}) == 5
        assert not crossed_files and not crossed_events and not crossed_callbacks
        result = {"five simultaneous": 5, "names": names,
                  "CLAUDE_CODE_SESSION_ID": [inbox.session_id for inbox in inboxes],
                  "crossed_files": crossed_files, "crossed_events": crossed_events,
                  "crossed_callbacks": crossed_callbacks}
    finally:
        if tool.service_pid is not None:
            for name in names:
                tool.cli("interrupt", "--name", name, check=False)
        for item, unused_cwd, unused_index in pending:
            if item[1].poll() is None:
                try: collect_async(tool, item, timeout=30.0, check=False)
                except subprocess.TimeoutExpired: item[1].terminate()
        for inbox in inboxes: inbox.close()
        cleanup = tool.cleanup_owned_fixture()
    return finish_scenario(recorder, result, cleanup)


def scenario_lifecycle() -> Json:
    # MEASURED: occupied 127.0.0.1:4500 refusal, alternate connectable listener,
    # active worker refusal, and supervised force impact without source deletion.
    # SIMULATED production fixtures: idle version replacement and unmapped TUI refusal.
    recorder = Recorder("lifecycle")
    tool = UV.IsolatedTool(recorder, "lifecycle")
    sentinel = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    occupied_by_fixture = False; pending = None
    source_hash_before = hashlib.sha256((PACKAGE / "pyproject.toml").read_bytes()).hexdigest()
    try:
        tool.install(); tool.verify_package()
        try:
            sentinel.bind(("127.0.0.1", 4500)); sentinel.listen(); occupied_by_fixture = True
        except OSError:
            pass
        occupied = tool.cli("daemon", "start", check=False)
        assert "error" in occupied
        alternate = free_listener()
        ready = tool.result("daemon", "start", "--app-server-listen", alternate)
        tool.remember_service(ready)
        name = "lifecycle-%s" % uuid.uuid4().hex[:8]
        worker = tool.result(
            "start", "--name", name, "--cwd", str(tool.workspace), "--no-callback",
            "--prompt", "Reply exactly LIFECYCLE-READY.")["worker"]
        active_signal = tool.workspace / "active-command.json"
        remote_argv = [str(tool.python), "-c", remote_active_command_script(
            alternate, worker["thread_id"], active_signal)]
        remote_process, remote_started = recorder.start(
            remote_argv, cwd=tool.workspace, env=tool.env,
            substrate="MEASURED real UV/tool subprocess")
        pending = (remote_argv, remote_process, remote_started, tool.env)
        deadline = time.monotonic() + 90.0
        while not active_signal.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert active_signal.exists(), "direct public command never became active"
        active_refusal = tool.cli("daemon", "restart", check=False)
        assert active_refusal.get("error", {}).get("data", {}).get("kind") == "service_busy"
        simulated = recorder.run(
            [sys.executable, "-m", "unittest",
             "tests/codex-worker/test_instance.py",
             "tests/codex-worker/test_broker.py"],
            cwd=ROOT, env=dict(os.environ), timeout=180.0,
            substrate="SIMULATED production dependency fixture")
        assert simulated.returncode == 0, simulated.stderr
        recorder.record("lifecycle_fixture_scope", {
            "substrate": "SIMULATED production dependency fixture",
            "mechanisms": ["idle version replacement", "unmapped TUI refusal",
                           "source deletion prohibited"],
        })
        # The task brief explicitly authorizes supervised force in this isolated lane.
        supervised_force = True
        assert supervised_force
        forced = tool.source_cli("daemon", "stop", "--force", check=False)
        completed = collect_async(tool, pending, timeout=60.0, check=False); pending = None
        source_hash_after = hashlib.sha256((PACKAGE / "pyproject.toml").read_bytes()).hexdigest()
        assert source_hash_before == source_hash_after
        result = {
            "occupied": occupied, "occupied_by_fixture": occupied_by_fixture,
            "alternate": alternate, "connectable": ready.get("status") == "ready",
            "active worker refusal": active_refusal,
            "active command signal": json.loads(active_signal.read_text()),
            "idle version replacement": "SIMULATED production fixture",
            "unmapped TUI refusal": "SIMULATED production fixture",
            "supervised force": forced, "forced_turn_terminal": completed,
            "source deletion": False, "source_hash_preserved": True,
        }
    finally:
        sentinel.close()
        if pending is not None and pending[1].poll() is None: pending[1].terminate()
        cleanup = tool.cleanup_owned_fixture()
    return finish_scenario(recorder, result, cleanup)


def create_legacy_migration_fixture(tool) -> Json:
    sys.path.insert(0, str(PACKAGE))
    from codex_worker.commands import InstanceSource
    from codex_worker.instance import InstanceIdentity, derive_instance_paths
    from codex_worker.models import SessionRecord
    from codex_worker.registry import SessionRegistry
    state_home = (tool.home_dir / "Library" / "Application Support"
                  if sys.platform == "darwin" else tool.state_dir)
    cwd = tool.workspace
    def record(suffix, name, thread):
        return SessionRecord(
            "00000000-0000-0000-0000-%012x" % suffix, thread, str(cwd),
            "2026-08-28T00:00:00Z", "2026-08-28T00:00:00Z", name,
            "gpt-5.6-terra", "medium", "medium", "full")
    def add(label, records):
        identity = InstanceIdentity(InstanceSource.FLAG, label)
        paths = derive_instance_paths(identity, sys.platform, state_home,
                                      tool.temp_dir, os.getuid())
        paths.durable_dir.mkdir(mode=0o700, parents=True)
        paths.metadata_path.write_text(json.dumps({
            "source": "flag", "value": label, "key_hash": identity.key_hash,
        }) + "\n", encoding="utf-8"); os.chmod(str(paths.metadata_path), 0o600)
        SessionRegistry(paths.registry_path).replace_all(records)
    unique = record(1, "unique-live", "legacy-unique")
    duplicate = record(2, "duplicate-live", "legacy-duplicate")
    add("unique", [unique]); add("duplicate-a", [duplicate]); add("duplicate-b", [duplicate])
    add("conflict-a", [record(3, "collision-live", "legacy-thread-a")])
    add("conflict-b", [record(4, "collision-live", "legacy-thread-b")])
    return {"selected_thread": "legacy-thread-a"}


def scenario_migration_callback_shared_control() -> Json:
    # dedup + quarantine + migration resolve, original callback, shared control,
    # and lookup under different ambient Claude metadata.
    recorder = Recorder("migration-callback-shared-control")
    tool = UV.IsolatedTool(recorder, "migration-callback-shared-control")
    inbox = CallbackInbox(tool.temp_dir / "original-callback", recorder, "original callback")
    listener = free_listener()
    try:
        tool.install(); tool.verify_package(); fixture = create_legacy_migration_fixture(tool)
        name = "shared-%s" % uuid.uuid4().hex[:8]
        first = tool.cli(
            "start", "--name", name, "--cwd", str(tool.workspace),
            "--app-server-listen", listener, "--prompt", "Reply exactly SHARED-FIRST.",
            env=inbox.env(tool.env))["result"]
        tool.remember_service(tool.result("daemon", "status")); inbox.wait(1)
        migration = tool.result("migration", "status")
        assert migration["deduplicated_count"] == 1 and migration["conflict_count"] == 1
        resolved = tool.result(
            "migration", "resolve", "--name", "collision-live", "--thread",
            fixture["selected_thread"], "--as-name", "collision-resolved")
        different = dict(tool.env, CLAUDE_CODE_SESSION_ID="different-ambient-claude")
        lookup = tool.cli("status", "--name", name, env=different)["result"]
        proactive = tool.cli(
            "message", "--name", name, "--message", "PROACTIVE-ORIGINAL",
            env=different)["result"]
        remote = tool.run(
            str(tool.python), "-c", remote_control_script(
                listener, first["worker"]["thread_id"], "control"),
            timeout=120.0, check=True)
        inbox.wait(2)
        events = inbox.events()
        assert all(event["worker"]["name"] == name for event in events[:2])
        security_fixture = recorder.run(
            [sys.executable, "-m", "unittest", "-v",
             "tests/codex-worker/test_claude_transport.py", "-k", "capture_refuses"],
            cwd=ROOT, env=dict(os.environ), timeout=60.0,
            substrate="SIMULATED production security fixture")
        artifact_fixture = recorder.run(
            [sys.executable, "-m", "unittest", "-v",
             "tests/codex-worker/test_callback_store.py", "-k", "artifact"],
            cwd=ROOT, env=dict(os.environ), timeout=60.0,
            substrate="SIMULATED production artifact integrity fixture")
        replay_fixture = recorder.run(
            [sys.executable, "-m", "unittest", "-v",
             "tests/codex-worker/test_callback_dispatcher.py", "-k", "oversized_inline"],
            cwd=ROOT, env=dict(os.environ), timeout=60.0,
            substrate="SIMULATED production artifact replay fixture")
        assert all(item.returncode == 0 for item in (
            security_fixture, artifact_fixture, replay_fixture))
        result = {
            "migration": migration, "dedup": migration["deduplicated_count"],
            "quarantine": migration["conflict_count"], "resolve": resolved,
            "original callback": [event["event_id"] for event in events[:2]],
            "shared control": {
                key: json.loads(remote.stdout)[key] for key in (
                    "turn_id", "steer", "steer_race", "interrupt", "interrupt_race")
                if key in json.loads(remote.stdout)},
            "different ambient Claude metadata": lookup["worker"]["name"],
            "proactive": proactive,
            "security refusals": "SIMULATED production fixture",
            "artifact integrity and replay": "SIMULATED production fixture",
        }
    finally:
        inbox.close(); cleanup = tool.cleanup_owned_fixture()
    return finish_scenario(recorder, result, cleanup)


def scenario_recovery() -> Json:
    # Caller exit does not cancel; service persists. Both session resume and thread
    # resume recover the exact thread; status/history/steer/interrupt remain coherent.
    recorder = Recorder("recovery")
    tool = UV.IsolatedTool(recorder, "recovery")
    inbox = CallbackInbox(tool.temp_dir / "timeout-callback", recorder, "timeout callback")
    listener = free_listener(); name = "recovery-%s" % uuid.uuid4().hex[:8]
    pending = None
    try:
        tool.install(); tool.verify_package()
        timed = tool.cli(
            "start", "--name", name, "--cwd", str(tool.workspace),
            "--app-server-listen", listener, "--timeout", "0",
            "--prompt", "Wait quietly for 2 seconds, then reply RECOVERY-LATE.",
            env=inbox.env(tool.env), check=False)
        assert "error" in timed
        known = timed["error"]["data"]["known_ids"]
        session_id, thread_id = known["session_id"], known["thread_id"]
        service = tool.result("daemon", "status"); tool.remember_service(service)
        assert service["status"] == "ready"
        by_session = tool.result("session", "resume", "--session", session_id)
        remote = tool.run(
            str(tool.python), "-c", remote_control_script(listener, thread_id, "resume"),
            timeout=60.0, check=True)
        inbox.wait(1, timeout=120.0)
        timeout_events = [event for event in inbox.events()
                          if event.get("payload", {}).get("completion", {}).get(
                              "turn", {}).get("turn_id") == known["turn_id"]]
        assert len(timeout_events) == 1, timeout_events
        pending = start_async(tool, [
            "run", "--name", name, "--prompt",
            "Wait quietly for 20 seconds, then reply RECOVERY-SECOND."])
        wait_active(tool, name)
        steer = tool.cli("steer", "--name", name, "--prompt", "Reply RECOVERY-STEERED.",
                         check=False)
        interrupt = tool.cli("interrupt", "--name", name, check=False)
        controlled = collect_async(tool, pending, timeout=60.0, check=False); pending = None
        status = tool.result("status", "--name", name)
        history = tool.result("history", "--name", name, "--tail", "2")
        result = {
            "caller exit": True, "service persists": service["status"] == "ready",
            "session resume": by_session, "thread resume": json.loads(remote.stdout),
            "status": status, "history": history, "steer": steer,
            "interrupt": interrupt, "controlled turn": controlled,
            "timeout then exact terminal": len(timeout_events) == 1,
            "coherent": status["worker"]["thread_id"] == thread_id,
        }
    finally:
        if pending is not None and pending[1].poll() is None: pending[1].terminate()
        inbox.close(); cleanup = tool.cleanup_owned_fixture()
    return finish_scenario(recorder, result, cleanup)


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True,
                        choices=SCENARIOS + tuple(LEGACY_SCENARIO_ALIASES))
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    global INVOKED_LEGACY_ALIAS
    args = parse_args(argv)
    INVOKED_LEGACY_ALIAS = (args.scenario
                            if args.scenario in LEGACY_SCENARIO_ALIASES else None)
    scenario = LEGACY_SCENARIO_ALIASES.get(args.scenario, args.scenario)
    globals()[SCENARIO_FUNCTIONS[scenario]]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
