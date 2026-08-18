"""Command-line entrypoint for the local Codex worker daemon/client."""
import argparse
import json
import math
import os
import signal
import sys
import tempfile
from pathlib import Path
from typing import Any, List, Optional

from .app_server import CodexAppServer
from .broker import WorkerBroker
from .models import JsonObject, RpcFault, rpc_response
from .registry import SessionRegistry
from .rpc import RpcServer, SocketInUse, SocketPathUnsafe, daemon_unavailable_fault, rpc_call
from .runtime import RuntimeStore


DOCUMENTED_CLIENT_METHODS = {
    "daemon/status",
    "daemon/shutdown",
    "model/list",
    "session/start",
    "session/resume",
    "session/list",
    "session/show",
    "turn/start",
    "turn/status",
    "turn/wait",
    "turn/events",
    "turn/steer",
    "turn/interrupt",
}


def default_socket_path() -> str:
    configured = os.environ.get("SUPERDEV_CODEX_WORKER_SOCKET")
    if configured:
        return configured
    uid = getattr(os, "getuid", lambda: 0)()
    return str(Path(tempfile.gettempdir()) / ("superdev-codex-worker-%s.sock" % uid))


def default_state_path() -> str:
    configured = os.environ.get("SUPERDEV_CODEX_WORKER_STATE")
    if configured:
        return configured
    if sys.platform == "darwin":
        root = Path.home() / "Library" / "Application Support" / "superdev" / "codex-worker"
    else:
        root = Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))
        root = root / "superdev" / "codex-worker"
    return str(root / "sessions.json")


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def _nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return parsed


def _event_limit(value: str) -> int:
    parsed = _positive_int(value)
    if parsed > 1000:
        raise argparse.ArgumentTypeError("must be <= 1000")
    return parsed


def _nonnegative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0 or not math.isfinite(parsed):
        raise argparse.ArgumentTypeError("must be a finite value >= 0")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex-worker",
        description="Local Unix-socket broker for durable Codex worker sessions.",
    )
    parser.add_argument("--socket", default=default_socket_path(),
                        help="Unix socket path (default: SUPERDEV_CODEX_WORKER_SOCKET or user temp path)")
    parser.add_argument("--pretty", action="store_true",
                        help="Pretty-print JSON responses for client commands")

    families = parser.add_subparsers(dest="family", required=True)

    daemon = families.add_parser("daemon", help="broker lifecycle")
    daemon_sub = daemon.add_subparsers(dest="action", required=True)
    serve = daemon_sub.add_parser("serve", help="run the worker daemon in the foreground")
    serve.set_defaults(method=None)
    serve.add_argument("--state", default=default_state_path(),
                       help="session registry path (default: SUPERDEV_CODEX_WORKER_STATE or user state dir)")
    serve.add_argument("--codex-bin", default="codex",
                       help="installed Codex CLI executable path")
    serve.add_argument("--event-limit", type=_positive_int, default=1000,
                       help="per-session in-memory event retention limit")
    daemon_sub.add_parser("status", help="read daemon health").set_defaults(method="daemon/status")
    daemon_sub.add_parser("shutdown", help="gracefully stop the daemon").set_defaults(method="daemon/shutdown")

    model = families.add_parser("model", help="live Codex model discovery")
    model_sub = model.add_subparsers(dest="action", required=True)
    model_sub.add_parser("list", help="list discovered models and reasoning efforts").set_defaults(method="model/list")

    session = families.add_parser("session", help="durable conversation identity")
    session_sub = session.add_subparsers(dest="action", required=True)
    session_start = session_sub.add_parser("start", help="create and persist a new session")
    session_start.set_defaults(method="session/start")
    session_start.add_argument("--cwd", required=True, help="absolute worker cwd")
    session_start.add_argument("--name", help="optional human annotation")
    session_start.add_argument("--model", help="optional live-discovered model ID")

    session_resume = session_sub.add_parser("resume", help="reattach a persisted or raw Codex thread")
    session_resume.set_defaults(method="session/resume")
    _add_selector_group(session_resume)
    session_resume.add_argument("--name", help="annotation only when recovering a raw --thread")

    session_sub.add_parser("list", help="list persisted sessions").set_defaults(method="session/list")
    session_show = session_sub.add_parser("show", help="inspect one session")
    session_show.set_defaults(method="session/show")
    _add_selector_group(session_show)

    turn = families.add_parser("turn", help="start, observe, steer, or interrupt turns")
    turn_sub = turn.add_subparsers(dest="action", required=True)

    turn_start = turn_sub.add_parser("start", help="start a turn and return immediately")
    turn_start.set_defaults(method="turn/start")
    _add_selector_group(turn_start)
    _add_prompt_group(turn_start)
    turn_start.add_argument("--model", help="optional live-discovered model ID")
    turn_start.add_argument("--effort", help="optional model-supported reasoning effort")

    turn_status = turn_sub.add_parser("status", help="read current turn state")
    turn_status.set_defaults(method="turn/status")
    _add_selector_group(turn_status)

    turn_wait = turn_sub.add_parser("wait", help="wait for terminal turn state")
    turn_wait.set_defaults(method="turn/wait")
    _add_selector_group(turn_wait)
    turn_wait.add_argument("--timeout", type=_nonnegative_float, default=900.0,
                           help="seconds to wait before a typed timeout")

    turn_events = turn_sub.add_parser("events", help="read bounded notification events")
    turn_events.set_defaults(method="turn/events")
    _add_selector_group(turn_events)
    turn_events.add_argument("--after", type=_nonnegative_int, default=0,
                             help="cursor after which to read events")
    turn_events.add_argument("--limit", type=_event_limit, default=100,
                             help="number of events to return, 1..1000")

    turn_steer = turn_sub.add_parser("steer", help="append instructions to the active turn")
    turn_steer.set_defaults(method="turn/steer")
    _add_selector_group(turn_steer)
    _add_prompt_group(turn_steer)

    turn_interrupt = turn_sub.add_parser("interrupt", help="interrupt the active turn")
    turn_interrupt.set_defaults(method="turn/interrupt")
    _add_selector_group(turn_interrupt)

    return parser


def _add_selector_group(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session", dest="session_id", help="daemon-minted session UUID")
    group.add_argument("--thread", dest="thread_id", help="raw Codex thread ID")


def _add_prompt_group(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", help="inline prompt text")
    group.add_argument("--prompt-file", help="path to a UTF-8 prompt file")


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)

    if args.family == "daemon" and args.action == "serve":
        if args.pretty:
            print("codex-worker: --pretty is not valid with daemon serve", file=sys.stderr)
            return 2
        return _serve(args)

    try:
        method = args.method
        params = _params_for(args)
        response = rpc_call(args.socket, method, params, timeout=_client_timeout(method, params))
    except RpcFault as fault:
        response = rpc_response(None, fault=fault)
        _print_json(response, args.pretty)
        return 1
    except OSError:
        response = rpc_response(None, fault=daemon_unavailable_fault(args.socket))
        _print_json(response, args.pretty)
        return 1
    except ValueError as exc:
        response = rpc_response(None, fault=RpcFault(
            -32602, "Invalid params", "invalid_params", details={"reason": str(exc)}
        ))
        _print_json(response, args.pretty)
        return 2

    _print_json(response, args.pretty)
    if "error" in response:
        return 1
    return 0


def _serve(args: argparse.Namespace) -> int:
    codex = None
    server = None
    try:
        runtime = RuntimeStore(args.event_limit)
        registry = SessionRegistry(args.state)
        codex = CodexAppServer(
            os.getcwd(),
            [args.codex_bin, "app-server"],
            runtime.on_notification,
        )
        broker = WorkerBroker(registry, codex, runtime, args.socket, args.state)
        server = RpcServer(args.socket, broker)
        previous_int = signal.getsignal(signal.SIGINT)
        previous_term = signal.getsignal(signal.SIGTERM)

        def request_stop(signum, frame):
            server.request_shutdown()

        signal.signal(signal.SIGINT, request_stop)
        signal.signal(signal.SIGTERM, request_stop)
        try:
            print("codex-worker daemon listening on %s" % args.socket, file=sys.stderr)
            server.serve_forever()
        finally:
            signal.signal(signal.SIGINT, previous_int)
            signal.signal(signal.SIGTERM, previous_term)
        return 0
    except (SocketInUse, SocketPathUnsafe, RpcFault, OSError, ValueError) as exc:
        print("codex-worker daemon failed: %s" % exc, file=sys.stderr)
        return 1
    finally:
        if server is not None:
            server.server_close()
        if codex is not None:
            try:
                codex.shutdown()
            except Exception:
                pass


def _params_for(args: argparse.Namespace) -> JsonObject:
    method = args.method
    if method in ("daemon/status", "daemon/shutdown", "model/list", "session/list"):
        return {}
    if method == "session/start":
        return {
            "cwd": str(Path(args.cwd).resolve()),
            "name": args.name,
            "model": args.model,
        }
    if method == "session/resume":
        return _selector_params(args, {"name": args.name})
    if method == "session/show":
        return _selector_params(args, {})
    if method == "turn/start":
        return _selector_params(args, {
            "prompt": _prompt(args),
            "model": args.model,
            "effort": args.effort,
        })
    if method == "turn/status":
        return _selector_params(args, {})
    if method == "turn/wait":
        return _selector_params(args, {"timeout": args.timeout})
    if method == "turn/events":
        return _selector_params(args, {"after": args.after, "limit": args.limit})
    if method == "turn/steer":
        return _selector_params(args, {"prompt": _prompt(args)})
    if method == "turn/interrupt":
        return _selector_params(args, {})
    raise ValueError("undocumented method: %s" % method)


def _selector_params(args: argparse.Namespace, extra: JsonObject) -> JsonObject:
    params = {
        "session_id": getattr(args, "session_id", None),
        "thread_id": getattr(args, "thread_id", None),
    }
    params.update(extra)
    return params


def _prompt(args: argparse.Namespace) -> str:
    if getattr(args, "prompt_file", None):
        try:
            return Path(args.prompt_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError("could not read prompt file: %s" % exc) from exc
    return args.prompt


def _client_timeout(method: str, params: JsonObject) -> float:
    if method == "turn/wait":
        timeout = params.get("timeout")
        if type(timeout) in (int, float):
            return max(float(timeout) + 5.0, 5.0)
    return 30.0


def _print_json(payload: JsonObject, pretty: bool) -> None:
    if pretty:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(json.dumps(payload, separators=(",", ":")))
