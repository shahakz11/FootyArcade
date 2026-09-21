import os
import glob
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPassportFcInitialLoad(unittest.TestCase):

    def test_passport_fc_template_no_static_barcelona_flash(self):
        """Verify templates/passport_fc_template.html has neutral placeholders and no hardcoded Barcelona in hero/step DOM."""
        template_path = os.path.join(REPO_ROOT, "templates", "passport_fc_template.html")
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Anchor club hero card header should be neutral placeholder "..."
        self.assertRegex(
            content,
            r'<h3 id="anchor-club-name"[^>]*>\s*\.\.\.\s*</h3>',
            "Anchor club name header must not contain hardcoded club text like BARCELONA."
        )

        # 2. Anchor club subtext should contain "..."
        self.assertRegex(
            content,
            r'<strong id="anchor-club-subtext"[^>]*>\.\.\.</strong>',
            "Anchor club subtext strong tag must not be hardcoded to Barcelona."
        )

        # 3. Active step label should be neutral
        self.assertIn('id="active-step-label"', content)
        self.assertIn('STEP 1 — NAME A QUALIFYING FOOTBALLER:', content)
        self.assertNotIn('STEP 1 — NAME A FRENCH PLAYER FOR BARCELONA:', content)

        # 4. Guess input placeholder should be generic
        self.assertRegex(
            content,
            r'placeholder="Type player name\.\.\."',
            "Input placeholder must be neutral and not mention Barcelona/French."
        )

        # 5. Modal club name should be neutral "..."
        self.assertRegex(
            content,
            r'<span id="modal-club-name"[^>]*>\.\.\.</span>',
            "Modal club name must be neutral placeholder."
        )

        # 6. initUI() JS fallback should not default to BARCELONA
        self.assertIn("activeGameData.club || '...'", content)
        self.assertNotIn("activeGameData.club || 'BARCELONA'", content)

    def test_compiled_passport_games_no_static_barcelona_flash(self):
        """Verify compiled games in games/ and es/games/ don't contain hardcoded static Barcelona in hero/step DOM."""
        en_games = glob.glob(os.path.join(REPO_ROOT, "games", "passport_fc*.html"))
        es_games = glob.glob(os.path.join(REPO_ROOT, "es", "games", "passport_fc*.html"))

        self.assertTrue(len(en_games) > 0, "Expected at least 1 English compiled passport game file")
        self.assertTrue(len(es_games) > 0, "Expected at least 1 Spanish compiled passport game file")

        for game_file in en_games + es_games:
            with open(game_file, "r", encoding="utf-8") as f:
                content = f.read()

            rel_path = os.path.relpath(game_file, REPO_ROOT)

            # Check anchor club header
            self.assertRegex(
                content,
                r'<h3 id="anchor-club-name"[^>]*>\s*\.\.\.\s*</h3>',
                f"File {rel_path} has hardcoded anchor-club-name instead of clean placeholder."
            )

            # Check subtext
            self.assertRegex(
                content,
                r'<strong id="anchor-club-subtext"[^>]*>\.\.\.</strong>',
                f"File {rel_path} has hardcoded anchor-club-subtext."
            )

            # Check step label does not have legacy Barcelona string
            self.assertNotIn(
                'NAME A FRENCH PLAYER FOR BARCELONA',
                content,
                f"File {rel_path} contains legacy French player Barcelona text."
            )
            self.assertNotIn(
                'NOMBRA A UN JUGADOR FRANCÉS DEL BARCELONA',
                content,
                f"File {rel_path} contains legacy Spanish French player Barcelona text."
            )

            # Check input placeholder does not mention Barcelona
            self.assertNotIn(
                'French footballer who played for Barcelona',
                content,
                f"File {rel_path} contains hardcoded French footballer placeholder."
            )
            self.assertNotIn(
                'futbolista francés que haya jugado en el Barcelona',
                content,
                f"File {rel_path} contains hardcoded Spanish placeholder."
            )


if __name__ == "__main__":
    unittest.main()
