"""
tests/test_player_disambiguation.py

Unit tests verifying:
1. Multi-entity player disambiguation: players with identical display names
   (e.g., 'Rafinha' b. 1985 vs 'Rafinha' b. 1993) do not have their club histories
   merged into a single fictitious career.
2. Intersecting clubs Bayern Munich + Inter + Barcelona yields NO match for 'Rafinha'.
3. Intersecting Bayern Munich + Schalke yields 'Rafinha' (Entity 1 / Marcio Rafael).
4. Intersecting Barcelona + Inter yields 'Rafinha' (Entity 2 / Rafael Alcantara).
5. Dataset builder correctly resolves entities to names post-intersection.
"""

import os
import sys
import unittest

# Ensure repo root is on sys.path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from build_player_chain_datasets import build_player_career_database


class TestPlayerDisambiguation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Build the actual career database from the raw transfer dataset
        cls.p_clubs, cls.player_metadata, cls.club_to_entities, cls.entity_name, cls.entity_clubs = build_player_career_database()

    def test_database_entity_level_separation(self):
        """Verify multiple entities exist for common homonyms like 'Rafinha'."""
        rafinha_entities = [
            e_id for e_id, name in self.entity_name.items()
            if name.strip().lower() == "rafinha"
        ]
        # There should be more than 1 Rafinha entity in the database
        self.assertGreater(len(rafinha_entities), 1, "Expected multiple entities with name 'Rafinha'")

    def test_rafinha_vidal_bayern_inter_barcelona_collision_prevented(self):
        """
        Verify that Bayern Munich + Inter + Barcelona does NOT resolve to 'Rafinha'.
        Previously, Bayern Rafinha (1985) and Barcelona/Inter Rafinha (1993) were merged,
        falsely making 'Rafinha' a valid candidate for Arturo Vidal's puzzle.
        """
        clubs = {"Bayern Munich", "Inter", "Barcelona"}
        
        # Collect entity matches via intersection
        valid_entities = None
        for c in clubs:
            e_set = self.club_to_entities.get(c, set())
            if valid_entities is None:
                valid_entities = set(e_set)
            else:
                valid_entities &= e_set

        valid_names = {self.entity_name[e] for e in (valid_entities or set())}

        # Vidal should be valid, Rafinha MUST NOT be valid
        self.assertNotIn("Rafinha", valid_names, "Collision bug: 'Rafinha' should not match Bayern + Inter + Barcelona")
        self.assertIn("Arturo Vidal", valid_names, "Arturo Vidal should match Bayern + Inter + Barcelona")

    def test_rafinha_bayern_schalke_matches(self):
        """
        Verify that Bayern Munich + FC Schalke 04 (or Schalke) correctly resolves to 'Rafinha' (entity b. 1985).
        """
        # Find Schalke name in database
        schalke_club = next((c for c in self.club_to_entities if "schalke" in c.lower()), "FC Schalke 04")
        clubs = {"Bayern Munich", schalke_club}
        
        valid_entities = None
        for c in clubs:
            e_set = self.club_to_entities.get(c, set())
            if valid_entities is None:
                valid_entities = set(e_set)
            else:
                valid_entities &= e_set

        valid_names = {self.entity_name[e] for e in (valid_entities or set())}
        self.assertIn("Rafinha", valid_names, "Rafinha (b. 1985) should match Bayern Munich + Schalke")

    def test_rafinha_barcelona_inter_matches(self):
        """
        Verify that Barcelona + Inter correctly resolves to 'Rafinha' (entity b. 1993).
        """
        clubs = {"Barcelona", "Inter"}
        
        valid_entities = None
        for c in clubs:
            e_set = self.club_to_entities.get(c, set())
            if valid_entities is None:
                valid_entities = set(e_set)
            else:
                valid_entities &= e_set

        valid_names = {self.entity_name[e] for e in (valid_entities or set())}
        self.assertIn("Rafael Alcântara", valid_names, "Rafael Alcântara (b. 1993) should match Barcelona + Inter")

    def test_danilo_disambiguation(self):
        """
        Verify that multiple players named 'Danilo' (e.g. Juventus/Real Madrid/Man City vs PSG/Porto Danilo Pereira)
        are segregated at the entity level.
        """
        danilo_entities = [
            e_id for e_id, name in self.entity_name.items()
            if name.strip().lower() == "danilo"
        ]
        self.assertGreater(len(danilo_entities), 1, "Expected multiple entities with name 'Danilo'")


if __name__ == '__main__':
    unittest.main()
