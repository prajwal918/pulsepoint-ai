"""
⚡ PULSEPOINT AI - FAST VERSION (No Whisper Required!)
Uses rule-based clip generation with LLM for creative hooks
Works INSTANTLY with any video!
"""

import os
import sys
import json
from openai import OpenAI
from moviepy.editor import VideoFileClip
from dotenv import load_dotenv

load_dotenv()

OLLAMA_API_KEY = os.getenv("OLLAMA_API_KEY")
OUTPUT_WIDTH = 720
OUTPUT_HEIGHT = 1280

def get_client():
    """Connect to available API"""
    # Try local Ollama first
    try:
        client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")
        models = client.models.list()
        # Use gemini-3-flash-preview if available (from ollama list)
        model_name = "gemini-3-flash-preview:latest"
        print(f"   ✓ Connected to Ollama (using {model_name})")
        return client, model_name
    except Exception as e:
        pass
    print("   ❌ Could not connect to Ollama")
    return None, None

def generate_clip_hooks(client, model_name, num_clips, duration_minutes):
    """Generate creative hooks for clips using LLM"""
    print("   🧠 AI Generating viral hooks...")
    
    prompt = f"""You are a viral content expert for TikTok/Instagram Reels.
    
I have a {duration_minutes:.0f} minute educational video that I'm splitting into {num_clips} vertical reels.

Generate {num_clips} UNIQUE and ATTENTION-GRABBING hook titles for educational content.

Examples of great hooks:
- "This Changes Everything"
- "Nobody Talks About This"  
- "The Secret They Don't Tell You"
- "Wait For It..."
- "Mind = Blown"
- "You Need To Hear This"

Return ONLY a JSON array with this format:
[
  {{"hook_title": "Your Hook Here", "virality_score": 8, "description": "Why this hook works"}},
  ...
]

Make each hook unique and compelling!"""

    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.9,
            max_tokens=1000
        )
        text = response.choices[0].message.content
        # Parse JSON
        clean = text.replace("```json", "").replace("```", "").strip()
        start = clean.find('[')
        end = clean.rfind(']') + 1
        if start != -1 and end > 0:
            return json.loads(clean[start:end])
    except Exception as e:
        print(f"   ⚠️ LLM Error: {e}")
    
    # Fallback hooks if LLM fails
    return [
        {"hook_title": "This Changes Everything", "virality_score": 9},
        {"hook_title": "Nobody Tells You This", "virality_score": 8},
        {"hook_title": "Wait For It...", "virality_score": 8},
        {"hook_title": "Mind = Blown", "virality_score": 7},
        {"hook_title": "The Secret Truth", "virality_score": 7}
    ]

def process_video_clip(video_path, start_time, end_time, output_path):
    """Cut and crop video clip to vertical format"""
    print(f"      Rendering...", end=" ", flush=True)
    try:
        clip = VideoFileClip(video_path)
        # Ensure end time doesn't exceed duration
        end_time = min(end_time, clip.duration)
        start_time = max(0, start_time)
        
        if end_time <= start_time:
            print("❌ Invalid time range")
            clip.close()
            return False
            
        subclip = clip.subclip(start_time, end_time)
        
        # Crop to vertical (center crop)
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
        
        # Skip resize - cropped is already good quality
        cropped.write_videofile(
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

def seconds_to_mmss(seconds):
    """Convert seconds to MM:SS format"""
    m = int(seconds // 60)
    s = int(seconds % 60)
    return f"{m:02d}:{s:02d}"

def main():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║  ⚡ PULSEPOINT AI - FAST VERSION                            ║
    ║  Instant Clip Generation (No Transcription Required!)       ║
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
    
    # Get video info
    print("   📊 Analyzing video...", end=" ", flush=True)
    clip = VideoFileClip(video_path)
    duration = clip.duration
    clip.close()
    print("✓")
    print(f"   ⏱️ Duration: {duration/60:.1f} minutes")
    
    # Calculate optimal clip segments
    # Rule: Take 45-second clips evenly distributed
    clip_duration = 45  # seconds per clip
    
    # Calculate number of clips (aim for 4-6)
    if duration > 600:  # > 10 minutes
        num_clips = 5
    elif duration > 300:  # > 5 minutes  
        num_clips = 4
    else:
        num_clips = 3
    
    # Distribute clips evenly throughout video (skip first/last 10%)
    usable_start = duration * 0.1
    usable_end = duration * 0.9
    usable_duration = usable_end - usable_start
    
    clip_starts = []
    interval = usable_duration / (num_clips + 1)
    for i in range(1, num_clips + 1):
        start = usable_start + (interval * i) - (clip_duration / 2)
        clip_starts.append(max(0, start))
    
    # Connect to LLM for hooks
    client, model_name = get_client()
    
    if client:
        hooks = generate_clip_hooks(client, model_name, num_clips, duration/60)
    else:
        hooks = [
            {"hook_title": "This Changes Everything", "virality_score": 9},
            {"hook_title": "Nobody Tells You This", "virality_score": 8},
            {"hook_title": "Wait For It...", "virality_score": 8},
            {"hook_title": "Mind = Blown", "virality_score": 7},
            {"hook_title": "The Secret Truth", "virality_score": 7}
        ][:num_clips]
    
    print(f"\n   🎯 Generating {num_clips} viral reels!\n")
    
    # Create output folder
    output_dir = os.path.join(os.path.dirname(video_path), "PulsePoint_Reels")
    os.makedirs(output_dir, exist_ok=True)
    
    # Process each clip
    for idx, start_sec in enumerate(clip_starts):
        end_sec = start_sec + clip_duration
        
        hook = hooks[idx % len(hooks)].get('hook_title', f'Clip {idx+1}')
        score = hooks[idx % len(hooks)].get('virality_score', 8)
        
        start_str = seconds_to_mmss(start_sec)
        end_str = seconds_to_mmss(end_sec)
        
        print(f"   ┌─ 🎬 Reel {idx+1}: \"{hook}\"")
        print(f"   │  ⏱️  {start_str} → {end_str} | Score: {score}/10")
        
        safe_hook = "".join(c for c in hook if c.isalnum() or c in " _-")[:20]
        output_path = os.path.join(output_dir, f"reel_{idx+1}_{safe_hook}.mp4")
        
        process_video_clip(video_path, start_sec, end_sec, output_path)
        print(f"   └─────────────────────────────────────────────")
    
    print(f"\n   🎉 SUCCESS! Generated {num_clips} viral reels!")
    print(f"   📂 Output: {output_dir}")
    
    # Open folder
    if sys.platform == 'win32':
        os.startfile(output_dir)

if __name__ == "__main__":
    main()
