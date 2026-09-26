#!/usr/bin/env python3
"""
tests/test_instagram_deduplication.py
======================================
Unit tests for Instagram Reel deduplication logic, verifying that:
1. Different games on the same date with identical Matchday Special badges
   (e.g., '⚔️ MADRID DERBY SPECIAL!') are NOT falsely deduplicated.
2. Only matching game patterns or target names trigger deduplication.
3. UGC format captions across morning (Player Chain) and evening (Passport FC)
   do NOT falsely deduplicate due to generic phrases like "player to play for".
"""

import unittest
from unittest.mock import patch, MagicMock
import json

from scripts.instagram_uploader import is_already_posted
from scripts.youtube_uploader import is_youtube_already_uploaded

class TestInstagramDeduplication(unittest.TestCase):

    @patch("scripts.instagram_uploader._load_ledger")
    @patch("scripts.instagram_uploader.load_config")
    @patch("urllib.request.urlopen")
    def test_matchday_different_games_no_false_positive(self, mock_urlopen, mock_load_config, mock_load_ledger):
        mock_load_ledger.return_value = {}
        mock_load_config.return_value = {"access_token": "fake_token", "ig_user_id": "12345"}

        # Simulate Instagram Graph API response having only Top Transfers posted on 2026-09-20
        mock_api_data = {
            "data": [
                {
                    "id": "18485664532111126",
                    "timestamp": "2026-09-20T13:04:18+0000",
                    "permalink": "https://www.instagram.com/reel/DdgpjbUDVfv/",
                    "caption": "⚔️ MADRID DERBY SPECIAL!\nCan you guess COTE D'IVOIRE's record transfers? ⚽\n\nComment your score below! 👇\n\n🎮 Play today's free daily puzzles at: playmaker.best\n#DerbiMadrileno #RealMadrid #Atleti #LaLiga"
                }
            ]
        }
        
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_api_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        # 1. Top transfers on 2026-09-20 should be detected as already posted
        is_top_posted, top_url = is_already_posted("top_transfers", "2026-09-20", target_name="COTE D'IVOIRE")
        self.assertTrue(is_top_posted)
        self.assertEqual(top_url, "https://www.instagram.com/reel/DdgpjbUDVfv/")

        # 2. Transfer destination (evening game) on 2026-09-20 MUST NOT be marked as already posted!
        is_dest_posted, dest_url = is_already_posted("transfer_destination", "2026-09-20", target_name="Julian Alvarez")
        self.assertFalse(is_dest_posted)
        self.assertEqual(dest_url, "")

    @patch("scripts.instagram_uploader._load_ledger")
    @patch("scripts.instagram_uploader.load_config")
    @patch("urllib.request.urlopen")
    def test_ugc_shorts_distinct_target_deduplication(self, mock_urlopen, mock_load_config, mock_load_ledger):
        """
        Verifies that a morning Player Chain UGC post (e.g. Chelsea & France)
        does NOT prevent an evening Passport FC UGC post (e.g. Borussia Dortmund & France).
        """
        mock_load_ledger.return_value = {}
        mock_load_config.return_value = {"access_token": "fake_token", "ig_user_id": "12345"}

        mock_api_data = {
            "data": [
                {
                    "id": "18115980182075523",
                    "timestamp": "2026-09-26T09:28:59+0000",
                    "permalink": "https://www.instagram.com/reel/DdvtrZ-D1-X/",
                    "caption": (
                        "Name ONE France player to play for Chelsea that NO ONE ELSE in the comments will say.\n\n"
                        "I'll start... Malo Gusto\n\nDrop yours below 👇⚽️\n\n"
                        "Play today's full Player Chain puzzle at the link in bio!\n\n#football #soccer"
                    )
                }
            ]
        }

        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(mock_api_data).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_resp

        # Morning Player Chain for Chelsea & France should be detected as already posted
        is_pc_posted, pc_url = is_already_posted("player_chain", "2026-09-26", target_name="Chelsea & France")
        self.assertTrue(is_pc_posted)
        self.assertEqual(pc_url, "https://www.instagram.com/reel/DdvtrZ-D1-X/")

        # Evening Passport FC for Borussia Dortmund & France MUST NOT be marked as already posted!
        is_pfc_posted, pfc_url = is_already_posted("passport_fc", "2026-09-26", target_name="Borussia Dortmund & France")
        self.assertFalse(is_pfc_posted)
        self.assertEqual(pfc_url, "")

if __name__ == "__main__":
    unittest.main()
