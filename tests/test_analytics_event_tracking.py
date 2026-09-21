import os
import re
import json
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestAnalyticsEventTracking(unittest.TestCase):

    def test_google_apps_script_event_headers(self):
        """Verify google-apps-script.js includes all required Events headers and dynamic mapper logic."""
        gas_path = os.path.join(REPO_ROOT, "google-apps-script.js")
        with open(gas_path, "r", encoding="utf-8") as f:
            gas_content = f.read()

        expected_headers = [
            "Timestamp",
            "Event Name",
            "Game ID",
            "Puzzle Number",
            "Score",
            "Max Score",
            "Lives Left",
            "Won",
            "Is Correct",
            "Guess",
            "Step",
            "Target",
            "Extra Details",
            "URL",
            "Visitor ID",
            "Session ID",
            "URL Source",
        ]

        for header in expected_headers:
            self.assertTrue(
                f"'{header}'" in gas_content or f'"{header}"' in gas_content,
                f"Missing header '{header}' in google-apps-script.js",
            )

        self.assertIn("ensureEventsHeaders", gas_content)
        self.assertIn("buildEventsRow", gas_content)
        self.assertTrue("payload.isCorrect" in gas_content or "payload.correct" in gas_content)
        self.assertIn("payload.guess", gas_content)
        self.assertTrue("payload.step" in gas_content or "payload.slot" in gas_content)
        self.assertIn("payload.target", gas_content)

    def test_footy_ui_tracking_exports_and_helpers(self):
        """Verify games/footy-ui.js exports semantic event helper functions and handles event payloads."""
        footy_ui_path = os.path.join(REPO_ROOT, "games", "footy-ui.js")
        with open(footy_ui_path, "r", encoding="utf-8") as f:
            ui_content = f.read()

        required_helpers = [
            "trackEvent",
            "trackGuess",
            "trackHint",
            "trackSkip",
            "trackGiveUp",
            "trackExtraLife",
            "trackVarAppeal",
            "trackVarDecision",
            "trackGameEnd",
        ]

        for helper in required_helpers:
            self.assertIn(helper, ui_content, f"Missing '{helper}' in games/footy-ui.js")

        # Verify FootyModal handles isRestore and prevents duplicate game_end refires
        self.assertIn("isRestore", ui_content)
        self.assertIn("hasTrackedGameEnd", ui_content)
        # Verify FootyVAR triggers var_appeal and var_decision
        self.assertTrue("'var_appeal'" in ui_content or '"var_appeal"' in ui_content)
        self.assertTrue("'var_decision'" in ui_content or '"var_decision"' in ui_content)
        # Verify FootyLives triggers extra_life
        self.assertTrue("'extra_life'" in ui_content or '"extra_life"' in ui_content)

    def test_top_transfers_template_event_instrumentation(self):
        """Verify top_transfers_template.html tracks guess, hint, and give up."""
        path = os.path.join(REPO_ROOT, "templates", "top_transfers_template.html")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FootyUI.trackGuess", content)
        self.assertIn("FootyUI.trackHint", content)
        self.assertIn("FootyUI.trackGiveUp", content)

    def test_top_scorers_template_event_instrumentation(self):
        """Verify top_scorers_template.html tracks guess, hint, and give up."""
        path = os.path.join(REPO_ROOT, "templates", "top_scorers_template.html")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FootyUI.trackGuess", content)
        self.assertIn("FootyUI.trackHint", content)
        self.assertIn("FootyUI.trackGiveUp", content)

    def test_transfer_destination_template_event_instrumentation(self):
        """Verify transfer_destination_template.html tracks guess, hint, and give up."""
        path = os.path.join(REPO_ROOT, "templates", "transfer_destination_template.html")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FootyUI.trackGuess", content)
        self.assertIn("FootyUI.trackHint", content)
        self.assertIn("FootyUI.trackGiveUp", content)

    def test_club_connect_template_event_instrumentation(self):
        """Verify club_connect_template.html tracks guess, hint, and give up."""
        path = os.path.join(REPO_ROOT, "templates", "club_connect_template.html")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FootyUI.trackGuess", content)
        self.assertIn("FootyUI.trackHint", content)
        self.assertIn("FootyUI.trackGiveUp", content)

    def test_player_chain_template_event_instrumentation(self):
        """Verify player_chain_template.html tracks guess, hint, skip, and give up."""
        path = os.path.join(REPO_ROOT, "templates", "player_chain_template.html")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FootyUI.trackGuess", content)
        self.assertIn("FootyUI.trackHint", content)
        self.assertIn("FootyUI.trackSkip", content)
        self.assertIn("FootyUI.trackGiveUp", content)

    def test_passport_fc_template_event_instrumentation(self):
        """Verify passport_fc_template.html tracks guess, hint, skip, and give up, and triggers both success and failure feedback toasts."""
        path = os.path.join(REPO_ROOT, "templates", "passport_fc_template.html")
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("FootyUI.trackGuess", content)
        self.assertIn("FootyUI.trackHint", content)
        self.assertIn("FootyUI.trackSkip", content)
        self.assertIn("FootyUI.trackGiveUp", content)
        # Verify success feedback toast on right answer (Task #35)
        self.assertIn("STAMP COLLECTED!", content)
        # Verify incorrect guess feedback and VAR remain intact
        self.assertIn("INCORRECT GUESS", content)

    def test_compiled_games_contain_event_tracking(self):
        """Verify compiled games in games/ and es/games/ include the updated tracking calls."""
        games_to_check = [
            "games/top_transfers.html",
            "games/top_scorers.html",
            "games/transfer_destination.html",
            "games/club_connect.html",
            "games/player_chain.html",
            "games/passport_fc.html",
            "es/games/top_transfers.html",
            "es/games/passport_fc.html",
        ]

        for rel_path in games_to_check:
            full_path = os.path.join(REPO_ROOT, rel_path)
            self.assertTrue(os.path.exists(full_path), f"File {rel_path} does not exist")
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertTrue(
                "FootyUI.trackGuess" in content or "FootyUI.trackGiveUp" in content,
                f"{rel_path} is missing compiled event tracking hooks",
            )

    def test_restore_game_prevents_duplicate_game_end_event(self):
        """Verify templates and compiled games set isRestore flag to prevent refiring game_end on landing."""
        templates_to_check = [
            "templates/top_transfers_template.html",
            "templates/top_scorers_template.html",
            "templates/transfer_destination_template.html",
            "templates/club_connect_template.html",
            "templates/player_chain_template.html",
        ]

        for tmpl_rel in templates_to_check:
            full_path = os.path.join(REPO_ROOT, tmpl_rel)
            with open(full_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("function checkAlreadyPlayed", content, f"Missing checkAlreadyPlayed in {tmpl_rel}")
            self.assertIn("isRestore", content, f"Missing isRestore in {tmpl_rel}")


if __name__ == "__main__":
    unittest.main()
