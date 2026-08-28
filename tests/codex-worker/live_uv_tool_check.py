#!/usr/bin/env python3
"""Isolated slow checks for the packaged UV-owned Codex worker command.

Each invocation runs exactly one scenario and writes a sanitized JSONL transcript plus
summary beneath the repository's ignored ``.superdev/codex-worker-live`` directory.
"""
import argparse
import datetime
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "skills" / "subagent-driven-development" / "scripts"
PREFLIGHT = PACKAGE / "install-codex-worker"
LIVE_ROOT = ROOT / ".superdev" / "codex-worker-live"
EXTERNAL_REPOSITORY = Path("/Users/tadas/Projects/ai-ethics/ai-trading-calibration")
SCENARIOS = (
    "package-independence",
    "preflight-recovery",
    "durable-reinstall",
    "external-status-worker",
)
Json = Dict[str, Any]


def utc_stamp() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")


def sanitize_text(value: str) -> str:
    sanitized = value
    secret_names = (
        "OPENAI_API_KEY", "CODEX_API_KEY", "CLAUDE_CODE_AGENT_TOKEN",
        "CLAUDE_CODE_AGENT_AUTH_TOKEN",
    )
    for name in secret_names:
        secret = os.environ.get(name)
        if secret:
            sanitized = sanitized.replace(secret, "[REDACTED]")
    sanitized = re.sub(
        r'(?i)(authorization["\s:=]+(?:bearer\s+)?)[A-Za-z0-9._~+/=-]+',
        r"\1[REDACTED]",
        sanitized,
    )
    return sanitized


class Recorder:
    def __init__(self, scenario: str):
        LIVE_ROOT.mkdir(parents=True, exist_ok=True)
        self.run_dir = LIVE_ROOT / ("%s-%s-%s" % (utc_stamp(), os.getpid(), scenario))
        self.run_dir.mkdir(mode=0o700)
        self.transcript = self.run_dir / "transcript.jsonl"
        self.sequence = 0

    def record(self, kind: str, payload: Json) -> None:
        self.sequence += 1
        event = {
            "sequence": self.sequence,
            "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "kind": kind,
        }
        event.update(payload)
        with self.transcript.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True, allow_nan=False) + "\n")

    def run(self, argv: Sequence[str], *, cwd: Optional[Path] = None,
            env: Optional[Dict[str, str]] = None, timeout: float = 180.0,
            substrate: str = "MEASURED real subprocess") -> subprocess.CompletedProcess:
        started = time.monotonic()
        completed = subprocess.run(
            list(argv), cwd=str(cwd) if cwd is not None else None, env=env,
            capture_output=True, text=True, timeout=timeout,
        )
        self.record("command", {
            "argv": list(argv),
            "cwd": str(cwd) if cwd is not None else None,
            "returncode": completed.returncode,
            "stdout": sanitize_text(completed.stdout),
            "stderr": sanitize_text(completed.stderr),
            "elapsed_seconds": time.monotonic() - started,
            "substrate": substrate,
        })
        return completed

    def finish(self, result: Json) -> Json:
        summary = {
            "status": "PASS",
            "evidence_tier": "MEASURED unless a row explicitly says SIMULATED fixture",
            "transcript": str(self.transcript),
            "result": result,
        }
        (self.run_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        print(json.dumps({"status": "PASS", "run_dir": str(self.run_dir), "result": result},
                         sort_keys=True))
        return summary


class IsolatedTool:
    def __init__(self, recorder: Recorder, label: str):
        self.recorder = recorder
        # macOS caps AF_UNIX paths near 104 bytes; managed socket paths include a hash.
        self.temporary = tempfile.TemporaryDirectory(prefix="cw-%s-" % label, dir="/tmp")
        self.root = Path(self.temporary.name)
        self.tool_dir = self.root / "uv-tools"
        self.bin_dir = self.root / "uv-bin"
        self.cache_dir = self.root / "uv-cache"
        self.state_dir = self.root / "state"
        self.runtime_dir = self.root / "runtime"
        self.home_dir = self.root / "home"
        for directory in (
                self.bin_dir, self.cache_dir, self.state_dir, self.runtime_dir, self.home_dir):
            directory.mkdir(mode=0o700)
        self.env = os.environ.copy()
        codex_home = os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))
        self.env.update({
            "HOME": str(self.home_dir),
            "CODEX_HOME": codex_home,
            "UV_TOOL_DIR": str(self.tool_dir),
            "UV_TOOL_BIN_DIR": str(self.bin_dir),
            "UV_CACHE_DIR": str(self.cache_dir),
            "XDG_STATE_HOME": str(self.state_dir),
            "TMPDIR": str(self.runtime_dir),
            "PATH": str(self.bin_dir) + os.pathsep + os.environ.get("PATH", ""),
        })
        self.env.pop("CLAUDE_PLUGIN_ROOT", None)
        self.uv = shutil.which("uv")
        assert self.uv is not None, "BLOCKED: uv is required for live UV tool checks"

    @property
    def command(self) -> Path:
        return self.bin_dir / "codex-worker"

    @property
    def durable_root(self) -> Path:
        if sys.platform == "darwin":
            return self.home_dir / "Library" / "Application Support"
        return self.state_dir

    def close(self) -> None:
        for index, log_path in enumerate(self.home_dir.rglob("daemon.log"), start=1):
            evidence = self.recorder.run_dir / ("raw-daemon-%s.log" % index)
            shutil.copy2(log_path, evidence)
            evidence.chmod(0o600)
            self.recorder.record("raw_evidence", {
                "path": str(evidence),
                "kind_label": "ignored raw daemon log; may contain provider diagnostics",
            })
        self.temporary.cleanup()

    def run(self, *argv: str, cwd: Optional[Path] = None, timeout: float = 180.0,
            env: Optional[Dict[str, str]] = None,
            substrate: str = "MEASURED real UV/tool subprocess") -> subprocess.CompletedProcess:
        return self.recorder.run(argv, cwd=cwd, env=env or self.env, timeout=timeout,
                                 substrate=substrate)

    def install(self, source: Path, python39: bool = False) -> subprocess.CompletedProcess:
        argv = [self.uv, "tool", "install"]
        if python39:
            argv.extend(["--python", "3.9"])
        argv.extend(["--reinstall", str(source)])
        assert "--editable" not in argv
        completed = self.run(*argv, timeout=300.0)
        assert completed.returncode == 0, completed.stderr
        return completed

    def cli(self, *argv: str, cwd: Optional[Path] = None, timeout: float = 930.0,
            env: Optional[Dict[str, str]] = None) -> Json:
        completed = self.run(str(self.command), *argv, cwd=cwd, timeout=timeout, env=env)
        assert len(completed.stdout.splitlines()) == 1, completed
        payload = json.loads(completed.stdout)
        assert isinstance(payload, dict), payload
        if completed.returncode != 0 or "error" in payload:
            raise AssertionError(payload)
        return payload["result"]

    def stop(self, instance: str) -> None:
        completed = self.run(str(self.command), "--instance", instance, "daemon", "stop")
        if completed.returncode not in (0, 3):
            raise AssertionError(completed)


def expected_version() -> str:
    matches = re.findall(
        r'^version\s*=\s*"([^"]+)"\s*$',
        PACKAGE.joinpath("pyproject.toml").read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    assert len(matches) == 1, matches
    return matches[0]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command_provenance(tool: IsolatedTool) -> Json:
    resolved = shutil.which("codex-worker", path=tool.env["PATH"])
    assert resolved is not None
    assert Path(resolved).resolve() == tool.command.resolve()
    listed = tool.run(tool.uv, "tool", "list", "--show-paths")
    assert listed.returncode == 0, listed.stderr
    assert "codex-worker" in listed.stdout and str(tool.tool_dir) in listed.stdout
    return {
        "path_command": str(Path(resolved).resolve()),
        "uv_bin_command": str(tool.command.resolve()),
        "uv_tool_dir": str(tool.tool_dir.resolve()),
        "uv_list": sanitize_text(listed.stdout),
    }


def copy_plugin_fixture(destination: Path) -> Path:
    plugin = destination / "plugin"
    shutil.copytree(
        ROOT / "skills" / "subagent-driven-development",
        plugin / "skills" / "subagent-driven-development",
    )
    manifest = plugin / ".claude-plugin" / "plugin.json"
    manifest.parent.mkdir(parents=True)
    shutil.copy2(ROOT / ".claude-plugin" / "plugin.json", manifest)
    return plugin


def parse_refusal(completed: subprocess.CompletedProcess, reason: str) -> Json:
    assert completed.returncode != 0, completed
    assert len(completed.stdout.splitlines()) == 1, completed.stdout
    payload = json.loads(completed.stdout)
    data = payload["error"]["data"]
    assert data["kind"] == "daemon_start_failed", data
    assert data["details"]["reason"] == reason, data
    assert "Traceback" not in completed.stderr
    return payload


def scenario_package_independence() -> Json:
    recorder = Recorder("package-independence")
    tool = IsolatedTool(recorder, "package")
    try:
        source = tool.root / "source-copy"
        shutil.copytree(PACKAGE, source)
        install = tool.install(source, python39=True)
        assert "--editable" not in " ".join(install.args)
        provenance = command_provenance(tool)
        source_away = tool.root / "source-away"
        source.rename(source_away)
        assert not source.exists() and source_away.exists()

        executable = tool.command.resolve()
        first_line = executable.read_text(encoding="utf-8").splitlines()[0]
        assert first_line.startswith("#!"), first_line
        interpreter = Path(first_line[2:])
        probe = tool.run(
            str(interpreter), "-c",
            "import json,sys,codex_worker; print(json.dumps({"
            "'python':[sys.version_info.major,sys.version_info.minor],"
            "'executable':sys.executable,'module':codex_worker.__file__}))",
            cwd=tool.root,
        )
        assert probe.returncode == 0, probe.stderr
        imported = json.loads(probe.stdout)
        assert imported["python"] == [3, 9], imported
        assert str(source_away) not in imported["module"], imported
        assert str(tool.tool_dir.resolve()) in str(Path(imported["module"]).resolve()), imported
        version = tool.run(str(tool.command), "--version", cwd=tool.root)
        assert version.returncode == 0 and version.stderr == ""
        assert version.stdout == "codex-worker %s\n" % expected_version()
        return recorder.finish({
            "source_moved_to": str(source_away),
            "installed_import": imported,
            "version_stdout": version.stdout,
            "provenance": provenance,
            "python_lane": "MEASURED Python 3.9",
        })
    finally:
        tool.close()


def scenario_preflight_recovery() -> Json:
    recorder = Recorder("preflight-recovery")
    tool = IsolatedTool(recorder, "recovery")
    try:
        plugin = copy_plugin_fixture(tool.root)
        installer = plugin / "skills" / "subagent-driven-development" / "scripts" / "install-codex-worker"
        absent = tool.run(str(installer), cwd=tool.root)
        assert absent.returncode == 0, absent.stderr
        provenance = command_provenance(tool)

        tool.command.write_text(
            "#!/bin/sh\nprintf 'codex-worker 0.0.1\\n'\n",
            encoding="utf-8",
        )
        tool.command.chmod(0o755)
        mismatch = tool.run(str(installer), cwd=tool.root)
        assert mismatch.returncode == 0, mismatch.stderr
        assert tool.run(str(tool.command), "--version").stdout == (
            "codex-worker %s\n" % expected_version()
        )

        shadow_bin = tool.root / "shadow-bin"
        shadow_bin.mkdir()
        shadow = shadow_bin / "codex-worker"
        shadow.write_text("#!/bin/sh\nprintf 'foreign shadow\\n'\n", encoding="utf-8")
        shadow.chmod(0o755)
        shadow_before = digest(shadow)
        shadow_env = tool.env.copy()
        shadow_env["PATH"] = str(shadow_bin) + os.pathsep + tool.env["PATH"]
        shadowed = tool.run(str(installer), cwd=tool.root, env=shadow_env)
        assert shadowed.returncode != 0 and "PATH shadowing" in shadowed.stderr
        assert digest(shadow) == shadow_before

        tool.command.write_text(
            "#!/bin/sh\nprintf 'codex-worker 0.0.2\\n'\n",
            encoding="utf-8",
        )
        tool.command.chmod(0o755)
        command_before = digest(tool.command)
        sentinel = tool.tool_dir / "durable-sentinel"
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_text("preserve\n", encoding="utf-8")
        fake_bin = tool.root / "fake-uv-bin"
        fake_bin.mkdir()
        fake_uv = fake_bin / "uv"
        fake_uv.write_text(
            "#!/bin/sh\n"
            "if [ \"$1 $2 $3\" = \"tool dir --bin\" ]; then exec \"$REAL_UV\" \"$@\"; fi\n"
            "if [ \"$1 $2\" = \"tool install\" ]; then echo forced-install-failure >&2; exit 47; fi\n"
            "exec \"$REAL_UV\" \"$@\"\n",
            encoding="utf-8",
        )
        fake_uv.chmod(0o755)
        failure_env = tool.env.copy()
        failure_env["REAL_UV"] = tool.uv
        failure_env["PATH"] = str(fake_bin) + os.pathsep + tool.env["PATH"]
        failed = tool.run(
            str(installer), cwd=tool.root, env=failure_env,
            substrate="SIMULATED forced UV install failure over MEASURED isolated tool state",
        )
        assert failed.returncode != 0 and "47" in failed.stderr
        assert digest(tool.command) == command_before and sentinel.read_text() == "preserve\n"

        tool.install(PACKAGE)
        no_codex_env = tool.env.copy()
        no_codex_env["PATH"] = os.pathsep.join((str(tool.bin_dir), "/usr/bin", "/bin"))
        absent_codex = tool.run(
            str(tool.command), "--instance", "absent-external-codex", "daemon", "start",
            env=no_codex_env,
        )
        refusal = parse_refusal(absent_codex, "codex_not_found")
        return recorder.finish({
            "absent_preflight": "MEASURED real UV install",
            "mismatch_repair": "MEASURED real UV reinstall",
            "shadow_refusal": sanitize_text(shadowed.stderr),
            "install_failure": "SIMULATED exit 47; prior bytes preserved",
            "absent_codex": refusal["error"]["data"]["details"],
            "provenance": provenance,
        })
    finally:
        tool.close()


def state_files(state_dir: Path) -> Dict[str, str]:
    return {
        str(path.relative_to(state_dir)): digest(path)
        for path in sorted(state_dir.rglob("*")) if path.is_file()
    }


def completion_worker(result: Json, name: str) -> Json:
    assert set(result) == {"worker", "turn", "messages", "structured_output", "metrics", "recovery"}
    assert result["worker"]["name"] == name
    assert result["turn"]["status"] == "completed", result
    return result["worker"]


def scenario_durable_reinstall() -> Json:
    recorder = Recorder("durable-reinstall")
    tool = IsolatedTool(recorder, "durable")
    instance = "durable-reinstall"
    name = "durable-reinstall-probe"
    try:
        tool.install(PACKAGE)
        provenance = command_provenance(tool)
        started = tool.cli(
            "--instance", instance, "start", "--name", name, "--read-only",
            "--no-callback", "--prompt", "Reply exactly: durable mapping created.",
            cwd=tool.root,
        )
        worker = completion_worker(started, name)
        tool.stop(instance)
        before_reinstall = state_files(tool.durable_root)
        assert before_reinstall, "named durable state was not written"
        tool.install(PACKAGE)
        after_reinstall = state_files(tool.durable_root)
        assert before_reinstall == after_reinstall, "UV reinstall mutated durable worker state"
        continued = tool.cli(
            "--instance", instance, "run", "--name", name,
            "--prompt", "Reply exactly: durable mapping preserved.",
            cwd=tool.root,
        )
        continued_worker = completion_worker(continued, name)
        assert continued_worker["session_id"] == worker["session_id"], continued_worker
        assert continued_worker["thread_id"] == worker["thread_id"], continued_worker
        observed = tool.cli("--instance", instance, "status", "--name", name)
        assert observed["worker"]["session_id"] == worker["session_id"], observed
        assert observed["worker"]["thread_id"] == worker["thread_id"], observed
        return recorder.finish({
            "worker": worker,
            "continued_worker": continued_worker,
            "observed_worker": observed["worker"],
            "durable_files_unchanged_across_reinstall": True,
            "durable_file_count": len(before_reinstall),
            "provenance": provenance,
        })
    finally:
        if tool.command.exists():
            tool.stop(instance)
        tool.close()


def git_status(repo: Path, recorder: Recorder, env: Dict[str, str]) -> Json:
    def git(*args: str) -> subprocess.CompletedProcess:
        return recorder.run(("git", "-C", str(repo)) + args, cwd=repo, env=env)

    porcelain = git("status", "--porcelain=v1", "--branch")
    assert porcelain.returncode == 0
    branch = git("branch", "--show-current")
    staged = git("diff", "--cached", "--quiet")
    unstaged = git("diff", "--quiet")
    untracked = git("ls-files", "--others", "--exclude-standard")
    assert branch.returncode == 0 and staged.returncode in (0, 1)
    assert unstaged.returncode in (0, 1) and untracked.returncode == 0
    untracked_paths = [line for line in untracked.stdout.splitlines() if line]
    result = {
        "raw": porcelain.stdout,
        "branch": branch.stdout.strip(),
        "staged": staged.returncode == 1,
        "unstaged": unstaged.returncode == 1,
        "untracked": untracked_paths,
    }
    result["clean"] = not (result["staged"] or result["unstaged"] or result["untracked"])
    return result


def worker_names(state_dir: Path) -> List[str]:
    names = []  # type: List[str]
    for registry in state_dir.rglob("registry.json"):
        data = json.loads(registry.read_text(encoding="utf-8"))
        records = data.get("records", data.get("sessions", []))
        if isinstance(records, dict):
            records = list(records.values())
        if isinstance(records, list):
            names.extend(
                record["name"] for record in records
                if isinstance(record, dict) and isinstance(record.get("name"), str)
            )
    return names


def scenario_external_status_worker() -> Json:
    recorder = Recorder("external-status-worker")
    tool = IsolatedTool(recorder, "external")
    instance = "uv-global-install"
    name = "status-checker-abc"
    assert EXTERNAL_REPOSITORY.is_dir(), EXTERNAL_REPOSITORY
    try:
        tool.install(PACKAGE)
        provenance = command_provenance(tool)
        before_status = git_status(EXTERNAL_REPOSITORY, recorder, tool.env)
        schema = tool.root / "status-schema.json"
        schema.write_text(json.dumps({
            "type": "object",
            "properties": {
                "branch": {"type": "string"},
                "staged": {"type": "boolean"},
                "unstaged": {"type": "boolean"},
                "untracked": {"type": "array", "items": {"type": "string"}},
                "clean": {"type": "boolean"},
            },
            "required": ["branch", "staged", "unstaged", "untracked", "clean"],
            "additionalProperties": False,
        }), encoding="utf-8")
        prompt = (
            "Read the current Git status without modifying anything. Return branch, whether "
            "staged and unstaged changes exist, the exact sorted untracked paths, and clean."
        )
        started = tool.cli(
            "--instance", instance, "start", "--name", name, "--read-only",
            "--no-callback", "--output-schema", str(schema), "--prompt", prompt,
            cwd=EXTERNAL_REPOSITORY,
        )
        worker = completion_worker(started, name)
        structured = started["structured_output"]
        expected = {key: before_status[key] for key in (
            "branch", "staged", "unstaged", "untracked", "clean",
        )}
        assert structured == expected, {"reported": structured, "measured": expected}
        names = worker_names(tool.durable_root)
        assert names == [name], "exactly one worker name must be status-checker-abc: %r" % names
        after_status = git_status(EXTERNAL_REPOSITORY, recorder, tool.env)
        assert before_status == after_status
        return recorder.finish({
            "instance": instance,
            "worker": worker,
            "structured_output": structured,
            "exactly_one_worker": names,
            "external_cwd": str(EXTERNAL_REPOSITORY),
            "before_status": before_status,
            "after_status": after_status,
            "repository_unchanged": before_status == after_status,
            "provenance": provenance,
        })
    finally:
        if tool.command.exists():
            tool.stop(instance)
        tool.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", required=True, choices=SCENARIOS)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    scenario = build_parser().parse_args(argv).scenario
    implementations = {
        "package-independence": scenario_package_independence,
        "preflight-recovery": scenario_preflight_recovery,
        "durable-reinstall": scenario_durable_reinstall,
        "external-status-worker": scenario_external_status_worker,
    }
    implementations[scenario]()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
