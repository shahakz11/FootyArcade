#!/usr/bin/env python3
"""
build_played_with_datasets.py — Dataset Generator for "Played With" (Teammate Connect)
=====================================================================================
Generates 365 daily challenges for the 'Played With' game mode in Playmaker.
Each daily challenge features a Mystery Player of the Day (peak market value >= €30M)
and 5 teammate clues revealed progressively by number of competitive appearances together:

- Clue 1 (Least Frequent): Teammate with minimum matches shared (e.g. 1-2 matches)
- Clue 2 (Low-Mid Tier):   Teammate around 25th percentile of appearances
- Clue 3 (Mid Tier):       Teammate around 50th percentile of appearances
- Clue 4 (10th Rank):      10th most frequent teammate in career appearances
- Clue 5 (Most Frequent):  #1 most frequent teammate (all-time most matches together)

Outputs: daily_played_with_games.csv
"""

import os
import sys
import json
import csv
import re
import unicodedata
import random
from collections import defaultdict, Counter
import pandas as pd
import kagglehub

# Club name cleaning patterns
PREFIX_PATTERN = re.compile(
    r'^(1\.\s*FC|1\.\s*FSV|1\.\s*|FC|CF|AC|AS|SS|SV|SC|SD|CD|UD|RC|RCD|FK|SK|BK|IF|IFK|OGC|US|USM|GC|AFC|SAD|CA|CE|CS|CP|VfB|VfL|TSG|BSC|FSV|SSV|SpVgg|Club)\s+',
    re.I
)
SUFFIX_PATTERN = re.compile(
    r'\s+(Football Club|Association Football Club|Club de Fútbol|Club de Futbol|Fútbol Club|Futbol Club|Soccer Club|Sports Club|Sport Club|Athletic Club|Club|FC|CF|SC|CSC|S\.A\.D\.|R\.C\.D\.|C\.D\.|F\.C\.|C\.F\.|AF|FK|SK|BK|SV|EV|e\.V\.|eV|AC|SD|UD|RC|SAD|Res|Reserves|Youth|Yth|Academy|Junioren|Castilla|II|B|U-?\d+|Sub-?\d+|Sub\s*\d+|Under-?\d+|Under\s*\d+)\b',
    re.I
)

ALIASES = {
    'FC Bayern München': 'Bayern Munich',
    'FC Bayern Munich': 'Bayern Munich',
    'Bayern Munich': 'Bayern Munich',
    'Borussia Dortmund': 'Borussia Dortmund',
    'Bayer 04 Leverkusen': 'Bayer Leverkusen',
    'Bayer Leverkusen': 'Bayer Leverkusen',
    'RB Leipzig': 'RB Leipzig',
    'RasenBallsport Leipzig': 'RB Leipzig',
    'Paris Saint-Germain': 'Paris Saint-Germain',
    'Paris Saint-Germain FC': 'Paris Saint-Germain',
    'Real Madrid CF': 'Real Madrid',
    'Real Madrid': 'Real Madrid',
    'FC Barcelona': 'Barcelona',
    'Barcelona': 'Barcelona',
    'Atlético de Madrid': 'Atlético Madrid',
    'Atlético Madrid': 'Atlético Madrid',
    'Club Atlético de Madrid': 'Atlético Madrid',
    'Manchester United FC': 'Manchester United',
    'Manchester United': 'Manchester United',
    'Manchester City FC': 'Manchester City',
    'Manchester City': 'Manchester City',
    'Liverpool FC': 'Liverpool',
    'Liverpool': 'Liverpool',
    'Chelsea FC': 'Chelsea',
    'Chelsea': 'Chelsea',
    'Arsenal FC': 'Arsenal',
    'Arsenal': 'Arsenal',
    'Tottenham Hotspur': 'Tottenham',
    'Tottenham Hotspur FC': 'Tottenham',
    'Juventus FC': 'Juventus',
    'Juventus': 'Juventus',
    'FC Internazionale Milano': 'Inter Milan',
    'Inter Milan': 'Inter Milan',
    'AC Milan': 'AC Milan',
    'SSC Napoli': 'Napoli',
    'Napoli': 'Napoli',
    'AS Roma': 'AS Roma',
    'SS Lazio': 'Lazio',
}

def clean_club_name(raw_name: str) -> str:
    if not raw_name or not isinstance(raw_name, str):
        return ""
    name = raw_name.strip()
    if name in ALIASES:
        return ALIASES[name]
    # Strip prefixes and suffixes
    cleaned = PREFIX_PATTERN.sub('', name)
    cleaned = SUFFIX_PATTERN.sub('', cleaned).strip()
    if cleaned in ALIASES:
        return ALIASES[cleaned]
    return cleaned if len(cleaned) >= 3 else name


def normalize_string(s: str) -> str:
    if not s:
        return ""
    nfkd = unicodedata.normalize('NFKD', s)
    return ''.join(c for c in nfkd if not unicodedata.combining(c)).strip()


def load_dataset():
    print("Loading dataset from Davidcariboo player-scores...")
    try:
        dc_path = kagglehub.dataset_download('davidcariboo/player-scores')
    except Exception:
        dc_path = os.path.expanduser('~/.cache/kagglehub/datasets/davidcariboo/player-scores/versions/679')
    print(f"Dataset path: {dc_path}")

    # 1. Players
    df_players = pd.read_csv(os.path.join(dc_path, 'players.csv'), low_memory=False)
    df_players['highest_market_value_in_eur'] = pd.to_numeric(df_players['highest_market_value_in_eur'], errors='coerce').fillna(0)
    
    # 2. Clubs
    df_clubs = pd.read_csv(os.path.join(dc_path, 'clubs.csv'), low_memory=False)
    club_map = {}
    for _, r in df_clubs.iterrows():
        club_map[r['club_id']] = clean_club_name(r.get('name', ''))

    # Player profile lookup
    p_info = {}
    for _, r in df_players.iterrows():
        pid = int(r['player_id'])
        p_info[pid] = {
            'player_id': pid,
            'name': r['name'] if pd.notna(r['name']) else f"{r.get('first_name', '')} {r.get('last_name', '')}".strip(),
            'country': r.get('country_of_citizenship', '') if pd.notna(r.get('country_of_citizenship', '')) else '',
            'position': r.get('position', '') if pd.notna(r.get('position', '')) else '',
            'sub_position': r.get('sub_position', '') if pd.notna(r.get('sub_position', '')) else '',
            'peak_val': float(r['highest_market_value_in_eur']),
            'current_club': clean_club_name(r.get('current_club_name', '')) if pd.notna(r.get('current_club_name', '')) else '',
            'image_url': r.get('image_url', '') if pd.notna(r.get('image_url', '')) else ''
        }

    # 3. Appearances
    print("Loading match appearances...")
    df_app = pd.read_csv(os.path.join(dc_path, 'appearances.csv'), usecols=['game_id', 'player_id', 'player_club_id'], low_memory=False)

    # Group games by (game_id, player_club_id) -> list of player_ids
    game_teams = defaultdict(list)
    for gid, cid, pid in zip(df_app['game_id'], df_app['player_club_id'], df_app['player_id']):
        if pd.notna(gid) and pd.notna(cid) and pd.notna(pid):
            game_teams[(int(gid), int(cid))].append(int(pid))

    print(f"Total club-match line appearances groups: {len(game_teams)}")

    # Target Mystery Player Pool: peak market value >= 30,000,000 EUR
    pool_30m = df_players[df_players['highest_market_value_in_eur'] >= 30_000_000].copy()
    target_pids = set(pool_30m['player_id'].astype(int))
    print(f"Total mystery candidates with peak value >= 30M: {len(target_pids)}")

    # Build co-appearance matrix & shared clubs
    teammate_matrix = defaultdict(Counter)
    teammate_shared_clubs = defaultdict(lambda: defaultdict(set))

    for (gid, cid), pids in game_teams.items():
        pids_set = set(pids)
        targets_in_game = pids_set.intersection(target_pids)
        cname = club_map.get(cid, "")
        if targets_in_game:
            for t in targets_in_game:
                for other in pids:
                    if other != t:
                        teammate_matrix[t][other] += 1
                        if cname:
                            teammate_shared_clubs[t][other].add(cname)

    return p_info, target_pids, teammate_matrix, teammate_shared_clubs


def generate_puzzles(p_info, target_pids, teammate_matrix, teammate_shared_clubs, num_days=365):
    print("Selecting and balancing mystery candidates...")
    candidates = []

    for pid in target_pids:
        tm_counter = teammate_matrix[pid]
        if len(tm_counter) < 15:
            continue
        
        sorted_tm = sorted(tm_counter.items(), key=lambda x: x[1], reverse=True)
        max_apps = sorted_tm[0][1]
        if max_apps < 15:
            continue
        
        info = p_info.get(pid, {})
        if not info.get('name'):
            continue
        
        # Calculate prominence weight
        peak_val = info.get('peak_val', 0)
        candidates.append({
            'player_id': pid,
            'name': info['name'],
            'country': info['country'],
            'position': info['position'],
            'peak_val': peak_val,
            'teammates_count': len(sorted_tm),
            'max_apps': max_apps,
            'sorted_tm': sorted_tm
        })

    print(f"Total eligible mystery candidates: {len(candidates)}")

    # Tier candidates by peak market value for diverse calendar rotation
    # Tier 1: Megastars (>= 100M)
    # Tier 2: World-Class (60M - 99M)
    # Tier 3: Elite Stars (40M - 59M)
    # Tier 4: Established Greats (30M - 39M)
    t1 = [c for c in candidates if c['peak_val'] >= 100_000_000]
    t2 = [c for c in candidates if 60_000_000 <= c['peak_val'] < 100_000_000]
    t3 = [c for c in candidates if 40_000_000 <= c['peak_val'] < 60_000_000]
    t4 = [c for c in candidates if 30_000_000 <= c['peak_val'] < 40_000_000]

    print(f"Tier 1 (>=100M): {len(t1)}, Tier 2 (60-99M): {len(t2)}, Tier 3 (40-59M): {len(t3)}, Tier 4 (30-39M): {len(t4)}")

    # Seed deterministic RNG for reproducible daily puzzle calendar
    rng = random.Random(42)
    rng.shuffle(t1)
    rng.shuffle(t2)
    rng.shuffle(t3)
    rng.shuffle(t4)

    # Build calendar sequence of mystery players
    calendar_players = []
    i1, i2, i3, i4 = 0, 0, 0, 0
    
    # Weekly cycle: Day 1: Megastar, Day 2: World-class, Day 3: Elite, Day 4: World-class, Day 5: Megastar, Day 6: Great, Day 7: Elite
    pattern = ['t1', 't2', 't3', 't2', 't1', 't4', 't3']

    for day in range(1, num_days + 1):
        slot = pattern[(day - 1) % len(pattern)]
        cand = None
        if slot == 't1' and i1 < len(t1):
            cand = t1[i1]; i1 += 1
        elif slot == 't2' and i2 < len(t2):
            cand = t2[i2]; i2 += 1
        elif slot == 't3' and i3 < len(t3):
            cand = t3[i3]; i3 += 1
        elif slot == 't4' and i4 < len(t4):
            cand = t4[i4]; i4 += 1
        
        # Fallback to any available if slot ran out
        if not cand:
            for pool, idx_var in [(t1, i1), (t2, i2), (t3, i3), (t4, i4)]:
                if idx_var < len(pool):
                    cand = pool[idx_var]
                    break
        
        if not cand:
            # If all exhausted, cycle from start
            cand = candidates[(day - 1) % len(candidates)]

        calendar_players.append((day, cand))

    # Build clue ladder for each daily puzzle
    puzzle_rows = []

    for day, cand in calendar_players:
        pid = cand['player_id']
        sorted_tm = cand['sorted_tm']
        n = len(sorted_tm)

        # 5 Clue Steps:
        # Clue 5: #1 Most frequent (highest apps together)
        # Clue 4: 10th most frequent
        # Clue 3: ~50th percentile (mid tier)
        # Clue 2: ~75th percentile (low-mid tier)
        # Clue 1: Least frequent (lowest apps together, e.g. 1 match)
        idx5 = 0
        idx4 = min(9, n - 1)
        idx3 = int(n * 0.50)
        idx2 = int(n * 0.75)
        idx1 = n - 1

        indices = [idx1, idx2, idx3, idx4, idx5]
        
        # Ensure indices are strictly distinct and sorted by appearance count ascending
        selected_teammates = []
        used_pids = set()

        for step_idx, tm_idx in enumerate(indices):
            # Pick teammate at or near tm_idx not yet used
            chosen = None
            for offset in [0, 1, -1, 2, -2, 3, -3, 4, -4, 5, -5]:
                cur_idx = max(0, min(n - 1, tm_idx + offset))
                tm_pid, tm_apps = sorted_tm[cur_idx]
                if tm_pid not in used_pids:
                    chosen = (tm_pid, tm_apps)
                    used_pids.add(tm_pid)
                    break
            if not chosen:
                chosen = sorted_tm[tm_idx]
            selected_teammates.append(chosen)

        # Sort the 5 clues by appearances together ascending
        selected_teammates.sort(key=lambda x: x[1])

        tier_labels = [
            "Least Frequent",
            "Low-Mid Tier",
            "Mid Tier",
            "10th Most Frequent",
            "Most Frequent"
        ]

        for step_num in range(1, 6):
            tm_pid, apps_cnt = selected_teammates[step_num - 1]
            tm_info = p_info.get(tm_pid, {})
            shared_c = list(teammate_shared_clubs[pid][tm_pid])
            if not shared_c:
                shared_c = [tm_info.get('current_club', '')]

            puzzle_rows.append({
                'game_day': day,
                'mystery_player': cand['name'],
                'mystery_id': pid,
                'mystery_nationality': cand['country'],
                'mystery_position': cand['position'],
                'mystery_peak_value': int(cand['peak_val']),
                'step_number': step_num,
                'total_steps': 5,
                'clue_tier': tier_labels[step_num - 1],
                'teammate_name': tm_info.get('name', f"Player #{tm_pid}"),
                'teammate_id': tm_pid,
                'teammate_nationality': tm_info.get('country', ''),
                'teammate_position': tm_info.get('position', ''),
                'shared_clubs': json.dumps(shared_c, ensure_ascii=False),
                'appearances_together': int(apps_cnt)
            })

    return puzzle_rows


def main():
    p_info, target_pids, teammate_matrix, teammate_shared_clubs = load_dataset()
    puzzle_rows = generate_puzzles(p_info, target_pids, teammate_matrix, teammate_shared_clubs, num_days=365)

    out_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'daily_played_with_games.csv')
    fieldnames = [
        'game_day', 'mystery_player', 'mystery_id', 'mystery_nationality', 'mystery_position',
        'mystery_peak_value', 'step_number', 'total_steps', 'clue_tier', 'teammate_name',
        'teammate_id', 'teammate_nationality', 'teammate_position', 'shared_clubs', 'appearances_together'
    ]

    with open(out_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(puzzle_rows)

    print(f"\nSuccessfully generated {len(puzzle_rows)} clue rows ({len(puzzle_rows)//5} daily puzzles) into {out_csv}!")

    # Display sample puzzle 1 and 2
    df_out = pd.read_csv(out_csv)
    for gday in [1, 2, 3]:
        day_df = df_out[df_out['game_day'] == gday]
        first = day_df.iloc[0]
        print(f"\n--- PUZZLE #{gday} : Mystery Player: {first['mystery_player']} ({first['mystery_nationality']} · €{first['mystery_peak_value']//1_000_000}M) ---")
        for _, r in day_df.iterrows():
            print(f"  Clue {r['step_number']} [{r['clue_tier']}]: {r['teammate_name']} ({r['teammate_nationality']}) — {r['appearances_together']} matches together at {r['shared_clubs']}")


if __name__ == '__main__':
    main()
