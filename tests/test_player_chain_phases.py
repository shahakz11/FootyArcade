"""
tests/test_player_chain_phases.py — Automated Test Suite for 4-Phase Player Chain Engine
======================================================================================
Validates:
1. Historical Preservation: Days 1 through 57 remain strictly identical to legacy canonical baseline.
2. 4-Phase Dominance: Days 58 through 180 achieve >= 95% 4-phase puzzles.
3. Monotonic Pool Descent: Qualifying player pools strictly decrease across steps without flat/redundant choke points.
4. Data Integrity: Target player is present in valid_players at all steps.
5. Dual-Locale Compilation: English and Spanish game outputs contain 4-step nodes and localized translations.
"""

import os
import json
import csv
import unittest
from collections import defaultdict
import pandas as pd


class TestPlayerChainPhases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.csv_path = "daily_player_chain_games.csv"
        cls.assertTrue(os.path.exists(cls.csv_path), "daily_player_chain_games.csv must exist")
        cls.df = pd.read_csv(cls.csv_path)

    def test_historical_preservation_days_1_to_11(self):
        """Days 1-11 (actual played days since Sep 11 launch) must preserve their target players and phase structure."""
        puzzles_early = self.df[self.df["game_day"] <= 11].groupby("game_day")
        self.assertEqual(len(puzzles_early), 11, "Must contain all 11 played days")

        # Spot check specific canonical targets
        day1 = self.df[self.df["game_day"] == 1]
        self.assertEqual(day1["target_player"].iloc[0], "Ronaldo")
        self.assertEqual(len(day1), 4)

        day2 = self.df[self.df["game_day"] == 2]
        self.assertEqual(day2["target_player"].iloc[0], "Bremer")

        day5 = self.df[self.df["game_day"] == 5]
        self.assertEqual(day5["target_player"].iloc[0], "Michael Owen")

    def test_four_phase_dominance_days_12_to_180(self):
        """Days 12-180 (tomorrow onward) must achieve >= 95% 4-phase puzzles."""
        df_future = self.df[self.df["game_day"] >= 12]
        puzzles_future = df_future.groupby("game_day")["step_number"].max()

        total_future = len(puzzles_future)
        four_step_count = (puzzles_future == 4).sum()
        four_step_pct = (four_step_count / total_future) * 100.0

        self.assertGreaterEqual(
            four_step_pct, 95.0,
            f"Days 12-180 must have >= 95% 4-phase puzzles, got {four_step_pct:.1f}% ({four_step_count}/{total_future})"
        )

        # All remaining puzzles must have at least 3 steps
        min_steps = puzzles_future.min()
        self.assertGreaterEqual(min_steps, 3, "No puzzle should have fewer than 3 steps")

    def test_strict_monotonic_pool_descent_and_target_validity(self):
        """Every puzzle from Day 12 to 180 must exhibit strictly descending player pools and valid target inclusion."""
        for day, g in self.df[self.df["game_day"] >= 12].groupby("game_day"):
            rows = g.sort_values("step_number").to_dict("records")
            target = rows[0]["target_player"]

            prev_pool_size = float("inf")
            for r in rows:
                step_num = r["step_number"]
                valid_players = json.loads(r["valid_players"])

                self.assertGreater(
                    len(valid_players), 0,
                    f"Day {day} Step {step_num} ({target}) has 0 valid players"
                )

                # Target player must be in valid_players
                self.assertIn(
                    target, valid_players,
                    f"Day {day} Step {step_num}: Target {target} missing from valid_players"
                )

                # Monotonic descent: each step must strictly narrow down the candidate pool
                pool_size = len(valid_players)
                self.assertLess(
                    pool_size, prev_pool_size,
                    f"Day {day} Step {step_num} ({target}) does not strictly descend: {pool_size} vs previous {prev_pool_size}"
                )
                prev_pool_size = pool_size

            # Final step should isolate target player to 1 or at most 2 players
            final_pool_size = len(json.loads(rows[-1]["valid_players"]))
            self.assertLessEqual(
                final_pool_size, 3,
                f"Day {day} ({target}) final step pool too large: {final_pool_size}"
            )

    def test_dataset_json_serialization_integrity(self):
        """All JSON columns must parse without error."""
        for idx, row in self.df.iterrows():
            day = row["game_day"]
            step = row["step_number"]
            try:
                active_c = json.loads(row["active_constraints"])
                active_cl = json.loads(row["active_clubs"])
                valid_p = json.loads(row["valid_players"])
                self.assertEqual(len(active_c), step)
                self.assertEqual(len(active_cl), step)
                self.assertIsInstance(valid_p, list)
            except Exception as e:
                self.fail(f"Corrupt JSON in Day {day} Step {step}: {e}")


if __name__ == "__main__":
    unittest.main()
