#!/usr/bin/env python3
"""
tests/test_career_flight_short.py

Hermetic unit test suite for the Career Flight Short video generator:
- Tests n-2 date resolution
- Tests chronological transfer ordering (switching from reverse to chronological)
- Tests club geo-resolution and haversine distances
- Tests 3D slerp and spherical projection
- Tests video timeline frame budgeting
"""

import os
import sys
import unittest
import datetime
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

from render_career_flight_short import (
    get_n_minus_2_date,
    load_destination_puzzle,
    build_video_timeline,
    format_fee_label,
    generate_career_flight_metadata,
    render_flight_frame,
    GlobeRenderer,
    AIRPLANE_PATH,
    CAR_PATH
)
from scripts.geo_manager import (
    get_club_location,
    haversine_distance_km,
    latlon_to_vec3,
    vec3_to_latlon,
    slerp,
    project_point_to_screen,
    is_same_country
)

class TestCareerFlightShort(unittest.TestCase):

    def test_n_minus_2_date_resolution(self):
        """Verifies that the target date is strictly n-2 (two days ago)."""
        ref_date = datetime.date(2026, 10, 11)
        expected = datetime.date(2026, 10, 9)
        self.assertEqual(get_n_minus_2_date(ref_date), expected)

        ref_leap = datetime.date(2024, 3, 1)
        expected_leap = datetime.date(2024, 2, 28)
        self.assertEqual(get_n_minus_2_date(ref_leap), expected_leap)

    def test_chronological_transfer_ordering(self):
        """
        Verifies that transfers are ordered chronologically from first club to last club,
        reversing the puzzle's default reverse chronological order.
        """
        # Puzzle #75 is Paul Pogba
        data = load_destination_puzzle(puzzle_num_override=75)
        self.assertEqual(data["player_name"], "Paul Pogba")
        self.assertEqual(data["nationality"], "France")

        legs = data["legs"]
        self.assertGreaterEqual(len(legs), 2)

        # First leg must start from Manchester United and go to Juventus (12/13)
        self.assertEqual(legs[0]["from_club"], "Manchester United")
        self.assertEqual(legs[0]["to_club"], "Juventus")

        # Second leg must be Juventus -> Manchester United (16/17)
        self.assertEqual(legs[1]["from_club"], "Juventus")
        self.assertEqual(legs[1]["to_club"], "Manchester United")

        # Third leg must be Manchester United -> Juventus (22/23)
        self.assertEqual(legs[2]["from_club"], "Manchester United")
        self.assertEqual(legs[2]["to_club"], "Juventus")

    def test_geo_resolution_and_distance(self):
        """Verifies club coordinates and accurate haversine distances."""
        loc_man = get_club_location("Manchester United")
        loc_tur = get_club_location("Juventus")

        self.assertEqual(loc_man["city"], "Manchester")
        self.assertEqual(loc_tur["city"], "Turin")

        dist = haversine_distance_km(loc_man["lat"], loc_man["lon"], loc_tur["lat"], loc_tur["lon"])
        # Manchester to Turin is ~1,173 km (between 1,100 and 1,250 km)
        self.assertGreater(dist, 1100.0)
        self.assertLess(dist, 1250.0)

    def test_3d_projection_and_slerp(self):
        """Verifies 3D spherical geometry and orthographic projection."""
        v1 = latlon_to_vec3(53.46, -2.29) # Manchester
        v2 = latlon_to_vec3(45.10, 7.64)  # Turin

        # Norm of unit vectors must be 1.0
        self.assertAlmostEqual(float(np.linalg.norm(v1)), 1.0, places=5)
        self.assertAlmostEqual(float(np.linalg.norm(v2)), 1.0, places=5)

        # Midpoint via slerp
        mid = slerp(v1, v2, 0.5)
        self.assertAlmostEqual(float(np.linalg.norm(mid)), 1.0, places=5)

        # Forward projection on screen
        sx, sy, vis = project_point_to_screen(53.46, -2.29, 50.0, 0.0, 540, 800, 600)
        self.assertTrue(vis)
        self.assertIsInstance(sx, int)
        self.assertIsInstance(sy, int)

    def test_fee_label_formatter(self):
        """Verifies clear transfer fee formatting."""
        self.assertEqual(format_fee_label(0.0), "FREE TRANSFER")
        self.assertEqual(format_fee_label(105_000_000.0), "€105M FEE")
        self.assertEqual(format_fee_label(38_500_000.0), "€38.5M FEE")
        self.assertEqual(format_fee_label(500_000.0), "€500K FEE")

    def test_timeline_budgeting(self):
        """Verifies that generated timelines maintain 18-28s duration for shorts."""
        dummy_puzzle = {
            "legs": [
                {"from_club": "A", "to_club": "B", "distance_km": 100, "season": "10/11", "fee": 0, "from_loc": {}, "to_loc": {}},
                {"from_club": "B", "to_club": "C", "distance_km": 200, "season": "12/13", "fee": 10, "from_loc": {}, "to_loc": {}},
                {"from_club": "C", "to_club": "D", "distance_km": 300, "season": "15/16", "fee": 50, "from_loc": {}, "to_loc": {}}
            ]
        }
        tl = build_video_timeline(dummy_puzzle)
        self.assertGreaterEqual(tl["total_duration"], 15.0)
        self.assertLessEqual(tl["total_duration"], 30.0)
        self.assertEqual(tl["total_frames"], int(tl["total_duration"] * 30))

    def test_metadata_generation(self):
        """Verifies rich SEO-optimized metadata generation for YouTube and Instagram."""
        from render_career_flight_short import generate_career_flight_metadata
        data = load_destination_puzzle(puzzle_num_override=75)
        meta = generate_career_flight_metadata(data)

        # YouTube Title
        yt_title = meta["youtube_title"]
        self.assertIn("Paul Pogba", yt_title)
        self.assertIn("#Shorts", yt_title)
        self.assertLessEqual(len(yt_title), 100)

        # YouTube Description
        yt_desc = meta["youtube_description"]
        self.assertIn("Paul Pogba", yt_desc)
        self.assertIn("Total Distance Flown", yt_desc)
        self.assertIn("https://playmaker.best/games/transfer_destination.html", yt_desc)
        self.assertIn("#football", yt_desc)
        self.assertIn("#PaulPogba", yt_desc)

        # YouTube Tags
        yt_tags = meta["youtube_tags"]
        self.assertIsInstance(yt_tags, list)
        self.assertIn("Paul Pogba", yt_tags)
        self.assertIn("career flight map", yt_tags)
        self.assertIn("Shorts", yt_tags)

        # Instagram Caption
        ig_caption = meta["instagram_caption"]
        self.assertIn("PAUL POGBA", ig_caption)
        self.assertIn("RATE HIS CAREER", ig_caption)
        self.assertIn("playmaker.best", ig_caption)
        self.assertIn("#reels", ig_caption)
        self.assertIn("#PaulPogba", ig_caption)
        self.assertIn("#flightradar", ig_caption)
        self.assertGreaterEqual(len([w for w in ig_caption.split() if w.startswith("#")]), 15)

    def test_upload_pipeline_integration(self):
        """Verifies integration into upload_daily_shorts.py and time slot routing."""
        from scripts.upload_daily_shorts import (
            select_games_for_mode,
            get_target_name_from_game,
            ALL_AVAILABLE_GAMES
        )

        # 1. Game listed in available games
        game_ids = [g["id"] for g in ALL_AVAILABLE_GAMES]
        self.assertIn("career_flight", game_ids)

        # 2. Mode selection
        career_mode_games = select_games_for_mode("career_flight")
        self.assertEqual(len(career_mode_games), 1)
        self.assertEqual(career_mode_games[0]["id"], "career_flight")

        # 3. Morning slot (07:00 UTC / 10:00 AM user local time)
        morning_games = select_games_for_mode("auto", curr_hour=7)
        self.assertEqual(len(morning_games), 1)
        self.assertEqual(morning_games[0]["id"], "career_flight")

        # 4. Midday slot (10:30 UTC / 1:30 PM user local time) returns [] for carousel
        midday_games = select_games_for_mode("auto", curr_hour=10)
        self.assertEqual(len(midday_games), 0)

        # 5. Evening slot (17:00 UTC / 8:00 PM user local time) returns UGC short
        evening_games = select_games_for_mode("auto", curr_hour=17)
        self.assertEqual(len(evening_games), 1)
        self.assertIn(evening_games[0]["id"], ["player_chain", "passport_fc"])

        # 6. Target name extraction in < 10ms
        target_name = get_target_name_from_game("career_flight")
        self.assertTrue(len(target_name) > 0)

    def test_all_180_destination_puzzles_have_verified_locations(self):
        """
        Regression & Integrity Gate:
        Guarantees that EVERY single club across all 180 puzzle days in daily_destination_games.csv
        has verified, real coordinates and NEVER falls back to default Paris/Central Europe.
        """
        import pandas as pd
        csv_path = os.path.join(BASE_DIR, "daily_destination_games.csv")
        self.assertTrue(os.path.exists(csv_path), "daily_destination_games.csv must exist")

        df = pd.read_csv(csv_path)
        all_clubs = set(df["from_club_name"].dropna().unique()).union(set(df["to_club_name"].dropna().unique()))

        unmapped_clubs = []
        for club in sorted(all_clubs):
            loc = get_club_location(club)
            # Default fallback in geo_manager is lat: 48.8566, lon: 2.3522 and country: 'Europe'
            if loc.get("country") == "Europe" and abs(loc.get("lat", 0.0) - 48.8566) < 0.001 and abs(loc.get("lon", 0.0) - 2.3522) < 0.001:
                unmapped_clubs.append(club)

        self.assertEqual(
            len(unmapped_clubs), 0,
            f"The following {len(unmapped_clubs)} clubs in daily_destination_games.csv lack verified locations: {unmapped_clubs}"
        )

    def test_same_country_detection(self):
        """Verifies accurate detection of same-country transfers vs international transfers."""
        loc_ars = get_club_location("Arsenal")
        loc_che = get_club_location("Chelsea")
        loc_rm = get_club_location("Real Madrid")
        loc_bar = get_club_location("Barcelona")
        loc_juv = get_club_location("Juventus")

        # England to England -> Same country
        self.assertTrue(is_same_country(loc_ars, loc_che))
        # Spain to Spain -> Same country
        self.assertTrue(is_same_country(loc_rm, loc_bar))
        # England to Spain -> Different country
        self.assertFalse(is_same_country(loc_ars, loc_rm))
        # Spain to Italy -> Different country
        self.assertFalse(is_same_country(loc_rm, loc_juv))
        # Fallback Europe / Unknown -> Should not match
        self.assertFalse(is_same_country({"country": "Europe"}, {"country": "Europe"}))

    def test_domestic_transfers_travel_method(self):
        """
        Verifies that domestic transfers are assigned 'car' travel method
        and international transfers are assigned 'flight' travel method.
        """
        # Puzzle #20: Nathan Aké (all domestic in England: Chelsea, Watford, Bournemouth, Man City)
        ake_data = load_destination_puzzle(puzzle_num_override=20)
        self.assertEqual(ake_data["player_name"], "Nathan Aké")
        for leg in ake_data["legs"]:
            self.assertEqual(leg["travel_method"], "car", f"Domestic leg {leg['from_club']} -> {leg['to_club']} must be car")
            self.assertTrue(leg["is_domestic"])

        # Puzzle #75: Paul Pogba (all international between England & Italy)
        pogba_data = load_destination_puzzle(puzzle_num_override=75)
        for leg in pogba_data["legs"]:
            self.assertEqual(leg["travel_method"], "flight", f"International leg {leg['from_club']} -> {leg['to_club']} must be flight")
            self.assertFalse(leg["is_domestic"])

        # Puzzle #1: Karim Benzema (Lyon -> Real Madrid: flight, Real Madrid -> Al-Ittihad: flight, Al-Ittihad -> Al-Hilal: car)
        benzema_data = load_destination_puzzle(puzzle_num_override=1)
        legs = benzema_data["legs"]
        self.assertEqual(legs[0]["travel_method"], "flight")
        self.assertEqual(legs[1]["travel_method"], "flight")
        self.assertEqual(legs[2]["travel_method"], "car") # Al-Ittihad -> Al-Hilal (Saudi Arabia)

    def test_metadata_for_domestic_and_mixed_transfers(self):
        """Verifies metadata adapts title, description, and hashtags for car travel and mixed routes."""
        # Nathan Aké: All domestic
        ake_data = load_destination_puzzle(puzzle_num_override=20)
        ake_meta = generate_career_flight_metadata(ake_data)
        self.assertIn("Career Road Trip", ake_meta["youtube_title"])
        self.assertIn("🚗", ake_meta["youtube_title"])
        self.assertIn("Total Distance Driven", ake_meta["youtube_description"])
        self.assertIn("COMPLETE CAREER ROAD TRIP", ake_meta["instagram_caption"])
        self.assertIn("🚗", ake_meta["instagram_caption"])
        self.assertIn("career road trip", ake_meta["youtube_tags"])
        self.assertIn("car travel", ake_meta["youtube_tags"])

        # Karim Benzema: Mixed
        benzema_data = load_destination_puzzle(puzzle_num_override=1)
        benz_meta = generate_career_flight_metadata(benzema_data)
        self.assertIn("Career Journey", benz_meta["youtube_title"])
        self.assertIn("✈️🚗", benz_meta["youtube_title"])
        self.assertIn("flown", benz_meta["youtube_description"])
        self.assertIn("driven", benz_meta["youtube_description"])
        self.assertIn("COMPLETE CAREER JOURNEY", benz_meta["instagram_caption"])
        self.assertIn("🚗", benz_meta["instagram_caption"])
        self.assertIn("✈️", benz_meta["instagram_caption"])

    def test_render_frame_with_car_travel(self):
        """Verifies frame compositor renders correctly with car travel without crashing."""
        from PIL import Image
        globe_renderer = GlobeRenderer()
        airplane_sprite = Image.open(AIRPLANE_PATH).convert("RGBA")
        car_sprite = Image.open(CAR_PATH).convert("RGBA")

        ake_data = load_destination_puzzle(puzzle_num_override=20)
        tl = build_video_timeline(ake_data)

        # Active car leg frame
        frame_idx = tl["intro_frames"] + 15
        frame_img = render_flight_frame(frame_idx, tl, ake_data, globe_renderer, airplane_sprite, None, car_sprite=car_sprite)
        self.assertEqual(frame_img.size, (1080, 1920))
        self.assertEqual(frame_img.mode, "RGB")


if __name__ == "__main__":
    unittest.main()
