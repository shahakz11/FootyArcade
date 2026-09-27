"""
tests/test_played_with_dataset.py — Unit & Integrity Tests for Played With Game
================================================================================
"""

import os
import csv
import json
import unittest

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'daily_played_with_games.csv')


class TestPlayedWithDataset(unittest.TestCase):

    def test_dataset_exists(self):
        self.assertTrue(os.path.exists(CSV_PATH), f"{CSV_PATH} does not exist")

    def test_puzzle_count_and_steps(self):
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 365 * 5, f"Expected 1825 rows, got {len(rows)}")

        puzzles = {}
        for r in rows:
            gday = int(r['game_day'])
            if gday not in puzzles:
                puzzles[gday] = []
            puzzles[gday].append(r)

        self.assertEqual(len(puzzles), 365, f"Expected 365 puzzles, got {len(puzzles)}")

        for gday, steps in puzzles.items():
            self.assertEqual(len(steps), 5, f"Puzzle #{gday} must have exactly 5 steps")
            
            # Verify step numbering 1..5
            step_nums = [int(s['step_number']) for s in steps]
            self.assertEqual(step_nums, [1, 2, 3, 4, 5], f"Puzzle #{gday} steps not 1..5")

            # Verify mystery player peak value >= 30,000,000
            first = steps[0]
            peak_val = int(first['mystery_peak_value'])
            self.assertGreaterEqual(peak_val, 30_000_000, f"Puzzle #{gday} mystery player {first['mystery_player']} peak value {peak_val} < 30M")

            # Verify appearance count is strictly non-decreasing: C1 <= C2 <= C3 <= C4 <= C5
            apps = [int(s['appearances_together']) for s in steps]
            for i in range(len(apps) - 1):
                self.assertLessEqual(apps[i], apps[i + 1], f"Puzzle #{gday} appearances not non-decreasing: {apps}")
            self.assertLess(apps[0], apps[4], f"Puzzle #{gday} Clue 1 ({apps[0]}) must be strictly less than Clue 5 ({apps[4]})")

            # Verify all 5 teammates in a puzzle are distinct
            tm_ids = [s['teammate_id'] for s in steps]
            self.assertEqual(len(set(tm_ids)), 5, f"Puzzle #{gday} contains duplicate teammates: {tm_ids}")

            # Verify mystery player is not one of their own teammates
            self.assertNotIn(first['mystery_id'], tm_ids, f"Puzzle #{gday} mystery player in teammates list")


if __name__ == '__main__':
    unittest.main()
