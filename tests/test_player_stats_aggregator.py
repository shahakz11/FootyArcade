"""
tests/test_player_stats_aggregator.py

Unit and regression test suite for PlayerStatsAggregator.
Validates entity resolution, deduplication, career stat aggregation,
and H2H comparison generation.
"""

import unittest
from scripts.player_stats_aggregator import PlayerStatsAggregator


class TestPlayerStatsAggregator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.aggregator = PlayerStatsAggregator(lazy_load=False)

    def test_messi_career_stats(self):
        stats = self.aggregator.get_player_career_stats('Lionel Messi')
        self.assertIsNotNone(stats)
        self.assertEqual(stats['name'], 'Lionel Messi')
        self.assertEqual(stats['nationality'], 'Argentina')
        
        # Verify club stats are non-zero and reasonable
        self.assertGreaterEqual(stats['club']['goals'], 700)
        self.assertGreaterEqual(stats['club']['appearances'], 900)
        self.assertGreaterEqual(stats['club']['assists'], 300)

        # Verify international stats
        self.assertGreaterEqual(stats['international']['caps'], 170)
        self.assertGreaterEqual(stats['international']['goals'], 100)
        self.assertGreaterEqual(stats['international']['world_cup_goals'], 10)
        self.assertGreaterEqual(stats['international']['copa_america_goals'], 10)

        # Verify totals consistency (no double counting)
        self.assertEqual(
            stats['overall']['total_goals'],
            stats['club']['goals'] + stats['international']['goals']
        )
        self.assertEqual(
            stats['overall']['total_appearances'],
            stats['club']['appearances'] + stats['international']['caps']
        )

    def test_ronaldo_career_stats(self):
        stats = self.aggregator.get_player_career_stats('Cristiano Ronaldo')
        self.assertIsNotNone(stats)
        self.assertEqual(stats['name'], 'Cristiano Ronaldo')
        self.assertEqual(stats['nationality'], 'Portugal')
        
        # Verify club + intl goals
        self.assertGreaterEqual(stats['club']['goals'], 750)
        self.assertGreaterEqual(stats['international']['caps'], 200)
        self.assertGreaterEqual(stats['international']['goals'], 120)
        self.assertGreaterEqual(stats['international']['euro_goals'], 10)
        self.assertGreaterEqual(stats['overall']['total_goals'], 900)

    def test_accent_and_alias_normalization(self):
        # Querying with or without accents should yield the exact same player ID and stats
        stats_with_accent = self.aggregator.get_player_career_stats('Luka Modrić')
        stats_without_accent = self.aggregator.get_player_career_stats('Luka Modric')

        self.assertIsNotNone(stats_with_accent)
        self.assertIsNotNone(stats_without_accent)
        self.assertEqual(stats_with_accent['player_id'], stats_without_accent['player_id'])
        self.assertEqual(stats_with_accent['overall']['total_goals'], stats_without_accent['overall']['total_goals'])

    def test_h2h_comparison_generation(self):
        h2h = self.aggregator.compare_players('Eden Hazard', 'Neymar')
        self.assertIsNotNone(h2h)
        self.assertIn('player_a', h2h)
        self.assertIn('player_b', h2h)
        self.assertIn('metrics', h2h)
        self.assertGreaterEqual(len(h2h['metrics']), 5)

        # Ensure winners are assigned
        for metric in h2h['metrics']:
            self.assertIn(metric['winner'], ['a', 'b', 'tie'])

    def test_find_h2h_matchups(self):
        matchups = self.aggregator.find_h2h_matchups(
            position='Attack',
            anchor_stat='total_goals',
            tolerance=0.20,
            limit=5
        )
        self.assertIsInstance(matchups, list)
        self.assertGreater(len(matchups), 0)
        for pair in matchups:
            self.assertIn('player_a', pair)
            self.assertIn('player_b', pair)
            self.assertLessEqual(pair['diff_pct'], 20.0)


if __name__ == '__main__':
    unittest.main()
