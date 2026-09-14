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

def get_game_voice_script(game_id, target_name="", extra_data=None):
    """
    Generates a structured commentary script containing cues for the intro,
    each revealed guess, the unrevealed cliffhanger (#1 & #3), and the call to action.
    """
    extra_data = extra_data or {}
    clean_target = str(target_name or "").strip()

    if game_id == "top_transfers":
        return {
            "intro": f"Can you guess {clean_target or 'this club'}'s record transfers? Let's test your ball knowledge!",
            "guess_5": "Starting at number five...",
            "guess_4": "Coming in at number four...",
            "guess_2": "And number two...",
            "cliffhanger": "We skipped number three and the record-breaking number one! Who is number one? Pause and comment below!",
            "outro": "Play today's free daily challenge at playmaker dot best!"
        }
    elif game_id == "top_scorers":
        return {
            "intro": f"Who scored the most goals in {clean_target or 'this competition'}? Let's find out!",
            "guess_5": "Starting off with number five...",
            "guess_4": "At number four...",
            "guess_2": "And number two...",
            "cliffhanger": "Who is the all-time number one top scorer? Drop your guess in the comments!",
            "outro": "Test your football IQ at playmaker dot best!"
        }
    elif game_id == "transfer_destination":
        return {
            "intro": "Can you guess this mystery player's career path backwards?",
            "wrong_1": "Nope! Not that club!",
            "step_1": "First club backwards!",
            "step_2": "Next destination backwards!",
            "cliffhanger": "Can you name his debut club? Drop your answer in the comments right now!",
            "outro": "Play the full mystery player career at playmaker dot best!"
        }
    elif game_id == "club_connect":
        return {
            "intro": "Which mystery club did all these football stars transfer to?",
            "clue_1": "Let's unlock the first player clue...",
            "clue_2": "Here comes another clue...",
            "cliffhanger": "What club connects all of them? Comment your guess before time runs out!",
            "outro": "Play live on playmaker dot best!"
        }
    elif game_id == "player_chain":
        return {
            "intro": "Can you crack today's teammate transfer chain?",
            "step_1": "Starting the link!",
            "wrong_1": "Not him! Keep thinking!",
            "step_2": "Next teammate locked in!",
            "cliffhanger": "Who connects all of them? Comment your answer below!",
            "outro": "Solve the full chain at playmaker dot best!"
        }
    elif game_id == "passport_fc":
        return {
            "intro": f"Can you complete the passport for {clean_target or 'today'}?",
            "step_1": "First nationality locked in!",
            "wrong_1": "Not on this team!",
            "step_2": "Great guess!",
            "cliffhanger": "Can you name the remaining players? Comment your answer below!",
            "outro": "Play today's free passport challenge at playmaker dot best!"
        }
    else:
        return {
            "intro": "Daily Football Quiz Challenge! Let's see your ball knowledge!",
            "cliffhanger": "Can you guess the answer? Drop your comment below!",
            "outro": "Play today's free puzzle at playmaker dot best!"
        }

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
