import cv2
import json
import zlib
import numpy as np
import gc
from PIL import Image
from pathlib import Path

def decompress_video(in_path, out_path):
    # Memory-efficient file reading
    try:
        with open(in_path, "rb") as f:
            compressed_data = f.read()
        
        # Try decompressing as v2/v3 format first
        try:
            json_str = zlib.decompress(compressed_data).decode('utf-8')
            data = json.loads(json_str)
            del json_str  # Free memory
        except:
            # Fallback to v1 format (plain JSON)
            with open(in_path, "r") as f:
                data = json.load(f)
        
        del compressed_data  # Free memory
        gc.collect()
        
    except Exception as e:
        raise ValueError(f"Could not read genesis file: {e}")
    
    # Support v1, v2, and v3 formats
    magic = data.get("magic", "GENESISVID-1")
    if magic not in ["GENESISVID-1", "GENESISVID-2", "GENESISVID-3"]:
        raise ValueError(f"Unsupported format: {magic}")
    
    w = int(data["width"])
    h = int(data["height"])
    original_fps = float(data.get("original_fps", 24))
    
    # v3 format has better duration preservation
    if magic == "GENESISVID-3":
        target_fps = data.get("target_fps", 20)
        original_duration = data.get("original_duration", 0)
        preserved_duration = data.get("preserved_duration", 0)
        frame_skip = data.get("frame_skip", 1)
        
        # Use target FPS for accurate playback
        playback_fps = target_fps
        print(f"v3: Original {original_duration:.1f}s -> Preserved {preserved_duration:.1f}s at {playback_fps} FPS")
    else:
        # Legacy format handling
        frame_skip = data.get("frame_skip", 1)
        playback_fps = original_fps / frame_skip
        
    # Ensure reasonable FPS range
    playback_fps = max(12, min(60, playback_fps))
    
    frames_hex = data["frames"]
    palette = np.array(data["palette"], dtype=np.uint8)
    
    # Create PIL palette
    pal_img = Image.new("P", (1, 1))
    flat_palette = []
    for rgb in palette:
        flat_palette.extend(rgb)
    pal_img.putpalette(flat_palette + [0]*(768-len(flat_palette)))
    
    # Use better codec and settings
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, playback_fps, (w, h))
    
    if not writer.isOpened():
        raise RuntimeError("Could not open VideoWriter")
    
    try:
        # Process frames in memory-efficient batches
        batch_size = 20
        total_frames = len(frames_hex)
        
        for batch_start in range(0, total_frames, batch_size):
            batch_end = min(batch_start + batch_size, total_frames)
            batch_frames = []
            
            # Decompress batch
            for i in range(batch_start, batch_end):
                try:
                    hx = frames_hex[i]
                    raw = zlib.decompress(bytes.fromhex(hx))
                    idx = np.frombuffer(raw, dtype=np.uint8).reshape((h, w))
                    
                    frame_p = Image.fromarray(idx, mode="P")
                    frame_p.putpalette(pal_img.getpalette())
                    frame_rgb = frame_p.convert("RGB")
                    frame_array = np.array(frame_rgb)
                    
                    batch_frames.append(frame_array)
                    
                    # Clean up immediately
                    del raw, idx, frame_p, frame_rgb
                    
                except Exception as e:
                    print(f"Warning: Could not decompress frame {i}: {e}")
                    # Use previous frame if available
                    if batch_frames:
                        batch_frames.append(batch_frames[-1].copy())
                    elif batch_start > 0:
                        # Use a black frame as fallback
                        black_frame = np.zeros((h, w, 3), dtype=np.uint8)
                        batch_frames.append(black_frame)
            
            # Apply smoothing to batch
            smoothed_batch = []
            for j, frame in enumerate(batch_frames):
                current_frame = frame.copy()
                
                # Temporal smoothing within batch
                if j > 0 and j < len(batch_frames) - 1:
                    prev_frame = batch_frames[j-1]
                    next_frame = batch_frames[j+1]
                    
                    # Gentle blending
                    current_frame = (
                        0.8 * current_frame.astype(np.float32) +
                        0.1 * prev_frame.astype(np.float32) +
                        0.1 * next_frame.astype(np.float32)
                    ).astype(np.uint8)
                
                # Light smoothing filter
                current_frame = cv2.GaussianBlur(current_frame, (3, 3), 0.3)
                smoothed_batch.append(current_frame)
            
            # Write batch to video
            for frame in smoothed_batch:
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                writer.write(frame_bgr)
                del frame_bgr
            
            # Clean up batch
            del batch_frames, smoothed_batch
            gc.collect()
            
    finally:
        writer.release()
        del frames_hex, palette, data
        gc.collect()
    
    print(f"Video reconstructed: {playback_fps} FPS, {total_frames} frames")
    return str(out_path)