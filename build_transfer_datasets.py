import os
import re
import pandas as pd
import random
import kagglehub

def main():
    print("Loading player-scores dataset...")
    try:
        path = kagglehub.dataset_download("davidcariboo/player-scores")
    except Exception:
        path = os.path.expanduser('~/.cache/kagglehub/datasets/davidcariboo/player-scores/versions/671')
    print(f"Dataset path: {path}")

    # Load players and transfers
    players_file = os.path.join(path, 'players.csv')
    transfers_file = os.path.join(path, 'transfers.csv')

    print("Loading players and transfers data...")
    df = pd.read_csv(players_file)
    df_transfers = pd.read_csv(transfers_file)

    # Convert transfer fee to numeric, drop NaNs
    df_transfers['transfer_fee'] = pd.to_numeric(df_transfers['transfer_fee'], errors='coerce')
    df_transfers.dropna(subset=['transfer_fee'], inplace=True)

    # Manual additions for famous missing historical transfers
    manual_transfers = pd.DataFrame([
        {
            'player_id': 39153,
            'player_name': 'Gonzalo Higuaín',
            'from_club_name': 'Napoli',
            'to_club_name': 'Juventus',
            'transfer_fee': 90000000.0,
            'transfer_date': '2016-07-26',
            'market_value_in_eur': 65000000.0
        }
    ])
    df_transfers = pd.concat([df_transfers, manual_transfers], ignore_index=True)

    # Normalize/clean club names (Youth, B teams, different variations, corporate suffixes, trailing dots)
    prefix_pattern = re.compile(r'^(1\.\s*FC|1\.\s*FSV|1\.\s*|FC|CF|AC|AS|SS|SV|SC|SD|CD|UD|RC|RCD|FK|SK|BK|IF|IFK|OGC|US|USM|GC|AFC|SAD|CA|CE|CS|CP|VfB|VfL|TSG|BSC|FSV|SSV|SpVgg|Club)\s+', re.I)
    suffix_pattern = re.compile(r'\s+(Football Club|Association Football Club|Club de Fútbol|Club de Futbol|Fútbol Club|Futbol Club|Soccer Club|Sports Club|Sport Club|Athletic Club|Club|FC|CF|SC|CSC|S\.A\.D\.|R\.C\.D\.|C\.D\.|F\.C\.|C\.F\.|AF|FK|SK|BK|SV|EV|e\.V\.|eV|AC|SD|UD|RC|SAD|Res|Reserves|Youth|Yth|Academy|Junioren|Castilla|II|B|U-?\d+|Sub-?\d+|Sub\s*\d+|Under-?\d+|Under\s*\d+)\b', re.I)

    aliases = {
        # Germany
        'Leipzig': 'RB Leipzig', 'RB Leipzig': 'RB Leipzig', 'RB Leipzig.': 'RB Leipzig', 'S. Leipzig': 'RB Leipzig', 'RasenBallsport Leipzig': 'RB Leipzig', 'Rasenballsport Leipzig': 'RB Leipzig',
        'Bor. Dortmund': 'Borussia Dortmund', 'B. Dortmund': 'Borussia Dortmund', 'Dortmund': 'Borussia Dortmund',
        'FC Bayern': 'Bayern Munich', 'Bayern München': 'Bayern Munich', 'FC Bayern München': 'Bayern Munich', 'Bayern Munich': 'Bayern Munich',
        'Bayer 04 Leverkusen': 'Bayer Leverkusen', 'B. Leverkusen': 'Bayer Leverkusen', 'Leverkusen': 'Bayer Leverkusen', 'Bayer Leverkusen': 'Bayer Leverkusen',
        'M\'gladbach': 'Borussia Mönchengladbach', 'B. M\'gladbach': 'Borussia Mönchengladbach', 'Bor. M\'gladbach': 'Borussia Mönchengladbach', 'Borussia M\'gladbach': 'Borussia Mönchengladbach', 'Borussia Mönchengladbach': 'Borussia Mönchengladbach',
        '1.FC Kaiserslautern': 'Kaiserslautern', '1. FC Kaiserslautern': 'Kaiserslautern', 'K\'lautern': 'Kaiserslautern',
        '1.FC Nürnberg': 'Nuremberg', '1. FC Nürnberg': 'Nuremberg', '1.FC Nuremberg': 'Nuremberg', 'Nürnberg': 'Nuremberg', 'Nuremberg': 'Nuremberg',
        '1.FC Köln': 'Köln', '1. FC Köln': 'Köln', 'FC Köln': 'Köln', 'Koln': 'Köln',
        '1.FC Magdeburg': 'Magdeburg', '1. FC Magdeburg': 'Magdeburg',
        '1.FC Union Berlin': 'Union Berlin', '1. FC Union Berlin': 'Union Berlin', 'Union Berlin': 'Union Berlin',
        '1.FSV Mainz 05': 'Mainz 05', '1. FSV Mainz 05': 'Mainz 05', 'FSV Mainz 05': 'Mainz 05', 'Mainz 05': 'Mainz 05', 'Mainz': 'Mainz 05',
        'VfB Stuttgart': 'Stuttgart', 'Stuttgart': 'Stuttgart',
        'VfL Wolfsburg': 'Wolfsburg', 'Wolfsburg': 'Wolfsburg',
        'VfL Bochum': 'Bochum', 'Bochum': 'Bochum',
        'TSG 1899 Hoffenheim': 'Hoffenheim', 'TSG Hoffenheim': 'Hoffenheim', 'Hoffenheim': 'Hoffenheim',
        'Hertha BSC': 'Hertha Berlin', 'Hertha Berlin': 'Hertha Berlin',
        'Schalke 04': 'Schalke', 'FC Schalke 04': 'Schalke', 'Schalke': 'Schalke',

        # England
        'Man City': 'Manchester City', 'Manchester City': 'Manchester City',
        'Man United': 'Manchester United', 'Man Utd': 'Manchester United', 'Manchester United': 'Manchester United',
        'Spurs': 'Tottenham Hotspur', 'Tottenham': 'Tottenham Hotspur', 'Tottenham Hotspur': 'Tottenham Hotspur',
        'Arsenal': 'Arsenal', 'Chelsea': 'Chelsea', 'Liverpool': 'Liverpool', 'Everton': 'Everton',
        'Newcastle': 'Newcastle United', 'Newcastle United': 'Newcastle United',
        'West Ham': 'West Ham United', 'West Ham United': 'West Ham United',
        'Wolves': 'Wolverhampton Wanderers', 'Wolverhampton Wanderers': 'Wolverhampton Wanderers', 'Wolverhampton': 'Wolverhampton Wanderers',
        'Leicester': 'Leicester City', 'Leicester City': 'Leicester City',
        'Leeds': 'Leeds United', 'Leeds United': 'Leeds United',
        'Brighton': 'Brighton & Hove Albion', 'Brighton & Hove Albion': 'Brighton & Hove Albion', 'Brighton and Hove Albion': 'Brighton & Hove Albion',

        # Spain
        'Real Madrid': 'Real Madrid', 'FC Barcelona': 'Barcelona', 'Barca': 'Barcelona', 'Barcelona': 'Barcelona',
        'Atlético Madrid': 'Atletico Madrid', 'Atlético': 'Atletico Madrid', 'Atletico': 'Atletico Madrid', 'Atletico Madrid': 'Atletico Madrid',
        'Athletic Bilbao': 'Athletic Bilbao', 'Athletic Club': 'Athletic Bilbao',
        'Sevilla FC': 'Sevilla', 'Sevilla': 'Sevilla',
        'Real Betis': 'Real Betis', 'Betis': 'Real Betis',
        'Real Sociedad': 'Real Sociedad',
        'Villarreal CF': 'Villarreal', 'Villarreal': 'Villarreal',
        'Valencia CF': 'Valencia', 'Valencia': 'Valencia',
        'UD Almería': 'Almería', 'Almería': 'Almería', 'Almeria': 'Almería',
        'CD Alcoyano': 'Alcoyano', 'Alcoyano': 'Alcoyano',
        'RCD Espanyol': 'Espanyol', 'Espanyol': 'Espanyol',
        'RCD Mallorca': 'Mallorca', 'Mallorca': 'Mallorca',
        'Celta de Vigo': 'Celta Vigo', 'Celta Vigo': 'Celta Vigo',
        'Osasuna': 'Osasuna', 'CA Osasuna': 'Osasuna',

        # Italy
        'Inter Milan': 'Inter', 'FC Internazionale Milano': 'Inter', 'Internazionale': 'Inter', 'Inter': 'Inter',
        'AC Milan': 'AC Milan', 'Milan': 'AC Milan',
        'Juventus': 'Juventus', 'SSC Napoli': 'Napoli', 'Napoli': 'Napoli',
        'AS Roma': 'Roma', 'Roma': 'Roma',
        'SS Lazio': 'Lazio', 'Lazio': 'Lazio',
        'ACF Fiorentina': 'Fiorentina', 'Fiorentina': 'Fiorentina',
        'Atalanta BC': 'Atalanta', 'Atalanta': 'Atalanta',
        'Torino FC': 'Torino', 'Torino': 'Torino',
        'AC Monaco': 'Monaco', 'AS Monaco': 'Monaco', 'Monaco': 'Monaco',
        'AC Ajaccio': 'Ajaccio', 'AS Ajaccio': 'Ajaccio', 'Ajaccio': 'Ajaccio',

        # France
        'Paris SG': 'Paris Saint-Germain', 'PSG': 'Paris Saint-Germain', 'Paris Saint-Germain': 'Paris Saint-Germain',
        'Paris FC': 'Paris FC', 'Paris FC.': 'Paris FC', 'Paris FC B': 'Paris FC', 'Paris FC U19': 'Paris FC', 'Paris FC U17': 'Paris FC', 'Paris FC Yth.': 'Paris FC',
        'Olympique Marseille': 'Marseille', 'Olympique de Marseille': 'Marseille', 'OM': 'Marseille', 'Marseille': 'Marseille',
        'Olympique Lyon': 'Lyon', 'Olympique Lyonnais': 'Lyon', 'OL': 'Lyon', 'Lyon': 'Lyon',
        'AS Saint-Étienne': 'Saint-Étienne', 'Saint-Étienne': 'Saint-Étienne', 'Saint-Etienne': 'Saint-Étienne',
        'LOSC Lille': 'Lille', 'Lille OSC': 'Lille', 'Lille': 'Lille',
        'OGC Nice': 'Nice', 'Nice': 'Nice',
        'FC Nantes': 'Nantes', 'Nantes': 'Nantes',
        'Stade Rennais': 'Rennes', 'Rennes': 'Rennes',

        # Portugal / Netherlands / Turkey / Others
        'Sporting CP': 'Sporting CP', 'Sporting Lisbon': 'Sporting CP', 'Sporting': 'Sporting CP',
        'SL Benfica': 'Benfica', 'Benfica': 'Benfica',
        'FC Porto': 'Porto', 'Porto': 'Porto',
        'AFC Ajax': 'Ajax', 'Ajax': 'Ajax',
        'PSV Eindhoven': 'PSV Eindhoven', 'PSV': 'PSV Eindhoven',
        'Feyenoord Rotterdam': 'Feyenoord', 'Feyenoord': 'Feyenoord',
        'Galatasaray SK': 'Galatasaray', 'Galatasaray': 'Galatasaray',
        'Fenerbahçe SK': 'Fenerbahce', 'Fenerbahce SK': 'Fenerbahce', 'Fenerbahce': 'Fenerbahce',
        'Beşiktaş JK': 'Besiktas', 'Besiktas JK': 'Besiktas', 'Besiktas': 'Besiktas',

        # Saudi / Gulf
        'Al-Nassr': 'Al-Nassr', 'Al Nassr': 'Al-Nassr', 'Al-Nassr FC': 'Al-Nassr',
        'Al-Hilal': 'Al-Hilal', 'Al Hilal': 'Al-Hilal',
        'Al-Ittihad': 'Al-Ittihad', 'Al Ittihad': 'Al-Ittihad',
        'Al-Ahli': 'Al-Ahli', 'Al Ahli': 'Al-Ahli', 'Al-Ahly': 'Al-Ahli',
        'Al-Ettifaq': 'Al-Ettifaq', 'Al Ettifaq': 'Al-Ettifaq',
        'Al-Fateh': 'Al-Fateh', 'Al Fateh': 'Al-Fateh',
        'Al-Fayha': 'Al-Fayha', 'Al Fayha': 'Al-Fayha',
        'Al-Gharafa': 'Al-Gharafa',
        'Al-Hazem': 'Al-Hazem',
        'Al-Shabab': 'Al-Shabab', 'Al Shabab': 'Al-Shabab',
        'Al-Taawoun': 'Al-Taawoun',
        'Al-Kholood': 'Al-Kholood', 'Al Kholood': 'Al-Kholood',
        'Al-Najma': 'Al-Najma',
        'Al-Okhdood': 'Al-Okhdood', 'Al Okhdood': 'Al-Okhdood',
        'Al-Qadsiah': 'Al-Qadsiah', 'Al Qadsiah': 'Al-Qadsiah',
    }

    def clean_club_name(val):
        if not isinstance(val, str):
            return val
        val = val.strip().strip('.').strip('"').strip("'")
        if not val:
            return ''

        if val in aliases:
            return aliases[val]

        cleaned = val
        cleaned = prefix_pattern.sub('', cleaned)
        cleaned = suffix_pattern.sub('', cleaned)
        cleaned = prefix_pattern.sub('', cleaned)
        cleaned = suffix_pattern.sub('', cleaned)
        cleaned = cleaned.strip().strip('.')

        if cleaned in aliases:
            return aliases[cleaned]

        if cleaned.startswith('Al ') and not cleaned.startswith('Al-'):
            cleaned = 'Al-' + cleaned[3:]

        return cleaned if cleaned else val

    print("Normalizing club names in dataset...")
    df_transfers['from_club_name'] = df_transfers['from_club_name'].apply(clean_club_name)
    df_transfers['to_club_name'] = df_transfers['to_club_name'].apply(clean_club_name)

    TRANSFER_FEE_THRESHOLD = 6_000_000

    # --- 1. Generating Club Transfers ---
    print("Processing Club Transfers...")
    high_value_transfers = df_transfers[df_transfers['transfer_fee'] > TRANSFER_FEE_THRESHOLD]
    club_high_value_transfers_count = high_value_transfers['to_club_name'].value_counts()
    eligible_clubs = club_high_value_transfers_count[club_high_value_transfers_count >= 10].index.tolist()

    print(f"Number of eligible clubs: {len(eligible_clubs)}")

    # We want to generate a deterministic list of daily games for 180 days (or cycling through all eligible clubs)
    all_game_data = []
    num_days = 180

    # Seed for deterministic generation
    random.seed(42)
    shuffled_clubs = eligible_clubs.copy()
    random.shuffle(shuffled_clubs)

    for day in range(num_days):
        selected_club = shuffled_clubs[day % len(shuffled_clubs)]
        club_transfers = df_transfers[
            (df_transfers['to_club_name'] == selected_club) &
            (df_transfers['transfer_fee'] > TRANSFER_FEE_THRESHOLD)
        ].copy()

        top_transfers = club_transfers.sort_values(by='transfer_fee', ascending=False).head(10)
        
        # Add metadata columns
        top_transfers['game_day'] = day + 1
        top_transfers['selected_club'] = selected_club
        
        all_game_data.append(top_transfers[['player_name', 'from_club_name', 'to_club_name', 'transfer_fee', 'transfer_date', 'game_day', 'selected_club']])

    club_df = pd.concat(all_game_data, ignore_index=True)
    club_df.to_csv('daily_transfer_games.csv', index=False)
    print(f"Successfully generated club game data and saved to 'daily_transfer_games.csv'")


    # --- 2. Generating Nationality Transfers ---
    print("Processing Nationality Transfers...")
    # Merge df_transfers with players to get nationality
    df_merged_for_nationality = pd.merge(
        df_transfers,
        df[['player_id', 'country_of_citizenship']],
        on='player_id',
        how='left'
    )
    df_merged_for_nationality.rename(columns={'country_of_citizenship': 'nationality_name'}, inplace=True)
    df_merged_for_nationality.dropna(subset=['nationality_name'], inplace=True)

    high_value_nationality_transfers = df_merged_for_nationality[
        df_merged_for_nationality['transfer_fee'] > TRANSFER_FEE_THRESHOLD
    ]
    # For nationalities, count unique players with transfer fee > threshold
    nat_unique_players = high_value_nationality_transfers.groupby('nationality_name')['player_name'].nunique()
    eligible_nationalities = nat_unique_players[nat_unique_players >= 10].index.tolist()

    print(f"Number of eligible nationalities: {len(eligible_nationalities)}")

    all_game_data_nationality = []
    shuffled_nationalities = eligible_nationalities.copy()
    random.shuffle(shuffled_nationalities)

    for day in range(num_days):
        selected_nationality = shuffled_nationalities[day % len(shuffled_nationalities)]
        
        nationality_transfers = df_merged_for_nationality[
            (df_merged_for_nationality['nationality_name'] == selected_nationality) &
            (df_merged_for_nationality['transfer_fee'] > TRANSFER_FEE_THRESHOLD)
        ].copy()

        # For each player, select only their highest transfer fee (unique player)
        idx = nationality_transfers.groupby(['player_name'])['transfer_fee'].idxmax()
        unique_player_transfers = nationality_transfers.loc[idx]

        top_transfers = unique_player_transfers.sort_values(by='transfer_fee', ascending=False).head(10)
        
        top_transfers['game_day'] = day + 1
        top_transfers['selected_nationality'] = selected_nationality

        all_game_data_nationality.append(top_transfers[['player_name', 'nationality_name', 'from_club_name', 'to_club_name', 'transfer_fee', 'transfer_date', 'game_day', 'selected_nationality']])

    nat_df = pd.concat(all_game_data_nationality, ignore_index=True)
    nat_df.to_csv('daily_nationality_transfer_games.csv', index=False)
    print(f"Successfully generated nationality game data and saved to 'daily_nationality_transfer_games.csv'")

    # --- 3. Generating Autocomplete Player List ---
    print("Generating autocomplete player list...")
    df_players_clean = df.dropna(subset=['name']).copy()
    df_players_clean['country_of_citizenship'] = df_players_clean['country_of_citizenship'].fillna('')
    df_players_clean['position'] = df_players_clean['position'].fillna('')
    df_players_clean.drop_duplicates(subset=['name'], inplace=True)
    
    autocomplete_list = []
    seen_players = set()
    for _, row in df_players_clean.iterrows():
        p_name = row['name']
        seen_players.add(p_name.lower())
        autocomplete_list.append({
            "Name": p_name,
            "Nationality": row['country_of_citizenship'],
            "Position": row['position']
        })
        
    for t_name in df_transfers['player_name'].dropna().unique():
        if t_name.lower() not in seen_players:
            seen_players.add(t_name.lower())
            autocomplete_list.append({
                "Name": t_name,
                "Nationality": "",
                "Position": "Player"
            })
        
    import json
    with open('all_players.json', 'w', encoding='utf-8') as f_out:
        json.dump(autocomplete_list, f_out, ensure_ascii=False, indent=2)
    print(f"Successfully generated autocomplete list with {len(autocomplete_list)} players in 'all_players.json'")

    # --- 4. Generating Transfer Destination Games ---
    print("Processing Transfer Destination Games...")
    # Merge transfers with player DOB, nationality, and position
    df_dest_merged = pd.merge(
        df_transfers,
        df[['player_id', 'date_of_birth', 'country_of_citizenship', 'position']],
        on='player_id',
        how='left'
    )
    df_dest_merged['transfer_date'] = pd.to_datetime(df_dest_merged['transfer_date'])
    df_dest_merged['date_of_birth'] = pd.to_datetime(df_dest_merged['date_of_birth'])
    df_dest_merged['age_at_transfer'] = (df_dest_merged['transfer_date'] - df_dest_merged['date_of_birth']).dt.days / 365.25

    # Filter youth teams
    youth_patterns = r"(?i)U\d+|Sub-\d+|Sub\s+\d+|Youth|Yth|Academy|Junioren|Under-|Sub\s+1|Sub\s+2"
    df_dest_clean = df_dest_merged[
        (~df_dest_merged['from_club_name'].str.contains(youth_patterns, na=False)) &
        (~df_dest_merged['to_club_name'].str.contains(youth_patterns, na=False))
    ].copy()
    
    # Filter age >= 17
    df_dest_clean = df_dest_clean[df_dest_clean['age_at_transfer'] >= 17]

    # Find players with at least one transfer >= 15m
    players_with_big_tr = df_dest_clean[df_dest_clean['transfer_fee'] >= 15_000_000]['player_id'].unique()
    df_dest_clean_big = df_dest_clean[df_dest_clean['player_id'].isin(players_with_big_tr)]
    
    # Count transfers per player and ensure at least 2 transfers
    dest_transfer_counts = df_dest_clean_big.groupby('player_id').size()
    eligible_dest_pids = dest_transfer_counts[dest_transfer_counts >= 2].index.tolist()
    
    df_dest_eligible = df_dest_clean_big[df_dest_clean_big['player_id'].isin(eligible_dest_pids)]
    
    # Sort eligible players by their maximum transfer fee to pick the most high-profile stars
    player_max_fees = df_dest_eligible.groupby('player_id')['transfer_fee'].max()
    top_dest_pids = player_max_fees.sort_values(ascending=False).index.tolist()
    
    # Take the top 300 to shuffle and select 180 games
    # Shuffling with a seed for deterministic daily puzzles
    random.seed(99)
    shuffled_pids = top_dest_pids[:300]
    random.shuffle(shuffled_pids)
    selected_pids = shuffled_pids[:180]
    
    dest_games_list = []
    clubs_in_careers = set()
    
    for day, pid in enumerate(selected_pids):
        p_transfers = df_dest_eligible[df_dest_eligible['player_id'] == pid].copy()
        # Sort chronologically
        p_transfers = p_transfers.sort_values(by='transfer_date')
        p_transfers['game_day'] = day + 1
        
        # Keep track of clubs for autocomplete
        for _, row in p_transfers.iterrows():
            if pd.notna(row['from_club_name']):
                clubs_in_careers.add(row['from_club_name'])
            if pd.notna(row['to_club_name']):
                clubs_in_careers.add(row['to_club_name'])
            
        dest_games_list.append(p_transfers)
        
    dest_games_df = pd.concat(dest_games_list, ignore_index=True)
    # Format transfer_date back to string for easier frontend parsing
    dest_games_df['transfer_date_str'] = dest_games_df['transfer_date'].dt.strftime('%Y-%m-%d')
    
    # Fill NaN columns with appropriate empty strings/values
    dest_games_df['from_club_name'] = dest_games_df['from_club_name'].fillna('')
    dest_games_df['to_club_name'] = dest_games_df['to_club_name'].fillna('')
    dest_games_df['transfer_fee'] = dest_games_df['transfer_fee'].fillna(0.0)
    dest_games_df['market_value_in_eur'] = dest_games_df['market_value_in_eur'].fillna(0.0)
    
    dest_games_df.to_csv('daily_destination_games.csv', index=False)
    print(f"Successfully generated destination game data for 180 days in 'daily_destination_games.csv'")
    
    # --- 6. Generating Top Scorers Games (Leagues & International/European Cups) ---
    print("Processing Top Scorers Games (Top 5 Leagues + Champions League, Europa League, World Cup)...")
    appearances_file = os.path.join(path, 'appearances.csv')
    clubs_file_path = os.path.join(path, 'clubs.csv')
    games_file_path = os.path.join(path, 'games.csv')

    if os.path.exists(appearances_file) and os.path.exists(clubs_file_path) and os.path.exists(games_file_path):
        from collections import Counter

        df_apps = pd.read_csv(appearances_file)
        df_clubs_raw = pd.read_csv(clubs_file_path)
        df_games_raw = pd.read_csv(games_file_path)

        # Map competition IDs to display names
        target_comps_map = {
            'GB1': 'Premier League',
            'ES1': 'La Liga',
            'IT1': 'Serie A',
            'L1': 'Bundesliga',
            'FR1': 'Ligue 1',
            'CL': 'UEFA Champions League',
            'EL': 'UEFA Europa League',
            'FIWC': 'FIFA World Cup'
        }

        # Merge appearances with games.csv to get true competition_id, season, and round
        df_apps_merged = pd.merge(
            df_apps,
            df_games_raw[['game_id', 'season', 'round', 'competition_id']],
            on='game_id',
            how='inner',
            suffixes=('', '_game')
        )

        df_apps_target = df_apps_merged[df_apps_merged['competition_id'].isin(target_comps_map.keys())].copy()
        df_apps_target['goals'] = pd.to_numeric(df_apps_target['goals'], errors='coerce').fillna(0).astype(int)

        # Exclude UCL/UEL qualifying rounds to match official main tournament top scorer tallies
        qualifying_rounds = ['1st Qualifying Round', '2nd Qualifying Round', '3rd Qualifying Round', 'Play-Offs', 'Qualifying Round']
        df_apps_target = df_apps_target[~((df_apps_target['competition_id'].isin(['CL', 'EL'])) & (df_apps_target['round'].isin(qualifying_rounds)))]

        # Derive edition (Season format YYYY/YY+1 for club competitions, Year format YYYY for World Cup)
        def get_edition(row):
            comp = row['competition_id']
            season = int(row['season'])
            if comp == 'FIWC':
                return str(season + 1)
            else:
                return f"{season}/{str(season+1)[-2:]}"

        df_apps_target['edition'] = df_apps_target.apply(get_edition, axis=1)

        # Filter valid complete editions (2012/13 to 2024/25 for club competitions, 2010 to 2022 for World Cup)
        valid_seasons = [f"{y}/{str(y+1)[-2:]}" for y in range(2012, 2025)]
        valid_tournament_years = ['2010', '2014', '2018', '2022']

        df_apps_target = df_apps_target[
            ((df_apps_target['competition_id'] != 'FIWC') & (df_apps_target['edition'].isin(valid_seasons))) |
            ((df_apps_target['competition_id'] == 'FIWC') & (df_apps_target['edition'].isin(valid_tournament_years)))
        ].copy()

        # Merge with club names
        df_apps_target = pd.merge(
            df_apps_target,
            df_clubs_raw[['club_id', 'name']],
            left_on='player_club_id',
            right_on='club_id',
            how='left'
        )
        df_apps_target.rename(columns={'name': 'club_name'}, inplace=True)
        df_apps_target['club_name'] = df_apps_target['club_name'].apply(clean_club_name)

        # Merge with players for nationality
        df_apps_target = pd.merge(
            df_apps_target,
            df[['player_id', 'country_of_citizenship']],
            on='player_id',
            how='left'
        )
        df_apps_target['country_of_citizenship'] = df_apps_target['country_of_citizenship'].fillna('')

        def get_primary_club(x):
            valid = [item for item in x if pd.notna(item) and item != '']
            if not valid:
                return ''
            return Counter(valid).most_common(1)[0][0]

        # Aggregate goals, appearances, and primary club per player per competition edition
        player_edition_stats = df_apps_target.groupby(['competition_id', 'edition', 'player_id', 'player_name', 'country_of_citizenship']).agg(
            goals=('goals', 'sum'),
            appearances=('appearance_id', 'count'),
            club_name=('club_name', get_primary_club)
        ).reset_index()

        # Build list of all available competition x edition combinations
        combinations = []
        comp_edition_groups = player_edition_stats.groupby(['competition_id', 'edition']).groups.keys()
        for comp_id, edition in comp_edition_groups:
            league_name = target_comps_map[comp_id]
            combinations.append((comp_id, league_name, edition))

        # Deterministically shuffle combinations across 180 days
        random.seed(88)
        shuffled_combos = combinations.copy()
        random.shuffle(shuffled_combos)

        all_scorer_game_data = []
        for day in range(num_days):
            comp_id, league_name, edition = shuffled_combos[day % len(shuffled_combos)]
            
            edition_scorers = player_edition_stats[
                (player_edition_stats['competition_id'] == comp_id) &
                (player_edition_stats['edition'] == edition)
            ].copy()

            top_scorers = edition_scorers.sort_values(by='goals', ascending=False).head(10)
            top_scorers['game_day'] = day + 1
            top_scorers['selected_target'] = f"{league_name} {edition}"

            all_scorer_game_data.append(top_scorers[['game_day', 'selected_target', 'player_name', 'club_name', 'goals', 'appearances', 'country_of_citizenship']])

        scorers_df = pd.concat(all_scorer_game_data, ignore_index=True)
        scorers_df.rename(columns={'country_of_citizenship': 'nationality'}, inplace=True)
        scorers_df.to_csv('daily_scorers_games.csv', index=False)
        print(f"Successfully generated top scorers game data ({len(combinations)} competition editions) and saved to 'daily_scorers_games.csv'")
    else:
        print("  WARNING: appearances.csv, clubs.csv, or games.csv not found. Skipping top scorers generation.")

    # --- 5. Generating Autocomplete Club List ---
    print("Generating autocomplete club list...")
    clubs_file = os.path.join(path, 'clubs.csv')
    df_clubs_csv = pd.read_csv(clubs_file) if os.path.exists(clubs_file) else pd.DataFrame()

    from_clubs = set(df_transfers['from_club_name'].dropna().apply(clean_club_name).unique())
    to_clubs = set(df_transfers['to_club_name'].dropna().apply(clean_club_name).unique())
    csv_clubs = set(df_clubs_csv['name'].dropna().apply(clean_club_name).unique()) if not df_clubs_csv.empty else set()
    cleaned_careers = set([clean_club_name(c) for c in clubs_in_careers if c])

    raw_clubs = cleaned_careers | from_clubs | to_clubs | csv_clubs
    all_autocomplete_clubs = sorted(list(set(clean_club_name(c) for c in raw_clubs if c)))

    with open('all_clubs.json', 'w', encoding='utf-8') as f_clubs:
        json.dump(all_autocomplete_clubs, f_clubs, ensure_ascii=False, indent=2)
    print(f"Successfully generated autocomplete club list with {len(all_autocomplete_clubs)} clubs in 'all_clubs.json'")

if __name__ == '__main__':
    main()

