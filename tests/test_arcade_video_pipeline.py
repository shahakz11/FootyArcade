#!/usr/bin/env python3
import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.badge_manager import get_club_badge, normalize_club_name, generate_procedural_crest
from narration_tts import get_game_voice_script
from render_arcade_short import load_game_payload, render_top_header, render_bottom_cta, WIDTH, HEIGHT

class TestArcadeVideoPipeline(unittest.TestCase):

    def test_badge_resolution_and_normalization(self):
        # 1. Alias normalization
        self.assertEqual(normalize_club_name("FC Bayern Munich"), "Bayern Munich")
        self.assertEqual(normalize_club_name("Madrid"), "Real Madrid")

        # 2. Badge generation & sizing
        b1 = get_club_badge("Chelsea", size=(120, 120))
        self.assertEqual(b1.size, (120, 120))
        self.assertEqual(b1.mode, "RGBA")

        # 3. Procedural fallback for unknown club
        b_fallback = generate_procedural_crest("Unknown Rovers", size=(100, 100))
        self.assertEqual(b_fallback.size, (100, 100))
        self.assertEqual(b_fallback.mode, "RGBA")

    def test_game_payload_loading(self):
        # top_transfers
        payload_tt = load_game_payload("top_transfers")
        self.assertIn("target_name", payload_tt)
        self.assertIn("transfers", payload_tt)
        self.assertGreater(len(payload_tt["transfers"]), 0)

        # transfer_destination
        payload_td = load_game_payload("transfer_destination")
        self.assertIn("target_name", payload_td)
        self.assertIn("transfers", payload_td)
        self.assertGreater(len(payload_td["transfers"]), 0)

    def test_narration_script_cues(self):
        payload_tt = load_game_payload("top_transfers")
        script_tt = get_game_voice_script("top_transfers", target_name=payload_tt["target_name"], extra_data=payload_tt)
        self.assertIn("intro", script_tt)
        self.assertIn("guess_5", script_tt)
        self.assertIn("guess_2", script_tt)
        self.assertIn("cliffhanger", script_tt)
        self.assertIn("outro", script_tt)

        payload_td = load_game_payload("transfer_destination")
        script_td = get_game_voice_script("transfer_destination", target_name=payload_td["target_name"], extra_data=payload_td)
        self.assertIn("intro", script_td)
        self.assertIn("step_1", script_td)
        self.assertIn("cliffhanger", script_td)
        self.assertIn("outro", script_td)

    def test_header_and_cta_elements(self):
        h = render_top_header("CAN YOU GUESS THIS CLUB?")
        self.assertEqual(h.size, (WIDTH, 200))
        self.assertEqual(h.mode, "RGBA")

        cta = render_bottom_cta()
        self.assertEqual(cta.size, (WIDTH, 220))
        self.assertEqual(cta.mode, "RGBA")

if __name__ == "__main__":
    unittest.main()
