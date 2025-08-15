import streamlit as st
from pathlib import Path
from compress_video import compress_video, decompress_video

st.set_page_config(page_title="SoulGenesis Video Compressor", layout="centered")

st.title("🎥 SoulGenesis Video Compressor")
st.write("Compress videos to `.genesisvid` format and reconstruct them with correct FPS.")

# ==============================
# SECTION 1 — Compress Video
# ==============================
st.header("📦 Compress a Video → `.genesisvid`")

uploaded_video = st.file_uploader("Upload MP4/MOV", type=["mp4", "mov", "mpeg4"], key="compress")
palette_sample_rate = st.number_input("Palette sample every N frames", min_value=1, value=10)
frame_limit = st.number_input("Limit frames (0 = all)", min_value=0, value=0)

if uploaded_video is not None:
    temp_video_path = Path("temp_input_video.mp4")
    with open(temp_video_path, "wb") as f:
        f.write(uploaded_video.read())  # Save uploaded file locally

    out_path = Path("compressed.genesisvid")

    if st.button("🚀 Compress Video"):
        try:
            compress_video(str(temp_video_path), str(out_path), palette_sample_rate, frame_limit)
            st.success(f"Video compressed successfully: {out_path}")

            # Download button for compressed file
            with open(out_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Compressed .genesisvid",
                    data=f,
                    file_name=out_path.name,
                    mime="application/octet-stream"
                )

        except Exception as e:
            st.error(f"Error during compression: {e}")

# ==============================
# SECTION 2 — Decompress Video
# ==============================
st.header("♻️ Reconstruct Video from `.genesisvid`")

uploaded_genesis = st.file_uploader("Upload `.genesisvid`", type=["genesisvid"], key="decompress")

if uploaded_genesis is not None:
    temp_genesis_path = Path("temp_input_file.genesisvid")
    with open(temp_genesis_path, "wb") as f:
        f.write(uploaded_genesis.read())  # Save uploaded file locally

    out_video_path = Path("reconstructed.mp4")

    if st.button("🔄 Decompress Video"):
        try:
            fps = decompress_video(str(temp_genesis_path), str(out_video_path))
            st.success(f"Video reconstructed successfully at {fps} FPS: {out_video_path}")

            # Download button for reconstructed MP4
            with open(out_video_path, "rb") as f:
                st.download_button(
                    label="⬇️ Download Reconstructed MP4",
                    data=f,
                    file_name=out_video_path.name,
                    mime="video/mp4"
                )

            # Preview video in browser
            st.video(str(out_video_path))

        except Exception as e:
            st.error(f"Error during decompression: {e}")
