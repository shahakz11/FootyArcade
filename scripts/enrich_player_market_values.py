import os
import glob
import json
import re
import unicodedata
import pandas as pd

def normalize_name(name):
    if not name:
        return ""
    # Strip any (12345) id suffix
    name = re.sub(r'\s*\(\d+\)$', '', str(name)).strip()
    # Normalize unicode accents
    norm = unicodedata.normalize('NFKD', name)
    norm = ''.join(c for c in norm if not unicodedata.combining(c))
    return norm.lower().strip()

def to_macro_pos(pos):
    p = (pos or '').lower().strip()
    if not p or p == 'player' or p == 'missing':
        return 'Player'
    if 'goal' in p or p == 'gk':
        return 'Goalkeeper'
    if 'def' in p or 'back' in p:
        return 'Defender'
    if 'mid' in p:
        return 'Midfield'
    if 'att' in p or 'forward' in p or 'wing' in p or 'striker' in p:
        return 'Attack'
    return pos.capitalize() if pos else 'Player'


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    all_players_path = os.path.join(base_dir, 'all_players.json')
    historical_path = os.path.join(base_dir, 'historical_careers.json')

    print(f"Loading existing all_players.json from {all_players_path}...")
    with open(all_players_path, 'r', encoding='utf-8') as f:
        existing_players = json.load(f)
    print(f"Total existing players: {len(existing_players)}")

    # 1. Ingest davidcariboo players
    dc_dir = os.path.expanduser('~/.cache/kagglehub/datasets/davidcariboo/player-scores/versions')
    player_files = sorted(glob.glob(dc_dir + '/**/players.csv', recursive=True))
    transfer_files = sorted(glob.glob(dc_dir + '/**/transfers.csv', recursive=True))

    market_val_by_name = {}  # norm_name -> max_val
    market_val_by_exact = {} # exact_name -> max_val
    market_val_by_tuple = {} # (norm_name, norm_nat, norm_pos) -> max_val

    if player_files:
        latest_player_file = player_files[-1]
        print(f"Loading players from {latest_player_file}...")
        df_players = pd.read_csv(latest_player_file, low_memory=False)
        for _, row in df_players.iterrows():
            raw_name = str(row['name']) if pd.notna(row['name']) else ""
            if not raw_name:
                continue
            
            # Use highest_market_value_in_eur or market_value_in_eur
            val1 = float(row['highest_market_value_in_eur']) if pd.notna(row['highest_market_value_in_eur']) else 0.0
            val2 = float(row['market_value_in_eur']) if pd.notna(row['market_value_in_eur']) else 0.0
            val = max(val1, val2)

            norm = normalize_name(raw_name)
            nat = normalize_name(str(row['country_of_citizenship'])) if pd.notna(row['country_of_citizenship']) else ""
            raw_pos = str(row['position']) if pd.notna(row['position']) else ""
            macro_pos = to_macro_pos(raw_pos)
            pos = normalize_name(macro_pos)
            key_tuple = (norm, nat, pos)
            if val > market_val_by_tuple.get(key_tuple, 0):
                market_val_by_tuple[key_tuple] = val
            if val > market_val_by_name.get(norm, 0):
                market_val_by_name[norm] = val
            if val > market_val_by_exact.get(raw_name, 0):
                market_val_by_exact[raw_name] = val

    # 2. Ingest davidcariboo transfers (transfer_fee as valuation floor)
    if transfer_files:
        latest_transfer_file = transfer_files[-1]
        print(f"Loading transfer fees from {latest_transfer_file}...")
        df_transfers = pd.read_csv(latest_transfer_file, low_memory=False)
        df_transfers['transfer_fee'] = pd.to_numeric(df_transfers['transfer_fee'], errors='coerce').fillna(0.0)
        for _, row in df_transfers.iterrows():
            t_name = str(row['player_name']) if pd.notna(row['player_name']) else ""
            fee = float(row['transfer_fee'])
            if not t_name or fee <= 0:
                continue
            norm = normalize_name(t_name)
            if fee > market_val_by_name.get(norm, 0):
                market_val_by_name[norm] = fee
            if fee > market_val_by_exact.get(t_name, 0):
                market_val_by_exact[t_name] = fee

    # 3. Benchmark all-time historical icons & legends with their specific nationality & position
    top_tier_icons = {
        ("Lionel Messi", "Argentina", "Attack"): 180000000,
        ("Cristiano Ronaldo", "Portugal", "Attack"): 180000000,
        ("Pelé", "Brazil", "Attack"): 180000000,
        ("Diego Maradona", "Argentina", "Attack"): 180000000,
        ("Johan Cruyff", "Netherlands", "Attack"): 170000000,
        ("Zinedine Zidane", "France", "Midfield"): 170000000,
        ("Zinédine Zidane", "France", "Midfield"): 170000000,
        ("Ronaldo", "Brazil", "Attack"): 170000000,           # Ronaldo Nazário (R9)
        ("Ronaldo Nazário", "Brazil", "Attack"): 170000000,
        ("Ronaldinho", "Brazil", "Attack"): 160000000,
        ("Franz Beckenbauer", "Germany", "Defender"): 160000000,
        ("Alfredo Di Stéfano", "Argentina", "Attack"): 150000000,
        ("Ferenc Puskás", "Hungary", "Attack"): 150000000,
        ("Michel Platini", "France", "Midfield"): 150000000,
        ("Gerd Müller", "Germany", "Attack"): 150000000,
        ("Marco van Basten", "Netherlands", "Attack"): 150000000,
        ("Paolo Maldini", "Italy", "Defender"): 150000000,
        ("Roberto Baggio", "Italy", "Attack"): 140000000,
        ("Thierry Henry", "France", "Attack"): 140000000,
        ("Kaká", "Brazil", "Midfield"): 140000000,
        ("Andrés Iniesta", "Spain", "Midfield"): 140000000,
        ("Xavi", "Spain", "Midfield"): 140000000,
        ("Dennis Bergkamp", "Netherlands", "Attack"): 130000000,
        ("David Beckham", "England", "Midfield"): 130000000,
        ("Ruud Gullit", "Netherlands", "Midfield"): 130000000,
        ("George Best", "Northern Ireland", "Attack"): 130000000,
        ("Garrincha", "Brazil", "Attack"): 130000000,
        ("Eusébio", "Portugal", "Attack"): 130000000,
        ("Lev Yashin", "Russia", "Goalkeeper"): 120000000,
        ("Franco Baresi", "Italy", "Defender"): 120000000,
        ("Bobby Charlton", "England", "Midfield"): 120000000,
        ("Lothar Matthäus", "Germany", "Midfield"): 120000000,
        ("Gianluigi Buffon", "Italy", "Goalkeeper"): 120000000,
        ("Iker Casillas", "Spain", "Goalkeeper"): 120000000,
        ("Wayne Rooney", "England", "Attack"): 120000000,
        ("Raúl", "Spain", "Attack"): 120000000,
        ("Luis Figo", "Portugal", "Attack"): 120000000,
        ("Rivaldo", "Brazil", "Attack"): 120000000,
        ("Romário", "Brazil", "Attack"): 120000000,
        ("Steven Gerrard", "England", "Midfield"): 110000000,
        ("Frank Lampard", "England", "Midfield"): 110000000,
        ("Andrea Pirlo", "Italy", "Midfield"): 110000000,
        ("Carles Puyol", "Spain", "Defender"): 100000000,
        ("Alessandro Del Piero", "Italy", "Attack"): 100000000,
        ("Francesco Totti", "Italy", "Attack"): 100000000,
        ("Didier Drogba", "Cote d'Ivoire", "Attack"): 100000000,
        ("Samuel Eto'o", "Cameroon", "Attack"): 100000000,
        ("Clarence Seedorf", "Netherlands", "Midfield"): 100000000,
        ("Patrick Vieira", "France", "Midfield"): 100000000,
        ("Paul Scholes", "England", "Midfield"): 100000000,
        ("Ryan Giggs", "Wales", "Midfield"): 100000000,
        ("Ruud van Nistelrooy", "Netherlands", "Attack"): 100000000,
        ("Andriy Shevchenko", "Ukraine", "Attack"): 100000000,
        ("Michael Ballack", "Germany", "Midfield"): 100000000,
        ("Pavel Nedvěd", "Czech Republic", "Midfield"): 100000000,
        ("Fabio Cannavaro", "Italy", "Defender"): 100000000,
        ("Roberto Carlos", "Brazil", "Defender"): 100000000,
        ("Cafu", "Brazil", "Defender"): 100000000,
        ("Javier Zanetti", "Argentina", "Defender"): 100000000
    }

    for (icon_name, icon_nat, icon_pos), icon_val in top_tier_icons.items():
        norm = normalize_name(icon_name)
        norm_nat = normalize_name(icon_nat)
        norm_pos = normalize_name(icon_pos)
        tuple_key = (norm, norm_nat, norm_pos)
        market_val_by_tuple[tuple_key] = max(market_val_by_tuple.get(tuple_key, 0), icon_val)

    # Ingest historical_careers.json (ensure all 507 legends have at least €80M benchmark)
    if os.path.exists(historical_path):
        with open(historical_path, 'r', encoding='utf-8') as f:
            hist_careers = json.load(f)
        for legend_name, info in hist_careers.items():
            norm = normalize_name(legend_name)
            nat = normalize_name(info.get("nationality", ""))
            pos = normalize_name(to_macro_pos(info.get("position", "Player")))
            benchmark = 80000000
            tuple_key = (norm, nat, pos)
            market_val_by_tuple[tuple_key] = max(market_val_by_tuple.get(tuple_key, 0), benchmark)

    # Track distinct entities per name in Kaggle database to identify homonyms
    entities_per_name = {}
    if player_files:
        for _, row in df_players.iterrows():
            name = str(row['name']).strip()
            if not name or name == 'nan':
                continue
            norm = normalize_name(name)
            nat = normalize_name(str(row['country_of_citizenship'])) if pd.notna(row['country_of_citizenship']) else ''
            pos = normalize_name(to_macro_pos(str(row['position']))) if pd.notna(row['position']) else ''
            entities_per_name.setdefault(norm, set()).add((nat, pos))

    # 4. Ingest players from df_players, existing_players, and historical legends
    # Deduplicate by (norm_name, norm_nat, norm_pos) so distinct players sharing the same name are preserved
    player_entity_map = {} # (norm_name, norm_nat, norm_pos) -> player_dict

    # Ingest from df_players first (full Kaggle database)
    if player_files:
        for _, row in df_players.iterrows():
            raw_name = str(row['name']) if pd.notna(row['name']) else ""
            if not raw_name or raw_name == 'nan':
                continue
            raw_name = re.sub(r'\s*\(\d+\)$', '', raw_name).strip()
            nat = str(row['country_of_citizenship']) if pd.notna(row['country_of_citizenship']) else ""
            pos = str(row['position']) if pd.notna(row['position']) else "Player"
            sub_pos = str(row['sub_position']) if pd.notna(row['sub_position']) else ""
            
            # Normalize to macro position (Attack, Midfield, Defender, Goalkeeper)
            display_pos = to_macro_pos(pos if pos != "Player" else sub_pos)
            
            val1 = float(row['highest_market_value_in_eur']) if pd.notna(row['highest_market_value_in_eur']) else 0.0
            val2 = float(row['market_value_in_eur']) if pd.notna(row['market_value_in_eur']) else 0.0
            val = max(val1, val2)

            norm = normalize_name(raw_name)
            key = (norm, normalize_name(nat), normalize_name(display_pos))
            
            if key not in player_entity_map or int(val) > player_entity_map[key]['MarketValue']:
                player_entity_map[key] = {
                    "Name": raw_name,
                    "Nationality": nat,
                    "Position": display_pos,
                    "MarketValue": int(val)
                }

    # Ingest / enrich existing_players
    for p in existing_players:
        raw_name = str(p.get('Name', '')).strip()
        if not raw_name:
            continue
        
        nationality = str(p.get('Nationality', ''))
        position = str(p.get('Position', ''))
        val = None

        # Fix specific historical mismatches
        if raw_name == 'Pelé' and nationality == 'Portugal':
            nationality = 'Brazil'
            position = 'Attack'
        elif raw_name == 'Roberto Baggio' and nationality == 'Brazil':
            nationality = 'Italy'
            position = 'Attack'

        macro_pos = to_macro_pos(position)
        norm = normalize_name(raw_name)
        norm_nat = normalize_name(nationality)
        norm_pos = normalize_name(macro_pos)

        # Check tuple override first (exact entity match)
        val = market_val_by_tuple.get((norm, norm_nat, norm_pos))
        if val is None:
            # ONLY use market_val_by_name if this name belongs to a SINGLE unique entity across world football
            if len(entities_per_name.get(norm, set())) <= 1:
                val = market_val_by_name.get(norm, 0)
            else:
                val = 0

        val_int = int(val or 0)
        key = (norm, norm_nat, norm_pos)
        if key not in player_entity_map:
            player_entity_map[key] = {
                "Name": raw_name,
                "Nationality": nationality,
                "Position": macro_pos,
                "MarketValue": val_int
            }
        else:
            if val_int > player_entity_map[key]['MarketValue']:
                player_entity_map[key]['MarketValue'] = val_int
            if not player_entity_map[key]['Nationality'] and nationality:
                player_entity_map[key]['Nationality'] = nationality
            if (not player_entity_map[key]['Position'] or player_entity_map[key]['Position'] == 'Player') and macro_pos != 'Player':
                player_entity_map[key]['Position'] = macro_pos

    # Ensure missing iconic all-time legends are included
    guaranteed_legends = [
        {"Name": "Pelé", "Nationality": "Brazil", "Position": "Attack", "MarketValue": 180000000},
        {"Name": "Diego Maradona", "Nationality": "Argentina", "Position": "Attack", "MarketValue": 180000000},
        {"Name": "Johan Cruyff", "Nationality": "Netherlands", "Position": "Attack", "MarketValue": 160000000},
        {"Name": "Ronaldo Nazário", "Nationality": "Brazil", "Position": "Attack", "MarketValue": 170000000},
        {"Name": "Garrincha", "Nationality": "Brazil", "Position": "Attack", "MarketValue": 130000000},
        {"Name": "Lev Yashin", "Nationality": "Russia", "Position": "Goalkeeper", "MarketValue": 120000000},
        {"Name": "Alfredo Di Stéfano", "Nationality": "Argentina", "Position": "Attack", "MarketValue": 150000000},
        {"Name": "Ferenc Puskás", "Nationality": "Hungary", "Position": "Attack", "MarketValue": 150000000},
        {"Name": "Bobby Charlton", "Nationality": "England", "Position": "Midfield", "MarketValue": 120000000},
        {"Name": "George Best", "Nationality": "Northern Ireland", "Position": "Attack", "MarketValue": 130000000},
        {"Name": "Dino Zoff", "Nationality": "Italy", "Position": "Goalkeeper", "MarketValue": 100000000},
    ]

    for g in guaranteed_legends:
        key = (normalize_name(g['Name']), normalize_name(g['Nationality']), normalize_name(to_macro_pos(g['Position'])))
        g_copy = dict(g)
        g_copy['Position'] = to_macro_pos(g['Position'])
        if key not in player_entity_map or g_copy['MarketValue'] > player_entity_map[key]['MarketValue']:
            player_entity_map[key] = g_copy

    # Ensure all legends from historical_careers.json are included
    if os.path.exists(historical_path):
        with open(historical_path, 'r', encoding='utf-8') as f:
            hist_careers = json.load(f)
        for legend_name, info in hist_careers.items():
            nat = info.get("nationality", "")
            pos = to_macro_pos(info.get("position", "Player"))
            key = (normalize_name(legend_name), normalize_name(nat), normalize_name(pos))
            if key not in player_entity_map:
                player_entity_map[key] = {
                    "Name": legend_name,
                    "Nationality": nat,
                    "Position": pos,
                    "MarketValue": 80000000
                }
            elif player_entity_map[key]['MarketValue'] < 80000000:
                player_entity_map[key]['MarketValue'] = 80000000

    clean_players = list(player_entity_map.values())
    # Pre-sort descending by MarketValue, then alphabetical by Name
    clean_players.sort(key=lambda x: (-x['MarketValue'], x['Name'].lower()))

    enriched_count = sum(1 for p in clean_players if p['MarketValue'] > 0)
    print(f"Enriched {enriched_count} / {len(clean_players)} players with market value > 0.")
    print("Top 15 players by MarketValue:")
    for p in clean_players[:15]:
        print(f"  {p['Name']} ({p['Nationality']} · {p['Position']}) — €{p['MarketValue']:,}")

    # Write back to all_players.json
    with open(all_players_path, 'w', encoding='utf-8') as f:
        json.dump(clean_players, f, ensure_ascii=False, indent=2)

    print(f"Successfully wrote {len(clean_players)} enriched players to {all_players_path}")

if __name__ == '__main__':
    main()
