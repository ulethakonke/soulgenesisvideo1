import cv2
import numpy as np
import json
import zlib
from PIL import Image
from pathlib import Path

def compress_video(in_path, out_path, palette_sample_rate=2, frame_limit=0, max_colors=128, quality_params=None):
    """Compress a video to GENESISVID-1 format"""
    
    if quality_params is None:
        quality_params = {"skip_frames": 1, "resize_factor": 0.7}
    
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
    
    # Extract frames
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_limit and frame_count >= frame_limit:
            break
            
        # Sample frames
        if frame_count % palette_sample_rate == 0:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize for compression
            h, w = frame_rgb.shape[:2]
            new_h = int(h * quality_params["resize_factor"])
            new_w = int(w * quality_params["resize_factor"])
            frame_resized = cv2.resize(frame_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            frames.append(frame_resized)
            
            # Sample pixels for palette
            pixels = frame_resized.reshape(-1, 3)
            step = max(1, len(pixels) // 1000)
            all_pixels.extend(pixels[::step])
            
        frame_count += 1
    
    cap.release()
    
    if not frames:
        raise ValueError("No frames extracted")
    
    h, w = frames[0].shape[:2]
    
    # Generate palette
    all_pixels = np.array(all_pixels)
    if len(all_pixels) > 5000:
        indices = np.random.choice(len(all_pixels), 5000, replace=False)
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
    
    # Compress frames
    compressed_frames = []
    for frame in frames:
        pil_frame = Image.fromarray(frame, mode="RGB")
        frame_p = pil_frame.quantize(palette=pal_img, dither=Image.FLOYDSTEINBERG)
        indices = np.array(frame_p, dtype=np.uint8)
        compressed = zlib.compress(indices.tobytes(), level=9)
        compressed_frames.append(compressed.hex())
    
    # Save compressed data
    data = {
        "magic": "GENESISVID-1",
        "width": w,
        "height": h,
        "fps": fps,
        "frame_interval": palette_sample_rate,
        "frames": compressed_frames,
        "palette": palette.tolist()
    }
    
    with open(out_path, "w") as f:
        json.dump(data, f, separators=(',', ':'))

def generate_palette(pixels, num_colors):
    """Generate color palette"""
    if len(pixels) == 0:
        return np.zeros((num_colors, 3), dtype=np.uint8)
    
    unique_pixels = np.unique(pixels.reshape(-1, pixels.shape[-1]), axis=0)
    
    if len(unique_pixels) <= num_colors:
        palette = np.zeros((num_colors, 3), dtype=np.uint8)
        palette[:len(unique_pixels)] = unique_pixels
        return palette
    
    indices = np.linspace(0, len(unique_pixels) - 1, num_colors, dtype=int)
    selected_colors = unique_pixels[indices]
    
    if len(selected_colors) < num_colors:
        padding = np.zeros((num_colors - len(selected_colors), 3), dtype=np.uint8)
        selected_colors = np.vstack([selected_colors, padding])
    
    return selected_colors

def decompress_video(in_path, out_path):
    """Decompress GENESISVID-1 file back to MP4"""
    
    with open(in_path, "r") as f:
        data = json.load(f)
    
    if data.get("magic") != "GENESISVID-1":
        raise ValueError("Not a GENESISVID-1 file")
    
    w = int(data["width"])
    h = int(data["height"])
    fps = float(data.get("fps", 24))
    frame_interval = data.get("frame_interval", 1)
    
    # Calculate playback FPS for smooth motion (20-30 FPS range)
    calculated_fps = fps / frame_interval
    
    if calculated_fps < 20:
        playback_fps = 20
    elif calculated_fps > 30:
        playback_fps = 30
    else:
        playback_fps = calculated_fps
    
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