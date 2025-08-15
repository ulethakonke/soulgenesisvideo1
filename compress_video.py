import cv2
import numpy as np
import pickle
from sklearn.cluster import MiniBatchKMeans

def quantize_frame(frame, num_colors=64):
    """Reduce frame colors to a fixed palette."""
    h, w, c = frame.shape
    reshaped = frame.reshape((-1, 3))

    # Use MiniBatchKMeans for speed
    kmeans = MiniBatchKMeans(n_clusters=num_colors, random_state=0, batch_size=2048)
    labels = kmeans.fit_predict(reshaped)
    palette = kmeans.cluster_centers_.astype(np.uint8)

    return labels.reshape((h, w)), palette

def compress_video(input_path, output_path, palette_sample_rate=10, frame_limit=0, num_colors=64):
    cap = cv2.VideoCapture(input_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frames_indexed = []
    palettes = []
    count = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        if frame_limit > 0 and count >= frame_limit:
            break
        if count % palette_sample_rate == 0:
            labels, palette = quantize_frame(frame, num_colors)
            frames_indexed.append(labels)
            palettes.append(palette)
        count += 1
    cap.release()

    data = {
        "fps": fps,
        "frames": frames_indexed,
        "palettes": palettes,
        "shape": frames_indexed[0].shape
    }
    with open(output_path, "wb") as f:
        pickle.dump(data, f)

def decompress_video(input_path, output_path):
    with open(input_path, "rb") as f:
        data = pickle.load(f)

    fps = data["fps"]
    frames_indexed = data["frames"]
    palettes = data["palettes"]
    height, width = data["shape"]

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

    for idx, labels in enumerate(frames_indexed):
        palette = palettes[idx]
        frame = palette[labels]  # Map indexes back to colors
        out.write(frame.astype(np.uint8))

    out.release()
    return fps
