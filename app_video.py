import streamlit as st
from compress_video import compress_video
from decompress_video import decompress_video
from pathlib import Path
import tempfile

st.set_page_config(page_title="SoulGenesis Video", page_icon="🎥", layout="centered")
st.title("🎥 SoulGenesis – Video Compression & Reconstruction")

# --- Compression ---
st.header("Compress a video → .genesisvid")
video_file = st.file_uploader("Upload MP4/MOV", type=["mp4", "mov", "mpeg4"], key="video_upload")

palette_every_n_frames = st.number_input("Palette sample every N frames", min_value=1, value=10)
frame_limit = st.number_input("Limit frames (0 = all)", min_value=0, value=0)

if video_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(video_file.name).suffix) as tmp_in:
        tmp_in.write(video_file.read())
        tmp_in_path = tmp_in.name
    
    out_path = Path(tempfile.gettempdir()) / (Path(video_file.name).stem + ".genesisvid")
    
    compress_video(tmp_in_path, out_path, palette_every_n_frames, frame_limit)
    
    st.success("✅ Video compressed successfully!")
    with open(out_path, "rb") as f:
        st.download_button("⬇️ Download Compressed .genesisvid", f, file_name=out_path.name)

# --- Decompression ---
st.header("Reconstruct video from .genesisvid")
genesisvid_file = st.file_uploader("Upload .genesisvid", type=["genesisvid"], key="genesisvid_upload")

if genesisvid_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".genesisvid") as tmp_in:
        tmp_in.write(genesisvid_file.read())
        tmp_in_path = tmp_in.name
    
    out_path = Path(tempfile.gettempdir()) / "reconstructed_video.mp4"
    
    decompress_video(tmp_in_path, out_path)
    
    st.success("✅ Video reconstructed successfully!")
    with open(out_path, "rb") as f:
        st.download_button("⬇️ Download Reconstructed Video", f, file_name="reconstructed_video.mp4")
