#!/usr/bin/env python3
"""
Playmaker Career Flight Map Short Video Generator (9:16 Vertical Video).
Format 6: 'Player Career Flight Map / Globe Journey'

Inspired by viral football career flight animations (e.g. Arturo Vidal's career journey).
Traces an iconic footballer's transfers across the globe:
- 3D rotating Earth globe with realistic satellite texture and glowing atmospheric halo
- Airplane icon flying along great-circle geodesic trajectories with altitude curvature
- Live odometer accumulating total kilometers flown
- High-res club crest badges, city & country tags, season and transfer fee pills
- Player portrait in broadcast HUD layout
- Chronological ordering (from first club to last club)
- Automatic selection of transfer destination puzzle from n-2 (two days ago)
"""

import os
import sys
import math
import json
import argparse
import datetime
import tempfile
import subprocess
import numpy as np
import cv2
import pandas as pd
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from scripts.geo_manager import (
    get_club_location,
    haversine_distance_km,
    latlon_to_vec3,
    vec3_to_latlon,
    slerp,
    project_point_to_screen,
    is_same_country
)
from scripts.badge_manager import get_club_badge
from scripts.player_image_manager import resolve_player_image_path
from audio_sfx import (
    SAMPLE_RATE,
    generate_whoosh_sound,
    generate_car_drive_sound,
    generate_correct_sound,
    generate_sub_drop_sound,
    generate_background_rhythm_bed
)

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"

WIDTH = 1080
HEIGHT = 1920
FPS = 30

GLOBE_CX = 540
GLOBE_CY = 840
DEFAULT_GLOBE_R = 640

EARTH_TEX_PATH = os.path.join(BASE_DIR, "assets", "map", "earth_day_2048.jpg")
AIRPLANE_PATH = os.path.join(BASE_DIR, "assets", "map", "airplane.png")
CAR_PATH = os.path.join(BASE_DIR, "assets", "map", "car.png")
LEDGER_PATH = os.path.join(BASE_DIR, "data", "puzzle_schedule_ledger.json")
DESTINATION_CSV = os.path.join(BASE_DIR, "daily_destination_games.csv")

# ─────────────────────────────────────────────────────────────
# Procedural Flag & Graphic Helpers
# ─────────────────────────────────────────────────────────────
def get_font(size, bold=True):
    """Loads system fonts with graceful fallback."""
    font_paths = [
        os.path.join(BASE_DIR, "assets", "fonts", "Arial-Bold.ttf" if bold else "Arial.ttf"),
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf"
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def draw_flag_badge(country_name, size=(44, 30)):
    """Draws a clean, vector-procedural flag badge with rounded border."""
    w, h = size
    flag = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    base = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    bdraw = ImageDraw.Draw(base)
    nat = str(country_name or "").strip().title()

    if nat in ["France", "Francia"]:
        sw = w // 3
        bdraw.rectangle([0, 0, sw, h], fill=(0, 35, 149, 255))
        bdraw.rectangle([sw, 0, sw * 2, h], fill=(255, 255, 255, 255))
        bdraw.rectangle([sw * 2, 0, w, h], fill=(237, 41, 57, 255))
    elif nat in ["Italy", "Italia"]:
        sw = w // 3
        bdraw.rectangle([0, 0, sw, h], fill=(0, 146, 70, 255))
        bdraw.rectangle([sw, 0, sw * 2, h], fill=(255, 255, 255, 255))
        bdraw.rectangle([sw * 2, 0, w, h], fill=(206, 43, 55, 255))
    elif nat in ["England", "Inglaterra", "Uk", "United Kingdom", "Great Britain"]:
        bdraw.rectangle([0, 0, w, h], fill=(255, 255, 255, 255))
        cw = max(2, w // 7)
        ch = max(2, h // 5)
        bdraw.rectangle([w // 2 - cw // 2, 0, w // 2 + cw // 2, h], fill=(207, 20, 43, 255))
        bdraw.rectangle([0, h // 2 - ch // 2, w, h // 2 + ch // 2], fill=(207, 20, 43, 255))
    elif nat in ["Spain", "España"]:
        sh = h // 4
        bdraw.rectangle([0, 0, w, sh], fill=(170, 21, 27, 255))
        bdraw.rectangle([0, sh, w, sh * 3], fill=(241, 191, 0, 255))
        bdraw.rectangle([0, sh * 3, w, h], fill=(170, 21, 27, 255))
    elif nat in ["Germany", "Alemania"]:
        sh = h // 3
        bdraw.rectangle([0, 0, w, sh], fill=(0, 0, 0, 255))
        bdraw.rectangle([0, sh, w, sh * 2], fill=(221, 0, 0, 255))
        bdraw.rectangle([0, sh * 2, w, h], fill=(255, 206, 0, 255))
    elif nat in ["Chile"]:
        bdraw.rectangle([0, 0, w, h // 2], fill=(255, 255, 255, 255))
        bdraw.rectangle([0, 0, w // 3, h // 2], fill=(0, 57, 166, 255))
        bdraw.rectangle([0, h // 2, w, h], fill=(213, 43, 30, 255))
    elif nat in ["Portugal"]:
        sw = int(w * 0.4)
        bdraw.rectangle([0, 0, sw, h], fill=(0, 102, 0, 255))
        bdraw.rectangle([sw, 0, w, h], fill=(255, 0, 0, 255))
    elif nat in ["Netherlands", "Holland"]:
        sh = h // 3
        bdraw.rectangle([0, 0, w, sh], fill=(174, 28, 40, 255))
        bdraw.rectangle([0, sh, w, sh * 2], fill=(255, 255, 255, 255))
        bdraw.rectangle([0, sh * 2, w, h], fill=(33, 70, 139, 255))
    elif nat in ["Brazil", "Brasil"]:
        bdraw.rectangle([0, 0, w, h], fill=(0, 156, 59, 255))
        bdraw.polygon([(w // 2, 2), (w - 3, h // 2), (w // 2, h - 3), (3, h // 2)], fill=(255, 223, 0, 255))
        bdraw.ellipse([w // 2 - 6, h // 2 - 6, w // 2 + 6, h // 2 + 6], fill=(0, 39, 118, 255))
    elif nat in ["Argentina"]:
        sh = h // 3
        bdraw.rectangle([0, 0, w, sh], fill=(117, 170, 219, 255))
        bdraw.rectangle([0, sh, w, sh * 2], fill=(255, 255, 255, 255))
        bdraw.rectangle([0, sh * 2, w, h], fill=(117, 170, 219, 255))
        bdraw.ellipse([w // 2 - 4, h // 2 - 4, w // 2 + 4, h // 2 + 4], fill=(255, 184, 28, 255))
    elif nat in ["Saudi Arabia"]:
        bdraw.rectangle([0, 0, w, h], fill=(0, 108, 53, 255))
    elif nat in ["Turkey"]:
        bdraw.rectangle([0, 0, w, h], fill=(227, 10, 23, 255))
        bdraw.ellipse([w // 2 - 8, h // 2 - 8, w // 2 + 8, h // 2 + 8], fill=(255, 255, 255, 255))
        bdraw.ellipse([w // 2 - 6, h // 2 - 6, w // 2 + 6, h // 2 + 6], fill=(227, 10, 23, 255))
    else:
        bdraw.rectangle([0, 0, w, h], fill=(20, 60, 120, 255))

    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, w, h], radius=5, fill=255)
    flag.paste(base, (0, 0), mask)
    ImageDraw.Draw(flag).rounded_rectangle([0, 0, w - 1, h - 1], radius=5, outline=(255, 255, 255, 200), width=1)
    return flag

def format_fee_label(fee_val):
    """Formats transfer fee cleanly: e.g. '€105M RECORD' or 'FREE TRANSFER'."""
    try:
        f = float(fee_val or 0.0)
    except Exception:
        f = 0.0
    if f <= 0.0:
        return "FREE TRANSFER"
    elif f >= 1_000_000:
        m = f / 1_000_000.0
        return f"€{m:.1f}M FEE" if m % 1 != 0 else f"€{int(m)}M FEE"
    elif f >= 1_000:
        return f"€{int(f / 1000)}K FEE"
    return f"€{int(f)} FEE"

# ─────────────────────────────────────────────────────────────
# 3D Earth Globe Renderer
# ─────────────────────────────────────────────────────────────
class GlobeRenderer:
    """High-performance 3D Earth Globe renderer using OpenCV remap and NASA textures."""

    def __init__(self, texture_path=EARTH_TEX_PATH):
        if not os.path.exists(texture_path):
            raise FileNotFoundError(f"Earth texture not found at {texture_path}")
        self.tex = cv2.imread(texture_path)
        self.th, self.tw = self.tex.shape[:2]

    def render_globe(self, cam_lat_deg, cam_lon_deg, radius=DEFAULT_GLOBE_R, cx=GLOBE_CX, cy=GLOBE_CY, canvas_shape=(HEIGHT, WIDTH)):
        """Renders 3D sphere projection of Earth onto canvas with glowing atmosphere."""
        h, w = canvas_shape
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        canvas[:] = [10, 8, 5] # Deep space navy

        x0, x1 = max(0, cx - radius), min(w, cx + radius)
        y0, y1 = max(0, cy - radius), min(h, cy + radius)
        bw, bh = x1 - x0, y1 - y0
        if bw <= 0 or bh <= 0:
            return canvas

        y_idx, x_idx = np.indices((bh, bw), dtype=np.float32)
        dx = (x_idx + x0 - cx) / radius
        dy = (cy - (y_idx + y0)) / radius
        rho2 = dx**2 + dy**2
        mask = rho2 <= 1.0

        z = np.sqrt(np.maximum(0.0, 1.0 - rho2))

        lat0 = math.radians(cam_lat_deg)
        lon0 = math.radians(cam_lon_deg)

        y_rot = dy * math.cos(lat0) + z * math.sin(lat0)
        z_rot = -dy * math.sin(lat0) + z * math.cos(lat0)
        x_rot = dx

        lat = np.arcsin(np.clip(y_rot, -1.0, 1.0))
        lon = lon0 + np.arctan2(x_rot, z_rot)

        map_x = ((lon + np.pi) / (2.0 * np.pi) % 1.0) * (self.tw - 1)
        map_y = ((np.pi / 2.0 - lat) / np.pi) * (self.th - 1)

        patch = cv2.remap(self.tex, map_x.astype(np.float32), map_y.astype(np.float32), cv2.INTER_LINEAR)

        # Fresnel limb atmospheric glow on the rim
        rim = np.clip((rho2 - 0.65) / 0.35, 0.0, 1.0) * 0.45
        patch_f = patch.astype(np.float32)
        patch_f[:, :, 0] += rim * 255.0 # Blue
        patch_f[:, :, 1] += rim * 190.0 # Green
        patch = np.clip(patch_f, 0, 255).astype(np.uint8)

        target_area = canvas[y0:y1, x0:x1]
        target_area[mask] = patch[mask]

        # Soft corona atmosphere outside sphere edge
        halo_mask = (rho2 > 1.0) & (rho2 <= 1.25)
        halo_intensity = np.clip((1.25 - rho2) / 0.25, 0.0, 1.0) * 0.35
        target_area[halo_mask, 0] = np.clip(target_area[halo_mask, 0] + halo_intensity[halo_mask] * 240, 0, 255)
        target_area[halo_mask, 1] = np.clip(target_area[halo_mask, 1] + halo_intensity[halo_mask] * 130, 0, 255)
        target_area[halo_mask, 2] = np.clip(target_area[halo_mask, 2] + halo_intensity[halo_mask] * 40, 0, 255)

        return canvas

# ─────────────────────────────────────────────────────────────
# Dataset Loader & Chronological Reversal
# ─────────────────────────────────────────────────────────────
def get_n_minus_2_date(reference_date=None):
    """Returns the date for n-2 (two days ago)."""
    ref = reference_date if reference_date else datetime.date.today()
    return ref - datetime.timedelta(days=2)

def load_destination_puzzle(target_date=None, puzzle_num_override=None):
    """
    Loads player and transfers for transfer_destination game.
    Defaults to n-2 (two days ago).
    Switches order from puzzle's reverse sequence to chronological (first to last club).
    """
    if puzzle_num_override:
        puzzle_id = int(puzzle_num_override)
        target_dt = target_date if target_date else datetime.date.today()
    else:
        target_dt = target_date if target_date else get_n_minus_2_date()
        date_str = target_dt.strftime("%Y-%m-%d")
        puzzle_id = None
        if os.path.exists(LEDGER_PATH):
            try:
                with open(LEDGER_PATH, "r", encoding="utf-8") as f:
                    ledger = json.load(f)
                    entry = ledger.get(date_str, {})
                    puzzle_id = entry.get("puzzles", {}).get("transfer_destination")
            except Exception:
                pass
        if not puzzle_id:
            launch_dt = datetime.date(2026, 7, 27)
            diff = (target_dt - launch_dt).days
            puzzle_id = (diff % 180) + 1

    if not os.path.exists(DESTINATION_CSV):
        raise FileNotFoundError(f"Missing {DESTINATION_CSV}")

    df = pd.read_csv(DESTINATION_CSV)
    p_df = df[df["game_day"] == puzzle_id].copy()
    if p_df.empty:
        # Fallback to puzzle #75 (Pogba) if day out of range
        p_df = df[df["game_day"] == 75].copy()
        puzzle_id = 75

    # Switch order: The actual puzzle presents transfers in reverse order (last to first).
    # We switch it up to chronological order (first club to last club).
    p_df["transfer_date_dt"] = pd.to_datetime(p_df["transfer_date"], format="mixed", errors="coerce")
    p_df = p_df.sort_values("transfer_date_dt", ascending=True)

    player_name = p_df["player_name"].iloc[0]
    nationality = p_df["country_of_citizenship"].iloc[0]
    position = p_df["position"].iloc[0] if "position" in p_df.columns else "Player"

    legs = []
    # Origin club: from_club_name of the first transfer
    first_from = p_df["from_club_name"].iloc[0]
    prev_club = first_from

    for _, row in p_df.iterrows():
        from_club = row["from_club_name"] or prev_club
        to_club = row["to_club_name"]
        season = row.get("transfer_season", "")
        fee = row.get("transfer_fee", 0.0)

        loc_from = get_club_location(from_club)
        loc_to = get_club_location(to_club)

        # Detect unmapped fallback coordinates to prevent silent rendering glitches
        for cname, loc in [(from_club, loc_from), (to_club, loc_to)]:
            if loc.get("country") == "Europe" and abs(loc.get("lat", 0.0) - 48.8566) < 0.001 and abs(loc.get("lon", 0.0) - 2.3522) < 0.001:
                print(f"⚠️ [GEO WARNING] Club '{cname}' is using default Central Europe fallback! Please map it in data/club_locations.json.")

        dist_km = haversine_distance_km(loc_from["lat"], loc_from["lon"], loc_to["lat"], loc_to["lon"])
        is_domestic = is_same_country(loc_from, loc_to)
        travel_method = "car" if is_domestic else "flight"

        legs.append({
            "from_club": from_club,
            "to_club": to_club,
            "season": str(season),
            "fee": fee,
            "from_loc": loc_from,
            "to_loc": loc_to,
            "distance_km": dist_km,
            "travel_method": travel_method,
            "is_domestic": is_domestic
        })
        prev_club = to_club

    return {
        "puzzle_id": puzzle_id,
        "target_date": target_dt.strftime("%Y-%m-%d"),
        "player_name": player_name,
        "nationality": nationality,
        "position": position,
        "origin_club": first_from,
        "legs": legs
    }

def generate_career_flight_metadata(puzzle_data):
    """
    Generates high-exposure, SEO-optimized metadata for YouTube Shorts and Instagram Reels:
    - YouTube Title: punchy, under 70 characters with #Shorts
    - YouTube Description: complete route, km stats, interactive trivia hook, Playmaker game link, viral tags
    - YouTube Tags: target player, clubs, general football SEO tags
    - Instagram Caption: emoji route timeline, engaging rating question, call to action, 18+ high-intent hashtags
    """
    player = puzzle_data.get("player_name", "Football Legend")
    origin = puzzle_data.get("origin_club", "")
    legs = puzzle_data.get("legs", [])
    
    # Calculate flight & drive stats
    total_km = sum(float(l.get("distance_km", 0.0)) for l in legs)
    flight_km = sum(float(l.get("distance_km", 0.0)) for l in legs if l.get("travel_method") != "car")
    drive_km = sum(float(l.get("distance_km", 0.0)) for l in legs if l.get("travel_method") == "car")
    has_flight = any(l.get("travel_method") != "car" for l in legs)
    has_car = any(l.get("travel_method") == "car" for l in legs)
    all_car = has_car and not has_flight
    
    # Build route sequence
    route_clubs = [origin] if origin else []
    for leg in legs:
        to_c = leg.get("to_club", "")
        if to_c and (not route_clubs or to_c != route_clubs[-1]):
            route_clubs.append(to_c)
    
    route_arrow_str = " ➡️ ".join(route_clubs)
    
    # Calculate fees summary
    total_fees = 0.0
    for leg in legs:
        f = leg.get("fee", 0.0)
        if isinstance(f, (int, float)) and not math.isnan(f):
            total_fees += f
            
    if total_fees >= 1000000:
        fee_str = f"€{total_fees / 1000000:.1f}M"
    elif total_fees > 0:
        fee_str = f"€{total_fees / 1000:.0f}K"
    else:
        fee_str = "Free Transfers / Academy"

    clean_tag = player.replace(" ", "").replace("'", "").replace("-", "")

    # 1. YouTube Title (< 70 chars for clean mobile truncation)
    if all_car:
        yt_title = f"{player}'s Career Road Trip! 🚗 Where Did He Play? #Shorts"
        if len(yt_title) > 95:
            yt_title = f"{player}'s Career Road Trip! 🚗 #Shorts"
    elif has_car and has_flight:
        yt_title = f"{player}'s Career Journey! ✈️🚗 Where Did He Play? #Shorts"
        if len(yt_title) > 95:
            yt_title = f"{player}'s Career Journey! ✈️🚗 #Shorts"
    else:
        yt_title = f"{player}'s Career Flight Map! ✈️🌍 Where Did He Play? #Shorts"
        if len(yt_title) > 95:
            yt_title = f"{player}'s Career Flight Map! ✈️🌍 #Shorts"

    # 2. YouTube Description
    if all_car:
        desc_intro = f"🚗 Tracing {player}'s complete career road trip across the country!\n"
        dist_str = f"📏 Total Distance Driven: {int(total_km):,} km\n"
        route_label = "🚗 Route"
    elif has_car and has_flight:
        desc_intro = f"✈️🚗 Tracing {player}'s complete career flight & road journey across the globe!\n"
        dist_str = f"📏 Total Distance: {int(total_km):,} km ({int(flight_km):,} km flown, {int(drive_km):,} km driven)\n"
        route_label = "🛫/🚗 Route"
    else:
        desc_intro = f"✈️ Tracing {player}'s complete career flight journey across the globe!\n"
        dist_str = f"📏 Total Distance Flown: {int(total_km):,} km\n"
        route_label = "🛫 Route"

    yt_desc = (
        f"{desc_intro}"
        f"Can you name every club he played for without missing one? 🤔\n\n"
        f"📍 Origin: {origin}\n"
        f"{route_label}: {route_arrow_str}\n"
        f"{dist_str}"
        f"💰 Career Transfer Fees: {fee_str}\n\n"
        f"🎮 Guess today's mystery transfer destination live (free, no sign up):\n"
        f"👉 https://playmaker.best/games/transfer_destination.html\n"
        f"👉 https://playmaker.best/\n\n"
        f"#Shorts #football #soccer #{clean_tag} #transfers #transfermarket #flightmap #career #trivia #ballknowledge #playmaker #footballquiz"
    )

    # 3. YouTube Tags
    yt_tags = [
        "Shorts",
        "football",
        "soccer",
        player,
        "transfers",
        "career flight map",
        "transfer destination",
        "flight radar",
        "football trivia",
        "ball knowledge",
        "playmaker",
        "football quiz",
        "soccer quiz",
        "career journey",
        "premier league",
        "champions league"
    ]
    if has_car:
        yt_tags.extend(["career road trip", "car travel", "road trip"])
    # Add clubs to tags
    for c in route_clubs[:4]:
        if c and c not in yt_tags:
            yt_tags.append(c)

    # 4. Instagram Caption
    leg_bullets = []
    for leg in legs:
        from_c = leg.get("from_club", "")
        to_c = leg.get("to_club", "")
        season = leg.get("season", "")
        season_str = f" ({season})" if season else ""
        icon = "🚗" if leg.get("travel_method") == "car" else "✈️"
        leg_bullets.append(f"• {from_c} {icon} {to_c}{season_str}")
    
    route_bullets_str = "\n".join(leg_bullets) if leg_bullets else f"• {route_arrow_str}"

    if all_car:
        ig_header = (
            f"🚗 {player.upper()}'S COMPLETE CAREER ROAD TRIP!\n"
            f"{int(total_km):,} km driven across his football journey.\n\n"
        )
    elif has_car and has_flight:
        ig_header = (
            f"✈️🚗 {player.upper()}'S COMPLETE CAREER JOURNEY!\n"
            f"{int(total_km):,} km traveled ({int(flight_km):,} km flown, {int(drive_km):,} km driven).\n\n"
        )
    else:
        ig_header = (
            f"✈️🌍 {player.upper()}'S COMPLETE CAREER FLIGHT MAP!\n"
            f"{int(total_km):,} km flown across his football journey.\n\n"
        )

    ig_caption = (
        f"{ig_header}"
        f"Can you name every single club he played for? 🤔\n\n"
        f"📍 The Career Journey:\n"
        f"{route_bullets_str}\n\n"
        f"👇 RATE HIS CAREER FROM 1 TO 10 IN THE COMMENTS!\n\n"
        f"🎮 Guess today's mystery transfer destination live at playmaker.best (link in bio!)\n\n"
        f"#reels #football #soccer #{clean_tag} #transfers #transferwindow #transfermarket "
        f"#flightradar #globe #careerjourney #ballknowledge #footballquiz #soccerquiz "
        f"#footballreels #playmaker #futbol #calcio #premierleague #championsleague"
    )

    return {
        "youtube_title": yt_title,
        "youtube_description": yt_desc,
        "youtube_tags": yt_tags,
        "instagram_caption": ig_caption,
        "target_name": player,
        "total_km": total_km,
        "flight_km": flight_km,
        "drive_km": drive_km,
        "route_str": route_arrow_str
    }

# ─────────────────────────────────────────────────────────────
# Video Scene Timeline Layout
# ─────────────────────────────────────────────────────────────
def build_video_timeline(puzzle_data):
    """
    Builds the frame-by-frame animation timeline:
    - Beat 1: Intro / Takeoff at Origin Club (~2.5s)
    - Beat 2: Flight legs (each ~4.0s - 4.5s)
    - Beat 3: Outro / Complete Career Overview (~3.5s)
    """
    legs = puzzle_data["legs"]
    num_legs = len(legs)

    INTRO_DUR = 2.4
    OUTRO_DUR = 3.6
    # Scale leg duration so total video is ~20-25 seconds
    LEG_DUR = max(3.2, min(4.8, 18.0 / max(1, num_legs)))

    total_duration = INTRO_DUR + (num_legs * LEG_DUR) + OUTRO_DUR
    total_frames = int(total_duration * FPS)

    timeline = {
        "total_duration": total_duration,
        "total_frames": total_frames,
        "intro_frames": int(INTRO_DUR * FPS),
        "outro_frames": int(OUTRO_DUR * FPS),
        "leg_duration": LEG_DUR,
        "leg_frames": int(LEG_DUR * FPS),
        "legs": legs
    }
    return timeline

# ─────────────────────────────────────────────────────────────
# Audio Track Generator
# ─────────────────────────────────────────────────────────────
def synthesize_career_audio(timeline, output_wav_path):
    """Builds energetic sports audio track with jet whooshes, engine zooms, arrival chimes, and rhythm bed."""
    total_samples = int(SAMPLE_RATE * timeline["total_duration"])
    audio = np.zeros(total_samples, dtype=np.float32)

    # 1. Driving sports drum rhythm bed
    bed = generate_background_rhythm_bed(timeline["total_duration"], bpm=128)
    audio[:len(bed)] += bed * 0.45

    def add_sfx(sound_arr, start_sec, gain=1.0):
        start_s = int(start_sec * SAMPLE_RATE)
        end_s = min(start_s + len(sound_arr), total_samples)
        valid = end_s - start_s
        if valid > 0:
            audio[start_s:end_s] += sound_arr[:valid] * gain

    whoosh = generate_whoosh_sound()
    car_sound = generate_car_drive_sound()
    chime = generate_correct_sound()
    sub_drop = generate_sub_drop_sound()

    # Intro whoosh
    add_sfx(whoosh, 0.2, 0.9)

    curr_time = timeline["intro_frames"] / FPS
    for i, leg in enumerate(timeline["legs"]):
        is_car = (leg.get("travel_method") == "car")
        if is_car:
            add_sfx(car_sound, curr_time + 0.1, 0.85)
        else:
            add_sfx(whoosh, curr_time + 0.1, 0.85)
        # Landing chime (at 75% of leg duration)
        landing_time = curr_time + (timeline["leg_duration"] * 0.72)
        add_sfx(chime, landing_time, 0.95)
        curr_time += timeline["leg_duration"]

    # Outro impact
    add_sfx(sub_drop, curr_time + 0.2, 1.0)
    add_sfx(whoosh, curr_time + 0.3, 0.7)

    # Normalize audio
    max_val = np.max(np.abs(audio))
    if max_val > 0.01:
        audio = (audio / max_val) * 0.92

    audio_int16 = (audio * 32767).astype(np.int16)
    import scipy.io.wavfile as wavfile
    wavfile.write(output_wav_path, SAMPLE_RATE, audio_int16)
    return output_wav_path

# ─────────────────────────────────────────────────────────────
# Frame Compositor
# ─────────────────────────────────────────────────────────────
def render_flight_frame(frame_idx, timeline, puzzle_data, globe_renderer, airplane_sprite, player_portrait_img, car_sprite=None):
    """Renders a single 1080x1920 video frame with 3D Earth, flight/road trajectory, and HUD cards."""
    if car_sprite is None and os.path.exists(CAR_PATH):
        try:
            car_sprite = Image.open(CAR_PATH).convert("RGBA")
        except Exception:
            pass

    total_frames = timeline["total_frames"]
    intro_frames = timeline["intro_frames"]
    leg_frames = timeline["leg_frames"]
    legs = timeline["legs"]
    num_legs = len(legs)

    player_name = puzzle_data["player_name"]
    nationality = puzzle_data["nationality"]
    origin_club = puzzle_data["origin_club"]
    origin_loc = get_club_location(origin_club)

    # 1. Determine Current Scene State
    if frame_idx < intro_frames:
        # Phase 1: Intro / Takeoff at Origin Club
        progress = frame_idx / float(intro_frames)
        cam_lat = origin_loc["lat"]
        cam_lon = origin_loc["lon"]
        cam_R = DEFAULT_GLOBE_R + 60.0 * (1.0 - progress)
        active_leg_idx = 0
        leg_progress = 0.0
        is_intro = True
        is_outro = False
        accumulated_dist = 0
    elif frame_idx < total_frames - timeline["outro_frames"]:
        # Phase 2: Active Flight Leg
        is_intro = False
        is_outro = False
        elapsed = frame_idx - intro_frames
        active_leg_idx = min(int(elapsed // leg_frames), num_legs - 1)
        leg_progress = (elapsed % leg_frames) / float(leg_frames)

        leg = legs[active_leg_idx]
        v_from = latlon_to_vec3(leg["from_loc"]["lat"], leg["from_loc"]["lon"])
        v_to = latlon_to_vec3(leg["to_loc"]["lat"], leg["to_loc"]["lon"])

        # Camera smoothly tracks plane with smooth ease
        ease_p = 0.5 - 0.5 * math.cos(math.pi * leg_progress)
        v_cam = slerp(v_from, v_to, ease_p)
        cam_lat, cam_lon = vec3_to_latlon(v_cam)
        # Dynamic zoom: zooms out slightly during mid-flight cruise
        cam_R = DEFAULT_GLOBE_R - 40.0 * math.sin(math.pi * leg_progress)

        # Calculate accumulated distance
        past_dist = sum(l["distance_km"] for l in legs[:active_leg_idx])
        curr_dist = leg["distance_km"] * leg_progress
        accumulated_dist = int(past_dist + curr_dist)
    else:
        # Phase 3: Outro Recap / Full Global View
        is_intro = False
        is_outro = True
        active_leg_idx = num_legs - 1
        leg_progress = 1.0
        last_loc = legs[-1]["to_loc"]
        cam_lat = 45.0
        cam_lon = 5.0
        cam_R = DEFAULT_GLOBE_R - 60.0
        accumulated_dist = int(sum(l["distance_km"] for l in legs))

    # 2. Render 3D Globe with Atmosphere
    globe_canvas = globe_renderer.render_globe(cam_lat, cam_lon, radius=int(cam_R), cx=GLOBE_CX, cy=GLOBE_CY)
    frame = Image.fromarray(cv2.cvtColor(globe_canvas, cv2.COLOR_BGR2RGBA))
    draw = ImageDraw.Draw(frame, "RGBA")

    # 3. Draw Completed & Active Flight/Road Trails
    for idx, leg in enumerate(legs):
        is_car_leg = (leg.get("travel_method") == "car")
        v1 = latlon_to_vec3(leg["from_loc"]["lat"], leg["from_loc"]["lon"])
        v2 = latlon_to_vec3(leg["to_loc"]["lat"], leg["to_loc"]["lon"])

        if idx < active_leg_idx or is_outro:
            # Fully completed past leg
            max_step = 40
            pts = []
            for s in range(max_step + 1):
                vt = slerp(v1, v2, s / float(max_step))
                lat_d, lon_d = vec3_to_latlon(vt)
                if is_car_leg:
                    alt = 1.002
                else:
                    alt = 1.0 + 0.03 * math.sin(math.pi * (s / float(max_step)))
                px, py, vis = project_point_to_screen(lat_d, lon_d, cam_lat, cam_lon, GLOBE_CX, GLOBE_CY, cam_R, alt)
                if vis:
                    pts.append((px, py))
            if len(pts) > 1:
                if is_car_leg:
                    for k in range(len(pts) - 1):
                        draw.line([pts[k], pts[k+1]], fill=(255, 190, 0, 80), width=6)
                        draw.line([pts[k], pts[k+1]], fill=(255, 245, 200, 160), width=2)
                else:
                    for k in range(len(pts) - 1):
                        draw.line([pts[k], pts[k+1]], fill=(0, 240, 255, 60), width=6)
                        draw.line([pts[k], pts[k+1]], fill=(255, 255, 255, 140), width=2)
        elif idx == active_leg_idx and not is_intro:
            # Active currently traveling leg
            max_step = max(2, int(40 * leg_progress))
            pts = []
            for s in range(max_step + 1):
                t_sub = (s / float(max_step)) * leg_progress
                vt = slerp(v1, v2, t_sub)
                lat_d, lon_d = vec3_to_latlon(vt)
                if is_car_leg:
                    alt = 1.002
                else:
                    alt = 1.0 + 0.045 * math.sin(math.pi * t_sub)
                px, py, vis = project_point_to_screen(lat_d, lon_d, cam_lat, cam_lon, GLOBE_CX, GLOBE_CY, cam_R, alt)
                if vis:
                    pts.append((px, py))
            if len(pts) > 1:
                if is_car_leg:
                    # Outer amber/gold road glow
                    for k in range(len(pts) - 1):
                        draw.line([pts[k], pts[k+1]], fill=(255, 200, 0, 140), width=10)
                    # Core bright road trail
                    for k in range(len(pts) - 1):
                        draw.line([pts[k], pts[k+1]], fill=(255, 255, 240, 240), width=4)
                else:
                    # Outer cyan neon glow
                    for k in range(len(pts) - 1):
                        draw.line([pts[k], pts[k+1]], fill=(0, 240, 255, 120), width=10)
                    # Core bright trail
                    for k in range(len(pts) - 1):
                        draw.line([pts[k], pts[k+1]], fill=(255, 255, 255, 240), width=4)

            # Draw Vehicle Icon at Current Head (Car or Airplane)
            if pts:
                head_x, head_y = pts[-1]
                # Tangent angle
                if len(pts) >= 2:
                    p_prev = pts[-2]
                    dx = head_x - p_prev[0]
                    dy = head_y - p_prev[1]
                else:
                    dx, dy = 1, 0
                angle_deg = math.degrees(math.atan2(dy, dx)) + 90.0
                active_sprite = car_sprite if (is_car_leg and car_sprite is not None) else airplane_sprite
                sprite_size = (64, 64) if is_car_leg else (72, 72)
                half_sz = sprite_size[0] // 2
                vehicle_rot = active_sprite.resize(sprite_size).rotate(-angle_deg, resample=Image.BICUBIC)
                frame.alpha_composite(vehicle_rot, (head_x - half_sz, head_y - half_sz))

    # 4. Draw Waypoints & Radar Pins
    all_visited_locs = [origin_loc] + [l["to_loc"] for l in legs[:active_leg_idx + (1 if leg_progress > 0.7 or is_outro else 0)]]
    for i_loc, loc in enumerate(all_visited_locs):
        px, py, vis = project_point_to_screen(loc["lat"], loc["lon"], cam_lat, cam_lon, GLOBE_CX, GLOBE_CY, cam_R)
        if vis:
            is_loc_car = False
            if i_loc > 0 and i_loc - 1 < len(legs):
                is_loc_car = (legs[i_loc - 1].get("travel_method") == "car")
            dot_color = (255, 200, 0, 240) if is_loc_car else (0, 240, 255, 240)
            draw.ellipse([px - 7, py - 7, px + 7, py + 7], fill=dot_color, outline=(255, 255, 255, 255), width=2)
            # Radar pulse rings on latest destination
            if not is_outro and loc == legs[active_leg_idx]["to_loc"] and leg_progress > 0.7:
                is_active_car = (legs[active_leg_idx].get("travel_method") == "car")
                pulse_color = (255, 200, 0, 180) if is_active_car else (0, 240, 255, 180)
                pulse_r = 12 + int(14 * ((frame_idx % 20) / 20.0))
                draw.ellipse([px - pulse_r, py - pulse_r, px + pulse_r, py + pulse_r], outline=pulse_color, width=2)

    # 5. Top Header Banner
    draw.rectangle([0, 0, WIDTH, 175], fill=(7, 10, 18, 230))
    draw.line([(0, 175), (WIDTH, 175)], fill=(0, 240, 255, 180), width=3)

    header_title = f"{player_name.upper()}'S CAREER"
    # Title centered in available left-to-right area
    draw.text((450, 58), header_title, fill=(255, 255, 255, 255), font=get_font(48, True), anchor="mm")

    # Subtitle Pill with Nationality Flag
    pill_w, pill_h = 420, 38
    pill_x0 = 450 - (pill_w // 2)
    pill_y0 = 108
    curr_is_car = (not is_intro and not is_outro and legs[active_leg_idx].get("travel_method") == "car")
    all_car = all(l.get("travel_method") == "car" for l in legs)

    if curr_is_car or (is_intro and all_car):
        subtitle_text = "CAREER ROAD TRIP • FOOTYARCADE"
        pill_border = (255, 200, 0)
        pill_text_col = (255, 200, 0)
    else:
        subtitle_text = "CAREER FLIGHT MAP • FOOTYARCADE"
        pill_border = (0, 240, 255)
        pill_text_col = (0, 240, 255)

    draw.rounded_rectangle([pill_x0, pill_y0, pill_x0 + pill_w, pill_y0 + pill_h], radius=14, fill=(12, 18, 30), outline=pill_border, width=2)
    flag_ico = draw_flag_badge(nationality, size=(30, 20))
    frame.alpha_composite(flag_ico, (pill_x0 + 12, pill_y0 + 9))
    draw.text((pill_x0 + 52, pill_y0 + 19), subtitle_text, fill=pill_text_col, font=get_font(18, True), anchor="lm")

    # 6. Live Distance Odometer (Top Right)
    draw.rounded_rectangle([WIDTH - 220, 24, WIDTH - 30, 84], radius=12, fill=(10, 16, 26, 230), outline=(255, 215, 0, 180), width=2)
    draw.text((WIDTH - 125, 42), f"LEG {min(active_leg_idx + 1, num_legs)} OF {num_legs}", fill=(255, 215, 0, 255), font=get_font(15, True), anchor="mm")
    draw.text((WIDTH - 125, 66), f"{accumulated_dist:,} KM", fill=(255, 255, 255, 255), font=get_font(21, True), anchor="mm")

    # 7. Destination Club Glassmorphic Card (Center HUD)
    if not is_outro:
        card_x, card_y, card_w, card_h = 70, 205, 940, 210
        glass = Image.new("RGBA", (card_w, card_h), (12, 18, 30, 230))
        ImageDraw.Draw(glass).rounded_rectangle([0, 0, card_w, card_h], radius=24, outline=(0, 240, 255, 180), width=2)
        frame.alpha_composite(glass, (card_x, card_y))

        curr_leg = legs[active_leg_idx]
        is_car_leg = (curr_leg.get("travel_method") == "car")
        if is_intro:
            disp_club = origin_club
            disp_loc = origin_loc
            disp_tag = "ORIGIN / EARLY CAREER"
            disp_fee = "DEPARTURE"
            disp_dist = "HOME BASE"
        else:
            disp_club = curr_leg["to_club"]
            disp_loc = curr_leg["to_loc"]
            disp_tag = f"SEASON {curr_leg['season']}" if curr_leg['season'] else "TRANSFER"
            disp_fee = format_fee_label(curr_leg["fee"])
            disp_dist = f"+{int(curr_leg['distance_km']):,} KM DRIVEN" if is_car_leg else f"+{int(curr_leg['distance_km']):,} KM FLOWN"

        # Luminous backing disc for badge so dark crests stand out
        badge_cx, badge_cy = card_x + 95, card_y + 105
        draw.ellipse([badge_cx - 65, badge_cy - 65, badge_cx + 65, badge_cy + 65], fill=(240, 245, 255, 45), outline=(0, 240, 255, 180), width=2)
        badge = get_club_badge(disp_club, (115, 115))
        frame.alpha_composite(badge, (badge_cx - 57, badge_cy - 57))

        # Club Title
        draw.text((card_x + 185, card_y + 45), disp_club.upper(), fill=(255, 255, 255, 255), font=get_font(40, True))

        # City & Country
        city_line = f"{disp_loc['city'].upper()}, {disp_loc['country'].upper()} [{disp_loc['code']}]"
        # Small marker dot (gold if car, cyan if flight)
        marker_color = (255, 200, 0, 255) if (not is_intro and is_car_leg) else (0, 240, 255, 255)
        draw.ellipse([card_x + 188, card_y + 105, card_x + 200, card_y + 117], fill=marker_color)
        draw.text((card_x + 210, card_y + 100), city_line, fill=(180, 210, 240, 255), font=get_font(24, False))

        # Transfer & Distance Pills
        # Left pill (Fee / Tag)
        draw.rounded_rectangle([card_x + 185, card_y + 144, card_x + 500, card_y + 186], radius=10, fill=(57, 255, 20, 220))
        draw.text((card_x + 342, card_y + 165), f"{disp_tag} • {disp_fee}", fill=(7, 12, 20, 255), font=get_font(18, True), anchor="mm")

        # Right pill (Distance)
        dist_fill = (255, 200, 0, 220) if (not is_intro and is_car_leg) else (0, 240, 255, 220)
        draw.rounded_rectangle([card_x + 515, card_y + 144, card_x + 765, card_y + 186], radius=10, fill=dist_fill)
        draw.text((card_x + 640, card_y + 165), disp_dist, fill=(7, 12, 20, 255), font=get_font(18, True), anchor="mm")
    else:
        # Outro Full Recap Summary Card
        card_x, card_y, card_w, card_h = 70, 205, 940, 220
        glass = Image.new("RGBA", (card_w, card_h), (12, 18, 30, 240))
        ImageDraw.Draw(glass).rounded_rectangle([0, 0, card_w, card_h], radius=24, outline=(255, 215, 0, 200), width=2)
        frame.alpha_composite(glass, (card_x, card_y))

        draw.text((card_x + card_w // 2, card_y + 35), "COMPLETE CAREER ROUTE", fill=(255, 215, 0, 255), font=get_font(34, True), anchor="mm")

        # Stats grid
        total_km = sum(l["distance_km"] for l in legs)
        total_fees = sum(float(l["fee"] or 0) for l in legs) / 1_000_000.0

        col_w = card_w // 3
        # Stat 1: Total Clubs
        draw.text((card_x + col_w * 0.5, card_y + 85), f"{num_legs + 1}", fill=(255, 255, 255, 255), font=get_font(44, True), anchor="mm")
        draw.text((card_x + col_w * 0.5, card_y + 130), "CLUBS PLAYED", fill=(160, 180, 210, 255), font=get_font(18, True), anchor="mm")

        # Stat 2: Total Km
        draw.text((card_x + col_w * 1.5, card_y + 85), f"{int(total_km):,}", fill=(0, 240, 255, 255), font=get_font(44, True), anchor="mm")
        draw.text((card_x + col_w * 1.5, card_y + 130), "KM TRAVELED", fill=(160, 180, 210, 255), font=get_font(18, True), anchor="mm")

        # Stat 3: Total Fees
        fee_str = f"€{int(total_fees)}M" if total_fees >= 1 else "FREE"
        draw.text((card_x + col_w * 2.5, card_y + 85), fee_str, fill=(57, 255, 20, 255), font=get_font(44, True), anchor="mm")
        draw.text((card_x + col_w * 2.5, card_y + 130), "TOTAL FEES", fill=(160, 180, 210, 255), font=get_font(18, True), anchor="mm")

        # CTA Bar
        draw.rounded_rectangle([card_x + 40, card_y + 160, card_x + card_w - 40, card_y + 200], radius=10, fill=(12, 18, 30), outline=(0, 240, 255), width=2)
        draw.text((card_x + card_w // 2, card_y + 180), "CAN YOU GUESS TODAY'S CAREER? PLAY ON PLAYMAKER.BEST", fill=(0, 240, 255, 255), font=get_font(18, True), anchor="mm")

    # 8. Player Persona Portrait (Bottom Right)
    if player_portrait_img:
        pw, ph = 260, 260
        p_circ = player_portrait_img.resize((pw, ph), Image.Resampling.LANCZOS)
        mask_c = Image.new("L", (pw, ph), 0)
        ImageDraw.Draw(mask_c).ellipse((0, 0, pw, ph), fill=255)

        # Outer glowing ring
        draw.ellipse([WIDTH - pw - 45, HEIGHT - ph - 65, WIDTH - 35, HEIGHT - 55], outline=(0, 240, 255, 220), width=6)
        frame.paste(p_circ, (WIDTH - pw - 40, HEIGHT - ph - 60), mask_c)

        # Name Badge Pill under portrait
        badge_box = [WIDTH - pw - 50, HEIGHT - 75, WIDTH - 30, HEIGHT - 25]
        draw.rounded_rectangle(badge_box, radius=12, fill=(8, 14, 24, 240), outline=(0, 240, 255, 160), width=2)
        draw.text((WIDTH - pw // 2 - 40, HEIGHT - 50), f"{player_name.upper()} [{puzzle_data.get('nationality', '')[:3].upper()}]", fill=(255, 255, 255, 255), font=get_font(22, True), anchor="mm")

    # 9. Brand Watermark & Link (Bottom Left)
    draw.text((60, 1845), "playmaker.best", fill=(0, 240, 255, 220), font=get_font(30, True))
    draw.text((60, 1880), "Daily Football Transfer Puzzles", fill=(160, 180, 210, 200), font=get_font(20, False))

    return frame.convert("RGB")

# ─────────────────────────────────────────────────────────────
# Main Video Synthesis Engine
# ─────────────────────────────────────────────────────────────
def render_career_flight_video(target_date=None, puzzle_num=None, output_path=None, force=False, preview_only=False):
    """
    Synthesizes the complete 1080x1920 MP4 video for the career flight short.
    Uses FFmpeg stdin pipe to encode at high speed without creating millions of temp image files on disk.
    """
    print("🌍 Initializing Playmaker Career Flight Video Generator...")

    puzzle_data = load_destination_puzzle(target_date=target_date, puzzle_num_override=puzzle_num)
    player_name = puzzle_data["player_name"]
    date_str = puzzle_data["target_date"]
    p_id = puzzle_data["puzzle_id"]

    print(f"🎯 Target Player: {player_name} (Puzzle #{p_id}, Date: {date_str})")
    print(f"🌍 Total Career Journey Legs: {len(puzzle_data['legs'])}")
    for i, leg in enumerate(puzzle_data["legs"]):
        m_ico = "🚗" if leg.get("travel_method") == "car" else "✈️"
        print(f"   Leg {i+1} [{m_ico} {leg.get('travel_method', 'flight').upper()}]: {leg['from_club']} -> {leg['to_club']} ({leg['season']}) [{int(leg['distance_km']):,} km]")

    if not output_path:
        sanitized = player_name.replace(" ", "_").replace("'", "")
        output_path = os.path.join(BASE_DIR, f"output_career_flight_{sanitized}_{date_str}.mp4")

    if not force and not preview_only and os.path.exists(output_path) and os.path.getsize(output_path) > 1_000_000:
        print(f"⚡ Video already exists at {output_path}. Skipping.")
        return output_path

    # Initialize Assets
    globe_renderer = GlobeRenderer()
    airplane_sprite = Image.open(AIRPLANE_PATH).convert("RGBA")
    car_sprite = Image.open(CAR_PATH).convert("RGBA") if os.path.exists(CAR_PATH) else None

    # Resolve Player Image
    portrait_path = resolve_player_image_path(player_name)
    player_portrait_img = None
    if os.path.exists(portrait_path):
        try:
            player_portrait_img = Image.open(portrait_path).convert("RGBA")
        except Exception:
            pass

    timeline = build_video_timeline(puzzle_data)
    print(f"⏱️ Total Video Duration: {timeline['total_duration']:.1f}s ({timeline['total_frames']} frames @ {FPS} FPS)")

    if preview_only:
        preview_frame_idx = timeline["intro_frames"] + int(timeline["leg_frames"] * 0.5)
        print(f"📸 Generating single preview frame at frame #{preview_frame_idx}...")
        img = render_flight_frame(preview_frame_idx, timeline, puzzle_data, globe_renderer, airplane_sprite, player_portrait_img, car_sprite=car_sprite)
        preview_out = os.path.join(BASE_DIR, f"preview_career_flight_{sanitized}.jpg")
        img.save(preview_out, quality=95)
        print(f"✓ Saved preview frame to {preview_out}")
        return preview_out

    # 1. Synthesize Audio
    with tempfile.TemporaryDirectory(prefix="career_flight_") as temp_dir:
        audio_wav = os.path.join(temp_dir, "career_audio.wav")
        print("🎵 Synthesizing dynamic sports audio track...")
        synthesize_career_audio(timeline, audio_wav)

        # 2. Pipe Video Frames Directly to FFmpeg
        print(f"🎬 Encoding video frames with FFmpeg to {output_path}...")
        ffmpeg_cmd = [
            FFMPEG_EXE, "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{WIDTH}x{HEIGHT}",
            "-pix_fmt", "rgb24",
            "-r", str(FPS),
            "-i", "-",
            "-i", audio_wav,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_path
        ]

        proc = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)

        for f_idx in range(timeline["total_frames"]):
            frame_img = render_flight_frame(f_idx, timeline, puzzle_data, globe_renderer, airplane_sprite, player_portrait_img, car_sprite=car_sprite)
            proc.stdin.write(frame_img.tobytes())

            if (f_idx + 1) % 60 == 0 or f_idx == timeline["total_frames"] - 1:
                pct = ((f_idx + 1) / float(timeline["total_frames"])) * 100.0
                print(f"   Rendering: {f_idx + 1}/{timeline['total_frames']} ({pct:.1f}%)")

        proc.stdin.close()
        stderr_output = proc.stderr.read()
        proc.wait()

        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg encoding failed: {stderr_output.decode('utf-8', errors='ignore')}")

    print(f"✅ Successfully rendered career flight short: {output_path} ({os.path.getsize(output_path):,} bytes)")
    return output_path

# ─────────────────────────────────────────────────────────────
# CLI Entry Point
# ─────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Playmaker Career Flight Map Short Video Generator")
    parser.add_argument("--date", type=str, default=None, help="Target date YYYY-MM-DD (defaults to n-2, two days ago)")
    parser.add_argument("--days-back", type=int, default=2, help="Number of days back from today (default 2)")
    parser.add_argument("--puzzle", type=int, default=None, help="Direct puzzle number override (1-180)")
    parser.add_argument("--output", type=str, default=None, help="Output MP4 video path")
    parser.add_argument("--preview", action="store_true", help="Generate single preview JPEG frame instead of full video")
    parser.add_argument("--force", action="store_true", help="Force re-rendering even if output file exists")

    args = parser.parse_args()

    target_dt = None
    if args.date:
        target_dt = datetime.datetime.strptime(args.date, "%Y-%m-%d").date()
    elif args.days_back:
        target_dt = datetime.date.today() - datetime.timedelta(days=args.days_back)

    render_career_flight_video(
        target_date=target_dt,
        puzzle_num=args.puzzle,
        output_path=args.output,
        force=args.force,
        preview_only=args.preview
    )

if __name__ == "__main__":
    main()
