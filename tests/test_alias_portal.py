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
    get_player_alias_map,
    get_hidden_clubs,
    get_hidden_players,
    filter_and_canonicalize_clubs,
    filter_and_canonicalize_players,
    filter_hidden_players,
    normalize_search_text
)
from scripts.alias_portal import app


class TestAliasPortal(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from scripts.alias_utils import get_config_path
        import scripts.alias_portal as ap
        cls.cfg_path = get_config_path()
        cls.original_content = None
        if os.path.exists(cls.cfg_path):
            with open(cls.cfg_path, "r", encoding="utf-8") as f:
                cls.original_content = f.read()

        # Seed test catalog with curated test fixtures for sub-second test runs
        test_catalog = []
        for ent in ap.CURATED_ENTITIES:
            item = dict(ent)
            item["norm_name"] = ap.normalize_search_text(item["Name"])
            item["norm_full"] = ap.normalize_search_text(item.get("FullName", item["Name"]))
            test_catalog.append(item)

        test_catalog.append({
            "Name": "Lionel Messi",
            "FullName": "Lionel Andrés Messi",
            "DOB": "1987-06-24",
            "Nationality": "Argentina",
            "Position": "Right Winger",
            "Clubs": "Barcelona, Paris Saint-Germain, Inter Miami",
            "MarketValue": 35000000,
            "norm_name": ap.normalize_search_text("Lionel Messi"),
            "norm_full": ap.normalize_search_text("Lionel Andrés Messi")
        })
        test_catalog.append({
            "Name": "Ángel Di María",
            "FullName": "Ángel Fabián Di María",
            "DOB": "1988-02-14",
            "Nationality": "Argentina",
            "Position": "Right Winger",
            "Clubs": "Benfica, Real Madrid, Manchester United, Paris Saint-Germain, Juventus",
            "MarketValue": 4000000,
            "norm_name": ap.normalize_search_text("Ángel Di María"),
            "norm_full": ap.normalize_search_text("Ángel Fabián Di María")
        })
        ap.CACHED_PLAYER_CATALOG = test_catalog

    @classmethod
    def tearDownClass(cls):
        if cls.original_content is not None and os.path.exists(cls.cfg_path):
            with open(cls.cfg_path, "w", encoding="utf-8") as f:
                f.write(cls.original_content)

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()
        if self.original_content is not None and os.path.exists(self.cfg_path):
            with open(self.cfg_path, "w", encoding="utf-8") as f:
                f.write(self.original_content)

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

        # Test alias search: "rafael alcantara" matches Rafinha / Rafael Alcântara
        res_raf = self.client.get('/api/search/players?q=rafael alcantara&limit=5')
        self.assertEqual(res_raf.status_code, 200)
        data_raf = json.loads(res_raf.data)
        self.assertTrue(len(data_raf) > 0)
        self.assertTrue(any("Rafael Alc" in (p.get("Name", "") if isinstance(p, dict) else p) for p in data_raf))


    def test_player_alias_mapping_and_canonicalization(self):
        mock_config = {
            "version": 1,
            "clubs": {"groups": [], "hidden_standalone": []},
            "players": {
                "groups": [
                    {
                        "display_name": "Raphinha",
                        "aliases": ["Raphael Dias Belloli", "R. Belloli"],
                        "hidden": False
                    },
                    {
                        "display_name": "Secret Player",
                        "aliases": ["Alias Secret"],
                        "hidden": True
                    }
                ],
                "hidden": ["Banned Player"]
            }
        }
        alias_map = get_player_alias_map(mock_config)
        self.assertEqual(alias_map.get("Raphael Dias Belloli"), "Raphinha")
        self.assertEqual(alias_map.get("R. Belloli"), "Raphinha")
        self.assertEqual(alias_map.get("Raphinha"), "Raphinha")

        raw_players = [
            "Raphael Dias Belloli",
            "Banned Player",
            "Secret Player",
            "Alias Secret",
            "Lionel Messi"
        ]
        filtered = filter_and_canonicalize_players(raw_players, mock_config)
        self.assertEqual(filtered, ["Raphinha", "Lionel Messi"])

        # Dict format
        dict_players = [
            {"Name": "Raphael Dias Belloli", "Goals": 10},
            {"Name": "Banned Player", "Goals": 5},
            {"Name": "Lionel Messi", "Goals": 30}
        ]
        filtered_dicts = filter_and_canonicalize_players(dict_players, mock_config)
        self.assertEqual(len(filtered_dicts), 2)
        self.assertEqual(filtered_dicts[0]["Name"], "Raphinha")
        self.assertEqual(filtered_dicts[1]["Name"], "Lionel Messi")

    def test_separate_alias_function(self):
        from scripts.alias_utils import separate_alias
        mock_config = {
            "version": 1,
            "clubs": {
                "groups": [
                    {
                        "display_name": "Sporting CP",
                        "aliases": ["Sporting Lisbon", "Sporting Portugal"],
                        "hidden": False
                    }
                ],
                "hidden_standalone": []
            },
            "players": {
                "groups": [
                    {
                        "display_name": "Rafinha",
                        "aliases": ["Rafinha Alcantara", "Rafael Alcantara"],
                        "hidden": False
                    }
                ],
                "hidden": []
            }
        }

        # Separate club alias
        success, msg, cfg = separate_alias("clubs", "Sporting CP", "Sporting Portugal", new_display_name="Sporting Portugal", config=mock_config)
        self.assertTrue(success)
        sporting_group = next(g for g in cfg["clubs"]["groups"] if g["display_name"] == "Sporting CP")
        self.assertNotIn("Sporting Portugal", sporting_group["aliases"])
        self.assertIn("Sporting Lisbon", sporting_group["aliases"])
        new_group = next((g for g in cfg["clubs"]["groups"] if g["display_name"] == "Sporting Portugal"), None)
        self.assertIsNotNone(new_group)

        # Separate player alias
        success_p, msg_p, cfg_p = separate_alias("players", "Rafinha", "Rafinha Alcantara", new_display_name="Rafinha Alcantara", config=mock_config)
        self.assertTrue(success_p)
        rafinha_group = next(g for g in cfg_p["players"]["groups"] if g["display_name"] == "Rafinha")
        self.assertNotIn("Rafinha Alcantara", rafinha_group["aliases"])
        self.assertIn("Rafael Alcantara", rafinha_group["aliases"])
        new_p_group = next((g for g in cfg_p["players"]["groups"] if g["display_name"] == "Rafinha Alcantara"), None)
        self.assertIsNotNone(new_p_group)

    def test_api_separate_alias_endpoint(self):
        # Create a temporary group in config
        curr_res = self.client.get('/api/config')
        curr_data = json.loads(curr_res.data)["config"]

        test_group = {
            "display_name": "Temp Test Club",
            "aliases": ["Temp Sub Alias"],
            "hidden": False
        }
        curr_data["clubs"]["groups"].append(test_group)
        self.client.post('/api/config', json=curr_data)

        # Test separation
        sep_res = self.client.post('/api/alias/separate', json={
            "entity_type": "clubs",
            "group_display_name": "Temp Test Club",
            "alias_to_separate": "Temp Sub Alias",
            "new_display_name": "Temp Sub Alias"
        })
        self.assertEqual(sep_res.status_code, 200)
        sep_json = json.loads(sep_res.data)
        self.assertEqual(sep_json["status"], "success")

        # Cleanup
        clean_res = self.client.get('/api/config')
        clean_data = json.loads(clean_res.data)["config"]
        clean_data["clubs"]["groups"] = [
            g for g in clean_data["clubs"]["groups"] 
            if g["display_name"] not in ("Temp Test Club", "Temp Sub Alias")
        ]
        self.client.post('/api/config', json=clean_data)

    def test_api_disambiguation_candidates(self):
        res = self.client.get('/api/players/disambiguation-candidates')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIsInstance(data, list)
        # Verify Rafinha and Fernandinho are found in disambiguation candidates
        names = [c["name"] for c in data]
        self.assertIn("Rafinha", names)
        self.assertIn("Fernandinho", names)

    def test_api_search_players_rich_details_and_homonyms(self):
        # Search for "fernandinho"
        res = self.client.get('/api/search/players?q=fernandinho&limit=10')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) >= 2, f"Expected multiple distinct Fernandinhos, got {len(data)}")

        # Verify all items have rich details: Name, FullName, DOB, Position, Clubs
        for p in data:
            self.assertTrue(any(n in p["Name"] for n in ("Fernandinho", "Édis Baise", "Fernando")))
            self.assertIn("FullName", p)
            self.assertIn("DOB", p)
            self.assertIn("Position", p)
            self.assertIn("Clubs", p)

        # Verify Man City Fernandinho (Fernando Luiz Roza) is present with clubs
        man_city_f = next((p for p in data if "Manchester City" in p["Clubs"] or "Fernando Luiz Roza" in p["FullName"]), None)
        self.assertIsNotNone(man_city_f)
        self.assertEqual(man_city_f["FullName"], "Fernando Luiz Roza")
        self.assertIn("Shakhtar", man_city_f["Clubs"])

    def test_rich_hidden_players_config(self):
        # Test saving rich player objects in config without collapsing
        mock_rich_hidden = [
            {
                "Name": "Fernandinho",
                "FullName": "Fernando Luiz Roza",
                "DOB": "1985-05-04",
                "Nationality": "Brazil",
                "Position": "Defensive Midfield",
                "Clubs": "Manchester City, Shakhtar Donetsk"
            },
            {
                "Name": "Fernandinho",
                "FullName": "Édis Baise / Fernandinho",
                "DOB": "1985-11-25",
                "Nationality": "Brazil",
                "Position": "Left Winger",
                "Clubs": "Hellas Verona, Grêmio"
            }
        ]

        # Save config with rich hidden players
        curr_res = self.client.get('/api/config')
        curr_cfg = json.loads(curr_res.data)["config"]
        orig_hidden = list(curr_cfg["players"].get("hidden", []))

        curr_cfg["players"]["hidden"] = mock_rich_hidden
        save_res = self.client.post('/api/config', json=curr_cfg)
        self.assertEqual(save_res.status_code, 200)
        saved_cfg = json.loads(save_res.data)["config"]

        # Verify both distinct Fernandinhos are preserved
        self.assertEqual(len(saved_cfg["players"]["hidden"]), 2)
        self.assertEqual(saved_cfg["players"]["hidden"][0]["FullName"], "Fernando Luiz Roza")
        self.assertEqual(saved_cfg["players"]["hidden"][1]["FullName"], "Édis Baise / Fernandinho")

        # Verify get_hidden_players returns both names
        hidden_set = get_hidden_players(saved_cfg)
        self.assertIn("Fernandinho", hidden_set)
        self.assertIn("Fernando Luiz Roza", hidden_set)

        # Cleanup
        curr_cfg["players"]["hidden"] = orig_hidden
        self.client.post('/api/config', json=curr_cfg)

    def test_all_homonym_player_aliases_configured(self):
        """Verify that all duplicate/homonym players (Fernandinho, Rafinha, Fernando, Willian, etc.) have (All) aliases."""
        cfg = load_aliases_config()
        alias_map = get_player_alias_map(cfg)

        sample_homonyms = ["Fernandinho", "Rafinha", "Fernando", "Willian", "Danilo", "Paulinho", "Adriano", "Gabriel", "Marcelo", "Eduardo"]
        for name in sample_homonyms:
            canonical = alias_map.get(name)
            self.assertEqual(canonical, f"{name} (All)", f"Expected {name} to map to '{name} (All)', got '{canonical}'")

        # Test canonicalization of a player list
        raw_list = [
            {"Name": "Fernandinho", "Nationality": "Brazil", "Position": "Midfield", "MarketValue": 80000000},
            {"Name": "Willian", "Nationality": "Brazil", "Position": "Attack", "MarketValue": 50000000},
            {"Name": "Robert Lewandowski", "Nationality": "Poland", "Position": "Attack", "MarketValue": 30000000}
        ]
        canon_list = filter_and_canonicalize_players(raw_list, cfg)
        names = [p["Name"] for p in canon_list if isinstance(p, dict)]
        self.assertIn("Fernandinho (All)", names)
        self.assertIn("Willian (All)", names)
        self.assertIn("Robert Lewandowski", names)

        # Check that Fernandinho (All) has 'Fernandinho' in its Aliases
        f_item = next(p for p in canon_list if isinstance(p, dict) and p["Name"] == "Fernandinho (All)")
        self.assertIn("Fernandinho", f_item.get("Aliases", []))


if __name__ == '__main__':
    unittest.main()



