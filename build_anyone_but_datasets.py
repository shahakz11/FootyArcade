#!/usr/bin/env python3
"""
build_anyone_but_datasets.py — Generate daily Anyone But puzzles for Playmaker.

Each puzzle features an iconic EXCLUDED PLAYER and 3 tables of criteria.
Players must guess anyone who fits each criterion — EXCEPT the excluded player.

Output: daily_anyone_but_games.csv  (3 rows per game_day, 180 game_days)

Criterion types:
  nat_club   – "{Nationality adj.} who played for {club}"
  club_club  – "Played for BOTH {club_a} & {club_b}"
  club_value – "Played for {club} (peak market value ≥ €{n}M)"
  nat_goals  – "{Nationality adj.} with {n}+ career goals"
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

# Reuse the canonical club-name normaliser (same approach as build_passport_fc)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_player_chain_datasets import clean_club_name


# ── Tuning constants ─────────────────────────────────────────────────────

SEED              = 42
TARGET_PUZZLES    = 180
MIN_ANSWERS       = 3       # per column
MAX_ANSWERS       = 10      # per column
MIN_TOTAL_UNIQUE  = 8       # across all 3 columns
MAX_TOTAL_UNIQUE  = 20
MIN_EXCLUDED_VAL  = 30_000_000   # excluded player peak value floor
MIN_ANSWER_VAL    = 5_000_000    # answer player peak value floor
MIN_MAJOR_CLUBS   = 2            # excluded player must have ≥2 major clubs

VALUE_THRESHOLDS  = [30_000_000, 50_000_000, 80_000_000, 100_000_000]
GOAL_THRESHOLDS   = [30, 50, 75, 100, 150]


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


# ── Major clubs (canonical names after clean_club_name) ──────────────────

MAJOR_CLUBS = {
    # England
    'Arsenal', 'Aston Villa', 'Chelsea', 'Everton FC', 'Leeds United',
    'Leicester City', 'Liverpool', 'Manchester City', 'Manchester United',
    'Newcastle United', 'Southampton FC', 'Tottenham Hotspur', 'West Ham United',
    # Spain
    'Atletico Madrid', 'Barcelona', 'Real Betis', 'Real Madrid',
    'Real Sociedad', 'Sevilla FC', 'Valencia CF', 'Villarreal CF', 'Athletic Bilbao',
    # Germany
    'Bayer 04 Leverkusen', 'Bayern Munich', 'Borussia Dortmund',
    'RB Leipzig', 'Schalke 04', 'VfL Wolfsburg', 'Eintracht Frankfurt',
    # Italy
    'AC Milan', 'ACF Fiorentina', 'AS Roma', 'Atalanta BC',
    'Inter Milan', 'Juventus', 'Lazio', 'SSC Napoli',
    # France
    'AS Monaco', 'LOSC Lille', 'Olympique Lyon', 'Olympique Marseille',
    'Paris Saint-Germain',
    # Portugal / Netherlands / Belgium
    'Ajax', 'Anderlecht', 'Benfica', 'Club Brugge', 'FC Porto',
    'Feyenoord', 'PSV Eindhoven', 'Sporting CP',
    # Other Europe
    'Besiktas', 'Celtic FC', 'Dynamo Kyiv', 'Fenerbahce', 'Galatasaray',
    'Rangers FC', 'Red Bull Salzburg', 'Shakhtar Donetsk',
    'Zenit St. Petersburg',
    # South America
    'Boca Juniors', 'Corinthians', 'Flamengo', 'Gremio',
    'Internacional', 'Palmeiras', 'River Plate', 'Santos FC',
    'Sao Paulo FC',
    # Rest of world
    'Al-Hilal', 'Al-Nassr', 'Inter Miami', 'LA Galaxy',
}


# ── Data loading ─────────────────────────────────────────────────────────

def load_kaggle_dataset():
    """Load davidcariboo/player-scores from kagglehub or local cache."""
    try:
        import kagglehub
        dc_path = kagglehub.dataset_download('davidcariboo/player-scores')
    except Exception:
        dc_dir = os.path.expanduser(
            '~/.cache/kagglehub/datasets/davidcariboo/player-scores/versions')
        if os.path.exists(dc_dir):
            versions = sorted(
                [v for v in os.listdir(dc_dir) if v.isdigit()], key=int)
            dc_path = (os.path.join(dc_dir, versions[-1])
                       if versions else os.path.join(dc_dir, '679'))
        else:
            dc_path = os.path.join(dc_dir, '679')

    print(f"Loading player-scores from {dc_path}")
    players_df     = pd.read_csv(os.path.join(dc_path, 'players.csv'))
    transfers_df   = pd.read_csv(os.path.join(dc_path, 'transfers.csv'))
    appearances_df = pd.read_csv(os.path.join(dc_path, 'appearances.csv'))
    return players_df, transfers_df, appearances_df


def _load_salimt_transfers(player_clubs, valid_pids):
    """Optionally augment club histories with the Salimt supplementary dataset for known players."""
    salimt_dir = os.path.expanduser(
        '~/.cache/kagglehub/datasets/xfkzujqjvx97n/football-datasets/versions')
    if not os.path.exists(salimt_dir):
        return 0
    versions = sorted(
        [v for v in os.listdir(salimt_dir) if v.isdigit()], key=int)
    if not versions:
        return 0
    tr_file = os.path.join(salimt_dir, versions[-1],
                           'transfer_history', 'transfer_history.csv')
    if not os.path.exists(tr_file):
        return 0

    df = pd.read_csv(
        tr_file,
        usecols=['player_id', 'from_team_name', 'to_team_name'],
        low_memory=False,
    )
    # Only process rows for players we track
    df = df[df['player_id'].isin(valid_pids)]
    added = 0
    clean_memo = {}
    for r in df.itertuples(index=False):
        try:
            pid = int(r.player_id)
        except (ValueError, TypeError):
            continue
        for col_val in (r.from_team_name, r.to_team_name):
            if pd.notna(col_val):
                raw = str(col_val)
                if raw not in clean_memo:
                    cleaned = re.sub(r'\s*\(\d+\)$', '', raw).strip()
                    clean_memo[raw] = clean_club_name(cleaned)
                club = clean_memo[raw]
                if club:
                    player_clubs[pid].add(club)
                    added += 1
    return added


def build_player_data(players_df, transfers_df, appearances_df):
    """Build lookup dicts: players, player_clubs, player_goals."""
    players = {}
    for r in players_df[['player_id', 'name', 'country_of_citizenship', 'highest_market_value_in_eur']].itertuples(index=False):
        if pd.isna(r.name):
            continue
        pid  = int(r.player_id)
        name = str(r.name)
        nat  = str(r.country_of_citizenship) if pd.notna(r.country_of_citizenship) else ''
        val  = float(r.highest_market_value_in_eur) if pd.notna(r.highest_market_value_in_eur) else 0.0
        players[pid] = {'name': name, 'nationality': nat, 'market_value': val}

    player_clubs = defaultdict(set)
    clean_memo = {}
    for r in transfers_df[['player_id', 'from_club_name', 'to_club_name']].itertuples(index=False):
        pid = int(r.player_id)
        for col_val in (r.from_club_name, r.to_club_name):
            if pd.notna(col_val):
                raw = str(col_val)
                if raw not in clean_memo:
                    clean_memo[raw] = clean_club_name(raw)
                club = clean_memo[raw]
                if club:
                    player_clubs[pid].add(club)

    valid_pids = set(players.keys())
    salimt = _load_salimt_transfers(player_clubs, valid_pids)
    if salimt:
        print(f"  +{salimt} Salimt transfer records")

    # Vectorized career goals
    player_goals = appearances_df.groupby('player_id')['goals'].sum().fillna(0).astype(int).to_dict()

    print(f"  {len(players)} players | {len(player_clubs)} with clubs | {len(player_goals)} with goals")
    return players, dict(player_clubs), player_goals


# ── Fast Inverted Indexes ────────────────────────────────────────────────

class PlayerIndex:
    def __init__(self, players, pc, pg):
        self.players = players
        self.pc = pc
        self.pg = pg
        
        # Eligible answers set (peak value >= MIN_ANSWER_VAL)
        self.eligible_answers = {pid for pid, m in players.items() if m['market_value'] >= MIN_ANSWER_VAL}
        
        # club -> set of eligible pids
        self.club_players = defaultdict(set)
        for pid, clubs in pc.items():
            if pid in self.eligible_answers:
                for club in clubs:
                    self.club_players[club].add(pid)
                    
        # nationality -> set of eligible pids
        self.nat_players = defaultdict(set)
        for pid in self.eligible_answers:
            nat = players[pid]['nationality']
            if nat:
                self.nat_players[nat].add(pid)
                
        # (club, thresh) -> set of eligible pids
        self.club_thresh_players = defaultdict(set)
        for club, pids in self.club_players.items():
            for t in VALUE_THRESHOLDS:
                self.club_thresh_players[(club, t)] = {pid for pid in pids if players[pid]['market_value'] >= t}
                
        # (nat, thresh) -> set of eligible pids
        self.nat_goals_players = defaultdict(set)
        for nat, pids in self.nat_players.items():
            for t in GOAL_THRESHOLDS:
                self.nat_goals_players[(nat, t)] = {pid for pid in pids if pg.get(pid, 0) >= t}

    def crit_nat_club(self, nat, club, xpid):
        label = f"{NAT_ADJ.get(nat, nat)} who played for {club}"
        ans = (self.nat_players[nat] & self.club_players[club]) - {xpid}
        return label, ans

    def crit_club_club(self, ca, cb, xpid):
        label = f"Played for BOTH {ca} & {cb}"
        ans = (self.club_players[ca] & self.club_players[cb]) - {xpid}
        return label, ans

    def crit_club_value(self, club, thresh, xpid):
        label = f"Played for {club} (peak market value ≥ €{thresh // 1_000_000}M)"
        ans = self.club_thresh_players[(club, thresh)] - {xpid}
        return label, ans

    def crit_nat_goals(self, nat, thresh, xpid):
        label = f"{NAT_ADJ.get(nat, nat)} with {thresh}+ career goals"
        ans = self.nat_goals_players[(nat, thresh)] - {xpid}
        return label, ans


# ── Puzzle generation ────────────────────────────────────────────────────

def _all_criteria(pid, players, pc, pg, index):
    """Generate every valid criterion (3–10 answers) for an excluded player."""
    m      = players[pid]
    clubs  = pc.get(pid, set())
    nat    = m['nationality']
    majors = sorted(clubs & MAJOR_CLUBS)
    out    = []

    # 1. nat_club
    if nat:
        for club in majors:
            lbl, ans = index.crit_nat_club(nat, club, pid)
            if MIN_ANSWERS <= len(ans) <= MAX_ANSWERS:
                out.append(('nat_club', lbl, ans))

    # 2. club_club
    for i, ca in enumerate(majors):
        for cb in majors[i + 1:]:
            lbl, ans = index.crit_club_club(ca, cb, pid)
            if MIN_ANSWERS <= len(ans) <= MAX_ANSWERS:
                out.append(('club_club', lbl, ans))

    # 3. club_value
    for club in majors:
        for t in VALUE_THRESHOLDS:
            if m['market_value'] >= t:
                lbl, ans = index.crit_club_value(club, t, pid)
                if MIN_ANSWERS <= len(ans) <= MAX_ANSWERS:
                    out.append(('club_value', lbl, ans))

    # 4. nat_goals
    if nat:
        for t in GOAL_THRESHOLDS:
            if pg.get(pid, 0) >= t:
                lbl, ans = index.crit_nat_goals(nat, t, pid)
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

    # Diversity of criterion types
    types = len({t1, t2, t3})
    score = types * 5

    # Column-size balance (smaller gap = better)
    sizes = sorted([len(a1), len(a2), len(a3)])
    score -= (sizes[2] - sizes[0])

    # Crossover bonus (players in 2+ columns)
    xovers = sum(1 for p in union if sum(p in s for s in [a1, a2, a3]) >= 2)
    score += min(xovers, 4) * 2

    # Prefer moderate total unique
    score += total

    return score


def best_puzzle_for(pid, players, pc, pg, index):
    """Return the best (c1, c2, c3) tuple or None."""
    crits = _all_criteria(pid, players, pc, pg, index)
    if len(crits) < 3:
        return None

    combos = list(itertools.combinations(range(len(crits)), 3))
    if len(combos) > 400:
        random.Random(pid).shuffle(combos)
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


# ── Main ─────────────────────────────────────────────────────────────────

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(base_dir)
    rng = random.Random(SEED)

    # 1. Load data
    players_df, transfers_df, appearances_df = load_kaggle_dataset()
    players, pc, pg = build_player_data(players_df, transfers_df, appearances_df)

    # 2. Build indexed lookup
    print("Building fast lookup index...")
    index = PlayerIndex(players, pc, pg)
    print("Index ready.")

    # 3. Select candidates
    cands = sorted(
        (pid for pid, m in players.items()
         if m['market_value'] >= MIN_EXCLUDED_VAL
         and len(pc.get(pid, set()) & MAJOR_CLUBS) >= MIN_MAJOR_CLUBS
         and m['nationality'] in set(NAT_ADJ.keys())),
        key=lambda p: -players[p]['market_value'],
    )
    print(f"Excluded-player candidates: {len(cands)}")

    # 4. Generate puzzles
    puzzles = []
    used    = set()
    for pid in cands:
        if len(puzzles) >= TARGET_PUZZLES:
            break
        if pid in used:
            continue
        combo = best_puzzle_for(pid, players, pc, pg, index)
        if combo is None:
            continue
        puzzles.append({
            'excluded_player':    players[pid]['name'],
            'excluded_player_id': pid,
            'val':                players[pid]['market_value'],
            'tables': [
                {
                    'label':   c[1],
                    'answers': sorted(players[p]['name'] for p in c[2]),
                }
                for c in combo
            ],
        })
        used.add(pid)

    print(f"Generated {len(puzzles)} puzzles (target {TARGET_PUZZLES})")
    if len(puzzles) < TARGET_PUZZLES:
        print(f"  Warning: Only {len(puzzles)} generated. Relaxing search...")
        # Fallback to single major club if needed
        cands2 = sorted(
            (pid for pid, m in players.items()
             if m['market_value'] >= 25_000_000
             and len(pc.get(pid, set()) & MAJOR_CLUBS) >= 1
             and pid not in used
             and m['nationality'] in set(NAT_ADJ.keys())),
            key=lambda p: -players[p]['market_value'],
        )
        for pid in cands2:
            if len(puzzles) >= TARGET_PUZZLES:
                break
            combo = best_puzzle_for(pid, players, pc, pg, index)
            if combo is None:
                continue
            puzzles.append({
                'excluded_player':    players[pid]['name'],
                'excluded_player_id': pid,
                'val':                players[pid]['market_value'],
                'tables': [
                    {
                        'label':   c[1],
                        'answers': sorted(players[p]['name'] for p in c[2]),
                    }
                    for c in combo
                ],
            })
            used.add(pid)
        print(f"Total after expansion: {len(puzzles)}")

    # 5. Schedule
    scheduled = schedule(puzzles, rng)
    print(f"Scheduled {len(scheduled)} days")

    # 6. Write CSV
    out_path = os.path.join(base_dir, 'daily_anyone_but_games.csv')
    write_csv(scheduled, out_path)
    print(f"Wrote {out_path}")

    # 7. Sample verification
    print("\n" + "=" * 60)
    print("SAMPLE PUZZLES")
    print("=" * 60)
    for p in scheduled[:5]:
        total_a = sum(len(t['answers']) for t in p['tables'])
        unique  = len(set(a for t in p['tables'] for a in t['answers']))
        print(f"\nDay {p['game_day']}: ANYONE BUT {p['excluded_player']} "
              f"(€{p['val']/1e6:.0f}M | {total_a} total | {unique} unique)")
        for t in p['tables']:
            preview = ', '.join(t['answers'][:4])
            extra   = f" +{len(t['answers'])-4}" if len(t['answers']) > 4 else ''
            print(f"  [{len(t['answers']):>2}] {t['label']}")
            print(f"       {preview}{extra}")

    # Stats
    sizes = [len(t['answers']) for p in scheduled for t in p['tables']]
    print(f"\nColumn sizes: min={min(sizes)} max={max(sizes)} avg={sum(sizes)/len(sizes):.1f}")
    totals = [len(set(a for t in p['tables'] for a in t['answers'])) for p in scheduled]
    print(f"Unique/puzzle: min={min(totals)} max={max(totals)} avg={sum(totals)/len(totals):.1f}")


if __name__ == '__main__':
    main()
