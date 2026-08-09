import os
import sys
import re
import math
import pandas as pd
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

def get_font(size, bold=False):
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial.ttf" if not bold else "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
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

def load_game_data(csv_path, game_day, selected_key=None):
    df = pd.read_csv(csv_path)
    if 'game_day' in df.columns:
        df = df[df['game_day'] == game_day]
    if selected_key and 'selected_nationality' in df.columns:
        df = df[df['selected_nationality'] == selected_key]
    elif selected_key and 'selected_club' in df.columns:
        df = df[df['selected_club'] == selected_key]
    
    if df.empty:
        raise ValueError(f"No game data found for day {game_day} / key {selected_key}")
    
    # Sort top 5 transfers by fee descending
    df['fee_num'] = pd.to_numeric(df['transfer_fee'], errors='coerce').fillna(0)
    df = df.sort_values(by='fee_num', ascending=False).head(5)
    
    title_key = ""
    if 'selected_nationality' in df.columns:
        title_key = df['selected_nationality'].iloc[0] + " National Team"
    elif 'selected_club' in df.columns:
        title_key = df['selected_club'].iloc[0]
    else:
        title_key = "Top Record Signings"
        
    records = df.to_dict('records')
    return title_key, records

def create_gradient_background(width, height):
    img = Image.new("RGBA", (width, height), (9, 9, 25, 255))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        r = int(9 + (22 - 9) * (y / height))
        g = int(9 + (18 - 9) * (y / height))
        b = int(25 + (51 - 25) * (y / height))
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))
    return img

def draw_card(draw, box, bg_color, border_color=None, corner_radius=16):
    x0, y0, x1, y1 = box
    draw.rounded_rectangle([x0, y0, x1, y1], radius=corner_radius, fill=bg_color, outline=border_color, width=3)

def generate_video(csv_path, game_day, output_path="top_transfers_short.mp4", selected_key=None, fps=30):
    print(f"Loading data for Day {game_day}...")
    title_entity, players = load_game_data(csv_path, game_day, selected_key)
    
    WIDTH, HEIGHT = 1080, 1920
    
    font_title = get_font(56, bold=True)
    font_badge = get_font(30, bold=True)
    font_row_rank = get_font(44, bold=True)
    font_row_name = get_font(38, bold=True)
    font_row_sub = get_font(26, bold=False)
    font_fee = get_font(38, bold=True)
    font_input = get_font(34, bold=False)
    font_cta = get_font(42, bold=True)
    
    events = [
        {"rank_idx": 4, "countdown_start": 1.0, "type_start": 4.0, "type_end": 6.2, "reveal": 6.8},
        {"rank_idx": 3, "countdown_start": 8.5, "type_start": 11.5, "type_end": 13.7, "reveal": 14.3},
        {"rank_idx": 1, "countdown_start": 16.0, "type_start": 19.0, "type_end": 21.2, "reveal": 21.8},
    ]
    total_duration = 26.0
    total_frames = int(total_duration * fps)
    
    print(f"Rendering {total_frames} frames to {output_path}...")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(output_path, fourcc, fps, (WIDTH, HEIGHT))
    
    bg_base = create_gradient_background(WIDTH, HEIGHT)
    hidden_indices = {0, 2}
    
    for f in range(total_frames):
        t = f / fps
        img = bg_base.copy()
        draw = ImageDraw.Draw(img)
        
        # --- HEADER SECTION ---
        draw_card(draw, (80, 90, 480, 150), (0, 240, 255, 40), border_color=(0, 240, 255, 230), corner_radius=25)
        draw.text((280, 120), "TOP TRANSFERS", font=font_badge, fill=(0, 240, 255), anchor="mm")
        
        # --- COUNTDOWN TIMER WIDGET (TOP RIGHT SAFE ZONE) ---
        timer_text = "GUESS IN 3s"
        timer_color = (57, 255, 20)
        border_color = (0, 240, 255)
        
        for ev in events:
            if ev["countdown_start"] <= t < ev["type_start"]:
                rem_sec = math.ceil(ev["type_start"] - t)
                rem_sec = max(1, min(3, rem_sec))
                timer_text = f"GUESS IN {rem_sec}s"
                if rem_sec == 3:
                    timer_color = (57, 255, 20)
                    border_color = (0, 240, 255)
                elif rem_sec == 2:
                    timer_color = (251, 191, 36)
                    border_color = (251, 191, 36)
                else:
                    timer_color = (239, 68, 68)
                    border_color = (239, 68, 68)
                break
            elif ev["type_start"] <= t <= ev["reveal"]:
                timer_text = "GUESSING..."
                timer_color = (0, 240, 255)
                border_color = (0, 240, 255)
                break
                
        draw_card(draw, (700, 85, 1000, 155), (15, 23, 42, 235), border_color=border_color, corner_radius=16)
        draw.text((725, 120), "⏱️", font=font_badge, fill=(255, 255, 255), anchor="mm")
        draw.text((865, 120), timer_text, font=font_badge, fill=timer_color, anchor="mm")

        draw.text((540, 205), title_entity.upper(), font=font_title, fill=(255, 255, 255), anchor="mm")
        
        timeframe_str = "Transfers 2000 – July 2026 | Non-Loan Moves"
        draw.text((540, 260), timeframe_str, font=font_row_sub, fill=(180, 190, 210), anchor="mm")
        
        # --- LEADERBOARD BOARD ---
        board_top = 310
        row_h = 140
        row_gap = 20
        
        revealed_ranks = set()
        for ev in events:
            if t >= ev["reveal"]:
                revealed_ranks.add(ev["rank_idx"])
                
        for i in range(5):
            ry0 = board_top + i * (row_h + row_gap)
            ry1 = ry0 + row_h
            box = (80, ry0, 1000, ry1)
            
            p_data = players[i]
            is_hidden = (i in hidden_indices)
            is_revealed = (i in revealed_ranks) or (not is_hidden and i not in {1, 3, 4})
            
            if is_hidden:
                bg_c = (25, 25, 45, 220)
                border_c = (255, 0, 85, 200) if i == 0 else (245, 158, 11, 200)
                draw_card(draw, box, bg_c, border_color=border_c, corner_radius=18)
                
                draw.text((130, ry0 + 70), f"#{i+1}", font=font_row_rank, fill=(220, 220, 240), anchor="mm")
                draw.text((220, ry0 + 48), "❓  HIDDEN PLAYER", font=font_row_name, fill=(255, 180, 200), anchor="lm")
                draw.text((220, ry0 + 92), "Guess in comments!", font=font_row_sub, fill=(140, 150, 170), anchor="lm")
                draw.text((950, ry0 + 70), "???", font=font_fee, fill=(255, 0, 85) if i==0 else (245, 158, 11), anchor="rm")
            else:
                if is_revealed:
                    bg_c = (18, 38, 32, 230)
                    border_c = (57, 255, 20, 220)
                    draw_card(draw, box, bg_c, border_color=border_c, corner_radius=18)
                    
                    draw.text((130, ry0 + 70), f"#{i+1}", font=font_row_rank, fill=(57, 255, 20), anchor="mm")
                    draw.text((220, ry0 + 45), p_data['player_name'], font=font_row_name, fill=(255, 255, 255), anchor="lm")
                    
                    from_c = str(p_data.get('from_club_name', ''))
                    to_c = str(p_data.get('to_club_name', ''))
                    date_str = str(p_data.get('transfer_date', ''))[:4]
                    route_str = f"{from_c}  ➔  {to_c} ({date_str})"
                    if len(route_str) > 42:
                        route_str = route_str[:40] + "..."
                    draw.text((220, ry0 + 92), route_str, font=font_row_sub, fill=(160, 220, 180), anchor="lm")
                    
                    fee_txt = format_fee(p_data['transfer_fee'])
                    draw.text((950, ry0 + 70), fee_txt, font=font_fee, fill=(57, 255, 20), anchor="rm")
                else:
                    bg_c = (20, 22, 35, 180)
                    border_c = (60, 70, 90, 150)
                    draw_card(draw, box, bg_c, border_color=border_c, corner_radius=18)
                    draw.text((130, ry0 + 70), f"#{i+1}", font=font_row_rank, fill=(100, 110, 130), anchor="mm")
                    draw.text((220, ry0 + 70), "•••••••••••••••••", font=font_row_name, fill=(80, 90, 110), anchor="lm")
                    draw.text((950, ry0 + 70), format_fee(p_data['transfer_fee']), font=font_fee, fill=(100, 110, 130), anchor="rm")
                    
        # --- INTERACTIVE SIMULATED TYPING INPUT BOX ---
        active_ev = None
        for ev in events:
            if ev["type_start"] <= t <= ev["reveal"]:
                active_ev = ev
                break
                
        input_box_y0 = 1130
        input_box_y1 = 1240
        
        if active_ev:
            target_p = players[active_ev["rank_idx"]]
            full_name = target_p['player_name']
            
            if t < active_ev["type_end"]:
                progress = (t - active_ev["type_start"]) / (active_ev["type_end"] - active_ev["type_start"])
                typed_len = int(progress * len(full_name))
                typed_str = full_name[:typed_len]
                show_dropdown = False
            else:
                typed_str = full_name
                show_dropdown = True
                
            draw_card(draw, (80, input_box_y0, 1000, input_box_y1), (15, 20, 35, 240), border_color=(0, 240, 255, 220), corner_radius=16)
            draw.text((120, input_box_y0 + 55), "🔍", font=font_row_name, fill=(0, 240, 255), anchor="mm")
            
            cursor = "|" if (int(t * 4) % 2 == 0 and not show_dropdown) else ""
            draw.text((160, input_box_y0 + 55), typed_str + cursor, font=font_input, fill=(255, 255, 255), anchor="lm")
            
            if show_dropdown:
                drop_y0 = input_box_y1 + 10
                drop_y1 = drop_y0 + 85
                draw_card(draw, (80, drop_y0, 1000, drop_y1), (25, 45, 35, 250), border_color=(57, 255, 20, 240), corner_radius=12)
                draw.text((130, drop_y0 + 42), "✔", font=font_row_name, fill=(57, 255, 20), anchor="mm")
                draw.text((180, drop_y0 + 42), f"Select: {full_name}", font=font_input, fill=(57, 255, 20), anchor="lm")
        else:
            draw_card(draw, (80, input_box_y0, 1000, input_box_y1), (15, 20, 30, 150), border_color=(50, 60, 80, 120), corner_radius=16)
            draw.text((120, input_box_y0 + 55), "🔍", font=font_row_name, fill=(100, 110, 130), anchor="mm")
            draw.text((160, input_box_y0 + 55), "Type player name...", font=font_input, fill=(80, 90, 110), anchor="lm")

        # --- BOTTOM CALL TO ACTION (CTA) ---
        cta_box_y0 = 1620
        cta_box_y1 = 1800
        
        pulse_alpha = int(200 + 55 * math.sin(t * 4))
        draw_card(draw, (80, cta_box_y0, 1000, cta_box_y1), (255, 0, 85, 40), border_color=(255, 0, 85, pulse_alpha), corner_radius=20)
        
        draw.text((540, cta_box_y0 + 50), "CAN YOU GUESS #1 AND #3? 🤔", font=font_cta, fill=(255, 255, 255), anchor="mm")
        draw.text((540, cta_box_y0 + 115), "Comment below or play live at playmaker.best!", font=font_row_name, fill=(0, 240, 255), anchor="mm")
        
        frame_np = cv2.cvtColor(np.array(img), cv2.COLOR_RGBA2BGR)
        out.write(frame_np)
        
    out.release()
    print(f"✅ Video rendering complete: {output_path}")

if __name__ == "__main__":
    csv_file = "/Users/ggbushi/Documents/Football/daily_nationality_transfer_games.csv"
    game_day = 2
    out_file = "/Users/ggbushi/Documents/Football/output_top_transfers_day2.mp4"
    generate_video(csv_file, game_day, output_path=out_file)
