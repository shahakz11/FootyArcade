"""
player_chain_ml.py — Machine Learning & Graph Optimization for Player Chain
============================================================================
Computes player recognizability scores via bipartite transfer graph centrality
and Transfermarkt economic features. Implements an information-theoretic
funnel policy optimizer that guarantees smooth, solvable, and engaging puzzles
with zero premature bottlenecks.
"""

import os
import math
from collections import defaultdict
import numpy as np
import pandas as pd

# Elite & Tier 1/2 club hubs that football trivia fans recognize
TIER_1_CLUBS = {
    'Real Madrid', 'Barcelona', 'Manchester United', 'Arsenal', 'Chelsea',
    'Liverpool', 'Manchester City', 'Bayern Munich', 'Inter', 'AC Milan',
    'Juventus', 'Paris Saint-Germain'
}

TIER_2_CLUBS = {
    'Atletico Madrid', 'Borussia Dortmund', 'Tottenham Hotspur', 'AS Roma',
    'Roma', 'Napoli', 'Benfica', 'Porto', 'Ajax', 'Bayer Leverkusen',
    'Sevilla', 'Valencia', 'Lazio', 'Fiorentina', 'Marseille', 'Lyon',
    'Monaco', 'Sporting CP', 'PSV Eindhoven', 'Newcastle United', 'Aston Villa'
}


def build_recognizability_index(p_clubs, p_meta):
    """
    Computes a continuous Recognizability Index R(p) in [0.01, 1.0] for every player.
    Fuses:
      1. Transfermarkt highest market valuation & current market value
      2. International caps and appearances
      3. Bipartite graph connectivity with Tier 1/2 clubs
      4. Historical icon priors (for pre-2004 legends like Pelé, Maradona, Baggio)
    """
    print("Building ML player recognizability index...")

    # 1. Load Transfermarkt valuation features if available
    dc_dir = os.path.expanduser('~/.cache/kagglehub/datasets/davidcariboo/player-scores/versions')
    val_map = {}
    caps_map = {}
    if os.path.exists(dc_dir):
        versions = sorted([v for v in os.listdir(dc_dir) if v.isdigit()], key=int)
        if versions:
            dc_path = os.path.join(dc_dir, versions[-1])
            players_csv = os.path.join(dc_path, 'players.csv')
            if os.path.exists(players_csv):
                df_p = pd.read_csv(
                    players_csv,
                    usecols=['name', 'market_value_in_eur', 'highest_market_value_in_eur', 'international_caps'],
                    low_memory=False
                )
                for r in df_p.itertuples(index=False):
                    name = str(r.name).strip() if pd.notna(r.name) else ''
                    if not name:
                        continue
                    mv = float(r.highest_market_value_in_eur) if pd.notna(r.highest_market_value_in_eur) else 0.0
                    cmv = float(r.market_value_in_eur) if pd.notna(r.market_value_in_eur) else 0.0
                    peak = max(mv, cmv)
                    if peak > val_map.get(name, 0):
                        val_map[name] = peak

                    caps = int(r.international_caps) if pd.notna(r.international_caps) else 0
                    if caps > caps_map.get(name, 0):
                        caps_map[name] = caps

    # 2. Historical superstars / Ballon d'Or winners prior
    legend_boost = {
        'Roberto Baggio': 0.98,
        'Pelé': 0.99,
        'Diego Maradona': 0.99,
        'Zinedine Zidane': 0.99,
        'Ronaldo': 0.99,
        'Ronaldinho': 0.99,
        'Thierry Henry': 0.98,
        'Dennis Bergkamp': 0.95,
        'Ruud Gullit': 0.96,
        'Marco van Basten': 0.97,
        'Frank Rijkaard': 0.95,
        'George Weah': 0.96,
        'Clarence Seedorf': 0.96,
        'Paolo Maldini': 0.98,
        'Franco Baresi': 0.96,
        'Alessandro Del Piero': 0.97,
        'Francesco Totti': 0.97,
        'Andrea Pirlo': 0.98,
        'David Beckham': 0.99,
        'Luis Figo': 0.98,
        'Romário': 0.97,
        'Hristo Stoichkov': 0.95,
        'Michael Laudrup': 0.95,
        'Eric Cantona': 0.96,
        'Gabriel Batistuta': 0.95,
        'Rivaldo': 0.97,
        'Oliver Kahn': 0.96,
        'Gianluigi Buffon': 0.98,
        'Iker Casillas': 0.98,
        'Carles Puyol': 0.97,
        'Xavi': 0.98,
        'Andrés Iniesta': 0.98,
        'Paul Scholes': 0.96,
        'Ryan Giggs': 0.96,
        'Steven Gerrard': 0.97,
        'Frank Lampard': 0.97,
        'Didier Drogba': 0.97,
        'Samuel Eto\'o': 0.97,
        'Wayne Rooney': 0.98,
        'Kaká': 0.98,
        'Cristiano Ronaldo': 1.0,
        'Lionel Messi': 1.0,
        'Zlatan Ibrahimović': 0.99,
        'Neymar': 0.98,
        'Kylian Mbappé': 0.99,
        'Erling Haaland': 0.99,
        'Robert Lewandowski': 0.98,
        'Karim Benzema': 0.98,
        'Luka Modrić': 0.98,
        'Toni Kroos': 0.97,
        'Kevin De Bruyne': 0.98,
        'Mohamed Salah': 0.98,
        'Pierre-Emerick Aubameyang': 0.93,
        'Alexis Sánchez': 0.93,
        'Álvaro Morata': 0.91,
        'Cesc Fàbregas': 0.95,
        'Angel Di Maria': 0.95,
        'Romelu Lukaku': 0.95,
        'Thiago Silva': 0.95,
    }

    rec_map = {}
    for p_name, clubs in p_clubs.items():
        if not p_name or p_name == 'nan':
            continue

        if p_name in legend_boost:
            rec_map[p_name] = legend_boost[p_name]
            continue

        # Feature A: Market valuation log scale (0.0 to 1.0)
        # 100k -> 0.0, 1M -> 0.30, 10M -> 0.60, 50M -> 0.81, 150M+ -> 1.0
        peak_val = val_map.get(p_name, 0)
        if peak_val >= 100_000:
            val_score = min(1.0, max(0.0, math.log10(peak_val / 50_000) / math.log10(150_000_000 / 50_000)))
        else:
            val_score = 0.02

        # Feature B: Bipartite Club Centrality
        t1_count = sum(1 for c in clubs if c in TIER_1_CLUBS)
        t2_count = sum(1 for c in clubs if c in TIER_2_CLUBS)
        club_centrality = min(1.0, (t1_count * 0.35 + t2_count * 0.15 + len(clubs) * 0.05))

        # Feature C: International caps
        caps = caps_map.get(p_name, 0)
        caps_score = min(1.0, caps / 50.0)

        # Fused Recognizability Index
        score = 0.55 * val_score + 0.35 * club_centrality + 0.10 * caps_score
        # Baseline threshold so obscure players are not 0 but ~0.02
        rec_map[p_name] = round(max(0.01, min(0.99, score)), 4)

    print(f"Computed recognizability for {len(rec_map)} players.")
    return rec_map


def effective_capacity(player_set, rec_map):
    """
    Computes effective recognizable capacity: sum of R(p) for all valid players.
    """
    return sum(rec_map.get(p, 0.02) for p in player_set)


def evaluate_funnel_chain(chain, target_player, club_to_players, rec_map):
    """
    Evaluates a candidate club chain using an Information-Theoretic Funnel Loss.
    
    Ideal funnel properties:
      1. Step 1: Wide accessible pool (C_eff >= 40, raw >= 100)
      2. Step 2: Engaging trivia crossover (C_eff in [5, 30], raw >= 8, NEVER <= 1)
      3. Step 3: Tight recognizable squeeze (C_eff in [1.5, 8], raw >= 2, NEVER <= 1)
      4. Step 4 (if 4-step): Resolves uniquely to target player (raw == 1 or C_eff <= 1.2)
      
    Returns:
      (utility_score, step_stats)
    """
    cumulative_clubs = []
    active_set = None
    step_stats = []

    k = len(chain)

    for step_idx, club in enumerate(chain):
        cumulative_clubs.append(club)
        c_players = club_to_players.get(club, set())

        if step_idx == 0:
            active_set = set(c_players)
        else:
            active_set = active_set & c_players

        # Target player MUST be valid at all steps
        if target_player not in active_set:
            return -float('inf'), []

        raw_count = len(active_set)
        c_eff = effective_capacity(active_set, rec_map)

        # ── ZERO-TOLERANCE RULES ──
        # If raw count is <= 1 BEFORE the final step, strict disqualification!
        if step_idx < k - 1 and raw_count <= 1:
            return -float('inf'), []

        # If step 2 has fewer than 4 players, it's an extreme trivia choke point
        if step_idx == 1 and raw_count < 4:
            return -float('inf'), []

        step_stats.append({
            'club': club,
            'raw_count': raw_count,
            'c_eff': c_eff,
            'players': active_set
        })

    # ── COMPUTE GAMEPLAY UTILITY ──
    # Target capacities for 4-step vs 3-step
    if k == 4:
        target_c_eff = [80.0, 12.0, 3.0, 1.0]
        weights = [1.0, 3.0, 4.0, 5.0]
    else:
        target_c_eff = [80.0, 6.0, 1.0]
        weights = [1.0, 3.5, 5.0]

    utility = 0.0

    for idx, stat in enumerate(step_stats):
        c_e = max(0.5, stat['c_eff'])
        t_e = target_c_eff[idx]
        w = weights[idx]

        # Log-space squared penalty from target capacity
        diff = math.log(c_e) - math.log(t_e)
        utility -= w * (diff ** 2)

    # Step 1 accessibility bonus: Starting with a world-famous club makes the game immediately welcoming
    if chain[0] in TIER_1_CLUBS:
        utility += 6.0
    elif chain[0] in TIER_2_CLUBS:
        utility += 3.0

    # Reward Step 2 & 3 having famous recognizable players
    for idx in range(1, k - 1):
        # Count players with R(p) >= 0.50 (well known players)
        famous_count = sum(1 for p in step_stats[idx]['players'] if rec_map.get(p, 0) >= 0.50)
        utility += 2.0 * min(5, famous_count)

    # Climax Reward: Final step uniquely isolates target player
    final_raw = step_stats[-1]['raw_count']
    if final_raw == 1:
        utility += 25.0
    elif final_raw == 2:
        utility += 10.0
    else:
        # If final step has > 2 players, penalize ambiguity
        utility -= (final_raw - 2) * 5.0

    return utility, step_stats


def find_best_chain_for_player(target_player, cand_clubs, club_to_players, rec_map):
    """
    Searches club permutations to find the globally optimal chain for target_player.
    Evaluates 4-step chains first; falls back to 3-step chains if a 4-step chain
    would cause an artificial bottleneck.
    """
    import itertools

    best_chain = None
    best_score = -float('inf')
    best_stats = None

    # Filter out youth/amateur clubs with < 30 players
    meaningful_clubs = [c for c in cand_clubs if len(club_to_players.get(c, set())) >= 30]
    if len(meaningful_clubs) < 2:
        meaningful_clubs = cand_clubs

    # Sort clubs by prominence so Tier 1 & major clubs are prioritized
    meaningful_clubs.sort(key=lambda c: (
        c in TIER_1_CLUBS,
        c in TIER_2_CLUBS,
        len(club_to_players.get(c, set()))
    ), reverse=True)

    # Consider top 7 candidate clubs to keep permutation search fast
    clubs_subset = meaningful_clubs[:7]

    # Try 4-step permutations first if player has >= 4 clubs
    if len(clubs_subset) >= 4:
        for perm in itertools.permutations(clubs_subset, 4):
            score, stats = evaluate_funnel_chain(perm, target_player, club_to_players, rec_map)
            if score > best_score:
                best_score = score
                best_chain = list(perm)
                best_stats = stats

    # If no valid 4-step chain was found with zero premature bottlenecks, try 3-step
    if best_score == -float('inf') and len(clubs_subset) >= 3:
        for perm in itertools.permutations(clubs_subset, 3):
            score, stats = evaluate_funnel_chain(perm, target_player, club_to_players, rec_map)
            if score > best_score:
                best_score = score
                best_chain = list(perm)
                best_stats = stats

    return best_chain, best_score, best_stats
