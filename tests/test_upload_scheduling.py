#!/usr/bin/env python3
"""
tests/test_upload_scheduling.py — Test Suite for 12-Hour Cadence Peak Scheduling & Mode Selection
=================================================================================================
Validates:
1. compute_scheduled_slots for immediate live publishing (iso=None) vs future scheduling.
2. select_games_for_mode:
   - Midday mode -> Top Transfers
   - Evening mode -> Transfer Destination
   - Both mode -> Top Transfers + Transfer Destination
   - Auto mode -> checks hour (< 16 midday, >= 16 evening)
   - Specific game selection and all games selection
3. Spacing between video releases when future slots are requested.
"""

import os
import sys
import unittest
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.upload_daily_shorts import (
    compute_scheduled_slots,
    select_games_for_mode,
    DAILY_GAMES,
    ALL_AVAILABLE_GAMES,
    DEFAULT_PEAK_SLOTS
)

class TestUploadScheduling(unittest.TestCase):

    def test_default_games_selection(self):
        """Validates that daily games default strictly to Top Transfers and Transfer Destination."""
        self.assertEqual(len(DAILY_GAMES), 2)
        game_ids = [g["id"] for g in DAILY_GAMES]
        self.assertIn("top_transfers", game_ids)
        self.assertIn("transfer_destination", game_ids)
        self.assertEqual(len(ALL_AVAILABLE_GAMES), 6)

    def test_select_games_midday_mode(self):
        """Midday mode strictly returns Top Transfers."""
        games = select_games_for_mode(mode="midday")
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["id"], "top_transfers")

    def test_select_games_evening_mode(self):
        """Evening mode strictly returns Transfer Destination."""
        games = select_games_for_mode(mode="evening")
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["id"], "transfer_destination")

    def test_select_games_auto_mode(self):
        """Auto mode: before 16:00 -> Top Transfers; 16:00 and after -> Transfer Destination."""
        morning_games = select_games_for_mode(mode="auto", curr_hour=11)
        self.assertEqual(len(morning_games), 1)
        self.assertEqual(morning_games[0]["id"], "top_transfers")

        evening_games = select_games_for_mode(mode="auto", curr_hour=19)
        self.assertEqual(len(evening_games), 1)
        self.assertEqual(evening_games[0]["id"], "transfer_destination")

    def test_select_games_both_and_all(self):
        """Both mode returns 2 games; all_games returns 6 games."""
        both_games = select_games_for_mode(mode="both")
        self.assertEqual(len(both_games), 2)
        self.assertEqual([g["id"] for g in both_games], ["top_transfers", "transfer_destination"])

        all_g = select_games_for_mode(all_games=True)
        self.assertEqual(len(all_g), 6)

    def test_immediate_live_publishing_default(self):
        """By default, compute_scheduled_slots returns immediate live slots (iso=None)."""
        slots = compute_scheduled_slots(2, immediate_first=True)
        self.assertEqual(len(slots), 2)
        self.assertIsNone(slots[0]["iso"])
        self.assertIsNone(slots[1]["iso"])
        self.assertIn("NOW", slots[0]["label"])
        self.assertIn("NOW", slots[1]["label"])

    def test_future_scheduled_slots(self):
        """When immediate_first=False, slots target future peak hours."""
        start = datetime.datetime(2026, 9, 16, 8, 0, 0, tzinfo=datetime.timezone.utc)
        slots = compute_scheduled_slots(2, start_dt=start, slot_hours=[12, 20], immediate_first=False)
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0]["iso"], "2026-09-16T12:00:00Z")
        self.assertEqual(slots[1]["iso"], "2026-09-16T20:00:00Z")

if __name__ == "__main__":
    unittest.main()
