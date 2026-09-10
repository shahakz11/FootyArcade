#!/usr/bin/env python3
import os
import sys
import asyncio
import datetime
import argparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from record_real_ui_short import record_short_video, ensure_server_running
from scripts.youtube_uploader import upload_short, build_default_metadata, get_channel_info

DAILY_GAMES = [
    {"id": "top_transfers",        "name": "Top Transfers"},
    {"id": "transfer_destination", "name": "Transfer Destination"},
    {"id": "club_connect",         "name": "Club Connect"},
    {"id": "player_chain",         "name": "Player Chain"},
    {"id": "top_scorers",          "name": "Top Scorers"}
]

async def process_all_games(interval_hours=1, fast_mode=False, port=8080, dry_run=False):
    print("\n" + "=" * 62)
    print("   ⚽  PLAYMAKER — DAILY SHORTS BATCH RENDER & UPLOADER")
    print("=" * 62)

    # 1. Verify channel identity
    channel_title, channel_id = get_channel_info()
    if not channel_id:
        print("\n\033[1;31m❌ Error: No YouTube channel has been created for this Google account yet!\033[0m")
        print("   (YouTube API returned: 'youtubeSignupRequired')\n")
        print("👉 \033[1;33mQUICK 3-STEP FIX:\033[0m")
        print("   1. Open \033[1;34mhttps://www.youtube.com/create_channel\033[0m in your browser while signed into Playmaker.")
        print("   2. Click 'Create Channel'.")
        print("   3. Delete the old token by running: \033[1;36mrm private/youtube_token.pickle\033[0m")
        print("   4. Re-run UploadTodayShorts.command and authorize your newly created channel!\n")
        return

    print(f"\n📺 Connected YouTube Channel: \033[1;32m{channel_title}\033[0m (ID: {channel_id})")
    print("💡 The first video will go live immediately; subsequent videos will be scheduled with 1-hour gaps.\n")

    server_proc = ensure_server_running(port)
    results = []

    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        for i, game in enumerate(DAILY_GAMES):
            game_id = game["id"]
            game_name = game["name"]

            # Calculate schedule
            if i == 0:
                publish_at = None
                timing_label = "NOW (Immediate Public)"
            else:
                scheduled_time = now_utc + datetime.timedelta(hours=i * interval_hours)
                publish_at = scheduled_time.strftime("%Y-%m-%dT%H:%M:%SZ")
                timing_label = f"+{i * interval_hours} hr ({scheduled_time.strftime('%H:%M UTC')})"

            print("\n" + "-" * 62)
            print(f"🎬 [{i+1}/{len(DAILY_GAMES)}] Processing: {game_name} ({game_id})")
            print(f"⏰ Schedule Target: {timing_label}")
            print("-" * 62)

            # Render video
            video_path = await record_short_video(game_id=game_id, day_offset=0, fast_mode=fast_mode, port=port)

            if not video_path or not os.path.exists(video_path):
                print(f"❌ Failed to render video for {game_name}. Skipping...")
                results.append({"game": game_name, "status": "Render Failed", "url": "—", "timing": timing_label})
                continue

            if dry_run:
                print(f"🔎 Dry run: Video created at {video_path}, skipping upload.")
                results.append({"game": game_name, "status": "Rendered (Dry Run)", "url": video_path, "timing": timing_label})
                continue

            # Upload to YouTube
            title, desc, tags = build_default_metadata(game_id=game_id)
            try:
                vid, shorts_url = upload_short(
                    video_path=video_path,
                    title=title,
                    description=desc,
                    tags=tags,
                    privacy_status="public",
                    publish_at=publish_at
                )
                status_text = "Live Now" if not publish_at else f"Scheduled {timing_label}"
                results.append({"game": game_name, "status": status_text, "url": shorts_url, "timing": timing_label})
            except Exception as e:
                print(f"❌ Upload error for {game_name}: {e}")
                results.append({"game": game_name, "status": f"Upload Error: {e}", "url": "—", "timing": timing_label})

    finally:
        if server_proc:
            server_proc.terminate()
            print("\n📡 Background HTTP server stopped.")

    # Print Summary Table
    print("\n" + "=" * 62)
    print("                🎉 BATCH SUMMARY REPORT")
    print("=" * 62)
    for r in results:
        print(f"• {r['game']:<22} | {r['status']:<20} | {r['url']}")
    print("=" * 62 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Render and upload all daily Playmaker games to YouTube Shorts with scheduled intervals.")
    parser.add_argument("--interval", type=int, default=1, help="Interval in hours between scheduled uploads (default: 1)")
    parser.add_argument("--port", type=int, default=8080, help="Local server port (default: 8080)")
    parser.add_argument("--fast", action="store_true", help="Fast mode for testing")
    parser.add_argument("--dry-run", action="store_true", help="Render videos only without uploading")

    args = parser.parse_args()
    asyncio.run(process_all_games(interval_hours=args.interval, fast_mode=args.fast, port=args.port, dry_run=args.dry_run))

if __name__ == "__main__":
    main()
