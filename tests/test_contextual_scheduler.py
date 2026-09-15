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
from scripts.youtube_uploader import build_default_metadata
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

    def test_social_metadata_matchday_injection(self):
        """Tests that YouTube and Instagram metadata functions inject matchday hooks and tags on derbies."""
        # 1. Derby Date (El Clásico on 2026-10-25)
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

        # 2. Non-Matchday Date (2026-08-01)
        yt_title_clean, yt_desc_clean, yt_tags_clean = build_default_metadata("top_transfers", "Arsenal", date_str="2026-08-01")
        self.assertNotIn("SPECIAL!", yt_title_clean)
        self.assertNotIn("ElClasico", yt_tags_clean)

        ig_caption_clean = build_instagram_caption("top_transfers", "Arsenal", date_str="2026-08-01")
        self.assertNotIn("SPECIAL!", ig_caption_clean)
        self.assertNotIn("#ElClasico", ig_caption_clean)

if __name__ == "__main__":
    unittest.main()
