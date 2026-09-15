#!/usr/bin/env python3
"""
scripts/fetch_analytics.py

Unified Social Media Performance & Analytics Tool for FootyArcade / Playmaker.
Connects to:
1. YouTube (YouTube Data API v3 + YouTube Analytics API v2)
2. Instagram (Meta Graph API v21.0 - Account, Media & Reels Insights)
"""

import os
import sys
import json
import glob
import pickle
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRIVATE_DIR = os.path.join(BASE_DIR, "private")
YT_TOKEN_FILE = os.path.join(PRIVATE_DIR, "youtube_token.pickle")
YT_TOKEN_JSON_FILE = os.path.join(PRIVATE_DIR, "youtube_token.json")
IG_CONFIG_FILE = os.path.join(PRIVATE_DIR, "instagram_config.json")

YT_SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
    "https://www.googleapis.com/auth/youtube.readonly"
]

def find_client_secrets():
    env_secret = os.getenv("YOUTUBE_CLIENT_SECRETS")
    if env_secret and os.path.exists(env_secret):
        return env_secret
    candidates = (
        glob.glob(os.path.join(PRIVATE_DIR, "client_secret*.json")) +
        glob.glob(os.path.join(BASE_DIR, "client_secret*.json"))
    )
    return candidates[0] if candidates else None

def get_youtube_credentials(force_reauth=False):
    import google_auth_oauthlib.flow
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    credentials = None
    if not force_reauth:
        if os.path.exists(YT_TOKEN_JSON_FILE):
            try:
                with open(YT_TOKEN_JSON_FILE, "r", encoding="utf-8") as f:
                    credentials = Credentials.from_authorized_user_info(json.load(f))
            except Exception:
                pass
        if not credentials and os.path.exists(YT_TOKEN_FILE):
            try:
                with open(YT_TOKEN_FILE, "rb") as f:
                    credentials = pickle.load(f)
            except Exception:
                pass

    if credentials and not force_reauth:
        if credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except Exception:
                credentials = None

    if not credentials or force_reauth:
        client_secrets = find_client_secrets()
        if not client_secrets:
            print("❌ No client_secrets*.json found in private/ directory.")
            return None
        print(f"🔑 Initiating YouTube OAuth Flow with scopes: {YT_SCOPES}")
        flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
            client_secrets, YT_SCOPES
        )
        credentials = flow.run_local_server(port=0)
        with open(YT_TOKEN_FILE, "wb") as f:
            pickle.dump(credentials, f)
        with open(YT_TOKEN_JSON_FILE, "w", encoding="utf-8") as f:
            f.write(credentials.to_json())
        print("✅ New YouTube credentials successfully saved.")

    return credentials

def analyze_youtube(force_reauth=False):
    import googleapiclient.discovery
    creds = get_youtube_credentials(force_reauth)
    if not creds:
        return

    youtube = googleapiclient.discovery.build("youtube", "v3", credentials=creds)

    print("\n" + "="*70)
    print("📺 YOUTUBE CHANNEL & CONTENT PERFORMANCE")
    print("="*70)

    # 1. Channel Info
    ch_res = youtube.channels().list(mine=True, part="snippet,statistics,contentDetails").execute()
    if not ch_res.get("items"):
        print("No YouTube channel found.")
        return

    ch = ch_res["items"][0]
    snippet = ch["snippet"]
    stats = ch["statistics"]
    uploads_playlist = ch["contentDetails"]["relatedPlaylists"]["uploads"]

    print(f"Channel:     {snippet.get('title')} ({snippet.get('customUrl', 'N/A')})")
    print(f"Channel ID:  {ch['id']}")
    print(f"Subscribers: {stats.get('subscriberCount')}")
    print(f"Total Views: {int(stats.get('viewCount', 0)):,}")
    print(f"Total Vids:  {stats.get('videoCount')}")

    # 2. Fetch all videos
    videos = []
    page_token = None
    while True:
        pl_res = youtube.playlistItems().list(
            playlistId=uploads_playlist,
            part="snippet,contentDetails",
            maxResults=50,
            pageToken=page_token
        ).execute()
        v_ids = [it["contentDetails"]["videoId"] for it in pl_res.get("items", [])]
        if v_ids:
            v_res = youtube.videos().list(
                id=",".join(v_ids),
                part="snippet,statistics,contentDetails,status"
            ).execute()
            for item in v_res.get("items", []):
                videos.append({
                    "id": item["id"],
                    "title": item["snippet"]["title"],
                    "publishedAt": item["snippet"]["publishedAt"],
                    "views": int(item["statistics"].get("viewCount", 0)),
                    "likes": int(item["statistics"].get("likeCount", 0)),
                    "comments": int(item["statistics"].get("commentCount", 0)),
                })
        page_token = pl_res.get("nextPageToken")
        if not page_token:
            break

    # 3. Categorize & summarize
    def classify(title):
        t = title.lower()
        if "passport" in t: return "Club Passport"
        if "teammate chain" in t or "chain" in t: return "Teammate Chain"
        if "career path backwards" in t or "career" in t or "mystery player" in t: return "Career Path / Mystery Player"
        if "record transfers" in t or "transfer" in t: return "Record Transfers"
        if "scored the most goals" in t or "top scorers" in t or "scorers" in t: return "Top Scorers"
        if "transferred to" in t or "destination" in t: return "Transfer Destination"
        if "manchester city" in t or "bayern" in t or "super-sub" in t or "barella" in t: return "Star Player / Big Club Hook"
        return "Other / Trivia"

    cats = defaultdict(lambda: {"count": 0, "views": 0, "likes": 0})
    for v in videos:
        c = classify(v["title"])
        cats[c]["count"] += 1
        cats[c]["views"] += v["views"]
        cats[c]["likes"] += v["likes"]

    print("\n--- Performance by Format ---")
    print(f"{'Format':32s} | {'Count':5s} | {'Total Views':11s} | {'Avg Views':9s} | {'Likes':5s}")
    print("-" * 70)
    for c, data in sorted(cats.items(), key=lambda x: x[1]["views"], reverse=True):
        avg_v = data["views"] / data["count"] if data["count"] else 0
        print(f"{c:32s} | {data['count']:5d} | {data['views']:11,d} | {avg_v:9.1f} | {data['likes']:5d}")

    # Top 5 videos
    print("\n--- Top 5 Videos ---")
    for v in sorted(videos, key=lambda x: x["views"], reverse=True)[:5]:
        print(f"🔥 {v['views']:5,d} views | {v['likes']:2d} likes | {v['publishedAt'][:10]} | {v['title']}")

    # 4. Try YouTube Analytics API v2
    print("\n--- YouTube Analytics API (v2) Reports ---")
    try:
        yt_analytics = googleapiclient.discovery.build("youtubeAnalytics", "v2", credentials=creds)
        start_date = (datetime.now() - timedelta(days=60)).strftime("%Y-%m-%d")
        end_date = datetime.now().strftime("%Y-%m-%d")
        report = yt_analytics.reports().query(
            ids="channel==MINE",
            startDate=start_date,
            endDate=end_date,
            metrics="views,estimatedMinutesWatched,averageViewDuration,subscribersGained,subscribersLost",
            dimensions="day",
            sort="day"
        ).execute()
        rows = report.get("rows", [])
        total_mins = sum(r[2] for r in rows) if rows else 0
        print(f"✅ YouTube Analytics API connected successfully!")
        print(f"Report period: {start_date} to {end_date}")
        print(f"Total Watch Time: {total_mins:.1f} minutes")
    except Exception as e:
        print(f"ℹ️ YouTube Analytics API v2 requires scope approval: {e}")
        print("💡 Run with `--reauth-youtube` to grant YouTube Analytics permissions in your browser.")


def analyze_instagram():
    if not os.path.exists(IG_CONFIG_FILE):
        print("❌ private/instagram_config.json not found.")
        return

    with open(IG_CONFIG_FILE, "r") as f:
        ig_cfg = json.load(f)

    access_token = ig_cfg.get("access_token")
    ig_user_id = ig_cfg.get("ig_user_id")

    print("\n" + "="*70)
    print("📸 INSTAGRAM ACCOUNT & CONTENT PERFORMANCE")
    print("="*70)

    # 1. Profile Info
    url = f"https://graph.facebook.com/v21.0/{ig_user_id}?fields=username,name,biography,followers_count,follows_count,media_count&access_token={access_token}"
    try:
        req = urllib.request.urlopen(url)
        profile = json.loads(req.read().decode("utf-8"))
        print(f"Username:    @{profile.get('username')}")
        print(f"Name:        {profile.get('name')}")
        print(f"Followers:   {profile.get('followers_count')}")
        print(f"Following:   {profile.get('follows_count')}")
        print(f"Total Posts: {profile.get('media_count')}")
    except Exception as e:
        print("Error fetching Instagram profile:", e)
        return

    # 2. Fetch Media List
    media_url = f"https://graph.facebook.com/v21.0/{ig_user_id}/media?fields=id,caption,media_type,media_product_type,like_count,comments_count,timestamp,permalink&limit=60&access_token={access_token}"
    try:
        req = urllib.request.urlopen(media_url)
        media_items = json.loads(req.read().decode("utf-8")).get("data", [])
    except Exception as e:
        print("Error fetching Instagram media:", e)
        return

    total_likes = sum(m.get("like_count", 0) for m in media_items)
    total_comments = sum(m.get("comments_count", 0) for m in media_items)

    print(f"\n--- Recent Posts Analyzed: {len(media_items)} ---")
    print(f"Total Likes Received:    {total_likes}")
    print(f"Total Comments Received: {total_comments}")
    if media_items:
        print(f"Avg Likes per Post:      {total_likes / len(media_items):.2f}")

    # Top liked posts
    print("\n--- Top Engaged Posts ---")
    for m in sorted(media_items, key=lambda x: x.get("like_count", 0), reverse=True)[:5]:
        cap = (m.get("caption") or "").split("\n")[0][:45]
        print(f"❤️ {m.get('like_count', 0):2d} likes | {m.get('comments_count', 0):2d} comments | {m.get('timestamp')[:10]} | {cap}")

    print("\n💡 Note: For detailed reach/views/retention per Reel, add `instagram_manage_insights` to the Meta App.")


def main():
    parser = argparse.ArgumentParser(description="FootyArcade Social Media Analytics Tool")
    parser.add_argument("--youtube", action="store_true", help="Analyze YouTube performance")
    parser.add_argument("--instagram", action="store_true", help="Analyze Instagram performance")
    parser.add_argument("--reauth-youtube", action="store_true", help="Re-authenticate YouTube with upgraded scopes")
    args = parser.parse_args()

    run_all = not args.youtube and not args.instagram and not args.reauth_youtube

    if args.reauth_youtube or args.youtube or run_all:
        analyze_youtube(force_reauth=args.reauth_youtube)

    if args.instagram or run_all:
        analyze_instagram()

if __name__ == "__main__":
    main()
