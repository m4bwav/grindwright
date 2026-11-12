import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "skills" / "grindwright" / "scripts"))
import grind_index  # noqa: E402


class TokenwrightUse(unittest.TestCase):
    def test_counts_hook_note_and_agent_estimate(self):
        lines = [
            {"type": "attachment", "attachment": {"stdout": '{"additionalContext": "tokenwright: that Bash output was ~5367 tokens."}'}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "Bash", "input": {
                "command": 'python tw.py note --saved 8k --why "long log" --how "grep -n"'}}]}},
        ]
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "t.jsonl"
            p.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
            use = grind_index.tokenwright_use(p)
        self.assertEqual((use["hook_notes"], use["saved"], use["used"]), (1, 8000, 1))
        self.assertEqual(grind_index.tw_cell(use), "~8,000 saved")
        self.assertEqual(grind_index.tw_cell({"used": 0}), "no")


if __name__ == "__main__":
    unittest.main()
