"""
scripts/player_stats_aggregator.py

Unified Football Career Stats Aggregator.
Consolidates club statistics, international match logs, tournament goals,
and player profile metadata into unified, deduplicated career profiles.
Powers Head-to-Head (H2H) comparison carousels, video shorts, and daily game modes.
"""

import os
import json
import re
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Union, Tuple
from collections import defaultdict

# Import alias utilities for text normalization & alias resolution
try:
    from scripts.alias_utils import normalize_search_text
except ImportError:
    from alias_utils import normalize_search_text


class PlayerStatsAggregator:
    def __init__(self, data_cache_dir: Optional[str] = None, lazy_load: bool = True):
        self.data_cache_dir = data_cache_dir
        self._is_loaded = False
        self._players_df: Optional[pd.DataFrame] = None
        self._club_stats_map: Dict[int, Dict] = {}
        self._senior_nat_map: Dict[int, Dict] = {}
        self._intl_goals_df: Optional[pd.DataFrame] = None
        self._name_country_to_id: Dict[Tuple[str, str], int] = {}
        self._name_to_ids: Dict[str, List[int]] = defaultdict(list)
        self._cached_profiles: Dict[int, Dict] = {}

        if not lazy_load:
            self.load_data()

    def _resolve_paths(self) -> Dict[str, str]:
        """Resolves file paths for all datasets across local project & kagglehub cache."""
        home = os.path.expanduser('~')
        
        # 1. Davidcariboo (player-scores)
        dc_versions = [
            os.path.join(home, '.cache/kagglehub/datasets/davidcariboo/player-scores/versions/679'),
            os.path.join(home, '.cache/kagglehub/datasets/davidcariboo/player-scores/versions/671')
        ]
        dc_path = next((p for p in dc_versions if os.path.exists(p)), None)
        
        # 2. Salimt (football-datasets)
        salimt_versions = [
            os.path.join(home, '.cache/kagglehub/datasets/xfkzujqjvx97n/football-datasets/versions/2'),
            os.path.join(home, '.cache/kagglehub/datasets/xfkzujqjvx97n/football-datasets/versions/1')
        ]
        salimt_path = next((p for p in salimt_versions if os.path.exists(p)), None)

        # 3. Martj42 (international-football-results-from-1872-to-2017)
        martj42_versions = [
            os.path.join(home, '.cache/kagglehub/datasets/martj42/international-football-results-from-1872-to-2017/versions/137'),
            os.path.join(home, '.cache/kagglehub/datasets/martj42/international-football-results-from-1872-to-2017/versions/1')
        ]
        martj42_path = next((p for p in martj42_versions if os.path.exists(p)), None)

        return {
            'cache_json': os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'player_career_stats_summary.json'),
            'players_csv': os.path.join(dc_path, 'players.csv') if dc_path else None,
            'player_performances_csv': os.path.join(salimt_path, 'player_performances', 'player_performances.csv') if salimt_path else None,
            'player_national_performances_csv': os.path.join(salimt_path, 'player_national_performances', 'player_national_performances.csv') if salimt_path else None,
            'goalscorers_csv': os.path.join(martj42_path, 'goalscorers.csv') if martj42_path else None,
            'results_csv': os.path.join(martj42_path, 'results.csv') if martj42_path else None
        }

    def load_data(self, force_reload: bool = False):
        """Loads and indexes datasets with entity disambiguation and deduplication."""
        if self._is_loaded and not force_reload:
            return

        paths = self._resolve_paths()

        # Check for warm cache first
        if not force_reload and paths.get('cache_json') and os.path.exists(paths['cache_json']):
            try:
                with open(paths['cache_json'], 'r', encoding='utf-8') as f:
                    cache_payload = json.load(f)
                    self._cached_profiles = {int(k): v for k, v in cache_payload.get('profiles', {}).items()}
                    # Index loaded names
                    for p_id, prof in self._cached_profiles.items():
                        norm_name = normalize_search_text(prof['name'])
                        norm_country = normalize_search_text(prof.get('nationality', ''))
                        if norm_name and norm_country:
                            self._name_country_to_id[(norm_name, norm_country)] = p_id
                        if norm_name:
                            self._name_to_ids[norm_name].append(p_id)
                    self._is_loaded = True
                    return
            except Exception:
                pass

        # 1. Load Player Profiles (players.csv)
        if paths['players_csv'] and os.path.exists(paths['players_csv']):
            self._players_df = pd.read_csv(
                paths['players_csv'],
                usecols=[
                    'player_id', 'name', 'country_of_citizenship', 'position',
                    'sub_position', 'highest_market_value_in_eur', 'image_url',
                    'international_caps', 'international_goals'
                ],
                low_memory=False
            )
            # Index players by ID, (norm_name, norm_country), and norm_name
            for _, row in self._players_df.iterrows():
                p_id = int(row['player_id'])
                name = str(row['name'])
                country = str(row['country_of_citizenship']) if pd.notna(row['country_of_citizenship']) else ''
                
                norm_name = normalize_search_text(name)
                norm_country = normalize_search_text(country)

                if norm_name and norm_country:
                    self._name_country_to_id[(norm_name, norm_country)] = p_id
                if norm_name:
                    self._name_to_ids[norm_name].append(p_id)

        # 2. Load Senior National Performances (caps and goals)
        if paths['player_national_performances_csv'] and os.path.exists(paths['player_national_performances_csv']):
            df_nat = pd.read_csv(
                paths['player_national_performances_csv'],
                usecols=['player_id', 'matches', 'goals', 'career_state'],
                low_memory=False
            )
            for p_id, group in df_nat.groupby('player_id'):
                max_matches = int(group['matches'].max()) if pd.notna(group['matches'].max()) else 0
                max_goals = int(group['goals'].max()) if pd.notna(group['goals'].max()) else 0
                self._senior_nat_map[int(p_id)] = {
                    'caps': max_matches,
                    'goals': max_goals
                }

        # 3. Load Club Career Performances (player_performances.csv)
        if paths['player_performances_csv'] and os.path.exists(paths['player_performances_csv']):
            df_perf = pd.read_csv(
                paths['player_performances_csv'],
                usecols=['player_id', 'team_name', 'nb_on_pitch', 'goals', 'assists', 'minutes_played'],
                low_memory=False
            )
            for p_id, group in df_perf.groupby('player_id'):
                total_apps = int(group['nb_on_pitch'].sum())
                total_goals = int(group['goals'].sum())
                total_assists = int(group['assists'].sum())
                total_minutes = float(group['minutes_played'].sum())
                unique_clubs = [c for c in group['team_name'].dropna().unique().tolist() if c]
                self._club_stats_map[int(p_id)] = {
                    'appearances': total_apps,
                    'goals': total_goals,
                    'assists': total_assists,
                    'minutes_played': total_minutes,
                    'clubs': unique_clubs
                }

        # 4. Load martj42 Goalscorers & Tournament Context
        if paths['goalscorers_csv'] and os.path.exists(paths['goalscorers_csv']):
            df_goals = pd.read_csv(paths['goalscorers_csv'])
            df_goals = df_goals[df_goals['own_goal'] == False]
            if paths['results_csv'] and os.path.exists(paths['results_csv']):
                df_res = pd.read_csv(paths['results_csv'], usecols=['date', 'home_team', 'away_team', 'tournament'])
                df_goals = pd.merge(df_goals, df_res, on=['date', 'home_team', 'away_team'], how='left')
            else:
                df_goals['tournament'] = 'Unknown'
            
            df_goals['norm_scorer'] = df_goals['scorer'].apply(lambda x: normalize_search_text(str(x)))
            df_goals['norm_team'] = df_goals['team'].apply(lambda x: normalize_search_text(str(x)))
            self._intl_goals_df = df_goals

        self._is_loaded = True

    def get_player_id(self, name_or_id: Union[int, str], country: Optional[str] = None) -> Optional[int]:
        """Resolves a player name or ID to their canonical Transfermarkt player_id."""
        self.load_data()

        if isinstance(name_or_id, int) or (isinstance(name_or_id, str) and name_or_id.isdigit()):
            p_id = int(name_or_id)
            if self._players_df is not None and (self._players_df['player_id'] == p_id).any():
                return p_id
            return None

        norm_name = normalize_search_text(str(name_or_id))
        if country:
            norm_country = normalize_search_text(str(country))
            if (norm_name, norm_country) in self._name_country_to_id:
                return self._name_country_to_id[(norm_name, norm_country)]

        candidate_ids = self._name_to_ids.get(norm_name, [])
        if not candidate_ids:
            return None
        if len(candidate_ids) == 1:
            return candidate_ids[0]

        # Disambiguate by highest peak market value
        if self._players_df is not None:
            sub_df = self._players_df[self._players_df['player_id'].isin(candidate_ids)]
            sorted_df = sub_df.sort_values(by='highest_market_value_in_eur', ascending=False)
            if not sorted_df.empty:
                return int(sorted_df.iloc[0]['player_id'])

        return candidate_ids[0]

    def get_player_career_stats(self, identifier: Union[int, str], country: Optional[str] = None) -> Optional[Dict]:
        """
        Returns the unified, deduplicated career statistics dictionary for a player.
        """
        self.load_data()
        p_id = self.get_player_id(identifier, country)
        if not p_id:
            return None

        if p_id in self._cached_profiles:
            return self._cached_profiles[p_id]

        p_row = self._players_df[self._players_df['player_id'] == p_id].iloc[0]
        canonical_name = str(p_row['name'])
        nationality = str(p_row['country_of_citizenship']) if pd.notna(p_row['country_of_citizenship']) else 'Unknown'
        position = str(p_row['position']) if pd.notna(p_row['position']) else 'Unknown'
        sub_position = str(p_row['sub_position']) if pd.notna(p_row['sub_position']) else position
        peak_val = float(p_row['highest_market_value_in_eur']) if pd.notna(p_row['highest_market_value_in_eur']) else 0.0
        image_url = str(p_row['image_url']) if pd.notna(p_row['image_url']) else ''

        # 1. Club Career Stats
        club_data = self._club_stats_map.get(p_id, {
            'appearances': 0,
            'goals': 0,
            'assists': 0,
            'minutes_played': 0.0,
            'clubs': []
        })

        # 2. Senior International Caps & Goals
        senior_nat = self._senior_nat_map.get(p_id, None)
        if senior_nat and senior_nat['caps'] > 0:
            intl_caps = senior_nat['caps']
            intl_goals = senior_nat['goals']
        else:
            intl_caps = int(p_row['international_caps']) if pd.notna(p_row['international_caps']) else 0
            intl_goals = int(p_row['international_goals']) if pd.notna(p_row['international_goals']) else 0

        # 3. martj42 Tournament Breakdown
        wc_goals = 0
        euro_goals = 0
        copa_goals = 0
        qual_goals = 0
        friendly_goals = 0
        penalties_scored = 0

        if self._intl_goals_df is not None:
            norm_n = normalize_search_text(canonical_name)
            norm_c = normalize_search_text(nationality)
            m_goals = self._intl_goals_df[
                (self._intl_goals_df['norm_scorer'] == norm_n) & 
                (self._intl_goals_df['norm_team'] == norm_c)
            ]
            if not m_goals.empty:
                wc_goals = int(len(m_goals[m_goals['tournament'] == 'FIFA World Cup']))
                euro_goals = int(len(m_goals[m_goals['tournament'] == 'UEFA Euro']))
                copa_goals = int(len(m_goals[m_goals['tournament'] == 'Copa América']))
                qual_goals = int(len(m_goals[m_goals['tournament'].str.contains('qualification|qualif', case=False, na=False)]))
                friendly_goals = int(len(m_goals[m_goals['tournament'] == 'Friendly']))
                penalties_scored = int(len(m_goals[m_goals['penalty'] == True]))

        # 4. Overall Unified Totals
        tot_apps = club_data['appearances'] + intl_caps
        tot_goals = club_data['goals'] + intl_goals
        tot_assists = club_data['assists']
        tot_ga = tot_goals + tot_assists
        goals_per_game = round(tot_goals / tot_apps, 2) if tot_apps > 0 else 0.0
        mins_per_ga = round(club_data['minutes_played'] / tot_ga, 1) if (tot_ga > 0 and club_data['minutes_played'] > 0) else None

        profile = {
            'player_id': p_id,
            'name': canonical_name,
            'nationality': nationality,
            'position': position,
            'sub_position': sub_position,
            'peak_market_value': peak_val,
            'image_url': image_url,
            'club': {
                'appearances': club_data['appearances'],
                'goals': club_data['goals'],
                'assists': club_data['assists'],
                'minutes_played': club_data['minutes_played'],
                'distinct_clubs_count': len(club_data['clubs']),
                'clubs': club_data['clubs']
            },
            'international': {
                'caps': intl_caps,
                'goals': intl_goals,
                'world_cup_goals': wc_goals,
                'euro_goals': euro_goals,
                'copa_america_goals': copa_goals,
                'qualifier_goals': qual_goals,
                'friendly_goals': friendly_goals,
                'penalties_scored': penalties_scored
            },
            'overall': {
                'total_appearances': tot_apps,
                'total_goals': tot_goals,
                'total_assists': tot_assists,
                'total_ga': tot_ga,
                'goals_per_game': goals_per_game,
                'mins_per_ga': mins_per_ga
            }
        }

        self._cached_profiles[p_id] = profile
        return profile

    def compare_players(self, player_a: Union[int, str], player_b: Union[int, str]) -> Optional[Dict]:
        """
        Generates a structured side-by-side Head-to-Head comparison payload.
        """
        stats_a = self.get_player_career_stats(player_a)
        stats_b = self.get_player_career_stats(player_b)

        if not stats_a or not stats_b:
            return None

        # Build comparison metrics matrix
        metrics = [
            {
                'key': 'total_appearances',
                'label': 'Career Appearances',
                'val_a': stats_a['overall']['total_appearances'],
                'val_b': stats_b['overall']['total_appearances'],
                'winner': 'a' if stats_a['overall']['total_appearances'] > stats_b['overall']['total_appearances'] else ('b' if stats_b['overall']['total_appearances'] > stats_a['overall']['total_appearances'] else 'tie')
            },
            {
                'key': 'total_goals',
                'label': 'Career Goals',
                'val_a': stats_a['overall']['total_goals'],
                'val_b': stats_b['overall']['total_goals'],
                'winner': 'a' if stats_a['overall']['total_goals'] > stats_b['overall']['total_goals'] else ('b' if stats_b['overall']['total_goals'] > stats_a['overall']['total_goals'] else 'tie')
            },
            {
                'key': 'total_assists',
                'label': 'Career Assists',
                'val_a': stats_a['overall']['total_assists'],
                'val_b': stats_b['overall']['total_assists'],
                'winner': 'a' if stats_a['overall']['total_assists'] > stats_b['overall']['total_assists'] else ('b' if stats_b['overall']['total_assists'] > stats_a['overall']['total_assists'] else 'tie')
            },
            {
                'key': 'total_ga',
                'label': 'Total Goal Contributions (G+A)',
                'val_a': stats_a['overall']['total_ga'],
                'val_b': stats_b['overall']['total_ga'],
                'winner': 'a' if stats_a['overall']['total_ga'] > stats_b['overall']['total_ga'] else ('b' if stats_b['overall']['total_ga'] > stats_a['overall']['total_ga'] else 'tie')
            },
            {
                'key': 'goals_per_game',
                'label': 'Goals per Match',
                'val_a': stats_a['overall']['goals_per_game'],
                'val_b': stats_b['overall']['goals_per_game'],
                'winner': 'a' if stats_a['overall']['goals_per_game'] > stats_b['overall']['goals_per_game'] else ('b' if stats_b['overall']['goals_per_game'] > stats_a['overall']['goals_per_game'] else 'tie')
            },
            {
                'key': 'intl_goals',
                'label': 'International Goals',
                'val_a': stats_a['international']['goals'],
                'val_b': stats_b['international']['goals'],
                'winner': 'a' if stats_a['international']['goals'] > stats_b['international']['goals'] else ('b' if stats_b['international']['goals'] > stats_a['international']['goals'] else 'tie')
            },
            {
                'key': 'intl_caps',
                'label': 'International Caps',
                'val_a': stats_a['international']['caps'],
                'val_b': stats_b['international']['caps'],
                'winner': 'a' if stats_a['international']['caps'] > stats_b['international']['caps'] else ('b' if stats_b['international']['caps'] > stats_a['international']['caps'] else 'tie')
            }
        ]

        return {
            'player_a': stats_a,
            'player_b': stats_b,
            'metrics': metrics
        }

    def find_h2h_matchups(
        self,
        position: Optional[str] = None,
        anchor_stat: str = 'total_goals',
        tolerance: float = 0.15,
        min_peak_value: float = 25_000_000,
        limit: int = 20
    ) -> List[Dict]:
        """
        Discovers natural, balanced head-to-head player pairings with close anchor stats.
        """
        # Collect candidate profiles
        profiles = []
        if self._cached_profiles:
            for prof in self._cached_profiles.values():
                if prof.get('peak_market_value', 0) >= min_peak_value:
                    if not position or prof.get('position', '').lower() == position.lower():
                        if prof['overall']['total_appearances'] >= 200:
                            profiles.append(prof)
        elif self._players_df is not None:
            cand_df = self._players_df[self._players_df['highest_market_value_in_eur'] >= min_peak_value].copy()
            if position:
                cand_df = cand_df[cand_df['position'].str.lower() == position.lower()]
            for p_id in cand_df['player_id'].head(300):
                prof = self.get_player_career_stats(p_id)
                if prof and prof['overall']['total_appearances'] >= 200:
                    profiles.append(prof)

        pairs = []
        used_ids = set()

        for i, p1 in enumerate(profiles):
            val1 = p1['overall'].get(anchor_stat) or p1['international'].get(anchor_stat, 0)
            if val1 == 0:
                continue

            for j in range(i + 1, len(profiles)):
                p2 = profiles[j]
                if p1['player_id'] == p2['player_id'] or (p1['player_id'], p2['player_id']) in used_ids:
                    continue

                val2 = p2['overall'].get(anchor_stat) or p2['international'].get(anchor_stat, 0)
                if val2 == 0:
                    continue

                diff_ratio = abs(val1 - val2) / max(val1, val2)
                if diff_ratio <= tolerance:
                    pairs.append({
                        'player_a': p1['name'],
                        'player_b': p2['name'],
                        'position': p1['position'],
                        'anchor_stat': anchor_stat,
                        'val_a': val1,
                        'val_b': val2,
                        'diff_pct': round(diff_ratio * 100, 1)
                    })
                    used_ids.add((p1['player_id'], p2['player_id']))
                    if len(pairs) >= limit:
                        return pairs

        return pairs

    def export_summary_cache(self, output_path: Optional[str] = None, min_market_value: float = 10_000_000, min_appearances: int = 50) -> str:
        """
        Builds and saves precomputed career profiles for all notable players to disk.
        """
        self.load_data()
        if not output_path:
            output_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'player_career_stats_summary.json')

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if self._players_df is None:
            return output_path

        eligible_ids = self._players_df[
            (self._players_df['highest_market_value_in_eur'] >= min_market_value) |
            (self._players_df['international_goals'] >= 5)
        ]['player_id'].unique()

        cached_profiles = {}
        for p_id in eligible_ids:
            prof = self.get_player_career_stats(int(p_id))
            if prof and prof['overall']['total_appearances'] >= min_appearances:
                cached_profiles[int(p_id)] = prof

        payload = {
            'version': 1,
            'count': len(cached_profiles),
            'profiles': cached_profiles
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

        return output_path

