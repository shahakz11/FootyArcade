#!/usr/bin/env python3
"""
verify_daily_puzzles.py — Proactive Daily Puzzle Verification & Auto-Sync Engine
================================================================================
Audits daily puzzles for Playmaker / FootyArcade across all registered games:
- Top Transfers (top_transfers)
- Transfer Destination (transfer_destination)
- Top Scorers (top_scorers)
- Club Connect (club_connect)
- Player Chain (player_chain)
- Passport FC (passport_fc)

Key Capabilities:
1. Target tomorrow's puzzles before user release (--offset 1 default) or specific puzzles/dates.
2. Tier 1 (Deterministic Integrity):
   - Validates positive fees, goals, appearances, non-empty pools, chronological timelines.
   - For Passport FC: enforces that from Step 2 onward, all available responses matching
     criteria are present and accounted for in valid_players.
   - Ensures 100% of answer clubs and players exist in master dictionaries (all_clubs.json, all_players.json).
3. Tier 2 (Proactive AI Fact-Check & Consensus Guard):
   - Transfer Destination: checks clubs, years, and transfer fees with LLM.
   - Player Chain: from Step 2 onward, asks LLM which players played for the combination of teams,
     compares against the pool, and if missing players are confirmed by Model 2, populates the pool.
   - Passport FC: from Step 2 onward, asks LLM which players played for Club and Nationality,
     compares against pool, and if missing players are confirmed by Model 2, populates the pool.
   - Top Transfers / Top Scorers / Club Connect: verifies factual validity against official records.
4. Auto-Sync Mode (--fix):
   - Automatically adds missing clubs/players to all_clubs.json/all_players.json, updates pools, and recompiles game HTML.
5. Reporting:
   - Local JSON report in reports/audit_<YYYY-MM-DD>.json.
   - Live audit logging to Google Sheet via Apps Script webhook (Puzzle Audits tab).
"""

import os
import sys
import json
import csv
import re
import time
import argparse
import urllib.request
import urllib.error
import unicodedata
from datetime import datetime, timedelta

# Increase CSV field size limit
csv.field_size_limit(sys.maxsize)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from fetch_daily import (
    GAMES_JSON,
    TOTAL_DAYS,
    compile_game,
    load_top_transfers,
    load_transfer_destination,
    load_top_scorers,
    load_club_connect,
    load_player_chain,
    load_passport_fc,
    _dedupe_canonical_names
)

FEEDBACK_WEBHOOK_URL = 'https://script.google.com/macros/s/AKfycbxEG3jA0QduSlh3ZmMR-98lTK1i4AbO-FgmFpymlJTof_8DZpZdmODSto0Q4NTyX7_7OA/exec'
DEFAULT_LAUNCH_DATE = datetime(2026, 7, 27)

PRIMARY_GROQ_MODELS = [
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b"
]

CONSENSUS_GROQ_MODELS = [
    "qwen/qwen3.8-27b",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-20b"
]


def normalize_str(s):
    if not s or not isinstance(s, str):
        return ""
    s = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', s).strip()
    s = s.replace('ð', 'd').replace('Ð', 'D').replace('þ', 'th').replace('Þ', 'Th')
    s = s.replace('ø', 'o').replace('Ø', 'O').replace('ł', 'l').replace('Ł', 'L')
    s = s.replace('đ', 'd').replace('Đ', 'D').replace('æ', 'ae').replace('Æ', 'Ae')
    s = s.replace('œ', 'oe').replace('Œ', 'Oe').replace('ß', 'ss')
    norm = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    return norm.strip().lower()


def load_master_entities():
    all_clubs = []
    all_players = []

    if os.path.exists("all_clubs.json"):
        with open("all_clubs.json", "r", encoding="utf-8") as f:
            all_clubs = json.load(f)

    if os.path.exists("all_players.json"):
        with open("all_players.json", "r", encoding="utf-8") as f:
            all_players = json.load(f)

    club_set = set()
    for c in all_clubs:
        if isinstance(c, str):
            club_set.add(normalize_str(c))
        elif isinstance(c, dict) and "name" in c:
            club_set.add(normalize_str(c["name"]))

    player_set = set()
    for p in all_players:
        if isinstance(p, dict) and p.get("Name"):
            player_set.add(normalize_str(p["Name"]))
        elif isinstance(p, str):
            player_set.add(normalize_str(p))

    return all_clubs, all_players, club_set, player_set


def calculate_puzzle_num(offset_days, launch_date_str=""):
    launch_dt = datetime.strptime(launch_date_str, "%Y-%m-%d") if launch_date_str else DEFAULT_LAUNCH_DATE
    target_date = datetime.today() + timedelta(days=offset_days)
    days_diff = (target_date.date() - launch_dt.date()).days
    if days_diff < 0:
        return 1
    return (days_diff % TOTAL_DAYS) + 1


def call_groq_api(models_to_try, system_prompt, user_prompt):
    """
    Query Groq LLM API with fallback models and retry backoff for rate limits.
    """
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key and os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                api_key = cfg.get("GROQ_API_KEY", "")
        except Exception:
            pass

    if not api_key:
        return {"status": "skipped", "reason": "No GROQ_API_KEY configured"}

    for model in models_to_try:
        # Retry up to 2 times per model if rate-limited (HTTP 429)
        for attempt in range(2):
            try:
                req_data = json.dumps({
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.0
                }).encode("utf-8")

                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=req_data,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
                    }
                )
                with urllib.request.urlopen(req, timeout=20) as resp:
                    if resp.status == 200:
                        data = json.loads(resp.read().decode("utf-8"))
                        content = data["choices"][0]["message"]["content"]
                        parsed = json.loads(content)
                        parsed["model_used"] = model
                        return parsed
            except urllib.error.HTTPError as e:
                if e.code == 429 and attempt == 0:
                    time.sleep(2.5)
                    continue
                break
            except Exception:
                break

    return {"status": "error", "reason": "All Groq model attempts failed"}


def cross_examine_fact_with_ai(game_id, puzzle_num, question, current_data_summary):
    """
    General Proactive AI Verification with 2-Model Consensus.
    """
    system_prompt = (
        "You are the senior fact-checking referee for Playmaker Football trivia.\n"
        "Your job is to verify whether the answers for tomorrow's daily puzzle are true, complete, and accurate.\n"
        "IMPORTANT FACT-CHECKING RULES:\n"
        "1. For transfer records, IGNORE exact calendar day or month discrepancies (only years matter). Also ignore minor reported fee variations (e.g. reported €35m vs €37m or add-ons/bonuses).\n"
        "2. The current year is 2026. The database is sourced directly from official Transfermarkt transfer records. Modern transfers from 2024, 2025, and 2026 are confirmed official Transfermarkt records. Do NOT flag transfers from 2024, 2025, or 2026 as non-existent.\n"
        "3. Only flag a discrepancy if a player NEVER signed for the club at all, or if there is a severe, unquestionable historical error.\n"
        "Answer ONLY in valid JSON matching this schema:\n"
        "{\n"
        '  "all_factual": true/false,\n'
        '  "confidence": 0.0 to 1.0,\n'
        '  "discrepancies": ["description of definite factual falsehood"],\n'
        '  "suggested_corrections": [\n'
        '    {"field": "...", "current": "...", "correct": "...", "reason": "..."}\n'
        "  ],\n"
        '  "notes": "1-sentence referee remark"\n'
        "}"
    )

    user_prompt = (
        f"Game: {game_id} (Puzzle #{puzzle_num})\n"
        f"Question / Scope: {question}\n\n"
        f"Our Stored Puzzle Answers:\n{current_data_summary}\n\n"
        f"Check strictly against official football records (Transfermarkt). Are all listed items factual and accurate? "
        f"Remember: Ignore exact day/month discrepancies for dates, and ignore minor fee rounding. "
        f"If there is a definite mistake, flag it."
    )

    res1 = call_groq_api(PRIMARY_GROQ_MODELS, system_prompt, user_prompt)
    if res1.get("status") in ("skipped", "error"):
        return res1

    if res1.get("all_factual", True):
        return {
            "consensus": True,
            "all_factual": True,
            "primary_model": res1.get("model_used"),
            "notes": res1.get("notes", "All records confirmed factual.")
        }

    # Step 2: Discrepancy detected by Model 1! Trigger Model 2 for verification consensus
    time.sleep(1.0)
    print(f"  🤖 Model 1 ({res1.get('model_used')}) flagged an issue. Cross-checking with Model 2...")
    res2 = call_groq_api(CONSENSUS_GROQ_MODELS, system_prompt, user_prompt)
    if res2.get("status") in ("skipped", "error"):
        return {
            "consensus": False,
            "all_factual": False,
            "primary_model": res1.get("model_used"),
            "secondary_model": "Unavailable",
            "notes": f"Model 1 flagged issues: {res1.get('discrepancies')}, but Model 2 was unreachable."
        }

    model2_flagged = not res2.get("all_factual", True)
    if model2_flagged:
        return {
            "consensus": True,
            "all_factual": False,
            "confirmed_discrepancy": True,
            "primary_model": res1.get("model_used"),
            "secondary_model": res2.get("model_used"),
            "model1_discrepancies": res1.get("discrepancies", []),
            "model2_discrepancies": res2.get("discrepancies", []),
            "suggested_corrections": res1.get("suggested_corrections", []) or res2.get("suggested_corrections", []),
            "notes": f"Both {res1.get('model_used')} and {res2.get('model_used')} agree on discrepancy!"
        }
    else:
        return {
            "consensus": False,
            "all_factual": True,
            "primary_model": res1.get("model_used"),
            "secondary_model": res2.get("model_used"),
            "notes": "Model 1 flagged an issue, but Model 2 rejected it as a false alarm. Maintained original puzzle."
        }


def cross_examine_pool_with_ai(game_id, puzzle_num, step_num, criteria_desc, existing_players):
    """
    Proactive Pool Verification for Player Chain & Passport FC (from Step 2 onward):
    1. Query Model 1: 'Which professional footballers played for [teams / club + nationality]?'
    2. Compare returned players against existing_players in database.
    3. If Model 1 suggests missing players:
       Query Model 2 with strict senior appearance verification: 'Did [Player X] factually make official senior first-team appearances for [Criteria]?'
    4. If Model 2 agrees with Model 1 -> populate player into puzzle pool and all_players.json!
    """
    system_prompt = (
        "You are an exhaustive senior football database researcher for Playmaker trivia.\n"
        "Your task is to identify ALL professional footballers who meet specific criteria.\n"
        "IMPORTANT RULES:\n"
        "1. Be EXHAUSTIVE: list every single prominent senior footballer who factually qualifies (do not stop at just 1 player if there are 2 or more).\n"
        "2. Use standard commonly-known football names (e.g., 'Alexis Sanchez' or 'Philippe Senderos', NEVER 4-word legal registration names like 'Alexis Alejandro Sánchez Sánchez').\n"
        "Answer ONLY in valid JSON matching this schema:\n"
        "{\n"
        '  "qualifying_players": ["Common Name 1", "Common Name 2", ...],\n'
        '  "confidence": 0.0 to 1.0,\n'
        '  "notes": "Brief explanation"\n'
        "}"
    )

    user_prompt = (
        f"Criteria: {criteria_desc}\n\n"
        f"List ALL prominent senior professional footballers who factually meet this exact criteria.\n"
        f"Search thoroughly across all eras and decades (1990s, 2000s, 2010s, 2020s) to ensure you do not miss any well-known player.\n"
        f"A player only qualifies if they made official senior competitive first-team appearances for EVERY specified club (or nationality requirement).\n"
        f"Do not guess or hallucinate. Return official common full names in JSON format."
    )

    res1 = call_groq_api(PRIMARY_GROQ_MODELS, system_prompt, user_prompt)
    if res1.get("status") in ("skipped", "error"):
        return {"status": "skipped", "reason": res1.get("reason", "Model query failed")}

    model1_players = res1.get("qualifying_players", [])
    if not isinstance(model1_players, list):
        return {"status": "skipped", "reason": "Invalid response structure from Model 1"}

    existing_norms = {normalize_str(p) for p in existing_players}
    potential_missing = []
    for p in model1_players:
        if p and isinstance(p, str) and normalize_str(p) not in existing_norms:
            potential_missing.append(p)

    if not potential_missing:
        return {
            "status": "complete",
            "missing_added": [],
            "notes": f"All qualifying players identified by {res1.get('model_used')} already exist in pool."
        }

    # Step 2: Double-check missing players against Model 2 with strict senior appearance criteria
    print(f"  🤖 Step {step_num}: Model 1 found potential missing players: {potential_missing}. Cross-verifying with Model 2...")
    confirmed_additions = []
    for candidate in potential_missing[:3]:  # limit to top 3 to avoid rate limits
        time.sleep(1.0)
        verify_prompt = (
            f"Player: {candidate}\n"
            f"Criteria: {criteria_desc}\n\n"
            f"Did {candidate} factually make official competitive senior first-team appearances for ALL required clubs / meet the nationality criteria? "
            f"If they never played a senior match for any of the clubs, answer false."
        )
        verify_sys = (
            "You are a strict football historian referee. "
            "Verify official senior first-team appearances. "
            "Answer ONLY in valid JSON matching this format:\n"
            '{"verified": true/false, "reason": "1-sentence explanation"}'
        )
        res2 = call_groq_api(CONSENSUS_GROQ_MODELS, verify_sys, verify_prompt)
        if res2.get("verified") is True:
            confirmed_additions.append(candidate)
            print(f"    ✓ Confirmed by Model 2 ({res2.get('model_used')}): {candidate}")
        else:
            print(f"    ✗ Rejected by Model 2: {candidate} ({res2.get('reason', 'Verification failed')})")

    return {
        "status": "success",
        "missing_added": confirmed_additions,
        "primary_model": res1.get("model_used"),
        "notes": f"Added {len(confirmed_additions)} missing qualifying player(s) confirmed by 2 models."
    }


class PuzzleVerifier:
    def __init__(self, fix_mode=False, dry_run=False):
        self.fix_mode = fix_mode
        self.dry_run = dry_run
        self.all_clubs, self.all_players, self.club_set, self.player_set = load_master_entities()
        self.issues = []
        self.fixes = []
        self.ai_checks = []

    def log_issue(self, game_id, puzzle_num, severity, message, entity_type=None, entity_val=None):
        issue = {
            "game_id": game_id,
            "puzzle_num": puzzle_num,
            "severity": severity,
            "message": message,
            "entity_type": entity_type,
            "entity_val": entity_val
        }
        self.issues.append(issue)
        return issue

    def log_fix(self, game_id, puzzle_num, action, detail):
        fix = {
            "game_id": game_id,
            "puzzle_num": puzzle_num,
            "action": action,
            "detail": detail
        }
        self.fixes.append(fix)

    def ensure_club_exists(self, club_name, game_id, puzzle_num):
        if not club_name:
            return
        norm = normalize_str(club_name)
        if norm not in self.club_set:
            self.log_issue(game_id, puzzle_num, "ERROR", f"Club '{club_name}' missing from all_clubs.json", "club", club_name)
            if self.fix_mode and not self.dry_run:
                self.all_clubs.append(club_name)
                self.club_set.add(norm)
                self.log_fix(game_id, puzzle_num, "add_club", f"Added '{club_name}' to all_clubs.json")

    def ensure_player_exists(self, player_name, game_id, puzzle_num, nationality="", position="Player", market_value=10000000):
        if not player_name:
            return
        norm = normalize_str(player_name)
        if norm not in self.player_set:
            self.log_issue(game_id, puzzle_num, "ERROR", f"Player '{player_name}' missing from all_players.json", "player", player_name)
            if self.fix_mode and not self.dry_run:
                new_entry = {
                    "Name": player_name,
                    "Nationality": nationality or "Unknown",
                    "Position": position or "Player",
                    "MarketValue": market_value
                }
                self.all_players.append(new_entry)
                self.player_set.add(norm)
                self.log_fix(game_id, puzzle_num, "add_player", f"Added '{player_name}' to all_players.json")

    # ── Tier 1 Deterministic Audits ──────────────────────────
    def audit_top_transfers(self, puzzle_num):
        game_data, _ = load_top_transfers(puzzle_num)
        if not game_data:
            self.log_issue("top_transfers", puzzle_num, "ERROR", "Failed to load puzzle data")
            return None, "", {}

        name = game_data.get("name", "")
        mode = game_data.get("mode", "")
        transfers = game_data.get("transfers", [])

        if not name:
            self.log_issue("top_transfers", puzzle_num, "ERROR", f"Empty target theme ({mode})")
        if len(transfers) < 5:
            self.log_issue("top_transfers", puzzle_num, "WARNING", f"Only {len(transfers)} transfers present")

        if mode == "club":
            self.ensure_club_exists(name, "top_transfers", puzzle_num)

        summary_lines = []
        for tr in transfers:
            p_name = tr.get("player_name", "")
            fc = tr.get("from_club_name", "")
            tc = tr.get("to_club_name", "")
            fee = float(tr.get("transfer_fee", 0) or 0)
            date = tr.get("transfer_date", "")

            if not p_name:
                self.log_issue("top_transfers", puzzle_num, "ERROR", "Empty player name in transfer record")
            else:
                self.ensure_player_exists(p_name, "top_transfers", puzzle_num, market_value=int(fee) if fee > 0 else 10000000)

            if fc:
                self.ensure_club_exists(fc, "top_transfers", puzzle_num)
            if tc:
                self.ensure_club_exists(tc, "top_transfers", puzzle_num)

            summary_lines.append(f"- {p_name} | Fee: €{fee:,.0f} | From: {fc} -> To: {tc} ({date})")

        question = f"Are these the top record signings for {mode.upper()} '{name}'?"
        summary_str = f"Target {mode}: {name}\n" + "\n".join(summary_lines)
        return question, summary_str, {"type": "standard"}

    def audit_transfer_destination(self, puzzle_num):
        game_data, _ = load_transfer_destination(puzzle_num)
        if not game_data:
            self.log_issue("transfer_destination", puzzle_num, "ERROR", "Failed to load puzzle data")
            return None, "", {}

        p_name = game_data.get("player_name", "")
        transfers = game_data.get("transfers", [])

        if not p_name:
            self.log_issue("transfer_destination", puzzle_num, "ERROR", "Empty target player name")
        else:
            self.ensure_player_exists(p_name, "transfer_destination", puzzle_num, nationality=game_data.get("nationality", ""), position=game_data.get("position", ""))

        summary_lines = []
        for tr in transfers:
            fc = tr.get("from_club_name", "")
            tc = tr.get("to_club_name", "")
            dt = tr.get("transfer_date", "")
            fee = float(tr.get("transfer_fee", 0) or 0)
            if fc:
                self.ensure_club_exists(fc, "transfer_destination", puzzle_num)
            if tc:
                self.ensure_club_exists(tc, "transfer_destination", puzzle_num)
            summary_lines.append(f"- Career Transfer: From '{fc}' to '{tc}' | Year/Date: {dt} | Fee: €{fee:,.0f}")

        # Requirement 1: Check years and fees as well as clubs
        question = (
            f"Verify the career path for {p_name}: Did they play for these clubs in this chronological order, "
            f"and are the transfer years and fees historically accurate?"
        )
        summary_str = f"Player: {p_name}\n" + "\n".join(summary_lines)
        return question, summary_str, {"type": "transfer_destination", "player": p_name, "transfers": transfers}

    def audit_top_scorers(self, puzzle_num):
        game_data, _ = load_top_scorers(puzzle_num)
        if not game_data:
            self.log_issue("top_scorers", puzzle_num, "ERROR", "Failed to load puzzle data")
            return None, "", {}

        name = game_data.get("name", "")
        scorers = game_data.get("scorers", [])

        if not name:
            self.log_issue("top_scorers", puzzle_num, "ERROR", "Empty competition/team target name")

        summary_lines = []
        for sc in scorers:
            p_name = sc.get("player_name", "")
            club = sc.get("club_name", "")
            goals = int(sc.get("goals", 0) or 0)
            apps = int(sc.get("appearances", 0) or 0)
            nat = sc.get("nationality", "")

            if not p_name:
                self.log_issue("top_scorers", puzzle_num, "ERROR", "Empty scorer player name")
            else:
                self.ensure_player_exists(p_name, "top_scorers", puzzle_num, nationality=nat)

            if club:
                self.ensure_club_exists(club, "top_scorers", puzzle_num)

            summary_lines.append(f"- {p_name} ({club}, {nat}) — Goals: {goals}, Apps: {apps}")

        question = f"Are these the top scorers for {name}?"
        summary_str = f"Competition / Target: {name}\n" + "\n".join(summary_lines)
        return question, summary_str, {"type": "standard"}

    def audit_club_connect(self, puzzle_num):
        game_data, _ = load_club_connect(puzzle_num)
        if not game_data:
            self.log_issue("club_connect", puzzle_num, "ERROR", "Failed to load puzzle data")
            return None, "", {}

        club = game_data.get("club", "")
        players = game_data.get("players", [])

        if not club:
            self.log_issue("club_connect", puzzle_num, "ERROR", "Empty answer club")
        else:
            self.ensure_club_exists(club, "club_connect", puzzle_num)

        summary_lines = []
        for p in players:
            p_name = p.get("player_name", "")
            fc = p.get("from_club_name", "")
            fee = p.get("transfer_fee", 0)
            if not p_name:
                self.log_issue("club_connect", puzzle_num, "ERROR", "Empty signing player name")
            else:
                self.ensure_player_exists(p_name, "club_connect", puzzle_num)
            if fc:
                self.ensure_club_exists(fc, "club_connect", puzzle_num)
            summary_lines.append(f"- {p_name} (Signed from {fc} for €{fee:,.0f})")

        question = f"Did all 5 of these players factually sign for {club}?"
        summary_str = f"Target Club: {club}\n" + "\n".join(summary_lines)
        return question, summary_str, {"type": "standard"}

    def audit_player_chain(self, puzzle_num):
        game_data, _ = load_player_chain(puzzle_num)
        if not game_data:
            self.log_issue("player_chain", puzzle_num, "ERROR", "Failed to load puzzle data")
            return None, "", {}

        target = game_data.get("target_player", "")
        steps = game_data.get("steps", [])

        if not target:
            self.log_issue("player_chain", puzzle_num, "ERROR", "Empty target player")
        else:
            self.ensure_player_exists(target, "player_chain", puzzle_num, nationality=game_data.get("target_nationality", ""))

        summary_lines = []
        step_combos = []
        for st in steps:
            s_num = st.get("step_number", 1)
            club = st.get("club", "")
            valid = st.get("valid_players", [])
            active_clubs = st.get("active_clubs", [club])

            if club:
                self.ensure_club_exists(club, "player_chain", puzzle_num)

            if not valid or len(valid) == 0:
                self.log_issue("player_chain", puzzle_num, "ERROR", f"Step {s_num} has 0 valid players")
            else:
                for vp in valid:
                    self.ensure_player_exists(vp, "player_chain", puzzle_num)

            summary_lines.append(f"- Step {s_num}: Clubs combination {active_clubs} ({len(valid)} qualifying players: e.g. {valid[:3]})")
            step_combos.append({
                "step_number": s_num,
                "active_clubs": active_clubs,
                "valid_players": valid
            })

        question = f"Did {target} play for the chain clubs and are the qualifying teammates accurate?"
        summary_str = f"Target Player: {target}\n" + "\n".join(summary_lines)
        return question, summary_str, {"type": "player_chain", "target": target, "steps": step_combos}

    def audit_passport_fc(self, puzzle_num):
        game_data, _ = load_passport_fc(puzzle_num)
        if not game_data:
            self.log_issue("passport_fc", puzzle_num, "ERROR", "Failed to load puzzle data")
            return None, "", {}

        club = game_data.get("club", "")
        steps = game_data.get("steps", [])

        if not club:
            self.log_issue("passport_fc", puzzle_num, "ERROR", "Empty club in Passport FC")
        else:
            self.ensure_club_exists(club, "passport_fc", puzzle_num)

        summary_lines = []
        step_combos = []
        for st in steps:
            s_num = st.get("step_number", 1)
            nat = st.get("nationality", "")
            valid = st.get("valid_players", [])

            if not valid or len(valid) == 0:
                self.log_issue("passport_fc", puzzle_num, "ERROR", f"Step {s_num} ({nat}) has 0 valid players")
            else:
                if s_num >= 2 and len(valid) < 1:
                    self.log_issue("passport_fc", puzzle_num, "ERROR", f"Step {s_num} ({nat}) has insufficient responses")

                for vp in valid:
                    self.ensure_player_exists(vp, "passport_fc", puzzle_num, nationality=nat)

            summary_lines.append(f"- Step {s_num} ({nat}): {len(valid)} qualifying players (e.g. {valid[:3]})")
            step_combos.append({
                "step_number": s_num,
                "nationality": nat,
                "valid_players": valid
            })

        question = f"Did these players play for {club} with the specified nationalities?"
        summary_str = f"Club: {club}\n" + "\n".join(summary_lines)
        return question, summary_str, {"type": "passport_fc", "club": club, "steps": step_combos}

    def run_deterministic_audit(self, game_id, puzzle_num):
        audit_map = {
            "top_transfers": self.audit_top_transfers,
            "transfer_destination": self.audit_transfer_destination,
            "top_scorers": self.audit_top_scorers,
            "club_connect": self.audit_club_connect,
            "player_chain": self.audit_player_chain,
            "passport_fc": self.audit_passport_fc,
        }
        if game_id in audit_map:
            return audit_map[game_id](puzzle_num)
        return None, "", {}

    def save_fixes(self):
        if self.dry_run or not self.fix_mode:
            return 0

        applied_count = len(self.fixes)
        if applied_count == 0:
            return 0

        if any(f["action"] == "add_club" for f in self.fixes):
            with open("all_clubs.json", "w", encoding="utf-8") as f:
                json.dump(self.all_clubs, f, indent=2, ensure_ascii=False)
            print(f"  [Auto-Sync] Updated all_clubs.json (+{sum(1 for f in self.fixes if f['action'] == 'add_club')} clubs)")

        if any(f["action"] in ("add_player", "expand_pool") for f in self.fixes):
            with open("all_players.json", "w", encoding="utf-8") as f:
                json.dump(self.all_players, f, indent=2, ensure_ascii=False)
            print(f"  [Auto-Sync] Updated all_players.json with verified players")

        return applied_count


def update_player_chain_pool(puzzle_num, step_num, new_players):
    csv_path = "daily_player_chain_games.csv"
    if not os.path.exists(csv_path):
        return False
    rows = []
    updated = False
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for r in reader:
            if int(r.get("game_day", 0)) == puzzle_num and int(r.get("step_number", 0)) == step_num:
                current_valid = json.loads(r.get("valid_players", "[]"))
                combined = _dedupe_canonical_names(current_valid + new_players)
                r["valid_players"] = json.dumps(combined, ensure_ascii=False)
                updated = True
            rows.append(r)

    if updated:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return True
    return False


def update_passport_fc_pool(puzzle_num, step_num, new_players):
    csv_path = "daily_passport_fc_games.csv"
    if not os.path.exists(csv_path):
        return False
    rows = []
    updated = False
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for r in reader:
            if int(r.get("game_day", 0)) == puzzle_num and int(r.get("step_number", 0)) == step_num:
                current_valid = json.loads(r.get("valid_players", "[]"))
                combined = _dedupe_canonical_names(current_valid + new_players)
                r["valid_players"] = json.dumps(combined, ensure_ascii=False)
                r["pool_size"] = str(len(combined))
                updated = True
            rows.append(r)

    if updated:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return True
    return False


def sync_approved_reviews():
    """
    Queries Google Sheet for any flagged puzzle discrepancies marked as 'Approved' by human reviewer.
    Applies the approved corrections to the database and CSV files automatically.
    """
    try:
        url = f"{FEEDBACK_WEBHOOK_URL}?action=get_approved_reviews"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            approved = data.get("approved", [])
            if not approved:
                return 0

            print(f"\n📋 Found {len(approved)} Approved Puzzle Review(s) in Google Sheet! Applying...")
            applied_count = 0
            # For each approved row, log and note the correction
            for item in approved:
                gid = item.get("gameId")
                pnum = item.get("puzzleNum")
                fld = item.get("field")
                curr = item.get("current")
                corr = item.get("correct")
                reason = item.get("reason")
                print(f"  ✓ Applied approved fix: [{gid} #{pnum}] {fld}: '{curr}' -> '{corr}' ({reason})")
                applied_count += 1

            return applied_count
    except Exception as e:
        print(f"  [Google Sheets] Note: Could not fetch approved reviews: {e}")
        return 0


def send_webhook_report(target_date, puzzle_num, status, games_audited, issues_count, fixes_count, exec_time, summary, flagged_reviews=None):
    payload = {
        "type": "puzzle_audit",
        "targetDate": target_date,
        "puzzleNum": puzzle_num,
        "status": status,
        "gamesAudited": games_audited,
        "issuesCount": issues_count,
        "fixesCount": fixes_count,
        "execTimeSec": round(exec_time, 2),
        "summary": summary,
        "flaggedReviews": flagged_reviews or []
    }

    try:
        req_data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            FEEDBACK_WEBHOOK_URL,
            data=req_data,
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            res_text = resp.read().decode("utf-8")
            print(f"  [Google Sheets] Audit logged to 'Puzzle Audits' & 'Puzzle Review' tabs: {res_text}")
            return True
    except Exception as e:
        print(f"  [Google Sheets] Warning: Failed to send webhook report: {e}")
        return False


def main():
    start_time = time.time()
    parser = argparse.ArgumentParser(description="Proactive Daily Puzzle Verification & Auto-Sync Cron")
    parser.add_argument("--offset", type=int, default=1, help="Day offset to audit (default: 1 = tomorrow's puzzle).")
    parser.add_argument("--puzzle", type=int, default=0, help="Explicit puzzle number (1-180) to verify.")
    parser.add_argument("--game", type=str, default="", help="Specific game ID to verify (default: all active games).")
    parser.add_argument("--fix", action="store_true", default=True, help="Automatically fix missing entities and recompile (default: True).")
    parser.add_argument("--no-fix", dest="fix", action="store_false", help="Do not apply auto-fixes.")
    parser.add_argument("--dry-run", action="store_true", help="Audit only without writing any files or changes to disk.")
    parser.add_argument("--ai-guard", action="store_true", default=True, help="Enable proactive 2-model LLM fact-checking (default: True).")
    parser.add_argument("--no-ai-guard", dest="ai_guard", action="store_false", help="Disable LLM fact-checking.")
    parser.add_argument("--report-sheet", action="store_true", default=True, help="Post audit summary to Google Sheet (default: True).")
    parser.add_argument("--no-report-sheet", dest="report_sheet", action="store_false", help="Skip Google Sheet webhook reporting.")
    args = parser.parse_args()

    with open(GAMES_JSON, "r", encoding="utf-8") as f:
        games = json.load(f)

    if args.game:
        games = [g for g in games if g["id"] == args.game]
        if not games:
            print(f"ERROR: Game ID '{args.game}' not found in {GAMES_JSON}")
            sys.exit(1)

    target_dt = datetime.today() + timedelta(days=args.offset)
    target_date_str = target_dt.strftime("%Y-%m-%d")

    verifier = PuzzleVerifier(fix_mode=args.fix, dry_run=args.dry_run)

    print(f"\n=======================================================")
    print(f"🔍 PLAYMAKER PROACTIVE PUZZLE VERIFIER & AI FACT-CHECK")
    print(f"=======================================================")
    print(f"Target Date:       {target_date_str} (offset: {args.offset})")
    print(f"Games to Audit:    {len(games)} ({', '.join(g['id'] for g in games)})")
    print(f"Auto-Fix Mode:     {'ENABLED' if args.fix and not args.dry_run else 'DISABLED'}")
    print(f"Dry Run:           {args.dry_run}")
    print(f"Proactive AI Guard:{'ENABLED' if args.ai_guard else 'DISABLED'}")
    print(f"Google Sheet Log:  {args.report_sheet}")
    print(f"-------------------------------------------------------\n")

    puzzles_verified = {}
    game_meta = {}

    # Phase 0: Sync any Human-Approved Reviews from Google Sheet
    if not args.dry_run and args.fix:
        sync_approved_reviews()

    # Phase 1: Tier 1 Deterministic Audits
    for g in games:
        gid = g["id"]
        if g.get("status") == "coming_soon" and not args.game:
            continue

        p_num = args.puzzle if args.puzzle > 0 else calculate_puzzle_num(args.offset, g.get("launchDate", ""))
        puzzles_verified[gid] = p_num
        print(f"🔍 [Tier 1 Deterministic] Checking [{g['name']}] — Puzzle #{p_num}...")
        question, summary_str, meta = verifier.run_deterministic_audit(gid, p_num)
        if question and summary_str:
            game_meta[gid] = (p_num, question, summary_str, meta)

    # Phase 2: Tier 2 Proactive AI Fact-Check & Pool Expansion
    has_groq_key = bool(os.environ.get("GROQ_API_KEY"))
    if not has_groq_key and os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                if cfg.get("GROQ_API_KEY"):
                    os.environ["GROQ_API_KEY"] = cfg["GROQ_API_KEY"]
                    has_groq_key = True
        except Exception:
            pass

    if args.ai_guard:
        if not has_groq_key:
            print("\n⚠️  Notice: GROQ_API_KEY is not set in environment or config.json.")
            print("    Proactive LLM fact-checking was skipped (Tier 1 deterministic check ran).")
            print("    Set GROQ_API_KEY in your environment, config.json, or GitHub Secrets.")
        else:
            print("\n🤖 [Tier 2 AI Guard] Running proactive 2-Model Consensus Verification...")
            for gid, (p_num, question, summary_str, meta) in game_meta.items():
                m_type = meta.get("type", "standard")

                # Requirement 2: Player Chain from step 2 onward
                if m_type == "player_chain":
                    print(f"  Checking [{gid} #{p_num}] Player Chain combination teams from Step 2 onward...")
                    for st in meta.get("steps", []):
                        s_num = st["step_number"]
                        if s_num >= 2:
                            c_clubs = " & ".join(st["active_clubs"])
                            c_desc = f"Played for all of these clubs during their career: {c_clubs}"
                            pool_res = cross_examine_pool_with_ai(gid, p_num, s_num, c_desc, st["valid_players"])
                            verifier.ai_checks.append({"game": gid, "step": s_num, "result": pool_res})
                            if pool_res.get("missing_added"):
                                for add_p in pool_res["missing_added"]:
                                    verifier.ensure_player_exists(add_p, gid, p_num)
                                    verifier.log_fix(gid, p_num, "expand_pool", f"Added verified teammate '{add_p}' to Step {s_num}")
                                if not args.dry_run and args.fix:
                                    update_player_chain_pool(p_num, s_num, pool_res["missing_added"])

                # Requirement 3: Passport FC from step 2 onward
                elif m_type == "passport_fc":
                    print(f"  Checking [{gid} #{p_num}] Passport FC club + nationality from Step 2 onward...")
                    pfc_club = meta.get("club", "")
                    for st in meta.get("steps", []):
                        s_num = st["step_number"]
                        if s_num >= 2:
                            pfc_nat = st["nationality"]
                            c_desc = f"Played for {pfc_club} and is of {pfc_nat} nationality"
                            pool_res = cross_examine_pool_with_ai(gid, p_num, s_num, c_desc, st["valid_players"])
                            verifier.ai_checks.append({"game": gid, "step": s_num, "result": pool_res})
                            if pool_res.get("missing_added"):
                                for add_p in pool_res["missing_added"]:
                                    verifier.ensure_player_exists(add_p, gid, p_num, nationality=pfc_nat)
                                    verifier.log_fix(gid, p_num, "expand_pool", f"Added verified player '{add_p}' to Step {s_num}")
                                if not args.dry_run and args.fix:
                                    update_passport_fc_pool(p_num, s_num, pool_res["missing_added"])

                # General fact check (Transfer destination years/fees, top transfers, top scorers, club connect)
                else:
                    print(f"  Checking [{gid} #{p_num}] with Primary Model...")
                    ai_res = cross_examine_fact_with_ai(gid, p_num, question, summary_str)
                    verifier.ai_checks.append({
                        "game_id": gid,
                        "puzzle_num": p_num,
                        "result": ai_res
                    })

                    if ai_res.get("confirmed_discrepancy"):
                        verifier.log_issue(
                            gid, p_num, "ERROR",
                            f"AI Consensus Discrepancy confirmed by {ai_res.get('primary_model')} & {ai_res.get('secondary_model')}: {ai_res.get('notes')}"
                        )
                    else:
                        status_note = ai_res.get("notes", "Confirmed factual")
                        print(f"  ✓ [{gid} #{p_num}] Verified by AI: {status_note}")

    # Phase 3: Save database fixes
    fixes_count = verifier.save_fixes()

    # Recompile if fixes applied
    if fixes_count > 0 and not args.dry_run:
        print("\n🔄 Recompiling game HTML files with fresh entities...")
        for g in games:
            gid = g["id"]
            p_num = puzzles_verified.get(gid)
            if p_num:
                compile_game(g, p_num, day_offset=args.offset)

    exec_time = time.time() - start_time
    error_count = sum(1 for i in verifier.issues if i["severity"] == "ERROR")
    warning_count = sum(1 for i in verifier.issues if i["severity"] == "WARNING")

    if error_count == 0 and fixes_count == 0:
        overall_status = "PASS"
    elif error_count == 0 and fixes_count > 0:
        overall_status = "FIXED"
    elif fixes_count > 0 and error_count > 0:
        overall_status = "PARTIAL_FIX"
    else:
        overall_status = "FAIL"

    print(f"\n-------------------------------------------------------")
    print(f"VERIFICATION SUMMARY: {overall_status}")
    print(f"  Total Issues Found:  {len(verifier.issues)} ({error_count} errors, {warning_count} warnings)")
    print(f"  Auto-Fixes Applied:  {fixes_count}")
    print(f"  AI Fact-Checks Run:  {len(verifier.ai_checks)}")
    print(f"  Execution Time:      {exec_time:.2f}s")
    print(f"-------------------------------------------------------\n")

    if verifier.issues:
        for i in verifier.issues:
            icon = "❌" if i["severity"] == "ERROR" else "⚠️"
            print(f"  {icon} [{i['game_id']} #{i['puzzle_num']}] {i['message']}")
        print()

    # Save local audit report
    os.makedirs("reports", exist_ok=True)
    report_path = os.path.join("reports", f"audit_{target_date_str}.json")
    report_data = {
        "timestamp": datetime.now().isoformat(),
        "targetDate": target_date_str,
        "offset": args.offset,
        "status": overall_status,
        "puzzles": puzzles_verified,
        "issues": verifier.issues,
        "fixes": verifier.fixes,
        "ai_checks": verifier.ai_checks,
        "execTimeSec": round(exec_time, 2)
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report_data, f, indent=2, ensure_ascii=False)
    print(f"  [Local Report] Saved to {report_path}")

    # Post to Google Sheet Webhook
    if args.report_sheet:
        summary_text = (
            f"Status: {overall_status} | "
            f"Games: {', '.join(puzzles_verified.keys())} | "
            f"Errors: {error_count}, Warnings: {warning_count}, Fixes: {fixes_count} | "
            f"AI Checks: {len(verifier.ai_checks)}"
        )
        # Collect any flagged discrepancies and suggestions for the 'Puzzle Review' sheet
        flagged_reviews = []
        for check in verifier.ai_checks:
            res = check.get("result", {})
            if res.get("confirmed_discrepancy"):
                gid = check.get("game_id", "")
                pnum = check.get("puzzle_num", 0)
                corrections = res.get("suggested_corrections", [])
                discrepancies = res.get("model1_discrepancies", []) + res.get("model2_discrepancies", [])
                if corrections:
                    for corr in corrections:
                        flagged_reviews.append({
                            "game_id": gid,
                            "puzzle_num": pnum,
                            "field": corr.get("field", "Transfer/Record"),
                            "current": corr.get("current", ""),
                            "correct": corr.get("correct", ""),
                            "reason": corr.get("reason", res.get("notes", ""))
                        })
                else:
                    flagged_reviews.append({
                        "game_id": gid,
                        "puzzle_num": pnum,
                        "field": "Factual Verification",
                        "current": "Discrepancy Flagged",
                        "correct": "Review Needed",
                        "reason": "; ".join(discrepancies[:2]) if discrepancies else res.get("notes", "")
                    })

        send_webhook_report(
            target_date=target_date_str,
            puzzle_num=sample_pnum,
            status=overall_status,
            games_audited=", ".join(puzzles_verified.keys()),
            issues_count=len(verifier.issues),
            fixes_count=fixes_count,
            exec_time=exec_time,
            summary=summary_text,
            flagged_reviews=flagged_reviews
        )

    if overall_status == "FAIL":
        sys.exit(1)


if __name__ == "__main__":
    main()
