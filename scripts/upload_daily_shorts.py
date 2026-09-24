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
from render_ugc_short import (
    extract_puzzle_data as extract_ugc_data,
    render_ugc_video,
    generate_social_copy as generate_ugc_caption
)
from scripts.broll_manager import select_broll_clip
from scripts.youtube_uploader import (
    upload_short,
    build_default_metadata,
    get_channel_info,
    is_youtube_already_uploaded,
    load_matchday_context_for_date,
    is_puzzle_context_matched
)
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
    {"id": "player_chain", "name": "Player Chain (Step 2)"},
    {"id": "passport_fc",  "name": "Passport FC (Step 2)"}
]

ALL_AVAILABLE_GAMES = [
    {"id": "player_chain",         "name": "Player Chain"},
    {"id": "passport_fc",          "name": "Passport FC"},
    {"id": "top_transfers",        "name": "Top Transfers"},
    {"id": "transfer_destination", "name": "Transfer Destination"},
    {"id": "club_connect",         "name": "Club Connect"},
    {"id": "top_scorers",          "name": "Top Scorers"}
]

DEFAULT_PEAK_SLOTS = [12, 20]  # 12:00 PM UTC and 8:00 PM UTC peak football engagement windows

def select_games_for_mode(mode="auto", selected_game="", all_games=False, curr_hour=None):
    """
    Selects which game(s) to process:
    - If all_games is True: returns ALL_AVAILABLE_GAMES (all 6)
    - If selected_game is provided: returns the matching game from ALL_AVAILABLE_GAMES
    - If mode in ('midday', 'morning'): returns [Top Transfers]
    - If mode in ('evening', 'night'): returns [Transfer Destination]
    - If mode == 'both': returns [Top Transfers, Transfer Destination]
    - If mode == 'auto' (default):
        - If current hour < 16 (before 4 PM): returns [Top Transfers] (Midday Peak Run)
        - If current hour >= 16 (4 PM onwards): returns [Transfer Destination] (Evening Peak Run)
    """
    if all_games:
        return ALL_AVAILABLE_GAMES
    if selected_game:
        matched = [g for g in ALL_AVAILABLE_GAMES if g["id"] == selected_game]
        if matched:
            return matched
        raise ValueError(f"Unknown game ID '{selected_game}'. Available: {[g['id'] for g in ALL_AVAILABLE_GAMES]}")
    
    mode_lower = (mode or "auto").lower()
    if mode_lower in ("midday", "morning"):
        return [DAILY_GAMES[0]]  # Player Chain (Step 2)
    elif mode_lower in ("evening", "night"):
        return [DAILY_GAMES[1]]  # Passport FC (Step 2)
    elif mode_lower == "both":
        return DAILY_GAMES

    # Auto mode: check hour
    if curr_hour is None:
        curr_hour = datetime.datetime.now().hour
    if curr_hour < 16:
        return [DAILY_GAMES[0]]  # Player Chain (Step 2)
    else:
        return [DAILY_GAMES[1]]  # Passport FC (Step 2)

def compute_scheduled_slots(num_videos, start_dt=None, slot_hours=None, immediate_first=True):
    """
    Computes scheduled publishing datetime slots.
    By default (immediate_first=True), publishes immediately live upon run.
    """
    if start_dt is None:
        start_dt = datetime.datetime.now(datetime.timezone.utc)
    if slot_hours is None:
        slot_hours = DEFAULT_PEAK_SLOTS
    
    slots = []
    if immediate_first and num_videos > 0:
        for _ in range(num_videos):
            slots.append({
                "dt": start_dt,
                "iso": None,
                "label": "NOW (Immediate Live Public)"
            })
        return slots

    sorted_hours = sorted(slot_hours)
    curr_date = start_dt.date()
    for day_offset in range(14):
        d = curr_date + datetime.timedelta(days=day_offset)
        for h in sorted_hours:
            candidate_dt = datetime.datetime(d.year, d.month, d.day, h, 0, 0, tzinfo=datetime.timezone.utc)
            if candidate_dt > start_dt + datetime.timedelta(minutes=5):
                if len(slots) < num_videos:
                    slots.append({
                        "dt": candidate_dt,
                        "iso": candidate_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "label": f"{candidate_dt.strftime('%Y-%m-%d %H:%M UTC')}"
                    })
            if len(slots) >= num_videos:
                break
        if len(slots) >= num_videos:
            break

    return slots

def get_target_name_from_game(game_id):
    """
    Extracts the daily puzzle target name/theme directly from the compiled HTML.
    Allows running live API deduplication BEFORE spending 2-3 minutes rendering video.
    """
    import json, re
    html_path = os.path.join(BASE_DIR, "games", f"{game_id}.html")
    if not os.path.exists(html_path):
        return ""
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
        var_map = {
            "top_transfers": r'const\s+DAILY_TRANSFER_GAME\s*=\s*(\{[\s\S]*?\});',
            "transfer_destination": r'const\s+DAILY_DESTINATION_GAME\s*=\s*(\{[\s\S]*?\});',
            "top_scorers": r'const\s+DAILY_SCORERS_GAME\s*=\s*(\{[\s\S]*?\});',
            "club_connect": r'const\s+DAILY_CLUBCONNECT_GAME\s*=\s*(\{[\s\S]*?\});',
            "player_chain": r'const\s+DAILY_CHAIN_GAME\s*=\s*(\{[\s\S]*?\});',
            "passport_fc": r'const\s+DAILY_PASSPORT_GAME\s*=\s*(\{[\s\S]*?\});',
        }
        pattern = var_map.get(game_id)
        if pattern:
            m = re.search(pattern, html)
            if m:
                data = json.loads(m.group(1))
                return data.get("name") or data.get("player_name") or data.get("target_player") or data.get("club") or ""
    except Exception as e:
        print(f"⚠️ Could not parse target name from {game_id}.html: {e}")
    return ""

async def process_all_games(
    mode="auto",
    slot_hours=None,
    fast_mode=False,
    port=8080,
    dry_run=False,
    selected_game="",
    all_games=False,
    no_youtube=False,
    no_instagram=False,
    instant_reels=True,
    immediate_first=True,
    wait_queue=False,
    force=False
):
    print("\n" + "=" * 68)
    print("   ⚽  PLAYMAKER — DAILY SHORTS & REELS UPLOADER (LIVE IMMEDIATE)")
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

    matchday_context = load_matchday_context_for_date(today_str)
    if matchday_context:
        print("\n" + "🔥" * 34)
        print(f"   MATCHDAY SPECIAL ACTIVE: {matchday_context.get('clash_name')} ({matchday_context.get('competition')})")
        print(f"   Hook: {matchday_context.get('hook')}")
        print(f"   Tags: {' '.join(matchday_context.get('hashtags', []))}")
        print("🔥" * 34 + "\n")

    print("\n💡 Publishing Mode: Direct Live Upload (Public YouTube Short & Instagram Reel immediately).")

    # 3. Compile today's latest daily puzzles
    print("🔄 Ensuring today's HTML game files are fully compiled and up to date...")
    subprocess.run([sys.executable, os.path.join(BASE_DIR, "fetch_daily.py")], check=True)

    server_proc = ensure_server_running(port)
    results = []
    
    games_to_run = select_games_for_mode(
        mode=mode,
        selected_game=selected_game,
        all_games=all_games
    )

    has_queued_reels = False

    try:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        target_slots = compute_scheduled_slots(
            num_videos=len(games_to_run),
            start_dt=now_utc,
            slot_hours=slot_hours,
            immediate_first=immediate_first
        )

        session_used_broll = []

        for i, game in enumerate(games_to_run):
            game_id = game["id"]
            game_name = game["name"]
            slot_info = target_slots[i]
            publish_at = slot_info["iso"]
            timing_label = slot_info["label"]
            sched_utc_dt = slot_info["dt"]

            print("\n" + "-" * 68)
            print(f"🎬 [{i+1}/{len(games_to_run)}] Processing: {game_name} ({game_id})")
            print(f"⏰ Schedule Target: {timing_label}")
            print("-" * 68)

            # Pre-flight check: extract target name from HTML
            preview_target = get_target_name_from_game(game_id)
            if preview_target:
                print(f"🔍 Pre-flight detected target: '{preview_target}' for {game_name}")

            # Deduplication checks
            yt_already_done = False
            yt_existing_url = ""
            ig_already_done = False
            ig_existing_url = ""

            if not force and not dry_run:
                # 1. YouTube check
                if not no_youtube and channel_id:
                    try:
                        yt_already_done, yt_existing_url = is_youtube_already_uploaded(
                            game_id=game_id,
                            target_name=preview_target,
                            date_str=today_str
                        )
                        if yt_already_done:
                            print(f"   ℹ️ [YouTube Check] Already uploaded today: {yt_existing_url}")
                    except Exception as e:
                        print(f"   ⚠️ YouTube deduplication check error: {e}")

                # 2. Instagram check
                if not no_instagram and ig_id:
                    try:
                        ig_already_done, ig_existing_url = is_ig_already_posted(
                            game_id=game_id,
                            date_str=today_str,
                            target_name=preview_target
                        )
                        if ig_already_done:
                            print(f"   ℹ️ [Instagram Check] Already uploaded today: {ig_existing_url}")
                    except Exception as e:
                        print(f"   ⚠️ Instagram deduplication check error: {e}")

                # If all requested platforms are already uploaded, skip rendering!
                yt_satisfied = no_youtube or yt_already_done
                ig_satisfied = no_instagram or ig_already_done

                if yt_satisfied and ig_satisfied:
                    print(f"\n⚡ [Deduplication] Both platforms already have today's video for {game_name}!")
                    print(f"   Skipping browser launch and video rendering to save compute & prevent duplicates.\n")
                    results.append({
                        "game": game_name,
                        "yt_status": "Already Uploaded" if yt_already_done else "Skipped",
                        "yt_url": yt_existing_url if yt_already_done else "—",
                        "ig_status": "Already Uploaded" if ig_already_done else "Skipped",
                        "ig_url": ig_existing_url if ig_already_done else "—"
                    })
                    continue

            # Render video
            custom_ig_caption = None
            custom_yt_title = None

            try:
                if game_id in ("player_chain", "passport_fc"):
                    ugc_data = extract_ugc_data(game_id, day=None)
                    target_name = f"{ugc_data['entity_1']} & {ugc_data['entity_2']}"
                    
                    broll_clip = select_broll_clip(exclude_paths=session_used_broll, game_id=game_id)
                    if broll_clip:
                        session_used_broll.append(broll_clip)
                        
                    os.makedirs(os.path.join(BASE_DIR, "output_shorts"), exist_ok=True)
                    video_path = os.path.join(BASE_DIR, "output_shorts", f"ugc_rarity_{game_id}_{today_str}.mp4")
                    render_ugc_video(ugc_data, video_path, bg_video_path=broll_clip)
                    custom_ig_caption = generate_ugc_caption(ugc_data)
                    
                    if ugc_data["mode"] == "passport_fc" or ugc_data.get("is_country"):
                        custom_yt_title = f"Name ONE {ugc_data['entity_2']} player for {ugc_data['entity_1']} (No one else will say) ⚽️ #Shorts"
                    else:
                        custom_yt_title = f"Name ONE player for {ugc_data['entity_1']} & {ugc_data['entity_2']} (No one else will say) ⚽️ #Shorts"
                else:
                    render_res = await record_short_video(game_id=game_id, day_offset=0, fast_mode=fast_mode, port=port, force=force)
                    if isinstance(render_res, tuple):
                        video_path, target_name = render_res
                    else:
                        video_path, target_name = render_res, ""
            except Exception as e:
                import traceback
                print(f"❌ Video rendering exception for {game_name}: {e}")
                traceback.print_exc()
                video_path, target_name = None, ""

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

            # Log metadata relevance status
            matched = is_puzzle_context_matched(game_id, target_name, matchday_context)
            if matchday_context:
                if matched:
                    clash = matchday_context.get("clash_name", "Matchday Special")
                    print(f"🎯 [Metadata] Context Matched: Applying '⚔️ {clash} SPECIAL!' for {game_name} ({target_name})")
                else:
                    print(f"ℹ️ [Metadata] Context Unmatched: Target '{target_name}' not in matchday clash. Using standard evergreen caption.")

            # ── A. Upload to YouTube Shorts ───────────────────────────────────
            yt_status, yt_url = "Skipped", "—"
            if yt_already_done:
                yt_status = "Already Uploaded"
                yt_url = yt_existing_url
            elif not no_youtube:
                if custom_yt_title:
                    title = custom_yt_title
                    desc = f"{title}\n\nPlay live football puzzles daily at https://playmaker.football\n\n#Shorts #football #ballknowledge #trivia"
                    tags = ["Shorts", "football", "soccer", "trivia", "quiz", "ball knowledge", "reels"]
                else:
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
            if ig_already_done:
                ig_status = "Already Uploaded"
                ig_url = ig_existing_url
            elif not no_instagram and ig_id:
                ig_caption = custom_ig_caption if custom_ig_caption else build_instagram_caption(game_id=game_id, target_name=target_name)
                
                if publish_at is None or instant_reels:
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
                            scheduled_utc_iso=publish_at,
                            game_id=game_id,
                            date_str=today_str,
                            target_name=target_name
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
    parser.add_argument("--mode", type=str, default="auto", choices=["auto", "midday", "morning", "evening", "night", "both", "all"], help="Publishing mode: auto (time-based), midday (Top Transfers), evening (Transfer Destination), or both")
    parser.add_argument("--midday", "--morning", dest="midday_flag", action="store_true", help="Shortcut for --mode midday (renders & uploads Top Transfers immediately)")
    parser.add_argument("--evening", "--night", dest="evening_flag", action="store_true", help="Shortcut for --mode evening (renders & uploads Transfer Destination immediately)")
    parser.add_argument("--both", action="store_true", help="Shortcut for --mode both (renders & uploads both Top Transfers & Transfer Destination)")
    parser.add_argument("--all-games", action="store_true", help="Render all 6 games instead of default 2")
    parser.add_argument("--game", type=str, default="", help="Run a specific game ID only (e.g. top_transfers, transfer_destination)")
    parser.add_argument("--slots", type=str, default="12,20", help="Comma-separated UTC peak hours (default: '12,20')")
    parser.add_argument("--schedule-future", action="store_true", help="Schedule uploads for future peak hours instead of uploading live immediately")
    parser.add_argument("--port", type=int, default=8080, help="Local server port (default: 8080)")
    parser.add_argument("--fast", action="store_true", help="Fast mode for testing")
    parser.add_argument("--dry-run", action="store_true", help="Render videos only without uploading")
    parser.add_argument("--no-youtube", action="store_true", help="Skip YouTube upload")
    parser.add_argument("--no-instagram", action="store_true", help="Skip Instagram upload")
    parser.add_argument("--wait-queue", action="store_true", help="Wait in foreground for all queued reels to finish (ideal for GitHub Actions)")
    parser.add_argument("--force", action="store_true", help="Bypass deduplication checks and re-render/re-upload")

    args = parser.parse_args()
    
    mode = args.mode
    if args.midday_flag:
        mode = "midday"
    elif args.evening_flag:
        mode = "evening"
    elif args.both:
        mode = "both"
    elif args.all_games:
        mode = "all"

    try:
        slot_hours = [int(h.strip()) for h in args.slots.split(",") if h.strip()]
    except Exception:
        slot_hours = DEFAULT_PEAK_SLOTS

    # By default, upload live immediately (immediate_first=True unless --schedule-future is passed)
    immediate_first = not args.schedule_future

    asyncio.run(process_all_games(
        mode=mode,
        slot_hours=slot_hours,
        fast_mode=args.fast,
        port=args.port,
        dry_run=args.dry_run,
        selected_game=args.game,
        all_games=args.all_games or (mode == "all"),
        no_youtube=args.no_youtube,
        no_instagram=args.no_instagram,
        instant_reels=True,
        immediate_first=immediate_first,
        wait_queue=args.wait_queue,
        force=args.force
    ))

if __name__ == "__main__":
    main()
