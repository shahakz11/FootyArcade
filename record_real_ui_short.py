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
        
        response = await page.goto(url)
        if not response or response.status >= 400:
            print(f"❌ Error: Page {url} failed to load (status {response.status if response else 'None'}).")
            await browser.close()
            return None
            
        await page.wait_for_selector("#guess-input")
        
        if day_offset < 0:
            for _ in range(abs(day_offset)):
                await page.click("#nav-back-btn")
                await page.wait_for_timeout(150)
        elif day_offset > 0:
            for _ in range(day_offset):
                await page.click("#nav-front-btn")
                await page.wait_for_timeout(150)

        await page.add_style_tag(content="""
            header, footer, #how-to-play, #game-note-bar, section.text-center > p, main > section:last-child { 
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
                background: rgba(19, 19, 19, 0.96);
                backdrop-filter: blur(16px);
                border: 2px solid #ff0055;
                border-radius: 18px;
                padding: 12px;
                text-align: center;
                z-index: 9999;
                box-shadow: 0 10px 30px rgba(255, 0, 85, 0.6);
            }
        """)
        
        # Game-specific CTA banner text:
        # - Top Transfers & Top Scorers -> "CAN YOU GUESS #1 AND #3? 🤔" / "CAN YOU GUESS THE MYSTERY PLAYERS? 🤔"
        # - Transfer Destination & Club Connect -> "CAN YOU GUESS THE MYSTERY CLUBS? 🤔"
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
        """)

        frames = []
        
        def add_frame(png_bytes):
            nparr = np.frombuffer(png_bytes, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            frame = cv2.resize(frame, (WIDTH, HEIGHT))
            frames.append(frame)

        async def capture_hold(num_frames):
            png_bytes = await page.screenshot(type="png", full_page=False)
            for _ in range(num_frames):
                add_frame(png_bytes)

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
        
        await capture_hold(5)
        
        async def make_guess(name):
            input_el = page.locator("#guess-input")
            await input_el.focus()
            await input_el.fill("")
            
            for i in range(len(name)):
                char = name[i]
                await input_el.type(char, delay=0)
                png = await page.screenshot(type="png")
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
            await capture_hold(45)

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
                await make_guess(wrong_club)
                
        elif game_id == "top_transfers":
            await make_guess("Cristiano Ronaldo")
            players_data = await page.evaluate("DAILY_TRANSFER_GAME.transfers")
            players_data.sort(key=lambda x: float(x.get('transfer_fee', 0)), reverse=True)
            top5 = players_data[:5]
            reveal_indices = [4, 3, 1]
            for idx in reveal_indices:
                if idx < len(top5):
                    p_name = top5[idx]['player_name']
                    print(f"  ➜ Guessing #{idx+1}: {p_name}")
                    await make_guess(p_name)
                    
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
            await make_guess("Real Madrid")
            transfers = await page.evaluate("DAILY_DESTINATION_GAME.transfers")
            for idx in range(min(2, len(transfers))):
                dest_club = transfers[idx]['to_club_name']
                print(f"  ➜ Guessing Step {idx+1} Destination: {dest_club}")
                await make_guess(dest_club)
                
        elif game_id == "top_scorers":
            await make_guess("Cristiano Ronaldo")
            scorers_data = await page.evaluate("DAILY_SCORERS_GAME.scorers")
            scorers_data.sort(key=lambda x: int(x.get('goals', 0)), reverse=True)
            top5 = scorers_data[:5]
            reveal_indices = [4, 3, 1]
            for idx in reveal_indices:
                if idx < len(top5):
                    p_name = top5[idx]['player_name']
                    print(f"  ➜ Guessing #{idx+1}: {p_name}")
                    await make_guess(p_name)

        # Final hold on full screen with CTA (~3.5s)
        await capture_hold(105)

        print(f"📹 Writing {len(frames)} frames to video...")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_mp4, fourcc, FPS, (WIDTH, HEIGHT))
        for f in frames:
            out.write(f)
        out.release()
        
        await browser.close()
        print(f"✨ Video successfully created: {output_mp4}")
        return output_mp4

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Playmaker Social Media Video Shorts")
    parser.add_argument("--game", default="top_transfers", help="Game ID (top_transfers, transfer_destination, top_scorers, club_connect, etc.)")
    parser.add_argument("--day", type=int, default=0, help="Day offset: -1 for yesterday, 0 for today, 1 for tomorrow")
    parser.add_argument("--fast", action="store_true", help="Fast mode for quick rendering tests")
    args = parser.parse_args()
    
    asyncio.run(record_short_video(game_id=args.game, day_offset=args.day, fast_mode=args.fast))
