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
import tempfile
import threading

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
    "haaland": "Erling Haaland",

    # Modern Stars, Nicknames & Common Aliases
    "vini": "Vinicius Junior",
    "vini jr": "Vinicius Junior",
    "vinicius": "Vinicius Junior",
    "vinicius jr": "Vinicius Junior",
    "kdb": "Kevin De Bruyne",
    "debruyne": "Kevin De Bruyne",
    "de bruyne": "Kevin De Bruyne",
    "vvd": "Virgil van Dijk",
    "van dijk": "Virgil van Dijk",
    "taa": "Trent Alexander-Arnold",
    "starboy": "Bukayo Saka",
    "saka": "Bukayo Saka",
    "foden": "Phil Foden",
    "lewa": "Robert Lewandowski",
    "lewandowski": "Robert Lewandowski",
    "sonny": "Heung-min Son",
    "son": "Heung-min Son",
    "bambi": "Jamal Musiala",
    "musiala": "Jamal Musiala",
    "wirtz": "Florian Wirtz",
    "pedri": "Pedri",
    "gavi": "Gavi",
    "rodri": "Rodri",
    "spider": "Julián Álvarez",
    "la arana": "Julián Álvarez",
    "julian alvarez": "Julián Álvarez",
    "alvarez": "Julián Álvarez",
    "valverde": "Federico Valverde",
    "el pajarito": "Federico Valverde",
    "camavinga": "Eduardo Camavinga",
    "cama": "Eduardo Camavinga",
    "tchouameni": "Aurélien Tchouaméni",
    "arda": "Arda Güler",
    "guler": "Arda Güler",
    "lamine": "Lamine Yamal",
    "yamal": "Lamine Yamal",
    "minjae": "Min-jae Kim",
    "min jae": "Min-jae Kim",
    "eze": "Eberechi Eze",
    "emre can": "Emre Can",
    "nico paz": "Nico Paz",
    "auba": "Pierre-Emerick Aubameyang",
    "aubameyang": "Pierre-Emerick Aubameyang",
    "choupo": "Eric Maxim Choupo-Moting",
    "choupo moting": "Eric Maxim Choupo-Moting"
}

# ── Dynamic Rotating Reply Templates ──────────────────────────────────────────
REPLY_TEMPLATES = [
    "🎯 Spot on with {player}! Elite ball knowledge 👏 Try today's 6 daily puzzles at playmaker.best (link in bio) ⚽",
    "🔥 {player}! That's 100% verified! 🧠 Can you beat today's full challenge on playmaker.best? (link in bio) 🏆",
    "🧠 Big brain ball knowledge! {player} is correct ⚽ Play today's daily football arcade at playmaker.best (link in bio)!",
    "👏 Quality shout with {player}! Spot on. Test your knowledge with 6 free daily games on playmaker.best 🎮",
    "🎯 Verified! {player} is in the official answer pool ⚽ Beat today's puzzle at playmaker.best (link in bio)!"
]

PLAYED_WITH_REPLY_TEMPLATES = [
    "🎯 Spot on! It's {player}! Elite ball knowledge 👏 Try today's 6 daily puzzles at playmaker.best (link in bio) ⚽",
    "🔥 Boom! {player} is 100% correct! 🧠 Can you beat today's full challenge on playmaker.best? (link in bio) 🏆",
    "🧠 Big brain shout! It is indeed {player} ⚽ Test your ball knowledge across 6 daily games at playmaker.best (link in bio)!",
    "👏 Quality guess with {player}! Nailed it. Play today's full daily arcade at playmaker.best (link in bio) 🎮",
    "🎯 Verified! {player} is the mystery footballer! ⚽ Can you solve today's live puzzle at playmaker.best (link in bio)!"
]

LATIN_TRANSLITERATION = {
    "Ø": "O",
    "ø": "o",
    "ß": "ss",
    "Æ": "AE",
    "æ": "ae",
    "Ł": "L",
    "ł": "l",
    "Đ": "D",
    "đ": "d",
}

def normalize_text(text):
    """Strips diacritics, lowercases, and removes punctuation."""
    if not text:
        return ""
    text = str(text)
    for k, v in LATIN_TRANSLITERATION.items():
        text = text.replace(k, v)
    text = unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8")
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

_LEDGER_LOCK = threading.Lock()

def save_ledger(ledger_path, ledger):
    """Atomically saves the reply ledger using a unique temp file and thread lock."""
    with _LEDGER_LOCK:
        dir_name = os.path.dirname(ledger_path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        tf = tempfile.NamedTemporaryFile("w", dir=dir_name or None, delete=False, encoding="utf-8")
        tmp_path = tf.name
        try:
            json.dump(ledger, tf, indent=2, ensure_ascii=False)
            tf.flush()
            os.fsync(tf.fileno())
            tf.close()
            os.replace(tmp_path, ledger_path)
        except Exception:
            tf.close()
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except OSError:
                    pass
            raise

# ── Answer Pool Resolvers ─────────────────────────────────────────────────────

def load_played_with_pools(csv_path=None):
    """
    Ingests daily_played_with_games.csv and returns structured answer pools:
    [
        {
            "type": "played_with",
            "game_day": int,
            "mystery_player": str,
            "players": [mystery_player],
            "teammates": [str, ...]
        },
        ...
    ]
    """
    if csv_path is None:
        csv_path = os.path.join(BASE_DIR, "daily_played_with_games.csv")

    if not os.path.exists(csv_path):
        return []

    import csv
    from collections import OrderedDict

    puzzles = OrderedDict()
    try:
        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    day = int(row.get("game_day", 0))
                except (ValueError, TypeError):
                    continue
                mystery = row.get("mystery_player", "").strip()
                teammate = row.get("teammate_name", "").strip()
                if day not in puzzles:
                    puzzles[day] = {
                        "mystery": mystery,
                        "teammates": []
                    }
                if teammate and teammate not in puzzles[day]["teammates"]:
                    puzzles[day]["teammates"].append(teammate)

        pools = []
        for day, data in puzzles.items():
            pools.append({
                "type": "played_with",
                "game_day": day,
                "mystery_player": data["mystery"],
                "players": [data["mystery"]],
                "teammates": data["teammates"]
            })
        return pools
    except Exception as e:
        print(f"⚠️ Error loading played_with games from {csv_path}: {e}")
        return []

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

    # 3. Played With
    try:
        pw_pools = load_played_with_pools()
        pools.extend(pw_pools)
    except Exception as e:
        print(f"⚠️ Error loading played_with games: {e}")

    return pools

def extract_pool_from_caption(caption_or_title, all_pools=None):
    """
    Parses a video title or caption to extract the corresponding answer pool.
    Supports:
    - Played With day numbers: e.g. 'Played With #19', 'Played With Day 19', 'Who Am I? #19'
    - Passport FC: (Country + Club)
    - Player Chain: (Club A + Club B)
    - Played With teammate clue list: if >= 2 teammates match a puzzle's teammate list

    Returns list of valid player names, or None if unrecognized.
    Guards against returning all historical players.
    """
    if not caption_or_title:
        return None

    if all_pools is None:
        all_pools = get_all_active_daily_answer_pools()

    norm_text = normalize_text(caption_or_title)

    # ── Pattern 1: Played With / Who Am I Day Number ──
    # Matches "Played With #19", "Played With Day 19", "Played With Puzzle #19", "Who Am I? #19", etc.
    pattern_pw = r"\bplayed\s+with\b[^\w\d\n\r]*(?:(?:day|puzzle)\b[^\w\d\n\r]*#?\s*(\d+)|#\s*(\d+))"
    pattern_wai = r"\bwho\s+am\s+i\b[^\w\d\n\r]*(?:(?:day|puzzle)\b[^\w\d\n\r]*#?\s*(\d+)|#\s*(\d+))"
    pattern_tag = r"#playedwith_?(\d+)\b"

    m_pw = re.search(pattern_pw, caption_or_title, re.IGNORECASE)
    day_num = None
    if m_pw:
        day_num = int(m_pw.group(1) or m_pw.group(2))
    else:
        m_wai = re.search(pattern_wai, caption_or_title, re.IGNORECASE)
        if m_wai:
            day_num = int(m_wai.group(1) or m_wai.group(2))
        else:
            m_tag = re.search(pattern_tag, caption_or_title, re.IGNORECASE)
            if m_tag:
                day_num = int(m_tag.group(1))

    if day_num is not None:
        for pool in all_pools:
            if pool.get("type") == "played_with" and pool.get("game_day") == day_num:
                return pool.get("players", [])

    # ── Pattern 2: Passport FC: Country + Club ──
    # ("Name ONE France player to play for Chelsea" / "France player for Chelsea")
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

    # ── Pattern 3: Player Chain: Club A + Club B ──
    # ("played for BOTH Barcelona and Benfica" / "played for Real Madrid & Juventus")
    m_clubs = re.search(r"(?:played for both|for|played for) (.+?) (?:and|&|\+) (.+?)(?: that| \n|\.|\(|$)", caption_or_title, re.IGNORECASE)
    if m_clubs:
        c1 = normalize_text(m_clubs.group(1).strip())
        c2 = normalize_text(m_clubs.group(2).strip())
        for pool in all_pools:
            if pool.get("type") == "player_chain":
                p_c1 = normalize_text(pool.get("entity_1", ""))
                p_c2 = normalize_text(pool.get("entity_2", ""))
                if (c1 in p_c1 and c2 in p_c2) or (c1 in p_c2 and c2 in p_c1):
                    return pool["players"]

    # ── Pattern 4: Played With Teammate Clue List ──
    # Match if >= 2 teammates mentioned in caption match a puzzle's teammate list
    best_match = None
    max_hits = 0
    for pool in all_pools:
        if pool.get("type") == "played_with":
            teammates = pool.get("teammates", [])
            hits = 0
            for tm in teammates:
                norm_tm = normalize_text(tm)
                if not norm_tm:
                    continue
                # Full teammate name match
                if re.search(r"\b" + re.escape(norm_tm) + r"\b", norm_text):
                    hits += 1
                    continue
                # Compound last name or single last name (min 3 chars)
                parts = norm_tm.split()
                if len(parts) >= 2:
                    compound_last = " ".join(parts[-2:])
                    if len(compound_last) >= 5 and re.search(r"\b" + re.escape(compound_last) + r"\b", norm_text):
                        hits += 1
                        continue
                    last = parts[-1]
                    if len(last) >= 3 and re.search(r"\b" + re.escape(last) + r"\b", norm_text):
                        hits += 1
                        continue
                elif len(norm_tm) >= 3 and re.search(r"\b" + re.escape(norm_tm) + r"\b", norm_text):
                    hits += 1
                    continue
            if hits > max_hits:
                max_hits = hits
                best_match = pool

    if max_hits >= 2 and best_match:
        return best_match.get("players", [])

    return None

CHATTER_WORDS = {
    # Pronouns & determiners
    "i", "me", "my", "myself", "mine",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself",
    "she", "her", "hers", "herself",
    "it", "its", "itself",
    "we", "us", "our", "ours", "ourselves",
    "they", "them", "their", "theirs", "themselves",
    "this", "that", "these", "those", "there", "here",
    "what", "which", "who", "whom", "whose", "where", "when", "why", "how",
    "a", "an", "the",

    # Prepositions & conjunctions
    "in", "on", "at", "to", "for", "of", "with", "by", "from", "about",
    "into", "through", "during", "before", "after", "above", "below",
    "up", "down", "out", "off", "over", "under", "again", "further",
    "then", "once", "as", "until", "while", "against", "between",
    "and", "but", "or", "nor", "so", "yet", "if", "because", "although",
    "though", "since", "unless", "than", "whether", "either", "neither",
    "without", "like",

    # Verbs, auxiliaries & contractions
    "is", "am", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "having",
    "do", "does", "did", "doing", "done",
    "can", "could", "will", "would", "shall", "should", "may", "might", "must",
    "s", "t", "re", "ve", "m", "d", "ll",
    "dont", "doesnt", "didnt", "cant", "wont", "isnt", "arent", "wasnt", "werent",
    "hasnt", "havent", "hadnt", "couldnt", "wouldnt", "shouldnt",

    # Speech / thinking / guessing verbs
    "think", "thinks", "thought", "thinking",
    "guess", "guesses", "guessed", "guessing",
    "know", "knows", "knew", "known", "knowing",
    "say", "says", "said", "saying",
    "mean", "means", "meant", "meaning",
    "believe", "believes", "believed", "believing",
    "bet", "bets", "betting",
    "feel", "feels", "felt",
    "reckon", "reckons", "reckoned",
    "suppose", "supposes", "supposed",
    "hope", "hopes", "hoped",
    "swear", "swears", "swore",
    "see", "sees", "saw", "seen", "seeing",
    "look", "looks", "looked", "looking",
    "sound", "sounds", "sounded", "sounding",
    "tell", "tells", "told",
    "remember", "remembers", "remembered",
    "played", "plays", "play", "playing",
    "got", "get", "gets", "getting",

    # Adverbs, certainty & reaction words
    "yes", "no", "not", "yeah", "yep", "nope", "nah", "aye",
    "sure", "surely", "definitely", "obviously", "clearly", "probably", "maybe",
    "perhaps", "certainly", "actually", "honestly", "truly", "literally", "really",
    "always", "never", "ever", "already", "still", "just", "only", "also", "too",
    "even", "very", "quite", "well", "now", "easily", "simply", "totally",
    "absolutely", "correctly", "pretty", "right", "wrong", "easy", "hard",

    # Community, slang & footy terms
    "bro", "brother", "bruh", "brah", "mate", "man", "dude", "guy", "guys",
    "lad", "lads", "boy", "boys", "blud", "fam", "boss", "chief", "king",
    "goat", "legend", "baller", "beast", "wall", "monster", "machine", "star",
    "great", "good", "best", "fav", "favorite", "favourite", "worst",
    "underrated", "overrated", "elite", "class", "prime", "top",
    "first", "second", "third", "one", "two", "three",
    "shout", "pick", "answer", "choice", "name", "player", "players",
    "footballer", "striker", "midfielder", "defender", "winger", "keeper",
    "goalkeeper", "captain", "club", "team", "country", "league", "match",
    "game", "video", "short", "shorts", "reel", "reels", "tiktok", "clip",
    "love", "hate", "fire", "boom", "doubt", "chance", "way", "case", "point",
    "fact", "facts", "lol", "lmao", "haha", "hahaha", "gg", "wow", "omg",
    "pls", "please", "thanks", "thank", "thx", "ty", "cheers",
    "drop", "comment", "comments", "bio", "link", "arcade", "puzzle", "puzzles",
    "challenge", "today", "todays", "day", "daily",
    "percent", "pct",

    # Common clubs & teams
    "arsenal", "chelsea", "liverpool", "city", "united", "barca", "barcelona",
    "madrid", "juve", "juventus", "milan", "inter", "bayern", "psg",
    "benfica", "sporting", "porto", "dortmund", "atletico", "spurs", "tottenham"
}

def _is_valid_adjacent_word(word, player_words):
    if not word:
        return True
    if word in player_words:
        return True
    if word in CHATTER_WORDS:
        return True
    if word.isdigit():
        return True
    return False

def _find_valid_match_span(comment_words, target_words, player_words):
    """
    Finds if target_words appears as a contiguous sub-slice in comment_words
    such that words immediately before and after (if any) are valid
    (either part of the player's name, or a known chatter word, or a number).
    Also guards against 2-word foreign player names (e.g. 'Felix Kroos', 'Gabriel Jesus').
    """
    L = len(target_words)
    if L == 0 or len(comment_words) < L:
        return False

    for i in range(len(comment_words) - L + 1):
        if comment_words[i : i + L] == target_words:
            prev_w = comment_words[i - 1] if i > 0 else None
            next_w = comment_words[i + L] if (i + L) < len(comment_words) else None

            if _is_valid_adjacent_word(prev_w, player_words) and _is_valid_adjacent_word(next_w, player_words):
                # Additional check: If comment has 2 words and neither is a chatter word,
                # both words MUST belong to the player's name.
                if len(comment_words) == 2:
                    w0, w1 = comment_words[0], comment_words[1]
                    if (w0 not in CHATTER_WORDS and not w0.isdigit()) and (w1 not in CHATTER_WORDS and not w1.isdigit()):
                        if w0 not in player_words or w1 not in player_words:
                            return False
                return True
    return False

def match_comment_to_pool(comment_text, valid_players):
    """
    Checks if comment_text contains a valid player name, nickname, or last name.
    Returns the canonical player name if matched, else None.
    Guards against collisions with different players sharing parts (e.g. 'Felix Kroos', 'Gabriel Jesus').
    """
    if not comment_text or not valid_players:
        return None

    norm_comment = normalize_text(comment_text)
    if not norm_comment:
        return None
    comment_words = norm_comment.split()

    # 1. Nicknames and typo dictionary check
    for nick, canonical in NICKNAMES.items():
        norm_nick = normalize_text(nick)
        if not norm_nick:
            continue
        nick_words = norm_nick.split()
        if re.search(r"\b" + re.escape(norm_nick) + r"\b", norm_comment):
            norm_canonical = normalize_text(canonical)
            canonical_words = set(norm_canonical.split()) | set(nick_words)
            for p in valid_players:
                norm_p = normalize_text(p)
                p_words = set(norm_p.split()) | canonical_words
                if norm_canonical == norm_p or re.search(r"\b" + re.escape(norm_canonical) + r"\b", norm_p):
                    if _find_valid_match_span(comment_words, nick_words, p_words):
                        return p

    # 2. Direct player matching - sort by descending length to prioritize full names before short surnames
    sorted_players = sorted(valid_players, key=lambda x: len(x), reverse=True)
    for p in sorted_players:
        norm_p = normalize_text(p)
        parts = norm_p.split()
        if not parts:
            continue
        player_words = set(parts)

        # A. Full name match with word boundaries
        if len(parts) >= 2:
            if _find_valid_match_span(comment_words, parts, player_words):
                return p

        # B. Multi-word parts (e.g. 'Di Maria', 'De Jong', 'Van Dijk')
        if len(parts) >= 2:
            compound_last = parts[-2:]
            if len(" ".join(compound_last)) >= 5:
                if _find_valid_match_span(comment_words, compound_last, player_words):
                    return p

        # C. Last name match (min 4 characters to avoid false positives)
        if len(parts) > 1:
            last = parts[-1]
            if len(last) >= 4:
                if _find_valid_match_span(comment_words, [last], player_words):
                    return p

        # D. Single-name superstars (e.g. 'Ronaldo', 'Neymar', 'Casemiro', 'Deco', 'Gabriel')
        elif len(parts) == 1 and len(norm_p) >= 4:
            if _find_valid_match_span(comment_words, [norm_p], player_words):
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
            # Guard against fallback to merging all historical players, preventing false-positive replies
            print(f"⚠️ [AUTO-REPLY] Could not resolve answer pool for '{v_title[:45]}'. Skipping reply matching.")
            continue

        # Check if matched pool is a played_with mystery player puzzle
        is_played_with = False
        for p in all_pools:
            if p.get("type") == "played_with" and p.get("players") == pool:
                is_played_with = True
                break

        matched_player = match_comment_to_pool(text, pool)
        if matched_player:
            total_matched += 1
            templates = PLAYED_WITH_REPLY_TEMPLATES if is_played_with else REPLY_TEMPLATES
            template = random.choice(templates)
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
            # Guard against fallback to merging all historical players, preventing false-positive replies
            print(f"⚠️ [AUTO-REPLY] Could not resolve answer pool for post '{(caption or '').splitlines()[0][:45]}'. Skipping reply matching.")
            continue

        # Check if matched pool is a played_with mystery player puzzle
        is_played_with = False
        for p in all_pools:
            if p.get("type") == "played_with" and p.get("players") == pool:
                is_played_with = True
                break

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
                templates = PLAYED_WITH_REPLY_TEMPLATES if is_played_with else REPLY_TEMPLATES
                template = random.choice(templates)
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
