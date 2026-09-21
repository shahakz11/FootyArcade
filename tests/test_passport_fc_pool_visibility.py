import os
import re
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPassportFcPoolVisibility(unittest.TestCase):

    def test_passport_fc_template_pool_visibility_gating(self):
        """Verify templates/passport_fc_template.html conceals pool counts during active gameplay."""
        template_path = os.path.join(REPO_ROOT, "templates", "passport_fc_template.html")
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Verify poolText is gated behind gameOver
        self.assertIn("if (gameOver) {", content)
        self.assertIn("poolText = poolCount === 1 ? 'Only 1 Qualifying Unicorn!' : `${poolCount} Qualifying Players`;", content)
        self.assertIn("poolText = isUnicorn ? 'The Unicorn Stamp' : `Stamp #${idx + 1}`;", content)

        # Verify answerDetail poolBadge is gated behind gameOver
        self.assertIn("const poolBadge = gameOver ? `<span class=\"text-[11px] font-mono text-accent/80\">${poolCount} total qualifying</span>` : '';", content)

        # Verify end-game summary breakdown retains player count and accordion
        self.assertIn("populateSummaryBreakdown", content)
        self.assertIn("View all ${canonicalPool.length} qualifying players", content)

    def test_fetch_daily_spanish_replacements(self):
        """Verify fetch_daily.py contains Spanish translations for the new Passport FC active ladder labels."""
        fetch_daily_path = os.path.join(REPO_ROOT, "fetch_daily.py")
        with open(fetch_daily_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn('("Stamp #${idx + 1}", "Sello #${idx + 1}")', content)
        self.assertIn("The Unicorn Stamp", content)
        self.assertIn("El Sello Unicornio", content)

    def test_compiled_passport_games_contain_gating(self):
        """Verify compiled games in games/ and es/games/ have the active gameplay pool count concealment."""
        en_game_path = os.path.join(REPO_ROOT, "games", "passport_fc.html")
        es_game_path = os.path.join(REPO_ROOT, "es", "games", "passport_fc.html")

        if os.path.exists(en_game_path):
            with open(en_game_path, "r", encoding="utf-8") as f:
                en_content = f.read()
            self.assertIn("isUnicorn ? 'The Unicorn Stamp' : `Stamp #${idx + 1}`", en_content)
            self.assertIn("const poolBadge = gameOver ?", en_content)

        if os.path.exists(es_game_path):
            with open(es_game_path, "r", encoding="utf-8") as f:
                es_content = f.read()
            self.assertIn("Sello #${idx + 1}", es_content)
            self.assertIn("El Sello Unicornio", es_content)
            self.assertIn("const poolBadge = gameOver ?", es_content)


if __name__ == "__main__":
    unittest.main()
