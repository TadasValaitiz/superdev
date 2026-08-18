#!/usr/bin/env python3
"""Slow, credentialed end-to-end checks for the local Codex worker broker.

This is deliberately separate from ``test_*.py`` discovery.  Every subprocess
interaction is recorded under the git-ignored ``.superdev/codex-worker-live``
directory before an assertion interprets it.
"""
import argparse
import datetime
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple


ROOT = Path(__file__).resolve().parents[2]
CLI = ROOT / "skills" / "subagent-driven-development" / "scripts" / "codex-worker"
LIVE_ROOT = ROOT / ".superdev" / "codex-worker-live"
Json = Dict[str, Any]


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
            sys.executable, str(CLI), "--socket", str(self.socket_path),
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
            [sys.executable, str(CLI), "--socket", str(self.socket_path)] + list(args),
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
        sys.executable, str(CLI), "--socket", str(daemon.socket_path),
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
            sys.executable, str(CLI), "--socket", str(daemon.socket_path),
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
        selected = choose_two_distinct_models_and_efforts(models)
        assert len({item["model"] for item in selected}) >= 2
        assert len({item["effort"] for item in selected}) >= 2
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
    parser.add_argument("--preflight", action="store_true", help="discover the D14 model/effort pairs")
    parser.add_argument("--scenario", choices=[
        "concurrent-worktrees", "control", "observe-socket", "recovery", "approvals",
    ])
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    if args.preflight:
        preflight()
        return 0
    if args.scenario == "concurrent-worktrees":
        scenario_concurrent_worktrees()
        return 0
    if args.scenario == "control":
        scenario_control()
        return 0
    if args.scenario == "observe-socket":
        scenario_observe_socket()
        return 0
    if args.scenario == "recovery":
        scenario_recovery()
        return 0
    if args.scenario == "approvals":
        scenario_approvals()
        return 0
    if args.scenario is None:
        preflight()
        scenario_concurrent_worktrees()
        scenario_control()
        scenario_observe_socket()
        scenario_recovery()
        scenario_approvals()
        print(json.dumps({"status": "PASS", "scenario": "all-live-broker-checks"}))
        return 0
    raise AssertionError("unreachable scenario")


if __name__ == "__main__":
    raise SystemExit(main())
