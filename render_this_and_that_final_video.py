#!/usr/bin/env python3
"""
Playmaker "This & That" 3D Animated Video Generator (Production V4).
- Header positioned directly above the football field
- Footer positioned up in safe social zone
- Base64 embedded crests & silhouette
- 3 pairs drop in (1.2s, 2.6s, 4.0s) with whoosh sfx
- Tension ticking countdown
"""

import os
import sys
import json
import base64
import asyncio
import tempfile
import subprocess
import pandas as pd
from playwright.async_api import async_playwright

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from audio_sfx import build_audio_track, mux_audio_to_video

WIDTH = 1080
HEIGHT = 1920
FPS = 30
DURATION_SEC = 9.0
TOTAL_FRAMES = int(DURATION_SEC * FPS)

FLAG_EMOJIS = {
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "France": "🇫🇷", "Argentina": "🇦🇷", "Portugal": "🇵🇹",
    "Brazil": "🇧🇷", "Germany": "🇩🇪", "Spain": "🇪🇸", "Italy": "🇮🇹",
    "Netherlands": "🇳🇱", "Belgium": "🇧🇪", "Uruguay": "🇺🇾", "Nigeria": "🇳🇬",
    "Switzerland": "🇨🇭", "Ireland": "🇮🇪", "Sweden": "🇸🇪", "Mexico": "🇲🇽",
    "Norway": "🇳🇴", "Poland": "🇵🇱", "Colombia": "🇨🇴", "Chile": "🇨🇱",
    "Denmark": "🇩🇰", "Serbia": "🇷🇸", "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿"
}

import unicodedata

SPECIAL_BADGE_MAP = {
    'inter': 'inter_milan.png',
    'inter milan': 'inter_milan.png',
    'ac milan': 'ac_milan.png',
    'manchester united': 'manchester_united.png',
    'manchester city': 'manchester_city.png',
    'man utd': 'manchester_united.png',
    'man city': 'manchester_city.png',
    'west ham united': 'west_ham_united.png',
    'west ham': 'west_ham_united.png',
    'sporting cp': 'sporting_cp.png',
    'sporting': 'sporting_cp.png',
    'paris saint-germain': 'paris_saint_germain.png',
    'psg': 'paris_saint_germain.png',
    'borussia dortmund': 'borussia_dortmund.png',
    'rb leipzig': 'rb_leipzig.png',
    'atletico madrid': 'atletico_madrid.png',
    'real madrid': 'real_madrid.png',
    'bayern munich': 'bayern_munich.png',
    'tottenham hotspur': 'tottenham.png',
    'tottenham': 'tottenham.png',
    'fenerbahce': 'fenerbahce.png',
    'fenerbahçe': 'fenerbahce.png',
    'celtic': 'celtic.png',
    'feyenoord': 'feyenoord.png'
}

def resolve_criteria_info(statement):
    s = statement.strip()
    badges_dir = os.path.join(BASE_DIR, "assets", "badges")
    available_badges = set(os.listdir(badges_dir)) if os.path.exists(badges_dir) else set()

    if s.startswith("Played for "):
        club = s.replace("Played for ", "").strip()
        clean = unicodedata.normalize('NFKD', club).encode('ascii', 'ignore').decode('utf-8').lower()
        badge_file = SPECIAL_BADGE_MAP.get(clean) or SPECIAL_BADGE_MAP.get(club.lower())
        if not badge_file:
            slug = clean.replace(' ', '_').replace('-', '_') + '.png'
            if slug in available_badges:
                badge_file = slug
            else:
                for f in available_badges:
                    if clean.replace(' ', '_') in f:
                        badge_file = f
                        break
        badge_path = os.path.join(badges_dir, badge_file) if badge_file else None
        return {
            "type": "club",
            "sub": "PLAYED FOR",
            "main": club,
            "badge_path": badge_path,
            "emoji": None
        }
    elif s.startswith("Represented ") and "internationally" in s:
        nat = s.replace("Represented ", "").replace(" internationally", "").strip()
        flag = FLAG_EMOJIS.get(nat, "🌍")
        return {
            "type": "nation",
            "sub": "REPRESENTED",
            "main": nat,
            "badge_path": None,
            "emoji": flag
        }
    elif s.startswith("Won the "):
        trophy = s.replace("Won the ", "").strip()
        return {
            "type": "trophy",
            "sub": "WON THE",
            "main": trophy,
            "badge_path": None,
            "emoji": "🏆"
        }
    elif s.startswith("Played in "):
        league = s.replace("Played in ", "").replace("the ", "").strip()
        return {
            "type": "league",
            "sub": "PLAYED IN",
            "main": league,
            "badge_path": None,
            "emoji": "⚽"
        }
    return {
        "type": "custom",
        "sub": "CRITERIA",
        "main": s,
        "badge_path": None,
        "emoji": "⭐"
    }

def img_to_base64(path):
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        ext = os.path.splitext(path)[1].replace(".", "").lower()
        mime = f"image/{ext}" if ext in ["png", "jpg", "jpeg", "webp"] else "image/png"
        return f"data:{mime};base64," + base64.b64encode(f.read()).decode("utf-8")

def get_slot_layouts(count):
    if count == 1:
        return [{"top": 50, "left": 50}]
    elif count == 2:
        return [{"top": 35, "left": 50}, {"top": 65, "left": 50}]
    elif count == 3:
        return [{"top": 25, "left": 50}, {"top": 52, "left": 35}, {"top": 75, "left": 65}]
    elif count == 4:
        return [
            {"top": 28, "left": 30}, {"top": 28, "left": 70},
            {"top": 70, "left": 30}, {"top": 70, "left": 70}
        ]
    elif count == 5:
        return [
            {"top": 22, "left": 30}, {"top": 22, "left": 70},
            {"top": 50, "left": 50},
            {"top": 78, "left": 30}, {"top": 78, "left": 70}
        ]
    else:
        return [
            {"top": 22, "left": 30}, {"top": 22, "left": 70},
            {"top": 49, "left": 25}, {"top": 49, "left": 75},
            {"top": 78, "left": 28}, {"top": 78, "left": 72}
        ]

async def render_video(game_day=2, output_mp4=None):
    df = pd.read_csv(os.path.join(BASE_DIR, "daily_this_and_that_games.csv"))
    puzzle = df[df["game_day"] == game_day].iloc[0]

    stmt_a = puzzle["statement_a"]
    stmt_b = puzzle["statement_b"]
    total_answers = int(puzzle["total_answers"])
    raw_details = json.loads(puzzle["answer_details"])

    players = raw_details[:6]
    player_count = len(players)
    layouts = get_slot_layouts(player_count)

    print(f"🎬 Rendering Video for Day {game_day}: {stmt_a} & {stmt_b} ({player_count} players)")

    sil_b64 = img_to_base64(os.path.join(BASE_DIR, "assets", "players", "fifa_mystery_silhouette_cropped.png"))

    crit_a = resolve_criteria_info(stmt_a)
    crit_b = resolve_criteria_info(stmt_b)

    if crit_a["badge_path"] and os.path.exists(crit_a["badge_path"]):
        badge_a_b64 = img_to_base64(crit_a["badge_path"])
        card_icon_a = f'<img class="club-logo" id="crit-logo-a" src="{badge_a_b64}">'
    else:
        emoji_a = crit_a["emoji"] or "⚽"
        card_icon_a = f'<div class="crit-emoji">{emoji_a}</div>'

    if crit_b["badge_path"] and os.path.exists(crit_b["badge_path"]):
        badge_b_b64 = img_to_base64(crit_b["badge_path"])
        card_icon_b = f'<img class="club-logo" id="crit-logo-b" src="{badge_b_b64}">'
    else:
        emoji_b = crit_b["emoji"] or "⚽"
        card_icon_b = f'<div class="crit-emoji">{emoji_b}</div>'

    modes = ["both", "nat_only", "pos_only", "both", "nat_only", "pos_only"]
    prepared_players = []
    for i, p in enumerate(players):
        mode = modes[i % len(modes)]
        nat = p.get("nationality", "Unknown")
        flag = FLAG_EMOJIS.get(nat, "🌍")
        pos = p.get("position", "Attack")
        pos_short = "FWD" if pos == "Attack" else ("MID" if pos == "Midfield" else "DEF")

        prepared_players.append({
            "idx": i,
            "top": layouts[i]["top"],
            "left": layouts[i]["left"],
            "mode": mode,
            "flag": flag,
            "pos": pos_short,
            "pair_group": i // 2
        })

    temp_dir = tempfile.mkdtemp(prefix="this_and_that_render_")
    frames_dir = os.path.join(temp_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    raw_video = os.path.join(temp_dir, "raw.mp4")
    raw_audio = os.path.join(temp_dir, "audio.wav")

    with open(os.path.join(BASE_DIR, "tight_header_stadium.html")) as f:
        html = f.read()

    html = html.replace('{card_icon_a}', card_icon_a)
    html = html.replace('{card_icon_b}', card_icon_b)
    html = html.replace('{crit_sub_a}', crit_a["sub"])
    html = html.replace('{crit_sub_b}', crit_b["sub"])
    html = html.replace('{crit_main_a}', crit_a["main"])
    html = html.replace('{crit_main_b}', crit_b["main"])
    html = html.replace('{total_answers}', str(total_answers))

    script = f"""
    <script>
      const playersData = {json.dumps(prepared_players)};
      const silB64 = "{sil_b64}";
      const pitch = document.querySelector('.pitch-turf');

      // Clear static slots
      document.querySelectorAll('.player-slot').forEach(el => el.remove());

      playersData.forEach(p => {{
        const slot = document.createElement('div');
        slot.className = 'player-slot';
        slot.id = 'slot-' + p.idx;
        slot.style.top = p.top + '%';
        slot.style.left = p.left + '%';

        let leftBadge = (p.mode === 'pos_only' || p.mode === 'both') 
          ? `<span class="badge-pill badge-pos">${{p.pos}}</span>`
          : `<span class="badge-pill badge-locked">🔒</span>`;

        let rightBadge = (p.mode === 'nat_only' || p.mode === 'both')
          ? `<span class="badge-pill badge-flag">${{p.flag}}</span>`
          : `<span class="badge-pill badge-locked">🔒</span>`;

        slot.innerHTML = `
          <img class="sil-img" src="${{silB64}}" alt="Sil">
          <div class="clue-row">
            ${{leftBadge}}
            ${{rightBadge}}
          </div>
          <div class="nameplate">???</div>
        `;
        pitch.appendChild(slot);
      }});

      window.setFrameState = function(frameIdx) {{
        const fps = 30;
        const timeSec = frameIdx / fps;

        playersData.forEach(p => {{
          const slot = document.getElementById('slot-' + p.idx);
          if (!slot) return;
          const dropTime = 1.2 + p.pair_group * 1.4;

          if (timeSec < dropTime) {{
            slot.style.opacity = '0';
            slot.style.transform = 'translate(-50%, -50%) scale(0.1)';
          }} else {{
            const animProgress = Math.min(1.0, (timeSec - dropTime) / 0.35);
            const scale = 0.1 + 0.9 * Math.sin(animProgress * Math.PI / 2);
            slot.style.opacity = '1';
            slot.style.transform = 'translate(-50%, -50%) scale(' + scale.toFixed(3) + ')';
          }}
        }});
      }};
    </script>
    """
    html = html.replace("</body>", script + "</body>")

    temp_html = os.path.join(temp_dir, "index.html")
    with open(temp_html, "w") as f:
        f.write(html)

    print("🚀 Recording frames via Playwright headless browser...")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": WIDTH, "height": HEIGHT})
        await page.goto("file://" + temp_html, wait_until="networkidle")
        await page.wait_for_timeout(300)

        for f_idx in range(TOTAL_FRAMES):
            await page.evaluate(f"window.setFrameState({f_idx})")
            frame_path = os.path.join(frames_dir, f"frame_{f_idx:04d}.jpg")
            await page.screenshot(path=frame_path, type="jpeg", quality=90)
            if f_idx % 60 == 0:
                print(f"   Frame progress: {f_idx}/{TOTAL_FRAMES} ({int(f_idx/TOTAL_FRAMES*100)}%)...")

        await browser.close()

    print("✅ All frames captured. Encoding video via ffmpeg...")
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%04d.jpg"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-preset", "fast",
        raw_video
    ]
    subprocess.run(ffmpeg_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Audio design
    sound_events = [
        ("whoosh", 1.2),
        ("whoosh", 2.6),
        ("whoosh", 4.0),
        ("tick", 5.0),
        ("tick", 6.0),
        ("tick", 7.0),
        ("tick", 8.0)
    ]
    print("🔊 Synthesizing audio track...")
    build_audio_track(sound_events, DURATION_SEC, raw_audio)

    final_out = output_mp4 or f"output_this_and_that_day_{game_day}.mp4"
    print(f"🎬 Muxing audio into {final_out}...")
    mux_audio_to_video(raw_video, raw_audio, final_out)
    print(f"🎉 Complete! Final video rendered at: {final_out}")

    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)
    return final_out

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--day", type=int, default=2)
    parser.add_argument("--output", type=str, default="test_animated_this_and_that_tight.mp4")
    args = parser.parse_args()

    asyncio.run(render_video(game_day=args.day, output_mp4=args.output))
