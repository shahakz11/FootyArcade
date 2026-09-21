"""
test_rules_modal_navigation.py — Verification Suite for Task #26
================================================================
Validates:
1. All game templates in templates/ have the question mark button and how-to-play modal.
2. All compiled English game files (games/*.html) have the question mark button and modal.
3. All compiled Spanish game files (es/games/*.html) have the question mark button and localized modal copy.
4. games/footy-ui.js exports and executes initHowToPlay on DOM ready.
"""

import os
import json
import unittest


class TestRulesModalNavigation(unittest.TestCase):

    def setUp(self):
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.games_json_path = os.path.join(self.root_dir, "games.json")
        with open(self.games_json_path, "r", encoding="utf-8") as f:
            self.games = json.load(f)
        self.live_games = [g for g in self.games if g.get("status") != "coming_soon"]

    def test_footy_ui_has_init_how_to_play(self):
        """Verify footy-ui.js has initHowToPlay implementation."""
        ui_path = os.path.join(self.root_dir, "games", "footy-ui.js")
        self.assertTrue(os.path.exists(ui_path))
        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertIn("function initHowToPlay()", content)
        self.assertIn("how-to-play-btn", content)
        self.assertIn("how-to-play-modal", content)
        self.assertIn("initHowToPlay()", content)

    def test_all_templates_have_how_to_play_button_and_modal(self):
        """Verify every live game template contains the question mark button and modal structure."""
        for game in self.live_games:
            tmpl_file = game.get("templateFile")
            if not tmpl_file:
                continue
            tmpl_path = os.path.join(self.root_dir, "templates", tmpl_file)
            self.assertTrue(os.path.exists(tmpl_path), f"Template {tmpl_file} must exist")

            with open(tmpl_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn('id="how-to-play-btn"', content, f"{tmpl_file} missing #how-to-play-btn")
            self.assertIn('help_outline', content, f"{tmpl_file} missing help_outline icon")
            self.assertIn('id="how-to-play-modal"', content, f"{tmpl_file} missing #how-to-play-modal")
            self.assertIn('id="close-how-to-play-btn"', content, f"{tmpl_file} missing #close-how-to-play-btn")
            self.assertIn('id="close-how-to-play-btn2"', content, f"{tmpl_file} missing #close-how-to-play-btn2")
            self.assertIn('HOW TO PLAY', content, f"{tmpl_file} missing HOW TO PLAY heading")
            self.assertIn('GOT IT', content, f"{tmpl_file} missing GOT IT button")

    def test_compiled_english_games_have_how_to_play_modal(self):
        """Verify compiled games in games/ have the question mark button and modal."""
        for game in self.live_games:
            gid = game["id"]
            game_file = os.path.join(self.root_dir, "games", f"{gid}.html")
            self.assertTrue(os.path.exists(game_file), f"{game_file} must exist")

            with open(game_file, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn('id="how-to-play-btn"', content, f"{gid}.html missing #how-to-play-btn")
            self.assertIn('help_outline', content, f"{gid}.html missing help_outline icon")
            self.assertIn('id="how-to-play-modal"', content, f"{gid}.html missing #how-to-play-modal")
            self.assertIn('HOW TO PLAY', content, f"{gid}.html missing HOW TO PLAY heading")

    def test_compiled_spanish_games_have_localized_modal(self):
        """Verify compiled games in es/games/ have localized Spanish modal content."""
        for game in self.live_games:
            gid = game["id"]
            game_file = os.path.join(self.root_dir, "es", "games", f"{gid}.html")
            self.assertTrue(os.path.exists(game_file), f"{game_file} must exist")

            with open(game_file, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn('id="how-to-play-btn"', content, f"es/games/{gid}.html missing #how-to-play-btn")
            self.assertIn('help_outline', content, f"es/games/{gid}.html missing help_outline icon")
            self.assertIn('id="how-to-play-modal"', content, f"es/games/{gid}.html missing #how-to-play-modal")
            self.assertIn('CÓMO JUGAR', content, f"es/games/{gid}.html missing CÓMO JUGAR heading")
            self.assertIn('ENTENDIDO', content, f"es/games/{gid}.html missing ENTENDIDO button")
            self.assertIn('Objetivo:', content, f"es/games/{gid}.html missing localized Objetivo:")


if __name__ == "__main__":
    unittest.main()
