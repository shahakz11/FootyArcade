#!/usr/bin/env python3
"""
Playmaker Reverse Rarity Video Generator (9:16 Vertical Video).
Format 5: 'Ball Knowledge Test / Reverse Rarity Challenge'
Generates high-engagement 1080x1920 short-form video loops for Instagram Reels, TikTok, and YouTube Shorts
using FootyArcade's Player Chain and Passport FC daily datasets.
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
import scipy.io.wavfile as wavfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from scripts.badge_manager import get_club_badge, normalize_club_name

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"

WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION_SEC = 7.0
SAMPLE_RATE = 44100

# Clean Country Codes
COUNTRY_CODES = {
    "France": "FRA", "Argentina": "ARG", "Brazil": "BRA", "Germany": "GER",
    "Spain": "ESP", "England": "ENG", "Italy": "ITA", "Netherlands": "NED",
    "Portugal": "POR", "Belgium": "BEL", "Croatia": "CRO", "Uruguay": "URU",
    "Colombia": "COL", "Ivory Coast": "CIV", "Nigeria": "NGA", "Senegal": "SEN",
    "Ghana": "GHA", "Cameroon": "CMR", "Egypt": "EGY", "Morocco": "MAR",
    "Algeria": "ALG", "Japan": "JPN", "South Korea": "KOR", "Australia": "AUS",
    "United States": "USA", "Mexico": "MEX", "Chile": "CHI", "Sweden": "SWE",
    "Norway": "NOR", "Denmark": "DEN", "Poland": "POL", "Austria": "AUT",
    "Switzerland": "SUI", "Turkey": "TUR", "Greece": "GRE", "Ukraine": "UKR",
    "Serbia": "SRB", "Czech Republic": "CZE", "Scotland": "SCO", "Wales": "WAL",
    "Iceland": "ISL", "Bosnia": "BIH", "Paraguay": "PAR", "Ecuador": "ECU",
    "Canada": "CAN", "Peru": "PER", "Venezuela": "VEN"
}

def get_font(size, bold=False):
    """Loads system fonts with graceful fallback."""
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf",
        "/System/Library/Fonts/Avenir.ttc"
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()

def draw_vector_flag(nationality, size=(160, 160)):
    """Draws a clean, high-res procedural circular flag badge."""
    w, h = size
    flag_img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(flag_img)
    
    rect = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    rdraw = ImageDraw.Draw(rect)
    
    nat = nationality.strip().title()
    if nat in ["France", "Francia"]:
        sw = w // 3
        rdraw.rectangle([0, 0, sw, h], fill=(0, 35, 149, 255))
        rdraw.rectangle([sw, 0, sw * 2, h], fill=(255, 255, 255, 255))
        rdraw.rectangle([sw * 2, 0, w, h], fill=(237, 41, 57, 255))
    elif nat in ["Italy", "Italia"]:
        sw = w // 3
        rdraw.rectangle([0, 0, sw, h], fill=(0, 146, 70, 255))
        rdraw.rectangle([sw, 0, sw * 2, h], fill=(255, 255, 255, 255))
        rdraw.rectangle([sw * 2, 0, w, h], fill=(206, 43, 55, 255))
    elif nat in ["Germany", "Alemania"]:
        sh = h // 3
        rdraw.rectangle([0, 0, w, sh], fill=(0, 0, 0, 255))
        rdraw.rectangle([0, sh, w, sh * 2], fill=(221, 0, 0, 255))
        rdraw.rectangle([0, sh * 2, w, h], fill=(255, 206, 0, 255))
    elif nat in ["Spain", "España"]:
        rdraw.rectangle([0, 0, w, h // 4], fill=(170, 21, 27, 255))
        rdraw.rectangle([0, h // 4, w, h * 3 // 4], fill=(241, 191, 0, 255))
        rdraw.rectangle([0, h * 3 // 4, w, h], fill=(170, 21, 27, 255))
    elif nat in ["Argentina"]:
        sh = h // 3
        rdraw.rectangle([0, 0, w, sh], fill=(116, 172, 223, 255))
        rdraw.rectangle([0, sh, w, sh * 2], fill=(255, 255, 255, 255))
        rdraw.rectangle([0, sh * 2, w, h], fill=(116, 172, 223, 255))
        rdraw.ellipse([w // 2 - 14, h // 2 - 14, w // 2 + 14, h // 2 + 14], fill=(246, 180, 14, 255))
    elif nat in ["Brazil", "Brasil"]:
        rdraw.rectangle([0, 0, w, h], fill=(0, 156, 59, 255))
        rdraw.polygon([(w // 2, 10), (w - 10, h // 2), (w // 2, h - 10), (10, h // 2)], fill=(255, 223, 0, 255))
        rdraw.ellipse([w // 2 - 28, h // 2 - 28, w // 2 + 28, h // 2 + 28], fill=(0, 39, 118, 255))
    elif nat in ["Netherlands", "Holanda", "Paises Bajos"]:
        sh = h // 3
        rdraw.rectangle([0, 0, w, sh], fill=(174, 28, 40, 255))
        rdraw.rectangle([0, sh, w, sh * 2], fill=(255, 255, 255, 255))
        rdraw.rectangle([0, sh * 2, w, h], fill=(33, 70, 139, 255))
    elif nat in ["Belgium", "Belgica"]:
        sw = w // 3
        rdraw.rectangle([0, 0, sw, h], fill=(0, 0, 0, 255))
        rdraw.rectangle([sw, 0, sw * 2, h], fill=(253, 218, 36, 255))
        rdraw.rectangle([sw * 2, 0, w, h], fill=(239, 51, 64, 255))
    elif nat in ["Portugal"]:
        rdraw.rectangle([0, 0, w * 2 // 5, h], fill=(0, 102, 0, 255))
        rdraw.rectangle([w * 2 // 5, 0, w, h], fill=(255, 0, 0, 255))
        rdraw.ellipse([w * 2 // 5 - 20, h // 2 - 20, w * 2 // 5 + 20, h // 2 + 20], fill=(255, 255, 0, 255))
    elif nat in ["Ivory Coast", "Costa De Marfil"]:
        sw = w // 3
        rdraw.rectangle([0, 0, sw, h], fill=(247, 127, 0, 255))
        rdraw.rectangle([sw, 0, sw * 2, h], fill=(255, 255, 255, 255))
        rdraw.rectangle([sw * 2, 0, w, h], fill=(0, 158, 96, 255))
    elif nat in ["Iceland", "Islandia"]:
        rdraw.rectangle([0, 0, w, h], fill=(2, 82, 156, 255))
        rdraw.rectangle([w // 3 - 16, 0, w // 3 + 16, h], fill=(255, 255, 255, 255))
        rdraw.rectangle([0, h // 2 - 16, w, h // 2 + 16], fill=(255, 255, 255, 255))
        rdraw.rectangle([w // 3 - 8, 0, w // 3 + 8, h], fill=(220, 30, 53, 255))
        rdraw.rectangle([0, h // 2 - 8, w, h // 2 + 8], fill=(220, 30, 53, 255))
    else:
        rdraw.rectangle([0, 0, w, h], fill=(20, 32, 55, 255))
        code = COUNTRY_CODES.get(nat, nat[:3].upper())
        font_c = get_font(52, bold=True)
        rdraw.text((w // 2, h // 2), code, fill=(255, 215, 0, 255), font=font_c, anchor="mm")

    mask = Image.new("L", (w, h), 0)
    mdraw = ImageDraw.Draw(mask)
    mdraw.ellipse([0, 0, w, h], fill=255)
    flag_img.paste(rect, (0, 0), mask)
    
    draw.ellipse([2, 2, w - 2, h - 2], outline=(255, 215, 0, 230), width=5)
    return flag_img

def draw_stadium_background(width=WIDTH, height=HEIGHT, frame_idx=0, total_frames=210):
    """Renders a cinematic dark sports stadium atmosphere with smooth diffused lighting."""
    img = Image.new("RGBA", (width, height), (10, 14, 24, 255))
    
    light_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    ldraw = ImageDraw.Draw(light_layer)

    t = (frame_idx / total_frames) * 2 * math.pi
    pulse = 0.85 + 0.15 * math.sin(t)
    
    # Top-Left Cyan Stadium Floodlight
    cx1, cy1 = 80, 160
    r1 = int(380 * pulse)
    ldraw.ellipse([cx1 - r1, cy1 - r1, cx1 + r1, cy1 + r1], fill=(0, 240, 255, 110))
    
    # Bottom-Right Neon Green Floodlight
    cx2, cy2 = width - 80, height - 200
    r2 = int(420 * pulse)
    ldraw.ellipse([cx2 - r2, cy2 - r2, cx2 + r2, cy2 + r2], fill=(57, 255, 20, 95))
    
    # Center soft Gold Accent
    cx3, cy3 = width // 2, 700
    r3 = int(320 * pulse)
    ldraw.ellipse([cx3 - r3, cy3 - r3, cx3 + r3, cy3 + r3], fill=(255, 215, 0, 45))

    blurred_light = light_layer.filter(ImageFilter.GaussianBlur(130))
    img.alpha_composite(blurred_light)

    # Floating stadium dust particles
    draw = ImageDraw.Draw(img)
    np.random.seed(42)
    for i in range(40):
        px = int((np.sin(i * 1.7 + frame_idx * 0.02) * 0.5 + 0.5) * width)
        py = int(((i * 57 + frame_idx * 1.6) % height))
        p_alpha = int(45 + 35 * math.sin(i + frame_idx * 0.05))
        p_size = 2 + (i % 3)
        draw.ellipse([px, py, px + p_size, py + p_size], fill=(255, 255, 255, p_alpha))

    return img

def create_badge_pill(club_name, size=(160, 160)):
    """Creates a circular card container for a club crest."""
    container = Image.new("RGBA", (size[0] + 40, size[1] + 40), (0, 0, 0, 0))
    draw = ImageDraw.Draw(container)
    
    cx, cy = container.width // 2, container.height // 2
    r = size[0] // 2 + 10
    
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(16, 22, 38, 255), outline=(0, 240, 255, 220), width=5)
    
    badge = get_club_badge(club_name, size=size)
    bx = (container.width - size[0]) // 2
    by = (container.height - size[1]) // 2
    container.alpha_composite(badge, (bx, by))
    return container

def create_flag_pill(nationality, size=(160, 160)):
    """Creates a container holding a clean vector country flag."""
    container = Image.new("RGBA", (size[0] + 40, size[1] + 40), (0, 0, 0, 0))
    draw = ImageDraw.Draw(container)
    
    cx, cy = container.width // 2, container.height // 2
    r = size[0] // 2 + 10
    
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(16, 22, 38, 255), outline=(255, 215, 0, 220), width=5)
    
    flag = draw_vector_flag(nationality, size=size)
    bx = (container.width - size[0]) // 2
    by = (container.height - size[1]) // 2
    container.alpha_composite(flag, (bx, by))
    return container

def draw_arrow_connector(draw, center_x, center_y, pulse):
    """Draws a crisp neon bidirectional exchange connector."""
    color = (57, 255, 20, 255) if pulse > 0 else (0, 240, 255, 255)
    w = 40
    
    y1 = center_y - 14
    draw.line([(center_x - w, y1), (center_x + w - 10, y1)], fill=color, width=6)
    draw.polygon([(center_x + w - 12, y1 - 10), (center_x + w + 6, y1), (center_x + w - 12, y1 + 10)], fill=color)
    
    y2 = center_y + 14
    draw.line([(center_x - w + 10, y2), (center_x + w, y2)], fill=color, width=6)
    draw.polygon([(center_x - w + 12, y2 - 10), (center_x - w - 6, y2), (center_x - w + 12, y2 + 10)], fill=color)

def draw_plus_connector(draw, center_x, center_y, pulse):
    """Draws a glowing gold plus connector."""
    color = (255, 215, 0, 255) if pulse > 0 else (57, 255, 20, 255)
    size = 28
    draw.line([(center_x - size, center_y), (center_x + size, center_y)], fill=color, width=8)
    draw.line([(center_x, center_y - size), (center_x, center_y + size)], fill=color, width=8)

def render_rarity_frame(data, frame_idx, total_frames):
    """Renders a single 1080x1920 video frame."""
    bg = draw_stadium_background(WIDTH, HEIGHT, frame_idx, total_frames)
    draw = ImageDraw.Draw(bg)

    t = (frame_idx / total_frames) * 2 * math.pi
    pulse = math.sin(t)

    # 1. TOP HEADER PILL
    header_w = 700
    header_h = 80
    header_x = (WIDTH - header_w) // 2
    header_y = 175
    
    glow_color = (255, 0, 85, 255) if (frame_idx // 15) % 2 == 0 else (255, 215, 0, 255)
    draw.rounded_rectangle([header_x, header_y, header_x + header_w, header_y + header_h], radius=40, fill=(20, 14, 28, 245), outline=glow_color, width=4)
    font_header = get_font(40, bold=True)
    draw.text((WIDTH // 2, header_y + header_h // 2), "BALL KNOWLEDGE TEST", fill=(255, 255, 255, 255), font=font_header, anchor="mm")

    # 2. CENTER BADGES / CRESTS AREA
    badge_y = 295
    if data["mode"] == "player_chain":
        badge1 = create_badge_pill(data["entity_1"], size=(175, 175))
        badge2 = create_badge_pill(data["entity_2"], size=(175, 175))
        
        b1_x = WIDTH // 2 - 275
        b2_x = WIDTH // 2 + 65
        bg.alpha_composite(badge1, (b1_x, badge_y))
        bg.alpha_composite(badge2, (b2_x, badge_y))
        
        draw_arrow_connector(draw, WIDTH // 2, badge_y + 105, pulse)
        
        font_cname = get_font(32, bold=True)
        draw.text((b1_x + badge1.width // 2, badge_y + badge1.height + 15), data["entity_1"].upper(), fill=(225, 235, 250, 255), font=font_cname, anchor="mm")
        draw.text((b2_x + badge2.width // 2, badge_y + badge2.height + 15), data["entity_2"].upper(), fill=(225, 235, 250, 255), font=font_cname, anchor="mm")

    else: # passport_fc
        badge1 = create_badge_pill(data["entity_1"], size=(175, 175))
        flag1 = create_flag_pill(data["entity_2"], size=(175, 175))
        
        b1_x = WIDTH // 2 - 275
        b2_x = WIDTH // 2 + 65
        bg.alpha_composite(badge1, (b1_x, badge_y))
        bg.alpha_composite(flag1, (b2_x, badge_y))
        
        draw_plus_connector(draw, WIDTH // 2, badge_y + 105, pulse)
        
        font_cname = get_font(32, bold=True)
        draw.text((b1_x + badge1.width // 2, badge_y + badge1.height + 15), data["entity_1"].upper(), fill=(225, 235, 250, 255), font=font_cname, anchor="mm")
        draw.text((b2_x + flag1.width // 2, badge_y + flag1.height + 15), data["entity_2"].upper(), fill=(225, 235, 250, 255), font=font_cname, anchor="mm")

    # 3. MAIN HOOK QUESTION CARD
    card_w = 950
    card_h = 390
    card_x = (WIDTH - card_w) // 2
    card_y = 635
    
    draw.rounded_rectangle([card_x, card_y, card_x + card_w, card_y + card_h], radius=32, fill=(14, 20, 34, 245), outline=(0, 240, 255, 180), width=4)

    font_main_q = get_font(52, bold=True)
    font_sub_q = get_font(42, bold=True)
    
    draw.text((WIDTH // 2, card_y + 80), "Name ONE Player", fill=(255, 255, 255, 255), font=font_main_q, anchor="mm")
    
    if data["mode"] == "player_chain":
        draw.text((WIDTH // 2, card_y + 150), "who played for BOTH clubs", fill=(0, 240, 255, 255), font=font_sub_q, anchor="mm")
    else:
        draw.text((WIDTH // 2, card_y + 150), f"from {data['entity_2']} to play for {data['entity_1']}", fill=(255, 215, 0, 255), font=font_sub_q, anchor="mm")
        
    draw.text((WIDTH // 2, card_y + 235), "that NO ONE ELSE", fill=(255, 0, 85, 255), font=font_main_q, anchor="mm")
    draw.text((WIDTH // 2, card_y + 310), "in the comments will say...", fill=(255, 255, 255, 255), font=font_sub_q, anchor="mm")

    # 4. STATS / POOL SIZE INDICATOR
    stats_y = 1070
    font_stats = get_font(34, bold=True)
    pool_str = f"TOTAL POOL: {data['pool_size']} PLAYERS IN HISTORY"
    draw.rounded_rectangle([WIDTH // 2 - 380, stats_y, WIDTH // 2 + 380, stats_y + 60], radius=16, fill=(22, 30, 48, 230), outline=(255, 255, 255, 30), width=2)
    draw.text((WIDTH // 2, stats_y + 30), pool_str, fill=(57, 255, 20, 255), font=font_stats, anchor="mm")

    # 5. SEED PLAYER HIGHLIGHT CARD ("I'LL START...")
    seed_w = 900
    seed_h = 240
    seed_x = (WIDTH - seed_w) // 2
    seed_y = 1175
    
    seed_pulse_border = (57, 255, 20, int(200 + 55 * pulse))
    draw.rounded_rectangle([seed_x, seed_y, seed_x + seed_w, seed_y + seed_h], radius=28, fill=(10, 16, 26, 250), outline=seed_pulse_border, width=5)

    font_start = get_font(36, bold=True)
    draw.text((WIDTH // 2, seed_y + 60), "I'll start with...", fill=(190, 210, 235, 255), font=font_start, anchor="mm")

    font_seed_name = get_font(56, bold=True)
    seed_tag = f" ({data['seed_country_code']})" if data.get('seed_country_code') else ""
    seed_full = f"{data['seed_player']}{seed_tag}"
    draw.text((WIDTH // 2, seed_y + 145), seed_full, fill=(57, 255, 20, 255), font=font_seed_name, anchor="mm")

    # 6. FOOTER CALL-TO-ACTION
    cta_y = 1500
    font_cta1 = get_font(42, bold=True)
    draw.text((WIDTH // 2, cta_y), "CAN YOU BEAT THIS RARITY?", fill=(255, 215, 0, 255), font=font_cta1, anchor="mm")
    
    font_cta2 = get_font(34, bold=False)
    draw.text((WIDTH // 2, cta_y + 60), "Drop your answer before reading others!", fill=(255, 255, 255, 255), font=font_cta2, anchor="mm")

    # Brand badge at bottom
    font_brand = get_font(30, bold=True)
    draw.text((WIDTH // 2, HEIGHT - 180), f"PLAYMAKER ARCADE • PUZZLE #{data['game_day']}", fill=(0, 240, 255, 220), font=font_brand, anchor="mm")
    font_url = get_font(26, bold=False)
    draw.text((WIDTH // 2, HEIGHT - 135), "Daily Live Games: playmaker.football", fill=(160, 175, 195, 200), font=font_url, anchor="mm")

    return bg

def generate_rarity_audio(duration_sec, output_wav_path):
    """Generates an upbeat electronic groove with opening arcade chime."""
    total_samples = int(SAMPLE_RATE * duration_sec)
    audio = np.zeros(total_samples, dtype=np.float32)
    t = np.linspace(0, duration_sec, total_samples, endpoint=False)

    # 1. Opening 3-chord arcade chime (0.0s - 0.6s)
    chime_freqs = [523.25, 659.25, 783.99, 1046.50]
    for idx, freq in enumerate(chime_freqs):
        start_t = idx * 0.12
        end_t = start_t + 0.45
        s_idx = int(start_t * SAMPLE_RATE)
        e_idx = min(int(end_t * SAMPLE_RATE), total_samples)
        sub_t = t[s_idx:e_idx] - start_t
        chime_wave = np.sin(2 * np.pi * freq * sub_t) * np.exp(-sub_t * 9) * 0.4
        audio[s_idx:e_idx] += chime_wave

    # 2. 120 BPM Bass & Kick Pulse
    bpm = 120
    beat_dur = 60.0 / bpm
    num_beats = int(duration_sec / beat_dur)
    
    for b in range(num_beats):
        b_time = b * beat_dur
        s_idx = int(b_time * SAMPLE_RATE)
        kick_dur = 0.18
        e_idx = min(int((b_time + kick_dur) * SAMPLE_RATE), total_samples)
        sub_t = t[s_idx:e_idx] - b_time
        
        # Kick sweep (120Hz -> 45Hz)
        freq_sweep = 45.0 + 80.0 * np.exp(-sub_t * 30)
        kick = np.sin(2 * np.pi * freq_sweep * sub_t) * np.exp(-sub_t * 16) * 0.5
        audio[s_idx:e_idx] += kick

        # Subtle hi-hat on upbeat
        hat_time = b_time + (beat_dur / 2.0)
        h_s = int(hat_time * SAMPLE_RATE)
        h_e = min(int((hat_time + 0.04) * SAMPLE_RATE), total_samples)
        if h_s < total_samples:
            hat_t = t[h_s:h_e] - hat_time
            hat = (np.random.rand(len(hat_t)) * 2 - 1) * np.exp(-hat_t * 90) * 0.15
            audio[h_s:h_e] += hat

    # Normalize audio
    max_val = np.max(np.abs(audio))
    if max_val > 0.01:
        audio = (audio / max_val) * 0.90
        
    audio_pcm = (audio * 32767).astype(np.int16)
    wavfile.write(output_wav_path, SAMPLE_RATE, audio_pcm)
    return output_wav_path

def extract_puzzle_data(game_type, day=1, step=None, custom_seed=None):
    """Extracts challenge data and seed player from daily CSVs."""
    if game_type == "player_chain":
        csv_path = os.path.join(BASE_DIR, "daily_player_chain_games.csv")
        df = pd.read_csv(csv_path)
        day_rows = df[df["game_day"] == day]
        if day_rows.empty:
            day_rows = df[df["game_day"] == 1]
            day = 1
        
        target_step = step if step is not None else 2
        step_row = day_rows[day_rows["step_number"] == target_step]
        if step_row.empty:
            step_row = day_rows.iloc[1:2]
        else:
            step_row = step_row.iloc[0:1]
            
        row = step_row.iloc[0]
        clubs = json.loads(row["active_clubs"])
        valid_players = json.loads(row["valid_players"])
        
        seed_player = custom_seed
        if not seed_player:
            candidates = [p for p in valid_players if p != row["target_player"]]
            seed_player = candidates[len(candidates) // 2] if candidates else valid_players[0]

        return {
            "mode": "player_chain",
            "entity_1": clubs[0],
            "entity_2": clubs[1] if len(clubs) > 1 else clubs[0],
            "seed_player": seed_player,
            "seed_country_code": "",
            "pool_size": len(valid_players),
            "game_day": int(day),
            "valid_players": valid_players
        }

    else: # passport_fc
        csv_path = os.path.join(BASE_DIR, "daily_passport_fc_games.csv")
        df = pd.read_csv(csv_path)
        day_rows = df[df["game_day"] == day]
        if day_rows.empty:
            day_rows = df[df["game_day"] == 1]
            day = 1
            
        target_step = step if step is not None else 1
        step_row = day_rows[day_rows["step_number"] == target_step]
        if step_row.empty:
            step_row = day_rows.iloc[0:1]
            
        row = step_row.iloc[0]
        club = row["club"]
        nationality = row["nationality"]
        valid_players = json.loads(row["valid_players"])
        
        seed_player = custom_seed
        if not seed_player:
            seed_player = valid_players[len(valid_players) // 2] if len(valid_players) > 1 else valid_players[0]

        code = COUNTRY_CODES.get(nationality.strip().title(), nationality[:3].upper())
        return {
            "mode": "passport_fc",
            "entity_1": club,
            "entity_2": nationality,
            "seed_player": seed_player,
            "seed_country_code": code,
            "pool_size": int(row["pool_size"]),
            "game_day": int(day),
            "valid_players": valid_players
        }

def generate_social_copy(data):
    """Generates viral Instagram/TikTok captions with hooks and hashtags."""
    if data["mode"] == "player_chain":
        caption = (
            f"🚨 BALL KNOWLEDGE TEST 🚨\n\n"
            f"Name ONE player who played for BOTH {data['entity_1']} and {data['entity_2']} "
            f"that NO ONE ELSE in the comments will say.\n\n"
            f"I'll start... {data['seed_player']}\n\n"
            f"👀 Let's see who has the best ball knowledge! Drop yours below 👇\n\n"
            f"⚽️ Play today's full Player Chain puzzle at the link in bio!\n\n"
            f"#football #soccer #ballknowledge #trivia #footballquiz #premierleague #laliga #seriea #championsleague #reels"
        )
    else:
        caption = (
            f"🚨 BALL KNOWLEDGE TEST 🚨\n\n"
            f"Name ONE {data['entity_2']} player to play for {data['entity_1']} "
            f"that NO ONE ELSE in the comments will say.\n\n"
            f"I'll start... {data['seed_player']} ({data.get('seed_country_code', '')})\n\n"
            f"👀 Only {data['pool_size']} players in history qualify! Drop yours below 👇\n\n"
            f"⚽️ Play today's full Passport FC puzzle at the link in bio!\n\n"
            f"#football #soccer #ballknowledge #trivia #footballquiz #barcelona #realmadrid #championsleague #reels"
        )
    return caption

def render_video(data, output_path, duration=DURATION_SEC, fps=FPS, add_audio=True):
    """Renders all frames and encodes with FFmpeg and audio track."""
    total_frames = int(duration * fps)
    print(f"🎬 Rendering {total_frames} frames (1080x1920 @ {fps}fps) -> {output_path}")

    temp_raw = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
    temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video_writer = cv2.VideoWriter(temp_raw, fourcc, fps, (WIDTH, HEIGHT))

    for frame_idx in range(total_frames):
        if frame_idx % 45 == 0:
            print(f"  Frame {frame_idx}/{total_frames} ({frame_idx/total_frames*100:.1f}%)")
        pil_frame = render_rarity_frame(data, frame_idx, total_frames)
        rgb_frame = pil_frame.convert("RGB")
        bgr_frame = cv2.cvtColor(np.array(rgb_frame), cv2.COLOR_RGB2BGR)
        video_writer.write(bgr_frame)

    video_writer.release()
    print("✅ Frame rendering complete. Synthesizing audio track...")

    if add_audio:
        generate_rarity_audio(duration, temp_wav)
        cmd = [
            FFMPEG_EXE, "-y",
            "-i", temp_raw,
            "-i", temp_wav,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            output_path
        ]
    else:
        cmd = [
            FFMPEG_EXE, "-y",
            "-i", temp_raw,
            "-c:v", "libx264",
            "-pix_fmt", "yuv420p",
            "-preset", "fast",
            "-crf", "18",
            "-movflags", "+faststart",
            output_path
        ]
        
    subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    
    for p in [temp_raw, temp_wav]:
        if os.path.exists(p):
            try:
                os.remove(p)
            except Exception:
                pass

    print(f"🎉 Successfully generated video: {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Render Reverse Rarity Short Video (Format 5)")
    parser.add_argument("--game", choices=["player_chain", "passport_fc"], default="player_chain", help="Game type")
    parser.add_argument("--day", type=int, default=1, help="Daily puzzle day number")
    parser.add_argument("--step", type=int, default=None, help="Step number in puzzle")
    parser.add_argument("--seed", type=str, default=None, help="Custom seed player override")
    parser.add_argument("--output", type=str, default=None, help="Output MP4 file path")
    parser.add_argument("--duration", type=float, default=DURATION_SEC, help="Video duration in seconds")
    parser.add_argument("--fps", type=int, default=FPS, help="Frames per second")
    args = parser.parse_args()

    data = extract_puzzle_data(args.game, day=args.day, step=args.step, custom_seed=args.seed)
    
    if not args.output:
        os.makedirs(os.path.join(BASE_DIR, "output_shorts"), exist_ok=True)
        filename = f"rarity_{args.game}_day{data['game_day']}_{args.step or 1}.mp4"
        output_path = os.path.join(BASE_DIR, "output_shorts", filename)
    else:
        output_path = args.output

    print(f"\n--- [PUZZLE SUMMARY: {args.game.upper()}] ---")
    print(f"Entity 1: {data['entity_1']}")
    print(f"Entity 2: {data['entity_2']}")
    print(f"Seed Player: {data['seed_player']}")
    print(f"Pool Size: {data['pool_size']} Players")
    print(f"-----------------------------------------\n")

    render_video(data, output_path, duration=args.duration, fps=args.fps, add_audio=True)

    caption = generate_social_copy(data)
    print("\n📝 --- [INSTAGRAM / TIKTOK READY CAPTION] ---")
    print(caption)
    print("---------------------------------------------\n")

if __name__ == "__main__":
    main()
