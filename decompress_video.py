import cv2
import json
import zlib
import numpy as np
from PIL import Image
from pathlib import Path

def decompress_video(in_path, out_path):
    with open(in_path, "r") as f:
        data = json.load(f)
    
    if data.get("magic") != "GENESISVID-1":
        raise ValueError("Not a GENESISVID-1 file")
    
    w = int(data["width"])
    h = int(data["height"])
    original_fps = float(data.get("original_fps", 24))
    frame_skip = data.get("frame_skip", 1)
    
    playback_fps = original_fps / frame_skip
    playback_fps = min(30, max(20, playback_fps))
    
    frames_hex = data["frames"]
    palette = np.array(data["palette"], dtype=np.uint8)
    
    pal_img = Image.new("P", (1, 1))
    flat_palette = []
    for rgb in palette:
        flat_palette.extend(rgb)
    pal_img.putpalette(flat_palette + [0]*(768-len(flat_palette)))
    
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, playback_fps, (w, h))
    
    if not writer.isOpened():
        raise RuntimeError("Could not open VideoWriter")
    
    try:
        for hx in frames_hex:
            raw = zlib.decompress(bytes.fromhex(hx))
            idx = np.frombuffer(raw, dtype=np.uint8).reshape((h, w))
            frame_p = Image.fromarray(idx, mode="P")
            frame_p.putpalette(pal_img.getpalette())
            frame_rgb = frame_p.convert("RGB")
            frame_bgr = cv2.cvtColor(np.array(frame_rgb), cv2.COLOR_RGB2BGR)
            writer.write(frame_bgr)
    finally:
        writer.release()
    
    return str(out_path)