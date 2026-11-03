"""
tests/test_this_and_that_dataset.py — Verification Suite for This & That Dataset
================================================================================
Validates:
1. Existence and integrity of daily_this_and_that_games.csv
2. Exactly 180 continuous daily puzzles
3. Solution pool Goldilocks sizing (4 to 9 players per challenge)
4. Autocomplete solvability whitelist compliance against all_players.json
5. No duplicates, empty strings, or invalid JSON payloads
"""

import os
import json
import csv
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestThisAndThatDataset(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.csv_path = os.path.join(PROJECT_ROOT, "daily_this_and_that_games.csv")
        cls.all_players_path = os.path.join(PROJECT_ROOT, "all_players.json")

        with open(cls.all_players_path, "r", encoding="utf-8") as f:
            players_data = json.load(f)
        cls.whitelist = set(p["Name"] for p in players_data)

        cls.rows = []
        if os.path.exists(cls.csv_path):
            with open(cls.csv_path, "r", encoding="utf-8") as f:
                cls.rows = list(csv.DictReader(f))

    def test_file_exists_and_populated(self):
        """Verify the CSV file exists and has records."""
        self.assertTrue(os.path.exists(self.csv_path), "daily_this_and_that_games.csv does not exist")
        self.assertGreater(len(self.rows), 0, "daily_this_and_that_games.csv is empty")

    def test_continuous_180_days(self):
        """Verify exactly 180 continuous daily puzzles (game_day 1 to 180)."""
        self.assertEqual(len(self.rows), 180, f"Expected 180 puzzles, found {len(self.rows)}")
        days = [int(r["game_day"]) for r in self.rows]
        self.assertEqual(days, list(range(1, 181)), "game_day sequence is not continuous 1..180")

    def test_goldilocks_pool_sizing(self):
        """Verify every challenge has between 4 and 9 answers."""
        for r in self.rows:
            day = r["game_day"]
            total = int(r["total_answers"])
            self.assertGreaterEqual(
                total, 4,
                f"Day {day} has fewer than 4 answers ({total})"
            )
            self.assertLessEqual(
                total, 9,
                f"Day {day} has more than 9 answers ({total})"
            )

    def test_statements_and_translations(self):
        """Verify statements are non-empty and have both English and Spanish."""
        for r in self.rows:
            day = r["game_day"]
            self.assertTrue(r["statement_a"].strip(), f"Day {day} has empty statement_a")
            self.assertTrue(r["statement_b"].strip(), f"Day {day} has empty statement_b")
            self.assertTrue(r["statement_a_es"].strip(), f"Day {day} has empty statement_a_es")
            self.assertTrue(r["statement_b_es"].strip(), f"Day {day} has empty statement_b_es")

    def test_all_answers_in_whitelist(self):
        """Verify every answer in answer_names exists in all_players.json for autocomplete."""
        for r in self.rows:
            day = r["game_day"]
            names = json.loads(r["answer_names"])
            self.assertEqual(
                len(names), int(r["total_answers"]),
                f"Day {day}: answer_names count does not match total_answers"
            )
            # Ensure no duplicates within puzzle
            self.assertEqual(
                len(names), len(set(names)),
                f"Day {day}: contains duplicate answers: {names}"
            )
            for name in names:
                self.assertIn(
                    name, self.whitelist,
                    f"Day {day}: player '{name}' is missing from all_players.json whitelist"
                )

    def test_answer_details_schema(self):
        """Verify answer_details JSON array structure."""
        for r in self.rows:
            day = r["game_day"]
            details = json.loads(r["answer_details"])
            self.assertEqual(
                len(details), int(r["total_answers"]),
                f"Day {day}: answer_details count does not match total_answers"
            )
            for d in details:
                self.assertIn("name", d)
                self.assertTrue(d["name"])
                self.assertIn("nationality", d)
                self.assertIn("position", d)


if __name__ == "__main__":
    unittest.main()
