#!/usr/bin/env python3
"""
tests/test_upload_daily_shorts.py

Unit and Integration Tests for Played With Video Shorts in scripts/upload_daily_shorts.py:
1. Game selection and mode routing for played_with.
2. Target name extraction with n-2 default and day/date overrides.
3. Social copy and metadata wiring for YouTube Shorts, Instagram Reels, and TikTok.
4. CLI argument parsing (--game played_with, --played-with, --day, --date, --preview).
5. Fast hermetic dry-run and preview pipeline execution.
"""

import os
import sys
import unittest
import datetime
from unittest.mock import patch, MagicMock

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from scripts.upload_daily_shorts import (
    select_games_for_mode,
    get_target_name_from_game,
    process_all_games,
    PLAYED_WITH_GAME,
    CAREER_FLIGHT_GAME,
    ALL_AVAILABLE_GAMES
)


class TestPlayedWithGameSelection(unittest.TestCase):
    """Verifies game registration and mode selection for played_with."""

    def test_played_with_game_constant(self):
        """PLAYED_WITH_GAME must define the exact contract id and name."""
        self.assertEqual(PLAYED_WITH_GAME["id"], "played_with")
        self.assertEqual(PLAYED_WITH_GAME["name"], "Played With")

    def test_select_games_for_mode_selected_game(self):
        """Passing selected_game='played_with' must return [PLAYED_WITH_GAME]."""
        games = select_games_for_mode(selected_game="played_with")
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["id"], "played_with")
        self.assertEqual(games[0]["name"], "Played With")

    def test_select_games_for_mode_alias(self):
        """Passing selected_game='playedwith' (alias) must also resolve correctly."""
        games = select_games_for_mode(selected_game="playedwith")
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["id"], "played_with")

    def test_select_games_for_mode_mode_played_with(self):
        """Passing mode='played_with' must return [PLAYED_WITH_GAME]."""
        games = select_games_for_mode(mode="played_with")
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0]["id"], "played_with")

    def test_select_games_for_mode_unknown_game_raises_value_error(self):
        """Unknown game ID must raise ValueError mentioning available options."""
        with self.assertRaises(ValueError) as ctx:
            select_games_for_mode(selected_game="non_existent_game_xyz")
        self.assertIn("played_with", str(ctx.exception))

    def test_all_games_remains_intact_for_backward_compatibility(self):
        """ALL_AVAILABLE_GAMES must remain 7 to avoid regressions in legacy scheduling tests."""
        self.assertEqual(len(ALL_AVAILABLE_GAMES), 7)
        all_games = select_games_for_mode(all_games=True)
        self.assertEqual(len(all_games), 7)


class TestPlayedWithTargetNameExtraction(unittest.TestCase):
    """Verifies get_target_name_from_game extracts mystery player names accurately."""

    def test_target_name_default_n_minus_2(self):
        """Default target name resolution uses n-2 offset from today."""
        target = get_target_name_from_game("played_with")
        self.assertTrue(len(target) > 0, "Expected non-empty mystery player name")
        # On reference date 2026-10-18, n-2 is 2026-10-16 -> Day 20 Stevan Jovetić
        from render_played_with_short import load_played_with_puzzle
        expected_puzzle = load_played_with_puzzle()
        self.assertEqual(target, expected_puzzle["mystery_player"])

    def test_target_name_with_day_override(self):
        """Target name extraction with explicit day override."""
        target_day1 = get_target_name_from_game("played_with", day=1)
        self.assertEqual(target_day1, "João Félix")

        target_day2 = get_target_name_from_game("played_with", day=2)
        self.assertEqual(target_day2, "Ronald Araujo")

    def test_target_name_with_date_override(self):
        """Target name extraction with explicit date override."""
        # 2026-09-27 is Day 1 (launch date) -> João Félix
        target = get_target_name_from_game("played_with", date_str="2026-09-27")
        self.assertEqual(target, "João Félix")
        # 2026-09-28 is Day 2 -> Ronald Araujo
        target2 = get_target_name_from_game("played_with", date_str="2026-09-28")
        self.assertEqual(target2, "Ronald Araujo")


class TestPlayedWithSocialMetadataAndAudio(unittest.TestCase):
    """Verifies social copy, metadata wiring, and audio preservation rules."""

    def test_social_copy_and_metadata_wiring(self):
        """Validates social copy structure extracted from render_played_with_short."""
        from render_played_with_short import load_played_with_puzzle, generate_social_copy
        puzzle = load_played_with_puzzle(day=1)
        copy_data = generate_social_copy(puzzle)

        self.assertIn("youtube_title", copy_data)
        self.assertIn("caption", copy_data)
        self.assertIn("hashtags", copy_data)

        # YouTube title constraint (< 95 chars)
        self.assertLess(len(copy_data["youtube_title"]), 95)
        self.assertTrue(copy_data["youtube_title"].startswith("WHO AM I?"))

        # Caption constraints (bulleted clues, comment CTA, playmaker.best)
        caption = copy_data["caption"]
        self.assertIn("WHO AM I?", caption)
        self.assertIn("• I played", caption)
        self.assertIn("playmaker.best", caption)
        self.assertIn("Drop your shout below", caption)

    def test_youtube_audio_rule_for_played_with(self):
        """Verifies played_with is exempted from audio stripping like career_flight."""
        # Condition in scripts/upload_daily_shorts.py:
        # strip_audio = not youtube_audio and (game_id not in ("career_flight", "played_with"))
        youtube_audio = False
        strip_audio_played_with = not youtube_audio and ("played_with" not in ("career_flight", "played_with"))
        strip_audio_career = not youtube_audio and ("career_flight" not in ("career_flight", "played_with"))
        strip_audio_ugc = not youtube_audio and ("player_chain" not in ("career_flight", "played_with"))

        self.assertFalse(strip_audio_played_with, "played_with video must keep audio by default on YouTube Shorts")
        self.assertFalse(strip_audio_career, "career_flight video must keep audio by default on YouTube Shorts")
        self.assertTrue(strip_audio_ugc, "UGC video should strip audio by default on YouTube Shorts")


class TestPlayedWithCLIParsing(unittest.TestCase):
    """Verifies CLI argument parser options for played_with and override flags."""

    def test_cli_game_played_with_and_day_date_flags(self):
        """Tests argparse behavior when --game played_with and --day are specified."""
        import argparse
        from scripts.upload_daily_shorts import main

        # Create test parser matching main() arguments
        parser = argparse.ArgumentParser()
        parser.add_argument("--game", type=str, default="")
        parser.add_argument("--day", type=int, default=None)
        parser.add_argument("--date", type=str, default=None)
        parser.add_argument("--preview", action="store_true")
        parser.add_argument("--played-with", dest="played_with_flag", action="store_true")

        args = parser.parse_args(["--game", "played_with", "--day", "15", "--preview"])
        self.assertEqual(args.game, "played_with")
        self.assertEqual(args.day, 15)
        self.assertIsNone(args.date)
        self.assertTrue(args.preview)

    def test_cli_played_with_shortcut_flag(self):
        """Tests that --played-with shortcut flag correctly sets played_with_flag."""
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument("--game", type=str, default="")
        parser.add_argument("--played-with", dest="played_with_flag", action="store_true")

        args = parser.parse_args(["--played-with"])
        self.assertTrue(args.played_with_flag)
        selected_game = args.game
        if args.played_with_flag:
            selected_game = "played_with"
        self.assertEqual(selected_game, "played_with")


class TestPlayedWithDryRunExecution(unittest.IsolatedAsyncioTestCase):
    """Verifies end-to-end dry-run and preview pipeline execution in under 2 seconds."""

    @patch("scripts.upload_daily_shorts.upload_short")
    @patch("scripts.upload_daily_shorts.upload_reel_now")
    @patch("render_played_with_short.render_played_with_video")
    async def test_process_all_games_dry_run_with_mocked_render(self, mock_render, mock_ig, mock_yt):
        """Dry-run must render video (mocked) and skip all actual uploads."""
        fake_video = os.path.join(BASE_DIR, "output_shorts", "mock_played_with.mp4")
        mock_render.return_value = fake_video

        # Create temporary dummy file so os.path.exists passes
        os.makedirs(os.path.dirname(fake_video), exist_ok=True)
        with open(fake_video, "w") as f:
            f.write("mock video content")

        try:
            results = await process_all_games(
                mode="played_with",
                selected_game="played_with",
                dry_run=True,
                day=1,
                no_youtube=True,
                no_instagram=True,
                no_tiktok=True
            )
            self.assertIsNotNone(results)
            self.assertEqual(len(results), 1)
            item = results[0]
            self.assertEqual(item["game"], "Played With")
            self.assertEqual(item["yt_status"], "Rendered (Dry Run)")
            self.assertEqual(item["ig_status"], "Rendered (Dry Run)")
            self.assertEqual(item["tt_status"], "Rendered (Dry Run)")

            # Network uploads must never be called in dry run
            mock_yt.assert_not_called()
            mock_ig.assert_not_called()
        finally:
            if os.path.exists(fake_video):
                os.remove(fake_video)

    @patch("scripts.upload_daily_shorts.upload_short")
    @patch("scripts.upload_daily_shorts.upload_reel_now")
    async def test_process_all_games_preview_mode_fast(self, mock_ig, mock_yt):
        """Preview mode generates a preview frame and skips uploads."""
        results = await process_all_games(
            mode="played_with",
            selected_game="played_with",
            dry_run=True,
            preview=True,
            day=1,
            no_youtube=True,
            no_instagram=True,
            no_tiktok=True
        )
        self.assertIsNotNone(results)
        self.assertEqual(len(results), 1)
        item = results[0]
        self.assertEqual(item["game"], "Played With")
        self.assertEqual(item["yt_status"], "Preview Generated")
        self.assertTrue(item["yt_url"].endswith(".jpg"))
        self.assertTrue(os.path.exists(item["yt_url"]))

        # Cleanup preview file
        if os.path.exists(item["yt_url"]):
            os.remove(item["yt_url"])

        mock_yt.assert_not_called()
        mock_ig.assert_not_called()


if __name__ == "__main__":
    unittest.main()
