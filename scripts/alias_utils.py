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

CONFIG_RELATIVE_PATH = os.path.join("private", "aliases_config.json")


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


def get_config_path(root_dir=None):
    """Return the absolute path to private/aliases_config.json."""
    if not root_dir:
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        root_dir = os.path.abspath(os.path.join(cur_dir, ".."))
    return os.path.join(root_dir, CONFIG_RELATIVE_PATH)


def load_aliases_config(root_dir=None):
    """
    Load aliases_config.json from private/ folder.
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
            if "hidden" not in data["players"] or not isinstance(data["players"]["hidden"], list):
                data["players"]["hidden"] = []
            return data
    except Exception as e:
        print(f"[alias_utils] Warning: Error reading {path}: {e}")
        return default_cfg


def save_aliases_config(config, root_dir=None):
    """
    Atomically save aliases_config.json to private/.
    """
    path = get_config_path(root_dir)
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
    """
    hidden = set()
    if not config or "players" not in config:
        return hidden
    for p in config.get("players", {}).get("hidden", []):
        if p and isinstance(p, str) and p.strip():
            hidden.add(p.strip())
    return hidden


def filter_and_canonicalize_clubs(club_list, config):
    """
    Takes a raw list of club names (strings):
      1. Translates names to canonical display names using alias map.
      2. Deduplicates while preserving order.
      3. Removes any club in the hidden set.
    Returns: cleaned list of strings.
    """
    alias_map = get_club_alias_map(config)
    hidden_clubs = get_hidden_clubs(config)
    hidden_lower = {h.lower() for h in hidden_clubs}

    result = []
    seen = set()

    for item in club_list:
        if not isinstance(item, str):
            continue
        c = item.strip()
        if not c:
            continue

        canonical = alias_map.get(c, c)
        if canonical.lower() in hidden_lower:
            continue

        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)

    return result


def filter_hidden_players(player_list, config):
    """
    Takes a list of player dicts (e.g. [{'Name': ..., 'MarketValue': ...}, ...]) or player names (strings),
    and filters out any players whose Name is in get_hidden_players(config).
    Returns: filtered list.
    """
    hidden = get_hidden_players(config)
    if not hidden:
        return player_list

    hidden_lower = {h.lower() for h in hidden}
    result = []

    for item in player_list:
        if isinstance(item, dict):
            name = (item.get("Name") or item.get("name") or item.get("player_name") or "").strip()
            if name.lower() not in hidden_lower:
                result.append(item)
        elif isinstance(item, str):
            if item.strip().lower() not in hidden_lower:
                result.append(item)
        else:
            result.append(item)

    return result
