#!/usr/bin/env python3
"""
scripts/generate_h2h_carousel.py

Automated Instagram Carousel Generator (4:5 1080x1350px).
Renders 6 high-contrast Head-to-Head (H2H) comparison slides using Playwright
and outputs formatted PNGs + optimized social media caption.
"""

import os
import sys
import json
import asyncio
import datetime
import argparse
from typing import Dict, List, Optional, Tuple

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from scripts.player_stats_aggregator import PlayerStatsAggregator
from scripts.player_image_manager import resolve_player_image_path, sanitize_filename

TEMPLATE_PATH = os.path.join(BASE_DIR, "templates", "carousel", "h2h_carousel_template.html")
OUTPUT_CAROUSEL_DIR = os.path.join(BASE_DIR, "output_carousel")

# Curated daily viral matchups schedule
CURATED_MATCHUPS = [
    ("Eden Hazard", "Neymar"),
    ("Karim Benzema", "Robert Lewandowski"),
    ("Toni Kroos", "Luka Modrić"),
    ("Son Heung-min", "Riyad Mahrez"),
    ("Sergio Agüero", "Luis Suárez"),
    ("Mohamed Salah", "Sadio Mané"),
    ("Virgil van Dijk", "Sergio Ramos"),
    ("Gareth Bale", "Arjen Robben"),
    ("Thierry Henry", "Wayne Rooney"),
    ("Zlatan Ibrahimović", "Samuel Eto'o"),
    ("Angel Di Maria", "David Silva"),
    ("Kevin De Bruyne", "Mesut Özil"),
    ("Manuel Neuer", "Gianluigi Buffon")
]

def get_daily_h2h_matchup(date_str: Optional[str] = None) -> Tuple[str, str]:
    """Deterministically returns the H2H matchup for the given date."""
    if not date_str:
        dt = datetime.date.today()
    else:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    
    idx = dt.toordinal() % len(CURATED_MATCHUPS)
    return CURATED_MATCHUPS[idx]

def build_slide_payload(stats_a: Dict, stats_b: Dict, img_path_a: str, img_path_b: str) -> Dict:
    """Formats the JSON payload injected into the HTML slide deck."""
    p_a = {
        "name": stats_a["name"],
        "nationality": stats_a["nationality"],
        "position": stats_a["sub_position"] or stats_a["position"],
        "imagePath": os.path.abspath(img_path_a),
        "totalApps": stats_a["overall"]["total_appearances"],
        "totalGoals": stats_a["overall"]["total_goals"],
        "totalAssists": stats_a["overall"]["total_assists"],
        "totalGA": stats_a["overall"]["total_ga"],
        "goalsPerGame": f"{stats_a['overall']['goals_per_game']:.2f}",
        "minsPerGA": f"{stats_a['overall']['mins_per_ga']:.1f}" if stats_a['overall']['mins_per_ga'] else None,
        "clubGoals": stats_a["club"]["goals"],
        "clubApps": stats_a["club"]["appearances"],
        "intlCaps": stats_a["international"]["caps"],
        "intlGoals": stats_a["international"]["goals"],
        "wcGoals": stats_a["international"]["world_cup_goals"],
        "euroGoals": stats_a["international"]["euro_goals"],
        "copaGoals": stats_a["international"]["copa_america_goals"],
        "qualGoals": stats_a["international"]["qualifier_goals"],
        "peakMarketValue": stats_a.get("peak_market_value", 0)
    }

    p_b = {
        "name": stats_b["name"],
        "nationality": stats_b["nationality"],
        "position": stats_b["sub_position"] or stats_b["position"],
        "imagePath": os.path.abspath(img_path_b),
        "totalApps": stats_b["overall"]["total_appearances"],
        "totalGoals": stats_b["overall"]["total_goals"],
        "totalAssists": stats_b["overall"]["total_assists"],
        "totalGA": stats_b["overall"]["total_ga"],
        "goalsPerGame": f"{stats_b['overall']['goals_per_game']:.2f}",
        "minsPerGA": f"{stats_b['overall']['mins_per_ga']:.1f}" if stats_b['overall']['mins_per_ga'] else None,
        "clubGoals": stats_b["club"]["goals"],
        "clubApps": stats_b["club"]["appearances"],
        "intlCaps": stats_b["international"]["caps"],
        "intlGoals": stats_b["international"]["goals"],
        "wcGoals": stats_b["international"]["world_cup_goals"],
        "euroGoals": stats_b["international"]["euro_goals"],
        "copaGoals": stats_b["international"]["copa_america_goals"],
        "qualGoals": stats_b["international"]["qualifier_goals"],
        "peakMarketValue": stats_b.get("peak_market_value", 0)
    }

    return {
        "playerA": p_a,
        "playerB": p_b
    }

def generate_h2h_caption(stats_a: Dict, stats_b: Dict) -> str:
    """
    Generates high-converting Instagram copy optimized for saves, shares, and comments
    following the /social-content and /instagram skill frameworks.
    """
    name_a = stats_a["name"]
    name_b = stats_b["name"]
    goals_a = stats_a["overall"]["total_goals"]
    goals_b = stats_b["overall"]["total_goals"]
    assists_a = stats_a["overall"]["total_assists"]
    assists_b = stats_b["overall"]["total_assists"]
    apps_a = stats_a["overall"]["total_appearances"]
    apps_b = stats_b["overall"]["total_appearances"]

    tag_a = "#" + sanitize_filename(name_a).replace("_", "")
    tag_b = "#" + sanitize_filename(name_b).replace("_", "")

    caption = (
        f"PRIME VS PRIME: {name_a} or {name_b}? ⚔️⚽\n\n"
        f"Two of the most gifted footballers of their generation, but who had the superior career when you look at all the official numbers?\n\n"
        f"📊 CAREER NUMBERS:\n"
        f"🔹 {name_a}: {apps_a} Games | {goals_a} Goals | {assists_a} Assists ({goals_a + assists_a} G+A)\n"
        f"🔸 {name_b}: {apps_b} Games | {goals_b} Goals | {assists_b} Assists ({goals_b + assists_b} G+A)\n\n"
        f"Swipe through for the full breakdown across Club, International & Efficiency metrics 👉\n\n"
        f"💬 THE DEBATE:\n"
        f"If you could build a team around one in their peak prime season, who are you picking?\n\n"
        f"Drop your pick below! 👇\n\n"
        f"🎮 Test your football IQ daily at playmaker.best\n\n"
        f"{tag_a} {tag_b} #football #soccer #footballtrivia #ucl #championsleague #premierleague #laliga #footballstats #playmaker"
    )
    return caption

async def render_carousel_slides_async(player_a_name: str, player_b_name: str, date_str: Optional[str] = None) -> Tuple[List[str], str]:
    """
    Renders 6 PNG slides (1080x1350) using Playwright.
    Returns list of slide file paths and the caption.
    """
    from playwright.async_api import async_playwright

    if not date_str:
        date_str = datetime.date.today().strftime("%Y-%m-%d")

    agg = PlayerStatsAggregator(lazy_load=False)
    stats_a = agg.get_player_career_stats(player_a_name)
    stats_b = agg.get_player_career_stats(player_b_name)

    if not stats_a or not stats_b:
        raise ValueError(f"Could not resolve career stats for '{player_a_name}' or '{player_b_name}'.")

    # Resolve player images
    img_path_a = resolve_player_image_path(stats_a["name"], stats_a.get("image_url"))
    img_path_b = resolve_player_image_path(stats_b["name"], stats_b.get("image_url"))

    slide_payload = build_slide_payload(stats_a, stats_b, img_path_a, img_path_b)
    caption = generate_h2h_caption(stats_a, stats_b)

    slug_a = sanitize_filename(stats_a["name"])
    slug_b = sanitize_filename(stats_b["name"])
    folder_name = f"h2h_{slug_a}_vs_{slug_b}_{date_str}"
    out_dir = os.path.join(OUTPUT_CAROUSEL_DIR, folder_name)
    os.makedirs(out_dir, exist_ok=True)

    # Save caption to folder
    caption_path = os.path.join(out_dir, "caption.txt")
    with open(caption_path, "w", encoding="utf-8") as f:
        f.write(caption)

    rendered_images = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1080, "height": 1350}, device_scale_factor=1)

        file_url = f"file://{os.path.abspath(TEMPLATE_PATH)}"
        await page.goto(file_url, wait_until="networkidle")

        # Inject data
        await page.evaluate(f"window.SLIDE_DATA = {json.dumps(slide_payload)};")

        for slide_idx in range(1, 7):
            await page.evaluate(f"renderSlide({slide_idx});")
            await page.wait_for_timeout(150)  # Render stabilization
            out_file = os.path.join(out_dir, f"slide_{slide_idx}.png")
            await page.screenshot(path=out_file, clip={"x": 0, "y": 0, "width": 1080, "height": 1350})
            rendered_images.append(out_file)
            print(f"  ✓ Snapshot slide {slide_idx}/6: {out_file}")

        await browser.close()

    print(f"\n🎉 Successfully rendered {len(rendered_images)} slides to {out_dir}")
    return rendered_images, caption

def render_carousel_slides(player_a_name: str, player_b_name: str, date_str: Optional[str] = None) -> Tuple[List[str], str]:
    """Synchronous entrypoint for carousel rendering."""
    return asyncio.run(render_carousel_slides_async(player_a_name, player_b_name, date_str))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Playmaker H2H Instagram Carousel")
    parser.add_argument("--player-a", type=str, default="", help="Player A name")
    parser.add_argument("--player-b", type=str, default="", help="Player B name")
    parser.add_argument("--date", type=str, default="", help="Date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true", help="Render slides only without uploading")

    args = parser.parse_args()

    p_a = args.player_a
    p_b = args.player_b
    if not p_a or not p_b:
        p_a, p_b = get_daily_h2h_matchup(args.date)

    print(f"🚀 Generating Head-to-Head Carousel: {p_a} vs {p_b}")
    slides, caption = render_carousel_slides(p_a, p_b, args.date)
    print("\n--- GENERATED CAPTION ---")
    print(caption)
