import cv2
import numpy as np
import json
import zlib
from PIL import Image
from pathlib import Path
from sklearn.cluster import MiniBatchKMeans

def compress_video(in_path, out_path, palette_sample_rate=5, frame_limit=0, max_colors=64, quality_params=None):
    if quality_params is None:
        quality_params = {"skip_frames": 1, "resize_factor": 0.5}
    
    cap = cv2.VideoCapture(str(in_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {in_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 24
    
    # Get total frame count for better sampling
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    frames = []
    frame_count = 0
    all_pixels = []
    
    # More aggressive frame skipping for better compression
    actual_skip = max(1, quality_params["skip_frames"])
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_limit and len(frames) >= frame_limit:
            break
            
        # Only process every nth frame for better compression
        if frame_count % actual_skip == 0:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame_rgb.shape[:2]
            
            # More aggressive resizing for better compression
            resize_factor = quality_params["resize_factor"]
            new_h = max(64, int(h * resize_factor))  # Minimum height
            new_w = max(64, int(w * resize_factor))  # Minimum width
            
            frame_resized = cv2.resize(frame_rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)
            frames.append(frame_resized)
            
            # Sample pixels more efficiently for palette generation
            if len(frames) % palette_sample_rate == 0:
                pixels = frame_resized.reshape(-1, 3)
                # Take more samples but more efficiently
                step = max(1, len(pixels) // 500)
                all_pixels.extend(pixels[::step])
            
        frame_count += 1
    
    cap.release()
    
    if not frames:
        raise ValueError("No frames extracted")
    
    h, w = frames[0].shape[:2]
    
    # Optimize palette generation
    all_pixels = np.array(all_pixels)
    if len(all_pixels) > 2000:
        indices = np.random.choice(len(all_pixels), 2000, replace=False)
        all_pixels = all_pixels[indices]
    
    # Generate optimized palette
    palette = generate_palette(all_pixels, max_colors)
    
    # Create PIL palette
    pal_img = Image.new("P", (1, 1))
    flat_palette = []
    for rgb in palette:
        flat_palette.extend(rgb)
    pal_img.putpalette(flat_palette + [0]*(768-len(flat_palette)))
    
    compressed_frames = []
    for i, frame in enumerate(frames):
        pil_frame = Image.fromarray(frame)
        
        # Use better quantization with error diffusion for smoother results
        frame_p = pil_frame.quantize(palette=pal_img, dither=Image.Dither.FLOYDSTEINBERG)
        indices = np.array(frame_p, dtype=np.uint8)
        
        # Use maximum compression
        compressed = zlib.compress(indices.tobytes(), level=9)
        compressed_frames.append(compressed.hex())
    
    # Store additional metadata for better reconstruction
    data = {
        "magic": "GENESISVID-2",  # Updated version
        "width": w,
        "height": h,
        "original_fps": fps,
        "frame_skip": actual_skip,
        "total_original_frames": total_frames,
        "frames": compressed_frames,
        "palette": palette.tolist(),
        "version": "2.0"
    }
    
    # Compress the entire JSON for even better compression
    json_str = json.dumps(data, separators=(',', ':'))
    final_compressed = zlib.compress(json_str.encode('utf-8'), level=9)
    
    with open(out_path, "wb") as f:
        f.write(final_compressed)

def generate_palette(pixels, num_colors):
    if len(pixels) == 0:
        return np.zeros((num_colors, 3), dtype=np.uint8)
    
    unique_pixels = np.unique(pixels.reshape(-1, 3), axis=0)
    
    if len(unique_pixels) <= num_colors:
        palette = np.zeros((num_colors, 3), dtype=np.uint8)
        palette[:len(unique_pixels)] = unique_pixels
        return palette
    
    # Use better clustering parameters
    kmeans = MiniBatchKMeans(
        n_clusters=num_colors, 
        random_state=42,
        batch_size=min(1000, len(pixels)),
        max_iter=100,
        n_init=3
    )
    kmeans.fit(pixels)
    return kmeans.cluster_centers_.astype(np.uint8)