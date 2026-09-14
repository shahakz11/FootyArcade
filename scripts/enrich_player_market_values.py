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
    player_files = glob.glob(dc_dir + '/**/players.csv', recursive=True)
    transfer_files = glob.glob(dc_dir + '/**/transfers.csv', recursive=True)

    market_val_by_name = {}  # norm_name -> max_val
    market_val_by_exact = {} # exact_name -> max_val

    if player_files:
        print(f"Loading players from {player_files[0]}...")
        df_players = pd.read_csv(player_files[0], low_memory=False)
        for _, row in df_players.iterrows():
            raw_name = str(row['name']) if pd.notna(row['name']) else ""
            if not raw_name:
                continue
            
            # Use highest_market_value_in_eur or market_value_in_eur
            val1 = float(row['highest_market_value_in_eur']) if pd.notna(row['highest_market_value_in_eur']) else 0.0
            val2 = float(row['market_value_in_eur']) if pd.notna(row['market_value_in_eur']) else 0.0
            val = max(val1, val2)

            norm = normalize_name(raw_name)
            if val > market_val_by_name.get(norm, 0):
                market_val_by_name[norm] = val
            if val > market_val_by_exact.get(raw_name, 0):
                market_val_by_exact[raw_name] = val

    # 2. Ingest davidcariboo transfers (transfer_fee as valuation floor)
    if transfer_files:
        print(f"Loading transfer fees from {transfer_files[0]}...")
        df_transfers = pd.read_csv(transfer_files[0], low_memory=False)
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

    # 3. Benchmark all-time historical icons & legends
    top_tier_icons = {
        "Lionel Messi": 180000000,
        "Cristiano Ronaldo": 180000000,
        "Pelé": 180000000,
        "Diego Maradona": 180000000,
        "Johan Cruyff": 170000000,
        "Zinedine Zidane": 170000000,
        "Zinédine Zidane": 170000000,
        "Ronaldo": 170000000,           # Ronaldo Nazário (R9)
        "Ronaldo Nazário": 170000000,
        "Ronaldinho": 160000000,
        "Franz Beckenbauer": 160000000,
        "Alfredo Di Stéfano": 150000000,
        "Ferenc Puskás": 150000000,
        "Michel Platini": 150000000,
        "Gerd Müller": 150000000,
        "Marco van Basten": 150000000,
        "Paolo Maldini": 150000000,
        "Roberto Baggio": 140000000,
        "Thierry Henry": 140000000,
        "Kaká": 140000000,
        "Andrés Iniesta": 140000000,
        "Xavi": 140000000,
        "Dennis Bergkamp": 130000000,
        "David Beckham": 130000000,
        "Ruud Gullit": 130000000,
        "George Best": 130000000,
        "Garrincha": 130000000,
        "Eusébio": 130000000,
        "Lev Yashin": 120000000,
        "Franco Baresi": 120000000,
        "Bobby Charlton": 120000000,
        "Lothar Matthäus": 120000000,
        "Gianluigi Buffon": 120000000,
        "Iker Casillas": 120000000,
        "Wayne Rooney": 120000000,
        "Raúl": 120000000,
        "Luis Figo": 120000000,
        "Rivaldo": 120000000,
        "Romário": 120000000,
        "Steven Gerrard": 110000000,
        "Frank Lampard": 110000000,
        "Andrea Pirlo": 110000000,
        "Carles Puyol": 100000000,
        "Alessandro Del Piero": 100000000,
        "Francesco Totti": 100000000,
        "Didier Drogba": 100000000,
        "Samuel Eto'o": 100000000,
        "Clarence Seedorf": 100000000,
        "Patrick Vieira": 100000000,
        "Paul Scholes": 100000000,
        "Ryan Giggs": 100000000,
        "Ruud van Nistelrooy": 100000000,
        "Andriy Shevchenko": 100000000,
        "Michael Ballack": 100000000,
        "Pavel Nedvěd": 100000000,
        "Fabio Cannavaro": 100000000,
        "Roberto Carlos": 100000000,
        "Cafu": 100000000,
        "Javier Zanetti": 100000000
    }

    for icon_name, icon_val in top_tier_icons.items():
        norm = normalize_name(icon_name)
        market_val_by_name[norm] = max(market_val_by_name.get(norm, 0), icon_val)
        market_val_by_exact[icon_name] = max(market_val_by_exact.get(icon_name, 0), icon_val)

    # Ingest historical_careers.json (ensure all 507 legends have at least €80M benchmark)
    if os.path.exists(historical_path):
        with open(historical_path, 'r', encoding='utf-8') as f:
            hist_careers = json.load(f)
        for legend_name in hist_careers.keys():
            norm = normalize_name(legend_name)
            benchmark = 80000000
            if benchmark > market_val_by_name.get(norm, 0):
                market_val_by_name[norm] = benchmark
            if benchmark > market_val_by_exact.get(legend_name, 0):
                market_val_by_exact[legend_name] = benchmark

    # 4. Enrich existing_players with MarketValue
    enriched_count = 0
    clean_players = []
    seen = set()

    for p in existing_players:
        raw_name = str(p.get('Name', '')).strip()
        if not raw_name:
            continue
        
        nationality = str(p.get('Nationality', ''))
        position = str(p.get('Position', ''))

        # Fix specific historical mismatches
        if raw_name == 'Pelé' and nationality == 'Portugal':
            # Create/correct Brazilian Pelé
            nationality = 'Brazil'
            position = 'Attack'
        elif raw_name == 'Roberto Baggio' and nationality == 'Brazil':
            nationality = 'Italy'
            position = 'Attack - Second Striker'

        norm = normalize_name(raw_name)
        val = market_val_by_exact.get(raw_name)
        if val is None:
            val = market_val_by_name.get(norm, 0)

        p_copy = {
            "Name": raw_name,
            "Nationality": nationality,
            "Position": position,
            "MarketValue": int(val)
        }
        if val > 0:
            enriched_count += 1

        seen.add(raw_name.lower())
        clean_players.append(p_copy)

    # Ensure missing iconic all-time legends are included
    guaranteed_legends = [
        {"Name": "Pelé", "Nationality": "Brazil", "Position": "Attack", "MarketValue": 180000000},
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
        if g['Name'].lower() not in seen:
            seen.add(g['Name'].lower())
            clean_players.append(g)
            enriched_count += 1

    # Pre-sort descending by MarketValue, then alphabetical by Name
    clean_players.sort(key=lambda x: (-x['MarketValue'], x['Name'].lower()))

    print(f"Enriched {enriched_count} / {len(clean_players)} players with market value > 0.")
    print("Top 15 players by MarketValue:")
    for p in clean_players[:15]:
        print(f"  {p['Name']} ({p['Nationality']}) — €{p['MarketValue']:,}")

    # Write back to all_players.json
    with open(all_players_path, 'w', encoding='utf-8') as f:
        json.dump(clean_players, f, ensure_ascii=False, indent=2)

    print(f"Successfully wrote {len(clean_players)} enriched players to {all_players_path}")

if __name__ == '__main__':
    main()
