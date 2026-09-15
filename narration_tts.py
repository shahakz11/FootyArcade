#!/usr/bin/env python3
"""
Playmaker Social Video Narration & Commentary Engine.
Uses edge-tts (zero-cost neural voice synthesis) with energetic sports commentary delivery
to narrate daily football shorts and reels.
"""

import os
import re
import sys
import asyncio
import tempfile
import subprocess
import numpy as np
import scipy.io.wavfile as wavfile
import imageio_ffmpeg

SAMPLE_RATE = 44100
DEFAULT_VOICE = "en-GB-RyanNeural" # Energetic British sports commentator tone
DEFAULT_RATE = "+12%"

def _clean_text_for_speech(text):
    """Sanitizes text for clean pronunciation by the TTS engine."""
    t = str(text or "").strip()
    # Expand common football abbreviations
    t = re.sub(r'\bFC\b', 'F C', t)
    t = re.sub(r'\bUCL\b', 'Champions League', t)
    t = re.sub(r'\bPL\b', 'Premier League', t)
    t = re.sub(r'\bCR7\b', 'Cristiano Ronaldo', t)
    t = re.sub(r'#(\d+)', r'number \1', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t

async def synthesize_text_to_wav(text, output_wav_path, voice=DEFAULT_VOICE, rate=DEFAULT_RATE):
    """
    Synthesizes a short text line to a 44.1kHz mono WAV file using edge-tts and FFmpeg.
    Returns output_wav_path on success, or None on failure.
    """
    cleaned = _clean_text_for_speech(text)
    if not cleaned:
        return None

    try:
        import edge_tts
    except ImportError:
        print("⚠️ edge-tts is not installed. Skipping voice synthesis.")
        return None

    temp_mp3 = output_wav_path + ".tmp.mp3"
    try:
        communicate = edge_tts.Communicate(cleaned, voice=voice, rate=rate)
        await communicate.save(temp_mp3)

        if not os.path.exists(temp_mp3) or os.path.getsize(temp_mp3) < 100:
            return None

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        cmd = [
            ffmpeg_exe, "-y",
            "-i", temp_mp3,
            "-ar", str(SAMPLE_RATE),
            "-ac", "1",
            output_wav_path
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(output_wav_path):
            return output_wav_path
        else:
            return None
    except Exception as e:
        print(f"⚠️ TTS synthesis error for '{text[:30]}...': {e}")
        return None
    finally:
        if os.path.exists(temp_mp3):
            try:
                os.remove(temp_mp3)
            except Exception:
                pass

def format_fee_spoken(fee):
    """Formats numeric transfer fees into natural spoken phrases."""
    try:
        f = float(fee)
        if f <= 0:
            return "a free transfer"
        m = round(f / 1000000.0)
        if m >= 100:
            return f"over {m} million euros"
        return f"{m} million euros"
    except Exception:
        return "a record fee"

def get_game_voice_script(game_id, target_name="", extra_data=None):
    """
    Generates a structured commentary script tailored to today's specific puzzle data.
    Announces the exact position and clues BEFORE the answer is submitted.
    """
    extra_data = extra_data or {}
    clean_target = str(target_name or "").strip()

    if game_id == "top_transfers":
        transfers = extra_data.get("transfers", [])
        t1_fee = format_fee_spoken(transfers[0].get("transfer_fee")) if len(transfers) > 0 else "a record fee"
        t2_from = transfers[1].get("from_club_name", "another club") if len(transfers) > 1 else "another club"
        t2_fee = format_fee_spoken(transfers[1].get("transfer_fee")) if len(transfers) > 1 else "a massive fee"
        t4_from = transfers[3].get("from_club_name", "another club") if len(transfers) > 3 else "another club"
        t4_fee = format_fee_spoken(transfers[3].get("transfer_fee")) if len(transfers) > 3 else "a high fee"
        t5_from = transfers[4].get("from_club_name", "another club") if len(transfers) > 4 else "another club"
        t5_fee = format_fee_spoken(transfers[4].get("transfer_fee")) if len(transfers) > 4 else "a big fee"

        return {
            "intro": f"Can you guess {clean_target or 'this club'}'s top five record transfers? Let's test your ball knowledge!",
            "guess_5": f"Can you guess number five? Signed from {t5_from} for {t5_fee}!",
            "guess_4": f"Next up is number four! Signed from {t4_from} for {t4_fee}!",
            "guess_2": f"And coming in at number two! Signed from {t2_from} for {t2_fee}!",
            "cliffhanger": f"We skipped number three and the record-breaking number one of {t1_fee}! Who is number one? Pause and comment below!",
            "outro": "Play today's free daily challenge at playmaker dot best, link in bio!"
        }
    elif game_id == "top_scorers":
        scorers = extra_data.get("scorers", [])
        s1_goals = scorers[0].get("goals", "top") if len(scorers) > 0 else "record"
        s2 = scorers[1] if len(scorers) > 1 else {}
        s4 = scorers[3] if len(scorers) > 3 else {}
        s5 = scorers[4] if len(scorers) > 4 else {}

        return {
            "intro": f"Who scored the most goals in {clean_target or 'this competition'}? Let's find out!",
            "guess_5": f"Can you guess number five? He scored {s5.get('goals', 14)} goals for {s5.get('club_name', 'his club')}!",
            "guess_4": f"Next is number four! {s4.get('goals', 14)} goals for {s4.get('club_name', 'his club')}!",
            "guess_2": f"Coming in at number two! {s2.get('goals', 15)} goals for {s2.get('club_name', 'his club')}!",
            "cliffhanger": f"Who is the all-time number one top scorer with {s1_goals} goals? Drop your guess in the comments!",
            "outro": "Test your football IQ at playmaker dot best, link in bio!"
        }
    elif game_id == "transfer_destination":
        transfers = extra_data.get("transfers", [])
        step1_to = transfers[0].get("to_club_name", "his current club") if transfers else "his club"
        step1_from = transfers[0].get("from_club_name", "another club") if transfers else "another club"
        step2_from = transfers[1].get("from_club_name", "his previous club") if len(transfers) > 1 else "another club"

        return {
            "intro": "Can you guess this mystery player's career path backwards?",
            "wrong_1": "Not that club! Try again!",
            "step_1": f"First destination backwards! Which club did he play for before moving to {step1_to}?",
            "step_2": f"Before {step1_from}, which club did he play for next backwards?",
            "cliffhanger": "Can you name this mystery player and where his career started? Drop your answer in the comments!",
            "outro": "Play the full mystery player career at playmaker dot best!"
        }
    elif game_id == "club_connect":
        players = extra_data.get("players", [])
        p1 = players[0] if len(players) > 0 else "this star"
        p2 = players[1] if len(players) > 1 else "this star"

        return {
            "intro": "Which mystery club did all these football stars transfer to?",
            "clue_1": f"First clue! {p1} played for today's mystery club!",
            "clue_2": f"Second clue! {p2} also played here!",
            "cliffhanger": "What club connects all of them? Comment your guess before time runs out!",
            "outro": "Play live on playmaker dot best!"
        }
    elif game_id == "player_chain":
        steps = extra_data.get("steps", [])
        s1_club = steps[0].get("club", "this club") if steps else "this club"
        s2_clubs = " and ".join(steps[1].get("active_clubs", [])) if len(steps) > 1 else "these clubs"

        return {
            "intro": "Can you crack today's teammate transfer chain?",
            "step_1": f"Step one! Name a teammate who played for {s1_club}!",
            "wrong_1": "Not him! Keep thinking!",
            "step_2": f"Step two! Name a player connecting {s2_clubs}!",
            "cliffhanger": "Who is the mystery target player linking all of them? Comment your answer below!",
            "outro": "Solve the full chain at playmaker dot best!"
        }
    elif game_id == "passport_fc":
        steps = extra_data.get("steps", [])
        n1 = steps[0].get("nationality", "first nationality") if steps else "first nationality"
        n2 = steps[1].get("nationality", "second nationality") if len(steps) > 1 else "second nationality"

        return {
            "intro": f"Can you complete the club passport for {clean_target or 'today'}?",
            "step_1": f"First player! Name a {n1} star who played for {clean_target}!",
            "wrong_1": "Not on this team!",
            "step_2": f"Second player! Name a {n2} star for this club!",
            "cliffhanger": "Can you complete the remaining nationalities? Drop your answers in the comments!",
            "outro": "Play today's free passport challenge at playmaker dot best!"
        }
    else:
        return {
            "intro": "Daily Football Quiz Challenge! Let's see your ball knowledge!",
            "cliffhanger": "Can you guess the answer? Drop your comment below!",
            "outro": "Play today's free puzzle at playmaker dot best!"
        }

async def pre_synthesize_voice_script(script_dict, temp_dir, voice=DEFAULT_VOICE, rate=DEFAULT_RATE):
    """
    Synthesizes each cue in script_dict to temp_dir and returns:
    { cue_key: {"text": text, "wav_path": path, "duration": dur_sec} }
    """
    results = {}
    for key, text in script_dict.items():
        if not text:
            continue
        out_wav = os.path.join(temp_dir, f"cue_{key}.wav")
        res = await synthesize_text_to_wav(text, out_wav, voice=voice, rate=rate)
        if res and os.path.exists(res):
            try:
                sr, data = wavfile.read(res)
                dur = len(data) / float(sr)
                results[key] = {"text": text, "wav_path": res, "duration": dur}
            except Exception:
                results[key] = {"text": text, "wav_path": res, "duration": 2.0}
        else:
            results[key] = {"text": text, "wav_path": None, "duration": 2.0}
    return results

def generate_narration_audio_track_from_cues(cue_placements, total_duration, output_wav_path):
    """
    Assembles synthesized audio cue files placed at specific timestamps into a single WAV track.
    cue_placements: list of (wav_path, timestamp_sec)
    """
    total_samples = int(SAMPLE_RATE * (total_duration + 1.0))
    master_audio = np.zeros(total_samples, dtype=np.float32)
    any_success = False

    for wav_path, time_sec in cue_placements:
        if not wav_path or not os.path.exists(wav_path) or time_sec < 0 or time_sec >= total_duration:
            continue
        try:
            sr, data = wavfile.read(wav_path)
            if data.dtype == np.int16:
                clip_float = data.astype(np.float32) / 32768.0
            elif data.dtype == np.int32:
                clip_float = data.astype(np.float32) / 2147483648.0
            else:
                clip_float = data.astype(np.float32)

            if len(clip_float.shape) > 1:
                clip_float = np.mean(clip_float, axis=1)

            start_sample = int(time_sec * SAMPLE_RATE)
            end_sample = min(start_sample + len(clip_float), total_samples)
            valid_len = end_sample - start_sample

            if valid_len > 0:
                master_audio[start_sample:end_sample] += clip_float[:valid_len]
                any_success = True
        except Exception as e:
            print(f"⚠️ Error loading cue {wav_path}: {e}")

    if not any_success:
        return None

    max_val = np.max(np.abs(master_audio))
    if max_val > 0.95:
        master_audio = master_audio / max_val * 0.95

    audio_pcm = (master_audio * 32767).astype(np.int16)
    wavfile.write(output_wav_path, SAMPLE_RATE, audio_pcm)
    return output_wav_path

async def generate_narration_audio_track(voice_events, total_duration, output_wav_path, voice=DEFAULT_VOICE, rate=DEFAULT_RATE):
    """
    Given a list of (cue_text, timestamp_sec), synthesizes each cue and places it
    at timestamp_sec on a silent 44.1kHz audio buffer.
    Returns output_wav_path on success, or None on failure.
    """
    if not voice_events:
        return None

    total_samples = int(SAMPLE_RATE * (total_duration + 1.0))
    master_audio = np.zeros(total_samples, dtype=np.float32)
    any_success = False

    with tempfile.TemporaryDirectory() as temp_dir:
        for idx, (cue_text, time_sec) in enumerate(voice_events):
            if not cue_text or time_sec < 0 or time_sec >= total_duration:
                continue

            clip_wav = os.path.join(temp_dir, f"clip_{idx}.wav")
            res_path = await synthesize_text_to_wav(cue_text, clip_wav, voice=voice, rate=rate)
            if not res_path or not os.path.exists(res_path):
                continue

            try:
                rate_read, data = wavfile.read(res_path)
                if data.dtype == np.int16:
                    clip_float = data.astype(np.float32) / 32768.0
                elif data.dtype == np.int32:
                    clip_float = data.astype(np.float32) / 2147483648.0
                else:
                    clip_float = data.astype(np.float32)

                # If stereo, average to mono
                if len(clip_float.shape) > 1:
                    clip_float = np.mean(clip_float, axis=1)

                start_sample = int(time_sec * SAMPLE_RATE)
                end_sample = min(start_sample + len(clip_float), total_samples)
                valid_len = end_sample - start_sample

                if valid_len > 0:
                    master_audio[start_sample:end_sample] += clip_float[:valid_len]
                    any_success = True
            except Exception as e:
                print(f"⚠️ Could not load audio clip {clip_wav}: {e}")

    if not any_success:
        return None

    # Normalize voice track to -1.0 to 1.0 without hard clipping
    max_val = np.max(np.abs(master_audio))
    if max_val > 0.95:
        master_audio = master_audio / max_val * 0.95

    audio_pcm = (master_audio * 32767).astype(np.int16)
    wavfile.write(output_wav_path, SAMPLE_RATE, audio_pcm)
    return output_wav_path

if __name__ == "__main__":
    # Quick standalone test
    async def _test():
        script = get_game_voice_script("top_transfers", "Chelsea")
        print("Test Script:", script)
        events = [
            (script["intro"], 0.2),
            (script["guess_5"], 4.0),
            (script["cliffhanger"], 8.0)
        ]
        out_path = "test_narration.wav"
        res = await generate_narration_audio_track(events, 14.0, out_path)
        if res and os.path.exists(res):
            print(f"✅ Narration track successfully generated: {res} ({os.path.getsize(res)} bytes)")
            os.remove(res)

    asyncio.run(_test())
