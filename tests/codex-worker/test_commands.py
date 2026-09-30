import contextlib
import sys
import tempfile
import unittest
from dataclasses import FrozenInstanceError
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.commands import (
    AccessMode, AgentMessageView, CompletionResponse, CompletionSelection, FacadeFault, FacadeFaultCode,
    CallbackAttemptState, CallbackAttemptView, CallbackCapture, CallbackSendResponse,
    CallbackState, CallbackStatusView, MessagePriority, MessageWorkerRequest,
    MetricAvailability, MetricEvidence, RecoveryView, StartWorkerRequest, Tier, TurnView,
    WorkerMessagesResponse, WorkerStatusResponse, WorkerView,
)
from codex_worker.models import RpcFault
from codex_worker.service_domain import AttachView, MigrationState, MigrationStatusView


class CommandModelTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.cwd = self.tempdir.name

    def tearDown(self):
        self.tempdir.cleanup()

    @property
    def session_id(self):
        return "12345678-1234-5678-1234-567812345678"

    def test_worker_name_and_start_configuration_are_strict(self):
        with self.assertRaises(ValueError):
            StartWorkerRequest(name="bad name", prompt="x", cwd=self.cwd)
        with self.assertRaises(ValueError):
            StartWorkerRequest(name="a" * 129, prompt="x", cwd=self.cwd)
        request = StartWorkerRequest(name="review-a31", prompt="inspect", cwd=self.cwd)
        self.assertEqual(request.tier, Tier.MEDIUM)
        self.assertEqual(request.effort, "medium")
        self.assertEqual(request.access, AccessMode.FULL)

    def test_facade_fault_has_exact_machine_recovery_shape(self):
        fault = FacadeFault.worker_not_found("review-a31", "scope")
        self.assertEqual(fault.to_dict()["data"], {
            "kind": "worker_not_found", "retryable": False,
            "source": "codex-worker", "details": {},
            "known_ids": {"name": "review-a31",
                          "session_id": None, "thread_id": None, "turn_id": None},
            "next_actions": [{"command": "codex-worker start --help",
                              "reason": "Review required creation inputs for this absent worker"}],
        })

    def test_facade_fault_rejects_placeholder_recovery_commands(self):
        with self.assertRaisesRegex(ValueError, "literal"):
            FacadeFault(
                FacadeFaultCode.DAEMON_STOPPED, "stopped", "daemon_stopped",
                next_actions=[{
                    "command": "codex-worker run --name worker-a --prompt <text>",
                    "reason": "not runnable",
                }],
            )

    def test_global_service_command_models_and_fault_codes_are_strict(self):
        from codex_worker.commands import (
            FACADE_FAULT_KINDS, MigrationStatusRequest,
            ResolveLegacyConflictRequest, RestartServiceRequest,
            StartServiceRequest, StatusServiceRequest, StopServiceRequest,
        )
        expected = {
            FacadeFaultCode.ADDRESS_IN_USE: (-32039, "address_in_use"),
            FacadeFaultCode.SERVICE_BUSY: (-32040, "service_busy"),
            FacadeFaultCode.LEGACY_NAME_CONFLICT: (-32041, "legacy_name_conflict"),
            FacadeFaultCode.SERVICE_CONFIG_CONFLICT: (-32042, "service_config_conflict"),
        }
        for code, (number, kind) in expected.items():
            self.assertEqual((code.value, FACADE_FAULT_KINDS[code]), (number, kind))
            self.assertEqual(FacadeFault(code, "message", kind).kind, kind)
        models = (
            StartServiceRequest("ws://127.0.0.1:4500"),
            StatusServiceRequest(), StopServiceRequest(False),
            RestartServiceRequest(None, True), MigrationStatusRequest(),
            ResolveLegacyConflictRequest("legacy-a", "thread-a", None),
        )
        for model in models:
            self.assertEqual(type(model).from_dict(model.to_dict()), model)
            wire = model.to_dict(); wire["extra"] = True
            with self.assertRaises(ValueError):
                type(model).from_dict(wire)

    def test_service_status_projects_listener_attach_counts_and_migration(self):
        from codex_worker.commands import CountEvidence, MetricAvailability, ServiceStatusResponse
        from codex_worker.models import ActiveInventory, WorkerImpact
        migration = MigrationStatusView(MigrationState.COMPLETE, True, 0, 0, 0, [], [])
        workers = WorkerImpact(["active-a"], ["idle-b"])
        inventory = ActiveInventory()
        status = ServiceStatusResponse(
            "ready", "8.1.0", 10, 11, "ws://127.0.0.1:4500",
            "loopback", "none", "codex --remote ws://127.0.0.1:4500",
            CountEvidence(2, "codex-worker registry", MetricAvailability.DERIVED,
                          workers.to_dict()),
            CountEvidence(0, "codex app-server inventory", MetricAvailability.DERIVED,
                          inventory.to_dict()), migration.to_dict(), "preserved",
        )
        self.assertEqual(ServiceStatusResponse.from_dict(status.to_dict()), status)
        self.assertEqual(status.worker_count.value, 2)
        self.assertEqual(status.worker_count.basis["active_names"], ["active-a"])
        invalid = status.to_dict()
        for key, value in (
                ("status", "starting"), ("exposure", "unknown"),
                ("auth", "token"), ("durable_state", "lost"),
                ("attach_command", "codex --remote wrong"), ("pid", None)):
            with self.subTest(key=key):
                changed = dict(invalid); changed[key] = value
                with self.assertRaises(ValueError):
                    ServiceStatusResponse.from_dict(changed)

    def test_start_rejects_incompatible_policy_and_budget(self):
        with self.assertRaises(ValueError):
            StartWorkerRequest("review-a31", "x", self.cwd, model="gpt", tier=Tier.MEDIUM)
        with self.assertRaises(ValueError):
            StartWorkerRequest("review-a31", "x", self.cwd, goal=None, token_budget=1)

    def test_start_requires_exactly_one_tier_or_raw_model_selection(self):
        defaulted = StartWorkerRequest("review-a31", "x", self.cwd)
        self.assertEqual((defaulted.tier, defaulted.model), (Tier.MEDIUM, None))
        raw = StartWorkerRequest("review-raw", "x", self.cwd, tier=None, model="raw-model")
        self.assertEqual((raw.tier, raw.model), (None, "raw-model"))
        with self.assertRaisesRegex(ValueError, "exactly one of tier or model"):
            StartWorkerRequest("review-none", "x", self.cwd, tier=None, model=None)
        invalid_wire = defaulted.to_dict()
        invalid_wire["tier"] = None
        invalid_wire["model"] = None
        with self.assertRaisesRegex(ValueError, "exactly one of tier or model"):
            StartWorkerRequest.from_dict(invalid_wire)
        invalid_wire["tier"] = Tier.MEDIUM.value
        invalid_wire["model"] = "raw-model"
        with self.assertRaisesRegex(ValueError, "exactly one of tier or model"):
            StartWorkerRequest.from_dict(invalid_wire)

    def test_start_config_is_optional_validated_creation_policy(self):
        request = StartWorkerRequest("search-a31", "x", self.cwd, config={"web_search": "live"})
        self.assertEqual(StartWorkerRequest.from_dict(request.to_dict()).config, {"web_search": "live"})
        for bad in ({}, {"": 1}, {"web_search": None}, ["web_search"]):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                StartWorkerRequest("search-a31", "x", self.cwd, config=bad)
        wire = StartWorkerRequest("search-a31", "x", self.cwd).to_dict()
        self.assertIsNone(wire["config"])
        wire.pop("config")
        self.assertIsNone(StartWorkerRequest.from_dict(wire).config)

    def test_worker_view_surfaces_config_and_reads_pre_config_wire(self):
        worker = WorkerView("search-a31", self.session_id, "thread", self.cwd, Tier.MEDIUM,
                            "model", "medium", AccessMode.READ_ONLY, None, {"web_search": "live"})
        self.assertEqual(worker.to_dict()["config"], {"web_search": "live"})
        self.assertEqual(WorkerView.from_dict(worker.to_dict()), worker)
        legacy = worker.to_dict()
        legacy.pop("config")
        self.assertIsNone(WorkerView.from_dict(legacy).config)
        legacy.pop("attach")
        self.assertIsNone(WorkerView.from_dict(legacy).config)
        with self.assertRaises(ValueError):
            WorkerView("search-a31", self.session_id, "thread", self.cwd, Tier.MEDIUM,
                       "model", "medium", AccessMode.FULL, None, {})

    def test_callback_contracts_are_strict_and_keep_capture_secret(self):
        capture = CallbackCapture(
            target_socket="/tmp/cc-socks/123.sock", child_token="a" * 32,
            claude_session_id="session-1", claude_pid=123,
            claude_proc_start="measured-start", claude_config_dir="/tmp/claude-config",
        )
        root_only = CallbackCapture(None, None, None, None, None, "/tmp/claude-config")
        for model in (capture, root_only):
            self.assertEqual(type(model).from_dict(model.to_dict()).to_dict(), model.to_dict())
            wire = model.to_dict()
            wire["extra"] = "forbidden"
            with self.assertRaises(ValueError):
                type(model).from_dict(wire)
        for partial in (
            ("/tmp/cc-socks/123.sock", None, None, None, None, "/tmp/claude-config"),
            (None, "a" * 32, None, None, None, "/tmp/claude-config"),
        ):
            with self.assertRaises(ValueError):
                CallbackCapture(*partial)
        for token in ("A" * 32, "a" * 31, "a" * 33):
            with self.assertRaises(ValueError):
                CallbackCapture("/tmp/cc-socks/123.sock", token, "session-1", 123,
                                "measured-start", "/tmp/claude-config")

        start = StartWorkerRequest("review-a31", "x", self.cwd, callback_capture=capture)
        self.assertEqual(StartWorkerRequest.from_dict(start.to_dict()).to_dict(), start.to_dict())
        with self.assertRaises(ValueError):
            StartWorkerRequest("review-a31", "x", self.cwd, no_callback=True, callback_capture=capture)

        request = MessageWorkerRequest("review-a31", "notify", MessagePriority.NEXT, None)
        self.assertEqual(MessageWorkerRequest.from_dict(request.to_dict()).to_dict(), request.to_dict())
        with self.assertRaises(ValueError):
            MessageWorkerRequest("review-a31", "", MessagePriority.NEXT, None)
        with self.assertRaises(ValueError):
            MessageWorkerRequest.from_dict({"name": "review-a31", "message": "notify", "priority": "urgent", "cc_agent_name": None})

        worker = WorkerView("review-a31", self.session_id, "thread", self.cwd,
                            Tier.MEDIUM, "model", "medium", AccessMode.FULL)
        attempt = CallbackAttemptView("event-1", CallbackAttemptState.WRITTEN, None,
                                      "2026-08-20T00:00:00Z", 1, "turn-1")
        status = CallbackStatusView(CallbackState.ENABLED, 0, attempt)
        response = CallbackSendResponse(worker, "event-1", attempt)
        worker_status = WorkerStatusResponse(worker, "ready", True, None, None, status)
        for model in (start, request, attempt, status, response, worker_status):
            self.assertEqual(type(model).from_dict(model.to_dict()).to_dict(), model.to_dict())
            wire = model.to_dict()
            wire["extra"] = "forbidden"
            with self.assertRaises(ValueError):
                type(model).from_dict(wire)
        self.assertEqual(attempt.to_dict()["turn_id"], "turn-1")
        legacy_attempt = attempt.to_dict()
        legacy_attempt.pop("turn_id")
        self.assertIsNone(CallbackAttemptView.from_dict(legacy_attempt).turn_id)
        public_wire = worker_status.to_dict()
        forbidden = {"target_socket", "child_token", "claude_session_id", "claude_pid", "claude_proc_start", "claude_config_dir"}
        self.assertFalse(forbidden.intersection(public_wire["callback"]))
        self.assertFalse(forbidden.intersection(response.to_dict()))

        expected_faults = {
            FacadeFaultCode.CALLBACK_UNAVAILABLE: (-32031, "callback_unavailable"),
            FacadeFaultCode.CALLBACK_TARGET_STALE: (-32032, "callback_target_stale"),
            FacadeFaultCode.CALLBACK_TARGET_NOT_FOUND: (-32033, "callback_target_not_found"),
            FacadeFaultCode.CALLBACK_TARGET_AMBIGUOUS: (-32034, "callback_target_ambiguous"),
            FacadeFaultCode.CALLBACK_TARGET_UNSAFE: (-32035, "callback_target_unsafe"),
            FacadeFaultCode.CALLBACK_SEND_FAILED: (-32036, "callback_send_failed"),
            FacadeFaultCode.CALLBACK_PAYLOAD_TOO_LARGE: (-32037, "callback_payload_too_large"),
        }
        for code, (number, kind) in expected_faults.items():
            self.assertEqual(code.value, number)
            self.assertEqual(FacadeFault(code, "message", kind).to_dict()["data"]["kind"], kind)

    def test_response_models_recursively_reject_bad_shapes_and_round_trip(self):
        worker = WorkerView("review-a31", self.session_id, "thread", self.cwd,
                            Tier.MEDIUM, "model", "medium", AccessMode.FULL)
        response = CompletionResponse(
            worker, TurnView("turn", "completed", None),
            [AgentMessageView("agent_message", "item", "final_answer", CompletionSelection.EXPLICIT_FINAL, "done")],
            None, {"wall_time_ms": MetricEvidence(1, "codex-worker", MetricAvailability.MEASURED)},
            RecoveryView("status", "messages", "interrupt"),
        )
        self.assertEqual(CompletionResponse.from_dict(response.to_dict()).to_dict(), response.to_dict())
        invalid = response.to_dict()
        invalid["worker"]["access"] = "unsafe"
        with self.assertRaises(ValueError):
            CompletionResponse.from_dict(invalid)
        with self.assertRaises(ValueError):
            WorkerView("bad name", self.session_id, "thread", self.cwd,
                       Tier.MEDIUM, "model", "medium", AccessMode.FULL)

    def test_fault_rejects_unknown_codes_and_malformed_wire_envelopes(self):
        with self.assertRaises(ValueError):
            FacadeFault(-32099, "no", "worker_not_found")
        fault = FacadeFault.worker_not_found("review-a31", "scope")
        self.assertEqual(FacadeFault.from_dict(fault.to_dict()).to_dict(), fault.to_dict())
        malformed = fault.to_dict()
        malformed["data"]["known_ids"]["extra"] = "no"
        with self.assertRaises(ValueError):
            FacadeFault.from_dict(malformed)

    def test_response_values_reject_closed_literals_and_boundary_counts(self):
        worker = WorkerView("review-a31", self.session_id, "thread", self.cwd,
                            Tier.MEDIUM, "model", "medium", AccessMode.FULL)
        with self.assertRaises(ValueError):
            TurnView("turn", "unknown", None)
        with self.assertRaises(ValueError):
            AgentMessageView("other", "item", None, CompletionSelection.LIVE, "text")
        with self.assertRaises(ValueError):
            MetricEvidence(None, "", MetricAvailability.UNAVAILABLE)
        with self.assertRaises(ValueError):
            WorkerMessagesResponse(worker, [], 1, -1, False, None)

    def test_worker_view_requires_uuid_session_id_on_construction_and_wire(self):
        with self.assertRaises(ValueError):
            WorkerView("review-a31", "not-a-uuid", "thread", self.cwd,
                       Tier.MEDIUM, "model", "medium", AccessMode.FULL)
        valid = WorkerView("review-a31", self.session_id, "thread", self.cwd,
                           Tier.MEDIUM, "model", "medium", AccessMode.FULL).to_dict()
        valid["session_id"] = "not-a-uuid"
        with self.assertRaises(ValueError):
            WorkerView.from_dict(valid)

    def test_every_common_fault_code_has_only_its_exact_kind(self):
        expected = {
            FacadeFaultCode.INVALID_PARAMS: "invalid_params",
            FacadeFaultCode.TURN_ACTIVE: "turn_active",
            FacadeFaultCode.TURN_NOT_ACTIVE: "turn_not_active",
            FacadeFaultCode.REGISTRY_ERROR: "registry_error",
            FacadeFaultCode.CODEX_PROTOCOL_ERROR: "codex_protocol_error",
            FacadeFaultCode.CODEX_FAILURE: "codex_failure",
            FacadeFaultCode.WORKER_NAME_EXISTS: "worker_name_exists",
            FacadeFaultCode.WORKER_NOT_FOUND: "worker_not_found",
            FacadeFaultCode.DAEMON_STOPPED: "daemon_stopped",
            FacadeFaultCode.DAEMON_START_FAILED: "daemon_start_failed",
            FacadeFaultCode.TIMEOUT_ACTIVE: "timeout_active",
            FacadeFaultCode.MODEL_UNAVAILABLE: "model_unavailable",
            FacadeFaultCode.EFFORT_UNSUPPORTED: "effort_unsupported",
            FacadeFaultCode.LIMITS_UNAVAILABLE: "limits_unavailable",
            FacadeFaultCode.INCOMPLETE_COMPLETION: "incomplete_completion",
            FacadeFaultCode.DAEMON_STOP_FAILED: "daemon_stop_failed",
        }
        for code, kind in expected.items():
            self.assertEqual(FacadeFault(code, "message", kind).to_dict()["data"]["kind"], kind)
            with self.assertRaises(ValueError):
                FacadeFault(code, "message", "worker_not_found" if kind != "worker_not_found" else "daemon_stopped")
            wire = FacadeFault(code, "message", kind).to_dict()
            wire["data"]["kind"] = "worker_not_found" if kind != "worker_not_found" else "daemon_stopped"
            with self.assertRaises(ValueError):
                FacadeFault.from_dict(wire)


class TypedFaultExceptionStateTests(unittest.TestCase):
    """Python >= 3.11 contextlib/unittest assign exception state from Python code."""

    @staticmethod
    def faults():
        return [RpcFault(-32602, "Invalid params", "invalid_params"),
                FacadeFault(FacadeFaultCode.INVALID_PARAMS, "Invalid params", "invalid_params")]

    def test_typed_faults_accept_the_exception_state_python_writes(self):
        for fault in self.faults():
            with self.subTest(fault=type(fault).__name__):
                cause = ValueError("cause")
                fault.__traceback__ = None
                fault.__cause__ = cause
                fault.__context__ = cause
                fault.__suppress_context__ = True
                fault.__notes__ = ["note"]
                self.assertIs(fault.__cause__, cause)
                self.assertIs(fault.__context__, cause)
                self.assertTrue(fault.__suppress_context__)
                self.assertEqual(fault.__notes__, ["note"])

    def test_typed_faults_keep_their_fields_frozen(self):
        for fault in self.faults():
            for name in ("message", "kind", "undeclared"):
                with self.subTest(fault=type(fault).__name__, name=name):
                    with self.assertRaises(FrozenInstanceError):
                        setattr(fault, name, "changed")
            self.assertEqual(fault.message, "Invalid params")

    def test_typed_faults_propagate_unchanged_through_context_managers(self):
        @contextlib.contextmanager
        def guarded():
            yield

        for fault in self.faults():
            with self.subTest(fault=type(fault).__name__):
                with self.assertRaises(type(fault)) as caught:
                    with guarded():
                        raise fault
                self.assertIs(caught.exception, fault)


if __name__ == "__main__":
    unittest.main()
