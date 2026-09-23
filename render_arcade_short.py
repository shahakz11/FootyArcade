#!/usr/bin/env python3
"""
Playmaker Arcade Video Generator (9:16 Vertical Video).
Renders high-octane sports broadcast HUD shorts for Instagram Reels, YouTube Shorts, and TikTok.
Directly composes 1080x1920 frames using Pillow, NumPy, OpenCV, and FFmpeg with official club badges.
"""

import os
import sys
import re
import math
import json
import asyncio
import tempfile
import subprocess
import datetime
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from scripts.badge_manager import get_club_badge, normalize_club_name
from narration_tts import (
    get_game_voice_script,
    pre_synthesize_voice_script,
    generate_narration_audio_track_from_cues,
    format_fee_spoken
)
from audio_sfx import build_audio_track, mux_audio_to_video

WIDTH = 1080
HEIGHT = 1920
FPS = 30

# Brand colors
NEON_GREEN = (57, 255, 20)       # #39FF14
CYAN_SHOCK = (0, 240, 255)       # #00F0FF
ACCENT_PINK = (255, 0, 85)       # #FF0055
GOLD_STAR   = (255, 215, 0)       # #FFD700
WHITE       = (255, 255, 255)
DARK_SURFACE = (18, 24, 38, 230)
CARD_BORDER  = (255, 255, 255, 40)

def get_font(size, bold=False):
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

def format_fee(fee):
    try:
        val = float(fee)
        if val >= 1_000_000:
            m = val / 1_000_000.0
            return f"€{m:.1f}M" if m % 1 != 0 else f"€{int(m)}M"
        elif val >= 1_000:
            return f"€{int(val/1000)}K"
        return f"€{int(val)}"
    except Exception:
        return str(fee)

def create_stadium_background(width=WIDTH, height=HEIGHT):
    """Creates a sleek, atmospheric dark sports stadium background."""
    img = Image.new("RGBA", (width, height), (10, 14, 22, 255))
    draw = ImageDraw.Draw(img)

    # Vertical gradient
    for y in range(height):
        ratio = y / height
        # subtle green tint at bottom pitch
        r = int(10 + 6 * ratio)
        g = int(14 + 20 * (ratio ** 1.8))
        b = int(22 + 15 * (1 - ratio))
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Stadium floodlight beams from top corners
    beam_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    bdraw = ImageDraw.Draw(beam_layer)
    # Left beam
    bdraw.polygon([(0, 0), (int(width * 0.45), height), (0, height)], fill=(0, 240, 255, 12))
    # Right beam
    bdraw.polygon([(width, 0), (width, height), (int(width * 0.55), height)], fill=(57, 255, 20, 12))
    
    # Pitch line arcs at bottom
    bdraw.arc([int(width * 0.1), height - 260, int(width * 0.9), height + 400], start=180, end=360, fill=(255, 255, 255, 20), width=3)
    bdraw.line([(0, height - 140), (width, height - 140)], fill=(255, 255, 255, 22), width=3)

    img = Image.alpha_composite(img, beam_layer)
    return img

def draw_player_silhouette(size=(220, 240)):
    """Generates a clean athletic player silhouette with subtle neon edge glow."""
    w, h = size
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(im)

    # Athletic torso & neck/head
    center_x = w // 2
    head_r = int(w * 0.22)
    head_cy = int(h * 0.30)
    draw.ellipse([center_x - head_r, head_cy - head_r, center_x + head_r, head_cy + head_r], fill=(22, 30, 48, 240))

    # Shoulders / jersey
    torso_top = int(h * 0.48)
    draw.chord([int(w * 0.05), torso_top, int(w * 0.95), int(h * 1.3)], start=180, end=360, fill=(22, 30, 48, 240))
    
    # Subtle inner glow line
    draw.ellipse([center_x - head_r, head_cy - head_r, center_x + head_r, head_cy + head_r], outline=(57, 255, 20, 100), width=2)
    return im

def render_transfer_card(from_club, to_club, fee_str, player_name=None, rank=None, is_mystery=False, mystery_countdown=None, card_width=920, card_height=180):
    """
    Renders an individual glassmorphism transfer card with official club crests.
    """
    card = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    bg_fill = (18, 24, 38, 235) if not is_mystery else (26, 20, 38, 245)
    border_color = (0, 240, 255, 180) if not is_mystery else (255, 215, 0, 220)
    border_width = 3 if not is_mystery else 4

    # Card background
    draw.rounded_rectangle([0, 0, card_width, card_height], radius=24, fill=bg_fill, outline=border_color, width=border_width)

    # Rank badge on top left corner
    if rank is not None:
        badge_w, badge_h = 70, 44
        badge_fill = (57, 255, 20, 240) if not is_mystery else (255, 215, 0, 255)
        badge_text_color = (0, 0, 0, 255)
        draw.rounded_rectangle([18, -4, 18 + badge_w, badge_h], radius=12, fill=badge_fill)
        font_rank = get_font(28, bold=True)
        draw.text((36, 6), f"#{rank}", fill=badge_text_color, font=font_rank)

    # Left: From Club Badge
    badge_size = (110, 110)
    from_badge = get_club_badge(from_club, size=badge_size)
    badge_y = (card_height - badge_size[1]) // 2
    card.alpha_composite(from_badge, (50, badge_y))

    # Right: To Club Badge
    to_badge = get_club_badge(to_club, size=badge_size)
    card.alpha_composite(to_badge, (card_width - 50 - badge_size[0], badge_y))

    # Center: Arrow & Transfer Fee
    center_x = card_width // 2
    font_fee = get_font(34, bold=True)
    draw.text((center_x, 52), fee_str, fill=(255, 255, 255, 255), font=font_fee, anchor="mm")

    # Neon arrow
    arrow_y = 88
    arrow_color = (57, 255, 20, 255) if not is_mystery else (255, 215, 0, 255)
    draw.line([(center_x - 55, arrow_y), (center_x + 45, arrow_y)], fill=arrow_color, width=5)
    draw.polygon([(center_x + 40, arrow_y - 8), (center_x + 58, arrow_y), (center_x + 40, arrow_y + 8)], fill=arrow_color)

    # Player Name or Mystery status
    font_player = get_font(36, bold=True)
    if is_mystery:
        # Mystery indicator with pulsing text or countdown
        if mystery_countdown is not None and mystery_countdown > 0:
            status_text = f"⏱️ GUESS IN {int(math.ceil(mystery_countdown))}s..."
            status_color = (255, 215, 0, 255)
        else:
            status_text = "❓ WHO IS NUMBER ONE? ❓"
            status_color = (255, 0, 85, 255)
        draw.text((center_x, 138), status_text, fill=status_color, font=font_player, anchor="mm")
    else:
        # Revealed player name with checkmark
        name_str = f"✔ {player_name.upper()}" if player_name else "✔ VERIFIED"
        draw.text((center_x, 138), name_str, fill=(57, 255, 20, 255), font=font_player, anchor="mm")

    return card

def render_mystery_spotlight_card(from_club, to_club, fee_str, countdown_sec, card_width=920, card_height=420):
    """
    Renders the dramatic large Mystery Centerpiece Card with player silhouette,
    circular countdown dial, and glowing mystery aura.
    """
    card = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    # Gold/Neon pulsating outline
    draw.rounded_rectangle([0, 0, card_width, card_height], radius=32, fill=(16, 22, 38, 250), outline=(255, 215, 0, 255), width=5)

    # Golden badge: NUMBER 1 RECORD SIGNING
    draw.rounded_rectangle([card_width // 2 - 200, -8, card_width // 2 + 200, 50], radius=16, fill=(255, 215, 0, 255))
    font_head = get_font(30, bold=True)
    draw.text((card_width // 2, 22), "🏆 #1 RECORD SIGNING", fill=(0, 0, 0, 255), font=font_head, anchor="mm")

    # Club Badges
    badge_size = (130, 130)
    from_badge = get_club_badge(from_club, size=badge_size)
    to_badge = get_club_badge(to_club, size=badge_size)
    card.alpha_composite(from_badge, (50, 100))
    card.alpha_composite(to_badge, (card_width - 50 - badge_size[0], 100))

    # Center: Fee and Arrow
    center_x = card_width // 2
    font_fee = get_font(46, bold=True)
    draw.text((center_x, 115), fee_str, fill=(255, 255, 255, 255), font=font_fee, anchor="mm")

    arrow_y = 155
    draw.line([(center_x - 65, arrow_y), (center_x + 55, arrow_y)], fill=(57, 255, 20, 255), width=6)
    draw.polygon([(center_x + 50, arrow_y - 10), (center_x + 72, arrow_y), (center_x + 50, arrow_y + 10)], fill=(57, 255, 20, 255))

    # Center Silhouette
    sil = draw_player_silhouette(size=(190, 200))
    card.alpha_composite(sil, (center_x - 95, 175))

    # Circular Countdown Timer Dial
    timer_cy = 280
    dial_r = 52
    draw.ellipse([center_x - dial_r, timer_cy - dial_r, center_x + dial_r, timer_cy + dial_r], fill=(10, 14, 24, 245), outline=(57, 255, 20, 255), width=4)
    
    # Dynamic Arc countdown
    if countdown_sec is not None:
        rem_clamped = max(0.0, min(3.0, countdown_sec))
        frac = rem_clamped / 3.0
        angle = int(360 * frac)
        if angle > 0:
            draw.arc([center_x - dial_r, timer_cy - dial_r, center_x + dial_r, timer_cy + dial_r], start=-90, end=-90 + angle, fill=(255, 215, 0, 255), width=6)
        
        display_sec = int(math.ceil(rem_clamped)) if rem_clamped > 0 else 0
        timer_text = f"{display_sec}s" if display_sec > 0 else "0s"
        font_timer = get_font(42, bold=True)
        draw.text((center_x, timer_cy - 2), timer_text, fill=(57, 255, 20, 255), font=font_timer, anchor="mm")

    # Bottom Mystery Teaser Text
    font_teaser = get_font(34, bold=True)
    draw.text((center_x, 385), "CAN YOU NAME HIM BEFORE TIME OUT?", fill=(255, 215, 0, 255), font=font_teaser, anchor="mm")

    return card

def render_career_step_card(step_num, from_club, to_club, fee_str, is_mystery=False, mystery_countdown=None, card_width=920, card_height=170):
    """
    Renders a backwards career path card for Transfer Destination.
    """
    card = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    bg_fill = (18, 24, 38, 235) if not is_mystery else (30, 20, 42, 245)
    border_color = (57, 255, 20, 180) if not is_mystery else (255, 215, 0, 240)
    draw.rounded_rectangle([0, 0, card_width, card_height], radius=22, fill=bg_fill, outline=border_color, width=3)

    # Step indicator pill
    font_step = get_font(24, bold=True)
    draw.rounded_rectangle([20, 14, 130, 52], radius=10, fill=(0, 240, 255, 230))
    draw.text((75, 33), f"STEP {step_num}", fill=(0, 0, 0, 255), font=font_step, anchor="mm")

    # Badges
    badge_size = (100, 100)
    to_badge = get_club_badge(to_club, size=badge_size)
    from_badge = get_club_badge(from_club, size=badge_size) if not is_mystery else None

    card.alpha_composite(to_badge, (50, 48))

    center_x = card_width // 2
    # Arrow
    draw.line([(center_x - 50, 95), (center_x + 40, 95)], fill=(0, 240, 255, 255), width=5)
    draw.polygon([(center_x - 50, 87), (center_x - 68, 95), (center_x - 50, 103)], fill=(0, 240, 255, 255))
    
    font_sub = get_font(24, bold=False)
    draw.text((center_x, 62), "TRANSFERRED FROM", fill=(148, 163, 184, 255), font=font_sub, anchor="mm")

    if is_mystery:
        # Mystery box on right
        draw.rounded_rectangle([card_width - 160, 40, card_width - 40, 145], radius=16, fill=(255, 215, 0, 40), outline=(255, 215, 0, 240), width=3)
        font_q = get_font(52, bold=True)
        draw.text((card_width - 100, 92), "❓", font=font_q, anchor="mm")
        
        font_label = get_font(30, bold=True)
        draw.text((center_x, 130), "MYSTERY ORIGIN CLUB", fill=(255, 215, 0, 255), font=font_label, anchor="mm")
    else:
        card.alpha_composite(from_badge, (card_width - 50 - badge_size[0], 48))
        font_club = get_font(32, bold=True)
        draw.text((center_x, 130), normalize_club_name(from_club).upper(), fill=(255, 255, 255, 255), font=font_club, anchor="mm")

    return card

def render_top_header(title_text, subtitle_text="🔥 ONLY 1% CAN SOLVE THIS!"):
    """Renders the top neon arcade title banner."""
    header = Image.new("RGBA", (WIDTH, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(header)

    # Top Banner Box
    bx0, by0, bx1, by1 = 50, 40, WIDTH - 50, 180
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=24, fill=(10, 14, 26, 240), outline=NEON_GREEN, width=4)

    # Title text
    font_title = get_font(48, bold=True)
    draw.text((WIDTH // 2, 85), title_text.upper(), fill=WHITE, font=font_title, anchor="mm")

    # Subtitle pill
    pill_w, pill_h = 440, 40
    px0 = (WIDTH - pill_w) // 2
    draw.rounded_rectangle([px0, 135, px0 + pill_w, 135 + pill_h], radius=12, fill=(255, 0, 85, 240))
    font_sub = get_font(24, bold=True)
    draw.text((WIDTH // 2, 155), subtitle_text, fill=WHITE, font=font_sub, anchor="mm")

    return header

def render_bottom_cta():
    """Renders the bottom high-contrast call to action banner."""
    cta = Image.new("RGBA", (WIDTH, 220), (0, 0, 0, 0))
    draw = ImageDraw.Draw(cta)

    # CTA Button Box
    bx0, by0, bx1, by1 = 60, 20, WIDTH - 60, 130
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=26, fill=(10, 14, 26, 245), outline=CYAN_SHOCK, width=4)

    font_cta = get_font(42, bold=True)
    draw.text((WIDTH // 2, 75), "👇 COMMENT YOUR ANSWER", fill=NEON_GREEN, font=font_cta, anchor="mm")

    # Website link
    font_url = get_font(30, bold=True)
    draw.text((WIDTH // 2, 170), "playmaker.best", fill=(200, 210, 230, 240), font=font_url, anchor="mm")

    return cta

def load_game_payload(game_id, day_offset=0):
    """
    Loads the exact daily puzzle payload directly from the compiled game HTML files.
    This guarantees 100% parity with what players see on playmaker.best today.
    """
    if day_offset == 0:
        html_file = os.path.join(BASE_DIR, "games", f"{game_id}.html")
    else:
        suffix = f"_d{abs(day_offset)}" if day_offset < 0 else f"_f{day_offset}"
        html_file = os.path.join(BASE_DIR, "games", f"{game_id}{suffix}.html")
        if not os.path.exists(html_file):
            html_file = os.path.join(BASE_DIR, "games", f"{game_id}.html")

    if not os.path.exists(html_file):
        raise FileNotFoundError(f"Compiled game file {html_file} not found. Run fetch_daily.py first.")

    with open(html_file, "r", encoding="utf-8") as f:
        html = f.read()

    if game_id == "top_transfers":
        m = re.search(r'const\s+DAILY_TRANSFER_GAME\s*=\s*(\{[\s\S]*?\});', html)
        if not m:
            raise ValueError(f"DAILY_TRANSFER_GAME not found in {html_file}")
        data = json.loads(m.group(1))
        target_name = data.get("name", "Unknown")
        mode = data.get("mode", "club")
        raw_transfers = data.get("transfers", [])
        sorted_transfers = sorted(raw_transfers, key=lambda x: float(x.get("transfer_fee", 0)), reverse=True)
        return {
            "game_id": "top_transfers",
            "target_name": target_name,
            "mode": mode,
            "transfers": sorted_transfers[:5]
        }
    elif game_id == "transfer_destination":
        m = re.search(r'const\s+DAILY_DESTINATION_GAME\s*=\s*(\{[\s\S]*?\});', html)
        if not m:
            raise ValueError(f"DAILY_DESTINATION_GAME not found in {html_file}")
        data = json.loads(m.group(1))
        target_player = data.get("player_name", "Mystery Player")
        return {
            "game_id": "transfer_destination",
            "target_name": target_player,
            "nationality": data.get("nationality", ""),
            "position": data.get("position", ""),
            "transfers": data.get("transfers", [])
        }
    else:
        raise ValueError(f"Unsupported game_id: {game_id}")

async def render_arcade_video(game_id="top_transfers", output_path=None, force=False):
    """
    Synthesizes the complete 1080x1920 MP4 video for game_id using direct canvas rendering.
    """
    print(f"🎬 Initializing Arcade Video Synthesis for '{game_id}'...")
    payload = load_game_payload(game_id)
    target_name = payload["target_name"]
    date_str = datetime.date.today().strftime("%Y-%m-%d")

    if not output_path:
        sanitized = re.sub(r'[^\w\-]', '', target_name.replace(' ', '_'))
        output_path = os.path.join(BASE_DIR, f"output_arcade_{game_id}_{sanitized}_{date_str}.mp4")

    if not force and os.path.exists(output_path) and os.path.getsize(output_path) > 1000000:
        print(f"⚡ Video already exists: {output_path}. Skipping.")
        return output_path

    # 1. Synthesize Audio & Commentary
    voice_script = get_game_voice_script(game_id, target_name=target_name, extra_data=payload)
    
    with tempfile.TemporaryDirectory(prefix=f"arcade_{game_id}_") as temp_dir:
        print("🎙️ Pre-synthesizing voice cues...")
        cues = await pre_synthesize_voice_script(voice_script, temp_dir)
        for k, v in cues.items():
            print(f"   [{k}]: \"{v['text']}\" ({v['duration']:.2f}s)")

        # Timeline Layout (in seconds)
        # Total duration ~ 19.0 seconds
        TOTAL_DURATION = 19.0
        TOTAL_FRAMES = int(TOTAL_DURATION * FPS)

        cue_timeline = []
        sfx_timeline = []

        # Beat 1: Intro (0.0s to 3.5s)
        cue_timeline.append((cues["intro"]["wav_path"], 0.3))
        sfx_timeline.append(('whoosh', 0.1))

        # Beat 2: Warmup Clues (3.5s to 10.5s)
        if game_id == "top_transfers":
            cue_timeline.append((cues["guess_5"]["wav_path"], 3.5))
            sfx_timeline.append(('whoosh', 3.4))
            sfx_timeline.append(('correct', 5.5))

            cue_timeline.append((cues["guess_2"]["wav_path"], 7.0))
            sfx_timeline.append(('whoosh', 6.9))
            sfx_timeline.append(('correct', 9.0))

            # Beat 3: Mystery Cliffhanger (10.5s to 16.5s)
            cue_timeline.append((cues["cliffhanger"]["wav_path"], 10.5))
            sfx_timeline.append(('sub_drop', 10.4))
            sfx_timeline.append(('tick_3', 13.0))
            sfx_timeline.append(('tick_2', 14.0))
            sfx_timeline.append(('tick_1', 15.0))

            # Beat 4: Outro CTA (16.5s to 19.0s)
            cue_timeline.append((cues["outro"]["wav_path"], 16.2))
        else: # transfer_destination
            cue_timeline.append((cues["step_1"]["wav_path"], 3.5))
            sfx_timeline.append(('whoosh', 3.4))
            sfx_timeline.append(('correct', 5.5))

            cue_timeline.append((cues["step_2"]["wav_path"], 7.0))
            sfx_timeline.append(('whoosh', 6.9))
            sfx_timeline.append(('correct', 9.0))

            cue_timeline.append((cues["cliffhanger"]["wav_path"], 10.5))
            sfx_timeline.append(('sub_drop', 10.4))
            sfx_timeline.append(('tick_3', 13.0))
            sfx_timeline.append(('tick_2', 14.0))
            sfx_timeline.append(('tick_1', 15.0))

            cue_timeline.append((cues["outro"]["wav_path"], 16.2))

        # Build composite audio
        voice_wav = os.path.join(temp_dir, "master_voice.wav")
        generate_narration_audio_track_from_cues(cue_timeline, TOTAL_DURATION, voice_wav)
        
        master_audio_wav = os.path.join(temp_dir, "master_audio.wav")
        build_audio_track(sfx_timeline, TOTAL_DURATION, master_audio_wav, voice_wav_path=voice_wav)

        # 2. Render Video Frames
        print(f"🖼️ Rendering {TOTAL_FRAMES} high-resolution frames (1080x1920 @ {FPS}fps)...")
        raw_video_path = os.path.join(temp_dir, "video_silent.mp4")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        video_writer = cv2.VideoWriter(raw_video_path, fourcc, FPS, (WIDTH, HEIGHT))

        # Pre-render static base templates
        bg_base = create_stadium_background(WIDTH, HEIGHT)
        header_base = render_top_header(
            f"CAN YOU GUESS {target_name}'S RECORD TRANSFERS?" if game_id == "top_transfers" else f"GUESS {target_name}'S CAREER BACKWARDS!"
        )
        cta_base = render_bottom_cta()

        transfers = payload["transfers"]

        for f_idx in range(TOTAL_FRAMES):
            t = f_idx / FPS
            frame_img = bg_base.copy()
            frame_img.alpha_composite(header_base, (0, 40))

            if game_id == "top_transfers":
                # Card #5 (Warmup) enters at t=3.5s
                if t >= 3.5 and len(transfers) > 4:
                    t5 = transfers[4]
                    c5 = render_transfer_card(
                        from_club=t5.get("from_club_name", "Club A"),
                        to_club=t5.get("to_club_name") or target_name,
                        fee_str=format_fee(t5.get("transfer_fee", 0)),
                        player_name=t5.get("player_name", ""),
                        rank=5
                    )
                    frame_img.alpha_composite(c5, (80, 260))

                # Card #2 (Mid-tier) enters at t=7.0s
                if t >= 7.0 and len(transfers) > 1:
                    t2 = transfers[1]
                    c2 = render_transfer_card(
                        from_club=t2.get("from_club_name", "Club B"),
                        to_club=t2.get("to_club_name") or target_name,
                        fee_str=format_fee(t2.get("transfer_fee", 0)),
                        player_name=t2.get("player_name", ""),
                        rank=2
                    )
                    frame_img.alpha_composite(c2, (80, 470))

                # Card #1 (Centerpiece Mystery) enters at t=10.5s
                if t >= 10.5 and len(transfers) > 0:
                    t1 = transfers[0]
                    countdown_rem = max(0.0, 16.0 - t) if t < 16.0 else 0.0
                    c1 = render_mystery_spotlight_card(
                        from_club=t1.get("from_club_name", "Origin Club"),
                        to_club=t1.get("to_club_name") or target_name,
                        fee_str=format_fee(t1.get("transfer_fee", 0)),
                        countdown_sec=countdown_rem
                    )
                    frame_img.alpha_composite(c1, (80, 680))

            else: # transfer_destination
                # Step 1 enters at t=3.5s
                if t >= 3.5 and len(transfers) > 0:
                    s1 = transfers[0]
                    c1 = render_career_step_card(
                        step_num=1,
                        from_club=s1.get("from_club_name", "Previous Club"),
                        to_club=s1.get("to_club_name", "Current Club"),
                        fee_str=format_fee(s1.get("transfer_fee", 0))
                    )
                    frame_img.alpha_composite(c1, (80, 260))

                # Step 2 enters at t=7.0s
                if t >= 7.0 and len(transfers) > 1:
                    s2 = transfers[1]
                    c2 = render_career_step_card(
                        step_num=2,
                        from_club=s2.get("from_club_name", "Earlier Club"),
                        to_club=s2.get("to_club_name", s1.get("from_club_name", "Club")),
                        fee_str=format_fee(s2.get("transfer_fee", 0))
                    )
                    frame_img.alpha_composite(c2, (80, 460))

                # Step 3 (Mystery Origin Club) enters at t=10.5s
                if t >= 10.5 and len(transfers) > 0:
                    countdown_rem = max(0.0, 16.0 - t) if t < 16.0 else 0.0
                    s_mystery = transfers[-1]
                    c_myst = render_mystery_spotlight_card(
                        from_club="Mystery Origin",
                        to_club=s_mystery.get("to_club_name") or s_mystery.get("from_club_name", "First Club"),
                        fee_str=format_fee(s_mystery.get("transfer_fee", 0)) if s_mystery.get("transfer_fee") else "YOUTH / ACADEMY",
                        countdown_sec=countdown_rem
                    )
                    frame_img.alpha_composite(c_myst, (80, 660))

            # Bottom CTA is always visible or intensifies after mystery
            frame_img.alpha_composite(cta_base, (0, HEIGHT - 240))

            # Convert PIL to OpenCV frame (BGR)
            np_frame = np.array(frame_img.convert("RGB"))
            bgr_frame = cv2.cvtColor(np_frame, cv2.COLOR_RGB2BGR)
            video_writer.write(bgr_frame)

            if f_idx % 60 == 0:
                print(f"   Progress: {f_idx}/{TOTAL_FRAMES} frames ({int(f_idx/TOTAL_FRAMES*100)}%)...")

        video_writer.release()
        print("✅ Frame rendering complete! Muxing audio track...")

        # 3. Mux Audio to Video with FFmpeg
        res_video = mux_audio_to_video(raw_video_path, master_audio_wav, output_path)
        if res_video and os.path.exists(res_video):
            file_size_mb = os.path.getsize(res_video) / 1024 / 1024
            print(f"🎉 Successfully rendered Arcade Short: {res_video} ({file_size_mb:.2f} MB)")
            return res_video
        else:
            raise RuntimeError("FFmpeg audio-video muxing failed.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--game", default="top_transfers", choices=["top_transfers", "transfer_destination"])
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    asyncio.run(render_arcade_video(game_id=args.game, force=args.force))
