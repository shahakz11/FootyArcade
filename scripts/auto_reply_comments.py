#!/usr/bin/env python3
"""
scripts/auto_reply_comments.py

Unified Social Media Comment Auto-Reply Engine for Playmaker / FootyArcade.
Supports both YouTube Shorts & Instagram Reels comments.
Monitors recent videos, verifies if comments contain a valid player name from that puzzle's
answer pool (supporting nicknames, full names, surnames, and typos), and posts an engaging,
personalized reply driving traffic to playmaker.best.

Usage:
  python3 scripts/auto_reply_comments.py            # Runs both YouTube & Instagram
  python3 scripts/auto_reply_comments.py --dry-run  # Previews matches without posting
  python3 scripts/auto_reply_comments.py --youtube  # YouTube only
  python3 scripts/auto_reply_comments.py --instagram# Instagram only
  python3 scripts/auto_reply_comments.py --daemon   # Runs continuously in background loop
"""

import os
import sys
import re
import time
import glob
import json
import random
import unicodedata
import argparse
import urllib.request
import urllib.parse
import urllib.error
import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

PRIVATE_DIR = os.path.join(BASE_DIR, "private")
IG_CONFIG_FILE = os.path.join(PRIVATE_DIR, "instagram_config.json")
IG_LEDGER_FILE = os.path.join(PRIVATE_DIR, "instagram_replies_ledger.json")

YT_TOKEN_JSON_FILE = os.path.join(PRIVATE_DIR, "youtube_token.json")
YT_TOKEN_PICKLE_FILE = os.path.join(PRIVATE_DIR, "youtube_token.pickle")
YT_LEDGER_FILE = os.path.join(PRIVATE_DIR, "youtube_replies_ledger.json")

# ── Nickname, Typo & Alias Dictionary ─────────────────────────────────────────
NICKNAMES = {
    # French players
    "titi": "Thierry Henry",
    "henry": "Thierry Henry",
    "grizou": "Antoine Griezmann",
    "griezmann": "Antoine Griezmann",
    "kounde": "Jules Koundé",
    "koundé": "Jules Koundé",
    "umtiti": "Samuel Umtiti",
    "dembele": "Ousmane Dembélé",
    "dembélé": "Ousmane Dembélé",
    "abidal": "Éric Abidal",
    "thuram": "Lilian Thuram",
    "gusto": "Malo Gusto",
    "malo gusto": "Malo Gusto",
    "kante": "N'Golo Kanté",
    "kanta": "N'Golo Kanté",
    "ngolo kante": "N'Golo Kanté",
    "ngolo ngolo kante": "N'Golo Kanté",
    "giroud": "Olivier Giroud",
    "oliver giroud": "Olivier Giroud",
    "anelka": "Nicolas Anelka",
    "malouda": "Florent Malouda",
    "desailly": "Marcel Desailly",
    "desaily": "Marcel Desailly",
    "leboeuf": "Frank Leboeuf",
    "zouma": "Kurt Zouma",
    "nkunku": "Christopher Nkunku",
    "mbappe": "Kylian Mbappé",
    "benzema": "Karim Benzema",
    "kb9": "Karim Benzema",
    "zidane": "Zinedine Zidane",
    "zizou": "Zinedine Zidane",

    # Superstars & Multi-Club Legends
    "cr7": "Cristiano Ronaldo",
    "cristiano": "Cristiano Ronaldo",
    "el fideo": "Ángel Di María",
    "di maria": "Ángel Di María",
    "dimaria": "Ángel Di María",
    "fenomeno": "Ronaldo",
    "r9": "Ronaldo",
    "la pulga": "Lionel Messi",
    "messi": "Lionel Messi",
    "el pipita": "Gonzalo Higuaín",
    "pipita": "Gonzalo Higuaín",
    "higuain": "Gonzalo Higuaín",
    "kun": "Sergio Agüero",
    "aguero": "Sergio Agüero",
    "kaka": "Kaká",
    "morata": "Álvaro Morata",
    "cannavaro": "Fabio Cannavaro",
    "seedorf": "Clarence Seedorf",
    "davids": "Edgar Davids",
    "ibrahimovic": "Zlatan Ibrahimović",
    "zlatan": "Zlatan Ibrahimović",
    "valencia": "Antonio Valencia",
    "antonio valencia": "Antonio Valencia",
    "remy": "Loïc Rémy",
    "loic remy": "Loïc Rémy",
    "conde": "Jules Koundé",
    "cristanval": "Philippe Christanval",
    "philipe cristanval": "Philippe Christanval",
    "philippe cristanval": "Philippe Christanval",

    # Portugal / Benfica / Croatia / Other
    "felix": "João Félix",
    "joao felix": "João Félix",
    "semedo": "Nélson Semedo",
    "grimaldo": "Alejandro Grimaldo",
    "koeman": "Ronald Koeman",
    "modric": "Luka Modrić",
    "mandzukic": "Mario Mandžukić",
    "mario mandzukic": "Mario Mandžukić",
    "rebic": "Ante Rebić",
    "boban": "Zvonimir Boban",
    "simic": "Dario Šimić",
    "pasalic": "Mario Pašalić",
    "bellingham": "Jude Bellingham",
    "haaland": "Erling Haaland"
}

# ── Dynamic Rotating Reply Templates ──────────────────────────────────────────
REPLY_TEMPLATES = [
    "🎯 Spot on with {player}! Elite ball knowledge 👏 Try today's 6 daily puzzles at playmaker.best (link in bio) ⚽",
    "🔥 {player}! That's 100% verified! 🧠 Can you beat today's full challenge on playmaker.best? (link in bio) 🏆",
    "🧠 Big brain ball knowledge! {player} is correct ⚽ Play today's daily football arcade at playmaker.best (link in bio)!",
    "👏 Quality shout with {player}! Spot on. Test your knowledge with 6 free daily games on playmaker.best 🎮",
    "🎯 Verified! {player} is in the official answer pool ⚽ Beat today's puzzle at playmaker.best (link in bio)!"
]

def normalize_text(text):
    """Strips diacritics, lowercases, and removes punctuation."""
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", str(text)).encode("ASCII", "ignore").decode("utf-8")
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())

def load_ledger(ledger_path):
    if os.path.exists(ledger_path):
        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_ledger(ledger_path, ledger):
    os.makedirs(os.path.dirname(ledger_path), exist_ok=True)
    with open(ledger_path, "w", encoding="utf-8") as f:
        json.dump(ledger, f, indent=2, ensure_ascii=False)

# ── Answer Pool Resolvers ─────────────────────────────────────────────────────

def get_all_active_daily_answer_pools():
    """Extracts answer pools from all daily CSVs for broad matching."""
    pools = []
    
    # 1. Passport FC
    p_csv = os.path.join(BASE_DIR, "daily_passport_fc_games.csv")
    if os.path.exists(p_csv):
        try:
            import pandas as pd
            df = pd.read_csv(p_csv)
            for _, row in df.iterrows():
                valid = json.loads(row.get("valid_players", "[]"))
                pools.append({
                    "type": "passport_fc",
                    "entity_1": row.get("club"),
                    "entity_2": row.get("nationality"),
                    "players": valid
                })
        except Exception:
            pass

    # 2. Player Chain
    c_csv = os.path.join(BASE_DIR, "daily_player_chain_games.csv")
    if os.path.exists(c_csv):
        try:
            import pandas as pd
            df = pd.read_csv(c_csv)
            for _, row in df.iterrows():
                valid = json.loads(row.get("valid_players", "[]"))
                clubs = json.loads(row.get("active_clubs", "[]"))
                pools.append({
                    "type": "player_chain",
                    "entity_1": clubs[0] if len(clubs) > 0 else "",
                    "entity_2": clubs[1] if len(clubs) > 1 else "",
                    "players": valid
                })
        except Exception:
            pass

    return pools

def extract_pool_from_caption(caption_or_title, all_pools=None):
    """
    Parses a video title or caption to extract (Club + Nationality) or (Club A + Club B).
    Examples:
    - 'Name ONE France player for Chelsea (No one else will say)...' -> (Chelsea, France)
    - 'Name ONE player for Barcelona & Benfica...' -> (Barcelona, Benfica)
    - 'Name A player who played for Real Madrid & Juventus' -> (Real Madrid, Juventus)
    """
    if not caption_or_title:
        return None

    if all_pools is None:
        all_pools = get_all_active_daily_answer_pools()

    norm_text = normalize_text(caption_or_title)

    # Pattern 1: Country + Club ("Name ONE France player to play for Chelsea" / "France player for Chelsea")
    m_country = re.search(r"name one (\w+(?:\s+\w+)?) player (?:to play for|for) (.+?)(?: that| \n|\.|\(|$)", caption_or_title, re.IGNORECASE)
    if m_country:
        nat = m_country.group(1).strip()
        club = m_country.group(2).strip()
        norm_nat = normalize_text(nat)
        norm_club = normalize_text(club)
        for pool in all_pools:
            if pool.get("type") == "passport_fc":
                p_club = normalize_text(pool.get("entity_1", ""))
                p_nat = normalize_text(pool.get("entity_2", ""))
                if (norm_nat in p_nat or p_nat in norm_nat) and (norm_club in p_club or p_club in norm_club):
                    return pool["players"]

    # Pattern 2: Club A + Club B ("played for BOTH Barcelona and Benfica" / "played for Real Madrid & Juventus")
    m_clubs = re.search(r"(?:played for both|for|played for) (.+?) (?:and|&|\+) (.+?)(?: that| \n|\.|\(|$)", caption_or_title, re.IGNORECASE)
    if m_clubs:
        c1 = normalize_text(m_clubs.group(1).strip())
        c2 = normalize_text(m_clubs.group(2).strip())
        for pool in all_pools:
            p_c1 = normalize_text(pool.get("entity_1", ""))
            p_c2 = normalize_text(pool.get("entity_2", ""))
            if (c1 in p_c1 and c2 in p_c2) or (c1 in p_c2 and c2 in p_c1):
                return pool["players"]

    return None

def match_comment_to_pool(comment_text, valid_players):
    """
    Checks if comment_text contains a valid player name, nickname, or last name.
    Returns the canonical player name if matched, else None.
    """
    if not comment_text or not valid_players:
        return None

    norm_comment = normalize_text(comment_text)

    # 1. Nicknames and typo dictionary check
    for nick, canonical in NICKNAMES.items():
        if re.search(r"\b" + re.escape(nick) + r"\b", norm_comment):
            norm_canonical = normalize_text(canonical)
            for p in valid_players:
                norm_p = normalize_text(p)
                if norm_canonical == norm_p or re.search(r"\b" + re.escape(norm_canonical) + r"\b", norm_p):
                    return p

    # 2. Direct player matching - sort by descending length to prioritize full names before short surnames
    sorted_players = sorted(valid_players, key=lambda x: len(x), reverse=True)
    for p in sorted_players:
        norm_p = normalize_text(p)
        parts = norm_p.split()

        # A. Full name match with word boundaries
        if re.search(r"\b" + re.escape(norm_p) + r"\b", norm_comment):
            return p

        # B. Multi-word parts (e.g. 'Di Maria', 'De Jong', 'Van Dijk')
        if len(parts) >= 2:
            compound_last = " ".join(parts[-2:])
            if len(compound_last) >= 5:
                if re.search(r"\b" + re.escape(compound_last) + r"\b", norm_comment):
                    return p

        # C. Last name match (min 4 characters to avoid false positives)
        if len(parts) > 1:
            last = parts[-1]
            if len(last) >= 4:
                # Word boundary match
                if re.search(r"\b" + re.escape(last) + r"\b", norm_comment):
                    return p

        # D. Single-name superstars (e.g. 'Ronaldo', 'Neymar', 'Casemiro', 'Deco')
        elif len(norm_p) >= 4:
            if re.search(r"\b" + re.escape(norm_p) + r"\b", norm_comment):
                return p

    return None

# ── YouTube Engine ────────────────────────────────────────────────────────────

def get_youtube_service():
    """Builds authenticated YouTube Data API client."""
    from google.oauth2.credentials import Credentials
    import googleapiclient.discovery

    creds = None
    if os.path.exists(YT_TOKEN_JSON_FILE):
        try:
            with open(YT_TOKEN_JSON_FILE, "r", encoding="utf-8") as f:
                creds = Credentials.from_authorized_user_info(json.load(f))
        except Exception:
            pass

    if not creds and os.path.exists(YT_TOKEN_PICKLE_FILE):
        try:
            import pickle
            with open(YT_TOKEN_PICKLE_FILE, "rb") as f:
                creds = pickle.load(f)
        except Exception:
            pass

    if not creds:
        return None

    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)

def run_youtube_auto_replies(dry_run=False, limit=20):
    """Scans recent YouTube video comment threads and posts auto-replies."""
    youtube = get_youtube_service()
    if not youtube:
        print("⚠️ YouTube credentials not found or unauthenticated. Skipping YouTube auto-replies.")
        return

    ledger = load_ledger(YT_LEDGER_FILE)
    all_pools = get_all_active_daily_answer_pools()

    try:
        ch_resp = youtube.channels().list(mine=True, part="id,snippet").execute()
        channel_id = ch_resp["items"][0]["id"]
        channel_title = ch_resp["items"][0]["snippet"]["title"]
    except Exception as e:
        print(f"❌ YouTube channel lookup failed: {e}")
        return

    print(f"\n📺 Scanning YouTube comments on channel '{channel_title}'...")

    try:
        ct_resp = youtube.commentThreads().list(
            allThreadsRelatedToChannelId=channel_id,
            part="snippet,replies",
            maxResults=min(limit * 3, 100),
            order="time"
        ).execute()
        threads = ct_resp.get("items", [])
    except Exception as e:
        print(f"❌ Failed to fetch YouTube comment threads: {e}")
        return

    # Cache video titles
    vid_ids = list(set(t["snippet"]["videoId"] for t in threads if "videoId" in t.get("snippet", {})))
    vid_titles = {}
    if vid_ids:
        try:
            v_resp = youtube.videos().list(id=",".join(vid_ids[:50]), part="snippet").execute()
            vid_titles = {v["id"]: v["snippet"]["title"] for v in v_resp.get("items", [])}
        except Exception:
            pass

    total_checked = 0
    total_matched = 0
    total_replied = 0

    for thread in threads:
        total_checked += 1
        t_id = thread["id"]
        t_snippet = thread.get("snippet", {})
        vid_id = t_snippet.get("videoId")
        v_title = vid_titles.get(vid_id, "")

        top_comment = t_snippet.get("topLevelComment", {}).get("snippet", {})
        c_id = thread.get("snippet", {}).get("topLevelComment", {}).get("id", t_id)
        author = top_comment.get("authorDisplayName", "Unknown")
        author_ch_id = top_comment.get("authorChannelId", {}).get("value")
        text = top_comment.get("textOriginal") or top_comment.get("textDisplay", "")

        # Ignore comments from our own channel
        if author_ch_id == channel_id or author == channel_title:
            continue

        # Ignore already replied comments
        if c_id in ledger:
            continue

        # Check if we already replied directly in the thread
        already_replied = False
        if "replies" in thread:
            for rep in thread["replies"].get("comments", []):
                rep_author_id = rep.get("snippet", {}).get("authorChannelId", {}).get("value")
                if rep_author_id == channel_id:
                    already_replied = True
                    break
        if already_replied:
            ledger[c_id] = {"status": "already_replied_manually"}
            save_ledger(YT_LEDGER_FILE, ledger)
            continue

        # Extract answer pool
        pool = extract_pool_from_caption(v_title, all_pools)
        if not pool:
            merged = []
            for p in all_pools:
                merged.extend(p.get("players", []))
            pool = list(set(merged))

        matched_player = match_comment_to_pool(text, pool)
        if matched_player:
            total_matched += 1
            template = random.choice(REPLY_TEMPLATES)
            reply_msg = template.format(player=matched_player)

            print(f"\n✨ [YOUTUBE MATCH FOUND!]")
            print(f"  • Video:    {v_title[:45]}...")
            print(f"  • User:     @{author}")
            print(f"  • Comment:  \"{text}\"")
            print(f"  • Answer:   ✅ {matched_player}")
            print(f"  • Reply:    \"{reply_msg}\"")

            if dry_run:
                print("  [DRY-RUN] Reply skipped.")
            else:
                try:
                    body = {
                        "snippet": {
                            "parentId": c_id,
                            "textOriginal": reply_msg
                        }
                    }
                    rep_res = youtube.comments().insert(part="snippet", body=body).execute()
                    reply_id = rep_res.get("id")
                    print(f"  🚀 YouTube reply posted! (ID: {reply_id})")

                    ledger[c_id] = {
                        "video_id": vid_id,
                        "video_title": v_title,
                        "username": author,
                        "comment_text": text,
                        "matched_player": matched_player,
                        "reply_text": reply_msg,
                        "reply_id": reply_id,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                    save_ledger(YT_LEDGER_FILE, ledger)
                    total_replied += 1
                except Exception as e:
                    print(f"  ❌ Failed to post YouTube reply: {e}")

    print(f"\n📊 --- [YOUTUBE AUTO-REPLY SUMMARY] ---")
    print(f"Comments Inspected: {total_checked}")
    print(f"Correct Answers:    {total_matched}")
    print(f"Replies Sent:       {total_replied} {'(Dry-run mode)' if dry_run else ''}")
    print(f"---------------------------------------\n")

# ── Instagram Engine ──────────────────────────────────────────────────────────

def run_instagram_auto_replies(dry_run=False, limit=15, my_username="playmaker.best1"):
    """Scans recent Instagram Reels and posts auto-replies."""
    if not os.path.exists(IG_CONFIG_FILE):
        print("⚠️ private/instagram_config.json not found. Skipping Instagram.")
        return

    with open(IG_CONFIG_FILE, "r", encoding="utf-8") as f:
        config = json.load(f)

    access_token = config["access_token"]
    ig_user_id = config.get("ig_user_id")

    ledger = load_ledger(IG_LEDGER_FILE)
    all_pools = get_all_active_daily_answer_pools()

    print(f"\n📸 Scanning recent {limit} Instagram Reels for comments...")

    media_url = f"https://graph.facebook.com/v21.0/{ig_user_id}/media?fields=id,caption,media_product_type,comments_count,permalink,timestamp&limit={limit}&access_token={access_token}"
    try:
        req = urllib.request.Request(media_url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            media_items = json.loads(resp.read().decode("utf-8")).get("data", [])
    except Exception as e:
        print(f"❌ Failed to fetch Instagram media list: {e}")
        return

    total_checked = 0
    total_matched = 0
    total_replied = 0

    for m in media_items:
        if m.get("comments_count", 0) <= 0:
            continue

        m_id = m["id"]
        caption = m.get("caption", "")
        comm_url = f"https://graph.facebook.com/v21.0/{m_id}/comments?fields=id,text,username,timestamp,from,replies{{id,username,text,from}}&limit=50&access_token={access_token}"
        try:
            comm_req = urllib.request.Request(comm_url)
            with urllib.request.urlopen(comm_req, timeout=10) as comm_resp:
                comments = json.loads(comm_resp.read().decode("utf-8")).get("data", [])
        except Exception:
            comments = []

        pool = extract_pool_from_caption(caption, all_pools)
        if not pool:
            merged = []
            for p in all_pools:
                merged.extend(p.get("players", []))
            pool = list(set(merged))

        for c in comments:
            total_checked += 1
            c_id = c.get("id")
            c_user = c.get("username", "")
            c_text = c.get("text", "")

            if c_user and c_user.lower() == my_username.lower():
                continue

            if c_id in ledger:
                continue

            # Live API check: verify if we already replied to this comment on Instagram
            replies_data = c.get("replies", {}).get("data", [])
            already_replied = any(
                rep.get("username", "").lower() == my_username.lower()
                or rep.get("from", {}).get("id") == ig_user_id
                for rep in replies_data
            )
            if already_replied:
                if not dry_run:
                    ledger[c_id] = {"status": "already_replied_live"}
                    save_ledger(IG_LEDGER_FILE, ledger)
                continue

            matched_player = match_comment_to_pool(c_text, pool)
            if matched_player:
                total_matched += 1
                template = random.choice(REPLY_TEMPLATES)
                reply_msg = template.format(player=matched_player)

                print(f"\n✨ [INSTAGRAM MATCH FOUND!]")
                print(f"  • Post:     {(caption or '').splitlines()[0][:45]}...")
                print(f"  • User:     @{c_user}")
                print(f"  • Comment:  \"{c_text}\"")
                print(f"  • Answer:   ✅ {matched_player}")
                print(f"  • Reply:    \"{reply_msg}\"")

                if dry_run:
                    print("  [DRY-RUN] Reply skipped.")
                else:
                    try:
                        url = f"https://graph.facebook.com/v21.0/{c_id}/replies"
                        data = urllib.parse.urlencode({
                            "message": reply_msg,
                            "access_token": access_token
                        }).encode("utf-8")
                        post_req = urllib.request.Request(url, data=data, method="POST")
                        with urllib.request.urlopen(post_req, timeout=10) as post_resp:
                            res = json.loads(post_resp.read().decode("utf-8"))
                        
                        reply_id = res.get("id")
                        print(f"  🚀 Instagram reply posted! (ID: {reply_id})")

                        ledger[c_id] = {
                            "media_id": m_id,
                            "username": c_user,
                            "comment_text": c_text,
                            "matched_player": matched_player,
                            "reply_text": reply_msg,
                            "reply_id": reply_id,
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                        save_ledger(IG_LEDGER_FILE, ledger)
                        total_replied += 1
                    except urllib.error.HTTPError as e:
                        print(f"  ❌ Failed to post Instagram reply (HTTP {e.code}): {e.read().decode('utf-8')}")
                    except Exception as e:
                        print(f"  ❌ Error posting Instagram reply: {e}")

    print(f"\n📊 --- [INSTAGRAM AUTO-REPLY SUMMARY] ---")
    print(f"Comments Inspected: {total_checked}")
    print(f"Correct Answers:    {total_matched}")
    print(f"Replies Sent:       {total_replied} {'(Dry-run mode)' if dry_run else ''}")
    print(f"-----------------------------------------\n")

# ── Main Entrypoint ───────────────────────────────────────────────────────────

def run_all_replies(dry_run=False, limit=20, platform="all"):
    if platform in ("all", "youtube"):
        run_youtube_auto_replies(dry_run=dry_run, limit=limit)
    if platform in ("all", "instagram"):
        run_instagram_auto_replies(dry_run=dry_run, limit=limit)

def main():
    parser = argparse.ArgumentParser(description="Playmaker Multi-Platform Comment Auto-Reply Engine (YouTube & Instagram)")
    parser.add_argument("--dry-run", action="store_true", help="Preview matches and replies without posting")
    parser.add_argument("--youtube", action="store_true", help="Run on YouTube only")
    parser.add_argument("--instagram", action="store_true", help="Run on Instagram only")
    parser.add_argument("--limit", type=int, default=20, help="Number of recent posts/videos to scan (default 20)")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background daemon loop")
    parser.add_argument("--interval", type=int, default=300, help="Interval in seconds between scans in daemon mode (default 300s / 5m)")
    args = parser.parse_args()

    platform = "all"
    if args.youtube and not args.instagram:
        platform = "youtube"
    elif args.instagram and not args.youtube:
        platform = "instagram"

    if args.daemon:
        print(f"🤖 Starting Multi-Platform Auto-Reply Daemon ({platform.upper()}, Polling every {args.interval}s)...")
        while True:
            try:
                run_all_replies(dry_run=args.dry_run, limit=args.limit, platform=platform)
            except Exception as e:
                print(f"⚠️ Error during scan cycle: {e}")
            time.sleep(args.interval)
    else:
        run_all_replies(dry_run=args.dry_run, limit=args.limit, platform=platform)

if __name__ == "__main__":
    main()
