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

    def test_edin_dzeko_day_55_clean_and_no_duplicates(self):
        """Verify that Day 55 (Edin Džeko) has clean sequential career progression without duplicate Fenerbahce/Fiorentina moves."""
        game_data, _ = load_transfer_destination(55)
        self.assertIsNotNone(game_data)
        self.assertIn("Edin Dzeko", game_data["player_name"])

        transfers = game_data["transfers"]
        self.assertGreaterEqual(len(transfers), 6)

        # In destination game, transfers are reversed (recent moves first)
        from_clubs = [t["from_club_name"] for t in transfers]
        to_clubs = [t["to_club_name"] for t in transfers]

        # Ensure no identical consecutive from_clubs
        for i in range(len(transfers) - 1):
            self.assertNotEqual(
                from_clubs[i].lower(),
                from_clubs[i + 1].lower(),
                f"Found consecutive duplicate guessing target '{from_clubs[i]}' in Day 55: {transfers}"
            )
            self.assertNotEqual(
                (from_clubs[i].lower(), to_clubs[i].lower()),
                (from_clubs[i + 1].lower(), to_clubs[i + 1].lower()),
                f"Found consecutive duplicate move in Day 55: {transfers[i]} vs {transfers[i+1]}"
            )

        # Verify key career clubs are present in sequence
        self.assertEqual(transfers[0]["to_club_name"], "FC Schalke 04")
        self.assertEqual(transfers[0]["from_club_name"], "Fiorentina")
        self.assertEqual(transfers[1]["to_club_name"], "Fiorentina")
        self.assertEqual(transfers[1]["from_club_name"], "Fenerbahce")
        self.assertEqual(transfers[2]["to_club_name"], "Fenerbahce")
        self.assertEqual(transfers[2]["from_club_name"], "Inter")

    def test_all_180_days_have_no_consecutive_duplicate_targets(self):
        """Verify that all 180 days have no consecutive duplicate target clubs or identical moves."""
        for day in range(1, 181):
            game_data, _ = load_transfer_destination(day)
            self.assertIsNotNone(game_data, f"Day {day} game data should not be None")
            transfers = game_data["transfers"]
            self.assertGreaterEqual(len(transfers), 2, f"Day {day} ({game_data['player_name']}) has < 2 transfers")

            for i in range(len(transfers)):
                tr = transfers[i]
                self.assertNotEqual(
                    tr["from_club_name"].strip().lower(),
                    tr["to_club_name"].strip().lower(),
                    f"Day {day} ({game_data['player_name']}) has same-club transfer: {tr}"
                )
                if i < len(transfers) - 1:
                    next_tr = transfers[i + 1]
                    # No duplicate consecutive from_clubs (targets)
                    self.assertNotEqual(
                        tr["from_club_name"].strip().lower(),
                        next_tr["from_club_name"].strip().lower(),
                        f"Day {day} ({game_data['player_name']}) has consecutive duplicate target '{tr['from_club_name']}'"
                    )

    def test_antoine_griezmann_day_57_multi_spell_career_preserved(self):
        """Verify that Day 57 (Antoine Griezmann) preserves his multi-spell career across Barcelona and Atletico Madrid."""
        game_data, _ = load_transfer_destination(57)
        self.assertIsNotNone(game_data)
        self.assertIn("Antoine Griezmann", game_data["player_name"])

        transfers = game_data["transfers"]
        self.assertGreaterEqual(len(transfers), 6, f"Expected at least 6 career transfers, found {len(transfers)}")

        from_clubs = [t["from_club_name"] for t in transfers]
        to_clubs = [t["to_club_name"] for t in transfers]

        # Barcelona and Atletico Madrid must be present
        self.assertIn("Barcelona", from_clubs + to_clubs)
        self.assertIn("Atletico Madrid", from_clubs + to_clubs)

        # No self-transfers
        for tr in transfers:
            self.assertNotEqual(
                tr["from_club_name"].strip().lower(),
                tr["to_club_name"].strip().lower(),
                f"Found same-club move in Day 57: {tr}"
            )

    def test_same_date_duplicate_deduplication(self):
        """Verify clean_career_transfers deduplicates exact identical moves and same-date duplicates without deleting multi-year spells."""
        from scripts.alias_utils import clean_career_transfers
        mock_raw = [
            {"from_club_name": "Inter", "to_club_name": "Fenerbahce", "transfer_date": "2023-07-01", "transfer_fee": 0, "transfer_type": "Transfer"},
            {"from_club_name": "Inter", "to_club_name": "Fenerbahçe", "transfer_date": "2023-07-01", "transfer_fee": 0, "transfer_type": ""},
            {"from_club_name": "Fenerbahce", "to_club_name": "Fiorentina", "transfer_date": "2024-07-01", "transfer_fee": 5000000, "transfer_type": "Transfer"},
        ]
        cleaned = clean_career_transfers(mock_raw)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(cleaned[0]["from_club_name"], "Inter")
        self.assertEqual(cleaned[0]["to_club_name"], "Fenerbahce")
        self.assertEqual(cleaned[1]["from_club_name"], "Fenerbahce")
        self.assertEqual(cleaned[1]["to_club_name"], "Fiorentina")

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
