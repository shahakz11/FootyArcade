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
    prepare_youtube_video,
    DAILY_GAMES,
    ALL_AVAILABLE_GAMES,
    DEFAULT_PEAK_SLOTS
)

class TestUploadScheduling(unittest.TestCase):

    def test_default_games_selection(self):
        """Validates that daily games default strictly to Player Chain and Passport FC."""
        self.assertEqual(len(DAILY_GAMES), 2)
        game_ids = [g["id"] for g in DAILY_GAMES]
        self.assertIn("player_chain", game_ids)
        self.assertIn("passport_fc", game_ids)
        self.assertEqual(len(ALL_AVAILABLE_GAMES), 6)

    def test_select_games_midday_mode(self):
        """Midday mode strictly returns Player Chain."""
        games = select_games_for_mode(mode="midday")
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["id"], "player_chain")

    def test_select_games_evening_mode(self):
        """Evening mode strictly returns Passport FC."""
        games = select_games_for_mode(mode="evening")
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["id"], "passport_fc")

    def test_select_games_daily_and_auto_mode(self):
        """Daily/auto mode returns one daily game alternating between Player Chain and Passport FC."""
        daily_games = select_games_for_mode(mode="daily")
        self.assertEqual(len(daily_games), 1)
        self.assertIn(daily_games[0]["id"], ["player_chain", "passport_fc"])

        # Midday 10:30 UTC Carousel window
        carousel_auto = select_games_for_mode(mode="auto", curr_hour=10)
        self.assertEqual(len(carousel_auto), 0)

        # Evening 17:00 UTC Video Short window
        video_auto = select_games_for_mode(mode="auto", curr_hour=17)
        self.assertEqual(len(video_auto), 1)
        self.assertIn(video_auto[0]["id"], ["player_chain", "passport_fc"])

    def test_select_games_both_and_all(self):
        """Both mode returns 2 games; all_games returns 6 games."""
        both_games = select_games_for_mode(mode="both")
        self.assertEqual(len(both_games), 2)
        self.assertEqual([g["id"] for g in both_games], ["player_chain", "passport_fc"])

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

    def test_prepare_youtube_video_strip_audio_false(self):
        """When strip_audio is False, returns original path."""
        path = "/tmp/non_existent_fake_video.mp4"
        result = prepare_youtube_video(path, strip_audio=False)
        self.assertEqual(result, path)

    def test_prepare_youtube_video_non_existent(self):
        """When file does not exist, gracefully returns original path."""
        path = "/tmp/non_existent_fake_video.mp4"
        result = prepare_youtube_video(path, strip_audio=True)
        self.assertEqual(result, path)

if __name__ == "__main__":
    unittest.main()
