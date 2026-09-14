import unittest
import os
import json
import tempfile
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.verify_daily_puzzles import PuzzleVerifier, normalize_str, calculate_puzzle_num

class TestPuzzleVerifier(unittest.TestCase):
    def setUp(self):
        self.verifier = PuzzleVerifier(fix_mode=False, dry_run=True)

    def test_normalize_str(self):
        self.assertEqual(normalize_str("Lionel Messi"), "lionel messi")
        self.assertEqual(normalize_str("  Éder Militão "), "eder militao")
        self.assertEqual(normalize_str("Klaas-Jan Huntelaar"), "klaas-jan huntelaar")
        self.assertEqual(normalize_str("Łukasz Fabiański"), "lukasz fabianski")

    def test_calculate_puzzle_num(self):
        p_today = calculate_puzzle_num(0)
        p_tomorrow = calculate_puzzle_num(1)
        self.assertTrue(1 <= p_today <= 180)
        self.assertTrue(1 <= p_tomorrow <= 180)
        self.assertEqual((p_today % 180) + 1, p_tomorrow)

    def test_audit_today_puzzles_clean(self):
        # Audit all standard games for day 1
        for gid in ["top_transfers", "transfer_destination", "top_scorers", "club_connect", "player_chain", "passport_fc"]:
            self.verifier.run_deterministic_audit(gid, 1)

        errors = [i for i in self.verifier.issues if i["severity"] == "ERROR"]
        self.assertEqual(len(errors), 0, f"Expected 0 errors on Puzzle #1, found: {errors}")

    def test_passport_fc_step2_onward_responses(self):
        # Verify that Passport FC puzzles from Step 2 onward have valid_players populated
        from fetch_daily import load_passport_fc
        data, _ = load_passport_fc(1)
        self.assertIsNotNone(data)
        self.assertEqual(len(data["steps"]), 4)
        for st in data["steps"]:
            if st["step_number"] >= 2:
                self.assertGreaterEqual(len(st["valid_players"]), 1)
                self.assertEqual(len(st["valid_players"]), st["pool_size"])

    def test_anomaly_detection_and_auto_fix(self):
        # Test that verifier detects missing player and can add to database in fix mode
        test_verifier = PuzzleVerifier(fix_mode=True, dry_run=True)
        fake_player = "ZzzTestNonExistentFootballer999"
        test_verifier.ensure_player_exists(fake_player, "test_game", 99)
        
        # Verify an issue was recorded
        issues = [i for i in test_verifier.issues if i["entity_val"] == fake_player]
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0]["severity"], "ERROR")

if __name__ == "__main__":
    unittest.main()
