#!/usr/bin/env python3
"""Isolated Python 3.9 UV package fixture used by Task 5 live scenarios."""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Dict, Optional, Sequence


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "skills" / "subagent-driven-development" / "scripts"
Json = Dict[str, object]


def expected_version() -> str:
    matches = re.findall(
        r'^version\s*=\s*"([^"]+)"\s*$',
        PACKAGE.joinpath("pyproject.toml").read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    assert len(matches) == 1, matches
    return matches[0]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_codex_01501(value: str) -> str:
    """Validate the exact measured version without inventing a CLI brand prefix."""
    match = re.fullmatch(r"[^\s]+\s+(0\.150\.1)", value.strip())
    assert match is not None, value
    return value.strip()


class IsolatedTool:
    """One non-editable UV tool and one machine-local service fixture."""

    def __init__(self, recorder, label: str):
        self.recorder = recorder
        self.root = (recorder.run_dir / ("fixture-" + label)).resolve()
        self.tool_dir = self.root / "uv-tools"
        self.bin_dir = self.root / "uv-bin"
        self.cache_dir = self.root / "uv-cache"
        self.home_dir = self.root / "home"
        self.state_dir = self.root / "state"
        self.temp_dir = Path(tempfile.mkdtemp(prefix="cw5-", dir="/tmp")).resolve()
        self.workspace = self.root / "workspace"
        for path in (
                self.root, self.bin_dir, self.cache_dir, self.home_dir,
                self.state_dir, self.workspace):
            path.mkdir(mode=0o700, parents=True, exist_ok=True)
            os.chmod(str(path), 0o700)
        self.owner_token = uuid.uuid4().hex
        self.owner_path = self.root / "fixture-owner.json"
        self.owner_path.write_text(json.dumps({
            "owner_token": self.owner_token,
            "owner_pid": os.getpid(),
            "expected_path": str(self.root),
        }, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(str(self.owner_path), 0o600)
        self.runtime_owner_path = self.temp_dir / "fixture-owner.json"
        self.runtime_owner_path.write_text(json.dumps({
            "owner_token": self.owner_token,
            "owner_pid": os.getpid(),
            "expected_path": str(self.temp_dir),
        }, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(str(self.runtime_owner_path), 0o600)
        self.uv = shutil.which("uv")
        assert self.uv, "BLOCKED: uv is required"
        codex_home = os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
        self.env = dict(os.environ)
        self.env.update({
            "HOME": str(self.home_dir),
            "CODEX_HOME": codex_home,
            "XDG_STATE_HOME": str(self.state_dir),
            "TMPDIR": str(self.temp_dir),
            "UV_TOOL_DIR": str(self.tool_dir),
            "UV_TOOL_BIN_DIR": str(self.bin_dir),
            "UV_CACHE_DIR": str(self.cache_dir),
            "PATH": str(self.bin_dir) + os.pathsep + os.environ.get("PATH", ""),
        })
        for key in (
                "CLAUDE_PLUGIN_ROOT", "CLAUDE_CODE_SESSION_ID",
                "CLAUDE_CODE_MESSAGING_SOCKET", "CLAUDE_CODE_MESSAGING_TOKEN",
                "CLAUDE_PID"):
            self.env.pop(key, None)
        self.service_pid = None  # type: Optional[int]

    @property
    def command(self) -> Path:
        return self.bin_dir / "codex-worker"

    @property
    def python(self) -> Path:
        return self.tool_dir / "codex-worker" / "bin" / "python"

    @property
    def durable_dir(self) -> Path:
        if sys.platform == "darwin":
            state_home = self.home_dir / "Library" / "Application Support"
        else:
            state_home = self.state_dir
        return state_home / "superdev" / "codex-worker" / "service"

    def run(self, *argv: str, cwd: Optional[Path] = None, timeout: float = 930.0,
            env: Optional[Dict[str, str]] = None, check: bool = False):
        completed = self.recorder.run(
            argv, cwd=cwd or self.workspace, env=env or self.env, timeout=timeout,
            substrate="MEASURED real UV/tool subprocess")
        if check:
            assert completed.returncode == 0, (completed.stdout, completed.stderr)
        return completed

    def install(self, source: Path = PACKAGE) -> None:
        argv = [self.uv, "tool", "install", "--reinstall", "--python", "3.9", str(source)]
        assert "--editable" not in argv
        self.run(*argv, timeout=300.0, check=True)

    def cli(self, *argv: str, cwd: Optional[Path] = None, timeout: float = 930.0,
            env: Optional[Dict[str, str]] = None, check: bool = True) -> Json:
        completed = self.run(str(self.command), *argv, cwd=cwd, timeout=timeout, env=env)
        lines = completed.stdout.splitlines()
        assert len(lines) == 1, completed.stdout
        payload = json.loads(lines[0])
        assert isinstance(payload, dict), payload
        if check:
            assert completed.returncode == 0 and "result" in payload and "error" not in payload, payload
        return payload

    def source_cli(self, *argv: str, cwd: Optional[Path] = None,
                   timeout: float = 930.0, env: Optional[Dict[str, str]] = None,
                   check: bool = True) -> Json:
        source = ROOT / "bin" / "codex-worker"
        completed = self.run(str(source), *argv, cwd=cwd, timeout=timeout, env=env)
        lines = completed.stdout.splitlines()
        assert len(lines) == 1, completed.stdout
        payload = json.loads(lines[0])
        if check:
            assert completed.returncode == 0 and "result" in payload and "error" not in payload, payload
        return payload

    def result(self, *argv: str, **kwargs) -> Json:
        return self.cli(*argv, **kwargs)["result"]  # type: ignore[index]

    def remember_service(self, status: Json) -> None:
        value = status.get("pid", status.get("daemon_pid"))
        if isinstance(value, int):
            self.service_pid = value

    def verify_package(self) -> Json:
        version = self.run(str(self.command), "--version", check=True).stdout.strip()
        py = self.run(str(self.python), "--version", check=True).stdout.strip()
        websockets = self.run(
            str(self.python), "-c",
            "import importlib.metadata as m; print(m.version('websockets'))",
            check=True).stdout.strip()
        codex = self.run("codex", "--version", check=True).stdout.strip()
        assert version == "codex-worker %s" % expected_version()
        assert py.startswith("Python 3.9."), py
        assert websockets
        codex = require_codex_01501(codex)
        resolved = shutil.which("codex-worker", path=self.env["PATH"])
        assert resolved and Path(resolved).resolve() == self.command.resolve()
        return {
            "worker_version": version,
            "python": py,
            "websockets": websockets,
            "codex": codex,
            "path_command": str(Path(resolved).resolve()),
            "package_sha256": sha256(PACKAGE / "pyproject.toml"),
        }

    def cleanup_owned_fixture(self) -> Json:
        owner = json.loads(self.owner_path.read_text(encoding="utf-8"))
        runtime_owner = json.loads(self.runtime_owner_path.read_text(encoding="utf-8"))
        token_verified = owner.get("owner_token") == self.owner_token
        token_verified = token_verified and runtime_owner.get("owner_token") == self.owner_token
        path_verified = (owner.get("expected_path") == str(self.root.resolve())
                         and runtime_owner.get("expected_path") == str(self.temp_dir))
        expected_pid = self.service_pid
        status = self.source_cli("daemon", "status", check=False)
        result = status.get("result") if isinstance(status, dict) else None
        observed_pid = (result.get("pid", result.get("daemon_pid"))
                        if isinstance(result, dict) else None)
        service_state = result.get("status") if isinstance(result, dict) else None
        service_socket = self.temp_dir / ("scw-%d-global" % os.getuid()) / "s"
        runtime_socket_present = service_socket.exists() or service_socket.is_symlink()
        pid_verified = (observed_pid == expected_pid if expected_pid is not None
                        and service_state != "stopped" else service_state == "stopped"
                        or isinstance(observed_pid, int))
        stopped = service_state == "stopped" and not runtime_socket_present
        if token_verified and path_verified and pid_verified and observed_pid is not None:
            stopped_payload = self.source_cli("daemon", "stop", check=False)
            stopped_result = stopped_payload.get("result", {})
            stopped = (isinstance(stopped_result, dict)
                       and stopped_result.get("status") == "completed")
            if stopped:
                after = self.source_cli("daemon", "status", check=False).get("result", {})
                stopped = (isinstance(after, dict) and after.get("status") == "stopped"
                           and not service_socket.exists()
                           and not service_socket.is_symlink())
        runtime_deleted = False
        if (token_verified and path_verified and pid_verified and stopped
                and self.temp_dir.parent == Path("/tmp").resolve()
                and self.temp_dir.name.startswith("cw5-")):
            shutil.rmtree(str(self.temp_dir))
            runtime_deleted = not self.temp_dir.exists()
        cleanup_outcome = {
            "owner_token": "[REDACTED]",
            "expected_pid": expected_pid,
            "observed_pid": observed_pid,
            "expected_path": str(self.root),
            "token_verified": token_verified,
            "pid_verified": pid_verified,
            "path_verified": path_verified,
            "service_stopped": stopped,
            "runtime_deleted": runtime_deleted,
            "cleanup_outcome": "verified isolated fixture retained as ignored raw evidence",
        }
        self.recorder.record("cleanup", cleanup_outcome)
        assert token_verified and path_verified and pid_verified and stopped, cleanup_outcome
        return cleanup_outcome


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--describe", action="store_true")
    args = parser.parse_args(argv)
    if args.describe:
        print(json.dumps({
            "python": "3.9", "package": str(PACKAGE),
            "codex": "codex 0.150.1", "dependency": "websockets",
            "owner": "fixture-owner.json",
        }, sort_keys=True))
        return 0
    parser.error("use live_broker_check.py --scenario preflight-package")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
