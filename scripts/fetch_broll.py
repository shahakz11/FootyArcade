#!/usr/bin/env python3
"""
Playmaker B-Roll Asset Curator.
Automatically searches, fetches, trims, and indexes clean 9:16 vertical football & lifestyle
B-roll clips into assets/broll/ for automatic video generation.
"""

import os
import sys
import glob
import argparse
import subprocess
import cv2

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BROLL_DIR = os.path.join(BASE_DIR, "assets", "broll")

CURATED_SEARCH_QUERIES = [
    "football freestyle juggling vertical 4k no watermark",
    "street football skills vertical no text",
    "football pitch training drills vertical raw",
    "football free kick practice vertical clean"
]

def trim_video_opencv(input_path, output_path, max_duration_sec=10):
    """
    Trims the first max_duration_sec from input_path to output_path using OpenCV.
    Ensures no system ffmpeg binary is strictly required.
    """
    cap = cv2.VideoCapture(input_path)
    if not cap.isOpened():
        print(f"❌ Failed to open video: {input_path}")
        return False

    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    target_frames = min(int(fps * max_duration_sec), total_frames)

    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    frames_written = 0
    while frames_written < target_frames:
        ret, frame = cap.read()
        if not ret:
            break
        out.write(frame)
        frames_written += 1

    cap.release()
    out.release()
    return frames_written > 0

def download_and_process_url(url, output_name=None, max_duration_sec=10):
    """Downloads a video by URL and trims to max_duration_sec."""
    os.makedirs(BROLL_DIR, exist_ok=True)
    temp_template = os.path.join(BROLL_DIR, "temp_download_%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        url,
        "-o", temp_template,
        "-f", "bestvideo[height<=1080][ext=mp4]/best[ext=mp4]/best",
        "--no-playlist",
        "--match-filter", "duration < 360",
        "--no-warnings"
    ]

    print(f"⬇️ Downloading video from URL: {url}...")
    res = subprocess.run(cmd)
    if res.returncode != 0:
        print(f"⚠️ Failed to download from URL: {url}")
        return False

    # Find downloaded temp file
    temp_files = glob.glob(os.path.join(BROLL_DIR, "temp_download_*"))
    if not temp_files:
        print("⚠️ No file downloaded (possibly failed match filter duration < 360s).")
        return False

    for temp_f in temp_files:
        base_id = os.path.splitext(os.path.basename(temp_f))[0].replace("temp_download_", "")
        final_name = f"clip_{output_name or base_id}.mp4"
        final_path = os.path.join(BROLL_DIR, final_name)

        print(f"✂️ Trimming {max_duration_sec}s slice with OpenCV -> {final_path}...")
        success = trim_video_opencv(temp_f, final_path, max_duration_sec=max_duration_sec)
        try:
            os.remove(temp_f)
        except OSError:
            pass

        if success:
            print(f"✅ Saved B-Roll clip: {final_name}")
            return True

    return False

def search_and_download_broll(query, limit=2, max_duration_sec=10):
    """Searches YouTube and downloads clean clips."""
    os.makedirs(BROLL_DIR, exist_ok=True)
    print(f"\n🔍 Searching for: '{query}' (limit {limit})...")

    # Target shorts or concise clips
    search_term = query if "shorts" in query.lower() else f"{query} shorts"
    temp_template = os.path.join(BROLL_DIR, "temp_search_%(id)s.%(ext)s")

    cmd = [
        "yt-dlp",
        f"ytsearch{limit}:{search_term}",
        "-o", temp_template,
        "-f", "bestvideo[height<=1080][ext=mp4]/best[ext=mp4]/best",
        "--max-downloads", str(limit),
        "--no-playlist",
        "--match-filter", "duration < 300",
        "--no-warnings"
    ]

    subprocess.run(cmd)

    # Process all temp files
    temp_files = glob.glob(os.path.join(BROLL_DIR, "temp_search_*"))
    if not temp_files:
        print(f"ℹ️ No matching clips found for '{query}'. Trying direct query without 'shorts'...")
        cmd[1] = f"ytsearch{limit}:{query}"
        subprocess.run(cmd)
        temp_files = glob.glob(os.path.join(BROLL_DIR, "temp_search_*"))

    for temp_f in temp_files:
        base_id = os.path.splitext(os.path.basename(temp_f))[0].replace("temp_search_", "")
        final_name = f"clip_{base_id}.mp4"
        final_path = os.path.join(BROLL_DIR, final_name)

        print(f"✂️ Processing clip -> {final_name}...")
        trim_video_opencv(temp_f, final_path, max_duration_sec=max_duration_sec)
        try:
            os.remove(temp_f)
        except OSError:
            pass

def list_available_broll():
    """Lists all available B-roll clips in assets/broll/."""
    os.makedirs(BROLL_DIR, exist_ok=True)
    files = [f for f in os.listdir(BROLL_DIR) if f.endswith((".mp4", ".mov", ".webm")) and not f.startswith("temp_")]
    print(f"\n📂 Available B-roll Library ({len(files)} clips in assets/broll/):")
    for idx, f in enumerate(files, 1):
        fpath = os.path.join(BROLL_DIR, f)
        size_mb = os.path.getsize(fpath) / (1024 * 1024)
        print(f"  [{idx}] {f} ({size_mb:.1f} MB)")
    print()
    return files

def main():
    parser = argparse.ArgumentParser(description="Fetch and Manage Clean B-Roll Clips")
    parser.add_argument("--url", type=str, default=None, help="Direct video URL (YouTube / Shorts)")
    parser.add_argument("--search", type=str, default=None, help="Custom search query")
    parser.add_argument("--name", type=str, default=None, help="Custom name for clip when using --url")
    parser.add_argument("--duration", type=int, default=10, help="Clip duration in seconds (default: 10)")
    parser.add_argument("--auto-curate", action="store_true", help="Download from curated query list")
    parser.add_argument("--list", action="store_true", help="List all available B-roll clips")
    parser.add_argument("--limit", type=int, default=1, help="Number of clips to download")
    args = parser.parse_args()

    if args.url:
        download_and_process_url(args.url, output_name=args.name, max_duration_sec=args.duration)
        list_available_broll()
    elif args.search:
        search_and_download_broll(args.search, limit=args.limit, max_duration_sec=args.duration)
        list_available_broll()
    elif args.auto_curate:
        for q in CURATED_SEARCH_QUERIES[:2]:
            search_and_download_broll(q, limit=args.limit, max_duration_sec=args.duration)
        list_available_broll()
    else:
        list_available_broll()

if __name__ == "__main__":
    main()
