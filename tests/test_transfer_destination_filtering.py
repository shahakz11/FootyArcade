import os
import sys
import csv
import unittest
import tempfile
import pandas as pd

# Add repo root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetch_daily import load_transfer_destination
from scripts.verify_daily_puzzles import PuzzleVerifier

class TestTransferDestinationFiltering(unittest.TestCase):
    def test_daily_destination_csv_has_no_same_club_transfers(self):
        """Verify that daily_destination_games.csv has 0 transfers where from_club_name == to_club_name."""
        csv_path = "daily_destination_games.csv"
        self.assertTrue(os.path.exists(csv_path), "daily_destination_games.csv should exist")
        
        df = pd.read_csv(csv_path)
        same_club = df[df['from_club_name'].str.strip().str.lower() == df['to_club_name'].str.strip().str.lower()]
        self.assertEqual(len(same_club), 0, f"Found {len(same_club)} same-club transfers in CSV: {same_club[['game_day', 'player_name', 'from_club_name', 'to_club_name']].to_dict('records')}")

    def test_all_180_days_have_at_least_two_transfers(self):
        """Verify that all 180 puzzle days have at least 2 distinct transfers."""
        df = pd.read_csv("daily_destination_games.csv")
        days = df['game_day'].unique()
        self.assertEqual(len(days), 180, f"Expected 180 days, found {len(days)}")
        
        counts = df.groupby('game_day').size()
        invalid_days = counts[counts < 2]
        self.assertEqual(len(invalid_days), 0, f"Days with < 2 transfers: {invalid_days.to_dict()}")

    def test_rafael_leao_puzzle_day_51_clean(self):
        """Verify that Day 51 (Rafael Leão) transfers are clean and realistic without youth/B-team self moves."""
        game_data, _ = load_transfer_destination(51)
        self.assertIsNotNone(game_data)
        self.assertIn("Rafael Leão", game_data["player_name"])
        
        # Check transfers
        transfers = game_data["transfers"]
        self.assertGreaterEqual(len(transfers), 2)
        for tr in transfers:
            self.assertNotEqual(
                tr["from_club_name"].strip().lower(),
                tr["to_club_name"].strip().lower(),
                f"Found self-transfer in Day 51: {tr}"
            )
        
        # Destination game runs reversed (most recent first):
        # Lille -> AC Milan, then Sporting CP -> Lille
        self.assertEqual(transfers[0]["from_club_name"], "Lille")
        self.assertEqual(transfers[0]["to_club_name"], "AC Milan")
        self.assertEqual(transfers[1]["from_club_name"], "Sporting CP")
        self.assertEqual(transfers[1]["to_club_name"], "Lille")

    def test_fetch_daily_defensively_filters_same_club(self):
        """Verify that load_transfer_destination skips identical from/to clubs even if present in CSV."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            sample_csv = os.path.join(tmp_dir, "daily_destination_games.csv")
            with open(sample_csv, "w", encoding="utf-8") as f:
                f.write(
                    "player_id,transfer_date,transfer_season,from_club_id,to_club_id,from_club_name,to_club_name,transfer_fee,market_value_in_eur,player_name,transfer_type,date_of_birth,country_of_citizenship,position,age_at_transfer,game_day,transfer_date_str\n"
                    "9999,2020-01-01,19/20,1,1,Sporting CP,Sporting CP,0.0,0.0,Test Player,Transfer,2000-01-01,Portugal,Attack,20.0,999,2020-01-01\n"
                    "9999,2021-01-01,20/21,1,2,Sporting CP,Lille,10000000.0,5000000.0,Test Player,Transfer,2000-01-01,Portugal,Attack,21.0,999,2021-01-01\n"
                    "9999,2022-01-01,21/22,2,3,Lille,AC Milan,20000000.0,15000000.0,Test Player,Transfer,2000-01-01,Portugal,Attack,22.0,999,2022-01-01\n"
                )
            
            orig_cwd = os.getcwd()
            try:
                os.chdir(tmp_dir)
                with open("all_clubs.json", "w", encoding="utf-8") as f:
                    f.write("[]")
                
                game_data, _ = load_transfer_destination(999)
                self.assertIsNotNone(game_data)
                self.assertEqual(len(game_data["transfers"]), 2)
                # transfers are reversed (recent first): Lille -> AC Milan, Sporting CP -> Lille
                self.assertEqual(game_data["transfers"][0]["from_club_name"], "Lille")
                self.assertEqual(game_data["transfers"][0]["to_club_name"], "AC Milan")
                self.assertEqual(game_data["transfers"][1]["from_club_name"], "Sporting CP")
                self.assertEqual(game_data["transfers"][1]["to_club_name"], "Lille")
            finally:
                os.chdir(orig_cwd)

    def test_verifier_audit_passes_clean_day(self):
        """Verify that PuzzleVerifier logs 0 issues for cleaned Day 51."""
        verifier = PuzzleVerifier()
        verifier.audit_transfer_destination(51)
        day51_issues = [i for i in verifier.issues if i["game_id"] == "transfer_destination" and i["puzzle_num"] == 51]
        self.assertEqual(len(day51_issues), 0, f"Unexpected issues in Day 51: {day51_issues}")

if __name__ == "__main__":
    unittest.main()
