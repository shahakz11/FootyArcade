#!/usr/bin/env python3
"""
Playmaker Club Badge Manager & Asset Resolver.
Resolves club names to official crest images with alias normalization,
local disk caching, and high-fidelity procedural fallback generation.
"""

import os
import re
import json
import urllib.request
import urllib.parse
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BADGES_DIR = os.path.join(BASE_DIR, "assets", "badges")
RAW_DATA_PATH = os.path.join(BASE_DIR, "data", "raw_api", "football_data_raw.json")
ALIASES_PATH = os.path.join(BASE_DIR, "data", "aliases_config.json")

# Pre-populated top European club crest URLs from official open repositories (football-data.org CDN)
ADDITIONAL_CRESTS = {
    "Real Madrid": "https://crests.football-data.org/86.png",
    "Barcelona": "https://crests.football-data.org/81.png",
    "FC Barcelona": "https://crests.football-data.org/81.png",
    "Atletico Madrid": "https://crests.football-data.org/78.png",
    "Atlético Madrid": "https://crests.football-data.org/78.png",
    "Sevilla": "https://crests.football-data.org/559.png",
    "Valencia": "https://crests.football-data.org/95.png",
    "Athletic Bilbao": "https://crests.football-data.org/77.png",
    "Villarreal": "https://crests.football-data.org/94.png",
    "Real Sociedad": "https://crests.football-data.org/92.png",
    "Manchester City": "https://crests.football-data.org/65.png",
    "Manchester United": "https://crests.football-data.org/66.png",
    "Liverpool": "https://crests.football-data.org/64.png",
    "Arsenal": "https://crests.football-data.org/57.png",
    "Chelsea": "https://crests.football-data.org/61.png",
    "Tottenham": "https://crests.football-data.org/73.png",
    "Newcastle": "https://crests.football-data.org/67.png",
    "Aston Villa": "https://crests.football-data.org/58.png",
    "Juventus": "https://crests.football-data.org/109.png",
    "Inter": "https://crests.football-data.org/108.png",
    "Inter Milan": "https://crests.football-data.org/108.png",
    "AC Milan": "https://crests.football-data.org/98.png",
    "Milan": "https://crests.football-data.org/98.png",
    "Napoli": "https://crests.football-data.org/113.png",
    "Roma": "https://crests.football-data.org/100.png",
    "AS Roma": "https://crests.football-data.org/100.png",
    "Lazio": "https://crests.football-data.org/110.png",
    "Atalanta": "https://crests.football-data.org/102.png",
    "Parma": "https://crests.football-data.org/112.png",
    "Sampdoria": "https://crests.football-data.org/584.png",
    "Fiorentina": "https://crests.football-data.org/99.png",
    "Bayern Munich": "https://crests.football-data.org/5.png",
    "Borussia Dortmund": "https://crests.football-data.org/4.png",
    "Bayer Leverkusen": "https://crests.football-data.org/3.png",
    "RB Leipzig": "https://crests.football-data.org/721.png",
    "Paris Saint-Germain": "https://crests.football-data.org/524.png",
    "PSG": "https://crests.football-data.org/524.png",
    "Marseille": "https://crests.football-data.org/516.png",
    "Monaco": "https://crests.football-data.org/548.png",
    "Lyon": "https://crests.football-data.org/523.png",
    "Lille": "https://crests.football-data.org/521.png",
    "Benfica": "https://crests.football-data.org/1903.png",
    "Sporting CP": "https://crests.football-data.org/498.png",
    "Porto": "https://crests.football-data.org/503.png",
    "Ajax": "https://crests.football-data.org/678.png",
    "PSV": "https://crests.football-data.org/674.png",
    "Feyenoord": "https://crests.football-data.org/675.png",
    "Celtic": "https://crests.football-data.org/732.png",
    "Rangers": "https://crests.football-data.org/734.png",
}

_URL_MAP = None
_ALIAS_MAP = None

def _sanitize_filename(name):
    s = str(name).strip().lower()
    return re.sub(r'[^a-z0-9]+', '_', s).strip('_')

def load_alias_mapping():
    global _ALIAS_MAP
    if _ALIAS_MAP is not None:
        return _ALIAS_MAP
    _ALIAS_MAP = {}
    if os.path.exists(ALIASES_PATH):
        try:
            with open(ALIASES_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            groups = data.get("clubs", {}).get("groups", [])
            for g in groups:
                disp = g.get("display_name", "")
                if disp:
                    _ALIAS_MAP[disp.lower()] = disp
                    for alias in g.get("aliases", []):
                        _ALIAS_MAP[alias.lower()] = disp
            
            # Common sports abbreviations
            shorthands = {
                "madrid": "Real Madrid",
                "barca": "Barcelona",
                "barça": "Barcelona",
                "bayern": "Bayern Munich",
                "juve": "Juventus",
                "inter": "Inter Milan",
                "milan": "AC Milan",
                "atleti": "Atletico Madrid",
                "atletico": "Atletico Madrid",
                "man city": "Manchester City",
                "mancity": "Manchester City",
                "man utd": "Manchester United",
                "manutd": "Manchester United",
                "united": "Manchester United",
                "psg": "Paris Saint-Germain",
                "dortmund": "Borussia Dortmund",
                "bvb": "Borussia Dortmund",
                "spurs": "Tottenham",
            }
            for k, v in shorthands.items():
                if k not in _ALIAS_MAP:
                    _ALIAS_MAP[k] = v
        except Exception as e:
            print(f"⚠️ Error loading aliases: {e}")
    return _ALIAS_MAP

def load_crest_url_database():
    global _URL_MAP
    if _URL_MAP is not None:
        return _URL_MAP
    _URL_MAP = {}
    # 1. Base dictionary
    for k, v in ADDITIONAL_CRESTS.items():
        _URL_MAP[k.lower()] = v

    # 2. Extract from football_data_raw.json
    if os.path.exists(RAW_DATA_PATH):
        try:
            with open(RAW_DATA_PATH, "r", encoding="utf-8") as f:
                raw = json.load(f)
            if isinstance(raw, dict):
                for comp, cdata in raw.items():
                    for match in cdata.get("matches", []):
                        for side in ("homeTeam", "awayTeam"):
                            team = match.get(side, {})
                            name = team.get("name")
                            short_name = team.get("shortName")
                            crest = team.get("crest")
                            if crest and crest.endswith(".png"):
                                if name:
                                    _URL_MAP[name.lower()] = crest
                                if short_name:
                                    _URL_MAP[short_name.lower()] = crest
        except Exception as e:
            print(f"⚠️ Error loading raw crest URLs: {e}")
    return _URL_MAP

def normalize_club_name(club_name):
    name = str(club_name or "").strip()
    if not name:
        return "Unknown FC"
    aliases = load_alias_mapping()
    return aliases.get(name.lower(), name)

def generate_procedural_crest(club_name, size=(160, 160)):
    """Generates an aesthetic modern shield crest when an official crest is missing."""
    w, h = size
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Hash club name to get consistent complementary colors
    hval = abs(hash(club_name))
    colors = [
        ((30, 58, 138), (59, 130, 246)),   # Royal Blue
        ((153, 27, 27), (239, 68, 68)),    # Crimson Red
        ((6, 78, 59), (16, 185, 129)),     # Pitch Emerald
        ((88, 28, 135), (168, 85, 247)),   # Electric Purple
        ((120, 53, 15), (245, 158, 11)),   # Gold/Amber
        ((15, 23, 42), (0, 240, 255)),     # Cyber Cyan
    ]
    bg_dark, bg_light = colors[hval % len(colors)]

    # Draw rounded shield
    margin = int(w * 0.08)
    x0, y0 = margin, margin
    x1, y1 = w - margin, h - margin
    radius = int(w * 0.22)
    draw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=bg_dark, outline=bg_light, width=int(w * 0.035))

    # Center initials
    words = [w for w in re.split(r'[\s\-_]+', club_name) if w and w.lower() not in ("fc", "cf", "afc", "sc")]
    if not words:
        words = [club_name[:2]]
    initials = "".join(w[0].upper() for w in words[:3])

    # Text styling
    try:
        font_paths = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/System/Library/Fonts/SFNS.ttf"
        ]
        font = None
        for p in font_paths:
            if os.path.exists(p):
                font = ImageFont.truetype(p, int(w * 0.32))
                break
        if not font:
            font = ImageFont.load_default()
    except Exception:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), initials, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = (w - tw) // 2
    ty = (h - th) // 2 - int(h * 0.04)

    draw.text((tx, ty), initials, fill=(255, 255, 255, 255), font=font)
    return img

def get_club_badge(club_name, size=(160, 160)):
    """
    Returns a PIL Image (RGBA) for the requested club name.
    1. Checks local cache in assets/badges/{slug}.png
    2. Downloads if online URL exists
    3. Falls back to generating a procedural shield crest
    """
    os.makedirs(BADGES_DIR, exist_ok=True)
    canonical = normalize_club_name(club_name)
    slug = _sanitize_filename(canonical)
    cache_path = os.path.join(BADGES_DIR, f"{slug}.png")

    # 1. Check local cache
    if os.path.exists(cache_path):
        try:
            im = Image.open(cache_path).convert("RGBA")
            if im.size != size:
                im = im.resize(size, Image.LANCZOS)
            return im
        except Exception:
            pass

    # 2. Try online download
    url_map = load_crest_url_database()
    crest_url = url_map.get(canonical.lower()) or url_map.get(club_name.lower())
    
    # If not found directly, try partial matching
    if not crest_url:
        for k, u in url_map.items():
            if k in canonical.lower() or canonical.lower() in k:
                crest_url = u
                break

    if crest_url and crest_url.startswith("http"):
        try:
            headers = {"User-Agent": "Mozilla/5.0"}
            req = urllib.request.Request(crest_url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = resp.read()
                temp_save = cache_path + ".tmp"
                with open(temp_save, "wb") as f:
                    f.write(data)
                im = Image.open(temp_save).convert("RGBA")
                im.save(cache_path, "PNG")
                if os.path.exists(temp_save):
                    os.remove(temp_save)
                if im.size != size:
                    im = im.resize(size, Image.LANCZOS)
                return im
        except Exception as e:
            print(f"⚠️ Failed to download crest for '{canonical}' ({crest_url}): {e}")

    # 3. Procedural fallback
    crest = generate_procedural_crest(canonical, size=size)
    try:
        crest.save(cache_path, "PNG")
    except Exception:
        pass
    return crest

if __name__ == "__main__":
    for test_club in ["Chelsea", "Benfica", "Inter Milan", "Real Madrid", "Parma"]:
        badge = get_club_badge(test_club, size=(160, 160))
        print(f"✅ Generated/Resolved badge for {test_club}: size {badge.size}, format PNG")
