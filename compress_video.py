import cv2
import numpy as np
import json
import zlib
from PIL import Image
from pathlib import Path

def compress_video(in_path, out_path, palette_sample_rate=5, frame_limit=0, max_colors=64, quality_params=None):
    """Compress a video to GENESISVID-1 format"""
    
    if quality_params is None:
        quality_params = {"skip_frames": 1, "resize_factor": 0.6}
    
    # Open video
    cap = cv2.VideoCapture(str(in_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {in_path}")
    
    # Get video properties
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 24
    
    frames = []
    frame_count = 0
    all_pixels = []
    
    # Extract frames - simple approach
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_limit and frame_count >= frame_limit:
            break
            
        # Take every Nth frame only
        if frame_count % palette_sample_rate == 0:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize frame
            h, w = frame_rgb.shape[:2]
            new_h = int(h * quality_params["resize_factor"])
            new_w = int(w * quality_params["resize_factor"])
            frame_resized = cv2.resize(frame_rgb, (new_w, new_h))
            
            frames.append(frame_resized)
            
            # Sample pixels for palette
            pixels = frame_resized.reshape(-1, 3)
            # Take much fewer pixels
            step = len(pixels) // 200  # Only 200 pixels per frame
            if step < 1:
                step = 1
            all_pixels.extend(pixels[::step])
            
        frame_count += 1
    
    cap.release()
    
    if not frames:
        raise ValueError("No frames extracted")
    
    h, w = frames[0].shape[:2]
    
    # Generate palette from fewer pixels
    all_pixels = np.array(all_pixels)
    if len(all_pixels) > 1000:
        indices = np.random.choice(len(all_pixels), 1000, replace=False)
        all_pixels = all_pixels[indices]
    
    palette = generate_palette(all_pixels, max_colors)
    
    # Create PIL palette
    pal_img = Image.new("P", (1, 1))
    flat_palette = []
    for rgb in palette:
        flat_palette.extend(rgb)
    while len(flat_palette) < 768:
        flat_palette.append(0)
    pal_img.putpalette(flat_palette)
    
    # Compress frames to indices
    compressed_frames = []
    for frame in frames:
        pil_frame = Image.fromarray(frame)
        frame_p = pil_frame.quantize(palette=pal_img)
        indices = np.array(frame_p, dtype=np.uint8)
        
        # Compress the indices
        compressed = zlib.compress(indices.tobytes(), level=9)
        compressed_frames.append(compressed.hex())
    
    # Save data
    data = {
        "magic": "GENESISVID-1",
        "width": w,
        "height": h,
        "original_fps": fps,
        "frame_skip": palette_sample_rate,
        "frames": compressed_frames,
        "palette": palette.tolist()
    }
    
    with open(out_path, "w") as f:
        json.dump(data, f, separators=(',', ':'))

def generate_palette(pixels, num_colors):
    """Simple palette generation"""
    if len(pixels) == 0:
        return np.zeros((num_colors, 3), dtype=np.uint8)
    
    # Simple quantization
    unique_pixels = np.unique(pixels.reshape(-1, 3), axis=0)
    
    if len(unique_pixels) <= num_colors:
        palette = np.zeros((num_colors, 3), dtype=np.uint8)
        palette[:len(unique_pixels)] = unique_pixels
        return palette
    
    # Sample evenly
    indices = np.linspace(0, len(unique_pixels) - 1, num_colors, dtype=int)
    return unique_pixels[indices]

def decompress_video(in_path, out_path):
    """Decompress GENESISVID-1 file back to MP4"""
    
    with open(in_path, "r") as f:
        data = json.load(f)
    
    if data.get("magic") != "GENESISVID-1":
        raise ValueError("Not a GENESISVID-1 file")
    
    w = int(data["width"])
    h = int(data["height"])
    original_fps = float(data.get("original_fps", 24))
    frame_skip = data.get("frame_skip", 1)
    
    # Calculate proper playback FPS
    # We skipped frames, so we need to maintain timing
    playback_fps = original_fps / frame_skip
    
    # Keep it smooth - minimum 20 fps, maximum 30 fps
    if playback_fps > 30:
        playback_fps = 30
    elif playback_fps < 20:
        playback_fps = 20
    
    frames_hex = data["frames"]
    palette = np.array(data["palette"], dtype=np.uint8)
    
    # Create palette image
    pal_img = Image.new("P", (1, 1))
    flat_palette = []
    for rgb in palette:
        flat_palette.extend(rgb)
    while len(flat_palette) < 768:
        flat_palette.append(0)
    pal_img.putpalette(flat_palette)
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, playback_fps, (w, h))
    
    if not writer.isOpened():
        raise RuntimeError("Could not open VideoWriter")
    
    try:
        for hx in frames_hex:
            # Decompress frame
            raw = zlib.decompress(bytes.fromhex(hx))
            idx = np.frombuffer(raw, dtype=np.uint8).reshape((h, w))
            
            # Convert back to RGB
            frame_p = Image.fromarray(idx, mode="P")
            frame_p.putpalette(pal_img.getpalette())
            frame_rgb = frame_p.convert("RGB")
            
            # Convert to BGR for OpenCV
            frame_bgr = cv2.cvtColor(np.array(frame_rgb), cv2.COLOR_RGB2BGR)
            writer.write(frame_bgr)
    
    finally:
        writer.release()
    
    return str(out_path)