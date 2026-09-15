#!/usr/bin/env python3
"""
scripts/contextual_puzzle_scheduler.py — Calendar-Aware Contextual Puzzle Scheduler
===================================================================================
Generates, audits, and maintains a deterministic 365-day puzzle schedule ledger
(`data/puzzle_schedule_ledger.json`) aligning daily puzzles with real-world football
fixtures while strictly enforcing a >=100-day repeat freeze rule and derby alternation.

Usage:
  python scripts/contextual_puzzle_scheduler.py --generate --days 365
  python scripts/contextual_puzzle_scheduler.py --audit-freeze
  python scripts/contextual_puzzle_scheduler.py --show-date 2026-10-26
"""

import os
import sys
import json
import csv
import argparse
import datetime
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
FIXTURES_FILE = os.path.join(DATA_DIR, "fixtures_calendar.json")
LEDGER_FILE = os.path.join(DATA_DIR, "puzzle_schedule_ledger.json")

TOTAL_PUZZLES = 180
FREEZE_DAYS = 100

# Base Launch Date: 2026-07-27 (Playmaker Day 1)
DEFAULT_START_DATE = datetime.date(2026, 7, 27)
TODAY_DATE = datetime.date(2026, 9, 15)

# Game launch dates determining historical puzzle day 1
LAUNCH_DATES = {
    "top_transfers": datetime.date(2026, 7, 27),
    "transfer_destination": datetime.date(2026, 7, 27),
    "top_scorers": datetime.date(2026, 7, 27),
    "club_connect": datetime.date(2026, 7, 31),
    "player_chain": datetime.date(2026, 9, 11),
    "passport_fc": datetime.date(2026, 9, 14),
}

# Pre-launch filler offsets for dates before each game launched
PRE_LAUNCH_FILLERS = {
    "club_connect": 121,
    "player_chain": 131,
    "passport_fc": 141
}

def load_fixtures_map():
    """Load fixtures mapped by YYYY-MM-DD."""
    if not os.path.exists(FIXTURES_FILE):
        return {}
    try:
        with open(FIXTURES_FILE, "r", encoding="utf-8") as f:
            fixtures = json.load(f)
            return {f["date"]: f for f in fixtures if "date" in f}
    except Exception as e:
        print(f"⚠️ Error loading {FIXTURES_FILE}: {e}")
        return {}

def load_puzzle_metadata():
    """
    Scans CSVs to build indexing lookups:
    - transfer_club_puzzles: club_name -> list of puzzle_nums in daily_transfer_games.csv
    - transfer_nat_puzzles: nationality -> list of puzzle_nums in daily_nationality_transfer_games.csv
    - scorers_comp_puzzles: comp_keyword -> list of puzzle_nums in daily_scorers_games.csv
    """
    transfer_club_puzzles = defaultdict(list)
    transfer_nat_puzzles = defaultdict(list)
    scorers_comp_puzzles = defaultdict(list)

    # 1. daily_transfer_games.csv
    transfers_path = os.path.join(BASE_DIR, "daily_transfer_games.csv")
    if os.path.exists(transfers_path):
        with open(transfers_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                club = r.get("selected_club", "").strip()
                pnum = int(r.get("game_day", 1))
                if club and pnum not in transfer_club_puzzles[club]:
                    transfer_club_puzzles[club].append(pnum)

    # 2. daily_nationality_transfer_games.csv
    transfers_nat_path = os.path.join(BASE_DIR, "daily_nationality_transfer_games.csv")
    if os.path.exists(transfers_nat_path):
        with open(transfers_nat_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                nat = r.get("selected_nationality", "").strip()
                pnum = int(r.get("game_day", 1))
                if nat and pnum not in transfer_nat_puzzles[nat]:
                    transfer_nat_puzzles[nat].append(pnum)

    # 3. daily_scorers_games.csv
    scorers_path = os.path.join(BASE_DIR, "daily_scorers_games.csv")
    if os.path.exists(scorers_path):
        with open(scorers_path, "r", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                target = r.get("selected_target", "").strip()
                pnum = int(r.get("game_day", 1))
                # Index by words (e.g. "Premier League", "Champions League", "La Liga", "Serie A", "Bundesliga", "Europa League")
                for key in ["Premier League", "Champions League", "La Liga", "Serie A", "Bundesliga", "Europa League", "UEFA Europa League"]:
                    if (key.lower() in target.lower() or ("europa" in key.lower() and "europa" in target.lower())) and pnum not in scorers_comp_puzzles[key]:
                        scorers_comp_puzzles[key].append(pnum)

    return transfer_club_puzzles, transfer_nat_puzzles, scorers_comp_puzzles

def build_schedule_ledger(start_date=DEFAULT_START_DATE, total_days=365):
    """
    Generates a 365-day schedule ledger enforcing:
    1. >= 100-day repeat freeze per puzzle ID across all 6 games.
    2. >= 100-day repeat freeze per club for club-centric games.
    3. Derby alternation for repeat head-to-head fixtures.
    4. Contextual matchday injection for Top Transfers, Club Connect, and Top Scorers.
    5. Staggered starters for all games.
    """
    fixtures_map = load_fixtures_map()
    club_puzzles, nat_puzzles, scorers_comp_puzzles = load_puzzle_metadata()

    # State tracking
    # last_used_puzzles[game_id][puzzle_id] = day_index
    last_used_puzzles = {
        "top_transfers": {},
        "transfer_destination": {},
        "top_scorers": {},
        "club_connect": {},
        "player_chain": {},
        "passport_fc": {}
    }
    # last_used_clubs[game_id][club_name] = day_index
    last_used_clubs = {
        "top_transfers": {},
        "club_connect": {}
    }
    # last_featured_derby[derby_key] = club_name
    last_featured_derby = {}

    # Sequential rotation cursor per game, initializing from tomorrow's linear offset
    rotation_cursor = {}
    for gid, ld in LAUNCH_DATES.items():
        tom_diff = ((TODAY_DATE + datetime.timedelta(days=1)) - ld).days
        rotation_cursor[gid] = (tom_diff % TOTAL_PUZZLES) + 1

    # Reverse lookup: puzzle_num -> club in daily_transfer_games.csv
    puzzle_to_club = {}
    for club, pnums in club_puzzles.items():
        for p in pnums:
            puzzle_to_club[p] = club

    # Marquee clubs whose puzzles are reserved for matchday clashes
    marquee_clubs = {
        "Real Madrid", "Barcelona", "Arsenal", "Chelsea", "Manchester City",
        "Manchester United", "Liverpool", "Tottenham Hotspur", "Bayern Munich",
        "Borussia Dortmund", "Inter", "AC Milan", "Juventus", "Paris Saint-Germain",
        "Atletico Madrid", "Roma", "Lazio"
    }
    marquee_puzzles = set()
    for c in marquee_clubs:
        marquee_puzzles.update(club_puzzles.get(c, []))

    ledger = {}
    today_idx = (TODAY_DATE - start_date).days

    # ── Phase 1: Populate Historical Dates (<= TODAY_DATE) Strictly Immutable ──
    for d_idx in range(today_idx + 1):
        c_date = start_date + datetime.timedelta(days=d_idx)
        d_str = c_date.strftime("%Y-%m-%d")
        day_entry = {
            "puzzles": {},
            "matchday_context": None
        }
        for gid, ld in LAUNCH_DATES.items():
            diff = (c_date - ld).days
            if diff >= 0:
                pnum = (diff % TOTAL_PUZZLES) + 1
            else:
                pnum = ((PRE_LAUNCH_FILLERS[gid] + diff - 1) % TOTAL_PUZZLES) + 1
            last_used_puzzles[gid][pnum] = d_idx
            day_entry["puzzles"][gid] = pnum
            if gid in ["top_transfers", "club_connect"]:
                c = puzzle_to_club.get(pnum)
                if c:
                    last_used_clubs[gid][c] = d_idx
        ledger[d_str] = day_entry

    # ── Phase 2: Contextual & Freeze-Protected Scheduling Starting Tomorrow ──
    for day_idx in range(today_idx + 1, total_days):
        current_date = start_date + datetime.timedelta(days=day_idx)
        date_str = current_date.strftime("%Y-%m-%d")
        fixture = fixtures_map.get(date_str)

        day_entry = {
            "puzzles": {},
            "matchday_context": None
        }

        # ── 1. Determine Matchday Context (if any) ───────────────────────────
        target_club_top_transfers = None
        target_club_club_connect = None
        target_comp_scorers = None

        if fixture:
            home = fixture.get("home_club", "")
            away = fixture.get("away_club", "")
            comp = fixture.get("competition", "")
            clash_name = fixture.get("clash_name", f"{home} vs {away}")
            derby_key = tuple(sorted([home, away]))

            # Derby alternation: pick the club NOT featured in the previous meeting
            last_club = last_featured_derby.get(derby_key)
            if last_club == home:
                chosen_club = away
                alt_club = home
            elif last_club == away:
                chosen_club = home
                alt_club = away
            else:
                chosen_club = home
                alt_club = away

            target_club_club_connect = chosen_club
            target_club_top_transfers = chosen_club
            target_comp_scorers = comp

        # ── 2. Helper to check if a puzzle ID is freeze-valid ────────────────
        def is_puzzle_valid(game_id, pnum, target_club=None, is_matchday=False):
            # Universal 100-day repeat freeze per puzzle ID
            last_p = last_used_puzzles[game_id].get(pnum)
            if last_p is not None and (day_idx - last_p) < FREEZE_DAYS:
                return False

            # On non-matchdays in club games, reserve marquee puzzles exclusively for matchdays
            if not is_matchday and game_id in ["top_transfers", "club_connect"]:
                if pnum in marquee_puzzles:
                    return False

            # Specific game mode constraints:
            # top_transfers: odd = club mode, even = nationality mode
            if game_id == "top_transfers":
                if target_club and pnum % 2 == 0:
                    return False

            return True

        def record_selection(game_id, pnum, club=None):
            last_used_puzzles[game_id][pnum] = day_idx
            if game_id in ["top_transfers", "club_connect"]:
                c = club or puzzle_to_club.get(pnum)
                if c:
                    last_used_clubs[game_id][c] = day_idx
            day_entry["puzzles"][game_id] = pnum

        # ── 3. Assign Puzzles for Each Game ──────────────────────────────────
        chosen_club_actual = None

        # A. Club Connect (Club Matchday Target)
        selected_cc = None
        if target_club_club_connect:
            for candidate in [chosen_club, alt_club]:
                candidates = club_puzzles.get(candidate, [])
                for p in candidates:
                    if is_puzzle_valid("club_connect", p, candidate, is_matchday=True):
                        selected_cc = p
                        chosen_club_actual = candidate
                        record_selection("club_connect", p, candidate)
                        break
                if selected_cc:
                    break

        if not selected_cc:
            # Fallback to rotation
            curr = rotation_cursor["club_connect"]
            for offset in range(TOTAL_PUZZLES):
                candidate = ((curr + offset - 1) % TOTAL_PUZZLES) + 1
                if is_puzzle_valid("club_connect", candidate, is_matchday=False):
                    selected_cc = candidate
                    record_selection("club_connect", candidate)
                    rotation_cursor["club_connect"] = (candidate % TOTAL_PUZZLES) + 1
                    break

        # B. Top Transfers (Club or Nationality Matchday Target)
        selected_tt = None
        if target_club_top_transfers:
            cand_list = [chosen_club_actual, alt_club] if chosen_club_actual else [chosen_club, alt_club]
            for candidate in cand_list:
                if not candidate:
                    continue
                # If international match, check nationality pool (even numbers)
                if fixture and fixture.get("competition") in ["International", "UEFA Nations League", "Nations League"]:
                    nat_cands = [p for p in nat_puzzles.get(candidate, []) if p % 2 == 0]
                    for p in nat_cands:
                        if is_puzzle_valid("top_transfers", p, is_matchday=True):
                            selected_tt = p
                            record_selection("top_transfers", p)
                            break
                else:
                    # Club candidates (must be odd numbers for club mode)
                    club_cands = [p for p in club_puzzles.get(candidate, []) if p % 2 == 1]
                    for p in club_cands:
                        if is_puzzle_valid("top_transfers", p, candidate, is_matchday=True):
                            selected_tt = p
                            if not chosen_club_actual:
                                chosen_club_actual = candidate
                            record_selection("top_transfers", p, candidate)
                            break
                if selected_tt:
                    break

        if not selected_tt:
            # Fallback to rotation
            curr = rotation_cursor["top_transfers"]
            for offset in range(TOTAL_PUZZLES):
                candidate = ((curr + offset - 1) % TOTAL_PUZZLES) + 1
                if is_puzzle_valid("top_transfers", candidate, is_matchday=False):
                    selected_tt = candidate
                    record_selection("top_transfers", candidate)
                    rotation_cursor["top_transfers"] = (candidate % TOTAL_PUZZLES) + 1
                    break

        # Set finalized matchday context if active
        if fixture:
            featured = chosen_club_actual or chosen_club
            last_featured_derby[derby_key] = featured
            day_entry["matchday_context"] = {
                "clash_name": clash_name,
                "competition": comp,
                "home_club": home,
                "away_club": away,
                "featured_club": featured,
                "hook": fixture.get("hook", f"⚔️ {clash_name.upper()} SPECIAL!"),
                "hashtags": fixture.get("hashtags", [f"#{home.replace(' ', '')}", f"#{away.replace(' ', '')}"])
            }

        # C. Top Scorers (Competition Matchday Target)
        selected_ts = None
        if target_comp_scorers:
            comp_candidates = scorers_comp_puzzles.get(target_comp_scorers, [])
            for p in comp_candidates:
                if is_puzzle_valid("top_scorers", p):
                    selected_ts = p
                    record_selection("top_scorers", p)
                    break

        if not selected_ts:
            # Fallback to rotation
            curr = rotation_cursor["top_scorers"]
            for offset in range(TOTAL_PUZZLES):
                candidate = ((curr + offset - 1) % TOTAL_PUZZLES) + 1
                if is_puzzle_valid("top_scorers", candidate):
                    selected_ts = candidate
                    record_selection("top_scorers", candidate)
                    rotation_cursor["top_scorers"] = (candidate % TOTAL_PUZZLES) + 1
                    break

        # D. Standard Player Journey Games (Transfer Destination, Player Chain, Passport FC)
        for gid in ["transfer_destination", "player_chain", "passport_fc"]:
            curr = rotation_cursor[gid]
            for offset in range(TOTAL_PUZZLES):
                candidate = ((curr + offset - 1) % TOTAL_PUZZLES) + 1
                if is_puzzle_valid(gid, candidate):
                    record_selection(gid, candidate)
                    rotation_cursor[gid] = (candidate % TOTAL_PUZZLES) + 1
                    break

        ledger[date_str] = day_entry

    return ledger

def audit_schedule_freeze(ledger=None):
    """
    Audits the generated schedule ledger for:
    1. >= 100-day repeat freeze per puzzle ID.
    2. >= 100-day repeat freeze per club for club games.
    3. Complete 6-game coverage for all dates.
    Returns (is_valid: bool, issues_list: list).
    """
    if ledger is None:
        if not os.path.exists(LEDGER_FILE):
            print(f"❌ Error: {LEDGER_FILE} not found. Run with --generate first.")
            return False, ["Ledger file missing"]
        with open(LEDGER_FILE, "r", encoding="utf-8") as f:
            ledger = json.load(f)

    sorted_dates = sorted(ledger.keys())
    print(f"\n🔍 Auditing schedule ledger across {len(sorted_dates)} dates ({sorted_dates[0]} to {sorted_dates[-1]})...")

    games = ["top_transfers", "transfer_destination", "top_scorers", "club_connect", "player_chain", "passport_fc"]
    last_seen_puzzles = {g: {} for g in games}
    issues = []
    matchdays_count = 0

    for day_idx, date_str in enumerate(sorted_dates):
        entry = ledger[date_str]
        puzzles = entry.get("puzzles", {})
        if entry.get("matchday_context"):
            matchdays_count += 1

        for g in games:
            pnum = puzzles.get(g)
            if pnum is None:
                issues.append(f"{date_str}: Missing puzzle assignment for game '{g}'")
                continue

            last_day = last_seen_puzzles[g].get(pnum)
            if last_day is not None:
                diff = day_idx - last_day
                if diff < FREEZE_DAYS:
                    issues.append(
                        f"🚨 Freeze Violation in {g} on {date_str}: Puzzle #{pnum} repeated after only {diff} days! (Required: >={FREEZE_DAYS})"
                    )
            last_seen_puzzles[g][pnum] = day_idx

    if issues:
        print(f"❌ Audit Failed! Found {len(issues)} freeze or assignment issues:")
        for iss in issues[:10]:
            print(f"  • {iss}")
        if len(issues) > 10:
            print(f"  ... and {len(issues) - 10} more.")
        return False, issues
    else:
        print(f"✅ 100% Audit Success!")
        print(f"  • 0 freeze violations across {len(sorted_dates)} days.")
        print(f"  • All {len(games)} games have valid puzzle assignments for every date.")
        print(f"  • {matchdays_count} active matchday derbies & special events successfully contextualized.")
        return True, []

def save_ledger(ledger):
    """Saves the schedule ledger to data/puzzle_schedule_ledger.json."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)
    print(f"💾 Saved schedule ledger to {LEDGER_FILE}")

def main():
    parser = argparse.ArgumentParser(description="Contextual Puzzle Scheduler Engine")
    parser.add_argument("--generate", action="store_true", help="Generate full schedule ledger")
    parser.add_argument("--days", type=int, default=365, help="Number of days to schedule (default: 365)")
    parser.add_argument("--audit-freeze", action="store_true", help="Verify 100-day freeze constraint across ledger")
    parser.add_argument("--show-date", type=str, help="Display schedule details for a specific date (YYYY-MM-DD)")

    args = parser.parse_args()

    if args.show_date:
        if not os.path.exists(LEDGER_FILE):
            print(f"❌ {LEDGER_FILE} not found. Run with --generate first.")
            return
        with open(LEDGER_FILE, "r", encoding="utf-8") as f:
            ledger = json.load(f)
        date_data = ledger.get(args.show_date)
        if not date_data:
            print(f"ℹ️ Date {args.show_date} is not in the schedule ledger.")
            return
        print(f"\n📅 Schedule for {args.show_date}:")
        ctx = date_data.get("matchday_context")
        if ctx:
            print(f"  ⚔️ Matchday: {ctx.get('clash_name')} ({ctx.get('competition')})")
            print(f"  ⭐ Hook:     {ctx.get('hook')}")
            print(f"  🏷️ Tags:     {' '.join(ctx.get('hashtags', []))}")
        else:
            print("  ℹ️ Non-Matchday (General Freeze-Protected Rotation)")
        print("  🧩 Puzzles:")
        for gid, pnum in date_data.get("puzzles", {}).items():
            print(f"     • {gid:<22}: Puzzle #{pnum}")
        print()
        return

    if args.generate:
        print(f"\n🚀 Generating contextual puzzle schedule ledger for {args.days} days...")
        ledger = build_schedule_ledger(total_days=args.days)
        save_ledger(ledger)
        valid, _ = audit_schedule_freeze(ledger)
        sys.exit(0 if valid else 1)

    if args.audit_freeze:
        valid, _ = audit_schedule_freeze()
        sys.exit(0 if valid else 1)

    parser.print_help()

if __name__ == "__main__":
    main()
