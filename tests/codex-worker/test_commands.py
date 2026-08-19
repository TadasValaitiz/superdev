import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.commands import (
    AccessMode, AgentMessageView, CompletionResponse, CompletionSelection, FacadeFault, FacadeFaultCode,
    MetricAvailability, MetricEvidence, RecoveryView, StartWorkerRequest, Tier, TurnView,
    WorkerMessagesResponse, WorkerView,
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
