#!/usr/bin/env python3
"""
Playmaker Organic UGC Short Video Generator (9:16 Vertical Video).
Renders authentic, minimalist, human-feeling Instagram Reels / TikTok shorts:
Clean bold white text with dark outline over real casual B-roll footage (freestyle skills, pitch drills).
Directly extracts Step 2 from daily Player Chain & Passport FC puzzles.
Guarantees unique, non-repeating B-roll videos across daily runs.
"""

import os
import sys
import glob
import math
import json
import random
import argparse
import datetime
import tempfile
import subprocess
import numpy as np
import cv2
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from scripts.broll_manager import select_broll_clip

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"

WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION_SEC = 7.0

# Country Flag Emojis
COUNTRY_FLAGS = {
    "France": "🇫🇷", "Argentina": "🇦🇷", "Brazil": "🇧🇷", "Germany": "🇩🇪",
    "Spain": "🇪🇸", "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "Italy": "🇮🇹", "Netherlands": "🇳🇱",
    "Portugal": "🇵🇹", "Belgium": "🇧🇪", "Croatia": "🇭🇷", "Uruguay": "🇺🇾",
    "Colombia": "🇨🇴", "Ivory Coast": "🇨🇮", "Nigeria": "🇳🇬", "Senegal": "🇸🇳",
    "Ghana": "🇬🇭", "Cameroon": "🇨🇲", "Egypt": "🇪🇬", "Morocco": "🇲🇦",
    "Algeria": "🇩🇿", "Japan": "🇯🇵", "South Korea": "🇰🇷", "Australia": "🇦🇺",
    "United States": "🇺🇸", "Mexico": "🇲🇽", "Chile": "🇨🇱", "Sweden": "🇸🇪",
    "Norway": "🇳🇴", "Denmark": "🇩🇰", "Poland": "🇵🇱", "Austria": "🇦🇹",
    "Switzerland": "SUI", "Turkey": "TUR", "Greece": "GRE", "Ukraine": "UKR",
    "Serbia": "SRB", "Czech Republic": "CZE", "Scotland": "SCO", "Wales": "WAL",
    "Iceland": "ISL", "Bosnia": "BIH", "Paraguay": "PAR", "Ecuador": "ECU"
}

def get_font(size, bold=True):
    """Loads clean, modern sans-serif typography matching Instagram native text."""
    font_paths = [
        os.path.join(BASE_DIR, "assets", "fonts", "Arial-Bold.ttf" if bold else "Arial.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
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
    try:
        return ImageFont.truetype("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf", size)
    except Exception:
        pass
    return ImageFont.load_default()

def draw_text_with_outline_and_shadow(draw, position, text, font, fill_color=(255, 255, 255, 255), stroke_color=(0, 0, 0, 240), stroke_width=6, anchor="mm"):
    """Draws crisp white text with strong black outline and subtle drop shadow for perfect readability on any video background."""
    x, y = position
    shadow_offset = stroke_width + 4
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(0, 0, 0, 150), anchor=anchor)
    draw.text((x, y), text, font=font, fill=fill_color, stroke_width=stroke_width, stroke_fill=stroke_color, anchor=anchor)

def get_today_puzzle_day(game_id):
    """Calculates today's puzzle number based on games.json configuration."""
    games_json_path = os.path.join(BASE_DIR, "games.json")
    if os.path.exists(games_json_path):
        with open(games_json_path, "r", encoding="utf-8") as f:
            games = json.load(f)
        for g in games:
            if g["id"] == game_id:
                launch_str = g.get("launchDate", "2026-07-10")
                launch_d = datetime.datetime.strptime(launch_str, "%Y-%m-%d").date()
                today = datetime.date.today()
                diff = (today - launch_d).days
                return (diff % 180) + 1 if diff >= 0 else 1
    return 1

def extract_puzzle_data(game_type, day=None, custom_seed=None):
    """Extracts Step 2 challenge data and a random right answer from daily CSVs."""
    if day is None:
        day = get_today_puzzle_day(game_type)

    if game_type == "player_chain":
        csv_path = os.path.join(BASE_DIR, "daily_player_chain_games.csv")
        df = pd.read_csv(csv_path)
        day_rows = df[df["game_day"] == day]
        if day_rows.empty:
            day_rows = df[df["game_day"] == 1]
            day = 1
        
        step_row = day_rows[day_rows["step_number"] == 2]
        if step_row.empty:
            step_row = day_rows.iloc[1:2]
        else:
            step_row = step_row.iloc[0:1]
            
        row = step_row.iloc[0]
        clubs = json.loads(row["active_clubs"])
        valid_players = json.loads(row["valid_players"])
        target_player = row.get("target_player", "")
        
        candidates = [p for p in valid_players if p != target_player]
        if not candidates:
            candidates = valid_players
            
        seed_player = custom_seed if custom_seed else random.choice(candidates)

        return {
            "mode": "player_chain",
            "entity_1": clubs[0],
            "entity_2": clubs[1] if len(clubs) > 1 else clubs[0],
            "is_country": len(clubs) > 1 and clubs[1] in COUNTRY_FLAGS,
            "seed_player": seed_player,
            "pool_size": len(valid_players),
            "game_day": int(day)
        }

    else: # passport_fc
        csv_path = os.path.join(BASE_DIR, "daily_passport_fc_games.csv")
        df = pd.read_csv(csv_path)
        day_rows = df[df["game_day"] == day]
        if day_rows.empty:
            day_rows = df[df["game_day"] == 1]
            day = 1
            
        step_row = day_rows[day_rows["step_number"] == 2]
        if step_row.empty:
            step_row = day_rows.iloc[1:2]
        else:
            step_row = step_row.iloc[0:1]
            
        row = step_row.iloc[0]
        club = row["club"]
        nationality = row["nationality"]
        valid_players = json.loads(row["valid_players"])
        
        seed_player = custom_seed if custom_seed else random.choice(valid_players)

        return {
            "mode": "passport_fc",
            "entity_1": club,
            "entity_2": nationality,
            "seed_player": seed_player,
            "pool_size": int(row["pool_size"]),
            "game_day": int(day)
        }

def center_crop_and_fill(frame, target_w=WIDTH, target_h=HEIGHT):
    """Scales and center-crops a frame to perfectly fill target_w x target_h without stretching."""
    fh, fw = frame.shape[:2]
    scale = max(target_w / fw, target_h / fh)
    nw, nh = int(round(fw * scale)), int(round(fh * scale))
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    x1 = (nw - target_w) // 2
    y1 = (nh - target_h) // 2
    return resized[y1:y1+target_h, x1:x1+target_w]

def render_ugc_video(data, output_path, bg_video_path=None, duration=DURATION_SEC, fps=FPS):
    """Renders authentic clean white text over background video."""
    total_frames = int(duration * fps)
    
    if not bg_video_path or not os.path.exists(bg_video_path):
        raise FileNotFoundError(f"❌ Background video file not found: {bg_video_path}")

    cap = cv2.VideoCapture(bg_video_path)
    if not cap.isOpened():
        raise IOError(f"❌ Could not open background video: {bg_video_path}")

    temp_raw = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    video_writer = cv2.VideoWriter(temp_raw, fourcc, fps, (WIDTH, HEIGHT))

    font_header = get_font(60, bold=True)
    font_main = get_font(58, bold=True)
    font_highlight = get_font(64, bold=True)
    font_seed = get_font(58, bold=True)
    font_cta = get_font(42, bold=True)

    print(f"🎬 Rendering {total_frames} frames (UGC Minimalist Style) -> {output_path}")

    for frame_idx in range(total_frames):
        if frame_idx % 45 == 0:
            print(f"  Frame {frame_idx}/{total_frames} ({frame_idx/total_frames*100:.1f}%)")

        ret, frame = cap.read()
        if not ret:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            
        if not ret:
            raise IOError("❌ Failed to read frame from background video")

        # Smart center-crop to 1080x1920
        cropped_bgr = center_crop_and_fill(frame, WIDTH, HEIGHT)
        frame_rgb = cv2.cvtColor(cropped_bgr, cv2.COLOR_BGR2RGB)
        bg_img = Image.fromarray(frame_rgb)

        # Subtle 20% dark overlay for guaranteed text readability
        dim = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 50))
        bg_img.paste(dim, (0, 0), dim)

        draw = ImageDraw.Draw(bg_img)

        # 1. TOP HEADER
        draw_text_with_outline_and_shadow(draw, (WIDTH // 2, 480), "BALL KNOWLEDGE TEST", font_header, stroke_width=6)

        # 2. MAIN PROMPT
        if data["mode"] == "player_chain":
            if data.get("is_country"):
                draw_text_with_outline_and_shadow(draw, (WIDTH // 2, 680), f"Name ONE {data['entity_2']} player", font_main, stroke_width=5)
                draw_text_with_outline_and_shadow(draw, (WIDTH // 2, 770), f"who played for {data['entity_1']}", font_highlight, stroke_width=6)
            else:
                draw_text_with_outline_and_shadow(draw, (WIDTH // 2, 680), "Name ONE player", font_main, stroke_width=5)
                draw_text_with_outline_and_shadow(draw, (WIDTH // 2, 765), "who played for BOTH", font_main, stroke_width=5)
                clubs_text = f"{data['entity_1']} & {data['entity_2']}"
                draw_text_with_outline_and_shadow(draw, (WIDTH // 2, 865), clubs_text, font_highlight, stroke_width=6)
            
            draw_text_with_outline_and_shadow(draw, (WIDTH // 2, 970), "no one else in the comments will say", font_main, stroke_width=5)
            
            seed_text = f"I'll start... {data['seed_player']}"
            draw_text_with_outline_and_shadow(draw, (WIDTH // 2, 1180), seed_text, font_seed, stroke_width=5)
        else:
            draw_text_with_outline_and_shadow(draw, (WIDTH // 2, 680), f"Name ONE {data['entity_2']} player", font_main, stroke_width=5)
            draw_text_with_outline_and_shadow(draw, (WIDTH // 2, 770), f"who played for {data['entity_1']}", font_highlight, stroke_width=6)
            draw_text_with_outline_and_shadow(draw, (WIDTH // 2, 875), "no one else in the comments will say", font_main, stroke_width=5)
            
            seed_text = f"I'll start... {data['seed_player']}"
            draw_text_with_outline_and_shadow(draw, (WIDTH // 2, 1120), seed_text, font_seed, stroke_width=5)

        # 3. SUBTLE CTA FOOTER
        draw_text_with_outline_and_shadow(draw, (WIDTH // 2, HEIGHT - 240), "Drop yours in the comments", font_cta, stroke_width=4)

        rgb_frame = bg_img.convert("RGB")
        bgr_frame = cv2.cvtColor(np.array(rgb_frame), cv2.COLOR_RGB2BGR)
        video_writer.write(bgr_frame)

    cap.release()
    video_writer.release()

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
    
    if os.path.exists(temp_raw):
        os.remove(temp_raw)

    print(f"🎉 Successfully generated UGC video: {output_path}")

def generate_social_copy(data):
    """Generates viral Instagram/TikTok captions."""
    if data["mode"] == "player_chain":
        if data.get("is_country"):
            caption = (
                f"Name ONE {data['entity_2']} player to play for {data['entity_1']} "
                f"that NO ONE ELSE in the comments will say.\n\n"
                f"I'll start... {data['seed_player']}\n\n"
                f"Drop yours below 👇⚽️\n\n"
                f"Play today's full Player Chain puzzle at the link in bio!\n\n"
                f"#football #soccer #ballknowledge #trivia #footballquiz #premierleague #laliga #seriea #championsleague #reels"
            )
        else:
            caption = (
                f"Name ONE player who played for BOTH {data['entity_1']} and {data['entity_2']} "
                f"that NO ONE ELSE in the comments will say.\n\n"
                f"I'll start... {data['seed_player']}\n\n"
                f"Drop yours below 👇⚽️\n\n"
                f"Play today's full Player Chain puzzle at the link in bio!\n\n"
                f"#football #soccer #ballknowledge #trivia #footballquiz #premierleague #laliga #seriea #championsleague #reels"
            )
    else:
        caption = (
            f"Name ONE {data['entity_2']} player to play for {data['entity_1']} "
            f"that NO ONE ELSE in the comments will say.\n\n"
            f"I'll start... {data['seed_player']}\n\n"
            f"Drop yours below 👇⚽️\n\n"
            f"Play today's full Passport FC puzzle at the link in bio!\n\n"
            f"#football #soccer #ballknowledge #trivia #footballquiz #barcelona #realmadrid #championsleague #reels"
        )
    return caption

def main():
    parser = argparse.ArgumentParser(description="Render Organic UGC Reverse Rarity Short Video")
    parser.add_argument("--game", choices=["player_chain", "passport_fc"], default="player_chain", help="Game type")
    parser.add_argument("--day", type=int, default=None, help="Daily puzzle day number (defaults to today)")
    parser.add_argument("--seed", type=str, default=None, help="Custom seed player override")
    parser.add_argument("--bg", type=str, default=None, help="Path to raw background video clip")
    parser.add_argument("--exclude-bg", nargs="*", default=None, help="B-roll paths to exclude (e.g. used in video 1)")
    parser.add_argument("--output", type=str, default=None, help="Output MP4 file path")
    parser.add_argument("--upload", action="store_true", help="Automatically upload to YouTube Shorts and Instagram Reels")
    args = parser.parse_args()

    data = extract_puzzle_data(args.game, day=args.day, custom_seed=args.seed)
    
    if args.bg and os.path.exists(args.bg):
        bg_clip = args.bg
    else:
        bg_clip = select_broll_clip(exclude_paths=args.exclude_bg, game_id=args.game)

    if not args.output:
        os.makedirs(os.path.join(BASE_DIR, "output_shorts"), exist_ok=True)
        filename = f"ugc_rarity_{args.game}_day{data['game_day']}.mp4"
        output_path = os.path.join(BASE_DIR, "output_shorts", filename)
    else:
        output_path = args.output

    print(f"\n--- [UGC SHORT: {args.game.upper()} (DAY {data['game_day']})] ---")
    print(f"Entities: {data['entity_1']} + {data['entity_2']}")
    print(f"Random Seed Player: {data['seed_player']}")
    print(f"B-Roll Background: {bg_clip}")
    print(f"---------------------------------------------------\n")

    render_ugc_video(data, output_path, bg_video_path=bg_clip)

    caption = generate_social_copy(data)
    print("\n📝 --- [INSTAGRAM / TIKTOK READY CAPTION] ---")
    print(caption)
    print("---------------------------------------------\n")

    if args.upload:
        print("🚀 Auto-upload enabled: Publishing to YouTube Shorts & Instagram Reels...")
        
        if data["mode"] == "passport_fc" or data.get("is_country"):
            yt_title = f"Name ONE {data['entity_2']} player for {data['entity_1']} (No one else will say) ⚽️ #Shorts"
        else:
            yt_title = f"Name ONE player for {data['entity_1']} & {data['entity_2']} (No one else will say) ⚽️ #Shorts"
            
        cmd_yt = [
            sys.executable, os.path.join(BASE_DIR, "scripts", "youtube_uploader.py"),
            "--file", output_path,
            "--title", yt_title,
            "--privacy", "public"
        ]
        try:
            subprocess.run(cmd_yt, check=True)
        except Exception as e:
            print(f"⚠️ YouTube upload error: {e}")

        cmd_ig = [
            sys.executable, os.path.join(BASE_DIR, "scripts", "instagram_uploader.py"),
            "--file", output_path,
            "--caption", caption
        ]
        try:
            subprocess.run(cmd_ig, check=True)
        except Exception as e:
            print(f"⚠️ Instagram upload error: {e}")

if __name__ == "__main__":
    main()
