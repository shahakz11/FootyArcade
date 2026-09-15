#!/usr/bin/env python3
import os
import sys
import glob
import json
import pickle
import argparse
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

# Scopes required for uploading YouTube videos and managing metadata
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl"
]

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIVATE_DIR = os.path.join(BASE_DIR, "private")
TOKEN_FILE = os.path.join(PRIVATE_DIR, "youtube_token.pickle")
TOKEN_JSON_FILE = os.path.join(PRIVATE_DIR, "youtube_token.json")

def find_client_secrets():
    """Finds client_secrets.json in Football or Manualz directory."""
    env_secret = os.getenv("YOUTUBE_CLIENT_SECRETS")
    if env_secret and os.path.exists(env_secret):
        return env_secret

    # Check Football/private or root
    candidates = (
        glob.glob(os.path.join(PRIVATE_DIR, "client_secret*.json")) +
        glob.glob(os.path.join(BASE_DIR, "client_secret*.json"))
    )
    if candidates:
        return candidates[0]
    return None

def get_authenticated_service():
    """Authenticates with YouTube API and returns a service object."""
    os.makedirs(PRIVATE_DIR, exist_ok=True)
    credentials = None

    if os.path.exists(TOKEN_JSON_FILE):
        try:
            with open(TOKEN_JSON_FILE, 'r', encoding='utf-8') as f:
                from google.oauth2.credentials import Credentials
                credentials = Credentials.from_authorized_user_info(json.load(f))
        except Exception as e:
            print(f"⚠️ Could not load youtube_token.json ({e}). Falling back to pickle...")

    if not credentials and os.path.exists(TOKEN_FILE):
        try:
            with open(TOKEN_FILE, 'rb') as token:
                credentials = pickle.load(token)
        except Exception as e:
            print(f"⚠️ Could not load token pickle ({e}). Re-authenticating...")

    if not credentials or not credentials.valid:
        refreshed = False
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
                refreshed = True
            except Exception as e:
                print(f"⚠️ Token refresh failed ({e}). Re-authenticating...")
                credentials = None

        if not refreshed:
            client_secrets = find_client_secrets()
            if not client_secrets:
                raise FileNotFoundError(
                    "❌ No client_secrets*.json found!\n"
                    "Please place your Google Cloud OAuth client secret in `private/client_secret.json`."
                )

            print(f"🔑 Using OAuth Client Secret: {client_secrets}")
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                client_secrets, SCOPES
            )
            credentials = flow.run_local_server(port=0)

        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(credentials, token)
        try:
            with open(TOKEN_JSON_FILE, 'w', encoding='utf-8') as f:
                f.write(credentials.to_json())
        except Exception:
            pass
        print(f"✅ Credentials saved to {TOKEN_FILE}")

    return googleapiclient.discovery.build("youtube", "v3", credentials=credentials)

def load_matchday_context_for_date(date_str=None):
    """Loads matchday context for the given date (default today) from the schedule ledger."""
    import datetime
    if not date_str:
        date_str = datetime.date.today().strftime("%Y-%m-%d")
    ledger_path = os.path.join(BASE_DIR, "data", "puzzle_schedule_ledger.json")
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                ledger = json.load(f)
                return ledger.get(date_str, {}).get("matchday_context")
        except Exception:
            pass
    return None

def build_default_metadata(game_id="top_transfers", target_name="", matchday_context=None, date_str=None):
    """Generates high-converting title, description, and tags for Shorts, with contextual matchday injection."""
    if matchday_context is None:
        matchday_context = load_matchday_context_for_date(date_str)

    hook_prefix = ""
    extra_desc = ""
    extra_tags = []

    if matchday_context:
        hook_prefix = f"{matchday_context.get('hook', '⚔️ MATCHDAY SPECIAL!')} "
        clash_name = matchday_context.get("clash_name", "")
        comp = matchday_context.get("competition", "")
        extra_desc = f"⚔️ Today's Matchday Special: {clash_name} ({comp})\n\n"
        for tag in matchday_context.get("hashtags", []):
            clean_tag = tag.lstrip("#")
            if clean_tag not in extra_tags:
                extra_tags.append(clean_tag)
        for club in [matchday_context.get("home_club"), matchday_context.get("away_club")]:
            if club and club not in extra_tags:
                extra_tags.append(club)

    game_titles = {
        "top_transfers": f"{hook_prefix}Can you guess {target_name or 'the club'}'s record transfers? ⚽ #Shorts",
        "transfer_destination": f"{hook_prefix}Guess the mystery player's career path backwards! ⚽ #Shorts",
        "player_chain": f"{hook_prefix}Can you complete this teammate chain? ⚽ #Shorts",
        "club_connect": f"{hook_prefix}Can you guess which team all of these players transferred to? ⚽ #Shorts",
        "top_scorers": f"{hook_prefix}Who scored the most goals in {target_name or 'this season'}? ⚽ #Shorts",
        "passport_fc": f"{hook_prefix}Can you complete {target_name or 'today'}'s club passport? ✈️ #Shorts"
    }

    title = game_titles.get(game_id, f"{hook_prefix}Daily Football Quiz Challenge! ⚽ #Shorts")

    description = (
        f"{extra_desc}"
        f"⚽ Playmaker — Daily Football Trivia & Transfer Arcade\n\n"
        f"Can you beat today's challenge? Comment your score below! 👇\n\n"
        f"🎮 Play today's free daily puzzle (no download, no sign up):\n"
        f"👉 https://playmaker.best/\n\n"
        f"#Shorts #football #soccer #footballquiz #soccerquiz #premierleague #realmadrid #championsleague #footballtrivia #playmaker"
    )

    tags = [
        "Shorts", "football", "soccer", "football quiz", "soccer quiz",
        "football trivia", "transfer quiz", "premier league", "champions league",
        "playmaker", "footy arcade", "trivia game"
    ]
    if extra_tags:
        tags = extra_tags + tags

    return title, description, tags

def get_channel_info(youtube=None):
    """Retrieves authenticated YouTube channel title and ID."""
    if youtube is None:
        youtube = get_authenticated_service()
    try:
        res = youtube.channels().list(mine=True, part="snippet").execute()
        items = res.get("items", [])
        if items:
            title = items[0]["snippet"]["title"]
            cid = items[0]["id"]
            return title, cid
        else:
            return None, None
    except Exception as e:
        print(f"⚠️ Could not fetch channel info: {e}")
        return None, None

def is_youtube_already_uploaded(game_id, target_name="", date_str=None, youtube=None):
    """
    Checks YouTube channel recent uploads via API.
    Returns (already_uploaded: bool, url_or_msg: str).
    """
    import datetime
    if not date_str:
        date_str = datetime.date.today().strftime("%Y-%m-%d")
    
    expected_title, _, _ = build_default_metadata(game_id, target_name)
    clean_expected = expected_title.replace("#Shorts", "").replace("#shorts", "").strip().lower()

    if youtube is None:
        try:
            youtube = get_authenticated_service()
        except Exception:
            return False, ""

    try:
        res = youtube.channels().list(mine=True, part="contentDetails").execute()
        items = res.get("items", [])
        if not items:
            return False, ""
        uploads_id = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        vids = youtube.playlistItems().list(playlistId=uploads_id, part="snippet", maxResults=20).execute().get("items", [])
        
        # Game generic title prefixes for matching even if target name varies
        game_patterns = {
            "top_transfers": "record transfers",
            "transfer_destination": "career path backwards",
            "player_chain": "teammate chain",
            "club_connect": "which team all of these players transferred to",
            "top_scorers": "scored the most goals",
            "passport_fc": "club passport"
        }
        pattern = game_patterns.get(game_id, "").lower()

        for v in vids:
            pub_date = v["snippet"].get("publishedAt", "")[:10]
            vtitle = v["snippet"].get("title", "")
            clean_vtitle = vtitle.replace("#Shorts", "").replace("#shorts", "").strip().lower()
            vid_id = v["snippet"]["resourceId"]["videoId"]
            shorts_url = f"https://youtube.com/shorts/{vid_id}"

            # If published on target date
            if pub_date == date_str:
                # 1. Exact or near match
                if clean_vtitle == clean_expected:
                    return True, shorts_url
                # 2. Target name in title
                if target_name and target_name.lower() in clean_vtitle:
                    return True, shorts_url
                # 3. Game pattern match (each game only posts once per day)
                if pattern and pattern in clean_vtitle:
                    return True, shorts_url
    except Exception as e:
        print(f"⚠️ YouTube deduplication check warning: {e}")

    return False, ""

def upload_short(video_path, title=None, description=None, tags=None, category="17", privacy_status="public", publish_at=None):
    """
    Uploads a vertical Short to YouTube.
    Category 17 = Sports.
    publish_at: ISO 8601 UTC formatted datetime string (e.g. '2026-09-10T15:00:00Z')
    Note: privacyStatus MUST be 'private' if publishAt is set.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    youtube = get_authenticated_service()
    channel_title, channel_id = get_channel_info(youtube)
    if not channel_id:
        raise RuntimeError(
            "No YouTube channel has been created for this Google Account yet! (Error: youtubeSignupRequired)\n\n"
            "👉 QUICK FIX:\n"
            "1. Open https://www.youtube.com/create_channel in your browser while signed in as Playmaker.\n"
            "2. Click 'Create Channel'.\n"
            "3. Delete the cached token: rm private/youtube_token.pickle\n"
            "4. Re-run UploadTodayShorts.command.\n"
        )

    print(f"📺 Channel: {channel_title} (ID: {channel_id})")

    clean_title = (title or "Daily Football Quiz ⚽ #Shorts").replace("<", "").replace(">", "").strip()
    if "#Shorts" not in clean_title and "#shorts" not in clean_title:
        clean_title = f"{clean_title[:85]} #Shorts"
    if len(clean_title) > 100:
        clean_title = clean_title[:97].rstrip() + "..."

    clean_description = (description or "").replace("<", "").replace(">", "")
    if len(clean_description) > 5000:
        clean_description = clean_description[:4990].rstrip() + "\n..."

    effective_privacy = "private" if publish_at else privacy_status
    body = {
        "snippet": {
            "title": clean_title,
            "description": clean_description,
            "tags": tags or ["Shorts", "football", "soccer"],
            "categoryId": category
        },
        "status": {
            "privacyStatus": effective_privacy,
            "selfDeclaredMadeForKids": False
        }
    }
    if publish_at:
        body["status"]["publishAt"] = publish_at

    print(f"\n🚀 Uploading Short to YouTube...")
    print(f"🎬 Title: {clean_title}")
    if publish_at:
        print(f"⏰ Scheduled for: {publish_at} (Status: {effective_privacy})")
    else:
        print(f"🔒 Privacy: {effective_privacy}")

    media = MediaFileUpload(video_path, chunksize=1024*1024*2, resumable=True)
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"⏳ Upload progress: {pct}%")

    video_id = response.get("id")
    shorts_url = f"https://youtube.com/shorts/{video_id}"
    print(f"\n🎉 Success! Video uploaded successfully!")
    print(f"🔗 YouTube Short URL: {shorts_url}\n")
    return video_id, shorts_url

def main():
    parser = argparse.ArgumentParser(description="Upload Daily Playmaker Video to YouTube Shorts")
    parser.add_argument("--file", help="Path to video file to upload")
    parser.add_argument("--game", default="top_transfers", help="Game ID for auto metadata")
    parser.add_argument("--target", default="", help="Target club, player, or season name")
    parser.add_argument("--title", help="Custom video title (will append #Shorts if omitted)")
    parser.add_argument("--privacy", default="public", choices=["public", "private", "unlisted"])
    parser.add_argument("--publish-at", help="Scheduled publish time in ISO 8601 UTC format (e.g. 2026-09-10T16:00:00Z)")
    parser.add_argument("--auth-only", action="store_true", help="Authorize OAuth credentials and exit")
    parser.add_argument("--channel", action="store_true", help="Show currently authenticated YouTube channel info and exit")

    args = parser.parse_args()

    if args.auth_only or args.channel:
        title, cid = get_channel_info()
        print(f"✅ Connected to YouTube Channel: {title} (ID: {cid})")
        return

    if not args.file:
        print("Error: --file argument is required unless using --auth-only or --channel.")
        sys.exit(1)

    default_title, default_desc, default_tags = build_default_metadata(args.game, args.target)
    title = args.title or default_title
    upload_short(
        video_path=args.file,
        title=title,
        description=default_desc,
        tags=default_tags,
        privacy_status=args.privacy,
        publish_at=args.publish_at
    )

if __name__ == "__main__":
    main()
