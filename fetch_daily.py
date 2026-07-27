"""
fetch_daily.py — Playmaker Game Compiler
==========================================
Reads games.json to discover all registered games and compiles
each game's HTML for today and past N days (back-in-time).

Usage
-----
  python fetch_daily.py                        # today's puzzles (all games)
  python fetch_daily.py --offset -1            # yesterday's puzzles (all games)
  python fetch_daily.py --puzzle 42            # force a specific puzzle number
  python fetch_daily.py --random               # random puzzle number
  python fetch_daily.py --max-back-days 7      # also compile last 7 days (default)
  python fetch_daily.py --game top_transfers   # compile only one game

Adding a new game
-----------------
1. Add an entry to games.json with all required fields.
2. Create a template in templates/<templateFile>.
3. Add the game's CSV data file (for fetch_daily.py to read).
4. Add a loader section in the GAME DATA LOADERS dict below.
5. Run this script — all output files are auto-generated.
"""

import os
import re
import json
import csv
import argparse
import random as rand_mod
from datetime import datetime, timedelta

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────
TOTAL_DAYS   = 180   # puzzle cycle length
GAMES_JSON   = "games.json"
TEMPLATES_DIR = "templates"
OUTPUT_DIR   = "games"


# ─────────────────────────────────────────────────────────────
# Game data loaders  (one function per game id)
# ─────────────────────────────────────────────────────────────
def load_top_transfers(puzzle_num):
    """Returns (game_data_dict, extra_data_dict) for the top_transfers game."""
    game_mode = "nationality" if puzzle_num % 2 == 0 else "club"
    game_data = {"mode": game_mode, "name": "", "transfers": []}

    if game_mode == "club":
        csv_path = "daily_transfer_games.csv"
        if not os.path.exists(csv_path):
            print(f"  ERROR: {csv_path} not found.")
            return None, None
        with open(csv_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if int(r.get("game_day", 1)) == puzzle_num:
                    if not game_data["name"]:
                        game_data["name"] = r.get("selected_club", "")
                    game_data["transfers"].append({
                        "player_name":    r.get("player_name", ""),
                        "from_club_name": r.get("from_club_name", ""),
                        "transfer_fee":   r.get("transfer_fee", "0"),
                        "transfer_date":  r.get("transfer_date", ""),
                    })
    else:
        csv_path = "daily_nationality_transfer_games.csv"
        if not os.path.exists(csv_path):
            print(f"  ERROR: {csv_path} not found.")
            return None, None
        with open(csv_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if int(r.get("game_day", 1)) == puzzle_num:
                    if not game_data["name"]:
                        game_data["name"] = r.get("selected_nationality", "")
                    game_data["transfers"].append({
                        "player_name":  r.get("player_name", ""),
                        "to_club_name": r.get("to_club_name", ""),
                        "transfer_fee": r.get("transfer_fee", "0"),
                        "transfer_date": r.get("transfer_date", ""),
                    })

    if not game_data["name"]:
        print(f"  WARNING: No top_transfers data for puzzle #{puzzle_num}")
        return None, None

    # extra data: all players list
    all_players_json = "[]"
    if os.path.exists("all_players.json"):
        with open("all_players.json", "r", encoding="utf-8") as f:
            all_players_json = f.read()
    else:
        print("  WARNING: all_players.json not found.")

    extra = {
        "ALL_PLAYERS": all_players_json,
    }
    return game_data, extra


def load_transfer_destination(puzzle_num):
    """Returns (game_data_dict, extra_data_dict) for the transfer_destination game."""
    game_data = {"player_name": "", "nationality": "", "position": "", "transfers": []}

    csv_path = "daily_destination_games.csv"
    if not os.path.exists(csv_path):
        print(f"  WARNING: {csv_path} not found.")
        return None, None

    with open(csv_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if int(r.get("game_day", 1)) == puzzle_num:
                if not game_data["player_name"]:
                    game_data["player_name"] = r.get("player_name", "")
                    game_data["nationality"]  = r.get("country_of_citizenship", "")
                    game_data["position"]     = r.get("position", "")
                game_data["transfers"].append({
                    "transfer_date":      r.get("transfer_date_str", r.get("transfer_date", "")),
                    "from_club_name":     r.get("from_club_name", ""),
                    "to_club_name":       r.get("to_club_name", ""),
                    "transfer_fee":       float(r.get("transfer_fee", "0.0") or 0.0),
                    "market_value_in_eur": float(r.get("market_value_in_eur", "0.0") or 0.0),
                })

    if not game_data["player_name"]:
        print(f"  WARNING: No transfer_destination data for puzzle #{puzzle_num}")
        return None, None

    all_clubs_json = "[]"
    if os.path.exists("all_clubs.json"):
        with open("all_clubs.json", "r", encoding="utf-8") as f:
            all_clubs_json = f.read()
    else:
        print("  WARNING: all_clubs.json not found.")

    extra = {
        "ALL_CLUBS": all_clubs_json,
    }
    return game_data, extra


def load_top_scorers(puzzle_num):
    """Returns (game_data_dict, extra_data_dict) for the top_scorers game."""
    game_data = {"name": "", "scorers": []}

    csv_path = "daily_scorers_games.csv"
    if not os.path.exists(csv_path):
        print(f"  ERROR: {csv_path} not found.")
        return None, None

    with open(csv_path, "r", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if int(r.get("game_day", 1)) == puzzle_num:
                if not game_data["name"]:
                    game_data["name"] = r.get("selected_target", "")
                game_data["scorers"].append({
                    "player_name":  r.get("player_name", ""),
                    "club_name":    r.get("club_name", ""),
                    "goals":        int(float(r.get("goals", "0"))),
                    "appearances":  int(float(r.get("appearances", "0"))),
                    "nationality":  r.get("nationality", ""),
                })

    if not game_data["name"]:
        print(f"  WARNING: No top_scorers data for puzzle #{puzzle_num}")
        return None, None

    # extra data: all players list
    all_players_json = "[]"
    if os.path.exists("all_players.json"):
        with open("all_players.json", "r", encoding="utf-8") as f:
            all_players_json = f.read()
    else:
        print("  WARNING: all_players.json not found.")

    extra = {
        "ALL_PLAYERS": all_players_json,
    }
    return game_data, extra


# Map game id → loader function
GAME_LOADERS = {
    "top_transfers":       load_top_transfers,
    "transfer_destination": load_transfer_destination,
    "top_scorers":         load_top_scorers,
}

# Map game id → the JS variable name for the main data object
GAME_DATA_VAR = {
    "top_transfers":       "DAILY_TRANSFER_GAME",
    "transfer_destination": "DAILY_DESTINATION_GAME",
    "top_scorers":         "DAILY_SCORERS_GAME",
}

# Patterns to strip from a template before injecting fresh data
STRIP_PATTERNS = {
    "top_transfers": [
        r'const\s+DAILY_TRANSFER_GAME\s*=\s*\{[\s\S]*?\};',
        r'const\s+ALL_PLAYERS\s*=\s*\[[\s\S]*?\];',
        r'const\s+PUZZLE_NUMBER\s*=\s*\d+;',
        r'const\s+IS_BACK_IN_TIME\s*=\s*(true|false);',
        r'const\s+MAX_BACK_DAYS\s*=\s*\d+;',
        r'const\s+GAME_NOTE\s*=\s*"[^"]*";',
    ],
    "transfer_destination": [
        r'const\s+DAILY_DESTINATION_GAME\s*=\s*\{[\s\S]*?\};',
        r'const\s+ALL_CLUBS\s*=\s*\[[\s\S]*?\];',
        r'const\s+PUZZLE_NUMBER\s*=\s*\d+;',
        r'const\s+IS_BACK_IN_TIME\s*=\s*(true|false);',
        r'const\s+MAX_BACK_DAYS\s*=\s*\d+;',
        r'const\s+GAME_NOTE\s*=\s*"[^"]*";',
    ],
    "top_scorers": [
        r'const\s+DAILY_SCORERS_GAME\s*=\s*\{[\s\S]*?\};',
        r'const\s+ALL_PLAYERS\s*=\s*\[[\s\S]*?\];',
        r'const\s+PUZZLE_NUMBER\s*=\s*\d+;',
        r'const\s+IS_BACK_IN_TIME\s*=\s*(true|false);',
        r'const\s+MAX_BACK_DAYS\s*=\s*\d+;',
        r'const\s+GAME_NOTE\s*=\s*"[^"]*";',
    ],
}


# ─────────────────────────────────────────────────────────────
# Core compiler
# ─────────────────────────────────────────────────────────────
def compile_game(game_cfg, puzzle_num, day_offset=0, max_back_days=7):
    """
    Compile a single game HTML for a given puzzle_num.
    day_offset=0 → today's file (game_id.html)
    day_offset=1 → yesterday's file (game_id_d1.html)
    etc.
    """
    game_id       = game_cfg["id"]
    template_file = game_cfg.get("templateFile", f"{game_id}_template.html")
    template_path = os.path.join(TEMPLATES_DIR, template_file)
    game_note     = game_cfg.get("note", "")

    if not os.path.exists(template_path):
        print(f"  ERROR: template not found: {template_path}")
        return False

    loader = GAME_LOADERS.get(game_id)
    if not loader:
        print(f"  ERROR: no loader registered for game id '{game_id}'")
        return False

    game_data, extra = loader(puzzle_num)
    if game_data is None:
        return False

    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Strip any previously injected data
    for pattern in STRIP_PATTERNS.get(game_id, []):
        html = re.sub(pattern, '', html)

    is_back_in_time = day_offset > 0
    data_var_name   = GAME_DATA_VAR.get(game_id, "DAILY_GAME")

    # Build injection block
    extra_lines = []
    for var_name, json_str in (extra or {}).items():
        extra_lines.append(f"        const {var_name} = {json_str};")

    # Inject game note (escaped for JS string)
    safe_note = game_note.replace('\\', '\\\\').replace('"', '\\"')
    extra_lines.append(f'        const GAME_NOTE = "{safe_note}";')

    injection = f"""
    <script id="daily-game-data">
        const {data_var_name} = {json.dumps(game_data, ensure_ascii=False)};
{chr(10).join(extra_lines)}
        const PUZZLE_NUMBER    = {puzzle_num};
        const IS_BACK_IN_TIME  = {'true' if is_back_in_time else 'false'};
        const MAX_BACK_DAYS    = {max_back_days};
    </script>
    """

    # Inject before the game-specific script (marker comment)
    marker = "<!-- Micro-interaction Script -->"
    if marker in html:
        compiled = html.replace(marker, injection + "\n" + marker)
    else:
        compiled = html.replace("</body>", injection + "\n</body>")

    # Determine output filename
    if day_offset == 0:
        out_name = f"{game_id}.html"
    else:
        out_name = f"{game_id}_d{day_offset}.html"

    out_path = os.path.join(OUTPUT_DIR, out_name)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(compiled)

    back_label = f" (back-in-time d{day_offset})" if is_back_in_time else ""
    print(f"  ✓ {out_path}  [puzzle #{puzzle_num}{back_label}]")
    return True


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Playmaker Game Compiler")
    parser.add_argument("--offset",        type=int,   default=0,  help="Offset today's date by N days.")
    parser.add_argument("--puzzle",        type=int,   default=0,  help="Force a specific puzzle index (1-indexed).")
    parser.add_argument("--random",        action="store_true",    help="Compile a random puzzle.")
    parser.add_argument("--max-back-days", type=int,   default=7,  help="Number of past days to compile (default 7).")
    parser.add_argument("--game",          type=str,   default="", help="Compile only this game id (default: all).")
    args = parser.parse_args()

    # Load games registry
    if not os.path.exists(GAMES_JSON):
        print(f"ERROR: {GAMES_JSON} not found.")
        return

    with open(GAMES_JSON, "r", encoding="utf-8") as f:
        games = json.load(f)

    if args.game:
        games = [g for g in games if g["id"] == args.game]
        if not games:
            print(f"ERROR: Game id '{args.game}' not found in {GAMES_JSON}.")
            return

    # Determine base puzzle number for today (offset=0)
    def puzzle_for_offset(off):
        if args.random:
            return rand_mod.randint(1, TOTAL_DAYS)
        if args.puzzle > 0:
            return min(args.puzzle, TOTAL_DAYS)
        target_date = datetime.today() + timedelta(days=args.offset + off * -1)
        return (target_date.timetuple().tm_yday - 1) % TOTAL_DAYS + 1

    max_back = args.max_back_days

    print(f"\n=== Playmaker Compiler — {datetime.today().strftime('%Y-%m-%d')} ===")
    print(f"Compiling {len(games)} game(s), today + {max_back} back-in-time days\n")

    for game_cfg in games:
        gid = game_cfg["id"]

        # Skip games not yet ready
        if game_cfg.get("status") == "coming_soon":
            print(f"── {game_cfg['name']} ({gid}) — SKIPPED (coming soon)\n")
            continue

        print(f"── {game_cfg['name']} ({gid}) ──")

        # Today (offset 0)
        pnum_today = puzzle_for_offset(0)
        compile_game(game_cfg, pnum_today, day_offset=0, max_back_days=max_back)

        # Back-in-time files
        for d in range(1, max_back + 1):
            pnum_past = puzzle_for_offset(d)
            compile_game(game_cfg, pnum_past, day_offset=d, max_back_days=max_back)

        print()

    print("=== Compilation complete ===\n")


if __name__ == "__main__":
    main()
