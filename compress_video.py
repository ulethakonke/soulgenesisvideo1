import cv2
import numpy as np
import json
import zlib
from PIL import Image
from pathlib import Path

def compress_video(in_path, out_path, palette_sample_rate=5, frame_limit=0, max_colors=64, quality_params=None):
    if quality_params is None:
        quality_params = {"skip_frames": 1, "resize_factor": 0.5}
    
    cap = cv2.VideoCapture(str(in_path))
    if not cap.isOpened():
        raise ValueError(f"Could not open video file: {in_path}")
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 24
    
    frames = []
    frame_count = 0
    all_pixels = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_limit and frame_count >= frame_limit:
            break
            
        if frame_count % quality_params["skip_frames"] == 0:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w = frame_rgb.shape[:2]
            new_h = int(h * quality_params["resize_factor"])
            new_w = int(w * quality_params["resize_factor"])
            frame_resized = cv2.resize(frame_rgb, (new_w, new_h))
            frames.append(frame_resized)
            
            pixels = frame_resized.reshape(-1, 3)
            step = max(1, len(pixels) // 200)
            all_pixels.extend(pixels[::step])
            
        frame_count += 1
    
    cap.release()
    
    if not frames:
        raise ValueError("No frames extracted")
    
    h, w = frames[0].shape[:2]
    
    all_pixels = np.array(all_pixels)
    if len(all_pixels) > 1000:
        indices = np.random.choice(len(all_pixels), 1000, replace=False)
        all_pixels = all_pixels[indices]
    
    palette = generate_palette(all_pixels, max_colors)
    
    pal_img = Image.new("P", (1, 1))
    flat_palette = []
    for rgb in palette:
        flat_palette.extend(rgb)
    pal_img.putpalette(flat_palette + [0]*(768-len(flat_palette)))
    
    compressed_frames = []
    for frame in frames:
        pil_frame = Image.fromarray(frame)
        frame_p = pil_frame.quantize(palette=pal_img, dither=0)
        indices = np.array(frame_p, dtype=np.uint8)
        compressed = zlib.compress(indices.tobytes(), level=5)
        compressed_frames.append(compressed.hex())
    
    data = {
        "magic": "GENESISVID-1",
        "width": w,
        "height": h,
        "original_fps": fps,
        "frame_skip": quality_params["skip_frames"],
        "frames": compressed_frames,
        "palette": palette.tolist()
    }
    
    with open(out_path, "w") as f:
        json.dump(data, f, separators=(',', ':'))

def generate_palette(pixels, num_colors):
    if len(pixels) == 0:
        return np.zeros((num_colors, 3), dtype=np.uint8)
    
    unique_pixels = np.unique(pixels.reshape(-1, 3), axis=0)
    
    if len(unique_pixels) <= num_colors:
        palette = np.zeros((num_colors, 3), dtype=np.uint8)
        palette[:len(unique_pixels)] = unique_pixels
        return palette
    
    kmeans = MiniBatchKMeans(n_clusters=num_colors, random_state=0)
    kmeans.fit(pixels)
    return kmeans.cluster_centers_.astype(np.uint8)