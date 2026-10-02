import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SDD = ROOT / "skills" / "subagent-driven-development" / "SKILL.md"
REFERENCE = ROOT / "skills" / "subagent-driven-development" / "codex-worker.md"
INSTALLER = ROOT / "skills" / "subagent-driven-development" / "scripts" / "install-codex-worker"
README = ROOT / "README.md"
MODEL_REFERENCE = ROOT / "skills" / "subagent-driven-development" / "codex-model-selection.md"
CODEX_TOOLS_REFERENCE = ROOT / "skills" / "using-superdev" / "references" / "codex-tools.md"
OPERATOR = REFERENCE
MODEL_POLICY = MODEL_REFERENCE
CODEX_TOOLS = CODEX_TOOLS_REFERENCE


class CodexWorkerSkillIntegrationTests(unittest.TestCase):
    def _reference(self):
        self.assertTrue(REFERENCE.is_file(), "Codex worker reference is missing")
        return " ".join(REFERENCE.read_text(encoding="utf-8").split())

    def test_sdd_links_codex_worker_reference(self):
        self.assertIn("[Codex worker broker](codex-worker.md)", SDD.read_text(encoding="utf-8"))

    def test_codex_selection_has_one_structural_preflight_before_short_dispatch(self):
        text = SDD.read_text(encoding="utf-8")
        installer = (
            '"$SUPERDEV_PLUGIN_ROOT/skills/subagent-driven-development/scripts/'
            'install-codex-worker"'
        )
        self.assertIn(installer, text)
        self.assertIn("codex-worker --version", text)
        self.assertLess(text.index(installer), text.index("codex-worker --version"))
        self.assertIn("&& codex-worker --version", " ".join(text.split()))
        self.assertLess(text.index("codex-worker --version"), text.index("Read [Codex worker broker]"))
        normalized = " ".join(text.split()).lower()
        for fragment in (
            "one successful trusted uv preflight per session",
            "failed attempt does not satisfy the preflight",
            "after success, do not rerun",
            "when codex is selected",
            "claude_plugin_root",
            "exact loaded `skill.md` path",
            "native claude-only work does not run this preflight",
            "never invoke the source launcher",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, normalized)

    def test_preflight_reference_keeps_lifecycle_optional_and_dispatch_short(self):
        text = REFERENCE.read_text(encoding="utf-8").lower()
        for fragment in (
            "uv tool install --reinstall",
            "local checkout",
            "git url",
            "future registry",
            "uv tool upgrade codex-worker",
            "uv tool list",
            "uv tool uninstall codex-worker",
            "uv tool update-shell",
            "never invoke the source launcher",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)
        start_section = text.index("## start, then continue")
        self.assertNotIn("scripts/codex-worker", text[start_section:])
        self.assertIn("codex-worker start --name", text[start_section:])

    def test_readme_makes_uv_and_external_codex_conditional_prerequisites(self):
        text = " ".join(README.read_text(encoding="utf-8").split()).lower()
        for fragment in (
            "when a codex worker is selected",
            "uv",
            "external `codex` cli",
            "native claude",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_reference_names_required_control_and_recovery_commands(self):
        text = self._reference()
        for fragment in ("model list", "turn start", "turn steer", "turn interrupt", "session resume"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_lifecycle_pressure_keeps_common_autostart_and_advanced_recovery(self):
        text = self._reference().lower()
        for fragment in ("start", "run", "daemon serve", "foreground", "model list", "live", "do not"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_role_pressure_separates_worktrees_and_reviewers(self):
        text = self._reference().lower()
        for fragment in ("distinct named conversation", "worktree", "implementer", "reviewer"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_handoff_pressure_preserves_sdd_artifacts_and_terminal_mapping(self):
        text = self._reference().lower()
        for fragment in ("task brief", "report", "review-package", "done", "done_with_concerns", "needs_context", "blocked"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_reference_preserves_canonical_sdd_status_tokens(self):
        text = REFERENCE.read_text(encoding="utf-8")
        for status in ("DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED"):
            with self.subTest(status=status):
                self.assertIn(f"`{status}`", text)

    def test_common_surface_uses_named_json_results_not_raw_session_extraction(self):
        text = self._reference()
        for fragment in ("exactly one JSON object", "result.worker", "result.messages", "start", "run"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_operator_sequence_keeps_start_then_run_order(self):
        text = self._reference()
        self.assertLess(
            text.index("codex-worker start --name implement-a31f --cwd /absolute/project --prompt-file task.md"),
            text.index('codex-worker run --name implement-a31f --prompt "Run the focused gate and report."'),
        )

    def test_operator_review_fan_out_assigns_each_start_its_own_worktree(self):
        text = self._reference()
        for worktree in ("$REVIEW_C_WORKTREE", "$REVIEW_D_WORKTREE", "$VERIFY_E_WORKTREE"):
            with self.subTest(worktree=worktree):
                self.assertIn(f'--cwd "{worktree}"', text)
        self.assertNotIn("(cd ", text)

    def test_response_semantics_distinguish_timeout_from_cancellation(self):
        text = self._reference().lower()
        for fragment in ("timeout is a local wait limit", "not cancellation", "status --name", "messages --name", "interrupt --name"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_recovery_and_role_sequences_preserve_identity_and_handoffs(self):
        text = self._reference()
        for fragment in ("session resume --thread <id>", "session resume --session <uuid>", "task brief", "report", "review-package"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_recovery_requires_terminal_turn_before_follow_up(self):
        text = self._reference().lower()
        for fragment in ("do not issue `run` until", "prior turn is terminal", "must not overlap an active old turn"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_recovery_pressure_covers_raw_thread_and_immutable_creation_context(self):
        text = self._reference().lower()
        for fragment in ("raw recovery", "thread", "retained", "cwd", "creation"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_brainstorming_pressure_keeps_design_in_main_session(self):
        text = SDD.read_text(encoding="utf-8").lower()
        self.assertIn("main-session brainstorming and design", text)

    def test_sdd_dispatch_keeps_native_claude_design_and_named_worker_happy_path(self):
        text = SDD.read_text(encoding="utf-8").lower()
        self.assertIn("collision-resistant", text)
        self.assertIn("`start`", text)
        self.assertIn("`run`", text)
        self.assertIn("native claude", text)
        self.assertIn("first-class implementer choice", text)
        self.assertIn("not the default", text)
        self.assertNotIn("daemon ensure", text)

    def test_operator_reference_links_appendix_and_covers_common_surface(self):
        text = OPERATOR.read_text(encoding="utf-8").lower()
        for fragment in (
            "codex-worker start --name implement-a31f --cwd /absolute/project --prompt-file task.md",
            "codex-worker run --name implement-a31f --prompt \"run the focused gate and report.\"",
            "collision-resistant",
            "full access",
            "read-only",
            "goal",
            "output-schema",
            "status",
            "messages",
            "steer",
            "interrupt",
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
            "claude_code_session_id",
            "full access",
            "read-only",
            "raw recovery",
            "model policy",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)
        self.assertIn("no setting inherits effort from\n`claude_effort`", text)

    def test_global_worker_workflow_is_explicit_and_reports_attach_handoff(self):
        text = self._reference()
        normalized = " ".join(text.split()).lower()
        for fragment in (
            "globally unique",
            "random suffix",
            "--cwd /absolute/project",
            "result.worker.session_id",
            "result.worker.thread_id",
            "result.worker.attach.resume_command",
            "exact controller resume command",
            "human attach (verbatim returned value)",
            "controller continuation",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, normalized)
        self.assertRegex(normalized, r"review-[a-f0-9]{4,}")

    def test_claude_environment_is_callback_only_and_never_selects_infrastructure(self):
        text = self._reference().lower()
        self.assertIn("callback-only", text)
        self.assertIn("does not select", text)
        self.assertIn("global service", text)
        self.assertIn("global lookup", text)
        self.assertIn("claude_plugin_root", text)
        self.assertIn("loaded package for trusted preflight", text)
        self.assertNotIn("claude session identity naturally selects", text)

    def test_skill_has_no_instance_examples_or_routine_shared_service_stop(self):
        skill = SDD.read_text(encoding="utf-8").lower()
        reference = REFERENCE.read_text(encoding="utf-8").lower()
        model = MODEL_REFERENCE.read_text(encoding="utf-8").lower()
        combined = "\n".join((skill, reference, model))
        self.assertNotIn("--instance", combined)
        self.assertNotIn("codex_worker_instance", combined)
        ordinary, marker, maintenance = reference.partition("## supervised machine-wide maintenance")
        self.assertEqual(marker, "## supervised machine-wide maintenance")
        self.assertNotIn("daemon stop", ordinary)
        self.assertNotIn("daemon restart", ordinary)
        self.assertIn("daemon stop", maintenance)
        self.assertIn("daemon restart", maintenance)
        self.assertIn("machine-wide", maintenance)
        self.assertIn("explicit human supervision", maintenance)
        self.assertIn("never cleanup", maintenance)
        self.assertNotIn("--force", ordinary)
        self.assertIn("never automated", maintenance)

    def test_model_policy_keeps_two_tiers_and_medium_default_effort(self):
        text = MODEL_POLICY.read_text(encoding="utf-8").lower()
        for fragment in (
            "`medium` | `gpt-6.1-sol`",
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

    def test_callback_guidance_keeps_global_nonblocking_semantics(self):
        reference = self._reference()
        skill = " ".join(SDD.read_text(encoding="utf-8").split())
        _, marker, remainder = reference.partition("## Callback guidance")
        self.assertEqual(marker, "## Callback guidance")
        callback, _, _ = remainder.partition("## Coordinate active work")
        callback_normalized = " ".join(callback.split())
        for fragment in (
            "codex-worker message --name <name>",
            "--message-file",
            "automatic terminal callback",
            "no-poll",
            "status/messages/history",
            "cc-agent-name",
            "one-send",
            "written",
            "delivered",
            "collision-resistant readable worker name",
            "random suffix avoids global clashes",
            "never pass or expose callback credentials",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, callback_normalized.lower())
        for fragment in ("continue", "does not pause", "does not wait"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, callback.lower())
        self.assertIn("first-class implementer choice beside native claude", skill.lower())
        self.assertIn("not the default", skill.lower())
        self.assertNotIn("callback token", callback.lower())
        self.assertNotIn("raw socket", callback.lower())
        self.assertNotIn("mcp", callback.lower())


class SddModelSelectionTests(unittest.TestCase):
    def test_core_skill_links_two_tier_codex_appendix_and_preserves_claude(self):
        text = SDD.read_text(encoding="utf-8")
        self.assertIn("[Codex model selection](codex-model-selection.md)", text)
        for fragment in ("`very smart`", "`medium`", "`opus`", "`sonnet`", "main-session brainstorming and design"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text.lower() if fragment.startswith("main-") else text)

    def test_codex_appendix_defines_explicit_two_tier_mappings(self):
        text = MODEL_REFERENCE.read_text(encoding="utf-8").lower()
        self.assertIn("`very smart` → `gpt-5.6-sol`", text)
        self.assertIn("`medium` → `gpt-6.1-sol`", text)

    def test_codex_appendix_requires_live_effort_validation_and_no_fallback(self):
        text = MODEL_REFERENCE.read_text(encoding="utf-8").lower()
        for fragment in ("model list", "supported_efforts", "independent", "block", "never silently", "codex-worker.md"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_codex_tools_reference_distinguishes_native_dispatch_from_broker(self):
        text = " ".join(CODEX_TOOLS_REFERENCE.read_text(encoding="utf-8").split()).lower()
        for fragment in ("native codex-harness dispatch", "not the local broker from claude code", "does not start or require the broker", "does not change native claude routing/main-session design", "../../subagent-driven-development/codex-model-selection.md"):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_active_routing_consumers_use_two_tier_vocabulary(self):
        consumers = (
            ROOT / "skills" / "brainstorming" / "SKILL.md",
            ROOT / "skills" / "brainstorming" / "spec-document-reviewer-prompt.md",
            ROOT / "skills" / "writing-plans" / "plan-document-reviewer-prompt.md",
            ROOT / "skills" / "requesting-code-review" / "code-reviewer.md",
            ROOT / "skills" / "finishing-a-development-branch" / "deviation-auditor-prompt.md",
            ROOT / "skills" / "cli-checkride" / "SKILL.md",
            ROOT / "skills" / "cli-checkride" / "evaluator-prompt.md",
            ROOT / "skills" / "cli-checkride" / "executor-prompt.md",
            ROOT / "skills" / "self-brainstorming" / "workflow-reference.md",
            CODEX_TOOLS_REFERENCE,
        )
        retired = ("most capable model", "standard model", "gpt-5.6-luna", "cheap, balanced, or frontier")
        for path in consumers:
            text = path.read_text(encoding="utf-8").lower()
            with self.subTest(path=str(path)):
                for phrase in retired:
                    self.assertNotIn(phrase, text)
                self.assertTrue("very smart" in text or "`medium`" in text)

    def test_self_brainstorm_workflow_pins_every_agent_role_to_native_tiers(self):
        text = " ".join((ROOT / "skills" / "self-brainstorming" / "workflow-reference.md").read_text(encoding="utf-8").split())
        for pin in (
            "{ schema: GROUND_SCHEMA, label: 'ground', model: 'sonnet' }",
            "{ schema: Q_SCHEMA, label: `q${round}`, phase: 'Dialogue', model: 'opus' }",
            "{ schema: A_SCHEMA, label: `a${round}`, phase: 'Dialogue', model: 'sonnet' }",
            "{ schema: PATHS_SCHEMA, label: 'synthesize', model: 'opus' }",
            "{ schema: REVIEW_SCHEMA, label: 'review', model: 'opus' }",
            "{ label: 'fix', model: 'opus' }",
            "{ schema: REVIEW_SCHEMA, label: 're-review', model: 'opus' }",
        ):
            with self.subTest(pin=pin):
                self.assertIn(pin, text)

    def test_self_brainstorm_inline_agent_fallback_pins_native_tiers(self):
        text = " ".join((ROOT / "skills" / "self-brainstorming" / "SKILL.md").read_text(encoding="utf-8").split()).lower()
        for fragment in (
            "inline with native claude agent calls",
            "grounding and responder to `sonnet` (`medium`)",
            "questioner, synthesis, review, fix, and re-review to `opus` (`very smart`)",
            "no codex substitution",
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)


if __name__ == "__main__":
    unittest.main()
