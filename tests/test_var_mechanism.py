"""
tests/test_var_mechanism.py — Test Suite for VAR Review Mechanism & Anti-Hallucination Integrity
"""

import os
import re
import unittest
import glob

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestVarMechanism(unittest.TestCase):

    def test_no_hardcoded_club_fallbacks_in_top_transfers_template(self):
        """Ensure templates/top_transfers_template.html has no hardcoded Schalke or Huntelaar fallbacks."""
        template_path = os.path.join(REPO_ROOT, "templates", "top_transfers_template.html")
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check for hardcoded fallbacks
        self.assertNotIn("|| 'Schalke'", content, "Found hardcoded 'Schalke' fallback in top_transfers_template.html")
        self.assertNotIn("playerName.toLowerCase().includes('huntelaar')", content, "Found hardcoded Huntelaar check in top_transfers_template.html")
        self.assertNotIn("you MUST set accepted=true", content, "Found forced acceptance prompt in top_transfers_template.html")

    def test_no_hardcoded_club_fallbacks_in_compiled_top_transfers(self):
        """Ensure all compiled top_transfers HTML files (English & Spanish) are free of hardcoded fallbacks."""
        patterns = [
            os.path.join(REPO_ROOT, "games", "top_transfers*.html"),
            os.path.join(REPO_ROOT, "es", "games", "top_transfers*.html")
        ]
        files = []
        for p in patterns:
            files.extend(glob.glob(p))

        self.assertGreater(len(files), 0, "No compiled top_transfers files found")

        for fpath in files:
            with open(fpath, "r", encoding="utf-8") as f:
                c = f.read()
            self.assertNotIn("|| 'Schalke'", c, f"Found hardcoded 'Schalke' fallback in {fpath}")
            self.assertNotIn("playerName.toLowerCase().includes('huntelaar')", c, f"Found hardcoded Huntelaar check in {fpath}")
            self.assertNotIn("you MUST set accepted=true", c, f"Found forced acceptance prompt in {fpath}")

    def test_google_apps_script_var_configuration(self):
        """Verify google-apps-script.js has strict anti-hallucination rules, Gemini + Groq waterfall, and to_club schema."""
        gas_path = os.path.join(REPO_ROOT, "google-apps-script.js")
        with open(gas_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check API Keys
        self.assertIn("GEMINI_API_KEY", content, "Missing GEMINI_API_KEY in google-apps-script.js")
        self.assertIn("GROQ_API_KEY", content, "Missing GROQ_API_KEY in google-apps-script.js")

        # Check Gemini search grounded models
        self.assertIn("gemini-2.5-flash", content, "Missing gemini-2.5-flash in google-apps-script.js")
        self.assertIn("gemini-2.5-flash-lite", content, "Missing gemini-2.5-flash-lite in google-apps-script.js")
        self.assertIn("googleSearch", content, "Missing googleSearch tool in google-apps-script.js")

        # Check high-quota Gemini text models
        self.assertIn("gemini-3.5-flash-lite", content, "Missing gemini-3.5-flash-lite in google-apps-script.js")
        self.assertIn("gemini-3.1-flash-lite", content, "Missing gemini-3.1-flash-lite in google-apps-script.js")
        self.assertIn("gemini-3.7-flash", content, "Missing gemini-3.7-flash in google-apps-script.js")

        # Check Groq models list
        self.assertIn("openai/gpt-oss-120b", content, "Missing gpt-oss-120b in google-apps-script.js")
        self.assertIn("qwen/qwen3.8-27b", content, "Missing qwen3.8-27b in google-apps-script.js")
        self.assertIn("openai/gpt-oss-20b", content, "Missing gpt-oss-20b in google-apps-script.js")
        self.assertNotIn("llama-prompt-guard-2-22m", content, "Prompt guard model should not be in chat completions list")

        # Check JSON parser helper
        self.assertIn("function parseVarJsonResponse", content, "Missing parseVarJsonResponse in google-apps-script.js")

        # Check strict anti-hallucination prompt rules
        self.assertIn("ZERO HALLUCINATION POLICY", content, "Missing ZERO HALLUCINATION POLICY in prompt")
        self.assertIn("DEFAULT TO REJECT", content, "Missing DEFAULT TO REJECT rule in prompt")
        self.assertIn("to_club", content, "Missing to_club in schema/return output")
        self.assertIn("from_club", content, "Missing from_club in schema/return output")

    def test_top_scorers_clean_context(self):
        """Verify top_scorers template does not force acceptance in prompt context."""
        template_path = os.path.join(REPO_ROOT, "templates", "top_scorers_template.html")
        with open(template_path, "r", encoding="utf-8") as f:
            content = f.read()
        self.assertNotIn("you MUST set accepted=true", content)
        self.assertNotIn("approve the appeal and return", content)

    def test_google_apps_script_var_full_logging(self):
        """Verify google-apps-script.js includes dynamic header management and comprehensive logging columns."""
        gas_path = os.path.join(REPO_ROOT, "google-apps-script.js")
        with open(gas_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("function ensureVarReviewsHeaders", content)
        self.assertIn("function buildVarReviewsRow", content)
        self.assertIn("Prompt Sent to AI", content)
        self.assertIn("Full AI Response (Raw JSON)", content)
        self.assertIn("Full Request Payload", content)
        self.assertIn("Error / Exception Details", content)
        self.assertIn("Model Used", content)

    def test_verify_daily_puzzles_ai_waterfall_config(self):
        """Verify scripts/verify_daily_puzzles.py has PRIMARY_AI_MODELS and CONSENSUS_AI_MODELS configured with search grounding."""
        script_path = os.path.join(REPO_ROOT, "scripts", "verify_daily_puzzles.py")
        with open(script_path, "r", encoding="utf-8") as f:
            content = f.read()

        self.assertIn("PRIMARY_AI_MODELS", content)
        self.assertIn("CONSENSUS_AI_MODELS", content)
        self.assertIn("gemini-2.5-flash", content)
        self.assertIn("googleSearch", content)
        self.assertIn("GEMINI_API_KEY", content)
        self.assertIn("GROQ_API_KEY", content)
        self.assertIn("call_ai_api", content)


if __name__ == "__main__":
    unittest.main()

