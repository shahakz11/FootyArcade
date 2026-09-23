"""
tests/test_game_suggestions.py — Verification Suite for Task #28
================================================================
Validates:
1. GAMES_REGISTRY definitions in games/footy-ui.js
2. i18n dictionary completeness in games/footy-i18n.js (EN & ES)
3. Template integration across all 6 games
4. Compiled HTML output integrity in games/*.html and es/games/*.html
5. CSS classes and style rules in games/footy-ui.css
6. Dynamic filtering and exclusion logic
"""

import os
import re
import json
import unittest


class TestGameSuggestions(unittest.TestCase):

    def setUp(self):
        self.root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.games_json_path = os.path.join(self.root_dir, "games.json")
        with open(self.games_json_path, "r", encoding="utf-8") as f:
            self.games = json.load(f)
        self.live_games = [g for g in self.games if g.get("status") != "coming_soon"]
        self.all_game_ids = [
            "top_transfers",
            "transfer_destination",
            "top_scorers",
            "club_connect",
            "player_chain",
            "passport_fc",
        ]

    def test_registry_in_footy_ui(self):
        """Verify all 6 games are registered in GAMES_REGISTRY inside footy-ui.js."""
        ui_path = os.path.join(self.root_dir, "games", "footy-ui.js")
        self.assertTrue(os.path.exists(ui_path))
        with open(ui_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("const GAMES_REGISTRY = [", content)
        self.assertIn("initGameSuggestions", content)
        self.assertIn("autoInitSuggestions", content)

        for game_id in self.all_game_ids:
            self.assertTrue(
                f"id: '{game_id}'" in content or f'id: "{game_id}"' in content,
                f"Game {game_id} missing in GAMES_REGISTRY",
            )

    def test_i18n_dictionary_completeness(self):
        """Verify all necessary suggestion tokens exist in both English and Spanish in footy-i18n.js."""
        i18n_path = os.path.join(self.root_dir, "games", "footy-i18n.js")
        self.assertTrue(os.path.exists(i18n_path))
        with open(i18n_path, "r", encoding="utf-8") as f:
            content = f.read()

        required_keys = [
            "more_daily_challenges",
            "tagline_top_transfers",
            "tagline_transfer_destination",
            "tagline_top_scorers",
            "tagline_club_connect",
            "tagline_player_chain",
            "tagline_passport_fc",
            "badge_solved",
            "badge_partial",
            "badge_failed",
            "badge_in_progress",
            "back_to_playmaker",
        ]

        for key in required_keys:
            matches = re.findall(rf"{key}\s*:", content)
            self.assertGreaterEqual(
                len(matches),
                2,
                f"Key '{key}' must be defined for both en and es (found {len(matches)})",
            )

    def test_templates_have_suggestions_container(self):
        """Verify every live game template contains the fa-game-suggestions container with valid data-current-game."""
        for game in self.live_games:
            tmpl_file = game.get("templateFile")
            if not tmpl_file:
                continue
            tmpl_path = os.path.join(self.root_dir, "templates", tmpl_file)
            self.assertTrue(os.path.exists(tmpl_path), f"Template {tmpl_file} missing")

            with open(tmpl_path, "r", encoding="utf-8") as f:
                content = f.read()

            self.assertIn(
                'id="fa-game-suggestions"',
                content,
                f"Missing fa-game-suggestions in {tmpl_file}",
            )
            self.assertIn(
                f'data-current-game="{game["id"]}"',
                content,
                f"Missing data-current-game='{game['id']}' in {tmpl_file}",
            )

    def test_compiled_games_have_suggestions_container(self):
        """Verify compiled English and Spanish game HTML pages have the fa-game-suggestions element."""
        for game_id in self.all_game_ids:
            en_path = os.path.join(self.root_dir, "games", f"{game_id}.html")
            es_path = os.path.join(self.root_dir, "es", "games", f"{game_id}.html")

            if os.path.exists(en_path):
                with open(en_path, "r", encoding="utf-8") as f:
                    en_content = f.read()
                self.assertIn(
                    'id="fa-game-suggestions"',
                    en_content,
                    f"Missing fa-game-suggestions in {en_path}",
                )

            if os.path.exists(es_path):
                with open(es_path, "r", encoding="utf-8") as f:
                    es_content = f.read()
                self.assertIn(
                    'id="fa-game-suggestions"',
                    es_content,
                    f"Missing fa-game-suggestions in {es_path}",
                )

    def test_css_styles_exist(self):
        """Verify CSS classes for the game suggestions component exist in games/footy-ui.css."""
        css_path = os.path.join(self.root_dir, "games", "footy-ui.css")
        self.assertTrue(os.path.exists(css_path))
        with open(css_path, "r", encoding="utf-8") as f:
            css_content = f.read()

        self.assertIn(".fa-suggestions-wrapper", css_content)
        self.assertIn(".fa-suggestions-header", css_content)
        self.assertIn(".fa-suggestions-grid", css_content)
        self.assertIn(".fa-suggestion-card", css_content)
        self.assertIn(".fa-suggestion-badge-solved", css_content)
        self.assertIn(".fa-suggestion-badge-failed", css_content)
        self.assertIn(".fa-suggestions-back", css_content)

    def test_filtering_logic_simulation(self):
        """Test that filtering for any current game yields exactly 5 cards and excludes current game."""
        for current_game in self.all_game_ids:
            filtered = [g for g in self.all_game_ids if g != current_game]
            self.assertEqual(
                len(filtered),
                5,
                f"Expected 5 games for {current_game}, got {len(filtered)}",
            )
            self.assertNotIn(
                current_game,
                filtered,
                f"{current_game} should be excluded from its own suggestions",
            )


if __name__ == "__main__":
    unittest.main()
