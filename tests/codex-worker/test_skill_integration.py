import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SDD = ROOT / "skills" / "subagent-driven-development" / "SKILL.md"
REFERENCE = ROOT / "skills" / "subagent-driven-development" / "codex-worker.md"


class CodexWorkerSkillIntegrationTests(unittest.TestCase):
    def _reference(self):
        self.assertTrue(REFERENCE.is_file(), "Codex worker reference is missing")
        return " ".join(REFERENCE.read_text(encoding="utf-8").split())

    def test_sdd_links_codex_worker_reference(self):
        text = SDD.read_text(encoding="utf-8")
        self.assertIn("[Codex worker broker](codex-worker.md)", text)

    def test_reference_names_required_control_and_recovery_commands(self):
        text = self._reference()
        for fragment in (
            "model list",
            "turn start",
            "turn steer",
            "turn interrupt",
            "session resume",
            "turn wait",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_lifecycle_pressure_requires_explicit_daemon_and_live_model_discovery(self):
        text = self._reference().lower()
        self.assertIn("daemon serve", text)
        self.assertIn("foreground", text)
        self.assertIn("explicit", text)
        self.assertIn("model list", text)
        self.assertIn("live", text)
        self.assertIn("do not auto", text)

    def test_role_pressure_separates_sessions_worktrees_and_reviewers(self):
        text = self._reference().lower()
        for fragment in (
            "distinct session",
            "worktree",
            "implementer",
            "reviewer",
            "never reviews its own diff",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_handoff_pressure_preserves_sdd_artifacts_and_terminal_mapping(self):
        text = self._reference().lower()
        for fragment in (
            "task brief",
            "report",
            "review-package",
            "done",
            "done_with_concerns",
            "needs_context",
            "blocked",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_recovery_pressure_covers_uuid_raw_thread_and_immutable_cwd(self):
        text = self._reference().lower()
        for fragment in (
            "uuid",
            "raw thread",
            "retained",
            "immutable",
            "cwd",
            "cannot be retargeted",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_brainstorming_pressure_keeps_design_in_main_session(self):
        text = self._reference().lower()
        self.assertIn("brainstorm", text)
        self.assertIn("main session", text)


if __name__ == "__main__":
    unittest.main()
