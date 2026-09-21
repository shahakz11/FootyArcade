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
    all_clubs_path = os.path.join(base_dir, 'all_clubs.json')

    print(f"Loading existing all_clubs.json from {all_clubs_path}...")
    existing_clubs = []
    if os.path.exists(all_clubs_path):
        with open(all_clubs_path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)
            for item in raw_data:
                if isinstance(item, dict):
                    name = item.get('name') or item.get('Name') or ''
                    if name:
                        existing_clubs.append(name.strip())
                elif isinstance(item, str) and item.strip():
                    existing_clubs.append(item.strip())
    print(f"Total raw clubs in all_clubs.json: {len(existing_clubs)}")

    # 1. Ingest davidcariboo datasets
    dc_dir = os.path.expanduser('~/.cache/kagglehub/datasets/davidcariboo/player-scores/versions')
    player_files = sorted(glob.glob(dc_dir + '/**/players.csv', recursive=True))
    transfer_files = sorted(glob.glob(dc_dir + '/**/transfers.csv', recursive=True))
    club_files = sorted(glob.glob(dc_dir + '/**/clubs.csv', recursive=True))

    market_val_by_norm = {}
    market_val_by_exact = {}

    # Aggregate squad market value from players.csv
    if player_files:
        latest_player_file = player_files[-1]
        print(f"Aggregating squad valuations from {latest_player_file}...")
        df_players = pd.read_csv(latest_player_file, low_memory=False)
        for _, row in df_players.iterrows():
            c_name = str(row['current_club_name']) if pd.notna(row['current_club_name']) else ''
            if not c_name or c_name == 'nan':
                continue
            val1 = float(row['market_value_in_eur']) if pd.notna(row['market_value_in_eur']) else 0.0
            val2 = float(row['highest_market_value_in_eur']) if pd.notna(row['highest_market_value_in_eur']) else 0.0
            # Current market value is prime indicator of active squad value, highest as secondary floor
            val = val1 if val1 > 0 else (val2 * 0.5)
            if val <= 0:
                continue
            
            norm = normalize_name(c_name)
            market_val_by_norm[norm] = market_val_by_norm.get(norm, 0) + val
            market_val_by_exact[c_name] = market_val_by_exact.get(c_name, 0) + val

    # Aggregate transfer spending from transfers.csv as valuation floor
    if transfer_files:
        latest_transfer_file = transfer_files[-1]
        print(f"Aggregating transfer volumes from {latest_transfer_file}...")
        df_transfers = pd.read_csv(latest_transfer_file, low_memory=False)
        df_transfers['transfer_fee'] = pd.to_numeric(df_transfers['transfer_fee'], errors='coerce').fillna(0.0)
        for _, row in df_transfers.iterrows():
            fee = float(row['transfer_fee'])
            if fee <= 0:
                continue
            for col in ['from_club_name', 'to_club_name']:
                c_name = str(row[col]) if pd.notna(row[col]) else ''
                if not c_name or c_name == 'nan':
                    continue
                norm = normalize_name(c_name)
                # Transfer volume contribution (scaled)
                contrib = fee * 0.1
                market_val_by_norm[norm] = market_val_by_norm.get(norm, 0) + contrib
                market_val_by_exact[c_name] = market_val_by_exact.get(c_name, 0) + contrib

    # 2. Benchmark curated powerhouse & historic world clubs (floors in EUR)
    curated_benchmarks = {
        # Tier 1 Superclubs (€1.2B - €1.5B)
        "Real Madrid": 1500000000,
        "Manchester City": 1450000000,
        "Arsenal": 1400000000,
        "Arsenal FC": 1400000000,
        "Barcelona": 1350000000,
        "FC Barcelona": 1350000000,
        "Bayern Munich": 1300000000,
        "FC Bayern Munich": 1300000000,
        "Paris Saint-Germain": 1300000000,
        "PSG": 1300000000,
        "Liverpool": 1250000000,
        "Liverpool FC": 1250000000,
        "Chelsea": 1200000000,
        "Chelsea FC": 1200000000,

        # Tier 1.5 Global Giants (€700M - €1.1B)
        "Manchester United": 1000000000,
        "Tottenham Hotspur": 850000000,
        "Tottenham": 850000000,
        "Inter Milan": 800000000,
        "Inter": 800000000,
        "Internazionale": 800000000,
        "FC Internazionale Milano": 800000000,
        "Juventus": 750000000,
        "Juventus FC": 750000000,
        "Atlético Madrid": 750000000,
        "Atlético de Madrid": 750000000,
        "Atletico Madrid": 750000000,
        "Borussia Dortmund": 700000000,
        "AC Milan": 700000000,
        "Milan": 700000000,
        "Aston Villa": 650000000,
        "Newcastle United": 650000000,
        "Newcastle": 650000000,
        "Bayer Leverkusen": 650000000,
        "RB Leipzig": 600000000,
        "Sporting CP": 550000000,
        "Sporting Lisbon": 550000000,
        "Benfica": 550000000,
        "SL Benfica": 550000000,
        "FC Porto": 500000000,
        "Porto": 500000000,
        "Ajax": 500000000,
        "AFC Ajax": 500000000,
        "AS Roma": 500000000,
        "Roma": 500000000,
        "Napoli": 500000000,
        "SSC Napoli": 500000000,
        "Lazio": 450000000,
        "SS Lazio": 450000000,
        "Atalanta": 450000000,
        "Atalanta BC": 450000000,
        "Olympique Marseille": 450000000,
        "Marseille": 450000000,
        "Monaco": 450000000,
        "AS Monaco": 450000000,
        "Olympique Lyon": 400000000,
        "Lyon": 400000000,
        "Sevilla": 400000000,
        "Sevilla FC": 400000000,
        "Real Sociedad": 400000000,
        "Real Betis": 400000000,
        "Athletic Bilbao": 400000000,
        "Athletic Club": 400000000,
        "Villarreal": 400000000,
        "Villarreal CF": 400000000,
        "Valencia": 400000000,
        "Valencia CF": 400000000,
        "Fiorentina": 350000000,
        "ACF Fiorentina": 350000000,
        "West Ham United": 400000000,
        "West Ham": 400000000,
        "Brighton": 400000000,
        "Brighton & Hove Albion": 400000000,
        "Brentford": 350000000,
        "Brentford FC": 350000000,
        "Crystal Palace": 350000000,
        "Fulham": 350000000,
        "Fulham FC": 350000000,
        "Everton": 350000000,
        "Everton FC": 350000000,
        "Wolverhampton Wanderers": 350000000,
        "Wolves": 350000000,

        # Americas & Rest of World Powerhouses
        "Flamengo": 300000000,
        "Palmeiras": 300000000,
        "Boca Juniors": 250000000,
        "River Plate": 250000000,
        "Santos": 200000000,
        "Sao Paulo": 200000000,
        "São Paulo": 200000000,
        "Corinthians": 200000000,
        "Gremio": 200000000,
        "Grêmio": 200000000,
        "Internacional": 200000000,
        "Galatasaray": 300000000,
        "Fenerbahce": 300000000,
        "Fenerbahçe": 300000000,
        "Besiktas": 250000000,
        "Beşiktaş": 250000000,
        "Celtic": 250000000,
        "Celtic FC": 250000000,
        "Rangers": 200000000,
        "Rangers FC": 200000000,
        "Al-Hilal": 300000000,
        "Al-Nassr": 300000000,
        "Al-Ittihad": 250000000,
        "Inter Miami": 250000000,
        "Inter Miami CF": 250000000,
        "LA Galaxy": 200000000,
    }

    for c_name, bench_val in curated_benchmarks.items():
        norm = normalize_name(c_name)
        market_val_by_norm[norm] = max(market_val_by_norm.get(norm, 0), bench_val)
        market_val_by_exact[c_name] = max(market_val_by_exact.get(c_name, 0), bench_val)

    # 3. Enrich existing clubs
    seen_names = set()
    enriched_clubs = []

    for raw_name in existing_clubs:
        norm = normalize_name(raw_name)
        if not norm or norm in seen_names:
            continue
        seen_names.add(norm)

        # Match valuation: 1. Exact, 2. Norm, 3. Cleaned suffix (FC, CF, etc.)
        val = market_val_by_exact.get(raw_name, 0)
        if val <= 0:
            val = market_val_by_norm.get(norm, 0)
        if val <= 0:
            # Try stripping common club suffixes/prefixes
            alt_norm = re.sub(r'^(fc|cf|sc|ac|afc|ssc|as|cd|ud|rcd|us)\s+', '', norm)
            alt_norm = re.sub(r'\s+(fc|cf|sc|ac|afc|ssc|as|cd|ud|rcd|us|de futbol|futbol club)$', '', alt_norm)
            if alt_norm != norm:
                val = market_val_by_norm.get(alt_norm, 0)

        enriched_clubs.append({
            "name": raw_name,
            "market_value": int(val)
        })

    # Also make sure all curated benchmarks are present in the list
    for c_name, bench_val in curated_benchmarks.items():
        norm = normalize_name(c_name)
        if norm not in seen_names:
            seen_names.add(norm)
            enriched_clubs.append({
                "name": c_name,
                "market_value": int(bench_val)
            })

    # Sort descending by market_value, then alphabetical by name
    enriched_clubs.sort(key=lambda x: (-x['market_value'], x['name'].lower()))

    print(f"Writing {len(enriched_clubs)} enriched clubs to {all_clubs_path}...")
    with open(all_clubs_path, 'w', encoding='utf-8') as f:
        json.dump(enriched_clubs, f, ensure_ascii=False, indent=2)

    top_10 = enriched_clubs[:10]
    print("\nTop 10 Enriched Clubs by Market Value:")
    for i, c in enumerate(top_10, 1):
        print(f"  {i}. {c['name']} - €{c['market_value']:,}")

    print("\nEnrichment complete successfully!")

if __name__ == "__main__":
    main()
