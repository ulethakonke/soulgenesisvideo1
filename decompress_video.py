import cv2
import json
import zlib
import numpy as np
from PIL import Image
from pathlib import Path

def _palette_image(palette):
    pal_img = Image.new("P", (1,1))
    flat = []
    for rgb in palette:
        flat.extend(rgb)
    pal_img.putpalette(flat)
    return pal_img

def decompress_video(in_path, out_path):
    in_path = Path(in_path)
    out_path = Path(out_path)

    with open(in_path, "r") as f:
        data = json.load(f)

    if data.get("magic") != "GENESISVID-1":
        raise ValueError("Not a GENESISVID-1 file.")

    w = int(data["width"])
    h = int(data["height"])
    fps = float(data["fps"])
    frames_hex = data["frames"]
    palette = data["palette"]

    pal_img = _palette_image(palette)

    # Try MP4; if your OpenCV build can't write mp4, change to .avi and fourcc below
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(out_path), fourcc, fps, (w, h))
    if not writer.isOpened():
        raise RuntimeError("Could not open VideoWriter. If this fails, try an .avi filename and use 'XVID' codec.")

    for hx in frames_hex:
        raw = zlib.decompress(bytes.fromhex(hx))
        idx = np.frombuffer(raw, dtype=np.uint8).reshape((h, w))
        frame_p = Image.fromarray(idx, mode="P")
        frame_p.putpalette(pal_img.getpalette())
        frame_rgb = frame_p.convert("RGB")
        frame_bgr = cv2.cvtColor(np.array(frame_rgb), cv2.COLOR_RGB2BGR)
        writer.write(frame_bgr)

    writer.release()
    return str(out_path)

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python3 decompress_video.py input.genesisvid output.mp4")
        sys.exit(1)
    out = decompress_video(sys.argv[1], sys.argv[2])
    print(f"Wrote reconstructed video: {out}")
