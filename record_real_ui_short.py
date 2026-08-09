#!/usr/bin/env python3
import asyncio
import os
import sys
import re
import json
import argparse
import datetime
import cv2
import numpy as np
from playwright.async_api import async_playwright
from audio_sfx import build_audio_track, mux_audio_to_video

def load_games_metadata():
    games_file = "games.json"
    if os.path.exists(games_file):
        with open(games_file, "r", encoding="utf-8") as f:
            return {g["id"]: g for g in json.load(f)}
    return {}

GAMES_META = load_games_metadata()

def sanitize_filename(name):
    s = str(name).strip().replace(" ", "_")
    return re.sub(r'[^\w\-]', '', s)

async def record_short_video(game_id="top_transfers", day_offset=0, fast_mode=False):
    url = f"http://localhost:8080/games/{game_id}.html"
    
    WIDTH, HEIGHT = 1080, 1920
    FPS = 30
    
    print(f"🎬 Initializing Universal Video Generator (Game: {game_id}, Day Offset: {day_offset})...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 430, "height": 932},
            device_scale_factor=2.0,
            is_mobile=True,
            has_touch=True
        )
        page = await context.new_page()
        
        # Use wait_until="domcontentloaded" to avoid waiting indefinitely for external CDN fonts or analytics scripts
        response = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
        if not response or response.status >= 400:
            print(f"❌ Error: Page {url} failed to load (status {response.status if response else 'None'}).")
            await browser.close()
            return None
            
        await page.wait_for_selector("#guess-input", timeout=10000)
        try:
            await page.evaluate("document.fonts.ready")
        except Exception:
            pass
        
        if day_offset < 0:
            for _ in range(abs(day_offset)):
                await page.click("#nav-back-btn")
                await page.wait_for_timeout(150)
        elif day_offset > 0:
            for _ in range(day_offset):
                await page.click("#nav-front-btn")
                await page.wait_for_timeout(150)

        await page.add_style_tag(content="""
            header, footer, #how-to-play, #game-note-bar, section.text-center > p, main > section:last-child, #nav-back-btn, #nav-front-btn, #puzzle-badge, div:has(> #puzzle-badge), #toast-container, .toast { 
                display: none !important; 
            }
            body { 
                padding-top: 10px !important; 
                padding-bottom: 120px !important;
            }
            main { 
                padding-top: 5px !important; 
                max-width: 100% !important;
            }
            #target-name, #player-name-display {
                font-size: 32px !important;
                margin-bottom: 5px !important;
            }
            table th, table td {
                padding: 10px 8px !important;
                font-size: 14px !important;
            }
            #short-cta-banner {
                position: fixed;
                bottom: 15px;
                left: 4%;
                right: 4%;
                background: rgba(15, 23, 42, 0.94);
                backdrop-filter: blur(16px);
                border: 2px solid #ff0055;
                border-radius: 18px;
                padding: 12px;
                text-align: center;
                z-index: 9999;
                box-shadow: 0 10px 30px rgba(255, 0, 85, 0.6);
            }
            #video-timer-widget {
                position: fixed;
                top: 110px; /* Safe zone: placed below Instagram/TikTok/YouTube Shorts top controls */
                right: 20px;
                z-index: 10000;
                background: rgba(15, 23, 42, 0.92);
                backdrop-filter: blur(12px);
                border: 2.5px solid #00f0ff;
                border-radius: 16px;
                padding: 8px 16px;
                display: flex;
                align-items: center;
                gap: 10px;
                box-shadow: 0 8px 25px rgba(0, 240, 255, 0.4), 0 0 12px rgba(0, 0, 0, 0.6);
                transition: all 0.2s ease-in-out;
            }
            #timer-badge-icon {
                font-size: 22px;
                line-height: 1;
            }
            #timer-text-container {
                display: flex;
                flex-direction: column;
                align-items: flex-end;
            }
            #timer-label {
                font-family: 'Space Grotesk', sans-serif;
                font-size: 10px;
                text-transform: uppercase;
                letter-spacing: 1.2px;
                color: #94a3b8;
                font-weight: 700;
            }
            #timer-value {
                font-family: 'Anton', sans-serif;
                font-size: 28px;
                color: #39ff14;
                line-height: 1;
                text-shadow: 0 0 12px rgba(57, 255, 20, 0.6);
            }
            #middle-feedback-modal {
                position: fixed;
                top: 42%;
                left: 50%;
                transform: translate(-50%, -50%) scale(0.85);
                z-index: 100000;
                opacity: 0;
                pointer-events: none;
                transition: all 0.25s cubic-bezier(0.34, 1.56, 0.64, 1);
                background: rgba(15, 23, 42, 0.96);
                backdrop-filter: blur(20px);
                border: 3.5px solid #39ff14;
                border-radius: 24px;
                padding: 24px 36px;
                text-align: center;
                box-shadow: 0 15px 45px rgba(57, 255, 20, 0.5), 0 0 25px rgba(0, 0, 0, 0.8);
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                gap: 8px;
                min-width: 280px;
            }
        """)
        
        if game_id in ["top_transfers", "top_scorers"]:
            cta_title = "CAN YOU GUESS #1 AND #3? 🤔"
        elif game_id in ["transfer_destination", "club_connect"]:
            cta_title = "CAN YOU GUESS THE MYSTERY CLUBS? 🤔"
        else:
            cta_title = "CAN YOU SOLVE THE MYSTERY PUZZLE? 🤔"
            
        await page.evaluate(f"""
            const cta = document.createElement("div");
            cta.id = "short-cta-banner";
            cta.innerHTML = `
                <div style="font-family:'Anton', sans-serif; font-size:22px; color:#ffffff; font-style:italic; text-transform:uppercase;">{cta_title}</div>
                <div style="font-family:'Space Grotesk', sans-serif; font-size:14px; color:#00f0ff; font-weight:bold; margin-top:3px;">Comment below or play live at playmaker.best!</div>
            `;
            document.body.appendChild(cta);

            const timerWidget = document.createElement("div");
            timerWidget.id = "video-timer-widget";
            timerWidget.innerHTML = `
                <div id="timer-badge-icon">⏱️</div>
                <div id="timer-text-container">
                    <span id="timer-label">GUESS IN</span>
                    <span id="timer-value">3s</span>
                </div>
            `;
            document.body.appendChild(timerWidget);

            const feedbackModal = document.createElement("div");
            feedbackModal.id = "middle-feedback-modal";
            feedbackModal.innerHTML = `
                <div id="modal-icon" style="font-size: 54px; line-height: 1;">✔</div>
                <div id="modal-title" style="font-family: 'Anton', sans-serif; font-size: 38px; color: #ffffff; letter-spacing: 1.5px; text-transform: uppercase;">CORRECT!</div>
                <div id="modal-sub" style="font-family: 'Space Grotesk', sans-serif; font-size: 18px; color: #39ff14; font-weight: bold;">GREAT GUESS!</div>
            `;
            document.body.appendChild(feedbackModal);
        """)

        frames = []
        audio_events = []
        
        def add_frame(png_bytes):
            nparr = np.frombuffer(png_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            frame = cv2.resize(frame, (WIDTH, HEIGHT))
            frames.append(frame)

        async def capture_hold(num_frames):
            png_bytes = await page.screenshot(type="png", full_page=False, timeout=10000)
            for _ in range(num_frames):
                add_frame(png_bytes)

        async def set_timer_visible(visible=True):
            op = "1" if visible else "0"
            tf = "translateY(0)" if visible else "translateY(-12px)"
            await page.evaluate(f"""
                const widget = document.getElementById("video-timer-widget");
                if (widget) {{
                    widget.style.opacity = "{op}";
                    widget.style.transform = "{tf}";
                }}
            """)

        async def set_timer_state(label_text, value_text, color="#39ff14", border_color="#00f0ff", icon="⏱️"):
            await page.evaluate(f"""
                const label = document.getElementById("timer-label");
                const val = document.getElementById("timer-value");
                const widget = document.getElementById("video-timer-widget");
                const iconEl = document.getElementById("timer-badge-icon");
                if (label && val && widget && iconEl) {{
                    label.textContent = "{label_text}";
                    val.textContent = "{value_text}";
                    val.style.color = "{color}";
                    val.style.textShadow = "0 0 12px {color}aa";
                    widget.style.borderColor = "{border_color}";
                    widget.style.boxShadow = "0 8px 25px {border_color}66";
                    iconEl.textContent = "{icon}";
                }}
            """)

        async def show_middle_feedback(is_correct=True, message=""):
            title_text = "CORRECT!" if is_correct else "WRONG!"
            sub_text = message if message else ("GREAT GUESS!" if is_correct else "NOT ON THE LIST!")
            color = "#39ff14" if is_correct else "#ff0055"
            border_color = "#39ff14" if is_correct else "#ff0055"
            icon_symbol = "✔" if is_correct else "✖"
            shadow_style = f"0 15px 45px {color}66, 0 0 30px rgba(0, 0, 0, 0.9)"
            
            await page.evaluate(f"""
                const m = document.getElementById("middle-feedback-modal");
                if (m) {{
                    m.style.borderColor = "{border_color}";
                    m.style.boxShadow = "{shadow_style}";
                    m.innerHTML = `
                        <div style="font-size: 54px; line-height: 1; color: {color};">{icon_symbol}</div>
                        <div style="font-family: 'Anton', sans-serif; font-size: 38px; color: #ffffff; letter-spacing: 1.5px; text-transform: uppercase;">{title_text}</div>
                        <div style="font-family: 'Space Grotesk', sans-serif; font-size: 18px; color: {color}; font-weight: bold;">{sub_text}</div>
                    `;
                    m.style.opacity = "1";
                    m.style.transform = "translate(-50%, -50%) scale(1)";
                }}
            """)

        async def hide_middle_feedback():
            await page.evaluate("""
                const m = document.getElementById("middle-feedback-modal");
                if (m) {
                    m.style.opacity = "0";
                    m.style.transform = "translate(-50%, -50%) scale(0.85)";
                }
            """)

        async def run_countdown(seconds=3):
            """Runs a synchronized visual countdown timer before each guess and emits SFX audio ticks."""
            await set_timer_visible(True)
            colors = {3: "#39ff14", 2: "#fbbf24", 1: "#ef4444"}
            borders = {3: "#00f0ff", 2: "#fbbf24", 1: "#ef4444"}
            
            for sec in range(seconds, 0, -1):
                color = colors.get(sec, "#39ff14")
                border = borders.get(sec, "#00f0ff")
                await set_timer_state("GUESS IN", f"{sec}s", color=color, border_color=border, icon="⏱️")
                
                current_t = len(frames) / FPS
                audio_events.append((f"tick_{sec}", current_t))
                await capture_hold(30) # 1 second hold per tick @ 30 FPS
                
            await set_timer_state("TIME'S UP!", "GO!", color="#ef4444", border_color="#ef4444", icon="🚨")
            current_t = len(frames) / FPS
            audio_events.append(("tick_go", current_t))
            await capture_hold(12) # 0.4s brief alert hold

        target_name = ""
        if await page.locator("#target-name").count() > 0:
            target_name = await page.inner_text("#target-name")
        elif await page.locator("#player-name-display").count() > 0:
            target_name = await page.inner_text("#player-name-display")
        else:
            target_name = game_id.upper()

        target_clean = sanitize_filename(target_name)
        target_date = (datetime.date.today() + datetime.timedelta(days=day_offset)).strftime("%Y-%m-%d")
        
        output_mp4 = f"/Users/ggbushi/Documents/Football/output_{game_id}_{target_clean}_{target_date}.mp4"

        print(f"🎯 Target Theme: {target_name} ({target_date})")
        print(f"📁 Output File: {output_mp4}")
        
        await capture_hold(15)
        
        async def make_guess(name, is_correct=True, do_countdown=True):
            if do_countdown:
                await run_countdown(3)
                
            # Hide top-right timer widget once countdown ends and typing/evaluation starts
            await set_timer_visible(False)
            
            input_el = page.locator("#guess-input")
            await input_el.focus()
            await input_el.fill("")
            
            for i in range(len(name)):
                char = name[i]
                await input_el.type(char, delay=0)
                png = await page.screenshot(type="png", timeout=10000)
                for _ in range(2):
                    add_frame(png)
                await page.wait_for_timeout(70)
                
            await page.wait_for_timeout(150)
            
            try:
                await page.wait_for_selector("#autocomplete-list div", state="visible", timeout=2000)
                await capture_hold(8)
                dropdown_items = page.locator("#autocomplete-list div")
                count = await dropdown_items.count()
                clicked = False
                for i in range(count):
                    text = await dropdown_items.nth(i).text_content()
                    if name.split()[0].lower() in text.lower():
                        await dropdown_items.nth(i).click()
                        clicked = True
                        break
                if not clicked and count > 0:
                    await dropdown_items.first.click()
            except Exception:
                await input_el.fill(name)
                
            await capture_hold(5)
            await page.click("#submit-btn")
            
            # Emit audio SFX event for correct / wrong answer
            current_t = len(frames) / FPS
            audio_events.append(('correct' if is_correct else 'wrong', current_t))
            
            # Display prominent enlarged centered modal feedback overlay
            sub_title = "GREAT GUESS!" if is_correct else "NOT ON THE LIST!"
            await show_middle_feedback(is_correct=is_correct, message=sub_title)
            await capture_hold(45) # Hold enlarged modal in middle of screen for ~1.5s
            await hide_middle_feedback()
            await capture_hold(15)

        # ----------------------------------------------------
        # Game-Specific Automation Logic
        # ----------------------------------------------------
        if game_id == "club_connect":
            mystery_club = await page.evaluate("DAILY_CLUBCONNECT_GAME.club")
            print(f"💡 Target Mystery Club (Hidden from viewer): {mystery_club}")
            
            wrong_clubs_pool = ["Real Madrid", "Chelsea", "Arsenal", "Barcelona", "Bayern Munich", "Juventus"]
            wrong_guesses = [c for c in wrong_clubs_pool if c.lower() != mystery_club.lower()][:2]
            
            for idx, wrong_club in enumerate(wrong_guesses, 1):
                print(f"  ➜ Wrong Guess {idx}/2 (unlocking next player): {wrong_club}")
                await make_guess(wrong_club, is_correct=False, do_countdown=True)
                
        elif game_id == "top_transfers":
            # Baseline first guess (always has 3s countdown)
            await make_guess("Cristiano Ronaldo", is_correct=False, do_countdown=True)
            players_data = await page.evaluate("DAILY_TRANSFER_GAME.transfers")
            players_data.sort(key=lambda x: float(x.get('transfer_fee', 0)), reverse=True)
            top5 = players_data[:5]
            reveal_indices = [4, 3, 1]
            for idx in reveal_indices:
                if idx < len(top5):
                    p_name = top5[idx]['player_name']
                    print(f"  ➜ Guessing #{idx+1}: {p_name}")
                    await make_guess(p_name, is_correct=True, do_countdown=True)
                    
            await page.evaluate("""
                const tbody = document.getElementById("table-body");
                if (tbody && tbody.children.length >= 3) {
                    tbody.children[0].style.filter = "blur(8px)";
                    tbody.children[0].style.opacity = "0.4";
                    tbody.children[2].style.filter = "blur(8px)";
                    tbody.children[2].style.opacity = "0.4";
                }
            """)
            
        elif game_id == "transfer_destination":
            # Baseline first guess (always has 3s countdown)
            await make_guess("Real Madrid", is_correct=False, do_countdown=True)
            transfers = await page.evaluate("DAILY_DESTINATION_GAME.transfers")
            for idx in range(min(2, len(transfers))):
                dest_club = transfers[idx]['to_club_name']
                print(f"  ➜ Guessing Step {idx+1} Destination: {dest_club}")
                await make_guess(dest_club, is_correct=True, do_countdown=True)
                
        elif game_id == "top_scorers":
            # Baseline first guess (always has 3s countdown)
            await make_guess("Cristiano Ronaldo", is_correct=False, do_countdown=True)
            scorers_data = await page.evaluate("DAILY_SCORERS_GAME.scorers")
            scorers_data.sort(key=lambda x: int(x.get('goals', 0)), reverse=True)
            top5 = scorers_data[:5]
            reveal_indices = [4, 3, 1]
            for idx in reveal_indices:
                if idx < len(top5):
                    p_name = top5[idx]['player_name']
                    print(f"  ➜ Guessing #{idx+1}: {p_name}")
                    await make_guess(p_name, is_correct=True, do_countdown=True)

        # Final hold on full screen with CTA (~4.5s)
        await capture_hold(135)

        print(f"📹 Writing {len(frames)} raw video frames...")
        temp_raw_mp4 = output_mp4 + ".raw.mp4"
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_raw_mp4, fourcc, FPS, (WIDTH, HEIGHT))
        for f in frames:
            out.write(f)
        out.release()
        
        await browser.close()
        
        # Audio track synthesis & FFmpeg muxing
        total_dur = len(frames) / FPS
        wav_track_path = output_mp4 + ".wav"
        print(f"🔊 Synthesizing audio track ({len(audio_events)} SFX events)...")
        build_audio_track(audio_events, total_dur, wav_track_path)
        
        print("🎬 Muxing audio track with video via FFmpeg...")
        final_mp4 = mux_audio_to_video(temp_raw_mp4, wav_track_path, output_mp4)
        
        if os.path.exists(wav_track_path):
            os.remove(wav_track_path)
            
        print(f"✨ Video successfully created with audio: {final_mp4}")
        return final_mp4

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Playmaker Social Media Video Shorts")
    parser.add_argument("--game", default="top_transfers", help="Game ID (top_transfers, transfer_destination, top_scorers, club_connect, etc.)")
    parser.add_argument("--day", type=int, default=0, help="Day offset: -1 for yesterday, 0 for today, 1 for tomorrow")
    parser.add_argument("--fast", action="store_true", help="Fast mode for quick rendering tests")
    args = parser.parse_args()
    
    asyncio.run(record_short_video(game_id=args.game, day_offset=args.day, fast_mode=args.fast))

