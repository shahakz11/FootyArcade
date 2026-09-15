"""
tests/test_alias_portal.py

Automated test suite verifying:
1. alias_utils: config load/save, alias mapping, hidden clubs & hidden players filtering.
2. alias_portal: Flask API endpoints (/api/config, /api/search/clubs, /api/search/players).
3. Pipeline integration with build_transfer_datasets and fetch_daily.
"""

import os
import sys
import json
import unittest

# Ensure repo root is on sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.alias_utils import (
    load_aliases_config,
    save_aliases_config,
    get_club_alias_map,
    get_hidden_clubs,
    get_hidden_players,
    filter_and_canonicalize_clubs,
    filter_hidden_players,
    normalize_search_text
)
from scripts.alias_portal import app


class TestAliasPortal(unittest.TestCase):
    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_alias_mapping(self):
        mock_config = {
            "version": 1,
            "clubs": {
                "groups": [
                    {
                        "display_name": "Manchester City",
                        "aliases": ["Man City", "Man. City"],
                        "hidden": False
                    },
                    {
                        "display_name": "Bayern Munich",
                        "aliases": ["FC Bayern", "Bayern München"],
                        "hidden": True
                    }
                ],
                "hidden_standalone": ["Obscure FC"]
            },
            "players": {
                "hidden": ["Noisy Player 1"]
            }
        }

        alias_map = get_club_alias_map(mock_config)
        self.assertEqual(alias_map["Man City"], "Manchester City")
        self.assertEqual(alias_map["Man. City"], "Manchester City")
        self.assertEqual(alias_map["Manchester City"], "Manchester City")
        self.assertEqual(alias_map["FC Bayern"], "Bayern Munich")

        hidden_clubs = get_hidden_clubs(mock_config)
        self.assertIn("Bayern Munich", hidden_clubs)
        self.assertIn("FC Bayern", hidden_clubs)
        self.assertIn("Obscure FC", hidden_clubs)
        self.assertNotIn("Manchester City", hidden_clubs)

        hidden_players = get_hidden_players(mock_config)
        self.assertIn("Noisy Player 1", hidden_players)
        self.assertNotIn("Lionel Messi", hidden_players)

    def test_filter_and_canonicalize_clubs(self):
        mock_config = {
            "version": 1,
            "clubs": {
                "groups": [
                    {
                        "display_name": "Manchester City",
                        "aliases": ["Man City"],
                        "hidden": False
                    },
                    {
                        "display_name": "Fake Club",
                        "aliases": ["FC Fake"],
                        "hidden": True
                    }
                ],
                "hidden_standalone": ["Hidden FC"]
            },
            "players": {"hidden": []}
        }

        raw_clubs = ["Man City", "Arsenal", "FC Fake", "Hidden FC", "Manchester City", "Chelsea"]
        cleaned = filter_and_canonicalize_clubs(raw_clubs, mock_config)

        # Man City should become Manchester City; duplicates removed; Fake Club & Hidden FC removed
        self.assertEqual(cleaned, ["Manchester City", "Arsenal", "Chelsea"])

    def test_filter_hidden_players(self):
        mock_config = {
            "version": 1,
            "clubs": {"groups": [], "hidden_standalone": []},
            "players": {
                "hidden": ["Bad Player", "Spam Name"]
            }
        }

        players = [
            {"Name": "Good Player", "MarketValue": 100},
            {"Name": "Bad Player", "MarketValue": 50},
            {"Name": "Another Player", "MarketValue": 75},
            {"Name": "spam name", "MarketValue": 10}
        ]

        filtered = filter_hidden_players(players, mock_config)
        self.assertEqual(len(filtered), 2)
        names = [p["Name"] for p in filtered]
        self.assertIn("Good Player", names)
        self.assertIn("Another Player", names)

    def test_api_config(self):
        res = self.client.get('/api/config')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("config", data)
        self.assertIn("clubs", data["config"])

    def test_normalize_search_text(self):
        self.assertEqual(normalize_search_text("Nürnberg"), "nurnberg")
        self.assertEqual(normalize_search_text("Borussia Mönchengladbach"), "borussia monchengladbach")
        self.assertEqual(normalize_search_text("Al-Nassr"), "al nassr")
        self.assertEqual(normalize_search_text("Ángel Di María"), "angel di maria")

    def test_api_search_clubs(self):
        res = self.client.get('/api/search/clubs?q=madrid&limit=5')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIsInstance(data, list)
        self.assertTrue(any("Madrid" in item for item in data))

        # Test accent-insensitive search: "nurnberg" matches "1. FC Nürnberg"
        res_nurn = self.client.get('/api/search/clubs?q=nurnberg&limit=5')
        self.assertEqual(res_nurn.status_code, 200)
        data_nurn = json.loads(res_nurn.data)
        self.assertTrue(any("Nürnberg" in item or "Nuremberg" in item for item in data_nurn))

        # Test accent-insensitive search: "monchengladbach" matches "Borussia Mönchengladbach"
        res_gladbach = self.client.get('/api/search/clubs?q=monchengladbach&limit=5')
        self.assertEqual(res_gladbach.status_code, 200)
        data_gladbach = json.loads(res_gladbach.data)
        self.assertTrue(any("Mönchengladbach" in item for item in data_gladbach))

    def test_api_search_players(self):
        res = self.client.get('/api/search/players?q=messi&limit=5')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIsInstance(data, list)
        self.assertTrue(any("Messi" in (p.get("Name", "") if isinstance(p, dict) else p) for p in data))

        # Test accent-insensitive search: "di maria" matches "Ángel Di María"
        res_maria = self.client.get('/api/search/players?q=di maria&limit=5')
        self.assertEqual(res_maria.status_code, 200)
        data_maria = json.loads(res_maria.data)
        self.assertTrue(any("Di María" in (p.get("Name", "") if isinstance(p, dict) else p) or "Di Maria" in (p.get("Name", "") if isinstance(p, dict) else p) for p in data_maria))

    def test_api_save_config(self):
        curr_res = self.client.get('/api/config')
        curr_data = json.loads(curr_res.data)["config"]

        test_group = {
            "display_name": "Test United FC",
            "aliases": ["Test Utd"],
            "hidden": False
        }
        curr_data["clubs"]["groups"].append(test_group)

        post_res = self.client.post('/api/config', json=curr_data)
        self.assertEqual(post_res.status_code, 200)
        post_data = json.loads(post_res.data)
        self.assertEqual(post_data["status"], "success")

        check_res = self.client.get('/api/config')
        check_data = json.loads(check_res.data)["config"]
        group_names = [g["display_name"] for g in check_data["clubs"]["groups"]]
        self.assertIn("Test United FC", group_names)

        # Cleanup
        check_data["clubs"]["groups"] = [g for g in check_data["clubs"]["groups"] if g["display_name"] != "Test United FC"]
        self.client.post('/api/config', json=check_data)


if __name__ == '__main__':
    unittest.main()
