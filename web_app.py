"""
⚡ PULSEPOINT AI - Flask Web Application
HTML/CSS Frontend + Python Backend
ByteSize Sage AI Hackathon
"""

from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
from moviepy.editor import VideoFileClip
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['REELS_FOLDER'] = 'static/reels'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['REELS_FOLDER'], exist_ok=True)

# Store results globally for simplicity
results = {"reels": [], "done": False}

def get_hooks(n):
    return ["This Changes Everything", "Nobody Tells You This", "Wait For It...", "Mind = Blown", "The Secret Truth"][:n]

def process_clip(video_path, start, end, output_path):
    """Cut and crop to vertical 9:16"""
    try:
        clip = VideoFileClip(video_path)
        end = min(end, clip.duration)
        subclip = clip.subclip(start, end)
        
        w, h = subclip.size
        if w / h > 9/16:
            new_w = int(h * 9/16)
            x1 = (w - new_w) / 2
            cropped = subclip.crop(x1=x1, y1=0, x2=x1+new_w, y2=h)
        else:
            cropped = subclip
        
        cropped.write_videofile(output_path, codec="libx264", audio_codec="aac",
                                temp_audiofile='temp-audio.m4a', remove_temp=True,
                                threads=4, preset='ultrafast', logger=None)
        clip.close()
        return True
    except Exception as e:
        print(f"Error: {e}")
        return False

@app.route('/')
def index():
    return render_template('index.html', reels=results["reels"], done=results["done"])

@app.route('/upload', methods=['POST'])
def upload():
    global results
    results = {"reels": [], "done": False}
    
    if 'video' not in request.files:
        return redirect('/')
    
    file = request.files['video']
    if file.filename == '':
        return redirect('/')
    
    filename = secure_filename(file.filename)
    video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(video_path)
    
    print(f"Processing: {video_path}")
    
    # Get duration
    clip = VideoFileClip(video_path)
    duration = clip.duration
    clip.close()
    print(f"Duration: {duration/60:.1f} min")
    
    # Generate 5 clips evenly distributed
    num_clips = 5
    clip_duration = 45
    hooks = get_hooks(num_clips)
    
    interval = (duration * 0.8) / (num_clips + 1)
    
    for i in range(num_clips):
        peak = duration * 0.1 + interval * (i + 1)
        start = max(0, peak - clip_duration/2)
        end = min(duration, peak + clip_duration/2)
        
        hook = hooks[i]
        safe_hook = "".join(c for c in hook if c.isalnum() or c in " _-")[:15]
        reel_filename = f"reel_{i+1}_{safe_hook}.mp4"
        reel_path = os.path.join(app.config['REELS_FOLDER'], reel_filename)
        
        print(f"Rendering reel {i+1}: {start:.0f}s - {end:.0f}s")
        
        if process_clip(video_path, start, end, reel_path):
            results["reels"].append({
                "filename": reel_filename,
                "hook": hook,
                "score": 8 - i % 3,
                "start": f"{int(start//60):02d}:{int(start%60):02d}",
                "end": f"{int(end//60):02d}:{int(end%60):02d}"
            })
            print(f"✓ Reel {i+1} done!")
    
    results["done"] = True
    print(f"✓ All done! {len(results['reels'])} reels generated")
    
    return redirect('/')

if __name__ == '__main__':
    print("\n" + "="*50)
    print("⚡ PULSEPOINT AI - Web Application")
    print("="*50)
    print("\n🌐 Open: http://127.0.0.1:5000\n")
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True)
