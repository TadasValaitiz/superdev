"""Command-line entrypoint for the local Codex worker daemon/client."""
import argparse
import json
import math
import os
import signal
import sys
import tempfile
import subprocess
import time
from pathlib import Path
from typing import Any, List, Optional

from .app_server import CodexAppServer
from .broker import WorkerBroker
from .models import JsonObject, RpcFault, rpc_response
from .registry import SessionRegistry
from .rpc import FacadeRpcFault, RpcServer, SocketInUse, SocketPathUnsafe, daemon_unavailable_fault, rpc_call
from .runtime import RuntimeStore
from .commands import (FacadeFault, FacadeFaultCode, GoalSetRequest, GoalShowRequest,
                       InterruptWorkerRequest, LimitsRequest, RunWorkerRequest,
                       MessageWorkerRequest, StartWorkerRequest, SteerWorkerRequest, WorkerHistoryRequest,
                       WorkerMessagesRequest, WorkerStatusRequest)
from .instance import (InstanceDeps, InstanceManager, derive_instance_paths,
                       resolve_instance, validate_instance_id)


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


class CliUsageError(ValueError):
    pass


class CodexWorkerArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self._print_message("%s: error: %s\n" % (self.prog, message), sys.stderr)
        raise CliUsageError(message)


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


def _absolute_path(value: str) -> str:
    if not value or not Path(value).is_absolute():
        raise argparse.ArgumentTypeError("must be an absolute path")
    return value


def _absolute_directory(value: str) -> str:
    path = Path(value)
    if not path.is_absolute() or not path.is_dir():
        raise argparse.ArgumentTypeError("must be an absolute existing directory")
    return value


def _instance_id(value: str) -> str:
    try:
        return validate_instance_id(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(str(exc)) from exc


def _unsupported_turn_selector(value: str) -> str:
    raise argparse.ArgumentTypeError(
        "unsupported argument --turn; use --session <session-id> or --thread <thread-id>"
    )


def build_parser() -> argparse.ArgumentParser:
    parser = CodexWorkerArgumentParser(
        prog="codex-worker",
        description="Local Unix-socket broker for durable Codex worker sessions.",
    )
    parser.add_argument("--socket", type=_absolute_path,
                        help="Unix socket path (default: SUPERDEV_CODEX_WORKER_SOCKET or user temp path)")
    parser.add_argument("--instance", type=_instance_id,
                        help="selected managed worker instance")
    parser.add_argument("--pretty", action="store_true",
                        help="Pretty-print JSON responses for client commands")

    families = parser.add_subparsers(
        dest="family", required=True, parser_class=CodexWorkerArgumentParser
    )

    _add_common_commands(families)

    daemon = families.add_parser("daemon", help="broker lifecycle")
    daemon_sub = daemon.add_subparsers(
        dest="action", required=True, parser_class=CodexWorkerArgumentParser
    )
    serve = daemon_sub.add_parser("serve", help="run the worker daemon in the foreground")
    serve.set_defaults(method=None)
    serve.add_argument("--state", type=_absolute_path, default=default_state_path(),
                       help="session registry path (default: SUPERDEV_CODEX_WORKER_STATE or user state dir)")
    serve.add_argument("--codex-bin", default="codex",
                       help="installed Codex CLI executable path")
    serve.add_argument("--event-limit", type=_positive_int, default=1000,
                       help="per-session in-memory event retention limit")
    daemon_sub.add_parser("status", help="read daemon health").set_defaults(method="daemon/status")
    daemon_sub.add_parser("stop", help="stop the selected managed daemon").set_defaults(method="daemon/stop", managed_daemon=True)
    daemon_sub.add_parser("shutdown", help="gracefully stop the daemon").set_defaults(method="daemon/shutdown")

    model = families.add_parser("model", help="live Codex model discovery")
    model_sub = model.add_subparsers(
        dest="action", required=True, parser_class=CodexWorkerArgumentParser
    )
    model_sub.add_parser("list", help="list discovered models and reasoning efforts").set_defaults(method="model/list")

    session = families.add_parser("session", help="durable conversation identity")
    session_sub = session.add_subparsers(
        dest="action", required=True, parser_class=CodexWorkerArgumentParser
    )
    session_start = session_sub.add_parser("start", help="create and persist a new session")
    session_start.set_defaults(method="session/start")
    session_start.add_argument("--cwd", required=True, type=_absolute_directory,
                               help="absolute worker cwd")
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
    turn_sub = turn.add_subparsers(
        dest="action", required=True, parser_class=CodexWorkerArgumentParser
    )

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


def _add_common_commands(families) -> None:
    start = families.add_parser("start", help="create a named worker and send its first message")
    start.set_defaults(method="worker/start", common=True)
    _add_name_prompt(start)
    start.add_argument("--cwd", default=os.getcwd())
    policy = start.add_mutually_exclusive_group()
    policy.add_argument("--tier", choices=("medium", "very-smart"))
    policy.add_argument("--model")
    start.add_argument("--effort", default="medium")
    start.add_argument("--read-only", action="store_true")
    start.add_argument("--goal")
    start.add_argument("--token-budget", type=_positive_int)
    start.add_argument("--no-callback", action="store_true")
    _add_turn_options(start)
    run = families.add_parser("run", help="send a follow-up to a named worker")
    run.set_defaults(method="worker/run", common=True)
    _add_name_prompt(run); _add_turn_options(run)
    message = families.add_parser("message", help="send a non-blocking Claude update")
    message.set_defaults(method="worker/message", common=True)
    message.add_argument("--name", required=True)
    message_input = message.add_mutually_exclusive_group(required=True)
    message_input.add_argument("--message")
    message_input.add_argument("--message-file")
    message.add_argument("--priority", choices=("now", "next", "later"), default="next")
    message.add_argument("--cc-agent-name")
    for name, method in (("status", "worker/status"), ("messages", "worker/messages"),
                         ("history", "worker/history"), ("interrupt", "worker/interrupt")):
        command = families.add_parser(name)
        command.set_defaults(method=method, common=True)
        command.add_argument("--name", required=True)
        if name in ("messages", "history"): command.add_argument("--tail", type=_positive_int, default=1)
    steer = families.add_parser("steer"); steer.set_defaults(method="worker/steer", common=True); _add_name_prompt(steer)
    goal = families.add_parser("goal"); goal_sub = goal.add_subparsers(dest="action", required=True, parser_class=CodexWorkerArgumentParser)
    goal_set = goal_sub.add_parser("set"); goal_set.set_defaults(method="worker/goal/set", common=True)
    goal_set.add_argument("--name", required=True); goal_set.add_argument("--goal"); goal_set.add_argument("--status", choices=("active", "paused", "blocked", "usageLimited", "budgetLimited", "complete")); goal_set.add_argument("--token-budget", type=_positive_int)
    goal_show = goal_sub.add_parser("show"); goal_show.set_defaults(method="worker/goal/show", common=True); goal_show.add_argument("--name", required=True)
    limits = families.add_parser("limits"); limits.set_defaults(method="account/limits", common=True)


def _add_name_prompt(parser) -> None:
    parser.add_argument("--name", required=True)
    _add_prompt_group(parser)


def _add_turn_options(parser) -> None:
    parser.add_argument("--output-schema")
    parser.add_argument("--timeout", type=_nonnegative_float)


def _add_selector_group(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--session", dest="session_id", help="daemon-minted session UUID")
    group.add_argument("--thread", dest="thread_id", help="raw Codex thread ID")
    group.add_argument("--turn", dest="unsupported_turn_id", type=_unsupported_turn_selector,
                       help=argparse.SUPPRESS)


def _add_prompt_group(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prompt", help="inline prompt text")
    group.add_argument("--prompt-file", help="path to a UTF-8 prompt file")


def _argv_selects_daemon_serve(argv: List[str]) -> bool:
    positional = []
    skip_next = False
    for token in argv:
        if skip_next:
            skip_next = False
            continue
        if token == "--socket":
            skip_next = True
            continue
        if token.startswith("--socket="):
            continue
        if token == "--pretty":
            continue
        if token in ("-h", "--help"):
            return False
        if token.startswith("-"):
            continue
        positional.append(token)
    return len(positional) >= 2 and positional[0] == "daemon" and positional[1] == "serve"


def _argv_wants_pretty(argv: List[str]) -> bool:
    return "--pretty" in argv


def main(argv: Optional[List[str]] = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    try:
        args = parser.parse_args(raw_argv)
    except CliUsageError as exc:
        if _argv_selects_daemon_serve(raw_argv):
            return 2
        response = rpc_response("cli", fault=RpcFault(
            -32602, "Invalid params", "invalid_params", details={"reason": str(exc)}
        ))
        _print_json(response, _argv_wants_pretty(raw_argv))
        return 2
    except SystemExit as exc:
        return int(exc.code)

    if args.family == "daemon" and args.action == "serve":
        if args.pretty or args.instance:
            print("codex-worker: --pretty and --instance are not valid with daemon serve", file=sys.stderr)
            return 2
        return _serve(args)

    try:
        if args.family == "daemon" and args.action == "status" and not args.socket:
            response = {"jsonrpc": "2.0", "id": "cli", "result": _instance_manager(args.instance).status().to_dict()}
            _print_json(response, args.pretty)
            return 0
        if args.family == "daemon" and args.action == "stop":
            if args.socket:
                raise ValueError("--socket is not valid with daemon stop")
            response = {"jsonrpc": "2.0", "id": "cli", "result": _instance_manager(args.instance).stop().to_dict()}
            _print_json(response, args.pretty)
            return 0
        if args.family == "daemon" and args.action == "shutdown" and args.instance:
            raise ValueError("--instance is not valid with daemon shutdown")
        method = args.method
        params = _params_for(args)
        if method == "worker/start" and not args.no_callback:
            from .claude_transport import capture_from_env
            capture = capture_from_env(os.environ)
            params["callback_capture"] = capture.to_dict() if capture is not None else None
        if getattr(args, "common", False):
            _validate_common_request(method, params)
            if args.socket:
                raise ValueError("--socket is not valid for common worker commands")
            socket_path = _common_endpoint(args.instance, autostart=method in ("worker/start", "worker/run"))
        else:
            if args.socket and args.instance:
                raise ValueError("--socket and --instance are mutually exclusive")
            socket_path = (str(_instance_manager(args.instance).deps.paths.socket_path)
                           if args.instance else args.socket or default_socket_path())
        response = rpc_call(socket_path, method, params, timeout=_client_timeout(method, params))
    except FacadeFault as fault:
        response = rpc_response("cli", fault=FacadeRpcFault(fault))
        _print_json(response, args.pretty)
        return 1
    except RpcFault as fault:
        response = rpc_response("cli", fault=fault)
        _print_json(response, args.pretty)
        return 1
    except OSError:
        response = rpc_response("cli", fault=daemon_unavailable_fault(args.socket or default_socket_path()))
        _print_json(response, args.pretty)
        return 1
    except ValueError as exc:
        response = rpc_response("cli", fault=RpcFault(
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
    callback_dispatcher = None
    try:
        runtime = RuntimeStore(args.event_limit)
        registry = SessionRegistry(args.state)
        codex = CodexAppServer(
            os.getcwd(),
            [args.codex_bin, "app-server"],
            runtime.on_notification,
        )
        socket_path = args.socket or default_socket_path()
        broker = WorkerBroker(registry, codex, runtime, socket_path, args.state)
        facade, callback_dispatcher = _managed_components(
            broker, runtime, registry, Path(args.state))
        server = RpcServer(socket_path, broker, facade)
        if callback_dispatcher is not None:
            callback_dispatcher.start()
        previous_int = signal.getsignal(signal.SIGINT)
        previous_term = signal.getsignal(signal.SIGTERM)

        def request_stop(signum, frame):
            server.request_shutdown()

        signal.signal(signal.SIGINT, request_stop)
        signal.signal(signal.SIGTERM, request_stop)
        try:
            print("codex-worker daemon listening on %s" % socket_path, file=sys.stderr)
            server.serve_forever()
        finally:
            signal.signal(signal.SIGINT, previous_int)
            signal.signal(signal.SIGTERM, previous_term)
        return 0
    except (SocketInUse, SocketPathUnsafe, RpcFault, OSError, ValueError) as exc:
        print("codex-worker daemon failed: %s" % exc, file=sys.stderr)
        return 1
    finally:
        if callback_dispatcher is not None:
            callback_dispatcher.shutdown()
        if server is not None:
            server.server_close()
        if codex is not None:
            try:
                codex.shutdown()
            except Exception:
                pass


def _params_for(args: argparse.Namespace) -> JsonObject:
    method = args.method
    if method == "worker/start":
        return {"name": args.name, "prompt": _prompt(args), "cwd": str(Path(args.cwd).resolve()),
                "tier": None if args.model else (args.tier or "medium"), "model": args.model, "effort": args.effort,
                "access": "read_only" if args.read_only else "full", "goal": args.goal,
                "token_budget": args.token_budget, "output_schema": _output_schema(args.output_schema),
                "timeout": args.timeout, "no_callback": args.no_callback,
                "callback_capture": None}
    if method == "worker/run":
        return {"name": args.name, "prompt": _prompt(args), "output_schema": _output_schema(args.output_schema), "timeout": args.timeout}
    if method == "worker/message":
        message = _message(args)
        from .claude_transport import MAX_USER_LINE_UTF16_UNITS
        if len(message.encode("utf-16-le")) // 2 > MAX_USER_LINE_UTF16_UNITS:
            raise FacadeFault(
                FacadeFaultCode.CALLBACK_PAYLOAD_TOO_LARGE,
                "Proactive callback message exceeds the Claude user-line limit",
                "callback_payload_too_large",
            )
        return {"name": args.name, "message": message, "priority": args.priority,
                "cc_agent_name": args.cc_agent_name}
    if method in ("worker/status", "worker/interrupt", "worker/goal/show"):
        return {"name": args.name}
    if method in ("worker/messages", "worker/history"):
        return {"name": args.name, "tail": args.tail}
    if method == "worker/steer": return {"name": args.name, "prompt": _prompt(args)}
    if method == "worker/goal/set":
        return {"name": args.name, "objective": args.goal, "status": args.status, "token_budget": args.token_budget}
    if method == "account/limits": return {}
    if method in ("daemon/status", "daemon/shutdown", "model/list", "session/list"):
        return {}
    if method == "session/start":
        return {
            "cwd": str(Path(args.cwd).resolve()),
            "name": args.name,
            "model": args.model,
        }
    if method == "session/resume":
        if getattr(args, "session_id", None) is not None and args.name is not None:
            raise ValueError("--name is only valid with --thread raw recovery")
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
    prompt_file = getattr(args, "prompt_file", None)
    if prompt_file is not None:
        if not prompt_file:
            raise ValueError("prompt file path must be non-empty")
        try:
            prompt = Path(prompt_file).read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError("could not read prompt file: %s" % exc) from exc
    else:
        prompt = args.prompt
    if not isinstance(prompt, str) or not prompt:
        raise ValueError("prompt must be a non-empty string")
    return prompt


def _message(args: argparse.Namespace) -> str:
    path = getattr(args, "message_file", None)
    if path is not None:
        try:
            message = Path(path).read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError("could not read message file: %s" % exc) from exc
    else:
        message = args.message
    if not isinstance(message, str) or not message:
        raise ValueError("message must be a non-empty string")
    return message


def _client_timeout(method: str, params: JsonObject) -> float:
    if method in ("worker/start", "worker/run"):
        timeout = params.get("timeout")
        return None if timeout is None else max(float(timeout) + 5.0, 5.0)
    if method == "turn/wait":
        timeout = params.get("timeout")
        if type(timeout) in (int, float):
            return max(float(timeout) + 5.0, 5.0)
    return 30.0


def _output_schema(path: Optional[str]):
    if path is None: return None
    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError("could not read output schema: %s" % exc) from exc
    if not isinstance(value, dict): raise ValueError("output schema must be a JSON object")
    return value


_COMMON_REQUESTS = {
    "worker/start": StartWorkerRequest, "worker/run": RunWorkerRequest, "worker/message": MessageWorkerRequest,
    "worker/status": WorkerStatusRequest, "worker/messages": WorkerMessagesRequest,
    "worker/history": WorkerHistoryRequest, "worker/steer": SteerWorkerRequest,
    "worker/interrupt": InterruptWorkerRequest, "worker/goal/set": GoalSetRequest,
    "worker/goal/show": GoalShowRequest, "account/limits": LimitsRequest,
}


def _validate_common_request(method: str, params: JsonObject) -> None:
    """Validate at the CLI lifecycle boundary before selecting an endpoint."""
    _COMMON_REQUESTS[method].from_dict(params)


def _managed_state_home() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support"
    return Path(os.environ.get("XDG_STATE_HOME", str(Path.home() / ".local" / "state")))


def _spawn_daemon(argv, log_path):
    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    handle = open(log_path, "ab", buffering=0)
    try:
        return subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=handle, stderr=handle,
                                start_new_session=True)
    finally:
        handle.close()


def _common_endpoint(explicit_instance, autostart):
    manager = _instance_manager(explicit_instance)
    status = manager.ensure_running() if autostart else manager.status()
    if status.status != "ready":
        raise FacadeFault(FacadeFaultCode.DAEMON_STOPPED, "Worker daemon is stopped", "daemon_stopped")
    return str(manager.deps.paths.socket_path)


def _instance_manager(explicit_instance):
    identity = resolve_instance(explicit_instance, os.environ)
    paths = derive_instance_paths(identity, sys.platform, _managed_state_home(), Path(tempfile.gettempdir()), os.getuid())
    launcher = str(Path(__file__).resolve().parents[4] / "bin" / "codex-worker")
    return InstanceManager(InstanceDeps(paths, launcher, "codex", _spawn_daemon, rpc_call, time.monotonic), identity)


def _managed_components(broker, runtime, registry, state_path):
    from .facade import FacadeDeps, WorkerFacade
    from .instance import load_managed_identity
    from .callback_dispatcher import TerminalCallbackDispatcher
    from .callback_store import CallbackStore
    from .claude_transport import ClaudeTransport
    from . import projection
    identity = load_managed_identity(state_path)
    if identity is None: return None, None
    paths = derive_instance_paths(identity, sys.platform, _managed_state_home(),
                                  Path(tempfile.gettempdir()), os.getuid())
    store = CallbackStore(paths.callback_path, paths.callback_artifact_dir)
    transport = ClaudeTransport()
    dispatcher = TerminalCallbackDispatcher(store, transport, runtime, projection,
                                            time.monotonic, transport.deps.now)
    facade = WorkerFacade(FacadeDeps(identity, registry, broker, runtime, projection,
                                     time.monotonic, store, dispatcher, transport))
    return facade, dispatcher


def _managed_facade(broker, runtime, registry, state_path):
    """Compatibility seam for tests and embedders that only need the façade."""
    return _managed_components(broker, runtime, registry, state_path)[0]


def _print_json(payload: JsonObject, pretty: bool) -> None:
    if pretty:
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    else:
        print(json.dumps(payload, separators=(",", ":"), allow_nan=False))
