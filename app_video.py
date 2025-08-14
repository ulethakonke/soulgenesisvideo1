import streamlit as st
import tempfile
import os
from pathlib import Path
from compress_video import compress_video, decompress_video

st.title("🎥 SoulGenesis Video Compressor")

st.header("Compress a video → .genesisvid")
uploaded_file = st.file_uploader("Upload MP4/MOV", type=["mp4", "mov", "mpeg4"], key="compress_uploader")

palette_sample_rate = st.number_input(
    "Palette sample every N frames", min_value=1, value=10
)
frame_limit = st.number_input(
    "Limit frames (0 = all)", min_value=0, value=0
)

if uploaded_file is not None:
    try:
        # Create unique temp file paths
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_input:
            tmp_input.write(uploaded_file.read())
            in_path = tmp_input.name
        
        # Create output path
        out_path = str(Path(in_path).with_suffix(".genesisvid"))
        
        # Compress the video
        compress_video(in_path, out_path, palette_sample_rate, frame_limit)
        
        st.success("✅ Compression complete!")
        
        # Read the compressed file and offer download
        with open(out_path, "rb") as f:
            compressed_data = f.read()
            st.download_button(
                label="⬇ Download Compressed File (.genesisvid)",
                data=compressed_data,
                file_name="compressed.genesisvid",
                mime="application/octet-stream"
            )
        
        # Clean up temporary files
        try:
            os.unlink(in_path)
            os.unlink(out_path)
        except:
            pass  # Don't fail if cleanup fails
            
    except Exception as e:
        st.error(f"Error during compression: {str(e)}")

st.header("Reconstruct video from .genesisvid")
uploaded_genesis = st.file_uploader("Upload .genesisvid", type=["genesisvid"], key="decompress_uploader")

if uploaded_genesis is not None:
    try:
        # Create unique temp file paths
        with tempfile.NamedTemporaryFile(delete=False, suffix=".genesisvid") as tmp_input:
            tmp_input.write(uploaded_genesis.read())
            in_path = tmp_input.name
        
        # Create output path
        out_path = str(Path(in_path).with_suffix(".mp4"))
        
        # Decompress the video
        decompress_video(in_path, out_path)
        
        st.success("✅ Decompression complete!")
        
        # Read the decompressed file and offer download
        with open(out_path, "rb") as f:
            video_data = f.read()
            st.download_button(
                label="⬇ Download Reconstructed Video (.mp4)",
                data=video_data,
                file_name="reconstructed.mp4",
                mime="video/mp4"
            )
        
        # Clean up temporary files
        try:
            os.unlink(in_path)
            os.unlink(out_path)
        except:
            pass  # Don't fail if cleanup fails
            
    except Exception as e:
        st.error(f"Error during decompression: {str(e)}")