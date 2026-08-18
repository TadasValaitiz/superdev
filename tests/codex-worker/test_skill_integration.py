import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SDD = ROOT / "skills" / "subagent-driven-development" / "SKILL.md"
REFERENCE = ROOT / "skills" / "subagent-driven-development" / "codex-worker.md"


class CodexWorkerSkillIntegrationTests(unittest.TestCase):
    def _reference(self):
        self.assertTrue(REFERENCE.is_file(), "Codex worker reference is missing")
        return " ".join(REFERENCE.read_text(encoding="utf-8").split()).replace("\\ ", "")

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

    def test_reference_preserves_canonical_sdd_status_tokens(self):
        text = REFERENCE.read_text(encoding="utf-8")
        for status in ("DONE", "DONE_WITH_CONCERNS", "NEEDS_CONTEXT", "BLOCKED"):
            with self.subTest(status=status):
                self.assertIn("`%s`" % status, text)

    def test_reference_requires_extracting_session_fields_from_json_envelopes(self):
        text = self._reference()
        for field in (".result.session.session_id", ".result.session.thread_id"):
            with self.subTest(field=field):
                self.assertIn(field, text)
        self.assertIn("For every `session start` and `session resume` response", text)
        self.assertIn("Do not assign the whole JSON response", text)
        self.assertNotIn("A_SESSION=$(codex-worker", text)

    def test_operator_sequence_keeps_daemon_health_and_model_discovery_order(self):
        text = self._reference()
        sequence = (
            'codex-worker --socket "$SOCKET" daemon serve --state "$STATE" '
            'codex-worker --socket "$SOCKET" daemon status '
            'codex-worker --socket "$SOCKET" model list'
        )
        self.assertIn(sequence, text)

    def test_operator_sequence_connects_extracted_session_id_to_turn(self):
        text = self._reference()
        self.assertIn(
            'codex-worker --socket "$SOCKET" session start --cwd '
            '"$IMPLEMENTER_WORKTREE" --name implementer --model "$MODEL"',
            text,
        )
        self.assertIn(
            '`.result.session.session_id` and `.result.session.thread_id` and retain '
            'those values before running later commands',
            text,
        )
        self.assertIn(
            'codex-worker --socket "$SOCKET" turn start --session "$SESSION_UUID"',
            text,
        )

    def test_response_semantics_distinguish_wait_error_from_terminal_results(self):
        text = self._reference().lower()
        for fragment in (
            'a `turn wait` timeout exits 1',
            '.error.data.kind == "wait_timeout"',
            'a successful terminal `turn wait` returns `.result.turn.status`',
            '`turn status` reports a latest terminal state at `.result.latest_turn.status`',
            '.result.turn.status == "interrupted"',
            '.result.latest_turn.status == "interrupted"',
        ):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, text)

    def test_recovery_and_role_sequences_preserve_identity_and_handoffs(self):
        text = self._reference()
        self.assertIn(
            'codex-worker --socket "$SOCKET" session resume --session "$SESSION_UUID"',
            text,
        )
        self.assertIn(
            'codex-worker --socket "$SOCKET" session resume --thread "$THREAD_ID" '
            '--name recovered-implementer',
            text,
        )
        self.assertIn("each implementer and reviewer a distinct session and worktree", text)
        self.assertIn(
            "provide the task brief, collect the worker's report, and generate/pass "
            "the review-package file",
            text,
        )

    def test_reference_distinguishes_wait_timeout_from_interrupted_terminal_state(self):
        text = self._reference().lower()
        for fragment in (
            "wait_timeout",
            '.result.turn.status == "interrupted"',
            '.result.latest_turn.status == "interrupted"',
            "terminal/incomplete",
            "needs_context",
            "done_with_concerns",
            "never treat an interrupted turn as merely a wait failure",
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
