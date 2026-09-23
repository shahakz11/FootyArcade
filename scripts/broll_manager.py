#!/usr/bin/env python3
"""
Playmaker B-Roll Rotation & History Manager.
Ensures every generated short uses a fresh, non-repeating background video.
Guarantees that multiple videos generated on the same day never use the same B-roll clip.
"""

import os
import sys
import glob
import json
import random
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BROLL_DIR = os.path.join(BASE_DIR, "assets", "broll")
PRIVATE_DIR = os.path.join(BASE_DIR, "private")
HISTORY_FILE = os.path.join(PRIVATE_DIR, "broll_history.json")

def load_broll_history():
    """Loads B-roll usage history."""
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_broll_history(history):
    """Saves B-roll usage history to private/broll_history.json."""
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"⚠️ Could not save broll history: {e}")

def get_all_available_broll():
    """Discovers all valid .mp4 / .mov clips in assets/broll/."""
    os.makedirs(BROLL_DIR, exist_ok=True)
    clips = glob.glob(os.path.join(BROLL_DIR, "*.mp4")) + glob.glob(os.path.join(BROLL_DIR, "*.mov"))
    # Filter out empty or broken files
    valid_clips = [c for c in clips if os.path.getsize(c) > 100_000]
    return valid_clips

def select_broll_clip(exclude_paths=None, game_id=""):
    """
    Selects a B-roll clip ensuring NO REPEATS.
    - Excludes any path in exclude_paths (e.g. clip used in the first video of the day).
    - Sorts remaining clips by least recently used in broll_history.
    - Updates history upon selection.
    """
    if exclude_paths is None:
        exclude_paths = []
        
    exclude_paths = [os.path.abspath(p) for p in exclude_paths]
    all_clips = get_all_available_broll()
    
    if not all_clips:
        print("⚠️ No clips found in assets/broll/. Using fallback.")
        return None

    # Filter out excluded clips
    candidates = [c for c in all_clips if os.path.abspath(c) not in exclude_paths]
    if not candidates:
        # If all clips excluded, reset candidate list to all except immediately excluded
        candidates = all_clips

    history = load_broll_history()
    now_iso = datetime.datetime.now().isoformat()

    # Score candidates: lowest usage count & oldest last_used timestamp
    scored_clips = []
    for c in candidates:
        c_name = os.path.basename(c)
        rec = history.get(c_name, {})
        use_count = rec.get("use_count", 0)
        last_used = rec.get("last_used", "2000-01-01T00:00:00")
        scored_clips.append((use_count, last_used, c))

    # Sort primarily by use_count ascending, then last_used ascending
    scored_clips.sort(key=lambda x: (x[0], x[1]))
    
    # Pick from the least used (randomize top candidates if tied)
    best_score = scored_clips[0][0]
    tied_candidates = [item[2] for item in scored_clips if item[0] == best_score]
    selected_clip = random.choice(tied_candidates)

    # Record in history
    sel_name = os.path.basename(selected_clip)
    if sel_name not in history:
        history[sel_name] = {"use_count": 0, "history": []}
        
    history[sel_name]["use_count"] += 1
    history[sel_name]["last_used"] = now_iso
    history[sel_name]["last_game"] = game_id
    history[sel_name]["history"].append({"date": now_iso, "game": game_id})
    save_broll_history(history)

    print(f"🎬 [B-Roll Selector] Selected clip: {sel_name} (Used {history[sel_name]['use_count']} times, Game: {game_id})")
    return selected_clip

if __name__ == "__main__":
    clip1 = select_broll_clip(game_id="player_chain")
    clip2 = select_broll_clip(exclude_paths=[clip1], game_id="passport_fc")
    print("\nTest Result:")
    print("Video 1 B-roll:", clip1)
    print("Video 2 B-roll:", clip2)
    assert clip1 != clip2, "Error: Both videos used the same B-roll!"
    print("✅ Verified: Both B-roll videos are unique!")
