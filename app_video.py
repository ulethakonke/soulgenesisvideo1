import streamlit as st
import cv2
import numpy as np
import os
import tempfile
from pathlib import Path

# -----------------------------
# Video Compression
# -----------------------------
def compress_video(input_path, output_path, num_colors=64, palette_sample_rate=10, frame_limit=0):
    cap = cv2.VideoCapture(str(input_path))
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    
    # Sample frames for palette building
    sample_frames = []
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % palette_sample_rate == 0:
            sample_frames.append(frame)
        frames.append(frame)
        frame_idx += 1
        if frame_limit > 0 and frame_idx >= frame_limit:
            break
    cap.release()

    # Build palette using OpenCV k-means
    all_pixels = np.vstack([f.reshape(-1, 3) for f in sample_frames])
    all_pixels = np.float32(all_pixels)
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 20, 1.0)
    _, labels, palette = cv2.kmeans(all_pixels, num_colors, None, criteria, 10, cv2.KMEANS_RANDOM_CENTERS)
    palette = np.uint8(palette)

    # Quantize all frames
    quantized_frames = []
    for frame in frames:
        h, w, _ = frame.shape
        pixels = frame.reshape(-1, 3)
        pixels = np.float32(pixels)
        _, labels, _ = cv2.kmeans(pixels, num_colors, None, criteria, 1, cv2.KMEANS_USE_INITIAL_LABELS, centers=palette)
        new_frame = palette[labels.flatten()].reshape(h, w, 3)
        quantized_frames.append(new_frame)

    # Save compressed data
    np.savez_compressed(output_path, frames=quantized_frames, fps=fps, palette=palette)
    return fps

# -----------------------------
# Video Decompression
# -----------------------------
def decompress_video(input_path, output_path):
    data = np.load(input_path, allow_pickle=True)
    frames = data['frames']
    fps = float(data['fps'])
    
    h, w, _ = frames[0].shape
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(str(output_path), fourcc, fps, (w, h))

    for frame in frames:
        out.write(frame)
    out.release()

# -----------------------------
# Streamlit UI
# -----------------------------
st.title("🎥 SoulGenesis Video Compression")

mode = st.radio("Select mode", ["Compress video → .genesisvid", "Decompress .genesisvid → video"])

if mode == "Compress video → .genesisvid":
    uploaded_file = st.file_uploader("Upload MP4/MOV", type=["mp4", "mov", "mpeg4"])
    num_colors = st.slider("Number of colors in palette", 8, 256, 64)
    palette_sample_rate = st.slider("Palette sample every N frames", 1, 30, 10)
    frame_limit = st.number_input("Limit frames (0 = all)", min_value=0, step=1)

    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(uploaded_file.read())
            in_path = Path(tmp.name)

        out_path = Path(f"{uploaded_file.name}_compressed.genesisvid")
        if st.button("Compress"):
            try:
                fps = compress_video(in_path, out_path, num_colors, palette_sample_rate, frame_limit)
                with open(out_path, "rb") as f:
                    st.download_button(
                        label="Download Compressed File",
                        data=f,
                        file_name=out_path.name,
                        mime="application/octet-stream"
                    )
                st.success(f"Compression complete! Original FPS preserved: {fps:.2f}")
            except Exception as e:
                st.error(f"Error during compression: {e}")

elif mode == "Decompress .genesisvid → video":
    uploaded_file = st.file_uploader("Upload .genesisvid", type=["genesisvid"])
    if uploaded_file:
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(uploaded_file.read())
            in_path = Path(tmp.name)

        out_path = Path(f"decompressed_{Path(uploaded_file.name).stem}.mp4")
        if st.button("Decompress"):
            try:
                decompress_video(in_path, out_path)
                with open(out_path, "rb") as f:
                    st.download_button(
                        label="Download Decompressed Video",
                        data=f,
                        file_name=out_path.name,
                        mime="video/mp4"
                    )
                st.success("Decompression complete! Video smoothness preserved.")
            except Exception as e:
                st.error(f"Error during decompression: {e}")
