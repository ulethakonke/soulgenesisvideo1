import cv2
import numpy as np
import json
import zlib
from PIL import Image
from pathlib import Path

def compress_video(in_path, out_path, palette_sample_rate=10, frame_limit=0, max_colors=64, quality_params=None):
    """
    Compress a video to GENESISVID-1 format using palette-based compression
    """
    if quality_params is None:
        quality_params = {"skip_frames": 2, "resize_factor": 0.6}
    
    cap = cv2.VideoCapture(str(in_path))
    
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {in_path}")
    
    # Get video properties before processing
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 24  # Default fallback
    
    frames = []
    frame_count = 0
    all_pixels = []
    
    # First pass: collect frames and pixels for palette generation
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_limit and frame_count >= frame_limit:
            break
        
        # Skip frames for compression - but not too aggressively
        if frame_count % palette_sample_rate == 0:
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Resize frame for compression
            resize_factor = quality_params["resize_factor"]
            h, w = frame_rgb.shape[:2]
            new_h, new_w = int(h * resize_factor), int(w * resize_factor)
            frame_resized = cv2.resize(frame_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            frames.append(frame_resized)
            
            # Collect pixels for palette (sample subset to avoid memory issues)
            pixels = frame_resized.reshape(-1, 3)
            step = max(1, len(pixels) // 1000)  # Much smaller sample
            all_pixels.extend(pixels[::step])
        frame_count += 1
    
    cap.release()
    
    if not frames:
        raise ValueError("No frames were extracted from the video")
    
    h, w = frames[0].shape[:2]
    
    # Calculate the actual frame interval we used (just palette_sample_rate now)
    actual_frame_interval = palette_sample_rate
    
    # Limit pixels for palette generation
    all_pixels = np.array(all_pixels)
    if len(all_pixels) > 5000:  # Much smaller limit
        indices = np.random.choice(len(all_pixels), 5000, replace=False)
        all_pixels = all_pixels[indices]
    
    # Create smaller palette
    palette = generate_palette(all_pixels, max_colors)
    
    # Create palette image for PIL
    pal_img = Image.new("P", (1, 1))
    flat_palette = []
    for rgb in palette:
        flat_palette.extend(rgb)
    # Pad palette to 768 values if needed (256 * 3)
    while len(flat_palette) < 768:
        flat_palette.append(0)
    pal_img.putpalette(flat_palette)
    
    # Convert frames to palette indices with better compression
    compressed_frames = []
    for frame in frames:
        # Convert to PIL Image
        pil_frame = Image.fromarray(frame, mode="RGB")
        # Apply palette with dithering for better quality
        frame_p = pil_frame.quantize(palette=pal_img, dither=Image.FLOYDSTEINBERG)
        # Get indices
        indices = np.array(frame_p, dtype=np.uint8)
        
        # Use higher compression level
        compressed = zlib.compress(indices.tobytes(), level=9)
        compressed_frames.append(compressed.hex())
    
    # Save to JSON format with minimal whitespace
    data = {
        "magic": "GENESISVID-1",
        "width": w,
        "height": h,
        "fps": fps,  # Keep original FPS
        "frame_interval": actual_frame_interval,  # Store the actual frame interval we used
        "frames": compressed_frames,
        "palette": palette.tolist()
    }
    
    with open(out_path, "w") as f:
        json.dump(data, f, separators=(',', ':'))  # No whitespace

def generate_palette(pixels, num_colors):
    """
    Generate a palette using a simple k-means-like clustering
    """
    if len(pixels) == 0:
        return np.zeros((num_colors, 3), dtype=np.uint8)
    
    # Simple but effective palette generation
    # Reduce colors by quantizing each channel
    unique_pixels = np.unique(pixels.reshape(-1, pixels.shape[-1]), axis=0)
    
    if len(unique_pixels) <= num_colors:
        # Pad with black if we have fewer unique colors than requested
        palette = np.zeros((num_colors, 3), dtype=np.uint8)
        palette[:len(unique_pixels)] = unique_pixels
        return palette
    
    # Use uniform sampling in RGB space for better distribution
    indices = np.linspace(0, len(unique_pixels) - 1, num_colors, dtype=int)
    selected_colors = unique_pixels[indices]
    
    # Ensure we have exactly num_colors
    if len(selected_colors) < num_colors:
        padding = np.zeros((num_colors - len(selected_colors), 3), dtype=np.uint8)
        selected_colors = np.vstack([selected_colors, padding])
    
    return selected_colors

def decompress_video(in_path, out_path):
    """
    Decompress a GENESISVID-1 file back to MP4
    """
    in_path = Path(in_path)
    out_path = Path(out_path)
    
    with open(in_path, "r") as f:
        data = json.load(f)
    
    if data.get("magic") != "GENESISVID-1":
        raise ValueError("Not a GENESISVID-1 file.")
    
    w = int(data["width"])
    h = int(data["height"])
    
    # Use original FPS for proper playback speed
    fps = float(data.get("fps", 24))
    frame_interval = data.get("frame_interval", 1)
    
    # Calculate the correct playback FPS
    # If we took every Nth frame, we need to play back at fps/N to maintain correct timing
    playback_fps = fps / frame_interval
    
    # Ensure minimum playback FPS for smoothness
    if playback_fps < 15:
        playback_fps = 15
    
    print(f"Original FPS: {fps}, Frame interval: {frame_interval}, Playback FPS: {playback_fps}")
    
    frames_hex = data["frames"]
    palette = np.array(data["palette"], dtype=np.uint8)
    
    # Create palette image
    pal_img = Image.new("P", (1, 1))
    flat_palette = []
    for rgb in palette:
        flat_palette.extend(rgb)
    # Pad to 768 if needed
    while len(flat_palette) < 768:
        flat_palette.append(0)
    pal_img.putpalette(flat_palette)
    
    # Initialize video writer with correct FPS
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, playback_fps, (w, h))
    
    if not writer.isOpened():
        raise RuntimeError("Could not open VideoWriter. Try changing the output to .avi extension.")
    
    try:
        for hx in frames_hex:
            # Decompress frame indices
            raw = zlib.decompress(bytes.fromhex(hx))
            idx = np.frombuffer(raw, dtype=np.uint8).reshape((h, w))
            
            # Convert indices back to RGB using palette
            frame_p = Image.fromarray(idx, mode="P")
            frame_p.putpalette(pal_img.getpalette())
            frame_rgb = frame_p.convert("RGB")
            
            # Convert RGB to BGR for OpenCV
            frame_bgr = cv2.cvtColor(np.array(frame_rgb), cv2.COLOR_RGB2BGR)
            writer.write(frame_bgr)
    
    finally:
        writer.release()
    
    return str(out_path)