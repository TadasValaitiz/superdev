import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "subagent-driven-development" / "scripts"))

from codex_worker.models import ItemRecord, SessionRecord, TurnSnapshot
from codex_worker.projection import select_completion_messages


class ProjectionTests(unittest.TestCase):
    def test_terminal_fallback_and_live_messages_preserve_nullable_phase(self):
        items = [
            ItemRecord("a", "agentMessage", {"text": "work"}),
            ItemRecord("b", "agentMessage", {"text": "answer"}),
        ]
        selected = select_completion_messages(items, terminal=True)
        self.assertEqual([(x.item_id, x.selection.value) for x in selected],
                         [("b", "terminal_fallback")])
        self.assertEqual([x.selection.value for x in select_completion_messages(items, terminal=False)],
                         ["live", "live"])

