import cv2
import numpy as np
import pickle
from pathlib import Path

def compress_video(in_path, out_path, palette_sample_rate=1, frame_limit=0):
    cap = cv2.VideoCapture(str(in_path))
    if not cap.isOpened():
        raise ValueError("Could not open video file.")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frames = []
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_limit and frame_count >= frame_limit:
            break
        if frame_count % palette_sample_rate == 0:
            # JPEG compression in memory
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 60]  # 60% quality
            _, buffer = cv2.imencode('.jpg', frame, encode_param)
            frames.append(buffer)
        frame_count += 1

    cap.release()

    # Save FPS and compressed frames
    data = {
        "frames": frames,
        "fps": fps / palette_sample_rate  # adjust playback speed for skipped frames
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

    # Decode one frame to get video size
    first_frame = cv2.imdecode(np.frombuffer(frames[0], np.uint8), cv2.IMREAD_COLOR)
    height, width, _ = first_frame.shape

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(str(out_path), fourcc, fps, (width, height))

    for buffer in frames:
        frame = cv2.imdecode(np.frombuffer(buffer, np.uint8), cv2.IMREAD_COLOR)
        out.write(frame)
    out.release()
