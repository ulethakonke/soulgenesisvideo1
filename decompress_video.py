import cv2
import json
import zlib
import numpy as np
from PIL import Image
from pathlib import Path

def decompress_video(in_path, out_path):
    # Try to read as compressed binary first (v2), then fallback to JSON (v1)
    try:
        with open(in_path, "rb") as f:
            compressed_data = f.read()
        
        # Try decompressing as v2 format
        try:
            json_str = zlib.decompress(compressed_data).decode('utf-8')
            data = json.loads(json_str)
        except:
            # Fallback to v1 format (plain JSON)
            with open(in_path, "r") as f:
                data = json.load(f)
    except Exception as e:
        raise ValueError(f"Could not read genesis file: {e}")
    
    # Support both v1 and v2 formats
    magic = data.get("magic", "GENESISVID-1")
    if magic not in ["GENESISVID-1", "GENESISVID-2"]:
        raise ValueError(f"Unsupported format: {magic}")
    
    w = int(data["width"])
    h = int(data["height"])
    original_fps = float(data.get("original_fps", 24))
    frame_skip = data.get("frame_skip", 1)
    
    # Calculate smooth playback FPS
    # Ensure minimum 15 FPS for smooth playback
    playback_fps = original_fps / frame_skip
    if playback_fps < 15:
        playback_fps = 15
    elif playback_fps > 60:
        playback_fps = 60
    
    frames_hex = data["frames"]
    palette = np.array(data["palette"], dtype=np.uint8)
    
    # Create PIL palette
    pal_img = Image.new("P", (1, 1))
    flat_palette = []
    for rgb in palette:
        flat_palette.extend(rgb)
    pal_img.putpalette(flat_palette + [0]*(768-len(flat_palette)))
    
    # Use better codec for smoother playback
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, playback_fps, (w, h))
    
    if not writer.isOpened():
        raise RuntimeError("Could not open VideoWriter")
    
    try:
        processed_frames = []
        
        # First pass: decompress all frames
        for i, hx in enumerate(frames_hex):
            try:
                raw = zlib.decompress(bytes.fromhex(hx))
                idx = np.frombuffer(raw, dtype=np.uint8).reshape((h, w))
                
                frame_p = Image.fromarray(idx, mode="P")
                frame_p.putpalette(pal_img.getpalette())
                frame_rgb = frame_p.convert("RGB")
                
                # Apply smoothing filter to reduce blockiness
                frame_array = np.array(frame_rgb)
                processed_frames.append(frame_array)
                
            except Exception as e:
                print(f"Warning: Could not decompress frame {i}: {e}")
                # Use previous frame if available
                if processed_frames:
                    processed_frames.append(processed_frames[-1])
        
        # Second pass: apply temporal smoothing and frame interpolation
        smoothed_frames = []
        
        for i, frame in enumerate(processed_frames):
            current_frame = frame.copy()
            
            # Temporal smoothing: blend with adjacent frames
            if i > 0 and i < len(processed_frames) - 1:
                prev_frame = processed_frames[i-1]
                next_frame = processed_frames[i+1]
                
                # Weighted average for smoother transitions
                current_frame = (
                    0.7 * current_frame.astype(np.float32) +
                    0.15 * prev_frame.astype(np.float32) +
                    0.15 * next_frame.astype(np.float32)
                ).astype(np.uint8)
            
            # Apply gentle gaussian blur to reduce pixelation
            current_frame = cv2.GaussianBlur(current_frame, (3, 3), 0.5)
            
            smoothed_frames.append(current_frame)
        
        # Frame interpolation for very low frame rates
        if playback_fps < 20 and len(smoothed_frames) > 1:
            interpolated_frames = []
            for i in range(len(smoothed_frames) - 1):
                interpolated_frames.append(smoothed_frames[i])
                
                # Add interpolated frame between current and next
                current = smoothed_frames[i].astype(np.float32)
                next_frame = smoothed_frames[i + 1].astype(np.float32)
                interpolated = (0.5 * current + 0.5 * next_frame).astype(np.uint8)
                interpolated_frames.append(interpolated)
            
            # Add the last frame
            interpolated_frames.append(smoothed_frames[-1])
            smoothed_frames = interpolated_frames
            playback_fps *= 2  # Double the FPS since we doubled frames
        
        # Write all frames
        for frame in smoothed_frames:
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            writer.write(frame_bgr)
            
    finally:
        writer.release()
    
    return str(out_path)