import streamlit as st
from pathlib import Path
from compress_video import compress_video
from decompress_video import decompress_video
import tempfile

st.set_page_config(page_title="SoulGenesis Video", page_icon="🎥", layout="centered")
st.title("🎥 SoulGenesis Video Compressor")

st.markdown("### Compress a video → `.genesisvid`")
uploaded_file = st.file_uploader("Upload MP4/MOV", type=["mp4", "mov", "mpeg4"], help="Limit 200MB per file")
palette_sample_rate = st.number_input("Palette sample every N frames", min_value=1, value=10)
frame_limit = st.number_input("Limit frames (0 = all)", min_value=0, value=0)

if st.button("Start Compression"):
    if uploaded_file is not None:
        # Save uploaded file to a temp location
        temp_in = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4")
        temp_in.write(uploaded_file.read())
        temp_in.close()

        out_path = Path("compressed.genesisvid")
        compress_video(temp_in.name, out_path, palette_sample_rate, frame_limit)

        st.success("✅ Video compressed successfully!")

        # Show size difference
        original_size = Path(temp_in.name).stat().st_size / (1024 * 1024)
        compressed_size = out_path.stat().st_size / (1024 * 1024)
        reduction = (1 - compressed_size / original_size) * 100
        st.write(f"**Original size:** {original_size:.2f} MB")
        st.write(f"**Compressed size:** {compressed_size:.2f} MB")
        st.write(f"**Reduction:** {reduction:.1f}% smaller")

        # Download compressed file
        with open(out_path, "rb") as f:
            st.download_button(
                label="⬇️ Download Compressed File",
                data=f,
                file_name=out_path.name,
                mime="application/octet-stream"
            )
    else:
        st.warning("⚠️ Please upload a video first.")

st.markdown("---")
st.markdown("### Reconstruct video from `.genesisvid`")
uploaded_genesis = st.file_uploader("Upload `.genesisvid`", type=["genesisvid"], help="Limit 200MB per file")

if st.button("Start Decompression"):
    if uploaded_genesis is not None:
        # Save uploaded .genesisvid file to temp
        temp_genesis = tempfile.NamedTemporaryFile(delete=False, suffix=".genesisvid")
        temp_genesis.write(uploaded_genesis.read())
        temp_genesis.close()

        out_video_path = Path("reconstructed.mp4")
        decompress_video(temp_genesis.name, out_video_path)

        st.success("✅ Video reconstructed successfully!")

        # Show decompressed file size
        reconstructed_size = out_video_path.stat().st_size / (1024 * 1024)
        st.write(f"**Reconstructed size:** {reconstructed_size:.2f} MB")

        # Download decompressed file
        with open(out_video_path, "rb") as f:
            st.download_button(
                label="⬇️ Download Reconstructed Video",
                data=f,
                file_name=out_video_path.name,
                mime="video/mp4"
            )
    else:
        st.warning("⚠️ Please upload a `.genesisvid` file first.")
