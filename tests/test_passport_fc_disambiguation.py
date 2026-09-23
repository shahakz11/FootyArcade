"""
tests/test_passport_fc_disambiguation.py

Unit tests verifying:
1. Entity-level nationality isolation in Passport FC daily games dataset.
2. Pepe is strictly Portuguese (Real Madrid, Porto, Besiktas) and never Brazilian.
3. Kaká, Robinho, Fabinho, Roberto Carlos, and Danilo are strictly Brazilian and never Portuguese/Belgian.
4. Real Madrid Day 10 (Portugal) and Day 89 (Brazil) qualifying pools are 100% accurate.
5. Global consistency check across all 180 puzzles ensuring no cross-nation contamination.
"""

import os
import json
import csv
import unittest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CSV_PATH = os.path.join(ROOT_DIR, "daily_passport_fc_games.csv")


class TestPassportFCDisambiguation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.puzzles_by_day = {}
        with open(CSV_PATH, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                day = int(row["game_day"])
                if day not in cls.puzzles_by_day:
                    cls.puzzles_by_day[day] = []
                cls.puzzles_by_day[day].append(row)

    def test_day_10_real_madrid_portugal_qualifying_pool(self):
        """Verify Real Madrid Day 10 Portugal step contains Pepe and NO Brazilians."""
        day_rows = self.puzzles_by_day.get(10, [])
        self.assertTrue(day_rows, "Day 10 puzzle not found in daily_passport_fc_games.csv")
        
        portugal_step = next((r for r in day_rows if r["nationality"] == "Portugal"), None)
        self.assertIsNotNone(portugal_step, "Day 10 missing Portugal step")

        valid_players = json.loads(portugal_step["valid_players"])
        valid_lower = [p.lower() for p in valid_players]

        # Must include legitimate Portuguese players
        self.assertTrue(any("pepe" == p or "pêpê" == p for p in valid_lower), f"Pepe missing from Real Madrid Portugal pool: {valid_players}")
        self.assertTrue(any("cristiano ronaldo" in p for p in valid_lower), "Cristiano Ronaldo missing from Portugal pool")
        self.assertTrue(any("ricardo carvalho" in p for p in valid_lower), "Ricardo Carvalho missing from Portugal pool")

        # MUST NOT include Brazilian players who previously collided
        self.assertFalse(any("kaka" in p or "káká" in p or "kaká" in p for p in valid_lower), "Kaká erroneously found in Portugal pool")
        self.assertFalse(any("robinho" in p for p in valid_lower), "Robinho erroneously found in Portugal pool")
        self.assertFalse(any("fabinho" in p for p in valid_lower), "Fabinho erroneously found in Portugal pool")
        self.assertFalse(any("danilo" in p for p in valid_lower), "Danilo erroneously found in Portugal pool")
        self.assertFalse(any("roberto carlos" in p for p in valid_lower), "Roberto Carlos erroneously found in Portugal pool")

    def test_day_89_real_madrid_brazil_qualifying_pool(self):
        """Verify Real Madrid Day 89 Brazil step contains Brazilian icons and NO Pepe."""
        day_rows = self.puzzles_by_day.get(89, [])
        self.assertTrue(day_rows, "Day 89 puzzle not found in daily_passport_fc_games.csv")

        brazil_step = next((r for r in day_rows if r["nationality"] == "Brazil"), None)
        self.assertIsNotNone(brazil_step, "Day 89 missing Brazil step")

        valid_players = json.loads(brazil_step["valid_players"])
        valid_lower = [p.lower() for p in valid_players]

        # Must include Brazilian superstars
        self.assertTrue(any("kaka" in p or "kaká" in p for p in valid_lower), "Kaká missing from Real Madrid Brazil pool")
        self.assertTrue(any("robinho" in p for p in valid_lower), "Robinho missing from Real Madrid Brazil pool")
        self.assertTrue(any("fabinho" in p for p in valid_lower), "Fabinho missing from Real Madrid Brazil pool")
        self.assertTrue(any("danilo" in p for p in valid_lower), "Danilo missing from Real Madrid Brazil pool")
        self.assertTrue(any("roberto carlos" in p for p in valid_lower), "Roberto Carlos missing from Real Madrid Brazil pool")
        self.assertTrue(any("vinicius" in p for p in valid_lower), "Vinicius Junior missing from Real Madrid Brazil pool")
        self.assertTrue(any("casemiro" in p for p in valid_lower), "Casemiro missing from Real Madrid Brazil pool")

        # MUST NOT include Portuguese Pepe
        self.assertFalse(any(p == "pepe" for p in valid_lower), "Portuguese Pepe erroneously found in Brazil pool")

    def test_day_157_real_madrid_belgium_qualifying_pool(self):
        """Verify Day 157 Belgium step contains Courtois & Hazard and NOT Danilo."""
        day_rows = self.puzzles_by_day.get(157, [])
        self.assertTrue(day_rows, "Day 157 puzzle not found")

        belgium_step = next((r for r in day_rows if r["nationality"] == "Belgium"), None)
        self.assertIsNotNone(belgium_step, "Day 157 missing Belgium step")

        valid_players = json.loads(belgium_step["valid_players"])
        valid_lower = [p.lower() for p in valid_players]

        self.assertTrue(any("courtois" in p for p in valid_lower), "Courtois missing from Belgium step")
        self.assertTrue(any("hazard" in p for p in valid_lower), "Hazard missing from Belgium step")
        self.assertFalse(any("danilo" in p for p in valid_lower), "Danilo erroneously found in Belgium step")

    def test_global_no_cross_nationality_contamination(self):
        """Verify across all 180 days that known homonyms never leak into incorrect nationalities."""
        KNOWN_BRAZILIAN_NAMES = {"kaká", "kaka", "robinho", "fabinho", "roberto carlos", "ronaldinho", "rivaldo"}
        KNOWN_PORTUGUESE_NAMES = {"pepe", "luís figo", "luis figo", "ricardo carvalho", "fábio coentrão", "fabio coentrao"}

        for day, rows in self.puzzles_by_day.items():
            for r in rows:
                nat = r["nationality"]
                club = r["club"]
                valid_players = json.loads(r["valid_players"])
                valid_lower = {p.lower() for p in valid_players}

                # If nationality is NOT Brazil, no strictly Brazilian player should be in pool
                if nat != "Brazil":
                    for b_name in KNOWN_BRAZILIAN_NAMES:
                        self.assertNotIn(
                            b_name, valid_lower,
                            f"Cross-contamination: Brazilian player '{b_name}' found in {club} [{nat}] pool on Day {day}"
                        )

                # If nationality is NOT Portugal, no strictly Portuguese player should be in pool
                if nat != "Portugal":
                    for p_name in KNOWN_PORTUGUESE_NAMES:
                        self.assertNotIn(
                            p_name, valid_lower,
                            f"Cross-contamination: Portuguese player '{p_name}' found in {club} [{nat}] pool on Day {day}"
                        )


if __name__ == "__main__":
    unittest.main()
