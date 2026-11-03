"""
tests/test_this_and_that_frontend.py — Verification of This & That Frontend Engine & UI
======================================================================================
Validates:
1. FootyLives supports both .lose() and .loseLife() alias.
2. FootyWrongGuesses supports .getGuesses() alias.
3. This & That template has the standardized #fa-lives-bar matching anyone_but.
4. This & That template contains both hint-btn and reveal-btn with window.revealPlayerCardManual.
5. In-progress persistence uses FootyStorage.saveInProgress and getInProgress.
6. Navigation arrows disable previous button when puzzleNum <= 1.
7. Partial win (50%+ answers without surrender) and streak recording in endGame.
8. GAMES_REGISTRY and isVarSupportedGame in footy-ui.js include this_and_that.
"""

import os
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestThisAndThatFrontend(unittest.TestCase):

    def setUp(self):
        self.template_path = os.path.join(PROJECT_ROOT, "templates", "this_and_that_template.html")
        self.footy_ui_path = os.path.join(PROJECT_ROOT, "games", "footy-ui.js")

        with open(self.template_path, "r", encoding="utf-8") as f:
            self.template_html = f.read()

        with open(self.footy_ui_path, "r", encoding="utf-8") as f:
            self.footy_ui_js = f.read()

    def test_footy_lives_and_wrong_guesses_aliases(self):
        """Verify footy-ui.js defines loseLife alias on FootyLives and getGuesses on FootyWrongGuesses."""
        self.assertIn("this.loseLife = this.lose;", self.footy_ui_js,
                      "FootyLives must alias loseLife to lose")
        self.assertIn("this.getGuesses = this.getAll;", self.footy_ui_js,
                      "FootyWrongGuesses must alias getGuesses to getAll")

    def test_var_and_registry_registered(self):
        """Verify this_and_that is in isVarSupportedGame and GAMES_REGISTRY."""
        self.assertIn("'this_and_that'", self.footy_ui_js)
        self.assertIn("id: 'this_and_that'", self.footy_ui_js)

    def test_fa_lives_bar_structure(self):
        """Verify #fa-lives-bar structure matches standard Playmaker UI (lives counter, +1 life, give up, score)."""
        self.assertIn('id="fa-lives-bar"', self.template_html)
        self.assertIn('id="lives-counter"', self.template_html)
        self.assertIn('id="add-life-btn"', self.template_html)
        self.assertIn('id="give-up-btn"', self.template_html)
        self.assertIn('id="found-count"', self.template_html)
        self.assertIn('id="total-count"', self.template_html)

    def test_reveal_player_buttons_and_manual_reveal(self):
        """Verify reveal button with visibility icon and revealPlayerCardManual exist in template."""
        self.assertIn('id="reveal-btn-${i}"', self.template_html)
        self.assertIn('window.revealPlayerCardManual', self.template_html)
        self.assertIn('manuallyRevealed', self.template_html)
        self.assertIn('FootyUI.confirm', self.template_html)

    def test_local_storage_persistence(self):
        """Verify in-progress state uses FootyStorage saveInProgress and getInProgress instead of sessionStorage."""
        self.assertIn('storage.saveInProgress', self.template_html)
        self.assertIn('storage.getInProgress', self.template_html)
        self.assertNotIn('sessionStorage.setItem', self.template_html)

    def test_previous_day_navigation_disabled_on_day_1(self):
        """Verify navigation logic disables prev button when puzzleNum <= 1."""
        self.assertIn('puzzleNum <= 1', self.template_html)
        self.assertIn('prevBtn.disabled = true;', self.template_html)
        self.assertIn("prevBtn.classList.add('opacity-30', 'pointer-events-none')", self.template_html)

    def test_partial_win_and_streak_recording(self):
        """Verify partial win (50%+ without surrender) and streak recording via storage.recordResult."""
        self.assertIn("score >= Math.ceil(totalAnswers / 2)", self.template_html)
        self.assertIn("!isFullWin && !isSurrender", self.template_html)
        self.assertIn("storage.recordResult(puzzleNum, isFullWin, score, totalAnswers, isBackInTime, outcome)", self.template_html)

    def test_var_answer_addition_and_in_progress_restore(self):
        """Verify VAR acceptance appends rather than replaces, and in-progress restore is non-destructive."""
        # 1. VAR adds answers rather than overwriting
        self.assertIn("targetIndex = validAnswerNames.length;", self.template_html)
        self.assertIn("validAnswerNames.push(playerName);", self.template_html)
        self.assertIn("createAnswerCard(targetIndex)", self.template_html)
        
        # 2. revealCardHint has silent flag to prevent mid-restore localStorage wipe
        self.assertIn("window.revealCardHint = function(index, silent = false)", self.template_html)
        self.assertIn("window.revealCardHint(idx, true);", self.template_html)
        
        # 3. Dynamic VAR expansion is restored on refresh
        self.assertIn("state.validAnswerNames.length > validAnswerNames.length", self.template_html)

    def test_back_in_time_wrapper_structure_for_modal(self):
        """Verify #bit-wrapper wraps #back-in-time-container so modal unhides without clearing container."""
        self.assertIn('id="bit-wrapper"', self.template_html)
        self.assertIn('id="back-in-time-container"', self.template_html)

    def test_modal_card_class_and_partial_styling(self):
        """Verify inner card of #result-modal has .fa-modal-card and supports .is-partial."""
        self.assertIn('fa-modal-card', self.template_html)
        self.assertIn('class="fa-modal-card bg-surface border border-accent/20 rounded-3xl', self.template_html)

    def test_restore_in_progress_state_score_and_wrong_guesses(self):
        """Verify restoreInProgressState restores score cleanly without duplicate increments and restores wrong guesses."""
        self.assertIn('wrongGuessesCtrl.restore(state.wrongGuesses)', self.template_html)
        self.assertIn('(typeof state.score === \'number\') ? state.score : guessedPlayers.size', self.template_html)

    def test_reopen_modal_preserves_outcome(self):
        """Verify reopen modal button calculates isPartial and outcome properly."""
        self.assertIn('const isFullWin = score >= totalAnswers;', self.template_html)
        self.assertIn('showResultModal(isFullWin, outcome, isPartial, false);', self.template_html)


if __name__ == "__main__":
    unittest.main()
