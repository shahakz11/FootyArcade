"""
tests/test_h2h_carousel_pipeline.py

Unit test suite for the Head-to-Head (H2H) Instagram Carousel Pipeline.
Validates daily scheduling rotation, slide payload structure, caption generation,
and image resolution.
"""

import unittest
import os
from scripts.generate_h2h_carousel import (
    get_daily_h2h_matchup,
    build_slide_payload,
    generate_h2h_caption,
    CURATED_MATCHUPS
)
from scripts.player_stats_aggregator import PlayerStatsAggregator
from scripts.player_image_manager import resolve_player_image_path, sanitize_filename


class TestH2HCarouselPipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aggregator = PlayerStatsAggregator(lazy_load=False)

    def test_daily_h2h_rotation(self):
        pair1 = get_daily_h2h_matchup("2026-10-01")
        pair2 = get_daily_h2h_matchup("2026-10-02")
        self.assertIsInstance(pair1, tuple)
        self.assertEqual(len(pair1), 2)
        self.assertIn(pair1, CURATED_MATCHUPS)
        self.assertNotEqual(pair1, pair2)

    def test_build_slide_payload_structure(self):
        stats_a = self.aggregator.get_player_career_stats("Eden Hazard")
        stats_b = self.aggregator.get_player_career_stats("Neymar")
        self.assertIsNotNone(stats_a)
        self.assertIsNotNone(stats_b)

        img_a = resolve_player_image_path(stats_a["name"], stats_a.get("image_url"))
        img_b = resolve_player_image_path(stats_b["name"], stats_b.get("image_url"))

        payload = build_slide_payload(stats_a, stats_b, img_a, img_b)
        self.assertIn("playerA", payload)
        self.assertIn("playerB", payload)

        p_a = payload["playerA"]
        self.assertEqual(p_a["name"], "Eden Hazard")
        self.assertGreater(p_a["totalApps"], 500)
        self.assertGreater(p_a["totalGoals"], 100)
        self.assertIsNotNone(p_a["imagePath"])

    def test_generate_h2h_caption_quality(self):
        stats_a = self.aggregator.get_player_career_stats("Karim Benzema")
        stats_b = self.aggregator.get_player_career_stats("Robert Lewandowski")
        self.assertIsNotNone(stats_a)
        self.assertIsNotNone(stats_b)

        caption = generate_h2h_caption(stats_a, stats_b)
        self.assertIn("PRIME VS PRIME", caption)
        self.assertIn("Karim Benzema", caption)
        self.assertIn("Robert Lewandowski", caption)
        self.assertIn("CAREER NUMBERS", caption)
        self.assertIn("playmaker.best", caption)
        self.assertIn("#karimbenzema", caption)
        self.assertIn("#robertlewandowski", caption)
        self.assertIn("#football", caption)

    def test_player_image_path_resolution(self):
        path_hazard = resolve_player_image_path("Eden Hazard")
        self.assertTrue(os.path.exists(path_hazard))
        self.assertGreater(os.path.getsize(path_hazard), 1000)

        slug = sanitize_filename("Luka Modrić")
        self.assertEqual(slug, "luka_modric")


if __name__ == '__main__':
    unittest.main()
