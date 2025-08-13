import streamlit as st
from pathlib import Path
import tempfile
from compress_video import compress_video
from decompress_video import decompress_video

st.set_page_config(page_title="SoulGenesis Video", page_icon="🎬", layout="centered")
st.title("🎬 SoulGenesis – Video Compression & Reconstruction")

st.markdown("Upload a **short, low-FPS** clip to compress it into a `.genesisvid` file, or upload a `.genesisvid` to reconstruct an MP4.")

st.divider()
st.subheader("Compress a video → .genesisvid")
vid = st.file_uploader("Upload MP4/MOV", type=["mp4", "mov"], key="upl_vid")

col1, col2 = st.columns(2)
with col1:
    sample_every = st.number_input("Palette sample every N frames", min_value=1, max_value=50, value=10, step=1)
with col2:
    max_frames = st.number_input("Limit frames (0 = all)", min_value=0, value=0, step=1)

if vid:
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(vid.name).suffix) as tmp_in:
        tmp_in.write(vid.read())
        in_path = Path(tmp_in.name)
    out_path = Path(tempfile.gettempdir()) / (Path(vid.name).stem + ".genesisvid")
    info = compress_video(in_path, out_path, sample_every=int(sample_every), max_frames=int(max_frames) or None)
    st.success(f"Compressed {info['frames']} frames at {info['fps']:.2f} fps. Output size: {info['bytes']} bytes")
    with open(out_path, "rb") as f:
        st.download_button("⬇️ Download .genesisvid", f, file_name=out_path.name)

st.divider()
st.subheader("Reconstruct video from .genesisvid")
gvid = st.file_uploader("Upload .genesisvid", type=["genesisvid"], key="upl_genvid")
if gvid:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".genesisvid") as tmp_in:
        tmp_in.write(gvid.read())
        in_path = Path(tmp_in.name)
    out_path = Path(tempfile.gettempdir()) / (Path(gvid.name).stem + ".mp4")
    try:
        out_file = decompress_video(in_path, out_path)
        st.video(str(out_file))
        with open(out_file, "rb") as f:
            st.download_button("⬇️ Download reconstructed MP4", f, file_name=Path(out_file).name)
    except Exception as e:
        st.error(f"Reconstruction failed: {e}")
        st.info("If this is a codec issue on your system, try renaming output to .avi and using 'XVID' in the code.")
