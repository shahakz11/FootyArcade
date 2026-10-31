"""
tests/test_anyone_but_dataset.py — Unit & Integrity Tests for Anyone But Game
=============================================================================
"""

import os
import csv
import json
import unittest

CSV_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'daily_anyone_but_games.csv')


class TestAnyoneButDataset(unittest.TestCase):

    def test_dataset_exists(self):
        self.assertTrue(os.path.exists(CSV_PATH), f"{CSV_PATH} does not exist")

    def test_puzzle_count_and_tables(self):
        with open(CSV_PATH, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 180 * 3, f"Expected 540 rows, got {len(rows)}")

        puzzles = {}
        for r in rows:
            gday = int(r['game_day'])
            if gday not in puzzles:
                puzzles[gday] = []
            puzzles[gday].append(r)

        self.assertEqual(len(puzzles), 180, f"Expected 180 puzzles, got {len(puzzles)}")

        for gday, tables in puzzles.items():
            self.assertEqual(len(tables), 3, f"Puzzle #{gday} must have exactly 3 tables")

            # Verify table numbering 1..3
            tbl_nums = [int(t['table_number']) for t in tables]
            self.assertEqual(tbl_nums, [1, 2, 3], f"Puzzle #{gday} table numbers not 1..3")

            excluded_name = tables[0]['excluded_player']
            self.assertTrue(bool(excluded_name), f"Puzzle #{gday} missing excluded player name")

            all_answers = []
            for t in tables:
                answers = json.loads(t['answers'])
                self.assertIsInstance(answers, list)
                self.assertGreaterEqual(len(answers), 3, f"Puzzle #{gday} table {t['table_number']} has < 3 answers")
                self.assertLessEqual(len(answers), 10, f"Puzzle #{gday} table {t['table_number']} has > 10 answers")
                self.assertEqual(len(answers), int(t['answer_count']))

                # Excluded player must NOT be in answers
                self.assertNotIn(
                    excluded_name.lower(),
                    [a.lower() for a in answers],
                    f"Puzzle #{gday} excluded player {excluded_name} is in table {t['table_number']} answers!"
                )
                all_answers.extend(answers)

            # Verify unique answers across the puzzle
            unique_answers = set(all_answers)
            self.assertGreaterEqual(
                len(unique_answers), 8,
                f"Puzzle #{gday} has only {len(unique_answers)} unique answers (< 8)"
            )
            self.assertLessEqual(
                len(unique_answers), 20,
                f"Puzzle #{gday} has {len(unique_answers)} unique answers (> 20)"
            )

    def test_fetch_daily_loader(self):
        import fetch_daily
        game_data, extra = fetch_daily.load_anyone_but(1)
        self.assertIsNotNone(game_data)
        self.assertEqual(game_data['excluded_player'], 'Bernardo Silva')
        self.assertEqual(len(game_data['tables']), 3)
        self.assertEqual(extra, {})


if __name__ == '__main__':
    unittest.main()
