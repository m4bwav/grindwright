import pathlib
import re
import unittest

SKILL = pathlib.Path(__file__).resolve().parents[1] / "skills" / "grindwright"


class ReferenceLinks(unittest.TestCase):
    def test_every_skill_link_resolves(self):
        text = (SKILL / "SKILL.md").read_text(encoding="utf-8")
        for target in re.findall(r"\]\((references/[^)#]+)", text):
            self.assertTrue((SKILL / target).is_file(), target)

    def test_game_systems_reference(self):
        text = (SKILL / "references" / "game-systems.md").read_text(encoding="utf-8")
        self.assertIn("references/game-systems.md", (SKILL / "SKILL.md").read_text(encoding="utf-8"))
        for needle in (".bad", "host", "version", "end_turn", "Cap model calls"):
            self.assertIn(needle, text)
        self.assertNotIn("\u2014", text)


if __name__ == "__main__":
    unittest.main()
