#!/usr/bin/env python3
"""
build_passport_fc_datasets.py — Dataset Generator for Passport FC
==================================================================
Generates 180 daily progressive deduction puzzles where players identify
footballers who played for the Club of the Day and an expanding ladder of
nationalities, getting strictly harder as the pool of qualifying players shrinks.

Step 1: Easy (Large pool, 8+ players)
Step 2: Medium (Moderate pool, 4-7 players)
Step 3: Hard (Tight pool, 2-3 players)
Step 4: Hardest / The Unicorn (Ultra-rare pool, 1-2 players with a famous star)

Outputs: daily_passport_fc_games.csv
"""

import os
import sys
import json
import re
import unicodedata
from collections import defaultdict, Counter
import pandas as pd

NATION_ALIASES = {
    "Cote d'Ivoire": "Ivory Coast",
    "Korea, South": "South Korea",
    "Korea, North": "North Korea",
    "Bosnia-Herzegovina": "Bosnia & Herzegovina",
    "Türkiye": "Turkey",
    "The Gambia": "Gambia",
    "DR Congo": "DR Congo",
    "Congo": "Congo",
    "United States": "United States",
    "Czech Republic": "Czech Republic",
    "Ireland": "Republic of Ireland",
}

def clean_nation_name(val):
    if not val or not isinstance(val, str):
        return ""
    val = val.strip()
    return NATION_ALIASES.get(val, val)

def normalize_name(s):
    if not isinstance(s, str):
        return ""
    s = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', s)
    s = s.replace('ð', 'd').replace('Ð', 'D').replace('þ', 'th').replace('Þ', 'Th')
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').strip()

MAJOR_CLUBS = [
    # Spain
    {"name": "Barcelona", "club_id": 131, "country": "Spain"},
    {"name": "Real Madrid", "club_id": 418, "country": "Spain"},
    {"name": "Atletico Madrid", "club_id": 13, "country": "Spain"},
    {"name": "Sevilla", "club_id": 368, "country": "Spain"},
    {"name": "Valencia", "club_id": 1049, "country": "Spain"},
    {"name": "Villarreal", "club_id": 1050, "country": "Spain"},
    {"name": "Real Sociedad", "club_id": 681, "country": "Spain"},
    {"name": "Real Betis", "club_id": 150, "country": "Spain"},

    # England
    {"name": "Arsenal", "club_id": 11, "country": "England"},
    {"name": "Manchester United", "club_id": 985, "country": "England"},
    {"name": "Liverpool", "club_id": 31, "country": "England"},
    {"name": "Chelsea", "club_id": 631, "country": "England"},
    {"name": "Manchester City", "club_id": 281, "country": "England"},
    {"name": "Tottenham Hotspur", "club_id": 148, "country": "England"},
    {"name": "Newcastle United", "club_id": 762, "country": "England"},
    {"name": "Aston Villa", "club_id": 405, "country": "England"},
    {"name": "Everton", "club_id": 29, "country": "England"},
    {"name": "West Ham United", "club_id": 379, "country": "England"},

    # Italy
    {"name": "Juventus", "club_id": 506, "country": "Italy"},
    {"name": "AC Milan", "club_id": 5, "country": "Italy"},
    {"name": "Inter", "club_id": 46, "country": "Italy"},
    {"name": "Roma", "club_id": 12, "country": "Italy"},
    {"name": "Napoli", "club_id": 6195, "country": "Italy"},
    {"name": "Lazio", "club_id": 398, "country": "Italy"},
    {"name": "Fiorentina", "club_id": 430, "country": "Italy"},
    {"name": "Atalanta", "club_id": 800, "country": "Italy"},

    # Germany
    {"name": "Bayern Munich", "club_id": 27, "country": "Germany"},
    {"name": "Borussia Dortmund", "club_id": 16, "country": "Germany"},
    {"name": "Bayer Leverkusen", "club_id": 15, "country": "Germany"},
    {"name": "RB Leipzig", "club_id": 23826, "country": "Germany"},
    {"name": "Eintracht Frankfurt", "club_id": 24, "country": "Germany"},
    {"name": "Wolfsburg", "club_id": 82, "country": "Germany"},

    # France
    {"name": "Paris Saint-Germain", "club_id": 583, "country": "France"},
    {"name": "Monaco", "club_id": 162, "country": "France"},
    {"name": "Marseille", "club_id": 244, "country": "France"},
    {"name": "Lyon", "club_id": 1041, "country": "France"},
    {"name": "Lille", "club_id": 1082, "country": "France"},

    # Rest of Europe
    {"name": "Ajax", "club_id": 610, "country": "Netherlands"},
    {"name": "PSV Eindhoven", "club_id": 383, "country": "Netherlands"},
    {"name": "Benfica", "club_id": 294, "country": "Portugal"},
    {"name": "Porto", "club_id": 720, "country": "Portugal"},
    {"name": "Sporting CP", "club_id": 336, "country": "Portugal"},
    {"name": "Celtic", "club_id": 371, "country": "Scotland"},
    {"name": "Galatasaray", "club_id": 141, "country": "Turkey"},
    {"name": "Fenerbahce", "club_id": 36, "country": "Turkey"},
]

def load_data():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Load all_players.json
    all_players_file = os.path.join(base_dir, 'all_players.json')
    with open(all_players_file, 'r', encoding='utf-8') as f:
        all_players_data = json.load(f)

    player_canonical = {}
    player_by_norm = {}
    for p in all_players_data:
        name = p['Name']
        norm = normalize_name(name).lower()
        player_canonical[name] = {
            'name': name,
            'nationality': clean_nation_name(p.get('Nationality', '')),
            'position': p.get('Position', '')
        }
        player_by_norm[norm] = name

    # 2. Load historical careers
    hist_file = os.path.join(base_dir, 'historical_careers.json')
    hist_careers = {}
    if os.path.exists(hist_file):
        with open(hist_file, 'r', encoding='utf-8') as f:
            hist_careers = json.load(f)
        for h_name, d in hist_careers.items():
            norm = normalize_name(h_name).lower()
            if norm in player_by_norm:
                actual = player_by_norm[norm]
            else:
                actual = h_name
                player_canonical[actual] = {
                    'name': actual,
                    'nationality': clean_nation_name(d.get('nationality', '')),
                    'position': d.get('position', '')
                }
                player_by_norm[norm] = actual

    # 3. Load Davidcariboo dataset with VECTORIZED filtering
    dc_dir = os.path.expanduser('~/.cache/kagglehub/datasets/davidcariboo/player-scores/versions/679')
    df_players = pd.read_csv(os.path.join(dc_dir, 'players.csv'), low_memory=False)
    
    # Map prominence
    player_prominence = defaultdict(float)
    player_id_to_norm = {}
    for r in df_players.itertuples(index=False):
        pid = r.player_id
        pname = str(r.name)
        norm = normalize_name(pname).lower()
        player_id_to_norm[pid] = norm
        mv = float(r.highest_market_value_in_eur) if pd.notna(r.highest_market_value_in_eur) else 0.0
        caps = float(r.international_caps) if pd.notna(r.international_caps) else 0.0
        player_prominence[norm] = mv + (caps * 1_000_000.0)

    for h_name in hist_careers:
        norm = normalize_name(h_name).lower()
        player_prominence[norm] = max(player_prominence[norm], 100_000_000.0)

    club_players = defaultdict(set)
    club_id_to_name = {c['club_id']: c['name'] for c in MAJOR_CLUBS}
    target_cids = set(club_id_to_name.keys())

    # Appearances (vectorized filter)
    df_app = pd.read_csv(os.path.join(dc_dir, 'appearances.csv'), usecols=['player_id', 'player_club_id'], low_memory=False)
    df_app_filtered = df_app[df_app['player_club_id'].isin(target_cids)]
    for r in df_app_filtered.itertuples(index=False):
        cname = club_id_to_name.get(r.player_club_id)
        norm = player_id_to_norm.get(r.player_id)
        if cname and norm and norm in player_by_norm:
            club_players[cname].add(player_by_norm[norm])

    # Transfers (vectorized filter, senior relevance)
    df_tr = pd.read_csv(os.path.join(dc_dir, 'transfers.csv'), low_memory=False)
    df_tr['parsed_date'] = pd.to_datetime(df_tr['transfer_date'], errors='coerce')
    df_tr = df_tr[df_tr['parsed_date'] <= '2026-09-13']
    df_tr_filtered = df_tr[(df_tr['from_club_id'].isin(target_cids)) | (df_tr['to_club_id'].isin(target_cids))]
    
    for r in df_tr_filtered.itertuples(index=False):
        fee = float(r.transfer_fee) if pd.notna(r.transfer_fee) else 0.0
        mv = float(r.market_value_in_eur) if pd.notna(r.market_value_in_eur) else 0.0
        if fee > 0 or mv >= 1_000_000:
            norm = normalize_name(str(r.player_name)).lower()
            if norm in player_by_norm:
                actual = player_by_norm[norm]
                if r.from_club_id in club_id_to_name:
                    club_players[club_id_to_name[r.from_club_id]].add(actual)
                if r.to_club_id in club_id_to_name:
                    club_players[club_id_to_name[r.to_club_id]].add(actual)

    # Historical careers
    for h_name, d in hist_careers.items():
        norm = normalize_name(h_name).lower()
        actual = player_by_norm.get(norm, h_name)
        for c in d.get('clubs', []):
            for mc in MAJOR_CLUBS:
                cname = mc['name']
                if cname.lower() in c.lower():
                    club_players[cname].add(actual)

    # Manual specific historical enrichments
    manual_stars = [
        ("Eiður Guðjohnsen", "Barcelona", "Iceland"),
        ("Gary Lineker", "Barcelona", "England"),
        ("Gary Lineker", "Tottenham Hotspur", "England"),
        ("Gary Lineker", "Everton", "England"),
        ("Hristo Stoichkov", "Barcelona", "Bulgaria"),
        ("Jari Litmanen", "Barcelona", "Finland"),
        ("Jari Litmanen", "Liverpool", "Finland"),
        ("Jari Litmanen", "Ajax", "Finland"),
        ("Dennis Bergkamp", "Arsenal", "Netherlands"),
        ("Dennis Bergkamp", "Inter", "Netherlands"),
        ("Dennis Bergkamp", "Ajax", "Netherlands"),
        ("Thierry Henry", "Arsenal", "France"),
        ("Thierry Henry", "Barcelona", "France"),
        ("Patrick Vieira", "Arsenal", "France"),
        ("Patrick Vieira", "Juventus", "France"),
        ("Patrick Vieira", "Inter", "France"),
        ("Patrick Vieira", "Manchester City", "France"),
        ("Ruud van Nistelrooy", "Manchester United", "Netherlands"),
        ("Ruud van Nistelrooy", "Real Madrid", "Netherlands"),
        ("Robin van Persie", "Arsenal", "Netherlands"),
        ("Robin van Persie", "Manchester United", "Netherlands"),
        ("Robin van Persie", "Feyenoord", "Netherlands"),
        ("Robin van Persie", "Fenerbahce", "Netherlands"),
        ("Michael Laudrup", "Barcelona", "Denmark"),
        ("Michael Laudrup", "Real Madrid", "Denmark"),
        ("Michael Laudrup", "Juventus", "Denmark"),
        ("Brian Laudrup", "Bayern Munich", "Denmark"),
        ("Brian Laudrup", "Chelsea", "Denmark"),
        ("Brian Laudrup", "AC Milan", "Denmark"),
        ("Andriy Shevchenko", "AC Milan", "Ukraine"),
        ("Andriy Shevchenko", "Chelsea", "Ukraine"),
        ("Goran Pandev", "Inter", "North Macedonia"),
        ("Goran Pandev", "Lazio", "North Macedonia"),
        ("Goran Pandev", "Napoli", "North Macedonia"),
        ("Son Heung-min", "Tottenham Hotspur", "South Korea"),
        ("Son Heung-min", "Bayer Leverkusen", "South Korea"),
        ("Park Ji-sung", "Manchester United", "South Korea"),
        ("Park Ji-sung", "PSV Eindhoven", "South Korea"),
        ("Sadio Mané", "Liverpool", "Senegal"),
        ("Sadio Mané", "Bayern Munich", "Senegal"),
        ("Mohamed Salah", "Liverpool", "Egypt"),
        ("Mohamed Salah", "Chelsea", "Egypt"),
        ("Mohamed Salah", "Roma", "Egypt"),
        ("Didier Drogba", "Chelsea", "Ivory Coast"),
        ("Didier Drogba", "Marseille", "Ivory Coast"),
        ("Didier Drogba", "Galatasaray", "Ivory Coast"),
        ("Yaya Touré", "Barcelona", "Ivory Coast"),
        ("Yaya Touré", "Manchester City", "Ivory Coast"),
        ("Franck Kessié", "Barcelona", "Ivory Coast"),
        ("Franck Kessié", "AC Milan", "Ivory Coast"),
        ("Pierre-Emerick Aubameyang", "Arsenal", "Gabon"),
        ("Pierre-Emerick Aubameyang", "Barcelona", "Gabon"),
        ("Pierre-Emerick Aubameyang", "Borussia Dortmund", "Gabon"),
        ("Pierre-Emerick Aubameyang", "Chelsea", "Gabon"),
        ("Pierre-Emerick Aubameyang", "Marseille", "Gabon"),
    ]

    for s_name, s_club, s_nat in manual_stars:
        norm = normalize_name(s_name).lower()
        actual = player_by_norm.get(norm, s_name)
        if s_club in club_players:
            club_players[s_club].add(actual)
        if actual not in player_canonical:
            player_canonical[actual] = {
                'name': actual,
                'nationality': clean_nation_name(s_nat),
                'position': 'Attack'
            }
        player_prominence[norm] = max(player_prominence[norm], 100_000_000.0)

    print(f"Data loading complete! Mapped {len(club_players)} clubs.")
    return club_players, player_canonical, player_prominence


def build_puzzles(club_players, player_canonical, player_prominence, total_days=180):
    print(f"Building {total_days} daily puzzles...")

    # Group players by nationality for each club
    club_nat_players = {}
    club_nat_prominence = {}

    for mc in MAJOR_CLUBS:
        cname = mc['name']
        players = club_players.get(cname, set())
        by_nat = defaultdict(list)
        for p in players:
            meta = player_canonical.get(p, {})
            nat = meta.get('nationality', '')
            if nat:
                by_nat[nat].append(p)

        # Sort each nation's players by prominence descending
        nat_sorted = {}
        nat_prom = {}
        for nat, plist in by_nat.items():
            plist_sorted = sorted(plist, key=lambda x: player_prominence.get(normalize_name(x).lower(), 0), reverse=True)
            nat_sorted[nat] = plist_sorted
            nat_prom[nat] = player_prominence.get(normalize_name(plist_sorted[0]).lower(), 0)

        club_nat_players[cname] = nat_sorted
        club_nat_prominence[cname] = nat_prom

def deduplicate_canonical_names(names):
    seen = {}
    for p in names:
        if not p or not isinstance(p, str):
            continue
        clean_p = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', p).strip()
        norm = normalize_name(clean_p).lower()
        if norm not in seen:
            seen[norm] = clean_p
        else:
            # Prefer version with accented letters if one exists
            if any(ord(c) > 127 for c in clean_p) and not any(ord(c) > 127 for c in seen[norm]):
                seen[norm] = clean_p
    return list(seen.values())

def build_puzzles(club_players, player_canonical, player_prominence, total_days=180):
    print(f"Building {total_days} daily puzzles...")

    # Group players by nationality for each club, deduplicating spelling variants
    club_nat_players = {}
    club_nat_prominence = {}

    for mc in MAJOR_CLUBS:
        cname = mc['name']
        players = club_players.get(cname, set())
        by_nat = defaultdict(list)
        for p in players:
            meta = player_canonical.get(p, {})
            nat = meta.get('nationality', '')
            if nat:
                by_nat[nat].append(p)

        # Sort each nation's players by prominence descending, deduplicating spelling variants
        nat_sorted = {}
        nat_prom = {}
        for nat, plist in by_nat.items():
            plist_dedup = deduplicate_canonical_names(plist)
            plist_sorted = sorted(plist_dedup, key=lambda x: player_prominence.get(normalize_name(x).lower(), 0), reverse=True)
            nat_sorted[nat] = plist_sorted
            nat_prom[nat] = player_prominence.get(normalize_name(plist_sorted[0]).lower(), 0)

        club_nat_players[cname] = nat_sorted
        club_nat_prominence[cname] = nat_prom

    # Build balanced club schedule: each of the 45 clubs appears 4 times across 180 days
    leagues = ["Spain", "England", "Italy", "Germany", "France", "Netherlands", "Portugal", "Turkey", "Scotland"]
    by_league = defaultdict(list)
    for c in MAJOR_CLUBS:
        by_league[c['country']].append(c['name'])

    all_cycles = []
    for cycle in range(4):
        cycle_clubs = []
        league_ptrs = {k: 0 for k in leagues}
        while any(by_league[k] for k in leagues if league_ptrs[k] < len(by_league[k])):
            for l in leagues:
                if league_ptrs[l] < len(by_league[l]):
                    c = by_league[l][league_ptrs[l]]
                    cycle_clubs.append(c)
                    league_ptrs[l] += 1
        shift = (cycle * 11) % 45
        rotated = cycle_clubs[shift:] + cycle_clubs[:shift]
        all_cycles.extend(rotated)

    # Ensure Day 1 starts with Barcelona
    if all_cycles[0] != 'Barcelona':
        b_idx = all_cycles.index('Barcelona')
        all_cycles[0], all_cycles[b_idx] = all_cycles[b_idx], all_cycles[0]

    puzzle_schedule = []
    used_combos = defaultdict(set)
    used_unicorns = defaultdict(set)
    used_nats = defaultdict(Counter)

    # Day 1: Curated Barcelona puzzle
    barca_nats = club_nat_players['Barcelona']
    day1_puzzle = {
        'game_day': 1,
        'club': 'Barcelona',
        'steps': [
            {'step': 1, 'difficulty': 'Easy', 'nationality': 'France', 'count': len(barca_nats['France']), 'players': barca_nats['France']},
            {'step': 2, 'difficulty': 'Medium', 'nationality': 'Argentina', 'count': len(barca_nats['Argentina']), 'players': barca_nats['Argentina']},
            {'step': 3, 'difficulty': 'Hard', 'nationality': 'Ivory Coast', 'count': len(barca_nats['Ivory Coast']), 'players': barca_nats['Ivory Coast']},
            {'step': 4, 'difficulty': 'The Unicorn', 'nationality': 'Iceland', 'count': len(barca_nats['Iceland']), 'players': barca_nats['Iceland']},
        ]
    }
    puzzle_schedule.append(day1_puzzle)
    used_combos['Barcelona'].add(('France', 'Argentina', 'Ivory Coast', 'Iceland'))
    used_unicorns['Barcelona'].add('Iceland')
    for n in ['France', 'Argentina', 'Ivory Coast', 'Iceland']:
        used_nats['Barcelona'][n] += 1

    for day in range(2, total_days + 1):
        chosen_club = all_cycles[day - 1]
        nats = club_nat_players[chosen_club]
        proms = club_nat_prominence[chosen_club]
        nat_counts = used_nats[chosen_club]

        # Easy candidates: pool >= 8, or maximum available
        e_cands = [(n, len(pl), pl, proms[n]) for n, pl in nats.items() if len(pl) >= 8]
        if not e_cands:
            max_len = max(len(pl) for pl in nats.values())
            e_cands = [(n, len(pl), pl, proms[n]) for n, pl in nats.items() if len(pl) == max_len]
        e_cands.sort(key=lambda x: (nat_counts[x[0]], -x[1], -x[3]))

        # Unicorn candidate: count 1 or 2
        u_cands = [(n, len(pl), pl, proms[n]) for n, pl in nats.items() if len(pl) in (1, 2) and n not in used_unicorns[chosen_club]]
        if not u_cands:
            u_cands = [(n, len(pl), pl, proms[n]) for n, pl in nats.items() if len(pl) in (1, 2)]
        u_cands.sort(key=lambda x: (nat_counts[x[0]], -(x[1] == 1), -x[3]))

        found = False
        for u_pick in u_cands:
            h_cands = [(n, len(pl), pl, proms[n]) for n, pl in nats.items() if n != u_pick[0] and u_pick[1] < len(pl) <= 5]
            h_cands.sort(key=lambda x: (nat_counts[x[0]], -x[3]))
            for h_pick in h_cands:
                m_cands = [(n, len(pl), pl, proms[n]) for n, pl in nats.items() if n not in (u_pick[0], h_pick[0]) and h_pick[1] < len(pl) <= 9]
                m_cands.sort(key=lambda x: (nat_counts[x[0]], -x[3]))
                for m_pick in m_cands:
                    e_avail = [e for e in e_cands if e[0] not in (u_pick[0], h_pick[0], m_pick[0]) and e[1] > m_pick[1]]
                    if e_avail:
                        e_avail.sort(key=lambda e: (nat_counts[e[0]], -e[3]))
                        e_pick = e_avail[0]
                        combo = (e_pick[0], m_pick[0], h_pick[0], u_pick[0])
                        if combo not in used_combos[chosen_club]:
                            used_combos[chosen_club].add(combo)
                            used_unicorns[chosen_club].add(u_pick[0])
                            for n in combo:
                                used_nats[chosen_club][n] += 1
                            puzzle = {
                                'game_day': day,
                                'club': chosen_club,
                                'steps': [
                                    {'step': 1, 'difficulty': 'Easy', 'nationality': e_pick[0], 'count': e_pick[1], 'players': e_pick[2]},
                                    {'step': 2, 'difficulty': 'Medium', 'nationality': m_pick[0], 'count': m_pick[1], 'players': m_pick[2]},
                                    {'step': 3, 'difficulty': 'Hard', 'nationality': h_pick[0], 'count': h_pick[1], 'players': h_pick[2]},
                                    {'step': 4, 'difficulty': 'The Unicorn', 'nationality': u_pick[0], 'count': u_pick[1], 'players': u_pick[2]},
                                ]
                            }
                            puzzle_schedule.append(puzzle)
                            found = True
                            break
                if found: break
            if found: break

        if not found:
            print(f"Fallback for Day {day}: {chosen_club}")
            # Fallback if strict combo already used
            u_pick = u_cands[0]
            h_pick = [n for n in nats.items() if n[0] != u_pick[0] and len(n[1]) > u_pick[1]][0]
            m_pick = [n for n in nats.items() if n[0] not in (u_pick[0], h_pick[0]) and len(n[1]) > len(h_pick[1])][0]
            e_pick = [n for n in nats.items() if n[0] not in (u_pick[0], h_pick[0], m_pick[0]) and len(n[1]) > len(m_pick[1])][0]
            puzzle_schedule.append({
                'game_day': day,
                'club': chosen_club,
                'steps': [
                    {'step': 1, 'difficulty': 'Easy', 'nationality': e_pick[0], 'count': len(e_pick[1]), 'players': e_pick[1]},
                    {'step': 2, 'difficulty': 'Medium', 'nationality': m_pick[0], 'count': len(m_pick[1]), 'players': m_pick[1]},
                    {'step': 3, 'difficulty': 'Hard', 'nationality': h_pick[0], 'count': len(h_pick[1]), 'players': h_pick[1]},
                    {'step': 4, 'difficulty': 'The Unicorn', 'nationality': u_pick[0], 'count': len(u_pick[1]), 'players': u_pick[1]},
                ]
            })

    # Flatten into CSV
    csv_rows = []
    for p in puzzle_schedule:
        day = p['game_day']
        club = p['club']
        for s in p['steps']:
            canon_players = deduplicate_canonical_names(s['players'])
            samples = canon_players[:3]

            csv_rows.append({
                'game_day': day,
                'club': club,
                'step_number': s['step'],
                'total_steps': 4,
                'difficulty': s['difficulty'],
                'nationality': s['nationality'],
                'pool_size': len(canon_players),
                'sample_players': json.dumps(samples, ensure_ascii=False),
                'valid_players': json.dumps(canon_players, ensure_ascii=False)
            })

    df_out = pd.DataFrame(csv_rows)
    out_csv = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'daily_passport_fc_games.csv')
    df_out.to_csv(out_csv, index=False, encoding='utf-8')
    print(f"\nSuccessfully generated {len(df_out)} steps ({total_days} puzzles) to {out_csv}")
    return df_out

def main():
    club_players, player_canonical, player_prominence = load_data()
    df_puzzles = build_puzzles(club_players, player_canonical, player_prominence, total_days=180)

    print("\n--- SAMPLE DAILY PUZZLES ---")
    for day in range(1, 8):
        day_rows = df_puzzles[df_puzzles['game_day'] == day]
        club = day_rows.iloc[0]['club']
        print(f"\n==========================================")
        print(f"DAY {day}: Club of the Day = {club.upper()}")
        print(f"==========================================")
        for _, r in day_rows.iterrows():
            samples = json.loads(r['sample_players'])
            print(f"  Step {r['step_number']} [{r['difficulty']:<11}] {club} & {r['nationality']:<18} ({r['pool_size']:>2} players) -> e.g. {samples}")

if __name__ == '__main__':
    main()
