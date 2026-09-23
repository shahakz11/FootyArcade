#!/usr/bin/env python3
"""
Playmaker B-Roll Asset Curator.
Automatically searches, fetches, and indexes clean 9:16 vertical football & lifestyle
B-roll clips into assets/broll/ for automatic video generation.
"""

import os
import sys
import json
import argparse
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BROLL_DIR = os.path.join(BASE_DIR, "assets", "broll")

CURATED_SEARCH_QUERIES = [
    "football freestyle juggling vertical 4k no watermark",
    "street football skills vertical no text",
    "football pitch training drills vertical raw",
    "casual football juggling mini ball street",
    "football free kick practice vertical clean"
]

def search_and_download_broll(query, limit=3):
    """Downloads clean vertical video clips using yt-dlp."""
    os.makedirs(BROLL_DIR, exist_ok=True)
    print(f"🔍 Searching clean vertical B-roll for: '{query}' (limit {limit})...")

    cmd = [
        "yt-dlp",
        f"ytsearch{limit}:{query}",
        "-o", os.path.join(BROLL_DIR, "%(id)s.%(ext)s"),
        "-f", "bestvideo[height<=1920][ext=mp4]/best[ext=mp4]/best",
        "--max-downloads", str(limit),
        "--no-playlist",
        "--match-filter", "duration < 60",
        "--quiet"
    ]
    try:
        subprocess.run(cmd, check=True)
        print(f"✅ Successfully downloaded clips to: {BROLL_DIR}")
    except Exception as e:
        print(f"⚠️ Download warning: {e}")

def list_available_broll():
    """Lists all available B-roll clips in assets/broll/."""
    os.makedirs(BROLL_DIR, exist_ok=True)
    files = [f for f in os.listdir(BROLL_DIR) if f.endswith((".mp4", ".mov", ".webm"))]
    print(f"\n📂 Available B-roll Library ({len(files)} clips in assets/broll/):")
    for idx, f in enumerate(files, 1):
        fpath = os.path.join(BROLL_DIR, f)
        size_mb = os.path.getsize(fpath) / (1024 * 1024)
        print(f"  [{idx}] {f} ({size_mb:.1f} MB)")
    print()
    return files

def main():
    parser = argparse.ArgumentParser(description="Fetch and Manage Clean B-Roll Clips")
    parser.add_argument("--search", type=str, default=None, help="Custom search query")
    parser.add_argument("--auto-curate", action="store_true", help="Download from curated query list")
    parser.add_argument("--list", action="store_true", help="List all available B-roll clips")
    parser.add_argument("--limit", type=int, default=2, help="Number of clips to download")
    args = parser.parse_args()

    if args.search:
        search_and_download_broll(args.search, limit=args.limit)
        list_available_broll()
    elif args.auto_curate:
        for q in CURATED_SEARCH_QUERIES[:2]:
            search_and_download_broll(q, limit=args.limit)
        list_available_broll()
    else:
        list_available_broll()

if __name__ == "__main__":
    main()
