"""Command-line entrypoint for the local Codex worker daemon/client."""
import argparse
import contextlib
import errno
import json
import math
import os
import shlex
import signal
import shutil
import sys
import tempfile
import subprocess
import time
import uuid
from dataclasses import replace
from pathlib import Path
from typing import Any, List, Optional

from .broker import WorkerBroker
from .models import JsonObject, RpcFault, rpc_response
from .registry import SessionRegistry
from .rpc import (FacadeRpcFault, RpcServer, SocketInUse, SocketPathUnsafe,
                  daemon_unavailable_fault, rpc_call, validate_raw_params)
from .runtime import RuntimeStore
from .commands import (FacadeFault, FacadeFaultCode, GoalSetRequest, GoalShowRequest,
                       InterruptWorkerRequest, LimitsRequest, RunWorkerRequest,
                       MessageWorkerRequest, StartWorkerRequest, SteerWorkerRequest, WorkerHistoryRequest,
                       WorkerMessagesRequest, WorkerStatusRequest,
                       ResolveLegacyConflictRequest)
from .instance import (ServiceDeps, ServiceManager)
from .service_domain import (DEFAULT_PUBLIC_LISTENER, derive_service_paths,
                             validate_public_listener)
from .version import distribution_version
from .websocket_transport import strict_json_loads


DOCUMENTED_CLIENT_METHODS = {
    "daemon/status",
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
    return str(root / "service" / "registry.json")


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


def _config_override(value: str):
    key, separator, raw = value.partition("=")
    key = key.strip()
    if not separator or not key:
        raise argparse.ArgumentTypeError("must be KEY=VALUE with a non-empty KEY")
    try:
        parsed = strict_json_loads(raw)
    except ValueError:
        parsed = raw
    return key, parsed


def _absolute_path(value: str) -> str:
    if not value or not Path(value).is_absolute():
        raise argparse.ArgumentTypeError("must be an absolute path")
    return value


def _absolute_directory(value: str) -> str:
    path = Path(value)
    if not path.is_absolute() or not path.is_dir():
        raise argparse.ArgumentTypeError("must be an absolute existing directory")
    return value


def _public_listener(value: str) -> str:
    try:
        return validate_public_listener(value)
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
    parser.add_argument(
        "--version",
        action="version",
        version="codex-worker %s" % distribution_version(),
    )
    parser.add_argument("--socket", type=_absolute_path,
                        help="expert raw-only Unix RPC endpoint; bypasses managed service lifecycle")
    parser.add_argument("--pretty", action="store_true",
                        help="Pretty-print JSON responses for client commands")

    families = parser.add_subparsers(
        dest="family", required=True, parser_class=CodexWorkerArgumentParser
    )

    _add_common_commands(families)

    daemon = families.add_parser("daemon", help="broker lifecycle")
    daemon_sub = daemon.add_subparsers(
        dest="action", required=True, parser_class=CodexWorkerArgumentParser,
        metavar="{start,status,stop,restart}",
    )
    serve = daemon_sub.add_parser("serve")
    serve.set_defaults(method=None)
    serve.add_argument("--state", type=_absolute_path, default=default_state_path(),
                       help="session registry path (default: SUPERDEV_CODEX_WORKER_STATE or user state dir)")
    serve.add_argument("--codex-bin", default="codex",
                       help="installed Codex CLI executable path")
    serve.add_argument("--event-limit", type=_positive_int, default=1000,
                       help="per-session in-memory event retention limit")
    serve.add_argument("--app-server-listen", type=_public_listener,
                       default=DEFAULT_PUBLIC_LISTENER)
    serve.add_argument("--generation", help=argparse.SUPPRESS)
    serve.add_argument("--startup-receipt", type=_absolute_path, help=argparse.SUPPRESS)
    start_service = daemon_sub.add_parser("start", help="ensure the global service")
    start_service.set_defaults(method="service/start", managed_daemon=True)
    start_service.add_argument("--app-server-listen", type=_public_listener)
    daemon_sub.add_parser("status", help="inspect the global service without starting").set_defaults(method="service/status")
    stop_service = daemon_sub.add_parser(
        "stop", help="dangerous supervised global stop",
        description="Stop the one global service while preserving durable state; active work refuses unless --force explicitly accepts global impact.")
    stop_service.set_defaults(method="service/stop", managed_daemon=True)
    stop_service.add_argument(
        "--force", action="store_true",
        help=("interrupt every measured active name/session/thread/turn; accepts an "
              "unknown global blast radius if degraded inventory is unavailable"))
    restart_service = daemon_sub.add_parser(
        "restart", help="dangerous supervised global restart",
        description="Restart the one global service while preserving durable state; active work refuses unless --force explicitly accepts global impact.")
    restart_service.set_defaults(method="service/restart", managed_daemon=True)
    restart_service.add_argument("--app-server-listen", type=_public_listener)
    restart_service.add_argument(
        "--force", action="store_true",
        help=("interrupt every measured active name/session/thread/turn; accepts an "
              "unknown global blast radius if degraded inventory is unavailable"))

    migration = families.add_parser("migration", help="inspect or resolve legacy imports")
    migration_sub = migration.add_subparsers(
        dest="action", required=True, parser_class=CodexWorkerArgumentParser)
    migration_sub.add_parser(
        "status", help="inspect preserved import and conflict state").set_defaults(
            method="migration/status")
    resolve = migration_sub.add_parser(
        "resolve", help="select one preserved legacy candidate explicitly")
    resolve.set_defaults(method="migration/resolve")
    resolve.add_argument("--name", required=True)
    resolve.add_argument("--thread", dest="thread_id", required=True)
    resolve.add_argument("--as-name")

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

    _add_public_limits(parser)
    return parser


def _add_public_limits(parser: argparse.ArgumentParser) -> None:
    """Attach an explicit operational boundary to every public help surface."""
    generic = ("Uses the one machine-wide service and global worker names. It may replace an "
               "incompatible idle service, but never forces active work or performs cleanup stop.")
    creation = ("Creation policy (--tier/--model, --effort, --read-only, --search, --config) is "
                "fixed at creation and reapplied when the worker is resumed; run cannot change it.")
    danger = ("Machine-wide and human-supervised. Active work refuses unless --force is "
              "explicitly supplied. Healthy force reports every measured active turn; "
              "degraded force accepts an unknown global blast radius when inventory is unavailable.")
    raw = ("Without the expert global --socket bypass, requires the existing strictly ready "
           "service and never auto-starts it. --socket targets only that exact Unix endpoint.")

    def visit(current: argparse.ArgumentParser, path: List[str]) -> None:
        if path == ["daemon", "serve"]:
            return
        current.formatter_class = argparse.RawDescriptionHelpFormatter
        if path in (["daemon", "stop"], ["daemon", "restart"]):
            boundary = danger
        elif path and path[0] in ("model", "session", "turn"):
            boundary = raw
        elif path == ["start"]:
            boundary = generic + "\n  " + creation
        else:
            boundary = generic
        current.epilog = "Limits:\n  %s" % boundary
        for action in current._actions:
            if isinstance(action, argparse._SubParsersAction):
                for name, child in action.choices.items():
                    visit(child, path + [name])

    visit(parser, [])


def _add_common_commands(families) -> None:
    start = families.add_parser("start", help="create a named worker and send its first message")
    start.set_defaults(method="worker/start", common=True)
    _add_name_prompt(start)
    start.add_argument("--cwd", required=True, type=_absolute_directory)
    policy = start.add_mutually_exclusive_group()
    policy.add_argument("--tier", choices=("medium", "very-smart"))
    policy.add_argument("--model")
    start.add_argument("--effort", default="medium")
    start.add_argument("--read-only", action="store_true")
    start.add_argument("--goal")
    start.add_argument("--token-budget", type=_positive_int)
    start.add_argument("--search", action="store_true",
                       help='enable live web search (codex --search); sugar for --config web_search="live"')
    start.add_argument("--config", action="append", type=_config_override, metavar="KEY=VALUE",
                       help="repeatable Codex config override, like codex -c; VALUE is parsed as JSON "
                            "when it parses, otherwise used as a string")
    start.add_argument("--no-callback", action="store_true")
    start.add_argument("--app-server-listen", type=_public_listener)
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


def _removed_instance_reason(argv: List[str]) -> Optional[str]:
    if "--instance" in argv or any(token.startswith("--instance=") for token in argv):
        return ("--instance was removed because codex-worker now has one global service; "
                "use global --name values and run 'codex-worker migration status' for legacy data")
    return None


def main(argv: Optional[List[str]] = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    removed_reason = _removed_instance_reason(raw_argv)
    if removed_reason is not None:
        response = rpc_response("cli", fault=RpcFault(
            -32602, "Invalid params", "invalid_params", details={"reason": removed_reason}))
        _print_json(response, _argv_wants_pretty(raw_argv))
        return 2
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
        if args.pretty:
            print("codex-worker: --pretty is not valid with daemon serve", file=sys.stderr)
            return 2
        try:
            _require_loaded_plugin_version(args)
            return _serve(args)
        except FacadeFault as fault:
            response = rpc_response("cli", fault=FacadeRpcFault(fault))
            _print_json(response, False)
            return 3

    try:
        params = _params_for(args)
        managed_family = args.family in ("migration",) or (
            args.family == "daemon" and args.action in ("start", "status", "stop", "restart"))
        if getattr(args, "common", False):
            _validate_common_request(args.method, params)
            if args.socket:
                raise ValueError("--socket is not valid for common worker commands")
        elif not managed_family:
            validate_raw_params(args.method, params)
        elif managed_family and args.socket and not (
                args.family == "daemon" and args.action == "status"):
            raise ValueError("--socket is not valid with managed lifecycle or migration commands")

        _require_loaded_plugin_version(args)
        if args.family == "daemon" and args.action == "start":
            manager = _service_manager()
            manager.ensure_running(args.app_server_listen)
            response = {"jsonrpc": "2.0", "id": "cli",
                        "result": manager.status().to_dict()}
            _print_json(response, args.pretty)
            return 0
        if args.family == "daemon" and args.action == "status" and not args.socket:
            response = {"jsonrpc": "2.0", "id": "cli",
                        "result": _service_manager().status().to_dict()}
            _print_json(response, args.pretty)
            return 0
        if args.family == "daemon" and args.action == "stop":
            response = {"jsonrpc": "2.0", "id": "cli",
                        "result": _service_manager().stop(args.force)}
            _print_json(response, args.pretty)
            return 0
        if args.family == "daemon" and args.action == "restart":
            response = {"jsonrpc": "2.0", "id": "cli",
                        "result": _service_manager().restart(
                            args.app_server_listen, args.force)}
            _print_json(response, args.pretty)
            return 0
        method = args.method
        if method == "worker/start" and not args.no_callback:
            from .claude_transport import capture_from_env
            capture = capture_from_env(os.environ)
            params["callback_capture"] = capture.to_dict() if capture is not None else None
        if getattr(args, "common", False):
            socket_path = _common_endpoint(
                args.app_server_listen if method == "worker/start" else None, True)
        elif args.family == "migration":
            socket_path = _common_endpoint(None, True)
        else:
            socket_path = args.socket or _managed_raw_endpoint()
            if args.family == "daemon" and args.action == "status" and args.socket:
                method = "daemon/status"
        response = rpc_call(socket_path, method, params, timeout=_client_timeout(method, params))
    except FacadeFault as fault:
        response = rpc_response("cli", fault=FacadeRpcFault(fault))
        _print_json(response, args.pretty)
        return 3
    except RpcFault as fault:
        response = rpc_response("cli", fault=fault)
        _print_json(response, args.pretty)
        return _response_error_exit(response)
    except OSError:
        response = rpc_response("cli", fault=daemon_unavailable_fault(args.socket or default_socket_path()))
        _print_json(response, args.pretty)
        return 3
    except ValueError as exc:
        response = rpc_response("cli", fault=RpcFault(
            -32602, "Invalid params", "invalid_params", details={"reason": str(exc)}
        ))
        _print_json(response, args.pretty)
        return 2

    _print_json(response, args.pretty)
    if "error" in response:
        return _response_error_exit(response)
    return 0


def _response_error_exit(response: JsonObject) -> int:
    error = response.get("error")
    data = error.get("data") if isinstance(error, dict) else None
    kind = data.get("kind") if isinstance(data, dict) else None
    return 1 if kind in ("internal_error", "broker_error") else 3


def _serve(args: argparse.Namespace) -> int:
    service = None
    server = None
    callback_dispatcher = None
    try:
        paths = _service_paths()
        state_path = Path(args.state)
        if state_path != paths.registry_path or (args.socket and Path(args.socket) != paths.rpc_socket):
            durable = state_path.parent
            paths = replace(
                paths, durable_dir=durable,
                rpc_socket=Path(args.socket) if args.socket else paths.rpc_socket,
                private_codex_socket=paths.private_codex_socket.parent / (
                    "c-%s.sock" % uuid.uuid4().hex[:8]),
                start_lock=(Path(args.socket).with_suffix(".start.lock")
                            if args.socket else paths.start_lock),
                registry_path=state_path,
                config_path=durable / "service.json",
                migration_path=durable / "migration.json",
                log_path=durable / "daemon.log",
                callback_path=durable / "callbacks.json",
                callback_artifact_dir=durable / "callback-artifacts")
        config = _serve_config(paths, args.app_server_listen, args.generation)
        from .migration import (LegacyMigrationDeps, LegacyMigrator,
                                LiveMigrationCoordinator)
        migrator = LegacyMigrator(LegacyMigrationDeps(
            paths, paths.durable_dir.parent / "instances"))
        migrator.scan_and_apply()
        runtime = RuntimeStore(args.event_limit)
        registry = SessionRegistry(paths.registry_path, migration_path=paths.migration_path)
        from .service import GlobalWorkerService
        service = GlobalWorkerService(
            paths, config, runtime.on_notification, codex_argv=(args.codex_bin,))
        service.start()
        # The public gateway and private child now both exist; this is the only
        # commit point at which a listener generation becomes durable.
        config_manager = ServiceManager(ServiceDeps(
            paths, _daemon_launcher(), args.codex_bin, _spawn_daemon, rpc_call,
            time.monotonic, which=shutil.which,
            expected_version=distribution_version()))
        existing_config = config_manager._read_config()
        if existing_config is None:
            config_manager._write_config_once(config)
        elif existing_config != config:
            config_manager._replace_config(config)
        lifecycle = service._lifecycle_for_composition()
        codex = service._connection
        if codex is None:
            raise RuntimeError("global service connection was not composed")
        broker = WorkerBroker(
            registry, codex, runtime, str(paths.rpc_socket), str(paths.registry_path),
            worker_version=config.worker_version, gate=lifecycle.gate,
            listener=config.listener)
        facade, callback_dispatcher = _global_worker_facade(
            broker, runtime, registry, paths, config.listener)
        from .broker import MaintenanceCoordinator
        from .facade import ServiceFacade, ServiceFacadeDeps
        maintenance = MaintenanceCoordinator(broker, lifecycle)
        migration = LiveMigrationCoordinator(
            migrator, broker, facade.deps.callback_store)
        service_facade = ServiceFacade(ServiceFacadeDeps(
            service, broker, maintenance, migration, config))
        server = RpcServer(str(paths.rpc_socket), broker, facade, service_facade)
        if callback_dispatcher is not None:
            callback_dispatcher.start()
        previous_int = signal.getsignal(signal.SIGINT)
        previous_term = signal.getsignal(signal.SIGTERM)

        def request_stop(signum, frame):
            server.request_shutdown()

        signal.signal(signal.SIGINT, request_stop)
        signal.signal(signal.SIGTERM, request_stop)
        try:
            server.serve_forever()
        finally:
            signal.signal(signal.SIGINT, previous_int)
            signal.signal(signal.SIGTERM, previous_term)
        return 0
    except (SocketInUse, SocketPathUnsafe, RpcFault, OSError, ValueError) as exc:
        if (args.startup_receipt and isinstance(exc, OSError)
                and exc.errno == errno.EADDRINUSE):
            _write_startup_receipt(
                Path(args.startup_receipt), args.app_server_listen)
        print("codex-worker daemon failed: %s" % exc, file=sys.stderr)
        return 1
    finally:
        if callback_dispatcher is not None:
            callback_dispatcher.shutdown()
        if server is not None:
            server.server_close()
        if service is not None:
            try:
                service._terminate_resources(suppress_errors=True)
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
                "callback_capture": None, "config": _start_config(args)}
    if method == "worker/run":
        return {"name": args.name, "prompt": _prompt(args), "output_schema": _output_schema(args.output_schema), "timeout": args.timeout}
    if method == "worker/message":
        message = _message(args)
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
    if method in ("daemon/status", "service/status", "service/start", "model/list",
                  "session/list", "migration/status"):
        return {}
    if method == "service/stop": return {"force": args.force}
    if method == "service/restart":
        return {"listener": args.app_server_listen, "force": args.force}
    if method == "migration/resolve":
        value = {"name": args.name, "thread_id": args.thread_id,
                 "as_name": args.as_name}
        ResolveLegacyConflictRequest.from_dict(value)
        return value
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


def _start_config(args: argparse.Namespace) -> Optional[JsonObject]:
    config = {}  # type: JsonObject
    for key, value in args.config or []:
        if key in config:
            raise ValueError("--config %s is given more than once" % key)
        config[key] = value
    if args.search:
        if "web_search" in config:
            raise ValueError("--search already sets web_search; drop --config web_search")
        config["web_search"] = "live"
    return config or None


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


def _common_endpoint(listener=None, autostart=True):
    """Ensure the singleton for every common command after local validation."""
    del autostart  # compatibility parameter for older internal callers
    manager = _service_manager()
    status = manager.ensure_running(listener)
    if status.status != "ready":
        raise FacadeFault(
            FacadeFaultCode.DAEMON_STOPPED, "Global worker service is stopped",
            "daemon_stopped", next_actions=[{
                "command": "codex-worker daemon start",
                "reason": "Start the global service without starting a turn"}])
    return str(manager.deps.paths.rpc_socket)


def _managed_raw_endpoint(unused=None):
    """Require exact-ready singleton state without starting or replacing it."""
    del unused
    manager = _service_manager()
    status = manager.readiness()
    socket_path = str(manager.deps.paths.rpc_socket)
    if status is None:
        raise daemon_unavailable_fault(socket_path)
    if status.service_version != distribution_version():
        raise FacadeFault(
            FacadeFaultCode.TOOL_VERSION_MISMATCH,
            "Global codex-worker service does not match the installed command",
            "tool_version_mismatch",
            details={
                "reason": "managed_service_version_differs",
                "expected_version": distribution_version(),
                "actual_version": status.service_version,
                "socket_path": socket_path,
            },
            next_actions=[{
                "command": "codex-worker daemon status",
                "reason": "Inspect the incompatible global service without replacing it",
            }],
        )
    if getattr(status, "status", None) != "ready":
        raise daemon_unavailable_fault(socket_path)
    return socket_path


def _daemon_launcher():
    source_launcher = Path(__file__).resolve().parent.parent / "codex-worker"
    if source_launcher.is_file():
        return str(source_launcher)
    return str(Path(sys.executable).with_name("codex-worker"))


def _service_paths():
    return derive_service_paths(
        sys.platform, _managed_state_home(), Path(tempfile.gettempdir()), os.getuid())


def _service_manager():
    return ServiceManager(ServiceDeps(
        _service_paths(), _daemon_launcher(), "codex", _spawn_daemon, rpc_call,
        time.monotonic, which=shutil.which, expected_version=distribution_version()))


def _instance_manager(explicit_instance=None):
    """Private test/embedder shim; public instance routing is rejected before parsing."""
    del explicit_instance
    return _service_manager()


def _require_loaded_plugin_version(args: argparse.Namespace) -> None:
    """Refuse operational use when this executable differs from the loaded plugin."""
    if getattr(args, "version", False):
        return
    root_value = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if not root_value:
        return
    root = Path(root_value)
    manifest_path = root / ".claude-plugin" / "plugin.json"
    loaded_version = None
    reason = "loaded_manifest_invalid"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        candidate = payload.get("version") if isinstance(payload, dict) else None
        if isinstance(candidate, str) and candidate:
            loaded_version = candidate
            reason = "loaded_plugin_version_differs"
    except (OSError, ValueError):
        pass
    installed_version = distribution_version()
    if loaded_version == installed_version:
        return
    installer = root / "skills" / "subagent-driven-development" / "scripts" / "install-codex-worker"
    next_actions = [{
        "command": "codex-worker --version",
        "reason": "Inspect the installed command version without runtime contact",
    }]
    if installer.is_file():
        next_actions.append({
            "command": shlex.quote(str(installer)),
            "reason": "After coordinating other rooms, repair from this loaded plugin root",
        })
    raise FacadeFault(
        FacadeFaultCode.TOOL_VERSION_MISMATCH,
        "Installed codex-worker does not match the loaded Superdev plugin",
        "tool_version_mismatch",
        details={
            "reason": reason,
            "loaded_root": str(root),
            "loaded_version": loaded_version,
            "installed_version": installed_version,
            "coordination": (
                "One global codex-worker version is shared by all rooms. Coordinate cached "
                "plugin versions before rerunning this room's trusted installer."
            ),
        },
        known_ids={"name": None, "session_id": None,
                   "thread_id": None, "turn_id": None},
        next_actions=next_actions,
    )


def _serve_config(paths, listener, generation=None):
    from .service_domain import ServiceConfig
    manager = ServiceManager(ServiceDeps(
        paths, _daemon_launcher(), "codex", _spawn_daemon, rpc_call,
        time.monotonic, which=shutil.which, expected_version=distribution_version()))
    existing = manager._read_config()
    requested = validate_public_listener(listener)
    if existing is not None:
        if existing.listener != requested:
            raise manager._conflict(existing.listener, requested)
        if (existing.worker_version == distribution_version()
                and (generation is None or existing.generation_id == generation)):
            return existing
    return ServiceConfig(requested, distribution_version(),
                         generation or str(uuid.uuid4()))


def _write_startup_receipt(path: Path, listener: str) -> None:
    """Publish one bounded child-bind failure without log or peer content."""
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"kind": "address_in_use", "listener": listener}, handle,
                      separators=(",", ":"), sort_keys=True)
            handle.write("\n"); handle.flush(); os.fsync(handle.fileno())
    except BaseException:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(str(path))
        raise


def _global_worker_facade(broker, runtime, registry, paths, listener):
    from .facade import FacadeDeps, WorkerFacade
    from .callback_dispatcher import TerminalCallbackDispatcher
    from .callback_store import CallbackStore
    from .claude_transport import ClaudeTransport
    from . import projection
    store = CallbackStore(paths.callback_path, paths.callback_artifact_dir)
    transport = ClaudeTransport()
    dispatcher = TerminalCallbackDispatcher(store, transport, runtime, projection,
                                            time.monotonic, transport.deps.now)
    facade = WorkerFacade(FacadeDeps(
        registry, broker, runtime, projection, time.monotonic,
        store, dispatcher, transport, listener=listener))
    return facade, dispatcher


def _managed_components(broker, runtime, registry, state_path):
    """Compatibility shim over global callback/facade composition."""
    paths = _service_paths()
    if Path(state_path) != paths.registry_path:
        durable = Path(state_path).parent
        paths = replace(paths, durable_dir=durable, registry_path=Path(state_path),
                        callback_path=durable / "callbacks.json",
                        callback_artifact_dir=durable / "callback-artifacts")
    return _global_worker_facade(
        broker, runtime, registry, paths, DEFAULT_PUBLIC_LISTENER)


def _managed_facade(broker, runtime, registry, state_path):
    """Compatibility seam for tests and embedders that only need the façade."""
    return _managed_components(broker, runtime, registry, state_path)[0]


def _print_json(payload: JsonObject, pretty: bool) -> None:
    _validate_wire_recovery_actions(payload)
    if pretty:
        print(json.dumps(payload, indent=2, sort_keys=True, allow_nan=False))
    else:
        print(json.dumps(payload, separators=(",", ":"), allow_nan=False))


def _validate_wire_recovery_actions(payload: JsonObject) -> None:
    commands = []  # type: List[str]
    def walk(value: Any) -> None:
        if isinstance(value, dict):
            commands.extend(value[key] for key in ("attach_command", "resume_command")
                            if isinstance(value.get(key), str))
            recovery = value.get("recovery")
            if isinstance(recovery, str):
                commands.append(recovery)
            elif isinstance(recovery, dict):
                commands.extend(command for command in recovery.values()
                                if isinstance(command, str))
            for action_field in ("next_actions", "resolution_actions"):
                actions = value.get(action_field)
                if isinstance(actions, list):
                    for action in actions:
                        if isinstance(action, str):
                            commands.append(action)
                        elif (isinstance(action, dict)
                              and isinstance(action.get("command"), str)):
                            commands.append(action["command"])
            for nested in value.values():
                walk(nested)
        elif isinstance(value, list):
            for nested in value:
                walk(nested)

    walk(payload)
    parser = build_parser()
    for command in commands:
        if "\n" in command or "\r" in command:
            raise ValueError("recovery action must be one direct argv")
        tokens = shlex.split(command)
        if not tokens:
            raise ValueError("recovery action is not literal")
        if _has_unquoted_shell_syntax(command):
            raise ValueError("recovery action must be one direct argv")
        if tokens[0] == "codex-worker":
            if any(tokens[index:index + 2] == ["daemon", "serve"]
                   for index in range(1, len(tokens) - 1)):
                raise ValueError("hidden daemon serve is not a public recovery action")
            try:
                with open(os.devnull, "w") as discard:
                    with contextlib.redirect_stdout(discard), \
                            contextlib.redirect_stderr(discard):
                        parsed = parser.parse_args(tokens[1:])
                if (getattr(parsed, "family", None) == "daemon"
                        and getattr(parsed, "action", None) == "serve"):
                    raise ValueError("hidden daemon serve is not a public recovery action")
            except SystemExit as exc:
                if exc.code != 0:
                    raise ValueError("recovery action does not parse: %s" % command)
            except CliUsageError as exc:
                raise ValueError("recovery action does not parse: %s" % command) from exc
        elif tokens[0] == "codex":
            if len(tokens) not in (3, 5) or tokens[1] != "--remote" or (
                    len(tokens) == 5 and tokens[3] != "resume"):
                raise ValueError("Codex recovery action does not match the public attach grammar")
            validate_public_listener(tokens[2])
        elif (not Path(tokens[0]).is_absolute() or not Path(tokens[0]).is_file()
              or not os.access(tokens[0], os.X_OK)):
            raise ValueError("recovery action executable does not exist: %s" % tokens[0])


def _has_unquoted_shell_syntax(command: str) -> bool:
    quote = None
    escaped = False
    for character in command:
        if character in "\r\n":
            return True
        if escaped:
            escaped = False
            continue
        if character == "\\" and quote != "'":
            escaped = True
            continue
        if quote is not None:
            if character == quote:
                quote = None
            elif quote == '"' and character in "$`":
                return True
            continue
        if character in "'\"":
            quote = character
        elif character in ";&|`$()#*?[]{}<>":
            return True
    return escaped or quote is not None
