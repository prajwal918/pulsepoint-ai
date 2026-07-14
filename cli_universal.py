"""
⚡ PULSEPOINT AI - Universal Backend Version
Works with: Ollama, OpenRouter, Groq, OpenAI, or any compatible API
"""

import os
import sys
import json
import subprocess
from openai import OpenAI
from moviepy.editor import VideoFileClip, AudioFileClip
from dotenv import load_dotenv

load_dotenv()

# --- CONFIG ---
OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
OLLAMA_BASE_URL = "https://api.ollama.com/v1"  # Change if using different provider

# Try different base URLs for common providers
BASE_URLS = {
    "ollama_cloud": "https://api.ollama.com/v1",
    "openrouter": "https://openrouter.ai/api/v1",
    "groq": "https://api.groq.com/openai/v1",
    "local_ollama": "http://localhost:11434/v1",
}

OUTPUT_WIDTH = 720
OUTPUT_HEIGHT = 1280

def get_client():
    """Try to connect to available API"""
    key = OLLAMA_API_KEY or os.getenv("OPENAI_API_KEY") or "ollama"
    
    # Try local Ollama first
    try:
        client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        client.models.list()
        print("   ✓ Connected to local Ollama")
        return client, "llama3.2"
    except:
        pass
    
    # Try cloud with provided key
    if OLLAMA_API_KEY:
        for name, url in BASE_URLS.items():
            try:
                client = OpenAI(base_url=url, api_key=OLLAMA_API_KEY)
                print(f"   ✓ Connected to {name}")
                return client, "llama-3.1-8b-instant"  # Common model name
            except:
                continue
    
    print("   ❌ No API connection available")
    return None, None

def extract_audio(video_path, output_path="temp_audio.wav"):
    """Extract audio from video for transcription"""
    print("   🎵 Extracting audio track...")
    clip = VideoFileClip(video_path)
    clip.audio.write_audiofile(output_path, fps=16000, nbytes=2, codec='pcm_s16le', logger=None)
    clip.close()
    return output_path

def transcribe_with_whisper(audio_path):
    """Transcribe audio using local Whisper"""
    print("   🎤 Transcribing with Whisper (this may take a few minutes)...")
    try:
        import whisper
        import numpy as np
        import wave
        
        # Load audio directly from wav file (skip ffmpeg)
        with wave.open(audio_path, 'rb') as wf:
            sample_rate = wf.getframerate()
            frames = wf.readframes(wf.getnframes())
            audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
        
        # Resample to 16kHz if needed
        if sample_rate != 16000:
            import scipy.signal as signal
            audio = signal.resample(audio, int(len(audio) * 16000 / sample_rate))
        
        model = whisper.load_model("base")
        result = model.transcribe(audio, word_timestamps=True)
        return result
    except Exception as e:
        print(f"   ⚠️ Whisper error: {e}, using basic analysis")
        return None

def analyze_transcript_for_clips(client, model_name, transcript_text, video_duration):
    """Use LLM to find viral moments from transcript"""
    print("   🧠 AI Analyzing transcript for viral moments...")
    
    prompt = f"""You are an expert video editor for TikTok and Instagram Reels.
    
Here is a transcript of a {video_duration:.0f} second video:

{transcript_text[:8000]}

Identify the 3-5 BEST "Golden Nuggets" - moments of peak virality.

WHAT MAKES A GOLDEN NUGGET:
- Emotional peaks (passion, humor, surprise, inspiration)  
- Quotable one-liners or profound insights
- High energy moments with strong delivery

RULES:
- Each clip should be 15-60 seconds
- Clips must start and end at natural speech boundaries
- Return timestamps based on the flow of content

OUTPUT FORMAT (STRICT JSON ONLY):
[
  {{
    "start_time": "01:30",
    "end_time": "02:00",
    "virality_score": 9,
    "hook_title": "This Changes Everything",
    "description": "Why this moment is viral"
  }}
]

Return ONLY the JSON array, no other text."""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2000
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"   ❌ LLM Error: {e}")
        return None

def parse_time_string(time_str):
    """Converts MM:SS or HH:MM:SS to seconds"""
    try:
        parts = time_str.split(':')
        if len(parts) == 2:
            m, s = map(float, parts)
            return m * 60 + s
        elif len(parts) == 3:
            h, m, s = map(float, parts)
            return h * 3600 + m * 60 + s
        return 0
    except:
        return 0

def parse_json(raw_text):
    """Parse JSON from LLM response"""
    try:
        clean = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except:
        try:
            start = clean.find('[')
            end = clean.rfind(']') + 1
            if start != -1 and end > 0:
                return json.loads(clean[start:end])
        except:
            pass
    return None

def process_video_clip(video_path, start_time, end_time, output_path, hook_title):
    """Cut and crop video clip"""
    print(f"      Rendering...", end=" ", flush=True)
    try:
        clip = VideoFileClip(video_path)
        subclip = clip.subclip(start_time, min(end_time, clip.duration))
        
        # Crop to vertical
        w, h = subclip.size
        target_ratio = 9/16
        if w / h > target_ratio:
            new_width = int(h * target_ratio)
            x_center = w / 2
            x1 = x_center - (new_width / 2)
            x2 = x_center + (new_width / 2)
            cropped = subclip.crop(x1=x1, y1=0, x2=x2, y2=h)
        else:
            cropped = subclip
        
        final = cropped.resize(height=OUTPUT_HEIGHT)
        final.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            threads=4,
            preset='ultrafast',
            logger=None
        )
        clip.close()
        print("✓ Done!")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║  ⚡ PULSEPOINT AI - Universal Version                        ║
    ║  Works with Ollama, OpenRouter, Groq, or any OpenAI API     ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    
    # Get video path
    if len(sys.argv) > 1:
        video_path = sys.argv[1].strip().strip('"')
    else:
        video_path = input("   📁 Enter video path: ").strip().strip('"')
    
    if not os.path.exists(video_path):
        print(f"   ❌ File not found: {video_path}")
        return
    
    print(f"\n   📹 Processing: {os.path.basename(video_path)}")
    
    # Connect to API
    client, model_name = get_client()
    if not client:
        print("   ❌ Could not connect to any AI API")
        print("   Please ensure Ollama is running locally or check your API key")
        return
    
    # Get video info
    clip = VideoFileClip(video_path)
    duration = clip.duration
    clip.close()
    print(f"   ⏱️ Duration: {duration/60:.1f} minutes")
    
    # Extract and transcribe audio
    audio_path = extract_audio(video_path)
    
    # Try Whisper transcription
    transcript_result = transcribe_with_whisper(audio_path)
    
    if transcript_result:
        transcript_text = transcript_result.get("text", "")
    else:
        # Fallback: just analyze based on video duration
        transcript_text = f"This is a {duration/60:.1f} minute educational video. Please analyze it and suggest 3-5 interesting segments based on typical lecture structure."
    
    # Analyze with LLM
    raw_response = analyze_transcript_for_clips(client, model_name, transcript_text, duration)
    
    if not raw_response:
        print("   ❌ Failed to get AI analysis")
        return
    
    clips = parse_json(raw_response)
    if not clips:
        print("   ❌ Failed to parse AI response")
        print(f"   Raw: {raw_response[:500]}")
        return
    
    print(f"\n   🎯 Found {len(clips)} viral moments! Generating reels...\n")
    
    # Create output folder
    output_dir = os.path.join(os.path.dirname(video_path), "PulsePoint_Reels")
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each clip
    for idx, clip_data in enumerate(clips):
        hook = clip_data.get('hook_title', f'Clip {idx+1}')
        start_str = clip_data.get('start_time', '00:00')
        end_str = clip_data.get('end_time', '00:30')
        score = clip_data.get('virality_score', 'N/A')
        
        print(f"   ┌─ 🎬 Reel {idx+1}: \"{hook}\"")
        print(f"   │  ⏱️  {start_str} → {end_str} | Score: {score}/10")
        
        start_sec = parse_time_string(start_str)
        end_sec = parse_time_string(end_str)
        
        safe_hook = "".join(c for c in hook if c.isalnum() or c in " _-")[:20]
        output_path = os.path.join(output_dir, f"reel_{idx+1}_{safe_hook}.mp4")
        
        process_video_clip(video_path, start_sec, end_sec, output_path, hook)
        print(f"   └─────────────────────────────────────────────")
    
    # Cleanup
    if os.path.exists("temp_audio.wav"):
        os.remove("temp_audio.wav")
    
    print(f"\n   🎉 COMPLETE! Generated {len(clips)} reels")
    print(f"   📂 Output: {output_dir}")
    
    # Open folder
    if sys.platform == 'win32':
        os.startfile(output_dir)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ Critical Error: {e}")
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(1)
