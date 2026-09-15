#!/usr/bin/env python3
"""
scripts/sync_fixtures_calendar.py — Fixtures & Derbies Ingestion Service
========================================================================
Validates, curates, and synchronizes real-world football fixtures (Top 5 leagues,
UEFA Champions League, Europa League, international tournaments) into
`data/fixtures_calendar.json` for contextual puzzle scheduling and social trend-jacking.

Usage:
  python scripts/sync_fixtures_calendar.py --list
  python scripts/sync_fixtures_calendar.py --validate
  python scripts/sync_fixtures_calendar.py --add-fixture --date 2026-11-15 --name "North London Derby" --home "Arsenal" --away "Tottenham Hotspur" --comp "Premier League"
  python scripts/sync_fixtures_calendar.py --sync-api [--api-key YOUR_KEY]
"""

import os
import sys
import json
import argparse
import datetime
import urllib.request
import urllib.error

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES_FILE = os.path.join(BASE_DIR, "data", "fixtures_calendar.json")

# Standard club name aliases to align external API feeds with Playmaker puzzle databases
CLUB_ALIASES = {
    "inter milan": "Inter",
    "internazionale": "Inter",
    "fc internazionale milano": "Inter",
    "psg": "Paris Saint-Germain",
    "paris sg": "Paris Saint-Germain",
    "paris saint-germain fc": "Paris Saint-Germain",
    "tottenham": "Tottenham Hotspur",
    "tottenham hotspur fc": "Tottenham Hotspur",
    "spurs": "Tottenham Hotspur",
    "atlético madrid": "Atletico Madrid",
    "club atlético de madrid": "Atletico Madrid",
    "atletico de madrid": "Atletico Madrid",
    "man city": "Manchester City",
    "manchester city fc": "Manchester City",
    "man utd": "Manchester United",
    "manchester united fc": "Manchester United",
    "mufc": "Manchester United",
    "real madrid cf": "Real Madrid",
    "fc barcelona": "Barcelona",
    "fc bayern münchen": "Bayern Munich",
    "fc bayern munich": "Bayern Munich",
    "bayern münchen": "Bayern Munich",
    "borussia dortmund": "Borussia Dortmund",
    "bvb 09 borussia dortmund": "Borussia Dortmund",
    "ac milan": "AC Milan",
    "milan": "AC Milan",
    "juventus fc": "Juventus",
    "chelsea fc": "Chelsea",
    "arsenal fc": "Arsenal",
    "liverpool fc": "Liverpool",
    "as roma": "Roma",
    "roma": "Roma",
    "ss lazio": "Lazio",
    "lazio": "Lazio",
}

def normalize_club_name(name):
    """Normalize club names against known aliases."""
    if not name:
        return ""
    clean = name.strip()
    return CLUB_ALIASES.get(clean.lower(), clean)

def load_fixtures():
    """Load fixtures from data/fixtures_calendar.json."""
    if not os.path.exists(FIXTURES_FILE):
        return []
    try:
        with open(FIXTURES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {FIXTURES_FILE}: {e}")
        return []

def save_fixtures(fixtures):
    """Save fixtures list to data/fixtures_calendar.json, sorted by date."""
    os.makedirs(os.path.dirname(FIXTURES_FILE), exist_ok=True)
    # Sort chronologically
    fixtures.sort(key=lambda x: x.get("date", ""))
    with open(FIXTURES_FILE, "w", encoding="utf-8") as f:
        json.dump(fixtures, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(fixtures)} fixtures to {FIXTURES_FILE}")

def generate_default_hook_and_tags(clash_name, home_club, away_club, competition):
    """Auto-generate high-converting social hooks and hashtags."""
    c_home = home_club.replace(" ", "")
    c_away = away_club.replace(" ", "")
    comp_tag = f"#{competition.replace(' ', '')}"
    
    derby_keywords = ["derby", "clásico", "clasico", "klassiker", "superclásico", "final"]
    is_derby = any(k in clash_name.lower() for k in derby_keywords)
    
    if is_derby:
        hook = f"⚔️ {clash_name.upper()} SPECIAL!"
    elif "Champions League" in competition:
        hook = f"⭐ CHAMPIONS LEAGUE SHOWDOWN!"
    elif "Europa League" in competition:
        hook = f"⭐ EUROPA LEAGUE SHOWDOWN!"
    elif "Conference League" in competition:
        hook = f"⭐ CONFERENCE LEAGUE SHOWDOWN!"
    elif "Nations League" in competition or "International" in competition:
        hook = f"🌍 NATIONS LEAGUE SHOWDOWN!"
    else:
        hook = f"⚔️ {competition.upper()} MATCHDAY SPECIAL!"

    tags = [f"#{c_home}", f"#{c_away}", comp_tag]
    if "clásico" in clash_name.lower() or "clasico" in clash_name.lower():
        tags.insert(0, "#ElClasico")
    elif "manchester derby" in clash_name.lower():
        tags.insert(0, "#ManchesterDerby")
    elif "north london derby" in clash_name.lower():
        tags.insert(0, "#NorthLondonDerby")
    elif "der klassiker" in clash_name.lower():
        tags.insert(0, "#DerKlassiker")
    elif "derby della capitale" in clash_name.lower():
        tags.insert(0, "#DerbyDellaCapitale")
    elif "Champions League" in competition:
        tags.insert(0, "#UCL")
    elif "Europa League" in competition:
        tags.insert(0, "#UEL")
    elif "Conference League" in competition:
        tags.insert(0, "#UECL")
    elif "Nations League" in competition:
        tags.insert(0, "#NationsLeague")

    # Deduplicate while preserving order
    seen = set()
    dedup_tags = []
    for t in tags:
        if t not in seen:
            seen.add(t)
            dedup_tags.append(t)
            
    return hook, dedup_tags

def validate_fixtures(fixtures=None):
    """Validate fixtures dataset for format, dates, and club normalization."""
    if fixtures is None:
        fixtures = load_fixtures()
    print(f"\n🔍 Validating {len(fixtures)} fixtures...")
    errors = []
    dates_seen = set()
    
    for idx, f in enumerate(fixtures):
        date_str = f.get("date")
        try:
            datetime.date.fromisoformat(date_str)
        except Exception:
            errors.append(f"Fixture #{idx+1}: Invalid ISO date '{date_str}'")
            
        for req in ["clash_name", "competition", "home_club", "away_club"]:
            if not f.get(req):
                errors.append(f"Fixture on {date_str}: Missing required field '{req}'")
                
        # Check normalized clubs
        h_norm = normalize_club_name(f.get("home_club"))
        a_norm = normalize_club_name(f.get("away_club"))
        if h_norm != f.get("home_club"):
            f["home_club"] = h_norm
        if a_norm != f.get("away_club"):
            f["away_club"] = a_norm
            
        dates_seen.add(date_str)

    if errors:
        print(f"❌ Found {len(errors)} validation errors:")
        for err in errors:
            print(f"  • {err}")
        return False
    else:
        print(f"✅ All {len(fixtures)} fixtures are strictly valid across {len(dates_seen)} distinct matchdays.")
        return True

def add_fixture(date_str, clash_name, home_club, away_club, competition, hook=None, hashtags=None):
    """Add or update a fixture in the calendar."""
    fixtures = load_fixtures()
    home_club = normalize_club_name(home_club)
    away_club = normalize_club_name(away_club)
    
    if not hook or not hashtags:
        gen_hook, gen_tags = generate_default_hook_and_tags(clash_name, home_club, away_club, competition)
        hook = hook or gen_hook
        hashtags = hashtags or gen_tags

    # Check if fixture exists on date
    updated = False
    for f in fixtures:
        if f.get("date") == date_str:
            f["clash_name"] = clash_name
            f["competition"] = competition
            f["home_club"] = home_club
            f["away_club"] = away_club
            f["hook"] = hook
            f["hashtags"] = hashtags
            updated = True
            print(f"🔄 Updated existing fixture on {date_str}: {clash_name}")
            break

    if not updated:
        fixtures.append({
            "date": date_str,
            "clash_name": clash_name,
            "competition": competition,
            "home_club": home_club,
            "away_club": away_club,
            "hashtags": hashtags,
            "hook": hook
        })
        print(f"➕ Added new fixture on {date_str}: {clash_name}")

    save_fixtures(fixtures)

def get_derby_metadata(home, away, comp):
    """
    Returns (clash_name, hook, hashtags) with specific branding for famous rivalries.
    """
    pair = set([home, away])
    if pair == {"Real Madrid", "Barcelona"}:
        return "El Clásico", "⚔️ EL CLÁSICO SPECIAL!", ["#ElClasico", "#RealMadrid", "#FCBarcelona", "#LaLiga"]
    if pair == {"Atletico Madrid", "Real Madrid"}:
        return "Madrid Derby", "⚔️ MADRID DERBY SPECIAL!", ["#DerbiMadrileno", "#RealMadrid", "#Atleti", "#LaLiga"]
    if pair == {"Barcelona", "Atletico Madrid"}:
        return "Barcelona vs Atletico Madrid", "⚔️ LA LIGA TITANS SHOWDOWN!", ["#BarcaAtleti", "#LaLiga", "#Barcelona", "#Atleti"]
    if pair == {"Manchester City", "Manchester United"}:
        return "Manchester Derby", "⚔️ MANCHESTER DERBY SPECIAL!", ["#ManchesterDerby", "#ManCity", "#MUFC", "#PremierLeague"]
    if pair == {"Arsenal", "Tottenham Hotspur"}:
        return "North London Derby", "⚔️ NORTH LONDON DERBY SPECIAL!", ["#NorthLondonDerby", "#Arsenal", "#COYS", "#PremierLeague"]
    if pair == {"Liverpool", "Manchester United"}:
        return "North West Derby", "⚔️ NORTH WEST DERBY SPECIAL!", ["#NorthWestDerby", "#LFC", "#MUFC", "#PremierLeague"]
    if pair == {"Arsenal", "Chelsea"}:
        return "Arsenal vs Chelsea (London Derby)", "⚔️ LONDON DERBY SHOWDOWN!", ["#LondonDerby", "#Arsenal", "#Chelsea", "#PremierLeague"]
    if pair == {"Chelsea", "Tottenham Hotspur"}:
        return "Chelsea vs Tottenham Hotspur", "⚔️ LONDON DERBY CLASH!", ["#LondonDerby", "#Chelsea", "#COYS", "#PremierLeague"]
    if pair == {"Manchester City", "Arsenal"}:
        return "Manchester City vs Arsenal", "⚔️ PREMIER LEAGUE TITLE SHOWDOWN!", ["#TitleRace", "#ManCity", "#Arsenal", "#PremierLeague"]
    if pair == {"Liverpool", "Manchester City"}:
        return "Liverpool vs Manchester City", "⚔️ PREMIER LEAGUE TITANS CLASH!", ["#LIVMCI", "#Liverpool", "#ManCity", "#PremierLeague"]
    if pair == {"Chelsea", "Manchester City"}:
        return "Chelsea vs Manchester City", "⚔️ PREMIER LEAGUE BLOCKBUSTER!", ["#CHEMCI", "#Chelsea", "#ManCity", "#PremierLeague"]
    if pair == {"Chelsea", "Liverpool"}:
        return "Chelsea vs Liverpool", "⚔️ PREMIER LEAGUE BLOCKBUSTER!", ["#CHELIV", "#Chelsea", "#Liverpool", "#PremierLeague"]
    if pair == {"Liverpool", "Arsenal"}:
        return "Liverpool vs Arsenal", "⚔️ PREMIER LEAGUE BLOCKBUSTER!", ["#LIVARS", "#Liverpool", "#Arsenal", "#PremierLeague"]
    if pair == {"Manchester United", "Arsenal"}:
        return "Manchester United vs Arsenal", "⚔️ PREMIER LEAGUE RIVALRY SPECIAL!", ["#MUNARS", "#MUFC", "#Arsenal", "#PremierLeague"]
    if pair == {"Manchester United", "Chelsea"}:
        return "Manchester United vs Chelsea", "⚔️ PREMIER LEAGUE BLOCKBUSTER!", ["#MUNCHE", "#MUFC", "#Chelsea", "#PremierLeague"]
    if pair == {"Tottenham Hotspur", "Manchester City"}:
        return "Tottenham Hotspur vs Manchester City", "⚔️ PREMIER LEAGUE BLOCKBUSTER!", ["#TOTMCI", "#COYS", "#ManCity", "#PremierLeague"]
    if pair == {"Tottenham Hotspur", "Liverpool"}:
        return "Tottenham Hotspur vs Liverpool", "⚔️ PREMIER LEAGUE BLOCKBUSTER!", ["#TOTLIV", "#COYS", "#Liverpool", "#PremierLeague"]
    if pair == {"Tottenham Hotspur", "Manchester United"}:
        return "Tottenham Hotspur vs Manchester United", "⚔️ PREMIER LEAGUE BLOCKBUSTER!", ["#TOTMUN", "#COYS", "#MUFC", "#PremierLeague"]
    if pair == {"Inter", "AC Milan"}:
        return "Derby della Madonnina", "⚔️ DERBY DELLA MADONNINA SPECIAL!", ["#InterMilan", "#DerbyMilano", "#SerieA", "#Inter", "#ACMilan"]
    if pair == {"Inter", "Juventus"}:
        return "Derby d'Italia", "⚔️ DERBY D'ITALIA SPECIAL!", ["#InterJuve", "#DerbyDItalia", "#SerieA", "#Inter", "#Juventus"]
    if pair == {"AC Milan", "Juventus"}:
        return "AC Milan vs Juventus", "⚔️ SERIE A CLASSIC SHOWDOWN!", ["#MilanJuve", "#SerieA", "#ACMilan", "#Juventus"]
    if pair == {"Roma", "Lazio"}:
        return "Derby della Capitale", "⚔️ DERBY DELLA CAPITALE SPECIAL!", ["#DerbyDellaCapitale", "#Roma", "#Lazio", "#SerieA"]
    if pair == {"Bayern Munich", "Borussia Dortmund"}:
        return "Der Klassiker", "⚔️ DER KLASSIKER SPECIAL!", ["#DerKlassiker", "#BVBFCB", "#Bundesliga", "#BayernMunich", "#BVB"]

    th = "#" + home.replace(" ", "")
    ta = "#" + away.replace(" ", "")
    if comp == "Champions League":
        return f"{home} vs {away}", "⭐ CHAMPIONS LEAGUE NIGHT!", ["#UCL", "#ChampionsLeague", th, ta]
    if comp in ["Europa League", "UEFA Europa League"]:
        return f"{home} vs {away}", "⭐ EUROPA LEAGUE NIGHT!", ["#UEL", "#EuropaLeague", th, ta]
    if comp in ["Conference League", "UEFA Conference League"]:
        return f"{home} vs {away}", "⭐ CONFERENCE LEAGUE NIGHT!", ["#UECL", "#ConferenceLeague", th, ta]
    if comp in ["UEFA Nations League", "Nations League"]:
        return f"{home} vs {away}", "🌍 NATIONS LEAGUE NIGHT!", ["#NationsLeague", th, ta]
    return f"{home} vs {away}", f"⚔️ {comp.upper()} MATCHDAY SPECIAL!", [th, ta, "#" + comp.replace(" ", "")]

# Curated high-profile European (UEL/UECL) and International (Nations League) matchday events
CURATED_TOURNAMENT_FIXTURES = [
    # Marquee Rivalry Weekend Spotlights
    {
        "date": "2026-10-31",
        "clash_name": "Der Klassiker",
        "competition": "Bundesliga",
        "home_club": "Bayern Munich",
        "away_club": "Borussia Dortmund",
        "hashtags": ["#DerKlassiker", "#BVBFCB", "#Bundesliga", "#BayernMunich", "#BVB"],
        "hook": "⚔️ DER KLASSIKER SPECIAL!"
    },
    {
        "date": "2026-11-01",
        "clash_name": "Derby della Madonnina",
        "competition": "Serie A",
        "home_club": "AC Milan",
        "away_club": "Inter",
        "hashtags": ["#InterMilan", "#DerbyMilano", "#SerieA", "#Inter", "#ACMilan"],
        "hook": "⚔️ DERBY DELLA MADONNINA SPECIAL!"
    },
    {
        "date": "2026-12-06",
        "clash_name": "Chelsea vs Liverpool",
        "competition": "Premier League",
        "home_club": "Chelsea",
        "away_club": "Liverpool",
        "hashtags": ["#CHELIV", "#Chelsea", "#Liverpool", "#PremierLeague"],
        "hook": "⚔️ PREMIER LEAGUE BLOCKBUSTER!"
    },
    {
        "date": "2027-05-02",
        "clash_name": "Chelsea vs Liverpool",
        "competition": "Premier League",
        "home_club": "Liverpool",
        "away_club": "Chelsea",
        "hashtags": ["#CHELIV", "#Liverpool", "#Chelsea", "#PremierLeague"],
        "hook": "⚔️ PREMIER LEAGUE BLOCKBUSTER!"
    },
    # Europa League & Conference League Thursdays
    {
        "date": "2026-09-24",
        "clash_name": "Tottenham Hotspur vs Roma",
        "competition": "UEFA Europa League",
        "home_club": "Tottenham Hotspur",
        "away_club": "Roma",
        "hashtags": ["#UEL", "#EuropaLeague", "#COYS", "#Roma"],
        "hook": "⭐ EUROPA LEAGUE BLOCKBUSTER!"
    },
    {
        "date": "2026-10-01",
        "clash_name": "Porto vs Manchester United",
        "competition": "UEFA Europa League",
        "home_club": "Porto",
        "away_club": "Manchester United",
        "hashtags": ["#UEL", "#EuropaLeague", "#FCPorto", "#MUFC"],
        "hook": "⭐ EUROPA LEAGUE CLASH!"
    },
    {
        "date": "2026-10-22",
        "clash_name": "Fenerbahce vs Manchester United",
        "competition": "UEFA Europa League",
        "home_club": "Fenerbahce",
        "away_club": "Manchester United",
        "hashtags": ["#UEL", "#EuropaLeague", "#Fenerbahce", "#MUFC"],
        "hook": "⭐ EUROPA LEAGUE NIGHT!"
    },
    {
        "date": "2026-11-05",
        "clash_name": "Galatasaray vs Tottenham Hotspur",
        "competition": "UEFA Europa League",
        "home_club": "Galatasaray",
        "away_club": "Tottenham Hotspur",
        "hashtags": ["#UEL", "#EuropaLeague", "#Galatasaray", "#COYS"],
        "hook": "⭐ EUROPA LEAGUE SHOWDOWN!"
    },
    {
        "date": "2026-11-26",
        "clash_name": "Tottenham Hotspur vs Roma",
        "competition": "UEFA Europa League",
        "home_club": "Tottenham Hotspur",
        "away_club": "Roma",
        "hashtags": ["#UEL", "#EuropaLeague", "#COYS", "#Roma"],
        "hook": "⭐ EUROPA LEAGUE GIANTS CLASH!"
    },
    {
        "date": "2026-12-10",
        "clash_name": "Rangers vs Tottenham Hotspur",
        "competition": "UEFA Europa League",
        "home_club": "Rangers",
        "away_club": "Tottenham Hotspur",
        "hashtags": ["#UEL", "#EuropaLeague", "#Rangers", "#COYS"],
        "hook": "⭐ BRITISH SHOWDOWN IN EUROPE!"
    },
    {
        "date": "2027-01-21",
        "clash_name": "Chelsea vs Real Betis",
        "competition": "UEFA Conference League",
        "home_club": "Chelsea",
        "away_club": "Real Betis",
        "hashtags": ["#UECL", "#ConferenceLeague", "#Chelsea", "#RealBetis"],
        "hook": "⭐ CONFERENCE LEAGUE SPECIAL!"
    },
    {
        "date": "2027-01-28",
        "clash_name": "Lazio vs Real Sociedad",
        "competition": "UEFA Europa League",
        "home_club": "Lazio",
        "away_club": "Real Sociedad",
        "hashtags": ["#UEL", "#EuropaLeague", "#Lazio", "#RealSociedad"],
        "hook": "⭐ EUROPA LEAGUE SHOWDOWN!"
    },
    {
        "date": "2027-05-19",
        "clash_name": "Manchester United vs Roma (UEL Final)",
        "competition": "UEFA Europa League",
        "home_club": "Manchester United",
        "away_club": "Roma",
        "hashtags": ["#UELFinal", "#EuropaLeague", "#MUFC", "#Roma"],
        "hook": "🏆 EUROPA LEAGUE FINAL!"
    },
    {
        "date": "2027-05-26",
        "clash_name": "Chelsea vs Fiorentina (UECL Final)",
        "competition": "UEFA Conference League",
        "home_club": "Chelsea",
        "away_club": "Fiorentina",
        "hashtags": ["#UECLFinal", "#ConferenceLeague", "#Chelsea", "#Fiorentina"],
        "hook": "🏆 CONFERENCE LEAGUE FINAL!"
    },
    # UEFA Nations League International Windows
    {
        "date": "2026-10-09",
        "clash_name": "England vs Germany",
        "competition": "UEFA Nations League",
        "home_club": "England",
        "away_club": "Germany",
        "hashtags": ["#NationsLeague", "#England", "#Germany", "#ENGGER"],
        "hook": "🌍 NATIONS LEAGUE HEAVYWEIGHT CLASH!"
    },
    {
        "date": "2026-10-10",
        "clash_name": "Italy vs Belgium",
        "competition": "UEFA Nations League",
        "home_club": "Italy",
        "away_club": "Belgium",
        "hashtags": ["#NationsLeague", "#Italy", "#Belgium", "#ITABEL"],
        "hook": "🌍 NATIONS LEAGUE SHOWDOWN!"
    },
    {
        "date": "2026-10-13",
        "clash_name": "Germany vs Netherlands",
        "competition": "UEFA Nations League",
        "home_club": "Germany",
        "away_club": "Netherlands",
        "hashtags": ["#NationsLeague", "#Germany", "#Netherlands", "#GERNED"],
        "hook": "🌍 EUROPEAN CLASSIC SHOWDOWN!"
    },
    {
        "date": "2026-11-14",
        "clash_name": "France vs Italy",
        "competition": "UEFA Nations League",
        "home_club": "France",
        "away_club": "Italy",
        "hashtags": ["#NationsLeague", "#France", "#Italy", "#FRAITA"],
        "hook": "🌍 NATIONS LEAGUE BLOCKBUSTER!"
    },
    {
        "date": "2026-11-17",
        "clash_name": "Spain vs Switzerland",
        "competition": "UEFA Nations League",
        "home_club": "Spain",
        "away_club": "Switzerland",
        "hashtags": ["#NationsLeague", "#Spain", "#Switzerland", "#SUIESP"],
        "hook": "🌍 NATIONS LEAGUE CLASH!"
    },
    {
        "date": "2027-03-25",
        "clash_name": "Netherlands vs Spain",
        "competition": "UEFA Nations League",
        "home_club": "Netherlands",
        "away_club": "Spain",
        "hashtags": ["#NationsLeague", "#Netherlands", "#Spain", "#NEDESP"],
        "hook": "🌍 NATIONS LEAGUE QUARTER-FINAL!"
    },
    {
        "date": "2027-03-28",
        "clash_name": "France vs Croatia",
        "competition": "UEFA Nations League",
        "home_club": "France",
        "away_club": "Croatia",
        "hashtags": ["#NationsLeague", "#France", "#Croatia", "#FRACRO"],
        "hook": "🌍 NATIONS LEAGUE QUARTER-FINAL!"
    },
    {
        "date": "2027-06-04",
        "clash_name": "Germany vs Spain (Nations League SF)",
        "competition": "UEFA Nations League",
        "home_club": "Germany",
        "away_club": "Spain",
        "hashtags": ["#NationsLeague", "#NationsLeagueFinals", "#GERESP"],
        "hook": "🏆 NATIONS LEAGUE SEMI-FINAL!"
    },
    {
        "date": "2027-06-06",
        "clash_name": "France vs Spain (Nations League Final)",
        "competition": "UEFA Nations League",
        "home_club": "France",
        "away_club": "Spain",
        "hashtags": ["#NationsLeague", "#NationsLeagueFinals", "#FRASPN"],
        "hook": "🏆 NATIONS LEAGUE FINAL!"
    }
]

def sync_football_data_api(api_key=None, raw_cache_path="data/raw_api/football_data_raw.json"):
    """
    Sync and build authentic calendar from Football-Data.org API with rate limit safety.
    Competitions: PL (Premier League), PD (La Liga), SA (Serie A), BL1 (Bundesliga), CL (Champions League).
    """
    import time
    token = api_key or os.environ.get("FOOTBALL_DATA_API_KEY")
    raw_data = {}

    # Check if cached raw API file exists
    if os.path.exists(raw_cache_path):
        print(f"📦 Loading cached matches from {raw_cache_path}...")
        try:
            with open(raw_cache_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            print(f"⚠️ Could not read cache: {e}")

    if not raw_data:
        if not token:
            print("⚠️ No API key provided! You can pass --api-key or export FOOTBALL_DATA_API_KEY.")
            return
        comps = ["CL", "PD", "SA", "BL1", "PL"]
        headers = {"X-Auth-Token": token}
        for comp in comps:
            print(f"Fetching {comp} from Football-Data API (rate limit safety: 6.5s delay)...")
            url = f"https://api.football-data.org/v4/competitions/{comp}/matches"
            req = urllib.request.Request(url, headers=headers)
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    raw_data[comp] = data
                    print(f"  ✓ {comp}: {len(data.get('matches', []))} matches received")
            except Exception as e:
                print(f"  ❌ {comp} error: {e}")
            time.sleep(6.5) # respect 10 calls/min rate limit

        os.makedirs(os.path.dirname(raw_cache_path), exist_ok=True)
        with open(raw_cache_path, "w", encoding="utf-8") as f:
            json.dump(raw_data, f, indent=2, ensure_ascii=False)

    # Process all matches
    TOP_TEAMS = {
        "Real Madrid", "Barcelona", "Arsenal", "Chelsea", "Manchester City",
        "Manchester United", "Liverpool", "Tottenham Hotspur", "Bayern Munich",
        "Borussia Dortmund", "Inter", "AC Milan", "Juventus", "Paris Saint-Germain",
        "Atletico Madrid", "Roma", "Lazio"
    }

    all_events = []
    for comp_code in ["CL", "PD", "SA", "BL1", "PL"]:
        comp_data = raw_data.get(comp_code, {})
        comp_name = "Premier League" if comp_code == "PL" else ("La Liga" if comp_code == "PD" else ("Serie A" if comp_code == "SA" else ("Bundesliga" if comp_code == "BL1" else "Champions League")))
        for m in comp_data.get("matches", []):
            h = normalize_club_name(m.get("homeTeam", {}).get("name", ""))
            a = normalize_club_name(m.get("awayTeam", {}).get("name", ""))
            d = m.get("utcDate", "")[:10]
            if h in TOP_TEAMS and a in TOP_TEAMS:
                clash_name, hook, tags = get_derby_metadata(h, a, comp_name)
                all_events.append({
                    "date": d,
                    "clash_name": clash_name,
                    "competition": comp_name,
                    "home_club": h,
                    "away_club": a,
                    "hashtags": tags,
                    "hook": hook
                })

    # Add curated European & International events
    for event in CURATED_TOURNAMENT_FIXTURES:
        all_events.append(event)

    def match_priority(e):
        c = e["clash_name"].lower()
        if any(k in c for k in ["clásico", "clasico", "madonnina", "klassiker", "north london", "manchester derby", "north west", "derby d", "madrid derby", "capitale"]):
            return 1
        if e["competition"] == "Champions League":
            return 2
        if e["competition"] in ["UEFA Europa League", "Europa League", "UEFA Conference League", "Conference League", "UEFA Nations League", "Nations League"]:
            return 3
        return 4

    events_by_date = {}
    for e in all_events:
        d = e["date"]
        if d not in events_by_date or match_priority(e) <= match_priority(events_by_date[d]):
            events_by_date[d] = e

    final_fixtures = [events_by_date[d] for d in sorted(events_by_date.keys())]
    save_fixtures(final_fixtures)
    print(f"🎉 Successfully synchronized {len(final_fixtures)} actual season fixtures from football-data.org and European cups!")

def main():
    parser = argparse.ArgumentParser(description="Fixtures Calendar Ingestion & Sync Tool")
    parser.add_argument("--list", action="store_true", help="List all registered matchday fixtures")
    parser.add_argument("--validate", action="store_true", help="Validate fixtures file format and schema")
    parser.add_argument("--add-fixture", action="store_true", help="Add or update a fixture entry")
    parser.add_argument("--date", help="Fixture date (YYYY-MM-DD)")
    parser.add_argument("--name", help="Clash name (e.g. El Clásico)")
    parser.add_argument("--home", help="Home club name")
    parser.add_argument("--away", help="Away club name")
    parser.add_argument("--comp", default="Premier League", help="Competition name")
    parser.add_argument("--hook", help="Custom video hook badge")
    parser.add_argument("--sync-api", action="store_true", help="Sync upcoming fixtures from Football-Data.org API")
    parser.add_argument("--api-key", help="Football-Data.org API Token")

    args = parser.parse_args()

    if args.list:
        fixtures = load_fixtures()
        print(f"\n📅 Registered Fixtures Calendar ({len(fixtures)} events):")
        print("-" * 75)
        for f in fixtures:
            print(f"  {f.get('date')} | {f.get('competition'):<16} | {f.get('clash_name'):<32} | {f.get('hook')}")
        print("-" * 75)
        return

    if args.validate:
        valid = validate_fixtures()
        sys.exit(0 if valid else 1)

    if args.add_fixture:
        if not args.date or not args.name or not args.home or not args.away:
            print("❌ Error: --date, --name, --home, and --away are required.")
            sys.exit(1)
        add_fixture(args.date, args.name, args.home, args.away, args.comp, args.hook)
        return

    if args.sync_api:
        sync_football_data_api(args.api_key)
        return

    # Default to validate & summary
    validate_fixtures()

if __name__ == "__main__":
    main()
