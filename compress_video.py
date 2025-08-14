import cv2
import numpy as np
import pickle
from pathlib import Path

def compress_video(in_path, out_path, palette_sample_rate=10, frame_limit=0):
    cap = cv2.VideoCapture(str(in_path))
    frames = []
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_limit and frame_count >= frame_limit:
            break
        if frame_count % palette_sample_rate == 0:
            frames.append(frame)
        frame_count += 1

    cap.release()

    # Very basic palette compression simulation
    data = {
        "frames": frames,
        "fps": cap.get(cv2.CAP_PROP_FPS)
    }
    with open(out_path, "wb") as f:
        pickle.dump(data, f)

def decompress_video(in_path, out_path):
    with open(in_path, "rb") as f:
        data = pickle.load(f)

    frames = data["frames"]
    fps = data.get("fps", 24)

    if not frames:
        raise ValueError("No frames found in compressed file.")

    height, width, layers = frames[0].shape
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

    for frame in frames:
        out.write(frame)
    out.release()
