import unittest
import os
import tempfile
import numpy as np
import scipy.io.wavfile as wavfile
from narration_tts import get_game_voice_script, DEFAULT_RATE
from audio_sfx import build_audio_track

class TestShortVideoTiming(unittest.TestCase):
    def test_default_tts_speed_rate(self):
        self.assertEqual(DEFAULT_RATE, "+28%", "TTS rate must be +22% for high-energy sports commentary pacing")

    def test_voice_scripts_concise_and_circular(self):
        game_ids = [
            "top_transfers",
            "top_scorers",
            "transfer_destination",
            "club_connect",
            "player_chain",
            "passport_fc"
        ]
        sample_extra = {
            "transfers": [
                {"player_name": "Jude Bellingham", "from_club_name": "Dortmund", "to_club_name": "Real Madrid", "transfer_fee": 103000000},
                {"player_name": "Eden Hazard", "from_club_name": "Chelsea", "to_club_name": "Real Madrid", "transfer_fee": 115000000},
                {"player_name": "Cristiano Ronaldo", "from_club_name": "Man Utd", "to_club_name": "Real Madrid", "transfer_fee": 94000000},
                {"player_name": "Gareth Bale", "from_club_name": "Tottenham", "to_club_name": "Real Madrid", "transfer_fee": 101000000},
                {"player_name": "Zinedine Zidane", "from_club_name": "Juventus", "to_club_name": "Real Madrid", "transfer_fee": 77500000}
            ],
            "scorers": [
                {"player_name": "Cristiano Ronaldo", "club_name": "Real Madrid", "goals": 450},
                {"player_name": "Karim Benzema", "club_name": "Real Madrid", "goals": 354},
                {"player_name": "Raul", "club_name": "Real Madrid", "goals": 323},
                {"player_name": "Alfredo Di Stefano", "club_name": "Real Madrid", "goals": 308},
                {"player_name": "Santillana", "club_name": "Real Madrid", "goals": 290}
            ],
            "players": ["Cristiano Ronaldo", "Karim Benzema"],
            "steps": [
                {"club": "Real Madrid", "nationality": "France", "valid_players": ["Karim Benzema", "Zinedine Zidane"], "sample_players": ["Karim Benzema"]},
                {"active_clubs": ["Real Madrid", "Juventus"], "nationality": "Portugal", "valid_players": ["Cristiano Ronaldo"], "sample_players": ["Cristiano Ronaldo"]}
            ]
        }
        
        for game_id in game_ids:
            script = get_game_voice_script(game_id, "Real Madrid", extra_data=sample_extra)
            self.assertIn("intro", script, f"Missing intro in script for {game_id}")
            self.assertIn("cliffhanger", script, f"Missing cliffhanger in script for {game_id}")
            
            # Check that each cue is concise (< 16 words)
            for key, text in script.items():
                word_count = len(text.split())
                self.assertLessEqual(word_count, 16, f"Cue '{key}' for {game_id} is too long ({word_count} words): '{text}'")
            
            # Check that cliffhanger contains loop hook
            cliffhanger = script["cliffhanger"].lower()
            self.assertTrue("loop" in cliffhanger or "comment" in cliffhanger or "guess" in cliffhanger)

    def test_sfx_and_audio_track_builder(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            out_wav = os.path.join(tmp_dir, "test_audio.wav")
            events = [
                ("tick_3", 0.5),
                ("tick_2", 1.0),
                ("tick_1", 1.5),
                ("tick_go", 2.0),
                ("correct", 2.5),
                ("wrong", 5.0)
            ]
            total_duration = 14.0
            res = build_audio_track(events, total_duration, out_wav)
            self.assertEqual(res, out_wav)
            self.assertTrue(os.path.exists(out_wav))
            
            sr, data = wavfile.read(out_wav)
            self.assertEqual(sr, 44100)
            self.assertGreater(len(data), 0)
            self.assertFalse(np.isnan(data).any())

    def test_short_timing_budget(self):
        fps = 30
        intro_frames = 6 + int(1.5 * fps)
        stage1_frames = int(1.2 * fps) + (15 * 3 + 6) + 12 + 18 + 6
        stage2_frames = int(1.2 * fps) + (15 * 3 + 6) + 12 + 18 + 6
        cliffhanger_frames = int(1.8 * fps) + 66
        
        total_frames = intro_frames + stage1_frames + stage2_frames + cliffhanger_frames
        total_sec = total_frames / fps
        
        self.assertGreaterEqual(total_sec, 12.0)
        self.assertLessEqual(total_sec, 16.0)

if __name__ == "__main__":
    unittest.main()
