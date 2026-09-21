"""
scripts/alias_portal.py

Local GUI portal for managing team & player aliases and hidden lists.
Run directly or via AliasPortal.command.
Serves on http://localhost:5050 by default.
"""

import os
import sys
import json
import logging
import subprocess
import threading
from flask import Flask, jsonify, request, render_template_string

# Add repository root to python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from scripts.alias_utils import (
    load_aliases_config,
    save_aliases_config,
    get_club_alias_map,
    get_player_alias_map,
    get_hidden_clubs,
    get_hidden_players,
    get_config_path,
    normalize_search_text,
    separate_alias,
    filter_and_canonicalize_clubs,
    filter_and_canonicalize_players
)

app = Flask(__name__)
# Suppress noisy Flask dev server logs
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)


def trigger_game_sync():
    """Runs fetch_daily.py in a background thread to compile updated aliases into all games."""
    if app.config.get("TESTING") or os.environ.get("TESTING") == "1":
        print("[alias_portal] ℹ️ Skipping game sync during test execution.")
        return

    def _run():
        try:
            print("[alias_portal] ⚡ Syncing daily games with updated aliases...")
            res = subprocess.run([sys.executable, "fetch_daily.py"], cwd=ROOT_DIR, capture_output=True, text=True)
            if res.returncode == 0:
                print("[alias_portal] ✅ Daily games synchronized successfully!")
            else:
                print(f"[alias_portal] ⚠️ Sync error: {res.stderr}")
        except Exception as e:
            print(f"[alias_portal] ⚠️ Error syncing daily games: {e}")
    t = threading.Thread(target=_run, daemon=True)
    t.start()


# In-memory cached dataset lists for fast searching
CACHED_CLUBS = None
CACHED_PLAYER_CATALOG = None

# Known curated entities with rich metadata
CURATED_ENTITIES = [
    {
        "Name": "Fernandinho",
        "FullName": "Fernando Luiz Roza",
        "DOB": "1985-05-04",
        "Nationality": "Brazil",
        "Position": "Defensive Midfield",
        "Clubs": "Manchester City, Shakhtar Donetsk, Athletico Paranaense",
        "MarketValue": 80000000
    },
    {
        "Name": "Fernandinho",
        "FullName": "Édis Baise / Fernandinho",
        "DOB": "1985-11-25",
        "Nationality": "Brazil",
        "Position": "Left Winger",
        "Clubs": "Hellas Verona, Grêmio, Chongqing Liangjiang, Chapecoense",
        "MarketValue": 2700000
    },
    {
        "Name": "Fernandinho",
        "FullName": "Fernando Silva dos Santos",
        "DOB": "1993-03-16",
        "Nationality": "Brazil",
        "Position": "Right Winger",
        "Clubs": "GD Estoril Praia, Chongqing Liangjiang",
        "MarketValue": 2700000
    },
    {
        "Name": "Fernandinho",
        "FullName": "Fernando Pereira",
        "DOB": "1994-09-11",
        "Nationality": "Brazil",
        "Position": "Right Winger",
        "Clubs": "Portimonense SC, Vila Nova",
        "MarketValue": 2700000
    },
    {
        "Name": "Rafinha",
        "FullName": "Márcio Rafael Ferreira de Souza",
        "DOB": "1985-09-07",
        "Nationality": "Brazil",
        "Position": "Right-Back",
        "Clubs": "Bayern Munich, Schalke 04, Flamengo, São Paulo, Genoa",
        "MarketValue": 18000000
    },
    {
        "Name": "Rafinha",
        "FullName": "Rafael Alcântara do Nascimento",
        "DOB": "1993-02-12",
        "Nationality": "Brazil",
        "Position": "Attacking Midfield",
        "Clubs": "Barcelona, Inter Milan, Paris Saint-Germain, Real Sociedad, Celta Vigo",
        "MarketValue": 28000000
    },
    {
        "Name": "Danilo",
        "FullName": "Danilo Luiz da Silva",
        "DOB": "1991-07-15",
        "Nationality": "Brazil",
        "Position": "Right-Back / Centre-Back",
        "Clubs": "Porto, Real Madrid, Manchester City, Juventus",
        "MarketValue": 35000000
    },
    {
        "Name": "Danilo",
        "FullName": "Danilo Pereira",
        "DOB": "1991-09-09",
        "Nationality": "Portugal",
        "Position": "Defensive Midfield / Centre-Back",
        "Clubs": "Porto, Paris Saint-Germain, Al-Ittihad, Parma, Roda JC",
        "MarketValue": 25000000
    },
    {
        "Name": "Danilo",
        "FullName": "Danilo dos Santos de Oliveira",
        "DOB": "2001-04-29",
        "Nationality": "Brazil",
        "Position": "Central Midfield",
        "Clubs": "Palmeiras, Nottingham Forest",
        "MarketValue": 28000000
    },
    {
        "Name": "Paulinho",
        "FullName": "José Paulo Bezerra Maciel Júnior",
        "DOB": "1988-07-25",
        "Nationality": "Brazil",
        "Position": "Central Midfield",
        "Clubs": "Tottenham, Barcelona, Corinthians, Guangzhou Evergrande",
        "MarketValue": 40000000
    },
    {
        "Name": "Paulinho",
        "FullName": "Paulo Henrique Sampaio Filho",
        "DOB": "2000-07-15",
        "Nationality": "Brazil",
        "Position": "Left Winger / Forward",
        "Clubs": "Vasco da Gama, Bayer Leverkusen, Atlético Mineiro",
        "MarketValue": 25000000
    },
    {
        "Name": "Adriano",
        "FullName": "Adriano Leite Ribeiro (L'Imperatore)",
        "DOB": "1982-02-17",
        "Nationality": "Brazil",
        "Position": "Centre-Forward",
        "Clubs": "Flamengo, Inter Milan, Parma, Fiorentina, Roma, São Paulo",
        "MarketValue": 40000000
    },
    {
        "Name": "Adriano",
        "FullName": "Adriano Correia Claro",
        "DOB": "1984-10-26",
        "Nationality": "Brazil",
        "Position": "Left-Back",
        "Clubs": "Coritiba, Sevilla, Barcelona, Beşiktaş, Athletico Paranaense",
        "MarketValue": 15000000
    },
    {
        "Name": "Fernando",
        "FullName": "Fernando Francisco Reges (O Polvo)",
        "DOB": "1987-07-25",
        "Nationality": "Brazil",
        "Position": "Defensive Midfield",
        "Clubs": "Porto, Manchester City, Galatasaray, Sevilla, Vila Nova",
        "MarketValue": 20000000
    },
    {
        "Name": "Fernando",
        "FullName": "Fernando Lucas Martins",
        "DOB": "1992-03-03",
        "Nationality": "Brazil",
        "Position": "Defensive Midfield",
        "Clubs": "Grêmio, Shakhtar Donetsk, Sampdoria, Spartak Moscow, Beijing Guoan, Antalyaspor",
        "MarketValue": 16000000
    },
    {
        "Name": "Emerson",
        "FullName": "Emerson Ferreira da Rosa",
        "DOB": "1976-04-04",
        "Nationality": "Brazil",
        "Position": "Defensive Midfield",
        "Clubs": "Grêmio, Bayer Leverkusen, Roma, Juventus, Real Madrid, AC Milan, Santos",
        "MarketValue": 25000000
    },
    {
        "Name": "Emerson Royal",
        "FullName": "Emerson Aparecido Leite de Souza Junior",
        "DOB": "1999-01-14",
        "Nationality": "Brazil",
        "Position": "Right-Back",
        "Clubs": "Ponte Preta, Atlético Mineiro, Real Betis, Barcelona, Tottenham Hotspur, AC Milan",
        "MarketValue": 25000000
    },
    {
        "Name": "Fred",
        "FullName": "Frederico Rodrigues de Paula Santos",
        "DOB": "1993-03-05",
        "Nationality": "Brazil",
        "Position": "Central Midfield",
        "Clubs": "Internacional, Shakhtar Donetsk, Manchester United, Fenerbahçe",
        "MarketValue": 50000000
    },
    {
        "Name": "Fred",
        "FullName": "Frederico Chaves Guedes",
        "DOB": "1983-10-03",
        "Nationality": "Brazil",
        "Position": "Centre-Forward",
        "Clubs": "América Mineiro, Cruzeiro, Lyon, Fluminense, Atlético Mineiro",
        "MarketValue": 15000000
    },
    {
        "Name": "Antony",
        "FullName": "Antony Matheus dos Santos",
        "DOB": "2000-02-24",
        "Nationality": "Brazil",
        "Position": "Right Winger",
        "Clubs": "São Paulo, Ajax, Manchester United, Real Betis",
        "MarketValue": 75000000
    },
    {
        "Name": "Antony",
        "FullName": "Antony Alves Santos",
        "DOB": "2001-09-08",
        "Nationality": "Brazil",
        "Position": "Right Winger",
        "Clubs": "Corinthians, Arouca, Portland Timbers",
        "MarketValue": 2500000
    }
]

def get_all_clubs():
    global CACHED_CLUBS
    if CACHED_CLUBS is None:
        path = os.path.join(ROOT_DIR, "all_clubs.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    CACHED_CLUBS = json.load(f)
            except Exception as e:
                print(f"Error loading all_clubs.json: {e}")
                CACHED_CLUBS = []
        else:
            CACHED_CLUBS = []
    return CACHED_CLUBS

def get_player_catalog():
    """
    Builds and caches a comprehensive player catalog with:
    - Name, FullName, DOB, Nationality, Position, Clubs, MarketValue
    - Fast normalized search indices
    """
    global CACHED_PLAYER_CATALOG
    if CACHED_PLAYER_CATALOG is not None:
        return CACHED_PLAYER_CATALOG

    disk_cache = os.path.join(ROOT_DIR, ".player_catalog_cache.json")
    if os.path.exists(disk_cache):
        try:
            with open(disk_cache, "r", encoding="utf-8") as f:
                cached_list = json.load(f)
                seen_curated = set()
                enriched_catalog = []
                for ent in CURATED_ENTITIES:
                    norm_n = normalize_search_text(ent["Name"])
                    norm_f = normalize_search_text(ent["FullName"])
                    key = (norm_n, norm_f, ent.get("DOB", ""), normalize_search_text(ent.get("Position", "")))
                    seen_curated.add(key)
                    item = dict(ent)
                    item["norm_name"] = norm_n
                    item["norm_full"] = norm_f
                    enriched_catalog.append(item)
                for p in cached_list:
                    key = (p.get("norm_name", ""), p.get("norm_full", ""), p.get("DOB", ""), normalize_search_text(p.get("Position", "")))
                    if key not in seen_curated:
                        enriched_catalog.append(p)
                CACHED_PLAYER_CATALOG = enriched_catalog
                print(f"[alias_portal] ⚡ Loaded {len(CACHED_PLAYER_CATALOG)} players from disk cache + curated.")
                return CACHED_PLAYER_CATALOG
        except Exception as e:
            print(f"[alias_portal] Note: Disk cache error: {e}")

    catalog = []
    seen_identities = set()

    # 1. Seed with curated disambiguated entities
    for ent in CURATED_ENTITIES:
        norm_n = normalize_search_text(ent["Name"])
        norm_f = normalize_search_text(ent["FullName"])
        key = (norm_n, norm_f, ent.get("DOB", ""), normalize_search_text(ent.get("Position", "")))
        seen_identities.add(key)
        item = dict(ent)
        item["norm_name"] = norm_n
        item["norm_full"] = norm_f
        catalog.append(item)

    # 2. Historical careers
    hc_path = os.path.join(ROOT_DIR, "historical_careers.json")
    hc_data = {}
    if os.path.exists(hc_path):
        try:
            with open(hc_path, "r", encoding="utf-8") as f:
                hc_data = json.load(f)
        except Exception as e:
            print(f"Error reading historical_careers.json: {e}")

    # 3. Kagglehub dataset (if present in local cache)
    try:
        import glob
        import pandas as pd
        dc_dir = os.path.expanduser("~/.cache/kagglehub/datasets/davidcariboo/player-scores/versions")
        p_files = sorted(glob.glob(dc_dir + "/**/players.csv", recursive=True))
        t_files = sorted(glob.glob(dc_dir + "/**/transfers.csv", recursive=True))
        if p_files and t_files:
            df_p = pd.read_csv(p_files[-1], usecols=[
                "player_id", "first_name", "last_name", "name", "date_of_birth",
                "country_of_citizenship", "position", "sub_position",
                "current_club_name", "market_value_in_eur", "highest_market_value_in_eur"
            ])
            df_t = pd.read_csv(t_files[-1], usecols=["player_id", "from_club_name", "to_club_name"])

            t_from = df_t[["player_id", "from_club_name"]].dropna().rename(columns={"from_club_name": "club"})
            t_to = df_t[["player_id", "to_club_name"]].dropna().rename(columns={"to_club_name": "club"})
            all_t = pd.concat([t_from, t_to]).drop_duplicates()
            all_t = all_t[all_t["club"] != "Unknown"]
            clubs_by_pid = all_t.groupby("player_id")["club"].apply(lambda s: list(s)[:6]).to_dict()

            for r in df_p.to_dict("records"):
                name = str(r["name"]) if pd.notna(r["name"]) else ""
                if not name:
                    continue
                pid = int(r["player_id"])
                fn = str(r["first_name"]) if pd.notna(r["first_name"]) else ""
                ln = str(r["last_name"]) if pd.notna(r["last_name"]) else ""
                full = f"{fn} {ln}".strip()
                if not full or full.lower() == name.lower():
                    full = name
                
                dob = str(r["date_of_birth"])[:10] if pd.notna(r["date_of_birth"]) else ""
                curr = str(r["current_club_name"]) if pd.notna(r["current_club_name"]) else ""
                clubs = list(clubs_by_pid.get(pid, []))
                if curr and curr not in clubs:
                    clubs.append(curr)

                pos = str(r["sub_position"]) if pd.notna(r["sub_position"]) else (str(r["position"]) if pd.notna(r["position"]) else "")
                nat = str(r["country_of_citizenship"]) if pd.notna(r["country_of_citizenship"]) else ""
                val = int(r["market_value_in_eur"]) if pd.notna(r["market_value_in_eur"]) else (int(r["highest_market_value_in_eur"]) if pd.notna(r["highest_market_value_in_eur"]) else 0)

                norm_n = normalize_search_text(name)
                norm_f = normalize_search_text(full)
                key = (norm_n, norm_f, dob, normalize_search_text(pos))

                if key not in seen_identities:
                    seen_identities.add(key)
                    catalog.append({
                        "Name": name,
                        "FullName": full,
                        "DOB": dob,
                        "Nationality": nat,
                        "Position": pos,
                        "Clubs": ", ".join(clubs) if clubs else "",
                        "MarketValue": val,
                        "norm_name": norm_n,
                        "norm_full": norm_f
                    })
    except Exception as e:
        print(f"[alias_portal] Note: Transfermarkt cache index skipped: {e}")

    # 4. Integrate all_players.json and historical careers
    p_path = os.path.join(ROOT_DIR, "all_players.json")
    if os.path.exists(p_path):
        try:
            with open(p_path, "r", encoding="utf-8") as f:
                all_p = json.load(f)
            for p in all_p:
                if isinstance(p, dict):
                    name = (p.get("Name") or "").strip()
                    nat = p.get("Nationality") or ""
                    pos = p.get("Position") or ""
                    val = p.get("MarketValue") or 0
                elif isinstance(p, str):
                    name = p.strip()
                    nat, pos, val = "", "", 0
                else:
                    continue

                if not name:
                    continue

                norm_n = normalize_search_text(name)
                key = (norm_n, norm_n, "", normalize_search_text(pos))
                if key not in seen_identities:
                    seen_identities.add(key)
                    clubs = ""
                    if name in hc_data:
                        clubs = ", ".join(hc_data[name].get("clubs", []))
                    catalog.append({
                        "Name": name,
                        "FullName": name,
                        "DOB": "",
                        "Nationality": nat,
                        "Position": pos,
                        "Clubs": clubs,
                        "MarketValue": val,
                        "norm_name": norm_n,
                        "norm_full": norm_n
                    })
        except Exception as e:
            print(f"Error loading all_players.json: {e}")

    # Sort catalog by market value descending by default
    catalog.sort(key=lambda x: x.get("MarketValue", 0), reverse=True)
    CACHED_PLAYER_CATALOG = catalog
    try:
        disk_cache = os.path.join(ROOT_DIR, ".player_catalog_cache.json")
        with open(disk_cache, "w", encoding="utf-8") as f:
            json.dump(catalog, f)
    except Exception as e:
        print(f"[alias_portal] Note: Failed to persist disk cache: {e}")
    print(f"[alias_portal] ✅ Player catalog indexed: {len(catalog)} players ready.")
    return CACHED_PLAYER_CATALOG

# ─────────────────────────────────────────────────────────────
# API Endpoints
# ─────────────────────────────────────────────────────────────

@app.route("/api/config", methods=["GET"])
def api_get_config():
    cfg = load_aliases_config(ROOT_DIR)
    return jsonify({
        "status": "success",
        "config": cfg,
        "path": get_config_path(ROOT_DIR)
    })

def _sanitize_groups(raw_groups):
    clean_groups = []
    for g in raw_groups:
        if not isinstance(g, dict):
            continue
        d_name = (g.get("display_name") or "").strip()
        if not d_name:
            continue
        aliases = [a.strip() for a in g.get("aliases", []) if isinstance(a, str) and a.strip() and a.strip() != d_name]
        seen_a = set()
        clean_a = []
        for a in aliases:
            if a not in seen_a:
                seen_a.add(a)
                clean_a.append(a)
        clean_groups.append({
            "display_name": d_name,
            "aliases": clean_a,
            "hidden": bool(g.get("hidden", False))
        })
    return clean_groups

def _sanitize_hidden_players(raw_hidden):
    clean = []
    seen = set()
    for p in raw_hidden:
        if isinstance(p, dict):
            name = (p.get("Name") or p.get("name") or "").strip()
            if not name:
                continue
            full = (p.get("FullName") or p.get("full_name") or name).strip()
            dob = str(p.get("DOB") or p.get("dob") or "").strip()
            nat = (p.get("Nationality") or p.get("nationality") or "").strip()
            pos = (p.get("Position") or p.get("position") or "").strip()
            clubs = p.get("Clubs") or p.get("clubs") or ""
            if isinstance(clubs, list):
                clubs = ", ".join(clubs)
            key = f"{name.lower()}|{full.lower()}|{dob}|{pos.lower()}|{nat.lower()}"
            if key not in seen:
                seen.add(key)
                clean.append({
                    "Name": name,
                    "FullName": full,
                    "DOB": dob,
                    "Nationality": nat,
                    "Position": pos,
                    "Clubs": clubs
                })
        elif isinstance(p, str) and p.strip():
            s = p.strip()
            if s.lower() not in seen:
                seen.add(s.lower())
                clean.append(s)
    return clean

@app.route("/api/config", methods=["POST"])
def api_save_config():
    data = request.get_json(force=True, silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"status": "error", "message": "Invalid JSON body"}), 400
    
    clubs_data = data.get("clubs", {})
    players_data = data.get("players", {})

    sanitized = {
        "version": data.get("version", 1),
        "clubs": {
            "groups": _sanitize_groups(clubs_data.get("groups", [])),
            "hidden_standalone": [c.strip() for c in clubs_data.get("hidden_standalone", []) if isinstance(c, str) and c.strip()]
        },
        "players": {
            "groups": _sanitize_groups(players_data.get("groups", [])),
            "hidden": _sanitize_hidden_players(players_data.get("hidden", []))
        }
    }

    save_aliases_config(sanitized, ROOT_DIR)
    trigger_game_sync()
    return jsonify({"status": "success", "message": "Saved successfully & syncing games...", "config": sanitized})

@app.route("/api/alias/separate", methods=["POST"])
def api_separate_alias():
    data = request.get_json(force=True, silent=True)
    if not data or not isinstance(data, dict):
        return jsonify({"status": "error", "message": "Invalid JSON body"}), 400
    
    entity_type = data.get("entity_type", "clubs")
    group_display_name = (data.get("group_display_name") or "").strip()
    alias_to_separate = (data.get("alias_to_separate") or "").strip()
    new_display_name = (data.get("new_display_name") or alias_to_separate).strip()

    if not group_display_name or not alias_to_separate:
        return jsonify({"status": "error", "message": "Missing group_display_name or alias_to_separate"}), 400

    ok, msg, updated_cfg = separate_alias(
        entity_type=entity_type,
        group_display_name=group_display_name,
        alias_to_separate=alias_to_separate,
        new_display_name=new_display_name,
        root_dir=ROOT_DIR
    )

    if not ok:
        return jsonify({"status": "error", "message": msg}), 400
    
    trigger_game_sync()
    return jsonify({"status": "success", "message": msg, "config": updated_cfg})

@app.route("/api/sync-games", methods=["POST"])
def api_sync_games():
    try:
        res = subprocess.run([sys.executable, "fetch_daily.py"], cwd=ROOT_DIR, capture_output=True, text=True, timeout=30)
        if res.returncode == 0:
            return jsonify({"status": "success", "message": "All games recompiled and synchronized successfully!"})
        else:
            return jsonify({"status": "error", "message": f"Compilation error: {res.stderr}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/search/clubs", methods=["GET"])
def api_search_clubs():
    raw_q = (request.args.get("q") or "").strip()
    norm_q = normalize_search_text(raw_q)
    limit = int(request.args.get("limit", 25))
    if not norm_q:
        return jsonify([])
    
    clubs = get_all_clubs()
    prefix_matches = []
    sub_matches = []
    
    for c in clubs:
        c_clean = (c.get("name") or c.get("Name") or "").strip() if isinstance(c, dict) else (c.strip() if isinstance(c, str) else "")
        if not c_clean:
            continue
        c_norm = normalize_search_text(c_clean)
        if c_norm.startswith(norm_q):
            prefix_matches.append(c_clean)
        elif norm_q in c_norm:
            sub_matches.append(c_clean)
        if len(prefix_matches) >= limit:
            break
            
    results = (prefix_matches + sub_matches)[:limit]
    return jsonify(results)

@app.route("/api/search/players", methods=["GET"])
def api_search_players():
    raw_q = (request.args.get("q") or "").strip()
    norm_q = normalize_search_text(raw_q)
    limit = int(request.args.get("limit", 25))
    if not norm_q:
        return jsonify([])
    
    catalog = get_player_catalog()
    prefix_matches = []
    sub_matches = []
    seen_keys = set()
    
    # 1. Search in rich player catalog
    for p in catalog:
        norm_name = p.get("norm_name", "")
        norm_full = p.get("norm_full", "")
        
        # Deduplication key across unique entity
        ent_key = (norm_name, norm_full, p.get("DOB", ""), normalize_search_text(p.get("Position", "")))
        if ent_key in seen_keys:
            continue
        
        item = {
            "Name": p["Name"],
            "FullName": p.get("FullName") or p["Name"],
            "DOB": p.get("DOB", ""),
            "Nationality": p.get("Nationality", ""),
            "Position": p.get("Position", ""),
            "Clubs": p.get("Clubs", ""),
            "MarketValue": p.get("MarketValue", 0)
        }

        if norm_name.startswith(norm_q) or norm_full.startswith(norm_q):
            seen_keys.add(ent_key)
            prefix_matches.append(item)
        elif norm_q in norm_name or norm_q in norm_full:
            seen_keys.add(ent_key)
            sub_matches.append(item)

        if len(prefix_matches) >= limit or (len(prefix_matches) + len(sub_matches) >= limit * 2):
            break

    # 2. Search configured player alias groups (aliases_config.json)
    try:
        cfg = load_aliases_config(ROOT_DIR)
        p_groups = cfg.get("players", {}).get("groups", [])
        for g in p_groups:
            d_name = g.get("display_name", "")
            aliases = g.get("aliases", [])
            d_norm = normalize_search_text(d_name)
            g_key = (d_norm, d_norm, "", "player group")
            if d_name and g_key not in seen_keys:
                is_all = "(all)" in d_name.lower()
                item = {
                    "Name": d_name,
                    "FullName": d_name,
                    "DOB": "",
                    "Nationality": "" if is_all else "Config Group",
                    "Position": "" if is_all else "Alias Group",
                    "Clubs": "" if is_all else ", ".join(aliases[:4]),
                    "MarketValue": 0
                }
                if d_norm.startswith(norm_q):
                    seen_keys.add(g_key)
                    prefix_matches.append(item)
                elif norm_q in d_norm:
                    seen_keys.add(g_key)
                    sub_matches.append(item)

            for a in aliases:
                a_norm = normalize_search_text(a)
                a_key = (a_norm, a_norm, "", "alias")
                if a and a_key not in seen_keys:
                    item = {
                        "Name": a,
                        "FullName": f"Alias of {d_name}",
                        "DOB": "",
                        "Nationality": f"Maps to {d_name}",
                        "Position": "Alias",
                        "Clubs": "",
                        "MarketValue": 0
                    }
                    if a_norm.startswith(norm_q):
                        seen_keys.add(a_key)
                        prefix_matches.append(item)
                    elif norm_q in a_norm:
                        seen_keys.add(a_key)
                        sub_matches.append(item)
    except Exception as e:
        print(f"Error searching alias config: {e}")

    results = (prefix_matches + sub_matches)[:limit]
    return jsonify(results)


@app.route("/api/players/disambiguation-candidates", methods=["GET"])
def api_disambiguation_candidates():
    catalog = get_player_catalog()
    mononym_map = {}
    for p in catalog:
        name = (p.get("Name") or "").strip()
        if not name or " " in name:
            continue
        mononym_map.setdefault(name, []).append(p)
    
    candidates = []
    priority_names = ["Fernandinho", "Rafinha", "Antony", "Adriano", "Danilo", "Fernando", "Willian", "Paulinho", "Emerson", "Fred", "Gabriel", "Marcelo", "Eduardo"]
    
    handled = set()
    for name in priority_names:
        if name in mononym_map and len(mononym_map[name]) > 1:
            handled.add(name)
            entities = []
            for p in mononym_map[name]:
                entities.append({
                    "full_name": p.get("FullName") or p.get("Name"),
                    "dob": p.get("DOB", ""),
                    "pos": p.get("Position", ""),
                    "notable_clubs": p.get("Clubs", "")
                })
            candidates.append({
                "name": name,
                "count": len(entities),
                "entities": entities
            })
            
    for name, p_list in sorted(mononym_map.items()):
        if name not in handled and len(p_list) > 1:
            entities = []
            for p in p_list:
                entities.append({
                    "full_name": p.get("FullName") or p.get("Name"),
                    "dob": p.get("DOB", ""),
                    "pos": p.get("Position", ""),
                    "notable_clubs": p.get("Clubs", "")
                })
            candidates.append({
                "name": name,
                "count": len(entities),
                "entities": entities
            })
            
    return jsonify(candidates[:50])

# ─────────────────────────────────────────────────────────────
# UI Template
# ─────────────────────────────────────────────────────────────

PORTAL_HTML = r"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Playmaker · Team & Player Aliases & Disambiguation</title>
    <link rel="icon" href="/favicon.ico" type="image/x-icon">
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    colors: {
                        brand: {
                            gold: '#fbbf24',
                            emerald: '#10b981',
                            red: '#ef4444',
                            dark: '#0f172a',
                            card: '#1e293b',
                            border: '#334155'
                        }
                    }
                }
            }
        }
    </script>
    <style>
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0f172a; }
        ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: #475569; }
        .tab-active { border-bottom: 2px solid #fbbf24; color: #fbbf24; }
    </style>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col font-sans selection:bg-amber-500 selection:text-black">

    <!-- Header / Navbar -->
    <header class="border-b border-slate-800 bg-slate-900/90 sticky top-0 z-50 backdrop-blur">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <span class="text-2xl">⚽</span>
                <div>
                    <h1 class="text-lg font-bold tracking-wide flex items-center gap-2">
                        <span>PLAYMAKER</span>
                        <span class="text-xs uppercase px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 font-semibold border border-amber-500/30">Aliases & Disambiguation Portal</span>
                    </h1>
                    <p class="text-xs text-slate-400">Manage team & player aliases, separate shared names, and curate dropdowns</p>
                </div>
            </div>
            <div class="flex items-center space-x-3">
                <span id="save-status" class="text-xs text-emerald-400 font-medium px-2.5 py-1 rounded bg-emerald-500/10 border border-emerald-500/20 hidden">Saved & Synced</span>
                <button onclick="syncGames()" id="sync-games-btn" class="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-200 font-medium px-3 py-2 rounded-lg text-sm shadow transition flex items-center gap-2 active:scale-95" title="Recompile all daily game HTMLs immediately">
                    <span id="sync-spinner" class="text-amber-400">⚡</span>
                    <span id="sync-btn-text">Sync Games</span>
                </button>
                <button onclick="saveConfig()" class="bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-4 py-2 rounded-lg text-sm shadow-lg shadow-amber-500/20 transition flex items-center gap-2 active:scale-95">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"/></svg>
                    Save Changes
                </button>
            </div>

        </div>
    </header>

    <!-- Main Container -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex-1 w-full space-y-6">

        <!-- Navigation Tabs & Stats Bar -->
        <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between border-b border-slate-800 pb-3 gap-4">
            <nav class="flex flex-wrap gap-4 sm:gap-6 text-sm font-medium">
                <button onclick="switchTab('groups')" id="tab-btn-groups" class="pb-2 text-slate-400 hover:text-slate-200 transition tab-active flex items-center gap-2">
                    <span>🛡️ Team Aliases</span>
                    <span id="stat-groups-count" class="text-xs bg-slate-800 px-2 py-0.5 rounded-full text-slate-300">0</span>
                </button>
                <button onclick="switchTab('player-groups')" id="tab-btn-player-groups" class="pb-2 text-slate-400 hover:text-slate-200 transition flex items-center gap-2">
                    <span>👤 Player Aliases</span>
                    <span id="stat-player-groups-count" class="text-xs bg-slate-800 px-2 py-0.5 rounded-full text-slate-300">0</span>
                </button>
                <button onclick="switchTab('hidden-clubs')" id="tab-btn-hidden-clubs" class="pb-2 text-slate-400 hover:text-slate-200 transition flex items-center gap-2">
                    <span>🚫 Hidden Clubs</span>
                    <span id="stat-hidden-clubs-count" class="text-xs bg-slate-800 px-2 py-0.5 rounded-full text-slate-300">0</span>
                </button>
                <button onclick="switchTab('hidden-players')" id="tab-btn-hidden-players" class="pb-2 text-slate-400 hover:text-slate-200 transition flex items-center gap-2">
                    <span>👤 Hidden Players</span>
                    <span id="stat-hidden-players-count" class="text-xs bg-slate-800 px-2 py-0.5 rounded-full text-slate-300">0</span>
                </button>
            </nav>

            <div class="flex items-center gap-2 text-xs text-slate-400">
                <span>Config Path:</span>
                <code id="config-path" class="bg-slate-900 px-2 py-1 rounded text-slate-300 border border-slate-800 font-mono">private/aliases_config.json</code>
            </div>
        </div>

        <!-- TAB 1: TEAM ALIAS GROUPS -->
        <section id="tab-groups" class="space-y-6">
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
                <div class="relative md:col-span-2">
                    <input type="text" id="group-search-input" oninput="renderGroups()" placeholder="Filter team alias groups by name or variant..." class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500 transition">
                    <span class="absolute right-3 top-2.5 text-slate-500">🔍</span>
                </div>
                <div class="flex justify-end">
                    <button onclick="openNewGroupModal('clubs')" class="w-full sm:w-auto bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-100 font-medium px-4 py-2.5 rounded-lg text-sm transition flex items-center justify-center gap-2 shadow">
                        <span class="text-amber-400 font-bold">+</span> Create Team Alias Group
                    </button>
                </div>
            </div>
            <div id="groups-container" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"></div>
        </section>

        <!-- TAB 2: PLAYER ALIAS GROUPS & DISAMBIGUATION -->
        <section id="tab-player-groups" class="hidden space-y-6">
            <!-- Disambiguation Helper Banner -->
            <div class="bg-amber-500/10 border border-amber-500/30 rounded-xl p-4 space-y-3">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-2">
                        <span class="text-xl">⚡</span>
                        <h3 class="font-bold text-amber-300 text-sm">Player Disambiguation & Homonym Helper</h3>
                    </div>
                    <span class="text-xs text-slate-400">Separate distinct players with matching names (e.g. Fernandinho, Rafinha, Danilo, Paulinho)</span>
                </div>
                <div id="disambiguation-pills" class="flex flex-wrap gap-2 pt-1"></div>
            </div>

            <!-- Action Bar -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-4 items-center">
                <div class="relative md:col-span-2">
                    <input type="text" id="player-group-search-input" oninput="renderPlayerGroups()" placeholder="Filter player alias groups by name or alias..." class="w-full bg-slate-900 border border-slate-700 rounded-lg px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-amber-500 transition">
                    <span class="absolute right-3 top-2.5 text-slate-500">🔍</span>
                </div>
                <div class="flex justify-end">
                    <button onclick="openNewGroupModal('players')" class="w-full sm:w-auto bg-slate-800 hover:bg-slate-700 border border-slate-600 text-slate-100 font-medium px-4 py-2.5 rounded-lg text-sm transition flex items-center justify-center gap-2 shadow">
                        <span class="text-amber-400 font-bold">+</span> Create Player Alias Group
                    </button>
                </div>
            </div>
            <div id="player-groups-container" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"></div>
        </section>

        <!-- TAB 3: HIDDEN STANDALONE CLUBS -->
        <section id="tab-hidden-clubs" class="hidden space-y-6">
            <div class="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
                <div>
                    <h3 class="font-semibold text-slate-200">Standalone Hidden Clubs</h3>
                    <p class="text-xs text-slate-400">Clubs in this list are completely excluded from autocomplete dropdowns across all games.</p>
                </div>
                <div class="w-full md:w-96 relative">
                    <input type="text" id="hide-club-input" placeholder="Search club to hide (e.g. 01 Bamberg)..." oninput="searchClubToHide(this.value)" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-amber-500 transition">
                    <div id="hide-club-results" class="absolute z-20 w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg shadow-xl max-h-48 overflow-y-auto hidden"></div>
                </div>
            </div>
            <div id="hidden-clubs-chips" class="flex flex-wrap gap-2"></div>
        </section>

        <!-- TAB 4: HIDDEN PLAYERS -->
        <section id="tab-hidden-players" class="hidden space-y-6">
            <div class="bg-slate-900/60 border border-slate-800 p-4 rounded-xl flex flex-col md:flex-row gap-4 justify-between items-start md:items-center">
                <div>
                    <h3 class="font-semibold text-slate-200">Hidden Players</h3>
                    <p class="text-xs text-slate-400">Specific players in this list are excluded from autocomplete suggestions across all games.</p>
                </div>
                <div class="w-full md:w-96 relative">
                    <input type="text" id="hide-player-input" placeholder="Search player to hide by name or full name..." oninput="searchPlayerToHide(this.value)" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-amber-500 transition">
                    <div id="hide-player-results" class="absolute z-30 w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl max-h-64 overflow-y-auto hidden"></div>
                </div>
            </div>
            <div id="hidden-players-chips" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3"></div>
        </section>

    </main>

    <!-- Modal: Create / Edit Group (Clubs or Players) -->
    <div id="group-modal" class="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 hidden">
        <div class="bg-slate-900 border border-slate-700 rounded-xl max-w-xl w-full p-6 space-y-5 shadow-2xl relative">
            <button onclick="closeGroupModal()" class="absolute top-4 right-4 text-slate-400 hover:text-slate-100 text-xl font-bold">&times;</button>
            <h2 id="modal-title" class="text-lg font-bold text-slate-100 flex items-center gap-2">
                <span>🛡️</span> Alias Group
            </h2>

            <div class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Primary Display Name</label>
                    <div class="relative">
                        <input type="text" id="modal-display-name" oninput="searchModalDisplayName(this.value)" placeholder="Start typing to search player or enter canonical name..." class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-amber-500 font-semibold" autocomplete="off">
                        <div id="modal-display-results" class="absolute z-30 w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl max-h-60 overflow-y-auto hidden"></div>
                    </div>
                    <p class="text-xs text-slate-500 mt-1">This canonical name is what appears in answer checks & suggestions.</p>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Search & Add Aliases</label>
                    <div class="relative">
                        <input type="text" id="modal-alias-search" oninput="searchModalAliases(this.value)" onkeydown="if(event.key === 'Enter') { event.preventDefault(); const v = this.value.trim(); if(v) selectModalAlias(v); }" placeholder="Search database or type any custom alias..." class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:border-amber-500" autocomplete="off">
                        <div id="modal-alias-results" class="absolute z-30 w-full mt-1 bg-slate-900 border border-slate-700 rounded-lg shadow-2xl max-h-56 overflow-y-auto hidden"></div>
                    </div>
                </div>

                <div>
                    <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1">Attached Aliases (Variants)</label>
                    <div id="modal-aliases-container" class="min-h-[60px] p-2 bg-slate-950 border border-slate-800 rounded-lg flex flex-wrap gap-2 items-start max-h-40 overflow-y-auto"></div>
                    <div class="flex gap-2 mt-2">
                        <input type="text" id="modal-custom-alias-input" onkeydown="if(event.key === 'Enter') { event.preventDefault(); addCustomAlias(); }" placeholder="Or manually type an alias / nickname..." class="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-slate-600">
                        <button onclick="addCustomAlias()" class="bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs px-3 py-1.5 rounded-lg border border-slate-700 font-medium">Add</button>
                    </div>
                </div>

                <div class="flex items-center gap-2 pt-2 border-t border-slate-800">
                    <input type="checkbox" id="modal-hidden-checkbox" class="rounded bg-slate-950 border-slate-700 text-amber-500 focus:ring-amber-500 h-4 w-4">
                    <label for="modal-hidden-checkbox" class="text-xs text-slate-300 font-medium">Hide this entire group from autocomplete dropdowns</label>
                </div>
            </div>

            <div class="flex justify-end gap-3 pt-3 border-t border-slate-800">
                <button onclick="closeGroupModal()" class="px-4 py-2 text-sm text-slate-400 hover:text-slate-200">Cancel</button>
                <button onclick="saveGroupModal()" class="bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold px-4 py-2 rounded-lg text-sm shadow active:scale-95">Save Group</button>
            </div>
        </div>
    </div>

    <!-- JavaScript Application Logic -->
    <script>
        let config = { version: 1, clubs: { groups: [], hidden_standalone: [] }, players: { groups: [], hidden: [] } };
        let activeTab = 'groups';
        let modalEntityType = 'clubs';
        let editingIndex = -1;
        let modalAliases = [];
        let disambiguationCandidatesList = [];
        let currentModalDisplayMatches = [];
        let currentModalAliasMatches = [];
        let currentHideClubMatches = [];
        let currentHidePlayerMatches = [];

        async function init() {
            try {
                const res = await fetch('/api/config');
                const data = await res.json();
                if (data.status === 'success') {
                    config = data.config;
                    if (!config.players) config.players = { groups: [], hidden: [] };
                    if (!config.players.groups) config.players.groups = [];
                    if (!config.players.hidden) config.players.hidden = [];
                    document.getElementById('config-path').textContent = data.path;
                    updateStats();
                    renderGroups();
                    renderPlayerGroups();
                    renderHiddenClubs();
                    renderHiddenPlayers();
                    loadDisambiguationCandidates();
                }
            } catch (err) {
                console.error("Failed to load initial config:", err);
            }
        }

        function updateStats() {
            document.getElementById('stat-groups-count').textContent = config.clubs.groups.length;
            document.getElementById('stat-player-groups-count').textContent = (config.players.groups || []).length;
            document.getElementById('stat-hidden-clubs-count').textContent = config.clubs.hidden_standalone.length;
            document.getElementById('stat-hidden-players-count').textContent = (config.players.hidden || []).length;
        }

        function switchTab(tab) {
            activeTab = tab;
            ['groups', 'player-groups', 'hidden-clubs', 'hidden-players'].forEach(t => {
                const btn = document.getElementById('tab-btn-' + t);
                const section = document.getElementById('tab-' + t);
                if (btn && section) {
                    if (t === tab) {
                        btn.classList.add('tab-active');
                        btn.classList.remove('text-slate-400');
                        section.classList.remove('hidden');
                    } else {
                        btn.classList.remove('tab-active');
                        btn.classList.add('text-slate-400');
                        section.classList.add('hidden');
                    }
                }
            });
        }

        function normalizeSearchText(str) {
            if (!str) return '';
            return String(str)
                .replace(/[\u200b-\u200f\u202a-\u202e\ufeff]/g, '')
                .replace(/[ðÐ]/g, 'd').replace(/[þÞ]/g, 'th').replace(/[øØ]/g, 'o')
                .replace(/[łŁ]/g, 'l').replace(/[đĐ]/g, 'd').replace(/[æÆ]/g, 'ae')
                .replace(/[œŒ]/g, 'oe').replace(/ß/g, 'ss')
                .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
                .toLowerCase().replace(/[-._']/g, ' ').replace(/\s+/g, ' ').trim();
        }

        // ── Render Team Aliases ──
        function renderGroups() {
            const container = document.getElementById('groups-container');
            const search = normalizeSearchText(document.getElementById('group-search-input').value || '');
            container.innerHTML = '';
            let matchCount = 0;

            config.clubs.groups.forEach((g, idx) => {
                const normDisplay = normalizeSearchText(g.display_name);
                const matchesSearch = !search || normDisplay.includes(search) || g.aliases.some(a => normalizeSearchText(a).includes(search));
                if (!matchesSearch) return;
                matchCount++;

                const card = document.createElement('div');
                card.className = "bg-slate-900/90 border border-slate-800 hover:border-slate-700 p-4 rounded-xl flex flex-col justify-between space-y-3 transition shadow-sm relative group";

                let aliasesHtml = g.aliases.map((a, aIdx) => `
                    <span class="inline-flex items-center gap-1 bg-slate-800 text-slate-300 text-xs px-2 py-0.5 rounded border border-slate-700">
                        <span>${escapeHtml(a)}</span>
                        <button onclick="separateAliasFromGroupIndex('clubs', ${idx}, ${aIdx})" title="Separate into independent group" class="text-amber-400 hover:text-amber-200 text-[10px] font-bold px-1 ml-0.5 hover:bg-slate-700 rounded">✂️</button>
                    </span>
                `).join(' ');

                if (!aliasesHtml) aliasesHtml = `<span class="text-xs text-slate-500 italic">No additional aliases</span>`;

                card.innerHTML = `
                    <div>
                        <div class="flex items-start justify-between gap-2">
                            <div class="flex items-center gap-2">
                                <span class="text-amber-400 font-bold">🛡️</span>
                                <h3 class="font-bold text-slate-100 text-base">${escapeHtml(g.display_name)}</h3>
                            </div>
                            <div class="flex items-center gap-1.5">
                                ${g.hidden ? '<span class="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">Hidden</span>' : ''}
                                <button onclick="editGroup('clubs', ${idx})" class="text-slate-400 hover:text-amber-400 p-1 text-xs" title="Edit">✏️</button>
                                <button onclick="deleteGroup('clubs', ${idx})" class="text-slate-400 hover:text-red-400 p-1 text-xs" title="Delete">&times;</button>
                            </div>
                        </div>
                        <div class="mt-3">
                            <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Attached Aliases (${g.aliases.length}):</p>
                            <div class="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">${aliasesHtml}</div>
                        </div>
                    </div>
                    <div class="pt-2 border-t border-slate-800 flex justify-between items-center text-xs text-slate-500">
                        <span>Maps to: <strong class="text-slate-300">${escapeHtml(g.display_name)}</strong></span>
                        <button onclick="toggleGroupHidden('clubs', ${idx})" class="text-[11px] hover:underline ${g.hidden ? 'text-emerald-400' : 'text-slate-400'}">
                            ${g.hidden ? 'Unhide' : 'Hide from dropdown'}
                        </button>
                    </div>
                `;
                container.appendChild(card);
            });

            if (matchCount === 0) {
                container.innerHTML = `<div class="col-span-full py-12 text-center text-slate-500"><p class="text-sm">No team alias groups match your search.</p></div>`;
            }
        }

        // ── Render Player Aliases ──
        function renderPlayerGroups() {
            const container = document.getElementById('player-groups-container');
            const search = normalizeSearchText(document.getElementById('player-group-search-input').value || '');
            container.innerHTML = '';
            let matchCount = 0;

            const pGroups = config.players.groups || [];
            pGroups.forEach((g, idx) => {
                const normDisplay = normalizeSearchText(g.display_name);
                const matchesSearch = !search || normDisplay.includes(search) || g.aliases.some(a => normalizeSearchText(a).includes(search));
                if (!matchesSearch) return;
                matchCount++;

                const card = document.createElement('div');
                card.className = "bg-slate-900/90 border border-slate-800 hover:border-slate-700 p-4 rounded-xl flex flex-col justify-between space-y-3 transition shadow-sm relative group";

                let aliasesHtml = g.aliases.map((a, aIdx) => `
                    <span class="inline-flex items-center gap-1 bg-slate-800 text-slate-300 text-xs px-2 py-0.5 rounded border border-slate-700">
                        <span>${escapeHtml(a)}</span>
                        <button onclick="separateAliasFromGroupIndex('players', ${idx}, ${aIdx})" title="Separate into independent player" class="text-amber-400 hover:text-amber-200 text-[10px] font-bold px-1 ml-0.5 hover:bg-slate-700 rounded">✂️</button>
                    </span>
                `).join(' ');

                if (!aliasesHtml) aliasesHtml = `<span class="text-xs text-slate-500 italic">No additional aliases</span>`;

                card.innerHTML = `
                    <div>
                        <div class="flex items-start justify-between gap-2">
                            <div class="flex items-center gap-2">
                                <span class="text-amber-400 font-bold">👤</span>
                                <h3 class="font-bold text-slate-100 text-base">${escapeHtml(g.display_name)}</h3>
                            </div>
                            <div class="flex items-center gap-1.5">
                                ${g.hidden ? '<span class="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">Hidden</span>' : ''}
                                <button onclick="editGroup('players', ${idx})" class="text-slate-400 hover:text-amber-400 p-1 text-xs" title="Edit">✏️</button>
                                <button onclick="deleteGroup('players', ${idx})" class="text-slate-400 hover:text-red-400 p-1 text-xs" title="Delete">&times;</button>
                            </div>
                        </div>
                        <div class="mt-3">
                            <p class="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-1.5">Attached Aliases (${g.aliases.length}):</p>
                            <div class="flex flex-wrap gap-1.5 max-h-24 overflow-y-auto">${aliasesHtml}</div>
                        </div>
                    </div>
                    <div class="pt-2 border-t border-slate-800 flex justify-between items-center text-xs text-slate-500">
                        <span>Canonical: <strong class="text-slate-300">${escapeHtml(g.display_name)}</strong></span>
                        <button onclick="toggleGroupHidden('players', ${idx})" class="text-[11px] hover:underline ${g.hidden ? 'text-emerald-400' : 'text-slate-400'}">
                            ${g.hidden ? 'Unhide' : 'Hide from dropdown'}
                        </button>
                    </div>
                `;
                container.appendChild(card);
            });

            if (matchCount === 0) {
                container.innerHTML = `<div class="col-span-full py-12 text-center text-slate-500"><p class="text-sm">No player alias groups configured yet. Click "+ Create Player Alias Group" or use the Disambiguation Helper above.</p></div>`;
            }
        }

        // ── Disambiguation Helper Loading ──
        async function loadDisambiguationCandidates() {
            try {
                const res = await fetch('/api/players/disambiguation-candidates');
                const items = await res.json();
                disambiguationCandidatesList = items || [];
                const container = document.getElementById('disambiguation-pills');
                container.innerHTML = '';
                disambiguationCandidatesList.forEach((cand, candIdx) => {
                    const pill = document.createElement('div');
                    pill.className = "bg-slate-900 border border-slate-700 hover:border-amber-500/50 p-2.5 rounded-lg text-xs space-y-1.5 max-w-sm flex-1 min-w-[260px]";
                    let entitiesHtml = (cand.entities || []).map((e, eIdx) => `
                        <div class="text-[11px] text-slate-300 border-l-2 border-amber-500/40 pl-2 py-0.5 flex justify-between items-start gap-2">
                            <div class="overflow-hidden">
                                <div class="font-semibold text-white">${escapeHtml(e.full_name)} <span class="text-slate-400 font-normal">(${e.dob ? e.dob.split('-')[0] : ''})</span></div>
                                <div class="text-[10px] text-slate-400 truncate" title="${escapeAttr(e.notable_clubs)}">${escapeHtml(e.notable_clubs)}</div>
                            </div>
                            <button onclick="quickDisambiguateCandidateEntity(${candIdx}, ${eIdx})" class="bg-slate-800 hover:bg-amber-500/20 text-slate-300 hover:text-amber-300 px-1.5 py-0.5 rounded text-[10px] font-medium border border-slate-700 shrink-0">+ Set</button>
                        </div>
                    `).join('');

                    pill.innerHTML = `
                        <div class="flex items-center justify-between">
                            <span class="font-bold text-amber-400 text-sm">${escapeHtml(cand.name)}</span>
                            <button onclick="quickDisambiguateCandidate(${candIdx})" class="bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 px-2 py-0.5 rounded text-[11px] font-semibold border border-amber-500/30">+ Custom Group</button>
                        </div>
                        <div class="space-y-1">${entitiesHtml}</div>
                    `;
                    container.appendChild(pill);
                });
            } catch (err) {
                console.error("Error loading candidates:", err);
            }
        }

        function quickDisambiguateCandidate(candIdx) {
            const cand = disambiguationCandidatesList[candIdx];
            if (!cand) return;
            openNewGroupModal('players');
            document.getElementById('modal-display-name').value = cand.name;
            modalAliases = [];
            renderModalAliases();
        }

        function quickDisambiguateCandidateEntity(candIdx, eIdx) {
            const cand = disambiguationCandidatesList[candIdx];
            if (!cand || !cand.entities || !cand.entities[eIdx]) return;
            const entity = cand.entities[eIdx];
            openNewGroupModal('players');
            document.getElementById('modal-display-name').value = entity.full_name;
            modalAliases = [cand.name];
            renderModalAliases();
        }

        // ── Alias Separation API Action ──
        async function separateAliasFromGroupIndex(entityType, groupIdx, aliasIdx) {
            const list = entityType === 'players' ? config.players.groups : config.clubs.groups;
            const g = list[groupIdx];
            if (!g || !g.aliases || aliasIdx >= g.aliases.length) return;
            const alias = g.aliases[aliasIdx];
            const groupName = g.display_name;

            const newName = prompt(`Separate "${alias}" into its own independent ${entityType === 'players' ? 'player' : 'team'} group?\nEnter new Display Name:`, alias);
            if (newName === null) return;
            
            try {
                const res = await fetch('/api/alias/separate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        entity_type: entityType,
                        group_display_name: groupName,
                        alias_to_separate: alias,
                        new_display_name: newName.trim() || alias
                    })
                });
                const data = await res.json();
                if (data.status === 'success') {
                    config = data.config;
                    updateStats();
                    renderGroups();
                    renderPlayerGroups();
                    showSavedBanner();
                } else {
                    alert('Error separating alias: ' + data.message);
                }
            } catch (err) {
                alert('Network error separating alias: ' + err);
            }
        }

        function toggleGroupHidden(entityType, idx) {
            const list = entityType === 'players' ? config.players.groups : config.clubs.groups;
            list[idx].hidden = !list[idx].hidden;
            if (entityType === 'players') renderPlayerGroups(); else renderGroups();
            triggerSaveFeedback();
        }

        function deleteGroup(entityType, idx) {
            const list = entityType === 'players' ? config.players.groups : config.clubs.groups;
            if (confirm(`Delete alias group "${list[idx].display_name}"?`)) {
                list.splice(idx, 1);
                updateStats();
                if (entityType === 'players') renderPlayerGroups(); else renderGroups();
                triggerSaveFeedback();
            }
        }

        // ── Modal Operations ──
        function openNewGroupModal(entityType) {
            modalEntityType = entityType || 'clubs';
            editingIndex = -1;
            modalAliases = [];
            const icon = modalEntityType === 'players' ? '👤' : '🛡️';
            const titleWord = modalEntityType === 'players' ? 'Player' : 'Team';
            document.getElementById('modal-title').innerHTML = `<span>${icon}</span> New ${titleWord} Alias Group`;
            document.getElementById('modal-display-name').value = '';
            document.getElementById('modal-alias-search').value = '';
            document.getElementById('modal-custom-alias-input').value = '';
            document.getElementById('modal-hidden-checkbox').checked = false;
            document.getElementById('modal-display-results').classList.add('hidden');
            document.getElementById('modal-alias-results').classList.add('hidden');
            currentModalDisplayMatches = [];
            currentModalAliasMatches = [];
            renderModalAliases();
            document.getElementById('group-modal').classList.remove('hidden');
        }

        function editGroup(entityType, idx) {
            modalEntityType = entityType;
            editingIndex = idx;
            const list = entityType === 'players' ? config.players.groups : config.clubs.groups;
            const g = list[idx];
            modalAliases = [...g.aliases];
            const icon = modalEntityType === 'players' ? '👤' : '🛡️';
            const titleWord = modalEntityType === 'players' ? 'Player' : 'Team';
            document.getElementById('modal-title').innerHTML = `<span>${icon}</span> Edit ${titleWord} Alias Group`;
            document.getElementById('modal-display-name').value = g.display_name;
            document.getElementById('modal-alias-search').value = '';
            document.getElementById('modal-custom-alias-input').value = '';
            document.getElementById('modal-hidden-checkbox').checked = !!g.hidden;
            document.getElementById('modal-display-results').classList.add('hidden');
            document.getElementById('modal-alias-results').classList.add('hidden');
            currentModalDisplayMatches = [];
            currentModalAliasMatches = [];
            renderModalAliases();
            document.getElementById('group-modal').classList.remove('hidden');
        }

        function closeGroupModal() {
            document.getElementById('group-modal').classList.add('hidden');
        }

        function renderModalAliases() {
            const container = document.getElementById('modal-aliases-container');
            container.innerHTML = '';
            if (modalAliases.length === 0) {
                container.innerHTML = '<span class="text-xs text-slate-500 italic p-1">No aliases attached yet.</span>';
                return;
            }
            modalAliases.forEach((alias, aIdx) => {
                const chip = document.createElement('span');
                chip.className = "bg-slate-800 text-slate-200 text-xs px-2.5 py-1 rounded-md border border-slate-700 flex items-center gap-1.5";
                chip.innerHTML = `
                    <span>${escapeHtml(alias)}</span>
                    <button onclick="removeModalAlias(${aIdx})" class="text-slate-400 hover:text-red-400 font-bold ml-1">&times;</button>
                `;
                container.appendChild(chip);
            });
        }

        function removeModalAlias(aIdx) {
            modalAliases.splice(aIdx, 1);
            renderModalAliases();
        }

        function addCustomAlias() {
            const val = (document.getElementById('modal-custom-alias-input').value || '').trim();
            if (val && !modalAliases.includes(val)) {
                modalAliases.push(val);
                renderModalAliases();
                document.getElementById('modal-custom-alias-input').value = '';
            }
        }

        // ── Autocomplete for Primary Display Name ──
        async function searchModalDisplayName(q) {
            const resultsBox = document.getElementById('modal-display-results');
            q = q.trim();
            if (!q) {
                resultsBox.classList.add('hidden');
                currentModalDisplayMatches = [];
                return;
            }
            try {
                const endpoint = modalEntityType === 'players' ? `/api/search/players?q=${encodeURIComponent(q)}&limit=12` : `/api/search/clubs?q=${encodeURIComponent(q)}&limit=12`;
                const res = await fetch(endpoint);
                const matches = await res.json();
                currentModalDisplayMatches = matches || [];
                
                if (currentModalDisplayMatches.length === 0) {
                    resultsBox.classList.add('hidden');
                    return;
                }

                let html = '';
                if (modalEntityType === 'players') {
                    html = currentModalDisplayMatches.map((p, idx) => {
                        const name = p.Name;
                        const fullName = p.FullName && p.FullName !== name ? p.FullName : '';
                        const dobStr = p.DOB ? `<span class="bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded text-[10px]">b. ${escapeHtml(p.DOB.substring(0, 4))}</span>` : '';
                        const meta = `${p.Position || ''} ${p.Nationality ? '· ' + p.Nationality : ''}`.trim();
                        const clubsStr = p.Clubs ? `<div class="text-[11px] text-slate-400 truncate mt-0.5" title="${escapeAttr(p.Clubs)}">🏟️ ${escapeHtml(p.Clubs)}</div>` : '';
                        
                        return `
                            <div onclick="selectModalDisplayNameIndex(${idx})" class="px-3 py-2 text-xs text-slate-200 hover:bg-slate-800 cursor-pointer border-b border-slate-800/60 last:border-0 transition">
                                <div class="flex items-center justify-between gap-2">
                                    <div class="font-bold text-slate-100 flex items-center gap-1.5">
                                        <span>${escapeHtml(name)}</span>
                                        ${fullName ? `<span class="text-xs text-slate-400 font-normal italic">(${escapeHtml(fullName)})</span>` : ''}
                                    </div>
                                    <div class="flex items-center gap-1 shrink-0">
                                        ${dobStr}
                                        <span class="text-amber-400 text-[10px] font-semibold bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">Select</span>
                                    </div>
                                </div>
                                ${meta ? `<div class="text-[11px] text-amber-300/80 font-medium mt-0.5">${escapeHtml(meta)}</div>` : ''}
                                ${clubsStr}
                            </div>
                        `;
                    }).join('');
                } else {
                    html = currentModalDisplayMatches.map((c, idx) => `
                        <div onclick="selectModalDisplayNameIndex(${idx})" class="px-3 py-2 text-xs text-slate-200 hover:bg-slate-800 cursor-pointer flex justify-between items-center border-b border-slate-800/60 last:border-0">
                            <span class="font-medium">${escapeHtml(c)}</span>
                            <span class="text-amber-400 text-[10px] font-semibold">Select</span>
                        </div>
                    `).join('');
                }

                resultsBox.innerHTML = html;
                resultsBox.classList.remove('hidden');
            } catch (err) {
                console.error(err);
            }
        }

        function selectModalDisplayNameIndex(idx) {
            const item = currentModalDisplayMatches[idx];
            if (!item) return;
            if (modalEntityType === 'players') {
                selectModalDisplayNameItem(item);
            } else {
                selectModalDisplayName(item);
            }
        }

        function selectModalDisplayNameItem(p) {
            const disp = document.getElementById('modal-display-name');
            disp.value = p.FullName || p.Name;
            
            // Auto attach short name or aliases if distinct
            if (p.Name && p.FullName && p.Name !== p.FullName && !modalAliases.includes(p.Name)) {
                modalAliases.push(p.Name);
            }
            renderModalAliases();
            document.getElementById('modal-display-results').classList.add('hidden');
        }

        function selectModalDisplayName(name) {
            document.getElementById('modal-display-name').value = name;
            document.getElementById('modal-display-results').classList.add('hidden');
        }

        // ── Autocomplete for Attached Aliases ──
        async function searchModalAliases(q) {
            const resultsBox = document.getElementById('modal-alias-results');
            q = q.trim();
            if (!q) {
                resultsBox.classList.add('hidden');
                currentModalAliasMatches = [];
                return;
            }
            try {
                const endpoint = modalEntityType === 'players' ? `/api/search/players?q=${encodeURIComponent(q)}&limit=12` : `/api/search/clubs?q=${encodeURIComponent(q)}&limit=12`;
                const res = await fetch(endpoint);
                const matches = await res.json();
                currentModalAliasMatches = matches || [];
                
                let html = `
                    <div onclick="addModalCustomAliasFromSearch()" class="px-3 py-2 text-xs text-amber-300 hover:bg-slate-800 cursor-pointer flex justify-between items-center bg-amber-950/30 border-b border-slate-800">
                        <div class="flex items-center gap-1.5 font-semibold">
                            <span class="text-amber-400">➕</span>
                            <span>Add &ldquo;${escapeHtml(q)}&rdquo; as custom alias</span>
                        </div>
                        <span class="text-slate-400 text-[10px] font-mono uppercase bg-slate-900 px-1.5 py-0.5 rounded border border-slate-700">↵ Enter</span>
                    </div>
                `;

                if (currentModalAliasMatches.length > 0) {
                    if (modalEntityType === 'players') {
                        html += currentModalAliasMatches.map((p, idx) => {
                            const name = p.Name;
                            const fullName = p.FullName && p.FullName !== name ? p.FullName : '';
                            const meta = `${p.Position || ''} ${p.Nationality ? '· ' + p.Nationality : ''}`.trim();
                            const clubsStr = p.Clubs ? `<div class="text-[10px] text-slate-400 truncate" title="${escapeAttr(p.Clubs)}">🏟️ ${escapeHtml(p.Clubs)}</div>` : '';
                            return `
                                <div onclick="selectModalAliasIndex(${idx})" class="px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 cursor-pointer border-b border-slate-800/60 last:border-0 flex flex-col gap-0.5">
                                    <div class="flex justify-between items-center">
                                        <div class="font-medium text-slate-100">${escapeHtml(name)} ${fullName ? `<span class="text-[11px] text-slate-400 italic">(${escapeHtml(fullName)})</span>` : ''}</div>
                                        <span class="text-amber-400 text-[10px] uppercase font-semibold">+ Add</span>
                                    </div>
                                    ${meta ? `<div class="text-[10px] text-amber-300/70">${escapeHtml(meta)}</div>` : ''}
                                    ${clubsStr}
                                </div>
                            `;
                        }).join('');
                    } else {
                        html += currentModalAliasMatches.map((c, idx) => `
                            <div onclick="selectModalAliasIndex(${idx})" class="px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 cursor-pointer flex justify-between items-center border-b border-slate-800/60 last:border-0">
                                <span class="font-medium">${escapeHtml(c)}</span>
                                <span class="text-amber-400 text-[10px] uppercase font-semibold">+ Add</span>
                            </div>
                        `).join('');
                    }
                }
                
                resultsBox.innerHTML = html;
                resultsBox.classList.remove('hidden');
            } catch (err) {
                console.error(err);
            }
        }

        function addModalCustomAliasFromSearch() {
            const input = document.getElementById('modal-alias-search');
            const q = (input.value || '').trim();
            if (q) {
                selectModalAlias(q);
            }
        }

        function selectModalAliasIndex(idx) {
            const item = currentModalAliasMatches[idx];
            if (!item) return;
            const alias = typeof item === 'object' ? item.Name : item;
            selectModalAlias(alias);
        }

        function selectModalAlias(alias) {
            if (!modalAliases.includes(alias)) {
                modalAliases.push(alias);
                renderModalAliases();
            }
            const disp = document.getElementById('modal-display-name');
            if (!disp.value.trim()) disp.value = alias;
            document.getElementById('modal-alias-search').value = '';
            document.getElementById('modal-alias-results').classList.add('hidden');
        }

        function saveGroupModal() {
            const displayName = (document.getElementById('modal-display-name').value || '').trim();
            if (!displayName) {
                alert('Please enter a Primary Display Name.');
                return;
            }
            const isHidden = document.getElementById('modal-hidden-checkbox').checked;
            const newGroup = {
                display_name: displayName,
                aliases: modalAliases.filter(a => a !== displayName),
                hidden: isHidden
            };

            const list = modalEntityType === 'players' ? config.players.groups : config.clubs.groups;
            if (editingIndex >= 0) {
                list[editingIndex] = newGroup;
            } else {
                list.unshift(newGroup);
            }

            updateStats();
            if (modalEntityType === 'players') renderPlayerGroups(); else renderGroups();
            closeGroupModal();
            triggerSaveFeedback();
        }

        // ── TAB 3: Hidden Clubs ──
        function renderHiddenClubs() {
            const container = document.getElementById('hidden-clubs-chips');
            container.innerHTML = '';
            const list = config.clubs.hidden_standalone;
            if (list.length === 0) {
                container.innerHTML = '<p class="text-xs text-slate-500 italic">No standalone hidden clubs.</p>';
                return;
            }
            list.forEach((c, idx) => {
                const chip = document.createElement('span');
                chip.className = "bg-red-500/10 border border-red-500/30 text-red-300 text-xs px-3 py-1 rounded-lg flex items-center gap-2";
                chip.innerHTML = `
                    <span>${escapeHtml(c)}</span>
                    <button onclick="removeHiddenClub(${idx})" class="text-red-400 hover:text-red-100 font-bold">&times;</button>
                `;
                container.appendChild(chip);
            });
        }

        async function searchClubToHide(q) {
            const resultsBox = document.getElementById('hide-club-results');
            q = q.trim();
            if (!q) {
                resultsBox.classList.add('hidden');
                currentHideClubMatches = [];
                return;
            }
            try {
                const res = await fetch(`/api/search/clubs?q=${encodeURIComponent(q)}&limit=15`);
                const matches = await res.json();
                currentHideClubMatches = matches || [];
                if (currentHideClubMatches.length === 0) {
                    resultsBox.innerHTML = '<div class="p-2 text-xs text-slate-500">No clubs found</div>';
                } else {
                    resultsBox.innerHTML = currentHideClubMatches.map((c, idx) => `
                        <div onclick="addHiddenClubIndex(${idx})" class="px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 cursor-pointer flex justify-between items-center">
                            <span>${escapeHtml(c)}</span>
                            <span class="text-red-400 text-[10px] uppercase font-semibold">Hide</span>
                        </div>
                    `).join('');
                }
                resultsBox.classList.remove('hidden');
            } catch (err) {
                console.error(err);
            }
        }

        function addHiddenClubIndex(idx) {
            const c = currentHideClubMatches[idx];
            if (c) addHiddenClub(c);
        }

        function addHiddenClub(club) {
            if (!config.clubs.hidden_standalone.includes(club)) {
                config.clubs.hidden_standalone.push(club);
                renderHiddenClubs();
                updateStats();
                triggerSaveFeedback();
            }
            document.getElementById('hide-club-input').value = '';
            document.getElementById('hide-club-results').classList.add('hidden');
        }

        function removeHiddenClub(idx) {
            config.clubs.hidden_standalone.splice(idx, 1);
            renderHiddenClubs();
            updateStats();
            triggerSaveFeedback();
        }

        // ── TAB 4: Hidden Players ──
        function renderHiddenPlayers() {
            const container = document.getElementById('hidden-players-chips');
            container.innerHTML = '';
            const list = config.players.hidden || [];
            if (list.length === 0) {
                container.innerHTML = '<div class="col-span-full py-8 text-center text-slate-500"><p class="text-xs italic">No hidden players configured yet. Search any player above to hide them.</p></div>';
                return;
            }
            list.forEach((p, idx) => {
                const card = document.createElement('div');
                card.className = "bg-slate-900 border border-slate-800 hover:border-red-500/30 p-3.5 rounded-xl flex flex-col justify-between gap-3 shadow-sm transition group";
                
                let name = typeof p === 'object' ? p.Name : p;
                let fullName = typeof p === 'object' && p.FullName && p.FullName !== name ? p.FullName : '';
                let dob = typeof p === 'object' && p.DOB ? p.DOB : '';
                let pos = typeof p === 'object' && p.Position ? p.Position : '';
                let nat = typeof p === 'object' && p.Nationality ? p.Nationality : '';
                let clubs = typeof p === 'object' && p.Clubs ? p.Clubs : '';

                card.innerHTML = `
                    <div class="space-y-1.5">
                        <div class="flex items-start justify-between gap-2">
                            <div>
                                <div class="font-bold text-slate-100 text-sm flex items-center gap-1.5">
                                    <span class="text-amber-400">👤</span>
                                    <span>${escapeHtml(name)}</span>
                                </div>
                                ${fullName ? `<div class="text-xs text-slate-300 font-medium italic mt-0.5">${escapeHtml(fullName)}</div>` : ''}
                            </div>
                            <span class="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-red-500/20 text-red-400 border border-red-500/30">Hidden</span>
                        </div>
                        
                        <div class="flex flex-wrap gap-1.5 pt-1">
                            ${dob ? `<span class="text-[10px] bg-slate-800 text-slate-400 px-2 py-0.5 rounded border border-slate-700">b. ${escapeHtml(dob.substring(0, 4))}</span>` : ''}
                            ${pos ? `<span class="text-[10px] bg-slate-800/80 text-amber-300/80 px-2 py-0.5 rounded border border-slate-700">${escapeHtml(pos)}</span>` : ''}
                            ${nat ? `<span class="text-[10px] bg-slate-800/80 text-slate-300 px-2 py-0.5 rounded border border-slate-700">${escapeHtml(nat)}</span>` : ''}
                        </div>

                        ${clubs ? `<div class="text-[11px] text-slate-400 pt-1 leading-snug"><span class="text-slate-500 font-medium">Clubs:</span> <span class="text-slate-300">${escapeHtml(clubs)}</span></div>` : ''}
                    </div>

                    <div class="pt-2 border-t border-slate-800/80 flex justify-end">
                        <button onclick="removeHiddenPlayer(${idx})" class="text-xs text-red-400 hover:text-red-200 hover:underline flex items-center gap-1 font-semibold">
                            <span>Unhide Player</span> &times;
                        </button>
                    </div>
                `;
                container.appendChild(card);
            });
        }

        async function searchPlayerToHide(q) {
            const resultsBox = document.getElementById('hide-player-results');
            q = q.trim();
            if (!q) {
                resultsBox.classList.add('hidden');
                currentHidePlayerMatches = [];
                return;
            }
            try {
                const res = await fetch(`/api/search/players?q=${encodeURIComponent(q)}&limit=15`);
                const matches = await res.json();
                currentHidePlayerMatches = matches || [];
                if (currentHidePlayerMatches.length === 0) {
                    resultsBox.innerHTML = '<div class="p-3 text-xs text-slate-500 text-center">No players found</div>';
                } else {
                    resultsBox.innerHTML = currentHidePlayerMatches.map((p, idx) => {
                        const fullName = p.FullName && p.FullName !== p.Name ? p.FullName : '';
                        const dobStr = p.DOB ? `<span class="bg-slate-800 text-slate-400 px-1.5 py-0.5 rounded text-[10px]">b. ${escapeHtml(p.DOB.substring(0, 4))}</span>` : '';
                        const meta = `${p.Position || ''} ${p.Nationality ? '· ' + p.Nationality : ''}`.trim();
                        const clubsStr = p.Clubs ? `<div class="text-[11px] text-slate-400 truncate mt-0.5" title="${escapeAttr(p.Clubs)}">🏟️ ${escapeHtml(p.Clubs)}</div>` : '';

                        return `
                            <div onclick="addHiddenPlayerIndex(${idx})" class="px-3 py-2 text-xs text-slate-200 hover:bg-slate-800 cursor-pointer border-b border-slate-800/60 last:border-0 transition flex flex-col gap-0.5">
                                <div class="flex items-center justify-between gap-2">
                                    <div class="font-bold text-slate-100 flex items-center gap-1.5">
                                        <span>${escapeHtml(p.Name)}</span>
                                        ${fullName ? `<span class="text-xs text-slate-400 font-normal italic">(${escapeHtml(fullName)})</span>` : ''}
                                    </div>
                                    <div class="flex items-center gap-1.5 shrink-0">
                                        ${dobStr}
                                        <span class="text-red-400 text-[10px] uppercase font-bold bg-red-500/10 px-2 py-0.5 rounded border border-red-500/20 hover:bg-red-500/20">Hide</span>
                                    </div>
                                </div>
                                ${meta ? `<div class="text-[11px] text-amber-300/80 font-medium">${escapeHtml(meta)}</div>` : ''}
                                ${clubsStr}
                            </div>
                        `;
                    }).join('');
                }
                resultsBox.classList.remove('hidden');
            } catch (err) {
                console.error(err);
            }
        }

        function addHiddenPlayerIndex(idx) {
            const p = currentHidePlayerMatches[idx];
            if (p) addHiddenPlayerObject(p);
        }

        function addHiddenPlayerObject(p) {
            if (!config.players.hidden) config.players.hidden = [];
            
            // Check uniqueness by matching Name, FullName, DOB, and Position
            const pKey = `${(p.Name || '').toLowerCase()}|${(p.FullName || p.Name || '').toLowerCase()}|${p.DOB || ''}|${(p.Position || '').toLowerCase()}`;
            const exists = config.players.hidden.some(item => {
                if (typeof item === 'object') {
                    const iKey = `${(item.Name || '').toLowerCase()}|${(item.FullName || item.Name || '').toLowerCase()}|${item.DOB || ''}|${(item.Position || '').toLowerCase()}`;
                    return iKey === pKey;
                }
                return item.toLowerCase() === (p.Name || '').toLowerCase();
            });

            if (!exists) {
                config.players.hidden.push({
                    Name: p.Name,
                    FullName: p.FullName || p.Name,
                    DOB: p.DOB || '',
                    Nationality: p.Nationality || '',
                    Position: p.Position || '',
                    Clubs: p.Clubs || ''
                });
                renderHiddenPlayers();
                updateStats();
                triggerSaveFeedback();
            }
            document.getElementById('hide-player-input').value = '';
            document.getElementById('hide-player-results').classList.add('hidden');
        }

        function removeHiddenPlayer(idx) {
            config.players.hidden.splice(idx, 1);
            renderHiddenPlayers();
            updateStats();
            triggerSaveFeedback();
        }

        // ── Save Config & Sync Games ──
        async function saveConfig() {
            try {
                showSavedBanner('Saving & Syncing...');
                const res = await fetch('/api/config', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(config)
                });
                const data = await res.json();
                if (data.status === 'success') {
                    config = data.config;
                    showSavedBanner('Saved & Synced! ⚡');
                } else {
                    alert('Error saving config: ' + data.message);
                }
            } catch (err) {
                alert('Network error saving config: ' + err);
            }
        }

        async function syncGames() {
            const btn = document.getElementById('sync-games-btn');
            const txt = document.getElementById('sync-btn-text');
            const spin = document.getElementById('sync-spinner');
            try {
                btn.disabled = true;
                txt.textContent = 'Compiling...';
                spin.classList.add('animate-spin');
                showSavedBanner('Recompiling games...');

                const res = await fetch('/api/sync-games', { method: 'POST' });
                const data = await res.json();
                if (data.status === 'success') {
                    showSavedBanner('Games Recompiled! ✅');
                } else {
                    alert('Sync error: ' + (data.message || 'Unknown error'));
                }
            } catch (err) {
                alert('Network error syncing games: ' + err);
            } finally {
                btn.disabled = false;
                txt.textContent = 'Sync Games';
                spin.classList.remove('animate-spin');
            }
        }

        function triggerSaveFeedback() {
            saveConfig();
        }

        function showSavedBanner(msg = 'Saved & Synced') {
            const b = document.getElementById('save-status');
            b.textContent = msg;
            b.classList.remove('hidden');
            setTimeout(() => { b.classList.add('hidden'); }, 3000);
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&#039;");
        }
        function escapeAttr(str) {
            if (!str) return '';
            return String(str).replace(/'/g, "\\\\'").replace(/"/g, "&quot;");
        }

        // Close search dropdowns when clicking outside
        document.addEventListener('click', function(e) {
            if (!e.target.closest('#modal-display-name') && !e.target.closest('#modal-display-results')) {
                const el = document.getElementById('modal-display-results');
                if (el) el.classList.add('hidden');
            }
            if (!e.target.closest('#modal-alias-search') && !e.target.closest('#modal-alias-results')) {
                const el = document.getElementById('modal-alias-results');
                if (el) el.classList.add('hidden');
            }
            if (!e.target.closest('#hide-player-input') && !e.target.closest('#hide-player-results')) {
                const el = document.getElementById('hide-player-results');
                if (el) el.classList.add('hidden');
            }
            if (!e.target.closest('#hide-club-input') && !e.target.closest('#hide-club-results')) {
                const el = document.getElementById('hide-club-results');
                if (el) el.classList.add('hidden');
            }
        });

        init();
    </script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(PORTAL_HTML)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"==================================================")
    print(f"⚽ Playmaker Aliases & Dropdown Portal")
    print(f"🌐 Running on: http://localhost:{port}")
    print(f"==================================================")
    app.run(host="0.0.0.0", port=port, debug=False)
