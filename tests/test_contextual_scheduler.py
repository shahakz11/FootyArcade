#!/usr/bin/env python3
"""
tests/test_contextual_scheduler.py — Test Suite for Contextual Puzzle Scheduler & Social Trend-Jacking
=====================================================================================================
Validates:
1. Integrity and schema of `data/fixtures_calendar.json`.
2. Schedule ledger completeness (365 days, all 6 games mapped, valid puzzle IDs 1..180).
3. Universal 100-Day Freeze constraint (0 puzzle ID repeats within 100 days across all 6 games).
4. Derby alternation logic (alternates featured clubs between consecutive head-to-head meetings).
5. Compiler integration in `fetch_daily.py` (ledger lookup priority and modulo fallback).
6. Social metadata generation (matchday clash hooks, titles, tags vs standard non-matchday).
"""

import os
import sys
import json
import unittest
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.sync_fixtures_calendar import validate_fixtures, load_fixtures
from scripts.contextual_puzzle_scheduler import (
    build_schedule_ledger,
    audit_schedule_freeze,
    LEDGER_FILE,
    FREEZE_DAYS
)
from fetch_daily import load_schedule_ledger
from scripts.youtube_uploader import build_default_metadata, is_puzzle_context_matched
from scripts.instagram_uploader import build_instagram_caption

class TestContextualScheduler(unittest.TestCase):

    def setUp(self):
        self.fixtures = load_fixtures()
        with open(LEDGER_FILE, "r", encoding="utf-8") as f:
            self.ledger = json.load(f)

    def test_fixtures_calendar_validity(self):
        """Validates that fixtures_calendar.json has valid dates, competitions, and teams."""
        self.assertGreater(len(self.fixtures), 30, "Should have at least 30 marquee fixtures registered")
        is_valid = validate_fixtures(self.fixtures)
        self.assertTrue(is_valid, "Fixtures calendar must pass all schema validation rules")

    def test_schedule_ledger_completeness(self):
        """Validates that ledger covers 365 days with all 6 games assigned valid puzzle numbers."""
        self.assertEqual(len(self.ledger), 365, "Schedule ledger must contain exactly 365 days")
        games = ["top_transfers", "transfer_destination", "top_scorers", "club_connect", "player_chain", "passport_fc"]
        
        for date_str, day_data in self.ledger.items():
            puzzles = day_data.get("puzzles", {})
            for g in games:
                self.assertIn(g, puzzles, f"{date_str} must have puzzle for {g}")
                pnum = puzzles[g]
                self.assertIsInstance(pnum, int, f"{date_str} {g} puzzle must be int")
                self.assertTrue(1 <= pnum <= 180, f"{date_str} {g} puzzle #{pnum} must be between 1 and 180")

    def test_100_day_freeze_constraint(self):
        """Audits all 365 days and asserts zero 100-day repeat freeze violations across all games."""
        valid, issues = audit_schedule_freeze(self.ledger)
        self.assertTrue(valid, f"Schedule ledger violated freeze constraints: {issues}")
        self.assertEqual(len(issues), 0, "There must be 0 freeze issues across 365 days")

    def test_derby_alternation(self):
        """Validates that repeat clashes alternate featured clubs between meetings."""
        # El Clásico 1: 2026-10-25 (Barcelona vs Real Madrid)
        # El Clásico 2: 2027-05-09 (Real Madrid vs Barcelona)
        day1 = self.ledger.get("2026-10-25")
        day2 = self.ledger.get("2027-05-09")
        self.assertIsNotNone(day1, "El Clásico 1 must exist in ledger")
        self.assertIsNotNone(day2, "El Clásico 2 must exist in ledger")

        club1 = day1.get("matchday_context", {}).get("featured_club")
        club2 = day2.get("matchday_context", {}).get("featured_club")

        self.assertIn(club1, ["Barcelona", "Real Madrid"])
        self.assertIn(club2, ["Barcelona", "Real Madrid"])
        self.assertNotEqual(club1, club2, f"Consecutive derbies must alternate clubs: {club1} vs {club2}")

    def test_fetch_daily_ledger_integration(self):
        """Tests that fetch_daily properly reads the schedule ledger and preserves historical chronological numbers."""
        ledger = load_schedule_ledger()
        self.assertTrue(len(ledger) >= 365)
        
        # 1. Historical & Today: must strictly match chronological puzzle numbers
        today_entry = ledger.get("2026-09-15", {}).get("puzzles", {})
        self.assertEqual(today_entry.get("top_transfers"), 51)
        self.assertEqual(today_entry.get("transfer_destination"), 51)
        self.assertEqual(today_entry.get("top_scorers"), 51)
        self.assertEqual(today_entry.get("club_connect"), 47)
        self.assertEqual(today_entry.get("player_chain"), 5)
        self.assertEqual(today_entry.get("passport_fc"), 2)

        # 2. Tomorrow: starts sequential progression and matchday swaps
        tomorrow_entry = ledger.get("2026-09-16", {}).get("puzzles", {})
        self.assertEqual(tomorrow_entry.get("club_connect"), 48)
        self.assertEqual(tomorrow_entry.get("player_chain"), 6)
        self.assertEqual(tomorrow_entry.get("passport_fc"), 3)

        # 3. Future matchday verification (e.g. 2026-10-25 El Clásico)
        self.assertIn("2026-10-25", ledger)
        puzzles = ledger["2026-10-25"]["puzzles"]
        self.assertIn("top_scorers", puzzles)
        self.assertTrue(1 <= puzzles["top_scorers"] <= 180)

    def test_is_puzzle_context_matched(self):
        """Tests the logic that determines if a puzzle is relevant to the active matchday context."""
        ctx = {
            "clash_name": "El Clásico",
            "competition": "La Liga",
            "home_club": "Real Madrid",
            "away_club": "Barcelona",
            "featured_club": "Real Madrid",
            "hook": "⚔️ EL CLÁSICO SPECIAL!",
            "hashtags": ["#ElClasico", "#RealMadrid", "#FCBarcelona"]
        }

        # 1. Direct and alias club matches
        self.assertTrue(is_puzzle_context_matched("top_transfers", "Real Madrid", ctx))
        self.assertTrue(is_puzzle_context_matched("top_transfers", "Barcelona", ctx))
        self.assertTrue(is_puzzle_context_matched("top_transfers", "FC Barcelona", ctx))
        self.assertTrue(is_puzzle_context_matched("top_transfers", "Barca", ctx))
        self.assertTrue(is_puzzle_context_matched("club_connect", "Real Madrid", ctx))
        self.assertTrue(is_puzzle_context_matched("club_connect", "Barcelona", ctx))

        # 2. Unmatched clubs on derby day
        self.assertFalse(is_puzzle_context_matched("top_transfers", "Bayern Munich", ctx))
        self.assertFalse(is_puzzle_context_matched("top_transfers", "Arsenal", ctx))
        self.assertFalse(is_puzzle_context_matched("club_connect", "Chelsea", ctx))

        # 3. Top Scorers competition matching
        self.assertTrue(is_puzzle_context_matched("top_scorers", "La Liga 2023/24", ctx))
        self.assertFalse(is_puzzle_context_matched("top_scorers", "Premier League 2023/24", ctx))
        self.assertFalse(is_puzzle_context_matched("top_scorers", "Serie A 2022/23", ctx))

        # 4. Standard player journey games should return False (evergreen fallback)
        self.assertFalse(is_puzzle_context_matched("transfer_destination", "Erling Haaland", ctx))
        self.assertFalse(is_puzzle_context_matched("player_chain", "Mystery Chain", ctx))
        self.assertFalse(is_puzzle_context_matched("passport_fc", "Spain", ctx))

        # 5. Empty or missing context
        self.assertFalse(is_puzzle_context_matched("top_transfers", "Real Madrid", None))
        self.assertFalse(is_puzzle_context_matched("top_transfers", "", ctx))

    def test_social_metadata_matchday_injection_and_relevance_gating(self):
        """Tests that YouTube and Instagram metadata inject matchday hooks ONLY for relevant puzzles."""
        # 1. Matched Puzzle on Derby Date (El Clásico on 2026-10-25 -> Real Madrid Top Transfers)
        yt_title, yt_desc, yt_tags = build_default_metadata("top_transfers", "Real Madrid", date_str="2026-10-25")
        self.assertIn("EL CLÁSICO SPECIAL", yt_title)
        self.assertIn("ElClasico", yt_tags)
        self.assertIn("RealMadrid", yt_tags)
        self.assertIn("FCBarcelona", yt_tags)
        self.assertIn("Today's Matchday Special: El Clásico", yt_desc)

        ig_caption = build_instagram_caption("top_transfers", "Real Madrid", date_str="2026-10-25")
        self.assertIn("EL CLÁSICO SPECIAL", ig_caption)
        self.assertIn("#ElClasico", ig_caption)
        self.assertIn("#RealMadrid", ig_caption)

        # 2. Unmatched Puzzle on Derby Date (El Clásico on 2026-10-25 -> Transfer Destination / Erling Haaland)
        # MUST strictly receive regular evergreen title and caption with NO clash hooks or tags
        yt_title_td, yt_desc_td, yt_tags_td = build_default_metadata("transfer_destination", "Erling Haaland", date_str="2026-10-25")
        self.assertNotIn("SPECIAL", yt_title_td)
        self.assertNotIn("ElClasico", yt_tags_td)
        self.assertNotIn("RealMadrid", yt_tags_td)
        self.assertNotIn("Today's Matchday Special", yt_desc_td)
        self.assertEqual(yt_title_td, "Guess the mystery player's career path backwards! ⚽ #Shorts")

        ig_caption_td = build_instagram_caption("transfer_destination", "Erling Haaland", date_str="2026-10-25")
        self.assertNotIn("SPECIAL", ig_caption_td)
        self.assertNotIn("#ElClasico", ig_caption_td)
        self.assertNotIn("#RealMadrid", ig_caption_td)
        self.assertIn("Guess the mystery player's career path backwards! ⚽", ig_caption_td)

        # 3. Mismatched Club on Derby Date (El Clásico on 2026-10-25 -> Top Transfers for Bayern Munich)
        yt_title_mismatch, yt_desc_mismatch, yt_tags_mismatch = build_default_metadata("top_transfers", "Bayern Munich", date_str="2026-10-25")
        self.assertNotIn("SPECIAL", yt_title_mismatch)
        self.assertNotIn("ElClasico", yt_tags_mismatch)
        self.assertNotIn("RealMadrid", yt_tags_mismatch)
        self.assertNotIn("Today's Matchday Special", yt_desc_mismatch)
        self.assertIn("Can you guess Bayern Munich's record transfers?", yt_title_mismatch)

        ig_caption_mismatch = build_instagram_caption("top_transfers", "Bayern Munich", date_str="2026-10-25")
        self.assertNotIn("SPECIAL", ig_caption_mismatch)
        self.assertNotIn("#ElClasico", ig_caption_mismatch)

        # 4. Non-Matchday Date (2026-08-01)
        yt_title_clean, yt_desc_clean, yt_tags_clean = build_default_metadata("top_transfers", "Arsenal", date_str="2026-08-01")
        self.assertNotIn("SPECIAL!", yt_title_clean)
        self.assertNotIn("ElClasico", yt_tags_clean)

        ig_caption_clean = build_instagram_caption("top_transfers", "Arsenal", date_str="2026-08-01")
        self.assertNotIn("SPECIAL!", ig_caption_clean)
        self.assertNotIn("#ElClasico", ig_caption_clean)

if __name__ == "__main__":
    unittest.main()
