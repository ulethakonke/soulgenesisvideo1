import cv2
import json
import zlib
import numpy as np
from PIL import Image
from pathlib import Path

def _grab_frames(path, max_frames=None, target_max_side=720):
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {path}")
    fps = cap.get(cv2.CAP_PROP_FPS) or 10.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frames = []
    count = 0
    while True:
        ok, frame_bgr = cap.read()
        if not ok:
            break
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        # Optional: downscale if huge (keeps aspect ratio)
        if max(h, w) > target_max_side:
            scale = target_max_side / max(h, w)
            frame_rgb = cv2.resize(frame_rgb, (int(w*scale), int(h*scale)), interpolation=cv2.INTER_AREA)
            h, w = frame_rgb.shape[:2]
        frames.append(Image.fromarray(frame_rgb))
        count += 1
        if max_frames and count >= max_frames:
            break
    cap.release()
    return frames, fps, w, h

def _build_global_palette(sample_images, colors=256, thumb=96):
    if not sample_images:
        raise ValueError("No frames to sample for palette.")
    # Stack small thumbnails to one strip, then quantize to get a stable palette
    thumbs = []
    for im in sample_images:
        thumbs.append(im.resize((thumb, int(im.height * (thumb / im.width))), Image.LANCZOS))
    strip_w = max(t.width for t in thumbs)
    strip_h = sum(t.height for t in thumbs)
    strip = Image.new("RGB", (strip_w, strip_h))
    y = 0
    for t in thumbs:
        strip.paste(t, (0, y))
        y += t.height
    pal_img = strip.quantize(colors=colors, method=Image.MEDIANCUT, dither=Image.NONE)
    # Extract palette as flat list length 768 (256*3); pad if shorter
    raw_pal = pal_img.getpalette()[:colors*3] if pal_img.getpalette() else []
    raw_pal = (raw_pal + [0]* (256*3 - len(raw_pal)))[:256*3]
    # Return as list of [r,g,b]
    palette = [raw_pal[i:i+3] for i in range(0, 256*3, 3)]
    return palette

def _quantize_with_palette(img, palette):
    pal_img = Image.new("P", (1,1))
    flat = []
    for rgb in palette:
        flat.extend(rgb)
    pal_img.putpalette(flat)
    # Force quantization to our fixed palette
    q = img.quantize(palette=pal_img, dither=Image.NONE)
    return q

def compress_video(in_path, out_path, sample_every=10, max_frames=None):
    in_path = Path(in_path)
    out_path = Path(out_path)
    frames, fps, w, h = _grab_frames(in_path, max_frames=max_frames)
    if not frames:
        raise RuntimeError("No frames decoded.")

    # Build palette from every Nth frame
    sample = frames[::max(1, sample_every)]
    palette = _build_global_palette(sample, colors=256)

    # Encode each frame as indices (bytes), then zlib compress -> hex string
    encoded_frames = []
    for im in frames:
        q = _quantize_with_palette(im, palette)
        idx = np.array(q, dtype=np.uint8)  # HxW indices 0..255
        comp = zlib.compress(idx.tobytes(), level=9)
        encoded_frames.append(comp.hex())

    container = {
        "magic": "GENESISVID-1",
        "width": w,
        "height": h,
        "fps": float(fps),
        "frame_count": len(frames),
        "palette": palette,   # [[r,g,b], ...] length 256
        "frames": encoded_frames
    }
    with open(out_path, "w") as f:
        json.dump(container, f)
    return {
        "frames": len(frames),
        "fps": fps,
        "w": w,
        "h": h,
        "out": str(out_path),
        "bytes": out_path.stat().st_size
    }

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python3 compress_video.py input.mp4 output.genesisvid")
        sys.exit(1)
    info = compress_video(sys.argv[1], sys.argv[2])
    print(f"Compressed {info['frames']} frames at {info['fps']:.2f} fps to {info['out']} ({info['bytes']} bytes)")
