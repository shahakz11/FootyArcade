"""
build_player_chain_datasets.py — Dataset generator for Player Chain
===================================================================
Generates 180 daily puzzles for the 'Player Chain' game mode.
Each puzzle features an iconic Mystery Player of the Day with an
expanding chain of club constraints, where every step has a precomputed
list of all valid players who satisfy all cumulative constraints.
"""

import os
import re
import json
import csv
import random
from collections import defaultdict
import pandas as pd

# Patterns to strip youth, reserves, corporate prefixes/suffixes from club names
PREFIX_PATTERN = re.compile(
    r'^(1\.\s*FC|1\.\s*FSV|1\.\s*|FC|CF|AC|AS|SS|SV|SC|SD|CD|UD|RC|RCD|FK|SK|BK|IF|IFK|OGC|US|USM|GC|AFC|SAD|CA|CE|CS|CP|VfB|VfL|TSG|BSC|FSV|SSV|SpVgg|Club)\s+',
    re.I
)
SUFFIX_PATTERN = re.compile(
    r'\s+(Football Club|Association Football Club|Club de Fútbol|Club de Futbol|Fútbol Club|Futbol Club|Soccer Club|Sports Club|Sport Club|Athletic Club|Club|FC|CF|SC|CSC|S\.A\.D\.|R\.C\.D\.|C\.D\.|F\.C\.|C\.F\.|AF|FK|SK|BK|SV|EV|e\.V\.|eV|AC|SD|UD|RC|SAD|Res|Reserves|Youth|Yth|Academy|Junioren|Castilla|II|B|U-?\d+|Sub-?\d+|Sub\s*\d+|Under-?\d+|Under\s*\d+)\b',
    re.I
)
YOUTH_PATTERNS = re.compile(
    r'(?i)U\d+|Sub-\d+|Sub\s+\d+|Youth|Yth|Academy|Junioren|Under-|Sub\s+1|Sub\s+2|Castilla|II\b|B\b'
)

ALIASES = {
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
    'Brescia Calcio': 'Brescia', 'Brescia': 'Brescia',
    'Bologna FC 1909': 'Bologna', 'Bologna': 'Bologna',
    'Udinese Calcio': 'Udinese', 'Udinese': 'Udinese',
    'Parma Calcio 1913': 'Parma', 'Parma FC': 'Parma', 'Parma': 'Parma',
    'LR Vicenza': 'Vicenza', 'Vicenza': 'Vicenza',
    'UC Sampdoria': 'Sampdoria', 'Sampdoria': 'Sampdoria',
    'Genoa CFC': 'Genoa', 'Genoa': 'Genoa',
    'Hellas Verona': 'Verona', 'Verona': 'Verona',

    # France
    'Paris SG': 'Paris Saint-Germain', 'PSG': 'Paris Saint-Germain', 'Paris Saint-Germain': 'Paris Saint-Germain',
    'Olympique Marseille': 'Marseille', 'Olympique de Marseille': 'Marseille', 'OM': 'Marseille', 'Marseille': 'Marseille',
    'Olympique Lyon': 'Lyon', 'Olympique Lyonnais': 'Lyon', 'OL': 'Lyon', 'Lyon': 'Lyon',
    'AS Monaco': 'Monaco', 'Monaco': 'Monaco',
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
    'Celtic FC': 'Celtic', 'Celtic': 'Celtic',
    'Rangers FC': 'Rangers', 'Rangers': 'Rangers',
    'Shakhtar Donetsk': 'Shakhtar Donetsk', 'Shakhtar D.': 'Shakhtar Donetsk', 'Shakhtar D': 'Shakhtar Donetsk',
    'Dynamo Kyiv': 'Dynamo Kyiv', 'Dynamo Kiev': 'Dynamo Kyiv',
    'RSC Anderlecht': 'Anderlecht', 'Anderlecht': 'Anderlecht',
    'Club Brugge KV': 'Club Brugge', 'Club Brugge': 'Club Brugge',
    'KRC Genk': 'Genk', 'Genk': 'Genk',
    'Red Bull Salzburg': 'Red Bull Salzburg', 'RB Salzburg': 'Red Bull Salzburg', 'Salzburg': 'Red Bull Salzburg',

    # Saudi / Rest of World
    'Al-Nassr': 'Al-Nassr', 'Al Nassr': 'Al-Nassr', 'Al-Nassr FC': 'Al-Nassr',
    'Al-Hilal': 'Al-Hilal', 'Al Hilal': 'Al-Hilal',
    'Al-Ittihad': 'Al-Ittihad', 'Al Ittihad': 'Al-Ittihad',
    'Al-Ahli': 'Al-Ahli', 'Al Ahli': 'Al-Ahli',
    'Inter Miami CF': 'Inter Miami', 'Inter Miami': 'Inter Miami',
    'Los Angeles Galaxy': 'LA Galaxy', 'LA Galaxy': 'LA Galaxy',
    'New York City FC': 'New York City', 'New York City': 'New York City',
}

def clean_club_name(val):
    if not isinstance(val, str):
        return ''
    val = val.strip().strip('.').strip('"').strip("'")
    if not val or YOUTH_PATTERNS.search(val):
        return ''
    if val in ALIASES:
        return ALIASES[val]

    cleaned = val
    cleaned = PREFIX_PATTERN.sub('', cleaned)
    cleaned = SUFFIX_PATTERN.sub('', cleaned)
    cleaned = PREFIX_PATTERN.sub('', cleaned)
    cleaned = SUFFIX_PATTERN.sub('', cleaned)
    cleaned = cleaned.strip().strip('.')

    if cleaned in ALIASES:
        return ALIASES[cleaned]

    if cleaned.startswith('Al ') and not cleaned.startswith('Al-'):
        cleaned = 'Al-' + cleaned[3:]

    return cleaned if cleaned else val


def build_player_career_database():
    """
    Combines Davidcariboo and Salimt datasets with all_players.json
    Returns (p_clubs, player_metadata)
    """
    print("Loading all_players.json...")
    with open('all_players.json', 'r', encoding='utf-8') as f:
        all_players = json.load(f)

    player_metadata = {}
    for p in all_players:
        player_metadata[p['Name']] = {
            'name': p['Name'],
            'nationality': p.get('Nationality', ''),
            'position': p.get('Position', '')
        }

    p_clubs = defaultdict(set)

    # 1. Davidcariboo transfers
    dc_path = os.path.expanduser('~/.cache/kagglehub/datasets/davidcariboo/player-scores/versions/671')
    if os.path.exists(dc_path):
        print("Reading Davidcariboo transfers...")
        df_dc_t = pd.read_csv(
            os.path.join(dc_path, 'transfers.csv'),
            usecols=['player_name', 'from_club_name', 'to_club_name'],
            low_memory=False
        )
        for _, r in df_dc_t.iterrows():
            name = str(r['player_name']).strip()
            if name and name != 'nan' and name in player_metadata:
                c1 = clean_club_name(str(r['from_club_name']))
                c2 = clean_club_name(str(r['to_club_name']))
                if c1: p_clubs[name].add(c1)
                if c2: p_clubs[name].add(c2)

    # 2. Salimt transfers
    salimt_path = os.path.expanduser('~/.cache/kagglehub/datasets/xfkzujqjvx97n/football-datasets/versions/2')
    if os.path.exists(salimt_path):
        print("Reading Salimt profiles & transfers...")
        p_prof = pd.read_csv(
            os.path.join(salimt_path, 'player_profiles', 'player_profiles.csv'),
            usecols=['player_id', 'player_name'],
            low_memory=False
        )
        p_prof['name'] = p_prof['player_name'].fillna('').astype(str).str.replace(r'\s*\(\d+\)$', '', regex=True)
        salimt_map = dict(zip(p_prof['player_id'], p_prof['name']))

        salimt_tr = pd.read_csv(
            os.path.join(salimt_path, 'transfer_history', 'transfer_history.csv'),
            usecols=['player_id', 'from_team_name', 'to_team_name'],
            low_memory=False
        )
        for _, r in salimt_tr.iterrows():
            pid = r['player_id']
            name = salimt_map.get(pid, '').strip()
            if name and name != 'nan' and name in player_metadata:
                c1 = clean_club_name(str(r['from_team_name']))
                c2 = clean_club_name(str(r['to_team_name']))
                if c1: p_clubs[name].add(c1)
                if c2: p_clubs[name].add(c2)

    # 3. Manual legendary career enrichments (for historical legends)
    manual_legends = {
        'Roberto Baggio': {
            'nationality': 'Italy',
            'position': 'Attack - Second Striker',
            'clubs': {'Vicenza', 'Fiorentina', 'Juventus', 'AC Milan', 'Bologna', 'Inter', 'Brescia'}
        },
        'Andrea Pirlo': {
            'nationality': 'Italy',
            'position': 'Midfield',
            'clubs': {'Brescia', 'Inter', 'Reggina', 'AC Milan', 'Juventus', 'New York City'}
        },
        'Zlatan Ibrahimović': {
            'nationality': 'Sweden',
            'position': 'Attack',
            'clubs': {'Malmö FF', 'Ajax', 'Juventus', 'Inter', 'Barcelona', 'AC Milan', 'Paris Saint-Germain', 'Manchester United', 'LA Galaxy'}
        },
        'Cristiano Ronaldo': {
            'nationality': 'Portugal',
            'position': 'Attack',
            'clubs': {'Sporting CP', 'Manchester United', 'Real Madrid', 'Juventus', 'Al-Nassr'}
        },
        'Lionel Messi': {
            'nationality': 'Argentina',
            'position': 'Attack',
            'clubs': {'Barcelona', 'Paris Saint-Germain', 'Inter Miami'}
        },
        'Álvaro Morata': {
            'nationality': 'Spain',
            'position': 'Attack',
            'clubs': {'Real Madrid', 'Juventus', 'Chelsea', 'Atletico Madrid', 'AC Milan'}
        },
        'Alexis Sánchez': {
            'nationality': 'Chile',
            'position': 'Attack',
            'clubs': {'Cobreloa', 'Udinese', 'Colo-Colo', 'River Plate', 'Barcelona', 'Arsenal', 'Manchester United', 'Inter', 'Marseille'}
        },
        'Cesc Fàbregas': {
            'nationality': 'Spain',
            'position': 'Midfield',
            'clubs': {'Arsenal', 'Barcelona', 'Chelsea', 'Monaco', 'Como'}
        },
        'Angel Di Maria': {
            'nationality': 'Argentina',
            'position': 'Attack',
            'clubs': {'Rosario Central', 'Benfica', 'Real Madrid', 'Manchester United', 'Paris Saint-Germain', 'Juventus'}
        },
        'Romelu Lukaku': {
            'nationality': 'Belgium',
            'position': 'Attack',
            'clubs': {'Anderlecht', 'Chelsea', 'West Bromwich Albion', 'Everton', 'Manchester United', 'Inter', 'Roma', 'Napoli'}
        },
        'Pierre-Emerick Aubameyang': {
            'nationality': 'Gabon',
            'position': 'Attack',
            'clubs': {'AC Milan', 'Dijon', 'Lille', 'Monaco', 'Saint-Étienne', 'Borussia Dortmund', 'Arsenal', 'Barcelona', 'Chelsea', 'Marseille', 'Al-Qadsiah'}
        },
        'Thiago Silva': {
            'nationality': 'Brazil',
            'position': 'Defender',
            'clubs': {'Fluminense', 'AC Milan', 'Paris Saint-Germain', 'Chelsea'}
        },
        'Luis Figo': {
            'nationality': 'Portugal',
            'position': 'Attack',
            'clubs': {'Sporting CP', 'Barcelona', 'Real Madrid', 'Inter'}
        },
        'Nicolas Anelka': {
            'nationality': 'France',
            'position': 'Attack',
            'clubs': {'Paris Saint-Germain', 'Arsenal', 'Real Madrid', 'Liverpool', 'Manchester City', 'Fenerbahce', 'Bolton Wanderers', 'Chelsea', 'Juventus'}
        },
        'Michael Owen': {
            'nationality': 'England',
            'position': 'Attack',
            'clubs': {'Liverpool', 'Real Madrid', 'Newcastle United', 'Manchester United', 'Stoke City'}
        },
        'Clarence Seedorf': {
            'nationality': 'Netherlands',
            'position': 'Midfield',
            'clubs': {'Ajax', 'Sampdoria', 'Real Madrid', 'Inter', 'AC Milan', 'Botafogo'}
        },
        'Ronaldo': {
            'nationality': 'Brazil',
            'position': 'Attack - Centre-Forward',
            'clubs': {'Cruzeiro', 'PSV Eindhoven', 'Barcelona', 'Inter', 'Real Madrid', 'AC Milan', 'Corinthians'}
        },
        'David Beckham': {
            'nationality': 'England',
            'position': 'Midfield',
            'clubs': {'Manchester United', 'Preston', 'Real Madrid', 'LA Galaxy', 'AC Milan', 'Paris Saint-Germain'}
        },
        'Thierry Henry': {
            'nationality': 'France',
            'position': 'Attack',
            'clubs': {'Monaco', 'Juventus', 'Arsenal', 'Barcelona', 'New York Red Bulls'}
        },
        'Gianluigi Buffon': {
            'nationality': 'Italy',
            'position': 'Goalkeeper',
            'clubs': {'Parma', 'Juventus', 'Paris Saint-Germain'}
        },
        'Xabi Alonso': {
            'nationality': 'Spain',
            'position': 'Midfield',
            'clubs': {'Real Sociedad', 'Eibar', 'Liverpool', 'Real Madrid', 'Bayern Munich'}
        },
        'Mesut Özil': {
            'nationality': 'Germany',
            'position': 'Midfield',
            'clubs': {'Schalke', 'Werder Bremen', 'Real Madrid', 'Arsenal', 'Fenerbahce', 'Basaksehir'}
        },
        'Dani Alves': {
            'nationality': 'Brazil',
            'position': 'Defender',
            'clubs': {'Bahia', 'Sevilla', 'Barcelona', 'Juventus', 'Paris Saint-Germain', 'São Paulo'}
        },
        'James Rodríguez': {
            'nationality': 'Colombia',
            'position': 'Attack',
            'clubs': {'Envigado', 'Banfield', 'Porto', 'Monaco', 'Real Madrid', 'Bayern Munich', 'Everton', 'Al-Rayyan', 'Olympiacos', 'São Paulo', 'Rayo Vallecano'}
        },
        'Memphis Depay': {
            'nationality': 'Netherlands',
            'position': 'Attack',
            'clubs': {'PSV Eindhoven', 'Manchester United', 'Lyon', 'Barcelona', 'Atletico Madrid', 'Corinthians'}
        },
        'Henrikh Mkhitaryan': {
            'nationality': 'Armenia',
            'position': 'Midfield',
            'clubs': {'Pyunik', 'Metalurh Donetsk', 'Shakhtar Donetsk', 'Borussia Dortmund', 'Manchester United', 'Arsenal', 'Roma', 'Inter'}
        },
        'Christian Pulisic': {
            'nationality': 'United States',
            'position': 'Attack',
            'clubs': {'Borussia Dortmund', 'Chelsea', 'AC Milan'}
        },
        'Karim Benzema': {
            'nationality': 'France',
            'position': 'Attack',
            'clubs': {'Lyon', 'Real Madrid', 'Al-Ittihad'}
        },
        'Robert Lewandowski': {
            'nationality': 'Poland',
            'position': 'Attack',
            'clubs': {'Znicz Pruszkow', 'Lech Poznan', 'Borussia Dortmund', 'Bayern Munich', 'Barcelona'}
        },
        'Erling Haaland': {
            'nationality': 'Norway',
            'position': 'Attack',
            'clubs': {'Bryne', 'Molde', 'Red Bull Salzburg', 'Borussia Dortmund', 'Manchester City'}
        },
        'Jude Bellingham': {
            'nationality': 'England',
            'position': 'Midfield',
            'clubs': {'Birmingham City', 'Borussia Dortmund', 'Real Madrid'}
        },
        'Eden Hazard': {
            'nationality': 'Belgium',
            'position': 'Attack',
            'clubs': {'Lille', 'Chelsea', 'Real Madrid'}
        },
        'Kevin De Bruyne': {
            'nationality': 'Belgium',
            'position': 'Midfield',
            'clubs': {'Genk', 'Chelsea', 'Werder Bremen', 'Wolfsburg', 'Manchester City'}
        },
        'Mohamed Salah': {
            'nationality': 'Egypt',
            'position': 'Attack',
            'clubs': {'El Mokawloon', 'Basel', 'Chelsea', 'Fiorentina', 'Roma', 'Liverpool'}
        },
        'Sadio Mané': {
            'nationality': 'Senegal',
            'position': 'Attack',
            'clubs': {'Metz', 'Red Bull Salzburg', 'Southampton', 'Liverpool', 'Bayern Munich', 'Al-Nassr'}
        },
        'Gareth Bale': {
            'nationality': 'Wales',
            'position': 'Attack',
            'clubs': {'Southampton', 'Tottenham Hotspur', 'Real Madrid', 'Los Angeles FC'}
        },
        'Luka Modrić': {
            'nationality': 'Croatia',
            'position': 'Midfield',
            'clubs': {'Dinamo Zagreb', 'Zrinjski Mostar', 'Inter Zapresic', 'Tottenham Hotspur', 'Real Madrid'}
        },
        'Toni Kroos': {
            'nationality': 'Germany',
            'position': 'Midfield',
            'clubs': {'Bayern Munich', 'Bayer Leverkusen', 'Real Madrid'}
        },
        'Gonzalo Higuaín': {
            'nationality': 'Argentina',
            'position': 'Attack',
            'clubs': {'River Plate', 'Real Madrid', 'Napoli', 'Juventus', 'AC Milan', 'Chelsea', 'Inter Miami'}
        },
    }

    for name, data in manual_legends.items():
        if name not in player_metadata:
            player_metadata[name] = {
                'name': name,
                'nationality': data.get('nationality', ''),
                'position': data.get('position', '')
            }
        else:
            if data.get('nationality'):
                player_metadata[name]['nationality'] = data['nationality']
            if data.get('position'):
                player_metadata[name]['position'] = data['position']

        for c in data.get('clubs', []):
            clean_c = clean_club_name(c)
            if clean_c:
                p_clubs[name].add(clean_c)

    print(f"Total mapped players: {len(p_clubs)}")
    return p_clubs, player_metadata


def generate_puzzles(p_clubs, player_metadata, total_puzzles=180):
    """
    Generates 180 puzzles with iconic target players and expanding constraints.
    Returns list of dicts for CSV export.
    """
    print("Selecting target players and designing chains...")

    # Load destination players to use as primary star candidates
    df_dest = pd.read_csv('daily_destination_games.csv')
    dest_stars = list(dict.fromkeys(df_dest['player_name'].tolist()))

    # Curate primary target players starting with Day 1: Roberto Baggio!
    priority_stars = [
        'Roberto Baggio',
        'Zlatan Ibrahimović',
        'Cristiano Ronaldo',
        'Andrea Pirlo',
        'Álvaro Morata',
        'Alexis Sánchez',
        'Cesc Fàbregas',
        'Angel Di Maria',
        'Romelu Lukaku',
        'Pierre-Emerick Aubameyang',
        'Thiago Silva',
        'Luis Figo',
        'Nicolas Anelka',
        'Michael Owen',
        'Clarence Seedorf',
        'Ronaldo',
        'David Beckham',
        'Thierry Henry',
        'Gianluigi Buffon',
        'Xabi Alonso',
        'Mesut Özil',
        'Dani Alves',
        'James Rodríguez',
        'Memphis Depay',
        'Henrikh Mkhitaryan',
        'Christian Pulisic',
        'Karim Benzema',
        'Robert Lewandowski',
        'Erling Haaland',
        'Jude Bellingham',
        'Eden Hazard',
        'Kevin De Bruyne',
        'Mohamed Salah',
        'Sadio Mané',
        'Gareth Bale',
        'Luka Modrić',
        'Toni Kroos',
        'Gonzalo Higuaín',
    ]

    all_candidates = []
    seen = set()
    for s in priority_stars + dest_stars:
        if s not in seen and s in p_clubs and len(p_clubs[s]) >= 3:
            all_candidates.append(s)
            seen.add(s)

    # If more candidates needed, find high profile players with >= 3 clubs
    if len(all_candidates) < total_puzzles:
        for p, clubs in p_clubs.items():
            if p not in seen and len(clubs) >= 3:
                all_candidates.append(p)
                seen.add(p)
                if len(all_candidates) >= total_puzzles + 50:
                    break

    print(f"Candidate star pool size: {len(all_candidates)}")

    puzzle_rows = []
    puzzle_day = 1

    # Specific handcrafted sequences for famous superstars to make them exceptionally fun
    handcrafted = {
        'Roberto Baggio': ['AC Milan', 'Inter', 'Juventus', 'Bologna'],
        'Zlatan Ibrahimović': ['Ajax', 'Juventus', 'Inter', 'Barcelona'],
        'Cristiano Ronaldo': ['Sporting CP', 'Manchester United', 'Real Madrid', 'Juventus'],
        'Andrea Pirlo': ['Brescia', 'Inter', 'AC Milan', 'Juventus'],
        'Álvaro Morata': ['Real Madrid', 'Juventus', 'Chelsea', 'Atletico Madrid'],
        'Alexis Sánchez': ['Udinese', 'Barcelona', 'Arsenal', 'Inter'],
        'Cesc Fàbregas': ['Arsenal', 'Barcelona', 'Chelsea', 'Monaco'],
        'Angel Di Maria': ['Benfica', 'Real Madrid', 'Paris Saint-Germain', 'Juventus'],
        'Romelu Lukaku': ['Anderlecht', 'Chelsea', 'Everton', 'Inter'],
        'Pierre-Emerick Aubameyang': ['Saint-Étienne', 'Borussia Dortmund', 'Arsenal', 'Barcelona'],
        'Thiago Silva': ['Fluminense', 'AC Milan', 'Paris Saint-Germain', 'Chelsea'],
        'Luis Figo': ['Sporting CP', 'Barcelona', 'Real Madrid', 'Inter'],
        'Nicolas Anelka': ['Paris Saint-Germain', 'Arsenal', 'Real Madrid', 'Chelsea'],
        'Michael Owen': ['Liverpool', 'Real Madrid', 'Newcastle United', 'Manchester United'],
        'Clarence Seedorf': ['Ajax', 'Sampdoria', 'Real Madrid', 'Inter'],
        'Ronaldo': ['PSV Eindhoven', 'Barcelona', 'Inter', 'Real Madrid'],
        'David Beckham': ['Manchester United', 'Real Madrid', 'LA Galaxy', 'AC Milan'],
        'Thierry Henry': ['Monaco', 'Juventus', 'Arsenal', 'Barcelona'],
        'Gianluigi Buffon': ['Parma', 'Juventus', 'Paris Saint-Germain'],
        'Xabi Alonso': ['Real Sociedad', 'Liverpool', 'Real Madrid', 'Bayern Munich'],
        'Mesut Özil': ['Werder Bremen', 'Real Madrid', 'Arsenal', 'Fenerbahce'],
        'Dani Alves': ['Sevilla', 'Barcelona', 'Juventus', 'Paris Saint-Germain'],
        'James Rodríguez': ['Porto', 'Monaco', 'Real Madrid', 'Bayern Munich'],
        'Memphis Depay': ['PSV Eindhoven', 'Manchester United', 'Lyon', 'Barcelona'],
        'Henrikh Mkhitaryan': ['Shakhtar Donetsk', 'Borussia Dortmund', 'Manchester United', 'Arsenal'],
        'Christian Pulisic': ['Borussia Dortmund', 'Chelsea', 'AC Milan'],
        'Karim Benzema': ['Lyon', 'Real Madrid', 'Al-Ittihad'],
        'Robert Lewandowski': ['Lech Poznan', 'Borussia Dortmund', 'Bayern Munich', 'Barcelona'],
        'Erling Haaland': ['Molde', 'Red Bull Salzburg', 'Borussia Dortmund', 'Manchester City'],
        'Jude Bellingham': ['Birmingham City', 'Borussia Dortmund', 'Real Madrid'],
        'Eden Hazard': ['Lille', 'Chelsea', 'Real Madrid'],
        'Kevin De Bruyne': ['Genk', 'Chelsea', 'Wolfsburg', 'Manchester City'],
        'Mohamed Salah': ['Basel', 'Chelsea', 'Roma', 'Liverpool'],
        'Sadio Mané': ['Metz', 'Red Bull Salzburg', 'Southampton', 'Liverpool'],
        'Gareth Bale': ['Southampton', 'Tottenham Hotspur', 'Real Madrid'],
        'Luka Modrić': ['Dinamo Zagreb', 'Tottenham Hotspur', 'Real Madrid'],
        'Toni Kroos': ['Bayer Leverkusen', 'Bayern Munich', 'Real Madrid'],
        'Gonzalo Higuaín': ['River Plate', 'Real Madrid', 'Napoli', 'Juventus'],
    }

    # Helper to find valid players for a set of clubs
    def find_valid(club_set):
        matches = []
        for p_name, p_clubset in p_clubs.items():
            if p_name and p_name != 'nan' and club_set.issubset(p_clubset):
                matches.append(p_name)
        matches.sort()
        return matches

    for candidate in all_candidates:
        if puzzle_day > total_puzzles:
            break

        cand_clubs = list(p_clubs[candidate])
        if len(cand_clubs) < 2:
            continue

        selected_chain = None

        if candidate in handcrafted:
            seq = handcrafted[candidate]
            if all(c in p_clubs[candidate] for c in seq):
                selected_chain = seq

        if not selected_chain:
            # Pick 3 or 4 clubs that form a descending funnel of valid players
            clubs_to_try = cand_clubs[:6]
            best_chain = None
            best_score = -1

            chain_len = 4 if len(clubs_to_try) >= 4 else 3
            import itertools
            for comb in itertools.permutations(clubs_to_try, chain_len):
                valid_counts = []
                is_funnel = True
                curr_set = set()
                for c in comb:
                    curr_set.add(c)
                    cnt = len(find_valid(curr_set))
                    valid_counts.append(cnt)
                    if cnt == 0:
                        is_funnel = False
                        break

                if not is_funnel:
                    continue

                if valid_counts[0] >= 5 and valid_counts[-1] >= 1:
                    score = valid_counts[0] - valid_counts[-1]
                    if score > best_score:
                        best_score = score
                        best_chain = list(comb)

            selected_chain = best_chain

        if not selected_chain or len(selected_chain) < 2:
            continue

        # Verify each step has valid players and candidate is present
        steps_data = []
        cumulative_clubs = []
        cumulative_constraints = []
        valid_puzzle = True

        for step_idx, club in enumerate(selected_chain):
            cumulative_clubs.append(club)
            constraint_text = f"Played for {club}"
            cumulative_constraints.append(constraint_text)

            valid_for_step = find_valid(set(cumulative_clubs))
            if candidate not in valid_for_step or len(valid_for_step) == 0:
                valid_puzzle = False
                break

            steps_data.append({
                'step_number': step_idx + 1,
                'new_constraint': constraint_text,
                'club': club,
                'active_constraints': list(cumulative_constraints),
                'active_clubs': list(cumulative_clubs),
                'valid_players': valid_for_step
            })

        if not valid_puzzle or len(steps_data) < 2:
            continue

        meta = player_metadata.get(candidate, {})
        nat = meta.get('nationality', 'Unknown')
        pos = meta.get('position', 'Forward')
        total_steps = len(steps_data)

        for step in steps_data:
            puzzle_rows.append({
                'game_day': puzzle_day,
                'target_player': candidate,
                'target_nationality': nat,
                'target_position': pos,
                'total_steps': total_steps,
                'step_number': step['step_number'],
                'new_constraint': step['new_constraint'],
                'club': step['club'],
                'active_constraints': json.dumps(step['active_constraints'], ensure_ascii=False),
                'active_clubs': json.dumps(step['active_clubs'], ensure_ascii=False),
                'valid_players': json.dumps(step['valid_players'], ensure_ascii=False),
            })

        puzzle_day += 1

    print(f"Successfully generated {puzzle_day - 1} puzzles with {len(puzzle_rows)} total step records.")
    return puzzle_rows


def main():
    p_clubs, player_metadata = build_player_career_database()
    puzzle_rows = generate_puzzles(p_clubs, player_metadata, total_puzzles=180)

    out_file = 'daily_player_chain_games.csv'
    fieldnames = [
        'game_day',
        'target_player',
        'target_nationality',
        'target_position',
        'total_steps',
        'step_number',
        'new_constraint',
        'club',
        'active_constraints',
        'active_clubs',
        'valid_players',
    ]

    with open(out_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(puzzle_rows)

    print(f"Saved dataset to {out_file}.")


if __name__ == '__main__':
    main()
