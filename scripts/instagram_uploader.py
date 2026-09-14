#!/usr/bin/env python3
"""
Playmaker Instagram Reels Uploader & Resilient Queue Scheduler.
Uses Meta Graph API's Resumable Binary Upload protocol to publish Reels directly.
Handles delayed publishing via a lightweight local background queue daemon with sleep catch-up.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.parse
import urllib.error
import datetime
import argparse
import subprocess
import signal

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIVATE_DIR = os.path.join(BASE_DIR, "private")
CONFIG_FILE = os.path.join(PRIVATE_DIR, "instagram_config.json")
QUEUE_FILE = os.path.join(PRIVATE_DIR, "instagram_queue.json")
LEDGER_FILE = os.path.join(PRIVATE_DIR, "instagram_ledger.json")
LOG_FILE = os.path.join(PRIVATE_DIR, "instagram_uploader.log")
PID_FILE = os.path.join(PRIVATE_DIR, "instagram_daemon.pid")

def log_message(msg):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    try:
        os.makedirs(PRIVATE_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

def load_config():
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            f"❌ Instagram configuration not found at {CONFIG_FILE}!\n"
            "Please ensure private/instagram_config.json exists with your Meta tokens."
        )
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def check_connection(silent=False):
    """Verifies token validity and prints connected Instagram business profile."""
    config = load_config()
    token = config["access_token"]
    page_id = config["page_id"]
    
    url = f"https://graph.facebook.com/v21.0/{page_id}?fields=id,name,instagram_business_account{{id,username}}&access_token={token}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            ig_account = data.get("instagram_business_account")
            if not ig_account:
                raise RuntimeError("Facebook page is not connected to an Instagram Business account.")
            username = ig_account.get("username", "unknown")
            ig_id = ig_account.get("id", config.get("ig_user_id"))
            if not silent:
                print(f"✅ Connected to Instagram: @{username} (ID: {ig_id})")
            return username, ig_id
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        raise RuntimeError(f"Meta Graph API authentication failed (HTTP {e.code}): {err_msg}")
    except Exception as e:
        raise RuntimeError(f"Could not connect to Instagram: {e}")

def build_instagram_caption(game_id="top_transfers", target_name=""):
    """Generates an engaging, high-converting caption with hashtags for Instagram Reels."""
    game_hooks = {
        "top_transfers": f"Can you guess {target_name or 'the club'}'s record transfers? ⚽",
        "transfer_destination": "Guess the mystery player's career path backwards! ⚽",
        "player_chain": "Can you complete this teammate chain? ⚽",
        "club_connect": "Name players who played for both clubs! ⚽",
        "top_scorers": f"Who scored the most goals in {target_name or 'this season'}? ⚽",
        "passport_fc": f"Can you complete {target_name or 'today'}'s club passport? ✈️"
    }
    hook = game_hooks.get(game_id, "Daily Football Quiz Challenge! ⚽")
    
    caption = (
        f"{hook}\n\n"
        f"Comment your score below! 👇\n\n"
        f"🎮 Play today's free daily puzzles at: playmaker.best (link in bio!)\n\n"
        f"#reels #football #soccer #footballquiz #soccerquiz #premierleague #realmadrid "
        f"#championsleague #footballtrivia #playmaker #footy"
    )
    return caption

# ── Ledger (Deduplication) ───────────────────────────────────────────────────

def _load_ledger():
    if os.path.exists(LEDGER_FILE):
        try:
            with open(LEDGER_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def _save_ledger(ledger):
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    with open(LEDGER_FILE, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2)

def is_already_posted(game_id, date_str, target_name=""):
    """
    Checks if a reel for game_id was already posted on date_str.
    Checks both the local ledger and live Instagram Graph API.
    Returns (already_posted: bool, permalink_or_reason: str).
    """
    # 1. Check local ledger
    ledger = _load_ledger()
    key = f"{date_str}_{game_id}"
    if key in ledger:
        return True, ledger[key].get("permalink", "In Local Ledger")

    # 2. Check live Instagram Graph API
    try:
        config = load_config()
        token = config.get("access_token")
        ig_user_id = config.get("ig_user_id")
        if not token or not ig_user_id:
            return False, ""
        url = f"https://graph.facebook.com/v21.0/{ig_user_id}/media?fields=id,caption,timestamp,permalink&limit=15&access_token={token}"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            expected_caption = build_instagram_caption(game_id, target_name)
            hook = expected_caption.splitlines()[0].strip().lower()
            
            for item in data.get("data", []):
                pub_date = item.get("timestamp", "")[:10]
                caption = item.get("caption", "")
                permalink = item.get("permalink", f"https://www.instagram.com/reel/{item.get('id')}/")
                first_line = caption.splitlines()[0].strip().lower() if caption else ""
                
                # Check if published on the given date and hook or target_name matches
                if pub_date == date_str:
                    if hook in first_line or first_line in hook or (target_name and target_name.lower() in caption.lower()):
                        mark_as_posted(game_id, date_str, permalink, item.get("id"))
                        return True, permalink
    except Exception as e:
        log_message(f"⚠️ Instagram live deduplication check warning: {e}")

    return False, ""

def mark_as_posted(game_id, date_str, permalink, ig_media_id):
    ledger = _load_ledger()
    key = f"{date_str}_{game_id}"
    ledger[key] = {
        "game_id": game_id,
        "date": date_str,
        "permalink": permalink,
        "ig_media_id": ig_media_id,
        "posted_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    _save_ledger(ledger)

# ── Resumable Reel Upload ────────────────────────────────────────────────────

def upload_reel_now(video_path, caption=None, share_to_feed=True, max_retries=3):
    """
    Directly uploads and publishes an MP4 video as an Instagram Reel using
    Meta's official Resumable Upload protocol.
    Returns (ig_media_id, permalink).
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
    
    file_size = os.path.getsize(video_path)
    if file_size == 0:
        raise ValueError(f"Video file is empty: {video_path}")

    config = load_config()
    token = config["access_token"]
    ig_user_id = config["ig_user_id"]

    log_message(f"🚀 [Instagram] Initializing Reels container for {os.path.basename(video_path)} ({file_size / (1024*1024):.2f} MB)...")

    # Step 1: Create media container
    container_url = f"https://graph.facebook.com/v21.0/{ig_user_id}/media"
    container_data = {
        "upload_type": "resumable",
        "media_type": "REELS",
        "share_to_feed": "true" if share_to_feed else "false",
        "access_token": token
    }
    if caption:
        container_data["caption"] = caption

    encoded_data = urllib.parse.urlencode(container_data).encode("utf-8")
    req = urllib.request.Request(container_url, data=encoded_data, method="POST")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            container_id = res["id"]
            upload_uri = res["uri"]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        raise RuntimeError(f"Failed to create Instagram media container (HTTP {e.code}): {err_body}")

    log_message(f"📦 [Instagram] Container created (ID: {container_id}). Uploading binary data...")

    # Step 2: Resumable binary upload to rupload.facebook.com
    with open(video_path, "rb") as vf:
        video_bytes = vf.read()

    upload_headers = {
        "Authorization": f"OAuth {token}",
        "file_size": str(file_size),
        "offset": "0",
        "Content-Type": "application/octet-stream"
    }

    upload_req = urllib.request.Request(upload_uri, data=video_bytes, headers=upload_headers, method="POST")

    upload_success = False
    for attempt in range(1, max_retries + 1):
        try:
            with urllib.request.urlopen(upload_req, timeout=120) as resp:
                upload_resp = json.loads(resp.read().decode("utf-8"))
                if upload_resp.get("success") is True or resp.status in (200, 201):
                    upload_success = True
                    break
        except Exception as e:
            log_message(f"⚠️ [Instagram] Binary upload attempt {attempt}/{max_retries} error: {e}")
            if attempt < max_retries:
                time.sleep(3 * attempt)
            else:
                raise RuntimeError(f"Failed to upload video binary after {max_retries} attempts: {e}")

    if not upload_success:
        raise RuntimeError("Video binary upload did not receive success confirmation.")

    log_message(f"⏳ [Instagram] Binary uploaded. Polling Meta video processing...")

    # Step 3: Poll container status until FINISHED
    status_url = f"https://graph.facebook.com/v21.0/{container_id}?fields=status_code,status&access_token={token}"
    max_polls = 60 # 5 minutes total (60 * 5s)
    processed = False

    for poll in range(max_polls):
        time.sleep(5)
        try:
            req = urllib.request.Request(status_url)
            with urllib.request.urlopen(req, timeout=15) as resp:
                status_res = json.loads(resp.read().decode("utf-8"))
                status_code = status_res.get("status_code", "")
                if status_code == "FINISHED":
                    processed = True
                    break
                elif status_code == "ERROR":
                    err_detail = status_res.get("status", "Unknown transcoding error")
                    raise RuntimeError(f"Meta video processing failed: {err_detail}")
                elif status_code == "IN_PROGRESS":
                    if poll % 4 == 0:
                        log_message(f"⏳ [Instagram] Video processing in progress... ({poll*5}s elapsed)")
        except urllib.error.HTTPError as e:
            log_message(f"⚠️ Polling warning (HTTP {e.code}): {e.read().decode('utf-8')}")

    if not processed:
        raise TimeoutError(f"Meta video processing timed out after {max_polls*5} seconds.")

    log_message(f"✨ [Instagram] Video processed! Publishing Reel...")

    # Step 4: Publish media
    publish_url = f"https://graph.facebook.com/v21.0/{ig_user_id}/media_publish"
    publish_data = urllib.parse.urlencode({
        "creation_id": container_id,
        "access_token": token
    }).encode("utf-8")

    pub_req = urllib.request.Request(publish_url, data=publish_data, method="POST")
    try:
        with urllib.request.urlopen(pub_req, timeout=30) as resp:
            pub_res = json.loads(resp.read().decode("utf-8"))
            ig_media_id = pub_res["id"]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        raise RuntimeError(f"Failed to publish Reel (HTTP {e.code}): {err_body}")

    # Step 5: Query permalink
    permalink = f"https://www.instagram.com/reel/{ig_media_id}/"
    try:
        detail_url = f"https://graph.facebook.com/v21.0/{ig_media_id}?fields=permalink&access_token={token}"
        req = urllib.request.Request(detail_url)
        with urllib.request.urlopen(req, timeout=15) as resp:
            detail_res = json.loads(resp.read().decode("utf-8"))
            if "permalink" in detail_res:
                permalink = detail_res["permalink"]
    except Exception:
        pass

    log_message(f"🎉 [Instagram] Reel published successfully! Link: {permalink}")
    return ig_media_id, permalink

# ── Queue & Scheduler ────────────────────────────────────────────────────────

def _load_queue():
    if os.path.exists(QUEUE_FILE):
        try:
            with open(QUEUE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def _save_queue(queue):
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    with open(QUEUE_FILE, "w", encoding="utf-8") as f:
        json.dump(queue, f, indent=2)

def queue_reel(video_path, caption, scheduled_utc_iso, game_id, date_str):
    """Adds a reel to the local queue for delayed publishing."""
    queue = _load_queue()
    # Check if this exact item is already queued
    for item in queue:
        if item.get("game_id") == game_id and item.get("date_str") == date_str and item.get("status") == "pending":
            log_message(f"ℹ️ [Instagram Queue] {game_id} for {date_str} already in queue.")
            return

    queue.append({
        "video_path": os.path.abspath(video_path),
        "caption": caption,
        "scheduled_utc": scheduled_utc_iso,
        "game_id": game_id,
        "date_str": date_str,
        "status": "pending",
        "retries": 0,
        "added_at": datetime.datetime.now(datetime.timezone.utc).isoformat()
    })
    _save_queue(queue)
    log_message(f"📅 [Instagram Queue] Scheduled {game_id} for {scheduled_utc_iso}")

def get_queue_status():
    queue = _load_queue()
    pending = [q for q in queue if q.get("status") == "pending"]
    return {"total": len(queue), "pending": len(pending), "items": pending}

def process_queue(force_all=False):
    """
    Evaluates queued reels. If scheduled_utc <= now (or force_all), uploads and publishes.
    Returns list of processed items and their results.
    """
    queue = _load_queue()
    if not queue:
        return []

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    remaining_queue = []
    processed_results = []

    for item in queue:
        if item.get("status") != "pending":
            continue

        sched_str = item.get("scheduled_utc")
        try:
            sched_dt = datetime.datetime.fromisoformat(sched_str.replace("Z", "+00:00"))
        except Exception:
            sched_dt = now_utc

        is_due = (sched_dt <= now_utc) or force_all
        game_id = item.get("game_id")
        date_str = item.get("date_str")
        video_path = item.get("video_path")

        if not is_due:
            remaining_queue.append(item)
            continue

        log_message(f"⏰ [Instagram Queue] Processing due reel: {game_id} (scheduled {sched_str})")

        # Deduplication check
        if is_already_posted(game_id, date_str):
            log_message(f"ℹ️ [Instagram Queue] {game_id} ({date_str}) is already recorded in ledger. Skipping.")
            item["status"] = "already_posted"
            processed_results.append({"game_id": game_id, "status": "Already Posted"})
            continue

        try:
            ig_id, permalink = upload_reel_now(
                video_path=video_path,
                caption=item.get("caption")
            )
            mark_as_posted(game_id, date_str, permalink, ig_id)
            item["status"] = "published"
            item["permalink"] = permalink
            processed_results.append({"game_id": game_id, "status": "Published", "permalink": permalink})
        except Exception as e:
            log_message(f"❌ [Instagram Queue] Failed to publish {game_id}: {e}")
            retries = item.get("retries", 0) + 1
            item["retries"] = retries
            if retries >= 3:
                item["status"] = f"failed: {e}"
                processed_results.append({"game_id": game_id, "status": f"Failed: {e}"})
            else:
                # Keep in queue to retry on next loop
                remaining_queue.append(item)

    _save_queue(remaining_queue)
    return processed_results

def run_daemon():
    """Background daemon loop: wakes every 60s, processes due reels, exits when queue is clear."""
    # Write PID
    pid = os.getpid()
    with open(PID_FILE, "w") as f:
        f.write(str(pid))
    log_message(f"🤖 [Instagram Daemon] Started with PID {pid}")

    try:
        while True:
            queue = _load_queue()
            pending = [q for q in queue if q.get("status") == "pending"]
            if not pending:
                log_message("🎉 [Instagram Daemon] All queued reels have been processed! Exiting cleanly.")
                break

            process_queue(force_all=False)
            time.sleep(60)
    finally:
        if os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except Exception:
                pass

def start_background_daemon():
    """Spawns the background daemon detached from the current process."""
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            # Check if running
            os.kill(old_pid, 0)
            log_message(f"ℹ️ [Instagram Daemon] Background scheduler already active (PID {old_pid}).")
            return
        except (OSError, ValueError):
            # Stale PID file
            pass

    log_message("🚀 Spawning background Instagram scheduler daemon...")
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as out:
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--daemon"],
            stdout=out,
            stderr=subprocess.STDOUT,
            start_new_session=True
        )

# ── CLI Interface ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Playmaker Instagram Reels Uploader & Scheduler")
    parser.add_argument("--check", action="store_true", help="Verify Instagram connection and credentials")
    parser.add_argument("--file", help="Path to video file to upload immediately")
    parser.add_argument("--caption", help="Caption for the reel")
    parser.add_argument("--game", default="top_transfers", help="Game ID for caption generation")
    parser.add_argument("--target", default="", help="Target name for caption generation")
    parser.add_argument("--daemon", action="store_true", help="Run background queue processor loop")
    parser.add_argument("--process-now", action="store_true", help="Process all due queued reels now")
    parser.add_argument("--force-queue", action="store_true", help="Force publish all queued reels immediately")
    parser.add_argument("--queue-status", action="store_true", help="Print current queue status")

    args = parser.parse_args()

    if args.check:
        try:
            check_connection(silent=False)
        except Exception as e:
            print(f"❌ Connection check failed: {e}")
            sys.exit(1)
        return

    if args.queue_status:
        st = get_queue_status()
        print(f"Queue Status: {st['pending']} pending items out of {st['total']} total.")
        for item in st["items"]:
            print(f"  • {item['game_id']} | Scheduled: {item['scheduled_utc']} | Retries: {item['retries']}")
        return

    if args.process_now or args.force_queue:
        results = process_queue(force_all=args.force_queue)
        print("Processed results:", results)
        return

    if args.daemon:
        run_daemon()
        return

    if args.file:
        caption = args.caption or build_instagram_caption(args.game, args.target)
        try:
            ig_id, permalink = upload_reel_now(args.file, caption)
            print(f"✅ Success! Reel URL: {permalink}")
        except Exception as e:
            print(f"❌ Upload failed: {e}")
            sys.exit(1)
        return

    parser.print_help()

if __name__ == "__main__":
    main()
