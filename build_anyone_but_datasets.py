#!/usr/bin/env python3
"""
build_anyone_but_datasets.py — Generate & enrich daily Anyone But puzzles for Playmaker.

Each puzzle features an iconic EXCLUDED PLAYER and 3 tables of criteria.
Players must guess anyone who fits each criterion — EXCEPT the excluded player.

Output: daily_anyone_but_games.csv  (3 rows per game_day, 180 game_days)

Criterion types:
  nat_club   – "{Nationality adj.} who played for {club}"
  club_club  – "Played for BOTH {club_a} & {club_b}"
  club_value – "Played for {club} (peak market value ≥ €{n}M)"
  nat_goals  – "{Nationality adj.} with {n}+ career goals"

Holistic architecture:
  - Uses .player_career_db.pkl (Davidcariboo + Salimt + historical_careers.json + manual legends)
  - Answers are strictly whitelisted against all_players.json (ensuring UI autocomplete parity)
  - NO peak market value floor for answer player eligibility
  - Merges historical career goals from Davidcariboo and Salimt
"""

import os
import sys
import json
import csv
import re
import random
import itertools
from collections import defaultdict

import pandas as pd

# Flush prints immediately
sys.stdout.reconfigure(line_buffering=True)

# Reuse the canonical club-name normaliser & db builder from build_player_chain_datasets
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT_DIR)
from build_player_chain_datasets import clean_club_name, build_player_career_database


# ── Tuning constants ─────────────────────────────────────────────────────

SEED              = 42
TARGET_PUZZLES    = 180
MIN_ANSWERS       = 3       # per column
MAX_ANSWERS       = 15      # per column (comfortably accommodates rich pairs like Barca & Juve)
MIN_TOTAL_UNIQUE  = 8       # across all 3 columns
MAX_TOTAL_UNIQUE  = 25
MIN_EXCLUDED_VAL  = 30_000_000   # excluded player peak value floor
MIN_MAJOR_CLUBS   = 2            # excluded player must have ≥2 major clubs

VALUE_THRESHOLDS  = [30_000_000, 50_000_000, 80_000_000, 100_000_000]
GOAL_THRESHOLDS   = [50, 75, 100, 150, 200]


# ── Nationality adjective map ────────────────────────────────────────────

NAT_ADJ = {
    'Argentina': 'Argentinian', 'Brazil': 'Brazilian', 'France': 'French',
    'Germany': 'German', 'Spain': 'Spanish', 'Portugal': 'Portuguese',
    'Italy': 'Italian', 'England': 'English', 'Netherlands': 'Dutch',
    'Belgium': 'Belgian', 'Uruguay': 'Uruguayan', 'Colombia': 'Colombian',
    'Croatia': 'Croatian', 'Poland': 'Polish', 'Denmark': 'Danish',
    'Sweden': 'Swedish', 'Serbia': 'Serbian', 'Switzerland': 'Swiss',
    'Senegal': 'Senegalese', 'Nigeria': 'Nigerian', 'Cameroon': 'Cameroonian',
    'Ghana': 'Ghanaian', "Cote d'Ivoire": 'Ivorian', 'Ivory Coast': 'Ivorian',
    'Morocco': 'Moroccan', 'Algeria': 'Algerian', 'Egypt': 'Egyptian',
    'Japan': 'Japanese', 'South Korea': 'South Korean',
    'Korea, South': 'South Korean',
    'Mexico': 'Mexican', 'United States': 'American', 'Chile': 'Chilean',
    'Paraguay': 'Paraguayan', 'Ecuador': 'Ecuadorian',
    'Wales': 'Welsh', 'Scotland': 'Scottish', 'Ireland': 'Irish',
    'Republic of Ireland': 'Irish', 'Northern Ireland': 'Northern Irish',
    'Norway': 'Norwegian', 'Czech Republic': 'Czech', 'Austria': 'Austrian',
    'Turkey': 'Turkish', 'Greece': 'Greek', 'Romania': 'Romanian',
    'Hungary': 'Hungarian', 'Bosnia-Herzegovina': 'Bosnian',
    'North Macedonia': 'Macedonian', 'Slovakia': 'Slovak',
    'Slovenia': 'Slovenian', 'Finland': 'Finnish', 'Iceland': 'Icelandic',
    'Australia': 'Australian', 'Costa Rica': 'Costa Rican',
    'Jamaica': 'Jamaican', 'Peru': 'Peruvian', 'Venezuela': 'Venezuelan',
    'Tunisia': 'Tunisian', 'Mali': 'Malian', 'Guinea': 'Guinean',
    'Gabon': 'Gabonese', 'DR Congo': 'Congolese', 'Congo DR': 'Congolese',
    'Cape Verde': 'Cape Verdean', 'Burkina Faso': 'Burkinabé',
    'South Africa': 'South African', 'Saudi Arabia': 'Saudi',
    'Iran': 'Iranian', 'China': 'Chinese',
}

ADJ_TO_NAT = {v: k for k, v in NAT_ADJ.items()}


# ── Major clubs (canonical names matching club_to_entities) ──────────────

RAW_MAJOR_CLUBS = {
    # England
    'Arsenal', 'Aston Villa', 'Chelsea', 'Everton', 'Leeds United',
    'Leicester City', 'Liverpool', 'Manchester City', 'Manchester United',
    'Newcastle United', 'Southampton', 'Tottenham Hotspur', 'West Ham United',
    # Spain
    'Atletico Madrid', 'Barcelona', 'Real Betis', 'Real Madrid',
    'Real Sociedad', 'Sevilla', 'Valencia', 'Villarreal', 'Athletic Bilbao',
    # Germany
    'Bayer Leverkusen', 'Bayern Munich', 'Borussia Dortmund',
    'RB Leipzig', 'Schalke', 'VfL Wolfsburg', 'Eintracht Frankfurt',
    # Italy
    'AC Milan', 'Fiorentina', 'Roma', 'Atalanta',
    'Inter', 'Juventus', 'Lazio', 'Napoli',
    # France
    'Monaco', 'Lille', 'Lyon', 'Marseille',
    'Paris Saint-Germain',
    # Portugal / Netherlands / Belgium
    'Ajax', 'Anderlecht', 'Benfica', 'Club Brugge', 'Porto',
    'Feyenoord', 'PSV Eindhoven', 'Sporting CP',
    # Other Europe
    'Besiktas', 'Celtic', 'Dynamo Kyiv', 'Fenerbahce', 'Galatasaray',
    'Rangers', 'Red Bull Salzburg', 'Shakhtar Donetsk',
    'Zenit St. Petersburg',
    # South America
    'Boca Juniors', 'Corinthians', 'Flamengo', 'Gremio',
    'Internacional', 'Palmeiras', 'River Plate', 'Santos FC',
    'Sao Paulo FC',
    # Rest of world
    'Al-Hilal', 'Al-Nassr', 'Inter Miami', 'LA Galaxy',
}

MAJOR_CLUBS = {clean_club_name(c) or c for c in RAW_MAJOR_CLUBS}


# ── Data loading ─────────────────────────────────────────────────────────

def load_career_database():
    """Load unified career database (.player_career_db.pkl)."""
    cache_path = os.path.join(ROOT_DIR, '.player_career_db.pkl')
    if os.path.exists(cache_path):
        import pickle
        with open(cache_path, 'rb') as f:
            data = pickle.load(f)
            print(f"Loaded career database from {cache_path}")
            return data
    print("Building career database via build_player_career_database()...")
    return build_player_career_database()


def load_player_whitelist():
    """Load all_players.json whitelist mapping canonical name -> dict."""
    whitelist_file = os.path.join(ROOT_DIR, 'all_players.json')
    with open(whitelist_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    players = {}
    for p in data:
        name = p.get('Name')
        if not name:
            continue
        if name not in players or p.get('MarketValue', 0) > players[name].get('MarketValue', 0):
            players[name] = {
                'name': name,
                'nationality': p.get('Nationality', ''),
                'position': p.get('Position', ''),
                'market_value': float(p.get('MarketValue', 0)),
            }
    print(f"Loaded {len(players)} players from {whitelist_file}")
    return players


def load_dc_market_values(whitelist):
    """Augment with Transfermarkt peak values from Davidcariboo for value criteria."""
    dc_dir = os.path.expanduser('~/.cache/kagglehub/datasets/davidcariboo/player-scores/versions')
    if os.path.exists(dc_dir):
        versions = sorted([v for v in os.listdir(dc_dir) if v.isdigit()], key=int)
        dc_path = os.path.join(dc_dir, versions[-1]) if versions else os.path.join(dc_dir, '679')
    else:
        dc_path = os.path.join(dc_dir, '679')

    p_file = os.path.join(dc_path, 'players.csv')
    if not os.path.exists(p_file):
        return {}

    df = pd.read_csv(p_file, usecols=['name', 'highest_market_value_in_eur'], low_memory=False)
    dc_mv = {}
    for r in df.itertuples(index=False):
        if pd.isna(r.name) or pd.isna(r.highest_market_value_in_eur):
            continue
        clean_name = re.sub(r'\s*\(\d+\)$', '', str(r.name)).strip()
        val = float(r.highest_market_value_in_eur)
        if clean_name in whitelist:
            dc_mv[clean_name] = max(dc_mv.get(clean_name, 0.0), val)
    return dc_mv


def load_career_goals(whitelist):
    """Aggregate career goals combining Davidcariboo and Salimt historical performances."""
    player_goals = defaultdict(int)

    # 1. Davidcariboo appearances
    dc_dir = os.path.expanduser('~/.cache/kagglehub/datasets/davidcariboo/player-scores/versions')
    if os.path.exists(dc_dir):
        versions = sorted([v for v in os.listdir(dc_dir) if v.isdigit()], key=int)
        dc_path = os.path.join(dc_dir, versions[-1]) if versions else os.path.join(dc_dir, '679')
        p_file = os.path.join(dc_path, 'players.csv')
        app_file = os.path.join(dc_path, 'appearances.csv')
        if os.path.exists(p_file) and os.path.exists(app_file):
            df_p = pd.read_csv(p_file, usecols=['player_id', 'name'], low_memory=False)
            df_p['clean_name'] = df_p['name'].fillna('').astype(str).str.replace(r'\s*\(\d+\)$', '', regex=True).str.strip()
            dc_id_to_name = dict(zip(df_p['player_id'], df_p['clean_name']))

            df_app = pd.read_csv(app_file, usecols=['player_id', 'goals'], low_memory=False)
            dc_sum = df_app.groupby('player_id')['goals'].sum().to_dict()
            for pid, g in dc_sum.items():
                name = dc_id_to_name.get(pid)
                if name and name in whitelist:
                    player_goals[name] = max(player_goals[name], int(g))

    # 2. Salimt performances (covers 102 seasons back to 1990s & 2000s)
    salimt_dir = os.path.expanduser('~/.cache/kagglehub/datasets/xfkzujqjvx97n/football-datasets/versions')
    if os.path.exists(salimt_dir):
        versions = sorted([v for v in os.listdir(salimt_dir) if v.isdigit()], key=int)
        salimt_path = os.path.join(salimt_dir, versions[-1]) if versions else os.path.join(salimt_dir, '2')
        prof_file = os.path.join(salimt_path, 'player_profiles', 'player_profiles.csv')
        perf_file = os.path.join(salimt_path, 'player_performances', 'player_performances.csv')
        if os.path.exists(prof_file) and os.path.exists(perf_file):
            df_prof = pd.read_csv(prof_file, usecols=['player_id', 'player_name'], low_memory=False)
            df_prof['clean_name'] = df_prof['player_name'].fillna('').astype(str).str.replace(r'\s*\(\d+\)$', '', regex=True).str.strip()
            s_id_to_name = dict(zip(df_prof['player_id'], df_prof['clean_name']))

            df_perf = pd.read_csv(perf_file, usecols=['player_id', 'goals'], low_memory=False)
            s_sum = df_perf.groupby('player_id')['goals'].sum().to_dict()
            for pid, g in s_sum.items():
                name = s_id_to_name.get(pid)
                if name and name in whitelist:
                    player_goals[name] = max(player_goals[name], int(g))

    print(f"Aggregated career goals for {len(player_goals)} players")
    return player_goals


# ── Fast Inverted Indexes ────────────────────────────────────────────────

class PlayerIndex:
    def __init__(self, players, p_clubs, club_to_entities, entity_name, entity_clubs, player_goals, dc_market_values=None):
        self.players = players
        self.p_clubs = p_clubs
        self.club_to_entities = club_to_entities
        self.entity_name = entity_name
        self.entity_clubs = entity_clubs
        self.player_goals = player_goals
        self.dc_mv = dc_market_values or {}

        # Eligible answers: all players in whitelist (NO peak market value floor!)
        self.eligible_answers = set(players.keys())

        # club -> set of entity_ids
        self.club_entities = defaultdict(set)
        for club, eids in club_to_entities.items():
            for eid in eids:
                pname = entity_name.get(eid)
                if pname and pname in self.eligible_answers:
                    self.club_entities[club].add(eid)

        # nationality -> set of player names
        self.nat_players = defaultdict(set)
        for name, m in players.items():
            nat = m.get('nationality')
            if nat:
                self.nat_players[nat].add(name)

        # (club, thresh) -> set of player names
        self.club_thresh_players = defaultdict(set)
        for club, eids in self.club_entities.items():
            for t in VALUE_THRESHOLDS:
                self.club_thresh_players[(club, t)] = {
                    entity_name[eid] for eid in eids
                    if self.get_player_peak_value(entity_name[eid]) >= t
                }

        # (nat, thresh) -> set of player names
        self.nat_goals_players = defaultdict(set)
        for nat, names in self.nat_players.items():
            for t in GOAL_THRESHOLDS:
                self.nat_goals_players[(nat, t)] = {
                    name for name in names if self.player_goals.get(name, 0) >= t
                }

    def get_player_peak_value(self, name):
        """Returns player's peak market value in EUR."""
        return max(self.dc_mv.get(name, 0.0), self.players.get(name, {}).get('market_value', 0.0))

    def crit_nat_club(self, nat, club, xname):
        label = f"{NAT_ADJ.get(nat, nat)} who played for {club}"
        eids = self.club_entities.get(club, set())
        ans = {
            self.entity_name[e] for e in eids
            if self.players.get(self.entity_name[e], {}).get('nationality') == nat and self.entity_name[e] != xname
        }
        return label, ans

    def crit_club_club(self, ca, cb, xname):
        label = f"Played for BOTH {ca} & {cb}"
        both_eids = self.club_entities.get(ca, set()) & self.club_entities.get(cb, set())
        ans = {self.entity_name[e] for e in both_eids if self.entity_name[e] != xname}
        return label, ans

    def crit_club_value(self, club, thresh, xname):
        label = f"Played for {club} (peak market value ≥ €{thresh // 1_000_000}M)"
        ans = self.club_thresh_players.get((club, thresh), set()) - {xname}
        return label, ans

    def crit_nat_goals(self, nat, thresh, xname):
        label = f"{NAT_ADJ.get(nat, nat)} with {thresh}+ career goals"
        ans = self.nat_goals_players.get((nat, thresh), set()) - {xname}
        return label, ans


# ── Puzzle generation ────────────────────────────────────────────────────

def _all_criteria(pname, players, pc, pg, index):
    """Generate every valid criterion (3–15 answers) for an excluded player."""
    m      = players[pname]
    clubs  = pc.get(pname, set())
    nat    = m.get('nationality', '')
    majors = sorted(clubs & MAJOR_CLUBS)
    out    = []

    # 1. nat_club
    if nat:
        for club in majors:
            lbl, ans = index.crit_nat_club(nat, club, pname)
            if MIN_ANSWERS <= len(ans) <= MAX_ANSWERS:
                out.append(('nat_club', lbl, ans))

    # 2. club_club
    for i, ca in enumerate(majors):
        for cb in majors[i + 1:]:
            lbl, ans = index.crit_club_club(ca, cb, pname)
            if MIN_ANSWERS <= len(ans) <= MAX_ANSWERS:
                out.append(('club_club', lbl, ans))

    # 3. club_value
    for club in majors:
        for t in VALUE_THRESHOLDS:
            if index.get_player_peak_value(pname) >= t:
                lbl, ans = index.crit_club_value(club, t, pname)
                if MIN_ANSWERS <= len(ans) <= MAX_ANSWERS:
                    out.append(('club_value', lbl, ans))

    # 4. nat_goals
    if nat:
        for t in GOAL_THRESHOLDS:
            if pg.get(pname, 0) >= t:
                lbl, ans = index.crit_nat_goals(nat, t, pname)
                if MIN_ANSWERS <= len(ans) <= MAX_ANSWERS:
                    out.append(('nat_goals', lbl, ans))

    return out


def _score_combo(c1, c2, c3):
    """Higher = better puzzle. Returns −999 for invalid combos."""
    t1, _, a1 = c1
    t2, _, a2 = c2
    t3, _, a3 = c3

    union = a1 | a2 | a3
    total = len(union)
    if total < MIN_TOTAL_UNIQUE or total > MAX_TOTAL_UNIQUE:
        return -999

    # Reject near-identical columns (Jaccard > 0.7)
    for x, y in [(a1, a2), (a1, a3), (a2, a3)]:
        u = len(x | y)
        if u and len(x & y) / u > 0.7:
            return -999

    types = len({t1, t2, t3})
    score = types * 5
    sizes = sorted([len(a1), len(a2), len(a3)])
    score -= (sizes[2] - sizes[0])
    xovers = sum(1 for p in union if sum(p in s for s in [a1, a2, a3]) >= 2)
    score += min(xovers, 4) * 2
    score += total

    return score


def best_puzzle_for(pname, players, pc, pg, index):
    """Return the best (c1, c2, c3) tuple or None."""
    crits = _all_criteria(pname, players, pc, pg, index)
    if len(crits) < 3:
        return None

    combos = list(itertools.combinations(range(len(crits)), 3))
    if len(combos) > 400:
        random.Random(pname).shuffle(combos)
        combos = combos[:400]

    best, best_s = None, -999
    for i, j, k in combos:
        s = _score_combo(crits[i], crits[j], crits[k])
        if s > best_s:
            best_s, best = s, (crits[i], crits[j], crits[k])

    return best if best_s > -999 else None


# ── Tiered scheduling ────────────────────────────────────────────────────

def schedule(puzzles, rng):
    """Assign game_day 1–180 with weekly tier rotation."""
    t1 = [p for p in puzzles if p['val'] >= 90_000_000]
    t2 = [p for p in puzzles if 50_000_000 <= p['val'] < 90_000_000]
    t3 = [p for p in puzzles if p['val'] < 50_000_000]
    for tier in (t1, t2, t3):
        rng.shuffle(tier)
    print(f"  Tiers: T1(≥90M)={len(t1)}  T2(50-89M)={len(t2)}  T3(<50M)={len(t3)}")

    pattern = ['t1', 't2', 't3', 't2', 't1', 't3', 't2']
    iters   = {'t1': iter(t1), 't2': iter(t2), 't3': iter(t3)}

    out = []
    for day in range(1, TARGET_PUZZLES + 1):
        slot = pattern[(day - 1) % len(pattern)]
        p = next(iters[slot], None)
        if p is None:
            for fb in ('t2', 't3', 't1'):
                p = next(iters[fb], None)
                if p:
                    break
        if p is None:
            break
        p['game_day'] = day
        out.append(p)
    return out


# ── CSV writer ───────────────────────────────────────────────────────────

FIELDS = [
    'game_day', 'excluded_player', 'excluded_player_id',
    'table_number', 'total_tables', 'table_label',
    'answers', 'answer_count',
]


def write_csv(puzzles, path):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for p in puzzles:
            for idx, tbl in enumerate(p['tables'], 1):
                w.writerow({
                    'game_day':            p['game_day'],
                    'excluded_player':     p['excluded_player'],
                    'excluded_player_id':  p['excluded_player_id'],
                    'table_number':        idx,
                    'total_tables':        len(p['tables']),
                    'table_label':         tbl['label'],
                    'answers':             json.dumps(tbl['answers'], ensure_ascii=False),
                    'answer_count':        len(tbl['answers']),
                })


# ── Holistic Enrichment Engine ───────────────────────────────────────────

def enrich_dataset(csv_path="daily_anyone_but_games.csv"):
    """
    Enriches all 180 puzzles in daily_anyone_but_games.csv:
    - Merges complete career database into each table's answer pool
    - Backfills pre-2012 legends (Zambrotta, Henry, Thuram, Davids, etc.)
    - Removes peak market value floor for answer candidate eligibility
    - Preserves existing scheduled game days and excluded stars
    """
    if not os.path.exists(csv_path):
        print(f"Error: {csv_path} not found.")
        return False

    print(f"\n🔄 Running holistic Anyone But enrichment on {csv_path}...")
    p_clubs, player_meta, club_to_entities, entity_name, entity_clubs = load_career_database()
    players = load_player_whitelist()
    dc_mv = load_dc_market_values(players)
    player_goals = load_career_goals(players)
    index = PlayerIndex(players, p_clubs, club_to_entities, entity_name, entity_clubs, player_goals, dc_mv)

    with open(csv_path, 'r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    updated_rows = []
    total_added = 0

    for r in rows:
        lbl = r['table_label']
        excluded = r['excluded_player']
        cur_ans = set(json.loads(r['answers']))

        m_cc = re.match(r'^Played for BOTH (.+?) & (.+)$', lbl)
        m_nc = re.match(r'^(\w+)\s+who played for\s+(.+)$', lbl)
        m_ng = re.match(r'^(\w+)\s+with\s+(\d+)\+\s*career goals$', lbl)

        combined = set(cur_ans)

        if m_cc:
            ca = clean_club_name(m_cc.group(1).strip())
            cb = clean_club_name(m_cc.group(2).strip())
            _, valid = index.crit_club_club(ca, cb, excluded)
            combined |= valid
        elif m_nc:
            adj = m_nc.group(1).strip()
            club = clean_club_name(m_nc.group(2).strip())
            nat = ADJ_TO_NAT.get(adj)
            if nat:
                _, valid = index.crit_nat_club(nat, club, excluded)
                combined |= valid
        elif m_ng:
            adj = m_ng.group(1).strip()
            n = int(m_ng.group(2))
            nat = ADJ_TO_NAT.get(adj)
            if nat:
                for name, g in player_goals.items():
                    if g >= n and players.get(name, {}).get('nationality') == nat and name != excluded:
                        if len(p_clubs.get(name, set())) > 0 and len(combined) < 14:
                            combined.add(name)

        # Explicit legend additions for notable puzzles
        if r['game_day'] == '3':
            if r['table_number'] == '1':
                combined.add('Jonas Rouhi')
            elif r['table_number'] == '2':
                combined.update(['Gianluca Zambrotta', 'Thierry Henry', 'Lilian Thuram', 'Edgar Davids', 'Michael Laudrup'])
            elif r['table_number'] == '3':
                combined.add('Henrik Larsson')

        # Strictly exclude the puzzle's featured star
        combined.discard(excluded)

        added = len(combined) - len(cur_ans)
        total_added += added
        sorted_ans = sorted(combined)

        r['answers'] = json.dumps(sorted_ans, ensure_ascii=False)
        r['answer_count'] = str(len(sorted_ans))
        updated_rows.append(r)

    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(updated_rows)

    print(f"✅ Successfully enriched {len(updated_rows)} tables (+{total_added} missing answers restored)")
    return True


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)

    # By default, enrich existing dataset to preserve launched puzzles
    csv_path = os.path.join(base_dir, 'daily_anyone_but_games.csv')
    if os.path.exists(csv_path) and '--regenerate' not in sys.argv:
        enrich_dataset(csv_path)
        return

    # Full regeneration mode (only if --regenerate is passed)
    rng = random.Random(SEED)
    p_clubs, player_meta, club_to_entities, entity_name, entity_clubs = load_career_database()
    players = load_player_whitelist()
    dc_mv = load_dc_market_values(players)
    player_goals = load_career_goals(players)
    index = PlayerIndex(players, p_clubs, club_to_entities, entity_name, entity_clubs, player_goals, dc_mv)

    cands = sorted(
        (p for p, m in players.items()
         if index.get_player_peak_value(p) >= MIN_EXCLUDED_VAL
         and len(p_clubs.get(p, set()) & MAJOR_CLUBS) >= MIN_MAJOR_CLUBS
         and m['nationality'] in set(NAT_ADJ.keys())),
        key=lambda p: -index.get_player_peak_value(p),
    )
    print(f"Excluded-player candidates: {len(cands)}")

    puzzles = []
    used    = set()
    for pname in cands:
        if len(puzzles) >= TARGET_PUZZLES:
            break
        if pname in used:
            continue
        combo = best_puzzle_for(pname, players, p_clubs, player_goals, index)
        if combo is None:
            continue
        puzzles.append({
            'excluded_player':    pname,
            'excluded_player_id': 0,
            'val':                index.get_player_peak_value(pname),
            'tables': [
                {
                    'label':   c[1],
                    'answers': sorted(c[2]),
                }
                for c in combo
            ],
        })
        used.add(pname)

    scheduled = schedule(puzzles, rng)
    write_csv(scheduled, csv_path)
    print(f"Wrote {csv_path}")


if __name__ == '__main__':
    main()
