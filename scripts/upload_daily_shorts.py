#!/usr/bin/env python3
import os
import sys
import asyncio
import datetime
import argparse
import subprocess

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from record_real_ui_short import record_short_video, ensure_server_running
from scripts.youtube_uploader import upload_short, build_default_metadata, get_channel_info
from scripts.instagram_uploader import (
    check_connection as check_ig_connection,
    upload_reel_now,
    queue_reel,
    run_daemon as run_ig_daemon,
    build_instagram_caption,
    start_background_daemon,
    is_already_posted as is_ig_already_posted,
    mark_as_posted as mark_ig_as_posted
)

DAILY_GAMES = [
    {"id": "top_transfers",        "name": "Top Transfers"},
    {"id": "transfer_destination", "name": "Transfer Destination"},
    {"id": "club_connect",         "name": "Club Connect"},
    {"id": "player_chain",         "name": "Player Chain"},
    {"id": "top_scorers",          "name": "Top Scorers"}
]

async def process_all_games(interval_hours=1, fast_mode=False, port=8080, dry_run=False, selected_game="", no_youtube=False, no_instagram=False, instant_reels=False, wait_queue=False):
    print("\n" + "=" * 68)
    print("   ⚽  PLAYMAKER — DAILY SHORTS & REELS BATCH RENDER & UPLOADER")
    print("=" * 68)

    today_str = datetime.date.today().strftime("%Y-%m-%d")

    # 1. Verify YouTube channel identity
    channel_title, channel_id = None, None
    if not no_youtube:
        try:
            channel_title, channel_id = get_channel_info()
        except Exception as e:
            print(f"⚠️ YouTube check warning: {e}")

        if not channel_id:
            print("\n\033[1;31m❌ Error: No YouTube channel has been created for this Google account yet!\033[0m")
            print("   (YouTube API returned: 'youtubeSignupRequired')\n")
            print("👉 \033[1;33mQUICK 3-STEP FIX:\033[0m")
            print("   1. Open \033[1;34mhttps://www.youtube.com/create_channel\033[0m in your browser while signed into Playmaker.")
            print("   2. Click 'Create Channel'.")
            print("   3. Delete the old token by running: \033[1;36mrm private/youtube_token.pickle\033[0m")
            print("   4. Re-run UploadTodayShorts.command and authorize your newly created channel!\n")
            return
        print(f"📺 YouTube Channel: \033[1;32m{channel_title}\033[0m (ID: {channel_id})")

    # 2. Verify Instagram identity
    ig_username, ig_id = None, None
    if not no_instagram:
        try:
            ig_username, ig_id = check_ig_connection(silent=True)
            print(f"📸 Instagram Account: \033[1;32m@{ig_username}\033[0m (ID: {ig_id})")
        except Exception as e:
            print(f"⚠️ Instagram warning: {e}")
            print("   Reels upload will be skipped if authentication is invalid.")

    print("\n💡 Video #1 will publish immediately; Videos #2..#5 will publish with 1-hour delays.")
    print("   (YouTube scheduled via API, Instagram queued via background scheduler).\n")

    # 3. Compile today's latest daily puzzles
    print("🔄 Ensuring today's HTML game files are fully compiled and up to date...")
    subprocess.run([sys.executable, os.path.join(BASE_DIR, "fetch_daily.py")], check=True)

    server_proc = ensure_server_running(port)
    results = []
    games_to_run = [g for g in DAILY_GAMES if not selected_game or g["id"] == selected_game]
    has_queued_reels = False

    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc)

        for i, game in enumerate(games_to_run):
            game_id = game["id"]
            game_name = game["name"]

            # Calculate schedule
            if i == 0:
                publish_at = None
                timing_label = "NOW (Immediate Public)"
                sched_utc_dt = now_utc
            else:
                sched_utc_dt = now_utc + datetime.timedelta(hours=i * interval_hours)
                publish_at = sched_utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                timing_label = f"+{i * interval_hours} hr ({sched_utc_dt.strftime('%H:%M UTC')})"

            print("\n" + "-" * 68)
            print(f"🎬 [{i+1}/{len(games_to_run)}] Processing: {game_name} ({game_id})")
            print(f"⏰ Schedule Target: {timing_label}")
            print("-" * 68)

            # Render video
            video_path, target_name = await record_short_video(game_id=game_id, day_offset=0, fast_mode=fast_mode, port=port)

            if not video_path or not os.path.exists(video_path):
                print(f"❌ Failed to render video for {game_name}. Skipping...")
                results.append({
                    "game": game_name,
                    "yt_status": "Render Failed", "yt_url": "—",
                    "ig_status": "Render Failed", "ig_url": "—"
                })
                continue

            if dry_run:
                print(f"🔎 Dry run: Video created at {video_path}, skipping actual uploads.")
                results.append({
                    "game": game_name,
                    "yt_status": "Rendered (Dry Run)", "yt_url": video_path,
                    "ig_status": "Rendered (Dry Run)", "ig_url": video_path
                })
                continue

            # ── A. Upload to YouTube Shorts ───────────────────────────────────
            yt_status, yt_url = "Skipped", "—"
            if not no_youtube:
                title, desc, tags = build_default_metadata(game_id=game_id, target_name=target_name)
                try:
                    vid, shorts_url = upload_short(
                        video_path=video_path,
                        title=title,
                        description=desc,
                        tags=tags,
                        privacy_status="public",
                        publish_at=publish_at
                    )
                    yt_status = "Live Now" if not publish_at else f"Scheduled"
                    yt_url = shorts_url
                except Exception as e:
                    print(f"❌ YouTube upload error for {game_name}: {e}")
                    yt_status = "Upload Error"
                    yt_url = str(e)

            # ── B. Upload to Instagram Reels ──────────────────────────────────
            ig_status, ig_url = "Skipped", "—"
            if not no_instagram and ig_id:
                ig_caption = build_instagram_caption(game_id=game_id, target_name=target_name)
                
                # Check deduplication ledger
                if is_ig_already_posted(game_id, today_str):
                    print(f"ℹ️ [Instagram] {game_name} was already posted today according to ledger.")
                    ig_status = "Already Posted"
                    ig_url = "In Ledger"
                elif i == 0 or instant_reels:
                    # Upload immediately
                    try:
                        print(f"🚀 Uploading Reel immediately to Instagram...")
                        ig_media_id, permalink = upload_reel_now(video_path, ig_caption)
                        mark_ig_as_posted(game_id, today_str, permalink, ig_media_id)
                        ig_status = "Live Now"
                        ig_url = permalink
                    except Exception as e:
                        print(f"❌ Instagram upload error for {game_name}: {e}")
                        ig_status = "Upload Error"
                        ig_url = str(e)
                else:
                    # Queue for delayed publishing
                    try:
                        queue_reel(
                            video_path=video_path,
                            caption=ig_caption,
                            scheduled_utc_iso=sched_utc_dt.isoformat(),
                            game_id=game_id,
                            date_str=today_str
                        )
                        ig_status = f"Queued ({timing_label})"
                        ig_url = "Pending Schedule"
                        has_queued_reels = True
                    except Exception as e:
                        print(f"❌ Instagram queue error for {game_name}: {e}")
                        ig_status = "Queue Error"
                        ig_url = str(e)

            results.append({
                "game": game_name,
                "yt_status": yt_status, "yt_url": yt_url,
                "ig_status": ig_status, "ig_url": ig_url
            })

    finally:
        if server_proc:
            server_proc.terminate()
            print("\n📡 Background HTTP server stopped.")

    # 4. Spawn or run background scheduler if any reels are queued
    if has_queued_reels:
        if wait_queue:
            print("\n⏳ [Cloud/CI Mode] Waiting in foreground for all queued reels to publish...")
            run_ig_daemon()
        else:
            start_background_daemon()
            print("\n🤖 Detached background Instagram daemon started.")
            print("   Queued reels will publish automatically at their scheduled hours.")

    # 5. Print Consolidated Dual-Platform Summary Table
    print("\n" + "=" * 80)
    print("                      🎉 BATCH SUMMARY REPORT")
    print("=" * 80)
    print(f"{'Game':<20} | {'YouTube Shorts':<28} | {'Instagram Reels':<28}")
    print("-" * 80)
    for r in results:
        yt_disp = f"{r['yt_status']}: {r['yt_url']}" if r['yt_url'] != "—" else r['yt_status']
        ig_disp = f"{r['ig_status']}: {r['ig_url']}" if r['ig_url'] != "—" else r['ig_status']
        print(f"{r['game']:<20} | {yt_disp[:28]:<28} | {ig_disp[:28]:<28}")
    print("=" * 80 + "\n")

def main():
    parser = argparse.ArgumentParser(description="Render and upload daily Playmaker games to YouTube Shorts & Instagram Reels.")
    parser.add_argument("--interval", type=int, default=1, help="Interval in hours between scheduled uploads (default: 1)")
    parser.add_argument("--port", type=int, default=8080, help="Local server port (default: 8080)")
    parser.add_argument("--fast", action="store_true", help="Fast mode for testing")
    parser.add_argument("--dry-run", action="store_true", help="Render videos only without uploading")
    parser.add_argument("--game", type=str, default="", help="Run a specific game ID only")
    parser.add_argument("--no-youtube", action="store_true", help="Skip YouTube upload")
    parser.add_argument("--no-instagram", action="store_true", help="Skip Instagram upload")
    parser.add_argument("--instant-reels", action="store_true", help="Publish all Instagram Reels immediately without queue delay")
    parser.add_argument("--wait-queue", action="store_true", help="Wait in foreground for all queued reels to finish (ideal for GitHub Actions)")

    args = parser.parse_args()
    asyncio.run(process_all_games(
        interval_hours=args.interval,
        fast_mode=args.fast,
        port=args.port,
        dry_run=args.dry_run,
        selected_game=args.game,
        no_youtube=args.no_youtube,
        no_instagram=args.no_instagram,
        instant_reels=args.instant_reels,
        wait_queue=args.wait_queue
    ))

if __name__ == "__main__":
    main()
