#!/usr/bin/env python3
"""
Playmaker TikTok Video Uploader & Deduplication Ledger.
Uses TikTok Content Posting API v2:
- Chunked Resumable Video Uploads (FILE_UPLOAD)
- Automatic OAuth 2.0 Token Refresh via https://open.tiktokapis.com/v2/oauth/token/
- User Info verification via https://open.tiktokapis.com/v2/user/info/
- Publish status polling via https://open.tiktokapis.com/v2/post/publish/status/fetch/
- Deduplication ledger in private/tiktok_ledger.json
"""

import os
import sys
import time
import json
import math
import datetime
import argparse
import urllib.request
import urllib.parse
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIVATE_DIR = os.path.join(BASE_DIR, "private")
CONFIG_FILE = os.path.join(PRIVATE_DIR, "tiktok_config.json")
LEDGER_FILE = os.path.join(PRIVATE_DIR, "tiktok_ledger.json")
LOG_FILE = os.path.join(PRIVATE_DIR, "tiktok_uploader.log")

DEFAULT_CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB per chunk (TikTok minimum is 5MB, max 64MB; total size is allowed for small files)

def log_message(msg):
    """Logs message with timestamp to stdout and private/tiktok_uploader.log."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted = f"[{timestamp}] {msg}"
    print(formatted)
    try:
        os.makedirs(PRIVATE_DIR, exist_ok=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted + "\n")
    except Exception:
        pass

# ── Configuration Management & Token Refresh ──────────────────────────────────

def load_config():
    """Loads TikTok configuration from private/tiktok_config.json."""
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            f"❌ TikTok configuration not found at {CONFIG_FILE}!\n"
            "Please run scripts/exchange_tiktok_token.py or configure private/tiktok_config.json."
        )
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    """Saves TikTok configuration to private/tiktok_config.json."""
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

def refresh_access_token(config=None):
    """
    Refreshes the TikTok OAuth 2.0 access token using refresh_token.
    POST https://open.tiktokapis.com/v2/oauth/token/
    Content-Type: application/x-www-form-urlencoded
    """
    if config is None:
        config = load_config()

    client_key = config.get("client_key")
    client_secret = config.get("client_secret")
    refresh_token = config.get("refresh_token")

    if not client_key or not client_secret:
        raise ValueError("client_key and client_secret are required in tiktok_config.json")
    if not refresh_token:
        raise ValueError("refresh_token is missing in tiktok_config.json. Re-authenticate via exchange_tiktok_token.py")

    url = "https://open.tiktokapis.com/v2/oauth/token/"
    payload = urllib.parse.urlencode({
        "client_key": client_key,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        raise RuntimeError(f"TikTok token refresh HTTP error ({e.code}): {err_msg}")
    except Exception as e:
        raise RuntimeError(f"TikTok token refresh failed: {e}")

    # Check TikTok v2 response structure
    # Response may contain tokens directly or inside data field
    token_data = data.get("data", data)
    new_access_token = token_data.get("access_token")
    if not new_access_token:
        err_desc = data.get("error_description", data.get("message", json.dumps(data)))
        raise RuntimeError(f"TikTok token refresh returned no access_token: {err_desc}")

    now_ts = int(time.time())
    expires_in = token_data.get("expires_in", 86400)
    refresh_expires_in = token_data.get("refresh_expires_in", 31536000)

    config["access_token"] = new_access_token
    if token_data.get("refresh_token"):
        config["refresh_token"] = token_data["refresh_token"]
    if token_data.get("open_id"):
        config["open_id"] = token_data["open_id"]

    config["expires_at"] = now_ts + int(expires_in)
    config["refresh_expires_at"] = now_ts + int(refresh_expires_in)

    save_config(config)
    log_message(f"🔄 TikTok access token refreshed successfully (valid for ~{expires_in // 3600} hours).")
    return config

def get_valid_access_token():
    """Returns a valid access token, auto-refreshing if expired or within 5 minutes of expiring."""
    config = load_config()
    expires_at = config.get("expires_at", 0)
    now_ts = int(time.time())

    # If expires_at is 0 or expires within 300 seconds, refresh
    if expires_at == 0 or (expires_at - now_ts) < 300:
        log_message("⏳ TikTok access token expired or near expiration. Auto-refreshing...")
        config = refresh_access_token(config)

    return config["access_token"]

# ── Connection Verification ──────────────────────────────────────────────────

def check_connection(silent=False):
    """
    Verifies TikTok connection and fetches creator info.
    Primary: POST https://open.tiktokapis.com/v2/post/publish/creator_info/query/
    Fallback: GET https://open.tiktokapis.com/v2/user/info/?fields=avatar_url,display_name,username,open_id
    Returns dict with username, display_name, avatar_url, open_id.
    """
    token = get_valid_access_token()
    config = load_config()

    # Try creator_info endpoint first (authorized via Content Posting API)
    creator_url = "https://open.tiktokapis.com/v2/post/publish/creator_info/query/"
    req = urllib.request.Request(
        creator_url,
        data=b"{}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("error", {}).get("code") == "ok":
            c_data = data.get("data", {})
            user_sub = c_data.get("user", {})
            username = c_data.get("creator_username") or user_sub.get("username")
            if username:
                display_name = c_data.get("creator_nickname") or user_sub.get("display_name", username)
                avatar_url = c_data.get("creator_avatar_url") or user_sub.get("avatar_url", "")
                open_id = user_sub.get("open_id") or config.get("open_id", "")
                if not silent:
                    log_message(f"✅ Connected to TikTok: @{username} ({display_name})")
                return {
                    "username": username,
                    "display_name": display_name,
                    "avatar_url": avatar_url,
                    "open_id": open_id,
                    "privacy_levels": c_data.get("privacy_level_options", []),
                    "max_duration": c_data.get("max_video_post_duration_sec", 600)
                }
    except Exception:
        pass

    # Fallback to user/info if Login Kit scope is present
    fields = "avatar_url,display_name,username,open_id"
    url = f"https://open.tiktokapis.com/v2/user/info/?fields={fields}"
    req = urllib.request.Request(
        url,
        headers={"Authorization": f"Bearer {token}"},
        method="GET"
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        raise RuntimeError(f"TikTok user info request failed (HTTP {e.code}): {err_msg}")
    except Exception as e:
        raise RuntimeError(f"Could not connect to TikTok: {e}")

    error_info = data.get("error", {})
    if error_info.get("code") and error_info.get("code") != "ok":
        raise RuntimeError(f"TikTok API Error: {error_info.get('message', 'Unknown error')} (code: {error_info.get('code')})")

    user_info = data.get("data", {}).get("user", {})
    username = user_info.get("username", "unknown")
    display_name = user_info.get("display_name", username)
    avatar_url = user_info.get("avatar_url", "")
    open_id = user_info.get("open_id", config.get("open_id", ""))

    if not silent:
        log_message(f"✅ Connected to TikTok: @{username} ({display_name})")

    return {
        "username": username,
        "display_name": display_name,
        "avatar_url": avatar_url,
        "open_id": open_id
    }

# ── Resumable Chunked Video Upload (TikTok Content Posting API v2) ───────────

def init_video_publish(
    video_path,
    caption,
    title=None,
    privacy_level="PUBLIC_TO_EVERYONE",
    disable_duet=False,
    disable_comment=False,
    disable_stitch=False,
    chunk_size=DEFAULT_CHUNK_SIZE
):
    """
    Initializes a video publish request via TikTok Content Posting API v2.
    POST https://open.tiktokapis.com/v2/post/publish/video/init/
    Returns (publish_id, upload_url, total_chunks, chunk_size, total_size).
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    total_size = os.path.getsize(video_path)
    if total_size <= 0:
        raise ValueError(f"Video file is empty: {video_path}")

    # If the video is smaller than chunk_size, single chunk is fine
    actual_chunk_size = min(chunk_size, total_size)
    total_chunks = math.ceil(total_size / actual_chunk_size)

    token = get_valid_access_token()
    url = "https://open.tiktokapis.com/v2/post/publish/video/init/"

    raw_text = (title or caption or "")
    post_title = clean_tiktok_caption(raw_text)[:2200]

    body = {
        "post_info": {
            "title": post_title,
            "privacy_level": privacy_level,
            "disable_duet": disable_duet,
            "disable_comment": disable_comment,
            "disable_stitch": disable_stitch,
            "video_cover_timestamp_ms": 1000
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": total_size,
            "chunk_size": actual_chunk_size,
            "total_chunk_count": total_chunks
        }
    }

    req_data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=req_data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json; charset=UTF-8"
        },
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8")
        raise RuntimeError(f"TikTok init_video_publish HTTP {e.code}: {err_msg}")
    except Exception as e:
        raise RuntimeError(f"TikTok init_video_publish failed: {e}")

    error_info = data.get("error", {})
    if error_info.get("code") and error_info.get("code") != "ok":
        raise RuntimeError(f"TikTok init video error: {error_info.get('message')} (code: {error_info.get('code')})")

    res_data = data.get("data", {})
    publish_id = res_data.get("publish_id")
    upload_url = res_data.get("upload_url")

    if not publish_id or not upload_url:
        raise RuntimeError(f"TikTok init video response missing publish_id or upload_url: {data}")

    return publish_id, upload_url, total_chunks, actual_chunk_size, total_size

def upload_video_chunks(video_path, upload_url, actual_chunk_size, total_size):
    """
    Streams video binary bytes to upload_url in chunks with Content-Range header.
    PUT upload_url
    Content-Range: bytes <start>-<end>/<total>
    Content-Type: video/mp4
    """
    log_message(f"📤 Uploading video ({total_size / (1024*1024):.2f} MB) in chunks of {actual_chunk_size / (1024*1024):.2f} MB...")

    with open(video_path, "rb") as f:
        bytes_sent = 0
        chunk_idx = 0

        while bytes_sent < total_size:
            chunk_data = f.read(actual_chunk_size)
            if not chunk_data:
                break

            start = bytes_sent
            end = bytes_sent + len(chunk_data) - 1

            headers = {
                "Content-Type": "video/mp4",
                "Content-Range": f"bytes {start}-{end}/{total_size}",
                "Content-Length": str(len(chunk_data))
            }

            req = urllib.request.Request(
                upload_url,
                data=chunk_data,
                headers=headers,
                method="PUT"
            )

            retries = 3
            success = False
            while retries > 0:
                try:
                    with urllib.request.urlopen(req, timeout=60) as resp:
                        if resp.status in (200, 201, 206):
                            success = True
                            break
                        else:
                            raise RuntimeError(f"Unexpected status: {resp.status}")
                except urllib.error.HTTPError as e:
                    # Some upload servers respond with 200/206
                    if e.code in (200, 201, 206):
                        success = True
                        break
                    retries -= 1
                    time.sleep(2)
                    if retries == 0:
                        err_body = e.read().decode("utf-8") if hasattr(e, "read") else ""
                        raise RuntimeError(f"Chunk upload failed at bytes {start}-{end} (HTTP {e.code}): {err_body}")
                except Exception as e:
                    retries -= 1
                    time.sleep(2)
                    if retries == 0:
                        raise RuntimeError(f"Chunk upload error at bytes {start}-{end}: {e}")

            bytes_sent += len(chunk_data)
            chunk_idx += 1
            progress_pct = (bytes_sent / total_size) * 100
            log_message(f"   ✓ Chunk {chunk_idx}: bytes {start}-{end}/{total_size} uploaded ({progress_pct:.1f}%)")

    log_message("✅ All video chunks uploaded successfully.")

def poll_publish_status(publish_id, max_attempts=30, interval_seconds=3):
    """
    Polls the TikTok publish status until completion, failure, or timeout.
    POST https://open.tiktokapis.com/v2/post/publish/status/fetch/
    Returns status_dict with status, post_id, reason, etc.
    """
    token = get_valid_access_token()
    url = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"

    req_data = json.dumps({"publish_id": publish_id}).encode("utf-8")

    for attempt in range(1, max_attempts + 1):
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=UTF-8"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            err_msg = e.read().decode("utf-8")
            log_message(f"⚠️ Status check HTTP {e.code}: {err_msg}")
            time.sleep(interval_seconds)
            continue
        except Exception as e:
            log_message(f"⚠️ Status check error: {e}")
            time.sleep(interval_seconds)
            continue

        res_data = data.get("data", {})
        status = res_data.get("status", "")

        if status == "SUCCESS":
            log_message(f"🎉 TikTok publish SUCCESS! Publish ID: {publish_id}")
            return res_data
        elif status == "FAILED":
            fail_reason = res_data.get("fail_reason", "Unknown failure reason")
            raise RuntimeError(f"TikTok video publish FAILED: {fail_reason}")
        elif status in ("PROCESSING_UPLOAD", "PROCESSING_DOWNLOAD", "CHECK_PASS", "UPLOADING"):
            log_message(f"⏳ Processing TikTok video... (attempt {attempt}/{max_attempts}, status: {status})")
        else:
            log_message(f"ℹ️ Status: {status} (attempt {attempt}/{max_attempts})")

        time.sleep(interval_seconds)

    # If timed out, return last status rather than crashing hard if already processing
    log_message(f"⚠️ Polling timed out after {max_attempts * interval_seconds}s for publish ID: {publish_id}. Status remains {status}.")
    return res_data

def upload_tiktok_now(
    video_path,
    caption,
    privacy_level="PUBLIC_TO_EVERYONE",
    title=None,
    disable_duet=False,
    disable_comment=False,
    disable_stitch=False,
    poll_status=True
):
    """
    High-level function: initializes, uploads chunks, and optionally polls status.
    Returns (publish_id, result_data).
    """
    log_message(f"🚀 [TikTok] Starting upload for '{video_path}'...")
    publish_id, upload_url, total_chunks, chunk_size, total_size = init_video_publish(
        video_path=video_path,
        caption=caption,
        title=title,
        privacy_level=privacy_level,
        disable_duet=disable_duet,
        disable_comment=disable_comment,
        disable_stitch=disable_stitch
    )

    upload_video_chunks(video_path, upload_url, chunk_size, total_size)

    result_data = {"publish_id": publish_id, "status": "UPLOADED"}
    if poll_status:
        result_data = poll_publish_status(publish_id)

    return publish_id, result_data

# ── Deduplication & Ledger ───────────────────────────────────────────────────

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
    Checks if a video for game_id was already posted on date_str.
    Checks the local ledger first.
    Returns (already_posted: bool, publish_id_or_url: str).
    """
    ledger = _load_ledger()
    key = f"{date_str}_{game_id}"

    if key in ledger:
        entry = ledger[key]
        return True, entry.get("publish_id", "In Local Ledger")

    # If target_name is specified, also check by target key if present
    if target_name and target_name.strip():
        norm_target = target_name.strip().lower()
        for k, v in ledger.items():
            if v.get("date") == date_str and v.get("target_name", "").strip().lower() == norm_target:
                return True, v.get("publish_id", "In Local Ledger")

    return False, ""

def mark_as_posted(game_id, date_str, publish_id, target_name="", post_data=None):
    """Records an uploaded video in private/tiktok_ledger.json."""
    ledger = _load_ledger()
    key = f"{date_str}_{game_id}"
    ledger[key] = {
        "game_id": game_id,
        "date": date_str,
        "publish_id": publish_id,
        "target_name": target_name,
        "posted_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "post_data": post_data or {}
    }
    _save_ledger(ledger)

# ── Caption Helper ────────────────────────────────────────────────────────────

def clean_tiktok_caption(caption: str) -> str:
    """
    Sanitizes caption for TikTok:
    - Strips #reels, #reel, #linkinbio hashtags
    - Strips 'link in bio' / '(link in bio!)' references
    - Ensures TikTok discovery hashtags (#fyp, #footballtiktok, #foryou)
    - Normalizes spacing and clean line breaks
    """
    if not caption:
        return ""
    import re
    text = caption
    # Remove #reels, #reel, #linkinbio hashtags (case-insensitive)
    text = re.sub(r"(?i)#reels\b", "", text)
    text = re.sub(r"(?i)#reel\b", "", text)
    text = re.sub(r"(?i)#linkinbio\b", "", text)
    
    # Remove "(link in bio!)", "link in bio!", "(link in bio)", "link in bio"
    text = re.sub(r"(?i)\(?\s*link\s+in\s+bio\s*!?\s*\)?", "", text)
    
    # Clean up empty parens and normalize spaces
    text = re.sub(r"\(\s*\)", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Ensure TikTok specific discovery tags
    if "#fyp" not in text:
        text = text.strip() + " #fyp #footballtiktok #foryou"

    return text.strip()

def build_tiktok_caption(game_id="top_transfers", target_name="", matchday_context=None, date_str=None):
    """
    Generates high-converting, viral caption with relevant hashtags for TikTok.
    Excludes #reels and 'link in bio', optimizing for TikTok algorithmic distribution.
    """
    try:
        from scripts.instagram_uploader import build_instagram_caption
        raw_cap = build_instagram_caption(game_id, target_name, matchday_context, date_str)
        return clean_tiktok_caption(raw_cap)
    except Exception:
        # Fallback if instagram uploader is not imported
        return clean_tiktok_caption(
            f"Daily Football Challenge! Can you guess {target_name or 'the answer'}? ⚽ #football #soccer #trivia #playmaker"
        )

# ── CLI Interface ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Playmaker TikTok Video Uploader & Verification CLI")
    parser.add_argument("--verify", "--check", dest="verify", action="store_true", help="Verify TikTok connection and access token")
    parser.add_argument("--refresh-token", action="store_true", help="Manually force refresh TikTok OAuth access token")
    parser.add_argument("--upload", type=str, help="Path to video file to upload to TikTok")
    parser.add_argument("--caption", type=str, help="Caption for the TikTok post")
    parser.add_argument("--title", type=str, help="Title for the post (max 150 chars)")
    parser.add_argument("--privacy", default="PUBLIC_TO_EVERYONE", choices=["PUBLIC_TO_EVERYONE", "MUTUAL_FOLLOW_FRIENDS", "SELF_ONLY", "FOLLOWER_OF_CREATOR"], help="Privacy level")
    parser.add_argument("--game", default="daily_short", help="Game ID for ledger tracking")
    parser.add_argument("--target", default="", help="Target name for ledger tracking")
    parser.add_argument("--dry-run", action="store_true", help="Validate credentials and file without uploading")
    parser.add_argument("--no-poll", action="store_true", help="Do not poll status after upload")

    args = parser.parse_args()

    if args.refresh_token:
        try:
            refresh_access_token()
            print("✅ Access token refreshed successfully.")
        except Exception as e:
            print(f"❌ Failed to refresh token: {e}")
            sys.exit(1)
        return

    if args.verify:
        try:
            info = check_connection(silent=False)
            print(f"✅ Connection verified: @{info['username']} (Name: {info['display_name']})")
        except Exception as e:
            print(f"❌ Connection check failed: {e}")
            sys.exit(1)
        return

    if args.upload:
        video_path = os.path.abspath(args.upload)
        if not os.path.exists(video_path):
            print(f"❌ Video file does not exist: {video_path}")
            sys.exit(1)

        caption = args.caption or build_tiktok_caption(args.game, args.target)

        if args.dry_run:
            print(f"🔎 Dry run enabled. File: {video_path} ({os.path.getsize(video_path)} bytes)")
            print(f"Caption: {caption}")
            print(f"Privacy: {args.privacy}")
            return

        try:
            publish_id, res = upload_tiktok_now(
                video_path=video_path,
                caption=caption,
                privacy_level=args.privacy,
                title=args.title,
                poll_status=not args.no_poll
            )
            today_str = datetime.date.today().strftime("%Y-%m-%d")
            mark_as_posted(args.game, today_str, publish_id, target_name=args.target, post_data=res)
            print(f"🎉 Success! Publish ID: {publish_id}")
        except Exception as e:
            print(f"❌ TikTok upload failed: {e}")
            sys.exit(1)
        return

    parser.print_help()

if __name__ == "__main__":
    main()
