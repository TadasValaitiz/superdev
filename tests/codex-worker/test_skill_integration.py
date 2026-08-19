import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SDD = ROOT / "skills" / "subagent-driven-development" / "SKILL.md"
OPERATOR = ROOT / "skills" / "subagent-driven-development" / "codex-worker.md"
MODEL_POLICY = ROOT / "skills" / "subagent-driven-development" / "codex-model-selection.md"
CODEX_TOOLS = ROOT / "skills" / "using-superdev" / "references" / "codex-tools.md"


class CodexWorkerSkillIntegrationTests(unittest.TestCase):
    def test_sdd_dispatch_keeps_native_claude_and_named_worker_happy_path(self):
        text = SDD.read_text(encoding="utf-8").lower()
        self.assertIn("collision-resistant", text)
        self.assertIn("`start`", text)
        self.assertIn("`run`", text)
        self.assertIn("native claude", text)
        self.assertIn("codex is opt-in", text)
        self.assertNotIn("daemon ensure", text)

    def test_operator_reference_links_appendix_and_covers_common_surface(self):
        text = OPERATOR.read_text(encoding="utf-8").lower()
        for fragment in (
            "codex-worker start --name implement-a31 --prompt-file task.md",
            "codex-worker run --name implement-a31 --prompt \"run the focused gate and report.\"",
            "collision-resistant",
            "full access",
            "read-only",
            "goal",
            "output-schema",
            "status",
            "messages",
            "steer",
            "interrupt",
            "daemon stop",
            "technical appendix",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)
        self.assertNotIn("daemon ensure", text)

    def test_technical_appendix_covers_recovery_and_policy_boundaries(self):
        text = OPERATOR.read_text(encoding="utf-8").lower()
        for fragment in (
            "goal",
            "history",
            "limits",
            "stop",
            "timeout",
            "--instance",
            "codex_worker_instance",
            "claude_code_session_id",
            "full access",
            "read-only",
            "raw recovery",
            "model policy",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)
        self.assertIn("no setting inherits effort from\n`claude_effort`", text)

    def test_model_policy_keeps_two_tiers_and_medium_default_effort(self):
        text = MODEL_POLICY.read_text(encoding="utf-8").lower()
        for fragment in (
            "`medium` | `gpt-5.6-terra`",
            "`very-smart` | `gpt-5.6-sol`",
            "default effort is `medium`",
            "never inherits from `claude_effort`",
            "never silently\nfall back or substitute",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_codex_harness_routing_remains_separate_from_claude_worker_routing(self):
        text = " ".join(CODEX_TOOLS.read_text(encoding="utf-8").split()).lower()
        for fragment in (
            "native codex-harness dispatch",
            "not the local broker from claude code",
            "does not start or require the broker",
            "does not change native claude routing/main-session design",
            "codex is opt-in",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)


if __name__ == "__main__":
    unittest.main()
