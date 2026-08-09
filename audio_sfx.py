#!/usr/bin/env python3
import os
import math
import subprocess
import numpy as np
import scipy.io.wavfile as wavfile
import imageio_ffmpeg

SAMPLE_RATE = 44100

def generate_tick_sound(is_tok=False):
    """Generates a crisp 40ms clock tick ('tik' or 'tok') impulse sound."""
    duration = 0.045
    num_samples = int(SAMPLE_RATE * duration)
    t = np.linspace(0, duration, num_samples, endpoint=False)
    
    freq = 900.0 if is_tok else 1350.0
    # Pitch drop decay
    pitch = freq * np.exp(-t * 60)
    phase = 2 * np.pi * np.cumsum(pitch) / SAMPLE_RATE
    
    # Sharp exponential attack and fast decay
    envelope = np.exp(-t * 120)
    wave = np.sin(phase) * envelope * 0.7
    
    # Add a touch of noise for mechanical wood-block feel
    noise = (np.random.rand(num_samples) * 2 - 1) * np.exp(-t * 200) * 0.25
    audio = wave + noise
    return audio

def generate_correct_sound():
    """Generates an uplifting 3-note arcade chime (C5 -> E5 -> G5)."""
    notes = [523.25, 659.25, 783.99] # C5, E5, G5
    note_dur = 0.12
    total_samples = int(SAMPLE_RATE * (note_dur * 3 + 0.15))
    audio = np.zeros(total_samples)
    
    for idx, freq in enumerate(notes):
        start_sample = int(idx * note_dur * SAMPLE_RATE)
        dur = 0.25
        num_s = int(SAMPLE_RATE * dur)
        t = np.linspace(0, dur, num_s, endpoint=False)
        
        # Fundamental + harmonic
        sig = np.sin(2 * np.pi * freq * t) * 0.6 + np.sin(2 * np.pi * freq * 2 * t) * 0.25
        envelope = np.exp(-t * 12)
        tone = sig * envelope
        
        end_s = min(start_sample + num_s, total_samples)
        valid_len = end_s - start_sample
        audio[start_sample:end_s] += tone[:valid_len]
        
    return audio * 0.75

def generate_wrong_sound():
    """Generates a low retro game error buzzer sound."""
    dur = 0.35
    num_s = int(SAMPLE_RATE * dur)
    t = np.linspace(0, dur, num_s, endpoint=False)
    
    # Dual low frequencies with vibrato/buzz
    f1, f2 = 145.0, 110.0
    sig1 = np.sign(np.sin(2 * np.pi * f1 * t)) # Square wave buzz
    sig2 = np.sign(np.sin(2 * np.pi * f2 * t))
    
    envelope = np.exp(-t * 6)
    audio = (sig1 + sig2) * 0.3 * envelope
    return audio

def build_audio_track(events, total_duration, output_wav_path):
    """
    Builds a composite audio track from timeline events:
    events = [
        ('tick_3', timestamp_sec),
        ('tick_2', timestamp_sec),
        ('tick_1', timestamp_sec),
        ('correct', timestamp_sec),
        ('wrong', timestamp_sec)
    ]
    """
    total_samples = int(SAMPLE_RATE * (total_duration + 0.5))
    audio_track = np.zeros(total_samples, dtype=np.float32)
    
    tick_sound = generate_tick_sound(is_tok=False)
    tok_sound = generate_tick_sound(is_tok=True)
    correct_sound = generate_correct_sound()
    wrong_sound = generate_wrong_sound()
    
    for ev_type, time_sec in events:
        start_idx = int(time_sec * SAMPLE_RATE)
        if start_idx < 0 or start_idx >= total_samples:
            continue
            
        if ev_type in ['tick_3', 'tick_1']:
            clip = tick_sound
        elif ev_type in ['tick_2', 'tick_go']:
            clip = tok_sound
        elif ev_type == 'correct':
            clip = correct_sound
        elif ev_type == 'wrong':
            clip = wrong_sound
        else:
            continue
            
        end_idx = min(start_idx + len(clip), total_samples)
        length = end_idx - start_idx
        audio_track[start_idx:end_idx] += clip[:length]
        
    # Clip to prevent distortion & normalize
    max_val = np.max(np.abs(audio_track))
    if max_val > 0.95:
        audio_track = audio_track / max_val * 0.95
        
    # Convert to 16-bit PCM WAV
    audio_pcm = (audio_track * 32767).astype(np.int16)
    wavfile.write(output_wav_path, SAMPLE_RATE, audio_pcm)
    return output_wav_path

def mux_audio_to_video(video_path, wav_path, final_output_path):
    """Muxes the generated WAV audio track into the MP4 video file using FFmpeg."""
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    temp_out = final_output_path + ".tmp.mp4"
    
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i", video_path,
        "-i", wav_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        temp_out
    ]
    
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if res.returncode == 0 and os.path.exists(temp_out):
        os.replace(temp_out, final_output_path)
        if os.path.exists(video_path) and video_path != final_output_path:
            try:
                os.remove(video_path)
            except Exception:
                pass
        return final_output_path
    else:
        print(f"⚠️ Warning: FFmpeg audio muxing failed ({res.stderr.decode('utf-8')})")
        return video_path
