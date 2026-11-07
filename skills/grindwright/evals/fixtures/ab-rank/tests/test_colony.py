import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "game"))
import colony


class Smoke(unittest.TestCase):
    def test_new_game(self):
        self.assertEqual(colony.new_game()["turn"], 1)


if __name__ == "__main__":
    unittest.main()
