import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.commands import (
    AccessMode, AgentMessageView, CompletionResponse, CompletionSelection, FacadeFault, FacadeFaultCode,
    CallbackAttemptState, CallbackAttemptView, CallbackCapture, CallbackSendResponse,
    CallbackState, CallbackStatusView, MessagePriority, MessageWorkerRequest,
    MetricAvailability, MetricEvidence, RecoveryView, StartWorkerRequest, Tier, TurnView,
    WorkerMessagesResponse, WorkerStatusResponse, WorkerView,
)


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
            "known_ids": {"instance": "scope", "name": "review-a31",
                          "session_id": None, "thread_id": None, "turn_id": None},
            "next_actions": [{"command": "codex-worker start --name review-a31",
                              "reason": "Create this worker in the selected instance"}],
        })

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

        worker = WorkerView("scope", "review-a31", self.session_id, "thread", self.cwd,
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
        worker = WorkerView("scope", "review-a31", self.session_id, "thread", self.cwd,
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
            WorkerView("scope", "bad name", self.session_id, "thread", self.cwd,
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
        worker = WorkerView("scope", "review-a31", self.session_id, "thread", self.cwd,
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
            WorkerView("scope", "review-a31", "not-a-uuid", "thread", self.cwd,
                       Tier.MEDIUM, "model", "medium", AccessMode.FULL)
        valid = WorkerView("scope", "review-a31", self.session_id, "thread", self.cwd,
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


if __name__ == "__main__":
    unittest.main()
