import os
import json
import pandas as pd
import re

def main():
    cache_path = os.path.expanduser('~/.cache/kagglehub/datasets/davidcariboo/player-scores/versions/671')
    players_df = pd.read_csv(os.path.join(cache_path, 'players.csv'))
    transfers_df = pd.read_csv(os.path.join(cache_path, 'transfers.csv'))

    def clean_club(val):
        if not isinstance(val, str): return ''
        val = re.sub(r'(?i)\s+(U\d+|Sub-\d+|II|B|Castilla|Youth|Academy)\b', '', val).strip()
        aliases = {
            'FC Barcelona': 'Barcelona', 'Barca': 'Barcelona',
            'Paris SG': 'Paris Saint-Germain', 'PSG': 'Paris Saint-Germain',
            'FC Bayern': 'Bayern Munich', 'Man City': 'Manchester City',
            'Man United': 'Manchester United', 'Spurs': 'Tottenham Hotspur',
            'Inter Miami CF': 'Inter Miami', 'Miami': 'Inter Miami'
        }
        return aliases.get(val, val)

    transfers_df['from_club'] = transfers_df['from_club_name'].apply(clean_club)
    transfers_df['to_club'] = transfers_df['to_club_name'].apply(clean_club)

    p_meta = {
        int(r['player_id']): {
            'name': r['name'], 
            'nat': r['country_of_citizenship'],
            'val': float(r['highest_market_value_in_eur']) if pd.notna(r['highest_market_value_in_eur']) else 0
        } 
        for _, r in players_df.iterrows() if pd.notna(r['name'])
    }

    p_clubs = {}
    for _, r in transfers_df.iterrows():
        pid = int(r['player_id'])
        if pid not in p_clubs: p_clubs[pid] = set()
        if r['from_club']: p_clubs[pid].add(r['from_club'])
        if r['to_club']: p_clubs[pid].add(r['to_club'])

    # Demo Puzzles for Iconic Excluded Players
    puzzles = []

    # 1. ANYONE BUT: LIONEL MESSI
    messi_id = [pid for pid, m in p_meta.items() if 'Lionel Messi' in m['name']][0]
    
    table1_messi = [p_meta[pid]['name'] for pid, c in p_clubs.items() if pid != messi_id and 'Barcelona' in c and 'Paris Saint-Germain' in c and p_meta[pid]['val'] > 5_000_000]
    table2_messi = [p_meta[pid]['name'] for pid, c in p_clubs.items() if pid != messi_id and p_meta[pid]['nat'] == 'Argentina' and 'Barcelona' in c]
    table3_messi = [p_meta[pid]['name'] for pid, c in p_clubs.items() if pid != messi_id and 'Barcelona' in c and p_meta[pid]['val'] >= 80_000_000]

    puzzles.append({
        "excluded_player": "Lionel Messi",
        "hint_subtitle": "ANYONE BUT LIONEL MESSI",
        "description": "Guess any player who fits the table criteria, EXCEPT Lionel Messi!",
        "tables": [
            {
                "title": "Played for BOTH Barcelona & PSG",
                "answers": table1_messi,
                "count": len(table1_messi)
            },
            {
                "title": "Argentinians who played for Barcelona",
                "answers": table2_messi,
                "count": len(table2_messi)
            },
            {
                "title": "Played for Barcelona (Peak Value €80M+)",
                "answers": table3_messi,
                "count": len(table3_messi)
            }
        ]
    })

    # 2. ANYONE BUT: CRISTIANO RONALDO
    cr7_id = [pid for pid, m in p_meta.items() if 'Cristiano Ronaldo' in m['name']][0]
    table1_cr7 = [p_meta[pid]['name'] for pid, c in p_clubs.items() if pid != cr7_id and 'Manchester United' in c and 'Real Madrid' in c]
    table2_cr7 = [p_meta[pid]['name'] for pid, c in p_clubs.items() if pid != cr7_id and p_meta[pid]['nat'] == 'Portugal' and ('Manchester United' in c or 'Real Madrid' in c or 'Juventus' in c)]
    table3_cr7 = [p_meta[pid]['name'] for pid, c in p_clubs.items() if pid != cr7_id and 'Real Madrid' in c and 'Juventus' in c]

    puzzles.append({
        "excluded_player": "Cristiano Ronaldo",
        "hint_subtitle": "ANYONE BUT CRISTIANO RONALDO",
        "description": "Guess any player who fits the table criteria, EXCEPT Cristiano Ronaldo!",
        "tables": [
            {
                "title": "Played for BOTH Man United & Real Madrid",
                "answers": table1_cr7,
                "count": len(table1_cr7)
            },
            {
                "title": "Portuguese players for Man Utd, Real Madrid or Juventus",
                "answers": table2_cr7,
                "count": len(table2_cr7)
            },
            {
                "title": "Played for BOTH Real Madrid & Juventus",
                "answers": table3_cr7,
                "count": len(table3_cr7)
            }
        ]
    })

    # Find overlap check (rule 3 support)
    # Check if any player appears in multiple columns for Messi puzzle
    all_messi_answers = table1_messi + table2_messi + table3_messi
    from collections import Counter
    counts = Counter(all_messi_answers)
    crossovers = {name: cnt for name, cnt in counts.items() if cnt > 1}

    print("=== SAMPLE GENERATED ANYONE BUT PUZZLES ===")
    print(json.dumps(puzzles, indent=2))
    print("\n--- Multi-table crossover test (Messi puzzle) ---")
    print("Players appearing in more than 1 column:", crossovers)

if __name__ == '__main__':
    main()
