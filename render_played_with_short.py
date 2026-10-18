#!/usr/bin/env python3
"""
Playmaker "Played With" Vertical Video Generator (9:16 Vertical Short).
Renders high-retention vertical videos (1080x1920 @ 30fps) for the "Played With" daily football puzzle.

Key Features:
- Strict n-2 date selection logic protecting active gameplay
- 5-tier static clue ladder with difficulty-coded colors (#E53935 to #43A047)
- Adaptive typography scaling (44px down to 34px) so long names fit within 840px safe zone
- Progressive highlight animation culminating in prominent "WHO AM I?" terminal hook card
- Looped background audio muxing (-stream_loop -1 -shortest) with OpenCV + Pillow + imageio_ffmpeg
- Viral social copy and YouTube title generation (< 95 chars)
"""

import os
import sys
import math
import argparse
import datetime
import tempfile
import subprocess
from typing import Optional, List, Dict, Union, Any

import numpy as np
import cv2
import pandas as pd
from PIL import Image, ImageDraw, ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from scripts.broll_manager import select_broll_clip
from scripts.audio_manager import select_audio_track

try:
    import imageio_ffmpeg
    FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
except Exception:
    FFMPEG_EXE = "ffmpeg"

WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION_SEC = 7.5
MAX_SAFE_WIDTH = 840

LAUNCH_DATE = datetime.date(2026, 9, 27)
CSV_PATH = os.path.join(BASE_DIR, "daily_played_with_games.csv")

# 5-Tier Difficulty Color Palette:
# Step 1 (Hardest, 20th most frequent): Crimson #E53935
# Step 2 (10th most frequent): Dark Orange #FB8C00
# Step 3 (5th most frequent): Amber #FDD835
# Step 4 (2nd most frequent): Light Green #7CB342
# Step 5 (Easiest, Most frequent): Vibrant Green #43A047
DIFFICULTY_COLORS = {
    1: (229, 57, 53),    # Crimson #E53935
    2: (251, 140, 0),    # Orange #FB8C00
    3: (253, 216, 53),   # Amber #FDD835
    4: (124, 179, 66),   # Light Green #7CB342
    5: (67, 160, 71),    # Vibrant Green #43A047
}


def get_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont:
    """Loads clean sans-serif typography matching modern mobile interfaces."""
    font_paths = [
        os.path.join(BASE_DIR, "assets", "fonts", "Arial-Bold.ttf" if bold else "Arial.ttf"),
        "/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFNS.ttf"
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


def draw_text_with_outline_and_shadow(
    draw: ImageDraw.ImageDraw,
    position: tuple,
    text: str,
    font: ImageFont.ImageFont,
    fill_color: tuple = (255, 255, 255, 255),
    stroke_color: tuple = (0, 0, 0, 240),
    stroke_width: int = 5,
    anchor: str = "mm",
    shadow_offset: Optional[int] = None,
    shadow_color: tuple = (0, 0, 0, 160)
) -> None:
    """Draws text with stroke outline and drop shadow for maximum legibility over video."""
    x, y = position
    if shadow_offset is None:
        shadow_offset = stroke_width + 4
    draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=shadow_color, anchor=anchor)
    draw.text((x, y), text, font=font, fill=fill_color, stroke_width=stroke_width, stroke_fill=stroke_color, anchor=anchor)


def center_crop_and_fill(frame: np.ndarray, target_w: int = WIDTH, target_h: int = HEIGHT) -> np.ndarray:
    """Scales and center-crops a video frame to fill target_w x target_h without stretching."""
    fh, fw = frame.shape[:2]
    scale = max(target_w / fw, target_h / fh)
    nw, nh = int(round(fw * scale)), int(round(fh * scale))
    resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_LANCZOS4)
    x1 = (nw - target_w) // 2
    y1 = (nh - target_h) // 2
    return resized[y1:y1 + target_h, x1:x1 + target_w]


def get_n_minus_2_date(reference_date: Optional[datetime.date] = None) -> datetime.date:
    """Computes the target date two days prior to reference_date (defaults to today - 2 days)."""
    ref = reference_date if reference_date is not None else datetime.date.today()
    return ref - datetime.timedelta(days=2)


def get_puzzle_day_for_date(date_obj: datetime.date) -> int:
    """
    Maps calendar date to puzzle day (1 to 365) based on launchDate 2026-09-27.
    Cycle repeats cleanly modulo 365.
    """
    diff = (date_obj - LAUNCH_DATE).days
    if diff < 0:
        return 1
    return (diff % 365) + 1


def load_played_with_puzzle(day: Optional[int] = None, date_str: Optional[str] = None) -> Dict[str, Any]:
    """
    Loads 5-tier Played With puzzle from daily_played_with_games.csv.
    Raises ValueError on invalid day (< 1 or > 365) or malformed date_str.
    """
    if day is not None:
        try:
            day_int = int(day)
        except (ValueError, TypeError):
            raise ValueError(f"Day must be an integer, got {day}")
        if day_int < 1 or day_int > 365:
            raise ValueError(f"Day {day_int} is out of bounds (1..365)")
        puzzle_day = day_int
    elif date_str is not None:
        try:
            if isinstance(date_str, datetime.date):
                dt = date_str
            else:
                dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
        except Exception as e:
            raise ValueError(f"Invalid date format '{date_str}', expected YYYY-MM-DD: {e}")
        puzzle_day = get_puzzle_day_for_date(dt)
    else:
        target_date = get_n_minus_2_date()
        puzzle_day = get_puzzle_day_for_date(target_date)

    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(f"Puzzle CSV not found at {CSV_PATH}")

    df = pd.read_csv(CSV_PATH)
    day_rows = df[df["game_day"] == puzzle_day]
    if day_rows.empty:
        raise ValueError(f"No puzzle data found for day {puzzle_day}")

    day_rows = day_rows.sort_values("step_number")
    first_row = day_rows.iloc[0]

    steps = []
    for _, r in day_rows.iterrows():
        steps.append({
            "step_number": int(r["step_number"]),
            "teammate_name": str(r["teammate_name"]),
            "teammate_id": int(r["teammate_id"]) if pd.notna(r.get("teammate_id")) else 0,
            "teammate_nationality": str(r["teammate_nationality"]) if pd.notna(r.get("teammate_nationality")) else "",
            "teammate_position": str(r["teammate_position"]) if pd.notna(r.get("teammate_position")) else "",
            "appearances_together": int(r["appearances_together"]),
            "clue_tier": str(r["clue_tier"]),
            "shared_clubs": str(r.get("shared_clubs", "[]"))
        })

    return {
        "game_day": int(puzzle_day),
        "mystery_player": str(first_row["mystery_player"]),
        "mystery_position": str(first_row["mystery_position"]),
        "mystery_nationality": str(first_row["mystery_nationality"]),
        "mystery_id": int(first_row.get("mystery_id", 0)) if pd.notna(first_row.get("mystery_id")) else 0,
        "mystery_peak_value": int(first_row.get("mystery_peak_value", 0)) if pd.notna(first_row.get("mystery_peak_value")) else 0,
        "steps": steps
    }


# Backwards compatibility alias
extract_puzzle_data = load_played_with_puzzle


def calculate_adaptive_font_size(
    clues: list,
    max_width: int = MAX_SAFE_WIDTH,
    base_size: int = 44,
    min_size: int = 32,
    stroke_width: int = 5
) -> int:
    """
    Finds the optimal uniform font size across all clues so all text lines
    fit comfortably within max_width (default 840px) without clipping,
    accounting for stroke outline width padding (stroke_width * 2 = 10px).
    Steps down from base_size to min_size.
    """
    if not clues:
        return base_size

    stroke_padding = stroke_width * 2
    for size in range(base_size, min_size - 1, -1):
        font = get_font(size, bold=True)
        fits_all = True
        for clue in clues:
            if isinstance(clue, dict):
                apps = clue.get("appearances_together", "")
                name = clue.get("teammate_name", "")
                text = f"I played {apps} games with {name}"
            elif isinstance(clue, str):
                text = clue
            else:
                text = str(clue)
            bbox = font.getbbox(text)
            w = bbox[2] - bbox[0]
            if (w + stroke_padding) > max_width:
                fits_all = False
                break
        if fits_all:
            return size
    return min_size


class SocialCopy(dict):
    """
    Dict subclass providing backward-compatible string access:
    str(copy) and "WHO AM I?" in copy work as if copy were a caption string,
    while copy["caption"], copy["youtube_title"], copy["hashtags"] work as a dict.
    """
    def __contains__(self, item):
        if super().__contains__(item):
            return True
        return item in self.get("caption", "")

    def __str__(self):
        return self.get("caption", "")


def generate_youtube_title(puzzle_data: dict) -> str:
    """Generates engaging YouTube Shorts title strictly < 95 characters."""
    day = puzzle_data.get("game_day") or puzzle_data.get("day")
    day_prefix = f"WHO AM I? #{day} | " if day else "WHO AM I? | "
    steps = puzzle_data.get("steps", [])
    if len(steps) >= 5:
        s4 = steps[3]["teammate_name"].split()[-1]
        s5 = steps[4]["teammate_name"].split()[-1]
        title = f"{day_prefix}I played with {s4} & {s5}... Can you guess me? ⚽️ #Shorts"
    else:
        title = f"WHO AM I? #{day} ⚽️ Guess this footballer from 5 teammates! #Shorts" if day else "WHO AM I? ⚽️ Guess this footballer from 5 teammates! #Shorts"

    if len(title) >= 95:
        title = f"WHO AM I? #{day} ⚽️ Guess this footballer from 5 teammates! #Shorts" if day else "WHO AM I? ⚽️ Guess this footballer from 5 teammates! #Shorts"

    if len(title) >= 95:
        title = f"WHO AM I? #{day} ⚽️ #Shorts" if day else "WHO AM I? ⚽️ #Shorts"
    return title


def generate_social_copy(puzzle_data: dict) -> SocialCopy:
    """
    Generates high-converting platform social copy, YouTube Shorts title,
    comment CTA, and playmaker.best promo.
    """
    day = puzzle_data.get("game_day") or puzzle_data.get("day")
    steps = puzzle_data.get("steps", [])
    clue_bullets = "\n".join([f"• I played {s['appearances_together']} games with {s['teammate_name']}" for s in steps])

    header = f"WHO AM I? #{day} ⚽️🤔" if day else "WHO AM I? ⚽️🤔"
    day_tag = f"#playedwith_{day}" if day else "#playedwith"

    hashtags = [
        day_tag,
        "#football", "#soccer", "#ballknowledge", "#trivia", "#footballquiz",
        "#premierleague", "#laliga", "#championsleague", "#seriea", "#reels", "#shorts"
    ]
    tags_str = " ".join(hashtags)

    caption = (
        f"{header}\n\n"
        f"I played with these 5 teammates during my career:\n"
        f"{clue_bullets}\n\n"
        f"Can you name this player before checking the comments? 👇 Drop your shout below!\n\n"
        f"🎮 Beat all 6 daily football puzzles today on playmaker.best (link in bio)!\n\n"
        f"{tags_str}"
    )

    youtube_title = generate_youtube_title(puzzle_data)

    return SocialCopy({
        "caption": caption,
        "youtube_title": youtube_title,
        "hashtags": hashtags
    })


def render_played_with_frame(
    bg_image: Any,
    puzzle_data: dict,
    frame_idx: int = 0,
    total_frames: int = 225,
    font_size: Optional[int] = None
) -> Image.Image:
    """
    Renders a single 1080x1920 frame for the Played With Short:
    - Dimmed B-roll background (25%)
    - Top Header (Y=350, 420)
    - 5-Tier Static Clue Ladder (Y=580, 725, 870, 1015, 1160) with progressive difficulty highlighting
    - Terminal Hook Card ("WHO AM I?", Y=1460, neon green)
    - Secondary CTA (Y=1655, 1720)
    """
    # 1. Prepare base image in RGBA
    if bg_image is None:
        base = Image.new("RGBA", (WIDTH, HEIGHT), (15, 20, 30, 255))
    elif isinstance(bg_image, np.ndarray):
        if bg_image.shape[:2] != (HEIGHT, WIDTH):
            bg_image = center_crop_and_fill(bg_image, WIDTH, HEIGHT)
        rgb_arr = cv2.cvtColor(bg_image, cv2.COLOR_BGR2RGB)
        base = Image.fromarray(rgb_arr).convert("RGBA")
    elif isinstance(bg_image, Image.Image):
        base = bg_image.convert("RGBA")
        if base.size != (WIDTH, HEIGHT):
            base = base.resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
    else:
        base = Image.new("RGBA", (WIDTH, HEIGHT), (15, 20, 30, 255))

    # Dim background by 25% for high-contrast typography
    dim_overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 65))
    base = Image.alpha_composite(base, dim_overlay)

    # 2. Compute progressive timeline state
    # Total ladder reveal runs across first 77% of duration, remaining 23% is terminal hook
    hook_start_frame = int(round(total_frames * 0.77))
    step_duration = max(1.0, hook_start_frame / 5.0)

    if frame_idx < hook_start_frame:
        active_step = min(5, int(frame_idx / step_duration) + 1)
        revealed_steps = set(range(1, active_step + 1))
        is_hook_active = False
    else:
        active_step = None
        revealed_steps = {1, 2, 3, 4, 5}
        is_hook_active = True

    # 3. Create overlay layer for translucent rounded pill cards
    overlay = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw_ol = ImageDraw.Draw(overlay)

    steps = puzzle_data.get("steps", [])
    if font_size is None:
        font_size = calculate_adaptive_font_size(steps, max_width=MAX_SAFE_WIDTH)

    # Clue ladder vertical centers
    centers = [580, 725, 870, 1015, 1160]
    card_w = 900
    card_h = 104
    x1 = (WIDTH - card_w) // 2  # 90
    x2 = x1 + card_w            # 990

    for i in range(5):
        step_num = i + 1
        cy = centers[i]
        y1 = cy - card_h // 2
        y2 = cy + card_h // 2
        diff_col = DIFFICULTY_COLORS.get(step_num, (200, 200, 200))

        if step_num == active_step:
            # Active clue currently being highlighted
            pill_fill = (20, 30, 52, 215)
            pill_outline = (*diff_col, 255)
            border_w = 4
            accent_fill = (*diff_col, 255)
        elif step_num in revealed_steps:
            # Already revealed clue
            pill_fill = (12, 18, 30, 175)
            pill_outline = (*diff_col, 190)
            border_w = 2
            accent_fill = (*diff_col, 240)
        else:
            # Base static pill before reveal
            pill_fill = (10, 16, 28, 150)
            pill_outline = (255, 255, 255, 45)
            border_w = 2
            accent_fill = (*diff_col, 120)

        # Draw rounded card
        draw_ol.rounded_rectangle(
            (x1, y1, x2, y2),
            radius=22,
            fill=pill_fill,
            outline=pill_outline,
            width=border_w
        )

        # Left difficulty-coded accent bar
        bar_x1 = x1 + 10
        bar_x2 = x1 + 20
        bar_y1 = y1 + 14
        bar_y2 = y2 - 14
        draw_ol.rounded_rectangle(
            (bar_x1, bar_y1, bar_x2, bar_y2),
            radius=4,
            fill=accent_fill
        )

    # Terminal Hook Card at Y=1460
    hook_cx = WIDTH // 2
    hook_cy = 1460
    hook_w = 640
    hook_h = 120
    hx1 = hook_cx - hook_w // 2
    hx2 = hook_cx + hook_w // 2
    hy1 = hook_cy - hook_h // 2
    hy2 = hook_cy + hook_h // 2

    if is_hook_active:
        hook_frame = frame_idx - hook_start_frame
        pulse_alpha = int(210 + 45 * math.sin(hook_frame * 0.3))
        hook_fill = (12, 28, 20, 215)
        hook_outline = (0, 230, 118, pulse_alpha)
        hook_border_w = 5
    else:
        hook_fill = (10, 16, 28, 160)
        hook_outline = (255, 255, 255, 45)
        hook_border_w = 2

    draw_ol.rounded_rectangle(
        (hx1, hy1, hx2, hy2),
        radius=26,
        fill=hook_fill,
        outline=hook_outline,
        width=hook_border_w
    )

    # Composite translucent overlay onto base image
    base = Image.alpha_composite(base, overlay)
    draw = ImageDraw.Draw(base)

    # 4. Typography Rendering
    font_header = get_font(58, bold=True)
    font_sub = get_font(36, bold=True)
    font_clue = get_font(font_size, bold=True)
    font_cta1 = get_font(40, bold=True)
    font_cta2 = get_font(32, bold=True)

    # Top Header
    draw_text_with_outline_and_shadow(
        draw, (WIDTH // 2, 350),
        "BALL KNOWLEDGE TEST",
        font=font_header,
        fill_color=(255, 255, 255),
        stroke_color=(0, 0, 0, 240),
        stroke_width=6,
        anchor="mm"
    )
    draw_text_with_outline_and_shadow(
        draw, (WIDTH // 2, 420),
        "Can you name this mystery footballer?",
        font=font_sub,
        fill_color=(255, 213, 79),
        stroke_color=(0, 0, 0, 240),
        stroke_width=4,
        anchor="mm"
    )

    # 5 Clue texts
    for i in range(5):
        if i < len(steps):
            s = steps[i]
            clue_text = f"I played {s['appearances_together']} games with {s['teammate_name']}"
            cy = centers[i]
            step_num = i + 1

            if step_num == active_step:
                text_col = (255, 255, 255)
                stroke_w = 5
            elif step_num in revealed_steps:
                text_col = (255, 255, 255)
                stroke_w = 4
            else:
                text_col = (220, 225, 235)
                stroke_w = 4

            draw_text_with_outline_and_shadow(
                draw, (WIDTH // 2, cy),
                clue_text,
                font=font_clue,
                fill_color=text_col,
                stroke_color=(0, 0, 0, 240),
                stroke_width=stroke_w,
                anchor="mm",
                shadow_offset=6
            )

    # Hook Card Text ("WHO AM I?")
    if is_hook_active:
        hook_font = get_font(88, bold=True)
        hook_col = (0, 240, 120)
        hook_stroke_w = 7
        hook_shadow = 10
    else:
        hook_font = get_font(84, bold=True)
        hook_col = (0, 230, 118)
        hook_stroke_w = 6
        hook_shadow = 8

    draw_text_with_outline_and_shadow(
        draw, (hook_cx, hook_cy),
        "WHO AM I?",
        font=hook_font,
        fill_color=hook_col,
        stroke_color=(0, 0, 0, 255),
        stroke_width=hook_stroke_w,
        anchor="mm",
        shadow_offset=hook_shadow
    )

    # Secondary Call To Action
    draw_text_with_outline_and_shadow(
        draw, (WIDTH // 2, 1655),
        "Drop your guess in the comments",
        font=font_cta1,
        fill_color=(255, 255, 255),
        stroke_color=(0, 0, 0, 240),
        stroke_width=4,
        anchor="mm"
    )
    draw_text_with_outline_and_shadow(
        draw, (WIDTH // 2, 1720),
        "PLAYMAKER.BEST • DAILY FOOTBALL PUZZLES",
        font=font_cta2,
        fill_color=(64, 196, 255),
        stroke_color=(0, 0, 0, 240),
        stroke_width=4,
        anchor="mm"
    )

    return base


def render_played_with_video(
    puzzle_data: dict,
    output_path: str,
    bg_clip: Optional[str] = None,
    audio_track: Optional[str] = None,
    duration: float = DURATION_SEC,
    fps: int = FPS
) -> str:
    """
    Renders 1080x1920 30fps vertical MP4 video with looped audio:
    - Centers and crops B-roll clip
    - Applies progressive ladder animation & WHO AM I hook
    - Muxes with looped audio (-stream_loop -1 -shortest)
    - Returns output_path string
    """
    if duration < 7.0 or duration > 9.0:
        raise ValueError(f"Target duration must be strictly between 7.0 and 9.0 seconds, got {duration}")

    total_frames = int(round(duration * fps))

    if not bg_clip or not os.path.exists(bg_clip):
        bg_clip = select_broll_clip(game_id="played_with")

    if not bg_clip or not os.path.exists(bg_clip):
        raise FileNotFoundError(f"No valid B-roll video found at {bg_clip}")

    if not audio_track or not os.path.exists(audio_track):
        audio_track = select_audio_track(game_id="played_with")

    cap = cv2.VideoCapture(bg_clip)
    if not cap.isOpened():
        raise IOError(f"Could not open background video: {bg_clip}")

    # Ensure parent output directory exists
    out_dir = os.path.dirname(os.path.abspath(output_path))
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    temp_raw = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False).name
    try:
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        video_writer = cv2.VideoWriter(temp_raw, fourcc, fps, (WIDTH, HEIGHT))

        adaptive_size = calculate_adaptive_font_size(puzzle_data.get("steps", []), max_width=MAX_SAFE_WIDTH)
        print(f"🎬 Rendering Played With Short ({total_frames} frames @ {fps}fps, font {adaptive_size}px) -> {output_path}")

        try:
            for f_idx in range(total_frames):
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                if not ret:
                    raise IOError(f"Failed to read frame {f_idx} from {bg_clip}")

                pil_frame = render_played_with_frame(
                    frame,
                    puzzle_data,
                    frame_idx=f_idx,
                    total_frames=total_frames,
                    font_size=adaptive_size
                )

                rgb_frame = pil_frame.convert("RGB")
                bgr_frame = cv2.cvtColor(np.array(rgb_frame), cv2.COLOR_RGB2BGR)
                video_writer.write(bgr_frame)

                if (f_idx + 1) % 45 == 0 or f_idx == total_frames - 1:
                    pct = ((f_idx + 1) / float(total_frames)) * 100.0
                    print(f"   Progress: {f_idx + 1}/{total_frames} ({pct:.1f}%)")
        finally:
            cap.release()
            video_writer.release()

        # Mux audio with looped audio and clean truncation
        if audio_track and os.path.exists(audio_track):
            cmd = [
                FFMPEG_EXE, "-y",
                "-i", temp_raw,
                "-stream_loop", "-1",
                "-i", audio_track,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                "-shortest",
                output_path
            ]
        else:
            cmd = [
                FFMPEG_EXE, "-y",
                "-i", temp_raw,
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "18",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                output_path
            ]

        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            err_msg = proc.stderr.decode("utf-8", errors="ignore")
            raise RuntimeError(f"FFmpeg muxing failed: {err_msg}")
    finally:
        if os.path.exists(temp_raw):
            try:
                os.remove(temp_raw)
            except Exception:
                pass

    print(f"✅ Successfully rendered Played With short: {output_path} ({os.path.getsize(output_path):,} bytes)")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Render 'Played With' 9:16 Vertical Video Short")
    parser.add_argument("--day", type=int, default=None, help="Puzzle day number (1-365)")
    parser.add_argument("--date", type=str, default=None, help="Target date YYYY-MM-DD")
    parser.add_argument("--bg", type=str, default=None, help="Path to custom B-roll clip")
    parser.add_argument("--exclude-bg", nargs="*", default=None, help="B-roll paths to exclude")
    parser.add_argument("--audio", type=str, default=None, help="Path to custom audio track")
    parser.add_argument("--output", type=str, default=None, help="Output MP4 or image file path")
    parser.add_argument("--duration", type=float, default=DURATION_SEC, help="Video duration in seconds (7.0-9.0)")
    parser.add_argument("--fps", type=int, default=FPS, help="Frames per second (default 30)")
    parser.add_argument("--preview", action="store_true", help="Generate single preview JPEG frame instead of full video")
    parser.add_argument("--upload", action="store_true", help="Auto-upload to YouTube Shorts and Instagram Reels")

    args = parser.parse_args()

    puzzle = load_played_with_puzzle(day=args.day, date_str=args.date)
    print(f"🎯 Loaded Played With Puzzle #{puzzle['game_day']}: {puzzle['mystery_player']} ({puzzle['mystery_nationality']}, {puzzle['mystery_position']})")

    social_copy = generate_social_copy(puzzle)
    print(f"\n📺 YouTube Shorts Title: {social_copy['youtube_title']}")
    print(f"\n📝 Caption:\n{social_copy['caption']}\n")

    if args.preview:
        out_img = args.output if (args.output and (args.output.endswith(".jpg") or args.output.endswith(".png"))) else "preview_played_with.jpg"
        bg_clip = args.bg if (args.bg and os.path.exists(args.bg)) else select_broll_clip(game_id="played_with")
        cap = cv2.VideoCapture(bg_clip)
        frame = None
        if cap.isOpened():
            # Grab frame at ~5.8s
            target_f = min(int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1, int(5.8 * 30))
            cap.set(cv2.CAP_PROP_POS_FRAMES, max(0, target_f))
            ret, frame = cap.read()
            cap.release()

        pil_img = render_played_with_frame(frame, puzzle, frame_idx=180, total_frames=225)
        pil_img.convert("RGB").save(out_img, quality=95)
        print(f"📸 Preview frame saved to {out_img}")
        return

    output_path = args.output
    if not output_path:
        out_dir = os.path.join(BASE_DIR, "output")
        os.makedirs(out_dir, exist_ok=True)
        output_path = os.path.join(out_dir, f"played_with_day_{puzzle['game_day']}.mp4")

    render_played_with_video(
        puzzle_data=puzzle,
        output_path=output_path,
        bg_clip=args.bg,
        audio_track=args.audio,
        duration=args.duration,
        fps=args.fps
    )

    if args.upload:
        print("🚀 Auto-upload enabled: Publishing to YouTube Shorts & Instagram Reels...")
        cmd_yt = [
            sys.executable, os.path.join(BASE_DIR, "scripts", "youtube_uploader.py"),
            "--file", output_path,
            "--title", social_copy["youtube_title"],
            "--privacy", "public"
        ]
        try:
            subprocess.run(cmd_yt, check=True)
        except Exception as e:
            print(f"⚠️ YouTube upload error: {e}")

        cmd_ig = [
            sys.executable, os.path.join(BASE_DIR, "scripts", "instagram_uploader.py"),
            "--file", output_path,
            "--caption", social_copy["caption"]
        ]
        try:
            subprocess.run(cmd_ig, check=True)
        except Exception as e:
            print(f"⚠️ Instagram upload error: {e}")


if __name__ == "__main__":
    main()
