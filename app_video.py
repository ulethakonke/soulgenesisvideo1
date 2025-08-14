import streamlit as st
import tempfile
from pathlib import Path
from compress_video import compress_video, decompress_video

st.title("🎥 SoulGenesis Video Compressor")

st.header("Compress a video → .genesisvid")
uploaded_file = st.file_uploader("Upload MP4/MOV", type=["mp4", "mov", "mpeg4"])

palette_sample_rate = st.number_input(
    "Palette sample every N frames", min_value=1, value=10
)
frame_limit = st.number_input(
    "Limit frames (0 = all)", min_value=0, value=0
)

if uploaded_file is not None:
    # Save the uploaded file to a temp location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
        tmp.write(uploaded_file.read())
        in_path = tmp.name

    out_path = Path(in_path).with_suffix(".genesisvid")
    compress_video(in_path, out_path, palette_sample_rate, frame_limit)

    st.success("✅ Compression complete!")
    with open(out_path, "rb") as f:
        st.download_button(
            label="⬇ Download Compressed File (.genesisvid)",
            data=f,
            file_name="compressed.genesisvid",
            mime="application/octet-stream"
        )

st.header("Reconstruct video from .genesisvid")
uploaded_genesis = st.file_uploader("Upload .genesisvid", type=["genesisvid"])

if uploaded_genesis is not None:
    # Save the uploaded .genesisvid file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".genesisvid") as tmp:
        tmp.write(uploaded_genesis.read())
        in_path = tmp.name

    out_path = Path(in_path).with_suffix(".mp4")
    decompress_video(in_path, out_path)

    st.success("✅ Decompression complete!")
    with open(out_path, "rb") as f:
        st.download_button(
            label="⬇ Download Reconstructed Video (.mp4)",
            data=f,
            file_name="reconstructed.mp4",
            mime="video/mp4"
        )
