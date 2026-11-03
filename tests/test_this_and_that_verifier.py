"""
tests/test_this_and_that_verifier.py — Unit tests for 'This & That' LLM Verifier
================================================================================
Fast, hermetic unittest suite (< 1s runtime) with mocked Gemini calls.
"""

import os
import sys
import csv
import json
import tempfile
import unittest
from unittest.mock import patch

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from scripts.verify_this_and_that_llm import (
    parse_json_response,
    verify_puzzle,
    update_puzzle_in_csv,
    get_gemini_api_key,
    _normalize_name,
)


class TestThisAndThatVerifier(unittest.TestCase):

    def setUp(self):
        self.mock_catalog = {
            _normalize_name("Frank Lampard"): {
                "Name": "Frank Lampard",
                "Nationality": "England",
                "Position": "Midfield",
                "MarketValue": 110000000,
            },
            _normalize_name("Rio Ferdinand"): {
                "Name": "Rio Ferdinand",
                "Nationality": "England",
                "Position": "Defender",
                "MarketValue": 80000000,
            },
            _normalize_name("Joe Cole"): {
                "Name": "Joe Cole",
                "Nationality": "England",
                "Position": "Midfield",
                "MarketValue": 35000000,
            },
            _normalize_name("Michael Carrick"): {
                "Name": "Michael Carrick",
                "Nationality": "England",
                "Position": "Midfield",
                "MarketValue": 30000000,
            },
            _normalize_name("Javier Mascherano"): {
                "Name": "Javier Mascherano",
                "Nationality": "Argentina",
                "Position": "Midfield",
                "MarketValue": 40000000,
            },
        }

    def _create_temp_csv(self, rows):
        fd, path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        fieldnames = [
            "game_day",
            "category",
            "statement_a",
            "statement_b",
            "statement_a_es",
            "statement_b_es",
            "total_answers",
            "answer_names",
            "answer_details",
        ]
        with open(path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        return path

    def test_parse_json_clean(self):
        """Test parsing valid clean JSON text."""
        raw = json.dumps({
            "qualifying_players": ["Frank Lampard", "Carlos Tevez"],
            "confidence": 0.98,
            "notes": "Both won UCL and played for West Ham"
        })
        parsed = parse_json_response(raw)
        self.assertIsNotNone(parsed)
        self.assertIn("qualifying_players", parsed)
        self.assertEqual(parsed["qualifying_players"], ["Frank Lampard", "Carlos Tevez"])
        self.assertEqual(parsed["confidence"], 0.98)

    def test_parse_json_markdown_fenced(self):
        """Test parsing markdown-fenced ```json ... ``` blocks."""
        fenced_1 = (
            "```json\n"
            "{\n"
            '  "qualifying_players": ["Frank Lampard", "Rio Ferdinand"],\n'
            '  "confidence": 0.95\n'
            "}\n"
            "```"
        )
        parsed_1 = parse_json_response(fenced_1)
        self.assertIsNotNone(parsed_1)
        self.assertEqual(parsed_1["qualifying_players"], ["Frank Lampard", "Rio Ferdinand"])

        fenced_2 = (
            "Here is the database check result:\n"
            "```\n"
            '{"qualifying_players": ["Joe Cole"]}\n'
            "```\n"
            "Hope this helps!"
        )
        parsed_2 = parse_json_response(fenced_2)
        self.assertIsNotNone(parsed_2)
        self.assertEqual(parsed_2["qualifying_players"], ["Joe Cole"])

        # Test embedded raw JSON
        embedded = "Preamble: {\"qualifying_players\": [\"Michael Carrick\"]} Trailing thoughts."
        parsed_3 = parse_json_response(embedded)
        self.assertIsNotNone(parsed_3)
        self.assertEqual(parsed_3["qualifying_players"], ["Michael Carrick"])

    @patch("scripts.verify_this_and_that_llm.call_gemini")
    def test_verify_puzzle_detects_missing(self, mock_gemini):
        """Test detecting qualifying players who are whitelisted but missing from existing answers."""
        mock_gemini.return_value = {
            "qualifying_players": ["Frank Lampard", "Rio Ferdinand", "Joe Cole"],
            "model_used": "gemini-2.5-flash",
        }

        csv_rows = [{
            "game_day": "1",
            "category": "trophy_club",
            "statement_a": "Won the UEFA Champions League",
            "statement_b": "Played for West Ham United",
            "statement_a_es": "Ganó la UEFA Champions League",
            "statement_b_es": "Jugó en el West Ham United",
            "total_answers": "2",
            "answer_names": json.dumps(["Frank Lampard", "Rio Ferdinand"]),
            "answer_details": json.dumps([
                {"name": "Frank Lampard", "detail_a": "Won the UEFA Champions League", "detail_b": "Played for West Ham United"},
                {"name": "Rio Ferdinand", "detail_a": "Won the UEFA Champions League", "detail_b": "Played for West Ham United"},
            ]),
        }]
        csv_path = self._create_temp_csv(csv_rows)

        status, missing, model_used = verify_puzzle(1, csv_path=csv_path, catalog=self.mock_catalog)

        self.assertEqual(status, "ok")
        self.assertEqual(missing, ["Joe Cole"])
        self.assertEqual(model_used, "gemini-2.5-flash")

    @patch("scripts.verify_this_and_that_llm.call_gemini")
    def test_verify_puzzle_filters_unwhitelisted(self, mock_gemini):
        """Test that unwhitelisted hallucinated candidates are discarded."""
        mock_gemini.return_value = {
            "qualifying_players": ["Frank Lampard", "Fictional Footballer 123", "Imaginary Player"],
            "model_used": "gemini-2.5-flash",
        }

        csv_rows = [{
            "game_day": "1",
            "category": "trophy_club",
            "statement_a": "Won the UEFA Champions League",
            "statement_b": "Played for West Ham United",
            "statement_a_es": "Ganó la UEFA Champions League",
            "statement_b_es": "Jugó en el West Ham United",
            "total_answers": "1",
            "answer_names": json.dumps(["Frank Lampard"]),
            "answer_details": json.dumps([
                {"name": "Frank Lampard", "detail_a": "Won the UEFA Champions League", "detail_b": "Played for West Ham United"},
            ]),
        }]
        csv_path = self._create_temp_csv(csv_rows)

        status, missing, model_used = verify_puzzle(1, csv_path=csv_path, catalog=self.mock_catalog)

        self.assertEqual(status, "ok")
        # "Fictional Footballer 123" and "Imaginary Player" must be discarded
        self.assertEqual(missing, [])
        self.assertEqual(model_used, "gemini-2.5-flash")

    @patch("scripts.verify_this_and_that_llm.call_gemini")
    def test_verify_puzzle_no_false_positives(self, mock_gemini):
        """Test that when all candidates returned are already in the puzzle, missing is empty."""
        mock_gemini.return_value = {
            "qualifying_players": ["Frank Lampard", "Rio Ferdinand"],
            "model_used": "gemini-2.0-flash",
        }

        csv_rows = [{
            "game_day": "1",
            "category": "trophy_club",
            "statement_a": "Won the UEFA Champions League",
            "statement_b": "Played for West Ham United",
            "statement_a_es": "Ganó la UEFA Champions League",
            "statement_b_es": "Jugó en el West Ham United",
            "total_answers": "2",
            "answer_names": json.dumps(["Frank Lampard", "Rio Ferdinand"]),
            "answer_details": json.dumps([
                {"name": "Frank Lampard", "detail_a": "Won the UEFA Champions League", "detail_b": "Played for West Ham United"},
                {"name": "Rio Ferdinand", "detail_a": "Won the UEFA Champions League", "detail_b": "Played for West Ham United"},
            ]),
        }]
        csv_path = self._create_temp_csv(csv_rows)

        status, missing, model_used = verify_puzzle(1, csv_path=csv_path, catalog=self.mock_catalog)

        self.assertEqual(status, "ok")
        self.assertEqual(missing, [])
        self.assertEqual(model_used, "gemini-2.0-flash")

    def test_update_puzzle_in_csv_appends_under_9(self):
        """Test that --fix appends missing players if pool < 9, capping at 9."""
        initial_answers = [f"Player {i}" for i in range(1, 8)]  # 7 players
        csv_rows = [{
            "game_day": "1",
            "category": "trophy_club",
            "statement_a": "Won the UEFA Champions League",
            "statement_b": "Played for West Ham United",
            "statement_a_es": "Ganó la UEFA Champions League",
            "statement_b_es": "Jugó en el West Ham United",
            "total_answers": str(len(initial_answers)),
            "answer_names": json.dumps(initial_answers),
            "answer_details": json.dumps([{"name": p} for p in initial_answers]),
        }]
        csv_path = self._create_temp_csv(csv_rows)

        # 3 missing candidates, but only 2 slots remaining (9 - 7 = 2)
        missing_candidates = ["Joe Cole", "Michael Carrick", "Javier Mascherano"]
        updated, added = update_puzzle_in_csv(1, missing_candidates, csv_path=csv_path, catalog=self.mock_catalog, dry_run=False)

        self.assertTrue(updated)
        self.assertEqual(added, ["Joe Cole", "Michael Carrick"])

        # Read back CSV
        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["total_answers"], "9")
        final_names = json.loads(rows[0]["answer_names"])
        self.assertEqual(len(final_names), 9)
        self.assertIn("Joe Cole", final_names)
        self.assertIn("Michael Carrick", final_names)
        self.assertNotIn("Javier Mascherano", final_names)

        # Check detail structure
        details = json.loads(rows[0]["answer_details"])
        self.assertEqual(len(details), 9)
        jc_detail = next(d for d in details if d["name"] == "Joe Cole")
        self.assertEqual(jc_detail["nationality"], "England")
        self.assertEqual(jc_detail["position"], "Midfield")
        self.assertEqual(jc_detail["detail_a"], "Won the UEFA Champions League")
        self.assertEqual(jc_detail["detail_b"], "Played for West Ham United")

    def test_update_puzzle_in_csv_skips_when_pool_full(self):
        """Test that update_puzzle_in_csv does nothing if pool >= 9."""
        initial_answers = [f"Player {i}" for i in range(1, 10)]  # 9 players
        csv_rows = [{
            "game_day": "1",
            "category": "trophy_club",
            "statement_a": "A",
            "statement_b": "B",
            "statement_a_es": "A_es",
            "statement_b_es": "B_es",
            "total_answers": "9",
            "answer_names": json.dumps(initial_answers),
            "answer_details": json.dumps([{"name": p} for p in initial_answers]),
        }]
        csv_path = self._create_temp_csv(csv_rows)

        updated, added = update_puzzle_in_csv(1, ["Joe Cole"], csv_path=csv_path, catalog=self.mock_catalog)
        self.assertFalse(updated)
        self.assertEqual(added, [])

    def test_update_puzzle_in_csv_dry_run(self):
        """Test that dry_run=True returns changes without modifying CSV."""
        initial_answers = ["Frank Lampard"]
        csv_rows = [{
            "game_day": "1",
            "category": "trophy_club",
            "statement_a": "A",
            "statement_b": "B",
            "statement_a_es": "A_es",
            "statement_b_es": "B_es",
            "total_answers": "1",
            "answer_names": json.dumps(initial_answers),
            "answer_details": json.dumps([{"name": "Frank Lampard"}]),
        }]
        csv_path = self._create_temp_csv(csv_rows)

        updated, added = update_puzzle_in_csv(1, ["Joe Cole"], csv_path=csv_path, catalog=self.mock_catalog, dry_run=True)
        self.assertTrue(updated)
        self.assertEqual(added, ["Joe Cole"])

        # Ensure file content remains untouched
        with open(csv_path, "r", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["total_answers"], "1")
        self.assertEqual(json.loads(rows[0]["answer_names"]), ["Frank Lampard"])

    def test_get_gemini_api_key(self):
        """Test retrieval of GEMINI_API_KEY from environment."""
        with patch.dict(os.environ, {"GEMINI_API_KEY": "test_env_key_12345"}):
            self.assertEqual(get_gemini_api_key(), "test_env_key_12345")


if __name__ == "__main__":
    unittest.main()
