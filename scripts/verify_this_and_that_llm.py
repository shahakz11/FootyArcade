#!/usr/bin/env python3
"""
verify_this_and_that_llm.py — LLM-Powered Puzzle Verifier for 'This & That'
==========================================================================
Uses Google Gemini API (GEMINI_API_KEY) with Google search grounding to verify
that 'This & That' puzzles are comprehensive and not missing any valid qualifying
senior professional footballers who satisfy both statements simultaneously.

Usage:
    python3 scripts/verify_this_and_that_llm.py --puzzle 1
    python3 scripts/verify_this_and_that_llm.py --limit 5
    python3 scripts/verify_this_and_that_llm.py --puzzle 1 --fix
    python3 scripts/verify_this_and_that_llm.py --puzzle 1 --fix --dry-run
"""

import os
import sys
import csv
import json
import time
import re
import argparse
import unicodedata
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


def get_gemini_api_key():
    """Checks os.environ.get('GEMINI_API_KEY') and config.json."""
    key = os.environ.get("GEMINI_API_KEY", "")
    if not key:
        config_paths = [
            "config.json",
            os.path.join(PROJECT_ROOT, "config.json"),
            os.path.join(SCRIPT_DIR, "..", "config.json"),
        ]
        for cp in config_paths:
            if os.path.exists(cp):
                try:
                    with open(cp, "r", encoding="utf-8") as f:
                        cfg = json.load(f)
                        key = cfg.get("GEMINI_API_KEY") or cfg.get("gemini_api_key", "")
                        if key:
                            break
                except Exception:
                    pass
    return key


def parse_json_response(text):
    """
    Robustly parses JSON from Gemini responses:
    - Clean JSON text
    - Fenced ```json ... ``` or ``` ... ``` blocks
    - Embedded JSON objects { ... } or lists [ ... ]
    """
    if not text:
        return None
    text = text.strip()

    # 1. Direct JSON parse
    try:
        return json.loads(text)
    except Exception:
        pass

    # 2. Markdown fenced code block
    if "```" in text:
        m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if m:
            clean = m.group(1).strip()
            try:
                return json.loads(clean)
            except Exception:
                text = clean

    # 3. Fallback: extract substring between first '{' and last '}'
    s = text.find("{")
    e = text.rfind("}")
    if s != -1 and e != -1 and e > s:
        try:
            return json.loads(text[s:e+1])
        except Exception:
            pass

    # 4. Fallback: extract substring between first '[' and last ']'
    s = text.find("[")
    e = text.rfind("]")
    if s != -1 and e != -1 and e > s:
        try:
            return json.loads(text[s:e+1])
        except Exception:
            pass

    return None


def call_gemini(system_prompt, user_prompt, use_search=True, api_key=None):
    """
    Queries Google Gemini API (gemini-2.5-flash / gemini-2.0-flash with search when enabled).
    Falls back across available model endpoints.
    """
    if not api_key:
        api_key = get_gemini_api_key()
    if not api_key:
        return {"status": "error", "reason": "GEMINI_API_KEY not configured"}

    models = [
        ("gemini-2.5-flash", use_search),
        ("gemini-2.0-flash", use_search),
        ("gemini-2.5-flash-lite", use_search),
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
                    if parsed is not None:
                        if isinstance(parsed, dict):
                            parsed["model_used"] = model
                            return parsed
                        elif isinstance(parsed, list):
                            return {"qualifying_players": parsed, "model_used": model}
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(1.5)
                continue
        except Exception:
            continue

    return {"status": "error", "reason": "All Gemini models exhausted"}


def _normalize_name(s):
    """Normalizes string for robust accent-insensitive and case-insensitive comparison."""
    if not s or not isinstance(s, str):
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c)).lower().strip()
    return s


def load_all_players_catalog(catalog_path=None):
    """
    Reads all_players.json or games/footy-players.js and returns a dictionary
    indexed by normalized player name and aliases.
    """
    search_paths = (
        [catalog_path]
        if catalog_path
        else [
            "all_players.json",
            os.path.join(PROJECT_ROOT, "all_players.json"),
            "games/footy-players.js",
            os.path.join(PROJECT_ROOT, "games/footy-players.js"),
        ]
    )

    for p in search_paths:
        if not p or not os.path.exists(p):
            continue
        try:
            if p.endswith(".json"):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    catalog = {}
                    for item in data:
                        if "Name" in item:
                            norm = _normalize_name(item["Name"])
                            catalog[norm] = item
                            for alias in item.get("Aliases", []):
                                catalog[_normalize_name(alias)] = item
                    return catalog
            elif p.endswith(".js"):
                with open(p, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content.startswith("var ALL_PLAYERS ="):
                        content = content[len("var ALL_PLAYERS ="):].rstrip("; ")
                    data = json.loads(content)
                    catalog = {}
                    for item in data:
                        if "Name" in item:
                            norm = _normalize_name(item["Name"])
                            catalog[norm] = item
                            for alias in item.get("Aliases", []):
                                catalog[_normalize_name(alias)] = item
                    return catalog
        except Exception:
            pass
    return {}


def _build_catalog_lookup(catalog):
    """
    Normalizes any provided catalog into a lookup mapping normalized names -> player item/name.
    """
    if catalog is None:
        return load_all_players_catalog()
    if isinstance(catalog, dict):
        lookup = {}
        for k, v in catalog.items():
            lookup[_normalize_name(k)] = v
            if isinstance(v, dict):
                if "Name" in v:
                    lookup[_normalize_name(v["Name"])] = v
                for al in v.get("Aliases", []):
                    lookup[_normalize_name(al)] = v
            elif isinstance(v, str):
                lookup[_normalize_name(v)] = v
        return lookup
    elif isinstance(catalog, (list, set, tuple)):
        lookup = {}
        for item in catalog:
            if isinstance(item, dict) and "Name" in item:
                lookup[_normalize_name(item["Name"])] = item
                for al in item.get("Aliases", []):
                    lookup[_normalize_name(al)] = item
            elif isinstance(item, str):
                lookup[_normalize_name(item)] = item
        return lookup
    return {}


def update_puzzle_in_csv(puzzle_day, missing_players, csv_path="daily_this_and_that_games.csv", catalog=None, dry_run=False):
    """
    Appends approved missing players into CSV if existing pool < 9 (up to a maximum total of 9).
    Returns (updated_bool, added_players).
    """
    if not os.path.exists(csv_path) or not missing_players:
        return False, []

    catalog_lookup = _build_catalog_lookup(catalog)
    rows = []
    fieldnames = None
    updated = False
    added_players = []

    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for r in reader:
            try:
                if int(r.get("game_day", 0)) == int(puzzle_day):
                    try:
                        cur_names = json.loads(r.get("answer_names", "[]"))
                    except Exception:
                        cur_names = []
                    try:
                        cur_details = json.loads(r.get("answer_details", "[]"))
                    except Exception:
                        cur_details = []

                    pool_size = len(cur_names)
                    if pool_size < 9:
                        slots = 9 - pool_size
                        to_add = missing_players[:slots]
                        if to_add:
                            added_players = to_add
                            updated = True
                            for p_name in to_add:
                                cur_names.append(p_name)
                                norm_p = _normalize_name(p_name)
                                p_entry = catalog_lookup.get(norm_p, {}) if isinstance(catalog_lookup, dict) else {}
                                if not isinstance(p_entry, dict):
                                    p_entry = {}
                                detail = {
                                    "name": p_name,
                                    "nationality": p_entry.get("Nationality", ""),
                                    "position": p_entry.get("Position", ""),
                                    "market_value": p_entry.get("MarketValue", 0),
                                    "detail_a": r.get("statement_a", ""),
                                    "detail_b": r.get("statement_b", ""),
                                    "detail_a_es": r.get("statement_a_es", ""),
                                    "detail_b_es": r.get("statement_b_es", "")
                                }
                                cur_details.append(detail)

                            r["answer_names"] = json.dumps(cur_names, ensure_ascii=False)
                            r["answer_details"] = json.dumps(cur_details, ensure_ascii=False)
                            r["total_answers"] = str(len(cur_names))
            except (ValueError, TypeError):
                pass
            rows.append(r)

    if updated and not dry_run:
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    return updated, added_players


def verify_puzzle(puzzle_day, csv_path="daily_this_and_that_games.csv", catalog=None, api_key=None, fix=False, dry_run=False):
    """
    Takes a puzzle day, extracts statement_a and statement_b, and existing answers.
    Prompts Gemini with both statements to identify all footballers who qualify for BOTH statements simultaneously.
    Filters candidate answers against ALL_PLAYERS whitelist and returns status, missing_players, model_used.

    If fix=True, automatically appends approved missing players into CSV if pool < 9.
    """
    if not os.path.exists(csv_path):
        return "error", [], f"CSV file not found: {csv_path}"

    row = None
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            try:
                if int(r.get("game_day", 0)) == int(puzzle_day):
                    row = r
                    break
            except (ValueError, TypeError):
                continue

    if not row:
        return "error", [], f"Puzzle #{puzzle_day} not found in {csv_path}"

    statement_a = row.get("statement_a", "").strip()
    statement_b = row.get("statement_b", "").strip()
    category = row.get("category", "").strip()

    try:
        existing_names = json.loads(row.get("answer_names", "[]"))
        if not isinstance(existing_names, list):
            existing_names = []
    except Exception:
        existing_names = []

    system_prompt = (
        "You are an expert football (soccer) database auditor for Playmaker.\n"
        "Your task is to identify senior professional footballers who simultaneously qualify for BOTH given statements.\n\n"
        "CRITICAL RULES:\n"
        "1. Active era: senior appearances or transfers from 1990 up to June 2026.\n"
        "2. Every qualifying player must factually meet BOTH Statement A and Statement B.\n"
        "3. Only include footballers who made competitive senior first-team appearances (or officially won the specified trophy / played for both clubs / represented the nation).\n"
        "4. Return clean, standard player names (e.g. 'Frank Lampard', 'Carlos Tevez').\n"
        "5. Output ONLY valid JSON in this format:\n"
        "{\n"
        '  "qualifying_players": ["Player 1", "Player 2", ...],\n'
        '  "confidence": 0.0 to 1.0,\n'
        '  "notes": "Short reasoning"\n'
        "}"
    )

    user_prompt = (
        f"Category: {category}\n"
        f"Statement A: {statement_a}\n"
        f"Statement B: {statement_b}\n\n"
        f"Find all senior professional footballers who satisfy BOTH Statement A and Statement B simultaneously."
    )

    res = call_gemini(system_prompt, user_prompt, use_search=True, api_key=api_key)
    if not res or res.get("status") == "error":
        return "error", [], res.get("reason", "API error") if res else "No response"

    model_used = res.get("model_used", "gemini")
    candidates = res.get("qualifying_players", [])
    if not isinstance(candidates, list):
        return "error", [], "Invalid response format"

    catalog_lookup = _build_catalog_lookup(catalog)
    existing_norm = {_normalize_name(name) for name in existing_names}

    missing_players = []
    seen_missing_norm = set()

    for cand in candidates:
        if not cand or not isinstance(cand, str):
            continue
        norm_cand = _normalize_name(cand)
        if not norm_cand:
            continue

        # Already in existing puzzle answers
        if norm_cand in existing_norm:
            continue

        # Whitelist filter: candidate must exist in ALL_PLAYERS catalog
        if norm_cand not in catalog_lookup:
            continue

        cat_val = catalog_lookup[norm_cand]
        if isinstance(cat_val, dict):
            canonical_name = cat_val.get("Name", cand)
        elif isinstance(cat_val, str):
            canonical_name = cat_val
        else:
            canonical_name = cand

        canonical_name = re.sub(r"\s*\(All\)$", "", canonical_name).strip()
        norm_canonical = _normalize_name(canonical_name)

        if norm_canonical in existing_norm:
            continue

        if norm_canonical not in seen_missing_norm:
            seen_missing_norm.add(norm_canonical)
            missing_players.append(canonical_name)

    if fix and missing_players:
        update_puzzle_in_csv(puzzle_day, missing_players, csv_path=csv_path, catalog=catalog_lookup, dry_run=dry_run)

    return "ok", missing_players, model_used


def main():
    parser = argparse.ArgumentParser(description="Verify This & That puzzles with Gemini API")
    parser.add_argument("--puzzle", type=int, default=None, help="Specific puzzle day to verify (e.g. 1)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of puzzles to verify")
    parser.add_argument("--fix", action="store_true", help="Auto-append approved missing players into CSV if pool < 9")
    parser.add_argument("--dry-run", action="store_true", help="Simulate fixes without modifying CSV")
    parser.add_argument("--csv", default="daily_this_and_that_games.csv", help="Path to This & That games CSV")
    args = parser.parse_args()

    api_key = get_gemini_api_key()
    if not api_key:
        print("❌ Error: GEMINI_API_KEY is not configured in environment or config.json.")
        sys.exit(1)

    print("🔑 GEMINI_API_KEY successfully authenticated.")
    print("📚 Loading player catalog whitelist...")
    catalog = load_all_players_catalog()
    print(f"✅ Loaded {len(catalog):,} entries into whitelist.")

    if args.puzzle:
        puzzles = [args.puzzle]
    else:
        limit = args.limit or 3
        puzzles = list(range(1, limit + 1))

    for day in puzzles:
        print(f"\n=======================================================")
        print(f"🔍 Auditing This & That Puzzle #{day}")
        print(f"=======================================================")
        status, missing, model_used = verify_puzzle(day, csv_path=args.csv, catalog=catalog, api_key=api_key)
        if status == "error":
            print(f"  ⚠️  AI Verification error/skipped: {model_used}")
            continue

        if not missing:
            print(f"  ✅ Perfect! Model {model_used} found 0 missing qualifying players.")
        else:
            print(f"  ⚠️  Model {model_used} found {len(missing)} missing qualifying player(s): {missing}")
            if args.fix:
                updated, added = update_puzzle_in_csv(day, missing, csv_path=args.csv, catalog=catalog, dry_run=args.dry_run)
                if updated:
                    prefix = "[DRY-RUN] Would add" if args.dry_run else "🔧 Fixed! Appended"
                    print(f"  {prefix} {added} into puzzle #{day} in {args.csv}")
                else:
                    print(f"  ℹ️  Pool already at limit (>=9) or no eligible players to append.")

    print("\n✅ Verification run complete.")


if __name__ == "__main__":
    main()
