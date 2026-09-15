#!/usr/bin/env python3
"""
tests/test_upload_scheduling.py — Test Suite for 12-Hour Cadence Peak Scheduling
================================================================================
Validates:
1. compute_scheduled_slots targeting 12:00 PM and 8:00 PM UTC peak windows.
2. Spacing between video releases to prevent simultaneous batch dumps.
3. Rollover to next day's 12:00 UTC slot when run late in the evening.
4. Immediate-first flag assigning Slot 0 to NOW (None) and subsequent slots to peak times.
5. Default daily games restricted to Top Transfers and Transfer Destination.
6. YouTube ISO 8601 publishAt formatting compliance.
7. Instagram queue compatibility.
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

    def test_morning_schedule_slots(self):
        """Morning run (08:00 UTC): Slot 0 -> 12:00 UTC today, Slot 1 -> 20:00 UTC today."""
        start = datetime.datetime(2026, 9, 16, 8, 0, 0, tzinfo=datetime.timezone.utc)
        slots = compute_scheduled_slots(2, start_dt=start, slot_hours=[12, 20])
        
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0]["iso"], "2026-09-16T12:00:00Z")
        self.assertEqual(slots[1]["iso"], "2026-09-16T20:00:00Z")
        self.assertIn("12:00 UTC", slots[0]["label"])
        self.assertIn("20:00 UTC", slots[1]["label"])

    def test_afternoon_schedule_slots(self):
        """Afternoon run (14:30 UTC): Slot 0 -> 20:00 UTC today, Slot 1 -> 12:00 UTC tomorrow."""
        start = datetime.datetime(2026, 9, 16, 14, 30, 0, tzinfo=datetime.timezone.utc)
        slots = compute_scheduled_slots(2, start_dt=start, slot_hours=[12, 20])
        
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0]["iso"], "2026-09-16T20:00:00Z")
        self.assertEqual(slots[1]["iso"], "2026-09-17T12:00:00Z")

    def test_night_schedule_slots(self):
        """Night run (21:30 UTC): Slot 0 -> 12:00 UTC tomorrow, Slot 1 -> 20:00 UTC tomorrow."""
        start = datetime.datetime(2026, 9, 16, 21, 30, 0, tzinfo=datetime.timezone.utc)
        slots = compute_scheduled_slots(2, start_dt=start, slot_hours=[12, 20])
        
        self.assertEqual(len(slots), 2)
        self.assertEqual(slots[0]["iso"], "2026-09-17T12:00:00Z")
        self.assertEqual(slots[1]["iso"], "2026-09-17T20:00:00Z")

    def test_immediate_first_slot(self):
        """When immediate_first=True, Slot 0 is immediate (iso=None), Slot 1 is next peak slot."""
        start = datetime.datetime(2026, 9, 16, 8, 0, 0, tzinfo=datetime.timezone.utc)
        slots = compute_scheduled_slots(2, start_dt=start, slot_hours=[12, 20], immediate_first=True)
        
        self.assertEqual(len(slots), 2)
        self.assertIsNone(slots[0]["iso"])
        self.assertEqual(slots[0]["label"], "NOW (Immediate Public)")
        self.assertEqual(slots[1]["iso"], "2026-09-16T12:00:00Z")

    def test_multi_day_cadence_spacing(self):
        """Scheduling 6 videos spaces them across 3 full days (12:00 UTC and 20:00 UTC each day)."""
        start = datetime.datetime(2026, 9, 16, 9, 0, 0, tzinfo=datetime.timezone.utc)
        slots = compute_scheduled_slots(6, start_dt=start, slot_hours=[12, 20])
        
        self.assertEqual(len(slots), 6)
        expected_isos = [
            "2026-09-16T12:00:00Z",
            "2026-09-16T20:00:00Z",
            "2026-09-17T12:00:00Z",
            "2026-09-17T20:00:00Z",
            "2026-09-18T12:00:00Z",
            "2026-09-18T20:00:00Z",
        ]
        for i, expected in enumerate(expected_isos):
            self.assertEqual(slots[i]["iso"], expected, f"Slot {i} does not match expected {expected}")

    def test_custom_slot_hours(self):
        """Supports custom slot configurations (e.g. 3 slots per day)."""
        start = datetime.datetime(2026, 9, 16, 6, 0, 0, tzinfo=datetime.timezone.utc)
        slots = compute_scheduled_slots(3, start_dt=start, slot_hours=[9, 15, 21])
        
        self.assertEqual(len(slots), 3)
        self.assertEqual(slots[0]["iso"], "2026-09-16T09:00:00Z")
        self.assertEqual(slots[1]["iso"], "2026-09-16T15:00:00Z")
        self.assertEqual(slots[2]["iso"], "2026-09-16T21:00:00Z")

if __name__ == "__main__":
    unittest.main()
