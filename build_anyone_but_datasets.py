import os
import json
import pandas as pd
import random
from collections import defaultdict

def main():
    cache_path = os.path.expanduser('~/.cache/kagglehub/datasets/davidcariboo/player-scores/versions/671')
    print("Loading player-scores dataset from cache...")
    
    players_df = pd.read_csv(os.path.join(cache_path, 'players.csv'))
    transfers_df = pd.read_csv(os.path.join(cache_path, 'transfers.csv'))
    appearances_df = pd.read_csv(os.path.join(cache_path, 'appearances.csv'))
    
    # 1. Map player metadata
    players_meta = {}
    for idx, row in players_df.iterrows():
        p_id = int(row['player_id'])
        name = str(row['name']) if pd.notna(row['name']) else ''
        nat = str(row['country_of_citizenship']) if pd.notna(row['country_of_citizenship']) else ''
        val = float(row['highest_market_value_in_eur']) if pd.notna(row['highest_market_value_in_eur']) else 0.0
        players_meta[p_id] = {'name': name, 'nationality': nat, 'market_value': val}
        
    # 2. Player clubs history
    player_clubs = defaultdict(set)
    for idx, row in transfers_df.iterrows():
        p_id = int(row['player_id'])
        for col in ['from_club_name', 'to_club_name']:
            if pd.notna(row[col]):
                club = str(row[col]).strip()
                if club:
                    player_clubs[p_id].add(club)
                    
    # 3. Aggregate career goals & appearances per player
    player_goals = defaultdict(int)
    player_apps = defaultdict(int)
    for idx, row in appearances_df.iterrows():
        p_id = int(row['player_id'])
        goals = int(row['goals']) if pd.notna(row['goals']) else 0
        player_goals[p_id] += goals
        player_apps[p_id] += 1

    print(f"Loaded {len(players_meta)} players.")

    # Define candidate iconic target players (Key Excluded Players)
    # Filter high market value or well-known players
    top_players = [p_id for p_id, meta in players_meta.items() if meta['market_value'] >= 30_000_000 and len(player_clubs[p_id]) >= 2]
    print(f"Top high-profile candidate key players: {len(top_players)}")

    # Let's test generating sample Anyone But games for 5 iconic players
    sample_games = []
    
    for p_id in top_players[:30]:
        key_name = players_meta[p_id]['name']
        key_nat = players_meta[p_id]['nationality']
        key_clubs = list(player_clubs[p_id])
        key_goals = player_goals[p_id]
        
        if len(key_clubs) < 2 or not key_nat:
            continue
            
        # Build 3 potential criteria that key player fits:
        # C1: Nationality + played for Club A
        # C2: Played for Club A and Club B
        # C3: Scored X+ career goals OR played for Club C
        c1_desc = f"Argentinian who played for {key_clubs[0]}" if key_nat == 'Argentina' else f"{key_nat} player who played for {key_clubs[0]}"
        c2_desc = f"Played for both {key_clubs[0]} and {key_clubs[1]}"
        
        # Find who else matches C1
        c1_matches = [
            players_meta[pid]['name'] for pid in players_meta 
            if pid != p_id and players_meta[pid]['nationality'] == key_nat and key_clubs[0] in player_clubs[pid]
        ]
        
        # Find who else matches C2
        c2_matches = [
            players_meta[pid]['name'] for pid in players_meta 
            if pid != p_id and key_clubs[0] in player_clubs[pid] and key_clubs[1] in player_clubs[pid]
        ]
        
        # Validate counts (e.g. 2 to 10 answers)
        if 2 <= len(c1_matches) <= 12 and 2 <= len(c2_matches) <= 12:
            sample_games.append({
                "key_player": key_name,
                "c1_label": c1_desc,
                "c1_answers": c1_matches,
                "c2_label": c2_desc,
                "c2_answers": c2_matches
            })
            if len(sample_games) >= 5:
                break

    print("\n--- SAMPLE GENERATED ANYONE BUT GAMES ---")
    print(json.dumps(sample_games, indent=2))

if __name__ == '__main__':
    main()
