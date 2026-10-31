import unittest
from unittest.mock import patch
import json
from scripts.verify_anyone_but_llm import (
    parse_json_response,
    verify_puzzle_table,
    update_puzzle_in_csv
)


class TestAnyoneButVerifier(unittest.TestCase):
    def test_parse_json_response_clean(self):
        txt = '{"qualifying_players": ["Ederson", "Ruben Dias"], "confidence": 0.95}'
        parsed = parse_json_response(txt)
        self.assertIsNotNone(parsed)
        self.assertEqual(len(parsed["qualifying_players"]), 2)

    def test_parse_json_response_markdown_fenced(self):
        txt = '```json\n{"qualifying_players": ["Ederson"], "confidence": 1.0}\n```'
        parsed = parse_json_response(txt)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["qualifying_players"], ["Ederson"])

    def test_parse_json_response_noisy(self):
        txt = 'Here is the result:\n{"qualifying_players": ["Javi Garcia"]}\nHope that helps!'
        parsed = parse_json_response(txt)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["qualifying_players"], ["Javi Garcia"])

    @patch('scripts.verify_anyone_but_llm.call_gemini')
    def test_verify_puzzle_table_detects_missing(self, mock_gemini):
        mock_gemini.return_value = {
            "qualifying_players": ["Ederson", "Ruben Dias", "Claudio Bravo"],
            "model_used": "gemini-2.5-flash"
        }
        existing = ["Ederson", "Ruben Dias"]
        status, missing, model = verify_puzzle_table("Bernardo Silva", "Played for Manchester City", existing)
        self.assertEqual(status, "ok")
        self.assertIn("Claudio Bravo", missing)
        self.assertNotIn("Ederson", missing)
        self.assertNotIn("Bernardo Silva", missing)

    @patch('scripts.verify_anyone_but_llm.call_gemini')
    def test_verify_puzzle_table_excludes_excluded_star(self, mock_gemini):
        # Ensure that even if Gemini accidentally returns the excluded star, it is filtered out
        mock_gemini.return_value = {
            "qualifying_players": ["Bernardo Silva", "Ederson"],
            "model_used": "gemini-2.5-flash"
        }
        existing = ["Ederson"]
        status, missing, model = verify_puzzle_table("Bernardo Silva", "Played for Benfica", existing)
        self.assertEqual(status, "ok")
        self.assertEqual(missing, [])

    @patch('scripts.verify_anyone_but_llm.call_gemini')
    def test_verify_puzzle_table_enforces_peak_value_cutoff(self, mock_gemini):
        # Test that candidate below threshold is filtered out by programmatic guard
        mock_gemini.return_value = {
            "qualifying_players": ["Axel Witsel", "Angel Di Maria"],
            "model_used": "gemini-2.5-flash"
        }
        existing = []
        mock_catalog = {
            "axel witsel": {"Name": "Axel Witsel", "MarketValue": 40_000_000},
            "angel di maria": {"Name": "Ángel Di María", "MarketValue": 80_000_000}
        }
        status, missing, model = verify_puzzle_table(
            "Bernardo Silva",
            "Played for Benfica (peak market value ≥ €80M)",
            existing,
            catalog=mock_catalog
        )
        self.assertEqual(status, "ok")
        self.assertIn("Angel Di Maria", missing)
        self.assertNotIn("Axel Witsel", missing)


if __name__ == '__main__':
    unittest.main()
