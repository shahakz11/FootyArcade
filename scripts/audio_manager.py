#!/usr/bin/env python3
"""
Playmaker Background Audio & Music Rotation Manager.
Manages royalty-free background music tracks for Shorts & Reels video generation.
Ensures tracks rotate smoothly without repetitive overuse.
"""

import os
import sys
import glob
import json
import random
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE_DIR, "assets", "audio")
PRIVATE_DIR = os.path.join(BASE_DIR, "private")
HISTORY_FILE = os.path.join(PRIVATE_DIR, "audio_history.json")

def load_audio_history():
    """Loads audio track usage history."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_audio_history(history):
    """Saves audio usage history to private/audio_history.json."""
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"⚠️ Could not save audio history: {e}")

def get_all_available_audio():
    """Discovers all valid audio tracks in assets/audio/."""
    os.makedirs(AUDIO_DIR, exist_ok=True)
    extensions = ["*.wav", "*.mp3", "*.m4a", "*.aac", "*.ogg"]
    tracks = []
    for ext in extensions:
        tracks.extend(glob.glob(os.path.join(AUDIO_DIR, ext)))
    # Filter out empty or corrupted files (<10KB)
    valid_tracks = [t for t in tracks if os.path.getsize(t) > 10_000]
    return valid_tracks

def select_audio_track(exclude_paths=None, game_id=""):
    """
    Selects a background audio track ensuring rotation.
    - Sorts remaining tracks by least recently used in audio_history.
    - Updates history upon selection.
    """
    if exclude_paths is None:
        exclude_paths = []
        
    exclude_paths = [os.path.abspath(p) for p in exclude_paths]
    all_tracks = get_all_available_audio()
    
    if not all_tracks:
        return None

    history = load_audio_history()
    
    # Filter out excluded tracks
    available = [t for t in all_tracks if os.path.abspath(t) not in exclude_paths]
    if not available:
        available = all_tracks

    # Score tracks based on usage count and last used date
    scored = []
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    for track_path in available:
        filename = os.path.basename(track_path)
        track_info = history.get(filename, {})
        use_count = track_info.get("count", 0)
        last_used = track_info.get("last_used", "2000-01-01T00:00:00Z")
        scored.append((use_count, last_used, track_path))
        
    # Sort by lowest use count, then oldest last_used timestamp
    scored.sort(key=lambda x: (x[0], x[1]))
    
    min_count = scored[0][0]
    least_used_candidates = [s[2] for s in scored if s[0] == min_count]
    selected = random.choice(least_used_candidates)
    
    # Update history
    sel_filename = os.path.basename(selected)
    curr_info = history.get(sel_filename, {"count": 0, "last_used": ""})
    history[sel_filename] = {
        "count": curr_info.get("count", 0) + 1,
        "last_used": now_iso,
        "last_game": game_id
    }
    save_audio_history(history)
    
    display_title = os.path.splitext(sel_filename)[0].replace("_", " ").title()
    print(f"🎵 [Audio Selector] Selected track: {sel_filename} ({display_title})")
    return selected

def get_track_display_name(audio_path):
    """Formats an audio file path into a clean display title for Instagram/TikTok."""
    if not audio_path:
        return "Trending Football Beat"
    base = os.path.splitext(os.path.basename(audio_path))[0]
    return base.replace("_", " ").replace("-", " ").title()

if __name__ == "__main__":
    tracks = get_all_available_audio()
    print(f"Available audio tracks ({len(tracks)}):")
    for t in tracks:
        print(f"  • {os.path.basename(t)} ({os.path.getsize(t) / 1024:.1f} KB)")
    sel = select_audio_track()
    print(f"Selected: {sel}")
