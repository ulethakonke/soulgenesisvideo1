import streamlit as st
import cv2
import numpy as np
import pickle
from pathlib import Path
from sklearn.cluster import MiniBatchKMeans
import tempfile
import uuid

# ------------------- Compression Functions -------------------

def quantize_frame(frame, num_colors=64):
    """Reduce frame colors to a fixed palette."""
    h, w, _ = frame.shape
    reshaped = frame.reshape((-1, 3))

    # KMeans clustering to reduce colors
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
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (width, height))

    for idx, labels in enumerate(frames_indexed):
        palette = palettes[idx]
        frame = palette[labels]  # Map indexes back to colors
        out.write(frame.astype(np.uint8))

    out.release()
    return fps

# ------------------- Streamlit UI -------------------

st.set_page_config(page_title="SoulGenesis Video Compression", layout="centered")
st.title("🎥 SoulGenesis Video Compressor")
st.write("Compress videos into `.genesisvid` format with color palette quantization for massive size reduction.")

st.header("📦 Compress a video → .genesisvid")
uploaded_video = st.file_uploader("Upload MP4/MOV", type=["mp4", "mov", "m4v"])
palette_sample_rate = st.number_input("Palette sample every N frames", min_value=1, value=10, step=1)
frame_limit = st.number_input("Limit frames (0 = all)", min_value=0, value=0, step=1)
num_colors = st.slider("Number of colors in palette", min_value=16, max_value=256, value=64, step=16)

if uploaded_video is not None:
    if st.button("Compress Video"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(uploaded_video.read())
            temp_video_path = Path(tmp.name)

        out_name = f"compressed_{uuid.uuid4().hex}.genesisvid"
        out_path = Path(tempfile.gettempdir()) / out_name

        try:
            compress_video(str(temp_video_path), str(out_path), palette_sample_rate, frame_limit, num_colors)
            with open(out_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Compressed File",
                    data=f,
                    file_name=out_name,
                    mime="application/octet-stream"
                )
        except Exception as e:
            st.error(f"Error during compression: {e}")

st.header("🔄 Reconstruct video from .genesisvid")
uploaded_genesis = st.file_uploader("Upload .genesisvid", type=["genesisvid"])

if uploaded_genesis is not None:
    if st.button("Decompress Video"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".genesisvid") as tmp:
            tmp.write(uploaded_genesis.read())
            temp_genesis_path = Path(tmp.name)

        out_video_name = f"decompressed_{uuid.uuid4().hex}.mp4"
        out_video_path = Path(tempfile.gettempdir()) / out_video_name

        try:
            fps = decompress_video(str(temp_genesis_path), str(out_video_path))
            with open(out_video_path, "rb") as f:
                st.download_button(
                    label=f"⬇️ Download Decompressed Video ({fps:.2f} FPS)",
                    data=f,
                    file_name=out_video_name,
                    mime="video/mp4"
                )
        except Exception as e:
            st.error(f"Error during decompression: {e}")
