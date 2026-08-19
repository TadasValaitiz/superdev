import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.commands import AccessMode, FacadeFault, StartWorkerRequest, Tier


class CommandModelTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.cwd = self.tempdir.name

    def tearDown(self):
        self.tempdir.cleanup()

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


if __name__ == "__main__":
    unittest.main()
