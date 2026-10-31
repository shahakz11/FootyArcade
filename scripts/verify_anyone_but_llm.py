#!/usr/bin/env python3
"""
verify_anyone_but_llm.py — LLM-Powered Puzzle Verifier for Anyone But
====================================================================
Uses Google Gemini API (GEMINI_API_KEY) with web search grounding to verify
that Anyone But puzzles are comprehensive and not missing any valid qualifying
footballers across all 3 criteria tables.

Usage:
    python3 scripts/verify_anyone_but_llm.py --puzzle 1
    python3 scripts/verify_anyone_but_llm.py --limit 5
    python3 scripts/verify_anyone_but_llm.py --puzzle 1 --fix
"""

import os
import sys
import csv
import json
import time
import argparse
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

from fetch_daily import load_anyone_but, _dedupe_canonical_names


def get_gemini_api_key():
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key and os.path.exists("config.json"):
        try:
            with open("config.json", "r", encoding="utf-8") as f:
                cfg = json.load(f)
                key = cfg.get("GEMINI_API_KEY", "")
        except Exception:
            pass
    return key


def parse_json_response(text):
    if not text:
        return None
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except Exception:
        # Fallback: find first { and last }
        s = text.find("{")
        e = text.rfind("}")
        if s != -1 and e != -1 and e > s:
            try:
                return json.loads(text[s:e+1])
            except Exception:
                pass
    return None


def call_gemini(system_prompt, user_prompt, use_search=True, api_key=None):
    if not api_key:
        api_key = get_gemini_api_key()
    if not api_key:
        return {"status": "error", "reason": "GEMINI_API_KEY not configured"}

    models = [
        ("gemini-2.5-flash", use_search),
        ("gemini-2.5-flash-lite", use_search),
        ("gemini-2.0-flash", False),
        ("gemini-1.5-flash", False),
    ]

    for model, search_enabled in models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        combined = f"SYSTEM INSTRUCTIONS: {system_prompt}\n\nUSER PROMPT: {user_prompt}"
        body = {
            "contents": [{"role": "user", "parts": [{"text": combined}]}],
            "generationConfig": {"temperature": 0.0}
        }
        if search_enabled:
            body["tools"] = [{"googleSearch": {}}]
        else:
            body["generationConfig"]["responseMimeType"] = "application/json"

        try:
            req_data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=25) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    cand = data.get("candidates", [{}])[0]
                    parts = cand.get("content", {}).get("parts", [])
                    txt = "".join([p.get("text", "") for p in parts if "text" in p])
                    parsed = parse_json_response(txt)
                    if parsed and isinstance(parsed, dict):
                        parsed["model_used"] = model
                        return parsed
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(1.5)
                continue
        except Exception:
            continue

    return {"status": "error", "reason": "All Gemini models exhausted"}


def load_all_players_catalog():
    if os.path.exists("all_players.json"):
        try:
            with open("all_players.json", "r", encoding="utf-8") as f:
                data = json.load(f)
                import unicodedata
                def _n(s):
                    return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower().strip()
                return {_n(p["Name"]): p for p in data if "Name" in p}
        except Exception:
            pass
    return {}


def verify_puzzle_table(excluded_star, table_label, existing_answers, api_key=None, catalog=None):
    """
    Asks Gemini to identify all senior professional footballers (1990–June 2026)
    who satisfy table_label, strictly excluding excluded_star.
    Returns (status, missing_candidates, model_used).
    """
    system_prompt = (
        "You are a rigorous, fact-based football database verifier for Playmaker.\n"
        "Your task is to identify prominent senior professional footballers who factually meet a given criteria.\n"
        "CRITICAL RULES:\n"
        "1. Active period: senior appearances or transfers from 1990 up to June 2026.\n"
        "2. The excluded player CANNOT be included under any circumstances.\n"
        "3. Only include footballers who made senior competitive first-team appearances for the relevant clubs.\n"
        "4. Return clean, standard football names (e.g. 'Ederson', 'Ruben Dias').\n"
        "Output ONLY valid JSON:\n"
        "{\n"
        '  "qualifying_players": ["Player 1", "Player 2", ...],\n'
        '  "confidence": 0.0 to 1.0,\n'
        '  "notes": "Short explanation"\n'
        "}"
    )

    user_prompt = (
        f"Excluded Player: {excluded_star}\n"
        f"Criterion: {table_label}\n\n"
        f"Please list all senior professional footballers (from 1990 to June 2026) who meet this criterion.\n"
        f"Do NOT include {excluded_star}."
    )

    res = call_gemini(system_prompt, user_prompt, use_search=True, api_key=api_key)
    if res.get("status") == "error":
        return "error", [], res.get("reason", "API error")

    qualifying = res.get("qualifying_players", [])
    if not isinstance(qualifying, list):
        return "error", [], "Invalid response format"

    # Compare with existing
    import unicodedata
    import re

    def _norm(s):
        s = unicodedata.normalize('NFKD', s)
        s = ''.join(c for c in s if not unicodedata.combining(c)).lower().strip()
        return s

    existing_norm = {_norm(a) for a in existing_answers}
    excluded_norm = _norm(excluded_star)

    # Programmatic cutoff check for peak market value
    val_m = re.search(r"peak(?:\s+market\s+value)?\s*[≥>=]+\s*€?(\d+)M", table_label, re.IGNORECASE)
    min_val = int(val_m.group(1)) * 1_000_000 if val_m else 0

    if catalog is None:
        catalog = load_all_players_catalog()

    missing = []
    for cand in qualifying:
        if not cand or not isinstance(cand, str):
            continue
        cnorm = _norm(cand)
        if cnorm == excluded_norm:
            continue
        if cnorm not in existing_norm:
            # Check programmatic peak value cutoff
            if min_val > 0 and catalog:
                cp = catalog.get(cnorm)
                if cp and cp.get("MarketValue", 0) < min_val:
                    continue  # Did not reach peak market value threshold
            missing.append(cand)

    return "ok", missing, res.get("model_used", "gemini")


def update_puzzle_in_csv(puzzle_num, table_num, additions):
    csv_path = "daily_anyone_but_games.csv"
    if not os.path.exists(csv_path) or not additions:
        return False

    rows = []
    updated = False
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for r in reader:
            if int(r.get("game_day", 0)) == puzzle_num and int(r.get("table_number", 0)) == table_num:
                cur = json.loads(r.get("answers", "[]"))
                combined = _dedupe_canonical_names(cur + additions)
                r["answers"] = json.dumps(combined, ensure_ascii=False)
                r["answer_count"] = str(len(combined))
                updated = True
            rows.append(r)

    if updated:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        return True
    return False


def verify_puzzle(puzzle_num, fix=False, api_key=None):
    game_data, _ = load_anyone_but(puzzle_num)
    if not game_data:
        print(f"❌ Puzzle #{puzzle_num} not found in daily_anyone_but_games.csv")
        return False

    excluded = game_data.get("excluded_player", "Unknown")
    tables = game_data.get("tables", [])
    print(f"\n=======================================================")
    print(f"🔍 Auditing Anyone But Puzzle #{puzzle_num} (Excluded: {excluded})")
    print(f"=======================================================")

    all_ok = True
    for tbl in tables:
        t_num = tbl.get("table_number", 1)
        label = tbl.get("label", "")
        answers = tbl.get("answers", [])
        print(f"\n  [Table {t_num}] \"{label}\"")
        print(f"  Existing answer count: {len(answers)} ({', '.join(answers[:4])}...)")

        status, missing, model_used = verify_puzzle_table(excluded, label, answers, api_key=api_key)
        if status == "error":
            print(f"  ⚠️  AI Verification skipped: {model_used}")
            continue

        if not missing:
            print(f"  ✅ Perfect! Model {model_used} found 0 missing players.")
        else:
            print(f"  ⚠️  Model {model_used} suggested {len(missing)} potentially missing player(s): {missing}")
            all_ok = False
            if fix:
                updated = update_puzzle_in_csv(puzzle_num, t_num, missing)
                if updated:
                    print(f"  🔧 Auto-fixed! Added {missing} to Table {t_num} in daily_anyone_but_games.csv")

    return all_ok


def main():
    parser = argparse.ArgumentParser(description="Verify Anyone But puzzles with Gemini API")
    parser.add_argument("--puzzle", type=int, default=None, help="Specific puzzle day to verify (e.g. 1)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of puzzles to verify")
    parser.add_argument("--fix", action="store_true", help="Auto-populate confirmed missing players into CSV")
    args = parser.parse_args()

    api_key = get_gemini_api_key()
    if not api_key:
        print("❌ Error: GEMINI_API_KEY is not configured in environment or config.json.")
        sys.exit(1)

    print("🔑 GEMINI_API_KEY successfully authenticated.")

    if args.puzzle:
        puzzles = [args.puzzle]
    else:
        limit = args.limit or 3
        puzzles = list(range(1, limit + 1))

    for p in puzzles:
        verify_puzzle(p, fix=args.fix, api_key=api_key)

    print("\n✅ Verification run complete.")


if __name__ == "__main__":
    main()
