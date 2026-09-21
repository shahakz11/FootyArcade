import os
import unittest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPassportFcAddLife(unittest.TestCase):

    def test_passport_fc_template_add_life_wiring(self):
        """Verify templates/passport_fc_template.html contains button, onChange toggle, and click handler."""
        template_path = os.path.join(REPO_ROOT, "templates", "passport_fc_template.html")
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        # 1. Check button in HTML lives bar
        self.assertIn('id="add-life-btn"', content)
        self.assertIn('+1 Life', content)

        # 2. Check onChange callback in FootyLives initialization
        self.assertIn('onChange: (val) => {', content)
        self.assertIn("addLifeBtn.classList.remove('hidden')", content)
        self.assertIn("addLifeBtn.classList.add('hidden')", content)

        # 3. Check click handler in setupEvents
        self.assertIn("addLifeBtn.addEventListener('click', () => {", content)
        self.assertIn("if (!gameOver) livesCtrl.add();", content)

    def test_player_chain_template_add_life_wiring(self):
        """Verify templates/player_chain_template.html contains button, onChange toggle, and click handler."""
        template_path = os.path.join(REPO_ROOT, "templates", "player_chain_template.html")
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check button in HTML
        self.assertIn('id="add-life-btn"', content)

        # Check onChange callback in FootyLives initialization
        self.assertIn('onChange: (val) => {', content)

        # Check click handler in setupEvents
        self.assertIn("addLifeBtn.addEventListener('click', () => {", content)
        self.assertIn("if (!gameOver) livesCtrl.add();", content)

    def test_compiled_passport_games_add_life(self):
        """Verify compiled games in games/ and es/games/ have add-life-btn and event handlers."""
        en_game_path = os.path.join(REPO_ROOT, "games", "passport_fc.html")
        es_game_path = os.path.join(REPO_ROOT, "es", "games", "passport_fc.html")

        if os.path.exists(en_game_path):
            with open(en_game_path, "r", encoding="utf-8") as f:
                en_content = f.read()
            self.assertIn('id="add-life-btn"', en_content)
            self.assertIn('+1 Life', en_content)
            self.assertIn('onChange: (val) =>', en_content)

        if os.path.exists(es_game_path):
            with open(es_game_path, "r", encoding="utf-8") as f:
                es_content = f.read()
            self.assertIn('id="add-life-btn"', es_content)
            self.assertIn('+1 Vida', es_content)
            self.assertIn('onChange: (val) =>', es_content)


if __name__ == "__main__":
    unittest.main()
