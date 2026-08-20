"""Hardened transport for Claude Code's measured local messaging inbox."""
import datetime
import hashlib
import json
import os
import socket
import stat
import subprocess
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from .callback_domain import CallbackEvent
from .callback_store import CallbackBinding
from .commands import (CallbackAttemptState, CallbackAttemptView, CallbackCapture,
                       CallbackState, FACADE_FAULT_KINDS, FacadeFault,
                       FacadeFaultCode)
from .instance import _unsafe_ancestor


MAX_USER_LINE_UTF16_UNITS = 1_048_576
CALLBACK_UUID_NAMESPACE = uuid.UUID("5b290fd0-2df0-5c73-980f-04f284476f55")
_HEX32 = frozenset("0123456789abcdef")
_PROCESS_START_FORMAT = "%a %b %d %H:%M:%S %Y"


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def _process_start(pid: int) -> Optional[str]:
    stable_env = dict(os.environ)
    stable_env["LC_ALL"] = "C"
    try:
        completed = subprocess.run(
            ["ps", "-o", "lstart=", "-p", str(pid)],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, timeout=1.0, check=False, env=stable_env,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = completed.stdout.strip()
    return value if completed.returncode == 0 and value else None


def _same_process_start(registry_value: str, ps_value: Optional[str],
                        localize=None) -> bool:
    if registry_value == ps_value:
        return True
    if not isinstance(registry_value, str) or not isinstance(ps_value, str):
        return False
    try:
        registry_utc = datetime.datetime.strptime(
            registry_value.strip(), _PROCESS_START_FORMAT)
        process_local = datetime.datetime.strptime(ps_value.strip(), _PROCESS_START_FORMAT)
        if localize is None:
            localize = lambda value: value.replace(
                tzinfo=datetime.timezone.utc).astimezone().replace(tzinfo=None)
        return localize(registry_utc) == process_local
    except (TypeError, ValueError, OverflowError):
        return False


@dataclass(frozen=True)
class ClaudeTransportDeps:
    socket_factory: Callable[..., socket.socket] = field(default_factory=lambda: socket.socket)
    now: Callable[[], str] = _utc_now
    lstat: Callable[[Path], os.stat_result] = field(default_factory=lambda: os.lstat)
    getuid: Callable[[], int] = field(default_factory=lambda: os.getuid)
    process_start: Callable[[int], Optional[str]] = _process_start


def _fault(code: FacadeFaultCode, message: str, retryable: bool = False) -> FacadeFault:
    return FacadeFault(code, message, FACADE_FAULT_KINDS[code], retryable=retryable)


def _is_hex32(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 32 and set(value) <= _HEX32


class ClaudeTransport:
    """Resolve, validate, encode, and write one callback without claiming delivery."""

    def __init__(self, deps: Optional[ClaudeTransportDeps] = None):
        self.deps = deps or ClaudeTransportDeps()

    def validate_capture(self, capture: CallbackCapture) -> CallbackCapture:
        root = self._safe_config_root(capture.claude_config_dir)
        if root != capture.claude_config_dir:
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                         "Claude callback config root is not canonical")
        if capture.target_socket is None:
            return capture
        if not _pid_socket_basename_matches(capture.target_socket, capture.claude_pid):
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_STALE,
                         "Captured Claude callback socket does not match its PID")
        records = self._records(Path(root))
        matches = [record for record in records if self._matches_capture(record, capture)]
        if (len(matches) != 1
                or not _same_process_start(capture.claude_proc_start,
                                           self.deps.process_start(capture.claude_pid))):
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_STALE,
                         "Captured Claude callback target no longer matches its live identity")
        self._safe_live_socket(capture.target_socket)
        return capture

    def encode_user_line(self, binding: CallbackBinding, event: CallbackEvent) -> str:
        event_object = {
            "schema": event.schema,
            "event": event.event,
            "event_id": event.event_id,
            "emitted_at": event.emitted_at,
            "priority": event.priority,
            "worker": event.worker.to_dict(),
            "payload": event.payload,
        }
        try:
            content = json.dumps(event_object, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise _fault(FacadeFaultCode.CALLBACK_SEND_FAILED,
                         "Callback event cannot be serialized") from exc
        envelope = {
            "type": "user",
            "message": {"role": "user", "content": content},
            "uuid": str(uuid.uuid5(CALLBACK_UUID_NAMESPACE, event.event_id)),
            "msg_id": event.event_id,
            "from_mode": "bypass",
            "priority": event.priority,
        }  # type: Dict[str, Any]
        if binding.target_socket is not None:
            envelope["from"] = "uds:" + binding.target_socket
        try:
            line = json.dumps(envelope, sort_keys=True, separators=(",", ":"),
                              ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise _fault(FacadeFaultCode.CALLBACK_SEND_FAILED,
                         "Callback event cannot be serialized") from exc
        if len(line.encode("utf-16-le")) // 2 > MAX_USER_LINE_UTF16_UNITS:
            raise _fault(FacadeFaultCode.CALLBACK_PAYLOAD_TOO_LARGE,
                         "Claude callback payload exceeds the measured user-line limit")
        return line

    def send(self, binding: CallbackBinding, event: CallbackEvent,
             cc_agent_name: Optional[str]) -> CallbackAttemptView:
        if binding.state == CallbackState.DISABLED:
            raise _fault(FacadeFaultCode.CALLBACK_UNAVAILABLE,
                         "Callbacks were disabled when this worker started")
        if cc_agent_name is None:
            if binding.state != CallbackState.ENABLED:
                raise _fault(FacadeFaultCode.CALLBACK_UNAVAILABLE,
                             "No default Claude callback target is available")
            capture = CallbackCapture(binding.target_socket, binding.child_token,
                                      binding.claude_session_id, binding.claude_pid,
                                      binding.claude_proc_start, binding.claude_config_dir)
            self.validate_capture(capture)
            target, token = binding.target_socket, binding.child_token
        else:
            if binding.claude_config_dir is None:
                raise _fault(FacadeFaultCode.CALLBACK_UNAVAILABLE,
                             "No captured Claude config root is available for an override")
            root = self._safe_config_root(binding.claude_config_dir)
            target, token = self._resolve_override(Path(root), cc_agent_name)
        line = self.encode_user_line(binding, event)
        auth = json.dumps({"type": "auth", "token": token}, sort_keys=True,
                          separators=(",", ":"), allow_nan=False) + "\n"
        payload = auth.encode("utf-8") + line.encode("utf-8") + b"\n"
        client = self._open_verified_socket(target)
        try:
            client.sendall(payload)
            client.shutdown(socket.SHUT_WR)
        except (OSError, ValueError) as exc:
            raise _fault(FacadeFaultCode.CALLBACK_SEND_FAILED,
                         "Claude callback socket write failed", retryable=True) from exc
        finally:
            client.close()
        return CallbackAttemptView(event.event_id, CallbackAttemptState.WRITTEN,
                                   None, self.deps.now(), 1)

    def _safe_config_root(self, value: str) -> str:
        path = Path(value)
        if not path.is_absolute() or os.path.abspath(str(path)) != str(path):
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                         "Claude callback config root is not canonical")
        try:
            canonical = str(path.resolve(strict=True))
        except (OSError, RuntimeError) as exc:
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                         "Claude callback config root is unavailable") from exc
        if canonical != str(path):
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                         "Claude callback config root is not canonical")
        self._safe_directory(path, exact_mode=None)
        sessions = path / "sessions"
        self._safe_directory(sessions, exact_mode=0o700)
        return canonical

    def _safe_directory(self, path: Path, exact_mode: Optional[int]) -> None:
        try:
            metadata = self.deps.lstat(path)
        except OSError as exc:
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                         "Claude callback directory is unavailable") from exc
        mode = stat.S_IMODE(metadata.st_mode)
        if (not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != self.deps.getuid()
                or mode & 0o022 or (exact_mode is not None and mode != exact_mode)
                or _unsafe_ancestor(path) is not None):
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                         "Claude callback directory is unsafe")

    def _safe_file(self, path: Path, mode: int) -> bytes:
        try:
            before = self.deps.lstat(path)
            if (not stat.S_ISREG(before.st_mode) or before.st_uid != self.deps.getuid()
                    or stat.S_IMODE(before.st_mode) != mode
                    or _unsafe_ancestor(path.parent) is not None):
                raise OSError("unsafe metadata")
            data = path.read_bytes()
            after = self.deps.lstat(path)
            if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                raise OSError("file identity changed")
            return data
        except OSError as exc:
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                         "Claude callback metadata file is unsafe") from exc

    def _records(self, root: Path) -> List[Dict[str, Any]]:
        records = []  # type: List[Dict[str, Any]]
        try:
            paths = sorted((root / "sessions").glob("*.json"))
        except OSError as exc:
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                         "Claude callback registry cannot be scanned") from exc
        for path in paths:
            raw = self._safe_file(path, 0o644)
            try:
                record = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                             "Claude callback registry contains malformed JSON") from exc
            if (isinstance(record, dict)
                    and record.get("messagingSocketPath") is None
                    and record.get("kind") == "interactive"
                    and record.get("status") == "idle"
                    and type(record.get("pid")) is int and record["pid"] > 0
                    and all(isinstance(record.get(key), str) and record[key]
                            for key in ("sessionId", "procStart"))):
                continue
            required = {"pid", "sessionId", "messagingSocketPath", "procStart"}
            if (not isinstance(record, dict) or not required <= set(record)
                    or type(record["pid"]) is not int or record["pid"] <= 0
                    or not all(isinstance(record[key], str) and record[key]
                               for key in ("sessionId", "messagingSocketPath", "procStart"))
                    or not Path(record["messagingSocketPath"]).is_absolute()
                    or not _pid_socket_basename_matches(record["messagingSocketPath"], record["pid"])
                    or ("name" in record and record["name"] is not None
                        and (not isinstance(record["name"], str) or not record["name"]))):
                raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                             "Claude callback registry contains a malformed record")
            records.append(record)
        return records

    @staticmethod
    def _matches_capture(record: Dict[str, Any], capture: CallbackCapture) -> bool:
        return (record["sessionId"] == capture.claude_session_id
                and record["pid"] == capture.claude_pid
                and record["procStart"] == capture.claude_proc_start
                and record["messagingSocketPath"] == capture.target_socket)

    def _safe_live_socket(self, value: str) -> None:
        probe = self._open_verified_socket(value)
        try:
            probe.shutdown(socket.SHUT_WR)
        finally:
            probe.close()

    def _socket_metadata(self, path: Path) -> os.stat_result:
        path = Path(path)
        try:
            metadata = self.deps.lstat(path)
        except OSError as exc:
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_STALE,
                         "Claude callback socket is unavailable") from exc
        if (not path.is_absolute() or stat.S_IMODE(metadata.st_mode) != 0o600
                or not stat.S_ISSOCK(metadata.st_mode)
                or metadata.st_uid != self.deps.getuid()
                or _unsafe_ancestor(path.parent) is not None):
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                         "Claude callback socket is unsafe")
        return metadata

    def _open_verified_socket(self, value: str) -> socket.socket:
        path = Path(value)
        before = self._socket_metadata(path)
        client = self.deps.socket_factory(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            client.settimeout(5.0)
            client.connect(str(path))
            after = self._socket_metadata(path)
            if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
                raise _fault(FacadeFaultCode.CALLBACK_TARGET_STALE,
                             "Claude callback socket identity changed during connect")
        except OSError as exc:
            client.close()
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_STALE,
                         "Claude callback socket is not live") from exc
        except FacadeFault:
            client.close()
            raise
        return client

    def _resolve_override(self, root: Path, name: str) -> Tuple[str, str]:
        named = [record for record in self._records(root) if record.get("name") == name]
        live = []  # type: List[Dict[str, Any]]
        for record in named:
            if not _same_process_start(record["procStart"],
                                       self.deps.process_start(record["pid"])):
                continue
            try:
                self._safe_live_socket(record["messagingSocketPath"])
            except FacadeFault as exc:
                if exc.code == FacadeFaultCode.CALLBACK_TARGET_STALE:
                    continue
                raise
            live.append(record)
        if not live:
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_NOT_FOUND,
                         "Named live Claude callback target was not found")
        if len(live) != 1:
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_AMBIGUOUS,
                         "Named live Claude callback target is ambiguous")
        record = live[0]
        target = record["messagingSocketPath"]
        digest = hashlib.sha256(os.path.abspath(target).encode("utf-8")).hexdigest()
        key_path = root / "sessions" / ("%s.%s.key" % (record["pid"], digest))
        raw = self._safe_file(key_path, 0o600)
        try:
            key = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                         "Claude callback peer key is malformed") from exc
        if (not isinstance(key, dict) or not _is_hex32(key.get("peerToken"))
                or key.get("procStart") != record["procStart"]):
            raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                         "Claude callback peer key does not match the target")
        return target, key["peerToken"]


def _pid_socket_basename_matches(socket_path: str, pid: int) -> bool:
    return (isinstance(socket_path, str) and type(pid) is int and pid > 0
            and Path(socket_path).name == "%s.sock" % pid)


def capture_from_env(env: Mapping[str, str]) -> Optional[CallbackCapture]:
    """Capture a live ambient parent route, or a safe root-only resolver snapshot."""
    explicit_root = env.get("CLAUDE_CONFIG_DIR")
    raw_root = explicit_root or os.path.expanduser("~/.claude")
    transport = ClaudeTransport()
    try:
        root = transport._safe_config_root(raw_root)
    except FacadeFault:
        if not explicit_root:
            path = Path(raw_root)
            if not path.exists() and not path.is_symlink():
                return None
        raise
    values = (env.get("CLAUDE_CODE_MESSAGING_SOCKET"),
              env.get("CLAUDE_CODE_MESSAGING_TOKEN"),
              env.get("CLAUDE_CODE_SESSION_ID"), env.get("CLAUDE_PID"))
    root_only = CallbackCapture(None, None, None, None, None, root)
    if not all(values):
        return root_only
    target, token, session_id, raw_pid = values
    try:
        pid = int(raw_pid)
    except (TypeError, ValueError):
        raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                     "Ambient Claude PID is malformed")
    if pid <= 0 or not _is_hex32(token) or not Path(target).is_absolute():
        raise _fault(FacadeFaultCode.CALLBACK_TARGET_UNSAFE,
                     "Ambient Claude callback credentials are malformed")
    records = transport._records(Path(root))
    matches = [record for record in records
               if record["sessionId"] == session_id and record["pid"] == pid
               and record["messagingSocketPath"] == target]
    if not matches:
        return root_only
    if len(matches) != 1:
        raise _fault(FacadeFaultCode.CALLBACK_TARGET_AMBIGUOUS,
                     "Ambient Claude callback identity is ambiguous")
    capture = CallbackCapture(target, token, session_id, pid, matches[0]["procStart"], root)
    return transport.validate_capture(capture)
