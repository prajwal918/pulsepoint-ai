"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  ⚡ PULSEPOINT AI - ByteSize Sage Hackathon Entry                            ║
║  Transforms long-form educational content into viral vertical reels          ║
║  Using: Google Gemini 1.5 Flash (1M context) + MoviePy + PIL                ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import google.generativeai as genai
import os
import time
import json
import sys
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, ColorClip
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

# --- CONFIGURATION & SETUP ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("⚠️ Missing Google API Key! Please check your .env file.")
    sys.exit(1)

genai.configure(api_key=api_key)

# --- BRANDING CONFIG ---
BRAND_COLOR = "#FF6B35"  # Orange accent
OUTPUT_WIDTH = 720
OUTPUT_HEIGHT = 1280

# --- GEMINI AI ENGINE ---

def upload_to_gemini(path, mime_type="video/mp4"):
    """Upload video to Gemini File API with progress tracking"""
    print(f"\n   📤 [1/5] Uploading {os.path.basename(path)} to Google Cloud...")
    file = genai.upload_file(path, mime_type=mime_type)
    print(f"   ✓ Uploaded. File ID: {file.name}")
    
    print("   ⏳ [2/5] Processing video (Transcoding)...", end="")
    while file.state.name == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(2)
        file = genai.get_file(file.name)
        
    if file.state.name == "FAILED":
        raise ValueError("Gemini processing failed.")
        
    print("\n   ✓ Video Ready for AI Analysis.")
    return file

def analyze_video_for_clips(file_obj):
    """
    Uses Gemini 1.5 Flash's 1M token context window to analyze entire video
    and identify viral-worthy moments using multimodal understanding.
    """
    print("   🧠 [3/5] AI Watching Video & Finding Emotional Peaks...")
    print("        (Using Gemini 2.0 Flash Lite with 1M token context window)")
    
    model = genai.GenerativeModel(model_name="gemini-2.0-flash-lite")
    
    # Advanced prompt engineering for maximum quality output
    prompt = """
    You are an elite video editor specializing in viral TikTok and Instagram Reels content.
    Your task is to identify the 3-5 BEST "Golden Nuggets" - moments of peak virality.

    WHAT MAKES A GOLDEN NUGGET:
    - Emotional peaks (passion, humor, surprise, inspiration)
    - Quotable one-liners or profound insights
    - High energy moments with strong delivery
    - Visual interest (gestures, expressions, demonstrations)
    - Self-contained ideas that work out of context

    RULES:
    - Each clip should be 15-60 seconds (ideal for Reels/TikTok)
    - Clips must start and end at natural speech boundaries
    - Prioritize moments that would make viewers stop scrolling

    OUTPUT FORMAT (STRICT JSON - NO MARKDOWN):
    Return ONLY a JSON array. Example:
    [
      {
        "start_time": "02:15",
        "end_time": "02:45",
        "virality_score": 9,
        "hook_title": "This Changed Everything",
        "caption_text": "The moment I realized success isn't about working harder...",
        "description": "Speaker delivers powerful insight about redefining success with emotional conviction"
      }
    ]
    
    IMPORTANT: Return ONLY the JSON array, no other text.
    """
    
    response = model.generate_content(
        [file_obj, prompt],
        request_options={"timeout": 600}
    )
    print("   ✓ AI Analysis Complete.")
    return response.text

def get_captions_for_clip(file_obj, start_time, end_time):
    """Generate word-by-word captions for a specific clip segment"""
    model = genai.GenerativeModel(model_name="gemini-2.0-flash-lite")
    
    prompt = f"""
    For the video segment from {start_time} to {end_time}, transcribe the speech 
    and provide word-level timestamps for karaoke-style captions.
    
    OUTPUT FORMAT (STRICT JSON):
    {{
      "words": [
        {{"word": "Hello", "start": 0.0, "end": 0.5}},
        {{"word": "world", "start": 0.6, "end": 1.0}}
      ]
    }}
    
    Times should be relative to clip start (0.0 = clip beginning).
    Return ONLY JSON, no other text.
    """
    
    try:
        response = model.generate_content(
            [file_obj, prompt],
            request_options={"timeout": 120}
        )
        return parse_gemini_json(response.text)
    except:
        return None

# --- JSON PARSING ---

def parse_gemini_json(raw_text):
    """Robust JSON parser handling LLM formatting quirks"""
    try:
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except json.JSONDecodeError:
        try:
            start = clean_text.find('[')
            end = clean_text.rfind(']') + 1
            if start != -1 and end != 0:
                return json.loads(clean_text[start:end])
            # Try object format
            start = clean_text.find('{')
            end = clean_text.rfind('}') + 1
            if start != -1 and end != 0:
                return json.loads(clean_text[start:end])
        except:
            pass
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

# --- VIDEO PROCESSING ENGINE ---

def create_hook_overlay(text, width, height):
    """Creates a stylish text overlay image for the hook title"""
    # Create transparent image
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Try to use a nice font, fallback to default
    try:
        font = ImageFont.truetype("arial.ttf", 48)
        small_font = ImageFont.truetype("arial.ttf", 24)
    except:
        font = ImageFont.load_default()
        small_font = font
    
    # Draw semi-transparent background bar at top
    bar_height = 120
    draw.rectangle([(0, 0), (width, bar_height)], fill=(0, 0, 0, 180))
    
    # Draw hook text (centered)
    text_upper = text.upper()
    bbox = draw.textbbox((0, 0), text_upper, font=font)
    text_width = bbox[2] - bbox[0]
    x = (width - text_width) // 2
    
    # Draw text with shadow effect
    draw.text((x+2, 37), text_upper, font=font, fill=(0, 0, 0, 255))
    draw.text((x, 35), text_upper, font=font, fill=(255, 107, 53, 255))  # Orange
    
    return img

def create_caption_overlay(text, width, height):
    """Creates bottom caption overlay"""
    img = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except:
        font = ImageFont.load_default()
    
    # Position at bottom
    y_pos = height - 200
    
    # Draw background
    draw.rectangle([(20, y_pos - 10), (width - 20, y_pos + 80)], fill=(0, 0, 0, 160))
    
    # Wrap text if too long
    max_chars = 35
    lines = [text[i:i+max_chars] for i in range(0, len(text), max_chars)]
    
    for i, line in enumerate(lines[:2]):  # Max 2 lines
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x = (width - text_width) // 2
        draw.text((x, y_pos + i * 40), line, font=font, fill=(255, 255, 255, 255))
    
    return img

def generate_thumbnail(video_path, output_path, hook_title, timestamp=1):
    """Generate an eye-catching thumbnail from the video"""
    try:
        clip = VideoFileClip(video_path)
        frame = clip.get_frame(timestamp)
        clip.close()
        
        # Convert to PIL Image
        img = Image.fromarray(frame)
        
        # Resize to vertical
        img = img.resize((OUTPUT_WIDTH, OUTPUT_HEIGHT), Image.Resampling.LANCZOS)
        
        # Add hook text overlay
        overlay = create_hook_overlay(hook_title, OUTPUT_WIDTH, OUTPUT_HEIGHT)
        img = img.convert('RGBA')
        img = Image.alpha_composite(img, overlay)
        
        # Save
        img.convert('RGB').save(output_path, quality=95)
        return True
    except Exception as e:
        print(f"      (Thumbnail generation skipped: {e})")
        return False

def process_video_clip(original_video_path, start_time, end_time, output_path, hook_title, caption_text=None):
    """
    Full video processing pipeline:
    1. Extract subclip
    2. Crop to 9:16 vertical
    3. Add hook title overlay
    4. Add caption (if available)
    5. Render with optimal settings
    """
    print(f"      Rendering...", end=" ", flush=True)
    
    try:
        # Load and subclip
        clip = VideoFileClip(original_video_path)
        subclip = clip.subclip(start_time, end_time)
        
        # Crop to vertical (9:16)
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
        
        # Resize to standard output
        resized = cropped.resize(height=OUTPUT_HEIGHT)
        
        # Create text overlays using MoviePy TextClip
        final_clip = resized
        
        try:
            # Hook title at top
            hook_clip = TextClip(
                hook_title.upper(),
                fontsize=42,
                color='white',
                font='Arial-Bold',
                stroke_color='black',
                stroke_width=2,
                size=(OUTPUT_WIDTH - 40, None),
                method='caption'
            ).set_position(('center', 30)).set_duration(resized.duration)
            
            layers = [resized, hook_clip]
            
            # Add caption at bottom if available
            if caption_text:
                caption_clip = TextClip(
                    caption_text,
                    fontsize=32,
                    color='white',
                    font='Arial',
                    bg_color='rgba(0,0,0,0.6)',
                    size=(OUTPUT_WIDTH - 40, None),
                    method='caption'
                ).set_position(('center', OUTPUT_HEIGHT - 150)).set_duration(resized.duration)
                layers.append(caption_clip)
            
            final_clip = CompositeVideoClip(layers, size=(OUTPUT_WIDTH, OUTPUT_HEIGHT))
        except Exception as text_err:
            # If text overlay fails, continue without it
            print(f"(text overlay skipped) ", end="")
            final_clip = resized
        
        # Render with optimal settings for social media
        final_clip.write_videofile(
            output_path,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            threads=4,
            preset='ultrafast',
            fps=30,
            logger=None
        )
        
        clip.close()
        print("✓ Done!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return False

# --- MAIN EXECUTION ---

def print_banner():
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║  ⚡ PULSEPOINT AI - Viral Clip Generator                     ║
    ║  ═══════════════════════════════════════════════════════════ ║
    ║  🎯 Powered by Google Gemini 1.5 Flash (1M Context Window)   ║
    ║  🎬 ByteSize Sage AI Hackathon Submission                    ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

def main():
    print_banner()
    
    # Handle command line argument or prompt
    if len(sys.argv) > 1:
        video_path = sys.argv[1].strip().strip('"')
    else:
        video_path = input("   📁 Enter video path (drag & drop): ").strip().strip('"')
    
    if not os.path.exists(video_path):
        print(f"   ❌ File not found: {video_path}")
        sys.exit(1)
    
    print(f"\n   📹 Processing: {os.path.basename(video_path)}")
    print(f"   📊 Size: {os.path.getsize(video_path) / 1024 / 1024:.1f} MB")
    
    try:
        # Phase 1: Upload
        gemini_file = upload_to_gemini(video_path)
        
        # Phase 2: AI Analysis
        raw_response = analyze_video_for_clips(gemini_file)
        clips = parse_gemini_json(raw_response)
        
        if not clips:
            print("\n   ❌ Failed to parse AI response. Raw output:")
            print(raw_response[:500])
            sys.exit(1)
        
        print(f"\n   🎯 [4/5] Found {len(clips)} Golden Nuggets! Generating Reels...\n")
        
        # Create output directory
        output_dir = os.path.join(os.path.dirname(video_path), "PulsePoint_Reels")
        os.makedirs(output_dir, exist_ok=True)
        
        # Phase 3: Render each clip
        results = []
        for idx, clip_data in enumerate(clips):
            hook = clip_data.get('hook_title', f'Clip {idx+1}')
            start_str = clip_data['start_time']
            end_str = clip_data['end_time']
            score = clip_data.get('virality_score', 'N/A')
            caption = clip_data.get('caption_text', '')
            
            print(f"   ┌─ 🎬 Reel {idx+1}: \"{hook}\"")
            print(f"   │  ⏱️  {start_str} → {end_str} | Score: {score}/10")
            
            start_sec = parse_time_string(start_str)
            end_sec = parse_time_string(end_str)
            
            output_video = os.path.join(output_dir, f"reel_{idx+1}_{hook.replace(' ', '_')[:20]}.mp4")
            output_thumb = os.path.join(output_dir, f"thumb_{idx+1}.jpg")
            
            success = process_video_clip(
                video_path, start_sec, end_sec, 
                output_video, hook, caption
            )
            
            if success:
                # Generate thumbnail
                generate_thumbnail(video_path, output_thumb, hook, start_sec + 1)
                results.append({
                    'video': output_video,
                    'thumbnail': output_thumb,
                    'hook': hook,
                    'score': score
                })
            
            print(f"   └─────────────────────────────────────────────")
        
        # Summary
        print(f"\n   ═══════════════════════════════════════════════════")
        print(f"   🎉 [5/5] COMPLETE! Generated {len(results)} viral reels")
        print(f"   📂 Output: {output_dir}")
        print(f"   ═══════════════════════════════════════════════════\n")
        
        # Open output folder
        if sys.platform == 'win32':
            os.startfile(output_dir)
        
    except Exception as e:
        print(f"\n   ❌ Critical Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
