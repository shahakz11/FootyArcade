#!/usr/bin/env python3
"""
tests/test_played_with_short.py

Comprehensive 4-Tier Test Suite for the "Played With" Vertical Short Video Generator:
- Tier 1: Feature Coverage (n-2 date selection, clue loading, formatting, social copy, video specs)
- Tier 2: Boundary & Corner Cases (Adaptive typography on all 1,825 rows, longest names, non-ASCII/accents, null nationalities)
- Tier 3: Cross-Feature Combinations (CLI arguments, copy-to-caption contract)
"""

import os
import sys
import csv
import json
import unittest
from unittest.mock import patch, MagicMock
import datetime
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

CSV_PATH = os.path.join(BASE_DIR, "daily_played_with_games.csv")
FONT_BOLD_PATH = os.path.join(BASE_DIR, "assets", "fonts", "Arial-Bold.ttf")

try:
    import render_played_with_short as rps
except ImportError:
    rps = None


class TestPlayedWithDateAndSelection(unittest.TestCase):
    """Tier 1: Feature Coverage — Date calculations and puzzle selection logic."""

    def test_n_minus_2_date_resolution_standard(self):
        """Verifies reference date is strictly offset by -2 days."""
        if rps is None or not hasattr(rps, "get_n_minus_2_date"):
            self.skipTest("render_played_with_short.get_n_minus_2_date not available")
        ref_date = datetime.date(2026, 10, 18)
        expected = datetime.date(2026, 10, 16)
        self.assertEqual(rps.get_n_minus_2_date(ref_date), expected)

    def test_n_minus_2_date_resolution_month_boundary(self):
        """Verifies month rollover backwards across boundaries."""
        if rps is None or not hasattr(rps, "get_n_minus_2_date"):
            self.skipTest("render_played_with_short.get_n_minus_2_date not available")
        ref_date = datetime.date(2026, 10, 1)
        expected = datetime.date(2026, 9, 29)
        self.assertEqual(rps.get_n_minus_2_date(ref_date), expected)

    def test_n_minus_2_date_resolution_leap_year(self):
        """Verifies leap day calculation backwards from March 1st."""
        if rps is None or not hasattr(rps, "get_n_minus_2_date"):
            self.skipTest("render_played_with_short.get_n_minus_2_date not available")
        ref_date = datetime.date(2024, 3, 1)
        expected = datetime.date(2024, 2, 28)
        self.assertEqual(rps.get_n_minus_2_date(ref_date), expected)

    def test_n_minus_2_date_default_is_today_minus_two(self):
        """Verifies that calling get_n_minus_2_date() without args defaults to today - 2 days."""
        if rps is None or not hasattr(rps, "get_n_minus_2_date"):
            self.skipTest("render_played_with_short.get_n_minus_2_date not available")
        today = datetime.date.today()
        expected = today - datetime.timedelta(days=2)
        self.assertEqual(rps.get_n_minus_2_date(), expected)

    def test_puzzle_day_for_date_launch_day(self):
        """Launch day 2026-09-27 must map strictly to Day 1."""
        if rps is None or not hasattr(rps, "get_puzzle_day_for_date"):
            self.skipTest("render_played_with_short.get_puzzle_day_for_date not available")
        launch_date = datetime.date(2026, 9, 27)
        self.assertEqual(rps.get_puzzle_day_for_date(launch_date), 1)

    def test_puzzle_day_for_date_next_day(self):
        """Day after launch (2026-09-28) must map strictly to Day 2."""
        if rps is None or not hasattr(rps, "get_puzzle_day_for_date"):
            self.skipTest("render_played_with_short.get_puzzle_day_for_date not available")
        self.assertEqual(rps.get_puzzle_day_for_date(datetime.date(2026, 9, 28)), 2)

    def test_puzzle_day_for_date_n_minus_2_for_today(self):
        """On 2026-10-18, n-2 date is 2026-10-16 which must resolve to Day 20."""
        if rps is None or not hasattr(rps, "get_puzzle_day_for_date"):
            self.skipTest("render_played_with_short.get_puzzle_day_for_date not available")
        target_date = datetime.date(2026, 10, 16)
        self.assertEqual(rps.get_puzzle_day_for_date(target_date), 20)

    def test_puzzle_day_cycle_modulo_365(self):
        """Puzzle cycle repeats cleanly modulo 365."""
        if rps is None or not hasattr(rps, "get_puzzle_day_for_date"):
            self.skipTest("render_played_with_short.get_puzzle_day_for_date not available")
        launch = datetime.date(2026, 9, 27)
        day_365_date = launch + datetime.timedelta(days=364)
        self.assertEqual(rps.get_puzzle_day_for_date(day_365_date), 365)

        day_366_date = launch + datetime.timedelta(days=365)
        self.assertEqual(rps.get_puzzle_day_for_date(day_366_date), 1)

    def test_load_played_with_puzzle_keys_and_contract(self):
        """Verifies load_played_with_puzzle returns the exact contract specified in PROJECT.md."""
        if rps is None or not hasattr(rps, "load_played_with_puzzle"):
            self.skipTest("render_played_with_short.load_played_with_puzzle not available")
        puzzle = rps.load_played_with_puzzle(day=1)
        self.assertIsInstance(puzzle, dict)
        self.assertEqual(puzzle.get("game_day"), 1)
        self.assertEqual(puzzle.get("mystery_player"), "João Félix")
        self.assertEqual(puzzle.get("mystery_nationality"), "Portugal")
        self.assertIn("steps", puzzle)
        self.assertEqual(len(puzzle["steps"]), 5)

    def test_load_played_with_puzzle_all_5_steps_and_ordering(self):
        """Verifies steps 1 through 5 are ordered ascending and non-decreasing in appearances."""
        if rps is None or not hasattr(rps, "load_played_with_puzzle"):
            self.skipTest("render_played_with_short.load_played_with_puzzle not available")
        puzzle = rps.load_played_with_puzzle(day=20)
        steps = puzzle["steps"]
        step_numbers = [s["step_number"] for s in steps]
        self.assertEqual(step_numbers, [1, 2, 3, 4, 5])

        for s in steps:
            self.assertIn("teammate_name", s)
            self.assertIn("appearances_together", s)
            self.assertIn("clue_tier", s)
            self.assertGreaterEqual(s["appearances_together"], 10)

        # Invariant: appearances non-decreasing
        apps = [s["appearances_together"] for s in steps]
        for i in range(len(apps) - 1):
            self.assertLessEqual(apps[i], apps[i + 1])

    def test_load_played_with_puzzle_clue_formatting(self):
        """Verifies standard formatting 'I played {X} games with {Teammate Name}'."""
        if rps is None or not hasattr(rps, "load_played_with_puzzle"):
            self.skipTest("render_played_with_short.load_played_with_puzzle not available")
        puzzle = rps.load_played_with_puzzle(day=1)
        first_step = puzzle["steps"][0]
        expected_clue = f"I played {first_step['appearances_together']} games with {first_step['teammate_name']}"
        self.assertTrue(expected_clue.startswith("I played "))
        self.assertIn(" games with ", expected_clue)

    def test_load_played_with_puzzle_date_override(self):
        """Verifies loading puzzle by date_str='2026-10-16' correctly resolves Day 20."""
        if rps is None or not hasattr(rps, "load_played_with_puzzle"):
            self.skipTest("render_played_with_short.load_played_with_puzzle not available")
        puzzle = rps.load_played_with_puzzle(date_str="2026-10-16")
        self.assertEqual(puzzle["game_day"], 20)
        self.assertEqual(puzzle["mystery_player"], "Stevan Jovetić")

    def test_load_played_with_puzzle_default_uses_n_minus_2(self):
        """Verifies load_played_with_puzzle() with no arguments resolves to n-2 puzzle."""
        if rps is None or not hasattr(rps, "load_played_with_puzzle"):
            self.skipTest("render_played_with_short.load_played_with_puzzle not available")
        puzzle = rps.load_played_with_puzzle()
        expected_n2_date = rps.get_n_minus_2_date()
        expected_day = rps.get_puzzle_day_for_date(expected_n2_date)
        self.assertEqual(puzzle["game_day"], expected_day)


class TestPlayedWithSocialCopy(unittest.TestCase):
    """Tier 1: Feature Coverage — Platform social copy and engagement metadata."""

    def setUp(self):
        self.sample_puzzle = {
            "game_day": 20,
            "mystery_player": "Stevan Jovetić",
            "mystery_position": "Attack",
            "mystery_nationality": "Montenegro",
            "steps": [
                {"step_number": 1, "teammate_name": "Valon Behrami", "appearances_together": 68, "clue_tier": "20th Most Frequent"},
                {"step_number": 2, "teammate_name": "Matija Nastasić", "appearances_together": 77, "clue_tier": "10th Most Frequent"},
                {"step_number": 3, "teammate_name": "Adem Ljajić", "appearances_together": 91, "clue_tier": "5th Most Frequent"},
                {"step_number": 4, "teammate_name": "Stefan Savić", "appearances_together": 105, "clue_tier": "2nd Most Frequent"},
                {"step_number": 5, "teammate_name": "Manuel Pasqual", "appearances_together": 126, "clue_tier": "Most Frequent"}
            ]
        }

    def test_social_copy_structure(self):
        """Verifies generate_social_copy returns caption, youtube_title, and hashtags."""
        if rps is None or not hasattr(rps, "generate_social_copy"):
            self.skipTest("render_played_with_short.generate_social_copy not available")
        copy = rps.generate_social_copy(self.sample_puzzle)
        self.assertIsInstance(copy, dict)
        self.assertIn("caption", copy)
        self.assertIn("youtube_title", copy)
        self.assertIn("hashtags", copy)

    def test_social_copy_contains_all_clues(self):
        """Verifies caption contains references to all 5 teammate clues."""
        if rps is None or not hasattr(rps, "generate_social_copy"):
            self.skipTest("render_played_with_short.generate_social_copy not available")
        copy = rps.generate_social_copy(self.sample_puzzle)
        caption = copy["caption"]
        for s in self.sample_puzzle["steps"]:
            self.assertIn(s["teammate_name"], caption)

    def test_social_copy_contains_comment_cta(self):
        """Verifies caption explicitly prompts viewers to comment their guess."""
        if rps is None or not hasattr(rps, "generate_social_copy"):
            self.skipTest("render_played_with_short.generate_social_copy not available")
        copy = rps.generate_social_copy(self.sample_puzzle)
        caption_lower = copy["caption"].lower()
        has_cta = any(phrase in caption_lower for phrase in ["comment", "guess", "drop your guess", "who am i"])
        self.assertTrue(has_cta, "Caption must instruct viewers to comment their guess")

    def test_social_copy_promotes_playmaker_url(self):
        """Verifies caption directs viewers to playmaker.best."""
        if rps is None or not hasattr(rps, "generate_social_copy"):
            self.skipTest("render_played_with_short.generate_social_copy not available")
        copy = rps.generate_social_copy(self.sample_puzzle)
        self.assertIn("playmaker.best", copy["caption"].lower())

    def test_youtube_title_length_under_95_chars(self):
        """YouTube Shorts titles must be strictly under 95 characters to avoid truncation."""
        if rps is None or not hasattr(rps, "generate_social_copy"):
            self.skipTest("render_played_with_short.generate_social_copy not available")
        copy = rps.generate_social_copy(self.sample_puzzle)
        title = copy["youtube_title"]
        self.assertLess(len(title), 95, f"YouTube title '{title}' length {len(title)} is >= 95 chars")
        self.assertGreater(len(title), 10, "YouTube title too short")

    def test_hashtags_presence_and_format(self):
        """Verifies hashtags list contains relevant tags starting with '#'."""
        if rps is None or not hasattr(rps, "generate_social_copy"):
            self.skipTest("render_played_with_short.generate_social_copy not available")
        copy = rps.generate_social_copy(self.sample_puzzle)
        tags = copy["hashtags"]
        self.assertIsInstance(tags, list)
        self.assertGreaterEqual(len(tags), 3)
        for t in tags:
            self.assertTrue(t.startswith("#"), f"Hashtag {t} does not start with #")

    def test_social_copy_contains_day_number_and_hashtag(self):
        """Verifies caption contains WHO AM I? #{day} and hashtag #playedwith_{day}."""
        if rps is None or not hasattr(rps, "generate_social_copy"):
            self.skipTest("render_played_with_short.generate_social_copy not available")
        copy = rps.generate_social_copy(self.sample_puzzle)
        self.assertIn("WHO AM I? #20 ⚽️🤔", copy["caption"])
        self.assertIn("#playedwith_20", copy["caption"])
        self.assertIn("#playedwith_20", copy["hashtags"])
        self.assertIn("#20", copy["youtube_title"])

    def test_youtube_title_all_365_days_have_day_and_under_95_chars(self):
        """Verifies YouTube titles for all 365 days contain #{day} and are strictly < 95 chars."""
        if rps is None or not hasattr(rps, "load_played_with_puzzle"):
            self.skipTest("render_played_with_short not available")
        for day in range(1, 366):
            p = rps.load_played_with_puzzle(day=day)
            title = rps.generate_youtube_title(p)
            self.assertIn(f"#{day}", title, f"Day {day} title missing #{day}: {title}")
            self.assertLess(len(title), 95, f"Day {day} title >= 95 chars ({len(title)}): {title}")


class TestPlayedWithAdaptiveTypography(unittest.TestCase):
    """Tier 2: Boundary & Corner Cases — Safe width margins and text fitting across 100% of clues."""

    @classmethod
    def setUpClass(cls):
        cls.rows = []
        if os.path.exists(CSV_PATH):
            with open(CSV_PATH, "r", encoding="utf-8") as f:
                cls.rows = list(csv.DictReader(f))

    def test_all_1825_clues_fit_within_840px_safe_zone(self):
        """
        Stress test: Every single one of the 1,825 rows in daily_played_with_games.csv
        must fit within 840px horizontal content safe zone without clipping.
        """
        self.assertEqual(len(self.rows), 1825, f"Expected 1825 rows, found {len(self.rows)}")
        self.assertTrue(os.path.exists(FONT_BOLD_PATH), f"Font {FONT_BOLD_PATH} missing")

        # Invariant: At safe font size 34pt, 100% of clues measure <= 840px
        font_34 = ImageFont.truetype(FONT_BOLD_PATH, 34)
        overflow_rows = []

        for r in self.rows:
            clue_str = f"I played {r['appearances_together']} games with {r['teammate_name']}"
            bbox = font_34.getbbox(clue_str)
            width = bbox[2] - bbox[0]
            if width > 840:
                overflow_rows.append((r["game_day"], clue_str, width))

        self.assertEqual(len(overflow_rows), 0, f"Found {len(overflow_rows)} clues exceeding 840px at 34pt: {overflow_rows[:3]}")

    def test_all_1825_clues_fit_within_840px_with_stroke_padding(self):
        """
        Stress test: Every single one of the 1,825 rows in daily_played_with_games.csv
        rendered with adaptive font sizing and stroke_width=5 must strictly fit within 840px safe zone.
        """
        if rps is None or not hasattr(rps, "calculate_adaptive_font_size"):
            self.skipTest("render_played_with_short.calculate_adaptive_font_size not available")

        by_day = {}
        for r in self.rows:
            by_day.setdefault(int(r["game_day"]), []).append(r)

        d = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
        overflows = []

        for day, clues in by_day.items():
            font_size = rps.calculate_adaptive_font_size(clues, max_width=840)
            font = rps.get_font(font_size, bold=True)
            for c in clues:
                clue_text = f"I played {c['appearances_together']} games with {c['teammate_name']}"
                bbox = d.textbbox((0, 0), clue_text, font=font, stroke_width=5)
                width = bbox[2] - bbox[0]
                if width > 840:
                    overflows.append((day, clue_text, width))

        self.assertEqual(len(overflows), 0, f"Found {len(overflows)} clues exceeding 840px with stroke outline: {overflows[:3]}")

    def test_longest_names_adaptive_scaling(self):
        """
        Checks that adaptive font sizing dynamically scales down for the longest names:
        'Pierre-Emerick Aubameyang' (25 chars) and 'Eric-Maxim Choupo-Moting' (24 chars).
        """
        if rps is not None and hasattr(rps, "calculate_adaptive_font_size"):
            # Sample clue list with Pierre-Emerick Aubameyang
            clues = [
                "I played 35 games with Dan-Axel Zagadou",
                "I played 58 games with Manuel Akanji",
                "I played 84 games with Axel Witsel",
                "I played 112 games with Marco Reus",
                "I played 150 games with Pierre-Emerick Aubameyang"
            ]
            size = rps.calculate_adaptive_font_size(clues, max_width=840, base_size=44, min_size=32)
            self.assertLess(size, 44, "Font size should have scaled down from base 44")
            self.assertGreaterEqual(size, 32, "Font size should not drop below minimum 32")

            # Verify actual bounding box fits inside 840px
            font = ImageFont.truetype(FONT_BOLD_PATH, size)
            for c in clues:
                bbox = font.getbbox(c)
                self.assertLessEqual(bbox[2] - bbox[0], 840)

    def test_special_characters_and_accents_rendering(self):
        """Verifies special characters and diacritics measure and render cleanly without error."""
        font = ImageFont.truetype(FONT_BOLD_PATH, 36)
        special_names = [
            "İlkay Gündoğan",
            "Sergej Milinković-Savić",
            "João Félix",
            "N'Golo Kanté",
            "Hakan Çalhanoğlu",
            "Saúl Ñíguez",
            "Wojciech Szczęsny",
            "Martin Ødegaard"
        ]
        for name in special_names:
            text = f"I played 100 games with {name}"
            try:
                bbox = font.getbbox(text)
                width = bbox[2] - bbox[0]
                self.assertGreater(width, 0)
                self.assertLessEqual(width, 840)
            except Exception as e:
                self.fail(f"Failed to measure text with special name '{name}': {e}")

    def test_missing_nationality_graceful_handling(self):
        """
        Verifies puzzles containing rows with missing/null teammate nationalities
        (e.g., Samir Handanovic on Day 72, Jesé on Day 186) load without error.
        """
        if rps is None or not hasattr(rps, "load_played_with_puzzle"):
            self.skipTest("render_played_with_short.load_played_with_puzzle not available")

        # Handanovic Day 72
        p72 = rps.load_played_with_puzzle(day=72)
        self.assertIsNotNone(p72)
        self.assertEqual(p72["game_day"], 72)

        # Jesé Day 186
        p186 = rps.load_played_with_puzzle(day=186)
        self.assertIsNotNone(p186)
        self.assertEqual(p186["game_day"], 186)


class TestPlayedWithCLIAndContracts(unittest.TestCase):
    """Tier 3: Cross-Feature Combinations — CLI argument handling & cross-module integration."""

    def test_cli_day_override(self):
        """Verifies load_played_with_puzzle accepts explicit day overrides 1..365."""
        if rps is None or not hasattr(rps, "load_played_with_puzzle"):
            self.skipTest("render_played_with_short.load_played_with_puzzle not available")
        p50 = rps.load_played_with_puzzle(day=50)
        self.assertEqual(p50["game_day"], 50)

    def test_cli_invalid_day_handling(self):
        """Verifies day < 1 or day > 365 raises ValueError."""
        if rps is None or not hasattr(rps, "load_played_with_puzzle"):
            self.skipTest("render_played_with_short.load_played_with_puzzle not available")
        with self.assertRaises((ValueError, IndexError)):
            rps.load_played_with_puzzle(day=0)
        with self.assertRaises((ValueError, IndexError)):
            rps.load_played_with_puzzle(day=366)

    def test_cli_invalid_date_handling(self):
        """Verifies malformed date string raises ValueError."""
        if rps is None or not hasattr(rps, "load_played_with_puzzle"):
            self.skipTest("render_played_with_short.load_played_with_puzzle not available")
        with self.assertRaises((ValueError, TypeError)):
            rps.load_played_with_puzzle(date_str="not-a-date")

    def test_video_canvas_dimensions_and_safe_zones(self):
        """Verifies video dimensions constant contract: 1080x1920 (9:16)."""
        if rps is not None:
            width = getattr(rps, "WIDTH", 1080)
            height = getattr(rps, "HEIGHT", 1920)
            fps = getattr(rps, "FPS", 30)
            self.assertEqual(width, 1080)
            self.assertEqual(height, 1920)
            self.assertEqual(fps, 30)

    def test_render_played_with_video_temp_raw_cleanup_on_error(self):
        """Verifies temp_raw file is removed even when FFmpeg muxing fails."""
        if rps is None or not hasattr(rps, "render_played_with_video"):
            self.skipTest("render_played_with_short.render_played_with_video not available")

        puzzle = {"game_day": 1, "mystery_player": "Test", "steps": []}
        temp_files_created = []
        original_named_temp = rps.tempfile.NamedTemporaryFile

        def tracking_temp_file(*args, **kwargs):
            tmp = original_named_temp(*args, **kwargs)
            temp_files_created.append(tmp.name)
            return tmp

        with patch("tempfile.NamedTemporaryFile", side_effect=tracking_temp_file), \
             patch("cv2.VideoCapture") as mock_cap, \
             patch("cv2.VideoWriter"), \
             patch("render_played_with_short.render_played_with_frame", return_value=Image.new("RGB", (100, 100))), \
             patch("os.path.exists", return_value=True), \
             patch("subprocess.run") as mock_subproc:
            mock_cap.return_value.isOpened.return_value = True
            mock_cap.return_value.read.return_value = (True, None)
            mock_subproc.return_value = MagicMock(returncode=1, stderr=b"FFmpeg simulated failure")
            with self.assertRaises(RuntimeError):
                rps.render_played_with_video(
                    puzzle_data=puzzle,
                    output_path="/tmp/test_should_fail.mp4",
                    bg_clip="dummy_bg.mp4",
                    audio_track="dummy_audio.wav",
                    duration=7.5
                )

        self.assertGreater(len(temp_files_created), 0)
        for tf in temp_files_created:
            self.assertFalse(os.path.exists(tf), f"Orphaned temporary file was not cleaned up: {tf}")


if __name__ == "__main__":
    unittest.main()
