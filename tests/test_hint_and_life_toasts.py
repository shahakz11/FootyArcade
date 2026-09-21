import unittest
import os
import re

class TestHintAndLifeToasts(unittest.TestCase):
    """
    Automated regression tests for Task #41:
    Verifies that all 6 game templates, footy-ui.css, footy-ui.js, and footy-i18n.js
    contain consistent, localized toast notifications for Hints and +1 Life additions.
    """

    def setUp(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.css_path = os.path.join(self.base_dir, 'games', 'footy-ui.css')
        self.js_path = os.path.join(self.base_dir, 'games', 'footy-ui.js')
        self.i18n_path = os.path.join(self.base_dir, 'games', 'footy-i18n.js')
        self.templates_dir = os.path.join(self.base_dir, 'templates')

    def test_css_toast_info_styling(self):
        """Verify .fa-toast-info is styled with radiant amber arcade glow in footy-ui.css"""
        with open(self.css_path, 'r', encoding='utf-8') as f:
            css = f.read()

        self.assertIn('.fa-toast-info', css)
        self.assertIn('#ffd700', css)
        self.assertIn('rgba(255, 215, 0', css)

    def test_i18n_toast_dictionary_keys(self):
        """Verify toast_life_added and toast_hint_revealed exist for both EN and ES in footy-i18n.js"""
        with open(self.i18n_path, 'r', encoding='utf-8') as f:
            i18n = f.read()

        # English
        self.assertIn("toast_life_added: '+1 Life! ❤️'", i18n)
        self.assertIn("toast_hint_revealed: 'Hint revealed! 💡'", i18n)

        # Spanish
        self.assertIn("toast_life_added: '¡+1 Vida! ❤️'", i18n)
        self.assertIn("toast_hint_revealed: '¡Pista revelada! 💡'", i18n)

    def test_footy_lives_add_triggers_toast(self):
        """Verify FootyLives.prototype.add in footy-ui.js triggers a toast when lives are added"""
        with open(self.js_path, 'r', encoding='utf-8') as f:
            js = f.read()

        self.assertIn("this.add = (n = 1, reason = 'bonus', opts = {}) =>", js)
        self.assertIn("toast_life_added", js)
        self.assertIn("toast(toastMsg, 'success')", js)

    def test_top_transfers_hint_toast(self):
        """Verify revealHint in top_transfers_template.html dispatches FootyUI.toast with hint_revealed"""
        template_path = os.path.join(self.templates_dir, 'top_transfers_template.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('function revealHint(index)', content)
        self.assertIn('FootyUI.toast(hintToastMsg, \'info\')', content)
        self.assertIn('toast_hint_revealed', content)

    def test_top_scorers_hint_toast(self):
        """Verify revealHint in top_scorers_template.html dispatches FootyUI.toast with hint_revealed"""
        template_path = os.path.join(self.templates_dir, 'top_scorers_template.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('function revealHint(index)', content)
        self.assertIn('FootyUI.toast(hintToastMsg, \'info\')', content)
        self.assertIn('toast_hint_revealed', content)

    def test_club_connect_hint_toast(self):
        """Verify revealCardHint in club_connect_template.html dispatches FootyUI.toast with hint_revealed"""
        template_path = os.path.join(self.templates_dir, 'club_connect_template.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('function revealCardHint(index, silent = false)', content)
        self.assertIn('FootyUI.toast(hintToastMsg, \'info\')', content)
        self.assertIn('toast_hint_revealed', content)

    def test_transfer_destination_hint_toast(self):
        """Verify reveal-btn in transfer_destination_template.html dispatches FootyUI.toast with hint_revealed"""
        template_path = os.path.join(self.templates_dir, 'transfer_destination_template.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('FootyUI.toast(hintToastMsg, \'info\')', content)
        self.assertIn('toast_hint_revealed', content)

    def test_player_chain_hint_toast(self):
        """Verify hint-nat-btn and hint-pos-btn in player_chain_template.html dispatch FootyUI.toast with 💡"""
        template_path = os.path.join(self.templates_dir, 'player_chain_template.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn("FootyUI.toast(msg, 'info')", content)
        self.assertIn("Nationality revealed:", content)
        self.assertIn("Position revealed:", content)

    def test_passport_fc_hint_toast(self):
        """Verify revealActiveHint in passport_fc_template.html dispatches localized FootyUI.toast with hint_revealed"""
        template_path = os.path.join(self.templates_dir, 'passport_fc_template.html')
        with open(template_path, 'r', encoding='utf-8') as f:
            content = f.read()

        self.assertIn('FootyUI.toast(hintToastMsg, \'info\')', content)
        self.assertIn('toast_hint_revealed', content)


if __name__ == '__main__':
    unittest.main()
