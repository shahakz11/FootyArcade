"""
scripts/player_image_manager.py

Automated Player Image Resolver and Local Cache Manager.
Fetches high-resolution player portraits from dataset CDN URLs,
with automated Wikipedia / Wikimedia PageImages API fallback for retro legends.
Saves cached images to assets/players/{player_slug_or_id}.jpg.
"""

import os
import re
import json
import urllib.request
import urllib.parse
from typing import Optional

try:
    from scripts.alias_utils import normalize_search_text
except ImportError:
    from alias_utils import normalize_search_text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS_PLAYERS_DIR = os.path.join(BASE_DIR, "assets", "players")

def sanitize_filename(name: str) -> str:
    """Sanitizes player name into safe ascii filesystem filename."""
    norm = normalize_search_text(str(name).strip())
    return re.sub(r'[-\s]+', '_', norm)


def fetch_wiki_player_image(player_name: str) -> Optional[str]:
    """Queries Wikipedia / Wikimedia API for high-resolution player image."""
    try:
        query = urllib.parse.quote(player_name)
        url = f"https://en.wikipedia.org/w/api.php?action=query&titles={query}&prop=pageimages&format=json&pithumbsize=1000"
        req = urllib.request.Request(url, headers={'User-Agent': 'PlaymakerArcade/1.0 (contact@playmaker.best)'})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            pages = data.get('query', {}).get('pages', {})
            for _, page in pages.items():
                if 'thumbnail' in page and 'source' in page['thumbnail']:
                    return page['thumbnail']['source']
    except Exception:
        pass
    return None

def download_and_cache_image(image_url: str, dest_path: str) -> bool:
    """Downloads image from remote URL to local destination."""
    try:
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        req = urllib.request.Request(image_url, headers={'User-Agent': 'Mozilla/5.0 (Playmaker/1.0)'})
        with urllib.request.urlopen(req, timeout=12) as resp:
            if resp.status == 200:
                with open(dest_path, 'wb') as f:
                    f.write(resp.read())
                return True
    except Exception:
        pass
    return False

def resolve_player_image_path(player_name: str, dataset_image_url: Optional[str] = None, force_download: bool = False) -> str:
    """
    Returns absolute local path to player portrait JPEG.
    Downloads and caches if not already present.
    """
    os.makedirs(ASSETS_PLAYERS_DIR, exist_ok=True)
    slug = sanitize_filename(player_name)
    local_path = os.path.join(ASSETS_PLAYERS_DIR, f"{slug}.jpg")

    if os.path.exists(local_path) and os.path.getsize(local_path) > 1000 and not force_download:
        return local_path

    # 1. Try dataset CDN URL if valid and not a default avatar
    if dataset_image_url and "default.jpg" not in dataset_image_url and dataset_image_url.startswith("http"):
        if download_and_cache_image(dataset_image_url, local_path):
            return local_path

    # 2. Fall back to Wikipedia / Wikimedia API
    wiki_url = fetch_wiki_player_image(player_name)
    if wiki_url:
        if download_and_cache_image(wiki_url, local_path):
            return local_path

    # 3. If dataset URL was default or both failed, try dataset URL anyway
    if dataset_image_url and dataset_image_url.startswith("http"):
        if download_and_cache_image(dataset_image_url, local_path):
            return local_path

    return local_path
