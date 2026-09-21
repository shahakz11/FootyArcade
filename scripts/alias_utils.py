"""
scripts/alias_utils.py

Shared utilities for loading, saving, querying, and applying alias groups
and hidden statuses for clubs and players.
Used by:
  - scripts/alias_portal.py (the local GUI portal)
  - build_transfer_datasets.py (pipeline dataset generation)
  - fetch_daily.py (daily games HTML compilation)
"""

import os
import json
import re
import unicodedata

CONFIG_RELATIVE_PATH = os.path.join("data", "aliases_config.json")
LEGACY_CONFIG_RELATIVE_PATH = os.path.join("private", "aliases_config.json")


def normalize_search_text(text):
    """
    Normalizes a search query or entity name:
      - Strips invisible unicode marks
      - Maps special characters (ø->o, ł->l, đ->d, æ->ae, œ->oe, ß->ss, etc.)
      - Strips NFD diacritics / accents (e.g. ü -> u, ö -> o, é -> e)
      - Normalizes punctuation (-._') to spaces
      - Lowercases and collapses multiple spaces
    e.g. 'Nürnberg' -> 'nurnberg', 'Mönchengladbach' -> 'monchengladbach'
    """
    if not text:
        return ''
    s = str(text)
    s = re.sub(r'[\u200b-\u200f\u202a-\u202e\ufeff]', '', s)
    replacements = {
        'ð': 'd', 'Ð': 'D', 'þ': 'th', 'Þ': 'Th',
        'ø': 'o', 'Ø': 'O', 'ł': 'l', 'Ł': 'L',
        'đ': 'd', 'Đ': 'D', 'æ': 'ae', 'Æ': 'Ae',
        'œ': 'oe', 'Œ': 'Oe', 'ß': 'ss',
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    s = ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')
    s = s.lower()
    s = re.sub(r'[-._\']', ' ', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()


def get_config_path(root_dir=None, for_writing=False):
    """
    Return the path to aliases_config.json.
    Prioritizes data/aliases_config.json (tracked in git for production deployment).
    Falls back to legacy private/aliases_config.json if data/ does not exist during reads.
    """
    if not root_dir:
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(cur_dir, ".."))
    
    primary_path = os.path.join(root_dir, CONFIG_RELATIVE_PATH)
    if for_writing:
        return primary_path

    if os.path.exists(primary_path):
        return primary_path
    
    legacy_path = os.path.join(root_dir, LEGACY_CONFIG_RELATIVE_PATH)
    if os.path.exists(legacy_path):
        return legacy_path

    return primary_path


def load_aliases_config(root_dir=None):
    """
    Load aliases_config.json from data/ (or legacy private/) folder.
    If missing or invalid, returns an empty default schema.
    """
    path = get_config_path(root_dir)
    default_cfg = {
        "version": 1,
        "clubs": {
            "groups": [],
            "hidden_standalone": []
        },
        "players": {
            "groups": [],
            "hidden": []
        }
    }

    if not os.path.exists(path):
        return default_cfg

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return default_cfg
            if "clubs" not in data or not isinstance(data["clubs"], dict):
                data["clubs"] = default_cfg["clubs"]
            if "groups" not in data["clubs"] or not isinstance(data["clubs"]["groups"], list):
                data["clubs"]["groups"] = []
            if "hidden_standalone" not in data["clubs"] or not isinstance(data["clubs"]["hidden_standalone"], list):
                data["clubs"]["hidden_standalone"] = []
            if "players" not in data or not isinstance(data["players"], dict):
                data["players"] = default_cfg["players"]
            if "groups" not in data["players"] or not isinstance(data["players"]["groups"], list):
                data["players"]["groups"] = []
            if "hidden" not in data["players"] or not isinstance(data["players"]["hidden"], list):
                data["players"]["hidden"] = []
            return data
    except Exception as e:
        print(f"[alias_utils] Warning: Error reading {path}: {e}")
        return default_cfg


def save_aliases_config(config, root_dir=None):
    """
    Atomically save aliases_config.json to data/aliases_config.json.
    """
    path = get_config_path(root_dir, for_writing=True)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    os.replace(tmp_path, path)
    return True


def get_club_alias_map(config):
    """
    Returns a dictionary mapping every variant (including display_name itself and aliases)
    to its canonical display_name.
    e.g. {'FC Bayern': 'Bayern Munich', 'Bayern München': 'Bayern Munich', 'Bayern Munich': 'Bayern Munich'}
    """
    alias_map = {}
    if not config or "clubs" not in config:
        return alias_map

    for group in config.get("clubs", {}).get("groups", []):
        display_name = group.get("display_name", "").strip()
        if not display_name:
            continue
        alias_map[display_name] = display_name
        for alias in group.get("aliases", []):
            a_clean = alias.strip()
            if a_clean:
                alias_map[a_clean] = display_name
    return alias_map


def get_player_alias_map(config):
    """
    Returns a dictionary mapping every player alias variant (including display_name itself)
    to its canonical display_name.
    e.g. {'Raphael Dias Belloli': 'Raphinha', 'Raphinha': 'Raphinha'}
    """
    alias_map = {}
    if not config or "players" not in config:
        return alias_map

    for group in config.get("players", {}).get("groups", []):
        display_name = group.get("display_name", "").strip()
        if not display_name:
            continue
        alias_map[display_name] = display_name
        for alias in group.get("aliases", []):
            a_clean = alias.strip()
            if a_clean:
                alias_map[a_clean] = display_name
    return alias_map


def get_club_alias_groups(config):
    """
    Returns a dictionary mapping canonical club display_name to its list of aliases.
    e.g. {'Manchester City': ['Man City', 'Man. City']}
    """
    groups = {}
    if not config or "clubs" not in config:
        return groups
    for g in config.get("clubs", {}).get("groups", []):
        d = g.get("display_name", "").strip()
        if d:
            aliases = [a.strip() for a in g.get("aliases", []) if a.strip()]
            if aliases:
                groups[d] = aliases
    return groups


def get_player_alias_groups(config):
    """
    Returns a dictionary mapping canonical player display_name to its list of aliases.
    e.g. {'Rafinha': ['Rafael Alcantara', 'Rafinha Alcantara']}
    """
    groups = {}
    if not config or "players" not in config:
        return groups
    for g in config.get("players", {}).get("groups", []):
        d = g.get("display_name", "").strip()
        if d:
            aliases = [a.strip() for a in g.get("aliases", []) if a.strip()]
            if aliases:
                groups[d] = aliases
    return groups


def get_hidden_clubs(config):
    """
    Returns a set of club names that should be hidden from dropdowns / games.
    Includes clubs from groups flagged with 'hidden': True, plus 'hidden_standalone'.
    """
    hidden = set()
    if not config or "clubs" not in config:
        return hidden

    clubs_cfg = config.get("clubs", {})
    # Groups marked hidden
    for group in clubs_cfg.get("groups", []):
        if group.get("hidden", False):
            display = group.get("display_name", "").strip()
            if display:
                hidden.add(display)
            for a in group.get("aliases", []):
                if a.strip():
                    hidden.add(a.strip())

    # Standalone hidden
    for c in clubs_cfg.get("hidden_standalone", []):
        if c and isinstance(c, str) and c.strip():
            hidden.add(c.strip())

    return hidden


def get_hidden_players(config):
    """
    Returns a set of player names that should be hidden from player dropdowns.
    Includes players from player groups flagged with 'hidden': True, plus standalone hidden players.
    """
    hidden = set()
    if not config or "players" not in config:
        return hidden

    players_cfg = config.get("players", {})
    for group in players_cfg.get("groups", []):
        if group.get("hidden", False):
            display = group.get("display_name", "").strip()
            if display:
                hidden.add(display)
            for a in group.get("aliases", []):
                if a.strip():
                    hidden.add(a.strip())

    for p in players_cfg.get("hidden", []):
        if isinstance(p, str) and p.strip():
            hidden.add(p.strip())
        elif isinstance(p, dict):
            name = (p.get("Name") or p.get("name") or "").strip()
            full_name = (p.get("FullName") or p.get("full_name") or "").strip()
            if name:
                hidden.add(name)
            if full_name:
                hidden.add(full_name)
    return hidden


def filter_and_canonicalize_clubs(club_list, config, as_objects=False):
    """
    Takes a raw list of club names (strings or dicts):
      1. Translates names to canonical display names using alias map.
      2. Deduplicates while preserving order or descending market value.
      3. Removes any club in the hidden set.
      4. If as_objects=True, returns list of dicts: {'name': canonical, 'aliases': [...], 'market_value': ...}.
    Returns: cleaned list of strings or objects.
    """
    alias_map = get_club_alias_map(config)
    club_groups = get_club_alias_groups(config)
    hidden_clubs = get_hidden_clubs(config)
    hidden_lower = {h.lower() for h in hidden_clubs}

    result = []
    seen = {} # canonical.lower() -> index in result
    
    for item in club_list:
        val = 0
        if isinstance(item, dict):
            c = (item.get("name") or item.get("Name") or "").strip()
            val = int(item.get("market_value") or item.get("MarketValue") or 0)
        elif isinstance(item, str):
            c = item.strip()
        else:
            continue

        if not c:
            continue

        canonical = alias_map.get(c, c)
        if canonical.lower() in hidden_lower:
            continue

        c_lower = canonical.lower()
        if c_lower not in seen:
            seen[c_lower] = len(result)
            if as_objects:
                result.append({
                    "name": canonical,
                    "aliases": club_groups.get(canonical, []),
                    "market_value": val
                })
            else:
                result.append(canonical)
        else:
            # If already seen as object and this instance has a higher market value, update it
            if as_objects:
                idx = seen[c_lower]
                if val > result[idx].get("market_value", 0):
                    result[idx]["market_value"] = val

    # 5. Guarantee any configured club group is included if not already present
    c_groups_list = config.get("clubs", {}).get("groups", [])
    for g in c_groups_list:
        d_name = g.get("display_name", "").strip()
        if d_name and d_name.lower() not in seen and d_name.lower() not in hidden_lower:
            seen[d_name.lower()] = len(result)
            if as_objects:
                result.append({
                    "name": d_name,
                    "aliases": g.get("aliases", []),
                    "market_value": int(g.get("market_value", 0))
                })
            else:
                result.append(d_name)

    return result



def filter_and_canonicalize_players(player_list, config):
    """
    Takes a raw list of player dicts or player names (strings):
      1. Translates names to canonical display names using player alias map.
      2. Deduplicates by (name, position, nationality) for dicts so distinct homonym players are preserved.
      3. Removes any player in the hidden set.
      4. Attaches 'Aliases' list to each player dict if defined in config.
      5. Ensures all configured player alias groups are present in the list.
    Returns: cleaned list.
    """
    alias_map = get_player_alias_map(config)
    player_groups = get_player_alias_groups(config)
    hidden_players = get_hidden_players(config)
    hidden_lower = {h.lower() for h in hidden_players}

    result = []
    seen = set()
    seen_names = set()

    for item in player_list:
        if isinstance(item, dict):
            raw_name = (item.get("Name") or item.get("name") or item.get("player_name") or "").strip()
            if not raw_name:
                continue
            canonical = alias_map.get(raw_name, raw_name)
            if canonical.lower() in hidden_lower:
                continue
            
            pos = (item.get("Position") or item.get("position") or "").strip().lower()
            nat = (item.get("Nationality") or item.get("nationality") or "").strip().lower()
            val = str(item.get("MarketValue") or item.get("market_value") or 0)
            dedupe_key = (canonical.lower(), pos, nat, val)

            if dedupe_key not in seen:
                seen.add(dedupe_key)
                seen_names.add(canonical.lower())
                c_item = dict(item)
                if "Name" in c_item:
                    c_item["Name"] = canonical
                elif "name" in c_item:
                    c_item["name"] = canonical
                elif "player_name" in c_item:
                    c_item["player_name"] = canonical
                
                # Attach aliases for search matching
                if canonical in player_groups:
                    c_item["Aliases"] = player_groups[canonical]
                
                # If it's an '(All)' alias, omit position and nationality / country
                if re.search(r'\(\s*all\s*\)$', canonical, re.IGNORECASE):
                    if "Nationality" in c_item: c_item["Nationality"] = ""
                    if "nationality" in c_item: c_item["nationality"] = ""
                    if "Position" in c_item: c_item["Position"] = ""
                    if "position" in c_item: c_item["position"] = ""
                result.append(c_item)
        elif isinstance(item, str):
            c = item.strip()
            if not c:
                continue
            canonical = alias_map.get(c, c)
            if canonical.lower() in hidden_lower:
                continue
            if canonical.lower() not in seen:
                seen.add(canonical.lower())
                seen_names.add(canonical.lower())
                result.append(canonical)
        else:
            result.append(item)

    # 5. Guarantee any configured player group is included if not already present
    p_groups_list = config.get("players", {}).get("groups", [])
    for g in p_groups_list:
        d_name = g.get("display_name", "").strip()
        if d_name and d_name.lower() not in seen_names and d_name.lower() not in hidden_lower:
            seen_names.add(d_name.lower())
            is_all_alias = bool(re.search(r'\(\s*all\s*\)$', d_name, re.IGNORECASE))
            result.append({
                "Name": d_name,
                "Nationality": "",
                "Position": "" if is_all_alias else "Player",
                "MarketValue": 0,
                "Aliases": g.get("aliases", [])
            })

    return result




def separate_alias(entity_type, group_display_name, alias_to_separate, new_display_name=None, config=None, root_dir=None):
    """
    Separates an alias out of an existing group into its own standalone group.
    """
    is_custom_config = config is not None
    if config is None:
        config = load_aliases_config(root_dir)

    target_key = "players" if entity_type == "players" else "clubs"
    groups = config.get(target_key, {}).get("groups", [])

    found_group = None
    for g in groups:
        if g.get("display_name", "").strip().lower() == group_display_name.strip().lower():
            found_group = g
            break

    if not found_group:
        return False, f"Group '{group_display_name}' not found in {target_key}.", config

    # Remove alias from existing group
    original_aliases = found_group.get("aliases", [])
    new_aliases = [a for a in original_aliases if a.strip().lower() != alias_to_separate.strip().lower()]
    found_group["aliases"] = new_aliases

    # Create new independent group for the separated alias
    sep_display = (new_display_name or alias_to_separate).strip()
    if sep_display:
        # Check if group already exists
        exists = any(g.get("display_name", "").strip().lower() == sep_display.lower() for g in groups)
        if not exists:
            groups.append({
                "display_name": sep_display,
                "aliases": [],
                "hidden": False
            })

    if not is_custom_config:
        save_aliases_config(config, root_dir)
    return True, f"Separated '{alias_to_separate}' from '{group_display_name}' into its own group '{sep_display}'.", config


# Backwards compatibility alias
filter_hidden_players = filter_and_canonicalize_players


KNOWN_CANONICAL_CLUBS = {
    'olymp lyon': 'Lyon',
    'ol lyon': 'Lyon',
    'olympique lyon': 'Lyon',
    'olympique lyonnais': 'Lyon',
    'fenerbahce': 'Fenerbahce',
    'fenerbahce sk': 'Fenerbahce',
    'fc schalke 04': 'FC Schalke 04',
    'schalke 04': 'FC Schalke 04',
    'schalke': 'FC Schalke 04',
    'e frankfurt': 'Eintracht Frankfurt',
    'frankfurt': 'Eintracht Frankfurt',
    'eintracht frankfurt': 'Eintracht Frankfurt',
    'krc genk': 'KRC Genk',
    'genk': 'KRC Genk',
    'sporting lisbon': 'Sporting CP',
    'barca': 'Barcelona',
    'fc barcelona': 'Barcelona',
    'inter milan': 'Inter',
    'internazionale': 'Inter',
    'fc internazionale milano': 'Inter',
    'as roma': 'Roma',
    'psg': 'Paris Saint-Germain',
    'paris sg': 'Paris Saint-Germain',
    'atletico de madrid': 'Atletico Madrid',
    'atletico madrid': 'Atletico Madrid',
    'sheff utd': 'Sheffield United',
    'sheffield utd': 'Sheffield United',
    'sheffield united': 'Sheffield United',
    'forest': "Nottingham Forest",
    'nott m forest': "Nottingham Forest",
    'nottingham forest': "Nottingham Forest",
    'eto': "ETO Győr",
    'eto gyor': "ETO Győr",
    'salzburg': "Red Bull Salzburg",
    'rb salzburg': "Red Bull Salzburg",
    'red bull salzburg': "Red Bull Salzburg",
    'r sociedad': "Real Sociedad",
    'r. sociedad': "Real Sociedad",
    'milan': "AC Milan",
    'ac milan': "AC Milan",
    'rm': "Real Madrid",
    'real madrid castilla': "Real Madrid",
    'castilla': "Real Madrid",
    'real madrid b': "Real Madrid",
}


DUMMY_STATUS_CLUBS = {
    'without club', 'without', 'without team', 'retired', 'career break',
    'unknown', 'end of career', 'ban', 'suspended', 'unknown club', 'unattached', 'none'
}

CLUB_PREFIX_RE = re.compile(r'^(1\.\s*FC|1\.\s*FSV|1\.\s*|FC|CF|AC|AS|SS|SV|SC|SD|CD|UD|RC|RCD|FK|SK|BK|IF|IFK|OGC|US|USM|GC|AFC|SAD|CA|CE|CS|CP|VfB|VfL|TSG|BSC|FSV|SSV|SpVgg|Club)\s+', re.I)
CLUB_SUFFIX_RE = re.compile(r'\s+(Football Club|Association Football Club|Club de Fútbol|Club de Futbol|Fútbol Club|Futbol Club|Soccer Club|Sports Club|Sport Club|Athletic Club|Club|FC|CF|SC|CSC|S\.A\.D\.|R\.C\.D\.|C\.D\.|F\.C\.|C\.F\.|AF|FK|SK|BK|SV|EV|e\.V\.|eV|AC|SD|UD|RC|SAD|Res|Reserves|Youth|Yth|Academy|Junioren|Castilla|II|B|U-?\d+|Sub-?\d+|Sub\s*\d+|Under-?\d+|Under\s*\d+)\b', re.I)


def canonical_club_name(c, alias_map=None):
    """Returns canonical display name for a club, stripping diacritics / aliases / youth prefixes & suffixes."""
    if not c or not isinstance(c, str):
        return ''
    c_clean = c.strip().strip('.').strip('"').strip("'")
    if not c_clean or c_clean.lower() in DUMMY_STATUS_CLUBS:
        return ''
    if alias_map and c_clean in alias_map:
        return alias_map[c_clean]
    norm = normalize_search_text(c_clean)
    if alias_map:
        for k, v in alias_map.items():
            if normalize_search_text(k) == norm:
                return v
    if norm in KNOWN_CANONICAL_CLUBS:
        return KNOWN_CANONICAL_CLUBS[norm]

    # Try stripping prefix & suffix (e.g. LOSC Lille -> Lille, Sporting U19 -> Sporting CP)
    stripped = CLUB_PREFIX_RE.sub('', c_clean)
    stripped = CLUB_SUFFIX_RE.sub('', stripped)
    stripped = CLUB_PREFIX_RE.sub('', stripped)
    stripped = CLUB_SUFFIX_RE.sub('', stripped).strip().strip('.')
    if stripped and stripped.lower() not in DUMMY_STATUS_CLUBS:
        if alias_map and stripped in alias_map:
            return alias_map[stripped]
        stripped_norm = normalize_search_text(stripped)
        if alias_map:
            for k, v in alias_map.items():
                if normalize_search_text(k) == stripped_norm:
                    return v
        if stripped_norm in KNOWN_CANONICAL_CLUBS:
            return KNOWN_CANONICAL_CLUBS[stripped_norm]
        if stripped.startswith('Al ') and not stripped.startswith('Al-'):
            stripped = 'Al-' + stripped[3:]
        return stripped

    return c_clean


def clean_career_transfers(records, alias_map=None):
    """
    Cleans, deduplicates, and normalizes a player's career transfers for Transfer Destination quiz:
      - Canonicalizes club names using alias map, prefix/suffix stripping & accent normalization
      - Filters out dummy status clubs ('Without Club', 'Retired') and same-club moves
      - Sorts chronologically by transfer date
      - Deduplicates identical (from_club, to_club) records and exact same-date duplicate entries (merging fees & transfer_type)
    """
    parsed = []
    for r in records:
        from_c = canonical_club_name(r.get('from_club_name', ''), alias_map)
        to_c = canonical_club_name(r.get('to_club_name', ''), alias_map)
        if not from_c or not to_c or from_c.lower() in DUMMY_STATUS_CLUBS or to_c.lower() in DUMMY_STATUS_CLUBS or normalize_search_text(from_c) == normalize_search_text(to_c):
            continue
        rec = dict(r)
        rec['from_club_name'] = from_c
        rec['to_club_name'] = to_c
        try:
            rec['transfer_fee'] = float(r.get('transfer_fee', 0.0) or 0.0)
        except Exception:
            rec['transfer_fee'] = 0.0
        try:
            rec['market_value_in_eur'] = float(r.get('market_value_in_eur', 0.0) or 0.0)
        except Exception:
            rec['market_value_in_eur'] = 0.0
        t_type = str(r.get('transfer_type', '') or '').strip()
        rec['transfer_type'] = '' if t_type.lower() == 'nan' else t_type
        rec['transfer_date'] = str(r.get('transfer_date', r.get('transfer_date_str', '')) or '').strip()
        parsed.append(rec)

    # Sort chronologically
    parsed.sort(key=lambda x: str(x.get('transfer_date', '')))

    # Deduplicate:
    # 1. Exact identical move (same from_club and same to_club)
    # 2. Duplicate entries on the exact same date (e.g. Fenerbahçe vs Fenerbahce on 2023-07-01)
    # 3. Duplicate consecutive transitions leaving the same from_club without returning
    filtered = []
    for rec in parsed:
        if not filtered:
            filtered.append(rec)
            continue
        prev = filtered[-1]

        # Exact same transition or duplicate entry on the exact same date
        if (prev['from_club_name'].lower() == rec['from_club_name'].lower() and prev['to_club_name'].lower() == rec['to_club_name'].lower()) or \
           (prev['transfer_date'] and prev['transfer_date'] == rec['transfer_date'] and (prev['from_club_name'].lower() == rec['from_club_name'].lower() or prev['to_club_name'].lower() == rec['to_club_name'].lower())):
            if rec['transfer_fee'] > prev['transfer_fee']:
                prev['transfer_fee'] = rec['transfer_fee']
            if rec['transfer_type'] and not prev['transfer_type']:
                prev['transfer_type'] = rec['transfer_type']
            continue

        # Consecutive duplicate origin club without intermediate return
        if prev['from_club_name'].lower() == rec['from_club_name'].lower():
            if rec['transfer_fee'] > prev['transfer_fee']:
                prev['to_club_name'] = rec['to_club_name']
                prev['transfer_fee'] = rec['transfer_fee']
                prev['transfer_date'] = rec['transfer_date']
                if rec['transfer_type']:
                    prev['transfer_type'] = rec['transfer_type']
            continue

        filtered.append(rec)

    return filtered



