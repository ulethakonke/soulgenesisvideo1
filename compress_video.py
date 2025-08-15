import cv2
import numpy as np
import pickle

def compress_video(input_path, output_path, palette_sample_rate=10, frame_limit=0):
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)  # Store FPS
    frames = []
    count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_limit > 0 and count >= frame_limit:
            break
        if count % palette_sample_rate == 0:
            frames.append(frame)
        count += 1
    cap.release()

    data = {"fps": fps, "frames": frames}
    with open(output_path, "wb") as f:
        pickle.dump(data, f)

def decompress_video(input_path, output_path):
    with open(input_path, "rb") as f:
        data = pickle.load(f)

    fps = data["fps"]
    frames = data["frames"]
    height, width, _ = frames[0].shape

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for frame in frames:
        out.write(frame)
    out.release()

    return fps  # So Streamlit can display correct FPS
